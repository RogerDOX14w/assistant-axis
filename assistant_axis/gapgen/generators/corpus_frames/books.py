"""The Google Books n-grams: locating each frame's shards, streaming them once, keeping the matching lines.

The v3 English n-grams (20200217) are 6,881 gzipped 3-gram **shards** and 6,668 4-gram shards in a public bucket
(:data:`BASE_URL`; CC BY 3.0), *measured* 0.47-0.56 GB each.  Each line is ``ngram TAB year,match,volumes TAB ...``
(every year of one n-gram on one line), and the shards are **globally sorted by the n-gram string in byte order**,
so a frame with a fixed prefix occupies a contiguous run of shards, and an untagged block (``very ...``) precedes its
tagged forms (``very_ADJ ...``): the block of prefix ``very `` is exactly the keys in ``["very ", "very \\x7f")``.

* :func:`locate` finds a prefix's run by **head-peeking**: a 4 KB range request per probed shard, decompressing only
  its first line (:func:`head_ngram`), in a binary search for the first shard and a galloping search for the last
  (about 13 + 2 requests a prefix; :class:`Heads` caches every head, so frames sharing a prefix share the peeks).
* :func:`shard_plan` lists every shard the frames need **once**, the frames each serves, and its size from a HEAD
  request (``Content-Length``): ``locate`` prints the shard count and GB before anything streams.
* :func:`stream_shard` reads one shard as a stream (gzip over the HTTP response, one pass, never stored), applies
  every frame's regex (:func:`.frames.regex_for`) to the lines starting with one of its prefixes, and returns the
  **kept lines** and the hits summed over years >= ``year_min`` (1920, Roger 2026-10-13).  A kept line is
  **compacted to decade sums** (:func:`decade_line`: ``ngram TAB 1920,match,volumes TAB 1930,...``, the decade's
  start as its year), in the n-grams' own format: a common 3-gram carries 150 or more year triples, and the plan's
  extracts are "tens of MB" (Roger is short of disk), while decade sums keep any decade-start cutoff exact (1920
  included; a cutoff inside a decade counts from the next decade).
* :func:`run_stream` streams a plan, ``parallel`` shards at a time: **refused** (:class:`NotApproved`, the IPIP rule)
  before any request unless ``approved_by`` names Roger's go; each shard's kept lines go to
  ``parts/<n>-<index>/<frame_id>.tsv`` with a ``done.json`` marker written last (``resume`` skips a shard whose marker
  covers its frames; a shard already done is refused without ``resume`` or ``force``, so that 27 GB is never
  re-streamed by accident); then the per-frame extracts ``<frame_id>.tsv`` (the kept lines in decade sums, so the
  cutoff can move by decades without a new stream) and ``DOWNLOAD_MANIFEST.json`` (bytes streamed per shard, lines
  scanned and kept, the sha256 of every extract, the approval, the licence), copied to the tracked sources manifest.
  **Every kept line is on disk twice**: in its shard's part (kept for ``--resume`` and for reassembling a frame when a
  later tier streams a shard it shares) and in the assembled extract, so the extracts take about twice their own size.

The background frequency is ``wordfreq``'s Zipf (``gapgen.freq``), never the Books 1-grams (plan section 1).  No
paid API is involved; every network call goes through a :class:`Fetcher`, which the tests replace.
"""
from __future__ import annotations

import gzip
import hashlib
import http.client
import json
import threading
import time
import urllib.error
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import BinaryIO, Callable, Iterable, Mapping, Optional, Protocol, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.registry import utc_now

from ..ipip.download import NotApproved
from . import DOWNLOAD_MANIFEST_NAME, EXTERNAL_DIR
from .frames import Frame, bank_sha256, regex_for

BASE_URL = "https://storage.googleapis.com/books/ngrams/books/20200217/eng/"
N_SHARDS: dict[int, int] = {3: 6881, 4: 6668}
SOURCE_ID = "google_books_ngrams_v3_20200217_eng"
LICENCE = "CC BY 3.0 (Creative Commons Attribution 3.0 Unported; the Google Books Ngram Viewer datasets page)"
LICENCE_URL = "https://creativecommons.org/licenses/by/3.0/"
DATASET_URL = "https://storage.googleapis.com/books/ngrams/books/datasetsv3.html"
CITATION = ("Google Books Ngram Viewer, version 3 (20200217), English: Michel et al., Quantitative analysis of "
            "culture using millions of digitized books, Science 331 (2011); https://books.google.com/ngrams")
