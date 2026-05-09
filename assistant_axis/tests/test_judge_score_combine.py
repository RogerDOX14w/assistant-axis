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
    add_di_weights_arg,
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
    assert DEFAULT_GPT_HAIKU_Q9_WEIGHT == 0.60
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
