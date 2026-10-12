#!/usr/bin/env python3
"""
Compute per-role vectors from activations and scores.

For regular roles: computes the mean of activations where score=3 (fully playing role)
For default role: computes the mean of ALL activations (no score filtering)

An activation is matched to its score by key, ``{label}_p{prompt_index}_q{question_index}``
(step 2 and step 3 build it the same way).  Activations with no score are not
used: that is how the incongruity filter works, since step 3 scores only the
congruous variants of a combination.

Usage (from pipeline/):
    uv run 4_vectors.py \
        --activations_dir outputs/gemma-2-27b/activations \
        --scores_dir outputs/gemma-2-27b/scores \
        --output_dir outputs/gemma-2-27b/vectors \
        --min_count 50

    # recompute only the entities a scan listed (corrupt or stub vectors are
    # overwritten; entities with no vector are computed anyway):
    uv run 4_vectors.py ... --overwrite vectors/missing_vectors_rerun.txt

Exit status: 0 when every entity was computed, skipped (vector already there,
0-byte placeholder activation) or legitimately filtered (fewer than
--min_count score=3 samples, no scores file); 1 when any entity failed (an
activation or scores file that cannot be read, an empty activation file, a
save that failed) or the activations directory has no .pt files.  The failed
entities have no vector, so a rerun retries exactly them.
"""

import argparse
import hashlib
import json
import logging
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from assistant_axis.atomic_io import (  # noqa: E402
    read_text_with_retry,
    torch_load_with_retry,
    torch_save_with_retry,
)

logger = logging.getLogger("pipeline.4_vectors")


class BelowMinCount(ValueError):
    """Too few usable activations for a vector: a legitimate filter, not a
    failure (a ValueError subclass, as the bare ValueError it replaces)."""


def load_scores(scores_file: Path) -> dict:
    """Load scores from JSON file (with project-standard NFS retry)."""
    text = read_text_with_retry(scores_file, logger_obj=logger)
    return json.loads(text)


def load_activations(activations_file: Path) -> tuple[dict, dict]:
    """Load activations from .pt file, separating metadata.

    Retries on transient I/O errors using the project standard
    (5 attempts, [5, 20, 60, 180] s backoff -- see
    :data:`assistant_axis.atomic_io.DEFAULT_RETRY_DELAYS_S`).
    MooseFS / NFS can return truncated reads under chunkserver load;
    torch.load surfaces these as ``RuntimeError`` ("unexpected EOF,
    expected N more bytes" or "storage has wrong byte size of dtype")
    -- the consolidated retry helper catches both flavours.

    Returns:
        (activations_dict, metadata) where metadata is empty for old-format files.
    """
    data = torch_load_with_retry(
        activations_file, map_location="cpu", weights_only=False,
        logger_obj=logger,
    )
    metadata = data.pop("metadata", {})
    return data, metadata


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

    if len(filtered_acts) < max(min_count, 1):
        raise BelowMinCount(f"Only {len(filtered_acts)} score=3 samples, need {min_count}")

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
    if not all_acts:
        raise BelowMinCount("no activations left after --reduce_questions")
    stacked = torch.stack(all_acts)
    return stacked.nanmean(dim=0)


def is_default_entity(name: str) -> bool:
    """The default baseline, whose vector is the mean of all its activations.

    An exact match, as in step 3 (``stem == "default"``) and every
    downstream reader; the substring test used before 2026-10-12 would
    also have caught any future entity whose name contains "default"
    and averaged it unfiltered."""
    return name == "default"


def read_overwrite_list(path: Path) -> set[str]:
    """Entity names from a rerun list (one per line, as
    ``scan_missing_vectors.py`` writes ``missing_vectors_rerun.txt``);
    blank lines and ``#`` comments are ignored, a trailing ``.pt`` is
    dropped."""
    names = set()
    for line in read_text_with_retry(path, logger_obj=logger).splitlines():
        line = line.split("#", 1)[0].strip()
        if line.endswith(".pt"):
            line = line[:-3]
        if line:
            names.add(line)
    return names


