"""The label probe: is each label known to a 32B model in the intended sense? (plan 08 step 7's "label known to a
32B model"; coding plan § 1.)

``qwen/qwen3-32b`` through OpenRouter, **pinned to DeepInfra (United States)** with ``allow_fallbacks: false``
(:data:`ALLOWED_PROVIDERS`; the hosted-models rule of CLAUDE.md: western hosts only, the host checked before the
first request, a response naming another host thrown away and counted).  Thinking is switched off two ways, as in
``opening_form_experiment.py``: ``reasoning: {"enabled": false}`` and Qwen's own `` /no_think`` at the end of the
user turn; a ``<think>`` block that comes back anyway is stripped.  No ``OPENROUTER_API_KEY``: the probe is
skipped, the readout says so, and the rank formula drops the factor.

The prompt (:data:`PROMPT`, version :data:`PROMPT_VERSION`; one label per call, shown in the judge display form)
asks for a one-sentence definition of the label as said of a person or an assistant, or ``known: false``.  A label
is **known** when the model gives a definition whose embedding (``text-embedding-3-large`` through the cache, the
dedup's model) is at cosine :data:`MIN_COS_TO_GLOSS` or more from the label's gloss: known, and in the intended
sense.  The floor is provisional (2026-10-10, first run); ``probe.json`` keeps every cosine so it can be re-read.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import extract_usage_openai

MODEL = "qwen/qwen3-32b"
OPENROUTER_URL = "https://openrouter.ai/api/v1"
#: The only host this probe may use, with its country (checked 2026-09-29 for opening_form_experiment.py).
ALLOWED_PROVIDERS: dict[str, str] = {"deepinfra": "United States"}
PROVIDER = "deepinfra"
NO_THINK_SUFFIX = " /no_think"
MAX_TOKENS = 160
TEMPERATURE = 0.0
CONCURRENCY = 8
MIN_COS_TO_GLOSS = 0.5
PROMPT_VERSION = 1
PROMPT = ("What does the expression '{label}' mean when it describes a person or an AI assistant? If you recognize "
          "it, give its usual meaning in one sentence. If you do not, say so. Answer with one JSON object and nothing "
          'else: {{"definition": "<one sentence>" or null, "known": true or false}}')
PROBE_NAME = "probe.json"
#: Estimate per call (the opening-form experiment's DeepInfra calls; tiny either way).
IN_TOKENS, OUT_TOKENS = 90, 45

_THINK = re.compile(r"<think>.*?</think>", re.S)


def prompt_sha256() -> str:
    return hashlib.sha256(PROMPT.encode("utf-8")).hexdigest()


@dataclass
class ProbeInput:
    label: str
    gloss: str


@dataclass
class ProbeRow:
    label: str
    definition: Optional[str] = None
    known_claimed: Optional[bool] = None
    cos_to_gloss: Optional[float] = None
    label_known: Optional[bool] = None
    provider: Optional[str] = None
    finish_reason: Optional[str] = None
    discarded: Optional[str] = None
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class ProbeResult:
    rows: dict = field(default_factory=dict)
    n_calls: int = 0
    n_discarded: int = 0
    n_errors: int = 0


def key_status(env_path: Optional[Path] = None) -> str:
    """``"ok"`` when an ``OPENROUTER_API_KEY`` loads (from the environment, or ``env_path`` read with dotenv), else
    the skip message.  The key itself is never read here."""
    if env_path is not None:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    return "ok" if os.getenv("OPENROUTER_API_KEY") else "skipped: no OPENROUTER_API_KEY loads"


def render_user(label: str, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    return PROMPT.format(label=prompt_label(label, label_form)) + NO_THINK_SUFFIX


def _parse(text: str) -> tuple[Optional[dict], Optional[str]]:
    blob = extract_json_blob(_THINK.sub("", text or "").strip())
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict) or "known" not in d:
        return None, "unparseable"
    definition = d.get("definition")
    definition = definition.strip() if isinstance(definition, str) and definition.strip() else None
    return {"known": bool(d.get("known")) and definition is not None, "definition": definition}, None


async def run_probe(inputs: Sequence[ProbeInput], *, client, usage, embedder=None, cache=None,
                    concurrency: int = CONCURRENCY, label_form: str = DEFAULT_LABEL_FORM) -> ProbeResult:
    """One call per label (module docstring); every response is charged, a discarded one too."""
    res = ProbeResult()
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(inp: ProbeInput) -> None:
        row = ProbeRow(label=inp.label)
        async with sem:
            try:
                r = await client.chat.completions.create(
                    model=MODEL, temperature=TEMPERATURE, max_tokens=MAX_TOKENS,
                    messages=[{"role": "user", "content": render_user(inp.label, label_form=label_form)}],
                    extra_body={"reasoning": {"enabled": False},
                                "provider": {"order": [PROVIDER], "allow_fallbacks": False}})
            except Exception as exc:  # noqa: BLE001 - recorded, the probe is advisory
                row.error = f"{type(exc).__name__}: {exc}"[:200]
                res.n_errors += 1
                res.rows[inp.label] = row
                return
        res.n_calls += 1
        usage.charge(MODEL, *extract_usage_openai(r))
        row.provider = getattr(r, "provider", None)
        try:
            choice = r.choices[0]
            row.finish_reason = getattr(choice, "finish_reason", None)
            text = choice.message.content or ""
        except (AttributeError, IndexError):
            text = ""
        if str(row.provider or "").lower() not in ALLOWED_PROVIDERS:
            row.discarded = f"host {row.provider} not allowed"
            res.n_discarded += 1
            res.rows[inp.label] = row
            return
        ans, err = _parse(text)
        if ans is None:
            row.error = err
            res.n_errors += 1
        else:
            row.definition, row.known_claimed = ans["definition"], ans["known"]
        res.rows[inp.label] = row

    await asyncio.gather(*(one(i) for i in inputs))
    # known in the intended sense: the definition near the gloss
    have = [i for i in inputs if res.rows[i.label].definition and res.rows[i.label].known_claimed]
    if have and embedder is not None:
        from assistant_axis.gapgen.embed import embed_texts
        E = embed_texts(embedder, [t for i in have for t in (res.rows[i.label].definition, i.gloss)], cache=cache,
                        usage=usage)
        for k, i in enumerate(have):
            row = res.rows[i.label]
            row.cos_to_gloss = round(float(np.dot(E[2 * k], E[2 * k + 1])), 4)
            row.label_known = row.cos_to_gloss >= MIN_COS_TO_GLOSS
    for i in inputs:
        row = res.rows[i.label]
        if row.discarded is None and row.error is None and row.label_known is None:
            row.label_known = False if row.known_claimed is False else row.label_known
    res.rows = {i.label: res.rows[i.label] for i in inputs}
    return res


def write_probe(res: Optional[ProbeResult], path: Path, *, status: str, inputs: Sequence = (),
                extra: Optional[dict] = None) -> Path:
    from assistant_axis import json_metadata
    payload = {"status": status, "model": MODEL, "host": dict(ALLOWED_PROVIDERS), "prompt_version": PROMPT_VERSION,
               "prompt_sha256": prompt_sha256(), "min_cos_to_gloss": MIN_COS_TO_GLOSS,
               "n_calls": res.n_calls if res else 0, "n_discarded": res.n_discarded if res else 0,
               "n_errors": res.n_errors if res else 0,
               "rows": [r.as_dict() for r in res.rows.values()] if res else [], **(extra or {})}
    env = json_metadata(payload, inputs=list(inputs), title="alignment sweep: Qwen label probe (DeepInfra, US)")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", Path(path))
    return Path(path)


def load_label_known(path: Path) -> dict[str, Optional[bool]]:
    """``{label: label_known}`` from a ``probe.json`` (empty for a skipped probe)."""
    p = Path(path)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    d = d.get("result", d)
    return {r["label"]: r.get("label_known") for r in d.get("rows") or []}


def estimate_usd(n: int) -> float:
    from assistant_axis.judge_pricing import cost_for_usage
    return round(cost_for_usage(MODEL, n * IN_TOKENS, n * OUT_TOKENS), 5)


__all__ = ["MODEL", "ALLOWED_PROVIDERS", "PROVIDER", "PROMPT", "PROMPT_VERSION", "MIN_COS_TO_GLOSS", "ProbeInput",
           "ProbeRow", "ProbeResult", "key_status", "render_user", "run_probe", "write_probe", "load_label_known",
           "estimate_usd", "prompt_sha256"]
