"""The LLM-entropy generator's CLI (``llm_entropy_generator.py``; coding_plan_06 section 8, CLI and ``roles``): every
subcommand's dry run writes nothing; paid commands refuse over budget; ``generate`` refuses an unknown family and a
share outside (0, 1]; ``translate-prompts`` refuses to overwrite; and the pipeline translate-prompts -> generate (a,
b, c on two models, e) -> backtranslate -> verbalized -> postprocess -> collapse -> submit -> model-test ->
roles-report -> report runs end to end on fake clients, a toy corpus and a tmp registry.  No network, no model; every
person is invented."""
from __future__ import annotations

import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.generators.llm_entropy import prompts as P
from assistant_axis.gapgen.generators.llm_entropy import seeds as SD
from assistant_axis.gapgen.registry import Registry
from assistant_axis.tests import llm_entropy_fakes as F
from assistant_axis.tests import structural_fakes as SF
from data_analysis.gap_generation import llm_entropy_generator as CLI


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


@pytest.fixture()
def env(tmp_path, monkeypatch):
    import tempfile
    data = SF.write_corpus(tmp_path)
    rdir = data / "roles" / "instructions"
    rdir.mkdir(parents=True)
    (rdir / "zzwardenly.json").write_text(json.dumps({"description": "A role fixture."}), encoding="utf-8")
    cand = tmp_path / "candidates"
    reg = SF.write_registry(cand / "registry.jsonl", [
        SF.registry_row("zzshared", "censuses", verdict="trait", decision="covered")])
    tmpdir = tmp_path / "tmpdir"
    tmpdir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(tmpdir))
    live = F.ScriptedAnthropic(default=F.family_reply)
    batch = F.FakeBatchClient(F.family_reply)
    clock = Clock()
    session = F.FakeWikidataSession()
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: live)
    monkeypatch.setattr(CLI, "_batch_client", lambda: batch)
    monkeypatch.setattr(CLI, "_wikidata", lambda args: SD.Throttle(session, clock=clock, sleep=clock.sleep))
    monkeypatch.setattr(CLI, "_dirty", lambda args: None)
    base = ["--data-dir", str(data), "--registry", str(reg), "--candidates-dir", str(cand)]
    return SimpleNamespace(tmp=tmp_path, data=data, cand=cand, reg=reg, base=base, live=live, batch=batch,
                           session=session, tmpdir=tmpdir, edir=cand / "llm_entropy")


def run(env, *argv) -> int:
    return CLI.main([*env.base, *argv])


def _tree(root: Path) -> dict:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _run_dir(env, run_id):
    return env.cand / "runs" / "llm_entropy" / run_id


# --------------------------------------------------------------------------- refusals and dry runs

def test_generate_refuses_an_unknown_family_and_a_bad_share(env):
    assert run(env, "generate", "--run-id", "r", "--family", "z") == 2
    assert run(env, "generate", "--run-id", "r", "--family", "d") == 2          # (d) is --with-probabilities
    for bad in ("0", "1.5", "-0.2"):
        assert run(env, "generate", "--run-id", "r", "--family", "a", "--share", bad) == 2
    assert run(env, "generate", "--run-id", "r", "--family", "b", "--with-probabilities") == 2


def test_paid_commands_refuse_over_budget(env):
    assert run(env, "generate", "--run-id", "r", "--family", "a", "--budget-usd", "0.001") == 2
    assert run(env, "generate", "--run-id", "r", "--family", "b", "--budget-usd", "0.001") == 2
    assert run(env, "translate-prompts", "--budget-usd", "0.001") == 2
    assert run(env, "generate", "--run-id", "r", "--family", "a", "--budget-usd", "25") == 2   # over the $20 line
    assert env.live.calls == [] and env.batch.batches.created == [] and not env.cand.joinpath("runs").exists()


