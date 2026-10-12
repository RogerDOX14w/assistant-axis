"""Request parameters by model in assistant_axis/judge.py (code review
2026-10-12, B1: reviews 7 D1 and 8 D3).

* A temperature equal to the provider default (1) is never sent, on either
  provider, so a default call works on models that refuse the field.
* ``MODEL_CAPABILITIES`` lists the non-default cases (models that refuse a
  temperature); a non-default temperature for one of them raises
  ``JudgeRequestError`` before anything is sent.
* An HTTP 400 from either SDK is raised as ``JudgeRequestError``, not logged
  and turned into None (which made every item of a run unparseable).

No network: the clients are fakes.
"""
from __future__ import annotations

import asyncio
from types import SimpleNamespace

import httpx
import pytest

from assistant_axis import judge as J
from assistant_axis.judge import (
    DEFAULT_TEMPERATURE,
    MODEL_CAPABILITIES,
    JudgeRequestError,
    RateLimiter,
    accepts_temperature,
    call_anthropic_judge_single,
    call_judge_batch,
    call_judge_single,
    call_judge_single_unified,
    chat_request_body,
    model_capabilities,
    request_temperature,
)


class _Status400(Exception):
    status_code = 400


class _Status500(Exception):
    status_code = 500


def _openai_response(text="SCORE: 2"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text))], usage=None)


def _anthropic_response(text="SCORE: 2"):
    return SimpleNamespace(content=[SimpleNamespace(text=text)], usage=None)


class FakeOpenAI:
    def __init__(self, fail_on=None, exc=None):
        self.calls = []
        self.fail_on, self.exc = fail_on, exc

        async def create(**kw):
            self.calls.append(kw)
            if self.exc is not None and (self.fail_on is None or self.fail_on in kw["messages"][0]["content"]):
                raise self.exc
            return _openai_response()
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


class FakeAnthropic:
    def __init__(self, exc=None):
        self.calls = []
        self.exc = exc

        async def create(**kw):
            self.calls.append(kw)
            if self.exc is not None:
                raise self.exc
            return _anthropic_response()
        self.messages = SimpleNamespace(create=create)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# the capability table
# ---------------------------------------------------------------------------

class TestModelCapabilities:
    @pytest.mark.parametrize("model", [
        "gpt-4.1-mini", "gpt-4o-mini", "claude-haiku-4-5-20251001", "claude-haiku-4-5",
        "claude-3-5-haiku-20241022", "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-opus-4-6",
        "claude-3-5-sonnet-20241022",
    ])
    def test_models_that_take_a_temperature(self, model):
        assert accepts_temperature(model)
        assert model_capabilities(model) == {"temperature": True}

    @pytest.mark.parametrize("model", [
        "claude-haiku-5-5", "CLAUDE-HAIKU-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-4-7",
        "claude-opus-4-8", "o1-mini", "o3-mini", "o4-mini", "gpt-5-mini", "gpt-5.6-luna", "gpt-6-luna",
    ])
    def test_models_that_refuse_one(self, model):
        assert not accepts_temperature(model)

    def test_the_platform_list_is_covered(self):
        """judge.py keeps its own copy (pipeline/3_judge.py imports judge.py without the package, so it cannot
        import gapgen); every fragment of the platform's list refuses here too."""
        from assistant_axis.gapgen.llm import NO_TEMPERATURE_FRAGMENTS, accepts_temperature as platform_accepts
        for frag in NO_TEMPERATURE_FRAGMENTS:
            assert MODEL_CAPABILITIES.get(frag) == {"temperature": False}, frag
        for model in ("claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-4-7",
                      "claude-opus-4-8", "claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"):
            assert accepts_temperature(model) == platform_accepts(model), model


class TestRequestTemperature:
    def test_default_and_none_are_left_out(self):
        for model in ("gpt-4.1-mini", "claude-haiku-4-5", "claude-haiku-5-5", "claude-opus-4-7", "gpt-6-luna"):
            assert request_temperature(model, None) is None
            assert request_temperature(model, DEFAULT_TEMPERATURE) is None
            assert request_temperature(model, 1) is None

    def test_non_default_is_sent_where_taken(self):
        assert request_temperature("claude-haiku-4-5", 0.0) == 0.0
        assert request_temperature("gpt-4.1-mini", 0.7) == 0.7

    def test_non_default_on_a_refusing_model_raises(self):
        with pytest.raises(JudgeRequestError, match="claude-haiku-5-5 refuses a temperature"):
            request_temperature("claude-haiku-5-5", 0.0)
        with pytest.raises(JudgeRequestError):
            request_temperature("gpt-6-luna", 0.0)


