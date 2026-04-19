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

    Retries on transient I/O errors (MooseFS can return truncated reads
    under chunkserver load; torch.load surfaces these as RuntimeError with
    "unexpected EOF, expected N more bytes").

    Returns:
        (activations_dict, metadata) where metadata is empty for old-format files.
    """
    import time
    last_err = None
    for attempt in range(3):
        try:
            data = torch.load(activations_file, map_location="cpu", weights_only=False)
            metadata = data.pop("metadata", {})
            return data, metadata
        except (RuntimeError, OSError) as e:
            last_err = e
            if attempt < 2:
                print(f"Warning: load failed for {activations_file.name} "
                      f"({e}), retrying in 5s...")
                time.sleep(5)
    raise last_err


def _question_index(key: str) -> int:
    """Extract q_idx from an activation key like 'pos_p3_q7'.

    NOTE: this is the 0-based index into the already-reduced question list
    from step 1, not into the original questions file. See the TODO in
    assistant_axis/generation.py load_questions for why.
    """
    return int(key.rsplit("_q", 1)[1])


def _keep_by_reduce(key: str, reduce_questions: int) -> bool:
    """Return True if this activation's question index survives an Nth-only reduction."""
    if reduce_questions <= 1:
        return True
    return _question_index(key) % reduce_questions == 0


def compute_pos_3_vector(activations: dict, scores: dict, min_count: int,
                         reduce_questions: int = 1) -> torch.Tensor:
    """
    Compute mean vector from activations where score=3.

    Handles both old 2D tensors (n_layers, hidden_dim) and new 3D tensors
    (1+N, n_layers, hidden_dim). Output shape matches input tensor shape.

    With reduce_questions=N (default 1 = no further reduction), takes only
    activations whose question index satisfies q_idx % N == 0.  This is
    applied on top of any reduction already done at step 1, so the effective
    reduction compounds (reduce=3 at step 1 + reduce=3 here = 9x overall).

    NOTE: Each entity is filtered independently — the set of score=3 questions
    for trait A may differ substantially from trait B.  When computing trait
    *directions* (A_vec - B_vec) for antonym pairs, this means the two means
    are averaged over different question distributions, so the difference
    captures question-mix effects on top of the actual trait contrast.

    A cleaner approach for paired directions would be question-matched
    filtering: intersect the score=3 sets for both sides, recompute means
    over only the shared questions, then difference.  This would require a
    step 4b that loads both activation files for a pair, intersects their
    score=3 keys, and saves a matched direction vector.  The activation files
    are too large for ad-hoc analysis scripts to reopen, so this must be
    precomputed in the pipeline.
    """
    filtered_acts = []
    for key, act in activations.items():
        if key in scores and scores[key] == 3 and _keep_by_reduce(key, reduce_questions):
            filtered_acts.append(act)

    if len(filtered_acts) < min_count:
        raise ValueError(f"Only {len(filtered_acts)} score=3 samples, need {min_count}")

    stacked = torch.stack(filtered_acts)
    return stacked.nanmean(dim=0)


def compute_mean_vector(activations: dict, reduce_questions: int = 1) -> torch.Tensor:
    """
    Compute mean vector from all activations (no score filtering).

    With reduce_questions=N, takes only activations whose question index
    satisfies q_idx % N == 0. See compute_pos_3_vector for caveats.

    Handles both old 2D tensors (n_layers, hidden_dim) and new 3D tensors
    (1+N, n_layers, hidden_dim). Output shape matches input tensor shape.
    """
    all_acts = [act for key, act in activations.items()
                if _keep_by_reduce(key, reduce_questions)]
    stacked = torch.stack(all_acts)
    return stacked.nanmean(dim=0)


def main():
    parser = argparse.ArgumentParser(description="Compute per-role vectors")
    parser.add_argument("--activations_dir", type=str, required=True, help="Directory with activation .pt files")
    parser.add_argument("--scores_dir", type=str, required=True, help="Directory with score JSON files")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for vector .pt files")
    parser.add_argument("--min_count", type=int, default=50, help="Minimum score=3 samples required")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output files")
    parser.add_argument("--reduce_questions", type=int, default=1,
                        help="Take only activations with q_idx %% N == 0 (default 1 = no reduction). "
                             "Compounds with any reduction already done at step 1.")
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

        try:
            activations, act_metadata = load_activations(act_file)
        except (RuntimeError, OSError) as e:
            print(f"Warning: {role}: load failed after retries ({e}), skipping")
            failed += 1
            continue

        if not activations:
            print(f"Warning: No activations for {role}")
            failed += 1
            continue

        try:
            if "default" in role:
                # Default roles: use all activations (no score filtering)
                vector = compute_mean_vector(activations, args.reduce_questions)
                vector_type = "mean"
            else:
                # Regular roles: filter by score=3
                scores_file = scores_dir / f"{role}.json"
                if not scores_file.exists():
                    print(f"Warning: No scores file for {role}")
                    failed += 1
                    continue

                scores = load_scores(scores_file)
                vector = compute_pos_3_vector(activations, scores, args.min_count,
                                              args.reduce_questions)
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
        except (RuntimeError, OSError) as e:
            print(f"Warning: {role}: save failed after retries ({e}), skipping")
            failed += 1

    print(f"\nSummary: {successful} successful, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
