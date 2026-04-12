#!/bin/bash
#
# Pipeline for computing the Assistant Axis.
#
# Supports two modes:
#   roger (default) — combined role+trait instructions, standalone traits/roles, default
#     --types combinations roles traits  (any subset; default: all three)
#       Each type gets its own subdirectory under OUTPUT_DIR.
#       "default" is generated once and symlinked into each type's dirs.
#   christina — standalone roles (rerun with ROLES_DIR for traits)
#     --types is ignored in christina mode.
#
# Usage:
#   ./pipeline/run_pipeline.sh
#   ./pipeline/run_pipeline.sh --types combinations roles
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
REDUCE_QUESTIONS=3              # roger mode: take every Nth question (1=all, 3=every 3rd)
MIN_COUNT=30                    # roger mode: min score=3 samples for vector (50 for christina)
OUTPUT_DIR="/workspace/qwen-3-32b/roger"

# ---- Parse --types from command line --------------------------------------
TYPES=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --types)
            shift
            while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do
                TYPES="$TYPES $1"
                shift
            done
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done
TYPES="${TYPES# }"  # trim leading space
if [ -z "$TYPES" ]; then
    TYPES="combinations roles traits"
fi

# Validate types
for t in $TYPES; do
    case "$t" in
        combinations|roles|traits) ;;
        *) echo "Invalid type: $t (must be combinations, roles, or traits)" >&2; exit 1 ;;
    esac
done

# ---- Logging --------------------------------------------------------------
LOG_FILE="$OUTPUT_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$OUTPUT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Assistant Axis Pipeline ==="
echo "Log: $LOG_FILE"
echo "Model:  $MODEL"
echo "Mode:   $MODE"
echo "Output: $OUTPUT_DIR"
if [ "$MODE" = "roger" ]; then
    echo "Types:  $TYPES"
fi
echo ""

# ---- Helper: symlink default files into a type's subdir -------------------
# Usage: symlink_default <subdir_name> <file_extension>
# e.g.  symlink_default responses jsonl
symlink_default() {
    local subdir="$1" ext="$2"
    local src="$OUTPUT_DIR/default/$subdir/default.$ext"
    local dst_dir="$OUTPUT_DIR/$type/$subdir"
    local rel="../../default/$subdir/default.$ext"
    mkdir -p "$dst_dir"
    if [ -f "$src" ] && [ ! -e "$dst_dir/default.$ext" ]; then
        ln -s "$rel" "$dst_dir/default.$ext"
        echo "  Symlinked default.$ext -> $type/$subdir/"
    fi
}

# ---- Christina mode (unchanged) -------------------------------------------
if [ "$MODE" = "christina" ]; then

    echo "=== Step 1: Generating responses ==="
    uv run 1_generate.py \
        --mode "$MODE" \
        --model "$MODEL" \
        --output_dir "$OUTPUT_DIR/responses"

    echo ""
    echo "=== Step 2: Extracting activations ==="
    uv run 2_activations.py \
        --model "$MODEL" \
        --responses_dir "$OUTPUT_DIR/responses" \
        --output_dir "$OUTPUT_DIR/activations" \
        --batch_size 8

    echo ""
    echo "=== Step 3: Scoring responses ==="
    uv run 3_judge.py \
        --responses_dir "$OUTPUT_DIR/responses" \
        --output_dir "$OUTPUT_DIR/scores"

    echo ""
    echo "=== Step 4: Computing vectors ==="
    uv run 4_vectors.py \
        --activations_dir "$OUTPUT_DIR/activations" \
        --scores_dir "$OUTPUT_DIR/scores" \
        --output_dir "$OUTPUT_DIR/vectors"

    echo ""
    echo "=== Step 5: Computing axis ==="
    uv run 5_axis.py \
        --vectors_dir "$OUTPUT_DIR/vectors" \
        --output "$OUTPUT_DIR/axis.pt"

    echo ""
    echo "=== Pipeline complete ==="
    echo "Axis saved to: $OUTPUT_DIR/axis.pt"

