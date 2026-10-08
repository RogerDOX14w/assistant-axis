"""Fetch the census files, verify them against the published hashes, record a manifest.

``fetch_all`` writes each file to ``<dest>.part``, verifies it and renames it into place; a
mismatch on an OSF file deletes the part file and raises :class:`ChecksumError` naming both
hashes.  A Dataverse file is checked against its one published md5, first in the original
upload's form (``?format=original``), then in the ingested ``.tab`` form; ``checksum_source``
records which matched, and when neither does the file is kept with ``checksum_verified:
false`` (plan section 6; a QUESTIONS entry, then proceed).  An existing file that verifies is
not fetched again unless ``force``.

Beside each source directory a ``LICENSE.txt`` holds the licence name, URL, attribution and
the licence text; ``README.md`` in the wordlists directory lists every file with its URL,
date, size and hashes.  ``DOWNLOAD_MANIFEST.json`` (gitignored, with the downloads) and the
tracked ``data/candidates/censuses/sources_manifest.json`` carry the same list, which every
run copies into ``run.json["args"]["sources"]``.

Attribution is read from the providers' APIs (:func:`osf_node_attribution`,
:func:`dataverse_citation`), never typed.  No paid API is involved.
"""
from __future__ import annotations

import hashlib
import html
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

from . import DOWNLOAD_MANIFEST_NAME, SOURCES_MANIFEST_PATH, WORDLISTS_DIR
from .sources import (
    DEFAULT_FETCH, LICENCE_TEXT_URLS, OSF_DOI, OSF_NODE_API, OSF_NODE_URL, SKIPPED, TDA_CITATION_API, Source,
)
from .sources import SOURCES as _SOURCES

Fetcher = Callable[[str], bytes]
TOOL = "census_generator.py download"
USER_AGENT = "assistant-axis census generator (research; contact via the repository owner)"


class ChecksumError(RuntimeError):
    """A downloaded file does not match its published hash."""


@dataclass(frozen=True)
class Verification:
    sha256: str
    md5: str
    verified: bool
    checksum_source: Optional[str]


@dataclass
class DownloadManifest:
    entries: list[dict] = field(default_factory=list)
    attribution: dict = field(default_factory=dict)
    written: list[Path] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    dry_run_lines: list[str] = field(default_factory=list)


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


def _hashes(data: bytes) -> tuple[str, str]:
    return hashlib.sha256(data).hexdigest(), hashlib.md5(data).hexdigest()  # noqa: S324 - published md5


def _sha256_file(path: Path, *, chunk_size: int = 1 << 20) -> tuple[str, str]:
    """sha256 and md5 of a file, read in chunks (after ``atomic_io._sha256_file``)."""
    sha, md5 = hashlib.sha256(), hashlib.md5()  # noqa: S324
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()


def _check(sha: str, md5: str, source: Source, *, form: str) -> Verification:
    if source.provider == "osf":
        ok = (source.sha256 is None or sha == source.sha256) and (source.md5 is None or md5 == source.md5)
        ok = ok and (source.sha256 is not None or source.md5 is not None)
        return Verification(sha, md5, ok, "osf:extra.hashes" if ok else None)
    ok = source.md5 is not None and md5 == source.md5
    return Verification(sha, md5, ok, f"dataverse:md5({form})" if ok else None)


def verify_file(path: Path, source: Source) -> Verification:
    """Hash a file on disk and compare it with the source's published hashes."""
    sha, md5 = _sha256_file(path)
    return _check(sha, md5, source, form="on disk")


def osf_node_attribution(fetcher: Fetcher = _urlopen_bytes) -> dict:
    """Title and bibliographic contributors of the OSF node, as the API lists them."""
    node = json.loads(fetcher(OSF_NODE_API))["data"]["attributes"]
    contrib = json.loads(fetcher(OSF_NODE_API + "contributors/?embed=users"))["data"]
    names = []
    for c in sorted(contrib, key=lambda c: c.get("attributes", {}).get("index", 0)):
        if not c.get("attributes", {}).get("bibliographic", True):
            continue
        user = (((c.get("embeds") or {}).get("users") or {}).get("data") or {}).get("attributes") or {}
        if user.get("full_name"):
            names.append(user["full_name"])
    title = node.get("title")
    return {"title": title, "contributors": names, "url": OSF_NODE_URL, "doi": OSF_DOI,
            "attribution": f"{title} ({', '.join(names)}), {OSF_NODE_URL}"}


