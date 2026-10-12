"""Fetch the generator's datasets, verify them, record manifests (plan section 7, ``fetch``).

Nothing downloads without Roger's recorded approval (plan section 5a; ``approved_by`` is copied into every
manifest entry).  For each source:

1. the published size and hash are read first (the Hub's ``paths-info`` API for ``wiki_bio``: size and LFS
   sha256; an HTTP ``HEAD`` for O*NET: size only) and the size is printed before anything is written;
2. the licence page is read and must name the licence (``licence_verified``; a mismatch is recorded, not
   fatal, and printed loudly);
3. the file is streamed to ``<dest>.part``, hashed, checked against the published sha256 where there is one
   (a mismatch deletes the part file and raises :class:`ChecksumError`), and renamed into place;
4. ``LICENSE.txt`` (licence, attribution, citation) and ``DOWNLOAD_MANIFEST.json`` go beside the file (all
   gitignored under ``data/external/``), and the entry is merged into the tracked
   ``data/candidates/base_model/sources_manifest.json`` (no biography text: names, URLs, sizes, hashes).

The model itself is downloaded by ``setup_external.py --hf-model Qwen/Qwen3-8B-Base``; :func:`record_model`
verifies the snapshot (each safetensors blob's name is its sha256 in the Hub cache, compared with the published
LFS hash), reads its licence from the model card, and records it with Roger's delete-when-done TODO.

Downloads are plain HTTPS through :mod:`urllib` (the Hub's ``resolve`` URL for ``wiki_bio``): the ``hf_xet``
transfer backend panics inside the Claude Code sandbox ("Attempted to create a NULL object", 2026-10-10).
"""
from __future__ import annotations

import hashlib
import http.client
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.paths import DATA_EXTERNAL, REPO_ROOT, hf_cache_dir
from assistant_axis.gapgen.registry import utc_now

from . import DOWNLOAD_MANIFEST_NAME, SOURCES_MANIFEST_PATH
from .sources import DEFAULT_FETCH, LICENCE_CHECK, MODEL, SKIPPED, SOURCES, ModelSource, Source

TOOL = "base_model_generator.py fetch"
USER_AGENT = "assistant-axis base-model generator (research; contact via the repository owner)"
APPROVAL_REQUIRED = ("refused: downloads need Roger's approval recorded with --approved-by '<Roger, date>' "
                     "(coding_plan_03_base_model.md section 5a)")

#: ``fetcher(url, part_path) -> None``: write the body of ``url`` to ``part_path``.
Fetcher = Callable[[str, Path], None]
#: ``info_fn(source) -> {"size": int | None, "sha256": str | None}``: the provider's published figures.
InfoFn = Callable[[Source], dict]
#: ``text_fn(url) -> str``: a licence page.
TextFn = Callable[[str], str]


class ChecksumError(RuntimeError):
    """A downloaded file does not match its published hash."""


class NotApproved(SystemExit):
    def __init__(self):
        super().__init__(2)
        self.msg = APPROVAL_REQUIRED

    def __str__(self) -> str:
        return self.msg


@dataclass
class FetchResult:
    entries: list[dict] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    written: list[Path] = field(default_factory=list)
    dry_run_lines: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------- network (real)

