"""Alignment sweep (workstream 8): the source table and the two gold files (coding_plan_08_alignment_sweep.md § 8,
``sources``; task 1).  No network."""
from __future__ import annotations

import json

import pytest

from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.generators import alignment_sweep as AS
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


def test_gate_gold_items_ten_of_each_and_no_none_item_is_a_corpus_label():
    doc = json.loads(AS.GATE_GOLD_PATH.read_text(encoding="utf-8"))
    items = doc["items"]
    assert len(items) == 30
    by = {}
    for it in items:
        by.setdefault(it["expected"], []).append(it)
        assert it["label"] and it["gloss"].startswith("This means "), it
        assert it["key"] and it["source"] in ("corpus", "written"), it
    assert {k: len(v) for k, v in by.items()} == {"chat": 10, "agentic-only": 10, "none": 10}
    corpus = _corpus_stems()
    for it in by["chat"]:
        assert it["source"] == "corpus" and normalize_to_file_name(it["label"]) in corpus, it["label"]
    for it in by["none"] + by["agentic-only"]:
        assert it["source"] == "written"
    for it in by["none"]:
        assert normalize_to_file_name(it["label"]) not in corpus, it["label"]
    assert len({it["key"] for it in items}) == 30


def test_paths_are_inside_the_repository():
    for p in (AS.SWEEP_DIR, AS.EXTERNAL_DIR, AS.GOLD_PATH, AS.GATE_GOLD_PATH, AS.SOURCES_MANIFEST_PATH,
              AS.DEDUP_PAIRS_PATH):
        assert str(p).startswith(str(REPO)), p


@pytest.mark.parametrize("key", ["model_spec", "constitution"])
def test_chunk_prefix_is_the_key(key):
    assert SRC.SOURCES[key].key == key
