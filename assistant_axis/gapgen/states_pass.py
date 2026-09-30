"""The states pass: a separate rubric for words the classifier tagged ``state``.

Open point C of ``reports/trait_gap_generation/decisions_m1.md`` (confirmed by
Roger on 2026-09-29, with one correction): rubric v1's ``transient_only`` tag
folds into ``state``, the classifier sets nothing about plausibility, "and we
do a separate pass with a different rubric for plausibility (my step a),
rather than relying on a rubric that's doing a lot of other things as well to
determine it."  (His words, typing slips corrected.)  His three steps for a
state word (decision 12): "a) figure out if a habitual predisposition to state
is plausible, b) whether the name of the state is still a good name for the
predisposition (or if not, change the stem to that), and [c)] write the
description to describe the habitual predisposition."

Two modes, each with its own prompt and prompt hash, one rubric version:

* ``queue``: rows on the ``states`` holding list (or, for checks, rows of a
  filter ``results.jsonl`` tagged ``state``).  Per row, reason first:
  ``plausible`` (is a habitual predisposition to the state plausible?),
  ``name_fits`` (is the state's name still a good name for the
  predisposition?), ``suggested_name`` (when it is not), and ``gloss`` (a
  draft description of the predisposition, in the filter's gloss form and
  20-40 word band).  These are suggestions for Roger; the only thing that acts
  on them is promotion (:func:`assistant_axis.gapgen.promote.promote`), which
  lets a ``states`` row through once the pass has judged it plausible, under
  the suggested name and with the draft gloss.
* ``corpus``: existing corpus labels that came back tagged ``state``.  Given
  the label and its corpus description, the model says whether the
  description describes a habitual predisposition or a momentary state.  The
  default assumption, in Roger's words, is that "this has already been done",
  so the output is a short list of exceptions (descriptions read as
  momentary) for him to look at, not a verdict on the label.  This mode only
  reads corpus files and writes nothing but its own run directory.

The block written on a row (registry field ``states_pass``, or the run's
``results.jsonl``) carries ``mode``, ``rubric_version``, ``model``,
``batch_id``, the answers, ``confidence``, ``prompt_sha256`` and ``at``.
Changing anything the model reads here is a rubric change: bump
its entry in :data:`RUBRIC_VERSIONS` (and the pin in rubric_versions).  Example words are checked by the tests never
to be corpus labels, seed-queue entries, the six September rejects or the
decisions file's appendix words.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from .filter_rubric import _bool, _label_key, _load_json, _num, _rows_of, gloss_in_band
from .llm import call_anthropic_json
from .normalize import normalize_candidate
from .registry import utc_now

logger = logging.getLogger(__name__)

#: One version per prompt (round 3, QUESTIONS 17: a version identifies one
#: prompt text; pinned in rubric_versions).  Queue v2: the example "sulking"
#: became "moping", since sulking appears in the "You are X." probe results.
RUBRIC_VERSIONS = {"queue": 3, "corpus": 2}
#: Round 4 (review_rubric_v2.md finding 10): queue v3 drops "listless", "single", "usual" and "usually",
#: validation-file words, from its text; corpus v2 replaces the example "exasperated", a
#: validation-file word, with "vexed", and drops "usually".
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_BATCH_SIZE = 20
DEFAULT_MAX_TOKENS = 6000
MODES = ("queue", "corpus")
READINGS = ("predisposition", "momentary")
#: Tags that put a filter row in the states queue (``transient_only`` is
#: rubric v1's, folded into ``state``).
STATE_TAGS = ("state", "transient_only")

#: Example words of both prompts, and the names the examples suggest.
QUEUE_EXAMPLES = ("moping", "startled", "bored", "tearful", "sunburned", "drenched")
CORPUS_EXAMPLES = ("fretful", "vexed")
EXAMPLE_WORDS = QUEUE_EXAMPLES + CORPUS_EXAMPLES
SUGGESTED_NAMES = ("mopey", "jumpy", "easily bored")

QUEUE_PROMPT = """\
You are helping to build a research corpus of personality traits. Each trait is a label plus a \
one-sentence description, and a persona is prompted to embody it while answering ordinary questions \
in text, so a trait must be something a person can have as a standing way of being, not something that \
happens to them once.

