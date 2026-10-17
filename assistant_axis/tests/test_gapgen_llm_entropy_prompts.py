"""LLM-entropy generator: the pinned texts, their hygiene, the grids and the rendered user turns (coding_plan_06
section 8, ``prompts``; task 1).  No network."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.generators.llm_entropy import prompts as P
from assistant_axis.gapgen.generators.structural.prompts import forbidden_stems
from assistant_axis.gapgen.prompt_hygiene import PROSE_ALLOWED, prompt_words

REPO = Path(__file__).resolve().parents[2]
#: The pin each text is expected to be on, so that a bump is a deliberate edit here.
EXPECTED_VERSIONS = {P.SCAFFOLD_RUBRIC: 1, P.MULTILINGUAL_RUBRIC: 1, P.BACKTRANSLATE_RUBRIC: 1}
#: Ordinary words of the texts that are corpus, queue or validation words anyway (beyond the platform's
#: PROSE_ALLOWED), each only as prose: "single" ("a single word", as the structural texts record it), and the three
#: language names that are corpus membership traits (German, Japanese, Russian), which the back-translation and
#: translation calls must name.  A new hit fails.
PROSE_RECORDED = {"rubric": frozenset({"single"}), "user": frozenset({"single"}),
                  "language": frozenset({"german", "japanese", "russian", "single"})}


@pytest.fixture(scope="module")
def forbidden():
    return forbidden_stems()


@pytest.mark.parametrize("name", P.RUBRICS)
def test_rubric_pinned_and_named_in_generator_files(name):
    assert sr.GENERATOR_FILES[name] == f"{name}.md" and name in sr.PINNED_NAMES
    assert not [p for p in sr.mismatches() if p.split(":", 1)[0] == name]
    rub = P.load_rubric(name)
    assert rub["version"] == EXPECTED_VERSIONS[name] and rub["sha256"] == sr.sha256(sr.load_prompt(name))


def test_an_unpinned_edit_is_refused(tmp_path):
    d = tmp_path / "rubrics"
    shutil.copytree(sr.RUBRICS_DIR, d)
    p = d / "llm_entropy_scaffold.md"
    p.write_text(p.read_text(encoding="utf-8").replace("Satisfy the constraint first", "Satisfy it first"),
                 encoding="utf-8")
    with pytest.raises(P.RubricNotPinned):
        P.load_rubric(P.SCAFFOLD_RUBRIC, d)
    assert P.load_rubric(P.SCAFFOLD_RUBRIC, d, allow_unpinned=True)["version"] is None


@pytest.mark.parametrize("name", (P.SCAFFOLD_RUBRIC, P.MULTILINGUAL_RUBRIC))
def test_approach_first_in_the_schema_and_a_short_reason_not_thinking(name):
    text = sr.load_prompt(name)
    fmt = text[text.index("Respond with a JSON object only"):]
    assert fmt.index('"approach"') < fmt.index('"items"') < fmt.index('"label"') < fmt.index('"gloss"')
    assert "short reason, one or two sentences" in fmt
    # Sonnet 5.5 refuses prompts that ask it to think in a field (judging rule, 2026-10-13)
    assert not re.search(r"\bthink\b|\breasoning\b", text, re.I)


def test_the_system_turn_defers_to_the_request_on_the_count():
    """The (b) user turn asks for 8 to 12 items, (a) and (e) for 15 to 20: the system turn names no count."""
    text = sr.load_prompt(P.SCAFFOLD_RUBRIC)
    assert "Give as many items as the request asks for" in text and "15 to 20" not in text
    assert "8 to 12" in P.render_b(P.DRY_RUN_SEED) and "15 to 20" in P.render_a("money", "habit")


def test_the_kind_vocabulary_is_m1s():
    from assistant_axis.gapgen.generators.llm_entropy.parse import KINDS
    for name in (P.SCAFFOLD_RUBRIC, P.MULTILINGUAL_RUBRIC):
        text = sr.load_prompt(name)
        assert all(f'"{k}"' in text for k in KINDS)
        assert "<" + " | ".join(KINDS) + ">" in text


# --------------------------------------------------------------------------- hygiene

@pytest.mark.parametrize("name", P.RUBRICS)
def test_no_example_word_is_a_corpus_queue_or_validation_word(name, forbidden):
    assert len(forbidden) > 2000
    text = sr.load_prompt(name).lower()
    for w in P.EXAMPLE_WORDS[name]:
        assert w.lower() in text, f"{w!r} is declared an example but is not in the text"
        assert normalize_to_file_name(w) not in forbidden, w
        for part in re.findall(r"[a-z]+", w.lower()):
            if part not in ("to", "the"):
                assert part not in forbidden, (w, part)


def _hits(text: str, forbidden) -> set:
    return {w for w in prompt_words(text) if normalize_to_file_name(w) in forbidden}


def _phrase_hits(text: str, forbidden) -> set:
    flat = " " + " ".join(re.findall(r"[a-z]+", text.lower())) + " "
    return {s for s in forbidden if "_" in s and f" {s.replace('_', ' ')} " in flat}


@pytest.mark.parametrize("name", P.RUBRICS)
def test_rubric_words_against_the_lists(name, forbidden):
    text = sr.load_prompt(name)
    assert _hits(text, forbidden) - PROSE_ALLOWED - PROSE_RECORDED["rubric"] == set()
    assert _phrase_hits(text, forbidden) == set()


def _user_texts() -> dict[str, str]:
    """Every user-turn text the code can send, but the persons and the translated (c) texts: (a) 210, (e) 181, the
    (b) template, (d)'s paragraphs and topics, the (c) master request."""
    a, e = P.grid_prompts("a"), P.grid_prompts("e")
    return {"a": "\n".join(p.user for p in a), "e": "\n".join(p.user for p in e),
            "b": P.B_TEMPLATE.replace("{person}", ""),
            "d": "\n".join([P.D_STAGE1_APPEND, P.D_STAGE2_TEMPLATE] + [P.d_topic(p.prompt_id) for p in a + e]),
            "c": P.C_USER_MASTER}


