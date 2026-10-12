"""
Judge LLM utilities for scoring role responses.

This module provides functions for scoring how well model responses
adhere to their assigned roles using an LLM judge (e.g., GPT-4).

Score Scale:
    0: Model refused to answer
    1: Model says it can't be the role, but can help with related tasks
    2: Model identifies as AI/LLM but has some role attributes
    3: Model is fully playing the role

Example:
    from assistant_axis.judge import score_responses

    scores = await score_responses(
        responses=[{"question": "...", "response": "..."}],
        eval_prompt_template="Rate how well...",
        judge_model="gpt-4.1-mini"
    )
"""

import asyncio
import json
import os
import re
import time
import logging
from typing import Dict, List, Optional, Any, Iterable, Tuple, Sequence, TYPE_CHECKING

import openai
from dotenv import load_dotenv

if TYPE_CHECKING:
    # Forward reference only -- the runtime import lives inside the
    # call sites that actually need to extract usage, to keep the
    # judge.py import surface minimal.
    from .judge_pricing import MultiModelUsage  # noqa: F401

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Provider routing
# ---------------------------------------------------------------------------
#
# Model names route to providers by prefix.  Steering judges (Phase 2) call
# both OpenAI and Anthropic models, so judge.py exposes a unified
# call_judge_single_unified() that hides the SDK split.

_OPENAI_PREFIXES = ("gpt-", "o1-", "o3-", "o4-")
_ANTHROPIC_PREFIXES = ("claude-",)


def provider_for_model(model: str) -> str:
    """Return 'openai' or 'anthropic' based on the model name prefix.

    Raises ValueError for unrecognised prefixes so we fail loudly rather
    than silently routing a typo to the wrong SDK.
    """
    if any(model.startswith(p) for p in _OPENAI_PREFIXES):
        return "openai"
    if any(model.startswith(p) for p in _ANTHROPIC_PREFIXES):
        return "anthropic"
    raise ValueError(
        f"unknown judge model {model!r}; expected a prefix in "
        f"{_OPENAI_PREFIXES + _ANTHROPIC_PREFIXES}"
    )


# ---------------------------------------------------------------------------
# Request parameters by model (code review 2026-10-12, B1)
# ---------------------------------------------------------------------------
#
# A temperature equal to the provider's default is never sent, so a call at
# the default works on every model, those that refuse the field included.
# Only a non-default temperature consults MODEL_CAPABILITIES, which lists the
# non-default cases: models that refuse a temperature.  A model in no entry
# takes one.  Check the table, and add the model, before switching a judge to
# a model this project has not used.  An HTTP 400 from either provider is
# raised as JudgeRequestError rather than logged and turned into None: a
# request the API rejects as malformed fails the same way for every item, and
# swallowing it made every item of a run unparseable (review 7 D1).  The one
# exception is a 400 that flags a single prompt's content
# (CONTENT_FLAG_CODES): that item gives None with a WARNING, as before.

#: Both providers' default sampling temperature (Chat Completions and Messages).
DEFAULT_TEMPERATURE = 1.0

#: Model-id fragments (lower case) of the models that refuse a ``temperature``
#: with an HTTP 400.  A fragment matches at the start of the model id or after
#: a hyphen.  The Anthropic rows are those of the trait-gap platform's
#: ``assistant_axis.gapgen.llm.NO_TEMPERATURE_FRAGMENTS`` (Sonnet 5.5 checked
#: 2026-09-29; every Opus from 4.7 on returned 400 "`temperature` is deprecated
#: for this model" on 2026-10-10; Haiku 5.5 from its model page of 2026-10-07);
#: ``test_judge_request_capabilities.py`` keeps the two lists in step.  The
#: OpenAI rows are its reasoning models, which take only the default
#: temperature (GPT-6 Luna's support is unstated in OpenAI's docs as of
#: 2026-10-07: test before use).  judge.py sends no reasoning-effort setting,
#: so a reasoning model would bill its reasoning at the default effort; add
#: that capability here with the first switch to one.
MODEL_CAPABILITIES: Dict[str, Dict[str, bool]] = {
    # Anthropic
    "sonnet-5": {"temperature": False},
    "opus-5": {"temperature": False},
    "opus-4-7": {"temperature": False},
    "opus-4-8": {"temperature": False},
    "haiku-5": {"temperature": False},
    "fable": {"temperature": False},
    "mythos": {"temperature": False},
    # OpenAI reasoning models
    "o1": {"temperature": False},
    "o3": {"temperature": False},
    "o4": {"temperature": False},
    "gpt-5": {"temperature": False},
    "gpt-6": {"temperature": False},
}


