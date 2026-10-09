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
INST = REPO / "data" / "traits" / "instructions"
QUEUE = REPO / "data" / "seed_queue.json"
UPDATE_HINT = ("Run `uv run python data_analysis/gap_generation/roget_generate.py map --update` (re-places new and "
               "changed labels, drops stale ones, leaves the rest), then `roget_generate.py place-check "
               "--unchecked-only --resume --budget-usd <cap>`, `roget_generate.py head-scope --budget-usd 0.1` "
               "(no call unless a head entered the scope; drops a Class I-III head that left it with its last "
               "trait) and `roget_generate.py coverage`.  Never remap an old key onto a renamed stem: the old "
               "placement is for the old meaning.")
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
    # since the head-scope check (QUESTIONS 44, 2026-10-08) the heads rated 0 are counted apart
    nc = (s.get("not_character") or {}).get("n", 0)
    assert cpu["covered"] + cpu["partly_covered"] + cpu["uncovered"] + nc == s["n_heads"]


def _renamed_from(d: dict):
    rf = d.get("renamed_from")
    return rf.get("stem") if isinstance(rf, dict) else rf if isinstance(rf, str) else None


def missing_message(missing, inst_dir: Path) -> str:
    """For each corpus stem missing from label_heads.json: whether its file carries ``renamed_from``, and from
    what; then the command to run."""
    lines = []
    for s in sorted(missing):
        p = inst_dir / f"{s}.json"
        old = _renamed_from(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else None
        lines.append(f"  {s}: renamed_from {old!r} in its file" if old else f"  {s}: no renamed_from in its file (new)")
    return f"{len(missing)} corpus trait(s) missing from label_heads.json:\n" + "\n".join(lines) + "\n" + UPDATE_HINT


def stale_message(stale, inst_dir: Path, queue_entries) -> str:
    """For each label_heads.json key that is no corpus trait and no queue trait entry: the file or queue entry
    whose ``renamed_from`` names it, if any; then the command to run."""
    succ = {}
    for p in sorted(inst_dir.glob("*.json")):
        old = _renamed_from(json.loads(p.read_text(encoding="utf-8")))
        if old:
            succ.setdefault(old, f"{p.stem} (file)")
    for e in queue_entries:
        old = _renamed_from(e)
        if old and e.get("entity_type") == "trait":
            succ.setdefault(old, f"{e.get('stem')} (queue entry)")
    lines = [f"  {s}: renamed to {succ[s]}" if s in succ else f"  {s}: no file or queue entry names it in renamed_from"
             for s in sorted(stale)]
    return (f"{len(stale)} label_heads.json key(s) are no corpus trait and no queue trait entry:\n" + "\n".join(lines)
            + "\n" + UPDATE_HINT)


def test_failure_messages_name_the_rename(tmp_path):
    (tmp_path / "ocd.json").write_text(json.dumps({"renamed_from": {"stem": "compulsive", "date": "2026-10-08"}}))
    (tmp_path / "fresh.json").write_text(json.dumps({"description": "d"}))
    m = missing_message({"ocd", "fresh"}, tmp_path)
    assert "ocd: renamed_from 'compulsive' in its file" in m and "fresh: no renamed_from" in m and "map --update" in m
    s = stale_message({"compulsive", "in_pain", "gone"}, tmp_path,
                      [{"stem": "in_chronic_pain", "entity_type": "trait", "renamed_from": {"stem": "in_pain"}}])
    assert "compulsive: renamed to ocd (file)" in s and "in_pain: renamed to in_chronic_pain (queue entry)" in s
    assert "gone: no file or queue entry" in s and "map --update" in s


def test_every_corpus_trait_is_in_label_heads():
    lh = result(OUT / "label_heads.json")["labels"]
    stems = {p.stem for p in INST.glob("*.json")}
    missing = stems - set(lh)
    assert not missing, missing_message(missing, INST)
    # route llm: placed by the label placement check (QUESTIONS 39, 2026-10-08)
    assert all(v["route"] in ("agree", "rule", "semantic", "lexical", "none", "llm") for v in lh.values())
    assert all((v["primary"] is None) == (v["route"] == "none") for v in lh.values())


def test_label_heads_has_no_stale_stems():
    """Every key is a corpus trait or a queue trait entry (``mapping.load_labels``'s set): a rename leaves the
    old key behind, placed for the old meaning (2026-10-08, chunk 5)."""
    from assistant_axis.entity_id import normalize_to_file_name
    lh = result(OUT / "label_heads.json")["labels"]
    entries = json.loads(need(QUEUE).read_text(encoding="utf-8")).get("entries") or []
    known = {p.stem for p in INST.glob("*.json")} | {e.get("stem") or normalize_to_file_name(e.get("label") or "")
                                                     for e in entries if e.get("entity_type") == "trait"}
    stale = set(lh) - known
    assert not stale, stale_message(stale, INST, entries)


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


def test_head_scope_covers_the_scope_within_its_cap():
    from assistant_axis.gapgen import split_rubrics as sr
    hs = result(OUT / "head_scope.json")
    cov = result(OUT / "roget_coverage.json")
    assert [r["id"] for r in hs["heads"]] == [r["id"] for r in cov["rows"]], \
        "head_scope.json and the coverage map disagree on the heads in scope (a corpus drop or addition?).  " + UPDATE_HINT
    assert hs["summary"]["n_unrated"] == 0                      # every head with adjectives rated
    assert all((r["rating"] is None) == (r["skipped"] == "no_adjectives") for r in hs["heads"])
    assert (hs["rubric"]["version"], hs["rubric"]["sha256"]) == \
        sr.current_versions(names=("roget_head_scope",))["roget_head_scope"]
    u = json.loads(need(OUT / "head_scope_usage.json").read_text())
    assert u["total_cost_usd"] < 1.0 and set(u["per_model"]) == {"claude-haiku-5-5"}
    assert cov["summary"]["not_character"]["n"] == hs["summary"]["by_rating"]["0"]


def test_placement_check_recorded_within_its_cap():
    lh = result(OUT / "label_heads.json")
    meta = lh.get("placement_check")
    if meta is None:
        pytest.skip("placement check not run")
    labels = lh["labels"]
    checked = [v for v in labels.values() if v.get("llm")]
    assert len(checked) == meta["n_checked"] and sum(meta["outcomes"].values()) == len(checked)
    for v in checked:
        llm = v["llm"]
        assert llm["previous_route"] != "agree"
        assert llm["sonnet"]["head"] is None or llm["sonnet"]["head"] in llm["candidates"]
        assert v["primary"] == llm["final"]
        assert (llm["opus"] is not None) == (llm["sonnet"]["head"] != llm["previous_primary"])
    # cumulative: the first check's $5 cap (2026-10-08) plus the chunk-5 update's $3 cap (same day)
    u = json.loads(need(OUT / "placement_usage.json").read_text())
    assert u["total_cost_usd"] < 8.0 and set(u["per_model"]) <= {"claude-sonnet-5-5", "claude-opus-5-5"}
