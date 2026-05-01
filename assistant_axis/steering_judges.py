"""Steering-sweep judging stubs (Phase 1 of the steering sweep plan).

This module ships in Phase 1 as a stable interface only.  Real Sonnet
judging implementations land in a follow-up plan ("steering judge plan
v2", not yet written).  The runner imports `JudgeDispatcher` and uses
`NoOpJudgeDispatcher` as the default so Phase 1 can run end-to-end
without Anthropic API access.

The interface has two methods, called from the runner's hot loop:

    handle_record(record)        -> None    # called once per generated record
    should_stop_at(strength)     -> bool    # called once per strength after batches done

Phase 2 will swap in a real dispatcher that:
  - Builds 3 judge prompts per record (coherence / persona / effect)
  - Calls Sonnet asynchronously with backoff/retry
  - Writes scores back into the record's "judges" field on disk
  - Tracks per-strength mean coherence and returns True from
    should_stop_at(S) when mean_coh(S) >= COH_STOP_THRESHOLD
    (default 1.5, configurable)

The follow-up plan will fill in:
  - judge_coherence(...)  -> 0..3
  - judge_persona(...)    -> 0..3
  - judge_effect(...)     -> -3..+3

with prompt templates derived from the conversation preceding the v1
plan: each judge sees persona+description, steering direction+description,
question, optional baseline response, and the steered response.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


# ---------------------------------------------------------------------------
# Public protocol the runner depends on.
# ---------------------------------------------------------------------------

class JudgeDispatcher(Protocol):
    """Interface for a steering-sweep judging backend.

    Phase-1 callers should always pass a `NoOpJudgeDispatcher`.  Phase-2
    will provide an `AsyncSonnetJudgeDispatcher` (or similar) implementing
    the same protocol.
    """

    def handle_record(self, record: Dict[str, Any]) -> None:
        """Receive a freshly-generated record (no judges yet) for processing.

        Real implementations will async-dispatch judge API calls and write
        the scores back into the record's ``judges`` slot on disk.  The
        record dict structure is documented in the v1 plan; the
        ``judges`` slot is reserved for Phase 2:

            record["judges"] = {
                "coherence": {"score": int, "thinking": str} | None,
                "persona":   {"score": int, "thinking": str} | None,
                "effect":    {"score": int, "thinking": str} | None,
            }
        """
        ...

    def should_stop_at(self, strength: float) -> bool:
        """Return True if the worker should stop sweeping after this strength.

        Phase 2 implementation: returns True iff all records at `strength`
        have been judged and their mean coherence is at or above the
        configured stop threshold (default 1.5, escalation rule per
        Roger).

        Phase 1 (NoOp) always returns False so sweeps run to max strength.
        """
        ...

    def flush(self) -> None:
        """Wait for all in-flight judge tasks and persist any buffered state.

        Called once at the end of a worker's run.  NoOp implementation
        does nothing.
        """
        ...


# ---------------------------------------------------------------------------
# Default no-op implementation used in Phase 1.
# ---------------------------------------------------------------------------

class NoOpJudgeDispatcher:
    """Default dispatcher used in Phase 1.

    Lets the steering runner exercise its full sweep / restart / output
    paths without any judging.  Records land on disk with ``judges`` left
    as None / null, ready for a Phase-2 judge pass to fill in.
    """

    def handle_record(self, record: Dict[str, Any]) -> None:
        # Intentionally a no-op.  Records have already been written to
        # records.jsonl by the runner before this call; we just don't
        # populate the judges field.
        return

    def should_stop_at(self, strength: float) -> bool:
        # Never stop in NoOp mode -- sweep runs to its configured max.
        return False

    def flush(self) -> None:
        return


# ---------------------------------------------------------------------------
# Real-judge entry points -- stubs only in Phase 1.
# ---------------------------------------------------------------------------
#
# These signatures are reserved so the v2 plan can fill them in without
# changing the import surface.  Calling any of them raises with a pointer
# to the v2 plan.

_PHASE_2_MSG = (
    "Real judge implementations are deferred to the steering-judge plan v2. "
    "Phase 1 ships only the JudgeDispatcher protocol + NoOpJudgeDispatcher."
)


async def judge_coherence(
    *,
    persona_role: str,
    persona_description: str,
    steering_direction: str,
    steering_description: str,
    question: str,
    baseline_response: Optional[str],
    steered_response: str,
    model: str = "claude-sonnet-4-20250514",
) -> Dict[str, Any]:
    """0-3 coherence judge.

    Rubric (Phase 2 will implement):
      0 = normal, in-character (may include traits of steering direction)
      1 = slightly off (over-poetic / mystical / mildly drunk-confused)
      2 = very off (drunk / confused / wrong-language / answer-mismatch);
          may start repeating near end
      3 = quickly trapped in repetition; most of response is repetition

    Returns ``{"score": int, "thinking": str}``.
    """
    raise NotImplementedError(_PHASE_2_MSG)


async def judge_persona(
    *,
    persona_role: str,
    persona_description: str,
    steering_direction: str,
    steering_description: str,
    question: str,
    baseline_response: Optional[str],
    steered_response: str,
    model: str = "claude-sonnet-4-20250514",
) -> Dict[str, Any]:
    """0-3 persona / RP-filter judge.

    Adapted from pipeline/3_judge.py's rubric.  System prompt explicitly
    tells the judge: the response *may* legitimately display traits of
    the steering direction; only count off-character behaviour unrelated
    to either persona or steering direction.

    Returns ``{"score": int, "thinking": str}``.
    """
    raise NotImplementedError(_PHASE_2_MSG)


async def judge_effect(
    *,
    persona_role: str,
    persona_description: str,
    steering_direction: str,
    steering_description: str,
    question: str,
    baseline_response: Optional[str],
    steered_response: str,
    model: str = "claude-sonnet-4-20250514",
) -> Dict[str, Any]:
    """-3..+3 steering-effect judge.

    Mirrors results_analysis/axis_judge_correlation.py's +/-3 rubric.
    Pos pole = steering direction; neg pole = persona / opposite.
    0 = matches baseline / neutral.

    Returns ``{"score": int, "thinking": str}``.
    """
    raise NotImplementedError(_PHASE_2_MSG)
