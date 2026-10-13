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
# BidirectionalCursor (2026-05-14: new default scan_mode)
# ---------------------------------------------------------------------------


class TestDecodeWithTruncationMarker:
    """The HF generate convention is that once a sequence emits a stop
    token, the remaining positions in its row of the output tensor are
    filled with ``pad_token_id``.  ``_decode_with_truncation_marker``
    detects truncation = "zero pad tokens in the generated slice =
    model never reached a stop = max_new_tokens cap was hit"."""

    def _tok(self):
        # Minimal tokenizer stand-in.  pad_token_id=0; decode treats the
        # token IDs as raw bytes via _FakeTokenizer convention but here
        # we just need pad_token_id + decode(skip_special_tokens=True).
        class _T:
            pad_token_id = 0

            def decode(self, ids, skip_special_tokens=False):
                if isinstance(ids, torch.Tensor):
                    ids = ids.tolist()
                # Strip pad bytes; convert remaining to ascii.
                keep = [c for c in ids if c != 0]
                try:
                    return bytes(keep).decode("utf-8", errors="replace")
                except Exception:
                    return ""

        return _T()

    def test_natural_stop_no_marker(self):
        """Generated 'OK' then pad-filled to max_new_tokens=8 -> not
        truncated, no marker appended."""
        gen_ids = torch.tensor(list(b"OK") + [0] * 6, dtype=torch.long)
        response, n_tok, truncated = (
            steering_runner._decode_with_truncation_marker(gen_ids, self._tok())
        )
        assert response == "OK"
        assert n_tok == 2
        assert truncated is False

    def test_truncated_appends_marker(self):
        """Generated 8 real tokens with zero pad -> truncated, " …" appended."""
        gen_ids = torch.tensor(list(b"truncate"), dtype=torch.long)
        assert len(gen_ids) == 8
        response, n_tok, truncated = (
            steering_runner._decode_with_truncation_marker(gen_ids, self._tok())
        )
        assert response == "truncate …"
        assert n_tok == 8
        assert truncated is True

    def test_n_tok_excludes_pad(self):
        """n_tokens is the count of non-pad tokens."""
        gen_ids = torch.tensor(list(b"hi") + [0] * 14, dtype=torch.long)
        _, n_tok, truncated = (
            steering_runner._decode_with_truncation_marker(gen_ids, self._tok())
        )
        assert n_tok == 2
        assert truncated is False


