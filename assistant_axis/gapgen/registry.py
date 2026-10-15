"""The candidate registry: an append-only JSONL log keyed by ``(stem, sense_id)``.

Every write appends one JSON line per changed record; the **latest line per
``key`` is the record** (``rev`` counts its revisions).  Readers fold the log
(:meth:`Registry.fold`); :func:`compact` rewrites it to one line per key after
copying it to ``registry.jsonl.bak.<UTC>`` and also writes the tracked
snapshot (review amendment 3: the live log is gitignored, the snapshot is what
gets committed and what reports read).  Since 2026-10-12 (code review A5) the
snapshot is gzipped, ``registry.snapshot.jsonl.gz``, and a :class:`Registry`
whose path ends in ``.gz`` reads it (read-only); ``compact`` refuses an
uncompressed snapshot over :data:`SNAPSHOT_UNCOMPRESSED_MAX_BYTES`, and
:func:`snapshot_file` names the snapshot to read in a directory.

Generators never write the file directly: they call
:func:`submit_candidates` (frozen interface); rows a run left in another
checkout's log are brought over by :func:`import_rows`, which replays that
log's lines through the same write path.  The filter and the novelty
scorer update one block of a record at a time (:meth:`Registry.merge_block`,
:meth:`Registry.update_many`).  Appends and read-modify-write cycles hold an
exclusive ``fcntl`` lock on ``<registry>.lock``, so parallel generator runs can
submit to one registry.

Row schema: ``reports/trait_gap_generation/coding_plan_platform.md`` §6.

**Retractions** (2026-10-15, Roger: a way to back out a run whose output was buggy).  :func:`retract` appends a
*control record* (key ``retraction:<generator>/<run_id>``, :data:`RETRACTION_PREFIX`; never a row) saying the run is
retracted, by whom, when and why; :func:`unretract` appends the next state of the same record.  The log's rows are
never rewritten: a retraction is applied when the log is **read**.  :meth:`Registry.fold` (every reader: M1's and
M3's selection, the review graph and app, promotion, the dashboard through :func:`read_snapshot`) removes the
retracted runs' entries from every row's ``sources``; a row left with none is not in the fold; a row that keeps other
sources gains a ``retraction`` note (the runs, how many sources went, whether its first gloss hint, which M1 shows as
the intended sense, changed); a ``relabel`` link that points at a dropped row is cleared.  The writers
(``update_many``, ``submit_candidates``, ``import_rows``) work on the raw rows (``fold(raw=True)``), so a block
written to a row while a run is retracted keeps the run's sources, and :func:`unretract` restores everything.
:func:`compact` keeps the raw rows and the control records in the log and writes the folded view (with the control
records, so the tracked file carries the audit trail) to the snapshot.
"""
from __future__ import annotations

import contextlib
import copy
import fcntl
import gzip
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
from .paths import REGISTRY_PATH, REGISTRY_SNAPSHOT_GZ_NAME, REGISTRY_SNAPSHOT_NAME

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

#: ``compact`` refuses to write an uncompressed snapshot larger than this (code review 2026-10-12, A5): GitHub refuses
#: files over 100 MB, and the next snapshot would have been about 133 MB.  The gzipped one has no limit here.
SNAPSHOT_UNCOMPRESSED_MAX_BYTES = 90 * 1024 * 1024


def is_gzip_path(path: Path | str) -> bool:
    return str(path).endswith(".gz")


def _open_text(path: Path):
    """A registry file for reading, gzipped (``.gz``) or not; bytes that are not UTF-8 are kept (surrogateescape)."""
    if is_gzip_path(path):
        return gzip.open(path, "rt", encoding="utf-8", errors="surrogateescape")
    return open(path, encoding="utf-8", errors="surrogateescape")


def snapshot_file(directory: Path | str) -> Path:
    """The registry snapshot to read in ``directory``: the gzipped one ``compact`` writes since 2026-10-12 when it is
    there, else the uncompressed one (which may not exist either).  ``Registry(snapshot_file(d)).fold()`` reads
    either."""
    d = Path(directory)
    gz = d / REGISTRY_SNAPSHOT_GZ_NAME
    return gz if gz.exists() else d / REGISTRY_SNAPSHOT_NAME


def read_snapshot(path: Path | str) -> dict[str, dict]:
    """A snapshot's rows by key, gzipped or not, read without taking the registry lock (``compact`` replaces a
    snapshot atomically, and nothing appends to one).  Empty when the file is missing.  Retractions recorded in the
    file are applied, as :meth:`Registry.fold` applies them (a live log read this way gets the same view)."""
    return Registry(path)._view_unlocked()

#: Top-level fields of a registry row, in schema order (§6).
ROW_FIELDS = ("schema_version", "key", "stem", "sense_id", "surface", "label", "gloss", "entity_type",
              "sources", "freq", "wordnet", "filter", "novelty", "holding", "matches_existing",
              "heldout_hit", "review", "seed_queue_stem", "relabel", "rev", "created_at", "updated_at")
#: Blocks other workstreams fill (merge_block targets).  ``lexical``: workstream 11's lexical sweep
#: (``assistant_axis.gapgen.lexical_sweep``; not in :data:`ROW_FIELDS`, so a new row is unchanged).  ``persona``:
#: workstream 12's persona-space score (plan 12 decision 1a, Roger 2026-10-13), written beside ``novelty`` and never
#: into it.  ``relabel``: the noun-to-adjective link (``assistant_axis.gapgen.nouns``, 2026-10-14): ``to_key`` /
#: ``to_corpus_stem`` on a noun row, ``from_key`` on its adjective row; written by :func:`submit_candidates` and the
#: ``noun_relabel.py`` streams, ``None`` on every other row (``schema_version`` stays 1: the field is additive).
BLOCKS = ("freq", "wordnet", "filter", "novelty", "review", "lexical", "persona", "relabel")

