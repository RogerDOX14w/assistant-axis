"""``pc_round_trip/launch_judge_runs.py`` exits non-zero when a cell fails
(review of 2026-10-12: it printed "FAIL rc=..." and returned 0).

No judge is called: ``subprocess.run`` is replaced by a stub.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from results_analysis.pc_round_trip import launch_judge_runs


def _sweep_dir(root: Path) -> Path:
    cell = root / "pc001_inline"
    cell.mkdir(parents=True)
    (cell / "spec.json").write_text(json.dumps({
        "axis_name": "x vs y",
        "pos_pole_standardized": "This means x.",
        "neg_pole_standardized": "This means y.",
        "pos_examples": ["helpful"], "neg_examples": ["unhelpful"],
    }))
    return root


@pytest.mark.parametrize("rc, expected", [(0, 0), (2, 1)])
def test_exit_status_reflects_cell_failures(tmp_path, monkeypatch, rc,
                                            expected):
    sweep = _sweep_dir(tmp_path / "sweep")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=rc)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [
        "launch_judge_runs.py", "--skip_setup", "--sweep_dir", str(sweep),
        "--pcs", "1", "--styles", "inline", "--providers", "openai",
        "--max_parallel", "1",
    ])
    assert launch_judge_runs.main() == expected
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Walk-through D7 (review 9a D8): every judge subprocess gets --budget_usd.
# ---------------------------------------------------------------------------

def _run_capturing(tmp_path, monkeypatch, extra_argv, providers="openai,anthropic"):
    sweep = _sweep_dir(tmp_path / "sweep")
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [
        "launch_judge_runs.py", "--skip_setup", "--sweep_dir", str(sweep),
        "--pcs", "1", "--styles", "inline", "--providers", providers,
        "--max_parallel", "1", *extra_argv,
    ])
    assert launch_judge_runs.main() == 0
    return calls


def _flag(cmd, name):
    return cmd[cmd.index(name) + 1]


def test_default_budget_per_provider(tmp_path, monkeypatch):
    calls = _run_capturing(tmp_path, monkeypatch, [])
    assert len(calls) == 2
    by_provider = {_flag(c, "--provider"): float(_flag(c, "--budget_usd")) for c in calls}
    assert by_provider == launch_judge_runs.DEFAULT_BUDGET_USD_PER_CELL


def test_budget_override_reaches_every_cell(tmp_path, monkeypatch):
    calls = _run_capturing(tmp_path, monkeypatch, ["--budget_usd", "2.5"])
    assert [float(_flag(c, "--budget_usd")) for c in calls] == [2.5, 2.5]


def test_budget_must_be_positive(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        _run_capturing(tmp_path, monkeypatch, ["--budget_usd", "0"])


def test_dry_run_prints_the_cap(tmp_path, monkeypatch, capsys):
    sweep = _sweep_dir(tmp_path / "sweep")
    monkeypatch.setattr(sys, "argv", [
        "launch_judge_runs.py", "--dry_run", "--sweep_dir", str(sweep),
        "--pcs", "1", "--styles", "inline", "--providers", "anthropic",
    ])
    assert launch_judge_runs.main() == 0
    out = capsys.readouterr().out
    assert "--budget_usd 19" in out
    assert "ceiling over all cells $19.00" in out


def test_budget_flag_is_accepted_by_the_judge_script():
    """The flag the launcher passes is one axis_judge_correlation.py parses."""
    from results_analysis import axis_judge_correlation as ajc
    cmd = launch_judge_runs.build_command(
        data_dir=Path("d"), sweep_dir=Path("s"), pc=1, style="inline",
        provider="openai", layer=25, spec={
            "pos_pole_standardized": "x", "neg_pole_standardized": "y",
            "pos_examples": ["a"], "neg_examples": ["b"]},
        batch_size=20, rps=10.0, save_every=40, max_tokens=1024,
        temperature=0.0, whiten_K=0, budget_usd=6.0)
    argv = cmd[cmd.index("results_analysis/axis_judge_correlation.py") + 1:]
    old = sys.argv
    try:
        sys.argv = ["axis_judge_correlation.py", *argv]
        args = ajc.parse_args()
    finally:
        sys.argv = old
    assert args.budget_usd == 6.0
