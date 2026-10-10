"""Fetch the sweep's sources into ``data/external/alignment_sweep/`` and record what was fetched.

:func:`fetch_all` downloads each source (default :data:`.sources.DEFAULT_FETCH`; ``only`` names others) to
``<dest>.part`` and renames it into place, then records an entry: the file, URL, size, sha256, UTC time, the
version label (in chunk ids) and pin (the Model Spec's commit; for a page with no printed version, ``captured
<date>, sha256 <hash>``), and the licence as the source table states it (``license``, ``license_line``,
``license_verified_at``) beside the licence line found in what was fetched (``license_line_found``: the first two
lines of the repository's LICENSE file, or the page's sentence naming the licence).  The entries go to
``FETCH_MANIFEST.json`` beside the files (git-ignored) and to the tracked
``data/candidates/alignment_sweep/sources_manifest.json``.  A file already on disk whose sha256 the previous manifest
records is not fetched again unless ``force``.

A source with ``store`` false (the Krakovna list) is never written: :func:`fetch_all` refuses it, and
:func:`fetch_transient` returns its text to the caller (``extract --variant B``) without touching the disk.

No paid API.
"""
from __future__ import annotations

import hashlib
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

from . import EXTERNAL_DIR, FETCH_MANIFEST_NAME, SOURCES_MANIFEST_PATH
from .chunk import html_table_to_tsv, html_to_markdown
from .sources import DEFAULT_FETCH, SOURCES as _SOURCES, Source

Fetcher = Callable[[str], bytes]
TOOL = "alignment_sweep.py fetch"
USER_AGENT = "Mozilla/5.0 (compatible; assistant-axis alignment sweep; research use)"


def _urlopen_bytes(url: str, *, timeout: float = 120.0, attempts: int = 4) -> bytes:
    """GET ``url``; a short read or a dropped connection is retried (``attempts`` in all)."""
    last: Optional[Exception] = None
    for i in range(attempts):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https URLs
                return resp.read()
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last!r}")


@dataclass
class FetchManifest:
    entries: list = field(default_factory=list)
    written: list = field(default_factory=list)
    fetched: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    dry_run_lines: list = field(default_factory=list)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _rel(path: Path) -> str:
    """Repository-relative path when the path is spelt under the repository (``data/external`` may be a
    symlink, so the unresolved spelling is tried first), else the path as given."""
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


def load_manifest(path: Path) -> list:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def write_manifest(entries: list, path: Path) -> Path:
    atomic_write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", Path(path))
    return Path(path)


def licence_sentence(text: str, needle: str) -> Optional[str]:
    """The first sentence of ``text`` that contains ``needle`` (whitespace collapsed), or None."""
    flat = " ".join(text.split())
    for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z‘“\"'])", flat):
        if needle in sent:
            return sent.strip()
    return None


def licence_line_found(s: Source, data: bytes, fetcher: Fetcher) -> Optional[str]:
    """The licence statement in what was fetched: the first two non-empty lines of the repository's LICENSE file
    (``license_file_url``), or the page's sentence naming the licence (an HTML source with a licence)."""
    if s.license_file_url:
        lines = [l.strip() for l in fetcher(s.license_file_url).decode("utf-8", "replace").splitlines() if l.strip()]
        return " / ".join(lines[:2]) or None
    if s.fmt == "html" and s.license:
        needle = s.license.split()[0]                       # "CC0", "CC"
        return licence_sentence(html_to_markdown(data.decode("utf-8", "replace")), needle)
    return None


def _entry(s: Source, dest: Path, data_sha: str, size: int, *, now: str, git_sha: Optional[str],
           found: Optional[str]) -> dict:
    label = s.version_label or now[:10]
    pin = s.version_pin or f"captured {now[:10]}, sha256 {data_sha[:12]}"
    return {"key": s.key, "name": s.name, "file": _rel(dest), "url": s.url, "page_url": s.page_url, "kind": s.kind,
            "fmt": s.fmt, "variant": s.variant, "size_bytes": size, "sha256": data_sha, "fetched_at": now,
            "version_label": label, "version_pin": pin, "license": s.license, "license_url": s.license_url,
            "license_line": s.license_line, "license_line_found": found, "license_verified_at": s.license_verified_at,
            "read_only": s.read_only, "weight": s.weight, "citation": s.citation, "tool": TOOL, "git_sha": git_sha}