#: The key prefix of a control record: ``retraction:<generator>/<run_id>`` (a stem is ``[a-z0-9_]``, so no row key
#: can take this form).  The latest line of such a key is the run's retraction state (``"retracted": true | false``).
RETRACTION_PREFIX = "retraction:"
RETRACTION_RECORD = "retraction"
#: The note a row of the folded view gains when a retraction removed some of its sources (not in ROW_FIELDS: it is
#: never written to the log, only to the snapshot, which is the folded view).
RETRACTION_NOTE = "retraction"
#: Review statuses a retraction will not drop or change a row under without ``force`` (normalize.REVIEW_STATUSES;
#: ``parked`` and ``deferred`` are not settled).
SETTLED_REVIEW_STATUSES = ("accepted", "rejected", "merged_into")


def retraction_key(generator: str, run_id: str) -> str:
    return f"{RETRACTION_PREFIX}{generator}/{run_id}"


def is_control_key(key) -> bool:
    return isinstance(key, str) and key.startswith(RETRACTION_PREFIX)


def _run_of(source: dict) -> tuple:
    return (source.get("generator"), source.get("run_id"))


def active_retractions(controls: dict) -> set[tuple[str, str]]:
    """``{(generator, run_id)}`` of the control records (``{key: latest record}``) whose state is retracted."""
    return {(c.get("generator"), c.get("run_id")) for c in controls.values()
            if c.get("record") == RETRACTION_RECORD and c.get("retracted")}


def apply_retractions(rows: dict[str, dict], runs: Iterable[tuple[str, str]]) -> dict[str, dict]:
    """The folded view of ``rows`` (``{key: raw row}``) with ``runs`` retracted (module docstring).

    A row with no source of a retracted run is the same object as in ``rows``; with no runs, ``rows`` itself is
    returned, so a log without retractions folds exactly as before.  A changed row is a shallow copy with
    ``sources`` filtered and a :data:`RETRACTION_NOTE` block ``{"runs", "n_sources_removed", "gloss_hint_changed",
    "relabel_cleared"}``; ``rows`` is never modified."""
    runs = {tuple(r) for r in runs}
    if not runs:
        return rows
    out: dict[str, dict] = {}
    dropped: set[str] = set()
    for k, r in rows.items():
        srcs = r.get("sources") or []
        keep = [s for s in srcs if _run_of(s) not in runs]
        if len(keep) == len(srcs):
            out[k] = r
            continue
        if not keep:
            dropped.add(k)
            continue
        rec = dict(r)
        rec["sources"] = keep
        gone = sorted({f"{g}/{i}" for g, i in (_run_of(s) for s in srcs if _run_of(s) in runs)})
        rec[RETRACTION_NOTE] = {"runs": gone, "n_sources_removed": len(srcs) - len(keep),
                                "gloss_hint_changed": first_gloss_hint(r) != first_gloss_hint(rec),
                                "relabel_cleared": False}
        out[k] = rec
    if dropped:
        for k, r in out.items():
            rb = r.get("relabel")
            if isinstance(rb, dict) and (rb.get("to_key") in dropped or rb.get("from_key") in dropped):
                rec = dict(r) if r is rows.get(k) else r
                rec["relabel"] = None
                note = dict(rec.get(RETRACTION_NOTE) or {"runs": [], "n_sources_removed": 0,
                                                         "gloss_hint_changed": False})
                note["relabel_cleared"] = True
                note["relabel_was"] = rb
                rec[RETRACTION_NOTE] = note
                out[k] = rec
    return out


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


#: ``candidates.jsonl``'s fields: exactly :class:`Candidate`'s, as ``dataclasses.asdict`` writes them.
CANDIDATE_FIELDS: tuple[str, ...] = ("surface", "generator", "run_id", "rank", "score", "gloss_hint", "sense_id",
                                     "source_ref", "partner_hint")
_REQUIRED_CANDIDATE_FIELDS = ("surface", "generator", "run_id")


def read_candidates(path: Path | str) -> list[Candidate]:
    """A generator run's ``candidates.jsonl`` (the convention of coding_plan_platform.md, "Interface as built":
    one JSON object per line, exactly :class:`Candidate`'s fields as ``dataclasses.asdict`` gives them, the
    file :meth:`runs.RunContext.record_candidates` writes), read back as ``Candidate(**row)``, in file order.
    Blank lines are skipped.  ``ValueError`` (naming the file and line) for a line that is not a JSON object,
    has a field :class:`Candidate` does not have, lacks ``surface``, ``generator`` or ``run_id``, or names a
    generator or run id that could not be a directory name."""
    from .paths import check_id
    p = Path(path)
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{p}:{i}: not JSON ({exc.msg})") from None
        if not isinstance(d, dict):
            raise ValueError(f"{p}:{i}: not a JSON object")
        extra = sorted(set(d) - set(CANDIDATE_FIELDS))
        if extra:
            raise ValueError(f"{p}:{i}: fields Candidate does not have: {', '.join(extra)} (the fields are "
                             f"{', '.join(CANDIDATE_FIELDS)})")
        missing = [f for f in _REQUIRED_CANDIDATE_FIELDS if not d.get(f)]
        if missing:
            raise ValueError(f"{p}:{i}: missing {', '.join(missing)}")
        try:
            check_id(d["generator"], "generator")
            check_id(d["run_id"], "run_id")
        except ValueError as exc:
            raise ValueError(f"{p}:{i}: {exc}") from None
        if d.get("sense_id") is None:
            d.pop("sense_id", None)
        out.append(Candidate(**d))
    return out


@dataclass
class SubmitReport:
    n_submitted: int
    n_new: int
    n_merged: int
    keys: list[str]
    n_unchanged: int = 0
    invalid: list[str] = field(default_factory=list)
    #: nouns given an adjective sibling by the relabel step, and ``(noun_key, adj_key | None, corpus_stem | None)``
    #: for each (``adj_key`` None when the adjective is a corpus trait: no row)
    n_relabelled: int = 0
    relabels: list = field(default_factory=list)

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


