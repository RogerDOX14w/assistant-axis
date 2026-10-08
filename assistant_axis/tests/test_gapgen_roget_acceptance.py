"""Recorded-output acceptance for workstream 2 (plan § 8 "Acceptance", as revised 2026-10-08).

Reads the tracked outputs under ``data/candidates/roget/`` and the pilot run; each test skips when
its file is absent.  Hard gates: spend caps, ``usage.json`` presence, file shapes, the corpus left
untouched.  First measurements (the share of traits placed, the agreement rate) are recorded in the
readout for Roger, not asserted."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import Candidate

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "data" / "candidates" / "roget"
PILOT = REPO / "data" / "candidates" / "runs" / "roget" / "2026-10-08-pilot"
WN_PILOT = REPO / "data" / "candidates" / "runs" / "wn_clusters" / "2026-10-08-pilot"


def need(p: Path):
    if not p.exists():
        pytest.skip(f"{p} not present")
    return p


def result(p: Path) -> dict:
    d = json.loads(need(p).read_text(encoding="utf-8"))
    return d.get("result", d)


def test_every_dispositional_head_has_a_coverage_row():
    heads = result(OUT / "heads.json")
    cov = result(OUT / "roget_coverage.json")
    disp = {h["id"] for h in heads["heads"] if h["number"] >= 450}
    rows = {r["id"] for r in cov["rows"]}
    assert disp <= rows
    s = cov["summary"]
    assert s["n_heads"] == len(rows)
    cpu = s["covered_partly_uncovered"]
    assert cpu["covered"] + cpu["partly_covered"] + cpu["uncovered"] == s["n_heads"]


def test_every_corpus_trait_is_in_label_heads():
    lh = result(OUT / "label_heads.json")["labels"]
    stems = {p.stem for p in (REPO / "data" / "traits" / "instructions").glob("*.json")}
    assert stems <= set(lh)
    assert all(v["route"] in ("agree", "rule", "semantic", "lexical", "none") for v in lh.values())
    assert all((v["primary"] is None) == (v["route"] == "none") for v in lh.values())


def test_spotcheck_has_forty_rows():
    md = need(OUT / "map_spotcheck.md").read_text(encoding="utf-8")
    assert sum(1 for l in md.splitlines() if l.startswith("| [")) == 40


def test_mapping_spend_under_cap():
    u = json.loads(need(OUT / "mapping_usage.json").read_text())
    assert u["total_cost_usd"] < 0.25
    assert set(u["per_model"]) <= {"text-embedding-3-large"}


def test_head_pairs_are_reciprocal():
    pairs = result(OUT / "head_pairs.json")["pairs"]
    for h, p in pairs.items():
        if p["partner"]:
            assert pairs[p["partner"]]["partner"] == h


@pytest.mark.parametrize("run", [PILOT, WN_PILOT], ids=["roget", "wn_clusters"])
def test_pilot_run_files(run):
    rows = [json.loads(l) for l in need(run / "candidates.jsonl").read_text(encoding="utf-8").splitlines()]
    cands = [Candidate(**r) for r in rows]
    gen = run.parent.name
    assert all(c.generator == gen and c.run_id == "2026-10-08-pilot" for c in cands)
    assert len({(c.surface, c.sense_id, c.source_ref) for c in cands}) == len(cands)
    rj = json.loads(need(run / "run.json").read_text())
    assert rj["n_emitted"] == len(cands)
    u = json.loads(need(run / "usage.json").read_text())
    assert u["n_calls"] == 0 and u["total_cost_usd"] == 0
    if gen == "roget":
        assert all(c.source_ref.startswith("roget:") and c.gloss_hint for c in cands)
    else:
        assert all(c.source_ref.startswith("oewn:") for c in cands)
