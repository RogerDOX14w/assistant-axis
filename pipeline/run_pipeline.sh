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
#     A --roles_dir with no default.json (traits) gets the default from
#     $DEFAULT_ROLE_DIR, generated once under default/ and symlinked in.
#
# Usage -- run from the pipeline/ directory: the steps are invoked by relative
# path (uv run 1_generate.py ...), and relative paths such as the default
# --roles_dir ../data/roles/instructions are relative to pipeline/:
#   cd pipeline
#   ./run_pipeline.sh
#   ./run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/roles
#   ./run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/traits \
#       --roles_dir ../data/traits/instructions
#   ./run_pipeline.sh --types combinations roles
#   ./run_pipeline.sh --types r_combinations          # only r_ combos
#   ./run_pipeline.sh --types r_combinations t_combinations roles traits
#   ./run_pipeline.sh --skip-gpu-check                # bypass pre-flight
#   ./run_pipeline.sh --steps23serial                 # disable parallel steps 2+3
#   ./run_pipeline.sh --no-scan                       # skip the scan before step 5
#   ./run_pipeline.sh --types roles --judge-batch-requests 3000   # one of several pods
#   ./run_pipeline.sh --tmpfs-method cp               # model mirror: auto (default),
#                                                     # rsync or cp (assistant_axis/tmpfs.py)
#   ./run_pipeline.sh --types roles --from-step 3 --judge-prompt-version 4
#                                                     # steps 3-5 again under rubric 4
#   ./run_pipeline.sh --types roles --judge-model gpt-5.6-luna --judge-save-replies
#                                                     # the October role judging (version 10)
#
# Rubric versions (--judge-prompt-version N, 2026-10-23): step 3 judges under
# version N of its rubrics (3_judge.py --prompt_version; 0 the original
# number-only rubrics, 3 the rubrics from 2026-10-12, 4 a draft; 5
# version 4 and a clause for helpful professional roles, a draft; 6 the role
# rubric as a decision procedure, 7 version 6 without its reversal rule and 8
# version 7 with its helpful-professional clause given its converse, drafts;
# 9, a rejected draft, is not runnable; 10 version 8's text with a role reply
# scored from its A, B and C answers, settled, the default since 2026-10-28:
# the role rubric for the October extraction, roles judged by gpt-5.6-luna
# only, so a roles run needs --judge-model gpt-5.6-luna; traits and
# combinations as version 3).  A
# version other than the default writes scores_v<N>/, vectors_v<N>/ and
# axis_v<N>.pt beside the default's scores/, vectors/ and axis.pt, so the
# versions can be compared on the same responses and activations; the scan
# checks vectors_v<N>/ against scores_v<N>/.  --from-step 3 (or 4, 5) starts
# there: no GPU check, no model mirror, no steps 0 to 2.  Step 3 refuses a
# scores directory judged under another version.
#
# A failing step stops the pipeline: steps 1 to 3 as before, and step 4 since
# 2026-10-12 (4_vectors.py exits 1 when an activation, scores or vector file
# cannot be read or written), so no axis is computed from a partial set of
# vectors.  A rerun skips everything already done.
#
# Scan before step 5 (default ON): after step 4, runs
# pipeline/scan_missing_vectors.py to audit every (activation, vector) pair
# and flag any corrupt-on-write activations, missing scores, below-min-count
# entities, or unloadable vectors.  Cache-backed so re-scans are cheap.  Re-run
# candidates (scanner exit 3) STOP the pipeline before step 5, so no axis is
# built from a partial set (Roger, 2026-10-12: a stop, not a warning, which is
# easy to miss).  Pass --no-scan to skip (e.g. when you want to inspect
# intermediate state yourself, or when the pipeline is part of a larger
# automated job that runs the scanner separately).
#
# Step 2/3 parallelism (default ON): step 2 (GPU-bound activation extraction)
# and step 3 (judge-API-bound response scoring) share no resources beyond
# step 1's response files, so they run concurrently by default.  Step 2's
# stdout is prefixed with "[step2] " and step 3's with "[step3] " so the
# interleaved output is still readable; if you prefer clean per-step logs
# (e.g. for debugging) pass --steps23serial.  The script waits for both to
# finish (and surfaces failures of either) before moving on to step 4.
#
# Step 3 judges through the OpenAI Batch API by default (since 2026-10-10,
# Roger): half the real-time price, results within 24 hours, usually much
# sooner, and step 2 runs for longer anyway.  Pass --judge-realtime to judge
# in real time (3_judge.py --no_batch).  A batch-mode step 3 that leaves
# requests unanswered exits 1 and stops the pipeline before step 4; run it
# again to submit the rest (it collects batches already submitted).
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

