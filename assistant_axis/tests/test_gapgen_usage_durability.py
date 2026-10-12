"""A killed process must not lose its spend (code review 2026-10-12, B3: reviews 1 D1 and 2 D3).

* ``GuardedUsage`` with a ``usage_path`` writes the file as it charges, at most every ``write_interval_s``, and
  every write is atomic;
* the SIGTERM handler the first ``GuardedUsage`` installs writes every live usage file, then raises
  ``SystemExit(143)`` so the CLI's ``finally`` runs;
* ``resume_usage`` starts a resume from the larger of ``usage.json`` and the response records, with a WARNING.

No network."""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from assistant_axis.gapgen import cost as C
from assistant_axis.gapgen.cost import GuardedUsage, resume_usage, usage_from_records
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage, cost_for_usage

HAIKU = "claude-haiku-4-5-20251001"
REPO = Path(__file__).resolve().parents[2]


def _calls(path: Path) -> int:
    return json.loads(path.read_text())["n_calls"]


class _Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


class TestThrottledWrites:
    def test_first_charge_writes_then_at_most_every_interval(self, tmp_path, monkeypatch):
        clock = _Clock()
        monkeypatch.setattr(C.time, "monotonic", clock)
        p = tmp_path / "usage.json"
        u = GuardedUsage(budget_usd=10.0, usage_path=p, write_interval_s=30.0)
        assert not p.exists()
        u.charge(HAIKU, 100, 10)
        assert _calls(p) == 1                                   # the first charge writes
        clock.t += 29
        u.charge(HAIKU, 100, 10)
        assert _calls(p) == 1                                   # within the interval: not yet
        clock.t += 1
        u.charge(HAIKU, 100, 10)
        assert _calls(p) == 3                                   # the interval has passed: the whole total
        assert json.loads(p.read_text()) == u.as_dict()

    def test_no_interval_means_no_writes_while_charging(self, tmp_path):
        p = tmp_path / "usage.json"
        u = GuardedUsage(budget_usd=10.0, usage_path=p, write_interval_s=None)
        u.charge(HAIKU, 100, 10)
        assert not p.exists()
        u.write_json(p)
        assert _calls(p) == 1

    def test_no_path_writes_nothing(self, tmp_path, monkeypatch):
        written = []
        monkeypatch.setattr("assistant_axis.atomic_io.atomic_write_text", lambda *a, **k: written.append(a))
        u = GuardedUsage(budget_usd=10.0)
        u.charge(HAIKU, 100, 10)
        assert written == []

    def test_a_resumed_total_is_what_the_file_holds(self, tmp_path):
        """Every CLI merges the earlier spend in before the first charge, so the throttled write carries it."""
        p = tmp_path / "usage.json"
        prior = MultiModelUsage()
        prior.charge(HAIKU, 1000, 100)
        u = GuardedUsage(budget_usd=10.0, usage_path=p)
        u.merge_from(prior)
        u.charge(HAIKU, 100, 10)
        assert _calls(p) == 2

    def test_writes_are_atomic(self, tmp_path, monkeypatch):
        import assistant_axis.atomic_io as A
        seen = []
        real = A.atomic_write_text

        def spy(text, path, *a, **k):
            seen.append(Path(path))
            return real(text, path, *a, **k)
        monkeypatch.setattr(A, "atomic_write_text", spy)
        p = tmp_path / "sub" / "usage.json"
        u = GuardedUsage(budget_usd=10.0, usage_path=p)
        u.charge(HAIKU, 100, 10)
        u.write_json(p)
        assert seen == [p, p] and _calls(p) == 1

    def test_the_budget_stop_still_writes_first(self, tmp_path):
        p = tmp_path / "usage.json"
        u = GuardedUsage(budget_usd=0.0, usage_path=p, write_interval_s=None)
        with pytest.raises(BudgetExceededError):
            u.charge(HAIKU, 100, 10)
        assert _calls(p) == 1


class TestSigterm:
    def test_the_handler_writes_every_live_usage_with_a_path_and_exits_143(self, tmp_path):
        a, b = tmp_path / "a.json", tmp_path / "b.json"
        ua = GuardedUsage(budget_usd=10.0, usage_path=a, write_interval_s=None)
        ub = GuardedUsage(budget_usd=10.0, usage_path=b, write_interval_s=None)
        GuardedUsage(budget_usd=10.0)                                            # no path: nothing to write
        ua.charge(HAIKU, 100, 10)
        ub.charge(HAIKU, 100, 10)
        ub.charge(HAIKU, 100, 10)
        with pytest.raises(SystemExit) as ei:
            C._on_sigterm(signal.SIGTERM, None)
        assert ei.value.code == 128 + signal.SIGTERM == 143
        assert _calls(a) == 1 and _calls(b) == 2

    def test_a_real_sigterm_writes_the_usage_and_runs_the_finally(self, tmp_path):
        """In a child process: SIGTERM mid-run leaves usage.json with the spend and the finally's marker."""
        usage, marker = tmp_path / "usage.json", tmp_path / "finally.txt"
        script = textwrap.dedent(f"""
            import os, signal, sys, time
            sys.path.insert(0, {str(REPO)!r})
            from assistant_axis.gapgen.cost import GuardedUsage
            u = GuardedUsage(budget_usd=10.0, usage_path={str(usage)!r}, write_interval_s=None)
            try:
                u.charge({HAIKU!r}, 100, 10)
                u.charge({HAIKU!r}, 100, 10)
                os.kill(os.getpid(), signal.SIGTERM)
                time.sleep(30)
            finally:
                open({str(marker)!r}, "w").write("ran")
        """)
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        assert r.returncode == 143, r.stderr
        assert _calls(usage) == 2 and marker.read_text() == "ran"
        assert "STOPPED by signal 15" in r.stderr

    def test_a_handler_someone_else_installed_is_left_alone(self, tmp_path):
        script = textwrap.dedent(f"""
            import signal, sys
            sys.path.insert(0, {str(REPO)!r})
            mine = lambda s, f: None
            signal.signal(signal.SIGTERM, mine)
            from assistant_axis.gapgen import cost
            cost.GuardedUsage(budget_usd=1.0)
            print(signal.getsignal(signal.SIGTERM) is mine, cost.install_sigterm_handler())
        """)
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert r.stdout.split() == ["True", "False"]