## Your task
Each candidate below names a state: a condition someone is in for a while (a mood, a reaction, a bodily \
or situational condition). You are given the state's name and a one-sentence description of the state. \
For each, work through three steps:
1. plausible: is a habitual predisposition to this state plausible? That is, could a person be prone \
to falling into it again and again, so that the proneness is part of who they are and would show in how \
they talk? Moods, reactions and emotional or social states mostly allow it. Conditions imposed from \
outside, or purely bodily conditions that no temperament brings about, mostly do not.
2. name_fits: if plausible, is the state's own name still a good name for the predisposition? It is \
when ordinary speakers already use the word for a person who is often that way. If not, give \
suggested_name: the plainest ordinary English name for the predisposition (one word if one \
exists, otherwise a short phrase such as "easily ..." or "prone to ...").
3. gloss: if plausible, write one sentence of 20 to 40 words (count them) describing the habitual \
predisposition, not the passing state, in the form "This means ...", from the inside: what the person \
habitually does, feels or says. Go straight to the behaviour. No hedges ("tends to", "sometimes", \
"may"). A vice is described as a vice. US spelling.
If a predisposition is not plausible, set name_fits, suggested_name and gloss to null.

## Examples (reason first, then the answers)
- "moping": people are often prone to moping; the habit has its own ordinary name; plausible true; \
name_fits false; suggested_name "mopey"; gloss "This means sinking into idle gloom after any \
setback, trailing about without energy or interest, and letting everyone see how low one feels \
until something lifts the mood."
- "startled": some people are startled by every small surprise; the ordinary name for that is jumpy; \
plausible true; name_fits false; suggested_name "jumpy"; gloss "This means reacting to every sudden \
noise, interruption or unexpected question with a jolt of alarm, losing the thread for a moment and \
needing time to settle again."
- "bored": a person can be easily bored as a standing way of being; the state's name does not say \
that; plausible true; name_fits false; suggested_name "easily bored"; gloss "This means losing interest \
quickly in any topic, task or conversation that is not new, pushing for a change of subject and \
treating repetition or routine as something hard to endure."
- "tearful": said of people who cry easily as well as of a passing moment; plausible true; name_fits \
true; suggested_name null; gloss "This means being moved to tears easily and often, by sad news, kind \
words or strong memories, and letting the emotion show openly in how one speaks and responds."
- "sunburned": a condition caused by the sun on the skin; no temperament brings it about; plausible \
false; name_fits null; suggested_name null; gloss null.
- "drenched": a condition imposed by rain or water; plausible false; name_fits null; suggested_name \
null; gloss null.

## Output
Respond with one JSON object and nothing else. For every candidate, reason first (at most 30 words), \
then give the answers. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the candidate>", "reason": "<at most 30 words>", \
"plausible": true|false, "name_fits": true|false|null, "suggested_name": "<name>"|null, \
"gloss": "<sentence>"|null, "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that the plausible answer is right. Return one row per \
candidate id, in the order given.
"""

CORPUS_PROMPT = """\
You are checking entries in a research corpus of personality traits. Each trait is a label plus a \
one-sentence corpus description, and a persona is prompted to embody it in text, so every description \
should describe a standing way of being: a habitual predisposition that a person carries from one day \
to the next.

## Your task
Each label below also names a state, a condition someone can be in for a while. You are given the label \
and its corpus description. Decide which reading the description takes:
- "predisposition": the description describes a habitual or standing tendency to be in, or to fall \
into, the state (how the person mostly is);
- "momentary": the description describes being in the state now, or for a passing spell, with nothing \
that makes it a lasting way of being.
Judge the description as written, not the label on its own. When the description could be read either \
way, choose "predisposition" and say why.

## Examples (reason first, then the reading)
- "fretful", description "This means worrying over small things day after day, turning every plan into \
a list of what could go wrong.": written as a daily habit; reading predisposition.
- "vexed", description "This means being fed up right now with someone who has tried one's \
patience past its limit.": written as a condition of the moment; reading momentary.