def test_every_user_turn_word_against_the_lists(forbidden):
    for fam, text in _user_texts().items():
        assert _hits(text, forbidden) - PROSE_ALLOWED - PROSE_RECORDED["user"] == set(), fam
        assert _phrase_hits(text, forbidden) == set(), fam


def test_domain_mode_and_constraint_words_are_clean(forbidden):
    words = [p for _, p in P.DOMAINS] + [m.name for m in P.MODES] + list(P.SUFFIXES) + list(P.PREFIXES)
    for w in words:
        for t in prompt_words(w):
            assert normalize_to_file_name(t) not in forbidden or t in PROSE_ALLOWED, (w, t)


def test_translation_and_back_translation_words(forbidden):
    master = sr.load_prompt(P.MULTILINGUAL_RUBRIC)
    for lang in P.LANGUAGES:
        system, user = P.render_translate(lang.code, master)
        text = system + "\n" + user + "\n" + P.PROMPT_BACK_SYSTEM.replace("{language}", lang.name) + "\n" + \
            P.BACKTRANSLATE_HEADER.format(language=lang.name)
        assert _hits(text, forbidden) - PROSE_ALLOWED - PROSE_RECORDED["language"] == set(), lang.code


def test_recorded_prose_is_never_quoted_as_an_example():
    for name in P.RUBRICS:
        text = sr.load_prompt(name)
        for w in PROSE_RECORDED["rubric"]:
            assert f'"{w}"' not in text
            assert w not in {x.lower() for x in P.EXAMPLE_WORDS[name]}


# --------------------------------------------------------------------------- grids and user turns