class TestBidirectionalCursor:
    """Unit tests for the lazy bidirectional geometric strength cursor."""

    def test_centre_anchor(self):
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=64.0, min_strength=0.125,
            multiplier=1.189, start_steps_up=2,
        )
        # s_init = 1.0 * 1.189**2 ≈ 1.4136
        assert abs(c.s_init - 1.413721) < 1e-6

    def test_first_three_up(self):
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=64.0, min_strength=0.125,
            multiplier=1.189, start_steps_up=2,
        )
        ups = [c.next_up() for _ in range(3)]
        # s_init * 1.189, * 1.189**2, * 1.189**3
        assert ups[0] == pytest.approx(1.413721 * 1.189, rel=1e-4)
        assert ups[1] == pytest.approx(1.413721 * 1.189**2, rel=1e-4)
        assert ups[2] == pytest.approx(1.413721 * 1.189**3, rel=1e-4)
        # Monotonic increasing
        assert ups[0] < ups[1] < ups[2]

    def test_first_three_down(self):
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=64.0, min_strength=0.125,
            multiplier=1.189, start_steps_up=2,
        )
        downs = [c.next_down() for _ in range(3)]
        # s_init / 1.189, / 1.189**2, / 1.189**3 = 1.189, 1.0, 0.841
        assert downs[0] == pytest.approx(1.189, rel=1e-3)
        assert downs[1] == pytest.approx(1.0, rel=1e-3)
        assert downs[2] == pytest.approx(0.841, rel=1e-3)
        # Monotonic decreasing
        assert downs[0] > downs[1] > downs[2]

    def test_up_exhausts_at_max(self):
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=2.0, min_strength=0.5,
            multiplier=2.0, start_steps_up=0,
        )
        # s_init=1.0, next_up=2.0 (=max, allowed),
        # next_up=4.0 (> max, None).
        assert c.s_init == 1.0
        assert c.next_up() == pytest.approx(2.0)
        assert c.next_up() is None
        assert c.up_exhausted is True
        # Idempotent: keeps returning None
        assert c.next_up() is None

    def test_down_exhausts_at_min(self):
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=4.0, min_strength=0.25,
            multiplier=2.0, start_steps_up=0,
        )
        # s_init=1.0, next_down=0.5, next_down=0.25 (=min, allowed),
        # next_down=0.125 (< min, None).
        assert c.next_down() == pytest.approx(0.5)
        assert c.next_down() == pytest.approx(0.25)
        assert c.next_down() is None
        assert c.down_exhausted is True

    def test_geometric_chain_to_floor(self):
        """Plan §9.1 spec: with weakest=1.0, mult=1.189, max=64, min=0.125,
        the DOWN chain extends from s_init=1.414 down to just above 0.125
        (with mult=1.189 the closest stop is around 0.125, the next would
        be ~0.105 = exhausted)."""
        c = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=64.0, min_strength=0.125,
            multiplier=1.189, start_steps_up=2,
        )
        downs = []
        while True:
            v = c.next_down()
            if v is None:
                break
            downs.append(v)
        # Last value should be just at-or-above floor; next would be below.
        assert downs[-1] >= 0.125 * (1.0 - 1e-9)
        # The chain should fit in a sensible window: roughly
        # log_1.189(1.414/0.125) ≈ 14 steps.
        assert 12 <= len(downs) <= 16

    def test_rejects_min_above_weakest(self):
        with pytest.raises(ValueError, match="min_strength"):
            steering_runner.BidirectionalCursor(
                weakest=1.0, max_strength=64.0, min_strength=2.0,
                multiplier=1.189,
            )

    def test_rejects_bad_multiplier(self):
        with pytest.raises(ValueError, match="multiplier"):
            steering_runner.BidirectionalCursor(
                weakest=1.0, max_strength=64.0, min_strength=0.125,
                multiplier=1.0,
            )

    def test_allows_negative_start_steps_when_above_min_strength(self):
        # Negative start_steps_up means s_init < weakest (e.g. start
        # below the historical floor when the coh cliff is already
        # close to weakest).  Allowed as long as s_init >= min_strength.
        # Required by sweep_start_heuristics.OVERRIDES for the
        # (all, slot=7, layer=49) cell on Qwen-3-32B (start_steps=-3).
        cursor = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=64.0, min_strength=0.125,
            multiplier=1.189, start_steps_up=-3,
        )
        # 1.189^-3 ≈ 0.595, well above min_strength=0.125.
        assert cursor.s_init == pytest.approx(0.595, abs=0.005)

    def test_rejects_start_below_min_strength(self):
        # When the resolved s_init falls below the safety floor we
        # fail-loud rather than silently clamping; operator should
        # either raise start_steps or lower min_strength.
        with pytest.raises(ValueError, match="min_strength"):
            steering_runner.BidirectionalCursor(
                weakest=1.0, max_strength=64.0, min_strength=0.5,
                multiplier=1.189, start_steps_up=-5,
            )

    def test_negative_start_walks_up_correctly(self):
        # The cursor must walk UP through weakest when starting below
        # it, so the schedule still covers the productive band.
        cursor = steering_runner.BidirectionalCursor(
            weakest=1.0, max_strength=8.0, min_strength=0.125,
            multiplier=2.0, start_steps_up=-1,
        )
        # s_init = 1.0 * 2^-1 = 0.5
        assert cursor.s_init == pytest.approx(0.5)
        # next_up should walk 0.5 -> 1.0 -> 2.0 -> 4.0 -> 8.0 -> None
        seq = []
        while True:
            x = cursor.next_up()
            if x is None: break
            seq.append(x)
            if len(seq) > 10: break  # safety
        assert seq == [pytest.approx(1.0), pytest.approx(2.0),
                       pytest.approx(4.0), pytest.approx(8.0)]


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
        # appears verbatim and is decoded back recognisably.  With
        # tokenize=True (how the runner calls it since 2026-10-13), the
        # same text as character codes, as __call__ below makes them.
        sys_msg = next((m["content"] for m in conv if m["role"] == "system"), "")
        usr_msg = next((m["content"] for m in conv if m["role"] == "user"), "")
        text = f"S:{sys_msg}|U:{usr_msg}|A:"
        return list(text.encode("utf-8")) if tokenize else text

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
            # Legacy mode: these tests pre-date the 2026-05-14
            # bidirectional default and assert behaviour of the
            # bottom-up sweep over the explicit `strengths` list.
            scan_mode="legacy_unidirectional",
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
        # Schema sanity.  NoOp dispatcher's
        # judge_coherence_for_strength_async stamps strength_mean_coh=0.0
        # alongside the (still-null) coherence/persona/effect slots so
        # the rest of the pipeline can rely on the field being present.
        for r in records:
            assert r["slot"] == 3
            assert r["layer"] == 25
            assert r["sign"] == 1
            assert r["judges"]["coherence"] is None
            assert r["judges"]["persona"] is None
            assert r["judges"]["effect"] is None
            assert r["judges"]["strength_mean_coh"] == 0.0
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

        from concurrent.futures import Future as _Future

        class StopAfterTwoConsecutive:
            """Pipelined-protocol dispatcher: returns mean coh = 3.0 for
            every strength so the runner's two-consecutive-crossings rule
            fires after the second strength.  enqueue_strength_group is
            called via the coh-future done-callback chain.
            """
            def __init__(self):
                self.coh_dispatched_for = []      # strengths
                self.enqueued_groups = []
                self.drained = False

            def judge_coherence_for_strength_async(self, records):
                # Stamp records and return an immediately-resolved future.
                for r in records:
                    r.setdefault("judges", {})["coherence"] = {
                        "score": 3, "reason": "test", "model": "test",
                        "ts": 0, "rubric_version": 1,
                    }
                    r["judges"]["strength_mean_coh"] = 3.0
                self.coh_dispatched_for.append(records[0]["strength"])
                fut: _Future = _Future()
                fut.set_result(3.0)
                return fut

            def judge_coherence_blocking(self, record):
                # Legacy path -- not used by the pipelined runner but
                # kept for protocol completeness.
                return 3

            def enqueue_strength_group(self, *, cell_dir, slot, layer, sign,
                                       strength, records):
                self.enqueued_groups.append({
                    "strength": strength, "n": len(records),
                })

            def should_stop_at(self, strength):
                # Legacy hook; the pipelined runner doesn't call this.
                return False

            def drain(self, timeout_s=None):
                self.drained = True

            def write_records_atomic(self, records):
                from assistant_axis.atomic_io import write_jsonl
                write_jsonl(records, tmp_path / "cell" / "records.jsonl")

        dispatcher = StopAfterTwoConsecutive()
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
            coh_stop_threshold=1.5,
            coh_stop_consecutive=2,
            scan_mode="legacy_unidirectional",
        )

        assert result.reason == "incoherent"
        # Stop fires after generating strength 2.0 (1.0 = first crossing,
        # 2.0 = second consecutive crossing).  Records for strengths 1, 2 only.
        assert result.stopped_at_strength == 2.0
        records = [json.loads(line)
                   for line in (tmp_path / "cell/records.jsonl").read_text().splitlines()
                   if line.strip()]
        assert len(records) == 4    # 2 strengths * 2 questions
        assert sorted({r["strength"] for r in records}) == [1.0, 2.0]
        # Coherence dispatched once per generated strength.
        assert dispatcher.coh_dispatched_for == [1.0, 2.0]
        # Two strength groups enqueued via the coh-future callback.
        assert [g["strength"] for g in dispatcher.enqueued_groups] == [1.0, 2.0]
        assert all(g["n"] == 2 for g in dispatcher.enqueued_groups)
        # Drain called at the end.
        assert dispatcher.drained is True

    def test_greenlight_pipelining_continues_one_past_first_crossing(
            self, tmp_path, monkeypatch):
        """First crossing alone shouldn't stop; need K=2 consecutive."""
        from concurrent.futures import Future as _Future
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        class CrossThenClear:
            """Strength 1.0 returns mean=2.0 (cross); 2.0 returns 0.5 (clear).
            Should NOT stop after 1.0 alone."""
            def __init__(self):
                self.coh_dispatched_for = []
                self.enqueued_groups = []
                self.drained = False
                # Map strength -> mean coh
                self._mean_at = {1.0: 2.0, 2.0: 0.5, 4.0: 0.5, 8.0: 0.5}

            def judge_coherence_for_strength_async(self, records):
                s = records[0]["strength"]
                m = self._mean_at.get(s, 0.0)
                for r in records:
                    r.setdefault("judges", {})["coherence"] = {
                        "score": int(round(m)), "reason": "test", "model": "test",
                        "ts": 0, "rubric_version": 1,
                    }
                    r["judges"]["strength_mean_coh"] = m
                self.coh_dispatched_for.append(s)
                fut: _Future = _Future()
                fut.set_result(m)
                return fut

            def judge_coherence_blocking(self, record):
                return 0

            def enqueue_strength_group(self, *, cell_dir, slot, layer, sign,
                                       strength, records):
                self.enqueued_groups.append({"strength": strength, "n": len(records)})

            def should_stop_at(self, strength):
                return False

            def drain(self, timeout_s=None):
                self.drained = True

            def write_records_atomic(self, records):
                from assistant_axis.atomic_io import write_jsonl
                write_jsonl(records, tmp_path / "cell" / "records.jsonl")

        dispatcher = CrossThenClear()
        result = steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0, 4.0, 8.0],
            persona_system_prompt="hist",
            questions=["q1", "q2"],
            output_dir=tmp_path / "cell",
            batch_size=2, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=dispatcher,
            coh_stop_threshold=1.5, coh_stop_consecutive=2,
            scan_mode="legacy_unidirectional",
        )
        # No stop -- single crossing didn't trigger; sweep ran to completion.
        assert result.reason == "completed"
        assert result.stopped_at_strength is None
        # All 4 strengths' coh judges were dispatched.
        assert dispatcher.coh_dispatched_for == [1.0, 2.0, 4.0, 8.0]
        # All 4 enqueue_strength_group callbacks fired.
        assert [g["strength"] for g in dispatcher.enqueued_groups] == [1.0, 2.0, 4.0, 8.0]

    def test_two_consecutive_crossings_stops(self, tmp_path, monkeypatch):
        """Two consecutive strengths above threshold -> stop after second."""
        from concurrent.futures import Future as _Future
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        class CrossAndStay:
            """1.0 mean=0; 2.0 mean=2 (first cross); 4.0 mean=2 (second cross -> STOP)."""
            def __init__(self):
                self._mean_at = {1.0: 0.0, 2.0: 2.0, 4.0: 2.0, 8.0: 2.0}
                self.coh_dispatched_for = []

            def judge_coherence_for_strength_async(self, records):
                s = records[0]["strength"]
                m = self._mean_at.get(s, 0.0)
                for r in records:
                    r.setdefault("judges", {})["coherence"] = {
                        "score": int(round(m)), "reason": "t", "model": "t",
                        "ts": 0, "rubric_version": 1}
                    r["judges"]["strength_mean_coh"] = m
                self.coh_dispatched_for.append(s)
                fut: _Future = _Future(); fut.set_result(m); return fut

            def judge_coherence_blocking(self, r): return 0
            def enqueue_strength_group(self, **kw): pass
            def should_stop_at(self, s): return False
            def drain(self, timeout_s=None): pass

        dispatcher = CrossAndStay()
        result = steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0, 4.0, 8.0],
            persona_system_prompt="hist",
            questions=["q1", "q2"],
            output_dir=tmp_path / "cell",
            batch_size=2, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=dispatcher,
            coh_stop_threshold=1.5, coh_stop_consecutive=2,
            scan_mode="legacy_unidirectional",
        )
        assert result.reason == "incoherent"
        # Generated 1.0, 2.0, 4.0; stopped before 8.0.  4.0 is the second
        # consecutive crossing.
        assert result.stopped_at_strength == 4.0
        assert dispatcher.coh_dispatched_for == [1.0, 2.0, 4.0]

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

    def test_skip_when_previous_cap_below_new_max_strength_with_incoherent_stop(
        self, tmp_path, monkeypatch,
    ):
        """A cell that previously stopped due to the COHERENCE CLIFF must
        be skipped even if the caller has raised max_strength: the cell
        already found its physical cliff, no extension is meaningful.
        """
        out_dir = tmp_path / "cell"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text(json.dumps({
            "stopped_at_strength": 11.286,
            "reason": "bidirectional_done",
            "n_records": 99,
            "n_strengths_swept": 5,
            "up_blocked_reason": "incoherent",
            "down_blocked_reason": "sub_threshold_effect",
            "max_strength": 16.0,
            "min_strength": 0.125,
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
            scan_mode="bidirectional",
            max_strength=128.0,  # raised from old 16.0
        )

        # Skipped: cell hit the cliff, not the cap.
        assert result.stopped_at_strength == 11.286
        assert _FakeActivationSteering.construct_calls == []

    def test_cap_extension_fallthrough_when_previously_capped(
        self, tmp_path, monkeypatch,
    ):
        """A cell that previously stopped because it hit the CONFIGURED
        max_strength cap (not the coherence cliff) must NOT be skipped
        when max_strength is raised -- it should fall through so the
        bidirectional state machine can extend the UP-walk past the old
        cap.  Existing records are not regenerated; only the new
        strengths beyond the old cap will be touched.

        This test only validates the FALL-THROUGH (no early-return); the
        full integration is exercised by the bidirectional state-machine
        tests below.
        """
        out_dir = tmp_path / "cell"
        out_dir.mkdir()
        (out_dir / "summary.json").write_text(json.dumps({
            "stopped_at_strength": 16.0,
            "reason": "bidirectional_done",
            "n_records": 200,
            "n_strengths_swept": 8,
            "up_blocked_reason": "max_strength_reached",
            "down_blocked_reason": "sub_threshold_effect",
            "max_strength": 16.0,
            "min_strength": 0.125,
        }))
        # Empty records file so the bidirectional cell will try to
        # generate.  (Caller normally pre-loads existing records; we
        # only need to verify fall-through here.)
        (out_dir / "records.jsonl").write_text("")
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)

        # Caller raises the cap to 128.  Bidirectional resume should
        # be entered, which means we DO touch generation code paths
        # (in this minimal smoke test with no existing records it
        # generates from s_init upward).
        steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0],
            persona_system_prompt="hist",
            questions=["q1"],
            output_dir=out_dir, batch_size=1, max_new_tokens=4,
            positions_mode="all",
            scan_mode="bidirectional",
            max_strength=128.0,  # raised from old 16.0
            weakest_strength=1.0,
        )

        # If the early-skip had fired, construct_calls would be empty.
        # The fall-through must have happened, so generation ran.
        assert len(_FakeActivationSteering.construct_calls) > 0, (
            "Cap-extension fall-through failed: cell was early-skipped "
            "despite max_strength_reached + new max_strength > old cap."
        )


