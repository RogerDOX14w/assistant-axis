"""The physical pass: M3, the review graph and promotion for rows on the ``physical`` holding list.

Roger, 2026-10-09 (QUESTIONS 1): "On the physical queue, I think we handle promotion normally, and if promoted they
get the physical tag.  I suspect the proportion of them promoted may be small, so probably worth doing this as a
separate pass, but I think the process and tooling is the same."

M1 (the split filter) tags a word ``physical`` when its accepted reading is a lasting bodily feature, and stops there:
the row gets verdict ``tagged``, outcome ``physical`` and ``holding: "physical"``, but no gloss and no alignment score,
because the split runner writes those only for outcome ``trait`` (wave 4 and 6).  M3 needs both (the gloss is
embedded, retrieved on and read by the relation and overlap calls; the alignment score sets the cut-off).  So the
pass begins with a **gloss stage**: M1's own gloss call (``gloss.md`` as pinned) on the row's accepted reading
(``filter.judged_sense``), then M1's alignment call (``alignment.md`` as pinned) on that gloss, on M1's first model
with M1's request settings, one item per call, a failed answer retried once.  The descriptors call is not run: its
rubric lists the seven trait regions and none for a bodily feature (``split.SPLIT_REGIONS``), so ``region`` stays
null.  The result is written on the registry row as its own block, :data:`BLOCK` (``physical_gloss``), beside the
untouched ``filter`` block, in the manner of the states pass's ``states_pass`` block; the row's own ``gloss`` stays
null.  Everything after the stage is M3 as for trait rows (``novelty_score.py score --holding physical``).

The three steps (``coding_plan_review.md``, "Physical pass"):

1. ``novelty_score.py score --holding physical --batch-id <B> (--unscored | --run G/R | --keys K ...)``: the gloss
   stage for rows without a block, then M3 against the whole corpus (the physical track included); each block and
   the run's ``run.json`` and ``summary.json`` carry ``"pass": "physical"``.  One batch id per pass.
2. ``review_graph.py build --batch-id <R> --from-batches <B>``: R1 reads the physical rows of a physical batch
   (:func:`assistant_axis.gapgen.review_graph.pair_candidate`); their nodes carry ``outcome: "physical"``.
3. ``review_app.py serve --batch-id <R>``, then ``apply``: a promoted physical row goes through
   :func:`assistant_axis.gapgen.promote.promote` with ``allow_physical``, and its queue entry carries the tag
   ``physical`` and the physical track's section (:func:`section_for`).  ``gap_registry.py promote --keys`` promotes
   one by name the same way; ``promote --status accepted`` (the bulk path) still refuses it.
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

#: The holding list this pass reads, and the name the pass goes by in blocks and ``run.json``.
HOLDING = "physical"
PASS_NAME = "physical"
#: The registry field holding the gloss stage's answers for a row.
BLOCK = "physical_gloss"
#: The physical track's section in ``data/seed_queue.json`` (chunk 6, commit 5026ca2: the 26 traits tagged
#: ``physical``, among them ``blond``).  :func:`section_for` reads it from the queue; this is the fallback, and the
#: tests check that the real queue's physical entries carry it.
SECTION = "Physical-attribute traits: a separate research track (decided 2026-09-08)"
#: M1's first model (``split_runner.DEFAULT_MODEL``, Haiku 5.5 from 2026-10-08); checked equal by the tests.
MODEL = "claude-haiku-5-5"
#: The gloss stage's steps, in order; each is M1's call of the same name.
STEPS = ("gloss", "alignment")
STAGE = "physical_gloss"
#: The gloss stage's files in an M3 run directory.
RESPONSES_NAME = "physical_gloss_responses.jsonl"
RESULTS_NAME = "physical_gloss.jsonl"
DEFAULT_CONCURRENCY = 4


# --------------------------------------------------------------------------- reading a row

def is_physical(row: Mapping) -> bool:
    return row.get("holding") == HOLDING


def accepted_reading(row: Mapping) -> Optional[str]:
    """The reading M1 accepted (what its gloss call would have been given): ``filter.judged_sense``, else the
    sense block's reading at ``accepted_reading``."""
    f = row.get("filter") or {}
    r = f.get("judged_sense")
    if isinstance(r, str) and r.strip():
        return r.strip()
    acc = f.get("accepted_reading")
    rs = (f.get("sense") or {}).get("readings") or []
    if isinstance(acc, int) and 1 <= acc <= len(rs):
        r = (rs[acc - 1] or {}).get("reading")
        if isinstance(r, str) and r.strip():
            return r.strip()
    return None


