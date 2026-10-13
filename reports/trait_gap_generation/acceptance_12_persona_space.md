# Acceptance report: workstream 12, novelty measured in persona space

Built 2026-10-13 (Opus 5.5) from [coding_plan_12_persona_space.md](./coding_plan_12_persona_space.md), with Roger's
two decisions of 2026-10-13 as recommended: the score lives in a **`persona` block on the registry row** (1a), and
the disagreements go **to Roger and through M3's own overlap call** (2b).  Every free step has run; the paid steps
(about $2.1 in all) are listed at the end with their commands, for the coordinator to run from the main checkout.
Terms: the plan's own are in the [glossary](./glossary.md#persona-space-novelty) (canonical cell, ridge, kind
covariate, arrangement-grouped folds, energy outside the top N, shrinkage, calibration percentile, pair-axis
position, duplicate-like and novel-like, disagreement quantile, orphan vector, prospective test).

## What was built (§ 5)

- The package [persona_space/](../../assistant_axis/gapgen/persona_space/__init__.py):
  [pool.py](../../assistant_axis/gapgen/persona_space/pool.py) (the 582-row pool keyed `name|T` / `name|R`, the
  training rows, fold groups, pair partners, the residual),
  [fit.py](../../assistant_axis/gapgen/persona_space/fit.py) (ridge, grouped cross-validation, the alpha and N rules,
  the model file), [calibrate.py](../../assistant_axis/gapgen/persona_space/calibrate.py) (the percentile, the
  z-score, the flags, the overlap-test check), [score.py](../../assistant_axis/gapgen/persona_space/score.py) (M3's
  candidate selection, the scores, the block, `apply_blocks`),
  [compare.py](../../assistant_axis/gapgen/persona_space/compare.py) (agreement with M3, the three disagreement
  kinds), [judge.py](../../assistant_axis/gapgen/persona_space/judge.py) (decision 2b through
  `NoveltyRunner.run_pairs`), [prospective.py](../../assistant_axis/gapgen/persona_space/prospective.py) and
  [report.py](../../assistant_axis/gapgen/persona_space/report.py); the frozen interface of the plan's last section
  is exported from the package.
- The CLI [persona_novelty.py](../../data_analysis/gap_generation/persona_novelty.py): `fit`, `score`, `apply`,
  `compare`, `judge-disagreements`, `prospective predict | compare`, `report`.
- The one platform edit: `BLOCKS` in [registry.py](../../assistant_axis/gapgen/registry.py) gains `"persona"`
  (enumerated by `test_blocks_enumerated` in [test_gapgen_registry.py](../../assistant_axis/tests/test_gapgen_registry.py));
  `ROW_FIELDS` is unchanged, so a new row has no `persona` key until it is scored.
- [.gitignore](../../.gitignore): `data/candidates/persona/**/*.npz` (the 63 MB model and the float16 predictions)
  and `**/*.bak.*`.
