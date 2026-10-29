#!/usr/bin/env bash
# Cap pilot, step 3 on the Mac (plan § 4; 2026-10-28): for each tree, wait until the pod has its
# 64 response files, copy them to roger/cap_pilot/<tree>/responses, judge them, one directory per
# entity type under judged/<scores>/<type>/ (step 3 stamps one rubric record per directory, and
# version 10's role and trait rubrics differ), gather the per-entity score files into
# <tree>/<scores>/ for step 4 and the compare tool, and copy them back to the pod.  cap512 is
# judged twice (scores/ and scores_rejudge/), the judge-only floor.  Resumable: step 3 judges only
# what is not yet scored.
#
# Roles: gpt-5.6-luna on OpenAI Flex, --save_replies, step 3's default version (10).  Traits: the
# same judge under version 12, the draft trait rubric (Roger, 2026-10-29: "Traits rubric is likely
# to be v12, work with that for the moment"; the trait test plans the extraction's trait judging
# around luna).  If version 12's text changes when it is pinned, step 3 refuses these directories
# (the stamp's hash) and the traits are judged again.  Combinations: step 3's default judge
# (gpt-4.1-mini) through the Batch API (Flex refuses it), version 3's text for now (Roger,
# 2026-10-29: a new combination rubric is coming, not yet due), and again once that rubric is
# settled.  Every judging marks a response cut at the cap with "…" (step 3's default since
# 2026-10-28; the pilot's cap256 was judged with " …" first and is kept as scores_space_marker).
#
# TYPES (default "role trait combination") names the entity types to judge; watchers for
# different types can run side by side (TYPES="role combination" and TYPES=trait on 2026-10-29).
# TREES (default all five) names the trees.  Run from the repo root:
#   TYPES=trait reports/pipeline/cap_pilot/cap_pilot_judge_watch.sh > roger/cap_pilot/judge_watch_trait.log 2>&1
set -uo pipefail
UV=/Users/roger/.local/bin/uv
SSH=(ssh -o ConnectTimeout=20 -F .secrets/runpod/ssh_config)
SCP=(scp -q -F .secrets/runpod/ssh_config)
E=reports/pipeline/cap_pilot_entities.json
REMOTE=/workspace/cap_pilot
TYPES=${TYPES:-role trait combination}
TREES=${TREES:-cap256 cap512 cap512b cap768 cap1024}
stamp() { echo "[$(date -u +%FT%TZ)] $*"; }
type_args() {  # step 3's judge arguments for an entity type
    case $1 in
        role)  echo "--judge_model gpt-5.6-luna --save_replies --no_batch --service_tier flex" ;;
        trait) echo "--prompt_version 12 --judge_model gpt-5.6-luna --save_replies --no_batch --service_tier flex" ;;
        *)     echo "" ;;
    esac
}
names() { python3 -c "import json,sys; print(' '.join(json.load(open('$E'))['by_type'][sys.argv[1]]))" "$1"; }

expected=0
for T in $TYPES; do expected=$((expected + $(names "$T" | wc -w))); done
stamp "types: $TYPES ($expected entities per tree); trees: $TREES"

judge() {  # tree scores_subdir
    local t=$1 sub=$2 out=roger/cap_pilot/$1
    stamp "$t: step 3 into $sub"
    for T in $TYPES; do
        $UV run python pipeline/3_judge.py --entity_type "$T" --roles $(names "$T") $(type_args "$T") \
            --responses_dir "$out/responses" --output_dir "$out/judged/$sub/$T" || return 1
    done
    mkdir -p "$out/$sub"
    n=0
    for T in $TYPES; do
        for f in "$out/judged/$sub/$T"/*.json; do
            case "$(basename "$f")" in
                usage.json|judge_rubric.json|batch_state.json) ;;
                # renamed in, so that the other watcher's copy to the pod never takes one half-written
                *) cp "$f" "$out/$sub/.incoming.$$" && mv -f "$out/$sub/.incoming.$$" "$out/$sub/$(basename "$f")" \
                       || return 1
                   n=$((n + 1)) ;;
            esac
        done
    done
    stamp "$t: $sub has $n score files for $TYPES"
    [ "$n" -eq "$expected" ] || { stamp "$t: expected $expected score files in $sub"; return 1; }
}

for t in $TREES; do
    out=roger/cap_pilot/$t
    while :; do
        n=$("${SSH[@]}" pod "ls $REMOTE/$t/responses/*.jsonl 2>/dev/null | wc -l" 2>/dev/null || echo err)
        [ "$n" = 64 ] && break
        sleep 300
    done
    stamp "$t: 64 response files on the pod; copying"
    # copied beside the directory and renamed in, file by file, so that another watcher (one per
    # entity type) reading these files never sees one half-written
    tmp="$out/.incoming.$$"
    mkdir -p "$tmp" "$out/responses"
    "${SCP[@]}" "pod:$REMOTE/$t/responses/*" "$tmp/" || { stamp "$t: copy failed"; exit 1; }
    for f in "$tmp"/*; do mv -f "$f" "$out/responses/"; done
    rmdir "$tmp"
    judge "$t" scores || { stamp "$t: judging FAILED"; exit 1; }
    if [ "$t" = cap512 ]; then
        judge "$t" scores_rejudge || { stamp "$t: rejudge FAILED"; exit 1; }
    fi
    "${SSH[@]}" pod "mkdir -p $REMOTE/$t/scores" && \
        "${SCP[@]}" "$out"/scores/*.json "pod:$REMOTE/$t/scores/" || { stamp "$t: scores copy to the pod failed"; exit 1; }
    stamp "$t: scores on the pod"
done
stamp "trees judged for $TYPES: $TREES"
