"""Fetch the IPIP pages and record what was received.

``fetch_all`` writes each page to ``<dest>.part`` and renames it into place.  IPIP publishes no hashes, so the
manifest records the sha256 and size of the bytes received, the URL, the UTC time and the tool; a later run
checks the file on disk against that record and fetches again only a file that is missing or changed (or every
file with ``force``).  The licence: IPIP's blanket public-domain statement, quoted in :mod:`.sources`; when one
of the fetched pages carries the full sentence, it is recorded verbatim with the page it came from
(:func:`find_licence_sentence`).

``DOWNLOAD_MANIFEST.json`` (git-ignored, beside the pages in ``data/external/ipip/``) and the tracked
``data/candidates/ipip/sources_manifest.json`` carry the same record; every run copies it into ``run.json``.
No paid API is involved.  The network fetch itself needed Roger's go (the file-access boundary): given
2026-10-10 for the three pages, and 2026-10-11 for IPIP's 21 per-inventory key pages, Tedone's assignment
workbook and the home page (QUESTIONS 52 option C and QUESTIONS 46).  The manifest's ``licence`` block credits
Tedone for the workbook although no licence requires it (``sources.WORKBOOK_CREDIT``).
"""
from __future__ import annotations

import hashlib
import html as _html
import http.client
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.gapgen.registry import utc_now

from . import DOWNLOAD_MANIFEST_NAME, EXTERNAL_DIR, SOURCES_MANIFEST_PATH
from .sources import DEFAULT_FETCH, LICENCE, LICENCE_QUOTE, LICENCE_URL, WORKBOOK_CREDIT, Source
from .sources import SOURCES as _SOURCES

Fetcher = Callable[[str], bytes]
TOOL = "ipip_generator.py download"
USER_AGENT = "assistant-axis IPIP generator (research; contact via the repository owner)"
HASH_SOURCE = "received bytes (IPIP publishes no hashes)"
#: The IPIP pages are a single-byte Windows encoding, not UTF-8 (QUESTIONS 49); the same constant as
#: ``ingest.PAGE_ENCODING`` (see its comment for why cp1252 and not iso-8859-1), repeated here so that this
#: module does not import the parser.
PAGE_ENCODING = "cp1252"


def _urlopen_bytes(url: str, *, timeout: float = 120.0, attempts: int = 6) -> bytes:
    """GET ``url`` whole.  A body cut short (``IncompleteRead``: on 2026-10-10 urllib received 835,315 of the item
    list's 849,217 bytes on every attempt, while curl through the same proxy received all of it) is kept, and the
    rest is asked for with a ``Range`` request (the server sends ``Accept-Ranges: bytes``) until the bytes add up
    to the first response's ``Content-Length``; a dropped connection is retried (``attempts`` requests in all)."""
    data = b""
    total: Optional[int] = None
    last: Optional[Exception] = None
    for i in range(attempts):
        headers = {"User-Agent": USER_AGENT}
        if data:
            headers["Range"] = f"bytes={len(data)}-"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https URLs
                if data and resp.status != 206:   # the server ignored the range: start again
                    data = b""
                if total is None and resp.headers.get("Content-Length") and not data:
                    total = int(resp.headers["Content-Length"])
                try:
                    data += resp.read()
                except http.client.IncompleteRead as exc:
                    data += exc.partial
                    raise
            if total is None or len(data) == total:
                return data
            last = RuntimeError(f"received {len(data)} of {total} bytes")
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = exc
        if total is not None and len(data) > total:
            raise RuntimeError(f"GET {url}: received {len(data)} bytes, more than the {total} announced")
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts ({len(data)} of {total} bytes): {last!r}")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_LICENCE_RE = re.compile(r"The items and scales are in the public domain[^.]*\.", re.IGNORECASE)


def find_licence_sentence(page_html: str) -> Optional[str]:
    """IPIP's public-domain sentence as one of its pages prints it (tags stripped, whitespace collapsed), or
    ``None`` when the page does not carry it."""
    text = " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", page_html)).split())
    m = _LICENCE_RE.search(text)
    return m.group(0) if m else None


def _rel(path: Path) -> str:
    """Repository-relative spelling when the path is under the repository (``data/external`` may be a
    symlink, so the unresolved spelling is tried first), else the path as given."""
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


@dataclass
class DownloadManifest:
    entries: list[dict] = field(default_factory=list)
    licence: dict = field(default_factory=dict)
    written: list[Path] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run_lines: list[str] = field(default_factory=list)

    def as_json(self) -> dict:
        return {"tool": TOOL, "licence": self.licence, "entries": self.entries,
                "total_bytes": sum(int(e.get("size_bytes") or 0) for e in self.entries)}


def load_manifest(path: Path) -> dict:
    """A manifest as written by :func:`fetch_all` (``{}`` when there is none)."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def write_manifest(doc: Mapping, path: Path) -> Path:
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", path)
    return Path(path)


def _entry(s: Source, dest: Path, data_sha: str, size: int, *, now: str, git_sha: Optional[str],
           approval: Optional[str]) -> dict:
    return {"key": s.key, "file": _rel(dest), "url": s.url, "size_bytes": size, "sha256": data_sha,
            "hash_source": HASH_SOURCE, "optional": s.optional, "role": s.role, "what": s.what,
            "licence": s.licence, "approval": approval, "downloaded_at": now, "tool": TOOL, "git_sha": git_sha}


class NotApproved(PermissionError):
    """A source with no recorded approval was asked for without the caller naming Roger's go."""


