"""The recovery harness end to end on the toy corpus (``recovery_test.py``), ``novelty_score.py score --hide``, and
``gap_registry.py submit --from`` (a run's ``candidates.jsonl``).  No API calls: the fake Anthropic client and the
hash embedder standing in for OpenAI's, as in the novelty CLI tests."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import recovery as RC
from assistant_axis.gapgen.registry import CANDIDATE_FIELDS, Candidate, Registry, read_candidates, submit_candidates
from assistant_axis.gapgen.runs import start_run
from assistant_axis.tests.fake_anthropic import user_text
from data_analysis.gap_generation import gap_registry
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.gap_generation import recovery_test as rt
from data_analysis.tests.test_gap_generation_novelty_cli import OVERLAP, RELATIONS, ROWS, make_env

ZROWS = ROWS + [("zetaish", "This means being zeta zeta gamma in every way.", "trait", 0, None)]
ZREL = RELATIONS | {("zetaish", "zeta"): "similar"}
ZOV = OVERLAP | {("zetaish", "zeta"): 4, ("zetaish", "gamma"): 4}
HIDDEN = ["alpha", "beta", "gamma", "lambda_mu"]
REGIONS = {"alpha": "moral_stance", "beta": "moral_stance", "gamma": "moral_stance", "lambda_mu": "moral_stance",
           "delta": "cognitive_epistemic", "epsilon": "cognitive_epistemic"}


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = make_env(tmp_path, monkeypatch, rows=ZROWS, relations=ZREL, overlap=ZOV)
    monkeypatch.setattr(rt, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(rt, "platform_dirty_files", lambda *a, **k: [])
    e["regions"] = tmp_path / "corpus_regions.json"
    e["regions"].write_text(json.dumps({"result": {s: {"region": r} for s, r in REGIONS.items()}}), encoding="utf-8")
    return e


def calls(env):
    c = env["holder"].get("client")
    return list(c.calls) if c is not None else []


def write_hidden(env, stems=HIDDEN, name="hidden.json"):
    p = env["tmp"] / name
    p.write_text(json.dumps({"hidden": list(stems)}), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- score --hide

def test_score_hide_scores_against_the_reduced_corpus_and_leaves_the_registry_alone(env):
    before = env["reg"].path.read_text()
    hp = write_hidden(env)
    assert cli.main(["score", "--batch-id", "red", "--run", "toy/r1", "--hide", str(hp), *env["base"]]) == 0
    assert env["reg"].path.read_text() == before                                    # nothing written to the registry
    d = env["cand_dir"] / "novelty" / "red"
    res = {r["key"]: r["novelty"] for r in cli._read_jsonl(d / "results.jsonl")}
    assert set(res) == {"alpha#1", "queued#1", "alphoid#1", "deltaish#1", "lambdaish#1", "zetaish#1"}
    for nv in res.values():
        assert not {x["stem"] for x in nv["listed"]} & set(HIDDEN)                   # never retrieved nor expanded
        assert nv["hide"]["sha256"] == RC.file_sha256(hp) and nv["hide"]["n_hidden"] == 4
    assert res["alpha#1"]["reason"] != "exact_label" and res["alpha#1"]["decision"] == "new"   # a hidden stem
    assert res["queued#1"]["exact_label"]["match"] == "queue"                       # the queue still covers
    assert res["zetaish#1"]["decision"] == "covered" and res["zetaish#1"]["covered_by"] == "zeta"
    run = json.loads((d / "run.json").read_text())
    assert run["hide"] == {"path": str(hp), "sha256": RC.file_sha256(hp), "n_hidden": 4}
    assert run["plan"]["corpus"]["n_corpus"] == 7
    s = json.loads((d / "summary.json").read_text())
    assert s["result"]["hide"]["n_hidden"] == 4 and any(i["dep_key"] == "hidden" for i in s["_provenance"]["inputs"])


def test_score_hide_takes_rows_another_run_decided(env):
    assert cli.main(["score", "--batch-id", "full", "--run", "toy/r1", *env["base"]]) == 0
    before = env["reg"].path.read_text()
    hp = write_hidden(env)
    assert cli.main(["score", "--batch-id", "red", "--run", "toy/r1", "--hide", str(hp), *env["base"]]) == 0
    assert env["reg"].path.read_text() == before
    assert len(cli._read_jsonl(env["cand_dir"] / "novelty" / "red" / "results.jsonl")) == 6


def test_score_hide_refusals(env, capsys):
    hp = write_hidden(env)
    base = ["score", "--batch-id", "red", "--run", "toy/r1", *env["base"]]
    assert cli.main([*base, "--hide", str(write_hidden(env, ["alpha", "nope"], "bad.json"))]) == 2
    assert "not in the corpus" in capsys.readouterr().err
    (env["tmp"] / "junk.json").write_text("{}")
    assert cli.main([*base, "--hide", str(env["tmp"] / "junk.json")]) == 2
    assert cli.main(["score", "--batch-id", "x", "--redecide", "--from-batch", "red", "--hide", str(hp), *env["base"]]) == 2
    assert "--hide is for a new score run" in capsys.readouterr().err
    assert cli.main([*base, "--hide", str(hp), "--dry-run"]) == 0
    assert "no registry write: --hide" in capsys.readouterr().out
    assert cli.main([*base, "--hide", str(hp)]) == 0
    other = write_hidden(env, ["delta", "epsilon"], "other.json")
    assert cli.main([*base, "--hide", str(other), "--resume"]) == 2               # a resume hides the same traits
    assert "a resume must hide the same traits" in capsys.readouterr().err


# --------------------------------------------------------------------------- the harness

def fixed_draw(stems=HIDDEN):
    """``draw_hidden`` replaced: the same hidden set for every seed (the triangle and lambda mu)."""
    def draw(traits, *, frac, seed, regions, kinds):
        groups = [["alpha", "beta", "gamma"], ["lambda_mu"]]
        tr = {s: {"region": regions.get(s), "stratum": "moral_stance", "kind": kinds.get(s), "group": i}
              for i, g in enumerate(groups) for s in g}
        return {"schema": 1, "seed": seed, "hidden_frac": frac, "n_corpus": len(traits), "n_target": 4,
                "n_hidden": 4, "n_groups": 2, "hidden": sorted(stems), "groups":
                [{"members": g, "stratum": "moral_stance", "kind": kinds.get(g[0])} for g in groups],
                "strata": {"moral_stance": {"n_traits": 5, "n_groups": 2, "quota": 4, "n_hidden": 4, "n_groups_hidden": 2}},
                "traits": tr}
    return draw


def harness(env, *extra):
    return rt.main(["--generator", "toy", "--run-id", "r1", "--hidden-frac", "0.3", "--budget-usd", "2",
                    "--registry", str(env["reg"].path), "--data-dir", str(env["data"]), "--out-root", str(env["cand_dir"]),
                    "--metric-config", str(env["tmp"] / "metric_config.json"), "--cache-dir", str(env["tmp"] / "cache"),
                    "--regions", str(env["regions"]), "--transport", "live", *extra])


def test_the_harness_end_to_end(env, monkeypatch, capsys):
    monkeypatch.setattr(RC, "draw_hidden", fixed_draw())
    before = env["reg"].path.read_text()
    rec = env["cand_dir"] / "recovery" / "rec_toy_r1"
    # the dry run: the draws, the M3 dry runs and the estimate; nothing written, nothing sent
    assert harness(env, "--dry-run") == 0
    o = capsys.readouterr().out
    assert "seed 0: hidden 4 of 11 traits" in o and "seed 1: hidden 4" in o and "total estimate = $" in o
    assert "hard cap of the whole harness: $2.00" in o
    assert not rec.exists() and not (env["cand_dir"] / "novelty").exists() and calls(env) == []
    # the run
    assert harness(env) == 0
    assert env["reg"].path.read_text() == before                                    # the registry is never written
    for s in (0, 1):
        sd = rec / f"seed{s}"
        for name in ("hidden.json", "matches.jsonl", "responses.jsonl", "usage.json"):
            assert (sd / name).exists(), (s, name)
        m3 = env["cand_dir"] / "novelty" / f"rec_toy_r1_s{s}"
        run = json.loads((m3 / "run.json").read_text())
        assert run["hide"]["sha256"] == RC.file_sha256(sd / "hidden.json") and run["status"] == 0
    for name in ("recovery_report.json", "recovery_report.md", "usage.json", "run.json"):
        assert (rec / name).exists(), name
    rep = json.loads((rec / "recovery_report.json").read_text())
    assert "_provenance" in rep
    rep = rep["result"]
    f = rep["seeds"][0]
    k = f["kept"]
    # kept: alpha (its label is a hidden stem), alphoid (Sonnet 4 on alpha), deltaish, lambdaish
    assert f["candidates"]["by_decision"] == {"new": 4, "covered": 2}
    assert k["n_recovered"] == 1 and k["recall"] == 0.25 and k["by_label"] == 1
    assert {b["key"] for b in k["recovered"][0]["by"]} == {"alpha#1", "alphoid#1"}
    assert k["candidates"] == {"n": 4, "n_recovering": 2, "precision": 0.5}
    # zetaish: covered by zeta against the reduced corpus, but it fills hidden gamma's gap
    c = f["covered"]
    assert c["n_false_cover_candidates"] == 1 and c["false_covers"][0]["stem"] == "gamma"
    assert c["hidden_missed_only_through_covers"] == ["gamma"] and f["either"]["n_recovered"] == 2
    assert rep["mean"]["recall_kept"] == 0.25 and rep["n_seeds"] == 2
    cost = f["cost"]
    assert cost["total_usd"] == pytest.approx(cost["reduced_m3_usd"] + cost["match_usd"]) and cost["match_usd"] > 0
    total = json.loads((rec / "usage.json").read_text())
    assert total["total_cost_usd"] == pytest.approx(rep["total_cost_usd"], abs=1e-4)
    md = (rec / "recovery_report.md").read_text()
    assert "[gamma](../../../traits/instructions/gamma.json)" in md and "| zetaish |" in md
    run = json.loads((rec / "run.json").read_text())
    assert run["status"] == 0 and run["seeds_reported"] == [0, 1] and run["m3_runs"]["0"] == "rec_toy_r1_s0"
    matches = [json.loads(x) for x in (rec / "seed0" / "matches.jsonl").read_text().splitlines()]
    assert any(m["how"] == "label" and m["key"] == "alpha#1" for m in matches)
    # a second run is refused; --resume sends nothing (M3 finished, every match answer on record)
    assert harness(env) == 1
    env["holder"].pop("client", None)
    assert harness(env, "--resume") == 0
    assert calls(env) == []
    assert json.loads((rec / "recovery_report.json").read_text())["result"]["seeds"][0]["kept"]["n_recovered"] == 1


def test_the_harness_refusals(env, monkeypatch, capsys):
    monkeypatch.setattr(RC, "draw_hidden", fixed_draw())
    assert harness(env, "--budget-usd", "0.00001") == 2
    assert "exceeds --budget-usd" in capsys.readouterr().err
    assert not (env["cand_dir"] / "recovery" / "rec_toy_r1").exists()              # a refused run leaves nothing
    monkeypatch.setattr(rt, "platform_dirty_files", lambda *a, **k: [" M assistant_axis/gapgen/recovery.py"])
    assert harness(env) == 2
    assert "uncommitted changes" in capsys.readouterr().err
    assert rt.main(["--generator", "nobody", "--run-id", "r1", "--budget-usd", "1", "--registry", str(env["reg"].path),
                    "--data-dir", str(env["data"]), "--out-root", str(env["cand_dir"])]) == 2
    assert "no registry rows from nobody/r1" in capsys.readouterr().err
    assert harness(env, "--resume") == 1                                            # nothing to resume


def test_the_draw_is_real_without_the_patch(env, capsys):
    """Without the fixed draw: the harness's own draw (seeded, by region) reaches hidden.json."""
    assert harness(env, "--seed", "3", "--dry-run") == 0
    o = capsys.readouterr().out
    assert "seed 3: hidden 3 of 11 traits" in o or "seed 3: hidden 4 of 11 traits" in o or "seed 3: hidden 5 of 11" in o


