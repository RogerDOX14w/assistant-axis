#!/usr/bin/env python3
"""Audit a vectors/ directory against its source activations/ and
scores/ directories, classifying why each missing vector is missing.

Motivation
----------
On RunPod / NFS we have observed three distinct failure modes in step 4
(``pipeline/4_vectors.py``):

    1. **Legitimate** misses -- the activation file exists but a
       vector cannot be computed:

         * the scores file is absent (judging never ran, or was
           interrupted before this entity); OR
         * the score=3 count is below ``--min_count``; OR
         * the activation tensor for the entity is empty / all-NaN.

    2. **Mysterious** misses -- everything upstream looks fine, the
       activation file is full-size and loadable, the scores file has
       enough score=3 entries, yet step 4 produced no vector.  These
       are almost always caused by transient NFS read failures that
       step 4 logged as warnings and skipped (the bug that motivated
       the project-standard 5-attempt retry rolled out alongside this
       script).  Re-running step 4 with ``--overwrite`` on just these
       entities is enough to recover.

    3. **Corrupt-on-write vectors** -- the vector file exists at the
       expected size, but ``torch.load`` raises ``RuntimeError`` /
       ``EOFError`` ("storage has wrong byte size of dtype" /
       "PytorchStreamReader failed reading zip archive: ... unexpected
       EOF, expected N more bytes") on read.  This is the failure
       mode the post-write size-sanity check in
       ``torch_save_with_retry`` was added to catch on the writer
       side; the scanner now actively loads each vector to detect any
       that slipped through before the check was in place.

The script also flags **truncated activation files** (anything whose
on-disk size is dramatically smaller than the median size of its
peers) as a separate category, since those are the upstream bug that
caused the original ``r_guardian__casual.pt`` corruption.

Usage
-----

**Comprehensive mode** (recommended).  Point the scanner at an
output root and it auto-discovers every entity-type subdir
(``default/``, ``roles/``, ``traits/``, ``combinations/``, ...) with
an ``activations/`` subdir, and scans every sibling ``vectors*``
variant (``vectors/``, ``vectors_unfiltered/``, etc.) that contains
real (non-symlinked) ``.pt`` files::

    uv run pipeline/scan_missing_vectors.py \\
        --root outputs/qwen-3-32b/ \\
        --min_count 50

**Single-pair mode** (back-compat with earlier invocations)::

    uv run pipeline/scan_missing_vectors.py \\
        --activations_dir outputs/qwen-3-32b/roles/activations \\
        --vectors_dir     outputs/qwen-3-32b/roles/vectors \\
        --scores_dir      outputs/qwen-3-32b/roles/scores \\
        --min_count       50

For unfiltered (mean-of-all-activations) vectors, drop ``--scores_dir``
and use ``--mode unfiltered`` (single-pair) or just leave a directory
named ``vectors_unfiltered/`` next to the activations (comprehensive
mode auto-detects per-vectors-dir).

Outputs a per-entity JSON report next to each scanned vectors dir
(``missing_vectors_audit.json``) plus a re-run list
(``missing_vectors_rerun.txt``) for the suspects that need step 4
re-runs.  Prints a summary table to stdout.  Entities classified as
``mysterious``, ``corrupt_or_truncated_activation``, ``corrupt_vector``,
or ``ok_zero_size`` are the ones worth re-running.
"""
from __future__ import annotations

import argparse
import json
import logging
import pickle
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import torch
from tqdm import tqdm

# Errors we treat as "this file is unreadable" when classifying.
# torch.load on a corrupt-on-write or short-read file can raise any
# of these; we don't retry past atomic_io's own retry loop here, just
# label the file as corrupt.  pickle.UnpicklingError covers
# "_pickle.UnpicklingError: pickle data was truncated" / "invalid
# load key", which is a parse error (per Roger's "don't retry parse
# errors" rule) but still indicates a genuinely broken file we should
# flag for re-run.
LOAD_FAILURE_ERRORS: tuple[type[BaseException], ...] = (
    RuntimeError, OSError, EOFError, pickle.UnpicklingError, ValueError,
)

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant_axis.atomic_io import (  # noqa: E402
    read_text_with_retry,
    torch_load_with_retry,
)

logger = logging.getLogger("pipeline.scan_missing_vectors")


