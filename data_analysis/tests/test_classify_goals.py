"""Tests for classify_goals.py: the text- and model-aware cache, aggregation
over the current corpus, the usage record, --batch and the cost gate.

No API calls: the Anthropic client is mocked, as in the generator tests.
"""

import asyncio
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import data_analysis.classify_goals as module
from assistant_axis.judge_pricing import MultiModelUsage
from data_analysis.classify_goals import WorkItem

OPUS = "claude-opus-4-6"

GOOD = json.dumps({"reasoning": "Steers toward plunder.", "score": 2,
                   "goals": [{"description": "plunder", "goal_type": "terminal"}]})
NONE = json.dumps({"reasoning": "A style only.", "score": 0, "goals": []})
TOKENS = (800, 250)


def _message(text, tokens=TOKENS):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason="end_turn",
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]))


def _cost(model_rates, n, tokens=TOKENS):
    rate_in, rate_out = model_rates
    return n * (tokens[0] * rate_in + tokens[1] * rate_out) / 1e6


OPUS_RATES = (5.0, 25.0)
OPUS_BATCH_RATES = (2.5, 12.5)


# ---------------------------------------------------------------------------
# A small corpus: the role pirate (two instructions) and the trait wry (one
# pair), so four items
# ---------------------------------------------------------------------------

PIRATE = ["You are a pirate who seizes every ship you can.", "Be a pirate: take what you want."]
WRY = {"pos": "You are wry.", "neg": "You are earnest."}


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    roles = tmp_path / "roles"
    traits = tmp_path / "traits"
    roles.mkdir()
    traits.mkdir()
    (roles / "pirate.json").write_text(json.dumps({"instruction": [{"pos": t} for t in PIRATE]}))
    (traits / "wry.json").write_text(json.dumps({"positive_label": "wry", "instruction": [WRY]}))
    monkeypatch.setattr(module, "ROLES_DIR", roles)
    monkeypatch.setattr(module, "TRAITS_DIR", traits)
    out = tmp_path / "out"
    return SimpleNamespace(roles=roles, traits=traits, out=out, raw=out / module.RAW_NAME,
                           agg=out / module.AGG_NAME, usage=out / module.USAGE_NAME)


def _items():
    return module.load_work_items(module.ROLES_DIR, module.TRAITS_DIR)


def _rec(name, source, polarity, index, text, *, model=None, classification=None, **extra):
    r = {"name": name, "source": source, "polarity": polarity, "index": index, "text": text,
         "classification": classification if classification is not None else json.loads(GOOD)}
    if model is not None:
        r["model"] = model
    r.update(extra)
    return r


def _write_raw(corpus, records):
    corpus.out.mkdir(exist_ok=True)
    corpus.raw.write_text(json.dumps(records))


class _Results:
    """What ``client.messages.batches.results`` resolves to: an async iterator."""

    def __init__(self, entries):
        self._entries = list(entries)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._entries:
            raise StopAsyncIteration
        return self._entries.pop(0)


def _entry(custom_id, kind="succeeded", text=GOOD, tokens=TOKENS):
    result = SimpleNamespace(type=kind)
    if kind == "succeeded":
        result.message = _message(text, tokens)
    return SimpleNamespace(custom_id=custom_id, result=result)


def _counts(**kw):
    base = dict(succeeded=0, errored=0, expired=0, canceled=0, processing=0)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def client(monkeypatch):
    """A mocked AsyncAnthropic: real-time calls answer GOOD; the batch calls
    are set per test."""
    c = MagicMock()
    c.messages.create = AsyncMock(side_effect=lambda **kw: _message(GOOD))
    c.messages.batches.create = AsyncMock(return_value=SimpleNamespace(id="msgbatch_test"))
    c.messages.batches.retrieve = AsyncMock(side_effect=lambda batch_id: SimpleNamespace(
        processing_status="ended", request_counts=_counts(succeeded=4)))
    monkeypatch.setattr(module.anthropic, "AsyncAnthropic", lambda **kw: c)
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    return c


def _run(corpus, *extra):
    module.main(["--output-dir", str(corpus.out), *extra])


