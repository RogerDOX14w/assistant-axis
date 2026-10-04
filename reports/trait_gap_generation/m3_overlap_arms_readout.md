# The overlap rubric arms: more graduation did not help (2026-10-04)

The experiment Roger asked for after the overlap test ([m3_overlap_test_readout.md](./m3_overlap_test_readout.md);
brief [coding_plan_overlap_arms.md](./coding_plan_overlap_arms.md)): would another step in rubric A's
1-3 range make the judgement easier for the models?  Four arms on the same 409 pairs of existing traits
as the test, Sonnet 5.5 and Opus 5.5, each arm run twice with the listed traits in a fresh random order
(so self-consistency is measured on every pair).  Run `overlap_arms_1`, every file under
[data/candidates/overlap_test/overlap_arms_1/](../../data/candidates/overlap_test/overlap_arms_1/):
2,884 calls, **$15.89** ([usage.json](../../data/candidates/overlap_test/overlap_arms_1/usage.json)), every
stage 409 of 409 parsed, 2,872 of 2,884 calls at the first attempt (the misses Sonnet's usual
self-corrections).  Tables in [tables.md](../../data/candidates/overlap_test/overlap_arms_1/tables.md),
section "The arms experiment".

| arm | rubric | what changed |
|---|---|---|
| A | [overlap_concept.md](./rubrics/overlap_concept.md), version 4 | nothing: the current rubric, the baseline |
| C | [overlap_six.md](./rubrics/overlap_six.md) | six rungs 0-5, the 2-3 region split by who adds something |
| D | [overlap_relation.md](./rubrics/overlap_relation.md) | the kind of relationship named (same / variant / contains, which is wider / overlap / neighbours / different / opposite), the score derived |
| E | [overlap_scope.md](./rubrics/overlap_scope.md) | Roger's rewrite of line 3 (scope, degree, strength or emphasis; narrowed or broadened; the reason says which) |

Arms C and D are compared on the *decision scale*, their answers mapped back to 0-4 (C: 5 to 4, 4 and
3 to 3; D: same 4, variant and contains 3, overlap 2, neighbours 1, different 0).  The cut-off is 3, the
far-from-alignment one; "nearest" is the 300 nearest-neighbour pairs, where the decision lives.

## The cross-arm table

| arm | model | self-consistency, exact | pass flips across the cut-off, nearest | Sonnet-Opus agreement, pass 1 / pass 2 | between-model crossings at the cut-off, pass 1 / pass 2 | nearest pairs covered at 3, pass 1 |
|---|---|---|---|---|---|---|
| **A** | Sonnet | 89% | 10 of 300 | **87% / 85%** | **8 / 14 of 300** | 15% |
| **A** | Opus | **92%** | **4 of 300** | | | 13% |
| C | Sonnet | 90% | 7 | 83% / 83% | 16 / 20 | 9% |
| C | Opus | 85% | 11 | | | 11% |
| D | Sonnet | 90% | 6 | 84% / 79% | 19 / 20 | 6% |
| D | Opus | 87% | 5 | | | 11% |
| E | Sonnet | 90% | 8 | 86% / 84% | 13 / 19 | 15% |
| E | Opus | 89% | 6 | | | 14% |

Every model under every arm is within one point of itself and of the other model on every numeric pair
(99-100%); the differences are all about which side of a boundary a pair falls.

## Findings

1. **The current rubric is the best of the four on every decision statistic.**  Highest agreement
   between the models (87% / 85%), fewest pairs the models put on different sides of the cut-off (8 and
   14 of 300, against 16-20 for the other arms), and the most self-consistent single reading (Opus,
   92%, 4 flips at the cut-off in 300).  No arm beat it on anything that matters to the decision.
2. **A finer or a named scale moved the cut-off instead of sharpening it.**  The share of nearest pairs
   covered at 3 fell from 15% / 13% (A) to 9% / 11% (C) and 6% / 11% (D), and the two models drifted
   apart: under D Sonnet answered "contains" for 9 pairs and Opus for 22, Sonnet preferring "overlap"
   where Opus saw containment, so the crossings doubled.  Both would need a re-tuned cut-off, and both
   agree less at it.  The one thing D did reliably is **direction**: wherever both models said
   "contains" they named the same wider trait (8 of 8, 5 of 5), and Opus repeated its direction on 19
   of 20 pairs across passes.  Naming the wider side is easy; deciding between "overlap" and "contains"
   is the hard part, under any wording.