# The steps are run by relative path; fail at once (before the GPU check and a
# possibly long tmpfs copy) when started from anywhere else.
for step_script in 1_generate.py 2_activations.py 3_judge.py 4_vectors.py 5_axis.py; do
    if [ ! -f "$step_script" ]; then
        echo "run_pipeline.sh: $step_script not found in $(pwd)." >&2
        echo "Run it from the pipeline/ directory:  cd pipeline && ./run_pipeline.sh ..." >&2
        exit 1
    fi
done

# ---- Configuration (defaults) ---------------------------------------------
MODEL="Qwen/Qwen3-32B"
MODE="roger"                    # roger | christina
ROLES_DIR="../data/roles/instructions"  # christina: directory of instruction JSONs
# Where the default entity's default.json is read when ROLES_DIR has none
# (a christina run over traits; roger mode's step 0 reads it from here too).
DEFAULT_ROLE_DIR="../data/roles/instructions"
GOAL_COUNT=30                   # roger mode: top-N from goal lists
NON_GOAL_COUNT=30               # roger mode: top-N from non-goal lists
REDUCE_QUESTIONS=3              # roger mode: take every Nth question (1=all, 3=every 3rd)
MIN_COUNT=30                    # roger mode: min score=3 samples for vector
CHRISTINA_MIN_COUNT=50          # christina mode: the same, for step 4 and the scan
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
# How the model mirror is copied: auto (rsync if installed, else cp), rsync,
# or cp.  The copy is done by assistant_axis/tmpfs.py, the same code the
# steering driver uses (one implementation since 2026-10-12, P8.6); both
# methods write the completeness marker .tmpfs_mirror_complete.
TMPFS_METHOD=auto
# Where step 2's atomic-write staging files land.  Default /dev/shm
# (RAM-backed tmpfs).  Override via --tmpdir.  Unconditional override
# of $TMPDIR by design: pod-defaults like /workspace/tmp silently
# route every staging write through slow NFS.  Callers who genuinely
# want to preserve their existing $TMPDIR must pass --tmpdir "$TMPDIR".
TMPFS_TMPDIR=/dev/shm

# GPU pre-flight check: refuse to run if any visible GPU has >GPU_BUSY_THRESHOLD_MIB
# of memory in use, since that strongly suggests an orphaned vLLM worker from a
# previous (crashed) run still holding a CUDA context.  Such orphans cause OOMs
# on individual workers and silent partial outputs (other workers proceed,
# until 2026-10-12 2_activations.py exited 0 even when some workers died and the
# pipeline marched on with an incomplete activations directory; it now exits 1,
# but an orphan still wastes the run).  See the discussion in
# AGENT_NOTES.md / README.md.  Pass --skip-gpu-check to bypass.
GPU_BUSY_THRESHOLD_MIB=2048

# Run Step 2 (GPU-bound activation extraction) and Step 3 (judge-API-bound
# response scoring) concurrently.  They share no resources -- step 2 uses the
# GPU and step 3 talks to OpenAI/Anthropic over the network -- and only depend
# on step 1's responses, which are fully written before step 2 begins.
# Wall-clock savings can be substantial when step 3 is hours of API calls.
# Disable with --steps23serial if you want the historical sequential behaviour
# (cleaner per-step logs; useful for debugging).
STEPS23_PARALLEL=true
JUDGE_ARGS=()                   # --judge-realtime adds --no_batch for step 3

# Step 3's rubric version (3_judge.py --prompt_version; versions in
# assistant_axis/judge_rubrics.py).  Any version other than the default
# writes its own scores_v<N>/, vectors_v<N>/ and axis_v<N>.pt beside the
# default's scores/, vectors/ and axis.pt, so that steps 3 to 5 can be rerun
# under another rubric on the same responses and activations (Roger,
# 2026-10-23; with --from-step 3).  The default is step 3's
# DEFAULT_PROMPT_VERSION (a test pins the two together).
JUDGE_PROMPT_VERSION_DEFAULT=10
JUDGE_PROMPT_VERSION=""
# First step to run: 1 (everything, the default), or 3, 4 or 5 to rerun from
# that step on outputs already there.  From step 3 on no step uses the GPU or
# the model, so the GPU check and the model mirror are skipped too, and the
# default entity's vector must already exist.
FROM_STEP=1

# Run pipeline/scan_missing_vectors.py between step 4 and step 5 to verify
# every activation produced a healthy vector; re-run candidates stop the run.  Cheap when nothing went wrong
# (cache hits dominate -- a re-scan after a clean run is typically a few
# minutes), genuinely useful when something silently failed during step 2 or
# step 4 (corrupt-on-write activation, ZFS/NFS short-read, missing scores
# file, ...).  Disable with --no-scan if you want to inspect intermediate
# state by hand or are on a tight wall-clock budget.
RUN_SCAN=true

