"""The base-model generator's CLI (``base_model_generator.py``): every subcommand's dry run writes nothing; fetch
needs Roger's recorded approval; bench and sample refuse without the model and never download; the pipeline
parse -> stats -> submit -> report runs end to end on fixtures (fake lookups, tmp registry)."""
import hashlib
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.base_model import table as TB
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.base_model_fakes import (
    CENSUS_TABLE_SMALL, ONET_SMALL, SAMPLES_SMALL, make_wikibio_zip, samples_small_text,
)
from assistant_axis.tests.censuses_fakes import make_corpus
from assistant_axis.tests.test_gapgen_base_model_table import lookups
from data_analysis.gap_generation import base_model_generator as CLI


@pytest.fixture
def env(tmp_path, monkeypatch):
    ext = tmp_path / "ext"
    make_wikibio_zip(ext / "wikibio" / "data" / "wikipedia-biography-dataset.zip")
    (ext / "onet").mkdir(parents=True)
    (ext / "onet" / "occupation_data.csv").write_bytes(ONET_SMALL.read_bytes())
    nouns = tmp_path / "nouns.txt"
    nouns.write_text("lighthouse\nspreadsheet\nharvest\nviolin\n")
    rdir = tmp_path / "samples" / "round1"
    rdir.mkdir(parents=True)
    (rdir / "samples.jsonl").write_bytes(SAMPLES_SMALL.read_bytes())
    (rdir / "sampling.json").write_text(json.dumps({
        "round": 1, "model": "Qwen/Qwen3-8B-Base",
        "key": {"seed": 0, "prompts_version": 1, "temperatures": [1.0]},
        "bundle": {"bio_split": "train", "bio_pool_size": 50, "pool_seed": 0, "min_bio_words": 15,
                   "max_bio_words": 200}}))
    data = make_corpus(tmp_path, traits=("generous", "warm", "patient"), queue=("unflappable",))
    monkeypatch.setattr(TB, "default_lookups", lambda: lookups())
    common = ["--data-dir", str(data), "--registry", str(tmp_path / "cand" / "registry.jsonl"),
              "--candidates-dir", str(tmp_path / "cand"), "--external-dir", str(ext),
              "--sources-manifest", str(tmp_path / "sources_manifest.json"), "--hf-dir", str(tmp_path / "hf"),
              "--samples-dir", str(tmp_path / "samples"), "--base-dir", str(tmp_path / "base"),
              "--census-table", str(CENSUS_TABLE_SMALL), "--nouns-file", str(nouns)]
    return tmp_path, common


def snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def run(common, *argv):
    return CLI.main(common + list(argv))


def test_fixture_is_current():
    assert SAMPLES_SMALL.read_text(encoding="utf-8") == samples_small_text()


def test_every_dry_run_writes_nothing(env, capsys):
    tmp, common = env
    before = snapshot(tmp)
    for argv in (["fetch", "--dry-run"], ["bench", "--dry-run"], ["sample", "--round", "3", "--n", "12", "--dry-run"],
                 ["parse", "--round", "1", "--dry-run"]):
        assert run(common, *argv) == 0, argv
    assert snapshot(tmp) == before
    # the later commands need the earlier ones' outputs: make them, then dry-run again
    assert run(common, "parse", "--round", "1") == 0
    assert run(common, "stats", "--round", "1", "--step", "2") == 0
    assert run(common, "submit", "--round", "1", "--run-id", "r1") == 0
    mid = snapshot(tmp)
    for argv in (["stats", "--round", "1", "--dry-run"], ["submit", "--round", "1", "--run-id", "r2", "--dry-run"],
                 ["report", "--run-id", "r1", "--dry-run"]):
        assert run(common, *argv) == 0, argv
    assert snapshot(tmp) == mid
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "setup_external.py" in out


def test_fetch_without_approval_refuses(env, capsys):
    _, common = env
    assert run(common, "fetch") == 2
    assert "5a" in capsys.readouterr().err


def test_bench_and_sample_refuse_without_the_model(env, capsys):
    tmp, common = env
    assert run(common, "bench") == 2
    assert "setup_external.py --hf-model Qwen/Qwen3-8B-Base" in capsys.readouterr().err
    assert run(common, "sample", "--round", "2", "--n", "4") == 2
    assert "setup_external.py" in capsys.readouterr().err
    assert not (tmp / "hf").exists() and not (tmp / "samples" / "round2").exists()


def test_sample_refuses_a_round_sampled_with_other_settings(env, capsys, monkeypatch):
    tmp, common = env
    monkeypatch.setattr(CLI, "_model_present", lambda args: True)
    rec = tmp / "samples" / "round1" / "sampling.json"
    d = json.loads(rec.read_text())
    d["key"].update({"wording_sha256": "old", "families": [], "familiarity_floor": 0.5, "bio_pool_size": 20000})
    rec.write_text(json.dumps(d))
    assert run(common, "sample", "--round", "1", "--n", "4") == 2
    assert "use a new --round" in capsys.readouterr().err


def test_pipeline_end_to_end_and_report(env, capsys):
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    table = TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")
    stems = {r["stem"] for r in table}
    assert {"generous", "warm", "unflappable", "patient", "kind"} <= stems and "walter" not in stems
    assert run(common, "stats", "--round", "1", "--step", "4") == 0
    st = json.loads((tmp / "base" / "stats_round1.json").read_text())
    assert "_provenance" in st and st["result"]["recovery_strings"]["found"] == 3
    assert run(common, "submit", "--round", "1", "--run-id", "r1") == 0
    out = capsys.readouterr().out
    assert "traithood_filter.py --batch-id r1_base_model --run base_model/r1" in out
    rd = tmp / "cand" / "runs" / "base_model" / "r1"
    run_json = json.loads((rd / "run.json").read_text())
    assert run_json["args"]["round"] == 1 and len(run_json["args"]["table_sha256"]) == 64
    # pretend M1 and M3 ran on two rows, one of them from the AI family
    reg = Registry(tmp / "cand" / "registry.jsonl")
    folded = reg.fold()
    reg.merge_block("generous#1", "filter", {"verdict": "trait", "outcome": "trait", "alignment": 1}, replace=True)
    reg.merge_block("humility#1", "filter", {"verdict": "reject", "outcome": "turned_away"}, replace=True)
    reg.merge_block("generous#1", "novelty", {"decision": "new", "readings": [{"relation": "antonym"}]}, replace=True)
    assert "humility#1" in folded
    assert run(common, "report", "--run-id", "r1") == 0
    md = (rd / "report.md").read_text()
    assert "measured pass rate 50.0%" in md and "**ai_assistant**" in md
    assert "../../../../base/candidate_table_round1.jsonl" in md or "candidate_table_round1.jsonl" in md
    sample = (rd / "roger_sample.md").read_text()
    assert "| 1 | generous |" in sample
    ev = json.loads((rd / "evaluation.json").read_text())["result"]
    assert ev["m3"]["decision"] == {"new": 1} and ev["cost"]["total_usd"] == 0.0
