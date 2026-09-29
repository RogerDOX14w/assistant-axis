"""Stage B of the split filter: each wave sent as one Message Batch (coding_plan_split.md section 7).

:class:`BatchTransport` is a transport for :class:`assistant_axis.gapgen.split_runner.SplitRunner`,
beside the live one: the runner builds the same calls, and this sends them as one batch, one request
for each call, ``custom_id`` made of step, key and reading index (``Call.custom_id``).  Request and
result shapes follow the Anthropic SDK (``client.messages.batches.create(requests=[{"custom_id",
"params"}])``, ``retrieve(id).processing_status == "ended"``, ``results(id)`` yielding
``.custom_id`` and ``.result.type`` of succeeded / errored / canceled / expired, the message under
``.result.message``).  Results arrive in any order and are matched by ``custom_id``.

Money.  Every succeeded result is charged under ``<model>@batch``, which
:func:`assistant_axis.judge_pricing.price_for_model` prices at half the model's rates.  Before a batch
is submitted its estimate is checked against the cap: when the spend so far plus the estimate would
pass the budget, nothing is submitted and ``BudgetExceededError`` is raised.  A batch already
submitted is paid for whatever happens, so every one of its results is recorded and charged, even
past the cap; the stop is raised after the last one.

Restart.  Batch ids and wave state go to ``filter/<batch>/batches.json``, written as soon as a batch
is created.  A killed process started again with ``--resume`` finds the wave's batches there: it
polls each batch not yet collected and collects its results for the calls still unanswered instead
of submitting them again.  A batch already collected is skipped (its answers are in
``responses.jsonl`` and were charged); a call of it still unanswered failed validation and goes into
a new batch, as it would live.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, UsageTotals

from .llm import billed_usage, request_params, response_text
from .registry import utc_now

logger = logging.getLogger(__name__)

POLL_SECONDS = 30.0
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


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


class BatchTransport:
    """Sends a wave's calls as Message Batches (see the module docstring)."""
    name = "batches"

    def __init__(self, runner, client, state_path: Path, *, poll_seconds: float = POLL_SECONDS,
                 sleep: Optional[Callable[[float], Any]] = None, budget_usd: Optional[float] = None):
        self.runner = runner
        self.client = client            # a synchronous anthropic.Anthropic (or a fake)
        self.state_path = Path(state_path)
        self.poll_seconds = poll_seconds
        self.sleep = sleep or asyncio.sleep
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
        pending = {c.custom_id: c for c in calls}
        if len(pending) != len(calls):
            raise ValueError(f"{wave}: duplicate custom_id in one wave")
        state = self.load_state()
        stop: Optional[BaseException] = None
        # batches of this wave recorded by an earlier process: collect before submitting anything.
        # Only a batch never collected: every result of a collected one is already in responses.jsonl
        # and charged, so a call of it still pending here failed validation and needs a new request
        # (collecting it again would record and charge the same answer twice).
        for b in state["waves"].get(wave, []):
            if b.get("status") == "collected":
                continue
            mine = [cid for cid in b["custom_ids"] if cid in pending]
            if not mine:
                continue
            logger.info("%s: collecting %d results from recorded batch %s", wave, len(mine), b["id"])
            stop = await self._collect(b, pending, on_result, state) or stop
        if stop is not None:
            raise stop
        todo = list(pending.values())
        if not todo:
            return
        est = self.runner.estimate_usd(todo, batch=True)
        spent = self.runner.usage.total_cost_usd
        budget = self.budget_usd if self.budget_usd is not None else getattr(self.runner.usage, "budget_usd", None)
        if budget is not None and spent + est > budget:
            u = self.runner.usage
            agg = UsageTotals(model="+".join(sorted(u.per_model)) or "none", prompt_tokens=u.total_prompt_tokens,
                              completion_tokens=u.total_completion_tokens, cost_usd=spent, n_calls=u.n_calls)
            logger.warning("%s: not submitted: spent $%.4f + estimate $%.4f > cap $%.2f", wave, spent, est, budget)
            raise BudgetExceededError(agg, budget)
        requests = [{"custom_id": c.custom_id,
                     "params": request_params(model=c.model, system=c.system, user=c.user, max_tokens=c.max_tokens,
                                              temperature=c.temperature, cache_system=False)} for c in todo]
        batch = self.client.messages.batches.create(requests=requests)
        rec = {"id": _get(batch, "id"), "custom_ids": [c.custom_id for c in todo], "n_requests": len(todo),
               "estimate_usd": round(est, 6), "submitted_at": utc_now(), "status": "submitted"}
        state["waves"].setdefault(wave, []).append(rec)
        self.save_state(state)   # at once: a killed process finds the batch here
        self.submitted += 1
        logger.info("%s: submitted batch %s (%d requests, estimate $%.4f)", wave, rec["id"], len(todo), est)
        stop = await self._collect(rec, pending, on_result, state)
        if stop is not None:
            raise stop

    async def _collect(self, rec: dict, pending: dict, on_result: Callable, state: dict) -> Optional[BaseException]:
        """Wait for a batch to end, then hand every result for a pending call to ``on_result``.
        Returns the budget stop raised while charging, if any (every result is still recorded)."""
        bid = rec["id"]
        while True:
            b = self.client.messages.batches.retrieve(bid)
            status = _get(b, "processing_status")
            if status == "ended":
                break
            counts = _get(b, "request_counts")
            logger.info("batch %s: %s (%s)", bid, status, counts)
            await self.sleep(self.poll_seconds)
        stop: Optional[BaseException] = None
        seen = set()
        for res in self.client.messages.batches.results(bid):
            cid = _get(res, "custom_id")
            c = pending.pop(cid, None)
            if c is None:
                continue  # answered already (recorded by an earlier process) or not ours
            seen.add(cid)
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
                    stop = stop or exc
            else:
                err = _get(result, "error")
                text = None
                meta.update(stop_reason=None, usage_raw={}, error=f"batch result {rtype}: {err}", charged_as=None)
            on_result(c, text, meta)
        for cid in [x for x in rec["custom_ids"] if x in pending]:
            c = pending.pop(cid)
            on_result(c, None, {"batch_request_id": bid, "error": "no result in the batch", "usage_raw": {},
                                "charged_as": None})
        rec["status"], rec["collected_at"] = "collected", utc_now()
        self.save_state(state)
        return stop
