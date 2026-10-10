"""OpenAI Batch API for chat-completion judge calls (pipeline step 3).

Pipeline step 3 (``pipeline/3_judge.py``) judges every response of an
extraction, about 600,000 calls for the October 2026 corpus.  Since
2026-10-10 it sends them through OpenAI's Batch API by default (Roger:
"make batch mode the default, with a flag to override that"), at half the
real-time price (``gpt-4.1-mini``: $0.20 / $0.80 per million tokens against
$0.40 / $1.60).  This module is the transport: it writes request lines into
chunk files, uploads and submits them, polls, and hands every result back to
the caller by ``custom_id``.

Service limits (OpenAI batch guide, read 2026-10-10): a batch holds at most
50,000 requests and 200 MB, the completion window is 24 hours, and each model
has a queue limit on the prompt tokens enqueued per organisation, shown only
on the organisation's limits page.  A batch over that limit fails validation
with the code ``token_limit_exceeded``; :meth:`OpenAIBatchRunner.run` then
waits for a batch in flight to finish and tries again, or, with none in
flight, splits the chunk in half, so the run adapts to whatever the limit is.

Restart.  The state file (``batch_state.json`` beside the scores) records
every chunk as it is submitted.  A run started again finds the batches still
in flight, excludes their requests from what it submits (:meth:`resume`), and
collects them; chunks written but never submitted are discarded and rebuilt.

Only the standard library and ``openai`` are imported, because step 3 loads
this file without the ``assistant_axis`` package (whose ``__init__`` imports
torch).
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import json
import logging
import os
from collections import deque
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple

ENDPOINT = "/v1/chat/completions"
COMPLETION_WINDOW = "24h"
MAX_BATCH_REQUESTS = 50_000
MAX_BATCH_BYTES = 200 * 1024 * 1024
# A chunk well inside both limits, and about 10 million prompt tokens of step-3
# requests (about 1,000 tokens each), so a modest queue limit takes a few at once.
DEFAULT_CHUNK_REQUESTS = 10_000
DEFAULT_CHUNK_BYTES = 100 * 1024 * 1024
# The smallest chunk the token-limit split goes down to before giving up.
MIN_SPLIT_REQUESTS = 50
TERMINAL_STATUSES = ("completed", "failed", "expired", "cancelled")
TOKEN_LIMIT_CODE = "token_limit_exceeded"

STATE_VERSION = 1


class BatchFailedError(RuntimeError):
    """A batch failed validation for a reason other than the queue limit (a
    bad model name, a malformed line): nothing is retried or sent in real
    time, because the same requests would fail the same way."""


def request_line(custom_id: str, body: Dict[str, Any]) -> str:
    """One line of a batch input file."""
    return json.dumps({"custom_id": custom_id, "method": "POST", "url": ENDPOINT,
                       "body": body}, ensure_ascii=False) + "\n"


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _error_codes(batch: Any) -> List[str]:
    errors = _get(batch, "errors")
    data = _get(errors, "data") or []
    return [str(_get(e, "code") or "") for e in data]


def _error_text(batch: Any) -> str:
    errors = _get(batch, "errors")
    data = _get(errors, "data") or []
    return "; ".join(f"{_get(e, 'code')}: {_get(e, 'message')}" for e in data[:5]) or "(no detail)"


def _content_text(content: Any) -> str:
    text = _get(content, "text")
    if callable(text):
        text = text()
    if text is None and hasattr(content, "read"):
        raw = content.read()
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    return text or ""


def _read_custom_ids(path: Path) -> List[str]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line)["custom_id"] for line in f if line.strip()]


def _read_prompts(path: Path, wanted: Set[str]) -> Dict[str, Dict[str, Any]]:
    """``custom_id -> body`` for the wanted requests of a chunk file."""
    out: Dict[str, Dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec["custom_id"] in wanted:
                out[rec["custom_id"]] = rec["body"]
    return out


class OpenAIBatchRunner:
    """Write, submit, poll and collect OpenAI batches for one output directory.

    ``on_result(custom_id, body, error)`` is called for every request a batch
    returns: ``body`` is the chat-completion response (a dict) on success,
    ``error`` a short string otherwise.  ``on_batch_done()`` is called after
    each batch's results, before the batch is marked collected, so the caller
    can make them durable first.  Requests a batch never answered (expired,
    cancelled, or an error line) come back from :meth:`run` as
    ``custom_id -> request body``, for the caller to send in real time or
    leave for a rerun.
    """

    def __init__(self, client: Any, work_dir: Path, state_path: Path, *,
                 poll_seconds: float = 60.0, validation_poll_seconds: float = 10.0,
                 metadata: Optional[Dict[str, str]] = None,
                 logger: Optional[logging.Logger] = None):
        self.client = client
        self.work_dir = Path(work_dir)
        self.state_path = Path(state_path)
        self.poll_seconds = poll_seconds
        self.validation_poll_seconds = validation_poll_seconds
        self.metadata = dict(metadata or {})
        self.log = logger or logging.getLogger(__name__)
        self.state: Dict[str, Any] = self._load_state()

    # -- state ------------------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            if state.get("version") != STATE_VERSION:
                raise RuntimeError(f"{self.state_path}: unknown state version {state.get('version')!r}")
            return state
        return {"version": STATE_VERSION, "chunks": []}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_name(f".{self.state_path.name}.tmp{os.getpid()}")
        tmp.write_text(json.dumps(self.state, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, self.state_path)

    def _record(self, path: Path) -> Dict[str, Any]:
        for rec in self.state["chunks"]:
            if rec["path"] == str(path):
                return rec
        rec = {"path": str(path)}
        self.state["chunks"].append(rec)
        return rec

    def _inflight_records(self) -> List[Dict[str, Any]]:
        return [r for r in self.state["chunks"] if r.get("batch_id") and not r.get("collected")]

    async def resume(self) -> Set[str]:
        """Prepare a restart: drop chunks never submitted, and return the
        ``custom_id`` of every request in a batch still to be collected (the
        caller must not submit those again).  A chunk file that is gone is
        read back from the batch's input file on the service."""
        keep = []
        for rec in self.state["chunks"]:
            if rec.get("batch_id"):
                keep.append(rec)
            else:
                Path(rec["path"]).unlink(missing_ok=True)
        self.state["chunks"] = keep
        ids: Set[str] = set()
        for rec in self._inflight_records():
            path = Path(rec["path"])
            if not path.exists():
                self.log.warning(f"batch {rec['batch_id']}: chunk file {path} is gone; "
                                 f"reading the batch's input file back from the service")
                content = await self.client.files.content(rec["input_file_id"])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(_content_text(content), encoding="utf-8")
            ids.update(_read_custom_ids(path))
        self._save_state()
        if ids:
            self.log.info(f"resuming {len(self._inflight_records())} batch(es) in flight, "
                          f"{len(ids)} requests")
        return ids

    # -- chunk files --------------------------------------------------------

    def write_chunks(self, requests: Iterable[Tuple[str, Dict[str, Any]]], *,
                     max_requests: int = DEFAULT_CHUNK_REQUESTS,
                     max_bytes: int = DEFAULT_CHUNK_BYTES) -> List[Path]:
        """Stream ``(custom_id, body)`` pairs into chunk files of at most
        ``max_requests`` lines and ``max_bytes`` bytes; return their paths."""
        max_requests = min(max_requests, MAX_BATCH_REQUESTS)
        max_bytes = min(max_bytes, MAX_BATCH_BYTES)
        self.work_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
        paths: List[Path] = []
        f = None
        n = size = 0
        for custom_id, body in requests:
            line = request_line(custom_id, body).encode("utf-8")
            if f is None or n >= max_requests or size + len(line) > max_bytes:
                if f is not None:
                    f.close()
                path = self.work_dir / f"chunk_{stamp}_{len(paths):04d}.jsonl"
                paths.append(path)
                f = open(path, "wb")
                n = size = 0
            f.write(line)
            n += 1
            size += len(line)
        if f is not None:
            f.close()
        for path in paths:
            self._record(path)["n_requests"] = sum(1 for _ in open(path, "rb"))
        self._save_state()
        return paths

    def _split(self, path: Path) -> List[Path]:
        lines = path.read_bytes().splitlines(keepends=True)
        half = len(lines) // 2
        out = []
        for i, part in enumerate((lines[:half], lines[half:])):
            p = path.with_name(f"{path.stem}_{'ab'[i]}.jsonl")
            p.write_bytes(b"".join(part))
            rec = self._record(p)
            rec["n_requests"] = len(part)
            out.append(p)
        self.state["chunks"] = [r for r in self.state["chunks"] if r["path"] != str(path)]
        path.unlink(missing_ok=True)
        self._save_state()
        return out

    # -- submission and collection -----------------------------------------

    async def _submit(self, path: Path) -> Any:
        uploaded = await self.client.files.create(file=(path.name, path.read_bytes()),
                                                  purpose="batch")
        batch = await self.client.batches.create(
            input_file_id=uploaded.id, endpoint=ENDPOINT,
            completion_window=COMPLETION_WINDOW,
            metadata={**self.metadata, "chunk": path.name})
        rec = self._record(path)
        rec.update(batch_id=batch.id, input_file_id=uploaded.id, submitted_at=_now(),
                   status=_get(batch, "status"))
        self._save_state()
        self.log.info(f"submitted {path.name}: batch {batch.id}, {rec.get('n_requests')} requests")
        return batch

    async def _wait_validation(self, batch: Any) -> Any:
        while _get(batch, "status") == "validating":
            await asyncio.sleep(self.validation_poll_seconds)
            batch = await self.client.batches.retrieve(batch.id)
        return batch

    async def _collect(self, rec: Dict[str, Any], batch: Any,
                       on_result: Callable[[str, Optional[dict], Optional[str]], None],
                       on_batch_done: Callable[[], None],
                       unanswered: Dict[str, Dict[str, Any]]) -> None:
        path = Path(rec["path"])
        expected = set(_read_custom_ids(path))
        seen: Set[str] = set()
        failed: Set[str] = set()
        for file_id in (_get(batch, "output_file_id"), _get(batch, "error_file_id")):
            if not file_id:
                continue
            content = await self.client.files.content(file_id)
            for line in _content_text(content).splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                cid = item.get("custom_id")
                if cid not in expected or cid in seen:
                    continue
                seen.add(cid)
                response = item.get("response") or {}
                if item.get("error") is None and response.get("status_code") == 200:
                    on_result(cid, response.get("body") or {}, None)
                else:
                    err = item.get("error") or (response.get("body") or {}).get("error") or {}
                    failed.add(cid)
                    on_result(cid, None, str(err.get("message") or err or "error")[:200])
        missing = expected - seen
        status = _get(batch, "status")
        if failed or missing:
            self.log.warning(f"batch {batch.id} ({status}): {len(failed)} errored, "
                             f"{len(missing)} not answered, of {len(expected)}")
        unanswered.update(_read_prompts(path, failed | missing))
        on_batch_done()
        rec.update(collected=True, status=status, collected_at=_now(),
                   n_answered=len(seen) - len(failed))
        self._save_state()
        path.unlink(missing_ok=True)
        for file_id in (rec.get("input_file_id"), _get(batch, "output_file_id"),
                        _get(batch, "error_file_id")):
            if file_id:
                try:
                    await self.client.files.delete(file_id)
                except Exception as e:  # noqa: BLE001 -- tidying only
                    self.log.debug(f"could not delete file {file_id}: {e}")

    async def run(self, chunks: List[Path],
                  on_result: Callable[[str, Optional[dict], Optional[str]], None],
                  on_batch_done: Callable[[], None] = lambda: None) -> Dict[str, Dict[str, Any]]:
        """Submit ``chunks`` (and collect any batches :meth:`resume` found in
        flight) and wait until every batch has been collected.  Returns the
        requests no batch answered, as ``custom_id -> body``."""
        pending: Deque[Path] = deque(chunks)
        inflight: Dict[str, Dict[str, Any]] = {r["batch_id"]: r for r in self._inflight_records()}
        unanswered: Dict[str, Dict[str, Any]] = {}
        hold = False
        while pending or inflight:
            while pending and not hold:
                path = pending.popleft()
                batch = await self._wait_validation(await self._submit(path))
                rec = self._record(path)
                if _get(batch, "status") == "failed":
                    rec.update(status="failed", collected=True)
                    if TOKEN_LIMIT_CODE in _error_codes(batch):
                        rec.pop("batch_id", None)
                        rec.pop("collected", None)
                        if inflight:
                            self.log.info(f"{path.name}: queue limit reached; waiting for one "
                                          f"of {len(inflight)} batch(es) in flight")
                            pending.appendleft(path)
                            hold = True
                        elif rec.get("n_requests", 0) > MIN_SPLIT_REQUESTS:
                            self.log.info(f"{path.name}: over the queue limit on its own "
                                          f"({rec.get('n_requests')} requests); splitting it")
                            self._save_state()
                            pending.extendleft(reversed(self._split(path)))
                        else:
                            self._save_state()
                            raise BatchFailedError(f"{path.name}: over the queue limit even at "
                                                   f"{rec.get('n_requests')} requests: {_error_text(batch)}")
                        self._save_state()
                        continue
                    self._save_state()
                    raise BatchFailedError(f"batch {batch.id} ({path.name}) failed validation: "
                                           f"{_error_text(batch)}")
                inflight[batch.id] = rec
            if not inflight:
                continue
            await asyncio.sleep(self.poll_seconds)
            for batch_id in list(inflight):
                batch = await self.client.batches.retrieve(batch_id)
                status = _get(batch, "status")
                counts = _get(batch, "request_counts")
                if status not in TERMINAL_STATUSES:
                    self.log.info(f"batch {batch_id}: {status} "
                                  f"({_get(counts, 'completed', 0)}/{_get(counts, 'total', '?')})")
                    continue
                rec = inflight.pop(batch_id)
                if status == "failed":
                    rec.update(status="failed", collected=True)
                    self._save_state()
                    raise BatchFailedError(f"batch {batch_id} failed: {_error_text(batch)}")
                await self._collect(rec, batch, on_result, on_batch_done, unanswered)
                hold = False
        return unanswered
