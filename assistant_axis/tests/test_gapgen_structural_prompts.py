"""Structural generators: the two pinned prompts, their hygiene and the rendered user turn (coding_plan_09 section 8,
``prompts``; task 3)."""
from __future__ import annotations

import json
import re

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.structural import modernise as M
from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import prompts as P
from assistant_axis.gapgen.generators.structural.classical import load_all
from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words
from assistant_axis.tests import structural_fakes as F

#: The pin each text is expected to be on, so that a bump is a deliberate edit here.
EXPECTED_VERSIONS = {P.OPERATORS_RUBRIC: 1, P.MODERNISE_RUBRIC: 1}


@pytest.mark.parametrize("name", P.RUBRICS)
def test_rubric_pinned_and_named_in_generator_files(name):
    assert name in sr.GENERATOR_FILES and sr.GENERATOR_FILES[name] == f"{name}.md"
    assert not [p for p in sr.mismatches() if p.split(":", 1)[0] == name]
    rub = P.load_rubric(name)
    assert rub["version"] == EXPECTED_VERSIONS[name] and rub["sha256"] == sr.sha256(sr.load_prompt(name))


def test_an_unpinned_edit_is_refused(tmp_path):
    import shutil
    d = tmp_path / "rubrics"
    shutil.copytree(sr.RUBRICS_DIR, d)
    p = d / "structural_operators.md"
    p.write_text(p.read_text(encoding="utf-8").replace("Think first", "Think hard first"), encoding="utf-8")
    with pytest.raises(P.RubricNotPinned):
        P.load_rubric(P.OPERATORS_RUBRIC, d)
    assert P.load_rubric(P.OPERATORS_RUBRIC, d, allow_unpinned=True)["version"] is None


def test_operators_reasoning_first_in_schema_and_example():
    text = sr.load_prompt(P.OPERATORS_RUBRIC)
    fmt = text[text.index("Respond with one JSON object"):]
    assert fmt.index('"reasoning"') < fmt.index('"position"') < fmt.index('"opposite"') < fmt.index('"retarget"')
    ex = text[text.index("is answered\n") + len("is answered\n"):].split("\n", 1)[0]
    d = json.loads(ex)
    assert list(d)[0] == "reasoning" and list(d) == ["reasoning", "position", "opposite", "excess", "deficiency",
                                                     "retarget", "remode"]
    assert "reasoning first" in fmt
    # the example's own reply parses under the parser, with its forbidden-form words nowhere in it
    rep, why = O.parse_operator_reply(ex, principal=False, source_label="provident", source_stem="provident")
    assert why is None and rep.position == "mean" and rep.excess["label"] == "miserly" and not rep.rejected


def test_modernise_reasoning_first():
    text = sr.load_prompt(P.MODERNISE_RUBRIC)
    fmt = text[text.index("Respond with one JSON object"):]
    assert fmt.index('"id"') < fmt.index('"reasoning"') < fmt.index('"labels"') < fmt.index('"gloss"')
    assert "reasoning first" in fmt


@pytest.fixture(scope="module")
def forbidden():
    return P.forbidden_stems()


@pytest.mark.parametrize("name", P.RUBRICS)
def test_no_example_word_is_a_corpus_queue_or_validation_word(name, forbidden):
    assert len(forbidden) > 2000                       # corpus (~930), queue (~1,000), validation files
    text = sr.load_prompt(name).lower()
    for w in P.EXAMPLE_WORDS[name]:
        assert w.lower() in text, f"{w!r} is declared an example but is not in the text"
        assert normalize_to_file_name(w) not in forbidden, w
        for part in re.findall(r"[a-z]+", w.lower()):
            if part not in ("too", "over", "slow", "to", "self", "penny"):
                assert part not in forbidden, (w, part)


@pytest.mark.parametrize("name", P.RUBRICS)
def test_prompt_words_against_the_lists(name, forbidden):
    """Every word of the text that is a corpus, queue or validation word is ordinary prose, recorded; a new one
    fails."""
    text = sr.load_prompt(name)
    hits = {w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden}
    assert hits - PROSE_ALLOWED - P.PROSE_RECORDED[name] == set(), hits - PROSE_ALLOWED - P.PROSE_RECORDED[name]
    flat = " " + " ".join(re.findall(r"[a-z]+", text.lower())) + " "
    assert {s for s in forbidden if "_" in s and f" {s.replace('_', ' ')} " in flat} == set()
    for w in P.PROSE_RECORDED[name]:                                  # prose only, never quoted as an example
        assert f'"{w}"' not in text.replace('"mean" (', "") or w == "mean"
        assert w not in {x.lower() for x in P.EXAMPLE_WORDS[name]}


