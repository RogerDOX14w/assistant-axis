"""IPIP generator, evaluation: census overlap, known analogues, the covered_by inversion, naming agreement."""
import subprocess
import sys
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.generators.ipip import evaluate as E


def nm(label, antonym=None, kind="trait", single=False, amb=False):
    return {"label": label, "stem": label.replace(" ", "_").replace("-", "_"), "antonym_label": antonym,
            "kind": kind, "single_word_exists": single, "ambiguity_flag": amb}


ROWS = [
    {"granularity": 350, "cluster_id": 1, "consensus": "kept", "bipolar": True, "poles": [
        {"pole": "a", "items": ["H1"], "blind": nm("tidy", antonym="messy", single=True), "hinted": nm("orderly"),
         "labels_disagree": True},
        {"pole": "b", "items": ["H2"], "blind": nm("messy", antonym="tidy"), "hinted": nm("messy"),
         "labels_disagree": False}]},
    {"granularity": 350, "cluster_id": 2, "consensus": "kept", "bipolar": True, "poles": [
        {"pole": "a", "items": ["H3"], "blind": nm("quick to forgive", antonym="grudge-holding"),
         "hinted": nm("forgiving")},
        {"pole": "b", "items": ["H4"], "blind": nm("holds grudges", antonym="forgiving", amb=True)}]},
    {"granularity": 350, "cluster_id": 3, "consensus": "kept", "bipolar": False, "poles": [
        {"pole": "a", "items": ["H5"], "blind": nm("likes gardening", kind="membership")}]},
]


def test_census_overlap_through_the_frozen_table():
    table = [SimpleNamespace(stem="tidy"), SimpleNamespace(stem="messy"), SimpleNamespace(stem=None)]
    out = E.census_overlap(["tidy", "messy", "quick_to_forgive", "holds_grudges"], E.census_stems(table))
    assert out == {"n": 4, "n_census": 2, "share": 0.5, "words": ["messy", "tidy"]}


def test_census_stems_reads_the_frozen_loader(monkeypatch, tmp_path):
    import assistant_axis.gapgen.generators.censuses as C
    monkeypatch.setattr(C, "load_census_table", lambda path=None: [SimpleNamespace(stem="tidy")])
    p = tmp_path / "t.jsonl"
    p.write_text("")
    assert E.load_census_stems(p) == {"tidy"}
    assert E.load_census_stems(tmp_path / "missing.jsonl") is None


def test_known_analogues_normalise_construct_labels():
    corpus = {"anxiety", "orderliness", "artistic_interests", "achievement_striving", "orderly", "sociable", "kind"}
    constructs = ["Anxiety", "Orderliness", "Aesthetic Appreciation/Artistic Interests", "Achievement-striving",
                  "Sociability", "Gregariousness"]
    out = E.known_analogues(constructs, corpus)
    assert out["exact"] == {"achievement_striving": ["Achievement-striving"], "anxiety": ["Anxiety"],
                            "artistic_interests": ["Aesthetic Appreciation/Artistic Interests"],
                            "orderliness": ["Orderliness"]}
    # a second tier, by simple derivation, reported apart: sociability -> sociable, orderliness -> orderly
    assert out["variant"] == {"orderly": ["Orderliness"], "sociable": ["Sociability"]}


def test_recovery_from_covers_inverts_covered_by():
    reg = [
        {"key": "neat#1", "stem": "neat", "novelty": {"decision": "covered", "covered_by": "orderly"}},
        {"key": "anxious#1", "stem": "anxiety", "novelty": {"decision": "covered", "covered_by": "anxiety",
                                                             "exact_label": {"covered_by": "anxiety"}}},
        {"key": "fresh#1", "stem": "fresh", "novelty": {"decision": "new", "covered_by": None}},
        {"key": "x#1", "stem": "x"},
    ]
    out = E.recovery_from_covers(reg, ["anxiety", "orderly", "sociable"])
    assert out["n_analogues"] == 3 and out["n_hit"] == 2 and out["share"] == pytest.approx(2 / 3, abs=1e-4)
    assert out["hits"] == {"anxiety": ["anxious#1"], "orderly": ["neat#1"]} and out["misses"] == ["sociable"]
    assert out["target"] == 0.9


