"""M3, the novelty check (coding_plan_m3.md): the exact-label check, retrieval and expansion, the relation
call, the shortlist and the pair check, the overlap walk under every branch of the rule, the decision and
the block, the review order and the rename shortlist, the waves (live and through the Message Batches
API) and the estimate.  No API calls: fake clients, a toy corpus written to a temporary data dir (the
overlap test's stems and descriptions)."""
import asyncio
import json
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import overlap_test as OT
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text

REPO = Path(__file__).resolve().parents[2]
#: The pilot's decision rules (decisions 1-11) and round 2's (decisions 12-15 and the floor; the default from
#: 2026-10-07).  The tests written for the pilot's rules are pinned to R1 with their expectations unchanged;
#: round 2's tests are further down (TestRound2*).
R1, R2 = NV.RULES[1], NV.RULES[2]

# --------------------------------------------------------------------------- the toy corpus
#
# The overlap test's eleven stems.  Arrangements: two clean pairs (delta / epsilon, theta / iota), a triangle
# (alpha, beta, gamma), a sequence (zeta, eta, kappa) and a non-X singleton (lambda_mu).  Each trait has its
# own axis in a 12-d space (a twelfth axis is free for queries), so a cosine is whatever a query puts on it.

STEMS = ["alpha", "beta", "delta", "epsilon", "eta", "gamma", "iota", "kappa", "lambda_mu", "theta", "zeta"]
PAIRS = {"delta": "epsilon", "epsilon": "delta", "theta": "iota", "iota": "theta"}
TRIANGLE = ["alpha", "beta", "gamma"]
SEQUENCE = ["zeta", "eta", "kappa"]
DIM = 12


def write_corpus(data_dir: Path, *, renamed: dict | None = None) -> Path:
    d = data_dir / "traits" / "instructions"
    d.mkdir(parents=True, exist_ok=True)
    for s in STEMS:
        doc = {"positive_label": s.replace("_", " "), "description": f"This means being {s.replace('_', ' ')} in every way.",
               "negative_label": PAIRS[s].replace("_", " ") if s in PAIRS else f"non-{s}"}
        if s in PAIRS:
            doc["arrangement"] = {"kind": "pair", "members": sorted([s, PAIRS[s]])}
        elif s in TRIANGLE:
            doc["arrangement"] = {"kind": "triangle", "members": sorted(TRIANGLE)}
        elif s in SEQUENCE:
            doc["arrangement"] = {"kind": "sequence", "members": SEQUENCE}
        else:
            doc["arrangement"] = {"kind": "singleton"}
        if renamed and s in renamed:
            doc["renamed_from"] = {"stem": renamed[s], "date": "2026-10-01", "reason": "test"}
        (d / f"{s}.json").write_text(json.dumps(doc), encoding="utf-8")
    return data_dir


def toy_index(tmp_path, **kw) -> NV.CorpusIndex:
    traits = NV.load_trait_corpus(write_corpus(tmp_path / "data", **kw))
    E = np.zeros((len(STEMS), DIM))
    for i in range(len(STEMS)):
        E[i, i] = 1.0
    return NV.build_index(traits, E, variant="raw", settings={"k": 4})


def query(**weights) -> np.ndarray:
    """A raw query vector putting ``weights[stem]`` on each named trait's axis, the rest on the free axis."""
    v = np.zeros(DIM)
    for s, w in weights.items():
        v[sorted(STEMS).index(s)] = w
    v[-1] = 0.2
    return v


# --------------------------------------------------------------------------- the corpus and stage 0

class TestCorpus:
    def test_partners_expansion_and_pair_partner(self, tmp_path):
        t = NV.load_trait_corpus(write_corpus(tmp_path / "data"))
        assert t["delta"].pair_partner == "epsilon" and t["delta"].partners == ["epsilon"]
        assert t["delta"].expands_to == ["epsilon"]
        assert t["alpha"].pair_partner is None and t["alpha"].partners == ["beta", "gamma"]   # triangle corners
        assert t["alpha"].expands_to == ["beta", "gamma"]
        assert t["zeta"].partners == [] and t["zeta"].expands_to == []                         # a sequence: nothing
        assert t["lambda_mu"].partners == [] and t["lambda_mu"].label == "lambda mu"

    def test_cut_off(self):
        assert [NV.cut_off(a) for a in (0, 1, 2, 3)] == [3, 3, 4, 4]
        assert NV.cut_off(None) == 4 and NV.cut_off(True) == 4      # no score: the cut-off that cuts less


class TestExactLabel:
    def sets(self, tmp_path):
        t = NV.load_trait_corpus(write_corpus(tmp_path / "data", renamed={"gamma": "old_gamma"}))
        queue = {"entries": [{"stem": "queued_one", "label": "Queued-One", "status": "candidate", "entity_type": "trait"},
                             {"stem": "turned_down", "label": "turned down", "status": "not_adopted", "entity_type": "trait"},
                             {"stem": "beta", "label": "beta", "status": "exists", "entity_type": "trait"},
                             {"stem": "other", "label": "other label", "status": "tbd", "entity_type": "role"}]}
        return NV.label_sets(t, queue)

    def test_corpus_queue_and_renamed(self, tmp_path):
        s = self.sets(tmp_path)
        assert NV.exact_label_match("alpha", s, rules=R1) == {"covered_by": "alpha", "match": "corpus"}
        assert NV.exact_label_match("beta", s, rules=R1)["match"] == "corpus"       # the corpus is checked first
        q = NV.exact_label_match("queued_one", s, rules=R1)
        assert q["covered_by"] == "queued_one" and q["match"] == "queue" and q["queue_status"] == "candidate"
        assert NV.exact_label_match("turned_down", s, rules=R1)["queue_status"] == "not_adopted"   # any status
        assert NV.exact_label_match("other_label", s, rules=R1)["covered_by"] == "other"  # a normalised queue label
        r = NV.exact_label_match("old_gamma", s, rules=R1)
        assert r == {"covered_by": "gamma", "match": "renamed_from", "old_stem": "old_gamma"}
        assert NV.exact_label_match("brand_new", s, rules=R1) is None


# --------------------------------------------------------------------------- stages 1-2

class TestRetrievalAndExpansion:
    def test_a_pair_member_brings_its_partner_a_triangle_its_corners_a_sequence_nothing(self, tmp_path):
        idx = toy_index(tmp_path)
        q = idx.project(query(delta=0.9, alpha=0.8, zeta=0.7, kappa=0.1, epsilon=0.05, beta=0.02))
        ret = idx.retrieve(q, 3)
        assert [s for s, _ in ret] == ["delta", "alpha", "zeta"]
        listed = NV.expand(ret, idx.traits, lambda s: idx.cosine_to(q, s))
        by = {x.stem: x for x in listed}
        assert [x.stem for x in listed[:3]] == ["delta", "alpha", "zeta"] and all(x.via == "retrieved" for x in listed[:3])
        assert set(by) == {"delta", "alpha", "zeta", "epsilon", "beta", "gamma"}              # no eta, no kappa
        assert by["epsilon"].via == "expanded" and by["epsilon"].expanded_from == ["delta"] and by["epsilon"].rank is None
        assert by["beta"].expanded_from == ["alpha"] and by["gamma"].expanded_from == ["alpha"]
        for s in ("epsilon", "beta", "gamma"):                                                 # each its own cosine
            assert by[s].cosine == pytest.approx(idx.cosine_to(q, s), abs=1e-6)
        assert by["beta"].cosine > by["gamma"].cosine                                          # added by cosine
        assert by["delta"].partners == ["epsilon"] and by["delta"].pair_partner == "epsilon"
        assert by["alpha"].partners == ["beta", "gamma"] and by["alpha"].pair_partner is None

    def test_both_sides_retrieved_are_listed_once(self, tmp_path):
        idx = toy_index(tmp_path)
        q = idx.project(query(delta=0.9, epsilon=0.8))
        listed = NV.expand(idx.retrieve(q, 2), idx.traits, lambda s: idx.cosine_to(q, s))
        assert [x.stem for x in listed] == ["delta", "epsilon"] and all(x.via == "retrieved" for x in listed)

    def test_query_text_forms(self):
        from assistant_axis.gapgen.retrieval import query_text as m2_query
        gloss = "This means treating every task as a lever on how the world goes, near and far, today and later."
        lg = NV.query_text("world-shaping", gloss, query_form="label_gloss")
        assert lg.startswith("world-shaping: This means")
        # the default is metric_config.json's form, the one M2 measured recall on (2026-10-07)
        assert NV.DEFAULT_QUERY_FORM == "gloss_w14"
        g = NV.query_text("x", gloss)
        assert g == m2_query(gloss) and not g.startswith("x:") and len(g.split()) <= 15
        with pytest.raises(ValueError):
            NV.query_text("x", "y", query_form="nope")


