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
    """The old rule (``rule="jaccard"``; R2 is the default since 2026-10-12)."""

    def test_shared_cluster_kept_one_arm_cluster_loose(self):
        a = [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10]]
        b = [[0, 1, 2, 3], [4, 5, 20, 21, 22, 23], [8, 9, 10, 11]]
        kept, loose = C.consensus(a, b, rule="jaccard", min_jaccard=0.5)
        assert [(k.members, k.jaccard) for k in kept] == [([0, 1, 2, 3], 1.0), ([8, 9, 10], 0.75)]
        assert [(lo.members, lo.jaccard) for lo in loose] == [([4, 5, 6, 7], pytest.approx(2 / 8))]

    def test_one_to_one_matching(self):
        a = [[0, 1, 2, 3], [0, 1, 2]]
        b = [[0, 1, 2, 3]]
        kept, loose = C.consensus(a, b, rule="jaccard")
        assert [k.members for k in kept] == [[0, 1, 2, 3]] and [lo.members for lo in loose] == [[0, 1, 2]]


def _old_consensus(a, b, *, min_jaccard=0.5):
    """``consensus`` as it was before 2026-10-12 (commit f94fde15), verbatim: the reference the ``jaccard`` rule
    must reproduce."""
    from collections import defaultdict
    sa = [set(x) for x in a]
    sb = [set(x) for x in b]
    where = defaultdict(set)
    for j, s in enumerate(sb):
        for x in s:
            where[x].add(j)
    pairs, best = [], [0.0] * len(sa)
    for i, s in enumerate(sa):
        for j in sorted(set().union(*(where[x] for x in s)) if s else ()):
            jac = len(s & sb[j]) / len(s | sb[j])
            pairs.append((-jac, i, j))
            best[i] = max(best[i], jac)
    pairs.sort()
    used_a, used_b, match = set(), set(), {}
    for neg, i, j in pairs:
        if i in used_a or j in used_b:
            continue
        used_a.add(i)
        used_b.add(j)
        match[i] = (j, -neg)
    kept, loose = [], []
    for i, members in enumerate(a):
        j, jac = match.get(i, (None, 0.0))
        if j is not None and jac >= min_jaccard:
            kept.append((list(members), round(jac, 6), j))
        else:
            loose.append((list(members), round(best[i], 6), j))
    return kept, loose


def _random_partition(rng, n_items, n_groups, max_size):
    pool = list(rng.permutation(n_items))
    out = []
    for _ in range(n_groups):
        k = int(rng.integers(2, max_size + 1))
        if len(pool) < k:
            break
        out.append(sorted(int(x) for x in pool[:k]))
        pool = pool[k:]
    return out


class TestConsensusR2:
    """Gate audit 4's rule R2 (Roger 2026-10-12): every cluster of 3+ items is kept; a pair is kept only when the
    second arm puts both its items in one cluster; the Jaccard column is the old rule's, whatever the rule."""

    def test_a_3plus_cluster_is_kept_whatever_the_second_arm_does(self):
        a = [[0, 1, 2], [3, 4, 5, 6]]
        for b in ([], [[0, 10], [1, 11], [2, 12]], [[3, 4, 5, 6, 20, 21, 22, 23, 24]]):
            kept, loose = C.consensus(a, b, rule="r2")
            assert [k.members for k in kept] == a and loose == []
            assert {k.reason for k in kept} == {"size>=3"}

    def test_a_pair_is_kept_only_when_the_second_arm_coclusters_it(self):
        a = [[0, 1], [2, 3], [4, 5]]
        b = [[0, 1, 7, 8, 9],         # the pair nested in a 5-item cluster: J 0.4, held by the old rule
             [2, 10], [3, 11]]        # the second pair split
        kept, loose = C.consensus(a, b, rule="r2")
        assert [(k.members, k.reason, k.core, k.core_partner) for k in kept] == [([0, 1], "pair_coclustered", 2, 0)]
        assert [(lo.members, lo.reason, lo.core) for lo in loose] == [([2, 3], "pair_not_coclustered", 1),
                                                                      ([4, 5], "pair_not_coclustered", 0)]
        assert kept[0].jaccard == pytest.approx(0.4)
        j_kept, j_loose = C.consensus(a, b, rule="jaccard")
        assert j_kept == [] and len(j_loose) == 3                       # the old rule held all three

    def test_the_jaccard_column_does_not_depend_on_the_rule(self):
        rng = np.random.default_rng(5)
        for _ in range(50):
            a = _random_partition(rng, 60, 15, 6)
            b = _random_partition(rng, 60, 15, 6)
            r2 = {tuple(m.members): (m.jaccard, m.partner, m.core) for m in sum(C.consensus(a, b, rule="r2"), [])}
            jc = {tuple(m.members): (m.jaccard, m.partner, m.core) for m in sum(C.consensus(a, b, rule="jaccard"), [])}
            assert r2 == jc

    def test_the_jaccard_rule_reproduces_the_old_function_exactly(self):
        rng = np.random.default_rng(11)
        for trial in range(200):
            a = _random_partition(rng, 50, 14, 7)
            b = _random_partition(rng, 50, 14, 7)
            if trial % 5 == 0:
                b = b + [list(x) for x in a[:3]]                   # some exact reproductions, some nesting
            new_k, new_l = C.consensus(a, b, rule="jaccard")
            old_k, old_l = _old_consensus(a, b)
            assert [(m.members, m.jaccard, m.partner) for m in new_k] == old_k
            assert [(m.members, m.jaccard, m.partner) for m in new_l] == old_l

    def test_unknown_rule_refused(self):
        with pytest.raises(ValueError):
            C.consensus([[0, 1, 2]], [], rule="r1")