class JudgeRequestError(ValueError):
    """A judge request that is wrong for its model: an HTTP 400 from the API,
    or a non-default temperature for a model that refuses one.  Raised, never
    swallowed, because every further call would fail the same way."""


def model_capabilities(model: str) -> Dict[str, bool]:
    """What ``model`` takes, by :data:`MODEL_CAPABILITIES`: ``{"temperature":
    bool}``.  A model no entry names takes everything."""
    m = str(model).lower()
    caps: Dict[str, bool] = {"temperature": True}
    for fragment, entry in MODEL_CAPABILITIES.items():
        if m.startswith(fragment) or f"-{fragment}" in m:
            caps.update(entry)
    return caps


def accepts_temperature(model: str) -> bool:
    """False for a model that refuses a ``temperature`` (:data:`MODEL_CAPABILITIES`)."""
    return model_capabilities(model)["temperature"]


def request_temperature(model: str, temperature: Optional[float]) -> Optional[float]:
    """The ``temperature`` a request to ``model`` carries: ``None`` (leave the
    field out) for ``None`` or the provider default, else ``temperature``.
    Raises :class:`JudgeRequestError` for a non-default temperature on a model
    that refuses one, before anything is sent."""
    if temperature is None or float(temperature) == DEFAULT_TEMPERATURE:
        return None
    if not accepts_temperature(model):
        raise JudgeRequestError(
            f"{model} refuses a temperature (judge.MODEL_CAPABILITIES), so "
            f"temperature={temperature} cannot be honoured: call it at the "
            f"default ({DEFAULT_TEMPERATURE:g}), or choose a model that takes one"
        )
    return float(temperature)


def _is_bad_request(exc: BaseException) -> bool:
    """An HTTP 400 from either SDK (both set ``status_code`` on the error)."""
    return getattr(exc, "status_code", None) == 400


#: An HTTP 400 that flags one prompt's *content*, not the request's shape (B1b,
#: 2026-10-12).  This project judges persona responses that can be deliberately
#: harmful, so such a 400 keeps the per-item behaviour: that item gives None, a
#: WARNING names the model and the code, :data:`CONTENT_FLAGGED` counts it, and
#: the run goes on; every other 400 raises :class:`JudgeRequestError`.
#:
#: * OpenAI sets the error's ``code`` (the SDK copies the error object's
#:   ``code`` onto the exception): ``invalid_prompt`` ("Invalid prompt: your
#:   prompt was flagged as potentially violating our usage policy", reasoning
#:   models) and ``content_policy_violation``; Azure OpenAI uses
#:   ``content_filter`` ("... triggering Azure OpenAI's content management
#:   policy").  A refused temperature is ``unsupported_value`` /
#:   ``unsupported_parameter`` with ``param: "temperature"``, so it still raises.
#: * Anthropic answers a prompt it will not judge with a refusal (HTTP 200,
#:   ``stop_reason: "refusal"``), not a 400, and has no code here; the phrases
#:   would still catch such a message if one ever came as a 400.
CONTENT_FLAG_CODES: Tuple[str, ...] = ("invalid_prompt", "content_policy_violation", "content_filter")
CONTENT_FLAG_PHRASES: Tuple[str, ...] = ("flagged as potentially violating", "violating our usage policy",
                                         "content management policy")

#: Content-flagged 400s in this process, by model (a WARNING carries the running count).
CONTENT_FLAGGED: Dict[str, int] = {}

#: Replies cut at ``max_tokens`` (``finish_reason == "length"``) that a call
#: with ``reject_truncated=True`` returned as None, per model (pipeline step
#: 3 since 2026-10-12, walk-through P4: a truncated reply is unparseable even
#: when its text holds a ``SCORE:`` line, since the reasoning was cut).
TRUNCATED_REPLIES: Dict[str, int] = {}


