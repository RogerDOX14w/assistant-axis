# Haiku 5.5 against Haiku 4.5 on the gap-filling platform (2026-10-07)

Roger, 2026-10-07: "Haiku 5.5 is out: we should run a quality and price comparison with Haiku 4.5, and
if it's as good or better, move up to it", for this subproject only (the project's other Haiku uses
are a separate decision).  Run by an Opus agent to [coding_plan_haiku55.md](./coding_plan_haiku55.md),
$2.34 in all; the per-run tables are in each run directory's `haiku55_comparison.md` (linked below),
built from the records by [haiku55_compare.py](../../data_analysis/gap_generation/haiku55_compare.py).
Terms: the [glossary](./glossary.md); the platform's three Haiku uses are the *M1 filter* (is the
word a trait; its gloss and alignment score), the *relation call* (M3's first pass over a candidate's
nearest traits: similar, opposed or unrelated) and the *overlap call* (how similar two concepts are,
0-4), which Sonnet does today with Opus as the second opinion.

**The facts** (the vendor's pages, 2026-10-07): `claude-haiku-5-5`, $0.10 / $0.50 per MTok against
4.5's $1 / $5; caches at 512 tokens (4.5: 4,096); the newer tokenizer (inputs about 1.3x); adaptive
thinking, so it writes 2-3 times 4.5's output tokens, none of it in the answer text; **it refuses a
temperature**, so it cannot be run at 0 and is not deterministic.  Code: a price row, the
no-temperature list, the tokenizer list, `KNOWN_MODELS`, and `--relation-model` / `--relation-only`
on the M3 CLI (commits dda51f0, ec759da; `overlap_test.py --corpus-at` to rebuild a pair set from an
earlier corpus, ef81ac4).  No default was changed.

## The verdict by use

| use | quality | price | recommendation |
|---|---|---|---|
| **Relation call** | better: 20 of Roger's 24 corrections right (4.5: 7); shortlists 18% shorter; recall 75 of 76 on the scan's ground truth (the miss changed no decision); unsure rate 1.0% (4.5: 0.2%) | $0.53 against $2.78 for 460 candidates, re-asks included; the shorter shortlists save about a sixth of the overlap calls too | **move up** |
| **Overlap call** (could Haiku take Sonnet's place?) | closer to Opus (79-80% against 76%) and to Roger's marks (20 against 18 of 30) than 4.5, and fewer containment slips; but self-consistency 91.7% (4.5: 100% at temperature 0; Sonnet 95%) and it under-reads 3s (9.5% of pairs at 3 or more, Opus 16%), so as the first line it would leave 27 pairs a pass that Opus reads at the cut-off unseen (Sonnet 16-17) | a tenth of Sonnet's | **no: Sonnet stays** (answers Roger's 2026-10-03 question) |
| **M1 filter** | mixed, below | about a seventh of 4.5's per word | **not yet as a whole; the gloss step yes** (below) |

## A. The M1 filter in detail

Like for like: Haiku 4.5's "92 of 99" came from the September pilot on older rubric versions; the
agent built a current-version 4.5 reference (63 words from `m1_validation_r2` plus a $0.29 run on the
other 36).  Two Haiku 5.5 runs, to measure its own noise.

| | Haiku 5.5 | Haiku 4.5 (current versions) |
|---|---|---|
| 99 test words, outcome matches the reference join | **86 and 80** of 99 (the two runs agree on 90) | **90** of 99 (live and batch pilot agreed on 93) |
| its misses | stricter: turns away traits as stretched or unreadable (disciplinary, economic, deterministic, watertight, middle, concrete); accepts some the reference turns away (decided, false, linear, unsharpened) | over-accepts (below) |
| validation pool, agreement with Sonnet 5.5 (143 random adjectives) | **79.0% / 79.7%**; disagreements balanced, 13 each way | **72.0%**; 33 passed that Sonnet turned away, 3 the reverse |
| glosses in the 18-43-word band (non-memberships) | **63 of 63**, mean 27.9 words | 15 of 63, 48 too short, mean 15.9 |
| membership glosses padded past 18 words (against the fact-wins rule) | 4 of 10 | 0 of 13 |
| alignment scores (0 / 1 / 2 / 3) | 38 / 16 / 11 / 9 | 59 / 9 / 1 / 7 |
| per word | about $0.0012 | about $0.008 |

Reading it: on the words nearest the corpus (the test words) 5.5 is a little worse and errs toward
turning traits away, which for this pipeline is the costlier direction (a turned-away trait is a lost
candidate; a passed non-trait is caught at M3 or review; Roger's bar: "a few slipping through is
fine").  On random dictionary adjectives it is closer to Sonnet than 4.5 is, but neither reaches the
plan's 90% line, so Sonnet stays the first line for that source either way.  Its glosses are the
first that meet the length rule as written, which matters for M3's retrieval (the pilot's one false
cover, earthy, came from a thin 4.5 gloss), though it pads membership glosses the way Sonnet did
before the fact-wins rule, which a line in [gloss.md](./rubrics/gloss.md) would address.  Its
alignment scores sit higher (20 of 74 at 2 or 3, against 8 of 76), which would move more candidates
to the cut-off of 4; which calibration is right is untested (Roger's 69 marked words would tell, for
about $0.05 on 5.5).  And it is not repeatable: 9 of 99 and 22 of 143 outcomes changed between its
two runs, against 4.5's live-against-batch 6 of 99.

The split filter already names a gloss model separately from the verdict model (a second-opinion
word takes its gloss from the second model), so the natural move is: **verdict steps stay on 4.5 (or
Sonnet for a hard source), the gloss moves to 5.5** after the membership line, and the alignment
rubric is checked against Roger's marks on both models before it moves.

## B. The relation call in detail

457 candidates, the same lists and order seeds as the pilot.  Per listed trait the two Haikus agree
76% (kappa 0.65); 5.5 moves 904 "similar" and 608 "opposed" answers to "unrelated", which is where the
shorter shortlists come from (5.9 traits against 7.2), and marks fewer traits similar (4.3 against 6.1
a candidate).  On the full scan's 76 ground-truth pairs it misses one (financially stable / wealthy,
Sonnet 2 / Opus 3), and wealthy still reached the shortlist through the opposite rule, so no decision
changed.  Of Roger's 24 corrections ([roger_review.json](../../data/candidates/novelty/m3_pilot_1/roger_review.json))
it gets 20 right; its four misses are all ones he marked harmless.  Unsure answers rose to 1.0% (59
candidates re-asked on Sonnet, $0.15 of the $0.53).  Tables:
[m3_pilot_1_relation_h55/haiku55_comparison.md](../../data/candidates/novelty/m3_pilot_1_relation_h55/haiku55_comparison.md).

