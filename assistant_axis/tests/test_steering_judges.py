"""Tests for assistant_axis/steering_judges.py.

Covers:
- PersonaSpec / SteeringSpec dataclasses (label/description rendering)
- Prompt builders (coherence, RP, effect bidirectional, effect pole)
- NoOpJudgeDispatcher's protocol surface
- RealJudgeDispatcher batch-planning and skip-or-judge decision logic
  (with the network calls mocked)

Network-touching paths (real OpenAI/Anthropic calls, the asyncio loop
thread, retries) are exercised end-to-end on the pod, not here.  These
unit tests pin the prompt structure and the in-process branching.
"""
from __future__ import annotations

import asyncio
import json
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

from assistant_axis import steering_judges as sj
from assistant_axis.steering_judges import (
    EFFECT_MODE_BIDIRECTIONAL,
    EFFECT_MODE_BOTH,
    EFFECT_MODE_SEPARATE_POLES,
    NoOpJudgeDispatcher,
    PersonaSpec,
    RealJudgeDispatcher,
    SteeringSpec,
    build_baseline_lookup,
    build_coherence_prompt,
    build_effect_bidir_batch_prompt,
    build_effect_pole_batch_prompt,
    build_rp_prompt,
)


# ---------------------------------------------------------------------------
# PersonaSpec / SteeringSpec
# ---------------------------------------------------------------------------

class TestSpecs:
    def test_persona_simple(self):
        p = PersonaSpec(role="counselor", description="provides emotional support")
        assert p.display_label() == "counselor"
        assert p.display_description() == "provides emotional support"

    def test_persona_with_traits(self):
        p = PersonaSpec(
            role="counselor", description="emotional support",
            extra_traits=[("compassionate", "warmth"), ("traditional", "old-school")],
        )
        assert p.display_label() == "counselor + compassionate + traditional"
        # Description preserves all parts via " | " join
        desc = p.display_description()
        assert "counselor: emotional support" in desc
        assert "compassionate: warmth" in desc
        assert "traditional: old-school" in desc

    def test_steering_spec(self):
        s = SteeringSpec(
            axis_name="compassionate-callous",
            pos_label="callous", pos_description="hard, indifferent",
            neg_label="compassionate", neg_description="warm, sensitive",
        )
        assert s.axis_name == "compassionate-callous"
        assert s.pos_label == "callous"


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

@pytest.fixture
def persona():
    return PersonaSpec(role="counselor",
                       description="provides compassionate emotional support")


@pytest.fixture
def steering():
    return SteeringSpec(
        axis_name="compassionate-callous",
        pos_label="callous", pos_description="hard, indifferent",
        neg_label="compassionate", neg_description="warm, sensitive",
    )


class TestCoherencePrompt:
    def test_includes_all_required_fields(self, persona, steering):
        p = build_coherence_prompt(
            persona=persona, steering=steering, sign=+1, strength=4.0,
            question="How do I cope with grief?",
            baseline_response="I'm so sorry for your loss...",
            steered_response="Get over it.",
        )
        assert "counselor" in p
        assert "compassionate emotional support" in p
        assert "compassionate-callous" in p
        assert "callous" in p
        assert "hard, indifferent" in p
        assert "compassionate" in p
        assert "How do I cope with grief?" in p
        assert "I'm so sorry for your loss" in p
        assert "Get over it." in p
        # Block delimiters present and used to wrap the response
        assert "[QUESTION START]" in p and "[QUESTION END]" in p
        assert "[BASELINE START]" in p and "[BASELINE END]" in p
        assert "[RESPONSE START]" in p and "[RESPONSE END]" in p
        # Rubric anchors visible
        assert "0-3" in p
        assert "drunk" in p.lower()
        assert "repetition" in p.lower()
        # New v2 anchors: empty/echo as level-2 (c)/level-3 (b)
        assert "echo" in p.lower()                         # echo-of-question
        assert "empty" in p.lower()                        # empty case
        assert "wrong language" in p.lower()               # explicit wrong-lang clause
        # JSON output instruction visible
        assert '"score"' in p

    def test_sign_and_strength_appear(self, persona, steering):
        p_pos = build_coherence_prompt(
            persona=persona, steering=steering, sign=+1, strength=4.0,
            question="q", baseline_response="b", steered_response="r",
        )
        p_neg = build_coherence_prompt(
            persona=persona, steering=steering, sign=-1, strength=2.0,
            question="q", baseline_response="b", steered_response="r",
        )
        assert "+1" in p_pos
        assert "-1" in p_neg
        assert "4.0" in p_pos
        assert "2.0" in p_neg


