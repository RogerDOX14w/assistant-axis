"""``judge_comparison.xy_mark``: the arm reading sheets' X / Y verdicts as good / bad data (2026-10-26)."""
from __future__ import annotations

from results_analysis.judge_comparison import xy_mark


def test_the_right_score_decides_good_or_bad():
    item = {"a0_score": 3, "arm_score": 2, "x_is": "A0"}
    assert xy_mark("X", item) == "G"          # A0's 3 was right
    assert xy_mark("Y", item) == "B"          # the arm's 2 was right
    flipped = {"a0_score": 3, "arm_score": 2, "x_is": "A3"}
    assert xy_mark("X", flipped) == "B"       # X is now the arm
    assert xy_mark("Y ", flipped) == "G"


def test_borderline_unsure_and_skips():
    item = {"a0_score": 1, "arm_score": 3, "x_is": "A0"}
    assert xy_mark("T", item) == "T" and xy_mark("?", item) == "?"
    assert xy_mark("SKIP", item) is None and xy_mark("", item) is None


def test_kappa_is_agreement_beyond_chance():
    from results_analysis.judge_comparison import kappa
    assert kappa(50, 0, 0, 50) == 1.0                     # perfect agreement
    assert abs(kappa(25, 25, 25, 25)) < 1e-12             # coin flips: chance level
    # 90% raw agreement at a 90% keep rate is no better than chance
    assert abs(kappa(81, 9, 9, 1)) < 1e-12
    assert kappa(0, 0, 0, 0) != kappa(0, 0, 0, 0)         # nan when empty


def test_auc_counts_ties_half():
    from results_analysis.judge_comparison import auc
    assert auc([3, 3], [0, 1]) == 1.0
    assert auc([3], [3]) == 0.5
    assert auc([3, 1], [2]) == 0.5
    assert auc([], [1]) != auc([], [1])                   # nan when a side is empty
