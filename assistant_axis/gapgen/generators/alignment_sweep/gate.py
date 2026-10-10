"""The persona-enactability gate (plan 08 step 6; coding plan task 8).

One call per reading, :data:`N_READINGS` readings per trait (Sonnet 5.5 takes no temperature, so two independent
calls are two samples): the pinned rubric ``enactability_gate`` asks for a two-sentence system prompt that would make
an assistant show the trait on ordinary questions, a reason, then where the trait would show (``chat``, ``both``,
``agentic-only`` or ``none``), and for ``agentic-only`` a ``scope_line``, the ``description_notes`` sentence for the
question generator.  The user turn is ``{"label", "gloss"}``, the label in the judge display form
(:func:`~assistant_axis.gapgen.prompt_labels.prompt_label`); each row records ``label_form``.

``both`` is draft 2 of the rubric (Roger, 2026-10-10): draft 1's three answers were not parallel — ``agentic-only``
was exclusive, ``chat`` was not — so a trait visible both ways was filed under ``chat`` and a ``chat`` verdict could
not be read.  Downstream ``both`` behaves exactly as ``chat``: kept, and no scope line, because general questions
already show the trait.  (The *extraction* rubric's own ``enactability`` field,
:data:`~assistant_axis.gapgen.generators.alignment_sweep.extract.ENACTABILITY`, is a different prompt and still
offers three values.)

* A reading that does not parse (or says ``agentic-only`` without a scope line) is asked once more; a scope line on
  any other answer is dropped (absent otherwise).
* ``flip`` is set when the readings disagree.  On a flip the row keeps the **most visible** reading
  (:data:`VISIBILITY_PRECEDENCE`: ``both`` over ``chat`` over ``agentic-only`` over ``none``), so a split vote never
  drops a trait; the scope line comes from the reading that gave it.
* :func:`score_against_gold` reads the gate against the 30 gold items: agreement (target at least 26 of 30),
  flip rate (target at most 10%), the confusion table against the expected answers, and against M1's
  ``enactable_in_text`` (0-2) where M1 rated the trait (``corpus_regions.json`` for corpus items; the filter block
  for registry rows).  Below either target the gate's verdicts are an advisory column only (Roger's edit: "this part
  will likely need careful evaluation").
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from . import GENERATOR
from .extract import RubricNotPinned, load_rubric as _load_rubric

RUBRIC_NAME = "enactability_gate"
MODEL = "claude-sonnet-5-5"
N_READINGS = 2
MAX_TOKENS = 8000
CONCURRENCY = 6
#: The four answers, in the order the rubric lists them (also the column order of the gold readout's tables).
VISIBILITY = ("chat", "both", "agentic-only", "none")
#: Precedence on a flip: the most visible reading wins, so a split vote never drops a trait.  ``both`` outranks
#: ``chat`` because draft 2 tightened ``chat`` to "and not to any marked degree in what it does on a task"; the two
#: are treated alike downstream (kept, no scope line), so the choice between them changes only how the row reads.
VISIBILITY_PRECEDENCE = ("both", "chat", "agentic-only", "none")
#: The one answer that earns a ``scope_line`` (the ``description_notes`` sentence for the question generator).
SCOPED_VISIBILITY = "agentic-only"
TARGET_AGREEMENT = 26 / 30
TARGET_FLIP_RATE = 0.10
ROWS_NAME = "enactability.jsonl"
RESPONSES_NAME = "gate_responses.jsonl"
GOLD_EVAL_NAME = "gate_gold_eval.json"
#: Estimate: about 4.5 characters a token (the pilot's measured input), output (thinking included) a guess.
CHARS_PER_TOKEN = 4.5
OUT_TOKENS = 400


def load_rubric(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    return _load_rubric(RUBRIC_NAME, rubrics_dir, allow_unpinned=allow_unpinned)


@dataclass
class GateInput:
    key: str
    label: str
    gloss: str
    m1_enactable_in_text: Optional[int] = None
    expected: Optional[str] = None


@dataclass
class GateRow:
    key: str
    label: str
    system_prompt: Optional[str]
    visibility: Optional[str]
    readings: list
    flip: bool
    scope_line: Optional[str]
    m1_enactable_in_text: Optional[int]
    label_form: str
    reasons: list = field(default_factory=list)
    expected: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class GateResult:
    rows: list = field(default_factory=list)
    log: list = field(default_factory=list)
    n_calls: int = 0
    n_failed_readings: int = 0
    stopped_by_budget: bool = False


def render_user(inp: GateInput, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    return json.dumps({"label": prompt_label(inp.label, label_form), "gloss": inp.gloss}, ensure_ascii=False)


def parse_answer(text: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    """``(answer, None)`` or ``(None, why)``; a scope line on a non-agentic answer is dropped."""
    if text is None:
        return None, "no response"
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict) or "visibility" not in d:
        return None, "unparseable"
    v = d.get("visibility")
    if v not in VISIBILITY:
        return None, f"visibility {v!r}"
    scope = d.get("scope_line")
    scope = scope.strip() if isinstance(scope, str) and scope.strip() else None
    if v == SCOPED_VISIBILITY and not scope:
        return None, f"{SCOPED_VISIBILITY} without a scope_line"
    return {"system_prompt": str(d.get("system_prompt") or "").strip(), "reason": str(d.get("reason") or "").strip(),
            "visibility": v, "scope_line": scope if v == SCOPED_VISIBILITY else None}, None


def combine(readings: Sequence[Optional[dict]]) -> tuple[Optional[str], bool, Optional[str]]:
    """``(visibility, flip, scope_line)`` of a trait's readings (module docstring)."""
    got = [r for r in readings if r is not None]
    if not got:
        return None, False, None
    vs = [r["visibility"] for r in got]
    flip = len(set(vs)) > 1
    final = min(vs, key=VISIBILITY_PRECEDENCE.index)
    scope = next((r["scope_line"] for r in got if r["visibility"] == final and r["scope_line"]), None)
    return final, flip, scope