# ---- Roger mode (types-aware) ---------------------------------------------
else

    # -- Step 0: Generate, extract, and vectorize default (once) ---------------
    echo "=== Step 0: Default role ==="
    DEFAULT_DIR="$OUTPUT_DIR/default"
    DEFAULT_RESP="$DEFAULT_DIR/responses"
    DEFAULT_ACT="$DEFAULT_DIR/activations"
    DEFAULT_VEC="$DEFAULT_DIR/vectors"
    mkdir -p "$DEFAULT_RESP" "$DEFAULT_ACT" "$DEFAULT_DIR/scores" "$DEFAULT_VEC"

    if [ ! -f "$DEFAULT_RESP/default.jsonl" ]; then
        echo "  Generating default responses..."
        uv run 1_generate.py \
            --mode roger \
            --model "$MODEL" \
            --roles_only \
            --roles default \
            --reduce_questions "$REDUCE_QUESTIONS" \
            --output_dir "$DEFAULT_RESP"
    else
        echo "  default.jsonl already exists, skipping generation."
    fi

    if [ ! -f "$DEFAULT_ACT/default.pt" ]; then
        echo "  Extracting default activations..."
        uv run 2_activations.py \
            --model "$MODEL" \
            --responses_dir "$DEFAULT_RESP" \
            --output_dir "$DEFAULT_ACT" \
            --batch_size 8
    else
        echo "  default.pt already exists, skipping extraction."
    fi

    if [ ! -f "$DEFAULT_VEC/default.pt" ]; then
        echo "  Computing default vector..."
        uv run 4_vectors.py \
            --activations_dir "$DEFAULT_ACT" \
            --scores_dir "$DEFAULT_DIR/scores" \
            --output_dir "$DEFAULT_VEC"
    else
        echo "  default vector already exists, skipping."
    fi
    echo ""

    # -- Step 1: Generate responses ------------------------------------------
    echo "=== Step 1: Generating responses ==="
    for type in $TYPES; do
        echo "--- Step 1 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"
        symlink_default responses jsonl

        case "$type" in
            combinations)
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --goal_count "$GOAL_COUNT" \
                    --non_goal_count "$NON_GOAL_COUNT" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --no_traits \
                    --output_dir "$TYPE_DIR/responses"
                ;;
            roles)
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --roles_only \
                    --output_dir "$TYPE_DIR/responses"
                ;;
            traits)
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --traits_only \
                    --output_dir "$TYPE_DIR/responses"
                ;;
        esac
    done
    echo ""

    # -- Step 2: Extract activations -----------------------------------------
    echo "=== Step 2: Extracting activations ==="
    for type in $TYPES; do
        echo "--- Step 2 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"
        symlink_default activations pt

        uv run 2_activations.py \
            --model "$MODEL" \
            --responses_dir "$TYPE_DIR/responses" \
            --output_dir "$TYPE_DIR/activations" \
            --batch_size 8
    done
    echo ""

    # -- Step 3: Score responses ----------------------------------------------
    echo "=== Step 3: Scoring responses ==="
    for type in $TYPES; do
        echo "--- Step 3 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"

        uv run 3_judge.py \
            --responses_dir "$TYPE_DIR/responses" \
            --output_dir "$TYPE_DIR/scores"
    done
    echo ""

    # -- Step 4: Compute vectors ----------------------------------------------
    echo "=== Step 4: Computing vectors ==="
    for type in $TYPES; do
        echo "--- Step 4 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"
        symlink_default vectors pt

        uv run 4_vectors.py \
            --activations_dir "$TYPE_DIR/activations" \
            --scores_dir "$TYPE_DIR/scores" \
            --output_dir "$TYPE_DIR/vectors" \
            --min_count "$MIN_COUNT"
    done
    echo ""

    # -- Step 5: Compute axis -------------------------------------------------
    echo "=== Step 5: Computing axis ==="
    for type in $TYPES; do
        echo "--- Step 5 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"

        uv run 5_axis.py \
            --vectors_dir "$TYPE_DIR/vectors" \
            --output "$TYPE_DIR/axis.pt"
    done
    echo ""

    echo "=== Pipeline complete ==="
    for type in $TYPES; do
        echo "  $type axis: $OUTPUT_DIR/$type/axis.pt"
    done

fi

echo "Log:  $LOG_FILE"

# ---- Summary of warnings/errors ------------------------------------------
ISSUES=$(grep -E ' - (WARNING|ERROR) - ' "$LOG_FILE" 2>/dev/null || true)
if [ -n "$ISSUES" ]; then
    COUNT=$(echo "$ISSUES" | wc -l | tr -d ' ')
    echo ""
    echo "*** $COUNT warning(s)/error(s) during pipeline run: ***"
    echo "$ISSUES"
fi
