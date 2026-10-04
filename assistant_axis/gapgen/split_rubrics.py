"""The split filter's eight prompts, read from Roger's rubric files, and their version pins.

Each file in :data:`paths.RUBRICS_DIR` holds one prompt inside a fenced block under the heading
"## The prompt"::

    ## The prompt

    ````text
    <the prompt, sent byte for byte>
    ````

:func:`load_prompt` returns the text between the two fence lines, exactly as the probe scripts
extracted it (the same regular expression), so the hash of a loaded prompt equals the hash recorded
by the paid runs that tuned it.  Roger edits these files himself; the code never rewrites them.

The rule of :mod:`assistant_axis.gapgen.rubric_versions` holds here too: **a version names one
prompt text.**  ``versions.json`` beside the rubrics is append-only: for each prompt, every version
with the SHA-256 of its text, the date it was pinned and why.  The first rows are the draft numbers
in each file's status row.  A changed text with no new row is a mismatch, and a paid run refuses
to start until the text is pinned with ``data_analysis/gap_generation/rubric_pins.py bump NAME
--why TEXT``.

The M3 overlap rubrics (2026-10-03) live in the same directory, in the same file format, and are
pinned in the same ``versions.json`` (:data:`OVERLAP_FILES`): concept similarity (rubric A) and
co-occurrence (rubric B), first pinned as version 2, the draft Roger signed off; and since 2026-10-04
the three arms of the overlap rubric arms experiment (rubrics C, D and E, variants of A) and its round 2
(A2, C2, D2 and E2, the round-1 rubrics with their 2 and 3 lines redrafted), first pinned as version 1.
They are not split
prompts: :data:`NAMES` and :func:`load_all` stay the split filter's eight (the split runner and its
records use them), while :data:`PINNED_NAMES` (both sets) is what the pins, :func:`mismatches` and
``rubric_pins.py`` cover.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Optional

from .paths import RUBRICS_DIR

#: Prompt name -> rubric file name.  The names are the ones the filter block's ``step_versions``
#: and ``prompt_sha256`` use.
FILES: dict[str, str] = {
    "sense": "step1_sense.md",
    "established": "check_established.md",
    "vague": "check_vague.md",
    "kind": "step2_kind.md",
    "same_sense": "check_same_sense.md",
    "gloss": "gloss.md",
    "alignment": "alignment.md",
    "descriptors": "descriptors.md",
}
NAMES: tuple[str, ...] = tuple(FILES)
#: The M3 overlap call's rubrics: A and B (m3_overlap_rubric_draft.md draft 2, signed off 2026-10-03),
#: and the three arms of the overlap rubric arms experiment (coding_plan_overlap_arms.md, 2026-10-04),
#: variants of A: C six rungs, D relation first, E Roger's line 3; first pinned as version 1.  Round 2
#: of that experiment (same day, "Round 2"): A2, C2, D2 and E2, each a round-1 rubric with its 2 and 3
#: lines redrafted around the one-way implication test; first pinned as version 1.
OVERLAP_FILES: dict[str, str] = {
    "overlap_concept": "overlap_concept.md",
    "overlap_cooccurrence": "overlap_cooccurrence.md",
    "overlap_six": "overlap_six.md",
    "overlap_relation": "overlap_relation.md",
    "overlap_scope": "overlap_scope.md",
    "overlap_concept_implies": "overlap_concept_implies.md",
    "overlap_six_implies": "overlap_six_implies.md",
    "overlap_relation_implies": "overlap_relation_implies.md",
    "overlap_scope_implies": "overlap_scope_implies.md",
}
OVERLAP_NAMES: tuple[str, ...] = tuple(OVERLAP_FILES)
#: Every prompt file pinned in ``versions.json``.
PINNED_FILES: dict[str, str] = {**FILES, **OVERLAP_FILES}
PINNED_NAMES: tuple[str, ...] = tuple(PINNED_FILES)
VERSIONS_NAME = "versions.json"

#: The same expression the probe scripts used (probe_single/probe.py and the rest).
_BLOCK_RE = re.compile(r"## The prompt\n\n````text\n(.*?)\n````", re.S)


class RubricFileError(ValueError):
    """A rubric file is missing or does not hold exactly one prompt block."""


def rubric_path(name: str, rubrics_dir: Optional[Path] = None) -> Path:
    if name not in PINNED_FILES:
        raise KeyError(f"unknown rubric prompt {name!r}; known: {', '.join(PINNED_NAMES)}")
    return Path(rubrics_dir or RUBRICS_DIR) / PINNED_FILES[name]


def load_prompt(name: str, rubrics_dir: Optional[Path] = None) -> str:
    """The text inside the fenced block of the rubric file for ``name``, byte for byte."""
    p = rubric_path(name, rubrics_dir)
    if not p.exists():
        raise RubricFileError(f"{p}: rubric file missing")
    blocks = _BLOCK_RE.findall(p.read_text(encoding="utf-8"))
    if len(blocks) != 1:
        raise RubricFileError(f"{p}: expected one '## The prompt' fenced block, found {len(blocks)}")
    return blocks[0]


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_all(rubrics_dir: Optional[Path] = None) -> dict[str, str]:
    """The split filter's eight prompts (not the overlap rubrics)."""
    return {n: load_prompt(n, rubrics_dir) for n in NAMES}


