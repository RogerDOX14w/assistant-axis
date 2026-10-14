"""The shared noun-to-adjective relabel helper (``assistant_axis/gapgen/nouns.py``;
``reports/trait_gap_generation/coding_plan_noun_normalization.md`` sections 5 and 8).

Everything but :class:`TestRealOewn` runs on :class:`FakeLookups`: no OEWN, no wordfreq."""
import pytest

from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen.registry import Candidate

D = N.Derivation


def fake(**kw):
    """A small fake lexicon: one word per branch of the rule order."""
    pos = {
        "atheist": ["a", "n"], "run": ["v"], "stubbornness": ["n"], "stubborn": ["a"],
        "pedant": ["n"], "pedantic": ["a"], "rat": ["n", "v"], "ratty": ["a", "s"],
        "empathy": ["n"], "empathetic": ["a"], "narcissist": ["n"], "narcissistic": ["a"],
        "hypocrite": ["n"], "hypocritical": ["a"], "fool": ["n", "v"], "foolish": ["a"],
        "honesty": ["n"], "honest": ["a"], "doctor": ["n", "v"], "doctoral": ["a"], "doctorial": ["a"],
        "fogy": ["n"], "fogyish": ["a"], "child": ["n"], "childly": ["a"], "childlike": ["a"],
        "personality": ["n"], "personal": ["a"], "slipper": ["n"], "slippery": ["a"],
        "pimp": ["n"], "pimply": ["a"], "plumber": ["n"], "bacon": ["n"], "grace": ["n"], "graceful": ["a"],
        "yes-man": ["n"],
    }
    lexfiles = {
        "atheist": {"noun.person"}, "stubbornness": {"noun.attribute"}, "pedant": {"noun.person"},
        "rat": {"noun.animal"}, "empathy": {"noun.feeling"}, "narcissist": {"noun.person"},
        "hypocrite": {"noun.person"}, "fool": {"noun.person"}, "honesty": {"noun.attribute", "noun.plant"},
        "doctor": {"noun.person", "noun.act"}, "fogy": {"noun.person"}, "child": {"noun.person"},
        "personality": {"noun.attribute", "noun.person"}, "slipper": {"noun.artifact", "noun.person"},
        "pimp": {"noun.person"}, "plumber": {"noun.person"}, "bacon": {"noun.food"}, "grace": {"noun.attribute"},
        "yes-man": {"noun.person"},
    }
    derivations = {
        "pedant": [D("pedantic", "noun.person", "marked by a narrow focus on learning")],
        "rat": [D("ratty", "noun.animal", "of or characteristic of rats")],
        "empathy": [D("empathetic", "noun.feeling", "showing empathy")],
        "doctor": [D("doctorial", "noun.person", "of or relating to a doctor or doctorate"),
                   D("doctoral", "noun.person", "of or relating to a doctor or doctorate")],
        "child": [D("childly", "noun.person", "befitting a young child")],
        "personality": [D("personal", "noun.attribute", "of or arising from personality")],
    }
    definitions = {
        "pedantic": ["marked by a narrow focus on learning"], "ratty": ["of or characteristic of rats"],
        "empathetic": ["showing empathy"], "narcissistic": ["characteristic of those having an inflated idea"],
        "hypocritical": ["professing feelings or virtues one does not have"],
        "foolish": ["devoid of good sense or judgment"], "honest": ["not disposed to cheat or defraud"],
        "doctoral": ["of or relating to a doctor or doctorate"],
        "doctorial": ["of or relating to a doctor or doctorate"], "fogyish": ["old-fashioned"],
        "childly": ["befitting a young child"], "childlike": ["befitting a young child"],
        "personal": ["concerning a particular person", "of or arising from personality"],
        "slippery": ["causing things to slip", "not to be trusted"], "pimply": ["having pimples"],
        "graceful": ["characterized by beauty of movement"], "stubborn": ["tenaciously unwilling to yield"],
    }
    mates = {"childly": {"childly", "childlike"}, "childlike": {"childly", "childlike"}}
    zipf = {"pedantic": 2.66, "ratty": 2.47, "empathetic": 2.94, "narcissistic": 3.22, "hypocritical": 3.31,
            "foolish": 3.89, "honest": 4.73, "doctoral": 3.55, "doctorial": 0.0, "fogyish": 0.0, "childly": 0.0,
            "childlike": 2.94, "personal": 5.2, "slippery": 3.61, "pimply": 2.0, "graceful": 3.3,
            "stubborn": 3.6}
    args = dict(pos=pos, lexfiles=lexfiles, derivations=derivations, definitions=definitions, mates=mates,
                zipf=zipf)
    args.update(kw)
    return N.FakeLookups(**args)


