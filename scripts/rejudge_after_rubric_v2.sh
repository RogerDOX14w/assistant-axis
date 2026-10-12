#!/bin/bash
# ---------------------------------------------------------------
# MAY 2026 RECORD, NOT A RECIPE TO RUN TODAY (walk-through A1,
# review 10 D1, 2026-10-12).  The guard below exits 2 unless
# HISTORICAL_RERUN=1; the reasons are in its message.
# ---------------------------------------------------------------
if [ "${HISTORICAL_RERUN:-}" != "1" ]; then
    cat >&2 <<'EOF'
rejudge_after_rubric_v2.sh is a May 2026 record (it ran once, on 2026-05-09),
not a recipe to run today (walk-through A1, review 10 D1, 2026-10-12).  Run
now, it would:
  - judge at B=10 with a uniform q9 subsample (the default is B=7 since May 2026);
  - pass no --budget_usd, so nothing caps the spend;
  - read the current pair_list_responses.json, not the _v1 record of what was
    judged then;
  - move today's correlations.json / gaps.json / correlation_plot.png aside in
    48 cohort dirs before rejudging them;
  - pass its pre-flight even if the pair-list read fails.
Copy the pattern into a new script with today's settings instead.  To rerun this
record deliberately, set HISTORICAL_RERUN=1 (after the cost confirmation in
AGENT_NOTES "Expensive Operations").
EOF
    exit 2
fi

# Rejudge response-mode caches after the rubric v1 -> v2 change
# (axis_judge_correlation.py:RUBRIC_RESPONSE_BATCH no longer names
# the entity in the body; see RUBRIC_VERSION history block in that
# file).
#
# v1 snapshots are at scores_responses__rubric_v1.json /
# correlations__rubric_v1.json / correlation_plot__rubric_v1.png
# in every response-mode subdir, plus the top-level derived
# aggregates (batch_size_curve_*, *_response_weight_sweep_slot6.*,
# gpt_sonnet_weight_sweep.*).  Those stay archived; this script
# only touches the canonical paths for the 4 production configs:
#
#   Phase 1: gpt b10 traits  (pair_list_responses.json, 12 axes)
#   Phase 2: gpt b10 roles
#   Phase 3: haiku b10_q9 traits
#   Phase 4: haiku b10_q9 roles
#
# The other 68 v1 caches (sonnet *, gpt b5/b7/b15, haiku b10-full,
# gpt-q9) are intentionally NOT rejudged -- they are not in the
# production pipeline.  Their v1 snapshots remain on disk for
# empirical v1<->v2 ρ comparison if ever needed.
#
# Pre-phase cleanup: for each of the 48 in-scope dirs, move the
# canonical correlations.json / gaps.json / correlation_plot.png
# aside to a timestamped <file>.bak.<YYYYMMDD_HHMMSS> sibling (since
# 2026-10-12, walk-through A1; it used to delete them, relying on the
# __rubric_v1 snapshots, which a rerun today would not match).
# scores_responses.json was already renamed
# to scores_responses__rubric_v1.json earlier.  With all canonical
# state cleared, the orchestrator's resume logic does a fresh run
# for every pair, so we do NOT pass --refill_gaps (which would be
# a no-op here anyway since corr_path won't exist).
#
# Each phase logs to /tmp/rejudge_v2_<ts>/<phase>.log.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="roger/axis_judge_experiments"
DATA_DIR='runpod_workspace/qwen/qwen-3-32b Roger 8slot'
PAIR_LIST="$ROOT/pair_list_responses.json"   # 12 axes
TS="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="/tmp/rejudge_v2_$TS"
mkdir -p "$LOG_DIR"
echo "Logs: $LOG_DIR"

IN_SCOPE_SUBDIRS=(
    gpt_responses_traits_b10
    gpt_responses_roles_b10
    haiku_responses_traits_b10_q9
    haiku_responses_roles_b10_q9
)

