#!/bin/zsh
# The one sampled combination whose role was renamed in the corpus (aligned_artificial_intelligence ->
# instrumentally_aligned_ai, 2026-09-28, text unchanged): step 3 resolves rubrics by file stem, so the
# combination and the role are judged again under the new name, into their own directories.
cd /Users/roger/Documents/GitHub/assistant-axis || exit 1
R=runpod_workspace/combo_explore
LOG=${0:a:h}/logs
OLD=r_aligned_artificial_intelligence__pensive
NEW=r_instrumentally_aligned_ai__pensive
mkdir -p $R/combo_renamed/responses $R/role_renamed/responses
cp $R/combo/responses/$OLD.jsonl $R/combo_renamed/responses/$NEW.jsonl
cp $R/role/$OLD/responses/aligned_artificial_intelligence.jsonl $R/role_renamed/responses/instrumentally_aligned_ai.jsonl
rt=(--judge_model gpt-5.6-luna --no_batch --service_tier flex --save_replies --no_incongruity_filtering
    --requests_per_second 15 --batch_size 30)
uv run python pipeline/3_judge.py --entity_type combination --responses_dir $R/combo_renamed/responses \
  --output_dir $R/combo_renamed/scores $rt > $LOG/combo_renamed.log 2>&1
echo "combo renamed exit $?" >> $LOG/done.txt
uv run python pipeline/3_judge.py --entity_type role --responses_dir $R/role_renamed/responses \
  --output_dir $R/role_renamed/scores $rt > $LOG/role_renamed.log 2>&1
echo "role renamed exit $?" >> $LOG/done.txt