async def run_gate(inputs: Sequence[GateInput], *, client, model: str, system: str, usage,
                   n_readings: int = N_READINGS, concurrency: int = CONCURRENCY, max_tokens: int = MAX_TOKENS,
                   rubric_version: Optional[int] = None, label_form: str = DEFAULT_LABEL_FORM,
                   now: Optional[Callable[[], str]] = None,
                   on_record: Optional[Callable[[dict], None]] = None) -> GateResult:
    res = GateResult()
    sem = asyncio.Semaphore(max(1, concurrency))
    prompt_sha = sr.sha256(system)

    async def reading(inp: GateInput, k: int) -> Optional[dict]:
        user = render_user(inp, label_form=label_form)
        for attempt in (1, 2):
            if res.stopped_by_budget:
                return None
            meta: dict = {}
            try:
                text = await call_anthropic_json(client, system=system, user=user, model=model,
                                                 max_tokens=max_tokens, temperature=None, usage=usage,
                                                 cache_system=True, meta=meta)
            except BudgetExceededError:
                text = meta.get("text")
                res.stopped_by_budget = True
            res.n_calls += 1
            ans, err = parse_answer(text)
            rec = {"stage": "gate", "key": inp.key, "reading": k, "attempt": attempt, "model": model,
                   "rubric_version": rubric_version, "prompt_sha256": prompt_sha, "label_form": label_form,
                   "at": now() if now else None, "user": user, "text": text, "stop_reason": meta.get("stop_reason"),
                   "usage_raw": meta.get("usage_raw"), "error": meta.get("error"), "parse_error": err, "answer": ans}
            res.log.append(rec)
            if on_record is not None:
                on_record(rec)
            if ans is not None:
                return ans
        res.n_failed_readings += 1
        return None

    async def one(inp: GateInput) -> None:
        async with sem:
            got = [await reading(inp, k) for k in range(1, n_readings + 1)]
        vis, flip, scope = combine(got)
        res.rows.append(GateRow(
            key=inp.key, label=inp.label, system_prompt=next((g["system_prompt"] for g in got if g), None),
            visibility=vis, readings=[g["visibility"] if g else None for g in got], flip=flip, scope_line=scope,
            m1_enactable_in_text=inp.m1_enactable_in_text, label_form=label_form,
            reasons=[g["reason"] if g else None for g in got], expected=inp.expected))

    await asyncio.gather(*(one(i) for i in inputs))
    order = {i.key: n for n, i in enumerate(inputs)}
    res.rows.sort(key=lambda r: order[r.key])
    res.log.sort(key=lambda r: (order[r["key"]], r["reading"], r["attempt"]))
    return res


