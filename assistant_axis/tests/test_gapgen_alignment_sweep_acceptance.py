"""Alignment sweep: acceptance on the recorded outputs (coding_plan_08_alignment_sweep.md § 8, last item).

Skips when no run is recorded.  Per the platform's review amendment 2, first-measurement numbers are
**report-and-decide** (printed with their targets, never failed): raw items 150-350 and dedup to 50-110 for a full
variant-A run; the gate's gold agreement (at least 26/30) and flip rate (at most 10%); gold recovery (at least 7 of
10, and the frame pair).  The mechanical checks are hard: the parse rate of every extraction, rewrite and gate at
least 99%; a ``usage.json`` in every run directory and in the run's M1 and M3 batch directories when they exist; and
every kept pole with a polysemy flag carries a gloss (the disambiguation the plan asks for).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.alignment_sweep import GENERATOR
from assistant_axis.gapgen.paths import DATA_CANDIDATES

RUNS = DATA_CANDIDATES / "runs" / GENERATOR
RUN_DIRS = sorted(p for p in RUNS.iterdir() if p.is_dir()) if RUNS.exists() else []

pytestmark = pytest.mark.skipif(not RUN_DIRS, reason="no alignment-sweep run recorded")


def _json(p: Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) else d


@pytest.mark.parametrize("rdir", RUN_DIRS, ids=lambda p: p.name)
def test_usage_json_in_every_run_and_batch_dir(rdir):
    assert (rdir / "usage.json").exists(), rdir
    for kind in ("filter", "novelty"):
        b = DATA_CANDIDATES / kind / f"{rdir.name}_{GENERATOR}"
        if b.exists():
            assert (b / "usage.json").exists(), b


@pytest.mark.parametrize("rdir", RUN_DIRS, ids=lambda p: p.name)
def test_parse_rate_at_least_99_percent(rdir):
    s = rdir / "extract_summary.json"
    if s.exists():
        d = _json(s)
        assert d["n_chunks_answered"] / d["n_chunks"] >= 0.99, d["unparsed"]
    for name, key in (("extract_responses.jsonl", "items"), ("gate_responses.jsonl", "answer")):
        p = rdir / name
        if not p.exists():
            continue
        recs = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        units = {}
        for r in recs:
            u = (r.get("stage"), r.get("unit_id") or r.get("key"), r.get("reading"))
            units[u] = units.get(u) or (r.get(key) is not None)
        ok = sum(1 for v in units.values() if v)
        assert ok / len(units) >= 0.99, (name, len(units) - ok)


@pytest.mark.parametrize("rdir", RUN_DIRS, ids=lambda p: p.name)
def test_polysemy_flags_carry_a_gloss(rdir):
    p = rdir / "extraction.jsonl"
    if not p.exists():
        pytest.skip("no extraction")
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    for r in rows:
        if r["polysemy_flag"] and r["dropped_reason"] is None:
            assert r["gloss"].startswith("This means") and len(r["gloss"].split()) >= 8, r["item_id"]


@pytest.mark.parametrize("rdir", RUN_DIRS, ids=lambda p: p.name)
def test_report_and_decide_numbers(rdir, capsys):
    """Printed with their targets; never failed (first measurements)."""
    lines = [f"[{rdir.name}]"]
    s = rdir / "extract_summary.json"
    if s.exists():
        d = _json(s)
        lines.append(f"raw poles {d['n_poles']} ({d['n_pairs']} pairs from {d['n_chunks']} chunks; a full variant-A "
                     f"run targets 150-350 raw items)")
    g = rdir / "dedup_groups.json"
    if g.exists():
        d = _json(g)
        lines.append(f"dedup: {d['n_members']} kept poles -> {d['n_groups']} groups (full run target 50-110)")
    e = rdir / "gate_gold_eval.json"
    if e.exists():
        ev = _json(e)["eval"]
        lines.append(f"gate gold: agreement {ev['n_agree']}/{ev['n']} (target >= 26/30), flip rate "
                     f"{ev['flip_rate']:.1%} (target <= 10%); {'binding' if ev['meets_targets'] else 'advisory'}")
    gr = rdir / "gold_recovery.md"
    if gr.exists():
        head = gr.read_text(encoding="utf-8").split("Recovered ", 1)[1].split(".", 1)[0]
        lines.append(f"gold recovery: {head} (target >= 7 of 10 and the frame pair)")
    with capsys.disabled():
        print("\n  ".join(lines))
    assert lines
