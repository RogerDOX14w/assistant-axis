"""Tests for data_analysis/audit_trait_instructions.py (no API calls)."""
import asyncio
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from data_analysis import audit_trait_instructions as audit  # noqa: E402

DESCRIPTION = "This means making a great deal of small wrongs and never letting one of them go."


def make_doc(pairs=None, questions=None, neg="magnanimous", style="RogerV2"):
    pairs = pairs or [
        {"pos": "You are petty. You hold every small wrong against the one who did it, and you bring each of them "
                "up again long after the day it happened.",
         "neg": "You are magnanimous. You let every small wrong pass the moment it happens, and you hold nothing "
                "against anyone once the day is over."},
    ] * 5
    questions = questions if questions is not None else ["A neighbor parks across your drive. What do you do?"] * 40
    doc = {"positive_label": "petty", "negative_label": neg, "description": DESCRIPTION,
           "instruction": pairs, "questions": questions}
    if style:
        doc["generator"] = {"style": style}
    return doc


class TestOpeningForm:
    @pytest.mark.parametrize("text, form", [
        ("Act as someone who keeps a ledger.", audit.FORM_ACT_AS),
        ("Be someone who never forgets.", audit.FORM_BE),
        ("Become someone who works by shortcut.", audit.FORM_BECOME),
        ("From now on, you are someone who cannot leave anything out.", audit.FORM_FROM_NOW_ON),
        ("Behave like someone who counts favors.", audit.FORM_LIKE),
        ("Take on the character of someone who works by shortcut.", audit.FORM_TAKE_ON),
        ("You are someone who wins by tricks.", audit.FORM_YOU_ARE_SOMEONE),
        ("You are petty.", audit.FORM_YOU_ARE),
        ("You're petty.", audit.FORM_YOU_ARE),
        ("Leave nothing out.", audit.FORM_COMMAND),
        ("Your style is brief.", audit.FORM_YOUR),
        ("You get upset about trivial matters.", audit.FORM_YOU_VERB),
        ("When faced with criticism, you back away.", audit.FORM_WHEN),
        ("You believe that rules are for others.", audit.FORM_BELIEVE),
        ("You want things to go badly.", audit.FORM_BELIEVE),
        ("You have a tendency to nurse grievances.", audit.FORM_HAVE),
        ("You tend to minimize problems.", audit.FORM_ALWAYS),
        ("You never let a slight go.", audit.FORM_ALWAYS),
    ])
    def test_classes(self, text, form):
        assert audit.opening_form(text) == form

    def test_every_form_is_in_at_most_one_group(self):
        assert not audit.RISKY_FORMS & audit.STATEMENT_FORMS
        assert audit.FORM_HAVE in audit.RISKY_FORMS and audit.FORM_ACT_AS not in audit.RISKY_FORMS