# ---- Parse command line ---------------------------------------------------
TYPES=""
SKIP_GPU_CHECK=false
JUDGE_MODEL=""
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
        --tmpfs-method)
            TMPFS_METHOD="$2"; shift 2 ;;
        --tmpdir)
            TMPFS_TMPDIR="$2"; shift 2 ;;
        --skip-gpu-check)
            SKIP_GPU_CHECK=true; shift ;;
        --gpu-busy-threshold-mib)
            GPU_BUSY_THRESHOLD_MIB="$2"; shift 2 ;;
        --steps23serial)
            STEPS23_PARALLEL=false; shift ;;
        --judge-realtime)
            JUDGE_ARGS+=(--no_batch); shift ;;
        --judge-batch-requests)
            # step 3's --batch_requests, sized from the organisation's queue
            # limit when several pods share one API key (pipeline/README.md)
            JUDGE_ARGS+=(--batch_requests "$2"); shift 2 ;;
        --judge-prompt-version)
            JUDGE_PROMPT_VERSION="$2"; shift 2 ;;
        --judge-model)
            # step 3's --judge_model (its default: gpt-4.1-mini); roles under
            # version 10 need gpt-5.6-luna (Roger, 2026-10-28)
            JUDGE_MODEL="$2"; JUDGE_ARGS+=(--judge_model "$2"); shift 2 ;;
        --judge-save-replies)
            # step 3's --save_replies: every reply beside the scores, so that a
            # change of reading needs no rejudging (3_judge.py --reread_replies)
            JUDGE_ARGS+=(--save_replies); shift ;;
        --judge-no-mark-truncated)
            # step 3's --no_mark_truncated: show the judge a response cut at
            # --max_tokens as stored, without the "…" step 3 appends by default
            # (Roger, 2026-10-28; christina mode passes it on its own)
            JUDGE_ARGS+=(--no_mark_truncated); shift ;;
        --from-step)
            FROM_STEP="$2"; shift 2 ;;
        --no-scan)
            RUN_SCAN=false; shift ;;
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
# Step 3 marks a response cut at --max_tokens for the judge by default (Roger,
# 2026-10-28), except in christina mode, which reproduces the paper's method.
if [ "$MODE" = "christina" ] && [[ " ${JUDGE_ARGS[*]-} " != *" --no_mark_truncated "* ]]; then
    JUDGE_ARGS+=(--no_mark_truncated)
fi
case "$TMPFS_METHOD" in
    auto|rsync|cp) ;;
    *) echo "Invalid --tmpfs-method: $TMPFS_METHOD (must be auto, rsync or cp)" >&2; exit 1 ;;
esac
case "$FROM_STEP" in
    1|3|4|5) ;;
    *) echo "Invalid --from-step: $FROM_STEP (must be 1, 3, 4 or 5)" >&2; exit 1 ;;
esac
# Directory names of the scores, vectors and axis for the prompt version.
VERSION_SUFFIX=""
if [ -n "$JUDGE_PROMPT_VERSION" ]; then
    if ! [[ "$JUDGE_PROMPT_VERSION" =~ ^[0-9]+$ ]]; then
        echo "Invalid --judge-prompt-version: $JUDGE_PROMPT_VERSION (a version number)" >&2
        exit 1
    fi
    JUDGE_ARGS+=(--prompt_version "$JUDGE_PROMPT_VERSION")
    if [ "$JUDGE_PROMPT_VERSION" != "$JUDGE_PROMPT_VERSION_DEFAULT" ]; then
        VERSION_SUFFIX="_v$JUDGE_PROMPT_VERSION"
    fi
fi
SCORES_SUB="scores$VERSION_SUFFIX"
VECTORS_SUB="vectors$VERSION_SUFFIX"
AXIS_NAME="axis$VERSION_SUFFIX.pt"

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
echo "Steps 2+3: $([ "$STEPS23_PARALLEL" = "true" ] && echo "parallel (GPU+judge concurrent)" || echo "serial (--steps23serial)")"
echo "Scan:   $([ "$RUN_SCAN" = "true" ] && echo "yes (before step 5; re-run candidates stop the run; --no-scan to skip)" || echo "no (--no-scan)")"
echo "Judge:  ${JUDGE_MODEL:-the default model}, prompt version ${JUDGE_PROMPT_VERSION:-$JUDGE_PROMPT_VERSION_DEFAULT} (into $SCORES_SUB/, $VECTORS_SUB/, $AXIS_NAME)"
if [ "$FROM_STEP" -gt 1 ]; then
    echo "From:   step $FROM_STEP (earlier steps not run)"
