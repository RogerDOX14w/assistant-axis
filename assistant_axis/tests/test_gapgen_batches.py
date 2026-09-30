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


class TestLargeWaves:
    """A wave over the batch limits becomes several batches (the limits lowered for the test)."""

    def test_a_wave_over_the_request_limit_becomes_several_batches(self, tmp_path, monkeypatch):
        from assistant_axis.gapgen import batches as bt
        monkeypatch.setattr(bt, "MAX_BATCH_REQUESTS", 40)
        r, _, bc = make(tmp_path)
        res = {x.label: x.filter for x in r.run(test_items())}
        state = json.loads((tmp_path / "batches.json").read_text())
        sense = state["waves"]["w1_sense"]
        assert [b["n_requests"] for b in sense] == [40, 40, 19]
        checks = state["waves"]["w2_checks"]
        assert len(checks) > 1 and all(b["n_requests"] <= 40 for b in checks)
        # every call of a wave is in exactly one batch, and every result is matched and charged once
        for w, bs in state["waves"].items():
            ids = [cid for b in bs for cid in b["custom_ids"]]
            assert len(ids) == len(set(ids)), w
        n_requests = sum(len(b["requests"]) for b in bc.batches.created)
        assert r.usage.n_calls == n_requests == len(r.responses)
        assert len({(rec["custom_id"], rec["stage"]) for rec in r.responses}) == len(r.responses)
        exp = {e["word"]: e for e in load_jsonl("expected_outcomes.jsonl")}
        assert all(res[w]["outcome"] == e["outcome"] for w, e in exp.items())

    def test_the_byte_limit_splits_too(self, tmp_path, monkeypatch):
        from assistant_axis.gapgen import batches as bt
        items = test_items(20)
        a, b = tmp_path / "a", tmp_path / "b"
        a.mkdir()
        b.mkdir()
        r0, _, _ = make(a)                     # the default limits: one batch for the wave
        r0.run(items)
        whole = json.loads((a / "batches.json").read_text())["waves"]["w1_sense"]
        assert len(whole) == 1
        per_request = whole[0]["bytes"] / whole[0]["n_requests"]
        monkeypatch.setattr(bt, "MAX_BATCH_BYTES", int(3.5 * per_request))   # about three requests a batch
        r1, _, _ = make(b)
        r1.run(items)
        sense = json.loads((b / "batches.json").read_text())["waves"]["w1_sense"]
        assert len(sense) >= 6 and sum(x["n_requests"] for x in sense) == 20
        assert all(x["bytes"] <= bt.MAX_BATCH_BYTES for x in sense)
        assert {x.label: x.filter["outcome"] for x in r1.results.values()} == \
            {x.label: x.filter["outcome"] for x in r0.results.values()}

    def test_restart_in_the_middle_of_a_wave_collects_what_was_submitted_and_submits_the_rest(
            self, tmp_path, monkeypatch):
        from assistant_axis.gapgen import batches as bt
        monkeypatch.setattr(bt, "MAX_BATCH_REQUESTS", 10)
        items = test_items(25)
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)))
        real_create = bc.batches.create
        n = {"create": 0}

        def dies_on_second(*, requests):   # the process is killed while submitting wave 1's 2nd batch
            n["create"] += 1
            if n["create"] == 2:
                raise KeyboardInterrupt
            return real_create(requests=requests)
        bc.batches.create = dies_on_second
        r1, _, _ = make(tmp_path, bclient=bc)
        with pytest.raises(KeyboardInterrupt):
            r1.run(items)
        state = json.loads((tmp_path / "batches.json").read_text())
        assert [b["n_requests"] for b in state["waves"]["w1_sense"]] == [10]    # one batch on record
        assert r1.usage.n_calls == 0                                            # nothing collected yet
        bc.batches.create = real_create
        r2, _, _ = make(tmp_path, bclient=bc, resume_records=list(r1.responses))
        res = {x.label: x.filter["outcome"] for x in r2.run(items)}
        sense = json.loads((tmp_path / "batches.json").read_text())["waves"]["w1_sense"]
        assert [b["n_requests"] for b in sense] == [10, 10, 5]      # the recorded batch, then the rest
        ids = [cid for b in sense for cid in b["custom_ids"]]
        assert len(ids) == len(set(ids)) == 25                      # nothing submitted twice
        assert r2.usage.n_calls == sum(len(b["requests"]) for b in bc.batches.created)   # charged once
        exp = {e["word"]: e["outcome"] for e in load_jsonl("expected_outcomes.jsonl")[:25]}
        assert res == exp

    def test_the_budget_check_sees_the_whole_wave(self, tmp_path, monkeypatch):
        from assistant_axis.gapgen import batches as bt
        monkeypatch.setattr(bt, "MAX_BATCH_REQUESTS", 10)
        items = test_items(30)
        usage = GuardedUsage(budget_usd=1.0)
        r, _, bc = make(tmp_path, usage=usage)
        # a cap that one batch of 10 sense calls fits under but the wave of 30 does not
        from assistant_axis.gapgen.split_runner import tokens_for
        i, o = tokens_for("sense", HAIKU)
        usage.budget_usd = 20 * cost_for_usage(HAIKU + "@batch", i, o)
        with pytest.raises(BudgetExceededError):
            r.run(items)
        assert bc.batches.created == []                  # not even the first batch of the wave went
        assert usage.n_calls == 0


