"""The switch to Haiku 5.5 on the CLIs (coding_plan_haiku55.md, "The switch", 2026-10-08): the filter's
``--readings`` and its records, the resume guards, a re-decided run replaying its source's relation model,
the registry write of a re-decided run (``--write-registry`` / ``promote-redecide``) and its idempotence, and
the paraphrase cache's per-entry model.  No API call: fake clients, the toy corpus."""
import json
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.test_gapgen_batches import cli, _args  # noqa: F401  (the split CLI fixture)
from data_analysis.gap_generation import novelty_score as NS
from data_analysis.tests.test_gap_generation_novelty_cli import calls_made, make_env, out, score

H45, H55 = "claude-haiku-4-5-20251001", "claude-haiku-5-5"


# ---------------------------------------------------------------------------
# the filter CLI
# ---------------------------------------------------------------------------

class TestFilterCLI:
    def test_the_default_run_reads_three_times_and_records_it(self, cli):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--transport", "live")) == 0
        d = cli["out"] / "filter" / "p"
        run = json.loads((d / "run.json").read_text())
        assert run["model"] == H55 and run["readings"] == 3 and run["readings_rule"]
        assert run["plan"]["readings"] == 3 and "measured" in run["plan"]["token_figures"][H55]
        s = json.loads((d / "summary.json").read_text())["result"]
        rd = s["split"]["readings"]
        assert rd["n_readings"] == 3 and rd["n_words"] == 15
        assert rd["all_the_same"] == 15 and rd["rescued"]["n"] == 0     # the replayed answers never vary
        assert s["split"]["pilot_figures"]["same_outcome_as_expected"] == 15
        rows = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        assert all(r["filter"]["verdict_readings"]["n"] == 3 for r in rows)
        recs = [json.loads(x) for x in (d / "responses.jsonl").read_text().splitlines()]
        assert {r["verdict_reading"] for r in recs if r["step"] == "sense" and r["role"] == "first"} == {1, 2, 3}

    def test_dry_run_quotes_the_readings_and_the_figures(self, cli, capsys):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--dry-run")) == 0
        o = capsys.readouterr().out
        assert "readings: 3 of the verdict waves per word" in o
        assert "sense (3 readings): 45 x (820, 553) tokens at claude-haiku-5-5 rates" in o
        assert f"token figures per call: {H55}: measured" in o
        assert traithood_filter.main(_args(cli, "--dry-run", "--model", H45)) == 0
        o = capsys.readouterr().out
        assert "readings: 1 of the verdict waves" in o and "sense: 15 x (567, 207) tokens at claude-haiku-4-5-20251001 rates" in o
        assert traithood_filter.main(_args(cli, "--dry-run", "--model", H45, "--readings", "3")) == 0
        assert "sense (3 readings): 45 x (567, 207)" in capsys.readouterr().out

    def test_readings_refused_where_they_do_not_apply(self, cli, capsys):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--readings", "0")) == 2
        with pytest.raises(SystemExit):
            traithood_filter.main(_args(cli, "--pipeline", "single", "--readings", "3"))

    def test_resume_refuses_another_model_or_number_of_readings(self, cli, capsys):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--transport", "live", "--model", H45)) == 0
        capsys.readouterr()
        # an older batch resumed without its --model would go on with Haiku 5.5 and three readings
        assert traithood_filter.main(_args(cli, "--transport", "live", "--resume")) == 2
        assert f"resume with --model {H45}" in capsys.readouterr().err
        assert traithood_filter.main(_args(cli, "--transport", "live", "--resume", "--model", H45, "--readings", "3")) == 2
        assert "resume with --readings 1" in capsys.readouterr().err
        first = cli["live"]
        assert traithood_filter.main(_args(cli, "--transport", "live", "--resume", "--model", H45)) == 0
        assert cli["live"] is not first and cli["live"].calls == []      # every answer on record


def test_resume_mismatch_reads_an_old_run_as_one_reading():
    from data_analysis.gap_generation.split_cli import resume_mismatch
    a = SimpleNamespace(model=H45, readings=1)
    assert resume_mismatch({"model": H45}, a) is None                        # before 2026-10-08: no readings key
    assert resume_mismatch(None, a) is None
    assert "readings" in resume_mismatch({"model": H45, "readings": 3}, a)
    assert "--model" in resume_mismatch({"model": H55, "readings": 1}, a)


# ---------------------------------------------------------------------------
# M3: the relation model of a re-decided run, and the registry write
# ---------------------------------------------------------------------------

def redecide(env, batch, *extra, src="m3t"):
    return NS.main(["score", "--redecide", "--from-batch", src, "--batch-id", batch, "--corpus-at", "current",
                    *env["base"], *extra])