def _rec(model, raw, **kw):
    return {"charged_as": model, "usage_raw": raw, **kw}


class TestResumeUsage:
    RECS = [
        _rec(HAIKU, {"input_tokens": 300, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                     "output_tokens": 50}),
        _rec(HAIKU, {"input_tokens": 100, "cache_creation_input_tokens": 400, "cache_read_input_tokens": 1000,
                     "output_tokens": 20}),
        _rec(HAIKU + "@batch", {"input_tokens": 200, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                                "output_tokens": 30}),
        _rec(HAIKU + ":batch", {"input_tokens": 50, "cache_creation_input_tokens": 300,
                                "cache_creation_1h_input_tokens": 100, "cache_read_input_tokens": 0,
                                "output_tokens": 5}),
        _rec(None, {}, error="failed"),                       # a failed request: charged nothing
        _rec(HAIKU, {}),                                      # no usage recorded
    ]

    def test_records_are_charged_as_billed_usage_charges_them(self):
        u = usage_from_records(self.RECS)
        assert set(u.per_model) == {HAIKU, HAIKU + ":batch"}
        live = u.per_model[HAIKU]
        assert live.n_calls == 2 and live.prompt_tokens == 300 + (100 + 500 + 100) and live.completion_tokens == 70
        batch = u.per_model[HAIKU + ":batch"]
        # 1-hour writes at 2x, the rest at 1.25x
        assert batch.n_calls == 2 and batch.prompt_tokens == 200 + (50 + 250 + 200) and batch.completion_tokens == 35
        assert u.total_cost_usd == pytest.approx(cost_for_usage(HAIKU, 1000, 70)
                                                 + cost_for_usage(HAIKU + ":batch", 700, 35))

    def test_agrees_with_the_split_filters_cost_by_step(self):
        from assistant_axis.gapgen.split import cost_by_step
        recs = [dict(r, stage="sense") for r in self.RECS]
        by_step = cost_by_step(recs)
        assert sum(v["cost_usd"] for v in by_step.values()) == pytest.approx(usage_from_records(recs).total_cost_usd,
                                                                            abs=1e-5)

    def test_the_records_win_when_usage_json_is_short(self, caplog):
        recorded = MultiModelUsage()
        recorded.charge(HAIKU, 300, 50)                       # the killed session's calls never reached the file
        with caplog.at_level("WARNING", logger="assistant_axis.gapgen.cost"):
            out = resume_usage(recorded, self.RECS, where="filter/x")
        assert out.n_calls == 4
        assert "filter/x: usage.json records 1 calls" in caplog.text and "starts from the records" in caplog.text

    def test_usage_json_wins_when_it_holds_more(self, caplog):
        recorded = usage_from_records(self.RECS)
        recorded.charge(HAIKU, 5000, 500)                     # e.g. records of an older format the rebuild skips
        with caplog.at_level("WARNING", logger="assistant_axis.gapgen.cost"):
            out = resume_usage(recorded, self.RECS)
        assert out is recorded and "starts from usage.json" in caplog.text

    def test_no_warning_when_they_agree(self, caplog):
        recorded = usage_from_records(self.RECS)
        with caplog.at_level("WARNING", logger="assistant_axis.gapgen.cost"):
            out = resume_usage(recorded, self.RECS)
        assert out is recorded and caplog.text == ""


def test_m3_resume_merges_the_larger(tmp_path, caplog):
    """novelty_score's resumes (score, full-scan, broader-pilot) go through one helper."""
    from data_analysis.gap_generation import novelty_score as NS
    recorded = MultiModelUsage()
    recorded.charge(HAIKU, 300, 50)
    recorded.write_json(tmp_path / "usage.json")
    u = GuardedUsage(budget_usd=10.0, usage_path=tmp_path / "usage.json", write_interval_s=None)
    with caplog.at_level("WARNING", logger="assistant_axis.gapgen.cost"):
        NS._merge_earlier_usage(u, tmp_path, TestResumeUsage.RECS)
    assert u.n_calls == 4 and "starts from the records" in caplog.text
