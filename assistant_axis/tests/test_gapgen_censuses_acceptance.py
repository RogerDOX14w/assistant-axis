"""Census generator, acceptance on the recorded outputs (skips when they are absent).

Hard gates only (plan, review amendments of 2026-09-24): the table's shape, the run files and
their zero generator cost, the 95% keep-existing-labels policy.  First measurements (filter pass
rates, recovery) are report-and-decide, read by ``census_generator.py report``."""
import json
import math
from dataclasses import fields

import pytest

from assistant_axis.gapgen import Candidate
from assistant_axis.gapgen.generators.censuses import CENSUS_TABLE_PATH, INGEST_COUNTS_PATH, SOURCES_MANIFEST_PATH
from assistant_axis.gapgen.paths import runs_root

RUNS = runs_root() / "censuses"
RUN_DIRS = sorted(p for p in RUNS.glob("*") if (p / "candidates.jsonl").exists()) if RUNS.exists() else []
FIELDS = [f.name for f in fields(Candidate)]


def test_manifest_verified():
    if not SOURCES_MANIFEST_PATH.exists():
        pytest.skip("no sources manifest yet")
    entries = json.loads(SOURCES_MANIFEST_PATH.read_text())
    assert {e["key"] for e in entries} >= {"allport_I", "allport_II", "allport_III", "allport_IV", "tda_properties"}
    assert all(e["checksum_verified"] and e["licence"] and e["attribution"] for e in entries)


def test_table_shape_and_policy():
    if not CENSUS_TABLE_PATH.exists() or not INGEST_COUNTS_PATH.exists():
        pytest.skip("no census table yet")
    ranks, tda_ineligible = [], 0
    with open(CENSUS_TABLE_PATH, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            ranks.append(r["rank"])
            tda_ineligible += bool(r["tda"] and r["stem"] and not r["eligible"])
    assert ranks == list(range(1, len(ranks) + 1)) and tda_ineligible == 0
    counts = json.loads(INGEST_COUNTS_PATH.read_text())
    assert counts["n_tda"] == 2818
    assert counts["ceiling"]["submitted_of_matched"] >= 0.95


@pytest.mark.parametrize("rdir", RUN_DIRS, ids=[p.name for p in RUN_DIRS])
def test_run_files(rdir):
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines() if x.strip()]
    assert cands and all(list(c) == FIELDS for c in cands)
    assert {c["generator"] for c in cands} == {"censuses"} and {c["run_id"] for c in cands} == {rdir.name}
    assert all(c["sense_id"] == 1 and c["source_ref"] for c in cands)
    usage = json.loads((rdir / "usage.json").read_text())
    assert usage["total_cost_usd"] == 0 and usage["n_calls"] == 0          # the generator's own cost
    run = json.loads((rdir / "run.json").read_text())
    args = run["args"]
    assert args["sources"] and all(s["checksum_verified"] for s in args["sources"])
    keys = (rdir / "keys.txt").read_text().split()
    assert len(keys) == len({c["surface"] for c in cands})
    if args.get("every_nth"):
        assert len(cands) == math.ceil((args["n_stage"] - args["offset"]) / args["every_nth"])
