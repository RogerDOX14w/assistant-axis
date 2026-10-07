# Haiku 5.5 against Haiku 4.5: the overlap call (rubric A version 6, one pair per call)

From `haiku55_compare.py overlap`: `overlap_arms_4` (both Haikus) beside `overlap_arms_3` (Sonnet 5.5, Opus 5.5).  Passes [1, 2].

## Like for like

The same calls as the reference run: True; 409 pairs; over 1636 records matched by pair and pass, the same user turn on 1636 and the same system prompt on 1636.  Rubric versions [('A', 6)]; forms ['single'].

## all: self-consistency, pass 1 against pass 2

| model | both answered | exact | within one | kappa | exact (decision) | flips at 3 |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 409 | 91.7% | 100.0% | 0.9331 | 91.7% | 11 of 409 |
| Haiku 4.5 | 409 | 100.0% | 100.0% | 1.0 | 100.0% | 0 of 409 |
| Sonnet 5.5 | 409 | 95.1% | 100.0% | 0.9643 | 95.1% | 5 of 409 |
| Opus 5.5 | 409 | 94.6% | 100.0% | 0.9635 | 94.6% | 6 of 409 |

## all: between models, per pass (crossings: pairs on different sides of 3; then which covers alone: the reference, the other)

| pass | reference | model | both answered | exact | within one | kappa | crossings | reference covers only | model covers only |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Opus 5.5 | Haiku 5.5 | 409 | 78.7% | 99.1% | 0.8205 | 27 of 409 | 27 | 0 |
| 2 | Opus 5.5 | Haiku 5.5 | 409 | 80.2% | 99.7% | 0.8468 | 28 of 409 | 27 | 1 |
| 1 | Opus 5.5 | Haiku 4.5 | 409 | 75.8% | 98.7% | 0.821 | 31 of 409 | 13 | 18 |
| 2 | Opus 5.5 | Haiku 4.5 | 409 | 76.5% | 99.0% | 0.8303 | 27 of 409 | 11 | 16 |
| 1 | Opus 5.5 | Sonnet 5.5 | 409 | 86.6% | 100.0% | 0.9073 | 23 of 409 | 16 | 7 |
| 2 | Opus 5.5 | Sonnet 5.5 | 409 | 84.6% | 100.0% | 0.8957 | 24 of 409 | 17 | 7 |
| 1 | Sonnet 5.5 | Haiku 5.5 | 409 | 83.1% | 100.0% | 0.8618 | 22 of 409 | 20 | 2 |
| 2 | Sonnet 5.5 | Haiku 5.5 | 409 | 79.0% | 99.7% | 0.8291 | 24 of 409 | 20 | 4 |
| 1 | Sonnet 5.5 | Haiku 4.5 | 409 | 76.3% | 99.4% | 0.8169 | 30 of 409 | 8 | 22 |
| 2 | Sonnet 5.5 | Haiku 4.5 | 409 | 75.5% | 99.4% | 0.8146 | 31 of 409 | 8 | 23 |
| 1 | Sonnet 5.5 | Opus 5.5 | 409 | 86.6% | 100.0% | 0.9073 | 23 of 409 | 7 | 16 |
| 2 | Sonnet 5.5 | Opus 5.5 | 409 | 84.6% | 100.0% | 0.8957 | 24 of 409 | 7 | 17 |
| 1 | Haiku 4.5 | Haiku 5.5 | 409 | 78.2% | 98.7% | 0.8038 | 34 of 409 | 33 | 1 |
| 2 | Haiku 4.5 | Haiku 5.5 | 409 | 75.3% | 98.7% | 0.7747 | 37 of 409 | 34 | 3 |
| 1 | Haiku 4.5 | Sonnet 5.5 | 409 | 76.3% | 99.4% | 0.8169 | 30 of 409 | 22 | 8 |
| 2 | Haiku 4.5 | Sonnet 5.5 | 409 | 75.5% | 99.4% | 0.8146 | 31 of 409 | 23 | 8 |
| 1 | Haiku 4.5 | Opus 5.5 | 409 | 75.8% | 98.7% | 0.821 | 31 of 409 | 18 | 13 |
| 2 | Haiku 4.5 | Opus 5.5 | 409 | 76.5% | 99.0% | 0.8303 | 27 of 409 | 16 | 11 |

## all: at 3 or more, per pass

| model | pass 1 | pass 2 |
|---|---|---|
| Haiku 5.5 | 39 of 409 (9.5%) | 40 of 409 (9.8%) |
| Haiku 4.5 | 71 of 409 (17.4%) | 71 of 409 (17.4%) |
| Sonnet 5.5 | 57 of 409 (13.9%) | 56 of 409 (13.7%) |
| Opus 5.5 | 66 of 409 (16.1%) | 66 of 409 (16.1%) |