def test_naming_agreement():
    out = E.naming_agreement(ROWS)
    # 2 bipolar clusters, 4 directions: tidy->messy exact, messy->tidy exact, quick to forgive -> grudge-holding vs
    # "holds grudges" (shared word "grudge"), holds grudges -> forgiving vs "quick to forgive" (shared "forgiv")
    assert out["bipolar_directions"] == 4 and out["antonym_exact"] == 2 and out["antonym_agreement"] == 1.0
    assert out["antonym_target"] == 0.8
    assert out["n_both_forms"] == 3 and out["disagree_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert out["kind"]["blind"] == {"membership": 1, "trait": 4} and out["n_named"]["blind"] == 5
    assert out["kind"]["hinted"] == {"trait": 3}
    assert "is_trait" not in out
    assert out["single_word_exists"] == pytest.approx(1 / 5) and out["ambiguity_flag"] == pytest.approx(1 / 5)


def test_kind_against_m1_is_a_cross_tab():
    """QUESTIONS 48: the guess is made in M1's vocabulary so that the two can be set side by side."""
    reg = {"tidy": {"filter": {"verdict": "trait", "tags": []}},
           "messy": {"filter": {"verdict": "trait", "tags": ["membership"]}},
           "likes_gardening": {"filter": {"verdict": "trait", "tags": ["membership"],
                                          "membership_kind": "affinity"}},
           "quick_to_forgive": {"filter": {"verdict": "tagged", "tags": ["state"]}}}
    out = E.kind_against_m1(ROWS, reg)
    assert out["n_pairs"] == 4 and out["form"] == "blind"
    assert out["cross"] == {"membership / trait": 1, "trait / tagged": 1, "trait / trait": 2}
    assert out["m1_tags"] == {"membership": 2, "state": 1}
    # tidy (trait, no kind tag), messy (trait against M1's trait + membership) and likes gardening
    # (membership against M1's membership tag) agree; quick-to-forgive, guessed trait and tagged state, does
    # not.  trait and membership count as compatible in both directions, because Roger's decision 3 makes a
    # membership a trait: M1 passes it with verdict trait and a membership tag.
    assert out["n_agree"] == 3 and out["agreement"] == 0.75
    assert E.kind_against_m1(ROWS, {})["n_pairs"] == 0


def test_antonym_match_levels():
    assert E.antonym_match("last-minute", "last minute") == "exact"
    assert E.antonym_match("grudge-holding", "holds grudges") == "overlap"
    assert E.antonym_match("calm", "anxious") is None


def test_useful_per_dollar_and_cost_summary(tmp_path):
    import json
    p = tmp_path / "usage.json"
    p.write_text(json.dumps({"per_model": {"claude-haiku-5-5": {"cost_usd": 0.5}, "claude-sonnet-5-5": {"cost_usd": 1.5}}}))
    c = E.cost_summary({"naming": p, "missing": tmp_path / "nope.json"})
    assert c["per_model"] == {"claude-haiku-5-5": 0.5, "claude-sonnet-5-5": 1.5} and c["total_usd"] == 2.0
    assert c["by_stage"] == {"naming": 2.0}
    reg = [{"novelty": {"decision": "new"}}, {"novelty": {"decision": "covered", "pair_completion_for": ["x"]}},
           {"novelty": {"decision": "covered"}}]
    assert E.useful_per_dollar(reg, 2.0) == {"n_new": 1, "n_pair_completion": 1, "useful": 2, "usd": 2.0, "per_dollar": 1.0}


def test_package_imports_neither_anthropic_nor_openai():
    code = ("import sys\n"
            "import assistant_axis.gapgen.generators.ipip as P\n"
            "from assistant_axis.gapgen.generators.ipip import sources, download, ingest, cluster, naming, granularity, "
            "submit, evaluate, report, corpus\n"
            "bad = [m for m in ('anthropic', 'openai') if m in sys.modules]\n"
            "print(','.join(bad))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "", f"imported at import time: {out}"
