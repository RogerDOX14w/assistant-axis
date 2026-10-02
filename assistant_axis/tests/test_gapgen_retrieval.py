"""Retrieval recall and the paired statistics of M2 round 4 (gapgen/retrieval.py).

Every statistic is checked on synthetic data whose answer is known in closed
form (McNemar's exact p from the binomial, Holm's step-down by hand) or by
construction (a bootstrap of identical arrays, of a constant difference, of
clusters of copies)."""
from __future__ import annotations

import json
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


# --------------------------------------------------------------------------- round 4: query sources


def test_query_text_is_the_text_alone_cut_to_14_words():
    long = ("This means keeping every promise one makes, showing up on time, and doing what one said one would "
            "do without being reminded.")
    q = R.query_text(long)
    assert not q.startswith("reliable") and ":" not in q.split()[0]
    assert len(q.split()) <= 14 and q.startswith("This means keeping every promise") and q.endswith(".")
    assert R.query_text("This means being kind.") == "This means being kind."
    with pytest.raises(ValueError):
        R.query_text("  ")


def test_plain_reading_same_keeps_only_the_corpus_sense(tmp_path):
    p = tmp_path / "results.jsonl"
    rows = [{"key": "open_minded", "label": "open-minded", "comparison": {"relation": "same"}},
            {"key": "absentee", "label": "absentee", "comparison": {"relation": "related"}},
            {"key": "gay", "label": "gay", "comparison": {"relation": "different"}},
            {"key": "broken", "label": "broken", "comparison": None}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n\n")
    assert R.plain_reading_same(p) == {"open_minded"}


def test_m1_gloss_queries_filters_stratum_gloss_corpus_and_keep(tmp_path):
    p = tmp_path / "results.jsonl"
    rows = [{"label": "open-minded", "gloss": "This means open.", "meta": {"stratum": "existing"}},
            {"label": "open-minded", "gloss": "This means a second row.", "meta": {"stratum": "existing"}},
            {"label": "absentee", "gloss": "", "meta": {"stratum": "existing"}},          # no gloss
            {"label": "honest", "gloss": "This means honest.", "meta": {"stratum": "existing"}},   # not kept
            {"label": "zorbic", "gloss": "This means zorbic.", "meta": {"stratum": "existing"}},   # not in corpus
            {"label": "aloof", "gloss": "This means aloof.", "meta": {"stratum": "not_adopted"}}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    q, counts = R.m1_gloss_queries(p, corpus={"open_minded", "absentee", "honest", "aloof"},
                                   keep={"open_minded", "absentee", "aloof"})
    assert q == {"open_minded": "This means open."}
    # "renamed" and "not_in_corpus" since 2026-10-02 (the merge with the main line)
    assert counts == {"existing": 5, "with_gloss": 4, "in_corpus": 3, "renamed": 0, "not_in_corpus": 1, "kept": 1}
    q_all, _ = R.m1_gloss_queries(p, corpus={"open_minded", "honest"})
    assert set(q_all) == {"open_minded", "honest"}


def test_renamed_labels_count_for_the_renamed_trait(tmp_path):
    """2026-10-02: a gloss or plain-reading judgement filed under a label the corpus has since renamed counts
    for the renamed trait; a label with no current trait (and no rename followed) is dropped and counted."""
    p = tmp_path / "results.jsonl"
    rows = [{"label": "tough", "gloss": "This means tough.", "meta": {"stratum": "existing"}},
            {"label": "bland", "gloss": "This means bland.", "meta": {"stratum": "existing"}},   # rename not followed
            {"label": "calm", "gloss": "This means calm.", "meta": {"stratum": "existing"}}]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    q, counts = R.m1_gloss_queries(p, corpus={"strict", "dull", "calm"}, renames={"tough": "strict"})
    assert q == {"strict": "This means tough.", "calm": "This means calm."}
    assert counts["renamed"] == 1 and counts["not_in_corpus"] == 1 and counts["kept"] == 2
    pr = tmp_path / "plain.jsonl"
    pr.write_text(json.dumps({"key": "tough", "label": "tough", "comparison": {"relation": "same"}}) + "\n")
    assert R.plain_reading_same(pr, renames={"tough": "strict"}) == {"strict"}
    assert R.plain_reading_same(pr) == {"tough"}


# --------------------------------------------------------------------------- round 4: evaluation


def _round4_fixture(n=30, d=24, seed=0):
    """Two models, one representation each of two; source "easy" queries are near-copies of their own
    trait (always first), source "hard" queries for traits 0-4 are copies of the NEXT trait (rank >= 1)."""
    rng = np.random.default_rng(seed)
    corpus, queries = {}, {}
    stems = [f"t{i}" for i in range(n)]
    q_targets = list(range(n)) + list(range(5))
    q_sources = ["easy"] * n + ["hard"] * 5
    for model in ("m_a", "m_b"):
        E = rng.standard_normal((n, d))
        E /= np.linalg.norm(E, axis=1, keepdims=True)
        corpus[model] = {"w14": E, "w20": E + 0.001 * rng.standard_normal(E.shape)}
        Q = np.vstack([E + 0.01 * rng.standard_normal(E.shape), E[1:6] + 0.01 * rng.standard_normal((5, d))])
        queries[model] = Q
    return corpus, queries, stems, q_targets, q_sources


def test_evaluate_and_summarise_round4_on_known_answers():
    corpus, queries, stems, targets, sources = _round4_fixture()
    cells = R.evaluate_round4(corpus, queries, targets, variants=("centred", "pw4"), top=10,
                              antonym_pairs=[(0, 1), (2, 3)])
    assert set(cells) == {(m, r, v) for m in ("m_a", "m_b") for r in ("w14", "w20") for v in ("centred", "pw4")}
    assert all(len(c["antonym_sims"]) == 2 and "Z" not in c for c in cells.values())
    q_stems = [stems[t] for t in targets]
    out = R.summarise_round4(cells, models=("m_a", "m_b"), sources=sources, stems=q_stems, targets=targets,
                             corpus_stems=stems, n_boot=200, seed=0, miss_k=1)
    assert out["n_queries"] == {"pooled": 35, "easy": 30, "hard": 5} and out["n_traits_queried"] == 30
    rec = {(r["model"], r["representation"], r["variant"], r["source"]): r["recall"] for r in out["recall"]}
    assert rec[("m_a", "w14", "centred", "easy")]["1"] == 1.0
    assert rec[("m_a", "w14", "centred", "hard")]["1"] == 0.0           # the next trait comes first
    assert rec[("m_a", "w14", "centred", "pooled")]["1"] == pytest.approx(30 / 35, abs=1e-4)
    # comparisons: pw4 (same representation) and w20 (same variant) against centred w14, k = 1 and 5
    settings = {(c["model"], c["k"], c["setting"]) for c in out["comparisons"]}
    assert settings == {(m, k, s) for m in ("m_a", "m_b") for k in (1, 5) for s in ("w14|pw4", "w20|centred")}
    for c in out["comparisons"]:
        assert c["baseline"] == "w14|centred" and 0 <= c["p"] <= c["p_holm"] <= 1 and c["real"] is False
        assert c["boot_lo"] <= c["diff"] <= c["boot_hi"]
    assert {c["source"] for c in out["comparisons_by_source"]} == {"easy", "hard"}
    # union of the two models' top 3: every easy query found; lists hold 3 to 6 distinct traits
    u = {(x["representation"], x["variant"], x["k"], x["source"]): x for x in out["union"]}
    assert u[("w14", "centred", 3, "easy")]["recall"] == 1.0
    assert 3 <= u[("w14", "centred", 3, "pooled")]["mean_length"] <= 6
    assert {x["k"] for x in out["union"]} == {3, 5, 10}
    assert {x["against"] for x in out["union_vs_single"]} == {"m_a top 10", "m_b top 10", "m_a top 20", "m_b top 20"}
    # the second family: inside w20, pw4 against centred w20
    assert {(c["model"], c["k"], c["setting"], c["baseline"]) for c in out["comparisons_within"]} == {
        (m, k, "w20|pw4", "w20|centred") for m in ("m_a", "m_b") for k in (1, 5)}
    assert all("p_holm" in c for c in out["comparisons_within"])
    # the five hard queries are the misses at k = 1, first retrieved trait = the next one
    miss = out["misses"]["by_cell"]["m_a|w14|centred"]
    assert sorted(m[1] for m in miss) == ["t0", "t1", "t2", "t3", "t4"]
    assert all(m[0] == "hard" and m[3] == f"t{int(m[1][1:]) + 1}" for m in miss)
    td = {(r["model"], r["representation"], r["variant"]): r for r in out["threshold_design"]}
    assert td[("m_a", "w14", "centred")]["n_antonym_pairs"] == 2
    md = R.round4_markdown(out)
    for head in ("## Pooled recall@k", "## Paired comparisons against centred w14, pooled", "## Both models' lists merged",
                 "## Recall@1 / recall@5 per source", "## The old threshold design", "## Inside the other representation"):
        assert head in md
    assert "| m_a | w14 | centred |" in md and "w14 pw4" in md


def test_a_real_difference_is_marked_real():
    # 300 traits, one query each: setting A finds 60 that the baseline misses and loses none
    rng = np.random.default_rng(5)
    n = 300
    base_ranks = np.where(rng.random(n) < 0.7, 0, 7)
    better = base_ranks.copy()
    better[np.where(base_ranks == 7)[0][:60]] = 0
    cells = {("m", "w14", "centred"): {"ranks": base_ranks, "top": np.zeros((n, 10), int), "own": np.ones(n),
                                       "other_max": np.zeros(n), "antonym_sims": np.zeros(0)},
             ("m", "w14", "pw8"): {"ranks": better, "top": np.zeros((n, 10), int), "own": np.ones(n),
                                   "other_max": np.zeros(n), "antonym_sims": np.zeros(0)}}
    out = R.summarise_round4(cells, models=("m",), sources=["s"] * n, stems=[f"t{i}" for i in range(n)],
                             targets=np.zeros(n, int), corpus_stems=["t0"], comparison_ks=(1,), n_boot=500)
    (c,) = out["comparisons"]
    assert (c["setting_only"], c["baseline_only"]) == (60, 0) and c["real"] is True
    assert c["p"] == pytest.approx(2 * 0.5 ** 60) and c["boot_lo"] > 0
    assert out["union"] == [] and out["threshold_design"][0]["antonym_above_t_hi"] is None
