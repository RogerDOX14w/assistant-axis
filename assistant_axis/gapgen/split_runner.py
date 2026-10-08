"""The split trait-hood filter's runner: the waves of coding_plan_split.md section 6.

Every call carries one item.  The waves:

====  =========================================================================================
wave  calls
====  =========================================================================================
0     frequency floor and WordNet (no call, :meth:`FilterRunner.prepare`); definition probe for
      the probe band, one word per call
1     sense (the label)
2     established, vague and kind, once for each primary reading
3     same sense (a word with two readings left by rule 2 that are both trait or membership);
      comparison (a row with an intended sense), one pair per call
4     gloss (outcome trait; on the second model for a word chosen for a second opinion);
      second (and third) opinion, step 1
5     second (and third) opinion, established / vague / kind; then the disagreement tripwire
6     alignment and descriptors on the gloss; second (and third) opinion, same sense
====  =========================================================================================

The words for a second opinion are chosen after wave 3, from the join, so wave 4 knows which model
writes each gloss: a seeded ``second_opinion_frac`` of the words that reached step 1, plus every
word with the note ``obvious_sense_not_trait`` or ``most_likely_reading_stretched``.  The first
model's outcome stays the outcome; agreement means the same outcome.  The second model's gloss is
written for the row's accepted reading.  (The plan's table lists the second opinion's three steps
in wave 4; they depend on each other, so they run in waves 4 to 6.)

Readings (``readings``, coding_plan_haiku55.md "The switch", item 2; Roger 2026-10-08).  The first
model's verdict waves (step 1, the established / vague / kind checks, the same-sense check) run
``readings`` times per word as independent readings, each recorded (``verdict_reading`` on the response
record, 1 to N; reading 1 keeps the state keys and request identity of a one-reading run, reading r > 1
lives under ``r<r>_sense`` / ``r<r>_same_sense``).  Each reading's outcome is known after wave 2, so the
vote (:func:`split.combine_readings`: turned away only if every reading turns the word away, else the
majority; no majority: trait if any reading says trait, else the first reading left) is taken there, and
the winning reading (the first whose outcome won) is the row's: wave 3's comparison runs on its readings
only, and the gloss, alignment and descriptors run once, on its accepted reading.  The second opinion and
the tripwire compare the combined outcome.  The default is :func:`default_readings` (3 on Haiku 5.5, else
1); with one reading the run is the one-reading run it always was.  A row voted on several readings
carries ``verdict_readings`` (each reading's outcome, join and answers, the vote).

Third opinion (``third_model``, Roger 2026-10-02).  The same rows get the second opinion's steps
(1 to 3, no gloss) on a third model, beside the second opinion in waves 4 to 6, recorded as
``third_opinion`` with the second opinion's shape plus ``agree_first`` and ``agree_second``.

Disagreement tripwire (``max_disagreement``, default 0.10).  The opinions' outcomes are known after
wave 5 (the same-sense check adds a note, never changes an outcome), so the tripwire is checked
there, before wave 6: when the first and second models disagree on more than ``max_disagreement``
of the sampled rows, overall or for a source (``split.opinion_source``) with at least
``split.TRIPWIRE_MIN_N`` compared rows, a loud WARNING is logged (``*** HIGH DISAGREEMENT ***``)
and, unless ``accept_disagreement``, :class:`DisagreementStop` is raised before wave 6 sends
anything: every answer paid for is kept, the rows stay ``pending``, and a resume with
``accept_disagreement`` sends wave 6 only.  When wave 6 has nothing left to send the run finishes
and is marked (``tripwire["action"] == "marked"``).  Alignment and descriptors moved from wave 5 to
wave 6 for this on 2026-10-02, so that a stop saves them; the number of waves is unchanged whenever
an opinion has a same-sense check.

Transports.  :class:`LiveTransport` sends each wave's calls at once through the Messages API
(``call_anthropic_json``, ``concurrency`` in flight).  :class:`assistant_axis.gapgen.batches.
BatchTransport` sends each wave as one Message Batch.  Both hand every response to the runner as
it is received, and the runner records it at once (``responses.jsonl``) before parsing it.

Retries.  A call whose answer fails validation (or that returned nothing) is retried once, alone,
in a follow-up wave (``<step>_retry``); the second answer replaces nothing but a failure.

Stops.  A budget stop (``BudgetExceededError`` from a guarded usage) keeps every answer paid for:
live, the call that crossed the cap is recorded and no new call starts; in batches, every result of
the batch that crossed it is recorded.  The error then propagates.  Rows whose path was not
finished stay ``pending`` with what they have in ``meta["split_partial"]``.  ``resume_records``
(the ``responses.jsonl`` of an earlier run of the same batch id) are replayed first: no call is
sent whose answer is already recorded for the same step, prompt hash, model and input.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from assistant_axis.judge import warn_if_low_parse_rate
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage, cost_for_usage

from . import filter_rubric as fr
from . import plain_reading as pr
from . import split
from . import split_rubrics as sr
from .filter import FilterItem, FilterRunner
from .llm import call_anthropic_json
from .registry import utc_now

logger = logging.getLogger(__name__)

#: Haiku 5.5 from 2026-10-08 (coding_plan_haiku55.md, "The switch"; M3 decision 17); Haiku 4.5
#: (``claude-haiku-4-5-20251001``) stays selectable with ``model=`` / ``--model``.
DEFAULT_MODEL = "claude-haiku-5-5"
#: The second opinion (steps 1 to 3 and, for its words, the gloss) and the comparison
#: (Roger, 2026-09-29: "SG, but use Sonnet 5.5"; "I'm inclined to move it").
DEFAULT_SECOND_MODEL = "claude-sonnet-5-5"
DEFAULT_COMPARE_MODEL = "claude-sonnet-5-5"
TEMPERATURE = 0.0
#: max_tokens on the first model (each answer is one short JSON row) and on a model whose
#: thinking cannot be switched off (claude-sonnet-5-5: 2000, as tested 2026-09-29).
MAX_TOKENS_FIRST = {"sense": 1000}
MAX_TOKENS_FIRST_DEFAULT = 500
MAX_TOKENS_THINKING = 2000

#: Measured tokens for each call on Haiku 4.5 (the probe records' usage.json), and the second
#: model's: Haiku's raised by 30%, apart from the kind call, which was measured (955, 59).
#: The comparison and the probe were not measured one item per call; their figures are estimates.
HAIKU_TOKENS: dict[str, tuple[int, int]] = {
    "probe": (420, 70), "sense": (567, 207), "established": (420, 94), "vague": (420, 94), "kind": (718, 78),
    "same_sense": (347, 80), "comparison": (900, 110), "gloss": (490, 44), "alignment": (350, 70),
    "descriptors": (350, 70)}
SECOND_MODEL_MEASURED: dict[str, tuple[int, int]] = {"kind": (955, 59)}
SECOND_MODEL_SCALE = 1.3
#: An Opus model, whatever its role: Haiku's figures times 1.5.  Opus 5.5 ran the whole filter on
#: the audit's 207 words for $8.98 live against $6.06 estimated at Haiku's token counts
#: (opus_audit_m1.md, 2026-10-02), a ratio of 1.48.
OPUS_SCALE = 1.5
#: Haiku 5.5's measured tokens per call (coding_plan_haiku55.md, "The switch", item 4): the means of
#: input and output tokens over every first-attempt call of the step on Haiku 5.5 in h55_split_test_words,
#: h55_m1_validation_pool and h55_verdict_600 (742 to 745 words; output includes the adaptive thinking,
#: which is why it runs two to four times Haiku 4.5's; same_sense from 32 calls).  The comparison was never
#: sent to Haiku 5.5 (it goes to the compare model): Haiku 4.5's figures times the tokenizer factor 1.3.
#: The estimates before 2026-10-08 used Haiku 4.5's figures for 5.5 and under-stated it by about 40%.
HAIKU55_TOKENS: dict[str, tuple[int, int]] = {
    "probe": (413, 107), "sense": (820, 553), "established": (634, 300), "vague": (467, 112),
    "kind": (1018, 103), "same_sense": (428, 140), "comparison": (1170, 143), "gloss": (663, 94),
    "alignment": (780, 176), "descriptors": (480, 243)}
#: Measured tables by model-id fragment, checked before any scaling rule.
MEASURED_TOKENS: dict[str, dict[str, tuple[int, int]]] = {"haiku-5-5": HAIKU55_TOKENS}


def token_source(model: str, first_model: str = DEFAULT_MODEL) -> str:
    """Where :func:`tokens_for` takes ``model``'s figures from, for the dry run's per-model line."""
    m = str(model).lower()
    for frag in MEASURED_TOKENS:
        if frag in m:
            return f"measured on {frag} (h55_split_test_words, h55_m1_validation_pool, h55_verdict_600; thinking included)"
    if "opus" in m:
        return f"Haiku 4.5's measured figures x {OPUS_SCALE}"
    if model == first_model or "haiku" in m:
        return "Haiku 4.5's measured figures (the probe records)"
    return f"Haiku 4.5's figures x {SECOND_MODEL_SCALE} (the kind call measured)"


def tokens_for(step: str, model: str, first_model: str = DEFAULT_MODEL) -> tuple[int, int]:
    """Estimated (input, output) tokens for one call of ``step`` on ``model``: a model with a measured table
    (:data:`MEASURED_TOKENS`, Haiku 5.5) gets its own figures; otherwise Haiku 4.5's, scaled for Opus and for
    a second model."""
    m = str(model).lower()
    for frag, table in MEASURED_TOKENS.items():
        if frag in m:
            return table[step]
    base = HAIKU_TOKENS[step]
    if "opus" in m:
        return int(round(base[0] * OPUS_SCALE)), int(round(base[1] * OPUS_SCALE))
    if model == first_model or "haiku" in m:
        return base
    if step in SECOND_MODEL_MEASURED:
        return SECOND_MODEL_MEASURED[step]
    return int(round(base[0] * SECOND_MODEL_SCALE)), int(round(base[1] * SECOND_MODEL_SCALE))


#: ``readings`` by first-model fragment (coding_plan_haiku55.md, "The switch", item 2: "default 3 when the
#: model is Haiku 5.5, 1 otherwise").
READINGS_BY_MODEL: tuple[tuple[str, int], ...] = (("haiku-5-5", 3),)
#: The first model's steps that a reading repeats (the comparison follows the winning reading only).
VERDICT_STEPS = ("sense", "established", "vague", "kind", "same_sense")


def default_readings(model: str) -> int:
    """How many readings the verdict waves get on ``model`` by default: 3 on Haiku 5.5, else 1."""
    m = str(model).lower()
    return next((n for frag, n in READINGS_BY_MODEL if frag in m), 1)


_CID_RE = re.compile(r"[^A-Za-z0-9_-]")


@dataclass
class Call:
    """One API call: one item, one prompt."""
    step: str                 # probe | sense | established | vague | kind | same_sense | comparison | gloss | ...
    key: str
    label: str
    model: str
    system: str
    user: str
    max_tokens: int
    temperature: Optional[float]
    index: Optional[int] = None   # the reading (0-based) a per-reading call is about
    role: str = "first"           # first | second | third (an opinion's own path)
    retry: bool = False
    rep: int = 0                  # the verdict reading (0-based) of a first-model verdict call; 0 otherwise

    @property
    def stage(self) -> str:
        s = self.step if self.role == "first" else f"{self.role}_{self.step}"
        return s + ("_retry" if self.retry else "")

    @property
    def prompt_sha256(self) -> str:
        return sr.sha256(self.system)

    @property
    def custom_id(self) -> str:
        """``<step>-<role>-<key>-<hash>-<index>``: made of step, key and reading index, within the
        Message Batches limit of 64 characters from ``[A-Za-z0-9_-]``; a verdict reading after the first
        adds its number to the role letter (``f2``, ``f3``), so the readings of one wave differ."""
        h = hashlib.sha256(self.key.encode("utf-8")).hexdigest()[:8]
        k = _CID_RE.sub("_", self.key)[:28]
        r = self.role[0] + (str(self.rep + 1) if self.rep else "")
        return f"{self.step[:11]}-{r}-{k}-{h}-{'x' if self.index is None else self.index}"

    def cache_key(self) -> tuple:
        """``(step, prompt hash, model, user)``, plus the verdict reading after the first: the readings
        send the same request, so on a resume each must find its own answer."""
        return (self.step, self.prompt_sha256, self.model, self.user) + ((self.rep,) if self.rep else ())


def record_cache_key(rec: Mapping) -> tuple:
    """:meth:`Call.cache_key` of a response record (``verdict_reading`` 1 or absent: the first reading)."""
    vr = rec.get("verdict_reading")
    rep = vr - 1 if isinstance(vr, int) and vr > 1 else 0
    return (rec["step"], rec.get("prompt_sha256"), rec.get("model"), rec.get("user")) + ((rep,) if rep else ())


#: Where each role's own path is kept in a word's state: step 1 under ``<prefix>sense``, the
#: same-sense check under ``<prefix>same_sense``, the join under ``<prefix>join``.
ROLE_PREFIX = {"first": "", "second": "so_", "third": "to_"}


def state_prefix(role: str, rep: int = 0) -> str:
    """A path's prefix in the state: the role's, and for a verdict reading after the first ``r<n>_``
    (reading 2 under ``r2_sense``, ``r2_same_sense``); reading 1 keeps the one-reading run's keys."""
    return ROLE_PREFIX[role] + (f"r{rep + 1}_" if rep else "")


