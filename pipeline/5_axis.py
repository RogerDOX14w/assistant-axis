#!/usr/bin/env python3
"""
Compute the assistant axis from per-role vectors.

Formula: axis = mean(default_vectors) - nanmean(pos_3_vectors across roles)

The ``*.pt`` files in ``--vectors_dir`` whose stem has a response file in
``--responses_dir`` (default: ``responses/`` beside the vectors directory;
since 2026-10-12, walk-through P2) take part: the file named ``default`` (or
any vector of type "mean") on the default side, every other file on the role
side, each entity weighing the same.  The rest (a renamed entity's old
vector, the scan's ``orphan_vector``) are named in a WARNING and left out;
fewer than ``--min_entities`` (10) non-default vectors is an error.  run_pipeline.sh runs this once per
entity-type directory, so ``roles/axis.pt``, ``traits/axis.pt`` and
``combinations/axis.pt`` (r_ and t_ combinations together) each contrast the
shared default vector (the ``default.pt`` symlink) with that directory's
entities.  The means are taken over whole (n_slots, n_layers, hidden)
tensors, so every slot and layer gets its own axis.

The axis points FROM role-playing TOWARD default assistant behavior.

Usage (from pipeline/):
    uv run 5_axis.py \
        --vectors_dir outputs/gemma-2-27b/vectors \
        --output outputs/gemma-2-27b/axis.pt
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant_axis.atomic_io import (  # noqa: E402
    torch_load_with_retry,
    torch_save_with_retry,
)

logger = logging.getLogger("pipeline.5_axis")

# The fewest non-default vectors an axis is built from (walk-through P2,
# 2026-10-12: a guard against an axis from a nearly empty or wrong
# directory, not a statistical threshold; the October types have 339 to
# 1,800 entities, the May ones 280 to 1,793).
DEFAULT_MIN_ENTITIES = 10


def load_vector(vector_file: Path) -> dict:
    """Load vector data from .pt file with project-standard NFS retry
    (5 attempts, [5, 20, 60, 180] s backoff -- handles transient
    short-reads that surface as ``RuntimeError``).
    """
    return torch_load_with_retry(
        vector_file, map_location="cpu", weights_only=False,
        logger_obj=logger,
    )


class NanMeanAccumulator:
    """Running element-wise nanmean of equally shaped tensors in float64,
    one tensor at a time (no stack of every vector: 1,800 float32
    combination vectors would be about 19 GB)."""

    def __init__(self):
        self.total = None
        self.count = None

    def add(self, t: torch.Tensor) -> None:
        x = t.to(torch.float64)
        if self.total is None:
            self.total = torch.zeros_like(x)
            self.count = torch.zeros(x.shape, dtype=torch.int64)
        finite = ~torch.isnan(x)
        self.total += torch.where(finite, x, torch.zeros((), dtype=torch.float64))
        self.count += finite

    def mean(self) -> torch.Tensor:
        """float64; NaN where every tensor was NaN."""
        return self.total / self.count


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Compute assistant axis from vectors")
    parser.add_argument("--vectors_dir", type=str, required=True, help="Directory with vector .pt files")
    parser.add_argument("--output", type=str, required=True, help="Output axis.pt file path")
    parser.add_argument("--responses_dir", type=str, default=None,
                        help="Only vectors whose stem has <stem>.jsonl here are averaged "
                             "(default: the responses/ directory beside --vectors_dir)")
    parser.add_argument("--min_entities", type=int, default=DEFAULT_MIN_ENTITIES,
                        help="Refuse (exit 1) when fewer non-default vectors than this "
                             f"remain (default {DEFAULT_MIN_ENTITIES})")
    args = parser.parse_args()

    vectors_dir = Path(args.vectors_dir)
    output_path = Path(args.output)
    responses_dir = (Path(args.responses_dir) if args.responses_dir
                     else vectors_dir.parent / "responses")

    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Only the entities of this run (walk-through P2, 2026-10-12): a vector
    # whose stem has no response file beside the tree (a renamed entity's
    # old vector, a stem dropped from the corpus: the scan's orphan_vector)
    # is named and left out.  Until then every *.pt was averaged.
    if not responses_dir.is_dir():
        print(f"Error: no responses directory at {responses_dir}; step 5 averages only the "
              f"entities that have responses there (pass --responses_dir)")
        sys.exit(1)
    response_stems = {p.stem for p in responses_dir.glob("*.jsonl")}
    all_vector_files = sorted(vectors_dir.glob("*.pt"))
    vector_files = [f for f in all_vector_files if f.stem in response_stems]
    excluded = [f.stem for f in all_vector_files if f.stem not in response_stems]
    print(f"Found {len(all_vector_files)} vector files")
    if excluded:
        logger.warning("%d vector(s) have no response file in %s and are left out of the "
                       "axis: %s%s", len(excluded), responses_dir, ", ".join(excluded[:30]),
                       " ..." if len(excluded) > 30 else "")

    # Separate default and role vectors, accumulated one file at a time
    # (float64 sums, float32 axis: walk-through P3, 2026-10-12)
    default_acc = NanMeanAccumulator()
    role_acc = NanMeanAccumulator()
    default_names: list[str] = []
    role_names: list[str] = []
    metadata = {}
    shapes: set[str] = set()
    dtypes: set[str] = set()

    for vec_file in tqdm(vector_files, desc="Loading vectors"):
        data = load_vector(vec_file)
        vector = data["vector"]
        vector_type = data.get("type", "unknown")
        role = data.get("role", vec_file.stem)
        shapes.add(str(tuple(vector.shape)))
        dtypes.add(str(vector.dtype).replace("torch.", ""))
        if len(shapes) > 1:
            print(f"Error: mixed vector shapes: {sorted(shapes)} (at {vec_file.name})")
            sys.exit(1)

        if "metadata" in data:
            file_meta = data["metadata"]
            if not metadata:
                metadata = file_meta
            else:
                if file_meta.get("header_ids") != metadata.get("header_ids"):
                    print(f"Error: metadata mismatch in {vec_file.name}: "
                          f"header_ids {file_meta.get('header_ids')} != {metadata.get('header_ids')}")
                    sys.exit(1)
                if file_meta.get("model_name") != metadata.get("model_name"):
                    print(f"Error: metadata mismatch in {vec_file.name}: "
                          f"model_name {file_meta.get('model_name')!r} != {metadata.get('model_name')!r}")
                    sys.exit(1)

        # Exact name, as in step 3 and step 4 (a substring test would put any
        # entity whose name contains "default" on the default side).
        if role == "default" or vector_type == "mean":
            default_acc.add(vector)
            default_names.append(vec_file.stem)
            print(f"  {role}: default/mean vector")
        else:
            role_acc.add(vector)
            role_names.append(vec_file.stem)

    print(f"\nLoaded {len(default_names)} default vectors, {len(role_names)} role vectors")

    if not default_names:
        print("Error: No default vectors found")
        sys.exit(1)

    if not role_names:
        print("Error: No role vectors found")
        sys.exit(1)

    if len(role_names) < args.min_entities:
        print(f"Error: only {len(role_names)} non-default vector(s) with responses, below "
              f"--min_entities {args.min_entities}; refusing to build an axis from so few")
        sys.exit(1)

    if len(dtypes) > 1:
        # bf16 (May 2026) beside float32 (since 2026-10-12): averaged in
        # float64 all the same, but the tree mixes two extractions.
        logger.warning("the vectors mix dtypes %s; a tree should come from one extraction",
                       sorted(dtypes))

    # Means per element over whole (n_slots, n_layers, hidden) tensors (2D
    # (n_layers, hidden) too), NaN-skipping, in float64; the difference is
    # taken in float64 and stored as float32.  Until 2026-10-12 the stacked
    # bf16 vectors were averaged and subtracted in bf16: 1.3-1.5% median,
    # up to 6.3%, relative error in the axis (review P4's measurement).
    # Points from role-playing toward default.
    axis = (default_acc.mean() - role_acc.mean()).to(torch.float32)

    print(f"\nAxis shape: {axis.shape}")

    # Per-layer norms; use dim=-1 to handle both 2D and 3D
    norms = axis.norm(dim=-1)
    if axis.ndim == 3:
        n_slots = axis.shape[0]
        print(f"Produced {n_slots} axes (slot 0 = body mean, slots 1..{n_slots-1} = header tokens)")
        # Print norms for body-mean axis (slot 0)
        body_norms = norms[0]
        print("Body-mean axis norms per layer (first 10):")
        for i, norm in enumerate(body_norms[:10]):
            print(f"  Layer {i}: {norm:.4f}")
        print("  ...")
        print(f"  Mean norm: {body_norms.mean():.4f}")
        print(f"  Max norm: {body_norms.max():.4f} (layer {body_norms.argmax().item()})")
    else:
        print("Axis norms per layer (first 10):")
        for i, norm in enumerate(norms[:10]):
            print(f"  Layer {i}: {norm:.4f}")
        print("  ...")
        print(f"  Mean norm: {norms.mean():.4f}")
        print(f"  Max norm: {norms.max():.4f} (layer {norms.argmax().item()})")

    # Save axis -- dict format for metadata, backward compat via load_axis().
    # torch_save_with_retry stages to TMPDIR, copies with retry/backoff,
    # atomically renames into place, and verifies post-copy size.  A
    # mid-write crash or silent NFS short-write never leaves a
    # half-written axis.pt at the destination.
    save_data = {
        "axis": axis,
        # What the axis was made of (additive, 2026-10-12; readers look keys
        # up by name).  Without it a vector added or regenerated after the
        # axis went unnoticed: traits/axis.pt in the 8slot tree predates
        # traits/vectors/unhelpful.pt.
        "inputs": {
            "script": "pipeline/5_axis.py",
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "vectors_dir": str(vectors_dir.resolve()),
            "default": default_names,
            "entities": role_names,
            "n_default": len(default_names),
            "n_entities": len(role_names),
            # since the responses filter (P2, 2026-10-12)
            "responses_dir": str(responses_dir.resolve()),
            "excluded_without_responses": excluded,
            "min_entities": args.min_entities,
            # since the float32 change (P3, 2026-10-12)
            "vector_dtypes": sorted(dtypes),
            "axis_dtype": "float32",
            "accumulation": "float64",
        },
    }
    if metadata:
        save_data["metadata"] = metadata
    torch_save_with_retry(save_data, output_path, logger_obj=logger)
    print(f"\nSaved axis to {output_path}")


if __name__ == "__main__":
    main()
