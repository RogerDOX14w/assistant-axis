"""Alignment sweep: within-sweep dedup (coding_plan_08_alignment_sweep.md § 8, ``dedupe``; task 6).  A hash
embedder, no network."""
from __future__ import annotations

import json

import numpy as np
import pytest

from assistant_axis.gapgen.embed import EmbeddingCache, HashEmbedder
from assistant_axis.gapgen.generators.alignment_sweep import dedupe as D
from assistant_axis.gapgen.generators.alignment_sweep import extract as X
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.alignment_sweep_fakes import item, pole


def pairs_to_items(specs, *, source="model_spec", ordinal=1, rank_start=1):
    raw = [item(pole(v[0], v[1]), pole(w[0], w[1]), source_pole=sp) for (v, w, sp) in specs]
    return X.apply_drops(X.build_items(f"{source}:v:c{ordinal}", raw, ordinal=ordinal, source=SOURCES[source],
                                       rank_start=rank_start))


HONEST_V = ("tells the truth", "This means telling the truth about facts plainly even when the truth disappoints")
HONEST_W = ("tells comfortable lies", "This means telling comfortable lies about facts whenever the truth would "
                                      "disappoint")
HONEST_V2 = ("truthful", "This means telling the truth about facts plainly even when the truth would disappoint")
SCOPE_V = ("stays within scope", "This means changing only what the task asked for and leaving every other file "
                                 "alone")
SCOPE_W = ("oversteps the task", "This means changing files the task never mentioned and doing extra work nobody "
                                 "requested")
WARM_V = ("warm", "This means greeting people kindly and showing gladness to talk with them")
WARM_W = ("cold", "This means greeting people curtly and showing no interest in talking with them")


@pytest.fixture
def world():
    a = pairs_to_items([(HONEST_V, HONEST_W, "virtue"), (SCOPE_V, SCOPE_W, "virtue")], ordinal=1)
    b = pairs_to_items([(HONEST_V2, HONEST_W, "virtue"), (WARM_V, WARM_W, "virtue")], source="constitution",
                       ordinal=2, rank_start=3)
    items = a + b
    emb = HashEmbedder(dim=256)
    vecs = D.embed_glosses(items, embedder=emb, cache=None, usage=MultiModelUsage())
    return items, vecs


def test_exact_stems_merge_and_planted_duplicates_group(world):
    items, vecs = world
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    by_member = {m: g for g in groups for m in g.members}
    # "tells comfortable lies" is proposed twice (same stem, same pole): one group, exact-stem
    assert by_member["ms001-1b"] is by_member["con002-1b"] and "exact stem" in by_member["ms001-1b"].note
    # the two honesty glosses differ by one word: grouped at 0.9
    assert by_member["ms001-1a"] is by_member["con002-1a"]
    # distinct dispositions do not group, and a virtue never groups with a vice
    assert by_member["ms001-2a"] is not by_member["ms001-1a"] and by_member["con002-2a"] is not by_member["ms001-1a"]
    assert all(len({next(i for i in items if i.item_id == m).pole for m in g.members}) == 1 for g in groups)


def test_representative_prefers_weight_then_rank(world):
    items, vecs = world
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    g = next(g for g in groups if "ms001-1a" in g.members)
    assert g.rep == "ms001-1a"                    # both weight 2: the lower rank represents
    assert g.min_cos == pytest.approx(float(vecs["ms001-1a"] @ vecs["con002-1a"]), abs=1e-4)


def test_no_group_loses_an_item_id_and_dropped_items_are_left_out(world):
    items, vecs = world
    items[2].dropped_reason = "label rule: 5 words (at most 4)"       # ms001-2a
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    members = [m for g in groups for m in g.members]
    kept = {it.item_id for it in items if it.kept}
    assert sorted(members) == sorted(kept) and len(members) == len(set(members))
    assert "ms001-2a" not in members


def test_high_threshold_keeps_everything_apart(world):
    items, vecs = world
    groups = D.dedup_groups(items, vecs, threshold=0.9999)
    exact = [g for g in groups if len(g.members) > 1]
    assert [sorted(g.members) for g in exact] == [["con002-1b", "ms001-1b"]]     # exact stems still merge


def test_partner_hints_point_at_the_partner_group_s_representative(world):
    items, vecs = world
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    hints = D.rewrite_partner_hints(items, groups)
    # con002-1a ("truthful") was deduped into ms001-1a's group: only representatives get hints
    assert "con002-1a" not in hints
    assert hints["ms001-1a"] == "tells comfortable lies" and hints["ms001-1b"] == "tells the truth"
    assert hints["con002-2a"] == "cold" and hints["con002-2b"] == "warm"
    # a representative whose partner pole was dropped gets no hint
    items[3].dropped_reason = "label rule: 5 words (at most 4)"       # ms001-2b, partner of ms001-2a
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    hints = D.rewrite_partner_hints(items, groups)
    assert hints["ms001-2a"] is None


