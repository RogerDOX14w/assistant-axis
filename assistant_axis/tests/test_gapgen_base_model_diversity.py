"""The diversity harness (frozen interface of plan 03 section 7): rarefaction, Chao1, collapse index,
string recovery, per-family splits."""
import pytest

from assistant_axis.gapgen.generators.base_model import diversity as D


def test_rarefaction_flat_stream():
    stream = ["a", "b", "a", "c", "a", "d", "b", "e"]
    # every emission counts one step; points every 3 emissions plus the end
    assert D.rarefaction(stream, step=3) == [(3, 2), (6, 4), (8, 5)]
    assert D.rarefaction(stream, step=8) == [(8, 5)]
    assert D.rarefaction([], step=5) == []


def test_rarefaction_grouped_by_sample():
    # one list per sample: the x axis counts samples, not emissions
    per_sample = [["a", "b"], ["a"], ["c", "d", "a"], [], ["e"]]
    assert D.rarefaction(per_sample, step=2) == [(2, 2), (4, 4), (5, 5)]
    with pytest.raises(ValueError):
        D.rarefaction(["a"], step=0)


def test_chao1_hand_computed():
    # S_obs = 5; f1 = 3 (c, d, e), f2 = 1 (b): 5 + 3*3 / (2*1) = 9.5
    counts = {"a": 4, "b": 2, "c": 1, "d": 1, "e": 1}
    assert D.chao1(counts) == pytest.approx(9.5)
    assert D.chao1(list(counts.values())) == pytest.approx(9.5)
    # no doubletons: the bias-corrected form S + f1 (f1 - 1) / 2 = 3 + 2*1/2 = 4
    assert D.chao1({"a": 1, "b": 1, "c": 3}) == pytest.approx(4.0)
    # no singletons: the observed count
    assert D.chao1({"a": 2, "b": 5}) == pytest.approx(2.0)
    assert D.chao1({}) == 0.0


def test_collapse_index():
    counts = {f"w{i}": 1 for i in range(100)} | {"top": 100}
    # the top 50 hold 100 + 49 of 200 emissions
    assert D.collapse_index(counts, top=50) == pytest.approx(149 / 200)
    assert D.collapse_index({"a": 3, "b": 1}, top=1) == pytest.approx(0.75)
    assert D.collapse_index({}, top=50) == 0.0


def test_string_recovery_resolves_renamed_from():
    corpus = {"kind", "stoic", "unreliable", "cheerful"}
    renamed = {"undependable": "unreliable"}          # old stem -> current stem
    r = D.string_recovery(["kind", "undependable", "zany", "kind"], corpus, renamed)
    assert r["n_corpus"] == 4 and r["found"] == 2 and r["recall"] == pytest.approx(0.5)
    assert r["found_stems"] == ["kind", "unreliable"]
    assert r["via_renamed_from"] == {"undependable": "unreliable"}
    assert D.string_recovery([], corpus, {})["recall"] == 0.0


def test_per_family_splits_sum_to_totals():
    rows = [{"stem": "a", "count": 5, "families": {"list": 3, "person": 2}},
            {"stem": "b", "count": 2, "families": {"list": 2}},
            {"stem": "c", "count": 1, "families": {"ai_assistant": 1}}]
    samples = [{"family": "list"}, {"family": "list"}, {"family": "person"}, {"family": "ai_assistant"}]
    pf = D.per_family(rows, samples=samples)
    assert sum(v["n_emissions"] for v in pf.values()) == sum(r["count"] for r in rows)
    assert sum(v["n_samples"] for v in pf.values()) == len(samples)
    assert pf["list"]["n_unique"] == 2 and pf["person"]["n_unique"] == 1 and pf["ai_assistant"]["n_unique"] == 1
    assert pf["list"]["uniques_per_1k"] == pytest.approx(1000.0)
    assert pf["list"]["n_only_here"] == 1 and pf["person"]["n_only_here"] == 0