# ---------------------------------------------------------------------------
# Cache validity
# ---------------------------------------------------------------------------

class TestCacheValidity:
    ITEM = WorkItem(name="pirate", source="role", polarity="pos", index=0, text="current text")

    def test_valid_only_for_the_same_text_and_model(self):
        rec = _rec("pirate", "role", "pos", 0, "current text", model=OPUS)
        assert module.cache_status(rec, self.ITEM, OPUS) == module.CACHE_VALID
        assert module.cache_status(dict(rec, text="older text"), self.ITEM, OPUS) == module.CACHE_STALE_TEXT
        assert module.cache_status(rec, self.ITEM, "claude-sonnet-4-6") == module.CACHE_STALE_MODEL

    def test_a_record_without_a_model_is_the_april_default(self):
        rec = _rec("pirate", "role", "pos", 0, "current text")
        assert "model" not in rec and module.LEGACY_RECORD_MODEL == OPUS
        assert module.cache_status(rec, self.ITEM, OPUS) == module.CACHE_VALID
        assert module.cache_status(rec, self.ITEM, "claude-opus-4-7") == module.CACHE_STALE_MODEL

    def test_no_record_or_a_failed_one_is_missing(self):
        assert module.cache_status(None, self.ITEM, OPUS) == module.CACHE_MISSING
        failed = dict(_rec("pirate", "role", "pos", 0, "current text"), classification=None)
        assert module.cache_status(failed, self.ITEM, OPUS) == module.CACHE_MISSING

    def test_a_record_differing_in_both_counts_as_another_model(self):
        rec = _rec("pirate", "role", "pos", 0, "older text", model="claude-sonnet-4-6")
        assert module.cache_status(rec, self.ITEM, OPUS) == module.CACHE_STALE_MODEL

    def test_which_items_are_classified(self, corpus):
        items = _items()
        by_key = {it.key: it for it in items}
        existing = {
            "pirate/role/pos/0": _rec("pirate", "role", "pos", 0, PIRATE[0]),                 # valid
            "pirate/role/pos/1": _rec("pirate", "role", "pos", 1, "an older text"),           # stale text
            "wry/trait/pos/0": _rec("wry", "trait", "pos", 0, WRY["pos"], model="claude-sonnet-4-6"),
        }                                                                                    # wry neg missing
        plan = module.plan_cache(items, existing, OPUS)
        assert [len(plan[s]) for s in (module.CACHE_VALID, module.CACHE_STALE_TEXT,
                                       module.CACHE_STALE_MODEL, module.CACHE_MISSING)] == [1, 1, 1, 1]
        keys = lambda xs: [it.key for it in xs]  # noqa: E731
        # in corpus order
        assert keys(module.items_to_classify(items, existing, OPUS)) == [
            "pirate/role/pos/1", "wry/trait/pos/0", "wry/trait/neg/0"]
        # --allow-stale keeps the older text, never another model's record
        assert keys(module.items_to_classify(items, existing, OPUS, allow_stale=True)) == [
            "wry/trait/pos/0", "wry/trait/neg/0"]
        assert keys(module.items_to_classify(items, existing, OPUS, force=True)) == list(by_key)

    def test_a_run_classifies_only_what_is_not_valid(self, corpus, client):
        _write_raw(corpus, [_rec("pirate", "role", "pos", 0, PIRATE[0]),
                            _rec("pirate", "role", "pos", 1, "an older text")])
        _run(corpus)
        sent = [kw["messages"][0]["content"] for kw in
                (c.kwargs for c in client.messages.create.call_args_list)]
        assert len(sent) == 3 and not any(PIRATE[0] in s for s in sent)
        raw = {module.record_key(r): r for r in json.loads(corpus.raw.read_text())}
        assert raw["pirate/role/pos/1"]["text"] == PIRATE[1]                    # replaced
        assert "model" not in raw["pirate/role/pos/0"]                          # kept as it was

    def test_new_records_carry_the_model_and_date(self, corpus, client):
        _run(corpus, "--names", "wry")
        for r in json.loads(corpus.raw.read_text()):
            assert r["model"] == OPUS
            assert len(r["classified_at"]) == 10 and r["classified_at"][4] == "-"
            assert "batch_id" not in r

    def test_a_failure_does_not_overwrite_a_classified_record(self):
        item = WorkItem(name="pirate", source="role", polarity="pos", index=0, text="new text")
        existing = {item.key: _rec("pirate", "role", "pos", 0, "older text")}
        module.store_result(existing, item, None, OPUS)
        assert existing[item.key]["text"] == "older text"
        module.store_result(existing, item, json.loads(NONE), OPUS)
        assert existing[item.key]["text"] == "new text" and existing[item.key]["classification"]["score"] == 0

    def test_an_unreadable_raw_file_stops_the_run(self, corpus, client):
        corpus.out.mkdir()
        corpus.raw.write_text("{ not json")
        with pytest.raises(SystemExit, match="Could not load"):
            _run(corpus)
        assert corpus.raw.read_text() == "{ not json"


