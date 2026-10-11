"""IPIP generator, the granularity readings: pair sampling, the item "corpus", the readout (no API)."""
import asyncio
import json

import pytest

from assistant_axis.gapgen import overlap_test as OT
from assistant_axis.gapgen.generators.ipip import granularity as G
from assistant_axis.gapgen.generators.ipip.ingest import ItemRow
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text


def item(code, text):
    return ItemRow(schema_version=1, ipip_id=code, codes=[code], text=text, scales=[])


ITEMS = {f"H{i}": item(f"H{i}", f"Do thing number {i}.") for i in range(1, 30)}


def row(cid, poles, consensus="kept"):
    return {"granularity": 350, "cluster_id": cid, "consensus": consensus,
            "items": [i for p in poles for i in p], "bipolar": len(poles) == 2,
            "poles": [{"pole": "ab"[k], "items": list(p)} for k, p in enumerate(poles)]}


ROWS = [row(1, [["H1", "H2", "H3", "H4"], ["H5", "H6"]]), row(2, [["H7", "H8", "H9"]]),
        row(3, [["H10", "H11"]]), row(4, [["H12", "H13", "H14"]], consensus="loose")]


def test_model_is_the_overlap_tests_sonnet():
    assert G.MODEL == OT.SONNET and G.CONCURRENCY == OT.DEFAULT_CONCURRENCY


def test_item_entry_shape():
    e = G.item_entry(ITEMS["H1"])
    assert e == {"label": "I do thing number 1.",
                 "description": 'This means being someone of whom "I do thing number 1." is generally true, as a '
                                'tendency rather than an episode.'}


class TestSampling:
    def test_seeded_within_pole_only_cross_flagged(self):
        calls, corpus = G.sample_pairs(ROWS, ITEMS, per_cluster=3, cross_pole=1, seed=0)
        again, _ = G.sample_pairs(ROWS, ITEMS, per_cluster=3, cross_pole=1, seed=0)
        other, _ = G.sample_pairs(ROWS, ITEMS, per_cluster=3, cross_pole=1, seed=1)
        assert [(c.call_id, c.target, c.listed) for c in calls] == [(c.call_id, c.target, c.listed) for c in again]
        assert [(c.target, c.listed) for c in calls] != [(c.target, c.listed) for c in other]
        pole_of = {i: (r["cluster_id"], p["pole"]) for r in ROWS for p in r["poles"] for i in p["items"]}
        within = [c for c in calls if c.set == "within"]
        cross = [c for c in calls if c.set == "cross"]
        assert all(pole_of[c.target] == pole_of[c.listed[0]] for c in within)
        assert all(pole_of[c.target][0] == pole_of[c.listed[0]][0] and pole_of[c.target][1] != pole_of[c.listed[0]][1]
                   for c in cross)
        # cluster 1: 3 of its 7 within-pole pairs, 1 cross; cluster 2: 3 of 3; cluster 3: 1 of 1; loose: none
        per = {}
        for c in within:
            per[pole_of[c.target][0]] = per.get(pole_of[c.target][0], 0) + 1
        assert per == {1: 3, 2: 3, 3: 1} and len(cross) == 1
        assert all(isinstance(c, OT.PairCall) and len(c.listed) == 1 for c in calls)
        assert len({c.call_id for c in calls}) == len(calls)
        # the id names the pair, so a later, different split cannot reuse an answer for another pair
        assert all(c.call_id == f"{c.origin_call_id}:{c.set}:{c.target}>{c.listed[0]}" for c in calls)
        assert set(corpus) == {i for c in calls for i in (c.target, c.listed[0])}
        assert not any(c.target in ("H12", "H13", "H14") for c in calls)

    def test_no_pair_repeats_within_a_cluster(self):
        calls, _ = G.sample_pairs(ROWS, ITEMS, per_cluster=10, cross_pole=3, seed=0)
        pairs = [frozenset((c.target, c.listed[0])) for c in calls]
        assert len(pairs) == len(set(pairs))
        assert sum(1 for c in calls if c.set == "within" and c.origin_call_id.endswith("c001")) == 7


