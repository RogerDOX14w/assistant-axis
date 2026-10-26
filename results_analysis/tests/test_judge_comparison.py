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
