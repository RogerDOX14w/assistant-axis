"""WordNet lookups and the ``wn_clusters`` sibling stream (workstream 2, plan § 8 "WordNet clusters").

A fake ``wn`` handle (``roget_fakes.FakeWordnet``) pins our wrapper; one smoke test reads the real
Open English WordNet and skips when ``data/external/wn`` has no database."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.roget import wn_clusters as W
from assistant_axis.gapgen.generators.roget.mapping import LabelRecord
from assistant_axis.tests.roget_fakes import small_wordnet


def zipf(w: str) -> float:
    return {"incautious": 2.6, "unwary": 2.2, "cowardly": 3.4, "courageous": 3.8, "cautious": 3.9,
            "deep": 4.5}.get(w, 3.0)


@pytest.fixture()
def lex():
    return W.Lexicon(small_wordnet())


def test_adj_synsets_include_satellites(lex):
    assert [s.id for s in lex.adj_synsets("wary")] == ["s-wary"]
    assert [s.id for s in lex.adj_synsets("cautious")] == ["a-cautious"]
    assert lex.is_adjective("wary") and not lex.is_adjective("caution")


def test_direct_and_indirect_antonyms(lex):
    assert lex.antonyms("cautious") == [("incautious", "a-incautious")]
    # a satellite with no antonym of its own: its cluster head's antonym
    assert lex.antonyms("wary") == [("incautious", "a-incautious")]
    assert lex.antonyms("caution") == []


def test_cluster_heads_and_antonym_heads(lex):
    assert lex.head_synsets("wary") == {"a-cautious"}
    assert lex.head_synsets("cautious") == {"a-cautious"}
    assert lex.antonym_heads("wary") == {"a-incautious"}
    assert "a-incautious" in lex.head_synsets("unwary")


def test_derivations(lex):
    assert ("caution", "n") in lex.derivations("cautious")
    assert lex.derivational_adjs(lex.synsets("caution", "n")[0]) == ["cautious"]


def test_cluster(lex):
    c = lex.cluster(lex.synsets("wary", "s")[0])
    assert c.head_id == "a-cautious"
    assert c.satellites == [("s-wary", ["wary", "chary"])]
    assert c.antonym_head_id == "a-incautious"


def test_trait_closure_is_bounded(lex):
    deep = lex.trait_closure(["trait"], max_depth=3, root_synsets=["n-trait"])
    assert {k: d for k, (_, d) in deep.items()} == {"n-trait": 0, "n-courage": 1, "n-caution": 2, "n-mid": 3}
    shallow = lex.trait_closure(["trait"], max_depth=1, root_synsets=["n-trait"])
    assert set(shallow) == {"n-trait", "n-courage"}


def test_harvest_wn_antonyms_only_for_partnerless_existing_labels(lex):
    recs = [LabelRecord("cautious", "cautious", "d", "existing", None, None, False),
            LabelRecord("brave", "brave", "d", "existing", None, "cowardly", True),       # partner has a file
            LabelRecord("wary", "wary", "d", "queued", "candidate", None, False)]          # queued: skipped
    items = W.harvest_wn_antonyms(recs, lex, known_stems={"cautious", "brave", "wary"}, zipf=zipf)
    assert [(it.surface, it.partner_hint, it.synset_id, it.route) for it in items] == \
        [("incautious", "cautious", "a-incautious", "antonym")]
    assert items[0].gloss_hint == "This means lacking in caution."
    # a word already known is never emitted
    assert W.harvest_wn_antonyms(recs, lex, known_stems={"cautious", "incautious"}, zipf=zipf) == []


def test_harvest_trait_closure(lex):
    items = W.harvest_trait_closure(lex, known_stems={"cautious"}, zipf=zipf, max_depth=3, root_synsets=["n-trait"])
    by = {it.surface: it for it in items}
    assert set(by) == {"courageous"}           # cautious known; deep lies below the depth bound
    assert by["courageous"].gloss_hint.startswith("This means having courage: ")
    assert by["courageous"].synset_id == "n-courage"
    deeper = W.harvest_trait_closure(lex, known_stems=set(), zipf=zipf, max_depth=4, root_synsets=["n-trait"])
    assert {it.surface for it in deeper} == {"courageous", "cautious", "deep"}


def test_freq_floor_drops_only_rare_words_without_a_gloss_hint():
    """Rule 1b (Roger, 2026-10-12): a word below the floor with a gloss hint (its synset's definition) goes to
    M1's probe; one with no hint is still rejected.  Before, every word below the floor without a negating
    prefix was dropped here (the test asserted ``[]`` for the hinted antonym)."""
    recs = [LabelRecord("cautious", "cautious", "d", "existing", None, None, False)]
    c = Counter()
    items = W.harvest_wn_antonyms(recs, W.Lexicon(small_wordnet()), known_stems={"cautious"}, zipf=lambda w: 0.5,
                                  counts=c)
    assert [(it.surface, it.rescue, it.gloss_hint) for it in items] == \
        [("incautious", "gloss_hint", "This means lacking in caution.")]
    assert c["below_line"] == 1 and c["rescued_gloss_hint"] == 1 and c["zipf_hard_reject"] == 0
    wn = small_wordnet()
    wn.synset("a-incautious")._def = ""                              # no definition, so no gloss hint
    c = Counter()
    assert W.harvest_wn_antonyms(recs, W.Lexicon(wn), known_stems={"cautious"}, zipf=lambda w: 0.5, counts=c) == []
    assert c["below_line"] == 1 and c["zipf_hard_reject"] == 1


WN_DB = Path(__file__).resolve().parents[2] / "data" / "external" / "wn" / "wn.db"


@pytest.mark.skipif(not WN_DB.exists(), reason="Open English WordNet not installed in data/external/wn")
def test_real_oewn_smoke():
    lex = W.Lexicon(W.oewn())
    assert ("incautious", "oewn-00327334-a") in lex.antonyms("cautious")
    assert lex.antonym_heads("jubilant") & lex.head_synsets("dejected")


def test_closure_hint_when_the_noun_is_spelt_as_the_adjective():
    """Review 2026-10-12: OEWN has noun senses spelt as their adjective ("defensive", "mum"), and the hint read
    "This means having defensive: ..."; it is now the definition alone."""
    wn = small_wordnet()
    wn.add("n-defensive", "n", ["defensive"], "an attitude of defensiveness")
    wn.add("a-defensive", "a", ["defensive"], "attempting to justify or defend in speech or writing")
    wn.derivation("defensive", "a-defensive", "defensive", "n-defensive")
    wn.hyponym("n-trait", "n-defensive")
    lex = W.Lexicon(wn)
    items = W.harvest_trait_closure(lex, known_stems={"cautious", "courageous"}, zipf=zipf, max_depth=1,
                                    root_synsets=["n-trait"])
    by = {it.surface: it for it in items}
    assert by["defensive"].gloss_hint == "This means an attitude of defensiveness."


# --------------------------------------------------------------------------- depth 6 and the drop counts

def _deep_wordnet():
    """small_wordnet's chain (trait 0, courage 1, caution 2, middleness 3, deepness 4) carried on to depth 7:
    a planted trait adjective at depths 4 (deep), 5 (pernickety), 6 (uppity) and 7 (beyond the bound)."""
    wn = small_wordnet()
    for sid, noun, adj, parent in (("n-five", "pernicketiness", "pernickety", "n-deep"),
                                   ("n-six", "uppitiness", "uppity", "n-five"),
                                   ("n-seven", "bumptiousness", "bumptious", "n-six")):
        wn.add(sid, "n", [noun], f"the trait of being {adj}")
        wn.add(f"a-{adj}", "a", [adj], f"being {adj}")
        wn.derivation(adj, f"a-{adj}", noun, sid)
        wn.hyponym(parent, sid)
    return wn


def test_closure_default_depth_is_six():
    """Roger, 2026-10-12: the bound goes from 3 to 6 (no derivation for 3; the 117 words beyond it 97% traits)."""
    from assistant_axis.gapgen.generators.roget.harvest import HarvestConfig
    assert W.WN_CLOSURE_DEPTH == 6 and HarvestConfig().wn_closure_depth == 6
    lex = W.Lexicon(_deep_wordnet())
    c = Counter()
    items = W.harvest_trait_closure(lex, known_stems=set(), zipf=zipf, root_synsets=["n-trait"], counts=c)
    depth = {it.surface: it.extra["depth"] for it in items}
    assert depth == {"courageous": 1, "cautious": 2, "deep": 4, "pernickety": 5, "uppity": 6}
    assert "bumptious" not in depth                                   # depth 7: one past the bound
    assert c["depth_cut_off_synsets"] == 1 and c["depth_cut_off_adjectives"] == 1
    old = W.harvest_trait_closure(lex, known_stems=set(), zipf=zipf, root_synsets=["n-trait"], max_depth=3)
    assert {it.surface for it in old} == {"courageous", "cautious"}   # the bound before 2026-10-12


def test_closure_drop_counts_and_rescues():
    wn = _deep_wordnet()
    wn.add("n-nodef", "n", ["fainéance"], "")                          # no definition: no gloss hint
    wn.add("a-faineant", "a", ["faineant"], "")
    wn.derivation("faineant", "a-faineant", "fainéance", "n-nodef")
    wn.hyponym("n-trait", "n-nodef")
    wn.add("n-multi", "n", ["good nature"], "a cheerful willingness to be agreeable")
    wn.add("a-multi", "a", ["good natured"], "having an easygoing disposition")
    wn.derivation("good natured", "a-multi", "good nature", "n-multi")
    wn.hyponym("n-trait", "n-multi")
    rare = {"pernickety": 1.1, "uppity": 0.0, "faineant": 0.0}
    c = Counter()
    items = W.harvest_trait_closure(W.Lexicon(wn), known_stems={"cautious"}, taken={"courageous"},
                                    zipf=lambda w: rare.get(w, 3.0), root_synsets=["n-trait"], counts=c)
    by = {it.surface: it for it in items}
    assert set(by) == {"deep", "pernickety", "uppity"}
    assert by["pernickety"].rescue == "gloss_hint" and by["uppity"].rescue == "gloss_hint"
    assert by["deep"].rescue is None
    # synsets below the roots: courage, caution, middleness, deepness, five, six, nodef, multi; no adjective:
    # middleness; known: cautious; antonym route: courageous; multiword: good natured; faineant has no gloss
    # hint and is rejected
    assert c["synsets"] == 8 and c["no_adjective"] == 1
    assert (c["known"], c["antonym_route"], c["multiword"]) == (1, 1, 1)
    assert (c["below_line"], c["zipf_hard_reject"], c["rescued_gloss_hint"]) == (3, 1, 2)


def test_antonym_route_counts():
    recs = [LabelRecord("cautious", "cautious", "d", "existing", None, None, False),
            LabelRecord("wary", "wary", "d", "existing", None, None, False),
            LabelRecord("brave", "brave", "d", "existing", None, "cowardly", True)]
    c = Counter()
    items = W.harvest_wn_antonyms(recs, W.Lexicon(small_wordnet()), known_stems={"cautious", "wary", "brave"},
                                  zipf=zipf, counts=c)
    assert [it.surface for it in items] == ["incautious"]
    # two partner-less labels looked up; both give incautious (wary through its cluster head): one repeat
    assert c["labels"] == 2 and c["repeat"] == 1 and c["below_line"] == 0
