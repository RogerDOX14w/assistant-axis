"""R1 after gate audit 8 (reports/code_review_2026-10-12/gate_audits/review_graph_thresholds.md; Roger, 2026-10-12):
the candidate edges as the k nearest **and** every pair at the pair floor (0.55); the label-variant link
(other-worldly / otherworldly, a 3-edge whatever its readings); the estimate calibrated on an earlier R1 build's own
records; and the Opus pilot on first directions Sonnet read 2, its selection against Roger's decisions and its
report.  No API calls: the fake Anthropic client and the toy corpus of ``test_gapgen_review_graph``."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.tests.fake_anthropic import user_text
from assistant_axis.tests.test_gapgen_novelty import responder_for
from assistant_axis.tests.test_gapgen_review_graph import (
    BATCH, OVERLAP, QUEUE, RELATIONS, both, edge, key, make_runner, overlap_calls, row, toy_rows, toy_vectors)


@pytest.fixture(autouse=True)
def _no_real_operator_table(monkeypatch):
    """Keep these tests hermetic: never read the repository's real structural operator table (review S5)."""
    monkeypatch.setattr(RG, "structural_operator_table", lambda *a, **k: [])

GODLESS3 = sorted(key(x) for x in ["godless", "irreligious", "nonreligious"])


def pad(vectors: dict, dim: int) -> dict:
    return {k: np.concatenate([v, np.zeros(dim - len(v))]) for k, v in vectors.items()}


def build_plan(tmp_path, plan, responder=None, *, name="out", proposed_cut_off=RG.DEFAULT_PROPOSED_CUT_OFF):
    runner, client, idx = make_runner(tmp_path, responder or responder_for(RELATIONS, OVERLAP), name=name)
    g = RG.build_graph(plan, runner=runner, corpus=idx.traits, queue=QUEUE, batch_id="rv",
                       proposed_cut_off=proposed_cut_off)
    return g, runner, client


# --------------------------------------------------------------------------- the pair floor (P1)

