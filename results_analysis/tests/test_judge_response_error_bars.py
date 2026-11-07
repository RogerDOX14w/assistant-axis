"""scripts/judge_response_error_bars.py (2026-11-07): the pure pieces.  The vectorised blended means and Spearman
match the figure's path (judge_response_pareto.means + blend, judge_tier_robustness.cell_rho) on fake items; question
weights, a ninth, an instruction drop and rejudging noise act on the right items; the rejudge sd estimator recovers a
known noise.  No cells, no projections, no network."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def eb():
    return _load("judge_response_error_bars")


@pytest.fixture(scope="module")
def jrp():
    return _load("judge_response_pareto")


def fake_axis(rng, n_entities=24, n_p=3, n_q=12):
    """Two judges' items on one axis (every entity, instruction and question), entity names e0.., ranks, a projection."""
    names = [f"e{n}" for n in range(n_entities)]
    rank = {n: i for i, n in enumerate(names)}
    items = {j: {(n, p, q): float(rng.integers(0, 101)) for n in names for p in range(n_p) for q in range(n_q)} for j in ("ja", "jb")}
    proj = {n: float(rng.normal()) for n in names}
    return names, rank, items, proj


def arrays_of(eb, items_by_judge, ent_index, rank, share_of=None):
    q_index = {q: i for i, q in enumerate(sorted({q for it in items_by_judge.values() for (_, _, q) in it}))}
    members = []
    for j, it in items_by_judge.items():
        item_index = {k: i for i, k in enumerate(it)}
        sel = it if share_of is None else {k: v for k, v in it.items() if share_of(j, k)}
        members.append(dict(judge=j, model=f"model-{j}", **eb.member_arrays(sel, ent_index, q_index, rank, item_index)))
    return members, q_index


def test_blended_means_match_the_figure_path(eb, jrp):
    rng = np.random.default_rng(1)
    names, rank, items, proj = fake_axis(rng)
    ent_index = {n: i for i, n in enumerate(names)}
    # a golden-like split: judge a takes the even questions, judge b the odd ones
    members, _ = arrays_of(eb, items, ent_index, rank, share_of=lambda j, k: (k[2] % 2 == 0) == (j == "ja"))
    weights = {"model-ja": 0.4, "model-jb": 0.6}
    m = eb.blended_means(members, weights, len(names))
    parts = {"model-ja": jrp.means({k: v for k, v in items["ja"].items() if k[2] % 2 == 0}),
             "model-jb": jrp.means({k: v for k, v in items["jb"].items() if k[2] % 2 == 1})}
    jrp.BLEND_WEIGHTS = weights
    try:
        expected = jrp.blend(parts)
    finally:
        jrp.BLEND_WEIGHTS = None
    assert np.allclose(m, [expected[n] for n in names])
    # and the Spearman with a projection matches scipy's on the same pairs
    pv = {"v": np.array([proj[n] for n in names])}
    from scipy.stats import spearmanr
    assert eb.spearman_each(m, pv)[0] == pytest.approx(spearmanr(m, pv["v"])[0])


def test_cell_rho_agrees_on_lifted_names(eb, jrp):
    """The script's Spearman over an entity order equals judge_tier_robustness.cell_rho over the lifted dicts the
    figure uses, poles excluded in both."""
    rng = np.random.default_rng(2)
    names, rank, items, proj = fake_axis(rng, n_entities=16)
    ent_index = {n: i for i, n in enumerate(names)}
    members, _ = arrays_of(eb, {"ja": items["ja"]}, ent_index, rank)
    m = eb.blended_means(members, {"model-ja": 1.0}, len(names))
    poles = {"e0", "e1"}
    pv = {"v": np.array([np.nan if n in poles else proj[n] for n in names])}
    lifted_scores = {f"{n}|R": float(m[i]) for i, n in enumerate(names)}
    lifted_proj = {f"{n}|R": proj[n] for n in names}
    expected, n = jrp.rob.cell_rho(lifted_scores, lifted_proj, poles)
    assert n == len(names) - 2
    assert eb.spearman_each(m, pv)[0] == pytest.approx(expected, abs=1e-12)


def test_weights_ninth_drop_and_noise_act_on_the_right_items(eb, jrp):
    rng = np.random.default_rng(3)
    names, rank, items, _ = fake_axis(rng, n_entities=9, n_p=3, n_q=9)
    ent_index = {n: i for i, n in enumerate(names)}
    members, q_index = arrays_of(eb, {"ja": items["ja"]}, ent_index, rank)
    w = {"model-ja": 1.0}
    it = items["ja"]
    # question weights: doubling question 0 and dropping question 1 is the mean over that multiset
    wq = np.ones(len(q_index)); wq[q_index[0]] = 2.0; wq[q_index[1]] = 0.0
    m = eb.blended_means(members, w, len(names), wq=wq)
    for n in names:
        vals = [v for (nn, p, q), v in it.items() if nn == n and q != 1] + [v for (nn, p, q), v in it.items() if nn == n and q == 0]
        assert m[ent_index[n]] == pytest.approx(np.mean(vals))
    # one ninth: the items with (q + rank) % 9 == 4
    m9 = eb.blended_means(members, w, len(names), ninth_part=4)
    for n in names:
        vals = [v for (nn, p, q), v in it.items() if nn == n and (q + rank[n]) % 9 == 4]
        assert m9[ent_index[n]] == pytest.approx(np.mean(vals))
    # dropping instruction 2
    md = eb.blended_means(members, w, len(names), drop_p=(2,))
    for n in names:
        assert md[ent_index[n]] == pytest.approx(np.mean([v for (nn, p, q), v in it.items() if nn == n and p != 2]))
    # rejudging noise: a constant shift of every item moves every mean by it
    eps = {"ja": np.full(len(it), 3.5)}
    assert np.allclose(eb.blended_means(members, w, len(names), eps=eps), eb.blended_means(members, w, len(names)) + 3.5)
    # a member without items for an entity leaves it to the other judges (renormalised), nan when none has it
    half = {k: v for k, v in it.items() if k[0] != "e3"}
    members2, _ = arrays_of(eb, {"ja": it, "jb": half}, ent_index, rank)
    m2 = eb.blended_means(members2, {"model-ja": 0.25, "model-jb": 0.75}, len(names))
    assert m2[ent_index["e3"]] == pytest.approx(np.mean([v for (nn, _, _), v in it.items() if nn == "e3"]))
    members3, _ = arrays_of(eb, {"jb": half}, ent_index, rank)
    assert np.isnan(eb.blended_means(members3, {"model-jb": 1.0}, len(names))[ent_index["e3"]])


def test_rejudge_sigma_recovers_a_known_noise(eb):
    rng = np.random.default_rng(4)
    keys = [(f"e{n}", p, q) for n in range(50) for p in range(4) for q in range(50)]
    base = {k: float(rng.uniform(0, 100)) for k in keys}
    a = {k: v + rng.normal(0, 6.0) for k, v in base.items()}
    b = {k: v + rng.normal(0, 6.0) + 2.0 for k, v in base.items()}       # a shift of 2 between designs
    sigma, n, shift = eb.rejudge_sigma([(a, b)])
    assert n == len(keys)
    assert sigma == pytest.approx(6.0, rel=0.03)
    assert shift == pytest.approx(2.0, abs=0.2)
    assert eb.rejudge_sigma([({}, {})])[1] == 0