def test_grid_sizes():
    assert len(P.DOMAINS) == 30 and len(P.MODES) == 7 and len(P.LANGUAGES) == 10
    assert (len(P.LETTERS), len(P.BIGRAMS), len(P.SUFFIXES), len(P.PREFIXES), len(P.FRAMES)) == (26, 120, 20, 12, 3)
    assert len(set(P.BIGRAMS)) == 120 and all(re.fullmatch(r"[a-z]{2}", b) for b in P.BIGRAMS)
    assert P.GRID_SIZES == {"a": 210, "b": 600, "c": 300, "e": 181}
    assert len(P.grid_prompts("a")) == 210 and len(P.grid_prompts("e")) == 181
    assert len({p.prompt_id for p in P.grid_prompts("a")}) == 210
    assert len({p.prompt_id for p in P.grid_prompts("e")}) == 181


def test_the_languages_are_rogers_ten():
    assert [lang.name for lang in P.LANGUAGES] == ["German", "Japanese", "Mandarin", "Russian", "Arabic", "Persian",
                                                   "Finnish", "Korean", "Hindi", "Turkish"]


def test_a_user_turn_is_the_plans_text():
    u = P.render_a("money", "habit")
    assert u.startswith("Domain: money. Mode: a habit.\nName 15 to 20 traits that are specifically about how a person "
                        "relates to money, each in the form of a habit (something the person does as a rule, as "
                        "opposed to an attitude they hold, a way they speak, a feeling they tend to have, a way they "
                        "think, a moral stance they take, or a strategy they use with other people).")
    assert "the body" in P.render_a("body", "speech") and "a way the person speaks, as opposed to" in \
        P.render_a("body", "speech")


def test_b_user_turn_and_the_fixed_dry_run_row():
    u = P.render_b(P.DRY_RUN_SEED)
    assert u.startswith("Person: Tian Yi (person, CBDB ID = 367824; died 1684).\nThis person may be little known;")
    fict = P.render_b({"name": "Zorbel Quint", "description": "invented puppet villain", "kind": "fictional"})
    assert fict.startswith("Person: Zorbel Quint (invented puppet villain; fictional).")    # invented name
    assert P.person_line({"name": "X Y", "description": "", "kind": "real", "born": "-44", "died": None}) == \
        "X Y (born 44 BC)"


def test_e_user_turns():
    assert P.render_e("bigram:sc").startswith('Spelling constraint: the label\'s main word begins with the letters "sc".')
    assert P.render_e("suffix:minded").startswith('Spelling constraint: the label\'s main word ends in "-minded".')
    assert P.render_e("frame:about").startswith('Form constraint: the label has the form "X about Y", an adjective '
                                                'about a thing or a subject (two to four words).')
    assert "each about a different Y" in P.render_e("frame:about")
    with pytest.raises(KeyError):
        P.render_e("vowel:a")


def test_d_stage1_appends_and_stage2_quotes_stage1_verbatim():
    base = P.render_a("money", "habit")
    s1 = P.render_d_stage1(base)
    assert s1.startswith(base) and s1.endswith("do not give every item the same number.")
    answer = '{"approach": "Money as a habit.", "items": [{"label": "zzz", "probability": 0.2}]}'
    s2 = P.render_d_stage2("a:money:habit", s1, answer)
    assert f"Question: {s1}\nYour answer: {answer}\n" in s2
    assert "traits about money as a habit that are real and nameable" in s2 and "below 0.03" in s2
    assert "satisfies the same constraint" in P.render_d_stage2("e:bigram:sc", P.render_e("bigram:sc"), "{}")
    with pytest.raises(ValueError):
        P.d_topic("b:r0001")


def test_with_probabilities_only_on_a_and_e():
    assert all(p.user.endswith("the same number.") for p in P.grid_prompts("e", with_probabilities=True))
    with pytest.raises(ValueError):
        P.grid_prompts("b", seeds=[], with_probabilities=True)


