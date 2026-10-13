"""The structural generators' CLI (``structural_generator.py``; coding_plan_09 section 8, CLI): every subcommand's dry
run writes nothing; paid commands refuse over budget, on an unverified VIA scheme and on uncommitted platform code;
and the pipeline operators -> null-rate -> stability -> postprocess -> side-table -> submit -> report runs end to end
on a scripted Anthropic client, a toy corpus and a tmp registry.  No network, no model."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.structural import operators as O
from assistant_axis.gapgen.generators.structural import prompts as P
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import structural_fakes as F
from data_analysis.gap_generation import structural_generator as CLI

SYSTEM = P.operator_system()


def _answers(stem: str, principal: bool) -> str:
    if stem == "brave":
        return F.reply("mean", opposite=F.item("timid"), excess=F.item("foolhardy"), deficiency=F.item("craven"),
                       retarget={"self": F.item("hard on oneself", common=False)})
    if stem == "gloomy":
        return F.reply("excess", opposite=F.item("sunny"), deficiency=F.item("giddy"),
                       remode={"speech": F.item("doom-saying", common=False)})
    if stem == "obedient":
        return F.reply("excess", principal=True, opposite=F.item("rebellious"),
                       retarget={"the_user": F.item("user-deferring", common=False)})
    return F.reply("mean", principal=principal, opposite=F.item(f"anti-{stem.replace('_', '-')}"))


def _unverified_classical(tmp_path):
    """The real classical tables copied with VIA's `verified_by` cleared, so these tests exercise the VIA gate whatever
    the repository's table holds (VIA was verified 2026-10-13, 938bd617)."""
    import shutil
    from assistant_axis.gapgen.generators import structural as S
    cdir = tmp_path / "classical"
    shutil.copytree(S.CLASSICAL_DIR, cdir)
    via = cdir / "via.json"
    rows = json.loads(via.read_text())
    for r in rows:
        r["verified_by"] = None
    via.write_text(json.dumps(rows, indent=2) + "\n")
    return cdir



@pytest.fixture()
def env(tmp_path, monkeypatch):
    data = F.write_corpus(tmp_path)
    reg = F.write_registry(tmp_path / "candidates" / "registry.jsonl", [
        F.registry_row("foolhardy", "base_model", verdict="trait", decision="new"),
        F.registry_row("craven", "censuses")])
    sdir = tmp_path / "candidates" / "structural"
    cdir = _unverified_classical(tmp_path)
    base = ["--classical-dir", str(cdir), "--data-dir", str(data), "--registry", str(reg), "--candidates-dir", str(tmp_path / "candidates"),
            "--regions", str(data / "candidates" / "corpus_regions.json"), "--queue", str(data / "seed_queue.json"),
            "--structural-dir", str(sdir), "--classical-modern", str(sdir / "classical_modern.jsonl"),
            "--operator-table", str(sdir / "operator_table.jsonl"),
            "--position-table", str(sdir / "position_table.jsonl"),
            "--mismatches", str(sdir / "negative_label_mismatches.md")]
    ins = O.build_inputs(None, data_dir=data, regions_path=data / "candidates" / "corpus_regions.json")
    script = F.script_for(ins, SYSTEM, {t.stem: _answers(t.stem, t.principal_targets) for t in ins})
    client = F.ScriptedClient(script)
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: client)
    monkeypatch.setattr(CLI, "_dirty", lambda args: None)
    monkeypatch.setattr(CLI, "_lexicon", lambda args: F.LEXICON)
    return {"tmp": tmp_path, "data": data, "reg": reg, "sdir": sdir, "base": base, "client": client}


def _snapshot(root: Path) -> dict:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


DRY_RUNS = [
    ["classical"],
    ["modernise", "--run-id", "m1", "--dry-run"],
    ["operators", "--run-id", "o1", "--all", "--dry-run"],
    ["operators", "--run-id", "o1", "--traits", "brave", "obedient", "--dry-run"],
    ["operators", "--run-id", "o1", "--sample", "5", "--seed", "0", "--dry-run"],
    ["operators", "--run-id", "o1", "--all", "--principal-min-score", "2", "--principal-only", "--dry-run"],
    ["operators", "--run-id", "o1", "--render", "brave", "careful_hexaco"],
    ["null-rate", "--run-id", "n1", "--n", "6", "--dry-run"],
    ["stability", "--run-id", "s1", "--against", "s2", "--n", "4", "--dry-run"],
    ["postprocess", "--embedder", "hash", "--dry-run"],
    ["side-table", "--dry-run"],
]


