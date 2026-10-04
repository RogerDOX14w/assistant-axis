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
   agree less at it.  D's **direction** answers agreed wherever both models said "contains" (8 of 8,
   5 of 5), and Opus repeated its direction on 19 of 20 pairs across passes, but two caveats from the
   agent's report keep that from being a finding: the question "say which is the wider one" has no
   clear answer for the "something more added" case (is the wider one the plainer concept, or the one
   with more in it?), and Sonnet wrote `"wider": "target"` on 150 rows whose relation was not
   "contains" (the same copying reflex as the label key; the parser drops them), so its 12 of 16
   "target" answers on real containments may be partly the same reflex; Opus's were balanced (23
   target, 19 listed) and never stray.  Deciding between "overlap" and "contains" is the hard part
   under any wording; if direction is ever wanted it needs its own, unambiguous question.
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

Two more details from the agent's report.  Under C and D the stricter model swaps: on A Sonnet covers
more than Opus (every crossing in pass 1 was a Sonnet-only cover), on C and D Opus does (D: 17 of 19
crossings Opus-only).  And the persona-space correlation is lowest under D (0.58 / 0.59 against A's
0.66 / 0.69), with overlapping intervals.  "unsure" was never used by either model in any arm.

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

## Follow-up: Sonnet misapplies D's lines, so D gets a redraft before a verdict (Roger, 2026-10-04)

Roger, shown the anxious / neurotic crossing (both models describe neurotic as anxiety with instability
added; Sonnet says "overlap", Opus "contains"): "So Sonnet is simply disobeying rubric D?  That sounds
like a reason to try redrafting the 2 and/or 3 entries of rubric D to make the distinction clearer, not
immediately abandon it."  The records bear him out.  On the 15 nearest pairs where Opus said "contains"
or "variant" and Sonnet "overlap", most of Sonnet's reasons describe containment in D's own words and
then label it overlap: careless / sloppy ("the … work *part of* careless, but leaves out broken
deadlines"), cruel / callous ("the indifference-to-suffering *part of* cruel … cruel *adds more*"),
environmental / ecocentric ("*includes* the environmental priority but *adds* …"), and anxious /
neurotic, where the slip is visible: "neurotic adds emotional instability …, **so each has something the
other lacks**": the shared core is counted as the plainer trait's addition.  Across all of D, Sonnet's
"overlap" reasons name an addition on both sides in 28% of cases (Opus 51%).  Two or three of the 15
are defensible overlaps (agreeable / conciliatory, gluttonous / self-indulgent); the rest are the one
slip.  Under rubric A, Sonnet's 2-against-3 reasons showed the same slip, so the same clarification is
worth an arm on A's lines.

**Draft 2 of D's two lines** (the rest of [overlap_relation.md](./rubrics/overlap_relation.md) unchanged;
example words checked free of the corpus: fussy, fussy eater, proud, boastful):

> - "contains": one of the two is the other with something more: narrowed to a single domain, or with an extra behaviour, feeling or condition added. The plainer one adds nothing of its own: everything it says, the richer one says too. The plainer one is the wider; say which it is. For example, fussy and fussy eater: fussy is the wider. Or proud and boastful: boastful is proud with the telling of it added, so proud is the wider.
> - "overlap": overlapping concepts. They share a core, and each adds something the other lacks. Name what each adds; the shared core itself is not an addition. If only one of the two adds anything beyond the core, the answer is "contains", not "overlap". For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.

**The same clarification on rubric A** (arm F, a new file `overlap_concept_adds.md`, A's text with lines
2 and 3 replaced; A's own pin is untouched, since A is the production rubric):

> - 3: the same concept, differing only in scope, degree or emphasis: one may be the other narrowed to a single domain, carried further, or with something more added, and the plainer one adds nothing of its own: everything it says, the richer one says too. For example, penny-pinching and miserly: miserly is the same carefulness with money, carried further. Or proud and boastful: boastful is proud with the telling of it added.
> - 2: overlapping concepts. They share a core, and each adds something the other lacks. Name what each adds; the shared core itself is not an addition. If only one of the two adds anything beyond the core, the answer is 3, not 2. For example, studious and bookish: both are about learning from books, but studious adds diligence and bookish adds a taste for reading.

Plan, on Roger's word (he may edit the lines first): pin D's draft 2 as version 2 and F as version 1,
run both on the 409 pairs, Sonnet and Opus, two passes (about $8), and compare with A and D on the
cross-arm table.  Arms C and E are not run again.  The results go in this file.

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