def test_partner_hint_rewritten_to_the_representative_when_the_partner_was_deduped():
    a = pairs_to_items([(HONEST_V, HONEST_W, "virtue")], ordinal=1)
    b = pairs_to_items([(("candid with clients", "This means giving clients a frank verdict on their plans and "
                                                 "pointing out each weak spot directly"),
                         ("lies to please", "This means telling comfortable lies about facts whenever the truth would "
                                            "disappoint"), "virtue")],
                       source="constitution", ordinal=2, rank_start=2)
    items = a + b
    vecs = D.embed_glosses(items, embedder=HashEmbedder(dim=256), cache=None, usage=MultiModelUsage())
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    hints = D.rewrite_partner_hints(items, groups)
    # "lies to please" (con002-1b) joined "tells comfortable lies" (ms001-1b): its surviving partner "candid with
    # clients" (con002-1a) gets the representative's label as its partner hint, and the deduped pole gets none
    assert set(hints) == {"ms001-1a", "ms001-1b", "con002-1a"}
    assert hints["con002-1a"] == "tells comfortable lies" and hints["ms001-1a"] == "tells comfortable lies"


def test_tune_threshold_on_the_labelled_fixture():
    labeled = [{"a": "x1", "b": "y1", "same": True, "cos": 0.95}, {"a": "x2", "b": "y2", "same": True, "cos": 0.88},
               {"a": "x3", "b": "y3", "same": True, "cos": 0.80}, {"a": "x4", "b": "y4", "same": False, "cos": 0.75},
               {"a": "x5", "b": "y5", "same": False, "cos": 0.60}, {"a": "x6", "b": "y6", "same": False, "cos": 0.81}]
    t = D.tune_threshold(labeled)
    # best accuracy is 5/6 at any threshold in (0.75, 0.80] or (0.81, 0.88]; the wider gap is (0.81, 0.88], and
    # the threshold sits in its middle
    assert t.value == pytest.approx(0.845) and t.accuracy == pytest.approx(5 / 6)
    assert t.n == 6 and t.n_same == 3 and t.precision == 1.0 and t.recall == pytest.approx(2 / 3, abs=1e-4)
    with pytest.raises(ValueError):
        D.tune_threshold([])


def test_a_false_merge_costs_more_than_a_missed_one():
    """A false merge loses a candidate; a missed merge costs one more M1/M3 row, and the end-of-waves grouping
    catches it.  With the default cost 2:1 the threshold stays above every distinct pair when that costs fewer
    weighted errors; at 1:1 it is plain accuracy."""
    labeled = [{"same": True, "cos": c} for c in (0.85, 0.83, 0.79, 0.72)] + \
              [{"same": False, "cos": c} for c in (0.80, 0.74, 0.60, 0.55, 0.50)]
    t2 = D.tune_threshold(labeled)                                    # cost 2:1: (0.80, 0.83] costs 2, alone
    assert t2.value == pytest.approx(0.815) and t2.precision == 1.0 and t2.false_merge_cost == 2.0
    assert t2.recall == pytest.approx(0.5) and t2.cost == pytest.approx(2.0)
    t1 = D.tune_threshold(labeled, false_merge_cost=1.0)              # three gaps cost 2; (0.60, 0.72] is widest
    assert t1.value == pytest.approx(0.66) and t1.accuracy == pytest.approx(7 / 9)


def test_embed_glosses_uses_the_cache_and_charges_usage(tmp_path):
    items = pairs_to_items([(HONEST_V, HONEST_W, "virtue")])
    cache = EmbeddingCache(root=tmp_path / "emb")
    usage = MultiModelUsage()
    emb = HashEmbedder(dim=32)
    v1 = D.embed_glosses(items, embedder=emb, cache=cache, usage=usage)
    assert set(v1) == {"ms001-1a", "ms001-1b"} and usage.n_calls == 1
    v2 = D.embed_glosses(items, embedder=emb, cache=cache, usage=usage)
    assert usage.n_calls == 1                                         # all from the cache the second time
    assert np.allclose(v1["ms001-1a"], v2["ms001-1a"]) and np.isclose(np.linalg.norm(v1["ms001-1a"]), 1.0)


def test_pairs_for_labeling_spread_over_the_cosine_range(world):
    items, vecs = world
    pairs = D.pairs_for_labeling(items, vecs, n=4, seed=0)
    assert len(pairs) == 4 and all(p["same"] is None for p in pairs)
    for p in pairs:
        a = next(i for i in items if i.item_id == p["a"])
        b = next(i for i in items if i.item_id == p["b"])
        assert a.pole == b.pole and a.partner_item_id != b.item_id and p["gloss_a"] == a.gloss
    assert len({(p["a"], p["b"]) for p in pairs}) == 4


def test_groups_file_round_trip(world, tmp_path):
    items, vecs = world
    groups = D.dedup_groups(items, vecs, threshold=0.9)
    p = D.write_groups(groups, tmp_path / "dedup_groups.json", threshold=0.9, model="hash-256", inputs=[])
    env = json.loads(p.read_text())
    assert "_provenance" in env and env["result"]["threshold"] == 0.9
    back = D.load_groups(p)
    assert [g.as_dict() for g in back] == [g.as_dict() for g in groups]
    rep_ids = D.representatives(back)
    assert rep_ids == {g.rep for g in groups}