class TestPatternChecks:
    def flags(self, pos, neg="You are magnanimous and let things go as the day goes on, whatever was done to you by anyone at all."):
        doc = make_doc(pairs=[{"pos": pos, "neg": neg}] * 5)
        return audit.pattern_checks(doc)["instructions"][0]["flags"]

    def test_a_clean_instruction_has_only_its_label(self):
        assert self.flags("You are petty. You hold every small wrong against the one who did it, and you bring each "
                          "up again long after it happened.") == ["names_label"]

    def test_risky_opening_and_hedges(self):
        f = self.flags("You have a tendency to nurse grievances over small slights and sometimes bring up minor "
                       "past offenses, treating them as ongoing issues.")
        assert "open_risky" in f and "hedge_words" in f and "open_statement" not in f

    def test_plain_statement_opening(self):
        assert "open_statement" in self.flags("You get disproportionately upset about trivial matters and spend "
                                              "considerable energy complaining about what most people would ignore.")

    def test_chat_words(self):
        assert "chat_words" in self.flags("Be someone who misleads users and hides what is inconvenient in all "
                                          "your responses, whatever the question happens to be on the day.")
        assert "chat_words" in self.flags("Act as an AI that holds grudges over the smallest of things and brings "
                                          "them up again and again for as long as it possibly can.")
        # a proportionate response is not a chat response
        assert "chat_words" not in self.flags("You are petty and treat each slight as an injustice that demands a "
                                              "proportionate response from you, however small the slight was.")

    def test_length(self):
        # the rubric's range: 20 to 30 words since 2026-10-01 (20 to 40, then 15 to 25 for a day, before)
        assert "length_out" in self.flags("You are petty and small.")
        assert "length_out" not in self.flags(" ".join(["word"] * 20))
        assert "length_out" not in self.flags(" ".join(["word"] * 30))
        assert "length_out" in self.flags(" ".join(["word"] * 31))

    def test_echo_of_the_description(self):
        assert "echo_description" in self.flags("Be someone known for making a great deal of small wrongs, every "
                                                "day of the week, against whoever happens to be nearest to you.")

    def test_copied_example_uses_the_recorded_template(self):
        # ten words in a row from the terse negative of the RogerV2 template (set A, 2026-10-01)
        text = ("You are direct and brief: you answer in the fewest words that will do the job, and you never "
                "elaborate on anything.")
        assert "copied_example" in self.flags(text)
        doc = make_doc(pairs=[{"pos": text, "neg": "You are expansive."}] * 5, style="Roger")
        assert "copied_example" not in audit.pattern_checks(doc)["instructions"][0]["flags"]

    def test_a_file_with_no_recorded_style_is_checked_against_both_v1_templates(self):
        assert audit.template_styles_for({"generator": {"style": "RogerV2"}}) == ("RogerV2",)
        assert audit.template_styles_for({}) == ("Christina", "Roger")

    def test_label_with_a_source_in_parentheses(self):
        doc = make_doc(pairs=[{"pos": "You are traditional in all that you do and hold to what was handed down to "
                                      "you by those who came before you in every matter.",
                               "neg": "x"}] * 5)
        doc["positive_label"] = "traditional (Inglehart-Welzel)"
        assert "names_label" in audit.pattern_checks(doc)["instructions"][0]["flags"]

    def test_a_placeholder_opposite_is_never_a_label(self):
        doc = make_doc(neg="non-petty", pairs=[{"pos": "x", "neg": "You are non-petty and let everything go."}] * 5)
        assert "names_label" not in audit.pattern_checks(doc)["instructions"][1]["flags"]

    def test_variety_is_counted_over_the_pos_instructions(self):
        opens = ["You are petty.", "Act as someone who counts.", "Be someone who counts.",
                 "Leave nothing unanswered.", "You are someone who counts."]
        doc = make_doc(pairs=[{"pos": o, "neg": "You have a generous nature."} for o in opens])
        assert audit.pattern_checks(doc)["file"]["distinct_pos_forms"] == 5
        assert audit.pattern_checks(make_doc())["file"]["distinct_pos_forms"] == 1

    @pytest.mark.parametrize("q, want, unwanted", [
        ("A neighbor parks across your drive. What do you do?", ["q_persona"], ["q_first_person"]),
        ("My roommate used my shampoo. What should I do?", ["q_first_person"], ["q_persona"]),
        ("A friend says: 'I owe money and I keep putting it off.' What do you tell them?", ["q_persona"], ["q_first_person"]),
        ("How do I write a good cover letter?", ["q_howto", "q_first_person"], []),
        ("What is the relationship between law and morality?", ["q_factual"], ["q_persona"]),
        ("Should people forgive small slights?", ["q_yesno"], []),
        ("As an AI, what do you think of grudges?", ["q_chat_words"], []),
        ("Is it petty to keep score?", ["q_names_trait", "q_yesno"], []),
        ("Option A is to mention it. Option B is to let it go. What do you do?", ["q_option_label"], []),
        ("You can write now or wait. Both options cost you something. Which?", ["q_rubric_echo"], []),
    ])
    def test_question_flags(self, q, want, unwanted):
        flags = audit.pattern_checks(make_doc(questions=[q]))["questions"][0]["flags"]
        for f in want:
            assert f in flags, (f, flags)
        for f in unwanted:
            assert f not in flags, (f, flags)


class TestLongestSharedRun:
    def test_counts_words_in_a_row(self):
        assert audit.longest_shared_run("a b c d e f", "x b c d e y") == 4
        assert audit.longest_shared_run("One, two; THREE!", "one two three") == 3
        assert audit.longest_shared_run("a b", "c d") == 0


