#!/usr/bin/env python3
"""Auto axis describer: infer a semantic axis from a sorted projection list.

Given a list of ``(role|trait, projection)`` pairs -- raw scalar projections
of each entity onto an unknown direction in a semantic embedding space of
role and trait concepts -- this tool asks Claude Opus to identify the latent
semantic axis that direction captures, and writes a structured spec
(``axis_name``, ``pos_pole``, ``neg_pole``, ``pos_examples``,
``neg_examples``) suitable for plugging straight into
``axis_judge_correlation.py``.

The tool is geometry-agnostic: callers handle the layer / whitening / shear
upstream. We just receive numbers, z-normalize them (mean to 0, sd to 1),
round to 0.1 precision, and ask Opus what the axis is about.

Inputs
------
``--input scored.json|csv`` -- list of ``{name, type, score}`` entries.

* ``name``  -- filename format with underscores (e.g. ``systems_thinker``).
* ``type``  -- ``R`` / ``T`` / ``role`` / ``trait`` / ``roles`` / ``traits``
  (case-insensitive).
* ``score`` -- any float (the raw scalar projection; tool does the
  z-normalization internally).

``--instructions_dir`` (default ``data``) -- directory holding
``{roles,traits}/instructions/*.json`` files; used to build the glossary.

Outputs
-------
A JSON file at ``--output`` containing exactly:

.. code-block:: json

    {
      "axis_name": "...",
      "pos_pole": "...",
      "neg_pole": "...",
      "pos_examples": ["name1", "name2", ...],
      "neg_examples": ["name1", "name2", ...]
    }

``pos_examples`` / ``neg_examples`` are converted back to filename format
so they pipe straight into ``axis_judge_correlation.py``::

    --pos_examples $(cat axis_spec.json | jq -r '.pos_examples | join(",")')

Model
-----
Default ``DEFAULT_MODEL = "claude-opus-4-6"`` (versioned alias; pinned to the
4.6 release line). Extended thinking enabled by default with a 10K-token
budget. ``temperature=1`` (API-enforced when thinking is on).

CLI
---
::

    uv run python results_analysis/infer_axis_description.py \\
      --input scored.json --output axis_spec.json \\
      [--style glossary] [--model claude-opus-4-6] [--top_n 0]

Library
-------
::

    from results_analysis.infer_axis_description import summarize_axis
    result = summarize_axis(
        scores=[{"name": "helpful", "type": "trait", "score": 2.34}, ...],
    )
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("infer_axis")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-opus-4-6"          # Versioned alias; bump explicitly to a
                                            # dated snapshot if Anthropic ever
                                            # rotates this alias under us.
DEFAULT_THINKING_BUDGET = 10_000           # Extended-thinking tokens (output-billed)
DEFAULT_MAX_TOKENS = 12_000                # Includes the thinking budget; the
                                            # API requires max_tokens > thinking
                                            # budget. We give the response itself
                                            # ~2K headroom.
DEFAULT_STYLE = "glossary"                 # "glossary" | "inline"
DEFAULT_INSTRUCTIONS_DIR = Path("data")
DEFAULT_TYPE_FALLBACK_GLOSSARY = "data"    # Glossary lookup root


# ---------------------------------------------------------------------------
# Type normalization
# ---------------------------------------------------------------------------

_TYPE_ALIASES = {
    "r": "role", "role": "role", "roles": "role",
    "t": "trait", "trait": "trait", "traits": "trait",
}


def _normalize_type(t: str) -> str:
    """Accept R/T/role/trait/roles/traits (any case); return 'role' or 'trait'."""
    s = str(t).strip().lower()
    if s not in _TYPE_ALIASES:
        raise ValueError(f"Unknown entity type {t!r} (expected R/T/role/trait/roles/traits)")
    return _TYPE_ALIASES[s]


# ---------------------------------------------------------------------------
# Glossary loading
# ---------------------------------------------------------------------------

def _glossary_dir(instructions_dir: Path, etype: str) -> Path:
    """Map normalized type ('role'/'trait') to the on-disk subdirectory.

    Repo layout: ``data/roles/instructions/*.json`` and ``data/traits/instructions/*.json``.
    """
    plural = {"role": "roles", "trait": "traits"}[etype]
    return instructions_dir / plural / "instructions"


def _load_entity_json(instructions_dir: Path, etype: str, name: str) -> dict[str, Any]:
    p = _glossary_dir(instructions_dir, etype) / f"{name}.json"
    if not p.exists():
        raise FileNotFoundError(f"No {etype} JSON for {name!r} at {p}")
    return json.loads(p.read_text())


def _display_label(etype: str, name: str, blob: dict[str, Any]) -> str:
    """Filename -> display label.

    * Traits: use the JSON's ``positive_label`` (e.g. ``systems-thinker``).
    * Roles : convert filename underscores to spaces (``paperclip_maximizer`` ->
      ``paperclip maximizer``); roles never use hyphens by convention.
    """
    if etype == "trait":
        lbl = blob.get("positive_label")
        if lbl:
            return str(lbl)
        # Fall through to the role rule if a trait somehow lacks the label.
        logger.warning(f"trait {name!r}: no positive_label; falling back to underscore->space")
    return name.replace("_", " ")


def _entity_description(blob: dict[str, Any]) -> str:
    return str(blob.get("description", "")).strip()


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def _load_input_file(path: Path) -> list[dict[str, Any]]:
    """Read a {name, type, score} list from .json or .csv."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected JSON list, got {type(data).__name__}")
        return data
    if suffix == ".csv":
        out: list[dict[str, Any]] = []
        with path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                out.append({
                    "name": row["name"].strip(),
                    "type": row["type"].strip(),
                    "score": float(row["score"]),
                })
        return out
    raise ValueError(f"{path}: unsupported extension {suffix!r}; use .json or .csv")


def _validate_and_normalize_scores(
    scores: Iterable[dict[str, Any]],
) -> list[tuple[str, str, float]]:
    """Returns [(name, etype, raw_score), ...]; deduped on (name, etype)."""
    seen: dict[tuple[str, str], float] = {}
    for entry in scores:
        name = str(entry["name"]).strip()
        etype = _normalize_type(entry["type"])
        score = float(entry["score"])
        key = (name, etype)
        if key in seen:
            logger.warning(f"duplicate entry for {etype} {name!r}; keeping last")
        seen[key] = score
    if len(seen) < 5:
        raise ValueError(f"need at least 5 entities; got {len(seen)}")
    return [(n, t, s) for (n, t), s in seen.items()]


def _z_normalize(scores: list[tuple[str, str, float]]) -> list[tuple[str, str, float]]:
    raw = np.array([s for _, _, s in scores], dtype=np.float64)
    mu = float(raw.mean())
    sd = float(raw.std(ddof=0))
    if sd < 1e-12:
        raise ValueError("all input projections are (essentially) equal; cannot z-normalize")
    z = (raw - mu) / sd
    return [(n, t, float(z[i])) for i, (n, t, _) in enumerate(scores)]


def _filter_by_top_n(
    scored: list[tuple[str, str, float]], top_n: int,
) -> list[tuple[str, str, float]]:
    """If top_n > 0, keep top-N and bottom-N by z-score; else keep all."""
    if top_n <= 0:
        return scored
    sorted_desc = sorted(scored, key=lambda x: x[2], reverse=True)
    if 2 * top_n >= len(sorted_desc):
        return sorted_desc
    head = sorted_desc[:top_n]
    tail = sorted_desc[-top_n:]
    return head + tail


# ---------------------------------------------------------------------------
# Display label map (bidirectional)
# ---------------------------------------------------------------------------

class LabelMap:
    """Holds (name, etype) <-> display_label, plus descriptions, for entities
    that appear in the input scoring list. Glossary is filtered to these only.
    """

    def __init__(
        self,
        scored: list[tuple[str, str, float]],
        instructions_dir: Path,
    ) -> None:
        self.entries: list[dict[str, Any]] = []  # ordered by ranking
        self._label_to_key: dict[str, tuple[str, str]] = {}
        for name, etype, z in scored:
            blob = _load_entity_json(instructions_dir, etype, name)
            label = _display_label(etype, name, blob)
            desc = _entity_description(blob)
            self.entries.append({
                "name": name,
                "etype": etype,
                "z": z,
                "label": label,
                "description": desc,
            })
            self._label_to_key[self._fuzzy_key(label)] = (name, etype)

    @staticmethod
    def _fuzzy_key(s: str) -> str:
        """Normalize a label string for fuzzy lookup."""
        return re.sub(r"[^a-z0-9]+", "", s.lower())

    def filename_for_label(self, label_or_name: str) -> Optional[str]:
        """Look up a model-emitted example back to filename format.

        Accepts the display label, the filename, or anything close (lowercase
        + alphanumerics). Returns None if no match.
        """
        s = label_or_name.strip()
        # Exact filename match
        for entry in self.entries:
            if entry["name"] == s:
                return entry["name"]
        # Fuzzy display-label match
        key = self._fuzzy_key(s)
        if key in self._label_to_key:
            return self._label_to_key[key][0]
        # Fuzzy filename match (handles e.g. spaces in user output)
        for entry in self.entries:
            if self._fuzzy_key(entry["name"]) == key:
                return entry["name"]
        return None


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

# TODO(phrase-cleanup): Opus tends to start each pole description with
# "This pole represents ..." / "This represents ..." / "This end represents ...".
# That works fine when interpolated into ``axis_judge_correlation.py``'s rubric
# template ("**+3 (strong positive pole):** {pos_pole}"), but produces a mild
# cosmetic redundancy ("(strong positive pole):** This pole represents ...")
# vs. the hand-written rubric style ("This means ..." for traits, "A {name} is
# ..." for roles). Two ways to fix when it bites:
#   1. Add a one-liner style hint to OUTPUT_SCHEMA_INSTRUCTIONS asking for
#      "This means ..." phrasing. Risk: any prompt change risks shifting the
#      axis-inference behavior beyond just the opening clause; not worth it
#      for a cosmetic gain.
#   2. Add a separate post-processing step that does a trivial Sonnet (cheap)
#      call: "Rewrite this pole description in 'This means ...' style without
#      changing meaning." Robust, reversible, decoupled from the inference
#      call. Probably the right answer when this becomes a problem.
# For now: leave as-is. Re-runs of axis_judge_correlation.py work fine with
# either phrasing; the redundancy is purely cosmetic.

SYSTEM_PROMPT = (
    "You are characterizing a direction in a semantic embedding space of role "
    "and trait concepts. You'll be shown a list of role/trait concepts with "
    "their definitions, sorted by their projection onto an unknown direction in "
    "that embedding space. Identify what semantic axis this direction captures, "
    "and write descriptions of each pole in the style of the supplied "
    "definitions."
)

OUTPUT_SCHEMA_INSTRUCTIONS = """\
Produce your answer in exactly the following format. Do not add any other \
text outside the tags.

<axis_name>
A short conceptual title for the axis, ideally phrased as "POSITIVE_POLE \
vs NEGATIVE_POLE" using natural-language pole names (e.g. "ecocentric vs \
anthropocentric"). The positive pole corresponds to the high (positive z) \
end of the ranking; the negative pole to the low end.
</axis_name>

<pos_pole>
1-3 sentences describing concepts at the positive (high-z) end of the axis. \
Match the style of the supplied role/trait descriptions: focus on what kind \
of person/persona/behaviour this end represents, in plain prose.
</pos_pole>

<neg_pole>
1-3 sentences describing concepts at the negative (low-z) end, same style.
</neg_pole>

<pos_examples>
A comma-separated list of 5 to 10 names from the ranking that best exemplify \
the positive pole. Use the names exactly as they appear in the ranking \
(e.g. "systems-thinker", "paperclip maximizer").
</pos_examples>

<neg_examples>
A comma-separated list of 5 to 10 names from the ranking that best exemplify \
the negative pole. Same naming convention as pos_examples.
</neg_examples>
"""


def _format_z(z: float) -> str:
    """Round to 0.1 with explicit sign."""
    rounded = round(z, 1)
    # Avoid "-0.0"
    if rounded == 0.0:
        rounded = 0.0
    return f"{rounded:+.1f}"


def _type_letter(etype: str) -> str:
    return {"role": "R", "trait": "T"}[etype]


def build_prompt(label_map: LabelMap, style: str) -> str:
    """Build the user-side prompt for the Opus call.

    ``style``: ``"glossary"`` (compact ranking + alphabetical glossary) or
    ``"inline"`` (ranking with descriptions on each line).
    """
    if style not in ("glossary", "inline"):
        raise ValueError(f"unknown style {style!r}; expected 'glossary' or 'inline'")

    # Sort high-to-low for the ranking.
    ranked = sorted(label_map.entries, key=lambda e: e["z"], reverse=True)

    # Pad the rank index width and the label width for readability.
    rank_w = len(str(len(ranked)))
    label_w = max(len(e["label"]) for e in ranked)

    if style == "inline":
        ranking_lines = []
        for i, e in enumerate(ranked, 1):
            line = (
                f"#{i:0{rank_w}}  {_format_z(e['z'])}  {_type_letter(e['etype'])}  "
                f"{e['label']:<{label_w}}  - {e['description']}"
            )
            ranking_lines.append(line)
        ranking_block = "\n".join(ranking_lines)

        return (
            "Below is a sorted list of role/trait concepts, ranked high-to-low "
            "by their projection onto an unknown direction in the embedding "
            "space. The numeric column is the projection (z-normalized to mean "
            "0, standard deviation 1 across all listed entities, rounded to "
            "0.1). T = trait, R = role.\n\n"
            "--- ranking ---\n"
            f"{ranking_block}\n"
            "--- end ranking ---\n\n"
            f"{OUTPUT_SCHEMA_INSTRUCTIONS}"
        )

    # glossary style
    ranking_lines = []
    for i, e in enumerate(ranked, 1):
        line = (
            f"#{i:0{rank_w}}  {_format_z(e['z'])}  {_type_letter(e['etype'])}  "
            f"{e['label']}"
        )
        ranking_lines.append(line)
    ranking_block = "\n".join(ranking_lines)

    glossary_sorted = sorted(label_map.entries, key=lambda e: e["label"].lower())
    label_w_g = max(len(e["label"]) for e in glossary_sorted)
    glossary_lines = []
    for e in glossary_sorted:
        glossary_lines.append(
            f"{e['label']:<{label_w_g}}  ({_type_letter(e['etype'])}) - {e['description']}"
        )
    glossary_block = "\n".join(glossary_lines)

    return (
        "Below is a sorted list of role/trait concepts, ranked high-to-low "
        "by their projection onto an unknown direction in the embedding space. "
        "The numeric column is the projection (z-normalized to mean 0, "
        "standard deviation 1 across all listed entities, rounded to 0.1). "
        "T = trait, R = role.\n\n"
        "--- ranking ---\n"
        f"{ranking_block}\n"
        "--- end ranking ---\n\n"
        "An alphabetical glossary of every concept in the ranking follows. "
        "Use it to look up any unfamiliar names while you reason about the "
        "axis.\n\n"
        "--- glossary ---\n"
        f"{glossary_block}\n"
        "--- end glossary ---\n\n"
        f"{OUTPUT_SCHEMA_INSTRUCTIONS}"
    )


# ---------------------------------------------------------------------------
# Anthropic call + parsing
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<\s*([a-zA-Z_]+)\s*>(.*?)<\s*/\s*\1\s*>", re.DOTALL)


