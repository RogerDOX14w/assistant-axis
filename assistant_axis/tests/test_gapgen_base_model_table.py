"""Base-model generator, task 5: the candidate table (one row per stem; eligibility from the platform's floor;
rank by count; evaluation-only corpus flags)."""
import json

import pytest

from assistant_axis.gapgen.freq import FreqInfo, zipf_info
from assistant_axis.gapgen.generators.base_model import parse as PA
from assistant_axis.gapgen.generators.base_model import table as T
from assistant_axis.tests.base_model_fakes import ADJECTIVES, NOUNS, SENSES, fake_zipf


def S(i, family, text, **kw):
    d = {"sample_id": f"R1-{i:06d}", "index": i, "family": family, "text": text, "seed_words": [],
         "seed_refs": [], "partner_seed": None, "temperature": 1.0}
    d.update(kw)
    return d


SAMPLES = [
    S(0, "list", " stubborn, generous, kindness.", seed_words=["brave", "blunt"]),
    S(1, "person", " Generous, warm, Walter, founder of extra flugzeugbau.", seed_refs=["wikibio:train:0"],
      seed_words=["calm", "loyal"]),
    S(2, "contrast", " unflappable and warm.", partner_seed="cold", seed_words=["cold", "peel", "yogurt"]),
    S(3, "list_gloss", "unflappable: staying calm when everything goes wrong\nzorbish: odd\n"),
    S(4, "list", " brave, generous, generous, hidebound, quick-tempered.", seed_words=["brave", "kind"]),
    S(5, "ai_assistant", " tireless\n2. humility: it never boasts\n"),
]
BIOS = {"wikibio:train:0": ("Walter Extra", "Walter Extra is a german pilot and founder of extra flugzeugbau.")}


def lookups(**over):
    kw = dict(zipf_word=fake_zipf, in_wordnet=lambda s: s in ADJECTIVES or s in NOUNS or s in SENSES,
              senses=lambda s: list(SENSES.get(s, [])), lexicon=PA.Lexicon(adjectives=ADJECTIVES, nouns=NOUNS),
              freq=lambda s: zipf_info(s, zipf_fn=fake_zipf))
    kw.update(over)
    return T.Lookups(**kw)


def build(samples=SAMPLES, **kw):
    kw.setdefault("lookups", lookups())
    kw.setdefault("bio_lookup", BIOS.get)
    return T.build_table(samples, corpus_stems=kw.pop("corpus", {"generous", "warm"}),
                         queue_stems=kw.pop("queue", {"unflappable"}), **kw)


def by_stem(rows):
    return {r["stem"]: r for r in rows}


def test_rows_counts_families_rank():
    rows, counts = build()
    r = by_stem(rows)
    # generous: samples 0, 1, 4 (the repeat inside sample 4 counts once)
    assert r["generous"]["count"] == 3 and r["generous"]["families"] == {"list": 2, "person": 1}
    assert r["warm"]["count"] == 2 and r["unflappable"]["count"] == 2
    assert [x["stem"] for x in rows][:3] == ["generous", "warm", "unflappable"]   # count, then first appearance
    assert [x["rank"] for x in rows] == list(range(1, len(rows) + 1))
    assert r["generous"]["first_sample_id"] == "R1-000000"
    # seed echoes are not candidates (brave was a seed of samples 0 and 4)
    assert "brave" not in r and counts["n_seed_echo"] >= 1


def test_mechanical_normalization_in_the_table():
    r = by_stem(build()[0])
    assert r["kind"]["form"] == "adjective" and r["kind"]["normalized_from"] == "kindness"
    assert r["humility"]["form"] == "noun" and r["humility"]["normalized_from"] is None


def test_biography_text_never_enters_the_table():
    rows, counts = build()
    r = by_stem(rows)
    assert "walter" not in r                            # the person's name
    assert "founder of extra flugzeugbau" not in r      # a span copied from the biography
    assert counts["n_bio_echo"] == 2
    assert "Walter" not in json.dumps(rows)


class TestNameEcho:
    """Roger, QUESTIONS 54: the two bio rules counted apart, the dropped word logged, and the run reporting
    any word that the name rule cost it."""

    def test_the_two_rules_are_counted_apart(self):
        _, c = build()
        assert c["n_name_echo"] == 1 and c["n_bio_span_echo"] == 1
        assert c["n_bio_echo"] == c["n_name_echo"] + c["n_bio_span_echo"]

    def test_the_dropped_word_is_logged_but_never_the_span(self):
        _, c = build()
        # our own one-word candidate label, so nothing changes legally
        assert c["name_echo_words"] == {"walter": 1}
        # the span is verbatim CC BY-SA biography prose: counted, never logged
        assert "flugzeugbau" not in json.dumps(c)

    def test_a_word_that_arrived_from_another_seed_is_not_reported_as_lost(self):
        # "generous" is dropped from the person sample as a name echo but also arrives from the list family
        samples = [S(0, "list", " generous, kind."),
                   S(1, "person", " generous, warm.", seed_refs=["wikibio:train:1"])]
        bios = {"wikibio:train:1": ("Generous Smith", "Generous Smith was a pilot.")}
        rows, c = T.build_table(samples, lookups=lookups(), bio_lookup=bios.get)
        assert c["n_name_echo"] == 1 and c["name_echo_words"] == {"generous": 1}
        assert c["name_echo_not_elsewhere"] == []            # nothing was lost: it came from another seed
        assert "generous" in by_stem(rows)

    def test_a_word_no_other_seed_brought_in_is_the_whitelist(self):
        samples = [S(0, "person", " frank, warm.", seed_refs=["wikibio:train:2"])]
        bios = {"wikibio:train:2": ("Frank Jones", "Frank Jones was a pilot.")}
        rows, c = T.build_table(samples, lookups=lookups(), bio_lookup=bios.get)
        assert c["name_echo_not_elsewhere"] == ["frank"] and "frank" not in by_stem(rows)

    def test_a_multiword_label_is_never_a_name_echo(self):
        # the name rule is single words only; a span is dropped only when it is in the biography verbatim
        samples = [S(0, "person", " walter white, quietly stubborn.", seed_refs=["wikibio:train:3"])]
        bios = {"wikibio:train:3": ("Walter Extra", "Walter Extra was a pilot.")}
        rows, c = T.build_table(samples, lookups=lookups(), bio_lookup=bios.get)
        assert c["n_name_echo"] == 0 and c["n_bio_span_echo"] == 0
        assert "walter_white" in by_stem(rows)


