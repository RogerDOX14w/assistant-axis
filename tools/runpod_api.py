#!/usr/bin/env python3
"""Read-only views of the RunPod account through its GraphQL API.

Built 2026-10-22 at Roger's request, after the first pod showed what the web
console hides: stock per datacenter in one call (the console needs a click per
datacenter), and a pod's configuration as RunPod stored it (the console had
silently dropped a deploy's environment overrides; the API showed they were
never saved).

    uv run python tools/runpod_api.py stock                 # in-stock A100/H100/H200 per datacenter
    uv run python tools/runpod_api.py stock --gpu A100 --volumes-only
    uv run python tools/runpod_api.py stock --gpu ''        # every GPU type in stock
    uv run python tools/runpod_api.py pods                  # the account's pods
    uv run python tools/runpod_api.py pod jntvhjap6e308i    # one pod's stored configuration
    uv run python tools/runpod_api.py volumes               # network volumes
    uv run python tools/runpod_api.py record                # append one stock sample to the log
    uv run python tools/runpod_api.py history --gpu A100    # how often each was in stock where
    (add --json to any of them for the raw answer, still redacted)

**Pods of 1, 2 and 4 GPUs** (2026-10-28, for the cap pilot's move from 1x to
2x): ``stock`` and ``record`` also ask, for each GPU type the ``--gpu``
filter keeps (default A100 / H100 / H200), the stock of a secure-cloud pod of
1, 2 and 4 GPUs in every datacenter: one request per GPU type,
``gpuTypes(input: {id: ...})`` with one aliased ``lowestPrice(input:
{gpuCount: N, secureCloud: true, dataCenterId: ...}) { stockStatus
uninterruptablePrice }`` per (datacenter, count); a null ``stockStatus``
means none.  ``stock`` prints a table of them; ``record`` adds them to the
sample under ``by_count`` (what was asked, what was in stock, and any GPU
type whose request failed); ``history`` gives the share of samples with each
(type, datacenter, count) in stock, over the samples that asked for it.  A
record without ``by_count`` is the older form (1x only, from the datacenter
listing) and is read as before.

The key: ``RUNPOD_API_KEY`` in the repository's ``.env``, loaded with
``load_dotenv`` and sent only to api.runpod.io over HTTPS.  It is never
printed; the output is scrubbed of it in any case.  Roger's key (2026-10-22)
is read-only, and this tool refuses to send a mutation whatever key it is
given, so nothing here can create, change, stop or bill anything.

Environment variables of a pod are shown by name only: a pod's ``env`` holds
the Jupyter password and secret values in plain text.

The shared team account also holds a colleague's resources; this tool lists
them like ours (reads only).  Stock is RunPod's coarse ``stockStatus``
("Low", "Medium", "High"); the count fields the API defines come back empty.
Introspection is switched off on RunPod's server, so the queries here follow
the documentation and what answered on 2026-10-22.

Uses only the standard library for HTTP (urllib honours the sandbox's
HTTPS_PROXY), plus python-dotenv.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

API_URL = "https://api.runpod.io/graphql"
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GPU_FILTERS = ("A100", "H100", "H200")
GPU_COUNTS = (1, 2, 4)
_DATACENTER_ID = re.compile(r"^[A-Za-z0-9_-]+$")   # a datacenter id put into a query

Opener = Callable[[urllib.request.Request, float], bytes]


class RunPodAPIError(RuntimeError):
    """The API answered with errors, or not with JSON."""


TRANSIENT_DELAYS_S = (2, 5, 15)


def _default_opener(req: urllib.request.Request, timeout: float) -> bytes:
    """POST and read the whole answer, asking for gzip, and retrying transient
    network failures.  Gzip is not optional here: on 2026-10-22 every
    uncompressed answer over about 6 kB (the 26 kB stock answer) came through
    the sandbox's proxy cut short with IncompleteRead, while the gzip answer
    arrived whole every time."""
    import gzip
    import http.client
    import time
    req.add_header("Accept-Encoding", "gzip")
    for attempt, delay in enumerate((*TRANSIENT_DELAYS_S, None)):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (fixed https URL)
                raw = resp.read()
                if (resp.headers.get("Content-Encoding") or "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                return raw
        except urllib.error.HTTPError:
            raise
        except (http.client.IncompleteRead, urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            if delay is None:
                raise RunPodAPIError(f"network error after {attempt + 1} attempts: {type(exc).__name__}") from None
            print(f"runpod_api: {type(exc).__name__}; retrying in {delay} s", file=sys.stderr)
            time.sleep(delay)
    raise AssertionError("unreachable")


def load_key(env_file: Optional[Path] = None) -> str:
    """The API key from ``.env`` (or the environment).  Exits with a message,
    never the key, when it is missing."""
    try:
        from dotenv import load_dotenv
        load_dotenv(env_file or REPO_ROOT / ".env")
    except ImportError:  # pragma: no cover - python-dotenv is a project dependency
        pass
    key = os.environ.get("RUNPOD_API_KEY", "").strip()
    if not key:
        raise SystemExit("RUNPOD_API_KEY is not set (expected in the repository's .env)")
    return key


def scrub(text: str, key: str) -> str:
    """Remove the key from any text before it is shown."""
    return text.replace(key, "<key>") if key else text


def hide_env_values(obj: Any) -> Any:
    """Replace every ``env`` list's ``NAME=value`` entries by ``NAME=<hidden>``."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "env" and isinstance(v, list):
                out[k] = [f"{str(e).split('=', 1)[0]}=<hidden>" for e in v]
            else:
                out[k] = hide_env_values(v)
        return out
    if isinstance(obj, list):
        return [hide_env_values(x) for x in obj]
    return obj