def _extract_tag(text: str, tag: str) -> Optional[str]:
    for m in _TAG_RE.finditer(text):
        if m.group(1) == tag:
            return m.group(2).strip()
    return None


def parse_response(text: str) -> dict[str, Any]:
    """Parse the tag-delimited Opus response into a dict (raw, before
    converting examples back to filename format).

    Raises ValueError if any required tag is missing or empty.
    """
    out: dict[str, Any] = {}
    for tag in ("axis_name", "pos_pole", "neg_pole", "pos_examples", "neg_examples"):
        val = _extract_tag(text, tag)
        if val is None or not val.strip():
            raise ValueError(f"response missing/empty <{tag}>")
        out[tag] = val.strip()

    # Normalize the example lists: split on commas, strip, drop empties.
    for k in ("pos_examples", "neg_examples"):
        items = [x.strip() for x in out[k].split(",")]
        out[k] = [x for x in items if x]
    return out


def _resolve_examples(
    examples: list[str], label_map: LabelMap, side: str,
) -> list[str]:
    """Convert model-emitted display labels back to filename format."""
    out: list[str] = []
    for raw in examples:
        fn = label_map.filename_for_label(raw)
        if fn is None:
            logger.warning(
                f"{side}: model returned example {raw!r} that couldn't be matched "
                f"to a filename; dropping"
            )
            continue
        out.append(fn)
    if not out:
        logger.warning(f"{side}: no examples survived filename resolution")
    return out


