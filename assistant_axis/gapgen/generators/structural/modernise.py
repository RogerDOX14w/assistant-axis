"""Generator A's call: the classical rows modernised by Haiku 5.5 (plan section 5, ``modernise.py``; tasks 3 and 9).

Twenty rows a call (rubric ``structural_modernise``, pinned).  The user turn (:func:`render_modernise_user`) is one
JSON object ``{"rows": [...]}``: each row's ``id``, its scheme's name, the ``item``, its ``role``, the hand-typed
``gloss`` and the other items of its structure (``structure``: item and role of each sibling).  The answer, one
entry per row, reasoning first: ``labels`` (1-3 modern names, best first), ``gloss`` ("This means ...", at most 25
words, without the label) and ``polysemy``.

Parsing (:func:`parse_modernise`): a reply that is not a JSON object with a ``rows`` list does not parse and the
call is asked once more; an entry for an id the call did not send is dropped; a label that breaks the label rule
(:func:`.operators.label_problem`) is dropped and counted, the others kept; an entry with no usable label is a
problem, and the rows of a call left without an answer are asked once more in a call of their own.  Every response
is appended to the run's ``responses.jsonl`` before it is parsed and charged to the usage; a rerun of the same run
reuses every recorded answer to the same prompt (system and user turn) and model, the retry of left-out rows included
(:func:`reusable`), as the operators call does.

The output is ``classical_modern.jsonl`` (:data:`.CLASSICAL_MODERN_PATH`): one :class:`ModernRow` per classical row
answered (the classical fields plus ``labels``, ``gloss_modern``, ``polysemy``, ``reasoning``, ``model``,
``prompt_sha256``, ``run_id``), written with a ``.bak.<UTC>`` snapshot when its content changes.
"""
from __future__ import annotations

import asyncio
import json
import shutil
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.registry import utc_stamp
from assistant_axis.judge import extract_json_blob
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage

from . import CLASSICAL_MODERN_PATH, SCHEMA_VERSION
from .classical import SCHEME_NAMES, ClassicalRow
from .operators import (CHARS_PER_TOKEN, MAX_GLOSS_WORDS, append_response, label_problem, prompt_sha256,
                        read_responses, sha256, stop_problem)

MODEL = "claude-haiku-5-5"
PER_CALL = 20
MAX_LABELS = 3
#: Haiku 5.5's thinking counts against max_tokens; twenty answers are about 2,500 tokens (the plan's figure).
MAX_TOKENS = 12000
EST_OUT_PER_ROW = 125
CONCURRENCY = 4
STAGE = "modernise"


@dataclass
class ModernItem:
    """One row's parsed answer."""
    id: str
    reasoning: str
    labels: list
    gloss: Optional[str]
    polysemy: Optional[bool]
    rejected_labels: list = field(default_factory=list)
    notes: list = field(default_factory=list)


@dataclass
class ModernRow:
    """A classical row with its modern labels (a line of ``classical_modern.jsonl``)."""
    id: str
    scheme: str
    item: str
    role: str
    gloss: str
    sibling_ids: list
    source: Optional[str]
    labels: list
    gloss_modern: Optional[str]
    polysemy: Optional[bool]
    reasoning: str
    model: str
    prompt_sha256: str
    run_id: str
    rejected_labels: list = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    def as_dict(self) -> dict:
        return asdict(self)


def batches(rows: Sequence[ClassicalRow], per_call: int = PER_CALL) -> list[list[ClassicalRow]]:
    """The rows in file order, ``per_call`` at a time."""
    return [list(rows[i:i + per_call]) for i in range(0, len(rows), max(1, per_call))]


def render_modernise_user(rows: Sequence[ClassicalRow], *, siblings_from: Optional[Sequence[ClassicalRow]] = None
                          ) -> str:
    """The user turn for one call: ``{"rows": [...]}`` (module docstring).  ``siblings_from``: the rows the
    siblings are looked up in (default ``rows``; pass every row so that a structure split across two calls is
    still shown whole)."""
    by_id = {r.id: r for r in (siblings_from or rows)}
    out = []
    for r in rows:
        out.append({"id": r.id, "scheme": SCHEME_NAMES.get(r.scheme, r.scheme), "item": r.item, "role": r.role,
                    "gloss": r.gloss,
                    "structure": [{"item": by_id[s].item, "role": by_id[s].role} for s in r.sibling_ids if s in by_id]})
    return "{\"rows\": [\n" + ",\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n]}"