## all: known groups (mean / share at 3+ / share opposite, per pass)

| model | pass | nearest | drop_or_merge | deliberate_duplicate | duplicate | near_distinct | antonym | random |
|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 1 | 1.97 / 10.9% / 14.3% | 3.0 / 80.0% / 9.1% | 2.0 / 0.0% / 0.0% | 3.0 / 100.0% / 0.0% | 1.46 / 7.7% / 23.5% | None / – / 100.0% | 0.18 / 0.0% / 6.7% |
| Haiku 5.5 | 2 | 1.96 / 10.9% / 14.3% | 3.0 / 90.0% / 9.1% | 2.0 / 0.0% / 0.0% | 3.0 / 100.0% / 0.0% | 1.65 / 8.7% / 32.4% | None / – / 100.0% | 0.2 / 0.0% / 0.0% |
| Haiku 4.5 | 1 | 2.09 / 21.8% / 16.0% | 3.2 / 90.0% / 9.1% | 2.67 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.95 / 25.0% / 41.2% | None / – / 100.0% | 0.19 / 0.0% / 10.0% |
| Haiku 4.5 | 2 | 2.09 / 21.8% / 16.0% | 3.2 / 90.0% / 9.1% | 2.67 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.95 / 25.0% / 41.2% | None / – / 100.0% | 0.19 / 0.0% / 10.0% |
| Sonnet 5.5 | 1 | 1.92 / 15.6% / 14.7% | 3.2 / 100.0% / 9.1% | 2.33 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.54 / 19.2% / 23.5% | None / – / 100.0% | 0.17 / 0.0% / 3.3% |
| Sonnet 5.5 | 2 | 1.89 / 15.2% / 14.7% | 3.3 / 100.0% / 9.1% | 2.33 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.64 / 20.0% / 26.5% | None / – / 100.0% | 0.14 / 0.0% / 3.3% |
| Opus 5.5 | 1 | 1.93 / 19.8% / 14.0% | 3.3 / 100.0% / 9.1% | 2.33 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.54 / 11.5% / 23.5% | None / – / 100.0% | 0.13 / 0.0% / 0.0% |
| Opus 5.5 | 2 | 1.95 / 20.2% / 14.0% | 3.2 / 90.0% / 9.1% | 2.33 / 33.3% / 0.0% | 3.0 / 100.0% / 0.0% | 1.46 / 11.5% / 23.5% | None / – / 100.0% | 0.13 / 0.0% / 0.0% |

## all: slips, pooled (2s with a containment reason; 3s with a two-sided reason; 3s stating line 2)

| model | 2s | containment | 3s | two-sided | line 2's words |
|---|---|---|---|---|---|
| Haiku 5.5 | 428 | 40 (9.3%) | 67 | 5 (7.5%) | 0 (0.0%) |
| Haiku 4.5 | 364 | 54 (14.8%) | 124 | 2 (1.6%) | 0 (0.0%) |
| Sonnet 5.5 | 329 | 25 (7.6%) | 99 | 26 (26.3%) | 9 (9.1%) |
| Opus 5.5 | 309 | 12 (3.9%) | 112 | 8 (7.1%) | 0 (0.0%) |

## nearest: self-consistency, pass 1 against pass 2

| model | both answered | exact | within one | kappa | exact (decision) | flips at 3 |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 300 | 91.7% | 100.0% | 0.8583 | 91.7% | 10 of 300 |
| Haiku 4.5 | 300 | 100.0% | 100.0% | 1.0 | 100.0% | 0 of 300 |
| Sonnet 5.5 | 300 | 94.7% | 100.0% | 0.9368 | 94.7% | 5 of 300 |
| Opus 5.5 | 300 | 93.7% | 100.0% | 0.939 | 93.7% | 5 of 300 |

## nearest: between models, per pass (crossings: pairs on different sides of 3; then which covers alone: the reference, the other)

