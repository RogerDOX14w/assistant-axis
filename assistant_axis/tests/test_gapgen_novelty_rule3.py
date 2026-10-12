"""M3 rule set 3 and the broader check (the M3 gate audit, ``reports/code_review_2026-10-12/gate_audits/m3_novelty.md``;
Roger's decisions of 2026-10-12): the graded cut-off (P1), ``renamed_from`` before the queue at stage 0 (P2, review 2
D1, and the same leak in ``recovery.reduced_label_sets``), the partner skip (P5), and the broader check (P3: its
rubric pin, render, parse, verdict and gate, the walk and the runner's wave, the CLI flag and the pilot command).
Rule sets 1 and 2 are checked unchanged here too (their blocks and their decisions on the same readings).  No API
calls: fake clients, the toy corpus of test_gapgen_novelty.py, the toy CLI environment of
test_gap_generation_novelty_cli.py."""
import json
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen import recovery as RC
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from assistant_axis.tests.test_gapgen_novelty import (L, R1, R2, cand, query, responder_for, rubrics, toy_index,
                                                      write_corpus)

REPO = Path(__file__).resolve().parents[2]
R3 = NV.RULES[3]
RB = R3.with_broader("mean")


# --------------------------------------------------------------------------- the rule sets

class TestRuleSets:
    def test_rule_set_3_is_rule_set_2_plus_three_switches_and_the_default(self):
        assert NV.DEFAULT_RULES == R3 and R3.version == 3 and R3.name == "m3_rules_3"
        diff = {k for k in NV.Rules.__dataclass_fields__ if k not in ("name", "version")
                and getattr(R2, k) != getattr(R3, k)}
        assert diff == {"renamed_before_queue", "cut_off_rule", "skip_unrelated_partners"}
        assert R3.broader_check is None and RB.broader_check == "mean" and R3.grey_kinds == R2.grey_kinds
        with pytest.raises(ValueError):
            R3.with_broader("most")
        with pytest.raises(ValueError):
            NV.Rules(**{**R3.as_dict(), "cut_off_rule": "steep"})

    def test_the_older_rule_sets_record_what_they_always_recorded(self):
        """A block's ``rules`` of rule set 1 or 2 has exactly the keys it had before 2026-10-12, and every recorded
        form reads back (a block without the new keys: their defaults, rule sets 1 and 2's behaviour)."""
        old_keys = {"name", "version", "cover_on_opus_check", "both_similar_excluded", "pair_flag_grey",
                    "renamed_from_covers", "separator_blind", "cosine_floor"}
        assert set(R1.as_dict()) == old_keys and set(R2.as_dict()) == old_keys
        assert set(R3.as_dict()) == old_keys | {"renamed_before_queue", "cut_off_rule", "skip_unrelated_partners"}
        assert set(RB.as_dict()) == set(R3.as_dict()) | {"broader_check"}
        for r in (R1, R2, R3, RB, R2.with_floor(None)):
            assert NV.rules_of({"rules": r.as_dict()}) == r
        assert NV.rules_of({}) == R1

    def test_the_attribution_chain_one_switch_a_step(self):
        chain = NV.attribution_chain(R2, R3)
        assert [n.split(" (")[0] for n, _ in chain] == ["source rules", "review 2 D1", "graded cut-off", "partner skip"]
        assert chain[0][1] == R2 and chain[-1][1] == R3
        for (_, a), (_, b) in zip(chain, chain[1:]):
            assert len({k for k in NV.Rules.__dataclass_fields__ if k not in ("name", "version")
                        and getattr(a, k) != getattr(b, k)}) == 1
        assert [n.split(" (")[0] for n, _ in NV.attribution_chain(R2, RB)][-1] == "broader check"
        full = NV.attribution_chain(R1, R3)
        assert len(full) == 1 + 5 + 3 and full[-1][1] == R3
        assert NV.attribution_chain(R3, R3) == [("source rules (m3_rules_3)", R3)]
        assert NV.rule_chain()[-1][1] == R2                    # rule set 1 to 2: unchanged


# --------------------------------------------------------------------------- P1: the graded cut-off