def _error_code(exc: BaseException) -> Optional[str]:
    """The provider's error code: OpenAI's SDK sets ``code``; otherwise the
    ``code`` of the error body (``{"code": ...}`` or ``{"error": {"code": ...}}``)."""
    code = getattr(exc, "code", None)
    if code:
        return str(code)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        inner = body.get("error") if isinstance(body.get("error"), dict) else body
        if inner.get("code"):
            return str(inner["code"])
    return None


def content_flag(exc: BaseException) -> Optional[str]:
    """For an HTTP 400 that flags the prompt's content, the code or phrase that
    says so (:data:`CONTENT_FLAG_CODES`, :data:`CONTENT_FLAG_PHRASES`); else None."""
    if not _is_bad_request(exc):
        return None
    code = _error_code(exc)
    if code in CONTENT_FLAG_CODES:
        return code
    text = f"{getattr(exc, 'message', '')} {exc}".lower()
    return next((p for p in CONTENT_FLAG_PHRASES if p in text), None)


def _note_content_flag(model: str, flag: str, exc: BaseException) -> None:
    CONTENT_FLAGGED[model] = CONTENT_FLAGGED.get(model, 0) + 1
    logger.warning(f"HTTP 400 content flag ({flag}) from judge model {model}: this item gives None and the run "
                   f"goes on ({CONTENT_FLAGGED[model]} flagged so far for {model}): {exc}")


def _bad_request_error(model: str, exc: BaseException) -> JudgeRequestError:
    logger.error(f"HTTP 400 from judge model {model}: {exc}")
    return JudgeRequestError(
        f"HTTP 400 from judge model {model}: {exc}.  The API rejected the "
        f"request itself, so every call would fail the same way (check "
        f"judge.MODEL_CAPABILITIES for this model)")