def error_key(role: str, step: str, index: Optional[int], rep: int = 0) -> str:
    """The key of a per-reading check's error in ``state["errors"]`` (``first:kind:0``; ``first:kind:0:r2``
    for verdict reading 2)."""
    return f"{role}:{step}:{index}" + (f":r{rep + 1}" if rep else "")
#: The wave the tripwire holds back.
LAST_WAVE = "w6_last_step"


class DisagreementStop(Exception):
    """The disagreement tripwire stopped the run before wave 6; ``tripwire`` is its record."""

    def __init__(self, tripwire: dict):
        self.tripwire = tripwire
        super().__init__(f"first-vs-second disagreement over {tripwire['threshold']:.1%} "
                         f"({', '.join(tripwire['tripped_by'])}); stopped before {tripwire.get('stopped_before')}")


class LiveTransport:
    """Sends a wave's calls through the Messages API, ``concurrency`` at a time."""
    name = "live"

    def __init__(self, runner: "SplitRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: list[Call], on_result: Callable[[Call, Optional[str], dict], None]
                      ) -> None:
        r = self.runner

        async def one(c: Call) -> None:
            r._check_stop()
            async with r._sem:
                r._check_stop()  # the stop may have come while we waited for a slot
                meta: dict = {}
                try:
                    text = await call_anthropic_json(
                        r.client, system=c.system, user=c.user, model=c.model, max_tokens=c.max_tokens,
                        temperature=c.temperature, usage=r.usage, limiter=r.limiter, cache_system=False,
                        meta=meta, **r.retry_kw)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    r._stop_on(exc)
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, text, meta)

        await r._gather([one(c) for c in calls])


