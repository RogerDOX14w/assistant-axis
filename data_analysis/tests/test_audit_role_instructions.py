"""Tests for audit_role_instructions.py: the role companion of the trait audit."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from data_analysis import audit_role_instructions as audit
from data_analysis import audit_trait_instructions as trait_audit
from data_analysis.regenerate_role_instructions import build_eval_prompt

DESCRIPTION = "A forger is someone who copies signatures and documents for money, so well that they pass."


def make_role(instructions=None, questions=None, description=DESCRIPTION, style="RogerV2"):
    return {
        "description": description,
        "instruction": [{"pos": t} for t in (instructions or [
            "You are a forger who copies any signature and ages the paper until nobody looks twice at it.",
            "Act as a forger who sells papers that pass, and never asks what the buyer wants them for.",
            "You're a forger: a steady hand, the right ink, and a buyer waiting with cash in an envelope.",
            "Be a forger. Practice the loop of a stranger's signature until your hand knows it better than theirs.",
            "You copy passports and diplomas, and you take pride that your work has never once been caught.",
        ])],
        "questions": questions or [f"A buyer wants a deed by Friday and offers double. What do you do, number {i}?"
                                   for i in range(40)],
        "eval_prompt": build_eval_prompt("forger", description),
        "generator": {"style": style, "template_sha256": "abc"},
    }


class TestPatternChecks:
    def flags(self, doc, stem="forger"):
        return [r["flags"] for r in audit.pattern_checks(doc, stem)["instructions"]]

    def test_role_play_and_statement_openings(self):
        f = self.flags(make_role())
        assert "open_roleplay" in f[1] and "open_roleplay" not in f[0]
        assert "open_statement" in f[4]

    def test_observer_words_and_dashes(self):
        doc = make_role(instructions=["You are a forger navigating the challenges of a risky trade with skill.",
                                      "You are a forger — careful, quiet, and paid in cash every single time.",
                                      "You are a forger.", "You are a forger.", "You are a forger."])
        f = self.flags(doc)
        assert "observer_words" in f[0] and "dashes" in f[1] and "dashes" not in f[0]

    def test_length_window_is_the_role_rubrics(self):
        assert audit.ROLE_LENGTH_RANGE == (15, 25)
        f = self.flags(make_role(instructions=["You are a forger."] + ["word " * 15] + ["word " * 25]
                                 + ["word " * 26] + ["word " * 20]))
        assert "length_out" in f[0] and "length_out" not in f[1] and "length_out" not in f[2] and "length_out" in f[3]

    def test_chat_words_are_not_a_fault_for_an_ai_role(self):
        doc = make_role(instructions=["You are an assistant who answers every user at once."] * 5)
        assert "chat_words" in self.flags(doc)[0]
        ai = make_role(instructions=["You are an assistant who answers every user at once."] * 5,
                       description="A virtue-aligned AI is an AI assistant that does good because it cares.")
        assert "chat_words" not in self.flags(ai, "virtue_aligned_ai")[0]

    def test_a_copied_template_example_is_flagged(self):
        examples = audit.role_example_instructions("RogerV2")
        assert len(examples) == 4 and examples[0].startswith("You are an actuary")
        doc = make_role(instructions=[examples[1]] + ["You are a forger."] * 4)
        assert "copied_example" in self.flags(doc)[0] and "copied_example" not in self.flags(doc)[1]

    def test_questions(self):
        doc = make_role(questions=["Have you ever been caught?", "How do you forge a passport?",
                                   "I found a forged deed in my attic. What should I do?",
                                   "As a forger, which job are you proudest of?"])
        q = [r["flags"] for r in audit.pattern_checks(doc, "forger")["questions"]]
        assert "q_have_you_ever" in q[0] and "q_yesno" in q[0]
        assert "q_howto" in q[1]
        assert "q_first_person" in q[2]
        assert "q_names_role" in q[3] and "q_persona" in q[3]

    def test_file_counts_distinct_openings(self):
        p = audit.pattern_checks(make_role(), "forger")["file"]
        assert p["n_pairs"] == 5 and p["distinct_pos_forms"] == len(set(p["pos_forms"]))


class TestJudgePrompts:
    def test_instruction_prompt_is_about_the_role(self):
        p = audit.build_instruction_judge_prompt(make_role(), "devils_advocate")
        assert "<role>\ndevil's advocate\n</role>" in p and DESCRIPTION in p
        assert "p0: You are a forger" in p and "p4: You copy" in p
        for fault in audit.INSTRUCTION_FAULTS:
            assert f"- {fault}:" in p, fault
        assert "trait" not in p.lower().replace("personality trait", "")
        assert "neg" not in p.split("<instructions>")[1]
        # reason (the quote) before the verdict (the id), as AGENT_NOTES asks of judge prompts
        assert p.index('"quote"') < p.index('"id"')

    def test_question_prompt(self):
        p = audit.build_question_judge_prompt(make_role(), "forger")
        assert "0: A buyer wants a deed" in p and "39: A buyer" in p
        for flag in audit.QUESTION_FLAGS:
            assert f"- {flag}:" in p, flag
        assert p.index('"note"') < p.index('"shape"')

    def test_taste_prompt(self):
        p = audit.build_taste_prompt(make_role(), "forger")
        assert "Role: forger" in p and "1. You are a forger" in p and "5. You copy" in p
        assert p.index('"reasons"') < p.index('"quality"')


class TestParse:
    def reply(self, **faults):
        return json.dumps({f: faults.get(f, []) for f in audit.INSTRUCTION_FAULTS})

    def test_instruction_judgement(self):
        items = audit.parse_instruction_judgement(
            self.reply(generic=[{"quote": "a steady hand", "id": "p2"}], softened=[{"quote": "x", "id": "p2"}]), 5)
        assert [i["id"] for i in items] == ["p0", "p1", "p2", "p3", "p4"]
        assert items[2]["faults"] == ["generic", "softened"] and items[0]["faults"] == []

    @pytest.mark.parametrize("bad, message", [
        (json.dumps({"softened": []}), "no entry"),
        (json.dumps({**{f: [] for f in audit.INSTRUCTION_FAULTS}, "weak_opposite": []}), "unknown fault"),
        (json.dumps({**{f: [] for f in audit.INSTRUCTION_FAULTS}, "generic": [{"quote": "q", "id": "p9"}]}), "no such"),
    ])
    def test_instruction_judgement_refused(self, bad, message):
        with pytest.raises(ValueError, match=message):
            audit.parse_instruction_judgement(bad, 5)

    def test_question_judgement(self):
        reply = json.dumps({"items": [{"i": 0, "note": "n", "shape": "situation", "flags": ["two_option", "situation"]},
                                      {"i": 1, "note": "n", "shape": "advice", "flags": ["outside_world"]}]})
        items = audit.parse_question_judgement(reply, 2)
        assert items[0]["flags"] == ["two_option"] and items[1]["flags"] == ["outside_world"]
        with pytest.raises(ValueError, match="unknown flag"):
            audit.parse_question_judgement(json.dumps({"items": [{"i": 0, "shape": "situation", "flags": ["names_trait"]}]}), 1)
        with pytest.raises(ValueError, match="no judgement"):
            audit.parse_question_judgement(json.dumps({"items": []}), 1)


class TestCounts:
    def test_pattern_and_judged_measures(self):
        doc = make_role()
        judged = {"instruction_judge": {"items": [{"id": f"p{k}", "faults": ["generic"] if k == 2 else []}
                                                  for k in range(5)]},
                  "question_judge": {"items": [{"i": i, "shape": "situation" if i % 2 else "other",
                                                "flags": ["two_option"] if i < 10 else []} for i in range(40)]}}
        c = audit.counts_for(doc, "forger", judged)
        assert c["open_roleplay"] == (1, 5) and c["generic"] == (1, 5) and c["softened"] == (0, 5)
        assert c["q_two_option"] == (10, 40) and c["q_shape_situation"] == (20, 40)
        assert c["q_shape_other_kinds"] == (20, 40)
        assert "generic" not in audit.counts_for(doc, "forger", None)   # not judged: left out, not counted as zero


class TestSplitAndStage:
    def test_split_is_disjoint_stratified_and_drawn_once(self, tmp_path, monkeypatch, capsys):
        roles, old = tmp_path / "roles", tmp_path / "old"
        roles.mkdir(), old.mkdir()
        for i in range(40):
            (roles / f"r{i:02d}.json").write_text(json.dumps(make_role()))
            if i < 30:
                (old / f"r{i:02d}.json").write_text("{}")
        (roles / "default.json").write_text(json.dumps({"instruction": [{"pos": ""}]}))
        monkeypatch.setattr(audit, "ROLES_DIR", roles)
        out = tmp_path / "audit"
        args = ["split", "--out", str(out), "--n-dev", "16", "--n-held-out", "16", "--sample", "10",
                "--old-scores-dir", str(old)]
        audit.main(args)
        split = json.loads((out / "split.json").read_text())
        assert len(split["dev"]) == 16 and len(split["held_out"]) == 16 and not set(split["dev"]) & set(split["held_out"])
        assert split["strata"]["old_regenerated"]["dev"] == 12 and split["strata"]["new"]["dev"] == 4
        sample = json.loads((out / "sample10.json").read_text())
        assert len(sample) == 10 and set(sample) <= set(split["dev"])
        with pytest.raises(SystemExit, match="drawn once"):
            audit.main(args)
        audit.main(["stage", "--out", str(out), "--arm", "corpus"])
        assert len(list((out / "stage" / "dev" / "corpus").glob("*.json"))) == 16
        with pytest.raises(SystemExit, match="final check"):
            audit.main(["stage", "--out", str(out), "--set", "held_out", "--arm", "corpus"])
        # the corpus set: every role but default, no --final needed, --stems narrows it
        audit.main(["stage", "--out", str(out), "--set", "corpus", "--arm", "final"])
        staged = sorted(p.stem for p in (out / "stage" / "corpus" / "final").glob("*.json"))
        assert len(staged) == 40 and "default" not in staged
        (out / "three.json").write_text(json.dumps(["r00", "r01", "r02"]))
        audit.main(["stage", "--out", str(out), "--set", "corpus", "--arm", "three", "--stems", str(out / "three.json")])
        assert len(list((out / "stage" / "corpus" / "three").glob("*.json"))) == 3
        (out / "bad.json").write_text(json.dumps(["r00", "nobody"]))
        with pytest.raises(SystemExit, match="not in the corpus set"):
            audit.main(["stage", "--out", str(out), "--set", "corpus", "--arm", "bad", "--stems", str(out / "bad.json")])


class TestJudgeAndReport:
    def test_judge_writes_records_and_the_report_pairs_two_arms(self, tmp_path, monkeypatch, capsys):
        out = tmp_path / "audit"
        stems = ["forger", "herder"]
        (out).mkdir()
        (out / "split.json").write_text(json.dumps({"dev": stems, "held_out": [], "excluded": {}}))
        for arm, opening in (("corpus", "Act as"), ("v3", "Be")):
            d = out / "stage" / "dev" / arm
            d.mkdir(parents=True)
            for s in stems:
                doc = make_role(instructions=[f"{opening} a {s} number {k}, with work that passes every single time."
                                              for k in range(5)])
                (d / f"{s}.json").write_text(json.dumps(doc))

        async def fake_call(client, model, prompt, parse, max_tokens, semaphore, usage, tally, label):
            tally.total[label] += 1
            tally.ok[label] += 1
            usage.charge(model, 1000, 200)
            if label.startswith("instructions"):
                return parse(json.dumps({f: ([{"quote": "Act as", "id": "p0"}] if f == "generic" and "Act as" in prompt
                                             else []) for f in audit.INSTRUCTION_FAULTS}))
            return parse(json.dumps({"items": [{"i": i, "note": "n", "shape": "situation", "flags": []} for i in range(40)]}))
        monkeypatch.setattr(trait_audit, "_judge_call", fake_call)
        monkeypatch.setattr(audit.anthropic, "AsyncAnthropic", lambda **kw: object())
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        audit.main(["judge", "--out", str(out), "--arm", "corpus", "v3"])
        rec = json.loads((out / "judged" / "corpus" / "forger.json").read_text())
        assert rec["instruction_judge"]["rubric_version"] == audit.INSTRUCTION_AUDIT_RUBRIC_VERSION
        assert json.loads((out / "judged" / "usage.json").read_text())["n_calls"] == 8
        capsys.readouterr()
        audit.main(["judge", "--out", str(out), "--arm", "corpus", "--dry-run"])
        assert "0 of 2 files to judge" in capsys.readouterr().out   # current judgements are not repeated
        report = audit.build_report(out, "dev", {"corpus": out / "stage" / "dev" / "corpus",
                                                 "v3": out / "stage" / "dev" / "v3"}, "corpus", stems)
        assert report["measures"]["open_roleplay"]["arms"]["corpus"]["rate"] == 1.0
        assert report["measures"]["open_roleplay"]["arms"]["v3"]["rate"] == 0.0
        assert report["measures"]["generic"]["arms"]["corpus"]["with"] == 2
        assert report["measures"]["open_roleplay"]["against_baseline"]["v3"]["difference"] == -1.0
        text = audit.render_report(report)
        assert "open_roleplay" in text and "(role-play)" in text


class TestReplyReading:
    def test_text_after_the_json_is_ignored(self):
        """2026-10-02: the fault judge sometimes adds a note with a brace after its JSON."""
        body = json.dumps({f: [] for f in audit.INSTRUCTION_FAULTS})
        for tail in ("\n\nNote: p2 reads {fine}.", "\n{\"extra\": 1}", ""):
            items = audit.parse_instruction_judgement(body + tail, 5)
            assert [i["faults"] for i in items] == [[]] * 5

    def test_fenced_and_prefixed_replies(self):
        body = json.dumps({f: [] for f in audit.INSTRUCTION_FAULTS})
        assert len(audit.parse_instruction_judgement("Here it is:\n```json\n" + body + "\n```", 5)) == 5
        with pytest.raises(ValueError, match="no JSON"):
            audit.parse_instruction_judgement("no json here", 5)


class TestRoleOpeningForm:
    """The V3 menu's own classifier: tells You're from You are, and You are a X who from You are a X."""

    def test_the_menu_forms(self):
        f = audit.role_opening_form
        assert f("From now on, you are a liar who says whatever gets you what you want.") == audit.ROLE_FORM_FROM_NOW_ON
        assert f("Be a goldfish. Circle the bowl.") == audit.ROLE_FORM_BE
        assert f("You're a forger. You copy signatures.") == audit.ROLE_FORM_YOURE
        assert f("Become a glacier. Move a few feet a year.") == audit.ROLE_FORM_BECOME
        assert f("You are an actuary who prices the chance of things going wrong.") == audit.ROLE_FORM_YOU_ARE_WHO
        assert f("You are a herder. Your camels are your living.") == audit.ROLE_FORM_YOU_ARE
        assert f("You are the village herder who counts wealth in stock.") == audit.ROLE_FORM_YOU_ARE_WHO

    def test_role_play_statements_and_commands(self):
        f = audit.role_opening_form
        assert f("Act as a liar who lies.") == audit.ROLE_FORM_ACT_AS
        assert f("Pretend to be a pirate.") == audit.ROLE_FORM_OTHER_ROLEPLAY
        assert f("Take on the character of a smuggler.") == audit.ROLE_FORM_OTHER_ROLEPLAY
        assert f("You keep a herd of goats on the hills.") == audit.ROLE_FORM_STATEMENT
        assert f("You believe the market is always right.") == audit.ROLE_FORM_STATEMENT
        assert f("Pour the drinks and keep the tabs.") == audit.ROLE_FORM_COMMAND
        assert f("Pretend to be a pirate.") in audit.ROLE_ROLEPLAY_FORMS

    def test_file_variety_uses_the_menu_classifier(self):
        doc = make_role(instructions=["You are a forger who copies signatures and ages the paper with tea.",
                                      "You're a forger. Your buyers pay cash and never ask what the papers are for.",
                                      "Be a forger. Practice the loop of a stranger's signature until your hand knows it.",
                                      "Become a forger who sells documents that pass because nobody looks twice at them.",
                                      "From now on, you are a forger with a steady hand, the right ink, and no questions."])
        p = audit.pattern_checks(doc, "forger")
        assert p["file"]["distinct_pos_forms"] == 5
        assert p["instructions"][0]["form"] == audit.ROLE_FORM_YOU_ARE_WHO and p["instructions"][1]["form"] == audit.ROLE_FORM_YOURE
        assert p["instructions"][0]["trait_form"] == trait_audit.FORM_YOU_ARE_SOMEONE   # the flags still use the trait classifier
