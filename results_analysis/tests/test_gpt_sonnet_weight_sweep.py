"""``gpt_sonnet_weight_sweep._one_judge_di_scores``: migrate each cache to
entity ids before the desc/inst combine (review of 2026-10-12).

Combining first treated a bare ``"x"`` (v1 cache) and ``"x|T"`` (v2 cache)
as two entities, each kept at 100% of its one mode, and the later
migration then overwrote one with the other.
"""
from __future__ import annotations

import pytest

from results_analysis.gpt_sonnet_weight_sweep import _one_judge_di_scores

KINDS = {"helpful": {"traits"}, "angel": {"roles"},
         "patient": {"traits", "roles"}}
W = (0.499, 0.501)


def test_mixed_v1_desc_v2_inst_is_combined_not_overwritten():
    desc_v1 = {"helpful": 3, "angel": -1, "patient": 2}
    inst_v2 = {"helpful|T": 1, "angel|R": 1, "patient|T": 0}
    out = _one_judge_di_scores(desc_v1, inst_v2, weights=W,
                               kinds_for_name=KINDS)
    assert out["helpful|T"] == pytest.approx(0.499 * 3 + 0.501 * 1)
    assert out["angel|R"] == pytest.approx(0.499 * -1 + 0.501 * 1)
    # The v1 collision entry is dropped; the v2 one survives on its own.
    assert out["patient|T"] == pytest.approx(0.0)
    assert set(out) == {"helpful|T", "angel|R", "patient|T"}


def test_pure_v1_and_pure_v2_unchanged():
    v1 = _one_judge_di_scores({"helpful": 3}, {"helpful": 1}, weights=W,
                              kinds_for_name=KINDS)
    v2 = _one_judge_di_scores({"helpful|T": 3}, {"helpful|T": 1}, weights=W,
                              kinds_for_name=KINDS)
    assert v1 == v2 == {"helpful|T": pytest.approx(0.499 * 3 + 0.501 * 1)}
