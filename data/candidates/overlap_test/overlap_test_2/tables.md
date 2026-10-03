# Overlap test: tables

409 pairs in 180 calls.  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Sonnet 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 87% | 324 | 86% | 100% | 0.04 | 0.92 (0.86) |

Categorical answers against the reference (rows: reference; columns: model):

- rubric A, Sonnet 5.5: numeric: numeric 324, opposite 8; opposite: opposite 77

## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | persona | 0.67 [0.57, 0.76] (n 233) | 0.67 [0.57, 0.76] (n 233) | 0.62 [0.51, 0.71] (n 199) | 0.62 [0.51, 0.71] (n 199) |
| A | Sonnet 5.5 | embedding | 0.71 [0.63, 0.77] (n 324) | 0.71 [0.63, 0.77] (n 324) | 0.60 [0.50, 0.68] (n 257) | 0.60 [0.50, 0.68] (n 257) |
| A | Opus 5.5 | persona | 0.67 [0.56, 0.76] (n 240) | 0.67 [0.56, 0.76] (n 240) | 0.62 [0.51, 0.72] (n 203) | 0.62 [0.51, 0.72] (n 203) |
| A | Opus 5.5 | embedding | 0.69 [0.62, 0.76] (n 332) | 0.69 [0.62, 0.76] (n 332) | 0.59 [0.49, 0.67] (n 261) | 0.59 [0.49, 0.67] (n 261) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|

## Known groups, rubric A

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.74 / 16% / 14% / 0% | 1.70 / 14% / 13% / 0% |
| drop_or_merge | 11 | 3.20 / 100% / 9% / 0% | 2.90 / 80% / 9% / 0% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0% / 0% | 2.33 / 33% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 2.00 / 0% / 0% / 0% |
| near_distinct | 34 | 1.56 / 16% / 26% / 0% | 1.52 / 11% / 21% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.14 / 0% / 7% / 0% | 0.13 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 13, 1 93, 2 119, 3 32, 4 4, opposite 39
- drop_or_merge: 2 2, 3 7, 4 1, opposite 1
- deliberate_duplicate: 2 2, 3 1
- duplicate: 2 1
- near_distinct: 0 2, 1 13, 2 9, 3 2, 4 1, opposite 7
- antonym: opposite 30
- random: 0 27, 1 2, 2 1

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 0% (0) | 21% (85) | 100% of 30 | 100% of 31 | 7% of 348 |
| A | Opus 5.5 | 409 | 0% (0) | 19% (77) | 100% of 30 | 100% of 31 | 5% of 348 |

## Rubric A (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 42 | 0.114 | 16 | 0.223 |
| 1 | 108 | 0.328 | 87 | 0.439 |
| 2 | 134 | 0.406 | 102 | 0.602 |
| 3 | 42 | 0.552 | 29 | 0.818 |
| 4 | 6 | 0.621 | 6 | 0.873 |
| opposite | 77 | 0.399 | 40 | 0.033 |

## The same pair in two calls

- rubric A: Sonnet 5.5 32 of 38 the same; Opus 5.5 32 of 38 the same
- rubric B: 
