"""Cost estimates, hard caps and the confirmation gate for platform CLIs.

Every CLI prints an estimate as ``n_calls x (in, out) tokens at model rates =
$X`` (:func:`format_estimate`), checks it with :func:`confirm_or_abort`, and
charges every response to a :class:`GuardedUsage`, which raises
``BudgetExceededError`` as soon as the running total crosses the cap.  The
caller writes ``usage.json`` in a ``finally`` block; :class:`GuardedUsage`
also writes it itself before raising when given ``usage_path``.

A killed process must not lose its spend (code review 2026-10-12, B3: reviews
1 D1 and 2 D3).  So a :class:`GuardedUsage` with ``usage_path`` also writes the
file as it charges, at most every :data:`USAGE_WRITE_INTERVAL_S` seconds and
atomically; the first one built in a process installs a SIGTERM handler that
writes every such file and raises ``SystemExit(143)``, so a plain ``kill``
runs the CLI's ``finally`` too; and a resume takes the larger of
``usage.json`` and the spend its response records show
(:func:`resume_usage`), with a WARNING when they differ.  Only a SIGKILL
between two writes still loses spend from ``usage.json``, and the records
give it back on the next resume.

Rules (CLAUDE.md "Expensive operations"; decision 9 / open point A): the
typed ``--budget-usd`` is the cap, and an estimate over it is refused (type a
larger budget to spend more).  A budget or estimate over the $20 line needs
``--confirm-expensive`` **and** ``--confirmed-by`` naming Roger's explicit go
in chat, recorded in the run's ``run.json``.
"""
from __future__ import annotations

import json
import logging
import signal
import sys
import threading
import time
import weakref
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional

from assistant_axis.judge_pricing import (
    BudgetExceededError, MultiModelUsage, UsageTotals, cost_for_usage,
)

logger = logging.getLogger(__name__)

HARD_LINE_USD = 20.0

#: How often, at most, a :class:`GuardedUsage` with a ``usage_path`` rewrites the file as it charges (seconds).
USAGE_WRITE_INTERVAL_S = 30.0


