"""The estimators' sanity check (``assistant_axis/gapgen/testing/simulate.py``; coding plan 13, § 8 "simulate"):
a synthetic population caught by four occasions, 200 replicates per scenario.  Heterogeneous catchability makes
both estimators low on average; with equal catchability and independent occasions Chao2's interval covers the
truth in at least 90% of replicates; dependent occasions make the leave-one-occasion-out estimates move more."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen.testing import estimators as E
from assistant_axis.gapgen.testing import simulate as S


@pytest.fixture(scope="module")
def scenarios():
    return S.run_scenarios(N=2000, m_occ=4, sigma=1.0, rho=0.3, replicates=200, seed=0)


class TestSimulate:
    def test_seeded(self):
        a, b = S.simulate(N=500, seed=3), S.simulate(N=500, seed=3)
        assert a.incidence == b.incidence and a.Q == b.Q and a.n_by_occasion == b.n_by_occasion
        assert S.simulate(N=500, seed=4).incidence != a.incidence

    def test_shape(self):
        sim = S.simulate(N=1000, m_occ=5, seed=1)
        assert sim.N == 1000 and len(sim.n_by_occasion) == 5
        assert all(occ and occ <= set(range(5)) for occ in sim.incidence.values())
        assert all(0 <= c < 1000 for c in sim.incidence)
        assert sim.Q == E.incidence_counts(sim.incidence)
        assert sum(sim.n_by_occasion) == sum(len(o) for o in sim.incidence.values())

    def test_equal_catchability_is_bernoulli_at_p_mean(self):
        sim = S.simulate(N=20000, m_occ=4, sigma_catch=0.0, rho_occ=0.0, p_mean=0.2, seed=2)
        rates = np.array(sim.n_by_occasion) / 20000
        assert np.all(np.abs(rates - 0.2) < 0.015)
        k = np.arange(1, 5)                                   # Binomial(4, 0.2) frequencies
        expected = 20000 * np.array([4 * 0.2 * 0.8 ** 3, 6 * 0.04 * 0.64, 4 * 0.008 * 0.8, 0.0016])
        observed = np.array([sim.Q.get(int(i), 0) for i in k])
        assert np.all(np.abs(observed - expected) < 5 * np.sqrt(expected) + 2)

    def test_marginal_catch_rate_is_p_mean_in_every_scenario(self):
        for sigma, rho in [(1.0, 0.0), (1.0, 0.3), (0.0, 0.5)]:
            sim = S.simulate(N=20000, sigma_catch=sigma, rho_occ=rho, p_mean=0.15, seed=5)
            assert np.all(np.abs(np.array(sim.n_by_occasion) / 20000 - 0.15) < 0.015)

    def test_heterogeneity_raises_recaptures(self):
        """With the same marginal rate, heterogeneity makes the occasions overlap more (fewer distinct)."""
        flat = S.simulate(N=5000, sigma_catch=0.0, rho_occ=0.0, seed=7)
        het = S.simulate(N=5000, sigma_catch=1.0, rho_occ=0.0, seed=7)
        assert len(het.incidence) < len(flat.incidence)


class TestEstimates:
    def test_keys_and_consistency(self):
        sim = S.simulate(N=2000, seed=11)
        est = S.estimates(sim)
        assert est["chao2"]["N"] == pytest.approx(E.chao2(sim.Q, 4).N)
        n1 = sum(1 for o in sim.incidence.values() if 0 in o)
        n2 = sum(1 for o in sim.incidence.values() if 1 in o)
        m = sum(1 for o in sim.incidence.values() if {0, 1} <= o)
        assert est["chapman_01"]["N"] == pytest.approx(E.chapman(n1, n2, m).N)
        assert len(est["loo"]["N"]) == 4
        q0 = E.incidence_counts({c: o - {0} for c, o in sim.incidence.items()})
        assert est["loo"]["N"][0] == pytest.approx(E.chao2(q0, 3).N)
        assert est["loo"]["spread_rel"] == pytest.approx((max(est["loo"]["N"]) - min(est["loo"]["N"]))
                                                         / est["chao2"]["N"])


    def test_a_history_without_bitmasks(self):
        """A SimResult built by hand (no ``patterns``) gives the same estimates."""
        sim = S.simulate(N=800, seed=12)
        bare = S.SimResult(incidence=sim.incidence, Q=sim.Q, N=sim.N, n_by_occasion=sim.n_by_occasion, m_occ=4)
        assert S.estimates(bare) == S.estimates(sim)

    def test_rejects_bad_parameters(self):
        for kw in ({"m_occ": 1}, {"rho_occ": 1.5}, {"p_mean": 0.0}, {"sigma_catch": -1.0},
                   {"dependent_occasions": [7]}):
            with pytest.raises(ValueError):
                S.simulate(N=10, **kw)


class TestScenarios:
    def test_heterogeneous_catchability_makes_both_estimators_low(self, scenarios):
        for name in ("heterogeneous_independent", "heterogeneous_correlated"):
            for est in ("chao2", "chapman_01"):
                rec = scenarios["scenarios"][name]["check"]["estimators"][est]
                assert rec["bias_sign"] == -1 and rec["mean_bias"] < 0, (name, est, rec)

    def test_equal_independent_chao2_interval_covers(self, scenarios):
        rec = scenarios["scenarios"]["equal_independent"]["check"]["estimators"]["chao2"]
        assert rec["coverage"] >= 0.90, rec
        assert abs(rec["mean_bias"]) < 0.03, rec                  # and is about unbiased

    def test_leave_one_out_moves_more_under_correlated_occasions(self, scenarios):
        """Same heterogeneity, with and without the dependent occasions' shared bias.  (Not against
        ``equal_independent``: there Chao2 is unbiased but noisier, and its spread is mostly sampling noise.)"""
        s = scenarios["scenarios"]
        corr, ind = s["heterogeneous_correlated"]["check"], s["heterogeneous_independent"]["check"]
        assert corr["loo_spread"]["mean"] > 1.3 * ind["loo_spread"]["mean"]
        # Leaving out occasion 0, the only one outside the dependent block, leaves three mutually dependent
        # occasions and the lowest estimate; under independence no occasion stands out.
        by_occ = corr["loo_mean_N_by_left_out"]
        assert by_occ[0] < min(by_occ[1:]) - 0.03 * 2000
        assert max(ind["loo_mean_N_by_left_out"]) - min(ind["loo_mean_N_by_left_out"]) < 0.02 * 2000

    def test_payload_is_json_and_deterministic(self, scenarios):
        assert json.loads(json.dumps(scenarios)) == scenarios
        assert scenarios["params"]["replicates"] == 200 and scenarios["params"]["seed"] == 0
        assert set(scenarios["scenarios"]) == {"equal_independent", "heterogeneous_independent",
                                               "heterogeneous_correlated"}
        again = S.run_scenarios(N=300, replicates=5, seed=9)
        assert again == S.run_scenarios(N=300, replicates=5, seed=9)
        assert again != S.run_scenarios(N=300, replicates=5, seed=10)


class TestCheckAndTable:
    def test_check_on_hand_made_results(self):
        results = [{"chao2": {"N": 90.0, "lo": 80.0, "hi": 105.0}, "chapman_01": {"N": 95.0, "lo": 70.0, "hi": 99.0},
                    "loo": {"spread_rel": 0.1}},
                   {"chao2": {"N": 100.0, "lo": 90.0, "hi": 99.0}, "chapman_01": {"N": 85.0, "lo": 60.0, "hi": 110.0},
                    "loo": {"spread_rel": 0.3}}]
        out = S.check(results, truth=100)
        assert out["estimators"]["chao2"]["mean_N"] == pytest.approx(95.0)
        assert out["estimators"]["chao2"]["mean_bias"] == pytest.approx(-0.05)
        assert out["estimators"]["chao2"]["bias_sign"] == -1
        assert out["estimators"]["chao2"]["coverage"] == pytest.approx(0.5)
        assert out["estimators"]["chapman_01"]["coverage"] == pytest.approx(0.5)
        assert out["loo_spread"]["mean"] == pytest.approx(0.2)
        assert "loo_mean_N_by_left_out" not in out                     # the hand-made results carry no LOO list
        assert out["n_replicates"] == 2

    def test_bias_table(self, scenarios):
        md = S.bias_table_markdown(scenarios)
        lines = md.strip().splitlines()
        assert lines[0].startswith("| scenario") and "bias" in lines[0] and "coverage" in lines[0]
        assert len([ln for ln in lines if ln.startswith("| ")]) == 1 + 6     # header + 3 scenarios x 2 estimators
        for name in scenarios["scenarios"]:
            assert name in md