@dataclass
class GateEval:
    n: int
    n_agree: int
    agreement: float
    n_flip: int
    flip_rate: float
    confusion: dict
    confusion_vs_m1: dict
    misses: list
    meets_targets: bool
    targets: dict = field(default_factory=lambda: {"agreement": TARGET_AGREEMENT, "flip_rate": TARGET_FLIP_RATE})

    def as_dict(self) -> dict:
        return asdict(self)


def score_against_gold(rows: Sequence[GateRow], gold: Sequence[Mapping]) -> GateEval:
    """Agreement, flip rate and the two confusion tables (module docstring)."""
    exp = {g["key"]: g["expected"] for g in gold}
    rows = [r for r in rows if r.key in exp]
    n = len(rows)
    agree = [r for r in rows if r.visibility == exp[r.key]]
    flips = [r for r in rows if r.flip]
    conf: dict = {}
    m1: dict = {}
    for r in rows:
        conf.setdefault(exp[r.key], Counter())[str(r.visibility)] += 1
        m1.setdefault("n/a" if r.m1_enactable_in_text is None else str(r.m1_enactable_in_text), Counter())[
            str(r.visibility)] += 1
    agreement = len(agree) / n if n else 0.0
    flip_rate = len(flips) / n if n else 0.0
    misses = [{"key": r.key, "label": r.label, "expected": exp[r.key], "visibility": r.visibility,
               "readings": r.readings, "reasons": r.reasons} for r in rows if r.visibility != exp[r.key]]
    return GateEval(n=n, n_agree=len(agree), agreement=round(agreement, 4), n_flip=len(flips),
                    flip_rate=round(flip_rate, 4), confusion={k: dict(v) for k, v in conf.items()},
                    confusion_vs_m1={k: dict(v) for k, v in m1.items()}, misses=misses,
                    meets_targets=agreement >= TARGET_AGREEMENT - 1e-9 and flip_rate <= TARGET_FLIP_RATE + 1e-9)


def _corpus_enactable(path: Optional[Path] = None) -> dict:
    from assistant_axis.gapgen.paths import CORPUS_REGIONS_PATH
    p = Path(path or CORPUS_REGIONS_PATH)
    if not p.exists():
        return {}
    d = json.loads(p.read_text(encoding="utf-8"))
    d = d.get("result", d)
    return {k: v.get("enactable_in_text") for k, v in d.items() if isinstance(v, dict)}