def parse_modernise(text: Optional[str], *, ids: Sequence[str]) -> tuple[Optional[list[ModernItem]], Optional[str]]:
    """``(items, None)`` for a reply holding ``{"rows": [...]}`` (only the ids asked, each at most once, with at
    least one usable label), else ``(None, why)``."""
    if text is None:
        return None, "no response"
    blob = extract_json_blob(text)
    try:
        d = json.loads(blob) if blob else None
    except (json.JSONDecodeError, TypeError):
        d = None
    if not isinstance(d, dict) or not isinstance(d.get("rows"), list):
        return None, "unparseable"
    want = set(ids)
    out: dict[str, ModernItem] = {}
    for e in d["rows"]:
        if not isinstance(e, dict) or e.get("id") not in want or e["id"] in out:
            continue
        labels = e.get("labels")
        if isinstance(labels, str):
            labels = [labels]
        if not isinstance(labels, list):
            continue
        reasoning = e.get("reasoning") if isinstance(e.get("reasoning"), str) else ""
        keep, rejected, notes = [], [], []
        for lab in labels:
            why = label_problem(lab)
            if why:
                rejected.append({"label": lab, "why": why})
            elif " ".join(lab.split()) not in keep:
                keep.append(" ".join(lab.split()))
        if len(keep) > MAX_LABELS:
            notes.append(f"{len(keep)} labels, the first {MAX_LABELS} kept")
            keep = keep[:MAX_LABELS]
        if not keep:
            continue
        gloss = " ".join(e["gloss"].split()) if isinstance(e.get("gloss"), str) and e["gloss"].strip() else None
        if gloss is None:
            notes.append("no gloss")
        elif not gloss.startswith("This means"):
            notes.append("gloss does not start 'This means'")
        if gloss and len(gloss.split()) > MAX_GLOSS_WORDS:
            notes.append(f"gloss {len(gloss.split())} words")
        out[e["id"]] = ModernItem(id=e["id"], reasoning=reasoning.strip(), labels=keep, gloss=gloss,
                                  polysemy=e.get("polysemy") if isinstance(e.get("polysemy"), bool) else None,
                                  rejected_labels=rejected, notes=notes)
    if not out:
        return None, "no usable row"
    return [out[i] for i in ids if i in out], None


@dataclass
class ModerniseRun:
    items: dict = field(default_factory=dict)          # row id -> (ModernItem, record)
    missing: list = field(default_factory=list)        # row ids left without an answer
    records: list = field(default_factory=list)
    n_calls: int = 0
    n_units: int = 0
    n_units_ok: int = 0
    n_reused: int = 0
    stopped_by_budget: bool = False
    #: responses that stopped other than ``end_turn``, by stop reason (each a failed call; review B1, 2026-10-13)
    failures: Counter = field(default_factory=Counter)


def _unit_id(rows: Sequence[ClassicalRow]) -> str:
    return rows[0].id if len(rows) == 1 else f"{rows[0].id}..{rows[-1].id}"


def reusable(records: Sequence[Mapping], *, model: str) -> dict:
    """``{prompt sha256: (items, record)}`` for the recorded answers by ``model`` that parse (the last one per prompt
    winning).  A call is reused when the prompt it would send now (system and user turn) is one of these: a full unit
    of twenty rows, or the call that asks the rows a unit left out, whose user turn depends only on those rows (so it is
    recomputed exactly on a later run; review S1, 2026-10-13: before, the retry's record was keyed by the full units'
    ids and could never be matched)."""
    out = {}
    for r in records:
        if r.get("stage") == STAGE and r.get("model") == model and r.get("prompt_sha256") and not stop_problem(r):
            items, _ = parse_modernise(r.get("text"), ids=r.get("ids") or [])
            if items is not None:
                out[r["prompt_sha256"]] = (items, r)
    return out