# ---------------------------------------------------------------
# Sanity check: every in-scope axis dir must already have a v1
# snapshot of scores_responses (renamed earlier).  Fail fast if
# anything is missing -- prevents silently overwriting v1 data.
# ---------------------------------------------------------------
echo
echo "=== Pre-flight: verify v1 snapshots exist for all 48 in-scope caches ==="
missing=0
while IFS= read -r pos_neg; do
    for sd in "${IN_SCOPE_SUBDIRS[@]}"; do
        d="$ROOT/$pos_neg/$sd"
        [ -d "$d" ] || { echo "  MISSING dir: $d"; missing=$((missing+1)); continue; }
        [ -f "$d/scores_responses__rubric_v1.json" ] \
            || { echo "  MISSING v1 snapshot: $d/scores_responses__rubric_v1.json"; missing=$((missing+1)); }
    done
done < <(uv run python -c "
import json
for p in json.load(open('$PAIR_LIST')):
    print(f'{p[\"pos\"]}_vs_{p[\"neg\"]}')
")
if [ "$missing" -gt 0 ]; then
    echo "ABORT: $missing in-scope dirs missing v1 snapshots."
    exit 1
fi
echo "  OK: all 48 in-scope dirs have v1 snapshots."

# ---------------------------------------------------------------
# Pre-phase cleanup: snapshot then move aside canonical state in the
# 48 in-scope dirs so the orchestrator does a clean fresh run.
# v1 versions are preserved at __rubric_v1 paths.
# scores_responses.json is already gone (renamed to __rubric_v1
# earlier in a separate pass).  This pass:
#   - snapshots gaps.json / run.log / config.json (which an earlier
#     pass overlooked) to their __rubric_v1 siblings, idempotently
#     (skip if a v1 sibling already exists; never overwrite),
#   - moves correlations.json / gaps.json / correlation_plot.png to
#     <file>.bak.$TS (never deleted) so the orchestrator's resume
#     logic does a fresh per-pair run.
# We keep config.json AND its v1 snapshot because the orchestrator
# rewrites config.json with new args+timestamps; v1 lets us diff
# the prior run's config retroactively.  run.log is a diagnostic
# tail and only of interest for v1<->v2 parse-failure forensics.
# ---------------------------------------------------------------
echo
echo "=== Cleanup: snapshot + move aside canonical state in 48 in-scope dirs ==="
cleared=0
snapshotted=0
while IFS= read -r pos_neg; do
    for sd in "${IN_SCOPE_SUBDIRS[@]}"; do
        d="$ROOT/$pos_neg/$sd"
        # Snapshot pass: gaps.json -> gaps__rubric_v1.json (etc.).
        # Idempotent: if v1 sibling already exists we leave it
        # alone (the existing v1 snapshot is the authoritative one;
        # we never overwrite a snapshot).
        for src in gaps.json run.log config.json; do
            if [ -f "$d/$src" ]; then
                stem="${src%.*}"
                ext="${src##*.}"
                snap="$d/${stem}__rubric_v1.${ext}"
                if [ ! -f "$snap" ]; then
                    cp "$d/$src" "$snap"
                    snapshotted=$((snapshotted+1))
                fi
            fi
        done
        # Move-aside pass (snapshot, never delete; walk-through A1).
        for f in correlations.json gaps.json correlation_plot.png; do
            if [ -f "$d/$f" ]; then
                mv -n "$d/$f" "$d/$f.bak.$TS"
                [ -f "$d/$f" ] && { echo "ABORT: could not move $d/$f aside"; exit 1; }
                cleared=$((cleared+1))
            fi
        done
    done
done < <(uv run python -c "
import json
for p in json.load(open('$PAIR_LIST')):
    print(f'{p[\"pos\"]}_vs_{p[\"neg\"]}')
")
echo "  snapshotted $snapshotted v1 siblings (gaps/run.log/config)"
echo "  moved aside $cleared canonical files to <file>.bak.$TS"

# ---------------------------------------------------------------
# Helper: orchestrator wrapper, mirrors rejudge_after_trait_edits.sh
# ---------------------------------------------------------------
run_orch() {
    local phase="$1"; shift
    echo
    echo "=== [$phase] $* ==="
    local log="$LOG_DIR/${phase}.log"
    if uv run python results_analysis/run_axis_experiment_batch.py "$@" \
        --data_dir "$DATA_DIR" --instructions_dir data \
        --concurrency 3 \
        2>&1 | tee "$log"; then
        echo "[$phase] DONE"
    else
        echo "[$phase] FAILED -- see $log"
        exit 1
    fi
}

# ---------------------------------------------------------------
# Phase 1: GPT b10 traits (full questions, no subsample).
# ---------------------------------------------------------------
run_orch phase1_gpt_b10_traits \
    --pair_list "$PAIR_LIST" \
    --provider gpt --judge_model gpt-4.1-mini \
    --output_root "$ROOT" \
    --score_responses \
    --scores_dir "$DATA_DIR/traits/scores" \
    --responses_dir "$DATA_DIR/traits/responses" \
    --subdir gpt_responses_traits_b10 \
    --response_target_batch_size 10

# ---------------------------------------------------------------
# Phase 2: GPT b10 roles.
# ---------------------------------------------------------------
run_orch phase2_gpt_b10_roles \
    --pair_list "$PAIR_LIST" \
    --provider gpt --judge_model gpt-4.1-mini \
    --output_root "$ROOT" \
    --score_responses \
    --scores_dir "$DATA_DIR/roles/scores" \
    --responses_dir "$DATA_DIR/roles/responses" \
    --subdir gpt_responses_roles_b10 \
    --response_target_batch_size 10

# ---------------------------------------------------------------
# Phase 3: Haiku b10 q9 traits (1/3 question subsample, modulo=9).
# ---------------------------------------------------------------
run_orch phase3_haiku_q9_traits \
    --pair_list "$PAIR_LIST" \
    --provider anthropic --judge_model claude-haiku-4-5-20251001 \
    --output_root "$ROOT" \
    --subdir haiku_responses_traits_b10_q9 \
    --score_responses \
    --scores_dir "$DATA_DIR/traits/scores" \
    --responses_dir "$DATA_DIR/traits/responses" \
    --response_target_batch_size 10 \
    --question_subsample_modulo 9 \
    --questions_file data/extraction_questions.jsonl

# ---------------------------------------------------------------
# Phase 4: Haiku b10 q9 roles.
# ---------------------------------------------------------------
run_orch phase4_haiku_q9_roles \
    --pair_list "$PAIR_LIST" \
    --provider anthropic --judge_model claude-haiku-4-5-20251001 \
    --output_root "$ROOT" \
    --subdir haiku_responses_roles_b10_q9 \
    --score_responses \
    --scores_dir "$DATA_DIR/roles/scores" \
    --responses_dir "$DATA_DIR/roles/responses" \
    --response_target_batch_size 10 \
    --question_subsample_modulo 9 \
    --questions_file data/extraction_questions.jsonl

echo
echo "=== ALL PHASES COMPLETE ==="
echo "Logs in $LOG_DIR"
echo
echo "Next steps:"
echo "  1. Inspect /tmp/rejudge_v2_*/phase*.log for any errors."
echo "  2. Spot-check a few v2 caches:"
echo "     uv run python -c \"import json; o=json.load(open('$ROOT/concise_vs_verbose/gpt_responses_traits_b10/scores_responses.json')); print(o['_provenance']['inputs'][0]['extras'])\""
echo "     -> should show 'rubric_version': 'v2'"
echo "  3. Regenerate derived aggregates from v2 caches:"
echo "       uv run python -m results_analysis.gpt_anthropic_response_weight_sweep --anthropic_model haiku_q9"
echo "       uv run python -m results_analysis.judge_ensemble_rho_curve  # only b10 column will be valid under v2"
echo "       uv run python -m results_analysis.plot_batch_size_quality_vs_cost  # b10 anchor only under v2"