def versions_path(rubrics_dir: Optional[Path] = None) -> Path:
    return Path(rubrics_dir or RUBRICS_DIR) / VERSIONS_NAME


def read_versions(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"prompts": {name: [{"version", "sha256", "pinned_at", "why"}, ...]}}``; empty when absent."""
    p = versions_path(rubrics_dir)
    if not p.exists():
        return {"prompts": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def current_versions(rubrics_dir: Optional[Path] = None, names: Optional[tuple] = NAMES
                     ) -> dict[str, tuple[int, str]]:
    """``{name: (latest pinned version, its sha256)}`` from ``versions.json``, for ``names`` (default:
    the split filter's eight, which is what the split runner stamps as its ``step_versions``; pass
    :data:`PINNED_NAMES` for every pinned prompt, :data:`OVERLAP_NAMES` for the overlap rubrics)."""
    out = {}
    want = set(names) if names is not None else None
    for name, rows in (read_versions(rubrics_dir).get("prompts") or {}).items():
        if rows and (want is None or name in want):
            last = max(rows, key=lambda r: int(r["version"]))
            out[name] = (int(last["version"]), str(last["sha256"]))
    return out


def mismatches(rubrics_dir: Optional[Path] = None) -> list[str]:
    """Human-readable problems; empty when every prompt's text on disk (the split prompts and the
    overlap rubrics) is the text its latest pinned version names."""
    out = []
    pinned = current_versions(rubrics_dir, PINNED_NAMES)
    for name in PINNED_NAMES:
        try:
            sha = sha256(load_prompt(name, rubrics_dir))
        except RubricFileError as exc:
            out.append(f"{name}: {exc}")
            continue
        if name not in pinned:
            out.append(f"{name}: no version pinned in {VERSIONS_NAME} (sha {sha[:12]}...)")
        elif pinned[name][1] != sha:
            out.append(f"{name}: text changed (sha {sha[:12]}...) but version {pinned[name][0]} is pinned to "
                       f"{pinned[name][1][:12]}...: pin it with rubric_pins.py bump {name} --why '...'")
    return out


def bump_command(problems: list[str]) -> str:
    """The ``rubric_pins.py bump`` commands that would pin the changed texts."""
    names = [p.split(":", 1)[0] for p in problems if p.split(":", 1)[0] in PINNED_FILES]
    return "\n".join(f"uv run python data_analysis/gap_generation/rubric_pins.py bump {n} --why '<what changed>'"
                     for n in names)


def bump(name: str, why: str, *, now: str, rubrics_dir: Optional[Path] = None,
         version: Optional[int] = None, revert_to: Optional[int] = None) -> dict:
    """Append a row for the text on disk: the next version (or ``version``, for the first row of a
    prompt), its sha256, ``now`` and ``why``.  Refuses when the text is already the latest pin, or
    when ``why`` is empty.  A text an earlier version already names is refused too, unless
    ``revert_to`` names that version: the revert is then pinned as the next version with
    ``"same_text_as": revert_to``, so version numbers keep rising and a record stamped with the new
    one can be traced to the earlier text.  Returns the new row."""
    if not why or not why.strip():
        raise ValueError("--why is required: say what changed in the text")
    sha = sha256(load_prompt(name, rubrics_dir))
    data = read_versions(rubrics_dir)
    rows = data.setdefault("prompts", {}).setdefault(name, [])
    extra: dict = {}
    if rows:
        last = max(rows, key=lambda r: int(r["version"]))
        if last["sha256"] == sha:
            raise ValueError(f"{name}: the text on disk is already version {last['version']}")
        earlier = [int(r["version"]) for r in rows if r["sha256"] == sha]
        if revert_to is not None:
            if int(revert_to) not in earlier:
                raise ValueError(f"{name}: the text on disk is not version {revert_to}'s text"
                                 + (f" (it is version {earlier[0]}'s)" if earlier else ""))
            extra["same_text_as"] = int(revert_to)
        elif earlier:
            raise ValueError(f"{name}: the text on disk is version {earlier[0]}'s; to go back to it, pin it "
                             f"as a new version with --revert-to {earlier[0]}")
        new_v = int(last["version"]) + 1
        if version is not None and int(version) != new_v:
            raise ValueError(f"{name}: next version is {new_v}, not {version}")
    else:
        if version is None:
            raise ValueError(f"{name}: first pin needs an explicit version (the draft number)")
        if revert_to is not None:
            raise ValueError(f"{name}: nothing is pinned yet to revert to")
        new_v = int(version)
    row = {"version": new_v, "sha256": sha, "pinned_at": now, "why": why.strip(), **extra}
    rows.append(row)
    ordered = {"_about": data.get("_about") or ABOUT, "prompts": {n: data["prompts"][n] for n in PINNED_NAMES
                                                                  if n in data["prompts"]}}
    versions_path(rubrics_dir).write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
                                          encoding="utf-8")
    return row


ABOUT = ("Append-only.  For each split-filter prompt and each M3 overlap rubric, every version and the SHA-256 "
         "of its text (the fenced block of its rubric file).  A version names one text.  Add a row with "
         "data_analysis/gap_generation/rubric_pins.py bump NAME --why TEXT; never edit a row.")
