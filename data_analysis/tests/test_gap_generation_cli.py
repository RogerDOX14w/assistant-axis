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


def _row(i, label):
    row = {"id": i, "label": label, "reason": "A habit.",
           "person_senses": [{"sense": label, "kind": "trait"}], "trait_senses_equally_obvious": False,
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
        rc = traithood_filter.main(["--batch-id", "b1", "--unfiltered", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--dry-run"])
        out = capsys.readouterr().out
        assert rc == 0 and reg.read_bytes() == raw
        assert not (cand_dir / "filter").exists() and "client" not in fake_client
        assert "tokens at claude-haiku-4-5-20251001 rates = $" in out
        assert "--- prompt 1 ---" in out and '"label": "stubborn"' in out

    def test_validation_run(self, tmp_path, cand_dir, fake_client):
        val = _validation(tmp_path)
        rc = traithood_filter.main(["--batch-id", "pilot", "--validation-file", str(val), "--out-root",
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
        args = ["--batch-id", "b", "--validation-file", str(val), "--out-root", str(cand_dir), "--no-second-opinion"]
        assert traithood_filter.main(args) == 0
        assert traithood_filter.main(args) == 1

    def test_run_selector_writes_registry(self, cand_dir, fake_client):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "tall", "librarian"], run="r1")
        _submit(reg, ["vain"], gen="censuses", run="t1")
        rc = traithood_filter.main(["--batch-id", "b2", "--run", "wordnet_walk/r1", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--no-second-opinion"])
        assert rc == 0
        rows = Registry(reg).fold()
        assert rows["stubborn#1"]["filter"]["verdict"] == "trait" and rows["stubborn#1"]["gloss"]
        assert rows["stubborn#1"]["freq"]["zipf_min"] > 2
        assert rows["tall#1"]["holding"] == "physical"
        assert rows["librarian#1"]["holding"] == "roles" and rows["librarian#1"]["entity_type"] == "role"
        assert rows["vain#1"]["filter"] is None  # other run untouched
        # a second pass over the same run finds nothing unfiltered
        assert traithood_filter.main(["--batch-id", "b3", "--run", "wordnet_walk/r1", "--registry", str(reg),
                                      "--out-root", str(cand_dir)]) == 0
        assert not (cand_dir / "filter" / "b3").exists()

    def test_estimate_over_budget_refused(self, cand_dir, fake_client):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn"])
        rc = traithood_filter.main(["--batch-id", "b4", "--unfiltered", "--registry", str(reg),
                                    "--out-root", str(cand_dir), "--budget-usd", "0.00001"])
        assert rc == 2 and not (cand_dir / "filter" / "b4").exists() and "client" not in fake_client

    def test_cap_stops_run_and_keeps_what_was_paid_for(self, cand_dir, fake_client):
        """Review finding 4: a stop must stop (bounded calls) and keep the rows
        and responses already paid for."""
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm", "proud", "witty"])
        fake_client["responder"] = lambda kw: responder(kw, tokens=(40_000, 0))  # $0.04 per call
        fake_client["delay"] = 0.01  # calls overlap like network I/O
        rc = traithood_filter.main(["--batch-id", "b5", "--unfiltered", "--registry", str(reg), "--out-root",
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
        assert traithood_filter.main(["--batch-id", "b6", "--keys", "stubborn#1", "--registry", str(reg),
                                      "--out-root", str(cand_dir), "--no-second-opinion"]) == 0
        f = Registry(reg).get("stubborn#1")["filter"]
        assert f["verdict"] == "trait" and "classifier_verdict" not in f and f["rubric_version"] == 3  # classifier v3 (round 3)

    def test_prompt_hashes_recorded(self, tmp_path, cand_dir, fake_client):
        """Review finding 10: which prompt text was sent is recorded."""
        import hashlib
        from assistant_axis.gapgen import filter_rubric as fr
        from assistant_axis.gapgen import plain_reading as pr
        val = _validation(tmp_path)
        assert traithood_filter.main(["--batch-id", "h", "--validation-file", str(val), "--out-root",
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
        base = ["--validation-file", str(val), "--out-root", str(cand_dir), "--no-second-opinion"]
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
        assert traithood_filter.main(["--batch-id", "u1", "--validation-file", str(val), "--out-root",
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
            traithood_filter.main(["--batch-id", "e1", "--unfiltered", "--registry", str(reg), "--out-root",
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
        rc = traithood_filter.main(["--batch-id", "b7", "--unfiltered", "--registry", str(reg),
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