fi
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
    if [ "$FROM_STEP" -ge 3 ]; then
        echo "[gpu-check] skipped (--from-step $FROM_STEP: no step uses the GPU)"
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
        echo "vLLM worker holding a CUDA context.  To clean up, kill the PIDs"
        echo "listed above (check with 'ps -fp <pid>' that they are leftovers):"
        echo ""
        echo "  kill <pid> ...   # then, if one survives: kill -9 <pid>"
        echo "  sleep 3"
        echo "  nvidia-smi   # all GPUs should now show 0 MiB"
        echo ""
        echo "(pkill -f 'assistant-axis/.venv/bin/python3' also works, but kills every"
        echo "Python from this checkout, including a step-3 batch run or steering"
        echo "sweep you meant to keep.)"
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
    # (Until 2026-10-12 a missing /dev/shm skipped everything here; now the
    # TMPDIR block below falls back to /tmp on its own, and the mirror is
    # skipped when its mount, the parent of --tmpfs-dir, is missing.)

    # Redirect TMPDIR to $TMPFS_TMPDIR (default /dev/shm) unconditionally.
    # Step 2 (2_activations.py) honours TMPDIR for its staging files; if
    # the pod sets a default like TMPDIR=/workspace/tmp (NFS-backed), every
    # 2.6 GB staging write would route through slow network storage.
    # Unconditional override avoids that silent footgun.  Callers who want
    # to preserve their existing $TMPDIR must pass --tmpdir "$TMPDIR".
    if [ ! -d "$TMPFS_TMPDIR" ]; then
        echo "[tmpfs] WARNING: --tmpdir target '$TMPFS_TMPDIR' not present; falling back to /tmp"
        export TMPDIR=/tmp
    elif [ -n "$TMPDIR" ] && [ "$TMPDIR" != "$TMPFS_TMPDIR" ]; then
        echo "[tmpfs] TMPDIR=$TMPFS_TMPDIR (overriding prior $TMPDIR; pass --tmpdir '$TMPDIR' to preserve)"
        export TMPDIR="$TMPFS_TMPDIR"
    else
        export TMPDIR="$TMPFS_TMPDIR"
        echo "[tmpfs] TMPDIR=$TMPDIR (avoid filling small container /tmp / NFS staging)"
    fi

    # Triton / torchinductor compile CUDA kernels into .so files at runtime
    # then dlopen() them.  RunPod (and most hardened containers) mount /dev/shm
    # noexec, so dlopen on a .so under /dev/shm/torchinductor_root/... fails
    # with "ImportError: ... failed to map segment from shared object".  Route
    # the compile cache to ~/.cache/{triton,torchinductor} (regular FS, exec
    # allowed) unless the user has overridden them.  Bonus: persists across
    # container restarts so the ~50 s torch.compile pass is amortised.
    local cache_root="${XDG_CACHE_HOME:-$HOME/.cache}"
    if [ -z "$TRITON_CACHE_DIR" ]; then
        export TRITON_CACHE_DIR="$cache_root/triton"
        mkdir -p "$TRITON_CACHE_DIR"
        echo "[tmpfs] TRITON_CACHE_DIR=$TRITON_CACHE_DIR (off /dev/shm noexec)"
    fi
    if [ -z "$TORCHINDUCTOR_CACHE_DIR" ]; then
        export TORCHINDUCTOR_CACHE_DIR="$cache_root/torchinductor"
        mkdir -p "$TORCHINDUCTOR_CACHE_DIR"
        echo "[tmpfs] TORCHINDUCTOR_CACHE_DIR=$TORCHINDUCTOR_CACHE_DIR (off /dev/shm noexec)"
    fi

    # Mirror the HF cache for $MODEL (<HF_HOME>/hub/models--<owner>--<name>/,
    # just that model's subtree) with assistant_axis/tmpfs.py, the code the
    # steering driver uses too (P8.6, 2026-10-12; this function had its own
    # cp -r until then).  It reuses a mirror only when its completeness
    # marker is there and the tree has not shrunk, checks for 1.5x the
    # model's size free on the mount, copies with --tmpfs-method (auto: rsync
    # if installed, else a staged cp renamed into place), writes the marker,
    # and prints the new HF_HOME; it exits 1 (and says why on stderr) when
    # the source cache should be used instead.  A mirror made by this
    # function's cp -r before 2026-10-12 has no marker: rsync tops it up;
    # cp refuses to trust or delete it (delete it by hand first).
    local source_hf="${HF_HOME:-$HOME/.cache/huggingface}"
    if [ "$FROM_STEP" -ge 3 ]; then
        echo "[tmpfs] no model mirror (--from-step $FROM_STEP: no step loads the model)"
        return
    fi
    if [ ! -d "$(dirname "$TMPFS_HF_HOME")" ]; then
        echo "[tmpfs] $(dirname "$TMPFS_HF_HOME") not present; no model mirror (HF_HOME=$source_hf)"
        return
    fi
    local new_hf_home
    if new_hf_home=$(uv run python ../assistant_axis/tmpfs.py mirror \
            --model "$MODEL" \
            --tmpfs-hf-home "$TMPFS_HF_HOME" \
            --source-hf-home "$source_hf" \
            --method "$TMPFS_METHOD") && [ -n "$new_hf_home" ]; then
        export HF_HOME="$new_hf_home"
        echo "[tmpfs] HF_HOME=$HF_HOME"
    else
        echo ""
        echo "[tmpfs] ============================================================"
        echo "[tmpfs]  no tmpfs mirror (the reason is above); using HF_HOME=$source_hf"
        echo "[tmpfs]  If that is on NFS or other slow storage, expect step 2 to"
        echo "[tmpfs]  hang for HOURS on cold mmap reads of model weights."
        echo "[tmpfs] ============================================================"
        echo ""
    fi
}

