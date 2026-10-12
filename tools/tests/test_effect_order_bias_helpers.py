"""Tests for the record-reading helpers of tools/test_effect_order_bias.py
(no API calls).  The module's own name starts with ``test_`` but it is a
CLI, not a test file; this file covers its pure helpers."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import test_effect_order_bias as eob  # noqa: E402


def test_v7_record_uses_the_straight_mean_not_the_averaged_combined() -> None:
    """Regression (2026-10-12): on v7 records ``combined`` is
    ``(straight - swap) / 2``; the diagnostic compares a fresh swap score
    with the ORIGINAL straight score."""
    eff = {
        "bidirectional": {
            "straight": {"scores": {"m": {"score": 2}, "mean": 2.0}},
            "swap": {"scores": {"m": {"score": 1}, "mean": 1.0}},
            "averaged": 0.5,
        },
        "combined": 0.5,
    }
    assert eob.original_straight_score(eff) == 2.0


def test_v6_record_uses_its_scores_mean_or_combined() -> None:
    assert eob.original_straight_score(
        {"bidirectional": {"scores": {"mean": -1.5}}, "combined": -1.5}) == -1.5
    assert eob.original_straight_score({"combined": 1.0}) == 1.0


def test_missing_scores_give_none() -> None:
    assert eob.original_straight_score({}) is None
    assert eob.original_straight_score(
        {"bidirectional": {"straight": {"scores": {"mean": None}}},
         "combined": 0.3}) is None


def test_gather_swap_items_reads_straight_scores(tmp_path: Path) -> None:
    exp = tmp_path / "exp"
    (exp / "baselines").mkdir(parents=True)
    (exp / "baselines" / "records.jsonl").write_text(
        json.dumps({"question_idx": 0, "response": "base"}) + "\n")
    cell = exp / "s3_l25_+1"
    cell.mkdir()
    rec = {"strength": 2.0, "question_idx": 0, "question": "q", "response": "r",
           "judges": {"effect": {"bidirectional": {
               "straight": {"scores": {"mean": 3.0}}, "averaged": 1.0},
               "combined": 1.0}}}
    (cell / "records.jsonl").write_text(json.dumps(rec) + "\n")
    (item,) = eob.gather_swap_items(exp)
    assert item.orig_combined == 3.0 and item.sign == 1
    assert item.baseline_response == "base"
