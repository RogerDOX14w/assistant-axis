"""The plain reading of a label, and its comparison with the intended meaning.

Open point D of ``reports/trait_gap_generation/decisions_m1.md``, case 3 of
Roger's reply ("A word with more then one sense that applies to a person isn't
that problematic unless its most obvious sense isn't a trait, or at least isn't
the trait sense we're trying to describe, and is enough more well-known than
the trait we're trying to describe as to be potentially confusing as part of a
'You are X: ...' prompt").  Appendix 2 of that file measured the failure: a
model given only "You are X." almost never hesitates (75 of 77 words read one
way by all five readers), but for five of the six September rejects it read a
different trait from the one the description meant.  The failure is silent.

Two steps, each with its own prompt, version and pinned hash
(:mod:`assistant_axis.gapgen.rubric_versions`):

1. **The plain reading.**  The model is shown the bare label as a persona
   prompt, "You are <word>.", and nothing else (no system prompt, no intended
   meaning: a model that has seen the intended meaning cannot unsee it), and
   says in one sentence how that persona behaves.  One reading at temperature
   0; the measurement showed readings do not vary.  The prompt is the one the
   measurement used.  It runs only for a row that has an intended meaning to
   compare with (a gloss hint, a validation row carrying one, a corpus label
   with its description); for any other row the classifier's own gloss, which
   was written from the bare word, already is the plain reading.
2. **The comparison.**  A second call compares the plain reading with the
   intended meaning, reason first, and answers ``same``, ``related`` (a
   related trait a careful writer would name differently) or ``different``.
   ``different`` sets the note ``overshadowed`` and ``related`` the note
   ``reading_related`` (round 4); either note raises the row's polysemy flag
   (:func:`notes_for`, ``filter_rubric.derive_notes``).  A corpus comparison
   raises no note and no flag; it lists every row instead.  The row keeps both
   texts so Roger sees them side by side.

Nothing here rejects a word.  :class:`PlainReadingRunner` is used by the
filter (rows with a gloss hint) and by ``data_analysis/gap_generation/
plain_reading.py`` (development sets, the held-out six, and later the whole
corpus: every label read bare and compared with its own description).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from .filter_rubric import _label_key, _load_json, _num, _rows_of
from .llm import call_anthropic_json
from .prompt_labels import DEFAULT_LABEL_FORM, check_label_form, prompt_label
from .registry import utc_now

logger = logging.getLogger(__name__)

READING_VERSION = 1
#: v2 (round 3, after the first development run): "same" spelled out to
#: cover differences of scope, degree, emphasis and setting; v1 answered
#: "related" to 11 of 30 same-by-construction pairs for such differences.
COMPARISON_VERSION = 2
RELATIONS = ("same", "related", "different")
#: Haiku 5.5 from 2026-10-08 (coding_plan_haiku55.md, "The switch"); Haiku 4.5
#: (``claude-haiku-4-5-20251001``) stays selectable with ``--reading-model``.
DEFAULT_READING_MODEL = "claude-haiku-5-5"
#: The second-opinion model, unless a development set shows the classifier
#: model agrees with it on at least 95% of rows (see "M1 as built").
DEFAULT_COMPARE_MODEL = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = 20
READING_MAX_TOKENS = 120
#: The reading's max_tokens on a model that thinks and cannot be told not to (Haiku 5.5, Sonnet 5.5:
#: ``llm.accepts_temperature`` false): its thinking counts against max_tokens, and 120 would cut the
#: sentence off (the split filter gives such models 2000, ``split_runner.MAX_TOKENS_THINKING``).
READING_MAX_TOKENS_THINKING = 2000
COMPARE_MAX_TOKENS = 6000


def reading_max_tokens(model: str) -> int:
    """max_tokens of the plain reading on ``model`` (:data:`READING_MAX_TOKENS`, or
    :data:`READING_MAX_TOKENS_THINKING` for a model that thinks)."""
    from .llm import accepts_temperature
    return READING_MAX_TOKENS if accepts_temperature(model) else READING_MAX_TOKENS_THINKING
HELDOUT_TARGET = 4

#: The user message of the plain reading; the only text the model sees.  It
#: is the prompt of the Appendix 2 measurement (probe_you_are_x/probe.py).
READING_PROMPT = ('A persona is given one instruction and nothing else: "You are {word}."\n'
                  "In one sentence of at most 25 words, describe how this persona behaves. "
                  "Reply with the sentence only.")

#: Words the comparison prompt uses as examples (checked by the tests).
EXAMPLE_WORDS = ("penny-pinching", "outspoken", "sporting", "spendthrift")

COMPARISON_PROMPT = """\
You are checking labels for a research corpus of personality traits. Each trait is a label plus a \
one-sentence description (the intended meaning). A persona is later prompted with the label, so the \
label must lead a reader to the intended trait. For each row you are given the label, a plain reading \
(what a model wrote when told only "You are <label>." and asked how that persona behaves), and the \
intended meaning. Each input row has the keys "label", "plain_reading" and "intended_meaning". \
Decide whether a persona built from the plain reading would be the trait the intended meaning \
describes.

