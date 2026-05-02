"""Tests for assistant_axis.steering_runner.

We don't load a real model.  Instead we build a tiny stand-in
``model``/``tokenizer`` that accepts the inputs the runner actually
produces and returns deterministic ``outputs``, so we can exercise the
runner's loop, restart, and dispatcher-hook semantics without GPU.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest import mock

import pytest
import torch

from assistant_axis import steering_runner
from assistant_axis.steering_judges import NoOpJudgeDispatcher


# ---------------------------------------------------------------------------
# directional_schedule
# ---------------------------------------------------------------------------

class TestDirectionalSchedule:
    def test_geometric_basic(self):
        sched = steering_runner.directional_schedule(
            sign=+1, weakest=1.0, max_strength=8.0, multiplier=2.0
        )
        assert sched == [1.0, 2.0, 4.0, 8.0]

    def test_quarter_octave_matches_notebook(self):
        # Notebook used multiplier ≈ 2**(1/4) = 1.189..., from 1 to 64.
        sched = steering_runner.directional_schedule(
            sign=-1, weakest=1.0, max_strength=64.0, multiplier=1.189
        )
        assert sched[0] == 1.0
        # Last element is the largest <= max_strength
        assert sched[-1] <= 64.0
        # Roughly geometric -- should produce ~25 entries (4 per octave * 6
        # octaves)
        assert 22 <= len(sched) <= 27

    def test_includes_max_when_exact(self):
        sched = steering_runner.directional_schedule(
            sign=+1, weakest=1.0, max_strength=4.0, multiplier=2.0
        )
        assert sched[-1] == 4.0

    def test_rejects_bad_sign(self):
        with pytest.raises(ValueError, match="sign"):
            steering_runner.directional_schedule(
                sign=0, weakest=1.0, max_strength=8.0, multiplier=2.0
            )

    def test_rejects_zero_or_negative(self):
        with pytest.raises(ValueError):
            steering_runner.directional_schedule(
                sign=+1, weakest=0.0, max_strength=8.0, multiplier=2.0
            )

    def test_rejects_max_below_weakest(self):
        with pytest.raises(ValueError, match="max_strength"):
            steering_runner.directional_schedule(
                sign=+1, weakest=10.0, max_strength=2.0, multiplier=2.0
            )


# ---------------------------------------------------------------------------
# _build_position_kwargs
# ---------------------------------------------------------------------------

class TestPositionKwargs:
    def test_all(self):
        assert steering_runner._build_position_kwargs("all") == {"positions": "all"}

    def test_prefill_only(self):
        assert steering_runner._build_position_kwargs("prefill_only") == {"positions": "prefill_only"}

    def test_deferred_modes_raise_not_implemented(self):
        for mode in ("header_matched", "system_only", "user_only", "system_user_only"):
            with pytest.raises(NotImplementedError, match="deferred"):
                steering_runner._build_position_kwargs(mode)

    def test_unknown_mode_raises_value_error(self):
        with pytest.raises(ValueError, match="unknown"):
            steering_runner._build_position_kwargs("nonsense")


# ---------------------------------------------------------------------------
# Mock model + tokenizer for full-runner tests
# ---------------------------------------------------------------------------

class _FakeTokenizer:
    """Minimal tokenizer compatible with the runner's tokenisation path.

    We don't need real BPE; the tokens are character codes, and
    apply_chat_template just concatenates with a separator so we can
    eyeball them.
    """
    pad_token = " "
    pad_token_id = 0
    eos_token = "\n"
    eos_token_id = ord("\n")
    name_or_path = "fake/tokenizer"
    padding_side = "right"

    def apply_chat_template(self, conv, tokenize=False, add_generation_prompt=False, **_):
        # Render as "S: <sys> | U: <user> | A: " so the user-prompt text
        # appears verbatim and is decoded back recognisably.
        sys_msg = next((m["content"] for m in conv if m["role"] == "system"), "")
        usr_msg = next((m["content"] for m in conv if m["role"] == "user"), "")
        text = f"S:{sys_msg}|U:{usr_msg}|A:"
        return text

    def __call__(self, prompts, return_tensors="pt", padding=True):
        # Convert each prompt to a tensor of char codes.  Left-pad to
        # the longest with pad_token_id (= 0).  Returns a plain dict so
        # the runner's `{k: v.to(device) for k, v in inputs.items()}`
        # works (real HF returns a dict-compatible BatchEncoding).
        rows = [list(p.encode("utf-8")) for p in prompts]
        max_len = max(len(r) for r in rows)
        ids = []
        attn = []
        for r in rows:
            pad = max_len - len(r)
            if self.padding_side == "left":
                ids.append([self.pad_token_id] * pad + r)
                attn.append([0] * pad + [1] * len(r))
            else:
                ids.append(r + [self.pad_token_id] * pad)
                attn.append([1] * len(r) + [0] * pad)
        return {
            "input_ids": torch.tensor(ids, dtype=torch.long),
            "attention_mask": torch.tensor(attn, dtype=torch.long),
        }

    def decode(self, ids, skip_special_tokens=False):
        # Drop pad tokens from the start (left-padding) and convert back
        # to string from char codes.
        if isinstance(ids, torch.Tensor):
            ids = ids.tolist()
        # Strip pads (pad_token_id == 0)
        keep = [c for c in ids if c != self.pad_token_id]
        try:
            return bytes(keep).decode("utf-8", errors="replace")
        except Exception:
            return ""


class _FakeModel:
    """Stand-in model whose .generate echoes the persona+question with
    a strength suffix, so the tests can verify what the runner did."""
    def __init__(self, hidden_size=8):
        self.config = SimpleNamespace(hidden_size=hidden_size)
        self._param = torch.nn.Parameter(
            torch.zeros(hidden_size, dtype=torch.bfloat16))
        # Deterministic strength tag set by the tests via .last_strength
        self.calls: List[Dict[str, Any]] = []

    @property
    def device(self):
        return torch.device("cpu")

    def parameters(self):
        return iter([self._param])

    def to(self, *args, **kwargs):
        return self

    def eval(self):
        return self

    def generate(self, *, input_ids, attention_mask=None, max_new_tokens=64,
                 do_sample=False, temperature=None, pad_token_id=0,
                 **_kwargs):
        # Record the call for assertions.
        self.calls.append({
            "input_ids_shape": tuple(input_ids.shape),
            "max_new_tokens": max_new_tokens,
        })
        # Echo: append a deterministic suffix as new tokens.  The runner
        # decodes [prompt_len:] so we just produce a fixed suffix per
        # element, padded to max_new_tokens with pad_token_id.
        batch_size = input_ids.shape[0]
        prompt_len = input_ids.shape[1]
        suffix = b"OK"
        suffix_ids = list(suffix)
        # Pad to max_new_tokens
        pad = [pad_token_id] * (max_new_tokens - len(suffix_ids))
        gen_per_row = suffix_ids + pad
        new_ids = torch.tensor([gen_per_row] * batch_size, dtype=torch.long)
        return torch.cat([input_ids, new_ids], dim=1)


# ---------------------------------------------------------------------------
# Patch ActivationSteering inside the runner so we don't actually try to
# hook the fake model.  We just need to know it was constructed with the
# right kwargs.
# ---------------------------------------------------------------------------

class _FakeActivationSteering:
    construct_calls: List[Dict[str, Any]] = []

    def __init__(self, model, *, steering_vectors, coefficients, layer_indices,
                 positions="all", **_):
        _FakeActivationSteering.construct_calls.append({
            "n_vectors": len(steering_vectors),
            "coefficients": list(coefficients),
            "layer_indices": list(layer_indices),
            "positions": positions,
        })

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture(autouse=True)
def reset_fakes():
    _FakeActivationSteering.construct_calls.clear()
    yield


# ---------------------------------------------------------------------------
# run_steering_cell
# ---------------------------------------------------------------------------

class TestRunSteeringCell:
    def _setup(self, tmp_path, monkeypatch, *, sign=+1, n_questions=4,
               batch_size=2, strengths=None):
        if strengths is None:
            strengths = [1.0, 2.0, 4.0]
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        model = _FakeModel(hidden_size=8)
        tokenizer = _FakeTokenizer()
        axis_vec = torch.zeros(8, dtype=torch.bfloat16)
        out_dir = tmp_path / "cell"
        questions = [f"Q{i}?" for i in range(n_questions)]

        result = steering_runner.run_steering_cell(
            model, tokenizer,
            axis_vector=axis_vec,
            slot=3, layer=25, sign=sign,
            strengths=strengths,
            persona_system_prompt="You are a historian.",
            questions=questions,
            output_dir=out_dir,
            batch_size=batch_size,
            max_new_tokens=8,
            positions_mode="all",
            judge_dispatcher=NoOpJudgeDispatcher(),
        )
        return result, out_dir, model, questions

    def test_completes_full_sweep_when_no_dispatcher_stop(self, tmp_path, monkeypatch):
        result, out_dir, model, questions = self._setup(
            tmp_path, monkeypatch, n_questions=4, batch_size=2,
            strengths=[1.0, 2.0],
        )
        assert result.reason == "completed"
        assert result.stopped_at_strength is None
        # 4 questions x 2 strengths = 8 records
        records = [json.loads(line)
                   for line in (out_dir / "records.jsonl").read_text().splitlines()
                   if line.strip()]
        assert len(records) == 8
        # Schema sanity
        for r in records:
            assert r["slot"] == 3
            assert r["layer"] == 25
            assert r["sign"] == 1
            assert r["judges"] == {"coherence": None, "persona": None, "effect": None}
            assert "response" in r and r["response"]
            assert r["abandoned"] is False
        # Summary present and consistent
        summary = json.loads((out_dir / "summary.json").read_text())
        assert summary["reason"] == "completed"
        assert summary["n_records"] == 8

    def test_uses_correct_signed_coefficient(self, tmp_path, monkeypatch):
        self._setup(tmp_path, monkeypatch, sign=-1,
                    n_questions=2, batch_size=2, strengths=[1.0, 4.0])
        # Each strength fires one ActivationSteering construction (one
        # batch covers both questions at batch_size=2).
        constructs = _FakeActivationSteering.construct_calls
        assert len(constructs) == 2
        assert constructs[0]["coefficients"] == [-1.0]
        assert constructs[1]["coefficients"] == [-4.0]
        assert constructs[0]["layer_indices"] == [25]
        assert constructs[0]["positions"] == "all"

    def test_restart_skips_existing_records(self, tmp_path, monkeypatch):
        # First run: 2 strengths x 2 questions
        self._setup(tmp_path, monkeypatch, n_questions=2, batch_size=2,
                    strengths=[1.0, 2.0])
        first_n_calls = len(_FakeActivationSteering.construct_calls)
        assert first_n_calls == 2  # one per strength

        # Second run: same args + an additional strength.  The first 2
        # strengths' records should be reused; only the new strength
        # should generate.
        _FakeActivationSteering.construct_calls.clear()
        result, out_dir, _, _ = self._setup(
            tmp_path, monkeypatch, n_questions=2, batch_size=2,
            strengths=[1.0, 2.0, 4.0],
        )
        # Only the new strength=4.0 should have triggered generation
        assert len(_FakeActivationSteering.construct_calls) == 1
        assert _FakeActivationSteering.construct_calls[0]["coefficients"] == [4.0]
        # Total records: 3 strengths x 2 questions = 6
        records = [json.loads(line)
                   for line in (out_dir / "records.jsonl").read_text().splitlines()
                   if line.strip()]
        assert len(records) == 6

    def test_dispatcher_can_stop_sweep_early(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        class StopAfterTwo:
            """Two-tier dispatcher fixture matching the new protocol.

            judge_coherence_blocking returns 0 (records flow through);
            enqueue_strength_group records the call;
            should_stop_at returns True after the second strength group.
            """
            def __init__(self):
                self.seen_strengths = []
                self.coh_called_for = []
                self.enqueued_groups = []
                self.drained = False

            def judge_coherence_blocking(self, record):
                self.coh_called_for.append(record["question_idx"])
                # Stamp the record so downstream stays consistent with
                # what RealJudgeDispatcher would have done.
                record.setdefault("judges", {})["coherence"] = {
                    "score": 0, "reason": "test", "model": "test",
                    "ts": 0, "rubric_version": 1,
                }
                return 0

            def enqueue_strength_group(self, *, cell_dir, slot, layer, sign,
                                       strength, records):
                self.enqueued_groups.append({
                    "strength": strength, "n": len(records),
                })

            def should_stop_at(self, strength):
                self.seen_strengths.append(strength)
                return len(self.seen_strengths) >= 2

            def drain(self, timeout_s=None):
                self.drained = True

            def write_records_atomic(self, records):
                # Mirror RealJudgeDispatcher.write_records_atomic so the
                # runner's _flush_records prefers our path.  Just defer
                # to write_jsonl (no concurrent writers in tests).
                from assistant_axis.atomic_io import write_jsonl
                write_jsonl(records, tmp_path / "cell" / "records.jsonl")

        dispatcher = StopAfterTwo()
        model = _FakeModel(hidden_size=8)
        tokenizer = _FakeTokenizer()

        result = steering_runner.run_steering_cell(
            model, tokenizer,
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0, 4.0, 8.0],
            persona_system_prompt="hist",
            questions=["q1", "q2"],
            output_dir=tmp_path / "cell",
            batch_size=2,
            max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=dispatcher,
        )

        assert result.reason == "incoherent"
        assert result.stopped_at_strength == 2.0
        # Records for the first 2 strengths (4 total), but NOT the 3rd or 4th
        records = [json.loads(line)
                   for line in (tmp_path / "cell/records.jsonl").read_text().splitlines()
                   if line.strip()]
        assert len(records) == 4
        assert sorted({r["strength"] for r in records}) == [1.0, 2.0]
        # Coherence judged on every record (4 = 2 strengths * 2 questions).
        assert len(dispatcher.coh_called_for) == 4
        # Two strength groups enqueued (one per completed strength).
        assert [g["strength"] for g in dispatcher.enqueued_groups] == [1.0, 2.0]
        assert all(g["n"] == 2 for g in dispatcher.enqueued_groups)
        # Stop check ran after each of the 2 completed strengths.
        assert dispatcher.seen_strengths == [1.0, 2.0]
        # Drain called at the end.
        assert dispatcher.drained is True

    def test_skip_when_summary_already_says_stopped(self, tmp_path, monkeypatch):
        # Pre-create a summary.json with a stop already recorded.
        out_dir = tmp_path / "cell"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text(json.dumps({
            "stopped_at_strength": 4.0,
            "reason": "incoherent",
            "n_records": 99,
            "n_strengths_swept": 5,
        }))
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        result = steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0],
            persona_system_prompt="hist",
            questions=["q1"],
            output_dir=out_dir, batch_size=1, max_new_tokens=4,
            positions_mode="all",
        )

        assert result.reason == "incoherent"
        assert result.stopped_at_strength == 4.0
        # Should NOT have triggered any new generation
        assert _FakeActivationSteering.construct_calls == []


# ---------------------------------------------------------------------------
# compute_baselines
# ---------------------------------------------------------------------------

class TestComputeBaselines:
    def test_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        model = _FakeModel(8)
        tokenizer = _FakeTokenizer()
        questions = ["q0", "q1", "q2"]

        steering_runner.compute_baselines(
            model, tokenizer,
            persona_system_prompt="persona",
            questions=questions,
            output_dir=tmp_path,
            batch_size=2, max_new_tokens=4,
        )
        first_call_count = len(model.calls)
        assert first_call_count >= 1

        # Second invocation should be a no-op (all questions already done).
        steering_runner.compute_baselines(
            model, tokenizer,
            persona_system_prompt="persona",
            questions=questions,
            output_dir=tmp_path,
            batch_size=2, max_new_tokens=4,
        )
        # No additional generation calls
        assert len(model.calls) == first_call_count

        # Records on disk
        baselines = [json.loads(line) for line in
                     (tmp_path / "baselines/records.jsonl").read_text().splitlines()
                     if line.strip()]
        assert len(baselines) == 3
        assert {r["question_idx"] for r in baselines} == {0, 1, 2}
        for r in baselines:
            assert r["strength"] == 0.0
            assert r["sign"] == 0