def test_per_family_counts_for_the_readout():
    """Roger, QUESTIONS 61: the per-family numbers the readout compares the wiki_bio family on."""
    _, c = build()
    fam = c["by_family"]
    assert set(fam) == {"list", "person", "contrast", "list_gloss", "ai_assistant"}
    assert sum(v["n_samples"] for v in fam.values()) == c["n_samples"]
    assert sum(v.get("n_raw_items", 0) for v in fam.values()) == c["n_raw_items"]
    assert fam["person"]["n_name_echo"] == 1 and fam["person"]["n_bio_span_echo"] == 1
    assert "n_name_echo" not in fam["list"]              # no echo of a kind the family cannot have


def test_contrast_partner_and_sample_gloss():
    r = by_stem(build()[0])
    assert r["warm"]["partner_seed"] == "cold" and r["unflappable"]["partner_seed"] == "cold"
    assert r["generous"]["partner_seed"] is None
    assert r["unflappable"]["sample_gloss"] == "staying calm when everything goes wrong"
    assert r["humility"]["sample_gloss"] == "it never boasts"
    # gloss_hint only from (fake) OEWN, never the sampled gloss
    assert r["unflappable"]["gloss_hint"].startswith("not easily perturbed")
    assert r["zorbish"]["gloss_hint"] is None and r["zorbish"]["sample_gloss"] == "odd"


def fixed_freq(flags):
    def f(surface):
        hard, probe = flags.get(surface, (False, False))
        return FreqInfo(zipf_min=1.0 if hard else (2.0 if probe else 4.0), hard_reject=hard, probe_band=probe)
    return f


def test_eligibility_truth_table():
    lk = lookups(freq=fixed_freq({"warm": (True, False), "generous": (False, True)}))
    r = by_stem(build(lookups=lk)[0])
    assert r["warm"]["eligible"] is False and r["warm"]["ineligible_reason"] == "below_hard_reject"
    assert r["generous"]["eligible"] is True and r["generous"]["freq_probe_band"] is True
    assert r["stubborn"]["eligible"] is True and r["stubborn"]["ineligible_reason"] is None
    # zorbish: neither wordfreq nor OEWN knows it -> unknown_word (which wins over the floor)
    assert r["zorbish"]["eligible"] is False and r["zorbish"]["ineligible_reason"] == "unknown_word"
    # a real floor: hidebound has Zipf 1.4 < 1.5 and no rescue
    r2 = by_stem(build()[0])
    assert r2["hidebound"]["freq_hard_reject"] is True and r2["hidebound"]["ineligible_reason"] == "below_hard_reject"


def test_corpus_flags_never_change_eligibility():
    rows, _ = build()
    flipped, _ = build(corpus={r["stem"] for r in rows} - {"generous", "warm"}, queue={r["stem"] for r in rows})
    a, b = by_stem(rows), by_stem(flipped)
    assert {k: v["corpus_stem_match"] for k, v in a.items()} != {k: v["corpus_stem_match"] for k, v in b.items()}
    assert {k: v["eligible"] for k, v in a.items()} == {k: v["eligible"] for k, v in b.items()}
    assert [x["stem"] for x in rows] == [x["stem"] for x in flipped]


def test_rerun_is_byte_identical(tmp_path):
    p = tmp_path / "t.jsonl"
    rows, _ = build()
    assert T.write_table(rows, p) is None
    first = p.read_bytes()
    assert T.write_table(build()[0], p) is None and p.read_bytes() == first
    assert T.load_table(p) == rows
    # a changed table keeps the old one as a snapshot
    changed = [dict(rows[0], count=99)] + rows[1:]
    bak = T.write_table(changed, p)
    assert bak is not None and bak.read_bytes() == first


def test_counts():
    _, c = build()
    assert c["n_samples"] == 6 and c["n_raw_items"] >= c["n_unique"] and c["n_unique"] == len(build()[0])
    assert c["by_form"]["adjective"] >= 1 and "noun" in c["by_form"] and "phrase" in c["by_form"]
    assert c["normalized_mechanically"] == 1


def test_row_schema():
    row = build()[0][0]
    want = {"schema_version", "surface", "stem", "form", "normalized_from", "count", "families", "first_sample_id",
            "first_family", "sample_gloss", "zipf", "freq_hard_reject", "freq_probe_band", "in_oewn", "in_tda", "wordnet",
            "gloss_hint", "partner_seed", "eligible", "ineligible_reason", "rank", "corpus_stem_match",
            "queue_stem_match", "unknown_word"}
    assert set(row) == want


@pytest.mark.parametrize("text,expected", [(" kind, kind, kind.", 1)])
def test_within_sample_repeats_count_once(text, expected):
    rows, _ = build([S(0, "list", text)])
    assert by_stem(rows)["kind"]["count"] == expected