#: The year cutoff (Roger, 2026-10-13: "Maybe 1920?"): a filler's counts are summed over years >= this.
YEAR_MIN = 1920
HEAD_PEEK_BYTES = 4096
HEAD_PEEK_MAX_BYTES = 65536
#: Closes an untagged block: every key starting with the prefix and a lowercase letter or a space sorts below it,
#: every ``prefix_TAG`` form above it.
END_SENTINEL = "\x7f"
TOOL = "corpus_frames_generator.py stream"
USER_AGENT = "assistant-axis corpus-frames generator (research; contact via the repository owner)"
PARTS_DIRNAME = "parts"
DONE_NAME = "done.json"
SHARD_ATTEMPTS = 3


def shard_url(n: int, index: int, *, base_url: str = BASE_URL, n_shards: Optional[Mapping[int, int]] = None) -> str:
    total = (n_shards or N_SHARDS)[n]
    return f"{base_url}{n}-{index:05d}-of-{total:05d}.gz"


def shard_name(n: int, index: int) -> str:
    return f"{n}-{index:05d}"


# --------------------------------------------------------------------------- the network seam

class Fetcher(Protocol):
    """What the module asks of the network (tests pass a fake)."""
    def range(self, url: str, start: int, end: int) -> bytes: ...
    def size(self, url: str) -> int: ...
    def stream(self, url: str) -> BinaryIO: ...


class HttpFetcher:  # pragma: no cover - the network
    """The real fetcher: ``urllib`` through the environment's proxy settings, retried on a dropped connection."""

    def __init__(self, *, timeout: float = 120.0, attempts: int = 4):
        self.timeout, self.attempts = timeout, attempts
        self._lock = threading.Lock()
        self.bytes_fetched = 0
        self.n_requests = 0

    def _count(self, n: int) -> None:
        with self._lock:
            self.bytes_fetched += n
            self.n_requests += 1

    def _retry(self, fn):
        last = None
        for i in range(self.attempts):
            try:
                return fn()
            except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
                last = exc
                time.sleep(1.5 * (i + 1))
        raise RuntimeError(f"request failed after {self.attempts} attempts: {last!r}")

    def range(self, url: str, start: int, end: int) -> bytes:
        def go():
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Range": f"bytes={start}-{end}"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 - fixed https URLs
                data = resp.read(end - start + 1)
            self._count(len(data))
            return data
        return self._retry(go)

    def size(self, url: str) -> int:
        def go():
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                n = int(resp.headers.get("Content-Length") or 0)
            self._count(0)
            return n
        return self._retry(go)

    def stream(self, url: str) -> BinaryIO:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        self._count(0)
        return self._retry(lambda: urllib.request.urlopen(req, timeout=self.timeout))  # noqa: S310


# --------------------------------------------------------------------------- head-peeking and locate

def first_ngram(gz_prefix: bytes) -> Optional[str]:
    """The first line's n-gram (the text before its first tab) from the start of a gzip file, or None when the bytes
    given do not decompress as far as the first tab."""
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = d.decompress(gz_prefix)
    except zlib.error:
        return None
    for sep in (b"\t", b"\n"):
        i = out.find(sep)
        if i >= 0:
            return out[:i].decode("utf-8", errors="replace")
    return None


def head_ngram(n: int, index: int, *, fetch: Fetcher, peek: int = HEAD_PEEK_BYTES, base_url: str = BASE_URL,
               n_shards: Optional[Mapping[int, int]] = None) -> tuple[str, int]:
    """``(the first n-gram of shard <n>-<index>, bytes fetched)``: a ``peek``-byte range request, widened (x4, up to
    :data:`HEAD_PEEK_MAX_BYTES`) when the first line does not fit."""
    url = shard_url(n, index, base_url=base_url, n_shards=n_shards)
    got = 0
    size = peek
    while True:
        data = fetch.range(url, 0, size - 1)
        got += len(data)
        head = first_ngram(data)
        if head is not None:
            return head, got
        if size >= HEAD_PEEK_MAX_BYTES or len(data) < size:
            raise RuntimeError(f"{url}: no first line in the first {size} bytes")
        size *= 4


