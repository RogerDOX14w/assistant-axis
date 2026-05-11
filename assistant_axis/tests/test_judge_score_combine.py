"""Tests for assistant_axis.judge_score_combine."""
import argparse
import math

import pytest

from assistant_axis.judge_score_combine import (
    DEFAULT_DI_WEIGHTS,
    DEFAULT_GPT_HAIKU_Q9_WEIGHT,
    DEFAULT_GPT_SONNET_DI_WEIGHT,
    DEFAULT_RESPONSE_DI_WEIGHT,
    DI_WEIGHTS_DESC_TIE,
    DI_WEIGHTS_EQUAL,
    DI_WEIGHTS_INST_TIE,
    PRIMARY_AXIS_SAMPLE_WEIGHT,
    add_di_weights_arg,
    cohort_mean_curves,
    combine_desc_inst_one_judge,
    combine_desc_inst_two_judges,
    parse_di_weights_arg,
)


def test_default_is_inst_tie():
    assert DEFAULT_DI_WEIGHTS == DI_WEIGHTS_INST_TIE
    assert DI_WEIGHTS_INST_TIE == (0.499, 0.501)
    assert DI_WEIGHTS_EQUAL == (0.5, 0.5)
    assert DI_WEIGHTS_DESC_TIE == (0.501, 0.499)


def test_parse_di_weights_arg():
    assert parse_di_weights_arg("inst_tie") == DI_WEIGHTS_INST_TIE
    assert parse_di_weights_arg("equal") == DI_WEIGHTS_EQUAL
    assert parse_di_weights_arg("desc_tie") == DI_WEIGHTS_DESC_TIE
    with pytest.raises(ValueError):
        parse_di_weights_arg("nonsense")


def test_combine_one_judge_equal():
    d = {"a": 2, "b": 0, "c": -1}
    i = {"a": 2, "b": 2, "c": 1}
    out = combine_desc_inst_one_judge(d, i, weights=(0.5, 0.5))
    assert out == {"a": 2.0, "b": 1.0, "c": 0.0}


def test_combine_one_judge_inst_tie():
    d = {"a": 2, "b": 0}
    i = {"a": 2, "b": 2}
    # 0.499 * 2 + 0.501 * 2 = 2.0  (no diff when d==i, that's the tiebreak property)
    # 0.499 * 0 + 0.501 * 2 = 1.002 (when they differ, inst gets slightly more weight)
    out = combine_desc_inst_one_judge(d, i)  # default = inst-tie
    assert out["a"] == pytest.approx(2.0)
    assert out["b"] == pytest.approx(1.002)


def test_combine_two_judges_default():
    g_d = {"x": 2, "y": -1}
    g_i = {"x": 2, "y":  3}
    s_d = {"x": 0, "y": -1}
    s_i = {"x": 2, "y":  3}
    # Default = inst-tie. Per entity:
    #   desc_avg = (g_d + s_d) / 2,  inst_avg = (g_i + s_i) / 2
    #   score = 0.499 * desc_avg + 0.501 * inst_avg
    out = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
    expected_x = 0.499 * (2+0)/2 + 0.501 * (2+2)/2
    expected_y = 0.499 * (-1+-1)/2 + 0.501 * (3+3)/2
    assert out["x"] == pytest.approx(expected_x)
    assert out["y"] == pytest.approx(expected_y)


def test_combine_two_judges_equal_matches_4way_mean():
    """Equal weighting must reproduce the historical (g_d + g_i + s_d + s_i) / 4."""
    g_d = {"a": 2, "b": -3, "c": 1}
    g_i = {"a": 0, "b":  1, "c": 2}
    s_d = {"a": -1, "b": -2, "c": 0}
    s_i = {"a": 3, "b": 0, "c": 1}
    out = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i, weights=(0.5, 0.5))
    for n in g_d:
        manual_4way = (g_d[n] + g_i[n] + s_d[n] + s_i[n]) / 4
        assert out[n] == pytest.approx(manual_4way), n


def test_combine_skips_missing_entities():
    """Only entities present in all four input dicts are included."""
    g_d = {"a": 1, "b": 1}
    g_i = {"a": 1}            # b missing here
    s_d = {"a": 1, "b": 1}
    s_i = {"a": 1, "b": 1}
    out = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
    assert set(out) == {"a"}