def _read_held() -> dict:
    """registry path -> depth of shared locks this thread holds."""
    if not hasattr(_HELD, "readers"):
        _HELD.readers = {}
    return _HELD.readers


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
        """Exclusive lock (re-entrant within one thread).

        ``flock`` cannot upgrade a shared lock safely, so asking for the
        exclusive lock while this thread holds the shared one raises
        ``RuntimeError`` at once instead of blocking for ever
        (review_m1_fixes.md item 5b)."""
        key = self._key()
        if key in _held_paths():
            yield
            return
        if _read_held().get(key):
            raise RuntimeError(f"{self.path}: writer lock requested while this thread holds the reader "
                               f"lock (flock cannot upgrade); take the writer lock first")
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
        key = self._key()
        if key in _held_paths() or not self.path.exists():
            yield
            return
        readers = _read_held()
        if readers.get(key):
            readers[key] += 1
            try:
                yield
            finally:
                readers[key] -= 1
            return
        with open(self.lock_path, "a+") as fh:
            fcntl.flock(fh, fcntl.LOCK_SH)
            readers[key] = 1
            try:
                yield
            finally:
                readers.pop(key, None)
                fcntl.flock(fh, fcntl.LOCK_UN)

    # -- reading --------------------------------------------------------
    def iter_lines(self) -> Iterator[dict]:
        """Parsed lines (no lock: callers hold one).  Malformed lines (not JSON,
        not an object, or an object without a ``key``) are skipped, logged and
        recorded in ``self.malformed``.  Bytes that are not valid UTF-8 (a line
        torn inside a multi-byte character) are read with ``surrogateescape``,
        so they make that line malformed instead of making the whole registry
        unreadable, and are written back byte for byte (review_m1_fixes.md
        items 4 and 5a)."""
        self.malformed = []
        if not self.path.exists():
            return
        with _open_text(self.path) as fh:
            for i, raw in enumerate(fh, 1):
                line = raw.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    rec = None
                if not isinstance(rec, dict) or not rec.get("key"):
                    self.malformed.append((i, raw.rstrip("\n")))
                    logger.warning("%s:%d: malformed registry line skipped", self.path, i)
                    continue
                yield rec

    def _scan_unlocked(self) -> tuple[dict[str, dict], dict[str, dict]]:
        """``(rows, controls)``: the latest line of each row key, and of each control key (:data:`RETRACTION_PREFIX`)."""
        rows: dict[str, dict] = {}
        controls: dict[str, dict] = {}
        for rec in self.iter_lines():
            k = rec.get("key")
            if is_control_key(k):
                controls[k] = rec
            elif k:
                rows[k] = rec
        return rows, controls

    def _fold_unlocked(self) -> dict[str, dict]:
        """The raw rows (no retraction applied, no control record): what the writers read and rewrite."""
        return self._scan_unlocked()[0]

    def _view_unlocked(self) -> dict[str, dict]:
        rows, controls = self._scan_unlocked()
        return apply_retractions(rows, active_retractions(controls))

    def fold(self, *, raw: bool = False) -> dict[str, dict]:
        """``{key: latest record}`` (last line per key wins), under a shared lock.  "Latest" is the log's order,
        the order in which writers took the exclusive lock, not any timestamp inside a block.  The retracted runs'
        sources are removed and rows left without a source dropped (:func:`apply_retractions`); ``raw=True`` gives
        the rows as written, which only tools that rewrite rows or audit retractions need."""
        with self._read_locked():
            return self._fold_unlocked() if raw else self._view_unlocked()

    def controls(self) -> dict[str, dict]:
        """``{control key: latest record}``: the retraction records, retracted or not (the audit trail)."""
        with self._read_locked():
            return self._scan_unlocked()[1]

    def retracted_runs(self) -> set[tuple[str, str]]:
        """``{(generator, run_id)}`` currently retracted."""
        return active_retractions(self.controls())

    def get(self, key: str) -> Optional[dict]:
        return self.fold().get(key)

    def __len__(self) -> int:
        return len(self.fold())

    # -- writing --------------------------------------------------------
    def _append(self, records: Sequence[dict]) -> None:
        if not records:
            return
        if is_gzip_path(self.path):
            raise ValueError(f"{self.path} is a gzipped registry snapshot, read-only: write to the live log "
                             f"(registry.jsonl) and run `gap_registry.py compact`")
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
        """Append full records (each gets ``rev`` = previous + 1).  A record replaces its row whole, so pass a row
        read with ``fold(raw=True)``, never one from the retraction view (it would lose the retracted runs' sources
        for good).  Control records are written by :func:`retract` / :func:`unretract` only."""
        records = list(records)
        viewed = [r.get("key") for r in records if RETRACTION_NOTE in r]
        if viewed:      # a row from the retraction view would lose the retracted sources for good (review S1)
            raise ValueError(f"write() takes raw rows, not the retraction view: {viewed[:5]} carry a "
                             f"{RETRACTION_NOTE!r} note (read with fold(raw=True))")
        bad = [r.get("key") for r in records if is_control_key(r.get("key"))]
        if bad:
            raise ValueError(f"{bad[0]!r} is a control record's key: use retract / unretract")
        with self.locked():
            # the time is taken under the lock, so that ``updated_at`` follows the log's order (the fold's)
            now = now or utc_now()
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
        with self.locked():
            now = now or utc_now()          # under the lock: ``updated_at`` follows the log's order
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

_RELABEL_WARNED = False


def _auto_relabel_lookups():
    """The real lookups when OEWN is installed in-tree, else ``None`` after one WARNING per process (the backlog pass,
    ``noun_relabel.py backlog``, catches the rows up later)."""
    global _RELABEL_WARNED
    from . import nouns
    from . import wordnet as W
    try:
        installed = W.oewn_installed()
    except ImportError:
        installed = False
    if not installed:
        if not _RELABEL_WARNED:
            logger.warning("submit_candidates: OEWN is not installed in data/external/wn, so no noun is given its "
                           "adjective sibling; `noun_relabel.py backlog --apply` catches the rows up later")
            _RELABEL_WARNED = True
        return None
    return nouns.OewnLookups.default()


def _relabel_lookups(relabel):
    if relabel is None or relabel is False:
        return None
    if isinstance(relabel, str):
        if relabel != "auto":
            raise ValueError(f"relabel must be 'auto', None or a NounLookups, not {relabel!r}")
        return _auto_relabel_lookups()
    return relabel


