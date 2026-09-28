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
    row = {"id": i, "reason": "A habit.", "senses": [label], "trait_sense_rank": 1, "enactable_in_text": 2,
           "verdict": "trait", "tags": [], "region": "social_interpersonal",
           "gloss": "This means " + "doing things " * 9 + "always.", "confidence": 0.9}
    if label == "tall":
        row.update(verdict="tagged", tags=["physical"], region="physical")
    if label == "librarian":
        row.update(verdict="tagged", tags=["role_person"])
    return row


def responder(kw, *, tokens=(1000, 300)):
    items = [json.loads(x) for x in user_text(kw).splitlines()[1:]]
    if "rare English words" in system_text(kw):
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
        holder["client"] = FakeAsyncAnthropic(holder.get("responder", responder))
        return holder["client"]

    monkeypatch.setattr(anthropic, "AsyncAnthropic", factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    return holder


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

    def test_cap_stops_run_and_usage_written(self, cand_dir, fake_client):
        reg = cand_dir / "registry.jsonl"
        _submit(reg, ["stubborn", "vain", "timid", "loyal", "brave", "shy", "rude", "calm", "proud", "witty"])
        fake_client["responder"] = lambda kw: responder(kw, tokens=(2_000_000, 0))  # $2 per call
        rc = traithood_filter.main(["--batch-id", "b5", "--unfiltered", "--registry", str(reg), "--out-root",
                                    str(cand_dir), "--budget-usd", "0.001", "--confirm-expensive",
                                    "--batch-size", "2", "--concurrency", "1", "--no-second-opinion"])
        assert rc == 2
        d = cand_dir / "filter" / "b5"
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] >= 1 and usage["total_cost_usd"] >= 2.0
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["stopped_by_budget"] is True

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
