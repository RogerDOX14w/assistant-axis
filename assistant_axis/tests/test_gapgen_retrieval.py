"""Retrieval recall and the paired statistics of M2 round 4 (gapgen/retrieval.py).

Every statistic is checked on synthetic data whose answer is known in closed
form (McNemar's exact p from the binomial, Holm's step-down by hand) or by
construction (a bootstrap of identical arrays, of a constant difference, of
clusters of copies)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from assistant_axis.gapgen import retrieval as R


# --------------------------------------------------------------------------- ranks, recall@k, union


def test_target_ranks_and_recall_at_k():
    S = np.array([[0.9, 0.1, 0.5, 0.2],      # target 0: first
                  [0.9, 0.1, 0.5, 0.2],      # target 2: second
                  [0.9, 0.1, 0.5, 0.2]])     # target 1: last
    ranks = R.target_ranks(S, np.array([0, 2, 1]))
    assert ranks.tolist() == [0, 1, 3]
    rec = R.recall_at_k(ranks, (1, 2, 4))
    assert rec == {1: pytest.approx(1 / 3), 2: pytest.approx(2 / 3), 4: pytest.approx(1.0)}
    assert R.hits(ranks, 2).tolist() == [True, True, False]


def test_topk_indices_are_sorted_nearest_first():
    S = np.array([[0.1, 0.7, 0.3, 0.9], [0.5, 0.4, 0.6, 0.0]])
    assert R.topk_indices(S, 3).tolist() == [[3, 1, 2], [2, 0, 1]]


def test_union_of_two_top_lists():
    top_a = np.array([[0, 1, 7], [2, 3, 8]])
    top_b = np.array([[1, 4, 9], [5, 6, 2]])
    hit, length = R.union_hits(top_a, top_b, np.array([4, 9]), k=2)
    assert hit.tolist() == [True, False]        # 4 is in B's top 2; 9 is in neither top 2
    assert length.tolist() == [3, 4]            # {0, 1, 4}; {2, 3, 5, 6}


def test_evaluate_view_finds_noisy_copies_first():
    rng = np.random.default_rng(0)
    E = rng.standard_normal((40, 16))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    targets = np.arange(40)
    Q = E + 0.01 * rng.standard_normal(E.shape)
    ev = R.evaluate_view(E, Q, targets, "centred", top=5)
    assert (ev["ranks"] == 0).all()
    assert ev["top"].shape == (40, 5) and (ev["top"][:, 0] == targets).all()
    assert (ev["own"] > ev["other_max"]).all()


# --------------------------------------------------------------------------- McNemar's exact test


def _pairs(a_only, b_only, both=0, neither=0):
    a = np.array([1] * a_only + [0] * b_only + [1] * both + [0] * neither, bool)
    b = np.array([0] * a_only + [1] * b_only + [1] * both + [0] * neither, bool)
    return a, b


def test_mcnemar_exact_matches_the_binomial():
    a, b = _pairs(10, 0, both=30, neither=20)
    m = R.mcnemar_exact(a, b)
    assert (m["a_only"], m["b_only"], m["n"]) == (10, 0, 60)
    assert m["p"] == pytest.approx(2 * 0.5 ** 10)           # 0.001953125
    assert m["diff"] == pytest.approx(10 / 60)
    a, b = _pairs(2, 8)
    assert R.mcnemar_exact(a, b)["p"] == pytest.approx(2 * (1 + 10 + 45) / 1024)   # 0.109375
    assert R.mcnemar_exact(b, a)["p"] == pytest.approx(2 * (1 + 10 + 45) / 1024)   # symmetric


def test_mcnemar_exact_balanced_and_empty_discordance():
    a, b = _pairs(5, 5, both=10)
    assert R.mcnemar_exact(a, b)["p"] == pytest.approx(1.0)
    a, b = _pairs(0, 0, both=7, neither=3)
    m = R.mcnemar_exact(a, b)
    assert m["p"] == 1.0 and m["a_only"] == m["b_only"] == 0


# --------------------------------------------------------------------------- paired bootstrap


def test_bootstrap_of_identical_arrays_is_zero():
    a = np.random.default_rng(1).random(200) > 0.5
    bs = R.paired_bootstrap(a, a.copy(), n_boot=500, seed=0)
    assert bs["diff"] == 0 and bs["lo"] == 0 and bs["hi"] == 0


def test_bootstrap_of_a_constant_difference_is_that_difference():
    a, b = np.ones(50, bool), np.zeros(50, bool)
    bs = R.paired_bootstrap(a, b, n_boot=300, seed=0)
    assert bs["diff"] == bs["lo"] == bs["hi"] == 1.0


def test_bootstrap_interval_covers_a_known_difference_and_is_reproducible():
    rng = np.random.default_rng(3)
    n = 4000
    b = rng.random(n) < 0.6
    flip = rng.random(n) < 0.1                    # a = b, plus 10% of b's misses turned into hits
    a = b | (flip & ~b)
    true = a.mean() - b.mean()
    bs = R.paired_bootstrap(a, b, n_boot=2000, seed=0)
    assert bs["lo"] < true < bs["hi"]
    # the paired standard error is sqrt(p_discordant / n) here (all discordance one way)
    se = math.sqrt(true * (1 - true) / n)
    assert (bs["hi"] - bs["lo"]) == pytest.approx(2 * 1.96 * se, rel=0.15)
    assert R.paired_bootstrap(a, b, n_boot=2000, seed=0) == bs


def test_cluster_bootstrap_widens_the_interval_for_copied_queries():
    rng = np.random.default_rng(4)
    a1 = rng.random(12) < 0.6
    b1 = rng.random(12) < 0.4
    a, b = np.repeat(a1, 25), np.repeat(b1, 25)    # 12 traits, 25 identical queries each
    clusters = np.repeat(np.arange(12), 25)
    q = R.paired_bootstrap(a, b, n_boot=2000, seed=0)
    c = R.paired_bootstrap(a, b, n_boot=2000, seed=0, clusters=clusters)
    assert q["diff"] == pytest.approx(c["diff"])
    assert (c["hi"] - c["lo"]) > 3 * (q["hi"] - q["lo"])
    # resampling whole clusters of copies equals resampling the 12 traits once each
    one = R.paired_bootstrap(a1, b1, n_boot=2000, seed=0)
    assert (c["lo"], c["hi"]) == pytest.approx((one["lo"], one["hi"]), abs=0.05)


# --------------------------------------------------------------------------- Holm


def test_holm_step_down_by_hand():
    assert R.holm([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    assert R.holm([0.5]) == pytest.approx([0.5])
    assert R.holm([0.4, 0.6]) == pytest.approx([0.8, 0.8])     # monotone, capped at 1 below
    assert R.holm([0.9, 0.9]) == pytest.approx([1.0, 1.0])


# --------------------------------------------------------------------------- the threshold design


def test_threshold_design_numbers():
    own = np.arange(1, 101) / 100.0                       # 0.01 .. 1.00
    other_max = np.full(100, 0.5)
    antonyms = np.array([0.02, 0.04, 0.06, 0.9])
    t = R.threshold_design(own, other_max, antonyms, recall=0.95)
    assert t["t_hi"] == pytest.approx(0.06)               # 95 of 100 own similarities at or above it
    assert t["recall_at_t_hi"] == pytest.approx(0.95)
    assert t["antonym_above_t_hi"] == pytest.approx(0.5)  # 0.06 and 0.9
    assert t["hidden_original_still_covered"] == pytest.approx(1.0)