@pytest.mark.parametrize("argv", DRY_RUNS, ids=lambda a: " ".join(a[:2]))
def test_every_dry_run_exits_0_and_writes_nothing(env, argv, capsys):
    before = _snapshot(env["tmp"])
    assert CLI.main(env["base"] + argv) == 0
    assert _snapshot(env["tmp"]) == before
    assert env["client"].calls == []
    out = capsys.readouterr().out
    if "operators" in argv and "--render" not in argv and "--principal-only" not in argv:
        assert "a singleton" in out and "a pair pole" in out and "a principal-target trait" in out
        assert "claude-haiku-5-5 rates = $" in out          # the model actually used (review B3)


def test_modernise_dry_run_renders_a_classical_batch(env, capsys):
    assert CLI.main(env["base"] + ["modernise", "--run-id", "m1", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "via left out (unverified: the gate)" in out and '"rows": [' in out and "aristotle:courage:mean" in out


def test_modernise_refuses_an_unverified_via(env, capsys):
    assert CLI.main(env["base"] + ["modernise", "--run-id", "m1", "--scheme", "via", "--dry-run"]) == 2
    assert "verified_by null" in capsys.readouterr().err
    assert CLI.main(env["base"] + ["classical", "--scheme", "via"]) == 2


def test_paid_commands_refuse_over_budget(env):
    for argv in (["operators", "--run-id", "o1", "--all", "--budget-usd", "0.0001"],
                 ["null-rate", "--run-id", "n1", "--budget-usd", "0.0001"],
                 ["modernise", "--run-id", "m1", "--budget-usd", "0.0001"],
                 ["stability", "--run-id", "s1", "--against", "s2", "--budget-usd", "0.0001"]):
        with pytest.raises(SystemExit) as e:
            CLI.main(env["base"] + argv)
        assert e.value.code == 2, argv
    assert env["client"].calls == []


def test_paid_commands_refuse_uncommitted_platform_code(env, monkeypatch):
    monkeypatch.setattr(CLI, "_dirty", lambda args: "uncommitted changes (test)")
    with pytest.raises(SystemExit, match="REFUSED: uncommitted"):
        CLI.main(env["base"] + ["operators", "--run-id", "o1", "--traits", "brave"])
    assert env["client"].calls == []


def test_end_to_end(env, capsys):
    b = env["base"]
    # the null-rate pilot freezes the hold-out lists first, then answers its sample
    rc = CLI.main(b + ["null-rate", "--run-id", "n1", "--n", "6", "--seed", "0"])
    assert rc in (0, CLI.EXIT_GATE)
    ev = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]
    assert ev["holdout_lists"]["counts"] == {"holdout": 2, "rejected": 1, "accepted": 0, "candidates": 1}
    readout = json.loads((env["tmp"] / "candidates" / "runs" / "structural" / "n1" / "nullrate_readout.json").read_text())
    assert readout["n"] == 6 and readout["parse_rate"]["rate"] == 1.0
    # the full pass, then a second identical command sends nothing (answers reused by prompt hash)
    assert CLI.main(b + ["operators", "--run-id", "o1", "--all"]) == 0
    n = len(env["client"].calls)
    assert CLI.main(b + ["operators", "--run-id", "o1", "--all"]) == 0
    assert len(env["client"].calls) == n
    rdir = env["tmp"] / "candidates" / "runs" / "structural" / "o1"
    assert (rdir / "responses.jsonl").exists() and json.loads((rdir / "usage.json").read_text())["n_calls"] > 0
    # stability: o1 is reused, s2 answered fresh; identical scripted answers give a median of 1.0
    assert CLI.main(b + ["stability", "--run-id", "o1", "--against", "s2", "--n", "4", "--seed", "1"]) == 0
    st = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]["stability"]
    assert st["jaccard_median"] == 1.0 and st["n_traits"] == 4
    # postprocess and the side table, free; a rerun leaves the table byte-identical
    assert CLI.main(b + ["postprocess", "--run-id", "o1", "--embedder", "hash"]) == 0
    table = [json.loads(x) for x in (env["sdir"] / "operator_table.jsonl").read_text().splitlines()]
    first = (env["sdir"] / "operator_table.jsonl").read_bytes()
    assert CLI.main(b + ["postprocess", "--run-id", "o1", "--embedder", "hash"]) == 0
    assert (env["sdir"] / "operator_table.jsonl").read_bytes() == first
    by = {r["stem"]: r for r in table}
    assert by["foolhardy"]["registered_decided"] and by["craven"]["registered"] and by["craven"]["net_new"]
    assert by["user_deferring"]["principal_target"] and by["timid"]["exists"]
    ev = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]
    assert ev["pair_recovery"]["n_pairs"] >= 4 and "recall_cos_0.8" in ev["pair_recovery"]
    assert ev["principal"]["n_items"] == ev["principal"]["n_table_rows"] == 1
    assert ev["parse_rate"]["rate"] == 1.0 and ev["stability"]["jaccard_median"] == 1.0   # kept across reruns
    assert CLI.main(b + ["side-table", "--run-id", "o1"]) == 0
    pos = [json.loads(x) for x in (env["sdir"] / "position_table.jsonl").read_text().splitlines()]
    assert len(pos) == len(list((env["data"] / "traits" / "instructions").glob("*.json")))
    assert "negative_label_check" in pos[0] and (env["sdir"] / "negative_label_mismatches.md").exists()
    # submit --all, dry and real; then M1 and M3 blocks on the rows; then the report's three files
    assert CLI.main(b + ["submit", "--run-id", "w1", "--all", "--dry-run"]) == 0
    assert not (env["tmp"] / "candidates" / "runs" / "structural" / "w1").exists()
    assert CLI.main(b + ["submit", "--run-id", "w1", "--kept-target", "2", "--kept-share", "0.5"]) == 0
    wdir = env["tmp"] / "candidates" / "runs" / "structural" / "w1"
    rep = json.loads((wdir / "submit_report.json").read_text())
    assert rep["rows_submitted"] == rep["rows_counted"] + rep["rows_already_filtered"]
    reg = Registry(env["reg"])
    rows = reg.fold()
    for k, r in rows.items():
        if any(s.get("run_id") == "w1" for s in r["sources"]) and not r.get("novelty"):
            reg.update(k, {"filter": {"verdict": "trait"}, "novelty": {"decision": "new"}})
    assert CLI.main(b + ["report", "--run-id", "w1", "--operator-run", "o1"]) == 0
    for f in ("report.md", "roger_sample.md", "ai_identity_subfamily.md", "report.json"):
        assert (wdir / f).exists(), f
    md = (wdir / "report.md").read_text()
    assert md.index("Already registered") < md.index("Pair completions and degree fillers") < md.index(
        "Wholly new concepts")
    assert "raw" in md and "net" in md


