"""Record files that may live gzip-compressed (``X.gz``) beside or instead of their plain form ``X``.

The platform records every paid model answer in JSON-lines files under ``data/candidates/``, and these are
tracked in git.  One reached 126 MB and GitHub refused the push (limit 100 MB), so a record file may be
**packed**: its content moved into ``X.gz`` (about 6x smaller) and the plain ``X`` deleted.  Every reader
goes through this module, so a packed file reads exactly as the plain one did.  Writers are unchanged: they
keep writing the plain ``X``.  Two kinds of record file (:data:`KINDS`, by file name):

* **Logs** (:data:`LOG`: ``responses.jsonl``), only ever appended to while a run is live.  The logical
  content is ``X.gz`` (if present) followed by ``X`` (if present), byte for byte.  Packing appends the plain
  file's bytes to ``X.gz`` as a new gzip member (``gzip`` reads multi-member files as one stream) and deletes
  ``X``; a later resume appends to a fresh plain ``X``, so there is never a stale copy.  A writer that
  rewrites a log whole from what it read (the traithood filter, the plain-reading pass and the states pass
  rewrite ``responses.jsonl`` at the end so the per-call lines gain their parse errors) uses
  :func:`rewrite_jsonl`, which drops ``X.gz`` once the plain file holds everything.
* **Snapshots** (:data:`SNAPSHOT`: ``results.jsonl``, ``graph.json``, ``readings.jsonl``,
  ``matches.jsonl``), rewritten whole each time.  A reader takes the plain ``X`` if it exists, else
  ``X.gz``: a writer that rewrites the plain file makes it current again, and packing again replaces the
  ``.gz``.

A file name not in :data:`KINDS` is an ordinary file: :func:`exists` and the readers look at the plain file
only, and :func:`pack` refuses it.  :func:`pack` is what ``data_analysis/gap_generation/pack_records.py``
runs; it verifies the new ``.gz`` decompresses to exactly the content it read before deleting the plain file.
Do not pack a run that is live: a cooperating session's lock (``overlap_test.acquire_session_lock``) is
honoured, and a plain file that changes while it is being packed is left alone, but an unlocked writer that
appends between the check and the delete would lose that line from the logical content.

Out of scope (2026-10-14): the registry log ``registry.jsonl`` (git-ignored; its tracked copy is the gzipped
snapshot ``gap_registry.py compact`` writes) and the review app's ``decisions.jsonl``.
"""
from __future__ import annotations

import fcntl
import gzip
import io
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

LOG = "log"
SNAPSHOT = "snapshot"

#: Record files by name.  Each entry is what the code does with the file (2026-10-14): every writer of a
#: ``responses.jsonl`` appends each answer as it arrives (three also rewrite it whole at the end, through
#: :func:`rewrite_jsonl`); the snapshots are only ever written whole (``atomic_write_text`` /
#: ``write_jsonl`` / ``json_metadata`` envelopes).  ``registry_writes.jsonl`` is left out on purpose: M3
#: appends to it while ``lexical_recall.py`` rewrites it whole, and it stays under 6 MB.
KINDS: dict[str, str] = {
    "responses.jsonl": LOG,
    "results.jsonl": SNAPSHOT,
    "graph.json": SNAPSHOT,
    "readings.jsonl": SNAPSHOT,
    "matches.jsonl": SNAPSHOT,
}

GZ_SUFFIX = ".gz"
#: Bytes read to estimate a file's packed size (:func:`estimate_packed_bytes`).
ESTIMATE_SAMPLE_BYTES = 8 << 20


def kind_of(path: Path | str) -> Optional[str]:
    """:data:`LOG`, :data:`SNAPSHOT` or None (not a record file) from ``path``'s name (a ``.gz`` name counts
    as its plain form's)."""
    name = Path(path).name
    if name.endswith(GZ_SUFFIX):
        name = name[: -len(GZ_SUFFIX)]
    return KINDS.get(name)


def plain_path(path: Path | str) -> Path:
    """``X`` for a record file's ``X`` or ``X.gz``; any other path as given (``registry.snapshot.jsonl.gz`` is not
    a packed record: it stays what it is)."""
    p = Path(path)
    if p.name.endswith(GZ_SUFFIX) and kind_of(p) is not None:
        return p.with_name(p.name[: -len(GZ_SUFFIX)])
    return p


