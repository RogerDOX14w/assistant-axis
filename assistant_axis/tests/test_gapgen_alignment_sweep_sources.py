"""Alignment sweep (workstream 8): the source table and the two gold files (coding_plan_08_alignment_sweep.md § 8,
``sources``; task 1).  No network."""
from __future__ import annotations

import json

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.generators import alignment_sweep as AS
from assistant_axis.gapgen.generators.alignment_sweep import gate as GATE
from assistant_axis.gapgen.generators.alignment_sweep import sources as SRC

REPO = AS.SWEEP_DIR.parents[2]


def test_every_source_has_url_kind_licence_or_read_only_and_a_check_date():
    assert SRC.SOURCES, "no sources"
    for key, s in SRC.SOURCES.items():
        assert s.key == key
        assert s.url.startswith("https://"), key
        assert s.kind in SRC.KINDS, (key, s.kind)
        assert s.license or s.read_only, key
        assert s.license_verified_at and len(s.license_verified_at) == 10, key   # YYYY-MM-DD
        assert s.weight in (0.5, 1, 2), (key, s.weight)
        assert s.variant in ("A", "B"), key
        assert s.fmt in SRC.FORMATS, (key, s.fmt)
        assert s.short and s.short.isalnum(), key


def test_krakovna_and_machiavelli_are_optional_and_krakovna_is_never_stored():
    k, m = SRC.SOURCES["krakovna"], SRC.SOURCES["machiavelli"]
    assert k.optional and m.optional
    assert k.read_only and not k.store and k.license is None
    assert m.license == "MIT" and "Alex Pan" in m.license_line


def test_licence_lines_of_the_plan_verbatim():
    ms, con = SRC.SOURCES["model_spec"], SRC.SOURCES["constitution"]
    assert ms.license == "CC0 1.0 Universal" and ms.license_verified_at == "2026-10-10"
    assert con.license == "CC0 1.0" and con.license_verified_at == "2026-10-10"
    # verbatim from the page (curly apostrophes); the plan quotes it with straight ones
    assert ("We're releasing Claude's constitution in full under a Creative Commons CC0 1.0 Deed"
            in con.license_line.replace("’", "'"))
    # the preface and the acknowledgements are not part of the constitution
    assert con.drop_before == "Overview" and "Acknowledgements" in con.drop_sections


def test_weights_follow_plan_step_7():
    assert SRC.SOURCES["model_spec"].weight == 2 and SRC.SOURCES["constitution"].weight == 2
    for s in SRC.SOURCES.values():
        if s.kind == "taxonomy":
            assert s.weight == 1, s.key
        if s.kind == "glossary":
            assert s.weight == 0.5, s.key


def test_version_pins_and_quote_policy():
    ms = SRC.SOURCES["model_spec"]
    assert ms.version_label == "2026-08-18" and ms.version_pin.startswith("7f1cf79")
    assert ms.commit in ms.url                                      # the fetch is pinned to the commit
    for s in SRC.SOURCES.values():
        assert SRC.quote_limit(s.key) == (25 if s.read_only else None), s.key


def test_default_fetch_is_the_approved_set():
    assert SRC.DEFAULT_FETCH == ("model_spec", "constitution")
    for k in SRC.DEFAULT_FETCH:
        assert SRC.SOURCES[k].variant == "A" and SRC.SOURCES[k].store


def test_shorts_are_unique():
    shorts = [s.short for s in SRC.SOURCES.values()]
    assert len(shorts) == len(set(shorts))


# --------------------------------------------------------------------------- the gold files


def _corpus_stems():
    return {p.stem for p in (REPO / "data" / "traits" / "instructions").glob("*.json")}


def test_gold_alignment_traits_are_the_ten_corpus_traits():
    doc = json.loads(AS.GOLD_PATH.read_text(encoding="utf-8"))
    stems = [g["stem"] for g in doc["traits"]]
    assert stems == ["sycophantic", "harmless", "honest", "obedient", "calibrated", "confabulatory", "transparent",
                     "motivated_reasoning_prone", "ruthless_while_playing", "ends_justify_means"]
    corpus = _corpus_stems()
    for g in doc["traits"]:
        assert g["stem"] in corpus, g["stem"]
        assert g["maps_from"] and g["note"], g["stem"]
    mrp = next(g for g in doc["traits"] if g["stem"] == "motivated_reasoning_prone")
    assert mrp["maps_from"] == "rationalizing"
    assert doc["frame_pair"] == ["honorable_while_playing", "ruthless_while_playing"]


def test_gate_gold_items_are_thirty_well_formed_items_over_the_four_answers():
    """The invariants that survive a relabelling.

    The predecessor of this test asserted the counts of the rubric's draft-1 three-way labels
    (``{"chat": 10, "agentic-only": 10, "none": 10}``) and that every ``chat`` item was a corpus trait while
    every other item was written for the file.  Draft 2 of the gate rubric adds a fourth answer ``both``, so
    any honest four-way relabelling breaks both halves of that assertion — and the second half was a flaw in
    its own right: it *required* the perfect confounding of ``expected`` with ``source``, under which the gate
    could score the ``chat`` row by reading prose style rather than content.  What is actually invariant is the
    shape of the file: thirty well-formed items, every answer one the gate can give, the corpus items real
    corpus traits, no ``none`` item a corpus label, and draft 1's label kept beside the new one so the
    relabelling stays auditable.  The distribution over the four answers is deliberately not asserted: the set's
    job is to span the space, not to be balanced.
    """
    doc = json.loads(AS.GATE_GOLD_PATH.read_text(encoding="utf-8"))
    items = doc["items"]
    assert len(items) == 30
    assert len({it["key"] for it in items}) == 30
    corpus = _corpus_stems()
    for it in items:
        assert it["label"] and it["gloss"].startswith("This means "), it
        assert it["key"] and it["source"] in ("corpus", "written"), it
        assert it["expected"] in GATE.VISIBILITY, it                     # an answer the gate can actually give
        assert it["expected_v1"] in ("chat", "agentic-only", "none"), it  # draft 1's label, kept for the audit
        assert it.get("reason"), it["key"]                                # why this item has this label
        in_corpus = normalize_to_file_name(it["label"]) in corpus
        if it["source"] == "corpus":
            assert in_corpus, it["label"]            # the corpus items are real corpus traits
        else:
            assert not in_corpus, it["label"]        # the written items are not corpus labels (the file says so)
        if it["expected"] == "none":
            assert not in_corpus, it["label"]        # nothing the corpus enacts can be unenactable
    assert sum(1 for it in items if it["source"] == "corpus") == 10
    # The relabelling is recorded: blind, by whom, when, and against which rubric pin.
    rel = doc["_relabelling"]
    assert rel["blind"] and rel["by"] and rel["relabelled_at"]
    assert "1fb03517a414" in rel["rubric"]
    # The criteria were stated before the labels; the one judgement the rubric leaves open is settled there.
    assert doc["_criteria"]["chat_vs_both"]["action_log_test"]


def test_paths_are_inside_the_repository():
    for p in (AS.SWEEP_DIR, AS.EXTERNAL_DIR, AS.GOLD_PATH, AS.GATE_GOLD_PATH, AS.SOURCES_MANIFEST_PATH,
              AS.DEDUP_PAIRS_PATH):
        assert str(p).startswith(str(REPO)), p


@pytest.mark.parametrize("key", ["model_spec", "constitution"])
def test_chunk_prefix_is_the_key(key):
    assert SRC.SOURCES[key].key == key