# Activation files smaller than this fraction of the median peer-group
# file size are flagged as "suspiciously small / likely truncated".
TRUNCATION_RATIO = 0.5
# Vector files smaller than this many bytes are treated as suspect.
# A healthy bf16 (n_slots × n_layers × hidden) vector is in the low MB;
# even a tiny smoke-test tensor pickled by torch.save is ~700 bytes.
# Anything under 256 bytes is almost certainly a stub / aborted write.
MIN_HEALTHY_VECTOR_BYTES = 256

# Statuses that should be re-run by step 4.  Kept in one place so the
# stdout summary, the rerun list and any callers stay in sync.
RERUN_STATUSES = (
    "mysterious",
    "corrupt_or_truncated_activation",
    "corrupt_vector",
    "ok_zero_size",
)

# Status display order for the summary table.
ALL_STATUSES = (
    "ok",
    "ok_zero_size",
    "missing_activation",
    "corrupt_or_truncated_activation",
    "corrupt_vector",
    "missing_scores",
    "below_min_count",
    "all_nan_or_empty",
    "mysterious",
    "orphan_vector",
)


# ---------------------------------------------------------------------------
# Per-entity classification
# ---------------------------------------------------------------------------

def _question_index(key: str) -> int:
    return int(key.rsplit("_q", 1)[1])


def _keep_by_reduce(key: str, reduce_questions: int) -> bool:
    if reduce_questions <= 1:
        return True
    return _question_index(key) % reduce_questions == 0


def classify_entity(
    role: str,
    act_file: Path,
    median_act_size: int,
    vectors_dir: Path,
    scores_dir: Path | None,
    min_count: int,
    reduce_questions: int,
    mode: str,
    deep_load: bool,
    load_check: bool,
) -> dict[str, Any]:
    """Classify a single entity.

    See module docstring for the status taxonomy.  Returns a dict
    with at minimum ``role`` and ``status`` plus category-specific
    extras (sizes, counts, reasons).
    """
    out: dict[str, Any] = {"role": role}

    vec_file = vectors_dir / f"{role}.pt"
    has_vector = vec_file.exists()
    out["vector_path"] = str(vec_file)
    out["activation_path"] = str(act_file)
    out["activation_size_bytes"] = act_file.stat().st_size if act_file.exists() else 0

    # 1. Activation upstream check.
    if not act_file.exists():
        out["status"] = "missing_activation"
        return out

    if median_act_size > 0 and out["activation_size_bytes"] < median_act_size * TRUNCATION_RATIO:
        out["status"] = "corrupt_or_truncated_activation"
        out["median_peer_bytes"] = median_act_size
        out["ratio_to_median"] = out["activation_size_bytes"] / median_act_size
        return out

    # 2. Vector exists?
    if has_vector:
        size = vec_file.stat().st_size
        out["vector_size_bytes"] = size
        if size < MIN_HEALTHY_VECTOR_BYTES:
            out["status"] = "ok_zero_size"
            return out

        # 2b. Vector loadability check.  This catches the
        # "corrupt-on-write" failure mode where the file is at the
        # expected size but torch.load raises RuntimeError / EOFError
        # because pickle / safetensors content is malformed.  Use a
        # short retry schedule -- a corrupt file won't recover from
        # waiting, but one quick retry gives NFS a chance to clear a
        # one-off hiccup.
        if load_check:
            try:
                torch_load_with_retry(
                    vec_file, map_location="cpu", weights_only=False,
                    delays_s=[5.0], logger_obj=logger,
                )
            except LOAD_FAILURE_ERRORS as e:
                out["status"] = "corrupt_vector"
                out["note"] = f"vector .pt unreadable: {type(e).__name__}: {e}"
                return out

        out["status"] = "ok"
        return out

    # 3. Vector missing -- figure out why.
    is_default = "default" in role or mode == "unfiltered"

    if not is_default:
        if scores_dir is None:
            out["status"] = "mysterious"
            out["note"] = "filtered mode requested but no scores_dir provided"
            return out
        scores_file = scores_dir / f"{role}.json"
        if not scores_file.exists():
            out["status"] = "missing_scores"
            return out

        try:
            scores = json.loads(read_text_with_retry(scores_file, logger_obj=logger))
        except (OSError, RuntimeError, EOFError, json.JSONDecodeError) as e:
            out["status"] = "mysterious"
            out["note"] = f"scores file unreadable: {e}"
            return out

        # Cheap path: count score=3 entries from the scores dict alone,
        # without loading the activation tensor.  Step 4 also requires
        # the matching activation key to be present, so this is an
        # upper bound on the realised score=3 count.  If it's already
        # below min_count, we're done.
        score3_in_scores = sum(
            1 for k, v in scores.items()
            if v == 3 and _keep_by_reduce(k, reduce_questions)
        )
        out["score3_in_scores"] = score3_in_scores
        if score3_in_scores < min_count:
            out["status"] = "below_min_count"
            return out

    if not deep_load:
        # Skip the expensive activation-load step: any other case is
        # presumed mysterious until a deep load disagrees.
        out["status"] = "mysterious"
        out["note"] = "shallow scan (--deep_load disabled)"
        return out

    # 4. Deep check: load the activation tensor and recompute the
    # filter to confirm whether step 4 *should* have produced a
    # vector.  Use a fast retry schedule (one short retry) rather
    # than the project-standard [5,20,60,180]s -- a corrupt file
    # won't recover, and waiting 4+ minutes per corrupt file makes
    # auditing thousands of files painful.  One 5 s retry still
    # gives NFS a chance to clear a one-off hiccup.
    try:
        data = torch_load_with_retry(
            act_file, map_location="cpu", weights_only=False,
            delays_s=[5.0],
            logger_obj=logger,
        )
    except LOAD_FAILURE_ERRORS as e:
        out["status"] = "corrupt_or_truncated_activation"
        out["note"] = f"activation .pt unloadable: {type(e).__name__}: {e}"
        return out

    data.pop("metadata", None)
    if not data:
        out["status"] = "all_nan_or_empty"
        out["note"] = "activation file contains no tensors"
        return out

    if is_default:
        all_acts = [act for k, act in data.items() if _keep_by_reduce(k, reduce_questions)]
        out["activation_count"] = len(all_acts)
        if not all_acts:
            out["status"] = "all_nan_or_empty"
            return out
        # Any non-NaN entries?
        any_finite = any(torch.isfinite(a).any().item() for a in all_acts)
        if not any_finite:
            out["status"] = "all_nan_or_empty"
            return out
        out["status"] = "mysterious"
        return out

    # Filtered mode.
    matched = [
        act for k, act in data.items()
        if k in scores and scores[k] == 3 and _keep_by_reduce(k, reduce_questions)
    ]
    out["score3_matched"] = len(matched)
    if len(matched) < min_count:
        out["status"] = "below_min_count"
        out["note"] = (f"score3 in scores file = {out['score3_in_scores']}, "
                       f"actually realised in activations = {len(matched)}")
        return out

    any_finite = any(torch.isfinite(a).any().item() for a in matched)
    if not any_finite:
        out["status"] = "all_nan_or_empty"
        return out

    out["status"] = "mysterious"
    return out