setup_tmpfs
echo ""

# ---- Helper: stop on a failed step 4 or 5 ---------------------------------
# set -e would stop the script too, silently; this says which step failed and
# that a rerun picks up where it stopped.
step_failed() {
    echo ""
    echo "=== Pipeline aborted: $1 failed ($2) ==="
    echo "Fix the cause and run the same command again: finished outputs are skipped."
    echo "Log: $LOG_FILE"
    exit 1
}

# ---- Helper: the scan between step 4 and step 5 ---------------------------
# Walks every activation/vector pair under $OUTPUT_DIR and classifies any
# misses or corruptions (corrupt-on-write activation .pt, missing scores,
# below-min-count, etc).  The scanner caches its torch.load outcomes at
# $OUTPUT_DIR/scan_cache.json so this is a fast no-op on the second run
# (cache hits skip the expensive deep_load).  Output:
#   - $OUTPUT_DIR/<type>/vectors/missing_vectors_audit.json (per-target)
#   - $OUTPUT_DIR/<type>/vectors/missing_vectors_rerun.txt (re-run candidates)
# Exit 3 means it found re-run candidates (or an entity with responses but no
# activation): the pipeline stops before step 5, so that no axis is built
# from a partial set.  Until 2026-10-12 the scan ran after step 5 and exit 3
# was a warning (and until that morning exit 0: 870 candidates on 2026-05-03
# went unremarked).  Any other non-zero exit stops the run too: an unknown
# scan state is not a reason to build the axis.  Skip with --no-scan.
scan_before_axis() {
    [ "$RUN_SCAN" = "true" ] || return 0
    echo ""
    echo "=== Scan before step 5 ==="
    local rc=0
    case "$MODE" in
        roger)
            # --root mode: scanner auto-discovers entity-type subdirs and
            # every vectors* sibling under $OUTPUT_DIR.  Use the same
            # MIN_COUNT the pipeline used so below_min_count classifications
            # match what step 4 would actually skip.
            uv run scan_missing_vectors.py \
                --root        "$OUTPUT_DIR" \
                --min_count   "$MIN_COUNT" \
                --deep_load \
                || rc=$?
            ;;
        christina)
            # Single-pair mode: christina mode writes one entity-type tree
            # directly under $OUTPUT_DIR, no entity-type subdir layer.
            uv run scan_missing_vectors.py \
                --activations_dir "$OUTPUT_DIR/activations" \
                --vectors_dir     "$OUTPUT_DIR/$VECTORS_SUB" \
                --scores_dir      "$OUTPUT_DIR/$SCORES_SUB" \
                --min_count       "$CHRISTINA_MIN_COUNT" \
                --deep_load \
                --rerun_list      "$OUTPUT_DIR/$VECTORS_SUB/missing_vectors_rerun.txt" \
                || rc=$?
            ;;
    esac
    if [ "$rc" -eq 3 ]; then
        echo "[scan] the scan found re-run candidates (exit 3): see the suspect lists above"
        echo "[scan] and each vectors dir's missing_vectors_rerun.txt; recompute with"
        echo "[scan] 4_vectors.py --overwrite <that file>.  Entities reported"
        echo "[scan] missing_activation need step 2 first.  Then run this command again."
        step_failed "Scan" "re-run candidates found; step 5 not run, so no axis is built from a partial set"
    elif [ "$rc" -ne 0 ]; then
        step_failed "Scan" "scanner exited $rc; rerun it by hand for details, or pass --no-scan"
    fi
    echo ""
}

