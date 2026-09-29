"""One Anthropic call with a cached system prompt, retries and usage charging.

``call_anthropic_json`` is the sibling of ``judge.call_anthropic_judge_single``
that the platform needs: it takes a ``system`` block (marked
``cache_control: ephemeral`` when ``cache_system``), retries transient errors
with the project back-off ``(5, 20, 60, 180)`` seconds, and charges **every
response received** to ``usage``, including ones the caller later fails to
parse.  It returns the response text, or ``None`` when every attempt failed
(the caller counts it as unparseable).

Token accounting: the Messages API reports uncached input
(``input_tokens``), cache writes (``cache_creation_input_tokens``, billed at
1.25x input) and cache reads (``cache_read_input_tokens``, 0.1x).  The call
is charged as ``prompt_tokens = input + round(1.25 x writes + 0.1 x reads)``,
i.e. input-token *equivalents at the uncached rate*, so ``usage.json`` costs
are correct whether or not the cache hits.  (Haiku 4.5 caches only prompts of
4,096 tokens or more, so the M1 rubric, about 2k tokens, is not cached on
Haiku; the marker is harmless.)
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Sequence

from assistant_axis.judge_pricing import MultiModelUsage

logger = logging.getLogger(__name__)

RETRY_DELAYS_S: tuple[float, ...] = (5, 20, 60, 180)
CACHE_WRITE_FACTOR = 1.25
CACHE_READ_FACTOR = 0.10


def billed_usage(resp: Any) -> tuple[int, int, dict]:
    """``(prompt_equiv_tokens, completion_tokens, raw)`` from a response."""
    u = getattr(resp, "usage", None)
    if u is None:
        return 0, 0, {}
    inp = int(getattr(u, "input_tokens", 0) or 0)
    cw = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
    cr = int(getattr(u, "cache_read_input_tokens", 0) or 0)
    out = int(getattr(u, "output_tokens", 0) or 0)
    prompt = inp + int(round(CACHE_WRITE_FACTOR * cw + CACHE_READ_FACTOR * cr))
    return prompt, out, {"input_tokens": inp, "cache_creation_input_tokens": cw,
                         "cache_read_input_tokens": cr, "output_tokens": out}


def _is_transient(exc: BaseException) -> bool:
    try:
        import anthropic
    except ImportError:  # pragma: no cover
        return False
    if isinstance(exc, (anthropic.RateLimitError, anthropic.APIConnectionError,
                        anthropic.APITimeoutError, anthropic.InternalServerError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return getattr(exc, "status_code", 0) in (408, 409, 429, 529) or getattr(exc, "status_code", 0) >= 500
    return isinstance(exc, (asyncio.TimeoutError, ConnectionError))


def response_text(resp: Any) -> str:
    parts = []
    for block in getattr(resp, "content", None) or []:
        if getattr(block, "type", "text") == "text":
            parts.append(getattr(block, "text", "") or "")
    return "".join(parts)


#: Model-id fragments of models that refuse a ``temperature`` setting with a 400
#: (checked 2026-09-29 for claude-sonnet-5-5, probe_sonnet55_api/results.jsonl;
#: the rest from the API reference: Sonnet 5, Opus 4.7 and later, Fable, Mythos).
NO_TEMPERATURE_FRAGMENTS: tuple[str, ...] = ("sonnet-5", "opus-5", "opus-4-7", "opus-4-8", "fable", "mythos")


def accepts_temperature(model: str) -> bool:
    """False for a model that refuses ``temperature`` (the request must leave it out)."""
    m = str(model).lower()
    return not any(f in m for f in NO_TEMPERATURE_FRAGMENTS)


def request_params(*, model: str, system: Optional[str], user: str, max_tokens: int,
                   temperature: Optional[float], cache_system: bool = True) -> dict:
    """The Messages API parameters for one call, shared by the live path and the Message Batches
    path so both send the same request.  ``temperature`` is left out when it is ``None`` or the
    model refuses it (:func:`accepts_temperature`); no ``thinking`` or effort setting is ever sent.
    An empty or ``None`` system prompt is omitted."""
    params: dict = {"model": model, "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": user}]}
    if temperature is not None and accepts_temperature(model):
        params["temperature"] = temperature
    if system:
        sys_block: list[dict] = [{"type": "text", "text": system}]
        if cache_system:
            sys_block[0]["cache_control"] = {"type": "ephemeral"}
        params["system"] = sys_block
    return params


async def call_anthropic_json(client, *, system: Optional[str], user: str, model: str, max_tokens: int,
                              temperature: Optional[float], usage: Optional[MultiModelUsage], limiter=None,
                              cache_system: bool = True,
                              retry_delays: Sequence[float] = RETRY_DELAYS_S,
                              meta: Optional[dict] = None) -> Optional[str]:
    """Send one request; return its text or ``None`` after the last failure.

    ``temperature`` is optional and is left out of the request for a model
    that refuses it (:func:`accepts_temperature`).

    ``meta`` (optional dict) receives ``stop_reason``, ``usage_raw``,
    ``attempts``, ``error`` and ``text`` for the caller's response log; it is
    filled *before* the usage is charged.  ``BudgetExceededError`` raised by a
    guarded ``usage`` propagates, with the response already in ``meta``.
    """
    params = request_params(model=model, system=system, user=user, max_tokens=max_tokens,
                            temperature=temperature, cache_system=cache_system)
    attempts = len(retry_delays) + 1
    last_err: Optional[str] = None
    for attempt in range(attempts):
        if limiter is not None:
            await limiter.acquire()
        try:
            resp = await client.messages.create(**params)
        except Exception as exc:  # noqa: BLE001 - classified below
            last_err = f"{type(exc).__name__}: {exc}"
            if _is_transient(exc) and attempt < attempts - 1:
                delay = retry_delays[attempt]
                logger.warning("transient error from %s (attempt %d/%d): %s; retrying in %ss", model,
                               attempt + 1, attempts, last_err, delay)
                await asyncio.sleep(delay)
                continue
            logger.error("API call to %s failed: %s", model, last_err)
            break
        prompt, out, raw = billed_usage(resp)
        text = response_text(resp)
        # Record the response before charging: a guarded usage may raise
        # BudgetExceededError here, and the caller must still be able to keep
        # the response it paid for (meta["text"]).
        if meta is not None:
            meta.update({"stop_reason": getattr(resp, "stop_reason", None), "usage_raw": raw,
                         "attempts": attempt + 1, "error": None, "text": text})
        if usage is not None:
            usage.charge(model, prompt, out)
        return text
    if meta is not None:
        meta.update({"stop_reason": None, "usage_raw": {}, "attempts": attempt + 1, "error": last_err})
    return None