def submit_candidates(cands: Iterable[Candidate], *, registry_path: Path = REGISTRY_PATH,
                      run=None, relabel="auto", corpus_stems=None) -> SubmitReport:
    """Add candidates to the registry.

    New ``(stem, sense_id)`` keys become new rows; a candidate whose key exists
    (from any generator, or earlier in the same call) adds its source to the
    row's ``sources[]`` and counts in ``n_merged``; a candidate whose source is
    already recorded (same generator, run_id, surface and source_ref) changes
    nothing (``n_unchanged``), so re-submitting a run is a no-op.  Candidates
    whose surface does not normalise are skipped and listed in ``invalid``.
    With ``run`` (a :class:`~assistant_axis.gapgen.runs.RunContext`) the
    candidates are first recorded in ``<run.dir>/candidates.jsonl``, the
    tracked record, and only then appended to the (per-checkout, git-ignored)
    log, so that nothing reaches a log without its record (2026-10-08; before,
    the record came after the append).  A generator may also call
    ``run.record_candidates(cands)`` itself and submit with ``run=None``.

    The relabel step (``reports/trait_gap_generation/coding_plan_noun_normalization.md``, Roger 2026-10-14): every
    single-word noun that :func:`assistant_axis.gapgen.nouns.relabel` gives an adjective (pedant: pedantic) is
    submitted as given, and the adjective is added as a second candidate of the same generator and run
    (``source_ref`` ``relabel:<rule>:<noun>``), appended after the given candidates and linked both ways by the
    ``relabel`` block (a noun row's ``to_key``, the adjective row's ``from_key``; an adjective row keeps the first
    noun that linked it).  An adjective that is a corpus trait (``corpus_stems``: a set, or ``{stem: current stem}``;
    default the corpus's own, ``nouns.corpus_stem_map``) makes no row: the noun row records ``to_corpus_stem``.
    Derived candidates are not written to ``candidates.jsonl`` (they are a function of it; ``gap_registry.py submit
    --from`` re-derives them).  ``relabel``: ``"auto"`` (the default) uses OEWN when it is installed in-tree, else
    logs one WARNING and relabels nothing; ``None`` or ``False``: off (the M1 validation set, a replay that must be
    judged as given); a :class:`~assistant_axis.gapgen.nouns.NounLookups`: used as given (tests).  The report's
    ``keys``, ``n_new``, ``n_merged`` and ``n_unchanged`` count the derived rows too; ``n_submitted`` counts the
    candidates given.
    """
    cands = list(cands)
    if run is not None:
        run.record_candidates(cands)
    lookups = _relabel_lookups(relabel)
    derived = []
    if lookups is not None:
        from . import nouns
        derived = nouns.relabel_candidates(cands, lookups=lookups,
                                           corpus_stems=nouns.corpus_stem_map() if corpus_stems is None
                                           else corpus_stems)
    all_cands = cands + [d.adjective for d in derived if d.adjective is not None]
    reg = Registry(registry_path)
    keys: list[str] = []
    seen_keys: set[str] = set()
    invalid: list[str] = []
    n_new = n_merged = n_unchanged = 0
    with reg.locked():
        now = utc_now()                     # under the lock: ``created_at`` / ``updated_at`` follow the log's order
        cur = reg._fold_unlocked()
        changed: dict[str, dict] = {}
        for c in all_cands:
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
        relabels = _link_relabels(derived, cur, changed, now) if derived else []
        out = [reg._stamp(r, cur.get(k), now) for k, r in changed.items()]
        reg._append(out)
    if invalid:
        logger.warning("submit_candidates: %d surface(s) did not normalise: %s", len(invalid),
                       ", ".join(repr(s) for s in invalid[:10]))
    return SubmitReport(n_submitted=len(cands), n_new=n_new, n_merged=n_merged, keys=keys,
                        n_unchanged=n_unchanged, invalid=invalid, n_relabelled=len(relabels), relabels=relabels)


def _link_relabels(derived, cur: dict, changed: dict, now: str) -> list[tuple]:
    """Write the ``relabel`` blocks of ``derived`` (``nouns.Derived``) into ``changed`` (rows touched by this
    submission; a row only read so far is copied from ``cur``), as :func:`nouns.link_wanted` allows: a block equal
    but for its time stamp is left alone, so a resubmission writes nothing, and the first noun to link an adjective
    stays its ``from_key``.  Returns ``[(noun_key, adj_key | None, corpus_stem | None)]``."""
    from . import nouns
    out = []

    def link(key: str, block: dict) -> None:
        rec = changed.get(key)
        if rec is None:
            if key not in cur:
                return
            rec = copy.deepcopy(cur[key])
        if not nouns.link_wanted(rec.get("relabel"), block):
            return
        rec["relabel"] = block
        changed[key] = rec

    for d in derived:
        try:
            noun_key = make_key(normalize_candidate(d.noun.surface).stem, d.noun.sense_id)
        except ValueError:
            continue
        try:
            adj_key = None if d.adjective is None else make_key(normalize_candidate(d.adjective.surface).stem, 1)
        except ValueError:      # an adjective the stem rule refuses: as the main loop treats it (review S6)
            continue
        nb, ab = nouns.relabel_blocks(noun_key, adj_key, d.relabel, corpus_stem=d.corpus_stem,
                                      run=f"{d.noun.generator}/{d.noun.run_id}", now=now)
        link(noun_key, nb)
        if ab is not None:
            link(adj_key, ab)
        out.append((noun_key, adj_key, d.corpus_stem))
    return out


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
    #: the folded content's size, and the snapshot's on disk (smaller when gzipped)
    n_bytes: int = 0
    snapshot_bytes: int = 0
    #: an uncompressed snapshot left beside the gzipped one just written: out of date from now on
    stale_snapshot: Optional[Path] = None
    #: control records kept (retractions, retracted or not), and the rows of the snapshot (the folded view: fewer
    #: than ``n_keys`` while a run is retracted)
    n_controls: int = 0
    n_snapshot_rows: int = 0


def _unused_path(base: Path) -> Path:
    """``base`` if free, else ``base-1``, ``base-2``, ... (never overwrite a backup)."""
    if not base.exists():
        return base
    i = 1
    while base.with_name(f"{base.name}-{i}").exists():
        i += 1
    return base.with_name(f"{base.name}-{i}")