def _licence_record(dest_root: Path, entries: Iterable[Mapping], sources: Mapping[str, Source],
                    previous: Mapping) -> dict:
    """The licence block of the manifest.  ``verbatim`` is IPIP's public-domain sentence **as one of the fetched
    pages prints it** (QUESTIONS 46: our record of the licence was second-hand, a quote of plan 07's prose, and
    none of the three pages fetched on 2026-10-10 carried the sentence, which is why the home page is now
    fetched).  The pages are decoded cp1252 (:data:`PAGE_ENCODING`, QUESTIONS 49), and only pages are searched,
    never the workbook."""
    rec = {"name": LICENCE, "url": LICENCE_URL, "quote_from_plan": LICENCE_QUOTE,
           "verbatim": (previous or {}).get("verbatim"), "verbatim_source": (previous or {}).get("verbatim_source"),
           "verbatim_url": (previous or {}).get("verbatim_url"), "credit": WORKBOOK_CREDIT}
    order = [e for e in entries if (sources.get(e["key"]) or Source("", "", "", "")).role == "licence"]
    order += [e for e in entries if e not in order]
    for e in order:
        s = sources.get(e["key"])
        p = dest_root / s.dest if s else None
        if p is None or not p.exists() or not str(s.dest).lower().endswith((".htm", ".html", ".txt")):
            continue
        found = find_licence_sentence(p.read_bytes().decode(PAGE_ENCODING))
        if found:
            rec["verbatim"], rec["verbatim_source"], rec["verbatim_url"] = found, e["key"], s.url
            break
    return rec


def fetch_all(*, dest_root: Path = EXTERNAL_DIR, only: Optional[Iterable[str]] = None, force: bool = False,
              fetcher: Fetcher = _urlopen_bytes, dry_run: bool = False, now: Optional[str] = None,
              git_sha: Optional[str] = None, sources_manifest_path: Optional[Path] = SOURCES_MANIFEST_PATH,
              sources: Optional[Mapping[str, Source]] = None, approved_by: Optional[str] = None) -> DownloadManifest:
    """Download and record the IPIP pages (see the module docstring).  ``only`` names source keys (default
    :data:`~.sources.DEFAULT_FETCH`, every approved source); ``sources`` replaces :data:`~.sources.SOURCES`
    (tests).  A source with no recorded approval (``Source.approval is None``; none today, the workbook was
    approved on 2026-10-11) is refused with :class:`NotApproved` unless ``approved_by`` names Roger's go, which
    its manifest entry then records."""
    SOURCES = sources if sources is not None else _SOURCES  # noqa: N806
    dest_root = Path(dest_root)
    now = now or utc_now()
    keys = list(only) if only else list(DEFAULT_FETCH)
    unknown = [k for k in keys if k not in SOURCES]
    if unknown:
        raise KeyError(f"unknown source key(s): {', '.join(unknown)} (known: {', '.join(SOURCES)})")
    unapproved = [k for k in keys if SOURCES[k].approval is None and not (approved_by or "").strip()]
    if unapproved:
        raise NotApproved(f"{', '.join(unapproved)}: no approval on record for this download; fetch it only after "
                          f"Roger's go, naming it with --approved-by '<Roger, date>' (QUESTIONS 52)")
    out = DownloadManifest()
    if dry_run:
        for k in keys:
            s = SOURCES[k]
            out.dry_run_lines.append(f"{k}: {s.url} -> {dest_root / s.dest} ({s.what}; {s.licence})")
        return out
    manifest_path = dest_root / DOWNLOAD_MANIFEST_NAME
    prev_doc = load_manifest(manifest_path)
    previous = {e["key"]: e for e in prev_doc.get("entries") or []}
    entries = dict(previous)
    for k in keys:
        s = SOURCES[k]
        approval = s.approval or approved_by
        dest = dest_root / s.dest
        prev = previous.get(k)
        if dest.exists() and not force:
            on_disk = sha256_file(dest)
            if prev is None or prev.get("sha256") == on_disk:
                if prev is None:   # a page already on disk with no record: record it as it is
                    entries[k] = _entry(s, dest, on_disk, dest.stat().st_size, now=now, git_sha=git_sha,
                                        approval=approval)
                out.skipped.append(k)
                continue
        data = fetcher(s.url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(data)
        part.replace(dest)
        out.fetched.append(k)
        entries[k] = _entry(s, dest, sha256_bytes(data), len(data), now=now, git_sha=git_sha, approval=approval)
    order = list(SOURCES)
    out.entries = sorted(entries.values(), key=lambda e: order.index(e["key"]) if e["key"] in order else 99)
    out.licence = _licence_record(dest_root, out.entries, SOURCES, prev_doc.get("licence") or {})
    doc = out.as_json()
    if doc != prev_doc:
        out.written.append(write_manifest(doc, manifest_path))
    if sources_manifest_path is not None and doc != load_manifest(sources_manifest_path):
        Path(sources_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        out.written.append(write_manifest(doc, sources_manifest_path))
    return out