## The three answers
- "same": the plain reading and the intended meaning share the same core disposition, the thing the \
persona would most characteristically do. They count as the same when one is broader or narrower \
than the other, when one is a milder or stronger degree of the other, when they stress different \
aspects of the same disposition, or when the intended meaning applies the disposition to one setting \
(such as how the persona answers questions) that the reading describes in general.
- "related": the core dispositions differ but are neighbors, so a careful writer would give them \
different names; or the reading blends the intended trait with another trait that dominates it.
- "different": the plain reading is a different trait, not a trait at all, or a sense of the word that \
the intended meaning does not use; the intended trait is missing from the reading.
Judge the behaviour described, not the wording. Do not reward shared words: a reading can repeat the \
label and still describe a different trait.

## Examples (reason first, then the answer)
- "penny-pinching": plain reading "Counts every cent, hunts for bargains and refuses to spend on \
anything unnecessary."; intended "This means spending as little as possible, begrudging every \
purchase and treating money saved as the point of every decision." Both describe extreme reluctance \
to spend; relation same.
- "outspoken": plain reading "Voices opinions freely and directly, even when they are unpopular or \
uncomfortable."; intended "This means openly defying people in authority and refusing orders one \
disagrees with." Speaking one's mind overlaps with defiance of authority, but a careful writer would \
call the intended trait defiant; relation related.
- "sporting": plain reading "Loves games and athletics, competitive and always up for a physical \
challenge."; intended "This means playing fair and being generous to opponents, gracious in defeat \
and modest in victory." The reading is fondness for sport; the intended trait is sportsmanship, \
which the reading does not contain; relation different.
- "spendthrift": plain reading "Spends money freely and impulsively, rarely saving and often running \
short."; intended "This means buying on impulse and running through money as soon as it arrives." \
The same carelessness with money; relation same.

## Output
Respond with one JSON object and nothing else. For every row, reason first (at most 40 words), then \
give the relation. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the label>", "reason": "<at most 40 words>", \
"relation": "same"|"related"|"different", "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that the relation is right. Return one row per id, \
in the order given.
"""

PROMPT_SHA256 = {"plain_reading": hashlib.sha256(READING_PROMPT.encode("utf-8")).hexdigest(),
                 "comparison": hashlib.sha256(COMPARISON_PROMPT.encode("utf-8")).hexdigest()}


def build_reading_prompt(label: str, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The bare reading prompt for ``label`` (as stored), shown in ``label_form``
    (:mod:`assistant_axis.gapgen.prompt_labels`: the judge display form by default)."""
    return READING_PROMPT.format(word=" ".join(str(prompt_label(label, label_form)).split()))


def parse_reading(text: Optional[str]) -> Optional[str]:
    """The reading sentence (first non-empty line, whitespace collapsed) or None."""
    for line in (text or "").splitlines():
        line = " ".join(line.split()).strip('"').strip()
        if line:
            return line
    return None


#: A plain reading that is a refusal (the corpus comparison of 2026-09-30: for one label Haiku
#: answered "I can't create content that describes or normalizes homophobic behavior, ...").  The
#: rule: the sentence opens with a first-person refusal AND it names the request or its output.
#: The second half keeps a first-person reading of the persona ("I can't stop talking") from
#: counting.  It misses a refusal that opens any other way ("As an AI, ...", "This request ..."),
#: one that complies with a caveat, and one in another language.
_REFUSAL_OPENING = re.compile(
    r"^(?:i\s+(?:can['’]?t|cannot|can\s+not|won['’]?t|will\s+not|do\s+not|don['’]?t|am\s+(?:not\s+able|unable|sorry))"
    r"|i['’]m\s+(?:not\s+able|unable|sorry|not\s+comfortable|not\s+going\s+to)"
    r"|sorry\b|i\s+apologi[sz]e)", re.I)