# ---------------------------------------------------------------------------
# Aggregation covers the current corpus only
# ---------------------------------------------------------------------------

class TestAggregation:
    def _existing(self):
        recs = [
            _rec("pirate", "role", "pos", 0, PIRATE[0]),
            _rec("pirate", "role", "pos", 1, "an older text"),
            _rec("libertarian", "trait", "pos", 0, "a dropped trait"),          # renamed since
            _rec("pirate", "role", "pos", 4, "a position that is gone"),
        ]
        return {module.record_key(r): r for r in recs}

    def test_dropped_stems_and_older_texts_are_left_out(self, corpus):
        selected, counts = module.select_for_aggregation(self._existing(), _items())
        assert [module.record_key(r) for r in selected] == ["pirate/role/pos/0"]
        assert counts == {"aggregated": 1, "not_in_corpus": 2, "stale_text_left_out": 1}

    def test_allow_stale_takes_older_texts_and_marks_them(self, corpus):
        existing = self._existing()
        selected, counts = module.select_for_aggregation(existing, _items(), allow_stale=True)
        assert counts["stale_text"] == 1 and counts["aggregated"] == 2
        assert "stale_text" not in existing["pirate/role/pos/1"]               # the raw record is untouched
        agg = module.aggregate_results(selected)
        assert len(agg) == 1
        details = agg[0]["instructions"]
        assert [d.get("stale_text", False) for d in details] == [False, True]
        assert all(d["model"] == OPUS for d in details)
        assert agg[0]["aggregate"]["n_stale_text"] == 1

    def test_a_run_keeps_history_in_the_raw_file(self, corpus, client):
        _write_raw(corpus, list(self._existing().values()))
        _run(corpus, "--allow-stale")
        raw = {module.record_key(r) for r in json.loads(corpus.raw.read_text())}
        assert {"libertarian/trait/pos/0", "pirate/role/pos/4"} <= raw
        agg = json.loads(corpus.agg.read_text())
        assert {(a["name"], a["source"], a["polarity"]) for a in agg} == {
            ("pirate", "role", "pos"), ("wry", "trait", "pos"), ("wry", "trait", "neg")}
        pirate = next(a for a in agg if a["name"] == "pirate")
        assert [d["index"] for d in pirate["instructions"]] == [0, 1]
        assert pirate["instructions"][1]["stale_text"] is True
        # under --allow-stale only the two wry items were missing
        assert client.messages.create.call_count == 2

    def test_without_allow_stale_the_older_text_is_classified_again(self, corpus, client):
        _write_raw(corpus, list(self._existing().values()))
        _run(corpus)
        agg = json.loads(corpus.agg.read_text())
        pirate = next(a for a in agg if a["name"] == "pirate")
        assert [d["text"] for d in pirate["instructions"]] == PIRATE
        assert not any(d.get("stale_text") for d in pirate["instructions"])


# ---------------------------------------------------------------------------
# Usage record
# ---------------------------------------------------------------------------