3. **Roger's rewrite (E) changed nothing measurable.**  Consistency 90% / 89%, agreement 86% / 84%,
   covered 15% / 14%, crossings 13 / 19: the same as A within noise, slightly more crossings.  What it
   did do is make the reasons say which kind of difference a 3 is: asked, Sonnet named one (narrowed,
   broadened, stronger, milder, emphasis) in 88% of its 3s and Opus in 96-98%, against roughly 60-70%
   when not asked.  Worth keeping as a line in the reason instruction if we ever want the kinds counted;
   it does not change the scores.
4. **Half the noise is the order of the list.**  When pass 2 happened to send the same prompt again (a
   call listing one trait, or a longer list that shuffled into the same order), Sonnet gave the same
   answer 95-96% of the time and Opus 98%; when the list was reordered, 86% and 89%.  Across days, the
   same prompts in run 1 and in this run agreed 92% (Sonnet) and 95% (Opus).  So where a pair sits
   among three listed traits moves its score about one time in ten, and sampling alone about one in
   twenty.  This is the position effect AGENT_NOTES warns of for every LLM judge, and it is a lever M3
   can pull cheaply (below).
5. **The boundaries are where they were.**  Flips between passes and disagreements between models sit
   mostly at 1 / 2 (harmless: both mean keep), then at 2 / 3 (Sonnet 13 of its 45 flips under A, Opus
   4 of 34).  Opus under A is the steadiest reading at the cut-off in the whole experiment.

Housekeeping: under D, Sonnet attached a `wider` field to rows whose relation was not "contains" in 86
and 64 of its 409 rows (passes 1 and 2); the parser ignores it, as it ignores the label key, and Opus
never did it.

## What I recommend (for Roger to decide)

1. **Keep rubric A as it is** (version 4, draft 2's text) as the provisional M3 overlap rubric.  No new
   rung, no renaming.  The arms answered the question Roger asked: the scale is not short of
   graduation; the 2 / 3 line is fuzzy under every wording, and the fuzz is about one pair in twenty
   at the cut-off.
2. **Read each overlap call twice, in two list orders**, in the M3 pipeline.  It doubles the cheapest
   call (about $0.003 a pair on Sonnet) and removes half the noise.  It fits Roger's escalation rule
   with one extension: a pair is *on the line* if either of Sonnet's two readings is exactly at the
   cut-off, **or** if the two readings fall on different sides of it; those go to Opus, which keeps the
   candidate if it reads under the cut-off.  A Sonnet keep in both readings is never re-examined.  On
   this run's figures that sends about one pair in six to Opus instead of one in seven.
3. **Opus stays the second opinion.**  It is more self-consistent than Sonnet at the cut-off (4 flips
   against 10 in 300) in this run as in the test; the difference is small, but it points the same way
   every time.

Not recommended: arm D's direction judgement is tempting for the rename shortlist (it says which trait
is the wider one), but it comes with a scale the models agree on less.  If direction is ever wanted, ask
for it as a separate question on pairs already scored 3, not as part of the score.

## Files

- Run: [pairs.json](../../data/candidates/overlap_test/overlap_arms_1/pairs.json) (identical pairs to run 1),
  [responses.jsonl](../../data/candidates/overlap_test/overlap_arms_1/responses.jsonl) (every request and
  answer, with `pass`), [results.jsonl](../../data/candidates/overlap_test/overlap_arms_1/results.jsonl),
  [summary.json](../../data/candidates/overlap_test/overlap_arms_1/summary.json),
  [tables.md](../../data/candidates/overlap_test/overlap_arms_1/tables.md),
  [run.json](../../data/candidates/overlap_test/overlap_arms_1/run.json),
  [run.log](../../data/candidates/overlap_test/overlap_arms_1/run.log),
  [rendered_prompts.md](../../data/candidates/overlap_test/overlap_arms_1/rendered_prompts.md) (one
  rendered prompt per arm).
- Code: the harness ([assistant_axis/gapgen/overlap_test.py](../../assistant_axis/gapgen/overlap_test.py),
  CLI [data_analysis/gap_generation/overlap_test.py](../../data_analysis/gap_generation/overlap_test.py))
  gained rubric arms with per-rubric facts and a decision-scale mapping, `--passes`, and the arms
  analysis; the three arm rubrics are pinned as version 1 in [rubrics/versions.json](./rubrics/versions.json).
- Command: `uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_1 --models
  claude-sonnet-5-5 claude-opus-5-5 --rubrics A C D E --passes 2 --budget-usd 20`.
