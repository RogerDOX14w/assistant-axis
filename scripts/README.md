# `scripts/` directory

This directory holds **operational** shell scripts and Python orchestrators
that drive multi-phase judging campaigns, one-shot data migrations, and a
handful of diagnostic utilities.  These are intentionally separate from
[`results_analysis/`](../results_analysis/) (per-axis analysis producers
that read caches and emit plots / JSON), [`data_analysis/`](../data_analysis/)
(corpus-building tools that prepare trait/role data for the pipeline), and
[`tools/`](../tools/) (small, single-purpose utilities and audits).

Most scripts here are **idempotent** and safe to re-run, either by
honoring per-file freshness (e.g. `--refill_gaps`, the resume logic in
`run_axis_experiment_batch.py`) or by checking for prior outputs and
skipping when present.

## Quick index

| Script | Purpose | Cost | Idempotent? |
|---|---|---|---|
| [`rejudge_after_rubric_v2.sh`](./rejudge_after_rubric_v2.sh) | **May 2026 record, guarded.**  Response-mode rejudge after the 2026-05-09 rubric v1→v2 change (12 axes × 4 cohorts) | $$ judging cost | yes (resume-based) |
| [`rejudge_after_trait_edits.sh`](./rejudge_after_trait_edits.sh) | **May 2026 record, guarded.**  Multi-phase rejudge after April–May 2026 trait-file edits (desc/instr + responses, across GPT / Sonnet / Haiku) | $$$ today (see below) | yes (`--refill_gaps`) |
| [`run_phase5a_recompute.sh`](./run_phase5a_recompute.sh) | **May 2026 record, guarded.**  Recompute ~25 aggregate JSONs / plots after upstream caches change.  Pure numerical — no LLM calls. | free | yes (overwrites canonical aggregates) |
| [`run_phase5b_collision_rejudge.py`](./run_phase5b_collision_rejudge.py) | **May 2026 record, guarded.**  Surgical static-mode rejudge of the 9 trait/role collision names (patient, stoic, …) across 12 axes × {GPT, Haiku} | ~$0.55 in May; ~$13 today | no longer (rejudges all 24 cells today) |

**The four May 2026 recipes are guarded** (since 2026-10-12, walk-through
A1, review 10 D1): each exits 2 before doing anything unless
`HISTORICAL_RERUN=1` is set, and its message lists what it would do wrong
today (current pair lists instead of the `_v1` records, pre-B=7 batch sizes,
Sonnet 4.6 rejudging whole Sonnet 4.5 caches, no budget cap).  They are kept
as the record of what ran and as patterns to copy into a new script with
today's settings.  Tests:
[`tests/test_historical_recipe_guards.py`](./tests/test_historical_recipe_guards.py).
| [`run_describer_for_new_pcs.sh`](./run_describer_for_new_pcs.sh) | Batch driver: for each `pc<NNN>_<style>` cell missing `spec.json`, prepare inputs and run [`results_analysis/infer_axis_description.py`](../results_analysis/infer_axis_description.py) (Opus, ~30–60 s/cell) | ~$0.10/cell | yes (skips cells with existing `spec.json`) |
| [`move_sweep_logs_into_experiment_dirs.sh`](./move_sweep_logs_into_experiment_dirs.sh) | One-shot historical cleanup: move pre-2026-05-14 sweep logs out of `/workspace/` into their `{experiment}/sweep.log` homes | free | yes (skips when destination exists) |
| [`dump_rf_regret_regression_picks.py`](./dump_rf_regret_regression_picks.py) | Diagnostic: per-axis table of K picks under the RF regret-regression policy at ε=0.005 (the nominal "winner-by-a-hair" K-policy CV result) | free | yes (read-only) |

## When to use what

### After a rubric change

Use [`rejudge_after_rubric_v2.sh`](./rejudge_after_rubric_v2.sh) as the
template.  It demonstrates the canonical "snapshot to `__rubric_v1`, move
canonical paths aside, re-run from empty cache" pattern.  Pre-flight checks
that v1 snapshots exist before clearing, fails fast on any missing one.
Since 2026-10-12 (walk-through A1) it moves `correlations.json`,
`gaps.json` and `correlation_plot.png` to `<file>.bak.<YYYYMMDD_HHMMSS>`
beside the original instead of deleting them.

Scope: 12 axes in `pair_list_responses.json` × 4 in-scope cohorts (gpt
b10 traits/roles, haiku b10_q9 traits/roles).  The 68 out-of-scope v1
caches (sonnet, gpt b5/b7/b15, haiku b10-full, gpt-q9) are
*deliberately* NOT rejudged — they're frozen for comparison.

This particular script ran once on 2026-05-09 and is archival; the
pattern is what to copy for any future rubric bump.

### After a trait-file edit

Use [`rejudge_after_trait_edits.sh`](./rejudge_after_trait_edits.sh).  Seven
sequential phases:

1. `gpt desc/instr` — 33 axes covering everything desc/instr touched.
2–3. `gpt response` cohorts A (12-axis b15/b10) + B (3-axis b5/b7).
4. `sonnet desc/instr`.
5. `haiku desc/instr`.
6–7. `haiku response` + `sonnet response` cohorts.

Every phase uses `--refill_gaps`, so the orchestrator only re-judges
entries the pre-script cache invalidation actually cleared — unaffected
axes are no-ops.  Per-phase logs land in `/tmp/rejudge_<ts>/<phase>.log`.