class _Flaky:
    """Wraps a FakeBatchClient: the results stream of wave ``wave_prefix``'s batch breaks off
    after ``after`` results on each of the first ``fail_streams`` passes, and the first
    ``fail_retrieves`` retrievals raise, both with the error seen on 2026-09-30."""

    def __init__(self, bc, *, fail_streams=0, after=5, fail_retrieves=0, target=None):
        import httpx
        self.bc, self.after, self.target = bc, after, target
        self.left_streams, self.left_retrieves = fail_streams, fail_retrieves
        self.err = lambda: httpx.RemoteProtocolError(
            "peer closed connection without sending complete message body (incomplete chunked read)")
        real_results, real_retrieve = bc.batches.results, bc.batches.retrieve
        self.passes = 0

        def results(bid):
            rows = real_results(bid)
            if self.target is not None and bid != self.target():
                return rows
            self.passes += 1
            if self.left_streams > 0:
                self.left_streams -= 1

                def broken():
                    for i, r in enumerate(rows):
                        if i == self.after:
                            raise self.err()
                        yield r
                return broken()
            return rows

        def retrieve(bid):
            if self.left_retrieves > 0:
                self.left_retrieves -= 1
                raise self.err()
            return real_retrieve(bid)
        bc.batches.results, bc.batches.retrieve = results, retrieve


class TestDroppedConnections:
    """A results stream or a poll that breaks off is tried again (2026-09-30, the full validation
    run: httpx.RemoteProtocolError inside batches.results)."""

    def _first_batch(self, bc):
        return lambda: bc.batches.created[0]["id"] if bc.batches.created else None

    def test_a_stream_that_breaks_off_is_resumed_and_every_result_delivered_once(self, tmp_path):
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)))
        flaky = _Flaky(bc, fail_streams=1, after=7, target=self._first_batch(bc))
        r, _, _ = make(tmp_path, bclient=bc)
        res = {x.label: x.filter for x in r.run(test_items(20))}
        assert flaky.passes == 2 and flaky.left_streams == 0          # broke once, read again
        n_requests = sum(len(b["requests"]) for b in bc.batches.created)
        assert r.usage.n_calls == n_requests == len(r.responses)      # each charged and recorded once
        ids = [(rec["custom_id"], rec["stage"]) for rec in r.responses]
        assert len(ids) == len(set(ids))
        exp = {e["word"]: e["outcome"] for e in load_jsonl("expected_outcomes.jsonl")[:20]}
        assert {w: f["outcome"] for w, f in res.items()} == exp

    def test_a_stream_that_always_breaks_ends_the_run_with_the_batch_still_submitted(self, tmp_path):
        import httpx
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)))
        flaky = _Flaky(bc, fail_streams=99, after=7, target=self._first_batch(bc))
        r, _, _ = make(tmp_path, bclient=bc)
        with pytest.raises(httpx.RemoteProtocolError):
            r.run(test_items(20))
        assert flaky.passes == 1 + len(r.transport.retry_delays)      # tried and retried, then gave up
        state = json.loads((tmp_path / "batches.json").read_text())
        (b,) = state["waves"]["w1_sense"]
        assert b["status"] == "submitted"                               # --resume will collect it
        assert len(r.responses) == 7 and r.usage.n_calls == 7           # what arrived is kept, once
        # a restart collects the rest from the same batch, charging nothing twice
        flaky.left_streams = 0
        r2, _, _ = make(tmp_path, bclient=bc, resume_records=list(r.responses))
        r2.run(test_items(20))
        assert r2.usage.n_calls == sum(len(x["requests"]) for x in bc.batches.created) - 7
        assert len(bc.batches.created[0]["requests"]) == 20            # wave 1 was not resubmitted
        assert sum(1 for x in bc.batches.created if any(q["custom_id"].startswith("sense-") for q in x["requests"])) == 1

    def test_a_poll_that_fails_once_is_tried_again(self, tmp_path):
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)))
        flaky = _Flaky(bc, fail_retrieves=1)
        r, _, _ = make(tmp_path, bclient=bc)
        res = r.run(test_items(5))
        assert flaky.left_retrieves == 0 and all(x.stage == "classified" for x in res)

    def test_a_non_network_error_is_not_retried(self, tmp_path):
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)))
        calls = {"n": 0}
        real = bc.batches.retrieve

        def broken(bid):
            calls["n"] += 1
            raise ValueError("a bug, not the network")
        bc.batches.retrieve = broken
        r, _, _ = make(tmp_path, bclient=bc)
        with pytest.raises(ValueError):
            r.run(test_items(3))
        assert calls["n"] == 1
        bc.batches.retrieve = real

    def test_the_transient_classes(self):
        import anthropic
        import httpx
        from assistant_axis.gapgen.batches import is_transient_stream_error
        assert is_transient_stream_error(httpx.RemoteProtocolError("x"))
        assert is_transient_stream_error(httpx.ReadTimeout("x"))
        assert is_transient_stream_error(anthropic.APIConnectionError(request=httpx.Request("GET", "http://x")))
        assert not is_transient_stream_error(ValueError("x"))