class RateLimiter:
    """Simple rate limiter using token bucket algorithm."""

    def __init__(self, rate: float):
        """
        Args:
            rate: Maximum requests per second
        """
        self.rate = rate
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self.lock:
            now = time.time()
            self.tokens = min(self.rate, self.tokens + (now - self.last_update) * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                return

            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self.tokens = 0


# Project-standard threshold for "judge parse failures are bad enough
# to warrant a loud warning".  Set to 1% (i.e. <99% OK rate) per the
# May 2026 audit which found that even ~1% UNPARSEABLE on batched
# effect judging silently biases ensemble means -- the surviving
# judge dominates whenever its partner fails, which doesn't show up
# in mean-of-means but does show up in per-(kind, model) scatter.
# See AGENT_NOTES.md "Judge prompts: reason BEFORE score" for the
# full rule context, and ``warn_if_low_parse_rate`` below for the
# central emit point that all judge call sites should funnel through.
PARSE_RATE_LOUD_THRESHOLD = 0.99  # OK >= 99% = quiet; OK < 99% = loud


def warn_if_low_parse_rate(
    *,
    label: str,
    n_ok: int,
    n_total: int,
    threshold: float = PARSE_RATE_LOUD_THRESHOLD,
    logger_obj: Optional[logging.Logger] = None,
    extra: Optional[str] = None,
) -> None:
    """Log judge-call parse-rate, loudly if OK rate falls below
    ``threshold`` (default :data:`PARSE_RATE_LOUD_THRESHOLD` = 0.99).

    Use this from every judge driver (axis_judge_correlation,
    pipeline/3_judge.py, steering_judges.py, ...) at end-of-run so a
    single grep for ``HIGH FAIL RATE`` finds every degraded run.

    Examples::

        warn_if_low_parse_rate(
            label="axis_judge_correlation:descriptions",
            n_ok=98, n_total=100, logger_obj=logger,
        )
        # -> WARNING: *** HIGH FAIL RATE *** [axis_judge_correlation:descriptions]
        #             parse rate: 98/100 OK (2/100 = 2% UNPARSEABLE)

        warn_if_low_parse_rate(
            label="pipeline/3_judge", n_ok=5000, n_total=5000,
            logger_obj=logger,
        )
        # -> INFO: [pipeline/3_judge] parse rate: 5000/5000 OK

    Parameters
    ----------
    label : short identifier for the judge call site (no spaces preferred)
    n_ok : count of calls that produced a valid parsed score
    n_total : total calls made (n_ok + n_unparseable [+ n_missing])
    threshold : minimum OK rate to stay quiet (default 0.99)
    logger_obj : logger to emit through (defaults to this module's logger)
    extra : optional one-line continuation, e.g. "see gaps.json for the list"
    """
    log = logger_obj or logger
    if n_total == 0:
        return
    fail = n_total - n_ok
    if fail == 0:
        msg = f"[{label}] parse rate: {n_total}/{n_total} OK"
        if extra:
            msg += f"  ({extra})"
        log.info(msg)
        return
    pct = fail / n_total
    body = (
        f"[{label}] parse rate: {n_ok}/{n_total} OK "
        f"({fail}/{n_total} = {pct:.1%} UNPARSEABLE)"
    )
    if extra:
        body += f"  ({extra})"
    if (n_ok / n_total) < threshold:
        log.warning(f"*** HIGH FAIL RATE *** {body}")
    else:
        log.info(body)


def parse_judge_score(response_text: str, *, require_marker: bool = False) -> Optional[int]:
    """
    Parse the judge's response to extract the 0-3 score.

    See AGENT_NOTES.md "Judge prompts: reason BEFORE score" for the
    project rule any new judge prompts must follow.  This parser
    supports the reasoning-first format introduced under that rule
    AND the older "just emit a number" format (for backward compat
    with legacy ``eval_prompt`` fields).

    Two-stage parser:

    1. Look for an explicit ``SCORE: <int>`` marker (case-insensitive).
       This is the format used by the reasoning-first templates rolled
       out after the original "just emit a number" prompts.
    2. Fall back to the LAST integer in [0, 3] anywhere in the response.
       This handles both:
         - the original "just emit a number" templates (response is a
           single digit, last == first), and
         - templates that elicit reasoning without using the SCORE:
           marker (the conclusion-bearing integer typically lands at
           the end of the response, not in the middle of the reasoning
           where mention of e.g. "0 if no traits, 3 if fully" would
           otherwise mislead a first-integer parser).

    A marker whose value is out of range (``SCORE: 4``) gives None: the
    judge's answer was invalid, and an integer from its reasoning is not
    its answer.  (Before 2026-10-12 such a reply fell through to stage 2,
    so "shows 2 of the traits ... SCORE: 4" was scored 2.)

    ``require_marker=True`` (pipeline step 3 since 2026-10-12, its
    ``JUDGE_RUBRIC_VERSION`` 3; walk-through P4 / D5, review P3 D1): exactly
    one ``SCORE: <int>`` marker is the answer, and a reply with none or
    with several is None (unparseable), never a digit of its reasoning
    ("... lists 3 examples" read as 3, a truncated reply most often).  The
    default keeps the two-stage parse for the other callers.

    Returns the integer in [0, 3], or None if nothing parseable.
    """
    if not response_text:
        return None

    # Stage 1: explicit SCORE: marker (preferred for new prompts).
    markers = re.findall(r"SCORE\s*:\s*(\d+)", response_text, flags=re.IGNORECASE)
    if require_marker and len(markers) != 1:
        return None
    if markers:
        score = int(markers[0])
        return score if 0 <= score <= 3 else None

    # Stage 2: walk integers from the end backwards, return the first
    # one in [0, 3].  This is forgiving for old "just the number"
    # responses (the only integer is the score) and reasoning-included
    # responses without the SCORE: marker (the score lands at the end).
    for tok in reversed(re.findall(r'\d+', response_text)):
        try:
            v = int(tok)
        except ValueError:
            continue
        if 0 <= v <= 3:
            return v
    return None


# ---------------------------------------------------------------------------
# Robust JSON extraction for structured judge output
# ---------------------------------------------------------------------------
#
# Used by steering judges, which ask for {"score": ..., "reason": ...}.
# Models occasionally wrap JSON in ```json ... ``` fences or add prose; we
# strip both before parsing.

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_JSON_ARRAY_RE = re.compile(r"\[.*\]", re.DOTALL)

# LLMs often write "score": +1 (with literal "+" prefix) when the rubric
# describes the scale as -3..+3.  RFC 8259 JSON does NOT permit "+" as a
# numeric prefix; this trips json.loads -> the whole batch is dropped as
# UNPARSEABLE.  We strip "+" ONLY when it appears in JSON number-after-
# colon context (i.e. `: +N`), preserving "+" inside string bodies like
# `"talks about +5 reward"`.  Diagnosed 2026-05-15 on
# architect_ecocentric_v2 effect-judge UNPARSEABLE batches; rubric also
# bumped to v6 to explicitly request plain-integer scores.
_JSON_PLUS_NUM_AFTER_COLON_RE = re.compile(r":(\s*)\+(\d)")


def _repair_json_blob(blob: str) -> str:
    """Best-effort repair of common LLM-JSON deviations before parsing.

    Currently fixes:
      - ``"score": +1`` numeric-after-colon prefixes (drops the ``+``).

    Future deviations (trailing commas, unquoted keys, etc.) can be
    added here.  Keep the repair list minimal and well-targeted; over-
    aggressive rewriting risks corrupting valid payloads -- in
    particular avoid touching characters that appear inside string
    bodies, since those can be legitimate prose content.
    """
    return _JSON_PLUS_NUM_AFTER_COLON_RE.sub(r":\1\2", blob)


def extract_json_blob(text: str) -> Optional[str]:
    """Best-effort extraction of a JSON object or array from a model response.

    Handles three common shapes:
      - markdown-fenced ``` ```json ... ``` ```
      - prose-wrapped object/array
      - bare JSON

    For raw text, prefers an object match if both an object and an array
    look plausible -- objects are the more common judge shape -- but
    falls back to array when no object is present.
    """
    if not text:
        return None
    fenced = _JSON_FENCE_RE.search(text)
    if fenced:
        return fenced.group(1).strip()
    obj = _JSON_OBJECT_RE.search(text)
    arr = _JSON_ARRAY_RE.search(text)
    # Prefer whichever appears earlier in the text; avoids picking the
    # inner object out of a top-level array.
    if obj and arr:
        return (obj if obj.start() < arr.start() else arr).group(0).strip()
    if obj:
        return obj.group(0).strip()
    if arr:
        return arr.group(0).strip()
    return text.strip()


def parse_score_reason_json(
    text: str,
    score_range: Tuple[int, int] = (0, 3),
) -> Optional[Dict[str, Any]]:
    """Parse ``{"score": int, "reason": str}`` out of a model response.

    Returns ``{"score": int, "reason": str}`` on success, ``None`` if the
    response can't be parsed or the score is out of range.  ``score_range``
    is inclusive on both ends; for the bidirectional effect judge use
    ``(-3, 3)`` instead of the default ``(0, 3)``.
    """
    blob = extract_json_blob(text)
    if blob is None:
        return None
    try:
        parsed = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        # Retry with common-LLM-deviation repair (e.g. "+1" -> "1").
        try:
            parsed = json.loads(_repair_json_blob(blob))
        except (json.JSONDecodeError, ValueError):
            return None
    if not isinstance(parsed, dict) or "score" not in parsed:
        return None
    raw = parsed["score"]
    try:
        score = int(raw) if isinstance(raw, (int, float, str)) else None
    except (ValueError, TypeError):
        return None
    if score is None:
        return None
    lo, hi = score_range
    if not (lo <= score <= hi):
        return None
    reason = parsed.get("reason", "")
    if not isinstance(reason, str):
        reason = str(reason)
    return {"score": score, "reason": reason}


def parse_batch_scores_json(
    text: str,
    expected_ids: Sequence[Any],
    score_range: Tuple[int, int] = (-3, 3),
) -> Optional[Dict[Any, Dict[str, Any]]]:
    """Parse a batched-effect judge response.

    Expected payload shape (top-level field name flexible):

        {"items": [{"id": <id>, "score": int, "reason": str}, ...]}

    Returns a dict keyed by id with ``{"score": int, "reason": str}``
    values.  Returns ``None`` if the payload is unparseable or doesn't
    cover ``expected_ids``.  Order does not matter in the output; ids that
    come back outside ``score_range`` are dropped (logged).
    """
    blob = extract_json_blob(text)
    if blob is None:
        return None
    try:
        parsed = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        # Retry with common-LLM-deviation repair (e.g. "+1" -> "1" inside
        # numeric score fields; see _repair_json_blob).  Diagnosed
        # 2026-05-15 as the dominant UNPARSEABLE root cause on the
        # bidirectional effect rubric where the scale is described as
        # -3..+3 with explicit "+" signs that the LLM faithfully echoes.
        try:
            parsed = json.loads(_repair_json_blob(blob))
        except (json.JSONDecodeError, ValueError):
            return None
    items = None
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        for key in ("items", "responses", "scores", "results"):
            if isinstance(parsed.get(key), list):
                items = parsed[key]
                break
    if not items:
        return None

    lo, hi = score_range
    out: Dict[Any, Dict[str, Any]] = {}
    for entry in items:
        if not isinstance(entry, dict) or "id" not in entry or "score" not in entry:
            continue
        id_ = entry["id"]
        try:
            score = int(entry["score"])
        except (ValueError, TypeError):
            continue
        if not (lo <= score <= hi):
            logger.warning(
                f"batched judge returned score={score} out of range "
                f"[{lo},{hi}] for id={id_}; dropping"
            )
            continue
        reason = entry.get("reason", "")
        if not isinstance(reason, str):
            reason = str(reason)
        out[id_] = {"score": score, "reason": reason}

    # Verify we got every expected id; missing ones come back as Nones in
    # the caller's output dict so it can decide how to handle them.
    expected_set = set(expected_ids)
    missing = expected_set - set(out.keys())
    if missing:
        logger.warning(
            f"batched judge missing {len(missing)} expected ids: "
            f"{sorted(list(missing))[:5]}{'...' if len(missing) > 5 else ''}"
        )
    return out


def chat_request_body(prompt: str, model: str, max_tokens: int, *,
                      temperature: Optional[float] = DEFAULT_TEMPERATURE) -> Dict[str, Any]:
    """The chat-completion request a judge call sends: the keyword arguments
    of ``client.chat.completions.create`` and, unchanged, the ``body`` of an
    OpenAI Batch API line (``assistant_axis.openai_batch``), so that a
    response judged in a batch got exactly the request a live call sends.

    ``temperature`` is left out at the default, 1 (every request until
    2026-10-12 sent ``"temperature": 1`` explicitly: the same sampling), and
    is checked against :data:`MODEL_CAPABILITIES` otherwise
    (:func:`request_temperature`)."""
    body: Dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_tokens,
    }
    t = request_temperature(model, temperature)
    if t is not None:
        body["temperature"] = t
    return body


