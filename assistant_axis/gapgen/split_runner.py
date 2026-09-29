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
      second opinion, step 1 on the second model
5     alignment and descriptors on the gloss; second opinion, established / vague / kind
6     second opinion, same sense
====  =========================================================================================

The words for a second opinion are chosen after wave 3, from the join, so wave 4 knows which model
writes each gloss: a seeded ``second_opinion_frac`` of the words that reached step 1, plus every
word with the note ``obvious_sense_not_trait`` or ``most_likely_reading_stretched``.  The first
model's outcome stays the outcome; agreement means the same outcome.  The second model's gloss is
written for the row's accepted reading.  (The plan's table lists the second opinion's three steps
in wave 4; they depend on each other, so they run in waves 4 to 6.)

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

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
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


def tokens_for(step: str, model: str, first_model: str = DEFAULT_MODEL) -> tuple[int, int]:
    """Estimated (input, output) tokens for one call of ``step`` on ``model``."""
    base = HAIKU_TOKENS[step]
    if model == first_model or "haiku" in model:
        return base
    if step in SECOND_MODEL_MEASURED:
        return SECOND_MODEL_MEASURED[step]
    return int(round(base[0] * SECOND_MODEL_SCALE)), int(round(base[1] * SECOND_MODEL_SCALE))


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
    role: str = "first"           # first | second (the second opinion's own path)
    retry: bool = False

    @property
    def stage(self) -> str:
        s = self.step if self.role == "first" else f"second_{self.step}"
        return s + ("_retry" if self.retry else "")

    @property
    def prompt_sha256(self) -> str:
        return sr.sha256(self.system)

    @property
    def custom_id(self) -> str:
        """``<step>-<role>-<key>-<hash>-<index>``: made of step, key and reading index, within the
        Message Batches limit of 64 characters from ``[A-Za-z0-9_-]``."""
        h = hashlib.sha256(self.key.encode("utf-8")).hexdigest()[:8]
        k = _CID_RE.sub("_", self.key)[:28]
        return f"{self.step[:11]}-{self.role[0]}-{k}-{h}-{'x' if self.index is None else self.index}"

    def cache_key(self) -> tuple[str, str, str, str]:
        return (self.step, self.prompt_sha256, self.model, self.user)


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
                 plain_reading: bool = True):
        super().__init__(client=client, batch_id=batch_id, model=model, second_model=second_model, usage=usage,
                         limiter=limiter, second_opinion_frac=second_opinion_frac, seed=seed, probe=probe,
                         second_opinion=second_opinion, concurrency=concurrency, zipf_fn=zipf_fn, wordnet=wordnet,
                         retry_delays=retry_delays, responses_path=responses_path, plain_reading=plain_reading,
                         compare_model=compare_model or DEFAULT_COMPARE_MODEL)
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
                self.cache[(rec["step"], rec.get("prompt_sha256"), rec.get("model"), rec.get("user"))] = rec
        self.second_keys: list[str] = []

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
              role: str = "first") -> Call:
        return Call(step=step, key=key, label=self.state[key]["label"], model=model, system=self._system(step),
                    user=user, max_tokens=self._max_tokens(step, model), temperature=TEMPERATURE, index=index,
                    role=role)

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
    def _reading(self, key: str, i: int, role: str = "first") -> dict:
        s = self.state[key]["sense" if role == "first" else "so_sense"]
        return s["readings"][i]

    def _path_calls(self, keys: Sequence[str], step: str, *, role: str, model: str) -> list[Call]:
        """Wave 2 (``step`` established / vague / kind) for every primary reading of ``keys``."""
        calls = []
        for k in keys:
            s = self.state[k]["sense" if role == "first" else "so_sense"]
            if not s:
                continue
            for i in split.primary_indices(s):
                x = s["readings"][i]
                user = (split.payload("established", label=s_label(self.state[k]), first_thought=s.get("first_thought"),
                                      reading=x["reading"]) if step == "established"
                        else split.payload(step, label=s_label(self.state[k]), reading=x["reading"]))
                calls.append(self._make(step, k, model=model, user=user, index=i, role=role))
        return calls

    async def _run_path(self, keys: list[str], *, role: str, model: str, wave_prefix: str) -> None:
        """Steps 1 and 2 of the path for ``keys`` on ``model`` (``role`` first or second)."""
        sense_key = "sense" if role == "first" else "so_sense"
        calls = [self._make("sense", k, model=model, user=split.payload("sense", label=s_label(self.state[k])),
                            role=role) for k in keys]
        res = await self._wave(f"{wave_prefix}sense", calls)
        for c in calls:
            row, err = res.get(id(c), (None, "not run"))
            if row is not None:
                row = {k: v for k, v in row.items() if k != "label"}
                self.state[c.key][sense_key] = row
            elif id(c) in res:
                self.state[c.key]["errors"][sense_key] = err
        self._check_stop()

    async def _run_checks(self, keys: list[str], *, role: str, model: str, wave: str) -> None:
        calls = []
        for step in ("established", "vague", "kind"):
            calls += self._path_calls(keys, step, role=role, model=model)
        res = await self._wave(wave, calls)
        field_of = {"established": "check_established", "vague": "check_vague", "kind": "kind_call"}
        for c in calls:
            row, err = res.get(id(c), (None, "not run"))
            x = self._reading(c.key, c.index, role)
            if row is not None:
                x[field_of[c.step]] = row
            elif id(c) in res:
                self.state[c.key]["errors"][f"{c.role}:{c.step}:{c.index}"] = err
        self._check_stop()

    def _complete(self, key: str, role: str = "first") -> Optional[str]:
        """None when every primary reading has its established and kind answers; else why not."""
        s = self.state[key]["sense" if role == "first" else "so_sense"]
        if not s:
            return self.state[key]["errors"].get("sense" if role == "first" else "so_sense") or "no sense answer"
        for i in split.primary_indices(s):
            x = s["readings"][i]
            if not x.get("check_established") or not x.get("kind_call"):
                est = self.state[key]["errors"].get(f"{role}:established:{i}")
                kd = self.state[key]["errors"].get(f"{role}:kind:{i}")
                return f"reading {i + 1}: established {est or 'ok'}, kind {kd or 'ok'}"
        return None

    async def _run_wave3(self, keys: list[str], *, role: str, model: str, wave: str) -> None:
        """Same sense (both roles) and, for the first role only, the comparison."""
        calls = []
        sense_key = "sense" if role == "first" else "so_sense"
        for k in keys:
            s = self.state[k][sense_key]
            pair = split.same_sense_pair(s)
            if pair:
                a, b = pair
                calls.append(self._make("same_sense", k, model=model, role=role, index=a,
                                        user=split.payload("same_sense", label=s_label(self.state[k]),
                                                           reading=s["readings"][a]["reading"],
                                                           reading_2=s["readings"][b]["reading"])))
            if role == "first" and self.plain_reading and self.state[k].get("intended"):
                for i in split.survivors(s):
                    calls.append(self._make("comparison", k, model=self.compare_model, index=i,
                                            user=split.comparison_payload(label=s_label(self.state[k]),
                                                                          reading=s["readings"][i]["reading"],
                                                                          intended=self.state[k]["intended"])))
        res = await self._wave(wave, calls)
        for c in calls:
            if id(c) not in res:
                continue
            row, err = res[id(c)]
            st = self.state[c.key]
            if c.step == "same_sense":
                pair = split.same_sense_pair(st[sense_key])
                st["same_sense" if role == "first" else "so_same_sense"] = (
                    {**row, "readings": [pair[0] + 1, pair[1] + 1], "model": c.model} if row is not None
                    else {"error": err, "readings": [pair[0] + 1, pair[1] + 1], "model": c.model})
            else:
                st["comparison"][c.index] = row if row is not None else {"error": err}
        self._check_stop()

    def _join(self, key: str, role: str = "first") -> dict:
        st = self.state[key]
        if role == "first":
            comps = None
            if self.plain_reading and st.get("intended") and st["comparison"] is not None:
                comps = {i: (st["comparison"].get(i) or {}).get("relation") for i in split.survivors(st["sense"])}
            return split.join(st["sense"], (st.get("same_sense") or {}).get("relation"), comps)
        return split.join(st["so_sense"], (st.get("so_same_sense") or {}).get("relation"))

    def select_second_opinion(self, keys: Sequence[str]) -> list[str]:
        """A seeded ``second_opinion_frac`` of the words that reached step 1, plus every word with the note
        ``obvious_sense_not_trait`` or ``most_likely_reading_stretched`` (section 6).  Sorted."""
        reached = sorted(k for k in keys if self.state[k].get("sense") is not None)
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
                                  "same_sense": None, "so_same_sense": None, "comparison": {}, "gloss": None,
                                  "gloss_model": None, "alignment": None, "descriptors": None, "join": None,
                                  "so_join": None, "probe": None, "errors": {}, "cut": None}
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
        # waves 1 and 2
        await self._run_path(keys, role="first", model=self.model, wave_prefix="w1_")
        await self._run_checks([k for k in keys if self.state[k]["sense"]], role="first", model=self.model,
                               wave="w2_checks")
        ready = []
        for k in keys:
            why = self._complete(k)
            if why is None:
                ready.append(k)
            else:
                self.state[k]["failed"] = why
        # wave 3
        await self._run_wave3(ready, role="first", model=self.model, wave="w3_same_sense")
        for k in ready:
            self.state[k]["join"] = self._join(k)
        self.second_keys = self.select_second_opinion(ready) if self.second_opinion else []
        self.stats["second_opinion_n"] = len(self.second_keys)
        so = set(self.second_keys)
        # wave 4: gloss (outcome trait), and the second opinion's step 1
        gloss_calls = []
        for k in ready:
            j = self.state[k]["join"]
            if j["outcome"] != "trait":
                continue
            m = self.second_model if k in so else self.model
            gloss_calls.append(self._make("gloss", k, model=m, index=j["accepted_index"],
                                          user=split.payload("gloss", label=s_label(self.state[k]),
                                                             reading=j["accepted"])))
        so_sense = [self._make("sense", k, model=self.second_model, role="second",
                               user=split.payload("sense", label=s_label(self.state[k]))) for k in self.second_keys]
        res = await self._wave("w4_gloss", gloss_calls + so_sense)
        for c in gloss_calls:
            if id(c) in res:
                row, err = res[id(c)]
                st = self.state[c.key]
                st["gloss"], st["gloss_model"] = (row if row is not None else {"error": err}), c.model
        for c in so_sense:
            if id(c) in res:
                row, err = res[id(c)]
                if row is not None:
                    self.state[c.key]["so_sense"] = {k: v for k, v in row.items() if k != "label"}
                else:
                    self.state[c.key]["errors"]["so_sense"] = err
        self._check_stop()
        # wave 5: alignment and descriptors on the gloss; the second opinion's checks
        last = []
        for k in ready:
            g = (self.state[k].get("gloss") or {}).get("gloss")
            if g:
                for step in ("alignment", "descriptors"):
                    last.append(self._make(step, k, model=self.model,
                                           user=split.payload(step, label=s_label(self.state[k]), description=g)))
        so_checks = []
        so_ready = [k for k in self.second_keys if self.state[k]["so_sense"]]
        for step in ("established", "vague", "kind"):
            so_checks += self._path_calls(so_ready, step, role="second", model=self.second_model)
        res = await self._wave("w5_last_step", last + so_checks)
        for c in last:
            if id(c) in res:
                row, err = res[id(c)]
                self.state[c.key][c.step] = row if row is not None else {"error": err}
        field_of = {"established": "check_established", "vague": "check_vague", "kind": "kind_call"}
        for c in so_checks:
            if id(c) in res:
                row, err = res[id(c)]
                if row is not None:
                    self._reading(c.key, c.index, "second")[field_of[c.step]] = row
                else:
                    self.state[c.key]["errors"][f"second:{c.step}:{c.index}"] = err
        self._check_stop()
        # wave 6: the second opinion's same-sense check
        so_done = [k for k in so_ready if self._complete(k, "second") is None]
        await self._run_wave3(so_done, role="second", model=self.second_model, wave="w6_second_same_sense")
        for k in self.second_keys:
            why = self._complete(k, "second")
            self.state[k]["so_join"] = self._join(k, "second") if why is None else {"error": why}
            if why is None and self.state[k]["so_join"]["outcome"] != self.state[k]["join"]["outcome"]:
                self.stats["disagreements"] += 1
            if why is not None:
                self.stats["second_opinion_failed"] += 1
        self.stats["done"] = 1

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
    def _second_block(self, key: str) -> Optional[dict]:
        if key not in self.second_keys:
            return None
        st = self.state[key]
        sj = st.get("so_join")
        if not sj:
            return None
        if "error" in sj:
            return {"model": self.second_model, "error": sj["error"]}
        return {"model": self.second_model, "outcome": sj["outcome"], "accepted": sj["accepted"],
                "cause": sj["cause"], "notes": sj["notes"], "agree": sj["outcome"] == st["join"]["outcome"],
                "same_sense": (st.get("so_same_sense") or {}).get("relation"),
                "sense": {k: (st["so_sense"] or {}).get(k) for k in ("note", "first_thought", "first_thought_said_of",
                                                                     "usable")}
                | {"readings": split.block_readings(st["so_sense"] or {})}}

    def _comparison_block(self, key: str) -> Optional[dict]:
        st = self.state[key]
        if not (self.plain_reading and st.get("intended")) or st.get("sense") is None:
            return None
        per = []
        for i in split.survivors(st["sense"]):
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
            failed_why = st.get("failed") or (st["errors"].get("sense") if st.get("sense") is None else None)
            if failed_why:  # a step 1 or step 2 answer failed validation twice: the join cannot be made
                res.stage, res.error = "failed", failed_why
                res.meta["split_partial"] = _partial(st)
                continue
            if not finished or j is None:  # a stop: the path is not finished
                res.stage = "pending"
                res.meta["split_partial"] = _partial(st)
                continue
            g = st.get("gloss") or {}
            block, gloss, holding, et = split.to_filter_block(
                sense=st["sense"], j=j, model=self.model, batch_id=self.batch_id, now=now,
                step_versions=self.step_versions, prompt_sha256=self.prompt_sha, same_sense=st.get("same_sense"),
                comparison=self._comparison_block(it.key), gloss_model=st.get("gloss_model"),
                alignment=st.get("alignment") if "error" not in (st.get("alignment") or {}) else None,
                descriptors=st.get("descriptors") if "error" not in (st.get("descriptors") or {}) else None,
                second_opinion=self._second_block(it.key), gloss=g.get("gloss"))
            errs = {k: (st.get(k) or {}).get("error") for k in ("gloss", "alignment", "descriptors")
                    if (st.get(k) or {}).get("error")}
            if errs:
                block["last_step_errors"] = errs
            res.stage, res.error = "classified", None
            res.filter, res.gloss, res.holding, res.entity_type = block, gloss, holding, et

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


def _partial(st: Mapping) -> dict:
    """What a row has so far, for ``meta["split_partial"]``."""
    keep = ("sense", "same_sense", "gloss", "gloss_model", "alignment", "descriptors", "join", "so_sense",
            "so_same_sense", "so_join", "errors", "failed")
    out = {k: st.get(k) for k in keep if st.get(k)}
    if st.get("comparison"):
        out["comparison"] = {str(i): v for i, v in st["comparison"].items()}
    return out
