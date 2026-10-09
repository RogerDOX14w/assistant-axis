"""``novelty_score.py score --holding physical`` end to end on the toy corpus (the physical pass, QUESTIONS 1): the
gloss stage (M1's gloss and alignment calls on the accepted reading), then M3 as for trait rows, the pass recorded in
every block, ``run.json`` and ``summary.json``; a trait run is unchanged and leaves the physical rows alone.  No API
calls: the novelty CLI tests' fake client and hash embedder."""
import json

import pytest

from assistant_axis.gapgen import physical_pass as PP
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.tests.fake_anthropic import make_response, system_text, user_text
from data_analysis.gap_generation import novelty_score as cli
from data_analysis.tests.test_gap_generation_novelty_cli import OVERLAP, RELATIONS, ROWS, make_env, out

#: (surface, accepted reading): ``beta`` is a corpus label (covered at the exact-label stage), ``alphoform`` reads
#: like the trait ``alpha`` (covered by it), ``brawny`` like nothing (new).
PHYSICAL = [("beta", "has a beta build"), ("alphoform", "alpha alpha beta in every way"),
            ("brawny", "has big strong muscles")]


@pytest.fixture
def env(tmp_path, monkeypatch):
    rows = ROWS + [(s, None, "tagged", None, "physical") for s, _ in PHYSICAL]
    e = make_env(tmp_path, monkeypatch, rows=rows,
                 relations={**RELATIONS, ("alphoform", "alpha"): "similar"},
                 overlap={**OVERLAP, ("alphoform", "alpha"): 4})
    e["reg"].update_many({f"{s}#1": {"filter": {"outcome": "physical", "tags": ["physical"], "judged_sense": r,
                                                "alignment": None, "region": None}} for s, r in PHYSICAL})
    e["gloss_calls"] = []
    base = e["holder"]["responder"]
    gloss_sys, align_sys = sr.load_prompt("gloss"), sr.load_prompt("alignment")

    def responder(kw):
        s = system_text(kw)
        if s == gloss_sys:
            obj = json.loads(user_text(kw))
            e["gloss_calls"].append(obj["label"])
            return make_response(json.dumps({"results": [{"id": 1, "gloss": f"This means having {obj['reading']}."}]}),
                                 input_tokens=650, output_tokens=90)
        if s == align_sys:
            return make_response(json.dumps({"results": [{"id": 1, "reason": "A body.", "alignment": 0}]}),
                                 input_tokens=780, output_tokens=170)
        return base(kw)
    e["holder"]["responder"] = responder
    return e


def phys(env, *extra, batch="phys1"):
    return cli.main(["score", "--batch-id", batch, "--holding", "physical", *env["base"], *extra])


