"""The base-model generator's CLI (``base_model_generator.py``): every subcommand's dry run writes nothing; fetch
needs Roger's recorded approval; bench and sample refuse without the model and never download; the pipeline
parse -> sense -> stats -> submit -> report runs end to end on fixtures (fake lookups, the hash embedder, a fake
model, tmp registry)."""
import hashlib
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.base_model import sense as SE
from assistant_axis.gapgen.generators.base_model import table as TB
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.base_model_fakes import (
    CENSUS_TABLE_SMALL, ONET_SMALL, SAMPLES_SMALL, make_wikibio_zip, samples_small_text,
)
from assistant_axis.tests.censuses_fakes import make_corpus
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response
from assistant_axis.tests.test_gapgen_base_model_table import lookups
from data_analysis.gap_generation import base_model_generator as CLI

SENSE_ANSWER = json.dumps({"choice": "dictionary", "legible": False,
                           "reason": "the dictionary sense is the one a reader would take"})


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
    # the gloss-sense step's one call: a fake model, so no request leaves the process
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(lambda kw: make_response(
        SENSE_ANSWER, input_tokens=400, output_tokens=40)))
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
    after_parse = snapshot(tmp)
    assert run(common, "sense", "--round", "1", "--arm", "hash", "--dry-run") == 0
    assert snapshot(tmp) == after_parse
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
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


def test_submit_refuses_before_the_sense_step(env, capsys):
    """QUESTIONS 56: a table straight out of `parse` has rows with two candidate senses, and M1 must not see
    one that could change afterwards."""
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    assert run(common, "submit", "--round", "1", "--run-id", "r0") == 2
    err = capsys.readouterr().err
    assert "sense --round 1" in err and "QUESTIONS 56" in err
    assert not (tmp / "cand" / "runs").exists()


