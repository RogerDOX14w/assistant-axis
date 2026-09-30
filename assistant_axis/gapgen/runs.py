"""Generator run bookkeeping (frozen interface: ``start_run`` / ``RunContext``).

A run lives in ``data/candidates/runs/<generator>/<run_id>/`` and holds
``candidates.jsonl`` (what was submitted), ``run.json`` (git sha, args,
``n_emitted``, UTC start/finish, sessions) and ``usage.json`` (always written
by :meth:`RunContext.finish`, with zero calls if the generator made none:
interface resolution 5).  ``RunContext.usage`` is the ``MultiModelUsage`` the
generator passes to every LLM call it makes.

Sessions (review_m1.md finding 1; review_m1_fixes.md item 1).  A run id may be
reused: a generator resumed in a second process, its candidates file
submitted later through ``gap_registry.py submit``, a generator that calls
``finish()`` as a checkpoint, or two shards sharing a run id.  Each
``start_run`` creates a session with its own ``session_id``.  ``run.json`` is::

    {"generator", "run_id", "git_sha", "args" (the first session's),
     "n_emitted" (sum over sessions), "started_at" (earliest),
     "finished_at" (latest), "confirmed_by", "cost_usd" (sum),
     "sessions": [{"session_id", "started_at", "finished_at", "git_sha", "args",
                   "n_emitted", "confirmed_by", "cost_usd", "n_calls",
                   "usage": <MultiModelUsage.as_dict() of this session>}, ...],
     "legacy_usage": <only for a run first written before sessions carried usage>}

and ``usage.json`` is the sum of the sessions' ``usage`` (plus
``legacy_usage``).  ``finish()`` takes an exclusive ``flock`` on
``<run dir>/.run.lock``, re-reads ``run.json``, replaces or appends its own
session by id and writes both files, so overlapping sessions, in one process
or several, never drop each other's spend, and a repeated ``finish()``
replaces its session instead of adding it again.  ``candidates.jsonl`` is
updated under the same lock.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import logging
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import MultiModelUsage

from .paths import REPO_ROOT, run_dir
from .registry import utc_now

RUN_LOCK_NAME = ".run.lock"

#: Paths whose uncommitted changes can alter what a paid platform run sends or
#: how its output is read: the platform package (rubric, prompts, parser,
#: normalisation, cost), its CLIs, the helpers they import from the project
#: (JSON extraction, pricing, entity-name normalisation), the dependency lock,
#: and the tracked validation inputs (review_m1_fixes.md item 5c).
PLATFORM_PATHS: tuple[str, ...] = (
    "assistant_axis/gapgen",
    "data_analysis/gap_generation",
    "assistant_axis/judge.py",
    "assistant_axis/judge_pricing.py",
    "assistant_axis/entity_id.py",
    "assistant_axis/atomic_io.py",
    "data/candidates/validation",
    # the split filter's prompts are read from these files at run time
    "reports/trait_gap_generation/rubrics",
    "pyproject.toml",
    "uv.lock",
)


#: The platform CLIs' log format: every line carries its UTC time, in the form the records use
#: (``batches.json``, ``responses.jsonl``), so a run's log can be read against them.
LOG_FORMAT = "%(asctime)s %(levelname)s %(message)s"
LOG_DATEFMT = "%Y-%m-%dT%H:%M:%SZ"


def log_formatter() -> logging.Formatter:
    """The platform log formatter (UTC)."""
    f = logging.Formatter(LOG_FORMAT, LOG_DATEFMT)
    f.converter = time.gmtime
    return f


def configure_logging(level: int = logging.INFO) -> None:
    """``logging.basicConfig`` with :func:`log_formatter`; like ``basicConfig``, it does nothing
    when the root logger already has a handler."""
    h = logging.StreamHandler()
    h.setFormatter(log_formatter())
    logging.basicConfig(level=level, handlers=[h])


def git_sha(repo: Path = REPO_ROOT) -> Optional[str]:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


def platform_dirty_files(repo: Path = REPO_ROOT, paths: Iterable[str] = PLATFORM_PATHS) -> Optional[list[str]]:
    """``git status --porcelain`` lines for uncommitted changes (tracked or
    new, not ignored) under ``paths`` only; ``[]`` when clean, ``None`` when
    git is unavailable.  An edited report elsewhere does not count."""
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all", "--", *paths],
                             cwd=repo, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return [line for line in out.splitlines() if line.strip()]


@dataclass
class RunContext:
    generator: str
    run_id: str
    dir: Path
    usage: MultiModelUsage = field(default_factory=MultiModelUsage)
    args: dict = field(default_factory=dict)
    started_at: str = field(default_factory=utc_now)
    n_emitted: int = 0
    finished_at: Optional[str] = None
    confirmed_by: Optional[str] = None
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def log(self, msg: str) -> None:
        """Print to stderr and append to ``run.log`` in the run directory."""
        line = f"[{utc_now()}] {msg}"
        print(line, file=sys.stderr)
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "run.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    @contextlib.contextmanager
    def _run_lock(self) -> Iterator[None]:
        """Exclusive ``flock`` on ``<run dir>/.run.lock`` (every session of this
        run id, in any process, serialises its read-modify-write here)."""
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / RUN_LOCK_NAME, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    def record_candidates(self, cands: Iterable) -> int:
        """Append candidates to ``candidates.jsonl`` (deduplicated on
        ``(surface, sense_id, source_ref)``); count them in ``n_emitted``."""
        path = self.dir / "candidates.jsonl"
        with self._run_lock():
            seen, lines = set(), []
            if path.exists():
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        d = json.loads(line)
                        seen.add((d.get("surface"), d.get("sense_id"), d.get("source_ref")))
                        lines.append(line)
            n_new = 0
            for c in cands:
                d = asdict(c) if is_dataclass(c) else dict(c)
                ident = (d.get("surface"), d.get("sense_id"), d.get("source_ref"))
                if ident in seen:
                    continue
                seen.add(ident)
                lines.append(json.dumps(d, ensure_ascii=False))
                n_new += 1
            atomic_write_text("".join(line + "\n" for line in lines), path)
        self.n_emitted += n_new
        return n_new

    def session_json(self) -> dict:
        """This session only, with its own usage."""
        return {"session_id": self.session_id, "started_at": self.started_at, "finished_at": self.finished_at,
                "git_sha": git_sha(), "args": self.args, "n_emitted": self.n_emitted,
                "confirmed_by": self.confirmed_by, "cost_usd": round(self.usage.total_cost_usd, 4),
                "n_calls": self.usage.n_calls, "usage": self.usage.as_dict()}

    def _merged(self) -> tuple[dict, MultiModelUsage]:
        """The run as it would be with this session recorded: reads the
        on-disk ``run.json`` (and, for a run written before sessions carried
        their usage, ``usage.json``), replaces or appends this session by
        ``session_id``, and sums usage over sessions.  Pure: writes nothing."""
        p = self.dir / "run.json"
        run = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        sessions = [dict(s) for s in run.get("sessions") or []]
        legacy = run.get("legacy_usage")
        if not sessions and run:  # a run.json written before sessions existed
            sessions = [{k: run.get(k) for k in ("started_at", "finished_at", "git_sha", "args", "n_emitted",
                                                 "confirmed_by", "cost_usd")}]
        if legacy is None and any("usage" not in s for s in sessions):
            # earlier layout: the sessions' usage exists only as the total in usage.json
            legacy = MultiModelUsage.load_or_create(self.dir / "usage.json").as_dict()
        for i, s in enumerate(sessions):
            s.setdefault("session_id", f"legacy-{i}")
        mine = self.session_json()
        for i, s in enumerate(sessions):
            if s["session_id"] == self.session_id:
                sessions[i] = mine
                break
        else:
            sessions.append(mine)
        total = MultiModelUsage()
        if legacy:
            total.merge_from(MultiModelUsage.from_dict(legacy))
        for s in sessions:
            if s.get("usage"):
                total.merge_from(MultiModelUsage.from_dict(s["usage"]))
        starts = [s.get("started_at") for s in sessions if s.get("started_at")]
        confirmed = [s.get("confirmed_by") for s in sessions if s.get("confirmed_by")]
        merged = {"generator": self.generator, "run_id": self.run_id, "git_sha": git_sha(),
                  "args": sessions[0].get("args") if sessions else self.args,
                  "n_emitted": sum(int(s.get("n_emitted") or 0) for s in sessions),
                  "started_at": min(starts) if starts else self.started_at,
                  "finished_at": max((s.get("finished_at") or "") for s in sessions) or self.finished_at,
                  "confirmed_by": confirmed[-1] if confirmed else None,
                  "cost_usd": round(total.total_cost_usd, 4), "sessions": sessions}
        if legacy:
            merged["legacy_usage"] = legacy
        return merged, total

    def total_usage(self) -> MultiModelUsage:
        """Every session's usage, including this one's (as of now, not locked)."""
        return self._merged()[1]

    def run_json(self) -> dict:
        """The run across every session (see the module docstring); not locked,
        writes nothing."""
        return self._merged()[0]

    def finish(self, *, n_emitted: Optional[int] = None) -> Path:
        """Record this session and write ``run.json`` and ``usage.json``
        (always, even with zero calls).  Under the run lock: re-read
        ``run.json``, replace or append this session by ``session_id``, and
        write ``usage.json`` as the sum over sessions.  Safe to call repeatedly
        (checkpoints) and from overlapping sessions or processes."""
        if n_emitted is not None:
            self.n_emitted = n_emitted
        self.finished_at = utc_now()
        with self._run_lock():
            run, total = self._merged()
            atomic_write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", self.dir / "run.json")
            atomic_write_text(json.dumps(total.as_dict(), indent=2, sort_keys=True), self.dir / "usage.json")
        return self.dir


def start_run(generator: str, run_id: str, *, args: Optional[dict] = None,
              candidates_dir: Optional[Path] = None) -> RunContext:
    """Open a run directory (frozen interface).  ``candidates_dir`` overrides
    ``data/candidates`` (tests)."""
    d = run_dir(generator, run_id, candidates_dir=candidates_dir)
    d.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(generator=generator, run_id=run_id, dir=d, args=dict(args or {}))
    return ctx