class TestGradedCutOff:
    def test_the_step_rule_is_unchanged(self):
        assert [NV.cut_off(a) for a in (0, 1, 2, 3)] == [3, 3, 4, 4] and NV.cut_off(None) == 4
        for rules in (None, R1, R2):
            assert [NV.cut_off(a, rules) for a in (0, 1, 2, 3, None, True)] == [3, 3, 4, 4, 4, 4]
            s = NV.cut_off_spec(2, rules)
            assert s.sonnet_alone and s.opus_check and s.rule == "step"

    def test_the_graded_rule(self):
        g = {a: NV.cut_off_spec(a, R3) for a in (0, 1, 2, 3, None)}
        assert [g[a].c for a in (0, 1, 2, 3, None)] == [3, 3, 3, 4, 4]
        assert g[0].sonnet_alone and g[0].opus_check and g[0].band == "alignment 0-1"
        assert not g[2].sonnet_alone and not g[2].opus_check and g[2].band == "alignment 2"
        assert g[3].sonnet_alone and g[3].opus_check and g[3].band == "alignment 3"
        assert g[None].band == "no alignment score" and g[2].rule == "graded"

    @pytest.mark.parametrize("value,action", [(4, "opus_confirms"), (3, "opus_decides"), (2, "continue"),
                                              (1, "continue"), ("unsure", "opus_replaces"), ("opposite", "opposite")])
    def test_sonnet_action_at_alignment_2(self, value, action):
        assert NV.sonnet_action(value, NV.cut_off_spec(2, R3)) == action
        assert NV.OPUS_ROLES.get("opus_confirms") == "above_cut_off"

    def walk(self, a, rules, queue=("a", "b")):
        info = {s: L(s, 0.9 - i * 0.1) for i, s in enumerate(queue)}
        return NV.Walk("cand#1", NV.cut_off_spec(a, rules), list(queue), info, rules=rules)

    @staticmethod
    def step(w, sonnet, opus="NONE"):
        w.next_pair()
        need = w.give_sonnet(sonnet, "s")
        assert need == (opus != "NONE")
        if need:
            w.give_opus(opus, "o")

    def test_alignment_2_is_covered_when_both_models_read_3_or_more(self):
        for s, o in ((3, 3), (3, 4), (4, 3), (4, 4)):
            w = self.walk(2, R3)
            self.step(w, s, o)
            assert w.decision == "covered" and w.covered_by == "a" and w.review == []
            assert w.covering.opus_role == ("above_cut_off" if s == 4 else "at_cut_off")
        for s, o in ((3, 2), (4, 2)):                                   # Opus under 3: rescued, the walk goes on
            w = self.walk(2, R3)
            self.step(w, s, o)
            assert not w.decided and w.readings[0].outcome == "rescued"
        w = self.walk(2, R3)
        self.step(w, 2)                                                 # a Sonnet 2: settled, no Opus check
        self.step(w, 1)
        assert w.next_pair() is None and w.decision == "new" and w.review == []

    def test_the_same_readings_under_rule_set_2_and_at_the_other_scores(self):
        w = self.walk(2, R2)                                            # the step rule: cut-off 4
        self.step(w, 3, 3)
        self.step(w, 2)
        assert w.next_pair() is None and w.decision == "new"
        w = self.walk(3, R3)                                            # alignment 3 keeps cut-off 4
        self.step(w, 3, 3)
        self.step(w, 4, 3)
        assert w.next_pair() is None and w.decision == "new" and [r.outcome for r in w.readings] == ["continue", "rescued"]
        w = self.walk(3, R3)
        self.step(w, 3, 4)                                              # decision 12 at 4, as before
        assert w.decision == "covered" and w.review == ["sonnet_below_opus_at"]
        for rules in (R2, R3):                                          # alignment 0-1: unchanged
            w = self.walk(1, rules)
            self.step(w, 2, 3)
            assert w.decision == "covered" and w.review == ["sonnet_below_opus_at"]

    def test_the_records_of_a_step_run_hold_every_reading_the_graded_rule_needs(self):
        """At cut-off 4 every Sonnet 3 or 4 has its Opus reading on record and a Sonnet 2 has none; the graded rule
        asks Opus for exactly those, so a re-decided step run needs no call (the audit's § 7.5)."""
        spec4, graded = NV.cut_off_spec(2, R2), NV.cut_off_spec(2, R3)
        for s in (0, 1, 2, 3, 4, "unsure", "opposite"):
            assert (NV.sonnet_action(s, spec4) in NV.OPUS_ROLES) == (NV.sonnet_action(s, graded) in NV.OPUS_ROLES)
        readings = {"a": {"sonnet": {"value": 3, "reason": "r"}, "opus": {"value": 3, "reason": "o"}}}
        w = NV.replay_walk(self.walk(2, R3, ("a",)), readings)
        assert w.decision == "covered"
        assert NV.replay_walk(self.walk(2, R2, ("a",)), readings).decision == "new"
        assert NV.pair_verdict(3, 3, graded)["verdict"] == "cut" and NV.pair_verdict(2, 3, graded)["verdict"] == "keep"
        assert NV.pair_verdict(4, 3, graded)["verdict"] == "cut" and NV.pair_verdict(4, None, graded)["verdict"] == "unparsed"
        assert NV.pair_verdict(3, 3, 4)["verdict"] == "keep"            # an integer: the step rule, as before

    def test_the_block_says_which_rule_decided(self, tmp_path):
        cnd = {"alignment_score": 2, "region": None}
        kw = dict(run_id="r", cand=cnd, decision="new", reason="no_listed", rubrics={}, config_version="c", at="t")
        b3 = NV.novelty_block(rules=R3, **kw)
        assert b3["cut_off"] == 3 and b3["cut_off_rule"] == {"c": 3, "sonnet_alone": False, "opus_check": False,
                                                             "rule": "graded", "band": "alignment 2"}
        b2 = NV.novelty_block(rules=R2, **kw)
        assert b2["cut_off"] == 4 and "cut_off_rule" not in b2 and "partners_skipped" not in b2
        assert b3["partners_skipped"] == []


# --------------------------------------------------------------------------- P2: stage 0 (review 2 D1)