def test_a_redecided_run_replays_its_sources_relation_model(tmp_path, monkeypatch, capsys):
    """A run scored on Haiku 4.5 before the switch, re-decided after it: the relation answers on record are
    Haiku 4.5's and are found by model, so the re-decision asks for Haiku 4.5 and sends nothing."""
    env = make_env(tmp_path, monkeypatch)
    assert score(env, "--rules", "1", "--relation-model", H45) == 0
    rel = [json.loads(x) for x in (out(env) / "responses.jsonl").read_text().splitlines()]
    assert {r["model"] for r in rel if r["step"] == "relation"} == {H45}
    env["holder"].pop("client", None)
    assert redecide(env, "m3t_r", "--rules", "1") == 0
    assert calls_made(env) == []                                            # every answer was on record
    run = json.loads((out(env, "m3t_r") / "run.json").read_text())
    assert run["models"]["relation"] == H45 and run["redecide"]["relation_model"] == H45
    # and --relation-model is refused with --redecide
    capsys.readouterr()
    assert redecide(env, "m3t_x", "--relation-model", H55) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_source_relation_model_falls_back_to_the_records():
    assert NS.source_relation_model({"run": {"models": {"relation": H45}}}) == H45
    recs = [{"step": "relation", "model": H45}, {"step": "relation", "model": H45}, {"step": "overlap", "model": "x"}]
    assert NS.source_relation_model({"run": {}, "records": recs}) == H45
    assert NS.source_relation_model({"run": {}, "records": []}) == NS.NR.RELATION_MODEL == H55


def test_resume_of_an_m3_run_on_another_relation_model_is_refused(tmp_path, monkeypatch, capsys):
    env = make_env(tmp_path, monkeypatch)
    assert score(env, "--relation-model", H45, "--embed-only") == 0          # started before the switch, not finished
    capsys.readouterr()
    assert score(env, "--resume") == 2                                      # the default is Haiku 5.5 now
    assert f"resume with --relation-model {H45}" in capsys.readouterr().err
    assert calls_made(env) == []
    assert score(env, "--resume", "--relation-model", H45) == 0
    assert {k["model"] for k in calls_made(env) if "candidate" in json.loads(k["messages"][0]["content"])} == {H45}


def _reg_text(env):
    return env["reg"].path.read_text()


def test_write_registry_and_promote_redecide(tmp_path, monkeypatch, capsys):
    env = make_env(tmp_path, monkeypatch)
    assert score(env, "--rules", "1") == 0
    before = {k: r.get("novelty") for k, r in env["reg"].fold().items()}
    decided = {k for k, v in before.items() if v}
    assert decided and all(v["run_id"] == "m3t" for v in before.values() if v)
    env["holder"].pop("client", None)
    # a re-decision without the flag writes its own directory only
    assert redecide(env, "m3t_r2") == 0
    assert {k: r.get("novelty") for k, r in env["reg"].fold().items()} == before
    # --write-registry is for --redecide only
    capsys.readouterr()
    assert score(env, "--write-registry") == 2
    # promote-redecide: a dry run writes nothing; then every decided row takes the re-decided block
    raw = _reg_text(env)
    assert NS.main(["promote-redecide", "--batch-id", "m3t_r2", "--registry", str(env["reg"].path),
                    "--out-root", str(env["cand_dir"]), "--dry-run"]) == 0
    assert _reg_text(env) == raw and not (out(env, "m3t_r2") / "registry_writes.jsonl").exists()
    assert NS.main(["promote-redecide", "--batch-id", "m3t_r2", "--registry", str(env["reg"].path),
                    "--out-root", str(env["cand_dir"])]) == 0
    rows = env["reg"].fold()
    res = {r["key"]: r["novelty"] for r in NS._read_jsonl(out(env, "m3t_r2") / "results.jsonl")}
    assert set(res) == decided
    for k in decided:
        nv = rows[k]["novelty"]
        assert nv == res[k] and nv["run_id"] == "m3t_r2" and nv["redecided_from"] == "m3t"
    w = [json.loads(x) for x in (out(env, "m3t_r2") / "registry_writes.jsonl").read_text().splitlines()]
    assert len(w) == 1 and w[0]["counts"]["written"] == len(decided) and w[0]["replaced_runs"] == ["m3t"]
    # idempotent per (run, key): a second promotion appends nothing to the registry
    raw = _reg_text(env)
    assert NS.main(["promote-redecide", "--batch-id", "m3t_r2", "--registry", str(env["reg"].path),
                    "--out-root", str(env["cand_dir"])]) == 0
    assert _reg_text(env) == raw
    w = [json.loads(x) for x in (out(env, "m3t_r2") / "registry_writes.jsonl").read_text().splitlines()]
    assert w[-1]["counts"]["written"] == 0 and w[-1]["n_already"] == len(decided)
    # promote-redecide refuses a run that is not a re-decision
    capsys.readouterr()
    assert NS.main(["promote-redecide", "--batch-id", "m3t", "--registry", str(env["reg"].path),
                    "--out-root", str(env["cand_dir"])]) == 2
    assert "not a re-decided run" in capsys.readouterr().err


