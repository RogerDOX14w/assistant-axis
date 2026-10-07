# Overlap test: tables

409 pairs in 180 calls.  (Rubric A went out one pair per call, 409 calls a stage; the calls here are the pair set's.)  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Round 3: rubric A version 6, one pair per call

Versions compared on the same pairs: version 6: rubric A version 6, single form, run `overlap_arms_4`.  Version 6 went out one pair per call, and its second pass sent the identical prompts (there is no list to reorder), so the agreement between its passes is sampling noise alone; version 4's and A2's second passes reshuffled their lists, so their like-for-like figure is the one on the pairs whose prompt came out identical (a call of one trait, or a list that shuffled into the same order).  Decision scale: rubric A's own; cut-off 3.  Crossings, flips and shares count every pair of the population named.  M3's rule: Sonnet 5.5 reads every pair; above 3 is cut, below it (or "opposite") kept; at 3 (or "unsure") the pair goes to Opus 5.5, and is kept if Opus 5.5 reads it under 3.

### Parse rates, the cache and the spend

| version | model | pass | parsed at the first attempt | parsed in the end |
|---|---|---|---|---|
| version 6 | Haiku 5.5 | 1 | 409 / 409 | 409 / 409 |
| version 6 | Haiku 4.5 | 1 | 409 / 409 | 409 / 409 |
| version 6 | Haiku 5.5 | 2 | 409 / 409 | 409 / 409 |
| version 6 | Haiku 4.5 | 2 | 409 / 409 | 409 / 409 |

Version 6's answer format (first attempts; in the end): an answer wrapped in a results list (the list form's shape), extra keys, the answer before the reason, and self-corrections (more than one answer object):

| model | pass | calls | wrapped | extra keys | answer before reason | self-corrections |
|---|---|---|---|---|---|---|
| Haiku 4.5 | 1 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Haiku 4.5 | 2 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Haiku 5.5 | 1 | 409 | 0; 0 | 0; 0 | 0; 0 | 2; 2 |
| Haiku 5.5 | 2 | 409 | 0; 0 | 0; 0 | 0; 0 | 3; 3 |

The prompt cache and the spend, from the usage each record holds (every answered request, re-asks included).  "Charged" is what the usage records charge (cache writes 1.25x, reads 0.1x the input price, as `llm.billed_usage` does for every model); "published" reads Opus 5.5's cache at its published 0.05x; "uncached" puts every input token at the full price.

| version | model | requests | reading the cache | writing it | input tokens: uncached / written / read | share of input read from the cache | charged | published | uncached | saved (charged; published) | per pair answered |
|---|---|---|---|---|---|---|---|---|---|---|---|
| version 6 | Haiku 4.5 | 818 | 0 (0%) | 0 | 450,800 / 0 / 0 | 0% | $0.6800 | $0.6800 | $0.6800 | $0.0000; $0.0000 | $0.00083 (818) |
| version 6 | Haiku 5.5 | 818 | 810 (99%) | 8 | 128,038 / 4,592 / 464,940 | 78% | $0.0755 | $0.0755 | $0.1173 | $0.0417; $0.0417 | $0.00009 (818) |

### Every pair: 409 pairs