class Heads:
    """Shard heads, fetched on first use and cached (frames sharing a prefix share the peeks)."""

    def __init__(self, fetch: Fetcher, *, peek: int = HEAD_PEEK_BYTES, base_url: str = BASE_URL,
                 n_shards: Optional[Mapping[int, int]] = None):
        self.fetch, self.peek, self.base_url = fetch, peek, base_url
        self.n_shards = dict(n_shards or N_SHARDS)
        self.cache: dict[tuple[int, int], str] = {}
        self.n_peeks = 0
        self.peek_bytes = 0

    def __call__(self, n: int, index: int) -> str:
        k = (n, index)
        if k not in self.cache:
            head, got = head_ngram(n, index, fetch=self.fetch, peek=self.peek, base_url=self.base_url,
                                   n_shards=self.n_shards)
            self.cache[k] = head
            self.n_peeks += 1
            self.peek_bytes += got
        return self.cache[k]


def _last_at_or_below(heads: Heads, n: int, lo: int, hi: int, key: str, *, strict: bool) -> int:
    """The largest ``i`` in ``[lo, hi]`` whose head is ``<= key`` (``< key`` when ``strict``); ``lo`` when none is."""
    def ok(i: int) -> bool:
        h = heads(n, i)
        return h < key if strict else h <= key
    if not ok(lo):
        return lo
    a, b = lo, hi
    while a < b:
        mid = (a + b + 1) // 2
        if ok(mid):
            a = mid
        else:
            b = mid - 1
    return a


def _gallop_last_below(heads: Heads, n: int, lo: int, hi: int, key: str) -> int:
    """The largest ``i >= lo`` whose head is ``< key``, galloping from ``lo`` (a block spans one or two shards, so
    this costs two or three peeks rather than a full binary search)."""
    i, step = lo, 1
    while i + step <= hi and heads(n, i + step) < key:
        i += step
        step *= 2
    return _last_at_or_below(heads, n, i, min(i + step, hi), key, strict=True)


@dataclass(frozen=True)
class Span:
    n: int
    key: str
    start: int
    end: int


def locate(n: int, key: str, *, heads: Heads) -> Span:
    """The shards ``start..end`` (inclusive) holding the untagged block of prefix ``key`` (``"very "``): the first is
    the last shard whose head sorts at or below ``key``; the last is **one past** the last shard whose head sorts below
    ``key + "\\x7f"``.

    Why one past (measured 2026-10-17, the first live stream): each shard holds a contiguous key range, but its lines
    are **not sorted** inside it (about half of adjacent pairs are in order, as for random order), so a shard's head
    is just some line of its range, not its first.  A key between two heads can therefore sit in either shard, but in
    no later one: the 4-gram frames "he is always" and "known for his" found nothing in the shard located for them,
    and "he is always" lines are in the next one.  The ``_TAG`` forms interleave with the untagged ones for the same
    reason; the frame's regex, not the span, leaves them out."""
    total = heads.n_shards[n]
    start = _last_at_or_below(heads, n, 0, total - 1, key, strict=False)
    end = _gallop_last_below(heads, n, start, total - 1, key + END_SENTINEL)
    return Span(n=n, key=key, start=start, end=min(total - 1, max(start, end) + 1))


# --------------------------------------------------------------------------- the shard plan

@dataclass
class ShardEntry:
    n: int
    index: int
    url: str
    bytes: int
    frames: list
    head: str

    @property
    def name(self) -> str:
        return shard_name(self.n, self.index)


