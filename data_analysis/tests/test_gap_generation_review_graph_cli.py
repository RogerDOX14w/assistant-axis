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
    # (schema 2 before gate audit 8: 3 adds the pair floor and the label variants; 4 the relabel pairs, 2026-10-14)
    assert g.config["proposed_cut_off"] == 3 and run["settings"]["proposed_cut_off"] == 3 and g.schema == 4
    assert g.config["pair_floor"] == 0.55 and run["settings"]["pair_floor"] == 0.55
    assert run["plan"]["edges_by_via"] == {"k_nearest": len([e for e in g.edges if e.source == "r1"]),
                                           "pair_floor": 0, "label_variant": 0}
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


# --------------------------------------------------------------------------- gate audit 8 (Roger, 2026-10-12)

def test_the_pair_floor_in_the_cli_and_none_for_the_rule_before(env, capsys):
    # k = 1: the godless triangle's third side (irreligious / nonreligious, 0.81) is in neither list; the pair floor
    # (default 0.55) brings it in, --pair-floor none leaves it out
    assert build(env, "--k", "1") == 0
    g = RG.Graph.from_json(json.loads((out(env) / "graph.json").read_text()))
    run = json.loads((out(env) / "run.json").read_text())
    assert run["plan"]["edges_by_via"]["pair_floor"] == 1 and run["settings"]["pair_floor"] == 0.55
    assert ["godless#1", "irreligious#1", "nonreligious#1"] in g.cliques
    e = next(x for x in g.edges if (x.a, x.b) == ("irreligious#1", "nonreligious#1"))
    assert e.via == "pair_floor" and e.strict
    assert build(env, "--k", "1", "--pair-floor", "none", batch="rv_old") == 0
    g0 = RG.Graph.from_json(json.loads((out(env, "rv_old") / "graph.json").read_text()))
    run0 = json.loads((out(env, "rv_old") / "run.json").read_text())
    assert run0["settings"]["pair_floor"] is None and g0.config["pair_floor"] is None
    assert run0["plan"]["edges_by_via"] == {"k_nearest": run0["plan"]["n_candidate_edges"], "pair_floor": 0,
                                            "label_variant": 0}
    assert ["godless#1", "irreligious#1", "nonreligious#1"] not in g0.cliques
    with pytest.raises(SystemExit):
        build(env, "--pair-floor", "high", "--dry-run", batch="rv_bad")


def test_the_estimate_is_calibrated_on_an_earlier_r1_build(env, capsys):
    # the default calibration (review_tda_1) is not under this out-root: M3's shares, said so
    assert build(env) == 0
    o = capsys.readouterr().out
    assert "shares (M3's" in o and "default calibration review_tda_1 not found" in o
    run1 = json.loads((out(env) / "run.json").read_text())
    assert run1["estimate_inputs"]["calibration"]["source"] == "m3_blocks"
    # named: rv1's own graph and records
    assert build(env, "--calibrate-from", "rv1", "--dry-run", batch="rv2") == 0
    o = capsys.readouterr().out
    assert "shares (R1's own, by cosine bin, from rv1)" in o and '"source": "r1:rv1"' in o
    assert "unsure [" in o and "overlap, second direction, Opus (" in o
    assert build(env, "--calibrate-from", "rv1", batch="rv2") == 0
    run2 = json.loads((out(env, "rv2") / "run.json").read_text())
    cal = run2["estimate_inputs"]["calibration"]
    assert cal["source"] == "r1:rv1" and cal["builds"] == ["rv1"] and run2["estimate_inputs"]["shares"]["source"] == "r1:rv1"
    capsys.readouterr()
    # a named build that is not there is refused; none is M3's shares, the rule before
    assert build(env, "--calibrate-from", "nope", "--dry-run", batch="rv3") == 2
    assert "--calibrate-from: no graph.json for nope" in capsys.readouterr().err
    assert build(env, "--calibrate-from", "none", "--dry-run", batch="rv3") == 0
    assert "shares (M3's, by cosine bin, from the source batches' blocks; --calibrate-from none)" in capsys.readouterr().out


