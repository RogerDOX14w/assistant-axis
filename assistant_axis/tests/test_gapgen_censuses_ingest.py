"""Census generator, ingest: parsers, cleaning, OCR repair, the table, eligibility, ranks.

Fixtures in ``fixtures/censuses``; ``wordfreq`` and OEWN are faked (``censuses_fakes``)."""
import dataclasses
import json

import pytest

from assistant_axis.gapgen.freq import FreqInfo
from assistant_axis.gapgen.generators.censuses import ingest as I
from assistant_axis.tests.censuses_fakes import FIXTURES, fake_lookups, fixture_inputs, fixture_table


def by_surface(rows):
    return {r.surface: r for r in rows if r.surface}


class TestParsers:
    def test_allport_lines_blank_and_crlf_and_bom(self):
        e = I.parse_allport_txt(FIXTURES / "allport_I.txt", "I")
        assert [x.raw for x in e][:3] == ["ABANDONED", "Accomodating", "Afald"]
        assert [x.line for x in e][:3] == [1, 2, 4]  # line 3 is blank and skipped, numbering kept
        assert all(x.column == "I" for x in e)
        e2 = I.parse_allport_txt(FIXTURES / "allport_II.txt", "II")
        assert e2[0].raw == "flustered"  # BOM stripped

    def test_tda_two_rows_merge(self):
        t = {r.adjective: r for r in I.parse_tda_properties(FIXTURES / "tda_properties_small.csv")}
        assert len(t) == 5
        g = t["gloomy"]
        assert g.n_rows == 2 and g.prop == pytest.approx(0.75) and g.n == 100
        assert g.gbooks_freq == -0.2 and g.gn1710 is True and g.sg435 is True and g.bffm100 is False
        assert g.row == 3
        assert t["abandoned"].gbooks_freq is None and t["obscurish"].prop == 0.12
        assert t["kind"].row == 1 and t["kind"].n_rows == 1

    def test_tda_tab_separated(self, tmp_path):
        p = tmp_path / "t.tab"
        p.write_text("adjective\tN\tprop\tgbooks.freq\n\"kind\"\t80\t0.98\tNA\n")
        r = I.parse_tda_properties(p)[0]
        assert (r.adjective, r.n, r.prop, r.gbooks_freq, r.gn1710) == ("kind", 80, 0.98, None, None)

    def test_tda_header_required(self, tmp_path):
        p = tmp_path / "t.csv"
        p.write_text("word,N\nkind,1\n")
        with pytest.raises(ValueError, match="adjective"):
            I.parse_tda_properties(p)


class TestCleaning:
    @pytest.mark.parametrize("raw,clean", [
        ("Accomodating ", "accomodating"), ("ABANDONED", "abandoned"), ("à la mode", "a la mode"),
        ("well-bred", "well-bred"), ("Assistfu;", "assistfu"), ("ne’er-do-well", "ne'er-do-well"),
        ("Œdipus", "oedipus"), ("preëminent", "preeminent"), ("Tom o’Bedlam", "tom o'bedlam"),
        ("  Blasé  ", "blase"), ("F.F.V", None), ("abc1", None), ("Привет", None), ("", None), ("-", None),
    ])
    def test_clean_surface(self, raw, clean):
        assert I.clean_surface(raw) == clean

    def test_repair_unique_only(self):
        assert I.repair_ocr("accomodating", lexicon={"accommodating", "kind"}) == "accommodating"
        # two lemmas one edit away: no repair
        assert I.repair_ocr("accomodating", lexicon={"accommodating", "accomodatinf"}) is None
        assert I.repair_ocr("afald", lexicon={"accommodating"}) is None

    @pytest.mark.parametrize("a,b,kind", [
        ("accomodating", "accommodating", "doubling"), ("probbing", "probing", "doubling"),
        ("orented", "oriented", "vowel_insertion"), ("unorthadox", "unorthodox", "vowel_substitution"),
        ("cullying", "bullying", "early"), ("unlicked", "unlocked", "vowel_substitution"),
        ("tantling", "tattling", "other"), ("reslendent", "resplendent", "other"),
    ])
    def test_repair_kind(self, a, b, kind):
        assert I.repair_kind(a, b) == kind