## C. The overlap call in detail

Rubric A version 6, one pair per call, the 409 pairs, two passes, both Haikus beside Sonnet and Opus
from `overlap_arms_3` (same prompts byte for byte, the pair set rebuilt from the corpus at the test's
commit).  Tables: [overlap_arms_4/haiku55_comparison.md](../../data/candidates/overlap_test/overlap_arms_4/haiku55_comparison.md).

| | Haiku 5.5 | Haiku 4.5 | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|---|
| self-consistency, exact | 91.7% | 100% | 95.1% | 94.6% |
| against Opus, exact (pass 1 / 2) | 78.7% / 80.2% | 75.8% / 76.5% | 86.6% / 84.6% | – |
| share of pairs at 3 or more | 9.5% | 17.4% | 13.9% | 16.1% |
| Roger's 30 marks, exact | 20 / 20 | 18 / 18 | 20 / 20 | 22 / 21 |
| as M3's first line: kept though Opus reads 3+ (per pass) | 27 | 13, 11 | 16, 17 | – |
| cost per pair | $0.0002 | $0.0017 | $0.0012 | $0.0031 |

Parse rates 100% everywhere.  Haiku 5.5 reads the rubric from the cache (99% hits; 4.5 could not).

## Decisions for Roger

1. **Relation call to Haiku 5.5**: recommended; `RELATION_MODEL` in the M3 runner, the CLI's default
   and the README; the pilot's dry-run estimate also learns 5.5's token figures (the agent found the
   estimates under-state 5.5 by about 40%, thinking not being counted).
   **Roger: Yes**
2. **Overlap call stays on Sonnet first, Opus second.**
   **Roger: Yes**