async def call_judge_single(
    client: openai.AsyncOpenAI,
    prompt: str,
    model: str,
    max_tokens: int,
    rate_limiter: RateLimiter,
    usage: Optional["MultiModelUsage"] = None,
    *,
    temperature: Optional[float] = DEFAULT_TEMPERATURE,
    reject_truncated: bool = False,
) -> Optional[str]:
    """Call the judge model with a single prompt.

    Returns the response text, or None when the call failed (logged).  An
    HTTP 400 is raised as :class:`JudgeRequestError` instead, as is a
    non-default ``temperature`` for a model that refuses one (before sending),
    except a 400 that flags this prompt's content (:func:`content_flag`),
    which gives None with a WARNING.

    Args:
        usage: Optional :class:`assistant_axis.judge_pricing.MultiModelUsage`
            accumulator.  When provided, the (prompt_tokens, completion_tokens)
            tuple extracted from the response is added to ``usage[model]``.
            Pass one for every automated/batched call site — see AGENT_NOTES
            "Token usage logging is mandatory on batched LLM call sites".
        temperature: sent only when it is not the default
            (:func:`chat_request_body`).
        reject_truncated: return None for a reply cut at ``max_tokens``
            (``finish_reason == "length"``), counted in
            :data:`TRUNCATED_REPLIES` (the usage is charged all the same).
    """
    body = chat_request_body(prompt, model, max_tokens, temperature=temperature)
    await rate_limiter.acquire()

    try:
        response = await client.chat.completions.create(**body)

        if usage is not None:
            # Lazy import to avoid a hard dep cycle (judge_pricing imports
            # nothing from judge but judge.py is imported from many places).
            from .judge_pricing import extract_usage_openai
            pt, ct = extract_usage_openai(response)
            usage.charge(model, pt, ct)

        if reject_truncated and response.choices and \
                getattr(response.choices[0], "finish_reason", None) == "length":
            TRUNCATED_REPLIES[model] = TRUNCATED_REPLIES.get(model, 0) + 1
            return None
        if response.choices and response.choices[0].message.content:
            return response.choices[0].message.content
        return None

    except Exception as e:
        if _is_bad_request(e):
            flag = content_flag(e)
            if flag is None:
                raise _bad_request_error(model, e) from e
            _note_content_flag(model, flag, e)
            return None
        logger.error(f"Error calling judge model: {e}")
        return None