# --------------------------------------------------------------------------- stage 3

def L(stem, cos, *, partners=(), pair=None, via="retrieved", rank=1, simplexes=()):
    return NV.Listed(stem=stem, cosine=cos, rank=rank, via=via, partners=list(partners), pair_partner=pair,
                     simplexes=[dict(s) for s in simplexes])


class TestRelationCall:
    def test_render_layout_and_order(self):
        u = NV.render_relation_user("world-shaping", "This means x.", [("alpha", "A."), ("beta", "B.")])
        lines = u.split("\n")
        assert lines[0] == '{"candidate": {"label": "world-shaping", "description": "This means x."},'
        assert lines[1] == ' "traits": [' and lines[-1] == " ]}"
        assert json.loads(u)["traits"][1] == {"id": 2, "label": "beta", "description": "B."}
        a = NV.relation_order(["x", "y", "z", "w"], "run1", "k#1")
        assert a == NV.relation_order(["w", "z", "y", "x"], "run1", "k#1")             # seeded, input order ignored
        assert sorted(a) == ["w", "x", "y", "z"]
        orders = {tuple(NV.relation_order(list("abcdefgh"), "run1", f"k{i}#1")) for i in range(6)}
        assert len(orders) > 1                                                           # differs by candidate

    def test_relation_rubric_is_pinned_and_parsed_as_the_list_form(self):
        text = sr.load_prompt("relation")
        assert sr.current_versions(names=sr.M3_NAMES)["relation"] == (1, sr.sha256(text))
        assert text.index('"reason"') < text.index('"relation"')                         # reason before the answer
        good = json.dumps({"results": [{"id": 1, "reason": "a", "relation": "similar"},
                                       {"id": 2, "label": "x", "reason": "b", "relation": "Opposed"}]})
        rows, errors, meta = NV.parse_relation("```json\n" + good + "\n```", 2)
        assert errors == {} and rows[1]["value"] == "similar" and rows[2]["value"] == "opposed"
        assert meta["extra_keys"] == ["label"] and meta["n_rows_extra_keys"] == 1
        bad = json.dumps({"results": [{"id": 1, "reason": "a", "relation": "close"}]})
        rows, errors, _ = NV.parse_relation(bad, 2)
        assert rows == {} and set(errors) == {1, 2} and errors[2] == "missing"
        # a self-correction: the last complete results object is the answer
        two = good.replace("Opposed", "similar") + "\nCorrection:\n" + good
        rows, errors, meta = NV.parse_relation(two, 2)
        assert errors == {} and rows[2]["value"] == "opposed" and meta["n_result_objects"] == 2

    def test_parse_answer_of_the_overlap_test_is_unchanged(self):
        """The list form's parser moved into parse_list (2026-10-07); rubric A's list answers parse as before
        and carry no extra-keys note."""
        t = json.dumps({"results": [{"id": 1, "label": "x", "reason": "r", "similarity": 3}]})
        rows, errors, meta = OT.parse_answer(t, "A", 1)
        assert rows[1]["value"] == 3 and errors == {} and "extra_keys" not in meta


class TestShortlist:
    def listed(self):
        return [L("alpha", 0.9, partners=["beta", "gamma"]), L("delta", 0.8, partners=["epsilon"], pair="epsilon"),
                L("zeta", 0.7), L("theta", 0.6, partners=["iota"], pair="iota"), L("beta", 0.5, partners=["alpha", "gamma"]),
                L("epsilon", 0.4, partners=["delta"], pair="delta", via="expanded", rank=None),
                L("iota", 0.3, partners=["theta"], pair="theta", via="expanded", rank=None),
                L("gamma", 0.2, partners=["alpha", "beta"], via="expanded", rank=None), L("lambda_mu", 0.1)]

    def test_order_partners_first_then_similar_by_cosine(self):
        rel = {"alpha": "similar", "delta": "opposed", "zeta": "similar", "theta": "unrelated", "beta": "similar",
               "epsilon": "unrelated", "iota": "similar", "gamma": "unrelated", "lambda_mu": "opposed"}
        sl = NV.build_shortlist(self.listed(), rel)
        # delta opposed: its partner epsilon goes to the front although the call did not mark it similar
        assert sl.front == ["epsilon"]
        assert sl.queue == ["epsilon", "alpha", "zeta", "beta", "iota"]
        # lambda_mu opposed with no partner: a pair completion, never in the queue
        assert sl.pair_completion_for == ["lambda_mu"] and "lambda_mu" not in sl.queue
        assert sl.pair_flags == []

    def test_an_opposed_corner_brings_the_other_corners_forward(self):
        rel = {x.stem: "unrelated" for x in self.listed()} | {"alpha": "opposed", "zeta": "similar"}
        sl = NV.build_shortlist(self.listed(), rel)
        assert sl.queue == ["beta", "gamma", "zeta"] and sl.pair_completion_for == []

    def test_pair_check(self):
        base = {x.stem: "unrelated" for x in self.listed()}
        expected = NV.build_shortlist(self.listed(), base | {"delta": "similar", "epsilon": "opposed"})
        assert expected.pair_flags == []                                   # one side similar, the other opposed
        both_sim = NV.build_shortlist(self.listed(), base | {"delta": "similar", "epsilon": "similar"})
        assert both_sim.pair_flags == [{"pair": ["delta", "epsilon"], "both": "similar"}]
        both_opp = NV.build_shortlist(self.listed(), base | {"theta": "opposed", "iota": "opposed"})
        assert both_opp.pair_flags == [{"pair": ["iota", "theta"], "both": "opposed"}]
        assert both_opp.front == ["theta", "iota"]                          # each is the other's partner
        # a triangle is not a pair: two corners both similar raise no flag
        tri = NV.build_shortlist(self.listed(), base | {"alpha": "similar", "beta": "similar"})
        assert tri.pair_flags == []

    def test_a_trait_still_unsure_is_shortlisted_but_left_out_of_the_pair_check(self):
        base = {x.stem: "unrelated" for x in self.listed()}
        sl = NV.build_shortlist(self.listed(), base | {"delta": "similar", "epsilon": "unsure", "zeta": "similar"})
        assert sl.queue == ["delta", "zeta", "epsilon"] and sl.pair_flags == []

    def test_the_fallback_shortlists_every_listed_trait_without_a_pair_check(self):
        sl = NV.build_shortlist(self.listed(), {}, fallback=True, rules=R1)
        assert sl.queue == [x.stem for x in self.listed()]                   # already in cosine order
        assert sl.pair_flags == [] and sl.pair_completion_for == [] and sl.front == []


# --------------------------------------------------------------------------- stage 4: the walk

def walk(c, queue, *, partners=None, review=(), rules=R1, exclude=()):
    """A walk under the pilot's rules unless ``rules`` says otherwise (the rule-table tests below were written
    for them)."""
    info = {s: L(s, 1.0 - i * 0.1) for i, s in enumerate(queue)}
    return NV.Walk("cand#1", c, queue, info, partners=partners or {}, review=review, rules=rules, exclude=exclude)


def step(w, sonnet, opus="NONE"):
    s = w.next_pair()
    need = w.give_sonnet(sonnet, "s-reason") if sonnet is not None else w.give_sonnet(None, error="bad")
    if need:
        assert opus != "NONE", f"Opus was needed for {s}"
        if opus is None:
            w.give_opus(None, error="bad")
        else:
            w.give_opus(opus, "o-reason")
    else:
        assert opus == "NONE", f"Opus was not expected for {s}"
    return s