3. **M1 filter**: keep 4.5 for the verdict steps for now; move the gloss step to 5.5 after a
   membership line in gloss.md; run the alignment rubric on Roger's 69 marked words on both models
   ($0.05) before deciding the alignment step.  Or, if the sevenfold saving outweighs 4-10 words in 99
   on the near-corpus pool, move the whole filter and accept the stricter verdicts; Roger's call.
4. **Not in this job**: the project's other Haiku uses (the response-mode axis judge, the steering
   effect judge, the refusal fallback, the trait-audit question judge), each its own test.

## Follow-ups on Roger's questions (2026-10-07, later the same day)

Roger asked for three more measurements: the filter against Opus; a blind taste test of the glosses
on scope alone; and blind judgement of every relation-call difference.  The first cost $0.44 of
API; the other two were Fable judges reading blinded files (the keys held in separate files they were
told not to open), each item judged twice with the two sides in opposite order, by different judges.

**1. The M1 verdict against Opus: no detectable difference between the Haikus.**  Haiku 5.5 was run
twice on the 207 words that carry Opus verdicts (the validation run's second-opinion sample, in
[h55_opus_audit_sample](../../data/candidates/filter/h55_opus_audit_sample/) and `_rep2`), beside
the recorded Haiku 4.5 and Sonnet verdicts on the same words:

| stratum (n) | Haiku 5.5, run 1 / run 2 | Haiku 4.5 | Sonnet 5.5 |
|---|---|---|---|
| corpus labels (80) | 91% / 92% | 95% | 96% |
| random adjectives (107) | 76% / 75% | 68% | 84% |
| not adopted (12) | 92% / 92% | 92% | 92% |
| physical (8) | 50% / 75% | 88% | 88% |
| all (207) | 82% / 83% | 81% | 89% |

Paired on the same words, none of the Haiku-against-Haiku differences is significant (corpus labels
4 against 7, p = 0.55; random adjectives 25 against 17, p = 0.28; all 31 against 29, p = 0.90; run 2
28 against 24, p = 0.68); Sonnet's lead over 5.5 is (27 against 11, p = 0.014).  Haiku 5.5 gave the
same verdict as its own first run on 178 of 207 words.  With the earlier rows (the 99 test words:
one run p = 0.03, the other p = 0.45; the 143 random adjectives against Sonnet, p = 0.08-0.13) the
verdict step's answer is: no quality gap these samples can detect, 5.5 noisier, 5.5 erring toward
turning traits away and 4.5 toward passing non-traits, 5.5 about a seventh of the price.

**2. The glosses, on scope alone: equal on ordinary words, 5.5 better where the corpus has a
specialised sense.**  Two batches ([h55_glosses_blind/](../../data/candidates/filter/h55_glosses_blind/)):
151 word pairs from the test and pool words (66 with a hand reference sense), and the 91 audit words
not already judged, 67 of them corpus labels judged against the corpus's own description.  The
judges flagged a gloss "misleading or wrong in scope" and named the better-scoped one, length
excluded by the brief; a flag or preference counts when both orders gave it.

| batch | flagged, both orders | one side only (paired) | preference agreed |
|---|---|---|---|
| 1: 151 words | 4.5: 2, 5.5: 2 | 1 against 1 | 4.5 better 16, 5.5 better 15, tie 99 (21 split) |
| 2: 91 audit words | **4.5: 15, 5.5: 6** | 11 against 2, p = 0.02 | 4.5 better 12, 5.5 better 19, tie 49 (11 split) |

The judges' notes say why: where the corpus's sense of a word is narrowed or specialised, 4.5's
16-word gloss gives the ordinary dictionary sense and stops (uncalculating, grandiose, body-insecure,
immature, helpless, on the fence, masculine, focused), and 5.5's longer gloss more often carries the
clause that lands the scope.  Four words were flagged on both sides in both orders, where neither
gloss could reach a sense only the corpus knows (an identity rather than a judgement, a manner rather
than an opinion).  The first-shown gloss won 53-58% of the non-ties, absorbed by the two orders.  So
the gloss step moves to 5.5 on scope as well as on length.