L = fake()


def rl(word, lookups=L):
    return N.relabel(word, lookups=lookups)


class TestRuleOrder:
    def test_phrase(self):
        r = rl("bit of a pedant")
        assert isinstance(r, N.NoRelabel) and r.reason == "phrase"

    def test_not_in_oewn(self):
        assert rl("zorbish").reason == "not_in_oewn"

    def test_has_adjective_sense(self):
        assert rl("atheist").reason == "has_adjective_sense"

    def test_not_a_noun(self):
        assert rl("run").reason == "not_a_noun"

    def test_existing_suffix_fold(self):
        r = rl("stubbornness")
        assert isinstance(r, N.Relabel)
        assert (r.adjective, r.rule) == ("stubborn", "suffix:noun_suffix")
        assert r.helper_version == N.HELPER_VERSION

    def test_derivation_from_a_person_sense(self):
        r = rl("pedant")
        assert (r.surface, r.adjective, r.rule, r.lexfile) == ("pedant", "pedantic", "derivation", "noun.person")
        assert r.definition == "marked by a narrow focus on learning"
        assert r.zipf == 2.66

    def test_thing_sense_link_refused(self):
        r = rl("rat")
        assert isinstance(r, N.NoRelabel) and r.reason == "other_noun"

    def test_quality_link(self):
        r = rl("empathy")
        assert (r.adjective, r.rule, r.lexfile) == ("empathetic", "derivation", "noun.feeling")

    @pytest.mark.parametrize("noun,adj,rule", [("narcissist", "narcissistic", "suffix:-ist+istic"),
                                               ("hypocrite", "hypocritical", "suffix:-ite+itical"),
                                               ("fool", "foolish", "suffix:+ish")])
    def test_person_suffix_rules(self, noun, adj, rule):
        r = rl(noun)
        assert (r.adjective, r.rule, r.lexfile) == (adj, rule, "noun.person")

    def test_quality_suffix_rule(self):
        r = rl("honesty")
        assert (r.adjective, r.rule, r.lexfile) == ("honest", "suffix:-ty+t", "noun.attribute")
        assert r.definition == "not disposed to cheat or defraud"

    def test_quality_suffix_ful(self):
        assert (rl("grace").adjective, rl("grace").rule) == ("graceful", "suffix:+ful")

    def test_y_and_ly_rules_decision_2c(self):
        # Roger, 2026-10-14: +y and +ly are in (decision 2, (c)); their sense is not checked
        assert (rl("slipper").adjective, rl("slipper").rule) == ("slippery", "suffix:+y")
        assert (rl("pimp").adjective, rl("pimp").rule) == ("pimply", "suffix:+ly")

    def test_pertainym_only(self):
        assert rl("doctor").reason == "pertainym_only"

    def test_below_floor(self):
        assert rl("fogy").reason == "below_floor"

    def test_spelling_mate(self):
        r = rl("child")
        assert (r.adjective, r.rule, r.zipf) == ("childlike", "derivation+spelling", 2.94)

    def test_person_with_no_adjective(self):
        assert rl("plumber").reason == "person_no_adjective"
        assert rl("yes-man").reason == "person_no_adjective"

    def test_other_noun(self):
        assert rl("bacon").reason == "other_noun"

    def test_reasons_are_the_listed_ones(self):
        for w in ("bit of a pedant", "zorbish", "atheist", "run", "rat", "doctor", "fogy", "plumber", "bacon"):
            assert rl(w).reason in N.REASONS

    def test_ity_sense_drift_exceptions(self):
        # personality is not being personal, by the suffix fold or by OEWN's derivation link
        for w in ("personality", "reality", "mentality", "nationality", "sexuality", "individuality", "actuality",
                  "speciality", "locality", "totality", "legality"):
            assert w in N.SUFFIX_EXCEPTIONS
        r = rl("personality")
        assert isinstance(r, N.NoRelabel), r

    def test_case_and_hyphen_forms(self):
        assert rl("Pedant").adjective == "pedantic"

    def test_idempotent(self):
        for w in ("stubbornness", "pedant", "empathy", "narcissist", "hypocrite", "fool", "honesty", "child",
                  "slipper", "pimp", "grace"):
            r = rl(w)
            assert isinstance(r, N.Relabel), w
            assert rl(r.adjective).reason == "has_adjective_sense", w


