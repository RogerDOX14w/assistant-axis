"""Plan 13 § 8, "Acceptance on recorded outputs": the tracked outputs under ``data/candidates/testing/`` and the
harness batches.  Each check skips while its output is absent (the paraphrase set's report and the decision-1
harness batches are written by the paid steps).  No API calls."""
import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TESTING = REPO / "data" / "candidates" / "testing"
RECOVERY = REPO / "data" / "candidates" / "recovery"


def result(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")).get("result")


@pytest.mark.skipif(not (TESTING / "dashboard.json").exists(), reason="no dashboard yet")
def test_the_dashboard_has_a_row_per_registry_generator():
    from assistant_axis.gapgen.registry import read_snapshot, snapshot_file
    from assistant_axis.gapgen.testing import dashboard as D
    dash = result(TESTING / "dashboard.json")
    assert dash["schema_version"] == 1
    rows = read_snapshot(snapshot_file(REPO / "data" / "candidates"))
    assert {r["generator"] for r in dash["rows"]} >= set(D.generator_names(rows))
    for r in dash["rows"]:
        if r["recall"]["headline"] is None:
            assert r["recall"]["harness_batch"] is None           # n/a, never a 0 standing for no data
    assert (TESTING / "dashboard.md").exists()


@pytest.mark.skipif(not (TESTING / "review_rates.json").exists(), reason="no review_rates.json yet")
def test_review_rates_reproduce_the_hard_figures():
    rr = result(TESTING / "review_rates.json")
    tda = next(b for b in rr["batches"] if b["batch_id"] == "review_tda_1")
    assert tda["events"] == 354 and tda["active_minutes"] == 84.1
    assert tda["terms"]["applied"] == 204 and tda["terms"]["promoted"] == 35
    assert tda["times"]["singleton_median_s"] == 12 and round(tda["times"]["per_member_s"]) == 25
    assert tda["rate"]["terms_per_active_minute"] == 2.43
    assert "review_tda_1" in rr["pooled"]["batches"] and "review_states_v4" in rr["pooled"]["left_out"]


@pytest.mark.skipif(not (TESTING / "concepts.json").exists(), reason="no concepts.json yet")
def test_concepts_hard_figures():
    c = result(TESTING / "concepts.json")
    s = c["units"]["components_4"]
    assert (s["n_concepts"], s["n_singletons"], s["largest"]) == (3065, 2691, 21)
    assert c["chain_diagnostic"]["largest"] == 1028
    assert 2200 <= c["units"]["grown_3"]["n_concepts"] <= 2300


@pytest.mark.skipif(not (TESTING / "paraphrase_set" / "report.md").exists(), reason="the paraphrase set is not run yet")
def test_the_paraphrase_report_records_recall_and_pair_recovery():
    md = (TESTING / "paraphrase_set" / "report.md").read_text(encoding="utf-8").lower()
    assert "concept recall" in md and "pair-recovery" in md.replace("pair recovery", "pair-recovery")
    assert (TESTING / "paraphrase_set" / "usage.json").exists()


def decision1_batches() -> list[Path]:
    out = []
    for d in sorted(RECOVERY.glob("*")):
        run = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
        if run.get("pooled"):
            out.append(d)
    return out


@pytest.mark.skipif(not decision1_batches(), reason="the decision-1 harness has not run yet")
def test_every_decision1_batch_has_usage_and_extras():
    for d in decision1_batches():
        assert (d / "usage.json").exists() and (d / "extras.json").exists(), d.name
        ex = result(d / "extras.json")
        # report-and-decide: a pair the record cannot decide at 4 is listed, not counted; the record must say how many
        assert isinstance(ex["n_needs_opus"], int) and ex["n_needs_opus"] == len(ex["needs_opus"])


def test_every_paid_directory_has_usage():
    for d in [TESTING / "paraphrase_set"] + [p for p in RECOVERY.glob("*") if p.is_dir()]:
        if (d / "run.json").exists() and (d / "responses.jsonl").exists():
            assert (d / "usage.json").exists(), d


def test_the_corpus_and_the_queue_are_untouched():
    try:
        out = subprocess.run(["git", "status", "--porcelain", "data/traits", "data/roles", "data/seed_queue.json"],
                             cwd=REPO, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        pytest.skip("git unavailable")
    if out.returncode != 0:
        pytest.skip("not a git checkout")
    assert out.stdout.strip() == ""
