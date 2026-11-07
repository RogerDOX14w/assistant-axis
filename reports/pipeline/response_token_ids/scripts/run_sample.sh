#!/usr/bin/env bash
# The response-token-ids sample (reports/pipeline/response_token_ids/plan.md
# § 9, with the review's additions in build_report.md) on the sample pod, the
# roles volume: 20 entities through the new step 1 once (the family strip, ids
# stored), step 2 three ways on the same responses (text: today's path; ids:
# the stored ids, slot 0 over the content range; turn: the stored ids, slot 0
# over the whole generated turn), the padding floor (the text path at batch
# size 1 on two entities), step 3 once per entity type, steps 4 and 5 per
# variant, then the per-response comparisons and the token count on the pod,
# since the activations (about 170 GB) stay on the container disk.
#
# Launched as:
#   setsid nohup bash /root/run_sample.sh > /root/sample_ids/run.log 2>&1 &
# One step: bash /root/run_sample.sh 1|23|4|5|6  (all when omitted; each step
# skips files already there only where the pipeline step itself does).
set -uo pipefail
export PATH="$HOME/.local/bin:$PATH"
[ -f /workspace/pod_env.sh ] && source /workspace/pod_env.sh
# The template's secrets reach PID 1 only; an ssh shell has none.
if [ -z "${OPENAI_API_KEY:-}" ] && [ -r /proc/1/environ ]; then
    while IFS= read -r -d '' kv; do
        case "$kv" in OPENAI_API_KEY=*|HF_TOKEN=*) export "$kv" ;; esac
    done < /proc/1/environ
fi
export HF_HOME="${HF_HOME:-/workspace/.cache/huggingface}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-/workspace/.uv-cache}"
export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-/root/venvs/assistant-axis}"
export UV_LINK_MODE="${UV_LINK_MODE:-copy}"
export CUDA_VISIBLE_DEVICES=0
REPO=/workspace/assistant-axis
OUT=/root/sample_ids
SCRIPTS=/root/sample_scripts          # compare_activations.py, token_diff.py
MODEL=Qwen/Qwen3-32B
# Plan § 9's table: heavy leakers, cap-heavy, the six controls drawn with seed
# 20261103 (draw_controls.py), and the default.  The role specialist, not the
# trait (264 capped in October).
ROLES="gamer child researcher specialist witness operator angel"
TRAITS="aural_vark plugged_in millennial stream_of_consciousness gen_z thorough verbose exclusionary autistic flirty"
COMBOS="r_competitor__aural_vark r_rebel__aural_vark"
PAD_ENTITIES="gamer thorough"         # the padding floor: a leaker and a capped one
VARIANTS="text ids turn"

cd "$REPO/pipeline" || exit 1
stamp() { echo "== $(date -u +%FT%TZ) $*"; }
step=${1:-all}
want() { [ "$step" = all ] || [ "$step" = "$1" ]; }
mkdir -p "$OUT/responses" "$OUT/scores/all" "$OUT/logs" "$OUT/compare"
stamp "checkout: $(git -C "$REPO" log --oneline -1)"
if [ -z "${OPENAI_API_KEY:-}" ]; then
    echo "no OPENAI_API_KEY in the environment (nor in PID 1's): step 3 cannot run"; exit 1
fi
nvidia-smi --query-gpu=index,name,memory.used --format=csv,noheader

# ---- step 1: four runs into one responses directory -----------------------
# One side-car (generation_config.json) with four run records; the settings
# are the same, so no --allow_mixed_settings.  The driver's flags for each
# type (run_pipeline.sh, roger mode): --reduce_questions 3, --max_tokens 1024.
if want 1; then
    GEN="uv run python 1_generate.py --mode roger --model $MODEL --tensor_parallel_size 1 --max_tokens 1024 --reduce_questions 3 --output_dir $OUT/responses"
    stamp "step 1a: roles: $ROLES"
    $GEN --roles_only --roles $ROLES > "$OUT/logs/step1_roles.log" 2>&1; echo "   exit $?"
    stamp "step 1b: traits: $TRAITS"
    $GEN --traits_only --roles $TRAITS > "$OUT/logs/step1_traits.log" 2>&1; echo "   exit $?"
    stamp "step 1c: combinations: $COMBOS"
    $GEN --no_traits --combos_only_r --goal_count 30 --non_goal_count 30 --roles $COMBOS \
        > "$OUT/logs/step1_combos.log" 2>&1; echo "   exit $?"
    stamp "step 1d: default"
    $GEN --roles_only --roles default > "$OUT/logs/step1_default.log" 2>&1; echo "   exit $?"
    stamp "step 1 summary"
    uv run python - "$OUT/responses" "$OUT/step1_summary.json" <<'EOF'
