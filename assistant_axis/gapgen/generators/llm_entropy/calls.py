"""The generator's own calls, live or through the Message Batches API (plan sections 5-6, ``calls.py``).

:class:`EntropyCall` is one request: family, prompt id, run (1-based), stage (1, or 2 for (d)'s follow-up), model,
system and user turns, ``max_tokens``, no temperature (Haiku 5.5 and Sonnet 5.5 refuse one; ``llm.request_params``
leaves it out), the system block cached.  Its ``custom_id`` is at most 64 characters of ``[A-Za-z0-9_-]`` and differs
across runs, stages, models, steps and attempts; its ``cache_key`` (step, family, prompt id, run, stage, model,
prompt sha256, user sha256, and for a back-translation the answer it translates) is what a resume matches.

:class:`EntropyRunner` (frozen interface: another generator may reuse it for its own calls) sends a wave through a
transport (:class:`LiveTransport`, asyncio at :data:`CONCURRENCY`; or ``batches.BatchTransport``, whose state goes
to the run's ``batches.json``, so that a killed process collects what it paid for):

* **every response is recorded**: appended to ``responses.jsonl`` as it arrives, whatever its parse, unparseable
  and ``max_tokens``-stopped ones and refusals too, with its billed usage (``usage_raw``, ``charged_as``), and it is
  charged to the run's guarded usage by the transport (live: ``llm.call_anthropic_json``; batches: at half rate
  under ``<model>:batch``).  The parse runs on the text in memory and cannot stop the record being written;
* a reply that does not parse, stopped other than ``end_turn`` (``max_tokens``; ``refusal``, which Sonnet 5.5 gives
  a prompt it reads as reasoning extraction) or got no response is a failed call, counted, and **asked once more**
  at :data:`RETRY_MAX_TOKENS`;
* **resume** reuses every recorded answer that parsed, by ``cache_key``: an answered call is not sent again, a
  changed prompt is;
* a **budget stop** (``BudgetExceededError`` from the guarded usage, or the Batches transport refusing a wave over
  the cap) keeps the answer that crossed the cap, sends nothing more and is raised from :meth:`EntropyRunner.run`
  once the answers in hand are recorded.

**Family (b)** (section 5a): a call carries a ``redactor`` (a closure over its seed, in memory) and a
``record_user`` (the user turn with the person line replaced by ``Person: <b:r0137>.``).  The record's ``text`` is
the redacted answer and its ``items`` the parsed items with the same redaction applied to glosses and antonyms; an
item whose label carries a real seed's name token is dropped and counted (``n_dropped_name_label``).  The real text
never reaches the file.  :func:`cancel_open_batches` (``generate --family b --cancel-open``) cancels the (b) batches a
crashed process left open and records each of their results as a usage-only stub (no text: the seeds died with the
process).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

from assistant_axis.gapgen import records as RF
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.llm import billed_usage, call_anthropic_json
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM
from assistant_axis.gapgen.registry import utc_now
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage, UsageTotals, cost_for_usage

from . import SCHEMA_VERSION

HAIKU = "claude-haiku-5-5"
SONNET = "claude-sonnet-5-5"
MODELS: tuple[str, ...] = (HAIKU, SONNET)
#: Short tags for ``custom_id`` and ``source_ref`` (a model this table does not name gets a sanitised tag).
MODEL_TAGS: dict[str, str] = {HAIKU: "h55", SONNET: "s55"}
#: Plan section 7: 12,000 a generating call; a reply stopped at ``max_tokens`` or unparseable is asked once more at
#: 16,000 (both thinking models; the thinking counts against ``max_tokens``).
MAX_TOKENS = 12_000
RETRY_MAX_TOKENS = 16_000
CONCURRENCY = 6
CHARS_PER_TOKEN = 3.6
#: Output tokens a call is estimated at, by step, until the pilot measures them (plan section 7: 2,500 for a
#: generating call on a thinking model; the back-translation call about 1,500; a translation of the master with its
#: 30 domains about 4,000; its literal check about 3,000).
EST_OUT_TOKENS: dict[str, int] = {"generate": 2500, "verbalized": 2500, "backtranslate": 1500, "translate": 4000,
                                  "prompt_back": 3000}
OK_STOP_REASONS: tuple = ("end_turn", None)
STEPS: tuple[str, ...] = ("generate", "verbalized", "backtranslate", "translate", "prompt_back")
#: How often, at most, the runner calls its checkpoint (``RunContext.finish``) while answers arrive (seconds).
CHECKPOINT_INTERVAL_S = 30.0

logger = logging.getLogger(__name__)
_CID_RE = re.compile(r"[^A-Za-z0-9_]")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def model_tag(model: str) -> str:
    return MODEL_TAGS.get(model) or _CID_RE.sub("", model.replace("claude-", ""))[:8]


@dataclass
class EntropyCall:
    """One request (module docstring)."""
    family: str
    prompt_id: str
    run: int
    model: str
    system: str = field(repr=False)
    user: str = field(repr=False)              # family b: holds a person's name; never in a repr or a log
    max_tokens: int = MAX_TOKENS
    temperature: Optional[float] = None
    cache_system: bool = True
    cache_ttl: Optional[str] = None
    stage: int = 1
    step: str = "generate"
    language: str = "en"
    attempt: int = 1
    #: public facts recorded with the answer (domain, mode, constraint, seed kind and era, rubric, the language
    #: prompt's sha256, the source call of a back-translation ...); never a person's name or description
    meta: dict = field(default_factory=dict)
    #: the user turn as recorded (family b: the person line replaced by the opaque id); None: ``user`` itself
    record_user: Optional[str] = field(default=None, repr=False)
    #: family b: text -> redacted text, a closure over the seed (in memory only)
    redactor: Optional[Callable[[Optional[str]], Optional[str]]] = field(default=None, repr=False)
    #: family b: label -> True when it carries a real seed's name token (the item is dropped)
    name_label: Optional[Callable[[Optional[str]], bool]] = field(default=None, repr=False)
    #: family b: text -> what of the seed it still carries (``seeds.leaks``), the runner's last-resort guard
    leak_check: Optional[Callable[[str], list]] = field(default=None, repr=False)
    #: family b: True for a fictional seed, whose eponym labels are kept (the guard reads past them)
    labels_may_name: bool = False

    @property
    def system_sha256(self) -> str:
        return sha256(self.system)

    @property
    def user_sha256(self) -> str:
        return sha256(self.user)

    @property
    def prompt_sha256(self) -> str:
        """The sha256 of the system and user turns together (of the real text, also for family b: not
        reversible)."""
        return sha256(json.dumps([self.system, self.user], ensure_ascii=False))

    @property
    def custom_id(self) -> str:
        """``<family>-<prompt>-r<run>-s<stage>[-x<attempt>]-<model tag>-<hash>``, at most 64 characters."""
        seed = "|".join([self.step, self.family, self.prompt_id, str(self.run), str(self.stage), str(self.attempt),
                         self.model, self.system_sha256, self.user, str(self.meta.get("source_custom_id") or "")])
        h = sha256(seed)[:12]
        tail = f"-r{self.run}-s{self.stage}" + (f"-x{self.attempt}" if self.attempt > 1 else "") + \
            f"-{model_tag(self.model)}" + ("" if self.step in ("generate", "verbalized") else f"-{self.step[:2]}") + \
            f"-{h}"
        slug = _CID_RE.sub("_", self.prompt_id.split(":", 1)[-1] if ":" in self.prompt_id else self.prompt_id)
        room = 64 - len(self.family) - 1 - len(tail)
        return f"{self.family}-{slug[:max(1, room)]}{tail}"[:64]

    @property
    def cache_key(self) -> tuple:
        """What a resume matches: step, family, prompt id, run, stage, model, the prompt's and the user turn's
        sha256, and (a back-translation) the answer it translates."""
        return (self.step, self.family, self.prompt_id, int(self.run), int(self.stage), self.model,
                self.prompt_sha256, self.user_sha256, str(self.meta.get("source_custom_id") or ""))

    def retried(self) -> "EntropyCall":
        """The once-more request: the same prompt at :data:`RETRY_MAX_TOKENS`, attempt 2."""
        return EntropyCall(**{**self.__dict__, "attempt": self.attempt + 1,
                              "max_tokens": max(self.max_tokens, RETRY_MAX_TOKENS)})


def record_cache_key(rec: Mapping) -> tuple:
    return (rec.get("step") or "generate", rec.get("family"), rec.get("prompt_id"), int(rec.get("run") or 1),
            int(rec.get("stage") or 1), rec.get("model"), rec.get("prompt_sha256"), rec.get("user_sha256"),
            str((rec.get("meta") or {}).get("source_custom_id") or ""))


def call_tokens(c: EntropyCall) -> tuple[int, int]:
    """Estimated ``(input, output)`` tokens of one call."""
    return int((len(c.system) + len(c.user)) / CHARS_PER_TOKEN), EST_OUT_TOKENS.get(c.step, 2500)


def estimate_usd(calls: Sequence[EntropyCall], *, batch: bool = False) -> float:
    suffix = BATCH_SUFFIX if batch else ""
    return sum(cost_for_usage(c.model + suffix, *call_tokens(c)) for c in calls)


def estimate_lines(calls: Sequence[EntropyCall], *, batch: bool) -> list[str]:
    """``n_calls x (in, out) tokens at model rates = $X`` per (step, model) (plan section 7)."""
    groups: dict[tuple, list] = {}
    for c in calls:
        groups.setdefault((c.step, c.model), []).append(c)
    out = []
    for (step, model), cs in sorted(groups.items()):
        toks = [call_tokens(c) for c in cs]
        i, o = sum(t[0] for t in toks) // len(cs), sum(t[1] for t in toks) // len(cs)
        out.append(f"{step}: {len(cs)} calls x ({i:,}, {o:,}) tokens at {model}{BATCH_SUFFIX if batch else ''} "
                   f"rates = ${estimate_usd(cs, batch=batch):.4f}")
    return out


def stop_problem(stop_reason: Any, text: Optional[str], stop_details: Optional[Mapping] = None) -> Optional[str]:
    """Why a response with text is a failed call (a stop other than ``end_turn``), or None."""
    if text is None or stop_reason in OK_STOP_REASONS:
        return None
    cat = (stop_details or {}).get("category") if isinstance(stop_details, Mapping) else None
    return f"stop_reason {stop_reason}" + (f" ({cat})" if cat else "")


# --------------------------------------------------------------------------- the run's usage

@dataclass
class RunGuardedUsage(GuardedUsage):
    """A session's guarded usage whose file is the run's whole ``usage.json``: ``earlier`` (the run's other
    sessions) plus this session.  The cap (``budget_usd``) applies to this session's spend; the throttled writes, a
    budget stop and a SIGTERM write the same total as ``RunContext.finish`` (the sum of the sessions), so a process
    killed between checkpoints leaves a file at most ``write_interval_s`` old (minor 8 of the review, 2026-10-17)."""
    earlier: Optional[MultiModelUsage] = None

    def write_json(self, path) -> None:
        from assistant_axis.atomic_io import atomic_write_text
        total = MultiModelUsage.from_dict(self.as_dict())
        if self.earlier is not None:
            total.merge_from(self.earlier)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps(total.as_dict(), indent=2, sort_keys=True), p)
        if self.usage_path is not None and p == Path(self.usage_path):
            self._last_write = time.monotonic()


def usage_gap(rebuilt: MultiModelUsage, recorded: MultiModelUsage) -> MultiModelUsage:
    """What ``rebuilt`` (the spend the response records show) holds beyond ``recorded`` (the run's sessions), per
    model: the spend of a session killed before it recorded its usage."""
    out = MultiModelUsage()
    for m, r in rebuilt.per_model.items():
        e = recorded.per_model.get(m) or UsageTotals(model=m)
        dp, dc, dn = r.prompt_tokens - e.prompt_tokens, r.completion_tokens - e.completion_tokens, r.n_calls - e.n_calls
        if dp > 0 or dc > 0 or dn > 0:
            out.per_model[m] = UsageTotals(model=m, prompt_tokens=max(0, dp), completion_tokens=max(0, dc),
                                           cost_usd=max(0.0, r.cost_usd - e.cost_usd), n_calls=max(0, dn))
    return out


# --------------------------------------------------------------------------- family b's log lines

#: The loggers a wave of family b's calls could reach with a person's name in a message (an API error that quotes
#: the prompt, logged by ``llm.call_anthropic_json`` or the Batches transport): their records are redacted while
#: such a wave runs.
REDACTED_LOGGERS: tuple[str, ...] = ("assistant_axis.gapgen.llm", "assistant_axis.gapgen.batches", __name__)


class RedactingFilter(logging.Filter):
    """Rewrites a log record's message through every redactor of the running wave (family b)."""

    def __init__(self, redactors: Sequence[Callable[[Optional[str]], Optional[str]]]):
        super().__init__()
        self.redactors = list(redactors)

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001 - a malformed record is left as it is
            return True
        new = msg
        for r in self.redactors:
            new = r(new) or new
        if new != msg:
            record.msg, record.args = new, ()
        return True


class redacting_logs:
    """Context manager: :class:`RedactingFilter` on :data:`REDACTED_LOGGERS` for the duration (nothing when there is
    no redactor)."""

    def __init__(self, redactors):
        self.filter = RedactingFilter(redactors) if redactors else None

    def __enter__(self):
        if self.filter is not None:
            for name in REDACTED_LOGGERS:
                logging.getLogger(name).addFilter(self.filter)
        return self

    def __exit__(self, *exc):
        if self.filter is not None:
            for name in REDACTED_LOGGERS:
                logging.getLogger(name).removeFilter(self.filter)
        return False


# --------------------------------------------------------------------------- transports

class LiveTransport:
    """Sends a wave's calls through the Messages API, ``runner.concurrency`` at a time; a budget stop keeps the
    answer that crossed the cap and sends nothing more (the states pass's transport)."""
    name = "live"

    def __init__(self, runner: "EntropyRunner"):
        self.runner = runner

    async def execute(self, wave: str, calls: Sequence[EntropyCall], on_result: Callable) -> None:
        r = self.runner
        sem = asyncio.Semaphore(max(1, int(r.concurrency)))

        async def one(c: EntropyCall) -> None:
            if r._stop is not None:
                return
            async with sem:
                if r._stop is not None:
                    return
                meta: dict = {}
                try:
                    text = await call_anthropic_json(
                        r.client, system=c.system, user=c.user, model=c.model, max_tokens=c.max_tokens,
                        temperature=c.temperature, usage=r.usage, limiter=r.limiter, cache_system=c.cache_system,
                        cache_ttl=c.cache_ttl, meta=meta, **r.retry_kw)
                except BudgetExceededError as exc:
                    text = meta.get("text")
                    if r._stop is None:
                        r._stop = exc
            meta["charged_as"] = c.model if meta.get("usage_raw") else None
            on_result(c, text, meta)

        await asyncio.gather(*(one(c) for c in calls))


# --------------------------------------------------------------------------- the runner

@dataclass
class WaveResult:
    """What a wave (and its retry) gave: ``answers[cache_key] = (call, record, parsed)`` for the calls with a usable
    answer (reused ones included), ``failures[cache_key] = why`` for the rest, and the counts."""
    answers: dict = field(default_factory=dict)
    failures: dict = field(default_factory=dict)
    n_calls: int = 0              # requests whose answer came back (or failed) in this process
    n_reused: int = 0
    n_units: int = 0
    n_retried: int = 0
    stop_reasons: Counter = field(default_factory=Counter)
    stopped: Optional[BaseException] = None

    @property
    def n_ok(self) -> int:
        """Units answered by this process's own calls (the parse rate's numerator)."""
        return len(self.answers) - self.n_reused

    @property
    def n_attempted(self) -> int:
        """Units this process asked about (the parse rate's denominator)."""
        return self.n_units - self.n_reused


Parser = Callable[[EntropyCall, Optional[str]], tuple[bool, dict]]


class EntropyRunner:
    """Sends calls, records every answer, parses, retries once and resumes (module docstring).  ``usage`` is the
    run's guarded usage (its ``budget_usd`` is the cap the Batches transport checks a wave against)."""

    def __init__(self, *, client=None, batch_id: str, usage, transport: Any = None,
                 responses_path: Optional[Path] = None, resume_records: Sequence[Mapping] = (),
                 run_id: Optional[str] = None, concurrency: int = CONCURRENCY, limiter=None,
                 retry_delays: Optional[Sequence[float]] = None, checkpoint: Optional[Callable[[], Any]] = None,
                 checkpoint_interval_s: float = CHECKPOINT_INTERVAL_S, label_form: str = DEFAULT_LABEL_FORM,
                 prompts_version: Optional[int] = None, now: Callable[[], str] = utc_now):
        self.client = client
        self.batch_id = batch_id
        self.run_id = run_id
        self.usage = usage
        self.transport = transport if transport is not None else LiveTransport(self)
        self.responses_path = Path(responses_path) if responses_path is not None else None
        self.concurrency = concurrency
        self.limiter = limiter
        self.retry_kw = {} if retry_delays is None else {"retry_delays": tuple(retry_delays)}
        self.checkpoint = checkpoint
        self.checkpoint_interval_s = checkpoint_interval_s
        self._last_checkpoint = float("-inf")
        self.label_form = label_form
        self.prompts_version = prompts_version
        self.now = now
        self.records: list[dict] = []
        self._stop: Optional[BaseException] = None
        self._answered: dict[tuple, dict] = {}
        for rec in resume_records:
            if rec.get("ok"):
                self._answered[record_cache_key(rec)] = dict(rec)

    # -- money --------------------------------------------------------------------
    def estimate_usd(self, calls: Sequence[EntropyCall], *, batch: bool = False) -> float:
        return estimate_usd(calls, batch=batch)

    # -- records ------------------------------------------------------------------
    def _append(self, rec: dict) -> None:
        self.records.append(rec)
        if self.responses_path is not None:
            self.responses_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.responses_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
        if self.checkpoint is not None and time.monotonic() - self._last_checkpoint >= self.checkpoint_interval_s:
            self._last_checkpoint = time.monotonic()
            try:
                self.checkpoint()
            except Exception as exc:  # noqa: BLE001 - a checkpoint must never stop the recording
                logger.warning("checkpoint failed: %s", type(exc).__name__)

    def _copy_reused(self, rec: Mapping) -> dict:
        """An answer reused from another run (``--reuse-run``), appended to this run's record so that the run is
        self-contained: marked ``reused_from``, its usage left out (it was charged to the run that paid for it)."""
        cp = dict(rec)
        cp.update(reused_from=rec.get("run_id"), run_id=self.run_id, batch_id=self.batch_id, usage_raw=None,
                  charged_as=None, at=self.now())
        self._append(cp)
        self._answered[record_cache_key(cp)] = cp
        return cp

    def _record(self, c: EntropyCall, text: Optional[str], meta: Mapping, parsed: Mapping, ok: bool) -> dict:
        redact = c.redactor
        sd = meta.get("stop_details")
        err = meta.get("error")
        if redact is not None:              # family b: an error or a refusal's explanation could quote the prompt
            err = redact(err) if isinstance(err, str) else err
            if isinstance(sd, Mapping):
                sd = {k: redact(v) if isinstance(v, str) else v for k, v in sd.items()}
            parsed = dict(parsed)
            for k in ("failure", "parse_error"):
                if isinstance(parsed.get(k), str):
                    parsed[k] = redact(parsed[k])
        rec = {"schema_version": SCHEMA_VERSION, "batch_id": self.batch_id, "run_id": self.run_id, "step": c.step,
               "family": c.family, "prompt_id": c.prompt_id, "run": c.run, "stage": c.stage, "attempt": c.attempt,
               "model": c.model, "language": c.language, "prompt_sha256": c.prompt_sha256,
               "system_sha256": c.system_sha256, "user_sha256": c.user_sha256, "prompts_version": self.prompts_version,
               "label_form": self.label_form, "meta": dict(c.meta),
               "user": c.record_user if c.record_user is not None else c.user,
               "text": redact(text) if redact is not None else text,
               "stop_reason": meta.get("stop_reason"), "stop_details": sd,
               "usage_raw": meta.get("usage_raw"), "charged_as": meta.get("charged_as"),
               "custom_id": c.custom_id, "batch_request_id": meta.get("batch_request_id"),
               "transport": getattr(self.transport, "name", "live"), "attempts": meta.get("attempts"),
               "error": err, "max_tokens": c.max_tokens, "ok": bool(ok),
               "failure": parsed.get("failure"), "parse_error": parsed.get("parse_error"),
               "n_items": parsed.get("n_items"), "n_invalid": parsed.get("n_invalid"), "at": self.now()}
        for k in ("items", "n_dropped_name_label", "notes"):
            if k in parsed:
                rec[k] = parsed[k]
        if c.leak_check is not None:
            self._guard(c, rec)
        return rec

    @staticmethod
    def _guard(c: EntropyCall, rec: dict) -> None:
        """The last-resort guard of family b (Fable's review, 2026-10-17): the finished record, serialised (a
        fictional seed's kept labels left out, being allowed), must carry nothing of its seed; if anything does, the
        record keeps no text and no items and is a failed call (``failure: "redaction guard"``), so that no path the
        tests did not foresee can write a name."""
        view = dict(rec)
        if c.labels_may_name and isinstance(view.get("items"), list):
            view["items"] = [{k: v for k, v in it.items() if k != "label"} for it in view["items"]]
        found = c.leak_check(json.dumps(view, ensure_ascii=False))
        if found:
            rec.update(text=None, items=None, ok=False, failure="redaction guard", n_items=0,
                       guard=sorted(set(found)))
            for k in ("notes", "error", "stop_details", "parse_error"):
                rec[k] = None

    def _handle(self, c: EntropyCall, text: Optional[str], meta: Mapping, parse: Parser, res: WaveResult) -> None:
        """Parse in memory, then record whatever happened (the record is written even if the parser raises)."""
        res.n_calls += 1
        failure = stop_problem(meta.get("stop_reason"), text, meta.get("stop_details"))
        if text is None:
            err = meta.get("error")
            if c.redactor is not None and isinstance(err, str):     # family b: an API error may quote the prompt
                err = c.redactor(err)
            failure = failure or (f"no response ({err})" if err else "no response")
        parsed: dict = {}
        ok = False
        try:
            if failure is None:
                ok, parsed = parse(c, text)
                parsed = dict(parsed)
        except Exception as exc:  # noqa: BLE001 - a parser bug must not lose a paid answer
            ok, parsed = False, {"parse_error": f"parser raised {type(exc).__name__}"}
        finally:
            if failure is not None:
                parsed["failure"] = failure
            elif not ok and not parsed.get("parse_error"):
                parsed["parse_error"] = "did not parse"
            rec = self._record(c, text, meta, parsed, ok)
            self._append(rec)
        if ok and not rec.get("ok"):                 # the redaction guard turned the answer away
            ok, failure = False, rec.get("failure")
        res.stop_reasons[str(meta.get("stop_reason"))] += 1
        if ok:
            res.answers[c.cache_key] = (c, rec, parsed)
            res.failures.pop(c.cache_key, None)
        else:
            res.failures[c.cache_key] = failure or parsed.get("parse_error") or "failed"

    async def _send(self, wave: str, calls: Sequence[EntropyCall], parse: Parser, res: WaveResult) -> None:
        if not calls or self._stop is not None:
            return

        def on_result(c: EntropyCall, text: Optional[str], meta: Mapping) -> None:
            self._handle(c, text, dict(meta), parse, res)
        try:
            await self.transport.execute(wave, list(calls), on_result)
        except BaseException as exc:  # noqa: BLE001 - kept as the stop, raised by run() once the answers are in
            if self._stop is None:
                self._stop = exc

    async def wave_async(self, wave: str, calls: Sequence[EntropyCall], parse: Parser) -> WaveResult:
        """Reuse what the record answers, send the rest, ask the failures once more."""
        res = WaveResult(n_units=len(calls))
        keys = [c.cache_key for c in calls]
        if len(set(keys)) != len(keys):
            raise ValueError(f"{wave}: two calls with one cache key")
        todo = []
        for c in calls:
            rec = self._answered.get(c.cache_key)
            if rec is not None:
                if self.run_id is not None and rec.get("run_id") not in (None, self.run_id):
                    rec = self._copy_reused(rec)
                res.answers[c.cache_key] = (c, rec, {k: rec.get(k) for k in ("items", "n_items", "n_invalid")})
                res.n_reused += 1
            else:
                todo.append(c)
        with redacting_logs([c.redactor for c in todo if c.redactor is not None]):
            await self._send(wave, todo, parse, res)
            again = [c.retried() for c in todo if c.cache_key in res.failures]
            if again and self._stop is None:
                res.n_retried = len(again)
                await self._send(f"{wave}_retry", again, parse, res)
        res.stopped = self._stop
        return res

    def run(self, wave: str, calls: Sequence[EntropyCall], parse: Parser) -> WaveResult:
        """:meth:`wave_async` on a fresh event loop; a stop (a budget, a failed batch) is raised after the answers
        in hand are recorded."""
        res = asyncio.run(self.wave_async(wave, calls, parse))
        if res.stopped is not None:
            raise res.stopped
        return res


# --------------------------------------------------------------------------- parsers per step

def parse_generation(c: EntropyCall, text: Optional[str]) -> tuple[bool, dict]:
    """A generating call's reply (families a, b, c, d, e): the items, with family b's redaction and name-label drop
    applied in memory."""
    from .parse import parse_reply
    rep, err = parse_reply(text, multilingual=c.family == "c")
    if rep is None:
        return False, {"parse_error": err}
    out = {"n_items": len(rep.items), "n_invalid": rep.n_invalid, "notes": rep.notes}
    if c.redactor is not None:              # family b: the items as the record may hold them
        items, dropped = [], 0
        for it in rep.items:
            if c.name_label is not None and c.name_label(it.get("label")):
                dropped += 1
                continue
            it = dict(it)
            it["gloss"] = c.redactor(it.get("gloss"))
            it["antonym"] = c.redactor(it.get("antonym"))
            it["notes"] = [c.redactor(n) for n in it.get("notes") or []]
            items.append(it)
        out.update(items=items, n_dropped_name_label=dropped)
    return True, out


def parse_backtranslation_call(c: EntropyCall, text: Optional[str]) -> tuple[bool, dict]:
    from .parse import parse_backtranslation
    bt, err = parse_backtranslation(text, int(c.meta.get("n_items") or 0))
    if bt is None:
        return False, {"parse_error": err}
    return True, {"n_items": len(bt.by_index), "n_invalid": len(bt.missing),
                  "notes": [f"{len(bt.missing)} item(s) missing"] if bt.missing else []}


#: The JSON keys and every kind value (quoted, as the master's kind paragraph quotes them) a translation must keep in
#: English, so that one parser reads every language (minor 11 of the review: every kind value, not only one).
TRANSLATION_KEEPS: tuple[str, ...] = ('"approach"', '"items"', '"label"', '"romanization"', '"english_hint"',
                                      '"gloss"', '"antonym"', '"kind"', '"ambiguity_flag"',
                                      '"trait"', '"membership"', '"state"', '"physical"', '"role"', '"action"',
                                      '"evaluative"', '"not_a_persona"')


def translation_problems(d: Mapping, domain_ids: Sequence[str]) -> list[str]:
    """Why a translation cannot be used: a key or kind value lost, the placeholder lost or repeated, a domain
    missing."""
    probs = [f"system lost {k}" for k in TRANSLATION_KEEPS if k not in str(d.get("system") or "")]
    n = str(d.get("user_template") or "").count("{domain}")
    if n != 1:
        probs.append(f"user template has {n} {{domain}} placeholders, not 1")
    missing = [x for x in domain_ids if not (d.get("domains") or {}).get(x)]
    if missing:
        probs.append(f"domains missing: {', '.join(missing[:5])}{' ...' if len(missing) > 5 else ''}")
    return probs


def parse_translation_call(c: EntropyCall, text: Optional[str]) -> tuple[bool, dict]:
    from .parse import parse_tagged
    from .prompts import DOMAIN_IDS
    d, err = parse_tagged(text)
    if d is None:
        return False, {"parse_error": err}
    probs = translation_problems(d, DOMAIN_IDS) if c.step == "translate" else \
        [f"domains missing: {x}" for x in DOMAIN_IDS if x not in (d.get("domains") or {})][:1]
    if probs:
        return False, {"parse_error": "; ".join(probs)}
    return True, {"n_items": len(d.get("domains") or {}), "n_invalid": 0, "parsed": d}


# --------------------------------------------------------------------------- building calls

def generation_calls(prompts: Sequence, *, runs: Sequence[int], model: str, system: str, rubric: Mapping,
                     step: str = "generate", max_tokens: int = MAX_TOKENS) -> list[EntropyCall]:
    """One call per (prompt, run): ``prompts`` are :class:`.prompts.Prompt`; a (c) prompt brings its own system turn
    (``meta["system"]``)."""
    out = []
    for p in prompts:
        sys_text = p.meta.get("system") or system
        meta = {k: v for k, v in p.meta.items() if k != "system"}
        meta.update(rubric=rubric.get("name"), rubric_version=rubric.get("version"), rubric_sha256=rubric.get("sha256"))
        for r in runs:
            out.append(EntropyCall(family=p.family, prompt_id=p.prompt_id, run=int(r), model=model, system=sys_text,
                                   user=p.user, stage=int(p.meta.get("stage") or 1), step=step, language=p.language,
                                   max_tokens=max_tokens, meta=dict(meta)))
    return out


def b_record_user(user: str, seed_id: str) -> str:
    """The (b) user turn as recorded: its person line replaced by ``Person: <b:r0137>.``."""
    first, sep, rest = user.partition("\n")
    return f"Person: <{seed_id}>." + sep + rest


# --------------------------------------------------------------------------- reading records

def read_responses(path: Path) -> list[dict]:
    """A run's ``responses.jsonl`` (packed or not), or []."""
    p = Path(path)
    if not RF.exists(p):
        return []
    return RF.read_jsonl(p)


def final_records(records: Sequence[Mapping], *, step: Optional[str] = None) -> dict[tuple, dict]:
    """``{cache_key: record}``: the usable answer of every unit (the last ``ok`` record of its key), optionally of
    one step."""
    out: dict[tuple, dict] = {}
    for r in records:
        if step is not None and (r.get("step") or "generate") != step:
            continue
        if r.get("ok"):
            out[record_cache_key(r)] = dict(r)
    return out


def parse_rate(records: Sequence[Mapping], *, step: Optional[str] = None) -> dict:
    """Units answered over units asked (a unit is one cache key; its retry counts once), and records parsed over
    records, with the stop reasons of the failed ones."""
    units: dict[tuple, bool] = {}
    n_rec_ok = 0
    stops: Counter = Counter()
    n = 0
    for r in records:
        if step is not None and (r.get("step") or "generate") != step:
            continue
        if r.get("text") is None and r.get("abandoned"):
            continue
        n += 1
        k = record_cache_key(r)
        units[k] = units.get(k, False) or bool(r.get("ok"))
        n_rec_ok += bool(r.get("ok"))
        if not r.get("ok"):
            stops[str(r.get("failure") or r.get("parse_error"))] += 1
    n_ok = sum(units.values())
    return {"n_units": len(units), "n_ok": n_ok, "rate": round(n_ok / len(units), 4) if units else None,
            "n_records": n, "n_records_ok": n_rec_ok, "failures": dict(sorted(stops.items()))}


# --------------------------------------------------------------------------- family b: open batches

def cancel_open_batches(state_path: Path, client, *, responses_path: Optional[Path], usage, wave_prefix: str = "b_",
                        batch_id: Optional[str] = None, run_id: Optional[str] = None, poll_seconds: float = 30.0,
                        sleep: Callable[[float], Any] = time.sleep, max_polls: int = 240) -> list[str]:
    """Cancel every (b) batch the state file records as submitted and not collected (a process that died before
    collecting it), wait for each to end, and record each of its results as a usage-only stub: the billed usage
    charged under ``<model>:batch``, ``text`` None and ``abandoned`` true (section 5a: without the seeds the answers
    cannot be redacted, so they are not kept).  A result whose ``custom_id`` the run already recorded with its usage
    (a batch collected part-way before the crash) is skipped, so that nothing is charged twice.  Returns the batch
    ids cancelled."""
    state = json.loads(Path(state_path).read_text(encoding="utf-8")) if Path(state_path).exists() else {"waves": {}}
    charged = {r.get("custom_id") for r in (read_responses(responses_path) if responses_path is not None else [])
               if r.get("usage_raw")}
    done = []
    for wave, batches in (state.get("waves") or {}).items():
        if not wave.startswith(wave_prefix):
            continue
        for b in batches:
            if b.get("status") != "submitted":
                continue
            bid = b["id"]
            try:
                client.messages.batches.cancel(bid)
            except Exception as exc:  # noqa: BLE001 - an ended batch cannot be cancelled; collect its usage anyway
                logger.warning("batch %s: cancel refused (%s); collecting its usage", bid, type(exc).__name__)
            for _ in range(max_polls):
                st = client.messages.batches.retrieve(bid)
                status = st.get("processing_status") if isinstance(st, dict) else getattr(st, "processing_status", None)
                if status == "ended":
                    break
                sleep(poll_seconds)
            for res in client.messages.batches.results(bid):
                cid = res.get("custom_id") if isinstance(res, dict) else getattr(res, "custom_id", None)
                if cid in charged:                 # recorded and charged before the crash: not charged again
                    continue
                result = res.get("result") if isinstance(res, dict) else getattr(res, "result", None)
                rtype = result.get("type") if isinstance(result, dict) else getattr(result, "type", None)
                raw, model = {}, None
                if rtype == "succeeded":
                    msg = result.get("message") if isinstance(result, dict) else getattr(result, "message", None)
                    prompt, out, raw = billed_usage(msg)
                    model = (msg.get("model") if isinstance(msg, dict) else getattr(msg, "model", None)) or HAIKU
                    usage.charge(model + BATCH_SUFFIX, prompt, out)
                stub = {"schema_version": SCHEMA_VERSION, "batch_id": batch_id, "run_id": run_id, "step": "generate",
                        "family": "b", "custom_id": cid, "batch_request_id": bid, "result_type": rtype, "text": None,
                        "abandoned": True, "ok": False, "usage_raw": raw,
                        "charged_as": (model + BATCH_SUFFIX) if model else None,
                        "failure": "abandoned: the seeds died with the process that asked (section 5a)",
                        "at": utc_now()}
                if responses_path is not None:
                    Path(responses_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(responses_path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(stub, ensure_ascii=False) + "\n")
            b["status"], b["collected_at"], b["abandoned"] = "abandoned", utc_now(), True
            done.append(bid)
    if done:
        from assistant_axis.atomic_io import atomic_write_text
        atomic_write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", Path(state_path))
    return done


def open_batches(state_path: Path, *, wave_prefix: str = "b_") -> list[str]:
    """The batch ids of ``wave_prefix`` waves still submitted and not collected."""
    p = Path(state_path)
    if not p.exists():
        return []
    state = json.loads(p.read_text(encoding="utf-8"))
    return [b["id"] for w, bs in (state.get("waves") or {}).items() if w.startswith(wave_prefix)
            for b in bs if b.get("status") == "submitted"]


__all__ = ["HAIKU", "SONNET", "MODELS", "MODEL_TAGS", "MAX_TOKENS", "RETRY_MAX_TOKENS", "CONCURRENCY",
           "EST_OUT_TOKENS", "STEPS", "sha256", "model_tag", "EntropyCall", "record_cache_key", "call_tokens",
           "estimate_usd", "estimate_lines", "stop_problem", "LiveTransport", "WaveResult", "EntropyRunner",
           "parse_generation", "parse_backtranslation_call", "TRANSLATION_KEEPS", "translation_problems",
           "parse_translation_call", "generation_calls", "b_record_user", "read_responses", "final_records",
           "parse_rate", "cancel_open_batches", "open_batches", "RunGuardedUsage", "usage_gap", "redacting_logs",
           "RedactingFilter"]
