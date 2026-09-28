"""The candidate registry: an append-only JSONL log keyed by ``(stem, sense_id)``.

Every write appends one JSON line per changed record; the **latest line per
``key`` is the record** (``rev`` counts its revisions).  Readers fold the log
(:meth:`Registry.fold`); :func:`compact` rewrites it to one line per key after
copying it to ``registry.jsonl.bak.<UTC>`` and also writes the tracked
snapshot ``registry.snapshot.jsonl`` (review amendment 3: the live log is
gitignored, the snapshot is what gets committed and what reports read).

Generators never write the file directly: they call
:func:`submit_candidates` (frozen interface).  The filter and the novelty
scorer update one block of a record at a time (:meth:`Registry.merge_block`,
:meth:`Registry.update_many`).  Appends and read-modify-write cycles hold an
exclusive ``fcntl`` lock on ``<registry>.lock``, so parallel generator runs can
submit to one registry.

Row schema: ``reports/trait_gap_generation/coding_plan_platform.md`` §6.
"""
from __future__ import annotations

import contextlib
import copy
import fcntl
import json
import logging
import os
import shutil
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence

from .normalize import make_key, normalize_candidate
from .paths import REGISTRY_PATH, REGISTRY_SNAPSHOT_NAME

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

#: Top-level fields of a registry row, in schema order (§6).
ROW_FIELDS = ("schema_version", "key", "stem", "sense_id", "surface", "label", "gloss", "entity_type",
              "sources", "freq", "wordnet", "filter", "novelty", "holding", "matches_existing",
              "heldout_hit", "review", "seed_queue_stem", "rev", "created_at", "updated_at")
