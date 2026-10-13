"""The population estimators of workstream 13 (``assistant_axis/gapgen/testing/estimators.py``; coding plan 13,
§ 6 "Estimates" and § 8 "concepts and estimators").  Hand-computed figures, the plan's baseline (four occasions,
Q = {1: 2513, 2: 375, 3: 41}), and the shape of the accumulation curve and its extrapolation.  No I/O."""
import math
from collections import Counter

import pytest

from assistant_axis.gapgen.testing import estimators as E

BASELINE_Q = {1: 2513, 2: 375, 3: 41}          # the plan's 4-edge concept table, "3+" read as 3


# --------------------------------------------------------------------------- Chapman

class TestChapman:
    def test_the_plans_example(self):
        est = E.chapman(10, 10, 5)
        assert est.N == pytest.approx(121 / 6 - 1)                    # 19.17, the plan's 19.2
        assert round(est.N, 1) == 19.2
        assert est.se == pytest.approx(math.sqrt(11 * 11 * 5 * 5 / (36 * 7)))
        assert 15 <= est.lo < est.N < est.hi                        # S = 10 + 10 - 5 = 15
        assert est.lo == pytest.approx(16.0, abs=0.05) and est.hi == pytest.approx(32.25, abs=0.05)

    def test_complete_overlap_is_the_observed_count(self):
        est = E.chapman(30, 30, 30)
        assert est.N == pytest.approx(30) and est.se == 0 and est.lo == est.hi == 30

    def test_never_below_the_observed_distinct(self):
        for n1, n2, m in [(5, 50, 0), (40, 12, 3), (100, 100, 99), (7, 7, 1)]:
            est = E.chapman(n1, n2, m)
            assert est.N >= n1 + n2 - m - 1e-9 and est.lo >= n1 + n2 - m - 1e-9 and est.hi >= est.N

    def test_less_overlap_means_a_larger_population(self):
        assert E.chapman(100, 100, 10).N > E.chapman(100, 100, 40).N

    def test_rejects_an_impossible_overlap(self):
        with pytest.raises(ValueError):
            E.chapman(5, 10, 6)
        with pytest.raises(ValueError):
            E.chapman(-1, 10, 0)

    def test_as_dict_is_rounded(self):
        d = E.chapman(10, 10, 5).as_dict()
        assert d == {"N": 19.2, "se": round(math.sqrt(3025 / 252), 1), "lo": d["lo"], "hi": d["hi"]}
        assert set(d) == {"N", "se", "lo", "hi"} and all(isinstance(v, float) for v in d.values())


# --------------------------------------------------------------------------- Chao2

class TestChao2:
    def test_the_baseline_bias_corrected_and_classic(self):
        est = E.chao2(BASELINE_Q, 4)
        assert est.N == pytest.approx(9225, abs=1)
        assert E.chao2_classic(BASELINE_Q, 4) == pytest.approx(9244, abs=1)
        assert 2929 <= est.lo < est.N < est.hi and est.se > 0

    def test_bias_corrected_formula(self):
        Q = Counter({1: 10, 2: 4, 3: 1})
        S, A = 15, 2 / 3
        assert E.chao2(Q, 3).N == pytest.approx(S + A * 10 * 9 / (2 * 5))

    def test_no_doubletons_uses_the_corrected_form(self):
        Q = {1: 12, 3: 2}
        est = E.chao2(Q, 4)
        assert math.isfinite(est.N) and math.isfinite(est.se)
        assert est.N == pytest.approx(14 + 0.75 * 12 * 11 / 2)
        assert E.chao2_classic(Q, 4) == pytest.approx(est.N)       # the classic form falls back
        assert est.lo >= 14 and est.hi > est.N

    def test_bias_corrected_variance(self):
        """The bias-corrected variance (Chao 1987; the form EstimateS uses), for Q2 > 0 and for Q2 = 0."""
        Q1, Q2, m = 20, 5, 4
        A = (m - 1) / m
        var = (A * Q1 * (Q1 - 1) / (2 * (Q2 + 1)) + A ** 2 * Q1 * (2 * Q1 - 1) ** 2 / (4 * (Q2 + 1) ** 2)
               + A ** 2 * Q1 ** 2 * Q2 * (Q1 - 1) ** 2 / (4 * (Q2 + 1) ** 4))
        assert E.chao2({1: Q1, 2: Q2}, m).se == pytest.approx(math.sqrt(var))
        est0 = E.chao2({1: Q1, 3: 4}, m)
        var0 = A * Q1 * (Q1 - 1) / 2 + A ** 2 * Q1 * (2 * Q1 - 1) ** 2 / 4 - A ** 2 * Q1 ** 4 / (4 * est0.N)
        assert est0.se == pytest.approx(math.sqrt(var0))

    def test_no_singletons_is_the_observed_count(self):
        est = E.chao2({2: 7, 3: 3}, 3)
        assert est.N == 10 and est.lo == est.hi == 10

    def test_empty(self):
        est = E.chao2({}, 4)
        assert est.N == 0 and est.lo == est.hi == 0

    def test_rejects_a_frequency_outside_the_occasions(self):
        with pytest.raises(ValueError):
            E.chao2({1: 3, 5: 1}, 4)
        with pytest.raises(ValueError):
            E.chao2({0: 3, 1: 1}, 4)