def query(q: str, key: str, *, opener: Opener = _default_opener, timeout: float = 60.0) -> Dict[str, Any]:
    """Send one read-only GraphQL query; return its ``data``.  Refuses mutations."""
    head = q.lstrip().lower()
    if head.startswith("mutation") or "mutation " in head.split("{", 1)[0]:
        raise ValueError("runpod_api is read-only: it does not send mutations")
    body = json.dumps({"query": q}).encode()
    req = urllib.request.Request(
        API_URL, data=body, method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "User-Agent": "assistant-axis-runpod-api/1"})
    try:
        raw = opener(req, timeout)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        detail = scrub(exc.read().decode(errors="replace")[:500], key)
        raise RunPodAPIError(f"HTTP {exc.code}: {detail}") from None
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        raise RunPodAPIError("the API did not answer with JSON: " + scrub(raw[:300].decode(errors="replace"), key))
    if out.get("errors"):
        raise RunPodAPIError(scrub(json.dumps(out["errors"])[:800], key))
    return out.get("data") or {}


# ---------------------------------------------------------------------------
# The views
# ---------------------------------------------------------------------------

STOCK_QUERY = """{ dataCenters { id name storageSupport
  gpuAvailability { gpuTypeId gpuTypeDisplayName stockStatus available } }
  gpuTypes { id displayName memoryInGb
  lowestPrice(input: {gpuCount: 1, secureCloud: true}) { uninterruptablePrice stockStatus } } }"""

PODS_QUERY = """{ myself { pods { id name desiredStatus gpuCount costPerHr imageName
  machine { gpuDisplayName dataCenterId } } } }"""

POD_QUERY = """{ pod(input: {podId: "%s"}) { id name desiredStatus gpuCount costPerHr imageName
  env dockerArgs containerDiskInGb volumeMountPath ports templateId networkVolumeId
  machine { gpuDisplayName dataCenterId } runtime { uptimeInSeconds } } }"""

VOLUMES_QUERY = """{ myself { networkVolumes { id name size dataCenterId } } }"""


def stock_rows(data: Dict[str, Any], gpu_filters: List[str], volumes_only: bool) -> List[Dict[str, Any]]:
    """One row per (datacenter, GPU type) in stock, filtered by display-name
    substrings (an empty filter keeps every type)."""
    filters = [f for f in gpu_filters if f]
    rows = []
    for dc in data.get("dataCenters") or []:
        if volumes_only and not dc.get("storageSupport"):
            continue
        for a in dc.get("gpuAvailability") or []:
            name = a.get("gpuTypeDisplayName") or a.get("gpuTypeId") or ""
            if not a.get("stockStatus"):
                continue
            if filters and not any(f.lower() in name.lower() for f in filters):
                continue
            rows.append({"datacenter": dc.get("id"), "volumes": bool(dc.get("storageSupport")),
                         "gpu": name, "stock": a.get("stockStatus")})
    rows.sort(key=lambda r: (r["gpu"], r["datacenter"]))
    return rows