# ---------------------------------------------------------------------------
# the request builders
# ---------------------------------------------------------------------------

class TestChatRequestBody:
    def test_no_temperature_at_the_default(self):
        body = chat_request_body("p", "gpt-4.1-mini", 200)
        assert body == {"model": "gpt-4.1-mini", "messages": [{"role": "user", "content": "p"}],
                        "max_completion_tokens": 200}
        assert "temperature" not in body

    def test_a_non_default_temperature_is_sent(self):
        assert chat_request_body("p", "gpt-4.1-mini", 200, temperature=0.0)["temperature"] == 0.0

    def test_refusing_model_raises_before_sending(self):
        with pytest.raises(JudgeRequestError):
            chat_request_body("p", "o3-mini", 200, temperature=0.0)

    def test_live_call_sends_the_same_body(self):
        client = FakeOpenAI()
        out = _run(call_judge_single(client, "p", "gpt-4.1-mini", 200, RateLimiter(1000)))
        assert out == "SCORE: 2"
        assert client.calls == [chat_request_body("p", "gpt-4.1-mini", 200)]
        assert "temperature" not in client.calls[0]


class TestAnthropicRequest:
    def test_default_temperature_is_not_sent(self):
        client = FakeAnthropic()
        _run(call_anthropic_judge_single(client, "p", "claude-haiku-4-5", 100, RateLimiter(1000)))
        assert client.calls == [{"model": "claude-haiku-4-5", "max_tokens": 100,
                                 "messages": [{"role": "user", "content": "p"}]}]

    def test_default_temperature_on_a_refusing_model_is_not_sent(self):
        """Opus 4.7 and later refuse any temperature, the default included: the call goes out without it."""
        client = FakeAnthropic()
        out = _run(call_anthropic_judge_single(client, "p", "claude-opus-4-7", 100, RateLimiter(1000),
                                               temperature=1.0))
        assert out == "SCORE: 2" and "temperature" not in client.calls[0]

    def test_non_default_temperature_is_sent_where_taken(self):
        client = FakeAnthropic()
        _run(call_anthropic_judge_single(client, "p", "claude-haiku-4-5", 100, RateLimiter(1000), temperature=0.0))
        assert client.calls[0]["temperature"] == 0.0

    def test_non_default_on_a_refusing_model_raises_before_any_call(self):
        client = FakeAnthropic()
        with pytest.raises(JudgeRequestError):
            _run(call_anthropic_judge_single(client, "p", "claude-haiku-5-5", 100, RateLimiter(1000),
                                             temperature=0.0))
        assert client.calls == []


class TestUnified:
    def test_temperature_reaches_the_openai_path(self):
        client = FakeOpenAI()
        _run(call_judge_single_unified(prompt="p", model="gpt-4.1-mini", max_tokens=50,
                                       rate_limiter=RateLimiter(1000), openai_client=client, temperature=0.0))
        assert client.calls[0]["temperature"] == 0.0

    def test_default_sends_none_on_either_path(self):
        oa, an = FakeOpenAI(), FakeAnthropic()
        for model in ("gpt-4.1-mini", "claude-haiku-4-5-20251001"):
            _run(call_judge_single_unified(prompt="p", model=model, max_tokens=50, rate_limiter=RateLimiter(1000),
                                           openai_client=oa, anthropic_client=an))
        assert "temperature" not in oa.calls[0] and "temperature" not in an.calls[0]


# ---------------------------------------------------------------------------
# an HTTP 400 is raised, other failures still give None
# ---------------------------------------------------------------------------

def _sdk_400(sdk):
    req = httpx.Request("POST", "https://api.example.invalid/v1")
    return sdk.BadRequestError(message="`temperature` is deprecated for this model",
                               response=httpx.Response(400, request=req), body=None)