# --------------------------------------------------------------------------- the table: planted arms

def planted_groups(groups, *, dim=48, noise=0.05, seed=0, centres=None):
    """Unit vectors, one per item ``0..n-1``: each item near the centre of the group it is listed in."""
    rng = np.random.default_rng(seed)
    n = sum(len(g) for g in groups)
    C_ = centres if centres is not None else rng.standard_normal((len(groups), dim))
    C_ = C_ / np.linalg.norm(C_, axis=1, keepdims=True)
    E = np.zeros((n, dim))
    for k, g in enumerate(groups):
        for i in g:
            v = C_[k] + noise * rng.standard_normal(dim) / np.sqrt(dim)
            E[i] = v / np.linalg.norm(v)
    return E


#: the primary arm's six planted clusters (22 items) and a second arm that carves them differently
PRIMARY = {"A": [0, 1, 2, 3, 4], "B": [5, 6, 7, 8], "C": [9, 10, 11], "P1": [12, 13], "P2": [14, 15],
           "D": [16, 17, 18, 19, 20, 21]}
SECOND = [[5, 6, 7, 8, 14],          # B, with one item of P2
          [9, 10, 11, 15],           # C, with the other item of P2: P2 is split
          [12, 13, 16, 17, 18],      # P1 nested in a 5-item cluster with half of D (J 0.4)
          [19, 20, 21, 4],           # the rest of D, with one item of A
          [0, 1], [2, 3]]            # A cut into pieces (best J 0.4)


def planted_table(rule, **kw):
    E1 = planted_groups(list(PRIMARY.values()), seed=1)
    E2 = planted_groups(SECOND, seed=2)
    items = [item(f"H{i}", f"Item {i}.") for i in range(len(E1))]
    rows, summary = C.build_cluster_table(items, {"openai": E1, "gemma": E2}, target=6, hdbscan=False, corpus=None,
                                          rule=rule, **kw)
    name = {tuple(f"H{i}" for i in v): k for k, v in PRIMARY.items()}
    return {name[tuple(sorted(r["items"], key=lambda x: int(x[1:])))]: r for r in rows}, summary, rows


