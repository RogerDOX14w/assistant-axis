#!/usr/bin/env bash
# Cap pilot, step 3 on the Mac (plan § 4; 2026-10-28): for each tree, wait until the pod has its
# 64 response files, copy them to roger/cap_pilot/<tree>/responses, judge them (roles by
# gpt-5.6-luna on OpenAI Flex with --save_replies; traits and combinations by gpt-4.1-mini through
# the Batch API, since Flex refuses gpt-4.1-mini; every judging with --mark_truncated, a
# response cut at the cap shown to the judge with " …"), one directory per type under
# judged/<scores>/<type>/ (step 3 stamps one rubric record per directory, and version 10's role and
# trait rubrics differ), gather the per-entity score files into <tree>/<scores>/ for step 4 and the
# compare tool, and copy them back to the pod.  cap512 is judged twice (scores/ and
# scores_rejudge/), the judge-only floor.  Resumable: step 3 judges only what is not yet scored.
# Run from the repo root:
#   nohup reports/pipeline/cap_pilot/cap_pilot_judge_watch.sh > roger/cap_pilot/judge_watch.log 2>&1 &
set -uo pipefail
UV=/Users/roger/.local/bin/uv
SSH=(ssh -o ConnectTimeout=20 -F .secrets/runpod/ssh_config)
SCP=(scp -q -F .secrets/runpod/ssh_config)
E=reports/pipeline/cap_pilot_entities.json
REMOTE=/workspace/cap_pilot
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }
names() { python3 -c "import json,sys; print(' '.join(json.load(open('$E'))['by_type'][sys.argv[1]]))" "$1"; }

judge() {  # tree scores_subdir
    local t=$1 sub=$2 out=roger/cap_pilot/$1
    stamp "$t: step 3 into $sub"
    $UV run python pipeline/3_judge.py --entity_type role --roles $(names role) \
        --judge_model gpt-5.6-luna --save_replies --mark_truncated --no_batch --service_tier flex \
        --responses_dir "$out/responses" --output_dir "$out/judged/$sub/role" || return 1
    for T in trait combination; do
        $UV run python pipeline/3_judge.py --entity_type $T --roles $(names $T) --mark_truncated \
            --responses_dir "$out/responses" --output_dir "$out/judged/$sub/$T" || return 1
    done
    mkdir -p "$out/$sub"
    for T in role trait combination; do
        for f in "$out/judged/$sub/$T"/*.json; do
            case "$(basename "$f")" in usage.json|judge_rubric.json|batch_state.json) ;; *) cp "$f" "$out/$sub/" ;; esac
        done
    done
    n=$(ls "$out/$sub"/*.json 2>/dev/null | wc -l | tr -d ' ')
    stamp "$t: $sub has $n score files"
    [ "$n" -eq 64 ] || { stamp "$t: expected 64 score files in $sub"; return 1; }
}

for t in cap256 cap512 cap512b cap768 cap1024; do
    out=roger/cap_pilot/$t
    while :; do
        n=$("${SSH[@]}" pod "ls $REMOTE/$t/responses/*.jsonl 2>/dev/null | wc -l" 2>/dev/null || echo err)
        [ "$n" = 64 ] && break
        sleep 300
    done
    stamp "$t: 64 response files on the pod; copying"
    mkdir -p "$out/responses"
    "${SCP[@]}" "pod:$REMOTE/$t/responses/*" "$out/responses/" || { stamp "$t: copy failed"; exit 1; }
    judge "$t" scores || { stamp "$t: judging FAILED"; exit 1; }
    [ "$t" = cap512 ] && { judge "$t" scores_rejudge || { stamp "$t: rejudge FAILED"; exit 1; }; }
    "${SSH[@]}" pod "mkdir -p $REMOTE/$t/scores" && \
        "${SCP[@]}" "$out"/scores/*.json "pod:$REMOTE/$t/scores/" || { stamp "$t: scores copy to the pod failed"; exit 1; }
    stamp "$t: scores on the pod"
done
stamp "all five trees judged"
