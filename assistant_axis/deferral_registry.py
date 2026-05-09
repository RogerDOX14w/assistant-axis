"""Deferred-rejudge registry for the provenance system.

Judging is expensive and non-deterministic, so we sometimes
intentionally choose to live with a stale judge cache rather than
pay the cost (and accept the rng) of rerunning.  Audits should know
about these deferrals: a deferred cache shouldn't keep showing up in
"what's stale?" rollups, but it should be queryable as "what have I
deferred, and why?".

This module implements a small declarative registry that maps a
glob over cache paths (optionally with a ``dep_key`` filter) to a
deferral entry.  ``audit_caches.py`` and ``audit_pngs.py`` consult
the registry and reclassify both ``stale_direct`` /
``stale_transitive`` AND ``legacy`` rows to ``deferred`` when an
entry matches:

* ``stale_*`` -> ``deferred``: "this would otherwise need rerunning;
  defer the rerun instead".
* ``legacy`` -> ``deferred``: "this never had an envelope -- pre-
  migration bare JSON, or a producer we've decided not to migrate.
  Presume current as of mechanism introduction; would auto-clear if
  the producer were re-run with the modern writer pattern."

The legacy case is what supports the May 2026 backfill: judge caches
written by ``axis_judge_correlation.py`` predate the Phase 6
provenance wrap, and we deliberately don't re-run them; deferral
entries record that the staleness is known and intentional rather
than letting them accumulate as uncategorised ``legacy`` noise in
audits.

Schema
------
Stored at ``<repo_root>/deferred_rejudges.yaml``::

    schema_version: 1
    deferrals:
      - path_glob: "roger/axis_judge_experiments/q9_*/gpt/scores_descriptions.json"
        dep_key:   ~                # optional; matches any dep_key when null
        reason:    "Desc-mode rejudge deferred until the 4-model audit completes."
        deferred_at: "2026-05-08T04:30:00+00:00"
      - path_glob: "roger/axis_judge_experiments/*/sonnet/scores_descriptions.json"
        dep_key:   "judge_*_descriptions_sonnet"
        reason:    "Sonnet-desc judging is dropped from the canonical pipeline."
        deferred_at: "2026-05-09T11:00:00+00:00"

Semantics
---------
* ``path_glob`` is a Unix-shell glob applied to repo-relative paths
  via ``fnmatch.fnmatch``; matches any file the audit walks.

  **fnmatch quirk worth knowing**: ``*`` matches across path
  separators (so ``*/scores_descriptions.json`` will match
  ``roger/axis_judge_experiments/q9_x_vs_y/gpt/scores_descriptions.json``),
  but it does NOT match the empty string at the start of a path.
  In practice that means ``*/roger/foo.json`` will NOT match the
  top-level ``roger/foo.json`` (no characters before ``roger/``),
  while it does match ``archive/roger/foo.json``.  When deferring
  top-level files in ``roger/``, write the pattern as
  ``roger/foo.json`` directly (no ``*/`` prefix).
* ``dep_key`` (when set) is a glob over the dep_key string of the
  drift-source InputSpec inside the cache; useful when one cache file
  depends on many sub-inputs and only some should be deferred.
* ``reason`` is free-text; surfaced in audit reports.
* ``deferred_at`` is the ISO-8601 timestamp when the deferral was
  recorded.  Deferred-until-removed semantics: there's no
  ``expires_at``; deferrals stay active until the maintainer deletes
  the entry.

Public API
----------
* :func:`load_registry` -- parse the YAML.
* :func:`match_cache` -- given a cache path, return the list of
  matching :class:`DeferralEntry` records.
* :func:`append_deferral` -- add a new entry.
* :func:`remove_deferral` -- delete by index or by exact field match.
"""

from __future__ import annotations

import datetime as _dt
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml

__all__ = [
    "DEFERRAL_FILENAME",
    "DeferralEntry",
    "load_registry",
    "match_cache",
    "append_deferral",
    "remove_deferral",
]

DEFERRAL_FILENAME = "deferred_rejudges.yaml"
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DeferralEntry:
    """One declared deferred-rejudge entry."""

    path_glob: str            # repo-relative glob over cache paths
    dep_key: Optional[str]    # optional dep_key glob; None = match any
    reason: str
    deferred_at: str


def _repo_root_default() -> Path:
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def _registry_path(repo_root: Optional[Path] = None) -> Path:
    return (repo_root or _repo_root_default()) / DEFERRAL_FILENAME


