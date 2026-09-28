"""The trait-hood filter pipeline.

Per candidate: frequency floor (a hard reject below Zipf 2.0 costs nothing)
-> WordNet sense count -> classifier (``batch_size`` candidates per call,
cached rubric; a batch whose JSON is unparseable is retried once as two
halves, and rows that fail validation are retried once in a follow-up batch)
-> definition probe for the 2.0 <= Zipf < 2.5 band (and familiarity
overrides) -> second opinion on a random ``second_opinion_frac`` sample plus
every row with confidence < 0.6 or a prior/LLM disagreement.

The Haiku verdict stays the verdict; the second opinion is recorded beside it
and disagreements are counted for Roger.  A probe that says the word is not
known turns the verdict into ``reject`` with ``too_rare`` (the classifier's
verdict is kept in ``classifier_verdict``).  Every filter block records the
SHA-256 of both prompt texts (``prompt_sha256``).

Budget stops (review_m1.md finding 4).  Each response is recorded (and, with
``responses_path``, appended to ``responses.jsonl``) and each batch's rows are
stored in ``FilterRunner.results`` as soon as that batch returns, so when a
guarded usage raises ``BudgetExceededError`` the caller still has every
response and every row it paid for; rows whose batch never ran stay
``pending``.  After the stop no new call starts.  The overshoot is bounded:
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
from typing import Any, Callable, Optional, Sequence

from assistant_axis.entity_id import display_form_name
from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

from . import filter_rubric as fr
from .freq import familiarity_of, zipf_info
from .llm import call_anthropic_json
from .registry import first_gloss_hint, utc_now
from .wordnet import WordNetInfo, sense_info

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_SECOND_MODEL = "claude-sonnet-4-6"
DEFAULT_BATCH_SIZE = 25
DEFAULT_MAX_TOKENS = 8000
LOW_CONFIDENCE = 0.6

#: SHA-256 of the exact prompt texts sent (review_m1.md finding 10); stamped
#: into every filter block and the batch's run.json.
PROMPT_SHA256 = {"classifier": hashlib.sha256(fr.SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
                 "probe": hashlib.sha256(fr.DEFINE_PROBE_PROMPT.encode("utf-8")).hexdigest()}

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
                              familiarity=familiarity_of(r)))
    return out


def holding_for(verdict: str, tags: Sequence[str]) -> tuple[Optional[str], str]:
    """``(holding, entity_type)``: tagged physical -> physical; tagged role -> roles."""
    if verdict == "tagged" and "physical" in tags:
        return "physical", "trait"
    if verdict == "tagged" and ("role_person" in tags or "role_thing" in tags):
        return "roles", "role"
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
    """Keys for the second opinion: a seeded random ``frac`` of the classified
    rows, plus every row with confidence < ``low_conf``, plus every
    prior/LLM disagreement (evaluative-prior word or single word missing from
    WordNet, classified ``trait``).  Sorted, no duplicates."""
    classified = sorted((r for r in results if r.stage == "classified"), key=lambda r: r.key)
    keys = {r.key for r in classified if (r.filter or {}).get("confidence", 1.0) < low_conf}
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
                 responses_path: Optional[Path] = None):
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
        self._stop: Optional[BudgetExceededError] = None
        self.responses_path = Path(responses_path) if responses_path is not None else None

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
            fq = zipf_info(it.label, familiarity=it.familiarity, zipf_fn=self.zipf_fn)
            try:
                wn = sense_info(it.label, wordnet=self.wordnet) if self.wordnet is not False else WordNetInfo()
            except Exception as exc:  # noqa: BLE001 - a lookup error must not sink the run
                logger.warning("WordNet lookup failed for %r: %s", it.label, exc)
                wn = WordNetInfo()
            res = FilterResult(key=it.key, label=it.label, stage="pending", freq=fq.as_block(),
                               wordnet=wn.as_dict(), meta=dict(it.meta))
            self.results[it.key] = res
            if fq.hard_reject:
                res.stage = "hard_reject"
                res.filter = {
                    "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "model": None, "batch_id": self.batch_id,
                    "reason": f"Zipf {fq.zipf_min:.2f} is below the 2.0 floor (no LLM call).",
                    "verdict": "reject", "tags": ["too_rare"], "region": None, "senses": [],
                    "trait_sense_rank": None, "enactable_in_text": None, "confidence": 1.0,
                    "polysemy": False, "gloss_in_band": False, "second_opinion": None,
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

    def _record_response(self, rec: dict) -> None:
        """Keep one API response: in memory and, when ``responses_path`` is set,
        appended to ``responses.jsonl`` at once (a killed process keeps every
        response it received up to that point)."""
        self.responses.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()

    async def _call(self, *, stage: str, model: str, system: str, user: str, keys: list[str]
                    ) -> tuple[Optional[str], dict]:
        """One API call.  Returns ``(text, rec)``; the caller adds
        ``parse_errors`` to ``rec`` and records it with :meth:`_record_response`.

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
               "error": meta.get("error"), "at": utc_now()}
        self.stats[f"calls_{stage}"] += 1
        return text, rec

    async def _classify_batch(self, items: list[FilterItem], *, model: str, stage: str, apply,
                              allow_split: bool = True) -> tuple[dict[str, dict], dict[str, str]]:
        """Classify one batch; hands its valid rows to ``apply(stage, rows)``
        as soon as the response is parsed; returns ``(rows_by_key, errors_by_key)``."""
        payload = [{"id": i + 1, "label": it.label, "intended_sense": it.intended_sense}
                   for i, it in enumerate(items)]
        text, rec = await self._call(stage=stage, model=model, system=fr.SYSTEM_PROMPT,
                                     user=fr.build_batch_prompt(payload), keys=[it.key for it in items])
        rows, errs = fr.parse_batch(text or "", [p["id"] for p in payload])
        rec["parse_errors"] = {items[i - 1].key: e for i, e in errs.items()}
        self._record_response(rec)
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
        n_senses = res.wordnet.get("n_senses") if res.wordnet.get("found") else None
        hold, et = holding_for(row["verdict"], row["tags"])
        res.filter = {
            "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "model": self.model, "batch_id": self.batch_id,
            "reason": row["reason"], "verdict": row["verdict"], "tags": row["tags"],
            "region": row["region"], "senses": row["senses"], "trait_sense_rank": row["trait_sense_rank"],
            "enactable_in_text": row["enactable_in_text"], "confidence": row["confidence"],
            "polysemy": fr.derive_polysemy(row, n_senses), "gloss_in_band": fr.gloss_in_band(row["gloss"]),
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

    async def define_probe(self, items: list[FilterItem]) -> None:
        band = [it for it in items if self.results[it.key].stage == "classified"
                and self.results[it.key].freq.get("probe_band")]
        if not band:
            return
        self.stats["n_probe"] += len(band)

        async def one(batch: list[FilterItem]):
            payload = [{"id": i + 1, "label": it.label} for i, it in enumerate(batch)]
            text, rec = await self._call(stage="probe", model=self.model, system=fr.DEFINE_PROBE_PROMPT,
                                         user=fr.build_probe_prompt(payload), keys=[it.key for it in batch])
            rows, errs = fr.parse_probe(text or "", [p["id"] for p in payload])
            rec["parse_errors"] = {batch[i - 1].key: e for i, e in errs.items()}
            self._record_response(rec)
            for i, it in enumerate(batch, 1):
                self._apply_probe(it.key, rows.get(i), errs.get(i))

        await self._gather([one(b) for b in _chunks(band, self.batch_size)])
        self._check_stop()

    def _apply_probe(self, key: str, row: Optional[dict], err: Optional[str]) -> None:
        res = self.results[key]
        if row is None:
            self.stats["probe_failed"] += 1
            res.freq["define_probe"] = {"model": self.model, "error": err}
            return
        res.freq["define_probe"] = {"model": self.model, "rubric_version": fr.PROBE_RUBRIC_VERSION,
                                    "known": row["known"], "definition": row["definition"],
                                    "reason": row["reason"]}
        if not row["known"]:
            self.stats["probe_unknown"] += 1
            f = res.filter
            f["classifier_verdict"] = f["verdict"]
            f["verdict"] = "reject"
            f["tags"] = list(dict.fromkeys(list(f["tags"]) + ["too_rare"]))
            f["reason"] = f["reason"] + " [definition probe: word not known]"
            res.holding, res.entity_type = None, "trait"

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
                                       "trait_sense_rank": row["trait_sense_rank"],
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
        if todo:
            await self.classify(todo)
            if self.probe:
                await self.define_probe(todo)
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
    return out


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
