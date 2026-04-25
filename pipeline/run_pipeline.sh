#!/bin/bash
#
# Pipeline for computing the Assistant Axis.
#
# Supports two modes:
#   roger (default) — combined role+trait instructions, standalone traits/roles, default
#     --types combinations roles traits  (any subset; default: all three)
#       Each type gets its own subdirectory under OUTPUT_DIR.
#       "default" is generated once and symlinked into each type's dirs.
#   christina — standalone roles/traits from --roles_dir.
#     --types is ignored in christina mode.
#
# Usage:
#   ./pipeline/run_pipeline.sh
#   ./pipeline/run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/roles
#   ./pipeline/run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/traits \
#       --roles_dir ../data/traits/instructions
#   ./pipeline/run_pipeline.sh --types combinations roles
#   (RECOMMEND RUNNING STEPS 1 AND 2 INDIVIDUALLY; 3 CAN RUN IN PARALLEL ONCE 1 IS DONE)
#
# Requirements:
#   - OPENAI_API_KEY environment variable (for step 3)
#   - Sufficient GPU memory for the model

set -e

# ---- Configuration (defaults) ---------------------------------------------
MODEL="Qwen/Qwen3-32B"
MODE="roger"                    # roger | christina
ROLES_DIR="../data/roles/instructions"  # christina: directory of instruction JSONs
GOAL_COUNT=30                   # roger mode: top-N from goal lists
NON_GOAL_COUNT=30               # roger mode: top-N from non-goal lists
REDUCE_QUESTIONS=3              # roger mode: take every Nth question (1=all, 3=every 3rd)
MIN_COUNT=30                    # roger mode: min score=3 samples for vector (50 for christina)
OUTPUT_DIR="/workspace/outputs/qwen-3-32b"
# Tensor-parallel size per worker for steps 1 & 2.  The pipeline runs
# total_gpus / tensor_parallel_size workers in parallel.  Default 1 fits a
# 32B bf16 model on one 80 GB GPU and gives near-linear scaling on 4-GPU
# boxes.  Set to 2 for 40-48 GB GPUs that need two-way model splitting.
TENSOR_PARALLEL_SIZE=1

# ---- Parse command line ---------------------------------------------------
TYPES=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mode)
            MODE="$2"; shift 2 ;;
        --output_dir)
            OUTPUT_DIR="$2"; shift 2 ;;
        --roles_dir)
            ROLES_DIR="$2"; shift 2 ;;
        --model)
            MODEL="$2"; shift 2 ;;
        --tensor_parallel_size)
            TENSOR_PARALLEL_SIZE="$2"; shift 2 ;;
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

# Validate mode
case "$MODE" in
    roger|christina) ;;
    *) echo "Invalid mode: $MODE (must be roger or christina)" >&2; exit 1 ;;
esac

# Validate types (roger mode only)
if [ "$MODE" = "roger" ]; then
    for t in $TYPES; do
        case "$t" in
            combinations|roles|traits) ;;
            *) echo "Invalid type: $t (must be combinations, roles, or traits)" >&2; exit 1 ;;
        esac
    done
fi

# ---- Logging --------------------------------------------------------------
LOG_FILE="$OUTPUT_DIR/pipeline_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$OUTPUT_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=== Assistant Axis Pipeline ==="
echo "Log: $LOG_FILE"
echo "Model:  $MODEL"
echo "Mode:   $MODE"
echo "Output: $OUTPUT_DIR"
echo "TP size:$TENSOR_PARALLEL_SIZE"
if [ "$MODE" = "christina" ]; then
    echo "Roles:  $ROLES_DIR"
else
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
        --roles_dir "$ROLES_DIR" \
        --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
        --output_dir "$OUTPUT_DIR/responses"

    echo ""
    echo "=== Step 2: Extracting activations ==="
    uv run 2_activations.py \
        --model "$MODEL" \
        --responses_dir "$OUTPUT_DIR/responses" \
        --output_dir "$OUTPUT_DIR/activations" \
        --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
        --batch_size 8

    echo ""
    # Infer entity_type for step 3 from ROLES_DIR so the 9 collision names
    # (ascetic, contrarian, ... stoic) are scored against the right prompt.
    # Christina mode is standalone-only (no combinations).
    case "$ROLES_DIR" in
        *traits*) CHR_ENT_TYPE=trait ;;
        *roles*)  CHR_ENT_TYPE=role ;;
        *) echo "ERROR: cannot infer --entity_type from ROLES_DIR=$ROLES_DIR"; exit 1 ;;
    esac

    echo "=== Step 3: Scoring responses ==="
    uv run 3_judge.py \
        --entity_type "$CHR_ENT_TYPE" \
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
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
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
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
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
                    --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
                    --output_dir "$TYPE_DIR/responses"
                ;;
            roles)
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --roles_only \
                    --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
                    --output_dir "$TYPE_DIR/responses"
                ;;
            traits)
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --traits_only \
                    --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
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
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
            --batch_size 8
    done
    echo ""

    # -- Step 3: Score responses ----------------------------------------------
    echo "=== Step 3: Scoring responses ==="
    for type in $TYPES; do
        echo "--- Step 3 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"

        # entity_type disambiguates 9 names that exist in both data/roles and
        # data/traits, and tells the judge when to use the combined-eval prompt.
        case "$type" in
            roles)        ENT_TYPE=role ;;
            traits)       ENT_TYPE=trait ;;
            combinations) ENT_TYPE=combination ;;
        esac

        uv run 3_judge.py \
            --entity_type "$ENT_TYPE" \
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