class TestTable:
    def test_rows_and_merges(self, tmp_path):
        rows, extra, _ = fixture_table(tmp_path)
        s = by_surface(rows)
        assert len(rows) == 17
        assert s["agitated"].allport["columns"] == ["II", "III"]          # one row, both columns
        assert s["agitated"].allport["line"] == {"II": 2, "III": 1}
        assert s["kind"].tda["row"] == 1 and s["kind"].allport["columns"] == ["I"]   # TDA surface wins
        assert s["gloomy"].tda["n_rows"] == 2 and s["gloomy"].score == pytest.approx(0.75)
        assert s["a la mode"].stem == "a_la_mode" and s["a la mode"].label == "a la mode"
        assert s["well-bred"].stem == "well_bred"
        assert s["risk-averse"].stem == "risk_averse"
        assert all(r.in_merged for r in rows if r.allport and r.stem)
        assert extra["counters"]["allport_cross_column_merges"] == 1

    def test_unknown_and_repair(self, tmp_path):
        rows, extra, _ = fixture_table(tmp_path)
        s = by_surface(rows)
        assert s["afald"].unknown_word and not s["afald"].eligible
        assert s["afald"].ineligible_reason == "unknown_word"
        assert "accomodating" not in s
        acc = s["accommodating"]
        assert acc.repaired_from == "accomodating" and acc.eligible and not acc.unknown_word
        assert [r["repaired"] for r in extra["repaired"]] == ["accommodating"]
        assert s["assistfu"].ineligible_reason == "unknown_word"

    def test_repair_not_applied_for_unsafe_edit(self, tmp_path):
        rows, extra, _ = fixture_table(tmp_path, adjective_lemmas=frozenset({"assistful", "afield"}))
        s = by_surface(rows)
        assert "assistful" not in s and s["assistfu"].unknown_word          # no applied repair
        # assistfu -> assistful is an insertion of a consonant: a suggestion, not a repair
        assert {x["repaired"] for x in extra["repair_suggestions"]} >= {"assistful"}

    def test_malformed_kept(self, tmp_path):
        rows, extra, _ = fixture_table(tmp_path)
        bad = [r for r in rows if r.ineligible_reason == "malformed"]
        assert len(bad) == 1 and bad[0].label == "F.F.V" and bad[0].stem is None and bad[0].rank == len(rows)
        assert extra["malformed"] == [{"source": "allport:III", "raw": "F.F.V", "line": 2}]

    def test_eligibility_truth_table(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path)
        s = by_surface(rows)
        # TDA below the dictionary floor stays eligible (stage tda); the platform routes it to the probe
        ob = s["obscurish"]
        assert ob.tda and ob.freq_hard_reject and ob.eligible and ob.stage == "tda"
        assert ob.freq_platform == {"probe": True, "hard_reject": False, "rescue": "curated_source"}
        # Allport-only below the floor is cut
        assert not s["quaintish"].eligible and s["quaintish"].ineligible_reason == "below_hard_reject"
        # unknown, but the negating-prefix rescue holds: probe band, eligible
        u = s["unsprightly"]
        assert u.unknown_word and u.eligible and u.stage == "allport_probe" and u.freq_rescue == "negating_prefix"
        assert s["rarish"].stage == "allport_probe"
        assert s["flustered"].stage == "allport_hi" and s["agitated"].stage == "allport_hi"
        assert s["sunny"].stage == "tda"

    def test_stage_follows_zipf_info_flags(self, tmp_path):
        """No local literal: the stage reads ``hard_reject`` / ``probe_band`` from ``freq``."""
        def fake_freq(surface, **kw):
            if kw.get("curated"):
                return FreqInfo(zipf_min=9.0, probe_band=False, rescue=None)
            return FreqInfo(zipf_min=9.0, hard_reject=surface == "flustered", probe_band=surface == "agitated")
        rows, _, _ = fixture_table(tmp_path, freq=fake_freq, zipf_word=None)
        s = by_surface(rows)
        assert s["flustered"].ineligible_reason == "below_hard_reject"
        assert s["agitated"].stage == "allport_probe"
        assert s["quaintish"].stage == "allport_hi"
        assert s["kind"].stage == "tda"

    def test_global_rank_order(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path)
        order = [r.surface or r.label for r in rows]
        assert order[:5] == ["kind", "sunny", "abandoned", "gloomy", "obscurish"]   # TDA by prop
        assert order[5:13] == ["a la mode", "accommodating", "agitated", "risk-averse", "well-bred",
                               "flustered", "rarish", "quaintish"]                    # then Allport by Zipf
        assert order[13:16] == ["afald", "assistfu", "unsprightly"]
        assert [r.rank for r in rows] == list(range(1, 18))

    def test_corpus_and_queue_match(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path)
        s = by_surface(rows)
        assert s["risk-averse"].corpus_stem_match and s["kind"].corpus_stem_match
        assert not any(r.stem == "kind_to_animals" for r in rows)
        assert s["flustered"].queue_stem_match and not s["flustered"].corpus_stem_match

    def test_eligibility_independent_of_corpus(self, tmp_path):
        """Mutation test: other corpus and queue stems change no eligibility field."""
        rows, _, data = fixture_table(tmp_path)
        allport, merged, tda = fixture_inputs()
        rows2, _ = I.build_table(allport, tda, lookups=fake_lookups(), corpus_stems={r.stem for r in rows if r.stem},
                                 queue_stems=set(), merged=merged)
        key = lambda r: (r.stem, r.label, r.eligible, r.ineligible_reason, r.stage, r.rank, r.score)  # noqa: E731
        assert [key(r) for r in rows] == [key(r) for r in rows2]
        assert [r.corpus_stem_match for r in rows] != [r.corpus_stem_match for r in rows2]

    def test_gloss_hints_in_table(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path)
        s = by_surface(rows)
        assert s["flustered"].gloss_hint.startswith("disposition to be flustered (a general tendency")
        assert s["a la mode"].gloss_hint.endswith("(metaphorical or doubtful in Allport-Odbert)")
        assert "metaphorical" not in s["sunny"].gloss_hint            # TDA word, column IV: no note
        assert s["kind"].gloss_hint == "having or showing a tender and considerate and helpful nature"
        assert s["kind"].wordnet["person_sense_rank"] == 1 and s["kind"].wordnet["n_adj_senses"] == 1
        assert s["gloomy"].gloss_hint == "marked by melancholy and despondency"   # person cue outranks sense 1
        assert s["afald"].gloss_hint is None and s["afald"].wordnet["found"] is False

    def test_rerun_byte_identical_and_snapshot(self, tmp_path):
        rows, _, _ = fixture_table(tmp_path / "a")
        rows2, _, _ = fixture_table(tmp_path / "b")
        assert I.table_text(rows) == I.table_text(rows2)
        p = tmp_path / "census_table.jsonl"
        assert I.write_table(rows, p) is None
        before = p.read_bytes()
        assert I.write_table(rows2, p) is None and p.read_bytes() == before     # unchanged: no backup
        rows2[0].score = 0.5
        bak = I.write_table(rows2, p)
        assert bak is not None and bak.read_bytes() == before
        back = I.load_census_table(p)
        assert [dataclasses.asdict(r) for r in back] == [dataclasses.asdict(r) for r in rows2]

    def test_counts(self, tmp_path):
        rows, extra, _ = fixture_table(tmp_path)
        c = I.ingest_counts(rows, extra)
        assert c["n_rows"] == 17 and c["n_tda"] == 5 and c["n_both"] == 4
        assert c["per_stage"] == {"allport_hi": 6, "allport_probe": 2, "none": 4, "tda": 5}
        assert c["ineligible"] == {"below_hard_reject": 1, "malformed": 1, "unknown_word": 2}
        assert c["repaired"] == 1 and c["malformed"] == 1 and c["tda_below_dictionary_floor"] == 1
        json.dumps(c)


def test_frozen_interface_exports():
    from assistant_axis.gapgen.generators.censuses import CENSUS_TABLE_PATH, load_census_table
    assert CENSUS_TABLE_PATH.name == "census_table.jsonl" and callable(load_census_table)
