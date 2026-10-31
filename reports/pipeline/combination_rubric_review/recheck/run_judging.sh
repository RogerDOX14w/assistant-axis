#!/bin/zsh
# The combination re-check's judgings (2026-10-30), the exploration's three on the October sample built by
# build_sample.py under runpod_workspace/combo_recheck: each response as the combination (version 3's
# combination rubric, under the default version 13), as the role alone (version 10's text and A/B/C reading, 300
# tokens) and as the trait alone (version 13, 200 tokens), all by gpt-5.6-luna on Flex with the standard-tier
# fallback, replies saved.  "arms" as the first argument adds the draft combination versions 14 (both needed) and
# 15 (either enough) on the combination directory, into combo_v14/ and combo_v15/.  Cost: about $0.6 for the
# three runs on 20 combinations of 60 responses (3,600 calls), about $0.3 more for the arms; real time, under
# the $20 line.  Step 3 resumes, so a rerun after more files arrive judges only the new responses.
#
#   ./run_judging.sh          # the three judgings
#   ./run_judging.sh arms     # the three, then versions 14 and 15 on the combination directory
#   COMBO_ROOT=runpod_workspace/tcomb_recheck ./run_judging.sh arms   # another sample (the t_ one, built with
#                             # build_sample.py --out; logs go under logs/<root's last part>/)
cd ${0:a:h}/../../../.. || exit 1
R=${COMBO_ROOT:-runpod_workspace/combo_recheck}
LOG=${0:a:h}/logs
[ "$R" = runpod_workspace/combo_recheck ] || LOG=$LOG/${R:t}
mkdir -p $LOG
[ -f $R/sample.json ] || { echo "no $R/sample.json: run build_sample.py first" >&2; exit 1; }
stems=($(uv run python -c "import json; print(' '.join(json.load(open('$R/sample.json'))['combinations']))"))
rt=(--judge_model gpt-5.6-luna --no_batch --service_tier flex --save_replies --no_incongruity_filtering
    --requests_per_second 15 --batch_size 30)
(
  uv run python pipeline/3_judge.py --entity_type combination --responses_dir $R/combo/responses \
    --output_dir $R/combo/scores $rt > $LOG/combo.log 2>&1
  echo "combo exit $?" >> $LOG/done.txt
  if [ "$1" = "arms" ]; then
    for v in 14 15; do
      uv run python pipeline/3_judge.py --entity_type combination --responses_dir $R/combo/responses \
        --output_dir $R/combo_v$v/scores --prompt_version $v $rt > $LOG/combo_v$v.log 2>&1
      echo "combo_v$v exit $?" >> $LOG/done.txt
    done
  fi
) &
(
  for stem in $stems; do
    uv run python pipeline/3_judge.py --entity_type role --responses_dir $R/role/$stem/responses \
      --output_dir $R/role/$stem/scores $rt > $LOG/role_$stem.log 2>&1
    echo "role $stem exit $?" >> $LOG/done.txt
  done
) &
(
  for stem in $stems; do
    uv run python pipeline/3_judge.py --entity_type trait --responses_dir $R/trait/$stem/responses \
      --output_dir $R/trait/$stem/scores $rt > $LOG/trait_$stem.log 2>&1
    echo "trait $stem exit $?" >> $LOG/done.txt
  done
) &
wait
echo "all done" >> $LOG/done.txt