def price_rows(data: Dict[str, Any], gpu_filters: List[str]) -> List[Dict[str, Any]]:
    filters = [f for f in gpu_filters if f]
    rows = []
    for g in data.get("gpuTypes") or []:
        name = g.get("displayName") or g.get("id") or ""
        if filters and not any(f.lower() in name.lower() for f in filters):
            continue
        lp = g.get("lowestPrice") or {}
        rows.append({"gpu": name, "memory_gb": g.get("memoryInGb"),
                     "secure_price_hr": lp.get("uninterruptablePrice"), "stock": lp.get("stockStatus")})
    rows.sort(key=lambda r: r["gpu"])
    return rows


def _keeps(name: str, gpu_filters: List[str]) -> bool:
    filters = [f for f in gpu_filters if f]
    return not filters or any(f.lower() in name.lower() for f in filters)


def count_query(gpu_id: str, datacenter_ids: List[str],
                counts=GPU_COUNTS) -> tuple[str, Dict[str, tuple]]:
    """One GPU type's stock per (datacenter, GPU count) in one request: an
    aliased ``lowestPrice`` per pair.  Returns the query and ``{alias:
    (datacenter, count)}``.  The type id is quoted as a JSON string (GraphQL's
    string syntax); a datacenter id that is not letters, digits, ``-`` and
    ``_`` is left out."""
    aliases: Dict[str, tuple] = {}
    parts = []
    for dc in datacenter_ids:
        if not _DATACENTER_ID.match(dc or ""):
            continue
        for n in counts:
            a = f"a{len(aliases)}"
            aliases[a] = (dc, int(n))
            parts.append(f'{a}: lowestPrice(input: {{gpuCount: {int(n)}, secureCloud: true, '
                         f'dataCenterId: "{dc}"}}) {{ stockStatus uninterruptablePrice }}')
    q = ("{ gpuTypes(input: {id: " + json.dumps(gpu_id) + "}) { id displayName\n  "
         + "\n  ".join(parts) + " } }")
    return q, aliases


def stock_by_count(data: Dict[str, Any], key: str, gpu_filters: List[str], *,
                   opener: Opener = _default_opener, counts=GPU_COUNTS) -> Dict[str, Any]:
    """Stock of 1-, 2- and 4-GPU secure-cloud pods per datacenter, for the GPU
    types of ``data`` (the stock listing) that the filter keeps: one request
    per type (:func:`count_query`).  Returns ``{"counts", "gpus" (the types
    answered), "datacenters" (those asked), "in_stock": [{"gpu",
    "datacenter", "count", "stock", "price_hr"}], "errors": [{"gpu",
    "error"}]}``; a type whose request fails is listed under ``errors`` and
    not under ``gpus``, so it does not count as out of stock."""
    dcs = [dc.get("id") for dc in data.get("dataCenters") or []
           if _DATACENTER_ID.match(dc.get("id") or "")]
    out: Dict[str, Any] = {"counts": [int(n) for n in counts], "gpus": [], "datacenters": dcs,
                           "in_stock": [], "errors": []}
    for g in data.get("gpuTypes") or []:
        name = g.get("displayName") or g.get("id") or ""
        if not g.get("id") or not _keeps(name, gpu_filters):
            continue
        q, aliases = count_query(g["id"], dcs, counts)
        try:
            answer = query(q, key, opener=opener)
        except RunPodAPIError as exc:
            out["errors"].append({"gpu": name, "error": scrub(str(exc), key)[:300]})
            continue
        types = answer.get("gpuTypes") or []
        got = types[0] if isinstance(types, list) and types else {}
        out["gpus"].append(name)
        for a, (dc, n) in aliases.items():
            lp = got.get(a) or {}
            if lp.get("stockStatus"):
                out["in_stock"].append({"gpu": name, "datacenter": dc, "count": n,
                                        "stock": lp.get("stockStatus"),
                                        "price_hr": lp.get("uninterruptablePrice")})
    return out


