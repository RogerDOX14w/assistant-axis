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


class TestGateAudit3Leaks:
    """The parse leaks gate audit 3 found in the pilot table (base_model_table.md section 8, proposal 4; Roger
    accepted it on 2026-10-12)."""

    def test_a_list_ending_is_not_an_item(self):
        # `etc` reached the table at count 16 and cost an M1 call
        assert surfaces(" kind, generous, etc.") == ["kind", "generous"]
        assert surfaces(" calm, warm etc. She was") == ["calm", "warm"]
        assert surfaces(" brave, loyal and others.") == ["brave", "loyal"]
        assert surfaces(" brave, loyal, and so on") == ["brave", "loyal"]
        assert surfaces(" brave, et cetera") == ["brave"]

    def test_a_leading_be_and_frequency_adverbs_are_stripped(self):
        text = (" be sarcastic\n2. be a good listener\n3. occasionally robotic\n4. frequently late\n"
                "5. never bored\n6. overly literal\n7. not very social\n8. highly strung\n")
        assert [i.surface for i in PA.extract_items(text, "ai_assistant")] == [
            "sarcastic", "good listener", "robotic", "late",
            # words that carry the meaning stay
            "never bored", "overly literal", "not very social", "highly strung"]

    def test_a_little_and_a_bit_are_degree_words(self):
        assert surfaces(" a little shy, a bit lazy, a bit of a recluse, little, somewhat of a dreamer") == [
            "shy", "lazy", "bit of a recluse", "little", "somewhat of a dreamer"]
        # "be" goes, but a degree word heading an "of" phrase stays (not "of a dreamer")
        assert [i.surface for i in PA.extract_items(" be somewhat of a dreamer\n", "ai_assistant")] == [
            "somewhat of a dreamer"]

    def test_ai_assistant_items_are_split_on_and(self):
        text = (" unresponsive and dismissive: it ignores you\n2. considerate & thoughtful\n"
                "3. efficient, allowing for continuous operation\n4. fast processing speed and infinite memory\n"
                "5. patient listener: hears you out\n")
        items = PA.extract_items(text, "ai_assistant")
        # a comma inside an item starts an explanation, and an item longer than a row is prose: neither is mined
        # (both are dropped, as before; splitting them gave the reparsed pilot table rows such as "allowing for
        # continuous operation" and "fast processing speed")
        assert [i.surface for i in items] == ["unresponsive", "dismissive", "considerate", "thoughtful",
                                              "patient listener"]
        # a gloss written for the pair is no gloss of either word; a single item keeps its own
        assert [i.gloss for i in items] == [None] * 4 + ["hears you out"]


#: A lexicon with the adjectives the gate-audit-3 folds need (OEWN has all of them).
LEX3 = PA.Lexicon(
    adjectives=ADJECTIVES | {"incompetent", "bawdy", "gentle", "frantic", "kindly", "punctilious", "dull", "true",
                             "resilient", "efficient", "arrogant", "pugnacious", "ferocious", "optimistic",
                             "elitist", "cynical", "present", "organized", "self-centered", "good-humored",
                             "judgmental", "likable", "skillful", "untrammeled", "skeptical", "outer", "all",
                             "unshakable", "traveled", "over", "rare"},
    nouns=NOUNS | {"ally", "presence", "science", "perseverance", "tour", "tor", "colour", "color", "skepticism"})


@pytest.mark.parametrize("word,expected", [
    # -ly adverbs fold to the OEWN adjective (41 rows in the pilot)
    ("incompetently", ("incompetent", "adjective", "incompetently", "adverb")),
    ("bawdily", ("bawdy", "adjective", "bawdily", "adverb")),
    ("gently", ("gentle", "adjective", "gently", "adverb")),
    ("frantically", ("frantic", "adjective", "frantically", "adverb")),
    ("punctiliously", ("punctilious", "adjective", "punctiliously", "adverb")),
    ("dully", ("dull", "adjective", "dully", "adverb")),
    ("truly", ("true", "adjective", "truly", "adverb")),
    ("kindly", ("kindly", "adjective", None, None)),          # an OEWN adjective itself: kept
    ("ally", ("ally", "noun", None, None)),                   # an OEWN noun: not "all"
    ("zorbishly", ("zorbishly", "adjective", None, None)),    # no adjective to fold to: unchanged
    ("overly", ("overly", "adjective", None, None)),          # another sense than "over": an exception
    ("rarely", ("rarely", "adjective", None, None)),          # nor "rare"
    # further nouns of disposition (about 22 rows in the pilot)
    ("patience", ("patient", "adjective", "patience", "noun_suffix")),
    ("resilience", ("resilient", "adjective", "resilience", "noun_suffix")),
    ("efficiency", ("efficient", "adjective", "efficiency", "noun_suffix")),
    ("arrogance", ("arrogant", "adjective", "arrogance", "noun_suffix")),
    ("pugnacity", ("pugnacious", "adjective", "pugnacity", "noun_suffix")),
    ("ferocity", ("ferocious", "adjective", "ferocity", "noun_suffix")),
    ("optimism", ("optimistic", "adjective", "optimism", "noun_suffix")),
    ("elitism", ("elitist", "adjective", "elitism", "noun_suffix")),
    ("cynicism", ("cynical", "adjective", "cynicism", "noun_suffix")),
    ("presence", ("presence", "noun", None, None)),           # an exception: being present is another sense
    ("science", ("science", "noun", None, None)),             # a noun because OEWN says so
    ("perseverance", ("perseverance", "noun", None, None)),   # OEWN lacks the adjective: unchanged
    # British spellings become US (the entity-naming rule)
    ("organised", ("organized", "adjective", "organised", "us_spelling")),
    ("self-centred", ("self-centered", "adjective", "self-centred", "us_spelling")),
    ("good-humoured", ("good-humored", "adjective", "good-humoured", "us_spelling")),
    ("judgemental", ("judgmental", "adjective", "judgemental", "us_spelling")),
    ("likeable", ("likable", "adjective", "likeable", "us_spelling")),
    ("unshakeable", ("unshakable", "adjective", "unshakeable", "us_spelling")),
    ("skilful", ("skillful", "adjective", "skilful", "us_spelling")),
    ("untrammelled", ("untrammeled", "adjective", "untrammelled", "us_spelling")),
    # OEWN lacks the compound but has the changed word
    ("well-organised", ("well-organized", "adjective", "well-organised", "us_spelling")),
    ("travelled", ("traveled", "adjective", "travelled", "us_spelling")),
    ("well organised", ("well organized", "phrase", "well organised", "us_spelling")),
    ("colour", ("color", "noun", "colour", "us_spelling")),
    ("scepticism", ("skeptical", "adjective", "scepticism", "us_spelling+noun_suffix")),
    # the fold is kept only when OEWN has the result, and never turns a word into another one
    ("outre", ("outre", "adjective", None, None)),
    ("surprised", ("surprised", "adjective", None, None)),
    ("tour", ("tour", "noun", None, None)),
])
def test_gate_audit_3_folds(word, expected):
    assert PA.normalize_form_kind(word, lexicon=LEX3) == expected
    assert PA.normalize_form(word, lexicon=LEX3) == expected[:3]


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
