"""``novelty_score.py`` end to end on the toy corpus (coding_plan_m3.md, "Tests, written alongside"), the
``gap_registry.py synonyms`` subcommand, ``promote``'s use of the M3 block, and the pilot's pool builders
on the real files.  No API calls: a fake Anthropic client, a hash embedder standing in for OpenAI's."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen import embed as EM
from assistant_axis.gapgen import novelty_pools as NP
from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, user_text
from assistant_axis.tests.test_gapgen_novelty import responder_for, write_corpus
from data_analysis.gap_generation import gap_registry
from data_analysis.gap_generation import novelty_score as cli

REPO = Path(__file__).resolve().parents[2]


class FakeOpenAIEmbedder(EM.HashEmbedder):
    """The hash embedder under OpenAI's name and cache tag (no network)."""
    name = "openai"

    def __init__(self, model: str = "text-embedding-3-large", **kw):
        super().__init__(dim=32)
        self.model_id = model
        self.tag = "openai_text-embedding-3-large"
        self.usage_model = model


CONFIG = {"config_version": "test-cfg", "models": {"live": {"arm": "openai", "model_id": "text-embedding-3-large"}},
          "covered": {"space": {"variant": "centred", "mean": "corpus_fixed"}, "representation": "w20", "metric": "cos",
                      "k": 3, "retrieval": {}, "contrast": {"openai": "keep"}},
          "directional": {"space": {"variant": "centred", "mean": "corpus_fixed"}, "representation": "w20", "K": 2},
          "canary": {"texts": [{"stem": "alpha", "text": "alpha: This means being alpha in every way."}],
                     "min_cosine": 0.999}}

#: (surface, gloss, verdict, alignment, holding)
ROWS = [("alpha", "This means being alpha.", "trait", 0, None),
        ("queued", "This means being queued.", "trait", 1, None),
        ("alphoid", "This means being alpha alpha beta in every way.", "trait", 0, None),
        ("deltaish", "This means being delta delta delta in every way.", "trait", 3, None),
        ("lambdaish", "This means being lambda mu lambda mu in every way.", "trait", 0, None),
        ("faraway", "This means being faraway.", "trait", 0, "nationalities"),
        ("turned away", "This means nothing.", "reject", None, None)]

RELATIONS = {("alphoid", "alpha"): "similar", ("deltaish", "delta"): "opposed", ("lambdaish", "lambda mu"): "opposed"}
OVERLAP = {("alphoid", "alpha"): 4, ("deltaish", "epsilon"): 1}


