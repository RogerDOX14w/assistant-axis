"""Tests for the JSON-output parsers and provider routing added to
assistant_axis/judge.py for Phase-2 steering judges, plus the
reasoning-friendly upgrade of ``parse_judge_score`` (looks for
``SCORE: <int>`` first, falls back to last [0,3] integer).
``extract_json_blob``, ``parse_score_reason_json``,
``parse_batch_scores_json``, and ``provider_for_model`` are also
covered.  Network is never touched; the unified single-call helper is
exercised in test_steering_judges.py with mocked clients.
"""
from __future__ import annotations

import json

import pytest

from assistant_axis.judge import (
    extract_json_blob,
    parse_batch_scores_json,
    parse_judge_score,
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


# ---------------------------------------------------------------------------
# parse_judge_score (the legacy 0-3 integer parser used by pipeline/3_judge.py)
# ---------------------------------------------------------------------------

class TestParseJudgeScore:
    """The reasoning-friendly upgrade.  Stage 1 looks for an explicit
    ``SCORE: <int>`` marker; stage 2 falls back to the LAST [0, 3]
    integer (so reasoning text with mention of "0", "3" etc. before
    the actual conclusion doesn't mislead the parser).
    """

    def test_old_format_bare_digit(self):
        # Original "Don't say anything else, just the number" template
        # output is a single digit -- still parses correctly.
        assert parse_judge_score("2") == 2
        assert parse_judge_score("0") == 0
        assert parse_judge_score("3") == 3

    def test_score_marker_simple(self):
        assert parse_judge_score("SCORE: 1") == 1
        assert parse_judge_score("Some reasoning here.\nSCORE: 2") == 2

    def test_score_marker_case_insensitive(self):
        assert parse_judge_score("score: 1") == 1
        assert parse_judge_score("Score: 2") == 2
        assert parse_judge_score("SCORE : 3") == 3  # whitespace before colon

    def test_score_marker_beats_first_integer(self):
        # The reasoning mentions "5 traits"; without the marker
        # we'd want the LAST integer (2), but the marker is decisive.
        assert parse_judge_score(
            "The model exhibits 5 traits, score is 2.\nSCORE: 1"
        ) == 1

    def test_no_marker_last_integer_in_range_wins(self):
        # The rubric text recapped in reasoning ("0 if no, 1 if some,
        # 3 if full") would mislead a first-integer parser; the actual
        # judgment lands at the end as "2".
        assert parse_judge_score(
            "0 if no, 1 if some, 3 if full. So I rate this 2"
        ) == 2

    def test_no_marker_just_a_conclusion(self):
        assert parse_judge_score("After analysis, score is 3.") == 3

    def test_marker_with_out_of_range_returns_none(self):
        # Marker explicitly says 4, which is invalid for 0-3.  We do
        # NOT silently fall back to in-range integers elsewhere when
        # the marker is present-but-invalid -- that would be too
        # forgiving (the model meant 4, not 0).
        assert parse_judge_score("score: 4") is None
        assert parse_judge_score("Some reasoning. SCORE: 99") is None

    def test_marker_beats_out_of_range_first_integer(self):
        # Out-of-range integer earlier in the text doesn't poison the
        # parser when an in-range marker is present.
        assert parse_judge_score("It scored 7 out of 10. SCORE: 1") == 1

    def test_out_of_range_no_marker_returns_none(self):
        assert parse_judge_score("5 stars") is None
        assert parse_judge_score("99") is None

    def test_empty_input(self):
        assert parse_judge_score("") is None
        assert parse_judge_score(None) is None  # type: ignore[arg-type]

    def test_no_digits(self):
        assert parse_judge_score("REFUSAL") is None
        assert parse_judge_score("the model refused") is None
