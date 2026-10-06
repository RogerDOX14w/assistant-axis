# Overlap test: tables

409 pairs in 180 calls.  (Rubric A went out one pair per call, 409 calls a stage; the calls here are the pair set's.)  Reference model: Opus 5.5.  Generated from `summary.json` beside this file.

## Round 3: rubric A version 6, one pair per call

Versions compared on the same pairs: version 4: rubric A version 4, list form, run `overlap_arms_1`; A2: rubric A2 version 1, list form, run `overlap_arms_2`; version 6: rubric A version 6, single form, run `overlap_arms_3`.  Version 6 went out one pair per call, and its second pass sent the identical prompts (there is no list to reorder), so the agreement between its passes is sampling noise alone; version 4's and A2's second passes reshuffled their lists, so their like-for-like figure is the one on the pairs whose prompt came out identical (a call of one trait, or a list that shuffled into the same order).  Decision scale: rubric A's own; cut-off 3.  Crossings, flips and shares count every pair of the population named.  M3's rule: Sonnet 5.5 reads every pair; above 3 is cut, below it (or "opposite") kept; at 3 (or "unsure") the pair goes to Opus 5.5, and is kept if Opus 5.5 reads it under 3.

### Summary: version 4 against version 6

Verdict "same" when the two differ by no more than the noise band: for a figure read in each pass, the difference between version 4's two passes (round 1's passes); for a figure that already compares the passes (self-consistency, the rule's flips), two binomial standard errors of version 4's figure; never less than one pair.  Figures read in each pass are the means of the two passes.  "higher" / "lower" where neither direction is better.

| figure | model | version 4 | version 6 | noise band | verdict |
|---|---|---|---|---|---|
| self-consistency, exact, like for like: the pairs whose prompt was identical in both of version 4's passes (one-trait calls and lists that shuffled into the same order), both versions on those pairs | Sonnet 5.5 | 95.7% (139) | 97.8% (139) | 3.4% | same |
| self-consistency, exact, every pair (version 4 includes its reordered lists; not like for like) | Sonnet 5.5 | 89.0% (409) | 95.1% (409) | – | – |
| self-consistency, exact, like for like: the pairs whose prompt was identical in both of version 4's passes (one-trait calls and lists that shuffled into the same order), both versions on those pairs | Opus 5.5 | 97.8% (139) | 95.7% (139) | 2.5% | same |
| self-consistency, exact, every pair (version 4 includes its reordered lists; not like for like) | Opus 5.5 | 91.7% (409) | 94.6% (409) | – | – |
| Sonnet 5.5 against Opus 5.5, exact, every pair, mean of the passes | both | 86.1% | 85.6% | 1.5% | same |
| crossings at 3 between the models, nearest pairs, mean of the passes | both | 11 | 21 | 6 | worse |
| covered at 3, nearest pairs, mean of the passes | Sonnet 5.5 | 14.3% | 13.2% | 2.0% | same |
| covered at 3, nearest pairs, mean of the passes | Opus 5.5 | 12.7% | 17.1% | 0.3% | higher |
| kept though Opus reads 3 or more (the rule), every pair, mean of the passes | rule | 4 | 16.5 | 6 | worse |
| escalated to Opus (the rule), every pair, mean of the passes | rule | 51 | 49.5 | 6 | same |
| rescued by Opus (the rule), every pair, mean of the passes | rule | 10.5 | 7 | 1 | lower |
| the rule's decision differs between the passes, every pair | rule | 10 (409) | 7 (409) | 6.2 | same |
| 2s whose reason describes a containment (round 1's pattern), pooled | Sonnet 5.5 | 13.5% (35 of 260) | 7.6% (25 of 329) | 5.9% | same |
| 2s whose reason describes a containment (round 1's pattern), pooled | Opus 5.5 | 8.1% (20 of 247) | 3.9% (12 of 309) | 3.2% | better |
| the same, discounting "neither implies the other" wording | Sonnet 5.5 | 13.5% (35 of 260) | 6.1% (20 of 329) | 5.9% | better |
| the same, discounting "neither implies the other" wording | Opus 5.5 | 8.1% (20 of 247) | 2.3% (7 of 309) | 3.2% | better |
| 3s whose reason describes a two-sided overlap (round 2's pattern), pooled | Sonnet 5.5 | 2.0% (2 of 102) | 26.3% (26 of 99) | 2.0% | worse |
| 3s whose reason describes a two-sided overlap (round 2's pattern), pooled | Opus 5.5 | 3.4% (3 of 87) | 7.1% (8 of 112) | 2.3% | worse |
| 3s whose reason states line 2's words ("each adds something", "neither implies the other"), pooled | Sonnet 5.5 | 0.0% (0 of 102) | 9.1% (9 of 99) | 2.0% | worse |
| 3s whose reason states line 2's words ("each adds something", "neither implies the other"), pooled | Opus 5.5 | 0.0% (0 of 87) | 0.0% (0 of 112) | 2.3% | same |
| Roger's 30 marks: his leaning or the alternative he named (version 4: overlap_test_1; version 6: mean of the passes) | Sonnet 5.5 | 21 (30) | 23 | 3 | same |
| Roger's 30 marks: his leaning or the alternative he named (version 4: overlap_test_1; version 6: mean of the passes) | Opus 5.5 | 20 (30) | 24.5 | 1 | better |
| Roger's 30 marks: exact (version 4: overlap_test_1; version 6: mean of the passes) | Sonnet 5.5 | 19 (30) | 20 | 3 | same |
| Roger's 30 marks: exact (version 4: overlap_test_1; version 6: mean of the passes) | Opus 5.5 | 18 (30) | 21.5 | 1 | better |

### Parse rates, the cache and the spend

| version | model | pass | parsed at the first attempt | parsed in the end |
|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 1 | 409 / 409 | 409 / 409 |
| version 4 | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| version 4 | Sonnet 5.5 | 2 | 406 / 409 | 409 / 409 |
| version 4 | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| A2 | Sonnet 5.5 | 1 | 242 / 242 | 242 / 242 |
| A2 | Opus 5.5 | 1 | 242 / 242 | 242 / 242 |
| A2 | Sonnet 5.5 | 2 | 242 / 242 | 242 / 242 |
| A2 | Opus 5.5 | 2 | 242 / 242 | 242 / 242 |
| version 6 | Sonnet 5.5 | 1 | 409 / 409 | 409 / 409 |
| version 6 | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| version 6 | Sonnet 5.5 | 2 | 409 / 409 | 409 / 409 |
| version 6 | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |

Version 6's answer format (first attempts; in the end): an answer wrapped in a results list (the list form's shape), extra keys, the answer before the reason, and self-corrections (more than one answer object):

| model | pass | calls | wrapped | extra keys | answer before reason | self-corrections |
|---|---|---|---|---|---|---|
| Opus 5.5 | 1 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Opus 5.5 | 2 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Sonnet 5.5 | 1 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |
| Sonnet 5.5 | 2 | 409 | 0; 0 | 0; 0 | 0; 0 | 0; 0 |

The prompt cache and the spend, from the usage each record holds (every answered request, re-asks included).  "Charged" is what the usage records charge (cache writes 1.25x, reads 0.1x the input price, as `llm.billed_usage` does for every model); "published" reads Opus 5.5's cache at its published 0.05x; "uncached" puts every input token at the full price.

| version | model | requests | reading the cache | writing it | input tokens: uncached / written / read | share of input read from the cache | charged | published | uncached | saved (charged; published) | per pair answered |
|---|---|---|---|---|---|---|---|---|---|---|---|
| version 4 | Opus 5.5 | 360 | 0 (0%) | 0 | 324,386 / 0 / 0 | 0% | $2.4463 | $2.4463 | $2.4463 | $0.0000; $0.0000 | $0.00299 (818) |
| version 4 | Sonnet 5.5 | 361 | 0 (0%) | 0 | 325,295 / 0 / 0 | 0% | $1.2721 | $1.2721 | $1.2721 | $0.0000; $0.0000 | $0.00155 (818) |
| A2 | Opus 5.5 | 168 | 0 (0%) | 0 | 177,006 / 0 / 0 | 0% | $1.4064 | $1.4064 | $1.4064 | $0.0000; $0.0000 | $0.00291 (484) |
| A2 | Sonnet 5.5 | 168 | 0 (0%) | 0 | 177,006 / 0 / 0 | 0% | $0.7278 | $0.7278 | $0.7278 | $0.0000; $0.0000 | $0.00150 (484) |
| version 6 | Opus 5.5 | 818 | 810 (99%) | 8 | 128,038 / 4,592 / 464,940 | 78% | $2.5601 | $2.4672 | $4.2293 | $1.6692; $1.7622 | $0.00313 (818) |
| version 6 | Sonnet 5.5 | 818 | 811 (99%) | 7 | 128,038 / 4,018 / 465,514 | 78% | $0.9995 | $0.9995 | $1.8354 | $0.8359; $0.8359 | $0.00122 (818) |

### Every pair: 409 pairs

By group: nearest 300, near_distinct 34, antonym 30, drop_or_merge 11, random 30, duplicate 1, deliberate_duplicate 3.  Versions measured here: version 4, version 6.

Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on the pairs both passes scored; flips: pairs on different sides of 3 in the two passes).  The last columns: the pairs whose prompt was identical in both passes (all of version 6's).

| version | model | both answered | exact | within one | kappa | exact (decision) | flips at 3 | identical prompts: pairs | exact | within one | kappa | flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 409 | 89% | 100% | 0.93 | 89% | 13 of 409 | 139 | 96% | 100% | 0.98 | 1 of 139 |
| version 4 | Opus 5.5 | 409 | 92% | 100% | 0.95 | 92% | 4 of 409 | 139 | 98% | 100% | 0.99 | 1 of 139 |
| version 6 | Sonnet 5.5 | 409 | 95% | 100% | 0.96 | 95% | 5 of 409 | 409 (all) | 95% | 100% | 0.96 | 5 of 409 |
| version 6 | Opus 5.5 | 409 | 95% | 100% | 0.96 | 95% | 6 of 409 | 409 (all) | 95% | 100% | 0.96 | 6 of 409 |

Like for like, on the same pairs: the 139 pairs of this population whose prompt was identical in both of version 4's passes (one-trait calls, and lists that shuffled into the same order), every version on those pairs:

| version | model | pairs | exact | within one | kappa | exact (decision) | flips at 3 |
|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 139 | 96% | 100% | 0.98 | 96% | 1 of 139 |
| version 4 | Opus 5.5 | 139 | 98% | 100% | 0.99 | 98% | 1 of 139 |
| version 6 | Sonnet 5.5 | 139 | 98% | 100% | 0.99 | 98% | 1 of 139 |
| version 6 | Opus 5.5 | 139 | 96% | 100% | 0.98 | 96% | 2 of 139 |

Where the passes differ, by the two answers:

- version 4, Sonnet 5.5: 0/1 5, 0/opposite 2, 1/2 23, 1/opposite 1, 2/3 13, 3/4 1
- version 4, Opus 5.5: 0/1 5, 1/2 23, 1/opposite 1, 2/3 4, 3/4 1
- version 6, Sonnet 5.5: 0/1 2, 0/opposite 1, 1/2 10, 2/3 5, 3/4 2
- version 6, Opus 5.5: 0/1 3, 1/2 13, 2/3 6

Sonnet 5.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Sonnet 5.5 covers only |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 409 | 87% | 100% | 0.93 | 11 of 409 | 1 | 10 |
| version 4 | 2 | 409 | 85% | 100% | 0.91 | 18 of 409 | 7 | 11 |
| version 6 | 1 | 409 | 87% | 100% | 0.91 | 23 of 409 | 16 | 7 |
| version 6 | 2 | 409 | 85% | 100% | 0.90 | 24 of 409 | 17 | 7 |

Against version 4, the same model and pass (crossings: on different sides of 3):

| version | model | pass | both answered | exact | within one | kappa | crossings | version 4 covers only | this version covers only |
|---|---|---|---|---|---|---|---|---|---|
| version 6 | Sonnet 5.5 | 1 | 409 | 83% | 100% | 0.88 | 16 of 409 | 10 | 6 |
| version 6 | Sonnet 5.5 | 2 | 409 | 85% | 100% | 0.90 | 14 of 409 | 7 | 7 |
| version 6 | Opus 5.5 | 1 | 409 | 80% | 100% | 0.88 | 22 of 409 | 4 | 18 |
| version 6 | Opus 5.5 | 2 | 409 | 78% | 100% | 0.86 | 24 of 409 | 5 | 19 |

At 3 or more:

| version | model | pass 1 | pass 2 |
|---|---|---|---|
| version 4 | Sonnet 5.5 | 61 of 409 (15%) | 56 of 409 (14%) |
| version 4 | Opus 5.5 | 52 of 409 (13%) | 52 of 409 (13%) |
| version 6 | Sonnet 5.5 | 57 of 409 (14%) | 56 of 409 (14%) |
| version 6 | Opus 5.5 | 66 of 409 (16%) | 66 of 409 (16%) |

Known groups on the decision scale: mean of the numeric answers / share at 3 or more / share "opposite", pass 1; pass 2.

| group | n | version 4, Sonnet 5.5 | version 4, Opus 5.5 | version 6, Sonnet 5.5 | version 6, Opus 5.5 |
|---|---|---|---|---|---|
| nearest | 300 | 1.77 / 18% / 15%; 1.76 / 16% / 15% | 1.68 / 15% / 13%; 1.68 / 15% / 13% | 1.92 / 16% / 15%; 1.89 / 15% / 15% | 1.93 / 20% / 14%; 1.95 / 20% / 14% |
| drop_or_merge | 11 | 3.20 / 100% / 9%; 3.20 / 100% / 9% | 3.10 / 80% / 9%; 3.10 / 80% / 9% | 3.20 / 100% / 9%; 3.30 / 100% / 9% | 3.30 / 100% / 9%; 3.20 / 90% / 9% |
| deliberate_duplicate | 3 | 2.33 / 33% / 0%; 2.00 / 0% / 0% | 2.33 / 33% / 0%; 2.33 / 33% / 0% | 2.33 / 33% / 0%; 2.33 / 33% / 0% | 2.33 / 33% / 0%; 2.33 / 33% / 0% |
| duplicate | 1 | 2.00 / 0% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% |
| near_distinct | 34 | 1.52 / 16% / 26%; 1.54 / 19% / 24% | 1.52 / 15% / 21%; 1.48 / 15% / 21% | 1.54 / 19% / 24%; 1.64 / 20% / 26% | 1.54 / 12% / 24%; 1.46 / 12% / 24% |
| antonym | 30 | – / – / 100%; – / – / 100% | – / – / 100%; – / – / 100% | – / – / 100%; – / – / 100% | – / – / 100%; – / – / 100% |
| random | 30 | 0.14 / 0% / 7%; 0.17 / 0% / 3% | 0.17 / 0% / 0%; 0.17 / 0% / 0% | 0.17 / 0% / 3%; 0.14 / 0% / 3% | 0.13 / 0% / 0%; 0.13 / 0% / 0% |

M3's rule (Sonnet 5.5 first, Opus 5.5 on the 3s), per pass:

| version | pass | decided | escalated | rescued | cut | of which directly | kept though Opus 5.5 reads 3+ | decision differs from version 4 (keep to cut / cut to keep) |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 409 | 54 | 10 | 51 | 7 | 1 | – |
| version 4 | 2 | 409 | 48 | 11 | 45 | 8 | 7 | – |
| version 6 | 1 | 409 | 51 | 7 | 50 | 6 | 16 | 19 of 409 (9 / 10) |
| version 6 | 2 | 409 | 48 | 7 | 49 | 8 | 17 | 10 of 409 (7 / 3) |

- version 4: the rule's decision differs between the passes on 10 of 409 pairs
- version 6: the rule's decision differs between the passes on 7 of 409 pairs

Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the same counting "neither implies the other" too, and 3s whose reason states line 2 in its own words ("each adds something", "neither implies the other"; patterns in `summary.json`).

| version | model | pass | 2s | containment reason | discounting "neither implies" | 3s | two-sided reason | or "neither implies" | line 2's words |
|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 1 | 125 | 13 of 125 (10%) | 13 of 125 (10%) | 54 | 1 of 54 (2%) | 1 of 54 (2%) | 0 of 54 (0%) |
| version 4 | Sonnet 5.5 | 2 | 135 | 22 of 135 (16%) | 22 of 135 (16%) | 48 | 1 of 48 (2%) | 1 of 48 (2%) | 0 of 48 (0%) |
| version 4 | Sonnet 5.5 | pooled | 260 | 35 of 260 (14%) | 35 of 260 (14%) | 102 | 2 of 102 (2%) | 2 of 102 (2%) | 0 of 102 (0%) |
| version 4 | Opus 5.5 | 1 | 124 | 12 of 124 (10%) | 12 of 124 (10%) | 43 | 1 of 43 (2%) | 1 of 43 (2%) | 0 of 43 (0%) |
| version 4 | Opus 5.5 | 2 | 123 | 8 of 123 (6%) | 8 of 123 (6%) | 44 | 2 of 44 (4%) | 2 of 44 (4%) | 0 of 44 (0%) |
| version 4 | Opus 5.5 | pooled | 247 | 20 of 247 (8%) | 20 of 247 (8%) | 87 | 3 of 87 (3%) | 3 of 87 (3%) | 0 of 87 (0%) |
| version 6 | Sonnet 5.5 | 1 | 168 | 14 of 168 (8%) | 10 of 168 (6%) | 51 | 13 of 51 (26%) | 13 of 51 (26%) | 4 of 51 (8%) |
| version 6 | Sonnet 5.5 | 2 | 161 | 11 of 161 (7%) | 10 of 161 (6%) | 48 | 13 of 48 (27%) | 14 of 48 (29%) | 5 of 48 (10%) |
| version 6 | Sonnet 5.5 | pooled | 329 | 25 of 329 (8%) | 20 of 329 (6%) | 99 | 26 of 99 (26%) | 27 of 99 (27%) | 9 of 99 (9%) |
| version 6 | Opus 5.5 | 1 | 153 | 4 of 153 (3%) | 2 of 153 (1%) | 56 | 3 of 56 (5%) | 3 of 56 (5%) | 0 of 56 (0%) |
| version 6 | Opus 5.5 | 2 | 156 | 8 of 156 (5%) | 5 of 156 (3%) | 56 | 5 of 56 (9%) | 5 of 56 (9%) | 0 of 56 (0%) |
| version 6 | Opus 5.5 | pooled | 309 | 12 of 309 (4%) | 7 of 309 (2%) | 112 | 8 of 112 (7%) | 8 of 112 (7%) | 0 of 112 (0%) |

Opus 5.5 on the pairs the rule escalates (Sonnet 5.5 at 3): its answers on them in that pass, and on those it answered in both passes, how often alike:

| version | escalated in | pairs | Opus 5.5's answers | answered in both passes | same answer | same side of 3 |
|---|---|---|---|---|---|---|
| version 4 | pass 1 | 54 | 2 10, 3 42, 4 2 | 54 | 50 | 51 |
| version 4 | pass 2 | 48 | 2 11, 3 36, 4 1 | 48 | 45 | 46 |
| version 4 | either pass | 58 | – | 58 | 54 | 55 |
| version 6 | pass 1 | 51 | 2 7, 3 40, 4 4 | 51 | 47 | 47 |
| version 6 | pass 2 | 48 | 2 7, 3 39, 4 2 | 48 | 45 | 45 |
| version 6 | either pass | 53 | – | 53 | 49 | 49 |

### The nearest pairs: 300 pairs

By group: nearest 300.  Versions measured here: version 4, version 6.

Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on the pairs both passes scored; flips: pairs on different sides of 3 in the two passes).  The last columns: the pairs whose prompt was identical in both passes (all of version 6's).

| version | model | both answered | exact | within one | kappa | exact (decision) | flips at 3 | identical prompts: pairs | exact | within one | kappa | flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 300 | 87% | 100% | 0.89 | 87% | 10 of 300 | 66 | 95% | 100% | 0.97 | 0 of 66 |
| version 4 | Opus 5.5 | 300 | 89% | 100% | 0.91 | 89% | 4 of 300 | 66 | 97% | 100% | 0.98 | 1 of 66 |
| version 6 | Sonnet 5.5 | 300 | 95% | 100% | 0.94 | 95% | 5 of 300 | 300 (all) | 95% | 100% | 0.94 | 5 of 300 |
| version 6 | Opus 5.5 | 300 | 94% | 100% | 0.94 | 94% | 5 of 300 | 300 (all) | 94% | 100% | 0.94 | 5 of 300 |

Like for like, on the same pairs: the 66 pairs of this population whose prompt was identical in both of version 4's passes (one-trait calls, and lists that shuffled into the same order), every version on those pairs:

| version | model | pairs | exact | within one | kappa | exact (decision) | flips at 3 |
|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 66 | 95% | 100% | 0.97 | 95% | 0 of 66 |
| version 4 | Opus 5.5 | 66 | 97% | 100% | 0.98 | 97% | 1 of 66 |
| version 6 | Sonnet 5.5 | 66 | 97% | 100% | 0.97 | 97% | 1 of 66 |
| version 6 | Opus 5.5 | 66 | 95% | 100% | 0.97 | 95% | 1 of 66 |

Where the passes differ, by the two answers:

- version 4, Sonnet 5.5: 0/1 4, 1/2 22, 1/opposite 1, 2/3 10, 3/4 1
- version 4, Opus 5.5: 0/1 4, 1/2 23, 1/opposite 1, 2/3 4, 3/4 1
- version 6, Sonnet 5.5: 0/1 1, 1/2 9, 2/3 5, 3/4 1
- version 6, Opus 5.5: 0/1 1, 1/2 13, 2/3 5

Sonnet 5.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Sonnet 5.5 covers only |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 300 | 86% | 100% | 0.90 | 8 of 300 | 0 | 8 |
| version 4 | 2 | 300 | 83% | 100% | 0.87 | 14 of 300 | 6 | 8 |
| version 6 | 1 | 300 | 85% | 100% | 0.84 | 21 of 300 | 16 | 5 |
| version 6 | 2 | 300 | 82% | 100% | 0.81 | 21 of 300 | 17 | 4 |

Against version 4, the same model and pass (crossings: on different sides of 3):

| version | model | pass | both answered | exact | within one | kappa | crossings | version 4 covers only | this version covers only |
|---|---|---|---|---|---|---|---|---|---|
| version 6 | Sonnet 5.5 | 1 | 300 | 79% | 100% | 0.79 | 14 of 300 | 10 | 4 |
| version 6 | Sonnet 5.5 | 2 | 300 | 82% | 100% | 0.83 | 11 of 300 | 6 | 5 |
| version 6 | Opus 5.5 | 1 | 300 | 75% | 100% | 0.80 | 19 of 300 | 3 | 16 |
| version 6 | Opus 5.5 | 2 | 300 | 71% | 100% | 0.76 | 22 of 300 | 4 | 18 |

At 3 or more:

| version | model | pass 1 | pass 2 |
|---|---|---|---|
| version 4 | Sonnet 5.5 | 46 of 300 (15%) | 40 of 300 (13%) |
| version 4 | Opus 5.5 | 38 of 300 (13%) | 38 of 300 (13%) |
| version 6 | Sonnet 5.5 | 40 of 300 (13%) | 39 of 300 (13%) |
| version 6 | Opus 5.5 | 51 of 300 (17%) | 52 of 300 (17%) |

M3's rule (Sonnet 5.5 first, Opus 5.5 on the 3s), per pass:

| version | pass | decided | escalated | rescued | cut | of which directly | kept though Opus 5.5 reads 3+ | decision differs from version 4 (keep to cut / cut to keep) |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 300 | 42 | 8 | 38 | 4 | 0 | – |
| version 4 | 2 | 300 | 35 | 8 | 32 | 5 | 6 | – |
| version 6 | 1 | 300 | 37 | 5 | 35 | 3 | 16 | 15 of 300 (6 / 9) |
| version 6 | 2 | 300 | 35 | 4 | 35 | 4 | 17 | 7 of 300 (5 / 2) |

- version 4: the rule's decision differs between the passes on 8 of 300 pairs
- version 6: the rule's decision differs between the passes on 6 of 300 pairs

Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the same counting "neither implies the other" too, and 3s whose reason states line 2 in its own words ("each adds something", "neither implies the other"; patterns in `summary.json`).

| version | model | pass | 2s | containment reason | discounting "neither implies" | 3s | two-sided reason | or "neither implies" | line 2's words |
|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 1 | 114 | 11 of 114 (10%) | 11 of 114 (10%) | 42 | 1 of 42 (2%) | 1 of 42 (2%) | 0 of 42 (0%) |
| version 4 | Sonnet 5.5 | 2 | 124 | 21 of 124 (17%) | 21 of 124 (17%) | 35 | 0 of 35 (0%) | 0 of 35 (0%) | 0 of 35 (0%) |
| version 4 | Sonnet 5.5 | pooled | 238 | 32 of 238 (13%) | 32 of 238 (13%) | 77 | 1 of 77 (1%) | 1 of 77 (1%) | 0 of 77 (0%) |
| version 4 | Opus 5.5 | 1 | 111 | 11 of 111 (10%) | 11 of 111 (10%) | 33 | 0 of 33 (0%) | 0 of 33 (0%) | 0 of 33 (0%) |
| version 4 | Opus 5.5 | 2 | 110 | 7 of 110 (6%) | 7 of 110 (6%) | 34 | 1 of 34 (3%) | 1 of 34 (3%) | 0 of 34 (0%) |
| version 4 | Opus 5.5 | pooled | 221 | 18 of 221 (8%) | 18 of 221 (8%) | 67 | 1 of 67 (2%) | 1 of 67 (2%) | 0 of 67 (0%) |
| version 6 | Sonnet 5.5 | 1 | 157 | 13 of 157 (8%) | 9 of 157 (6%) | 37 | 12 of 37 (32%) | 12 of 37 (32%) | 4 of 37 (11%) |
| version 6 | Sonnet 5.5 | 2 | 151 | 9 of 151 (6%) | 9 of 151 (6%) | 35 | 10 of 35 (29%) | 11 of 35 (31%) | 4 of 35 (11%) |
| version 6 | Sonnet 5.5 | pooled | 308 | 22 of 308 (7%) | 18 of 308 (6%) | 72 | 22 of 72 (31%) | 23 of 72 (32%) | 8 of 72 (11%) |
| version 6 | Opus 5.5 | 1 | 141 | 2 of 141 (1%) | 1 of 141 (1%) | 45 | 3 of 45 (7%) | 3 of 45 (7%) | 0 of 45 (0%) |
| version 6 | Opus 5.5 | 2 | 143 | 5 of 143 (4%) | 4 of 143 (3%) | 46 | 5 of 46 (11%) | 5 of 46 (11%) | 0 of 46 (0%) |
| version 6 | Opus 5.5 | pooled | 284 | 7 of 284 (2%) | 5 of 284 (2%) | 91 | 8 of 91 (9%) | 8 of 91 (9%) | 0 of 91 (0%) |

Opus 5.5 on the pairs the rule escalates (Sonnet 5.5 at 3): its answers on them in that pass, and on those it answered in both passes, how often alike:

| version | escalated in | pairs | Opus 5.5's answers | answered in both passes | same answer | same side of 3 |
|---|---|---|---|---|---|---|
| version 4 | pass 1 | 42 | 2 8, 3 33, 4 1 | 42 | 38 | 39 |
| version 4 | pass 2 | 35 | 2 8, 3 27 | 35 | 32 | 33 |
| version 4 | either pass | 44 | – | 44 | 40 | 41 |
| version 6 | pass 1 | 37 | 2 5, 3 29, 4 3 | 37 | 34 | 34 |
| version 6 | pass 2 | 35 | 2 4, 3 29, 4 2 | 35 | 33 | 33 |
| version 6 | either pass | 39 | – | 39 | 36 | 36 |

### Round 2's pairs (those A2 was sent): 242 pairs

By group: nearest 219, near_distinct 14, random 1, drop_or_merge 5, duplicate 1, deliberate_duplicate 2.  Versions measured here: version 4, A2, version 6.

Self-consistency, pass 1 against pass 2 (exact over every answer; within one and kappa, quadratic, on the pairs both passes scored; flips: pairs on different sides of 3 in the two passes).  The last columns: the pairs whose prompt was identical in both passes (all of version 6's).

| version | model | both answered | exact | within one | kappa | exact (decision) | flips at 3 | identical prompts: pairs | exact | within one | kappa | flips |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 242 | 88% | 100% | 0.89 | 88% | 13 of 242 | 55 | 95% | 100% | 0.96 | 1 of 55 |
| version 4 | Opus 5.5 | 242 | 88% | 100% | 0.89 | 88% | 4 of 242 | 55 | 96% | 100% | 0.97 | 1 of 55 |
| A2 | Sonnet 5.5 | 242 | 88% | 100% | 0.90 | 88% | 10 of 242 | 55 | 96% | 100% | 0.97 | 1 of 55 |
| A2 | Opus 5.5 | 242 | 86% | 100% | 0.89 | 86% | 6 of 242 | 55 | 93% | 100% | 0.94 | 1 of 55 |
| version 6 | Sonnet 5.5 | 242 | 95% | 100% | 0.94 | 95% | 5 of 242 | 242 (all) | 95% | 100% | 0.94 | 5 of 242 |
| version 6 | Opus 5.5 | 242 | 93% | 100% | 0.92 | 93% | 6 of 242 | 242 (all) | 93% | 100% | 0.92 | 6 of 242 |

Like for like, on the same pairs: the 55 pairs of this population whose prompt was identical in both of version 4's passes (one-trait calls, and lists that shuffled into the same order), every version on those pairs:

| version | model | pairs | exact | within one | kappa | exact (decision) | flips at 3 |
|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 55 | 95% | 100% | 0.96 | 95% | 1 of 55 |
| version 4 | Opus 5.5 | 55 | 96% | 100% | 0.97 | 96% | 1 of 55 |
| A2 | Sonnet 5.5 | 55 | 96% | 100% | 0.97 | 96% | 1 of 55 |
| A2 | Opus 5.5 | 55 | 93% | 100% | 0.94 | 93% | 1 of 55 |
| version 6 | Sonnet 5.5 | 55 | 98% | 100% | 0.98 | 98% | 1 of 55 |
| version 6 | Opus 5.5 | 55 | 93% | 100% | 0.94 | 93% | 2 of 55 |

Where the passes differ, by the two answers:

- version 4, Sonnet 5.5: 0/1 2, 1/2 14, 2/3 13
- version 4, Opus 5.5: 0/1 2, 1/2 21, 1/opposite 1, 2/3 4, 3/4 1
- A2, Sonnet 5.5: 0/1 1, 1/2 17, 2/3 10, 3/4 1
- A2, Opus 5.5: 0/1 2, 1/2 22, 2/3 6, 3/4 3
- version 6, Sonnet 5.5: 0/1 1, 1/2 6, 2/3 5
- version 6, Opus 5.5: 0/1 1, 1/2 11, 2/3 6

Sonnet 5.5 against Opus 5.5 (crossings: pairs on different sides of 3, split by which model covers):

| version | pass | both answered | exact | within one | kappa | crossings at 3 | Opus 5.5 covers only | Sonnet 5.5 covers only |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 242 | 86% | 100% | 0.89 | 11 of 242 | 1 | 10 |
| version 4 | 2 | 242 | 83% | 100% | 0.85 | 18 of 242 | 7 | 11 |
| A2 | 1 | 242 | 80% | 100% | 0.83 | 24 of 242 | 4 | 20 |
| A2 | 2 | 242 | 82% | 100% | 0.86 | 16 of 242 | 3 | 13 |
| version 6 | 1 | 242 | 86% | 100% | 0.85 | 22 of 242 | 15 | 7 |
| version 6 | 2 | 242 | 81% | 100% | 0.79 | 23 of 242 | 16 | 7 |

Against version 4, the same model and pass (crossings: on different sides of 3):

| version | model | pass | both answered | exact | within one | kappa | crossings | version 4 covers only | this version covers only |
|---|---|---|---|---|---|---|---|---|---|
| A2 | Sonnet 5.5 | 1 | 242 | 84% | 100% | 0.85 | 20 of 242 | 5 | 15 |
| A2 | Sonnet 5.5 | 2 | 242 | 84% | 100% | 0.85 | 21 of 242 | 4 | 17 |
| A2 | Opus 5.5 | 1 | 242 | 80% | 99% | 0.79 | 23 of 242 | 10 | 13 |
| A2 | Opus 5.5 | 2 | 242 | 81% | 99% | 0.82 | 21 of 242 | 7 | 14 |
| version 6 | Sonnet 5.5 | 1 | 242 | 79% | 100% | 0.78 | 16 of 242 | 10 | 6 |
| version 6 | Sonnet 5.5 | 2 | 242 | 83% | 100% | 0.82 | 14 of 242 | 7 | 7 |
| version 6 | Opus 5.5 | 1 | 242 | 74% | 100% | 0.77 | 21 of 242 | 4 | 17 |
| version 6 | Opus 5.5 | 2 | 242 | 71% | 100% | 0.73 | 23 of 242 | 5 | 18 |

At 3 or more:

| version | model | pass 1 | pass 2 |
|---|---|---|---|
| version 4 | Sonnet 5.5 | 47 of 242 (19%) | 42 of 242 (17%) |
| version 4 | Opus 5.5 | 38 of 242 (16%) | 38 of 242 (16%) |
| A2 | Sonnet 5.5 | 57 of 242 (24%) | 55 of 242 (23%) |
| A2 | Opus 5.5 | 41 of 242 (17%) | 45 of 242 (19%) |
| version 6 | Sonnet 5.5 | 43 of 242 (18%) | 42 of 242 (17%) |
| version 6 | Opus 5.5 | 51 of 242 (21%) | 51 of 242 (21%) |

Known groups on the decision scale: mean of the numeric answers / share at 3 or more / share "opposite", pass 1; pass 2.

| group | n | version 4, Sonnet 5.5 | version 4, Opus 5.5 | A2, Sonnet 5.5 | A2, Opus 5.5 | version 6, Sonnet 5.5 | version 6, Opus 5.5 |
|---|---|---|---|---|---|---|---|
| nearest | 219 | 1.86 / 20% / 12%; 1.85 / 17% / 12% | 1.77 / 16% / 12%; 1.78 / 16% / 11% | 1.95 / 25% / 12%; 1.97 / 24% / 12% | 1.89 / 18% / 11%; 1.85 / 20% / 11% | 1.99 / 17% / 12%; 1.96 / 16% / 12% | 2.03 / 22% / 12%; 2.05 / 22% / 12% |
| drop_or_merge | 5 | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 2.60 / 60% / 0%; 2.60 / 60% / 0% | 2.80 / 80% / 0%; 2.80 / 80% / 0% | 2.80 / 60% / 0%; 2.80 / 60% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 2.80 / 80% / 0% |
| deliberate_duplicate | 2 | 2.50 / 50% / 0%; 2.00 / 0% / 0% | 2.50 / 50% / 0%; 2.50 / 50% / 0% | 2.50 / 50% / 0%; 2.50 / 50% / 0% | 2.50 / 50% / 0%; 2.50 / 50% / 0% | 2.50 / 50% / 0%; 2.50 / 50% / 0% | 2.50 / 50% / 0%; 2.50 / 50% / 0% |
| duplicate | 1 | 2.00 / 0% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% | 3.00 / 100% / 0%; 3.00 / 100% / 0% |
| near_distinct | 14 | 2.00 / 27% / 21%; 2.09 / 36% / 21% | 1.92 / 25% / 14%; 1.92 / 25% / 14% | 2.00 / 27% / 21%; 2.00 / 27% / 21% | 1.75 / 8% / 14%; 1.83 / 17% / 14% | 2.09 / 36% / 21%; 2.09 / 36% / 21% | 1.91 / 18% / 21%; 1.91 / 18% / 21% |
| random | 1 | 0.00 / 0% / 0%; 0.00 / 0% / 0% | 0.00 / 0% / 0%; 0.00 / 0% / 0% | 0.00 / 0% / 0%; 0.00 / 0% / 0% | 0.00 / 0% / 0%; 0.00 / 0% / 0% | 0.00 / 0% / 0%; 0.00 / 0% / 0% | 0.00 / 0% / 0%; 0.00 / 0% / 0% |

M3's rule (Sonnet 5.5 first, Opus 5.5 on the 3s), per pass:

| version | pass | decided | escalated | rescued | cut | of which directly | kept though Opus 5.5 reads 3+ | decision differs from version 4 (keep to cut / cut to keep) |
|---|---|---|---|---|---|---|---|---|
| version 4 | 1 | 242 | 45 | 10 | 37 | 2 | 1 | – |
| version 4 | 2 | 242 | 40 | 11 | 31 | 2 | 7 | – |
| A2 | 1 | 242 | 55 | 20 | 37 | 2 | 4 | 22 of 242 (11 / 11) |
| A2 | 2 | 242 | 52 | 13 | 42 | 3 | 3 | 19 of 242 (15 / 4) |
| version 6 | 1 | 242 | 41 | 7 | 36 | 2 | 15 | 19 of 242 (9 / 10) |
| version 6 | 2 | 242 | 40 | 7 | 35 | 2 | 16 | 10 of 242 (7 / 3) |

- version 4: the rule's decision differs between the passes on 10 of 242 pairs
- A2: the rule's decision differs between the passes on 7 of 242 pairs
- version 6: the rule's decision differs between the passes on 7 of 242 pairs

Slips (round 1's patterns; reasons matched case-insensitively): 2s whose reason describes a containment, and the same less the reasons that say neither implies the other; 3s whose reason describes a two-sided overlap (round 2's pattern, which also matches a two-sided difference of emphasis, as line 3 allows), the same counting "neither implies the other" too, and 3s whose reason states line 2 in its own words ("each adds something", "neither implies the other"; patterns in `summary.json`).

| version | model | pass | 2s | containment reason | discounting "neither implies" | 3s | two-sided reason | or "neither implies" | line 2's words |
|---|---|---|---|---|---|---|---|---|---|
| version 4 | Sonnet 5.5 | 1 | 100 | 13 of 100 (13%) | 13 of 100 (13%) | 45 | 1 of 45 (2%) | 1 of 45 (2%) | 0 of 45 (0%) |
| version 4 | Sonnet 5.5 | 2 | 109 | 22 of 109 (20%) | 22 of 109 (20%) | 40 | 0 of 40 (0%) | 0 of 40 (0%) | 0 of 40 (0%) |
| version 4 | Sonnet 5.5 | pooled | 209 | 35 of 209 (17%) | 35 of 209 (17%) | 85 | 1 of 85 (1%) | 1 of 85 (1%) | 0 of 85 (0%) |
| version 4 | Opus 5.5 | 1 | 101 | 12 of 101 (12%) | 12 of 101 (12%) | 35 | 0 of 35 (0%) | 0 of 35 (0%) | 0 of 35 (0%) |
| version 4 | Opus 5.5 | 2 | 102 | 8 of 102 (8%) | 8 of 102 (8%) | 36 | 1 of 36 (3%) | 1 of 36 (3%) | 0 of 36 (0%) |
| version 4 | Opus 5.5 | pooled | 203 | 20 of 203 (10%) | 20 of 203 (10%) | 71 | 1 of 71 (1%) | 1 of 71 (1%) | 0 of 71 (0%) |
| A2 | Sonnet 5.5 | 1 | 98 | 16 of 98 (16%) | 13 of 98 (13%) | 55 | 1 of 55 (2%) | 1 of 55 (2%) | 0 of 55 (0%) |
| A2 | Sonnet 5.5 | 2 | 103 | 17 of 103 (16%) | 14 of 103 (14%) | 52 | 3 of 52 (6%) | 3 of 52 (6%) | 1 of 52 (2%) |
| A2 | Sonnet 5.5 | pooled | 201 | 33 of 201 (16%) | 27 of 201 (13%) | 107 | 4 of 107 (4%) | 4 of 107 (4%) | 1 of 107 (1%) |
| A2 | Opus 5.5 | 1 | 113 | 11 of 113 (10%) | 7 of 113 (6%) | 35 | 0 of 35 (0%) | 0 of 35 (0%) | 0 of 35 (0%) |
| A2 | Opus 5.5 | 2 | 97 | 9 of 97 (9%) | 4 of 97 (4%) | 38 | 0 of 38 (0%) | 0 of 38 (0%) | 0 of 38 (0%) |
| A2 | Opus 5.5 | pooled | 210 | 20 of 210 (10%) | 11 of 210 (5%) | 73 | 0 of 73 (0%) | 0 of 73 (0%) | 0 of 73 (0%) |
| version 6 | Sonnet 5.5 | 1 | 132 | 14 of 132 (11%) | 10 of 132 (8%) | 41 | 12 of 41 (29%) | 12 of 41 (29%) | 4 of 41 (10%) |
| version 6 | Sonnet 5.5 | 2 | 129 | 11 of 129 (8%) | 10 of 129 (8%) | 40 | 12 of 40 (30%) | 13 of 40 (32%) | 5 of 40 (12%) |
| version 6 | Sonnet 5.5 | pooled | 261 | 25 of 261 (10%) | 20 of 261 (8%) | 81 | 24 of 81 (30%) | 25 of 81 (31%) | 9 of 81 (11%) |
| version 6 | Opus 5.5 | 1 | 123 | 4 of 123 (3%) | 2 of 123 (2%) | 48 | 3 of 48 (6%) | 3 of 48 (6%) | 0 of 48 (0%) |
| version 6 | Opus 5.5 | 2 | 124 | 8 of 124 (6%) | 5 of 124 (4%) | 48 | 5 of 48 (10%) | 5 of 48 (10%) | 0 of 48 (0%) |
| version 6 | Opus 5.5 | pooled | 247 | 12 of 247 (5%) | 7 of 247 (3%) | 96 | 8 of 96 (8%) | 8 of 96 (8%) | 0 of 96 (0%) |

Opus 5.5 on the pairs the rule escalates (Sonnet 5.5 at 3): its answers on them in that pass, and on those it answered in both passes, how often alike:

| version | escalated in | pairs | Opus 5.5's answers | answered in both passes | same answer | same side of 3 |
|---|---|---|---|---|---|---|
| version 4 | pass 1 | 45 | 2 10, 3 34, 4 1 | 45 | 41 | 42 |
| version 4 | pass 2 | 40 | 2 11, 3 29 | 40 | 37 | 38 |
| version 4 | either pass | 49 | – | 49 | 45 | 46 |
| A2 | pass 1 | 55 | 2 20, 3 31, 4 4 | 55 | 47 | 50 |
| A2 | pass 2 | 52 | 2 13, 3 35, 4 4 | 52 | 45 | 47 |
| A2 | either pass | 59 | – | 59 | 51 | 54 |
| version 6 | pass 1 | 41 | 2 7, 3 33, 4 1 | 41 | 37 | 37 |
| version 6 | pass 2 | 40 | 2 7, 3 32, 4 1 | 40 | 37 | 37 |
| version 6 | either pass | 43 | – | 43 | 39 | 39 |

### Agreement with Roger's 30 marks

His leaning per item, read by hand from the sheet, with the alternative he named on five items.  Exact counts every answer ("opposite" included); within one, the items where both are numbers.

| answers | model | items | exact | within one | leaning or alternative |
|---|---|---|---|---|---|
| version 4 (overlap_test_1) | Sonnet 5.5 | 30 | 19 of 30 (63%) | 23 of 23 (100%) | 21 of 30 (70%) |
| version 4 (overlap_test_1) | Opus 5.5 | 30 | 18 of 30 (60%) | 23 of 23 (100%) | 20 of 30 (67%) |
| version 4 (overlap_arms_1, pass 1) | Sonnet 5.5 | 30 | 18 of 30 (60%) | 23 of 23 (100%) | 20 of 30 (67%) |
| version 4 (overlap_arms_1, pass 1) | Opus 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 22 of 30 (73%) |
| version 4 (overlap_arms_1, pass 2) | Sonnet 5.5 | 30 | 21 of 30 (70%) | 23 of 23 (100%) | 23 of 30 (77%) |
| version 4 (overlap_arms_1, pass 2) | Opus 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 22 of 30 (73%) |
| version 6, pass 1 | Sonnet 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 23 of 30 (77%) |
| version 6, pass 1 | Opus 5.5 | 30 | 22 of 30 (73%) | 23 of 23 (100%) | 25 of 30 (83%) |
| version 6, pass 2 | Sonnet 5.5 | 30 | 20 of 30 (67%) | 23 of 23 (100%) | 23 of 30 (77%) |
| version 6, pass 2 | Opus 5.5 | 30 | 21 of 30 (70%) | 23 of 23 (100%) | 24 of 30 (80%) |

Per item:

| item | target / listed | Roger (alternative) | version 4 (overlap_test_1), Sonnet 5.5 | version 4 (overlap_test_1), Opus 5.5 | version 4 (overlap_arms_1, pass 1), Sonnet 5.5 | version 4 (overlap_arms_1, pass 1), Opus 5.5 | version 4 (overlap_arms_1, pass 2), Sonnet 5.5 | version 4 (overlap_arms_1, pass 2), Opus 5.5 | version 6, pass 1, Sonnet 5.5 | version 6, pass 1, Opus 5.5 | version 6, pass 2, Sonnet 5.5 | version 6, pass 2, Opus 5.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | self-blaming / blame-shifting | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 2 | erudite / esoteric | 1 (2) | 2 | 1 | 1 | 1 | 2 | 1 | 2 | 2 | 2 | 2 |
| 3 | utilitarian / deontological | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 4 | animated / flat | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 5 | conservative / overconfident | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 6 | materialist / relativist | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | excitable / narrative | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 8 | religious / secular | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 9 | extroverted / energetic | 0 | 1 | 1 | 1 | 0 | 0 | 0 | 1 | 1 | 1 | 1 |
| 10 | temperamental / even-tempered | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 11 | iconoclastic / deconstructionist | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 |
| 12 | ethereal / spiritual | 1 | 1 | 1 | 2 | 1 | 1 | 1 | 2 | 1 | 1 | 1 |
| 13 | strategic / long-term oriented | 1 (2) | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| 14 | agreeable / conciliatory | 2 | 3 | 3 | 3 | 3 | 2 | 2 | 2 | 2 | 2 | 3 |
| 15 | dispassionate / detached | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| 16 | nihilistic / essentialist | opposite | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 17 | hedonistic / self-indulgent | 3 (2) | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 18 | consequentialist / ends justify means | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| 19 | deconstructionist / structuralist | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| 20 | benevolent / benign | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 |
| 21 | honorable / deontological | 2 (3) | 2 | 2 | 3 | 3 | 2 | 3 | 3 | 3 | 3 | 3 |
| 22 | adventurous / adventurous-eater | 2 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 3 | 3 | 3 |
| 23 | strategic / tactical | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite | opposite |
| 24 | moral relativist / relativist | 4 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 25 | serious / formal | 3 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 3 | 2 | 3 |
| 26 | socratic / educational | 2 | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 2 | 1 | 2 |
| 27 | extroverted / gregarious | 3 (2) | 3 | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| 28 | theoretical / conceptual | 4 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| 29 | cosmopolitan / philanthropic | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 30 | moderate / temperate | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 2 | 2 | 2 | 2 |

### Where Opus 5.5's answer under version 6 changes the rule's decision against version 4

Pairs whose Opus 5.5 answers under the two versions fall on different sides of 3 while Sonnet 5.5 sends the pair to Opus 5.5 under either version (so that, Sonnet 5.5's answer held, Opus 5.5's change flips the decision); in pair order.  "Opus 5.5 changes side" counts every pair where its answers cross 3, escalated or not.

- pass 1: 13 pairs (Opus 5.5 changes side on 22)
- pass 2: 10 pairs (Opus 5.5 changes side on 24)

The first 6 in pass 1, both Opus 5.5 reasons in full:

- **agreeable / conciliatory** (nearest): Sonnet 5.5 version 4 3, version 6 2; the rule: version 4 cut, version 6 keep.  Opus 5.5 version 4, 3: "Both seek peaceful resolution and common ground, but conciliatory is specifically about making peace between conflicting parties, a narrower, active form of agreeableness."  Opus 5.5 version 6, 2: "Both centre on seeking harmony and common ground. Agreeable is a broad disposition to avoid confrontation, while conciliatory means actively making peace, often between other opposing parties, so each adds something the other lacks."
- **benevolent / altruistic** (nearest): Sonnet 5.5 version 4 3, version 6 3; the rule: version 4 keep, version 6 cut.  Opus 5.5 version 4, 2: "Both center on concern for others' wellbeing, but altruistic adds selflessness over personal gain while benevolent adds ethical kindness toward all involved."  Opus 5.5 version 6, 3: "Both describe concern for others' wellbeing, but altruistic stresses selflessness over personal gain while benevolent stresses kindness and ethical goodwill toward all involved, so the two overlap heavily without being identical."
- **calm / placid** (nearest): Sonnet 5.5 version 4 3, version 6 3; the rule: version 4 keep, version 6 cut.  Opus 5.5 version 4, 2: "Placid shares the unruffled core but focuses specifically on slowness to anger and patience with irritants, rather than de-escalating disputes."  Opus 5.5 version 6, 3: "Both describe an even, unruffled temperament, but placid narrows it to being slow to anger at small irritations, while calm covers general steadiness and de-escalation."
- **entertaining / witty** (nearest): Sonnet 5.5 version 4 2, version 6 3; the rule: version 4 keep, version 6 cut.  Opus 5.5 version 4, 2: "Witty is one specific route to being entertaining, clever verbal humor, so it is a narrower form of the same aim."  Opus 5.5 version 6, 3: "Witty is a narrower form of being entertaining, achieved specifically through clever verbal humor, while entertaining also covers playful tone and interesting examples."
- **formalist / ritualistic** (nearest): Sonnet 5.5 version 4 3, version 6 3; the rule: version 4 keep, version 6 cut.  Opus 5.5 version 4, 2: "Both prefer established procedures and structured methods over spontaneity; ritualistic adds a ceremonial, traditional flavour and formalist adds a downplaying of substance."  Opus 5.5 version 6, 3: "Both centre on preferring established procedures and formal structure over flexibility or spontaneity; ritualistic adds only a ceremonial, traditional emphasis."
- **honest / intellectually honest** (nearest): Sonnet 5.5 version 4 2, version 6 3; the rule: version 4 keep, version 6 cut.  Opus 5.5 version 4, 2: "Both share truthfulness and admitting uncertainty, but intellectual honesty adds self-scrutiny about one's own work and weighing evidence fairly, while honest adds avoiding deception toward others in general."  Opus 5.5 version 6, 3: "Intellectual honesty is honesty narrowed to one's own work and reasoning, adding self-honesty and fair weighing of evidence, so it is largely a scoped version of the same concept."

The others in pass 1 (Opus 5.5 version 4 → version 6): nationalist / regionalist 3 → 2; provocative / edgy 2 → 3; theatrical / melodramatic 3 → 2; zealous / passionate 2 → 3; compassionate / empathetic 2 → 3; clannish / cliqueish 3 → 2; sardonic / sarcastic 2 → 3

## Parse rates (pairs whose answer parsed)

| rubric | model | ok / total | rate | first attempt |
|---|---|---|---|---|
| A | Opus 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |
| A | Sonnet 5.5 | 409 / 409 | 1.0000 | 409 / 409 (1.0000) |

## Agreement with Opus 5.5

Exact agreement over every answer (categories included); then, on the pairs where both gave a number, exact, within one point, the mean difference (model minus reference) and the weighted kappa (quadratic; linear in brackets).

| rubric | model | both parsed | exact (all) | both numeric | exact | within one | mean diff | kappa |
|---|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 87% | 325 | 84% | 100% | -0.02 | 0.91 (0.84) |

Categorical answers against the reference (rows: reference; columns: model):

- rubric A, Sonnet 5.5: numeric: numeric 325, opposite 3; opposite: opposite 81

## Spearman correlation with the persona-space and the embedding cosine

Numeric answers only; 95% interval from a bootstrap that resamples targets.  Populations: all pairs; without recorded opposites (clean pairs, labelled antonyms); the nearest-neighbour pairs; the nearest pairs without recorded opposites.

| rubric | model | cosine | all | without opposites | nearest | nearest without opposites |
|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | persona | 0.63 [0.51, 0.73] (n 234) | 0.63 [0.51, 0.73] (n 234) | 0.55 [0.42, 0.66] (n 198) | 0.55 [0.42, 0.66] (n 198) |
| A | Sonnet 5.5 | embedding | 0.69 [0.60, 0.76] (n 325) | 0.69 [0.60, 0.76] (n 325) | 0.54 [0.44, 0.63] (n 256) | 0.54 [0.44, 0.63] (n 256) |
| A | Opus 5.5 | persona | 0.67 [0.56, 0.75] (n 236) | 0.67 [0.56, 0.75] (n 236) | 0.62 [0.51, 0.71] (n 200) | 0.62 [0.51, 0.71] (n 200) |
| A | Opus 5.5 | embedding | 0.70 [0.62, 0.76] (n 328) | 0.70 [0.62, 0.76] (n 328) | 0.57 [0.47, 0.65] (n 258) | 0.57 [0.47, 0.65] (n 258) |

## Rubric A against rubric B on the same pairs

rho(A) - rho(B) against each cosine, on the pairs without recorded opposites where both rubrics gave a number; paired 95% bootstrap interval (targets resampled).

| model | population | cosine | n | rho A | rho B | A - B | 95% interval |
|---|---|---|---|---|---|---|---|

## Known groups, rubric A

Mean of the numeric answers / share at 3 or more / share opposite / share unsure; n in the first column.

| group | n | Sonnet 5.5 | Opus 5.5 |
|---|---|---|---|
| nearest | 300 | 1.92 / 16% / 15% / 0% | 1.93 / 20% / 14% / 0% |
| drop_or_merge | 11 | 3.20 / 100% / 9% / 0% | 3.30 / 100% / 9% / 0% |
| deliberate_duplicate | 3 | 2.33 / 33% / 0% / 0% | 2.33 / 33% / 0% / 0% |
| duplicate | 1 | 3.00 / 100% / 0% / 0% | 3.00 / 100% / 0% / 0% |
| near_distinct | 34 | 1.54 / 19% / 24% / 0% | 1.54 / 12% / 24% / 0% |
| antonym | 30 | – / – / 100% / 0% | – / – / 100% / 0% |
| random | 30 | 0.17 / 0% / 3% / 0% | 0.13 / 0% / 0% / 0% |

Answer counts, Opus 5.5:

- nearest: 0 8, 1 58, 2 141, 3 45, 4 6, opposite 42
- drop_or_merge: 3 7, 4 3, opposite 1
- deliberate_duplicate: 2 2, 3 1
- duplicate: 3 1
- near_distinct: 0 2, 1 12, 2 9, 3 2, 4 1, opposite 8
- antonym: opposite 30
- random: 0 27, 1 2, 2 1

## Unsure and opposite rates

| rubric | model | n | unsure | opposite | opposite on the antonym group | opposite on nearest recorded opposites | opposite elsewhere |
|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 409 | 0% (0) | 20% (84) | 100% of 30 | 100% of 31 | 7% of 348 |
| A | Opus 5.5 | 409 | 0% (0) | 20% (81) | 100% of 30 | 100% of 31 | 6% of 348 |

## Rubric A (Opus 5.5): cosines by answer

| answer | n | mean embedding cosine | n with vectors | mean persona-space cosine |
|---|---|---|---|---|
| 0 | 37 | 0.081 | 12 | 0.191 |
| 1 | 72 | 0.323 | 57 | 0.430 |
| 2 | 153 | 0.383 | 119 | 0.563 |
| 3 | 56 | 0.522 | 38 | 0.787 |
| 4 | 10 | 0.629 | 10 | 0.861 |
| opposite | 81 | 0.394 | 44 | 0.028 |

## The same pair in two calls

- rubric A: Sonnet 5.5 36 of 38 the same; Opus 5.5 37 of 38 the same

## The arms experiment: 2 passes, decision scale, cut-off 3

Rubric A went out one pair per call (the single form): every later pass sent the identical prompt, there being no list to reorder, so the agreement between the passes is sampling noise alone.

The decision scale is rubric A's 0-4 with "opposite" and "unsure"; every rubric here answers on it directly.  Covered means 3 or more on it ("opposite" is not covered, "unsure" neither), over the nearest-neighbour pairs.  The native scale is each rubric's own answers.  Exact agreement counts every answer, categories included.

### Cross-arm table

| arm | model | consistency, exact (native) | consistency, exact (decision) | between-pass flips at 3 | agreement, exact, pass 1 (native / decision) | agreement, pass 2 | covered at 3, pass 1 | targets covered, pass 1 | between-model crossings at 3 (pass 1 / pass 2) |
|---|---|---|---|---|---|---|---|---|---|
| A | Sonnet 5.5 | 95% (409) | 95% | 5 of 300 | 87% / 87% | 85% / 85% | 40 of 300 (13%) | 31 of 100 | 21 of 300 / 21 of 300 |
| A | Opus 5.5 | 95% (409) | 95% | 5 of 300 | 87% / 87% | 85% / 85% | 51 of 300 (17%) | 41 of 100 | 21 of 300 / 21 of 300 |

Agreement is each model against the other one (Sonnet 5.5 against Opus 5.5 in this experiment); crossings are the nearest pairs the two models put on different sides of the cut-off, flips the nearest pairs one model put on different sides in its two passes.

### Parse rates by pass

| rubric | model | pass | ok / total | first attempt |
|---|---|---|---|---|
| A | Opus 5.5 | 1 | 409 / 409 | 409 / 409 |
| A | Sonnet 5.5 | 1 | 409 / 409 | 409 / 409 |
| A | Opus 5.5 | 2 | 409 / 409 | 409 / 409 |
| A | Sonnet 5.5 | 2 | 409 / 409 | 409 / 409 |

### Arm A: overlap_concept (concept similarity)

Self-consistency, pass 1 against pass 2 (pairs both passes answered; mean difference pass 2 minus pass 1; kappa quadratic):

| model | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | flips at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 409 | 95% | 100% | -0.02 | 0.96 | 95% | 100% | 5 of 300 (3 covered in pass 1 only, 2 in pass 2 only) |
| Opus 5.5 | 409 | 95% | 100% | 0.01 | 0.96 | 95% | 100% | 5 of 300 (2 covered in pass 1 only, 3 in pass 2 only) |

Where the passes differ, by the two answers (native; then decision):

- Sonnet 5.5: 0/1 2, 0/opposite 1, 1/2 10, 2/3 5, 3/4 2 (19 of 20 between neighbouring points); decision: 0/1 2, 0/opposite 1, 1/2 10, 2/3 5, 3/4 2
- Opus 5.5: 0/1 3, 1/2 13, 2/3 6 (22 of 22 between neighbouring points); decision: 0/1 3, 1/2 13, 2/3 6

Exact agreement between the passes by how pass 2 sent the pair's call (native / decision; pairs): a call of one trait and a longer call whose order came out the same were the same prompt asked again; a reordered call was another prompt:

| model | one trait | same order by chance | reordered |
|---|---|---|---|
| Sonnet 5.5 | 95% / 95% (409) | – / – (0) | – / – (0) |
| Opus 5.5 | 95% / 95% (409) | – / – (0) | – / – (0) |

Sonnet 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- adventurous / adventurous-eater: 2, 3
- entertaining / witty: 3, 2
- formalist / ritualistic: 3, 2
- perfectionist / meticulous: 2, 3
- theatrical / melodramatic: 3, 2

Opus 5.5's nearest pairs on different sides of 3 in the two passes (pass 1, pass 2):

- agreeable / conciliatory: 2, 3
- clannish / cliqueish: 2, 3
- nationalist / civilizationist: 3, 2
- sarcastic / sardonic: 3, 2
- theatrical / melodramatic: 2, 3

Sonnet 5.5 against Opus 5.5 (pairs both answered; mean difference Sonnet 5.5 minus Opus 5.5):

| pass | both answered | exact (native) | within one (native) | mean diff | kappa | exact (decision) | within one (decision) | crossings at 3, nearest |
|---|---|---|---|---|---|---|---|---|
| 1 | 409 | 87% | 100% | -0.02 | 0.91 | 87% | 100% | 21 of 300 (16 Opus 5.5 covered only, 5 Sonnet 5.5 covered only) |
| 2 | 409 | 85% | 100% | -0.05 | 0.90 | 85% | 100% | 21 of 300 (17 Opus 5.5 covered only, 4 Sonnet 5.5 covered only) |

Where they differ, by the two answers (native):

- pass 1: 0/1 7, 0/opposite 1, 1/2 18, 1/opposite 2, 2/3 23, 3/4 4
- pass 2: 0/1 2, 0/opposite 2, 1/2 31, 1/opposite 2, 2/3 24, 3/4 2

Pass 1, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- adventurous / adventurous-eater: 3, 2
- anxious / neurotic: 3, 2
- clannish / cliqueish: 2, 3
- clannish / insular: 2, 3
- cruel / callous: 3, 2
- decisive / confident: 3, 2
- ecocentric / environmental: 3, 2
- environmental / ecocentric: 3, 2
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- indecisive / uncertain: 3, 2
- independent / self-reliant: 3, 2
- innovative / creative: 2, 3
- methodical / organized: 3, 2
- nationalist / regionalist: 2, 3
- nationalist / civilizationist: 3, 2
- perfectionist / meticulous: 3, 2
- serious / formal: 3, 2
- theatrical / melodramatic: 2, 3
- wry / witty: 3, 2
- zealous / passionate: 3, 2

Pass 2, nearest pairs on different sides of 3 (Opus 5.5, Sonnet 5.5):

- agreeable / conciliatory: 3, 2
- anxious / neurotic: 3, 2
- clannish / insular: 2, 3
- cruel / callous: 3, 2
- decisive / confident: 3, 2
- ecocentric / environmental: 3, 2
- entertaining / witty: 3, 2
- environmental / ecocentric: 3, 2
- formalist / ritualistic: 3, 2
- gluttonous / self-indulgent: 3, 2
- goofy / playful: 3, 2
- indecisive / uncertain: 3, 2
- independent / self-reliant: 3, 2
- innovative / creative: 2, 3
- methodical / organized: 3, 2
- nationalist / regionalist: 2, 3
- sarcastic / sardonic: 2, 3
- serious / formal: 3, 2
- theatrical / melodramatic: 3, 2
- wry / witty: 3, 2
- zealous / passionate: 3, 2

Coverage at 3, nearest pairs:

| model | pass | answered | covered | share | targets covered | opposite | unsure |
|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 300 | 40 | 13% | 31 of 100 | 44 | 0 |
| Sonnet 5.5 | 2 | 300 | 39 | 13% | 32 of 100 | 44 | 0 |
| Opus 5.5 | 1 | 300 | 51 | 17% | 41 of 100 | 42 | 0 |
| Opus 5.5 | 2 | 300 | 52 | 17% | 41 of 100 | 42 | 0 |

Kinds of difference the reasons of 3s name (not asked: rubric A's 3s, as a control; a word search, a reason may name several):

| model | pass | 3s | narrowed | broadened | stronger | milder | emphasis | none | several |
|---|---|---|---|---|---|---|---|---|---|
| Sonnet 5.5 | 1 | 51 | 3 | 9 | 1 | 1 | 29 | 12 (24%) | 4 |
| Sonnet 5.5 | 2 | 48 | 6 | 5 | 1 | 1 | 24 | 13 (27%) | 2 |
| Opus 5.5 | 1 | 56 | 10 | 11 | 8 | 0 | 22 | 13 (23%) | 8 |
| Opus 5.5 | 2 | 56 | 9 | 7 | 8 | 0 | 21 | 15 (27%) | 4 |