# ---------------------------------------------------------------------------
# Bidirectional state-machine tests
# ---------------------------------------------------------------------------


class _BidirStubDispatcher:
    """Stub dispatcher for bidirectional state-machine tests.

    Returns canned ``mean_coh`` and ``mean_abs_eff`` per strength, both
    via immediately-resolved futures.  This lets us drive the runner's
    state machine through specific UP/DOWN block paths without spinning
    up a real judge dispatcher.

    Keys with abs-value precision: 6 decimals (matches the cursor's
    rounding).  Set values via ``.set(strength, mean_coh, mean_abs_eff)``.
    """

    def __init__(self):
        self._table: Dict[float, Tuple[float, float]] = {}
        self.coh_dispatched_for: List[float] = []
        self.eff_dispatched_for: List[float] = []
        self.enqueued_groups: List[Dict[str, Any]] = []
        self.drained = False

    def set(self, strength: float, mean_coh: float, mean_abs_eff: float) -> None:
        self._table[round(float(strength), 6)] = (
            float(mean_coh), float(mean_abs_eff),
        )

    def _lookup(self, strength: float) -> Tuple[float, float]:
        key = round(float(strength), 6)
        if key in self._table:
            return self._table[key]
        # Default: middle-of-the-road coh + zero eff (so an
        # unconfigured DOWN strength counts toward the eff-stop window).
        return 0.0, 0.0

    def judge_coherence_for_strength_async(self, records):
        from concurrent.futures import Future as _Future
        s = float(records[0]["strength"])
        m_coh, _ = self._lookup(s)
        for r in records:
            r.setdefault("judges", {})["coherence"] = {
                "score": int(round(m_coh)), "reason": "stub",
                "model": "stub", "ts": 0, "rubric_version": 1,
            }
            r["judges"]["strength_mean_coh"] = m_coh
        self.coh_dispatched_for.append(s)
        fut: _Future = _Future()
        fut.set_result(m_coh)
        return fut

    def judge_coherence_blocking(self, record):
        return 0

    def enqueue_strength_group(self, *, cell_dir, slot, layer, sign,
                               strength, records):
        # Stamp effect.combined consistently with the eff future the
        # runner is about to surface; the runner reads this back via
        # the on-disk records during restart bootstrap.
        _, m_eff = self._lookup(float(strength))
        for r in records:
            r.setdefault("judges", {})["effect"] = {
                "combined": m_eff,
                "mode": "bidirectional",
                "ts": 0,
                "rubric_version": 1,
                "skipped_due_to_strength_mean_coh": False,
            }
        self.enqueued_groups.append(
            {"strength": float(strength), "n": len(records)}
        )

    def judge_effect_for_strength_async(self, records):
        from concurrent.futures import Future as _Future
        s = float(records[0]["strength"])
        _, m_eff = self._lookup(s)
        self.eff_dispatched_for.append(s)
        fut: _Future = _Future()
        fut.set_result(m_eff)
        return fut

    def should_stop_at(self, strength):
        return False

    def drain(self, timeout_s=None):
        self.drained = True


