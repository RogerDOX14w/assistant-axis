# Overlap test: tables

409 pairs in 180 calls.  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Sonnet 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| C | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| C | Sonnet 5.5 | 409 / 409 | 1.0000 | 406 / 409 (0.9927) |
| D | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| D | Sonnet 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| E | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| E | Sonnet 5.5 | 409 / 409 | 1.0000 | 406 / 409 (0.9927) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).  Rubric C on its own 0-5 scale; rubric D's relations as ranks, different 0, neighbours 1, overlap 2, contains 3, variant 4, same 5 (C's rungs).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 87% | 322 | 86% | 100% | 0.06 | 0.93 (0.87) |
| C | Sonnet 5.5 | 409 | 83% | 322 | 81% | 98% | -0.01 | 0.90 (0.82) |
| D | Sonnet 5.5 | 409 | 84% | 325 | 82% | 97% | 0.01 | 0.87 (0.80) |
| E | Sonnet 5.5 | 409 | 86% | 325 | 85% | 100% | -0.01 | 0.92 (0.86) |

Categorical answers against the reference (rows: reference; columns: model):

- rubric A, Sonnet 5.5: numeric: numeric 322, opposite 9; opposite: opposite 77, numeric 1
- rubric C, Sonnet 5.5: numeric: numeric 322, opposite 7; opposite: opposite 79, numeric 1
- rubric D, Sonnet 5.5: numeric: numeric 325, opposite 8; opposite: opposite 76
- rubric E, Sonnet 5.5: numeric: numeric 325, opposite 7; opposite: opposite 77

## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | persona | 0.66 [0.56, 0.75] (n 232) | 0.66 [0.56, 0.75] (n 232) | 0.61 [0.49, 0.70] (n 198) | 0.61 [0.49, 0.70] (n 198) |
| A | Sonnet 5.5 | embedding | 0.69 [0.61, 0.76] (n 323) | 0.69 [0.61, 0.76] (n 323) | 0.59 [0.49, 0.67] (n 256) | 0.59 [0.49, 0.67] (n 256) |
| A | Opus 5.5 | persona | 0.69 [0.59, 0.77] (n 239) | 0.69 [0.59, 0.77] (n 239) | 0.64 [0.52, 0.73] (n 202) | 0.64 [0.52, 0.73] (n 202) |
| A | Opus 5.5 | embedding | 0.71 [0.63, 0.77] (n 331) | 0.71 [0.63, 0.77] (n 331) | 0.62 [0.53, 0.70] (n 260) | 0.62 [0.53, 0.70] (n 260) |
| C | Sonnet 5.5 | persona | 0.67 [0.57, 0.76] (n 232) | 0.67 [0.57, 0.76] (n 232) | 0.62 [0.50, 0.71] (n 198) | 0.62 [0.50, 0.71] (n 198) |
| C | Sonnet 5.5 | embedding | 0.66 [0.57, 0.73] (n 323) | 0.66 [0.57, 0.73] (n 323) | 0.52 [0.41, 0.62] (n 256) | 0.52 [0.41, 0.62] (n 256) |
| C | Opus 5.5 | persona | 0.63 [0.52, 0.72] (n 237) | 0.63 [0.52, 0.72] (n 237) | 0.57 [0.45, 0.67] (n 200) | 0.57 [0.45, 0.67] (n 200) |
| C | Opus 5.5 | embedding | 0.68 [0.59, 0.74] (n 329) | 0.68 [0.59, 0.74] (n 329) | 0.55 [0.44, 0.63] (n 258) | 0.55 [0.44, 0.63] (n 258) |
| D | Sonnet 5.5 | persona | 0.58 [0.46, 0.67] (n 233) | 0.58 [0.46, 0.67] (n 233) | 0.51 [0.38, 0.61] (n 198) | 0.51 [0.38, 0.61] (n 198) |
| D | Sonnet 5.5 | embedding | 0.64 [0.56, 0.71] (n 325) | 0.64 [0.56, 0.71] (n 325) | 0.48 [0.37, 0.57] (n 256) | 0.48 [0.37, 0.57] (n 256) |
| D | Opus 5.5 | persona | 0.59 [0.46, 0.68] (n 240) | 0.59 [0.46, 0.68] (n 240) | 0.52 [0.39, 0.63] (n 203) | 0.52 [0.39, 0.63] (n 203) |
| D | Opus 5.5 | embedding | 0.64 [0.55, 0.72] (n 333) | 0.64 [0.55, 0.72] (n 333) | 0.50 [0.39, 0.61] (n 262) | 0.50 [0.39, 0.61] (n 262) |
| E | Sonnet 5.5 | persona | 0.68 [0.57, 0.77] (n 234) | 0.68 [0.57, 0.77] (n 234) | 0.62 [0.51, 0.72] (n 198) | 0.62 [0.51, 0.72] (n 198) |
| E | Sonnet 5.5 | embedding | 0.70 [0.63, 0.77] (n 325) | 0.70 [0.63, 0.77] (n 325) | 0.60 [0.50, 0.68] (n 256) | 0.60 [0.50, 0.68] (n 256) |
| E | Opus 5.5 | persona | 0.68 [0.56, 0.76] (n 240) | 0.68 [0.56, 0.76] (n 240) | 0.62 [0.50, 0.72] (n 203) | 0.62 [0.50, 0.72] (n 203) |
| E | Opus 5.5 | embedding | 0.69 [0.61, 0.76] (n 332) | 0.69 [0.61, 0.76] (n 332) | 0.59 [0.49, 0.67] (n 261) | 0.59 [0.49, 0.67] (n 261) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|