@dataclass
class ShardPlan:
    tier: str
    bank_sha256: str
    shards: list
    frame_spans: dict
    n_shards: int
    total_bytes: int
    total_gb: float
    head_peek_bytes: int
    n_head_peeks: int
    n_head_requests: int
    approval: Optional[str] = None
    made_at: Optional[str] = None
    base_url: str = BASE_URL

    def as_dict(self) -> dict:
        d = asdict(self)
        d["shards"] = [asdict(s) if isinstance(s, ShardEntry) else dict(s) for s in self.shards]
        return d

    @classmethod
    def from_dict(cls, d: Mapping) -> "ShardPlan":
        d = dict(d.get("result", d))
        d["shards"] = [ShardEntry(**s) for s in d.get("shards") or []]
        return cls(**{k: d.get(k) for k in cls.__dataclass_fields__ if k in d})

    def frames(self) -> list[str]:
        return sorted({f for s in self.shards for f in s.frames})


def shard_plan(frames: Sequence[Frame], *, fetch: Fetcher, tier: str = "all", heads: Optional[Heads] = None,
               base_url: str = BASE_URL, n_shards: Optional[Mapping[int, int]] = None,
               now: Optional[str] = None) -> ShardPlan:
    """Every shard ``frames`` need, once, with the frames it serves and its size (HEAD ``Content-Length``)."""
    heads = heads or Heads(fetch, base_url=base_url, n_shards=n_shards)
    spans: dict[tuple[int, str], Span] = {}
    frame_spans: dict[str, dict] = {}
    for f in sorted(frames, key=lambda f: (f.n, f.key, f.id)):
        k = (f.n, f.key)
        if k not in spans:
            spans[k] = locate(f.n, f.key, heads=heads)
        sp = spans[k]
        frame_spans[f.id] = {"n": sp.n, "key": sp.key, "start": sp.start, "end": sp.end}
    serves: dict[tuple[int, int], set] = {}
    for fid, sp in frame_spans.items():
        for i in range(sp["start"], sp["end"] + 1):
            serves.setdefault((sp["n"], i), set()).add(fid)
    entries = []
    for (n, i) in sorted(serves):
        url = shard_url(n, i, base_url=base_url, n_shards=heads.n_shards)
        entries.append(ShardEntry(n=n, index=i, url=url, bytes=int(fetch.size(url)), frames=sorted(serves[(n, i)]),
                                  head=heads(n, i)))
    total = sum(e.bytes for e in entries)
    return ShardPlan(tier=str(tier), bank_sha256=bank_sha256(), shards=entries, frame_spans=dict(sorted(
        frame_spans.items())), n_shards=len(entries), total_bytes=total, total_gb=round(total / 1e9, 2),
        head_peek_bytes=heads.peek_bytes, n_head_peeks=heads.n_peeks, n_head_requests=len(entries),
        made_at=now or utc_now(), base_url=base_url)


# --------------------------------------------------------------------------- streaming one shard

@dataclass(frozen=True)
class Hit:
    filler: str
    noun: Optional[str]
    match: int
    volumes: int
    example: Optional[str] = None


def parse_counts(fields: Iterable[str], *, year_min: int = YEAR_MIN) -> tuple[int, int]:
    """``(match, volumes)`` summed over the ``year,match,volumes`` fields of years >= ``year_min``."""
    m = v = 0
    for f in fields:
        parts = f.split(",")
        if len(parts) != 3:
            continue
        try:
            y, mm, vv = int(parts[0]), int(parts[1]), int(parts[2])
        except ValueError:
            continue
        if y >= year_min:
            m += mm
            v += vv
    return m, v


def decade_line(line: str) -> str:
    """A Books line with its ``year,match,volumes`` fields summed per decade (the decade's start as its year, decades
    in order): the extract's form (module docstring).  Fields that do not parse are dropped."""
    parts = line.rstrip("\n").split("\t")
    acc: dict[int, list] = {}
    for f in parts[1:]:
        xs = f.split(",")
        if len(xs) != 3:
            continue
        try:
            y, m, v = int(xs[0]), int(xs[1]), int(xs[2])
        except ValueError:
            continue
        a = acc.setdefault(y - y % 10, [0, 0])
        a[0] += m
        a[1] += v
    return "\t".join([parts[0]] + [f"{d},{m},{v}" for d, (m, v) in sorted(acc.items())])


