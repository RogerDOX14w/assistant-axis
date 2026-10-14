"""Plan 12 § 8, acceptance on the recorded outputs under ``data/candidates/persona/`` (each check skips while its
output is absent): ``cv.json`` reproduces the hard figures; ``calibration.json`` records both thresholds and who set
them; every score batch has ``usage.json`` and ``summary.json``; the first full batch has a ``persona`` block on every
scored key of the tracked snapshot and an ``agreement.json``; the prospective ``predicted.jsonl`` has a row for every
pending entity; the corpus and the queue are untouched."""
import json
import os
import subprocess

import pytest

from assistant_axis.gapgen.paths import DATA_CANDIDATES, REPO_ROOT
from assistant_axis.gapgen.persona_space import PERSONA_DIR

FIT_DIRS = sorted(p.parent for p in (PERSONA_DIR / "fit").glob("*/cv.json")) if (PERSONA_DIR / "fit").exists() else []
SCORE_DIRS = sorted(p for p in (PERSONA_DIR / "score").glob("*") if p.is_dir() and ".bak." not in p.name) \
    if (PERSONA_DIR / "score").exists() else []
#: The pending entities of 2026-10-13: 637 traits with no vector, the two sense-changed renames' current files
#: (violent, metaphysical_libertarian), and 60 roles (QUESTIONS 147).
N_PENDING = 699


def env(p):
    d = json.loads(p.read_text(encoding="utf-8"))
    assert set(d) == {"result", "_provenance"}, f"{p} has no provenance envelope"
    return d["result"]


@pytest.mark.skipif(not FIT_DIRS, reason="no recorded fit yet")
@pytest.mark.parametrize("d", FIT_DIRS, ids=[d.name for d in FIT_DIRS])
def test_cv_reproduces_the_hard_figures(d):
    cv = env(d / "cv.json")
    s = cv["by_alpha"]["0.3"]
    assert s["median_cos"] >= 0.70 and s["top1"] >= 0.70 and s["top5"] >= 0.95
    assert s["per_pc_r2"][0] >= 0.75
    assert all(v >= 0.55 for v in s["rho_by_N"].values())
    assert cv["knn_cos_by_k"]["5"] <= 0.70
    assert cv["n_rows"] == 572 and cv["spectrum"]["k95"] == 170
    assert len(cv["orphans"]) == 8


@pytest.mark.skipif(not FIT_DIRS, reason="no recorded fit yet")
@pytest.mark.parametrize("d", FIT_DIRS, ids=[d.name for d in FIT_DIRS])
def test_calibration_records_the_thresholds(d):
    cal = env(d / "calibration.json")
    assert 0.0 < cal["dup_threshold"] < 1.0 and 0.0 < cal["novel_pct"] < 1.0
    assert cal["thresholds_set_by"]
    for f in ("fit_report.md", "fit_report.png", "run.json", "usage.json"):
        assert (d / f).exists(), f


@pytest.mark.skipif(not SCORE_DIRS, reason="no recorded score batch yet")
@pytest.mark.parametrize("d", SCORE_DIRS, ids=[d.name for d in SCORE_DIRS])
def test_every_batch_has_usage_and_summary(d):
    assert (d / "usage.json").exists() and (d / "run.json").exists()
    env(d / "summary.json")
    env(d / "agreement.json")


FULL = [d for d in SCORE_DIRS if d.name.endswith("_all")]


@pytest.mark.skipif(not FULL, reason="no full batch yet")
def test_the_first_full_batch_is_on_the_snapshot():
    from assistant_axis.gapgen.registry import read_snapshot, snapshot_file
    d = FULL[0]
    keys = [json.loads(x)["key"] for x in (d / "scores.jsonl").read_text().splitlines() if x.strip()]
    snap = read_snapshot(snapshot_file(DATA_CANDIDATES))
    missing = [k for k in keys if (snap.get(k) or {}).get("persona", {}).get("batch_id") != d.name]
    assert not missing, f"{len(missing)} scored keys without the batch's persona block in the snapshot " \
                        f"(run `gap_registry.py compact` after `score --write-registry` or `apply`): {missing[:5]}"
    assert len(keys) >= 6500


PRO_DIRS = sorted(p.parent for p in (PERSONA_DIR / "prospective").glob("*/predicted.jsonl")) \
    if (PERSONA_DIR / "prospective").exists() else []


@pytest.mark.skipif(not PRO_DIRS, reason="no prospective predictions yet")
def test_prospective_rows():
    rows = (PRO_DIRS[0] / "predicted.jsonl").read_text().splitlines()
    assert len(rows) == N_PENDING
    assert (PRO_DIRS[0] / "run.json").exists()


@pytest.mark.skipif(not os.environ.get("GAPGEN_ACCEPTANCE_WORKTREE"),
                    reason="an acceptance step, not a standing test: Roger's tree has uncommitted trait edits mid-chunk "
                           "(plan 12 review, should-fix 4); set GAPGEN_ACCEPTANCE_WORKTREE=1 to run it")
def test_the_corpus_and_the_queue_are_untouched():
    out = subprocess.run(["git", "status", "--porcelain", "data/traits", "data/roles", "data/seed_queue.json"],
                         cwd=REPO_ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("git unavailable")
    assert out.stdout.strip() == ""