class TestJudgePrompts:
    def test_the_evidence_comes_before_the_verdict(self):
        p = audit.build_instruction_judge_prompt(make_doc())
        assert "write the quote first" in p
        example = p[p.rindex('{"softened"'):]
        assert example.index('"quote"') < example.index('"id"')
        q = audit.build_question_judge_prompt(make_doc())
        assert "write a note first" in q
        example = q[q.rindex('{"items"'):]
        assert example.index('"note"') < example.index('"shape"') < example.index('"flags"')

    def test_the_judge_is_not_told_that_faults_are_rare(self):
        # version 1 said so, and passed "You mislead users"
        p = audit.build_instruction_judge_prompt(make_doc())
        assert "Most instructions have none" not in p and "one at a time" in " ".join(p.split())

    def test_the_judge_is_not_told_which_version_wrote_the_file(self):
        doc = make_doc(style="RogerV2")
        doc["generator"].update({"template_sha256": "abc123abc123", "concrete": True})
        for p in (audit.build_instruction_judge_prompt(doc), audit.build_question_judge_prompt(doc)):
            assert "RogerV2" not in p and "abc123abc123" not in p and "generator" not in p
            assert not re.search(r"\bv[12]\b", p, re.I)

    def test_the_file_is_in_the_prompt(self):
        doc = make_doc(questions=[f"Question {i}?" for i in range(40)])
        p = audit.build_instruction_judge_prompt(doc)
        assert "<trait>\npetty\n</trait>" in p and DESCRIPTION in p and "magnanimous" in p
        assert p.count("_pos: ") == 5 and p.count("_neg: ") == 5 and "p4_neg: You are magnanimous" in p
        q = audit.build_question_judge_prompt(doc)
        assert "\n39: Question 39?" in q and "0: Question 0?" in q

    def test_a_placeholder_opposite_is_not_named(self):
        p = audit.build_instruction_judge_prompt(make_doc(neg="non-petty"))
        assert "non-petty" not in p and "not named" in p

    def test_every_fault_and_flag_is_defined(self):
        for f in audit.INSTRUCTION_FAULTS:
            assert f"- {f}" in audit.INSTRUCTION_JUDGE_PROMPT, f
        for f in audit.QUESTION_FLAGS:
            assert f"- {f}:" in audit.QUESTION_JUDGE_PROMPT, f
        for s in audit.QUESTION_SHAPES:
            assert f"- {s}:" in audit.QUESTION_JUDGE_PROMPT, s
        # a shape that is one letter was written among the flags by the judge
        assert all(len(s) > 3 for s in audit.QUESTION_SHAPES)


def instr_reply(faults=None, drop=None, extra=None):
    """faults: {instruction id: [fault, ...]}, as the tests think of it; the
    reply itself is keyed by fault."""
    out = {f: [] for f in audit.INSTRUCTION_FAULTS if f != drop}
    for i, fs in (faults or {}).items():
        for f in fs:
            out.setdefault(f, []).append({"quote": f"words of {i}", "id": i})
    out.update(extra or {})
    return json.dumps(out)


def question_reply(n=40, shape="situation", flags=None):
    return json.dumps({"items": [{"i": i, "note": "asks", "shape": shape, "flags": flags or []} for i in range(n)]})


class TestParsing:
    def test_instruction_judgement(self):
        items = audit.parse_instruction_judgement(instr_reply({"p1_neg": ["weak_opposite", "softened"]}), 5)
        assert [i["id"] for i in items][:3] == ["p0_pos", "p0_neg", "p1_pos"] and len(items) == 10
        assert items[3]["faults"] == ["softened", "weak_opposite"]
        assert items[3]["quotes"]["softened"] == "words of p1_neg" and items[0]["faults"] == []

    def test_fences_and_text_around_the_object(self):
        text = "Here it is:\n```json\n" + instr_reply() + "\n```"
        assert len(audit.parse_instruction_judgement(text, 5)) == 10

    def test_a_missing_fault_is_an_error(self):
        with pytest.raises(ValueError, match="state"):
            audit.parse_instruction_judgement(instr_reply(drop="state"), 5)

    def test_an_unknown_fault_is_an_error(self):
        with pytest.raises(ValueError, match="unknown fault"):
            audit.parse_instruction_judgement(instr_reply(extra={"rude": []}), 5)

    def test_an_instruction_that_does_not_exist_is_an_error(self):
        with pytest.raises(ValueError, match="no such instruction"):
            audit.parse_instruction_judgement(instr_reply({"p7_pos": ["state"]}), 5)

    def test_weak_opposite_on_a_pos_instruction_is_dropped(self):
        items = audit.parse_instruction_judgement(instr_reply({"p0_pos": ["weak_opposite", "state"]}), 5)
        assert items[0]["faults"] == ["state"]

    def test_question_judgement(self):
        items = audit.parse_question_judgement(question_reply(flags=["two_option"]), 40)
        assert len(items) == 40 and items[7] == {"i": 7, "note": "asks", "shape": "situation", "flags": ["two_option"]}
        with pytest.raises(ValueError, match="unknown shape"):
            audit.parse_question_judgement(question_reply(shape="S"), 40)
        with pytest.raises(ValueError, match="no judgement for questions"):
            audit.parse_question_judgement(question_reply(n=39), 40)

    def test_a_shape_repeated_among_the_flags_is_dropped(self):
        items = audit.parse_question_judgement(question_reply(shape="how_to", flags=["how_to", "yes_no"]), 40)
        assert items[0]["shape"] == "how_to" and items[0]["flags"] == ["yes_no"]
        with pytest.raises(ValueError, match="unknown flag"):
            audit.parse_question_judgement(question_reply(flags=["rude"]), 40)