class TestRuleTable:
    @pytest.mark.parametrize("c,value,action", [
        (3, 4, "cut"), (3, 3, "opus_decides"), (3, 2, "opus_check"), (3, 1, "continue"), (3, 0, "continue"),
        (4, 4, "opus_decides"), (4, 3, "opus_check"), (4, 2, "continue"), (4, 0, "continue"),
        (3, "opposite", "opposite"), (4, "opposite", "opposite"), (3, "unsure", "opus_replaces"), (3, None, "unparsed")])
    def test_sonnet_action(self, c, value, action):
        assert NV.sonnet_action(value, c) == action

    def test_cut_off_3_sonnet_above_is_cut_directly(self):
        w = walk(3, ["a", "b"])
        assert step(w, 4) == "a"
        assert w.decision == "covered" and w.covered_by == "a" and w.next_pair() is None
        assert w.queue == ["b"] and len(w.readings) == 1                          # early exit: b never read

    def test_cut_off_3_sonnet_at_c_opus_decides(self):
        w = walk(3, ["a", "b"])
        step(w, 3, 3)
        assert w.decision == "covered" and w.covering.opus["value"] == 3 and w.covering.opus_role == "at_cut_off"
        w = walk(3, ["a", "b"])
        step(w, 3, 2)                                                             # rescued
        assert not w.decided and w.readings[0].outcome == "rescued"
        step(w, 1)
        assert w.next_pair() is None and w.decision == "new"

    def test_cut_off_3_sonnet_one_below_never_cuts(self):
        w = walk(3, ["a"])
        step(w, 2, 4)                                                             # Opus would cut: kept, review
        assert w.next_pair() is None and w.decision == "grey" and w.review == ["sonnet_below_opus_at"]
        d = w.review_details[0]
        assert d["stem"] == "a" and d["sonnet"]["value"] == 2 and d["opus"]["value"] == 4 and d["sonnet"]["reason"]
        w = walk(3, ["a"])
        step(w, 2, 2)
        assert w.next_pair() is None and w.decision == "new" and w.review == []

    def test_cut_off_4(self):
        w = walk(4, ["a", "b", "c", "d"])
        step(w, 2)                                                                # below c - 1: no Opus
        step(w, 3, 3)                                                             # c - 1, Opus under c: no flag
        step(w, 4, 3)                                                             # at c, Opus under: rescued
        step(w, 4, 4)                                                             # at c, Opus at c: covered by d
        assert w.decision == "covered" and w.covered_by == "d"
        assert [r.outcome for r in w.readings] == ["continue", "continue", "rescued", "cut"]
        w = walk(4, ["a"])
        step(w, 3, 4)
        assert w.next_pair() is None and w.decision == "grey" and w.review == ["sonnet_below_opus_at"]

    def test_opposite_judges_the_partner_next_then_continues(self):
        w = walk(3, ["x", "a", "b", "p"], partners={"x": ["p"], "p": ["x"]})
        step(w, "opposite")
        assert w.next_pair() == "p"                                              # the partner jumps the queue
        step(w, 1)
        assert step(w, 4) == "a"                                                 # then down the list (Roger, 2026-10-07)
        assert w.decision == "covered" and w.covered_by == "a" and w.pair_completion_for == []
        assert [r.stem for r in w.readings] == ["x", "p", "a"] and w.queue == ["b"]

    def test_opposite_with_a_partner_already_judged_or_none(self):
        w = walk(3, ["p", "x", "a"], partners={"x": ["p"], "p": ["x"]})
        step(w, 1)
        step(w, "opposite")                                                      # p was judged: nothing moves
        assert w.next_pair() == "a"
        w = walk(3, ["x", "a"])
        step(w, "opposite")                                                      # no partner: a pair completion
        assert w.pair_completion_for == ["x"] and w.next_pair() == "a"
        step(w, 0)
        assert w.next_pair() is None and w.decision == "new"                     # a find, not a review flag

    def test_opposite_to_a_partner_outside_the_list_uses_its_cosine(self):
        info = {"x": L("x", 0.9)}
        w = NV.Walk("c#1", 3, ["x"], info, partners={"x": ["far"], "far": ["x"]}, cosine_of=lambda s: 0.05)
        w.next_pair()
        w.give_sonnet("opposite", "r")
        assert w.next_pair() == "far" and w.current.cosine == 0.05 and w.current.via == "partner"

    def test_unsure_goes_to_opus_whose_answer_stands(self):
        w = walk(3, ["a"])
        step(w, "unsure", 3)
        assert w.decision == "covered" and w.covering.opus_role == "sonnet_unsure"
        w = walk(3, ["a", "b"])
        step(w, "unsure", 1)
        assert not w.decided and w.readings[0].outcome == "continue"
        w = walk(3, ["x", "a"], partners={"x": ["a"]})
        step(w, "unsure", "opposite")
        assert w.readings[0].outcome == "opposite" and w.next_pair() == "a"

    def test_unparsed_is_skipped_and_flagged(self):
        w = walk(3, ["a", "b"])
        step(w, None)
        step(w, 1)
        assert w.next_pair() is None and w.decision == "grey" and w.review == ["unparsed"]
        w = walk(3, ["a"])
        step(w, 3, None)                                                         # Opus never parsed: kept, flagged
        assert w.next_pair() is None and w.decision == "grey" and w.readings[0].outcome == "unparsed"

    def test_flags_from_stage_3_make_a_kept_candidate_grey_but_not_a_covered_one(self):
        w = walk(3, ["a"], review=["pair_flag"])
        step(w, 1)
        assert w.next_pair() is None and w.decision == "grey"
        w = walk(3, ["a"], review=["pair_flag"])
        step(w, 4)
        assert w.decision == "covered" and w.review == ["pair_flag"]
        with pytest.raises(ValueError):
            walk(3, ["a"], review=["nonsense"])

    def test_an_empty_queue_is_new(self):
        w = walk(3, [])
        assert w.next_pair() is None and w.decision == "new" and w.readings == []

    def test_replay_and_pair_verdict(self):
        readings = {"a": {"sonnet": {"value": 2, "reason": "r"}, "opus": {"value": 3, "reason": "o"}},
                    "b": {"sonnet": {"value": 3, "reason": "r"}, "opus": {"value": 3, "reason": "o"}},
                    "c": {"sonnet": {"value": 4, "reason": "r"}, "opus": None}}
        w = NV.replay_walk(walk(3, ["a", "b", "c"]), readings)
        assert w.decision == "covered" and w.covered_by == "b" and w.review == ["sonnet_below_opus_at"]
        assert NV.pair_verdict(2, 3, 3) == {"verdict": "review", "at_or_above": True}
        assert NV.pair_verdict(3, 3, 3) == {"verdict": "cut", "at_or_above": True}
        assert NV.pair_verdict(3, 2, 3) == {"verdict": "keep", "at_or_above": True}
        assert NV.pair_verdict(4, None, 3) == {"verdict": "cut", "at_or_above": True}
        assert NV.pair_verdict(3, None, 4) == {"verdict": "keep", "at_or_above": False}
        assert NV.pair_verdict("opposite", None, 3)["verdict"] == "opposite"


# --------------------------------------------------------------------------- review order and synonyms

def row(key, decision, *, review=(), a=0, region=None, covered_by=None, sonnet=None, opus=None, reason="overlap", run="r1"):
    d = None
    if sonnet is not None:
        d = {"stem": covered_by, "sonnet": {"value": sonnet, "reason": "s"}, "opus": {"value": opus, "reason": "o"} if opus else None}
    return {"key": key, "label": key.split("#")[0], "gloss": f"This means {key}.",
            "novelty": {"run_id": run, "decision": decision, "review": list(review), "alignment_score": a,
                        "region": region, "covered_by": covered_by, "deciding_reading": d, "reason": reason,
                        "exact_label": {"match": "corpus"} if reason == "exact_label" else None}}


class TestReviewAndSynonyms:
    def test_review_order_lists_grey_rows_alignment_first(self):
        rows = [row("b#1", "grey", review=["pair_flag"]), row("a#1", "grey", review=["unparsed", "pair_flag"]),
                row("c#1", "grey", review=["unparsed"], a=2), row("d#1", "new"), row("e#1", "covered"),
                row("f#1", "grey", review=["pair_flag"], region="alignment_ai_agent")]
        assert NV.review_order(rows) == [("alignment", "c#1"), ("alignment", "f#1"), ("other", "a#1"), ("other", "b#1")]
        with_new = NV.review_order(rows, include_new=True)
        assert with_new[-1] == ("other", "d#1") and len(with_new) == 5
        assert NV.review_order(rows, run_id="other_run") == []

    def test_synonyms_fours_first_then_threes_exact_labels_last(self):
        rows = [row("x#1", "covered", covered_by="alpha", sonnet=3, opus=3),
                row("y#1", "covered", covered_by="beta", sonnet=4),
                row("z#1", "covered", covered_by="alpha", sonnet=4),
                row("w#1", "covered", covered_by="gamma", reason="exact_label"),
                row("v#1", "new")]
        g = NV.synonyms(rows)
        assert [x["stem"] for x in g] == ["alpha", "beta", "gamma"]
        assert g[0]["best"] == 4 and [c["key"] for c in g[0]["candidates"]] == ["z#1", "x#1"]
        assert g[2]["best"] is None and g[2]["candidates"][0]["reason"] == "exact_label"
        assert [x["stem"] for x in NV.synonyms(rows, stem="beta")] == ["beta"]


# --------------------------------------------------------------------------- the waves

def is_relation(kw) -> bool:
    """A relation call (its user turn names a candidate and a list of traits), not an overlap call."""
    return "candidate" in json.loads(kw["messages"][0]["content"])


def rubrics():
    a = OT.load_rubrics(keys=["A"])["A"]
    rel = sr.load_prompt("relation")
    return {"overlap": {k: a[k] for k in ("name", "text", "version", "sha256")},
            "relation": {"name": "relation", "text": rel, "version": 1, "sha256": sr.sha256(rel)}}


