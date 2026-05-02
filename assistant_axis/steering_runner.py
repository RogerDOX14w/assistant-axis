"""Single-cell steering sweep runner.

One call to :func:`run_steering_cell` runs the sweep for a single
``(slot, layer, sign)`` work item: builds a directional sequence of
steering strengths (geometric: ±weakest, ±weakest*mult, ..., up to
±max), generates batched responses to a fixed question list at each
strength, writes records to ``records.jsonl``, and consults a pluggable
:class:`JudgeDispatcher` for both per-record judging side-effects and an
optional incoherence-based early-termination signal.

Phase 1 of the steering sweep plan ships with
:class:`NoOpJudgeDispatcher` as the default dispatcher: records land on
disk with their ``judges`` field left null, and
``should_stop_at(strength)`` always returns False so the sweep runs to
its configured max.  Phase 2 will provide a real Sonnet-backed
dispatcher implementing the same protocol.

Baselines (strength=0 responses) are computed once per
``(persona, question)`` via :func:`compute_baselines` and shared across
all cells via the shared ``baselines/records.jsonl`` file at the
experiment root.  Cell sweeps therefore start at ±weakest, not 0.

Restart semantics
-----------------

On entry, :func:`run_steering_cell` reads any existing
``records.jsonl`` and skips ``(strength, question_idx)`` pairs already
present.  If ``summary.json`` exists with a non-null
``stopped_at_strength``, the sweep is considered complete and the
function returns immediately with a no-op (subsequent judge passes
remain a Phase 2 concern).
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import torch

from .atomic_io import (
    atomic_write_text, read_jsonl_with_retry, read_text_with_retry, write_jsonl,
)
from .steering import ActivationSteering
from .steering_judges import JudgeDispatcher, NoOpJudgeDispatcher

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sweep schedule
# ---------------------------------------------------------------------------

def directional_schedule(
    sign: int,
    *,
    weakest: float,
    max_strength: float,
    multiplier: float,
) -> List[float]:
    """Geometric schedule of strengths along one sign of the sweep.

    Returns absolute values in increasing magnitude order; the caller
    multiplies by ``sign`` when applying the steering coefficient.
    Per Roger's notebook usage, the schedule is geometric:

        [weakest, weakest * multiplier, weakest * multiplier**2, ...,
         up to and including the largest <= max_strength]

    With weakest=1.0, multiplier=1.189 (≈ 2**(1/4)), max=64 we get
    30 strengths spaced ~quarter-octave apart, matching the notebook.

    `sign` is taken as informational here (the function doesn't use it
    directly) but is required so the caller can't accidentally lose
    it; we return abs values to keep the schedule symmetric across signs.
    """
    if sign not in (+1, -1):
        raise ValueError(f"sign must be +1 or -1, got {sign}")
    if weakest <= 0 or max_strength <= 0 or multiplier <= 1:
        raise ValueError(
            f"need weakest>0, max_strength>0, multiplier>1; "
            f"got weakest={weakest}, max_strength={max_strength}, multiplier={multiplier}"
        )
    if max_strength < weakest:
        raise ValueError(f"max_strength ({max_strength}) < weakest ({weakest})")

    schedule: List[float] = []
    s = weakest
    # Round to a stable precision so JSON keys / equality checks behave
    # well across runs, matching the notebook's truncated decimals
    # (1.189, 1.414, ...).  3 decimal places is plenty.
    while s <= max_strength * (1.0 + 1e-9):
        schedule.append(round(s, 6))
        s *= multiplier
    return schedule


# ---------------------------------------------------------------------------
# Position-mode kwargs
# ---------------------------------------------------------------------------

_SUPPORTED_POSITION_MODES_V1 = {"all", "prefill_only"}
_DEFERRED_POSITION_MODES = {
    "header_matched", "system_only", "user_only", "system_user_only", "last",
}


def _build_position_kwargs(positions_mode: str,
                           input_ids: Optional[torch.Tensor] = None,
                           **kwargs) -> Dict[str, Any]:
    """Build the ActivationSteering positions/region kwargs for v1.

    V1 supports `"all"` and `"prefill_only"`.  Other modes raise so the
    runner doesn't silently fall through to the wrong behaviour; the
    expected modes for v2 are listed in the error message.
    """
    if positions_mode in _SUPPORTED_POSITION_MODES_V1:
        return {"positions": positions_mode}
    if positions_mode in _DEFERRED_POSITION_MODES:
        raise NotImplementedError(
            f"positions_mode={positions_mode!r} is deferred to a later "
            f"plan; v1 supports {_SUPPORTED_POSITION_MODES_V1}."
        )
    raise ValueError(
        f"unknown positions_mode={positions_mode!r}; "
        f"v1 supports {_SUPPORTED_POSITION_MODES_V1}"
    )


# ---------------------------------------------------------------------------
# Tokenisation helpers
# ---------------------------------------------------------------------------

def _build_conversations(
    persona_system_prompt: str,
    questions: Sequence[str],
) -> List[List[Dict[str, str]]]:
    return [
        [
            {"role": "system", "content": persona_system_prompt},
            {"role": "user", "content": q},
        ]
        for q in questions
    ]


def _tokenize_batch(
    tokenizer,
    conversations: Sequence[Sequence[Dict[str, str]]],
    *,
    model_name: str = "",
):
    """Apply chat template + tokenize a list of conversations as a left-padded batch.

    Left-padding is required for `model.generate(...)`: with right-padding,
    generated tokens would start at different absolute positions for
    each batch element, producing garbled output.
    """
    chat_template_kwargs: Dict[str, Any] = {}
    if "qwen" in model_name.lower() or "qwen" in getattr(tokenizer, "name_or_path", "").lower():
        chat_template_kwargs["enable_thinking"] = False

    prompts = [
        tokenizer.apply_chat_template(
            conv, tokenize=False, add_generation_prompt=True,
            **chat_template_kwargs
        )
        for conv in conversations
    ]
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    prev_padding_side = tokenizer.padding_side
    tokenizer.padding_side = "left"
    try:
        inputs = tokenizer(prompts, return_tensors="pt", padding=True)
    finally:
        tokenizer.padding_side = prev_padding_side
    return inputs


# ---------------------------------------------------------------------------
# Records I/O
# ---------------------------------------------------------------------------

def _read_existing_records(records_path: Path) -> List[Dict[str, Any]]:
    """Read records.jsonl with NFS-flake retries.  Empty list if file absent."""
    if not records_path.exists():
        return []
    return read_jsonl_with_retry(records_path, logger_obj=logger)


def _read_summary(summary_path: Path) -> Optional[Dict[str, Any]]:
    """Read summary.json with NFS retries; return None if absent or corrupt.

    A corrupt summary.json is treated as "no summary" rather than fatal:
    the runner will rebuild from records.jsonl on next pass.
    """
    if not summary_path.exists():
        return None
    try:
        text = read_text_with_retry(summary_path, logger_obj=logger)
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"summary.json: corrupt at {summary_path}: {e}; "
                       f"treating as missing")
        return None
    except OSError as e:
        # Read retries already exhausted by read_text_with_retry; this
        # path is effectively unreachable since it would have re-raised.
        logger.error(f"summary.json: read failed at {summary_path}: {e}")
        return None


def _write_summary(summary_path: Path, summary: Dict[str, Any]) -> None:
    atomic_write_text(json.dumps(summary, indent=2) + "\n", summary_path,
                      logger_obj=logger)


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

def compute_baselines(
    model,
    tokenizer,
    *,
    persona_system_prompt: str,
    questions: Sequence[str],
    output_dir: Union[str, Path],
    batch_size: int = 8,
    max_new_tokens: int = 256,
    do_sample: bool = False,
    temperature: float = 0.0,
    model_name: str = "",
) -> List[Dict[str, Any]]:
    """Generate baseline (no-steering) responses for every question.

    Stored once per ``(persona, question)`` at
    ``output_dir/baselines/records.jsonl``; cell sweeps consume them by
    ``question_idx`` when assembling judge prompts in Phase 2 (and as a
    diff reference for cherrypicking).

    Idempotent: existing baseline records.jsonl entries are skipped.
    """
    output_dir = Path(output_dir)
    baselines_dir = output_dir / "baselines"
    baselines_dir.mkdir(parents=True, exist_ok=True)
    records_path = baselines_dir / "records.jsonl"

    existing = _read_existing_records(records_path)
    have_idx = {r["question_idx"] for r in existing}

    todo = [(i, q) for i, q in enumerate(questions) if i not in have_idx]
    if not todo:
        logger.info(f"[baselines] all {len(questions)} already present at {records_path}")
        return existing

    logger.info(
        f"[baselines] computing {len(todo)} of {len(questions)} baseline responses"
    )

    new_records: List[Dict[str, Any]] = []
    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start:batch_start + batch_size]
        batch_questions = [q for _, q in batch]
        batch_idx = [i for i, _ in batch]
        conversations = _build_conversations(persona_system_prompt, batch_questions)
        inputs = _tokenize_batch(tokenizer, conversations, model_name=model_name)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        prompt_len = inputs["input_ids"].shape[1]

        t0 = time.time()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else None,
                pad_token_id=tokenizer.pad_token_id,
            )
        elapsed = time.time() - t0

        for j, (q_idx, q) in enumerate(zip(batch_idx, batch_questions)):
            gen_ids = outputs[j, prompt_len:]
            response = tokenizer.decode(gen_ids, skip_special_tokens=True)
            n_tok = int((gen_ids != tokenizer.pad_token_id).sum().item())
            rec = {
                "strength": 0.0,
                "sign": 0,
                "question_idx": q_idx,
                "question": q,
                "response": response,
                "n_tokens": n_tok,
                "judges": {"coherence": None, "persona": None, "effect": None},
                "timing": {"gen_s": elapsed / max(1, len(batch))},
            }
            existing.append(rec)
            new_records.append(rec)

        # Flush after each batch so a crash doesn't lose more than a batch
        write_jsonl(existing, records_path, logger_obj=logger)

    logger.info(f"[baselines] wrote {len(new_records)} new records to {records_path}")
    return existing


# ---------------------------------------------------------------------------
# The main per-cell runner
# ---------------------------------------------------------------------------

@dataclass
class CellResult:
    """Outcome of running a single (slot, layer, sign) cell."""
    stopped_at_strength: Optional[float] = None
    reason: str = "completed"     # "completed" | "incoherent" | "already_done"
    n_records: int = 0
    n_strengths_swept: int = 0
    summary: Dict[str, Any] = field(default_factory=dict)


def run_steering_cell(
    model,
    tokenizer,
    *,
    axis_vector: torch.Tensor,
    slot: int,
    layer: int,
    sign: int,
    strengths: Sequence[float],
    persona_system_prompt: str,
    questions: Sequence[str],
    output_dir: Union[str, Path],
    batch_size: int = 8,
    max_new_tokens: int = 256,
    positions_mode: str = "all",
    do_sample: bool = False,
    temperature: float = 0.0,
    judge_dispatcher: Optional[JudgeDispatcher] = None,
    model_name: str = "",
) -> CellResult:
    """Run the steering sweep for one (slot, layer, sign) cell.

    Parameters
    ----------
    model, tokenizer
        Already-loaded HuggingFace model + tokenizer on the target GPU.
    axis_vector
        1-D steering direction, shape (hidden,).  Caller pre-extracts
        from ``axis_raw[slot, layer]``.
    slot, layer, sign
        Cell coordinates.  Recorded in each output record so cross-cell
        analysis can locate every record's origin.
    strengths
        Absolute-value strength schedule in increasing order (caller
        multiplies by ``sign`` internally; pass output of
        :func:`directional_schedule`).
    persona_system_prompt
        System prompt fixed for this experiment (one persona per run in
        v1).
    questions
        Frozen question list for the experiment.
    output_dir
        Cell-specific directory, e.g.
        ``/workspace/.../{experiment}/s{slot}_l{layer}_{sign}``.
    batch_size, max_new_tokens, do_sample, temperature
        Generation knobs.  Default greedy with 256 max tokens to keep
        screening sweeps fast.
    positions_mode
        ``"all"`` or ``"prefill_only"``; other modes raise NotImplementedError
        (deferred to v2).
    judge_dispatcher
        If None, a :class:`NoOpJudgeDispatcher` is used (Phase 1
        default).  Phase 2 callers will pass a real dispatcher.
    model_name
        Used to detect Qwen-family chat-template kwargs (enable_thinking).
        Optional.

    Returns
    -------
    CellResult describing whether the sweep completed or stopped early.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records_path = output_dir / "records.jsonl"
    summary_path = output_dir / "summary.json"

    dispatcher = judge_dispatcher or NoOpJudgeDispatcher()

    # Resume shortcut: if summary already records a stop, we're done with
    # generation and just need Phase 2 (in v1, nothing more to do).
    existing_summary = _read_summary(summary_path)
    if existing_summary and existing_summary.get("stopped_at_strength") is not None:
        logger.info(
            f"[cell s{slot}_l{layer}_{sign}] already stopped at "
            f"strength={existing_summary['stopped_at_strength']}; skipping"
        )
        return CellResult(
            stopped_at_strength=existing_summary.get("stopped_at_strength"),
            reason=existing_summary.get("reason", "incoherent"),
            n_records=existing_summary.get("n_records", 0),
            n_strengths_swept=existing_summary.get("n_strengths_swept", 0),
            summary=existing_summary,
        )

    existing_records = _read_existing_records(records_path)
    done_pairs = {(r["strength"], r["question_idx"]) for r in existing_records}
    if existing_records:
        logger.info(
            f"[cell s{slot}_l{layer}_{sign}] resuming with "
            f"{len(existing_records)} existing records"
        )

    # Validate positions_mode early so we don't get most of the way
    # through the sweep before discovering misconfiguration.
    _build_position_kwargs(positions_mode)

    # Pre-build conversations once (same across strengths).
    conversations = _build_conversations(persona_system_prompt, questions)

    n_strengths_swept = 0
    last_strength_completed: Optional[float] = None

    def _flush_records():
        """Use the dispatcher's atomic-write if available (avoids races with
        async judge writes); otherwise fall back to plain write_jsonl."""
        if hasattr(dispatcher, "write_records_atomic"):
            dispatcher.write_records_atomic(existing_records)
        else:
            write_jsonl(existing_records, records_path, logger_obj=logger)

    for strength in strengths:
        eff_coeff = float(strength) * float(sign)
        logger.info(
            f"[cell s{slot}_l{layer}_{sign}] strength={strength:.4f} "
            f"sign={sign:+d} eff_coeff={eff_coeff:+.4f}"
        )
        any_progress_this_strength = False
        # Tracks newly-generated records at this strength so we can
        # enqueue them as a single (cell, sign, strength) group after
        # the strength's batches finish.  Existing records (restored
        # from disk on restart) are not re-enqueued; post_judge.py is
        # the canonical retrospective fill-in path.
        new_at_strength: List[Dict[str, Any]] = []

        for batch_start in range(0, len(questions), batch_size):
            # Build batch of (q_idx, question, conversation) for items
            # not yet in the records.
            batch_items = []
            for offset in range(batch_size):
                q_idx = batch_start + offset
                if q_idx >= len(questions):
                    break
                if (strength, q_idx) in done_pairs:
                    continue
                batch_items.append((q_idx, questions[q_idx], conversations[q_idx]))
            if not batch_items:
                continue
            any_progress_this_strength = True

            batch_convs = [c for _, _, c in batch_items]
            inputs = _tokenize_batch(tokenizer, batch_convs, model_name=model_name)
            inputs = {k: v.to(model.device) for k, v in inputs.items()}
            prompt_len = inputs["input_ids"].shape[1]

            position_kwargs = _build_position_kwargs(positions_mode)
            t0 = time.time()
            with ActivationSteering(
                model,
                steering_vectors=[axis_vector],
                coefficients=[eff_coeff],
                layer_indices=[layer],
                **position_kwargs,
            ):
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=max_new_tokens,
                        do_sample=do_sample,
                        temperature=temperature if do_sample else None,
                        pad_token_id=tokenizer.pad_token_id,
                    )
            elapsed = time.time() - t0
            per_item_s = elapsed / max(1, len(batch_items))

            new_records_this_batch: List[Dict[str, Any]] = []
            for j, (q_idx, q, _conv) in enumerate(batch_items):
                gen_ids = outputs[j, prompt_len:]
                response = tokenizer.decode(gen_ids, skip_special_tokens=True)
                n_tok = int((gen_ids != tokenizer.pad_token_id).sum().item())
                rec: Dict[str, Any] = {
                    "strength": float(strength),
                    "sign": int(sign),
                    "slot": int(slot),
                    "layer": int(layer),
                    "question_idx": int(q_idx),
                    "question": q,
                    "response": response,
                    "n_tokens": n_tok,
                    "judges": {"coherence": None, "persona": None, "effect": None},
                    "timing": {"gen_s": per_item_s},
                    "abandoned": False,
                }
                existing_records.append(rec)
                new_records_this_batch.append(rec)
                new_at_strength.append(rec)
                done_pairs.add((float(strength), int(q_idx)))

            # Flush per-batch (per Roger's "save after each question set").
            # Records here have coherence=None; the inline coh-judge call
            # below populates that field and we re-flush.
            _flush_records()

            # Tier 1 -- coherence (synchronous, blocks the sweep).  This
            # is what gates early termination in should_stop_at().  In
            # Phase-1 NoOpJudgeDispatcher this returns 0 and writes
            # nothing; Phase-2 RealJudgeDispatcher does an OpenAI call,
            # parses {"score": int, "reason": str}, and stamps
            # judges.coherence.
            for rec in new_records_this_batch:
                dispatcher.judge_coherence_blocking(rec)
            # Re-flush so coh is durable before any async work fires.
            _flush_records()

        if any_progress_this_strength:
            n_strengths_swept += 1
            last_strength_completed = float(strength)

        # Tier 2 -- enqueue the strength group for async RP + effect
        # judging.  The dispatcher computes strength_mean_coh, decides
        # skip-or-judge based on its skip threshold, stamps every record
        # with strength_mean_coh, and (in the judge path) fans out
        # background API calls.  NoOp does nothing.
        if new_at_strength:
            dispatcher.enqueue_strength_group(
                cell_dir=str(output_dir), slot=int(slot), layer=int(layer),
                sign=int(sign), strength=float(strength),
                records=new_at_strength,
            )

        # Early-termination: with the real dispatcher this consults
        # strength_mean_coh against coh_stop_threshold; with NoOp it
        # always returns False.
        if dispatcher.should_stop_at(float(strength)):
            logger.info(
                f"[cell s{slot}_l{layer}_{sign}] dispatcher signalled stop "
                f"at strength={strength} (mean_coh past threshold)"
            )
            summary = {
                "slot": slot, "layer": layer, "sign": sign,
                "stopped_at_strength": float(strength),
                "reason": "incoherent",
                "n_records": len(existing_records),
                "n_strengths_swept": n_strengths_swept,
                "last_strength_completed": last_strength_completed,
            }
            _write_summary(summary_path, summary)
            dispatcher.drain()
            return CellResult(
                stopped_at_strength=float(strength),
                reason="incoherent",
                n_records=len(existing_records),
                n_strengths_swept=n_strengths_swept,
                summary=summary,
            )

    # Sweep completed all strengths
    summary = {
        "slot": slot, "layer": layer, "sign": sign,
        "stopped_at_strength": None,
        "reason": "completed",
        "n_records": len(existing_records),
        "n_strengths_swept": n_strengths_swept,
        "last_strength_completed": last_strength_completed,
    }
    _write_summary(summary_path, summary)
    dispatcher.drain()
    return CellResult(
        stopped_at_strength=None,
        reason="completed",
        n_records=len(existing_records),
        n_strengths_swept=n_strengths_swept,
        summary=summary,
    )
