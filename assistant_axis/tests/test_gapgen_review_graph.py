"""R1 of the review tooling (coding_plan_review.md, sections 2 and 4): the candidate graph, its 4-edges and maximal
cliques, the edges copied from M3's blocks, the estimate, a stop and its resume, and ``graph.json``.  No API calls:
the fake Anthropic client and the toy corpus of the novelty tests, with the candidates' vectors placed by hand (the
plan takes the projected query vectors, so a cosine here is whatever two vectors below make it)."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage, cost_for_usage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text
from assistant_axis.tests.test_gapgen_novelty import responder_for, rubrics, toy_index

BATCH = "m3b"
DIM = 12


def unit(*axes):
    """A unit vector with ``weight`` on each ``(axis, weight)``."""
    v = np.zeros(DIM)
    for i, w in axes:
        v[i] = w
    return v / np.linalg.norm(v)


#: Candidate label -> vector.  The godless triangle (axis 0); pious and devout (axis 3), 0.4-0.5 from the triangle
#: (antonyms sit close in an embedding space); skeptic, 0.6 from godless; the chain a - b - c (axes 5-7: a-b 0.70,
#: b-c 0.71, a-c 0.40); loner and lowsim at 0.30 (above the retrieval floor, below the overlap floor).  Groups on
#: different axes are at cosine 0, below the retrieval floor: no edge between them.
VECS = {
    "godless": unit((0, 1)),
    "irreligious": unit((0, .9), (1, .436)),
    "nonreligious": unit((0, .9), (2, .436)),
    "skeptic": unit((0, .6), (10, .8)),
    "pious": unit((0, .5), (3, .866)),
    "devout": unit((0, .45), (3, .8), (4, .4)),
    "chain a": unit((5, 1)),
    "chain b": unit((5, .7), (6, .714)),
    "chain c": unit((5, .4), (6, .6), (7, .69)),
    "loner": unit((8, 1)),
    "lowsim": unit((8, .3), (9, .954)),
}
GODLESS = ["godless", "irreligious", "nonreligious"]
PIOUS = ["pious", "devout"]


def key(label: str) -> str:
    return label.replace(" ", "_") + "#1"


def both(pairs, value):
    """``{(x, y): value, (y, x): value}`` for each pair."""
    out = {}
    for x, y in pairs:
        out[(x, y)] = out[(y, x)] = value
    return out


def pairs_of(labels):
    return [(x, y) for i, x in enumerate(labels) for y in labels[i + 1:]]


RELATIONS = {
    **both(pairs_of(GODLESS), "similar"), **both(pairs_of(PIOUS), "similar"),
    **both([(g, p) for g in GODLESS + ["skeptic"] for p in PIOUS], "opposed"),
    **both([("skeptic", g) for g in GODLESS], "similar"),
    **both(pairs_of(["chain a", "chain b", "chain c"]), "similar"),
    **both([("loner", "lowsim")], "similar"),
}
#: Overlap readings by (target, other) or (target, other, model family); anything else reads 1.
OVERLAP = {
    **both(pairs_of(GODLESS), 4), **both(pairs_of(PIOUS), 4),
    ("godless", "skeptic"): 4, ("skeptic", "godless", "sonnet"): 3, ("skeptic", "godless", "opus"): 3,
    ("irreligious", "skeptic"): 2, ("nonreligious", "skeptic"): 2,
    **both([("chain a", "chain b"), ("chain b", "chain c")], 4), **both([("chain a", "chain c")], 2),
    # an opposed pair read 4 would make a clique if it were ever sent: it must not be
    **both([(g, p) for g in GODLESS for p in PIOUS], 4),
}
QUEUE = {"entries": [{"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait",
                      "description": "This means being queued."}]}


def row(label, *, decision="new", batch=BATCH, listed=(), readings=(), covered_by=None, exact=None, deciding=None,
        gen="censuses", align=0, review=()):
    stem = label.replace(" ", "_")
    return {"key": f"{stem}#1", "stem": stem, "label": label, "gloss": f"This means being {label} through and through.",
            "filter": {"verdict": "trait", "alignment": align, "region": "moral_stance"},
            "sources": [{"generator": gen, "run_id": "r1"}],
            "novelty": {"run_id": batch, "decision": decision, "covered_by": covered_by, "exact_label": exact,
                        "deciding_reading": deciding, "review": list(review), "listed": list(listed),
                        "readings": list(readings), "cut_off": NV.cut_off(align), "alignment_score": align,
                        "region": "moral_stance"}}


GODLESS_LISTED = [{"stem": "alpha", "cosine": 0.41, "rank": 1, "via": "retrieved", "relation": "similar"},
                  {"stem": "delta", "cosine": 0.30, "rank": 2, "via": "retrieved", "relation": "opposed"},
                  {"stem": "epsilon", "cosine": 0.20, "rank": None, "via": "expanded", "relation": "unrelated"}]
GODLESS_READINGS = [{"position": 1, "stem": "epsilon", "cosine": 0.20, "relation": "unrelated", "via": "partner",
                     "sonnet": {"value": 0, "reason": "s0"}, "opus": None, "opus_role": None, "outcome": "continue"},
                    {"position": 2, "stem": "alpha", "cosine": 0.41, "relation": "similar", "via": "retrieved",
                     "sonnet": {"value": 2, "reason": "s2"}, "opus": {"value": 2, "reason": "o2"},
                     "opus_role": "below_cut_off", "outcome": "continue"}]


def toy_rows() -> dict:
    rows = [row(lb, gen="roget" if lb in PIOUS else "censuses") for lb in VECS if lb != "godless"]
    rows.append(row("godless", listed=GODLESS_LISTED, readings=GODLESS_READINGS, review=["both_similar"]))
    rows.append(row("atheistic", decision="covered", covered_by="alpha",
                    deciding={"position": 1, "stem": "alpha", "cosine": 0.7, "sonnet": {"value": 4, "reason": "r"},
                              "opus": {"value": 4, "reason": "r"}}))
    rows.append(row("queuedish", decision="covered", covered_by="queued",
                    exact={"covered_by": "queued", "match": "queue", "queue_status": "candidate"}))
    rows.append(row("elsewhere", batch="another_batch"))
    return {r["key"]: r for r in rows}


def toy_vectors() -> dict:
    return {key(lb): v for lb, v in VECS.items()}


def make_runner(tmp_path, responder=None, *, usage=None, records=(), name="out"):
    idx = toy_index(tmp_path)
    client = FakeAsyncAnthropic(responder or responder_for(RELATIONS, OVERLAP))
    r = RG.ReviewRunner(client=client, batch_id="rv", rubrics=rubrics(), index=idx, label_sets=NV.LabelSets(set(), {}, {}),
                        usage=usage if usage is not None else MultiModelUsage(),
                        responses_path=tmp_path / name / "responses.jsonl", config_version="cfg", retry_delays=(),
                        resume_records=records, relation_seed="rv")
    return r, client, idx


def build(tmp_path, responder=None, *, usage=None, records=(), name="out", rows=None, overlap_floor=0.35, gate=None):
    rows = rows if rows is not None else toy_rows()
    plan = RG.plan_graph(rows, [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
    runner, client, idx = make_runner(tmp_path, responder, usage=usage, records=records, name=name)
    g = RG.build_graph(plan, runner=runner, overlap_floor=overlap_floor, corpus=idx.traits, queue=QUEUE,
                       config={"k": 10}, batch_id="rv", gate=gate)
    return g, runner, client


def overlap_calls(client):
    """``(target label, other label, model family)`` of every overlap call sent."""
    out = []
    for kw in client.calls:
        obj = json.loads(user_text(kw))
        if "target" in obj:
            fam = "opus" if "opus" in kw["model"] else "sonnet"
            out.append((obj["target"]["label"], obj["other"]["label"], fam))
    return out


def edge(g, x, y):
    a, b = sorted([key(x), key(y)])
    return next(e for e in g.edges if e.source == "r1" and (e.a, e.b) == (a, b))


# --------------------------------------------------------------------------- selection and the plan

class TestPlan:
    def test_kept_and_covered_rows_of_the_named_batches_and_the_nearest_candidates(self):
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        assert set(plan.cands) == {key(lb) for lb in VECS}                           # "elsewhere" is another batch
        assert set(plan.covered) == {"atheistic#1", "queuedish#1"}
        assert all(c.cut_off == 4 for c in plan.cands.values())                     # cut-off 4 whatever the alignment
        assert plan.neighbours[key("loner")] == [(key("lowsim"), pytest.approx(0.3, abs=1e-3))]
        assert [o for o, _ in plan.neighbours[key("chain a")]] == [key("chain b"), key("chain c")]
        # nearest first; cosines on the vectors' own scale; no edge between groups (cosine 0)
        assert plan.edges[(key("chain a"), key("chain b"))] == pytest.approx(0.7, abs=1e-3)
        assert not any({a, b} & {key("loner")} and {a, b} & {key("godless")} for a, b in plan.edges)
        items = dict(plan.relation_items())
        assert set(items[key("godless")]) == {key(x) for x in ["irreligious", "nonreligious", "skeptic", "pious", "devout"]}

    def test_k_and_the_retrieval_floor(self):
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=1, cosine_floor=0.25)
        assert all(len(v) <= 1 for v in plan.neighbours.values())
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.35)
        assert plan.neighbours[key("loner")] == []

    def test_a_candidate_with_no_vector_is_a_node_without_candidate_edges(self):
        vec = toy_vectors()
        del vec[key("loner")]
        plan = RG.plan_graph(toy_rows(), [BATCH], vec, k=10, cosine_floor=0.25)
        assert plan.no_vector == [key("loner")] and key("loner") in plan.cands
        assert plan.neighbours[key("lowsim")] == []


# --------------------------------------------------------------------------- cliques

class TestMaximalCliques:
    def test_bron_kerbosch_on_a_hand_graph(self):
        k4 = [("a", "b"), ("a", "c"), ("a", "d"), ("b", "c"), ("b", "d"), ("c", "d")]
        assert RG.maximal_cliques(k4 + [("d", "e")]) == [["a", "b", "c", "d"], ["d", "e"]]
        # two triangles sharing an edge stay two overlapping cliques
        assert RG.maximal_cliques([("x", "y"), ("x", "z"), ("y", "z"), ("x", "w"), ("y", "w")]) == \
            [["w", "x", "y"], ["x", "y", "z"]]
        assert RG.maximal_cliques([("p", "q"), ("q", "p"), ("r", "r")]) == [["p", "q"]]
        assert RG.maximal_cliques([]) == []

    def test_every_clique_is_a_simplex_of_four_edges_in_both_directions(self, tmp_path):
        g, _, _ = build(tmp_path)
        assert g.cliques == [sorted(key(x) for x in GODLESS), [key("chain a"), key("chain b")],
                             [key("chain b"), key("chain c")], sorted(key(x) for x in PIOUS)]
        strict = {(e.a, e.b): e for e in g.edges if e.strict}
        for c in g.cliques:
            for i, x in enumerate(c):
                for y in c[i + 1:]:
                    e = strict[tuple(sorted((x, y)))]
                    assert e.readings["ab"]["four"] and e.readings["ba"]["four"] and e.relation != "opposed"
                    assert e.readings["ab"]["sonnet"] == 4 and e.readings["ab"]["opus"] == 4       # Opus confirmed
        assert g.complete and set(g.singletons()) == {key("skeptic"), key("loner"), key("lowsim")}

    def test_a_chain_gives_two_cliques_never_three(self, tmp_path):
        g, _, client = build(tmp_path)
        assert [key("chain a"), key("chain b"), key("chain c")] not in g.cliques
        ac = edge(g, "chain a", "chain c")
        assert ac.relation == "similar" and not ac.strict and ac.overlap == "first"
        assert ac.readings["ab"]["sonnet"] == 2 and "ba" not in ac.readings
        assert ("chain c", "chain a", "sonnet") not in overlap_calls(client)       # no second direction after a 2

    def test_opposed_edges_are_never_read_nor_in_a_clique_and_opposed_cliques_are_linked(self, tmp_path):
        g, _, client = build(tmp_path)
        sent = {(t, o) for t, o, _ in overlap_calls(client)}
        for x in GODLESS + ["skeptic"]:
            for y in PIOUS:
                e = edge(g, x, y)
                assert e.relation == "opposed" and not e.strict and e.readings == {}
                assert (x, y) not in sent and (y, x) not in sent
        gi = g.cliques.index(sorted(key(x) for x in GODLESS))
        pi = g.cliques.index(sorted(key(x) for x in PIOUS))
        link = next(lk for lk in g.clique_links if set(lk["cliques"]) == {gi, pi})
        assert link["relation"] == "opposed" and len(link["edges"]) == 6
        assert not any({gi, g.cliques.index([key("chain a"), key("chain b")])} == set(lk["cliques"])
                       for lk in g.clique_links)


# --------------------------------------------------------------------------- the overlap call's directions and floor

class TestOverlap:
    def test_the_second_direction_is_read_only_after_a_four(self, tmp_path):
        g, _, client = build(tmp_path)
        calls = overlap_calls(client)
        e = edge(g, "godless", "skeptic")                    # godless#1 sorts first: it is the first target
        assert e.overlap == "both" and e.readings["ab"]["four"] and not e.readings["ba"]["four"] and not e.strict
        assert ("skeptic", "godless", "sonnet") in calls and ("skeptic", "godless", "opus") in calls
        e2 = edge(g, "irreligious", "skeptic")
        assert e2.overlap == "first" and e2.readings["ab"]["sonnet"] == 2
        assert ("skeptic", "irreligious", "sonnet") not in calls
        # Opus only on Sonnet's 3s and 4s (the rule at cut-off 4)
        assert ("irreligious", "skeptic", "opus") not in calls
        assert sum(1 for c in calls if c[:2] == ("godless", "irreligious")) == 2      # Sonnet 4, then Opus

    def test_a_similar_pair_below_the_overlap_floor_is_not_read(self, tmp_path):
        g, _, client = build(tmp_path)
        e = edge(g, "loner", "lowsim")
        assert e.relation == "similar" and e.overlap == "below_floor" and e.readings == {}
        assert not any("loner" in c[:2] for c in overlap_calls(client))
        g2, _, client2 = build(tmp_path, name="out2", overlap_floor=0.25)
        assert edge(g2, "loner", "lowsim").overlap == "first"

    def test_the_relation_call_lists_the_other_candidates_with_their_glosses(self, tmp_path):
        g, runner, client = build(tmp_path)
        rel = [kw for kw in client.calls if "candidate" in json.loads(user_text(kw))]
        assert len(rel) == len(VECS) and all(kw["model"] == NR.RELATION_MODEL for kw in rel)
        obj = next(json.loads(user_text(kw)) for kw in rel if json.loads(user_text(kw))["candidate"]["label"] == "chain a")
        assert obj["candidate"]["description"] == "This means being chain a through and through."
        order = NV.relation_order([key("chain b"), key("chain c")], "rv", key("chain a"))
        assert [t["label"] for t in obj["traits"]] == [k[:-2].replace("_", " ") for k in order]
        assert obj["traits"][0]["description"].startswith("This means being chain")
        e = edge(g, "godless", "pious")
        assert e.relations == {"ab": "opposed", "ba": "opposed"}

    def test_unsure_is_asked_again_of_sonnet_and_one_side_similar_is_enough(self, tmp_path):
        base = responder_for(RELATIONS, OVERLAP)

        def resp(kw):
            obj = json.loads(user_text(kw))
            if "candidate" in obj and obj["candidate"]["label"] == "chain a":
                rows = [{"id": t["id"], "reason": "r",
                         "relation": "unsure" if "haiku" in kw["model"] and t["label"] == "chain b" else "unrelated"}
                        for t in obj["traits"]]
                return json.dumps({"results": rows})
            return base(kw)
        g, runner, client = build(tmp_path, resp)
        reask = [kw for kw in client.calls if "sonnet" in kw["model"] and "candidate" in json.loads(user_text(kw))]
        assert len(reask) == 1 and [t["label"] for t in json.loads(user_text(reask[0]))["traits"]] == ["chain b"]
        ab = edge(g, "chain a", "chain b")
        # chain a: Haiku unsure, Sonnet unrelated; chain b: similar -> similar, read, still a 4-edge
        assert ab.relations == {"ab": "unrelated", "ba": "similar"} and ab.relation == "similar" and ab.strict


# --------------------------------------------------------------------------- the edges copied from M3

class TestM3Edges:
    def test_corpus_and_queue_edges_are_copied_from_the_registry_and_cost_no_call(self, tmp_path):
        g, _, client = build(tmp_path)
        corpus_labels = set(STEM_LABELS)
        assert not any(o in corpus_labels for _, o, _ in overlap_calls(client))
        m3 = {e.b: e for e in g.edges if e.source == "m3" and e.a == key("godless")}
        assert set(m3) == {"trait:alpha", "trait:delta", "trait:epsilon"}
        assert m3["trait:alpha"].cosine == 0.41 and m3["trait:alpha"].relation == "similar" and not m3["trait:alpha"].strict
        assert m3["trait:alpha"].readings["ab"]["sonnet"] == 2 and m3["trait:alpha"].readings["ab"]["opus"] == 2
        assert m3["trait:alpha"].readings["ab"]["outcome"] == "continue" and m3["trait:alpha"].rank == 1
        assert m3["trait:delta"].relation == "opposed" and m3["trait:delta"].readings == {}
        assert m3["trait:epsilon"].via == "expanded" and m3["trait:epsilon"].readings["ab"]["sonnet"] == 0
        nodes = g.node_map()
        assert nodes["trait:alpha"].kind == "corpus" and nodes["trait:alpha"].label == "alpha"
        assert nodes["trait:alpha"].gloss == "This means being alpha in every way."
        # the covered candidates: shown greyed, pointing at what covered them; no edge, no call
        at = nodes["atheistic#1"]
        assert at.decision == "covered" and at.covered_by == "trait:alpha" and at.covered_reading["sonnet"] == 4
        assert nodes["queuedish#1"].covered_by == "queue:queued" and nodes["queue:queued"].kind == "queue"
        assert nodes["queue:queued"].label == "queued" and nodes["queue:queued"].status == "candidate"
        assert not any(e.a in ("atheistic#1", "queuedish#1") or e.b in ("atheistic#1", "queuedish#1") for e in g.edges)
        assert "elsewhere#1" not in nodes
        assert nodes[key("godless")].flags == ["both_similar"] and nodes[key("pious")].generator == "roget"
        assert set(g.candidate_keys()) == {key(lb) for lb in VECS}

    def test_stats(self, tmp_path):
        g, runner, _ = build(tmp_path)
        s = g.stats
        assert s["n_candidates"] == len(VECS) and s["n_covered_shown"] == 2
        assert s["cliques"]["by_size"] == {"2": 3, "3": 1} and s["singletons"] == 3
        assert s["candidate_edges"]["by_relation"]["opposed"] == 8
        # 4-edges: the triangle's 3, the chain's 2, pious-devout; godless -> skeptic read 4 one way only
        assert s["overlap"]["four_edges"] == 6 and s["overlap"]["four_first"] == 7
        assert s["overlap"]["similar_below_floor"] == 1
        assert s["agreement_on_fours"]["by_readings"]["sonnet 4, opus 4"] == 13
        assert s["agreement_on_fours"]["by_readings"]["sonnet 3, opus 3"] == 1
        assert set(runner.usage.per_model) == {NR.RELATION_MODEL, NV.SONNET, NV.OPUS}
        assert g.usage == {} or "per_model" in g.usage


STEM_LABELS = ["alpha", "beta", "delta", "epsilon", "eta", "gamma", "iota", "kappa", "lambda mu", "theta", "zeta"]


# --------------------------------------------------------------------------- the estimate

class TestEstimate:
    def test_the_estimate_matches_a_hand_count(self, tmp_path):
        shares = RG.Shares(bins=(0.35, 0.5), similar=(0.5, 1.0), opus=(0.5, 0.5), four=(0.5, 0.5),
                           n_listed=(100, 100), n_read=(100, 100))
        cosines = [0.2, 0.3, 0.36, 0.40, 0.42, 0.49, 0.5, 0.8]
        runner, _, _ = make_runner(tmp_path)
        plan = RG.plan_graph(toy_rows(), [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        runner.add_candidates(plan.cands.values())
        calls = runner.relation_calls(plan.relation_items()[:4])
        est = RG.estimate_build(relation_calls=calls, edge_cosines=cosines, shares=shares, overlap_floor=0.35,
                                overlap_tokens={"sonnet": (200, 80), "opus": (200, 150)}, unsure=(0.5, 2.0),
                                cand_chars=100.0)
        lines = {x.label.split(" (")[0]: x for x in est.lines}
        rel = lines["relation call"]
        assert rel.n_calls == 4 and rel.model == NR.RELATION_MODEL
        assert rel.in_tok == round(sum(NR.call_tokens(c)[0] for c in calls) / 4)
        assert lines["unsure re-ask"].n_calls == 2 and lines["unsure re-ask"].model == NV.SONNET
        # by hand: four pairs in the first bin (similar 0.5), two in the second (similar 1); two below the floor
        assert lines["overlap, first direction, Sonnet"].n_calls == 4          # 4 x 0.5 + 2 x 1
        assert lines["overlap, first direction, Opus"].n_calls == 2            # 2 x 0.5 + 2 x 0.5
        assert lines["overlap, second direction, Sonnet"].n_calls == 2         # 2 x 0.5 + 2 x 0.5
        assert lines["overlap, second direction, Opus"].n_calls == 2           # every second-direction Sonnet
        son, opus = 200 * 2e-6 + 80 * 10e-6, 200 * 4e-6 + 150 * 20e-6          # Sonnet 5.5 $2/$10, Opus 5.5 $4/$20
        assert son == pytest.approx(cost_for_usage(NV.SONNET, 200, 80))
        overlap = sum(x.usd for x in est.lines if x.label.startswith("overlap"))
        assert overlap == pytest.approx(6 * son + 4 * opus)
        batch = RG.estimate_build(relation_calls=calls, edge_cosines=cosines, shares=shares, overlap_floor=0.35,
                                  overlap_tokens={"sonnet": (200, 80), "opus": (200, 150)}, unsure=(0.5, 2.0),
                                  cand_chars=100.0, transport="batches")
        assert batch.usd == pytest.approx(0.5 * est.usd)

    def test_measured_shares_from_the_m3_blocks(self):
        listed = [{"stem": f"s{i}", "cosine": 0.4, "relation": "similar" if i < 15 else "unrelated"} for i in range(20)]
        readings = [{"stem": f"s{i}", "cosine": 0.5, "sonnet": {"value": v}, "opus": {"value": o} if o is not None else None}
                    for i, (v, o) in enumerate([(4, 4), (3, 4), (3, 2), (2, None), ("unsure", 4)] + [(1, None)] * 5)]
        rows = {"x#1": {"key": "x#1", "novelty": {"run_id": BATCH, "decision": "new", "listed": listed, "readings": readings}}}
        sh = RG.measured_shares(rows, [BATCH], bins=(0.35, 0.45, 0.55), min_obs=10)
        assert sh.n_listed == (20, 0, 0) and sh.similar[0] == pytest.approx(0.75)
        assert sh.n_read == (0, 10, 0) and sh.opus[1] == pytest.approx(0.4) and sh.four[1] == pytest.approx(0.3)
        # a bin with fewer than min_obs observations takes 1.0, so the estimate errs high
        assert sh.similar[1] == 1.0 and sh.opus[0] == 1.0 and sh.four[2] == 1.0
        assert sh.at(0.5) == (1.0, pytest.approx(0.4), pytest.approx(0.3)) and sh.at(0.99) == (1.0, 1.0, 1.0)

    def test_measured_overlap_tokens(self):
        recs = [{"step": "overlap", "role": "sonnet", "usage_raw": {"input_tokens": 100, "cache_read_input_tokens": 1000,
                                                                    "output_tokens": 50}},
                {"step": "overlap", "role": "sonnet", "usage_raw": {"input_tokens": 300, "output_tokens": 70}},
                {"step": "relation", "role": "haiku", "usage_raw": {"input_tokens": 9999, "output_tokens": 9999}}]
        t = RG.measured_overlap_tokens(recs)
        assert t["sonnet"] == (250, 60) and t["opus"] == NR.OVERLAP_TOKENS["opus"]


# --------------------------------------------------------------------------- stops and resume

class TestStopAndResume:
    def test_a_failed_request_leaves_the_graph_incomplete_and_a_resume_sends_only_the_unanswered(self, tmp_path):
        good = responder_for(RELATIONS, OVERLAP)

        def failing(kw):
            obj = json.loads(user_text(kw))
            if obj.get("target", {}).get("label") == "chain b":
                return RuntimeError("network down")
            return good(kw)
        g, runner, _ = build(tmp_path, failing)
        assert not g.complete and edge(g, "chain b", "chain c").overlap == "stalled"
        assert edge(g, "chain a", "chain b").overlap == "stalled"           # first read 4, the second failed
        assert [key("chain b"), key("chain c")] not in g.cliques
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        g2, runner2, client2 = build(tmp_path, good, records=recs, name="out")
        sent = overlap_calls(client2)
        assert all(json.loads(user_text(kw)).get("target") for kw in client2.calls)      # no relation call again
        assert {(t, o) for t, o, _ in sent} == {("chain b", "chain c"), ("chain b", "chain a"), ("chain c", "chain b")}
        assert g2.complete and g2.cliques == build(tmp_path, name="fresh")[0].cliques

    def test_a_budget_stop_raises_after_recording_and_a_resume_finishes(self, tmp_path):
        usage = GuardedUsage(budget_usd=0.01)
        with pytest.raises(BudgetExceededError):
            build(tmp_path, usage=usage)
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        assert recs and all(r.get("text") is not None for r in recs)
        g, runner, client = build(tmp_path, records=recs)
        assert client.calls                                                  # the stop came before the end
        answered = {(r["step"], r["model"], r["user"]) for r in recs}
        assert not any((("overlap" if "target" in json.loads(user_text(kw)) else "relation"), kw["model"],
                        user_text(kw)) in answered for kw in client.calls)
        assert g.complete and len(g.cliques) == 4

    def test_the_gate_after_the_relation_calls_can_stop_before_any_overlap_call(self, tmp_path):
        seen = {}

        def gate(pairs):
            seen["pairs"] = pairs
            raise RG.OverlapGateRefused("too dear")
        with pytest.raises(RG.OverlapGateRefused):
            build(tmp_path, gate=gate)
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        assert {r["step"] for r in recs} == {"relation"}
        assert (key("godless"), key("skeptic")) in {(a, b) for a, b, _ in seen["pairs"]}
        assert all(c >= 0.35 for _, _, c in seen["pairs"])


class TestBatches:
    def test_the_same_graph_through_the_message_batches_api(self, tmp_path):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.judge_pricing import BATCH_SUFFIX
        from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
        resp = responder_for(RELATIONS, OVERLAP)
        rows = toy_rows()
        plan = RG.plan_graph(rows, [BATCH], toy_vectors(), k=10, cosine_floor=0.25)
        runner, live, idx = make_runner(tmp_path, resp)
        runner.cache_ttl = NR.BATCH_CACHE_TTL
        bc = FakeBatchClient(resp)
        runner.transport = BatchTransport(runner, bc, tmp_path / "out" / "batches.json", sleep=no_sleep, poll_seconds=0)
        g = RG.build_graph(plan, runner=runner, corpus=idx.traits, queue=QUEUE, batch_id="rv")
        assert live.calls == [] and g.cliques == build(tmp_path, name="live")[0].cliques
        waves = list(json.loads((tmp_path / "out" / "batches.json").read_text())["waves"])
        assert waves == ["r1_relation", "ov1_sonnet", "ov1_opus", "ov2_sonnet", "ov2_opus"]
        assert all(m.endswith(BATCH_SUFFIX) for m in runner.usage.per_model)


# --------------------------------------------------------------------------- graph.json

class TestGraphJson:
    def test_round_trip_plain_and_in_its_envelope(self, tmp_path):
        g, _, _ = build(tmp_path)
        d = json.loads(json.dumps(g.to_json()))
        g2 = RG.Graph.from_json(d)
        assert g2.to_json() == g.to_json() and g2.cliques == g.cliques and g2.singletons() == g.singletons()
        env = RG.graph_envelope(g, inputs=None, title="t")
        assert set(env) == {"result", "_provenance"}
        assert RG.Graph.from_json(json.loads(json.dumps(env))).to_json() == g.to_json()
        assert d["batch_id"] == "rv" and d["schema"] == RG.GRAPH_SCHEMA
        assert d["nodes"][0]["kind"] == "candidate" and "covered_by" not in d["nodes"][0]    # empty fields left out

    def test_a_reading_under_the_rule_at_cut_off_4(self):
        r = lambda s, o=None: {"sonnet": {"value": s, "reason": "x"}, "opus": {"value": o, "reason": "y"} if o is not None else None}
        assert RG.reading_of(r(4, 4))["four"] and RG.reading_of(r(3, 4))["four"] and RG.reading_of(r("unsure", 4))["four"]
        assert not RG.reading_of(r(4, 3))["four"] and not RG.reading_of(r(3, 3))["four"]
        assert not RG.reading_of(r(2))["four"] and not RG.reading_of({"sonnet": {"value": None, "error": "e"}, "opus": None})["four"]
        assert RG.reading_of({"stalled": "Sonnet on x: failed", "phase": "sonnet"}) == {"stalled": "Sonnet on x: failed"}
        assert RG.reading_of(r(3, 4))["reasons"] == {"sonnet": "x", "opus": "y"}

    def test_relations_combined(self):
        c = RG.combine_relations
        assert c("similar", "similar") == "similar" and c("similar", "unrelated") == "similar"
        assert c("opposed", None) == "opposed" and c("opposed", "similar") == "mixed"
        assert c("unsure", "unrelated") == "unsure" and c("unparsed", None) == "unsure"
        assert c(None, None) == "unknown" and c("unrelated", "unrelated") == "unrelated"
