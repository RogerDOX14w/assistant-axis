"""Masked-LM generator, task 7: the table, its eligibility and union rank, and Variant B's universe (plan
section 8, ``table``)."""
import json

import pytest

from assistant_axis.gapgen import freq
from assistant_axis.gapgen.generators.censuses.glosshint import Sense
from assistant_axis.gapgen.generators.masked_lm import table as T
from assistant_axis.gapgen.generators.masked_lm import wordlist as W
from assistant_axis.gapgen.generators.masked_lm.pll import Contrast
from assistant_axis.gapgen.generators.masked_lm.singlemask import PassResult, WordAgg
from assistant_axis.tests.mlm_fakes import fake_person_wordnet

SENSES = {
    "kind": [Sense("having or showing a tender and considerate nature", "a")],
    "cruel": [Sense("lacking or showing a lack of mercy", "a")],
    "beautiful": [Sense("delighting the senses", "a")],
    "zorbish": [Sense("inclined to zorb habitually", "a")],
    "catholic": [Sense("of or relating to the Catholic Church", "a")],
    "kantian": [Sense("of or relating to Kant or his philosophy", "a")],
    "american": [Sense("of or relating to the United States of America or its people or language", "a")],
    "risk-averse": [Sense("disinclined to take risks", "a")],
}
ZIPF = {"kind": 5.0, "cruel": 4.0, "beautiful": 5.2, "strong": 5.5, "zorbish": 0.5, "blargy": 0.5, "plain": 3.0,
        "catholic": 3.5, "kantian": 2.0, "american": 5.5, "risk": 4.5, "averse": 2.7, "tied": 3.0, "tide": 3.0}


def fake_lookups(**kw):
    kw.setdefault("senses", lambda s: SENSES.get(s.lower(), []))
    kw.setdefault("zipf_word", lambda w: ZIPF.get(w.lower(), 3.0))
    kw.setdefault("is_proper", lambda s: s.lower() in ("catholic", "kantian", "american"))
    return T.Lookups(**kw)


def agg(word, lp, *, n_top=1, frame="disp_nature", subject="she", surface=None, gender=None, form=None):
    return WordAgg(word=word, surface=surface or word, best_logprob=lp, best_frame=frame, best_subject=subject,
                   mean_rank=10.0, n_top=n_top, n_instances=4, gender_log_odds=gender, form=form)


def passes():
    single = {w: agg(w, lp, gender=g) for w, lp, g in (("kind", -1.0, 0.1), ("cruel", -2.0, -0.2),
                                                      ("beautiful", -1.5, 2.0), ("plain", -3.0, 0.0),
                                                      ("blargy", -4.0, 0.0), ("tide", -5.0, 0.0),
                                                      ("tied", -5.0, 0.0), ("catholic", -6.0, 0.0),
                                                      ("american", -6.5, 0.0))}
    vb = {w: agg(w, lp, n_top=n, surface=w, frame="noun_avowed") for w, lp, n in
          (("Kantian", -3.5, 1), ("zorbish", -4.5, 1), ("kind", -0.5, 2), ("unseen", -2.5, 0),
           ("risk-averse", -3.2, 1))}
    multi = {"risk-averse": agg("risk-averse", -3.8, form="hyphenated"), "!!!": agg("!!!", -0.1)}
    return {"single:roberta": PassResult("single", "roberta", single, {}),
            "variant_b:roberta": PassResult("variant_b", "roberta", vb, {}),
            "multiword:roberta": PassResult("multiword", "roberta", multi, {})}


def build(**kw):
    kw.setdefault("lookups", fake_lookups())
    return T.build_table(passes(), **kw)


def by_stem(rows):
    return {r["stem"]: r for r in rows if r["stem"]}


def test_the_probe_pass_is_not_in_the_union():
    ps = passes()
    ps["probe:roberta"] = type(ps["single:roberta"])("probe", "roberta", {"used": agg("used", -0.01)}, {})
    assert "used" not in by_stem(T.build_table(ps, lookups=fake_lookups()))


def test_rows_have_the_schema_fields():
    rows = build()
    for r in rows:
        assert list(json.loads(T.row_text(r))) == list(T.ROW_FIELDS)
        assert r["schema_version"] == 1


def test_surfaced_words_only_and_merge_by_stem():
    rows = build()
    s = by_stem(rows)
    assert "unseen" not in s                              # Variant B scored it, but in no instance's top 2,000
    assert s["kind"]["passes"] == ["single:roberta", "variant_b:roberta"]
    assert s["kind"]["best_logprob"] == -0.5 and s["kind"]["best_pass"] == "variant_b:roberta"
    assert s["kind"]["best_frame"] == "noun_avowed" and s["kind"]["models"] == ["roberta-large"]
    assert s["kind"]["gender_log_odds"] == 0.1            # from the single-mask pass, whatever pass is best
    assert s["kantian"]["surface"] == "Kantian"           # OEWN's spelling
    assert s["risk_averse"]["passes"] == ["multiword:roberta", "variant_b:roberta"]
    assert s["risk_averse"]["token_class"] is None        # no tokenizer in this build