class SplitRunner(FilterRunner):
    """The split filter (see the module docstring).  Reuses :class:`FilterRunner`'s preparation
    (floor and WordNet), response log and stop machinery."""

    def __init__(self, *, client, batch_id: str, model: str = DEFAULT_MODEL,
                 second_model: Optional[str] = DEFAULT_SECOND_MODEL, compare_model: Optional[str] = None,
                 usage: Optional[MultiModelUsage] = None, limiter=None, second_opinion_frac: float = 0.10,
                 seed: int = 0, probe: bool = True, second_opinion: bool = True, concurrency: int = 4,
                 zipf_fn=None, wordnet: Any = None, retry_delays: Optional[Sequence[float]] = None,
                 responses_path: Optional[Path] = None, transport: Any = None,
                 resume_records: Optional[Sequence[dict]] = None, rubrics_dir: Optional[Path] = None,
                 plain_reading: bool = True, third_model: Optional[str] = None,
                 max_disagreement: Optional[float] = split.DEFAULT_MAX_DISAGREEMENT,
                 accept_disagreement: bool = False, readings: Optional[int] = None):
        # third_model: the second opinion's steps on a third model, for the same rows (None: none).
        # max_disagreement: the tripwire's threshold (None: not checked; 1.0 never trips).
        # accept_disagreement: a tripped tripwire is recorded and the run goes on.
        # readings: how many independent readings the first model's verdict waves get (None: the
        # model's default, default_readings: 3 on Haiku 5.5, else 1).
        if readings is None:
            readings = default_readings(model)
        if isinstance(readings, bool) or not isinstance(readings, int) or readings < 1:
            raise ValueError(f"readings must be a whole number from 1 up, not {readings!r}")
        self.readings = readings
        super().__init__(client=client, batch_id=batch_id, model=model, second_model=second_model, usage=usage,
                         limiter=limiter, second_opinion_frac=second_opinion_frac, seed=seed, probe=probe,
                         second_opinion=second_opinion, concurrency=concurrency, zipf_fn=zipf_fn, wordnet=wordnet,
                         retry_delays=retry_delays, responses_path=responses_path, plain_reading=plain_reading,
                         compare_model=compare_model or DEFAULT_COMPARE_MODEL)
        if third_model:
            if not self.second_opinion:
                raise ValueError("a third opinion runs on the second opinion's rows: it needs the second opinion")
            if third_model in (model, second_model):
                raise ValueError(f"the third model {third_model!r} must differ from the first and second models")
        self.third_model = third_model or None
        self.max_disagreement = max_disagreement
        self.accept_disagreement = bool(accept_disagreement)
        self.tripwire: Optional[dict] = None
        problems = sr.mismatches(rubrics_dir)
        if problems:
            raise ValueError("split rubric texts are not pinned: " + "; ".join(problems))
        self.prompts = sr.load_all(rubrics_dir)
        self.step_versions = {n: v for n, (v, _) in sr.current_versions(rubrics_dir).items()}
        self.prompt_sha = {n: sr.sha256(t) for n, t in self.prompts.items()}
        self.prompt_sha.update({"probe": sr.sha256(fr.DEFINE_PROBE_PROMPT), "comparison": pr.PROMPT_SHA256["comparison"]})
        self.transport = transport if transport is not None else LiveTransport(self)
        self.state: dict[str, dict] = {}
        self.cache: dict[tuple, dict] = {}
        for rec in resume_records or []:
            self.responses.append(rec)
            if rec.get("text") is not None and not rec.get("parse_errors") and rec.get("step"):
                self.cache[record_cache_key(rec)] = rec
        self.second_keys: list[str] = []
        self.third_keys: list[str] = []

    # -- helpers ----------------------------------------------------------------
    def _system(self, step: str) -> str:
        if step == "probe":
            return fr.DEFINE_PROBE_PROMPT
        if step == "comparison":
            return pr.COMPARISON_PROMPT
        return self.prompts[step]

    def _max_tokens(self, step: str, model: str) -> int:
        from .llm import accepts_temperature
        if not accepts_temperature(model):  # a model whose thinking cannot be switched off
            return MAX_TOKENS_THINKING
        return MAX_TOKENS_FIRST.get(step, MAX_TOKENS_FIRST_DEFAULT)

    def _make(self, step: str, key: str, *, model: str, user: str, index: Optional[int] = None,
              role: str = "first", rep: int = 0) -> Call:
        return Call(step=step, key=key, label=self.state[key]["label"], model=model, system=self._system(step),
                    user=user, max_tokens=self._max_tokens(step, model), temperature=TEMPERATURE, index=index,
                    role=role, rep=rep)

    def _verdict_reading(self, c: Call) -> Optional[int]:
        """The ``verdict_reading`` (1 to N) a record of a run with several readings carries: the reading
        of a first-model verdict call, or of the comparison (the winning reading's); None otherwise."""
        if c.role == "first" and (c.step in VERDICT_STEPS or c.step == "comparison"):
            return c.rep + 1
        return None

    def estimate_usd(self, calls: Sequence[Call], *, batch: bool = False) -> float:
        """Estimated cost of ``calls`` (the token figures of :data:`HAIKU_TOKENS`)."""
        total = 0.0
        for c in calls:
            i, o = tokens_for(c.step, c.model, self.model)
            total += cost_for_usage(c.model + (BATCH_SUFFIX if batch else ""), i, o)
        return total

    # -- one wave -----------------------------------------------------------------
    async def _wave(self, wave: str, calls: list[Call]) -> dict[int, tuple[Optional[dict], Optional[str]]]:
        """Run ``calls`` (answers replayed from ``resume_records`` first), retry each failure once
        alone, and return ``{id(call): (row, error)}`` for the first-try call objects."""
        out: dict[int, tuple[Optional[dict], Optional[str]]] = {}
        if not calls:
            return out

        def handle(c: Call, text: Optional[str], meta: dict, *, resumed: bool = False) -> None:
            row, err = split.parse(c.step, text, label=c.label)
            if text is None and err in (None, "empty response"):
                err = f"no response: {meta.get('error')}"
            if not resumed:
                rec = {"batch_id": self.batch_id, "stage": c.stage, "step": c.step, "role": c.role, "model": c.model,
                       "keys": [c.key], "index": c.index, "user": c.user, "prompt_sha256": c.prompt_sha256,
                       "text": text, "stop_reason": meta.get("stop_reason"), "usage_raw": meta.get("usage_raw"),
                       "attempts": meta.get("attempts"), "error": meta.get("error"),
                       "parse_errors": None, "transport": getattr(self.transport, "name", "live"),
                       "custom_id": c.custom_id, "charged_as": meta.get("charged_as"),
                       "batch_request_id": meta.get("batch_request_id"), "at": utc_now()}
                if self.readings > 1:   # a one-reading run's records keep their old shape
                    rec["verdict_reading"] = self._verdict_reading(c)
                # recorded before it is parsed into the row, so a parser bug keeps the answer
                self.stats[f"calls_{c.stage}"] += 1
                self._record_response(rec)
                rec["parse_errors"] = {c.key: err} if err else {}
                if err is None:
                    self.cache[c.cache_key()] = rec
            out[id(c)] = (row, err)

        first = list(calls)
        await self._send(wave, first, handle)
        failed = [c for c in first if out.get(id(c), (None, "not run"))[1] is not None and id(c) in out]
        for c in first:
            self.stats[f"n:{c.step}:{c.role}:{c.model}"] += 1
            if id(c) in out and out[id(c)][1] is None:
                self.stats[f"ok1:{c.step}:{c.role}:{c.model}"] += 1
        if failed and self._stop is None:
            retries = []
            back = {}
            for c in failed:
                rc = Call(**{**c.__dict__, "retry": True})
                retries.append(rc)
                back[id(rc)] = c
            got: dict[int, tuple] = {}

            def handle_retry(c: Call, text: Optional[str], meta: dict, *, resumed: bool = False) -> None:
                handle(c, text, meta, resumed=resumed)
                got[id(c)] = out.pop(id(c))

            await self._send(wave + "_retry", retries, handle_retry)
            for rid, res in got.items():
                if res[1] is None:
                    out[id(back[rid])] = res
                else:  # keep the first error with the retry's
                    first_err = out[id(back[rid])][1]
                    out[id(back[rid])] = (None, f"{first_err}; retry: {res[1]}")
        for c in first:
            if id(c) in out and out[id(c)][1] is None:
                self.stats[f"ok:{c.step}:{c.role}:{c.model}"] += 1
        # a stop is not raised here: the caller applies the answers received, then raises it
        return out

    async def _send(self, wave: str, calls: list[Call], handle) -> None:
        to_send = []
        for c in calls:
            rec = self.cache.get(c.cache_key()) if not c.retry else None
            if rec is not None:
                self.stats["resumed"] += 1
                handle(c, rec["text"], {"stop_reason": rec.get("stop_reason")}, resumed=True)
            else:
                to_send.append(c)
        if not to_send or self._stop is not None:
            return
        try:
            await self.transport.execute(wave, to_send, lambda c, t, m: handle(c, t, m))
        except BaseException as exc:  # noqa: BLE001 - kept as the stop; raised once the answers are applied
            self._stop_on(exc)

    # -- the path -------------------------------------------------------------------
    def _sense(self, key: str, role: str = "first", rep: int = 0) -> Optional[dict]:
        """Step 1's answer of ``role`` (and verdict reading ``rep``) for ``key``, or None."""
        return self.state[key].get(state_prefix(role, rep) + "sense")

    def _reading(self, key: str, i: int, role: str = "first", rep: int = 0) -> dict:
        return self._sense(key, role, rep)["readings"][i]

    def _winner(self, key: str) -> int:
        """The verdict reading (0-based) whose answers are the row's: the vote's winner, 0 before the vote
        and in a one-reading run."""
        return ((self.state[key].get("vote") or {}).get("winner")) or 0

    def _path_calls(self, keys: Sequence[str], step: str, *, role: str, model: str, rep: int = 0) -> list[Call]:
        """Wave 2 (``step`` established / vague / kind) for every primary reading of ``keys``."""
        calls = []
        for k in keys:
            s = self._sense(k, role, rep)
            if not s:
                continue
            for i in split.primary_indices(s):
                x = s["readings"][i]
                user = (split.payload("established", label=s_label(self.state[k]), first_thought=s.get("first_thought"),
                                      reading=x["reading"]) if step == "established"
                        else split.payload(step, label=s_label(self.state[k]), reading=x["reading"]))
                calls.append(self._make(step, k, model=model, user=user, index=i, role=role, rep=rep))
        return calls

    def _sense_calls(self, keys: Sequence[str], *, role: str, model: str, reps: Sequence[int] = (0,)) -> list[Call]:
        """Step 1 for ``keys`` on ``model``, once for each verdict reading in ``reps`` (each word's readings
        side by side)."""
        return [self._make("sense", k, model=model, user=split.payload("sense", label=s_label(self.state[k])),
                           role=role, rep=r) for k in keys for r in reps]

    def _apply_sense(self, calls: Sequence[Call], res: Mapping[int, tuple]) -> None:
        for c in calls:
            if id(c) not in res:
                continue
            row, err = res[id(c)]
            sense_key = state_prefix(c.role, c.rep) + "sense"
            if row is not None:
                self.state[c.key][sense_key] = {k: v for k, v in row.items() if k != "label"}
            else:
                self.state[c.key]["errors"][sense_key] = err

    def _check_calls(self, keys: Sequence[str], *, role: str, model: str, rep: int = 0) -> list[Call]:
        """Step 2 (established, vague and kind) for every primary reading of ``keys``."""
        calls = []
        for step in ("established", "vague", "kind"):
            calls += self._path_calls(keys, step, role=role, model=model, rep=rep)
        return calls

    def _apply_checks(self, calls: Sequence[Call], res: Mapping[int, tuple]) -> None:
        field_of = {"established": "check_established", "vague": "check_vague", "kind": "kind_call"}
        for c in calls:
            if id(c) not in res:
                continue
            row, err = res[id(c)]
            if row is not None:
                self._reading(c.key, c.index, c.role, c.rep)[field_of[c.step]] = row
            else:
                self.state[c.key]["errors"][error_key(c.role, c.step, c.index, c.rep)] = err

    def _complete(self, key: str, role: str = "first", rep: int = 0) -> Optional[str]:
        """None when every primary reading has its established and kind answers; else why not."""
        sense_key = state_prefix(role, rep) + "sense"
        s = self.state[key].get(sense_key)
        if not s:
            return self.state[key]["errors"].get(sense_key) or "no sense answer"
        for i in split.primary_indices(s):
            x = s["readings"][i]
            if not x.get("check_established") or not x.get("kind_call"):
                est = self.state[key]["errors"].get(error_key(role, "established", i, rep))
                kd = self.state[key]["errors"].get(error_key(role, "kind", i, rep))
                return f"reading {i + 1}: established {est or 'ok'}, kind {kd or 'ok'}"
        return None

    def _same_sense_call(self, key: str, *, role: str, model: str, rep: int = 0) -> Optional[Call]:
        s = self._sense(key, role, rep)
        pair = split.same_sense_pair(s)
        if not pair:
            return None
        a, b = pair
        return self._make("same_sense", key, model=model, role=role, index=a, rep=rep,
                          user=split.payload("same_sense", label=s_label(self.state[key]),
                                             reading=s["readings"][a]["reading"],
                                             reading_2=s["readings"][b]["reading"]))

    def _wave3_calls(self, keys: Sequence[str], *, role: str, model: str) -> list[Call]:
        """Same sense (every role; for the first role, once for each verdict reading that completed) and, for
        the first role only, the comparison, on the winning reading's readings."""
        calls = []
        for k in keys:
            reps = ([r for r in range(self.readings) if self._complete(k, role, r) is None]
                    if role == "first" else [0])
            for r in reps:
                c = self._same_sense_call(k, role=role, model=model, rep=r)
                if c is not None:
                    calls.append(c)
            if role == "first" and self.plain_reading and self.state[k].get("intended"):
                w = self._winner(k)
                s = self._sense(k, role, w)
                for i in split.survivors(s):
                    calls.append(self._make("comparison", k, model=self.compare_model, index=i, rep=w,
                                            user=split.comparison_payload(label=s_label(self.state[k]),
                                                                          reading=s["readings"][i]["reading"],
                                                                          intended=self.state[k]["intended"])))
        return calls

    def _apply_wave3(self, calls: Sequence[Call], res: Mapping[int, tuple]) -> None:
        for c in calls:
            if id(c) not in res:
                continue
            row, err = res[id(c)]
            st = self.state[c.key]
            if c.step == "same_sense":
                p = state_prefix(c.role, c.rep)
                pair = split.same_sense_pair(st[p + "sense"])
                st[p + "same_sense"] = (
                    {**row, "readings": [pair[0] + 1, pair[1] + 1], "model": c.model} if row is not None
                    else {"error": err, "readings": [pair[0] + 1, pair[1] + 1], "model": c.model})
            else:
                st["comparison"][c.index] = row if row is not None else {"error": err}

    async def _run_wave3(self, keys: list[str], *, role: str, model: str, wave: str) -> None:
        calls = self._wave3_calls(keys, role=role, model=model)
        res = await self._wave(wave, calls)
        self._apply_wave3(calls, res)
        self._check_stop()

    def _join(self, key: str, role: str = "first", rep: int = 0) -> dict:
        """The join of ``role``'s path (for the first role, of verdict reading ``rep``); the comparison
        counts on the winning reading only, the one it was asked about."""
        st = self.state[key]
        p = state_prefix(role, rep)
        if role == "first":
            comps = None
            if (rep == self._winner(key) and self.plain_reading and st.get("intended")
                    and st["comparison"] is not None):
                comps = {i: (st["comparison"].get(i) or {}).get("relation") for i in split.survivors(st[p + "sense"])}
            return split.join(st[p + "sense"], (st.get(p + "same_sense") or {}).get("relation"), comps)
        return split.join(st[p + "sense"], (st.get(p + "same_sense") or {}).get("relation"))

    # -- the verdict readings ------------------------------------------------------------
    def _vote(self, key: str) -> Optional[dict]:
        """The vote over the verdict readings of ``key`` after wave 2 (each complete reading's outcome; the
        same-sense check and the comparison never change an outcome), stored as ``state["vote"]``; None,
        with ``state["failed"]`` set, when no reading completed.  With one reading this is that reading."""
        st = self.state[key]
        whys = [self._complete(key, "first", r) for r in range(self.readings)]
        if all(w is not None for w in whys):
            st["failed"] = whys[0] if self.readings == 1 else "; ".join(
                f"verdict reading {r + 1}: {w}" for r, w in enumerate(whys))
            return None
        outs = [split.join(self._sense(key, "first", r))["outcome"] if whys[r] is None else None
                for r in range(self.readings)]
        v = split.combine_readings(outs)
        v["why_failed"] = {str(r + 1): w for r, w in enumerate(whys) if w is not None}
        st["vote"] = v
        return v

    def _final_joins(self, key: str) -> dict:
        """Every complete reading's join after wave 3 (``vote["joins"]``, None for a reading that failed), and
        the row's join: the winning reading's, whose outcome must be the vote's."""
        st = self.state[key]
        v = st["vote"]
        joins = [self._join(key, "first", r) if self._complete(key, "first", r) is None else None
                 for r in range(self.readings)]
        v["joins"] = joins
        j = joins[v["winner"]]
        if j["outcome"] != v["outcome"]:   # cannot happen: wave 3 adds notes and may move the accepted reading
            raise RuntimeError(f"{key}: the winning reading's join says {j['outcome']!r} after wave 3, the vote "
                               f"{v['outcome']!r}")
        return j

    def _readings_block(self, key: str) -> Optional[dict]:
        """The row's ``verdict_readings`` (a run with several readings): the rule, the vote, and each
        reading's outcome, join and answers (or why it failed)."""
        if self.readings == 1:
            return None
        st = self.state[key]
        v = st.get("vote")
        if not v:
            return None
        per = []
        for r in range(self.readings):
            p = state_prefix("first", r)
            j = (v.get("joins") or [None] * self.readings)[r]
            if j is None:
                per.append({"reading": r + 1, "error": v["why_failed"].get(str(r + 1))})
                continue
            s = st.get(p + "sense") or {}
            per.append({"reading": r + 1, "outcome": j["outcome"], "cause": j.get("cause"), "rule": j.get("rule"),
                        "accepted": j.get("accepted"),
                        "accepted_reading": None if j.get("accepted_index") is None else j["accepted_index"] + 1,
                        "kind": j.get("kind"), "membership_kind": j.get("membership_kind"), "notes": j.get("notes"),
                        "same_sense": (st.get(p + "same_sense") or {}).get("relation"),
                        "sense": {k: s.get(k) for k in ("note", "first_thought", "first_thought_said_of", "usable")}
                        | {"readings": split.block_readings(s)}})
        return {"n": self.readings, "rule": split.READINGS_RULE, "outcome": v["outcome"], "how": v["how"],
                "winner": v["winner"] + 1, "outcomes": v["outcomes"], "n_turned_away": v["n_turned_away"],
                "unanimous": v["unanimous"], "rescued": v["rescued"], "failed": [r + 1 for r in v["failed"]],
                "per_reading": per}

    def readings_summary(self) -> dict:
        """The summary's ``readings`` section (:func:`split.readings_summary`) over the words voted on."""
        votes = [{**st["vote"], "label": st["label"]} for st in self.state.values() if st.get("vote")]
        return split.readings_summary(votes, n_readings=self.readings)

    def _opinions(self) -> list[tuple[str, str, list[str]]]:
        """``(role, model, keys)`` of each opinion this run asks: the second, and the third when set."""
        out = []
        if self.second_keys:
            out.append(("second", self.second_model, self.second_keys))
        if self.third_keys:
            out.append(("third", self.third_model, self.third_keys))
        return out

    def _join_opinions(self) -> None:
        """Each opinion's join (or why it could not be made) for each of its words."""
        for role, _, keys in self._opinions():
            p = ROLE_PREFIX[role]
            for k in keys:
                why = self._complete(k, role)
                self.state[k][p + "join"] = self._join(k, role) if why is None else {"error": why}

    def select_second_opinion(self, keys: Sequence[str]) -> list[str]:
        """A seeded ``second_opinion_frac`` of the words that reached step 1, plus every word with the note
        ``obvious_sense_not_trait`` or ``most_likely_reading_stretched`` (section 6).  Sorted."""
        reached = sorted(k for k in keys if any(self._sense(k, "first", r) is not None for r in range(self.readings)))
        chosen = {k for k in reached if self.state[k].get("join") and
                  {"obvious_sense_not_trait", "most_likely_reading_stretched"} & set(self.state[k]["join"]["notes"])}
        n = int(round(self.second_opinion_frac * len(reached)))
        if n:
            chosen |= set(random.Random(self.seed).sample(reached, min(n, len(reached))))
        return sorted(chosen)

    # -- run ----------------------------------------------------------------------------
    async def run_async(self, items: Sequence[FilterItem]):
        self._sem = asyncio.Semaphore(self.concurrency)
        self._stop = None
        self._intended = {it.key: it.intended_sense for it in items}
        for it in items:
            self.state[it.key] = {"label": it.label, "intended": it.intended_sense, "sense": None, "so_sense": None,
                                  "to_sense": None, "same_sense": None, "so_same_sense": None, "to_same_sense": None,
                                  "comparison": {}, "gloss": None, "gloss_model": None, "alignment": None,
                                  "descriptors": None, "join": None, "so_join": None, "to_join": None, "probe": None,
                                  "errors": {}, "cut": None, "vote": None}
            for r in range(1, self.readings):   # verdict readings 2 to N
                self.state[it.key].update({state_prefix("first", r) + "sense": None,
                                           state_prefix("first", r) + "same_sense": None})
        todo = self.prepare(items)
        self.stats["n_llm"] += len(todo)
        try:
            await self._run(todo)
        finally:
            self._finish_rows(items)
        return [self.results[it.key] for it in items]

    async def _run(self, todo: list[FilterItem]) -> None:
        # wave 0: the definition probe, one word per call
        if self.probe:
            band = [it for it in todo if self.results[it.key].freq.get("probe_band")]
            calls = [self._make("probe", it.key, model=self.model,
                                user=fr.build_probe_prompt([{"id": 1, "label": it.label}])) for it in band]
            self.stats["n_probe"] += len(calls)
            res = await self._wave("w0_probe", calls)
            for c in calls:
                if id(c) in res:
                    self._apply_split_probe(c.key, *res[id(c)])
            self._check_stop()
        keys = [it.key for it in todo if self.state[it.key]["cut"] is None]
        reps = range(self.readings)
        # wave 1: step 1, once for each verdict reading
        calls = self._sense_calls(keys, role="first", model=self.model, reps=reps)
        res = await self._wave("w1_sense", calls)
        self._apply_sense(calls, res)
        self._check_stop()
        # wave 2: the checks of every reading that has its step 1
        calls = []
        for r in reps:
            calls += self._check_calls([k for k in keys if self._sense(k, "first", r)], role="first",
                                       model=self.model, rep=r)
        res = await self._wave("w2_checks", calls)
        self._apply_checks(calls, res)
        self._check_stop()
        # the vote: each complete reading's outcome is known here
        ready = [k for k in keys if self._vote(k) is not None]
        # wave 3: the same-sense check of every complete reading; the comparison on the winning reading
        await self._run_wave3(ready, role="first", model=self.model, wave="w3_same_sense")
        for k in ready:
            self.state[k]["join"] = self._final_joins(k)
        self.second_keys = self.select_second_opinion(ready) if self.second_opinion else []
        self.third_keys = list(self.second_keys) if self.third_model else []
        self.stats["second_opinion_n"] = len(self.second_keys)
        self.stats["third_opinion_n"] = len(self.third_keys)
        so = set(self.second_keys)
        # wave 4: gloss (outcome trait), and the opinions' step 1
        gloss_calls = []
        for k in ready:
            j = self.state[k]["join"]
            if j["outcome"] != "trait":
                continue
            m = self.second_model if k in so else self.model
            gloss_calls.append(self._make("gloss", k, model=m, index=j["accepted_index"],
                                          user=split.payload("gloss", label=s_label(self.state[k]),
                                                             reading=j["accepted"])))
        op_sense = [self._make("sense", k, model=model, role=role,
                               user=split.payload("sense", label=s_label(self.state[k])))
                    for role, model, keys in self._opinions() for k in keys]
        res = await self._wave("w4_gloss", gloss_calls + op_sense)
        for c in gloss_calls:
            if id(c) in res:
                row, err = res[id(c)]
                st = self.state[c.key]
                st["gloss"], st["gloss_model"] = (row if row is not None else {"error": err}), c.model
        self._apply_sense(op_sense, res)
        self._check_stop()
        # wave 5: the opinions' checks; their outcomes are then known (the same-sense check of wave 6
        # adds a note and never changes an outcome), so the tripwire is checked here
        op_checks = []
        for role, model, keys in self._opinions():
            op_checks += self._check_calls([k for k in keys if self._sense(k, role)], role=role, model=model)
        res = await self._wave("w5_opinion_checks", op_checks)
        self._apply_checks(op_checks, res)
        self._check_stop()
        self._join_opinions()
        # wave 6: alignment and descriptors on the gloss; the opinions' same-sense checks
        last = []
        for k in ready:
            g = (self.state[k].get("gloss") or {}).get("gloss")
            if g:
                for step in ("alignment", "descriptors"):
                    last.append(self._make(step, k, model=self.model,
                                           user=split.payload(step, label=s_label(self.state[k]), description=g)))
        op_same = []
        for role, model, keys in self._opinions():
            op_same += self._wave3_calls([k for k in keys if self._complete(k, role) is None], role=role, model=model)
        self._tripwire_gate(last + op_same)
        res = await self._wave(LAST_WAVE, last + op_same)
        for c in last:
            if id(c) in res:
                row, err = res[id(c)]
                self.state[c.key][c.step] = row if row is not None else {"error": err}
        self._apply_wave3(op_same, res)
        self._check_stop()
        self._join_opinions()   # again, with the same-sense notes
        for role, _, keys in self._opinions():
            for k in keys:
                oj = self.state[k][ROLE_PREFIX[role] + "join"]
                if "error" in oj:
                    self.stats[f"{role}_opinion_failed"] += 1
                elif oj["outcome"] != self.state[k]["join"]["outcome"]:
                    self.stats["disagreements" if role == "second" else "third_disagreements"] += 1
        self.stats["done"] = 1

    # -- the disagreement tripwire ------------------------------------------------------
    def opinion_rows(self) -> list[dict]:
        """One row for each word with a second opinion (``split``'s opinion rows): its source, the
        first model's outcome and each opinion's (None where the opinion failed or is not in yet)."""
        out = []
        for k in self.second_keys:
            st = self.state[k]
            field, groups = split.opinion_source(self.results[k].meta)

            def outcome(role: str) -> Optional[str]:
                j = st.get(ROLE_PREFIX[role] + "join") or {}
                return None if "error" in j else j.get("outcome")
            out.append({"label": st["label"], "key": k, "source_field": field, "groups": groups,
                        "first": (st.get("join") or {}).get("outcome"), "second": outcome("second"),
                        "third": outcome("third") if k in self.third_keys else None,
                        "third_run": k in self.third_keys})
        return out

    def agreement(self) -> dict:
        """The summary's agreement section (``split.agreement_section``) on this run's opinion rows."""
        return split.agreement_section(self.opinion_rows(), models={
            "first": self.model, "second": self.second_model, "third": self.third_model})

    def _tripwire_gate(self, next_calls: Sequence[Call]) -> None:
        """Check the tripwire once the opinions' outcomes are known; record it in ``self.tripwire``,
        log it, and raise :class:`DisagreementStop` when it trips, the override is not given and
        ``next_calls`` (wave 6) holds a call not already answered on record."""
        if self.max_disagreement is None or not self.second_keys:
            return
        tw = split.disagreement_tripwire(self.opinion_rows(), threshold=self.max_disagreement)
        tw.update(models={"first": self.model, "second": self.second_model}, accepted=self.accept_disagreement,
                  action=None, stopped_before=None, calls_not_sent=0, checked_at=utc_now())
        unpaid = [c for c in next_calls if c.cache_key() not in self.cache]
        if tw["tripped"]:
            if self.accept_disagreement:
                tw["action"] = "accepted"
            elif unpaid:
                tw.update(action="stopped", stopped_before=LAST_WAVE, calls_not_sent=len(unpaid))
            else:
                tw["action"] = "marked"
        self.tripwire = tw
        log_tripwire(tw, logger, label=f"traithood_filter:split:{self.batch_id}")
        if tw["action"] == "stopped":
            raise DisagreementStop(tw)

    def _apply_split_probe(self, key: str, row: Optional[dict], err: Optional[str]) -> None:
        res = self.results[key]
        if row is None:
            self.stats["probe_failed"] += 1
            res.freq["define_probe"] = {"model": self.model, "error": err}
            return
        res.freq["define_probe"] = {"model": self.model, "rubric_version": fr.PROBE_RUBRIC_VERSION,
                                    "known": row["known"], "definition": row["definition"],
                                    "reason": row["reason"], "prompt_sha256": self.prompt_sha["probe"],
                                    "one_item_per_call": True}
        if not row["known"]:
            self.stats["probe_unknown"] += 1
            self.state[key]["cut"] = "probe"

    # -- rows ------------------------------------------------------------------------------
    def _opinion_block(self, key: str, role: str = "second") -> Optional[dict]:
        """The row's ``second_opinion`` or ``third_opinion``: the opinion's outcome and readings, and
        ``agree`` (with the first model's outcome); the third also says ``agree_first`` (the same as
        its ``agree``) and ``agree_second`` (None when the second opinion failed)."""
        keys, model = (self.second_keys, self.second_model) if role == "second" else (self.third_keys, self.third_model)
        if key not in keys:
            return None
        st, p = self.state[key], ROLE_PREFIX[role]
        sj = st.get(p + "join")
        if not sj:
            return None
        if "error" in sj:
            return {"model": model, "error": sj["error"]}
        block = {"model": model, "outcome": sj["outcome"], "accepted": sj["accepted"],
                 "cause": sj["cause"], "notes": sj["notes"], "agree": sj["outcome"] == st["join"]["outcome"],
                 "same_sense": (st.get(p + "same_sense") or {}).get("relation"),
                 "sense": {k: (st[p + "sense"] or {}).get(k) for k in ("note", "first_thought",
                                                                       "first_thought_said_of", "usable")}
                 | {"readings": split.block_readings(st[p + "sense"] or {})}}
        if role == "third":
            so = st.get("so_join") or {}
            block["agree_first"] = block["agree"]
            block["agree_second"] = None if (not so or "error" in so) else sj["outcome"] == so["outcome"]
        return block

    def _second_block(self, key: str) -> Optional[dict]:
        return self._opinion_block(key, "second")

    def _comparison_block(self, key: str) -> Optional[dict]:
        st = self.state[key]
        sense = self._sense(key, "first", self._winner(key))   # the comparison was asked of the winning reading
        if not (self.plain_reading and st.get("intended")) or sense is None:
            return None
        per = []
        for i in split.survivors(sense):
            c = st["comparison"].get(i) or {"error": "not run"}
            per.append({"reading_index": i + 1, **c})
        return {"intended_meaning": st["intended"], "model": self.compare_model,
                "rubric_version": pr.COMPARISON_VERSION, "prompt_sha256": pr.PROMPT_SHA256["comparison"],
                "one_item_per_call": True, "per_reading": per, "effect": (st.get("join") or {}).get("comparison_effect")}

    def _finish_rows(self, items: Sequence[FilterItem]) -> None:
        """Build the filter block of every row whose path is finished; the rest stay pending with
        what they have in ``meta["split_partial"]`` (a stop, or a run cut short)."""
        now = utc_now()
        finished = bool(self.stats.get("done"))
        for it in items:
            res, st = self.results[it.key], self.state[it.key]
            if res.stage == "hard_reject":
                res.filter = split.floor_block(why=res.filter["reason"], rule="floor", model=None,
                                               batch_id=self.batch_id, now=now, step_versions=self.step_versions,
                                               prompt_sha256=self.prompt_sha)
                continue
            if st["cut"] == "probe":
                d = res.freq.get("define_probe") or {}
                res.stage, res.error = "classified", None
                res.filter = split.floor_block(why=f"Definition probe: word not known. {d.get('reason') or ''}".strip(),
                                               rule="probe", model=self.model, batch_id=self.batch_id, now=now,
                                               step_versions=self.step_versions, prompt_sha256=self.prompt_sha)
                continue
            j = st.get("join")
            failed_why = st.get("failed") or self._step1_failed(st)
            if failed_why:  # a step 1 or step 2 answer failed validation twice: the join cannot be made
                res.stage, res.error = "failed", failed_why
                res.meta["split_partial"] = _partial(st)
                continue
            if not finished or j is None:  # a stop: the path is not finished
                res.stage = "pending"
                res.meta["split_partial"] = _partial(st)
                continue
            g = st.get("gloss") or {}
            p = state_prefix("first", self._winner(it.key))   # the winning verdict reading's answers
            block, gloss, holding, et = split.to_filter_block(
                sense=st[p + "sense"], j=j, model=self.model, batch_id=self.batch_id, now=now,
                step_versions=self.step_versions, prompt_sha256=self.prompt_sha, same_sense=st.get(p + "same_sense"),
                comparison=self._comparison_block(it.key), gloss_model=st.get("gloss_model"),
                alignment=st.get("alignment") if "error" not in (st.get("alignment") or {}) else None,
                descriptors=st.get("descriptors") if "error" not in (st.get("descriptors") or {}) else None,
                second_opinion=self._second_block(it.key), gloss=g.get("gloss"),
                third_opinion=self._opinion_block(it.key, "third"))
            errs = {k: (st.get(k) or {}).get("error") for k in ("gloss", "alignment", "descriptors")
                    if (st.get(k) or {}).get("error")}
            if errs:
                block["last_step_errors"] = errs
            vr = self._readings_block(it.key)
            if vr is not None:
                block["verdict_readings"] = vr
            res.stage, res.error = "classified", None
            res.filter, res.gloss, res.holding, res.entity_type = block, gloss, holding, et

    def _step1_failed(self, st: Mapping) -> Optional[str]:
        """Why a row failed at step 1, when no verdict reading has its answer and every one failed validation
        twice; None when some reading has it or one was never sent (a stop: the row stays pending)."""
        errs = []
        for r in range(self.readings):
            p = state_prefix("first", r)
            if st.get(p + "sense") is not None:
                return None
            errs.append(st["errors"].get(p + "sense"))
        if not all(errs):
            return None
        return errs[0] if self.readings == 1 else "; ".join(f"verdict reading {r + 1}: {e}" for r, e in enumerate(errs))

    # -- reporting ------------------------------------------------------------------------------
    def parse_counts(self) -> tuple[int, int]:
        n = self.stats["n_llm"]
        ok = sum(1 for r in self.results.values() if r.stage == "classified")
        return ok, n

    def step_parse_rates(self) -> dict[str, dict]:
        """``{"<step>:<role>:<model>": {"n", "ok_first_pass", "ok"}}`` over every call asked."""
        out = {}
        for k, v in sorted(self.stats.items()):
            if k.startswith("n:"):
                name = k[2:]
                out[name] = {"n": v, "ok_first_pass": self.stats.get(f"ok1:{name}", 0), "ok": self.stats.get(f"ok:{name}", 0)}
        return out

    def warn_parse_rate(self, logger_obj=None) -> None:
        log = logger_obj or logger
        for name, d in self.step_parse_rates().items():
            warn_if_low_parse_rate(label=f"traithood_filter:split:{name}", n_ok=d["ok"], n_total=d["n"], logger_obj=log)


