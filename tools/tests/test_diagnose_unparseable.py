"""Tests for the record-scanning part of tools/diagnose_unparseable.py
(no API calls)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import diagnose_unparseable as du  # noqa: E402

MODELS = ["gpt-4.1-mini", "claude-haiku-4-5-20251001"]


def _v7(gpt, haiku, skipped=False):
    scores = {}
    if gpt != "absent":
        scores["gpt-4.1-mini"] = {"score": gpt, "reason": "r"}
    if haiku != "absent":
        scores["claude-haiku-4-5-20251001"] = {"score": haiku, "reason": "r"}
    return {"judges": {"effect": {
        "bidirectional": {"straight": {"scores": scores},
                          "swap": {"scores": {}}, "averaged": 0.0},
        "combined": 0.0,
        "skipped_due_to_strength_mean_coh": skipped,
    }}}


def _v6(gpt, haiku):
    return {"judges": {"effect": {"bidirectional": {"scores": {
        "gpt-4.1-mini": {"score": gpt}, "claude-haiku-4-5-20251001": {"score": haiku},
    }}}}}


def test_healthy_v7_records_show_no_failures() -> None:
    """Regression (2026-10-12): v7 keeps scores under
    ``bidirectional.straight``; reading only ``bidirectional.scores`` made
    every model look failed on every record."""
    fails, skip = du._fail_counts([_v7(2, 1), _v7(-1, 0)], MODELS)
    assert fails == {m: 0 for m in MODELS} and skip == 0


def test_v7_failures_counted_per_model() -> None:
    fails, _ = du._fail_counts([_v7(None, 1), _v7(None, None), _v7(2, 3)], MODELS)
    assert fails == {"gpt-4.1-mini": 2, "claude-haiku-4-5-20251001": 1}


def test_absent_entry_is_not_a_failure_and_skips_are_counted() -> None:
    fails, skip = du._fail_counts(
        [_v7("absent", 1), _v7(None, None, skipped=True)], MODELS)
    assert fails == {m: 0 for m in MODELS} and skip == 1


def test_legacy_v6_layout_still_read() -> None:
    fails, _ = du._fail_counts([_v6(None, 2), _v6(1, 2)], MODELS)
    assert fails == {"gpt-4.1-mini": 1, "claude-haiku-4-5-20251001": 0}
