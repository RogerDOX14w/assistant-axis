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

Roger then widened this to all four forms (A2, C2, D2, E2), run first on the pairs where the confusion
had been seen, and delegated the iteration ("a hill-climbing exercise in prompt engineering").  The
lines actually run use the one-way implication test rather than the "adds" wording above; they are in
the brief's "Round 2" section and in the four files `rubrics/overlap_*_implies.md`.

## Round 2: the implication wording on the confusion subset (2026-10-04, `overlap_arms_2`)

Setup: 123 pairs (87 with both a 2 and a 3 among their 22 readings so far, 36 more with an "overlap"
answer whose reason describes containment), sent as the 84 round-1 calls that contain them (242 pairs
in all, 119 of them controls), four arms, Sonnet and Opus, two passes, 1,348 calls, **$8.89**
([usage.json](../../data/candidates/overlap_test/overlap_arms_2/usage.json); the 84 calls carry more
listed traits than average, so the $7 estimate was low).  Each arm is compared with its round-1
counterpart on the same pairs ([tables.md](../../data/candidates/overlap_test/overlap_arms_2/tables.md),
section "Round 2").  **No arm improved on its counterpart**: between-model crossings at the cut-off rose
under every arm, on the subset and on all pairs sent.

| arm (subset, 123 pairs) | crossings at 3, both passes | self-consistency Sonnet / Opus | nearest share at 3+, Sonnet / Opus (pass 1) |
|---|---|---|---|
| A → A2 | 29 → 39 | 83% → 89% / 88% → 86% | 32% → 40% / 25% → 28% |
| C → C2 | 40 → 49 | 86% → 80% / 76% → 88% | 15% → 29% / 20% → 31% |
| D → D2 | 41 → 44 | 89% → 76% / 85% → 73% | 6% → 19% / 18% → 32% |
| E → E2 | 37 → 47 | 89% → 84% / 85% → 85% | 30% → 48% / 29% → 36% |

Two things qualify the headline without reversing it.  The subset was chosen on round 1's own
disagreements, so round 1's crossing counts on it are inflated and a fair fresh baseline would be
lower, which makes round 2's rise larger, not smaller.  And the slip the redraft aimed at did shrink:
counted by the round-1 patterns the self-contradictions barely moved, but those patterns do not know
the new "neither implies the other" wording the lines put into the models' mouths; discounting reasons
that use it, the 2-with-a-containment-reason count roughly halved (A: Sonnet 35 → 16, Opus 20 → 5;
D: 35 → 19, 11 → 1).  So the test was taken up, and the models still ended up on different sides more
often.  Coverage at 3 rose for both models under every arm, but on different pairs.

**What the reasons show** (the agent quoted the first six slips and crossings per arm; read in full):

1. **"Scope" lets a sibling domain pass as containment.**  Under A2 and E2 Sonnet now scores 3 on pairs
   that are the same pattern in a different domain: clannish / cliqueish ("same in-group loyalty, the
   group being a social circle rather than family, so the scope differs"), clannish / insular, calm /
   temperate.  Opus applies the test and says 2 ("neither implies the other").  These are members of
   the moral-circle sequence, distinct corpus traits by design; Opus is right, and the words that
   mislead are "scope" in A's line 3 and "narrowed or broadened" in E's.  A sub-domain is containment
   (fussy contains fussy eater); a sister domain is not (fussy eater and fussy dresser).
2. **"Lacks" survives in line 2 and Sonnet still uses it.**  Under D2 Opus applies the test ("every
   accommodating person is agreeable but not the reverse": contains) while Sonnet counts the broader
   trait's other facets as things the narrower one lacks ("agreeable also covers seeking common
   ground") and answers overlap: anxious / neurotic, careless / sloppy, agreeable / accommodating.
   The closing clause of line 2, "each adds something the other lacks", was kept from round 1 and
   invites exactly this.
3. **The two-sided-but-small cases stay fuzzy under any wording**: benevolent / altruistic, big-picture /
   holistic, analytical / reductionist, compassionate / empathetic (Sonnet "nearly the same, a shift of
   emphasis", Opus "each adds something").  Partial implication both ways; no test settles them.
4. **D2 destabilised both models** (flips 13 → 30; consistency 89% → 76% and 85% → 73%), and C2 helped
   neither; the relation and six-rung forms are dropped from the climb.

Housekeeping from the run: the guard stopped once (Sonnet left `"id"` out of every row of one call,
twice; the resume re-asked only that call); the example words proud and boastful are free of the corpus
but sit on the hygiene test's reserved list (the M1 probe words), recorded as such in the test, so a
wording taken into production needs other examples.

### Scored under the rule M3 will use (Roger's question, 2026-10-04)

Crossings count both models' errors alike, but Roger's escalation rule does not: Sonnet reads every
pair, a Sonnet 3 goes to Opus (which can rescue), a Sonnet 2 is final.  So a Sonnet over-call of 3
costs one escalation and nothing else, while a Sonnet 2 on a pair Opus would cut is a near-duplicate
let through.  Each arm simulated under the rule on the 242 pairs of the 84 calls (both rounds, same
pairs; pass 1 / pass 2):

| arm | escalated (Sonnet = 3) | rescued by Opus | cut | kept though Opus ≥ 3 | rule's decision differs between the passes |
|---|---|---|---|---|---|
| A | 45 / 40 | 10 / 11 | 37 / 31 | 1 / 7 | 10 |
| A2 | 55 / 52 | 20 / 13 | 37 / 42 | 4 / 3 | 7 |
| E | 42 / 44 | 8 / 12 | 36 / 34 | 7 / 10 | 8 |
| E2 | 64 / 59 | 20 / 18 | 47 / 43 | 4 / 7 | 8 |
| C | 24 / 23 | 7 / 6 | 19 / 19 | 12 / 15 | 8 |
| C2 | 41 / 45 | 11 / 13 | 32 / 35 | 13 / 12 | 7 |
| D | 12 / 11 | 2 / 3 | 12 / 10 | 17 / 19 | 4 |
| D2 | 27 / 29 | 3 / 3 | 27 / 28 | 20 / 18 | 15 |

Read this way the climb has converged.  A and A2 are the same within noise: A2 buys three fewer
decision flips in 242 (7 against 10) with about a quarter more escalations (55 against 45) and the
same handful of pairs kept against Opus's view (3-4 against 1-7).  E2 is A2 with more escalations.  The
six-rung and relation forms are worse under the rule in both rounds, because Sonnet seldom reaches
their containment rung, so it keeps what Opus would cut (12-20 pairs).  The wording question does not
move the decisions the pipeline will make; the rule and the second reading do.

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