class TestStage0:
    def sets(self, tmp_path):
        t = NV.load_trait_corpus(write_corpus(tmp_path / "data", renamed={"gamma": "old_gamma"}))
        queue = {"entries": [{"stem": "old_gamma", "label": "old gamma", "status": "paired", "entity_type": "trait"},
                             {"stem": "queued_one", "label": "queued one", "status": "candidate", "entity_type": "trait"}]}
        return t, queue, NV.label_sets(t, queue)

    def test_renamed_from_is_checked_before_the_queue(self, tmp_path):
        _, _, s = self.sets(tmp_path)
        leak = NV.exact_label_match("old_gamma", s, rules=R2)            # rule set 2: the stale entry covers
        assert leak["match"] == "queue" and leak["covered_by"] == "old_gamma"
        assert NV.renamed_match("old_gamma", s, rules=R2) == {"current": "gamma", "old_stem": "old_gamma"}
        assert NV.exact_label_match("old_gamma", s, rules=R3) is None     # rule set 3: judged, decision 15
        assert NV.exact_label_match("oldgamma", s, rules=R3) is None      # separator-blind too
        assert NV.renamed_match("old_gamma", s, rules=R3) == {"current": "gamma", "old_stem": "old_gamma"}
        assert NV.exact_label_match("queued_one", s, rules=R3)["match"] == "queue"     # a plain queue name still covers
        assert NV.exact_label_match("gamma", s, rules=R3)["match"] == "corpus"
        assert NV.exact_label_match("old_gamma", s, rules=R1)["match"] == "renamed_from"

    def test_the_runner_walks_it_with_the_current_trait_first(self, tmp_path):
        from assistant_axis.tests.test_gapgen_novelty import make_runner
        queue = {"entries": [{"stem": "old_gamma", "label": "old gamma", "status": "paired", "entity_type": "trait"}]}
        ov = {("old gamma", "gamma", "sonnet"): 4}
        vec = query(zeta=0.9, eta=0.8, kappa=0.7, delta=0.6)
        c = cand("old gamma")
        r2, client2, _ = make_runner(tmp_path / "r2", responder_for({}, ov), queue=queue, renamed={"gamma": "old_gamma"},
                                     rules=R2)
        b2 = r2.run([c], {c.key: vec})[c.key].block
        assert b2["reason"] == "exact_label" and b2["exact_label"]["match"] == "queue" and client2.calls == []
        r3, client3, _ = make_runner(tmp_path / "r3", responder_for({}, ov), queue=queue, renamed={"gamma": "old_gamma"},
                                     rules=R3)
        b3 = r3.run([c], {c.key: vec})[c.key].block
        assert b3["reason"] == "overlap" and b3["exact_label"] is None and b3["renamed_from"]["current"] == "gamma"
        assert b3["readings"][0]["stem"] == "gamma" and b3["decision"] == "covered" and b3["covered_by"] == "gamma"
        assert r3.stats["renamed_from_judged"] == 1

    def test_the_recovery_harness_drops_a_hidden_traits_old_name_from_the_queue(self, tmp_path):
        t, queue, _ = self.sets(tmp_path)
        red = RC.reduced_traits(t, ["gamma", "alpha", "beta"])           # gamma's triangle hides whole
        leaky = RC.reduced_label_sets(red, queue, ["gamma", "alpha", "beta"])
        assert NV.exact_label_match("old_gamma", leaky, rules=R3)["match"] == "queue"      # the leak, without traits
        fixed = RC.reduced_label_sets(red, queue, ["gamma", "alpha", "beta"], traits=t)
        assert NV.exact_label_match("old_gamma", fixed, rules=R3) is None
        assert NV.exact_label_match("old_gamma", fixed, rules=R2) is None
        assert NV.renamed_match("old_gamma", fixed, rules=R3) is None     # gamma is hidden: nothing names it
        assert NV.exact_label_match("queued_one", fixed, rules=R3)["match"] == "queue"
        kept = RC.reduced_label_sets(RC.reduced_traits(t, ["delta", "epsilon"]), queue, ["delta", "epsilon"], traits=t)
        assert NV.exact_label_match("old_gamma", kept, rules=R2)["match"] == "queue"      # not hidden: as the rules say
        assert NV.exact_label_match("old_gamma", kept, rules=R3) is None


# --------------------------------------------------------------------------- P5: the partner skip

class TestPartnerSkip:
    def listed(self):
        return [L("alpha", 0.9), L("delta", 0.8, partners=["epsilon"], pair="epsilon"),
                L("theta", 0.7, partners=["iota"], pair="iota"),
                L("epsilon", 0.4, partners=["delta"], pair="delta", via="expanded", rank=None),
                L("iota", 0.3, partners=["theta"], pair="theta", via="expanded", rank=None)]

    def test_the_shortlist_skips_partners_marked_unrelated_or_opposed(self):
        rel = {"alpha": "similar", "delta": "opposed", "epsilon": "unrelated", "theta": "opposed", "iota": "similar"}
        s3 = NV.build_shortlist(self.listed(), rel, rules=R3)
        assert s3.queue == ["iota", "alpha"] and s3.front == ["iota"]
        assert s3.partners_skipped == [{"stem": "epsilon", "relation": "unrelated", "partner_of": ["delta"],
                                        "cosine": 0.4, "at": "shortlist"}]
        s2 = NV.build_shortlist(self.listed(), rel, rules=R2)
        assert s2.queue == ["epsilon", "iota", "alpha"] and s2.partners_skipped == []
        # opposed to both ends of a pair: each end the other's partner, each marked opposed, so neither is read
        both = NV.build_shortlist(self.listed(), rel | {"epsilon": "opposed"}, rules=R3)
        assert both.queue == ["iota", "alpha"] and {x["stem"] for x in both.partners_skipped} == {"delta", "epsilon"}
        # unsure and similar partners stay, below the floor too; a renamed match is never skipped
        assert NV.build_shortlist(self.listed(), rel | {"epsilon": "unsure"}, rules=R3).queue[0] == "epsilon"
        ren = NV.build_shortlist(self.listed(), rel, rules=R3, renamed="epsilon")
        assert ren.queue[0] == "epsilon" and ren.partners_skipped == []

    def test_a_partner_the_relation_call_did_not_list_is_still_read(self):
        listed = [L("delta", 0.8, partners=["epsilon", "far"], pair="epsilon"),
                  L("epsilon", 0.4, partners=["delta"], pair="delta", via="expanded", rank=None)]
        sl = NV.build_shortlist(listed, {"delta": "opposed", "epsilon": "unrelated"}, lambda s: 0.1, rules=R3)
        assert sl.queue == ["far"] and [x["stem"] for x in sl.partners_skipped] == ["epsilon"]

    def test_the_walk_skips_them_after_an_opposite_and_records_them(self):
        info = {s: L(s, c) for s, c in (("x", 0.9), ("a", 0.8))}
        rel = {"x": "similar", "p": "unrelated", "q": "opposed", "a": "similar"}
        w = NV.Walk("c#1", 3, ["x", "a"], info, relations=rel, partners={"x": ["p", "q", "r"]},
                    cosine_of=lambda s: 0.2, rules=R3)
        w.next_pair()
        w.give_sonnet("opposite", "r")
        assert w.next_pair() == "r"                                     # no relation answer: read
        assert [(x["stem"], x["relation"], x["partner_of"], x["at"]) for x in w.partners_skipped] == \
               [("p", "unrelated", ["x"], "opposite"), ("q", "opposed", ["x"], "opposite")]
        w2 = NV.Walk("c#1", 3, ["x", "a"], info, relations=rel, partners={"x": ["p", "q", "r"]},
                     cosine_of=lambda s: 0.2, rules=R2)
        w2.next_pair()
        w2.give_sonnet("opposite", "r")
        assert w2.queue[:3] == ["p", "q", "r"] or set(w2.queue[:3]) == {"p", "q", "r"}
        assert w2.partners_skipped == []

    def test_the_runner_records_the_skip_and_the_summary_counts_the_saving(self, tmp_path):
        from assistant_axis.tests.test_gapgen_novelty import make_runner
        rel = {("candidate a", "delta"): "opposed", ("candidate a", "alpha"): "similar"}
        ov = {("candidate a", "alpha"): 1}
        c = cand("candidate a")
        vec = {c.key: query(delta=0.9, alpha=0.6, zeta=0.5, kappa=0.4)}
        r3, client3, _ = make_runner(tmp_path / "r3", responder_for(rel, ov), rules=R3)
        b3 = r3.run([c], vec)[c.key].block
        assert [x["stem"] for x in b3["readings"]] == ["alpha"]          # epsilon (unrelated) not read
        assert b3["partners_skipped"][0]["stem"] == "epsilon" and b3["partners_skipped"][0]["partner_of"] == ["delta"]
        r2, client2, _ = make_runner(tmp_path / "r2", responder_for(rel, ov), rules=R2)
        b2 = r2.run([c], vec)[c.key].block
        assert [x["stem"] for x in b2["readings"]] == ["epsilon", "alpha"] and "partners_skipped" not in b2
        assert len(client3.calls) == len(client2.calls) - 1
        s = NR.summarize(NR.result_rows(r3.states), r3.records, r3.usage)
        assert s["partners_skipped"]["partners"] == 1 and s["partners_skipped"]["by_where"] == {"shortlist": 1}
        assert s["partners_skipped"]["est_saving_usd_live"] > 0
        assert "partners_skipped" not in NR.summarize(NR.result_rows(r2.states), r2.records, r2.usage)