class TestBadRequestIsSurfaced:
    def test_openai_400_raises(self):
        import openai
        client = FakeOpenAI(exc=_sdk_400(openai))
        with pytest.raises(JudgeRequestError, match="HTTP 400 from judge model gpt-4.1-mini"):
            _run(call_judge_single(client, "p", "gpt-4.1-mini", 200, RateLimiter(1000)))

    def test_anthropic_400_raises(self):
        import anthropic
        client = FakeAnthropic(exc=_sdk_400(anthropic))
        with pytest.raises(JudgeRequestError, match="deprecated for this model"):
            _run(call_anthropic_judge_single(client, "p", "claude-opus-4-7", 100, RateLimiter(1000)))

    def test_unified_400_raises(self):
        client = FakeAnthropic(exc=_Status400("bad"))
        with pytest.raises(JudgeRequestError):
            _run(call_judge_single_unified(prompt="p", model="claude-haiku-5-5", max_tokens=50,
                                           rate_limiter=RateLimiter(1000), anthropic_client=client))

    def test_other_failures_still_give_none(self):
        assert _run(call_judge_single(FakeOpenAI(exc=_Status500("server")), "p", "gpt-4.1-mini", 200,
                                      RateLimiter(1000))) is None
        assert _run(call_anthropic_judge_single(FakeAnthropic(exc=RuntimeError("network")), "p",
                                                "claude-haiku-4-5", 100, RateLimiter(1000))) is None

    def test_batch_raises_on_a_400_and_keeps_none_for_other_failures(self):
        client = FakeOpenAI(fail_on="bad", exc=_Status400("bad request"))
        with pytest.raises(JudgeRequestError):
            _run(call_judge_batch(client, ["ok 1", "bad 2", "ok 3"], "gpt-4.1-mini", 200, RateLimiter(1000)))
        client = FakeOpenAI(fail_on="bad", exc=_Status500("server"))
        out = _run(call_judge_batch(client, ["ok 1", "bad 2", "ok 3"], "gpt-4.1-mini", 200, RateLimiter(1000)))
        assert out == ["SCORE: 2", None, "SCORE: 2"]

    def test_the_error_is_a_value_error(self):
        """Callers that catch ValueError for a bad request keep working."""
        assert issubclass(JudgeRequestError, ValueError)
        assert J._is_bad_request(_Status400()) and not J._is_bad_request(_Status500())


# ---------------------------------------------------------------------------
# B1b: a 400 that flags one prompt's content stays per-item
# ---------------------------------------------------------------------------

#: The inner error objects the OpenAI SDK puts in ``body`` (and whose ``code`` it copies onto the exception).
OPENAI_FLAGGED = {"message": "Invalid prompt: your prompt was flagged as potentially violating our usage policy. "
                             "Please try again with a different prompt.",
                  "type": "invalid_request_error", "param": None, "code": "invalid_prompt"}
OPENAI_TEMPERATURE = {"message": "Unsupported value: 'temperature' does not support 0 with this model. Only the "
                                 "default (1) value is supported.",
                      "type": "invalid_request_error", "param": "temperature", "code": "unsupported_value"}
#: The Anthropic SDK keeps the whole error document in ``body`` and sets no ``code``.
ANTHROPIC_TEMPERATURE = {"type": "error", "error": {"type": "invalid_request_error",
                                                   "message": "`temperature` is deprecated for this model."}}


def _openai_400(body):
    import openai
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    return openai.BadRequestError(f"Error code: 400 - {{'error': {body}}}", response=httpx.Response(400, request=req),
                                  body=body)


def _anthropic_400(body):
    import anthropic
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.BadRequestError(f"Error code: 400 - {body}", response=httpx.Response(400, request=req),
                                     body=body)


@pytest.fixture
def flagged(monkeypatch, caplog):
    monkeypatch.setattr(J, "CONTENT_FLAGGED", {})
    caplog.set_level("WARNING", logger="assistant_axis.judge")
    return caplog