def test_plan_illustrations_are_not_used():
    text = sr.load_prompt(P.OPERATORS_RUBRIC).lower()
    for w in ("cautious", "honest", "harsh", "arrogant", "reckless", "self-critical", "tightfisted", "wasteful"):
        assert not re.search(rf"\b{re.escape(w)}\b", text), w
    mt = sr.load_prompt(P.MODERNISE_RUBRIC).lower()
    for w in ("status-seeking", "self-effacing", "pusillanimous", "petty ambition"):
        assert w not in mt, w


# --------------------------------------------------------------------------- the user turn

@pytest.fixture()
def corpus(tmp_path):
    traits = dict(F.TRAITS)
    traits["watched"] = ("watched", "zzneglabel", {"kind": "pair", "members": ["watched", "zzpartner"]},
                         "This means keeping an eye on everything around one.")
    traits["zzpartner"] = ("zzpartner", "watched", {"kind": "pair", "members": ["watched", "zzpartner"]},
                           "This means a partner nobody should see.")
    return F.write_corpus(tmp_path, traits)


def test_user_turn_never_shows_the_negative_label_or_members(corpus):
    ins = O.build_inputs(None, data_dir=corpus, regions_path=corpus / "candidates" / "corpus_regions.json")
    ti = next(t for t in ins if t.stem == "watched")
    assert not hasattr(ti, "negative_label") and not hasattr(ti, "members")
    u = O.render_operator_user(ti)
    assert "zzneglabel" not in u and "zzpartner" not in u
    d = json.loads(u)
    assert d == {"trait": "watched", "description": "This means keeping an eye on everything around one.",
                 "arrangement": "pair", "retarget_toward": list(O.TARGETS)}
    for t in ins:                                       # no trait's turn names its recorded opposite's label
        u = O.render_operator_user(t)
        neg = F.TRAITS.get(t.stem, (None, "zzneglabel"))[1]
        if neg and not neg.startswith("non-"):
            assert neg not in json.loads(u)["description"] and json.loads(u)["trait"] != neg


def test_user_turn_label_in_judge_display_form(corpus):
    ins = {t.stem: t for t in O.build_inputs(None, data_dir=corpus,
                                             regions_path=corpus / "candidates" / "corpus_regions.json")}
    d = json.loads(O.render_operator_user(ins["careful_hexaco"]))
    assert d["trait"] == "careful (from HEXACO)" and d["arrangement"] == "pair"
    assert json.loads(O.render_operator_user(ins["zealous"]))["arrangement"] == "unclassified"
    assert json.loads(O.render_operator_user(ins["gloomy"]))["arrangement"] == "singleton"


def test_principal_keys_only_for_principal_traits(corpus):
    rp = corpus / "candidates" / "corpus_regions.json"
    ins = {t.stem: t for t in O.build_inputs(None, data_dir=corpus, regions_path=rp)}
    assert ins["obedient"].principal_targets and ins["honest"].principal_targets
    assert not ins["dishonest"].principal_targets and not ins["brave"].principal_targets
    assert json.loads(O.render_operator_user(ins["obedient"]))["retarget_toward"][-3:] == list(O.PRINCIPAL_TARGETS)
    assert not set(O.PRINCIPAL_TARGETS) & set(json.loads(O.render_operator_user(ins["brave"]))["retarget_toward"])
    lower = {t.stem: t for t in O.build_inputs(None, data_dir=corpus, regions_path=rp, principal_min_score=2)}
    assert lower["dishonest"].principal_targets
    only = O.build_inputs(None, data_dir=corpus, regions_path=rp, principal_min_score=2, principal_only=True)
    assert {t.stem for t in only} == {"obedient", "rebellious", "honest", "dishonest"}
    d = json.loads(O.render_operator_user(only[0]))
    assert d["retarget_toward"] == list(O.PRINCIPAL_TARGETS) and d["answer_only"] == "retarget"


def test_modernise_user_turn_shows_the_structure():
    rows = load_all(["aristotle"])
    u = json.loads(M.render_modernise_user(rows[:3]))
    assert [r["id"] for r in u["rows"]] == [r.id for r in rows[:3]]
    first = u["rows"][0]
    assert set(first) == {"id", "scheme", "item", "role", "gloss", "structure"}
    assert {s["role"] for s in first["structure"]} == {"mean", "excess"}
    assert "verified_by" not in M.render_modernise_user(rows[:3])