import json, sys
from pathlib import Path
d, out = Path(sys.argv[1]), Path(sys.argv[2])
rows = {}
for f in sorted(d.glob("*.jsonl")):
    n = stripped = susp = capped = null = with_ids = edge_ws = 0
    for line in open(f):
        r = json.loads(line); n += 1
        stripped += bool(r.get("thinking_stripped")); susp += bool(r.get("thinking_suspected"))
        capped += r.get("finish_reason") == "length"
        with_ids += r.get("response_token_ids") is not None
        null += r.get("response_token_ids") is not None and r.get("content_token_range") is None
        c = r["conversation"][-1]["content"]
        edge_ws += bool(c) and (c[0].isspace() or c[-1].isspace())
    rows[f.stem] = dict(n=n, stripped=stripped, suspected=susp, capped=capped, with_ids=with_ids,
                        range_null=null, edge_whitespace=edge_ws)
    print(f"   {f.stem:28} n={n} stripped={stripped} suspected={susp} capped={capped} "
          f"with_ids={with_ids} range_null={null} edge_ws={edge_ws}")
tot = {k: sum(r[k] for r in rows.values()) for k in next(iter(rows.values()))}
print("   total", tot)
out.write_text(json.dumps({"per_entity": rows, "total": tot}, indent=1) + "\n")
EOF
    # Per-type views of the same files for step 3 (--entity_type per run).
    for t in roles traits combinations; do mkdir -p "$OUT/by_type/$t"; done
    for e in $ROLES; do ln -sfn "../../responses/$e.jsonl" "$OUT/by_type/roles/$e.jsonl"; done
    for e in $TRAITS; do ln -sfn "../../responses/$e.jsonl" "$OUT/by_type/traits/$e.jsonl"; done
    for e in $COMBOS; do ln -sfn "../../responses/$e.jsonl" "$OUT/by_type/combinations/$e.jsonl"; done
fi