def process_entity(act_file: Path, output_file: Path, scores_dir: Path, *,
                   min_count: int, reduce_questions: int) -> str:
    """Compute and save one entity's vector.  Returns ``"ok"``,
    ``"filtered"`` (fewer than ``min_count`` usable samples, or no scores
    file: a legitimate skip) or ``"failed"`` (an I/O or data error; the
    reason is logged at ERROR)."""
    role = act_file.stem
    if not act_file.exists():
        # Listed a moment ago and gone now (a cleanup running beside step 4,
        # 2026-05-03: thirteen such files cost 265 s of read retries each).
        logger.error("%s: activation file vanished since the directory was listed", role)
        return "failed"

    try:
        activations, act_metadata = load_activations(act_file)
    except (RuntimeError, OSError, EOFError, pickle.UnpicklingError, ValueError) as e:
        # io_retry already logged an ERROR with full retry history.
        logger.error("%s: skipping due to unrecoverable load failure (%s: %s)",
                     role, type(e).__name__, e)
        return "failed"

    if not activations:
        logger.error("%s: activation file loaded but contains no entries; skipping", role)
        return "failed"

    inputs = {
        "script": "pipeline/4_vectors.py",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "activation_file": {"name": act_file.name, "size": act_file.stat().st_size},
        "n_activations": len(activations),
        "min_count": min_count,
        "reduce_questions": reduce_questions,
    }
    try:
        if is_default_entity(role):
            # Default role: use all activations (no score filtering)
            vector = compute_mean_vector(activations, reduce_questions)
            vector_type = "mean"
        else:
            # Regular roles: filter by score=3
            scores_file = scores_dir / f"{role}.json"
            if not scores_file.exists():
                logger.warning("%s: no scores file at %s; skipping", role, scores_file)
                return "filtered"
            try:
                scores_text = read_text_with_retry(scores_file, logger_obj=logger)
                scores = json.loads(scores_text)
            except (OSError, RuntimeError, EOFError, ValueError) as e:
                # ValueError covers JSONDecodeError: a corrupt scores file is
                # an error, not the min_count filter it used to be counted as.
                logger.error("%s: cannot read scores file %s (%s: %s)",
                             role, scores_file, type(e).__name__, e)
                return "failed"
            # What the vector was computed from, so a vector made from a
            # partial scores file (step 3 stopped, a batch not yet collected)
            # can be told from a complete one later.
            inputs["scores_file"] = {
                "name": scores_file.name,
                "size": len(scores_text.encode("utf-8")),
                "sha256": hashlib.sha256(scores_text.encode("utf-8")).hexdigest(),
                "n_scores": len(scores),
            }
            inputs["n_scored_activations"] = sum(1 for k in activations if k in scores)
            vector = compute_pos_3_vector(activations, scores, min_count,
                                          reduce_questions)
            inputs["n_score3_used"] = sum(
                1 for k in activations
                if k in scores and scores[k] == 3 and _keep_by_reduce(k, reduce_questions))
            vector_type = "pos_3"
    except BelowMinCount as e:
        # min_count not met -- legitimate skip, not an error.
        logger.warning("%s: %s", role, e)
        return "filtered"
    except (RuntimeError, ValueError, IndexError) as e:
        # torch.stack over mixed shapes, a malformed activation key, ...
        logger.error("%s: cannot compute the vector (%s: %s)", role, type(e).__name__, e)
        return "failed"

    save_data = {
        "vector": vector,
        "type": vector_type,
        "role": role,
        # Additive (2026-10-12): readers look keys up by name.  Kept out of
        # "metadata", which step 5 copies into the axis from the first file.
        "inputs": inputs,
    }
    if act_metadata:
        save_data["metadata"] = act_metadata

    # Atomic save with project-standard retry: TMPDIR staging + retry/backoff
    # copy to the (possibly NFS) destination, verified, then renamed into
    # place.  A mid-write crash or silent short-write never leaves a
    # half-written .pt at the final path.
    try:
        torch_save_with_retry(save_data, output_file, logger_obj=logger)
    except (RuntimeError, OSError, EOFError, pickle.UnpicklingError, ValueError) as e:
        logger.error("%s: skipping due to unrecoverable save failure (%s)", role, e)
        return "failed"
    return "ok"