# ---------------------------------------------------------------------------
# Comprehensive scan target discovery
# ---------------------------------------------------------------------------

@dataclass
class ScanTarget:
    """One (activations, vectors, optional scores) triple to scan."""
    entity_type: str          # "roles" / "traits" / "combinations" / "default" / ...
    vectors_variant: str      # "vectors" / "vectors_unfiltered" / "vectors_pca" / ...
    activations_dir: Path
    vectors_dir: Path
    scores_dir: Optional[Path] = None
    mode: str = "filtered"

    @property
    def label(self) -> str:
        return f"{self.entity_type}/{self.vectors_variant}"


def _is_skippable_vectors_dir(vec_dir: Path) -> tuple[bool, str]:
    """True if the directory has no real vector content.

    Skippable means:
      - directory empty, OR
      - all .pt files are symlinks (typically the default.pt symlink
        pointing at ../../default/vectors/default.pt that step 4 sets
        up as a baseline reference -- not a vector this dir actually
        owns).

    Returns (skippable, reason) for logging.
    """
    pt_files = list(vec_dir.glob("*.pt"))
    if not pt_files:
        return True, "empty (no .pt files)"
    real_files = [f for f in pt_files if not f.is_symlink()]
    if not real_files:
        return True, f"only {len(pt_files)} symlinks (default-only)"
    return False, ""