class TestSplit:
    STRATA = {"new": [f"n{i}" for i in range(366)], "old_untouched": [f"o{i}" for i in range(202)],
              "old_regenerated": [f"r{i}" for i in range(91)]}

    def test_disjoint_sized_and_proportional(self):
        s = audit.draw_split(self.STRATA, 150, 150, 1, exclude=set())
        assert len(s["dev"]) == 150 and len(s["held_out"]) == 150 and not set(s["dev"]) & set(s["held_out"])
        assert s["strata"]["new"]["dev"] == 83 and s["strata"]["old_untouched"]["dev"] == 46
        assert s["strata"]["old_regenerated"]["dev"] == 21
        assert sum(x.startswith("n") for x in s["held_out"]) == s["strata"]["new"]["held_out"]

    def test_same_seed_same_split(self):
        assert audit.draw_split(self.STRATA, 50, 50, 7, set()) == audit.draw_split(self.STRATA, 50, 50, 7, set())
        assert audit.draw_split(self.STRATA, 50, 50, 7, set()) != audit.draw_split(self.STRATA, 50, 50, 8, set())

    def test_excluded_traits_are_in_neither(self):
        s = audit.draw_split(self.STRATA, 150, 150, 1, exclude={"n0", "n1", "o5"})
        assert not {"n0", "n1", "o5"} & (set(s["dev"]) | set(s["held_out"]))

    def test_asking_for_too_many(self):
        with pytest.raises(ValueError):
            audit.draw_split({"a": ["x", "y"]}, 2, 1, 1, set())

    def test_strata(self):
        assert audit.stratum_of({}, "petty", {"petty"}) == "old_untouched"
        assert audit.stratum_of({"generator": {"style": "Roger"}}, "petty", {"petty"}) == "old_regenerated"
        assert audit.stratum_of({"generator": {"style": "Roger"}}, "fair", {"petty"}) == "new"

    def test_the_held_out_set_needs_final(self, tmp_path):
        (tmp_path / "split.json").write_text(json.dumps(
            {"dev": ["a"], "held_out": ["b"], "excluded": {"pilot": [], "near_example": []}}))
        for cmd in (["stage", "--arm", "v2"], ["judge", "--arm", "v2", "--dry-run"], ["report", "--baseline", "v1"]):
            with pytest.raises(SystemExit, match="final"):
                audit.main([cmd[0], "--out", str(tmp_path), "--set", "held_out", *cmd[1:]])

    def test_a_split_is_drawn_once(self, tmp_path):
        (tmp_path / "split.json").write_text("{}")
        with pytest.raises(SystemExit, match="drawn once"):
            audit.main(["split", "--out", str(tmp_path)])


class TestStatistics:
    def test_wilson(self):
        lo, hi = audit.wilson(0, 100)
        assert lo == 0.0 and 0.03 < hi < 0.04
        lo, hi = audit.wilson(50, 100)
        assert 0.40 < lo < 0.41 and 0.59 < hi < 0.60

    def test_mcnemar(self):
        assert audit.mcnemar_exact(0, 0) == 1.0
        assert audit.mcnemar_exact(6, 0) == pytest.approx(2 / 64)
        assert audit.mcnemar_exact(5, 5) == 1.0
        assert audit.mcnemar_exact(1, 9) == pytest.approx(2 * 11 / 1024)

    def test_paired_difference(self):
        rng = np.random.default_rng(0)
        base = np.array([3] * 40 + [0] * 60)
        arm = np.zeros(100, dtype=int)
        n = np.full(100, 5)
        out = audit.paired_difference(base, arm, n, rng)
        assert out["difference"] == pytest.approx(-0.24) and out["p"] < 0.001
        assert out["interval"][0] < -0.24 < out["interval"][1] < 0
        same = audit.paired_difference(base, base, n, rng)
        assert same["difference"] == 0 and same["p"] == 1.0

    def test_cluster_interval_is_wider_than_a_plain_one_when_faults_cluster(self):
        rng = np.random.default_rng(0)
        k = np.array([10] * 10 + [0] * 90)
        n = np.full(100, 10)
        lo, hi = audit.cluster_rate_interval(k, n, rng)
        plain = audit.wilson(100, 1000)
        assert (hi - lo) > 2 * (plain[1] - plain[0])