def test_combine_skips_non_numeric():
    g_d = {"a": 1, "b": 1}
    g_i = {"a": 1, "b": "oops"}
    s_d = {"a": 1, "b": 1}
    s_i = {"a": 1, "b": 1}
    out = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
    assert set(out) == {"a"}


def test_add_di_weights_arg():
    p = argparse.ArgumentParser()
    add_di_weights_arg(p)
    a = p.parse_args([])
    assert a.di_weights == "inst_tie"
    a = p.parse_args(["--di_weights", "equal"])
    assert a.di_weights == "equal"
    with pytest.raises(SystemExit):
        p.parse_args(["--di_weights", "garbage"])


def test_inst_tiebreak_only_matters_when_desc_neq_inst():
    """When desc and inst agree per entity, all three weight schemes give the same score.
    The asymmetry is a tiebreaker only for entities where the two modes disagree."""
    d = {"a": 2, "b": 0, "c": -3}
    i = {"a": 2, "b": 0, "c": -3}  # all agree
    eq = combine_desc_inst_one_judge(d, i, weights=DI_WEIGHTS_EQUAL)
    inst_tie = combine_desc_inst_one_judge(d, i, weights=DI_WEIGHTS_INST_TIE)
    desc_tie = combine_desc_inst_one_judge(d, i, weights=DI_WEIGHTS_DESC_TIE)
    for n in d:
        assert eq[n] == pytest.approx(inst_tie[n])
        assert eq[n] == pytest.approx(desc_tie[n])


def test_inst_tiebreak_weights_sum_to_one():
    for w in (DI_WEIGHTS_INST_TIE, DI_WEIGHTS_EQUAL, DI_WEIGHTS_DESC_TIE):
        assert math.isclose(sum(w), 1.0, abs_tol=1e-9)


def test_centralized_blend_constants_in_unit_interval():
    """All single-float blend weights must sit in [0, 1] and represent
    the empirical defaults documented in the module docstring + README."""
    assert DEFAULT_GPT_SONNET_DI_WEIGHT == 0.50
    # DEFAULT_GPT_HAIKU_Q9_WEIGHT was 0.60 pre-Phase-5d (v1 q9 sweep);
    # retuned to 0.41 on 2026-05-11 on the v2 mixed-cohort sweep
    # (actual parabolic peak w≈0.410, not rounded).  See
    # selection-history block in judge_score_combine module docstring.
    assert DEFAULT_GPT_HAIKU_Q9_WEIGHT == 0.41
    assert DEFAULT_RESPONSE_DI_WEIGHT == 0.80
    for w in (DEFAULT_GPT_SONNET_DI_WEIGHT,
              DEFAULT_GPT_HAIKU_Q9_WEIGHT,
              DEFAULT_RESPONSE_DI_WEIGHT):
        assert 0.0 <= w <= 1.0


def test_combine_two_judges_default_gs_matches_legacy_average():
    """At default ``gpt_sonnet_weight = 0.5`` the parameterised function
    must reproduce the historical hardcoded ``(gpt + sonnet) / 2``
    averaging exactly -- guards the strict-generalisation property."""
    g_d = {"x": 2, "y": -1, "z": 3}
    g_i = {"x": 2, "y":  3, "z": -2}
    s_d = {"x": 0, "y": -1, "z": -1}
    s_i = {"x": 2, "y":  3, "z": 1}
    out_param = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
    for n in g_d:
        # Manual legacy formula: (gd + sd) / 2 and (gi + si) / 2,
        # then 0.499 / 0.501 desc/inst combine.
        desc_avg = (g_d[n] + s_d[n]) / 2
        inst_avg = (g_i[n] + s_i[n]) / 2
        manual = 0.499 * desc_avg + 0.501 * inst_avg
        assert out_param[n] == pytest.approx(manual), n


def test_combine_two_judges_gs_weight_extremes():
    """At ``gpt_sonnet_weight = 1.0`` the score must collapse to GPT only;
    at ``gpt_sonnet_weight = 0.0`` it must collapse to Sonnet only."""
    g_d = {"x": 2, "y": -1}
    g_i = {"x": 2, "y":  3}
    s_d = {"x": 0, "y":  0}
    s_i = {"x": 0, "y":  0}
    only_gpt = combine_desc_inst_two_judges(
        g_d, g_i, s_d, s_i, gpt_sonnet_weight=1.0)
    only_sonnet = combine_desc_inst_two_judges(
        g_d, g_i, s_d, s_i, gpt_sonnet_weight=0.0)
    # With sonnet zeroed out and w_gs=1, only_gpt should equal the GPT-only
    # desc/inst combine of g_d, g_i.
    gpt_alone = combine_desc_inst_one_judge(g_d, g_i)
    for n in g_d:
        assert only_gpt[n] == pytest.approx(gpt_alone[n]), n
    # With Sonnet zeroed out and w_gs=0, only_sonnet picks up Sonnet only --
    # which is zero everywhere here.
    for n in g_d:
        assert only_sonnet[n] == pytest.approx(0.0), n


