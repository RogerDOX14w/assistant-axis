"""Base-model generator, acceptance on the recorded outputs (skips while they are absent; plan section 8).

Hard gates: the sources manifest (licences verified, the model's delete-when-done TODO), every stats record
carrying the section-6 fields, the generator's own usage at $0 with its tokens recorded, and a parse rate of at
least 0.99 in every M1 summary of this workstream's batches.  The collapse index is reported, never gated
(target under 15%: report-and-decide)."""
import json
import warnings

import pytest

from assistant_axis.gapgen.generators.base_model import BASE_DIR, GENERATOR, SOURCES_MANIFEST_PATH
from assistant_axis.gapgen.paths import DATA_CANDIDATES, runs_root

STATS = sorted(BASE_DIR.glob("stats_round*.json")) if BASE_DIR.exists() else []
RUNS = sorted(p for p in (runs_root() / GENERATOR).glob("*") if (p / "candidates.jsonl").exists()) \
    if (runs_root() / GENERATOR).exists() else []
M1_SUMMARIES = sorted((DATA_CANDIDATES / "filter").glob(f"*_{GENERATOR}/summary.json"))
SECTION6 = ("round", "prompts_version", "n_samples", "n_raw_items", "n_unique", "n_eligible", "uniques_per_1k_samples",
            "rarefaction", "chao1", "collapse_top50_share", "noun_share_unique", "noun_share_eligible",
            "normalized_mechanically", "per_family", "recovery_strings", "temperature", "model")


def test_sources_manifest():
    if not SOURCES_MANIFEST_PATH.exists():
        pytest.skip("no sources manifest yet")
    entries = {e["key"]: e for e in json.loads(SOURCES_MANIFEST_PATH.read_text())}
    assert {"wikibio", "onet"} <= set(entries)
    assert all(e["licence_verified"] and e["approved_by"] for e in entries.values())
    assert entries["wikibio"]["checksum_verified"]
    if "model" in entries:
        assert entries["model"]["checksum_verified"] and "delete" in entries["model"]["todo"]


@pytest.mark.parametrize("path", STATS, ids=[p.name for p in STATS])
def test_stats_fields(path):
    d = json.loads(path.read_text())
    st = d.get("result", d)
    missing = [k for k in SECTION6 if k not in st]
    assert not missing, missing
    if st["collapse_top50_share"] >= 0.15:
        warnings.warn(f"{path.name}: collapse index {st['collapse_top50_share']:.1%} >= 15% (report-and-decide)")


@pytest.mark.parametrize("run", RUNS, ids=[p.name for p in RUNS])
def test_generator_usage_is_free_but_recorded(run):
    u = json.loads((run / "usage.json").read_text())
    assert u["total_cost_usd"] == 0.0 and u["total_prompt_tokens"] > 0 and u["total_completion_tokens"] > 0


@pytest.mark.parametrize("summary", M1_SUMMARIES, ids=[p.parent.name for p in M1_SUMMARIES])
def test_m1_parse_rate(summary):
    s = json.loads(summary.read_text())
    s = s.get("result", s)
    assert s["parse_rate"] >= 0.99


def test_something_to_accept():
    if not (STATS or RUNS or M1_SUMMARIES):
        pytest.skip("no recorded outputs yet: the pilot has not run")