# ---- Helper: symlink default files into a type's subdir -------------------
# Usage: symlink_default <subdir_name> <file_extension> [<destination subdir>]
# e.g.  symlink_default responses jsonl
#       symlink_default vectors pt vectors_v4   (a prompt version's vectors)
symlink_default() {
    local subdir="$1" ext="$2"
    local src="$OUTPUT_DIR/default/$subdir/default.$ext"
    local dst_dir="$OUTPUT_DIR/$type/${3:-$subdir}"
    local rel="../../default/$subdir/default.$ext"
    mkdir -p "$dst_dir"
    if [ -f "$src" ] && [ ! -e "$dst_dir/default.$ext" ]; then
        ln -s "$rel" "$dst_dir/default.$ext"
        echo "  Symlinked default.$ext -> $type/${3:-$subdir}/"
    fi
}

# ---- Helper: step 0, the default entity, generated once under default/ -----
# Usage: run_step0_default <1_generate.py arguments selecting the default>
# Generates, extracts and averages the default entity into
# $OUTPUT_DIR/default/{responses,activations,vectors}; each part is skipped
# when its file exists.  Roger mode then symlinks it into every type's tree,
# christina mode (traits) into its one tree.
run_step0_default() {
    echo "=== Step 0: Default role ==="
    DEFAULT_DIR="$OUTPUT_DIR/default"
    DEFAULT_RESP="$DEFAULT_DIR/responses"
    DEFAULT_ACT="$DEFAULT_DIR/activations"
    DEFAULT_VEC="$DEFAULT_DIR/vectors"
    mkdir -p "$DEFAULT_RESP" "$DEFAULT_ACT" "$DEFAULT_DIR/scores" "$DEFAULT_VEC"

    if [ ! -f "$DEFAULT_RESP/default.jsonl" ]; then
        echo "  Generating default responses..."
        uv run 1_generate.py \
            --model "$MODEL" \
            "$@" \
            --roles default \
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
            --output_dir "$DEFAULT_VEC" \
            || step_failed "Step 0 (default vector)" "4_vectors.py exited non-zero; see its [ERROR] lines above"
    else
        echo "  default vector already exists, skipping."
    fi
    echo ""
}

