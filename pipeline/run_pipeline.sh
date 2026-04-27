#!/bin/bash
#
# Pipeline for computing the Assistant Axis.
#
# Supports two modes:
#   roger (default) — combined role+trait instructions, standalone traits/roles, default
#     --types combinations roles traits  (any subset; default: all three)
#       Each type gets its own subdirectory under OUTPUT_DIR.
#       "default" is generated once and symlinked into each type's dirs.
#     Two extra subset types restrict combinations to one half of the grid:
#       r_combinations  (goal role x non-goal trait, file prefix "r_")
#       t_combinations  (non-goal role x goal trait, file prefix "t_")
#     Both write into the SAME $OUTPUT_DIR/combinations/ tree as the full
#     "combinations" type, so downstream tooling sees a single combinations
#     directory regardless of which subset was generated.  Mixing
#     "combinations" with either subset is redundant (the subset is implied).
#   christina — standalone roles/traits from --roles_dir.
#     --types is ignored in christina mode.
#
# Usage:
#   ./pipeline/run_pipeline.sh
#   ./pipeline/run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/roles
#   ./pipeline/run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/traits \
#       --roles_dir ../data/traits/instructions
#   ./pipeline/run_pipeline.sh --types combinations roles
#   ./pipeline/run_pipeline.sh --types r_combinations          # only r_ combos
#   ./pipeline/run_pipeline.sh --types r_combinations t_combinations roles traits
#   ./pipeline/run_pipeline.sh --skip-gpu-check                # bypass pre-flight
#   (RECOMMEND RUNNING STEPS 1 AND 2 INDIVIDUALLY; 3 CAN RUN IN PARALLEL ONCE 1 IS DONE)
#
# Pre-flight check:
#   Before any GPU work, the script checks every visible GPU and aborts if
#   any has more than ${GPU_BUSY_THRESHOLD_MIB} MiB already in use -- this
#   catches orphaned vLLM workers from previous crashed runs (which would
#   otherwise cause silent partial step-2 output via per-worker OOMs).  Pass
#   --skip-gpu-check to bypass, or --gpu-busy-threshold-mib N to raise the
#   threshold (e.g. for shared boxes with known co-tenants).
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

# Use /dev/shm (tmpfs, RAM-backed) for two purposes:
#   1. As HF_HOME so model weights are loaded from RAM rather than NFS.  Some
#      RunPod network volumes have a flaky NFS layer where concurrent mmap
#      faults from multiple worker processes hang the kernel
#      (folio_wait_bit_common in D-state).  RAM-backed tmpfs sidesteps this.
#   2. As TMPDIR so step 2's per-role staging files (~2.6 GB each) don't blow
#      out a small container /tmp when 4 workers write concurrently.
# Set to false if you don't have /dev/shm, are on a RAM-constrained box, or
# already have an HF_HOME setup you want preserved.
USE_TMPFS=true
TMPFS_HF_HOME=/dev/shm/hf-cache

# GPU pre-flight check: refuse to run if any visible GPU has >GPU_BUSY_THRESHOLD_MIB
# of memory in use, since that strongly suggests an orphaned vLLM worker from a
# previous (crashed) run still holding a CUDA context.  Such orphans cause OOMs
# on individual workers and silent partial outputs (other workers proceed,
# 2_activations.py exits 0 even when some workers died, the pipeline marches on
# to step 3 with an incomplete activations directory).  See the discussion in
# AGENT_NOTES.md / README.md.  Pass --skip-gpu-check to bypass.
GPU_BUSY_THRESHOLD_MIB=2048

# ---- Parse command line ---------------------------------------------------
TYPES=""
SKIP_GPU_CHECK=false
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
        --no-tmpfs)
            USE_TMPFS=false; shift ;;
        --tmpfs-dir)
            TMPFS_HF_HOME="$2"; USE_TMPFS=true; shift 2 ;;
        --skip-gpu-check)
            SKIP_GPU_CHECK=true; shift ;;
        --gpu-busy-threshold-mib)
            GPU_BUSY_THRESHOLD_MIB="$2"; shift 2 ;;
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