@dataclass
class GuardedUsage(MultiModelUsage):
    """``MultiModelUsage`` with a hard cap.  ``charge`` records the call first
    (so the tokens are never lost), then raises ``BudgetExceededError`` when
    the total exceeds ``budget_usd``; with ``usage_path`` set, ``usage.json``
    is written before the exception propagates.

    With ``usage_path`` set it is also written as calls are charged, at most
    every ``write_interval_s`` seconds (``None``: only at a budget stop, a
    SIGTERM and the caller's own writes), so a process killed mid-run leaves a
    file at most that old (code review 2026-10-12, B3).  Every write is
    atomic.  The file holds this object's total, so a resuming caller merges
    the earlier spend in before the first charge, as every platform CLI does."""
    budget_usd: Optional[float] = None
    usage_path: Optional[Path] = None
    write_interval_s: Optional[float] = USAGE_WRITE_INTERVAL_S
    _last_write: float = field(default=float("-inf"), init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _LIVE[id(self)] = self
        install_sigterm_handler()

    def charge(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        delta = super().charge(model, prompt_tokens, completion_tokens)
        if self.budget_usd is not None and self.total_cost_usd > self.budget_usd:
            if self.usage_path is not None:
                self.write_json(self.usage_path)
            agg = UsageTotals(model="+".join(sorted(self.per_model)) or "none",
                              prompt_tokens=self.total_prompt_tokens,
                              completion_tokens=self.total_completion_tokens,
                              cost_usd=self.total_cost_usd, n_calls=self.n_calls)
            raise BudgetExceededError(agg, self.budget_usd)
        if (self.usage_path is not None and self.write_interval_s is not None
                and time.monotonic() - self._last_write >= self.write_interval_s):
            self.write_json(self.usage_path)
        return delta

    def write_json(self, path) -> None:
        """``MultiModelUsage.write_json``, atomically (a kill mid-write leaves the previous file, not a torn one,
        which ``load_or_create`` would read as zero spend)."""
        from assistant_axis.atomic_io import atomic_write_text
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps(self.as_dict(), indent=2, sort_keys=True), p)
        if self.usage_path is not None and p == Path(self.usage_path):
            self._last_write = time.monotonic()

    def plain(self) -> MultiModelUsage:
        return MultiModelUsage(per_model=dict(self.per_model))


# --------------------------------------------------------------------------- SIGTERM

#: The live guarded usages of this process (weakly held), which the SIGTERM handler writes.
_LIVE: "weakref.WeakValueDictionary[int, GuardedUsage]" = weakref.WeakValueDictionary()
_SIGTERM_INSTALLED = False


def _on_sigterm(signum, frame) -> None:
    """Write every live :class:`GuardedUsage` that has a ``usage_path``, then raise ``SystemExit(128 + signum)``
    so that the CLI's ``finally`` writes the rest of its outputs, as it does on a budget stop."""
    for u in list(_LIVE.values()):
        if u.usage_path is not None:
            try:
                u.write_json(u.usage_path)
            except Exception as exc:  # noqa: BLE001 - the exit must happen; the finally writes again
                print(f"could not write {u.usage_path} on SIGTERM: {exc}", file=sys.stderr)
    print(f"STOPPED by signal {signum}: usage written; the run's finally writes the rest", file=sys.stderr)
    raise SystemExit(128 + signum)


def install_sigterm_handler() -> bool:
    """Install :func:`_on_sigterm` for SIGTERM, once, from the main thread, and only over the default handler (a
    handler someone else installed is left alone).  True when it is in place.  :class:`GuardedUsage` calls this
    when it is built, so every paid CLI gets it without code of its own (code review 2026-10-12, B3)."""
    global _SIGTERM_INSTALLED
    if _SIGTERM_INSTALLED:
        return signal.getsignal(signal.SIGTERM) is _on_sigterm
    if threading.current_thread() is not threading.main_thread():
        return False
    if signal.getsignal(signal.SIGTERM) not in (signal.SIG_DFL, None):
        return False
    signal.signal(signal.SIGTERM, _on_sigterm)
    _SIGTERM_INSTALLED = True
    return True


# --------------------------------------------------------------------------- resume

def usage_from_records(records: Iterable[Mapping]) -> MultiModelUsage:
    """The spend a run's response records show: every record carrying the billed usage it was charged
    (``usage_raw``) and the model key it was charged under (``charged_as``), charged as ``llm.billed_usage``
    charges a response (cache writes at 1.25x, 1-hour writes at 2x, reads at 0.1x) under the current form of the
    key (``batches.current_batch_key``).  A record without either was not charged and is skipped.  The record
    format of the split filter, M3 and the passes; the overlap test's nests ``usage_raw`` and is not read here."""
    from .batches import current_batch_key
    from .llm import CACHE_READ_FACTOR, CACHE_WRITE_1H_FACTOR, CACHE_WRITE_FACTOR
    out = MultiModelUsage()
    for rec in records:
        raw, model = rec.get("usage_raw") or {}, rec.get("charged_as")
        if not raw or not model:
            continue
        cw = int(raw.get("cache_creation_input_tokens") or 0)
        cw1h = min(int(raw.get("cache_creation_1h_input_tokens") or 0), cw)
        cr = int(raw.get("cache_read_input_tokens") or 0)
        prompt = int(raw.get("input_tokens") or 0) + int(round(
            CACHE_WRITE_FACTOR * (cw - cw1h) + CACHE_WRITE_1H_FACTOR * cw1h + CACHE_READ_FACTOR * cr))
        out.charge(current_batch_key(model), prompt, int(raw.get("output_tokens") or 0))
    return out


def resume_usage(recorded: MultiModelUsage, records: Iterable[Mapping], *, where: str = "") -> MultiModelUsage:
    """The earlier spend a resumed run starts from: the larger (by cost) of ``recorded`` (its ``usage.json``) and
    :func:`usage_from_records` over its response records, with a WARNING when the two differ.  A process killed
    before writing its usage left ``usage.json`` short of what was paid (review 1 D1: m1_validation_r2 recorded
    12,261 calls for 13,378 charged records); the records are appended as each response arrives, so they hold it."""
    rebuilt = usage_from_records(records)
    if recorded.n_calls != rebuilt.n_calls or abs(recorded.total_cost_usd - rebuilt.total_cost_usd) > 1e-4:
        larger = "the records" if rebuilt.total_cost_usd > recorded.total_cost_usd else "usage.json"
        logger.warning("%susage.json records %d calls ($%.4f) but the response records show %d ($%.4f); the resume "
                       "starts from %s", f"{where}: " if where else "", recorded.n_calls, recorded.total_cost_usd,
                       rebuilt.n_calls, rebuilt.total_cost_usd, larger)
    return rebuilt if rebuilt.total_cost_usd > recorded.total_cost_usd else recorded


def estimate_calls_usd(model: str, n_calls: int, in_tok: int, out_tok: int) -> float:
    """Cost of ``n_calls`` calls of ``in_tok`` input and ``out_tok`` output tokens."""
    return n_calls * cost_for_usage(model, in_tok, out_tok)


@dataclass
class EstimateLine:
    label: str
    model: str
    n_calls: int
    in_tok: int
    out_tok: int

    @property
    def usd(self) -> float:
        return estimate_calls_usd(self.model, self.n_calls, self.in_tok, self.out_tok)

    def __str__(self) -> str:
        return (f"{self.label}: {self.n_calls} x ({self.in_tok:,}, {self.out_tok:,}) tokens at "
                f"{self.model} rates = ${self.usd:.3f}")


@dataclass
class Estimate:
    lines: list[EstimateLine] = field(default_factory=list)

    def add(self, label: str, model: str, n_calls: int, in_tok: int, out_tok: int) -> None:
        if n_calls > 0:
            self.lines.append(EstimateLine(label, model, n_calls, in_tok, out_tok))

    @property
    def usd(self) -> float:
        return sum(x.usd for x in self.lines)

    def format(self) -> str:
        body = "\n".join(f"  {x}" for x in self.lines) or "  (no API calls)"
        return f"{body}\n  total estimate = ${self.usd:.3f}"


def format_estimate(model: str, n_calls: int, in_tok: int, out_tok: int) -> str:
    return str(EstimateLine("estimate", model, n_calls, in_tok, out_tok))


class CostRefused(SystemExit):
    """Raised by :func:`confirm_or_abort`; exit code 2, ``str()`` is the reason.

    The reason is printed to stderr when the exception is created, because an
    uncaught ``SystemExit(2)`` prints nothing and generator scripts call
    :func:`confirm_or_abort` directly (review_m1_fixes.md item 2)."""

    def __init__(self, msg: str):
        super().__init__(2)
        self.msg = msg
        print(f"REFUSED (cost gate): {msg}", file=sys.stderr, flush=True)

    def __str__(self) -> str:
        return self.msg


def confirm_or_abort(estimate_usd: float, budget_usd: float, *, confirm_expensive: bool,
                     hard_line: float = HARD_LINE_USD, confirmed_by: Optional[str] = None) -> float:
    """Gate an estimated spend.  Returns the cap the run should enforce, which
    is always the typed ``budget_usd`` (decision 9 and open point A of
    ``reports/trait_gap_generation/decisions_m1.md``; Roger: "having a
    budget, and a flag to increase it, sounds like unneeded bells and
    whistles").

    * estimate <= budget: allowed; cap = budget.
    * estimate > budget: refused, whatever the flags; to spend more, type a
      larger ``--budget-usd``.
    * a budget (or an estimate) over ``hard_line`` ($20): needs Roger's
      explicit go in chat, recorded as ``confirmed_by``, **and**
      ``confirm_expensive``.  That is the flag's only remaining use; the
      signature is unchanged because other plans are written against it.
    Refusals raise :class:`CostRefused` (a ``SystemExit`` with code 2).
    """
    confirmed = bool(confirm_expensive and confirmed_by)
    if estimate_usd > hard_line and not confirmed:
        raise CostRefused(
            f"estimate ${estimate_usd:.2f} is over the ${hard_line:.0f} line: needs Roger's explicit go "
            f"in chat, then --confirm-expensive --confirmed-by '<who, when>' and a --budget-usd at least "
            f"the estimate")
    if budget_usd > hard_line and not confirmed:
        raise CostRefused(
            f"--budget-usd ${budget_usd:.2f} is over the ${hard_line:.0f} line: a cap above it needs Roger's "
            f"explicit go in chat, recorded with --confirm-expensive --confirmed-by '<who, when>'")
    if estimate_usd > budget_usd:
        raise CostRefused(
            f"estimate ${estimate_usd:.2f} exceeds --budget-usd ${budget_usd:.2f}: type a larger --budget-usd "
            f"(no flag raises the cap)")
    return budget_usd