def compact(registry_path: Path = REGISTRY_PATH, *, snapshot_path: Optional[Path] = None,
            stamp: Optional[str] = None, set_aside_malformed: bool = False,
            uncompressed: bool = False) -> CompactReport:
    """Fold the log to one line per key (sorted by key).

    Snapshot-before-invalidate: the log is first copied to
    ``registry.jsonl.bak.<UTC>`` (a suffix ``-1``, ``-2`` ... when that name
    is taken; a backup is never overwritten).  The folded content is also
    written to the tracked snapshot beside the log: gzipped,
    ``registry.snapshot.jsonl.gz`` (code review 2026-10-12, A5), or with
    ``uncompressed`` ``registry.snapshot.jsonl`` as before; a ``snapshot_path``
    is gzipped when it ends in ``.gz``.  The gzip stream is deterministic
    (level 9, no name, mtime 0), so the same content gives the same bytes.

    Refused (``ValueError``, nothing written) when the snapshot would be
    uncompressed and larger than :data:`SNAPSHOT_UNCOMPRESSED_MAX_BYTES`,
    and for a gzipped ``registry_path`` (a snapshot, not the log).

    Malformed lines (a torn write) would be dropped by folding, so compaction
    refuses (``ValueError``) while there are any, unless
    ``set_aside_malformed``: then they are written verbatim to
    ``registry.jsonl.rejected.<UTC>`` first and the report names that file.

    Retractions: the log keeps the raw rows and the control records (so a compacted log can still be unretracted);
    the snapshot is the folded view (:meth:`Registry.fold`) followed by the same control records.  A log with no
    control record compacts byte for byte as before.
    """
    reg = Registry(registry_path)
    if is_gzip_path(reg.path):
        raise ValueError(f"{reg.path} is a gzipped snapshot: compact the live log (registry.jsonl)")
    if not reg.path.exists():
        raise FileNotFoundError(f"no registry at {reg.path}")
    default_name = REGISTRY_SNAPSHOT_NAME if uncompressed else REGISTRY_SNAPSHOT_GZ_NAME
    snapshot_path = Path(snapshot_path) if snapshot_path else reg.path.with_name(default_name)
    gz = is_gzip_path(snapshot_path)
    stamp = stamp or utc_stamp()
    rejected = None
    with reg.locked():
        n_lines = sum(1 for _ in reg.iter_lines()) + reg.n_malformed
        folded, controls = reg._scan_unlocked()
        view = apply_retractions(folded, active_retractions(controls))
        if reg.n_malformed and not set_aside_malformed:
            raise ValueError(
                f"{reg.path}: {reg.n_malformed} malformed line(s) (line {reg.malformed[0][0]} first); "
                f"compaction would drop them. Inspect them, or pass set_aside_malformed=True "
                f"(gap_registry.py compact --set-aside-malformed) to move them to a .rejected file")
        tail = "".join(json.dumps(controls[k], ensure_ascii=False) + "\n" for k in sorted(controls))
        log_data = ("".join(json.dumps(folded[k], ensure_ascii=False) + "\n" for k in sorted(folded))
                    + tail).encode("utf-8")
        body = "".join(json.dumps(view[k], ensure_ascii=False) + "\n" for k in sorted(view)) + tail
        data = body.encode("utf-8")
        if not gz and len(data) > SNAPSHOT_UNCOMPRESSED_MAX_BYTES:
            raise ValueError(
                f"the uncompressed snapshot would be {len(data) / 2**20:.0f} MB, over the "
                f"{SNAPSHOT_UNCOMPRESSED_MAX_BYTES / 2**20:.0f} MB limit (GitHub refuses files over 100 MB): write "
                f"the gzipped one (gap_registry.py compact, without --uncompressed)")
        if reg.n_malformed:
            rejected = _unused_path(reg.path.with_name(f"{reg.path.name}.rejected.{stamp}"))
            rejected.write_text("".join(f"{raw}\n" for _, raw in reg.malformed), encoding="utf-8",
                                errors="surrogateescape")
        bak = _unused_path(reg.path.with_name(f"{reg.path.name}.bak.{stamp}"))
        shutil.copy2(reg.path, bak)
        tmp = reg.path.with_name(reg.path.name + ".compact.tmp")
        tmp.write_bytes(log_data)
        tmp.replace(reg.path)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        stmp = snapshot_path.with_name(snapshot_path.name + ".tmp")
        out = gzip.compress(data, compresslevel=9, mtime=0) if gz else data
        stmp.write_bytes(out)
        stmp.replace(snapshot_path)
    plain = snapshot_path.with_name(snapshot_path.name[:-len(".gz")]) if gz else None
    return CompactReport(backup_path=bak, snapshot_path=snapshot_path, n_lines_before=n_lines,
                         n_keys=len(folded), n_malformed=len(reg.malformed) if rejected else 0,
                         rejected_path=rejected, n_bytes=len(data), snapshot_bytes=len(out),
                         stale_snapshot=plain if plain is not None and plain.exists() else None,
                         n_controls=len(controls), n_snapshot_rows=len(view))


# ---------------------------------------------------------------------------
# Import from another checkout's log
# ---------------------------------------------------------------------------

#: The fields an imported row may differ in from the source's fold: the registry stamps them on every write.
IMPORT_STAMPED_FIELDS = ("rev", "updated_at")


@dataclass
class ImportReport:
    """What :func:`import_rows` did (or, with ``dry_run``, would do)."""
    source_path: Path
    registry_path: Path
    n_keys: int
    #: keys this registry lacked: ``{key: [{"line", "rev", "updated_at"} of each source line replayed, in order]}``
    #: (``line``: the n-th non-blank line of the source log; ``rev`` and ``updated_at`` as the source stamped them)
    replayed: dict = field(default_factory=dict)
    #: keys this registry had: ``{key: [the sources[] entries appended]}``
    sources_added: dict = field(default_factory=dict)
    #: keys this registry had with nothing to add
    unchanged: list = field(default_factory=list)
    n_lines_written: int = 0
    dry_run: bool = False
    #: after a write: keys whose new fold differs from what the import meant to write (empty when it landed)
    mismatches: dict = field(default_factory=dict)
    verified: Optional[bool] = None

    def counts(self) -> dict:
        return {"n_keys": self.n_keys, "replayed_keys": len(self.replayed),
                "replayed_lines": sum(len(v) for v in self.replayed.values()),
                "keys_gaining_sources": len(self.sources_added),
                "sources_added": sum(len(v) for v in self.sources_added.values()),
                "unchanged": len(self.unchanged),
                "lines_planned": sum(len(v) for v in self.replayed.values()) + len(self.sources_added),
                "n_lines_written": self.n_lines_written}

    def as_dict(self) -> dict:
        d = asdict(self)
        d["source_path"], d["registry_path"] = str(self.source_path), str(self.registry_path)
        return d