# Validate types (roger mode only).  r_combinations / t_combinations are
# subsets that share the combinations/ output directory.
if [ "$MODE" = "roger" ]; then
    for t in $TYPES; do
        case "$t" in
            combinations|r_combinations|t_combinations|roles|traits) ;;
            *) echo "Invalid type: $t (must be one of combinations, r_combinations, t_combinations, roles, traits)" >&2; exit 1 ;;
        esac
    done
fi

# Helper: map a type name (combinations | r_combinations | t_combinations |
# roles | traits) to the on-disk subdirectory under $OUTPUT_DIR.  The two
# combination subsets share the combinations/ tree.
type_subdir() {
    case "$1" in
        r_combinations|t_combinations) echo "combinations" ;;
        *) echo "$1" ;;
    esac
}

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
echo "Tmpfs:  $USE_TMPFS"
if [ "$MODE" = "christina" ]; then
    echo "Roles:  $ROLES_DIR"
else
    echo "Types:  $TYPES"
fi
echo ""

# ---- GPU pre-flight check --------------------------------------------------
# Refuses to run if any visible GPU is already holding more than
# GPU_BUSY_THRESHOLD_MIB of memory.  The most common cause is an orphaned
# vLLM worker from a previous (crashed) run -- the parent died but the worker
# child got adopted by init and kept its CUDA context, so its weights remain
# resident.  When the new run's worker tries to load the model on that same
# GPU, it OOMs partway through; the multi-worker pool joins all children and
# exits 0 even when some died, so the pipeline silently produces a partial
# step-2 output and the failure isn't noticed until step 4 (or later).
#
# This check runs *after* logging is set up so the diagnostic lands in the
# pipeline log, but before any GPU work starts.  Bypass with --skip-gpu-check.
gpu_preflight_check() {
    if [ "$SKIP_GPU_CHECK" = "true" ]; then
        echo "[gpu-check] skipped (--skip-gpu-check)"
        return
    fi
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        echo "[gpu-check] nvidia-smi not found; skipping"
        return
    fi

    # Restrict the check to GPUs the pipeline will actually use.
    local visible_arg=""
    if [ -n "$CUDA_VISIBLE_DEVICES" ]; then
        visible_arg="--id=$CUDA_VISIBLE_DEVICES"
        echo "[gpu-check] checking GPUs $CUDA_VISIBLE_DEVICES (CUDA_VISIBLE_DEVICES) for >${GPU_BUSY_THRESHOLD_MIB} MiB"
    else
        echo "[gpu-check] checking all visible GPUs for >${GPU_BUSY_THRESHOLD_MIB} MiB"
    fi

    # query: index, name, memory used in MiB.  Output is CSV without units/headers.
    local query
    query=$(nvidia-smi $visible_arg \
        --query-gpu=index,name,memory.used \
        --format=csv,noheader,nounits 2>/dev/null) || true
    if [ -z "$query" ]; then
        echo "[gpu-check] nvidia-smi returned no data; skipping"
        return
    fi

    local busy_lines=""
    while IFS=, read -r idx name used; do
        idx=$(echo "$idx" | xargs)       # trim whitespace
        used=$(echo "$used" | xargs)
        if [ -z "$used" ]; then continue; fi
        if [ "$used" -gt "$GPU_BUSY_THRESHOLD_MIB" ]; then
            busy_lines+="  GPU $idx ($name): ${used} MiB used"$'\n'
        fi
    done <<< "$query"

    if [ -n "$busy_lines" ]; then
        echo ""
        echo "[gpu-check] ERROR: one or more GPUs are already busy."
        echo "$busy_lines"
        echo "Holders (from nvidia-smi --query-compute-apps):"
        nvidia-smi $visible_arg \
            --query-compute-apps=gpu_uuid,pid,process_name,used_memory \
            --format=csv 2>/dev/null \
            | sed 's/^/  /' || true
        echo ""
        echo "This usually means a previous pipeline crashed leaving an orphaned"
        echo "vLLM worker holding a CUDA context.  To clean up:"
        echo ""
        echo "  pkill -f 'assistant-axis/.venv/bin/python3'"
        echo "  sleep 3"
        echo "  nvidia-smi   # all GPUs should now show 0 MiB"
        echo ""
        echo "If a PID still appears in nvidia-smi but ps shows no such process,"
        echo "the driver has zombie memory.  Try:"
        echo ""
        echo "  fuser -k /dev/nvidia*"
        echo "  # or as last resort, restart the container"
        echo ""
        echo "If you know the existing GPU usage is fine (e.g. a co-tenant on"
        echo "a shared box), pass --skip-gpu-check to bypass this check, or"
        echo "set CUDA_VISIBLE_DEVICES to limit the pipeline to free GPUs."
        echo "You can also raise the threshold with --gpu-busy-threshold-mib N."
        exit 1
    fi
    echo "[gpu-check] all visible GPUs are clean"
}
gpu_preflight_check
echo ""