class TestContentFlaggedPromptIsPerItem:
    def test_the_two_openai_400s_are_told_apart(self):
        assert J.content_flag(_openai_400(OPENAI_FLAGGED)) == "invalid_prompt"
        assert J.content_flag(_openai_400(OPENAI_TEMPERATURE)) is None
        assert J.content_flag(_openai_400({"message": "x", "code": "content_policy_violation"})) \
            == "content_policy_violation"
        assert J.content_flag(_anthropic_400(ANTHROPIC_TEMPERATURE)) is None
        # a code nested in the body, and the phrase fallback where no code says it
        assert J.content_flag(_Status400("bad")) is None
        e = _Status400("x")
        e.body = {"error": {"code": "content_filter", "message": "filtered"}}
        assert J.content_flag(e) == "content_filter"
        assert J.content_flag(_Status400("Your prompt was flagged as potentially violating our usage policy")) \
            == "flagged as potentially violating"
        assert J.content_flag(_Status500("flagged as potentially violating")) is None   # only a 400

    def test_single_call_gives_none_and_warns(self, flagged):
        out = _run(call_judge_single(FakeOpenAI(exc=_openai_400(OPENAI_FLAGGED)), "p", "gpt-4.1-mini", 200,
                                     RateLimiter(1000)))
        assert out is None
        assert J.CONTENT_FLAGGED == {"gpt-4.1-mini": 1}
        assert "content flag (invalid_prompt) from judge model gpt-4.1-mini" in flagged.text
        assert "1 flagged so far" in flagged.text

    def test_batch_keeps_the_other_items(self, flagged):
        client = FakeOpenAI(fail_on="bad", exc=_openai_400(OPENAI_FLAGGED))
        out = _run(call_judge_batch(client, ["ok 1", "bad 2", "ok 3", "bad 4"], "gpt-4.1-mini", 200,
                                    RateLimiter(1000)))
        assert out == ["SCORE: 2", None, "SCORE: 2", None]
        assert J.CONTENT_FLAGGED == {"gpt-4.1-mini": 2} and "2 flagged so far" in flagged.text

    def test_anthropic_and_unified_paths(self, flagged):
        flag_doc = {"type": "error", "error": {"type": "invalid_request_error",
                                               "message": "Your prompt was flagged as potentially violating our "
                                                          "usage policy."}}
        assert _run(call_anthropic_judge_single(FakeAnthropic(exc=_anthropic_400(flag_doc)), "p",
                                                "claude-haiku-4-5", 100, RateLimiter(1000))) is None
        assert _run(call_judge_single_unified(prompt="p", model="gpt-4.1-mini", max_tokens=50,
                                              rate_limiter=RateLimiter(1000),
                                              openai_client=FakeOpenAI(exc=_openai_400(OPENAI_FLAGGED)))) is None
        assert _run(call_judge_single_unified(prompt="p", model="claude-haiku-4-5", max_tokens=50,
                                              rate_limiter=RateLimiter(1000),
                                              anthropic_client=FakeAnthropic(exc=_anthropic_400(flag_doc)))) is None
        assert J.CONTENT_FLAGGED == {"claude-haiku-4-5": 2, "gpt-4.1-mini": 1}
        assert flagged.text.count("HTTP 400 content flag") == 3

    def test_an_unsupported_parameter_400_still_raises_in_every_path(self, flagged):
        rl = RateLimiter(1000)
        with pytest.raises(JudgeRequestError, match="does not support 0"):
            _run(call_judge_single(FakeOpenAI(exc=_openai_400(OPENAI_TEMPERATURE)), "p", "gpt-4.1-mini", 200, rl))
        with pytest.raises(JudgeRequestError):
            _run(call_judge_batch(FakeOpenAI(fail_on="bad", exc=_openai_400(OPENAI_TEMPERATURE)),
                                  ["ok 1", "bad 2"], "gpt-4.1-mini", 200, rl))
        with pytest.raises(JudgeRequestError, match="deprecated for this model"):
            _run(call_anthropic_judge_single(FakeAnthropic(exc=_anthropic_400(ANTHROPIC_TEMPERATURE)), "p",
                                             "claude-opus-4-7", 100, rl))
        with pytest.raises(JudgeRequestError):
            _run(call_judge_single_unified(prompt="p", model="gpt-4.1-mini", max_tokens=50, rate_limiter=rl,
                                           openai_client=FakeOpenAI(exc=_openai_400(OPENAI_TEMPERATURE))))
        with pytest.raises(JudgeRequestError):
            _run(call_judge_single_unified(prompt="p", model="claude-opus-4-7", max_tokens=50, rate_limiter=rl,
                                           anthropic_client=FakeAnthropic(exc=_anthropic_400(ANTHROPIC_TEMPERATURE))))
        assert J.CONTENT_FLAGGED == {}
        assert "content flag" not in flagged.text