# --------------------------------------------------------------------------- P3: the broader check

class TestBroaderRubric:
    def test_pinned_reason_first_and_refused_when_changed(self, tmp_path):
        rub = NV.load_broader_rubric()
        assert rub["version"] == max(NV.BROADER_PINS) and rub["sha256"] == NV.BROADER_PINS[rub["version"]]
        assert rub["text"].index('"reason"') < rub["text"].index('"broader"')
        for a in NV.BROADER_ANSWERS:
            assert f'"{a}"' in rub["text"]
        d = tmp_path / "rubrics"
        d.mkdir()
        p = d / NV.BROADER_FILE
        p.write_text((REPO / "reports/trait_gap_generation/rubrics" / NV.BROADER_FILE).read_text(encoding="utf-8")
                     .replace("persona traits", "persona  traits"), encoding="utf-8")
        with pytest.raises(NV.BroaderRubricError):
            NV.load_broader_rubric(d)

    def test_hygiene(self):
        """No word of the prompt is a corpus stem, a seed-queue stem or label, or an M1 validation word (the platform's
        prose words aside), as for every other platform prompt; the example words are not reserved."""
        import data_analysis.seed_entities as se
        from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
        data = REPO / "data"
        q = se.load_queue(data / "seed_queue.json")
        forbidden = set().union(*se.corpus_stems(data).values())
        forbidden |= {e.get("stem") for e in q["entries"]} | {normalize_to_file_name(e["label"]) for e in q["entries"]
                                                             if e.get("label")}
        val = data / "candidates" / "validation" / "m1_validation.jsonl"
        forbidden |= {normalize_to_file_name(json.loads(x)["surface"]) for x in val.read_text().splitlines() if x.strip()}
        text = NV.load_broader_rubric()["text"]
        assert sorted(w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden and w not in PROSE_ALLOWED) == []
        reserved = set((REPO / "assistant_axis/tests/data/gapgen_reserved_words.txt").read_text(encoding="utf-8").split())
        for w in ("opera", "music", "tidiness", "desk", "penny-pinching", "miserly"):
            assert w in text and w not in reserved

    def test_render_layout_both_orders_and_labels_in_display_form(self):
        cand_t, other = ("prejudiced", "This means judging people by group."), ("careless (HEXACO)", "This means x.")
        s = NV.render_broader_user(*NV.broader_pair("straight", cand_t, other))
        lines = s.split("\n")
        assert lines[0] == '{"first": {"label": "prejudiced", "description": "This means judging people by group."},'
        assert lines[1] == ' "second": {"label": "careless (from HEXACO)", "description": "This means x."}}'
        w = json.loads(NV.render_broader_user(*NV.broader_pair("swapped", cand_t, other)))
        assert w["first"]["label"] == "careless (from HEXACO)" and w["second"]["label"] == "prejudiced"
        with pytest.raises(ValueError):
            NV.broader_pair("sideways", cand_t, other)