def count_rows(by_count: Dict[str, Any], data: Dict[str, Any], volumes_only: bool) -> List[Dict[str, Any]]:
    """One row per (GPU type, datacenter) with a pod of some count in stock:
    the stock level at each count (blank: none)."""
    volumes = {dc.get("id"): bool(dc.get("storageSupport")) for dc in data.get("dataCenters") or []}
    rows: Dict[tuple, Dict[str, Any]] = {}
    for e in by_count.get("in_stock") or []:
        if volumes_only and not volumes.get(e["datacenter"]):
            continue
        r = rows.setdefault((e["gpu"], e["datacenter"]), {
            "gpu": e["gpu"], "datacenter": e["datacenter"], "volumes": volumes.get(e["datacenter"])})
        r[f"{e['count']}x"] = e["stock"]
    return sorted(rows.values(), key=lambda r: (r["gpu"], r["datacenter"]))


def _table(rows: List[Dict[str, Any]], cols: List[str]) -> str:
    if not rows:
        return "(none)"
    widths = {c: max(len(c), *(len("" if r.get(c) is None else str(r.get(c))) for r in rows)) for c in cols}
    lines = ["  ".join(c.ljust(widths[c]) for c in cols)]
    for r in rows:
        lines.append("  ".join(("" if r.get(c) is None else str(r.get(c))).ljust(widths[c]) for c in cols))
    return "\n".join(lines)


def render_stock(data: Dict[str, Any], gpu_filters: List[str], volumes_only: bool,
                 by_count: Optional[Dict[str, Any]] = None) -> str:
    rows = stock_rows(data, gpu_filters, volumes_only)
    prices = price_rows(data, gpu_filters)
    in_stock = [p for p in prices if p["stock"]]
    text = ("In stock, by datacenter (secure cloud; 'volumes' = the datacenter takes network volumes):\n"
            + _table(rows, ["gpu", "datacenter", "volumes", "stock"])
            + "\n\nCheapest secure-cloud price per GPU type now in stock anywhere ($/hr, 1 GPU):\n"
            + _table(in_stock, ["gpu", "memory_gb", "secure_price_hr", "stock"]))
    if by_count is not None:
        cols = [f"{n}x" for n in by_count["counts"]]
        text += ("\n\nSecure-cloud pods of " + ", ".join(cols) + " GPUs in stock, by datacenter "
                 f"({len(by_count['gpus'])} GPU types asked; blank = none):\n"
                 + _table(count_rows(by_count, data, volumes_only),
                          ["gpu", "datacenter", "volumes"] + cols))
        for e in by_count["errors"]:
            text += f"\n(no answer for {e['gpu']}: {e['error']})"
    return text


def render_pods(data: Dict[str, Any]) -> str:
    rows = []
    for p in (data.get("myself") or {}).get("pods") or []:
        m = p.get("machine") or {}
        rows.append({"id": p.get("id"), "name": p.get("name"), "status": p.get("desiredStatus"),
                     "gpu": f"{p.get('gpuCount')}x {m.get('gpuDisplayName')}", "datacenter": m.get("dataCenterId"),
                     "cost_hr": p.get("costPerHr"), "image": p.get("imageName")})
    return _table(rows, ["id", "name", "status", "gpu", "datacenter", "cost_hr", "image"])


def render_pod(data: Dict[str, Any]) -> str:
    p = hide_env_values(data.get("pod") or {})
    if not p:
        return "(no such pod)"
    m = p.get("machine") or {}
    rt = p.get("runtime") or {}
    lines = [
        f"id                 {p.get('id')}  ({p.get('name')})",
        f"status             {p.get('desiredStatus')}  uptime {rt.get('uptimeInSeconds')} s",
        f"gpu                {p.get('gpuCount')}x {m.get('gpuDisplayName')} in {m.get('dataCenterId')}, ${p.get('costPerHr')}/hr",
        f"image              {p.get('imageName')}",
        f"start command      {p.get('dockerArgs')}",
        f"container disk     {p.get('containerDiskInGb')} GB",
        f"volume             {p.get('networkVolumeId')} at {p.get('volumeMountPath')}",
        f"ports              {p.get('ports')}",
        f"template           {p.get('templateId')}",
        "env (names only)   " + (", ".join(e.split("=", 1)[0] for e in (p.get("env") or [])) or "(none)"),
    ]
    return "\n".join(lines)