def gloss_of(row: Mapping) -> Optional[str]:
    """The row's gloss: its own (M1's, for a trait row), else the gloss stage's."""
    g = row.get("gloss")
    if not (isinstance(g, str) and g.strip()):
        g = (row.get(BLOCK) or {}).get("gloss")
    return g.strip() if isinstance(g, str) and g.strip() else None


def alignment_of(row: Mapping) -> Optional[int]:
    a = (row.get(BLOCK) or {}).get("alignment")
    return a if isinstance(a, int) and not isinstance(a, bool) else None


def needs_gloss(row: Mapping) -> bool:
    return is_physical(row) and gloss_of(row) is None


def candidate_from_row(row: Mapping):
    """``(M3Candidate, None)`` for a row on the physical list with a gloss (its own or the gloss stage's), else
    ``(None, why)``: ``not_filtered``, ``not_on_physical_list``, ``no_gloss``.  The alignment score is the gloss
    stage's (None when its call failed: the near-alignment cut-off, as for a trait row), the region null."""
    from .novelty_runner import M3Candidate
    if not row.get("filter"):
        return None, "not_filtered"
    if not is_physical(row):
        return None, f"not_on_{HOLDING}_list"
    g = gloss_of(row)
    if g is None:
        return None, "no_gloss"
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    return M3Candidate(key=row["key"], stem=row["stem"], label=row["label"], gloss=g, alignment_score=alignment_of(row),
                       region=None, generators=gens), None


def provisional_candidate(row: Mapping):
    """A stand-in for a row the gloss stage has still to gloss, for the run's plan and estimate only (its gloss is
    the accepted reading, never sent): it is replaced by :func:`candidate_from_row` after the stage."""
    from .novelty_runner import M3Candidate
    gens = list(dict.fromkeys(s.get("generator") for s in row.get("sources") or [] if s.get("generator")))
    return M3Candidate(key=row["key"], stem=row["stem"], label=row["label"],
                       gloss=f"This means {accepted_reading(row) or row['label']}.", alignment_score=None, region=None,
                       generators=gens)


# --------------------------------------------------------------------------- the seed queue

def section_for(queue: Mapping) -> str:
    """The physical track's section: the commonest ``section`` among the queue's entries tagged ``physical``,
    else :data:`SECTION`."""
    c = Counter(e.get("section") for e in queue.get("entries") or []
                if HOLDING in (e.get("tags") or []) and e.get("section"))
    return c.most_common(1)[0][0] if c else SECTION


def queue_entry_extras(entry: dict, rec: Mapping, queue: Mapping, *, section: Optional[str] = None) -> dict:
    """A promoted physical row's queue entry (``promote.queue_entry_from_record``'s), made a physical-track entry
    in place: the tag ``physical`` (merged with the others), the physical track's section unless ``section`` is
    given, the gloss stage's gloss as ``description_draft`` when the row has none of its own, a note saying how it
    came, and ``gap_gen.holding``."""
    entry["tags"] = list(dict.fromkeys(list(entry.get("tags") or []) + [HOLDING]))
    entry["section"] = section or section_for(queue)
    if not entry.get("description_draft"):
        entry["description_draft"] = gloss_of(rec)
    nv = rec.get("novelty") or {}
    via = f" after the physical pass {nv['run_id']}" if nv.get("pass") == PASS_NAME and nv.get("run_id") else ""
    note = f"physical track: on the physical holding list, promoted by name{via}"
    entry["description_notes"] = " | ".join(x for x in (note, entry.get("description_notes")) if x)
    entry.setdefault("gap_gen", {})["holding"] = HOLDING
    return entry


# --------------------------------------------------------------------------- the gloss stage: requests

def max_tokens_for(step: str, model: str) -> int:
    """M1's ``max_tokens`` (``SplitRunner._max_tokens``): its thinking allowance on a model that refuses a
    temperature, else the first model's default."""
    from . import split_runner as SR
    from .llm import accepts_temperature
    if not accepts_temperature(model):
        return SR.MAX_TOKENS_THINKING
    return SR.MAX_TOKENS_FIRST.get(step, SR.MAX_TOKENS_FIRST_DEFAULT)


def request(step: str, *, label: str, text: str, model: str = MODEL, rubrics_dir: Optional[Path] = None) -> dict:
    """One call of the gloss stage, as M1 builds it (``SplitRunner._make``): ``gloss`` on the accepted reading,
    ``alignment`` on the gloss.  ``{"step", "model", "system", "user", "max_tokens", "temperature",
    "cache_system"}``."""
    from . import split
    from . import split_rubrics as sr
    from . import split_runner as SR
    if step not in STEPS:
        raise ValueError(f"the gloss stage sends {STEPS}, not {step!r}")
    system = sr.load_prompt(step, rubrics_dir)
    user = (split.payload("gloss", label=label, reading=text) if step == "gloss"
            else split.payload("alignment", label=label, description=text))
    return {"step": step, "model": model, "system": system, "user": user, "max_tokens": max_tokens_for(step, model),
            "temperature": SR.TEMPERATURE, "cache_system": SR.caches_system(system, model)}


