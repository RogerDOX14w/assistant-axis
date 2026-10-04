# Overlap test: tables

242 pairs in 84 calls.  The run sent only these calls, named in `data/candidates/overlap_test/overlap_arms_2/subset.json`, of the pair set's 180 calls (409 pairs); every table below is about the calls sent.  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A2 | Opus 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| A2 | Sonnet 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| C2 | Opus 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| C2 | Sonnet 5.5 | 242 / 242 | 1.0000 | 239 / 242 (0.9876) |
| D2 | Opus 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| D2 | Sonnet 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| E2 | Opus 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |
| E2 | Sonnet 5.5 | 242 / 242 | 1.0000 | 242 / 242 (1.0000) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).  Rubric C2 on its own 0-5 scale; rubric D2's relations as ranks, different 0, neighbours 1, overlap 2, contains 3, variant 4, same 5 (C's rungs).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|
| A2 | Sonnet 5.5 | 242 | 80% | 212 | 78% | 100% | 0.06 | 0.83 (0.74) |
| C2 | Sonnet 5.5 | 242 | 77% | 212 | 75% | 94% | 0.02 | 0.80 (0.71) |
| D2 | Sonnet 5.5 | 242 | 75% | 212 | 73% | 97% | -0.01 | 0.78 (0.68) |
| E2 | Sonnet 5.5 | 242 | 84% | 212 | 83% | 99% | 0.08 | 0.84 (0.79) |

Categorical answers against the reference (rows: reference; columns: model):

- rubric A2, Sonnet 5.5: numeric: numeric 212, opposite 3; opposite: opposite 27
- rubric C2, Sonnet 5.5: numeric: numeric 212, opposite 3; opposite: opposite 27
- rubric D2, Sonnet 5.5: numeric: numeric 212, opposite 3; opposite: opposite 27
- rubric E2, Sonnet 5.5: numeric: numeric 212, opposite 3; opposite: opposite 27

## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A2 | Sonnet 5.5 | persona | 0.59 [0.46, 0.69] (n 162) | 0.59 [0.46, 0.69] (n 162) | 0.57 [0.44, 0.68] (n 148) | 0.57 [0.44, 0.68] (n 148) |
| A2 | Sonnet 5.5 | embedding | 0.53 [0.42, 0.63] (n 212) | 0.53 [0.42, 0.63] (n 212) | 0.52 [0.41, 0.62] (n 192) | 0.52 [0.41, 0.62] (n 192) |
| A2 | Opus 5.5 | persona | 0.57 [0.43, 0.68] (n 165) | 0.57 [0.43, 0.68] (n 165) | 0.55 [0.41, 0.67] (n 150) | 0.55 [0.41, 0.67] (n 150) |
| A2 | Opus 5.5 | embedding | 0.53 [0.40, 0.63] (n 215) | 0.53 [0.40, 0.63] (n 215) | 0.52 [0.38, 0.63] (n 194) | 0.52 [0.38, 0.63] (n 194) |
| C2 | Sonnet 5.5 | persona | 0.60 [0.46, 0.71] (n 162) | 0.60 [0.46, 0.71] (n 162) | 0.58 [0.44, 0.70] (n 148) | 0.58 [0.44, 0.70] (n 148) |
| C2 | Sonnet 5.5 | embedding | 0.54 [0.42, 0.64] (n 212) | 0.54 [0.42, 0.64] (n 212) | 0.50 [0.39, 0.61] (n 192) | 0.50 [0.39, 0.61] (n 192) |
| C2 | Opus 5.5 | persona | 0.56 [0.41, 0.68] (n 165) | 0.56 [0.41, 0.68] (n 165) | 0.54 [0.39, 0.66] (n 150) | 0.54 [0.39, 0.66] (n 150) |
| C2 | Opus 5.5 | embedding | 0.53 [0.41, 0.63] (n 215) | 0.53 [0.41, 0.63] (n 215) | 0.51 [0.38, 0.62] (n 194) | 0.51 [0.38, 0.62] (n 194) |
| D2 | Sonnet 5.5 | persona | 0.49 [0.35, 0.61] (n 162) | 0.49 [0.35, 0.61] (n 162) | 0.46 [0.31, 0.60] (n 148) | 0.46 [0.31, 0.60] (n 148) |
| D2 | Sonnet 5.5 | embedding | 0.47 [0.35, 0.57] (n 212) | 0.47 [0.35, 0.57] (n 212) | 0.44 [0.29, 0.57] (n 192) | 0.44 [0.29, 0.57] (n 192) |
| D2 | Opus 5.5 | persona | 0.52 [0.37, 0.64] (n 165) | 0.52 [0.37, 0.64] (n 165) | 0.51 [0.36, 0.63] (n 150) | 0.51 [0.36, 0.63] (n 150) |
| D2 | Opus 5.5 | embedding | 0.46 [0.32, 0.59] (n 215) | 0.46 [0.32, 0.59] (n 215) | 0.46 [0.31, 0.58] (n 194) | 0.46 [0.31, 0.58] (n 194) |
| E2 | Sonnet 5.5 | persona | 0.62 [0.49, 0.72] (n 162) | 0.62 [0.49, 0.72] (n 162) | 0.60 [0.47, 0.70] (n 148) | 0.60 [0.47, 0.70] (n 148) |
| E2 | Sonnet 5.5 | embedding | 0.53 [0.41, 0.63] (n 212) | 0.53 [0.41, 0.63] (n 212) | 0.51 [0.40, 0.60] (n 192) | 0.51 [0.40, 0.60] (n 192) |
| E2 | Opus 5.5 | persona | 0.61 [0.47, 0.71] (n 165) | 0.61 [0.47, 0.71] (n 165) | 0.60 [0.46, 0.71] (n 150) | 0.60 [0.46, 0.71] (n 150) |
| E2 | Opus 5.5 | embedding | 0.55 [0.43, 0.64] (n 215) | 0.55 [0.43, 0.64] (n 215) | 0.55 [0.44, 0.64] (n 194) | 0.55 [0.44, 0.64] (n 194) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|

## Known groups, rubric A2

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 219 | 1.95 / 25% / 12% / 0% | 1.89 / 18% / 11% / 0% |
| drop_or_merge | 5 | 2.80 / 80% / 0% / 0% | 2.80 / 60% / 0% / 0% |
| deliberate_duplicate | 2 | 2.50 / 50% / 0% / 0% | 2.50 / 50% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 14 | 2.00 / 27% / 21% / 0% | 1.75 / 8% / 14% / 0% |
| antonym | 0 | – / – / – / – | – / – / – / – |
| random | 1 | 0.00 / 0% / 0% / 0% | 0.00 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 5, 1 50, 2 104, 3 31, 4 4, opposite 25
- drop_or_merge: 2 2, 3 2, 4 1
- deliberate_duplicate: 2 1, 3 1
- duplicate: 3 1
- near_distinct: 1 5, 2 6, 4 1, opposite 2
- antonym: 
- random: 0 1

