"""LLM-entropy generator: reading the replies (coding_plan_06 section 8, ``parse``).  No network."""
from __future__ import annotations

import json

import pytest

from assistant_axis.gapgen.generators.llm_entropy import parse as PA


def _item(label, gloss=None, **kw):
    d = {"label": label, "gloss": gloss if gloss is not None else f"This means acting in the {label} way.",
         "antonym": kw.pop("antonym", None), "kind": kw.pop("kind", "trait"), "ambiguity_flag": False}
    d.update(kw)
    return d


def _reply_20():
    items = [_item(f"zzword{i}") for i in range(16)]
    items.append(_item("thrifty, careful"))                          # invalid: two names joined by a comma
    items.append(_item("keeps every receipt for years"))             # five words: a label_problem, kept
    items.append(_item("naïve"))                                     # non-ASCII: a label_problem, kept
    items.append(_item("spends at once", gloss="Spending money as soon as it arrives."))   # no "This means": noted
    return json.dumps({"approach": "Money as a habit.", "items": items})


def test_a_scripted_reply_with_twenty_items():
    rep, err = PA.parse_reply(_reply_20())
    assert err is None and rep.approach == "Money as a habit."
    assert len(rep.items) == 19 and rep.n_invalid == 1
    assert rep.invalid == [{"label": "thrifty, careful", "why": "label with a comma"}]
    by = {it["label"]: it for it in rep.items}
    assert PA.label_problem("keeps every receipt for years") == "5 words (at most 4)"
    assert PA.label_problem("naïve") == "non-ASCII"
    assert "keeps every receipt for years" in by and "naïve" in by           # kept: the table records the problem
    assert by["spends at once"]["notes"] == ["gloss does not open 'This means'"]
    assert by["zzword0"]["notes"] == [] and by["zzword0"]["kind"] == "trait"


def test_label_problem_truth_table():
    cases = {"punctilious": None, "slow to anger": None, "avoids the limelight": None,
             "penny-wise": None, "well-to-do and proud": None,                   # a hyphenated compound is one word
             "one two three four five": "5 words (at most 4)", "under_score": "underscore",
             "café-minded": "non-ASCII", "": "empty", "   ": "empty", None: "empty", "---": "does not normalise"}
    for label, why in cases.items():
        assert PA.label_problem(label) == why, label
    assert PA.label_problem("x" * 85) == "does not normalise"


def test_probability_accepted_only_in_the_unit_interval():
    items = [_item("aa", probability=0.04), _item("bb", probability=1.5), _item("cc", probability=-0.1),
             _item("dd", probability="0.2"), _item("ee", probability=True), _item("ff", probability=0), _item("gg")]
    rep, _ = PA.parse_reply(json.dumps({"approach": "x", "items": items}))
    p = {it["label"]: it["probability"] for it in rep.items}
    assert p == {"aa": 0.04, "bb": None, "cc": None, "dd": None, "ee": None, "ff": 0.0, "gg": None}
    notes = {it["label"]: it["notes"] for it in rep.items}
    assert notes["bb"] == ["probability outside [0, 1]"] and notes["gg"] == []


def test_kinds_outside_the_vocabulary_are_kept_as_none():
    rep, _ = PA.parse_reply(json.dumps({"approach": "x", "items": [_item("aa", kind="not a persona"),
                                                                    _item("bb", kind="virtue"),
                                                                    _item("cc", kind=None)]}))
    k = {it["label"]: it["kind"] for it in rep.items}
    assert k == {"aa": "not_a_persona", "bb": None, "cc": None}
    assert any("outside M1's vocabulary" in n for n in rep.items[1]["notes"])


def test_labels_and_antonyms_are_lower_cased_with_a_note():
    rep, _ = PA.parse_reply(json.dumps({"approach": "x", "items": [_item("Penny-Wise", antonym="Pound-Wise")]}))
    it = rep.items[0]
    assert it["label"] == "penny-wise" and it["antonym"] == "pound-wise" and "label lower-cased" in it["notes"]