def fetch_all(*, only: Optional[Iterable[str]] = None, force: bool = False, fetcher: Fetcher = _urlopen_bytes,
              dry_run: bool = False, dest_root: Path = EXTERNAL_DIR,
              sources_manifest_path: Optional[Path] = SOURCES_MANIFEST_PATH, now: Optional[str] = None,
              git_sha: Optional[str] = None, sources: Optional[Mapping[str, Source]] = None) -> FetchManifest:
    """Download, record and manifest the sources (see the module docstring)."""
    SOURCES = sources if sources is not None else _SOURCES  # noqa: N806
    keys = list(only) if only else list(DEFAULT_FETCH)
    unknown = [k for k in keys if k not in SOURCES]
    if unknown:
        raise KeyError(f"unknown source key(s): {', '.join(unknown)} (known: {', '.join(SOURCES)})")
    never = [k for k in keys if not SOURCES[k].store]
    if never:
        raise ValueError(f"{', '.join(never)}: never stored in the repository (no licence); read transiently by "
                         f"`extract --variant B` (fetch_transient)")
    out = FetchManifest()
    dest_root = Path(dest_root)
    if dry_run:
        for k in keys:
            s = SOURCES[k]
            out.dry_run_lines.append(f"{k}: {s.url} -> {dest_root / s.dest_name} ({s.license or 'no licence'}"
                                     f"{', read-only' if s.read_only else ''}; pin {s.version_pin or 'capture date'})")
        return out
    now = now or utc_now()
    manifest_path = dest_root / FETCH_MANIFEST_NAME
    previous = {e["key"]: e for e in load_manifest(manifest_path)}
    entries = dict(previous)
    for k in keys:
        s = SOURCES[k]
        dest = dest_root / s.dest_name
        prev = previous.get(k)
        if dest.exists() and not force and prev and prev.get("sha256") == _sha256(dest.read_bytes()):
            out.skipped.append(k)
            continue
        data = fetcher(s.url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(data)
        part.replace(dest)
        found = licence_line_found(s, data, fetcher)
        entries[k] = _entry(s, dest, _sha256(data), len(data), now=now, git_sha=git_sha, found=found)
        out.fetched.append(k)
        out.written.append(dest)
    order = list(SOURCES)
    out.entries = sorted(entries.values(), key=lambda e: order.index(e["key"]) if e["key"] in order else 99)
    out.written.append(write_manifest(out.entries, manifest_path))
    if sources_manifest_path is not None:
        out.written.append(write_manifest(out.entries, sources_manifest_path))
    return out


def fetch_transient(key: str, *, fetcher: Fetcher = _urlopen_bytes) -> str:
    """The text of a never-stored source, read and returned without writing anything: for a published sheet,
    the landing page's first ``docs.google.com/spreadsheets`` link is followed and its table returned as
    tab-separated lines."""
    s = _SOURCES[key]
    if s.store:
        raise ValueError(f"{key} is stored by fetch_all; fetch_transient is for never-stored sources")
    raw = fetcher(s.url).decode("utf-8", "replace")
    if s.fmt != "sheet_html":
        return raw
    m = re.search(r'href="(https://docs\.google\.com/spreadsheets/[^"]+)"', raw)
    if not m:
        raise RuntimeError(f"{key}: no published-sheet link on {s.url}")
    url = m.group(1).replace("&amp;", "&")
    if "/pubhtml" not in url and "/edit" in url:
        url = url.split("/edit")[0] + "/pubhtml"
    return html_table_to_tsv(fetcher(url).decode("utf-8", "replace"))


__all__ = ["FetchManifest", "fetch_all", "fetch_transient", "load_manifest", "write_manifest", "licence_sentence",
           "licence_line_found", "TOOL"]