class TestUsage:
    def test_every_response_is_charged_including_a_failed_parse(self):
        c = MagicMock()
        c.messages.create = AsyncMock(side_effect=[_message("not json", (700, 40)), _message(GOOD, (900, 260))])
        usage = MultiModelUsage()
        item = WorkItem(name="pirate", source="role", polarity="pos", index=0, text=PIRATE[0])
        result = asyncio.run(module.classify_single(
            c, item, OPUS, module.RateLimiter(100), usage=usage))
        assert result["score"] == 2
        assert usage.n_calls == 2 and list(usage.per_model) == [OPUS]
        assert usage.total_prompt_tokens == 1600 and usage.total_completion_tokens == 300
        # the retry asks again with the reminder and a higher temperature
        retry = c.messages.create.call_args_list[1].kwargs
        assert retry["messages"][0]["content"].endswith(module.RETRY_SUFFIX) and retry["temperature"] == 0.1

    def test_persist_usage_merges_into_an_existing_file(self, tmp_path):
        path = tmp_path / module.USAGE_NAME
        first = MultiModelUsage(); first.charge(OPUS, 100, 200)
        module.persist_usage(first, path)
        second = MultiModelUsage(); second.charge(OPUS, 10, 20)
        module.persist_usage(second, path)
        total = MultiModelUsage.load_or_create(path)
        assert total.n_calls == 2 and total.total_prompt_tokens == 110 and total.total_completion_tokens == 220

    def test_a_run_without_calls_writes_no_usage_record(self, tmp_path):
        path = tmp_path / module.USAGE_NAME
        module.persist_usage(MultiModelUsage(), path)
        assert not path.exists()

    def test_runs_write_and_merge_the_usage_record_beside_the_outputs(self, corpus, client):
        _run(corpus)
        usage = json.loads(corpus.usage.read_text())
        assert usage["per_model"][OPUS]["n_calls"] == 4
        assert usage["total_cost_usd"] == pytest.approx(_cost(OPUS_RATES, 4), abs=1e-4)
        _run(corpus, "--force", "--names", "wry")
        assert json.loads(corpus.usage.read_text())["per_model"][OPUS]["n_calls"] == 6
        assert sorted(p.name for p in corpus.out.iterdir()) == sorted(
            [module.RAW_NAME, module.AGG_NAME, module.USAGE_NAME])

    def test_the_usage_line_is_logged(self, corpus, client, caplog):
        caplog.set_level(logging.INFO)
        _run(corpus)
        assert any(m.startswith("[usage] total=$") and "calls=4" in m for m in caplog.messages)


# ---------------------------------------------------------------------------
# Batch mode (--batch)
# ---------------------------------------------------------------------------

def _ids():
    return {it.key: module.batch_custom_id(it) for it in _items()}


class TestBatchRequests:
    def test_requests_carry_the_first_real_time_attempt(self, corpus):
        items = _items()
        requests = module.build_batch_requests(items, OPUS, 0.0)
        assert [r["custom_id"] for r in requests] == [module.batch_custom_id(it) for it in items]
        c = MagicMock()
        c.messages.create = AsyncMock(return_value=_message(GOOD))
        asyncio.run(module.classify_single(c, items[0], OPUS, module.RateLimiter(100)))
        assert requests[0]["params"] == c.messages.create.call_args.kwargs
        params = requests[0]["params"]
        assert params["model"] == OPUS and params["max_tokens"] == module.MAX_TOKENS
        assert params["system"] == module.SYSTEM_PROMPT and params["temperature"] == 0.0
        assert PIRATE[0] in params["messages"][0]["content"]

    def test_custom_ids_are_valid_unique_and_follow_the_text(self):
        long = WorkItem(name="x" * 60, source="trait", polarity="neg", index=4, text="t")
        assert module.BATCH_ID_PATTERN.match(module.batch_custom_id(long))
        a = WorkItem(name="wry", source="trait", polarity="pos", index=0, text="one")
        assert module.batch_custom_id(a).startswith("tp0-wry-")
        assert module.batch_custom_id(a) != module.batch_custom_id(WorkItem("wry", "trait", "pos", 0, "two"))
        assert module.batch_custom_id(a) != module.batch_custom_id(WorkItem("wry", "trait", "neg", 0, "one"))

    def test_every_corpus_item_has_a_distinct_valid_id(self):
        items = module.load_work_items(module.ROLES_DIR, module.TRAITS_DIR)
        if not items:
            pytest.skip("corpus not found")
        ids = [module.batch_custom_id(it) for it in items]
        assert len(set(ids)) == len(ids) and all(module.BATCH_ID_PATTERN.match(i) for i in ids)