# --------------------------------------------------------------------------- submit --from

def test_submit_from_a_runs_candidates_jsonl(tmp_path, capsys):
    reg = tmp_path / "registry.jsonl"
    run = start_run("gen_x", "pilot_1", candidates_dir=tmp_path)
    cands = [Candidate(surface="Brave", generator="gen_x", run_id="pilot_1", rank=1, score=2.5, source_ref="w:1"),
             Candidate(surface="kind-hearted", generator="gen_x", run_id="pilot_1", gloss_hint="g", sense_id=2,
                       partner_hint="callous")]
    submit_candidates(cands, registry_path=tmp_path / "elsewhere.jsonl", run=run)   # a run made in another checkout
    run.finish()
    path = run.dir / "candidates.jsonl"
    assert read_candidates(path) == cands                                          # exactly the dataclass round trip
    assert list(json.loads(path.read_text().splitlines()[0])) == list(CANDIDATE_FIELDS)
    run_json = (run.dir / "run.json").read_text()
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(path), "--dry-run"]) == 0
    assert "would submit 2 candidates" in capsys.readouterr().out and not reg.exists()
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(path)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["n_new"] == 2 and out["runs"] == {"gen_x/pilot_1": 2}
    rows = Registry(reg).fold()
    assert set(rows) == {"brave#1", "kind_hearted#2"} and rows["kind_hearted#2"]["sources"][0]["partner_hint"] == "callous"
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(path)]) == 0    # idempotent
    assert json.loads(capsys.readouterr().out)["n_unchanged"] == 2
    assert len(reg.read_text().splitlines()) == 2
    assert (run.dir / "run.json").read_text() == run_json                         # the run directory is not touched


