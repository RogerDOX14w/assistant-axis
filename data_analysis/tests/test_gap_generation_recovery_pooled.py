"""Plan 13 decision 1 on the toy corpus: the pooled harness (every generator at once, ``recovery_test.py
--pooled``), the affected-only reduced run (``--affected-only``, ``novelty_score.py score --affected-only``), the
fixed hidden list (``--hidden-file``) and the exclusions (``--exclude-stems``, ``--exclude-provenance``).

The acceptance test of decision 1 (c): with a deterministic responder, the affected-only run and a full re-score give
identical recall, precision and false covers, seed by seed, for a single run and for the pooled run; and the pooled
run's per-generator figures equal separate runs on the same draw.  No API calls: the fake Anthropic client and the
hash embedder of the novelty CLI tests."""
import json

import pytest

from assistant_axis.gapgen import recovery as RC
from assistant_axis.gapgen.registry import Candidate, submit_candidates
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.gap_generation import recovery_test as rt
from data_analysis.tests.test_gap_generation_novelty_cli import OVERLAP, RELATIONS, ROWS, make_env

#: More rows than the harness tests use, so that a draw leaves some rows unaffected (copied) and affects others.
XROWS = ROWS + [
    ("zetaish", "This means being zeta zeta gamma in every way.", "trait", 0, None),
    ("thetaesque", "This means being theta theta theta in every way.", "trait", 0, None),
    ("iotan", "This means being iota iota kappa in every way.", "trait", 1, None),
    ("kappalike", "This means being kappa kappa kappa in every way.", "trait", 0, None),
    ("etaform", "This means being eta eta eta in every way.", "trait", 0, None),
    ("epsilonic", "This means being epsilon epsilon delta in every way.", "trait", 0, None),
    ("betaish", "This means being beta beta beta in every way.", "trait", 0, None),
    ("gammoid", "This means being gamma gamma beta in every way.", "trait", 2, None),
    ("muish", "This means being lambda mu mu mu in every way.", "trait", 0, None)]
XREL = RELATIONS | {("zetaish", "zeta"): "similar", ("thetaesque", "theta"): "similar", ("iotan", "iota"): "similar",
                    ("kappalike", "kappa"): "similar", ("etaform", "eta"): "similar", ("betaish", "beta"): "similar",
                    ("gammoid", "gamma"): "similar", ("epsilonic", "epsilon"): "similar",
                    ("muish", "lambda mu"): "similar"}
XOV = OVERLAP | {("zetaish", "zeta"): 4, ("zetaish", "gamma"): 4, ("thetaesque", "theta"): 4, ("iotan", "iota"): 3,
                 ("kappalike", "kappa"): 2, ("etaform", "eta"): 4, ("betaish", "beta"): 4, ("gammoid", "gamma"): 3,
                 ("epsilonic", "epsilon"): 4, ("muish", "lambda mu"): 4}
REGIONS = {"alpha": "moral_stance", "beta": "moral_stance", "gamma": "moral_stance", "lambda_mu": "moral_stance",
           "delta": "cognitive_epistemic", "epsilon": "cognitive_epistemic", "theta": "communication_style",
           "iota": "communication_style", "zeta": "cognitive_epistemic", "eta": "cognitive_epistemic"}
#: A second generator proposing some of the same words and one of its own; a states-pass row from a toy row.
SECOND = [("zetaish", "toy2", "r2"), ("kappalike", "toy2", "r2"), ("betaish", "toy2", "r2")]


