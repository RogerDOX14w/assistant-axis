"""Cost estimates, hard caps and the confirmation gate for platform CLIs.

Every CLI prints an estimate as ``n_calls x (in, out) tokens at model rates =
$X`` (:func:`format_estimate`), checks it with :func:`confirm_or_abort`, and
charges every response to a :class:`GuardedUsage`, which raises
``BudgetExceededError`` as soon as the running total crosses the cap.  The
caller writes ``usage.json`` in a ``finally`` block; :class:`GuardedUsage`
also writes it itself before raising when given ``usage_path``.

Rules (CLAUDE.md "Expensive operations"): an estimate over ``--budget-usd``
needs ``--confirm-expensive``; an estimate over the $20 line needs the flag
**and** ``--confirmed-by`` naming Roger's explicit go in chat, recorded in the
run's ``run.json``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from assistant_axis.judge_pricing import (
    BudgetExceededError, MultiModelUsage, UsageTotals, cost_for_usage,
)

HARD_LINE_USD = 20.0


@dataclass
class GuardedUsage(MultiModelUsage):
    """``MultiModelUsage`` with a hard cap.  ``charge`` records the call first
    (so the tokens are never lost), then raises ``BudgetExceededError`` when
    the total exceeds ``budget_usd``; with ``usage_path`` set, ``usage.json``
    is written before the exception propagates."""
    budget_usd: Optional[float] = None
    usage_path: Optional[Path] = None

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
        return delta

    def plain(self) -> MultiModelUsage:
        return MultiModelUsage(per_model=dict(self.per_model))


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
    """Raised by :func:`confirm_or_abort`; exit code 2, ``str()`` is the reason."""

    def __init__(self, msg: str):
        super().__init__(2)
        self.msg = msg

    def __str__(self) -> str:
        return self.msg


def confirm_or_abort(estimate_usd: float, budget_usd: float, *, confirm_expensive: bool,
                     hard_line: float = HARD_LINE_USD, confirmed_by: Optional[str] = None) -> float:
    """Gate an estimated spend.  Returns the cap the run should enforce.

    * estimate <= budget: allowed; cap = budget.
    * budget < estimate <= hard_line: needs ``confirm_expensive``; cap =
      1.5 x estimate (the first-of-kind margin of the judge-cost rule).
    * estimate > hard_line: needs ``confirm_expensive`` **and**
      ``confirmed_by`` (Roger's go, recorded in run.json).
    * Without ``confirmed_by`` the returned cap never exceeds ``hard_line``
      (it is clamped), and a typed ``budget_usd`` above ``hard_line`` is
      refused, whatever the estimate (review_m1.md finding 3).
    Refusals raise :class:`CostRefused` (a ``SystemExit`` with code 2).
    """
    if estimate_usd > hard_line and not (confirm_expensive and confirmed_by):
        raise CostRefused(
            f"estimate ${estimate_usd:.2f} is over the ${hard_line:.0f} line: needs Roger's explicit go "
            f"in chat, then --confirm-expensive --confirmed-by '<who, when>'")
    if budget_usd > hard_line and not confirmed_by:
        raise CostRefused(
            f"--budget-usd ${budget_usd:.2f} is over the ${hard_line:.0f} line: a cap above it needs Roger's "
            f"explicit go in chat, recorded with --confirmed-by '<who, when>'")
    if estimate_usd > budget_usd:
        if not confirm_expensive:
            raise CostRefused(
                f"estimate ${estimate_usd:.2f} exceeds --budget-usd ${budget_usd:.2f}: raise the budget "
                f"or pass --confirm-expensive")
        cap = round(1.5 * estimate_usd, 4)
    else:
        cap = budget_usd
    if not confirmed_by:
        cap = min(cap, hard_line)
    return cap
