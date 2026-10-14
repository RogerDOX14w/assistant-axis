"""Plan 13 task 3: repetition (pre-handled terms) and concept units (``repetition.py``, ``concepts.py``): a toy graph
and a toy review log, then the recorded all-batches graph (the hard figures of plan 13 § 8 and decision 2's
table).  No API calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import records as RF
from assistant_axis.gapgen.testing import concepts as C
from assistant_axis.gapgen.testing import repetition as RP

REPO = Path(__file__).resolve().parents[2]
GRAPH = REPO / "data" / "candidates" / "review" / "review_traits_all_2" / "graph.json"
REVIEW = REPO / "data" / "candidates" / "review"


def node(key, gen="censuses", run="m3a", status=None, into=None, decision="new", region="moral_stance"):
    return {"key": key, "kind": "candidate", "label": key.split("#")[0], "generator": gen, "generators": [gen],
            "decision": decision, "region": region, "m3_run": run, "review_status": status, "review_into": into,
            "review_batch": "rev1" if status else None}


def edge(a, b, level):
    return {"a": a, "b": b, "cosine": 0.5, "source": "r1", "strict": level == 4, "proposed": level >= 3}


def toy_graph():
    """Decided in batch m3a: a (accepted), b (merged into a).  Undecided: c (3-edge to a), d (4-edge to b), e (no
    edge to a decided term, 3-edge to c), f (ipip, 3-edge to b), g (base model and censuses), h (covered)."""
    nodes = [node("a#1", status="accepted"), node("b#1", status="merged_into", into="a#1"), node("c#1", run="m3b"),
             node("d#1", run="m3b"), node("e#1", run="m3b"), node("f#1", gen="ipip", run="m3c"),
             dict(node("g#1", run="m3c"), generators=["censuses", "base_model"]), node("h#1", decision="covered")]
    edges = [edge("a#1", "b#1", 4), edge("a#1", "c#1", 3), edge("b#1", "d#1", 4), edge("c#1", "e#1", 3),
             edge("b#1", "f#1", 3), edge("e#1", "g#1", 1), edge("a#1", "h#1", 4)]
    return {"batch_id": "toy", "nodes": nodes, "edges": edges}


class TestRepetition:
    def test_pre_handled_by_level_and_attachment(self):
        g = toy_graph()
        assert set(RP.kept_nodes(g)) == {"a#1", "b#1", "c#1", "d#1", "e#1", "f#1", "g#1"}     # h is covered
        assert RP.decided_keys(g) == {"a#1": "accepted", "b#1": "merged_into"}
        r3 = RP.repetition(g, level=3, min_batch_decided=1)
        r4 = RP.repetition(g, level=4, min_batch_decided=1)
        c3, c4 = r3["censuses"], r4["censuses"]
        assert (c3.n_kept, c3.n_decided, c3.n_undecided) == (6, 2, 4)
        assert c3.pre_handled == 2 and c3.share == 0.5            # c (3-edge to a), d (4-edge to b)
        assert c4.pre_handled == 1                                # d only
        assert r3["ipip"].pre_handled == 1 and r4["ipip"].pre_handled == 0
        # attachment to batch m3a: censuses' undecided terms outside it (c d e g), with a 3-edge into it: c, d
        assert c3.attached_to_batch == {"m3a": {"n": 4, "attached": 2, "share": 0.5}}
        assert c3.with_another_generator == 1                     # g
        rows = {"c#1": {"review": {"status": "accepted"}}}        # the registry is the later record
        assert RP.decided_keys(g, rows)["c#1"] == "accepted"
        recs = RP.repetition_records(g, rows=None)
        assert {(r["generator"], r["level"]) for r in recs} >= {("censuses", 3), ("censuses", 4), ("ipip", 3)}
        assert "| censuses |" in RP.repetition_markdown(recs)


class TestUnits:
    def test_components(self):
        g = toy_graph()
        c4 = C.components(g, level=4)
        assert sorted(sorted(u) for u in c4) == [["a#1", "b#1", "d#1"], ["c#1"], ["e#1"], ["f#1"], ["g#1"]]
        c3 = C.components(g, level=3)
        assert sorted(sorted(u) for u in c3) == [["a#1", "b#1", "c#1", "d#1", "e#1", "f#1"], ["g#1"]]

    def chain(self, n=5):
        keys = [f"k{i}#1" for i in range(n)]
        return {"nodes": [node(k) for k in keys], "edges": [edge(keys[i], keys[i + 1], 3) for i in range(n - 1)]}, keys

    def test_a_chain_never_joins_its_ends(self):
        g, keys = self.chain()
        for tau in (0.5, 0.67, 0.8):
            units = C.grow(g, seeds=C.components(g, level=4), tau=tau)
            of = {x: i for i, u in enumerate(units) for x in u}
            assert of[keys[0]] != of[keys[-1]], tau
        units = C.grow(g, seeds=C.components(g, level=4), tau=0.67)
        assert max(len(u) for u in units) <= 2                    # a pair is dense (1 of 1), a triple of a chain not

    def test_two_triangles_sharing_an_edge_merge(self):
        ks = ["p#1", "q#1", "r#1", "s#1"]
        g = {"nodes": [node(k) for k in ks],
             "edges": [edge("p#1", "q#1", 3), edge("q#1", "r#1", 3), edge("p#1", "r#1", 3),
                       edge("q#1", "s#1", 3), edge("r#1", "s#1", 3)]}     # 5 of the 6 pairs: density 0.83
        assert [sorted(u) for u in C.grow(g, seeds=C.components(g, level=4), tau=0.67)] == [ks]
        assert len(C.grow(g, seeds=C.components(g, level=4), tau=0.9)) > 1

    def test_grow_is_deterministic_and_keeps_the_seeds_whole(self):
        g = toy_graph()
        seeds = C.components(g, level=4)
        a = C.grow(g, seeds=seeds, tau=0.67)
        assert a == C.grow(g, seeds=list(reversed(seeds)), tau=0.67)
        for s in seeds:
            assert any(s <= u for u in a)


def write_log(d, events):
    d.mkdir(parents=True, exist_ok=True)
    (d / "decisions.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    return d


def ev(seq, action, group="g1", **kw):
    return {"seq": seq, "at": f"2026-10-11T10:00:{seq:02d}+00:00", "by": "roger", "group": group, "action": action,
            **kw}


class TestAgreement:
    def test_hand_computed_shares(self, tmp_path):
        """Decided: a (accepted), b and c merged into a, d accepted: concepts {a b c} and {d}; same-concept pairs
        ab ac bc.  Units {a b} {c d}: kept together 1 of 3; decided pairs sharing a unit: ab (one concept), cd
        (not): one concept 1 of 2.  Hard negatives: e marked distinct from group g1 (a b c), and c dropped from a
        proposed group with d: (e,a) (e,b) (e,c) (c,d); units put c and d together: 1 joined."""
        nodes = [node("a#1", status="accepted"), node("b#1", status="merged_into", into="a#1"),
                 node("c#1", status="merged_into", into="b#1"), node("d#1", status="accepted"), node("e#1")]
        g = {"nodes": nodes, "edges": []}
        d = write_log(tmp_path / "rev1", [
            ev(1, "open", members=["a#1", "b#1", "c#1"]), ev(2, "resolve", members=["a#1", "b#1", "c#1"],
                                                               resolution="promote"),
            ev(3, "distinct", keys=["e#1"]), ev(4, "open", group="g2", members=["c#1", "d#1"]),
            ev(5, "drop", group="g2", key="c#1"), ev(6, "drop", group="g2", key="d#1"),
            ev(7, "undo", group="g2", undoes=6)])
        units = [{"a#1", "b#1"}, {"c#1", "d#1"}, {"e#1"}]
        ag = C.review_agreement(units, [d], g)
        assert ag.n_decided == 4 and ag.n_concepts == 2 and ag.n_pairs == 3
        assert ag.kept_together == pytest.approx(1 / 3, abs=1e-4) and ag.one_concept == 0.5
        assert ag.n_negatives == 4 and ag.hard_negatives_joined == 1
        assert C.final_concept("c#1", {n["key"]: n for n in nodes}) == "a#1"     # followed transitively

    def test_concept_table(self):
        g = toy_graph()
        t = C.concept_table(g, unit="components_4")
        assert t.n_concepts == 5 and t.largest == 3 and t.n_singletons == 4
        assert t.by_mechanism == {"base_model": 1, "ipip": 1, "lexicon": 4}         # abd, c, e, g
        assert {(p["a"], p["b"]): p["m"] for p in t.pairs} == {("lexicon", "ipip"): 0, ("lexicon", "base_model"): 1,
                                                                ("ipip", "base_model"): 0}
        assert t.incidence["1"] == 4 and t.incidence["2"] == 1
        big = t.concepts[0]
        assert big["keys"] == ["a#1", "b#1", "d#1"] and big["decided"] in ("accepted", "merged_into")


#: The recorded graph these figures belong to (sha256 of its content, packed or plain).  Re-pinned 2026-10-14 after
#: the day's review-graph resume (GG5's alignment rows imported, IPIP's hinted names added); the plan 13 build's
#: figures of 2026-10-13 are kept in each docstring.  A rebuilt graph skips the class with this message instead of
#: failing: recompute the figures and re-pin both (Roger, 2026-10-14).
GRAPH_SHA256 = "df084064389846123be625f1d809651597915888a1153a0215009e6d6b164c80"


def _graph_sha() -> str:
    import hashlib
    return hashlib.sha256(RF.read_bytes(GRAPH)).hexdigest() if RF.exists(GRAPH) else ""


@pytest.mark.skipif(not RF.exists(GRAPH), reason="the recorded review graph is absent")
@pytest.mark.skipif(RF.exists(GRAPH) and _graph_sha() != GRAPH_SHA256,
                    reason="the review graph was rebuilt since these figures were pinned: recompute them and re-pin "
                           "GRAPH_SHA256 (assistant_axis/tests/test_gapgen_testing_concepts.py)")
class TestRecorded:
    @pytest.fixture(scope="class")
    def graph(self):
        return RP.load_graph(GRAPH)

    def test_repetition_hard_figures(self, graph):
        """Plan 13 § 8: censuses 185 of 2,698 at level 3, 57 at level 4; 717 of 2,076 non-TDA censuses terms
        attached to the TDA batch (720, share 0.3468, on 2026-10-13)."""
        r3 = RP.repetition(graph, level=3, generators=["censuses"])["censuses"]
        r4 = RP.repetition(graph, level=4, generators=["censuses"])["censuses"]
        assert (r3.n_kept, r3.n_decided, r3.n_undecided, r3.pre_handled) == (2872, 174, 2698, 185)
        assert r4.pre_handled == 57
        assert r3.attached_to_batch["2026-10-10-tda_censuses_r3"] == {"n": 2076, "attached": 717, "share": 0.3454}

    def test_unit_hard_figures(self, graph):
        """3,373 four-edge components, 2,944 singletons, largest 25; a 3-edge component of 1,138; grown_3 at 0.67
        2,477 units, largest 27 (2026-10-13: 3,065, 2,691, 21; 1,028; about 2,250 and at most 28)."""
        cache = {}
        c4 = C.build_units(graph, "components_4", cache=cache)
        assert len(c4) == 3373 and sum(1 for u in c4 if len(u) == 1) == 2944 and max(map(len, c4)) == 25
        c3 = C.build_units(graph, "components_3", cache=cache)
        assert max(map(len, c3)) == 1138
        g3 = C.build_units(graph, "grown_3", tau=0.67, cache=cache)
        assert len(g3) == 2477 and max(map(len, g3)) <= 28

    def test_decision_2_agreement(self, graph):
        """Decision 2's table, rebuilt from every review log: kept together 39% and 53%, one concept 76% and 77%,
        hard negatives joined 19 and 27 of 147 (2026-10-13: 54%, 75%, 29)."""
        dirs = sorted(p.parent for p in REVIEW.glob("*/decisions.jsonl"))
        cache = {}
        a4 = C.review_agreement(C.build_units(graph, "components_4", cache=cache), dirs, graph)
        g3 = C.review_agreement(C.build_units(graph, "grown_3", tau=0.67, cache=cache), dirs, graph)
        assert a4.n_negatives == g3.n_negatives == 147 and a4.n_pairs == 328 and a4.n_concepts == 58
        assert round(100 * a4.kept_together) == 39 and round(100 * a4.one_concept) == 76
        assert round(100 * g3.kept_together) == 53 and g3.one_concept == pytest.approx(0.774, abs=0.01)
        assert (a4.hard_negatives_joined, g3.hard_negatives_joined) == (19, 27)

    def test_mechanism_overlaps(self, graph):
        """Plan 13 § "Baseline": lexicon 2,402, base_model 436, alignment 543, ipip 359 concepts at 4-edges; m 69
        (lexicon x ipip), 380 (lexicon x base model), 39 (ipip x base model); four occasions Q1 2,798, Q2 382, Q3+ 57
        (2026-10-13: 437, 319, 232; 54, 379, 32; 2,513, 375, 41)."""
        t = C.concept_table(graph, unit="components_4",
                            occasions=("lexicon", "ipip", "base_model", "alignment"))
        assert {k: t.by_mechanism[k] for k in ("lexicon", "base_model", "alignment", "ipip")} == \
            {"lexicon": 2402, "base_model": 436, "alignment": 543, "ipip": 359}
        m = {(p["a"], p["b"]): p["m"] for p in t.pairs}
        assert (m[("lexicon", "ipip")], m[("lexicon", "base_model")], m[("ipip", "base_model")]) == (69, 380, 39)
        assert (t.incidence["1"], t.incidence["2"], t.incidence["3+"]) == (2798, 382, 57)
