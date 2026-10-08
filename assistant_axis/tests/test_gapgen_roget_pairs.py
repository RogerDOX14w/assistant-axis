"""Opposed-head reconstruction by rule (workstream 2, plan § 8 "Pairing", revised: no LLM pass)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.roget import pairs as PR
from assistant_axis.gapgen.generators.roget import wn_clusters as W
from assistant_axis.tests.roget_fakes import make_index, small_wordnet

REPO = Path(__file__).resolve().parents[2]


def test_negation_overlap_prefixes_and_suffixes():
    a = ["resolute", "decided", "hopeful", "honest", "regular"]
    b = ["irresolute", "undecided", "hopeless", "dishonest", "wavering"]
    s = PR.negation_overlap(a, b)
    assert s.n == 4 and s.frac == pytest.approx(4 / 5)
    assert ["resolute", "irresolute"] in s.examples
    assert PR.negation_overlap(b, a).n == 4                      # symmetric
    assert PR.negation_overlap(["conformist"], ["nonconformist", "x", "y"]).frac == 1.0   # shorter list
    assert PR.negation_overlap(["ware"], ["aware"]).n == 0        # short stems are not negations
    assert PR.negation_overlap(["mindful"], ["mindless"]).n == 1  # -ful / -less


def test_title_negation():
    assert PR.title_negation("Willingness", "Unwillingness")
    assert PR.title_negation("Choice", "Absence of Choice")
    assert PR.title_negation("Intellect", "Absence or want of Intellect")
    assert not PR.title_negation("Rashness", "Caution")


def test_wn_links_with_fake_wordnet():
    lex = W.Lexicon(small_wordnet())
    assert PR.wn_antonym_links(["cautious", "wary"], ["incautious", "rash"], lex) == 2
    assert PR.wn_antonym_links(["cautious"], ["brave"], lex) == 0
    assert PR.wn_antonym_links(["cautious"], ["incautious"], None) == 0
    # cluster level: wary (satellite of cautious) against unwary (satellite of incautious)
    assert PR.wn_cluster_coverage(["wary"], ["unwary"], lex) == 1.0
    assert PR.wn_cluster_coverage(["wary"], ["brave"], lex) == 0.0


def _subsection():
    """Two confirmed adjacent pairs, a lettered head beside the first, an unconfirmed head."""
    return make_index([
        {"id": "604", "title": "Resolution", "adj": [["resolute", "decided"], ["determined"]]},
        {"id": "604a", "title": "Perseverance", "adj": [["persevering"], ["steadfast"]]},
        {"id": "605", "title": "Irresolution", "adj": [["irresolute", "undecided"], ["wavering"]]},
        {"id": "606", "title": "Willingness", "adj": [["willing"], ["ready"]]},
        {"id": "607", "title": "Unwillingness", "adj": [["unwilling"], ["loath"]]},
        {"id": "608", "title": "Caprice", "adj": [["capricious"], ["whimsical"]]},
    ])


def test_rule_pairs_on_a_synthetic_subsection():
    idx = _subsection()
    p = PR.rule_pairs(idx, None)
    assert (p["604"].partner, p["605"].partner) == ("605", "604")
    assert p["604"].kind == "pair" and p["604"].source == "rule"
    assert p["604"].evidence["negation"]["n"] == 3     # resolute, decided and the titles
    assert (p["606"].partner, p["607"].partner) == ("607", "606")      # title negation
    assert p["604a"].kind == "triad" and p["604a"].members == ["604", "604a", "605"]
    assert p["608"].kind == "singleton"                                # its neighbour is paired
    assert PR.residue(idx, p) == []


def test_unresolved_and_residue():
    idx = make_index([
        {"id": "838", "title": "Rejoicing", "adj": [["jubilant"]], "klass": "VI"},
        {"id": "839", "title": "Lamentation", "adj": [["mournful"]], "klass": "VI"},
    ])
    p = PR.rule_pairs(idx, None)
    assert p["838"].kind == p["839"].kind == "unresolved"
    assert PR.residue(idx, p) == [(idx.subsection_key("838"), ["838", "839"])]
    # the position pass (off by default) pairs evidence-free neighbours, marked as such
    q = PR.rule_pairs(idx, None, position_pass=True)
    assert q["838"].partner == "839" and q["838"].source == "position"


def test_weak_pass_and_tiling_prefers_the_stronger_cover():
    lex = W.Lexicon(small_wordnet())
    idx = make_index([
        {"id": "1", "title": "Ease", "adj": [["easy"]]},
        {"id": "2", "title": "Caution", "adj": [["cautious"]]},
        {"id": "3", "title": "Rashness", "adj": [["incautious"], ["rash"]]},
        {"id": "4", "title": "Doubt", "adj": [["doubtful"]]},
    ])
    p = PR.rule_pairs(idx, lex)
    # one negation pair and one WordNet link (cautious / incautious) are weak evidence: 2 and 3 pair
    # as rule_weak; 1 and 4 have no evidence
    assert p["2"].partner == "3" and p["2"].source == "rule_weak"
    assert p["1"].kind == "singleton" and p["4"].kind == "singleton"
    assert PR.rule_pairs(idx, lex, weak_pass=False)["2"].kind == "unresolved"


def test_annotation_pairs_non_adjacent_heads():
    idx = make_index([
        {"id": "476", "title": "Reasoning", "adj": [["logical"]], "ants": ["478"]},
        {"id": "477", "title": "Intuition", "adj": [["intuitive"]]},
        {"id": "478", "title": "Demonstration", "adj": [["demonstrative"]], "ants": ["476"]},
    ])
    p = PR.rule_pairs(idx, None)
    assert p["476"].partner == "478" and p["476"].evidence["annotation"]


def test_tile_dynamic_programming():
    w = {("a", "b"): 3.0, ("b", "c"): 5.0, ("c", "d"): 3.0}
    got = PR._tile(["a", "b", "c", "d"], lambda x, y: w.get((x, y)), lambda h: False)
    assert got == [("a", "b"), ("c", "d")]                           # 6 beats 5
    got = PR._tile(["a", "x", "b"], lambda x, y: {("a", "b"): 2.0}.get((x, y)), lambda h: h == "x")
    assert got == [("a", "b")]                                       # across a lettered head


def test_known_pairs_check():
    idx = _subsection()
    p = PR.rule_pairs(idx, None)
    known = [{"a": "604", "b": "605", "title_a": "Resolution", "title_b": "Irresolution"},
             {"a": "606", "b": "607", "title_a": "Willingness", "title_b": "Unwillingness"},
             {"a": "604a", "b": "608", "title_a": "Perseverance", "title_b": "Caprice"},
             {"a": "604", "b": "605", "title_a": "Obedience", "title_b": "Irresolution"}]
    r = PR.check_known_pairs(idx, p, known)
    assert r["checked"] == 3 and len(r["hit"]) == 2 and len(r["miss"]) == 1 and len(r["dropped"]) == 1
    assert r["recall"] == pytest.approx(2 / 3, abs=1e-3)


def test_save_and_load_pairs(tmp_path):
    idx = _subsection()
    p = PR.rule_pairs(idx, None)
    path = PR.save_pairs(p, tmp_path / "head_pairs.json", meta={"note": "x"})
    env = json.loads(path.read_text(encoding="utf-8"))
    assert "_provenance" in env and env["result"]["note"] == "x"
    back = PR.load_pairs(path)
    assert {h: (x.partner, x.kind, x.source) for h, x in back.items()} == \
        {h: (x.partner, x.kind, x.source) for h, x in p.items()}


FULL = REPO / "data" / "external" / "roget" / "pg10681.txt"
WN_DB = REPO / "data" / "external" / "wn" / "wn.db"


@pytest.mark.skipif(not (FULL.exists() and WN_DB.exists()), reason="needs the Roget text and OEWN")
def test_full_text_known_pairs():
    """Acceptance (first measurement recorded 2026-10-08): 41 of 42 hand-listed pairs, one wrong
    (606 Obstinacy / 607 Tergiversation: 607 pairs weakly with 608 Caprice)."""
    from assistant_axis.gapgen.generators.roget import parse as P
    idx = P.parse_file(FULL)
    p = PR.rule_pairs(idx, W.Lexicon(W.oewn()))
    known = PR.load_known_pairs(REPO / "data" / "candidates" / "roget" / "known_pairs.json")
    r = PR.check_known_pairs(idx, p, known)
    assert r["recall"] >= 0.9 and len(r["wrong"]) <= 2 and not r["dropped"]
    for h in ("600", "601", "604a", "609a", "615a"):
        assert p[h].kind != "unresolved"
    # reciprocal by construction
    assert all(p[x.partner].partner == h for h, x in p.items() if x.partner)
