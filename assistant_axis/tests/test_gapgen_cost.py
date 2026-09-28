"""gapgen.cost: GuardedUsage cap, usage.json on abort, confirmation gate."""
import json

import pytest

from assistant_axis.gapgen.cost import (
    CostRefused, Estimate, GuardedUsage, confirm_or_abort, estimate_calls_usd, format_estimate,
)
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage

HAIKU = "claude-haiku-4-5-20251001"


def test_guarded_usage_under_cap():
    g = GuardedUsage(budget_usd=1.0)
    g.charge(HAIKU, 1000, 100)
    assert g.n_calls == 1 and g.total_cost_usd == pytest.approx(0.0015)


def test_guarded_usage_raises_at_cap_and_writes_usage(tmp_path):
    path = tmp_path / "usage.json"
    g = GuardedUsage(budget_usd=0.01, usage_path=path)
    g.charge(HAIKU, 5000, 0)  # $0.005
    with pytest.raises(BudgetExceededError) as ei:
        g.charge(HAIKU, 6000, 0)  # $0.011 total
    assert "Budget cap exceeded" in str(ei.value)
    d = json.loads(path.read_text())
    assert d["n_calls"] == 2  # the call that crossed the cap is recorded
    assert d["total_cost_usd"] == pytest.approx(0.011)
    assert MultiModelUsage.load_or_create(path).n_calls == 2


def test_guarded_usage_no_cap():
    g = GuardedUsage()
    for _ in range(5):
        g.charge(HAIKU, 1_000_000, 0)
    assert g.total_cost_usd == pytest.approx(5.0)


def test_guarded_is_a_multimodelusage(tmp_path):
    g = GuardedUsage(budget_usd=10)
    g.charge("claude-sonnet-4-6", 1000, 1000)
    g.write_json(tmp_path / "u.json")
    d = json.loads((tmp_path / "u.json").read_text())
    assert set(d) == {"per_model", "total_cost_usd", "total_prompt_tokens", "total_completion_tokens", "n_calls"}


def test_estimates():
    assert estimate_calls_usd(HAIKU, 10, 2000, 3000) == pytest.approx(10 * (0.002 + 0.015))
    assert "12 x (2,000, 3,000) tokens at" in format_estimate(HAIKU, 12, 2000, 3000)
    e = Estimate()
    e.add("classifier", HAIKU, 2, 1000, 1000)
    e.add("probe", HAIKU, 0, 1000, 1000)
    assert len(e.lines) == 1 and e.usd == pytest.approx(0.012)
    assert "total estimate = $0.012" in e.format()


class TestConfirm:
    def test_under_budget(self):
        assert confirm_or_abort(0.5, 5.0, confirm_expensive=False) == 5.0

    def test_over_budget_refused_without_flag(self):
        with pytest.raises(CostRefused):
            confirm_or_abort(6.0, 5.0, confirm_expensive=False)
        with pytest.raises(SystemExit):
            confirm_or_abort(6.0, 5.0, confirm_expensive=False)

    def test_over_budget_with_flag_raises_cap(self):
        assert confirm_or_abort(6.0, 5.0, confirm_expensive=True) == pytest.approx(9.0)

    def test_over_hard_line_needs_flag_and_confirmed_by(self):
        with pytest.raises(CostRefused):
            confirm_or_abort(25.0, 5.0, confirm_expensive=False)
        with pytest.raises(CostRefused):
            confirm_or_abort(25.0, 5.0, confirm_expensive=True)
        with pytest.raises(CostRefused):
            confirm_or_abort(25.0, 50.0, confirm_expensive=False, confirmed_by="Roger 2026-09-28")
        assert confirm_or_abort(25.0, 50.0, confirm_expensive=True, confirmed_by="Roger 2026-09-28") == 50.0
        assert confirm_or_abort(25.0, 5.0, confirm_expensive=True,
                                confirmed_by="Roger") == pytest.approx(37.5)