def line_hit(line: str, frame: Frame, *, year_min: int = YEAR_MIN) -> Optional[Hit]:
    """The hit of one Books line in ``frame`` (None when the line is not the frame's), counts over years >=
    ``year_min`` (a hit with zero counts is still returned: it matched, but adds nothing)."""
    mo = regex_for(frame).match(line)
    if not mo:
        return None
    m, v = parse_counts(line.rstrip("\n").split("\t")[1:], year_min=year_min)
    return Hit(filler=mo.group("filler"), noun=mo.groupdict().get("noun"), match=m, volumes=v)


def aggregate(hits: Iterable[Hit]) -> list[Hit]:
    """Hits summed per ``(filler, noun)``, sorted."""
    acc: dict[tuple, list] = {}
    for h in hits:
        a = acc.setdefault((h.filler, h.noun), [0, 0, h.example])
        a[0] += h.match
        a[1] += h.volumes
        if a[2] is None and h.example:
            a[2] = h.example
    return [Hit(filler=f, noun=n, match=m, volumes=v, example=e) for (f, n), (m, v, e) in
            sorted(acc.items(), key=lambda kv: (kv[0][0], kv[0][1] or ""))]


class _Counting:
    """A read-through wrapper that counts the bytes read from a stream."""

    def __init__(self, raw: BinaryIO):
        self.raw, self.n = raw, 0

    def read(self, size: int = -1) -> bytes:
        b = self.raw.read(size)
        self.n += len(b)
        return b

    def readable(self) -> bool:
        return True

    def close(self) -> None:
        try:
            self.raw.close()
        except Exception:  # noqa: BLE001
            pass


@dataclass
class StreamedShard:
    url: str
    hits: dict              # frame id -> [Hit] (aggregated, counts over years >= year_min)
    lines: dict             # frame id -> [kept line] (decade sums: :func:`decade_line`)
    bytes_streamed: int
    lines_scanned: int
    seconds: float = 0.0


def stream_shard(url: str, frames: Sequence[Frame], *, fetch: Fetcher, year_min: int = YEAR_MIN) -> StreamedShard:
    """One pass over a shard (see the module docstring): every frame's regex applied to each line that starts with
    one of the frames' prefixes; the stream is read to its end (gzip's own check of the data)."""
    t0 = time.time()
    by_prefix: dict[bytes, list[Frame]] = {}
    for f in frames:
        by_prefix.setdefault(f.key.encode("utf-8"), []).append(f)
    prefixes = tuple(by_prefix)
    lines: dict[str, list[str]] = {f.id: [] for f in frames}
    hits: dict[str, list[Hit]] = {f.id: [] for f in frames}
    raw = _Counting(fetch.stream(url))
    n = 0
    try:
        with gzip.GzipFile(fileobj=raw, mode="rb") as gz:
            for b in gz:
                n += 1
                if not b.startswith(prefixes):
                    continue
                line = b.decode("utf-8", errors="replace").rstrip("\n")
                for p, fs in by_prefix.items():
                    if not b.startswith(p):
                        continue
                    for f in fs:
                        h = line_hit(line, f, year_min=year_min)
                        if h is not None:
                            lines[f.id].append(decade_line(line))
                            hits[f.id].append(h)
    finally:
        raw.close()
    return StreamedShard(url=url, hits={k: aggregate(v) for k, v in hits.items()}, lines=lines,
                         bytes_streamed=raw.n, lines_scanned=n, seconds=round(time.time() - t0, 2))


# --------------------------------------------------------------------------- extracts

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_extract(lines: Sequence[str], path: Path) -> str:
    """Write kept lines (one per line, as read) and return the file's sha256."""
    atomic_write_text("".join(line + "\n" for line in lines), Path(path))
    return sha256_file(Path(path))