def discover_scan_targets(root: Path) -> list[ScanTarget]:
    """Walk `root` for entity-type subdirs and yield one ScanTarget per
    non-empty ``vectors*`` variant.

    An entity-type subdir is any directory at the root level that
    contains an ``activations/`` subdir.  Each entity-type subdir may
    contain zero or more ``vectors*`` subdirs (``vectors``,
    ``vectors_unfiltered``, ...); we emit one ScanTarget per non-skippable
    one.  ``scores/`` is included if present (filtered mode); otherwise
    the target is run in unfiltered mode.

    Default entity-type subdirs (``default/``) typically contain a
    single ``default.pt`` and no scores; they're handled with mode=
    unfiltered automatically.
    """
    targets: list[ScanTarget] = []
    if not root.is_dir():
        raise ValueError(f"--root path is not a directory: {root}")

    for entity_dir in sorted(root.iterdir()):
        if not entity_dir.is_dir():
            continue
        act_dir = entity_dir / "activations"
        if not act_dir.is_dir():
            continue
        scores_dir = entity_dir / "scores"
        if not scores_dir.is_dir():
            scores_dir = None

        for vec_dir in sorted(entity_dir.iterdir()):
            if not vec_dir.is_dir():
                continue
            if not vec_dir.name.startswith("vectors"):
                continue
            skippable, reason = _is_skippable_vectors_dir(vec_dir)
            if skippable:
                logger.info(f"[skip] {vec_dir} ({reason})")
                continue
            mode = "filtered" if scores_dir is not None else "unfiltered"
            # If the vectors variant is named *_unfiltered, force
            # unfiltered mode regardless of whether scores/ exists.
            if vec_dir.name.endswith("_unfiltered"):
                mode = "unfiltered"
            targets.append(ScanTarget(
                entity_type=entity_dir.name,
                vectors_variant=vec_dir.name,
                activations_dir=act_dir,
                vectors_dir=vec_dir,
                scores_dir=scores_dir if mode == "filtered" else None,
                mode=mode,
            ))

    return targets


# ---------------------------------------------------------------------------
# One-target scan
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    target: ScanTarget
    median_activation_size: int
    results: list[dict[str, Any]] = field(default_factory=list)
    output_path: Optional[Path] = None
    rerun_list_path: Optional[Path] = None

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results:
            out[r["status"]] = out.get(r["status"], 0) + 1
        return out

    def suspects(self) -> list[dict[str, Any]]:
        return [r for r in self.results if r["status"] in RERUN_STATUSES]


def scan_one_target(
    target: ScanTarget,
    *,
    min_count: int,
    reduce_questions: int,
    deep_load: bool,
    load_check: bool,
) -> ScanResult:
    """Walk one ScanTarget's activations + vectors, classifying every entity."""
    act_files = sorted(target.activations_dir.glob("*.pt"))
    if not act_files:
        logger.warning(f"[{target.label}] no activation .pt files in "
                       f"{target.activations_dir}; skipping")
        return ScanResult(target=target, median_activation_size=0)

    sizes = [f.stat().st_size for f in act_files]
    median_size = int(statistics.median(sizes))

    print(f"\n[{target.label}] scanning {len(act_files)} activation files "
          f"(median {median_size / 1e6:.1f} MB) "
          f"in {target.vectors_dir}")
    if target.scores_dir is None:
        print(f"  mode: unfiltered (no scores filter)")
    else:
        print(f"  mode: filtered, scores from {target.scores_dir}")

    results: list[dict[str, Any]] = []
    desc = f"audit {target.label}"
    for act_file in tqdm(act_files, desc=desc, leave=False):
        role = act_file.stem
        results.append(classify_entity(
            role=role,
            act_file=act_file,
            median_act_size=median_size,
            vectors_dir=target.vectors_dir,
            scores_dir=target.scores_dir,
            min_count=min_count,
            reduce_questions=reduce_questions,
            mode=target.mode,
            deep_load=deep_load,
            load_check=load_check,
        ))

    # Also flag any vector files that exist with no source activation
    # (genuine orphans -- shouldn't happen, but cheap to check).
    act_role_set = {f.stem for f in act_files}
    for vec_file in sorted(target.vectors_dir.glob("*.pt")):
        if vec_file.stem == "missing_vectors_audit":
            continue
        # Skip symlinks (the default.pt symlink) -- they're shared
        # references, not genuine orphans.
        if vec_file.is_symlink():
            continue
        if vec_file.stem not in act_role_set:
            results.append({
                "role": vec_file.stem,
                "status": "orphan_vector",
                "vector_path": str(vec_file),
                "activation_path": None,
                "vector_size_bytes": vec_file.stat().st_size,
            })

    return ScanResult(target=target, median_activation_size=median_size,
                      results=results)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _write_scan_output(
    sr: ScanResult,
    *,
    min_count: int,
    reduce_questions: int,
    deep_load: bool,
    load_check: bool,
) -> None:
    """Write per-scan JSON report and rerun list next to the vectors dir."""
    output_path = sr.target.vectors_dir / "missing_vectors_audit.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({
        "activations_dir": str(sr.target.activations_dir),
        "vectors_dir": str(sr.target.vectors_dir),
        "scores_dir": str(sr.target.scores_dir) if sr.target.scores_dir else None,
        "entity_type": sr.target.entity_type,
        "vectors_variant": sr.target.vectors_variant,
        "mode": sr.target.mode,
        "min_count": min_count,
        "reduce_questions": reduce_questions,
        "deep_load": deep_load,
        "load_check": load_check,
        "median_activation_size_bytes": sr.median_activation_size,
        "results": sr.results,
    }, indent=2))
    sr.output_path = output_path

    rerun_path = sr.target.vectors_dir / "missing_vectors_rerun.txt"
    suspects = sr.suspects()
    rerun_path.write_text(
        "\n".join(r["role"] for r in suspects) + ("\n" if suspects else "")
    )
    sr.rerun_list_path = rerun_path