def test_sense_settles_the_divergent_rows(env, capsys):
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    out = capsys.readouterr().out
    assert "divergent" in out and "claude-haiku-5-5" in out
    table = TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")
    blocks = {r["stem"]: r.get(SE.BLOCK) for r in table if r.get(SE.BLOCK)}
    assert "unflappable" in blocks and blocks["unflappable"]["chosen"] in SE.CHOICES
    assert SE.unresolved(table) == []
    # the fake answered "dictionary" (and called the sample reading illegible), so the hint is unchanged
    assert SE.resolved_hint(next(r for r in table if r["stem"] == "unflappable")).startswith("not easily")
    u = json.loads((tmp / "samples" / "round1" / SE.USAGE_NAME).read_text())
    # the free screen's embedding calls and the paid sense calls are both recorded; only the latter cost
    assert u["total_cost_usd"] > 0 and u["per_model"][SE.MODEL]["n_calls"] >= 1
    rec = (tmp / "samples" / "round1" / SE.RESPONSES_NAME).read_text().splitlines()
    assert len(rec) == u["per_model"][SE.MODEL]["n_calls"]
    # rerunning it is a no-op: the decisions are on the rows
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    assert "nothing to screen" in capsys.readouterr().out
    # and a reparse carries them forward rather than throwing away what was paid for
    assert run(common, "parse", "--round", "1") == 0
    out = capsys.readouterr().out
    assert "carried 2 gloss-sense decisions forward" in out
    assert SE.unresolved(TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")) == []


def test_sense_rerun_asks_again_for_a_row_whose_call_failed(env, capsys):
    """A row whose call failed twice stays unresolved (submit refuses it rather than guessing), and a rerun of
    sense must ask for it again even when nothing needs the free screen; before 2026-10-12 the rerun returned
    early with such rows left as they were."""
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    capsys.readouterr()
    path = tmp / "base" / "candidate_table_round1.jsonl"
    table = TB.load_table(path)
    row = next(r for r in table if r["stem"] == "unflappable")
    b = dict(row[SE.BLOCK])
    b.update({"chosen": None, "chosen_gloss": None, "legible": None, "reason": None,
              "error": "empty response; retry: empty response"})
    row[SE.BLOCK] = b
    TB.write_table(table, path)
    assert SE.stale_reason(row) == "failed" and [r["stem"] for r in SE.unresolved(table)] == ["unflappable"]
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    out = capsys.readouterr().out
    assert "still need their call" in out and "nothing to screen;" in out
    table = TB.load_table(path)
    assert SE.unresolved(table) == []
    assert next(r for r in table if r["stem"] == "unflappable")[SE.BLOCK]["chosen"] in SE.CHOICES


def test_submit_records_the_floor_with_the_tables_sample_size(env, capsys):
    """Gate audit 3 (Roger, 2026-10-12): the default floor is 2, chosen at 2,000 samples; the run records it
    with the size of the table it was applied to (parse's counts: 8 samples here) and says when they differ."""
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    capsys.readouterr()
    assert run(common, "submit", "--round", "1", "--run-id", "f1") == 0
    out = capsys.readouterr().out
    assert "count floor: 2 at 8 samples" in out and "NOTE: the count floor 2 was chosen at 2,000 samples" in out
    assert "all rows, as if none had a verdict" in out and "the gate reads this one" in out
    rd = tmp / "cand" / "runs" / "base_model" / "f1"
    a = json.loads((rd / "run.json").read_text())["args"]
    assert a["min_count"] == 2 and a["floor"]["n_samples"] == 8 and a["floor"]["chosen_at_n_samples"] == 2000
    assert a["floor"]["flag_given"] is False
    assert json.loads((rd / "submit_report.json").read_text())["floor"] == a["floor"]
    # a value typed for this table is recorded as chosen for it, with no note
    assert run(common, "submit", "--round", "1", "--run-id", "f2", "--min-count", "3", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "count >= 3" in out and "chosen at 8 samples (--min-count, set for this run)" in out
    assert "NOTE" not in out


def test_parse_refuses_a_person_sample_it_cannot_screen(env, capsys):
    """QUESTIONS 54: the tracked table carries no biography text, which the echo screen ensures; without the
    biography (the archive missing, or a pool that does not hold the sample's ref) the screen would be skipped
    silently, so `parse` refuses and writes nothing (review of 2026-10-12)."""
    tmp, common = env
    rec = tmp / "samples" / "round1" / "sampling.json"
    d = json.loads(rec.read_text())
    d["bundle"]["bio_pool_size"] = 0                    # a pool that holds none of the samples' biographies
    rec.write_text(json.dumps(d))
    for argv in (["parse", "--round", "1", "--dry-run"], ["parse", "--round", "1"]):
        assert run(common, *argv) == 2, argv
        assert "no biography to screen against" in capsys.readouterr().err
    assert not (tmp / "base" / "candidate_table_round1.jsonl").exists()
    # the archive itself missing: the same refusal
    d["bundle"]["bio_pool_size"] = 50
    rec.write_text(json.dumps(d))
    (tmp / "ext" / "wikibio" / "data" / "wikipedia-biography-dataset.zip").unlink()
    assert run(common, "parse", "--round", "1") == 2
    assert "QUESTIONS 54" in capsys.readouterr().err
    assert not (tmp / "base" / "candidate_table_round1.jsonl").exists()


def test_sense_stops_at_its_cap_and_keeps_what_it_paid_for(env, capsys, monkeypatch):
    """--budget-usd is a hard cap on the sense calls (gapgen.cost.GuardedUsage), not only a check of the estimate;
    a stop part-way keeps the decision that crossed the cap on the table and the usage on disk, and exits 1
    (review of 2026-10-12: before, the cap was never enforced live and a failure lost the paid decisions)."""
    tmp, common = env
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(lambda kw: make_response(
        SENSE_ANSWER, input_tokens=400, output_tokens=50_000_000)))          # $25 a call at Haiku 5.5's rates
    assert run(common, "parse", "--round", "1") == 0
    capsys.readouterr()
    assert run(common, "sense", "--round", "1", "--arm", "hash", "--budget-usd", "2") == 1
    err = capsys.readouterr().err
    assert "STOPPED at the cap" in err
    table = TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")
    decided = [r for r in table if (r.get(SE.BLOCK) or {}).get("chosen") in SE.CHOICES
               and r[SE.BLOCK].get("divergent")]
    assert len(decided) == 1                         # the call that crossed the cap was answered and is kept
    assert SE.unresolved(table)                      # the rest wait for a rerun
    u = json.loads((tmp / "samples" / "round1" / SE.USAGE_NAME).read_text())
    assert u["per_model"][SE.MODEL]["n_calls"] == 1 and u["total_cost_usd"] > 2
    # a rerun with room asks only for what is still unresolved, and the usage file accumulates
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: FakeAsyncAnthropic(lambda kw: make_response(
        SENSE_ANSWER, input_tokens=400, output_tokens=40)))
    assert run(common, "sense", "--round", "1", "--arm", "hash", "--budget-usd", "2") == 0
    assert SE.unresolved(TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")) == []
    u2 = json.loads((tmp / "samples" / "round1" / SE.USAGE_NAME).read_text())
    assert u2["per_model"][SE.MODEL]["n_calls"] == 1 + len(SE.unresolved(table))


def test_pipeline_end_to_end_and_report(env, capsys):
    tmp, common = env
    assert run(common, "parse", "--round", "1") == 0
    table = TB.load_table(tmp / "base" / "candidate_table_round1.jsonl")
    stems = {r["stem"] for r in table}
    assert {"generous", "warm", "unflappable", "patient", "kind"} <= stems and "walter" not in stems
    assert run(common, "sense", "--round", "1", "--arm", "hash") == 0
    assert run(common, "stats", "--round", "1", "--step", "4") == 0
    st = json.loads((tmp / "base" / "stats_round1.json").read_text())
    assert "_provenance" in st and st["result"]["recovery_strings"]["found"] == 3
    # the fixture's eight samples emit most words once, so the run takes every count (below the default floor 2)
    assert run(common, "submit", "--round", "1", "--run-id", "r1", "--min-count", "1") == 0
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
    assert "the estimate assumed 80%, with 95% printed as its high case" in md   # QUESTIONS 55
    assert "../../../../base/candidate_table_round1.jsonl" in md or "candidate_table_round1.jsonl" in md
    # QUESTIONS 54: the two echo rules apart, and what the name rule cost
    assert "## The biography-echo screen" in md and "name echo" in md
    assert "No word was lost" in md or "Words lost altogether" in md
    assert "flugzeugbau" not in md                      # a dropped span is never printed
    # QUESTIONS 61: the wiki_bio family against the clean-prompt ones, with yield and malformed rate
    assert "## By family: the `wiki_bio` prompts against the clean ones" in md
    assert "**person**" in md and "wiki_bio opening (lower-cased)" in md and "professions (clean)" in md
    # QUESTIONS 56: the sense section
    assert "## The gloss sense (settled before M1)" in md and "fidelity first" in md
    # gate audit 3: the floor with the sample size it was applied at, and the families before the floor
    assert "| count floor | count >= 1 at 8 samples (125.0 per 1,000 samples); chosen at 8 samples" in md
    assert "## By family, before the count floor (the eligible table)" in md
    assert "**Noun share of M1 survivors before the floor**" in md
    sample = (rd / "roger_sample.md").read_text()
    assert "| 1 | generous |" in sample and "hint sent to M1" in sample
    ev = json.loads((rd / "evaluation.json").read_text())["result"]
    assert ev["m3"]["decision"] == {"new": 1}
    # the sampler is still free; the run's cost is the gloss-sense calls alone
    assert json.loads((rd / "usage.json").read_text())["total_cost_usd"] == 0.0
    assert 0 < ev["cost"]["total_usd"] < 0.01
    assert ev["by_family"]["person"]["stats"]["malformed_rate"] is not None
