"""Corpus-frames generator: a filler's fold through the platform's noun helper (plan section 8, ``relabel``; open
decision 3, built as ``assistant_axis.gapgen.nouns``).  Fake OEWN lookups; no local rules to test, only the
adapter's columns."""
from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen.generators.corpus_frames import relabel as R
from assistant_axis.tests.corpus_frames_fakes import PERSON_NOUNS, fake_nouns


def test_the_suffix_rules_of_the_helper():
    lk = fake_nouns()
    for noun, adj, rule in (("honesty", "honest", "suffix:-ty+t"), ("generosity", "generous", "suffix:noun_suffix"),
                            ("pugnacity", "pugnacious", "suffix:noun_suffix")):
        f = R.fold(noun, lookups=lk, kind_hint="noun")
        assert (f.surface, f.label, f.form, f.rule, f.reason) == (noun, adj, "adjective", rule, None), noun
        assert f.relabelled


def test_the_derivation_link():
    f = R.fold("pedant", lookups=fake_nouns(), kind_hint="noun")
    assert (f.label, f.rule, f.form) == ("pedantic", "derivation", "adjective")
    g = R.fold("Pedant", lookups=fake_nouns(), kind_hint="noun")
    assert (g.raw, g.surface, g.label) == ("Pedant", "pedant", "pedantic")


def test_a_noun_with_no_adjective_stays_the_label():
    f = R.fold("liar", lookups=fake_nouns(), kind_hint="noun")
    assert (f.surface, f.label, f.form, f.rule, f.reason) == ("liar", "liar", "noun", "none", "person_no_adjective")
    assert not f.relabelled


def test_an_adjective_is_left_alone_and_an_unknown_word_takes_the_frames_kind():
    lk = fake_nouns()
    f = R.fold("honest", lookups=lk, kind_hint="adj")
    assert (f.label, f.form, f.rule, f.reason) == ("honest", "adjective", None, "has_adjective_sense")
    assert R.fold("zorbish", lookups=lk, kind_hint="adj").form == "adjective"
    assert R.fold("zorbish", lookups=lk, kind_hint="noun").form == "noun"
    assert R.fold("good-natured", lookups=lk).form == "phrase"


def test_a_us_fold_records_the_british_spelling():
    lk = fake_nouns()
    f = R.fold("sceptical", lookups=lk)
    assert (f.raw, f.surface, f.label, f.us_spelling_from) == ("sceptical", "skeptical", "skeptical", "sceptical")
    g = R.fold("humour", lookups=lk, kind_hint="noun")        # spelling first, then the helper
    assert (g.surface, g.label, g.us_spelling_from, g.rule) == ("humor", "humorous", "humour", "derivation")
    assert R.fold("honest", lookups=lk).us_spelling_from is None


def test_is_person_noun_on_a_planted_hyponym():
    assert R.is_person_noun("liar", PERSON_NOUNS) and R.is_person_noun("Liar", PERSON_NOUNS)
    assert not R.is_person_noun("old", PERSON_NOUNS)
    assert R.is_person_noun("yes-man", {"yes man"}) and R.is_person_noun("story teller", {"story-teller"})


def test_the_adapter_has_no_rule_tables_of_its_own():
    # open decision 3's helper is the platform's: the adapter only calls it (its version stamps every block)
    names = set(vars(R))
    assert not {"SUFFIX_RULES", "PERSON_SUFFIX_RULES", "QUALITY_SUFFIX_RULES"} & names
    assert N.HELPER_VERSION >= 1