def test_a_row_decided_by_another_run_since_is_left_alone(tmp_path):
    reg = Registry(tmp_path / "registry.jsonl")
    reg.write([{"key": k, "label": k.split("#")[0]} for k in ("a#1", "b#1", "c#1", "d#1")])
    reg.update_many({"a#1": {"novelty": {"run_id": "src", "decision": "new"}},
                     "b#1": {"novelty": {"run_id": "later", "decision": "covered"}},
                     "c#1": {"novelty": {"run_id": "r2", "decision": "new", "redecided_from": "src"}}})
    results = [{"key": k, "novelty": {"run_id": "r2", "decision": "covered", "redecided_from": "src"}}
               for k in ("a#1", "b#1", "c#1", "d#1", "zz#1")] + [{"key": "e#1", "novelty": {"run_id": "r2"}}]
    rec = NS.promote_redecided(reg, results, run_id="r2", replaced_runs=["src", "r2"])
    assert rec["written"] == ["a#1", "d#1"]                     # the source's block, and a row with none
    assert rec["already"] == ["c#1"] and rec["other_run"] == {"later": ["b#1"]}
    assert rec["not_in_registry"] == ["zz#1"] and rec["undecided"] == ["e#1"]
    rows = reg.fold()
    assert rows["a#1"]["novelty"]["run_id"] == "r2" and rows["b#1"]["novelty"]["run_id"] == "later"
    assert rows["c#1"]["novelty"]["decision"] == "new"          # already this run's: not rewritten
    assert rec["replaced_runs"] == ["src"]


def test_write_registry_at_the_end_of_a_redecide(tmp_path, monkeypatch):
    env = make_env(tmp_path, monkeypatch)
    assert score(env, "--rules", "1") == 0
    env["holder"].pop("client", None)
    assert redecide(env, "m3t_w", "--write-registry") == 0
    rows = env["reg"].fold()
    got = {k: r["novelty"]["run_id"] for k, r in rows.items() if r.get("novelty")}
    assert got and set(got.values()) == {"m3t_w"}
    run = json.loads((out(env, "m3t_w") / "run.json").read_text())
    assert run["redecide"]["write_registry"] is True
    assert (out(env, "m3t_w") / "registry_writes.jsonl").exists()


# ---------------------------------------------------------------------------
# the paraphrase cache names the model of each entry
# ---------------------------------------------------------------------------

def test_paraphrase_cache_models(tmp_path):
    from data_analysis.gap_generation import calibrate_metric as CM
    old = {"model": H45, "paraphrases": {"a": "x", "b": "y"}}
    assert CM.paraphrase_models(old) == {"a": H45, "b": H45}
    mixed = {"model": "mixed", "models": {"a": H45, "c": H55}, "paraphrases": {"a": "x", "c": "z"}}
    assert CM.paraphrase_models(mixed) == {"a": H45, "c": H55}
    assert CM._one_model([H45, H45]) == H45 and CM._one_model([H45, H55]) == "mixed" and CM._one_model([]) is None
    p = tmp_path / "paraphrases.json"
    assert CM.paraphrase_cache_model(p) is None
    p.write_text(json.dumps(old))
    assert CM.paraphrase_cache_model(p) == H45
    p.write_text(json.dumps(mixed))
    assert CM.paraphrase_cache_model(p) == {H45: 1, H55: 1}


def test_a_topped_up_cache_says_which_model_wrote_what(tmp_path, monkeypatch):
    from data_analysis.gap_generation import calibrate_metric as CM
    p = tmp_path / "paraphrases.json"
    p.write_text(json.dumps({"model": H45, "style": "standard", "paraphrases": {"a": "old a"}, "sources": {}}))

    async def fake_run(client, todo, *, usage, style):
        return {it["stem"]: f"new {it['stem']}" for it in todo}
    monkeypatch.setattr(CM.CL, "run_paraphrases", fake_run)
    monkeypatch.setattr(CM, "_anthropic_client", lambda: None)
    ci = {"corpus": {"b": {"label": "b", "description": "This means b."}}}
    from assistant_axis.judge_pricing import MultiModelUsage
    CM.run_paraphrase_stage(ci, ["b"], p, {}, MultiModelUsage())
    d = json.loads(p.read_text())
    assert d["models"] == {"a": H45, "b": CM.CL.PARAPHRASE_MODEL} and d["model"] == "mixed"
    assert d["paraphrases"] == {"a": "old a", "b": "new b"}