class TestBidirectionalStateMachine:
    """End-to-end runner tests that drive the bidirectional state machine
    through the three canonical block paths from plan §9.2."""

    def _run_cell(self, *, tmp_path, monkeypatch, dispatcher, max_strength=8.0,
                  min_strength=0.0625, multiplier=2.0,
                  start_steps_up=1, weakest=1.0, coh_stop_threshold=1.5,
                  coh_stop_consecutive=2, eff_stop_threshold=0.25,
                  eff_stop_consecutive=2, n_questions=2, batch_size=2):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        out_dir = tmp_path / "cell"
        return steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            persona_system_prompt="hist",
            questions=[f"q{i}" for i in range(n_questions)],
            output_dir=out_dir,
            batch_size=batch_size, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=dispatcher,
            coh_stop_threshold=coh_stop_threshold,
            coh_stop_consecutive=coh_stop_consecutive,
            eff_stop_threshold=eff_stop_threshold,
            eff_stop_consecutive=eff_stop_consecutive,
            weakest_strength=weakest,
            max_strength=max_strength,
            min_strength=min_strength,
            multiplier=multiplier,
            start_strength_multiplier_steps=start_steps_up,
            scan_mode="bidirectional",
        )

    def test_up_blocks_first_then_down_keeps_stepping(self, tmp_path, monkeypatch):
        """BothOpen -> UpBlocked via 2 consec incoherent; DOWN continues
        until it also blocks on cursor exhaustion.

        Schedule with mult=2, weakest=1, start_steps_up=1: s_init=2,
        UP {4, 8}, DOWN {1, 0.5, 0.25, 0.125, 0.0625}.
        Set UP {4, 8} to mean_coh=2.0 (incoherent), all DOWN to
        mean_abs_eff=0.5 (active effect, so down keeps stepping until
        cursor exhausted).
        """
        d = _BidirStubDispatcher()
        # Incoherent UP -- both UP strengths cross the threshold.
        d.set(4.0, mean_coh=2.0, mean_abs_eff=0.5)
        d.set(8.0, mean_coh=2.0, mean_abs_eff=0.5)
        # DOWN: well-above eff threshold so eff-stop never fires.
        for s in (1.0, 0.5, 0.25, 0.125, 0.0625):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.5)
        # s_init is at 2.0 -- low coh + medium eff (irrelevant).
        d.set(2.0, mean_coh=0.0, mean_abs_eff=0.5)

        result = self._run_cell(
            tmp_path=tmp_path, monkeypatch=monkeypatch, dispatcher=d,
        )
        # Should have visited both UP strengths and exhausted DOWN at
        # the floor 0.0625.
        summary = result.summary
        assert summary["scan_mode"] == "bidirectional"
        assert summary["up_blocked_reason"] == "incoherent"
        assert summary["down_blocked_reason"] == "min_strength_reached"
        # UP tail strengths in order
        ups = sorted(s for s in d.coh_dispatched_for if s > 2.0)
        assert ups == [4.0, 8.0]
        # DOWN tail includes the geometric chain down to the floor
        downs = sorted({s for s in d.coh_dispatched_for if s < 2.0})
        assert downs[0] == pytest.approx(0.0625)
        assert downs[-1] == pytest.approx(1.0)

    def test_down_blocks_first_then_up_keeps_stepping(self, tmp_path, monkeypatch):
        """BothOpen -> DownBlocked via 2 consec sub-threshold |eff|; UP
        continues until coh-stop.

        Schedule (mult=2, weakest=1, start_steps_up=1): s_init=2,
        UP {4, 8}, DOWN {1, 0.5}.  Make DOWN values low-effect to
        trigger eff-stop after 2; UP at 4 and 8 are incoherent to
        eventually block UP too.
        """
        d = _BidirStubDispatcher()
        d.set(1.0, mean_coh=0.0, mean_abs_eff=0.1)   # below eff threshold
        d.set(0.5, mean_coh=0.0, mean_abs_eff=0.1)   # 2nd consec below
        d.set(2.0, mean_coh=0.0, mean_abs_eff=0.5)
        d.set(4.0, mean_coh=2.0, mean_abs_eff=0.5)   # 1st consec coh-cross
        d.set(8.0, mean_coh=2.0, mean_abs_eff=0.5)   # 2nd consec coh-cross

        result = self._run_cell(
            tmp_path=tmp_path, monkeypatch=monkeypatch, dispatcher=d,
        )
        summary = result.summary
        assert summary["scan_mode"] == "bidirectional"
        assert summary["down_blocked_reason"] == "sub_threshold_effect"
        assert summary["up_blocked_reason"] == "incoherent"
        # DOWN should NOT have gone past 0.5 (eff-stopped after 2 below)
        downs = sorted({s for s in d.coh_dispatched_for if s < 2.0})
        assert downs == [0.5, 1.0]
        # UP went 4, 8 then stopped on 2 consec incoherent.
        ups = sorted(s for s in d.coh_dispatched_for if s > 2.0)
        assert ups == [4.0, 8.0]

    def test_persists_positions_mode_in_summary(self, tmp_path, monkeypatch):
        """Tag-along §12: summary.json now carries positions_mode for
        per-cell audit."""
        d = _BidirStubDispatcher()
        # Make both ends block fast so the test is short.
        for s in (1.0, 0.5, 0.25, 0.125, 0.0625):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.0)  # eff-stop on first 2
        for s in (4.0, 8.0):
            d.set(s, mean_coh=3.0, mean_abs_eff=0.5)  # coh-stop on first 2

        result = self._run_cell(
            tmp_path=tmp_path, monkeypatch=monkeypatch, dispatcher=d,
        )
        assert result.summary["positions_mode"] == "all"