| pass | reference | model | both answered | exact | within one | kappa | crossings | reference covers only | model covers only |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Opus 5.5 | Haiku 5.5 | 300 | 76.7% | 98.8% | 0.679 | 23 of 300 | 23 | 0 |
| 2 | Opus 5.5 | Haiku 5.5 | 300 | 77.3% | 99.6% | 0.7122 | 26 of 300 | 25 | 1 |
| 1 | Opus 5.5 | Haiku 4.5 | 300 | 73.7% | 98.4% | 0.6884 | 28 of 300 | 12 | 16 |
| 2 | Opus 5.5 | Haiku 4.5 | 300 | 74.3% | 98.8% | 0.7003 | 25 of 300 | 11 | 14 |
| 1 | Opus 5.5 | Sonnet 5.5 | 300 | 84.7% | 100.0% | 0.8415 | 21 of 300 | 16 | 5 |
| 2 | Opus 5.5 | Sonnet 5.5 | 300 | 81.7% | 100.0% | 0.8139 | 21 of 300 | 17 | 4 |
| 1 | Sonnet 5.5 | Haiku 5.5 | 300 | 81.0% | 100.0% | 0.7293 | 16 of 300 | 14 | 2 |
| 2 | Sonnet 5.5 | Haiku 5.5 | 300 | 77.0% | 99.6% | 0.6819 | 19 of 300 | 15 | 4 |
| 1 | Sonnet 5.5 | Haiku 4.5 | 300 | 74.3% | 99.2% | 0.6707 | 27 of 300 | 6 | 21 |
| 2 | Sonnet 5.5 | Haiku 4.5 | 300 | 73.0% | 99.2% | 0.6724 | 28 of 300 | 6 | 22 |
| 1 | Sonnet 5.5 | Opus 5.5 | 300 | 84.7% | 100.0% | 0.8415 | 21 of 300 | 5 | 16 |
| 2 | Sonnet 5.5 | Opus 5.5 | 300 | 81.7% | 100.0% | 0.8139 | 21 of 300 | 4 | 17 |
| 1 | Haiku 4.5 | Haiku 5.5 | 300 | 78.0% | 99.2% | 0.6639 | 29 of 300 | 28 | 1 |
| 2 | Haiku 4.5 | Haiku 5.5 | 300 | 73.3% | 98.8% | 0.5893 | 33 of 300 | 30 | 3 |
| 1 | Haiku 4.5 | Sonnet 5.5 | 300 | 74.3% | 99.2% | 0.6707 | 27 of 300 | 21 | 6 |
| 2 | Haiku 4.5 | Sonnet 5.5 | 300 | 73.0% | 99.2% | 0.6724 | 28 of 300 | 22 | 6 |
| 1 | Haiku 4.5 | Opus 5.5 | 300 | 73.7% | 98.4% | 0.6884 | 28 of 300 | 16 | 12 |
| 2 | Haiku 4.5 | Opus 5.5 | 300 | 74.3% | 98.8% | 0.7003 | 25 of 300 | 14 | 11 |

## nearest: at 3 or more, per pass

| model | pass 1 | pass 2 |
|---|---|---|
| Haiku 5.5 | 28 of 300 (9.3%) | 28 of 300 (9.3%) |
| Haiku 4.5 | 55 of 300 (18.3%) | 55 of 300 (18.3%) |
| Sonnet 5.5 | 40 of 300 (13.3%) | 39 of 300 (13.0%) |
| Opus 5.5 | 51 of 300 (17.0%) | 52 of 300 (17.3%) |

## nearest: known groups (mean / share at 3+ / share opposite, per pass)

| model | pass | nearest | drop_or_merge | deliberate_duplicate | duplicate | near_distinct | antonym | random |
|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 1 | 1.97 / 10.9% / 14.3% | – | – | – | – | – | – |
| Haiku 5.5 | 2 | 1.96 / 10.9% / 14.3% | – | – | – | – | – | – |
| Haiku 4.5 | 1 | 2.09 / 21.8% / 16.0% | – | – | – | – | – | – |
| Haiku 4.5 | 2 | 2.09 / 21.8% / 16.0% | – | – | – | – | – | – |
| Sonnet 5.5 | 1 | 1.92 / 15.6% / 14.7% | – | – | – | – | – | – |
| Sonnet 5.5 | 2 | 1.89 / 15.2% / 14.7% | – | – | – | – | – | – |
| Opus 5.5 | 1 | 1.93 / 19.8% / 14.0% | – | – | – | – | – | – |
| Opus 5.5 | 2 | 1.95 / 20.2% / 14.0% | – | – | – | – | – | – |

## nearest: slips, pooled (2s with a containment reason; 3s with a two-sided reason; 3s stating line 2)

| model | 2s | containment | 3s | two-sided | line 2's words |
|---|---|---|---|---|---|
| Haiku 5.5 | 388 | 34 (8.8%) | 49 | 5 (10.2%) | 0 (0.0%) |
| Haiku 4.5 | 334 | 50 (15.0%) | 100 | 2 (2.0%) | 0 (0.0%) |
| Sonnet 5.5 | 308 | 22 (7.1%) | 72 | 22 (30.6%) | 8 (11.1%) |
| Opus 5.5 | 284 | 7 (2.5%) | 91 | 8 (8.8%) | 0 (0.0%) |

## Roger's 30 marks

