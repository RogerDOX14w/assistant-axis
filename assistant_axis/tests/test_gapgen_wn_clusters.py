"""WordNet lookups and the ``wn_clusters`` sibling stream (workstream 2, plan § 8 "WordNet clusters").

A fake ``wn`` handle (``roget_fakes.FakeWordnet``) pins our wrapper; one smoke test reads the real
Open English WordNet and skips when ``data/external/wn`` has no database."""
from __future__ import annotations

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


def test_freq_floor_drops_rare_words(lex):
    recs = [LabelRecord("cautious", "cautious", "d", "existing", None, None, False)]
    items = W.harvest_wn_antonyms(recs, lex, known_stems={"cautious"}, zipf=lambda w: 0.5)
    assert items == []


WN_DB = Path(__file__).resolve().parents[2] / "data" / "external" / "wn" / "wn.db"


@pytest.mark.skipif(not WN_DB.exists(), reason="Open English WordNet not installed in data/external/wn")
def test_real_oewn_smoke():
    lex = W.Lexicon(W.oewn())
    assert ("incautious", "oewn-00327334-a") in lex.antonyms("cautious")
    assert lex.antonym_heads("jubilant") & lex.head_synsets("dejected")
