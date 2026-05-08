"""End-to-end data-provenance primitives for caches and plots.

Phase 2 of the provenance redesign (see ``audits/post_pipeline_*``,
``tools/regenerate_dataset_manifest.py``, and the plan under
``.cursor/plans/``).

This module provides three things:

1. ``InputSpec`` — a typed, JSON-serialisable record of *one input* to a
   producer (e.g. a dataset subtree, an upstream cache JSON, an axis spec
   file).  Producers attach a list of these to every plot / cache they
   write so a reader can later validate that nothing the artifact depends
   on has drifted.

2. ``Manifest`` — a typed, read-only view of a dataset's
   ``MANIFEST.json``.  Loaded from disk via ``read_manifest(data_dir)``.

3. ``current_*_input`` helpers + ``validate_inputs`` — the core API used
   by writers (to build the provenance record at write time) and readers
   (to compare the recorded record against the current dataset/file
   state and detect drift).

Design choices:

* Fingerprints are *cheap* (mtime+size based for files, subtree
  ``summary_sha256`` from MANIFEST.json for dataset subtrees).  Phase 6
  may add an optional content-hash tier behind a feature flag; this
  module already accepts a ``fingerprint_kind`` field so future
  manifests can mark themselves as content-hash-grade without breaking
  older readers.
* ``InputSpec`` carries everything a downstream auditor needs: the
  ``role`` (semantic name), the ``path`` (repo-relative, so manifests
  port across machines), the ``fingerprint`` (the actual freshness
  signal), and ``extras`` for any per-plot discriminators (slot, layer,
  K-range, ...).
* Validation is *additive*: artifacts without a ``_provenance`` block or
  ``Inputs`` chunk keep working; auditors classify them as
  "legacy/unverifiable".  ``validate_inputs`` returns a ``ProvenanceCheck``
  describing per-role status; raising / rebuilding is left to higher-
  level helpers (Phase 4: ``load_validated_json``).

Public API (stable):

    InputSpec, Manifest, ManifestSubtree
    read_manifest(data_dir) -> Manifest
    current_data_subtree_input(data_dir, subtree_rel, role, *, extras=None) -> InputSpec
    current_file_input(role, path, *, extras=None) -> InputSpec
    validate_inputs(recorded, current) -> ProvenanceCheck
    inputs_to_jsonable(specs) -> list[dict]
    inputs_from_jsonable(blobs) -> list[InputSpec]

Repo path conventions:
    ``InputSpec.path`` is always recorded *relative to the repo root*
    (the directory containing the ``.git`` dir).  Helpers below use
    ``_repo_root()`` to do that resolution; consumers can rely on it.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable, Optional

__all__ = [
    "InputSpec",
    "Manifest",
    "ManifestSubtree",
    "ProvenanceCheck",
    "InputStatus",
    "StaleCacheError",
    "MANIFEST_FILENAME",
    "PROVENANCE_SCHEMA_VERSION",
    "FINGERPRINT_VERSION_TAG",
    "CACHE_POLICIES",
    "read_manifest",
    "current_data_subtree_input",
    "current_file_input",
    "current_files_input",
    "current_for_recorded",
    "validate_inputs",
    "validate_recorded",
    "inputs_to_jsonable",
    "inputs_from_jsonable",
    "load_validated_json",
]

MANIFEST_FILENAME = "MANIFEST.json"
PROVENANCE_SCHEMA_VERSION = "1.0"

# Length of the subtree summary_sha256 prefix embedded in fingerprints.
# Short enough to fit in PNG iTXt chunks comfortably; long enough that a
# random collision across the few-hundred subtrees we touch is negligible
# (12 hex = 48 bits; birthday collision threshold is ~17M items).
_SUBTREE_SHA_PREFIX_LEN = 12

# Version tag that prefixes every fingerprint string.  Lets future
# format changes (e.g. switching subtree summaries to content hashes,
# or files to mtime_ns) coexist with old recorded fingerprints: the
# validator can dispatch on the prefix rather than format-mismatch
# silently.  Bump to "v2:" when the fingerprint *string format* (not
# the underlying data) changes.
FINGERPRINT_VERSION_TAG = "v1"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputSpec:
    """One input that a writer depends on.

    Attributes:
        dep_key: Abbreviated, writer-chosen name for one dependency
            (literally a "key" identifying one "dep").  Used as the
            dict key inside :func:`validate_inputs` when comparing
            recorded vs current.  Choose a short, namespaced string
            (e.g. ``"data_dir/traits"``, ``"sweep_json_K"``,
            ``"judge_scores_inst"``); see ``AGENT_NOTES.md`` for the
            project naming convention.

            Why "dep_key" and not ``role``: the canonical character
            archetypes in this project are called *roles*
            (``data/roles/instructions/``), and ``roles/vectors`` is
            already a manifest subtree -- having ``InputSpec.role =
            "roles/vectors"`` would be an avoidable collision.
        path: Repo-relative path to the input.  For dataset-subtree
            inputs this is ``<dataset_root_rel>/<subtree>``; for files
            it's the full repo-relative path to the file.
        fingerprint: Versioned compact freshness signal.  Always
            prefixed with the current ``FINGERPRINT_VERSION_TAG`` so
            future format upgrades have a clean migration path.
            Current formats:

            - subtree: ``"v1:{dataset_id}@{summary_sha256[:12]}"``
            - file:    ``"v1:{mtime_iso}@{size}"``
        kind: ``"subtree"`` or ``"file"``.
        dataset_id: The dataset's ``dataset_id`` from ``MANIFEST.json``
            when ``kind == "subtree"``; ``None`` for plain files.
        last_modified_at: ISO-8601 UTC timestamp of the input's most
            recent modification at the time the InputSpec was built.
        extras: Free-form discriminators (slot, layer, K-range, ...);
            advisory only -- not used in equality / drift comparisons.
        member_paths: For ``kind == "multi"`` only: the repo-relative
            paths of the constituent files.  Allows a downstream reader
            to recompute the multi fingerprint from the same file set
            and detect drift.  Without it, multi fingerprints are
            write-only diagnostics (legacy multi InputSpecs are
            classified ``unverifiable`` by :func:`load_validated_json`).
            ``None`` for non-multi kinds.
    """
    dep_key: str
    path: str
    fingerprint: str
    kind: str
    dataset_id: Optional[str] = None
    last_modified_at: Optional[str] = None
    extras: dict = field(default_factory=dict)
    member_paths: Optional[list] = None  # list[str] | None


@dataclass(frozen=True)
class ManifestSubtree:
    """One row from a dataset's ``MANIFEST.json``."""
    name: str
    kind: str          # "raw" or "derived"
    recurse: bool
    count: int
    total_bytes: int
    newest_mtime: str
    summary_sha256: str


