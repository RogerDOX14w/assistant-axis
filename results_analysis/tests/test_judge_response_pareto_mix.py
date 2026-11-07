"""--judge mix of scripts/judge_response_pareto.py (2026-11-06): the settled-design dump's round trip, the split arms
(every share once, costs that add to one judge's worth, a style for every family) and the averaging of a split's
shifts.  Pure functions only: no cells, no projections, no network."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def jrp():
    spec = importlib.util.spec_from_file_location("judge_response_pareto", REPO / "scripts" / "judge_response_pareto.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_loaded(jrp):
    """{judge: (record, items by axis, cost parts)} as load_settled returns, for the four judges on two axes."""
    axes = ["a_vs_b", "c_vs_d"]
    loaded = {}
    for i, j in enumerate(jrp.MIX_JUDGES):
        items = {ax: {(f"e{n}", p, q): float((n * 7 + p + q + i) % 100) for n in range(5) for p in range(2) for q in range(3)}
                 for ax in axes}
        rec = {"judge": j, "model": f"model-{j}", "name": j, "arm": f"model-{j}@x", "label": j,
               "family": f"{jrp.MIX_SHORT[j]} alone, settled design"}
        loaded[j] = (rec, items, [(0.2, (10.0, 0.0)), (0.8, (4.0, 1.0))])
    return loaded


def test_dump_and_load_round_trip(jrp, tmp_path):
    loaded = fake_loaded(jrp)
    rec, items, cp = loaded["luna"]
    arm = dict(key=rec["arm"], label=rec["label"], family=rec["family"], cost_parts=cp)
    path = tmp_path / "settled61" / "luna.json.gz"
    jrp.dump_settled(path, "luna", rec["model"], rec["name"], arm, items, inputs=[], extra={"left_out": {"a_vs_b": 3}})
    rec2, items2, cp2 = jrp.load_settled(path)
    assert items2 == items and cp2 == cp
    assert rec2["arm"] == rec["arm"] and rec2["left_out"] == {"a_vs_b": 3}
    assert all(isinstance(k, tuple) and len(k) == 3 for ax in items2.values() for k in ax)


def test_mix_arms_shape_costs_and_styles(jrp):
    loaded = fake_loaded(jrp)
    arms = jrp.mix_arms(loaded)
    singles = [a for a in arms if a["key"].endswith("@settled")]
    splits = [a for a in arms if "@split" in a["key"]]
    assert len(singles) == 4 and len(splits) == 4 * 3 + 1 * 4       # four triples x 3 shifts, the quad x 4
    for a in splits:
        J = len(a["members"])
        assert sorted(share for _, _, share in a["members"]) == [("g", J, i) for i in range(J)]   # every share once
        assert abs(sum(f for f, _ in a["cost_parts"]) - 1.0) < 1e-9     # the shares' costs add to one judge's worth
    assert len({a["key"] for a in arms}) == len(arms)
    for a in arms:
        assert a["family"] in jrp.FAMILY_STYLE          # drawn with its own style, not rewritten as Luna's


def test_merge_shifts_averages_the_split_arms(jrp):
    vkeys = ["v1", "v2"]
    pts = {}
    for s, (r1, r2) in enumerate([(0.70, 0.80), (0.72, 0.84), (0.74, 0.82)]):
        pts[f"m1+m2+m3@split{s}|ninth x 3/3"] = dict(arm=f"m1+m2+m3@split{s}", label="L", family="F", coverage=1 / 9, m=3,
                                                   figures=["mix61"], measured=True, cost=100.0, rho={"v1": r1, "v2": r2},
                                                   per_axis={"v1": [r1 - 0.1, r1 + 0.1], "v2": [r2, r2]})
    pts["m1@settled|ninth x 3/3"] = dict(arm="m1@settled", rho={"v1": 0.5, "v2": 0.6}, cost=1.0, measured=True)
    merged = jrp.merge_shifts(pts, vkeys)
    assert set(merged) == {"m1+m2+m3@split|ninth x 3/3", "m1@settled|ninth x 3/3"}
    p = merged["m1+m2+m3@split|ninth x 3/3"]
    assert p["arm"] == "m1+m2+m3@split" and p["shifts"] == 3
    assert p["rho"] == pytest.approx({"v1": 0.72, "v2": 0.82})
    assert p["rho_shift_sd"]["v1"] == pytest.approx(np.std([0.70, 0.72, 0.74]))
    assert p["cost"] == 100.0
    assert p["per_axis"]["v1"] == pytest.approx([0.62, 0.82]) and p["per_axis"]["v2"] == pytest.approx([0.82, 0.82])
    assert merged["m1@settled|ninth x 3/3"]["rho"] == {"v1": 0.5, "v2": 0.6}


def test_penalty_law(jrp):
    """The question-cut penalty follows the (1/c - 1) law anchored at the measured gap at a ninth and zero at the third:
    delta9 at 1/9, four times it at 1/27, a quarter of it at 2/9, nothing at a third or above."""
    assert jrp.penalty(0.009, 1 / 9) == pytest.approx(0.009)
    assert jrp.penalty(0.009, 1 / 27) == pytest.approx(0.036)
    assert jrp.penalty(0.009, 2 / 9) == pytest.approx(0.009 * 1.5 / 6)
    assert jrp.penalty(0.009, 1 / 3) == 0.0 and jrp.penalty(0.009, 1.0) == 0.0


def test_arm_calibration_takes_the_arm_axes_and_the_pooled_fallback(jrp):
    """A judge with its own calibration contributes its per-axis penalty over the arm's axes (a missing axis at its mean);
    a judge without takes the pooled values; a mix arm averages its judges."""
    check = {"per_judge": {"m1": dict(judge="luna", delta9=0.010, delta9_by_axis={"a": 0.004, "b": 0.016}, ratio=1.01, s=1.2)},
             "pooled": dict(judge="pooled", delta9=0.007, delta9_by_axis={"a": 0.003, "b": 0.011}, ratio=1.02, s=1.0)}
    own = jrp.arm_calibration(check, ["m1"], ["a", "b"])
    assert own["delta9"] == pytest.approx(0.010) and own["s"] == 1.2 and own["judges"] == ["luna"]
    assert jrp.arm_calibration(check, ["m1"], ["a", "zz"])["delta9"] == pytest.approx((0.004 + 0.010) / 2)
    other = jrp.arm_calibration(check, ["m2"], ["a"])
    assert other["delta9"] == pytest.approx(0.003) and other["s"] == 1.0 and other["judges"] == ["pooled"]
    mix = jrp.arm_calibration(check, ["m1", "m2", "m1"], ["b"])
    assert mix["delta9"] == pytest.approx((0.016 + 0.011) / 2) and mix["s"] == pytest.approx(1.1) and mix["judges"] == ["luna", "pooled"]


def test_two_part_extrapolation_arithmetic(jrp):
    """From a cut ninth at rho 0.70 with split-half reliability 0.96: the lifted base is rho + delta9, its reliability
    R x ratio, and the coverage M x gains s x (sqrt(RM / R_g) - 1) of the lifted rho; from a third nothing is lifted."""
    import math
    cal = dict(delta9=0.008, ratio=1.0125, s=1.2)
    R, rho = 0.96, 0.70
    lift = jrp.penalty(cal["delta9"], 1 / 9)
    R_g = R * cal["ratio"]
    RM = 3 * R_g / (1 + 2 * R_g)
    expected_third = (rho + lift) * (1 + cal["s"] * (math.sqrt(RM / R_g) - 1))
    # the same arithmetic as arm_points, written out
    assert lift == pytest.approx(0.008) and expected_third > rho + lift
    assert jrp.penalty(cal["delta9"], 1 / 3) == 0.0


def test_subsample_by_question_share_is_the_split_part(jrp):
    """A ("q", 9, 0) share keeps exactly the questions with (q + entity rank) % 9 == 0 and the whole fraction (m = K):
    the third dump's part 0, which the calibration reads as the cut ninth (2026-11-07)."""
    rank = {"e0": 0, "e1": 4}
    qabs = {q: 3 * q for q in range(27)}
    items = {(n, p, q): float(q) for n in rank for p in range(2) for q in range(27)}
    items[("dup", 0, 0)] = 1.0                               # an entity without a rank (a collision name) is dropped
    part0 = jrp.subsample(items, rank, qabs, jrp.FRACTION_K, 0, ("q", 9, 0))
    assert set(part0) == {k for k in items if k[0] in rank and (k[2] + rank[k[0]]) % 9 == 0}
    assert {k[2] for k in part0 if k[0] == "e0"} == {0, 9, 18} and {k[2] for k in part0 if k[0] == "e1"} == {5, 14, 23}
    assert all(part0[k] == items[k] for k in part0)