def render_volumes(data: Dict[str, Any]) -> str:
    rows = [{"id": v.get("id"), "name": v.get("name"), "size_gb": v.get("size"), "datacenter": v.get("dataCenterId")}
            for v in (data.get("myself") or {}).get("networkVolumes") or []]
    return _table(rows, ["id", "name", "size_gb", "datacenter"])


# ---------------------------------------------------------------------------
# Stock over time (Roger, 2026-10-22: watch availability for 24 hours before
# judging the datacenter choice)
# ---------------------------------------------------------------------------

DEFAULT_STOCK_LOG = REPO_ROOT / "runpod_workspace" / "runpod_stock" / "stock_log.jsonl"


def stock_sample(data: Dict[str, Any], when: str) -> Dict[str, Any]:
    """One log line: every datacenter's in-stock GPU types (all types, not
    filtered) and the secure-cloud price per type."""
    dcs = []
    for dc in data.get("dataCenters") or []:
        avail = [{"gpu": a.get("gpuTypeDisplayName") or a.get("gpuTypeId"), "stock": a.get("stockStatus")}
                 for a in dc.get("gpuAvailability") or [] if a.get("stockStatus")]
        dcs.append({"id": dc.get("id"), "volumes": bool(dc.get("storageSupport")), "in_stock": avail})
    prices = {g.get("displayName") or g.get("id"): (g.get("lowestPrice") or {}).get("uninterruptablePrice")
              for g in data.get("gpuTypes") or []}
    return {"t": when, "datacenters": dcs, "secure_price_hr": prices}


def record_stock(log_path: Path, key: str, *, opener: Opener = _default_opener,
                 now: Optional[str] = None,
                 gpu_filters: Optional[List[str]] = None) -> Dict[str, Any]:
    """Query stock once and append the sample to ``log_path`` (JSON lines):
    the datacenter listing (every type, 1 GPU) and, since 2026-10-28, under
    ``by_count``, the 1-, 2- and 4-GPU stock of the types ``gpu_filters``
    keeps (default A100 / H100 / H200; :func:`stock_by_count`)."""
    from datetime import datetime, timezone
    when = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    data = query(STOCK_QUERY, key, opener=opener)
    sample = stock_sample(data, when)
    sample["by_count"] = stock_by_count(
        data, key, list(DEFAULT_GPU_FILTERS) if gpu_filters is None else gpu_filters,
        opener=opener)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(sample) + "\n")
    return sample


def stock_history(samples: List[Dict[str, Any]], gpu_filters: List[str],
                  volumes_only: bool) -> List[Dict[str, Any]]:
    """Per (GPU type, datacenter): the share of samples with it in stock, the
    levels seen, and the longest run of consecutive samples without it."""
    filters = [f for f in gpu_filters if f]
    n = len(samples)
    seen: Dict[tuple, Dict[str, Any]] = {}
    volumes: Dict[str, bool] = {}
    for s in samples:
        for dc in s.get("datacenters") or []:
            volumes[dc["id"]] = bool(dc.get("volumes"))
            for a in dc.get("in_stock") or []:
                g = a.get("gpu") or ""
                if filters and not any(f.lower() in g.lower() for f in filters):
                    continue
                seen.setdefault((g, dc["id"]), {"hits": set(), "levels": {}})
    for i, s in enumerate(samples):
        present = {(a.get("gpu"), dc["id"]): a.get("stock")
                   for dc in s.get("datacenters") or [] for a in dc.get("in_stock") or []}
        for k, rec in seen.items():
            if k in present:
                rec["hits"].add(i)
                rec["levels"][present[k]] = rec["levels"].get(present[k], 0) + 1
    rows = []
    for (g, dc), rec in seen.items():
        if volumes_only and not volumes.get(dc):
            continue
        gap = run = 0
        for i in range(n):
            run = 0 if i in rec["hits"] else run + 1
            gap = max(gap, run)
        rows.append({"gpu": g, "datacenter": dc, "volumes": volumes.get(dc),
                     "in_stock": f"{len(rec['hits'])}/{n}", "share": round(len(rec["hits"]) / n, 3) if n else 0.0,
                     "levels": ", ".join(f"{lv} {c}" for lv, c in sorted(rec["levels"].items())),
                     "longest_gap_samples": gap})
    rows.sort(key=lambda r: (r["gpu"], -r["share"], r["datacenter"]))
    return rows


