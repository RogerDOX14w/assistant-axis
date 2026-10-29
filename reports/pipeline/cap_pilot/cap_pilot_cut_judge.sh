#!/usr/bin/env bash
# Cap pilot: judge the cap1024 responses cut at 256, 512 and 768 tokens (cut_responses.py; Roger,
# 2026-10-29), as the trees are judged: roles under step 3's default version (10), traits under
# version 12, both by gpt-5.6-luna on OpenAI Flex with --save_replies, the cut marked "…" (each
# cut response carries finish_reason "length").  Only the responses that a cap at N would cut are
# in a cut tree; the rest keep the whole response's score (cap1024's), which the readout takes.
# Into roger/cap_pilot/cap1024_cut<N>/judged/scores/<type>/; no gathering, since step 4 does not run
# on these.  Resumable: step 3 judges only what is not yet scored.  Run from the repo root:
#   reports/pipeline/cap_pilot/cap_pilot_cut_judge.sh > roger/cap_pilot/cut_judge.log 2>&1
set -uo pipefail
UV=/Users/roger/.local/bin/uv
SCP=(scp -q -F .secrets/runpod/ssh_config)
E=reports/pipeline/cap_pilot_entities.json
REMOTE=/workspace/cap_pilot
CUTS=${CUTS:-256 512 768}
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }
type_args() {  # as cap_pilot_judge_watch.sh
    case $1 in
        role)  echo "--judge_model gpt-5.6-luna --save_replies --no_batch --service_tier flex" ;;
        trait) echo "--prompt_version 12 --judge_model gpt-5.6-luna --save_replies --no_batch --service_tier flex" ;;
    esac
}
present() {  # the names of a type with a non-empty responses file in $1
    python3 -c "
import json, os, sys
d = sys.argv[1]
print(' '.join(n for n in json.load(open('$E'))['by_type'][sys.argv[2]]
               if os.path.exists(os.path.join(d, n + '.jsonl')) if os.path.getsize(os.path.join(d, n + '.jsonl'))))" "$1" "$2"
}

for n in $CUTS; do
    t=cap1024_cut$n out=roger/cap_pilot/cap1024_cut$n
    tmp="$out/.incoming.$$"
    mkdir -p "$tmp" "$out/responses"
    "${SCP[@]}" "pod:$REMOTE/$t/responses/*.jsonl" "$tmp/" || { stamp "$t: copy failed"; exit 1; }
    for f in "$tmp"/*; do mv -f "$f" "$out/responses/"; done
    rmdir "$tmp"
    stamp "$t: $(ls "$out/responses" | wc -l | tr -d ' ') response files; judging"
    for T in role trait; do
        names=$(present "$out/responses" "$T")
        [ -n "$names" ] || { stamp "$t: no $T responses that long"; continue; }
        $UV run python pipeline/3_judge.py --entity_type "$T" --roles $names $(type_args "$T") \
            --responses_dir "$out/responses" --output_dir "$out/judged/scores/$T" \
            || { stamp "$t: $T judging FAILED"; exit 1; }
    done
    stamp "$t: judged"
done
stamp "cut trees judged: $CUTS"
