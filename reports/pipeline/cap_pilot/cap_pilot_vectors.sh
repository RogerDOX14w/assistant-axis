#!/usr/bin/env bash
# Cap pilot, step 4 on the pod (plan § 4; 2026-10-29): for each tree, once the Mac has copied its 64
# score files, the score-3 vectors (vectors/, --min_count 30, the driver's roger-mode value) and the
# all-response vectors (vectors_all/, --all_responses, the selection-only measure), the two side by
# side so that the second read of each 2.6-GB activation file can come from the page cache, every
# tree at once.  THREADS (default 5) torch threads per process: the pod's container has 54.4 CPUs
# (cpu.max) while torch starts 128 threads by default, and two step-4 processes at the default ran
# at 138 s an entity, each burning about 20 cores spinning (2026-10-29); ten at 5 fill the quota.
# Resumable: step 4 skips vectors that exist.  Run detached on the pod:
#   setsid nohup /workspace/cap_pilot_vectors.sh > /workspace/cap_pilot/vectors.log 2>&1 < /dev/null &
set -uo pipefail
source /workspace/pod_env.sh
cd /workspace/assistant-axis/pipeline
ROOT=/workspace/cap_pilot
THREADS=${THREADS:-5}
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }

tree() {
    local t=$1 OUT=$ROOT/$1
    until [ "$(ls "$OUT"/scores/*.json 2>/dev/null | wc -l)" -ge 64 ]; do sleep 300; done
    sleep 60   # scp writes in place: let the copy that brought the 64th file finish
    stamp "step 4: $t"
    uv run 4_vectors.py --activations_dir "$OUT/activations" --scores_dir "$OUT/scores" \
        --output_dir "$OUT/vectors" --min_count 30 >> "$OUT/vectors.log" 2>&1 &
    local p1=$!
    uv run 4_vectors.py --activations_dir "$OUT/activations" --all_responses \
        --output_dir "$OUT/vectors_all" --min_count 30 >> "$OUT/vectors_all.log" 2>&1 &
    local p2=$!
    wait $p1; local s1=$?
    wait $p2; local s2=$?
    [ $s1 -eq 0 ] && [ $s2 -eq 0 ] || { stamp "$t: step 4 FAILED (score-3 $s1, all $s2)"; return 1; }
    stamp "$t: $(ls "$OUT"/vectors/*.pt | wc -l) score-3 vectors, $(ls "$OUT"/vectors_all/*.pt | wc -l) all-response vectors"
}

stamp "threads per process: $THREADS"
pids=()
for t in ${TREES:-cap256 cap512 cap512b cap768 cap1024}; do
    tree "$t" & pids+=($!)
done
fail=0
for p in "${pids[@]}"; do wait "$p" || fail=1; done
[ $fail -eq 0 ] && stamp "step 4 done" || stamp "step 4 FAILED for at least one tree"
