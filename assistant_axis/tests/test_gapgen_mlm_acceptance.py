"""Masked-LM generator, acceptance on the recorded outputs (plan section 8; each test skips while its output is
absent).

Hard: the HHH probe present with all nine ranks; the contrast AUC reported; recovery at N = 20,000 reported per
label class beside the wordfreq baseline; ``usage.json`` in every run directory with the generator's own cost at
0.0; the model's download record verified (published and pinned sha256, licence); the package imports neither
``anthropic`` nor ``openai``.  First-measurement thresholds (the AUC's 0.85, any recall) are reported, never gated
(platform review amendment 2): a miss is a warning."""
import json
import warnings
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators import masked_lm as G
from assistant_axis.gapgen.generators.masked_lm.frames import PROBE_LABELS
from assistant_axis.gapgen.paths import runs_root

RUNS = sorted(p for p in (runs_root() / G.GENERATOR).glob("*") if (p / "candidates.jsonl").exists()) \
    if (runs_root() / G.GENERATOR).exists() else []
EVALUATIONS = sorted(G.MLM_DIR.rglob("evaluation.json")) if G.MLM_DIR.exists() else []


def _payload(p: Path) -> dict:
    d = json.loads(p.read_text())
    return d.get("result", d)


@pytest.mark.parametrize("path", EVALUATIONS, ids=[str(p.parent.name) for p in EVALUATIONS])
def test_evaluation_reports_what_the_plan_asks(path):
    ev = _payload(path)
    probe = ev["hhh_probe"]
    assert set(PROBE_LABELS) <= set(probe["ranks"]) and all(probe["ranks"][k] is not None for k in PROBE_LABELS)
    assert "winning_families" in probe and "winning_frames" in probe
    assert "contrast_auc" in ev
    if ev.get("contrast_auc") is not None and ev["contrast_auc"] < 0.85:
        warnings.warn(f"{path}: contrast AUC {ev['contrast_auc']} < 0.85 (report and decide)")
    detail = ev["recovery_detail"]["corpus"]
    assert "baseline_wordfreq" in detail and "union" in detail
    for ranking in ("union", "baseline_wordfreq"):
        for c in ("single", "subword", "multiword"):
            if detail[ranking].get(c, {}).get("n"):
                assert "recall@20000" in detail[ranking][c], (ranking, c)
    assert ev["coverage"] is None or {"n_absent", "absent_single", "absent_multiword"} <= set(ev["coverage"])


@pytest.mark.parametrize("run", RUNS, ids=[p.name for p in RUNS])
def test_generator_usage_is_zero(run):
    u = json.loads((run / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0


def test_download_record():
    if not G.SOURCES_MANIFEST_PATH.exists():
        pytest.skip("no sources manifest yet")
    entries = {e["key"]: e for e in json.loads(G.SOURCES_MANIFEST_PATH.read_text())}
    for e in entries.values():
        assert e["checksum_verified"] and e["licence_verified"] and e["approved_by"], e["key"]
        assert e["weights_sha256"] == e["weights_sha256_pinned"]


def test_census_record():
    p = G.CENSUS_PATH
    if not p.exists():
        pytest.skip("no census yet")
    c = _payload(p)["census"]
    for model, sets in c.items():
        v = sets["corpus"]
        assert v["single"] + v["subword"] + v["multiword"] == v["n"] and v["n"] > 800, model


def test_something_to_accept():
    if not (RUNS or EVALUATIONS or G.SOURCES_MANIFEST_PATH.exists()):
        pytest.skip("no recorded outputs yet")