## Known groups, rubric A

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.77 / 18% / 15% / 0% | 1.68 / 15% / 13% / 0% |
| drop_or_merge | 11 | 3.20 / 100% / 9% / 0% | 3.10 / 80% / 9% / 0% |
| deliberate_duplicate | 3 | 2.33 / 33% / 0% / 0% | 2.33 / 33% / 0% / 0% |
| duplicate | 1 | 2.00 / 0% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.52 / 16% / 26% / 0% | 1.52 / 15% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.14 / 0% / 7% / 0% | 0.17 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 15, 1 96, 2 111, 3 33, 4 5, opposite 40
- drop_or_merge: 2 2, 3 5, 4 3, opposite 1
- deliberate_duplicate: 2 2, 3 1
- duplicate: 3 1
- near_distinct: 0 3, 1 12, 2 8, 3 3, 4 1, opposite 7
- antonym: opposite 30
- random: 0 26, 1 3, 2 1

## Known groups, rubric C

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column. On the decision scale (rubric A's 0-4; C: 5 -> 4, 4 -> 3, 3 -> 3).

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.64 / 11% / 15% / 0% | 1.68 / 13% / 14% / 0% |
| drop_or_merge | 11 | 3.20 / 90% / 9% / 0% | 3.20 / 80% / 9% / 0% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0% / 0% | 2.00 / 0% / 0% / 0% |
| duplicate | 1 | 2.00 / 0% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.48 / 12% / 26% / 0% | 1.48 / 7% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.11 / 0% / 7% / 0% | 0.13 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 15, 1 90, 2 119, 3 30, 4 4, opposite 42
- drop_or_merge: 2 2, 3 4, 4 4, opposite 1
- deliberate_duplicate: 2 3
- duplicate: 3 1
- near_distinct: 0 2, 1 13, 2 10, 3 1, 4 1, opposite 7
- antonym: opposite 30
- random: 0 26, 1 4

## Known groups, rubric D

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column. On the decision scale (rubric A's 0-4; D: same 4, variant 3, contains 3, overlap 2, neighbours 1, different 0).

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.70 / 7% / 15% / 0% | 1.68 / 13% / 13% / 0% |
| drop_or_merge | 11 | 3.10 / 70% / 9% / 0% | 3.10 / 70% / 9% / 0% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0% / 0% | 2.00 / 0% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.48 / 8% / 26% / 0% | 1.37 / 7% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.13 / 0% / 0% / 0% | 0.10 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 16, 1 92, 2 121, 3 27, 4 6, opposite 38
- drop_or_merge: 2 3, 3 3, 4 4, opposite 1
- deliberate_duplicate: 2 3
- duplicate: 3 1
- near_distinct: 0 4, 1 12, 2 9, 3 1, 4 1, opposite 7
- antonym: opposite 30
- random: 0 27, 1 3

## Known groups, rubric E

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.77 / 17% / 15% / 0% | 1.75 / 16% / 13% / 0% |
| drop_or_merge | 11 | 3.00 / 80% / 9% / 0% | 3.10 / 80% / 9% / 0% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0% / 0% | 2.33 / 33% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.50 / 19% / 24% / 0% | 1.52 / 15% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.14 / 0% / 3% / 0% | 0.13 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 14, 1 84, 2 120, 3 38, 4 5, opposite 39
- drop_or_merge: 2 2, 3 5, 4 3, opposite 1
- deliberate_duplicate: 2 2, 3 1
- duplicate: 3 1
- near_distinct: 0 3, 1 12, 2 8, 3 3, 4 1, opposite 7
- antonym: opposite 30
- random: 0 27, 1 2, 2 1

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 0% (0) | 21% (86) | 100% of 30 | 100% of 31 | 7% of 348 |
| A | Opus 5.5 | 409 | 0% (0) | 19% (78) | 100% of 30 | 100% of 31 | 5% of 348 |
| C | Sonnet 5.5 | 409 | 0% (0) | 21% (86) | 100% of 30 | 100% of 31 | 7% of 348 |
| C | Opus 5.5 | 409 | 0% (0) | 20% (80) | 100% of 30 | 100% of 31 | 6% of 348 |
| D | Sonnet 5.5 | 409 | 0% (0) | 20% (84) | 100% of 30 | 100% of 31 | 7% of 348 |
| D | Opus 5.5 | 409 | 0% (0) | 19% (76) | 100% of 30 | 100% of 31 | 4% of 348 |
| E | Sonnet 5.5 | 409 | 0% (0) | 20% (84) | 100% of 30 | 100% of 31 | 7% of 348 |
| E | Opus 5.5 | 409 | 0% (0) | 19% (77) | 100% of 30 | 100% of 31 | 5% of 348 |

## Rubric A (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 44 | 0.121 | 19 | 0.215 |
| 1 | 111 | 0.329 | 87 | 0.450 |
| 2 | 124 | 0.407 | 96 | 0.604 |
| 3 | 43 | 0.540 | 28 | 0.813 |
| 4 | 9 | 0.627 | 9 | 0.865 |
| opposite | 78 | 0.399 | 41 | 0.041 |

## Rubric C (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 43 | 0.123 | 18 | 0.235 |
| 1 | 107 | 0.331 | 85 | 0.462 |
| 2 | 134 | 0.409 | 102 | 0.616 |
| 3 | 23 | 0.486 | 12 | 0.710 |
| 4 | 13 | 0.618 | 11 | 0.825 |
| 5 | 9 | 0.627 | 9 | 0.865 |
| opposite | 80 | 0.398 | 43 | 0.042 |

## Rubric D (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| different | 47 | 0.122 | 19 | 0.207 |
| neighbours | 107 | 0.349 | 84 | 0.485 |
| overlap | 136 | 0.404 | 106 | 0.586 |
| contains | 22 | 0.501 | 12 | 0.773 |
| variant | 10 | 0.585 | 8 | 0.833 |
| same | 11 | 0.639 | 11 | 0.859 |
| opposite | 76 | 0.399 | 40 | 0.033 |

## Rubric E (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 44 | 0.116 | 17 | 0.197 |
| 1 | 98 | 0.329 | 80 | 0.441 |
| 2 | 133 | 0.400 | 103 | 0.597 |
| 3 | 48 | 0.528 | 31 | 0.782 |
| 4 | 9 | 0.627 | 9 | 0.865 |
| opposite | 77 | 0.399 | 40 | 0.033 |

## The same pair in two calls

- rubric A: Sonnet 5.5 33 of 38 the same; Opus 5.5 30 of 38 the same
- rubric C: Sonnet 5.5 31 of 38 the same; Opus 5.5 30 of 38 the same
- rubric D: Sonnet 5.5 32 of 38 the same; Opus 5.5 30 of 38 the same
- rubric E: Sonnet 5.5 30 of 38 the same; Opus 5.5 30 of 38 the same

## The arms experiment: 2 passes, decision scale, cut-off 3

Pass 2 sent the same calls with the listed traits in a fresh order: 86 of 180 calls kept pass 1's order by chance (55 of them list one trait); 226 of 409 pairs went out under another id.

The decision scale is rubric A's 0-4 with "opposite" and "unsure": C maps 5 -> 4, 4 -> 3, 3 -> 3; D maps same 4, variant 3, contains 3, overlap 2, neighbours 1, different 0.  Covered means 3 or more on it ("opposite" is not covered, "unsure" neither), over the 300 nearest-neighbour pairs.  The native scale is each rubric's own answers (C 0-5; D's relations ranked different 0 ... same 5, as C's rungs).  Exact agreement counts every answer, categories included.

### Cross-arm table

| arm | model | consistency, exact (native) | consistency, exact (decision) | between-pass flips at 3 | agreement, exact, pass 1 (native / decision) | agreement, pass 2 | covered at 3, pass 1 | targets covered, pass 1 | between-model crossings at 3 (pass 1 / pass 2) |
|---|---|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 89% (409) | 89% | 10 of 300 | 87% / 87% | 85% / 85% | 46 of 300 (15%) | 39 of 100 | 8 of 300 / 14 of 300 |
| A | Opus 5.5 | 92% (409) | 92% | 4 of 300 | 87% / 87% | 85% / 85% | 38 of 300 (13%) | 32 of 100 | 8 of 300 / 14 of 300 |
| C | Sonnet 5.5 | 90% (409) | 90% | 7 of 300 | 83% / 84% | 83% / 84% | 28 of 300 (9%) | 21 of 100 | 16 of 300 / 20 of 300 |
| C | Opus 5.5 | 85% (409) | 86% | 11 of 300 | 83% / 84% | 83% / 84% | 34 of 300 (11%) | 28 of 100 | 16 of 300 / 20 of 300 |
| D | Sonnet 5.5 | 90% (409) | 90% | 6 of 300 | 84% / 84% | 79% / 79% | 18 of 300 (6%) | 16 of 100 | 19 of 300 / 20 of 300 |
| D | Opus 5.5 | 87% (409) | 87% | 5 of 300 | 84% / 84% | 79% / 79% | 33 of 300 (11%) | 27 of 100 | 19 of 300 / 20 of 300 |
| E | Sonnet 5.5 | 90% (409) | 90% | 8 of 300 | 86% / 86% | 84% / 84% | 44 of 300 (15%) | 36 of 100 | 13 of 300 / 19 of 300 |
| E | Opus 5.5 | 89% (409) | 89% | 6 of 300 | 86% / 86% | 84% / 84% | 43 of 300 (14%) | 34 of 100 | 13 of 300 / 19 of 300 |

Agreement is each model against the other one (Sonnet 5.5 against Opus 5.5 in this experiment); crossings are the nearest pairs the two models put on different sides of the cut-off, flips the nearest pairs one model put on different sides in its two passes.

### Parse rates by pass

| rubric | model | pass | ok / total | first attempt |
|---|---|---|---|---|
| A | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| A | Sonnet 5.5 | 1 | 409 / 409 | 409 / 409 |
| C | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| C | Sonnet 5.5 | 1 | 409 / 409 | 406 / 409 |
| D | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| D | Sonnet 5.5 | 1 | 409 / 409 | 409 / 409 |
| E | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| E | Sonnet 5.5 | 1 | 409 / 409 | 406 / 409 |
| A | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| A | Sonnet 5.5 | 2 | 409 / 409 | 406 / 409 |
| C | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| C | Sonnet 5.5 | 2 | 409 / 409 | 406 / 409 |
| D | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| D | Sonnet 5.5 | 2 | 409 / 409 | 409 / 409 |
| E | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| E | Sonnet 5.5 | 2 | 409 / 409 | 409 / 409 |

### Arm A: overlap_concept (concept similarity)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 89% | 100% | 0.00 | 0.93 | 89% | 100% | 10 of 300 (8 covered in pass 1 only, 2 in pass 2 only) |
| Opus 5.5 | 409 | 92% | 100% | -0.00 | 0.95 | 92% | 100% | 4 of 300 (2 covered in pass 1 only, 2 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 5, 0/opposite 2, 1/2 23, 1/opposite 1, 2/3 13, 3/4 1 (42 of 45 between neighbouring points); decision: 0/1 5, 0/opposite 2, 1/2 23, 1/opposite 1, 2/3 13, 3/4 1
- Opus 5.5: 0/1 5, 1/2 23, 1/opposite 1, 2/3 4, 3/4 1 (33 of 34 between neighbouring points); decision: 0/1 5, 1/2 23, 1/opposite 1, 2/3 4, 3/4 1

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 95% / 95% (55) | 96% / 96% (84) | 86% / 86% (270) |
| Opus 5.5 | 98% / 98% (55) | 98% / 98% (84) | 89% / 89% (270) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / accommodating: 2, 3
- agreeable / conciliatory: 3, 2
- analytical / reductionist: 2, 3
- careless / sloppy: 3, 2
- cruel / callous: 3, 2
- flippant / irreverent: 3, 2
- nationalist / regionalist: 3, 2
- nationalist / civilizationist: 3, 2
- theatrical / melodramatic: 3, 2
- zealous / passionate: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: 3, 2
- methodical / organized: 3, 2
- pacifist / peaceful: 2, 3
- provocative / edgy: 2, 3

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 409 | 87% | 100% | 0.06 | 0.93 | 87% | 100% | 8 of 300 (0 Opus 5.5 covered only, 8 Sonnet 5.5 covered only) |
| 2 | 409 | 85% | 100% | 0.06 | 0.91 | 85% | 100% | 14 of 300 (6 Opus 5.5 covered only, 8 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 7, 0/opposite 1, 1/2 24, 1/opposite 9, 2/3 11, 3/4 2
- pass 2: 0/1 2, 1/2 30, 1/opposite 8, 2/3 18, 3/4 2

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- calm / placid: 2, 3
- flippant / irreverent: 2, 3
- formalist / ritualistic: 2, 3
- innovative / creative: 2, 3
- provocative / edgy: 2, 3
- zealous / passionate: 2, 3

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / accommodating: 2, 3
- analytical / reductionist: 2, 3
- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- calm / placid: 2, 3
- careless / sloppy: 3, 2
- cruel / callous: 3, 2
- formalist / ritualistic: 2, 3
- innovative / creative: 2, 3
- methodical / organized: 2, 3
- nationalist / regionalist: 3, 2
- nationalist / civilizationist: 3, 2
- pacifist / peaceful: 3, 2
- theatrical / melodramatic: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 300 | 46 | 15% | 39 of 100 | 44 | 0 |
| Sonnet 5.5 | 2 | 300 | 40 | 13% | 35 of 100 | 45 | 0 |
| Opus 5.5 | 1 | 300 | 38 | 13% | 32 of 100 | 40 | 0 |
| Opus 5.5 | 2 | 300 | 38 | 13% | 32 of 100 | 39 | 0 |

Kinds of difference the reasons of 3s name (not asked: rubric A's 3s, as a control; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 54 | 2 | 3 | 1 | 1 | 20 | 28 (52%) | 1 |
| Sonnet 5.5 | 2 | 48 | 5 | 2 | 3 | 1 | 15 | 27 (56%) | 5 |
| Opus 5.5 | 1 | 43 | 5 | 0 | 4 | 3 | 13 | 20 (46%) | 2 |
| Opus 5.5 | 2 | 44 | 6 | 2 | 3 | 1 | 13 | 20 (46%) | 1 |

### Arm C: overlap_six (six rungs)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 90% | 98% | -0.01 | 0.93 | 90% | 100% | 7 of 300 (4 covered in pass 1 only, 3 in pass 2 only) |
| Opus 5.5 | 409 | 85% | 98% | 0.03 | 0.91 | 86% | 100% | 11 of 300 (4 covered in pass 1 only, 7 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 5, 0/opposite 2, 1/2 23, 1/opposite 1, 2/3 2, 2/4 7, 4/5 2 (32 of 42 between neighbouring points); decision: 0/1 5, 0/opposite 2, 1/2 23, 1/opposite 1, 2/3 9, 3/4 2
- Opus 5.5: 0/1 6, 1/2 33, 1/opposite 4, 2/3 5, 2/4 6, 3/4 1, 4/5 5 (50 of 60 between neighbouring points); decision: 0/1 6, 1/2 33, 1/opposite 4, 2/3 11, 3/4 5

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 96% / 96% (55) | 95% / 95% (84) | 87% / 87% (270) |
| Opus 5.5 | 96% / 96% (55) | 90% / 90% (84) | 81% / 82% (270) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- calm / serene: 4, 2
- entertaining / playful: 2, 4
- hedonistic / self-indulgent: 4, 2
- quantitative / data-driven: 2, 4
- sarcastic / sardonic: 2, 4
- sarcastic / ironic: 3, 2
- theatrical / melodramatic: 4, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- critical / skeptical: 2, 3
- cruel / callous: 3, 2
- entertaining / playful: 2, 4
- environmental / ecocentric: 3, 2
- grandiose / self-aggrandizing: 3, 2
- honest / transparent: 2, 4
- indecisive / noncommittal: 2, 4
- independent / self-reliant: 2, 4
- perfectionist / meticulous: 3, 2
- theatrical / dramatic: 2, 4
- theatrical / melodramatic: 2, 4

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 409 | 83% | 98% | -0.01 | 0.90 | 84% | 100% | 16 of 300 (11 Opus 5.5 covered only, 5 Sonnet 5.5 covered only) |
| 2 | 409 | 83% | 96% | -0.06 | 0.88 | 84% | 100% | 20 of 300 (15 Opus 5.5 covered only, 5 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 8, 0/opposite 1, 1/2 28, 1/opposite 7, 2/3 11, 2/4 8, 3/4 3, 4/5 2
- pass 2: 0/1 6, 1/2 30, 1/opposite 7, 2/3 9, 2/4 12, 3/4 3, 4/5 3

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: 3, 2
- anxious / neurotic: 3, 2
- careless / sloppy: 3, 2
- chaotic / disorganized: 3, 2
- compassionate / empathetic: 2, 4
- confident / overconfident: 4, 2
- cruel / callous: 3, 2
- environmental / ecocentric: 3, 2
- extroverted / gregarious: 2, 4
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- honest / transparent: 2, 4
- perfectionist / meticulous: 3, 2
- theatrical / dramatic: 2, 4
- theatrical / melodramatic: 2, 4
- wry / witty: 3, 2

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: 3, 2
- anxious / neurotic: 3, 2
- calm / serene: 4, 2
- careless / sloppy: 3, 2
- chaotic / disorganized: 3, 2
- compassionate / empathetic: 2, 4
- confident / overconfident: 4, 2
- critical / skeptical: 3, 2
- extroverted / gregarious: 2, 4
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- grandiose / self-aggrandizing: 2, 4
- hedonistic / self-indulgent: 4, 2
- indecisive / noncommittal: 4, 2
- independent / self-reliant: 4, 2
- quantitative / data-driven: 2, 4
- sarcastic / sardonic: 2, 4
- sarcastic / ironic: 3, 2
- theatrical / melodramatic: 4, 2
- wry / witty: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 300 | 28 | 9% | 21 of 100 | 44 | 0 |
| Sonnet 5.5 | 2 | 300 | 27 | 9% | 21 of 100 | 45 | 0 |
| Opus 5.5 | 1 | 300 | 34 | 11% | 28 of 100 | 42 | 0 |
| Opus 5.5 | 2 | 300 | 37 | 12% | 28 of 100 | 40 | 0 |

### Arm D: overlap_relation (relation first)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 90% | 99% | -0.03 | 0.93 | 90% | 100% | 6 of 300 (3 covered in pass 1 only, 3 in pass 2 only) |
| Opus 5.5 | 409 | 87% | 99% | -0.02 | 0.92 | 87% | 100% | 5 of 300 (3 covered in pass 1 only, 2 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: different/neighbours 8, neighbours/overlap 25, neighbours/opposite 2, overlap/contains 4, overlap/variant 3 (37 of 42 between neighbouring points); decision: 0/1 8, 1/2 25, 1/opposite 2, 2/3 7
- Opus 5.5: different/neighbours 8, neighbours/overlap 38, neighbours/opposite 2, overlap/contains 2, overlap/variant 3, overlap/same 1, variant/same 1 (49 of 55 between neighbouring points); decision: 0/1 8, 1/2 38, 1/opposite 2, 2/3 5, 2/4 1, 3/4 1

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 96% / 96% (55) | 92% / 92% (84) | 88% / 88% (270) |
| Opus 5.5 | 96% / 96% (55) | 95% / 95% (84) | 82% / 82% (270) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- compassionate / empathetic: variant, overlap
- confident / overconfident: overlap, variant
- ecocentric / environmental: contains, overlap
- entertaining / witty: contains, overlap
- perfectionist / detail-oriented: overlap, contains
- theatrical / dramatic: overlap, variant

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: contains, overlap
- entertaining / playful: overlap, variant
- honest / transparent: overlap, variant
- honest / intellectually honest: contains, overlap
- theatrical / melodramatic: variant, overlap

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 409 | 84% | 97% | 0.01 | 0.87 | 84% | 99% | 19 of 300 (17 Opus 5.5 covered only, 2 Sonnet 5.5 covered only) |
| 2 | 409 | 79% | 97% | 0.00 | 0.84 | 79% | 99% | 20 of 300 (17 Opus 5.5 covered only, 3 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: different/neighbours 5, different/opposite 1, neighbours/overlap 31, neighbours/opposite 7, overlap/contains 12, overlap/variant 5, overlap/same 2, contains/variant 1, contains/same 2, variant/same 1
- pass 2: different/neighbours 8, neighbours/overlap 44, neighbours/opposite 8, overlap/contains 14, overlap/variant 5, overlap/same 3, contains/variant 1, contains/same 2, variant/same 2

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: contains, overlap
- anxious / neurotic: contains, overlap
- calm / serene: variant, overlap
- careless / sloppy: contains, overlap
- compassionate / empathetic: overlap, variant
- confident / overconfident: variant, overlap
- cruel / callous: contains, overlap
- dramatic / theatrical: same, overlap
- ecocentric / environmental: overlap, contains
- environmental / ecocentric: contains, overlap
- gluttonous / self-indulgent: contains, overlap
- goofy / playful: contains, overlap
- hedonistic / self-indulgent: variant, overlap
- honest / truthful: same, overlap
- perfectionist / meticulous: contains, overlap
- sarcastic / ironic: contains, overlap
- systems-thinker / holistic: contains, overlap
- theatrical / melodramatic: variant, overlap
- wry / witty: contains, overlap

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- anxious / neurotic: contains, overlap
- calm / serene: variant, overlap
- careless / sloppy: contains, overlap
- cruel / callous: contains, overlap
- dramatic / theatrical: same, overlap
- entertaining / playful: variant, overlap
- entertaining / witty: contains, overlap
- environmental / ecocentric: contains, overlap
- gluttonous / self-indulgent: contains, overlap
- goofy / playful: contains, overlap
- hedonistic / self-indulgent: variant, overlap
- honest / truthful: same, overlap
- honest / transparent: variant, overlap
- honest / intellectually honest: overlap, contains
- perfectionist / meticulous: contains, overlap
- perfectionist / detail-oriented: overlap, contains
- sarcastic / ironic: contains, overlap
- systems-thinker / holistic: contains, overlap
- theatrical / dramatic: overlap, variant
- wry / witty: contains, overlap

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 300 | 18 | 6% | 16 of 100 | 44 | 0 |
| Sonnet 5.5 | 2 | 300 | 18 | 6% | 16 of 100 | 45 | 0 |
| Opus 5.5 | 1 | 300 | 33 | 11% | 27 of 100 | 38 | 0 |
| Opus 5.5 | 2 | 300 | 32 | 11% | 25 of 100 | 40 | 0 |

Relations named (all pairs):

| model | pass | same | variant | contains | overlap | neighbours | different | opposite | unsure | unparsed |
|---|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 10 | 9 | 9 | 170 | 82 | 45 | 84 | 0 | 0 |
| Sonnet 5.5 | 2 | 10 | 10 | 7 | 164 | 87 | 47 | 84 | 0 | 0 |
| Opus 5.5 | 1 | 11 | 10 | 22 | 136 | 107 | 47 | 76 | 0 | 0 |
| Opus 5.5 | 2 | 13 | 10 | 20 | 126 | 115 | 47 | 78 | 0 | 0 |

The wider of a "contains":

| model | pass | contains | wider: target | wider: listed | missing | not target or listed | wider given with another relation | alias spellings |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 9 | 7 | 2 | 0 | 0 | 86 | 0 |
| Sonnet 5.5 | 2 | 7 | 5 | 2 | 0 | 0 | 64 | 0 |
| Opus 5.5 | 1 | 22 | 13 | 9 | 0 | 0 | 0 | 0 |
| Opus 5.5 | 2 | 20 | 10 | 10 | 0 | 0 | 0 | 0 |

- Sonnet 5.5, pass 1 against pass 2: 6 pairs "contains" in both, the same wider 6, the other 0, unknown 0
- Opus 5.5, pass 1 against pass 2: 20 pairs "contains" in both, the same wider 19, the other 1, unknown 0
- Sonnet 5.5 against Opus 5.5, pass 1: 8 pairs "contains" for both, the same wider 8, the other 0, unknown 0
- Sonnet 5.5 against Opus 5.5, pass 2: 5 pairs "contains" for both, the same wider 5, the other 0, unknown 0

### Arm E: overlap_scope (Roger's line 3)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 90% | 100% | 0.02 | 0.94 | 90% | 100% | 8 of 300 (3 covered in pass 1 only, 5 in pass 2 only) |
| Opus 5.5 | 409 | 89% | 100% | -0.02 | 0.93 | 89% | 100% | 6 of 300 (2 covered in pass 1 only, 4 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 7, 1/2 19, 2/3 10, 3/4 4 (40 of 40 between neighbouring points); decision: 0/1 7, 1/2 19, 2/3 10, 3/4 4
- Opus 5.5: 0/1 5, 1/2 31, 2/3 7, 3/4 2 (45 of 45 between neighbouring points); decision: 0/1 5, 1/2 31, 2/3 7, 3/4 2

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 98% / 98% (55) | 98% / 98% (84) | 86% / 86% (270) |
| Opus 5.5 | 98% / 98% (55) | 95% / 95% (84) | 85% / 85% (270) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: 3, 2
- analytical / reductionist: 2, 3
- clannish / cliqueish: 2, 3
- honest / intellectually honest: 2, 3
- perfectionist / detail-oriented: 2, 3
- sarcastic / sardonic: 2, 3
- theatrical / melodramatic: 3, 2
- zealous / passionate: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- benevolent / altruistic: 2, 3
- edgy / provocative: 3, 2
- innovative / futuristic: 2, 3
- pacifist / peaceful: 2, 3
- quantitative / data-driven: 3, 2
- sarcastic / ironic: 2, 3

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 409 | 86% | 100% | -0.01 | 0.92 | 86% | 100% | 13 of 300 (6 Opus 5.5 covered only, 7 Sonnet 5.5 covered only) |
| 2 | 409 | 84% | 100% | 0.04 | 0.91 | 84% | 100% | 19 of 300 (9 Opus 5.5 covered only, 10 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 5, 0/opposite 1, 1/2 26, 1/opposite 6, 2/3 15, 3/4 3
- pass 2: 0/1 5, 0/opposite 1, 1/2 28, 1/opposite 6, 2/3 22, 3/4 3

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- benevolent / altruistic: 2, 3
- big-picture / holistic: 2, 3
- chaotic / disorganized: 3, 2
- environmental / ecocentric: 2, 3
- formalist / ritualistic: 2, 3
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- honest / intellectually honest: 3, 2
- indecisive / noncommittal: 3, 2
- methodical / organized: 2, 3
- provocative / edgy: 2, 3
- sarcastic / sardonic: 3, 2
- zealous / passionate: 2, 3

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: 3, 2
- analytical / reductionist: 2, 3
- big-picture / holistic: 2, 3
- chaotic / disorganized: 3, 2
- clannish / cliqueish: 2, 3
- edgy / provocative: 2, 3
- environmental / ecocentric: 2, 3
- formalist / ritualistic: 2, 3
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- indecisive / noncommittal: 3, 2
- innovative / futuristic: 3, 2
- methodical / organized: 2, 3
- pacifist / peaceful: 3, 2
- perfectionist / detail-oriented: 2, 3
- provocative / edgy: 2, 3
- quantitative / data-driven: 2, 3
- sarcastic / ironic: 3, 2
- theatrical / melodramatic: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 300 | 44 | 15% | 36 of 100 | 44 | 0 |
| Sonnet 5.5 | 2 | 300 | 46 | 15% | 37 of 100 | 44 | 0 |
| Opus 5.5 | 1 | 300 | 43 | 14% | 34 of 100 | 39 | 0 |
| Opus 5.5 | 2 | 300 | 45 | 15% | 35 of 100 | 39 | 0 |

Kinds of difference the reasons of 3s name (asked of a 3's reason; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 50 | 11 | 4 | 9 | 4 | 20 | 6 (12%) | 3 |
| Sonnet 5.5 | 2 | 50 | 14 | 6 | 7 | 4 | 19 | 6 (12%) | 4 |
| Opus 5.5 | 1 | 48 | 14 | 11 | 7 | 5 | 19 | 1 (2%) | 7 |
| Opus 5.5 | 2 | 47 | 13 | 8 | 8 | 2 | 18 | 2 (4%) | 4 |

### Arm A, pass 1, against overlap_test_1 (rubric A, the same pairs and user turns)

overlap_test_1 is the reference (mean difference: this run minus overlap_test_1).

| model | both answered | exact (native) | within one | mean diff | kappa | flips at 3, nearest |
|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 92% | 100% | 0.02 | 0.95 | 6 of 300 |
| Opus 5.5 | 409 | 95% | 100% | 0.00 | 0.97 | 2 of 300 |

Where they differ, by the two answers:

- Sonnet 5.5: 0/1 5, 1/2 19, 2/3 8, 3/4 1
- Opus 5.5: 0/1 5, 1/2 8, 1/opposite 1, 2/3 3, 3/4 3