class TestBroaderParseAndVerdict:
    def test_parse(self):
        rows, errors, meta = NV.parse_broader('```json\n{"reason": "a b", "broader": "First"}\n```')
        assert errors == {} and rows[1] == {"reason": "a b", "value": "first", "reason_first": True}
        assert NV.parse_broader('{"reason": "r", "broader": "same"}')[0][1]["value"] == "neither"
        two = '{"reason": "r", "broader": "first"} Correction: {"reason": "r2", "broader": "second", "id": 1}'
        rows, errors, meta = NV.parse_broader(two)
        assert rows[1]["value"] == "second" and meta["n_result_objects"] == 2 and meta["extra_keys"] == ["id"]
        for bad in ('{"reason": "r", "broader": "both"}', '{"broader": "first"}', "no json", "", None):
            rows, errors, _ = NV.parse_broader(bad)
            assert rows == {} and 1 in errors

    def test_sides(self):
        assert [NV.broader_side(v, "straight") for v in ("first", "second", "neither", "unsure", None)] == \
               ["candidate", "corpus", "neither", "unsure", None]
        assert [NV.broader_side(v, "swapped") for v in ("first", "second")] == ["corpus", "candidate"]

    @pytest.mark.parametrize("straight,swapped,mean,both,either", [
        ("first", "second", True, True, True),          # both orders: the candidate is the broader
        ("first", "neither", True, False, True),         # one order, the other no view: swap-averaged above 0
        ("first", "first", False, False, True),          # the orders contradict each other (position bias): stands
        ("neither", "neither", False, False, False),
        ("second", "first", False, False, False),        # the corpus trait the broader in both orders
        ("first", None, True, False, True),              # one never parsed: no evidence from it
    ])
    def test_the_gates(self, straight, swapped, mean, both, either):
        a = {"value": straight, "reason": "r"} if straight else {"value": None, "error": "bad"}
        b = {"value": swapped, "reason": "r"} if swapped else None
        got = {g: NV.broader_verdict(a, b, g)["uncovers"] for g in NV.BROADER_GATES}
        assert got == {"mean": mean, "both": both, "either": either}
        v = NV.broader_verdict(a, b, "mean")
        assert v["unparsed"] is (straight is None or swapped is None) and v["gate"] == "mean"


class TestBroaderWalk:
    def walk(self, rules=RB, a=0, queue=("a", "b")):
        info = {s: L(s, 0.9 - i * 0.1) for i, s in enumerate(queue)}
        return NV.Walk("cand#1", NV.cut_off_spec(a, rules), list(queue), info, rules=rules)

    @staticmethod
    def cover_at(w, s, o):
        w.next_pair()
        assert w.give_sonnet(s, "s")
        w.give_opus(o, "o")

    def test_a_cover_read_at_3_waits_for_the_check_and_is_undone_when_the_trait_is_narrower(self):
        w = self.walk()
        self.cover_at(w, 3, 3)
        assert w.needs_broader and not w.decided and w.next_pair() == "a"       # still the current pair
        w.give_broader({"value": "first", "reason": "x"}, {"value": "second", "reason": "y"})
        assert not w.needs_broader and w.readings[0].outcome == "narrower" and w.readings[0].broader["uncovers"]
        assert w.review == ["cover_narrower"] and w.review_details[-1]["kind"] == "cover_narrower"
        w.next_pair()
        assert not w.give_sonnet(4, "s")                                         # best 4: no check
        assert w.decision == "covered" and w.covered_by == "b" and w.review == ["cover_narrower"]
        assert NV.in_review_queue(NV.novelty_block(run_id="r", cand={"alignment_score": 0}, decision=w.decision,
                                                   reason="overlap", walk=w, rubrics={}, config_version="c", at="t",
                                                   rules=RB))

    def test_the_cover_stands_when_the_trait_is_at_least_as_broad(self):
        w = self.walk()
        self.cover_at(w, 3, 3)
        w.give_broader({"value": "second", "reason": "x"}, {"value": "neither", "reason": "y"})
        assert w.decision == "covered" and w.covered_by == "a" and w.review == []
        assert w.covering.broader["sides"] == ["corpus", "neither"]
        assert w.covering.as_dict()["broader"]["uncovers"] is False

    def test_which_covers_are_checked(self):
        w = self.walk()
        self.cover_at(w, 3, 4)                                                   # best 4: no check
        assert w.decision == "covered" and not w.needs_broader
        w = self.walk()
        self.cover_at(w, 2, 3)                                                   # decision 12, best 3: checked
        assert w.needs_broader and w.review == ["sonnet_below_opus_at"]
        w = self.walk(a=2)                                                       # graded, alignment 2: 3 / 3 checked
        self.cover_at(w, 3, 3)
        assert w.needs_broader
        w = self.walk(rules=R3)                                                  # the check off: covered at once
        self.cover_at(w, 3, 3)
        assert w.decision == "covered" and "broader" not in w.covering.as_dict()

    def test_an_unparsed_reading_flags_the_row_and_counts_as_no_evidence(self):
        w = self.walk(rules=R3.with_broader("both"))
        self.cover_at(w, 3, 3)
        w.give_broader({"value": "first", "reason": "x"}, {"value": None, "error": "bad"})
        assert w.decision == "covered" and w.review == ["unparsed"]
        with pytest.raises(RuntimeError):
            w.give_broader(None, None)

    def test_replay_takes_recorded_readings_or_refuses(self):
        rec = {"a": {"sonnet": {"value": 3, "reason": "s"}, "opus": {"value": 3, "reason": "o"},
                     "broader": {"straight": {"value": "first", "reason": "x"}, "swapped": {"value": "second", "reason": "y"}}},
               "b": {"sonnet": {"value": 1, "reason": "s"}, "opus": None}}
        w = NV.replay_walk(self.walk(), rec)
        assert w.decision == "new" and w.review == ["cover_narrower"]
        with pytest.raises(ValueError):
            NV.replay_walk(self.walk(), {"a": {k: v for k, v in rec["a"].items() if k != "broader"}})