class TestBidirectionalRestart:
    """Restart mid-bidirectional: pre-seed records.jsonl + verify resume
    continues from correct cursors and re-evaluates stop conditions
    against pre-seeded history."""

    def test_resume_from_partial_records(self, tmp_path, monkeypatch):
        from assistant_axis.atomic_io import write_jsonl
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        out_dir = tmp_path / "cell"
        out_dir.mkdir()

        # Schedule: mult=2, weakest=1, start_steps_up=1 -> s_init=2.
        # UP {4, 8}, DOWN {1, 0.5, 0.25, 0.125, 0.0625}.
        # Pre-seed s_init=2 + UP=4 + DOWN=1 with judged scores.
        questions = ["q0", "q1"]
        sign = +1

        def _mk_rec(strength, qi, mean_coh, mean_abs_eff):
            return {
                "strength": float(strength), "sign": sign,
                "slot": 0, "layer": 26, "question_idx": qi,
                "question": questions[qi],
                "response": "stub",
                "n_tokens": 1,
                "judges": {
                    "coherence": {"score": int(round(mean_coh)),
                                  "reason": "seed", "model": "seed",
                                  "ts": 0, "rubric_version": 1},
                    # Persona must be a populated dict (post-2026-05-17
                    # resume gap-fill needs persona.score or
                    # skipped_due_to_strength_mean_coh to consider the
                    # strength "complete" -- otherwise the gap-fill
                    # treats it as a partial-flush victim and
                    # regenerates).
                    "persona": {"score": 3, "reason": "seed",
                                "model": "seed", "ts": 0,
                                "rubric_version": 1,
                                "skipped_due_to_strength_mean_coh": False},
                    "effect": {
                        "combined": mean_abs_eff,
                        "mode": "bidirectional", "ts": 0,
                        "rubric_version": 1,
                        "skipped_due_to_strength_mean_coh": False,
                    },
                    "strength_mean_coh": float(mean_coh),
                },
                "timing": {"gen_s": 0.0},
                "abandoned": False,
            }

        seed = []
        for s, mc, me in [(2.0, 0.0, 0.5), (4.0, 0.0, 0.5),
                          (1.0, 0.0, 0.5)]:
            for qi in range(2):
                seed.append(_mk_rec(s, qi, mc, me))
        write_jsonl(seed, out_dir / "records.jsonl")

        # Run dispatcher: complete the scan.  UP {8} should reach
        # max=8 cap → "max_strength_reached".  DOWN walks {0.5, 0.25,
        # 0.125, 0.0625}; configure them all as low-eff so the eff-stop
        # fires on the first 2 below s_init=2 (which are seed=1.0 + new=0.5).
        d = _BidirStubDispatcher()
        d.set(8.0, mean_coh=0.0, mean_abs_eff=0.5)
        for s in (0.5, 0.25, 0.125, 0.0625):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.1)  # below eff threshold

        result = steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=sign,
            persona_system_prompt="hist",
            questions=questions,
            output_dir=out_dir,
            batch_size=2, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=d,
            coh_stop_threshold=1.5, coh_stop_consecutive=2,
            eff_stop_threshold=0.25, eff_stop_consecutive=2,
            weakest_strength=1.0, max_strength=8.0,
            min_strength=0.0625, multiplier=2.0,
            start_strength_multiplier_steps=1,
            scan_mode="bidirectional",
        )
        # Resume should NOT re-generate seeded strengths (2, 4, 1).
        gen_strengths = sorted(d.coh_dispatched_for)
        assert 2.0 not in gen_strengths
        assert 4.0 not in gen_strengths
        assert 1.0 not in gen_strengths
        # Should at minimum hit 8 (UP cap) and 0.5 (first new DOWN).
        assert 8.0 in gen_strengths
        assert 0.5 in gen_strengths
        # Summary reflects bidirectional mode with both sides eventually
        # blocked.
        assert result.summary["scan_mode"] == "bidirectional"
        assert result.summary["up_blocked_reason"] == "max_strength_reached"
        # DOWN should have eff-stopped because seed=1.0 has eff=0.5
        # (>= threshold so doesn't count) but new 0.5 + 0.25 are below
        # threshold -- wait, need to recount.  Seed records have
        # eff=0.5 (>= 0.25 threshold, so 1.0 doesn't count toward
        # below-threshold streak), but the eff-stop requires 2 consec
        # BELOW, so we need 0.5 and 0.25 both below 0.25.  My setup has
        # 0.5 at eff=0.1 and 0.25 at eff=0.1, so the streak of 2 fires.
        assert result.summary["down_blocked_reason"] == "sub_threshold_effect"


# ---------------------------------------------------------------------------
# Resume re-judges a strength whose responses are all on disk
# (2026-10-12, review Review 7 D4 / walk-through E2)
# ---------------------------------------------------------------------------


class _RecordingStubDispatcher(_BidirStubDispatcher):
    """The bidirectional stub, also recording which question indices each
    coherence call and each strength-group hand-over received."""

    def __init__(self):
        super().__init__()
        self.coh_qidx: Dict[float, List[List[int]]] = {}
        self.enqueued_qidx: Dict[float, List[List[int]]] = {}

    def judge_coherence_for_strength_async(self, records):
        s = float(records[0]["strength"])
        self.coh_qidx.setdefault(s, []).append(
            sorted(int(r["question_idx"]) for r in records))
        return super().judge_coherence_for_strength_async(records)

    def enqueue_strength_group(self, *, cell_dir, slot, layer, sign,
                               strength, records):
        self.enqueued_qidx.setdefault(float(strength), []).append(
            sorted(int(r["question_idx"]) for r in records))
        return super().enqueue_strength_group(
            cell_dir=cell_dir, slot=slot, layer=layer, sign=sign,
            strength=strength, records=records)


_RJ_QUESTIONS = ["q0", "q1"]


def _rj_rec(strength, qi, *, coherence=0, persona=3, effect=0.5,
            smc=0.0, response="seed", persona_skipped=False):
    """A seeded record; ``None`` for a judge means not judged (persona None
    with ``persona_skipped`` False reads as UNPARSEABLE)."""
    judges: Dict[str, Any] = {"strength_mean_coh": smc}
    judges["coherence"] = (
        None if coherence is None else
        {"score": coherence, "reason": "seed", "model": "seed", "ts": 0,
         "rubric_version": 1})
    judges["persona"] = {
        "score": persona,
        "reason": "UNPARSEABLE" if persona is None and not persona_skipped else "seed",
        "model": "seed", "ts": 0, "rubric_version": 1,
        "skipped_due_to_strength_mean_coh": bool(persona_skipped),
    }
    judges["effect"] = {
        "mode": "bidirectional", "ts": 0, "rubric_version": 1,
        "skipped_due_to_strength_mean_coh": bool(persona_skipped),
    }
    if effect is not None:
        judges["effect"]["combined"] = effect
    return {
        "strength": float(strength), "sign": +1, "slot": 0, "layer": 26,
        "question_idx": qi, "question": _RJ_QUESTIONS[qi],
        "response": response, "n_tokens": 1, "judges": judges,
        "timing": {"gen_s": 0.0}, "abandoned": False,
    }


