"""IPIP generator, clustering: synthetic embeddings with planted clusters (no model, no API)."""
import numpy as np
import pytest

from assistant_axis.gapgen.embed import EmbeddingCache, HashEmbedder
from assistant_axis.gapgen.generators.ipip import cluster as C
from assistant_axis.gapgen.generators.ipip.ingest import ItemRow
from assistant_axis.judge_pricing import MultiModelUsage


def planted(n_clusters=12, size=8, dim=48, noise=0.08, seed=0, n_outliers=0):
    """Unit vectors around ``n_clusters`` random centres; returns (E, labels)."""
    rng = np.random.default_rng(seed)
    centres = rng.standard_normal((n_clusters, dim))
    rows, labels = [], []
    for c in range(n_clusters):
        for _ in range(size):
            rows.append(centres[c] + noise * np.linalg.norm(centres[c]) * rng.standard_normal(dim) / np.sqrt(dim))
            labels.append(c)
    for i in range(n_outliers):
        rows.append(rng.standard_normal(dim) * 3)
        labels.append(-1 - i)
    E = np.asarray(rows)
    return E / np.linalg.norm(E, axis=1, keepdims=True), np.asarray(labels)


def item(code, text="x", scales=()):
    return ItemRow(schema_version=1, ipip_id=code, codes=[code], text=text,
                   scales=[{"inventory": i, "construct": c, "key": k} for i, c, k in scales])


def test_item_embed_text():
    assert C.item_embed_text("Get chores done right away.") == "I get chores done right away."
    assert C.item_embed_text("Am always prepared.") == "I am always prepared."
    assert C.item_embed_text("Don't like to draw attention to myself.") == "I don't like to draw attention to myself."
    assert C.item_embed_text("I'm the life of the party.") == "I'm the life of the party."


class TestTargetCount:
    @pytest.mark.parametrize("target", [6, 10, 12])
    def test_hits_the_target_within_tolerance(self, target):
        E, _ = planted(n_clusters=12, size=8)
        clusters, info = C.agglo_clusters(E, target_n=target)
        n = sum(1 for c in clusters if len(c.members) >= 2)
        assert abs(n - target) <= max(1, round(0.1 * target)), (n, target, info)
        assert info["n_clusters"] == n and info["target"] == target

    def test_planted_clusters_recovered_exactly(self):
        E, labels = planted(n_clusters=12, size=8)
        clusters, _ = C.agglo_clusters(E, target_n=12)
        found = sorted(sorted(c.members) for c in clusters)
        truth = sorted(sorted(np.flatnonzero(labels == k).tolist()) for k in range(12))
        assert found == truth

    def test_deterministic_and_ordered_by_size(self):
        E, _ = planted(n_clusters=10, size=6, n_outliers=3)
        a, _ = C.agglo_clusters(E, target_n=10)
        b, _ = C.agglo_clusters(E.copy(), target_n=10)
        assert [c.members for c in a] == [c.members for c in b]
        sizes = [len(c.members) for c in a]
        assert sizes == sorted(sizes, reverse=True)

    def test_singletons_are_not_clusters(self):
        E, _ = planted(n_clusters=5, size=6, n_outliers=4)
        clusters, info = C.agglo_clusters(E, target_n=5)
        assert all(len(c.members) >= 2 for c in clusters)
        assert info["n_singletons"] == len(E) - sum(len(c.members) for c in clusters)


class TestConsensus:
    def test_shared_cluster_kept_one_arm_cluster_loose(self):
        a = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10]]
        b = [[0, 1, 2, 3], [4, 5, 20, 21, 22, 23], [8, 9, 10, 11]]
        kept, loose = C.consensus(a, b, min_jaccard=0.5)
        assert [(k.members, k.jaccard) for k in kept] == [([0, 1, 2, 3], 1.0), ([8, 9, 10], 0.75)]
        assert [(lo.members, lo.jaccard) for lo in loose] == [([4, 5, 6, 7], pytest.approx(2 / 8))]

    def test_one_to_one_matching(self):
        a = [[0, 1, 2, 3], [0, 1, 2]]
        b = [[0, 1, 2, 3]]
        kept, loose = C.consensus(a, b)
        assert [k.members for k in kept] == [[0, 1, 2, 3]] and [lo.members for lo in loose] == [[0, 1, 2]]


