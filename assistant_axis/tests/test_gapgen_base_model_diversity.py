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


def test_round_stats_carries_every_section6_field():
    from assistant_axis.gapgen.generators.base_model import evaluate as EV
    from assistant_axis.tests.test_gapgen_base_model_table import SAMPLES, build
    per = []
    rows, counts = build(per_sample=per)
    st = EV.round_stats(SAMPLES, rows, per, counts, round_n=1, temperature=1.0, corpus_stems={"kind", "warm", "x"},
                        renamed={"undependable": "x"}, step=2)
    for k in ("round", "prompts_version", "n_samples", "n_raw_items", "n_unique", "n_eligible",
              "uniques_per_1k_samples", "rarefaction", "chao1", "collapse_top50_share", "noun_share_unique",
              "noun_share_eligible", "normalized_mechanically", "per_family", "recovery_strings", "temperature",
              "model"):
        assert k in st, k
    assert st["n_samples"] == 6 and st["rarefaction"][-1] == [6, st["n_unique"]]
    assert st["recovery_strings"]["found"] == 2 and st["recovery_strings"]["n_corpus"] == 3
    assert st["recovery_strings"]["by_family"]["contrast"] == pytest.approx(1 / 3, abs=1e-4)
    assert 0 < st["noun_share_unique"] < 1 and st["junk"]["empty_sample_share"] == 0.0
    assert sum(v["n_samples"] for v in st["per_family"].values()) == 6


PF_ROWS = [{"stem": "a", "count": 5, "families": {"list": 3, "person": 2}, "eligible": True},
           {"stem": "b", "count": 2, "families": {"list": 2}, "eligible": False},
           {"stem": "c", "count": 1, "families": {"ai_assistant": 1}, "eligible": True}]
PF_SAMPLES = [{"family": "list"}, {"family": "list"}, {"family": "person"}, {"family": "ai_assistant"}]


def test_per_family_splits_sum_to_totals():
    pf = D.per_family(PF_ROWS, samples=PF_SAMPLES)
    assert sum(v["n_emissions"] for v in pf.values()) == sum(r["count"] for r in PF_ROWS)
    assert sum(v["n_samples"] for v in pf.values()) == len(PF_SAMPLES)
    assert pf["list"]["n_unique"] == 2 and pf["person"]["n_unique"] == 1 and pf["ai_assistant"]["n_unique"] == 1
    assert pf["list"]["uniques_per_1k"] == pytest.approx(1000.0)
    assert pf["list"]["n_only_here"] == 1 and pf["person"]["n_only_here"] == 0


def test_per_family_yield_and_malformed_rate():
    """Roger, QUESTIONS 61: yield and malformed rate per family, so the lower-cased wiki_bio family is read
    against the clean-prompt ones in the same run."""
    counts = {"list": {"n_samples": 2, "n_raw_items": 10, "n_malformed": 1, "n_seed_echo": 2},
              "person": {"n_samples": 1, "n_raw_items": 8, "n_malformed": 4, "n_name_echo": 1,
                         "n_bio_span_echo": 2},
              "ai_assistant": {"n_samples": 1, "n_raw_items": 4, "n_malformed": 0}}
    pf = D.per_family(PF_ROWS, samples=PF_SAMPLES, counts=counts)
    assert pf["list"]["n_eligible"] == 1 and pf["list"]["ineligible_share"] == pytest.approx(0.5)
    assert pf["list"]["eligible_per_1k"] == pytest.approx(500.0)
    assert pf["person"]["malformed_rate"] == pytest.approx(0.5)      # 4 of 8: the family to watch
    assert pf["ai_assistant"]["malformed_rate"] == 0.0
    assert pf["person"]["items_per_sample"] == pytest.approx(8.0)
    assert pf["person"]["n_name_echo"] == 1 and pf["person"]["n_bio_span_echo"] == 2
    # the frozen harness stays usable without the extra block
    assert "malformed_rate" not in D.per_family(PF_ROWS, samples=PF_SAMPLES)["list"]