def test_every_dry_run_exits_0_and_writes_nothing(env, capsys):
    # a real run first, so that the later dry runs have something to read
    assert run(env, "generate", "--run-id", "r1", "--family", "a", "--n-prompts", "2", "--runs", "2") == 0
    assert run(env, "postprocess", "--run-id", "r1") == 0
    before = _tree(env.tmp)
    calls = (len(env.live.calls), len(env.batch.batches.created))
    for argv in (["seeds", "--real", "2", "--dry-run"], ["prompts", "--dry-run"],
                 ["translate-prompts", "--dry-run"],
                 ["generate", "--run-id", "r2", "--family", "a", "--share", "0.2", "--dry-run"],
                 ["generate", "--run-id", "r2", "--family", "e", "--share", "0.2", "--with-probabilities", "--dry-run"],
                 ["generate", "--run-id", "r2", "--family", "b", "--share", "0.2", "--dry-run"],
                 ["backtranslate", "--run-id", "r1", "--dry-run"],
                 ["verbalized", "--run-id", "r1", "--family", "a", "--dry-run"],
                 ["postprocess", "--dry-run"], ["collapse", "--embedder", "hash", "--dry-run"],
                 ["model-test", "--run-id", "r1", "--dry-run"],
                 ["submit", "--run-id", "r1", "--top", "5", "--dry-run", "--no-relabel"],
                 ["roles-report", "--run-id", "r1", "--dry-run"], ["report", "--run-id", "r1", "--dry-run"]):
        assert run(env, *argv) == 0, argv
    assert _tree(env.tmp) == before
    assert (len(env.live.calls), len(env.batch.batches.created)) == calls
    out = capsys.readouterr().out
    assert "Tian Yi" in out                                  # the (b) dry run's sample is the fixed row


def test_translate_prompts_refuses_to_overwrite_without_force(env, capsys):
    assert run(env, "translate-prompts") == 0
    pj = json.loads((env.edir / "multilingual_prompts.json").read_text())
    assert set(pj["languages"]) == {lang.code for lang in P.LANGUAGES}
    de = pj["languages"]["de"]
    assert de["system"].startswith("[German] ") and de["user_template"].count("{domain}") == 1
    assert de["master_sha256"] == P.load_rubric(P.MULTILINGUAL_RUBRIC)["sha256"] and len(de["sha256"]) == 64
    assert de["backtranslation"]["domains"]["money"] == "money"
    assert (env.edir / "multilingual_prompts_usage.json").exists()
    out = capsys.readouterr().out
    assert "THE ENGLISH MASTER" in out and "money -> money-ge -> money" in out
    assert run(env, "translate-prompts") == 2
    assert run(env, "translate-prompts", "--languages", "de", "--force") == 0
    assert list(env.edir.glob("multilingual_prompts.json.bak.*"))


def test_resume_is_needed_to_rerun_answered_calls(env):
    assert run(env, "generate", "--run-id", "r", "--family", "e", "--n-prompts", "2", "--runs", "1",
               "--transport", "live") == 0
    n = len(env.live.calls)
    assert run(env, "generate", "--run-id", "r", "--family", "e", "--n-prompts", "2", "--runs", "1",
               "--transport", "live") == 2
    assert run(env, "generate", "--run-id", "r", "--family", "e", "--n-prompts", "3", "--runs", "1",
               "--transport", "live", "--resume") == 0
    assert len(env.live.calls) == n + 1                       # only the new prompt was sent