async def call_judge_batch(
    client: openai.AsyncOpenAI,
    prompts: List[str],
    model: str,
    max_tokens: int,
    rate_limiter: RateLimiter,
    batch_size: int = 50,
    usage: Optional["MultiModelUsage"] = None,
    *,
    reject_truncated: bool = False,
) -> List[Optional[str]]:
    """Call the judge model with multiple prompts concurrently.

    ``usage``: optional :class:`assistant_axis.judge_pricing.MultiModelUsage`
    accumulator, passed to every :func:`call_judge_single` (AGENT_NOTES
    "Token usage logging is mandatory on batched LLM call sites").

    A failed call gives None in its place (a content-flagged prompt too),
    except a :class:`JudgeRequestError` (any other HTTP 400), which is raised
    once its chunk has finished.
    """
    results = []

    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i + batch_size]

        tasks = [
            call_judge_single(client, prompt, model, max_tokens, rate_limiter, usage=usage,
                              reject_truncated=reject_truncated)
            for prompt in batch
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        bad_request = next((r for r in batch_results if isinstance(r, JudgeRequestError)), None)
        if bad_request is not None:
            raise bad_request

        processed = []
        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Exception in batch: {result}")
                processed.append(None)
            else:
                processed.append(result)

        results.extend(processed)

    return results


async def score_responses(
    responses: List[Dict[str, str]],
    eval_prompt_template: str,
    judge_model: str = "gpt-4.1-mini",
    # 200, as pipeline/3_judge.py: the reasoning-first rubrics need room for
    # 2-3 sentences and the SCORE line (10 truncated every reply, and the
    # parser's fallback then read a digit out of the cut-off reasoning).
    max_tokens: int = 200,
    requests_per_second: int = 100,
    batch_size: int = 50,
) -> List[Optional[int]]:
    """
    Score a list of responses using an LLM judge.

    Args:
        responses: List of dicts with 'question' and 'response' keys
        eval_prompt_template: Template string with {question} and {answer} placeholders
        judge_model: OpenAI model to use as judge
        max_tokens: Max tokens for judge response
        requests_per_second: Rate limit for API calls
        batch_size: Concurrent batch size

    Returns:
        List of scores (0-3) or None for failed parsing
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY not found in environment variables")

    # Build prompts
    prompts = []
    for resp in responses:
        prompt = eval_prompt_template.format(
            question=resp["question"],
            answer=resp["response"]
        )
        prompts.append(prompt)

    # Initialize client and rate limiter
    client = openai.AsyncOpenAI()
    rate_limiter = RateLimiter(requests_per_second)

    # Call judge
    judge_responses = await call_judge_batch(
        client=client,
        prompts=prompts,
        model=judge_model,
        max_tokens=max_tokens,
        rate_limiter=rate_limiter,
        batch_size=batch_size
    )

    # Parse scores
    scores = []
    for response_text in judge_responses:
        score = parse_judge_score(response_text) if response_text else None
        scores.append(score)

    return scores


def score_responses_sync(
    responses: List[Dict[str, str]],
    eval_prompt_template: str,
    judge_model: str = "gpt-4.1-mini",
    max_tokens: int = 200,
    requests_per_second: int = 100,
    batch_size: int = 50,
) -> List[Optional[int]]:
    """
    Synchronous wrapper for score_responses.

    Args:
        responses: List of dicts with 'question' and 'response' keys
        eval_prompt_template: Template string with {question} and {answer} placeholders
        judge_model: OpenAI model to use as judge
        max_tokens: Max tokens for judge response
        requests_per_second: Rate limit for API calls
        batch_size: Concurrent batch size

    Returns:
        List of scores (0-3) or None for failed parsing
    """
    return asyncio.run(score_responses(
        responses=responses,
        eval_prompt_template=eval_prompt_template,
        judge_model=judge_model,
        max_tokens=max_tokens,
        requests_per_second=requests_per_second,
        batch_size=batch_size
    ))


# ---------------------------------------------------------------------------
# Anthropic equivalent of call_judge_single
# ---------------------------------------------------------------------------
#
# Steering judges (Phase 2) use the bidirectional GPT+Haiku effect
# ensemble, so judge.py needs an Anthropic single-call helper.  Kept
# minimal to mirror call_judge_single() shape; structured output is
# delivered via prompt instruction + JSON parsing rather than
# response_format (Anthropic supports a tools-based json mode but the
# prompt-instruction approach is simpler and works across both providers
# uniformly).

async def call_anthropic_judge_single(
    client: "anthropic.AsyncAnthropic",
    prompt: str,
    model: str,
    max_tokens: int,
    rate_limiter: RateLimiter,
    temperature: Optional[float] = DEFAULT_TEMPERATURE,
    usage: Optional["MultiModelUsage"] = None,
) -> Optional[str]:
    """Call an Anthropic judge model with a single prompt.

    Returns the response text, or None on error.  Errors are logged at
    ERROR level and swallowed so a single bad call doesn't take down a
    whole batch of judging, except an HTTP 400, raised as
    :class:`JudgeRequestError` because every call would fail alike (a 400
    that flags this prompt's content, :func:`content_flag`, gives None).

    Args:
        temperature: sent only when it is not the default; a model that
            refuses one (:data:`MODEL_CAPABILITIES`) raises
            :class:`JudgeRequestError` for any other value, before sending.
        usage: Optional :class:`assistant_axis.judge_pricing.MultiModelUsage`
            accumulator.  Same semantics as :func:`call_judge_single`.
    """
    params: Dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    t = request_temperature(model, temperature)
    if t is not None:
        params["temperature"] = t
    await rate_limiter.acquire()

    try:
        response = await client.messages.create(**params)
        if usage is not None:
            from .judge_pricing import extract_usage_anthropic
            pt, ct = extract_usage_anthropic(response)
            usage.charge(model, pt, ct)
        if response.content and response.content[0].text:
            return response.content[0].text
        return None
    except Exception as e:  # noqa: BLE001 - we deliberately catch everything
        if _is_bad_request(e):
            flag = content_flag(e)
            if flag is None:
                raise _bad_request_error(model, e) from e
            _note_content_flag(model, flag, e)
            return None
        logger.error(f"Error calling Anthropic judge model {model}: {e}")
        return None


async def call_judge_single_unified(
    *,
    prompt: str,
    model: str,
    max_tokens: int,
    rate_limiter: RateLimiter,
    openai_client: Optional["openai.AsyncOpenAI"] = None,
    anthropic_client: Optional["anthropic.AsyncAnthropic"] = None,
    temperature: Optional[float] = DEFAULT_TEMPERATURE,
    usage: Optional["MultiModelUsage"] = None,
) -> Optional[str]:
    """Provider-agnostic single judge call.

    Routes by ``model`` prefix (see :func:`provider_for_model`).  Caller is
    responsible for instantiating the relevant client(s) and rate
    limiter(s); this is a thin dispatch helper, not a connection pool.

    For mixed-provider workloads, the caller typically constructs one
    ``AsyncOpenAI`` and one ``AsyncAnthropic`` and passes both -- the
    routing picks whichever is needed per call.

    Args:
        temperature: for either provider, sent only when it is not the
            default (:func:`request_temperature`; until 2026-10-12 the
            OpenAI path ignored it and always sent 1).
        usage: Optional :class:`assistant_axis.judge_pricing.MultiModelUsage`
            accumulator -- ticks ``usage[model]`` with the per-call
            token counts.  Pass one on every batched/automated call site.

    Raises :class:`JudgeRequestError` on an HTTP 400 from either provider,
    other than one that flags this prompt's content (None, with a WARNING).
    """
    provider = provider_for_model(model)
    if provider == "openai":
        if openai_client is None:
            raise ValueError(
                f"openai_client required for model {model}"
            )
        return await call_judge_single(
            client=openai_client,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            rate_limiter=rate_limiter,
            usage=usage,
            temperature=temperature,
        )
    if provider == "anthropic":
        if anthropic_client is None:
            raise ValueError(
                f"anthropic_client required for model {model}"
            )
        return await call_anthropic_judge_single(
            client=anthropic_client,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            rate_limiter=rate_limiter,
            temperature=temperature,
            usage=usage,
        )
    raise ValueError(f"unknown provider for model {model!r}")