**3. The relation call: the judges side with Haiku 5.5 on 82% of the differences.**  All 1,810
differing answers (the five "unsure" excluded) were judged in both orders
([m3_pilot_1_relation_h55/blind/](../../data/candidates/novelty/m3_pilot_1_relation_h55/blind/)),
the judges seeing the candidate and trait descriptions and the two answers, not the models or their
reasons.  Both orders agreed on 1,625 items: **5.5 right on 1,388, 4.5 on 233**, neither on 4; 185
split between orders; the first-listed answer was chosen 49% and 53% of the time.  By kind:

| 4.5 said → 5.5 said | n | judges with 4.5 | with 5.5 | split |
|---|---|---|---|---|
| similar → unrelated | 929 | 62 | **736** | 131 |
| opposed → unrelated | 613 | 4 | **592** | 16 |
| unrelated → similar | 146 | 67 | 49 | 30 |
| unrelated → opposed | 109 | **97** | 4 | 7 |
| opposed → similar | 11 | 2 | 7 | 1 |

So 4.5's "similar" and "opposed" are loose, as Roger's review of the pilot had found (the
both-opposed pair flags), and 5.5's "unrelated" is nearly always upheld; 5.5's own weak spot is the
109 traits it newly calls "opposed", which the judges reject 97 to 4, and its new "similar" calls are
a coin toss.  On the 1,088 differences that change the shortlist (similar against not), the judges
side with 5.5 on 792 and 4.5 on 132.  This agrees with the full scan: the shorter shortlist lost no
cover.  The judges' recurring difficulty was the line between "share a core" and "the same broad
area" for a specific habit against a general disposition; several noted trait descriptions narrower
than the trait's name (observant, calculating, financially reckless), which they judged as written.