def responder_for(relations=None, overlap=None, *, default_rel="unrelated", default_overlap=1, garbage=()):
    """Relation calls answered from ``relations[(candidate label, trait label)]``; overlap calls from
    ``overlap[(candidate label, trait label, "sonnet"|"opus")]`` (or without the model); ``garbage`` holds
    (candidate, trait, model) keys whose answer never parses."""
    relations, overlap = relations or {}, overlap or {}

    def responder(kw):
        user, model = user_text(kw), kw["model"]
        fam = "opus" if "opus" in model else ("sonnet" if "sonnet" in model else "haiku")
        obj = json.loads(user)
        if "candidate" in obj:
            c = obj["candidate"]["label"]
            rows = [{"id": t["id"], "reason": "r", "relation": relations.get((c, t["label"]), default_rel)}
                    for t in obj["traits"]]
            return make_response(json.dumps({"results": rows}), input_tokens=1200, output_tokens=400)
        c, o = obj["target"]["label"], obj["other"]["label"]
        if (c, o, fam) in garbage:
            return make_response("I cannot answer that.", input_tokens=150, output_tokens=10, cache_read=600)
        v = overlap.get((c, o, fam), overlap.get((c, o), default_overlap))
        return make_response(json.dumps({"reason": f"{fam} on {o}", "similarity": v}), input_tokens=150,
                             output_tokens=80, cache_read=600)
    return responder


def cand(label, *, a=0, gloss=None):
    from assistant_axis.gapgen.normalize import normalize_candidate
    n = normalize_candidate(label)
    return NR.M3Candidate(key=f"{n.stem}#1", stem=n.stem, label=n.label, gloss=gloss or f"This means being {label}.",
                          alignment_score=a, region=None, generators=["g"])


def make_runner(tmp_path, responder, *, usage=None, records=(), queue=None, mode="shortlist", renamed=None, **kw):
    idx = toy_index(tmp_path, renamed=renamed)
    sets = NV.label_sets(idx.traits, queue or {"entries": [{"stem": "queued", "label": "queued", "status": "candidate"}]})
    client = FakeAsyncAnthropic(responder)
    r = NR.NoveltyRunner(client=client, batch_id="m3test", rubrics=rubrics(), index=idx, label_sets=sets,
                         usage=usage if usage is not None else MultiModelUsage(), responses_path=tmp_path / "out" / "responses.jsonl",
                         k=4, mode=mode, config_version="cfg", retry_delays=(), resume_records=records, **kw)
    return r, client, idx


def vectors_for(idx, cands_weights):
    return {k: query(**w) for k, w in cands_weights.items()}