class TestResumeRejudgesInsteadOfRegenerating:
    """Schedule: mult=2, weakest=1, start_steps_up=1 -> s_init=2.0; UP
    4.0, 8.0 (cap); DOWN 1.0, 0.5, 0.25, ...  Seeded strengths are complete
    unless a test breaks one; new DOWN strengths have eff 0.1 so DOWN stops
    after 0.5 and 0.25."""

    def _run(self, tmp_path, monkeypatch, seed, dispatcher=None):
        from assistant_axis.atomic_io import write_jsonl
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        out_dir = tmp_path / "cell"
        out_dir.mkdir()
        write_jsonl(seed, out_dir / "records.jsonl")
        d = dispatcher or _RecordingStubDispatcher()
        d.set(8.0, mean_coh=0.0, mean_abs_eff=0.5)
        for s in (0.5, 0.25, 0.125, 0.0625):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.1)
        for s in (1.0, 2.0, 4.0):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.5)
        steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            persona_system_prompt="hist", questions=_RJ_QUESTIONS,
            output_dir=out_dir, batch_size=2, max_new_tokens=4,
            positions_mode="all", judge_dispatcher=d,
            coh_stop_threshold=1.5, coh_stop_consecutive=2,
            eff_stop_threshold=0.25, eff_stop_consecutive=2,
            weakest_strength=1.0, max_strength=8.0,
            min_strength=0.0625, multiplier=2.0,
            start_strength_multiplier_steps=1, scan_mode="bidirectional",
        )
        on_disk = [json.loads(l) for l in
                   (out_dir / "records.jsonl").read_text().splitlines() if l.strip()]
        return d, on_disk

    @staticmethod
    def _generated_at(strength):
        return any(abs(c["coefficients"][0] - strength) < 1e-9
                   for c in _FakeActivationSteering.construct_calls)

    @staticmethod
    def _at(on_disk, strength):
        return sorted((r for r in on_disk if abs(r["strength"] - strength) < 1e-9),
                      key=lambda r: r["question_idx"])

    def test_one_unparseable_persona_is_rejudged_not_regenerated(
            self, tmp_path, monkeypatch):
        seed = [_rj_rec(s, q) for s in (2.0, 1.0) for q in (0, 1)]
        seed += [_rj_rec(4.0, 0), _rj_rec(4.0, 1, persona=None)]
        d, on_disk = self._run(tmp_path, monkeypatch, seed)

        assert not self._generated_at(4.0), "4.0 was regenerated"
        assert [r["response"] for r in self._at(on_disk, 4.0)] == ["seed", "seed"]
        # Coherence was on every record: not asked again.
        assert 4.0 not in d.coh_qidx
        # The whole strength was handed over for judging, once.
        assert d.enqueued_qidx[4.0] == [[0, 1]]
        # The complete strengths were left alone.
        for s in (2.0, 1.0):
            assert s not in d.enqueued_qidx and not self._generated_at(s)
        # New strengths still generated as usual.
        assert self._generated_at(8.0) and self._generated_at(0.5)

    def test_coherence_is_asked_only_where_missing(self, tmp_path, monkeypatch):
        seed = [_rj_rec(s, q) for s in (2.0, 4.0) for q in (0, 1)]
        seed += [_rj_rec(1.0, 0, persona=None, effect=None),
                 _rj_rec(1.0, 1, coherence=None, persona=None, effect=None)]
        d, on_disk = self._run(tmp_path, monkeypatch, seed)

        assert not self._generated_at(1.0)
        assert d.coh_qidx[1.0] == [[1]]
        assert d.enqueued_qidx[1.0] == [[0, 1]]
        recs = self._at(on_disk, 1.0)
        assert [r["response"] for r in recs] == ["seed", "seed"]
        assert all(r["judges"]["coherence"]["score"] == 0 for r in recs)
        assert all(r["judges"]["effect"]["combined"] == 0.5 for r in recs)

    def test_judges_none_records_are_rejudged(self, tmp_path, monkeypatch):
        """A kill between generation and judging (records with
        ``judges: None``): coherence for both, then the hand-over."""
        seed = [_rj_rec(s, q) for s in (2.0, 4.0) for q in (0, 1)]
        for q in (0, 1):
            r = _rj_rec(1.0, q)
            r["judges"] = None
            seed.append(r)
        d, on_disk = self._run(tmp_path, monkeypatch, seed)
        assert not self._generated_at(1.0)
        assert d.coh_qidx[1.0] == [[0, 1]]
        assert d.enqueued_qidx[1.0] == [[0, 1]]
        assert all(isinstance(r["judges"], dict) for r in self._at(on_disk, 1.0))

    def test_partial_generation_is_still_regenerated(self, tmp_path, monkeypatch):
        seed = [_rj_rec(s, q) for s in (2.0, 1.0) for q in (0, 1)]
        seed += [_rj_rec(4.0, 0)]                   # q1 never generated
        d, on_disk = self._run(tmp_path, monkeypatch, seed)
        assert self._generated_at(4.0)
        recs = self._at(on_disk, 4.0)
        assert [r["question_idx"] for r in recs] == [0, 1]
        assert all(r["response"] != "seed" for r in recs)   # wiped, regenerated
        assert d.coh_qidx[4.0] == [[0, 1]]

    def test_s_init_skipped_under_an_older_threshold_is_rejudged(
            self, tmp_path, monkeypatch):
        """competitor_improvisational_v1 s7_l49_+1's case: s_init skipped
        at mean coherence 1.29 under the pre-2026-05-17 threshold 1.0, so
        incomplete under 1.5; it used to fall through to the gap-fill on
        every resume and stay unjudged."""
        seed = [_rj_rec(2.0, q, coherence=c, persona=None, effect=None,
                        smc=1.5 - 0.25, persona_skipped=True)
                for q, c in ((0, 1), (1, 2))]
        seed += [_rj_rec(s, q) for s in (4.0, 1.0) for q in (0, 1)]
        d, on_disk = self._run(tmp_path, monkeypatch, seed)
        assert not self._generated_at(2.0)
        assert 2.0 not in d.coh_qidx
        assert d.enqueued_qidx[2.0] == [[0, 1]]
        assert [r["response"] for r in self._at(on_disk, 2.0)] == ["seed", "seed"]

    def test_partial_s_init_is_regenerated_whole(self, tmp_path, monkeypatch):
        """A partial s_init is wiped and regenerated like any other partial
        strength (it used to generate the missing question only and judge it
        as a group of its own, leaving the old record unjudged)."""
        old = _rj_rec(2.0, 0, coherence=None, persona=None, effect=None)
        seed = [old] + [_rj_rec(s, q) for s in (4.0, 1.0) for q in (0, 1)]
        d, on_disk = self._run(tmp_path, monkeypatch, seed)
        assert self._generated_at(2.0)
        recs = self._at(on_disk, 2.0)
        assert [r["question_idx"] for r in recs] == [0, 1]
        assert all(r["response"] != "seed" for r in recs)
        assert d.coh_qidx[2.0] == [[0, 1]]
        assert d.enqueued_qidx[2.0] == [[0, 1]]


class TestRejudgeStrengthWithTheRealDispatcher:
    """``_rejudge_strength`` against ``RealJudgeDispatcher`` (API calls
    faked): only the missing judgements are asked for, the judged ones are
    kept, and the coherence future gives the mean over all K records."""

    @pytest.fixture
    def real_dispatcher(self, tmp_path, monkeypatch):
        import anthropic as anthropic_mod
        import openai as openai_mod
        from assistant_axis import steering_judges as sj

        monkeypatch.setattr(openai_mod, "AsyncOpenAI", lambda: mock.MagicMock())
        monkeypatch.setattr(anthropic_mod, "AsyncAnthropic", lambda: mock.MagicMock())
        calls: List[str] = []

        async def fake_call(*, model, prompt, **_kw):
            if "evaluating the coherence" in prompt:
                calls.append("coherence")
                return json.dumps({"reason": "ok", "score": 1})
            if "embodies the persona" in prompt:
                calls.append("persona")
                return json.dumps({"reason": "ok", "score": 2})
            calls.append("effect")
            ids = [i for i in range(10) if f"id={i}" in prompt]
            return json.dumps({"items": [{"id": i, "reason": "ok", "score": 1}
                                         for i in ids]})

        monkeypatch.setattr(sj, "call_judge_single_unified", fake_call)
        records_path = tmp_path / "records.jsonl"
        d = sj.RealJudgeDispatcher(
            records_path=records_path,
            persona=sj.PersonaSpec(role="chef", description="cooks"),
            steering=sj.SteeringSpec(
                axis_name="unhelpful-helpful", pos_label="helpful",
                pos_description="helps", neg_label="unhelpful",
                neg_description="does not help"),
            baseline_lookup=lambda q: "",
        )
        yield d, calls, records_path
        d.shutdown()

    def _recs(self):
        recs = [
            _rj_rec(1.0, 0, coherence=0, persona=2, effect=0.5),
            _rj_rec(1.0, 1, coherence=0, persona=None, effect=-0.5),
        ]
        recs.append(dict(recs[0], question_idx=2, question="q2"))
        recs[2] = json.loads(json.dumps(recs[2]))
        recs[2]["judges"]["coherence"]["score"] = 1
        return recs

    def test_only_the_unparseable_persona_is_asked(self, real_dispatcher, tmp_path):
        from assistant_axis.atomic_io import write_jsonl
        d, calls, records_path = real_dispatcher
        recs = self._recs()
        write_jsonl(recs, records_path)
        coh_fut, eff_fut = steering_runner._rejudge_strength(
            strength=1.0, sign=+1, slot=0, layer=26, recs=recs,
            output_dir=tmp_path, dispatcher=d,
        )
        assert coh_fut.result(timeout=10) == pytest.approx(1 / 3)
        d.drain(timeout_s=10)
        assert calls == ["persona"]
        assert [r["judges"]["persona"]["score"] for r in recs] == [2, 2, 2]
        assert recs[0]["judges"]["persona"]["reason"] == "seed"   # kept, not re-asked
        assert [r["judges"]["effect"]["combined"] for r in recs] == [0.5, -0.5, 0.5]
        assert eff_fut.result(timeout=10) == pytest.approx(0.5 / 3)

    def test_missing_coherence_is_asked_then_the_strength_mean_is_over_all(
            self, real_dispatcher, tmp_path):
        from assistant_axis.atomic_io import write_jsonl
        d, calls, records_path = real_dispatcher
        recs = self._recs()
        recs[1]["judges"]["coherence"] = None
        write_jsonl(recs, records_path)
        coh_fut, _ = steering_runner._rejudge_strength(
            strength=1.0, sign=+1, slot=0, layer=26, recs=recs,
            output_dir=tmp_path, dispatcher=d,
        )
        # coherence 0 (kept), 1 (asked), 1 (kept)
        assert coh_fut.result(timeout=10) == pytest.approx(2 / 3)
        d.drain(timeout_s=10)
        assert sorted(calls) == ["coherence", "persona"]
        for r in recs:
            assert r["judges"]["strength_mean_coh"] == pytest.approx(2 / 3)
        on_disk = [json.loads(l) for l in records_path.read_text().splitlines() if l.strip()]
        assert sorted(r["judges"]["persona"]["score"] for r in on_disk) == [2, 2, 2]