# ---- Tmpfs setup -----------------------------------------------------------
# Mirror the HF cache for $MODEL into /dev/shm so all workers load weights
# from RAM-backed tmpfs (avoids flaky NFS mmap behavior) and redirect TMPDIR
# similarly so step 2's ~2.6 GB per-role staging files don't fill a small
# container /tmp.  Idempotent: re-uses an existing tmpfs cache, skips the
# copy if disk space is short, and is fully bypassed by --no-tmpfs.
setup_tmpfs() {
    if [ "$USE_TMPFS" != "true" ]; then
        echo "[tmpfs] disabled (--no-tmpfs); using system HF_HOME=${HF_HOME:-$HOME/.cache/huggingface} and TMPDIR=${TMPDIR:-/tmp}"
        return
    fi
    if [ ! -d /dev/shm ]; then
        echo "[tmpfs] /dev/shm not present; tmpfs setup skipped"
        return
    fi

    # Redirect TMPDIR to tmpfs unless the user explicitly set it to something
    # else.  Step 2 (2_activations.py) honours TMPDIR for its staging files.
    if [ -z "$TMPDIR" ]; then
        export TMPDIR=/dev/shm
        echo "[tmpfs] TMPDIR=$TMPDIR (avoid filling small container /tmp)"
    else
        echo "[tmpfs] TMPDIR=$TMPDIR (preserved from environment)"
    fi

    # Mirror HF cache for the requested $MODEL.  HF caches under
    # <HF_HOME>/hub/models--<owner>--<name>/.  We copy just the requested
    # model's subtree to keep the tmpfs footprint minimal.
    local source_hf="${HF_HOME:-$HOME/.cache/huggingface}"
    local model_subdir="models--${MODEL//\//--}"
    local source_model_dir="$source_hf/hub/$model_subdir"
    local tmpfs_model_dir="$TMPFS_HF_HOME/hub/$model_subdir"

    if [ ! -d "$source_model_dir" ]; then
        echo "[tmpfs] $MODEL not found at $source_model_dir; HF will download to $source_hf on first use (no tmpfs cache pre-populated)"
        return
    fi

    if [ -d "$tmpfs_model_dir" ]; then
        echo "[tmpfs] $MODEL already present at $tmpfs_model_dir; reusing"
        export HF_HOME="$TMPFS_HF_HOME"
        echo "[tmpfs] HF_HOME=$HF_HOME"
        return
    fi

    # Disk-space check: require 2× model size headroom in /dev/shm.
    local needed_kb
    needed_kb=$(du -sk "$source_model_dir" 2>/dev/null | awk '{print $1 * 2}')
    local avail_kb
    avail_kb=$(df --output=avail /dev/shm 2>/dev/null | tail -1 | tr -d ' ')
    if [ -z "$needed_kb" ] || [ -z "$avail_kb" ] || [ "$avail_kb" -lt "$needed_kb" ]; then
        echo "[tmpfs] insufficient /dev/shm space (need ${needed_kb}kB, have ${avail_kb}kB); skipping tmpfs cache"
        return
    fi

    echo "[tmpfs] copying $MODEL ($((needed_kb / 2 / 1024)) MB) from $source_model_dir to $tmpfs_model_dir ..."
    mkdir -p "$TMPFS_HF_HOME/hub"
    if cp -r "$source_model_dir" "$TMPFS_HF_HOME/hub/"; then
        export HF_HOME="$TMPFS_HF_HOME"
        echo "[tmpfs] copy complete; HF_HOME=$HF_HOME"
    else
        echo "[tmpfs] copy failed; falling back to $source_hf"
    fi
}

