"""Tests for data_analysis/edit_trait_openings.py and data_analysis/check_opening_edits.py (no API calls)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from data_analysis import check_opening_edits as check  # noqa: E402
from data_analysis import edit_trait_openings as edit  # noqa: E402

MENU = dict(edit.DEFAULT_MENU)


def make_doc(**over):
    doc = {
        "positive_label": "petty",
        "negative_label": "magnanimous",
        "description": "This means holding on to small wrongs.",
        "instruction": [
            {"pos": "Be someone who keeps score of every slight.", "neg": "Be someone who lets slights go."},
            {"pos": "Become someone who nurses grudges.", "neg": "Become someone who forgives at once."},
            {"pos": "From now on, you are someone who never forgets.", "neg": "From now on, you are someone who forgets."},
            {"pos": "You are someone who remembers it all.", "neg": "You are someone who lets it pass."},
            {"pos": "You are petty: you hold every small wrong against its doer.",
             "neg": "You are magnanimous: you let small wrongs go."},
        ],
        "questions": ["q1"],
        "eval_prompt": "e",
        "generator": {"style": "RogerV2"},
    }
    doc.update(over)
    return doc


class TestEditor:
    def test_the_menu_changes_three_openings_and_their_negatives(self):
        edits, skips = edit.plan_file("petty", make_doc(), MENU)
        got = {(e["index"], e["side"]): e["new"] for e in edits}
        assert got[(0, "pos")] == "Be a person who keeps score of every slight."
        assert got[(0, "neg")] == "Be a person who lets slights go."
        assert got[(2, "pos")] == "From now on, you are a person who never forgets."
        assert got[(4, "pos")] == "This is who you are: petty. You hold every small wrong against its doer."
        assert got[(4, "neg")] == "This is who you are: magnanimous. You let small wrongs go."
        assert {i for i, _ in got} == {0, 2, 4} and skips == []

    def test_a_missing_opening_is_a_skip_not_an_edit(self):
        doc = make_doc()
        doc["instruction"][2]["pos"] = "From now on, you are a hoarder of grievances."
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert not any(e["index"] == 2 for e in edits)
        assert {(s["side"], s["wanted"], s["reason"]) for s in skips} == {("pos", "W3", "no such opening")}

    def test_a_negative_that_opens_otherwise_is_left_and_listed(self):
        doc = make_doc()
        doc["instruction"][4]["neg"] = "You are someone who lets small wrongs go."
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert not any(e["index"] == 4 and e["side"] == "neg" for e in edits)
        assert [(s["index"], s["side"], s["wanted"]) for s in skips] == [(4, "neg", "A1")]

    def test_the_wide_match_takes_someone_whose_only_when_asked(self):
        doc = make_doc()
        doc["instruction"][2]["pos"] = "From now on, you are someone whose memory keeps every wrong."
        assert not any(e["index"] == 2 for e in edit.plan_file("petty", doc, MENU)[0])
        e = next(e for e in edit.plan_file("petty", doc, MENU, wide=True)[0] if e["index"] == 2 and e["side"] == "pos")
        assert e["new"] == "From now on, you are a person whose memory keeps every wrong." and e["wide"]

    def test_the_wide_match_needs_a_word_boundary(self):
        assert edit.who_edit("Be someone's friend.", MENU, wide=True) is None
        assert edit.who_edit("Be someone, always, who counts.", MENU, wide=True)[0] == "Be a person, always, who counts."

    def test_a_someone_who_form_in_other_words_is_not_an_adjective(self):
        # "You are a man who ..." splits as "You are X." but the audit classes it as a "someone who" form
        assert edit.adjective_edit("You are a man who never forgets. Every slight stays with you.", MENU) is None

    def test_a_sentence_form_adjective_keeps_its_rest(self):
        new, src, dst = edit.adjective_edit("You are petty. Every slight stays with you.", MENU)
        assert (new, src, dst) == ("This is who you are: petty. Every slight stays with you.", "A1", "A6")

    def test_the_menu_is_checked(self):
        with pytest.raises(SystemExit):
            edit.parse_menu("W1=W7")          # W7 is made from W3
        with pytest.raises(SystemExit):
            edit.parse_menu("A1=A8")          # a rewrite, not a rule
        assert edit.parse_menu("W4=W6,A1=A7") == {"W4": "W6", "A1": "A7"}

    def test_apply_appends_to_hand_edits_and_keeps_key_order(self):
        doc = make_doc(hand_edits="2026-10-04: p4 rewritten by hand")
        edits, _ = edit.plan_file("petty", doc, MENU)
        out = edit.apply_edits(doc, edits, "2026-11-07")
        assert list(out) == list(doc)
        assert out["hand_edits"].startswith("2026-10-04: p4 rewritten by hand; 2026-11-07: openings changed")
        assert "p0 pos+neg 'Be someone who' -> 'Be a person who'" in out["hand_edits"]
        assert "p4 pos+neg 'You are X:' -> 'This is who you are: X.'" in out["hand_edits"]

    def test_apply_refuses_a_text_that_changed_since_planning(self):
        doc = make_doc()
        edits, _ = edit.plan_file("petty", doc, MENU)
        doc["instruction"][0]["pos"] = "Be someone who keeps score."
        with pytest.raises(ValueError):
            edit.apply_edits(doc, edits, "2026-11-07")

    def test_edit_stages_files_and_leaves_the_corpus(self, tmp_path):
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        original = edit.dump(make_doc())
        (corpus / "petty.json").write_text(original, encoding="utf-8")
        out = tmp_path / "out"
        edit.main(["edit", "--traits-dir", str(corpus), "--out", str(out), "--date", "2026-11-07"])
        assert (corpus / "petty.json").read_text(encoding="utf-8") == original
        staged = json.loads((out / "staged" / "petty.json").read_text(encoding="utf-8"))
        assert staged["instruction"][0]["pos"].startswith("Be a person who")
        record = json.loads((out / "edits.json").read_text(encoding="utf-8"))
        assert record["files"] == ["petty"] and len(record["edits"]) == 6 and not record["applied"]


class TestPersonEcho:
    def test_person_twice_in_the_first_sentence_is_an_echo(self):
        assert edit.person_echo("Be a person who argues until the other person comes around.")
        assert edit.person_echo("From now on, you are a person who reads a person's outfit first.")
        assert not edit.person_echo("Be a person who argues. Every person you meet is a target.")
        assert not edit.person_echo("Be a person who keeps score of every slight.")
        assert not edit.person_echo("Be someone who argues until the other person comes around.")

    def test_an_echo_edit_and_its_negative_are_left_unmade(self):
        doc = make_doc()
        doc["instruction"][0] = {"pos": "Be someone who argues until the other person gives in.",
                                 "neg": "Be someone who lets the matter drop."}
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert not any(e["index"] == 0 for e in edits)
        assert {(s["side"], s["reason"]) for s in skips if s["index"] == 0} == {
            ("pos", "person echo"), ("neg", "its positive is kept (person echo)")}
        assert any(e["index"] == 0 for e in edit.plan_file("petty", doc, MENU, allow_echo=True)[0])

    def test_a_negative_echo_alone_keeps_the_negative_only(self):
        doc = make_doc()
        doc["instruction"][2]["neg"] = "From now on, you are someone who lets a person off."
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert any(e["index"] == 2 and e["side"] == "pos" for e in edits)
        assert not any(e["index"] == 2 and e["side"] == "neg" for e in edits)
        assert [(s["index"], s["side"], s["reason"]) for s in skips] == [(2, "neg", "person echo")]


class TestBalance:
    def test_an_echo_revert_swaps_w4_for_w6(self):
        doc = make_doc()
        doc["instruction"][0] = {"pos": "Be someone who argues until the other person gives in.",
                                 "neg": "Be someone who lets the matter drop."}
        edits, skips = edit.plan_file("petty", doc, MENU)
        w6 = [(e["index"], e["side"], e["new"]) for e in edits if e.get("rebalance")]
        assert w6 == [(3, "pos", "You are a person who remembers it all."), (3, "neg", "You are a person who lets it pass.")]
        assert edit.final_nouns(doc["instruction"], edits).count("someone") == 2
        assert not any(s["reason"] == "unbalanced" for s in skips)

    def test_a_w6_swap_that_would_echo_leaves_the_file_unbalanced(self):
        doc = make_doc()
        doc["instruction"][0] = {"pos": "Be someone who argues until the other person gives in.",
                                 "neg": "Be someone who lets the matter drop."}
        doc["instruction"][3]["pos"] = "You are someone who remembers what each person did."
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert not any(e.get("rebalance") for e in edits)
        assert [s["reason"] for s in skips if s["index"] in (3, None)] == ["rebalance would make a person echo", "unbalanced"]
        d = edit.decide({"edits": edits, "skips": skips}, {}, [])
        assert "out of balance" in d["regenerate"]["petty"]

    def test_three_a_person_openings_keep_w1(self):
        doc = make_doc()
        doc["instruction"][3]["pos"] = "You are a person who remembers it all."
        edits, skips = edit.plan_file("petty", doc, MENU)
        assert not any(e["from"] == "W1" for e in edits)
        assert {(s["index"], s["side"]) for s in skips if s["wanted"] == "W1"} == {(0, "pos"), (0, "neg")}
        assert edit.final_nouns(doc["instruction"], edits) == ["someone", "someone", "a person", "a person", None]

    def test_the_checker_allows_the_w6_swap(self):
        assert check.change_kind("You are someone who forgets.", "You are a person who forgets.") == "someone"
        assert check.opening_noun("This is who you are: a person steeped in lore.") == "a person"
        assert check.opening_noun("This is who you are: severe. When someone falls short, you say so.") is None


class TestDecisions:
    def test_a_kept_positive_keeps_its_negative(self):
        edits, _ = edit.plan_file("petty", make_doc(), MENU)
        out, skips = edit.apply_decisions(edits, {"keep": [{"stem": "petty", "index": 4, "side": "pos",
                                                             "reason": "grammar"}]})
        assert not any(e["index"] == 4 for e in out) and len(out) == 4
        assert [(s["side"], s["reason"]) for s in skips] == [("pos", "kept: grammar"),
                                                             ("neg", "kept: its positive is kept")]

    def test_a_kept_negative_leaves_its_positive(self):
        edits, _ = edit.plan_file("petty", make_doc(), MENU)
        out, skips = edit.apply_decisions(edits, {"keep": [{"stem": "petty", "index": 4, "side": "neg",
                                                             "reason": "grammar"}]})
        assert any(e["index"] == 4 and e["side"] == "pos" for e in out) and len(skips) == 1

    def test_edit_leaves_a_regenerated_trait_whole(self, tmp_path):
        corpus, out = tmp_path / "corpus", tmp_path / "out"
        corpus.mkdir()
        (corpus / "petty.json").write_text(edit.dump(make_doc()), encoding="utf-8")
        (corpus / "vain.json").write_text(edit.dump(make_doc(positive_label="vain")), encoding="utf-8")
        dec = tmp_path / "decisions.json"
        dec.write_text(json.dumps({"regenerate": {"vain": "p4 broken"}, "keep": []}), encoding="utf-8")
        (out / "staged").mkdir(parents=True)
        (out / "staged" / "stale.json").write_text("{}", encoding="utf-8")
        edit.main(["edit", "--traits-dir", str(corpus), "--out", str(out), "--decisions", str(dec)])
        assert sorted(p.name for p in (out / "staged").glob("*.json")) == ["petty.json"]
        record = json.loads((out / "edits.json").read_text(encoding="utf-8"))
        assert any(s["stem"] == "vain" and s["reason"].startswith("regenerated") for s in record["skips"])

    def test_decide_regenerates_on_a_broken_positive_and_keeps_a_broken_negative(self):
        plan = {"edits": [
            {"stem": "a", "index": 4, "side": "pos", "from": "A1"}, {"stem": "a", "index": 4, "side": "neg", "from": "A1"},
            {"stem": "b", "index": 4, "side": "pos", "from": "A1"}, {"stem": "b", "index": 4, "side": "neg", "from": "A1"},
            {"stem": "c", "index": 3, "side": "pos", "from": "A1"}, {"stem": "c", "index": 0, "side": "pos", "from": "W1"}]}
        verdicts = []
        for s, side, ans, i in (("a", "pos", ["broken", "broken", "ok"], 4), ("a", "neg", ["broken"] * 3, 4),
                                ("b", "pos", ["ok"] * 3, 4), ("b", "neg", ["broken", "ok", "broken"], 4),
                                ("c", "pos", ["ok", "broken", None], 3)):
            nb, no = ans.count("broken"), ans.count("ok")
            verdicts.append({"stem": s, "index": i, "side": side, "text": "t", "answers": ans,
                             "verdict": "broken" if nb > no else "ok" if no > nb else "unsure"})
        review = {"c|p0|straight": {"verdict": "edited worse"}, "c|p0|swapped": {"verdict": "neither"},
                  "c|p3|straight": {"verdict": "neither"}, "c|p3|swapped": {"verdict": "edited worse"}}
        d = edit.decide(plan, review, verdicts)
        assert sorted(d["regenerate"]) == ["a", "c"]          # c by the pairwise flag on its A6 edit, not its W edit
        assert "blind before-and-after" in d["regenerate"]["c"]
        assert [(k["stem"], k["side"]) for k in d["keep"]] == [("b", "neg")]   # a's negative goes with a
        assert [(u["stem"], u["side"]) for u in d["unsure"]] == [("c", "pos")]


class TestGrammar:
    def test_parse_and_majority(self):
        assert edit.parse_grammar('The verb has no subject.\n{"verdict": "broken"}') == "broken"
        assert edit.parse_grammar('Fine.\n{"verdict": "OK"}') == "ok" and edit.parse_grammar("none") is None
        t = {"stem": "a", "index": 4, "side": "pos", "text": "This is who you are: x. Y."}
        answers = {edit.grammar_key(t, 0): {"verdict": "broken"}, edit.grammar_key(t, 1): {"verdict": "ok"},
                   edit.grammar_key(t, 2): {"verdict": "broken"}}
        assert edit.grammar_verdicts(answers, [t], 3)[0]["verdict"] == "broken"
        answers[edit.grammar_key(t, 2)] = {"verdict": None}
        assert edit.grammar_verdicts(answers, [t], 3)[0]["verdict"] == "unsure"
        assert edit.grammar_verdicts({}, [t], 3)[0]["verdict"] is None

    def test_a_changed_text_is_asked_again(self):
        t = {"stem": "a", "index": 4, "side": "pos", "text": "This is who you are: x. Y."}
        assert edit.grammar_key(t, 0) != edit.grammar_key({**t, "text": "This is who you are: x. Z."}, 0)

    def test_targets_from_files_take_the_this_is_who_lines(self, tmp_path):
        doc = make_doc()
        doc["instruction"][4] = {"pos": "This is who you are: petty. You hold grudges.",
                                 "neg": "This is who you are: magnanimous. You let things go."}
        (tmp_path / "petty.json").write_text(edit.dump(doc), encoding="utf-8")
        got = edit.grammar_targets_from_files(tmp_path, ["petty"])
        assert [(t["index"], t["side"]) for t in got] == [(4, "pos"), (4, "neg")]

    def test_the_prompt_shows_the_text_alone(self):
        p = edit.grammar_prompt("This is who you are: petty. You hold grudges.")
        assert "<text>\nThis is who you are: petty. You hold grudges.\n</text>" in p
        assert p.rstrip().endswith('{"verdict": "ok" or "broken"}') and "{{" not in p


class TestRegenCheck:
    GOOD = [{"pos": "Be a person who keeps score of every slight against you.", "neg": "Be a person who lets go."},
            {"pos": "Become someone who nurses grudges for years.", "neg": "Become someone who forgives."},
            {"pos": "From now on, you are a person who never forgets a wrong.", "neg": "From now on, you are a person who forgets."},
            {"pos": "You are someone who remembers every wrong done to you.", "neg": "You are someone who lets it pass."},
            {"pos": "This is who you are: petty. You hold every small wrong against its doer.",
             "neg": "This is who you are: magnanimous. You let small wrongs go."}]

    def judged(self, faults=None):
        faults = faults or {}
        return {"instruction_judge": {"items": [{"id": f"p{k}_{s}", "faults": faults.get(f"p{k}_{s}", []), "quotes": {}}
                                                for k in range(5) for s in ("pos", "neg")]}}

    def doc(self, pairs=None):
        return make_doc(instruction=json.loads(json.dumps(pairs or self.GOOD)), questions=["q"] * 40)

    def test_a_good_file_passes(self):
        reasons, notes = edit.regen_problems(self.doc(), self.judged(), [])
        assert reasons == [], reasons

    def test_two_positives_with_the_same_fault_roll_again_one_slides(self):
        r, n = edit.regen_problems(self.doc(), self.judged({"p0_pos": ["softened"], "p3_pos": ["softened"]}), [])
        assert any("softened in 2 of 5" in x for x in r)
        r, n = edit.regen_problems(self.doc(), self.judged({"p0_pos": ["softened"], "p3_neg": ["softened"],
                                                            "p1_neg": ["weak_opposite"], "p2_neg": ["weak_opposite"]}), [])
        assert r == [] and any("softened in 1 of 5" in x for x in n)

    def test_the_failing_form_and_the_openings_rule(self):
        pairs = json.loads(json.dumps(self.GOOD))
        pairs[4]["pos"] = "You are petty: you hold every small wrong against its doer."
        assert any("plain 'You are X'" in x for x in edit.regen_problems(self.doc(pairs), self.judged(), [])[0])
        pairs = json.loads(json.dumps(self.GOOD))
        pairs[4]["pos"] = "Be someone who counts every slight and never lets one go."
        r = edit.regen_problems(self.doc(pairs), self.judged(), [])[0]
        assert any("distinct positive openings" in x for x in r)

    def test_broken_grammar_and_echo_roll_again(self):
        v = [{"stem": "petty", "index": 4, "side": "pos", "verdict": "broken", "answers": ["broken"] * 3}]
        assert any("broken English" in x for x in edit.regen_problems(self.doc(), self.judged(), v)[0])
        pairs = json.loads(json.dumps(self.GOOD))
        pairs[0]["pos"] = "Be a person who keeps score of every slight another person makes."
        assert any("'person' twice" in x for x in edit.regen_problems(self.doc(pairs), self.judged(), [])[0])

    def test_unjudged_rolls_again(self):
        assert "not judged" in edit.regen_problems(self.doc(), None, [])[0]

    def test_person_inside_the_this_is_who_phrase_rolls_again(self):
        # a note until Roger's ruling of 2026-11-07 ("make a reroll rule for this"); a reroll reason since
        pairs = json.loads(json.dumps(self.GOOD))
        pairs[4]["pos"] = "This is who you are: a petty person. You hold every small wrong against its doer."
        r, n = edit.regen_problems(self.doc(pairs), self.judged(), [])
        assert any("3 positive openings with 'a person' counting" in x for x in r), r
        pairs[4]["pos"] = "This is who you are: an anxious someone. You hold every small wrong against its doer."
        assert any("3 positive openings with 'someone' counting" in x
                   for x in edit.regen_problems(self.doc(pairs), self.judged(), [])[0])
        # right after the frame, the narrow reading counts it already
        pairs[4]["pos"] = "This is who you are: someone who keeps score. You hold every small wrong against its doer."
        assert "3 positive openings with 'someone'" in edit.regen_problems(self.doc(pairs), self.judged(), [])[0]
        # "person" later in the sentence, after the phrase's full stop, is not the opening
        pairs[4]["pos"] = "This is who you are: petty. Every person who wrongs you stays on your list."
        assert edit.regen_problems(self.doc(pairs), self.judged(), [])[0] == []

    def test_naming_the_label_is_monitored_not_a_reroll(self):
        # Roger, 2026-11-07: names_label is no longer a reroll reason, but stays a measure
        pairs = json.loads(json.dumps(self.GOOD))
        pairs[0]["pos"] = "Be a person who is petty about every slight against you."
        pairs[1]["pos"] = "Become someone who is petty for years on end."
        r, n = edit.regen_problems(self.doc(pairs), self.judged(), [])
        assert r == [], r
        assert any(x.startswith("names_label in 3 of 5 positives") and "monitored, not a reroll" in x for x in n), n
        m = edit.file_measures(self.doc(pairs), None, [])
        assert m["monitored"] == {"names_label": 3} and m["patterns_2of5"] == []

    def test_wide_opening_word(self):
        assert edit.wide_opening_word("This is who you are: the person no one picks.", "a person")
        assert edit.wide_opening_word("Be a person who waits.", "a person")
        assert not edit.wide_opening_word("This is who you are: petty. A person ...", "a person")
        assert edit.wide_opening_word("This is who you are: someone apart.", "someone")
        assert not edit.wide_opening_word("Become someone who waits.", "a person")


class TestCompare:
    def write(self, d: Path, stem: str, doc: dict) -> None:
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{stem}.json").write_text(json.dumps(doc), encoding="utf-8")

    def test_measures_of_an_old_and_a_new_file(self, tmp_path):
        old, new = tmp_path / "old", tmp_path / "new"
        self.write(old, "petty", make_doc(questions=["q"] * 40))
        pairs = json.loads(json.dumps(TestRegenCheck.GOOD))
        pairs[4]["pos"] = "This is who you are: a petty person. You hold every small wrong against its doer."
        self.write(new, "petty", make_doc(instruction=pairs, questions=["q"] * 40))
        verdicts = {"verdicts": [{"stem": "petty", "index": 4, "side": "pos", "verdict": "broken",
                                  "text": pairs[4]["pos"], "answers": ["broken"] * 3},
                                 {"stem": "petty", "index": 4, "side": "pos", "verdict": "broken",
                                  "text": "an older text", "answers": ["broken"] * 3}]}
        g = tmp_path / "grammar_x.json"
        g.write_text(json.dumps(verdicts), encoding="utf-8")
        r = edit.compare_sets({"old": old, "new": new}, {}, {"new": [g]})
        o, n = r["totals"]["old"], r["totals"]["new"]
        assert (o["plain_you_are"], o["someone_over_2"], o["this_is_who"]) == (1, 1, 0)
        assert (n["plain_you_are"], n["someone_over_2"], n["person_over_2"], n["person_over_2_wide"]) == (0, 0, 0, 1)
        assert (n["this_is_who"], n["this_is_who_noun"], n["this_is_who_is_label"]) == (1, 1, 0)
        # only the verdict on the file's current text counts
        assert (n["grammar_checked"], n["grammar_broken"]) == (1, 1)
        assert r["paired_stems"] == [] and "paired" not in n

    def test_judged_faults_are_totalled_on_the_traits_judged_in_every_set(self, monkeypatch, tmp_path):
        a, b = tmp_path / "a", tmp_path / "b"
        for d in (a, b):
            self.write(d, "petty", make_doc(questions=["q"] * 40))
            self.write(d, "vain", make_doc(positive_label="vain", questions=["q"] * 40))
        ja, jb = tmp_path / "ja", tmp_path / "jb"
        soft = TestRegenCheck().judged({"p0_pos": ["softened"], "p2_pos": ["softened"]})
        self.write(ja, "petty", soft)
        self.write(ja, "vain", soft)
        self.write(jb, "petty", TestRegenCheck().judged())
        monkeypatch.setattr(edit.audit, "judgement_is_current", lambda *a, **k: True)
        r = edit.compare_sets({"a": a, "b": b}, {"a": [ja], "b": [jb]}, {})
        assert r["paired_stems"] == ["petty"]
        assert r["totals"]["a"]["paired"]["faults_2of5"]["softened"] == 1
        assert r["totals"]["b"]["paired"]["any_fault_2of5"] == 0
        assert r["totals"]["a"]["n_judged"] == 2


class TestMerge:
    def test_only_the_regenerated_keys_may_differ(self):
        old = make_doc(hand_edits="x")
        new = {k: v for k, v in make_doc(generator={"style": "RogerV2", "template": "66cf"}).items()}
        new["instruction"] = [{"pos": "a", "neg": "b"}] * 5
        new["eval_prompt"] = "rebuilt"
        assert edit.merge_problems(old, new) == []
        assert edit.merge_problems({**old, "description": "edited by Roger"}, new) == ["description differs"]

    def test_merge_refuses_and_writes_nothing(self, tmp_path, monkeypatch):
        corpus, regen = tmp_path / "corpus", tmp_path / "regen"
        corpus.mkdir(), regen.mkdir()
        monkeypatch.setattr(edit, "TRAITS_DIR", corpus)
        old_text = edit.dump(make_doc(description="changed meanwhile"))
        (corpus / "petty.json").write_text(old_text, encoding="utf-8")
        (regen / "petty.json").write_text(edit.dump(make_doc()), encoding="utf-8")
        (tmp_path / "stems.json").write_text('["petty"]', encoding="utf-8")
        with pytest.raises(SystemExit):
            edit.main(["merge", "--dir", str(regen), "--stems", str(tmp_path / "stems.json")])
        assert (corpus / "petty.json").read_text(encoding="utf-8") == old_text
        (corpus / "petty.json").write_text(edit.dump(make_doc(hand_edits="x")), encoding="utf-8")
        edit.main(["merge", "--dir", str(regen), "--stems", str(tmp_path / "stems.json")])
        assert json.loads((corpus / "petty.json").read_text(encoding="utf-8")) == make_doc()


class TestReview:
    def test_parse_takes_the_last_json_object(self):
        assert edit.parse_review('Version 2 is clunky {"worse": "1"} wait.\n{"worse": "2"}') == "2"
        assert edit.parse_review('Both read fine.\n{"worse": "neither"}') == "neither"
        assert edit.parse_review("no json") is None and edit.parse_review(None) is None

    def test_the_verdict_follows_the_order(self):
        assert edit.edited_verdict("straight", "2") == "edited worse"
        assert edit.edited_verdict("swapped", "1") == "edited worse"
        assert edit.edited_verdict("swapped", "2") == "original worse"
        assert edit.edited_verdict("straight", "neither") == "neither"

    def test_items_run_each_positive_edit_both_ways_and_flag_either(self):
        edits, _ = edit.plan_file("petty", make_doc(), MENU)
        items = edit.review_items(edits)
        assert len(items) == 2 * 3
        straight = next(i for i in items if i["index"] == 0 and i["order"] == "straight")
        assert straight["first"].startswith("Be someone") and straight["second"].startswith("Be a person")
        done = {"petty|p0|straight": {"verdict": "neither"}, "petty|p0|swapped": {"verdict": "edited worse"},
                "petty|p2|straight": {"verdict": "original worse"}, "petty|p2|swapped": {"verdict": "neither"}}
        assert edit.summarise_review(done)["flagged"] == ["petty|p0"]

    def test_the_prompt_shows_the_judge_label_and_both_versions(self):
        p = edit.review_prompt("careless (HEXACO)", "This means ...", "A text.", "B text.")
        assert "**careless (from HEXACO)**" in p and "Version 1:\n<prompt>\nA text." in p
        assert p.rstrip().endswith('{"worse": "1", "2" or "neither"}')


class TestCheck:
    def pair(self, doc=None, **changes):
        doc = doc or make_doc()
        edits, _ = edit.plan_file("petty", doc, MENU, wide=True)
        return edit.dump(doc), edit.dump(edit.apply_edits(doc, edits, "2026-11-07"))

    def test_the_editors_output_passes(self):
        fails, counts = check.check_file("petty", *self.pair())
        assert fails == []
        assert counts[("pos", "someone")] == 2 and counts[("pos", "this is who")] == 1

    def test_a_change_past_the_opening_fails(self):
        old, new = self.pair()
        new = new.replace("keeps score of every slight", "keeps score of each slight")
        assert any("not an allowed opening change" in f for f in check.check_file("petty", old, new)[0])

    def test_a_changed_description_fails(self):
        old, new = self.pair()
        new = new.replace("holding on to small wrongs", "holding on to wrongs")
        fails = check.check_file("petty", old, new)[0]
        assert any("keys other than instruction" in f for f in fails)

    def test_a_lower_case_rest_after_this_is_who_fails(self):
        assert check.change_kind("You are petty: you hold grudges.", "This is who you are: petty. you hold grudges.") is None
        assert check.change_kind("You are petty: you hold grudges.", "This is who you are: petty. You hold grudges.") == "this is who"

    def test_an_edit_without_a_record_fails(self):
        doc = make_doc()
        edits, _ = edit.plan_file("petty", doc, MENU)
        out = edit.apply_edits(doc, edits, "2026-11-07")
        del out["hand_edits"]
        fails = check.check_file("petty", edit.dump(doc), edit.dump(out))[0]
        assert any("without a hand_edits record" in f for f in fails)

    def test_a_reformatted_file_fails(self):
        old, new = self.pair()
        new = json.dumps(json.loads(new), indent=4, ensure_ascii=False) + "\n"
        assert any("corpus format" in f for f in check.check_file("petty", old, new)[0])

    def test_main_over_directories(self, tmp_path, capsys):
        old_dir, new_dir = tmp_path / "old", tmp_path / "new"
        old_dir.mkdir(), new_dir.mkdir()
        old, new = self.pair()
        (old_dir / "petty.json").write_text(old, encoding="utf-8")
        (new_dir / "petty.json").write_text(new, encoding="utf-8")
        assert check.main(["--new", str(new_dir), "--old", str(old_dir)]) == 0
        (new_dir / "petty.json").write_text(new.replace("nurses grudges", "nurses a grudge"), encoding="utf-8")
        assert check.main(["--new", str(new_dir), "--old", str(old_dir)]) == 1
        assert "FAILED" in capsys.readouterr().out

    def regenerated(self, **over):
        old = make_doc(hand_edits="2026-10-04: p4 by hand")
        new = {k: v for k, v in make_doc().items() if k not in ("generator", "eval_prompt")}
        new["instruction"] = TestRegenCheck.GOOD
        new["eval_prompt"] = "rebuilt"
        new["generator"] = {"style": "RogerV2", "template": "66cf2d2511fb"}
        new.update(over)
        return edit.dump(old), edit.dump(new)

    def test_a_regeneration_passes_only_on_the_allowlist(self, tmp_path):
        old, new = self.regenerated()
        fails, counts = check.check_regenerated("petty", old, new)
        assert fails == [] and counts[("regenerated", "eval_prompt")] == 1
        assert check.check_file("petty", old, new)[0]          # the opening-edit rules reject it
        old_dir, new_dir = tmp_path / "old", tmp_path / "new"
        old_dir.mkdir(), new_dir.mkdir()
        (old_dir / "petty.json").write_text(old, encoding="utf-8")
        (new_dir / "petty.json").write_text(new, encoding="utf-8")
        assert check.main(["--new", str(new_dir), "--old", str(old_dir)]) == 1
        (tmp_path / "dec.json").write_text('{"regenerate": {"petty": "p4 broken"}}', encoding="utf-8")
        assert check.main(["--new", str(new_dir), "--old", str(old_dir), "--regenerated", str(tmp_path / "dec.json")]) == 0

    def test_a_regeneration_may_not_touch_other_keys_or_keep_hand_edits(self):
        fails = check.check_regenerated("petty", *self.regenerated(description="new words"))[0]
        assert any("description changed" in f for f in fails)
        fails = check.check_regenerated("petty", *self.regenerated(hand_edits="2026-10-04: p4 by hand"))[0]
        assert any("hand_edits is still there" in f for f in fails)        # the old record carried over
        assert check.check_regenerated("petty", *self.regenerated(hand_edits="2026-11-07: p0 by hand, after three rolls"))[0] == []

    def test_a_regeneration_keeps_to_the_openings_rule(self):
        pairs = json.loads(json.dumps(TestRegenCheck.GOOD))
        pairs[4]["pos"] = "You are someone who never lets a slight go."
        pairs[1]["pos"] = "Be someone who counts every slight."
        fails = check.check_regenerated("petty", *self.regenerated(instruction=pairs))[0]
        assert any("open with 'someone'" in f for f in fails)