_REFUSAL_OBJECT = re.compile(
    r"\b(?:content|create|write|generate|produce|describe|depict|portray|role-?play|persona\s+exercise"
    r"|help\s+with|assist\s+with|comply|this\s+request|that\s+request|this\s+prompt)\b", re.I)


def is_refusal(reading: Optional[str], stop_reason: Optional[str] = None) -> bool:
    """True when a plain reading is a refusal rather than a reading (see the rule above), or when
    the API itself stopped with ``stop_reason`` "refusal"."""
    if stop_reason == "refusal":
        return True
    text = " ".join((reading or "").split()).strip('"“” ')
    return bool(text and _REFUSAL_OPENING.match(text) and _REFUSAL_OBJECT.search(text))


def build_compare_prompt(items: Sequence[dict], *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """``items``: ``{"id", "label", "plain_reading", "intended_meaning"}``; each label (as stored) shown in
    ``label_form`` (the judge display form by default), which is what the answer's label echo must match."""
    lines = [json.dumps({"id": int(it["id"]), "label": prompt_label(it["label"], label_form),
                         "plain_reading": " ".join(str(it["plain_reading"]).split()),
                         "intended_meaning": " ".join(str(it["intended_meaning"]).split())}, ensure_ascii=False)
             for it in items]
    return f"Compare these {len(items)} rows. Reason first, then answer, for each.\n" + "\n".join(lines)


def parse_compare(text: str, ids: Sequence[int], *, labels: Optional[Mapping[int, str]] = None
                  ) -> tuple[dict[int, dict], dict[int, str]]:
    want = [int(i) for i in ids]
    try:
        raw = _rows_of(_load_json(text))
    except (ValueError, json.JSONDecodeError) as exc:
        return {}, {i: f"unparseable response: {exc}" for i in want}
    rows: dict[int, dict] = {}
    errors: dict[int, str] = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        rid = _num(r.get("id"), float("-inf"), float("inf"), integer=True)
        if rid is None or rid not in want or rid in rows:
            continue
        if labels is not None and _label_key(r.get("label")) != _label_key(labels.get(rid)):
            errors[rid] = f"label echo {r.get('label')!r} does not match {labels.get(rid)!r}"
            continue
        reason = r.get("reason")
        rel = str(r.get("relation") or "").strip().lower()
        conf = _num(r.get("confidence"), 0.0, 1.0)
        if not isinstance(reason, str) or not reason.strip():
            errors[rid] = "reason missing"
        elif rel not in RELATIONS:
            errors[rid] = f"relation {r.get('relation')!r} not in {RELATIONS}"
        elif conf is None:
            errors[rid] = "confidence missing or out of range"
        else:
            rows[rid] = {"reason": " ".join(reason.split()), "relation": rel, "confidence": float(conf)}
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    return rows, errors


def notes_for(relation: Optional[str]) -> list[str]:
    """``different`` -> ``overshadowed``; ``related`` -> ``reading_related``
    (round 4: a note under its own name, the conservative answer to the
    review's question 1; the held-out figure still counts ``overshadowed``)."""
    if relation == "different":
        return ["overshadowed"]
    if relation == "related":
        return ["reading_related"]
    return []


@dataclass
class ReadingItem:
    key: str
    label: str
    intended: str
    meta: dict = field(default_factory=dict)


@dataclass
class ReadingResult:
    key: str
    label: str
    intended: str
    stage: str = "pending"            # compared | failed | pending
    reading: Optional[str] = None
    reading_block: Optional[dict] = None
    comparison: Optional[dict] = None
    notes: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def corpus_pairs(data_dir: Path, stems: Optional[Sequence[str]] = None) -> list[ReadingItem]:
    """Every corpus trait (or the given stems) with its own description as the
    intended meaning, expected ``same``.  Reads the trait files only."""
    d = Path(data_dir) / "traits" / "instructions"
    paths = [d / f"{s}.json" for s in stems] if stems else sorted(d.glob("*.json"))
    out = []
    for p in paths:
        obj = json.loads(p.read_text(encoding="utf-8"))
        if not obj.get("description"):
            continue
        out.append(ReadingItem(key=p.stem, label=obj.get("positive_label") or p.stem.replace("_", " "),
                               intended=obj["description"],
                               meta={"expected": "same", "corpus_file": f"traits/instructions/{p.name}"}))
    return out


def _chunks(seq: Sequence, n: int) -> list[list]:
    return [list(seq[i:i + n]) for i in range(0, len(seq), n)]


class PlainReadingRunner:
    """Reads each distinct label once (a call that carries the bare prompt and
    nothing else), then compares readings with intended meanings in batches.
    Responses are recorded (and appended to ``responses_path``) as they
    return; comparison rows that fail validation are retried once.  A guarded
    ``usage`` that raises ``BudgetExceededError`` stops new calls; what was paid
    for is kept and the error propagates."""

    def __init__(self, *, client, batch_id: str, reading_model: str = DEFAULT_READING_MODEL,
                 compare_model: str = DEFAULT_COMPARE_MODEL, usage: Optional[MultiModelUsage] = None,
                 limiter=None, batch_size: int = DEFAULT_BATCH_SIZE, concurrency: int = 4,
                 retry_delays: Optional[Sequence[float]] = None, responses_path: Optional[Path] = None,
                 reuse_readings: Optional[Mapping[str, str]] = None, responses: Optional[list] = None,
                 flag: bool = True, label_form: str = DEFAULT_LABEL_FORM):
        # flag=False: record the answers but raise no note (the corpus comparison,
        # round 4: every label is listed for Roger instead)
        # label_form (prompt_labels): how both calls show the label; readings stay keyed by the stored label
        self.label_form = check_label_form(label_form)
        self.client = client
        self.batch_id = batch_id
        self.reading_model = reading_model
        self.compare_model = compare_model
        self.usage = usage if usage is not None else MultiModelUsage()
        self.limiter = limiter
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.responses_path = Path(responses_path) if responses_path is not None else None
        self.reuse = dict(reuse_readings or {})
        self.responses: list = responses if responses is not None else []
        self.results: dict[str, ReadingResult] = {}
        self.readings: dict[str, Optional[str]] = {}
        self.stats = Counter()
        self.flag = flag
        self._by_label: dict[str, list[str]] = {}
        self._refused_by_api: set[str] = set()
        self._sem: Optional[asyncio.Semaphore] = None
        self._stop: Optional[BaseException] = None

    def _record(self, rec: dict) -> None:
        self.responses.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def _call(self, *, stage: str, model: str, system: Optional[str], user: str, max_tokens: int,
                    keys: list[str]) -> tuple[Optional[str], dict]:
        if self._stop is not None:
            raise self._stop
        meta: dict = {}
        async with self._sem:
            if self._stop is not None:
                raise self._stop
            try:
                text = await call_anthropic_json(
                    self.client, system=system, user=user, model=model, max_tokens=max_tokens, temperature=0.0,
                    usage=self.usage, limiter=self.limiter, meta=meta, **self.retry_kw)
            except BudgetExceededError as exc:
                text = meta.get("text")
                if self._stop is None:
                    self._stop = exc
        rec = {"batch_id": self.batch_id, "stage": stage, "model": model, "keys": keys, "user": user,
               "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_errors": None,
               "at": utc_now()}
        self.stats[f"calls_{stage}"] += 1
        self._record(rec)
        return text, rec

    async def _read(self, label: str, keys: list[str]) -> None:
        text, rec = await self._call(stage="plain_reading", model=self.reading_model, system=None,
                                     user=build_reading_prompt(label, label_form=self.label_form),
                                     max_tokens=reading_max_tokens(self.reading_model), keys=keys)
        reading = parse_reading(text)
        if reading is None:
            rec["parse_errors"] = {k: "empty reading" for k in keys}
        if rec.get("stop_reason") == "refusal":
            self._refused_by_api.add(label)
        self.readings[label] = reading
        self._store_reading(label, reused=False)  # at once, so a stop keeps it (review finding 7)

    def _store_reading(self, label: str, *, reused: bool) -> None:
        reading = self.readings.get(label)
        if reading is None:
            return
        now = utc_now()
        for k in self._by_label.get(label, []):
            res = self.results[k]
            res.reading = reading
            res.reading_block = {"text": reading, "model": None if reused else self.reading_model,
                                 "reused": reused, "rubric_version": READING_VERSION,
                                 "prompt_sha256": PROMPT_SHA256["plain_reading"], "at": now,
                                 "refusal": self._is_refused(label)}

    def _is_refused(self, label: str) -> bool:
        return is_refusal(self.readings.get(label), "refusal" if label in self._refused_by_api else None)

    async def _compare(self, items: list[ReadingItem], stage: str) -> None:
        payload = [{"id": i + 1, "label": it.label, "plain_reading": self.readings[it.label],
                    "intended_meaning": it.intended} for i, it in enumerate(items)]
        text, rec = await self._call(stage=stage, model=self.compare_model, system=COMPARISON_PROMPT,
                                     user=build_compare_prompt(payload, label_form=self.label_form),
                                     max_tokens=COMPARE_MAX_TOKENS, keys=[it.key for it in items])
        # the echo is of the label as shown
        rows, errs = parse_compare(text or "", [p["id"] for p in payload],
                                   labels={p["id"]: prompt_label(p["label"], self.label_form) for p in payload})
        rec["parse_errors"] = {items[i - 1].key: e for i, e in errs.items()}
        now = utc_now()
        for i, row in rows.items():
            res = self.results[items[i - 1].key]
            res.stage, res.error = "compared", None
            res.comparison = {**row, "model": self.compare_model, "rubric_version": COMPARISON_VERSION,
                              "prompt_sha256": PROMPT_SHA256["comparison"], "at": now}
            res.notes = notes_for(row["relation"]) if self.flag else []
        for i, e in errs.items():
            self.results[items[i - 1].key].error = e

    async def _gather(self, coros):
        outs = await asyncio.gather(*coros, return_exceptions=True)
        for o in outs:
            if isinstance(o, BaseException):
                if self._stop is None:
                    self._stop = o
                raise o
        return outs

    async def run_async(self, items: Sequence[ReadingItem]) -> list[ReadingResult]:
        self._sem = asyncio.Semaphore(self.concurrency)
        self._stop = None
        for it in items:
            self.results[it.key] = ReadingResult(key=it.key, label=it.label, intended=it.intended,
                                                 meta=dict(it.meta))
        by_label: dict[str, list[str]] = {}
        for it in items:
            by_label.setdefault(it.label, []).append(it.key)
        self._by_label = by_label
        for label, reading in self.reuse.items():
            if label in by_label:
                self.readings[label] = reading
                self._store_reading(label, reused=True)
        to_read = [lb for lb in by_label if lb not in self.readings]
        self.stats["n_read"] += len(to_read)
        self.stats["n_reused"] += len(by_label) - len(to_read)
        completed = False
        try:
            await self._gather([self._read(lb, by_label[lb]) for lb in to_read])
            self.stats["read_failed"] += sum(1 for lb in to_read if self.readings.get(lb) is None)
            # a plain reading that is a refusal is recorded as one: no comparison, no note
            refused = {lb for lb in by_label if self.readings.get(lb) is not None and self._is_refused(lb)}
            for lb in refused:
                for k in by_label[lb]:
                    res = self.results[k]
                    res.stage, res.notes = "refused", []
                    res.error = "the plain reading was a refusal; no comparison made"
            self.stats["n_refused"] += sum(len(by_label[lb]) for lb in refused)
            todo = [it for it in items if self.results[it.key].reading is not None and it.label not in refused]
            self.stats["n_compare"] += len(todo)
            await self._gather([self._compare(b, "compare") for b in _chunks(todo, self.batch_size)])
            failed = [it for it in todo if self.results[it.key].stage != "compared"]
            if failed:
                self.stats["compare_retries"] += len(failed)
                await self._gather([self._compare(b, "compare_retry") for b in _chunks(failed, self.batch_size)])
            completed = True
        finally:
            if completed:
                for it in items:
                    res = self.results[it.key]
                    if res.stage not in ("compared", "refused"):
                        res.stage = "failed"
                        res.error = res.error or ("no plain reading" if res.reading is None else "unknown")
                self.stats["compare_failed"] += sum(1 for it in items if self.results[it.key].stage == "failed"
                                                    and self.results[it.key].reading is not None)
        return [self.results[it.key] for it in items]

    def run(self, items: Sequence[ReadingItem]) -> list[ReadingResult]:
        return asyncio.run(self.run_async(items))

    def parse_counts(self) -> dict[str, tuple[int, int]]:
        n_r, n_c = self.stats["n_read"], self.stats["n_compare"]
        return {"plain_reading": (n_r - self.stats["read_failed"], n_r),
                "comparison": (n_c - self.stats["compare_failed"], n_c)}

    def warn_parse_rate(self, logger_obj=None) -> None:
        pc = self.parse_counts()
        warn_if_low_parse_rate(label=f"plain_reading:{self.reading_model}", n_ok=pc["plain_reading"][0],
                               n_total=pc["plain_reading"][1], logger_obj=logger_obj or logger)
        warn_if_low_parse_rate(label=f"comparison:{self.compare_model}", n_ok=pc["comparison"][0],
                               n_total=pc["comparison"][1], logger_obj=logger_obj or logger)


def corpus_listing(results: Sequence[ReadingResult]) -> str:
    """The corpus comparison's output for Roger (round 4; review question 1):
    every label with both texts, no flag.  ``different`` first, then
    ``related`` by confidence (highest first), then ``same`` by confidence
    (lowest first), then rows that failed."""
    order = {"different": 0, "related": 1, "same": 2}

    def key(r: ReadingResult):
        rel = (r.comparison or {}).get("relation")
        conf = (r.comparison or {}).get("confidence") or 0.0
        return (order.get(rel, 3), -conf if rel != "same" else conf, r.label)

    lines = ["| answer | label | confidence | plain reading | intended meaning (corpus description) | reason |",
             "|---|---|---|---|---|---|"]
    for r in sorted(results, key=key):
        c = r.comparison or {}

        def cell(x):
            return str("" if x is None else x).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {cell(c.get('relation') or r.stage)} | {cell(r.label)} | {cell(c.get('confidence'))} "
                     f"| {cell(r.reading)} | {cell(r.intended)} | {cell(c.get('reason') or r.error)} |")
    return "\n".join(lines) + "\n"