@pytest.fixture
def env(tmp_path, monkeypatch):
    import anthropic
    import dotenv
    data = write_corpus(tmp_path / "data")
    (data / "seed_queue.json").write_text(json.dumps({"entries": [
        {"stem": "queued", "label": "queued", "status": "candidate", "entity_type": "trait"}]}), encoding="utf-8")
    cand_dir = tmp_path / "candidates"
    cand_dir.mkdir()
    cfg = tmp_path / "metric_config.json"
    cfg.write_text(json.dumps({"result": CONFIG}), encoding="utf-8")
    reg_path = cand_dir / "registry.jsonl"
    rep = submit_candidates([Candidate(surface=s, generator="toy", run_id="r1") for s, *_ in ROWS], registry_path=reg_path)
    reg = Registry(reg_path)
    upd = {}
    for (s, gloss, verdict, a, holding), key in zip(ROWS, rep.keys):
        upd[key] = {"filter": {"verdict": verdict, "outcome": verdict, "alignment": a, "region": "moral_stance"},
                    "gloss": gloss if verdict == "trait" else None, "holding": holding}
    reg.update_many(upd)
    holder = {"responder": responder_for(RELATIONS, OVERLAP)}

    def factory(*a, **k):
        holder["client"] = FakeAsyncAnthropic(holder["responder"])
        return holder["client"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(EM, "OpenAIEmbedder", FakeOpenAIEmbedder)
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    base = ["--registry", str(reg_path), "--data-dir", str(data), "--out-root", str(cand_dir), "--metric-config", str(cfg),
            "--cache-dir", str(tmp_path / "cache"), "--transport", "live"]
    return {"base": base, "reg": reg, "cand_dir": cand_dir, "holder": holder, "data": data, "tmp": tmp_path}


def score(env, *extra):
    return cli.main(["score", "--batch-id", "m3t", "--run", "toy/r1", *env["base"], *extra])


def out(env, name="m3t"):
    return env["cand_dir"] / "novelty" / name


def test_dry_run_prints_the_plan_and_writes_nothing(env, capsys):
    before = env["reg"].path.read_text()
    assert score(env, "--dry-run") == 0
    o = capsys.readouterr().out
    assert '"n_candidates": 5' in o and '"n_exact_label": 2' in o and '"held_nationalities": 1' in o
    assert '"not_a_trait": 1' in o and "estimate by stage" in o and "[relation]" in o and "[overlap]" in o
    assert not out(env).exists() and env["reg"].path.read_text() == before


def test_end_to_end_writes_the_registry_once_and_every_record(env):
    assert score(env) == 0
    rows = env["reg"].fold()
    nv = {r["label"]: r.get("novelty") for r in rows.values()}
    assert nv["alpha"]["decision"] == "covered" and nv["alpha"]["reason"] == "exact_label"
    assert nv["queued"]["exact_label"]["match"] == "queue"
    assert nv["alphoid"]["decision"] == "covered" and nv["alphoid"]["covered_by"] == "alpha"
    assert nv["alphoid"]["deciding_reading"]["sonnet"]["value"] == 4 and nv["alphoid"]["cut_off"] == 3
    assert nv["deltaish"]["decision"] == "new" and nv["deltaish"]["cut_off"] == 4
    assert nv["deltaish"]["readings"][0]["stem"] == "epsilon"                     # the opposed trait's partner first
    assert nv["lambdaish"]["pair_completion_for"] == ["lambda_mu"] and nv["lambdaish"]["decision"] == "new"
    assert nv["faraway"] is None and nv["turned away"] is None                    # held and rejected rows left alone
    for v in nv.values():
        if v:
            assert v["run_id"] == "m3t" and v["config_version"] == "test-cfg"
            assert v["rubrics"]["overlap"]["name"] == "overlap_concept" and v["rubrics"]["relation"]["version"] == 1
    # each decided row written once (one revision past the filter update)
    assert all(r["rev"] == 3 for r in rows.values() if r.get("novelty"))
    d = out(env)
    for name in ("responses.jsonl", "results.jsonl", "readings.jsonl", "summary.json", "decisions.md", "usage.json",
                 "run.json", "run.log"):
        assert (d / name).exists(), name
    summary = json.loads((d / "summary.json").read_text())
    assert "_provenance" in summary and summary["result"]["by_decision"] == {"covered": 3, "new": 2}
    run = json.loads((d / "run.json").read_text())
    assert run["rubrics"]["relation"]["version"] == 1 and run["settings"]["query_form"] == "gloss_w14"
    assert run["canary"]["model"] == "text-embedding-3-large" and run["status"] == 0
    readings = [json.loads(x) for x in (d / "readings.jsonl").read_text().splitlines()]
    assert {r["key"] for r in readings} == {"alphoid#1", "deltaish#1"} and all("cosine" in r for r in readings)
    md = (d / "decisions.md").read_text()
    assert "| alphoid | covered | [alpha](../../../traits/instructions/alpha.json) | 3 | Sonnet 4 |" in md
    assert "## Pair completions (1 candidates)" in md and "[lambda mu](../../../traits/instructions/lambda_mu.json)" in md
    usage = json.loads((d / "usage.json").read_text())
    assert usage["total_cost_usd"] > 0 and "text-embedding-3-large" in usage["per_model"]


def test_resume_skips_decided_rows_and_finishes_a_stalled_one(env):
    good = env["holder"]["responder"]

    def flaky(kw):
        obj = json.loads(user_text(kw))
        if obj.get("target", {}).get("label") == "deltaish":
            return RuntimeError("network down")
        return good(kw)
    env["holder"]["responder"] = flaky
    assert score(env) == 0
    rows = env["reg"].fold()
    assert rows["deltaish#1"].get("novelty") is None
    revs = {k: r["rev"] for k, r in rows.items()}
    summary = json.loads((out(env) / "summary.json").read_text())["result"]
    assert summary["n_stalled"] == 1 and "deltaish#1" in summary["stalled"]
    env["holder"]["responder"] = good
    assert score(env) == 1                                                        # the dir exists: refused
    assert score(env, "--resume") == 0
    rows2 = env["reg"].fold()
    assert rows2["deltaish#1"]["novelty"]["decision"] == "new"
    assert all(rows2[k]["rev"] == revs[k] for k in revs if k != "deltaish#1")    # decided rows not written again
    calls = env["holder"]["client"].calls
    assert all(json.loads(user_text(k)).get("target", {}).get("label") == "deltaish" for k in calls)
    run = json.loads((out(env) / "run.json").read_text())
    assert run["resumed"] and len(run["earlier_sessions"]) == 1
    summary = json.loads((out(env) / "summary.json").read_text())["result"]
    assert summary["skipped"]["decided_in_this_run"] == 4
    # the run dir's files cover every candidate of the run, the earlier session's included
    assert summary["n_decided"] == 5 and summary["n_stalled"] == 0 and summary["by_decision"] == {"covered": 3, "new": 2}
    res = [json.loads(x) for x in (out(env) / "results.jsonl").read_text().splitlines()]
    md = (out(env) / "decisions.md").read_text()
    assert len(res) == 5 and "| deltaish | new |" in md and "| alphoid | covered |" in md
    assert {r["key"] for r in res} == {"alpha#1", "queued#1", "alphoid#1", "deltaish#1", "lambdaish#1"}


def test_refusals(env, monkeypatch, capsys):
    assert score(env, "--budget-usd", "0.0001") == 2
    assert "exceeds --budget-usd" in capsys.readouterr().err
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [" M assistant_axis/gapgen/novelty.py"])
    assert score(env) == 2
    assert "uncommitted changes" in capsys.readouterr().err
    assert not out(env).exists()


