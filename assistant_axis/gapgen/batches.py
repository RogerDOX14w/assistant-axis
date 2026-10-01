"""Stage B of the split filter: each wave sent through the Message Batches API (coding_plan_split.md
section 7).

:class:`BatchTransport` is a transport for :class:`assistant_axis.gapgen.split_runner.SplitRunner`,
beside the live one: the runner builds the same calls, and this sends them as batches, one request
for each call, ``custom_id`` made of step, key and reading index (``Call.custom_id``).  A wave is one
batch unless it passes :data:`MAX_BATCH_REQUESTS` requests or :data:`MAX_BATCH_BYTES` of serialized
requests (half the service's limits); then it is split, in order, into as many batches as needed.
All the batches of a wave are submitted first and then polled, so a large wave waits about one
batch's time rather than one for each batch.  Request and
result shapes follow the Anthropic SDK (``client.messages.batches.create(requests=[{"custom_id",
"params"}])``, ``retrieve(id).processing_status == "ended"``, ``results(id)`` yielding
``.custom_id`` and ``.result.type`` of succeeded / errored / canceled / expired, the message under
``.result.message``).  Results arrive in any order and are matched by ``custom_id``.

Money.  Every succeeded result is charged under ``<model>:batch`` (``judge_pricing.BATCH_SUFFIX``), which
:func:`assistant_axis.judge_pricing.price_for_model` prices at half the model's rates.  Before any
batch of a wave is submitted, the whole wave's estimate is checked against the cap (the spend so
far, plus the recorded batches still to be charged, plus every request about to go): when it would
pass the budget, nothing is submitted, the recorded batches are still collected, and
``BudgetExceededError`` is raised.  A batch already submitted is paid for whatever happens, so every
one of its results is recorded and charged, even past the cap; the stop is raised after the last one.

Restart.  Batch ids and wave state go to ``filter/<batch>/batches.json``, each batch written as soon
as it is created.  A killed process started again with ``--resume`` finds the wave's batches there:
every batch not yet collected is polled and collected, and only the calls that no recorded batch
covers are submitted.  A batch already collected is skipped (its answers are in ``responses.jsonl``
and were charged); a call of it still unanswered failed validation and goes into a new batch, as it
would live.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, UsageTotals

#: The suffix the split filter wrote before 2026-10-01 (``<model>@batch``); the repository's
#: convention is ``judge_pricing.BATCH_SUFFIX`` (``<model>:batch``, priced by provider factor).
#: Records of the first full validation run carry the old form; readers map it with
#: :func:`current_batch_key`.
LEGACY_BATCH_SUFFIX = "@batch"


def current_batch_key(model: str) -> str:
    """``model`` with a legacy ``@batch`` suffix rewritten to ``BATCH_SUFFIX``; other keys unchanged."""
    if model and model.endswith(LEGACY_BATCH_SUFFIX) and LEGACY_BATCH_SUFFIX != BATCH_SUFFIX:
        return model[: -len(LEGACY_BATCH_SUFFIX)] + BATCH_SUFFIX
    return model


def with_current_batch_keys(tracker):
    """A ``MultiModelUsage`` whose legacy ``@batch`` entries are re-keyed to ``BATCH_SUFFIX`` (the
    stored tokens and cost are kept as they are)."""
    for key in list(tracker.per_model):
        new = current_batch_key(key)
        if new != key:
            tot = tracker.per_model.pop(key)
            tot.model = new
            tracker.per_model[new] = tot
    return tracker

from .llm import RETRY_DELAYS_S, _is_transient, billed_usage, request_params, response_text
from .registry import utc_now

logger = logging.getLogger(__name__)

POLL_SECONDS = 30.0
#: One Message Batch holds at most 100,000 requests and 256 MB (the claude-api skill's batches page,
#: 2026-09-30).  A wave larger than either limit below is split into several batches; the limits
#: keep half the service's room in hand, the byte one measured on the serialized requests.
MAX_BATCH_REQUESTS = 50_000
MAX_BATCH_BYTES = 128 * 1024 * 1024
#: A poll that finds a batch ended more than this long ago says so (a suspended process shows up).
LATE_ENDED_SECONDS = 600.0
#: ``--transport auto``: fewer words than this go live, this many or more through batches.
AUTO_BATCH_FROM = 300


def choose_transport(requested: str, n_words: int) -> tuple[str, str]:
    """``(transport, reason)`` for ``--transport auto|live|batches``."""
    if requested == "live":
        return "live", "--transport live"
    if requested == "batches":
        return "batches", "--transport batches"
    if n_words < AUTO_BATCH_FROM:
        return "live", f"auto: {n_words} words, fewer than {AUTO_BATCH_FROM}, go live"
    return "batches", f"auto: {n_words} words, {AUTO_BATCH_FROM} or more, go through the Message Batches API (half price)"


def _request_bytes(request: dict) -> int:
    """The size of one request as the API receives it (serialized JSON, UTF-8)."""
    return len(json.dumps(request, ensure_ascii=False).encode("utf-8"))


def split_requests(calls: list, build: Callable[[Any], dict], *, max_requests: Optional[int] = None,
                   max_bytes: Optional[int] = None) -> list[list[tuple[Any, dict]]]:
    """``calls`` in order, as chunks of ``(call, request)`` that each fit one batch: at most
    ``max_requests`` requests (default :data:`MAX_BATCH_REQUESTS`) and ``max_bytes`` of serialized
    requests (default :data:`MAX_BATCH_BYTES`).  The module constants are read at call time, so a
    test can lower them.  A single request larger than the byte limit goes in a batch of its own
    (the service may still refuse it, loudly)."""
    max_requests = MAX_BATCH_REQUESTS if max_requests is None else max_requests
    max_bytes = MAX_BATCH_BYTES if max_bytes is None else max_bytes
    chunks: list[list[tuple[Any, dict]]] = []
    cur: list[tuple[Any, dict]] = []
    size = 0
    for c in calls:
        req = build(c)
        n = _request_bytes(req)
        if cur and (len(cur) >= max_requests or size + n > max_bytes):
            chunks.append(cur)
            cur, size = [], 0
        cur.append((c, req))
        size += n
    if cur:
        chunks.append(cur)
    return chunks


def is_transient_stream_error(exc: BaseException) -> bool:
    """A network or server error worth trying again: whatever :func:`llm._is_transient` accepts
    (connection and timeout errors, 429 and 5xx), plus the HTTP library's own transport and stream
    errors, which a results stream raises unwrapped (``httpx.RemoteProtocolError: peer closed
    connection without sending complete message body``, 2026-09-30)."""
    if _is_transient(exc):
        return True
    try:
        import httpx
        if isinstance(exc, (httpx.TransportError, httpx.StreamError)):
            return True
    except ImportError:  # pragma: no cover
        pass
    try:
        import httpcore
        if isinstance(exc, (httpcore.NetworkError, httpcore.ProtocolError, httpcore.TimeoutException)):
            return True
    except ImportError:  # pragma: no cover
        pass
    return False


def _since(when: Any) -> Optional[float]:
    """Seconds from ``when`` (an ISO string or a datetime) to now; None when it is missing."""
    if not when:
        return None
    try:
        t = when if isinstance(when, datetime) else datetime.fromisoformat(str(when).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - t).total_seconds()


def _span(seconds: Optional[float]) -> str:
    """``1h02m``, ``4m10s`` or ``?``."""
    if seconds is None:
        return "?"
    s = int(max(0, seconds))
    h, m = divmod(s // 60, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s % 60:02d}s"


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class BatchTransport:
    """Sends a wave's calls as Message Batches (see the module docstring)."""
    name = "batches"

    def __init__(self, runner, client, state_path: Path, *, poll_seconds: float = POLL_SECONDS,
                 sleep: Optional[Callable[[float], Any]] = None, budget_usd: Optional[float] = None,
                 retry_delays: Optional[Sequence[float]] = None):
        self.runner = runner
        self.client = client            # a synchronous anthropic.Anthropic (or a fake)
        self.state_path = Path(state_path)
        self.poll_seconds = poll_seconds
        self.sleep = sleep or asyncio.sleep
        #: back-off for a transient error on a poll or a results stream (the live calls' own)
        self.retry_delays = tuple(RETRY_DELAYS_S if retry_delays is None else retry_delays)
        self.budget_usd = budget_usd
        self.submitted = 0

    # -- state file ------------------------------------------------------------
    def load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"batch_id": getattr(self.runner, "batch_id", None), "waves": {}}

    def save_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", self.state_path)

    # -- one wave ----------------------------------------------------------------
    async def execute(self, wave: str, calls: list, on_result: Callable) -> None:
        """Send one wave: collect what earlier processes submitted, submit the rest as one or more
        batches (all of them first, then poll them), and hand every result to ``on_result``."""
        pending = {c.custom_id: c for c in calls}
        if len(pending) != len(calls):
            raise ValueError(f"{wave}: duplicate custom_id in one wave")
        state = self.load_state()
        # Batches of this wave recorded by an earlier process and never collected: their calls are
        # paid for and will be collected, not submitted again.  A batch already collected is skipped:
        # every result of it is in responses.jsonl and charged, so a call of it still pending here
        # failed validation and needs a new request (collecting it again would record and charge the
        # same answer twice).
        recorded = [b for b in state["waves"].get(wave, []) if b.get("status") != "collected"
                    and any(cid in pending for cid in b["custom_ids"])]
        covered = {cid for b in recorded for cid in b["custom_ids"] if cid in pending}
        todo = [c for cid, c in pending.items() if cid not in covered]
        # The estimate check covers the whole wave before anything is submitted: the spend so far,
        # the recorded batches still to be charged, and every call about to be submitted.
        refused: Optional[BaseException] = None
        if todo:
            est = self.runner.estimate_usd(todo, batch=True)
            est_recorded = self.runner.estimate_usd([pending[cid] for cid in covered], batch=True)
            spent = self.runner.usage.total_cost_usd
            budget = self.budget_usd if self.budget_usd is not None else getattr(self.runner.usage, "budget_usd", None)
            if budget is not None and spent + est_recorded + est > budget:
                u = self.runner.usage
                agg = UsageTotals(model="+".join(sorted(u.per_model)) or "none", prompt_tokens=u.total_prompt_tokens,
                                  completion_tokens=u.total_completion_tokens, cost_usd=spent, n_calls=u.n_calls)
                logger.warning("%s: not submitted: spent $%.4f + recorded batches $%.4f + estimate $%.4f > cap $%.2f",
                               wave, spent, est_recorded, est, budget)
                refused = BudgetExceededError(agg, budget)
                todo = []
        new: list[dict] = []
        for chunk in split_requests(todo, self._request):
            calls_of = [c for c, _ in chunk]
            batch = self.client.messages.batches.create(requests=[r for _, r in chunk])
            est_c = self.runner.estimate_usd(calls_of, batch=True)
            rec = {"id": _get(batch, "id"), "custom_ids": [c.custom_id for c in calls_of], "n_requests": len(chunk),
                   "bytes": sum(_request_bytes(r) for _, r in chunk), "estimate_usd": round(est_c, 6),
                   "submitted_at": utc_now(), "status": "submitted"}
            state["waves"].setdefault(wave, []).append(rec)
            self.save_state(state)   # at once: a killed process finds the batch here
            self.submitted += 1
            new.append(rec)
            logger.info("%s: submitted batch %s (%d requests, estimate $%.4f)", wave, rec["id"], len(chunk), est_c)
        stop: Optional[BaseException] = None
        for b in recorded + new:
            if b in recorded:
                logger.info("%s: collecting recorded batch %s", wave, b["id"])
            stop = await self._collect(b, pending, on_result, state) or stop
        if stop is not None:
            raise stop
        if refused is not None:
            raise refused

    @staticmethod
    def _request(c) -> dict:
        return {"custom_id": c.custom_id,
                "params": request_params(model=c.model, system=c.system, user=c.user, max_tokens=c.max_tokens,
                                         temperature=c.temperature, cache_system=False)}

    async def _retrying(self, what: str, bid: str, fn: Callable[[], Any]) -> Any:
        """``fn()``, tried again after a transient error (:func:`is_transient_stream_error`) with
        the back-off of :attr:`retry_delays`; the last error propagates."""
        for attempt in range(len(self.retry_delays) + 1):
            try:
                return await fn()
            except Exception as exc:  # noqa: BLE001 - classified here
                if not is_transient_stream_error(exc) or attempt >= len(self.retry_delays):
                    raise
                delay = self.retry_delays[attempt]
                logger.warning("batch %s: %s failed (%s: %s), attempt %d of %d; trying again in %ss",
                               bid, what, type(exc).__name__, exc, attempt + 1, len(self.retry_delays) + 1, delay)
                await self.sleep(delay)

    async def _wait_ended(self, rec: dict) -> Any:
        """Poll until the batch has ended.  Each poll line says how long the batch has waited since
        submission; a batch found ended long after it ended (a suspended process) gets a line of its
        own."""
        bid = rec["id"]

        async def retrieve():
            return self.client.messages.batches.retrieve(bid)

        while True:
            b = await self._retrying("retrieve", bid, retrieve)
            status = _get(b, "processing_status")
            waited = _since(rec.get("submitted_at"))
            if status == "ended":
                late = _since(_get(b, "ended_at"))
                if late is not None and late > LATE_ENDED_SECONDS:
                    logger.warning("batch %s: found ended %s after it ended (submitted %s ago); the process may "
                                   "have been suspended", bid, _span(late), _span(waited))
                else:
                    logger.info("batch %s: ended (submitted %s ago)", bid, _span(waited))
                return b
            logger.info("batch %s: %s (%s), waiting %s since submission", bid, status,
                        _get(b, "request_counts"), _span(waited))
            await self.sleep(self.poll_seconds)

    async def _collect(self, rec: dict, pending: dict, on_result: Callable, state: dict) -> Optional[BaseException]:
        """Wait for a batch to end, then hand every result for a pending call to ``on_result``.
        Returns the budget stop raised while charging, if any (every result is still recorded).

        A results stream that breaks off (the connection dropped, 2026-09-30) is started again with
        the back-off of :attr:`retry_delays`.  A result already handed over in this call is not
        handed over again: it is gone from ``pending``, and ``delivered`` keeps its custom_id.
        When the retries are spent the error propagates with the batch still "submitted" and every
        result received recorded, so ``--resume`` collects the rest."""
        bid = rec["id"]
        await self._wait_ended(rec)
        stop: Optional[BaseException] = None
        delivered: set[str] = set()

        async def stream() -> None:
            nonlocal stop
            for res in self.client.messages.batches.results(bid):
                cid = _get(res, "custom_id")
                if cid in delivered:
                    continue  # handed over before the stream broke
                c = pending.pop(cid, None)
                if c is None:
                    continue  # answered already (recorded by an earlier process) or not ours
                delivered.add(cid)
                stop = self._deliver(bid, c, res, on_result) or stop

        await self._retrying("results stream", bid, stream)
        for cid in [x for x in rec["custom_ids"] if x in pending]:
            c = pending.pop(cid)
            on_result(c, None, {"batch_request_id": bid, "error": "no result in the batch", "usage_raw": {},
                                "charged_as": None})
        rec["status"], rec["collected_at"] = "collected", utc_now()
        self.save_state(state)
        return stop

    def _deliver(self, bid: str, c, res: Any, on_result: Callable) -> Optional[BaseException]:
        """Charge and hand over one result; returns the budget stop its charge raised, if any."""
        stop: Optional[BaseException] = None
        result = _get(res, "result")
        rtype = _get(result, "type")
        meta: dict = {"batch_request_id": bid, "attempts": 1}
        if rtype == "succeeded":
            msg = _get(result, "message")
            prompt, out, raw = billed_usage(msg)
            text = response_text(msg)
            meta.update(stop_reason=_get(msg, "stop_reason"), usage_raw=raw, error=None,
                        charged_as=c.model + BATCH_SUFFIX)
            try:
                self.runner.usage.charge(c.model + BATCH_SUFFIX, prompt, out)
            except BudgetExceededError as exc:  # already paid: record it, stop after the batch
                stop = exc
        else:
            err = _get(result, "error")
            text = None
            meta.update(stop_reason=None, usage_raw={}, error=f"batch result {rtype}: {err}", charged_as=None)
        on_result(c, text, meta)
        return stop