By group: nearest 300, near_distinct 34, antonym 30, drop_or_merge 11, random 30, duplicate 1, deliberate_duplicate 3.  Versions measured here: version 6.

Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on the pairs both passes scored; flips: pairs on different sides of 3 in the two passes).  The last columns: the pairs whose prompt was identical in both passes (all of version 6's).

| version | model | both answered | exact | within one | kappa | exact (decision) | flips at 3 | identical prompts: pairs | exact | within one | kappa | flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| version 6 | Haiku 5.5 | 409 | 92% | 100% | 0.93 | 92% | 11 of 409 | 409 (all) | 92% | 100% | 0.93 | 11 of 409 |
| version 6 | Haiku 4.5 | 409 | 100% | 100% | 1.00 | 100% | 0 of 409 | 409 (all) | 100% | 100% | 1.00 | 0 of 409 |

Where the passes differ, by the two answers:

- version 6, Haiku 5.5: 0/1 3, 0/opposite 4, 1/2 13, 1/opposite 1, 2/3 11, 3/4 2
- version 6, Haiku 4.5: none

Haiku 5.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Haiku 5.5 covers only |
|---|---|---|---|---|---|---|---|---|

Haiku 4.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Haiku 4.5 covers only |
|---|---|---|---|---|---|---|---|---|

At 3 or more:

| version | model | pass 1 | pass 2 |
|---|---|---|---|
| version 6 | Haiku 5.5 | 39 of 409 (10%) | 40 of 409 (10%) |
| version 6 | Haiku 4.5 | 71 of 409 (17%) | 71 of 409 (17%) |

Known groups on the decision scale: mean of the numeric answers / share at 3 or more / share "opposite", pass 1; pass 2.

| group | n | version 6, Haiku 5.5 | version 6, Haiku 4.5 |
|---|---|---|---|
| nearest | 300 | 1.97 / 11% / 14%; 1.96 / 11% / 14% | 2.09 / 22% / 16%; 2.09 / 22% / 16% |
| drop_or_merge | 11 | 3.00 / 80% / 9%; 3.00 / 90% / 9% | 3.20 / 90% / 9%; 3.20 / 90% / 9% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0%; 2.00 / 0% / 0% | 2.67 / 33% / 0%; 2.67 / 33% / 0% |
| duplicate | 1 | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% |
| near_distinct | 34 | 1.46 / 8% / 24%; 1.65 / 9% / 32% | 1.95 / 25% / 41%; 1.95 / 25% / 41% |
| antonym | 30 | – / – / 100%; – / – / 100% | – / – / 100%; – / – / 100% |
| random | 30 | 0.18 / 0% / 7%; 0.20 / 0% / 0% | 0.19 / 0% / 10%; 0.19 / 0% / 10% |

Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the same counting "neither implies the other" too, and 3s whose reason states line 2 in its own words ("each adds something", "neither implies the other"; patterns in `summary.json`).

| version | model | pass | 2s | containment reason | discounting "neither implies" | 3s | two-sided reason | or "neither implies" | line 2's words |
|---|---|---|---|---|---|---|---|---|---|
| version 6 | Haiku 5.5 | 1 | 215 | 21 of 215 (10%) | 17 of 215 (8%) | 33 | 3 of 33 (9%) | 3 of 33 (9%) | 0 of 33 (0%) |
| version 6 | Haiku 5.5 | 2 | 213 | 19 of 213 (9%) | 16 of 213 (8%) | 34 | 2 of 34 (6%) | 2 of 34 (6%) | 0 of 34 (0%) |
| version 6 | Haiku 5.5 | pooled | 428 | 40 of 428 (9%) | 33 of 428 (8%) | 67 | 5 of 67 (8%) | 5 of 67 (8%) | 0 of 67 (0%) |
| version 6 | Haiku 4.5 | 1 | 182 | 27 of 182 (15%) | 27 of 182 (15%) | 62 | 1 of 62 (2%) | 1 of 62 (2%) | 0 of 62 (0%) |
| version 6 | Haiku 4.5 | 2 | 182 | 27 of 182 (15%) | 27 of 182 (15%) | 62 | 1 of 62 (2%) | 1 of 62 (2%) | 0 of 62 (0%) |
| version 6 | Haiku 4.5 | pooled | 364 | 54 of 364 (15%) | 54 of 364 (15%) | 124 | 2 of 124 (2%) | 2 of 124 (2%) | 0 of 124 (0%) |

### The nearest pairs: 300 pairs

By group: nearest 300.  Versions measured here: version 6.

Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on the pairs both passes scored; flips: pairs on different sides of 3 in the two passes).  The last columns: the pairs whose prompt was identical in both passes (all of version 6's).

| version | model | both answered | exact | within one | kappa | exact (decision) | flips at 3 | identical prompts: pairs | exact | within one | kappa | flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| version 6 | Haiku 5.5 | 300 | 92% | 100% | 0.86 | 92% | 10 of 300 | 300 (all) | 92% | 100% | 0.86 | 10 of 300 |
| version 6 | Haiku 4.5 | 300 | 100% | 100% | 1.00 | 100% | 0 of 300 | 300 (all) | 100% | 100% | 1.00 | 0 of 300 |

Where the passes differ, by the two answers:

- version 6, Haiku 5.5: 0/1 2, 1/2 12, 2/3 10, 3/4 1
- version 6, Haiku 4.5: none

Haiku 5.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Haiku 5.5 covers only |
|---|---|---|---|---|---|---|---|---|

Haiku 4.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Haiku 4.5 covers only |
|---|---|---|---|---|---|---|---|---|

At 3 or more:

| version | model | pass 1 | pass 2 |
|---|---|---|---|
| version 6 | Haiku 5.5 | 28 of 300 (9%) | 28 of 300 (9%) |
| version 6 | Haiku 4.5 | 55 of 300 (18%) | 55 of 300 (18%) |

Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the same counting "neither implies the other" too, and 3s whose reason states line 2 in its own words ("each adds something", "neither implies the other"; patterns in `summary.json`).

| version | model | pass | 2s | containment reason | discounting "neither implies" | 3s | two-sided reason | or "neither implies" | line 2's words |
|---|---|---|---|---|---|---|---|---|---|
| version 6 | Haiku 5.5 | 1 | 195 | 18 of 195 (9%) | 16 of 195 (8%) | 25 | 3 of 25 (12%) | 3 of 25 (12%) | 0 of 25 (0%) |
| version 6 | Haiku 5.5 | 2 | 193 | 16 of 193 (8%) | 14 of 193 (7%) | 24 | 2 of 24 (8%) | 2 of 24 (8%) | 0 of 24 (0%) |
| version 6 | Haiku 5.5 | pooled | 388 | 34 of 388 (9%) | 30 of 388 (8%) | 49 | 5 of 49 (10%) | 5 of 49 (10%) | 0 of 49 (0%) |
| version 6 | Haiku 4.5 | 1 | 167 | 25 of 167 (15%) | 25 of 167 (15%) | 50 | 1 of 50 (2%) | 1 of 50 (2%) | 0 of 50 (0%) |
| version 6 | Haiku 4.5 | 2 | 167 | 25 of 167 (15%) | 25 of 167 (15%) | 50 | 1 of 50 (2%) | 1 of 50 (2%) | 0 of 50 (0%) |
| version 6 | Haiku 4.5 | pooled | 334 | 50 of 334 (15%) | 50 of 334 (15%) | 100 | 2 of 100 (2%) | 2 of 100 (2%) | 0 of 100 (0%) |

### Agreement with Roger's 30 marks

His leaning per item, read by hand from the sheet, with the alternative he named on five items.  Exact counts every answer ("opposite" included); within one, the items where both are numbers.

| answers | model | items | exact | within one | leaning or alternative |
|---|---|---|---|---|---|
| version 4 (overlap_test_1) | Haiku 4.5 | 30 | 23 of 30 (77%) | 23 of 23 (100%) | 25 of 30 (83%) |
| version 6, pass 1 | Haiku 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 23 of 30 (77%) |
| version 6, pass 1 | Haiku 4.5 | 30 | 18 of 30 (60%) | 20 of 21 (95%) | 20 of 30 (67%) |
| version 6, pass 2 | Haiku 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 22 of 30 (73%) |
| version 6, pass 2 | Haiku 4.5 | 30 | 18 of 30 (60%) | 20 of 21 (95%) | 20 of 30 (67%) |

Per item:

| item | target / listed | Roger (alternative) | version 4 (overlap_test_1), Haiku 4.5 | version 6, pass 1, Haiku 5.5 | version 6, pass 1, Haiku 4.5 | version 6, pass 2, Haiku 5.5 | version 6, pass 2, Haiku 4.5 |
|---|---|---|---|---|---|---|---|
| 1 | self-blaming / blame-shifting | opposite | opposite | opposite | opposite | opposite | opposite |
| 2 | erudite / esoteric | 1 (2) | 1 | 2 | 2 | 2 | 2 |
| 3 | utilitarian / deontological | opposite | opposite | opposite | opposite | opposite | opposite |
| 4 | animated / flat | opposite | opposite | opposite | opposite | opposite | opposite |
| 5 | conservative / overconfident | 0 | 0 | 0 | opposite | 0 | opposite |
| 6 | materialist / relativist | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | excitable / narrative | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 | religious / secular | opposite | opposite | opposite | opposite | opposite | opposite |
| 9 | extroverted / energetic | 0 | 1 | 1 | 0 | 1 | 0 |
| 10 | temperamental / even-tempered | opposite | opposite | opposite | opposite | opposite | opposite |
| 11 | iconoclastic / deconstructionist | 2 | 2 | 2 | 2 | 2 | 2 |
| 12 | ethereal / spiritual | 1 | 2 | 2 | 2 | 2 | 2 |
| 13 | strategic / long-term oriented | 1 (2) | 2 | 2 | 2 | 2 | 2 |
| 14 | agreeable / conciliatory | 2 | 3 | 2 | 3 | 2 | 3 |
| 15 | dispassionate / detached | 4 | 4 | 4 | 3 | 3 | 3 |
| 16 | nihilistic / essentialist | opposite | opposite | 0 | opposite | 0 | opposite |
| 17 | hedonistic / self-indulgent | 3 (2) | 3 | 2 | 3 | 3 | 3 |
| 18 | consequentialist / ends justify means | 2 | 2 | 2 | 2 | 2 | 2 |
| 19 | deconstructionist / structuralist | 1 | 1 | 1 | opposite | 1 | opposite |
| 20 | benevolent / benign | 2 | 2 | 2 | 2 | 2 | 2 |
| 21 | honorable / deontological | 2 (3) | 3 | 2 | 4 | 2 | 4 |
| 22 | adventurous / adventurous-eater | 2 | 3 | 3 | 3 | 3 | 3 |
| 23 | strategic / tactical | opposite | opposite | opposite | opposite | opposite | opposite |
| 24 | moral relativist / relativist | 4 | 3 | 3 | 3 | 3 | 3 |
| 25 | serious / formal | 3 | 3 | 2 | 2 | 2 | 2 |
| 26 | socratic / educational | 2 | 2 | 2 | 2 | 2 | 2 |
| 27 | extroverted / gregarious | 3 (2) | 3 | 3 | 3 | 3 | 3 |
| 28 | theoretical / conceptual | 4 | 4 | 4 | 4 | 4 | 4 |
| 29 | cosmopolitan / philanthropic | 1 | 1 | 0 | 0 | 0 | 0 |
| 30 | moderate / temperate | 2 | 2 | 2 | 2 | 2 | 2 |

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A | Haiku 4.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Haiku 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|

Categorical answers against the reference (rows: reference; columns: model):


## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A | Haiku 5.5 | persona | 0.58 [0.44, 0.69] (n 234) | 0.58 [0.44, 0.69] (n 234) | 0.53 [0.40, 0.64] (n 199) | 0.53 [0.40, 0.64] (n 199) |
| A | Haiku 5.5 | embedding | 0.63 [0.53, 0.72] (n 325) | 0.63 [0.53, 0.72] (n 325) | 0.43 [0.29, 0.54] (n 257) | 0.43 [0.29, 0.54] (n 257) |
| A | Haiku 4.5 | persona | 0.61 [0.50, 0.70] (n 224) | 0.61 [0.50, 0.70] (n 224) | 0.56 [0.45, 0.66] (n 195) | 0.56 [0.45, 0.66] (n 195) |
| A | Haiku 4.5 | embedding | 0.65 [0.56, 0.72] (n 313) | 0.65 [0.56, 0.72] (n 313) | 0.50 [0.39, 0.59] (n 252) | 0.50 [0.39, 0.59] (n 252) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|

## Known groups, rubric A

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Haiku 5.5 | Haiku 4.5 |
|---|---|---|---|
| nearest | 300 | 1.97 / 11% / 14% / 0% | 2.09 / 22% / 16% / 0% |
| drop_or_merge | 11 | 3.00 / 80% / 9% / 0% | 3.20 / 90% / 9% / 0% |
| deliberate_duplicate | 3 | 2.00 / 0% / 0% / 0% | 2.67 / 33% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.46 / 8% / 24% / 0% | 1.95 / 25% / 41% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.18 / 0% / 7% / 0% | 0.19 / 0% / 10% / 0% |

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A | Haiku 5.5 | 409 | 0% (0) | 20% (84) | 100% of 30 | 100% of 31 | 7% of 348 |
| A | Haiku 4.5 | 409 | 0% (0) | 24% (96) | 100% of 30 | 100% of 31 | 10% of 348 |

## The same pair in two calls

- rubric A: Haiku 5.5 30 of 38 the same; Haiku 4.5 32 of 38 the same

## The arms experiment: 2 passes, decision scale, cut-off 3

Rubric A went out one pair per call (the single form): every later pass sent the identical prompt, there being no list to reorder, so the agreement between the passes is sampling noise alone.

The decision scale is rubric A's 0-4 with "opposite" and "unsure"; every rubric here answers on it directly.  Covered means 3 or more on it ("opposite" is not covered, "unsure" neither), over the nearest-neighbour pairs.  The native scale is each rubric's own answers.  Exact agreement counts every answer, categories included.

### Cross-arm table

| arm | model | consistency, exact (native) | consistency, exact (decision) | between-pass flips at 3 | agreement, exact, pass 1 (native / decision) | agreement, pass 2 | covered at 3, pass 1 | targets covered, pass 1 | between-model crossings at 3 (pass 1 / pass 2) |
|---|---|---|---|---|---|---|---|---|---|
| A | Haiku 5.5 | 92% (409) | 92% | 10 of 300 | – | – | 28 of 300 (9%) | 22 of 100 | – |
| A | Haiku 4.5 | 100% (409) | 100% | 0 of 300 | – | – | 55 of 300 (18%) | 41 of 100 | – |

Agreement is each model against the other one (Sonnet 5.5 against Opus 5.5 in this experiment); crossings are the nearest pairs the two models put on different sides of the cut-off, flips the nearest pairs one model put on different sides in its two passes.

### Parse rates by pass

| rubric | model | pass | ok / total | first attempt |
|---|---|---|---|---|
| A | Haiku 4.5 | 1 | 409 / 409 | 409 / 409 |
| A | Haiku 5.5 | 1 | 409 / 409 | 409 / 409 |
| A | Haiku 4.5 | 2 | 409 / 409 | 409 / 409 |
| A | Haiku 5.5 | 2 | 409 / 409 | 409 / 409 |

### Arm A: overlap_concept (concept similarity)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 409 | 92% | 100% | 0.00 | 0.93 | 92% | 100% | 10 of 300 (5 covered in pass 1 only, 5 in pass 2 only) |
| Haiku 4.5 | 409 | 100% | 100% | 0.00 | 1.00 | 100% | 100% | 0 of 300 (0 covered in pass 1 only, 0 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Haiku 5.5: 0/1 3, 0/opposite 4, 1/2 13, 1/opposite 1, 2/3 11, 3/4 2 (29 of 34 between neighbouring points); decision: 0/1 3, 0/opposite 4, 1/2 13, 1/opposite 1, 2/3 11, 3/4 2
- Haiku 4.5: none (0 of 0 between neighbouring points); decision: none

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Haiku 5.5 | 92% / 92% (409) | – / – (0) | – / – (0) |
| Haiku 4.5 | 100% / 100% (409) | – / – (0) | – / – (0) |

Haiku 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- compassionate / empathetic: 3, 2
- confident / overconfident: 3, 2
- entertaining / playful: 3, 2
- environmental / ecocentric: 2, 3
- hedonistic / self-indulgent: 2, 3
- iconoclastic / contrarian: 2, 3
- sarcastic / sardonic: 3, 2
- systems-thinker / holistic: 2, 3
- wry / sardonic: 3, 2
- zealous / passionate: 2, 3

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 1 | 300 | 28 | 9% | 22 of 100 | 43 | 0 |
| Haiku 5.5 | 2 | 300 | 28 | 9% | 22 of 100 | 43 | 0 |
| Haiku 4.5 | 1 | 300 | 55 | 18% | 41 of 100 | 48 | 0 |
| Haiku 4.5 | 2 | 300 | 55 | 18% | 41 of 100 | 48 | 0 |

Kinds of difference the reasons of 3s name (not asked: rubric A's 3s, as a control; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Haiku 5.5 | 1 | 33 | 3 | 1 | 2 | 0 | 20 | 7 (21%) | 0 |
| Haiku 5.5 | 2 | 34 | 4 | 5 | 2 | 1 | 19 | 8 (24%) | 4 |
| Haiku 4.5 | 1 | 62 | 1 | 12 | 1 | 0 | 33 | 19 (31%) | 4 |
| Haiku 4.5 | 2 | 62 | 1 | 12 | 1 | 0 | 33 | 19 (31%) | 4 |
