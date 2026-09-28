"""Generator run bookkeeping (frozen interface: ``start_run`` / ``RunContext``).

A run lives in ``data/candidates/runs/<generator>/<run_id>/`` and holds
``candidates.jsonl`` (what was submitted), ``run.json`` (git sha, args,
``n_emitted``, UTC start/finish) and ``usage.json`` (always written by
:meth:`RunContext.finish`, with zero calls if the generator made none:
interface resolution 5).  ``RunContext.usage`` is the ``MultiModelUsage`` the
generator passes to every LLM call it makes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Iterable, Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import MultiModelUsage

from .paths import REPO_ROOT, run_dir
from .registry import utc_now


def git_sha(repo: Path = REPO_ROOT) -> Optional[str]:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo, capture_output=True,
                             text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo,
                               capture_output=True, text=True, check=True).stdout.strip()
        return sha + ("+dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return None


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

    def log(self, msg: str) -> None:
        """Print to stderr and append to ``run.log`` in the run directory."""
        line = f"[{utc_now()}] {msg}"
        print(line, file=sys.stderr)
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.dir / "run.log", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def record_candidates(self, cands: Iterable) -> int:
        """Append candidates to ``candidates.jsonl`` (deduplicated on
        ``(surface, sense_id, source_ref)``); count them in ``n_emitted``."""
        path = self.dir / "candidates.jsonl"
        self.dir.mkdir(parents=True, exist_ok=True)
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

    def run_json(self) -> dict:
        return {"generator": self.generator, "run_id": self.run_id, "git_sha": git_sha(),
                "args": self.args, "n_emitted": self.n_emitted, "started_at": self.started_at,
                "finished_at": self.finished_at, "confirmed_by": self.confirmed_by,
                "cost_usd": round(self.usage.total_cost_usd, 4)}

    def finish(self, *, n_emitted: Optional[int] = None) -> Path:
        """Write ``run.json`` and ``usage.json`` (always, even with zero calls)."""
        if n_emitted is not None:
            self.n_emitted = n_emitted
        self.finished_at = utc_now()
        self.dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(json.dumps(self.run_json(), indent=2, ensure_ascii=False) + "\n",
                          self.dir / "run.json")
        self.usage.write_json(self.dir / "usage.json")
        return self.dir


def start_run(generator: str, run_id: str, *, args: Optional[dict] = None,
              candidates_dir: Optional[Path] = None) -> RunContext:
    """Open a run directory (frozen interface).  ``candidates_dir`` overrides
    ``data/candidates`` (tests)."""
    d = run_dir(generator, run_id, candidates_dir=candidates_dir)
    d.mkdir(parents=True, exist_ok=True)
    ctx = RunContext(generator=generator, run_id=run_id, dir=d, args=dict(args or {}))
    return ctx