def pins(rubrics_dir: Optional[Path] = None) -> dict:
    """``{"step_versions": {step: version}, "prompt_sha256": {step: sha}}`` of the two prompts as pinned; a
    ``ValueError`` when either text on disk is not its latest pin."""
    from . import split_rubrics as sr
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] in STEPS]
    if probs:
        raise ValueError("; ".join(probs))
    cur = sr.current_versions(rubrics_dir, STEPS)
    return {"step_versions": {s: cur[s][0] for s in STEPS},
            "prompt_sha256": {s: sr.sha256(sr.load_prompt(s, rubrics_dir)) for s in STEPS}}


def estimate(n_rows: int, *, model: str = MODEL):
    """The stage's estimate: one gloss and one alignment call a row, at M1's measured tokens for ``model``."""
    from . import split_runner as SR
    from .cost import Estimate
    est = Estimate()
    for step in STEPS:
        i, o = SR.tokens_for(step, model)
        est.add(f"physical gloss stage: M1's {step} call", model, n_rows, i, o)
    return est


def render(row: Mapping, *, model: str = MODEL, rubrics_dir: Optional[Path] = None) -> str:
    """The gloss request for ``row`` and the alignment request's form, as the model receives them (for the dry
    run; the alignment call's description is the gloss, not known before the call)."""
    p = pins(rubrics_dir)
    q = request("gloss", label=row["label"], text=accepted_reading(row) or "", model=model, rubrics_dir=rubrics_dir)
    head = {k: q[k] for k in ("model", "max_tokens", "temperature", "cache_system")}
    a = request("alignment", label=row["label"], text="<the gloss>", model=model, rubrics_dir=rubrics_dir)
    return (f"=== physical gloss stage, {row['key']}: gloss v{p['step_versions']['gloss']}, request settings "
            f"{json.dumps(head)} ===\n--- system ---\n{q['system']}\n--- user ---\n{q['user']}\n"
            f"=== then alignment v{p['step_versions']['alignment']} on the gloss ===\n--- user ---\n{a['user']}\n")


# --------------------------------------------------------------------------- the gloss stage: calls

def _block(row: Mapping, *, model: str, batch_id: str, pinned: Mapping, gloss: Optional[dict],
           alignment: Optional[dict], errors: Mapping[str, str]) -> dict:
    from .registry import utc_now
    g = (gloss or {}).get("gloss")
    b = {"gloss": g, "gloss_form_ok": (gloss or {}).get("form_ok") if g else None,
         "alignment": (alignment or {}).get("alignment"), "alignment_reason": (alignment or {}).get("reason"),
         "reading": accepted_reading(row), "model": model, "batch_id": batch_id,
         "step_versions": dict(pinned["step_versions"]), "prompt_sha256": dict(pinned["prompt_sha256"]), "at": utc_now()}
    if errors:
        b["errors"] = dict(errors)
    return b