def _request(url: str, *, method: str = "GET", data: Optional[bytes] = None):
    req = urllib.request.Request(url, data=data, method=method, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(req, timeout=120)  # noqa: S310 - fixed https URLs


def stream_to(url: str, part: Path, *, attempts: int = 4, chunk: int = 1 << 20) -> None:
    """GET ``url`` into ``part`` in chunks (a dropped connection restarts the file; ``attempts`` in all)."""
    last: Optional[Exception] = None
    part.parent.mkdir(parents=True, exist_ok=True)
    for i in range(attempts):
        try:
            with _request(url) as resp, open(part, "wb") as fh:
                while True:
                    b = resp.read(chunk)
                    if not b:
                        break
                    fh.write(b)
            return
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            last = exc
            time.sleep(2.0 * (i + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last!r}")


def published_info(source: Source) -> dict:
    """Size and sha256 the provider publishes (Hub ``paths-info``; else ``HEAD``'s Content-Length)."""
    if source.repo_id:
        url = f"https://huggingface.co/api/datasets/{source.repo_id}/paths-info/{source.revision}"
        with _request(url, method="POST", data=f"paths={source.filename}".encode()) as resp:
            info = json.loads(resp.read())[0]
        return {"size": info.get("size"), "sha256": (info.get("lfs") or {}).get("oid")}
    with _request(source.url, method="HEAD") as resp:
        n = resp.headers.get("Content-Length")
    return {"size": int(n) if n else None, "sha256": None}


def read_text(url: str) -> str:
    with _request(url) as resp:
        return resp.read().decode("utf-8", errors="replace")


def source_url(source: Source) -> str:
    if source.repo_id:
        return f"https://huggingface.co/datasets/{source.repo_id}/resolve/{source.revision}/{source.filename}"
    return str(source.url)


# ---------------------------------------------------------------------------- helpers

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _rel(path: Path) -> str:
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


def load_manifest(path: Path) -> list[dict]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def merge_manifest(entries: Iterable[dict], path: Path) -> Path:
    """Replace or add entries by ``key`` (order: wikibio, onet, model, then any other key)."""
    cur = {e["key"]: e for e in load_manifest(path)}
    for e in entries:
        cur[e["key"]] = e
    order = ["wikibio", "onet", "model"]
    out = sorted(cur.values(), key=lambda e: order.index(e["key"]) if e["key"] in order else 99)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", path)
    return Path(path)


def _licence_file(directory: Path, s: Source, *, now: str, verified: bool) -> Path:
    path = directory / "LICENSE.txt"
    lines = [f"Licence: {s.licence} ({s.licence_url})", f"Attribution: {s.attribution}", f"Citation: {s.citation}",
             f"Source: {source_url(s)}",
             f"Downloaded unmodified on {now[:10]} by {TOOL}; licence {'confirmed' if verified else 'NOT confirmed'} "
             f"on {LICENCE_CHECK[s.key][0]}.", f"Note: {s.note}" if s.note else ""]
    atomic_write_text("\n".join(x for x in lines if x) + "\n", path)
    return path


def check_licence(key: str, text_fn: TextFn) -> tuple[bool, str]:
    url, needle = LICENCE_CHECK[key]
    try:
        ok = needle.lower() in text_fn(url).lower()
    except Exception as exc:  # noqa: BLE001 - recorded, not fatal
        return False, f"{url} could not be read ({type(exc).__name__})"
    return ok, url


# ---------------------------------------------------------------------------- the datasets

def fetch_source(s: Source, *, dest_root: Path, approved_by: str, fetcher: Fetcher, info_fn: InfoFn,
                 text_fn: TextFn, force: bool = False, now: Optional[str] = None, git_sha: Optional[str] = None,
                 echo=print) -> tuple[dict, bool]:
    """Fetch one source (see the module docstring).  Returns ``(manifest entry, fetched?)``."""
    now = now or utc_now()
    dest = Path(dest_root) / s.dest
    info = info_fn(s)
    size = info.get("size")
    published = info.get("sha256") or s.sha256
    if s.sha256 and info.get("sha256") and info["sha256"] != s.sha256:
        raise ChecksumError(f"{s.key}: the provider now publishes sha256 {info['sha256']}, the pinned source says "
                            f"{s.sha256}; nothing fetched")
    echo(f"{s.key}: {source_url(s)}  ->  {_rel(dest)}  "
         f"({size:,} bytes, {size / 1e6:.1f} MB, published)" if size else f"{s.key}: {source_url(s)} (size unknown)")
    lic_ok, lic_src = check_licence(s.key, text_fn)
    echo(f"{s.key}: licence {s.licence} {'confirmed on' if lic_ok else '*** NOT CONFIRMED *** on'} {lic_src}")
    fetched = False
    if dest.exists() and not force and (published is None or sha256_file(dest) == published):
        echo(f"{s.key}: already present and verified; not fetched again")
    else:
        part = dest.with_name(dest.name + ".part")
        fetcher(source_url(s), part)
        got = sha256_file(part)
        if published and got != published:
            part.unlink()
            raise ChecksumError(f"{s.key}: downloaded sha256 {got}, published {published}; nothing written")
        part.replace(dest)
        fetched = True
    sha = sha256_file(dest)
    entry = {"key": s.key, "file": _rel(dest), "url": source_url(s), "repo_id": s.repo_id, "revision": s.revision,
             "size_bytes": dest.stat().st_size, "size_bytes_published": size, "sha256": sha,
             "sha256_published": published, "checksum_verified": bool(published and sha == published),
             "licence": s.licence, "licence_url": s.licence_url, "licence_verified": lic_ok,
             "licence_checked_on": lic_src, "attribution": s.attribution, "citation": s.citation,
             "version": s.version, "note": s.note, "approved_by": approved_by, "downloaded_at": now, "tool": TOOL,
             "git_sha": git_sha}
    d = dest.parent if s.key != "wikibio" else dest.parent.parent
    _licence_file(d, s, now=now, verified=lic_ok)
    merge_manifest([entry], d / DOWNLOAD_MANIFEST_NAME)
    return entry, fetched


# ---------------------------------------------------------------------------- the model

def hub_model_info(model_id: str, revision: Optional[str] = None) -> dict:  # pragma: no cover - network
    """``{"sha", "license", "files": {name: {"size", "sha256"}}}`` from the Hub's model API."""
    url = f"https://huggingface.co/api/models/{model_id}" + (f"/revision/{revision}" if revision else "") + "?blobs=true"
    with _request(url) as resp:
        d = json.loads(resp.read())
    files = {s["rfilename"]: {"size": s.get("size"), "sha256": (s.get("lfs") or {}).get("sha256")}
             for s in d.get("siblings", [])}
    return {"sha": d.get("sha"), "license": (d.get("cardData") or {}).get("license"), "gated": d.get("gated"),
            "files": files}


def record_model(*, approved_by: str, model: ModelSource = MODEL, hf_dir: Optional[Path] = None,
                 info_fn: Callable[[str, Optional[str]], dict] = hub_model_info, now: Optional[str] = None,
                 echo=print) -> dict:
    """Verify the ``setup_external.py`` snapshot of the model and return its manifest entry."""
    from assistant_axis.gapgen.embed import hf_snapshot_dir
    snaps = hf_snapshot_dir(model.model_id, hf_dir or hf_cache_dir()) / "snapshots"
    revs = sorted(p for p in snaps.iterdir() if p.is_dir()) if snaps.is_dir() else []
    if not revs:
        raise FileNotFoundError(f"{model.model_id} is not downloaded: run `uv run python data_analysis/gap_generation/"
                                f"setup_external.py --hf-model {model.model_id}` first (approved in section 5a)")
    snap = revs[-1]
    info = info_fn(model.model_id, snap.name)
    files, bad, total = [], [], 0
    for p in sorted(snap.iterdir()):
        if not p.is_file():
            continue
        blob = p.resolve()
        size = blob.stat().st_size
        total += size
        pub = (info.get("files") or {}).get(p.name) or {}
        rec = {"file": p.name, "size_bytes": size}
        if pub.get("sha256"):
            rec["sha256"] = blob.name
            rec["sha256_verified"] = blob.name == pub["sha256"]
            if not rec["sha256_verified"]:
                bad.append(p.name)
        if pub.get("size") is not None and pub["size"] != size:
            bad.append(p.name)
        files.append(rec)
    shards = [f for f in files if f["file"].endswith(".safetensors")]
    lic = str(info.get("license") or "")
    lic_ok = lic.lower() == model.licence.lower()
    echo(f"model {model.model_id} @ {snap.name[:8]}: {len(files)} files, {total:,} bytes; {len(shards)} shards "
         f"{'verified' if not bad else 'MISMATCHED: ' + ', '.join(bad)}; licence {lic or '?'} "
         f"({'confirmed' if lic_ok else '*** NOT CONFIRMED ***'})")
    return {"key": "model", "model_id": model.model_id, "revision": snap.name, "revision_pinned": model.revision,
            "dir": _rel(snap), "size_bytes": total, "size_bytes_published": model.size_bytes,
            "files": files, "checksum_verified": not bad and bool(shards), "licence": model.licence,
            "licence_card": lic, "licence_url": model.licence_url, "licence_verified": lic_ok,
            "approved_by": approved_by, "recorded_at": now or utc_now(),
            "tool": "setup_external.py --hf-model (download); base_model_generator.py fetch --only model (record)",
            "todo": model.todo}


# ---------------------------------------------------------------------------- orchestration

def fetch(only: Optional[Iterable[str]] = None, *, approved_by: Optional[str], dry_run: bool = False,
          force: bool = False, external_dir: Path = DATA_EXTERNAL, sources: Optional[Mapping[str, Source]] = None,
          fetcher: Fetcher = stream_to, info_fn: InfoFn = published_info, text_fn: TextFn = read_text,
          model_info_fn=hub_model_info, hf_dir: Optional[Path] = None,
          sources_manifest_path: Optional[Path] = SOURCES_MANIFEST_PATH, git_sha: Optional[str] = None,
          echo=print) -> FetchResult:
    """``only`` from ``wikibio``, ``onet``, ``model`` (default: the two datasets, and the model's record when its
    snapshot is present).  Refuses without ``approved_by`` unless ``dry_run``."""
    srcs = dict(sources if sources is not None else SOURCES)
    keys = list(only) if only else list(DEFAULT_FETCH) + ["model?"]
    out = FetchResult()
    if dry_run:
        for k in keys:
            if k.startswith("model"):
                out.dry_run_lines.append(f"model: {MODEL.model_id} via `setup_external.py --hf-model {MODEL.model_id}` "
                                         f"(~{MODEL.size_bytes / 1e9:.1f} GB, {MODEL.licence}); `fetch --only model` "
                                         f"records it.  {MODEL.todo}")
                continue
            s = srcs[k]
            out.dry_run_lines.append(f"{k}: {source_url(s)} -> {_rel(Path(external_dir) / s.dest)} "
                                     f"(~{s.size_bytes / 1e6:.1f} MB, {s.licence})")
        out.dry_run_lines += [f"not fetched: {k} ({v})" for k, v in SKIPPED.items()]
        return out
    if not (approved_by and approved_by.strip()):
        raise NotApproved()
    now = utc_now()
    for k in keys:
        if k.startswith("model"):
            try:
                out.entries.append(record_model(approved_by=approved_by, hf_dir=hf_dir, info_fn=model_info_fn,
                                                now=now, echo=echo))
            except FileNotFoundError as exc:
                if k == "model":
                    raise
                echo(f"model: not recorded ({exc})")
            continue
        entry, fetched = fetch_source(srcs[k], dest_root=external_dir, approved_by=approved_by, fetcher=fetcher,
                                      info_fn=info_fn, text_fn=text_fn, force=force, now=now, git_sha=git_sha,
                                      echo=echo)
        out.entries.append(entry)
        (out.fetched if fetched else out.skipped).append(k)
    if sources_manifest_path is not None and out.entries:
        out.written.append(merge_manifest(out.entries, sources_manifest_path))
    return out
