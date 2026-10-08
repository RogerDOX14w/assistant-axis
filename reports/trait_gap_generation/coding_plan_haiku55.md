# Coding plan: Haiku 5.5 against Haiku 4.5 on the platform's Haiku calls (2026-10-07)

Brief for an Opus coding agent, from Fable, on Roger's instruction of 2026-10-07: "Haiku 5.5 is out:
we should run a quality and price comparison with Haiku 4.5, and if it's as good or better, move up
to it."  Runs after the M3 round-2 agent has reported (it works in the same worktree).

## Scope: the gap-filling subproject only (Roger, 2026-10-07)

Roger: "There are two separate decisions here: Haiku for this gap-filling subproject, and Haiku for
other places in the project, such as description / response judging.  Each needs to be tested
separately."  This job tests, and may later switch, only the gap-filling platform's Haiku calls: the
M1 filter (its first-line steps, gloss, kind, same-sense, alignment, descriptors, the states pass and
the plain-reading check), the M2 paraphrase check, and the M3 relation call, with comparison C
answering whether Haiku could also take the overlap call.  **Not in this job**, each its own test and
decision later: the response-mode axis judge (`axis_judge_correlation.py --judge_model`, the
`haiku_responses_*_b7_t3` cohorts and the rejudge scripts; a model change there makes new cohorts,
since caches are keyed by judge family and the judge-model drift check drops a cohort whose recorded
model differs), the steering effect judge (`steering_judges.DEFAULT_EFFECT_MODELS`), the refusal
fallback judge (`data/judge_refusal_allowlist.json`), and the question judge of
`audit_trait_instructions.py`.

## The facts (read from the model, pricing and caching pages on 2026-10-07)

- Model id `claude-haiku-5-5`, released 2026-10-07.  **$0.10 / $0.50 per MTok** for prompts up to
  100,000 tokens (Haiku 4.5: $1 / $5), cache reads $0.01, 1-hour cache write $0.20, batch half.
  Prompt caching minimum **512 tokens** (4.5: 4,096, which is why the filter never cached).
- Same tokenizer as Opus 4.7 and later: about 30% more tokens for the same text.
- Adaptive thinking, default effort `medium`; the harness sends no thinking or effort setting.
- **`temperature`, `top_p` and `top_k` must be omitted**: a non-default value returns a 400.

## Code changes first (no paid call)

1. [judge_pricing.py](../../assistant_axis/judge_pricing.py): a row for `haiku-5-5` at 0.10 / 0.50
   **before** the generic `haiku` row (matching is by fragment; the generic row would price 5.5 at
   4.5's rates); the batch factor table already halves `haiku`.  Cache reads at the standard 0.1x.
   A test.
2. [llm.py](../../assistant_axis/gapgen/llm.py): `haiku-5` in the no-temperature fragments
   (`accepts_temperature`), so requests leave it out.  A test.
3. [overlap_test.py](../../assistant_axis/gapgen/overlap_test.py): `haiku-5` in
   `NEW_TOKENIZER_FRAGMENTS`; Haiku 5.5 in `KNOWN_MODELS` with a `SHORT` name ("Haiku 5.5"); not in
   `MODELS` (the defaults stay).
4. [novelty_score.py](../../data_analysis/gap_generation/novelty_score.py): `--relation-model`
   (default the current `RELATION_MODEL`) and `--relation-only` (run stage 3 for the batch's
   candidates and stop, writing `relation.jsonl` with every answer, no overlap calls, no registry
   writes), so the relation call can be compared on a model without re-running M3.
5. The filter's `--model` and the states pass's `--model` already exist; check that `--model
   claude-haiku-5-5` reaches every Haiku call of the split (steps 1-3, gloss, kind, same_sense,
   alignment, descriptors) and that the record names the model per step.

## The three comparisons (all live; about $3 in all, caps below)

Every run writes its usage; report spend per run and per model.

**A. The M1 filter** (the use with the most calls).
- The 99 test words ([split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl))
  with `--model claude-haiku-5-5`, the rest as the pilot of 2026-09-29 (`m1_pilot`, live, which Haiku
  4.5 passed at 92 of 99 against the reference join in [split_reference/](./split_reference/)).  Cap
  $1.  Compare: outcomes against the reference (trait / state / physical / turned away), word by
  word against 4.5's recorded run, and the gloss checks (form, length band, the fact-wins rule for
  memberships).