def s_label(st: Mapping) -> str:
    return st["label"]


def log_tripwire(tw: Mapping, log: logging.Logger, *, label: str) -> None:
    """The tripwire in the log, in the style of the parse-rate alert: a ``*** HIGH DISAGREEMENT ***``
    WARNING for each rate over the threshold (all sampled rows, or one source), naming the source, the
    counts, the rate and the threshold; an INFO line for each rate within it or on too few rows; then
    what the run does about it."""
    thr, min_n = tw["threshold"], tw["min_n"]
    models = tw.get("models") or {}
    pair = f"{models.get('first')} vs {models.get('second')}" if models else "first vs second"
    named = [("all sampled rows", tw["overall"])] + [(f"{tw['source_field']} {g}", s)
                                                     for g, s in tw["by_source"].items()]
    for name, s in named:
        if not s["n"]:
            continue
        body = (f"[{label}] {name}: first-vs-second disagreement {s['disagree']}/{s['n']} = {s['rate']:.1%} "
                f"(threshold {thr:.1%}; {pair})")
        if s["over"]:
            log.warning(f"*** HIGH DISAGREEMENT *** {body}")
        elif not s["eligible"]:
            log.info(f"{body}; fewer than {min_n} sampled rows: reported, never trips")
        else:
            log.info(body)
    action = tw.get("action")
    if action == "stopped":
        log.warning(f"*** HIGH DISAGREEMENT *** [{label}] the run stops before {tw['stopped_before']} "
                    f"({tw['calls_not_sent']} calls not sent); every answer paid for is kept.  To go on "
                    f"regardless: --resume --accept-disagreement")
    elif action == "marked":
        log.warning(f"*** HIGH DISAGREEMENT *** [{label}] nothing is left to send: the run finishes, marked as "
                    f"tripped (the CLI exits non-zero)")
    elif action == "accepted":
        log.warning(f"*** HIGH DISAGREEMENT *** [{label}] accepted (--accept-disagreement): the run goes on")


def _partial(st: Mapping) -> dict:
    """What a row has so far, for ``meta["split_partial"]``."""
    keep = ("sense", "same_sense", "gloss", "gloss_model", "alignment", "descriptors", "join", "so_sense",
            "so_same_sense", "so_join", "to_sense", "to_same_sense", "to_join", "errors", "failed")
    keep += tuple(sorted(k for k in st if re.match(r"^r\d+_(sense|same_sense)$", k)))   # verdict readings 2 to N
    out = {k: st.get(k) for k in keep if st.get(k)}
    if st.get("vote") and len(st["vote"]["outcomes"]) > 1:   # a vote over several readings
        out["vote"] = st["vote"]
    if st.get("comparison"):
        out["comparison"] = {str(i): v for i, v in st["comparison"].items()}
    return out