class TestTableR2:
    def test_the_planted_clusters_are_the_rows(self):
        by, _s, rows = planted_table("r2")
        assert set(by) == set(PRIMARY) and len(rows) == 6

    def test_r2_keeps_3plus_whatever_the_second_arm_does_and_the_coclustered_pair_only(self):
        by, summary, _rows = planted_table("r2")
        assert {k: r["consensus"] for k, r in by.items()} == {
            "A": "kept", "B": "kept", "C": "kept", "D": "kept", "P1": "kept", "P2": "loose"}
        assert {k: r["consensus_reason"] for k, r in by.items()} == {
            "A": "size>=3", "B": "size>=3", "C": "size>=3", "D": "size>=3", "P1": "pair_coclustered",
            "P2": "pair_not_coclustered"}
        assert by["P1"]["core_vs_gemma"] == {"n": 2, "cluster": by["P1"]["core_vs_gemma"]["cluster"], "size": 5}
        assert by["P2"]["core_vs_gemma"]["n"] == 1
        assert by["A"]["jaccard_vs_gemma"] == pytest.approx(0.4)     # held by the old rule, kept by R2
        assert by["P1"]["jaccard_vs_gemma"] == pytest.approx(0.4)
        c = summary["consensus"]
        assert (c["rule"], c["n_kept"], c["n_loose"], c["loose_items"]) == ("r2", 5, 1, 2)
        assert c["reasons"] == {"pair_coclustered": 1, "pair_not_coclustered": 1, "size>=3": 4}
        assert all(r["schema_version"] == C.TABLE_SCHEMA_VERSION for r in by.values())

    def test_the_jaccard_rule_reproduces_the_old_table(self):
        by, summary, rows = planted_table("jaccard")
        assert {k for k, r in by.items() if r["consensus"] == "kept"} == {"B", "C"}
        # every row's status and Jaccard as the old function gives them on the same two cuts
        E1 = planted_groups(list(PRIMARY.values()), seed=1)
        E2 = planted_groups(SECOND, seed=2)
        cut = {arm: [[f"H{i}" for i in c.members] for c in C.agglo_clusters(E, target_n=6)[0]]
               for arm, E in (("openai", E1), ("gemma", E2))}
        old_k, old_l = _old_consensus(cut["openai"], cut["gemma"])
        old = {tuple(m): ("kept", j) for m, j, _p in old_k} | {tuple(m): ("loose", j) for m, j, _p in old_l}
        assert {tuple(r["items"]): (r["consensus"], r["jaccard_vs_gemma"]) for r in rows} == old
        assert [r["cluster_id"] for r in rows] == list(range(1, 7))
        assert summary["consensus"]["rule"] == "jaccard" and summary["ceiling"]["n_recut"] == 0
        assert {r["consensus_reason"] for r in rows} == {"jaccard>=0.5", "jaccard<0.5"}

    def test_the_jaccard_column_is_the_same_under_both_rules(self):
        r2, _s, _r = planted_table("r2")
        jc, _s, _r = planted_table("jaccard")
        assert {k: r["jaccard_vs_gemma"] for k, r in r2.items()} == {k: r["jaccard_vs_gemma"] for k, r in jc.items()}

    def test_nearest_other_is_chosen_among_the_kept_poles(self):
        """Review 5 D3: signal 1 dropped a kept pole whose nearest pole was loose (never named)."""
        from assistant_axis.gapgen.generators.ipip import granularity as G
        by, summary, rows = planted_table("r2")
        loose_ids = {r["cluster_id"] for r in rows if r["consensus"] == "loose"}
        assert loose_ids == {by["P2"]["cluster_id"]}
        for r in rows:
            for p in r["poles"]:
                assert p["nearest_other"]["cluster_id"] not in loose_ids
                assert p["nearest_other"]["among"] == "kept" and p["nearest_other"]["cluster_id"] != r["cluster_id"]
        assert summary["nearest_other_among"] == "kept"
        for r in rows:                                     # every kept pole named: nothing is dropped
            for p in r["poles"]:
                p["blind"] = {"label": f"word{r['cluster_id']}", "gloss": "This means x."}
        _calls, _corpus, counts = G.nearest_pair_calls(rows)
        assert counts["n_nearest_unnamed"] == 0 and counts["n_nearest_in_other_consensus"] == 0
        assert counts["nearest_among"] == ["kept"]


# --------------------------------------------------------------------------- the size ceiling (gate audit 4, P2)

def blob_vectors(seed=3, dim=48):
    """A blob of three 4-item sub-clusters (items 0-11) and three separate 3-item clusters (12-20).  At 4 clusters
    the blob is one cluster of 12; at 6 it is its three sub-clusters."""
    rng = np.random.default_rng(seed)
    centre = rng.standard_normal(dim)
    centre /= np.linalg.norm(centre)
    subs = []
    for _ in range(3):
        r = rng.standard_normal(dim)
        v = centre + 0.6 * r / np.linalg.norm(r)
        subs.append(v / np.linalg.norm(v))
    others = rng.standard_normal((3, dim))
    groups = [list(range(4 * k, 4 * k + 4)) for k in range(3)] + [list(range(12 + 3 * k, 15 + 3 * k)) for k in range(3)]
    return planted_groups(groups, centres=np.vstack([np.asarray(subs), others]), seed=seed, dim=dim), groups