**4. The alignment step: Haiku 5.5 is the closer to Opus, and the earlier shift was mostly the
glosses.**  The "69 marked words" named above were never marked (the marks column of
[alignment_accepts_for_marks.md](./alignment_accepts_for_marks.md) is empty; Fable's error), so the
reference is Opus.  On the 69 pilot glosses that the graded rubric was tuned on (fixed inputs, rubric
version 3, [probe_alignment_graded/](./probe_alignment_graded/): `haiku55_pilot` and `_rerun`,
`sonnet55_pilot`, `opus55_pilot`, beside the Haiku 4.5 runs; $0.59):

| model | scores 0 / 1 / 2 / 3 | same side of the cut-off as Opus | exact | self-agreement |
|---|---|---|---|---|
| Haiku 4.5 (two runs) | 54 / 6 / 2 / 7 | 68 and 67 of 69 | 49, 50 | 66 of 69 |
| Haiku 5.5 (two runs) | 42 / 17 / 3 / 7 | **69 and 68 of 69** | 54, 54 | 67 of 69 |
| Sonnet 5.5 | 40 / 19 / 6 / 4 | 67 of 69 | 59 | – |
| Opus 5.5 | 41 / 18 / 5 / 5 | – | – | – |

Both Haikus put the same words on the same side of M3's cut-off as Opus; 5.5's distribution is
Opus's and Sonnet's (4.5 under-uses the score of 1).  The higher distribution seen in the filter
comparison (20 of 74 test words at 2-3 against 8) was mostly the glosses, not the scorer: Opus
scoring the same 68 test words reads 5.5's glosses at 2-3 on 12 and 4.5's on 10 (64 of 68 on the
same side; `opus_on_glosses_haiku45` and `_haiku55`, $0.83), while 5.5 inside the filter scored its
own glosses at 2-3 on 17 of those 68 and 4.5 its own on 8.  So the gloss text moves a few words across
the line, which is a property of the gloss both models will then read, and 5.5 scoring its own longer
glosses runs a little high: five words in 68 on this sample.  The alignment step moves to 5.5 with the
rest.

**5. The verdict step on 600 words, with Opus as the reference, and voting over three Haiku 5.5
readings (2026-10-08).**  Roger's test 2: 300 near-corpus words (the antonym-check pool, the pool
that resembles generator output) and 300 random dictionary adjectives, all with Haiku 4.5's verdict
on record at the current rubric versions
([haiku55_verdict_600.jsonl](../../data/candidates/validation/haiku55_verdict_600.jsonl)), run
through the whole filter on Opus 5.5 ([opus55_verdict_600](../../data/candidates/filter/opus55_verdict_600/),
$23.75, 7% over its estimate; approved by Roger at about $27) and three times on Haiku 5.5
([h55_verdict_600](../../data/candidates/filter/h55_verdict_600/), `_rep2`, `_rep3`, $0.56 each).
Errors are weighted as Roger set them the same day: a trait wrongly turned away 3 (the lost
candidate), a trait mis-tagged as physical or a role 1, a trait/states confusion 0.5 ("the boundary
is particularly permeable"), a non-trait passed 1 (0.5 when Opus calls it a state).  The rules were
scored after the runs; the two-reading rule had been proposed on the earlier sets, the three-reading
rules are Roger's idea (2026-10-08: "majority vote some decisions, take best of three or require
unanimity on others").

| rule (cost per word) | pool | agrees with Opus | passes a non-trait | turns a trait away (fully) | weighted errors | paired against 4.5 |
|---|---|---|---|---|---|---|
| Haiku 4.5, one reading ($0.008) | near-corpus | 94% | 6 | 11 (5) | 21.0 | |
| | random | 79% | 16 | 25 (13) | 82.5 | |
| | all 600 | 87% | 22 | 36 (18) | 103.5 | |
| Haiku 5.5, one reading ($0.0012) | near-corpus | 94% | 4 | 12 (4) | 19.5 | 13 / 13, p = 1.0 |
| | random | 82% | 8 | 28 (19) | 88.0 | 33 / 24, p = 0.29 |
| | all | 88% | 12 | 40 (23) | 107.5 | 46 / 37, p = 0.38 |
| Haiku 5.5, trait if either of two ($0.0024) | near-corpus | 97% | 4 | 4 (1) | 7.5 | 13 / 5, p = 0.10 |
| | random | 81% | 17 | 25 (17) | 88.0 | 32 / 28, p = 0.70 |
| | all | 89% | 21 | 29 (18) | 95.5 | 45 / 33, p = 0.21 |
| Haiku 5.5, majority of three ($0.0036) | near-corpus | 95% | 3 | 10 (3) | 16.0 | 13 / 11, p = 0.84 |
| | random | 85% | 5 | 28 (18) | 78.0 | 37 / 21, p = 0.05 |
| | all | 90% | 8 | 38 (21) | 94.0 | 50 / 32, p = 0.06 |
| **Haiku 5.5, turned away only if all three agree, else majority** ($0.0036) | near-corpus | 96% | 3 | 8 (1) | **9.0** | 14 / 9, p = 0.40 |
| | random | 83% | 16 | 24 (14) | **75.5** | 32 / 22, p = 0.22 |
| | all | 89% | 19 | 32 (15) | **84.5** | 46 / 31, p = 0.11 |
| Haiku 5.5, trait if any of three ($0.0036) | near-corpus | 96% | 5 | 4 (1) | 9.0 | 11 / 5, p = 0.21 |
| | random | 83% | 17 | 23 (14) | 74.5 | 35 / 24, p = 0.19 |
| | all | 90% | 22 | 27 (15) | 83.5 | 46 / 29, p = 0.06 |

Haiku 5.5 gave the same verdict in all three readings on 531 of 600 words.  Reading it: a single 5.5
reading is level with 4.5 overall and turns more traits fully away on random adjectives; a second
reading removes most of that on the near-corpus pool and none of it on the random one; three
readings with the asymmetric rule cut the weighted errors by about a fifth overall and by more than
half on the near-corpus pool, at under half of 4.5's price.  "Trait if any of three" scores the same
and lets more non-traits through; "majority of three" agrees with Opus most but turns the most traits
fully away, the error Roger weights highest.  The differences against 4.5 are at p = 0.06-0.2 on 600
words: a consistent direction, not a settled magnitude.  Confirmation of the two-reading rule on the
207 Opus-audit words (two readings on record): agreement 85% against 4.5's 81%, weighted errors 39.0
against 37.5, level.  Opus itself over-accepts against Roger's marks (section 1's 63 words), so
"passes a non-trait" against Opus is an undercount for every model; Roger's marks on the 133
disagreement words of this set
([haiku55_verdict_600_disagreements_for_marks.md](./haiku55_verdict_600_disagreements_for_marks.md))
would sharpen the table.