class TestRunner:
    def test_the_whole_walk_live(self, tmp_path):
        # cand A (far from alignment, c = 3): nearest delta (opposed: epsilon to the front), alpha similar
        # cand B (c = 4): nearest beta similar, Sonnet 4 then Opus 4: covered
        # alpha (exact label), queued (exact label, queue)
        rel = {("candidate a", "delta"): "opposed", ("candidate a", "alpha"): "similar",
               ("candidate b", "beta"): "similar"}
        ov = {("candidate a", "epsilon"): 1, ("candidate a", "alpha", "sonnet"): 2, ("candidate a", "alpha", "opus"): 3,
              ("candidate b", "beta", "sonnet"): 4, ("candidate b", "beta", "opus"): 4}
        decided = []
        r, client, idx = make_runner(tmp_path, responder_for(rel, ov), on_decided=lambda sts: decided.extend(sts),
                                     rules=R1)
        cands = [cand("candidate a"), cand("candidate b", a=3), cand("alpha"), cand("queued")]
        vec = {cands[0].key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4),
               cands[1].key: query(beta=0.9, kappa=0.5, zeta=0.4, eta=0.3)}
        states = r.run(cands, vec)
        a, b = states[cands[0].key], states[cands[1].key]
        assert states[cands[2].key].block["reason"] == "exact_label" and states[cands[2].key].block["covered_by"] == "alpha"
        assert states[cands[3].key].block["exact_label"]["match"] == "queue"
        # A: listed delta, alpha, zeta, kappa + epsilon, beta, gamma; shortlist epsilon (front), alpha
        assert a.shortlist.queue == ["epsilon", "alpha"]
        assert a.block["decision"] == "grey" and a.block["review"] == ["sonnet_below_opus_at"]
        assert [x["stem"] for x in a.block["readings"]] == ["epsilon", "alpha"]
        assert b.block["decision"] == "covered" and b.block["covered_by"] == "beta" and b.block["cut_off"] == 4
        assert b.block["deciding_reading"]["opus"]["value"] == 4
        # the waves: one relation wave, then per position one Sonnet wave and one Opus wave
        waves = [rec["wave"] for rec in r.records]
        assert waves[:2] == ["r1_relation", "r1_relation"]
        assert set(waves[2:]) <= {"o01_sonnet", "o01_opus", "o02_sonnet", "o02_opus"}
        first_opus = waves.index("o01_opus")
        assert all(w == "o01_sonnet" for w in waves[2:first_opus])
        # position 1: A reads epsilon (1, no Opus), B reads beta (4 at c = 4: Opus); position 2: A reads alpha
        assert [(x["key"], x["stem"], x["role"]) for x in r.records if x["wave"].startswith("o02")] == \
               [(cands[0].key, "alpha", "sonnet"), (cands[0].key, "alpha", "opus")]
        # the overlap calls: rubric A, the user turn the single form's, the system prompt cached
        ov_calls = [k for k in client.calls if not is_relation(k)]
        assert all(k["system"][0]["cache_control"] == {"type": "ephemeral"} for k in ov_calls)
        assert all("temperature" not in k for k in ov_calls)
        assert system_text(ov_calls[0]) == rubrics()["overlap"]["text"]
        rel_calls = [k for k in client.calls if is_relation(k)]
        assert all("cache_control" not in k["system"][0] and k["temperature"] == 0.0 for k in rel_calls)
        assert {s.cand.key for s in decided} == {c.key for c in cands}
        # usage: charged per model, and per candidate in its block
        assert set(r.usage.per_model) == {NV.HAIKU, NV.SONNET, NV.OPUS}
        assert set(a.block["usage"]["per_model"]) == {NV.HAIKU, NV.SONNET, NV.OPUS}
        assert a.block["rubrics"]["relation"]["version"] == 1 and a.block["rubrics"]["overlap"]["version"] == 6
        rr = NV.reading_rows("m3test", a.cand.as_dict(), a.block)
        assert [x["stem"] for x in rr] == ["epsilon", "alpha"] and rr[0]["cosine"] == pytest.approx(
            idx.cosine_to(idx.project(vec[cands[0].key]), "epsilon"), abs=1e-6)

    def test_unsure_relations_go_to_sonnet_for_those_traits_only(self, tmp_path):
        state = {"n": 0}

        def resp(kw):
            obj = json.loads(user_text(kw))
            if "candidate" in obj and "haiku" in kw["model"]:
                rows = [{"id": t["id"], "reason": "r", "relation": "unsure" if t["label"] in ("alpha", "zeta") else "unrelated"}
                        for t in obj["traits"]]
                return json.dumps({"results": rows})
            if "candidate" in obj:
                state["n"] += 1
                state["labels"] = [t["label"] for t in obj["traits"]]
                return json.dumps({"results": [{"id": t["id"], "reason": "r",
                                                "relation": "similar" if t["label"] == "alpha" else "unsure"}
                                               for t in obj["traits"]]})
            return json.dumps({"reason": "r", "similarity": 0})
        r, _, _ = make_runner(tmp_path, resp)
        c = cand("candidate a")
        st = r.run([c], {c.key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4)})[c.key]
        assert state["n"] == 1 and sorted(state["labels"]) == ["alpha", "zeta"]
        assert st.relations["alpha"] == "similar" and st.relations["zeta"] == "unsure"    # still unsure: kept
        assert st.block["relation"]["unsure_reasked"]["model"] == NV.SONNET
        assert st.shortlist.queue == ["alpha", "zeta"] and st.block["decision"] == "new"

    def test_an_unparsed_overlap_answer_is_asked_again_once_then_flagged(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar", ("candidate a", "zeta"): "similar"}
        r, client, _ = make_runner(tmp_path, responder_for(rel, {}, garbage={("candidate a", "alpha", "sonnet")}))
        c = cand("candidate a")
        st = r.run([c], {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})[c.key]
        alpha = [x for x in r.records if x.get("stem") == "alpha"]
        assert [x["parse_attempt"] for x in alpha] == [1, 2] and [x["wave"] for x in alpha] == ["o01_sonnet", "o01_sonnet_retry"]
        assert st.block["decision"] == "grey" and st.block["review"] == ["unparsed"]
        assert [x["outcome"] for x in st.block["readings"]] == ["unparsed", "continue"]
        rates = r.warn_parse_rates()
        assert rates[f"overlap:{NV.SONNET}"] == {"n": 2, "ok_first": 1, "ok": 1}

    def test_a_relation_call_that_never_parses_falls_back_to_every_listed_trait(self, tmp_path):
        base = responder_for({}, {("candidate a", "epsilon"): 4})

        def resp(kw):
            if is_relation(kw):
                return "no JSON here"
            return base(kw)
        r, _, _ = make_runner(tmp_path, resp)
        c = cand("candidate a")
        st = r.run([c], {c.key: query(delta=0.9, epsilon=0.8, zeta=0.5, kappa=0.4)})[c.key]
        assert [x["parse_attempt"] for x in r.records if x["step"] == "relation"] == [1, 2]
        assert st.block["relation"]["status"] == "unparsed" and st.block["relation"]["fallback"]
        assert st.block["pair_flags"] == []                                   # no pair check without answers
        assert [x["stem"] for x in st.block["readings"]] == ["delta", "epsilon"]
        assert st.block["decision"] == "covered" and st.block["review"] == ["unparsed"]

    def test_a_flaky_answer_is_re_asked_and_parses(self, tmp_path):
        seen = {"n": 0}
        base = responder_for({("candidate a", "alpha"): "similar"}, {("candidate a", "alpha"): 0})

        def resp(kw):
            obj = json.loads(user_text(kw))
            if "target" in obj and seen["n"] == 0:
                seen["n"] += 1
                return "oops"
            return base(kw)
        r, _, _ = make_runner(tmp_path, resp)
        c = cand("candidate a")
        st = r.run([c], {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})[c.key]
        assert st.block["decision"] == "new" and st.block["review"] == []

    def test_a_failed_request_stalls_the_candidate_and_a_resume_finishes_it(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar"}
        good = responder_for(rel, {("candidate a", "alpha"): 4})

        def failing(kw):
            if "target" in json.loads(user_text(kw)):
                return RuntimeError("network down")
            return good(kw)
        r, _, _ = make_runner(tmp_path, failing)
        c = cand("candidate a")
        vec = {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)}
        st = r.run([c], vec)[c.key]
        assert st.block is None and "Sonnet on alpha" in st.stalled
        recs = [json.loads(x) for x in (tmp_path / "out" / "responses.jsonl").read_text().splitlines()]
        r2, client2, _ = make_runner(tmp_path, good, records=recs)
        st2 = r2.run([c], vec)[c.key]
        assert st2.block["decision"] == "covered" and st2.block["covered_by"] == "alpha"
        # the relation call was replayed from the record, not sent again
        assert not any(is_relation(k) for k in client2.calls)
        assert r2.stats["resumed"] == 1

    def test_a_budget_stop_keeps_what_was_paid_and_raises(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar", ("candidate b", "beta"): "similar"}
        usage = GuardedUsage(budget_usd=0.004)
        decided = []
        r, _, _ = make_runner(tmp_path, responder_for(rel, {}), usage=usage, on_decided=lambda s: decided.extend(s))
        cs = [cand("candidate a"), cand("candidate b")]
        with pytest.raises(BudgetExceededError):
            r.run(cs, {cs[0].key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4),
                       cs[1].key: query(beta=0.9, zeta=0.6, eta=0.5, kappa=0.4)})
        assert len(r.records) >= 1 and all(st.block is None for st in r.states.values())
        assert decided == []

    def test_a_stop_before_the_second_asking_concludes_nothing(self, tmp_path):
        """One answer that failed to parse, then the budget stop: the pair is not marked unparsed (that needs
        a second failure); the candidate waits for a resume."""
        rel = {("candidate a", "alpha"): "similar"}
        usage = GuardedUsage(budget_usd=0.0035)      # the relation call ($0.0032) fits, the first overlap answer crosses
        r, _, _ = make_runner(tmp_path, responder_for(rel, {}, garbage={("candidate a", "alpha", "sonnet")}), usage=usage)
        c = cand("candidate a")
        with pytest.raises(BudgetExceededError):
            r.run([c], {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})
        st = r.states[c.key]
        assert st.block is None and "not_sent" in st.stalled and st.walk.review == []
        assert [x["parse_attempt"] for x in r.records if x.get("stem") == "alpha"] == [1]

    def test_full_scan_reads_every_listed_trait_and_replays_the_walk(self, tmp_path):
        ov = {("candidate a", "alpha", "sonnet"): 3, ("candidate a", "alpha", "opus"): 3,
              ("candidate a", "beta", "sonnet"): 2, ("candidate a", "beta", "opus"): 1}
        r, client, _ = make_runner(tmp_path, responder_for({}, ov), mode="full_scan")
        c = cand("candidate a")
        st = r.run([c], {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})[c.key]
        assert not any(is_relation(k) for k in client.calls)                               # no relation call
        listed = {x["stem"] for x in st.block["listed"]}
        assert {p["stem"] for p in st.block["scan"]} == listed                             # every listed trait read
        assert {x["wave"] for x in r.records} == {"f_sonnet", "f_opus"}
        opus_read = {x["stem"] for x in r.records if x["role"] == "opus"}
        assert opus_read == {"alpha", "beta"}                                              # the rule's pairs only
        assert st.block["decision"] == "covered" and st.block["covered_by"] == "alpha"
        verdicts = {p["stem"]: p["verdict"] for p in st.block["scan"]}
        assert verdicts["alpha"] == "cut" and verdicts["beta"] == "keep"

    def test_summary_counts(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar"}
        r, _, _ = make_runner(tmp_path, responder_for(rel, {("candidate a", "alpha"): 4}))
        cs = [cand("candidate a"), cand("alpha")]
        r.run(cs, {cs[0].key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)})
        s = NR.summarize(NR.result_rows(r.states), r.records, r.usage)
        assert s["by_decision"] == {"covered": 2} and s["by_reason"] == {"exact_label": 1, "overlap": 1}
        assert s["early_exit_depth"] == {"1": 1} and s["pairs_judged_total"] == 1
        assert s["by_cut_off"] == {"3": {"covered": 2}}
        assert s["cache"][NV.SONNET]["cache_read"] == 600 and s["cache"][NV.SONNET]["hit_rate_calls"] == 1.0
        assert set(s["spend_by_stage"]) == {"relation", "overlap"}
        assert s["spend_usd"] == pytest.approx(r.usage.total_cost_usd)


# --------------------------------------------------------------------------- round 2: decisions 12-15 and the floor

TRI = {"kind": "triangle", "members": ["alpha", "beta", "gamma"]}


class TestRound2Rules:
    def test_the_two_rule_sets_and_the_chain_between_them(self):
        assert R1.cosine_floor is None and R2.cosine_floor == 0.25 and NV.DEFAULT_RULES == R2
        assert R1.grey_kinds == ("sonnet_below_opus_at", "unparsed", "pair_flag") and R2.grey_kinds == ("unparsed",)
        chain = NV.rule_chain()
        assert [r for _, r in chain][0] == R1 and chain[-1][1] == R2 and len(chain) == 6
        for (_, a), (_, b) in zip(chain, chain[1:]):           # one decision per step
            changed = {k for k in NV.Rules.__dataclass_fields__ if k not in ("name", "version")
                       and getattr(a, k) != getattr(b, k)}
            assert 1 <= len(changed) <= 2
        assert NV.rule_chain(0.3)[-1][1].cosine_floor == 0.3
        assert NV.rules_of({}) == R1 and NV.rules_of({"rules": R2.as_dict()}) == R2
        assert R2.below_floor(0.2499) and not R2.below_floor(0.25) and not R2.with_floor(None).below_floor(-1)
        assert NV.verdict_cuts("review", R2) and not NV.verdict_cuts("review", R1) and NV.verdict_cuts("cut", R1)


class TestDecision12:
    def test_sonnet_one_below_and_opus_at_covers_flagged_and_stops(self):
        w = walk(3, ["a", "b"], rules=R2)
        step(w, 2, 3)
        assert w.decision == "covered" and w.covered_by == "a" and w.review == ["sonnet_below_opus_at"]
        assert w.readings[0].outcome == "cut" and w.covering.opus_role == "below_cut_off" and w.queue == ["b"]
        d = w.review_details[0]
        assert d["kind"] == "sonnet_below_opus_at" and d["sonnet"]["value"] == 2 and d["opus"]["value"] == 3
        w = walk(4, ["a"], rules=R2)
        step(w, 3, 4)
        assert w.decision == "covered" and w.review == ["sonnet_below_opus_at"]

    def test_opus_under_the_cut_off_keeps_it_and_unparsed_is_still_grey(self):
        w = walk(3, ["a", "b"], rules=R2)
        step(w, 2, 2)
        step(w, 1)
        assert w.next_pair() is None and w.decision == "new" and w.review == []
        w = walk(3, ["a"], rules=R2)
        step(w, None)
        assert w.next_pair() is None and w.decision == "grey" and w.review == ["unparsed"]

    def test_a_pair_flag_carried_in_does_not_make_a_row_grey(self):
        w = walk(3, ["a"], review=["pair_flag"], rules=R2)
        step(w, 1)
        assert w.next_pair() is None and w.decision == "new"


class TestDecision13:
    def listed(self):
        return [L("alpha", 0.9, partners=["beta", "gamma"], simplexes=[TRI]), L("delta", 0.8, partners=["epsilon"], pair="epsilon"),
                L("zeta", 0.7), L("beta", 0.6, partners=["alpha", "gamma"], simplexes=[TRI]),
                L("epsilon", 0.5, partners=["delta"], pair="delta", via="expanded", rank=None),
                L("gamma", 0.4, partners=["alpha", "beta"], via="expanded", rank=None, simplexes=[TRI])]

    def base(self):
        return {x.stem: "unrelated" for x in self.listed()}

    def test_both_ends_of_a_pair_similar_leave_the_queue_with_a_note(self):
        rel = self.base() | {"delta": "similar", "epsilon": "similar", "zeta": "similar"}
        sl = NV.build_shortlist(self.listed(), rel, rules=R2)
        assert sl.pair_notes == [{"pair": ["delta", "epsilon"], "kind": "pair", "both": "similar"}]
        assert sl.excluded == ["delta", "epsilon"] and sl.queue == ["zeta"]
        assert sl.pair_flags == [{"pair": ["delta", "epsilon"], "both": "similar"}]          # still on record
        old = NV.build_shortlist(self.listed(), rel, rules=R1)
        assert old.pair_notes == [] and old.queue == ["delta", "zeta", "epsilon"]
        one = NV.build_shortlist(self.listed(), self.base() | {"delta": "similar", "epsilon": "opposed"}, rules=R2)
        assert one.pair_notes == [] and one.queue == ["delta"]                                # the expected shape

    def test_a_triangle_is_noted_only_when_every_corner_is_similar(self):
        two = NV.build_shortlist(self.listed(), self.base() | {"alpha": "similar", "beta": "similar"}, rules=R2)
        assert two.pair_notes == [] and two.queue == ["alpha", "beta"]
        three = NV.build_shortlist(self.listed(), self.base() | {"alpha": "similar", "beta": "similar", "gamma": "similar",
                                                                "zeta": "similar"}, rules=R2)
        assert three.pair_notes == [{"pair": ["alpha", "beta", "gamma"], "kind": "triangle", "both": "similar"}]
        assert three.queue == ["zeta"] and three.excluded == ["alpha", "beta", "gamma"]

    def test_the_walk_never_judges_an_excluded_trait_not_even_as_an_opposites_partner(self):
        w = walk(3, ["x", "p", "a"], partners={"x": ["p"]}, rules=R2, exclude=["p"])
        step(w, "opposite")
        assert w.next_pair() == "a" and w.pair_completion_for == []                          # x has a partner
        step(w, 1)
        assert w.next_pair() is None and [r.stem for r in w.readings] == ["x", "a"]

    def test_the_runner_notes_the_pair_and_attaches_the_readings_on_record(self, tmp_path):
        rel = {("candidate a", "delta"): "similar", ("candidate a", "epsilon"): "similar", ("candidate a", "zeta"): "similar"}
        r, client, idx = make_runner(tmp_path, responder_for(rel, {}), rules=R1)
        c = cand("candidate a")
        vec = {c.key: query(delta=0.9, epsilon=0.8, zeta=0.7, kappa=0.6)}
        st1 = r.run([c], vec)[c.key]                       # rule set 1 reads both ends (a pair flag, grey)
        assert st1.block["decision"] == "grey" and {"delta", "epsilon"} <= {x["stem"] for x in st1.block["readings"]}
        r2, client2, _ = make_runner(tmp_path, responder_for(rel, {}), replay_records=r.records)
        st = r2.run([c], vec)[c.key]
        nv = st.block
        assert nv["decision"] == "new" and nv["review"] == ["both_similar"] and nv["pair_flags"]
        note = nv["pair_notes"][0]
        assert note["pair"] == ["delta", "epsilon"] and set(note["cosines"]) == {"delta", "epsilon"}
        assert note["readings_on_record"]["delta"]["sonnet"]["value"] == 1                  # from rule set 1's records
        assert [x["stem"] for x in nv["readings"]] == ["zeta"]                               # the ends never judged
        assert not any(json.loads(user_text(k)).get("other", {}).get("label") in ("delta", "epsilon")
                       for k in client2.calls)
        assert NV.in_review_queue(nv) and nv["rules"]["name"] == "m3_rules_2"


class TestDecision14:
    def test_pair_flags_are_recorded_but_a_kept_row_is_new_not_grey(self, tmp_path):
        rel = {("candidate a", "theta"): "opposed", ("candidate a", "iota"): "opposed", ("candidate a", "alpha"): "similar"}
        vec = query(theta=0.9, iota=0.8, alpha=0.7, zeta=0.6)
        for rules, decision, review in ((R2, "new", []), (R1, "grey", ["pair_flag"])):
            r, _, _ = make_runner(tmp_path / rules.name, responder_for(rel, {}), rules=rules)
            c = cand("candidate a")
            nv = r.run([c], {c.key: vec})[c.key].block
            assert nv["pair_flags"] == [{"pair": ["iota", "theta"], "both": "opposed"}]
            assert nv["decision"] == decision and nv["review"] == review
            assert NV.in_review_queue(nv) is (rules is R1)


class TestDecision15:
    def sets(self, tmp_path):
        t = NV.load_trait_corpus(write_corpus(tmp_path / "data", renamed={"gamma": "old_gamma"}))
        queue = {"entries": [{"stem": "short_sighted", "label": "short-sighted", "status": "candidate", "entity_type": "trait"}]}
        return NV.label_sets(t, queue)

    def test_labels_are_compared_separator_blind(self, tmp_path):
        s = self.sets(tmp_path)
        from assistant_axis.entity_id import normalize_to_file_name
        for label in ("lambda mu", "lambda-mu", "lambdamu", "Lambda Mu"):
            m = NV.exact_label_match(normalize_to_file_name(label), s, rules=R2)
            assert m["covered_by"] == "lambda_mu" and m["match"] == "corpus"
        assert NV.exact_label_match("lambdamu", s, rules=R2)["blind"] is True
        assert NV.exact_label_match("lambdamu", s, rules=R1) is None                        # rule set 1: exact only
        q = NV.exact_label_match("shortsighted", s, rules=R2)
        assert q["covered_by"] == "short_sighted" and q["match"] == "queue" and q["matched"] == "short_sighted"

    def test_a_renamed_from_match_no_longer_covers_at_stage_0(self, tmp_path):
        s = self.sets(tmp_path)
        assert NV.exact_label_match("old_gamma", s, rules=R2) is None
        assert NV.renamed_match("old_gamma", s, rules=R2) == {"current": "gamma", "old_stem": "old_gamma"}
        assert NV.renamed_match("oldgamma", s, rules=R2) == {"current": "gamma", "old_stem": "old_gamma", "blind": True}
        assert NV.renamed_match("old_gamma", s, rules=R1) is None                          # rule set 1 covers it instead
        assert NV.exact_label_match("old_gamma", s, rules=R1)["match"] == "renamed_from"

    def test_a_renamed_from_match_is_judged_with_the_current_trait_first_below_the_floor_too(self, tmp_path):
        ov = {("old gamma", "gamma", "sonnet"): 4}
        r, client, idx = make_runner(tmp_path, responder_for({}, ov), renamed={"gamma": "old_gamma"})
        c = cand("old gamma")
        vec = {c.key: query(zeta=0.9, eta=0.8, kappa=0.7, delta=0.6)}                   # gamma not retrieved: cosine 0
        st = r.run([c], vec)[c.key]
        nv = st.block
        assert nv["reason"] == "overlap" and nv["exact_label"] is None
        assert nv["renamed_from"] == {"current": "gamma", "old_stem": "old_gamma"}
        assert st.shortlist.queue[0] == "gamma" and nv["readings"][0]["stem"] == "gamma"
        assert nv["readings"][0]["via"] == "renamed_from" and nv["readings"][0]["cosine"] < 0.25
        assert nv["decision"] == "covered" and nv["covered_by"] == "gamma"
        assert any(is_relation(k) for k in client.calls)                                    # judged like any other
        r1, client1, _ = make_runner(tmp_path / "r1", responder_for({}, ov), renamed={"gamma": "old_gamma"}, rules=R1)
        st1 = r1.run([c], vec)[c.key]
        assert st1.block["reason"] == "exact_label" and client1.calls == []


class TestCosineFloor:
    def test_the_floor_keeps_low_similar_traits_out_but_not_an_opposed_partner_or_a_renamed_match(self):
        listed = [L("alpha", 0.6), L("delta", 0.5, partners=["epsilon"], pair="epsilon"), L("eta", 0.3),
                  L("kappa", 0.24), L("zeta", 0.2), L("epsilon", 0.1, partners=["delta"], pair="delta", via="expanded", rank=None)]
        rel = {"alpha": "similar", "delta": "opposed", "eta": "unrelated", "kappa": "similar", "zeta": "unsure",
               "epsilon": "unrelated"}
        sl = NV.build_shortlist(listed, rel, rules=R2, renamed="lambda_mu")
        assert sl.queue == ["lambda_mu", "epsilon", "alpha"] and sl.renamed == "lambda_mu"
        assert sl.below_floor == ["kappa", "zeta"] and sl.n_below_floor == 3
        assert NV.build_shortlist(listed, rel, rules=R2.with_floor(None)).queue == ["epsilon", "alpha", "kappa", "zeta"]
        fb = NV.build_shortlist(listed, {}, rules=R2, fallback=True)
        assert fb.queue == ["alpha", "delta", "eta"] and fb.below_floor == ["kappa", "zeta", "epsilon"]

    def test_an_opposite_reading_brings_its_partner_even_below_the_floor(self, tmp_path):
        rel = {("candidate a", "delta"): "similar", ("candidate a", "zeta"): "similar"}
        ov = {("candidate a", "delta", "sonnet"): "opposite", ("candidate a", "epsilon", "sonnet"): 4}
        r, _, idx = make_runner(tmp_path, responder_for(rel, ov))
        c = cand("candidate a")
        nv = r.run([c], {c.key: query(delta=0.9, zeta=0.5, eta=0.3, kappa=0.2)})[c.key].block
        eps = next(x for x in nv["listed"] if x["stem"] == "epsilon")
        assert eps["cosine"] < 0.25 and "epsilon" not in nv["shortlist"]
        assert [x["stem"] for x in nv["readings"]] == ["delta", "epsilon"]
        assert nv["decision"] == "covered" and nv["covered_by"] == "epsilon"
        assert nv["n_below_floor"] == sum(1 for x in nv["listed"] if x["cosine"] < 0.25) and nv["rules"]["cosine_floor"] == 0.25


class TestReviewOrderRound2:
    def test_covered_and_flagged_and_noted_rows_are_in_the_queue(self):
        rows = [row("a#1", "covered", review=["sonnet_below_opus_at"], covered_by="x", sonnet=2, opus=3),
                row("b#1", "new", review=["both_similar"]), row("c#1", "grey", review=["unparsed"]),
                row("d#1", "covered", review=["pair_flag"]), row("e#1", "new")]
        assert NV.review_order(rows) == [("other", "c#1"), ("other", "a#1"), ("other", "b#1")]
        assert NV.review_order(rows, include_new=True)[-1] == ("other", "e#1")


class TestOfflineAndReplay:
    def test_replayed_records_are_used_but_not_counted_and_the_seed_is_the_sources(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar"}
        ov = {("candidate a", "alpha"): 4}
        r, _, _ = make_runner(tmp_path, responder_for(rel, ov), rules=R1)
        c = cand("candidate a")
        vec = {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)}
        first = r.run([c], vec)[c.key].block
        tr = NR.OfflineTransport()
        idx = toy_index(tmp_path / "again")
        r2 = NR.NoveltyRunner(client=None, batch_id="other_run", rubrics=rubrics(), index=idx,
                              label_sets=NV.label_sets(idx.traits, {"entries": []}), usage=MultiModelUsage(),
                              responses_path=tmp_path / "never.jsonl", k=4, transport=tr, rules=R1,
                              relation_seed="m3test", replay_records=r.records)
        again = r2.run([c], vec)[c.key].block
        assert tr.wanted == [] and r2.records == [] and not (tmp_path / "never.jsonl").exists()
        assert again["decision"] == first["decision"] and again["readings"] == first["readings"]
        # another seed orders the relation call's list differently: not on record, so it is wanted and stalls
        tr3 = NR.OfflineTransport()
        r3 = NR.NoveltyRunner(client=None, batch_id="other_run", rubrics=rubrics(), index=idx,
                              label_sets=NV.label_sets(idx.traits, {"entries": []}), usage=MultiModelUsage(),
                              responses_path=tmp_path / "never.jsonl", k=4, transport=tr3, rules=R1,
                              replay_records=r.records)
        st3 = r3.run([c], vec)[c.key]
        assert st3.block is None and [w["step"] for w in tr3.wanted] == ["relation"]


# --------------------------------------------------------------------------- the Message Batches path

class TestBatches:
    def test_one_sonnet_wave_then_one_opus_wave_per_position_with_the_one_hour_cache(self, tmp_path):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.tests.test_gapgen_batches import FakeBatchClient, no_sleep
        rel = {("candidate a", "alpha"): "similar", ("candidate a", "zeta"): "similar",
               ("candidate b", "beta"): "similar"}
        ov = {("candidate a", "alpha", "sonnet"): 3, ("candidate a", "alpha", "opus"): 2, ("candidate a", "zeta"): 0,
              ("candidate b", "beta", "sonnet"): 4}
        resp = responder_for(rel, ov)
        usage = GuardedUsage(budget_usd=5.0)
        r, live, _ = make_runner(tmp_path, resp, usage=usage, cache_ttl=NR.BATCH_CACHE_TTL)
        bc = FakeBatchClient(resp)
        r.transport = BatchTransport(r, bc, tmp_path / "out" / "batches.json", sleep=no_sleep, poll_seconds=0)
        cs = [cand("candidate a"), cand("candidate b")]
        states = r.run(cs, {cs[0].key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4),
                            cs[1].key: query(beta=0.9, zeta=0.6, eta=0.5, kappa=0.4)})
        assert live.calls == []
        waves = list(json.loads((tmp_path / "out" / "batches.json").read_text())["waves"])
        assert waves == ["r1_relation", "o01_sonnet", "o01_opus", "o02_sonnet"]
        assert states[cs[0].key].block["decision"] == "new" and states[cs[1].key].block["covered_by"] == "beta"
        for b in bc.batches.created:
            for q in b["requests"]:
                p = q["params"]
                if not is_relation(p):
                    assert p["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
                else:
                    assert "cache_control" not in p["system"][0]
                assert len(q["custom_id"]) <= 64
        assert all(m.endswith(BATCH_SUFFIX) for m in usage.per_model)
        assert all(x["transport"] == "batches" and x["batch_request_id"] for x in r.records)


# --------------------------------------------------------------------------- the estimate

class TestEstimate:
    def test_plan_estimate_counts(self):
        st = NR.plan_estimate(n_candidates=100, n_scan=10, mean_listed=15.0, relation_text_chars=1343, trait_chars=240,
                              cand_chars=140)
        rel = st["relation"].lines[0]
        assert rel.n_calls == 100 and rel.model == NV.HAIKU and rel.out_tok == 20 + 45 * 15
        assert rel.in_tok == round((1343 + 140 + 15 * 240) / 4.0)
        son, op = st["overlap"].lines
        assert son.n_calls == round(100 * 3 * 0.82) and op.n_calls == round(son.n_calls * NR.OPUS_SHARE_SHORTLIST)
        # Sonnet $0.0012 and Opus $0.0031 a pair, as overlap_arms_3 measured
        assert son.usd / son.n_calls == pytest.approx(0.0012, abs=0.0001)
        assert op.usd / op.n_calls == pytest.approx(0.0031, abs=0.0001)
        fs = st["full_scan"].lines[0]
        assert fs.n_calls == 150
        b = NR.plan_estimate(n_candidates=100, n_scan=10, mean_listed=15.0, relation_text_chars=1343, trait_chars=240,
                             cand_chars=140, transport="batches")
        assert b["overlap"].usd == pytest.approx(0.5 * st["overlap"].usd)

    def test_runner_estimate_of_calls(self, tmp_path):
        r, _, idx = make_runner(tmp_path, responder_for())
        st = NR.CandState(cand=cand("candidate a"))
        oc = r._overlap_call(st, "alpha", "opus", 1)
        assert r.estimate_usd([oc]) == pytest.approx(0.0031, abs=0.0001)
        assert r.estimate_usd([oc], batch=True) == pytest.approx(0.5 * r.estimate_usd([oc]))
        rc = r._relation_call(st, ["alpha", "beta"])
        assert NR.call_tokens(rc)[1] == 20 + 45 * 2

    def test_mean_listed_size_on_the_toy_corpus(self, tmp_path):
        idx = toy_index(tmp_path)
        assert NR.mean_listed_size(idx, 1) >= 1.0


# --------------------------------------------------------------------------- the relation call on another model

HAIKU55 = "claude-haiku-5-5"


class TestRelationModel:
    """``relation_model`` and ``relation_only`` (coding_plan_haiku55.md, comparison B)."""

    def test_the_relation_call_goes_to_the_model_given_and_the_unsure_re_ask_to_sonnet(self, tmp_path):
        def resp(kw):
            obj = json.loads(user_text(kw))
            if "candidate" in obj and "haiku" in kw["model"]:
                return json.dumps({"results": [{"id": t["id"], "reason": "r",
                                                "relation": "unsure" if t["label"] == "zeta" else "unrelated"}
                                               for t in obj["traits"]]})
            if "candidate" in obj:
                return json.dumps({"results": [{"id": t["id"], "reason": "r", "relation": "similar"}
                                               for t in obj["traits"]]})
            return json.dumps({"reason": "r", "similarity": 0})
        r, client, _ = make_runner(tmp_path, resp, relation_model=HAIKU55)
        c = cand("candidate a")
        st = r.run([c], {c.key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4)})[c.key]
        rel = [k for k in client.calls if is_relation(k)]
        assert [k["model"] for k in rel] == [HAIKU55, NV.SONNET]
        assert "temperature" not in rel[0] and "cache_control" not in rel[0]["system"][0]   # Haiku 5.5 refuses it
        assert rel[0]["max_tokens"] == NR.RELATION_MAX_TOKENS
        assert st.block["relation"]["model"] == HAIKU55 and st.block["relation"]["unsure_reasked"]["model"] == NV.SONNET
        recs = [x for x in r.records if x["step"] == "relation"]
        assert recs[0]["model"] == HAIKU55 and recs[0]["role"] == "haiku"
        assert st.relations["zeta"] == "similar" and st.block is not None             # the walk ran (not relation-only)
        assert set(r.usage.per_model) >= {HAIKU55, NV.SONNET} and NV.HAIKU not in r.usage.per_model

    def test_the_default_is_unchanged(self, tmp_path):
        r, _, _ = make_runner(tmp_path, responder_for())
        st = NR.CandState(cand=cand("candidate a"))
        c = r._relation_call(st, ["alpha"])
        assert c.model == NR.RELATION_MODEL == NV.HAIKU and c.role == "haiku" and c.temperature == 0.0
        assert r._relation_call(st, ["alpha"], step="relation_unsure").role == "sonnet"
        assert [NR.model_role(m) for m in (NV.HAIKU, HAIKU55, NV.SONNET, NV.OPUS, "claude-fable-5-1", "x")] == \
            ["haiku", "haiku", "sonnet", "opus", "fable", "relation"]

    def test_relation_only_sends_no_overlap_call_and_decides_nothing_past_stage_0(self, tmp_path):
        rel = {("candidate a", "delta"): "opposed", ("candidate a", "alpha"): "similar",
               ("candidate b", "beta"): "similar"}
        decided = []
        r, client, idx = make_runner(tmp_path, responder_for(rel, {}), relation_model=HAIKU55, relation_only=True,
                                     on_decided=lambda sts: decided.extend(sts))
        cands = [cand("candidate a"), cand("candidate b", a=3), cand("alpha")]
        vec = {cands[0].key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4),
               cands[1].key: query(beta=0.9, kappa=0.5, zeta=0.4, eta=0.3)}
        states = r.run(cands, vec)
        assert client.calls and all(is_relation(k) for k in client.calls)
        assert {k["model"] for k in client.calls} == {HAIKU55}
        a, b = states[cands[0].key], states[cands[1].key]
        assert a.block is None and b.block is None and a.walk is not None              # built, never walked
        assert a.shortlist.queue == ["epsilon", "alpha"] and b.shortlist.queue == ["beta"]
        assert states[cands[2].key].block["reason"] == "exact_label"                     # stage 0 still decides
        assert [s.cand.key for s in decided] == [cands[2].key]
        rows = NR.relation_rows(states, r.records)
        assert [x["key"] for x in rows] == sorted([cands[0].key, cands[1].key])
        ra = next(x for x in rows if x["key"] == cands[0].key)
        assert ra["model"] == HAIKU55 and ra["status"] == "ok" and ra["counts"]["opposed"] == 1
        assert ra["counts"]["similar"] == 1 and sum(ra["counts"].values()) == len(ra["order"]) == len(a.listed)
        assert ra["shortlist"] == ["epsilon", "alpha"] and ra["shortlist_length"] == 2
        assert ra["answers"]["alpha"]["relation"] == "similar" and ra["relations"]["delta"] == "opposed"
        assert ra["calls"][0]["model"] == HAIKU55 and ra["calls"][0]["usage_raw"]["output_tokens"] == 400
        assert ra["calls"][0]["text_chars"] > 0 and ra["listed"][0]["stem"] in ra["order"]
        s = NR.relation_summary(rows, r.records, r.usage, not_reached={"exact_label": 1})
        assert s["n_candidates_reached"] == 2 and s["call_status"] == {"ok": 2} and s["answers"]["similar"] == 2
        assert s["unsure_rate"] == 0 and s["shortlist_length_total"] == 3 and s["not_reached"] == {"exact_label": 1}
        calls = s["calls"][f"relation:{HAIKU55}"]
        assert calls["n_calls"] == 2 and calls["output_tokens"]["mean"] == 400 and calls["stop_reasons"] == {"end_turn": 2}
        assert calls["cost_usd"] == pytest.approx(2 * (1200 * 0.10 + 400 * 0.50) / 1e6)
        assert s["spend_usd"] == pytest.approx(calls["cost_usd"])
        with pytest.raises(ValueError):
            make_runner(tmp_path, responder_for(), mode="full_scan", relation_only=True)

    def test_the_estimate_on_another_model(self):
        kw = dict(n_candidates=100, n_scan=0, mean_listed=15.0, relation_text_chars=1343, trait_chars=240, cand_chars=140)
        h45 = NR.plan_estimate(**kw)["relation"].lines[0]
        h55 = NR.plan_estimate(**kw, relation_model=HAIKU55)["relation"].lines[0]
        assert h55.model == HAIKU55 and h55.in_tok == round((1343 + 140 + 15 * 240) / 4.0 * 1.3)
        assert h55.out_tok == round((20 + 45 * 15) * 1.3) and h45.out_tok == 20 + 45 * 15
        assert h55.usd == pytest.approx(h45.usd * 0.13, rel=0.01)


