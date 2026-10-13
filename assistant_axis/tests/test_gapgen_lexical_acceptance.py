"""Acceptance on the recorded outputs of workstream 11 (coding_plan_11_novelty_ensemble.md § 8, "Acceptance on recorded
outputs"); each test skips while its output is absent.

* hard: the lookup table covers every corpus trait and live seed-queue label; the dry readout reaches the two known
  cases (``pleasant#1`` -> agreeable, ``annoying#1`` -> disagreeable); every sweep's parse rate is at least 0.99 per
  step and model, its ``usage.json`` shows a nonzero cost, and no swept row's ``novelty`` block was changed by it
  (against its ``plan.json`` snapshot, where the registry is present: a row an M3 run decided again after the sweep
  is left out); the rubric pins are unmoved;
* reported: the stop-rule figure and the by-link counts are in ``sweep_report.json``.

Roger's blind marks are a manual check recorded in the acceptance report, never asserted here."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import lexical as LX
from assistant_axis.gapgen import lexical_sweep as LS
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import paths

LEX = paths.DATA_CANDIDATES / "lexical"
SWEEPS = sorted(p for p in (LEX / "sweep").glob("*") if (p / "sweep_report.json").exists()) \
    if (LEX / "sweep").exists() else []


def _result(path: Path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc["result"] if isinstance(doc, dict) and isinstance(doc.get("result"), dict) else doc


@pytest.mark.skipif(not LX.LOOKUP_PATH.exists(), reason="lookup.json not built yet")
def test_the_lookup_covers_every_corpus_trait_and_live_queue_label():
    doc = LX.read_lookup_doc(LX.LOOKUP_PATH)
    stems = {r["stem"] for r in doc["rows"]}
    corpus = NV.load_trait_corpus(paths.DATA_DIR)
    want = {s for s, t in corpus.items() if not LX.is_placeholder(t.label)}
    assert want - stems == set(), "corpus traits missing from the lookup table (rebuild: lexical_recall.py build)"
    queue = json.loads(paths.SEED_QUEUE_PATH.read_text(encoding="utf-8"))
    entries, _ = LX.live_queue_entries(queue, corpus)
    live = {e["stem"] for e in entries if not LX.is_placeholder(e["label"])}
    assert live - stems == set(), "live seed-queue labels missing from the lookup table"
    assert doc["header"]["lexicons"]["oewn"]["id"] == "oewn:2024"
    for r in doc["rows"]:
        if r["kind"] == "queue":
            assert r["has_text"] == any(e["stem"] == r["stem"] and e["has_text"] for e in entries)


@pytest.mark.skipif(not (LEX / "dry_readout.json").exists(), reason="dry_readout.json not written yet")
def test_the_dry_readout_reaches_the_two_known_cases():
    r = _result(LEX / "dry_readout.json")
    audit = r["audit_retrieval_misses"]
    assert audit["pleasant#1"]["reached"] and audit["pleasant#1"]["trait"] == "agreeable"
    assert audit["annoying#1"]["reached"] and audit["annoying#1"]["trait"] == "disagreeable"
    assert r["free_labels"]["lexical_target_merges"].get("pleasant#1") == "agreeable"
    assert r["free_labels"]["lexical_target_merges"].get("annoying#1") == "disagreeable"


@pytest.mark.skipif(not (LEX / "labelled_readout.json").exists(), reason="labelled_readout.json not written yet")
def test_the_labelled_readout_reports_recall_and_false_flags():
    m = _result(LEX / "labelled_readout.json")
    d = m["by_lexicon"]["oewn"]
    assert d["duplicate"]["recall"] is not None and d["antonym"]["recall"] is not None
    assert d["unrelated"]["false_flag"] is not None and d["unrelated"]["false_flag"] < 0.05


@pytest.mark.parametrize("sweep", SWEEPS, ids=[p.name for p in SWEEPS])
def test_a_recorded_sweep(sweep):
    run = json.loads((sweep / "run.json").read_text(encoding="utf-8"))
    for name, d in (run.get("parse_rates") or {}).items():
        assert d["n"] == 0 or d["ok"] / d["n"] >= 0.99, f"{sweep.name} {name}: parse rate {d['ok']}/{d['n']}"
    usage = json.loads((sweep / "usage.json").read_text(encoding="utf-8"))
    assert usage["total_cost_usd"] > 0 and usage["n_calls"] > 0
    rep = _result(sweep / "sweep_report.json")
    assert "covers_at_cut_off" in rep["stop_rule"] and "line" in rep["stop_rule"]          # reported
    assert isinstance(rep["by_link"], dict) and isinstance(rep["by_lexicon"], dict)
    if not paths.REGISTRY_PATH.exists():
        pytest.skip("no registry log in this checkout: the novelty-block check runs where the sweep wrote")
    from assistant_axis.gapgen.registry import Registry
    rows = Registry(paths.REGISTRY_PATH).fold()
    plan = _result(sweep / "plan.json")
    started = run.get("started_at") or ""
    checked = 0
    for key, snap in plan["rows"].items():
        nv = (rows.get(key) or {}).get("novelty")
        if nv is None or (nv.get("at") or "") > started:
            continue                       # decided again by a later M3 run: not the sweep's doing
        assert nv.get("at") == snap["novelty_at"] and nv.get("decision") == snap["novelty_decision"], key
        assert LS.block_sha256(nv) == snap["novelty_sha256"], key
        checked += 1
    assert checked > 0


def test_the_rubric_pins_are_unmoved():
    from data_analysis.gap_generation import rubric_pins
    assert rubric_pins.main(["check"]) == 0