class TestRouteText:
    def test_suffix_rule_says_sense_not_checked(self):
        r = rl("slipper")
        block = N.relabel_blocks("slipper#1", "slippery#1", r, run="base_model/r1", now="T")[1]
        assert N.route_text(block) == "suffix rule +y from 'slipper', sense not checked"

    def test_derivation_names_the_lexfile(self):
        r = rl("pedant")
        noun_b, adj_b = N.relabel_blocks("pedant#1", "pedantic#1", r, run="censuses/r", now="T")
        assert N.route_text(adj_b) == "derivation link from 'pedant' (noun.person)"
        assert N.route_text(noun_b) == "adjective 'pedantic' by derivation link (noun.person)"

    def test_corpus_stem(self):
        r = rl("fool")
        noun_b, adj_b = N.relabel_blocks("fool#1", None, r, corpus_stem="foolish", now="T")
        assert adj_b is None
        assert N.route_text(noun_b) == "adjective 'foolish' (a corpus trait) by suffix rule +ish, sense not checked"

    def test_llm_relabel_says_sense_not_checked(self):
        """The one-off Haiku pass (``noun_relabel.py llm-apply``; Roger 2026-10-14)."""
        r = N.Relabel("cad", "caddish", N.LLM_RULE, None, None, 1.2)
        noun_b, adj_b = N.relabel_blocks("cad#1", "caddish#1", r, run="noun_relabel/llm-x", now="T")
        assert N.route_text(adj_b) == "LLM relabel from 'cad', sense not checked"
        assert N.route_text(noun_b) == "adjective 'caddish' by LLM relabel, sense not checked"
        noun_c, _ = N.relabel_blocks("cad#1", None, r, corpus_stem="caddish", now="T")
        assert N.route_text(noun_c) == "adjective 'caddish' (a corpus trait) by LLM relabel, sense not checked"

    def test_none(self):
        assert N.route_text(None) is None and N.route_text({}) is None


class TestDerived:
    def test_derived_candidate_field_by_field(self):
        c = Candidate(surface="pedant", generator="censuses", run_id="2026-10-11-allport_hi", rank=412, score=0.7,
                      gloss_hint="a narrow-minded scholar", sense_id=2, source_ref="tda:412", partner_hint="lax")
        d = N.derived_candidate(c, rl("pedant"))
        assert d == Candidate(surface="pedantic", generator="censuses", run_id="2026-10-11-allport_hi", rank=412,
                              score=0.7, gloss_hint="marked by a narrow focus on learning", sense_id=1,
                              source_ref="relabel:derivation:pedant", partner_hint=None)

    def test_relabel_candidates_skips_corpus_stems(self):
        cands = [Candidate(surface=s, generator="g", run_id="r") for s in ("pedant", "fool", "bacon", "gentle soul")]
        out = N.relabel_candidates(cands, lookups=L, corpus_stems={"foolish"})
        assert [(d.noun.surface, d.adjective.surface if d.adjective else None, d.corpus_stem) for d in out] == [
            ("pedant", "pedantic", None), ("fool", None, "foolish")]

    def test_relabel_candidates_renamed_from(self):
        cands = [Candidate(surface="fool", generator="g", run_id="r")]
        out = N.relabel_candidates(cands, lookups=L, corpus_stems={"foolish": "silly"})
        assert out[0].corpus_stem == "silly" and out[0].adjective is None

    def test_relabel_candidates_dedupes_and_skips_derived(self):
        cands = [Candidate(surface="pedant", generator="g", run_id="r", source_ref="s1"),
                 Candidate(surface="pedant", generator="g", run_id="r", source_ref="s2"),
                 Candidate(surface="pedantic", generator="g", run_id="r", source_ref="relabel:derivation:pedant")]
        out = N.relabel_candidates(cands, lookups=L, corpus_stems=set())
        assert len(out) == 1 and out[0].noun.source_ref == "s1"

    def test_blocks_shape(self):
        r = rl("pedant")
        nb, ab = N.relabel_blocks("pedant#1", "pedantic#1", r, run="censuses/2026-10-11-allport_hi",
                                  now="2026-10-14T09:00:00+00:00")
        assert ab == {"from_key": "pedant#1", "from_surface": "pedant", "rule": "derivation", "lexfile": "noun.person",
                      "helper_version": N.HELPER_VERSION, "oewn": "oewn:2024", "run": "censuses/2026-10-11-allport_hi",
                      "at": "2026-10-14T09:00:00+00:00"}
        # the noun block carries the lexicographer file too (beside plan section 6's fields: the card's route text)
        assert nb == {"to_key": "pedantic#1", "rule": "derivation", "lexfile": "noun.person",
                      "helper_version": N.HELPER_VERSION, "oewn": "oewn:2024", "at": "2026-10-14T09:00:00+00:00"}
        nb2, ab2 = N.relabel_blocks("fool#1", None, rl("fool"), corpus_stem="foolish", now="T")
        assert ab2 is None and nb2["to_corpus_stem"] == "foolish" and "to_key" not in nb2