# --------------------------------------------------------------------------- incidence and coverage

class TestIncidenceAndCoverage:
    def test_incidence_counts(self):
        occ = {"a": {"lexicon"}, "b": {"lexicon", "ipip"}, "c": ["ipip", "ipip"], "d": set(),
               "e": {"lexicon", "ipip", "base_model"}}
        assert E.incidence_counts(occ) == Counter({1: 2, 2: 1, 3: 1})

    def test_coverage_of_the_baseline(self):
        cov = E.coverage_from_Q(BASELINE_Q)
        assert cov == pytest.approx(1 - 2513 / (2513 + 2 * 375 + 3 * 41))
        assert round(cov, 2) == 0.26

    def test_coverage_bounds(self):
        assert E.good_turing_coverage(0, 0) == 0.0
        assert E.good_turing_coverage(5, 5) == 0.0
        assert E.good_turing_coverage(0, 12) == 1.0
        for q1, inc in [(3, 10), (9, 10), (1, 1000)]:
            assert 0.0 <= E.good_turing_coverage(q1, inc) <= 1.0
        assert E.coverage_from_Q({}) == 0.0


# --------------------------------------------------------------------------- accumulation and extrapolation

ORDER = ["k1", "k2", "x", "k3", "k4", "k5", "k6", "k7", "k8"]
CONCEPT = {"k1": "A", "k2": "B", "k3": "A", "k4": "C", "k5": "B", "k6": "D", "k7": "D", "k8": "E"}


class TestAccumulation:
    def test_step_one(self):
        curve = E.accumulation(ORDER, CONCEPT)
        assert curve == [(1, 1), (2, 2), (3, 2), (4, 3), (5, 3), (6, 4), (7, 4), (8, 5)]   # "x" skipped

    def test_step_keeps_the_last_point(self):
        curve = E.accumulation(ORDER, CONCEPT, step=3)
        assert curve == [(3, 2), (6, 4), (8, 5)]
        assert E.accumulation(ORDER, CONCEPT, step=4) == [(4, 3), (8, 5)]

    def test_non_decreasing_and_unknown_keys_skipped(self):
        order = [f"c{i}" for i in range(200)] + ["missing"] * 5
        concept = {f"c{i}": (i * 7919) % 53 for i in range(200)}
        curve = E.accumulation(order, concept, step=7)
        ns, us = zip(*curve)
        assert all(a < b for a, b in zip(ns, ns[1:])) and all(a <= b for a, b in zip(us, us[1:]))
        assert curve[-1] == (200, 53)

    def test_empty(self):
        assert E.accumulation([], CONCEPT) == [] and E.accumulation(["x"], CONCEPT) == []

    def test_abundance_counts(self):
        assert E.abundance_counts(ORDER, CONCEPT) == Counter({2: 3, 1: 2})     # A, B, D twice; C, E once