def test_a_changed_prompt_fails_loudly_against_a_hash_script(env, monkeypatch):
    rub = P.load_rubric(P.SCAFFOLD_RUBRIC)
    ps = P.select_prompts(P.grid_prompts("a"), n=2, seed=0)
    script = {F.prompt_hash(rub["text"], p.user): F.reply_items(["zzpinned"]) for p in ps}
    pinned = F.ScriptedAnthropic(script)
    monkeypatch.setattr(CLI, "_anthropic_client", lambda: pinned)
    assert run(env, "generate", "--run-id", "h", "--family", "a", "--n-prompts", "2", "--runs", "1",
               "--transport", "live") == 0
    monkeypatch.setattr(P, "A_TEMPLATE", P.A_TEMPLATE.replace("Include admirable", "Include both admirable"))
    assert run(env, "generate", "--run-id", "h2", "--family", "a", "--n-prompts", "2", "--runs", "1",
               "--transport", "live") == 1                     # unscripted prompts: failed calls, no answer
    recs = [json.loads(x) for x in (_run_dir(env, "h2") / "responses.jsonl").read_text().splitlines()]
    assert recs and not any(r["ok"] for r in recs)


# --------------------------------------------------------------------------- the pipeline end to end

def _set_m1_m3(env, verdicts: dict):
    """Simulate M1 and M3 on registry rows: ``{stem: (verdict, decision, holding)}``."""
    reg = Registry(env.reg)
    raw = reg.fold(raw=True)
    out = []
    for key, r in raw.items():
        if r["stem"] in verdicts:
            v, d, h = verdicts[r["stem"]]
            r = dict(r, filter={"verdict": v, "tags": ["role_person"] if h == "roles" else []},
                     novelty={"decision": d, "run_id": "m3"} if d else None, holding=h)
            out.append(r)
    reg.write(out)


def test_the_pipeline_end_to_end(env, capsys):
    R = "pilot"
    assert run(env, "translate-prompts") == 0
    assert run(env, "generate", "--run-id", R, "--family", "a", "--n-prompts", "3", "--with-probabilities") == 0
    assert run(env, "generate", "--run-id", R, "--family", "e", "--n-prompts", "3", "--runs", "2") == 0
    assert run(env, "generate", "--run-id", R, "--family", "c", "--n-prompts", "2", "--runs", "2") == 0
    assert run(env, "generate", "--run-id", R, "--family", "c", "--n-prompts", "2", "--runs", "1", "--model",
               "claude-sonnet-5-5") == 0
    assert run(env, "generate", "--run-id", R, "--family", "b", "--real", "2", "--fictional", "1") == 0
    assert run(env, "backtranslate", "--run-id", R) == 0
    assert run(env, "verbalized", "--run-id", R, "--family", "a") == 0
    rdir = _run_dir(env, R)
    usage = json.loads((rdir / "usage.json").read_text())
    assert usage["n_calls"] > 0 and any(k.endswith(":batch") for k in usage["per_model"])
    recs = [json.loads(x) for x in (rdir / "responses.jsonl").read_text().splitlines()]
    assert {r["family"] for r in recs} == {"a", "b", "c", "d", "e"} and all(r["ok"] for r in recs)
    assert {r["step"] for r in recs} == {"generate", "backtranslate", "verbalized"}
    c_recs = [r for r in recs if r["family"] == "c" and r["step"] == "generate"]
    pj = json.loads((env.edir / "multilingual_prompts.json").read_text())
    assert all(r["meta"]["language_prompt_sha256"] == pj["languages"][r["language"]]["sha256"] for r in c_recs)
    assert run(env, "postprocess", "--run-id", R, "--embedder", "hash") == 0
    table = [json.loads(x) for x in (env.edir / "items_table.jsonl").read_text().splitlines()]
    by = {r["stem"]: r for r in table}
    assert by["zzshared"]["registered_decided"] and not by["zzshared"]["net_new"]
    assert by["zzshared"]["n_sources"] >= 4 and {"a", "d", "e"} <= set(by["zzshared"]["families"])
    assert any(r["families"] == ["c"] and r["raws"] for r in table)
    assert any(r["pair_completion_hint"] == "gloomy" for r in table)      # an antonym that is a non-X singleton
    ev = json.loads((env.edir / "evaluation.json").read_text())["result"]
    assert set(ev["string_recovery"]) >= {"a", "b", "c", "d", "e", "all"}
    assert run(env, "collapse", "--run-id", R, "--embedder", "hash") == 0
    coll = json.loads((env.edir / "collapse.json").read_text())["result"]
    assert set(coll["per_family"]) == {"a", "b", "c", "d", "e"} and coll["per_family"]["a"]["jaccard_median"] == 1.0
    assert coll["costs"]["usage_json_usd"] == pytest.approx(usage["total_cost_usd"])
    assert run(env, "submit", "--run-id", R, "--top", "12", "--per-cell", "2", "--no-relabel") == 0
    sub = json.loads((rdir / "submit_report.json").read_text())
    assert sub["rows_counted"] <= 12 and sub["n_candidates"] >= sub["rows_submitted"]
    cands = [json.loads(x) for x in (rdir / "candidates.jsonl").read_text().splitlines()]
    assert all(c["generator"] == "llm_entropy" and c["run_id"] == R and c["source_ref"].startswith("llm_entropy:")
               for c in cands)
    keys = (rdir / "keys.txt").read_text().split()
    stems = [k.split("#")[0] for k in keys]
    # M1 and M3, simulated: one row held as a role, the rest judged
    held = "zzwardenly" if "zzwardenly" in stems else stems[0]
    _set_m1_m3(env, {s: ("trait", "new" if i % 2 else "covered", None) for i, s in enumerate(stems) if s != held}
               | {held: ("tagged", None, "roles")})
    assert run(env, "model-test", "--run-id", R) == 0
    ev = json.loads((env.edir / "evaluation.json").read_text())["result"]
    cells = ev["model_test"][R]["cells"]
    assert "c|claude-sonnet-5-5" in cells and "c|claude-haiku-5-5" in cells
    assert run(env, "roles-report", "--run-id", R) == 0
    roles_md = (env.edir / "roles_report.md").read_text()
    assert held.replace("_", " ") in roles_md or held in roles_md
    assert run(env, "report", "--run-id", R) == 0
    for name in ("report.md", "roger_sample.md", "gloss_check.md"):
        assert (rdir / name).exists(), name
    rep = (rdir / "report.md").read_text()
    assert "Already registered (the headline)" in rep and "raw " in rep and "net " in rep
    assert "](../../../../../reports/trait_gap_generation/glossary.md)" in rep