# ---- steps 2 and 3, concurrently (as the driver runs them) -----------------
run_step2() {
    local ACT="uv run python 2_activations.py --model $MODEL --responses_dir $OUT/responses --tensor_parallel_size 1 --batch_size 4"
    local rc=0
    stamp "step 2 text: --token_source text --verify_spans 20 (today's path)"
    $ACT --output_dir "$OUT/act_text" --token_source text --verify_spans 20 \
        > "$OUT/logs/step2_text.log" 2>&1 || { rc=$?; echo "   step 2 text FAILED (exit $rc)"; return $rc; }
    stamp "step 2 ids: --token_source ids --verify_ids 20 (slot 0 over the content range)"
    $ACT --output_dir "$OUT/act_ids" --token_source ids --verify_ids 20 \
        > "$OUT/logs/step2_ids.log" 2>&1 || { rc=$?; echo "   step 2 ids FAILED (exit $rc)"; return $rc; }
    stamp "step 2 turn: --token_source ids --content_span turn (slot 0 over the whole turn)"
    $ACT --output_dir "$OUT/act_turn" --token_source ids --content_span turn \
        > "$OUT/logs/step2_turn.log" 2>&1 || { rc=$?; echo "   step 2 turn FAILED (exit $rc)"; return $rc; }
    stamp "step 2 padding floor: the text path at batch size 1 on $PAD_ENTITIES"
    uv run python 2_activations.py --model $MODEL --responses_dir "$OUT/responses" --tensor_parallel_size 1 \
        --batch_size 1 --roles $PAD_ENTITIES --output_dir "$OUT/act_text_bs1" --token_source text \
        > "$OUT/logs/step2_text_bs1.log" 2>&1 || { rc=$?; echo "   step 2 padding floor FAILED (exit $rc)"; return $rc; }
    stamp "step 2 done"
    du -sh "$OUT"/act_* 2>/dev/null | sed 's/^/   /'
}
run_step3() {
    # Flex with the standard-tier fallback, the driver's roger-mode default
    # (--no_batch --service_tier flex), the default judge (gpt-5.6-luna) under
    # the default rubric version (20), replies saved as in October.
    local rc=0 d e
    for t in roles:role traits:trait combinations:combination; do
        d=${t%%:*}; e=${t##*:}
        stamp "step 3 $d: --entity_type $e, Flex"
        uv run python 3_judge.py --entity_type "$e" --responses_dir "$OUT/by_type/$d" \
            --output_dir "$OUT/scores/$d" --no_batch --service_tier flex --save_replies \
            > "$OUT/logs/step3_$d.log" 2>&1 || { rc=$?; echo "   step 3 $d FAILED (exit $rc)"; }
        grep -E "\[usage\]" "$OUT/logs/step3_$d.log" | tail -2 | sed 's/^/   /'
    done
    stamp "step 3 done"
    return $rc
}
if want 23; then
    run_step2 > "$OUT/logs/step2.log" 2>&1 &
    P2=$!
    run_step3 > "$OUT/logs/step3.log" 2>&1 &
    P3=$!
    stamp "steps 2 (pid $P2) and 3 (pid $P3) running"
    wait $P2; R2=$?; cat "$OUT/logs/step2.log"
    wait $P3; R3=$?; cat "$OUT/logs/step3.log"
    stamp "step 2 exit $R2, step 3 exit $R3"
    if [ $R2 -ne 0 ] || [ $R3 -ne 0 ]; then
        echo "a step failed; steps 4 to 6 not run (rerun with the step number once fixed)"; exit 1
    fi
fi

# ---- step 4: one vectors directory per variant ------------------------------
# The three types' score files in one directory (the stamp, usage and
# disagreement files left out); step 4 reads <stem>.json per entity and takes
# the default's mean over all its responses without a scores file.
if want 4; then
    for d in roles traits combinations; do
        for f in "$OUT/scores/$d"/*.json; do
            b=$(basename "$f")
            case "$b" in judge_rubric.json|usage.json) continue ;; esac
            ln -sfn "$f" "$OUT/scores/all/$b"
        done
    done
    echo "   $(ls "$OUT/scores/all" | wc -l) score files linked"
    for v in $VARIANTS text_bs1; do
        stamp "step 4 $v: --min_count 30"
        OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 uv run python 4_vectors.py --activations_dir "$OUT/act_$v" \
            --scores_dir "$OUT/scores/all" --output_dir "$OUT/vec_$v" --min_count 30 \
            > "$OUT/logs/step4_$v.log" 2>&1; echo "   exit $?; $(ls "$OUT/vec_$v"/*.pt 2>/dev/null | wc -l) vectors"
        grep -E "WARNING|ERROR|BelowMinCount|skipp" "$OUT/logs/step4_$v.log" | head -10 | sed 's/^/   /'
    done
fi

# ---- step 5: an axis per variant (19 entities against the default) ---------
if want 5; then
    for v in $VARIANTS; do
        stamp "step 5 $v"
        uv run python 5_axis.py --vectors_dir "$OUT/vec_$v" --output "$OUT/axis_$v.pt" \
            --responses_dir "$OUT/responses" > "$OUT/logs/step5_$v.log" 2>&1; echo "   exit $?"
        grep -E "WARNING|ERROR|entities|Saved" "$OUT/logs/step5_$v.log" | tail -4 | sed 's/^/   /'
    done
fi

# ---- step 6: the comparisons on the pod ------------------------------------
if want 6; then
    CMP="uv run python $SCRIPTS/compare_activations.py --responses_dir $OUT/responses"
    for pair in text:ids ids:turn text:turn text:text_bs1; do
        a=${pair%%:*}; b=${pair##*:}
        stamp "compare act_$a vs act_$b"
        $CMP "$OUT/act_$a" "$OUT/act_$b" --out "$OUT/compare/${a}_vs_${b}" \
            > "$OUT/logs/compare_${a}_vs_${b}.log" 2>&1; echo "   exit $?"
        tail -25 "$OUT/logs/compare_${a}_vs_${b}.log" | sed 's/^/   /'
    done
    stamp "token diff (measurement 1): the stored ids against the text path's re-encoding"
    uv run python "$SCRIPTS/token_diff.py" --model "$MODEL" --responses_dir "$OUT/responses" \
        --out "$OUT/compare/token_diff" > "$OUT/logs/token_diff.log" 2>&1; echo "   exit $?"
    tail -30 "$OUT/logs/token_diff.log" | sed 's/^/   /'
fi
stamp "done ($step)"