#: Blocks other workstreams fill (merge_block targets).
BLOCKS = ("freq", "wordnet", "filter", "novelty", "review")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ---------------------------------------------------------------------------
# Candidate (frozen interface)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    """One word or phrase a generator proposes (frozen interface).

    A second intended sense of the same word is a second ``Candidate`` with
    ``sense_id=2``.  Submit one ``Candidate`` per source reference: two with the
    same ``(surface, sense_id)`` and different ``source_ref`` merge into one
    row with two ``sources[]`` entries (interface resolution 4).
    ``gloss_hint`` is shown to the filter as the intended sense;
    ``partner_hint`` (an antonym surface) lets ``promote`` set ``partner``.
    """
    surface: str
    generator: str
    run_id: str
    rank: Optional[int] = None
    score: Optional[float] = None
    gloss_hint: Optional[str] = None
    sense_id: int = 1
    source_ref: Optional[str] = None
    partner_hint: Optional[str] = None


@dataclass
class SubmitReport:
    n_submitted: int
    n_new: int
    n_merged: int
    keys: list[str]
    n_unchanged: int = 0
    invalid: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def source_entry(c: Candidate) -> dict:
    return {"generator": c.generator, "run_id": c.run_id, "rank": c.rank, "score": c.score,
            "source_ref": c.source_ref, "gloss_hint": c.gloss_hint, "partner_hint": c.partner_hint,
            "surface": c.surface}


def _source_identity(s: dict) -> tuple:
    return (s.get("generator"), s.get("run_id"), " ".join(str(s.get("surface") or "").lower().split()),
            s.get("source_ref"))


def new_record(surface: str, *, sense_id: int = 1, sources: Sequence[dict] = (),
               now: Optional[str] = None) -> dict:
    """A fresh registry row (rev 0; :meth:`Registry.write` sets rev 1)."""
    n = normalize_candidate(surface)
    now = now or utc_now()
    rec = {k: None for k in ROW_FIELDS}
    rec.update({
        "schema_version": SCHEMA_VERSION, "key": make_key(n.stem, sense_id), "stem": n.stem,
        "sense_id": int(sense_id), "surface": surface, "label": n.label, "entity_type": "trait",
        "sources": [dict(s) for s in sources],
        "review": {"status": "unreviewed", "by": None, "at": None, "note": None},
        "rev": 0, "created_at": now, "updated_at": now,
    })
    return rec


def first_gloss_hint(rec: dict) -> Optional[str]:
    for s in rec.get("sources") or []:
        if s.get("gloss_hint"):
            return s["gloss_hint"]
    return None


# ---------------------------------------------------------------------------
# The log
# ---------------------------------------------------------------------------

_HELD = threading.local()  # registry paths whose exclusive lock this thread holds


def _held_paths() -> set:
    if not hasattr(_HELD, "paths"):
        _HELD.paths = set()
    return _HELD.paths


class Registry:
    """Log-structured JSONL registry.  ``path`` defaults to ``REGISTRY_PATH``.

    Writers hold an exclusive ``flock`` on ``<registry>.lock``; readers
    (:meth:`fold`, :meth:`get`) hold a shared one, so a reader never sees a
    half-written line from a concurrent append.  A thread that already holds
    the exclusive lock reads without re-locking.  :meth:`fold` records the
    malformed lines it skipped in ``malformed`` / ``n_malformed``.
    """

    def __init__(self, path: Path | str = REGISTRY_PATH):
        self.path = Path(path)
        self.malformed: list[tuple[int, str]] = []

    @property
    def n_malformed(self) -> int:
        return len(self.malformed)

    @property
    def lock_path(self) -> Path:
        return self.path.with_name(self.path.name + ".lock")

    def _key(self) -> str:
        return str(self.path.resolve())

    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        """Exclusive lock (re-entrant within one thread)."""
        key = self._key()
        if key in _held_paths():
            yield
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            _held_paths().add(key)
            try:
                yield
            finally:
                _held_paths().discard(key)
                fcntl.flock(fh, fcntl.LOCK_UN)

    @contextlib.contextmanager
    def _read_locked(self) -> Iterator[None]:
        if self._key() in _held_paths() or not self.path.exists():
            yield
            return
        with open(self.lock_path, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            try:
                yield
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)

    # -- reading --------------------------------------------------------
    def iter_lines(self) -> Iterator[dict]:
        """Parsed lines (no lock: callers hold one).  Malformed lines are
        skipped, logged and recorded in ``self.malformed``."""
        self.malformed = []
        if not self.path.exists():
            return
        with open(self.path, encoding="utf-8") as fh:
            for i, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    rec = None
                if not isinstance(rec, dict):
                    self.malformed.append((i, raw.rstrip("\n")))
                    logger.warning("%s:%d: malformed registry line skipped", self.path, i)
                    continue
                yield rec

    def _fold_unlocked(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for rec in self.iter_lines():
            k = rec.get("key")
            if k:
                out[k] = rec
        return out

    def fold(self) -> dict[str, dict]:
        """``{key: latest record}`` (last line per key wins), under a shared lock."""
        with self._read_locked():
            return self._fold_unlocked()

    def get(self, key: str) -> Optional[dict]:
        return self.fold().get(key)

    def __len__(self) -> int:
        return len(self.fold())

    # -- writing --------------------------------------------------------
    def _append(self, records: Sequence[dict]) -> None:
        if not records:
            return
        body = "".join(json.dumps(r, ensure_ascii=False, sort_keys=False) + "\n" for r in records)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # A torn last line (a writer killed mid-write) must not swallow the
        # first record appended after it: start on a fresh line.
        if self.path.exists() and self.path.stat().st_size > 0:
            with open(self.path, "rb") as rf:
                rf.seek(-1, os.SEEK_END)
                if rf.read(1) != b"\n":
                    body = "\n" + body
                    logger.warning("%s: last line had no newline (torn write?); it will be counted as "
                                   "malformed", self.path)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(body)
            fh.flush()
            os.fsync(fh.fileno())

    def _stamp(self, rec: dict, prev: Optional[dict], now: str) -> dict:
        rec = dict(rec)
        rec["rev"] = int((prev or {}).get("rev") or 0) + 1
        rec["updated_at"] = now
        if prev is not None:
            rec["created_at"] = prev.get("created_at") or rec.get("created_at") or now
        return rec

    def write(self, records: Iterable[dict], *, now: Optional[str] = None) -> list[dict]:
        """Append full records (each gets ``rev`` = previous + 1)."""
        now = now or utc_now()
        with self.locked():
            cur = self._fold_unlocked()
            out = []
            for r in records:
                stamped = self._stamp(r, cur.get(r["key"]), now)
                cur[r["key"]] = stamped  # a second record for the same key gets the next rev
                out.append(stamped)
            self._append(out)
        return out

    def update_many(self, updates: dict[str, dict], *, now: Optional[str] = None,
                    merge_blocks: bool = True) -> list[dict]:
        """Apply ``{key: {field: value}}`` in one locked cycle.

        For a field in :data:`BLOCKS` whose current and new values are both
        dicts, the new keys are merged into the block (``merge_blocks``);
        every other field is replaced.  Unknown keys raise ``KeyError``.
        """
        now = now or utc_now()
        with self.locked():
            cur = self._fold_unlocked()
            out = []
            for key, fields in updates.items():
                if key not in cur:
                    raise KeyError(f"registry has no key {key!r}")
                rec = copy.deepcopy(cur[key])
                for name, value in fields.items():
                    if (merge_blocks and name in BLOCKS and isinstance(value, dict)
                            and isinstance(rec.get(name), dict)):
                        rec[name] = {**rec[name], **value}
                    else:
                        rec[name] = value
                out.append(self._stamp(rec, cur[key], now))
            self._append(out)
        return out

    def update(self, key: str, fields: dict, *, now: Optional[str] = None) -> dict:
        return self.update_many({key: fields}, now=now)[0]

    def merge_block(self, key: str, block: str, value: Optional[dict], *, replace: bool = False,
                    now: Optional[str] = None) -> dict:
        """Update one block of one record; every other field is untouched.
        ``replace=True`` (or ``value=None``) replaces the block instead of
        merging into it."""
        if block not in BLOCKS:
            raise ValueError(f"not a registry block: {block!r} (one of {BLOCKS})")
        return self.update_many({key: {block: value}}, now=now, merge_blocks=not replace)[0]


# ---------------------------------------------------------------------------
# Submission (frozen interface)
# ---------------------------------------------------------------------------

def submit_candidates(cands: Iterable[Candidate], *, registry_path: Path = REGISTRY_PATH,
                      run=None) -> SubmitReport:
    """Add candidates to the registry.

    New ``(stem, sense_id)`` keys become new rows; a candidate whose key exists
    (from any generator, or earlier in the same call) adds its source to the
    row's ``sources[]`` and counts in ``n_merged``; a candidate whose source is
    already recorded (same generator, run_id, surface and source_ref) changes
    nothing (``n_unchanged``), so re-submitting a run is a no-op.  Candidates
    whose surface does not normalise are skipped and listed in ``invalid``.
    With ``run`` (a :class:`~assistant_axis.gapgen.runs.RunContext`) the
    candidates are also recorded in ``<run.dir>/candidates.jsonl``.
    """
    cands = list(cands)
    reg = Registry(registry_path)
    now = utc_now()
    keys: list[str] = []
    seen_keys: set[str] = set()
    invalid: list[str] = []
    n_new = n_merged = n_unchanged = 0
    with reg.locked():
        cur = reg._fold_unlocked()
        changed: dict[str, dict] = {}
        for c in cands:
            try:
                n = normalize_candidate(c.surface)
            except ValueError:
                invalid.append(c.surface)
                continue
            key = make_key(n.stem, c.sense_id)
            if key not in seen_keys:
                seen_keys.add(key)
                keys.append(key)
            src = source_entry(c)
            if key in changed:
                rec = changed[key]
            elif key in cur:
                rec = copy.deepcopy(cur[key])
            else:
                rec = new_record(c.surface, sense_id=c.sense_id, sources=[src], now=now)
                changed[key] = rec
                n_new += 1
                continue
            ids = {_source_identity(s) for s in rec.get("sources") or []}
            if _source_identity(src) in ids:
                n_unchanged += 1
                continue
            rec.setdefault("sources", []).append(src)
            changed[key] = rec
            n_merged += 1
        out = [reg._stamp(r, cur.get(k), now) for k, r in changed.items()]
        reg._append(out)
    if invalid:
        logger.warning("submit_candidates: %d surface(s) did not normalise: %s", len(invalid),
                       ", ".join(repr(s) for s in invalid[:10]))
    report = SubmitReport(n_submitted=len(cands), n_new=n_new, n_merged=n_merged, keys=keys,
                          n_unchanged=n_unchanged, invalid=invalid)
    if run is not None:
        run.record_candidates(cands)
    return report


# ---------------------------------------------------------------------------
# Compaction and queries
# ---------------------------------------------------------------------------

@dataclass
class CompactReport:
    backup_path: Path
    snapshot_path: Path
    n_lines_before: int
    n_keys: int
    n_malformed: int = 0
    rejected_path: Optional[Path] = None


def _unused_path(base: Path) -> Path:
    """``base`` if free, else ``base-1``, ``base-2``, ... (never overwrite a backup)."""
    if not base.exists():
        return base
    i = 1
    while base.with_name(f"{base.name}-{i}").exists():
        i += 1
    return base.with_name(f"{base.name}-{i}")


def compact(registry_path: Path = REGISTRY_PATH, *, snapshot_path: Optional[Path] = None,
            stamp: Optional[str] = None, set_aside_malformed: bool = False) -> CompactReport:
    """Fold the log to one line per key (sorted by key).

    Snapshot-before-invalidate: the log is first copied to
    ``registry.jsonl.bak.<UTC>`` (a suffix ``-1``, ``-2`` ... when that name
    is taken; a backup is never overwritten).  The folded content is also
    written to the tracked snapshot (default ``registry.snapshot.jsonl``
    beside the log).

    Malformed lines (a torn write) would be dropped by folding, so compaction
    refuses (``ValueError``) while there are any, unless
    ``set_aside_malformed``: then they are written verbatim to
    ``registry.jsonl.rejected.<UTC>`` first and the report names that file.
    """
    reg = Registry(registry_path)
    if not reg.path.exists():
        raise FileNotFoundError(f"no registry at {reg.path}")
    snapshot_path = Path(snapshot_path) if snapshot_path else reg.path.with_name(REGISTRY_SNAPSHOT_NAME)
    stamp = stamp or utc_stamp()
    rejected = None
    with reg.locked():
        n_lines = sum(1 for _ in reg.iter_lines()) + reg.n_malformed
        folded = reg._fold_unlocked()
        if reg.n_malformed:
            if not set_aside_malformed:
                raise ValueError(
                    f"{reg.path}: {reg.n_malformed} malformed line(s) (line {reg.malformed[0][0]} first); "
                    f"compaction would drop them. Inspect them, or pass set_aside_malformed=True "
                    f"(gap_registry.py compact --set-aside-malformed) to move them to a .rejected file")
            rejected = _unused_path(reg.path.with_name(f"{reg.path.name}.rejected.{stamp}"))
            rejected.write_text("".join(f"{raw}\n" for _, raw in reg.malformed), encoding="utf-8")
        bak = _unused_path(reg.path.with_name(f"{reg.path.name}.bak.{stamp}"))
        shutil.copy2(reg.path, bak)
        body = "".join(json.dumps(folded[k], ensure_ascii=False) + "\n" for k in sorted(folded))
        tmp = reg.path.with_name(reg.path.name + ".compact.tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(reg.path)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        stmp = snapshot_path.with_name(snapshot_path.name + ".tmp")
        stmp.write_text(body, encoding="utf-8")
        stmp.replace(snapshot_path)
    return CompactReport(backup_path=bak, snapshot_path=snapshot_path, n_lines_before=n_lines,
                         n_keys=len(folded), n_malformed=len(reg.malformed) if rejected else 0,
                         rejected_path=rejected)


def holding_list(kind: str, *, registry: Registry | None = None) -> list[dict]:
    """Rows parked on a holding list (``physical`` or ``roles``), by key."""
    if kind not in ("physical", "roles"):
        raise ValueError(f"holding list must be 'physical' or 'roles', not {kind!r}")
    reg = registry or Registry()
    return [r for k, r in sorted(reg.fold().items()) if r.get("holding") == kind]


def has_source(rec: dict, generator: str, run_id: Optional[str] = None) -> bool:
    return any(s.get("generator") == generator and (run_id is None or s.get("run_id") == run_id)
               for s in rec.get("sources") or [])


def records_for_status(registry: Registry | None = None, *, verdict: Optional[str] = None,
                       decision: Optional[str] = None, review: Optional[str] = None,
                       holding: Optional[str] = None, generator: Optional[str] = None,
                       run: Optional[tuple[str, str]] = None, unfiltered: bool = False,
                       keys: Optional[Sequence[str]] = None) -> list[dict]:
    """Rows matching every given condition, sorted by key.

    ``run=(generator, run_id)`` selects rows with that source;
    ``unfiltered=True`` keeps rows with no ``filter`` block yet.
    """
    reg = registry or Registry()
    rows = reg.fold()
    if keys is not None:
        missing = [k for k in keys if k not in rows]
        if missing:
            raise KeyError(f"not in registry: {', '.join(missing[:10])}")
        sel = [rows[k] for k in keys]
    else:
        sel = [rows[k] for k in sorted(rows)]
    out = []
    for r in sel:
        f = r.get("filter") or {}
        nv = r.get("novelty") or {}
        if unfiltered and r.get("filter"):
            continue
        if verdict is not None and f.get("verdict") != verdict:
            continue
        if decision is not None and nv.get("decision") != decision:
            continue
        if review is not None and (r.get("review") or {}).get("status") != review:
            continue
        if holding is not None and r.get("holding") != holding:
            continue
        if generator is not None and not has_source(r, generator):
            continue
        if run is not None and not has_source(r, run[0], run[1]):
            continue
        out.append(r)
    return out
