"""Plan 13 task 1: each generator's stream, class and mechanism, the states pass's attribution, and the provenance
exclusion (``assistant_axis/gapgen/testing/independence.py``).  No API calls; the recorded registry snapshot is
read for the "every generator has a rule" check."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.testing import independence as IND

REPO = Path(__file__).resolve().parents[2]


def src(g, run="r1", ref=None, partner=None):
    return {"generator": g, "run_id": run, "source_ref": ref, "partner_hint": partner}


class TestStreams:
    def test_the_vocabularies_are_closed(self):
        assert IND.CLASSES == ("independent", "seeded", "separate_population", "not_a_generator")
        for s in IND.STREAMS.values():
            assert s.cls in IND.CLASSES and (s.mechanism is None or s.mechanism in IND.MECHANISMS)
        with pytest.raises(ValueError):
            IND.Stream("x", "x", "nearly_independent", "lexicon", "", "")
        with pytest.raises(ValueError):
            IND.Stream("x", "x", "seeded", "telepathy", "", "")

    def test_stream_of(self):
        assert IND.stream_of(src("censuses", ref="tda:5")) == "tda"
        assert IND.stream_of(src("censuses", ref="allport:12034")) == "allport"
        assert IND.stream_of(src("wn_clusters", ref="oewn:x", partner="kind")) == "antonym"
        assert IND.stream_of(src("wn_clusters", ref="oewn:x")) == "closure"
        assert IND.stream_of(src("roget", ref="roget:1")) == "heads"
        assert IND.stream_of(src("ipip", ref="ipip:g600:3")) == "ipip"
        assert IND.stream_of(src("states_pass", ref="preoccupied#1")) == "states_pass"

    def test_classes_as_verified(self):
        get = lambda g, s: IND.STREAMS[(g, s)]                          # noqa: E731
        assert get("censuses", "tda").cls == get("censuses", "allport").cls == "independent"
        assert get("roget", "heads").cls == "seeded" and get("roget", "heads").harness_side_only
        assert get("wn_clusters", "closure").cls == "independent" and get("wn_clusters", "antonym").cls == "seeded"
        assert get("ipip", "ipip").mechanism == "ipip" and get("base_model", "base_model").cls == "independent"
        assert get("alignment_sweep", "alignment_sweep").cls == "separate_population"
        assert get("states_pass", "states_pass").cls == "not_a_generator"
        assert not any(s.generator_side_hiding for s in IND.STREAMS.values())       # plan 13 § 1


class TestAttribution:
    def test_a_states_pass_row_counts_for_its_source_rows_generator(self):
        rows = {"preoccupied#1": {"key": "preoccupied#1", "sources": [src("censuses", "tda_run", "tda:9")]},
                "absent_minded#1": {"key": "absent_minded#1",
                                    "sources": [src("states_pass", "st1", "preoccupied#1"), src("base_model", "b1")]},
                "lonely_one#1": {"key": "lonely_one#1", "sources": [src("states_pass", "st1", "absent_minded#1")]},
                "loop#1": {"key": "loop#1", "sources": [src("states_pass", "st1", "loop#1")]}}
        a = IND.attributed_sources(rows["absent_minded#1"], rows)
        assert [(x["generator"], x["run_id"], x["stream"], x["via"]) for x in a] == \
            [("base_model", "b1", "base_model", None), ("censuses", "tda_run", "tda", "preoccupied#1")]
        chain = IND.attributed_sources(rows["lonely_one#1"], rows)            # followed through two pass rows
        assert {x["generator"] for x in chain} == {"base_model", "censuses"}
        assert IND.attributed_sources(rows["loop#1"], rows) == []             # a cycle ends the walk
        assert IND.generators_of(rows["absent_minded#1"], rows) == ["base_model", "censuses"]
        assert [c.mechanism for c in IND.classify(rows["absent_minded#1"], rows)] == ["base_model", "lexicon"]

    def test_pools_are_left_out_unless_asked(self):
        row = {"key": "x#1", "sources": [src("m1_validation", "pilot_1"), src("ipip", "g")]}
        assert IND.generators_of(row, {}) == ["ipip"]
        assert IND.generators_of(row, {}, pools=True) == ["ipip", "m1_validation"]


class TestProvenance:
    TRAITS = {"stubborn": {"source": None, "renamed_from": ["mulish"]},
              "conscientious_ipip": {"source": "IPIP-NEO, Goldberg 1999", "renamed_from": []},
              "intrinsic_allport": {"source": "Allport & Ross 1967, JPSP", "renamed_from": []},
              "obedient": {"source": None, "renamed_from": []},
              "curious": {"source": None, "renamed_from": []}}
    QUEUE = {"entries": [{"stem": "mulish", "tags": ["gap_gen", "source:censuses"], "status": "seeded"},
                         {"stem": "obedient", "gap_registry_key": "obedient#1", "status": "superseded"},
                         {"stem": "curious", "tags": ["plain"], "status": "seeded"}]}

    def test_a_planted_tag_file_source_and_renamed_from(self):
        why = IND.provenance_excluded("stubborn", traits=self.TRAITS, queue=self.QUEUE)
        assert why == "queue entry mulish tagged source:censuses (renamed to stubborn)"       # through renamed_from
        assert IND.provenance_excluded("stubborn", traits=self.TRAITS, queue=self.QUEUE, generator="ipip") is None
        assert "names 'ipip'" in IND.provenance_excluded("conscientious_ipip", traits=self.TRAITS, queue=self.QUEUE)
        assert "gap_registry_key" not in (IND.provenance_excluded("obedient", traits=self.TRAITS, queue=self.QUEUE)
                                          or "") and "handed to the registry" in \
            IND.provenance_excluded("obedient", traits=self.TRAITS, queue=self.QUEUE)
        assert IND.provenance_excluded("intrinsic_allport", traits=self.TRAITS, queue=self.QUEUE) is None  # Ross
        assert IND.provenance_excluded("curious", traits=self.TRAITS, queue=self.QUEUE) is None
        assert IND.excluded_stems("censuses", traits=self.TRAITS, queue=self.QUEUE) == \
            {"stubborn": "queue entry mulish tagged source:censuses (renamed to stubborn)"}

    def test_the_real_corpus_excludes_nothing_today(self):
        """2026-10-13: no trait file came from gap generation, and the two files naming Allport name Allport and
        Ross's religious orientation scale, not the census list."""
        traits = IND.trait_sources(REPO / "data")
        queue = json.loads((REPO / "data" / "seed_queue.json").read_text())
        assert len(traits) >= 932
        assert "Allport" in traits["intrinsic_allport"]["source"]
        for g in ("censuses", "roget", "wn_clusters", "ipip", "base_model", "alignment_sweep", "antonym_check"):
            assert IND.excluded_stems(g, traits=traits, queue=queue) == {}, g


class TestRecorded:
    @pytest.fixture(scope="class")
    def rows(self):
        from assistant_axis.gapgen.registry import read_snapshot, snapshot_file
        p = snapshot_file(REPO / "data" / "candidates")
        if not p.exists():
            pytest.skip("no registry snapshot")
        return read_snapshot(p)

    def test_every_registry_generator_has_a_rule(self, rows):
        assert IND.missing_rules(rows) == []
        table = IND.independence_table(rows, {}, {"entries": []})
        by = {(r["generator"], r["stream"]): r for r in table}
        assert by[("censuses", "tda")]["n_rows"] > 0 and by[("censuses", "allport")]["n_rows"] > 0
        assert by[("wn_clusters", "antonym")]["n_rows"] > 0 and by[("wn_clusters", "closure")]["n_rows"] > 0
        assert by[("states_pass", "states_pass")]["n_rows"] > 0
        assert all(not r.get("no_rule") for r in table)
        md = IND.table_markdown(table)
        assert "| censuses | tda | independent | lexicon |" in md