def test_combine_two_judges_gs_weight_intermediate_linear():
    """Score should be linear in gpt_sonnet_weight when desc and inst
    are held fixed across the two judges (no tiebreak interaction)."""
    g_d = {"x": 4}
    g_i = {"x": 4}        # GPT says 4 in both modes
    s_d = {"x": 0}
    s_i = {"x": 0}        # Sonnet says 0 in both modes
    # At w_gs in {0.0, 0.25, 0.5, 0.75, 1.0}, score should be 4 * w_gs.
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        out = combine_desc_inst_two_judges(
            g_d, g_i, s_d, s_i, gpt_sonnet_weight=w)
        assert out["x"] == pytest.approx(4.0 * w), w


# ---------------------------------------------------------------------------
# cohort_mean_curves: cross-axis averaging for ρ-vs-X plot overlays.
# ---------------------------------------------------------------------------

class TestCohortMeanCurves:
    """Three black overlays on the rho_vs_{whitening_K,shear_L} plots:
    (a) mean over responses, (b) mean over desc+inst, (c) blended mean
    with primary axes weighted 5x."""

    def test_primary_axis_constant_pattern(self):
        # 2 axes, both primary (have responses), 3 X-points each.
        # rho_rs = 1.0 everywhere, rho_di = 0.0 everywhere.
        # Expected:
        #   avg_rs = [1.0, 1.0, 1.0]
        #   avg_di = [0.0, 0.0, 0.0]
        #   avg_blend per axis = 0.8 * 1.0 + 0.2 * 0.0 = 0.8;
        #     both primary, so cross-axis mean = 0.8 at every X.
        pair_keys = [("a", "b"), ("c", "d")]
        rho_table = {
            ("a", "b", "responses"):  [1.0, 1.0, 1.0],
            ("a", "b", "desc_inst"):  [0.0, 0.0, 0.0],
            ("c", "d", "responses"):  [1.0, 1.0, 1.0],
            ("c", "d", "desc_inst"):  [0.0, 0.0, 0.0],
        }
        avg_rs, avg_di, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=1,
        )
        assert avg_rs == pytest.approx([1.0, 1.0, 1.0])
        assert avg_di == pytest.approx([0.0, 0.0, 0.0])
        assert avg_blend == pytest.approx([0.8, 0.8, 0.8])

    def test_di_only_axes_excluded_from_responses_mean(self):
        # 1 primary, 1 di-only.  Responses mean averages over the 1
        # primary axis only; di mean averages both.
        pair_keys = [("a", "b"), ("c", "d")]
        rho_table = {
            ("a", "b", "responses"):  [0.6],   # primary
            ("a", "b", "desc_inst"):  [0.4],
            ("c", "d", "responses"):  [float("nan")],   # di-only
            ("c", "d", "desc_inst"):  [0.2],
        }
        avg_rs, avg_di, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=1,
        )
        assert avg_rs == pytest.approx([0.6])
        assert avg_di == pytest.approx([(0.4 + 0.2) / 2])
        # blend = (5 * (0.8*0.6 + 0.2*0.4) + 1 * 0.2) / (5 + 1)
        #       = (5 * 0.56 + 0.2) / 6 = 3.0 / 6 = 0.5
        assert avg_blend == pytest.approx([(5 * (0.8 * 0.6 + 0.2 * 0.4) + 0.2) / 6])

    def test_primary_weight_actually_5x(self):
        # 1 primary axis with rho_blend=1.0, 1 di-only axis with
        # rho_di=0.0.  Weighted mean = (5 * 1.0 + 1 * 0.0) / 6 = 5/6.
        pair_keys = [("p", "q"), ("r", "s")]
        rho_table = {
            ("p", "q", "responses"):  [1.0],
            ("p", "q", "desc_inst"):  [1.0],  # blend = 0.8*1+0.2*1 = 1.0
            ("r", "s", "responses"):  [float("nan")],
            ("r", "s", "desc_inst"):  [0.0],
        }
        avg_rs, avg_di, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=1,
        )
        assert avg_blend == pytest.approx([5.0 / 6.0])
        # Sanity: the constant honored by the helper is the same constant
        # the rest of the project pins to.
        assert PRIMARY_AXIS_SAMPLE_WEIGHT == 5.0

    def test_response_di_weight_actually_080(self):
        # 1 primary axis, rho_rs=1, rho_di=0.  Per-axis blend = w_rs.
        pair_keys = [("p", "q")]
        rho_table = {
            ("p", "q", "responses"):  [1.0],
            ("p", "q", "desc_inst"):  [0.0],
        }
        _, _, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=1,
        )
        assert avg_blend == pytest.approx([DEFAULT_RESPONSE_DI_WEIGHT])
        assert DEFAULT_RESPONSE_DI_WEIGHT == 0.80

    def test_min_axes_threshold_yields_nan(self):
        # With min_axes=3 but only 2 axes provided, every X-point is NaN.
        pair_keys = [("a", "b"), ("c", "d")]
        rho_table = {
            ("a", "b", "responses"): [0.5],
            ("a", "b", "desc_inst"): [0.5],
            ("c", "d", "responses"): [0.5],
            ("c", "d", "desc_inst"): [0.5],
        }
        avg_rs, avg_di, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=3,
        )
        for v in avg_rs + avg_di + avg_blend:
            assert math.isnan(v)

    def test_per_x_nan_handled_per_curve(self):
        # X-point 0 has 2 of 2 primary axes finite; X-point 1 has only 1.
        # min_axes=2: X=0 gets a value, X=1 is NaN.
        pair_keys = [("a", "b"), ("c", "d")]
        rho_table = {
            ("a", "b", "responses"): [0.5, 0.5],
            ("a", "b", "desc_inst"): [0.5, 0.5],
            ("c", "d", "responses"): [0.5, float("nan")],
            ("c", "d", "desc_inst"): [0.5, 0.5],
        }
        avg_rs, _, _ = cohort_mean_curves(
            rho_table, pair_keys, min_axes=2,
        )
        assert avg_rs[0] == pytest.approx(0.5)
        assert math.isnan(avg_rs[1])

    def test_primary_axis_with_nan_response_falls_back_to_di(self):
        # Primary axis defined by having responses data SOMEWHERE on the
        # curve.  If responses is NaN at a specific X but di isn't, the
        # blend at that X falls back to di (at primary weight 5).
        pair_keys = [("a", "b"), ("c", "d")]
        rho_table = {
            ("a", "b", "responses"): [0.7, float("nan")],
            ("a", "b", "desc_inst"): [0.3, 0.3],
            ("c", "d", "responses"): [float("nan"), float("nan")],
            ("c", "d", "desc_inst"): [0.5, 0.5],
        }
        _, _, avg_blend = cohort_mean_curves(
            rho_table, pair_keys, min_axes=1,
        )
        # X=0: primary (a,b) blend = 0.8*0.7+0.2*0.3 = 0.62, w=5;
        #      di-only (c,d) blend = 0.5, w=1.
        # mean = (5*0.62 + 1*0.5) / 6 = (3.1 + 0.5) / 6 = 0.6
        assert avg_blend[0] == pytest.approx((5 * 0.62 + 0.5) / 6)
        # X=1: primary (a,b) has NaN response, falls back to di=0.3 at w=5;
        #      di-only (c,d) blend = 0.5 at w=1.
        # mean = (5*0.3 + 1*0.5) / 6 = (1.5 + 0.5) / 6 = 2/6
        assert avg_blend[1] == pytest.approx((5 * 0.3 + 0.5) / 6)

    def test_empty_inputs(self):
        # Empty rho_table or empty pair_keys returns empty lists.
        assert cohort_mean_curves({}, []) == ([], [], [])

    def test_returns_python_floats_not_numpy(self):
        # The helper should return plain Python floats so matplotlib's
        # NaN-skipping path works regardless of numpy version.
        pair_keys = [("a", "b")]
        rho_table = {
            ("a", "b", "responses"): [0.5],
            ("a", "b", "desc_inst"): [0.5],
        }
        avg_rs, _, _ = cohort_mean_curves(rho_table, pair_keys, min_axes=1)
        assert isinstance(avg_rs[0], float)
