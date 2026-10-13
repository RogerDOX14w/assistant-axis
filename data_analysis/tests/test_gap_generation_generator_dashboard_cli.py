"""``generator_dashboard.py`` end to end on a small fixture (plan 13 § 8, "CLI"): every subcommand's ``--dry-run``
exits 0 and writes nothing; the outputs carry the provenance envelope and the graph's path; ``paraphrase-set run``
refuses an estimate over its budget and sends nothing.  No API calls."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.tests.test_gapgen_novelty import write_corpus
from data_analysis.gap_generation import generator_dashboard as GD

REPO = Path(__file__).resolve().parents[2]
SURFACES = [("alphaish", "gen1", "r1", "new"), ("betaish", "gen1", "r1", "new"), ("gammaish", "gen2", "r2", "new"),
            ("deltaish", "gen2", "r2", "covered"), ("alpha", "gen2", "r2", "covered")]


@pytest.fixture
def env(tmp_path):
    data = write_corpus(tmp_path / "data")
    (data / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "meek", "label": "meek", "status": "not_adopted", "entity_type": "trait"}]}))
    regions = tmp_path / "regions.json"
    regions.write_text(json.dumps({"result": {"alpha": {"region": "moral_stance"}}}))
    cd = tmp_path / "candidates"
    reg = cd / "registry.jsonl"
    rep = submit_candidates([Candidate(surface=s, generator=g, run_id=r) for s, g, r, _ in SURFACES], registry_path=reg)
    Registry(reg).update_many({k: {"filter": {"verdict": "trait", "region": "moral_stance"}, "gloss": "g",
                                   "novelty": {"decision": d, "run_id": "m3", "covered_by": "alpha" if d == "covered"
                                               else None}}
                               for k, (_, _, _, d) in zip(rep.keys, SURFACES)})
    for g, r in (("gen1", "r1"), ("gen2", "r2")):
        d = cd / "runs" / g / r
        d.mkdir(parents=True)
        (d / "usage.json").write_text(json.dumps({"total_cost_usd": 0.5}))
        (d / "candidates.jsonl").write_text("".join(json.dumps({"surface": s, "generator": g, "run_id": r, "rank": i})
                                                    + "\n" for i, (s, gg, rr, _) in enumerate(SURFACES) if gg == g))
    rv = cd / "review" / "review_all"
    rv.mkdir(parents=True)
    nodes = [{"key": k, "kind": "candidate", "decision": d, "generators": [g], "generator": g, "label": s,
              "region": "moral_stance", "m3_run": "m3"} for k, (s, g, _, d) in zip(rep.keys, SURFACES)]
    graph = {"result": {"batch_id": "review_all", "nodes": nodes, "proposed_groups": [[rep.keys[0], rep.keys[1]]],
                        "edges": [{"a": rep.keys[0], "b": rep.keys[1], "strict": True, "proposed": True},
                                  {"a": rep.keys[1], "b": rep.keys[2], "strict": False, "proposed": True}]}}
    (rv / "graph.json").write_text(json.dumps(graph))
    (rv / "run.json").write_text(json.dumps({"from_batches": ["m3"]}))
    (rv / "usage.json").write_text(json.dumps({"total_cost_usd": 1.0}))
    (rv / "decisions.jsonl").write_text("".join(json.dumps(e) + "\n" for e in [
        {"seq": 1, "at": "2026-10-11T10:00:00+00:00", "group": "g1", "action": "open", "members": rep.keys[:2]},
        {"seq": 2, "at": "2026-10-11T10:01:00+00:00", "group": "g1", "action": "resolve", "members": rep.keys[:2],
         "resolution": "promote"}]))
    out = tmp_path / "testing"
    base = ["--registry", str(reg), "--data-dir", str(data), "--regions", str(regions), "--review-root",
            str(cd / "review"), "--recovery-root", str(cd / "recovery"), "--candidates-dir", str(cd), "--out", str(out)]
    return {"base": base, "out": out, "cd": cd, "tmp": tmp_path}


def files(d: Path) -> set:
    return {p.relative_to(d) for p in d.rglob("*")} if d.exists() else set()


@pytest.mark.parametrize("cmd", [["independence"], ["review-rate"], ["repetition"], ["concepts"], ["estimate"],
                                 ["simulate", "--replicates", "5", "--n", "200"], ["dashboard"]])
def test_dry_runs_write_nothing(env, cmd):
    before = files(env["tmp"])
    assert GD.main([*cmd, *env["base"], "--dry-run"]) == 0
    assert files(env["tmp"]) == before


def test_the_dashboard_writes_enveloped_outputs(env, capsys):
    assert GD.main(["dashboard", *env["base"]]) == 0
    o = capsys.readouterr().out
    assert "Assumptions of every estimate" in o                       # printed every time
    for name in ("independence", "review_rates", "repetition", "concepts", "estimates", "dashboard"):
        doc = json.loads((env["out"] / f"{name}.json").read_text())
        assert set(doc) == {"result", "_provenance"}, name
    dash = json.loads((env["out"] / "dashboard.json").read_text())
    assert dash["result"]["inputs"]["graph"].endswith("review_all/graph.json")
    assert {r["generator"] for r in dash["result"]["rows"]} == {"gen1", "gen2"}
    assert any(i["dep_key"] == "graph" for i in dash["_provenance"]["inputs"])
    md = (env["out"] / "dashboard.md").read_text()
    assert "| gen1 |" in md and "| gen2 |" in md
    # a second run with nothing changed keeps no backup; a changed result keeps the old file
    assert GD.main(["dashboard", *env["base"]]) == 0
    assert not list(env["out"].glob("*.bak.*"))


def test_independence_check(env, capsys):
    assert GD.main(["independence", *env["base"], "--check"]) == 1      # gen1, gen2 have no stream rule
    assert "MISSING: no stream rule for gen1/gen1" in capsys.readouterr().err


def test_recovery_extras_refuses_a_missing_batch(env, capsys):
    assert GD.main(["recovery-extras", "--batch", "nope", *env["base"]]) == 2


def test_paraphrase_set_build_dry_run_and_run_refusal(env, capsys, monkeypatch):
    """On the real corpus and calibration paraphrases (read only): the build's dry run writes nothing; a built set
    in a scratch directory; ``run`` with a budget below the estimate is refused before any call."""
    sd = env["tmp"] / "pset"
    real = ["--data-dir", str(REPO / "data"), "--regions", str(REPO / "data" / "candidates" / "corpus_regions.json"),
            "--set-dir", str(sd)]
    assert GD.main(["paraphrase-set", "build", *real, "--dry-run"]) == 0
    assert not sd.exists()
    assert "80 items" in capsys.readouterr().out
    assert GD.main(["paraphrase-set", "build", *real]) == 0
    assert (sd / "set.jsonl").exists() and (sd / "hidden.json").exists()
    import anthropic
    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda *a, **k: pytest.fail("no client may be built"))
    assert GD.main(["paraphrase-set", "run", *real, "--budget-usd", "0.00001"]) == 2
    assert "exceeds --budget-usd" in capsys.readouterr().err
    assert not (sd / "responses.jsonl").exists()