def _strip_stamps(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k not in IMPORT_STAMPED_FIELDS}


def import_rows(source_path: Path | str, keys: Sequence[str], *, registry_path: Path = REGISTRY_PATH,
                only_run: Optional[tuple[str, str]] = None, dry_run: bool = False,
                now: Optional[str] = None) -> ImportReport:
    """Bring the rows of ``keys`` from another checkout's registry log into this one (regeneration list GG5,
    2026-10-13: a generator run submitted, filtered and scored inside a worktree left its rows in that worktree's
    git-ignored log, so they never reached the main checkout's).

    * A key this registry lacks gets **every line the source log holds for it, in the source's order**, appended
      through the registry's own write path (under the writer lock, after a torn last line, fsynced): each line's
      ``rev`` is counted here from 1, ``created_at`` is the source's, ``updated_at`` the time of the import (so it
      follows this log's order, as every write's does).  Its fold then equals the source's fold in every field but
      those two (``rev`` too when the source's history starts at rev 1).  Lines of different keys keep their
      relative source order.
    * A key this registry already has keeps every field it has: it gains only the ``sources[]`` entries of the
      source's latest row that it lacks, compared as :func:`submit_candidates` compares them (generator, run id,
      surface, source ref), appended in the source's order, one line per key; with ``only_run`` (``(generator,
      run_id)``) only that run's entries.  A block the source holds (filter, novelty ...) is never copied onto an
      existing row, so an older block from another checkout cannot overwrite a newer one here.
    * Idempotent: a second import finds every key present and every source on it, and writes nothing.

    Refused (``ValueError``, nothing written): a key the source does not hold; a source with malformed lines (one
    could belong to a requested key); a gzipped target (a snapshot is read-only).  The source is read without its
    lock, so that reading another checkout's log creates nothing there (import from an idle log, or a copy of it).

    ``dry_run`` reads this registry under the reader lock and writes nothing.  After a write the target is folded
    again and every touched key compared with what was meant (``mismatches``, ``verified``).

    Rows are imported raw (as the writers see them), and the source's retraction records are not imported (a control
    key is refused): a run retracted there and imported here must be retracted here too."""
    src = Registry(source_path)
    reg = Registry(registry_path)
    if is_gzip_path(reg.path):
        raise ValueError(f"{reg.path} is a gzipped registry snapshot, read-only: import into the live log")
    if not src.path.exists():
        raise FileNotFoundError(f"no source registry at {src.path}")
    if src.path.resolve() == reg.path.resolve():
        raise ValueError(f"the source and the target are the same file: {src.path}")
    want = list(dict.fromkeys(k.strip() for k in keys if k and k.strip()))
    if any(is_control_key(k) for k in want):
        raise ValueError(f"{next(k for k in want if is_control_key(k))!r} is a retraction record, not a row")
    wanted = set(want)
    lines: list[tuple[int, dict]] = []          # (n-th non-blank source line, record) of the wanted keys, in order
    src_fold: dict[str, dict] = {}
    for n, rec in enumerate(src.iter_lines(), 1):
        if rec["key"] in wanted:
            lines.append((n, rec))
            src_fold[rec["key"]] = rec
    if src.n_malformed:
        raise ValueError(f"{src.path}: {src.n_malformed} malformed line(s) (line {src.malformed[0][0]} first); "
                         f"one could belong to a requested key: repair the source (or compact a copy) first")
    missing = [k for k in want if k not in src_fold]
    if missing:
        raise ValueError(f"{len(missing)} key(s) not in {src.path}: {', '.join(missing[:10])}"
                         + (" ..." if len(missing) > 10 else ""))
    report = ImportReport(source_path=src.path, registry_path=reg.path, n_keys=len(want), dry_run=dry_run)

    def plan(cur: dict) -> tuple[list[dict], dict[str, dict]]:
        """(records to append, in order; {key: what its fold should be afterwards, stamps aside})"""
        out, expect = [], {}
        absent = {k for k in want if k not in cur}
        for i, rec in lines:
            if rec["key"] in absent:
                rec2 = copy.deepcopy(rec)
                rec2.pop(RETRACTION_NOTE, None)     # a snapshot's view note is not a field (review S2)
                out.append(rec2)
                report.replayed.setdefault(rec["key"], []).append(
                    {"line": i, "rev": rec.get("rev"), "updated_at": rec.get("updated_at")})
        for k in absent:
            expect[k] = {f: v for f, v in _strip_stamps(src_fold[k]).items() if f != RETRACTION_NOTE}
        for k in want:
            if k in absent:
                continue
            row = cur[k]
            have = {_source_identity(s) for s in row.get("sources") or []}
            add = []
            for s in src_fold[k].get("sources") or []:
                ident = _source_identity(s)
                if ident in have or (only_run is not None and (s.get("generator"), s.get("run_id")) != tuple(only_run)):
                    continue
                have.add(ident)
                add.append(dict(s))
            if not add:
                report.unchanged.append(k)
                continue
            rec = copy.deepcopy(row)
            rec["sources"] = list(rec.get("sources") or []) + add
            out.append(rec)
            report.sources_added[k] = add
            expect[k] = _strip_stamps(rec)
        return out, expect

    if dry_run:
        plan(reg.fold(raw=True))
        return report
    with reg.locked():
        now = now or utc_now()              # under the lock: ``updated_at`` follows the log's order
        cur = reg._fold_unlocked()
        out, expect = plan(cur)
        stamped = []
        for rec in out:
            s = reg._stamp(rec, cur.get(rec["key"]), now)
            cur[rec["key"]] = s
            stamped.append(s)
        reg._append(stamped)
        report.n_lines_written = len(stamped)
        after = reg._fold_unlocked() if stamped else cur
    for k, exp in expect.items():
        got = _strip_stamps(after.get(k) or {})
        if got != exp:
            report.mismatches[k] = sorted(f for f in set(got) | set(exp) if got.get(f) != exp.get(f))
    report.verified = not report.mismatches
    return report