## Output
Respond with one JSON object and nothing else. For every label, reason first (at most 30 words), then \
give the reading. Use exactly these keys in this order:
{"results": [{"id": <int>, "label": "<the label>", "reason": "<at most 30 words>", \
"reading": "predisposition"|"momentary", "confidence": <0-1>}]}
confidence is your probability, between 0 and 1, that the reading is right. Return one row per id, in \
the order given.
"""

PROMPTS = {"queue": QUEUE_PROMPT, "corpus": CORPUS_PROMPT}
PROMPT_SHA256 = {m: hashlib.sha256(p.encode("utf-8")).hexdigest() for m, p in PROMPTS.items()}


# ---------------------------------------------------------------------------
# prompts and parsing
# ---------------------------------------------------------------------------

def build_batch_prompt(items: Sequence[dict], mode: str) -> str:
    """User message: one JSON line per item, ``{"id", "label", "state_description"}``
    (queue) or ``{"id", "label", "corpus_description"}`` (corpus)."""
    key = "state_description" if mode == "queue" else "corpus_description"
    lines = [json.dumps({"id": int(it["id"]), "label": it["label"],
                         key: " ".join(str(it.get("text") or "").split()) or None}, ensure_ascii=False)
             for it in items]
    what = "states" if mode == "queue" else "labels"
    return f"Judge these {len(items)} {what}. Reason first, then answer, for each.\n" + "\n".join(lines)


def _str_or_none(v) -> Optional[str]:
    if isinstance(v, str):
        v = " ".join(v.split())
        return v if v and v.lower() not in ("null", "none") else None
    return None


def validate_queue_row(row: dict, expected_label: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    """A queue-mode row: ``plausible`` is required; when true, ``name_fits``
    and ``gloss`` are required, and ``suggested_name`` when the name does not
    fit; when false, the other answers are dropped."""
    if not isinstance(row, dict):
        return None, "row is not an object"
    if expected_label is not None and _label_key(row.get("label")) != _label_key(expected_label):
        return None, f"label echo {row.get('label')!r} does not match {expected_label!r}"
    reason = _str_or_none(row.get("reason"))
    if reason is None:
        return None, "reason missing"
    plausible = _bool(row.get("plausible"))
    if plausible is None:
        return None, f"plausible {row.get('plausible')!r} is not a boolean"
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if conf is None:
        return None, "confidence missing or out of range"
    name_fits = suggested = gloss = None
    if plausible:
        name_fits = _bool(row.get("name_fits"))
        if name_fits is None:
            return None, "name_fits missing for a plausible predisposition"
        suggested = _str_or_none(row.get("suggested_name")) if not name_fits else None
        if not name_fits and suggested is None:
            return None, "suggested_name missing although the name does not fit"
        gloss = _str_or_none(row.get("gloss"))
        if gloss is None:
            return None, "gloss missing for a plausible predisposition"
    stem = None
    if suggested is not None:
        try:
            stem = normalize_candidate(suggested).stem
        except ValueError as exc:
            return None, f"suggested_name unusable: {exc}"
    return {"label": row.get("label"), "reason": reason, "plausible": plausible, "name_fits": name_fits,
            "suggested_name": suggested, "suggested_stem": stem, "gloss": gloss,
            "gloss_in_band": gloss_in_band(gloss) if gloss else None, "confidence": float(conf)}, None


def validate_corpus_row(row: dict, expected_label: Optional[str] = None) -> tuple[Optional[dict], Optional[str]]:
    if not isinstance(row, dict):
        return None, "row is not an object"
    if expected_label is not None and _label_key(row.get("label")) != _label_key(expected_label):
        return None, f"label echo {row.get('label')!r} does not match {expected_label!r}"
    reason = _str_or_none(row.get("reason"))
    if reason is None:
        return None, "reason missing"
    reading = str(row.get("reading") or "").strip().lower()
    if reading not in READINGS:
        return None, f"reading {row.get('reading')!r} not in {READINGS}"
    conf = _num(row.get("confidence"), 0.0, 1.0)
    if conf is None:
        return None, "confidence missing or out of range"
    return {"label": row.get("label"), "reason": reason, "reading": reading, "confidence": float(conf)}, None


def parse_batch(text: str, ids: Sequence[int], *, mode: str, labels: Optional[Mapping[int, str]] = None
                ) -> tuple[dict[int, dict], dict[int, str]]:
    """``(rows, errors)`` as :func:`assistant_axis.gapgen.filter_rubric.parse_batch`."""
    validate = validate_queue_row if mode == "queue" else validate_corpus_row
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
        ok, err = validate(r, (labels or {}).get(rid) if labels is not None else None)
        if ok is None:
            errors[rid] = err
        else:
            rows[rid] = ok
            errors.pop(rid, None)
    for i in want:
        if i not in rows and i not in errors:
            errors[i] = "missing"
    return rows, errors


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

@dataclass
class StatesItem:
    key: str
    label: str
    text: Optional[str]            # the state's gloss (queue) or the corpus description (corpus)
    meta: dict = field(default_factory=dict)


@dataclass
class StatesResult:
    key: str
    label: str
    stage: str                     # judged | failed | pending
    block: Optional[dict] = None
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def is_state_row(filter_block: Optional[dict]) -> bool:
    return bool(set((filter_block or {}).get("tags") or []) & set(STATE_TAGS))


def state_text(row: dict) -> Optional[str]:
    """The text the states pass reads for a row: the filter's gloss, or, for a row of the split
    filter (which writes no gloss for a word on the states list), the accepted reading
    (``filter.judged_sense``)."""
    return row.get("gloss") or (row.get("filter") or {}).get("judged_sense")


def items_from_filter_results(rows: Sequence[dict], *, stratum: Optional[str] = None) -> list[StatesItem]:
    """Rows of a filter ``results.jsonl`` whose filter block carries ``state``
    (or v1's ``transient_only``), optionally of one validation stratum.  The
    item text is the filter's gloss of the state, or the split filter's
    accepted reading when the row has no gloss (:func:`state_text`)."""
    out = []
    for r in rows:
        if not is_state_row(r.get("filter")):
            continue
        if stratum is not None and (r.get("meta") or {}).get("stratum") != stratum:
            continue
        out.append(StatesItem(key=r["key"], label=r["label"], text=state_text(r),
                              meta={"stratum": (r.get("meta") or {}).get("stratum"),
                                    "filter_verdict": (r.get("filter") or {}).get("verdict")}))
    return out


def items_from_registry(records: Sequence[dict]) -> list[StatesItem]:
    """Registry rows on the ``states`` holding list."""
    return [StatesItem(key=r["key"], label=r["label"], text=state_text(r)) for r in records
            if r.get("holding") == "states"]


def corpus_items(names: Sequence[str], data_dir: Path) -> tuple[list[StatesItem], dict[str, str]]:
    """Corpus-check items for trait labels or stems, read from
    ``<data_dir>/traits/instructions/<stem>.json`` (read only).  Returns
    ``(items, missing)``; ``missing`` maps a name to why it was skipped."""
    items, missing = [], {}
    for name in names:
        stem = normalize_to_file_name(name)
        path = Path(data_dir) / "traits" / "instructions" / f"{stem}.json"
        if not path.exists():
            missing[name] = f"no corpus trait file {path.name}"
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        desc = d.get("description")
        if not desc:
            missing[name] = "corpus file has no description"
            continue
        items.append(StatesItem(key=stem, label=d.get("positive_label") or name, text=desc,
                                meta={"corpus_file": f"traits/instructions/{path.name}"}))
    return items, missing


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _chunks(seq: Sequence, n: int) -> list[list]:
    return [list(seq[i:i + n]) for i in range(0, len(seq), n)]


class StatesPassRunner:
    """One states-pass run.  Each response is recorded (and appended to
    ``responses_path`` as it returns) before it is parsed; rows that fail
    validation are retried once in a follow-up batch.  A guarded ``usage``
    that raises ``BudgetExceededError`` stops new calls; every response and
    row paid for is kept in ``responses`` / ``results`` and the error
    propagates from :meth:`run`, as in the filter."""

    def __init__(self, *, client, batch_id: str, mode: str, model: str = DEFAULT_MODEL,
                 usage: Optional[MultiModelUsage] = None, limiter=None, batch_size: int = DEFAULT_BATCH_SIZE,
                 concurrency: int = 4, max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = 0.0,
                 retry_delays: Optional[Sequence[float]] = None, responses_path: Optional[Path] = None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.client = client
        self.batch_id = batch_id
        self.mode = mode
        self.model = model
        self.usage = usage if usage is not None else MultiModelUsage()
        self.limiter = limiter
        self.batch_size = batch_size
        self.concurrency = concurrency
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.responses_path = Path(responses_path) if responses_path is not None else None
        self.results: dict[str, StatesResult] = {}
        self.responses: list[dict] = []
        self.stats = Counter()
        self._sem: Optional[asyncio.Semaphore] = None
        self._stop: Optional[BaseException] = None

    @property
    def system_prompt(self) -> str:
        return PROMPTS[self.mode]

    def _record(self, rec: dict) -> None:
        self.responses.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def _batch(self, items: list[StatesItem], stage: str) -> dict[str, str]:
        """One call; valid rows are stored at once.  Returns errors by key."""
        if self._stop is not None:
            raise self._stop
        payload = [{"id": i + 1, "label": it.label, "text": it.text} for i, it in enumerate(items)]
        user = build_batch_prompt(payload, self.mode)
        meta: dict = {}
        async with self._sem:
            if self._stop is not None:
                raise self._stop
            try:
                text = await call_anthropic_json(
                    self.client, system=self.system_prompt, user=user, model=self.model,
                    max_tokens=self.max_tokens, temperature=self.temperature, usage=self.usage,
                    limiter=self.limiter, meta=meta, **self.retry_kw)
            except BudgetExceededError as exc:
                text = meta.get("text")
                if self._stop is None:
                    self._stop = exc
        rec = {"batch_id": self.batch_id, "stage": stage, "mode": self.mode, "model": self.model,
               "keys": [it.key for it in items], "user": user, "text": text,
               "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
               "attempts": meta.get("attempts"), "error": meta.get("error"), "parse_errors": None,
               "at": utc_now()}
        self.stats[f"calls_{stage}"] += 1
        self._record(rec)
        rows, errs = parse_batch(text or "", [p["id"] for p in payload], mode=self.mode,
                                 labels={p["id"]: p["label"] for p in payload})
        rec["parse_errors"] = {items[i - 1].key: e for i, e in errs.items()}
        now = utc_now()
        for i, row in rows.items():
            it = items[i - 1]
            res = self.results[it.key]
            res.stage, res.error = "judged", None
            res.block = {"mode": self.mode, "rubric_version": RUBRIC_VERSIONS[self.mode], "model": self.model,
                         "batch_id": self.batch_id, **{k: v for k, v in row.items() if k != "label"},
                         "prompt_sha256": PROMPT_SHA256[self.mode], "at": now}
        return {items[i - 1].key: e for i, e in errs.items()}

    async def _gather(self, coros):
        outs = await asyncio.gather(*coros, return_exceptions=True)
        for o in outs:
            if isinstance(o, BaseException):
                if self._stop is None:
                    self._stop = o
                raise o
        return outs

    async def run_async(self, items: Sequence[StatesItem]) -> list[StatesResult]:
        self._sem = asyncio.Semaphore(self.concurrency)
        self._stop = None
        for it in items:
            self.results[it.key] = StatesResult(key=it.key, label=it.label, stage="pending", meta=dict(it.meta))
        todo = [it for it in items if it.text]
        for it in items:
            if not it.text:
                self.results[it.key].stage = "failed"
                self.results[it.key].error = "no text to judge"
        self.stats["n_items"] += len(items)
        errs: dict[str, str] = {}
        completed = False
        try:
            for e in await self._gather([self._batch(b, "judge") for b in _chunks(todo, self.batch_size)]):
                errs.update(e)
            failed = [it for it in todo if self.results[it.key].stage != "judged"]
            if failed:
                self.stats["row_retries"] += len(failed)
                for e in await self._gather([self._batch(b, "judge_retry")
                                             for b in _chunks(failed, self.batch_size)]):
                    errs.update(e)
            completed = True
        finally:
            if completed:
                for it in todo:
                    res = self.results[it.key]
                    if res.stage != "judged":
                        res.stage, res.error = "failed", errs.get(it.key, "unknown")
            self.stats["n_judged_or_failed"] += sum(1 for it in todo
                                                    if self.results[it.key].stage in ("judged", "failed"))
        return [self.results[it.key] for it in items]

    def run(self, items: Sequence[StatesItem]) -> list[StatesResult]:
        return asyncio.run(self.run_async(items))

    def parse_counts(self) -> tuple[int, int]:
        """``(judged, attempted)`` over rows that had text to judge."""
        n = self.stats["n_judged_or_failed"]
        ok = sum(1 for r in self.results.values() if r.stage == "judged")
        return ok, n

    def warn_parse_rate(self, logger_obj=None) -> None:
        ok, n = self.parse_counts()
        warn_if_low_parse_rate(label=f"states_pass:{self.mode}:{self.model}", n_ok=ok, n_total=n,
                               logger_obj=logger_obj or logger)


def _name_key(name: str) -> str:
    """A name compared for renames: case, surrounding whitespace, and
    hyphen/space differences ignored (``job-satisfied`` == ``Job satisfied``)."""
    return " ".join(str(name).strip().lower().replace("-", " ").split())


def is_name_unchanged(label: str, suggested: str) -> bool:
    """True when a suggested name is the label itself under :func:`_name_key`.
    Spelling variants (``agonising`` / ``agonizing``) are not detected."""
    return _name_key(label) == _name_key(suggested)


def summarize(results: Sequence[StatesResult], *, mode: str, stats: Counter, usage: MultiModelUsage) -> dict:
    """``summary.json`` payload.  Queue mode: plausibility counts and the
    suggested renames (``renamed`` leaves out a suggestion that is the label
    itself up to case, surrounding whitespace and hyphen/space, counted in
    ``n_name_unchanged`` instead; the row keeps the suggestion either way).
    Corpus mode: ``exceptions``, the labels whose corpus description reads as
    a momentary state (the short list for Roger)."""
    judged = [r for r in results if r.stage == "judged"]
    n = stats.get("n_judged_or_failed", 0)
    out: dict[str, Any] = {
        "mode": mode, "n": len(results), "n_judged": len(judged),
        "n_failed": sum(1 for r in results if r.stage == "failed"),
        "n_pending": sum(1 for r in results if r.stage == "pending"),
        "parse_rate": round(len(judged) / n, 4) if n else None,
        "calls": {k[len("calls_"):]: v for k, v in sorted(stats.items()) if k.startswith("calls_")},
        "rubric_version": RUBRIC_VERSIONS[mode], "prompt_sha256": PROMPT_SHA256[mode],
        "cost_usd": round(usage.total_cost_usd, 4), "usage": usage.as_dict(),
    }
    if mode == "queue":
        pl = [r for r in judged if r.block["plausible"]]
        named = [r for r in pl if r.block.get("suggested_name")]
        out.update({
            "plausible": len(pl), "implausible": len(judged) - len(pl),
            "renamed": [f"{r.label} -> {r.block['suggested_name']}" for r in named
                        if not is_name_unchanged(r.label, r.block["suggested_name"])],
            "n_name_unchanged": sum(1 for r in named if is_name_unchanged(r.label, r.block["suggested_name"])),
            "gloss_in_band_rate": (round(sum(1 for r in pl if r.block.get("gloss_in_band")) / len(pl), 4)
                                   if pl else None),
        })
    else:
        out["exceptions"] = [{"label": r.label, "key": r.key, "reason": r.block["reason"],
                              "confidence": r.block["confidence"]}
                             for r in judged if r.block["reading"] == "momentary"]
        out["readings"] = dict(sorted(Counter(r.block["reading"] for r in judged).items()))
    return out