def test_full_scan_and_compare(env, capsys):
    assert score(env) == 0
    before = env["reg"].path.read_text()
    assert cli.main(["full-scan", "--batch-id", "scan1", "--from-batch", "m3t", "--sample", "5", *env["base"]]) == 0
    assert env["reg"].path.read_text() == before                                  # no registry writes
    res = [json.loads(x) for x in (out(env, "scan1") / "results.jsonl").read_text().splitlines()]
    assert {r["key"] for r in res} == {"alphoid#1", "deltaish#1", "lambdaish#1"}  # those that reached the relation call
    for r in res:
        nv = r["novelty"]
        assert nv["mode"] == "full_scan" and {p["stem"] for p in nv["scan"]} == {x["stem"] for x in nv["listed"]}
    recs = [json.loads(x) for x in (out(env, "scan1") / "responses.jsonl").read_text().splitlines()]
    assert {x["step"] for x in recs} == {"overlap"}
    assert cli.main(["compare", "--scan-batch", "scan1", "--main-batch", "m3t", "--out-root", str(env["cand_dir"])]) == 0
    c = json.loads((out(env, "scan1") / "comparison.json").read_text())["result"]
    assert c["n_candidates"] == 3 and "relation_recall" in c and c["relation_recall"]["pairs_cut_by_the_rule"] >= 1
    assert "covered -> covered" in c["decisions"]["main_vs_scan"]
    assert (out(env, "scan1") / "comparison.md").exists()


def test_decisions_review_list_and_synonyms(env, capsys):
    assert score(env) == 0
    capsys.readouterr()
    assert cli.main(["decisions", "--batch-id", "m3t", "--out-root", str(env["cand_dir"]), "--data-dir", str(env["data"])]) == 0
    assert cli.main(["review-list", "--registry", str(env["reg"].path), "--include-new"]) == 0
    o = capsys.readouterr().out
    assert "deltaish#1" in o and "lambdaish#1" in o
    assert gap_registry.main(["--registry", str(env["reg"].path), "synonyms"]) == 0
    o = capsys.readouterr().out
    lines = [ln for ln in o.splitlines() if ln.startswith("| ") and not ln.startswith("| trait")]
    assert lines[0].startswith("| alpha | 4 | alphoid | alphoid#1 | Sonnet 4 |")    # read 4 first, exact labels last
    assert any("exact label (queue)" in ln for ln in lines)
    assert gap_registry.main(["--registry", str(env["reg"].path), "synonyms", "--stem", "queued"]) == 0
    assert "alphoid" not in capsys.readouterr().out