class TestPoles:
    def items(self):
        return {
            "a1": item("a1", scales=[("NEO", "Orderliness", "+")]),
            "a2": item("a2", scales=[("NEO", "Orderliness", "+"), ("HEX", "Diligence", "+")]),
            "a3": item("a3", scales=[("HEX", "Diligence", "+")]),
            "b1": item("b1", scales=[("NEO", "Orderliness", "-")]),
            "b2": item("b2", scales=[("NEO", "Orderliness", "-")]),
            "c1": item("c1", scales=[("NEO", "Anxiety", "+")]),
        }

    def test_unipolar_cluster_is_one_pole(self):
        poles = C.split_poles(["a1", "a2", "a3"], self.items())
        assert len(poles) == 1 and poles[0].pole == "a" and poles[0].items == ["a1", "a2", "a3"]

    def test_split_exactly_at_the_minus_items_of_a_plus_sharing_scale(self):
        poles = C.split_poles(["a1", "a2", "a3", "b1", "b2"], self.items())
        assert [(p.pole, p.items) for p in poles] == [("a", ["a1", "a2", "a3"]), ("b", ["b1", "b2"])]
        assert poles[0].bipolar_scales == ["NEO:Orderliness"]

    def test_all_minus_cluster_stays_one_pole(self):
        poles = C.split_poles(["b1", "b2"], self.items())
        assert len(poles) == 1 and poles[0].items == ["b1", "b2"]

    def test_unconstrained_item_goes_to_the_nearer_pole(self):
        its = self.items()
        vec = {"a1": [1, 0], "a2": [1, 0.1], "a3": [1, -0.1], "b1": [0, 1], "b2": [0.1, 1], "c1": [0.05, 1]}
        poles = C.split_poles(["a1", "a2", "a3", "b1", "b2", "c1"], its,
                              vectors={k: np.asarray(v, float) for k, v in vec.items()})
        assert [p.items for p in poles] == [["a1", "a2", "a3"], ["b1", "b2", "c1"]]
        poles = C.split_poles(["a1", "a2", "a3", "b1", "b2", "c1"], its)        # no vectors: the larger pole
        assert [p.items for p in poles] == [["a1", "a2", "a3", "c1"], ["b1", "b2"]]


def test_purity_metrics_are_one_on_planted_labels():
    items = {f"i{k}": item(f"i{k}", scales=[("NEO", f"C{k // 4}", "+")]) for k in range(16)}
    clusters = [[f"i{k}" for k in range(4 * j, 4 * j + 4)] for j in range(4)]
    m = C.purity_metrics(clusters, items)
    assert m["nmi"] == pytest.approx(1.0) and m["ari"] == pytest.approx(1.0)
    assert m["purity_mean"] == pytest.approx(1.0) and m["n_items_scored"] == 16
    assert m["by_inventory"]["NEO"]["nmi"] == pytest.approx(1.0)
    mixed = [clusters[0][:2] + clusters[1][:2], clusters[0][2:] + clusters[1][2:]]
    assert C.purity_metrics(mixed, items)["purity_mean"] == pytest.approx(0.5)
    assert C.cluster_purity(["i0", "i1", "i4"], items) == (pytest.approx(2 / 3), {"NEO:C0": 2, "NEO:C1": 1})


