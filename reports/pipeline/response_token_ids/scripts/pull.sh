#!/usr/bin/env bash
# Pull the sample run's outputs (no activations) from the pod into the results
# tree and copy the session's scripts into its logs/, as the smoke run's were.
#   bash pull.sh            (from the repo root)
# rsync -rt, never -a (no owner or permission copying onto the Mac).
set -euo pipefail
SRC=sample-pull:/workspace/sample_ids_out
DST="runpod_workspace/qwen/qwen-3-32b Roger sample-ids"
SCRATCH=/private/tmp/claude-501/-Users-roger-Documents-GitHub-assistant-axis/2435c7bb-8854-4b5f-997a-5ecd5f1a7021/scratchpad/sample_ids
mkdir -p "$DST/logs"
rsync -rt --stats -e "ssh -F .secrets/runpod/ssh_config" \
    --exclude 'act_*' --exclude 'by_type' --exclude 'run.pid' \
    "$SRC/" "$DST/"
cp "$SCRATCH"/{run_sample.sh,compare_activations.py,token_diff.py,vector_compare.py,axis_projection_shift.py,rho_substitution.py,draw_controls.py,watch_run.sh,pull.sh,pod_ports.py,pod_stop.py,finish_chain.sh} \
    "$DST/logs/"
echo "--- pulled into $DST"
du -sh "$DST"/* | sed 's/^/   /'
ls "$DST"/responses/*.jsonl | wc -l | sed 's/^/   responses: /'
for v in text ids turn text_bs1; do
    [ -d "$DST/vec_$v" ] && echo "   vec_$v: $(ls "$DST/vec_$v"/*.pt 2>/dev/null | wc -l) vectors"
done
ls "$DST"/axis_*.pt 2>/dev/null | sed 's/^/   /'