class TestPairFloor:
    def test_nearest_candidates_the_k_nearest_then_every_further_pair_at_the_pair_floor(self):
        v = {"a": np.array([1.0, 0, 0]), "b": np.array([.9, .436, 0]), "c": np.array([.6, 0, .8]),
             "d": np.array([.5, .866, 0]), "e": np.array([0, 0, 1.0])}
        # cosines from a: b 0.90, c 0.60, d 0.50 (e 0)
        assert [x for x, _ in RG.nearest_candidates(v, k=1, floor=0.25)["a"]] == ["b"]
        got = RG.nearest_candidates(v, k=1, floor=0.25, pair_floor=0.55)["a"]
        assert [x for x, _ in got] == ["b", "c"] and got[1][1] == pytest.approx(0.6, abs=1e-6)
        # the k nearest still stop at the retrieval floor; a pair floor below it does not reach under it
        assert [x for x, _ in RG.nearest_candidates(v, k=3, floor=0.55, pair_floor=0.55)["a"]] == ["b", "c"]
        assert [x for x, _ in RG.nearest_candidates(v, k=1, floor=0.55, pair_floor=0.3)["a"]] == ["b", "c"]
        # a k large enough to hold them all: the pair floor adds nothing
        assert RG.nearest_candidates(v, k=10, floor=0.25, pair_floor=0.55) == RG.nearest_candidates(v, k=10, floor=0.25)

    def test_the_union_restores_a_triangle_k_alone_shatters(self, tmp_path):
        # k = 1: godless lists irreligious (0.9, the tie broken by key), nonreligious and irreligious list godless;
        # irreligious / nonreligious (0.81) is in neither list.  The pair floor 0.55 brings it in.
        old = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=1, cosine_floor=0.25, pair_floor=None)
        new = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=1, cosine_floor=0.25, pair_floor=0.55)
        ir_nr = (key("irreligious"), key("nonreligious"))
        assert ir_nr not in old.edges and old.via == {} and old.pair_floor is None
        assert set(new.edges) == set(old.edges) | {ir_nr}
        assert {e: c for e, c in new.edges.items() if e in old.edges} == old.edges        # the k nearest unchanged
        assert new.via == {ir_nr: "pair_floor"} and new.edges[ir_nr] == pytest.approx(0.81, abs=1e-3)
        # listed in both candidates' relation calls, after their k nearest
        items = dict(new.relation_items())
        assert items[key("irreligious")] == [key("godless"), key("nonreligious")]
        assert items[key("nonreligious")] == [key("godless"), key("irreligious")]
        assert new.edge_counts()["by_via"] == {"k_nearest": len(old.edges), "pair_floor": 1, "label_variant": 0}
        # built: read like any other edge, so the triangle is one merged group again
        g_old, _, _ = build_plan(tmp_path, old, name="old")
        g_new, _, client = build_plan(tmp_path, new, name="new")
        assert GODLESS3 not in g_old.cliques and [key("godless"), key("irreligious")] in g_old.cliques
        assert GODLESS3 in g_new.cliques
        e = edge(g_new, "irreligious", "nonreligious")
        assert e.via == "pair_floor" and e.strict and e.relations == {"ab": "similar", "ba": "similar"}
        assert ("irreligious", "nonreligious", "sonnet") in overlap_calls(client)
        assert edge(g_new, "godless", "irreligious").via is None                      # a k-nearest edge has none
        assert g_new.stats["candidate_edges"]["by_via"] == {"k_nearest": len(old.edges), "pair_floor": 1}
        assert g_new.stats["plan_edges"]["pair_floor"] == 0.55
        d = json.loads(json.dumps(g_new.to_json()))
        assert RG.Graph.from_json(d).to_json() == g_new.to_json() and d["schema"] == RG.GRAPH_SCHEMA == 4   # 4 since the relabel pairs (2026-10-14)

    def test_the_default_is_the_pair_floor_and_none_is_the_rule_before(self):
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=1, cosine_floor=0.25)
        assert plan.pair_floor == RG.DEFAULT_PAIR_FLOOR == 0.55 and plan.via
        assert RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=1, cosine_floor=0.25, pair_floor=None).via == {}