def test_union_rank_order_and_ties():
    rows = build()
    assert [r["union_rank"] for r in rows] == list(range(1, len(rows) + 1))
    lps = [r["best_logprob"] for r in rows]
    assert lps == sorted(lps, reverse=True)
    s = by_stem(rows)
    assert s["tide"]["union_rank"] + 1 == s["tied"]["union_rank"]   # equal log-prob and Zipf: by surface
    assert by_stem(T.build_table(passes(), lookups=fake_lookups(zipf_word=lambda w: {"tied": 4.0}.get(w, 3.0))))[
        "tied"]["union_rank"] < s["tied"]["union_rank"] + 1          # higher Zipf first


def test_deterministic_and_byte_identical(tmp_path):
    a, b = T.table_text(build()), T.table_text(build())
    assert a == b
    p = tmp_path / "mlm_table.jsonl"
    assert T.write_table(build(), p) is None and T.write_table(build(), p) is None
    assert p.read_text() == a
    assert T.load_mlm_table(p)[0]["union_rank"] == 1


def test_eligibility_truth_table():
    s = by_stem(build())
    assert s["kind"]["eligible"] and s["plain"]["eligible"] and not s["plain"]["gloss_hint"]
    assert s["zorbish"]["freq_hard_reject"] and s["zorbish"]["gloss_hint"] and s["zorbish"]["eligible"]   # rescue 2
    assert s["blargy"]["freq_hard_reject"] and not s["blargy"]["eligible"]
    assert s["blargy"]["ineligible_reason"] == "below_hard_reject"
    assert s["kantian"]["freq_probe_band"] and s["kantian"]["eligible"]
    bad = [r for r in build() if r["stem"] is None]
    assert len(bad) == 1 and bad[0]["ineligible_reason"] == "malformed" and not bad[0]["eligible"]


def test_the_platform_floor_moves_the_outcome(monkeypatch):
    """No local 1.5: raise ``gapgen.freq``'s floor and a gloss-less word at Zipf 3 is hard-rejected."""
    assert by_stem(build())["plain"]["eligible"]
    monkeypatch.setattr(freq, "HARD_REJECT_BELOW", 3.5)
    s = by_stem(build())
    assert not s["plain"]["eligible"] and s["kind"]["eligible"] and s["zorbish"]["eligible"]


def test_corpus_match_never_reaches_eligibility_or_rank():
    rows = build()
    stems = [r["stem"] for r in rows if r["stem"]]
    flipped = build(corpus_stems=stems, queue_stems=stems)
    assert all(r["corpus_stem_match"] for r in flipped if r["stem"])
    key = lambda rs: [(r["stem"], r["eligible"], r["union_rank"]) for r in rs]  # noqa: E731
    assert key(rows) == key(flipped)


def test_stoplist_flags_never_drop_a_row():
    s = by_stem(build())
    assert s["catholic"]["stoplist_flags"] == ["religion"] and s["catholic"]["eligible"]
    assert s["american"]["stoplist_flags"] == ["nationality"] and s["american"]["eligible"]
    assert s["kantian"]["stoplist_flags"] == []


def test_contrast_rides_the_row():
    con = {"roberta": {"kind": Contrast(2.5, False, False, -1.0, -3.5, -4.0),
                       "beautiful": Contrast(-1.0, False, True, -2.0, -3.0, -1.0).as_dict()}}
    s = by_stem(build(contrasts=con))
    assert (s["kind"]["trait_contrast"], s["kind"]["state_flag"], s["kind"]["physical_flag"]) == (2.5, False, False)
    assert s["beautiful"]["physical_flag"] is True and s["cruel"]["trait_contrast"] is None
    assert T.table_counts(build(contrasts=con))["with_contrast"] == 2


def test_token_class_from_the_primary_tokenizer():
    s = by_stem(build(lookups=fake_lookups(token_class=lambda w: "multiword" if "-" in w else "single")))
    assert s["risk_averse"]["token_class"] == "multiword" and s["kind"]["token_class"] == "single"


# ---------------------------------------------------------------------------- Variant B's universe

def test_oewn_candidates_on_a_fake_wordnet():
    words = W.oewn_candidates(wordnet=fake_person_wordnet())
    assert "leader" in words and "optimist" in words           # person nouns under actor / doer
    assert "Henry IV" not in words                             # a proper name: left out
    assert "Kantian" in words and "risk-averse" in words and "absent-minded" in words
    assert "x2" not in words and "a b c d e" not in words      # digits; more than four words
    assert words.count("kind") == 1 and words == sorted(words, key=lambda x: (x.lower(), x))
    assert "person" not in words or "individual" in words
    assert "leader" not in W.oewn_candidates(wordnet=fake_person_wordnet(), include_person_nouns=False)


def test_stoplist_and_coverage():
    assert W.stoplist_flags("Buddhist") == ["religion"]
    assert W.stoplist_flags("German", "of or relating to or characteristic of Germany or its people") == ["nationality"]
    assert W.stoplist_flags("kind", "of or relating to people") == []      # not capitalised
    cov = W.universe_coverage(["kind", "risk-averse", "kind to animals", "zorbish"], ["kind", "risk-averse"])
    assert (cov["n_absent"], cov["n_single_absent"], cov["n_multiword_absent"]) == (2, 1, 1)
    assert cov["absent_single"] == ["zorbish"] and cov["absent_multiword"] == ["kind to animals"]
    assert cov["share_absent"] == 0.5
