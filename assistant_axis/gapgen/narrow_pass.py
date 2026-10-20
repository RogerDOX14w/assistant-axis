"""The narrow pass: at most one narrow trait per parent goes to review (Roger, 2026-10-20, QUESTIONS 208 (3)).

A **narrow trait** is a narrower case of a broader corpus or queued trait: the same disposition restricted to a
domain, a context or one behaviour (humblebragging under self-aggrandizing, debt-averse under frugal, power-hungry
under dominant).  "At most one per parent, the rest held, so the corpus does not explode; this rule is the
platform's, for every generator."  The pass runs after M3 and before the review graph, in the style of the other
holding-list passes (the physical and states passes): it writes a ``narrow`` block on every row it judges and moves
the held rows to the ``narrow`` holding list (``normalize.HOLDING``), which the review graph leaves out
(``review_graph.select_rows``) and promotion refuses ("never promoted").  Nothing is dropped.

**Candidates** (:func:`select`): registry rows M3 kept (``new`` or ``grey``), awaiting review (no review status
other than ``unreviewed``, not promoted), on no holding list, not judged by this pass already (a ``narrow`` block
whose status is ``kept``, ``held`` or ``not_narrow``), with a gloss, whose best overlap reading by either model
(:func:`assistant_axis.gapgen.m3_neighbours.best_value`) against some corpus trait or queue entry is
:data:`MIN_READING` (2) or more.  Each is asked about its :data:`MAX_PARENTS` (one or two) traits with the highest
such readings (best reading, then final reading, then cosine; opposed traits never), whose text the corpus file or
the seed queue gives (:class:`TextLookup`).  Rows on the ``physical`` and ``states_released`` lists, which go through
review as passes of their own, are left out: a row has one holding list, and moving them to ``narrow`` would lose
theirs.

**The direction call** (the pinned rubric ``reports/trait_gap_generation/rubrics/narrow_direction.md``,
:data:`RUBRIC_NAME`): one ``(candidate, existing trait)`` pair per call, the user turn one JSON object
(:func:`build_user`: labels in the judge display form, ``prompt_labels.prompt_label``; the candidate's M1 gloss and
the trait's description); the answer a short reason, then ``relation`` (:data:`RELATIONS`).  Haiku 5.5 by default, no
temperature, ``max_tokens`` :data:`MAX_TOKENS`, :data:`DEFAULT_READINGS` readings per pair keyed by the reading
index.  Sent live or through the Message Batches API (``batches.BatchTransport``, half price).

**Combining** (:func:`combine`; Roger's rule for sampled outputs: combine, never gate): a pair's verdict is the
plurality of its answered readings; a tie for the most votes is ``tie`` (no verdict).  A row is ``narrower`` than the
first parent, in the order asked, whose verdict is ``narrower``; ``not_narrow`` when every parent has an answer and
none is; ``no_answer`` otherwise (asked again on the next run, from the record).

**One child per parent** (:func:`assign`): the rows judged narrower are grouped by parent (a review-app target key,
``trait:<stem>`` or ``queue:<stem>``).  The child kept for review is the most distinct: the lowest **final** M3
overlap reading to that parent (Opus's where Opus read, else Sonnet's), ties broken by a seeded random choice
(``random.Random(f"{seed}|{parent}")``).  The others are held, each recording the parent and the kept child.  A
parent that already has a kept child from an earlier run (:func:`earlier_kept`) keeps none here: every new child is
held (``held_because: "earlier_run"``), so the cap holds across runs.  The kept child's block carries the parent too,
and the review card shows it as "narrower than X" (``review_app.decisions.narrow_card``).

**Records** (``responses.jsonl``, append-only): every response before it is parsed, with the request's sha256 (system
and user turns), the rubric's version and sha, the reading, the billed usage (``usage_raw``, ``charged_as``) and the
parse.  A refusal is a failed call.  A resume reuses every parsed answer whose request sha, reading and model match.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.gapgen import m3_neighbours as MN
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import Estimate
from assistant_axis.gapgen.llm import call_anthropic_json
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, prompt_label
from assistant_axis.gapgen.registry import utc_now
from assistant_axis.gapgen.split_runner import MAX_TOKENS_THINKING
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, cost_for_usage

PASS_NAME = "narrow"
#: The holding list of a held child (``normalize.HOLDING``) and the registry block every judged row gets
#: (``registry.BLOCKS``).
HOLDING = "narrow"
BLOCK = "narrow"
RUBRIC_NAME = "narrow_direction"
DEFAULT_MODEL = "claude-haiku-5-5"
MODELS: tuple[str, ...] = ("claude-haiku-5-5", "claude-sonnet-5-5")
MAX_TOKENS = MAX_TOKENS_THINKING
RELATIONS: tuple[str, ...] = ("narrower", "same", "broader", "different")
ANSWER_KEYS: tuple[str, ...] = ("reason", "relation")
PARSER_VERSION = 1
DEFAULT_READINGS = 3
#: A row is a candidate when some corpus or queue trait's best overlap reading (either model) reaches this.
MIN_READING = 2
#: The traits asked about per row: the one or two with the highest readings.
MAX_PARENTS = 2
KEPT_DECISIONS = ("new", "grey")
#: Review statuses that still await review (any other status means the row was reviewed).
AWAITING_REVIEW = (None, "unreviewed")
#: A ``narrow`` block with one of these statuses is not judged again.
JUDGED_STATUSES = ("kept", "held", "not_narrow")
STATUSES = ("kept", "held", "not_narrow", "no_answer")
CONCURRENCY = 8
#: For the estimate: the system prompt is about 1,500 characters (about 500 tokens with the 5.x tokenizer; under
#: Haiku 5.5's cache minimum, so sent uncached), the user turn about 120; the answer about 60 tokens, with adaptive
#: thinking on top (both allowed for generously).
EST_IN_TOKENS, EST_OUT_TOKENS = 900, 500
RESPONSES_NAME = "responses.jsonl"
USAGE_NAME = "usage.json"
DECISIONS_NAME = "decisions.json"
READOUT_NAME = "readout.md"
RUN_NAME = "run.json"
BATCHES_NAME = "batches.json"
_CID_RE = re.compile(r"[^A-Za-z0-9_-]")


class RubricNotPinned(RuntimeError):
    """The prompt's text on disk is not its latest pinned version."""