@dataclass(frozen=True)
class Manifest:
    """Typed read-only view of a dataset's ``MANIFEST.json``."""
    dataset_id: str
    schema_version: str
    fingerprint_kind: str
    manifest_generated_at: str
    subtree_summaries: dict      # name -> ManifestSubtree
    data_dir: Path                # absolute path to the dataset root
    raw: dict                     # the full parsed JSON (escape hatch)

    def subtree(self, name: str) -> ManifestSubtree:
        """Return one subtree's summary, raising ``KeyError`` if missing."""
        try:
            return self.subtree_summaries[name]
        except KeyError as e:
            available = ", ".join(sorted(self.subtree_summaries)[:6])
            raise KeyError(
                f"subtree {name!r} not in MANIFEST.json for {self.data_dir}; "
                f"available (first 6): {available}, ..."
            ) from e


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InputStatus:
    dep_key: str
    status: str          # "ok" | "drift" | "missing_current" | "missing_recorded"
    recorded: Optional[InputSpec] = None
    current: Optional[InputSpec] = None
    detail: str = ""


@dataclass(frozen=True)
class ProvenanceCheck:
    """Per-input drift report built by :func:`validate_inputs`."""
    statuses: list           # list[InputStatus]
    ok: bool                 # True iff all statuses have status == "ok"

    def drifted(self) -> list:
        return [s for s in self.statuses if s.status == "drift"]

    def missing(self) -> list:
        return [s for s in self.statuses
                if s.status in ("missing_current", "missing_recorded")]

    def summary(self) -> str:
        lines = []
        for s in self.statuses:
            line = f"  [{s.status:>17s}] {s.dep_key}"
            if s.detail:
                line += f"  -- {s.detail}"
            lines.append(line)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Repo-root resolution (for path normalisation)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Locate the repository root (the dir containing ``.git``).

    Walks up from this module's location, which is at
    ``<repo>/assistant_axis/provenance.py``.  Falls back to the cwd if
    no .git is found (e.g. running outside a git checkout).
    """
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


def _to_repo_relative(path: Path) -> str:
    """Normalize a path to a forward-slash repo-relative string.  If the
    path is outside the repo, return its absolute form."""
    p = Path(path).resolve()
    root = _repo_root()
    try:
        rel = p.relative_to(root)
    except ValueError:
        return str(p).replace(os.sep, "/")
    return str(rel).replace(os.sep, "/")


# ---------------------------------------------------------------------------
# Manifest reading
# ---------------------------------------------------------------------------

def read_manifest(data_dir: Path) -> Manifest:
    """Load ``data_dir / 'MANIFEST.json'`` and return a typed view.

    Raises:
        FileNotFoundError: if no MANIFEST.json is present.  Suggests the
            ``tools/regenerate_dataset_manifest.py`` regeneration command.
        ValueError: if the schema is unrecognised.
    """
    data_dir = Path(data_dir)
    p = data_dir / MANIFEST_FILENAME
    if not p.exists():
        raise FileNotFoundError(
            f"No {MANIFEST_FILENAME} in {data_dir}.  Regenerate via:\n"
            f"    uv run python tools/regenerate_dataset_manifest.py "
            f"--dataset {str(data_dir)!r}"
        )
    raw = json.loads(p.read_text())
    schema_version = raw.get("schema_version", "?")
    if schema_version not in ("1.0",):
        raise ValueError(
            f"Unsupported MANIFEST.json schema_version {schema_version!r} at {p}; "
            f"this code understands 1.0."
        )
    summaries: dict[str, ManifestSubtree] = {}
    for name, blob in raw.get("subtree_summaries", {}).items():
        summaries[name] = ManifestSubtree(
            name=name,
            kind=blob["kind"],
            recurse=bool(blob.get("recurse", False)),
            count=int(blob["count"]),
            total_bytes=int(blob["total_bytes"]),
            newest_mtime=blob["newest_mtime"],
            summary_sha256=blob["summary_sha256"],
        )
    return Manifest(
        dataset_id=raw["dataset_id"],
        schema_version=schema_version,
        fingerprint_kind=raw.get("fingerprint_kind", "unknown"),
        manifest_generated_at=raw["manifest_generated_at"],
        subtree_summaries=summaries,
        data_dir=data_dir.resolve(),
        raw=raw,
    )


# ---------------------------------------------------------------------------
# InputSpec builders (writer-side)
# ---------------------------------------------------------------------------

def current_data_subtree_input(
    data_dir: Path,
    subtree_rel: str,
    dep_key: str,
    *,
    extras: Optional[dict] = None,
    manifest: Optional[Manifest] = None,
) -> InputSpec:
    """Build an :class:`InputSpec` describing one dataset subtree.

    Args:
        data_dir: Dataset root.
        subtree_rel: Subtree name as it appears in ``MANIFEST.json``
            (e.g. ``"traits/vectors"``,
            ``"combinations/vectors/derived/marginals/r_goal"``).
        dep_key: Caller-chosen abbreviated name for this dependency.
            See :class:`InputSpec` for the naming convention.
        extras: Optional per-call discriminators (e.g. ``{"slot": "6"}``).
        manifest: Pre-loaded :class:`Manifest`; if omitted, we read it
            from disk.

    Returns:
        InputSpec with fingerprint
        ``"v1:{dataset_id}@{summary_sha256[:12]}"``, ``kind="subtree"``,
        path ``"<dataset_root_rel>/<subtree_rel>"``.
    """
    if manifest is None:
        manifest = read_manifest(data_dir)
    sub = manifest.subtree(subtree_rel)
    dataset_root_rel = _to_repo_relative(manifest.data_dir)
    full_rel = f"{dataset_root_rel}/{subtree_rel}"
    fp = (f"{FINGERPRINT_VERSION_TAG}:{manifest.dataset_id}"
          f"@{sub.summary_sha256[:_SUBTREE_SHA_PREFIX_LEN]}")
    return InputSpec(
        dep_key=dep_key,
        path=full_rel,
        fingerprint=fp,
        kind="subtree",
        dataset_id=manifest.dataset_id,
        last_modified_at=sub.newest_mtime,
        extras=dict(extras or {}),
    )


def current_file_input(
    dep_key: str,
    path: Path,
    *,
    extras: Optional[dict] = None,
) -> InputSpec:
    """Build an :class:`InputSpec` for a single file (cache JSON, axis spec, ...).

    Fingerprint is ``"v1:{mtime_iso}@{size}"`` over ``os.stat``
    (follows symlinks -- so a symlink fingerprint reflects the
    target's stat, which is what we want for "did the data this
    points at change?" semantics).  ``size`` goes last because it's
    variable-length and we want the fixed-format mtime to anchor any
    prefix-based parser.

    Mtime is floored to whole seconds.  Roger's standard workflow
    (RunPod -> NFS -> rsync -> Mac) hands us second-precision mtimes
    on every transfer; storing nanos here would mostly waste space
    and would false-positive any time a file arrives via a
    sub-second-preserving path.  Phase 6 (content hashes) is the
    upgrade path for sub-second-precision drift detection.

    Use ``current_data_subtree_input`` for files that are part of a
    managed dataset subtree (those go through MANIFEST.json instead).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"current_file_input: {p} does not exist (dep_key={dep_key!r})"
        )
    st = os.stat(p)
    # Truncate to whole seconds (drops sub-second component) so
    # rsync-rounded and natively-stored mtimes produce the same
    # fingerprint.
    mtime_iso = _dt.datetime.fromtimestamp(
        int(st.st_mtime), tz=_dt.timezone.utc
    ).isoformat()
    return InputSpec(
        dep_key=dep_key,
        path=_to_repo_relative(p),
        fingerprint=f"{FINGERPRINT_VERSION_TAG}:{mtime_iso}@{st.st_size}",
        kind="file",
        dataset_id=None,
        last_modified_at=mtime_iso,
        extras=dict(extras or {}),
    )


