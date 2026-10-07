"""CLI tests for data_analysis/gap_generation/{traithood_filter,gap_registry}.py.

No API calls: the Anthropic client is replaced by a fake, and dry runs are
checked to write nothing."""
import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.registry import Candidate, Registry, submit_candidates
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response, system_text, user_text
from data_analysis.gap_generation import gap_registry, traithood_filter

HAIKU = "claude-haiku-4-5-20251001"
REPO = Path(__file__).resolve().parents[2]
#: These tests cover the single-call classifier; since coding_plan_split.md the CLI's default
#: pipeline is the split filter (tested in assistant_axis/tests/test_gapgen_split_runner.py).
SINGLE = ["--pipeline", "single"]


def _corpus_n() -> int:
    """The number of trait files the calibration reads (its own loader), so the calibration tests
    follow the corpus as it grows (659 traits at M2, 663 after the 2026-10-02 merge with the main
    line) instead of hard-coding one size."""
    from data_analysis.gap_generation import calibrate_metric as CM
    n = len(CM.corpus_inputs(CM._REPO_ROOT)["stems"])
    assert n == len(list((CM._REPO_ROOT / "data" / "traits" / "instructions").glob("*.json"))) > 600
    return n


def _paraphrase_calls(n: int) -> int:
    """Haiku calls to paraphrase ``n`` descriptions (one call per batch)."""
    from assistant_axis.gapgen import calibrate_llm as CL
    return -(-n // CL.PARAPHRASE_BATCH)


def _row(i, label):
    row = {"id": i, "label": label, "reason": "A habit.",
           "person_senses": [{"sense": label, "kind": "trait"}], "trait_senses_equally_obvious": False, "judged_sense": label,
           "enactable_in_text": 2, "verdict": "trait", "tags": [], "region": "social_interpersonal",
           "alignment_relevant": False, "gloss": "This means " + "doing things " * 9 + "always.",
           "confidence": 0.9}
    if label == "tall":
        row.update(verdict="tagged", tags=["physical"], region="physical")
    if label == "librarian":
        row.update(verdict="tagged", tags=["role_person"])
    return row


def responder(kw, *, tokens=(1000, 300)):
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    if "real English word" in system_text(kw):
        body = {"results": [{"id": it["id"], "reason": "ok", "definition": "d", "known": True} for it in items]}
    else:
        body = {"results": [_row(it["id"], it["label"]) for it in items]}
    return make_response(json.dumps(body), input_tokens=tokens[0], output_tokens=tokens[1])


@pytest.fixture
def fake_client(monkeypatch):
    import anthropic
    import dotenv

    holder = {}

    def factory(**kw):
        holder["client"] = FakeAsyncAnthropic(holder.get("responder", responder), delay=holder.get("delay", 0.0))
        return holder["client"]

    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    return holder


@pytest.fixture(autouse=True)
def clean_tree(monkeypatch):
    """Paid runs refuse a dirty tree (review finding 10); the tests' tree state
    is whatever the developer has, so pin it to clean unless a test says not."""
    monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234")
    if hasattr(traithood_filter, "platform_dirty_files"):
        monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])


@pytest.fixture
def cand_dir(tmp_path):
    d = tmp_path / "candidates"
    d.mkdir()
    return d


def _submit(reg_path, surfaces, gen="wordnet_walk", run="r1"):
    return submit_candidates([Candidate(surface=s, generator=gen, run_id=run) for s in surfaces],
                             registry_path=reg_path)


def _validation(tmp_path):
    p = tmp_path / "val.jsonl"
    rows = ([{"surface": w, "stratum": "existing", "expected": {"verdict": "trait"}}
             for w in (["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm",
                                    "proud", "witty", "frank", "meek"])]
            + [{"surface": "tall", "stratum": "physical", "expected": {"verdict": "tagged", "tags": ["physical"]}}])
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