Typical cost on a small edit (1–3 affected traits), in May 2026: ~$5–20.
A full-corpus regen would be much more; the `--refill_gaps` flag is the
key efficiency knob.  **Run today it costs several hundred dollars or
more**: it pins `claude-sonnet-4-6`, so every `claude-sonnet-4-5` cache is
rejudged whole (review 10 D1).  Since 2026-10-12 it therefore needs
`HISTORICAL_RERUN=1` and a required `--budget_usd <USD>`, a per-axis cap
passed to every phase's
[`run_axis_experiment_batch.py`](../results_analysis/run_axis_experiment_batch.py)
(each pair in each phase gets its own cap).

### After a numerical / cache change with no judging

Use [`run_phase5a_recompute.sh`](./run_phase5a_recompute.sh).  This
recomputes the second-tier aggregate JSONs and plots (whitening_k_sweep,
gpt_sonnet_weight_sweep, gpt_haiku_*_weight_sweep, response_di_weight_sweep,
rubric_v1_v2_compare, optimal_axis_for_judge diagnostics, peak fits,
scatter plots, etc.) after the upstream per-axis caches change.

Two tiers run in sequence; tier 1 is parallel-safe, tier 2 consumes
tier-1 outputs.  Failures in any one job don't abort the rest — the
final summary lists everything that didn't finish clean.  Pure
numerical: no LLM calls, no API spend.  Guarded since 2026-10-12
(`HISTORICAL_RERUN=1`): it reads the current pair lists, not the `_v1`
records that match the 8slot data, and overwrites the canonical aggregates.

### One-shot collision rejudge

Use [`run_phase5b_collision_rejudge.py`](./run_phase5b_collision_rejudge.py)
when you need to surgically re-judge the 9 trait/role collision
names (`patient`, `stoic`, `ascetic`, `contrarian`, `cosmopolitan`,
`generalist`, `pacifist`, `perfectionist`, `romantic`) in static mode
across all 12 axes × GPT + Haiku judges.

Mechanics: the producer's in-place v1→v2 cache migration drops
collision entries (because Bug A made bare-name values unreliable on
those), then a fresh judge pass refills just the dropped entries.
~$0.55 total spend; per-cell budget cap set to $5 with idempotent
short-circuit on already-v2 caches.

This particular script ran once in May 2026 as part of Phase 5b of
the trait/role disambiguation plan; the pattern is portable to any
future "fix-N-broken-entities-per-cache" surgical rejudge.  Its
"idempotent no-op on already-v2 caches" no longer holds: run today it
would rejudge all 24 cells (~$13), overwriting the May caches, hence the
`HISTORICAL_RERUN=1` guard.

### Generating Opus axis descriptions for new PCs

Use [`run_describer_for_new_pcs.sh`](./run_describer_for_new_pcs.sh)
once you've populated `axis_postshear.pt` and
`post_shear_projection.json` for new PCs (typically via
[`results_analysis/pc_round_trip/launch_judge_runs.py`](../results_analysis/pc_round_trip/launch_judge_runs.py)).

Default PCs: `3 6 12`; default styles: `glossary inline`.  Override
via positional args: `bash scripts/run_describer_for_new_pcs.sh "9 10" "glossary"`.

Per cell: converts `post_shear_projection.json` into
`input_scores.json` (parsing disambiguated `name|R` / `name|T`
entity_ids), then invokes
[`results_analysis/infer_axis_description.py`](../results_analysis/infer_axis_description.py)
against Opus.

### Legacy sweep-log relocation

Use [`move_sweep_logs_into_experiment_dirs.sh`](./move_sweep_logs_into_experiment_dirs.sh)
only if for some reason new sweep logs end up scattered across
`/workspace/` again — the 2026-05-14 update to `run_sweep.py` made
all future sweep logs land at `{experiment}/sweep.log` automatically,
so this should no longer be needed.

### Diagnostic: which K does the RF regret-regression policy pick?

Run [`dump_rf_regret_regression_picks.py`](./dump_rf_regret_regression_picks.py)
to print the per-axis K table for the RF regret-regression policy at
ε=0.005.  Useful for confirming whether the "winner-by-a-hair" K-policy
swap actually changes the K choice for non-trivially-many axes (it
mostly picks K=1 with a few K=0 outliers).

Output: per-axis table sorted (primary axes first, then alphabetical)
with predicted K, true K* (ε=0.005), ρ at predicted vs ρ at K=1.

## Conventions used across these scripts

- **Run from repo root.**  Most scripts `cd "$(dirname "$0")/.."` at the
  top so they're agnostic to the caller's CWD.
- **Per-phase logs** under `/tmp/<scriptname>_<ts>/` or
  `/tmp/<scriptname>_<ts>.log`.  Persistent across reboots only if
  copied somewhere durable.
- **Pair-list selection** is via JSON files under
  [`roger/axis_judge_experiments/pair_list_*.json`](../roger/axis_judge_experiments/)
  — see [`AGENT_NOTES.md`](../AGENT_NOTES.md) "Pair lists" for the
  canonical inventory.
- **Idempotency** is a hard requirement; the cache-invalidation
  pattern (snapshot to `__rubric_vN`, clear canonical, resume) plus
  `--refill_gaps` make every script safe to re-run.
- **Cost discipline**: see the
  [`HARD RULE — Expensive Operations`](../AGENT_NOTES.md#expensive-operations--confirm-parameters-first-hard-rule)
  in `AGENT_NOTES.md` before launching any judging-cost script.
  `run_phase5b_collision_rejudge.py` has a per-cell $5 cap as
  example — copy that defensive pattern for any new orchestrator.
