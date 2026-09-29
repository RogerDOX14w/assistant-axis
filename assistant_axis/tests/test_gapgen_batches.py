"""Stage B: the split filter through the Message Batches API (coding_plan_split.md section 8, test 8),
and the split side of the ``traithood_filter.py`` CLI.  A fake batch client replays the recorded
answers; no API call."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from assistant_axis.gapgen.batches import AUTO_BATCH_FROM, BatchTransport, choose_transport
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.split_runner import SplitRunner
from assistant_axis.judge_pricing import BudgetExceededError, cost_for_usage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response
from assistant_axis.tests.split_replay import HAIKU, SONNET55, load_jsonl, make_responder, test_items


class FakeBatches:
    """``client.messages.batches`` with create / retrieve / results.  Each request is answered by
    ``responder`` (the live fake's), results come back in reverse order, and a batch reports
    ``in_progress`` for ``polls`` retrievals before ``ended``."""

    def __init__(self, responder, *, polls=1, drop=(), error=()):
        self.responder = responder
        self.polls = polls
        self.drop, self.error = set(drop), set(error)
        self.created: list[dict] = []
        self.batches: dict[str, dict] = {}
        self.retrieves = 0

    def create(self, *, requests):
        bid = f"msgbatch_{len(self.created) + 1:03d}"
        self.created.append({"id": bid, "requests": list(requests)})
        self.batches[bid] = {"requests": list(requests), "left": self.polls}
        return SimpleNamespace(id=bid, processing_status="in_progress")

    def retrieve(self, bid):
        self.retrieves += 1
        b = self.batches[bid]
        if b["left"] > 0:
            b["left"] -= 1
            return SimpleNamespace(id=bid, processing_status="in_progress", request_counts={"processing": 1})
        return SimpleNamespace(id=bid, processing_status="ended", request_counts={})

    def results(self, bid):
        out = []
        for r in reversed(self.batches[bid]["requests"]):
            cid = r["custom_id"]
            if any(d in cid for d in self.drop):
                continue
            if any(e in cid for e in self.error):
                out.append(SimpleNamespace(custom_id=cid, result=SimpleNamespace(
                    type="errored", error={"type": "api_error", "message": "boom"})))
                continue
            msg = self.responder(dict(r["params"]))
            out.append(SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=msg)))
        return out


class FakeBatchClient:
    def __init__(self, responder, **kw):
        self.messages = SimpleNamespace(batches=FakeBatches(responder, **kw))

    @property
    def batches(self):
        return self.messages.batches


def no_sleep(_s):
    async def z():
        return None
    return z()


def make(tmp_path, *, bclient=None, usage=None, **kw):
    responder = make_responder(tokens=(1000, 100))
    live = FakeAsyncAnthropic(responder)
    r = SplitRunner(client=live, batch_id="b", wordnet=False, zipf_fn=lambda w: 4.0, retry_delays=(),
                    second_opinion=kw.pop("second_opinion", False), usage=usage, **kw)
    bc = bclient or FakeBatchClient(responder)
    r.transport = BatchTransport(r, bc, tmp_path / "batches.json", sleep=no_sleep, poll_seconds=0)
    return r, live, bc


class TestBatches:
    def test_waves_in_order_results_by_custom_id_same_outcomes_as_live(self, tmp_path):
        items = test_items()
        r, live, bc = make(tmp_path)
        res = {x.key: x.filter for x in r.run(items)}
        assert live.calls == []                                   # nothing went live
        ids = [c["id"] for c in bc.batches.created]
        state = json.loads((tmp_path / "batches.json").read_text())
        waves = list(state["waves"])
        assert waves == ["w1_sense", "w2_checks", "w3_same_sense", "w4_gloss", "w5_last_step"]
        assert [b["id"] for w in waves for b in state["waves"][w]] == ids
        for b in bc.batches.created:
            cids = [q["custom_id"] for q in b["requests"]]
            assert len(set(cids)) == len(cids)
            assert all(len(c) <= 64 and all(ch.isalnum() or ch in "_-" for ch in c) for c in cids)
        # matched by custom_id though returned in reverse: same outcomes as the live replay
        exp = {e["word"]: e for e in load_jsonl("expected_outcomes.jsonl")}
        by_label = {x.label: x.filter for x in r.results.values()}
        for label, e in exp.items():
            assert by_label[label]["outcome"] == e["outcome"] and by_label[label]["judged_sense"] == e["accepted"]
        assert all(rec["transport"] == "batches" and rec["batch_request_id"] for rec in r.responses)

    def test_charged_at_half_rate_under_model_at_batch(self, tmp_path):
        r, _, bc = make(tmp_path, second_opinion=True, second_opinion_frac=0.1)
        r.run(test_items(20))
        per = r.usage.per_model
        assert set(per) == {HAIKU + "@batch", SONNET55 + "@batch"}
        h = per[HAIKU + "@batch"]
        assert h.cost_usd == pytest.approx(0.5 * cost_for_usage(HAIKU, h.prompt_tokens, h.completion_tokens))
        s = per[SONNET55 + "@batch"]
        assert s.cost_usd == pytest.approx(s.prompt_tokens * 1e-6 + s.completion_tokens * 5e-6)
        for b in bc.batches.created:
            for q in b["requests"]:
                if q["params"]["model"] == SONNET55:
                    assert "temperature" not in q["params"] and "thinking" not in q["params"]
                    assert "output_config" not in q["params"] and q["params"]["max_tokens"] == 2000
                else:
                    assert q["params"]["temperature"] == 0.0

    def test_errored_results_are_retried_once_in_their_own_batch(self, tmp_path):
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)), error=("kind-f-argumentative",))
        r, _, _ = make(tmp_path, bclient=bc)
        res = {x.label: x for x in r.run(test_items(3))}
        waves = json.loads((tmp_path / "batches.json").read_text())["waves"]
        retry = waves["w2_checks_retry"]
        assert len(retry) == 1 and retry[0]["custom_ids"]
        assert all(c.startswith("kind-f-argumentative") for c in retry[0]["custom_ids"])   # only the failures
        assert res["argumentative"].stage == "failed" and "batch result errored" in res["argumentative"].error

    def test_restart_collects_a_recorded_batch_instead_of_resubmitting(self, tmp_path):
        items = test_items(8)
        responder = make_responder(tokens=(1000, 100))
        bc = FakeBatchClient(responder)
        r1, _, _ = make(tmp_path, bclient=bc)

        async def killed(wave, calls, on_result):  # submit wave 1, then the process dies
            t = r1.transport
            state = t.load_state()
            batch = t.client.messages.batches.create(requests=[{"custom_id": c.custom_id, "params": {
                "model": c.model, "max_tokens": c.max_tokens, "temperature": c.temperature,
                "system": [{"type": "text", "text": c.system}], "messages": [{"role": "user", "content": c.user}]}}
                for c in calls])
            state["waves"].setdefault(wave, []).append({"id": batch.id, "custom_ids": [c.custom_id for c in calls],
                                                        "n_requests": len(calls), "status": "submitted"})
            t.save_state(state)
            raise KeyboardInterrupt
        r1.transport.execute = killed
        with pytest.raises(KeyboardInterrupt):
            r1.run(items)
        assert len(bc.batches.created) == 1
        r2, _, _ = make(tmp_path, bclient=bc, resume_records=list(r1.responses))
        res = {x.label: x.filter["outcome"] for x in r2.run(items)}
        assert [b["id"] for b in bc.batches.created][0] == "msgbatch_001"
        first_wave_requests = [b for b in bc.batches.created if any(q["custom_id"].startswith("sense-")
                                                                     for q in b["requests"])]
        assert len(first_wave_requests) == 1                     # wave 1 was not submitted again
        exp = {e["word"]: e["outcome"] for e in load_jsonl("expected_outcomes.jsonl")[:8]}
        assert res == exp

    def test_resume_never_collects_a_collected_batch_again(self, tmp_path):
        """A call whose answer failed validation twice is sent again on --resume, in a new batch; the
        batch that answered it before was collected and charged, and is not collected a second time
        (that would record and charge the same answer twice)."""
        items = test_items(3)
        broken = {"on": True}
        good = make_responder(tokens=(1000, 100))

        def responder(kw):
            if broken["on"] and "argumentative" in json.dumps(kw["messages"]) and "kinds" in json.dumps(kw["system"]):
                return make_response("not json at all", input_tokens=1000, output_tokens=100)
            return good(kw)
        bc = FakeBatchClient(responder)
        r1, _, _ = make(tmp_path, bclient=bc)
        res1 = {x.label: x for x in r1.run(items)}
        assert res1["argumentative"].stage == "failed"
        n_before = len(bc.batches.created)
        broken["on"] = False
        r2, _, _ = make(tmp_path, bclient=bc, resume_records=list(r1.responses))
        res2 = {x.label: x for x in r2.run(items)}
        assert res2["argumentative"].stage == "classified"
        new = bc.batches.created[n_before:]
        assert new and all(q["custom_id"].startswith("kind-f-argumentative") or not q["custom_id"].startswith("kind-")
                           for b in new for q in b["requests"])
        # every answer r2 charged came from a batch r2 submitted
        assert r2.usage.n_calls == sum(len(b["requests"]) for b in new)

    def test_estimate_checked_before_each_wave(self, tmp_path):
        usage = GuardedUsage(budget_usd=0.01)
        r, _, bc = make(tmp_path, usage=usage)
        with pytest.raises(BudgetExceededError):
            r.run(test_items(30))
        assert len(bc.batches.created) <= 1 and usage.total_cost_usd <= 0.02
        assert {x.stage for x in r.results.values()} <= {"pending", "classified", "failed"}

    def test_a_batch_that_crosses_the_cap_is_recorded_whole(self, tmp_path):
        usage = GuardedUsage(budget_usd=1.0)
        r, _, bc = make(tmp_path, usage=usage)
        r.estimate_usd = lambda calls, batch=False: 0.0   # the estimate lets it through
        usage.budget_usd = 0.02
        with pytest.raises(BudgetExceededError):
            r.run(test_items(30))
        assert len(bc.batches.created) == 1
        assert len(r.responses) == len(bc.batches.created[0]["requests"]) == 30
        assert usage.n_calls == 30


class TestAuto:
    def test_auto_picks_live_below_300_and_batches_from_300(self):
        assert choose_transport("auto", AUTO_BATCH_FROM - 1)[0] == "live"
        assert choose_transport("auto", AUTO_BATCH_FROM)[0] == "batches"
        assert choose_transport("live", 10_000)[0] == "live"
        assert choose_transport("batches", 1)[0] == "batches"
        assert AUTO_BATCH_FROM == 300


# ---------------------------------------------------------------------------
# the CLI
# ---------------------------------------------------------------------------

@pytest.fixture
def cli(monkeypatch, tmp_path):
    import anthropic
    import dotenv
    from data_analysis.gap_generation import split_cli, traithood_filter
    holder = {"responder": make_responder(tokens=(600, 100))}

    def async_factory(**kw):
        holder["live"] = FakeAsyncAnthropic(holder["responder"])
        return holder["live"]

    def sync_factory(**kw):
        holder["batch"] = FakeBatchClient(holder["responder"])
        return holder["batch"]
    monkeypatch.setattr(anthropic, "AsyncAnthropic", async_factory)
    monkeypatch.setattr(anthropic, "Anthropic", sync_factory)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: None)
    # split_cli reads both through traithood_filter, so one patch covers both pipelines
    monkeypatch.setattr(traithood_filter, "git_sha", lambda *a, **k: "abc1234")
    monkeypatch.setattr(traithood_filter, "platform_dirty_files", lambda *a, **k: [])
    assert not hasattr(split_cli, "platform_dirty_files")
    val = tmp_path / "words.jsonl"
    val.write_text("".join(json.dumps({"surface": e["word"], "stratum": e["group"], "expected": e["outcome"],
                                       "expected_reading": e["accepted"]}) + "\n"
                           for e in load_jsonl("expected_outcomes.jsonl")[:15]))
    holder["val"], holder["out"] = val, tmp_path / "cand"
    holder["out"].mkdir()
    return holder


def _args(h, *extra):
    return ["--batch-id", "p", "--validation-file", str(h["val"]), "--out-root", str(h["out"]),
            "--budget-usd", "1", *extra]


class TestSplitCLI:
    def test_live_run_writes_every_output(self, cli):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--transport", "live")) == 0
        d = cli["out"] / "filter" / "p"
        for f in ("responses.jsonl", "results.jsonl", "summary.json", "usage.json", "run.json"):
            assert (d / f).exists(), f
        s = json.loads((d / "summary.json").read_text())["result"]
        assert s["pipeline"] == "split" and s["rubric_version"] == 5
        fig = s["split"]["pilot_figures"]
        assert fig["n_reached_step1"] == 15 and fig["same_outcome_as_expected"] == 15
        assert all(v["ok"] == v["n"] for v in s["split"]["step_parse_rates"].values())
        # the top-level second-opinion figures come from the split's records, not the single pipeline's
        assert s["second_opinion_n"] == s["split"]["second_opinion"]["n"] > 0
        assert s["disagreements"] == len(s["split"]["second_opinion"]["disagree"])
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] == len(cli["live"].calls)
        assert sum(v["n_calls"] for v in s["split"]["cost_by_step"].values()) == usage["n_calls"]
        run = json.loads((d / "run.json").read_text())
        assert run["pipeline"] == "split" and run["transport"] == "live" and run["step_versions"]["sense"] == 6
        # every prompt the run sends is named, the probe and comparison included
        from assistant_axis.gapgen import filter_rubric as fr
        from assistant_axis.gapgen import plain_reading as pr
        from assistant_axis.gapgen import split_rubrics as sr
        assert set(run["prompt_sha256"]) == set(sr.NAMES) | {"probe", "comparison"}
        assert run["prompt_sha256"]["probe"] == sr.sha256(fr.DEFINE_PROBE_PROMPT)
        assert run["prompt_sha256"]["comparison"] == pr.PROMPT_SHA256["comparison"]
        assert run["probe_rubric_version"] == fr.PROBE_RUBRIC_VERSION

    def test_batches_run_and_resume_sends_nothing_twice(self, cli):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--transport", "batches")) == 0
        d = cli["out"] / "filter" / "p"
        assert (d / "batches.json").exists()
        first = json.loads((d / "usage.json").read_text())
        assert all(m.endswith("@batch") for m in first["per_model"])
        assert traithood_filter.main(_args(cli, "--transport", "batches")) == 1      # exists: refused
        assert traithood_filter.main(_args(cli, "--transport", "batches", "--resume")) == 0
        assert cli["batch"].batches.created == []                                   # every answer on record
        again = json.loads((d / "usage.json").read_text())
        assert again["n_calls"] == first["n_calls"]
        run = json.loads((d / "run.json").read_text())
        assert run["resumed"] and len(run["earlier_sessions"]) == 1

    def test_batch_size_refused_with_split(self, cli):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--batch-size", "5")) == 2

    def test_unpinned_rubric_refuses_and_prints_the_bump_command(self, cli, monkeypatch, capsys):
        from assistant_axis.gapgen import split_rubrics
        from data_analysis.gap_generation import traithood_filter
        monkeypatch.setattr(split_rubrics, "mismatches", lambda *a, **k: ["kind: text changed (sha ab...)"])
        assert traithood_filter.main(_args(cli)) == 2
        assert "rubric_pins.py bump kind" in capsys.readouterr().err
        assert not (cli["out"] / "filter" / "p").exists()

    def test_auto_transport_printed_with_the_estimate(self, cli, capsys):
        from data_analysis.gap_generation import traithood_filter
        assert traithood_filter.main(_args(cli, "--dry-run")) == 0
        out = capsys.readouterr().out
        assert "transport: live (auto: 15 words, fewer than 300, go live)" in out
        assert "sense: 15 x (567, 207) tokens at claude-haiku-4-5-20251001 rates" in out
        assert "second opinion: kind" in out and "claude-sonnet-5-5 rates" in out

    def test_single_pipeline_still_there(self, cli):
        from data_analysis.gap_generation import traithood_filter
        ap = traithood_filter.build_parser()
        a = ap.parse_args(["--batch-id", "x", "--unfiltered", "--pipeline", "single"])
        assert a.pipeline == "single" and a.batch_size is None
        assert ap.parse_args(["--batch-id", "x", "--unfiltered"]).second_model == SONNET55
        assert ap.parse_args(["--batch-id", "x", "--unfiltered"]).compare_model == SONNET55