class TestRPPrompt:
    def test_includes_persona_and_axis(self, persona, steering):
        p = build_rp_prompt(
            persona=persona, steering=steering,
            question="How do I deal with grief?",
            steered_response="Death comes for us all.",
        )
        assert "counselor" in p
        assert "compassionate emotional support" in p
        # Mentions both poles for "may legitimately display..."
        assert "callous" in p
        assert "compassionate" in p
        # Question + answer present
        assert "deal with grief" in p
        assert "Death comes for us all" in p
        # 0-3 rubric scaffolding present
        assert "0-3" in p

    def test_rp_does_not_show_baseline(self, persona, steering):
        # RP rubric only takes the steered response, not the baseline.
        p = build_rp_prompt(
            persona=persona, steering=steering,
            question="q", steered_response="r",
        )
        assert "BASELINE" not in p


class TestEffectBidirBatchPrompt:
    def test_n_items_visible(self, persona, steering):
        items = [
            {"id": i, "question": f"Q{i}",
             "baseline_response": f"B{i}", "steered_response": f"R{i}"}
            for i in range(5)
        ]
        p = build_effect_bidir_batch_prompt(
            persona=persona, steering=steering, sign=-1, strength=8.0,
            items=items,
        )
        assert "5" in p          # n_items
        for i in range(5):
            assert f"Q{i}" in p
            assert f"R{i}" in p
            assert f"B{i}" in p
            # id label appears in the per-item header
            assert f"id={i}" in p
        # -3..+3 scale visible
        assert "-3" in p
        assert "+3" in p


class TestEffectPoleBatchPrompt:
    def test_pos_pole(self, persona, steering):
        items = [{"id": 7, "question": "q",
                  "baseline_response": "b", "steered_response": "r"}]
        p = build_effect_pole_batch_prompt(
            persona=persona, steering=steering, sign=+1, strength=2.0,
            pole="pos", items=items,
        )
        # The pos_label is the "trait to measure" -- that's "callous"
        assert "callous" in p
        # The other-pole label "compassionate" should also appear (for context)
        assert "compassionate" in p
        # 0-3 scale, not -3..+3
        assert "0-3" in p

    def test_neg_pole_swaps_labels(self, persona, steering):
        items = [{"id": 0, "question": "q",
                  "baseline_response": "b", "steered_response": "r"}]
        p = build_effect_pole_batch_prompt(
            persona=persona, steering=steering, sign=-1, strength=1.0,
            pole="neg", items=items,
        )
        # When pole=neg, the trait being measured is the neg pole = compassionate
        # (other_pole_label is callous)
        assert "TRAIT TO MEASURE: compassionate" in p
        assert "the other pole is callous" in p

    def test_invalid_pole_raises(self, persona, steering):
        items = [{"id": 0, "question": "q",
                  "baseline_response": "b", "steered_response": "r"}]
        with pytest.raises(ValueError, match="pole"):
            build_effect_pole_batch_prompt(
                persona=persona, steering=steering, sign=+1, strength=1.0,
                pole="middle", items=items,
            )


# ---------------------------------------------------------------------------
# NoOpJudgeDispatcher
# ---------------------------------------------------------------------------

class TestNoOpDispatcher:
    def test_full_protocol(self):
        d = NoOpJudgeDispatcher()
        rec = {"strength": 1.0, "sign": +1, "question_idx": 0,
               "question": "?", "response": "x", "judges": {}}
        # judge_coherence_blocking returns 0 (no work, sentinel)
        assert d.judge_coherence_blocking(rec) == 0
        # enqueue + drain are no-ops
        d.enqueue_strength_group(
            cell_dir="x", slot=3, layer=25, sign=+1, strength=1.0,
            records=[rec],
        )
        # should_stop_at always False -- sweep runs to max
        assert d.should_stop_at(1.0) is False
        d.drain()


# ---------------------------------------------------------------------------
# RealJudgeDispatcher: pure logic (mocked APIs)
# ---------------------------------------------------------------------------
#
# We mock call_judge_single_unified at the module boundary.  No real
# HTTP requests; no real OpenAI/Anthropic SDK construction (we patch the
# clients to mock instances, never imported real).

@pytest.fixture
def mock_clients(monkeypatch):
    """Patch the AsyncOpenAI/AsyncAnthropic constructors to return dummies.

    The dispatcher only needs them to be non-None; the actual API call
    goes through call_judge_single_unified which we patch separately.
    """
    fake_openai = mock.MagicMock(name="AsyncOpenAI-instance")
    fake_anthropic = mock.MagicMock(name="AsyncAnthropic-instance")

    import openai as openai_mod
    monkeypatch.setattr(openai_mod, "AsyncOpenAI",
                        lambda: fake_openai)
    import anthropic as anthropic_mod
    monkeypatch.setattr(anthropic_mod, "AsyncAnthropic",
                        lambda: fake_anthropic)
    return fake_openai, fake_anthropic


