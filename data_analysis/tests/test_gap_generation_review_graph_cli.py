"""``review_graph.py`` (R1 of the review tooling) end to end on the toy corpus: the dry run, the build and its files,
the refusals, a stalled run and its resume, a run with no call, ``groups``, and the embedding path.  No API calls: the
fake Anthropic client, and the hash embedder standing in for OpenAI's (as in the novelty CLI tests); most tests place
the candidates' query vectors by hand (``query_vectors`` replaced) so that the edges are the module tests' ones."""
import json

import pytest

from assistant_axis.gapgen import embed as EM
from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import review_graph as RG
from assistant_axis.gapgen.metric_config import MetricConfig
from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.judge_pricing import MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, user_text
from assistant_axis.tests.test_gapgen_novelty import responder_for, write_corpus
from assistant_axis.tests.test_gapgen_review_graph import OVERLAP, OVERLAP3, RELATIONS, toy_rows, toy_vectors
from data_analysis.gap_generation import novelty_score as NS
from data_analysis.gap_generation import review_graph as cli
from data_analysis.tests.test_gap_generation_novelty_cli import CONFIG, FakeOpenAIEmbedder

BATCH = "m3b"


def make_env(tmp_path, monkeypatch, *, rows=None, place_vectors=True):
    import anthropic
    import dotenv
    data = write_corpus(tmp_path / "data")
    (data / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait"}]}), encoding="utf-8")
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    cfg = tmp_path / "metric_config.json"
    cfg.write_text(json.dumps({"result": CONFIG}), encoding="utf-8")
    monkeypatch.setattr(EM, "OpenAIEmbedder", FakeOpenAIEmbedder)
    # the corpus in the embedding cache, as M3's runs leave it
    NS.load_index(MetricConfig.load(cfg), data_dir=data, cache=EM.EmbeddingCache(tmp_path / "cache"),
                  usage=MultiModelUsage(), allow_embed=True)
    reg_path = cand_dir / "registry.jsonl"
    rows = rows if rows is not None else toy_rows()
    rep = submit_candidates([Candidate(surface=r["label"], generator=r["sources"][0]["generator"], run_id="r1")
                             for r in rows.values()], registry_path=reg_path)
    assert sorted(rep.keys) == sorted(rows)
    reg = Registry(reg_path)
    reg.update_many({k: {"filter": r["filter"], "gloss": r["gloss"], "novelty": r["novelty"]} for k, r in rows.items()})
    holder = {"responder": responder_for(RELATIONS, OVERLAP)}

    def factory(*a, **k):
        holder["client"] = FakeAsyncAnthropic(holder["responder"])
        return holder["client"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    if place_vectors:
        vec = toy_vectors()

        def placed(cands, **kw):
            return {k: vec[k] for k in cands if k in vec}, {"n_query_texts": len(cands), "n_cached": len(cands),
                                                             "n_to_embed": 0}
        monkeypatch.setattr(cli, "query_vectors", placed)
    base = ["--registry", str(reg_path), "--data-dir", str(data), "--out-root", str(cand_dir), "--metric-config",
            str(cfg), "--cache-dir", str(tmp_path / "cache"), "--transport", "live"]
    return {"base": base, "reg": reg, "cand_dir": cand_dir, "holder": holder, "data": data, "tmp": tmp_path}


@pytest.fixture
def env(tmp_path, monkeypatch):
    return make_env(tmp_path, monkeypatch)


def build(env, *extra, batch="rv1", budget="2"):
    return cli.main(["build", "--batch-id", batch, "--from-batches", BATCH, "--budget-usd", budget, *env["base"], *extra])


def out(env, name="rv1"):
    return env["cand_dir"] / "review" / name


def calls(env):
    c = env["holder"].get("client")
    return list(c.calls) if c is not None else []


def test_dry_run_prints_the_estimate_and_the_rendered_prompts_and_writes_nothing(env, capsys):
    before = env["reg"].path.read_text()
    assert build(env, "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"n_candidates": 11' in o and '"n_candidate_edges":' in o and "total estimate = $" in o
    assert "relation call (" in o and "overlap, first direction, Sonnet" in o and "hard cap: $2.00" in o
    assert "=== relation call" in o and '{"candidate": {"label":' in o
    assert "=== overlap call" in o and '{"target": {"label":' in o
    assert not out(env).exists() and calls(env) == [] and env["reg"].path.read_text() == before


def test_build_writes_the_graph_usage_and_run_and_never_the_registry(env, capsys):
    before = env["reg"].path.read_text()
    assert build(env) == 0
    assert env["reg"].path.read_text() == before
    d = out(env)
    for name in ("graph.json", "usage.json", "responses.jsonl", "run.json", "run.log"):
        assert (d / name).exists(), name
    raw = json.loads((d / "graph.json").read_text())
    g = RG.Graph.from_json(raw)
    assert g.complete and g.from_batches == [BATCH] and len(g.cliques) == 4 and len(g.singletons()) == 3
    assert g.cliques[0] == ["godless#1", "irreligious#1", "nonreligious#1"]
    assert g.config["overlap_rubric"] == 6 and g.config["relation_rubric"] == 1 and g.config["rules"] == "cut_off_4"
    assert g.config["embedding"] == {"model": "text-embedding-3-large", "query_form": "gloss_w14"}
    assert g.config["cut_off"] == 4 and g.config["overlap_floor"] == 0.35 and g.config["k"] == 10
    inputs = {i["dep_key"]: i for i in raw["_provenance"]["inputs"]}
    assert inputs["registry"]["extras"]["from_batches"] == BATCH
    assert inputs["rubrics"]["extras"] == {"overlap_rubric": "6", "relation_rubric": "1"}
    usage = json.loads((d / "usage.json").read_text())
    assert "_provenance" in usage and usage["total_cost_usd"] > 0
    assert MultiModelUsage.load_or_create(d / "usage.json").total_cost_usd == pytest.approx(usage["total_cost_usd"], abs=1e-4)
    assert set(usage["per_model"]) == {"claude-haiku-5-5", NV.SONNET, NV.OPUS}
    assert g.usage["per_model"].keys() == usage["per_model"].keys()
    run = json.loads((d / "run.json").read_text())
    assert run["status"] == 0 and run["complete"] and run["cost_usd"] > 0 and run["estimate_usd"] > 0
    assert run["calls_sent"]["overlap:sonnet"] > 0 and run["settings"]["cut_off"] == 4
    assert "four_edges" in run["graph_stats"]["overlap"]
    o = capsys.readouterr().out
    # (was "4 cliques" before decision 12: the print now names both tiers)
    assert "4 merged groups" in o and "1 proposed groups" in o and "[usage]" in o
    assert g.config["proposed_cut_off"] == 3 and run["settings"]["proposed_cut_off"] == 3 and g.schema == 2
    assert g.proposed_groups == [["godless#1", "skeptic#1"]]


def test_over_budget_is_refused_before_any_call(env, capsys):
    assert build(env, budget="0.00001") == 2
    assert "exceeds --budget-usd" in capsys.readouterr().err
    assert "client" not in env["holder"] and not out(env).exists()


def test_refusals(env, monkeypatch, capsys):
    assert cli.main(["build", "--batch-id", "rv1", "--from-batches", "nope", "--budget-usd", "2", *env["base"]]) == 2
    assert "no registry row" in capsys.readouterr().err
    assert build(env, "--resume") == 1                                                   # nothing to resume
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [" M assistant_axis/gapgen/review_graph.py"])
    assert build(env) == 2 and "uncommitted changes" in capsys.readouterr().err
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    assert build(env) == 0
    assert build(env) == 1                                                               # the dir exists
    assert "client" in env["holder"]


def test_a_stalled_run_then_resume_sends_only_the_unanswered(env, capsys):
    good = env["holder"]["responder"]

    def flaky(kw):
        if json.loads(user_text(kw)).get("target", {}).get("label") == "chain b":
            return RuntimeError("network down")
        return good(kw)
    env["holder"]["responder"] = flaky
    assert build(env) == 0
    assert "INCOMPLETE" in capsys.readouterr().out
    run = json.loads((out(env) / "run.json").read_text())
    g = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    assert not run["complete"] and not g.complete and g.stalled["overlap"]
    cost1 = json.loads((out(env) / "usage.json").read_text())["total_cost_usd"]
    env["holder"]["responder"] = good
    assert build(env, "--resume") == 0
    sent = [json.loads(user_text(kw)) for kw in calls(env)]
    assert all("target" in x for x in sent)                                   # no relation call again
    assert {(x["target"]["label"], x["other"]["label"]) for x in sent} == \
        {("chain b", "chain c"), ("chain b", "chain a"), ("chain c", "chain b")}
    g2 = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    assert g2.complete and len(g2.cliques) == 4
    run2 = json.loads((out(env) / "run.json").read_text())
    assert run2["resumed"] and len(run2["earlier_sessions"]) == 1
    assert json.loads((out(env) / "usage.json").read_text())["total_cost_usd"] > cost1     # the sessions add up


def test_usage_json_is_written_with_zero_calls(tmp_path, monkeypatch, capsys):
    rows = {k: r for k, r in toy_rows().items() if k in ("loner#1", "atheistic#1")}
    env = make_env(tmp_path, monkeypatch, rows=rows)
    assert build(env) == 0
    usage = json.loads((out(env) / "usage.json").read_text())
    assert usage["n_calls"] == 0 and usage["total_cost_usd"] == 0 and calls(env) == []
    g = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    assert g.candidate_keys() == ["loner#1"] and g.singletons() == ["loner#1"] and g.cliques == []
    assert g.node_map()["atheistic#1"].covered_by == "trait:alpha"


def test_groups_lists_the_cliques_largest_first(env, capsys):
    assert cli.main(["groups", "--batch-id", "rv1", "--out-root", str(env["cand_dir"])]) == 1     # no graph yet
    assert build(env) == 0
    capsys.readouterr()
    assert cli.main(["groups", "--batch-id", "rv1", "--out-root", str(env["cand_dir"])]) == 0
    o = capsys.readouterr().out
    # (was "11 candidates, 4 cliques (sizes 3: 1, 2: 3), 3 singletons" before decision 12)
    assert "11 candidates, 4 merged groups, 1 proposed groups, 2 in no group" in o
    assert "merged groups (4-edges both ways): 4 (sizes 3: 1, 2: 3)" in o
    assert "proposed groups (3-edges both ways, none wholly inside a merged group): 1 (sizes 2: 1)" in o
    lines = [x for x in o.splitlines() if x.lstrip().startswith("[")]
    assert lines[0].lstrip().startswith("[0] 3: godless, irreligious, nonreligious")
    assert "opposed to [3]" in lines[0]
    assert lines[-1].strip() == "[0] 2: godless, skeptic"          # its opposed pole, pious, is in a merged group


def test_the_embedding_path_with_the_hash_embedder(tmp_path, monkeypatch, capsys):
    env = make_env(tmp_path, monkeypatch, place_vectors=False)
    assert build(env, "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"n_to_embed": 11' in o and "query embeddings not in the cache" in o
    assert build(env) == 0
    usage = json.loads((out(env) / "usage.json").read_text())
    assert "text-embedding-3-large" in usage["per_model"]
    capsys.readouterr()
    assert build(env, "--dry-run", batch="rv2") == 0                       # now cached: nothing left to embed
    assert '"n_to_embed": 0' in capsys.readouterr().out


def test_a_graph_built_at_cut_off_4_is_resumed_at_3_reading_only_the_missing_second_directions(env, capsys):
    env["holder"]["responder"] = responder_for(RELATIONS, OVERLAP3)          # the godless triangle reads 3 / 3
    assert build(env, "--proposed-cut-off", "4") == 0
    g4 = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    assert g4.proposed_groups == [] and g4.config["proposed_cut_off"] == 4
    cost1 = json.loads((out(env) / "usage.json").read_text())["total_cost_usd"]
    capsys.readouterr()
    # the dry run of the resume: the replay finds the three missing second directions, priced on their own
    assert build(env, "--resume", "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"calls_not_on_record": {"ov2_sonnet": 3}' in o
    assert "overlap, second direction, Sonnet, not on record: 3 x" in o and "relation call" not in o.split("estimate")[1]
    assert f"with the ${cost1:.3f} spent by the earlier sessions" in o
    assert build(env, "--resume") == 0
    sent = [json.loads(user_text(kw)) for kw in calls(env)]
    assert {(x["target"]["label"], x["other"]["label"]) for x in sent} == \
        {("irreligious", "godless"), ("nonreligious", "godless"), ("nonreligious", "irreligious")}
    g3 = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    assert g3.complete and g3.config["proposed_cut_off"] == 3
    assert ["godless#1", "irreligious#1", "nonreligious#1"] in g3.proposed_groups
    run = json.loads((out(env) / "run.json").read_text())
    assert run["resume_estimate"]["calls_not_on_record"] == {"ov2_sonnet": 3}
    assert run["resume_estimate"]["spent_usd"] == pytest.approx(cost1, abs=1e-4)


def test_a_resume_is_capped_with_the_earlier_spend(env, capsys):
    env["holder"]["responder"] = responder_for(RELATIONS, OVERLAP3)
    assert build(env, "--proposed-cut-off", "4") == 0
    cost1 = json.loads((out(env) / "usage.json").read_text())["total_cost_usd"]
    capsys.readouterr()
    # a cap below the earlier spend plus the new calls refuses the resume before any call
    assert build(env, "--resume", budget=f"{cost1 + 0.0001:.4f}") == 2
    assert "exceeds --budget-usd" in capsys.readouterr().err
