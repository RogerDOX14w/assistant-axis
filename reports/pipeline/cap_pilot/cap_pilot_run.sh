#!/usr/bin/env bash
# Cap pilot runner (reports/pipeline/plan_max_tokens_pilot.md, § 4; 2026-10-28).
#   cap_pilot_run.sh gen  <tree> <cap> [name ...]   step 1 for the pilot entities (or the names given)
#   cap_pilot_run.sh acts <tree> [extra step-2 args]  step 2 on the tree's responses
# <tree> is a directory name under /workspace/cap_pilot (cap256, cap512, cap512b, ...).
# The environment is the driver's (run_pipeline.sh): the model mirrored into /dev/shm,
# step 2's staging in /dev/shm, the compile caches off /dev/shm (mounted noexec).
set -uo pipefail
source /workspace/pod_env.sh
cd /workspace/assistant-axis/pipeline
ROOT=/workspace/cap_pilot
E=../reports/pipeline/cap_pilot_entities.json
MODEL=Qwen/Qwen3-32B
export TMPDIR=/dev/shm
export TRITON_CACHE_DIR=/root/.cache/triton TORCHINDUCTOR_CACHE_DIR=/root/.cache/torchinductor
mkdir -p "$TRITON_CACHE_DIR" "$TORCHINDUCTOR_CACHE_DIR"
if NEW=$(uv run python ../assistant_axis/tmpfs.py mirror --model "$MODEL" \
        --tmpfs-hf-home /dev/shm/hf-cache --source-hf-home "$HF_HOME" --method auto) && [ -n "$NEW" ]; then
    export HF_HOME="$NEW"
fi
echo "[$(date -u +%FT%TZ)] HF_HOME=$HF_HOME TMPDIR=$TMPDIR"

names() {  # names of one type in the pilot list: role | trait | combination
    uv run python -c "import json,sys; print(' '.join(json.load(open('$E'))['by_type'][sys.argv[1]]))" "$1"
}
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }

cmd=$1; tree=$2; shift 2
OUT="$ROOT/$tree"
mkdir -p "$OUT"
case "$cmd" in
  gen)
    cap=$1; shift
    if [ $# -gt 0 ]; then
        # explicit names (the smoke test): split by type through the list
        roles=""; others=""
        for n in "$@"; do
            if [[ " $(names role) " == *" $n "* ]]; then roles="$roles $n"; else others="$others $n"; fi
        done
    else
        roles=$(names role); others="$(names trait) $(names combination)"
    fi
    if [ -n "${roles// /}" ]; then
        stamp "step 1, roles, cap $cap: $roles"
        uv run 1_generate.py --model "$MODEL" --mode roger --roles_only --roles $roles \
            --max_tokens "$cap" --tensor_parallel_size 1 --output_dir "$OUT/responses" || { stamp "step 1 roles FAILED"; exit 1; }
    fi
    if [ -n "${others// /}" ]; then
        stamp "step 1, traits and combinations, cap $cap"
        uv run 1_generate.py --model "$MODEL" --mode roger --non_goal_count 54 --roles $others \
            --max_tokens "$cap" --tensor_parallel_size 1 --output_dir "$OUT/responses" || { stamp "step 1 others FAILED"; exit 1; }
    fi
    stamp "step 1 done: $(ls "$OUT/responses"/*.jsonl | wc -l) response files"
    ;;
  acts)
    stamp "step 2: $OUT"
    uv run 2_activations.py --model "$MODEL" --responses_dir "$OUT/responses" \
        --output_dir "$OUT/activations" --max_length 2048 --batch_size 8 --tensor_parallel_size 1 "$@" \
        || { stamp "step 2 FAILED"; exit 1; }
    stamp "step 2 done: $(ls "$OUT/activations"/*.pt | wc -l) activation files"
    ;;
  *) echo "usage: $0 gen|acts <tree> ..." >&2; exit 2 ;;
esac