@pytest.fixture
def dispatcher(tmp_path, mock_clients, persona, steering):
    """A dispatcher with stub clients, no baseline."""
    records_path = tmp_path / "records.jsonl"
    records_path.write_text("")
    d = RealJudgeDispatcher(
        records_path=records_path,
        persona=persona, steering=steering,
        baseline_lookup=lambda q_idx: f"baseline-{q_idx}",
        coherence_model="gpt-4.1-mini",
        rp_model="gpt-4.1-mini",
        effect_models=("gpt-4.1-mini", "claude-haiku-4-5-20251001"),
        effect_mode=EFFECT_MODE_BIDIRECTIONAL,
        effect_target_batch_size=10,
        skip_threshold=1.0,
        coh_stop_threshold=1.5,
        max_concurrency=4,
    )
    yield d
    d.shutdown()


def _make_record(q_idx: int, *, strength: float = 1.0, sign: int = +1,
                 coh: int | None = None) -> dict:
    judges = {"coherence": None, "persona": None, "effect": None}
    if coh is not None:
        judges["coherence"] = {
            "score": coh, "reason": "", "model": "test", "ts": 0,
            "rubric_version": 1,
        }
    return {
        "strength": float(strength), "sign": int(sign),
        "slot": 3, "layer": 25,
        "question_idx": int(q_idx), "question": f"Q{q_idx}",
        "response": f"R{q_idx}",
        "n_tokens": 10,
        "judges": judges,
        "timing": {"gen_s": 1.0},
        "abandoned": False,
    }


class TestRealDispatcherSkipLogic:
    def test_skip_when_strength_mean_above_threshold(self, dispatcher, tmp_path):
        """mean(coh) > skip_threshold -> records flagged skipped, no API calls."""
        records = [
            _make_record(0, coh=2),
            _make_record(1, coh=2),
            _make_record(2, coh=2),
        ]
        # mean = 2.0 > skip_threshold=1.0 -> SKIP
        dispatcher.enqueue_strength_group(
            cell_dir=str(tmp_path), slot=3, layer=25, sign=+1,
            strength=1.0, records=records,
        )
        for r in records:
            j = r["judges"]
            assert j["strength_mean_coh"] == pytest.approx(2.0)
            assert j["persona"]["skipped_due_to_strength_mean_coh"] is True
            assert j["effect"]["skipped_due_to_strength_mean_coh"] is True
            # No real persona/effect score populated
            assert j["persona"]["score"] is None
        # Should-stop True (mean >= 1.5)
        assert dispatcher.should_stop_at(1.0) is True

    def test_no_skip_when_strength_mean_below_threshold(self, dispatcher,
                                                       tmp_path, monkeypatch):
        """mean(coh) <= skip_threshold -> async judge work enqueued."""
        # Mock the async call so we don't hit the network; record what got
        # passed in.
        seen_calls = []

        async def fake_call(*, model, prompt, max_tokens, rate_limiter,
                             openai_client=None, anthropic_client=None,
                             temperature=1.0):
            seen_calls.append({"model": model, "prompt_len": len(prompt)})
            # Return a bidirectional batch JSON for both models
            if "items" in prompt and "+3" in prompt:
                # Bidirectional batch
                ids_in_prompt = []
                for i in range(20):
                    if f"id={i}" in prompt:
                        ids_in_prompt.append(i)
                items = [{"id": i, "score": 1, "reason": "test"}
                         for i in ids_in_prompt]
                return json.dumps({"items": items})
            # Persona (RP) call
            return json.dumps({"score": 2, "reason": "test"})

        monkeypatch.setattr(sj, "call_judge_single_unified", fake_call)

        records = [
            _make_record(0, coh=0),
            _make_record(1, coh=1),
            _make_record(2, coh=0),
        ]
        # mean = 1/3 < 1.0 -> JUDGE
        dispatcher.enqueue_strength_group(
            cell_dir=str(tmp_path), slot=3, layer=25, sign=+1,
            strength=1.0, records=records,
        )
        # Drain the async work
        dispatcher.drain(timeout_s=10.0)

        for r in records:
            j = r["judges"]
            assert j["strength_mean_coh"] == pytest.approx(1 / 3, rel=1e-3)
            assert j["persona"]["skipped_due_to_strength_mean_coh"] is False
            assert j["persona"]["score"] == 2
            assert j["effect"]["skipped_due_to_strength_mean_coh"] is False
            assert j["effect"]["combined"] is not None
        # No stop signal (mean << 1.5)
        assert dispatcher.should_stop_at(1.0) is False

        # Verify both effect models were called (one bidir prompt each).
        # Plus persona calls (one per record per RP_model).
        models_called = [c["model"] for c in seen_calls]
        assert "gpt-4.1-mini" in models_called
        assert "claude-haiku-4-5-20251001" in models_called

    def test_rerun_existing_effect_does_not_trip_over_prior_mean(
            self, dispatcher, tmp_path, monkeypatch):
        """Regression: re-judging effect over records that already have an
        effect dict (with a 'mean' float left from the previous run) used
        to crash with 'float object has no attribute get' because the
        mean-computation iteration treated the prior mean float as a
        per-model entry.  Fix: skip the 'mean' key explicitly when
        recomputing.
        """
        # Build a record with PREVIOUSLY-populated effect (containing a
        # float 'mean' under each pole bucket).
        prior = {
            "mode": "bidirectional",
            "bidirectional": {
                "scores": {
                    "gpt-4.1-mini": {"score": 1, "reason": "old"},
                    "claude-haiku-4-5-20251001": {"score": None,
                                                   "reason": "UNPARSEABLE"},
                    "mean": 1.0,
                },
            },
            "combined": 1.0,
            "ts": 0.0,
            "rubric_version": 1,
            "skipped_due_to_strength_mean_coh": False,
        }
        rec = _make_record(0, coh=0)
        rec["judges"]["effect"] = prior

        async def fake_call(*, model, prompt, max_tokens, rate_limiter,
                             openai_client=None, anthropic_client=None,
                             temperature=1.0):
            # Return a valid bidirectional batch payload.
            return json.dumps({
                "items": [{"id": 0, "score": 2, "reason": "new"}]
            })

        # Re-run: dispatcher with rerun_existing=True
        monkeypatch.setattr(sj, "call_judge_single_unified", fake_call)
        dispatcher.rerun_existing = True
        dispatcher.enqueue_strength_group(
            cell_dir=str(tmp_path), slot=3, layer=25, sign=+1,
            strength=1.0, records=[rec],
        )
        dispatcher.drain(timeout_s=10.0)

        # Should NOT have crashed.  New score replaces old per-model entry.
        eff = rec["judges"]["effect"]
        bid = eff["bidirectional"]["scores"]
        assert bid["gpt-4.1-mini"]["score"] == 2
        # mean recomputed correctly without tripping
        assert bid["mean"] == 2.0

    def test_strength_mean_coh_stamped_on_disk(self, dispatcher, tmp_path):
        records = [_make_record(i, coh=2) for i in range(2)]
        dispatcher.enqueue_strength_group(
            cell_dir=str(tmp_path), slot=3, layer=25, sign=+1,
            strength=1.0, records=records,
        )
        # The dispatcher merged updates to records.jsonl
        on_disk = (tmp_path / "records.jsonl").read_text().splitlines()
        on_disk = [json.loads(l) for l in on_disk if l.strip()]
        assert len(on_disk) == 2
        for r in on_disk:
            assert r["judges"]["strength_mean_coh"] == pytest.approx(2.0)