setup_tmpfs
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
        type_dir_name=$(type_subdir "$type")
        TYPE_DIR="$OUTPUT_DIR/$type_dir_name"
        # symlink_default reads the local variable $type, but uses it only as
        # the destination prefix; for the combo subsets we want the symlink
        # placed under combinations/ so override $type for the helper call.
        type_for_symlink="$type"; type="$type_dir_name"
        symlink_default responses jsonl
        type="$type_for_symlink"

        case "$type" in
            combinations|r_combinations|t_combinations)
                # Subset flag (empty for full combinations; --combos_only_r /
                # --combos_only_t for the half-grid subsets).  Skip already-
                # generated halves are a no-op thanks to per-file skip logic.
                subset_flag=""
                case "$type" in
                    r_combinations) subset_flag="--combos_only_r" ;;
                    t_combinations) subset_flag="--combos_only_t" ;;
                esac
                uv run 1_generate.py \
                    --mode roger \
                    --model "$MODEL" \
                    --goal_count "$GOAL_COUNT" \
                    --non_goal_count "$NON_GOAL_COUNT" \
                    --reduce_questions "$REDUCE_QUESTIONS" \
                    --no_traits $subset_flag \
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

    # Step 2 honours the r_/t_ subset distinction so disk-limited runs can
    # extract only one half of the combination grid at a time (each .pt is
    # ~2.6 GB; 1800 combos = ~4.7 TB).  We iterate $TYPES rather than the
    # deduped list, passing --name_prefix r_ / t_ to filter response files;
    # per-file skip-if-exists handles any redundant listings.
    #
    # Steps 3-5 only need the deduped list (their work is per-response or
    # per-vector and inexpensive enough to do all at once).
    DEDUP_TYPES=""
    for type in $TYPES; do
        d=$(type_subdir "$type")
        case " $DEDUP_TYPES " in
            *" $d "*) ;;
            *) DEDUP_TYPES="$DEDUP_TYPES $d" ;;
        esac
    done
    DEDUP_TYPES="${DEDUP_TYPES# }"

    # -- Step 2: Extract activations -----------------------------------------
    echo "=== Step 2: Extracting activations ==="
    for type in $TYPES; do
        echo "--- Step 2 [$type] ---"
        type_dir_name=$(type_subdir "$type")
        TYPE_DIR="$OUTPUT_DIR/$type_dir_name"
        type_for_symlink="$type"; type="$type_dir_name"
        symlink_default activations pt
        type="$type_for_symlink"

        prefix_flag=""
        case "$type" in
            r_combinations) prefix_flag="--name_prefix r_" ;;
            t_combinations) prefix_flag="--name_prefix t_" ;;
        esac

        uv run 2_activations.py \
            --model "$MODEL" \
            --responses_dir "$TYPE_DIR/responses" \
            --output_dir "$TYPE_DIR/activations" \
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
            --batch_size 8 $prefix_flag
    done
    echo ""

    # -- Step 3: Score responses ----------------------------------------------
    echo "=== Step 3: Scoring responses ==="
    for type in $DEDUP_TYPES; do
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
    for type in $DEDUP_TYPES; do
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
    for type in $DEDUP_TYPES; do
        echo "--- Step 5 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"

        uv run 5_axis.py \
            --vectors_dir "$TYPE_DIR/vectors" \
            --output "$TYPE_DIR/axis.pt"
    done
    echo ""

    echo "=== Pipeline complete ==="
    for type in $DEDUP_TYPES; do
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
