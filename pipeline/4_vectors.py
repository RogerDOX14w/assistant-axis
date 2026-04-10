#!/usr/bin/env python3
"""
Compute per-role vectors from activations and scores.

For regular roles: computes the mean of activations where score=3 (fully playing role)
For default role: computes the mean of ALL activations (no score filtering)

Usage:
    uv run scripts/4_vectors.py \
        --activations_dir outputs/gemma-2-27b/activations \
        --scores_dir outputs/gemma-2-27b/scores \
        --output_dir outputs/gemma-2-27b/vectors \
        --min_count 50
"""

import argparse
import json
import sys
from pathlib import Path

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))


def load_scores(scores_file: Path) -> dict:
    """Load scores from JSON file."""
    with open(scores_file, 'r') as f:
        return json.load(f)


def load_activations(activations_file: Path) -> tuple[dict, dict]:
    """Load activations from .pt file, separating metadata.

    Returns:
        (activations_dict, metadata) where metadata is empty for old-format files.
    """
    data = torch.load(activations_file, map_location="cpu", weights_only=False)
    metadata = data.pop("metadata", {})
    return data, metadata


def compute_pos_3_vector(activations: dict, scores: dict, min_count: int) -> torch.Tensor:
    """
    Compute mean vector from activations where score=3.

    Handles both old 2D tensors (n_layers, hidden_dim) and new 3D tensors
    (1+N, n_layers, hidden_dim). Output shape matches input tensor shape.
    """
    filtered_acts = []
    for key, act in activations.items():
        if key in scores and scores[key] == 3:
            filtered_acts.append(act)

    if len(filtered_acts) < min_count:
        raise ValueError(f"Only {len(filtered_acts)} score=3 samples, need {min_count}")

    stacked = torch.stack(filtered_acts)
    return stacked.nanmean(dim=0)


def compute_mean_vector(activations: dict) -> torch.Tensor:
    """
    Compute mean vector from all activations (no filtering).

    Handles both old 2D tensors (n_layers, hidden_dim) and new 3D tensors
    (1+N, n_layers, hidden_dim). Output shape matches input tensor shape.
    """
    all_acts = list(activations.values())
    stacked = torch.stack(all_acts)
    return stacked.nanmean(dim=0)


def main():
    parser = argparse.ArgumentParser(description="Compute per-role vectors")
    parser.add_argument("--activations_dir", type=str, required=True, help="Directory with activation .pt files")
    parser.add_argument("--scores_dir", type=str, required=True, help="Directory with score JSON files")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for vector .pt files")
    parser.add_argument("--min_count", type=int, default=50, help="Minimum score=3 samples required")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    activations_dir = Path(args.activations_dir)
    scores_dir = Path(args.scores_dir)

    # Get all activation files
    activation_files = sorted(activations_dir.glob("*.pt"))
    print(f"Found {len(activation_files)} activation files")

    successful = 0
    skipped = 0
    failed = 0

    for act_file in tqdm(activation_files, desc="Computing vectors"):
        role = act_file.stem
        output_file = output_dir / f"{role}.pt"

        # Skip if exists (unless --overwrite)
        if output_file.exists() and not args.overwrite:
            skipped += 1
            continue

        # Load activations
        activations, act_metadata = load_activations(act_file)

        if not activations:
            print(f"Warning: No activations for {role}")
            failed += 1
            continue

        try:
            if "default" in role:
                # Default roles: use all activations (no score filtering)
                vector = compute_mean_vector(activations)
                vector_type = "mean"
            else:
                # Regular roles: filter by score=3
                scores_file = scores_dir / f"{role}.json"
                if not scores_file.exists():
                    print(f"Warning: No scores file for {role}")
                    failed += 1
                    continue

                scores = load_scores(scores_file)
                vector = compute_pos_3_vector(activations, scores, args.min_count)
                vector_type = "pos_3"

            # Save vector with retry for MFS I/O errors
            save_data = {
                "vector": vector,
                "type": vector_type,
                "role": role,
            }
            if act_metadata:
                save_data["metadata"] = act_metadata

            for attempt in range(3):
                try:
                    torch.save(save_data, output_file)
                    break
                except RuntimeError as e:
                    if output_file.exists():
                        output_file.unlink()
                    if attempt < 2:
                        import time
                        print(f"Warning: {role}: save failed ({e}), retrying in 5s...")
                        time.sleep(5)
                    else:
                        raise
            successful += 1

        except ValueError as e:
            print(f"Warning: {role}: {e}")
            failed += 1

    print(f"\nSummary: {successful} successful, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
