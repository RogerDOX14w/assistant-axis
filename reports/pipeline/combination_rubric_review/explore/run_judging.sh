#!/bin/zsh
# The combination exploration's three judgings of the sample (Roger, 2026-10-30): each response as the
# combination (version 3's combination rubric, under the default version 13), as the role alone (version 10's
# text and A/B/C reading, 300 tokens) and as the trait alone (version 13, 200 tokens), all by gpt-5.6-luna on
# Flex with the standard-tier fallback, replies saved.  The combination run covers every stem at once; the role
# and trait runs go combination by combination (several combinations share a role or a trait).
cd /Users/roger/Documents/GitHub/assistant-axis || exit 1
R=runpod_workspace/combo_explore
LOG=${0:a:h}/logs
mkdir -p $LOG
rt=(--judge_model gpt-5.6-luna --no_batch --service_tier flex --save_replies --no_incongruity_filtering
    --requests_per_second 15 --batch_size 30)
(
  uv run python pipeline/3_judge.py --entity_type combination --responses_dir $R/combo/responses \
    --output_dir $R/combo/scores $rt > $LOG/combo.log 2>&1
  echo "combo exit $?" >> $LOG/done.txt
) &
(
  for stem in $(uv run python -c "import json; print(' '.join(json.load(open('$R/sample.json'))['combinations']))"); do
    uv run python pipeline/3_judge.py --entity_type role --responses_dir $R/role/$stem/responses \
      --output_dir $R/role/$stem/scores $rt > $LOG/role_$stem.log 2>&1
    echo "role $stem exit $?" >> $LOG/done.txt
  done
) &
(
  for stem in $(uv run python -c "import json; print(' '.join(json.load(open('$R/sample.json'))['combinations']))"); do
    uv run python pipeline/3_judge.py --entity_type trait --responses_dir $R/trait/$stem/responses \
      --output_dir $R/trait/$stem/scores $rt > $LOG/trait_$stem.log 2>&1
    echo "trait $stem exit $?" >> $LOG/done.txt
  done
) &
wait
echo "all done" >> $LOG/done.txt
