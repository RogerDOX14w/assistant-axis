"""Workstream 11 in R1 (coding_plan_11_novelty_ensemble.md § 9 task 7, as Roger decided gate 2 on 2026-10-14, option
(d)): a row's ``lexical`` block becomes ``source: "lexical"`` edges to corpus and queue nodes, with the sweep's
readings, and review flags on the candidate node; **no lexical link ever cuts**, whichever lexicon: a link read at
the row's own cut-off is a *proposed merge* (``lexical_proposed_merge``, shown on the review card as "dictionary
(WordNet | Moby thesaurus): probably the same as X"), the M3 decision stays as it was; below-cut readings are not
flagged (gate 2 (b)).  Stem families become ``via: "stem_family"`` candidate edges typed by their readings, never a
3-edge unread.  A graph whose rows carry no ``lexical`` block is byte-identical to before.  No API call: the fake
client and the toy rows of the R1 tests."""
import copy
import json

import pytest

from assistant_axis.gapgen import lexical_sweep as LS
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.review_app import decisions as D
from assistant_axis.tests import test_gapgen_review_app as APP
from assistant_axis.tests.test_gapgen_novelty import responder_for
from assistant_axis.tests.test_gapgen_review_graph import (BATCH, OVERLAP, QUEUE, RELATIONS, both, build, key,
                                                           make_runner, overlap_calls, toy_rows, toy_vectors)


@pytest.fixture(autouse=True)
def _no_real_operator_table(monkeypatch):
    monkeypatch.setattr(RG, "structural_operator_table", lambda *a, **k: [])


def link(stem, *, lexicon="oewn", ltype="similar", kind="corpus", cos=0.3, s=None, o=None, at=False, verdict=None,
         judged=True, not_judged=None, name_only=False, listed=False):
    x = {"stem": stem, "kind": kind, "link": ltype, "lexicon": lexicon, "cosine": cos, "name_only": name_only,
         "listed_by_m3": listed, "judged": judged, "word": stem}
    if judged:
        x |= {"sonnet": {"value": s, "reason": "s"}, "opus": {"value": o, "reason": "o"} if o is not None else None,
              "verdict": verdict or ("cut" if at else "keep"), "at_cut_off": at}
    else:
        x["not_judged"] = not_judged
    return x


def block(links, *, antonyms=(), family=()):
    ants = [dict(a) for a in antonyms]
    return {"run_id": "lex_t", "lookup_sha256": "f" * 64, "lexicons": {"oewn": "oewn:2024", "moby": "m" * 64},
            "links": list(links), "antonyms": ants, "family": list(family),
            "cut_off_rule": {"c": 3}, "rules": "m3_rules_3", "flags": LS.block_flags(links, ants),
            "n_pairs_judged": sum(1 for x in links if x.get("judged")), "usage": {}, "at": "2026-10-14T10:00:00+00:00"}


#: loner (kept, M3 decided new): an OEWN link read at its cut-off (alpha), a Moby link read at it (delta), a Moby link
#: read under it (epsilon), a name-only queue link (queued), a Moby link under the cosine floor (gamma, not judged), and
#: a link M3 had listed already (beta: no lexical edge, M3's own edge is the record).  Every target but gamma and beta is
#: already a node of the toy graph, so the node list is the same with or without the block.
LONER_LINKS = [link("alpha", s=3, o=3, at=True), link("delta", lexicon="moby", ltype="synonym", s=4, o=4, at=True),
               link("epsilon", lexicon="moby", ltype="synonym", s=1),
               link("queued", kind="queue", judged=False, not_judged="name_only", name_only=True),
               link("gamma", lexicon="moby", ltype="synonym", cos=0.05, judged=False, not_judged="moby_below_floor"),
               link("beta", judged=False, not_judged="listed_by_m3", listed=True)]


def lexical_rows(links=LONER_LINKS, **kw):
    rows = toy_rows()
    rows[key("loner")]["lexical"] = block(links, **kw)
    return rows