class TestRuleTablesPinned:
    def test_sha256_pinned_to_the_helper_version(self):
        # a change to any rule table must bump HELPER_VERSION and add its sha to RULES_HISTORY
        assert N.rules_sha256() == N.RULES_HISTORY[N.HELPER_VERSION]

    def test_parse_reexports_the_moved_names(self):
        from assistant_axis.gapgen.generators.base_model import parse as PA
        for name in ("Lexicon", "normalize_form_kind", "normalize_form", "us_spelling", "SUFFIX_EXCEPTIONS",
                     "NOUN_SUFFIXES", "ADVERB_EXCEPTIONS", "_UK_US"):
            assert getattr(PA, name) is getattr(N, name), name


# --------------------------------------------------------------------------- the real OEWN

def _oewn():
    try:
        from assistant_axis.gapgen.wordnet import oewn_installed
        return oewn_installed()
    except ImportError:
        return False


@pytest.mark.skipif(not _oewn(), reason="OEWN is not installed in data/external/wn")
class TestRealOewn:
    """Twelve words with their expected answers, so that an OEWN or ``wn`` upgrade shows."""

    EXPECTED = {
        "pedant": ("pedantic", "derivation"), "coward": ("cowardly", "derivation"),
        "snob": ("snobby", "derivation"), "atheist": "has_adjective_sense", "rat": "person_no_adjective",
        "doctor": "pertainym_only", "child": ("childlike", "derivation+spelling"),
        "narcissist": ("narcissistic", "suffix:-ist+istic"), "hypocrite": ("hypocritical", "suffix:-ite+itical"),
        "honesty": ("honest", "suffix:-ty+t"), "personality": "person_no_adjective",
        "yes-man": "person_no_adjective",
    }

    @pytest.fixture(scope="class")
    def lookups(self):
        return N.OewnLookups()

    @pytest.mark.parametrize("word", sorted(EXPECTED))
    def test_word(self, lookups, word):
        r = N.relabel(word, lookups=lookups)
        want = self.EXPECTED[word]
        if isinstance(want, tuple):
            assert isinstance(r, N.Relabel), r
            assert (r.adjective, r.rule) == want
            assert N.relabel(r.adjective, lookups=lookups).reason == "has_adjective_sense"
        else:
            assert isinstance(r, N.NoRelabel) and r.reason == want, r

    @pytest.mark.parametrize("word", ["hill", "wood", "funk", "fish"])
    def test_proper_names_are_not_person_nouns(self, lookups, word):
        """Review S4: OEWN's proper noun "Hill" (noun.person) must not make hill a person noun for the +y rule."""
        r = N.relabel(word, lookups=lookups)
        assert isinstance(r, N.NoRelabel), r

    def test_gloss_is_not_the_pertainym_sense(self, lookups):
        """Review S3: angel -> angelic is glossed by a dispositional sense, not "of or relating to angels"."""
        r = N.relabel("angel", lookups=lookups)
        assert isinstance(r, N.Relabel) and not N.PERTAINYM_RE.search(r.definition or ""), r

    @pytest.mark.parametrize("word", ["majority", "priority", "gravity", "activity"])
    def test_ity_sense_drifts_are_exceptions(self, lookups, word):
        assert isinstance(N.relabel(word, lookups=lookups), N.NoRelabel)

    def test_lexfile_present(self):
        from assistant_axis.gapgen.wordnet import oewn
        syn = oewn().words("pedant")[0].senses()[0].synset()
        assert syn.lexfile() == "noun.person"

    def test_lexfile_person_test_agrees_with_the_hyponym_closure(self, lookups):
        from wordfreq import zipf_frequency

        from assistant_axis.gapgen.generators.masked_lm.wordlist import person_noun_lemmas
        from assistant_axis.gapgen.wordnet import oewn
        closure = sorted((x for x in person_noun_lemmas(oewn()) if x.isalpha() and x == x.lower()),
                         key=lambda x: (-zipf_frequency(x, "en"), x))[:100]
        disagree = [x for x in closure if "noun.person" not in lookups.lexfiles(x)]
        assert len(disagree) <= 5, disagree