class TestCountsAndReport:
    def judged(self, doc, faults=None, shape="situation", flags=None):
        return {"content_sha256": audit.content_sha256(doc),
                "instruction_judge": {"items": audit.parse_instruction_judgement(instr_reply(faults), 5)},
                "question_judge": {"items": audit.parse_question_judgement(question_reply(shape=shape, flags=flags), 40)}}

    def test_counts(self):
        doc = make_doc()
        c = audit.counts_for(doc, self.judged(doc, {"p0_pos": ["softened"], "p1_neg": ["softened", "weak_opposite"]},
                                              flags=["two_option"]))
        assert c["softened_pos"] == (1, 5) and c["softened_neg"] == (1, 5) and c["weak_opposite"] == (1, 5)
        assert c["urges_others"] == (0, 10) and c["names_label"] == (10, 10)
        assert c["q_two_option"] == (40, 40) and c["q_shape_situation"] == (40, 40)
        assert c["q_shape_other_kinds"] == (0, 40) and c["q_shape_advice"] == (0, 40)
        assert c["q_persona"] == (40, 40)

    def test_an_unjudged_file_has_only_the_pattern_measures(self):
        c = audit.counts_for(make_doc(), None)
        assert "softened_pos" not in c and "q_two_option" not in c and "names_label" in c

    def test_report_over_two_arms(self, tmp_path):
        bad = {"pos": "You have a tendency to nurse grievances over small slights and sometimes bring up minor "
                      "past offenses, treating them as ongoing issues.",
               "neg": "You are magnanimous and let every small wrong pass the moment it happens, holding nothing "
                      "against anyone once the day is over."}
        stems = [f"t{i}" for i in range(12)]
        for arm, pairs in (("v1", [bad] * 5), ("v2", None)):
            d = tmp_path / "stage" / "dev" / arm
            d.mkdir(parents=True)
            for s in stems:
                doc = make_doc(pairs=pairs)
                (d / f"{s}.json").write_text(json.dumps(doc))
                j = tmp_path / "judged" / arm
                j.mkdir(parents=True, exist_ok=True)
                (j / f"{s}.json").write_text(json.dumps(self.judged(doc, {"p0_pos": ["softened"]} if arm == "v1" else None)))
        (tmp_path / "split.json").write_text(json.dumps(
            {"dev": stems, "held_out": [], "excluded": {"pilot": [], "near_example": []}}))
        arms = dict(audit._arm_dir(tmp_path, "dev", a) for a in ("v1", "v2"))
        report = audit.build_report(tmp_path, "dev", arms, "v1", stems)
        m = report["measures"]
        assert m["open_risky"]["arms"]["v1"]["rate"] == 1.0 and m["open_risky"]["arms"]["v2"]["rate"] == 0.0
        assert m["open_risky"]["against_baseline"]["v2"]["files_only_baseline"] == 12
        assert m["open_risky"]["against_baseline"]["v2"]["files_p"] == pytest.approx(2 / 4096)
        assert m["softened_pos"]["arms"]["v1"]["rate"] == pytest.approx(0.2)
        assert m["softened_pos"]["against_baseline"]["v2"]["difference"] == pytest.approx(-0.2)
        assert report["variety"]["v2"]["mean"] == 1.0
        text = audit.render_report(report)
        assert "open_risky" in text and "12 lost, 0 gained" in text and "You have ... (risky)" in text

    def test_a_trait_described_differently_in_two_arms_is_left_out_of_both(self, tmp_path, caplog):
        # chaotic was rewritten on 2026-09-30, between the staging of two arms
        stems = [f"t{i}" for i in range(6)]
        for arm in ("v1", "v2"):
            d = tmp_path / "stage" / "dev" / arm
            d.mkdir(parents=True)
            for s in stems:
                doc = make_doc()
                if arm == "v2" and s == "t3":
                    doc["description"] = "This means living in a whirl of disorder."
                if s == "t4":   # white space is not a change
                    doc["description"] = DESCRIPTION.replace(" ", "  " if arm == "v2" else " ", 1)
                (d / f"{s}.json").write_text(json.dumps(doc))
        arms = dict(audit._arm_dir(tmp_path, "dev", a) for a in ("v1", "v2"))
        with caplog.at_level("WARNING"):
            report = audit.build_report(tmp_path, "dev", arms, "v1", stems)
        assert report["left_out_described_differently"] == {"t3": ["v2"]}
        assert report["n_traits"] == {"v1": 5, "v2": 5}
        assert report["measures"]["names_label"]["against_baseline"]["v2"]["paired_traits"] == 5
        assert "t3 (v2)" in caplog.text
        assert "left out of every arm" in audit.render_report(report) and "t3" in audit.render_report(report)

    def test_a_judgement_of_an_older_text_is_ignored(self, tmp_path):
        doc = make_doc()
        d, j = tmp_path / "arm", tmp_path / "judged"
        d.mkdir(), j.mkdir()
        (d / "t.json").write_text(json.dumps(doc))
        stale = self.judged(make_doc(questions=["Other?"] * 40), {"p0_pos": ["softened"]})
        (j / "t.json").write_text(json.dumps(stale))
        assert "softened_pos" not in audit.load_arm(d, j, ["t"])["t"]

    def test_copied_examples_count_a_file_at_two(self):
        assert audit.FILE_THRESHOLDS["copied_example"] == 2
        arm = {"a": {"copied_example": (1, 10)}, "b": {"copied_example": (2, 10)}, "c": {"copied_example": (0, 10)}}
        s = audit.summarize(arm, "copied_example", np.random.default_rng(0))
        assert s["files_with"] == 1 and s["with"] == 3