async def run_modernise(rows: Sequence[ClassicalRow], *, client, model: str, usage, system: str, run_id: str,
                        out_path: Optional[Path] = None, resume: bool = False, per_call: int = PER_CALL,
                        rubric_version: Optional[int] = None, concurrency: int = CONCURRENCY,
                        max_tokens: int = MAX_TOKENS, now: Optional[Callable[[], str]] = None) -> ModerniseRun:
    """The modernise calls (module docstring)."""
    res = ModerniseRun()
    units = batches(rows, per_call)
    users = {_unit_id(u): render_modernise_user(u, siblings_from=rows) for u in units}
    done = reusable(read_responses(out_path), model=model) if (resume and out_path) else {}
    sem = asyncio.Semaphore(max(1, concurrency))
    sys_sha = sha256(system)

    async def one(u: Sequence[ClassicalRow], user: str, attempt: int) -> Optional[list]:
        meta: dict = {}
        over = False
        try:
            text = await call_anthropic_json(client, system=system, user=user, model=model, max_tokens=max_tokens,
                                             temperature=None, usage=usage, cache_system=True, meta=meta)
        except BudgetExceededError:
            text, over = meta.get("text"), True
        res.n_calls += 1
        uid = _unit_id(u)
        rec = {"schema_version": SCHEMA_VERSION, "stage": STAGE, "run_id": run_id, "unit_id": uid,
               "ids": [r.id for r in u], "attempt": attempt, "model": model, "rubric": "structural_modernise",
               "rubric_version": rubric_version, "system_sha256": sys_sha, "user_sha256": sha256(user),
               "prompt_sha256": prompt_sha256(system, user), "at": now() if now else None, "user": user,
               "text": text, "stop_reason": meta.get("stop_reason"), "stop_details": meta.get("stop_details"),
               "usage_raw": meta.get("usage_raw"),
               "charged_as": model if meta.get("usage_raw") else None, "error": meta.get("error")}
        rec["failure"] = stop_problem(rec)
        if rec["failure"]:
            res.failures[str(rec["stop_reason"])] += 1
        if out_path is not None:
            append_response(rec, out_path)
        res.records.append(rec)
        if over:
            res.stopped_by_budget = True
        items = None if rec["failure"] else parse_modernise(text, ids=rec["ids"])[0]
        if items is not None:
            for it in items:
                res.items[it.id] = (it, rec)
        return items

    async def ask(u: Sequence[ClassicalRow], user: str, attempt: int) -> Optional[list]:
        """A recorded answer to this exact prompt, or a call."""
        got = done.get(prompt_sha256(system, user))
        if got is not None:
            items, rec = got
            for it in items:
                res.items[it.id] = (it, rec)
            res.n_reused += 1
            return items
        return await one(u, user, attempt)

    async def run_unit(u: list[ClassicalRow]) -> None:
        async with sem:
            if res.stopped_by_budget:
                return
            res.n_units += 1
            items = await ask(u, users[_unit_id(u)], 1)
            if items is not None:
                res.n_units_ok += 1
            if res.stopped_by_budget:
                return
            left = [r for r in u if r.id not in res.items]
            if left:                  # the rows the answer left out, asked once more on their own
                await ask(left, render_modernise_user(left, siblings_from=rows), 2)

    await asyncio.gather(*(run_unit(u) for u in units))
    res.missing = [r.id for r in rows if r.id not in res.items]
    res.records.sort(key=lambda r: (r["unit_id"], r["attempt"]))
    return res


def modern_rows(rows: Sequence[ClassicalRow], run: ModerniseRun, *, model: str, run_id: str) -> list[ModernRow]:
    """One :class:`ModernRow` per answered classical row, in the classical rows' order."""
    out = []
    for r in rows:
        got = run.items.get(r.id)
        if got is None:
            continue
        it, rec = got
        out.append(ModernRow(id=r.id, scheme=r.scheme, item=r.item, role=r.role, gloss=r.gloss,
                             sibling_ids=list(r.sibling_ids), source=r.source, labels=list(it.labels),
                             gloss_modern=it.gloss, polysemy=it.polysemy, reasoning=it.reasoning,
                             model=rec.get("model") or model, prompt_sha256=rec.get("prompt_sha256") or "",
                             run_id=rec.get("run_id") or run_id, rejected_labels=list(it.rejected_labels)))
    return out


def merge_modern(old: Sequence[ModernRow], new: Sequence[ModernRow], *, order: Sequence[str]) -> list[ModernRow]:
    """The rows of ``old`` with ``new`` replacing them by id, in ``order`` (the classical tables' order; ids not in
    it after, sorted).  A modernise run of one scheme keeps the other schemes' rows."""
    by = {r.id: r for r in old}
    by.update({r.id: r for r in new})
    pos = {i: k for k, i in enumerate(order)}
    return sorted(by.values(), key=lambda r: (pos.get(r.id, len(pos)), r.id))


def write_modern(rows: Sequence[ModernRow], path: Path = CLASSICAL_MODERN_PATH) -> Optional[Path]:
    """Write ``classical_modern.jsonl``; a changed file is first copied to ``.bak.<UTC>``.  Returns the backup."""
    path = Path(path)
    body = "".join(json.dumps(r.as_dict(), ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_modern(path: Path = CLASSICAL_MODERN_PATH) -> list[ModernRow]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            out.append(ModernRow(**{k: d.get(k) for k in ModernRow.__dataclass_fields__ if k in d}))
    return out


def estimate(rows: Sequence[ClassicalRow], system: str, model: str = MODEL, *, per_call: int = PER_CALL) -> dict:
    """``{"n_calls", "in_tok", "out_tok", "usd"}``: input from the characters sent, output at
    :data:`EST_OUT_PER_ROW` a row."""
    units = batches(rows, per_call)
    if not units:
        return {"n_calls": 0, "in_tok": 0, "out_tok": 0, "usd": 0.0}
    in_tok = int(round(sum((len(system) + len(render_modernise_user(u, siblings_from=rows))) / CHARS_PER_TOKEN
                           for u in units)))
    out_tok = EST_OUT_PER_ROW * len(rows)
    return {"n_calls": len(units), "in_tok": in_tok, "out_tok": out_tok,
            "usd": round(cost_for_usage(model, in_tok, out_tok), 4)}


__all__ = ["MODEL", "PER_CALL", "ModernItem", "ModernRow", "ModerniseRun", "batches", "render_modernise_user",
           "parse_modernise", "run_modernise", "modern_rows", "merge_modern", "write_modern", "load_modern",
           "estimate", "reusable"]
