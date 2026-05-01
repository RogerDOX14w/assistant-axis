#!/usr/bin/env python3
"""Audit a vectors/ directory against its source activations/ and
scores/ directories, classifying why each missing vector is missing.

Motivation
----------
On RunPod / NFS we have observed two distinct failure modes for step 4
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

The script also flags **truncated activation files** (anything whose
on-disk size is dramatically smaller than the median size of its
peers) as a separate category, since those are the upstream bug that
caused the original ``r_guardian__casual.pt`` corruption.

Usage
-----
::

    uv run pipeline/scan_missing_vectors.py \\
        --activations_dir outputs/qwen3-32b/activations \\
        --vectors_dir     outputs/qwen3-32b/vectors \\
        --scores_dir      outputs/qwen3-32b/scores \\
        --min_count       50

To audit unfiltered (mean-of-all-activations) vectors, drop
``--scores_dir`` and use ``--mode unfiltered``.

Outputs a per-entity JSON report (``--output``) and prints a
summary table to stdout.  Entities classified as ``mysterious`` or
``truncated_activation`` are the ones worth re-running.
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import sys
from pathlib import Path
from typing import Any

import torch
from tqdm import tqdm

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
) -> dict[str, Any]:
    """Classify a single entity.

    Returns a dict with at minimum::

        {
            "role": role,
            "status": one of (
                "ok",                      # vector present and healthy
                "ok_zero_size",            # vector exists but is suspiciously tiny
                "missing_activation",      # no .pt in activations_dir
                "truncated_activation",    # activation .pt is way smaller than peers
                "missing_scores",          # filtered mode, no scores .json
                "below_min_count",         # filtered mode, < min_count score=3
                "all_nan_or_empty",        # nothing useful in the activation tensor
                "mysterious",              # everything upstream looks fine
            ),
            ... category-specific extras (sizes, counts, reasons) ...
        }
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
        out["status"] = "truncated_activation"
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
    # filter to confirm whether step 4 *should* have produced a vector.
    try:
        data = torch_load_with_retry(
            act_file, map_location="cpu", weights_only=False,
            logger_obj=logger,
        )
    except (RuntimeError, OSError, EOFError) as e:
        out["status"] = "truncated_activation"
        out["note"] = f"activation .pt unloadable: {e}"
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


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Audit vectors/ vs activations/ + scores/, "
                    "classifying every missing vector.")
    parser.add_argument("--activations_dir", type=Path, required=True)
    parser.add_argument("--vectors_dir", type=Path, required=True)
    parser.add_argument("--scores_dir", type=Path, default=None,
                        help="Required for --mode filtered (default).  "
                             "Drop for --mode unfiltered.")
    parser.add_argument("--min_count", type=int, default=50,
                        help="Minimum score=3 sample count required by step 4.")
    parser.add_argument("--reduce_questions", type=int, default=1,
                        help="Match the value passed to step 4 (compounds "
                             "with any reduction at step 1).")
    parser.add_argument("--mode", choices=("filtered", "unfiltered"),
                        default="filtered",
                        help="filtered = step 4's default behaviour "
                             "(score=3 mean for non-default roles, mean for "
                             "default roles).  unfiltered = treat every "
                             "entity as a 'default' role (mean of all acts).")
    parser.add_argument("--deep_load", action="store_true",
                        help="Load every suspect activation .pt to confirm "
                             "the score=3 / NaN classification.  Slow "
                             "(several minutes for hundreds of files) but "
                             "definitive.  Without this, anything that "
                             "passes the cheap shallow checks is reported "
                             "as 'mysterious'.")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write the full per-entity JSON report here. "
                             "Defaults to <vectors_dir>/missing_vectors_audit.json")
    parser.add_argument("--rerun_list", type=Path, default=None,
                        help="Write a newline-separated list of the role "
                             "names that should be re-run (mysterious + "
                             "truncated_activation + ok_zero_size).")
    args = parser.parse_args()

    if args.mode == "filtered" and args.scores_dir is None:
        parser.error("--scores_dir is required for --mode filtered")

    if args.output is None:
        args.output = args.vectors_dir / "missing_vectors_audit.json"

    activations_dir = args.activations_dir
    vectors_dir = args.vectors_dir
    scores_dir = args.scores_dir

    act_files = sorted(activations_dir.glob("*.pt"))
    if not act_files:
        print(f"ERROR: no .pt files in {activations_dir}", file=sys.stderr)
        sys.exit(1)

    sizes = [f.stat().st_size for f in act_files]
    median_size = int(statistics.median(sizes))
    print(f"Scanning {len(act_files)} activation files "
          f"(median size {median_size / 1e6:.1f} MB)...")

    results: list[dict[str, Any]] = []
    for act_file in tqdm(act_files, desc="Auditing"):
        role = act_file.stem
        results.append(classify_entity(
            role=role,
            act_file=act_file,
            median_act_size=median_size,
            vectors_dir=vectors_dir,
            scores_dir=scores_dir,
            min_count=args.min_count,
            reduce_questions=args.reduce_questions,
            mode=args.mode,
            deep_load=args.deep_load,
        ))

    # Also flag any vector files that exist with no source activation
    # (genuine orphans -- shouldn't happen, but cheap to check).
    act_role_set = {f.stem for f in act_files}
    vec_files = sorted(vectors_dir.glob("*.pt"))
    for vec_file in vec_files:
        if vec_file.stem == "missing_vectors_audit":
            continue
        if vec_file.stem not in act_role_set:
            results.append({
                "role": vec_file.stem,
                "status": "orphan_vector",
                "vector_path": str(vec_file),
                "activation_path": None,
                "vector_size_bytes": vec_file.stat().st_size,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "activations_dir": str(activations_dir),
        "vectors_dir": str(vectors_dir),
        "scores_dir": str(scores_dir) if scores_dir else None,
        "min_count": args.min_count,
        "reduce_questions": args.reduce_questions,
        "mode": args.mode,
        "deep_load": args.deep_load,
        "median_activation_size_bytes": median_size,
        "results": results,
    }, indent=2))

    # Summary table.
    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("\n=== Summary ===")
    for status in (
        "ok", "ok_zero_size",
        "missing_activation", "truncated_activation",
        "missing_scores", "below_min_count", "all_nan_or_empty",
        "mysterious", "orphan_vector",
    ):
        if status in counts:
            print(f"  {status:25s}  {counts[status]:5d}")
    print(f"  {'TOTAL':25s}  {len(results):5d}")
    print(f"\nFull report: {args.output}")

    suspects = [
        r for r in results
        if r["status"] in ("mysterious", "truncated_activation", "ok_zero_size")
    ]
    if suspects:
        print(f"\n{len(suspects)} suspects (re-run candidates):")
        for r in suspects[:30]:
            extra = r.get("note") or r.get("score3_in_scores") or ""
            print(f"  [{r['status']:22s}] {r['role']}  {extra}")
        if len(suspects) > 30:
            print(f"  ... and {len(suspects) - 30} more (see {args.output})")

    if args.rerun_list is not None:
        args.rerun_list.parent.mkdir(parents=True, exist_ok=True)
        args.rerun_list.write_text(
            "\n".join(r["role"] for r in suspects) + ("\n" if suspects else "")
        )
        print(f"Rerun list: {args.rerun_list}")


if __name__ == "__main__":
    main()