async def _call_opus(
    prompt: str,
    *,
    model: str,
    thinking_budget: int,
    max_tokens: int,
) -> str:
    """One Anthropic call, with extended thinking iff thinking_budget > 0.

    Returns the concatenated assistant text (excluding any thinking blocks).
    """
    import anthropic

    client = anthropic.AsyncAnthropic()
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    if thinking_budget > 0:
        # API requires temperature == 1 when thinking is enabled, and
        # max_tokens > thinking.budget_tokens.
        if max_tokens <= thinking_budget:
            raise ValueError(
                f"max_tokens ({max_tokens}) must exceed thinking_budget "
                f"({thinking_budget}); leave at least ~1-2K for the response."
            )
        kwargs["temperature"] = 1.0
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
    else:
        kwargs["temperature"] = 0.0

    resp = await client.messages.create(**kwargs)

    parts: list[str] = []
    for block in resp.content:
        # Skip thinking blocks; only collect the visible "text" output.
        btype = getattr(block, "type", None)
        if btype == "text":
            t = getattr(block, "text", None)
            if t:
                parts.append(t)
        elif btype == "thinking":
            # We don't surface thinking content; it's billed but not used.
            continue
    if not parts:
        raise RuntimeError("Anthropic returned no text content blocks")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarize_axis(
    scores: list[dict[str, Any]],
    *,
    instructions_dir: Path = DEFAULT_INSTRUCTIONS_DIR,
    style: str = DEFAULT_STYLE,
    model: str = DEFAULT_MODEL,
    thinking_budget: int = DEFAULT_THINKING_BUDGET,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    top_n: int = 0,
) -> dict[str, Any]:
    """Infer an axis description from a sorted projection list.

    Parameters
    ----------
    scores : list of {"name": str, "type": str, "score": float}
        Raw scalar projections of each entity onto the unknown direction.
        ``name`` is in filename format (underscores). ``type`` is any of
        R/T/role/trait/roles/traits (case-insensitive). The tool z-normalizes
        ``score`` internally and rounds to 0.1.
    instructions_dir : Path, optional
        Repo-relative directory holding ``{roles,traits}/instructions/*.json``.
        Default: ``data``.
    style : {"glossary", "inline"}, optional
        Layout for the prompt sent to Opus. Default ``"glossary"``: compact
        one-line-per-entity ranking + alphabetical glossary block. ``"inline"``
        puts each entity's description on the same line as its rank.
    model : str, optional
        Anthropic model name. Default ``DEFAULT_MODEL``.
    thinking_budget : int, optional
        Extended-thinking token budget. Default ``DEFAULT_THINKING_BUDGET``.
        Set to 0 to disable extended thinking (and use ``temperature=0``).
    max_tokens : int, optional
        Total output budget; must exceed ``thinking_budget`` when thinking is
        enabled. Default ``DEFAULT_MAX_TOKENS``.
    top_n : int, optional
        If >0, keep only the top-N and bottom-N entities (by z-score) in the
        prompt; otherwise include all. Default 0 (all).

    Returns
    -------
    dict
        ``{"axis_name", "pos_pole", "neg_pole", "pos_examples", "neg_examples"}``
        where ``pos_examples`` / ``neg_examples`` are in filename format.
    """
    return asyncio.run(
        _summarize_axis_async(
            scores=scores,
            instructions_dir=Path(instructions_dir),
            style=style,
            model=model,
            thinking_budget=thinking_budget,
            max_tokens=max_tokens,
            top_n=top_n,
        )
    )