def _clean(text) -> Optional[str]:
    return " ".join(str(text).split()) if isinstance(text, str) and text.strip() else None


# --------------------------------------------------------------------------- the prompt

def load_rubric(rubrics_dir: Optional[Path] = None, *, allow_unpinned: bool = False) -> dict:
    """``{"name", "text", "version", "sha256", "file"}``; refuses a text that is not the latest pin (with
    ``allow_unpinned``, for rendering only, ``version`` and ``sha256`` are None)."""
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] == RUBRIC_NAME]
    path = sr.rubric_path(RUBRIC_NAME, rubrics_dir)
    try:
        from assistant_axis.gapgen.paths import REPO_ROOT
        rel = str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        rel = str(path)
    text = sr.load_prompt(RUBRIC_NAME, rubrics_dir)
    if probs:
        if not allow_unpinned:
            raise RubricNotPinned("; ".join(probs) + "\n" + sr.bump_command(probs))
        return {"name": RUBRIC_NAME, "text": text, "version": None, "sha256": None, "file": rel}
    version, sha = sr.current_versions(rubrics_dir, (RUBRIC_NAME,))[RUBRIC_NAME]
    return {"name": RUBRIC_NAME, "text": text, "version": version, "sha256": sha, "file": rel}


def request_sha256(system: str, user: str) -> str:
    return hashlib.sha256(json.dumps([system, user], ensure_ascii=False).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- the existing traits' texts

@dataclass
class TraitText:
    key: str                # trait:<stem> | queue:<stem> (the review app's target keys)
    stem: str
    kind: str               # corpus | queue
    label: str
    description: str


class TextLookup:
    """The label and description of a corpus trait (``<data_dir>/traits/instructions/<stem>.json``:
    ``positive_label``, ``description``) or a seed-queue trait entry (``label``, and ``description`` else
    ``description_draft``, as ``novelty.queue_text``), by stem; the kind M3 recorded is tried first."""

    def __init__(self, data_dir: Path, queue_path: Optional[Path] = None):
        self.traits_dir = Path(data_dir) / "traits" / "instructions"
        qp = Path(queue_path) if queue_path else Path(data_dir) / "seed_queue.json"
        self.queue: dict[str, dict] = {}
        if qp.exists():
            q = json.loads(qp.read_text(encoding="utf-8"))
            for e in (q.get("entries") if isinstance(q, dict) else q) or []:
                if (e.get("entity_type") or "trait") == "trait" and e.get("stem"):
                    self.queue.setdefault(e["stem"], e)
        self._corpus: dict[str, Optional[TraitText]] = {}

    def corpus(self, stem: str) -> Optional[TraitText]:
        if stem not in self._corpus:
            p = self.traits_dir / f"{stem}.json"
            t = None
            if p.exists():
                try:
                    doc = json.loads(p.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    doc = {}
                desc = _clean(doc.get("description"))
                if desc:
                    t = TraitText(key=f"trait:{stem}", stem=stem, kind="corpus",
                                  label=doc.get("positive_label") or stem.replace("_", " "), description=desc)
            self._corpus[stem] = t
        return self._corpus[stem]

    def queued(self, stem: str) -> Optional[TraitText]:
        e = self.queue.get(stem)
        if not e:
            return None
        desc = next((_clean(e.get(k)) for k in ("description", "description_draft") if _clean(e.get(k))), None)
        if not desc:
            return None
        return TraitText(key=f"queue:{stem}", stem=stem, kind="queue", label=e.get("label") or stem.replace("_", " "),
                         description=desc)

    def get(self, stem: str, kind: str = "corpus") -> Optional[TraitText]:
        order = (self.queued, self.corpus) if kind == "queue" else (self.corpus, self.queued)
        for f in order:
            t = f(stem)
            if t is not None:
                return t
        return None


# --------------------------------------------------------------------------- selection

@dataclass
class Parent:
    key: str
    stem: str
    kind: str
    label: str
    description: str
    best: int               # the higher of the two models' overlap readings
    final: int              # Opus's where Opus read, else Sonnet's
    reading: str            # "3/2", "2/-"
    cosine: Optional[float]


@dataclass
class Item:
    key: str
    stem: str
    label: str
    gloss: str
    parents: list = field(default_factory=list)


def awaiting_review(row: Mapping) -> bool:
    return (row.get("review") or {}).get("status") in AWAITING_REVIEW and not row.get("seed_queue_stem")


def parents_of(row: Mapping, lookup: TextLookup, *, min_reading: int = MIN_READING,
               max_parents: int = MAX_PARENTS) -> tuple[list[Parent], list[str]]:
    """``(the parents to ask, the stems skipped for want of a text)``: the read, non-opposed corpus and queue traits
    whose best reading reaches ``min_reading``, by best reading, final reading and cosine, the first
    ``max_parents`` that have a text."""
    cands = [n for n in MN.neighbours(row) if n.read and n.best is not None and n.best >= min_reading]
    cands.sort(key=lambda n: (-n.best, -(n.final if n.final is not None else -1), -(n.cosine or 0.0), n.stem))
    out, missing = [], []
    for n in cands:
        if len(out) >= max_parents:
            break
        t = lookup.get(n.stem, n.kind)
        if t is None:
            missing.append(n.stem)
            continue
        out.append(Parent(key=t.key, stem=n.stem, kind=t.kind, label=t.label, description=t.description,
                          best=n.best, final=n.final, reading=n.reading_text, cosine=n.cosine))
    return out, missing


def select(rows: Mapping[str, Mapping], lookup: TextLookup, *, scope: Callable[[Mapping], bool],
           min_reading: int = MIN_READING, max_parents: int = MAX_PARENTS) -> tuple[list[Item], dict]:
    """``(items, skipped by reason)`` over the rows ``scope`` admits, by key (module docstring)."""
    items, skipped = [], Counter()
    for k in sorted(rows):
        r = rows[k]
        if not scope(r):
            continue
        nv = r.get("novelty") or {}
        if nv.get("decision") not in KEPT_DECISIONS:
            skipped[f"m3_{nv.get('decision') or 'not_scored'}"] += 1
            continue
        if r.get("holding"):
            skipped[f"held_{r['holding']}"] += 1
            continue
        if not awaiting_review(r):
            skipped["reviewed_or_promoted"] += 1
            continue
        if (r.get(BLOCK) or {}).get("status") in JUDGED_STATUSES:
            skipped["judged_already"] += 1
            continue
        gloss = _clean(r.get("gloss"))
        if not gloss:
            skipped["no_gloss"] += 1
            continue
        ps, missing = parents_of(r, lookup, min_reading=min_reading, max_parents=max_parents)
        if not ps:
            skipped["no_parent_text" if missing else f"no_reading_at_{min_reading}"] += 1
            continue
        items.append(Item(key=k, stem=r.get("stem") or k.split("#")[0], label=r.get("label") or r.get("stem"),
                          gloss=gloss, parents=ps))
    return items, dict(sorted(skipped.items()))


def build_user(item: Item, parent: Parent) -> str:
    """The user turn: one JSON object, the labels in the judge display form."""
    return json.dumps({"candidate": {"label": prompt_label(item.label), "description": item.gloss},
                       "existing": {"label": prompt_label(parent.label), "description": parent.description}},
                      ensure_ascii=False)


# --------------------------------------------------------------------------- calls

@dataclass
class Call:
    key: str                # the candidate row
    parent: str             # the parent's target key
    rep: int                # the reading, 0-based
    model: str
    system: str
    user: str
    max_tokens: int = MAX_TOKENS
    temperature: Optional[float] = None
    cache_system: bool = False
    cache_ttl: Optional[str] = None

    @property
    def request_sha256(self) -> str:
        return request_sha256(self.system, self.user)

    @property
    def custom_id(self) -> str:
        """``nar<reading>-<key>-<hash>``: within the Message Batches limit (64 characters of ``[A-Za-z0-9_-]``)."""
        h = hashlib.sha256(f"{self.key}|{self.parent}|{self.user}|{self.rep}".encode("utf-8")).hexdigest()[:12]
        return f"nar{self.rep + 1}-{_CID_RE.sub('_', self.key)[:36]}-{h}"


def plan_calls(items: Sequence[Item], *, rubric: Mapping, model: str, readings: int,
               answers: Mapping[tuple, Mapping]) -> list[Call]:
    """The ``(row, parent, reading)`` calls without an answer on record, in item order."""
    from assistant_axis.gapgen.split_runner import caches_system
    system = rubric["text"]
    cache = caches_system(system, model)
    out = []
    for it in items:
        for p in it.parents:
            u = build_user(it, p)
            sha = request_sha256(system, u)
            out += [Call(key=it.key, parent=p.key, rep=r, model=model, system=system, user=u, cache_system=cache)
                    for r in range(readings) if (sha, r) not in answers]
    return out


def n_pairs(items: Sequence[Item]) -> int:
    return sum(len(it.parents) for it in items)


def estimate(n_calls: int, model: str = DEFAULT_MODEL, *, transport: str = "live") -> Estimate:
    est = Estimate()
    est.add("narrow direction" + (" (batched)" if transport == "batches" else ""),
            model + (BATCH_SUFFIX if transport == "batches" else ""), n_calls, EST_IN_TOKENS, EST_OUT_TOKENS)
    return est


# --------------------------------------------------------------------------- the parser

def _one_object(text: str) -> tuple[Optional[str], list]:
    """The JSON object the text is, or ends with after leading prose, or holds in a code fence; None otherwise."""
    notes: list = []
    t = text.strip()
    if t.startswith("```"):
        body = t.split("\n", 1)[1] if "\n" in t else ""
        if body.rstrip().endswith("```"):
            t = body.rstrip()[:-3].strip()
            notes.append("code fence removed")
    if not t.startswith("{") and t.endswith("}"):
        for i in [k for k, ch in enumerate(t) if ch == "{"]:
            try:
                cand = json.loads(t[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(cand, dict):
                t = t[i:]
                notes.append("prose before the object")
                break
    if not (t.startswith("{") and t.endswith("}")):
        return None, notes
    return t, notes


def parse_answer(text: Optional[str], stop_reason: Optional[str] = None) -> tuple[Optional[dict], Optional[str], list]:
    """``(answer, None, notes)`` or ``(None, "<kind>: <detail>", notes)``; kinds: refusal, no_response, empty,
    not_one_object, not_json, missing_key, bad_value.  ``answer``: ``{"reason", "relation"}``."""
    if stop_reason == "refusal":
        return None, "refusal: the model declined to answer", []
    if text is None:
        return None, "no_response: the request failed", []
    if not text.strip():
        return None, "empty: no text", []
    t, notes = _one_object(text)
    if t is None:
        return None, "not_one_object: text outside the JSON object", notes
    try:
        obj = json.loads(t)
    except json.JSONDecodeError as exc:
        return None, f"not_json: {exc.msg}", notes
    if not isinstance(obj, dict):
        return None, "not_one_object: not a JSON object", notes
    missing = [k for k in ANSWER_KEYS if k not in obj]
    if missing:
        return None, f"missing_key: {', '.join(missing)}", notes
    reason = _clean(obj["reason"])
    if reason is None:
        return None, "bad_value: reason", notes
    v = obj["relation"]
    v = " ".join(str(v).split()).lower() if isinstance(v, str) else None
    if v not in RELATIONS:
        return None, f"bad_value: relation {obj['relation']!r} (one of {', '.join(RELATIONS)})", notes
    if v != obj["relation"]:
        notes.append("relation normalised")
    extra = sorted(set(obj) - set(ANSWER_KEYS))
    if extra:
        notes.append(f"extra keys {extra}")
    return {"reason": reason, "relation": v}, None, notes


# --------------------------------------------------------------------------- records and transports

def read_records(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue            # a torn last line from a killed run: the request is asked again
    return out


def answers_on_record(records: Sequence[Mapping], *, model: str) -> dict[tuple, dict]:
    """``{(request_sha256, reading): record}``: the latest parsed record of each request and reading on ``model``."""
    out: dict[tuple, dict] = {}
    for r in records:
        if r.get("model") == model and r.get("request_sha256") and r.get("parsed"):
            out[(r["request_sha256"], int(r.get("reading") or 0))] = r
    return out


@dataclass
class RunResult:
    n_calls: int = 0
    n_ok: int = 0
    error_kinds: dict = field(default_factory=dict)
    stopped_by_budget: bool = False


class LiveTransport:
    """Sends the calls through the Messages API, ``runner.concurrency`` at a time; a budget stop keeps the answer that
    crossed the cap and sends nothing more."""
    name = "live"

    def __init__(self, runner: "NarrowRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: Sequence[Call], on_result: Callable) -> None:
        r = self.runner
        sem = asyncio.Semaphore(max(1, int(r.concurrency)))

        async def one(c: Call) -> None:
            if r.result.stopped_by_budget:
                return
            async with sem:
                if r.result.stopped_by_budget:
                    return
                meta: dict = {}
                try:
                    text = await call_anthropic_json(r.client, system=c.system, user=c.user, model=c.model,
                                                     max_tokens=c.max_tokens, temperature=c.temperature,
                                                     usage=r.usage, cache_system=c.cache_system, meta=meta,
                                                     **r.retry_kw)
                except BudgetExceededError:
                    text = meta.get("text")
                    r.result.stopped_by_budget = True
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, text, meta)

        await asyncio.gather(*(one(c) for c in calls))


class NarrowRunner:
    """Sends the direction calls (live by default; ``transport`` a ``batches.BatchTransport`` built on this runner for
    the Message Batches API) and appends every response to ``responses_path`` before it is parsed."""

    def __init__(self, *, client, usage, responses_path: Path, rubric: Mapping, batch_id: str = "",
                 concurrency: int = CONCURRENCY, retry_delays: Optional[Sequence[float]] = None,
                 now: Callable[[], str] = utc_now):
        self.client = client
        self.usage = usage
        self.responses_path = Path(responses_path)
        self.rubric = rubric
        self.batch_id = batch_id
        self.concurrency = concurrency
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.now = now
        self.transport = LiveTransport(self)
        self.result = RunResult()

    def estimate_usd(self, calls: Sequence[Call], *, batch: bool = False) -> float:
        suffix = BATCH_SUFFIX if batch else ""
        return sum(cost_for_usage(c.model + suffix, EST_IN_TOKENS, EST_OUT_TOKENS) for c in calls)

    def on_result(self, c: Call, text: Optional[str], meta: Mapping) -> None:
        parsed, err, notes = parse_answer(text, meta.get("stop_reason"))
        rec = {"key": c.key, "parent": c.parent, "reading": c.rep, "model": c.model, "rubric": self.rubric["name"],
               "prompt_version": self.rubric["version"], "prompt_sha256": self.rubric["sha256"],
               "request_sha256": c.request_sha256, "user": c.user, "custom_id": c.custom_id,
               "transport": getattr(self.transport, "name", "live"), "batch_request_id": meta.get("batch_request_id"),
               "cache_system": c.cache_system, "max_tokens": c.max_tokens, "text": text,
               "stop_reason": meta.get("stop_reason"), "stop_details": meta.get("stop_details"),
               "usage_raw": meta.get("usage_raw"), "charged_as": meta.get("charged_as"), "error": meta.get("error"),
               "parsed": parsed, "parse_error": err, "notes": notes, "parser_version": PARSER_VERSION,
               "label_form": DEFAULT_LABEL_FORM, "at": self.now()}
        self.responses_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.responses_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self.result.n_calls += 1
        if parsed is not None:
            self.result.n_ok += 1
        else:
            k = err.split(":")[0]
            self.result.error_kinds[k] = self.result.error_kinds.get(k, 0) + 1

    async def run(self, calls: Sequence[Call]) -> RunResult:
        try:
            await self.transport.execute("narrow", list(calls), self.on_result)
        except BudgetExceededError:
            self.result.stopped_by_budget = True
        return self.result


# --------------------------------------------------------------------------- combining and the cap

def combine(answers: Sequence[Mapping]) -> dict:
    """One pair's readings: ``{"votes", "n_answered", "verdict"}``, the verdict the plurality (``tie`` when the most
    votes are shared, None when no reading answered)."""
    votes = [a["relation"] for a in answers]
    out = {"votes": votes, "n_answered": len(votes), "verdict": None}
    if not votes:
        return out
    c = Counter(votes).most_common()
    out["verdict"] = c[0][0] if len(c) == 1 or c[0][1] > c[1][1] else "tie"
    return out


def judge(items: Sequence[Item], answers: Mapping[tuple, Mapping], readings: int, *, system: str) -> list[dict]:
    """One row per item: ``{"key", "label", "asked": [per parent: key, label, best, final, reading, votes,
    n_answered, verdict, reasons], "status": "narrower" | "not_narrow" | "no_answer", "parent", "parent_label",
    "parent_final"}`` (module docstring)."""
    out = []
    for it in items:
        asked = []
        for p in it.parents:
            sha = request_sha256(system, build_user(it, p))
            got = [answers[(sha, r)]["parsed"] for r in range(readings) if (sha, r) in answers]
            asked.append({"parent": p.key, "label": p.label, "kind": p.kind, "best": p.best, "final": p.final,
                          "reading": p.reading, "cosine": p.cosine, **combine(got),
                          "reasons": [f"{g['relation']}: {g['reason']}" for g in got]})
        hit = next((a for a in asked if a["verdict"] == "narrower"), None)
        status = "narrower" if hit else ("not_narrow" if all(a["n_answered"] for a in asked) else "no_answer")
        out.append({"key": it.key, "label": it.label, "asked": asked, "status": status,
                    "parent": hit["parent"] if hit else None, "parent_label": hit["label"] if hit else None,
                    "parent_final": hit["final"] if hit else None})
    return out


def earlier_kept(rows: Mapping[str, Mapping], *, exclude: Iterable[str] = ()) -> dict[str, str]:
    """``{parent key: the kept child's key}`` from the registry's ``narrow`` blocks (earlier runs), leaving out
    ``exclude`` (the rows judged now).  Two kept children of one parent (not made by this pass) keep the first key."""
    ex = set(exclude)
    out: dict[str, str] = {}
    for k in sorted(rows):
        b = rows[k].get(BLOCK) or {}
        if k not in ex and b.get("status") == "kept" and b.get("parent"):
            out.setdefault(b["parent"], k)
    return out


def assign(judged: Sequence[Mapping], *, earlier: Mapping[str, str], seed: int | str = 0) -> list[dict]:
    """The decisions: every judged row with its final ``status`` (:data:`STATUSES`): one child per parent ``kept``,
    the most distinct (the lowest final overlap reading to the parent, ties by a seeded random choice), the others
    ``held`` with ``kept_child`` and ``held_because`` (``sibling``, or ``earlier_run`` when an earlier run kept a
    child of that parent); rows not narrower keep ``not_narrow`` or ``no_answer``."""
    out = [dict(d) for d in judged]
    groups: dict[str, list[dict]] = {}
    for d in out:
        if d["status"] == "narrower":
            groups.setdefault(d["parent"], []).append(d)
    for parent, kids in sorted(groups.items()):
        if parent in earlier:
            for d in kids:
                d.update(status="held", kept_child=earlier[parent], held_because="earlier_run")
            continue
        low = min(d["parent_final"] for d in kids)
        tied = sorted(d["key"] for d in kids if d["parent_final"] == low)
        keep = random.Random(f"{seed}|{parent}").choice(tied) if len(tied) > 1 else tied[0]
        for d in kids:
            if d["key"] == keep:
                d.update(status="kept", n_children=len(kids), tie_broken=len(tied) > 1)
            else:
                d.update(status="held", kept_child=keep, held_because="sibling")
    return out


def block_for(d: Mapping, *, run_id: str, rubric: Mapping, model: str, readings: int, seed, now: str) -> dict:
    """The ``narrow`` block a decision writes on its row."""
    b = {"pass": PASS_NAME, "run_id": run_id, "status": d["status"], "parent": d.get("parent"),
         "parent_label": d.get("parent_label"), "parent_final": d.get("parent_final"), "asked": d["asked"],
         "rubric": rubric["name"], "rubric_version": rubric["version"], "prompt_sha256": rubric["sha256"],
         "model": model, "readings": readings, "seed": seed, "label_form": DEFAULT_LABEL_FORM, "at": now}
    for k in ("kept_child", "held_because", "n_children", "tie_broken"):
        if k in d:
            b[k] = d[k]
    return b


def registry_updates(decisions: Sequence[Mapping], **kw) -> dict[str, dict]:
    """``{key: {"narrow": block}}``, and ``"holding": "narrow"`` for a held row."""
    out = {}
    for d in decisions:
        if d["status"] == "narrower":
            raise ValueError(f"{d['key']}: assign() first")
        u = {BLOCK: block_for(d, **kw)}
        if d["status"] == "held":
            u["holding"] = HOLDING
        out[d["key"]] = u
    return out


def counts(decisions: Sequence[Mapping]) -> dict:
    c = Counter(d["status"] for d in decisions)
    out = {s: c.get(s, 0) for s in STATUSES}
    out["parents"] = len({d["parent"] for d in decisions if d["status"] in ("kept", "held")})
    out["held_earlier_run"] = sum(1 for d in decisions if d.get("held_because") == "earlier_run")
    return out


# --------------------------------------------------------------------------- the readout

def _md(s) -> str:
    return str("" if s is None else s).replace("|", "/").replace("\n", " ")


def _rel(target: Path, doc: Path) -> str:
    return os.path.relpath(Path(target).resolve(), Path(doc).resolve().parent).replace(os.sep, "/")


def _target_text(key: Optional[str], label: Optional[str], doc: Path, data_dir: Path) -> str:
    if not key:
        return ""
    kind, _, stem = key.partition(":")
    name = _md(label or stem.replace("_", " "))
    if kind == "trait":
        return f"[{name}]({_rel(Path(data_dir) / 'traits' / 'instructions' / f'{stem}.json', doc)})"
    return f"{name} (queued)"


def render_readout(decisions: Sequence[Mapping], *, run_id: str, rubric: Mapping, model: str, readings: int,
                   usage_usd: float, doc_path: Path, data_dir: Path, files: Mapping[str, Path], skipped: Mapping,
                   labels: Mapping[str, str]) -> str:
    lk = {k: f"[{Path(p).name}]({_rel(p, doc_path)})" for k, p in files.items()}
    c = counts(decisions)
    lines = [f"# Narrow pass `{run_id}`", "",
             f"Roger's rule (QUESTIONS 208 (3), 2026-10-20): at most one narrow trait per parent goes to review; the "
             f"rest are held on the `narrow` list.  {len(decisions)} rows asked of {model}, {readings} reading"
             f"{'s' if readings != 1 else ''} a pair, combined by plurality, with {lk.get('rubric', rubric['name'])} "
             f"version {rubric['version']}; spend on record ${usage_usd:.4f} ({lk.get('usage', 'usage.json')}).  "
             f"Every response: {lk.get('responses', 'responses.jsonl')}; every decision: "
             f"{lk.get('decisions', 'decisions.json')}.", "",
             "| status | rows |", "| --- | ---: |", *[f"| {s} | {c[s]} |" for s in STATUSES],
             "", f"{c['parents']} parents; {c['held_earlier_run']} rows held because an earlier run kept a child of "
             f"their parent.  Not asked: {json.dumps(dict(skipped))}.", "",
             "## The parents", "", "| parent | kept for review (final reading) | held |", "| --- | --- | --- |"]
    by: dict[str, list] = {}
    for d in decisions:
        if d["status"] in ("kept", "held"):
            by.setdefault(d["parent"], []).append(d)
    for parent in sorted(by, key=lambda p: (-len(by[p]), p)):
        kids = by[parent]
        kept = [d for d in kids if d["status"] == "kept"]
        held = [d for d in kids if d["status"] == "held"]
        kept_txt = ", ".join(f"{_md(d['label'])} ({d['parent_final']})" for d in kept)
        if not kept and held:
            k = held[0].get("kept_child")
            kept_txt = f"earlier run: {_md(labels.get(k, k))}"
        lines.append(f"| {_target_text(parent, kids[0].get('parent_label'), doc_path, data_dir)} | {kept_txt} | "
                     + ", ".join(f"{_md(d['label'])} ({d['parent_final']})" for d in held) + " |")
    lines += ["", "## Every row asked", "", "| row | status | parent | asked: verdict (votes) |",
              "| --- | --- | --- | --- |"]
    for d in decisions:
        asked = "; ".join(f"{_md(a['label'])} {a['reading']}: {a['verdict']} ({', '.join(a['votes'])})"
                          for a in d["asked"])
        lines.append(f"| {_md(d['label'])} | {d['status']} | "
                     f"{_target_text(d.get('parent'), d.get('parent_label'), doc_path, data_dir)} | {asked} |")
    return "\n".join(lines) + "\n"


def decisions_doc(decisions: Sequence[Mapping], *, run_id: str, rubric: Mapping, model: str, readings: int, seed,
                  skipped: Mapping, extra: Optional[Mapping] = None) -> dict:
    return {"pass": PASS_NAME, "run_id": run_id, "rubric": rubric["name"], "rubric_version": rubric["version"],
            "prompt_sha256": rubric["sha256"], "model": model, "readings": readings, "seed": seed,
            "parser_version": PARSER_VERSION, "label_form": DEFAULT_LABEL_FORM, "counts": counts(decisions),
            "skipped": dict(skipped), **dict(extra or {}), "decisions": [dict(d) for d in decisions]}


__all__ = ["PASS_NAME", "HOLDING", "BLOCK", "RUBRIC_NAME", "DEFAULT_MODEL", "MODELS", "MAX_TOKENS", "RELATIONS",
           "PARSER_VERSION", "DEFAULT_READINGS", "MIN_READING", "MAX_PARENTS", "STATUSES", "RubricNotPinned",
           "load_rubric", "request_sha256", "TraitText", "TextLookup", "Parent", "Item", "awaiting_review",
           "parents_of", "select", "build_user", "Call", "plan_calls", "n_pairs", "estimate", "parse_answer",
           "read_records", "answers_on_record", "RunResult", "LiveTransport", "NarrowRunner", "combine", "judge",
           "earlier_kept", "assign", "block_for", "registry_updates", "counts", "render_readout", "decisions_doc"]