def rec(call_id, set_, value):
    text = json.dumps({"reason": "r", "similarity": value})
    return {"rubric": "A", "rubric_version": 6, "form": "single", "model": "claude-sonnet-5-5", "call_id": call_id,
            "set": set_, "target": "x", "listed": ["y"], "pass": 1, "parse_attempt": 1,
            "response": {"text": text, "usage_raw": {"input_tokens": 900, "output_tokens": 60}}}


def test_readout_shares_sum_to_one_and_share_3_4():
    records = ([rec(f"w{i}", "within", v) for i, v in enumerate([0, 1, 2, 3, 3, 4, "opposite", "unsure"])]
               + [rec("c0", "cross", "opposite"), rec("c1", "cross", 1)]
               + [{**rec("w9", "within", 2), "response": {"text": "not json", "usage_raw": {}}}])
    r = G.readout(records, granularity=350, n_clusters=3, label_form="judge-display-v1", cost_usd=0.01,
                  model="claude-sonnet-5-5", rubric_version=6)
    w = r["within"]
    shares = [w[k] for k in ("0", "1", "2", "3", "4", "opposite", "unsure")]
    assert sum(shares) == pytest.approx(1.0)
    assert w["share_3_4"] == pytest.approx(3 / 8) and w["n"] == 8 and w["n_unparsed"] == 1
    assert r["cross_pole"] == {"n": 2, "opposite": 0.5, "n_unparsed": 0}
    assert r["n_pairs_read"] == 10 and r["label_form"] == "judge-display-v1" and r["rubric"] == "A"
    assert r["granularity"] == 350 and r["n_clusters"] == 3 and r["model"] == "claude-sonnet-5-5"


def test_runner_reads_items_through_the_pinned_rubric(tmp_path):
    rubrics = OT.load_rubrics(keys=["A"])
    assert rubrics["A"]["form"] == "single"
    calls, corpus = G.sample_pairs(ROWS[:2], ITEMS, per_cluster=2, cross_pole=1, seed=0)

    def respond(kw):
        assert '"target": {"label": "I do thing number' in user_text(kw)
        return make_response(json.dumps({"reason": "r", "similarity": 3}), input_tokens=900, output_tokens=60)
    client = FakeAsyncAnthropic(respond)
    usage = MultiModelUsage()
    res = asyncio.run(G.run_readings(calls, corpus, client=client, usage=usage, out_dir=tmp_path / "g350",
                                     rubrics=rubrics))
    assert res.n_ok == len(calls) and usage.n_calls == len(calls)
    assert (tmp_path / "g350" / "responses.jsonl").exists() and (tmp_path / "g350" / "usage.json").exists()
    recs = OT.read_records(tmp_path / "g350" / "responses.jsonl")
    r = G.readout(recs, granularity=350, n_clusters=2, label_form="judge-display-v1", cost_usd=usage.total_cost_usd,
                  model=G.MODEL, rubric_version=rubrics["A"]["version"])
    assert r["within"]["share_3_4"] == 1.0 and r["rubric_version"] == rubrics["A"]["version"]


def test_estimate_cached_below_uncached_at_scale():
    items = {f"H{i}": item(f"H{i}", f"Do thing number {i}.") for i in range(1, 401)}
    rows = [row(c, [[f"H{4 * c + k}" for k in range(1, 5)]]) for c in range(99)]
    calls, corpus = G.sample_pairs(rows, items, seed=0)
    rubrics = OT.load_rubrics(keys=["A"])
    e = G.estimate_usd(calls, corpus, rubrics)
    assert e["n_calls"] == len(calls) == 297
    assert 0 < e["cached_usd"] < e["uncached_usd"]          # the 8 concurrent first calls write the cache


# --------------------------------------------------------------------------- QUESTIONS 50: the two signals

def named(label, gloss=None, kind="trait"):
    return {"label": label, "stem": label.replace(" ", "_").replace("-", "_"),
            "gloss": gloss or f"This means being {label}.", "kind": kind, "antonym_label": None}


def nrow(cid, poles, consensus="kept", granularity=350):
    """A cluster row as ``cluster`` writes it: ``poles`` is ``[(pole, items, blind label, nearest_other)]``."""
    return {"granularity": granularity, "cluster_id": cid, "consensus": consensus,
            "items": [i for _p, its, _l, _n in poles for i in its], "bipolar": len(poles) == 2,
            "nearest_corpus": {"stem": "orderly", "mean_cos": 0.41},
            "poles": [{"pole": p, "items": list(its),
                       **({"blind": named(lab), "hinted": named(lab + " (hinted)")} if lab else {}),
                       **({"nearest_other": nn} if nn else {})} for p, its, lab, nn in poles]}