def _prompts_json() -> dict:
    langs = {}
    for lang in P.LANGUAGES:
        langs[lang.code] = {"system": f"SYSTEM in {lang.name} (fixture)", "sha256": f"sha-{lang.code}",
                            "user_template": f"[{lang.code}] Domain: {{domain}}. Request.",
                            "domains": {d: f"{d}-{lang.code}" for d in P.DOMAIN_IDS}}
    return {"languages": langs}


def test_c_prompts_are_the_recorded_translations_with_their_hash():
    pj = _prompts_json()
    ps = P.grid_prompts("c", prompts_json=pj)
    assert len(ps) == 300 and len({p.prompt_id for p in ps}) == 300
    p = next(x for x in ps if x.prompt_id == "c:de:money")
    assert p.user == "[de] Domain: money-de. Request." and p.meta["system"] == "SYSTEM in German (fixture)"
    assert p.language == "de" and p.meta["language_prompt_sha256"] == "sha-de"
    with pytest.raises(ValueError):
        P.grid_prompts("c")


def test_back_translation_user_turn():
    u = P.render_backtranslate("de", [{"label": "geldscheu", "gloss": "Das bedeutet \"x\".", "antonym": None}])
    assert u == 'Language: German.\nItems:\n1. label: "geldscheu"; gloss: "Das bedeutet \\"x\\"."; antonym: null'


def test_translation_request_carries_the_master_for_the_language():
    master = sr.load_prompt(P.MULTILINGUAL_RUBRIC)
    system, user = P.render_translate("fi", master)
    assert "into Finnish" in system and "{domain}" in system and "{language}" not in system
    assert P.render_master("fi", master) in user and "{language}" not in user
    assert P.C_USER_MASTER in user and "money: money" in user and "past: the past" in user


# --------------------------------------------------------------------------- versions and draws

def test_version_pin_covers_every_wording():
    assert P.PROMPT_HASHES[P.PROMPTS_VERSION] == P.wording_sha256()
    assert sorted(P.PROMPT_HASHES) == list(range(1, P.PROMPTS_VERSION + 1))


def test_a_changed_table_changes_the_hash(monkeypatch):
    before = P.wording_sha256()
    monkeypatch.setattr(P, "DOMAINS", P.DOMAINS[:-1] + (("praise", "being praised"),))
    assert P.wording_sha256() != before


def test_share_draw_is_seeded_nested_and_bounded():
    a = P.grid_prompts("a")
    s20 = P.select_prompts(a, share=0.2, seed=0)
    assert len(s20) == 42
    assert len(P.select_prompts(P.grid_prompts("e"), share=0.2, seed=0)) == 36
    n40 = P.select_prompts(a, n=40, seed=0)
    assert {p.prompt_id for p in n40} <= {p.prompt_id for p in s20}          # the model-test arm is inside the share
    assert [p.prompt_id for p in P.select_prompts(list(reversed(a)), share=0.2, seed=0)] == \
        [p.prompt_id for p in reversed(s20)]                                  # independent of the list's order
    assert {p.prompt_id for p in P.select_prompts(a, share=0.2, seed=1)} != {p.prompt_id for p in s20}
    for bad in (0, 1.5, -0.1):
        with pytest.raises(ValueError):
            P.select_prompts(a, share=bad)
    assert P.select_prompts(a, share=1.0) == a


def test_rendering_needs_no_wordfreq():
    code = ("import sys\nfrom assistant_axis.gapgen.generators.llm_entropy import prompts as P\n"
            "P.grid_prompts('a'); P.grid_prompts('e'); P.variant_samples()\n"
            "print('wordfreq' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=True).stdout
    assert out.strip() == "False"


def test_variant_samples_cover_every_family():
    vs = P.variant_samples()
    fams = {pid.split(":")[0] for _, pid, _ in vs}
    assert {"a", "b", "d", "e", "c"} <= fams
    assert any(pid == "b:r0001" and "Tian Yi" in u for _, pid, u in vs)
    assert json.dumps(vs)            # plain strings
