"""``corpus_near_duplicates.py`` end to end on the toy corpus: the dry run, the run and its files, the refusals, a
resume that sends nothing again, and ``report``.  No API calls: the fake Anthropic client, and the hash embedder
standing in for OpenAI's to put the toy corpus in the embedding cache (as in the novelty CLI tests)."""
import json

import pytest

from assistant_axis.gapgen import embed as EM
from assistant_axis.gapgen.metric_config import MetricConfig
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic
from assistant_axis.tests.test_gapgen_near_duplicates import DROP_OR_MERGE, responder
from assistant_axis.tests.test_gapgen_novelty import write_corpus
from data_analysis.gap_generation import corpus_near_duplicates as cli
from data_analysis.gap_generation import novelty_score as NS
from data_analysis.tests.test_gap_generation_novelty_cli import CONFIG, FakeOpenAIEmbedder


@pytest.fixture
def env(tmp_path, monkeypatch):
    import anthropic
    import dotenv
    data = write_corpus(tmp_path / "data")
    cfg = tmp_path / "metric_config.json"
    cfg.write_text(json.dumps({"result": CONFIG}), encoding="utf-8")
    monkeypatch.setattr(EM, "OpenAIEmbedder", FakeOpenAIEmbedder)
    NS.load_index(MetricConfig.load(cfg), data_dir=data, cache=EM.EmbeddingCache(tmp_path / "cache"),
                  usage=MultiModelUsage(), allow_embed=True)
    cmp = tmp_path / "drop_or_merge.md"
    cmp.write_text(DROP_OR_MERGE, encoding="utf-8")
    (tmp_path / "m3runs").mkdir()
    holder = {"clients": []}

    def factory(*a, **k):
        c = FakeAsyncAnthropic(responder())
        holder["clients"].append(c)
        return c
    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc1234")
    holder["dirty"] = []
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: holder["dirty"])
    out = tmp_path / "out"
    common = ["--data-dir", str(data), "--metric-config", str(cfg), "--cache-dir", str(tmp_path / "cache"),
              "--out-dir", str(out), "--compare-with", str(cmp)]
    run = ["run", *common, "--m3-runs-dir", str(tmp_path / "m3runs"), "--cosine-floor", "-1",
           "--also", "eta/lambda_mu:Roger asked"]
    return {"out": out, "run": run, "common": common, "holder": holder}


def calls(env) -> int:
    return sum(len(c.calls) for c in env["holder"]["clients"])


def test_dry_run_writes_nothing(env, capsys):
    assert cli.main([*env["run"], "--budget-usd", "1", "--dry-run"]) == 0
    o = capsys.readouterr().out
    assert "estimate:" in o and "--- user ---" in o and '"target": {"label"' in o
    assert not env["out"].exists() and calls(env) == 0


def test_run_files_and_resume(env):
    assert cli.main([*env["run"], "--budget-usd", "1"]) == 0
    out = env["out"]
    for f in ("pairs.jsonl", "responses.jsonl", "usage.json", "run.json", "near_duplicates.md", "run.log"):
        assert (out / f).exists(), f
    rows = [json.loads(x) for x in (out / "pairs.jsonl").read_text().splitlines()]
    asked = next(r for r in rows if (r["a"], r["b"]) == ("eta", "lambda_mu"))
    assert asked["section"] == "one_way" and "asked" in asked["sources"] and asked["ba"]["final"] == 4
    assert all(r["section"] != "incomplete" for r in rows)
    n = calls(env)
    recs = (out / "responses.jsonl").read_text().splitlines()
    assert n == len(recs) > len(rows)
    usage = json.loads((out / "usage.json").read_text())
    assert usage["n_calls"] == n and "_provenance" in usage and usage["total_cost_usd"] > 0
    run = json.loads((out / "run.json").read_text())
    assert set(run) == {"result", "_provenance"}
    r = run["result"]
    assert r["complete"] and r["status"] == 0 and r["cost_usd"] == pytest.approx(usage["total_cost_usd"], abs=1e-4)
    assert r["settings"]["cut_off"] == 3 and r["rubric"]["name"] == "overlap_concept"
    assert r["plan"]["n_traits"] == 11 and r["readings"]["sections"]
    assert {d["dep_key"] for d in run["_provenance"]["inputs"]} >= {"trait_files", "rubric", "metric_config",
                                                                  "cosine_table", "producer_script"}
    md = (out / "near_duplicates.md").read_text()
    assert "## Pairs Roger asked about" in md and "[lambda mu](../../traits/instructions/lambda_mu.json)" in md
    # a resume replays every answer on record and sends nothing
    before = md
    assert cli.main([*env["run"], "--budget-usd", "1", "--resume"]) == 0
    assert calls(env) == n
    assert [json.loads(x) for x in (out / "pairs.jsonl").read_text().splitlines()] == rows
    assert (out / "near_duplicates.md").read_text().split("## The run")[0] == before.split("## The run")[0]
    # report: the document again from the files, no call
    (out / "near_duplicates.md").unlink()
    assert cli.main(["report", *env["common"]]) == 0
    assert (out / "near_duplicates.md").exists() and calls(env) == n


def test_refusals(env):
    assert cli.main([*env["run"], "--budget-usd", "0.0001"]) == 2           # the estimate is over the cap
    env["holder"]["dirty"] = ["?? assistant_axis/gapgen/x.py"]
    assert cli.main([*env["run"], "--budget-usd", "1"]) == 2                 # uncommitted platform code
    assert not env["out"].exists() and calls(env) == 0
    assert cli.main([*env["run"][:-1], "eta", "--budget-usd", "1"]) == 2     # not A/B
    assert cli.main([*env["run"][:-1], "eta/nonesuch", "--budget-usd", "1", "--allow-dirty"]) == 2