class TestRealDispatcherBatching:
    """The dispatcher reuses plan_response_batches semantics for effect."""

    def test_plan_batches_22_questions_target_10(self, dispatcher):
        records = [_make_record(i) for i in range(22)]
        batches = dispatcher._plan_batches(records)
        # round(22/10) = 2 batches
        assert len(batches) == 2
        # near-equal sizes; both 11
        assert all(len(b) == 11 for b in batches)
        # ids interleave by question_idx (sorted ascending)
        ids = [r["question_idx"] for batch in batches for r in batch]
        assert ids == list(range(22))

    def test_plan_batches_36_questions_target_10(self, dispatcher):
        records = [_make_record(i) for i in range(36)]
        batches = dispatcher._plan_batches(records)
        # round(36/10) = 4 batches; sizes 9,9,9,9
        assert len(batches) == 4
        assert all(len(b) == 9 for b in batches)

    def test_plan_batches_5_questions_target_10(self, dispatcher):
        records = [_make_record(i) for i in range(5)]
        batches = dispatcher._plan_batches(records)
        # round(5/10) = 0 -> max(1, 0) = 1 batch
        assert len(batches) == 1
        assert len(batches[0]) == 5


# ---------------------------------------------------------------------------
# build_baseline_lookup
# ---------------------------------------------------------------------------

class TestBuildBaselineLookup:
    def test_missing_file_returns_empty_string(self, tmp_path, caplog):
        lookup = build_baseline_lookup(tmp_path / "nope.jsonl")
        assert lookup(0) == ""
        assert lookup(99) == ""

    def test_lookup_by_question_idx(self, tmp_path):
        path = tmp_path / "baselines.jsonl"
        with path.open("w") as f:
            f.write(json.dumps({"question_idx": 0, "response": "first"}) + "\n")
            f.write(json.dumps({"question_idx": 7, "response": "seventh"}) + "\n")
        lookup = build_baseline_lookup(path)
        assert lookup(0) == "first"
        assert lookup(7) == "seventh"
        assert lookup(99) == ""  # missing -> empty string