# ---------------------------------------------------------------------------
# Retraction of a run
# ---------------------------------------------------------------------------

@dataclass
class RetractReport:
    """What :func:`retract` or :func:`unretract` did (or, with ``dry_run``, would do).  Key lists are sorted."""
    action: str                      # "retract" | "unretract"
    generator: str
    run_id: str
    dry_run: bool
    #: rows the folded view loses (retract) or regains (unretract)
    dropped: list = field(default_factory=list)
    #: rows that stay in the view with fewer (or, unretracting, more) sources
    changed: list = field(default_factory=list)
    #: of ``changed``: rows whose first gloss hint (the intended sense M1 is shown) changes
    gloss_hint_changed: list = field(default_factory=list)
    #: of ``gloss_hint_changed``: the rows M1 judged after the run began (or its start unknown): a rerun of M1 there
    gloss_hint_changed_after_run: list = field(default_factory=list)
    #: settled or queued rows that only lose a source (reported, not refused)
    settled_changed: list = field(default_factory=list)
    #: rows whose ``relabel`` link is cleared (retract) or restored (unretract) in the view
    relabel_changed: list = field(default_factory=list)
    #: ``{key: why}``: rows with a settled review, a seed-queue entry, or a merge into a dropped row
    blocked: dict = field(default_factory=dict)
    n_sources: int = 0
    forced: bool = False
    refused: Optional[str] = None
    written: bool = False
    record: Optional[dict] = None

    @property
    def run(self) -> str:
        return f"{self.generator}/{self.run_id}"

    def counts(self) -> dict:
        return {"n_sources": self.n_sources, "n_dropped": len(self.dropped), "n_changed": len(self.changed),
                "n_gloss_hint_changed": len(self.gloss_hint_changed),
                "n_gloss_hint_changed_after_run": len(self.gloss_hint_changed_after_run),
                "n_settled_changed": len(self.settled_changed), "n_relabel_changed": len(self.relabel_changed),
                "n_blocked": len(self.blocked)}

    def as_dict(self) -> dict:
        return {**asdict(self), "run": self.run, "counts": self.counts()}