def heldout_figure(rows: Sequence[Mapping[str, Any]], target: int = HELDOUT_TARGET) -> dict:
    """The recorded target for the six September rejects: ``overshadowed`` on
    at least ``target`` of them.  A target, not a gate."""
    hit = sorted(r["label"] for r in rows if "overshadowed" in (r.get("notes") or []))
    return {"n": len(rows), "overshadowed": len(hit), "overshadowed_labels": hit, "target": target,
            "meets_target": len(hit) >= target}


def summarize(results: Sequence[ReadingResult], *, stats: Counter, usage: MultiModelUsage) -> dict:
    """``summary.json`` payload: relation counts, parse rates, the confusion
    table and the wrong rows when rows carry ``meta["expected"]``, and the
    labels flagged ``overshadowed``."""
    done = [r for r in results if r.stage == "compared"]
    n_r, n_c = stats.get("n_read", 0), stats.get("n_compare", 0)
    out: dict[str, Any] = {
        "n": len(results), "n_compared": len(done), "n_failed": sum(1 for r in results if r.stage == "failed"),
        "n_refused": sum(1 for r in results if r.stage == "refused"),
        "refused": sorted({r.label for r in results if r.stage == "refused"}),
        "relations": {rel: sum(1 for r in done if r.comparison["relation"] == rel) for rel in RELATIONS},
        "overshadowed": sorted({r.label for r in done if "overshadowed" in r.notes}),
        "reading_parse_rate": round((n_r - stats.get("read_failed", 0)) / n_r, 4) if n_r else None,
        "compare_parse_rate": round((n_c - stats.get("compare_failed", 0)) / n_c, 4) if n_c else None,
        "n_readings_called": n_r, "n_readings_reused": stats.get("n_reused", 0),
        "calls": {k[len("calls_"):]: v for k, v in sorted(stats.items()) if k.startswith("calls_")},
        "versions": {"plain_reading": READING_VERSION, "comparison": COMPARISON_VERSION},
        "prompt_sha256": dict(PROMPT_SHA256),
        "cost_usd": round(usage.total_cost_usd, 4), "usage": usage.as_dict(),
    }
    exp = [r for r in done if r.meta.get("expected") in RELATIONS]
    if exp:
        conf: dict[str, dict[str, int]] = {}
        for r in exp:
            row = conf.setdefault(r.meta["expected"], {rel: 0 for rel in RELATIONS})
            row[r.comparison["relation"]] += 1
        out["confusion"] = dict(sorted(conf.items()))
        out["wrong"] = [{"key": r.key, "label": r.label, "expected": r.meta["expected"],
                         "relation": r.comparison["relation"], "reading": r.reading, "intended": r.intended,
                         "reason": r.comparison["reason"]}
                        for r in exp if r.comparison["relation"] != r.meta["expected"]]
        out["accuracy"] = round(1 - len(out["wrong"]) / len(exp), 4)
    return out