class TestLegacyModeParity:
    """Verify that scan_mode='legacy_unidirectional' preserves
    pre-2026-05-14 behaviour.

    Full byte-identical parity to a frozen baseline is impractical given
    summary.json schema additions (scan_mode + positions_mode fields are
    new in 2026-05-14).  This test pins the legacy-path invariants
    instead: visited strengths, stop semantics, and records.jsonl
    contents match the legacy expectations.
    """

    def test_legacy_completes_in_order_with_explicit_schedule(
            self, tmp_path, monkeypatch):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        out_dir = tmp_path / "cell"
        result = steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=+1,
            strengths=[1.0, 2.0, 4.0],
            persona_system_prompt="hist",
            questions=["q0", "q1"],
            output_dir=out_dir,
            batch_size=2, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=NoOpJudgeDispatcher(),
            scan_mode="legacy_unidirectional",
        )
        # Legacy: visits strengths in caller-supplied order, completes.
        assert result.reason == "completed"
        assert result.n_records == 6
        records = [json.loads(line) for line
                   in (out_dir / "records.jsonl").read_text().splitlines()
                   if line.strip()]
        # Strict order: 1.0 first, then 2.0, then 4.0.
        strengths_in_disk_order = [r["strength"] for r in records]
        assert strengths_in_disk_order == [1.0, 1.0, 2.0, 2.0, 4.0, 4.0]
        # Summary records the mode + positions_mode tag-along.
        summary = result.summary
        assert summary["scan_mode"] == "legacy_unidirectional"
        assert summary["positions_mode"] == "all"

    def test_resume_gapfill_regenerates_partial_strength(
        self, tmp_path, monkeypatch,
    ):
        """A kill mid-strength can leave a strength with < K records or
        with judges=None on each record.  The 2026-05-17 resume
        gap-fill must detect both.  Since 2026-10-12 (review Review 7
        D4 / walk-through E2) it regenerates only the strength with
        responses missing and re-judges the one whose responses are all
        there (before, it regenerated both).
        """
        from assistant_axis.atomic_io import write_jsonl
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        out_dir = tmp_path / "cell"
        out_dir.mkdir()

        # Schedule: mult=2, weakest=1, start_steps_up=1 -> s_init=2.
        # Seed: s_init=2.0 fully-judged (complete), UP=4.0 with only ONE
        # of two questions generated (partial-flush, judges=None),
        # DOWN=1.0 with both questions but judges=None on each (judging
        # never ran).  Resume gap-fill must regenerate 4.0, re-judge 1.0
        # without regenerating it, and leave 2.0 alone.
        questions = ["q0", "q1"]
        sign = +1

        def _complete_rec(s, qi):
            return {
                "strength": float(s), "sign": sign,
                "slot": 0, "layer": 26, "question_idx": qi,
                "question": questions[qi],
                "response": "seed_complete",
                "n_tokens": 1,
                "judges": {
                    "coherence": {"score": 0, "reason": "seed",
                                  "model": "seed", "ts": 0,
                                  "rubric_version": 1},
                    "persona": {"score": 3, "reason": "seed",
                                "model": "seed", "ts": 0,
                                "rubric_version": 1,
                                "skipped_due_to_strength_mean_coh": False},
                    "effect": {"combined": 0.5, "mode": "bidirectional",
                               "ts": 0, "rubric_version": 1,
                               "skipped_due_to_strength_mean_coh": False},
                    "strength_mean_coh": 0.0,
                },
                "timing": {"gen_s": 0.0},
                "abandoned": False,
            }

        def _unjudged_rec(s, qi):
            return {
                "strength": float(s), "sign": sign,
                "slot": 0, "layer": 26, "question_idx": qi,
                "question": questions[qi],
                "response": "seed_partial",
                "n_tokens": 1,
                "judges": None,  # killed before judging dispatched
                "timing": {"gen_s": 0.0},
                "abandoned": False,
            }

        seed = [
            _complete_rec(2.0, 0), _complete_rec(2.0, 1),    # full
            _unjudged_rec(4.0, 0),                            # partial: only 1/2
            _unjudged_rec(1.0, 0), _unjudged_rec(1.0, 1),     # 2/2 but unjudged
        ]
        write_jsonl(seed, out_dir / "records.jsonl")

        d = _BidirStubDispatcher()
        # Configure dispatcher to return non-blocking eff for 4.0 and 1.0
        # so the regenerated strengths don't trigger stop conditions.
        for s in (4.0, 1.0, 8.0, 0.5, 0.25, 0.125, 0.0625):
            d.set(s, mean_coh=0.0, mean_abs_eff=0.5)

        steering_runner.run_steering_cell(
            _FakeModel(8), _FakeTokenizer(),
            axis_vector=torch.zeros(8, dtype=torch.bfloat16),
            slot=0, layer=26, sign=sign,
            persona_system_prompt="hist",
            questions=questions,
            output_dir=out_dir,
            batch_size=2, max_new_tokens=4,
            positions_mode="all",
            judge_dispatcher=d,
            coh_stop_threshold=1.5, coh_stop_consecutive=2,
            eff_stop_threshold=0.25, eff_stop_consecutive=2,
            weakest_strength=1.0, max_strength=8.0,
            min_strength=0.0625, multiplier=2.0,
            start_strength_multiplier_steps=1,
            scan_mode="bidirectional",
        )

        # Gap-fill should have re-dispatched judging on 4.0 (partial)
        # and 1.0 (unjudged).  s_init=2.0 is fully complete, must NOT
        # be re-dispatched.
        gen_strengths = sorted(d.coh_dispatched_for)
        assert 4.0 in gen_strengths, (
            f"partial strength 4.0 should have been regenerated; "
            f"got {gen_strengths}"
        )
        assert 1.0 in gen_strengths, (
            f"unjudged strength 1.0 should have been re-judged; "
            f"got {gen_strengths}"
        )
        assert 2.0 not in gen_strengths, (
            f"complete strength 2.0 should NOT be regenerated; "
            f"got {gen_strengths}"
        )
        # 2026-10-12 (E2): 1.0 was re-judged, not regenerated -- no
        # generation at 1.0, and its two responses are the seeded ones;
        # 4.0 (responses missing) was regenerated.  Before, both were.
        coeffs = [c["coefficients"][0]
                  for c in _FakeActivationSteering.construct_calls]
        assert 1.0 not in coeffs and 4.0 in coeffs

        # Disk state: all records at 4.0 and 1.0 should now have
        # judges populated (the regen path generates K records and
        # dispatches judging via the stub).
        records = [
            json.loads(line) for line
            in (out_dir / "records.jsonl").read_text().splitlines()
            if line.strip()
        ]
        for r in records:
            if float(r["strength"]) in (4.0, 1.0):
                # Either fully judged or in-flight; for this stub
                # dispatcher the writeback is synchronous so judges
                # should be a dict.
                j = r.get("judges")
                assert isinstance(j, dict), (
                    f"regenerated record at {r['strength']} still has "
                    f"judges={j}"
                )
        assert sorted(r["response"] for r in records
                      if float(r["strength"]) == 1.0) == ["seed_partial"] * 2
        assert all(r["response"] != "seed_partial" for r in records
                   if float(r["strength"]) == 4.0)

    def test_legacy_requires_strengths(self, tmp_path, monkeypatch):
        """Legacy mode without `strengths` is an explicit error -- the
        caller is responsible for building the schedule via
        directional_schedule()."""
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setattr(steering_runner, "ActivationSteering",
                            _FakeActivationSteering)
        with pytest.raises(ValueError, match="legacy_unidirectional"):
            steering_runner.run_steering_cell(
                _FakeModel(8), _FakeTokenizer(),
                axis_vector=torch.zeros(8, dtype=torch.bfloat16),
                slot=0, layer=26, sign=+1,
                strengths=None,
                persona_system_prompt="hist",
                questions=["q0"],
                output_dir=tmp_path / "cell",
                batch_size=1, max_new_tokens=4,
                positions_mode="all",
                judge_dispatcher=NoOpJudgeDispatcher(),
                scan_mode="legacy_unidirectional",
            )


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

    def test_writes_completion_sentinel(self, tmp_path, monkeypatch):
        """compute_baselines must touch baselines/.complete after a
        successful run so multi-GPU workers picking up cell items for
        the same experiment can wait for it before constructing their
        dispatchers (otherwise build_baseline_lookup would silently
        see an empty/partial records.jsonl and emit blank baseline_responses
        in judge prompts).
        """
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        model = _FakeModel(8)
        tokenizer = _FakeTokenizer()
        questions = ["q0", "q1"]

        sentinel = tmp_path / "baselines" / ".complete"
        assert not sentinel.exists()

        steering_runner.compute_baselines(
            model, tokenizer,
            persona_system_prompt="persona",
            questions=questions,
            output_dir=tmp_path,
            batch_size=2, max_new_tokens=4,
        )
        assert sentinel.exists(), \
            "compute_baselines must touch baselines/.complete on success"

    def test_sentinel_touched_on_already_present_fastpath(
        self, tmp_path, monkeypatch
    ):
        """Sentinel should also be present after the 'all already on disk'
        fast path (e.g. resumed run where baselines were produced by a
        prior invocation that didn't write the sentinel, or where the
        sentinel was removed/lost).  Otherwise cells in a resumed
        multi-GPU run would deadlock waiting on a sentinel that never
        comes.
        """
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        model = _FakeModel(8)
        tokenizer = _FakeTokenizer()
        questions = ["q0", "q1"]

        steering_runner.compute_baselines(
            model, tokenizer,
            persona_system_prompt="persona",
            questions=questions,
            output_dir=tmp_path,
            batch_size=2, max_new_tokens=4,
        )
        sentinel = tmp_path / "baselines" / ".complete"
        sentinel.unlink()  # simulate sentinel loss
        assert not sentinel.exists()

        # Second invocation: takes fast path, must re-touch the sentinel.
        steering_runner.compute_baselines(
            model, tokenizer,
            persona_system_prompt="persona",
            questions=questions,
            output_dir=tmp_path,
            batch_size=2, max_new_tokens=4,
        )
        assert sentinel.exists()