def gz_path(path: Path | str) -> Path:
    """``X.gz`` for ``X`` (or ``X.gz``)."""
    p = plain_path(path)
    return p.with_name(p.name + GZ_SUFFIX)


def _kind(path: Path | str, kind: Optional[str]) -> Optional[str]:
    if kind is None:
        return kind_of(path)
    if kind not in (LOG, SNAPSHOT):
        raise ValueError(f"unknown record kind {kind!r}: use {LOG!r} or {SNAPSHOT!r}")
    return kind


def exists(path: Path | str, kind: Optional[str] = None) -> bool:
    """Whether the record has any content on disk: ``X`` or (a record file) ``X.gz``."""
    p = plain_path(path)
    if p.exists():
        return True
    return _kind(p, kind) is not None and gz_path(p).exists()


def current_path(path: Path | str, kind: Optional[str] = None) -> Path:
    """The file a provenance input should fingerprint: ``X`` when it exists (for a log, the tail that changes
    as answers land), else ``X.gz`` when that exists, else ``X`` (so a caller that needs the file fails on the
    name it asked for)."""
    p = plain_path(path)
    if p.exists() or _kind(p, kind) is None:
        return p
    g = gz_path(p)
    return g if g.exists() else p


def glob(root: Path | str, pattern: str) -> list[Path]:
    """``sorted(Path(root).glob(pattern))`` for a pattern ending in a record file's name, with a packed file
    found as its plain path: each record once, whether it is plain, packed or both."""
    root = Path(root)
    found = {p for p in root.glob(pattern)}
    if kind_of(pattern) is not None:
        found |= {plain_path(g) for g in root.glob(pattern + GZ_SUFFIX)}
    return sorted(found)


def read_bytes(path: Path | str, kind: Optional[str] = None) -> bytes:
    """The record's logical content (module docstring); FileNotFoundError when there is none."""
    p = plain_path(path)
    k = _kind(p, kind)
    g = gz_path(p)
    if k is None or not g.exists():
        return p.read_bytes()
    if k == SNAPSHOT:
        return p.read_bytes() if p.exists() else gzip.decompress(g.read_bytes())
    head = gzip.decompress(g.read_bytes())
    return head + p.read_bytes() if p.exists() else head


def read_text(path: Path | str, kind: Optional[str] = None, *, encoding: str = "utf-8") -> str:
    """:func:`read_bytes` decoded as ``Path.read_text`` decodes (universal newlines).  A plain file with no
    ``.gz`` beside it is read with ``Path.read_text`` itself, so its text is exactly what it was."""
    p = plain_path(path)
    if _kind(p, kind) is None or not gz_path(p).exists():
        return p.read_text(encoding=encoding)
    with io.TextIOWrapper(io.BytesIO(read_bytes(p, kind)), encoding=encoding) as fh:
        return fh.read()


def read_jsonl(path: Path | str, kind: Optional[str] = None) -> list[dict]:
    """Every non-blank line of the record parsed as JSON; FileNotFoundError when there is none."""
    return [json.loads(x) for x in read_text(path, kind).splitlines() if x.strip()]


def read_json(path: Path | str, kind: Optional[str] = None) -> Any:
    """A snapshot JSON file (``graph.json``) parsed; FileNotFoundError when there is none."""
    return json.loads(read_text(path, kind))


def rewrite_jsonl(rows: Iterable[dict], path: Path | str) -> None:
    """Rewrite a record file whole (``atomic_io.write_jsonl``) from rows that hold its entire content, then
    delete its ``.gz``, whose content the rows now carry.  For a writer that read the log (a resume),
    added to it in memory and writes it all back; never for a writer that writes only its own rows.  A
    process killed between the two steps leaves the old ``.gz`` beside the full plain file, so the log reads
    with the packed lines twice until that ``.gz`` is deleted by hand (a resume replays answers by key, so it is
    harmless there; :func:`pack` refuses such a log when its plain file starts with the ``.gz`` content byte for
    byte, which a rewrite that changed earlier lines does not)."""
    from assistant_axis.atomic_io import write_jsonl

    p = plain_path(path)
    write_jsonl(list(rows), p)
    g = gz_path(p)
    if g.exists():
        g.unlink()