# --------------------------------------------------------------------------- the 1-hour cache and its billing

class TestOneHourCache:
    def test_request_params_ttl(self):
        from assistant_axis.gapgen.llm import request_params
        p = request_params(model=NV.SONNET, system="S", user="U", max_tokens=10, temperature=0.0, cache_ttl="1h")
        assert p["system"][0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"} and "temperature" not in p
        p = request_params(model=NV.SONNET, system="S", user="U", max_tokens=10, temperature=0.0)
        assert p["system"][0]["cache_control"] == {"type": "ephemeral"}             # unchanged without a ttl
        with pytest.raises(ValueError):
            request_params(model=NV.SONNET, system="S", user="U", max_tokens=10, temperature=None, cache_ttl="2h")

    def test_one_hour_writes_are_billed_at_twice_the_input_price(self):
        from types import SimpleNamespace
        from assistant_axis.gapgen.llm import billed_usage
        resp = make_response("x", input_tokens=100, output_tokens=5, cache_creation=600)
        resp.usage.cache_creation = SimpleNamespace(ephemeral_5m_input_tokens=0, ephemeral_1h_input_tokens=600)
        p, o, raw = billed_usage(resp)
        assert p == 100 + 1200 and raw["cache_creation_1h_input_tokens"] == 600
        assert NR.billed_from_raw(raw) == (1300, 5)
        p5, _, raw5 = billed_usage(make_response("x", input_tokens=100, output_tokens=5, cache_creation=600))
        assert p5 == 100 + 750 and "cache_creation_1h_input_tokens" not in raw5

    def test_the_split_filter_batches_are_still_sent_uncached(self):
        from assistant_axis.gapgen.batches import BatchTransport
        from assistant_axis.gapgen.split_runner import Call as SplitCall
        c = SplitCall(step="sense", key="k#1", label="k", model=NV.HAIKU, system="S", user="U", max_tokens=10, temperature=0.0)
        assert "cache_control" not in BatchTransport._request(c)["params"]["system"][0]