class TestBatchRun:
    def _results(self, client, entries):
        client.messages.batches.results = AsyncMock(side_effect=lambda batch_id: _Results(entries))

    def _standard(self, client):
        ids = _ids()
        self._results(client, [
            _entry(ids["pirate/role/pos/0"]),
            _entry(ids["pirate/role/pos/1"], text="not json at all"),
            _entry(ids["wry/trait/pos/0"], kind="errored"),
            _entry(ids["wry/trait/neg/0"], text=NONE),
        ])

    def test_submit_wait_collect_and_redo_in_real_time(self, corpus, client):
        self._standard(client)
        client.messages.batches.retrieve = AsyncMock(side_effect=[
            SimpleNamespace(processing_status="in_progress", request_counts=_counts(processing=4)),
            SimpleNamespace(processing_status="ended", request_counts=_counts(succeeded=3, errored=1)),
        ])
        _run(corpus, "--batch")
        assert client.messages.batches.create.call_count == 1
        sent = client.messages.batches.create.call_args.kwargs["requests"]
        assert sorted(r["custom_id"] for r in sent) == sorted(_ids().values())
        assert client.messages.batches.retrieve.call_count == 2
        # the unusable reply and the errored request were classified in real time
        assert client.messages.create.call_count == 2
        redone = {c.kwargs["messages"][0]["content"] for c in client.messages.create.call_args_list}
        assert any(PIRATE[1] in m for m in redone) and any(WRY["pos"] in m for m in redone)
        raw = {module.record_key(r): r for r in json.loads(corpus.raw.read_text())}
        assert {k: r.get("batch_id") for k, r in raw.items()} == {
            "pirate/role/pos/0": "msgbatch_test", "pirate/role/pos/1": None,
            "wry/trait/pos/0": None, "wry/trait/neg/0": "msgbatch_test"}
        assert all(r["classification"] is not None and r["model"] == OPUS for r in raw.values())
        assert raw["wry/trait/neg/0"]["classification"]["score"] == 0

    def test_usage_is_kept_at_the_batch_price(self, corpus, client):
        self._standard(client)
        _run(corpus, "--batch")
        usage = json.loads(corpus.usage.read_text())["per_model"]
        # three replies came back from the batch (one unusable, and still paid for); two in real time
        assert usage[OPUS + module.BATCH_SUFFIX]["n_calls"] == 3
        assert usage[OPUS + module.BATCH_SUFFIX]["cost_usd"] == pytest.approx(_cost(OPUS_BATCH_RATES, 3), abs=1e-4)
        assert usage[OPUS]["n_calls"] == 2
        assert usage[OPUS]["cost_usd"] == pytest.approx(_cost(OPUS_RATES, 2), abs=1e-4)

    def test_the_batch_is_recorded_beside_the_usage_record(self, corpus, client):
        self._standard(client)
        _run(corpus, "--batch")
        log = json.loads(module.batch_log_path(corpus.out).read_text())
        assert len(log) == 1
        e = log[0]
        assert e["id"] == "msgbatch_test" and e["model"] == OPUS and e["n_requests"] == 4
        assert e["counts"] == {"entries": 4, "ok": 2, "unusable": 1, "errored": 1}
        assert e["collected"] and e["submitted"] and e["estimate_usd"] >= 0

    def test_a_reply_for_a_changed_text_is_charged_not_stored(self, corpus, client):
        stale = WorkItem("pirate", "role", "pos", 0, "the text when the batch was submitted")
        ids = _ids()
        self._results(client, [_entry(module.batch_custom_id(stale)),
                               _entry(ids["pirate/role/pos/1"]), _entry(ids["wry/trait/pos/0"]),
                               _entry(ids["wry/trait/neg/0"])])
        _run(corpus, "--batch")
        raw = {module.record_key(r): r for r in json.loads(corpus.raw.read_text())}
        assert raw["pirate/role/pos/0"]["text"] == PIRATE[0] and "batch_id" not in raw["pirate/role/pos/0"]
        assert client.messages.create.call_count == 1
        usage = json.loads(corpus.usage.read_text())["per_model"]
        assert usage[OPUS + module.BATCH_SUFFIX]["n_calls"] == 4
        log = json.loads(module.batch_log_path(corpus.out).read_text())
        assert log[0]["counts"]["unknown"] == 1

    def test_submit_without_waiting_then_collect_by_id(self, corpus, client, caplog):
        caplog.set_level(logging.INFO)
        self._standard(client)
        _run(corpus, "--batch", "--batch-no-wait")
        assert client.messages.batches.retrieve.call_count == 0
        assert any("--batch-id msgbatch_test" in m for m in caplog.messages)
        assert not corpus.raw.exists() and not corpus.usage.exists()
        _run(corpus, "--batch-id", "msgbatch_test")
        assert client.messages.batches.create.call_count == 1     # not submitted again
        raw = {module.record_key(r): r for r in json.loads(corpus.raw.read_text())}
        assert raw["pirate/role/pos/0"]["batch_id"] == "msgbatch_test"
        assert all(r["classification"] is not None for r in raw.values())

    def test_collecting_twice_does_not_charge_twice(self, corpus, client):
        self._standard(client)
        _run(corpus, "--batch")
        before = json.loads(corpus.usage.read_text())["per_model"][OPUS + module.BATCH_SUFFIX]["n_calls"]
        _run(corpus, "--batch-id", "msgbatch_test")
        after = json.loads(corpus.usage.read_text())["per_model"][OPUS + module.BATCH_SUFFIX]["n_calls"]
        assert before == after == 3

    def test_a_batch_of_another_model_is_refused(self, corpus, client):
        self._standard(client)
        _run(corpus, "--batch", "--batch-no-wait")
        with pytest.raises(SystemExit, match="submitted with --model claude-opus-4-6"):
            _run(corpus, "--batch-id", "msgbatch_test", "--model", "claude-sonnet-4-6")

    def test_a_dry_run_submits_nothing(self, corpus, client, caplog):
        caplog.set_level(logging.INFO)
        _run(corpus, "--batch", "--dry-run")
        assert client.messages.batches.create.call_count == 0 and client.messages.create.call_count == 0
        assert any("one Message Batch" in m for m in caplog.messages)
        assert not corpus.out.exists()

    def test_nothing_to_classify_submits_no_batch(self, corpus, client):
        _run(corpus)
        n = client.messages.create.call_count
        _run(corpus, "--batch")
        assert client.messages.batches.create.call_count == 0 and client.messages.create.call_count == n

    def test_real_time_is_the_default(self):
        args = module.parse_args([])
        assert args.batch is False and args.batch_id is None and args.batch_no_wait is False
        assert args.batch_poll == module.DEFAULT_BATCH_POLL_SECONDS
        with pytest.raises(SystemExit):
            module.parse_args(["--batch-no-wait"])