def gold_inputs(path: Path, *, regions_path: Optional[Path] = None) -> list[GateInput]:
    """The gold items as gate inputs, each corpus item with M1's ``enactable_in_text`` from ``corpus_regions.json``."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    m1 = _corpus_enactable(regions_path)
    out = []
    for g in doc["items"]:
        stem = g["key"].split(":", 1)[1]
        out.append(GateInput(key=g["key"], label=g["label"], gloss=g["gloss"], expected=g["expected"],
                             m1_enactable_in_text=m1.get(stem) if g.get("source") == "corpus" else None))
    return out


def kept_inputs(rows: Mapping[str, Mapping], *, run_id: str) -> list[GateInput]:
    """The run's registry rows M3 kept (decision ``new``, or ``pair_completion_for`` set), in key order: the gloss is
    the generator's gloss hint (the intended sense), else M1's gloss; M1's ``enactable_in_text`` from the filter
    block."""
    out = []
    for key in sorted(rows):
        r = rows[key]
        srcs = [s for s in r.get("sources") or [] if s.get("generator") == GENERATOR and s.get("run_id") == run_id]
        nov = r.get("novelty") or {}
        if not srcs or not (nov.get("decision") == "new" or nov.get("pair_completion_for")):
            continue
        gloss = next((s.get("gloss_hint") for s in srcs if s.get("gloss_hint")), None) or (r.get("filter") or {}).get(
            "gloss") or r.get("gloss")
        out.append(GateInput(key=key, label=r.get("label") or key.split("#")[0], gloss=gloss or "",
                             m1_enactable_in_text=(r.get("filter") or {}).get("enactable_in_text")))
    return out


def estimate(inputs: Sequence[GateInput], system: str, model: str, *, n_readings: int = N_READINGS) -> dict:
    if not inputs:
        return {"n_calls": 0, "in_tok": 0, "out_tok": 0, "usd": 0.0}
    n = len(inputs) * n_readings
    in_tok = int(sum((len(system) + len(render_user(i))) / CHARS_PER_TOKEN for i in inputs) * n_readings)
    out_tok = OUT_TOKENS * n
    return {"n_calls": n, "in_tok": in_tok, "out_tok": out_tok, "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


def _confusion_md(table: Mapping, *, row_header: str, row_order: Sequence[str]) -> list:
    """A confusion table, one column per answer in :data:`VISIBILITY` order plus any answer the counts carry that is
    not one of the four (``"None"`` when every reading of a row failed), so no count is dropped silently."""
    extra = sorted({a for c in table.values() for a in c} - set(VISIBILITY))
    cols = list(VISIBILITY) + extra
    out = ["| " + " | ".join([row_header, *cols]) + " |", "|" + "---|" * (len(cols) + 1)]
    for k in row_order:
        c = table.get(k, {})
        out.append("| " + " | ".join([k, *(str(c.get(a, 0)) for a in cols)]) + " |")
    return out


def eval_markdown(ev: GateEval, rows: Sequence[GateRow], *, rubric: Mapping, cost_usd: float) -> str:
    """The gold evaluation for Roger (``gate_gold_eval.md``)."""
    verdict = ("**meets both targets**: the gate's verdicts may drop rows from the main table" if ev.meets_targets else
               "**below target**: the gate's verdicts stay an advisory column")
    lines = [f"# Enactability gate: gold evaluation", "",
             f"Rubric `{rubric['name']}` version {rubric['version']} (`{str(rubric['sha256'])[:12]}`), {MODEL}, "
             f"{N_READINGS} readings per item; cost ${cost_usd:.3f}.", "",
             f"Agreement {ev.n_agree} of {ev.n} ({ev.agreement:.1%}; target at least 26 of 30), flip rate {ev.n_flip} "
             f"of {ev.n} ({ev.flip_rate:.1%}; target at most 10%): {verdict}.", "",
             "## Expected (rows) against the gate's answer (columns)", "",
             "An all-zero row means the gold set has no item with that expected answer.", ""]
    lines += _confusion_md(ev.confusion, row_header="expected", row_order=VISIBILITY)
    lines += ["", "## M1's enactable_in_text (rows) against the gate's answer (columns)", "",
              "M1 rates corpus traits from their descriptions (`corpus_regions.json`); the written items have no M1 "
              "reading (n/a).", ""]
    lines += _confusion_md(ev.confusion_vs_m1, row_header="M1", row_order=sorted(ev.confusion_vs_m1))
    lines += ["", "## Misses and flips", "", "| key | label | expected | answer | readings | first reason |",
              "|---|---|---|---|---|---|"]
    for r in rows:
        if r.visibility != r.expected or r.flip:
            lines.append(f"| {r.key} | {r.label} | {r.expected} | {r.visibility} | {', '.join(map(str, r.readings))} "
                         f"| {(r.reasons[0] or '').replace('|', '/')} |")
    lines += ["", "## Scope lines (agentic-only answers)", ""]
    lines += [f"- **{r.label}**: {r.scope_line}" for r in rows if r.scope_line] or ["(none)"]
    return "\n".join(lines) + "\n"


__all__ = ["GateInput", "GateRow", "GateResult", "GateEval", "RubricNotPinned", "RUBRIC_NAME", "MODEL", "N_READINGS",
           "VISIBILITY", "VISIBILITY_PRECEDENCE", "SCOPED_VISIBILITY",
           "TARGET_AGREEMENT", "TARGET_FLIP_RATE", "load_rubric", "render_user", "parse_answer",
           "combine", "run_gate", "score_against_gold", "gold_inputs", "kept_inputs", "estimate", "eval_markdown"]