def test_modernise_twice_sends_nothing_the_second_time(env, monkeypatch):
    """Review S1 (2026-10-13): the CLI always reuses recorded answers to the same prompt, without --resume."""
    from assistant_axis.gapgen.generators.structural import modernise as M
    from assistant_axis.gapgen.generators.structural.classical import load_all
    rows = [r for r in load_all(classical_dir=env["tmp"] / "classical") if r.scheme != "via"]
    system = P.modernise_system()
    answers = {}
    for unit in M.batches(rows):
        text = json.dumps({"rows": [{"id": r.id, "reasoning": "r", "labels": [r.item], "gloss": "This means it.",
                                     "polysemy": False} for r in unit]})
        answers[O.prompt_sha256(system, M.render_modernise_user(unit, siblings_from=rows))] = text
    client = F.ScriptedClient(answers)
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: client)
    assert CLI.main(env["base"] + ["modernise", "--run-id", "a1"]) == 0
    n = len(client.calls)
    assert n == len(M.batches(rows))
    out = env["sdir"] / "classical_modern.jsonl"
    first = out.read_bytes()
    assert CLI.main(env["base"] + ["modernise", "--run-id", "a1"]) == 0
    assert len(client.calls) == n and out.read_bytes() == first
    assert len(first.decode().splitlines()) == len(rows)