def test_a_held_role_reaches_neither_m3_nor_the_queue(env):
    from assistant_axis.gapgen.novelty_runner import candidate_from_row
    from assistant_axis.gapgen.promote import promote
    R = "roles"
    assert run(env, "generate", "--run-id", R, "--family", "b", "--real", "1", "--fictional", "0") == 0
    assert run(env, "postprocess", "--run-id", R) == 0
    assert run(env, "submit", "--run-id", R, "--all", "--no-relabel") == 0
    _set_m1_m3(env, {"zzwardenly": ("tagged", None, "roles")})
    row = Registry(env.reg).get("zzwardenly#1")
    assert row["holding"] == "roles"
    assert candidate_from_row(row) == (None, "not_a_trait")                  # M3 never scores it
    rep = promote(Registry(env.reg).fold(), {"entries": []}, ["zzwardenly#1"], data_dir=env.data)
    assert rep.promoted == [] and "never promoted" in rep.refused["zzwardenly#1"]
    assert run(env, "roles-report", "--run-id", R) == 0
    assert "zzwardenly" in (env.edir / "roles_report.md").read_text()


def test_report_renders_a_fixture_run_with_the_three_files(env):
    assert run(env, "generate", "--run-id", "fx", "--family", "e", "--n-prompts", "4", "--runs", "3") == 0
    assert run(env, "postprocess", "--run-id", "fx") == 0
    assert run(env, "report", "--run-id", "fx") == 0
    rdir = _run_dir(env, "fx")
    assert {p.name for p in rdir.glob("*.md")} == {"report.md", "roger_sample.md", "gloss_check.md"}
    assert "## Family e" in (rdir / "gloss_check.md").read_text()
