"""``axis_cosine_seriation.ontology_for_cohort``: a ``_v1`` record list
shares its cohort's ontology (review of 2026-10-12).

AGENT_NOTES says to pass ``pair_list_clean_v1.json`` with the 8slot data;
its cohort token is ``clean_v1``, which the old ``cohort in
COHORT_ONTOLOGIES`` test did not find, so the ontology overlay vanished
without a word.
"""
from __future__ import annotations

from assistant_axis.pair_list_cohort import cohort_from_pairs
from results_analysis.axis_cosine_seriation import (
    CLEAN_COHORT_ONTOLOGY,
    ontology_for_cohort,
)


def test_current_and_record_lists_share_the_ontology():
    for fname in ("pair_list_clean.json", "pair_list_clean_v1.json",
                  "pair_list_goalnongoal_v1.json"):
        registered = ontology_for_cohort(cohort_from_pairs(fname))
        assert registered is not None, fname
        assert registered[1] is CLEAN_COHORT_ONTOLOGY


def test_unregistered_cohort_has_none():
    assert ontology_for_cohort(cohort_from_pairs("pair_list_di_v1.json")) is None
    assert ontology_for_cohort("responses") is None
