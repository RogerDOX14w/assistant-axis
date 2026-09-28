"""Recorded-output acceptance tests for the trait-gap platform.

They read saved outputs under ``data/candidates/`` and **skip** when a file
is absent, so they pass before the paid runs and bite after them.

M1: the pilot (``filter/m1_pilot``) must meet the mechanical gates (parse
rate >= 99%, usage.json present, cost recorded).  The full validation run
(``filter/m1_validation``, plan §9 task 10, not run yet) must also meet the
quality thresholds of plan §8 and produce ``corpus_regions.json`` covering
every trait file.
"""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.paths import CORPUS_REGIONS_PATH, DATA_DIR, filter_dir

PILOT = filter_dir("m1_pilot")
FULL = filter_dir("m1_validation")


def _summary(d: Path) -> dict:
    p = d / "summary.json"
    if not p.exists():
        pytest.skip(f"{p} not recorded yet")
    obj = json.loads(p.read_text())
    return obj.get("result", obj)


def _results(d: Path) -> list[dict]:
    p = d / "results.jsonl"
    if not p.exists():
        pytest.skip(f"{p} not recorded yet")
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


@pytest.mark.parametrize("d", [PILOT, FULL], ids=["pilot", "full"])
def test_mechanical_gates(d):
    s = _summary(d)
    assert s["parse_rate"] >= 0.99
    assert not s.get("stopped_by_budget")
    usage = json.loads((d / "usage.json").read_text())
    assert usage["n_calls"] > 0 and usage["total_cost_usd"] == pytest.approx(s["cost_usd"], abs=1e-3)
    assert (d / "responses.jsonl").exists() and (d / "run.json").exists()


def test_full_existing_labels_mostly_trait():
    s = _summary(FULL)
    rs = [r for r in _results(FULL) if r["meta"]["stratum"] == "existing"]
    ok = sum(1 for r in rs if r["filter"]["verdict"] == "trait"
             or (r["filter"]["verdict"] == "tagged" and "physical" in r["filter"]["tags"]))
    assert ok / len(rs) >= 0.95, f"{ok}/{len(rs)} existing labels trait"
    assert s["by_stratum"]["existing"]["n"] == len(rs)


def test_full_six_rejects():
    rs = {r["label"]: r["filter"] for r in _results(FULL) if r["meta"]["stratum"] == "rejects"}
    flagged = [w for w, f in rs.items() if f.get("polysemy") or (f.get("trait_sense_rank") or 0) >= 2]
    assert len(flagged) >= 4, flagged
    if "empowered" in rs:
        assert {"state", "transient_only"} & set(rs["empowered"]["tags"])
    if "economic" in rs:
        assert "relational_only" in rs["economic"]["tags"]


def test_full_random_adjectives_rarely_trait():
    rs = [r for r in _results(FULL) if r["meta"]["stratum"] == "oewn_random"]
    assert sum(r["filter"]["verdict"] == "trait" for r in rs) / len(rs) <= 0.15


def test_full_stability_rerun():
    p = filter_dir("m1_stability") / "summary.json"
    if not p.exists():
        pytest.skip("stability rerun not recorded yet")
    a = {r["key"]: r["filter"]["verdict"] for r in _results(FULL) if r["filter"]}
    b = {r["key"]: r["filter"]["verdict"] for r in _results(filter_dir("m1_stability")) if r["filter"]}
    common = set(a) & set(b)
    assert len(common) >= 200
    assert sum(a[k] == b[k] for k in common) / len(common) >= 0.90


def test_corpus_regions_cover_every_trait_file():
    if not CORPUS_REGIONS_PATH.exists():
        pytest.skip("corpus_regions.json not written yet (task 10)")
    obj = json.loads(CORPUS_REGIONS_PATH.read_text())
    regions = obj.get("result", obj)
    stems = {p.stem for p in (DATA_DIR / "traits" / "instructions").glob("*.json")}
    assert stems <= set(regions)