@dataclass
class PackReport:
    """What :func:`pack` did (``action``: ``packed``, ``nothing`` or ``refused``) and the sizes involved."""

    path: str
    kind: Optional[str]
    action: str
    reason: str = ""
    plain_bytes: int = 0
    gz_bytes_before: int = 0
    gz_bytes_after: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _gzip_member(data: bytes) -> bytes:
    """One gzip member holding ``data`` (level 9, mtime 0: the same bytes give the same file)."""
    return gzip.compress(data, compresslevel=9, mtime=0)


def estimate_packed_bytes(path: Path | str) -> int:
    """A file's size once packed, from the compression ratio of its first :data:`ESTIMATE_SAMPLE_BYTES`."""
    p = Path(path)
    size = p.stat().st_size
    if size == 0:
        return 0
    with open(p, "rb") as fh:
        sample = fh.read(ESTIMATE_SAMPLE_BYTES)
    return round(len(gzip.compress(sample, compresslevel=6, mtime=0)) * size / len(sample))


def _stat_key(p: Path) -> tuple[int, int]:
    st = p.stat()
    return st.st_size, st.st_mtime_ns


def pack(path: Path | str, kind: Optional[str] = None) -> PackReport:
    """Move a record file's plain content into ``X.gz`` (module docstring) and delete the plain file.

    Refused (nothing changed): a name not in :data:`KINDS` with no ``kind``; a plain file another session
    holds locked; a plain file that changed while it was read; a new ``.gz`` that does not decompress to
    exactly the content read (old ``.gz`` content then the plain bytes, for a log).  The new ``.gz`` is
    written beside the old one and renamed into place only after that check, so a refusal leaves both files
    as they were.  A log whose plain file starts with the whole ``.gz`` content is refused too: it reads
    twice, and packing would keep it so.  ``nothing``: no plain file, or an empty one."""
    p = plain_path(path)
    k = _kind(p, kind)
    g = gz_path(p)
    rep = PackReport(path=str(p), kind=k, action="refused")
    if k is None:
        rep.reason = f"not a record file this module knows ({', '.join(sorted(KINDS))})"
        return rep
    rep.gz_bytes_before = rep.gz_bytes_after = g.stat().st_size if g.exists() else 0
    if not p.exists():
        rep.action, rep.reason = "nothing", "no plain file"
        return rep
    with open(p, "rb") as fh:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError:
            rep.reason = "another session holds the file locked (a live run): pack it after the run ends"
            return rep
        before = _stat_key(p)
        tail = fh.read()
        rep.plain_bytes = len(tail)
        if not tail:
            rep.action, rep.reason = "nothing", "the plain file is empty"
            return rep
        old_gz = g.read_bytes() if (k == LOG and g.exists()) else b""
        head = gzip.decompress(old_gz) if old_gz else b""
        if head and tail.startswith(head):
            rep.reason = ("the plain file starts with the whole .gz content (an interrupted whole rewrite, or a "
                          "plain copy kept beside the .gz): the log reads it twice; check the plain file is "
                          "complete, delete the .gz, then pack")
            return rep
        if head and head.endswith(tail):
            rep.reason = ("the .gz already ends with the plain file's content (a pack interrupted between its rename "
                          "and the plain file's deletion): the log reads it twice; check, delete the plain file, "
                          "then pack")
            return rep
        expected = head + tail
        new_gz = old_gz + _gzip_member(tail)
        tmp = g.with_name(f".{g.name}.packing.{os.getpid()}")
        try:
            with open(tmp, "wb") as out:
                out.write(new_gz)
                out.flush()
                os.fsync(out.fileno())
            if gzip.decompress(tmp.read_bytes()) != expected:
                rep.reason = "verification failed: the new .gz does not decompress to the content read"
                return rep
            if _stat_key(p) != before:
                rep.reason = "the plain file changed while it was packed (a live run?): try again after it ends"
                return rep
            os.replace(tmp, g)
        finally:
            if tmp.exists():
                tmp.unlink()
        p.unlink()
    rep.action, rep.gz_bytes_after = "packed", g.stat().st_size
    return rep