async def gloss_rows(rows: Sequence[Mapping], *, client, usage, batch_id: str, records_path: Path,
                     on_block: Optional[Callable[[str, dict], None]] = None, model: str = MODEL,
                     concurrency: int = DEFAULT_CONCURRENCY, retry_delays: Optional[Sequence[float]] = None,
                     rubrics_dir: Optional[Path] = None) -> dict[str, dict]:
    """The gloss stage for ``rows``: per row, the gloss call on the accepted reading, then the alignment call on the
    gloss (each retried once, alone, when its answer fails validation, as M1 retries).  Every response is appended
    to ``records_path`` as it arrives, before it is parsed.  ``on_block(key, block)`` is called as each row
    finishes (the CLI writes the registry there), so a budget stop keeps what was paid for: the error propagates
    once the calls in flight are recorded, and a row stopped half way gets no block.  Returns ``{key: block}``; a
    row whose gloss failed gets ``gloss: None`` and ``errors``."""
    from . import split
    from .llm import RETRY_DELAYS_S, call_anthropic_json
    from .registry import utc_now
    from assistant_axis.judge_pricing import BudgetExceededError
    pinned = pins(rubrics_dir)
    delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)
    sem = asyncio.Semaphore(max(1, int(concurrency)))
    stop: list[BaseException] = []
    out: dict[str, dict] = {}
    Path(records_path).parent.mkdir(parents=True, exist_ok=True)

    def record(row, q, text, meta, *, retry: bool, err: Optional[str]) -> None:
        rec = {"batch_id": batch_id, "stage": STAGE, "step": q["step"], "model": q["model"], "key": row["key"],
               "label": row["label"], "user": q["user"], "prompt_sha256": pinned["prompt_sha256"][q["step"]],
               "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_error": err,
               "charged_as": q["model"] if meta.get("usage_raw") else None, "retry": retry, "at": utc_now()}
        with open(records_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def ask(row, step: str, text: str) -> tuple[Optional[dict], Optional[str]]:
        q = request(step, label=row["label"], text=text, model=model, rubrics_dir=rubrics_dir)
        err: Optional[str] = None
        for retry in (False, True):
            if stop:
                return None, "not sent (stopped)"
            meta: dict = {}
            async with sem:
                if stop:
                    return None, "not sent (stopped)"
                try:
                    t = await call_anthropic_json(client, system=q["system"], user=q["user"], model=q["model"],
                                                  max_tokens=q["max_tokens"], temperature=q["temperature"], usage=usage,
                                                  cache_system=q["cache_system"], retry_delays=delays, meta=meta)
                except BudgetExceededError as exc:
                    t = meta.get("text")
                    stop.append(exc)
            parsed, perr = split.parse(step, t, label=row["label"])
            if t is None and perr in (None, "empty response"):
                perr = f"no response: {meta.get('error')}"
            record(row, q, t, meta, retry=retry, err=perr)
            if perr is None:
                return parsed, None
            err = perr if err is None else f"{err}; retry: {perr}"
        return None, err

    async def one(row) -> None:
        reading = accepted_reading(row)
        if not reading:
            b = _block(row, model=model, batch_id=batch_id, pinned=pinned, gloss=None, alignment=None,
                       errors={"gloss": "no accepted reading"})
        else:
            g, gerr = await ask(row, "gloss", reading)
            if gerr == "not sent (stopped)" or (g is None and stop):
                return
            a, aerr = (None, None)
            if g is not None:
                a, aerr = await ask(row, "alignment", g["gloss"])
                if stop and a is None:
                    return
            errors = {k: v for k, v in (("gloss", gerr), ("alignment", aerr)) if v}
            b = _block(row, model=model, batch_id=batch_id, pinned=pinned, gloss=g, alignment=a, errors=errors)
        out[row["key"]] = b
        if on_block is not None:
            on_block(row["key"], b)

    await asyncio.gather(*(one(r) for r in rows))
    if stop:
        raise stop[0]
    return out


def run_gloss_rows(rows: Sequence[Mapping], **kw) -> dict[str, dict]:
    """:func:`gloss_rows` from synchronous code.  The client is closed inside the same event loop before it ends
    (an ``AsyncAnthropic`` left open is closed by the garbage collector after ``asyncio.run`` has closed the loop,
    which raised "Event loop is closed" at the end of the 2026-10-09 Allport physical pass)."""
    async def main() -> dict[str, dict]:
        try:
            return await gloss_rows(rows, **kw)
        finally:
            close = getattr(kw.get("client"), "close", None)
            if close is not None:
                res = close()
                if asyncio.iscoroutine(res):
                    await res
    return asyncio.run(main())


def stage_summary(blocks: Mapping[str, Mapping]) -> dict:
    """Counts for ``run.json``: rows glossed, rows whose gloss failed, rows whose alignment failed, by score."""
    ok = [b for b in blocks.values() if b.get("gloss")]
    return {"n_rows": len(blocks), "n_glossed": len(ok), "n_gloss_failed": len(blocks) - len(ok),
            "n_alignment_failed": sum(1 for b in ok if b.get("alignment") is None),
            "alignment": dict(sorted(Counter(str(b.get("alignment")) for b in ok).items())),
            "n_gloss_form_ok": sum(1 for b in ok if b.get("gloss_form_ok"))}


def result_line(row: Mapping, block: Mapping) -> dict:
    """One line of the run's :data:`RESULTS_NAME`: the row, its reading and the block."""
    return {"key": row["key"], "label": row["label"], "reading": accepted_reading(row), BLOCK: dict(block)}


__all__ = ["HOLDING", "PASS_NAME", "BLOCK", "SECTION", "MODEL", "STEPS", "is_physical", "accepted_reading", "gloss_of",
           "alignment_of", "needs_gloss", "candidate_from_row", "provisional_candidate", "section_for",
           "queue_entry_extras", "request", "pins", "estimate", "render", "gloss_rows", "run_gloss_rows",
           "stage_summary", "result_line"]