# ---- Christina mode --------------------------------------------------------
if [ "$MODE" = "christina" ]; then

    # A christina run over traits has no default.json in its --roles_dir, so
    # step 5 had no default vector and always failed (review P4 D6).  Since
    # 2026-10-12 the default comes from the roles directory ($DEFAULT_ROLE_DIR),
    # generated once under default/ with the christina settings (as roger
    # mode's step 0) and symlinked into this tree.  A run over roles
    # generates its default.json with the other roles, as before.
    if [ ! -f "$ROLES_DIR/default.json" ]; then
        if [ ! -f "$DEFAULT_ROLE_DIR/default.json" ]; then
            echo "ERROR: $ROLES_DIR has no default.json and neither has $DEFAULT_ROLE_DIR; step 5 needs a default" >&2
            exit 1
        fi
        if [ "$FROM_STEP" -lt 3 ]; then
            run_step0_default --mode christina --roles_dir "$DEFAULT_ROLE_DIR"
        fi
        # (the last entry: a prompt version's own vectors directory)
        for sub_ext in "responses jsonl" "activations pt" "vectors pt" "vectors pt $VECTORS_SUB"; do
            set -- $sub_ext
            dst_sub="${3:-$1}"
            mkdir -p "$OUTPUT_DIR/$dst_sub"
            if [ -f "$OUTPUT_DIR/default/$1/default.$2" ] && [ ! -e "$OUTPUT_DIR/$dst_sub/default.$2" ]; then
                ln -s "../default/$1/default.$2" "$OUTPUT_DIR/$dst_sub/default.$2"
                echo "  Symlinked default.$2 -> $dst_sub/"
            fi
        done
        echo ""
    fi

    if [ "$FROM_STEP" -lt 3 ]; then
        echo "=== Step 1: Generating responses ==="
        uv run 1_generate.py \
            --mode "$MODE" \
            --model "$MODEL" \
            --roles_dir "$ROLES_DIR" \
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
            --output_dir "$OUTPUT_DIR/responses"

        echo ""
    fi

    # Infer entity_type for step 3 from ROLES_DIR so the 11 collision names
    # (ascetic, contrarian, ... stoic) are scored against the right prompt.
    # Christina mode is standalone-only (no combinations).
    case "$ROLES_DIR" in
        *traits*) CHR_ENT_TYPE=trait ;;
        *roles*)  CHR_ENT_TYPE=role ;;
        *) echo "ERROR: cannot infer --entity_type from ROLES_DIR=$ROLES_DIR"; exit 1 ;;
    esac

    # -- Step 2 + Step 3 (concurrent by default; serial with --steps23serial)
    christina_step2() {
        set -e
        set -o pipefail
        echo "=== Step 2: Extracting activations ==="
        uv run 2_activations.py \
            --model "$MODEL" \
            --responses_dir "$OUTPUT_DIR/responses" \
            --output_dir "$OUTPUT_DIR/activations" \
            --tensor_parallel_size "$TENSOR_PARALLEL_SIZE" \
            --batch_size 8
    }
    christina_step3() {
        set -e
        set -o pipefail
        echo "=== Step 3: Scoring responses ==="
        uv run 3_judge.py \
            --entity_type "$CHR_ENT_TYPE" \
            --responses_dir "$OUTPUT_DIR/responses" \
            --output_dir "$OUTPUT_DIR/$SCORES_SUB" \
            "${JUDGE_ARGS[@]}"
    }

    if [ "$FROM_STEP" -eq 3 ]; then
        christina_step3 || step_failed "Step 3" "3_judge.py exited non-zero (see above)"
    elif [ "$FROM_STEP" -ge 4 ]; then
        :   # steps 2 and 3 not run
    elif [ "$STEPS23_PARALLEL" = "true" ]; then
        echo "Running Step 2 (GPU) and Step 3 (judge API) concurrently."
        echo "Disable with --steps23serial.  stdout is prefixed with [step2]/[step3]."
        echo ""
        # pipefail inside each subshell: without it the subshell's status is
        # sed's (always 0), so a failed step 2 or 3 never reached the waits
        # below and the pipeline went on to step 4 (fixed 2026-10-12).
        ( set -o pipefail; christina_step2 2>&1 | sed -u 's/^/[step2] /' ) &
        PID2=$!
        ( set -o pipefail; christina_step3 2>&1 | sed -u 's/^/[step3] /' ) &
        PID3=$!
        fail=0
        wait $PID2 || { echo "ERROR: Step 2 failed (exit $?)"; fail=1; }
        wait $PID3 || { echo "ERROR: Step 3 failed (exit $?)"; fail=1; }
        if [ "$fail" -ne 0 ]; then
            echo "=== Pipeline aborted: parallel step 2/3 had failures ==="
            exit 1
        fi
    else
        christina_step2
        echo ""
        christina_step3
    fi
    echo ""

    if [ "$FROM_STEP" -le 4 ]; then
        echo "=== Step 4: Computing vectors ==="
        # --min_count passed explicitly (it was the script default, 50, while the
        # scan below was given MIN_COUNT=30, so entities with 30-49 score=3
        # samples were reported as re-run candidates that step 4 would skip
        # again).
        uv run 4_vectors.py \
            --activations_dir "$OUTPUT_DIR/activations" \
            --scores_dir "$OUTPUT_DIR/$SCORES_SUB" \
            --output_dir "$OUTPUT_DIR/$VECTORS_SUB" \
            --min_count "$CHRISTINA_MIN_COUNT" \
            || step_failed "Step 4" "4_vectors.py exited non-zero; see its [ERROR] lines above"
    fi

    scan_before_axis

    echo ""
    echo "=== Step 5: Computing axis ==="
    uv run 5_axis.py \
        --vectors_dir "$OUTPUT_DIR/$VECTORS_SUB" \
        --output "$OUTPUT_DIR/$AXIS_NAME" \
        || step_failed "Step 5" "5_axis.py exited non-zero (see above)"

    echo ""
    echo "=== Pipeline complete ==="
    echo "Axis saved to: $OUTPUT_DIR/$AXIS_NAME"