def stock_history_by_count(samples: List[Dict[str, Any]], gpu_filters: List[str],
                           volumes_only: bool) -> List[Dict[str, Any]]:
    """Per (GPU type, datacenter, GPU count) seen in stock in a ``by_count``
    sample: the share of the samples that asked for it with it in stock, the
    levels seen, and the longest run of such samples without it.  A sample
    asked for a triple when its ``by_count`` lists the type under ``gpus``,
    the datacenter and the count; older samples (no ``by_count``) and a type
    whose request failed are not counted."""
    volumes: Dict[str, bool] = {}
    asked: List[tuple] = []        # per sample: (gpus, datacenters, counts, {triple: level})
    for s in samples:
        for dc in s.get("datacenters") or []:
            volumes[dc["id"]] = bool(dc.get("volumes"))
        bc = s.get("by_count")
        if not bc:
            continue
        present = {(e["gpu"], e["datacenter"], int(e["count"])): e.get("stock")
                   for e in bc.get("in_stock") or []}
        asked.append((set(bc.get("gpus") or []), set(bc.get("datacenters") or []),
                      {int(n) for n in bc.get("counts") or []}, present))
    triples = {t for _, _, _, present in asked for t in present if _keeps(t[0], gpu_filters)}
    rows = []
    for g, dc, n in triples:
        if volumes_only and not volumes.get(dc):
            continue
        hits = asks = gap = run = 0
        levels: Dict[str, int] = {}
        for gpus, dcs, counts, present in asked:
            if g not in gpus or dc not in dcs or n not in counts:
                continue
            asks += 1
            if (g, dc, n) in present:
                hits += 1
                run = 0
                lv = present[(g, dc, n)]
                levels[lv] = levels.get(lv, 0) + 1
            else:
                run += 1
                gap = max(gap, run)
        rows.append({"gpu": g, "datacenter": dc, "count": f"{n}x", "volumes": volumes.get(dc),
                     "in_stock": f"{hits}/{asks}", "share": round(hits / asks, 3) if asks else 0.0,
                     "levels": ", ".join(f"{lv} {c}" for lv, c in sorted(levels.items())),
                     "longest_gap_samples": gap})
    rows.sort(key=lambda r: (r["gpu"], r["count"], -r["share"], r["datacenter"]))
    return rows


def render_history(samples: List[Dict[str, Any]], gpu_filters: List[str], volumes_only: bool) -> str:
    if not samples:
        return "(no samples)"
    rows = stock_history(samples, gpu_filters, volumes_only)
    head = (f"{len(samples)} samples, {samples[0]['t']} to {samples[-1]['t']} "
            "(share = samples with the type in stock; longest gap in consecutive samples):\n")
    text = head + _table(rows, ["gpu", "datacenter", "volumes", "in_stock", "share", "levels",
                                "longest_gap_samples"])
    n_counted = sum(1 for s in samples if s.get("by_count"))
    if not n_counted:
        return text + ("\n\nBy GPU count: no sample records it (samples before 2026-10-28 "
                       "list 1x stock only).")
    return (text + f"\n\nBy GPU count, secure cloud ({n_counted} of {len(samples)} samples record "
            "it; share = of the samples that asked for that type, datacenter and count):\n"
            + _table(stock_history_by_count(samples, gpu_filters, volumes_only),
                     ["gpu", "count", "datacenter", "volumes", "in_stock", "share", "levels",
                      "longest_gap_samples"]))


