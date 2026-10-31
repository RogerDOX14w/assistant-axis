#!/bin/zsh
# The context-aware combination drafts (prompt versions 16, the role rubric with the trait as context, and 17,
# the trait rubric with the role as context; Roger, 2026-10-30) run on the two judged samples: the May
# exploration sample (runpod_workspace/combo_explore/combo/responses, 27 combinations, and combo_renamed/responses,
# the aligned-AI combination under its new stem), whose responses carry the readers' and Roger's marks
# (../reader_check/), and the October re-check sample (runpod_workspace/combo_recheck/combo/responses).  Each
# version goes into its own scores directory beside the earlier arms (combo_v16, combo_v17, combo_renamed_v16,
# ...), by gpt-5.6-luna on Flex with the standard-tier fallback, replies saved.  Cost: about 6,000 calls, under
# $1; real time, under the $20 line.  Step 3 resumes, so a rerun judges only what is new.
#
#   ./run_judging.sh          # versions 16 and 17
#   ./run_judging.sh 18       # the versions named (18: the trait side in version 11's shape, added later)
#   COMBO_ROOT=runpod_workspace/tcomb_recheck ./run_judging.sh 16 17 18   # that sample's combo directory only
#                             # (the t_ sample; logs go under logs/<root's last part>/)
cd ${0:a:h}/../../../.. || exit 1
LOG=${0:a:h}/logs
versions=(${@:-16 17})
rt=(--judge_model gpt-5.6-luna --no_batch --service_tier flex --save_replies --no_incongruity_filtering
    --requests_per_second 15 --batch_size 30)
pairs=("runpod_workspace/combo_explore combo" "runpod_workspace/combo_explore combo_renamed"
       "runpod_workspace/combo_recheck combo")
if [ -n "$COMBO_ROOT" ]; then
  pairs=("$COMBO_ROOT combo")
  LOG=$LOG/${COMBO_ROOT:t}
fi
mkdir -p $LOG
for pair in $pairs; do
  (
    set -- ${=pair}
    root=$1; sub=$2
    tag=${root:t}_$sub
    for v in $versions; do
      uv run python pipeline/3_judge.py --entity_type combination --responses_dir $root/$sub/responses \
        --output_dir $root/${sub}_v$v/scores --prompt_version $v $rt > $LOG/${tag}_v$v.log 2>&1
      echo "$tag v$v exit $?" >> $LOG/done.txt
    done
  ) &
done
wait
echo "all done" >> $LOG/done.txt