class TestSizeCeiling:
    def table(self, target, **kw):
        E, groups = blob_vectors()
        items = [item(f"H{i}", f"Item {i}.") for i in range(len(E))]
        return C.build_cluster_table(items, {"openai": E, "gemma": E}, target=target, hdbscan=False, corpus=None,
                                     **kw)

    def test_without_a_ceiling_the_blob_is_one_row(self):
        rows, s = self.table(4)
        assert sorted(len(r["items"]) for r in rows) == [3, 3, 3, 12]
        assert [r["cluster_id"] for r in rows] == [1, 2, 3, 4] and not any(r.get("recut_from") for r in rows)
        assert s["ceiling"]["n_recut"] == 0 and s["ceiling"]["size_ceiling"] is None

    def test_a_cluster_over_the_ceiling_at_a_coarse_cut_is_replaced_by_its_finer_clusters(self):
        rows, s = self.table(4, size_ceiling=10, recut_targets=[6])
        assert sorted(len(r["items"]) for r in rows) == [3, 3, 3, 4, 4, 4]
        pieces = [r for r in rows if r.get("recut_from")]
        assert len(pieces) == 3 and all(len(r["items"]) == 4 for r in pieces)
        assert {r["recut_from"]["cluster_id"] for r in pieces} == {1}
        assert all(r["recut_from"]["size"] == 12 and r["recut_from"]["cut"] == 6 for r in pieces)
        # the clusters left whole keep their ids; the pieces are numbered after the coarse cut: offset + their id at ~6
        assert [r["cluster_id"] for r in rows] == [2, 3, 4, 5, 6, 7]
        assert all(r["cluster_id"] == 4 + r["recut_from"]["cut_cluster_id"] for r in pieces)
        assert all(r["granularity"] == 4 for r in rows)
        c = s["ceiling"]
        assert (c["n_recut"], c["recut_items"], c["n_pieces"], c["items_left_single"]) == (1, 12, 3, 0)
        assert c["blobs"] == [{"cluster_id": 1, "size": 12, "n_pieces": 3, "n_pieces_kept": 3, "piece_items": 12}]
        assert s["consensus"]["before_ceiling"]["n_kept"] == 4 and s["consensus"]["n_kept"] == 6
        assert s["n_rows"] == 6

    def test_a_piece_keeps_its_own_cuts_consensus(self):
        rows, _s = self.table(4, size_ceiling=10, recut_targets=[6])
        fine, _s6 = self.table(6)
        at6 = {tuple(r["items"]): (r["consensus"], r["consensus_reason"], r["jaccard_vs_gemma"]) for r in fine}
        for r in rows:
            if r.get("recut_from"):
                assert (r["consensus"], r["consensus_reason"], r["jaccard_vs_gemma"]) == at6[tuple(r["items"])]

    def test_no_ceiling_at_the_finest_cut_and_none_below_it(self):
        rows6, s6 = self.table(6, size_ceiling=3, recut_targets=[6])     # nothing finer than 6: nothing re-cut
        assert s6["ceiling"]["n_recut"] == 0 and len(rows6) == 6
        rows, s = self.table(4, size_ceiling=12, recut_targets=[6])      # the blob is at the ceiling, not over it
        assert s["ceiling"]["n_recut"] == 0 and len(rows) == 4

    def test_naming_carries_over_to_unchanged_poles_and_counts_the_lost(self):
        whole, _s = self.table(4)
        for r in whole:
            for p in r["poles"]:
                p["blind"] = {"label": f"w{r['cluster_id']}", "gloss": "This means x."}
        rows, s = self.table(4, size_ceiling=10, recut_targets=[6], previous=whole)
        named = {tuple(r["items"]) for r in rows for p in r["poles"] if p.get("blind")}
        assert named == {tuple(r["items"]) for r in rows if not r.get("recut_from")}
        assert s["naming_carried_over"] == 3 and s["naming_not_carried"] == 1        # the blob's name is gone

    def test_a_piece_keeps_the_name_its_own_cut_gave_it(self):
        """Fable 2026-10-12: names carry across tables by pole items; the table's own name wins, a missing form
        comes from the other cut, marked ``carried_from``."""
        fine, _s = self.table(6)
        for r in fine:
            for p in r["poles"]:
                p["blind"] = {"label": f"fine{r['cluster_id']}", "stem": f"fine{r['cluster_id']}", "gloss": "x"}
                p["hinted"] = {"label": f"h{r['cluster_id']}", "stem": f"h{r['cluster_id']}", "gloss": "y"}
        own, _s = self.table(4)
        kept_whole = next(r for r in own if len(r["items"]) == 3)
        kept_whole["poles"][0]["blind"] = {"label": "own", "stem": "own", "gloss": "z"}
        rows, s = self.table(4, size_ceiling=10, recut_targets=[6], previous=own, carry_from=[(6, fine)])
        at6 = {tuple(r["items"]): r for r in fine}
        for r in rows:
            p, src = r["poles"][0], at6[tuple(r["items"])]
            origin = {"granularity": 6, "cluster_id": src["cluster_id"], "pole": "a"}
            if r["items"] == kept_whole["items"]:
                assert p["blind"]["label"] == "own" and "carried_from" not in p["blind"]     # its own cut's name
                assert p["hinted"]["label"] == f"h{src['cluster_id']}" and p["hinted"]["carried_from"] == origin
            else:
                assert p["blind"]["label"] == f"fine{src['cluster_id']}" and p["blind"]["carried_from"] == origin
            assert p["labels_disagree"] is True
        assert s["naming_carried_across_cuts"] == 6 and s["naming_not_carried"] == 0


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