def _decisions(env, name="rv1"):
    """Roger's log on the toy graph: the godless triangle and skeptic merged into alpha; chain a and b into beta;
    chain c promoted alone.  Sonnet read 2 on irreligious > skeptic and nonreligious > skeptic (same resolution)
    and chain a > chain c (different)."""
    at = "2026-10-11T19:40:34+00:00"
    g1 = ["godless#1", "irreligious#1", "nonreligious#1", "skeptic#1"]
    evs = [{"group": "g1", "action": "open", "source": "merged:0", "members": g1, "status": "open"},
           {"group": "g1", "action": "resolve", "members": g1, "nominated": None, "resolution": "merge_into:trait:alpha"},
           {"group": "g2", "action": "open", "source": "merged:1", "members": ["chain_a#1", "chain_b#1"], "status": "open"},
           {"group": "g2", "action": "resolve", "members": ["chain_a#1", "chain_b#1"], "nominated": None,
            "resolution": "merge_into:trait:beta"},
           {"group": "g3", "action": "open", "source": "term:chain_c#1", "members": ["chain_c#1"], "status": "open"},
           {"group": "g3", "action": "resolve", "members": ["chain_c#1"], "nominated": "chain_c#1",
            "resolution": "promote"}]
    (out(env, name) / "decisions.jsonl").write_text(
        "".join(json.dumps({"seq": i, "at": at, "by": "roger", **e}) + "\n" for i, e in enumerate(evs, 1)))


def pilot(env, *extra, budget="1"):
    return cli.main(["opus-pilot", "--batch-id", "rv1", "--n", "4", "--budget-usd", budget, "--out-root",
                     str(env["cand_dir"]), *extra])


def test_the_opus_pilot_reads_what_sonnet_read_and_compares_with_roger(env, capsys):
    assert build(env) == 0
    assert pilot(env, "--dry-run") == 2                                   # no decisions.jsonl: no reference
    assert "settles no term" in capsys.readouterr().err
    _decisions(env)
    graph_bytes = (out(env) / "graph.json").read_bytes()
    sonnet_users = {(r["key"], r["stem"]): r["user"]
                    for r in map(json.loads, (out(env) / "responses.jsonl").read_text().splitlines())
                    if r["wave"] == "ov1_sonnet"}
    env["holder"].pop("client", None)
    assert pilot(env, "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"same": 2, "different": 1' in o and "selected: 2 same, 1 different (seed 20261012)" in o
    assert "prompts checked against the build's Sonnet records: 3 of 3 match" in o and "=== Opus call:" in o
    assert "client" not in env["holder"] and not (out(env) / "opus_pilot_1").exists()
    # Opus raises irreligious > skeptic to 3, leaves the other two at 2
    env["holder"]["responder"] = responder_for(RELATIONS, {**OVERLAP, ("irreligious", "skeptic", "opus"): 3})
    assert pilot(env) == 0
    o = capsys.readouterr().out
    sent = calls(env)
    assert len(sent) == 3 and all("opus" in kw["model"] for kw in sent)
    assert sorted(user_text(kw) for kw in sent) == sorted(
        sonnet_users[p] for p in [("chain_a#1", "chain_c#1"), ("irreligious#1", "skeptic#1"), ("nonreligious#1", "skeptic#1")])
    d = out(env) / "opus_pilot_1"
    for name in ("readings.jsonl", "report.json", "usage.json", "responses.jsonl", "run.json"):
        assert (d / name).exists(), name
    assert (out(env) / "graph.json").read_bytes() == graph_bytes            # the graph and its groups untouched
    rows = [json.loads(x) for x in (d / "readings.jsonl").read_text().splitlines()]
    by = {(r["a"], r["b"]): r for r in rows}
    assert by[("irreligious#1", "skeptic#1")]["opus"]["value"] == 3 and by[("irreligious#1", "skeptic#1")]["sonnet"] == 2
    assert by[("chain_a#1", "chain_c#1")]["reference"] == "different"
    assert by[("chain_a#1", "chain_c#1")]["resolution_b"] == "queue:chain_c"
    rep = json.loads((d / "report.json").read_text())["result"]
    assert rep["by_reference"]["same"]["raised"] == 1 and rep["by_reference"]["different"]["raised"] == 0
    assert "same      resolution: 1 of 2 answered raised to 3+ = 50%" in o and "[usage]" in o
    usage = json.loads((d / "usage.json").read_text())
    assert set(usage["per_model"]) == {NV.OPUS} and usage["n_calls"] == 3
    run = json.loads((d / "run.json").read_text())
    assert run["status"] == 0 and run["calls_sent"] == {"overlap:opus": 3} and run["pools"]["same"] == 2
    # a resume sends nothing already answered and writes the same report
    env["holder"].pop("client", None)
    assert pilot(env, "--resume") == 0
    assert calls(env) == [] and json.loads((d / "report.json").read_text())["result"] == rep