def read_extract(path: Path, frame: Frame, *, year_min: int = YEAR_MIN) -> list[Hit]:
    """A frame's hits from its extract (the kept lines, counts summed over years >= ``year_min``)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                h = line_hit(line.rstrip("\n"), frame, year_min=year_min)
                if h is not None:
                    out.append(h)
    return aggregate(out)


# --------------------------------------------------------------------------- the stream

def load_manifest(path: Path) -> dict:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _write_json(doc: Mapping, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", Path(path))


def done_record(parts_dir: Path) -> Optional[dict]:
    p = Path(parts_dir) / DONE_NAME
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


@dataclass
class StreamReport:
    approved_by: Optional[str]
    planned: list = field(default_factory=list)       # shard names in the plan
    streamed: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    failed: dict = field(default_factory=dict)        # shard name -> error
    bytes_streamed: int = 0
    bytes_planned: int = 0
    extracts: dict = field(default_factory=dict)      # frame id -> {"file", "lines", "sha256"}
    manifest_path: Optional[str] = None
    dry_run_lines: list = field(default_factory=list)


def _stream_one(entry: ShardEntry, frames: Sequence[Frame], *, fetch: Fetcher, parts_dir: Path, approval: str,
                now_fn: Callable[[], str], git_sha: Optional[str], attempts: int = SHARD_ATTEMPTS) -> dict:
    last: Optional[BaseException] = None
    for _ in range(attempts):
        try:
            res = stream_shard(entry.url, frames, fetch=fetch)
            # a stream that ended early but still decompressed (a cut at a gzip member boundary) is a dropped
            # stream too: checked inside the loop, so that it is retried (review M4)
            if entry.bytes and res.bytes_streamed != entry.bytes:
                raise RuntimeError(f"{entry.name}: streamed {res.bytes_streamed} bytes, the plan's Content-Length "
                                   f"is {entry.bytes}")
            break
        except (OSError, EOFError, zlib.error, http.client.HTTPException, RuntimeError) as exc:
            # a dropped stream: start the shard again
            last = exc
    else:
        raise RuntimeError(f"{entry.name}: {last!r} (after {attempts} attempts)")
    parts_dir.mkdir(parents=True, exist_ok=True)
    shas = {}
    for f in frames:
        shas[f.id] = write_extract(res.lines[f.id], parts_dir / f"{f.id}.tsv")
    rec = {"shard": entry.name, "n": entry.n, "index": entry.index, "url": entry.url, "content_length": entry.bytes,
           "bytes_streamed": res.bytes_streamed, "lines_scanned": res.lines_scanned,
           "lines_kept": {f.id: len(res.lines[f.id]) for f in frames},
           "fillers": {f.id: len({h.filler for h in res.hits[f.id] if h.match > 0}) for f in frames},
           "frames": sorted(f.id for f in frames), "parts_sha256": shas, "seconds": res.seconds,
           "streamed_at": now_fn(), "approval": approval, "tool": TOOL, "git_sha": git_sha}
    _write_json(rec, parts_dir / DONE_NAME)       # last: the marker means every part is written
    return rec


def assemble_extracts(plan: ShardPlan, external_dir: Path) -> dict:
    """``<frame_id>.tsv`` per frame of the plan: its shards' parts concatenated in shard order (the lines stay in the
    shards' sort order).  A frame with a shard not yet done is left out.  The parts are kept: every kept line exists
    twice on disk, in ``parts/<shard>/<frame_id>.tsv`` (what ``--resume`` and a later tier's reassembly read) and in
    the assembled ``<frame_id>.tsv`` (what ``table`` reads), so the disk the extracts take is about twice their size
    (review M3)."""
    out = {}
    root = Path(external_dir)
    for fid in plan.frames():
        shards = [s for s in plan.shards if fid in s.frames]
        parts = [root / PARTS_DIRNAME / s.name / f"{fid}.tsv" for s in sorted(shards, key=lambda s: (s.n, s.index))]
        if not all(done_record(p.parent) and p.exists() for p in parts):
            continue
        lines = []
        for p in parts:
            lines.extend(x for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
        dest = root / f"{fid}.tsv"
        sha = write_extract(lines, dest)
        out[fid] = {"file": dest.name, "lines": len(lines), "sha256": sha, "shards": [s.name for s in shards]}
    return out


def manifest_doc(plan: ShardPlan, external_dir: Path, *, previous: Mapping, extracts: Mapping,
                 approvals: Sequence[str]) -> dict:
    """The download manifest: every shard done (from its ``done.json``), the extracts, the approvals, the licence."""
    root = Path(external_dir)
    shards = []
    for s in sorted(plan.shards, key=lambda s: (s.n, s.index)):
        rec = done_record(root / PARTS_DIRNAME / s.name)
        if rec:
            shards.append(rec)
    prev_appr = list(previous.get("approvals") or [])
    for a in approvals:
        if a and a not in prev_appr:
            prev_appr.append(a)
    ex = dict(previous.get("extracts") or {})
    ex.update(extracts)
    return {"tool": TOOL, "source": SOURCE_ID, "base_url": plan.base_url, "dataset_url": DATASET_URL,
            "licence": {"name": LICENCE, "url": LICENCE_URL, "citation": CITATION},
            "approvals": prev_appr, "bank_sha256": plan.bank_sha256, "plan_tier": plan.tier,
            "shards": shards, "n_shards_done": len(shards), "n_shards_planned": plan.n_shards,
            "bytes_streamed": sum(int(r.get("bytes_streamed") or 0) for r in shards),
            "bytes_planned": plan.total_bytes,
            "extracts": dict(sorted(ex.items())),
            "kept_bytes": sum((root / e["file"]).stat().st_size for e in ex.values() if (root / e["file"]).exists()),
            "note": "the shards are read as streams and discarded; only the matching lines are kept (Roger, "
                    "2026-10-14: open decision 1 (b), both tiers streamed, nothing large on disk)"}


def stale_frames(plan: ShardPlan, frames: Iterable[Frame]) -> list[str]:
    """The frames whose place in the shards the plan does not know as it is now: no span recorded, or a span located
    for another prefix (``key``) or n-gram order (``n``).  Streaming such a plan would read the wrong shards (review
    S1, 2026-10-17: a prefix edited under the same id passed the id check); an edit to a frame's note or tier changes
    the bank's sha256 only, and the shards stay right."""
    out = []
    for f in frames:
        sp = (plan.frame_spans or {}).get(f.id)
        if not sp or sp.get("key") != f.key or int(sp.get("n") or 0) != f.n:
            out.append(f.id)
    return sorted(out)


class StalePlan(SystemExit):
    """The shard plan was located for frames whose prefix or n-gram order has changed since."""


def check_plan(plan: ShardPlan, frames: Iterable[Frame]) -> None:
    """Refuse (:class:`StalePlan`) a plan with stale frames (:func:`stale_frames`), naming them."""
    stale = stale_frames(plan, frames)
    if stale:
        raise StalePlan(f"the shard plan was located for another prefix or n-gram order of {', '.join(stale)}: run "
                        f"`locate` again before streaming (the shards it lists would be the wrong ones)")


def run_stream(plan: ShardPlan, *, approved_by: Optional[str], fetch: Fetcher, frames_by_id: Mapping[str, Frame],
               external_dir: Path = EXTERNAL_DIR, resume: bool = False, force: bool = False, parallel: int = 4,
               dry_run: bool = False, git_sha: Optional[str] = None, sources_manifest_path: Optional[Path] = None,
               echo=print, now_fn: Callable[[], str] = utc_now) -> StreamReport:
    """Stream a shard plan (see the module docstring).  Refused before any request without ``approved_by`` (a dry
    run, which makes no request, prints the plan without it)."""
    if not dry_run and not (approved_by or "").strip():
        raise NotApproved("the Books stream is a download over 2 GB: run it only after Roger's go, naming it with "
                          "--approved-by '<Roger, date>' (plan 05 open decision 1; the download rule of 2026-10-10)")
    check_plan(plan, [frames_by_id[f] for f in plan.frames()])
    root = Path(external_dir)
    rep = StreamReport(approved_by=approved_by, planned=[s.name for s in plan.shards], bytes_planned=plan.total_bytes)
    todo: list[ShardEntry] = []
    already = []
    for s in plan.shards:
        rec = done_record(root / PARTS_DIRNAME / s.name)
        if rec and set(s.frames) <= set(rec.get("frames") or []):
            already.append(s)
        else:
            todo.append(s)
    if already and not (resume or force):
        raise SystemExit(f"{len(already)} of the plan's {plan.n_shards} shards are already extracted under "
                         f"{root / PARTS_DIRNAME}: pass --resume to skip them, or --force to stream them again")
    if force:
        todo, already = list(plan.shards), []
    rep.skipped = [s.name for s in already]
    gb = sum(s.bytes for s in todo) / 1e9
    if dry_run:
        rep.dry_run_lines = [f"{s.name}: {s.url} ({s.bytes / 1e9:.2f} GB) for {', '.join(s.frames)}" for s in todo]
        rep.dry_run_lines.append(f"would stream {len(todo)} shards, {gb:.2f} GB ({len(already)} already extracted, "
                                 f"skipped), keep only the matching lines under {root}")
        return rep
    echo(f"streaming {len(todo)} shards, {gb:.2f} GB, {max(1, int(parallel))} at a time; {len(already)} already "
         f"extracted")
    lock = threading.Lock()
    manifest_path = root / DOWNLOAD_MANIFEST_NAME
    previous = load_manifest(manifest_path)

    def record() -> None:
        doc = manifest_doc(plan, root, previous=previous, extracts={}, approvals=[approved_by])
        _write_json(doc, manifest_path)

    with ThreadPoolExecutor(max_workers=max(1, int(parallel))) as pool:
        futs = {pool.submit(_stream_one, s, [frames_by_id[f] for f in s.frames], fetch=fetch,
                            parts_dir=root / PARTS_DIRNAME / s.name, approval=approved_by, now_fn=now_fn,
                            git_sha=git_sha): s for s in todo}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                rec = fut.result()
            except Exception as exc:  # noqa: BLE001 - one shard's failure must not lose the others
                rep.failed[s.name] = repr(exc)
                echo(f"  FAILED {s.name}: {exc!r}")
                continue
            with lock:
                rep.streamed.append(s.name)
                rep.bytes_streamed += int(rec["bytes_streamed"])
                record()
            echo(f"  {s.name}: {rec['bytes_streamed'] / 1e9:.2f} GB, {rec['lines_scanned']:,} lines, kept "
                 + ", ".join(f"{k} {v}" for k, v in rec["lines_kept"].items()))
    rep.streamed.sort()
    rep.extracts = assemble_extracts(plan, root)
    doc = manifest_doc(plan, root, previous=previous, extracts=rep.extracts, approvals=[approved_by])
    _write_json(doc, manifest_path)
    rep.manifest_path = str(manifest_path)
    if sources_manifest_path is not None:
        update_sources_manifest(sources_manifest_path, "books", doc)
    return rep


def update_sources_manifest(path: Path, key: str, doc: Mapping) -> None:
    """Copy a download manifest into the tracked sources manifest under ``key`` (``books``, ``text``)."""
    p = Path(path)
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    if cur.get(key) == doc:
        return
    cur[key] = doc
    _write_json(dict(sorted(cur.items())), p)


def extract_paths(external_dir: Path, frame_ids: Iterable[str]) -> dict[str, Path]:
    """The extracts present for ``frame_ids`` (``<frame_id>.tsv``)."""
    root = Path(external_dir)
    return {f: root / f"{f}.tsv" for f in frame_ids if (root / f"{f}.tsv").exists()}


__all__ = ["BASE_URL", "N_SHARDS", "SOURCE_ID", "LICENCE", "LICENCE_URL", "YEAR_MIN", "HEAD_PEEK_BYTES",
           "END_SENTINEL", "Fetcher", "HttpFetcher", "shard_url", "shard_name", "first_ngram", "head_ngram", "Heads",
           "Span", "locate", "ShardEntry", "ShardPlan", "shard_plan", "Hit", "parse_counts", "line_hit", "aggregate",
           "StreamedShard", "stream_shard", "write_extract", "read_extract", "run_stream", "StreamReport",
           "stale_frames", "StalePlan", "check_plan",
           "assemble_extracts", "manifest_doc", "update_sources_manifest", "extract_paths", "NotApproved"]