NROWS = [
    nrow(1, [("a", ["H1", "H2", "H3", "H4"], "tidy", {"cluster_id": 2, "pole": "a", "cos": 0.8}),
             ("b", ["H5", "H6"], "messy", None)]),
    nrow(2, [("a", ["H7", "H8", "H9"], "orderly", {"cluster_id": 1, "pole": "a", "cos": 0.8})]),
    nrow(3, [("a", ["H10", "H11"], "punctual", {"cluster_id": 2, "pole": "a", "cos": 0.5})]),
    nrow(4, [("a", ["H12", "H13"], None, {"cluster_id": 3, "pole": "a", "cos": 0.4})]),   # not named
    nrow(5, [("a", ["H14", "H15"], "loose one", {"cluster_id": 1, "pole": "a", "cos": 0.2})], consensus="loose"),
]


def test_size_bands():
    assert G.BAND_LABELS == ("2-3", "4-7", "8-15", "16+")
    assert [G.band_of(n) for n in (1, 2, 3, 4, 7, 8, 15, 16, 400)] == [
        "2-3", "2-3", "2-3", "4-7", "4-7", "8-15", "8-15", "16+", "16+"]


def test_pole_entry_is_the_name_and_gloss():
    p = NROWS[0]["poles"][0]
    assert G.pole_entry(p) == {"label": "tidy", "description": "This means being tidy."}
    assert G.pole_entry(p, form="hinted")["label"] == "tidy (hinted)"
    assert G.pole_entry({"pole": "a", "items": []}) is None


class TestNearestOtherCluster:
    """Signal 1: each pole against the nearest pole of another cluster, read by name and gloss."""

    def test_one_call_per_unordered_pair_of_named_poles(self):
        calls, corpus, counts = G.nearest_pair_calls(NROWS)
        assert [(c.target, c.listed[0], c.set) for c in calls] == [("c001a", "c002a", "nearest"),
                                                                   ("c003a", "c002a", "nearest")]
        # cluster 1a and 2a are each other's nearest: the pair is asked once, not twice
        assert len({frozenset((c.target, c.listed[0])) for c in calls}) == len(calls)
        assert counts["n_unnamed"] == 1 and counts["n_without_nearest"] == 1
        assert counts["n_poles"] == 5 and counts["n_named"] == 4          # the loose cluster is left out
        assert set(corpus) == {"c001a", "c002a", "c003a"}
        assert corpus["c001a"] == {"label": "tidy", "description": "This means being tidy."}
        assert all(c.origin_call_id == G.origin_id(350, int(c.target[1:4])) for c in calls)

    def test_the_hinted_name_can_be_read_instead(self):
        _calls, corpus, counts = G.nearest_pair_calls(NROWS, form="hinted")
        assert corpus["c001a"]["label"] == "tidy (hinted)" and counts["form"] == "hinted"

    def test_bands_come_from_the_cluster_the_call_belongs_to(self):
        calls, _corpus, _counts = G.nearest_pair_calls(NROWS)
        within, _c = G.sample_pairs(NROWS, {f"H{i}": item(f"H{i}", f"Do thing {i}.") for i in range(1, 16)},
                                    per_cluster=1, cross_pole=0, seed=0)
        bands = G.call_bands(NROWS, list(calls) + list(within))
        assert bands[calls[0].call_id] == "4-7"          # cluster 1 holds 6 items
        assert bands[calls[1].call_id] == "2-3"          # cluster 3 holds 2
        assert all(b in G.BAND_LABELS for b in bands.values())