# ---------------------------------------------------------------------------
# Cost gate and budget
# ---------------------------------------------------------------------------

class TestCostGate:
    def test_the_estimate_uses_the_measured_tokens_and_halves_for_batch(self):
        per_call = (module.MEAN_INPUT_TOKENS_PER_CALL * 5 + module.MEAN_OUTPUT_TOKENS_PER_CALL * 25) / 1e6
        assert module.estimate_cost_usd(100, OPUS) == pytest.approx(100 * per_call)
        assert module.estimate_cost_usd(100, OPUS, batch=True) == pytest.approx(50 * per_call)

    def test_an_unknown_model_fails_before_any_call(self):
        with pytest.raises(KeyError):
            module.estimate_cost_usd(1, "claude-unknown-9")

    def test_over_the_line_is_refused_without_confirm_expensive(self, corpus, client, monkeypatch):
        monkeypatch.setattr(module, "EXPENSIVE_LINE_USD", 0.01)
        with pytest.raises(SystemExit, match="confirm-expensive"):
            _run(corpus)
        with pytest.raises(SystemExit, match="confirm-expensive"):
            _run(corpus, "--batch")
        assert client.messages.create.call_count == 0 and client.messages.batches.create.call_count == 0
        assert not corpus.out.exists()
        _run(corpus, "--confirm-expensive")
        assert client.messages.create.call_count == 4

    def test_the_real_line_is_twenty_dollars(self):
        assert module.EXPENSIVE_LINE_USD == 20.0
        assert module.cost_gate_refusal(19.99, confirm_expensive=False, budget_usd=None) is None
        assert "confirm-expensive" in module.cost_gate_refusal(20.01, confirm_expensive=False, budget_usd=None)
        assert module.cost_gate_refusal(20.01, confirm_expensive=True, budget_usd=None) is None

    def test_an_estimate_above_the_budget_is_refused(self, corpus, client):
        with pytest.raises(SystemExit, match="budget-usd"):
            _run(corpus, "--budget-usd", "0.01")
        assert client.messages.create.call_count == 0

    def test_real_time_stops_once_the_budget_is_reached(self, corpus, client):
        # each reply costs far more than the estimate: the cap stops the run after the first chunk
        client.messages.create = AsyncMock(side_effect=lambda **kw: _message(GOOD, (100_000, 1000)))
        with pytest.raises(SystemExit) as exc:
            _run(corpus, "--budget-usd", "0.10", "--max-concurrent", "1")
        assert exc.value.code == 2
        assert client.messages.create.call_count == 1
        assert len(json.loads(corpus.raw.read_text())) == 1
        assert json.loads(corpus.usage.read_text())["n_calls"] == 1
        assert corpus.agg.exists()

    def test_the_redo_after_a_batch_is_gated_with_what_was_spent(self, corpus, client, caplog):
        caplog.set_level(logging.INFO)
        ids = _ids()
        client.messages.batches.results = AsyncMock(side_effect=lambda batch_id: _Results([
            _entry(ids["pirate/role/pos/0"]), _entry(ids["pirate/role/pos/1"]),
            _entry(ids["wry/trait/pos/0"], kind="expired"), _entry(ids["wry/trait/neg/0"], kind="errored")]))
        # batch estimate 4 x $0.0055 = $0.022 fits; spent ~$0.010 + redo estimate $0.022 does not
        _run(corpus, "--batch", "--budget-usd", "0.03")
        assert client.messages.create.call_count == 0
        assert any("Not classifying them now" in m for m in caplog.messages)
        raw = {module.record_key(r) for r in json.loads(corpus.raw.read_text())}
        assert raw == {"pirate/role/pos/0", "pirate/role/pos/1"}