async def _summarize_axis_async(
    *,
    scores: list[dict[str, Any]],
    instructions_dir: Path,
    style: str,
    model: str,
    thinking_budget: int,
    max_tokens: int,
    top_n: int,
) -> dict[str, Any]:
    if os.getenv("ANTHROPIC_API_KEY") is None:
        raise EnvironmentError("ANTHROPIC_API_KEY not set (load via .env)")

    raw = _validate_and_normalize_scores(scores)
    z_scored = _z_normalize(raw)
    if top_n > 0:
        z_scored = _filter_by_top_n(z_scored, top_n)

    label_map = LabelMap(z_scored, instructions_dir)
    prompt = build_prompt(label_map, style=style)
    n_chars = len(prompt)
    logger.info(
        f"calling {model} with {len(label_map.entries)} entities, "
        f"style={style}, prompt={n_chars:,} chars (~{n_chars // 4:,} tokens), "
        f"thinking_budget={thinking_budget}"
    )

    try:
        text = await _call_opus(
            prompt,
            model=model,
            thinking_budget=thinking_budget,
            max_tokens=max_tokens,
        )
    except Exception as e:
        logger.error(f"first call to Opus failed: {e}")
        raise

    try:
        parsed = parse_response(text)
    except ValueError as e:
        logger.warning(f"parse failed ({e}); retrying with a clarifying follow-up")
        retry_prompt = (
            prompt
            + "\n\n[Note: a previous attempt did not match the required output schema. "
            "Please respond using exactly the five tagged blocks shown above, "
            "with no other text outside the tags.]"
        )
        text = await _call_opus(
            retry_prompt,
            model=model,
            thinking_budget=thinking_budget,
            max_tokens=max_tokens,
        )
        parsed = parse_response(text)

    # Convert example labels back to filename format.
    parsed["pos_examples"] = _resolve_examples(parsed["pos_examples"], label_map, "pos_examples")
    parsed["neg_examples"] = _resolve_examples(parsed["neg_examples"], label_map, "neg_examples")
    return parsed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Infer an axis description from a sorted projection list of role/trait "
            "concepts using Claude Opus. Produces a JSON spec compatible with "
            "axis_judge_correlation.py."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input", type=Path, required=True,
                   help="Path to a JSON or CSV file with [{name, type, score}, ...].")
    p.add_argument("--output", type=Path, required=True,
                   help="Path to write the inferred axis spec (JSON).")
    p.add_argument("--instructions_dir", type=Path, default=DEFAULT_INSTRUCTIONS_DIR,
                   help="Repo-relative dir holding {roles,traits}/instructions/*.json.")
    p.add_argument("--style", choices=("glossary", "inline"), default=DEFAULT_STYLE,
                   help="Prompt layout: glossary (compact ranking + alphabetical "
                        "glossary block) or inline (descriptions on each line).")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Anthropic model name.")
    p.add_argument("--thinking_budget", type=int, default=DEFAULT_THINKING_BUDGET,
                   help="Extended-thinking token budget (0 disables).")
    p.add_argument("--max_tokens", type=int, default=DEFAULT_MAX_TOKENS,
                   help="Total output budget; must exceed thinking_budget when "
                        "thinking is enabled.")
    p.add_argument("--top_n", type=int, default=0,
                   help="If >0, keep only the top-N and bottom-N entities by "
                        "z-score in the prompt (cheaper). 0 = include all.")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    raw = _load_input_file(args.input)
    logger.info(f"loaded {len(raw)} entries from {args.input}")

    result = summarize_axis(
        scores=raw,
        instructions_dir=args.instructions_dir,
        style=args.style,
        model=args.model,
        thinking_budget=args.thinking_budget,
        max_tokens=args.max_tokens,
        top_n=args.top_n,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2))
    logger.info(f"wrote {args.output}")

    print(f"\naxis_name : {result['axis_name']}")
    print(f"pos_pole  : {result['pos_pole']}")
    print(f"neg_pole  : {result['neg_pole']}")
    print(f"pos_examples ({len(result['pos_examples'])}): {', '.join(result['pos_examples'])}")
    print(f"neg_examples ({len(result['neg_examples'])}): {', '.join(result['neg_examples'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
