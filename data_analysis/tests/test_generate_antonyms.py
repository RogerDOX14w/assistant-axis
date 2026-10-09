"""Tests for generate_antonyms.py: the classify call parses reasoning-first
JSON and ticks the usage tracker."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from assistant_axis.judge_pricing import MultiModelUsage
from data_analysis import generate_antonyms as module

INSTRUCTIONS = [{"pos": f"pos {i}", "neg": f"neg {i}"} for i in range(5)]
REPLY = {"reasoning": "the neg pole is humility", "negative_label": "humble", "antonym_score": 4}


def _client(text: str, usage=None) -> AsyncMock:
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text=text)]
    resp.usage = usage if usage is not None else MagicMock(input_tokens=500, output_tokens=80)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


class TestClassifyOne:
    def test_parses_reply_and_charges_usage(self):
        tracker = MultiModelUsage()
        result = asyncio.run(module.classify_one(
            _client(json.dumps(REPLY)), "arrogant", "Excessive confidence.", INSTRUCTIONS,
            asyncio.Semaphore(2), tracker,
        ))
        assert result["negative_label"] == "humble" and result["antonym_score"] == 4
        assert tracker.n_calls == 1
        assert tracker.total_prompt_tokens == 500 and tracker.total_completion_tokens == 80
        assert list(tracker.per_model) == [module.MODEL]

    def test_strips_fences_and_tolerates_no_tracker(self):
        text = "```json\n" + json.dumps(REPLY) + "\n```"
        result = asyncio.run(module.classify_one(
            _client(text), "arrogant", "Excessive confidence.", INSTRUCTIONS, asyncio.Semaphore(2),
        ))
        assert result["negative_label"] == "humble"

    def test_user_message_carries_definition_and_both_poles(self):
        msg = module.build_user_message("arrogant", "Excessive confidence.", INSTRUCTIONS)
        assert "positive_label: arrogant" in msg and "Definition: Excessive confidence." in msg
        assert "1. pos 0" in msg and "5. neg 4" in msg


class TestNamePos:
    """--name-pos: a label-blind call that names the pole the pos instructions describe."""

    POS_REPLY = {"reasoning": "all five push to change the world", "positive_name": "enterprising|driven"}

    def test_message_is_label_blind_and_pos_only(self):
        msg = module.build_pos_name_message(INSTRUCTIONS)
        assert "1. pos 0" in msg and "5. pos 4" in msg
        assert "neg" not in msg and "positive_label" not in msg and "Definition" not in msg

    def test_parses_reply_charges_usage_and_uses_its_own_prompt(self):
        tracker = MultiModelUsage()
        client = _client("```json\n" + json.dumps(self.POS_REPLY) + "\n```")
        result = asyncio.run(module.name_pos_one(client, INSTRUCTIONS, asyncio.Semaphore(2), tracker, "x"))
        assert result["positive_name"] == "enterprising|driven"
        assert tracker.n_calls == 1
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["system"] == module.POS_NAME_SYSTEM_PROMPT
        assert "arrogant" not in kwargs["messages"][0]["content"]

    def test_reply_without_the_field_is_retried_then_an_error_sentinel(self, monkeypatch):
        async def no_sleep(_):
            return None
        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        client = _client(json.dumps({"reasoning": "?", "negative_label": "x"}))
        result = asyncio.run(module.name_pos_one(client, INSTRUCTIONS, asyncio.Semaphore(2)))
        assert result["positive_name"] == "ERROR"
        assert client.messages.create.call_count == 5

    def test_flag_is_off_by_default(self):
        assert module.parse_args([]).name_pos is False
        assert module.parse_args(["--name-pos"]).name_pos is True
