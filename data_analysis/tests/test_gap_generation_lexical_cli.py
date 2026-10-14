"""``lexical_recall.py`` end to end on the M3 toy environment (coding_plan_11_novelty_ensemble.md § 8, "CLI"): every
dry run writes nothing; the sweep's estimate, rendered pair, budget refusal and $20 cost guard; the paid path with a
fake client (records, results, the registry's ``lexical`` blocks beside untouched ``novelty`` blocks, the report, the
marks sheet and its parse, replay); ``--resume`` sends nothing answered; ``setup_external.py --moby --dry-run``.
No API calls and no network: the fake Anthropic client and hash embedder of the M3 CLI tests, a fake lexicon."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import lexical as LX
from assistant_axis.gapgen import lexical_sweep as LS
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests.fake_anthropic import make_response, user_text
from assistant_axis.tests.test_gapgen_lexical import FakeLexicon
from data_analysis.gap_generation import lexical_recall as LR
from data_analysis.gap_generation import novelty_score as NS
from data_analysis.tests.test_gap_generation_novelty_cli import make_env


def tree(d: Path) -> dict:
    return {str(p.relative_to(d)): p.stat().st_mtime_ns for p in sorted(d.rglob("*")) if p.is_file()} if d.exists() else {}


@pytest.fixture
def lenv(tmp_path, monkeypatch):
    env = make_env(tmp_path, monkeypatch)
    assert NS.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"], "--rules", "3"]) == 0
    rows = env["reg"].fold()
    kept = {r["label"]: r for r in rows.values() if (r.get("novelty") or {}).get("decision") in ("new", "grey")}
    assert set(kept) == {"deltaish", "lambdaish"}
    corpus = sorted(p.stem for p in (env["data"] / "traits" / "instructions").glob("*.json"))
    free = {lab: [s for s in corpus if s not in LS.m3_seen(r["novelty"])] for lab, r in kept.items()}
    t1, t2 = free["deltaish"][:2]
    t3 = free["lambdaish"][0]
    lex = FakeLexicon(links={"deltaish": {"synonym": [t1], "also": [t2], "similar": ["queued"]},
                             "lambdaish": {"similar": [t3]}})
    monkeypatch.setattr(LX, "default_lexicons", lambda names, moby_path=None: {"oewn": lex})
    monkeypatch.setattr(LR, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(LR, "platform_dirty_files", lambda *a, **k: [])
    answers = {("deltaish", t1): 4, ("deltaish", t2): 1, ("lambdaish", t3): 3}

    def resp(kw):
        obj = json.loads(user_text(kw))
        v = answers.get((obj["target"]["label"], obj["other"]["label"].replace(" ", "_")), 0)
        return make_response(json.dumps({"reason": "r", "similarity": v}), input_tokens=150, output_tokens=80,
                             cache_read=600)
    env["holder"]["responder"] = resp
    lexdir = env["cand_dir"] / "lexical"
    labelled = env["tmp"] / "labelled_pairs.json"
    labelled.write_text(json.dumps({"result": {"schema_version": 1, "externals": {}, "pairs": [
        {"a": "deltaish", "b": t1, "relation": "duplicate"}, {"a": "alpha", "b": "beta", "relation": "unrelated"}]}}))
    base = ["--data-dir", str(env["data"]), "--registry", str(env["reg"].path), "--out-root", str(env["cand_dir"]),
            "--lookup", str(lexdir / "lookup.json")]
    plan = ["--metric-config", env["base"][env["base"].index("--metric-config") + 1],
            "--cache-dir", env["base"][env["base"].index("--cache-dir") + 1]]
    return env | {"lex": lex, "t": (t1, t2, t3), "lexdir": lexdir, "lbase": base, "plan": plan, "labelled": labelled}


def run(lenv, cmd, *extra):
    plan = lenv["plan"] if cmd in ("dry", "sweep", "reach") else []
    lex = ["--lexicons", "oewn"] if cmd in ("build", "labelled") else []
    return LR.main([cmd, *lenv["lbase"], *plan, *lex, *extra])


def test_every_dry_run_writes_nothing(lenv, capsys):
    reg_before = lenv["reg"].path.read_bytes()
    c0 = lenv["holder"]["client"]                                    # the M3 score run's client
    n0 = len(c0.calls)
    assert run(lenv, "build", "--dry-run") == 0
    assert "oewn coverage: corpus" in capsys.readouterr().out and not lenv["lexdir"].exists()
    assert run(lenv, "labelled", "--labelled", str(lenv["labelled"]), "--dry-run") == 0
    assert not lenv["lexdir"].exists()
    assert run(lenv, "build") == 0                                   # the table, for the rest
    before = tree(lenv["lexdir"])
    assert run(lenv, "dry", "--dry-run") == 0
    assert run(lenv, "dry", "--dry-run", "--batch-id", "lexd") == 0
    assert run(lenv, "dry", "--dry-run", "--lexicons", "oewn") == 0                # a lexicon filter
    out = capsys.readouterr().out
    assert "rows with lexical-only pairs 2" in out and "DRY-RUN" in out
    assert run(lenv, "sweep", "--batch-id", "lexd", "--dry-run") == 0
    out = capsys.readouterr().out
    assert "ASSUMED" in out and "total estimate" in out and "rendered pair (oewn synonym, corpus)" in out
    assert '{"target": {"label": "deltaish"' in out and "overlap_concept v" in out
    assert tree(lenv["lexdir"]) == before and lenv["reg"].path.read_bytes() == reg_before
    assert lenv["holder"]["client"] is c0 and len(c0.calls) == n0         # no client made, no call sent


def test_the_sweep_end_to_end(lenv, capsys):
    t1, t2, t3 = lenv["t"]
    assert run(lenv, "build") == 0
    assert run(lenv, "labelled", "--labelled", str(lenv["labelled"])) == 0
    lab = LR._read_json(lenv["lexdir"] / "labelled_readout.json")
    assert lab["by_lexicon"]["oewn"]["duplicate"]["linked"] == 1
    assert run(lenv, "dry", "--batch-id", "lexd") == 0
    dry = LR._read_json(lenv["lexdir"] / "dry_readout.json")
    assert dry["pairs"]["n_pairs"] == 4 and dry["pairs"]["n_judgeable"] == 3 and dry["pairs"]["name_only_links"] == 1
    assert (lenv["lexdir"] / "dry_readout.md").exists() and (lenv["lexdir"] / "sweep" / "lexd" / "plan.json").exists()
    before = {k: r.get("novelty") for k, r in lenv["reg"].fold().items()}
    capsys.readouterr()
    assert run(lenv, "sweep", "--batch-id", "lex1") == 0
    out = capsys.readouterr().out
    assert "covers at the cut-off: 2 pairs on 2 rows" in out
    d = lenv["lexdir"] / "sweep" / "lex1"
    for name in ("plan.json", "pairs.jsonl", "responses.jsonl", "results.jsonl", "sweep_report.json", "sweep_report.md",
                 "registry_writes.jsonl", "usage.json", "run.json", "run.log"):
        assert (d / name).exists(), name
    assert len(LR._read_jsonl(d / "pairs.jsonl")) == 3
    usage = json.loads((d / "usage.json").read_text())
    assert usage["total_cost_usd"] > 0 and usage["n_calls"] == 5                   # 3 Sonnet, 2 Opus (each at c)
    rep = LR._read_json(d / "sweep_report.json")
    assert rep["stop_rule"]["covers_at_cut_off"] == 2 and rep["n_judged"] == 3 and rep["opus_share_measured"] == round(2 / 3, 4)
    assert rep["parse_rate"]["overlap:claude-sonnet-5-5"]["ok"] == 3
    run_meta = json.loads((d / "run.json").read_text())
    assert run_meta["status"] == 0 and run_meta["n_blocks_written"] == 2 and run_meta["rubrics"]["overlap"]["version"] == 6
    rows = lenv["reg"].fold()
    after = {k: r.get("novelty") for k, r in rows.items()}
    assert after == before                                                          # the novelty blocks untouched
    lex = {r["label"]: r.get("lexical") for r in rows.values() if r.get("lexical")}
    assert set(lex) == {"deltaish", "lambdaish"}
    links = {x["stem"]: x for x in lex["deltaish"]["links"]}
    assert links[t1]["at_cut_off"] and links[t1]["sonnet"]["value"] == 4 and links[t1]["opus"]["value"] == 4
    assert links[t2]["verdict"] == "keep" and links["queued"]["not_judged"] == "name_only"
    assert lex["deltaish"]["flags"] == ["lexical_cover", "lexical_name_only"]
    assert lex["lambdaish"]["links"][0]["opus"]["value"] == 3 and lex["lambdaish"]["flags"] == ["lexical_cover"]
    assert lex["deltaish"]["usage"]["cost_usd"] > 0
    plan = LR._read_json(d / "plan.json")
    for k, snap in plan["rows"].items():
        assert snap["novelty_sha256"] == LS.block_sha256(rows[k]["novelty"])
    # the report, the marks sheet, Roger's marks, the folded report
    sheet = lenv["tmp"] / "marks.md"
    assert run(lenv, "marks", "--batch-id", "lex1", "--sheet", str(sheet)) == 0
    md = sheet.read_text()
    assert "deltaish" in md and "lambdaish" in md and "similarity" not in md
    marked = "\n".join(line.rstrip().rstrip("|").rstrip() + " C |" if line.startswith("| 1 ") or line.startswith("| 2 ")
                       else line for line in md.splitlines())
    sheet.write_text(marked)
    assert run(lenv, "marks", "--batch-id", "lex1", "--parse", str(sheet)) == 0
    mk = json.loads((d / "marks" / "marks.json").read_text())
    assert mk["counts"]["confirmed"] == 2 and mk["counts"]["precision"] == 1.0
    capsys.readouterr()
    assert run(lenv, "report", "--batch-id", "lex1", "--marks", str(d / "marks" / "marks.json")) == 0
    assert "marks: 2 confirmed" in capsys.readouterr().out
    assert LR._read_json(d / "sweep_report.json")["marks"]["confirmed"] == 2
    # replay: nothing to write here; into a registry without the blocks, every one
    capsys.readouterr()
    assert run(lenv, "replay", "--batch-id", "lex1") == 0
    assert "0 to write" in capsys.readouterr().out


def test_resume_sends_nothing_answered(lenv):
    assert run(lenv, "build") == 0
    assert run(lenv, "sweep", "--batch-id", "lex1") == 0
    n_before = len(lenv["holder"]["client"].calls)
    assert n_before == 5
    assert run(lenv, "sweep", "--batch-id", "lex1", "--resume") == 0
    assert lenv["holder"]["client"].calls == []
    lex = {r["label"]: r["lexical"] for r in lenv["reg"].fold().values() if r.get("lexical")}
    assert lex["deltaish"]["usage"]["cost_usd"] > 0                               # the earlier session's spend
    revs = {r["label"]: r["rev"] for r in lenv["reg"].fold().values() if r.get("lexical")}
    d = lenv["lexdir"] / "sweep" / "lex1"
    assert len(LR._read_jsonl(d / "responses.jsonl")) == 5
    assert json.loads((d / "run.json").read_text())["earlier_sessions"]
    assert run(lenv, "sweep", "--batch-id", "lex1") == 1                          # neither --resume nor --overwrite
    assert run(lenv, "sweep", "--batch-id", "lex1", "--resume") == 0
    assert {r["label"]: r["rev"] for r in lenv["reg"].fold().values() if r.get("lexical")} == revs   # not rewritten


def test_budget_refusal_and_the_20_dollar_guard(lenv, monkeypatch, capsys):
    assert run(lenv, "build") == 0
    assert run(lenv, "sweep", "--batch-id", "lexb", "--budget-usd", "0.0001") == 2
    assert "REFUSED (cost gate)" in capsys.readouterr().err
    assert not (lenv["lexdir"] / "sweep" / "lexb").exists()
    real = LS.sweep_plan

    def many(*a, **k):
        items, plans = real(*a, **k)
        one = next(it for it in items if it.judged)
        return [LS.PairItem.from_dict(one.as_dict() | {"stem": f"s{i}"}) for i in range(10_000)], plans
    monkeypatch.setattr(LS, "sweep_plan", many)
    assert run(lenv, "sweep", "--batch-id", "lexg", "--budget-usd", "40") == 2
    err = capsys.readouterr().err
    assert "over the $20 line" in err and "--confirmed-by" in err
    assert not (lenv["lexdir"] / "sweep" / "lexg").exists()


def test_replay_into_another_registry(lenv, tmp_path):
    import shutil
    other = tmp_path / "other_registry.jsonl"
    shutil.copy(lenv["reg"].path, other)
    assert run(lenv, "build") == 0
    assert run(lenv, "sweep", "--batch-id", "lex1", "--no-registry-write") == 0
    assert not any(r.get("lexical") for r in lenv["reg"].fold().values())
    assert LR.main(["replay", *lenv["lbase"][:2], "--registry", str(other), "--out-root", str(lenv["cand_dir"]),
                    "--batch-id", "lex1"]) == 0
    got = {r["label"] for r in Registry(other).fold().values() if r.get("lexical")}
    assert got == {"deltaish", "lambdaish"}


def test_setup_external_moby_dry_run_fetches_nothing(monkeypatch, capsys):
    from assistant_axis.gapgen.generators.ipip import download as D
    from data_analysis.gap_generation import setup_external as SE

    def boom(*a, **k):
        raise AssertionError("no network in a dry run")
    monkeypatch.setattr(D, "_urlopen_bytes", boom)
    before = (LX.MOBY_DIR / LX.MOBY_FILE).exists()
    assert SE.main(["--moby", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert LX.MOBY_URL in out and "DRY-RUN: nothing fetched" in out and "mthesaur.txt" in out
    assert (LX.MOBY_DIR / LX.MOBY_FILE).exists() == before


def test_setup_external_moby_refuses_a_target_outside_the_repository(tmp_path, capsys):
    from data_analysis.gap_generation import setup_external as SE

    def boom(url):
        raise AssertionError("nothing is fetched for a target outside the repository")
    rc = SE.fetch_moby(fetcher=boom, dest_dir=tmp_path / "moby", sources_manifest_path=tmp_path / "sources_manifest.json")
    assert rc == 1 and "REFUSED" in capsys.readouterr().err and not (tmp_path / "moby").exists()


# --------------------------------------------------------------------------- the forward path and task 8

def test_from_batches_sweeps_one_wave_flag_only(lenv, capsys):
    """The forward path for a new M3 wave (Roger, 2026-10-14, option (d): every lexical link only flags): ``dry`` and
    ``sweep`` restricted to the kept rows one M3 batch decided; an unknown batch is refused; the novelty blocks
    stay byte-identical (the M3 decisions never change)."""
    assert run(lenv, "build") == 0
    capsys.readouterr()
    assert run(lenv, "dry", "--dry-run", "--from-batches", "no_such_wave") == 2
    assert "REFUSED" in capsys.readouterr().err
    assert run(lenv, "sweep", "--batch-id", "lexw", "--from-batches", "no_such_wave") == 2
    assert not (lenv["lexdir"] / "sweep" / "lexw").exists()
    assert run(lenv, "dry", "--dry-run", "--from-batches", "m3t") == 0
    assert "kept rows 2; rows with lexical-only pairs 2" in capsys.readouterr().out
    before = {k: LS.block_sha256(r.get("novelty")) for k, r in lenv["reg"].fold().items()}
    assert run(lenv, "sweep", "--batch-id", "lexw", "--from-batches", "m3t") == 0
    d = lenv["lexdir"] / "sweep" / "lexw"
    meta = json.loads((d / "run.json").read_text())
    assert meta["from_batches"] == ["m3t"] and meta["n_rows"] == 2 and meta["n_blocks_written"] == 2
    rows = lenv["reg"].fold()
    assert {k: LS.block_sha256(r.get("novelty")) for k, r in rows.items()} == before
    assert {r["label"]: r["lexical"]["flags"] for r in rows.values() if r.get("lexical")} == \
        {"deltaish": ["lexical_cover", "lexical_name_only"], "lambdaish": ["lexical_cover"]}


def test_reach_counts_the_unrecovered_hidden_traits_a_lexical_link_reaches(lenv, capsys):
    """Task 8, dry ($0): over a recovery run's hidden set, the hidden traits no kept candidate recovered that a kept
    candidate's lexical link reaches, by lexicon, and whether the harness already read that pair."""
    t1, t2, t3 = lenv["t"]
    assert run(lenv, "build") == 0
    rec = lenv["cand_dir"] / "recovery" / "rec_t"
    (rec / "seed0").mkdir(parents=True)
    (rec / "run.json").write_text(json.dumps({"seeds": [0], "m3_runs": {"0": "m3t"}}))
    (rec / "seed0" / "hidden.json").write_text(json.dumps({"hidden": [t1, t2, t3, "zzz_hidden"]}))
    rows = {r["label"]: r for r in lenv["reg"].fold().values()}
    (rec / "seed0" / "matches.jsonl").write_text("".join(json.dumps(m) + "\n" for m in [
        {"key": rows["lambdaish"]["key"], "decision": "new", "stem": t3, "how": "overlap", "recovers": True},
        {"key": rows["deltaish"]["key"], "decision": "new", "stem": t2, "how": "overlap", "recovers": False}]))
    capsys.readouterr()
    assert run(lenv, "reach", "--recovery-batch", "rec_t", "--dry-run") == 0
    assert "unrecovered hidden traits a lexical link reaches: 2 of 3" in capsys.readouterr().out
    assert not (rec / "lexical_reach.json").exists()
    assert run(lenv, "reach", "--recovery-batch", "rec_t") == 0
    doc = LR._read_json(rec / "lexical_reach.json")
    s = doc["seeds"][0]
    assert s["n_hidden"] == 4 and s["n_recovered_by_kept"] == 1 and s["n_unrecovered"] == 3 and s["n_kept"] == 2
    assert s["reached"]["n"] == 2 and s["reached"]["by_lexicon"] == {"oewn": 2}
    assert s["reached"]["never_read"] == 1 and s["reached"]["read_below_cut"] == 1
    assert s["reached"]["judged_and_never_read"] == 1 and s["reached"]["would_be_judged"] == 2
    by = {x["stem"]: x for x in s["reached"]["traits"]}
    assert by[t1]["by"][0]["key"] == rows["deltaish"]["key"] and by[t1]["by"][0]["read_by_harness"] is False
    assert by[t2]["by"][0]["read_by_harness"] is True and s["unreached"] == ["zzz_hidden"]


def test_a_resumed_sweep_keeps_the_earlier_from_batches(tmp_path):
    """Review S1 (2026-10-15): a resume without --from-batches takes the earlier session's; a different one refuses."""
    import argparse
    import json as _json
    from data_analysis.gap_generation import lexical_recall as LR
    args = argparse.Namespace(out_root=tmp_path, batch_id="w5_lex", resume=True, from_batches=None)
    d = LR.sweep_dir(args)
    d.mkdir(parents=True)
    (d / "run.json").write_text(_json.dumps({"from_batches": ["wave5"]}))
    assert LR._resume_from_batches(args) is None and args.from_batches == ["wave5"]
    args2 = argparse.Namespace(out_root=tmp_path, batch_id="w5_lex", resume=True, from_batches=["wave6"])
    assert "differs" in LR._resume_from_batches(args2)
    fresh = argparse.Namespace(out_root=tmp_path, batch_id="w5_lex", resume=False, from_batches=None)
    assert LR._resume_from_batches(fresh) is None and fresh.from_batches is None
