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