class TestLexicalEdges:
    def test_a_lexical_block_becomes_lexical_edges_with_the_sweep_readings_and_costs_no_call(self, tmp_path):
        g, _, client = build(tmp_path, rows=lexical_rows())
        lex = {e.b: e for e in g.edges if e.source == "lexical"}
        assert set(lex) == {"trait:alpha", "trait:delta", "trait:epsilon", "queue:queued"}
        assert all(e.a == key("loner") and not e.strict and not e.proposed for e in lex.values())
        a = lex["trait:alpha"]
        assert a.readings["ab"]["sonnet"] == 3 and a.readings["ab"]["opus"] == 3 and a.via == "oewn:similar"
        assert a.lexical == {"lexicon": "oewn", "link": "similar", "word": "alpha", "judged": True, "at_cut_off": True,
                             "name_only": False, "verdict": "cut", "run_id": "lex_t"}
        assert lex["trait:delta"].lexical["lexicon"] == "moby" and lex["trait:delta"].lexical["at_cut_off"]
        assert not lex["trait:epsilon"].lexical["at_cut_off"] and lex["trait:epsilon"].readings["ab"]["sonnet"] == 1
        q = lex["queue:queued"]
        assert q.readings == {} and q.lexical["name_only"] and not q.lexical["judged"]
        assert g.node_map()["queue:queued"].kind == "queue"
        # no call for any of them: the readings are the sweep's
        assert not any(o in ("alpha", "delta", "epsilon", "queued", "gamma") for _, o, _ in overlap_calls(client))

    def test_flags_proposed_merge_and_name_only_never_below_cut(self, tmp_path):
        g, _, _ = build(tmp_path, rows=lexical_rows())
        flags = g.node_map()[key("loner")].flags
        assert flags == ["lexical_proposed_merge", "lexical_name_only"]
        # below-cut readings are not flagged (gate 2 (b)): a row whose every judged link reads under its cut-off
        g2, _, _ = build(tmp_path, rows=lexical_rows([link("epsilon", lexicon="moby", ltype="synonym", s=2)]),
                         name="below")
        assert g2.node_map()[key("loner")].flags == []
        assert [e.b for e in g2.edges if e.source == "lexical"] == ["trait:epsilon"]

    @pytest.mark.parametrize("lexicon", ["oewn", "moby"])
    def test_no_lexical_link_ever_cuts_whichever_lexicon(self, tmp_path, lexicon):
        """Roger, 2026-10-14, option (d): a link read at the row's own cut-off flags a proposed merge, and the
        candidate stays a kept candidate with its M3 decision; nothing covers it, nothing groups it."""
        rows = lexical_rows([link("alpha", lexicon=lexicon, s=4, o=4, at=True)])
        before = copy.deepcopy(rows[key("loner")]["novelty"])
        g, _, _ = build(tmp_path, rows=rows)
        n = g.node_map()[key("loner")]
        assert n.decision == "new" and n.covered_by is None and key("loner") in g.candidate_keys()
        assert n.flags == ["lexical_proposed_merge"]
        assert key("loner") in g.singletons() and key("loner") in g.ungrouped()
        assert rows[key("loner")]["novelty"] == before
        e = next(e for e in g.edges if e.source == "lexical")
        assert e.lexical["lexicon"] == lexicon and e.lexical["at_cut_off"] and not e.strict and not e.proposed

    def test_stats(self, tmp_path):
        g, _, _ = build(tmp_path, rows=lexical_rows())
        s = g.stats["lexical"]
        assert s["n_edges"] == 4 and s["by_lexicon"] == {"moby": 2, "oewn": 2}
        assert s["judged"] == 3 and s["proposed_merges"] == 2 and s["name_only"] == 1
        assert s["proposed_merges_by_lexicon"] == {"moby": 1, "oewn": 1}
        assert s["candidates_by_flag"] == {"lexical_name_only": 1, "lexical_proposed_merge": 1}
        assert s["candidates_with_proposed_merge"] == 1
        assert RG.lexical_counts_of_rows({key("loner"): lexical_rows()[key("loner")]}) == s

    def test_a_graph_without_lexical_blocks_is_byte_identical(self, tmp_path):
        """The byte-identity check: the same build with the block is the build without it plus the lexical edges,
        the lexical flags and ``stats.lexical``; without any block, nothing lexical appears anywhere."""
        g0, _, _ = build(tmp_path, name="plain")
        j0 = json.dumps(g0.to_json(), sort_keys=True)
        assert "lexical" not in j0 and "stem_family" not in j0
        g1, _, _ = build(tmp_path, rows=lexical_rows(), name="lex")
        j1 = g1.to_json()
        j1["edges"] = [e for e in j1["edges"] if e["source"] != "lexical"]
        for n in j1["nodes"]:
            if "flags" in n:
                n["flags"] = [f for f in n["flags"] if not f.startswith("lexical_")]
                if not n["flags"]:
                    del n["flags"]
        j1["stats"].pop("lexical")
        assert json.dumps(j1, sort_keys=True) == j0
        # and the graph reads back with its lexical fields
        rt = RG.Graph.from_json(json.loads(json.dumps(g1.to_json())))
        assert [e.lexical for e in rt.edges if e.source == "lexical"] == [e.lexical for e in g1.edges
                                                                         if e.source == "lexical"]