class TestArmFiles:
    """A staging directory starts as a copy of the corpus files; a run that fails part of the way
    leaves old text under the new arm's name (2026-09-29: 73 of 150, on API errors)."""

    def stage(self, tmp_path):
        d = tmp_path / "stage" / "dev" / "v2"
        d.mkdir(parents=True)
        (d / "done.json").write_text(json.dumps(make_doc(style="RogerV2")))
        (d / "untouched.json").write_text(json.dumps(make_doc(style="Roger")))
        (d / "old.json").write_text(json.dumps(make_doc(style=None)))
        return d

    def test_only_files_written_under_the_style_belong_to_the_arm(self, tmp_path, caplog):
        d = self.stage(tmp_path)
        with caplog.at_level("WARNING"):
            assert sorted(audit.arm_files(d, ["done", "untouched", "old", "absent"], "RogerV2")) == ["done"]
        assert "2 file(s) not written under RogerV2" in caplog.text
        assert sorted(audit.arm_files(d, ["done", "untouched", "old"])) == ["done", "old", "untouched"]

    def test_a_template_hash_pins_the_arm_to_one_draft(self, tmp_path):
        d = self.stage(tmp_path)
        for name, h in (("draft2", "aaaaaaaaaaaa"), ("draft3", "bbbbbbbbbbbb")):
            doc = make_doc(style="RogerV2")
            doc["generator"]["template_sha256"] = h
            (d / f"{name}.json").write_text(json.dumps(doc))
        stems = ["done", "draft2", "draft3"]
        assert sorted(audit.arm_files(d, stems, "RogerV2@bbbbbbbbbbbb")) == ["draft3"]
        assert sorted(audit.arm_files(d, stems, "RogerV2")) == ["done", "draft2", "draft3"]
        assert audit._arm_style("v2:RogerV2@bbbbbbbbbbbb=some/dir") == ("v2", "RogerV2@bbbbbbbbbbbb")

    def test_arm_specs(self, tmp_path):
        assert audit._arm_style("v2:RogerV2") == ("v2", "RogerV2")
        assert audit._arm_style("v2:RogerV2=some/dir") == ("v2", "RogerV2")
        assert audit._arm_style("v1_corpus") == ("v1_corpus", None)
        assert audit._arm_dir(tmp_path, "dev", "v2:RogerV2") == ("v2", tmp_path / "stage" / "dev" / "v2")
        assert audit._arm_dir(tmp_path, "dev", "v1=some/dir") == ("v1", Path("some/dir"))

    def test_a_report_on_part_of_a_set(self, tmp_path, capsys):
        d = self.stage(tmp_path)
        (tmp_path / "split.json").write_text(json.dumps(
            {"dev": ["done", "untouched", "old"], "held_out": ["h"], "excluded": {"pilot": [], "near_example": []}}))
        (tmp_path / "part.json").write_text(json.dumps(["done", "old"]))
        audit.main(["report", "--out", str(tmp_path), "--baseline", f"v2={d}", "--stems", str(tmp_path / "part.json")])
        assert "traits per arm: v2 2" in capsys.readouterr().out
        (tmp_path / "part.json").write_text(json.dumps(["done", "h"]))
        with pytest.raises(SystemExit, match="not in the dev set"):
            audit.main(["report", "--out", str(tmp_path), "--baseline", f"v2={d}", "--stems", str(tmp_path / "part.json")])

    def test_the_report_and_the_judge_leave_the_others_out(self, tmp_path, capsys):
        d = self.stage(tmp_path)
        report = audit.build_report(tmp_path, "dev", {"v2": d}, "v2", ["done", "untouched", "old"],
                                    styles={"v2": "RogerV2"})
        assert report["n_traits"] == {"v2": 1}
        assert list(report["generators"]["v2"]) == ["RogerV2 -"]
        (tmp_path / "split.json").write_text(json.dumps(
            {"dev": ["done", "untouched", "old"], "held_out": [], "excluded": {"pilot": [], "near_example": []}}))
        audit.main(["judge", "--out", str(tmp_path), "--arm", "v2:RogerV2", "--dry-run"])
        assert "v2: 1 of 3 files to judge" in capsys.readouterr().out