# ---------------------------------------------------------------------------
# Chat-template kwargs from the family table (multi-model plan § 15 Q7)
# ---------------------------------------------------------------------------

class TestTemplateKwargsFromTheFamily:
    """Until 2026-10-13 "qwen" in the model or tokenizer name switched
    thinking off and every other model got no kwargs; now the loaded model's
    config.model_type (or the name's config.json) picks the row."""

    def test_by_the_loaded_models_config(self):
        qwen = SimpleNamespace(config=SimpleNamespace(model_type="qwen3"))
        llama = SimpleNamespace(config=SimpleNamespace(model_type="llama"))
        assert steering_runner._chat_template_kwargs(qwen) == {"enable_thinking": False}
        assert steering_runner._chat_template_kwargs(llama, "Qwen/whatever") == {}

    def test_an_unknown_model_type_raises(self):
        from assistant_axis.model_families import UnknownFamilyError
        with pytest.raises(UnknownFamilyError):
            steering_runner._chat_template_kwargs(
                SimpleNamespace(config=SimpleNamespace(model_type="nope")))

    def test_by_the_name_when_the_model_has_no_type(self, monkeypatch):
        import assistant_axis.model_families as mf
        seen = []

        def fake(name):
            seen.append(name)
            return mf.FAMILIES["qwen3"]

        monkeypatch.setattr(mf, "family_for_model", fake)
        steering_runner._template_kwargs_for_name.cache_clear()
        try:
            for _ in range(2):
                assert steering_runner._chat_template_kwargs(
                    SimpleNamespace(config=SimpleNamespace()), "/local/q3") == {
                        "enable_thinking": False}
        finally:
            steering_runner._template_kwargs_for_name.cache_clear()
        assert seen == ["/local/q3"]                       # read once per name
        assert steering_runner._chat_template_kwargs(None, "") == {}

    def test_tokenize_batch_renders_with_the_rows_kwargs(self):
        seen = []

        class Tok:
            pad_token = "<pad>"
            padding_side = "right"

            pad_token_id = 0

            def apply_chat_template(self, conv, tokenize, add_generation_prompt, **kw):
                seen.append(kw)
                return [120] if tokenize else "x"

        model = SimpleNamespace(config=SimpleNamespace(model_type="qwen3"))
        steering_runner._tokenize_batch(Tok(), [[{"role": "user", "content": "q"}]],
                                        model_name="", model=model)
        # The template is asked for ids directly since 2026-10-13, so
        # return_dict=False rides along with the row's kwargs.
        assert seen == [{"return_dict": False, "enable_thinking": False}]