def test_readout_splits_the_signals_and_the_bands():
    records = ([rec(f"{G.origin_id(350, 1)}:within:H1>H2", "within", 3),
                rec(f"{G.origin_id(350, 3)}:within:H10>H11", "within", 1),
                rec(f"{G.origin_id(350, 1)}:nearest:c001a>c002a", "nearest", 3),
                rec(f"{G.origin_id(350, 3)}:nearest:c003a>c002a", "nearest", 2)])
    calls, _corpus, counts = G.nearest_pair_calls(NROWS)
    within_calls, _c = G.sample_pairs(NROWS, {f"H{i}": item(f"H{i}", f"Do thing {i}.") for i in range(1, 16)},
                                      per_cluster=1, cross_pole=0, seed=0)
    bands = {r["call_id"]: G.band_of(6 if ":c001:" in r["call_id"] else 2) for r in records}
    r = G.readout(records, granularity=350, n_clusters=4, label_form="judge-display-v1", cost_usd=0.02,
                  bands=bands, sizes=G.band_sizes(NROWS), nearest_counts=counts)
    assert r["nearest"]["n"] == 2 and r["nearest"]["share_3"] == 0.5 and r["nearest"]["share_3_4"] == 0.5
    assert r["within"]["n"] == 2 and r["within"]["share_3_4"] == 0.5
    assert r["nearest_by_band"]["4-7"]["share_3"] == 1.0 and r["nearest_by_band"]["4-7"]["n"] == 1
    assert r["nearest_by_band"]["2-3"]["share_3"] == 0.0 and r["nearest_by_band"]["2-3"]["n"] == 1
    assert r["nearest_by_band"]["16+"]["n"] == 0
    assert set(r["nearest_by_band"]) == set(G.BAND_LABELS)
    assert r["sizes"]["per_band"] == {"2-3": 3, "4-7": 1, "8-15": 0, "16+": 0}   # kept: 6, 3, 2, 2 items
    assert r["nearest_counts"]["n_calls"] == len(calls) and len(within_calls) == 4
    assert r["bands"] == list(G.BAND_LABELS)


def test_spanning_clusters_covers_the_size_range():
    rows = [nrow(c, [("a", [f"H{c}_{k}" for k in range(c)], f"word{c}", None)]) for c in range(2, 40)]
    picks = G.spanning_clusters(rows, 5, seed=0)
    sizes = sorted(len(r["items"]) for r in picks)
    assert len(picks) == 5 and sizes[-1] == 39                 # the largest cluster is always shown
    assert sizes[0] <= 11 and len(set(sizes)) == 5 and max(sizes) - min(sizes) > 25
    assert picks == G.spanning_clusters(rows, 5, seed=0)       # seeded
    assert [int(r["cluster_id"]) for r in picks] == sorted(int(r["cluster_id"]) for r in picks)
    assert len(G.spanning_clusters(rows[:3], 5)) == 3
    assert G.spanning_clusters([], 5) == []


def test_readout_markdown_prints_the_clusters_in_full(tmp_path):
    items = {f"H{i}": item(f"H{i}", f"Do thing number {i}.") for i in range(1, 16)}
    calls, _corpus, counts = G.nearest_pair_calls(NROWS)
    ro = G.readout([rec(calls[0].call_id, "nearest", 3)], granularity=350, n_clusters=4,
                   label_form="judge-display-v1", cost_usd=0.02, bands={calls[0].call_id: "4-7"},
                   sizes=G.band_sizes(NROWS), nearest_counts=counts)
    md = G.readout_markdown([ro], samples={350: NROWS[:2]}, items=items,
                            answers={G.origin_id(350, 1): [{"set": "nearest", "target": "tidy", "other": "orderly",
                                                            "value": "3", "reason": "much the same"}]},
                            doc_path=tmp_path / "granularity_readout.md",
                            files=[tmp_path / "granularity_readout.json"])
    assert "## Signal 1: each pole against the nearest pole of another cluster" in md
    assert "## Signal 2: ~350 clusters" in md and "spanning the size range" in md
    for band in G.BAND_LABELS:
        assert f"| {band} items |" in md
    # every item statement of a printed cluster, with both names of each pole
    for i in NROWS[0]["poles"][0]["items"]:
        assert f"- {G.item_embed_text(items[i].text)}" in md
    assert "blind **tidy**" in md and "hinted **tidy (hinted)**" in md
    assert "nearest other cluster: c002a at 0.8" in md
    assert "nearest corpus trait (novelty, not size)" in md          # kept apart from the size signals
    assert "finer** cut is preferred" in md
    assert "(granularity_readout.json)" in md