class TestLongListsSplit:
    """A list longer than RELATION_LIST_MAX (40) is split over several relation calls (the pair floor gave one of 79
    in the all-batches plan, which would overrun the call's 4,096 output tokens); here the maximum is 2."""

    def test_the_split_calls_give_the_same_graph(self, tmp_path, monkeypatch):
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        g1, _, c1 = build_plan(tmp_path, plan, name="one")
        monkeypatch.setattr(RG, "RELATION_LIST_MAX", 2)
        g2, runner, c2 = build_plan(tmp_path, plan, name="split")
        rel = lambda c: [json.loads(user_text(kw)) for kw in c.calls if "candidate" in json.loads(user_text(kw))]  # noqa: E731
        lens = [len(v) for v in plan.neighbours.values() if v]
        assert len(rel(c1)) == len(lens) and len(rel(c2)) == sum(-(-n // 2) for n in lens)
        assert max(len(x["traits"]) for x in rel(c2)) == 2
        # godless lists 5: three calls of 2, 2 and 1, in the seeded order of the one call
        godless = [[t["label"] for t in x["traits"]] for x in rel(c2) if x["candidate"]["label"] == "godless"]
        whole = next([t["label"] for t in x["traits"]] for x in rel(c1) if x["candidate"]["label"] == "godless")
        assert [len(p) for p in godless] == [2, 2, 1] and sum(godless, []) == whole
        assert [(e.a, e.b, e.relation, e.relations, e.strict, e.proposed) for e in g2.edges] == \
            [(e.a, e.b, e.relation, e.relations, e.strict, e.proposed) for e in g1.edges]
        assert g2.cliques == g1.cliques and g2.proposed_groups == g1.proposed_groups and g2.complete
        assert plan.edge_counts()["lists_split"] == sum(1 for n in lens if n > 2)

    def test_a_part_that_never_parses_answers_unparsed_and_a_failed_part_is_resent_alone(self, tmp_path, monkeypatch):
        monkeypatch.setattr(RG, "RELATION_LIST_MAX", 2)
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        good = responder_for(RELATIONS, OVERLAP)

        def bad(kind):
            def resp(kw):
                obj = json.loads(user_text(kw))
                if "candidate" in obj and obj["candidate"]["label"] == "godless" and \
                        any(t["label"] == "skeptic" for t in obj["traits"]):
                    return "no JSON here" if kind == "garbage" else RuntimeError("network down")
                return good(kw)
            return resp
        runner, _, _ = make_runner(tmp_path, bad("garbage"), name="garbage")
        runner.add_candidates(plan.cands.values())
        rec = runner.run_relations(plan.relation_items())[key("godless")]
        part = next(p for p in [rec["order"][i:i + 2] for i in range(0, 5, 2)] if key("skeptic") in p)
        assert rec["status"] == "unparsed" and [p["status"] for p in rec["parts"]].count("unparsed") == 1
        assert all(rec["answers"][s]["relation"] == "unparsed" for s in part)
        assert all(rec["answers"][s]["relation"] != "unparsed" for s in rec["order"] if s not in part)
        assert RG._answer(rec, key("skeptic")) == "unparsed"
        # a failed part stalls the graph; a resume sends that part alone
        g, _, _ = build_plan(tmp_path, plan, bad("fail"), name="fail")
        assert not g.complete and key("godless") in g.stalled["relation"]
        recs = [json.loads(x) for x in (tmp_path / "fail" / "responses.jsonl").read_text().splitlines()]
        runner2, client2, idx = make_runner(tmp_path, good, records=recs, name="fail")
        g2 = RG.build_graph(plan, runner=runner2, corpus=idx.traits, queue=QUEUE, batch_id="rv")
        sent_rel = [json.loads(user_text(kw)) for kw in client2.calls if "candidate" in json.loads(user_text(kw))]
        assert len(sent_rel) == 1 and sent_rel[0]["candidate"]["label"] == "godless"
        assert "skeptic" in [t["label"] for t in sent_rel[0]["traits"]]
        assert g2.complete and GODLESS3 in g2.cliques


# --------------------------------------------------------------------------- the label variants (P5)

DIM2 = 14


def variant_rows(cos_far: bool = True) -> tuple[dict, dict]:
    """The toy plus other-worldly / otherworldly (cosine 0.2, under the retrieval floor, when ``cos_far``; else
    0.545, the TDA case) and two senses of one word (cold#1, cold#2: one stem, never variants)."""
    rows = toy_rows()
    for lb in ("other-worldly", "otherworldly"):
        r = row(lb)
        r["key"], r["stem"] = f"{normalize(lb)}#1", normalize(lb)
        rows[r["key"]] = r
    for i in (1, 2):
        r = row("cold")
        r["key"] = f"cold#{i}"
        rows[r["key"]] = r
    vec = pad(toy_vectors(), DIM2)
    e12, e13 = np.eye(DIM2)[12], np.eye(DIM2)[13]
    c = 0.2 if cos_far else 0.545
    vec["other_worldly#1"] = e12
    vec["otherworldly#1"] = c * e12 + np.sqrt(1 - c * c) * e13
    vec["cold#1"] = vec["cold#2"] = np.eye(DIM2)[11]
    return rows, vec


def normalize(label: str) -> str:
    from assistant_axis.entity_id import normalize_to_file_name
    return normalize_to_file_name(label)


class TestLabelVariants:
    def test_the_blind_form(self):
        k = RG.label_variant_key
        assert k("other-worldly") == k("otherworldly") == k("Other Worldly") == "otherworldly"
        assert k("self-willed") == k("self willed") != k("selfish")

    def test_pairs_whose_labels_are_one_label_blind_and_whose_stems_differ(self):
        rows, _ = variant_rows()
        plan = RG.plan_graph(rows, [BATCH], variant_rows()[1], k=10)
        assert plan.label_variants == [("other_worldly#1", "otherworldly#1")]       # cold#1 / cold#2: one stem

    def test_a_variant_pair_outside_the_lists_is_linked_listed_and_a_3_edge_unread(self, tmp_path):
        rows, vec = variant_rows(cos_far=True)
        plan = RG.plan_graph(rows, [BATCH], vec, k=10, cosine_floor=0.25)
        p = ("other_worldly#1", "otherworldly#1")
        assert plan.edges[p] == pytest.approx(0.2, abs=1e-6) and plan.via[p] == "label_variant"
        items = dict(plan.relation_items())
        assert items["other_worldly#1"] == ["otherworldly#1"] and items["otherworldly#1"] == ["other_worldly#1"]
        g, _, client = build_plan(tmp_path, plan)                   # the relation calls answer "unrelated"
        e = next(x for x in g.edges if (x.a, x.b) == p)
        assert e.label_variant and e.via == "label_variant" and e.proposed and not e.strict
        assert e.relation == "unrelated" and e.overlap == "not_similar" and e.readings == {}
        assert list(p) in g.proposed_groups
        assert not any("worldly" in t for t, _, _ in overlap_calls(client))           # never read
        assert g.stats["candidate_edges"]["label_variants"] == 1
        assert RG.Graph.from_json(json.loads(json.dumps(g.to_json()))).to_json() == g.to_json()

    def test_a_variant_read_3_then_2_by_opus_is_still_a_3_edge_never_a_4_edge(self, tmp_path):
        # the TDA case: other-worldly / otherworldly at 0.545, read 3/2 because the two glosses took different senses
        rows, vec = variant_rows(cos_far=False)
        plan = RG.plan_graph(rows, [BATCH], vec, k=10, cosine_floor=0.25)
        p = ("other_worldly#1", "otherworldly#1")
        assert p not in plan.via and plan.label_variants == [p]                       # a k-nearest edge already
        rel = {**RELATIONS, **both([("other-worldly", "otherworldly")], "similar")}
        ov = {**OVERLAP, ("other-worldly", "otherworldly", "sonnet"): 3, ("other-worldly", "otherworldly", "opus"): 2}
        g, _, _ = build_plan(tmp_path, plan, responder_for(rel, ov))
        e = next(x for x in g.edges if (x.a, x.b) == p)
        assert e.readings["ab"]["sonnet"] == 3 and e.readings["ab"]["opus"] == 2 and e.overlap == "first"
        assert e.label_variant and e.proposed and not e.strict and e.via is None
        assert list(p) in g.proposed_groups and not any(set(p) <= set(c) for c in g.cliques)
        # the same pair read 4 both ways is a 4-edge as any other
        g4, _, _ = build_plan(tmp_path, plan, responder_for(rel, {**OVERLAP, **both([("other-worldly", "otherworldly")], 4)}),
                              name="out4")
        assert list(p) in g4.cliques

    def test_a_candidate_without_a_vector_has_no_variant_edge(self):
        rows, vec = variant_rows()
        del vec["otherworldly#1"]
        plan = RG.plan_graph(rows, [BATCH], vec, k=10)
        assert plan.label_variants == [] and "otherworldly#1" in plan.no_vector


# --------------------------------------------------------------------------- the estimate, calibrated on R1 (P4)

def hand_graph(edges) -> RG.Graph:
    return RG.Graph(batch_id="rv_prev", from_batches=["m"], config={}, nodes=[], edges=edges, cliques=[])


def r1(a, b, cos, rel, ab=None, ba=None, stalled=False) -> RG.Edge:
    def rd(x):
        if x is None:
            return None
        s, o = x
        return RG.reading_of({"sonnet": {"value": s}, "opus": {"value": o} if o is not None else None})
    readings = {d: rd(x) for d, x in (("ab", ab), ("ba", ba)) if x is not None}
    if stalled:
        readings["ab"] = {"stalled": "x"}
    return RG.Edge(a=a, b=b, cosine=cos, relation=rel, source="r1", readings=readings)


class TestR1Shares:
    def test_the_shares_from_a_build_s_own_readings_by_hand(self):
        edges = [
            # bin 0.35: 4 edges, 2 similar; read: 2/-, 3/3 (Opus; sends the second, 2/-)
            r1("a", "b", 0.36, "similar", (2, None)), r1("a", "c", 0.40, "unsure", (3, 3), (2, None)),
            r1("a", "d", 0.41, "unrelated"), r1("a", "e", 0.44, "opposed"),
            # bin 0.55: 2 edges, both similar; 4/4 both ways, and 1/-
            r1("b", "c", 0.60, "similar", (4, 4), (4, 4)), r1("b", "d", 0.70, "mixed", (1, None)),
            r1("x", "y", 0.20, "similar"),                                          # below the first bin: not counted
            r1("p", "q", 0.40, "similar", stalled=True),                            # a stalled reading is no observation
            RG.Edge(a="a", b="trait:t", cosine=0.5, relation="similar", source="m3"),  # an M3 edge: not R1's
        ]
        sh = RG.r1_shares([hand_graph(edges)], bins=(0.35, 0.55), min_obs=1)
        assert sh.n_listed == (5, 2) and sh.n_read == (2, 2)
        assert sh.similar == pytest.approx((3 / 5, 1.0)) and sh.opus == pytest.approx((0.5, 0.5))
        assert sh.four == pytest.approx((0.0, 0.5)) and sh.second == pytest.approx((0.5, 0.5))
        assert sh.second_opus == pytest.approx(1 / 2) and sh.n_second == 2 and sh.source == "r1:rv_prev"
        # a bin, or the second-direction share, with fewer than min_obs observations takes 1.0 (the estimate errs high)
        sh10 = RG.r1_shares([hand_graph(edges)], bins=(0.35, 0.55), min_obs=3)
        assert sh10.similar[1] == 1.0 and sh10.opus == (1.0, 1.0) and sh10.second_opus == 1.0
        # the second-direction share is recomputed at the cut-off asked for (a build at 4 serves a build at 3)
        assert RG.r1_shares([hand_graph(edges)], bins=(0.35, 0.55), min_obs=1, second_at=4).second == \
            pytest.approx((0.0, 0.5))
        d = sh.as_dict()
        assert d["second_opus"] == 0.5 and d["source"] == "r1:rv_prev" and d["n_second"] == 2

    def test_the_m3_shares_keep_the_assumed_second_opus_share(self):
        sh = RG.Shares(bins=(0.35,), similar=(1.0,), opus=(0.5,), four=(0.5,), n_listed=(10,), n_read=(10,))
        assert sh.second_opus_share() == RG.SECOND_OPUS_SHARE == 1.0
        assert sh.all_similar().second_opus_share() == 1.0
        sh2 = RG.Shares(bins=(0.35,), similar=(0.2,), opus=(0.5,), four=(0.5,), n_listed=(10,), n_read=(10,),
                        second_opus=0.9, source="r1:x")
        assert sh2.all_similar().similar == (1.0,) and sh2.all_similar().second_opus == 0.9

    def test_unsure_reasks_from_the_records(self):
        recs = [{"step": "relation", "parse_attempt": 1}] * 8 + [{"step": "relation", "parse_attempt": 2}] + \
            [{"step": "relation_unsure", "parse_attempt": 1, "stems": ["x", "y"]},
             {"step": "relation_unsure", "parse_attempt": 1, "stems": ["z"]}, {"step": "overlap"}]
        assert RG.r1_unsure(recs) == (pytest.approx(2 / 8), pytest.approx(1.5))
        assert RG.r1_unsure([{"step": "overlap"}]) is None

    def test_the_estimate_calibrated_on_a_build_reproduces_that_build_s_calls_and_spend(self, tmp_path):
        """In sample, the estimate of a plan from its own build's readings is that build: every overlap line's calls
        and the overlap spend (the TDA build replayed this way: $4.99 against $5.00 spent, against $16.09 from M3's
        shares)."""
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        rel = {**RELATIONS}
        g, runner, client = build_plan(tmp_path, plan, responder_for(rel, OVERLAP))
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        shares = RG.r1_shares([g], bins=(0.35, 0.55), min_obs=1)
        tokens = RG.measured_overlap_tokens(recs)
        assert tokens == {"sonnet": (210, 80), "opus": (210, 80)}                     # 150 + 0.1 x 600 cache read
        est = RG.estimate_build(relation_calls=[], edge_cosines=plan.edges.values(), shares=shares,
                                overlap_floor=0.35, overlap_tokens=tokens)
        n = {x.label.split(" (")[0]: x.n_calls for x in est.lines}
        sent = {(r["wave"], r["role"]) for r in recs}
        count = lambda w, role: sum(1 for r in recs if r["wave"] == w and r["role"] == role)  # noqa: E731
        assert ("ov1_sonnet", "sonnet") in sent and ("ov2_opus", "opus") in sent
        assert n["overlap, first direction, Sonnet"] == count("ov1_sonnet", "sonnet")
        assert n["overlap, first direction, Opus"] == count("ov1_opus", "opus")
        assert n["overlap, second direction, Sonnet"] == count("ov2_sonnet", "sonnet")
        assert n["overlap, second direction, Opus"] == count("ov2_opus", "opus")
        spent = sum(NR.record_cost(r) for r in recs if r["step"] == "overlap")
        assert est.usd == pytest.approx(spent)
        # the same plan from M3-style shares that send everything on: several times dearer
        flat = RG.Shares(bins=(0.35,), similar=(1.0,), opus=(1.0,), four=(1.0,), n_listed=(10,), n_read=(10,),
                         second=(1.0,))
        assert RG.estimate_build(relation_calls=[], edge_cosines=plan.edges.values(), shares=flat,
                                 overlap_tokens=tokens).usd > 2 * est.usd


# --------------------------------------------------------------------------- the Opus pilot (P2)

class TestPilotSelection:
    def test_sonnet2_pairs_are_first_directions_sonnet_read_2_that_opus_never_read(self):
        g = hand_graph([r1("a", "b", 0.5, "similar", (2, None)), r1("a", "c", 0.6, "similar", (3, 2)),
                        r1("a", "d", 0.7, "similar", (4, 4), (2, None)), r1("b", "c", 0.4, "similar", (1, None)),
                        r1("c", "d", 0.4, "similar", stalled=True),
                        RG.Edge(a="a", b="trait:t", cosine=0.5, relation="similar", source="m3",
                                readings={"ab": RG.reading_of({"sonnet": {"value": 2}, "opus": None})})])
        assert RG.sonnet2_pairs(g) == [{"a": "a", "b": "b", "cosine": 0.5, "relation": "similar"}]

    def test_resolution_labels_from_the_log_s_resolved_groups(self):
        groups = [{"id": "g1", "resolution": "merge_into:trait:unyielding", "nominated": None,
                   "resolved_members": ["a#1", "b#1"]},
                  {"id": "g2", "resolution": "merge_into:trait:unyielding", "nominated": None,
                   "resolved_members": ["c#1"]},
                  {"id": "g3", "resolution": "promote", "nominated": "d#1", "resolved_members": ["d#1", "e#1"]},
                  {"id": "g4", "resolution": "merge_into:queue:d", "nominated": None, "resolved_members": ["f#1"]},
                  {"id": "g5", "resolution": "reject", "nominated": None, "resolved_members": ["h#1"]},
                  {"id": "g6", "resolution": "park", "nominated": None, "resolved_members": ["i#1"]},
                  {"id": "g7", "resolution": "defer", "nominated": None, "resolved_members": ["j#1"]}]
        lab = RG.resolution_labels(groups, stem_of={"d#1": "d"})
        assert lab == {"a#1": "trait:unyielding", "b#1": "trait:unyielding", "c#1": "trait:unyielding",
                       "d#1": "queue:d", "e#1": "queue:d", "f#1": "queue:d", "h#1": "reject:g5"}

    def pool(self):
        """30 same-resolution pairs and 60 different, spread over the bins."""
        pairs, labels = [], {}
        for i in range(90):
            a, b = f"a{i:02d}", f"b{i:02d}"
            labels[a] = f"t{i}"
            labels[b] = f"t{i}" if i < 30 else f"u{i}"
            pairs.append({"a": a, "b": b, "cosine": [0.38, 0.5, 0.6, 0.7][i % 4], "relation": "similar"})
        pairs.append({"a": "zz1", "b": "zz2", "cosine": 0.5, "relation": "similar"})        # unsettled: no reference
        return pairs, labels

    def test_half_same_half_different_stratified_and_seeded(self):
        pairs, labels = self.pool()
        sel = RG.select_pilot(pairs, labels, 40, seed=7)
        s = [p for p in sel["selected"] if p["reference"] == "same"]
        d = [p for p in sel["selected"] if p["reference"] == "different"]
        assert len(s) == 20 and len(d) == 20 and sel["pools"] == {
            "same": 30, "different": 60, "unlabelled": 1, "by_bin": sel["pools"]["by_bin"]}
        assert all(labels[p["a"]] == labels[p["b"]] for p in s) and all(labels[p["a"]] != labels[p["b"]] for p in d)
        # proportional to the bins (the different pool: 15 a bin of 60, so 5 a bin of 20)
        from collections import Counter
        assert Counter(RG.bin_label(p["cosine"]) for p in d) == {"0.35-0.45": 5, "0.45-0.55": 5, "0.55-0.65": 5,
                                                                  "0.65+": 5}
        assert RG.select_pilot(pairs, labels, 40, seed=7) == sel                   # the seed decides the draw
        assert RG.select_pilot(pairs, labels, 40, seed=8)["selected"] != sel["selected"]

    def test_a_short_pool_is_taken_whole_and_the_other_fills_the_rest(self):
        pairs, labels = self.pool()
        sel = RG.select_pilot(pairs, labels, 80, seed=1)
        refs = [p["reference"] for p in sel["selected"]]
        assert refs.count("same") == 30 and refs.count("different") == 50
        sel = RG.select_pilot(pairs, labels, 200, seed=1)
        assert len(sel["selected"]) == 90                                          # everything with a reference
        assert RG.select_pilot(pairs, labels, 0)["selected"] == []


class TestPilotRun:
    def test_opus_reads_the_prompt_sonnet_read_and_the_graph_is_untouched(self, tmp_path):
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        g, runner, client = build_plan(tmp_path, plan)
        before = json.dumps(g.to_json(), sort_keys=True)
        pairs = [(p["a"], p["b"]) for p in RG.sonnet2_pairs(g)]
        assert pairs == [(key("chain a"), key("chain c")), (key("irreligious"), key("skeptic")),
                         (key("nonreligious"), key("skeptic"))]
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        recorded = {(r["key"], r["stem"]): r["user"] for r in recs if r["wave"] == "ov1_sonnet"}
        ov = {**OVERLAP, ("irreligious", "skeptic", "opus"): 3}
        pilot, pclient, _ = make_runner(tmp_path, responder_for(RELATIONS, ov), name="pilot")
        pilot.add_candidates(RG.node_candidate(n) for n in g.nodes if n.key in {m for p in pairs for m in p})
        assert RG.pilot_prompt_mismatches(pilot, pairs, recorded) == []
        got = pilot.run_opus(pairs)
        assert all("opus" in kw["model"] for kw in pclient.calls) and len(pclient.calls) == 3
        assert sorted(user_text(kw) for kw in pclient.calls) == sorted(recorded[p] for p in pairs)
        assert got[(key("irreligious"), key("skeptic"))]["opus"]["value"] == 3
        assert got[(key("chain a"), key("chain c"))]["opus"]["value"] == 2
        assert {r["wave"] for r in pilot.records} == {"pilot_opus"}
        assert json.dumps(g.to_json(), sort_keys=True) == before
        # a prompt that no longer renders as Sonnet read it is reported
        bad = dict(recorded)
        bad[pairs[0]] = bad[pairs[0]] + " "
        assert [m["a"] for m in RG.pilot_prompt_mismatches(pilot, pairs, bad)] == [pairs[0][0]]
        assert RG.pilot_prompt_mismatches(pilot, [("x#1", "y#1")], recorded)[0]["why"].startswith("no Sonnet record")


class TestPilotReport:
    def test_the_comparison_with_roger_s_decisions(self):
        rows = ([{"a": f"s{i}", "b": f"t{i}", "cosine": 0.6, "reference": "same", "opus": {"value": v}}
                 for i, v in enumerate([3, 4, 3, 2, 2, 1])] +
                [{"a": f"d{i}", "b": f"e{i}", "cosine": 0.4, "reference": "different", "opus": {"value": v}}
                 for i, v in enumerate([2, 2, 3, 1, "unsure"])] +
                [{"a": "d9", "b": "e9", "cosine": 0.4, "reference": "different", "stalled": "Opus: failed"}])
        g = hand_graph([r1("s0", "t0", 0.7, "similar", (4, 4), (4, 4)), r1("s1", "d1", 0.7, "similar", (3, 3), (3, 3)),
                        r1("s2", "t2", 0.7, "similar", (3, 3), (3, 3))])
        for e in g.edges:
            e.strict = e.readings["ab"]["four"] and e.readings["ba"]["four"]
            e.proposed = True
        labels = {"s0": "x", "t0": "x", "s1": "x", "d1": "y", "s2": "z", "t2": "z"}
        rep = RG.pilot_report(rows, pools={"same": 12, "different": 20}, graph=g, labels=labels)
        s, d = rep["by_reference"]["same"], rep["by_reference"]["different"]
        assert (s["n"], s["answered"], s["raised"], s["four"]) == (6, 6, 3, 1)
        assert (d["n"], d["answered"], d["no_answer"], d["raised"]) == (6, 5, 1, 1)
        assert s["raised_share"] == 0.5 and d["raised_share"] == 0.2
        assert s["opus_values"] == {"1": 1, "2": 2, "3": 2, "4": 1} and d["opus_values"]["unsure"] == 1
        lo, hi = s["ci95"]
        assert lo == pytest.approx(0.1181, abs=1e-3) and hi == pytest.approx(0.8819, abs=1e-3)
        assert rep["gap"] == pytest.approx(0.3) and 0 < rep["fisher_p_one_sided"] < 1
        sp = rep["scaled_to_pools"]
        assert sp["same_raised"] == 6.0 and sp["different_raised"] == 4.0
        assert sp["share_of_raised_that_roger_joined"] == pytest.approx(0.6)
        assert rep["by_bin"]["0.55-0.65"]["same"] == {"n": 6, "answered": 6, "raised": 3}
        assert rep["yardstick"]["four"]["n"] == 1 and rep["yardstick"]["four"]["same"] == 1
        assert rep["yardstick"]["three_only"] == {"n": 2, "same": 1, "same_share": 0.5,
                                                  "ci95": RG.clopper_pearson(1, 2)}
        text = RG.format_pilot_report(rep)
        assert "same      resolution: 3 of 6 answered raised to 3+ = 50%" in text
        assert "yardstick, the build's 4-edges between settled terms: 1 of 1" in text

    def test_raised_is_the_reading_at_the_proposed_cut_off(self):
        assert RG._raised(3) and RG._raised(4) and not RG._raised(2) and not RG._raised("unsure")
        assert RG.clopper_pearson(0, 0) is None and RG.clopper_pearson(0, 10)[0] == 0.0