# ---------------------------------------------------------------------------
# Dry run and the output directory
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_reports_the_cache_and_writes_nothing(self, corpus, client, caplog):
        caplog.set_level(logging.INFO)
        _write_raw(corpus, [_rec("pirate", "role", "pos", 0, PIRATE[0]),
                            _rec("pirate", "role", "pos", 1, "an older text"),
                            _rec("wry", "trait", "pos", 0, WRY["pos"], model="claude-sonnet-4-6")])
        before = corpus.raw.read_text()
        _run(corpus, "--dry-run")
        text = "\n".join(caplog.messages)
        assert "items:            4" in text
        assert "cached and valid: 1" in text
        assert "stale:            2 (text differs: 1, model differs: 1)" in text
        assert "missing:          1" in text
        assert "calls:            3" in text
        _run(corpus, "--dry-run", "--allow-stale")
        assert "calls:            2" in "\n".join(caplog.messages)
        assert client.messages.create.call_count == 0
        assert sorted(p.name for p in corpus.out.iterdir()) == [module.RAW_NAME]
        assert corpus.raw.read_text() == before


class TestOutputDir:
    def test_absolute_is_taken_as_given_and_relative_is_under_the_repo(self, tmp_path):
        assert module.resolve_output_dir(str(tmp_path)) == tmp_path
        assert module.resolve_output_dir("data_analysis/output") == module.REPO_ROOT / "data_analysis" / "output"