- The validation pool's words (`m1_validation/pilot_1`, 143 words after the shared 7), where both
  Haiku 4.5's verdicts ([m1_validation](../../data/candidates/filter/m1_validation/)) and Sonnet 5.5's
  ([m3_pilot_m1_validation](../../data/candidates/filter/m3_pilot_m1_validation/)) are on record:
  `--model claude-haiku-5-5 --no-second-opinion` into a new batch id, no registry writes (use
  `--validation-file` built from those rows, with `expected` the Sonnet verdict).  Cap $1.  Compare
  5.5's disagreement with Sonnet against 4.5's (the plan's rule: Haiku is used for a source where it
  agrees with the reference about 90% of the time).

**B. The relation call.**  `novelty_score.py score --relation-only --relation-model claude-haiku-5-5
--from-batch m3_pilot_1 --batch-id m3_pilot_1_relation_h55`, the 460 pilot candidates, same lists and
order seeds as the pilot.  Cap $1 (4.5 cost $2.75; 5.5 should be about $0.35).  Compare: agreement per
listed trait with 4.5's answers; recall on the full scan's ground truth (the 76 pairs either model put
at the cut-off or above on the 100 scanned candidates: 4.5 marked all 76 similar); the 24 answers Roger
corrected ([roger_review.json](../../data/candidates/novelty/m3_pilot_1/roger_review.json),
`relation_corrections`): how many 5.5 gets right; the number of similar and opposed per candidate (the
shortlist length, which drives the overlap cost); and unsure rate and parse rate.

**C. The overlap call** (Roger, 2026-10-03: re-evaluate Haiku for it when 5.5 arrives).  Rubric A
version 6, one pair per call, the 409 pairs of `overlap_test_1`, two passes, on **both** Haiku 5.5
and Haiku 4.5 (4.5 was never run in the one-pair form, so this is the like-for-like), caching on
where the model allows: `overlap_test.py --run-id overlap_arms_4 --models claude-haiku-5-5
claude-haiku-4-5-20251001 --rubrics A --passes 2 --baseline-run overlap_test_1 --budget-usd 3`.
Compare with Sonnet and Opus under version 6 (`overlap_arms_3`, the round-3 statistics: agreement,
crossings at the cut-off, self-consistency, the known groups, Roger's 30 marks) and with each other.

## The decision rule, for Roger

Per use, "as good or better" means: A, outcomes against the reference and disagreement with Sonnet no
worse than 4.5's (92 of 99; 4.5's disagreement on the validation words); B, recall 1.0 kept on the
scan's 76 pairs and no more of Roger's 24 corrections missed, shortlist length no longer; C, agreement
with Opus and with Roger's marks no worse than 4.5's, and self-consistency no worse.  Report the
numbers with the noise (the pass-to-pass differences) beside them; Fable writes the readout and Roger
decides.  If 5.5 passes, the switch is: `DEFAULT_MODEL` in [filter.py](../../assistant_axis/gapgen/filter.py),
[split_runner.py](../../assistant_axis/gapgen/split_runner.py), [states_pass.py](../../assistant_axis/gapgen/states_pass.py),
`DEFAULT_READING_MODEL` in [plain_reading.py](../../assistant_axis/gapgen/plain_reading.py),
`PARAPHRASE_MODEL` in [calibrate_llm.py](../../assistant_axis/gapgen/calibrate_llm.py),
`RELATION_MODEL` in the M3 runner, and the CLIs' usage strings and the README; with the M1 split's
rubrics then cacheable (the long ones) and the cost tables redone.  Do not make the switch in this
job; report, and Roger decides.  Whether Haiku 5.5 could take Sonnet's place as the overlap call's
first-line model is a separate question for Roger, answered by C's numbers.

## Tests and report

Tests for the four code changes with the fake clients.  Existing suites pass; a changed expectation
is reported with its reason.  Report: the commits; the three comparisons' tables with the numbers
quoted; the rendered prompt of one call per use on Haiku 5.5, read before sending; the per-call token
and output-length figures (5.5 may think more, as Opus did in the one-pair form); spend by run and
model; anything surprising.  The constraints of [coding_plan_m3.md](./coding_plan_m3.md)'s last
section apply unchanged (file boundary, sandbox, tools, git, no rubric edits).

## The switch (Roger agreed, 2026-10-08)

