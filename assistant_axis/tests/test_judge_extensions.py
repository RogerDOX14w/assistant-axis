"""Tests for the JSON-output parsers and provider routing added to
assistant_axis/judge.py for Phase-2 steering judges.

The original ``parse_judge_score`` (regex-based, 0-3 first-int) keeps
working unchanged; these tests just cover the new ``extract_json_blob``,
``parse_score_reason_json``, ``parse_batch_scores_json``, and
``provider_for_model`` helpers.  Network is never touched; the unified
single-call helper is exercised in test_steering_judges.py with mocked
clients.
"""
from __future__ import annotations

import json

import pytest

from assistant_axis.judge import (
    extract_json_blob,
    parse_batch_scores_json,
    parse_score_reason_json,
    provider_for_model,
)


# ---------------------------------------------------------------------------
# extract_json_blob
# ---------------------------------------------------------------------------

class TestExtractJsonBlob:
    def test_raw_object(self):
        s = '{"score": 2, "reason": "fine"}'
        assert extract_json_blob(s) == s

    def test_fenced_json(self):
        s = '```json\n{"score": 1, "reason": "x"}\n```'
        out = extract_json_blob(s)
        assert json.loads(out) == {"score": 1, "reason": "x"}

    def test_fenced_no_lang(self):
        s = '```\n{"score": 0}\n```'
        out = extract_json_blob(s)
        assert json.loads(out) == {"score": 0}

    def test_prose_wrapping(self):
        s = 'Here is my answer:\n{"score": 3, "reason": "yes"}\nHope that helps!'
        out = extract_json_blob(s)
        assert json.loads(out) == {"score": 3, "reason": "yes"}

    def test_empty_returns_none(self):
        assert extract_json_blob("") is None
        assert extract_json_blob(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# parse_score_reason_json
# ---------------------------------------------------------------------------

class TestParseScoreReasonJson:
    def test_happy_path_default_range(self):
        out = parse_score_reason_json('{"score": 2, "reason": "fine"}')
        assert out == {"score": 2, "reason": "fine"}

    def test_explicit_range_signed(self):
        out = parse_score_reason_json('{"score": -3, "reason": "neg"}', score_range=(-3, 3))
        assert out == {"score": -3, "reason": "neg"}

    def test_score_out_of_range_default(self):
        # +5 not in [0, 3]
        assert parse_score_reason_json('{"score": 5, "reason": "x"}') is None

    def test_score_out_of_range_signed(self):
        # +4 not in [-3, +3]
        assert parse_score_reason_json('{"score": 4}', score_range=(-3, 3)) is None

    def test_string_score_coerces(self):
        # Some judges return "2" as a string; we coerce.
        out = parse_score_reason_json('{"score": "2", "reason": "x"}')
        assert out == {"score": 2, "reason": "x"}

    def test_missing_score_field(self):
        assert parse_score_reason_json('{"reason": "no score"}') is None

    def test_missing_reason_defaults_empty(self):
        out = parse_score_reason_json('{"score": 1}')
        assert out == {"score": 1, "reason": ""}

    def test_non_string_reason_stringified(self):
        out = parse_score_reason_json('{"score": 1, "reason": 42}')
        assert out == {"score": 1, "reason": "42"}

    def test_fenced_input_works(self):
        out = parse_score_reason_json('```json\n{"score": 0, "reason": "z"}\n```')
        assert out == {"score": 0, "reason": "z"}

    def test_unparseable_returns_none(self):
        assert parse_score_reason_json("totally not json") is None
        assert parse_score_reason_json("{not even valid}") is None
        assert parse_score_reason_json("") is None


# ---------------------------------------------------------------------------
# parse_batch_scores_json
# ---------------------------------------------------------------------------

class TestParseBatchScoresJson:
    def test_happy_path_items_key(self):
        text = json.dumps({
            "items": [
                {"id": 0, "score": +2, "reason": "stronger callous"},
                {"id": 9, "score": -1, "reason": "slightly compassionate"},
            ]
        })
        out = parse_batch_scores_json(text, expected_ids=[0, 9])
        assert out == {
            0: {"score": 2, "reason": "stronger callous"},
            9: {"score": -1, "reason": "slightly compassionate"},
        }

    def test_alternate_top_level_keys(self):
        for key in ("responses", "scores", "results"):
            text = json.dumps({key: [{"id": 1, "score": 0}]})
            out = parse_batch_scores_json(text, expected_ids=[1])
            assert out == {1: {"score": 0, "reason": ""}}

    def test_top_level_list_works(self):
        text = json.dumps([{"id": 5, "score": 3}])
        out = parse_batch_scores_json(text, expected_ids=[5], score_range=(0, 3))
        assert out == {5: {"score": 3, "reason": ""}}

    def test_string_id_preserved(self):
        text = json.dumps({"items": [{"id": "q7", "score": 1}]})
        out = parse_batch_scores_json(text, expected_ids=["q7"], score_range=(0, 3))
        assert out == {"q7": {"score": 1, "reason": ""}}

    def test_score_out_of_range_dropped(self, caplog):
        text = json.dumps({
            "items": [
                {"id": 1, "score": 99},  # bad
                {"id": 2, "score": 1},
            ]
        })
        out = parse_batch_scores_json(text, expected_ids=[1, 2], score_range=(0, 3))
        assert out == {2: {"score": 1, "reason": ""}}

    def test_missing_id_leaves_caller_to_fill(self, caplog):
        # Judge omitted id=2 entirely -- we return what we have (id=1)
        # and log a warning about the missing one.
        text = json.dumps({"items": [{"id": 1, "score": 0}]})
        out = parse_batch_scores_json(text, expected_ids=[1, 2], score_range=(0, 3))
        assert out == {1: {"score": 0, "reason": ""}}

    def test_unparseable_returns_none(self):
        assert parse_batch_scores_json("nonsense", expected_ids=[1]) is None
        assert parse_batch_scores_json('{"score": 1}',  # missing list
                                       expected_ids=[1]) is None


# ---------------------------------------------------------------------------
# provider_for_model
# ---------------------------------------------------------------------------

class TestProviderForModel:
    @pytest.mark.parametrize("model", [
        "gpt-4.1-mini", "gpt-4o-mini", "gpt-5-preview", "o3-mini", "o4-mini",
    ])
    def test_openai(self, model):
        assert provider_for_model(model) == "openai"

    @pytest.mark.parametrize("model", [
        "claude-sonnet-4", "claude-haiku-4-5-20251001",
        "claude-3-5-sonnet-20241022",
    ])
    def test_anthropic(self, model):
        assert provider_for_model(model) == "anthropic"

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="unknown judge model"):
            provider_for_model("llama-3-70b")
        with pytest.raises(ValueError):
            provider_for_model("")
