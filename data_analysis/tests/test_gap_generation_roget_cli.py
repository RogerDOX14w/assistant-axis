"""CLI tests for data_analysis/gap_generation/roget_generate.py (workstream 2, plan § 8 "CLI and
cost guard").  A tmp tree: the 23-head fixture as the text, a small corpus and queue, the hash
embedder, no WordNet, a tmp registry.  No network, no model."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from data_analysis.gap_generation import roget_generate as R

FIXTURE = Path(__file__).resolve().parents[2] / "assistant_axis" / "tests" / "fixtures" / "roget_sample.txt"


@pytest.fixture()
def tree(tmp_path):
    text = tmp_path / "ext" / "pg.txt"
    text.parent.mkdir()
    shutil.copy(FIXTURE, text)
    inst = tmp_path / "data" / "traits" / "instructions"
    inst.mkdir(parents=True)
    for stem, neg, desc in [("cautious", "non-cautious", "This means looking before one leaps, wary and careful."),
                            ("determined", "non-determined", "This means holding to a decision once made."),
                            ("loving", "hateful", "This means feeling warm affection and showing it."),
                            ("hateful", "loving", "This means feeling hatred and showing it.")]:
        (inst / f"{stem}.json").write_text(json.dumps({"positive_label": stem, "negative_label": neg,
                                                       "description": desc}))
    q = tmp_path / "data" / "seed_queue.json"
    q.write_text(json.dumps({"entries": [{"stem": "willing", "label": "willing", "entity_type": "trait",
                                          "status": "candidate", "description": "This means agreeing readily."}]}))
    base = ["--data-dir", str(tmp_path / "data"), "--queue", str(q), "--out", str(tmp_path / "out"),
            "--text", str(text), "--candidates-dir", str(tmp_path / "cands"), "--no-wordnet"]
    return tmp_path, base


def run(base, *argv):
    return R.main([*base, *argv])


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in sorted(root.rglob("*")) if p.is_file()}


def build(tmp_path, base):
    assert run(base, "parse", "--allow-checksum-mismatch") == 0
    assert run(base, "pair") == 0
    assert run(base, "map", "--embedder", "hash", "--cache-dir", str(tmp_path / "cache")) == 0
    assert run(base, "coverage") == 0


def test_parse_refuses_a_mismatched_text(tree):
    tmp_path, base = tree
    with pytest.raises(SystemExit, match="differs from the pinned"):
        run(base, "parse")


def test_pipeline_end_to_end(tree):
    tmp_path, base = tree
    build(tmp_path, base)
    out = tmp_path / "out"
    for f in ("heads.json", "head_pairs.json", "label_heads.json", "map_spotcheck.md", "mapping_usage.json",
              "roget_coverage.json", "roget_coverage.md"):
        assert (out / f).exists(), f
    lh = json.loads((out / "label_heads.json").read_text())["result"]["labels"]
    assert lh["cautious"]["primary"] == "864" and lh["willing"]["source"] == "queued"
    assert json.loads((out / "mapping_usage.json").read_text())["n_calls"] >= 1
    assert run(base, "harvest", "--run-id", "t1") == 0
    rd = tmp_path / "cands" / "runs" / "roget" / "t1"
    cpath = rd / "candidates.jsonl"
    before = cpath.read_bytes()
    rows = [json.loads(l) for l in before.decode().splitlines()]
    assert rows and all(r["generator"] == "roget" and r["run_id"] == "t1" for r in rows)
    reg = tmp_path / "cands" / "registry.jsonl"
    assert run(base, "submit", "--run-id", "t1", "--registry", str(reg)) == 0
    assert cpath.read_bytes() == before                               # submit leaves the tracked file as written
    run_json = json.loads((rd / "run.json").read_text())
    assert run_json["n_emitted"] == len(rows)
    assert json.loads((rd / "usage.json").read_text())["n_calls"] == 0
    n_lines = len(reg.read_text().splitlines())
    assert run(base, "submit", "--run-id", "t1", "--registry", str(reg)) == 0
    assert len(reg.read_text().splitlines()) == n_lines              # idempotent: n_new = 0, nothing appended
    run_json = json.loads((rd / "run.json").read_text())
    assert run_json["n_emitted"] == len(rows) and len(run_json["sessions"]) == 2
    assert run_json["args"]["harvest_config"]["per_head_cap"] == 10
    assert not run_json["args"]["candidates"].startswith("/") or "cands" in run_json["args"]["candidates"]
    with pytest.raises(SystemExit, match="was submitted"):
        run(base, "harvest", "--run-id", "t1", "--force")


def test_submit_reports_zero_new_the_second_time(tree, capsys):
    tmp_path, base = tree
    build(tmp_path, base)
    run(base, "harvest", "--run-id", "t2")
    reg = tmp_path / "cands" / "registry.jsonl"
    run(base, "submit", "--run-id", "t2", "--registry", str(reg))
    capsys.readouterr()
    run(base, "submit", "--run-id", "t2", "--registry", str(reg))
    first = capsys.readouterr().out.splitlines()[0]
    rep = json.loads(first)
    assert rep["n_new"] == 0 and rep["n_merged"] == 0 and rep["n_unchanged"] == rep["n_submitted"] > 0


def test_dry_runs_write_nothing(tree):
    tmp_path, base = tree
    build(tmp_path, base)
    run(base, "harvest", "--run-id", "t3")
    snap = snapshot(tmp_path)
    for argv in (["parse", "--allow-checksum-mismatch"], ["pair"],
                 ["map", "--embedder", "hash", "--cache-dir", str(tmp_path / "cache")], ["coverage"],
                 ["harvest", "--run-id", "t4"], ["submit", "--run-id", "t3",
                                                  "--registry", str(tmp_path / "cands" / "registry.jsonl")],
                 ["fetch"]):
        assert R.main([*base, "--dry-run", *argv]) == 0, argv
    assert snapshot(tmp_path) == snap
    assert not (tmp_path / "cands" / "registry.jsonl").exists()


def test_dry_run_after_the_command(tree):
    tmp_path, base = tree
    snap = snapshot(tmp_path)
    assert run(base, "parse", "--allow-checksum-mismatch", "--dry-run") == 0
    assert snapshot(tmp_path) == snap
    args = R.build_parser().parse_args([*base, "coverage"])
    assert args.dry_run is False


def test_map_refuses_an_estimate_over_the_budget(tree):
    tmp_path, base = tree
    run(base, "parse", "--allow-checksum-mismatch")
    with pytest.raises(SystemExit, match="REFUSED"):
        run(base, "map", "--embedder", "openai", "--budget-usd", "0.0000001", "--cache-dir", str(tmp_path / "cache"))
    assert not (tmp_path / "out" / "label_heads.json").exists()


def test_harvest_refuses_to_overwrite_without_force(tree):
    tmp_path, base = tree
    build(tmp_path, base)
    run(base, "harvest", "--run-id", "t5")
    with pytest.raises(SystemExit, match="--force"):
        run(base, "harvest", "--run-id", "t5")
    assert run(base, "harvest", "--run-id", "t5", "--force") == 0


def test_submit_refuses_without_candidates(tree):
    tmp_path, base = tree
    with pytest.raises(SystemExit, match="harvest"):
        run(base, "submit", "--run-id", "nope")


def test_ids_spec():
    assert R._ids("1,2,600-602,604a") == ["1", "2", "600", "601", "602", "604a"]
