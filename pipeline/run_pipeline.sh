#!/bin/bash
#
# Pipeline for computing the Assistant Axis.
#
# Supports two modes:
#   roger (default) — combined role+trait instructions, standalone traits, default
#   christina       — standalone roles (rerun with ROLES_DIR for traits)
#
# Usage:
#   ./pipeline/run_pipeline.sh
#   (RECOMMEND RUNNING STEPS 1 AND 2 INDIVIDUALLY; 3 CAN RUN IN PARALLEL ONCE 1 IS DONE)
#
# Requirements:
#   - OPENAI_API_KEY environment variable (for step 3)
#   - Sufficient GPU memory for the model

set -e

# ---- Configuration --------------------------------------------------------
MODEL="Qwen/Qwen3-32B"
MODE="roger"                    # roger | christina
GOAL_COUNT=30                   # roger mode: top-N from goal lists
NON_GOAL_COUNT=30               # roger mode: top-N from non-goal lists
REDUCE_QUESTIONS=1              # take every Nth question (1=all, 3=every 3rd)
OUTPUT_DIR="/workspace/qwen-3-32b/roger"

echo "=== Assistant Axis Pipeline ==="
echo "Model:  $MODEL"
echo "Mode:   $MODE"
echo "Output: $OUTPUT_DIR"
echo ""

# ---- Step 1: Generate responses -------------------------------------------
echo "=== Step 1: Generating responses ==="
uv run 1_generate.py \
    --mode "$MODE" \
    --model "$MODEL" \
    --goal_count "$GOAL_COUNT" \
    --non_goal_count "$NON_GOAL_COUNT" \
    --reduce_questions "$REDUCE_QUESTIONS" \
    --output_dir "$OUTPUT_DIR/responses"

# ---- Step 2: Extract activations ------------------------------------------
echo ""
echo "=== Step 2: Extracting activations ==="
uv run 2_activations.py \
    --model "$MODEL" \
    --responses_dir "$OUTPUT_DIR/responses" \
    --output_dir "$OUTPUT_DIR/activations" \
    --batch_size 8

# ---- Step 3: Score responses with judge LLM --------------------------------
echo ""
echo "=== Step 3: Scoring responses ==="
uv run 3_judge.py \
    --responses_dir "$OUTPUT_DIR/responses" \
    --output_dir "$OUTPUT_DIR/scores"

# ---- Step 4: Compute per-entity vectors ------------------------------------
echo ""
echo "=== Step 4: Computing vectors ==="
uv run 4_vectors.py \
    --activations_dir "$OUTPUT_DIR/activations" \
    --scores_dir "$OUTPUT_DIR/scores" \
    --output_dir "$OUTPUT_DIR/vectors"

# ---- Step 5: Compute final axis -------------------------------------------
echo ""
echo "=== Step 5: Computing axis ==="
uv run 5_axis.py \
    --vectors_dir "$OUTPUT_DIR/vectors" \
    --output "$OUTPUT_DIR/axis.pt"

echo ""
echo "=== Pipeline complete ==="
echo "Axis saved to: $OUTPUT_DIR/axis.pt"

# ---- Christina mode notes --------------------------------------------------
# To run Christina mode for roles AND traits, run the pipeline twice:
#
#   MODE="christina"
#   OUTPUT_DIR="/workspace/qwen-3-32b/roles"
#   # ... steps 1-5 ...
#
#   MODE="christina"
#   ROLES_DIR="../data/traits/instructions"  # <-- point at traits
#   OUTPUT_DIR="/workspace/qwen-3-32b/traits"
#   # ... steps 1-5 with --roles_dir "$ROLES_DIR" ...
#
# Separate output dirs avoid name collisions (e.g. "ascetic" is both a role
# and a trait).
