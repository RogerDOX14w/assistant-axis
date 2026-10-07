"""gapgen.llm.call_anthropic_json with a fake client: caching marker, retry on
transient errors, usage charged (cache tokens billed), give-up returns None."""
import asyncio
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.llm import accepts_temperature, billed_usage, call_anthropic_json, request_params
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
from assistant_axis.tests.fake_anthropic import FakeAsyncAnthropic, make_response

HAIKU = "claude-haiku-4-5-20251001"


def _status_error(cls, code):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("boom", response=httpx.Response(code, request=req), body=None)


def run(coro):
    return asyncio.run(coro)


def test_success_charges_usage_and_marks_cache():
    client = FakeAsyncAnthropic(lambda kw: make_response('{"ok": 1}', input_tokens=100, output_tokens=50,
                                                         cache_creation=1000, cache_read=0))
    usage = MultiModelUsage()
    meta = {}
    out = run(call_anthropic_json(client, system="SYS", user="U", model=HAIKU, max_tokens=100,
                                  temperature=0.0, usage=usage, meta=meta))
    assert out == '{"ok": 1}'
    kw = client.calls[0]
    assert kw["system"] == [{"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}]
    assert kw["temperature"] == 0.0 and kw["model"] == HAIKU
    t = usage.per_model[HAIKU]
    assert t.prompt_tokens == 100 + 1250 and t.completion_tokens == 50 and t.n_calls == 1
    assert meta["usage_raw"]["cache_creation_input_tokens"] == 1000 and meta["attempts"] == 1


def test_no_cache_marker():
    client = FakeAsyncAnthropic(lambda kw: "x")
    run(call_anthropic_json(client, system="SYS", user="U", model=HAIKU, max_tokens=10, temperature=0,
                            usage=None, cache_system=False))
    assert "cache_control" not in client.calls[0]["system"][0]


def test_cache_read_billing():
    p, o, raw = billed_usage(make_response("x", input_tokens=10, output_tokens=5, cache_read=1000))
    assert (p, o) == (110, 5)


def test_transient_error_retried():
    errs = [_status_error(anthropic.RateLimitError, 429), _status_error(anthropic.InternalServerError, 500)]

    def responder(kw):
        return errs.pop(0) if errs else "done"

    client = FakeAsyncAnthropic(responder)
    usage = MultiModelUsage()
    meta = {}
    out = run(call_anthropic_json(client, system="S", user="U", model=HAIKU, max_tokens=10, temperature=0,
                                  usage=usage, retry_delays=(0, 0, 0, 0), meta=meta))
    assert out == "done" and len(client.calls) == 3 and meta["attempts"] == 3
    assert usage.n_calls == 1  # failed attempts returned no response to charge


def test_non_transient_error_not_retried():
    client = FakeAsyncAnthropic(lambda kw: _status_error(anthropic.BadRequestError, 400))
    meta = {}
    out = run(call_anthropic_json(client, system="S", user="U", model=HAIKU, max_tokens=10, temperature=0,
                                  usage=MultiModelUsage(), retry_delays=(0, 0), meta=meta))
    assert out is None and len(client.calls) == 1 and "BadRequestError" in meta["error"]


def test_gives_up_after_all_retries():
    client = FakeAsyncAnthropic(lambda kw: _status_error(anthropic.InternalServerError, 503))
    out = run(call_anthropic_json(client, system="S", user="U", model=HAIKU, max_tokens=10, temperature=0,
                                  usage=None, retry_delays=(0, 0)))
    assert out is None and len(client.calls) == 3


HAIKU55 = "claude-haiku-5-5"


def test_haiku_5_5_refuses_temperature():
    """Haiku 5.5 returns a 400 for any temperature, top_p or top_k (model page, 2026-10-07): the request
    leaves temperature out, sends no thinking or effort setting, and keeps the cache marker; Haiku 4.5
    still takes temperature 0."""
    assert not accepts_temperature(HAIKU55) and not accepts_temperature("CLAUDE-HAIKU-5-5")
    assert not accepts_temperature("claude-haiku-5")
    assert accepts_temperature(HAIKU) and accepts_temperature("claude-haiku-4-5")
    p = request_params(model=HAIKU55, system="s", user="u", max_tokens=2000, temperature=0.0)
    assert set(p) == {"model", "max_tokens", "messages", "system"}
    assert p["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request_params(model=HAIKU, system="s", user="u", max_tokens=10, temperature=0.0)["temperature"] == 0.0


def test_haiku_5_5_call_sends_no_sampling_parameter_and_is_charged_at_its_rates():
    """Haiku 5.5 thinks adaptively: its answer comes after a thinking block (empty by default), which the
    text leaves out; the thinking is billed as output, as the usage says."""
    def responder(kw):
        r = make_response('{"ok": 1}', input_tokens=1000, output_tokens=200, cache_read=4000)
        r.content = [SimpleNamespace(type="thinking", thinking="", signature="sig")] + r.content
        return r
    client = FakeAsyncAnthropic(responder)
    usage = MultiModelUsage()
    out = run(call_anthropic_json(client, system="SYS", user="U", model=HAIKU55, max_tokens=2000,
                                  temperature=0.0, usage=usage))
    assert out == '{"ok": 1}'
    kw = client.calls[0]
    assert not {"temperature", "top_p", "top_k", "thinking", "output_config"} & set(kw)
    t = usage.per_model[HAIKU55]
    assert t.prompt_tokens == 1000 + 400 and t.completion_tokens == 200      # reads at 0.1x
    assert t.cost_usd == pytest.approx((1400 * 0.10 + 200 * 0.50) / 1e6)


def test_budget_exceeded_propagates(tmp_path):
    client = FakeAsyncAnthropic(lambda kw: make_response("x", input_tokens=1_000_000, output_tokens=0))
    usage = GuardedUsage(budget_usd=0.5, usage_path=tmp_path / "usage.json")
    with pytest.raises(BudgetExceededError):
        run(call_anthropic_json(client, system="S", user="U", model=HAIKU, max_tokens=10, temperature=0,
                                usage=usage))
    assert (tmp_path / "usage.json").exists()