def test_promote_takes_the_partner_from_pair_completion_for():
    from assistant_axis.gapgen.promote import queue_entry_from_record
    rec = {"key": "lambdaish#1", "stem": "lambdaish", "label": "lambdaish", "gloss": "g", "sources": [],
           "filter": {"verdict": "trait", "tags": []},
           "novelty": {"run_id": "m3t", "decision": "grey", "pair_completion_for": ["lambda_mu", "zeta"],
                       "review": ["pair_flag"]}}
    e = queue_entry_from_record(rec)
    assert e["partner"] == "lambda_mu" and e["pairing"] == "pair"
    assert "pair completion for lambda_mu, zeta" in e["description_notes"] and "M3 review: pair_flag" in e["description_notes"]
    old = {**rec, "novelty": {"flags": ["pair_completion"], "nearest_existing": "zeta"}}
    assert queue_entry_from_record(old)["partner"] == "zeta"                       # the earlier block shape still reads


def test_render_a_registry_candidate(env, capsys):
    assert score(env) == 0                                                        # embeds the candidates (cached)
    capsys.readouterr()
    assert cli.main(["render", "--key", "alphoid#1", "--registry", str(env["reg"].path), "--data-dir", str(env["data"]),
                     "--metric-config", str(env["tmp"] / "metric_config.json"), "--cache-dir", str(env["tmp"] / "cache")]) == 0
    o = capsys.readouterr().out
    assert "=== relation call" in o and '{"candidate": {"label": "alphoid"' in o and '"other": {"label":' in o


# --------------------------------------------------------------------------- the pilot's pools, on the real files

class TestPilotPools:
    def test_antonym_pool(self):
        import data_analysis.seed_entities as se
        data = REPO / "data"
        queue = se.load_queue(data / "seed_queue.json")
        corpus, qn = NP.corpus_trait_stems(data), NP.queue_names(queue)
        rows, counts = NP.antonym_pool(data / "traits" / "antonym_check_history.jsonl", corpus=corpus, queue=qn)
        from assistant_axis.entity_id import normalize_to_file_name
        stems = {normalize_to_file_name(r["surface"]) for r in rows}
        assert len(stems) == counts["words"] and counts["words"] > 300
        assert not stems & corpus and not stems & qn
        hist = [json.loads(x) for x in (data / "traits" / "antonym_check_history.jsonl").read_text().splitlines() if x.strip()]
        proposed = {normalize_to_file_name(w) for h in hist for w in h.get("candidates") or []}
        assert stems == proposed - corpus - qn                                   # every proposed word, nothing else
        assert counts["words_proposed_more_than_once"] == sum(1 for s in stems if next(
            r["score"] for r in rows if normalize_to_file_name(r["surface"]) == s) > 1)
        assert all(r["gloss_hint"] is None and r["source_ref"] for r in rows)
        # the brief's 449 is the corpus subtraction alone (on 2026-10-04); the queue takes more out
        assert counts["distinct_words"] - counts["in_corpus"] >= counts["words"]

    def test_m1_validation_pool(self):
        p = REPO / "data" / "candidates" / "filter" / "m1_validation" / "results.jsonl"
        rows, counts = NP.m1_validation_pool(p, n=150, seed=0)
        again, _ = NP.m1_validation_pool(p, n=150, seed=0)
        assert len(rows) == 150 and rows == again and counts["passed_as_trait"] == 309
        assert len({r["source_ref"] for r in rows}) == 150
        res = {json.loads(x)["key"]: json.loads(x) for x in p.read_text().splitlines() if x.strip()}
        for r in rows:
            src = res[r["source_ref"].split(":", 1)[1]]
            assert src["meta"]["stratum"] == "oewn_random" and src["filter"]["verdict"] == "trait"
        other, _ = NP.m1_validation_pool(p, n=150, seed=1)
        assert other != rows

    def test_build_pilot_pools_writes_both_files(self, tmp_path):
        rec = NP.build_pilot_pools(REPO, tmp_path, n_m1=10, seed=0)
        assert (tmp_path / "antonym_check_pilot_1.jsonl").exists() and (tmp_path / "m1_validation_pilot_1.jsonl").exists()
        assert rec["m1_validation"]["drawn"] == 10 and json.loads((tmp_path / "pools.json").read_text()) == rec