**Recommendation, final**: relation call to Haiku 5.5 (by a wide margin); gloss step to 5.5 (on
scope and on length); alignment step to 5.5 (as close to Opus as 4.5 or closer); **verdict step to
Haiku 5.5 with three readings and the asymmetric rule** (turned away only when all three readings
agree, otherwise the majority verdict), the one form of 5.5 that beats 4.5 on both pools, at
$0.0036 a word against $0.008; the overlap call stays on Sonnet.  M3 decision 16 keeps the verdict
model open for re-examination on the first real generator's output.  Spend on the whole Haiku 5.5
question: $29.64 of API, $23.75 of it the Opus reference.

## The switch, built (2026-10-08)

Roger agreed the final recommendation ("OK, agreed") and an Opus agent built it to
[coding_plan_haiku55.md](./coding_plan_haiku55.md), "The switch" (commits 167c61a, 06e44be, 2ad1799,
cd94429; M3 decision 17).  Every Haiku default of the subproject is now `claude-haiku-5-5`: the filter
(`filter.DEFAULT_MODEL`, `split_runner.DEFAULT_MODEL`), the states pass, the plain-reading check, the M2
paraphrase check, and the M3 relation call (`novelty_runner.RELATION_MODEL`); the unsure re-ask, the
second opinion and the comparison stay on Sonnet 5.5, the overlap call on Sonnet then Opus.  The
verdict step reads three times by default on Haiku 5.5 (`--readings`, 1 for any other model) and
combines them as decided: turned away only if every reading turns the word away, otherwise the most
common remaining outcome, a three-way split going to *trait* if any reading said so and otherwise to
the first reading that did not turn the word away (the agent's reading of a brief wording that would
have let a first-reading turn-away win; it is the right one); a reading that fails to parse drops out
of the vote.  Each reading is recorded with its own cache key, the row carries a `verdict_readings`
block (every reading's outcome, the vote, the winner, rescues), and a run of one reading has exactly
the old record shape.  The gloss rubric is draft 4 (version 4): the membership line.  The estimates
use Haiku 5.5's measured tokens.  `score --redecide --write-registry` and `promote-redecide` write a
re-decided run's blocks to the registry; `m3_pilot_1_r2`'s 460 blocks are written (53 grey → covered,
23 grey → new, 4 covered → new), idempotently.  Two guards came with it: a resume refuses a changed
model or reading count, and a re-decision uses its source run's relation model, since relation answers
are matched by model.

Smoke runs ($0.47): the filter on the 99 test words with the new defaults matched the reference join
on 82 of 99 (the one-reading runs: 86 and 80; the three readings alone 80, 78, 82); all three readings
agreed on 79 words; 16 words were rescued by the rule, 10 rightly by the reference, 6 not; 5 traits
fully turned away (deterministic, disciplinary, economic, illegal, watertight).  Membership glosses
under draft 4: 3 of 9 still past 18 words (median 11, was 17); the other glosses unchanged, all in
band.  The relation call on 20 pilot candidates resolved to the new default and reproduced the earlier
one-reading answers 89%.  Haiku 5.5 came to $0.0027 a word for the verdict step's three readings.
Left for later: the filter's longer rubrics could now be cached (5.5's minimum is 512 tokens); the
estimate's proportions (primary readings, same-sense checks, second opinions, unsure re-asks) still
carry 4.5's shares and over-state 5.5 by about a third; the other rubric files' "Model" header lines
still name Haiku 4.5.

## Files

Runs: [h55_split_test_words](../../data/candidates/filter/h55_split_test_words/) and `_rep2`,
[h45_split_test_words_36](../../data/candidates/filter/h45_split_test_words_36/),
[h55_m1_validation_pool](../../data/candidates/filter/h55_m1_validation_pool/) and `_rep2`,
[m3_pilot_1_relation_h55](../../data/candidates/novelty/m3_pilot_1_relation_h55/),
[overlap_arms_4](../../data/candidates/overlap_test/overlap_arms_4/); two validation files under
[data/candidates/validation/](../../data/candidates/validation/).  Spend: Haiku 5.5 $1.03, Haiku 4.5
$0.97, Sonnet $0.34.