def _print_scan_summary(sr: ScanResult) -> None:
    """Print a per-scan summary table + suspect list to stdout."""
    counts = sr.counts()
    print(f"\n  === {sr.target.label} summary ===")
    for status in ALL_STATUSES:
        if status in counts:
            print(f"    {status:34s}  {counts[status]:5d}")
    print(f"    {'TOTAL':34s}  {len(sr.results):5d}")
    if sr.output_path:
        print(f"    report: {sr.output_path}")
    if sr.rerun_list_path:
        print(f"    rerun:  {sr.rerun_list_path}")

    suspects = sr.suspects()
    if suspects:
        print(f"  {len(suspects)} suspect(s):")
        for r in suspects[:30]:
            extra = r.get("note") or r.get("score3_in_scores") or ""
            print(f"    [{r['status']:34s}] {r['role']}  {extra}")
        if len(suspects) > 30:
            print(f"    ... and {len(suspects) - 30} more "
                  f"(see {sr.output_path})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Audit vectors/* dirs vs activations/+ scores/, "
                    "classifying every missing or corrupt vector.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See module docstring for the full status taxonomy.",
    )
    # Two ways to specify what to scan.  Comprehensive (--root) auto-
    # discovers entity-type subdirs and every sibling vectors* variant;
    # explicit single-pair (--activations_dir + --vectors_dir) is the
    # back-compat invocation.
    parser.add_argument("--root", type=Path, default=None,
                        help="Output root containing entity-type subdirs "
                             "(default/, roles/, traits/, combinations/, ...). "
                             "Auto-discovers every {entity}/vectors* sibling "
                             "with real (non-symlinked) .pt files.")
    parser.add_argument("--activations_dir", type=Path, default=None)
    parser.add_argument("--vectors_dir", type=Path, default=None)
    parser.add_argument("--scores_dir", type=Path, default=None,
                        help="Required for --mode filtered (default).  "
                             "Drop for --mode unfiltered (or for vectors_unfiltered/ dirs).")
    parser.add_argument("--mode", choices=("filtered", "unfiltered"),
                        default="filtered",
                        help="filtered = step 4's default behaviour "
                             "(score=3 mean for non-default roles, mean for "
                             "default roles).  unfiltered = treat every "
                             "entity as a 'default' role (mean of all acts). "
                             "In --root mode, auto-detected per vectors dir "
                             "(unfiltered if name ends with _unfiltered or "
                             "no sibling scores/ subdir).")
    parser.add_argument("--min_count", type=int, default=50,
                        help="Minimum score=3 sample count required by step 4.")
    parser.add_argument("--reduce_questions", type=int, default=1,
                        help="Match the value passed to step 4.")
    parser.add_argument("--deep_load", action="store_true",
                        help="For *missing* vectors, load every suspect "
                             "activation .pt to confirm the score=3 / "
                             "NaN classification.  Slow but definitive.  "
                             "Without this, anything that passes the cheap "
                             "shallow checks is reported as 'mysterious'.")
    parser.add_argument("--no_load_check", action="store_true",
                        help="Skip the per-vector torch.load check.  By "
                             "default every existing vector .pt is loaded "
                             "(with a short 1-retry schedule) to detect the "
                             "corrupt-on-write failure mode (full size, "
                             "torch.load raises).  Disabling makes the scan "
                             "much faster but won't catch corrupt vectors.")
    parser.add_argument("--rerun_list", type=Path, default=None,
                        help="Single-pair mode only: write the rerun list "
                             "here.  In --root mode, rerun lists are written "
                             "next to each vectors dir as missing_vectors_rerun.txt.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Single-pair mode only: write the JSON report "
                             "here.  In --root mode, JSON reports are written "
                             "next to each vectors dir as missing_vectors_audit.json.")
    args = parser.parse_args()

    # Validate input combinations.
    using_root = args.root is not None
    using_explicit = args.activations_dir is not None or args.vectors_dir is not None
    if using_root and using_explicit:
        parser.error("--root and --activations_dir/--vectors_dir are mutually exclusive")
    if not using_root and not using_explicit:
        parser.error("must specify either --root or both --activations_dir and --vectors_dir")
    if not using_root:
        if args.activations_dir is None or args.vectors_dir is None:
            parser.error("single-pair mode requires both --activations_dir and --vectors_dir")
        if args.mode == "filtered" and args.scores_dir is None:
            parser.error("--scores_dir is required for --mode filtered")

    load_check = not args.no_load_check

    # Build the list of scan targets.
    targets: list[ScanTarget]
    if using_root:
        targets = discover_scan_targets(args.root)
        if not targets:
            print(f"ERROR: no scan targets found under {args.root}", file=sys.stderr)
            print("       (looking for entity-type subdirs containing both an "
                  "activations/ subdir and at least one non-empty vectors* "
                  "subdir)", file=sys.stderr)
            sys.exit(1)
        print(f"Found {len(targets)} scan target(s) under {args.root}:")
        for t in targets:
            sf = "" if t.scores_dir is None else f"  scores={t.scores_dir.name}"
            print(f"  {t.label:40s}  mode={t.mode}{sf}")
    else:
        targets = [ScanTarget(
            entity_type=args.activations_dir.parent.name or "explicit",
            vectors_variant=args.vectors_dir.name or "vectors",
            activations_dir=args.activations_dir,
            vectors_dir=args.vectors_dir,
            scores_dir=args.scores_dir,
            mode=args.mode,
        )]

    # Run all scans.
    scan_results: list[ScanResult] = []
    for target in targets:
        sr = scan_one_target(
            target,
            min_count=args.min_count,
            reduce_questions=args.reduce_questions,
            deep_load=args.deep_load,
            load_check=load_check,
        )
        scan_results.append(sr)

    # Write outputs.
    if using_root:
        # One report + rerun list per scan, alongside the vectors dir.
        for sr in scan_results:
            _write_scan_output(
                sr, min_count=args.min_count,
                reduce_questions=args.reduce_questions,
                deep_load=args.deep_load, load_check=load_check,
            )
    else:
        sr = scan_results[0]
        if args.output is None:
            args.output = sr.target.vectors_dir / "missing_vectors_audit.json"
        sr.output_path = args.output
        sr.output_path.parent.mkdir(parents=True, exist_ok=True)
        sr.output_path.write_text(json.dumps({
            "activations_dir": str(sr.target.activations_dir),
            "vectors_dir": str(sr.target.vectors_dir),
            "scores_dir": str(sr.target.scores_dir) if sr.target.scores_dir else None,
            "min_count": args.min_count,
            "reduce_questions": args.reduce_questions,
            "mode": sr.target.mode,
            "deep_load": args.deep_load,
            "load_check": load_check,
            "median_activation_size_bytes": sr.median_activation_size,
            "results": sr.results,
        }, indent=2))
        if args.rerun_list is not None:
            sr.rerun_list_path = args.rerun_list
            sr.rerun_list_path.parent.mkdir(parents=True, exist_ok=True)
            suspects = sr.suspects()
            sr.rerun_list_path.write_text(
                "\n".join(r["role"] for r in suspects)
                + ("\n" if suspects else "")
            )

    # Print summaries.
    for sr in scan_results:
        _print_scan_summary(sr)

    # Aggregate header (if multiple).
    if len(scan_results) > 1:
        total_counts: dict[str, int] = {}
        total_results = 0
        for sr in scan_results:
            for status, n in sr.counts().items():
                total_counts[status] = total_counts.get(status, 0) + n
            total_results += len(sr.results)
        print(f"\n=== Aggregate across {len(scan_results)} scan(s) ===")
        for status in ALL_STATUSES:
            if status in total_counts:
                print(f"  {status:34s}  {total_counts[status]:5d}")
        print(f"  {'TOTAL':34s}  {total_results:5d}")

        n_suspects = sum(len(sr.suspects()) for sr in scan_results)
        if n_suspects:
            print(f"\n  Total re-run candidates: {n_suspects}")
            print("  See per-scan missing_vectors_rerun.txt files for the "
                  "lists.")


if __name__ == "__main__":
    main()