def load_registry(repo_root: Optional[Path] = None) -> List[DeferralEntry]:
    """Load the registry, returning the list of declared entries.

    Empty list when the YAML file doesn't exist.
    Raises ``ValueError`` for unknown ``schema_version`` values.
    """
    path = _registry_path(repo_root)
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text()) or {}
    sv = raw.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ValueError(
            f"{path}: unknown schema_version {sv!r}; "
            f"this assistant_axis build supports v{SCHEMA_VERSION}."
        )
    out: List[DeferralEntry] = []
    for entry in raw.get("deferrals", []) or []:
        out.append(DeferralEntry(
            path_glob=str(entry["path_glob"]),
            dep_key=str(entry["dep_key"]) if entry.get("dep_key") else None,
            reason=str(entry.get("reason", "")),
            deferred_at=str(entry.get("deferred_at", "")),
        ))
    return out


def _to_repo_relative(path: Path, repo_root: Path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def match_cache(
    cache_path: Path,
    *,
    dep_key: Optional[str] = None,
    registry: Optional[List[DeferralEntry]] = None,
    repo_root: Optional[Path] = None,
) -> List[DeferralEntry]:
    """Return all registry entries matching ``cache_path`` (and optionally
    ``dep_key``).

    ``dep_key`` is the dep_key string of the drift-source InputSpec
    inside the cache; pass ``None`` to match any dep_key.  An entry
    with ``dep_key=None`` in the registry matches any caller-side
    dep_key value (intent: "defer this cache regardless of which sub-
    input changed").

    Returns an empty list when no entries match -- the cache is not
    deferred.  Multiple matches indicate overlapping rules; callers
    typically just check whether the list is non-empty.

    ``repo_root`` is auto-detected (via ``.git``) when omitted.
    """
    reg = registry if registry is not None else load_registry(repo_root)
    if not reg:
        return []
    root = repo_root or _repo_root_default()
    rel = _to_repo_relative(Path(cache_path), root)
    matches: List[DeferralEntry] = []
    for entry in reg:
        if not fnmatch.fnmatch(rel, entry.path_glob):
            continue
        if entry.dep_key is not None and dep_key is not None:
            if not fnmatch.fnmatch(dep_key, entry.dep_key):
                continue
        matches.append(entry)
    return matches


def append_deferral(
    *,
    path_glob: str,
    reason: str,
    dep_key: Optional[str] = None,
    deferred_at: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> DeferralEntry:
    """Append one entry to the registry, creating the file if needed.

    Returns the new :class:`DeferralEntry`.

    Raises ``ValueError`` if an identical entry (same ``path_glob`` +
    ``dep_key``) already exists.  Reason / timestamp may differ; we
    refuse silent overwrites to keep the registry append-only.
    """
    if deferred_at is None:
        deferred_at = (_dt.datetime.now(tz=_dt.timezone.utc)
                       .replace(microsecond=0).isoformat())
    new = DeferralEntry(
        path_glob=path_glob, dep_key=dep_key,
        reason=reason, deferred_at=deferred_at,
    )
    path = _registry_path(repo_root)
    if path.exists():
        raw = yaml.safe_load(path.read_text()) or {}
        sv = raw.get("schema_version")
        if sv != SCHEMA_VERSION:
            raise ValueError(
                f"{path}: refusing to write to unknown schema_version {sv!r}"
            )
    else:
        raw = {"schema_version": SCHEMA_VERSION, "deferrals": []}
    entries = raw.setdefault("deferrals", []) or []
    raw["deferrals"] = entries
    for existing in entries:
        if (
            existing.get("path_glob") == new.path_glob
            and (existing.get("dep_key") or None) == new.dep_key
        ):
            raise ValueError(
                f"Duplicate deferral entry for path_glob={new.path_glob!r}, "
                f"dep_key={new.dep_key!r}; remove the old one first."
            )
    entries.append({
        "path_glob": new.path_glob,
        "dep_key": new.dep_key,
        "reason": new.reason,
        "deferred_at": new.deferred_at,
    })
    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    return new


def remove_deferral(
    *,
    path_glob: str,
    dep_key: Optional[str] = None,
    repo_root: Optional[Path] = None,
) -> bool:
    """Remove one entry by exact (path_glob, dep_key) match.

    Returns True when an entry was removed, False when no match was
    found.
    """
    path = _registry_path(repo_root)
    if not path.exists():
        return False
    raw = yaml.safe_load(path.read_text()) or {}
    sv = raw.get("schema_version")
    if sv != SCHEMA_VERSION:
        raise ValueError(
            f"{path}: refusing to mutate unknown schema_version {sv!r}"
        )
    entries = raw.get("deferrals", []) or []
    new_entries = [
        e for e in entries
        if not (
            e.get("path_glob") == path_glob
            and (e.get("dep_key") or None) == dep_key
        )
    ]
    if len(new_entries) == len(entries):
        return False
    raw["deferrals"] = new_entries
    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=True))
    return True