def dataverse_citation(fetcher: Fetcher = _urlopen_bytes) -> dict:
    """The dataset citation Dataverse generates (HTML tags stripped)."""
    msg = json.loads(fetcher(TDA_CITATION_API))["data"]["message"]
    text = html.unescape(re.sub(r"<[^>]+>", "", msg)).strip()
    return {"attribution": text, "url": "https://doi.org/10.7910/DVN/5T80PF"}


def licence_text(licence: str, fetcher: Fetcher = _urlopen_bytes) -> Optional[str]:
    """Full licence text (OSF's licence record for CC BY 4.0, the CC legalcode for CC0)."""
    url = LICENCE_TEXT_URLS.get(licence)
    if not url:
        return None
    raw = fetcher(url)
    if "api.osf.io" in url:
        return json.loads(raw)["data"]["attributes"]["text"]
    return raw.decode("utf-8")


def _rel(path: Path) -> str:
    """Repository-relative path when the path is spelt under the repository (``data/external`` may
    be a symlink, so the unresolved spelling is tried first), else the path as given."""
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


def load_manifest(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_manifest(entries: list[dict], path: Path) -> Path:
    atomic_write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", path)
    return Path(path)


def _entry(source: Source, dest: Path, v: Verification, attribution: str, *, size: int, now: str,
           git_sha: Optional[str], form: Optional[str]) -> dict:
    return {"key": source.key, "file": _rel(dest), "url": source.url, "form": form, "size_bytes": size,
            "sha256": v.sha256, "md5": v.md5, "sha256_published": source.sha256, "md5_published": source.md5,
            "checksum_verified": v.verified, "checksum_source": v.checksum_source, "licence": source.licence,
            "licence_url": source.licence_url, "attribution": attribution, "doi": source.doi,
            "version": source.version, "column": source.column, "downloaded_at": now, "tool": TOOL,
            "git_sha": git_sha}


def _write_verified(data: bytes, dest: Path, source: Source, *, form: str) -> Verification:
    """``<dest>.part`` -> verify -> rename.  OSF mismatch: delete the part, raise."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(data)
    sha, md5 = _sha256_file(part)
    v = _check(sha, md5, source, form=form)
    if not v.verified and source.provider == "osf":
        part.unlink()
        raise ChecksumError(f"{source.key}: {source.url} gave sha256 {sha} / md5 {md5}, published sha256 "
                            f"{source.sha256} / md5 {source.md5}; nothing written")
    part.replace(dest)
    return v


def _fetch_one(source: Source, dest: Path, fetcher: Fetcher) -> tuple[Verification, Optional[str], int]:
    data = fetcher(source.url)
    if source.provider == "osf":
        return _write_verified(data, dest, source, form="file"), "file", len(data)
    form = "format=original" if source.alt_url else "file"
    v = _check(*_hashes(data), source, form=form)
    if not v.verified and source.alt_url:
        alt = fetcher(source.alt_url)
        va = _check(*_hashes(alt), source, form="tab")
        if va.verified:
            return _write_verified(alt, dest, source, form="tab"), "tab", len(alt)
    return _write_verified(data, dest, source, form=form), form, len(data)


def _needs_frequencies(dest_root: Path) -> bool:
    p = dest_root / _SOURCES["tda_properties"].dest
    if not p.exists():
        return False
    header = p.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
    return not header or "gbooks.freq" not in header[0]


def render_readme(entries: list[dict], *, dest_root: Path) -> str:
    lines = ["# Census word lists (downloaded by `census_generator.py download`)", "",
             "Written by `assistant_axis/gapgen/generators/censuses/download.py`; regenerated on every "
             "download.  This directory is git-ignored (`/data/external/`); the tracked copy of the "
             "manifest is `data/candidates/censuses/sources_manifest.json`.", "",
             "| key | file | URL | downloaded (UTC) | bytes | sha256 | md5 | verified | licence | attribution |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for e in entries:
        lines.append(f"| {e['key']} | {'/'.join(Path(e['file']).parts[-2:])} "
                     f"| {e['url']} | {e['downloaded_at']} | {e['size_bytes']} | `{e['sha256']}` | `{e['md5']}` "
                     f"| {e['checksum_source'] if e['checksum_verified'] else 'NOT VERIFIED'} | "
                     f"[{e['licence']}]({e['licence_url']}) | {e['attribution']} |")
    lines += ["", "Original works: Allport, G. W., & Odbert, H. S. (1936). Trait-names: A psycho-lexical study. "
              "Psychological Monographs, 47(1), i-171 (the OSF files are a transcription of its four columns).  "
              "The TDA is described in the dataset's `Data Description.pdf`.", "",
              "Not downloaded, on purpose:", ""]
    lines += [f"- `{k}`: {v}" for k, v in SKIPPED.items()]
    return "\n".join(lines) + "\n"


def _licence_file(directory: Path, source: Source, attribution: str, fetcher: Fetcher, *, now: str,
                  force: bool) -> Optional[Path]:
    path = directory / "LICENSE.txt"
    if path.exists() and not force:
        return None
    try:
        text = licence_text(source.licence, fetcher)
        note = f"Licence text retrieved {now} from {LICENCE_TEXT_URLS.get(source.licence)}."
    except Exception as exc:  # noqa: BLE001 - the header alone still names the licence
        text, note = None, f"Licence text could not be retrieved ({type(exc).__name__}); see {source.licence_url}."
    head = [f"Licence: {source.licence} ({source.licence_url})", f"Attribution: {attribution}",
            f"Source: {OSF_NODE_URL if source.provider == 'osf' else 'https://doi.org/' + str(source.doi)}",
            f"Files in this directory were downloaded unmodified on {now[:10]} by {TOOL}.", note, "", ""]
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_text("\n".join(head) + (text or "") + ("\n" if text and not text.endswith("\n") else ""), path)
    return path


def fetch_all(*, dest_root: Path = WORDLISTS_DIR, only: Optional[Iterable[str]] = None, force: bool = False,
              fetcher: Fetcher = _urlopen_bytes, dry_run: bool = False, now: Optional[str] = None,
              git_sha: Optional[str] = None, sources_manifest_path: Optional[Path] = SOURCES_MANIFEST_PATH,
              sources: Optional[Mapping[str, Source]] = None) -> DownloadManifest:
    """Download, verify and record the census files (see the module docstring).  ``sources``
    replaces :data:`~.sources.SOURCES` (tests)."""
    SOURCES = sources if sources is not None else _SOURCES  # noqa: N806
    dest_root = Path(dest_root)
    now = now or utc_now()
    if only:
        keys = list(only)
    elif sources is None:
        keys = list(DEFAULT_FETCH)
    else:
        keys = [k for k, src in SOURCES.items() if not src.optional]
    unknown = [k for k in keys if k not in SOURCES]
    if unknown:
        raise KeyError(f"unknown source key(s): {', '.join(unknown)} (known: {', '.join(SOURCES)})")
    out = DownloadManifest()
    if dry_run:
        for k in keys:
            s = SOURCES[k]
            out.dry_run_lines.append(f"{k}: {s.url} -> {dest_root / s.dest} (sha256 {s.sha256}, md5 {s.md5}, "
                                     f"{s.licence})")
        return out
    manifest_path = dest_root / DOWNLOAD_MANIFEST_NAME
    previous = {e["key"]: e for e in load_manifest(manifest_path)}
    attribution: dict[str, str] = {}

    def attribution_for(s: Source) -> str:
        if s.provider not in attribution:
            info = osf_node_attribution(fetcher) if s.provider == "osf" else dataverse_citation(fetcher)
            out.attribution[s.provider] = info
            attribution[s.provider] = info["attribution"]
        return attribution[s.provider]

    entries = {k: e for k, e in previous.items()}
    i = 0
    while i < len(keys):
        k = keys[i]
        i += 1
        s = SOURCES[k]
        dest = dest_root / s.dest
        if dest.exists() and not force:
            v = verify_file(dest, s)
            if v.verified:
                prev = previous.get(k)
                if prev and prev.get("sha256") == v.sha256:
                    entries[k] = prev
                else:
                    entries[k] = _entry(s, dest, v, attribution_for(s), size=dest.stat().st_size, now=now,
                                        git_sha=git_sha, form=None)
                out.skipped.append(k)
                continue
        v, form, size = _fetch_one(s, dest, fetcher)
        out.fetched.append(k)
        entries[k] = _entry(s, dest, v, attribution_for(s), size=size, now=now, git_sha=git_sha, form=form)
        lic = _licence_file(dest.parent, s, attribution_for(s), fetcher, now=now, force=force)
        if lic:
            out.written.append(lic)
        if (k == "tda_properties" and only is None and "tda_frequencies" in SOURCES
                and "tda_frequencies" not in keys and _needs_frequencies(dest_root)):
            keys.append("tda_frequencies")
    order = list(SOURCES)
    out.entries = sorted(entries.values(), key=lambda e: order.index(e["key"]) if e["key"] in order else 99)
    out.written.append(write_manifest(out.entries, manifest_path))
    if sources_manifest_path is not None:
        out.written.append(write_manifest(out.entries, sources_manifest_path))
    readme = dest_root / "README.md"
    atomic_write_text(render_readme(out.entries, dest_root=dest_root), readme)
    out.written.append(readme)
    return out
