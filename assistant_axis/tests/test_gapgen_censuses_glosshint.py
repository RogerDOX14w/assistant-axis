"""Census generator, gloss hints from a fake OEWN."""
from assistant_axis.gapgen.generators.censuses import glosshint as G
from assistant_axis.tests.censuses_fakes import FakeWordnet

WN = FakeWordnet({
    "cool": [("a", [("neither warm nor very cold; giving relief from heat", "a"),
                    ("marked by calm self-control (especially in trying circumstances)", "a")]),
             ("n", [("the quality of being at a refreshingly low temperature", "n")])],
    "nodding": [("a", [("having branches or flower heads that bend downward", "s")])],
    "steady": [("a", [("having a red face", "s"), ("showing a disposition to persist", "s")])],
    "quandary": [("n", [("a situation from which extrication is difficult", "n")])],
    "whet": [("v", [("make keen or more acute", "v")])],
    "absent minded": [("a", [("lost in thought; abstracted", "s")])],
})


def senses(word):
    return G.adjective_senses(word, wordnet=WN)


def test_person_sense_outranks_first_sense():
    h = G.person_sense(senses("cool"))
    assert h.definition == "marked by calm self-control (especially in trying circumstances)"
    assert (h.rank, h.n_adj_senses, h.pos) == (2, 2, "a")


def test_strong_cue_outranks_weak_cue():
    h = G.person_sense(senses("steady"))
    assert h.rank == 2 and "disposition" in h.definition


def test_weak_cue_and_adjective_fallback():
    assert G.person_sense(senses("nodding")).definition.startswith("having branches")
    assert G.person_sense([G.Sense("bright", "a")]).definition == "bright"


def test_noun_and_verb_fallback():
    assert G.gloss_hint("quandary", G.person_sense(senses("quandary"))) == (
        "a situation from which extrication is difficult (noun)")
    assert G.gloss_hint("whet", G.person_sense(senses("whet"))) == "make keen or more acute (verb)"


def test_definition_cut_at_semicolon_and_forms():
    assert senses("cool")[0].definition == "neither warm nor very cold"
    assert senses("absent-minded")[0].definition == "lost in thought"     # hyphen -> space form
    assert G.lookup_forms("absent-minded") == ["absent-minded", "absent minded", "absentminded"]


def test_column_prefix_and_suffix():
    h = G.SenseHint("thrown into a state of agitated confusion", 1, 1, "s")
    assert G.gloss_hint("flustered", h, ["II"]) == (
        "disposition to be flustered (a general tendency, not an episode): thrown into a state of agitated confusion")
    assert G.gloss_hint("flustered", h, ["I", "II"]) == "thrown into a state of agitated confusion"
    assert G.gloss_hint("flustered", h, ["IV"]).endswith(" (metaphorical or doubtful in Allport-Odbert)")
    assert "metaphorical" not in G.gloss_hint("flustered", h, ["IV"], in_tda=True)
    noun = G.SenseHint("a situation", 1, 0, "n")
    assert G.gloss_hint("quandary", noun, ["II"]) == "a situation (noun)"     # no prefix on a noun sense


def test_word_limit_cuts_at_word_boundary():
    long = " ".join(f"word{i}" for i in range(40))
    out = G.gloss_hint("restless", G.SenseHint(long, 1, 1, "a"), ["II"])
    assert len(out.split()) == G.MAX_WORDS
    assert out.startswith("disposition to be restless") and out.split()[-1].startswith("word")
    out4 = G.gloss_hint("x", G.SenseHint(long, 1, 1, "a"), ["IV"])
    assert len(out4.split()) == G.MAX_WORDS and out4.endswith("(metaphorical or doubtful in Allport-Odbert)")


def test_absent():
    assert G.person_sense([]) is None and G.gloss_hint("x", None) is None
    assert senses("nonexistent") == []


def test_real_oewn_if_installed():
    import pytest
    from assistant_axis.gapgen.wordnet import oewn_installed
    if not oewn_installed():
        pytest.skip("OEWN not installed in data/external/wn")
    h = G.person_sense(G.adjective_senses("flustered"))
    assert h is not None and "agitated confusion" in h.definition