## Known groups, rubric C2

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column. On the decision scale (rubric A's 0-4; C2: 5 -> 4, 4 -> 3, 3 -> 3).

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 219 | 1.89 / 19% / 12% / 0% | 1.91 / 20% / 11% / 0% |
| drop_or_merge | 5 | 2.80 / 80% / 0% / 0% | 2.80 / 60% / 0% / 0% |
| deliberate_duplicate | 2 | 2.00 / 0% / 0% / 0% | 2.50 / 50% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 14 | 1.91 / 18% / 21% / 0% | 1.75 / 8% / 14% / 0% |
| antonym | 0 | – / – / – / – | – / – / – / – |
| random | 1 | 0.00 / 0% / 0% / 0% | 0.00 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 4, 1 52, 2 99, 3 36, 4 3, opposite 25
- drop_or_merge: 2 2, 3 2, 4 1
- deliberate_duplicate: 2 1, 3 1
- duplicate: 3 1
- near_distinct: 1 5, 2 6, 4 1, opposite 2
- antonym: 
- random: 0 1

## Known groups, rubric D2

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column. On the decision scale (rubric A's 0-4; D2: same 4, variant 3, contains 3, overlap 2, neighbours 1, different 0).

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 219 | 1.81 / 13% / 12% / 0% | 1.82 / 21% / 11% / 0% |
| drop_or_merge | 5 | 2.40 / 40% / 0% / 0% | 2.60 / 60% / 0% / 0% |
| deliberate_duplicate | 2 | 2.00 / 0% / 0% / 0% | 2.50 / 50% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 14 | 1.91 / 18% / 21% / 0% | 1.58 / 8% / 14% / 0% |
| antonym | 0 | – / – / – / – | – / – / – / – |
| random | 1 | 0.00 / 0% / 0% / 0% | 0.00 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 6, 1 65, 2 83, 3 37, 4 3, opposite 25
- drop_or_merge: 2 2, 3 3
- deliberate_duplicate: 2 1, 3 1
- duplicate: 3 1
- near_distinct: 1 7, 2 4, 4 1, opposite 2
- antonym: 
- random: 0 1

## Known groups, rubric E2

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 219 | 2.05 / 30% / 12% / 0% | 1.95 / 23% / 11% / 0% |
| drop_or_merge | 5 | 3.00 / 100% / 0% / 0% | 2.80 / 60% / 0% / 0% |
| deliberate_duplicate | 2 | 2.50 / 50% / 0% / 0% | 2.50 / 50% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 14 | 2.00 / 27% / 21% / 0% | 1.83 / 17% / 14% / 0% |
| antonym | 0 | – / – / – / – | – / – / – / – |
| random | 1 | 0.00 / 0% / 0% / 0% | 0.00 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 5, 1 45, 2 100, 3 42, 4 2, opposite 25
- drop_or_merge: 2 2, 3 2, 4 1
- deliberate_duplicate: 2 1, 3 1
- duplicate: 3 1
- near_distinct: 1 5, 2 5, 3 1, 4 1, opposite 2
- antonym: 
- random: 0 1

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A2 | Sonnet 5.5 | 242 | 0% (0) | 12% (30) | – of 0 | 100% of 20 | 4% of 222 |
| A2 | Opus 5.5 | 242 | 0% (0) | 11% (27) | – of 0 | 100% of 20 | 3% of 222 |
| C2 | Sonnet 5.5 | 242 | 0% (0) | 12% (30) | – of 0 | 100% of 20 | 4% of 222 |
| C2 | Opus 5.5 | 242 | 0% (0) | 11% (27) | – of 0 | 100% of 20 | 3% of 222 |
| D2 | Sonnet 5.5 | 242 | 0% (0) | 12% (30) | – of 0 | 100% of 20 | 4% of 222 |
| D2 | Opus 5.5 | 242 | 0% (0) | 11% (27) | – of 0 | 100% of 20 | 3% of 222 |
| E2 | Sonnet 5.5 | 242 | 0% (0) | 12% (30) | – of 0 | 100% of 20 | 4% of 222 |
| E2 | Opus 5.5 | 242 | 0% (0) | 11% (27) | – of 0 | 100% of 20 | 3% of 222 |

## Rubric A2 (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 6 | 0.274 | 4 | 0.214 |
| 1 | 55 | 0.350 | 45 | 0.480 |
| 2 | 113 | 0.404 | 87 | 0.603 |
| 3 | 35 | 0.498 | 23 | 0.771 |
| 4 | 6 | 0.660 | 6 | 0.853 |
| opposite | 27 | 0.444 | 18 | -0.002 |

## Rubric C2 (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 5 | 0.265 | 4 | 0.214 |
| 1 | 57 | 0.348 | 46 | 0.480 |
| 2 | 108 | 0.404 | 82 | 0.610 |
| 3 | 24 | 0.450 | 17 | 0.665 |
| 4 | 16 | 0.565 | 11 | 0.843 |
| 5 | 5 | 0.657 | 5 | 0.841 |
| opposite | 27 | 0.444 | 18 | -0.002 |

## Rubric D2 (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| different | 7 | 0.277 | 5 | 0.265 |
| neighbours | 72 | 0.365 | 58 | 0.514 |
| overlap | 90 | 0.410 | 69 | 0.601 |
| contains | 29 | 0.438 | 19 | 0.701 |
| variant | 13 | 0.583 | 10 | 0.844 |
| same | 4 | 0.638 | 4 | 0.840 |
| opposite | 27 | 0.444 | 18 | -0.002 |

## Rubric E2 (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 6 | 0.281 | 5 | 0.241 |
| 1 | 50 | 0.343 | 43 | 0.467 |
| 2 | 108 | 0.398 | 79 | 0.601 |
| 3 | 47 | 0.500 | 34 | 0.752 |
| 4 | 4 | 0.638 | 4 | 0.840 |
| opposite | 27 | 0.444 | 18 | -0.002 |

## The same pair in two calls

- rubric A2: Sonnet 5.5 14 of 18 the same; Opus 5.5 14 of 18 the same
- rubric C2: Sonnet 5.5 14 of 18 the same; Opus 5.5 15 of 18 the same
- rubric D2: Sonnet 5.5 13 of 18 the same; Opus 5.5 13 of 18 the same
- rubric E2: Sonnet 5.5 15 of 18 the same; Opus 5.5 13 of 18 the same

## The arms experiment: 2 passes, decision scale, cut-off 3

Pass 2 sent the same calls with the listed traits in a fresh order: 20 of 84 calls kept pass 1's order by chance (1 of them list one trait); 157 of 242 pairs went out under another id.

The decision scale is rubric A's 0-4 with "opposite" and "unsure": C2 maps 5 -> 4, 4 -> 3, 3 -> 3; D2 maps same 4, variant 3, contains 3, overlap 2, neighbours 1, different 0.  Covered means 3 or more on it ("opposite" is not covered, "unsure" neither), over the nearest-neighbour pairs.  The native scale is each rubric's own answers (C2 0-5; D2's relations ranked different 0 ... same 5, as C's rungs).  Exact agreement counts every answer, categories included.

### Cross-arm table

| arm | model | consistency, exact (native) | consistency, exact (decision) | between-pass flips at 3 | agreement, exact, pass 1 (native / decision) | agreement, pass 2 | covered at 3, pass 1 | targets covered, pass 1 | between-model crossings at 3 (pass 1 / pass 2) |
|---|---|---|---|---|---|---|---|---|---|
| A2 | Sonnet 5.5 | 88% (242) | 88% | 10 of 219 | 80% / 80% | 82% / 82% | 48 of 219 (22%) | 39 of 73 | 21 of 219 / 14 of 219 |
| A2 | Opus 5.5 | 86% (242) | 86% | 5 of 219 | 80% / 80% | 82% / 82% | 35 of 219 (16%) | 28 of 73 | 21 of 219 / 14 of 219 |
| C2 | Sonnet 5.5 | 81% (242) | 83% | 12 of 219 | 77% / 79% | 78% / 79% | 36 of 219 (16%) | 29 of 73 | 21 of 219 / 22 of 219 |
| C2 | Opus 5.5 | 85% (242) | 85% | 9 of 219 | 77% / 79% | 78% / 79% | 39 of 219 (18%) | 30 of 73 | 21 of 219 / 22 of 219 |
| D2 | Sonnet 5.5 | 80% (242) | 80% | 16 of 219 | 75% / 76% | 75% / 76% | 25 of 219 (11%) | 18 of 73 | 21 of 219 / 18 of 219 |
| D2 | Opus 5.5 | 79% (242) | 79% | 13 of 219 | 75% / 76% | 75% / 76% | 40 of 219 (18%) | 31 of 73 | 21 of 219 / 18 of 219 |
| E2 | Sonnet 5.5 | 83% (242) | 83% | 13 of 219 | 84% / 84% | 79% / 79% | 57 of 219 (26%) | 46 of 73 | 21 of 219 / 24 of 219 |
| E2 | Opus 5.5 | 86% (242) | 86% | 8 of 219 | 84% / 84% | 79% / 79% | 44 of 219 (20%) | 35 of 73 | 21 of 219 / 24 of 219 |

Agreement is each model against the other one (Sonnet 5.5 against Opus 5.5 in this experiment); crossings are the nearest pairs the two models put on different sides of the cut-off, flips the nearest pairs one model put on different sides in its two passes.

### Parse rates by pass

| rubric | model | pass | ok / total | first attempt |
|---|---|---|---|---|
| A2 | Opus 5.5 | 1 | 242 / 242 | 242 / 242 |
| A2 | Sonnet 5.5 | 1 | 242 / 242 | 242 / 242 |
| C2 | Opus 5.5 | 1 | 242 / 242 | 242 / 242 |
| C2 | Sonnet 5.5 | 1 | 242 / 242 | 239 / 242 |
| D2 | Opus 5.5 | 1 | 242 / 242 | 242 / 242 |
| D2 | Sonnet 5.5 | 1 | 242 / 242 | 242 / 242 |
| E2 | Opus 5.5 | 1 | 242 / 242 | 242 / 242 |
| E2 | Sonnet 5.5 | 1 | 242 / 242 | 242 / 242 |
| A2 | Opus 5.5 | 2 | 242 / 242 | 242 / 242 |
| A2 | Sonnet 5.5 | 2 | 242 / 242 | 242 / 242 |
| C2 | Opus 5.5 | 2 | 242 / 242 | 242 / 242 |
| C2 | Sonnet 5.5 | 2 | 242 / 242 | 239 / 242 |
| D2 | Opus 5.5 | 2 | 242 / 242 | 242 / 242 |
| D2 | Sonnet 5.5 | 2 | 242 / 242 | 242 / 242 |
| E2 | Opus 5.5 | 2 | 242 / 242 | 242 / 242 |
| E2 | Sonnet 5.5 | 2 | 242 / 242 | 242 / 242 |

### Arm A2: overlap_concept_implies (A with the implication test)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 242 | 88% | 100% | 0.01 | 0.90 | 88% | 100% | 10 of 219 (6 covered in pass 1 only, 4 in pass 2 only) |
| Opus 5.5 | 242 | 86% | 100% | -0.03 | 0.89 | 86% | 100% | 5 of 219 (1 covered in pass 1 only, 4 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 1, 1/2 17, 2/3 10, 3/4 1 (29 of 29 between neighbouring points); decision: 0/1 1, 1/2 17, 2/3 10, 3/4 1
- Opus 5.5: 0/1 2, 1/2 22, 2/3 6, 3/4 3 (33 of 33 between neighbouring points); decision: 0/1 2, 1/2 22, 2/3 6, 3/4 3

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 100% / 100% (1) | 96% / 96% (54) | 86% / 86% (187) |
| Opus 5.5 | 100% / 100% (1) | 93% / 93% (54) | 84% / 84% (187) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / accommodating: 3, 2
- cruel / malicious: 3, 2
- flippant / irreverent: 3, 2
- humble / modest: 3, 2
- indecisive / noncommittal: 2, 3
- innovative / futuristic: 2, 3
- moderate / diplomatic: 3, 2
- pacifist / peaceful: 2, 3
- perfectionist / detail-oriented: 2, 3
- unhelpful / uncaring: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: 2, 3
- methodical / organized: 2, 3
- quantitative / data-driven: 2, 3
- sarcastic / sardonic: 2, 3
- techno-hierophantic / spiritual: 3, 2

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 242 | 80% | 100% | 0.06 | 0.83 | 80% | 100% | 21 of 219 (4 Opus 5.5 covered only, 17 Sonnet 5.5 covered only) |
| 2 | 242 | 82% | 100% | 0.10 | 0.86 | 82% | 100% | 14 of 219 (3 Opus 5.5 covered only, 11 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 1, 1/2 17, 1/opposite 3, 2/3 24, 3/4 4
- pass 2: 1/2 20, 1/opposite 3, 2/3 16, 3/4 4

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: 2, 3
- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- compassionate / empathetic: 2, 3
- cruel / malicious: 2, 3
- deontological / principled: 2, 3
- ecocentric / environmental: 3, 2
- edgy / provocative: 2, 3
- flippant / irreverent: 2, 3
- formalist / ritualistic: 2, 3
- humble / modest: 2, 3
- indecisive / noncommittal: 3, 2
- methodical / organized: 2, 3
- moderate / diplomatic: 2, 3
- provocative / edgy: 2, 3
- quantitative / data-driven: 2, 3
- sarcastic / sardonic: 2, 3
- sarcastic / ironic: 3, 2
- techno-hierophantic / spiritual: 3, 2
- unhelpful / uncaring: 2, 3

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: 3, 2
- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- compassionate / empathetic: 2, 3
- deontological / principled: 2, 3
- ecocentric / environmental: 3, 2
- edgy / provocative: 2, 3
- formalist / ritualistic: 2, 3
- innovative / futuristic: 2, 3
- pacifist / peaceful: 2, 3
- perfectionist / detail-oriented: 2, 3
- provocative / edgy: 2, 3
- sarcastic / ironic: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 219 | 48 | 22% | 39 of 73 | 27 | 0 |
| Sonnet 5.5 | 2 | 219 | 46 | 21% | 38 of 73 | 27 | 0 |
| Opus 5.5 | 1 | 219 | 35 | 16% | 28 of 73 | 25 | 0 |
| Opus 5.5 | 2 | 219 | 38 | 17% | 29 of 73 | 25 | 0 |

Kinds of difference the reasons of 3s name (not asked: rubric A2's 3s, as a control; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 55 | 6 | 4 | 6 | 1 | 8 | 30 (55%) | 0 |
| Sonnet 5.5 | 2 | 52 | 9 | 2 | 6 | 1 | 11 | 25 (48%) | 2 |
| Opus 5.5 | 1 | 35 | 4 | 1 | 9 | 1 | 4 | 18 (51%) | 2 |
| Opus 5.5 | 2 | 38 | 10 | 2 | 11 | 1 | 4 | 12 (32%) | 2 |

### Arm C2: overlap_six_implies (C with the implication test)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 242 | 81% | 97% | 0.00 | 0.86 | 83% | 100% | 12 of 219 (3 covered in pass 1 only, 9 in pass 2 only) |
| Opus 5.5 | 242 | 85% | 98% | 0.00 | 0.89 | 85% | 100% | 9 of 219 (4 covered in pass 1 only, 5 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 1, 1/2 26, 2/3 7, 2/4 6, 3/4 4, 4/5 1 (39 of 45 between neighbouring points); decision: 0/1 1, 1/2 26, 2/3 13, 3/4 1
- Opus 5.5: 0/1 3, 1/2 22, 2/3 6, 2/4 4, 3/4 1, 4/5 1 (33 of 37 between neighbouring points); decision: 0/1 3, 1/2 22, 2/3 10, 3/4 1

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 100% / 100% (1) | 94% / 94% (54) | 78% / 80% (187) |
| Opus 5.5 | 100% / 100% (1) | 91% / 91% (54) | 83% / 83% (187) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: 4, 2
- analytical / reductionist: 2, 3
- big-picture / holistic: 2, 4
- careless / sloppy: 2, 3
- compassionate / empathetic: 4, 2
- indecisive / noncommittal: 2, 4
- innovative / creative: 2, 4
- pacifist / peaceful: 2, 3
- perfectionist / detail-oriented: 2, 3
- pluralist / cosmopolitan: 2, 3
- unhelpful / uncaring: 2, 3
- zealous / passionate: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- analytical / reductionist: 3, 2
- calm / temperate: 2, 3
- condescending / arrogant: 2, 3
- entertaining / playful: 2, 4
- indecisive / noncommittal: 2, 4
- methodical / organized: 2, 4
- sarcastic / sardonic: 4, 2
- serious / formal: 3, 2
- zealous / passionate: 3, 2

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 242 | 77% | 94% | 0.02 | 0.80 | 79% | 100% | 21 of 219 (12 Opus 5.5 covered only, 9 Sonnet 5.5 covered only) |
| 2 | 242 | 78% | 96% | 0.02 | 0.83 | 79% | 100% | 22 of 219 (10 Opus 5.5 covered only, 12 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 2, 1/2 20, 1/3 1, 1/opposite 3, 2/3 12, 2/4 11, 3/4 3, 4/5 3
- pass 2: 0/1 2, 1/2 19, 1/opposite 3, 2/3 16, 2/4 9, 3/4 2, 4/5 3

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: 3, 2
- agreeable / conciliatory: 2, 4
- analytical / reductionist: 3, 2
- benevolent / altruistic: 2, 4
- careless / sloppy: 3, 2
- chaotic / disorganized: 3, 2
- compassionate / empathetic: 2, 4
- critical / skeptical: 3, 2
- ecocentric / environmental: 3, 2
- edgy / provocative: 2, 4
- entertaining / playful: 2, 4
- formalist / ritualistic: 2, 4
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- methodical / organized: 2, 4
- perfectionist / detail-oriented: 3, 2
- provocative / edgy: 2, 4
- quantitative / data-driven: 2, 4
- serious / formal: 3, 2
- techno-hierophantic / spiritual: 3, 2
- wry / witty: 3, 1

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: 3, 2
- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 4
- big-picture / holistic: 2, 4
- calm / temperate: 3, 2
- chaotic / disorganized: 3, 2
- condescending / arrogant: 3, 2
- critical / skeptical: 3, 2
- ecocentric / environmental: 3, 2
- edgy / provocative: 2, 4
- formalist / ritualistic: 2, 4
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- innovative / creative: 2, 4
- pacifist / peaceful: 2, 3
- pluralist / cosmopolitan: 2, 3
- provocative / edgy: 2, 4
- quantitative / data-driven: 2, 4
- sarcastic / sardonic: 2, 4
- techno-hierophantic / spiritual: 3, 2
- unhelpful / uncaring: 2, 3
- wry / witty: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 219 | 36 | 16% | 29 of 73 | 27 | 0 |
| Sonnet 5.5 | 2 | 219 | 42 | 19% | 34 of 73 | 27 | 0 |
| Opus 5.5 | 1 | 219 | 39 | 18% | 30 of 73 | 25 | 0 |
| Opus 5.5 | 2 | 219 | 40 | 18% | 31 of 73 | 25 | 0 |

### Arm D2: overlap_relation_implies (D with the implication test)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 242 | 80% | 96% | -0.01 | 0.80 | 80% | 100% | 16 of 219 (8 covered in pass 1 only, 8 in pass 2 only) |
| Opus 5.5 | 242 | 79% | 99% | 0.00 | 0.85 | 79% | 99% | 13 of 219 (7 covered in pass 1 only, 6 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: neighbours/overlap 31, overlap/contains 9, overlap/variant 8, variant/same 1 (41 of 49 between neighbouring points); decision: 1/2 31, 2/3 17, 3/4 1
- Opus 5.5: different/neighbours 3, neighbours/overlap 31, overlap/contains 11, overlap/variant 1, overlap/same 2, contains/variant 2, variant/same 2 (49 of 52 between neighbouring points); decision: 0/1 3, 1/2 31, 2/3 12, 2/4 2, 3/4 2

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 100% / 100% (1) | 85% / 85% (54) | 78% / 78% (187) |
| Opus 5.5 | 100% / 100% (1) | 87% / 87% (54) | 76% / 77% (187) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- careless / sloppy: overlap, contains
- cruel / callous: contains, overlap
- environmental / ecocentric: contains, overlap
- extroverted / gregarious: overlap, variant
- formalist / ritualistic: variant, overlap
- goofy / playful: overlap, contains
- indecisive / noncommittal: overlap, variant
- perfectionist / meticulous: variant, overlap
- perfectionist / detail-oriented: contains, overlap
- pluralist / cosmopolitan: overlap, contains
- quantitative / data-driven: overlap, variant
- sarcastic / sardonic: overlap, variant
- sarcastic / ironic: contains, overlap
- systems-thinker / holistic: overlap, contains
- theatrical / melodramatic: variant, overlap
- wry / witty: contains, overlap

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: overlap, contains
- analytical / reductionist: contains, overlap
- calm / temperate: contains, overlap
- condescending / arrogant: contains, overlap
- ecocentric / environmental: overlap, contains
- entertaining / playful: variant, overlap
- formalist / formulaic: overlap, contains
- indecisive / noncommittal: overlap, same
- meditative / serene: contains, overlap
- serious / formal: contains, overlap
- theatrical / dramatic: overlap, same
- understated / modest: overlap, contains
- unhelpful / uncaring: contains, overlap

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 242 | 75% | 97% | -0.01 | 0.78 | 76% | 99% | 21 of 219 (18 Opus 5.5 covered only, 3 Sonnet 5.5 covered only) |
| 2 | 242 | 75% | 98% | -0.03 | 0.81 | 76% | 99% | 18 of 219 (16 Opus 5.5 covered only, 2 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: different/neighbours 2, different/opposite 1, neighbours/overlap 27, neighbours/contains 1, neighbours/variant 1, neighbours/opposite 2, overlap/contains 17, overlap/variant 4, overlap/same 1, contains/variant 2, variant/same 2
- pass 2: different/neighbours 3, different/opposite 1, neighbours/overlap 26, neighbours/variant 1, neighbours/opposite 2, overlap/contains 16, overlap/variant 3, overlap/same 1, contains/variant 2, variant/same 5

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: contains, overlap
- analytical / reductionist: contains, overlap
- anxious / neurotic: contains, overlap
- calm / temperate: contains, neighbours
- careless / sloppy: contains, overlap
- condescending / arrogant: contains, overlap
- critical / skeptical: contains, overlap
- ecocentric / environmental: overlap, contains
- entertaining / playful: variant, overlap
- extroverted / gregarious: contains, overlap
- formalist / ritualistic: overlap, variant
- goofy / playful: contains, overlap
- hedonistic / self-indulgent: variant, overlap
- meditative / serene: contains, overlap
- pluralist / cosmopolitan: contains, overlap
- serious / formal: contains, overlap
- systems-thinker / holistic: contains, overlap
- techno-hierophantic / spiritual: contains, overlap
- theatrical / dramatic: overlap, same
- unhelpful / uncaring: contains, overlap
- zealous / passionate: contains, overlap

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: contains, overlap
- agreeable / conciliatory: contains, overlap
- anxious / neurotic: contains, overlap
- critical / skeptical: contains, overlap
- cruel / callous: contains, overlap
- environmental / ecocentric: contains, overlap
- formalist / formulaic: contains, overlap
- hedonistic / self-indulgent: same, overlap
- perfectionist / meticulous: contains, overlap
- perfectionist / detail-oriented: contains, overlap
- quantitative / data-driven: overlap, variant
- sarcastic / sardonic: overlap, variant
- sarcastic / ironic: contains, overlap
- techno-hierophantic / spiritual: contains, overlap
- theatrical / melodramatic: variant, overlap
- understated / modest: contains, overlap
- wry / witty: contains, overlap
- zealous / passionate: contains, overlap

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 219 | 25 | 11% | 18 of 73 | 27 | 0 |
| Sonnet 5.5 | 2 | 219 | 25 | 11% | 21 of 73 | 27 | 0 |
| Opus 5.5 | 1 | 219 | 40 | 18% | 31 of 73 | 25 | 0 |
| Opus 5.5 | 2 | 219 | 39 | 18% | 31 of 73 | 25 | 0 |

Relations named (all pairs):

| model | pass | same | variant | contains | overlap | neighbours | different | opposite | unsure | unparsed |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 3 | 16 | 11 | 119 | 57 | 6 | 30 | 0 | 0 |
| Sonnet 5.5 | 2 | 2 | 19 | 10 | 113 | 62 | 6 | 30 | 0 | 0 |
| Opus 5.5 | 1 | 4 | 13 | 29 | 90 | 72 | 7 | 27 | 0 | 0 |
| Opus 5.5 | 2 | 8 | 10 | 28 | 87 | 74 | 8 | 27 | 0 | 0 |

The wider of a "contains":

| model | pass | contains | wider: target | wider: listed | missing | not target or listed | wider given with another relation | alias spellings |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 11 | 5 | 6 | 0 | 0 | 25 | 0 |
| Sonnet 5.5 | 2 | 10 | 6 | 4 | 0 | 0 | 32 | 0 |
| Opus 5.5 | 1 | 29 | 13 | 16 | 0 | 0 | 0 | 0 |
| Opus 5.5 | 2 | 28 | 15 | 13 | 0 | 0 | 0 | 0 |

- Sonnet 5.5, pass 1 against pass 2: 6 pairs "contains" in both, the same wider 6, the other 0, unknown 0
- Opus 5.5, pass 1 against pass 2: 22 pairs "contains" in both, the same wider 22, the other 0, unknown 0
- Sonnet 5.5 against Opus 5.5, pass 1: 10 pairs "contains" for both, the same wider 8, the other 2, unknown 0
- Sonnet 5.5 against Opus 5.5, pass 2: 10 pairs "contains" for both, the same wider 10, the other 0, unknown 0

### Arm E2: overlap_scope_implies (E with the implication test)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 242 | 83% | 100% | -0.06 | 0.86 | 83% | 100% | 13 of 219 (9 covered in pass 1 only, 4 in pass 2 only) |
| Opus 5.5 | 242 | 86% | 100% | -0.05 | 0.88 | 86% | 100% | 8 of 219 (5 covered in pass 1 only, 3 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 2, 1/2 23, 2/3 14, 3/4 1 (40 of 40 between neighbouring points); decision: 0/1 2, 1/2 23, 2/3 14, 3/4 1
- Opus 5.5: 0/1 3, 1/2 20, 2/3 9, 3/4 2 (34 of 34 between neighbouring points); decision: 0/1 3, 1/2 20, 2/3 9, 3/4 2

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 100% / 100% (1) | 93% / 93% (54) | 81% / 81% (187) |
| Opus 5.5 | 100% / 100% (1) | 94% / 94% (54) | 83% / 83% (187) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- condescending / arrogant: 3, 2
- cruel / indifferent-to-animals: 3, 2
- ecocentric / environmental: 2, 3
- experiential / practical: 3, 2
- flippant / irreverent: 3, 2
- goofy / playful: 3, 2
- inclusive / pluralist: 3, 2
- indecisive / noncommittal: 2, 3
- moderate / diplomatic: 3, 2
- perfectionist / detail-oriented: 2, 3
- pluralist / cosmopolitan: 2, 3
- religious / spiritual: 3, 2
- zealous / passionate: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / accommodating: 3, 2
- big-picture / holistic: 3, 2
- condescending / arrogant: 2, 3
- formalist / ritualistic: 3, 2
- iconoclastic / contrarian: 2, 3
- innovative / futuristic: 2, 3
- religious / spiritual: 3, 2
- sarcastic / sardonic: 3, 2

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 242 | 84% | 99% | 0.08 | 0.84 | 84% | 99% | 21 of 219 (4 Opus 5.5 covered only, 17 Sonnet 5.5 covered only) |
| 2 | 242 | 79% | 99% | 0.08 | 0.80 | 79% | 99% | 24 of 219 (7 Opus 5.5 covered only, 17 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 1, 1/2 9, 1/3 3, 1/opposite 3, 2/3 21, 3/4 1
- pass 2: 0/1 2, 1/2 18, 1/3 3, 1/opposite 3, 2/3 22, 3/4 2

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: 3, 2
- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 3
- clannish / cliqueish: 2, 3
- clannish / insular: 2, 3
- clannish / sectarian: 1, 3
- compassionate / merciful: 2, 3
- condescending / arrogant: 2, 3
- cruel / indifferent-to-animals: 1, 3
- deontological / principled: 2, 3
- experiential / practical: 2, 3
- flippant / irreverent: 2, 3
- inclusive / pluralist: 2, 3
- indecisive / noncommittal: 3, 2
- innovative / creative: 2, 3
- moderate / diplomatic: 2, 3
- nationalist / regionalist: 2, 3
- nationalist / civilizationist: 2, 3
- pacifist / peaceful: 2, 3
- sarcastic / ironic: 3, 2
- wry / witty: 3, 1

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- clannish / cliqueish: 2, 3
- clannish / insular: 2, 3
- clannish / sectarian: 1, 3
- compassionate / merciful: 2, 3
- condescending / arrogant: 3, 2
- deontological / principled: 2, 3
- ecocentric / environmental: 2, 3
- formalist / ritualistic: 2, 3
- goofy / playful: 3, 2
- iconoclastic / contrarian: 3, 2
- innovative / creative: 2, 3
- innovative / futuristic: 3, 2
- nationalist / regionalist: 1, 3
- nationalist / civilizationist: 1, 3
- pacifist / peaceful: 2, 3
- perfectionist / detail-oriented: 2, 3
- pluralist / cosmopolitan: 2, 3
- sarcastic / sardonic: 2, 3
- sarcastic / ironic: 3, 2
- wry / witty: 3, 2
- zealous / passionate: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 219 | 57 | 26% | 46 of 73 | 27 | 0 |
| Sonnet 5.5 | 2 | 219 | 52 | 24% | 41 of 73 | 27 | 0 |
| Opus 5.5 | 1 | 219 | 44 | 20% | 35 of 73 | 25 | 0 |
| Opus 5.5 | 2 | 219 | 42 | 19% | 35 of 73 | 25 | 0 |

Kinds of difference the reasons of 3s name (asked of a 3's reason; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 64 | 19 | 12 | 9 | 4 | 21 | 10 (16%) | 10 |
| Sonnet 5.5 | 2 | 59 | 17 | 6 | 11 | 5 | 22 | 7 (12%) | 8 |
| Opus 5.5 | 1 | 47 | 17 | 5 | 11 | 4 | 16 | 1 (2%) | 7 |
| Opus 5.5 | 2 | 46 | 12 | 10 | 10 | 6 | 16 | 0 (0%) | 7 |

## Round 2: the clarified lines, on the confusion subset

The subset: 123 pairs (87 with both a 2 and a 3 among their readings, 36 more with a 2 whose reason describes a containment) in 84 of 180 calls.  The run sent those calls whole, as round 1 built them: 242 pairs, 119 of them controls.

Each round-2 arm against its round-1 arm from overlap_arms_1 on the same pairs (A2 against A, C2 against C, D2 against D, E2 against E); pass 1 sent the round-1 order of every call and pass 2 the same reshuffle as round 1, so the user turns are round 1's.  Cut-off 3 on the decision scale.  Crossings (the two models on different sides of it in a pass), flips (one model's two passes on different sides) and the share at 3 or more count every pair of the population, whatever its group (round 1's headline table counted the nearest pairs only).  Self-contradictions, pooled over both passes: answers at 2 (2, "overlap") whose reason describes a containment and not a two-sided overlap; the reverse slip: answers at 3 (3, "contains", and C's 4 and D's "variant") whose reason describes a two-sided overlap; round 1's patterns (in `summary.json`).  Cells read round 1 → round 2.

**Selection.**  The subset was chosen from these round-1 readings (and earlier runs'), so round 1's figures on it lean toward confusion by construction, and any fresh reading would look better there (regression to the mean); on the controls the lean is the other way.  The round-2 arms are measured alike and compare fairly with each other.

### The brief's test

Improves: fewer self-contradictions and fewer between-model crossings at 3 than the round-1 arm on the same pairs, with self-consistency (exact, decision scale) not lower for either model.

| population | arm | self-contradictions, both models and passes | of which reverse | crossings at 3, both passes | flips at 3, both models | consistency, decision, Sonnet 5.5 | consistency, decision, Opus 5.5 | improves |
|---|---|---|---|---|---|---|---|---|
| subset | A2 vs A | 57 → 50 | 2 → 4 | 29 → 39 | 17 → 15 | 83% → 89% | 88% → 86% | no |
| subset | C2 vs C | 46 → 53 | 1 → 2 | 40 → 49 | 20 → 23 | 86% → 80% | 76% → 88% | no |
| subset | D2 vs D | 46 → 32 | 0 → 1 | 41 → 44 | 13 → 30 | 89% → 76% | 85% → 73% | no |
| subset | E2 vs E | 43 → 32 | 9 → 3 | 37 → 47 | 17 → 23 | 89% → 84% | 85% → 85% | no |
| sent | A2 vs A | 57 → 57 | 2 → 4 | 29 → 40 | 17 → 16 | 88% → 88% | 88% → 86% | no |
| sent | C2 vs C | 46 → 55 | 1 → 2 | 40 → 49 | 20 → 23 | 88% → 83% | 81% → 85% | no |
| sent | D2 vs D | 46 → 33 | 0 → 1 | 41 → 45 | 13 → 31 | 90% → 80% | 84% → 79% | no |
| sent | E2 vs E | 43 → 34 | 9 → 3 | 37 → 49 | 17 → 23 | 90% → 83% | 87% → 86% | no |

### The subset's pairs: 123 pairs

By group: nearest 112, near_distinct 6, drop_or_merge 3, duplicate 1, deliberate_duplicate 1.

| arm | model | consistency, exact, native | decision | flips at 3 | at 3 or more, pass 1 | pass 2 | 2s with a containment reason | 3s with a two-sided reason |
|---|---|---|---|---|---|---|---|---|
| A2 vs A | Sonnet 5.5 | 83% → 89% | 83% → 89% | 13 → 9 of 123 | 40 of 123 (32%) → 49 of 123 (40%) | 35 of 123 (28%) → 48 of 123 (39%) | 35 of 147 (24%) → 29 of 131 (22%) | 1 of 75 (1%) → 4 of 96 (4%) |
| A2 vs A | Opus 5.5 | 88% → 86% | 88% → 86% | 4 → 6 of 123 | 31 of 123 (25%) → 34 of 123 (28%) | 31 of 123 (25%) → 38 of 123 (31%) | 20 of 148 (14%) → 17 of 147 (12%) | 1 of 61 (2%) → 0 of 64 (0%) |
| C2 vs C | Sonnet 5.5 | 86% → 77% | 86% → 80% | 9 → 13 of 123 | 19 of 123 (15%) → 36 of 123 (29%) | 18 of 123 (15%) → 41 of 123 (33%) | 34 of 173 (20%) → 39 of 149 (26%) | 0 of 37 (0%) → 1 of 76 (1%) |
| C2 vs C | Opus 5.5 | 76% → 87% | 76% → 88% | 11 → 10 of 123 | 24 of 123 (20%) → 38 of 123 (31%) | 27 of 123 (22%) → 40 of 123 (32%) | 11 of 162 (7%) → 12 of 146 (8%) | 1 of 48 (2%) → 1 of 71 (1%) |
| D2 vs D | Sonnet 5.5 | 89% → 76% | 89% → 76% | 7 → 17 of 123 | 7 of 123 (6%) → 23 of 123 (19%) | 6 of 123 (5%) → 24 of 123 (20%) | 35 of 210 (17%) → 27 of 171 (16%) | 0 of 13 (0%) → 0 of 46 (0%) |
| D2 vs D | Opus 5.5 | 85% → 72% | 85% → 73% | 6 → 13 of 123 | 22 of 123 (18%) → 39 of 123 (32%) | 22 of 123 (18%) → 38 of 123 (31%) | 11 of 168 (6%) → 4 of 127 (3%) | 0 of 39 (0%) → 1 of 69 (1%) |
| E2 vs E | Sonnet 5.5 | 89% → 84% | 89% → 84% | 10 → 14 of 123 | 37 of 123 (30%) → 59 of 123 (48%) | 39 of 123 (32%) → 53 of 123 (43%) | 22 of 146 (15%) → 17 of 123 (14%) | 4 of 76 (5%) → 3 of 111 (3%) |
| E2 vs E | Opus 5.5 | 85% → 85% | 85% → 85% | 7 → 9 of 123 | 36 of 123 (29%) → 44 of 123 (36%) | 37 of 123 (30%) → 43 of 123 (35%) | 12 of 143 (8%) → 12 of 142 (8%) | 5 of 70 (7%) → 0 of 83 (0%) |

Between the models (Sonnet 5.5 against Opus 5.5):

| arm | agreement, exact, native, pass 1 | pass 2 | decision, pass 1 | pass 2 | crossings at 3, pass 1 | pass 2 |
|---|---|---|---|---|---|---|
| A2 vs A | 84% → 73% | 77% → 74% | 84% → 73% | 77% → 74% | 11 of 123 → 23 of 123 | 18 of 123 → 16 of 123 |
| C2 vs C | 74% → 69% | 73% → 70% | 76% → 72% | 74% → 72% | 19 of 123 → 24 of 123 | 21 of 123 → 25 of 123 |
| D2 vs D | 76% → 67% | 71% → 70% | 76% → 68% | 72% → 72% | 19 of 123 → 24 of 123 | 22 of 123 → 20 of 123 |
| E2 vs E | 79% → 79% | 74% → 72% | 79% → 79% | 74% → 72% | 15 of 123 → 23 of 123 | 22 of 123 → 24 of 123 |

D2 against D, the relations named and the wider of a "contains" (round 1 → round 2):

| model | pass | same | variant | contains | overlap | neighbours | different | opposite | unsure | wider: target | wider: listed | missing | not target or listed | wider given with another relation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 0 → 1 | 2 → 11 | 5 → 11 | 106 → 86 | 10 → 14 | 0 → 0 | 0 → 0 | 0 → 0 | 5 → 5 | 0 → 6 | 0 → 0 | 0 → 0 | 29 → 10 |
| Sonnet 5.5 | 2 | 0 → 0 | 3 → 14 | 3 → 10 | 104 → 85 | 13 → 14 | 0 → 0 | 0 → 0 | 0 → 0 | 3 → 6 | 0 → 4 | 0 → 0 | 0 → 0 | 25 → 18 |
| Opus 5.5 | 1 | 2 → 2 | 4 → 8 | 16 → 29 | 87 → 63 | 14 → 21 | 0 → 0 | 0 → 0 | 0 → 0 | 10 → 13 | 6 → 16 | 0 → 0 | 0 → 0 | 0 → 0 |
| Opus 5.5 | 2 | 3 → 6 | 5 → 5 | 14 → 27 | 81 → 64 | 20 → 21 | 0 → 0 | 0 → 0 | 0 → 0 | 7 → 14 | 7 → 13 | 0 → 0 | 0 → 0 | 0 → 0 |

- Sonnet 5.5, pass 1 against pass 2: "contains" in both 2 → 6, the same wider 2 → 6, the other 0 → 0
- Opus 5.5, pass 1 against pass 2: "contains" in both 14 → 22, the same wider 13 → 22, the other 1 → 0
- Sonnet 5.5 against Opus 5.5, pass 1: "contains" for both 4 → 10, the same wider 4 → 8, the other 0 → 2
- Sonnet 5.5 against Opus 5.5, pass 2: "contains" for both 1 → 10, the same wider 1 → 10, the other 0 → 0

### Every pair sent (the subset and its controls): 242 pairs

By group: nearest 219, near_distinct 14, random 1, drop_or_merge 5, duplicate 1, deliberate_duplicate 2.

| arm | model | consistency, exact, native | decision | flips at 3 | at 3 or more, pass 1 | pass 2 | 2s with a containment reason | 3s with a two-sided reason |
|---|---|---|---|---|---|---|---|---|
| A2 vs A | Sonnet 5.5 | 88% → 88% | 88% → 88% | 13 → 10 of 242 | 47 of 242 (19%) → 57 of 242 (24%) | 42 of 242 (17%) → 55 of 242 (23%) | 35 of 209 (17%) → 33 of 201 (16%) | 1 of 85 (1%) → 4 of 107 (4%) |
| A2 vs A | Opus 5.5 | 88% → 86% | 88% → 86% | 4 → 6 of 242 | 38 of 242 (16%) → 41 of 242 (17%) | 38 of 242 (16%) → 45 of 242 (19%) | 20 of 203 (10%) → 20 of 210 (10%) | 1 of 71 (1%) → 0 of 73 (0%) |
| C2 vs C | Sonnet 5.5 | 88% → 81% | 88% → 83% | 9 → 13 of 242 | 26 of 242 (11%) → 43 of 242 (18%) | 25 of 242 (10%) → 48 of 242 (20%) | 34 of 226 (15%) → 40 of 213 (19%) | 0 of 47 (0%) → 1 of 86 (1%) |
| C2 vs C | Opus 5.5 | 81% → 85% | 81% → 85% | 11 → 10 of 242 | 31 of 242 (13%) → 45 of 242 (19%) | 34 of 242 (14%) → 47 of 242 (19%) | 11 of 218 (5%) → 13 of 212 (6%) | 1 of 58 (2%) → 1 of 81 (1%) |
| D2 vs D | Sonnet 5.5 | 90% → 80% | 90% → 80% | 7 → 17 of 242 | 14 of 242 (6%) → 30 of 242 (12%) | 13 of 242 (5%) → 31 of 242 (13%) | 35 of 273 (13%) → 27 of 232 (12%) | 0 of 23 (0%) → 0 of 56 (0%) |
| D2 vs D | Opus 5.5 | 84% → 79% | 84% → 79% | 6 → 14 of 242 | 29 of 242 (12%) → 46 of 242 (19%) | 29 of 242 (12%) → 46 of 242 (19%) | 11 of 218 (5%) → 5 of 177 (3%) | 0 of 49 (0%) → 1 of 80 (1%) |
| E2 vs E | Sonnet 5.5 | 90% → 83% | 90% → 83% | 10 → 14 of 242 | 44 of 242 (18%) → 67 of 242 (28%) | 46 of 242 (19%) → 61 of 242 (25%) | 22 of 210 (10%) → 19 of 191 (10%) | 4 of 86 (5%) → 3 of 123 (2%) |
| E2 vs E | Opus 5.5 | 87% → 86% | 87% → 86% | 7 → 9 of 242 | 43 of 242 (18%) → 51 of 242 (21%) | 44 of 242 (18%) → 50 of 242 (21%) | 12 of 203 (6%) → 12 of 207 (6%) | 5 of 80 (6%) → 0 of 93 (0%) |

Between the models (Sonnet 5.5 against Opus 5.5):

| arm | agreement, exact, native, pass 1 | pass 2 | decision, pass 1 | pass 2 | crossings at 3, pass 1 | pass 2 |
|---|---|---|---|---|---|---|
| A2 vs A | 86% → 80% | 83% → 82% | 86% → 80% | 83% → 82% | 11 of 242 → 24 of 242 | 18 of 242 → 16 of 242 |
| C2 vs C | 80% → 77% | 79% → 78% | 81% → 79% | 80% → 79% | 19 of 242 → 24 of 242 | 21 of 242 → 25 of 242 |
| D2 vs D | 82% → 75% | 77% → 75% | 82% → 76% | 77% → 76% | 19 of 242 → 24 of 242 | 22 of 242 → 21 of 242 |
| E2 vs E | 84% → 84% | 81% → 79% | 84% → 84% | 81% → 79% | 15 of 242 → 24 of 242 | 22 of 242 → 25 of 242 |

D2 against D, the relations named and the wider of a "contains" (round 1 → round 2):

| model | pass | same | variant | contains | overlap | neighbours | different | opposite | unsure | wider: target | wider: listed | missing | not target or listed | wider given with another relation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 2 → 3 | 7 → 16 | 5 → 11 | 139 → 119 | 52 → 57 | 7 → 6 | 30 → 30 | 0 → 0 | 5 → 5 | 0 → 6 | 0 → 0 | 0 → 0 | 58 → 25 |
| Sonnet 5.5 | 2 | 2 → 2 | 8 → 19 | 3 → 10 | 134 → 113 | 57 → 62 | 8 → 6 | 30 → 30 | 0 → 0 | 3 → 6 | 0 → 4 | 0 → 0 | 0 → 0 | 43 → 32 |
| Opus 5.5 | 1 | 4 → 4 | 9 → 13 | 16 → 29 | 112 → 90 | 68 → 72 | 6 → 7 | 27 → 27 | 0 → 0 | 10 → 13 | 6 → 16 | 0 → 0 | 0 → 0 | 0 → 0 |
| Opus 5.5 | 2 | 5 → 8 | 10 → 10 | 14 → 28 | 106 → 87 | 72 → 74 | 8 → 8 | 27 → 27 | 0 → 0 | 7 → 15 | 7 → 13 | 0 → 0 | 0 → 0 | 0 → 0 |

- Sonnet 5.5, pass 1 against pass 2: "contains" in both 2 → 6, the same wider 2 → 6, the other 0 → 0
- Opus 5.5, pass 1 against pass 2: "contains" in both 14 → 22, the same wider 13 → 22, the other 1 → 0
- Sonnet 5.5 against Opus 5.5, pass 1: "contains" for both 4 → 10, the same wider 4 → 8, the other 0 → 2
- Sonnet 5.5 against Opus 5.5, pass 2: "contains" for both 1 → 10, the same wider 1 → 10, the other 0 → 0

### Round 2's answers behind the counts (every pair sent, in pair order)

#### A2 (overlap_concept_implies)

Answers at 2 whose reason describes a containment: 53 (32 pairs); the first 6 pairs:

- anxious / restless (subset, nearest): Sonnet 5.5 pass 1, 2: "Restless captures the fidgety, tense behavior part of anxious, but lacks worry and apprehension, and can occur without unease (e.g., boredom or novelty-seeking)."
- benevolent / helpful (subset, nearest): Sonnet 5.5 pass 2, 2: "Helpfulness is active, effective assistance to others' needs, while benevolence is a broader disposition of kindness and compassion; they overlap but neither implies the other."; Opus 5.5 pass 2, 2: "Both involve caring about others' outcomes, but helpful centers on actively providing assistance when needed, while benevolent is a broader kind, ethical goodwill toward everyone; neither strictly implies the other."
- calm / temperate (subset, nearest): Sonnet 5.5 pass 1, 2: "Temperate is about cool, measured handling of beliefs and distrust of fervor; it shares the unheated quality but is narrower and does not imply a steady, de-escalating temperament."
- careless / irresponsible (subset, nearest): Sonnet 5.5 pass 2, 2: "Irresponsible shares the letting-duties-slide and broken-promises part of careless, but lacks the inattention to detail and slapdash work; careless lacks the more serious dereliction."
- chaotic / disorganized (subset, nearest): Sonnet 5.5 pass 1, 2: "Disorganized, here applied to scattered communication, overlaps with chaotic's disorder and jumping around, but chaotic is broader and includes ignoring rules and leaving confusion behind, and disorganized is narrower in speech."; Opus 5.5 pass 1, 2: "Disorganized is scattered, non-linear structure in how information is presented, the same lack of order as chaotic but narrowed to communication; neither fully implies the other."; Opus 5.5 pass 2, 2: "Both share a core of disorder, but disorganized is narrowed to scattered presentation of information, while chaotic covers living and acting in a whirl; neither implies the other."
- collectivistic / cooperative (subset, nearest): Opus 5.5 pass 2, 2: "Both favor shared benefit over individual gain, but cooperative is about collaborating on tasks while collectivistic is a broader value orientation toward group needs."

Pairs the two models put on different sides of 3: 28 (40 crossings over the passes); the first 6:

- agreeable / accommodating (subset, nearest): pass 2, Opus 5.5 3: "Accommodating is agreeableness carried further: keeping the peace by readily giving up one's own stance." / Sonnet 5.5 2: "Accommodating means adjusting to others' needs and keeping the peace, which is close to agreeable's harmony-seeking, but it adds yielding one's position and lacks the active search for common ground."
- agreeable / conciliatory (subset, nearest): pass 1, Opus 5.5 2: "Both centre on making peace and finding common ground, but conciliatory adds active mediation between conflicting parties, while agreeable stresses a general disposition to avoid confrontation." / Sonnet 5.5 3: "Conciliatory is the active peacemaking and common-ground seeking that forms a core part of the target's description, though the target is broader in general harmony."
- analytical / reductionist (subset, nearest): pass 1, Opus 5.5 2: "Reductionism shares breaking things into components but adds explaining wholes by basic elements, while analytical stresses systematic examination; each adds something the other lacks." / Sonnet 5.5 3: "Reductionism is breaking complex things into simpler component parts, which is the core of analytical decomposition, though it adds a commitment to explaining things by basic elements."; pass 2, Opus 5.5 2: "Reductionism shares the core of breaking complex things into components and adds the claim that the whole is explained by its basic elements, so neither fully implies the other." / Sonnet 5.5 3: "Reductionism is breaking complex things into simpler component parts, which is close to analytical's decomposition, but it adds explaining everything in terms of basic elements and omits analytical's emphasis on methodical reasoning."
- benevolent / altruistic (subset, nearest): pass 1, Opus 5.5 2: "Both center on caring for others' welfare, but altruism adds selflessness over personal gain while benevolence adds ethical kindness toward everyone involved, so neither fully implies the other." / Sonnet 5.5 3: "Altruism is selfless concern for others' welfare and helping, close to benevolence's goodwill toward all, though it adds selflessness and sacrifice."; pass 2, Opus 5.5 2: "Both are concern for others' welfare, but altruism adds selflessness over personal gain, and benevolence adds an ethical aim of good outcomes for all involved." / Sonnet 5.5 3: "Altruism is selfless concern for others' welfare and societal benefit, close to benevolent's goodwill toward all, though it adds selflessness and sacrifice."
- big-picture / holistic (subset, nearest): pass 1, Opus 5.5 2: "Holistic shares the systemic, broad view, but it stresses interconnection where big-picture stresses macro-level generality." / Sonnet 5.5 3: "Holistic means seeing whole systems and interconnections rather than isolated parts, which is very close to big-picture systemic thinking, though big-picture also emphasizes general principles and themes."; pass 2, Opus 5.5 2: "Both take a systemic, broad view, but holistic stresses interconnections among parts while big-picture stresses general themes over detail." / Sonnet 5.5 3: "Holistic means considering whole systems and interconnections rather than isolated parts, closely matching big-picture's systemic, macro-level thinking, though big-picture also covers general principles and themes."
- compassionate / empathetic (subset, nearest): pass 1, Opus 5.5 2: "Empathy covers understanding all emotions and perspectives, while compassion focuses on suffering; each has a core the other lacks, though they overlap heavily." / Sonnet 5.5 3: "Empathetic is nearly the same concept, covering emotional understanding and a warm, caring response to others' feelings."; pass 2, Opus 5.5 2: "Empathy covers understanding all emotions and perspectives, while compassion focuses on responding to pain, so they share a core without either implying the other." / Sonnet 5.5 3: "Empathetic is nearly the same: understanding others' feelings and responding with warmth and compassion, with slightly more emphasis on understanding."

Answers at 3 whose reason describes a two-sided overlap: 4; the first 6 pairs:

- analytical / reductionist (subset, nearest): Sonnet 5.5 pass 2, 3: "Reductionism is breaking complex things into simpler component parts, which is close to analytical's decomposition, but it adds explaining everything in terms of basic elements and omits analytical's emphasis on methodical reasoning."
- cruel / callous (subset, nearest): Sonnet 5.5 pass 2, 3: "Callous is emotional hardness and indifference to suffering, which is the indifference part of cruel; cruel adds taking pleasure in pain, so each adds something the other lacks, but callous is largely contained in cruel."
- formalist / ritualistic (subset, nearest): Sonnet 5.5 pass 1, 3: "Both prefer established procedures and structured methods over informal or spontaneous ones; ritualistic adds ceremony and tradition, formalist adds form over substance, so they share a core largely."
- sarcastic / sardonic (subset, nearest): Sonnet 5.5 pass 2, 3: "Sardonic means dry, cutting, mocking ironic humor, very close to sarcasm, though it adds a cynical tone and an emphasis on humor."

#### C2 (overlap_six_implies)

Answers at 2 whose reason describes a containment: 53 (32 pairs); the first 6 pairs:

- agreeable / accommodating (subset, nearest): Sonnet 5.5 pass 1, 2: "Both involve keeping the peace and adjusting to others, but accommodating centers on yielding one's own position, while agreeable also includes seeking common ground and cooperation; they overlap without either implying the other."
- agreeable / conciliatory (subset, nearest): Sonnet 5.5 pass 2, 2: "Conciliatory captures the target's peace-making and common-ground-seeking core, but lacks the target's broader emphasis on avoiding confrontation and general cooperation; they overlap heavily though neither fully contains the other."; Opus 5.5 pass 2, 2: "Conciliatory is peacemaking and finding common ground between conflicting parties, which is the conflict-resolution part of agreeableness, but it is not the whole of it."
- calm / temperate (subset, nearest): Sonnet 5.5 pass 1, 2: "Temperate here is about holding beliefs coolly and distrusting fervor, which shares the unheated quality but is narrower and adds an attitude toward zeal, so it only overlaps with calm."; Opus 5.5 pass 1, 2: "Temperate narrows calmness to holding beliefs and causes without fervor, adding a distrust of zeal, so it shares a core but adds a domain and an attitude."
- careless / irresponsible (subset, nearest): Sonnet 5.5 pass 1, 2: "Irresponsible is failing at duties and shrugging them off, which overlaps with careless's letting responsibilities slide, but careless also includes slapdash work and inattention to detail, while irresponsible adds serious neglect like spending rent money."
- careless / sloppy (subset, nearest): Sonnet 5.5 pass 1, 2: "Sloppy centers on rough, unchecked work with small mistakes, which is the slapdash, inattentive-to-details part of careless, but it leaves out the broken deadlines and promises."
- chaotic / disorganized (subset, nearest): Sonnet 5.5 pass 1, 2: "Disorganized, here about scattered, unstructured presentation, is close to chaotic's disorder but narrower in domain and lacks the whirl of unfinished tasks and ignored rules; overlapping core of disorder."

Pairs the two models put on different sides of 3: 33 (49 crossings over the passes); the first 6:

- agreeable / accommodating (subset, nearest): pass 1, Opus 5.5 3: "Accommodating is harmony-seeking expressed specifically as yielding one's own stance to others, which adds concession to the agreeable core." / Sonnet 5.5 2: "Both involve keeping the peace and adjusting to others, but accommodating centers on yielding one's own position, while agreeable also includes seeking common ground and cooperation; they overlap without either implying the other."; pass 2, Opus 5.5 3: "Accommodating adds giving up one's own stance to keep the peace, so it is agreeableness plus yielding." / Sonnet 5.5 2: "Accommodating shares the harmony-keeping and conflict-avoiding core, but is specifically about yielding positions to others, which agreeable doesn't require, and it lacks the common-ground-seeking emphasis."
- agreeable / conciliatory (subset, nearest): pass 1, Opus 5.5 2: "Both centre on peace and common ground, but conciliatory means actively mediating between conflicting sides, while agreeable is a general harmony-seeking disposition; each has elements the other lacks." / Sonnet 5.5 4: "Conciliatory matches the agreeable core of reducing conflict, finding common ground and seeking peaceful resolution, with only a slightly more active peacemaking emphasis."
- analytical / reductionist (subset, nearest): pass 1, Opus 5.5 3: "Reductionism is breaking things into parts with the added claim that wholes are explained by their basic elements, so a reductionist is analytical but an analytical person need not be reductionist." / Sonnet 5.5 2: "Reductionism breaks complex phenomena into simpler component parts, which is the decomposing core of analytical thinking, but it adds a commitment to explaining things by fundamental elements; analytical can be systematic without it."; pass 2, Opus 5.5 2: "Both break complex things into components, but reductionism adds explaining wholes by their basic elements, while analytical stresses methodical examination of each part; they overlap without either implying the other." / Sonnet 5.5 3: "Reductionist breaks complex phenomena into simpler component parts, which closely matches the target's decomposition core, but it adds the claim that systems are explained in terms of basic elements, so it is a narrower, more committed version."
- benevolent / altruistic (subset, nearest): pass 1, Opus 5.5 2: "Both center on concern for others' wellbeing, but altruism adds selflessness over personal gain while benevolence adds ethical consideration and kindness toward all involved." / Sonnet 5.5 4: "Altruistic concern for others' welfare and selfless helping is nearly the same as benevolent's wellbeing-promoting kindness, with slightly more emphasis on selflessness."; pass 2, Opus 5.5 2: "Both are concern for others' welfare, but altruism adds selflessness over personal gain and benevolence adds ethical kindness toward all involved, so they share a core without either implying the other." / Sonnet 5.5 4: "Altruism is selfless concern for others' welfare and collective wellbeing, very close to benevolence's promotion of wellbeing out of kindness and compassion, though it adds the emphasis on putting others above personal gain."
- big-picture / holistic (subset, nearest): pass 2, Opus 5.5 2: "Holistic shares the systemic, whole-view thinking, but centers on interconnections rather than macro-level generality." / Sonnet 5.5 4: "Holistic means viewing whole systems and interconnections rather than isolated parts, which closely matches the systemic, broad-perspective core of big-picture."
- calm / temperate (subset, nearest): pass 2, Opus 5.5 3: "Temperate is calmness narrowed to how one holds beliefs and causes, avoiding fervor, so it is calm applied to one domain." / Sonnet 5.5 2: "Temperate is about holding beliefs coolly and distrusting fervor; it shares the cool, non-heated quality but is focused on moderation of convictions, not general steadiness."

Answers at 3 whose reason describes a two-sided overlap: 2; the first 6 pairs:

- indecisive / noncommittal (subset, nearest): Opus 5.5 pass 2, 4: "Both mean declining to take a position and laying out options without choosing, though indecisive adds expressed uncertainty while noncommittal stresses withholding one's own view."
- methodical / organized (subset, nearest): Sonnet 5.5 pass 1, 4: "Organized as described (a plan, one thing at a time in order, no losing the thread) closely matches methodical's plan-based, sequential approach, though it adds tidiness and lacks the finishing-each-stage and sticking-to-plan-under-surprise emphasis."

#### D2 (overlap_relation_implies)

Answers at 2 whose reason describes a containment: 32 (26 pairs); the first 6 pairs:

- agreeable / conciliatory (subset, nearest): Sonnet 5.5 pass 2, overlap: "Both center on seeking common ground and peaceful resolution, but conciliatory is actively making peace between conflicting parties, while agreeable is a broader harmony-keeping and conflict-avoiding disposition."
- anxious / neurotic (subset, nearest): Sonnet 5.5 pass 1, overlap: "Neurotic includes persistent anxiety and worry but adds emotional instability, reactivity and negative thinking, so it is broader than anxious and each can occur without the other's extras."
- anxious / restless (subset, nearest): Sonnet 5.5 pass 2, overlap: "Restless covers the fidgety, tense behaviour that is part of anxiety, but it needs no worry and anxiety needs no inability to settle, so they share only a part."
- benevolent / helpful (subset, nearest): Sonnet 5.5 pass 1, overlap: "Helpfulness is about actively and thoroughly meeting others' needs on request, while benevolence is a broader disposition of kindness and ethical concern; they share care for others' outcomes but differ in focus."
- careless / sloppy (subset, nearest): Sonnet 5.5 pass 1, overlap: "Sloppy is the slapdash, detail-neglecting side of careless work, but it lacks the broken deadlines and promises that careless includes."
- chaotic / disorganized (subset, nearest): Sonnet 5.5 pass 1, overlap: "Disorganized as described is scattered, unstructured communication, which shares the lack of order with chaotic but is narrower in focus and lacks the ignored rules and confusion left behind."; Opus 5.5 pass 2, overlap: "Disorganized is lack of structure narrowed to how information is presented, while chaotic is disorder across a whole way of living; a chaotic person need not ramble."

Pairs the two models put on different sides of 3: 37 (45 crossings over the passes); the first 6:

- agreeable / accommodating (subset, nearest): pass 1, Opus 5.5 contains: "Accommodating is harmony-seeking plus the specific move of yielding one's own position to others' needs, so every accommodating person is agreeable but not every agreeable person gives ground." / Sonnet 5.5 overlap: "Both involve keeping the peace and avoiding confrontation, but accommodating specifically adds yielding one's own position, while agreeable also covers seeking common ground and understanding."; pass 2, Opus 5.5 contains: "Accommodating is agreeableness with the added element of giving up one's own stance to keep the peace, so the accommodating person is agreeable but not the reverse." / Sonnet 5.5 overlap: "Accommodating means yielding positions to keep the peace, which shares agreeable's harmony-keeping and conflict avoidance but not its seeking of common ground."
- agreeable / conciliatory (subset, nearest): pass 2, Opus 5.5 contains: "Conciliatory is the harmony-seeking disposition applied specifically to making peace between conflicting parties, so a conciliatory person is agreeable but not every agreeable person actively mediates." / Sonnet 5.5 overlap: "Both center on seeking common ground and peaceful resolution, but conciliatory is actively making peace between conflicting parties, while agreeable is a broader harmony-keeping and conflict-avoiding disposition."
- analytical / reductionist (subset, nearest): pass 1, Opus 5.5 contains: "Reductionism is analytical breakdown plus the further commitment to explain wholes entirely by their basic elements." / Sonnet 5.5 overlap: "Reductionism is breaking complex things into simpler components, which is the core of analytical thinking, but it adds the commitment to explaining wholes in terms of basic elements."
- anxious / neurotic (subset, nearest): pass 1, Opus 5.5 contains: "Neurotic includes persistent anxiety and worry, then adds emotional instability and reactivity, so every neurotic persona is anxious but not the reverse." / Sonnet 5.5 overlap: "Neurotic includes persistent anxiety and worry but adds emotional instability, reactivity and negative thinking, so it is broader than anxious and each can occur without the other's extras."; pass 2, Opus 5.5 contains: "Neurotic includes persistent anxiety and worry but adds emotional instability and reactivity, so every neurotic person is anxious but not the reverse." / Sonnet 5.5 overlap: "Neurotic shares persistent worry and tension with anxious but adds emotional instability and reactivity, so each has something the other lacks."
- calm / temperate (subset, nearest): pass 1, Opus 5.5 contains: "Temperate is calmness narrowed to how one holds beliefs and causes, with an added distrust of fervor." / Sonnet 5.5 neighbours: "Temperate is coolness and measure about beliefs and causes, distrusting fervor; related to calm but a distinct focus on restraint of zeal rather than general steadiness."
- careless / sloppy (subset, nearest): pass 1, Opus 5.5 contains: "Sloppy covers the slapdash, unchecked work part of careless, but careless also includes letting responsibilities slide and breaking promises, so sloppy is careless narrowed to the quality of work." / Sonnet 5.5 overlap: "Sloppy is the slapdash, detail-neglecting side of careless work, but it lacks the broken deadlines and promises that careless includes."

Answers at 3 whose reason describes a two-sided overlap: 1; the first 6 pairs:

- extroverted / gregarious (subset, nearest): Opus 5.5 pass 1, contains: "Gregarious covers seeking out company. Extroversion adds being energized by people and drained by solitude, but gregarious adds nothing beyond that."

#### E2 (overlap_scope_implies)

Answers at 2 whose reason describes a containment: 31 (22 pairs); the first 6 pairs:

- agreeable / cooperative (subset, nearest): Opus 5.5 pass 1, 2: "Cooperation is part of agreeableness, but cooperative stresses teamwork and shared success rather than avoiding confrontation, and neither trait implies the other."
- benevolent / helpful (subset, nearest): Sonnet 5.5 pass 1, 2: "Helpful is active, task-focused assistance to meet others' needs, while benevolent is a broader disposition of kindness and ethics; they overlap but neither implies the other."; Sonnet 5.5 pass 2, 2: "Helpfulness is active, effective assistance toward others' success; benevolence is a broader disposition of kindness and ethical concern, so each has elements the other lacks."; Opus 5.5 pass 1, 2: "Helpful is benevolent care narrowed to actively and effectively meeting others' needs when asked, with an added focus on competence and thoroughness."
- calm / temperate (subset, nearest): Opus 5.5 pass 1, 2: "Temperate is calm narrowed to holding beliefs and causes without fervor, and it adds a distrust of zeal."; Opus 5.5 pass 2, 2: "Temperate is calmness narrowed to how one holds beliefs and causes, adding a distrust of fervor that calm lacks."
- careless / irresponsible (subset, nearest): Sonnet 5.5 pass 2, 2: "Irresponsible matches the target's letting responsibilities slide and breaking promises, but lacks the slapdash, detail-neglecting side; the target is broader on work quality."
- condescending / arrogant (subset, nearest): Sonnet 5.5 pass 2, 2: "Arrogance centres on overconfidence and dismissing others as inferior, which includes a condescending tone; the two share a core, but arrogance need not talk down to anyone and condescension need not rest on real overconfidence."; Opus 5.5 pass 1, 2: "Arrogance includes a condescending tone but adds excessive self-confidence and dismissing other viewpoints, while condescension's feigned helpfulness is not part of arrogance, so neither implies the other."
- cruel / malicious (control, nearest): Sonnet 5.5 pass 1, 2: "Malice involves deliberately causing harm and taking satisfaction in others' suffering, which overlaps with cruelty's pleasure in pain, but it also includes deceit and manipulation, and cruelty includes mere callousness."; Sonnet 5.5 pass 2, 2: "Both involve taking satisfaction in others' suffering, but malicious centres on deliberately causing harm and deception, while cruel includes callous indifference without intent to harm."

Pairs the two models put on different sides of 3: 34 (49 crossings over the passes); the first 6:

- agreeable / accommodating (subset, nearest): pass 1, Opus 5.5 3: "Accommodating is a stronger form of agreeableness, keeping the peace by actually giving up one's own stance, so an accommodating person is agreeable." / Sonnet 5.5 2: "Both involve keeping the peace by adjusting to others, but accommodating stresses yielding one's own position while agreeable is broader harmony-seeking, so each adds something the other lacks."
- analytical / reductionist (subset, nearest): pass 1, Opus 5.5 2: "Both break complex things into components, but reductionism adds explaining wholes by their basic elements, and analysis need not be reductive." / Sonnet 5.5 3: "Reductionism is breaking complex things into simpler component parts, which is the core of analytical decomposition, though narrower and focused on fundamentals."; pass 2, Opus 5.5 2: "Both break complex things into component parts, but reductionism adds the claim that wholes are explained by their basic elements, which analytical does not require." / Sonnet 5.5 3: "Reductionism is breaking complex phenomena into simpler component parts, which is the decomposing core of analytical thinking, narrowed to explaining wholes by their basic elements."
- benevolent / altruistic (subset, nearest): pass 1, Opus 5.5 2: "Both center on concern for others' wellbeing; altruistic adds selflessness and putting others over personal gain, while benevolent adds ethical consideration for all involved, so neither strictly implies the other." / Sonnet 5.5 3: "Both center on concern for others' welfare and promoting wellbeing; altruistic stresses selflessness, benevolent stresses kindness and goodwill, so the emphasis shifts."; pass 2, Opus 5.5 2: "Both are concern for others' wellbeing; altruistic stresses selflessness over personal gain, while benevolent stresses kindness and ethics, so each adds something the other lacks." / Sonnet 5.5 3: "Altruism is selfless concern for others' welfare and collective wellbeing, which closely matches benevolence, with a stronger emphasis on putting others before oneself."
- big-picture / holistic (subset, nearest): pass 2, Opus 5.5 2: "Holistic shares the systemic, whole-view thinking, but it adds a stress on interconnections, while big-picture adds macro-level themes." / Sonnet 5.5 3: "Holistic means viewing whole systems and interconnections rather than isolated parts, which closely matches the big-picture emphasis on systemic, macro-level thinking; a shift of emphasis."
- clannish / cliqueish (subset, nearest): pass 1, Opus 5.5 2: "Both share in-group loyalty with exclusion of outsiders, but cliqueish concerns a social circle and clannish concerns kin, and neither implies the other." / Sonnet 5.5 3: "Same in-group loyalty and exclusion of outsiders, with the group being a social circle rather than family, so the scope differs."; pass 2, Opus 5.5 2: "Both are the same exclusionary in-group loyalty, but cliqueish is based on a social circle rather than kinship, so they overlap without either implying the other." / Sonnet 5.5 3: "Same exclusionary in-group loyalty, applied to a social circle rather than family; a shift of the group type, narrower and more social."
- clannish / insular (subset, nearest): pass 1, Opus 5.5 2: "Both share in-group concern with indifference to outsiders, but insular centers on local community, clannish on kin, and neither implies the other." / Sonnet 5.5 3: "Same in-group-only concern and distance from outsiders, but the group is the local community rather than kin, so the scope differs."; pass 2, Opus 5.5 2: "Both show in-group-only concern and distance toward outsiders, but insular centres on local community and familiar group rather than kin, so neither implies the other." / Sonnet 5.5 3: "Same in-group-only concern with outsiders treated as irrelevant, but the group is the local community rather than kin, so it differs in scope."

Answers at 3 whose reason describes a two-sided overlap: 3; the first 6 pairs:

- quantitative / data-driven (subset, nearest): Sonnet 5.5 pass 1, 3: "Both stress numerical data and measurable evidence over subjective impressions; data-driven adds the idea of basing decisions and claims on that data, a slight shift of emphasis."; Sonnet 5.5 pass 2, 3: "Both stress numerical, measurable evidence over subjective description; data-driven adds relying on it to justify claims and decisions, a shift of emphasis."
- honorable / deontological (subset, deliberate_duplicate): Sonnet 5.5 pass 1, 3: "Both hold that some acts are wrong whatever the outcome; deontological is the abstract rule-based stance, while honorable is the personal willingness to accept loss to keep one's code, so the core is shared and each adds something."