def test_postprocess_budget_stop_still_writes_usage(env, monkeypatch, capsys):
    """Review S3 (2026-10-13): the gloss embeddings' spend is recorded when the cap stops them, and accumulates."""
    import assistant_axis.gapgen.embed as EMB

    def priced(arm, **kw):
        e = EMB.HashEmbedder()
        e.usage_model = "text-embedding-3-large"          # charged at the live model's rate, so the cap can bite
        return e
    monkeypatch.setattr(EMB, "make_embedder", priced)
    assert CLI.main(env["base"] + ["operators", "--run-id", "o1", "--all"]) == 0
    up = env["sdir"] / "usage.json"
    assert CLI.main(env["base"] + ["postprocess", "--run-id", "o1", "--embedder", "hash",
                                   "--budget-usd", "0.000000001"]) == 1
    assert "STOPPED at the cap" in capsys.readouterr().err
    u = json.loads(up.read_text())
    assert u["n_calls"] >= 1 and u["per_model"]["text-embedding-3-large"]["prompt_tokens"] > 0
    ev = json.loads((env["sdir"] / "evaluation.json").read_text())["result"] if (
        env["sdir"] / "evaluation.json").exists() else {}
    assert "pair_recovery" not in ev
    first = u["n_calls"]
    assert CLI.main(env["base"] + ["postprocess", "--run-id", "o1", "--embedder", "hash", "--budget-usd", "1"]) == 0
    assert json.loads(up.read_text())["n_calls"] > first                    # cumulative across runs


def _refusing_client(env, *, first_ok: bool):
    """Every trait refused (``first_ok``: answered once, then refused, so a first run answers and a second refuses)."""
    ins = O.build_inputs(None, data_dir=env["data"], regions_path=env["data"] / "candidates" / "corpus_regions.json")
    return F.ScriptedClient(F.script_for(ins, SYSTEM, {
        t.stem: ([_answers(t.stem, t.principal_targets), F.refusal(), F.refusal()] if first_ok else F.refusal())
        for t in ins}))


def test_stability_is_reported_never_a_gate(env, monkeypatch, capsys):
    """Roger, 2026-10-13: stability is reported, never a gate.  The two-run form exits 0 whatever it finds, and says
    how many traits both runs answered (review B2: the Sonnet runs' 1.0 was on 3 of 30)."""
    client = _refusing_client(env, first_ok=True)          # one client for both runs: the second gets refusals
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: client)
    rc = CLI.main(env["base"] + ["stability", "--run-id", "sa", "--against", "sb", "--n", "4", "--seed", "1"])
    captured = capsys.readouterr()
    assert rc == 0 and "answered in both runs: 0 of 4 sampled traits" in captured.out
    assert "REPORTED (not a gate" in captured.out and "stopped other than end_turn" in captured.err
    st = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]["stability"]
    assert st["coverage"]["pass"] is False and st["n_sampled"] == 4 and st["reported_not_gated"]


def test_null_rate_gate_fails_when_the_sample_is_not_answered(env, monkeypatch, capsys):
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: _refusing_client(env, first_ok=False))
    rc = CLI.main(env["base"] + ["null-rate", "--run-id", "nr", "--n", "6"])          # 6 traits x 3 samples
    captured = capsys.readouterr()
    assert rc == CLI.EXIT_GATE and "answered 0 of 18 (trait, sample) calls" in captured.out
    assert "only 0 of 18 (trait, sample) calls answered" in captured.err and "*** 36 of 36 responses" in captured.err
    readout = json.loads((env["tmp"] / "candidates" / "runs" / "structural" / "nr" / "nullrate_readout.json").read_text())
    assert readout["coverage"]["pass"] is False and readout["stops"]["stop_reasons"] == {"refusal": 36}
    assert readout["stops"]["categories"] == {"reasoning_extraction": 36} and readout["samples"] == 3