def test_submit_from_refuses_what_is_not_a_candidate(tmp_path, capsys):
    reg = tmp_path / "registry.jsonl"
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps({"surface": "x", "generator": "g", "run_id": "r", "colour": "red"}) + "\n")
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(bad)]) == 2
    assert "bad.jsonl:1: fields Candidate does not have: colour" in capsys.readouterr().err
    bad.write_text("\n" + json.dumps({"surface": "x", "generator": "g"}) + "\n")
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(bad)]) == 2
    assert "bad.jsonl:2: missing run_id" in capsys.readouterr().err
    bad.write_text(json.dumps({"surface": "x", "generator": "../g", "run_id": "r"}) + "\n")
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(bad)]) == 2
    good = tmp_path / "good.jsonl"
    good.write_text(json.dumps({"surface": "x", "generator": "g", "run_id": "r"}) + "\n")
    assert gap_registry.main(["--registry", str(reg), "submit", "--from", str(good), "--generator", "g"]) == 2
    assert "drop --generator" in capsys.readouterr().err and not reg.exists()
    assert gap_registry.main(["--registry", str(reg), "submit", "--file", str(good)]) == 2   # --file needs both ids


def test_score_hide_with_the_seed_queue_in_the_search(env):
    """The reduced run searches the seed queue too (a new run), and the hiding reaches it: an entry whose recorded
    partner is hidden joins without the partner, so neither retrieval nor expansion nor the opposite rule reaches a
    hidden trait through the queue.  ``--no-queue-search`` passes through the harness's command line."""
    (env["data"] / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait"},
        {"stem": "anti_lambda", "label": "anti lambda", "status": "candidate", "entity_type": "trait", "partner": "lambda_mu",
         "description_draft": "This means being lambda mu lambda mu lambda in every way."}]}), encoding="utf-8")
    hp = write_hidden(env)
    assert cli.main(["score", "--batch-id", "redq", "--run", "toy/r1", "--hide", str(hp), *env["base"]]) == 0
    d = env["cand_dir"] / "novelty" / "redq"
    res = {r["key"]: r["novelty"] for r in cli._read_jsonl(d / "results.jsonl")}
    for nv in res.values():
        assert not {x["stem"] for x in nv["listed"] + nv["readings"]} & set(HIDDEN)
        assert nv["queue_search"]["n_entries"] == 1
    lam = res["lambdaish#1"]
    assert any(x["stem"] == "anti_lambda" and x["queue_status"] == "candidate" for x in lam["listed"])
    run = json.loads((d / "run.json").read_text())
    assert run["queue_search"]["stems"] == ["anti_lambda"] and run["hide"]["n_hidden"] == 4
    a = rt.build_parser().parse_args(["--generator", "toy", "--run-id", "r1", "--budget-usd", "1", "--no-queue-search"])
    a.batch_id = "rec_toy_r1"
    assert "--no-queue-search" in rt.score_argv(a, 0, hp, budget=1.0, dry_run=True, resume=False)
    a = rt.build_parser().parse_args(["--generator", "toy", "--run-id", "r1", "--budget-usd", "1"])
    a.batch_id = "rec_toy_r1"
    argv = rt.score_argv(a, 0, hp, budget=1.0, dry_run=True, resume=False)
    assert "--queue-search" not in argv and "--no-queue-search" not in argv          # the default: a new run's (on)