def test_dry_run_plans_the_gloss_stage_and_writes_nothing(env, capsys):
    before = env["reg"].path.read_text()
    assert phys(env, "--run", "toy/r1", "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"n_candidates": 3' in o and '"holding": "physical"' in o and '"n_to_gloss": 3' in o
    assert "[physical_gloss]" in o and "M1's gloss call: 3 x" in o and "M1's alignment call: 3 x" in o
    assert "=== physical gloss stage, alphoform#1: gloss v" in o and '"reading": "alpha alpha beta in every way"' in o
    assert '"not_on_physical_list": 7' in o                                      # the run's other rows
    assert not out(env, "phys1").exists() and env["reg"].path.read_text() == before and env["gloss_calls"] == []


def test_end_to_end_glosses_scores_and_records_the_pass(env):
    assert phys(env, "--run", "toy/r1") == 0
    rows = env["reg"].fold()
    assert sorted(env["gloss_calls"]) == ["alphoform", "beta", "brawny"]
    for s, reading in PHYSICAL:
        r = rows[f"{s}#1"]
        b = r[PP.BLOCK]
        assert b["gloss"] == f"This means having {reading}." and b["alignment"] == 0 and b["batch_id"] == "phys1"
        assert r["gloss"] is None and r["filter"]["verdict"] == "tagged"            # M1's own fields untouched
        nv = r["novelty"]
        assert nv["pass"] == "physical" and nv["run_id"] == "phys1" and nv["cut_off"] == 3
    nv = {s: rows[f"{s}#1"]["novelty"] for s, _ in PHYSICAL}
    assert nv["beta"]["decision"] == "covered" and nv["beta"]["reason"] == "exact_label"
    assert nv["alphoform"]["decision"] == "covered" and nv["alphoform"]["covered_by"] == "alpha"
    assert nv["brawny"]["decision"] == "new"
    # the trait rows are not this pass's
    assert all(r.get("novelty") is None for k, r in rows.items() if r.get("holding") != "physical")
    d = out(env, "phys1")
    run = json.loads((d / "run.json").read_text())
    assert run["pass"] == "physical" and run["plan"]["holding"] == "physical" and run["status"] == 0
    assert run["physical_gloss"]["n_glossed"] == 3 and run["physical_gloss"]["alignment"] == {"0": 3}
    assert json.loads((d / "summary.json").read_text())["result"]["pass"] == "physical"
    res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
    assert {r["key"] for r in res} == {"beta#1", "alphoform#1", "brawny#1"}
    assert {r["key"]: r["gloss"] for r in res}["brawny#1"] == "This means having has big strong muscles."
    gl = [json.loads(x) for x in (d / PP.RESULTS_NAME).read_text().splitlines()]
    assert {x["key"] for x in gl} == {"beta#1", "alphoform#1", "brawny#1"} and all(PP.BLOCK in x for x in gl)
    recs = [json.loads(x) for x in (d / PP.RESPONSES_NAME).read_text().splitlines()]
    assert len(recs) == 6 and {x["step"] for x in recs} == {"gloss", "alignment"}
    assert (d / "decisions.md").read_text().startswith("# M3 decisions: `phys1` (physical pass)")
    usage = json.loads((d / "usage.json").read_text())
    assert usage["per_model"]["claude-haiku-5-5"]["n_calls"] >= 6                # the gloss stage is charged


def test_a_trait_run_leaves_the_physical_rows_alone_and_writes_no_pass(env, capsys):
    assert cli.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"], "--dry-run"]) == 0
    assert '"not_a_trait": 4' in capsys.readouterr().out                         # the three physical and the reject
    assert cli.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"]]) == 0
    rows = env["reg"].fold()
    assert all(rows[f"{s}#1"].get("novelty") is None and PP.BLOCK not in rows[f"{s}#1"] for s, _ in PHYSICAL)
    assert all("pass" not in r["novelty"] for r in rows.values() if r.get("novelty"))
    run = json.loads((out(env, "m3t") / "run.json").read_text())
    assert "pass" not in run and "holding" not in run["plan"] and env["gloss_calls"] == []
    assert not (out(env, "m3t") / PP.RESPONSES_NAME).exists()


def test_a_row_glossed_before_is_not_glossed_again(env):
    assert phys(env, "--keys", "brawny#1") == 0
    assert env["gloss_calls"] == ["brawny"]
    block = env["reg"].fold()["brawny#1"][PP.BLOCK]
    assert phys(env, "--keys", "brawny#1", "--rescore", batch="phys2") == 0
    assert env["gloss_calls"] == ["brawny"]                                       # no second gloss call
    r = env["reg"].fold()["brawny#1"]
    assert r[PP.BLOCK] == block and r["novelty"]["run_id"] == "phys2" and r["novelty"]["pass"] == "physical"
    assert json.loads((out(env, "phys2") / "run.json").read_text())["physical_gloss"]["n_rows"] == 0


def test_a_failed_gloss_skips_the_row(env):
    good = env["holder"]["responder"]
    gloss_sys = sr.load_prompt("gloss")

    def bad(kw):
        if system_text(kw) == gloss_sys and json.loads(user_text(kw))["label"] == "brawny":
            return make_response("no", input_tokens=600, output_tokens=5)
        return good(kw)
    env["holder"]["responder"] = bad
    assert phys(env, "--run", "toy/r1") == 0
    rows = env["reg"].fold()
    assert PP.BLOCK not in rows["brawny#1"] and rows["brawny#1"].get("novelty") is None
    summary = json.loads((out(env, "phys1") / "summary.json").read_text())["result"]
    assert summary["skipped"]["physical_gloss_failed"] == 1 and summary["n_decided"] == 2
    run = json.loads((out(env, "phys1") / "run.json").read_text())
    assert run["physical_gloss"]["n_gloss_failed"] == 1


def test_a_resume_of_another_pass_is_refused(env, capsys):
    assert cli.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"]]) == 0
    assert phys(env, "--run", "toy/r1", "--resume", batch="m3t") == 2
    assert "separate batch id per pass" in capsys.readouterr().err
    assert phys(env, "--run", "toy/r1") == 0
    assert cli.main(["score", "--batch-id", "phys1", "--run", "toy/r1", *env["base"], "--resume", "--rescore"]) == 2
    assert "separate batch id per pass" in capsys.readouterr().err


def test_holding_is_refused_where_the_source_run_decides(env, capsys):
    assert phys(env, "--redecide", "--from-batch", "x") == 2
    assert "--holding" in capsys.readouterr().err
    assert phys(env, "--relation-only", "--from-batch", "x") == 2
    assert "--holding" in capsys.readouterr().err
    hidden = env["tmp"] / "hidden.json"
    hidden.write_text(json.dumps({"hidden": ["gamma"]}))
    assert phys(env, "--run", "toy/r1", "--hide", str(hidden)) == 2
    assert "--holding" in capsys.readouterr().err


def test_embed_only_is_refused_while_rows_wait_for_a_gloss(env, capsys):
    assert phys(env, "--run", "toy/r1", "--embed-only") == 2
    assert "gloss stage" in capsys.readouterr().err and not out(env, "phys1").exists()


def test_a_physical_batch_re_decides_on_its_own_records(env, capsys):
    assert phys(env, "--run", "toy/r1") == 0
    capsys.readouterr()
    assert cli.main(["score", "--redecide", "--from-batch", "phys1", "--batch-id", "phys1_r", "--corpus-at", "current",
                     "--dry-run", *env["base"]]) == 0
    o = capsys.readouterr().out
    assert "identical [OK]" in o and "calls not on record (sent live by the run): 0" in o


def test_gap_registry_promotes_a_physical_row_by_key_but_not_by_status(env, capsys):
    from data_analysis.gap_generation import gap_registry
    assert phys(env, "--run", "toy/r1") == 0
    env["reg"].update_many({"brawny#1": {"review": {"status": "accepted"}}, "alphoid#1": {"review": {"status": "accepted"}}})
    q = env["data"] / "seed_queue.json"                                            # the toy queue, under tmp_path
    base = ["--registry", str(env["reg"].path), "--data-dir", str(env["data"]), "promote", "--queue", str(q)]
    capsys.readouterr()
    assert gap_registry.main([*base, "--status", "accepted", "--dry-run"]) == 0
    o = capsys.readouterr().out
    assert "REFUSED brawny#1: on the physical holding list" in o and "WOULD PROMOTE alphoid#1" in o
    before = q.read_text()
    assert gap_registry.main([*base, "--keys", "brawny#1"]) == 0
    assert "PROMOTED brawny#1 -> brawny" in capsys.readouterr().out and q.read_text() != before
    e = json.loads(q.read_text())["entries"][-1]
    assert e["stem"] == "brawny" and "physical" in e["tags"] and e["section"] == PP.SECTION
    assert e["description_draft"] == "This means having has big strong muscles."
    assert env["reg"].fold()["brawny#1"]["seed_queue_stem"] == "brawny"


def test_r1_and_the_review_app_take_a_physical_batch(env, monkeypatch, capsys):
    """M3's physical pass, then R1 on its batch (unchanged but for the node's outcome), then the review app: the card
    shows the tag, and apply promotes the nominee into the physical track (on the toy queue under tmp_path)."""
    from assistant_axis.gapgen import review_graph as RG
    from assistant_axis.gapgen.review_app import decisions as D
    from data_analysis.gap_generation import review_graph as r1
    assert phys(env, "--run", "toy/r1") == 0
    monkeypatch.setattr(r1, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(r1, "platform_dirty_files", lambda *a, **k: [])
    assert r1.main(["build", "--batch-id", "rv_phys", "--from-batches", "phys1", "--budget-usd", "1",
                    *env["base"]]) == 0
    rdir = env["cand_dir"] / "review" / "rv_phys"
    g = RG.Graph.from_json(json.loads((rdir / "graph.json").read_text()))
    nodes = g.node_map()
    assert g.complete and g.candidate_keys() == ["brawny#1"]
    assert nodes["brawny#1"].outcome == "physical" and nodes["brawny#1"].gloss == "This means having has big strong muscles."
    assert nodes["alphoform#1"].decision == "covered" and nodes["alphoform#1"].covered_by == "trait:alpha"
    assert nodes["beta#1"].outcome == "physical"
    log = D.DecisionLog.open(rdir, by="roger", data_dir=env["data"])
    assert "physical" in log.state.member_card("brawny#1")["tags"]
    gid, = [log.act({"action": "open", "source": "term:brawny#1"})[1]]
    log.act({"action": "resolve", "group": gid, "resolution": "promote"})
    q = env["data"] / "seed_queue.json"
    rep = D.apply_decisions(log.state, batch_id="rv_phys", registry=env["reg"], queue_path=q, data_dir=env["data"],
                            review_dir=rdir, by="roger")
    assert [p["key"] for p in rep.promotions] == ["brawny#1"] and rep.refused == {}
    e = json.loads(q.read_text())["entries"][-1]
    assert e["stem"] == "brawny" and "physical" in e["tags"] and e["section"] == PP.SECTION and e["also_proposed"] == []
    assert env["reg"].fold()["brawny#1"]["review"]["status"] == "accepted"