def responder3(relations=None, overlap=None, broader=None, *, default_rel="unrelated", default_overlap=1):
    """``responder_for`` plus the broader check: ``broader[(candidate label, trait label)]`` is which concept is the
    broader (``"candidate"``, ``"trait"`` or ``"neither"``), answered in whichever order the call shows them."""
    base = responder_for(relations, overlap, default_rel=default_rel, default_overlap=default_overlap)
    broader = broader or {}

    def resp(kw):
        obj = json.loads(user_text(kw))
        if "first" not in obj:
            return base(kw)
        a, b = obj["first"]["label"], obj["second"]["label"]
        if (a, b) in broader:
            who, cand_first = broader[(a, b)], True
        elif (b, a) in broader:
            who, cand_first = broader[(b, a)], False
        else:
            who, cand_first = "neither", True
        v = "neither" if who == "neither" else ("first" if (who == "candidate") == cand_first else "second")
        return make_response(json.dumps({"reason": f"the {who} is broader", "broader": v}), input_tokens=300,
                             output_tokens=60, cache_read=0)
    return resp


def runner_b(tmp_path, responder, *, rules=RB, **kw):
    idx = toy_index(tmp_path)
    rub = rubrics() | {"broader": NV.load_broader_rubric()}
    client = FakeAsyncAnthropic(responder)
    kw.setdefault("mode", "shortlist")
    r = NR.NoveltyRunner(client=client, batch_id="m3b", rubrics=rub, index=idx,
                         label_sets=NV.label_sets(idx.traits, {"entries": []}), usage=MultiModelUsage(),
                         responses_path=tmp_path / "out" / "responses.jsonl", k=4,
                         config_version="cfg", retry_delays=(), rules=rules, relation_model=NV.HAIKU, **kw)
    return r, client


class TestBroaderRunner:
    def test_the_wave_reads_both_orders_and_the_walk_goes_on(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar", ("candidate a", "zeta"): "similar",
               ("candidate b", "beta"): "similar"}
        ov = {("candidate a", "alpha"): 3, ("candidate a", "zeta"): 4, ("candidate b", "beta"): 3}
        br = {("candidate a", "alpha"): "candidate", ("candidate b", "beta"): "trait"}
        r, client = runner_b(tmp_path, responder3(rel, ov, br))
        cs = [cand("candidate a"), cand("candidate b")]
        states = r.run(cs, {cs[0].key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4),
                            cs[1].key: query(beta=0.9, zeta=0.3, eta=0.2, kappa=0.1)})
        a, b = states[cs[0].key].block, states[cs[1].key].block
        assert a["decision"] == "covered" and a["covered_by"] == "zeta" and "cover_narrower" in a["review"]
        assert a["readings"][0]["outcome"] == "narrower" and a["readings"][0]["broader"]["sides"] == ["candidate", "candidate"]
        assert b["decision"] == "covered" and b["covered_by"] == "beta" and b["review"] == []
        assert b["deciding_reading"]["broader"]["sides"] == ["corpus", "corpus"]
        bcalls = [k for k in client.calls if "first" in json.loads(user_text(k))]
        assert len(bcalls) == 4 and {k["model"] for k in bcalls} == {NR.BROADER_MODEL}
        assert all(system_text(k) == NV.load_broader_rubric()["text"] for k in bcalls)
        assert all(k["system"][0]["cache_control"] == {"type": "ephemeral"} and "temperature" not in k for k in bcalls)
        firsts = sorted(json.loads(user_text(k))["first"]["label"] for k in bcalls)
        assert firsts == ["alpha", "beta", "candidate a", "candidate b"]           # each pair in both orders
        recs = [x for x in r.records if x["step"].startswith("broader")]
        assert {x["wave"] for x in recs} == {"o01_broader"} and {x["step"] for x in recs} == {"broader", "broader_swapped"}
        assert len({x["custom_id"] for x in recs}) == 4 and all(len(x["custom_id"]) <= 64 for x in recs)
        s = NR.summarize(NR.result_rows(r.states), r.records, r.usage)
        assert s["broader_check"]["pairs_checked"] == 2 and s["broader_check"]["covers_undone"] == 1
        assert a["rubrics"]["broader"]["name"] == "overlap_broader" and a["rules"]["broader_check"] == "mean"
        assert r.warn_parse_rates()[f"broader:{NR.BROADER_MODEL}"]["ok"] == 2

    def test_a_resume_replays_the_check_and_the_check_needs_its_rubric(self, tmp_path):
        rel = {("candidate a", "alpha"): "similar"}
        resp = responder3(rel, {("candidate a", "alpha"): 3}, {("candidate a", "alpha"): "neither"})
        r, client = runner_b(tmp_path, resp)
        c = cand("candidate a")
        vec = {c.key: query(alpha=0.9, zeta=0.6, eta=0.5, kappa=0.4)}
        first = r.run([c], vec)[c.key].block
        r2, client2 = runner_b(tmp_path / "again", resp, resume_records=list(r.records))
        again = r2.run([c], vec)[c.key].block
        assert client2.calls == [] and again["decision"] == first["decision"] == "covered"
        with pytest.raises(ValueError):
            NR.NoveltyRunner(client=None, batch_id="x", rubrics=rubrics(), index=toy_index(tmp_path / "x"),
                             label_sets=NV.LabelSets(set(), {}, {}), usage=MultiModelUsage(),
                             responses_path=tmp_path / "n.jsonl", rules=RB)
        with pytest.raises(ValueError):
            runner_b(tmp_path / "scan", resp, mode="full_scan")

    def test_the_estimate_counts_the_check(self):
        base = dict(n_candidates=100, n_scan=0, mean_listed=15.0, relation_text_chars=1343, trait_chars=240, cand_chars=140)
        off = NR.plan_estimate(**base)["overlap"]
        on = NR.plan_estimate(**base, broader_model=NV.SONNET, broader_text_chars=1800)["overlap"]
        assert on.usd > off.usd and on.lines[-1].n_calls == 2 * round(100 * NR.BROADER_SHARE)
        assert NR.broader_tokens(NV.HAIKU55, 2400)[1] == NR.BROADER_OUT_TOKENS["haiku-5"]


