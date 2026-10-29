#!/usr/bin/env bash
# Cap pilot, step 4 on the pod (plan § 4; 2026-10-29): for each tree, wait until the Mac has copied
# its 64 score files, then the score-3 vectors (vectors/, --min_count 30, the driver's roger-mode
# value) and the all-response vectors (vectors_all/, --all_responses, the selection-only measure),
# the two side by side so that the second read of each 2.6-GB activation file comes from the page
# cache.  Resumable: step 4 skips vectors that exist.  Run detached on the pod:
#   setsid nohup /workspace/cap_pilot_vectors.sh > /workspace/cap_pilot/vectors.log 2>&1 < /dev/null &
set -uo pipefail
source /workspace/pod_env.sh
cd /workspace/assistant-axis/pipeline
ROOT=/workspace/cap_pilot
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }

for t in ${TREES:-cap256 cap512 cap512b cap768 cap1024}; do
    OUT=$ROOT/$t
    until [ "$(ls "$OUT"/scores/*.json 2>/dev/null | wc -l)" -ge 64 ]; do sleep 300; done
    sleep 60   # scp writes in place: let the copy that brought the 64th file finish
    stamp "step 4: $t"
    uv run 4_vectors.py --activations_dir "$OUT/activations" --scores_dir "$OUT/scores" \
        --output_dir "$OUT/vectors" --min_count 30 > "$OUT/vectors.log" 2>&1 &
    p1=$!
    uv run 4_vectors.py --activations_dir "$OUT/activations" --all_responses \
        --output_dir "$OUT/vectors_all" --min_count 30 > "$OUT/vectors_all.log" 2>&1 &
    p2=$!
    wait $p1; s1=$?
    wait $p2; s2=$?
    [ $s1 -eq 0 ] && [ $s2 -eq 0 ] || { stamp "$t: step 4 FAILED (score-3 $s1, all $s2)"; exit 1; }
    stamp "$t: $(ls "$OUT"/vectors/*.pt | wc -l) score-3 vectors, $(ls "$OUT"/vectors_all/*.pt | wc -l) all-response vectors"
done
stamp "step 4 done"