def main(argv: Optional[List[str]] = None, *, opener: Opener = _default_opener,
         key: Optional[str] = None, out=None) -> int:
    out = out or sys.stdout
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", action="store_true", help="print the raw answer (redacted) instead of a table")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stock", help="GPU types in stock per datacenter, secure-cloud prices, and "
                                     "the stock of 1-, 2- and 4-GPU pods of the --gpu types")
    s.add_argument("--gpu", nargs="*", default=list(DEFAULT_GPU_FILTERS),
                   help="display-name substrings to keep (default: A100 H100 H200; '' keeps all, "
                        "and asks the per-count stock of every type, one request each)")
    s.add_argument("--volumes-only", action="store_true", help="only datacenters that take network volumes")
    sub.add_parser("pods", help="the account's pods")
    p = sub.add_parser("pod", help="one pod's stored configuration (env names only)")
    p.add_argument("pod_id")
    sub.add_parser("volumes", help="network volumes")
    r = sub.add_parser("record", help="append one stock sample (all GPU types, all datacenters; "
                                      "pods of 1, 2 and 4 GPUs for the --gpu types) to a log")
    r.add_argument("--log", type=Path, default=DEFAULT_STOCK_LOG)
    r.add_argument("--gpu", nargs="*", default=list(DEFAULT_GPU_FILTERS),
                   help="display-name substrings of the types whose 1-, 2- and 4-GPU stock is "
                        "recorded (default: A100 H100 H200; '' keeps all, one request per type)")
    h = sub.add_parser("history", help="summarise a stock log: how often each type was in stock where")
    h.add_argument("--log", type=Path, default=DEFAULT_STOCK_LOG)
    h.add_argument("--gpu", nargs="*", default=list(DEFAULT_GPU_FILTERS),
                   help="display-name substrings to keep (default: A100 H100 H200; '' keeps all)")
    h.add_argument("--volumes-only", action="store_true", help="only datacenters that take network volumes")
    args = ap.parse_args(argv)

    if args.cmd == "history":   # reads the log only: no key, no network
        samples = [json.loads(line) for line in args.log.read_text().splitlines() if line.strip()]
        print(render_history(samples, args.gpu, args.volumes_only), file=out)
        return 0

    key = key or load_key()
    if args.cmd == "record":
        s = record_stock(args.log, key, opener=opener, gpu_filters=args.gpu)
        n = sum(len(dc["in_stock"]) for dc in s["datacenters"])
        bc = s["by_count"]
        failed = f", no answer for {len(bc['errors'])}" if bc["errors"] else ""
        print(scrub(f"{s['t']}: {n} (datacenter, GPU type) pairs in stock; "
                    f"{len(bc['in_stock'])} (datacenter, type, count) of {len(bc['gpus'])} types "
                    f"asked at {'/'.join(f'{c}x' for c in bc['counts'])}{failed}; "
                    f"appended to {args.log}", key), file=out)
        return 0
    if args.cmd == "stock":
        data = query(STOCK_QUERY, key, opener=opener)
        by_count = stock_by_count(data, key, args.gpu, opener=opener)
        text = (json.dumps(dict(data, by_gpu_count=by_count), indent=1) if args.json
                else render_stock(data, args.gpu, args.volumes_only, by_count))
    elif args.cmd == "pods":
        data = query(PODS_QUERY, key, opener=opener)
        text = json.dumps(data, indent=1) if args.json else render_pods(data)
    elif args.cmd == "pod":
        if not args.pod_id.isalnum():
            raise SystemExit("a pod id is letters and digits")
        data = query(POD_QUERY % args.pod_id, key, opener=opener)
        text = json.dumps(hide_env_values(data), indent=1) if args.json else render_pod(data)
    else:
        data = query(VOLUMES_QUERY, key, opener=opener)
        text = json.dumps(data, indent=1) if args.json else render_volumes(data)
    print(scrub(text, key), file=out)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RunPodAPIError as exc:
        print(f"runpod_api: {exc}", file=sys.stderr)
        sys.exit(1)