Decided on the readout's final numbers ([haiku55_readout.md](./haiku55_readout.md), sections 1-5):
every Haiku call of the gap-filling subproject moves to Haiku 5.5; the overlap call stays on Sonnet
first, Opus second.  One Opus build round, in the worktree; the platform plan records it as M3
decision 17.

1. **Defaults to `claude-haiku-5-5`**: `DEFAULT_MODEL` in [filter.py](../../assistant_axis/gapgen/filter.py),
   [split_runner.py](../../assistant_axis/gapgen/split_runner.py) and [states_pass.py](../../assistant_axis/gapgen/states_pass.py);
   `DEFAULT_READING_MODEL` in [plain_reading.py](../../assistant_axis/gapgen/plain_reading.py);
   `PARAPHRASE_MODEL` in [calibrate_llm.py](../../assistant_axis/gapgen/calibrate_llm.py); `RELATION_MODEL`
   in the M3 runner (`UNSURE_MODEL` stays Sonnet 5.5; the overlap models stay); the CLIs' usage
   strings; [data_analysis/README.md](../../data_analysis/README.md).  Haiku 4.5 remains selectable by
   `--model`, and every record names its model as now.
2. **The verdict step reads three times** (Roger: "best of three ... require unanimity on others").
   New `--readings N` on the filter (default 3 when the model is Haiku 5.5, 1 otherwise): the verdict
   waves (sense, the established / vague checks, kind, same-sense) run N times per word as independent
   readings, each recorded; the word's verdict is **turned away only if every reading turns it away,
   otherwise the majority verdict of the readings**; with no majority (three different verdicts),
   `trait` if any reading says trait, else the first reading's verdict.  The gloss, alignment and
   descriptors run once, on the reading whose verdict won (the first such reading).  The second-opinion
   sample and the disagreement tripwire are unchanged and compare the combined verdict.  Cost: three
   readings at about $0.0012 each against 4.5's $0.008.  `summary.json` reports the readings'
   agreement (all three the same; the rule's rescues: words one or two readings turned away).
3. **The gloss rubric's membership line.**  Haiku 5.5 pads membership glosses (4 of 10 past 18 words
   against the fact-wins rule).  Add to [rubrics/gloss.md](./rubrics/gloss.md), after the fact-wins
   sentence, exactly: "A membership gloss is one clause and may be well under the length above; do not
   add how the person acts or feels about it."  Render a membership and a trait sample, read them, pin
   as the next version, and check on the smoke run that membership glosses stop padding.  Do not change
   any other rubric.
4. **Cost estimates learn Haiku 5.5's token figures**: per-step input and output means measured from
   `h55_split_test_words`, `h55_m1_validation_pool` and `h55_verdict_600` (output includes thinking),
   and the relation call's from `m3_pilot_1_relation_h55`; the dry run quotes them per model (the
   agent of 2026-10-07 found the estimates under-stated 5.5 by about 40%).  The tokenizer factor and
   the no-temperature list already know `haiku-5`.
5. **The registry takes the round-2 decisions**: a `--write-registry` on `score --redecide` (or a
   `promote-redecide` command) writes `m3_pilot_1_r2`'s `novelty` blocks to the registry rows,
   idempotent per (run_id, key), with the source run named in the block; run it for `m3_pilot_1_r2`.
   No API call.
6. **Tests** for 1-5 with the fake clients (the three-reading rule's every branch: unanimous turn-away,
   majority, no majority with and without a trait reading; the recorded readings; the estimate per
   model; the registry write and its idempotence).  Existing suites pass; a changed expectation is
   reported with its reason.
7. **Smoke run, live, under $1, no approval needed** (Roger: run such jobs and say so): the filter on
   the 99 test words ([split_test_words.jsonl](../../data/candidates/validation/split_test_words.jsonl))
   with the new defaults, batch id `h55_x3_split_test_words`; report the combined verdicts against the
   reference join and against the one-reading 5.5 runs, the readings' agreement, the membership gloss
   lengths, and the spend against the new estimate.  Then `novelty_score.py score --relation-only` on
   20 pilot candidates with the new relation default, to confirm the wiring (about $0.02).
8. **Report**: commits; what each default is now; the smoke figures; spend; changed expectations.  The
   constraints of [coding_plan_m3.md](./coding_plan_m3.md)'s last section apply unchanged.
