"""The corpus's regions and alignment scores from its own descriptions (``gap_registry.py corpus-regions
--from-descriptions``).

Roger, 2026-10-09 (QUESTIONS 3): "The corpus contains cases where the label is somewhat contrived and the
description picks out a less-obvious meaning of it, so glossing the label is unreliable.  This fundamentally differs
from the case of the gap-filling candidates, where we generate a word or short phrase first, then gloss its most
obvious interpretation as applied to a person.  So doing this from corpus descriptions rather than labels makes
sense."

Until then ``corpus_regions.json`` copied the region the trait-hood filter (M1) gave each corpus *label* when the
labels were run through it as if they were candidates (``corpus-regions --from-filter``): the filter glosses the bare
label and assigns the region from its own gloss.  This module sends M1's two last calls instead, the ``descriptors``
call (``rubrics/descriptors.md``: one of seven regions and ``enactable_in_text`` 0 to 2) and the ``alignment`` call
(``rubrics/alignment.md``: a score 0 to 3), as pinned and exactly as M1's wave 6 sends them
(:meth:`split_runner.SplitRunner._make`: the step's system prompt, ``split.payload(step, label=..., description=...)``,
M1's ``max_tokens``, temperature and caching), with the trait file's ``description`` standing where a candidate's
gloss stands and its ``positive_label`` as the label.  One item per call; the two calls of a trait are independent and
go out together; an answer that fails validation is retried once, alone, as M1 retries.  Candidates keep getting their
region from the filter: nothing here touches M1.

Selection (:func:`select`): ``all`` judges every trait; ``only_missing`` (after a corpus chunk) judges the traits with
no row, with a row that did not come from a description (a filter row or the null placeholder), with a row whose
description hash or label no longer matches the trait file, or whose earlier call failed.

A row (:func:`row`): ``label``, ``region``, ``enactable_in_text``, ``alignment_score``, ``alignment_relevant`` (the
filter's convention, :func:`split.alignment_relevant_of`: true for a score of 2 or 3), ``source: "description"``,
``description_sha256``, ``model``, ``rubric_versions``, ``reasons``, ``batch_id``, ``at``, and ``errors`` when a call
failed twice.  :func:`merge` adds ``previous_region``, ``previous_alignment_relevant`` and ``previous_source`` (where
the replaced row came from) to every row it replaces, so a run's changes can be read from the file.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

#: M1's first model (``split_runner.DEFAULT_MODEL``, Haiku 5.5 from 2026-10-08); checked equal by the tests.
MODEL = "claude-haiku-5-5"
#: The two calls, each M1's call of the same name.
STEPS = ("descriptors", "alignment")
SOURCE = "description"
STAGE = "corpus_descriptors"
MODES = ("all", "only_missing")
RESPONSES_NAME = "responses.jsonl"
DEFAULT_CONCURRENCY = 8


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- the corpus

def load_corpus(data_dir: Path) -> list[dict]:
    """Every trait file under ``<data_dir>/traits/instructions``: ``{"stem", "label", "description",
    "description_sha256"}`` sorted by stem; the label is the file's ``positive_label`` (its display form, which is
    what the filter was given for a corpus label)."""
    from assistant_axis.entity_id import display_form_name
    out = []
    for p in sorted((Path(data_dir) / "traits" / "instructions").glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        label = (d.get("positive_label") or "").strip() or display_form_name(p.stem)
        desc = d.get("description") if isinstance(d.get("description"), str) else ""
        out.append({"stem": p.stem, "label": label, "description": desc, "description_sha256": sha256_text(desc)})
    return out


def load_existing(path: Path) -> dict[str, dict]:
    """The ``result`` block of a ``corpus_regions.json`` (``{}`` when there is none)."""
    p = Path(path)
    if not p.exists():
        return {}
    obj = json.loads(p.read_text(encoding="utf-8"))
    res = obj.get("result", obj) if isinstance(obj, dict) else {}
    return {s: dict(v) for s, v in res.items() if isinstance(v, Mapping)}


def stale_reason(trait: Mapping, entry: Optional[Mapping]) -> Optional[str]:
    """Why ``only_missing`` judges ``trait`` again, or None when its row is current: ``absent`` (no row),
    ``placeholder`` (a row not from a description: the filter's, or the null entry), ``description_changed``,
    ``label_changed``, ``failed`` (a call of the earlier run failed twice)."""
    if entry is None:
        return "absent"
    if entry.get("source") != SOURCE:
        return "placeholder"
    if entry.get("description_sha256") != trait["description_sha256"]:
        return "description_changed"
    if entry.get("label") != trait["label"]:
        return "label_changed"
    if entry.get("errors") or entry.get("region") is None or entry.get("alignment_score") is None:
        return "failed"
    return None


def select(corpus: Sequence[Mapping], existing: Mapping[str, Mapping], *, mode: str) -> list[tuple[dict, str]]:
    """``[(trait, reason)]`` to judge, in corpus order: every trait (reason ``all``) or, for ``only_missing``, those
    :func:`stale_reason` names."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    out = []
    for t in corpus:
        why = "all" if mode == "all" else stale_reason(t, existing.get(t["stem"]))
        if why:
            out.append((dict(t), why))
    return out


# --------------------------------------------------------------------------- the requests (M1's)

def request(step: str, *, label: str, description: str, model: str = MODEL, rubrics_dir: Optional[Path] = None,
            label_form: Optional[str] = None) -> dict:
    """One call as M1's wave 6 builds it (``SplitRunner._make``), the description where the gloss goes:
    ``{"step", "model", "system", "user", "max_tokens", "temperature", "cache_system"}``.  ``label`` (the stored
    ``positive_label``) is shown in ``label_form`` (:mod:`assistant_axis.gapgen.prompt_labels`; default the judge
    display form: ``careless (HEXACO)`` -> ``careless (from HEXACO)``); the row keeps the stored label."""
    from . import split
    from . import split_rubrics as sr
    from . import split_runner as SR
    from .physical_pass import max_tokens_for
    from .prompt_labels import DEFAULT_LABEL_FORM
    if step not in STEPS:
        raise ValueError(f"the corpus pass sends {STEPS}, not {step!r}")
    system = sr.load_prompt(step, rubrics_dir)
    return {"step": step, "model": model, "system": system,
            "user": split.payload(step, label=label, description=description,
                                  label_form=label_form or DEFAULT_LABEL_FORM),
            "max_tokens": max_tokens_for(step, model), "temperature": SR.TEMPERATURE,
            "cache_system": SR.caches_system(system, model)}


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


def estimate(n_traits: int, *, model: str = MODEL):
    """One descriptors and one alignment call a trait, at M1's measured tokens for ``model``."""
    from . import split_runner as SR
    from .cost import Estimate
    est = Estimate()
    for step in STEPS:
        i, o = SR.tokens_for(step, model)
        est.add(f"corpus regions: M1's {step} call on the description", model, n_traits, i, o)
    return est


def render(trait: Mapping, *, model: str = MODEL, rubrics_dir: Optional[Path] = None,
           label_form: Optional[str] = None) -> str:
    """Both requests for ``trait`` as the model receives them (system prompt, user turn, settings)."""
    p = pins(rubrics_dir)
    parts = []
    for step in STEPS:
        q = request(step, label=trait["label"], description=trait["description"], model=model, rubrics_dir=rubrics_dir,
                    label_form=label_form)
        head = {k: q[k] for k in ("model", "max_tokens", "temperature", "cache_system")}
        parts.append(f"=== {step} v{p['step_versions'][step]} for {trait['stem']}, request settings {json.dumps(head)} "
                     f"===\n--- system ---\n{q['system']}\n--- user ---\n{q['user']}\n")
    return "".join(parts)


# --------------------------------------------------------------------------- rows

def row(trait: Mapping, *, descriptors: Optional[Mapping], alignment: Optional[Mapping], errors: Mapping[str, str],
        model: str, batch_id: str, pinned: Mapping) -> dict:
    from . import split
    from .registry import utc_now
    d, a = descriptors or {}, alignment or {}
    score = a.get("alignment")
    r = {"label": trait["label"], "region": d.get("region"), "enactable_in_text": d.get("enactable_in_text"),
         "alignment_score": score, "alignment_relevant": split.alignment_relevant_of(score), "source": SOURCE,
         "description_sha256": trait["description_sha256"], "model": model,
         "rubric_versions": dict(pinned["step_versions"]),
         "reasons": {"descriptors": d.get("reason"), "alignment": a.get("reason")}, "batch_id": batch_id,
         "at": utc_now()}
    if errors:
        r["errors"] = dict(errors)
    return r


def previous_fields(entry: Optional[Mapping]) -> dict:
    """What a replaced row said: ``previous_region``, ``previous_alignment_relevant`` and ``previous_source``
    (``"filter <batch>"`` for a row from ``--from-filter``, ``"description <batch>"`` for one from here, ``"none"``
    for the null entry); ``{}`` when there was no row."""
    if entry is None:
        return {}
    src, bid = entry.get("source"), entry.get("batch_id")
    source = f"{src} {bid}" if src else (f"filter {bid}" if bid else "none")
    return {"previous_region": entry.get("region"), "previous_alignment_relevant": entry.get("alignment_relevant"),
            "previous_source": source}


def null_entry(label: Optional[str]) -> dict:
    """A trait with no row yet (the shape ``--from-filter`` writes for a stem no run contains)."""
    return {"label": label, "region": None, "alignment_relevant": None, "verdict": None, "batch_id": None}


def merge(corpus: Sequence[Mapping], existing: Mapping[str, Mapping], judged: Mapping[str, Mapping]) -> dict:
    """The new ``result`` block, one entry per corpus trait in stem order: the judged row (with
    :func:`previous_fields` of the row it replaces), else the existing row unchanged, else :func:`null_entry`.
    Rows for stems the corpus no longer has are dropped."""
    out = {}
    for t in sorted(corpus, key=lambda x: x["stem"]):
        s = t["stem"]
        if s in judged:
            out[s] = {**judged[s], **previous_fields(existing.get(s))}
        elif s in existing:
            out[s] = dict(existing[s])
        else:
            out[s] = null_entry(t["label"])
    return out


def parse_rates(rows: Mapping[str, Mapping]) -> dict[str, dict]:
    """``{step: {"n", "ok"}}`` over the rows whose calls were sent (a trait with no description sends none)."""
    sent = [r for r in rows.values() if (r.get("errors") or {}).get("descriptors") != "no description"]
    return {step: {"n": len(sent), "ok": sum(1 for r in sent if step not in (r.get("errors") or {}))}
            for step in STEPS}


def region_counts(result: Mapping[str, Mapping]) -> dict[str, int]:
    c = Counter(str((v or {}).get("region")) for v in result.values())
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


def changes(before: Mapping[str, Mapping], after: Mapping[str, Mapping]) -> dict:
    """Counts of region changes between two ``result`` blocks over the stems of ``after``: ``changed`` (a region
    before and a different one after), ``same``, ``gained`` (none before), ``lost`` (none after)."""
    c = Counter()
    for s, a in after.items():
        old, new = (before.get(s) or {}).get("region"), (a or {}).get("region")
        c["same" if old == new and old is not None else "changed" if old and new else
          "gained" if new and not old else "lost" if old and not new else "neither"] += 1
    return {k: c[k] for k in ("changed", "same", "gained", "lost", "neither")}


# --------------------------------------------------------------------------- the calls

async def judge(traits: Sequence[Mapping], *, client, usage, batch_id: str, records_path: Path,
                on_row: Optional[Callable[[str, dict], None]] = None, model: str = MODEL,
                concurrency: Optional[int] = None, retry_delays: Optional[Sequence[float]] = None,
                rubrics_dir: Optional[Path] = None, label_form: Optional[str] = None) -> dict[str, dict]:
    """Both calls for each of ``traits`` (each retried once, alone, when its answer fails validation).  Every
    response is appended to ``records_path`` as it arrives, before it is parsed.  ``on_row(stem, row)`` is called
    as each trait finishes, so a budget stop keeps what was paid for: the error propagates once the calls in flight
    are recorded, and a trait stopped half way gets no row.  A trait with an empty description sends nothing and
    gets a row with ``errors``.  Returns ``{stem: row}``.  ``label_form``: how the label is shown (default the judge
    display form); the rows, their ``label`` and the selection keep the stored label."""
    from . import split
    from .llm import RETRY_DELAYS_S, call_anthropic_json
    from .prompt_labels import DEFAULT_LABEL_FORM, check_label_form, prompt_label
    from .registry import utc_now
    from assistant_axis.judge_pricing import BudgetExceededError
    form = check_label_form(label_form or DEFAULT_LABEL_FORM)
    pinned = pins(rubrics_dir)
    delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)
    sem = asyncio.Semaphore(max(1, int(concurrency or DEFAULT_CONCURRENCY)))
    stop: list[BaseException] = []
    out: dict[str, dict] = {}
    Path(records_path).parent.mkdir(parents=True, exist_ok=True)

    def record(t, q, text, meta, *, retry: bool, err: Optional[str]) -> None:
        rec = {"batch_id": batch_id, "stage": STAGE, "step": q["step"], "model": q["model"], "stem": t["stem"],
               "label": t["label"], "user": q["user"], "prompt_sha256": pinned["prompt_sha256"][q["step"]],
               "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_error": err,
               "charged_as": q["model"] if meta.get("usage_raw") else None, "retry": retry, "at": utc_now()}
        with open(records_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def ask(t, step: str) -> tuple[Optional[dict], Optional[str]]:
        q = request(step, label=t["label"], description=t["description"], model=model, rubrics_dir=rubrics_dir,
                    label_form=form)
        err: Optional[str] = None
        for retry in (False, True):
            if stop:
                return None, "not sent (stopped)"
            meta: dict = {}
            async with sem:
                if stop:
                    return None, "not sent (stopped)"
                try:
                    text = await call_anthropic_json(client, system=q["system"], user=q["user"], model=q["model"],
                                                     max_tokens=q["max_tokens"], temperature=q["temperature"],
                                                     usage=usage, cache_system=q["cache_system"],
                                                     retry_delays=delays, meta=meta)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    stop.append(exc)
            parsed, perr = split.parse(step, text, label=prompt_label(t["label"], form))
            if text is None and perr in (None, "empty response"):
                perr = f"no response: {meta.get('error')}"
            record(t, q, text, meta, retry=retry, err=perr)
            if perr is None:
                return parsed, None
            err = perr if err is None else f"{err}; retry: {perr}"
        return None, err

    async def one(t) -> None:
        if not (t.get("description") or "").strip():
            r = row(t, descriptors=None, alignment=None, model=model, batch_id=batch_id, pinned=pinned,
                    errors={s: "no description" for s in STEPS})
        else:
            (d, derr), (a, aerr) = await asyncio.gather(ask(t, "descriptors"), ask(t, "alignment"))
            if stop and (d is None or a is None):
                return
            errors = {k: v for k, v in (("descriptors", derr), ("alignment", aerr)) if v}
            r = row(t, descriptors=d, alignment=a, errors=errors, model=model, batch_id=batch_id, pinned=pinned)
        out[t["stem"]] = r
        if on_row is not None:
            on_row(t["stem"], r)

    await asyncio.gather(*(one(t) for t in traits))
    if stop:
        raise stop[0]
    return out


def run_judge(traits: Sequence[Mapping], **kw) -> dict[str, dict]:
    """:func:`judge` from synchronous code."""
    return asyncio.run(judge(traits, **kw))


__all__ = ["MODEL", "STEPS", "SOURCE", "STAGE", "MODES", "RESPONSES_NAME", "DEFAULT_CONCURRENCY", "sha256_text",
           "load_corpus", "load_existing", "stale_reason", "select", "request", "pins", "estimate", "render", "row",
           "previous_fields", "null_entry", "merge", "parse_rates", "region_counts", "changes", "judge", "run_judge"]
