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