- Tests ([persona_space_fakes.py](../../assistant_axis/tests/persona_space_fakes.py) and the files below), the
  [glossary](./glossary.md#persona-space-novelty) section, [QUESTIONS](./QUESTIONS.md) 140-159, and in the plan the
  pre-registered entries renumbered 91-99 → 140-148.

## Deviations, with reasons

1. **572 training rows, not 574.**  The plan's § 1 keeps the sense-changed renames out of training; two of the three
   have a May vector (libertarian, savage; bland has none), so 293 traits and 279 roles train.  "574 with a current
   file" holds (295 + 279).  Every measured figure moved by less than 0.02.
2. **699 pending entities, not 698** (639 traits, 60 roles; QUESTIONS 149): the same rule makes
   [violent](../../data/traits/instructions/violent.json) and
   [metaphysical_libertarian](../../data/traits/instructions/metaphysical_libertarian.json) pending, and
   [instrumentally_aligned_ai](../../data/roles/instructions/instrumentally_aligned_ai.json) not.
3. **The alpha rule has a 0.01 tie window** (QUESTIONS 150): without it alpha 1 (median cosine 0.737) beats 0.3
   (0.732) on a difference five folds cannot resolve, while 0.3 recovers better and ranks residuals better.
4. **Role texts use the mechanical display form** (`devils advocate: ...`; QUESTIONS 151): the form every role text
   is cached under, so the fit costs $0 and reproduces the plan's measurement.
5. **485 fold groups** (QUESTIONS 152): every role arrangement but `singleton` groups its members.
6. **Ridge is solved in closed form** (the dual, as scikit-learn's `Ridge` solves it; a test checks the two agree to
   1e-8) so that two fits give the same bytes and a rebuilt model can be checked by its arrays' sha256.
7. **Added, not in § 5**: the flag's base rate and the duplicate threshold's check against the overlap test's rubric-A
   readings (in [calibration.json](../../data/candidates/persona/fit/fit_2026-10-13/calibration.json) and the fit
   report; § 1 names those readings as calibration data); the gloss-side check of the measured figures; `score`
   writes `score_report.md` itself (`report` rewrites it); `--snapshot`, `--keys-file`, `--pool-cache-dir`,
   `--force`, `--rebuild-model`, the gate-1 overrides (`--alpha`, `--N`, `--dup-threshold`, `--novel-pct`,
   `--thresholds-set-by`) and `judge-disagreements --write-registry` (the reading also goes on the blocks by itself when `score` wrote them to the same registry, as § 7 says); score rows add `nearest_traits`,
   `m3_covered_by`, `m3_cosine`, `cos_to_covered_by` and `holding` (fields added, none renamed).
8. **Readings of § 6** the plan left open (QUESTIONS 154, 155): the overlap call's "other" is the persona-nearest
   *trait*; each disagreement kind is capped separately at 10% of the scored rows; the agreement with M3 is read on the
   nearest trait's cosine.
9. **A $0 smoke batch on real data** (QUESTIONS 156): the 36 rows whose `label: gloss` text was already cached.
10. **The whole suite** (`uv run pytest -q`) stops on collection errors that predate this build (the `tests` packages
    of `results_analysis` and `tools` collide, as plans 04 and 13 found), so it was run directory by directory.

## Commands (§ 8), in the worktree

```
VIRTUAL_ENV= uv run --extra dev python -m pytest assistant_axis/tests/test_gapgen_persona_space_*.py data_analysis/tests/test_gap_generation_persona_novelty_cli.py assistant_axis/tests/test_gapgen_persona.py assistant_axis/tests/test_gapgen_registry.py -q
    115 passed, 2 skipped  (the skips: the full-batch acceptance check, waiting for the paid step; test_gapgen_persona's
    real-pool test, which looks for the vectors at the default path, absent in this worktree)
uv run pytest -q   # by directory, see deviation 10
    assistant_axis/tests 4,111 passed, 51 skipped; data_analysis/tests 906 passed; results_analysis/tests 193 passed;
    pipeline/tests 232 passed; tools/tests 262 passed.  No failures.  Left out: test_generation.py (Hugging Face
    tokenizers, absent here) and test_boundary_check.py (needs .claude/hooks/, absent from this sparse worktree)
uv run python data_analysis/gap_generation/rubric_pins.py check     # exit 0: no rubric changed
uv run python data_analysis/check_arrangements.py --quiet           # exit 0
uv run python tools/sync_entity_lists.py --check                    # exit 0 (932 traits, 339 roles up to date)
git status --porcelain data/traits data/roles data/seed_queue.json  # empty
```

The hard tests read the vectors tree and the embedding cache of the main checkout through
`PERSONA_SPACE_VECTORS_DIR` and `PERSONA_SPACE_EMBED_CACHE` (in the main checkout the defaults find them).  The
acceptance file [test_gapgen_persona_space_acceptance.py](../../assistant_axis/tests/test_gapgen_persona_space_acceptance.py)
checks the recorded fit, the batches and the prospective rows; its full-batch check waits for the paid step and
`compact`.  The tests: [pool](../../assistant_axis/tests/test_gapgen_persona_space_pool.py),
[fit](../../assistant_axis/tests/test_gapgen_persona_space_fit.py),
[calibrate](../../assistant_axis/tests/test_gapgen_persona_space_calibrate.py),
[score](../../assistant_axis/tests/test_gapgen_persona_space_score.py),
[compare](../../assistant_axis/tests/test_gapgen_persona_space_compare.py),
[judge](../../assistant_axis/tests/test_gapgen_persona_space_judge.py),
[prospective](../../assistant_axis/tests/test_gapgen_persona_space_prospective.py),
[CLI](../../data_analysis/tests/test_gap_generation_persona_novelty_cli.py).

## The fit (gate 1), $0

[fit_report.md](../../data/candidates/persona/fit/fit_2026-10-13/fit_report.md) and
[fit_report.png](../../data/candidates/persona/fit/fit_2026-10-13/fit_report.png) (read back: no overlaps), from
[cv.json](../../data/candidates/persona/fit/fit_2026-10-13/cv.json) and
[calibration.json](../../data/candidates/persona/fit/fit_2026-10-13/calibration.json);
[run.json](../../data/candidates/persona/fit/fit_2026-10-13/run.json), 0 calls.

**The pool.**  582 vectors at the [canonical cell](./glossary.md#canonical-cell) of the
[8-slot tree](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/traits/vectors/>) (302 traits, 280 roles), shear
applied; 574 with a current file (295 + 279; 19 + 1 through `renamed_from`); 572 train.
[Orphans](./glossary.md#orphan-vector) (no file to link): conceptual, cruel, dramatic, enigmatic, mercurial,
regulatory, technical, and the role adolescent.  Sense-changed renames with a May vector: libertarian, savage.
K for 50 / 80 / 90 / 95 / 99% of the variance = **10 / 45 / 96 / 170 / 373**; the top 12 carry 55.1%; log-log slope
−1.11; λ1/λ12 = 5.8, λ1/λ32 = 19.2.

**Alpha** (5 grouped folds, 485 groups; chosen **0.3** by the rule with its tie window):

| alpha | median cos | top-1 | top-5 | best residual Spearman |
|---|---|---|---|---|
| 0.03 | 0.697 | 0.703 | 0.969 | 0.634 |
| 0.1 | 0.717 | 0.740 | 0.969 | 0.647 |
| **0.3** | **0.732** | **0.745** | **0.970** | **0.644** |
| 1 | 0.737 | 0.734 | 0.960 | 0.598 |
| 3 | 0.716 | 0.640 | 0.935 | 0.506 |

**Recovery by kind** (alpha 0.3): traits median cosine 0.751, top-1 0.737, top-5 0.966; roles 0.721, 0.753, 0.975.
For a held-out trait the nearest other entity is a role 10.6% of the time.  **kNN**: 0.568 / 0.663 / 0.675 / 0.693
at k = 1 / 3 / 5 / 10, against ridge's 0.732.  **The gloss side**: the 277 trained traits with an M1 gloss land at
0.697 from `label: M1 gloss` against 0.753 from their descriptions (the plan measured 0.695 / 0.752).

**Per-PC R²** (held-out predictions on the pool's principal components):

| PC | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R² | 0.81 | 0.80 | 0.77 | 0.76 | 0.81 | 0.71 | 0.64 | 0.65 | 0.69 | 0.68 | 0.50 | 0.65 |

| PC | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R² | 0.56 | 0.57 | 0.49 | 0.43 | 0.43 | 0.57 | 0.47 | 0.53 | 0.40 | 0.50 | 0.40 | 0.44 |

Means: PCs 25-48 0.32, 49-64 0.17.  The tail is predicted worse, not at zero, as the plan found.

**The N sweep** (residual Spearman, predicted against actual, all rows / traits): N = 12 0.644 / 0.609; 16 0.620 /
0.574; **20 0.637 / 0.617**; 24 0.626 / 0.624; 28 0.618 / 0.609; 32 0.604 / 0.585.  The best is N = 12; every N but
32 is within the 0.02 window, and **the tie rule picks N = 20** (QUESTIONS 143).

**[Shrinkage](./glossary.md#shrinkage) and the thresholds** (plan defaults, `thresholds_set_by: "plan default"`):
the held-out predicted `residual_20` has median 0.219 against the actual 0.399 (`residual_24`: 0.184 against 0.362).
`dup_threshold` = **0.732**, `novel_pct` = **0.80**; the cover-questioned cosine 0.610, novel-vs-covered 0.90.  The
evidence for decision (b) (QUESTIONS 153): at 0.732 a held-out existing entity's prediction is duplicate-like to
another entity **32%** of the time, and against M3's own concept readings (the overlap test's corpus pairs) it
catches 6 of 6 pairs read 4, 55% read 3, 12% read 2, 7% read 1, none read 0 or opposite.  A threshold of 0.80 would
bring the base rate to 10% and keep half of the pairs read 4 and 29% of those read 3.

**Gate 1 for Roger** (20 minutes): (a) N = 20, or another N of the flat curve; (b) `dup_threshold` (0.732, or
higher for a lower base rate) and `novel_pct` (0.80); (c) whether the per-PC table changes which generators to run.
To record a move: `persona_novelty.py fit --fit-id fit_<date> --dup-threshold X --novel-pct Y --N n
--thresholds-set-by "Roger, gate 1"` (a new fit id, $0).  *Roger's gate-1 notes: not yet.*

## Comparison with M3, so far only on the smoke batch ($0)

[smoke_cached36_2026-10-13](../../data/candidates/persona/score/smoke_cached36_2026-10-13/score_report.md) (36
censuses rows, no API call, no registry write): flags 5 duplicate-like, 7 novel-like, 24 ordinary; AUC of the
nearest-trait cosine for M3's 3 covered rows against its 33 new ones 0.71; M3's covering trait is the persona-nearest
trait for 1 of 2 and among the three nearest for 2 of 2.  Of 5 `dup_vs_new` rows, 3 are listed
([disagreements.md](../../data/candidates/persona/score/smoke_cached36_2026-10-13/disagreements.md)): derisive
nearest [sardonic](../../data/traits/instructions/sardonic.json) at 0.82 (M3 read
[sarcastic](../../data/traits/instructions/sarcastic.json) first), parasitic nearest
[greedy](../../data/traits/instructions/greedy.json) at 0.77, insulting nearest
[sarcastic](../../data/traits/instructions/sarcastic.json) at 0.75.  Too few rows to read anything into; it shows the
pipeline end to end on real data.  The full batch's agreement table, the flag counts by generator and the
disagreement counts by kind and generator are not there yet: they come with the paid step below
([agreement.json](../../data/candidates/persona/score/persona_2026-10-13_all/agreement.json), not there yet).

**The rendered prompt of decision 2b** (the judge's dry run on the smoke batch; M3's pinned rubric A, unchanged,
[overlap_concept.md](./rubrics/overlap_concept.md) as the cached system turn; Sonnet 5.5, `max_tokens` 2048, no
temperature):

```
[user]
{"target": {"label": "derisive", "description": "This means mocking others with scorn, treating their ideas, efforts and failings as objects to ridicule rather than to take seriously."},
 "other": {"label": "sardonic", "description": "This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge."}}
```

## The prospective set, $0

[predicted.jsonl](../../data/candidates/persona/prospective/fit_2026-10-13/predicted.jsonl) (699 rows) and
[prospective_report.md](../../data/candidates/persona/prospective/fit_2026-10-13/prospective_report.md): traits 69
duplicate-like, 252 novel-like, 318 ordinary; roles 6, 19, 35.  The most novel-looking are memberships, generations
and physical traits ([polygynous](../../data/traits/instructions/polygynous.json),
[gen-z](../../data/traits/instructions/gen_z.json), [tall](../../data/traits/instructions/tall.json)), as the seeding
intended.  The workstream plan's named pairs, predicted: [risk-averse](../../data/traits/instructions/risk_averse.json)
nearest [traditional](../../data/traits/instructions/traditional.json) (0.64), [bold](../../data/traits/instructions/bold.json)
nearest [risk-seeking](../../data/traits/instructions/risk_seeking.json) (0.69),
[overconfident](../../data/traits/instructions/overconfident.json) nearest
[arrogant](../../data/traits/instructions/arrogant.json) (0.73).  After the next extraction:

```
uv run python data_analysis/gap_generation/persona_novelty.py prospective compare --fit-id fit_2026-10-13 --new-vectors-dir '<the new extraction's model directory, holding traits/vectors and roles/vectors>'
```

It writes `compare_<tree>.json` and `.md` beside the predictions (not there yet).

## The paid steps, in order (coordinator, main checkout, after cherry-picking)

| # | command (from the repository root) | estimate |
|---|---|---|
| 0 | `uv run python data_analysis/gap_generation/persona_novelty.py fit --fit-id fit_2026-10-13` (rebuilds the git-ignored model; prints "matches the recorded model") | $0 |
| 1 | `uv run python data_analysis/gap_generation/persona_novelty.py score --batch-id persona_2026-10-13_ipip_g600 --fit-id fit_2026-10-13 --run ipip/2026-10-13-g600` (490 texts, 2 embedding calls, the canary first) | $0.002 |
| 2 | `uv run python data_analysis/gap_generation/persona_novelty.py judge-disagreements --batch-id persona_2026-10-13_ipip_g600` (at most 49 pairs) | $0.12 (projected $0.15) |
| | **Gate 2**: Roger reads the batch's [score_report.md](../../data/candidates/persona/score/persona_2026-10-13_ipip_g600/score_report.md) and [disagreements.md](../../data/candidates/persona/score/persona_2026-10-13_ipip_g600/disagreements.md) (not there yet); a bad read stops step 3 | |
| 3 | `uv run python data_analysis/gap_generation/persona_novelty.py score --batch-id persona_2026-10-13_all --fit-id fit_2026-10-13 --all-rows --write-registry` (6,735 rows, 6,699 texts to embed, 27 calls) | $0.029 |
| 4 | `uv run python data_analysis/gap_generation/persona_novelty.py judge-disagreements --batch-id persona_2026-10-13_all --write-registry --budget-usd 5` (at most 673 pairs) | $1.66 (projected $2.07; cap $5) |
| 5 | `uv run python data_analysis/gap_generation/persona_novelty.py compare --batch-id persona_2026-10-13_all`, then `report --batch-id persona_2026-10-13_all`, then `uv run python data_analysis/gap_generation/gap_registry.py compact` | $0 |

Total about $1.8 estimated, $2.25 projected, live (under the $20 line).  The registry log appends whole rows, so step 3 grows the live log by about 133 MB (6,735 rows of about 20 KB) and step 4 by about 13 MB until step 5's `compact` (QUESTIONS 159).  If gate 1 moves a threshold, steps 1-5 use
the new fit id.  Every paid command refuses uncommitted platform code without `--allow-dirty`, prints its estimate
first, and writes `usage.json` and `run.json`; the judge records every response before parsing it, counts refusals as
failed calls, and never writes the `novelty` block.

## Cost so far

Every [usage.json](../../data/candidates/persona/fit/fit_2026-10-13/usage.json) of this build records 0 calls, $0
(the fit, the prospective predictions, the smoke batch).

## Open QUESTIONS

140-159 in [QUESTIONS.md](./QUESTIONS.md), all open except 148 (the two decisions, answered).  The ones that need
Roger: **153** (the duplicate threshold, gate 1), 149 (the pending count), 150 (the alpha tie window), 151 (the role
label form), 156 (keep or drop the smoke batch).

## Interface requests (§ "Interface requests"; written, not implemented)

1. **Plan 13's dashboard** (QUESTIONS 157): a `persona` sub-object per generator read from the blocks,
   `{"scored", "duplicate_like", "novel_like", "dup_vs_new", "novel_vs_covered", "mean_residual_pct", "batch_id"}`,
   `n/a` where no batch covers the generator; `agreement.json`'s `by_generator` already computes all but the batch id.
2. **The review graph** (QUESTIONS 158): optional `persona_nearest`, `persona_flag`, `persona_residual_pct` on
   candidate nodes, from the block when present; no edge from them.
3. **The registry**: `BLOCKS` gains `"persona"`: done.
4. **M3**: nothing now; a later rule on the readings is Roger's call on the full batch.

## Proposed paragraph for [data/README.md](../../data/README.md) (not edited; the platform owns it)

Its links are written for `data/README.md`'s own directory, where they resolve.

> - **[`candidates/persona/`](candidates/persona/)** (tracked, except `*.npz`): workstream 12's persona-space
>   scorer ([`persona_novelty.py`](../data_analysis/gap_generation/persona_novelty.py)).  `fit/<fit_id>/`: the
>   cross-validation (`cv.json`), the calibration (`calibration.json`: the thresholds and who set them),
>   `fit_report.md` and `.png`, `run.json`, `usage.json`; `model.npz` is git-ignored and rebuilt by `fit` from the
>   recorded alpha.  `score/<batch_id>/`: `scores.jsonl` (one row per scored registry key: the `persona` block's
>   fields and the neighbour lists), `summary.json`, `agreement.json`, `disagreements.jsonl` and `.md`,
>   `score_report.md`, `readings.jsonl` and `responses.jsonl` (decision 2b), `run.json`, `usage.json`;
>   `predictions.npz` git-ignored.  `apply --batch-id` re-applies a batch's blocks to another checkout's registry
>   log.  `prospective/<fit_id>/`: the predictions for the entities with no vector yet, and `compare_<tree>.*` after
>   an extraction.  The JSON outputs carry the provenance envelope.

## The workstream plan's question

**How many registry candidates does persona space call duplicates that the text missed, and how many novel
directions does it see that the text called covered?**  Not answered yet: it is the full batch's `dup_vs_new` and
`novel_vs_covered` counts (step 3, $0.03).  On the 36-row smoke batch: 5 duplicate-like rows M3 called new, 0 novel
rows M3 called covered.