def _response(text, tokens=(100, 50)):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]))


class TestJudgeFile:
    def run(self, replies):
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=replies)
        usage, tally = audit.MultiModelUsage(), audit.ParseTally()
        doc = make_doc()
        out = asyncio.run(audit.judge_file(client, doc, instruction_model="claude-sonnet-4-6",
                                           question_model="claude-haiku-4-5-20251001",
                                           semaphore=asyncio.Semaphore(1), usage=usage, tally=tally))
        return out, usage, tally, client, doc

    def test_two_calls_are_charged_and_stamped(self):
        def reply(**kw):
            shown = kw["messages"][0]["content"]
            return _response(instr_reply() if "<instructions>" in shown else question_reply())
        out, usage, tally, client, doc = self.run(reply)
        assert client.messages.create.call_count == 2
        assert all(c.kwargs["temperature"] == 0.0 for c in client.messages.create.call_args_list)
        assert usage.n_calls == 2 and set(usage.as_dict()["per_model"]) == {
            "claude-sonnet-4-6", "claude-haiku-4-5-20251001"}
        assert out["instruction_judge"]["rubric_version"] == audit.INSTRUCTION_AUDIT_RUBRIC_VERSION
        assert out["question_judge"]["model"] == "claude-haiku-4-5-20251001"
        assert audit.judgement_is_current(out, doc, "claude-sonnet-4-6", "claude-haiku-4-5-20251001")
        assert not audit.judgement_is_current(out, doc, "claude-sonnet-4-6", "other-model")
        assert not audit.judgement_is_current(out, make_doc(questions=["Other?"] * 40), "claude-sonnet-4-6",
                                              "claude-haiku-4-5-20251001")
        assert sum(tally.ok.values()) == 2 and sum(tally.total.values()) == 2

    def test_an_unparseable_reply_is_retried_and_still_charged(self, monkeypatch):
        monkeypatch.setattr(audit.asyncio, "sleep", AsyncMock())
        seen = {"instr": 0}

        def reply(**kw):
            shown = kw["messages"][0]["content"]
            if "<instructions>" in shown:
                seen["instr"] += 1
                return _response("I cannot" if seen["instr"] == 1 else instr_reply())
            return _response(question_reply())
        out, usage, tally, client, _ = self.run(reply)
        assert client.messages.create.call_count == 3 and usage.n_calls == 3
        # at temperature 0 the same unreadable reply would come back
        temps = [c.kwargs["temperature"] for c in client.messages.create.call_args_list
                 if "<instructions>" in c.kwargs["messages"][0]["content"]]
        assert temps == [0.0, 0.5]
        asked = [c.kwargs["messages"][0]["content"] for c in client.messages.create.call_args_list
                 if "<instructions>" in c.kwargs["messages"][0]["content"]]
        assert "could not be used" not in asked[0]
        assert "Your previous reply could not be used: no JSON object in the reply" in asked[1]
        assert tally.total["instructions:claude-sonnet-4-6"] == 2 and tally.ok["instructions:claude-sonnet-4-6"] == 1
        assert len(out["instruction_judge"]["items"]) == 10


