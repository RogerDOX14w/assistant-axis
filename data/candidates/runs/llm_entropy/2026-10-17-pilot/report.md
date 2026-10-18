# LLM-entropy generator, run `2026-10-17-pilot`

The readout of [coding_plan_06_llm_entropy.md](../../../../../reports/trait_gap_generation/coding_plan_06_llm_entropy.md) sections 10 and 11, built from the registry, the run's records and every `usage.json`.  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md) (label-set Jaccard, Lincoln-Petersen, net-new row, net-new kept share).  Files beside this one: [roger_sample.md](./roger_sample.md), [gloss_check.md](./gloss_check.md), [run.json](./run.json), [usage.json](./usage.json), [responses.jsonl](./responses.jsonl).

## Already registered (the headline)

Of the run's **11091** unique stems, **1410** (12.7%) are already in the registry by some generator, and 1410 of those (100.0%) were already decided by M1 and M3.  Single words registered: 65.2%; phrases: 2.8%.  Corpus traits 310, queued 217, net-new 9648.  Submitted: 1218 rows, 500 of them net-new.

## M1, M3 and the novel figure

M1 judged 1218 of 1218 submitted rows; trait share 95.2%.  M3 scored 1183: {'covered': 605, 'new': 578}.
Novel (M3 `new` or `grey`): **raw 578, net 308** (net of other generators' candidates of the same stem: 237 pending, 33 reviewed).  Net-new kept share: **61.6%** (308 kept; the wave assumed 35.0% before the pilot).

| family | rows | M1 trait share | novel raw | novel net |
|---|---|---|---|---|
| a (domain x mode) | 188 | 97.9% | 98 | 78 |
| b (person seeding) | 305 | 99.3% | 116 | 63 |
| c (multilingual) | 353 | 95.2% | 162 | 92 |
| d (verbalized sampling) | 359 | 94.2% | 201 | 107 |
| e (spelling constraints) | 709 | 94.2% | 297 | 85 |

## The model test and the cells

| cell | items | unique | semantic | cost | unique/$ | M1 trait | net-new | kept | kept share | kept/$ | label rule | parse |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a x h55 | 2148 | 1959 | n/a | $0.305 | 6420.4 | 97.9% | 87 | 56 | 64.4% | 183.53 | 8.3% | 100.0% |
| a x s55 | 791 | 766 | n/a | $0.903 | 848.2 | 99.1% | 71 | 53 | 74.7% | 58.69 | 9.6% | 100.0% |
| b x h55 | 1245 | 735 | n/a | $0.148 | 4971.6 | 99.5% | 86 | 42 | 48.8% | 284.09 | 0.8% | 100.0% |
| b x s55 | 441 | 346 | n/a | $0.529 | 654.0 | 98.9% | 75 | 41 | 54.7% | 77.5 | 0.2% | 100.0% |
| c x h55 | 2941 | 2374 | n/a | $1.342 | 1768.9 | 94.6% | 115 | 72 | 62.6% | 53.65 | 0.3% | 100.0% |
| c x s55 | 1962 | 1602 | n/a | $6.575 | 243.6 | 96.1% | 116 | 74 | 63.8% | 11.25 | 0.3% | 99.1% |
| d x h55 | 3370 | 2952 | n/a | $0.626 | 4713.5 | 94.6% | 126 | 73 | 57.9% | 116.56 | 6.2% | 100.0% |
| d x s55 | 680 | 679 | n/a | $1.410 | 481.6 | 90.6% | 53 | 42 | 79.2% | 29.79 | 17.8% | 95.0% |
| e x h55 | 1471 | 699 | n/a | $0.174 | 4016.3 | 94.0% | 87 | 47 | 54.0% | 270.05 | 0.0% | 100.0% |
| e x s55 | 673 | 652 | n/a | $1.023 | 637.5 | 94.4% | 101 | 64 | 63.4% | 62.57 | 0.4% | 100.0% |

The rest of (c) by the section 10 rule: **claude-haiku-5-5** (net-new kept rows per dollar {'claude-haiku-5-5': 53.65, 'claude-sonnet-5-5': 11.25}; ).  Roger's 30-gloss read per arm can overrule it.

## Verbalized sampling (d)

- a: 164 prompts; stage 1 unique 2594, stage 2 added 2624 (101.2%); M1 reject 2.4% stage 1 against 8.8% added; adopt by the rule: False
- e: 108 prompts; stage 1 unique 699, stage 2 added 784 (112.2%); M1 reject 6.2% stage 1 against 9.4% added; adopt by the rule: False
- all: 272 prompts; stage 1 unique 3263, stage 2 added 3390 (103.9%); M1 reject 5.4% stage 1 against 9.2% added; adopt by the rule: False

## Collapse (from collapse.json)

| family | calls | unique | semantic | Jaccard median | p90 | L-P N | seen/N | end slope | unique/$ |
|---|---|---|---|---|---|---|---|---|---|
| a | 166 | 2629 | 2551 | 0.0318 | 0.0909 | 10679.84 | 0.2462 | 14.5152 | 2175.9 |
| b | 160 | 995 | 967 | None | None | 2261.27 | 0.44 | 5.4062 | 1469.9 |
| c | 287 | 3671 | 3526 | 0.0602 | 0.1352 | 7450.43 | 0.4927 | 10.3333 | 463.7 |
| d | 272 | 3621 | 3578 | 0.0213 | 0.266 | 12175.29 | 0.2974 | 12.4815 | 1778.4 |
| e | 148 | 965 | 955 | 0.4949 | 0.737 | 1026.23 | 0.9403 | 3.9655 | 806.3 |

## Parse rates, the label rule and Zipf

- a: parse 166 of 166 (100.0%); label rule refused 255 of 2939 items {'non-ASCII': 3, 'over 4 words': 252}; single words below Zipf 3: 77.9%
- b: parse 160 of 160 (100.0%); label rule refused 11 of 1686 items {'over 4 words': 11}; single words below Zipf 3: 58.9%
- c: parse 287 of 288 (99.7%); label rule refused 15 of 4903 items {'over 4 words': 15}; single words below Zipf 3: 64.4%
- d: parse 272 of 274 (99.3%); label rule refused 329 of 4050 items {'non-ASCII': 5, 'over 4 words': 324}; single words below Zipf 3: 85.3%
- e: parse 148 of 148 (100.0%); label rule refused 3 of 2144 items {'non-ASCII': 1, 'over 4 words': 2}; single words below Zipf 3: 57.1%

## Roles (decision 1: held, not promoted)

5 rows held on the `roles` list by M1; 16 guessed `role` by most of their readings; 1 both.  See [roles_report.md](../../../llm_entropy/roles_report.md).

## Cost

- claude-haiku-5-5: $2.6109 (1070 calls)
- claude-haiku-5-5:batch: $0.7609 (8286 calls)
- claude-opus-5-5:batch: $0.9576 (546 calls)
- claude-sonnet-5-5: $10.7741 (283 calls)
- claude-sonnet-5-5:batch: $2.4136 (2451 calls)
- text-embedding-3-large: $0.0527 (109 calls)
- **total $17.5698**; useful rows (new, or read as a pair completion) 673, 38.3 per dollar

## Projections, re-based on the measured share

- the 300-kept wave: 488 net-new rows, about 1189 rows to submit, novel raw 301 / net 301, 2.0 h of review, about $10.04 batched
- the whole table: 9078 net-new rows, about 5592 kept, 37.28 h of review, about $76.90 batched
