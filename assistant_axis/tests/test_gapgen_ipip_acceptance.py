"""IPIP generator, acceptance on the recorded outputs (plan § 8, last item).  Each check skips while its output is
not on disk (the item-to-scale workbook waits for Roger's go, QUESTIONS 52, and the runs come after it)."""
import json

import pytest

from assistant_axis.gapgen.generators import ipip as P
from assistant_axis.gapgen.generators.ipip import ingest as I
from assistant_axis.gapgen.generators.ipip.report import naming_parse_stats
from assistant_axis.gapgen.paths import runs_root


def _skip_unless(path):
    if not path.exists():
        pytest.skip(f"{path} not recorded yet")


def test_ingest_counts():
    _skip_unless(P.ITEMS_PATH)
    items = I.load_items(P.ITEMS_PATH)
    assert len(items) >= 3000
    counts = json.loads(P.INGEST_COUNTS_PATH.read_text())
    assert counts["hex"]["constructs"] >= 20 and counts["hex_assertion"] == "passed"
    assert [r.ipip_id for r in items] == sorted((r.ipip_id for r in items), key=I.code_order)


def test_naming_parse_rate():
    _skip_unless(P.NAMING_RESPONSES_PATH)
    recs = [json.loads(x) for x in P.NAMING_RESPONSES_PATH.read_text().splitlines() if x.strip()]
    stats = naming_parse_stats(recs)
    assert stats["parse_rate"] >= 0.99, stats
    assert P.NAMING_USAGE_PATH.exists()


def test_usage_json_in_every_run_and_granularity_dir():
    dirs = [d for d in (runs_root() / P.GENERATOR).glob("*") if d.is_dir()] if (runs_root() / P.GENERATOR).exists() else []
    dirs += [d for d in P.GRANULARITY_DIR.glob("g*") if d.is_dir()] if P.GRANULARITY_DIR.exists() else []
    if not dirs:
        pytest.skip("no IPIP run or granularity directory recorded yet")
    for d in dirs:
        assert (d / "usage.json").exists(), d


def test_evaluations_report_agreement_and_recovery():
    root = runs_root() / P.GENERATOR
    evs = sorted(root.glob("*/evaluation.json")) if root.exists() else []
    if not evs:
        pytest.skip("no IPIP evaluation recorded yet")
    for p in evs:
        ev = json.loads(p.read_text())["result"]
        for g, a in ev["naming"]["agreement"].items():
            assert "antonym_agreement" in a and a["antonym_target"] == 0.8
        assert "share" in ev["recovery"]["exact"] and ev["recovery"]["exact"]["target"] == 0.9