def test_replies_that_do_not_parse():
    assert PA.parse_reply(None) == (None, "no response")
    assert PA.parse_reply("") == (None, "empty response")
    assert PA.parse_reply("I cannot help with that.") == (None, "no JSON object")
    assert PA.parse_reply('{"approach": "x", "items": [{"label": "a"') [0] is None   # cut at max_tokens
    assert PA.parse_reply('{"approach": "x"}') == (None, "no items list")
    rep, err = PA.parse_reply('```json\n{"approach": "x", "items": []}\n```')
    assert err is None and rep.items == []                    # an empty list parses: a constraint may fit nothing


def test_approach_missing_or_late_is_noted_not_fatal():
    rep, _ = PA.parse_reply(json.dumps({"items": [_item("aa")], "approach": "late"}))
    assert rep.notes == ["approach not first"]
    rep, _ = PA.parse_reply(json.dumps({"items": [_item("aa")]}))
    assert rep.notes == ["no approach"] and rep.approach is None


def test_multilingual_items_keep_the_original_label_and_its_fields():
    raw = {"approach": "Geld als Gewohnheit.", "items": [
        {"label": "Pfennigfuchser", "romanization": "Pfennigfuchser", "english_hint": None,
         "gloss": "Das bedeutet, um jeden Cent zu feilschen.", "antonym": "Verschwender", "kind": "trait",
         "ambiguity_flag": False},
        {"label": "けち", "romanization": "kechi", "english_hint": None, "gloss": "ケチとは", "antonym": None,
         "kind": "trait"}]}
    rep, err = PA.parse_reply(json.dumps(raw, ensure_ascii=False), multilingual=True)
    assert err is None
    a, b = rep.items
    assert a["label"] == "Pfennigfuchser" and a["romanization"] == "Pfennigfuchser" and a["notes"] == []
    assert b["label"] == "けち" and b["romanization"] == "kechi" and b["english_hint"] is None
    rep, _ = PA.parse_reply(json.dumps({"approach": "x", "items": [{"label": "a、b"}]}, ensure_ascii=False),
                            multilingual=True)
    assert rep.n_invalid == 1                                # a comma in another script counts too


def test_back_translation_matched_by_index_and_a_short_reply_counted():
    reply = {"items": [{"index": 2, "romanization": "geldscheu", "label": "Money-Shy", "gloss": "This means avoiding "
                        "money talk.", "antonym": None, "listicle": False},
                       {"index": 1, "romanization": "pfennigfuchserisch", "label": "penny-pinching",
                        "gloss": "This means haggling over every cent.", "antonym": "Lavish", "listicle": "false"}]}
    bt, err = PA.parse_backtranslation(json.dumps(reply), 3)
    assert err is None and bt.n_expected == 3 and bt.n_returned == 2 and bt.missing == [3]
    assert bt.by_index[1]["label"] == "penny-pinching" and bt.by_index[1]["antonym"] == "lavish"
    assert bt.by_index[1]["listicle"] is False and bt.by_index[2]["label"] == "money-shy"
    # no index: by position; a duplicate or out-of-range index is extra
    reply2 = {"items": [{"label": "a"}, {"label": "b"}, {"index": 9, "label": "c"}, {"index": 1, "label": "d"}]}
    bt2, _ = PA.parse_backtranslation(json.dumps(reply2), 2)
    assert {i: v["label"] for i, v in bt2.by_index.items()} == {1: "a", 2: "b"} and bt2.extra == 2
    assert PA.parse_backtranslation("nope", 2) == (None, "no JSON object")


def test_tagged_translation_answer():
    text = ("<note>Used Sie.</note>\n<system>\nDu hilfst ...\n</system>\n<user_template>Lebensbereich: {domain}."
            "</user_template>\n<domains>\nmoney: Geld\nbody: der Körper\n</domains>")
    d, err = PA.parse_tagged(text)
    assert err is None and d["note"] == "Used Sie." and d["system"] == "Du hilfst ..."
    assert d["user_template"] == "Lebensbereich: {domain}." and d["domains"] == {"money": "Geld", "body": "der Körper"}
    assert PA.parse_tagged("<system>x</system>") == (None, "missing <user_template>, <domains>")