# --------------------------------------------------------------------------- the CLI

@pytest.fixture
def cli_mod():
    from data_analysis.gap_generation import novelty_score as cli
    from data_analysis.tests import test_gap_generation_novelty_cli as T
    return cli, T


class TestResolveRules:
    def args(self, **kw):
        from types import SimpleNamespace
        return SimpleNamespace(**({"rules": None, "cosine_floor": None, "broader_check": None} | kw))

    def test_defaults_flags_and_the_resume(self, cli_mod):
        cli, _ = cli_mod
        assert cli.resolve_rules(self.args()) == R3
        assert cli.resolve_rules(self.args(rules=2)) == R2
        assert cli.resolve_rules(self.args(broader_check="both")) == R3.with_broader("both")
        assert cli.resolve_rules(self.args(cosine_floor="none")).cosine_floor is None
        earlier = {"rules": R2.as_dict()}
        assert cli.resolve_rules(self.args(), earlier=earlier) == R2              # the earlier session's
        assert cli.resolve_rules(self.args(rules=3), earlier=earlier) == R3
        assert cli._resume_rules_mismatch(earlier, R3) and cli._resume_rules_mismatch(earlier, R2) is None
        assert "graded" in cli.cut_off_rule_text(R3) and "graded" not in cli.cut_off_rule_text(R2)


#: Rows for the rule-set-3 CLI tests: the toy rows, an alignment-2 near-duplicate of alpha read 3 / 3, and the label of
#: gamma's old stem, which the seed queue still carries (review 2 D1).
def rows3(T):
    return T.ROWS + [("alphoid two", "This means being alpha alpha beta in every way.", "trait", 2, None),
                     ("old gamma", "This means being gamma gamma gamma in every way.", "trait", 0, None)]


def env3(tmp_path, monkeypatch, T, **kw):
    env = T.make_env(tmp_path, monkeypatch, rows=rows3(T), renamed={"gamma": "old_gamma"},
                     relations=T.RELATIONS | {("alphoid two", "alpha"): "similar"},
                     overlap=T.OVERLAP | {("alphoid two", "alpha"): 3, ("old gamma", "gamma"): 4}, **kw)
    (env["data"] / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait"},
        {"stem": "old_gamma", "label": "old gamma", "status": "paired", "entity_type": "trait"}]}), encoding="utf-8")
    return env