class TestStemFamily:
    def rows_with_family(self):
        rows = toy_rows()
        rows[key("chain a")]["lexical"] = block([], family=[{"stem": "chain_c", "kind": "candidate", "via": "affix"},
                                                            {"stem": "alpha", "kind": "corpus", "via": "derivation"}])
        return rows

    def plan(self, rows, stem_family):
        # k=1: chain a's and chain c's nearest is chain b, so the a-c pair (cosine 0.40) is in neither list
        return RG.plan_graph(rows, [BATCH], toy_vectors(), k=1, cosine_floor=0.25, pair_floor=None,
                             stem_family=stem_family)

    def test_off_by_default_and_on_adds_a_stem_family_candidate_edge(self):
        rows = self.rows_with_family()
        off = self.plan(rows, False)
        assert (key("chain a"), key("chain c")) not in off.edges and off.family_pairs == []
        assert "n_family_pairs" not in off.edge_counts()
        on = self.plan(rows, True)
        e = (key("chain a"), key("chain c"))
        assert on.edges[e] == pytest.approx(0.40, abs=0.01) and on.via[e] == "stem_family"
        assert on.family_pairs == [e] and e not in set(map(tuple, on.label_variants))
        assert key("chain c") in dict(on.neighbours[key("chain a")]) and key("chain a") in dict(on.neighbours[key("chain c")])
        assert on.edge_counts()["by_via"]["stem_family"] == 1 and on.edge_counts()["n_family_pairs"] == 1

    def _graph(self, tmp_path, overlap, name):
        plan = self.plan(self.rows_with_family(), True)
        runner, client, idx = make_runner(tmp_path, responder_for(RELATIONS, overlap), name=name)
        return RG.build_graph(plan, runner=runner, corpus=idx.traits, queue=QUEUE, config={}, batch_id="rv")

    def test_a_family_edge_is_typed_by_its_readings_never_a_3_edge_unread(self, tmp_path):
        g = self._graph(tmp_path, OVERLAP, "two")                   # chain a / chain c read 2 both ways
        e = next(e for e in g.edges if e.source == "r1" and (e.a, e.b) == (key("chain a"), key("chain c")))
        assert e.via == "stem_family" and not e.label_variant and not e.proposed and not e.strict
        assert e.relation == "similar" and e.readings["ab"]["sonnet"] == 2
        g3 = self._graph(tmp_path, {**OVERLAP, **both([("chain a", "chain c")], 3)}, "three")
        e3 = next(e for e in g3.edges if e.source == "r1" and (e.a, e.b) == (key("chain a"), key("chain c")))
        assert e3.proposed and not e3.strict and not e3.label_variant          # a 3-edge by its readings
        assert g3.stats["candidate_edges"]["by_via"]["stem_family"] == 1


class TestCard:
    def graph(self):
        g = APP.toy_graph()
        g.edges += [RG.Edge(a=APP.k("loner"), b="trait:beta", cosine=0.21, relation=None, source="lexical",
                            readings={"ab": APP.rd(4, 4)}, via="moby:synonym",
                            lexical={"lexicon": "moby", "link": "synonym", "word": "beta", "judged": True,
                                     "at_cut_off": True, "name_only": False, "verdict": "cut", "run_id": "lex_t"}),
                    RG.Edge(a=APP.k("loner"), b="queue:queued", cosine=None, relation=None, source="lexical",
                            readings={}, via="oewn:synonym",
                            lexical={"lexicon": "oewn", "link": "synonym", "word": "queued", "judged": False,
                                     "at_cut_off": False, "name_only": True, "run_id": "lex_t"})]
        next(n for n in g.nodes if n.key == APP.k("loner")).flags = ["lexical_proposed_merge", "lexical_name_only"]
        g.stats = RG.summarize(g)
        return g

    def test_the_member_card_says_dictionary_probably_the_same_as_and_names_the_lexicon(self):
        st = D.ReviewState(self.graph())
        m = st.member_card(APP.k("loner"))
        assert m["flags"] == ["lexical_proposed_merge", "lexical_name_only"]
        assert m["lexical_merges"] == [{"key": "trait:beta", "kind": "corpus", "label": "beta",
                                        "gloss": "This means being beta.", "path": "data/traits/instructions/beta.json",
                                        "href": "/files/traits/beta.json", "lexicon": "moby", "lexicon_name": "Moby thesaurus",
                                        "link": "synonym", "word": "beta", "at_cut_off": True, "name_only": False,
                                        "reading": "4/4"}]
        assert "lexical_merges" not in st.member_card(APP.k("godless"))     # no block, the card as before

    def test_the_linked_trait_is_among_the_card_s_targets_marked_lexical(self):
        st = D.ReviewState(self.graph())
        corpus = {t["key"]: t for t in st.neighbourhood([APP.k("loner")])["corpus"]}
        assert set(corpus) == {"trait:alpha", "trait:beta", "queue:queued"}
        assert corpus["trait:beta"]["lexical"]["lexicon_name"] == "Moby thesaurus" and corpus["trait:beta"]["level"] == 4
        assert corpus["queue:queued"]["lexical"]["name_only"] and "lexical" not in corpus["trait:alpha"]
        edges = {x["key"]: x for x in st.term_card(APP.k("loner"))["edges"]}
        assert edges["trait:beta"]["lexical"]["lexicon"] == "moby"

    def test_the_page_renders_the_badge(self):
        from pathlib import Path
        js = (Path(D.__file__).parent / "static" / "app.js").read_text(encoding="utf-8")
        assert "probably the same as" in js and "lexical_merges" in js