def current_files_input(
    dep_key: str,
    paths: Iterable[Path],
    *,
    extras: Optional[dict] = None,
) -> InputSpec:
    """Build an :class:`InputSpec` summarising a heterogeneous *set* of files
    (e.g. per-axis judge caches, scattered config files) into one composite
    fingerprint.

    Use this when a writer fans out over many small inputs that aren't
    naturally a managed dataset subtree.  Examples:

    * ``whitening_k_sweep.py``: ~132 per-axis judge caches at
      ``roger/axis_judge_experiments/<axis>/{gpt,sonnet}/scores_*.json``.
    * ``batch_size_rho_curve.py``: per-batch-size cache fan-out.

    Granularity rationale: the question we want answered downstream is
    "do I need to rebuild?", not "which file in the set changed".  A
    composite fingerprint answers the former cheaply; if you need the
    latter for debugging, re-stat the files and compare to the
    recorded sub-list (the writer can always log it on demand, or we
    can add it to ``extras`` per-call).

    Fingerprint shape: ``"v1:multi:{sha256[:12]}"`` over the sorted JSON
    list ``[(rel_path, mtime_seconds, size), ...]`` of every existing
    path.  Non-existent paths are silently skipped (lets writers iterate
    over an "expected" set that includes optional caches; see the
    ``responses`` files in ``whitening_k_sweep.py``).

    If *every* path is missing, returns a sentinel
    ``"v1:multi:empty"`` fingerprint -- still a valid InputSpec so the
    declared dependency stays visible to auditors, but obviously
    distinguishable from any real fingerprint.

    The ``path`` field is set to the longest common path prefix when
    there's more than one file (advisory; useful for human inspection),
    or the single file's path when there's exactly one.

    The ``last_modified_at`` field is the max mtime across the set
    (ISO-8601 UTC, second precision).  Useful for human inspection
    even when the fingerprint matches.
    """
    # Materialise once; ``paths`` may be a generator.
    paths = [Path(p) for p in paths]
    triples: list[tuple[str, int, int]] = []
    rels: list[str] = []
    newest_mtime_secs = 0
    for p in paths:
        if not p.exists():
            continue
        st = os.stat(p)
        rel = _to_repo_relative(p)
        # Floor mtime to whole seconds for rsync stability (see
        # ``current_file_input`` docstring).
        mtime_secs = int(st.st_mtime)
        triples.append((rel, mtime_secs, int(st.st_size)))
        rels.append(rel)
        if mtime_secs > newest_mtime_secs:
            newest_mtime_secs = mtime_secs

    # Member paths capture the *full* expected set (including missing
    # ones) so a downstream reader can re-stat them and recompute the
    # fingerprint -- including detecting "a file that was missing at
    # write-time has since appeared" as drift.  This is symmetric with
    # the read-time treatment in ``_current_for_recorded``.
    all_member_rels: list[str] = []
    for p in paths:
        all_member_rels.append(_to_repo_relative(Path(p)))
    all_member_rels = sorted(set(all_member_rels))

    if not triples:
        return InputSpec(
            dep_key=dep_key,
            path="(empty)",
            fingerprint=f"{FINGERPRINT_VERSION_TAG}:multi:empty",
            kind="multi",
            dataset_id=None,
            last_modified_at=None,
            extras=dict(extras or {}),
            member_paths=all_member_rels or None,
        )

    triples.sort()
    blob = json.dumps(triples, separators=(",", ":")).encode("utf-8")
    sha = hashlib.sha256(blob).hexdigest()
    fp = f"{FINGERPRINT_VERSION_TAG}:multi:{sha[:_SUBTREE_SHA_PREFIX_LEN]}"

    path = rels[0] if len(rels) == 1 else os.path.commonpath(rels)
    newest_iso = _dt.datetime.fromtimestamp(
        newest_mtime_secs, tz=_dt.timezone.utc).isoformat()

    return InputSpec(
        dep_key=dep_key,
        path=path,
        fingerprint=fp,
        kind="multi",
        dataset_id=None,
        last_modified_at=newest_iso,
        extras=dict(extras or {}),
        member_paths=all_member_rels,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_inputs(
    recorded: Iterable[InputSpec],
    current: Iterable[InputSpec],
) -> ProvenanceCheck:
    """Compare two lists of :class:`InputSpec` by ``dep_key``; return
    per-input status.

    A drift is any of:

    * ``dep_key`` present in ``recorded`` but absent in ``current``
      (``missing_current``); the dependency vanished.
    * ``dep_key`` present in ``current`` but absent in ``recorded``
      (``missing_recorded``); typically not an error -- the caller may
      have added a new dependency post-record -- but flagged so the
      caller can decide.
    * Both present but ``fingerprint`` differs (``drift``).

    Returns a :class:`ProvenanceCheck` whose ``ok`` field is ``True``
    iff every ``dep_key`` is matched and fingerprints agree.
    """
    rec_by_key: dict[str, InputSpec] = {s.dep_key: s for s in recorded}
    cur_by_key: dict[str, InputSpec] = {s.dep_key: s for s in current}
    statuses: list[InputStatus] = []
    all_keys = sorted(set(rec_by_key) | set(cur_by_key))
    for k in all_keys:
        r = rec_by_key.get(k)
        c = cur_by_key.get(k)
        if r is None:
            statuses.append(InputStatus(
                dep_key=k, status="missing_recorded",
                recorded=None, current=c,
                detail=("recorded list has no entry for this dep_key; "
                        "caller may have added a new dependency."),
            ))
            continue
        if c is None:
            statuses.append(InputStatus(
                dep_key=k, status="missing_current",
                recorded=r, current=None,
                detail="dependency vanished; the input no longer exists.",
            ))
            continue
        if r.fingerprint != c.fingerprint:
            statuses.append(InputStatus(
                dep_key=k, status="drift",
                recorded=r, current=c,
                detail=f"fingerprint changed: {r.fingerprint} -> {c.fingerprint}",
            ))
            continue
        statuses.append(InputStatus(
            dep_key=k, status="ok", recorded=r, current=c,
        ))
    ok = all(s.status == "ok" for s in statuses)
    return ProvenanceCheck(statuses=statuses, ok=ok)


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

def inputs_to_jsonable(specs: Iterable[InputSpec]) -> list[dict]:
    """Serialise a list of :class:`InputSpec` for inclusion in a PNG
    iTXt chunk or a JSON cache's ``_provenance.inputs`` field."""
    out: list[dict] = []
    for s in specs:
        d = asdict(s)
        # Drop ``member_paths`` for non-multi inputs to keep records
        # tidy (it's always None for those).  Round-trip is preserved
        # because ``inputs_from_jsonable`` re-defaults to None.
        if d.get("member_paths") is None:
            d.pop("member_paths", None)
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Reader-side helpers (Phase 4)
# ---------------------------------------------------------------------------

CACHE_POLICIES = ("strict", "warn", "rebuild", "off")


class StaleCacheError(Exception):
    """Raised by :func:`load_validated_json` under ``policy="strict"``
    (or ``"rebuild"`` without a callback) when a recorded provenance
    drifts from current state.

    Attributes:
        path: The cache file we tried to load.
        check: The :class:`ProvenanceCheck` describing the drift.

    Example::

        try:
            data, _ = load_validated_json(cache_path, policy="strict")
        except StaleCacheError as e:
            print(e.check.summary())
            sys.exit(1)
    """

    def __init__(self, path: Path, check: "ProvenanceCheck"):
        self.path = path
        self.check = check
        msg = (f"Stale cache: {path}\n"
               f"  drifted/missing inputs:\n{check.summary()}")
        super().__init__(msg)


class _UnverifiableInput(Exception):
    """Internal: raised when we can't compute current state for a recorded
    InputSpec (e.g. legacy multi without member_paths)."""


def _find_dataset_root(rel_path: str) -> Optional[Path]:
    """Walk up from ``<repo>/rel_path`` looking for ``MANIFEST.json``.
    Returns ``None`` if no manifest is found anywhere up the chain."""
    p = (_repo_root() / rel_path).resolve()
    if p.is_file():
        p = p.parent
    for ancestor in [p, *p.parents]:
        if (ancestor / MANIFEST_FILENAME).exists():
            return ancestor
    return None


def current_for_recorded(spec: InputSpec) -> InputSpec:
    """Re-derive the *current* :class:`InputSpec` for a previously-recorded one.

    Dispatches on ``spec.kind``:

    - ``"subtree"``: walks up ``spec.path`` looking for the dataset
      root's ``MANIFEST.json``, then re-fingerprints the named subtree.
    - ``"file"``: re-stats the file at ``spec.path``.
    - ``"multi"``: re-stats every ``spec.member_paths`` entry and
      recomputes the composite fingerprint.  Raises
      :class:`_UnverifiableInput` if ``member_paths`` is missing
      (legacy multi spec) -- callers should treat that case as
      "unverifiable" rather than "drift".

    Raises:
        FileNotFoundError: file/manifest vanished.
        KeyError: subtree was renamed/removed in the manifest.
        ValueError: unknown ``kind``.
        _UnverifiableInput: legacy multi spec without member_paths.
    """
    if spec.kind == "subtree":
        root = _find_dataset_root(spec.path)
        if root is None:
            raise FileNotFoundError(
                f"No MANIFEST.json found above {spec.path!r}; "
                f"cannot revalidate subtree input."
            )
        full_abs = (_repo_root() / spec.path).resolve()
        try:
            sub_rel = full_abs.relative_to(root)
        except ValueError as e:
            raise FileNotFoundError(
                f"Recorded subtree path {spec.path!r} not under "
                f"discovered dataset root {root}; broken layout?"
            ) from e
        return current_data_subtree_input(
            data_dir=root,
            subtree_rel=str(sub_rel).replace(os.sep, "/"),
            dep_key=spec.dep_key,
            extras=dict(spec.extras or {}),
        )
    if spec.kind == "file":
        return current_file_input(
            dep_key=spec.dep_key,
            path=_repo_root() / spec.path,
            extras=dict(spec.extras or {}),
        )
    if spec.kind == "multi":
        if not spec.member_paths:
            raise _UnverifiableInput(
                f"multi input {spec.dep_key!r} has no recorded "
                f"member_paths (likely written before that field "
                f"existed); regenerate the cache to enable validation."
            )
        return current_files_input(
            dep_key=spec.dep_key,
            paths=[_repo_root() / mp for mp in spec.member_paths],
            extras=dict(spec.extras or {}),
        )
    raise ValueError(f"Unknown InputSpec.kind {spec.kind!r}")


def validate_recorded(
    recorded: Iterable[InputSpec],
) -> ProvenanceCheck:
    """Compute current state for each recorded input and produce a
    :class:`ProvenanceCheck`.

    Differs from :func:`validate_inputs` in that the caller does not
    have to provide a ``current`` list; this helper re-derives current
    state from each recorded :class:`InputSpec` via
    :func:`current_for_recorded`.  Used by audits / reader-side
    helpers (notably :func:`load_validated_json`).

    Status semantics:

    - ``ok``: recorded fingerprint matches the freshly-recomputed
      current fingerprint.
    - ``drift``: both exist but fingerprints differ.
    - ``missing_current``: file vanished or manifest disappeared
      since the record was made.
    - ``unverifiable``: e.g. legacy multi-input without
      ``member_paths``; can't recompute the current fingerprint.
    """
    recorded = list(recorded)
    statuses: list[InputStatus] = []
    for r in recorded:
        try:
            c = current_for_recorded(r)
        except _UnverifiableInput as e:
            statuses.append(InputStatus(
                dep_key=r.dep_key, status="unverifiable",
                recorded=r, current=None, detail=str(e),
            ))
            continue
        except (FileNotFoundError, KeyError) as e:
            statuses.append(InputStatus(
                dep_key=r.dep_key, status="missing_current",
                recorded=r, current=None, detail=str(e),
            ))
            continue
        if r.fingerprint == c.fingerprint:
            statuses.append(InputStatus(
                dep_key=r.dep_key, status="ok",
                recorded=r, current=c,
            ))
        else:
            statuses.append(InputStatus(
                dep_key=r.dep_key, status="drift",
                recorded=r, current=c,
                detail=f"fingerprint changed: {r.fingerprint} -> {c.fingerprint}",
            ))
    ok = all(s.status == "ok" for s in statuses)
    return ProvenanceCheck(statuses=statuses, ok=ok)


def load_validated_json(
    path: Path,
    *,
    policy: str = "warn",
    rebuild_callback=None,
):
    """Load a JSON file (envelope-aware) and validate its recorded
    inputs against current state.

    Args:
        path: JSON file to load.
        policy: Drift handling.  One of:

            * ``"strict"`` -- raise :class:`StaleCacheError` on any
              drift / missing / unverifiable.
            * ``"warn"`` (default) -- print a summary to stderr and
              return the payload anyway.
            * ``"rebuild"`` -- if ``rebuild_callback`` is provided,
              call ``rebuild_callback(path, check)`` (it should bring
              the cache back to currency) and re-validate; else
              behaves like ``"strict"``.
            * ``"off"`` -- skip validation entirely; just return the
              payload (with the envelope still unwrapped if present).

        rebuild_callback: Optional ``Callable[[Path, ProvenanceCheck], None]``
            invoked under ``policy="rebuild"``.  After it returns, the
            file is reloaded and re-validated; if drift persists, a
            :class:`StaleCacheError` is raised.

    Returns:
        ``(payload, check)`` where:

        * ``payload`` is the unwrapped result list/dict.  When the
          loaded JSON has no provenance envelope (legacy or hand-
          written), ``payload`` is the raw decoded JSON.
        * ``check`` is the :class:`ProvenanceCheck` from the
          revalidation pass.  ``None`` for legacy files without an
          envelope, or when ``policy="off"``.

    Notes:
        ``policy="off"`` skips validation but still unwraps the
        envelope, so callers can use it as a one-liner replacement for
        ``json.load`` that quietly tolerates either format.
    """
    if policy not in CACHE_POLICIES:
        raise ValueError(
            f"Unknown cache policy {policy!r}; "
            f"choose from {CACHE_POLICIES}.")

    path = Path(path)
    obj = json.loads(path.read_text(encoding="utf-8"))

    # Detect envelope.  The schema is ``{"result": <payload>, "_provenance": {...}}``.
    has_envelope = (
        isinstance(obj, dict)
        and "_provenance" in obj
        and "result" in obj
    )
    payload = obj["result"] if has_envelope else obj

    if policy == "off" or not has_envelope:
        return payload, None

    recorded = inputs_from_jsonable(obj["_provenance"].get("inputs", []))
    check = validate_recorded(recorded)

    if check.ok:
        return payload, check

    if policy == "warn":
        import sys
        sys.stderr.write(
            f"[provenance] {path}: drift detected (policy=warn, returning "
            f"payload anyway):\n{check.summary()}\n"
        )
        return payload, check

    if policy == "rebuild" and rebuild_callback is not None:
        rebuild_callback(path, check)
        # Re-load + re-validate after the callback.
        obj = json.loads(path.read_text(encoding="utf-8"))
        if not (isinstance(obj, dict)
                and "_provenance" in obj and "result" in obj):
            raise StaleCacheError(path, check)
        payload = obj["result"]
        recorded = inputs_from_jsonable(
            obj["_provenance"].get("inputs", []))
        check = validate_recorded(recorded)
        if check.ok:
            return payload, check
        # Still drifted -- callback didn't fix it.
        raise StaleCacheError(path, check)

    # strict, or rebuild without a callback.
    raise StaleCacheError(path, check)


def inputs_from_jsonable(blobs: Iterable[dict]) -> list[InputSpec]:
    """Inverse of :func:`inputs_to_jsonable`.  Tolerates blobs missing
    the optional fields (``dataset_id``, ``last_modified_at``,
    ``extras``, ``member_paths``) for forward and backward
    compatibility."""
    out: list[InputSpec] = []
    for b in blobs:
        mp = b.get("member_paths")
        if mp is not None:
            mp = list(mp)
        out.append(InputSpec(
            dep_key=b["dep_key"],
            path=b["path"],
            fingerprint=b["fingerprint"],
            kind=b.get("kind", "file"),
            dataset_id=b.get("dataset_id"),
            last_modified_at=b.get("last_modified_at"),
            extras=dict(b.get("extras") or {}),
            member_paths=mp,
        ))
    return out