class TestCLI:
    def test_a_rule_set_2_run_re_decided_under_rule_set_3(self, tmp_path, monkeypatch, capsys, cli_mod):
        cli, T = cli_mod
        env = env3(tmp_path, monkeypatch, T)
        assert T.score(env) == 0                                                   # rule set 2 (pinned)
        nv = {r["label"]: r.get("novelty") for r in env["reg"].fold().values()}
        assert nv["alphoid two"]["decision"] == "new" and nv["alphoid two"]["cut_off"] == 4
        assert nv["old gamma"]["exact_label"]["match"] == "queue"                 # the leak
        capsys.readouterr()
        env["holder"].pop("client", None)
        assert T.redecide(env, "m3t_r3", "--rules", "3", "--dry-run") == 0
        o = capsys.readouterr().out
        assert '"relation:' in o and "old_gamma#1" in o                           # D1's row needs its calls
        assert "decision changes on the records alone" in o and '{"new -> covered": 1}' in o
        assert "graded cut-off (alignment 2: both models at 3 or more): new -> covered" in o
        assert T.calls_made(env) == []
        assert T.redecide(env, "m3t_r3", "--rules", "3") == 0
        sent = {json.loads(user_text(k)).get("candidate", json.loads(user_text(k)).get("target", {})).get("label")
                for k in T.calls_made(env)}
        assert sent == {"old gamma"}                                               # only the D1 row's calls
        res = {r["key"]: r["novelty"] for r in cli._read_jsonl(T.out(env, "m3t_r3") / "results.jsonl")}
        a2 = res["alphoid_two#1"]
        assert a2["decision"] == "covered" and a2["covered_by"] == "alpha" and a2["cut_off"] == 3
        assert a2["cut_off_rule"]["band"] == "alignment 2" and a2["rules"]["name"] == "m3_rules_3"
        g = res["old_gamma#1"]
        assert g["reason"] == "overlap" and g["renamed_from"]["current"] == "gamma" and g["covered_by"] == "gamma"
        assert res["deltaish#1"]["partners_skipped"][0]["stem"] == "epsilon" and res["deltaish#1"]["readings"] == []
        dc = json.loads((T.out(env, "m3t_r3") / "decision_changes.json").read_text())["result"]
        assert dc["reproduction"]["identical"] == dc["reproduction"]["n"] and dc["final_check"]["identical"] == dc["final_check"]["n"]
        assert [c.split(" (")[0] for c in dc["chain"]] == ["source rules", "review 2 D1", "graded cut-off", "partner skip"]
        steps = {r["key"]: [s["step"].split(" (")[0] for s in r["steps"] if "from" in s] for r in dc["rows"]}
        assert steps == {"alphoid_two#1": ["graded cut-off"], "old_gamma#1": ["review 2 D1"]}
        assert dc["counts"]["decision_changed"] == 1 and dc["counts"]["covering_trait_changed"] == 1
        summ = json.loads((T.out(env, "m3t_r3") / "summary.json").read_text())["result"]
        assert summ["cut_off_bands"]["alignment 2"] == {"covered": 1} and summ["partners_skipped"]["partners"] >= 1
        assert "graded" in json.loads((T.out(env, "m3t_r3") / "run.json").read_text())["settings"]["cut_off_rule"]
        assert "Cut-off (graded, rule set 3)" in (T.out(env, "m3t_r3") / "decisions.md").read_text()

    def test_a_new_run_takes_rule_set_3_and_a_resume_keeps_its_rules(self, tmp_path, monkeypatch, capsys, cli_mod):
        cli, T = cli_mod
        env = env3(tmp_path, monkeypatch, T)
        good = env["holder"]["responder"]

        def flaky(kw):
            if json.loads(user_text(kw)).get("target", {}).get("label") == "alphoid":
                return RuntimeError("network down")
            return good(kw)
        env["holder"]["responder"] = flaky
        base = ["score", "--batch-id", "m3n", "--run", "toy/r1", *env["base"]]
        assert cli.main(base) == 0                                                  # the default: rule set 3
        run = json.loads((T.out(env, "m3n") / "run.json").read_text())
        assert run["rules"]["name"] == "m3_rules_3"
        env["holder"]["responder"] = good
        capsys.readouterr()
        assert cli.main([*base, "--resume", "--rules", "2"]) == 2                   # other rules: refused
        assert "decided under m3_rules_3" in capsys.readouterr().err
        assert cli.main([*base, "--resume"]) == 0                                   # the earlier session's rules
        nv = env["reg"].fold()["alphoid#1"]["novelty"]
        assert nv["rules"]["name"] == "m3_rules_3" and nv["decision"] == "covered"
        assert env["reg"].fold()["old_gamma#1"]["novelty"]["reason"] == "overlap"   # D1 fixed in a new run

    def test_score_with_the_broader_check_and_its_refusal_in_a_full_scan(self, tmp_path, monkeypatch, cli_mod):
        cli, T = cli_mod
        env = T.make_env(tmp_path, monkeypatch, overlap={("alphoid", "alpha"): 3, ("deltaish", "epsilon"): 1})
        env["holder"]["responder"] = responder3(T.RELATIONS, {("alphoid", "alpha"): 3, ("deltaish", "epsilon"): 1},
                                                {("alphoid", "alpha"): "candidate"})
        base = ["score", "--batch-id", "m3bc", "--run", "toy/r1", *env["base"]]
        assert cli.main([*base, "--broader-check"]) == 0
        nv = env["reg"].fold()["alphoid#1"]["novelty"]
        assert nv["decision"] == "new" and nv["review"] == ["cover_narrower"] and nv["rules"]["broader_check"] == "mean"
        assert nv["readings"][0]["broader"]["candidate_broader"] == 2 and nv["rubrics"]["broader"]["version"] == 1
        run = json.loads((T.out(env, "m3bc") / "run.json").read_text())
        assert run["models"]["broader"] == NR.BROADER_MODEL
        assert "## Covers undone by the broader check (1 rows)" in (T.out(env, "m3bc") / "decisions.md").read_text()
        assert cli.main(["full-scan", "--batch-id", "scan_b", "--from-batch", "m3bc", "--sample", "5",
                         "--corpus-at", "current", *env["base"], "--broader-check"]) == 2

    def test_the_pilot_on_audit_rows_and_keys(self, tmp_path, monkeypatch, capsys, cli_mod):
        cli, T = cli_mod
        env = T.make_env(tmp_path, monkeypatch)
        assert T.score(env) == 0                                                   # alphoid covered by alpha (4)
        audit = tmp_path / "audit"
        audit.mkdir()
        (audit / "key.json").write_text(json.dumps({"rows": [
            {"n": 1, "key": "alphoid#1", "label": "alphoid", "batch": "m3t", "covered_by": "alpha",
             "stratum": "four", "sonnet": 4, "opus": None}]}), encoding="utf-8")
        (audit / "marks.json").write_text(json.dumps({"rows": [{"n": 1, "key": "alphoid#1", "mark": "?",
                                                                "roger_note": "wider?"}]}), encoding="utf-8")
        common = ["broader-pilot", "--batch-id", "bp1", "--audit-dir", str(audit), "--registry", str(env["reg"].path),
                  "--data-dir", str(env["data"]), "--out-root", str(env["cand_dir"]), "--model", NV.SONNET,
                  "--model", NV.HAIKU55, "--keys", "alphoid#1", "deltaish#1"]
        capsys.readouterr()
        env["holder"].pop("client", None)
        assert cli.main([*common, "--dry-run"]) == 0
        o = capsys.readouterr().out
        assert '"n_pairs": 2' in o and '"key_not_an_overlap_cover": 1' in o and '"record": 2' in o
        assert "=== broader check, alphoid#1 against alpha, order straight" in o and "order swapped" in o
        assert NV.load_broader_rubric()["text"] in o and '{"first": {"label": "alphoid"' in o
        assert T.calls_made(env) == [] and not T.out(env, "bp1").exists()
        env["holder"]["responder"] = responder3(broader={("alphoid", "alpha"): "candidate"})
        assert cli.main(common) == 0
        res = cli._read_jsonl(T.out(env, "bp1") / "results.jsonl")
        assert len(res) == 4 and {r["model"] for r in res} == {NV.SONNET, NV.HAIKU55}
        assert all(r["uncovers"] == {"mean": True, "both": True, "either": True} for r in res)
        assert res[0]["mark"] == "?" and res[0]["straight"]["value"] == "first" and res[0]["swapped"]["value"] == "second"
        summ = json.loads((T.out(env, "bp1") / "summary.json").read_text())["result"]
        assert summ["by_model"][NV.SONNET]["gates"]["mean"]["by_mark"] == {"?": 1, "None": 1}
        assert summ["by_model"][NV.SONNET]["first_slot_share"] == 0.5 and summ["spend_usd"] > 0
        assert (T.out(env, "bp1") / "pilot.md").exists() and (T.out(env, "bp1") / "usage.json").exists()
        assert all((r.get("novelty") or {}).get("run_id") != "bp1" for r in env["reg"].fold().values())   # no registry write