@pytest.fixture
def env(tmp_path, monkeypatch):
    e = make_env(tmp_path, monkeypatch, rows=XROWS, relations=XREL, overlap=XOV)
    monkeypatch.setattr(rt, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(rt, "platform_dirty_files", lambda *a, **k: [])
    e["regions"] = tmp_path / "corpus_regions.json"
    e["regions"].write_text(json.dumps({"result": {s: {"region": r} for s, r in REGIONS.items()}}), encoding="utf-8")
    return e


def add_second_generator(env):
    submit_candidates([Candidate(surface=s, generator=g, run_id=r) for s, g, r in SECOND],
                      registry_path=env["reg"].path)
    rep = submit_candidates([Candidate(surface="kappaesque", generator="states_pass", run_id="st1",
                                       source_ref="thetaesque#1")], registry_path=env["reg"].path)
    env["reg"].update_many({rep.keys[0]: {"filter": {"verdict": "trait", "outcome": "trait", "alignment": 0,
                                                     "region": "moral_stance"},
                                          "gloss": "This means being theta theta iota in every way.", "holding": None}})


def score_full(env):
    """The recorded blocks: one full-corpus M3 run over every row (the rules and seed-queue setting the harness's
    reduced runs use, so that a copied block is what a full-corpus run gives today)."""
    keys = sorted(k for k, r in env["reg"].fold().items() if (r.get("filter") or {}).get("verdict") == "trait")
    assert cli.main(["score", "--batch-id", "full", "--keys", *keys, *env["base"]]) == 0


def harness(env, *extra, batch="b"):
    return rt.main(["--hidden-frac", "0.3", "--budget-usd", "2", "--batch-id", batch,
                    "--registry", str(env["reg"].path), "--data-dir", str(env["data"]), "--out-root", str(env["cand_dir"]),
                    "--metric-config", str(env["tmp"] / "metric_config.json"), "--cache-dir", str(env["tmp"] / "cache"),
                    "--regions", str(env["regions"]), "--transport", "live", *extra])


def report(env, batch):
    return json.loads((env["cand_dir"] / "recovery" / batch / "recovery_report.json").read_text())["result"]


def figures(seed):
    k, c = seed["kept"], seed["covered"]
    return {"recall": k["recall"], "recovered": sorted(x["stem"] for x in k["recovered"]),
            "precision": k["candidates"]["precision"], "n_kept": k["candidates"]["n"],
            "false_covers": sorted((r["key"], r["stem"]) for r in c["false_covers"]),
            "by_decision": seed["candidates"]["by_decision"]}


SEEDS = ["--seed", "0", "1", "2", "3"]


class TestAffectedOnly:
    def test_equals_a_full_rescore_for_one_run(self, env):
        score_full(env)
        assert harness(env, "--generator", "toy", "--run-id", "r1", *SEEDS, batch="full_rescore") == 0
        assert harness(env, "--generator", "toy", "--run-id", "r1", *SEEDS, "--affected-only", batch="affected") == 0
        full, aff = report(env, "full_rescore"), report(env, "affected")
        n_copied = 0
        for a, b in zip(full["seeds"], aff["seeds"]):
            assert a["seed"] == b["seed"] and a["hidden_stems"] == b["hidden_stems"]
            assert figures(a) == figures(b), a["seed"]
            n_copied += b["affected"]["n_copied"]
            assert b["affected"]["n_scored"] + b["affected"]["n_copied"] == b["affected"]["n_selected"]
        assert n_copied > 0                                         # the test exercises copying
        # the copied rows are in the reduced run's results, marked, and in affected.jsonl as not scored
        d = env["cand_dir"] / "novelty" / "affected_s0"
        res = cli._read_jsonl(d / "results.jsonl")
        aff_rows = {r["key"]: r for r in cli._read_jsonl(d / "affected.jsonl")}
        for r in res:
            assert bool(r["novelty"].get("copied_from")) == (not aff_rows[r["key"]]["scored"])
            if r["novelty"].get("copied_from"):
                assert r["novelty"]["copied_from"] == "full" and not aff_rows[r["key"]]["reasons"]
        assert not any(x.get("key") in {r["key"] for r in res if r["novelty"].get("copied_from")}
                       for x in cli._read_jsonl(d / "readings.jsonl"))
        summ = json.loads((d / "summary.json").read_text())["result"]
        assert summ["n_copied"] == aff["seeds"][0]["affected"]["n_copied"]
        assert summ["affected_only"]["n_scored"] == aff["seeds"][0]["affected"]["n_scored"]
        md = (env["cand_dir"] / "recovery" / "affected" / "recovery_report.md").read_text()
        assert "## Rows scored again and rows copied (affected only)" in md

    def test_pooled_affected_equals_pooled_full_and_separate_runs(self, env):
        add_second_generator(env)
        score_full(env)
        assert harness(env, "--pooled", *SEEDS, batch="pool_full") == 0
        assert harness(env, "--pooled", *SEEDS, "--affected-only", batch="pool_aff") == 0
        full, aff = report(env, "pool_full"), report(env, "pool_aff")
        for a, b in zip(full["seeds"], aff["seeds"]):
            assert figures(a) == figures(b), a["seed"]
            for part in ("by_generator", "by_run"):
                strip = lambda d: {g: {k: v for k, v in x.items() if k != "n_copied"} for g, x in d.items()}  # noqa
                assert strip(a["breakdown"][part]) == strip(b["breakdown"][part]), (a["seed"], part)
        # the states-pass row counts for toy (its source row's generator), not for states_pass
        assert set(aff["seeds"][0]["breakdown"]["by_generator"]) == {"toy", "toy2"}
        assert set(aff["seeds"][0]["breakdown"]["by_run"]) == {"toy/r1", "toy2/r2"}
        # per generator equals a separate run of the harness on the same draw
        for gen, run in (("toy", "r1"), ("toy2", "r2")):
            assert harness(env, "--generator", gen, "--run-id", run, *SEEDS, batch=f"sep_{gen}") == 0
            sep = report(env, f"sep_{gen}")
            for p, s in zip(full["seeds"], sep["seeds"]):
                g = p["breakdown"]["by_generator"][gen]
                if gen == "toy":
                    continue        # toy's pooled rows include the states-pass row, which --run toy/r1 does not select
                assert (g["recall"], g["n_recovered"], g["precision"], g["false_cover_candidates"], g["n_kept"]) == \
                    (s["kept"]["recall"], s["kept"]["n_recovered"], s["kept"]["candidates"]["precision"],
                     s["covered"]["n_false_cover_candidates"], s["kept"]["candidates"]["n"]), (gen, p["seed"])
        md = (env["cand_dir"] / "recovery" / "pool_aff" / "recovery_report.md").read_text()
        assert "## By generator (pooled)" in md and "| toy2 |" in md and "| toy/r1 |" in md
        run = json.loads((env["cand_dir"] / "recovery" / "pool_aff" / "run.json").read_text())
        assert run["pooled"] and run["affected_only"] and run["pooled_selection"]["counts"]["pooled"] == 16

    def test_pooled_dry_run_prints_the_estimate_and_rows_and_writes_nothing(self, env, capsys):
        add_second_generator(env)
        score_full(env)
        before = env["reg"].path.read_text()
        assert harness(env, "--pooled", *SEEDS, "--affected-only", "--dry-run", batch="pool_dry") == 0
        o = capsys.readouterr().out
        assert "pooled: 16 registry rows" in o and "total estimate = $" in o and "affected only:" in o
        assert "rows by generator" in o and "toy2 | 3 |" in o
        assert not (env["cand_dir"] / "recovery" / "pool_dry").exists() and env["reg"].path.read_text() == before
        assert not list((env["cand_dir"] / "novelty").glob("pool_dry*"))

    def test_refusals(self, env, capsys):
        assert harness(env, "--pooled", "--generator", "toy", batch="x") == 2
        assert "drop --generator" in capsys.readouterr().err
        assert harness(env, batch="x") == 2
        assert "or --pooled" in capsys.readouterr().err
        assert cli.main(["score", "--batch-id", "y", "--run", "toy/r1", "--affected-only", *env["base"]]) == 2
        assert "--affected-only is for a run with --hide" in capsys.readouterr().err
        assert harness(env, "--pooled", "--budget-usd", "0.00001", batch="x") == 2       # the estimate is checked
        assert "exceeds --budget-usd" in capsys.readouterr().err


class TestFixedAndExcluded:
    def test_hidden_file_draws_nothing(self, env):
        hp = env["tmp"] / "fixed.json"
        hp.write_text(json.dumps({"hidden": ["delta", "theta"]}))
        assert harness(env, "--generator", "toy", "--run-id", "r1", "--seed", "0", "--hidden-file", str(hp),
                       batch="fixed") == 0
        doc = json.loads((env["cand_dir"] / "recovery" / "fixed" / "seed0" / "hidden.json").read_text())
        assert doc["hidden_frac"] is None and doc["hidden"] == ["delta", "epsilon", "iota", "theta"]   # pairs whole
        assert doc["requested"] == ["delta", "theta"]
        rep = report(env, "fixed")
        assert rep["hidden_frac"] is None and rep["seeds"][0]["hidden"]["n_hidden"] == 4
        assert harness(env, "--generator", "toy", "--run-id", "r1", "--seed", "0", "1", "--hidden-file", str(hp),
                       batch="fixed2") == 2                                              # one seed only

    def test_exclude_stems(self, env):
        ex = env["tmp"] / "ex.txt"
        ex.write_text("alpha\nzeta\n")
        for s in range(6):
            assert harness(env, "--generator", "toy", "--run-id", "r1", "--seed", str(s), "--exclude-stems", str(ex),
                           "--dry-run", batch=f"ex{s}") == 0
        traits = __import__("assistant_axis.gapgen.novelty", fromlist=["x"]).load_trait_corpus(env["data"])
        kinds = RC.arrangement_kinds(env["data"], traits)
        for s in range(20):
            d = RC.draw_hidden(traits, frac=0.3, seed=s, regions=REGIONS, kinds=kinds, exclude=["alpha", "zeta"])
            assert not {"alpha", "beta", "gamma", "zeta"} & set(d["hidden"])           # alpha's triangle, zeta
            assert d["excluded"] == ["alpha", "zeta"] and ["alpha", "beta", "gamma"] in d["excluded_groups"]

    def test_exclude_provenance_with_nothing_to_exclude(self, env, capsys):
        assert harness(env, "--generator", "toy", "--run-id", "r1", "--seed", "0", "--exclude-provenance", "censuses",
                       "--dry-run", batch="exp") == 0
        assert "no exclusion applies" in capsys.readouterr().out


def test_affected_only_with_nothing_to_score(env):
    """Every selected row unaffected: the run scores nothing, copies every block, and finishes (status 0, none
    stalled), so the harness can read it."""
    score_full(env)
    hp = env["tmp"] / "far.json"
    hp.write_text(json.dumps({"hidden": ["theta", "iota"]}))
    keys = []
    for k in ("alphoid#1", "betaish#1", "deltaish#1", "epsilonic#1", "zetaish#1", "lambdaish#1", "muish#1"):
        d = env["cand_dir"] / "novelty" / f"probe_{k[:-2]}"
        assert cli.main(["score", "--batch-id", d.name, "--keys", k, "--hide", str(hp), "--affected-only",
                         *env["base"]]) == 0
        if not json.loads((d / "affected.jsonl").read_text())["scored"]:
            keys.append(k)
            run = json.loads((d / "run.json").read_text())
            assert run["status"] == 0 and run["n_stalled"] == 0 and run["finished_at"]
            res = cli._read_jsonl(d / "results.jsonl")
            assert len(res) == 1 and res[0]["novelty"]["copied_from"] == "full"
            assert cli._read_jsonl(d / "readings.jsonl") == []
    assert keys                                                     # at least one row was wholly unaffected
