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

The 1-hour cache (``cache_ttl="1h"``, M3's batch waves, 2026-10-07): its writes
are billed at 2x input.  When the response breaks the writes down by lifetime
(``usage.cache_creation.ephemeral_1h_input_tokens``), the 1-hour part is
charged at :data:`CACHE_WRITE_1H_FACTOR` and the rest at 1.25x; a response
without the breakdown is charged as before.  Reads are charged at 0.1x for
every model (Opus 5.5 reads at 0.05x, so its reads are slightly overcharged).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Sequence

from assistant_axis.judge_pricing import MultiModelUsage

logger = logging.getLogger(__name__)

RETRY_DELAYS_S: tuple[float, ...] = (5, 20, 60, 180)
CACHE_WRITE_FACTOR = 1.25
CACHE_WRITE_1H_FACTOR = 2.0
CACHE_READ_FACTOR = 0.10
#: The cache lifetimes ``request_params`` accepts (``None`` is the default 5 minutes).
CACHE_TTLS: tuple[Optional[str], ...] = (None, "5m", "1h")


def _one_hour_writes(u: Any) -> int:
    """Cache-write tokens the response reports for the 1-hour lifetime (0 when it gives no breakdown)."""
    cc = getattr(u, "cache_creation", None)
    if cc is None:
        return 0
    v = cc.get("ephemeral_1h_input_tokens") if isinstance(cc, dict) else getattr(cc, "ephemeral_1h_input_tokens", 0)
    return int(v or 0)


def billed_usage(resp: Any) -> tuple[int, int, dict]:
    """``(prompt_equiv_tokens, completion_tokens, raw)`` from a response.  ``raw`` gains
    ``cache_creation_1h_input_tokens`` only when the response reports 1-hour writes."""
    u = getattr(resp, "usage", None)
    if u is None:
        return 0, 0, {}
    inp = int(getattr(u, "input_tokens", 0) or 0)
    cw = int(getattr(u, "cache_creation_input_tokens", 0) or 0)
    cr = int(getattr(u, "cache_read_input_tokens", 0) or 0)
    out = int(getattr(u, "output_tokens", 0) or 0)
    cw1h = min(_one_hour_writes(u), cw)
    prompt = inp + int(round(CACHE_WRITE_FACTOR * (cw - cw1h) + CACHE_WRITE_1H_FACTOR * cw1h + CACHE_READ_FACTOR * cr))
    raw = {"input_tokens": inp, "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr, "output_tokens": out}
    if cw1h:
        raw["cache_creation_1h_input_tokens"] = cw1h
    return prompt, out, raw


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
#: the rest from the API reference: Sonnet 5, Opus 4.7 and later, Fable, Mythos;
#: Haiku 5, from the Haiku 5.5 model page of 2026-10-07: a non-default temperature,
#: top_p or top_k returns a 400, and it thinks adaptively, so it is also a "thinking"
#: model to ``split_runner._max_tokens``).  Haiku 4.5 ("haiku-4-5") still takes 0.
NO_TEMPERATURE_FRAGMENTS: tuple[str, ...] = ("sonnet-5", "opus-5", "opus-4-7", "opus-4-8", "fable", "mythos",
                                             "haiku-5")


def accepts_temperature(model: str) -> bool:
    """False for a model that refuses ``temperature`` (the request must leave it out)."""
    m = str(model).lower()
    return not any(f in m for f in NO_TEMPERATURE_FRAGMENTS)


def request_params(*, model: str, system: Optional[str], user: str, max_tokens: int,
                   temperature: Optional[float], cache_system: bool = True,
                   cache_ttl: Optional[str] = None) -> dict:
    """The Messages API parameters for one call, shared by the live path and the Message Batches
    path so both send the same request.  ``temperature`` is left out when it is ``None`` or the
    model refuses it (:func:`accepts_temperature`); no ``thinking`` or effort setting is ever sent.
    An empty or ``None`` system prompt is omitted.  ``cache_ttl`` ("1h" or "5m", with
    ``cache_system``) sets the cache lifetime of the system block; ``None`` leaves the default
    (5 minutes) and sends no ``ttl`` key, as every request before 2026-10-07 was sent."""
    if cache_ttl not in CACHE_TTLS:
        raise ValueError(f"cache_ttl must be one of {CACHE_TTLS}, not {cache_ttl!r}")
    params: dict = {"model": model, "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": user}]}
    if temperature is not None and accepts_temperature(model):
        params["temperature"] = temperature
    if system:
        sys_block: list[dict] = [{"type": "text", "text": system}]
        if cache_system:
            sys_block[0]["cache_control"] = {"type": "ephemeral"}
            if cache_ttl:
                sys_block[0]["cache_control"]["ttl"] = cache_ttl
        params["system"] = sys_block
    return params


async def call_anthropic_json(client, *, system: Optional[str], user: str, model: str, max_tokens: int,
                              temperature: Optional[float], usage: Optional[MultiModelUsage], limiter=None,
                              cache_system: bool = True,
                              retry_delays: Sequence[float] = RETRY_DELAYS_S,
                              meta: Optional[dict] = None, cache_ttl: Optional[str] = None) -> Optional[str]:
    """Send one request; return its text or ``None`` after the last failure.

    ``temperature`` is optional and is left out of the request for a model
    that refuses it (:func:`accepts_temperature`).  ``cache_ttl``: see
    :func:`request_params`.

    ``meta`` (optional dict) receives ``stop_reason``, ``usage_raw``,
    ``attempts``, ``error`` and ``text`` for the caller's response log; it is
    filled *before* the usage is charged.  ``BudgetExceededError`` raised by a
    guarded ``usage`` propagates, with the response already in ``meta``.
    """
    params = request_params(model=model, system=system, user=user, max_tokens=max_tokens,
                            temperature=temperature, cache_system=cache_system, cache_ttl=cache_ttl)
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