# ---- Roger mode (types-aware) ---------------------------------------------
else

    if [ "$FROM_STEP" -lt 3 ]; then
        # -- Step 0: Generate, extract, and vectorize default (once) ---------------
        run_step0_default --mode roger --roles_only --roles_dir "$DEFAULT_ROLE_DIR" \
            --reduce_questions "$REDUCE_QUESTIONS"

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
    elif [ ! -f "$OUTPUT_DIR/default/vectors/default.pt" ]; then
        # --from-step 3 or later: step 0 is not run, and step 5 needs its vector
        echo "ERROR: --from-step $FROM_STEP needs the default vector, $OUTPUT_DIR/default/vectors/default.pt" >&2
        exit 1
    fi

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

    # -- Step 2 + Step 3 (concurrent by default; serial with --steps23serial) ----
    # Step 2 is GPU-bound (model forward pass + hidden-state hooks); step 3 is
    # judge-API-bound (network calls).  They share no resources beyond step 1's
    # response files (which are fully written by now), so we can run them in
    # parallel for substantial wall-clock savings.  Each runs in its own
    # subshell with stdout/stderr prefixed for readability.

    run_step2_loop() {
        set -e
        set -o pipefail
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
    }

    run_step3_loop() {
        set -e
        set -o pipefail
        echo "=== Step 3: Scoring responses ==="
        for type in $DEDUP_TYPES; do
            echo "--- Step 3 [$type] ---"
            TYPE_DIR="$OUTPUT_DIR/$type"

            # entity_type disambiguates 11 names that exist in both data/roles and
            # data/traits, and tells the judge when to use the combined-eval prompt.
            case "$type" in
                roles)        ENT_TYPE=role ;;
                traits)       ENT_TYPE=trait ;;
                combinations) ENT_TYPE=combination ;;
            esac

            uv run 3_judge.py \
                --entity_type "$ENT_TYPE" \
                --responses_dir "$TYPE_DIR/responses" \
                --output_dir "$TYPE_DIR/$SCORES_SUB" \
                "${JUDGE_ARGS[@]}"
        done
    }

    if [ "$FROM_STEP" -eq 3 ]; then
        run_step3_loop || step_failed "Step 3" "3_judge.py exited non-zero (see above)"
    elif [ "$FROM_STEP" -ge 4 ]; then
        :   # steps 2 and 3 not run
    elif [ "$STEPS23_PARALLEL" = "true" ]; then
        echo "Running Step 2 (GPU) and Step 3 (judge API) concurrently."
        echo "Disable with --steps23serial.  stdout is prefixed with [step2]/[step3]."
        echo ""
        # pipefail inside each subshell, or the status is sed's (see above)
        ( set -o pipefail; run_step2_loop 2>&1 | sed -u 's/^/[step2] /' ) &
        PID2=$!
        ( set -o pipefail; run_step3_loop 2>&1 | sed -u 's/^/[step3] /' ) &
        PID3=$!
        fail=0
        wait $PID2 || { echo "ERROR: Step 2 failed (exit $?)"; fail=1; }
        wait $PID3 || { echo "ERROR: Step 3 failed (exit $?)"; fail=1; }
        if [ "$fail" -ne 0 ]; then
            echo "=== Pipeline aborted: parallel step 2/3 had failures ==="
            exit 1
        fi
    else
        run_step2_loop
        echo ""
        run_step3_loop
    fi
    echo ""

    # -- Step 4: Compute vectors ----------------------------------------------
    if [ "$FROM_STEP" -le 4 ]; then
        echo "=== Step 4: Computing vectors ==="
        for type in $DEDUP_TYPES; do
            echo "--- Step 4 [$type] ---"
            TYPE_DIR="$OUTPUT_DIR/$type"
            symlink_default vectors pt "$VECTORS_SUB"

            uv run 4_vectors.py \
                --activations_dir "$TYPE_DIR/activations" \
                --scores_dir "$TYPE_DIR/$SCORES_SUB" \
                --output_dir "$TYPE_DIR/$VECTORS_SUB" \
                --min_count "$MIN_COUNT" \
                || step_failed "Step 4 [$type]" "4_vectors.py exited non-zero; see its [ERROR] lines above"
        done
        echo ""
    fi

    scan_before_axis

    # -- Step 5: Compute axis -------------------------------------------------
    echo "=== Step 5: Computing axis ==="
    for type in $DEDUP_TYPES; do
        echo "--- Step 5 [$type] ---"
        TYPE_DIR="$OUTPUT_DIR/$type"

        uv run 5_axis.py \
            --vectors_dir "$TYPE_DIR/$VECTORS_SUB" \
            --output "$TYPE_DIR/$AXIS_NAME" \
            || step_failed "Step 5 [$type]" "5_axis.py exited non-zero (see above)"
    done
    echo ""

    echo "=== Pipeline complete ==="
    for type in $DEDUP_TYPES; do
        echo "  $type axis: $OUTPUT_DIR/$type/$AXIS_NAME"
    done

fi

echo "Log:  $LOG_FILE"

# ---- Summary of warnings/errors ------------------------------------------
# Two log formats: steps 1-3 write "<time> - WARNING - ...", steps 4 and 5 and
# the scan "<time> [WARNING] <logger>: ...".  Only the first was matched
# before 2026-10-12, so step 4's load failures never reached this summary.
ISSUE_PATTERN=' - (WARNING|ERROR) - |\[(WARNING|ERROR)\] '
ISSUES=$(grep -E "$ISSUE_PATTERN" "$LOG_FILE" 2>/dev/null || true)
if [ -n "$ISSUES" ]; then
    COUNT=$(echo "$ISSUES" | wc -l | tr -d ' ')
    echo ""
    echo "*** $COUNT warning(s)/error(s) during pipeline run: ***"
    echo "$ISSUES"
fi