class TestTraithoodFilterCLI:
    def test_dry_run_writes_nothing(self, cand_dir, fake_client, capsys):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "vain"])
        raw = reg.read_bytes()
        rc = traithood_filter.main([*SINGLE, "--batch-id", "b1", "--unfiltered", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0 and reg.read_bytes() == raw
        assert not (cand_dir / "filter").exists() and "client" not in fake_client
        assert "tokens at claude-haiku-4-5-20251001 rates = $" in out
        assert "--- prompt 1 ---" in out and '"label": "stubborn"' in out

    def test_validation_run(self, tmp_path, cand_dir, fake_client):
        val = _validation(tmp_path)
        rc = traithood_filter.main([*SINGLE, "--batch-id", "pilot", "--validation-file", str(val), "--out-root",
                                    str(cand_dir), "--no-second-opinion", "--sample-frac", "0.5"])
        assert rc == 0
        d = cand_dir / "filter" / "pilot"
        for f in ("responses.jsonl", "results.jsonl", "summary.json", "usage.json", "run.json"):
            assert (d / f).exists(), f
        env = json.loads((d / "summary.json").read_text())
        s = env["result"]
        assert "_provenance" in env
        assert s["n"] == 7  # 6 of 12 existing, the 1-row stratum whole
        assert s["by_stratum"]["physical"]["tag_counts"] == {"physical": 1}
        assert s["parse_rate"] == 1.0 and s["cost_usd"] > 0
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] == len(fake_client["client"].calls)
        res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        assert {r["meta"]["stratum"] for r in res} == {"existing", "physical"}
        assert not (cand_dir / "registry.jsonl").exists()

    def test_refuses_existing_batch(self, tmp_path, cand_dir, fake_client):
        val = _validation(tmp_path)
        args = [*SINGLE, "--batch-id", "b", "--validation-file", str(val), "--out-root", str(cand_dir), "--no-second-opinion"]
        assert traithood_filter.main(args) == 0
        assert traithood_filter.main(args) == 1

    def test_run_selector_writes_registry(self, cand_dir, fake_client):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "tall", "librarian"], run="r1")
        _submit(reg, ["vain"], gen="censuses", run="t1")
        rc = traithood_filter.main([*SINGLE, "--batch-id", "b2", "--run", "wordnet_walk/r1", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--no-second-opinion"])
        assert rc == 0
        rows = Registry(reg).fold()
        assert rows["stubborn#1"]["filter"]["verdict"] == "trait" and rows["stubborn#1"]["gloss"]
        assert rows["stubborn#1"]["freq"]["zipf_min"] > 2
        assert rows["tall#1"]["holding"] == "physical"
        assert rows["librarian#1"]["holding"] == "roles" and rows["librarian#1"]["entity_type"] == "role"
        assert rows["vain#1"]["filter"] is None  # other run untouched
        # a second pass over the same run finds nothing unfiltered
        assert traithood_filter.main([*SINGLE, "--batch-id", "b3", "--run", "wordnet_walk/r1", "--registry", str(reg),
                                      "--out-root", str(cand_dir)]) == 0
        assert not (cand_dir / "filter" / "b3").exists()

    def test_estimate_over_budget_refused(self, cand_dir, fake_client):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        rc = traithood_filter.main([*SINGLE, "--batch-id", "b4", "--unfiltered", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--budget-usd", "0.00001"])
        assert rc == 2 and not (cand_dir / "filter" / "b4").exists() and "client" not in fake_client

    def test_cap_stops_run_and_keeps_what_was_paid_for(self, cand_dir, fake_client):
        """Review finding 4: a stop must stop (bounded calls) and keep the rows
        and responses already paid for."""
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm", "proud", "witty"])
        fake_client["responder"] = lambda kw: responder(kw, tokens=(40_000, 0))  # $0.04 per call
        fake_client["delay"] = 0.01  # calls overlap like network I/O
        rc = traithood_filter.main([*SINGLE, "--batch-id", "b5", "--unfiltered", "--registry", str(reg), "--out-root",
                                    str(cand_dir), "--budget-usd", "0.10", "--batch-size", "2",
                                    "--concurrency", "2", "--no-second-opinion", "--no-probe"])
        assert rc == 2
        d = cand_dir / "filter" / "b5"
        usage = json.loads((d / "usage.json").read_text())
        n = usage["n_calls"]
        assert 3 <= n <= 4  # trips on the 3rd call; at most concurrency - 1 more in flight
        assert len(fake_client["client"].calls) == n
        assert len((d / "responses.jsonl").read_text().splitlines()) == n
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["stopped_by_budget"] is True
        rows = Registry(reg).fold()
        filtered = [k for k, r in rows.items() if r.get("filter")]
        assert len(filtered) == 2 * n
        assert sum(1 for r in rows.values() if not r.get("filter")) == 10 - 2 * n

    def test_refilter_replaces_filter_block(self, cand_dir, fake_client):
        """Review finding 5: a re-filter must not keep keys from the old block."""
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        Registry(reg).update("stubborn#1", {"filter": {"verdict": "reject", "classifier_verdict": "trait",
                                                       "tags": ["too_rare"], "rubric_version": 0}})
        assert traithood_filter.main([*SINGLE, "--batch-id", "b6", "--keys", "stubborn#1", "--registry", str(reg),
                                      "--out-root", str(cand_dir), "--no-second-opinion"]) == 0
        f = Registry(reg).get("stubborn#1")["filter"]
        assert f["verdict"] == "trait" and "classifier_verdict" not in f and f["rubric_version"] == 6  # classifier v6 (2026-10-02)

    def test_prompt_hashes_recorded(self, tmp_path, cand_dir, fake_client):
        """Review finding 10: which prompt text was sent is recorded."""
        import hashlib
        from assistant_axis.gapgen import filter_rubric as fr
        from assistant_axis.gapgen import plain_reading as pr
        val = _validation(tmp_path)
        assert traithood_filter.main([*SINGLE, "--batch-id", "h", "--validation-file", str(val), "--out-root",
                                      str(cand_dir), "--no-second-opinion"]) == 0
        d = cand_dir / "filter" / "h"
        want = hashlib.sha256(fr.SYSTEM_PROMPT.encode()).hexdigest()
        want_probe = hashlib.sha256(fr.DEFINE_PROBE_PROMPT.encode()).hexdigest()
        rj = json.loads((d / "run.json").read_text())
        want_all = {"classifier": want, "probe": want_probe, **pr.PROMPT_SHA256}  # round 3: four prompts
        assert rj["prompt_sha256"] == want_all
        res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        assert all(r["filter"]["prompt_sha256"] == want_all for r in res)

    def test_dirty_tree_refused_without_flag(self, tmp_path, cand_dir, fake_client, monkeypatch):
        """Review finding 10 / re-review 5c: a paid run with uncommitted changes
        to the platform's own paths needs --allow-dirty; the check is recorded."""
        monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234+dirty")
        monkeypatch.setattr(traithood_filter, "platform_dirty_files",
                            lambda *a, **k: [" M assistant_axis/gapgen/filter.py"])
        val = _validation(tmp_path)
        base = [*SINGLE, "--validation-file", str(val), "--out-root", str(cand_dir), "--no-second-opinion"]
        assert traithood_filter.main(["--batch-id", "d1", *base]) == 2
        assert not (cand_dir / "filter" / "d1").exists() and "client" not in fake_client
        assert traithood_filter.main(["--batch-id", "d1", "--dry-run", *base]) == 0
        assert traithood_filter.main(["--batch-id", "d2", "--allow-dirty", *base]) == 0
        rj = json.loads((cand_dir / "filter" / "d2" / "run.json").read_text())
        assert rj["git_sha"] == "abc1234+dirty" and rj["allow_dirty"] is True
        assert rj["dirty_check"]["dirty"] == [" M assistant_axis/gapgen/filter.py"]
        assert "assistant_axis/gapgen" in rj["dirty_check"]["paths"]

    def test_unrelated_dirty_file_does_not_block(self, tmp_path, cand_dir, fake_client, monkeypatch):
        """Re-review 5c: an edited report elsewhere makes git_sha '+dirty' but
        must not force --allow-dirty."""
        monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234+dirty")
        monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])
        val = _validation(tmp_path)
        assert traithood_filter.main([*SINGLE, "--batch-id", "u1", "--validation-file", str(val), "--out-root",
                                      str(cand_dir), "--no-second-opinion"]) == 0
        rj = json.loads((cand_dir / "filter" / "u1" / "run.json").read_text())
        assert rj["dirty_check"]["dirty"] == [] and rj["allow_dirty"] is False

    def test_non_budget_exception_keeps_paid_rows(self, cand_dir, fake_client, monkeypatch):
        """Re-review item 3: an exception that is not a budget stop still stops
        new calls, and the CLI writes results, usage and registry rows in a
        finally."""
        from assistant_axis.gapgen import filter_rubric as fr
        real = fr.parse_batch
        n = {"parse": 0}

        def flaky(text, ids, **kw):
            n["parse"] += 1
            if n["parse"] == 3:
                raise RuntimeError("injected parser crash")
            return real(text, ids, **kw)

        monkeypatch.setattr(fr, "parse_batch", flaky)
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm", "proud", "witty"])
        with pytest.raises(RuntimeError, match="injected"):
            traithood_filter.main([*SINGLE, "--batch-id", "e1", "--unfiltered", "--registry", str(reg), "--out-root",
                                   str(cand_dir), "--batch-size", "1", "--concurrency", "1",
                                   "--no-second-opinion", "--no-probe"])
        d = cand_dir / "filter" / "e1"
        calls = len(fake_client["client"].calls)
        assert calls == 3
        assert json.loads((d / "usage.json").read_text())["n_calls"] == 3
        assert len((d / "responses.jsonl").read_text().splitlines()) == 3
        res = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        assert sum(r["stage"] == "classified" for r in res) == 2
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["stopped_by_error"] and "injected" in s["stopped_by_error"]
        rows = Registry(reg).fold()
        assert sum(1 for r in rows.values() if r.get("filter")) == 2

    def test_torn_multibyte_line_recoverable_from_cli(self, cand_dir):
        """Re-review item 4, through the recovery command."""
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        torn = '{"key": "naïve#1", "label": "naï'.encode("utf-8")[:-1]  # cut inside the ï
        with open(reg, "ab") as fh:
            fh.write(torn)
        _submit(reg, ["timid"])
        assert gap_registry.main(["--registry", str(reg), "compact", "--set-aside-malformed"]) == 0
        rejected = list(cand_dir.glob("registry.jsonl.rejected.*"))
        assert len(rejected) == 1 and rejected[0].read_bytes() == torn + b"\n"
        assert set(Registry(reg).fold()) == {"stubborn#1", "timid#1"}

    def test_dry_run_prints_even_when_budget_would_refuse(self, cand_dir, fake_client, capsys):
        """Review finding 12: --dry-run shows the plan and prompts, and says the
        real run would be refused, instead of refusing before printing."""
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        rc = traithood_filter.main([*SINGLE, "--batch-id", "b7", "--unfiltered", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--budget-usd", "0.00001", "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0 and "--- prompt 1 ---" in out and "would be REFUSED" in out

    def test_run_selector_syntax(self):
        with pytest.raises(SystemExit):
            traithood_filter.build_parser().parse_args(["--batch-id", "b", "--run", "no-slash"])


class TestGapRegistryCLI:
    def test_submit_status_holding_compact(self, tmp_path, cand_dir, capsys):
        reg = cand_dir / "registry.jsonl"
        f = tmp_path / "c.jsonl"
        f.write_text("".join(json.dumps(r) + "\n" for r in [
            {"surface": "world-shaping", "rank": 1, "score": 0.7, "source_ref": "oewn:1-a",
             "gloss_hint": "shaping the world"},
            {"surface": "tall", "rank": 2},
            {"surface": "world shaping", "rank": 3, "source_ref": "oewn:2-a"}]))
        assert gap_registry.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "wordnet_walk",
                                  "--run-id", "r1"]) == 0
        out = capsys.readouterr().out
        rep = json.loads(out.strip().splitlines()[-1])
        assert rep["n_new"] == 2 and rep["n_merged"] == 1
        assert (cand_dir / "runs" / "wordnet_walk" / "r1" / "usage.json").exists()
        Registry(reg).update("tall#1", {"holding": "physical", "gloss": "This means being tall.",
                                        "filter": {"verdict": "tagged", "tags": ["physical"]}})
        assert gap_registry.main(["--registry", str(reg), "status"]) == 0
        out = capsys.readouterr().out
        assert "2 rows" in out and '"unfiltered": 1' in out and '"wordnet_walk": 2' in out
        assert gap_registry.main(["--registry", str(reg), "holding", "--list", "physical"]) == 0
        out = capsys.readouterr().out
        assert "- **tall** (physical" in out and "TRAITS_TO_ADD" in out
        assert gap_registry.main(["--registry", str(reg), "report"]) == 0
        assert "| world_shaping#1 | world-shaping |" in capsys.readouterr().out
        assert gap_registry.main(["--registry", str(reg), "compact"]) == 0
        assert (cand_dir / "registry.snapshot.jsonl").exists()
        assert list(cand_dir.glob("registry.jsonl.bak.*"))
        assert len(reg.read_text().splitlines()) == 2

    def test_compact_cli_refuses_torn_log_then_sets_aside(self, cand_dir, capsys):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        with open(reg, "a") as fh:
            fh.write('{"key": "va')
        _submit(reg, ["vain"])
        assert gap_registry.main(["--registry", str(reg), "status"]) == 0
        assert "1 malformed line(s)" in capsys.readouterr().out
        assert gap_registry.main(["--registry", str(reg), "compact"]) == 1
        assert gap_registry.main(["--registry", str(reg), "compact", "--set-aside-malformed"]) == 0
        assert "moved to" in capsys.readouterr().out
        assert set(Registry(reg).fold()) == {"stubborn#1", "vain#1"}

    def test_submit_dry_run(self, tmp_path, cand_dir):
        reg = cand_dir / "registry.jsonl"
        f = tmp_path / "c.jsonl"
        f.write_text(json.dumps({"surface": "vain"}) + "\n")
        assert gap_registry.main(["--registry", str(reg), "submit", "--file", str(f), "--generator", "g",
                                  "--run-id", "r", "--dry-run"]) == 0
        assert not reg.exists()

    def test_promote_dry_run_leaves_queue_byte_identical(self, tmp_path, cand_dir, capsys):
        data = tmp_path / "data"
        for et in ("traits", "roles"):
            (data / et / "instructions").mkdir(parents=True)
        (data / "traits" / "instructions" / "stubborn.json").write_text("{}")
        q = tmp_path / "seed_queue.json"
        q.write_text(json.dumps({"_meta": {}, "entries": []}, indent=1) + "\n")
        raw = q.read_bytes()
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "world-shaping", "tall"])
        Registry(reg).update_many({
            "stubborn#1": {"filter": {"verdict": "trait", "tags": []}, "review": {"status": "accepted"}},
            "world_shaping#1": {"filter": {"verdict": "trait", "tags": []}, "gloss": "This means ...",
                                "review": {"status": "accepted"}},
            "tall#1": {"filter": {"verdict": "tagged", "tags": ["physical"]}, "holding": "physical",
                       "review": {"status": "accepted"}}})
        reg_raw = reg.read_bytes()
        rc = gap_registry.main(["--registry", str(reg), "--data-dir", str(data), "promote", "--status", "accepted",
                                "--queue", str(q), "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0 and q.read_bytes() == raw and reg.read_bytes() == reg_raw
        assert "WOULD PROMOTE world_shaping#1" in out
        assert "REFUSED stubborn#1: stem exists in the corpus" in out
        assert "REFUSED tall#1: on the physical holding list" in out

    def test_promote_writes_queue_and_registry(self, tmp_path, cand_dir):
        data = tmp_path / "data"
        for et in ("traits", "roles"):
            (data / et / "instructions").mkdir(parents=True)
        q = tmp_path / "seed_queue.json"
        q.write_text(json.dumps({"_meta": {}, "entries": []}))
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["world-shaping"])
        Registry(reg).update("world_shaping#1", {"filter": {"verdict": "trait", "tags": []}, "gloss": "g"})
        assert gap_registry.main(["--registry", str(reg), "--data-dir", str(data), "promote", "--keys",
                                  "world_shaping#1", "--queue", str(q)]) == 0
        entries = json.loads(q.read_text())["entries"]
        assert [e["stem"] for e in entries] == ["world_shaping"] and entries[0]["status"] == "candidate"
        assert Registry(reg).get("world_shaping#1")["seed_queue_stem"] == "world_shaping"


class TestBuildValidationSet:
    def test_strata_and_dedupe(self, tmp_path):
        from data_analysis.gap_generation.build_validation_set import build_rows

        data = tmp_path / "data"
        for et in ("traits", "roles"):
            (data / et / "instructions").mkdir(parents=True)
        for stem, label in [("stubborn", "stubborn"), ("openness_big_five", "openness (Big Five)"),
                            ("balanced", "balanced")]:
            (data / "traits" / "instructions" / f"{stem}.json").write_text(json.dumps({"positive_label": label}))
        queue = {"entries": [
            {"stem": "tall", "label": "tall", "entity_type": "trait", "status": "candidate", "tags": ["physical"]},
            {"stem": "aloof", "label": "aloof", "entity_type": "trait", "status": "not_adopted"},
            {"stem": "stubborn", "label": "stubborn", "entity_type": "trait", "status": "not_adopted"},
            {"stem": "economic", "label": "economic", "entity_type": "trait", "status": "not_adopted"}]}
        adjs = ["hexagonal", ".22 caliber", "tall", "aloof", "stubborn", "blue", "green", "Parisian"]
        rows, notes = build_rows(data, queue, adjs, n_oewn=10, seed=0)
        by = {}
        for r in rows:
            by.setdefault(r["stratum"], []).append(r["surface"])
        assert "balanced" not in by["rejects"] and notes["rejects_now_in_corpus"] == ["balanced"]
        assert by["rejects"] == ["disciplinary", "engaging", "economic", "empowered", "emotive"]
        assert sorted(by["existing"]) == ["balanced", "openness (Big Five)", "stubborn"]
        assert by["physical"] == ["tall"] and by["not_adopted"] == ["aloof"]
        assert notes["not_adopted_in_corpus"] == ["stubborn"]
        assert sorted(by["oewn_random"], key=str.lower) == ["blue", "green", "hexagonal", "Parisian"]
        assert len({r["surface"].lower() for r in rows}) == len(rows)


# --------------------------------------------------------------------------- setup_external --hf-model (M2)

def test_setup_external_hf_model_dry_run(capsys):
    from data_analysis.gap_generation import setup_external
    assert setup_external.main(["--hf-model", "BAAI/bge-large-en-v1.5", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "data/external/hf" in out and "model.safetensors" in out


def test_setup_external_unknown_model_refused(capsys):
    from data_analysis.gap_generation import setup_external
    assert setup_external.main(["--hf-model", "org/unknown", "--dry-run"]) == 2
    assert "HF_ALLOW_PATTERNS" in capsys.readouterr().err


# --------------------------------------------------------------------------- calibrate_metric.py (M2)

def _calib_args(tmp_path, *extra):
    return ["--models", "hash", "--representations", "full", "strip", "--variants", "raw", "centred",
            "--out", str(tmp_path / "cal"), "--cache-dir", str(tmp_path / "cache"),
            "--marks-sheet", str(tmp_path / "marks.md"), "--vectors-dir", str(tmp_path / "no_vectors"),
            "--skip-llm", "--allow-dirty", *extra]


def test_calibrate_dry_run_writes_nothing(tmp_path, capsys):
    from data_analysis.gap_generation import calibrate_metric
    assert calibrate_metric.main(_calib_args(tmp_path, "--dry-run")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "cost estimate" in out
    assert not (tmp_path / "cal").exists() and not (tmp_path / "cache").exists()


def test_calibrate_write_config_refuses_without_recorded_outputs(tmp_path, capsys):
    # task 19 (Roger's go, 2026-10-02): --write-config builds the config from the recorded calibration outputs
    from data_analysis.gap_generation import calibrate_metric
    args = _calib_args(tmp_path, "--write-config", "--config-out", str(tmp_path / "metric_config.json"))
    assert calibrate_metric.main(args) == 2
    assert "retrieval_round4.json" in capsys.readouterr().err
    assert not (tmp_path / "metric_config.json").exists()


def test_calibrate_end_to_end_with_hash_embedder(tmp_path):
    from data_analysis.gap_generation import calibrate_metric
    assert calibrate_metric.main(_calib_args(tmp_path, "--no-residual")) == 0
    cal = tmp_path / "cal"
    for name in ("loo_metrics.json", "loo_table.md", "hubness.json", "thresholds.json", "contrast_ablation.json", "summary.json",
                 "run.json", "usage.json", "drop_or_merge.md", "nn_hist_hash.png", "labelled_pairs.json",
                 "contrast_cuts.json", "contrast_comparisons_key.json"):
        assert (cal / name).exists(), name
    loo = json.loads((cal / "loo_metrics.json").read_text())
    assert "_provenance" in loo
    rows = loo["result"]["rows"]
    assert {(r["representation"], r["variant"]) for r in rows} == {(a, b) for a in ("full", "strip")
                                                                   for b in ("raw", "centred")}
    assert all(r["auc_dup_vs_distinct"] is not None for r in rows if r["metric"] == "cos")
    usage = json.loads((cal / "usage.json").read_text())
    assert usage["n_calls"] >= 1 and usage["total_cost_usd"] == 0
    abl = json.loads((cal / "contrast_ablation.json").read_text())["result"]["hash"]["centred"]
    assert abl["criteria_status"]["e"].startswith("skipped") and abl["recommendation"]["recommendation"] in ("keep", "strip")
    assert (tmp_path / "marks.md").read_text().count("Mark (A / B / same)") == 30


def test_calibrate_usage_is_cumulative_over_runs(tmp_path):
    from data_analysis.gap_generation import calibrate_metric
    args = _calib_args(tmp_path, "--no-residual")
    assert calibrate_metric.main(args) == 0
    first = json.loads((tmp_path / "cal" / "usage.json").read_text())
    assert first["n_calls"] >= 1
    assert calibrate_metric.main(args) == 0          # all cached: no new calls
    second = json.loads((tmp_path / "cal" / "usage.json").read_text())
    assert second["n_calls"] == first["n_calls"]
    run = json.loads((tmp_path / "cal" / "run.json").read_text())
    assert run["usage_this_run"]["n_calls"] == 0


def test_calibrate_dup_and_partial_whitening(tmp_path):
    from data_analysis.gap_generation import calibrate_metric
    args = ["--models", "hash", "--representations", "full", "dup", "strip", "--variants", "centred", "pw2",
            "--out", str(tmp_path / "cal"), "--cache-dir", str(tmp_path / "cache"), "--marks-sheet",
            str(tmp_path / "marks.md"), "--vectors-dir", str(tmp_path / "none"), "--skip-llm", "--allow-dirty"]
    assert calibrate_metric.main(args) == 0
    loo = json.loads((tmp_path / "cal" / "loo_metrics.json").read_text())["result"]
    reps = {(r["representation"], r["variant"]) for r in loo["rows"]}
    assert ("dup", "pw2") in reps and ("full", "pw2") in reps
    # dup leaves the corpus side as written: the leave-one-out NN geometry equals full's
    gl = {(g["representation"], g["variant"]): g for g in loo["gloss_recovery"]}
    assert gl[("dup", "centred")]["n"] == gl[("full", "centred")]["n"]
    assert any(r.get("metric") == "resid_20" and r["variant"] == "pw2" for r in loo["rows"])


def test_calibrate_paraphrase_stage_with_fake_haiku(tmp_path, monkeypatch):
    """--llm-criteria g: paraphrases from a fake client, cached, embedded, and turned into
    paraphrase recall, the covered threshold, criterion (i) and the two settings; (e) not run."""
    from data_analysis.gap_generation import calibrate_metric

    def responder(kw):
        rows = [json.loads(x) for x in user_text(kw).splitlines()]
        res = [{"id": r["id"], "reason": "keep it", "paraphrase": "This means, put otherwise, "
                + r["description"][len("This means "):]} for r in rows]
        return make_response(json.dumps({"results": res}), input_tokens=1500, output_tokens=1500)
    fake = FakeAsyncAnthropic(responder)
    monkeypatch.setattr(calibrate_metric, "_anthropic_client", lambda: fake)
    args = ["--models", "hash", "--representations", "full", "w14", "--variants", "centred",
            "--out", str(tmp_path / "cal"), "--cache-dir", str(tmp_path / "cache"), "--marks-sheet",
            str(tmp_path / "marks.md"), "--vectors-dir", str(tmp_path / "none"), "--llm-criteria", "g",
            "--allow-dirty", "--budget-usd", "1.0"]
    assert calibrate_metric.main(args) == 0
    cal = tmp_path / "cal"
    para = json.loads((cal / "paraphrases.json").read_text())
    n = _corpus_n()
    assert para["prompt_version"] == 2 and para["n"] == n
    usage = json.loads((cal / "usage.json").read_text())
    assert "claude-haiku-4-5-20251001" in usage["per_model"]
    assert all("sonnet" not in m for m in usage["per_model"])           # (e) not run
    pm = json.loads((cal / "paraphrase_metrics.json").read_text())["result"]
    assert {r["query"] for r in pm["recall_and_covered"]} == {"label", "no_label", "no_label_14w"}
    assert pm["heldout_directional"] and pm["heldout_directional"][0]["n"] == n
    summ = json.loads((cal / "summary.json").read_text())["result"]
    assert set(summ["settings"]) == {"covered", "directional"}
    assert summ["proposed_metric_config"]["covered"]["thresholds"]["hash"]["t_hi"] is not None
    assert not (tmp_path / "cal" / "metric_config.json").exists()
    abl = json.loads((cal / "contrast_ablation.json").read_text())["result"]
    # contrast ablation needs strip; with full only, (e) is reported as waiting for Roger
    assert abl == {}          # no strip representation in this run: no ablation, no draw


def test_calibrate_metric_default_models_drop_bge():
    # Roger, 2026-10-02: bge is dropped from round 4 on (its recorded outputs stay; "--models bge" still runs it)
    from data_analysis.gap_generation import calibrate_metric as CM
    assert CM.parse_args([]).models == ["openai", "gemma"]
    assert CM.parse_args(["--models", "bge"]).models == ["bge"]


# --------------------------------------------------------------------------- calibrate_metric.py --round4 (M2 round 4)

def _paraphrase_responder(kw):
    rows = [json.loads(x) for x in user_text(kw).splitlines()]
    res = [{"id": r["id"], "reason": "keep it", "paraphrase": "This means, put otherwise, "
            + r["description"][len("This means "):]} for r in rows]
    return make_response(json.dumps({"results": res}), input_tokens=1500, output_tokens=1500)


def _round4_args(tmp_path, *extra):
    return ["--round4", "--models", "hash", "--out", str(tmp_path / "cal"), "--cache-dir", str(tmp_path / "cache"),
            "--allow-dirty", "--bootstrap-n", "100", *extra]


def test_round4_defaults_and_dry_run_writes_nothing(tmp_path, capsys):
    from data_analysis.gap_generation import calibrate_metric as CM
    a = CM.parse_args(["--round4"])
    assert a.round4 and a.representations is None and a.variants is None and a.query_sources is None
    assert a.bootstrap_n == 2000 and a.seed == 0
    assert CM.main(_round4_args(tmp_path, "--dry-run", "--budget-usd", "10")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "round 4" in out and "cost estimate" in out
    # nothing cached in the empty out dir: all three paraphrase sets would be generated (3 x the corpus),
    # estimated as one pooled count of batches
    assert f"round 4 styled paraphrases: {_paraphrase_calls(3 * _corpus_n())} x" in out
    for src in ("paraphrase", "plain", "terse", "m1_gloss_1", "m1_gloss_2"):
        assert f"source {src} " in out
    assert "['w14', 'w20']" in out and "pw24" in out
    assert not (tmp_path / "cal").exists() and not (tmp_path / "cache").exists()


def test_round4_end_to_end_with_fake_haiku_and_hash_embedder(tmp_path, monkeypatch):
    from data_analysis.gap_generation import calibrate_metric as CM
    fake = FakeAsyncAnthropic(_paraphrase_responder)
    monkeypatch.setattr(CM, "_anthropic_client", lambda: fake)
    assert CM.main(_round4_args(tmp_path, "--budget-usd", "10", "--variants", "centred", "pw8")) == 0
    cal = tmp_path / "cal"
    n = _corpus_n()
    for style, name in (("standard", "paraphrases.json"), ("plain", "paraphrases_plain.json"),
                        ("terse", "paraphrases_terse.json")):
        d = json.loads((cal / name).read_text())
        assert d["style"] == style and d["n"] == n and d["prompt_version"] == CM.CL.paraphrase_version(style)
        assert d["prompt_sha256"] == CM._sha256(CM.CL.paraphrase_prompt(style))
        assert set(d["sources"]) == set(d["paraphrases"])     # what each paraphrase was written from
    usage = json.loads((cal / "usage.json").read_text())
    assert usage["per_model"][HAIKU]["n_calls"] == 3 * _paraphrase_calls(n)   # each style batched on its own
    run = json.loads((cal / "run_round4.json").read_text())
    assert run["round"] == 4 and run["models_run"] == ["hash"]
    assert set(run["rubric_versions"]) == {"calibration_paraphrase", "calibration_paraphrase_plain",
                                           "calibration_paraphrase_terse"}
    n_same = len(CM.RT.plain_reading_same(CM._REPO_ROOT / CM.RT.PLAIN_READING_COMPARISON))   # 591 labels
    assert run["n_queries"]["paraphrase"] == n and 0 < run["n_queries"]["m1_gloss_1"] <= n_same
    env = json.loads((cal / "retrieval_round4.json").read_text())
    assert "_provenance" in env
    res = env["result"]
    assert res["n_queries"]["pooled"] == sum(run["n_queries"].values())
    cells = {(r["representation"], r["variant"]) for r in res["recall"] if r["source"] == "pooled"}
    assert cells == {(r, v) for r in ("w14", "w20") for v in ("centred", "pw8")}
    assert {c["setting"] for c in res["comparisons"]} == {"w14|pw8", "w20|centred"}
    assert {c["setting"] for c in res["comparisons_within"]} == {"w20|pw8"}
    assert set(res["ks"]) == {1, 3, 5, 10, 20}
    assert all("p_holm" in c and "real" in c for c in res["comparisons"])
    assert res["union"] == []                       # one model: no merged lists
    assert res["antonym_pairs"] > 0 and res["threshold_design"]
    md = (cal / "retrieval_round4.md").read_text()
    assert "## Pooled recall@k" in md and "M1 gloss, run 2" in md
    # a rerun from the caches makes no Haiku call
    calls = usage["per_model"][HAIKU]["n_calls"]
    assert CM.main(_round4_args(tmp_path, "--budget-usd", "10", "--variants", "centred")) == 0
    assert json.loads((cal / "usage.json").read_text())["per_model"][HAIKU]["n_calls"] == calls


def test_round4_skip_llm_uses_only_what_is_cached(tmp_path):
    from data_analysis.gap_generation import calibrate_metric as CM
    args = _round4_args(tmp_path, "--skip-llm", "--variants", "centred", "--representations", "w14",
                        "--query-sources", "plain", "m1_gloss_2")
    assert CM.main(args) == 0
    res = json.loads((tmp_path / "cal" / "retrieval_round4.json").read_text())["result"]
    assert set(res["n_queries"]) == {"pooled", "m1_gloss_2"} and res["comparisons"] == []
    assert not (tmp_path / "cal" / "paraphrases_plain.json").exists()


def test_round4_refuses_a_cache_from_another_prompt_version(tmp_path, capsys):
    from data_analysis.gap_generation import calibrate_metric as CM
    (tmp_path / "cal").mkdir()
    (tmp_path / "cal" / "paraphrases_terse.json").write_text(json.dumps(
        {"style": "terse", "prompt_version": 99, "paraphrases": {"absentee": "This means gone."}}))
    assert CM.main(_round4_args(tmp_path, "--skip-llm", "--query-sources", "terse", "--dry-run")) == 2
    assert "prompt version 99" in capsys.readouterr().err


def _mini_ci():
    corpus = {"calm": {"label": "calm", "description": "This means staying calm."},
              "strict": {"label": "strict", "description": "This means being strict with people."},
              "neat": {"label": "neat", "description": "This means keeping things tidy."}}
    stems = sorted(corpus)
    return {"corpus": corpus, "stems": stems, "index": {s: i for i, s in enumerate(stems)}}


def test_paraphrases_of_a_changed_text_are_stale(tmp_path):
    """2026-10-02 (merge with the main line rewrote 13 descriptions): a cached paraphrase whose recorded source
    is not the trait's current label and description is stale; one with no recorded source is kept."""
    from data_analysis.gap_generation import calibrate_metric as CM
    ci = _mini_ci()
    p = tmp_path / "paraphrases.json"
    cached = {"calm": "This means keeping cool.", "strict": "This means being tough.", "neat": "This means tidy.",
              "gone": "This means a trait no longer in the corpus."}
    p.write_text(json.dumps({"paraphrases": cached, "sources": {
        "calm": CM.paraphrase_source("calm", "This means staying calm."),
        "strict": CM.paraphrase_source("tough", "This means being tough on people.")}}))
    fresh, stale = CM.fresh_paraphrases(p, cached, ci)
    assert fresh == {"calm": "This means keeping cool.", "neat": "This means tidy."} and stale == ["strict"]


def test_paraphrase_stage_records_sources_and_keeps_old_entries(tmp_path, monkeypatch):
    from data_analysis.gap_generation import calibrate_metric as CM
    from assistant_axis.gapgen.cost import GuardedUsage
    ci = _mini_ci()
    monkeypatch.setattr(CM, "_anthropic_client", lambda: FakeAsyncAnthropic(_paraphrase_responder))
    p = tmp_path / "paraphrases_terse.json"
    p.write_text(json.dumps({"style": "terse", "prompt_version": CM.CL.paraphrase_version("terse"),
                             "paraphrases": {"tough": "This means an old stem's paraphrase.",
                                             "strict": "This means stale."},
                             "sources": {"tough": "x", "strict": "y"}, "sources_note": "backfilled"}))
    merged = CM.run_paraphrase_stage(ci, ["strict"], p, {"calm": "This means cool."}, GuardedUsage(budget_usd=1.0),
                                     style="terse")
    d = json.loads(p.read_text())
    assert merged == d["paraphrases"] and d["paraphrases"]["tough"] == "This means an old stem's paraphrase."
    assert d["paraphrases"]["strict"].startswith("This means, put otherwise, being strict")
    assert d["sources"]["strict"] == CM.paraphrase_source("strict", "This means being strict with people.")
    assert d["sources"]["tough"] == "x" and "calm" not in d["sources"] and d["sources_note"] == "backfilled"
    assert CM.fresh_paraphrases(p, d["paraphrases"], ci)[1] == []


def test_round4_rebuild_labels_dry_run_writes_nothing(tmp_path, capsys):
    from data_analysis.gap_generation import calibrate_metric as CM
    assert CM.main(_round4_args(tmp_path, "--skip-llm", "--rebuild-labels", "--query-sources", "m1_gloss_2",
                                "--dry-run")) == 0
    out = capsys.readouterr().out
    assert "labelled pairs rebuilt from the current corpus" in out and "'antonym'" in out
    assert not (tmp_path / "cal").exists()


# --------------------------------------------------------------------------- calibrate_metric.py --write-config (task 19)

RECORDED = ("retrieval_round4.json", "paraphrase_metrics.json", "loo_metrics.json")


def _write_config_args(tmp_path, *extra):
    import shutil
    from assistant_axis.gapgen.paths import CALIBRATION_DIR
    cal = tmp_path / "cal"
    cal.mkdir(exist_ok=True)
    for name in RECORDED:
        if not (CALIBRATION_DIR / name).exists():
            pytest.skip(f"{name} not recorded")
        shutil.copy(CALIBRATION_DIR / name, cal / name)
    return ["--write-config", "--models", "hash", "--out", str(cal), "--cache-dir", str(tmp_path / "cache"),
            "--config-out", str(tmp_path / "metric_config.json"), "--allow-dirty", *extra]


def test_write_config_dry_run_writes_nothing(tmp_path, capsys):
    from data_analysis.gap_generation import calibrate_metric as CM
    assert CM.main(_write_config_args(tmp_path, "--dry-run")) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN" in out and "covered: w20 centred cos k=10" in out and "K=10" in out
    assert not (tmp_path / "metric_config.json").exists()
    assert sorted(p.name for p in (tmp_path / "cal").iterdir()) == sorted(RECORDED)


def test_write_config_end_to_end(tmp_path, monkeypatch):
    from assistant_axis.gapgen.metric_config import MetricConfig, validate_payload
    from data_analysis.gap_generation import calibrate_metric as CM
    monkeypatch.setattr(CM.EM, "canary_applies", lambda e: True)     # let the hash embedder run the canary
    assert CM.main(_write_config_args(tmp_path)) == 0
    env = json.loads((tmp_path / "metric_config.json").read_text())
    assert "_provenance" in env
    validate_payload(env["result"])
    cfg = MetricConfig.load(path=tmp_path / "metric_config.json")
    assert (cfg.representation, cfg.space["variant"], cfg.covered["metric"], cfg.k) == ("w20", "centred", "cos", 10)
    assert (cfg.directional["representation"], cfg.directional["K"]) == ("w20", 10)
    assert cfg.live_model["model_id"] == "text-embedding-3-large" and cfg.fallback_model["active"] is False
    assert cfg.thresholds["used_for_decisions"] is False
    assert cfg.covered["retrieval"]["target"]["met"] is True
    assert len(cfg.canary["texts"]) == 8 and cfg.canary["check_at_write"]["hash"]["n"] == 8
    run = json.loads((tmp_path / "cal" / "run_write_config.json").read_text())
    assert run["read_back"]["valid"] and run["canary"]["hash"]["ok"]
    assert json.loads((tmp_path / "cal" / "usage.json").read_text())["n_calls"] == 1     # the canary call


def test_write_config_keeps_the_written_canary(tmp_path, monkeypatch):
    """2026-10-02: a rewrite keeps the config's canary texts even when the corpus changed (the rule would pick
    others), as embed.canary_texts promises."""
    from assistant_axis.gapgen.metric_config import MetricConfig
    from data_analysis.gap_generation import calibrate_metric as CM
    assert CM.main(_write_config_args(tmp_path)) == 0
    first = MetricConfig.load(path=tmp_path / "metric_config.json").canary["texts"]
    real = CM.corpus_inputs

    def fewer(repo):                     # a corpus edit: drop the first few stems, so the rule would move
        ci = real(repo)
        keep = ci["stems"][5:]
        corpus = {s: ci["corpus"][s] for s in keep}
        return {**ci, "corpus": corpus, "stems": keep, "labels": [corpus[s]["label"] for s in keep],
                "descriptions": [corpus[s]["description"] for s in keep], "index": {s: i for i, s in enumerate(keep)}}
    monkeypatch.setattr(CM, "corpus_inputs", fewer)
    moved = CM.EM.canary_texts(fewer(CM._REPO_ROOT)["stems"], ["x"] * len(fewer(CM._REPO_ROOT)["stems"]))
    assert [c["stem"] for c in moved] != [c["stem"] for c in first]
    assert CM.main(_write_config_args(tmp_path)) == 0
    assert MetricConfig.load(path=tmp_path / "metric_config.json").canary["texts"] == first


def test_embedding_runs_check_the_canary(tmp_path, monkeypatch):
    from data_analysis.gap_generation import calibrate_metric as CM
    monkeypatch.setattr(CM.EM, "canary_applies", lambda e: True)
    args = _round4_args(tmp_path, "--skip-llm", "--variants", "centred", "--representations", "w14",
                        "--query-sources", "m1_gloss_2", "--config-out", str(tmp_path / "no_config.json"))
    assert CM.main(args) == 0
    run = json.loads((tmp_path / "cal" / "run_round4.json").read_text())
    can = run["canary"]["hash"]
    assert can["n"] == 8 and can["ok"] and can["n_new_reference"] + can["n_compared"] == 8
    assert CM.main(args) == 0                                        # second run compares against the references
    can = json.loads((tmp_path / "cal" / "run_round4.json").read_text())["canary"]["hash"]
    assert can["n_compared"] == 8 and can["min_cosine"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- overlap_test.py (M3 overlap rubric test)

def _overlap_inputs(tmp_path):
    """Synthetic inputs (the library test's corpus, space and labelled pairs) with real files to fingerprint."""
    from assistant_axis.gapgen import overlap_test as OT
    from assistant_axis.tests import test_gapgen_overlap_test as T
    stems, Z = T.space()
    files = {}
    for k in ("metric_config", "embedding_cache", "labelled_pairs", "drop_or_merge", "persona_cache"):
        files[k] = tmp_path / "inputs" / f"{k}.txt"
        files[k].parent.mkdir(parents=True, exist_ok=True)
        files[k].write_text(k)
    return OT.Inputs(corpus=T.corpus(), emb_stems=stems, Z=Z, persona=T.persona(),
                     persona_info={"slot": 6, "layer": 25, "shear_applied": True, "n_traits_in_corpus": 6},
                     labelled=list(T.LABELLED), dm_pairs=list(T.DM), partner=dict(T.PARTNER),
                     settings={"model": "text-embedding-3-large", "representation": "w20", "variant": "centred"},
                     paths=files)


@pytest.fixture
def overlap_env(tmp_path, monkeypatch, fake_client):
    """The CLI on synthetic inputs and a fake client.  Rubric A is loaded at version 4 (the list form, the
    library test's ``list_rubrics``), as every run before round 3 sent it; ``e["single_form"]()`` puts the
    pinned rubric A back (version 6, one pair per call) for the round-3 tests."""
    from data_analysis.gap_generation import overlap_test as cli
    from assistant_axis.gapgen import overlap_test as OT
    from assistant_axis.tests import test_gapgen_overlap_test as T
    monkeypatch.setattr(OT, "load_inputs", lambda *a, **k: _overlap_inputs(tmp_path))
    monkeypatch.setattr(OT, "load_rubrics", T.list_rubrics)
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc1234")
    fake_client["responder"] = T.responder_for(OT.load_rubrics(), value=2)
    base = ["--run-id", "t1", "--out-root", str(tmp_path / "out"), "--marks-sheet", str(tmp_path / "rep" / "marks.md"),
            "--n-targets", "4", "--n-antonyms", "2", "--n-random", "2", "--n-boot", "20"]
    return {"cli": cli, "OT": OT, "T": T, "base": base, "out": tmp_path / "out" / "t1", "client": fake_client,
            "sheet": tmp_path / "rep" / "marks.md",
            "single_form": lambda: monkeypatch.setattr(OT, "load_rubrics", T._LOAD_RUBRICS)}


def test_overlap_dry_run_prints_prompts_and_writes_nothing(overlap_env, capsys):
    e = overlap_env
    assert e["cli"].main(e["base"] + ["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "total estimate" in out and "DRY-RUN" in out
    assert "## Variant: normal" in out and "## Variant: antonym_in_list" in out and "## Variant: single" in out
    assert "--- system ---" in out and '"traits": [' in out
    assert not e["out"].exists() and not e["sheet"].exists() and "client" not in e["client"]


def test_overlap_knows_fable_and_refuses_an_unknown_model(overlap_env, capsys):
    """Fable 5.1 joined overlap_test_1 on 2026-10-04 (not a default); anything else is refused."""
    e = overlap_env
    assert e["cli"].main(e["base"] + ["--models", e["OT"].FABLE, "--rubrics", "A", "--dry-run"]) == 0
    assert "Fable 5.1" in capsys.readouterr().out
    assert e["cli"].main(e["base"] + ["--models", "claude-opus-4-1", "--dry-run"]) == 1
    assert "this test knows" in capsys.readouterr().err
    assert e["OT"].FABLE not in e["OT"].MODELS and e["OT"].FABLE in e["OT"].KNOWN_MODELS


def test_overlap_refuses_an_estimate_over_the_budget(overlap_env):
    e = overlap_env
    assert e["cli"].main(e["base"] + ["--budget-usd", "0.0001"]) == 2
    assert not e["out"].exists()


def test_overlap_end_to_end_with_a_fake_client(overlap_env):
    e = overlap_env
    OT = e["OT"]
    assert e["cli"].main(e["base"]) == 0
    out = e["out"]
    ps = OT.PairSet.from_json(json.loads((out / "pairs.json").read_text()))
    assert "_provenance" in json.loads((out / "pairs.json").read_text())
    n_calls, n_pairs = len(ps.calls), len(ps.pairs)
    client = e["client"]["client"]
    assert len(client.calls) == n_calls * 6                          # one call per target per (rubric, model)
    recs = OT.read_records(out / "responses.jsonl")
    assert len(recs) == n_calls * 6
    assert {(r["rubric"], r["model"]) for r in recs} == {(r, m) for r in "AB" for m in OT.MODELS}
    assert len((out / "results.jsonl").read_text().splitlines()) == n_pairs * 6
    usage = json.loads((out / "usage.json").read_text())
    assert usage["n_calls"] == n_calls * 6 and set(usage["per_model"]) == set(OT.MODELS)
    run = json.loads((out / "run.json").read_text())
    assert len(run["stages"]) == 6 and [s["model"] for s in run["stages"]][:2] == [OT.HAIKU, OT.HAIKU]
    pinned = OT.load_rubrics()                                       # the latest pins, not a fixed number
    assert run["rubric_versions"] == {pinned[r]["name"]: pinned[r]["version"] for r in "AB"} and run["exit_code"] == 0
    summ = json.loads((out / "summary.json").read_text())
    assert "_provenance" in summ and summ["result"]["parse"][f"A|{OT.OPUS}"]["rate"] == 1.0
    assert (out / "tables.md").read_text().startswith("# Overlap test: tables")
    assert "## Variant: antonym_in_list" in (out / "rendered_prompts.md").read_text()
    sheet = e["sheet"].read_text()
    key = json.loads((out / "marks_key.json").read_text())
    assert sheet.count("Your answer (") == len(key["items"]) > 0
    assert "opus" not in sheet.lower() and "haiku" not in sheet.lower()


def test_overlap_corpus_at_reads_a_commits_trait_files(overlap_env, monkeypatch, tmp_path):
    """--corpus-at (coding_plan_haiku55.md, comparison C): the pair set is built from the trait files as committed
    at the given commit (overlap_arms_3's fc6d542: 663 files), recorded in run.json and the provenance; Haiku 5.5
    and Haiku 4.5 run side by side, 5.5 without temperature."""
    e = overlap_env
    OT, cli = e["OT"], e["cli"]
    seen = {}

    def capture(*a, **k):
        d = k.get("data_dir")
        seen.update(data_dir=d, corpus_at=k.get("corpus_at"),
                    n_files=len(list((Path(d) / "traits" / "instructions").glob("*.json"))) if d else None)
        inp = _overlap_inputs(tmp_path)
        inp.corpus_at = k.get("corpus_at")
        return inp
    monkeypatch.setattr(OT, "load_inputs", capture)
    e["single_form"]()
    e["client"]["responder"] = e["T"].single_answer(OT.load_rubrics(keys=("A",)))
    args = e["base"] + ["--rubrics", "A", "--models", OT.HAIKU55, OT.HAIKU, "--passes", "2", "--corpus-at", "fc6d542"]
    assert cli.main(args + ["--dry-run"]) == 0
    assert seen["corpus_at"] == "fc6d542" and seen["n_files"] == 663
    assert cli.main(args) == 0
    run = json.loads((e["out"] / "run.json").read_text())
    assert run["corpus_at"] == "fc6d542" and run["models"] == [OT.HAIKU55, OT.HAIKU] and run["exit_code"] == 0
    prov = json.loads((e["out"] / "pairs.json").read_text())["_provenance"]
    assert "fc6d542" in json.dumps(prov) and "trait_files" not in json.dumps(prov)
    sent = e["client"]["client"].calls
    assert {k["model"] for k in sent} == {OT.HAIKU55, OT.HAIKU}
    assert all("temperature" not in k for k in sent if k["model"] == OT.HAIKU55)
    assert all(k["temperature"] == 0.0 for k in sent if k["model"] == OT.HAIKU)
    # without the flag the working tree's trait files are read (no data_dir is passed)
    seen.clear()
    assert cli.main(e["base"] + ["--run-id", "t2", "--dry-run"]) == 0
    assert seen["data_dir"] is None and seen["corpus_at"] is None


def test_overlap_load_inputs_reads_the_corpus_from_data_dir(monkeypatch, tmp_path):
    from assistant_axis.gapgen import contrast as CT
    from assistant_axis.gapgen import overlap_test as OT

    class Stop(Exception):
        pass
    got = {}

    def fake(data_dir):
        got["dir"] = Path(data_dir)
        raise Stop
    monkeypatch.setattr(CT, "load_corpus_texts", fake)
    kw = dict(metric_config_path=REPO / "data" / "candidates" / "metric_config.json", cache_dir=tmp_path,
              vectors_dir=tmp_path, labelled_path=tmp_path / "l.json", dm_path=tmp_path / "d.md")
    with pytest.raises(Stop):
        OT.load_inputs(REPO, data_dir=tmp_path / "snap" / "data", **kw)
    assert got["dir"] == tmp_path / "snap" / "data"
    with pytest.raises(Stop):
        OT.load_inputs(REPO, **kw)
    assert got["dir"] == REPO / "data"


def test_overlap_a_second_run_leaves_the_marks_sheet_alone(overlap_env):
    """overlap_test_2 rewrote overlap_test_1's sheet (it checked only for its own key); a sheet that
    exists is never overwritten, whoever's it is, since it may hold Roger's marks."""
    e = overlap_env
    assert e["cli"].main(e["base"]) == 0
    marked = e["sheet"].read_text().replace("Your answer (0 / 1 / 2 / 3 / 4 / opposite / unsure): ",
                                            "Your answer (0 / 1 / 2 / 3 / 4 / opposite / unsure): 2", 1)
    e["sheet"].write_text(marked)
    second = [("t2" if a == "t1" else a) for a in e["base"]]
    assert e["cli"].main(second) == 0
    assert e["sheet"].read_text() == marked
    assert not (e["out"].parent / "t2" / "marks_key.json").exists()
    assert (e["out"] / "marks_key.json").exists()


def test_overlap_resume_and_existing_run(overlap_env):
    e = overlap_env
    assert e["cli"].main(e["base"] + ["--models", e["OT"].HAIKU]) == 0
    n_first = len(e["client"]["client"].calls)
    assert e["cli"].main(e["base"]) == 1                              # responses exist: needs --resume
    assert e["cli"].main(e["base"] + ["--resume"]) == 0
    assert len(e["client"]["client"].calls) == n_first * 2           # Sonnet and Opus only; Haiku not re-sent
    usage = json.loads((e["out"] / "usage.json").read_text())
    assert usage["n_calls"] == n_first * 3                            # cumulative over the two sessions


def test_overlap_stops_on_a_low_parse_rate(overlap_env):
    e = overlap_env
    e["client"]["responder"] = e["T"].responder_for(e["OT"].load_rubrics(), bad_model=e["OT"].HAIKU)
    assert e["cli"].main(e["base"]) == 3
    run = json.loads((e["out"] / "run.json").read_text())
    assert len(run["stages"]) == 1 and "parse rate" in run["stopped"]


def test_overlap_analyse_only_and_decode_marks(overlap_env, capsys):
    e = overlap_env
    assert e["cli"].main(e["base"]) == 0
    (e["out"] / "summary.json").unlink()
    assert e["cli"].main(e["base"] + ["--analyse-only"]) == 0
    assert (e["out"] / "summary.json").exists()
    sheet = e["sheet"].read_text()
    e["sheet"].write_text(sheet.replace("Your answer (0 / 1 / 2 / 3 / 4 / opposite / unsure): ",
                                        "Your answer (0 / 1 / 2 / 3 / 4 / opposite / unsure): 2"))
    assert e["cli"].main(e["base"] + ["--decode-marks"]) == 0
    dec = json.loads((e["out"] / "marks_decoded.json").read_text())
    assert dec["counts"] == {"ok": len(dec["items"])}
    assert dec["agreement_with_roger"][e["OT"].OPUS]["exact_all"] == 1.0      # the fake answers 2 everywhere


# --------------------------------------------------------------------------- the overlap rubric arms (2026-10-04)

def _arms(e):
    """The fake answers every rubric (A-E) in its own format, by the listed trait's label."""
    e["client"]["responder"] = e["T"].arms_responder(e["OT"].load_rubrics(keys=tuple(e["OT"].RUBRICS)))
    return e["OT"]


def test_overlap_arms_end_to_end_with_two_passes(overlap_env):
    """coding_plan_overlap_arms.md: --rubrics C D E --passes 2 on Sonnet and Opus."""
    e = overlap_env
    OT = _arms(e)
    models = (OT.SONNET, OT.OPUS)
    assert e["cli"].main(e["base"] + ["--models", *models, "--rubrics", "C", "D", "E", "--passes", "2"]) == 0
    out = e["out"]
    ps = OT.PairSet.from_json(json.loads((out / "pairs.json").read_text()))
    n_calls, n_pairs = len(ps.calls), len(ps.pairs)
    client = e["client"]["client"]
    assert len(client.calls) == n_calls * 3 * 2 * 2                   # rubrics x models x passes
    recs = OT.read_records(out / "responses.jsonl")
    assert {(r["rubric"], r["model"], r["pass"]) for r in recs} == {(r, m, p) for r in "CDE" for m in models
                                                                     for p in (1, 2)}
    users = {(r["rubric"], r["model"], r["call_id"], r["pass"]): r["request"]["user"] for r in recs}
    assert any(users[(k[0], k[1], k[2], 1)] != u for k, u in users.items() if k[3] == 2)    # pass 2 reshuffled
    results = [json.loads(x) for x in (out / "results.jsonl").read_text().splitlines()]
    assert len(results) == n_pairs * 3 * 2 * 2 and {r["pass"] for r in results} == {1, 2}
    assert all(r["decision"] == OT.decision_value(r["rubric"], r["value"]) for r in results)
    run = json.loads((out / "run.json").read_text())
    assert run["passes"] == 2 and run["rubrics"] == ["C", "D", "E"] and run["exit_code"] == 0
    assert run["rubric_versions"] == {"overlap_six": 1, "overlap_relation": 1, "overlap_scope": 1}
    assert [s["pass"] for s in run["stages"]] == [1] * 6 + [2] * 6
    assert [s["model"] for s in run["stages"]][:4] == [OT.SONNET] * 3 + [OT.OPUS]
    usage = json.loads((out / "usage.json").read_text())
    assert usage["n_calls"] == len(client.calls) == OT.usage_from_records(recs).n_calls
    arms = json.loads((out / "summary.json").read_text())["result"]["arms"]
    assert arms["rubrics"] == ["C", "D", "E"] and arms["passes"] == [1, 2]
    for r in "CDE":
        for m in models:
            # the fake answers by label: pass 2's reshuffled ids must land on the same pairs as pass 1's
            sc = arms["per_arm"][r]["self_consistency"][m]
            assert sc["native"]["n_both_parsed"] == n_pairs and sc["native"]["exact_all"] == 1.0
    assert len(arms["cross_arm"]) == 6
    tables = (out / "tables.md").read_text()
    assert "### Cross-arm table" in tables and "### Arm D: overlap_relation" in tables
    prompts = (out / "rendered_prompts.md").read_text()
    assert "## Pass 2: the same calls" in prompts and "=== rubric C (overlap_six)" in prompts
    assert "=== rubric A (" not in prompts                             # only the run's rubrics


def test_overlap_arms_dry_run_shows_every_arm_and_the_second_pass(overlap_env, capsys):
    e = overlap_env
    OT = e["OT"]
    assert e["cli"].main(e["base"] + ["--models", OT.SONNET, OT.OPUS, "--rubrics", "A", "C", "D", "E",
                                      "--passes", "2", "--dry-run"]) == 0
    out = capsys.readouterr().out
    for r, name in (("A", "overlap_concept"), ("C", "overlap_six"), ("D", "overlap_relation"), ("E", "overlap_scope")):
        assert f"=== rubric {r} ({name})" in out and f"rubric {r} ({name}) on Opus 5.5, pass 2" in out
    assert "## Pass 2: the same calls" in out and "passes 2" in out and "DRY-RUN" in out
    assert not e["out"].exists() and not e["sheet"].exists()


def test_overlap_a_second_pass_on_resume_sends_only_the_second_pass(overlap_env):
    e = overlap_env
    OT = _arms(e)
    base = e["base"] + ["--models", OT.SONNET, "--rubrics", "D"]
    assert e["cli"].main(base) == 0
    n1 = len(e["client"]["client"].calls)
    assert e["cli"].main(base + ["--passes", "2", "--resume"]) == 0
    assert len(e["client"]["client"].calls) == n1                       # pass 2 only; pass 1 not re-sent
    recs = OT.read_records(e["out"] / "responses.jsonl")
    assert sorted(r["pass"] for r in recs) == [1] * n1 + [2] * n1
    assert json.loads((e["out"] / "usage.json").read_text())["n_calls"] == 2 * n1


def test_overlap_a_baseline_run_with_other_pairs_is_refused(overlap_env, capsys):
    e = overlap_env
    other = e["out"].parent / "overlap_test_1"
    other.mkdir(parents=True)
    (other / "pairs.json").write_text(json.dumps(e["T"].pair_set(n_targets=3).to_json()))
    assert e["cli"].main(e["base"] + ["--dry-run"]) == 2
    assert "differs from overlap_test_1's pairs.json" in capsys.readouterr().err
    assert e["cli"].main(e["base"] + ["--dry-run", "--baseline-run", "none"]) == 0


def test_overlap_arm_a_is_compared_with_the_baseline_run(overlap_env):
    e = overlap_env
    OT = _arms(e)
    models = [OT.SONNET, OT.OPUS]
    first = [("overlap_test_1" if a == "t1" else a) for a in e["base"]] + ["--models", *models, "--rubrics", "A"]
    assert e["cli"].main(first) == 0
    baseline_responses = e["out"].parent / "overlap_test_1" / "responses.jsonl"
    before = baseline_responses.read_bytes()
    assert e["cli"].main(e["base"] + ["--models", *models, "--rubrics", "A", "C", "--passes", "2"]) == 0
    assert baseline_responses.read_bytes() == before                    # only read
    summ = json.loads((e["out"] / "summary.json").read_text())
    b = summ["result"]["arms"]["baseline"]
    assert b["run_id"] == "overlap_test_1" and set(b["per_model"]) == set(models)
    assert b["per_model"][OT.OPUS]["native"]["exact_all"] == 1.0         # the fake answers by label
    assert "baseline_responses" in json.dumps(summ["_provenance"])
    assert "### Arm A, pass 1, against overlap_test_1" in (e["out"] / "tables.md").read_text()


def test_overlap_a_second_live_session_is_refused_while_one_holds_the_lock(overlap_env, capsys):
    e = overlap_env
    OT = e["OT"]
    assert e["cli"].main(e["base"] + ["--models", OT.HAIKU]) == 0
    held = OT.acquire_session_lock(e["out"])
    try:
        assert e["cli"].main(e["base"] + ["--resume"]) == 4
        assert "another session" in capsys.readouterr().err
    finally:
        held.close()
    assert e["cli"].main(e["base"] + ["--resume"]) == 0


def test_overlap_arms_analyse_only_recomputes_everything(overlap_env):
    e = overlap_env
    OT = _arms(e)
    models = [OT.SONNET, OT.OPUS]
    assert e["cli"].main(e["base"] + ["--models", *models, "--rubrics", "E", "--passes", "2"]) == 0
    first = json.loads((e["out"] / "summary.json").read_text())["result"]["arms"]
    (e["out"] / "summary.json").unlink()
    (e["out"] / "tables.md").unlink()
    assert e["cli"].main(e["base"] + ["--models", *models, "--analyse-only"]) == 0
    again = json.loads((e["out"] / "summary.json").read_text())["result"]["arms"]
    assert again["cross_arm"] == first["cross_arm"] and again["passes"] == [1, 2]
    assert "### Arm E: overlap_scope" in (e["out"] / "tables.md").read_text()


# --------------------------------------------------------------------------- round 2 (2026-10-04): the subset

def _sources(e):
    """Two source runs under the out-root, as round 2's subset reads them: ``overlap_arms_1`` (A, C, D, E on
    Sonnet and Opus, two passes) and ``overlap_test_1`` (A and B on the three default models).  The fake
    answers 1 ("neighbours") with a plain reason, except: the first pair's ordered labels get a 2 from Sonnet
    and a 3 from Opus under A (rule 1); the last call's last pair gets "overlap" under D with a reason that
    describes a containment (rule 2); rubric B answers 2 or 3 on every pair (it never counts).  Returns the
    pair set and the subset's pair ids and call ids as the rule gives them."""
    OT, T = e["OT"], e["T"]
    ps = T.pair_set(n_targets=4, n_antonyms=2, n_random=2)
    confused, slipped = ps.pairs[0], [p for p in ps.pairs if p.call_id == ps.calls[-1].call_id][-1]
    assert confused.call_id != slipped.call_id
    lab = {s: T.corpus()[s]["label"] for s in T.corpus()}
    rb = OT.load_rubrics(keys=tuple(OT.RUBRICS))
    by_text = {v["text"]: k for k, v in rb.items()}
    slip = "Fussy eater is fussiness narrowed to food."

    def responder(kw):
        r = by_text[system_text(kw)]
        obj = json.loads(user_text(kw))
        rows = []
        for t in obj["traits"]:
            pair = (obj["target"]["label"], t["label"])
            v, why = ("neighbours" if r == "D" else 1), "Both are about speech."
            if r == "B":
                v = 3 if kw["model"] == OT.OPUS else 2
            elif r == "A" and pair == (lab[confused.target], lab[confused.listed]):
                v = 3 if kw["model"] == OT.OPUS else 2
            elif r == "D" and pair == (lab[slipped.target], lab[slipped.listed]):
                v, why = "overlap", slip
            rows.append({"id": t["id"], "reason": why, OT.RUBRICS[r]["key"]: v})
        return make_response(json.dumps({"results": rows}), input_tokens=900, output_tokens=150)
    e["client"]["responder"] = responder
    models = [OT.SONNET, OT.OPUS]
    r1 = [("overlap_arms_1" if a == "t1" else a) for a in e["base"]] + ["--models", *models, "--rubrics", "A", "C",
                                                                          "D", "E", "--passes", "2"]
    assert e["cli"].main(r1) == 0
    t1 = [("overlap_test_1" if a == "t1" else a) for a in e["base"]] + ["--rubrics", "A", "B"]
    assert e["cli"].main(t1) == 0
    want = {(confused.target, confused.listed), (slipped.target, slipped.listed)}
    pair_ids = [p.pair_id for p in ps.pairs if (p.target, p.listed) in want]
    held = {p.call_id for p in ps.pairs if p.pair_id in pair_ids}
    return ps, pair_ids, [c.call_id for c in ps.calls if c.call_id in held]


SOURCES = ["--subset-sources", "overlap_arms_1", "overlap_test_1"]


def test_overlap_write_subset_from_the_source_runs(overlap_env, capsys):
    e = overlap_env
    ps, pair_ids, call_ids = _sources(e)
    assert len(call_ids) < len(ps.calls)
    assert e["cli"].main(e["base"] + ["--write-subset"]) == 2                   # the default names overlap_test_2 too
    assert "subset source overlap_test_2 has no pairs.json" in capsys.readouterr().err
    assert e["cli"].main(e["base"] + ["--write-subset", "--dry-run"] + SOURCES) == 0
    assert "DRY-RUN" in capsys.readouterr().out and not (e["out"] / "subset.json").exists()
    assert e["cli"].main(e["base"] + ["--write-subset"] + SOURCES) == 0
    out = capsys.readouterr().out
    env = json.loads((e["out"] / "subset.json").read_text())
    assert "_provenance" in env and "responses_overlap_arms_1" in json.dumps(env["_provenance"])
    s = env["result"]
    assert s["pair_ids"] == pair_ids and s["call_ids"] == call_ids              # rubric B's 2s and 3s never count
    sent = [p.pair_id for p in ps.pairs if p.call_id in call_ids]
    assert s["control_pair_ids"] == [x for x in sent if x not in pair_ids]
    assert s["counts"]["n_pairs_sent"] == len(sent) and s["source_runs"] == ["overlap_arms_1", "overlap_test_1"]
    # every reading: round 1's 4 arms x 2 models x 2 passes, and overlap_test_1's A on 3 models
    assert s["counts"]["readings_per_pair"] == {"19": len(ps.pairs)}
    assert {x["rubric"] for x in s["sources"]} == {"A", "C", "D", "E"}
    assert f"confusion subset: {len(pair_ids)} pairs" in out
    assert e["cli"].main(e["base"] + ["--write-subset"] + SOURCES) == 0         # the same subset: left alone
    assert "left as it is" in capsys.readouterr().out
    assert e["cli"].main(e["base"] + ["--write-subset", "--subset-sources", "overlap_test_1"]) == 2   # another one
    assert "holds another subset" in capsys.readouterr().err
    assert e["cli"].main(e["base"] + ["--write-subset", "--subset-sources", "nope"]) == 2


def test_overlap_round_2_sends_only_the_subset_calls_and_compares_with_round_1(overlap_env, capsys):
    e = overlap_env
    ps, pair_ids, call_ids = _sources(e)
    assert e["cli"].main(e["base"] + ["--write-subset"] + SOURCES) == 0
    OT = _arms(e)
    models = (OT.SONNET, OT.OPUS)
    subset_path = str(e["out"] / "subset.json")
    args = e["base"] + ["--models", *models, "--rubrics", "A2", "C2", "D2", "E2", "--passes", "2",
                        "--calls-from", subset_path]
    capsys.readouterr()
    assert e["cli"].main(args + ["--dry-run"]) == 0
    dry = capsys.readouterr().out
    assert f"calls sent: {len(call_ids)} of {len(ps.calls)}" in dry and "DRY-RUN" in dry
    assert f"rubric A2 (overlap_concept_implies) on Opus 5.5, pass 2: {len(call_ids)} x" in dry
    assert "pair set: the same calls as overlap_test_1" in dry                  # the baseline check still applies
    assert e["cli"].main(args) == 0
    out = e["out"]
    client = e["client"]["client"]
    assert len(client.calls) == len(call_ids) * 4 * 2 * 2                       # rubrics x models x passes
    recs = OT.read_records(out / "responses.jsonl")
    assert {r["call_id"] for r in recs} == set(call_ids) and {r["rubric"] for r in recs} == set(OT.ROUND2)
    run = json.loads((out / "run.json").read_text())
    assert run["calls_from"]["call_ids"] == call_ids and run["calls_from"]["n_subset_pairs"] == len(pair_ids)
    assert run["rubric_versions"] == {OT.RUBRICS[r]["name"]: 1 for r in OT.ROUND2} and run["round1_run"] == "overlap_arms_1"
    assert run["pair_set"]["n_calls"] == len(ps.calls)                           # the pair set is unchanged
    sent = [p.pair_id for p in ps.pairs if p.call_id in call_ids]
    results = [json.loads(x) for x in (out / "results.jsonl").read_text().splitlines()]
    assert len(results) == len(sent) * 4 * 2 * 2
    assert {r["pair_id"] for r in results if r["in_subset"]} == set(pair_ids)
    assert {r["pair_id"] for r in results if not r["in_subset"]} == set(sent) - set(pair_ids)
    summ = json.loads((out / "summary.json").read_text())
    res = summ["result"]
    assert res["n_calls"] == len(call_ids) and res["n_pairs"] == len(sent)          # the calls sent
    assert res["sent"]["of_calls"] == len(ps.calls) and res["subset"]["n_pairs"] == len(pair_ids)
    r2 = res["round2"]
    assert r2["round1_run"] == "overlap_arms_1" and r2["arms"] == list(OT.ROUND2)
    assert r2["populations"]["subset"]["n_pairs"] == len(pair_ids) and r2["populations"]["sent"]["n_pairs"] == len(sent)
    one = r2["per_population"]["subset"]["A2"]["round1"]
    # round 1 on the subset's pairs: Sonnet 2 / Opus 3 on the confused pair(s) under A, in both passes
    n_confused = sum(1 for x in pair_ids if x in [p.pair_id for p in ps.pairs
                                                   if (p.target, p.listed) == (ps.pairs[0].target, ps.pairs[0].listed)])
    assert [one["between_models"][OT.SONNET][p]["cutoff"]["crossings"] for p in ("1", "2")] == [n_confused] * 2
    d1 = r2["per_population"]["subset"]["D2"]["round1"]
    assert d1["contradictions"][OT.OPUS]["pooled"]["forward"] == 2 * (len(pair_ids) - n_confused)   # the slip, both passes
    assert {"round1_responses", "subset"} <= {i["dep_key"] for i in summ["_provenance"]["inputs"]}
    tables = (out / "tables.md").read_text()
    for head in ("The run sent only these calls", "## Round 2: the clarified lines, on the confusion subset",
                 "### The brief's test", "### The subset's pairs", "#### D2 (overlap_relation_implies)",
                 "### Arm C2: overlap_six_implies"):
        assert head in tables, head
    prompts = (out / "rendered_prompts.md").read_text()
    assert "=== rubric E2 (overlap_scope_implies)" in prompts and "=== rubric A (" not in prompts
    variant_ids = [ln.split("(")[1].rstrip("):") for ln in prompts.splitlines() if ln.startswith("## Variant: ")]
    assert variant_ids and set(variant_ids) <= set(call_ids)                    # read from the calls sent
    # a resume must name the same calls; --analyse-only recomputes the same round 2
    assert e["cli"].main(e["base"] + ["--models", *models, "--rubrics", "A2", "--passes", "2", "--resume"]) == 2
    assert "a resume must send the calls the run was started with" in capsys.readouterr().err
    assert e["cli"].main(args + ["--resume"]) == 0
    assert len(e["client"]["client"].calls) == 0                                 # a new client; nothing re-sent
    (out / "summary.json").unlink()
    assert e["cli"].main(e["base"] + ["--models", *models, "--analyse-only"]) == 0
    again = json.loads((out / "summary.json").read_text())["result"]["round2"]
    assert again["test"] == r2["test"] and again["rows"] == r2["rows"]


def test_overlap_calls_from_refuses_unknown_calls(overlap_env, tmp_path, capsys):
    e = overlap_env
    bad = tmp_path / "bad_subset.json"
    bad.write_text(json.dumps({"call_ids": ["nn:nope"], "pair_ids": []}))
    assert e["cli"].main(e["base"] + ["--calls-from", str(bad), "--dry-run"]) == 2
    assert "REFUSED: --calls-from" in capsys.readouterr().err
    stray = tmp_path / "stray.json"
    ps = e["T"].pair_set(n_targets=4, n_antonyms=2, n_random=2)
    stray.write_text(json.dumps({"call_ids": [ps.calls[0].call_id], "pair_ids": [ps.pairs[-1].pair_id]}))
    assert e["cli"].main(e["base"] + ["--calls-from", str(stray), "--dry-run"]) == 2
    assert "not in its calls" in capsys.readouterr().err
    assert not e["out"].exists()


# --------------------------------------------------------------------------- round 3 (2026-10-06): one pair per call

def test_overlap_round_3_one_pair_per_call_against_rounds_1_and_2(overlap_env, capsys):
    """coding_plan_overlap_arms.md, "Round 3": rubric A version 6 sent one pair per call (--rubrics A --passes 2),
    compared with version 4 in overlap_arms_1, A2 in overlap_arms_2 and Roger's marks of overlap_test_1, all
    three made first in the list form (rubric A at version 4)."""
    e = overlap_env
    OT, T = e["OT"], e["T"]
    models = [OT.SONNET, OT.OPUS]
    e["client"]["responder"] = T.single_answer(OT.load_rubrics(keys=tuple(OT.RUBRICS)))     # A at version 4
    named = lambda run: [(run if a == "t1" else a) for a in e["base"]] + ["--models", *models]  # noqa: E731
    assert e["cli"].main(named("overlap_test_1") + ["--rubrics", "A"]) == 0
    assert (e["out"].parent / "overlap_test_1" / "marks_key.json").exists()
    assert e["cli"].main(named("overlap_arms_1") + ["--rubrics", "A", "--passes", "2"]) == 0
    ps = OT.PairSet.from_json(json.loads((e["out"].parent / "overlap_arms_1" / "pairs.json").read_text()))
    sub = e["out"].parent / "subset_in.json"
    sub.write_text(json.dumps({"call_ids": [c.call_id for c in ps.calls[:2]],
                               "pair_ids": [p.pair_id for p in ps.pairs if p.call_id == ps.calls[0].call_id]}))
    assert e["cli"].main(named("overlap_arms_2") + ["--rubrics", "A2", "--passes", "2", "--calls-from", str(sub)]) == 0
    n_a2 = sum(p.call_id in {c.call_id for c in ps.calls[:2]} for p in ps.pairs)

    e["single_form"]()                                                                     # A at version 6
    rb = OT.load_rubrics(keys=tuple(OT.RUBRICS))
    assert rb["A"]["form"] == "single"
    e["client"]["responder"] = T.single_answer(rb)
    args = e["base"] + ["--models", *models, "--rubrics", "A", "--passes", "2", "--budget-usd", "10"]
    capsys.readouterr()
    assert e["cli"].main(args + ["--dry-run"]) == 0
    dry = capsys.readouterr().out
    n = len(ps.pairs)
    assert f"rubric A (overlap_concept, one pair per call) on Opus 5.5, pass 2: {n} x" in dry
    assert "(single form, cached system block)" in dry and "with the rubric read from the prompt cache" in dry
    assert "## One pair per call (the single form)" in dry and '\n "other": {"label": ' in dry
    assert "pair set: the same calls as overlap_test_1" in dry and not e["out"].exists()
    assert e["cli"].main(args) == 0
    out, client = e["out"], e["client"]["client"]
    assert len(client.calls) == n * 2 * 2                                                  # pairs x models x passes
    assert all(kw["system"][0].get("cache_control") == {"type": "ephemeral"} for kw in client.calls)
    recs = OT.read_records(out / "responses.jsonl")
    assert {r["form"] for r in recs} == {"single"} and {r["call_id"] for r in recs} == {p.pair_id for p in ps.pairs}
    assert all(r["origin_call_id"] == r["pair_id"].rsplit(">", 1)[0] for r in recs)
    run = json.loads((out / "run.json").read_text())
    assert run["forms"] == {"overlap_concept": "single"} and run["cache_system"] == {"overlap_concept": True}
    assert run["rubric_versions"] == {"overlap_concept": 6} and run["exit_code"] == 0
    assert [s["n_calls"] for s in run["stages"]] == [n] * 4 and run["round2_run"] == "overlap_arms_2"
    assert len((out / "results.jsonl").read_text().splitlines()) == n * 2 * 2
    summ = json.loads((out / "summary.json").read_text())
    res = summ["result"]
    assert res["arms"]["forms"] == {"A": "single"} and res["arms"]["baseline"] is None
    r3 = res["round3"]
    assert (r3["versions"]["v4"]["run"], r3["versions"]["A2"]["run"]) == ("overlap_arms_1", "overlap_arms_2")
    assert (r3["versions"]["v4"]["rubric_versions"], r3["versions"]["v6"]["rubric_versions"]) == ([4], [6])
    assert set(r3["populations"]["all"]["versions"]) == {"v4", "v6"}
    assert set(r3["populations"]["round2"]["versions"]) == {"v4", "A2", "v6"}
    assert r3["populations"]["round2"]["n_pairs"] == n_a2
    for m in models:                                    # the fake answers by label in either form
        assert all(x["exact"] == 1.0 for x in r3["populations"]["all"]["against_v4"]["v6"][m].values())
    assert r3["marks"]["v4_test1"][OT.OPUS]["n"] > 0 and r3["cache"]["v6"][OT.OPUS]["hit_rate"] == 1.0
    assert r3["parse"]["v6"][f"{OT.SONNET}|2"] == {"model": OT.SONNET, "pass": 2, "first_ok": n, "first_total": n,
                                                   "ok": n, "total": n}
    assert {"round1_responses", "round2_responses", "marks_key"} <= {i["dep_key"] for i in summ["_provenance"]["inputs"]}
    tables = (out / "tables.md").read_text()
    assert tables.index("## Round 3:") < tables.index("### Summary: version 4 against version 6") < \
        tables.index("## Parse rates")
    assert "every later pass sent the identical prompt" in tables
    prompts = (out / "rendered_prompts.md").read_text()
    assert "## One pair per call" in prompts and "## Variant:" not in prompts
    (out / "summary.json").unlink()                                                        # --analyse-only: the same
    assert e["cli"].main(e["base"] + ["--models", *models, "--analyse-only"]) == 0
    assert json.loads((out / "summary.json").read_text())["result"]["round3"]["summary"] == r3["summary"]