def _run_started_at(generator: str, run_id: str) -> Optional[str]:
    """The run's ``started_at`` from its ``run.json`` (the earliest session's), or ``None`` when unknown."""
    try:
        from .runs import run_dir
        meta = json.loads((run_dir(generator, run_id) / "run.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    times = [meta.get("started_at")] + [s.get("started_at") for s in meta.get("sessions") or []]
    times = [t for t in times if t]
    return min(times) if times else None


def _blocked(before: dict, after: dict, touched: Iterable[str], queue_keys: Iterable[str], *,
             dropped: Iterable[str] = (), gloss_changed: Iterable[str] = (), run_start: Optional[str] = None) -> dict:
    """``{key: why}`` for the rows a retraction must not move without ``force`` (the Fable review's rule,
    2026-10-15): a settled or queued row the retraction *drops*; a settled or queued row whose first gloss hint
    changes when its review or M1 postdates the run (or the run's start is unknown), since that gloss is what Roger
    saw; and a row merged into a row the retraction drops.  A settled row that merely loses a source is reported
    (:func:`_settled_changed`), not refused: none of its review, M1 or M3 blocks is touched."""
    queued = set(queue_keys or ())
    dropped, gloss_changed = set(dropped), set(gloss_changed)
    out: dict[str, str] = {}
    for k in touched:
        if k not in dropped:
            if k not in gloss_changed:
                continue
            r0 = before.get(k) or {}
            seen = max(str((r0.get("review") or {}).get("at") or ""), str((r0.get("filter") or {}).get("at") or ""))
            if run_start is not None and seen and seen < run_start:
                continue
        r = before.get(k) or after.get(k) or {}
        why = []
        st = (r.get("review") or {}).get("status")
        if st in SETTLED_REVIEW_STATUSES:
            into = (r.get("review") or {}).get("into")
            why.append(f"review {st}" + (f" {into}" if into else ""))
        if r.get("seed_queue_stem"):
            why.append(f"seed queue entry {r['seed_queue_stem']}")
        elif k in queued:
            why.append("named by a seed-queue entry's gap_gen.registry_key")
        if why:
            out[k] = "; ".join(why)
    gone = set(before) - set(after)
    for k, r in after.items():
        into = (r.get("review") or {}).get("into")
        if into in gone:
            out[k] = f"review merged_into {into}, which the retraction drops"
    return dict(sorted(out.items()))


def _settled_changed(before: dict, changed: Iterable[str], queue_keys: Iterable[str]) -> list:
    """The settled or queued rows that only lose a source: reported, never refused."""
    queued = set(queue_keys or ())
    return sorted(k for k in changed if ((before.get(k) or {}).get("review") or {}).get("status") in
                  SETTLED_REVIEW_STATUSES or (before.get(k) or {}).get("seed_queue_stem") or k in queued)


def _effect(rows: dict, runs_before: set, runs_after: set, queue_keys,
            run_start: Optional[str] = None) -> tuple[dict, dict, dict]:
    before = apply_retractions(rows, runs_before)
    after = apply_retractions(rows, runs_after)
    dropped = sorted(set(before) ^ set(after))
    both = set(before) & set(after)
    changed = sorted(k for k in both if (before[k].get("sources") or []) != (after[k].get("sources") or []))
    gloss = sorted(k for k in changed if first_gloss_hint(before[k]) != first_gloss_hint(after[k]))
    relabel = sorted(k for k in both if before[k].get("relabel") != after[k].get("relabel"))
    touched = set(dropped) | set(changed) | set(relabel)
    # the gloss changes that matter: rows M1 judged after the run began (or the run's start unknown); the others
    # were judged before the run's gloss existed (Fable review 2026-10-15, should-fix 3)
    gloss_after = sorted(k for k in gloss if run_start is None or
                         str(((before[k].get("filter") or {}).get("at")) or "") >= run_start)
    eff = {"dropped": dropped, "changed": changed, "gloss_hint_changed": gloss, "gloss_hint_changed_after_run":
           gloss_after, "relabel_changed": relabel, "settled_changed": _settled_changed(before, changed, queue_keys)}
    return eff, _blocked(before, after, touched, queue_keys, dropped=dropped, gloss_changed=gloss,
                         run_start=run_start), {"before": before, "after": after}


def _control_record(prev: Optional[dict], *, generator: str, run_id: str, retracted: bool, reason: str, by: str,
                    now: str, forced: bool, effect: dict) -> dict:
    """The next state of a run's control record: the current state at the top, and every earlier state's event in
    ``history`` (so the latest line alone, the only one compaction keeps, carries the whole audit trail)."""
    history = list((prev or {}).get("history") or [])
    if prev is not None:
        history.append({k: prev.get(k) for k in ("action", "by", "at", "reason", "forced", "effect")})
    return {"key": retraction_key(generator, run_id), "record": RETRACTION_RECORD, "generator": generator,
            "run_id": run_id, "retracted": bool(retracted), "action": "retract" if retracted else "unretract",
            "by": by, "at": now, "reason": reason, "forced": bool(forced), "effect": effect, "history": history,
            "rev": 0, "created_at": now, "updated_at": now}


def _set_retraction(registry_path, generator: str, run_id: str, *, retracted: bool, reason: str, by: str,
                    dry_run: bool, force: bool, queue_keys, now: Optional[str]) -> RetractReport:
    from .paths import check_id
    check_id(generator, "generator")
    check_id(run_id, "run_id")
    if not reason or not str(reason).strip():
        raise ValueError("a reason is required (it is kept in the log)")
    if not by or not str(by).strip():
        raise ValueError("who retracts is required (by)")
    reg = Registry(registry_path)
    if is_gzip_path(reg.path):
        raise ValueError(f"{reg.path} is a gzipped registry snapshot, read-only: retract in the live log")
    run = (generator, run_id)
    rep = RetractReport(action="retract" if retracted else "unretract", generator=generator, run_id=run_id,
                        dry_run=dry_run, forced=bool(force))
    lock = reg._read_locked() if dry_run else reg.locked()
    with lock:
        now = now or utc_now()
        rows, controls = reg._scan_unlocked()
        active = active_retractions(controls)
        rep.n_sources = sum(1 for r in rows.values() for s in r.get("sources") or [] if _run_of(s) == run)
        if retracted:
            if rep.n_sources == 0:
                rep.refused = f"no row of {reg.path} has a source of run {generator}/{run_id}"
                return rep
            if run in active:
                rep.refused = f"run {generator}/{run_id} is already retracted"
                return rep
            new_active = active | {run}
        else:
            if run not in active:
                rep.refused = f"run {generator}/{run_id} is not retracted"
                return rep
            new_active = active - {run}
        eff, blocked, _ = _effect(rows, active, new_active, queue_keys, run_start=_run_started_at(generator, run_id))
        rep.dropped, rep.changed = eff["dropped"], eff["changed"]
        rep.gloss_hint_changed, rep.relabel_changed = eff["gloss_hint_changed"], eff["relabel_changed"]
        rep.gloss_hint_changed_after_run, rep.settled_changed = eff["gloss_hint_changed_after_run"], eff["settled_changed"]
        rep.blocked = blocked if retracted else {}
        if retracted and blocked and not force:
            rep.refused = (f"{len(blocked)} row(s) the retraction would drop, or whose gloss Roger saw it would change, "
                           f"are settled (review, seed queue or a merge into a dropped row); pass force to retract "
                           f"anyway")
            return rep
        effect = {**rep.counts(), "blocked_overridden": sorted(blocked) if retracted and force else []}
        rec = _control_record(controls.get(retraction_key(generator, run_id)), generator=generator, run_id=run_id,
                              retracted=retracted, reason=str(reason).strip(), by=str(by).strip(), now=now,
                              forced=bool(force and blocked), effect=effect)
        if dry_run:
            rep.record = rec
            return rep
        stamped = reg._stamp(rec, controls.get(rec["key"]), now)
        reg._append([stamped])
        rep.record, rep.written = stamped, True
    return rep


def retract(registry_path: Path | str, generator: str, run_id: str, *, reason: str, by: str, dry_run: bool = False,
            force: bool = False, queue_keys: Iterable[str] = (), now: Optional[str] = None) -> RetractReport:
    """Retract the run ``generator/run_id`` (module docstring): append its control record, after which
    :meth:`Registry.fold` no longer shows the run's sources, nor the rows only it proposed.

    Refused (``report.refused`` set, nothing written): no row has a source of the run (a typo); the run is already
    retracted; or, unless ``force``, a row the retraction would drop or change has a settled review status
    (:data:`SETTLED_REVIEW_STATUSES`), a ``seed_queue_stem``, or a key in ``queue_keys`` (the seed queue's
    ``gap_gen.registry_key`` values), or a row that stays is ``merged_into`` a row that goes (``report.blocked``
    lists them all).  ``dry_run`` computes the same report under the reader lock and writes nothing.  The record
    keeps ``by``, the time, ``reason``, whether ``force`` overrode a block (and which keys), the counts, and the
    history of earlier retractions and unretractions of the run."""
    return _set_retraction(registry_path, generator, run_id, retracted=True, reason=reason, by=by, dry_run=dry_run,
                           force=force, queue_keys=queue_keys, now=now)


def unretract(registry_path: Path | str, generator: str, run_id: str, *, reason: str, by: str,
              dry_run: bool = False, now: Optional[str] = None) -> RetractReport:
    """Undo :func:`retract`: append the next state of the run's control record (``retracted: false``), after which
    the fold is what it was before the retraction (plus whatever was written since).  Refused when the run is not
    retracted.  Never blocked: it only gives rows back their sources."""
    return _set_retraction(registry_path, generator, run_id, retracted=False, reason=reason, by=by, dry_run=dry_run,
                           force=False, queue_keys=(), now=now)


def holding_list(kind: str, *, registry: Registry | None = None) -> list[dict]:
    """Rows parked on a holding list (``physical``, ``roles``, ``states`` or
    ``nationalities``; ``normalize.HOLDING``), by key."""
    from .normalize import HOLDING
    if kind not in HOLDING or kind is None:
        raise ValueError(f"holding list must be one of {[h for h in HOLDING if h]}, not {kind!r}")
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