def test_estimates_name_the_model_used(env, capsys):
    """Review B3 (2026-10-13): the estimate line said Haiku 5.5 whatever --model was."""
    for argv in (["operators", "--run-id", "o1", "--traits", "brave", "--dry-run", "--model", "claude-sonnet-5-5"],
                 ["stability", "--run-id", "a", "--against", "b", "--n", "3", "--dry-run", "--model",
                  "claude-sonnet-5-5"],
                 ["modernise", "--run-id", "m", "--dry-run", "--model", "claude-sonnet-5-5"]):
        assert CLI.main(env["base"] + argv) == 0
        out = capsys.readouterr().out
        line = next(x for x in out.splitlines() if "rates = $" in x)
        assert "at claude-sonnet-5-5 rates" in line and "Haiku" not in line and "haiku" not in line, line


def test_samples_dry_run_estimate_is_three_calls_a_trait(env, capsys):
    """Roger, 2026-10-13: three independent samples a trait by default; --samples 1 still possible."""
    n = len(list((env["data"] / "traits" / "instructions").glob("*.json")))
    assert CLI.main(env["base"] + ["operators", "--run-id", "o1", "--all", "--dry-run"]) == 0
    line = next(x for x in capsys.readouterr().out.splitlines() if "rates = $" in x)
    assert f"operators: {3 * n} calls" in line
    assert CLI.main(env["base"] + ["operators", "--run-id", "o1", "--all", "--samples", "1", "--dry-run"]) == 0
    line = next(x for x in capsys.readouterr().out.splitlines() if "rates = $" in x)
    assert f"operators: {n} calls" in line


def test_three_samples_end_to_end_with_support_and_the_within_run_agreement(env, capsys):
    b = env["base"]
    assert CLI.main(b + ["operators", "--run-id", "o3", "--all"]) == 0
    recs = [json.loads(x) for x in (env["tmp"] / "candidates" / "runs" / "structural" / "o3" /
                                    "responses.jsonl").read_text().splitlines()]
    assert sorted({r["sample"] for r in recs}) == [1, 2, 3]
    out = capsys.readouterr().out
    assert "union of 3 samples" in out
    # free: the agreement between the run's own samples, reported, exit 0
    assert CLI.main(b + ["stability", "--run-id", "o3"]) == 0
    st = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]["stability"]
    assert st["mode"] == "between the samples of one run" and st["jaccard_median"] == 1.0   # identical scripts
    assert "REPORTED (not a gate)" in capsys.readouterr().out
    assert CLI.main(b + ["postprocess", "--run-id", "o3", "--embedder", "none"]) == 0
    assert "union of 3 samples" in capsys.readouterr().out
    ev = json.loads((env["sdir"] / "evaluation.json").read_text())["result"]
    assert ev["n_samples"] == 3 and ev["union"] == "union of 3 samples" and set(ev["support"]["by_support"]) == {"3"}
    table = [json.loads(x) for x in (env["sdir"] / "operator_table.jsonl").read_text().splitlines()]
    assert all(s["support"] == 3 and s["n_samples"] == 3 for r in table for s in r["sources"])


def test_void_command_and_the_readouts_skip_a_void_run(env, capsys):
    b = env["base"]
    assert CLI.main(b + ["operators", "--run-id", "v1", "--traits", "brave", "--samples", "1"]) == 0
    assert CLI.main(b + ["void", "--run-id", "v1", "--reason", "refused", "--by", "test", "--dry-run"]) == 0
    assert not (env["tmp"] / "candidates" / "runs" / "structural" / "v1" / "void.json").exists()
    assert CLI.main(b + ["void", "--run-id", "v1", "--reason", "refused", "--by", "test"]) == 0
    assert CLI.main(b + ["void", "--run-id", "v1", "--reason", "again", "--by", "test"]) == 2   # once only
    capsys.readouterr()
    assert CLI.main(b + ["postprocess", "--run-id", "v1", "--embedder", "none"]) == 0
    captured = capsys.readouterr()
    assert "skipped run v1: marked void" in captured.err and "0 traits answered in full" in captured.out
    assert CLI.main(b + ["stability", "--run-id", "v1"]) == 2
    assert CLI.main(b + ["report", "--run-id", "v1"]) == 2