| pass | model | items | exact | within one (numeric) | his leaning or his alternative |
|---|---|---|---|---|---|
| pass1 | Haiku 5.5 | 30 | 20 | 23 of 23 | 23 |
| pass1 | Haiku 4.5 | 30 | 18 | 20 of 21 | 20 |
| pass1 | Sonnet 5.5 | 30 | 20 | 23 of 23 | 23 |
| pass1 | Opus 5.5 | 30 | 22 | 23 of 23 | 25 |
| pass2 | Haiku 5.5 | 30 | 20 | 23 of 23 | 22 |
| pass2 | Haiku 4.5 | 30 | 18 | 20 of 21 | 20 |
| pass2 | Sonnet 5.5 | 30 | 20 | 23 of 23 | 23 |
| pass2 | Opus 5.5 | 30 | 21 | 23 of 23 | 24 |

## M3's rule with each model as the first line (Opus 5.5 second), per pass

| first line | pass | decided | escalated | rescued | cut | of which directly | kept though Opus reads 3+ | decision differs from Sonnet first (keep to cut / cut to keep) |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 409 | 51 | 7 | 50 | 6 | 16 | – |
| Sonnet 5.5 | 2 | 409 | 48 | 7 | 49 | 8 | 17 | – |
| Sonnet 5.5 | flips between passes | 409 | | | | | | 7 |
| Haiku 5.5 | 1 | 409 | 33 | 0 | 39 | 6 | 27 | 15 of 409 (2 / 13) |
| Haiku 5.5 | 2 | 409 | 34 | 1 | 39 | 6 | 27 | 16 of 409 (3 / 13) |
| Haiku 5.5 | flips between passes | 409 | | | | | | 10 |
| Haiku 4.5 | 1 | 409 | 62 | 18 | 53 | 9 | 13 | 11 of 409 (7 / 4) |
| Haiku 4.5 | 2 | 409 | 62 | 16 | 55 | 9 | 11 | 12 of 409 (9 / 3) |
| Haiku 4.5 | flips between passes | 409 | | | | | | 4 |

## Parse rates (Haikus)

| model, pass | first attempt | in the end |
|---|---|---|
| Haiku 5.5|1 | 409 / 409 | 409 / 409 |
| Haiku 4.5|1 | 409 / 409 | 409 / 409 |
| Haiku 5.5|2 | 409 / 409 | 409 / 409 |
| Haiku 4.5|2 | 409 / 409 | 409 / 409 |

## The calls (every answered request, re-asks included)

| model | calls | stop reasons | input tokens (uncached) mean | cache reads mean | output tokens: mean / median / p90 / max | answer characters mean |
|---|---|---|---|---|---|---|
| Haiku 5.5 | 818 | {"end_turn": 818} | 156.5 | 568.4 | 140.6 / 94.0 / 304.30000000000007 / 576.0 | 263.0 |
| Haiku 4.5 | 818 | {"end_turn": 818} | 551.1 | 0.0 | 56.0 / 56.0 / 68.30000000000007 / 95.0 | 270.2 |
| Sonnet 5.5 | 818 | {"end_turn": 818} | 156.5 | 569.1 | 78.3 / 79.0 / 92.0 / 121.0 | 231.5 |
| Opus 5.5 | 818 | {"end_turn": 818} | 156.5 | 568.4 | 112.4 / 77.0 / 233.0 / 452.0 | 210.5 |

## The cache and the spend (as charged)

| model | requests | reading | writing | read share | charged | uncached |
|---|---|---|---|---|---|---|
| Haiku 4.5 | 818 | 0 | 0 | 0.0% | $0.6800 | $0.6800 |
| Haiku 5.5 | 818 | 810 | 8 | 77.8% | $0.0755 | $0.1173 |
| Opus 5.5 | 818 | 810 | 8 | 77.8% | $2.5601 | $4.2293 |
| Sonnet 5.5 | 818 | 811 | 7 | 77.9% | $0.9995 | $1.8354 |

## Answers

| model, pass | answers |
|---|---|
| Haiku 5.5|1 | {"0": 36, "1": 35, "2": 215, "3": 33, "4": 6, "opposite": 84} |
| Haiku 4.5|1 | {"0": 32, "1": 28, "2": 182, "3": 62, "4": 9, "opposite": 96} |
| Sonnet 5.5|1 | {"0": 35, "1": 65, "2": 168, "3": 51, "4": 6, "opposite": 84} |
| Opus 5.5|1 | {"0": 37, "1": 72, "2": 153, "3": 56, "4": 10, "opposite": 81} |
| Haiku 5.5|2 | {"0": 35, "1": 36, "2": 213, "3": 34, "4": 6, "opposite": 85} |
| Haiku 4.5|2 | {"0": 32, "1": 28, "2": 182, "3": 62, "4": 9, "opposite": 96} |
| Sonnet 5.5|2 | {"0": 34, "1": 73, "2": 161, "3": 48, "4": 8, "opposite": 85} |
| Opus 5.5|2 | {"0": 38, "1": 68, "2": 156, "3": 56, "4": 10, "opposite": 81} |