class TestTaste:
    """The blind rating (Roger, 2026-09-30): label, description and the five
    positive instructions, two scores from 1 to 5, reasons first."""

    def test_the_prompt_shows_the_five_positives_and_nothing_of_the_arm(self):
        doc = make_doc()
        p = audit.build_taste_prompt(doc)
        assert "Trait: petty" in p and DESCRIPTION in p and "5. You are petty." in p
        assert "magnanimous" not in p and "RogerV2" not in p and "neg" not in p.split("The five system prompts:")[1]
        assert p.index("Reason first") < p.index('"quality"') and p.index('"reasons"') < p.index('"quality"')

    @pytest.mark.parametrize("text, quality, coverage", [
        ('{"reasons": "Strong and plain.", "quality": 5, "coverage": 4}', 5, 4),
        ('Here it is:\n```json\n{"reasons": "ok", "quality": "3", "coverage": 2}\n```', 3, 2),
    ])
    def test_a_rating_is_read(self, text, quality, coverage):
        r = audit.parse_taste_judgement(text)
        assert (r["quality"], r["coverage"]) == (quality, coverage) and r["reasons"]

    @pytest.mark.parametrize("text", [
        '{"reasons": "x", "quality": 6, "coverage": 3}', '{"reasons": "x", "quality": 3}',
        '{"reasons": "x", "quality": 3.5, "coverage": 3}', '{"reasons": "x", "quality": true, "coverage": 3}',
        "no json here"])
    def test_a_bad_rating_is_refused(self, text):
        with pytest.raises(ValueError):
            audit.parse_taste_judgement(text)

    def test_a_model_that_refuses_a_temperature_is_asked_without_one(self):
        import anthropic
        import httpx
        calls = []

        async def create(**kw):
            calls.append(kw)
            if "temperature" in kw:
                response = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
                raise anthropic.BadRequestError("`temperature` is not supported", response=response,
                                                body={"error": {"message": "`temperature` is not supported"}})
            return _response('{"reasons": "fine", "quality": 4, "coverage": 4}')
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        usage, tally = audit.MultiModelUsage(), audit.ParseTally()
        audit._NO_TEMPERATURE_MODELS.discard("claude-sonnet-5-test")
        out = asyncio.run(audit._taste_call(client, "claude-sonnet-5-test", "the prompt", asyncio.Semaphore(1), usage, tally))
        assert out["quality"] == 4 and len(calls) == 2 and "temperature" not in calls[1]
        assert "claude-sonnet-5-test" in audit._NO_TEMPERATURE_MODELS and usage.n_calls == 1
        audit._NO_TEMPERATURE_MODELS.discard("claude-sonnet-5-test")

    def test_report_over_two_arms(self, tmp_path):
        stems = [f"t{i}" for i in range(8)]
        for arm in ("base", "new"):
            d = tmp_path / "stage" / "dev" / arm
            d.mkdir(parents=True)
            for s in stems:
                doc = make_doc()
                (d / f"{s}.json").write_text(json.dumps(doc))
                where = audit.taste_dir(tmp_path, "claude-sonnet-4-6", arm)
                where.mkdir(parents=True, exist_ok=True)
                q = 3 if arm == "base" else 4
                (where / f"{s}.json").write_text(json.dumps({
                    "content_sha256": audit.content_sha256(doc), "model": "claude-sonnet-4-6",
                    "rubric_version": audit.TASTE_RUBRIC_VERSION, "quality": q, "coverage": 3, "reasons": "r"}))
        # a stale rating (another content hash) does not count
        stale = audit.taste_dir(tmp_path, "claude-sonnet-4-6", "new") / "t0.json"
        stale.write_text(json.dumps({**json.loads(stale.read_text()), "content_sha256": "0000"}))
        arms = dict(audit._arm_dir(tmp_path, "dev", a) for a in ("base", "new"))
        report = audit.taste_report(tmp_path, "claude-sonnet-4-6", arms, stems)
        assert report["n_rated"] == {"base": 8, "new": 7}
        q = report["scores"]["quality"]
        assert q["base"]["mean"] == 3.0 and q["new"]["mean"] == 4.0
        assert q["new"]["against_baseline"]["paired_traits"] == 7 and q["new"]["against_baseline"]["difference"] == 1.0
        assert q["new"]["against_baseline"]["better"] == 7 and q["new"]["against_baseline"]["p"] < 0.02
        assert report["scores"]["coverage"]["new"]["against_baseline"]["difference"] == 0.0
        text = audit.render_taste_report(report)
        assert "quality" in text and "+1.00" in text and "better in 7, worse in 0 of 7" in text
