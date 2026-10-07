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
2. **Overlap call stays on Sonnet first, Opus second.**
3. **M1 filter**: keep 4.5 for the verdict steps for now; move the gloss step to 5.5 after a
   membership line in gloss.md; run the alignment rubric on Roger's 69 marked words on both models
   ($0.05) before deciding the alignment step.  Or, if the sevenfold saving outweighs 4-10 words in 99
   on the near-corpus pool, move the whole filter and accept the stricter verdicts; Roger's call.
4. **Not in this job**: the project's other Haiku uses (the response-mode axis judge, the steering
   effect judge, the refusal fallback, the trait-audit question judge), each its own test.

## Files

Runs: [h55_split_test_words](../../data/candidates/filter/h55_split_test_words/) and `_rep2`,
[h45_split_test_words_36](../../data/candidates/filter/h45_split_test_words_36/),
[h55_m1_validation_pool](../../data/candidates/filter/h55_m1_validation_pool/) and `_rep2`,
[m3_pilot_1_relation_h55](../../data/candidates/novelty/m3_pilot_1_relation_h55/),
[overlap_arms_4](../../data/candidates/overlap_test/overlap_arms_4/); two validation files under
[data/candidates/validation/](../../data/candidates/validation/).  Spend: Haiku 5.5 $1.03, Haiku 4.5
$0.97, Sonnet $0.34.