class TestExtrapolation:
    CURVE = [(10, 8), (20, 15), (30, 21), (40, 26)]

    def f0(self, n, Q1, Q2):
        return (n - 1) / n * (Q1 * Q1 / (2 * Q2) if Q2 else Q1 * (Q1 - 1) / 2)

    def test_starts_at_the_last_point_and_is_bounded(self):
        ext = E.chao_extrapolate(self.CURVE, Q1=14, Q2=6, to_n=80)
        assert ext[0] == (40, 26.0) and ext[-1][0] == 80
        bound = 26 + self.f0(40, 14, 6)
        ns, us = zip(*ext)
        assert all(a < b for a, b in zip(ns, ns[1:])) and all(a <= b for a, b in zip(us, us[1:]))
        assert all(u <= bound + 1e-9 for u in us) and us[-1] > 26

    def test_formula(self):
        Q1, Q2, n, S = 14, 6, 40, 26
        f0 = self.f0(n, Q1, Q2)
        expected = S + f0 * (1 - (1 - Q1 / (n * f0 + Q1)) ** 40)
        assert E.chao_extrapolate(self.CURVE, Q1=Q1, Q2=Q2, to_n=80)[-1][1] == pytest.approx(expected)

    def test_no_doubletons_and_no_singletons(self):
        ext = E.chao_extrapolate(self.CURVE, Q1=5, Q2=0, to_n=80)
        assert ext[-1][1] <= 26 + self.f0(40, 5, 0) + 1e-9 and ext[-1][1] > 26
        flat = E.chao_extrapolate(self.CURVE, Q1=0, Q2=3, to_n=80)
        assert all(u == 26.0 for _, u in flat) and flat[-1][0] == 80

    def test_points_and_short_targets(self):
        ext = E.chao_extrapolate(self.CURVE, Q1=14, Q2=6, to_n=80, points=4)
        assert [n for n, _ in ext] == [40, 50, 60, 70, 80]
        assert E.chao_extrapolate(self.CURVE, Q1=14, Q2=6, to_n=40) == [(40, 26.0)]
        assert E.chao_extrapolate([], Q1=1, Q2=1, to_n=10) == []

    def test_continues_a_real_curve(self):
        curve = E.accumulation(ORDER, CONCEPT)
        Q = E.abundance_counts(ORDER, CONCEPT)
        ext = E.chao_extrapolate(curve, Q1=Q[1], Q2=Q[2], to_n=16)
        assert ext[0] == (curve[-1][0], float(curve[-1][1])) and ext[-1][1] >= curve[-1][1]


class TestEndSlope:
    def test_hand_made_curve(self):
        curve = [(10, 10), (20, 18), (30, 24), (40, 28), (50, 30)]
        assert E.end_slope(curve, 10) == pytest.approx(0.2)
        assert E.end_slope(curve, 20) == pytest.approx((30 - 24) / 20)
        assert E.end_slope(curve, 15) == pytest.approx((30 - 24) / 20)    # nearest point at or before 35 is 30

    def test_too_short(self):
        assert E.end_slope([], 5) == 0.0
        assert E.end_slope([(10, 4)], 5) == 0.0
        assert E.end_slope([(10, 4), (20, 9)], 15) == 0.0                # nothing at or before 5

    def test_window_must_be_positive(self):
        with pytest.raises(ValueError):
            E.end_slope([(1, 1), (2, 2)], 0)


# --------------------------------------------------------------------------- assumptions

def test_assumptions_are_the_four_statements():
    a = E.ASSUMPTIONS
    assert isinstance(a, tuple) and len(a) == 4 and all(isinstance(s, str) and s.endswith(".") for s in a)
    text = " ".join(a).lower()
    assert "closed" in a[0].lower()
    assert "equal catchability" in a[1].lower() and "low" in a[1].lower()
    assert "independent" in a[2].lower() and "llm" in a[2].lower() and "low" in a[2].lower()
    assert "lower bound" in a[3].lower() and "generators of these kinds can reach" in a[3]
    assert "—" not in text and "–" not in text
