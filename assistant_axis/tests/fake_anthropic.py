"""A fake ``anthropic.AsyncAnthropic`` for platform tests (no network)."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Callable, Optional


def make_response(text: str, *, input_tokens: int = 1000, output_tokens: int = 200,
                  cache_creation: int = 0, cache_read: int = 0, stop_reason: str = "end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens,
                              cache_creation_input_tokens=cache_creation,
                              cache_read_input_tokens=cache_read))


class FakeMessages:
    def __init__(self, responder: Callable[[dict], object], delay: float = 0.0):
        self.responder = responder
        self.delay = delay
        self.calls: list[dict] = []

    async def create(self, **kw):
        self.calls.append(kw)
        if self.delay:
            # suspend like network I/O so concurrent calls interleave
            import asyncio
            await asyncio.sleep(self.delay)
        out = self.responder(kw)
        if isinstance(out, BaseException):
            raise out
        if isinstance(out, str):
            return make_response(out)
        return out


class FakeAsyncAnthropic:
    """``responder(kwargs) -> str | response | Exception``; ``delay`` seconds
    of ``asyncio.sleep`` per call make concurrent calls overlap."""

    def __init__(self, responder: Callable[[dict], object], delay: float = 0.0):
        self.messages = FakeMessages(responder, delay)

    @property
    def calls(self):
        return self.messages.calls


def user_text(kw: dict) -> str:
    return kw["messages"][0]["content"]


def system_text(kw: dict) -> str:
    s = kw["system"]
    return s if isinstance(s, str) else "".join(b["text"] for b in s)