def main(argv=None) -> int:
    # Ensure pipeline log messages (including io_retry's WARNING/ERROR
    # output) are visible.  Format mirrors axis_judge_correlation.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(description="Compute per-role vectors")
    parser.add_argument("--activations_dir", type=str, required=True, help="Directory with activation .pt files")
    parser.add_argument("--scores_dir", type=str, required=True, help="Directory with score JSON files")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for vector .pt files")
    parser.add_argument("--min_count", type=int, default=50, help="Minimum score=3 samples required")
    parser.add_argument("--overwrite", nargs="?", const=True, default=False, metavar="RERUN_LIST",
                        help="Overwrite existing output files.  With a file argument (one entity "
                             "name per line, e.g. a scan's missing_vectors_rerun.txt) only those "
                             "entities are overwritten; the rest keep skip-if-exists.")
    parser.add_argument("--reduce_questions", type=int, default=1,
                        help="Take only activations with q_idx %% N == 0 (default 1 = no reduction). "
                             "Compounds with any reduction already done at step 1.")
    args = parser.parse_args(argv)

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    activations_dir = Path(args.activations_dir)
    scores_dir = Path(args.scores_dir)

    # Get all activation files
    activation_files = sorted(activations_dir.glob("*.pt"))
    print(f"Found {len(activation_files)} activation files")
    if not activation_files:
        logger.error("no activation .pt files in %s", activations_dir)
        return 1

    overwrite_names: set[str] | None = None      # None: --overwrite applies to all
    if isinstance(args.overwrite, str):
        overwrite_list = Path(args.overwrite)
        if not overwrite_list.is_file():
            parser.error(f"--overwrite list not found: {overwrite_list}")
        overwrite_names = read_overwrite_list(overwrite_list)
        unknown = sorted(overwrite_names - {f.stem for f in activation_files})
        print(f"--overwrite {overwrite_list}: {len(overwrite_names)} entities")
        if unknown:
            logger.warning("%d entities in %s have no activation file here and cannot be "
                           "recomputed: %s", len(unknown), overwrite_list, ", ".join(unknown[:20]))

    counts = {"ok": 0, "skipped": 0, "placeholder": 0, "filtered": 0, "failed": 0}
    failed_names: list[str] = []

    for act_file in tqdm(activation_files, desc="Computing vectors"):
        role = act_file.stem
        output_file = output_dir / f"{role}.pt"

        overwrite = (bool(args.overwrite) if overwrite_names is None
                     else role in overwrite_names)
        # Skip if exists (unless overwriting it)
        if output_file.exists() and not overwrite:
            counts["skipped"] += 1
            continue

        # A 0-byte activation file is a deliberate placeholder (written to
        # make step 2 skip an entity whose activations were deleted to save
        # disk; scan_missing_vectors.py's "placeholder").  Loading it would
        # only spend 265 s in read retries before failing.
        try:
            if act_file.stat().st_size == 0:
                logger.info("%s: 0-byte placeholder activation file; skipping", role)
                counts["placeholder"] += 1
                continue
        except OSError:
            pass  # process_entity reports it

        status = process_entity(act_file, output_file, scores_dir,
                                min_count=args.min_count,
                                reduce_questions=args.reduce_questions)
        counts[status] += 1
        if status == "failed":
            failed_names.append(role)

    print(f"\nSummary: {counts['ok']} successful, {counts['skipped']} skipped "
          f"(vector exists), {counts['placeholder']} placeholders, "
          f"{counts['filtered']} filtered (below --min_count or no scores file), "
          f"{counts['failed']} failed")
    if failed_names:
        logger.error("%d entities failed and have no vector; fix the cause and rerun "
                     "(existing vectors are skipped): %s",
                     len(failed_names), ", ".join(failed_names[:30]))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