class TestCorpusIndependence:
    def test_membership_does_not_change_with_the_corpus(self, tmp_path):
        E, _ = planted(n_clusters=6, size=5, seed=3, dim=32)        # the hash embedder's dimension
        ids = [f"q{i}" for i in range(len(E))]
        clusters, _ = C.agglo_clusters(E, target_n=6)
        groups = [[ids[i] for i in c.members] for c in clusters]
        vecs = {i: E[k] for k, i in enumerate(ids)}
        emb = HashEmbedder(dim=32)
        cache = EmbeddingCache(root=tmp_path / "cache")
        one = C.nearest_corpus(groups, vecs, corpus={"tidy": "tidy: keeps things in order"}, embedder=emb,
                               cache=cache, usage=MultiModelUsage())
        two = C.nearest_corpus(groups, vecs, corpus={"calm": "calm: rarely worried", "bold": "bold: takes risks"},
                               embedder=emb, cache=cache, usage=MultiModelUsage())
        assert set(one) == set(two) == set(range(len(groups)))
        assert {v["stem"] for v in one.values()} == {"tidy"}
        clusters2, _ = C.agglo_clusters(E, target_n=6)                  # nothing the corpus does reaches membership
        assert [c.members for c in clusters2] == [c.members for c in clusters]


def test_hdbscan_check_reports(tmp_path):
    E, labels = planted(n_clusters=6, size=12, seed=1)
    rep = C.hdbscan_check(E, seed=0, use_umap=False, min_cluster_size=4, reference=labels)
    assert rep["n_clusters"] >= 4 and 0 <= rep["noise_share"] <= 1 and rep["ari_vs_reference"] > 0.5


def test_embed_items_uses_the_cache_and_charges_usage(tmp_path):
    items = [item("H1", "Get chores done right away."), item("H2", "Leave a mess in my room.")]
    usage = MultiModelUsage()
    cache = EmbeddingCache(root=tmp_path / "c")
    E = C.embed_items(items, embedder=HashEmbedder(dim=16), cache=cache, usage=usage)
    assert E.shape == (2, 16) and usage.n_calls == 1
    E2 = C.embed_items(items, embedder=HashEmbedder(dim=16), cache=cache, usage=usage)
    assert np.allclose(E, E2) and usage.n_calls == 1                  # the second time from the cache


class TestNearestOtherPole:
    """QUESTIONS 50, signal 1: the cluster table carries each pole's nearest pole of **another** cluster, so the
    granularity command needs no vectors."""

    def test_the_other_pole_of_the_same_cluster_is_not_an_other_cluster(self):
        v = {"H1": np.array([1.0, 0.0, 0.0]), "H2": np.array([0.99, 0.1, 0.0]),   # cluster 1, poles a and b
             "H3": np.array([0.0, 1.0, 0.0]), "H4": np.array([0.0, 0.0, 1.0])}
        poles = [((1, "a"), ["H1"]), ((1, "b"), ["H2"]), ((2, "a"), ["H3"]), ((3, "a"), ["H4"])]
        out = C.nearest_other_poles(poles, v)
        assert out[(1, "a")]["cluster_id"] in (2, 3) and out[(1, "a")]["pole"] == "a"
        assert out[(1, "b")]["cluster_id"] in (2, 3)
        assert out[(2, "a")]["cluster_id"] in (1, 3)
        assert all(0 <= r["cos"] <= 1 for r in out.values())

    def test_a_lone_pole_has_no_nearest_other(self):
        assert C.nearest_other_poles([((1, "a"), ["H1"])], {"H1": np.array([1.0, 0.0])}) == {}
        assert C.nearest_other_poles([], {}) == {}

    def test_written_on_every_pole_row_of_the_table(self):
        E, _ = planted(n_clusters=6, size=5, dim=16)
        items = [item(f"H{i}", f"Item {i}.") for i in range(len(E))]
        rows, _summary = C.build_cluster_table(items, {"openai": E, "gemma": E}, target=6, hdbscan=False,
                                               corpus=None)
        assert len(rows) >= 2
        for r in rows:
            for p in r["poles"]:
                nn = p["nearest_other"]
                assert nn["cluster_id"] != r["cluster_id"]
                assert -1.0 <= nn["cos"] <= 1.0
        # it is a size signal, kept apart from nearest_corpus (novelty), which is absent without a corpus
        assert all(r["nearest_corpus"] is None for r in rows)
