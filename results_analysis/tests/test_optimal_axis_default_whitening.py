"""``optimal_axis_for_judge.py``'s default whitening is soft_K=3, read from the
one named constant ``whitening.OPTIMAL_AXIS_SOFT_K`` (walk-through D6,
2026-10-12: every recorded run of the script used soft_K=3; review 9a D7
found a bare literal disagreeing with ``DEFAULT_SOFT_K=2`` unexplained).
"""
from __future__ import annotations

import re
from pathlib import Path

from results_analysis import optimal_axis_for_judge as oafj
from results_analysis.canonical_angles import whitening

REPO = Path(__file__).resolve().parents[2]


def test_optimal_axis_soft_k_is_3():
    assert whitening.OPTIMAL_AXIS_SOFT_K == 3


def test_default_whitening_comes_from_the_constant():
    assert oafj.DEFAULT_WHITENING == f"soft_K={whitening.OPTIMAL_AXIS_SOFT_K}"
    assert oafj.parse_whitening_spec(oafj.DEFAULT_WHITENING) == ("soft_K", 3)


def test_project_default_unchanged():
    """The exception does not move the project-wide soft-K default."""
    assert whitening.DEFAULT_SOFT_K == 2


def test_no_literal_soft_k_default_in_the_script():
    src = (REPO / "results_analysis" / "optimal_axis_for_judge.py").read_text()
    assert not re.search(r'^DEFAULT_WHITENING\s*=\s*["\']soft_K=\d', src, re.M)


def test_default_output_dir_matches_the_recorded_runs():
    """A default run keys its output on soft_K=3, as the five recorded
    ``..._softK3_M30_...`` directories do."""
    assert oafj._slug_whitening(oafj.DEFAULT_WHITENING) == "softK3"
