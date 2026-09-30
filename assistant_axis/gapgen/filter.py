"""The trait-hood filter pipeline.

Per candidate: frequency floor (a hard reject below ``freq.HARD_REJECT_BELOW``,
with the rescue routes of rule 1b, costs nothing)
-> WordNet sense count -> classifier (``batch_size`` candidates per call,
cached rubric; a batch whose JSON is unparseable is retried once as two
halves, and rows that fail validation are retried once in a follow-up batch)
-> definition probe for the probe band (and rescued words) -> plain reading
and comparison for rows with an intended meaning (round 3,
:mod:`assistant_axis.gapgen.plain_reading`; ``overshadowed``) -> second
opinion on a random ``second_opinion_frac`` sample plus every row with low
confidence, a verdict/tag disagreement or a prior/LLM disagreement.

The Haiku verdict stays the verdict; the second opinion is recorded beside it
and disagreements are counted for Roger.  A probe that says the word is not
known turns the verdict into ``reject`` with ``too_rare`` (the classifier's
verdict is kept in ``classifier_verdict``).  Every filter block records the
SHA-256 of every prompt text (``prompt_sha256``).

Stops (review_m1.md finding 4; review_m1_fixes.md item 3).  Each response is recorded (and, with
``responses_path``, appended to ``responses.jsonl``) and each batch's rows are
stored in ``FilterRunner.results`` as soon as that batch returns, so when a
guarded usage raises ``BudgetExceededError`` the caller still has every
response and every row it paid for; rows whose batch never ran stay
``pending``.  After the stop no new call starts.  Any other exception in a
batch (a parser bug, an unexpected error) stops the run the same way, and is
the exception re-raised; the response that preceded it is already recorded.  The overshoot is bounded:
the call whose charge crossed the cap plus at most ``concurrency - 1`` calls
already in flight, each of which completes and is charged and recorded (a
process killed at that moment would lose only those in-flight responses).
:func:`run_traithood_filter` is the one-call wrapper.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from assistant_axis.entity_id import display_form_name
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from . import filter_rubric as fr
from . import plain_reading as pr
from .freq import HARD_REJECT_BELOW, familiarity_of, is_curated, zipf_info
from .llm import call_anthropic_json
from .registry import first_gloss_hint, utc_now
from .wordnet import WordNetInfo, sense_info

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_SECOND_MODEL = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_TOKENS = 8000
LOW_CONFIDENCE = 0.75  # decision 7 (was 0.6 in the pilot)

#: SHA-256 of the exact prompt texts sent (review_m1.md finding 10); stamped
#: into every filter block and the batch's run.json.
PROMPT_SHA256 = {"classifier": hashlib.sha256(fr.SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
                 "probe": hashlib.sha256(fr.DEFINE_PROBE_PROMPT.encode("utf-8")).hexdigest(),
                 "plain_reading": pr.PROMPT_SHA256["plain_reading"],
                 "comparison": pr.PROMPT_SHA256["comparison"]}

#: Local evaluative prior (plan 14 §3.3): a word here classified ``trait``
#: is a prior/LLM disagreement and gets a second opinion.
EVALUATIVE_PRIOR = frozenset("""
nice good bad great awful fine decent terrible wonderful excellent lovely horrible amazing awesome
dreadful pleasant unpleasant poor superb fantastic brilliant marvelous splendid nasty mediocre perfect
admirable worthy worthless lousy cool neat super grand fabulous terrific outstanding remarkable
impressive disappointing pathetic
""".split())


@dataclass
class FilterItem:
    key: str
    label: str
    intended_sense: Optional[str] = None
    familiarity: Optional[float] = None
    meta: dict = field(default_factory=dict)
    curated: bool = False   # from a curated generator (freq.CURATED_GENERATORS): floor rescue route 3


@dataclass
class FilterResult:
    key: str
    label: str
    stage: str                       # hard_reject | classified | failed
    freq: dict
    wordnet: dict
    filter: Optional[dict] = None
    gloss: Optional[str] = None
    holding: Optional[str] = None
    entity_type: str = "trait"
    meta: dict = field(default_factory=dict)
    error: Optional[str] = None

    def registry_fields(self) -> dict:
        return {"freq": self.freq, "wordnet": self.wordnet, "filter": self.filter, "gloss": self.gloss,
                "holding": self.holding, "entity_type": self.entity_type}

    def as_dict(self) -> dict:
        return asdict(self)


def items_from_records(records: Sequence[dict]) -> list[FilterItem]:
    """Filter items from registry rows (intended sense = first gloss hint)."""
    out = []
    for r in records:
        hint = first_gloss_hint(r)
        out.append(FilterItem(key=r["key"], label=r["label"],
                              intended_sense=display_form_name(hint) if hint else None,
                              familiarity=familiarity_of(r), curated=is_curated(r)))
    return out


#: The membership kind held on its own list (decision 3, open point B).
NATIONALITY_KIND = "nationality_ethnicity_language"


def holding_for(verdict: str, tags: Sequence[str], membership_kind: Optional[str] = None
                ) -> tuple[Optional[str], str]:
    """``(holding, entity_type)`` for a verdict and its tags (routing follows
    the verdict; tags of another verdict never reroute a row, decision 4):
    tagged role -> roles (entity type role); tagged physical -> physical;
    tagged state -> states (decision 12's separate queue; a v1
    ``transient_only`` row too, since that tag folded into ``state``); a
    membership trait of the nationality, ethnicity or language kind ->
    nationalities (still a trait, but held off the main review list: Roger,
    open point B, "Add a tag for this, we can build a queue for them, and draw
    more samples from it if needed"); anything else, including every other
    membership trait, -> no holding list."""
    if verdict == "tagged" and ("role_person" in tags or "role_thing" in tags):
        return "roles", "role"
    if verdict == "tagged" and "physical" in tags:
        return "physical", "trait"
    if verdict == "tagged" and ("state" in tags or "transient_only" in tags):
        return "states", "trait"
    if verdict == "trait" and "membership" in tags and membership_kind == NATIONALITY_KIND:
        return "nationalities", "trait"
    return None, "trait"


def prior_disagrees(res: FilterResult) -> bool:
    f = res.filter or {}
    if f.get("verdict") != "trait":
        return False
    words = res.label.lower().split()
    if len(words) == 1 and words[0] in EVALUATIVE_PRIOR:
        return True
    if len(words) == 1 and "-" not in res.label and not res.wordnet.get("found"):
        return True
    return False


def select_second_opinion(results: Sequence[FilterResult], *, frac: float = 0.10, seed: int = 0,
                          low_conf: float = LOW_CONFIDENCE) -> list[str]:
    """Keys for the second opinion (decision 7): a seeded random ``frac`` of
    the classified rows, plus every row with confidence < ``low_conf`` (0.75),
    plus every row whose verdict and tags disagree (decision 4), plus the
    plan's prior/LLM disagreement (evaluative-prior word or single word
    missing from WordNet, classified ``trait``).  Sorted, no duplicates."""
    classified = sorted((r for r in results if r.stage == "classified"), key=lambda r: r.key)
    keys = {r.key for r in classified if (r.filter or {}).get("confidence", 1.0) < low_conf}
    keys |= {r.key for r in classified if (r.filter or {}).get("tag_disagreement")}
    keys |= {r.key for r in classified if prior_disagrees(r)}
    n_rand = int(round(frac * len(classified)))
    if n_rand:
        rng = random.Random(seed)
        keys |= {r.key for r in rng.sample(classified, min(n_rand, len(classified)))}
    return sorted(keys)


def _chunks(seq: Sequence, n: int) -> list[list]:
    return [list(seq[i:i + n]) for i in range(0, len(seq), n)]


class FilterRunner:
    """Stateful filter run (see module docstring)."""

    def __init__(self, *, client, batch_id: str, model: str = DEFAULT_MODEL,
                 second_model: Optional[str] = DEFAULT_SECOND_MODEL, usage: Optional[MultiModelUsage] = None,
                 limiter=None, batch_size: int = DEFAULT_BATCH_SIZE, second_opinion_frac: float = 0.10,
                 seed: int = 0, probe: bool = True, second_opinion: bool = True,
                 max_tokens: int = DEFAULT_MAX_TOKENS, temperature: float = 0.0, concurrency: int = 4,
                 zipf_fn: Optional[Callable[[str], float]] = None, wordnet: Any = None,
                 retry_delays: Optional[Sequence[float]] = None, shuffle_seed: Optional[int] = None,
                 responses_path: Optional[Path] = None, probe_only: bool = False,
                 plain_reading: bool = True, compare_model: Optional[str] = None):
        # plain_reading: for every classified row with an intended meaning (a
        # gloss hint), read the bare label and compare (plain_reading module);
        # compare_model defaults to plain_reading.DEFAULT_COMPARE_MODEL.
        # probe_only: every item goes to the definition probe, whatever its
        # frequency, and nothing to the classifier or the second opinion (a
        # check of the probe itself; rows end in stage "probed").
        self.client = client
        self.batch_id = batch_id
        self.model = model
        self.second_model = second_model
        self.usage = usage if usage is not None else MultiModelUsage()
        self.limiter = limiter
        self.batch_size = batch_size
        self.second_opinion_frac = second_opinion_frac
        self.seed = seed
        self.probe = probe
        self.second_opinion = second_opinion and bool(second_model)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.concurrency = concurrency
        self.zipf_fn = zipf_fn
        self.wordnet = wordnet
        self.shuffle_seed = shuffle_seed
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.results: dict[str, FilterResult] = {}
        self.responses: list[dict] = []
        self.stats = Counter()
        self._sem: Optional[asyncio.Semaphore] = None
        self._intended: dict[str, Optional[str]] = {}
        self._stop: Optional[BaseException] = None
        self.responses_path = Path(responses_path) if responses_path is not None else None
        self.probe_only = probe_only
        self.plain_reading = plain_reading
        self.compare_model = compare_model or pr.DEFAULT_COMPARE_MODEL

    # -- local stages ------------------------------------------------------
    def prepare(self, items: Sequence[FilterItem]) -> list[FilterItem]:
        """Frequency and WordNet for every item; hard rejects are final here.
        Returns the items that need the classifier."""
        todo = []
        now = utc_now()
        if self.wordnet is None:
            from .wordnet import oewn, oewn_installed
            if oewn_installed():
                self.wordnet = oewn()
            else:
                logger.warning("OEWN is not installed in data/external/wn (run setup_external.py --wn); "
                               "WordNet sense counts are recorded as not found")
                self.wordnet = False
        for it in items:
            fq = zipf_info(it.label, familiarity=it.familiarity, gloss_hint=bool(it.intended_sense),
                           curated=it.curated, zipf_fn=self.zipf_fn)
            try:
                wn = sense_info(it.label, wordnet=self.wordnet) if self.wordnet is not False else WordNetInfo()
            except Exception as exc:  # noqa: BLE001 - a lookup error must not sink the run
                logger.warning("WordNet lookup failed for %r: %s", it.label, exc)
                wn = WordNetInfo()
            res = FilterResult(key=it.key, label=it.label, stage="pending", freq=fq.as_block(),
                               wordnet=wn.as_dict(), meta=dict(it.meta))
            self.results[it.key] = res
            if fq.hard_reject and not self.probe_only:
                res.stage = "hard_reject"
                res.filter = {
                    "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "model": None, "batch_id": self.batch_id,
                    "reason": f"Zipf {fq.zipf_min:.2f} is below the {HARD_REJECT_BELOW} floor and no "
                              f"rescue route applies (no LLM call).",
                    "verdict": "reject", "tags": ["too_rare"], "region": None, "senses": [],
                    "person_senses": [], "trait_senses_equally_obvious": False, "judged_sense": None,
                    "membership_kind": None, "alignment_relevant": False,
                    "tag_disagreement": False,
                    "trait_sense_rank": None, "enactable_in_text": None, "confidence": 1.0,
                    "polysemy": False, "polysemy_notes": [], "plain_reading": None, "comparison": None,
                    "gloss_in_band": False, "second_opinion": None,
                    "prompt_sha256": dict(PROMPT_SHA256), "at": now}
            else:
                todo.append(it)
        self.stats["n_items"] += len(items)
        self.stats["n_hard_reject"] += len(items) - len(todo)
        return todo

    # -- one LLM call -------------------------------------------------------
    def _check_stop(self) -> None:
        if self._stop is not None:
            raise self._stop

    async def _gather(self, coros):
        """Like ``asyncio.gather``, but lets every started coroutine finish
        (so calls already in flight are recorded and their rows kept) before
        re-raising the first exception."""
        outs = await asyncio.gather(*coros, return_exceptions=True)
        for o in outs:
            if isinstance(o, BaseException):
                raise o
        return outs

    def _stop_on(self, exc: BaseException) -> None:
        """Any exception in a batch stops the run: no new call starts after it
        (review_m1_fixes.md item 3).  The first exception is the one re-raised."""
        if self._stop is None:
            self._stop = exc

    def _record_response(self, rec: dict) -> None:
        """Keep one API response: in memory and, when ``responses_path`` is set,
        appended to ``responses.jsonl`` at once, before it is parsed (a killed
        process, or a parser that raises, keeps every response received).  The
        caller adds ``parse_errors`` to the in-memory record afterwards; the CLI
        rewrites the file from memory at the end so the lines gain them."""
        self.responses.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()

    async def _call(self, *, stage: str, model: str, system: str, user: str, keys: list[str]
                    ) -> tuple[Optional[str], dict]:
        """One API call.  Returns ``(text, rec)``; ``rec`` is already recorded
        (:meth:`_record_response`), with ``parse_errors`` still ``None``.

        After a budget stop no new call starts (``BudgetExceededError`` is
        raised before the request); the call whose charge crossed the cap
        returns its text normally, so its rows are kept, and the stop is
        raised at the end of the stage."""
        self._check_stop()
        meta: dict = {}
        async with self._sem:
            self._check_stop()  # the stop may have come while we waited for a slot
            try:
                text = await call_anthropic_json(
                    self.client, system=system, user=user, model=model, max_tokens=self.max_tokens,
                    temperature=self.temperature, usage=self.usage, limiter=self.limiter, meta=meta,
                    **self.retry_kw)
            except BudgetExceededError as exc:
                text = meta.get("text")
                if self._stop is None:
                    self._stop = exc
        rec = {"batch_id": self.batch_id, "stage": stage, "model": model, "keys": keys,
               "user": user, "text": text, "stop_reason": meta.get("stop_reason"),
               "usage_raw": meta.get("usage_raw"), "attempts": meta.get("attempts"),
               "error": meta.get("error"), "parse_errors": None, "at": utc_now()}
        self.stats[f"calls_{stage}"] += 1
        self._record_response(rec)
        return text, rec

    async def _classify_batch(self, items: list[FilterItem], *, model: str, stage: str, apply,
                              allow_split: bool = True) -> tuple[dict[str, dict], dict[str, str]]:
        """Classify one batch; hands its valid rows to ``apply(stage, rows)``
        as soon as the response is parsed; returns ``(rows_by_key, errors_by_key)``.
        Any exception here stops the run (:meth:`_stop_on`) and propagates."""
        try:
            return await self._classify_batch_inner(items, model=model, stage=stage, apply=apply,
                                                    allow_split=allow_split)
        except BaseException as exc:
            self._stop_on(exc)
            raise

    async def _classify_batch_inner(self, items: list[FilterItem], *, model: str, stage: str, apply,
                                    allow_split: bool) -> tuple[dict[str, dict], dict[str, str]]:
        payload = [{"id": i + 1, "label": it.label, "intended_sense": it.intended_sense}
                   for i, it in enumerate(items)]
        text, rec = await self._call(stage=stage, model=model, system=fr.SYSTEM_PROMPT,
                                     user=fr.build_batch_prompt(payload), keys=[it.key for it in items])
        rows, errs = fr.parse_batch(text or "", [p["id"] for p in payload],
                                    labels={p["id"]: p["label"] for p in payload})
        rec["parse_errors"] = {items[i - 1].key: e for i, e in errs.items()}
        by_key = {items[i - 1].key: r for i, r in rows.items()}
        if by_key:
            apply(stage, by_key)
        whole_failed = not rows and all(str(e).startswith("unparseable") for e in errs.values())
        if (text is None or whole_failed) and allow_split and len(items) > 1 and self._stop is None:
            mid = len(items) // 2
            self.stats["split_retries"] += 1
            a, b = await self._gather([
                self._classify_batch(items[:mid], model=model, stage=stage + "_split", apply=apply,
                                     allow_split=False),
                self._classify_batch(items[mid:], model=model, stage=stage + "_split", apply=apply,
                                     allow_split=False)])
            return {**a[0], **b[0]}, {**a[1], **b[1]}
        return by_key, {items[i - 1].key: e for i, e in errs.items()}

    async def _classify_all(self, items: list[FilterItem], *, model: str, stage: str, apply
                            ) -> tuple[dict[str, dict], dict[str, str]]:
        batches = _chunks(items, self.batch_size)
        outs = await self._gather([self._classify_batch(b, model=model, stage=stage, apply=apply)
                                   for b in batches])
        rows: dict[str, dict] = {}
        errs: dict[str, str] = {}
        for r, e in outs:
            rows.update(r)
            errs.update(e)
        failed = [it for it in items if it.key not in rows]
        if failed and self._stop is None:
            self.stats[f"row_retries_{stage}"] += len(failed)
            outs = await self._gather([self._classify_batch(b, model=model, stage=stage + "_retry", apply=apply,
                                                            allow_split=False)
                                       for b in _chunks(failed, self.batch_size)])
            for r, e in outs:
                rows.update(r)
                for k in r:
                    errs.pop(k, None)
                for k, v in e.items():
                    if k not in rows:
                        errs[k] = v
        return rows, errs

    # -- stages ------------------------------------------------------------
    def _set_classified(self, key: str, row: dict, now: str) -> None:
        res = self.results[key]
        res.stage = "classified"
        res.error = None
        hold, et = holding_for(row["verdict"], row["tags"], row.get("membership_kind"))
        notes = fr.derive_notes(row)
        res.filter = {
            "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "model": self.model, "batch_id": self.batch_id,
            "reason": row["reason"], "verdict": row["verdict"], "tags": row["tags"],
            "membership_kind": row.get("membership_kind"), "region": row["region"],
            "alignment_relevant": row.get("alignment_relevant"),
            "person_senses": row["person_senses"],
            "trait_senses_equally_obvious": row["trait_senses_equally_obvious"],
            "judged_sense": row.get("judged_sense"),
            "senses": row["senses"], "trait_sense_rank": row["trait_sense_rank"],
            "enactable_in_text": row["enactable_in_text"], "confidence": row["confidence"],
            "polysemy": bool(notes), "polysemy_notes": notes, "plain_reading": None, "comparison": None,
            "tag_disagreement": row.get("tag_disagreement", False),
            "validator_repairs": list(row.get("validator_repairs") or []),
            "gloss_in_band": fr.gloss_in_band(row["gloss"]),
            "second_opinion": None, "prompt_sha256": dict(PROMPT_SHA256), "at": now}
        res.gloss = row["gloss"]
        res.holding, res.entity_type = hold, et

    async def classify(self, items: list[FilterItem]) -> None:
        """Classify ``items``.  Each batch's rows are stored in ``self.results``
        as the batch returns, so a budget stop keeps every row paid for; rows
        whose batch never ran stay ``pending``; rows that failed parsing after
        the retries become ``failed``."""
        order = list(items)
        if self.shuffle_seed is not None:
            # mix sources/strata within each batch so no batch is all of one kind
            random.Random(self.shuffle_seed).shuffle(order)
        now = utc_now()

        def apply(stage: str, rows: dict[str, dict]) -> None:
            for key, row in rows.items():
                self._set_classified(key, row, now)
            if stage in ("classify", "classify_split"):
                self.stats["n_llm_ok_first_pass"] += len(rows)

        completed = False
        try:
            _, errs = await self._classify_all(order, model=self.model, stage="classify", apply=apply)
            completed = True
        finally:
            if completed and self._stop is None:
                for it in items:
                    res = self.results[it.key]
                    if res.stage != "classified":
                        res.stage = "failed"
                        res.error = errs.get(it.key, "unknown")
            # rows actually answered or given up on (a budget stop leaves the rest pending)
            self.stats["n_llm"] += sum(1 for it in items if self.results[it.key].stage in ("classified", "failed"))
        self._check_stop()

    async def define_probe(self, items: list[FilterItem], *, every: bool = False) -> None:
        """Probe the classified rows in the probe band (or, with ``every``,
        every item given: the probe-only mode)."""
        band = list(items) if every else [it for it in items if self.results[it.key].stage == "classified"
                                           and self.results[it.key].freq.get("probe_band")]
        if not band:
            return
        self.stats["n_probe"] += len(band)

        async def one(batch: list[FilterItem]):
            try:
                await one_inner(batch)
            except BaseException as exc:
                self._stop_on(exc)
                raise

        async def one_inner(batch: list[FilterItem]):
            payload = [{"id": i + 1, "label": it.label} for i, it in enumerate(batch)]
            text, rec = await self._call(stage="probe", model=self.model, system=fr.DEFINE_PROBE_PROMPT,
                                         user=fr.build_probe_prompt(payload), keys=[it.key for it in batch])
            rows, errs = fr.parse_probe(text or "", [p["id"] for p in payload])
            rec["parse_errors"] = {batch[i - 1].key: e for i, e in errs.items()}
            for i, it in enumerate(batch, 1):
                self._apply_probe(it.key, rows.get(i), errs.get(i))

        await self._gather([one(b) for b in _chunks(band, self.batch_size)])
        self._check_stop()

    def _apply_probe(self, key: str, row: Optional[dict], err: Optional[str]) -> None:
        res = self.results[key]
        if row is None:
            self.stats["probe_failed"] += 1
            res.freq["define_probe"] = {"model": self.model, "error": err}
            if res.filter is None:  # probe-only mode
                res.stage, res.error = "failed", err
            return
        res.freq["define_probe"] = {"model": self.model, "rubric_version": fr.PROBE_RUBRIC_VERSION,
                                    "known": row["known"], "definition": row["definition"],
                                    "reason": row["reason"], "prompt_sha256": PROMPT_SHA256["probe"]}
        if res.filter is None:  # probe-only mode: no verdict to change
            res.stage = "probed"
            if not row["known"]:
                self.stats["probe_unknown"] += 1
            return
        if not row["known"]:
            self.stats["probe_unknown"] += 1
            f = res.filter
            f["classifier_verdict"] = f["verdict"]
            f["verdict"] = "reject"
            f["tags"] = list(dict.fromkeys(list(f["tags"]) + ["too_rare"]))
            f["reason"] = f["reason"] + " [definition probe: word not known]"
            res.holding, res.entity_type = None, "trait"

    async def plain_readings(self, items: list[FilterItem]) -> None:
        """Case 3 of open point D: for every classified row (verdict trait or
        tagged) that came with an intended meaning, read the bare label in a
        call of its own and compare it with that meaning.  A row with no
        intended meaning gets no call: its classifier gloss, written from the
        bare word, already is the plain reading."""
        todo = [pr.ReadingItem(key=it.key, label=it.label, intended=self._intended[it.key])
                for it in items if self._intended.get(it.key) and self.results[it.key].stage == "classified"
                and self.results[it.key].filter["verdict"] in ("trait", "tagged")]
        if not todo:
            return
        runner = pr.PlainReadingRunner(client=self.client, batch_id=self.batch_id, reading_model=self.model,
                                       compare_model=self.compare_model, usage=self.usage, limiter=self.limiter,
                                       batch_size=self.batch_size, concurrency=self.concurrency,
                                       responses_path=self.responses_path, responses=self.responses,
                                       **({"retry_delays": self.retry_kw["retry_delays"]} if self.retry_kw else {}))
        try:
            await runner.run_async(todo)
        except BaseException as exc:
            self._stop_on(exc)
            raise
        finally:
            for k, v in runner.stats.items():
                self.stats[f"pr_{k}"] += v
            for it in todo:
                out = runner.results[it.key]
                f = self.results[it.key].filter
                f["plain_reading"] = out.reading_block
                if out.comparison is not None:
                    f["comparison"] = {**out.comparison, "intended_meaning": it.intended}
                elif out.reading is not None:
                    f["comparison"] = {"error": out.error, "intended_meaning": it.intended}
                notes = fr.derive_notes(f)
                f["polysemy_notes"], f["polysemy"] = notes, bool(notes)

    async def second_opinions(self) -> None:
        keys = select_second_opinion(list(self.results.values()), frac=self.second_opinion_frac, seed=self.seed)
        if not keys:
            return
        items = [FilterItem(key=k, label=self.results[k].label) for k in keys]
        # carry the intended sense the first pass saw
        for it in items:
            it.intended_sense = self._intended.get(it.key)
        self.stats["second_opinion_n"] += len(keys)

        def apply(stage: str, rows: dict[str, dict]) -> None:
            for k, row in rows.items():
                f = self.results[k].filter
                agree = row["verdict"] == (f.get("classifier_verdict") or f["verdict"])
                f["second_opinion"] = {"model": self.second_model, "reason": row["reason"],
                                       "verdict": row["verdict"], "tags": row["tags"], "region": row["region"],
                                       "membership_kind": row.get("membership_kind"),
                                       "alignment_relevant": row.get("alignment_relevant"),
                                       "trait_sense_rank": row["trait_sense_rank"],
                                       "person_senses": row["person_senses"],
                                       "judged_sense": row.get("judged_sense"),
                                       "confidence": row["confidence"], "agree": agree}
                if not agree:
                    self.stats["disagreements"] += 1

        completed = False
        try:
            rows, errs = await self._classify_all(items, model=self.second_model, stage="second", apply=apply)
            completed = True
        finally:
            if completed and self._stop is None:
                for k in keys:
                    if k not in rows:
                        self.results[k].filter["second_opinion"] = {"model": self.second_model,
                                                                    "error": errs.get(k)}
                        self.stats["second_opinion_failed"] += 1
        self._check_stop()

    async def run_async(self, items: Sequence[FilterItem]) -> list[FilterResult]:
        self._sem = asyncio.Semaphore(self.concurrency)
        self._stop = None
        self._intended = {it.key: it.intended_sense for it in items}
        todo = self.prepare(items)
        if todo and self.probe_only:
            await self.define_probe(todo, every=True)
        elif todo:
            await self.classify(todo)
            if self.probe:
                await self.define_probe(todo)
            if self.plain_reading:
                await self.plain_readings(todo)
            if self.second_opinion:
                await self.second_opinions()
        return [self.results[it.key] for it in items]

    def run(self, items: Sequence[FilterItem]) -> list[FilterResult]:
        """Run every stage.  On a budget stop ``BudgetExceededError`` propagates
        and ``self.results`` / ``self.responses`` hold everything paid for."""
        return asyncio.run(self.run_async(items))

    # -- reporting -------------------------------------------------------------
    def parse_counts(self) -> tuple[int, int]:
        n = self.stats["n_llm"]
        ok = sum(1 for r in self.results.values() if r.stage == "classified")
        return ok, n

    def warn_parse_rate(self, logger_obj=None) -> None:
        log = logger_obj or logger
        ok, n = self.parse_counts()
        warn_if_low_parse_rate(label=f"traithood_filter:{self.model}", n_ok=ok, n_total=n, logger_obj=log)
        n_probe = self.stats["n_probe"]
        if n_probe:
            warn_if_low_parse_rate(label=f"traithood_filter:probe:{self.model}",
                                   n_ok=n_probe - self.stats["probe_failed"], n_total=n_probe, logger_obj=log)
        n_r = self.stats["pr_n_read"]
        if n_r:
            warn_if_low_parse_rate(label=f"traithood_filter:plain_reading:{self.model}",
                                   n_ok=n_r - self.stats["pr_read_failed"], n_total=n_r, logger_obj=log)
        n_c = self.stats["pr_n_compare"]
        if n_c:
            warn_if_low_parse_rate(label=f"traithood_filter:comparison:{self.compare_model}",
                                   n_ok=n_c - self.stats["pr_compare_failed"], n_total=n_c, logger_obj=log)
        n2 = self.stats["second_opinion_n"]
        if n2:
            warn_if_low_parse_rate(label=f"traithood_filter:second:{self.second_model}",
                                   n_ok=n2 - self.stats["second_opinion_failed"], n_total=n2, logger_obj=log)


def _fractions(counter: Counter, n: int) -> dict:
    return {k: round(v / n, 4) for k, v in sorted(counter.items())} if n else {}


def summarize(results: Sequence[FilterResult], *, stats: Counter, usage: MultiModelUsage,
              stratum_key: Optional[str] = None) -> dict:
    """``summary.json`` payload (plan §6 report rows, plus per-stratum blocks)."""
    def block(rs: Sequence[FilterResult]) -> dict:
        done = [r for r in rs if r.filter is not None]
        clf = [r for r in rs if r.stage == "classified"]
        vc = Counter(r.filter["verdict"] for r in done)
        tc = Counter(t for r in done for t in r.filter["tags"])
        rc = Counter(r.filter.get("region") for r in done if r.filter.get("region"))
        poly = sum(1 for r in clf if r.filter.get("polysemy"))
        useful = sum(1 for r in done if r.filter["verdict"] == "trait" and not r.filter.get("polysemy"))
        so = [r.filter["second_opinion"] for r in clf if r.filter.get("second_opinion")
              and "verdict" in r.filter["second_opinion"]]
        return {"n": len(rs), "n_done": len(done), "n_failed": sum(1 for r in rs if r.stage == "failed"),
                "n_pending": sum(1 for r in rs if r.stage == "pending"),
                "n_hard_reject": sum(1 for r in rs if r.stage == "hard_reject"),
                "verdict_counts": dict(sorted(vc.items())), "verdict_fractions": _fractions(vc, len(done)),
                "tag_counts": dict(sorted(tc.items())), "tag_fractions": _fractions(tc, len(done)),
                "region_counts": dict(sorted(rc.items())),
                "polysemy_n": poly, "polysemy_rate": round(poly / len(clf), 4) if clf else None,
                "gloss_in_band_rate": (round(sum(1 for r in clf if r.filter.get("gloss_in_band")) / len(clf), 4)
                                       if clf else None),
                "n_useful": useful,
                "second_opinion_n": len(so), "disagreements": sum(1 for s in so if not s.get("agree"))}

    out = block(results)
    n_llm = stats.get("n_llm", 0)
    ok = sum(1 for r in results if r.stage == "classified")
    cost = usage.total_cost_usd
    out.update({
        "parse_rate": round(ok / n_llm, 4) if n_llm else None,
        "parse_rate_first_pass": round(stats.get("n_llm_ok_first_pass", 0) / n_llm, 4) if n_llm else None,
        "n_llm": n_llm, "probe_n": stats.get("n_probe", 0), "probe_unknown": stats.get("probe_unknown", 0),
        "probe_failed": stats.get("probe_failed", 0),
        "second_opinion_requested": stats.get("second_opinion_n", 0),
        "second_opinion_failed": stats.get("second_opinion_failed", 0),
        "calls": {k[len("calls_"):]: v for k, v in sorted(stats.items()) if k.startswith("calls_")},
        "cost_usd": round(cost, 4),
        "cost_per_candidate_usd": round(cost / len(results), 6) if results else None,
        "yield_per_usd": round(out["n_useful"] / cost, 1) if cost > 0 else None,
        "usage": usage.as_dict(),
    })
    if stratum_key:
        strata: dict[str, list] = {}
        for r in results:
            strata.setdefault(str(r.meta.get(stratum_key)), []).append(r)
        out["by_stratum"] = {s: block(rs) for s, rs in sorted(strata.items())}
        if stratum_key == "stratum":
            out["validation_figures"] = validation_figures(results)
    clf = [r for r in results if r.stage == "classified"]
    out["v2_fields"] = {
        "alignment_relevant_true": sum(1 for r in clf if r.filter.get("alignment_relevant") is True),
        "membership_kind": dict(sorted(Counter(r.filter.get("membership_kind") for r in clf
                                               if r.filter.get("membership_kind")).items())),
        "tag_disagreement": sum(1 for r in clf if r.filter.get("tag_disagreement")),
        # rows the validator repaired instead of refusing (round 5, defect 1)
        "validator_repairs": dict(sorted(Counter(x for r in clf
                                                 for x in (r.filter.get("validator_repairs") or [])).items())),
        "polysemy_notes": {n: sum(1 for r in clf if n in (r.filter.get("polysemy_notes") or []))
                           for n in fr.POLYSEMY_NOTES},
        "comparison_relations": dict(sorted(Counter(str((r.filter.get("comparison") or {}).get("relation"))
                                                    for r in clf if r.filter.get("comparison")).items())),
        "holding": dict(sorted(Counter(r.holding for r in results if r.holding).items())),
        "freq_rescue": dict(sorted(Counter(r.freq.get("rescue") for r in results
                                           if r.freq.get("rescue")).items())),
    }
    return out


#: The M1 quality figures (decision 2: recorded targets, not gates).
TARGET_EXISTING_CORRECT = 0.95
TARGET_REJECTS_FLAGGED = 4
TARGET_RANDOM_TRAIT_MAX = 0.15
#: Tags that make an existing corpus label count as correct although the
#: verdict is not ``trait`` (decision 2, "How an existing label is scored").
EXISTING_OK_TAGS = ("state", "physical", "membership")


def existing_label_outcome(r: FilterResult) -> str:
    """``correct`` (verdict trait, or verdict tagged with a state / physical /
    membership tag), or the kind of miss: ``floor`` (cut by the frequency
    floor or the probe), ``reject``, ``roles`` (sent to the roles list),
    ``other``, ``failed``.  A ``reject`` verdict is a miss whatever tags it
    carries (Roger, decision 2: a label "counts as a miss when it is
    rejected"; review_rubric_v2.md finding 4)."""
    f = r.filter or {}
    if not f:
        return "failed"
    tags = set(f.get("tags") or [])
    verdict = f.get("verdict")
    if verdict == "trait":
        return "correct"
    if verdict == "reject":
        return "floor" if (r.stage == "hard_reject" or "too_rare" in tags) else "reject"
    if tags & set(EXISTING_OK_TAGS):
        return "correct"
    if r.holding == "roles":
        return "roles"
    return "other"


#: Size and seed of the sample of random adjectives that passed as traits,
#: printed for Roger's marks (coordinator, round 4; review question 2).
RANDOM_SAMPLE_N = 50
RANDOM_SAMPLE_SEED = 0


def random_trait_sample_for_marks(results: Sequence[FilterResult], *, n: int = RANDOM_SAMPLE_N,
                                  seed: int = RANDOM_SAMPLE_SEED) -> tuple[list[dict], bool]:
    """A fixed-seed sample of ``n`` random adjectives (stratum ``oewn_random``)
    that passed with verdict ``trait``: ``{"label", "key", "gloss"}``, listed
    alphabetically by key.  The pool is sorted by key before sampling so the
    sample does not depend on row order.

    The sample is drawn only from rows never seen in development
    (``meta["seen_in"]`` empty or absent), since a seen row tells Roger little
    about the rubric (m1_validation: 22 of the 50 had been seen).  When fewer
    than ``n`` unseen rows passed, it falls back to all passing rows.  Returns
    ``(sample, unseen_only)``; ``unseen_only`` is False after a fallback."""
    passed = sorted((r for r in results if str(r.meta.get("stratum")) == "oewn_random" and r.filter
                     and r.filter.get("verdict") == "trait"), key=lambda r: r.key)
    unseen = [r for r in passed if not r.meta.get("seen_in")]
    unseen_only = len(unseen) >= n
    pool = unseen if unseen_only else passed
    pick = random.Random(seed).sample(pool, min(n, len(pool)))
    return ([{"label": r.label, "key": r.key, "gloss": r.gloss} for r in sorted(pick, key=lambda r: r.key)],
            unseen_only)


def random_trait_sample(results: Sequence[FilterResult], *, n: int = RANDOM_SAMPLE_N,
                        seed: int = RANDOM_SAMPLE_SEED) -> list[dict]:
    """The sample of :func:`random_trait_sample_for_marks` without its flag."""
    return random_trait_sample_for_marks(results, n=n, seed=seed)[0]


def _figures(results: Sequence[FilterResult]) -> dict:
    by: dict[str, list[FilterResult]] = {}
    for r in results:
        by.setdefault(str(r.meta.get("stratum")), []).append(r)
    ex = by.get("existing", [])
    outcomes = {r.label: existing_label_outcome(r) for r in ex}
    correct = sum(1 for o in outcomes.values() if o == "correct")
    misses: dict[str, list[str]] = {}
    for label, o in sorted(outcomes.items()):
        if o != "correct":
            misses.setdefault(o, []).append(label)
    share = round(correct / len(ex), 4) if ex else None
    rej = by.get("rejects", [])
    # the flag and the figure agree: a reject-stratum word counts as flagged
    # when its polysemy flag (any note) is set (review finding 2)
    flagged = [r.label for r in rej if r.filter and r.filter.get("polysemy")]
    rnd = [r for r in by.get("oewn_random", []) if r.filter]
    rnd_trait = sum(1 for r in rnd if r.filter.get("verdict") == "trait")
    rnd_share = round(rnd_trait / len(rnd), 4) if rnd else None
    # a figure with no rows has no verdict on its target: None, not False
    # (round 5, review_rubric_v2_fixes.md defect 7)
    return {
        "existing": {"n": len(ex), "correct": correct, "share": share, "target": TARGET_EXISTING_CORRECT,
                     "meets_target": None if share is None else share >= TARGET_EXISTING_CORRECT,
                     "misses": misses,
                     "labels_with_state": sorted(r.label for r in ex
                                                 if "state" in ((r.filter or {}).get("tags") or [])),
                     "labels_with_physical": sorted(r.label for r in ex
                                                    if "physical" in ((r.filter or {}).get("tags") or []))},
        "rejects": {"n": len(rej), "flagged": len(flagged), "flagged_labels": sorted(flagged),
                    "target": TARGET_REJECTS_FLAGGED,
                    "meets_target": None if not rej else len(flagged) >= TARGET_REJECTS_FLAGGED},
        "oewn_random": {"n": len(rnd), "trait": rnd_trait, "trait_share": rnd_share,
                        "target": TARGET_RANDOM_TRAIT_MAX,
                        "meets_target": None if rnd_share is None else rnd_share <= TARGET_RANDOM_TRAIT_MAX},
    }


def validation_figures(results: Sequence[FilterResult]) -> dict:
    """The three M1 figures against their targets (decision 2), plus the
    existing labels that received ``state`` or ``physical``, by name.

    Every figure is given twice (review_rubric_v2.md finding 1): at the top
    level for all rows, and under ``unseen`` for the rows never seen in
    development (``meta["seen_in"]`` empty or absent; see
    :func:`development_seen`).  ``oewn_random`` also carries
    ``sample_for_marks``, a fixed-seed sample of the random adjectives that
    passed as traits, for Roger's marks, drawn from the unseen rows only
    unless fewer than 50 of them passed (``sample_for_marks_unseen_only``
    says which)."""
    out = _figures(results)
    unseen = [r for r in results if not r.meta.get("seen_in")]
    out["unseen"] = _figures(unseen)
    out["n_seen_in_development"] = len(results) - len(unseen)
    sample, unseen_only = random_trait_sample_for_marks(results)
    out["oewn_random"]["sample_for_marks"] = sample
    out["oewn_random"]["sample_for_marks_unseen_only"] = unseen_only
    return out


def is_measurement_run(run_dir: Path) -> bool:
    """True when ``run_dir/run.json`` records ``"measurement": true``."""
    p = Path(run_dir) / "run.json"
    if not p.exists():
        return False
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("measurement") is True
    except (ValueError, AttributeError):
        return False


def stability_agreement(full: Sequence[Mapping], rerun: Sequence[Mapping]) -> dict:
    """Verdict agreement between the full validation run and the stability
    rerun, over the keys both classified.  Rows cut by the frequency floor
    (stage ``hard_reject`` in either run) are left out: the floor is a fixed
    rule, so counting them would inflate the agreement (round 5,
    review_rubric_v2_fixes.md defect 2).  Rows without a filter block
    (failed, pending) are left out too.

    Returns ``{"n", "agree", "share", "n_floor_excluded", "disagreements"}``,
    ``disagreements`` a sorted list of ``(key, full verdict, rerun verdict)``."""
    def index(rows):
        return {r["key"]: r for r in rows if r.get("filter")}
    a, b = index(full), index(rerun)
    common = sorted(set(a) & set(b))
    floor = [k for k in common if "hard_reject" in (a[k].get("stage"), b[k].get("stage"))]
    keys = [k for k in common if k not in set(floor)]
    dis = [(k, a[k]["filter"]["verdict"], b[k]["filter"]["verdict"]) for k in keys
           if a[k]["filter"]["verdict"] != b[k]["filter"]["verdict"]]
    n = len(keys)
    return {"n": n, "agree": n - len(dis), "share": round((n - len(dis)) / n, 4) if n else None,
            "n_floor_excluded": len(floor), "disagreements": dis}


def development_seen(candidates_dir: Path, *, exclude: Sequence[str] = ()) -> dict[str, list[str]]:
    """Registry-style key -> the recorded runs (``filter/<id>``,
    ``plain_reading/<id>``) whose results contain it: where a validation row
    was seen while the rules were being written (review finding 1).  Runs
    whose id is in ``exclude`` (the run being scored) are skipped, and so are
    ``.bak`` copies and **measurement runs** (run.json ``"measurement":
    true``, set by ``traithood_filter.py --measurement`` or ``--stability``):
    a measurement looks at rows without shaping the rules, so it does not make
    them seen (round 5, review_rubric_v2_fixes.md defect 2).  Plain-reading
    keys (``calm#same``) are mapped to the label's stem with sense 1."""
    from .normalize import make_key, normalize_candidate
    seen: dict[str, set[str]] = {}
    for kind in ("filter", "plain_reading"):
        for res in sorted(Path(candidates_dir).glob(f"{kind}/*/results.jsonl")):
            run = res.parent.name
            if run in exclude or ".bak." in run or is_measurement_run(res.parent):
                continue
            for line in res.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if kind == "filter":
                    key = row.get("key")
                else:
                    try:
                        key = make_key(normalize_candidate(row["label"]).stem, 1)
                    except (KeyError, ValueError):
                        continue
                if key:
                    seen.setdefault(key, set()).add(f"{kind}/{run}")
    return {k: sorted(v) for k, v in sorted(seen.items())}


def corpus_regions(results: Sequence[dict], trait_stems: Sequence[str], *, batch_id: Optional[str]) -> dict:
    """``corpus_regions.json`` payload from a validation run's results (no
    API call; review finding 8): every corpus trait stem -> ``{"label",
    "region", "alignment_relevant", "verdict", "batch_id"}`` from the run's
    ``existing``-stratum row, ``region`` null when the row was cut or
    rejected, and every field null for a stem the run did not contain."""
    from .normalize import split_key
    by_stem = {}
    for r in results:
        if (r.get("meta") or {}).get("stratum") != "existing" or not r.get("key"):
            continue
        f = r.get("filter") or {}
        by_stem[split_key(r["key"])[0]] = {"label": r.get("label"), "region": f.get("region"),
                                           "alignment_relevant": f.get("alignment_relevant"),
                                           "verdict": f.get("verdict"), "batch_id": batch_id}
    return {s: by_stem.get(s, {"label": None, "region": None, "alignment_relevant": None, "verdict": None,
                               "batch_id": batch_id})
            for s in sorted(trait_stems)}


def run_traithood_filter(records: Sequence[dict] | Sequence[FilterItem], *, client, model: str = DEFAULT_MODEL,
                         second_model: Optional[str] = DEFAULT_SECOND_MODEL, usage: Optional[MultiModelUsage] = None,
                         limiter=None, batch_size: int = DEFAULT_BATCH_SIZE, second_opinion_frac: float = 0.10,
                         seed: int = 0, batch_id: str = "adhoc", **kw) -> list[FilterResult]:
    """Filter registry rows (dicts) or :class:`FilterItem` objects (plan §5 signature)."""
    items = [r if isinstance(r, FilterItem) else None for r in records]
    if any(i is None for i in items):
        items = items_from_records(records)  # type: ignore[arg-type]
    runner = FilterRunner(client=client, batch_id=batch_id, model=model, second_model=second_model,
                          usage=usage, limiter=limiter, batch_size=batch_size,
                          second_opinion_frac=second_opinion_frac, seed=seed, **kw)
    out = runner.run(items)
    runner.warn_parse_rate()
    return out
