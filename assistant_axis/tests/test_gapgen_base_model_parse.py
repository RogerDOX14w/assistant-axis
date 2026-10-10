"""Base-model generator, task 5: items out of a continuation, and the mechanical noun-to-adjective rule."""
import pytest

from assistant_axis.gapgen.generators.base_model import parse as PA
from assistant_axis.tests.base_model_fakes import ADJECTIVES, NOUNS

LEX = PA.Lexicon(adjectives=ADJECTIVES, nouns=NOUNS)


def surfaces(text, family="list"):
    return [i.surface for i in PA.extract_items(text, family)]


def test_split_commas_newline_and():
    assert surfaces(" stubborn, kind, generous, and fiercely loyal.") == ["stubborn", "kind", "generous",
                                                                          "fiercely loyal"]
    # a comma list ends at the first line break or sentence end; prose after it is not mined
    assert surfaces(" warm, calm\nAdjectives about work: diligent, prompt") == ["warm", "calm"]
    assert surfaces(" proud and vain. She was born in 1950 in Ohio, and moved") == ["proud", "vain"]
    assert surfaces(" kind but stern; patient") == ["kind", "stern", "patient"]


def test_spans_of_one_to_four_words_only():
    got = surfaces(" brave, fiercely loyal to her many friends, quick to anger")
    assert got == ["brave", "quick to anger"]


def test_determiners_and_intensifiers_stripped():
    assert surfaces(" a stubborn, the very kind, an extremely generous, always willing to listen") == [
        "stubborn", "kind", "generous", "willing to listen"]


def test_digits_and_non_latin_dropped():
    assert surfaces(" calm, 3d, 勇敢, naïve, top10") == ["calm", "naive"]


def test_lowercase_quotes_and_brackets():
    assert surfaces(' "Unflappable", (Warm), Calm!') == ["unflappable", "warm", "calm"]


def test_numbered_list_for_the_ai_family():
    text = " Tireless\n2. Never bored: it does not tire\n3. Overly literal - takes words at face value\n4. 4\nNotes"
    items = PA.extract_items(text, "ai_assistant")
    assert [i.surface for i in items] == ["tireless", "never bored", "overly literal"]
    assert items[1].gloss == "it does not tire" and items[2].gloss == "takes words at face value"


def test_gloss_lines():
    text = "unflappable: not easily upset\nbrash: offensively bold\nThe end of the list\nwarm: kind"
    items = PA.extract_items(text, "list_gloss")
    assert [(i.surface, i.gloss) for i in items] == [("unflappable", "not easily upset"),
                                                     ("brash", "offensively bold")]


def test_contrast_first_sentence():
    assert surfaces(" patient and kind, always willing to listen. Her sister never", "contrast") == [
        "patient", "kind", "willing to listen"]


def test_function_words_alone_dropped():
    assert surfaces(" and, the, so, kind") == ["kind"]


def test_truncated_last_item_dropped():
    """Real output (smoke round, 2026-10-10): 36 of 48 continuations hit the 80-token cap mid-word."""
    text = " modest, calm, quiet, patient, self-reliant, conscientio"
    assert [i.surface for i in PA.extract_items(text, "list", truncated=True)] == [
        "modest", "calm", "quiet", "patient", "self-reliant"]
    assert surfaces(text) == ["modest", "calm", "quiet", "patient", "self-reliant", "conscientio"]
    # a capped continuation that ended on a delimiter keeps its last item
    assert [i.surface for i in PA.extract_items(" calm, quiet,", "list", truncated=True)] == ["calm", "quiet"]
    gl = "honest: sincere\nhopeful: confident\nhumorless: not incl"
    assert [i.surface for i in PA.extract_items(gl, "list_gloss", truncated=True)] == ["honest", "hopeful"]
    ai = " collaborative\n2. cooperative\n3. cour"
    assert [i.surface for i in PA.extract_items(ai, "ai_assistant", truncated=True)] == ["collaborative",
                                                                                         "cooperative"]
    # a capped comma list that already ended its sentence is complete
    assert [i.surface for i in PA.extract_items(" calm, quiet. He was a lon", "list", truncated=True)] == [
        "calm", "quiet"]


def test_clause_fragments_dropped():
    # smoke-round examples: a sentence fragment is not a candidate
    assert surfaces(" creative, can be quite annoying, also very amusing, all excited") == [
        "creative", "amusing", "excited"]
    assert [i.surface for i in PA.extract_items(" Body has a wrist\n2. data-driven", "ai_assistant")] == ["data-driven"]


@pytest.mark.parametrize("word,expected", [
    ("stubbornness", ("stubborn", "adjective", "stubbornness")),
    ("kindness", ("kind", "adjective", "kindness")),
    ("happiness", ("happy", "adjective", "happiness")),
    ("carelessness", ("careless", "adjective", "carelessness")),
    ("generosity", ("generous", "adjective", "generosity")),
    ("curiosity", ("curious", "adjective", "curiosity")),
    ("sincerity", ("sincere", "adjective", "sincerity")),
    ("stupidity", ("stupid", "adjective", "stupidity")),
    ("hostility", ("hostile", "adjective", "hostility")),
    ("ability", ("able", "adjective", "ability")),
    # the lexicon lacks the adjective: kept as a noun, nothing recorded
    ("humility", ("humility", "noun", None)),
    ("zanyness", ("zanyness", "noun", None)),
])
def test_mechanical_normalization(word, expected):
    assert PA.normalize_form(word, lexicon=LEX) == expected


def test_normalization_only_when_lexicon_has_it():
    bare = PA.Lexicon(adjectives=frozenset(), nouns=frozenset())
    assert PA.normalize_form("stubbornness", lexicon=bare) == ("stubbornness", "noun", None)


@pytest.mark.parametrize("surface,form", [
    ("stubborn", "adjective"),          # adjective lexicon
    ("cold", "adjective"),              # both: the adjective wins
    ("temper", "noun"),                 # noun lexicon only
    ("loyalty", "noun"),                # an -ity noun whose adjective the rule cannot reach
    ("quick-tempered", "adjective"),    # hyphenated adjective lemma
    ("willing to listen", "phrase"),    # several words
    ("good listener", "phrase"),
    ("zorbish", "adjective"),           # unknown single word: treated as adjective-like (the floor decides)
])
def test_form_tag_truth_table(surface, form):
    assert PA.normalize_form(surface, lexicon=LEX)[1] == form