class TestPollLog:
    def test_poll_lines_say_how_long_the_batch_has_waited(self, tmp_path, caplog):
        import logging
        r, _, bc = make(tmp_path)
        with caplog.at_level(logging.INFO, logger="assistant_axis.gapgen.batches"):
            r.run(test_items(3))
        polls = [m for m in caplog.messages if "in_progress" in m]
        assert polls and all("since submission" in m for m in polls)
        assert any("ended (submitted" in m for m in caplog.messages)

    def test_a_batch_found_ended_long_ago_gets_a_line(self, tmp_path, caplog):
        import logging
        from datetime import datetime, timedelta, timezone
        bc = FakeBatchClient(make_responder(tokens=(1000, 100)), polls=0)
        real = bc.batches.retrieve

        def ended_long_ago(bid):
            b = real(bid)
            b.ended_at = datetime.now(timezone.utc) - timedelta(hours=3)
            return b
        bc.batches.retrieve = ended_long_ago
        r, _, _ = make(tmp_path, bclient=bc)
        with caplog.at_level(logging.INFO, logger="assistant_axis.gapgen.batches"):
            r.run(test_items(3))
        late = [m for m in caplog.messages if "found ended" in m]
        assert late and "3h00m after it ended" in late[0] and "suspended" in late[0]


def test_log_lines_carry_their_utc_time():
    import logging
    import re
    from assistant_axis.gapgen.runs import LOG_FORMAT, log_formatter
    rec = logging.LogRecord("assistant_axis.gapgen.batches", logging.INFO, __file__, 1, "batch %s: ended", ("b",),
                            None)
    rec.created = 0.0                     # 1970-01-01T00:00:00Z whatever the local zone
    line = log_formatter().format(rec)
    assert line == "1970-01-01T00:00:00Z INFO batch b: ended"
    assert "%(asctime)s" in LOG_FORMAT
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ ", log_formatter().format(
        logging.LogRecord("x", logging.WARNING, __file__, 1, "m", (), None)))


def test_the_clis_use_the_timestamped_format():
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "data_analysis" / "gap_generation"
    for name in ("traithood_filter.py", "plain_reading.py", "states_pass.py"):
        text = (root / name).read_text(encoding="utf-8")
        assert "configure_logging()" in text and "basicConfig" not in text, name


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
        # the alignment score counts, beside the count of the boolean derived from them
        rows = [json.loads(x) for x in (d / "results.jsonl").read_text().splitlines()]
        traits = [r for r in rows if r["filter"]["outcome"] == "trait"]
        sc = s["v2_fields"]["alignment_scores"]
        assert set(sc) == {"0", "1", "2", "3", "none"} and sum(sc.values()) == len(traits) > 0
        assert sc == {k: sum(1 for r in traits if str(r["filter"]["alignment"]) == k) for k in ("0", "1", "2", "3")} \
            | {"none": 0}
        assert s["v2_fields"]["alignment_relevant_true"] == sc["2"] + sc["3"]
        assert sc["2"] + sc["3"] > 0 and sc["0"] + sc["1"] > 0      # the recorded answers cover both sides
        usage = json.loads((d / "usage.json").read_text())
        assert usage["n_calls"] == len(cli["live"].calls)
        assert sum(v["n_calls"] for v in s["split"]["cost_by_step"].values()) == usage["n_calls"]
        run = json.loads((d / "run.json").read_text())
        from assistant_axis.gapgen import split_rubrics as sr
        # the latest pin, not a literal: the literal (6) went stale with the sense 7 and 8 bumps
        assert run["pipeline"] == "split" and run["transport"] == "live"
        assert run["step_versions"] == {n: v for n, (v, _) in sr.current_versions().items()}
        # every prompt the run sends is named, the probe and comparison included
        from assistant_axis.gapgen import filter_rubric as fr
        from assistant_axis.gapgen import plain_reading as pr
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