class TestBeforeTheFloor:
    """Gate audit 3, proposal 7: the readout's per-family and noun numbers over the eligible table before the count
    floor, read against every verdict the registry holds, so the family comparison is not an artefact of the
    floor (at 8 it kept 1 of the 462 rows only `ai_assistant` emitted, and 2 of 324 eligible nouns)."""

    TABLE = [
        {"stem": "kind", "count": 9, "families": {"list": 5, "ai_assistant": 4}, "eligible": True, "form": "adjective"},
        {"stem": "tireless", "count": 1, "families": {"ai_assistant": 1}, "eligible": True, "form": "adjective"},
        {"stem": "data", "count": 1, "families": {"ai_assistant": 1}, "eligible": True, "form": "noun"},
        {"stem": "introvert", "count": 3, "families": {"list": 2, "person": 1}, "eligible": True, "form": "noun"},
        {"stem": "zorbish", "count": 4, "families": {"list": 4}, "eligible": False, "form": "adjective"},
    ]
    REG = {"kind#1": {"filter": {"verdict": "trait"}, "novelty": {"decision": "covered"}},
           "tireless#1": {"filter": {"verdict": "trait"}, "novelty": {"decision": "new"}},
           "data#1": {"filter": {"verdict": "reject"}},
           "introvert#1": {"filter": {"verdict": "trait"}}}

    def test_per_family_and_only_here(self):
        from assistant_axis.gapgen.generators.base_model import evaluate as EV
        b = EV.before_floor(self.TABLE, self.REG, min_count=8)
        assert b["n_eligible"] == 4 and b["n_at_floor"] == 1 and b["min_count"] == 8
        ai = b["by_family"]["ai_assistant"]
        assert (ai["n_eligible"], ai["n_at_floor"], ai["n_nouns"], ai["n_m1"]) == (3, 1, 1, 3)
        assert ai["m1_pass_rate"] == pytest.approx(2 / 3, abs=1e-4) and ai["m3_new_rate"] == pytest.approx(0.5)
        # what only this family brought: two rows, neither at the floor of 8
        assert ai["only_here"]["n_eligible"] == 2 and ai["only_here"]["n_at_floor"] == 0
        assert ai["only_here"]["m1_pass_rate"] == pytest.approx(0.5) and ai["only_here"]["m3_new_rate"] == 1.0
        assert "zorbish" not in str(b) and set(b["by_family"]) == {"ai_assistant", "list", "person"}

    def test_the_noun_share_of_m1_survivors_before_the_floor(self):
        from assistant_axis.gapgen.generators.base_model import evaluate as EV
        b = EV.before_floor(self.TABLE, self.REG, min_count=8)
        # survivors: kind, tireless, introvert; one noun among them.  After the floor of 8 it would be 0 of 1.
        assert b["n_m1_survivors"] == 3 and b["noun_share_m1_survivors"] == pytest.approx(1 / 3, abs=1e-4)
        assert (b["n_nouns"], b["n_nouns_m1_judged"]) == (2, 2)
        # rows no run judged are counted, never guessed
        b2 = EV.before_floor(self.TABLE, {}, min_count=2)
        assert b2["n_m1_judged"] == 0 and b2["noun_share_m1_survivors"] is None
        assert b2["by_family"]["list"]["m1_pass_rate"] is None

    def test_the_floor_of_a_run(self):
        from assistant_axis.gapgen.generators.base_model import evaluate as EV
        from assistant_axis.gapgen.generators.base_model import report as RP
        rec = {"min_count": 2, "n_samples": 2000, "per_1k_samples": 1.0, "chosen_at_n_samples": 2000, "source": "x"}
        assert EV.floor_of_run({"floor": rec, "min_count": 2}, {"n_samples": 2000}) == rec
        # the pilot, before the record: its value with the table's sample size, the size it was chosen at unknown
        old = EV.floor_of_run({"min_count": 8}, {"n_samples": 2000})
        assert old["per_1k_samples"] == 4.0 and old["chosen_at_n_samples"] is None
        assert RP.floor_text(old).startswith("count >= 8 at 2,000 samples (4.0 per 1,000 samples); the sample size")
        assert "another size" in RP.floor_text(dict(rec, n_samples=20_000, per_1k_samples=0.1))
        assert EV.floor_of_run({}, None) is None and RP.floor_text(None) == "not recorded"
