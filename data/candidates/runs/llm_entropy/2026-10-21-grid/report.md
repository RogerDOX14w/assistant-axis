# LLM-entropy generator, run `2026-10-21-grid`

The readout of [coding_plan_06_llm_entropy.md](../../../../../reports/trait_gap_generation/coding_plan_06_llm_entropy.md) sections 10 and 11, built from the registry, the run's records and every `usage.json`.  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md) (label-set Jaccard, Lincoln-Petersen, net-new row, net-new kept share).  Files beside this one: [roger_sample.md](./roger_sample.md), [gloss_check.md](./gloss_check.md), [run.json](./run.json), [usage.json](./usage.json), [responses.jsonl](./responses.jsonl).

## Already registered (the headline)

Of the run's **35151** unique stems, **3544** (10.1%) are already in the registry by some generator, and 3535 of those (99.8%) were already decided by M1 and M3.  Single words registered: 60.5%; phrases: 3.1%.  Corpus traits 506, queued 360, net-new 31588.  Submitted: 1930 rows, 488 of them net-new.

## M1, M3 and the novel figure

M1 judged 1930 of 1930 submitted rows; trait share 97.0%.  M3 scored 1888: {'covered': 1063, 'new': 825}.
Novel (M3 `new` or `grey`): **raw 825, net 353** (net of other generators' candidates of the same stem: 408 pending, 64 reviewed).  Net-new kept share: **56.1%** (274 kept; the wave assumed 35.0% before the pilot).

| family | rows | M1 trait share | novel raw | novel net |
|---|---|---|---|---|
| a (domain x mode) | 541 | 97.4% | 273 | 179 |
| b (person seeding) | 596 | 99.5% | 214 | 100 |
| c (multilingual) | 638 | 95.9% | 246 | 110 |
| d (verbalized sampling) | 797 | 97.7% | 404 | 138 |
| e (spelling constraints) | 1282 | 97.1% | 479 | 95 |

## The model test and the cells

| cell | items | unique | semantic | cost | unique/$ | M1 trait | net-new | kept | kept share | kept/$ | label rule | parse |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a x h55 | 10780 | 9124 | n/a | $0.603 | 15142.7 | 97.4% | 206 | 139 | 67.5% | 230.69 | 8.1% | 100.0% |
| b x h55 | 6154 | 2649 | n/a | $0.364 | 7274.4 | 99.5% | 152 | 63 | 41.4% | 173.0 | 0.4% | 99.7% |
| c x h55 | 14860 | 10168 | n/a | $2.181 | 4661.9 | 95.9% | 140 | 75 | 53.6% | 34.39 | 0.7% | 100.0% |
| d x h55 | 17369 | 14077 | n/a | $1.516 | 9285.8 | 97.7% | 170 | 112 | 65.9% | 73.88 | 6.4% | 100.0% |
| e x h55 | 7754 | 2574 | n/a | $0.352 | 7317.4 | 97.1% | 126 | 69 | 54.8% | 196.15 | 0.1% | 100.0% |

The rest of (c) by the section 10 rule: **not decidable yet** (net-new kept rows per dollar {'claude-haiku-5-5': 34.39}; not decidable yet: needs both (c) arms submitted and scored by M3).  Roger's 30-gloss read per arm can overrule it.

## Verbalized sampling (d)

- a: 630 prompts; stage 1 unique 9124, stage 2 added 9492 (104.0%); M1 reject 2.9% stage 1 against 1.7% added; adopt by the rule: True
- e: 541 prompts; stage 1 unique 2572, stage 2 added 3272 (127.2%); M1 reject 7.7% stage 1 against 13.4% added; adopt by the rule: False
- all: 1171 prompts; stage 1 unique 11431, stage 2 added 12617 (110.4%); M1 reject 6.9% stage 1 against 13.5% added; adopt by the rule: False

## Collapse (from collapse.json)

| family | calls | unique | semantic | Jaccard median | p90 | L-P N | seen/N | end slope | unique/$ |
|---|---|---|---|---|---|---|---|---|---|
| a | 630 | 9124 | 8679 | 0.0297 | 0.0899 | 28825.67 | 0.3165 | 13.0397 | 15142.7 |
| b | 598 | 2649 | 2492 | None | None | 4785.08 | 0.5536 | 3.5294 | 7274.4 |
| c | 900 | 10168 | 9585 | 0.0489 | 0.1167 | 18722.59 | 0.5431 | 9.5333 | 4661.9 |
| d | 1171 | 14077 | 13814 | 0.0215 | 0.2775 | 32526.4 | 0.4328 | 11.0128 | 9285.8 |
| e | 543 | 2574 | 2524 | 0.5175 | 0.6904 | 2421.51 | 1.063 | 1.8704 | 7317.4 |

## Parse rates, the label rule and Zipf

- a: parse 630 of 630 (100.0%); label rule refused 878 of 10780 items {'non-ASCII': 3, 'over 4 words': 875}; single words below Zipf 3: 68.7%
- b: parse 598 of 600 (99.7%); label rule refused 26 of 6154 items {'over 4 words': 26}; single words below Zipf 3: 55.8%
- c: parse 900 of 900 (100.0%); label rule refused 105 of 14860 items {'over 4 words': 105}; single words below Zipf 3: 65.1%
- d: parse 1173 of 1173 (100.0%); label rule refused 1118 of 17369 items {'non-ASCII': 6, 'over 4 words': 1112}; single words below Zipf 3: 82.9%
- e: parse 543 of 543 (100.0%); label rule refused 10 of 7754 items {'non-ASCII': 4, 'over 4 words': 6}; single words below Zipf 3: 56.9%

## Roles (decision 1: held, not promoted)

17 rows held on the `roles` list by M1; 74 guessed `role` by most of their readings; 2 both.  See [roles_report.md](../../../llm_entropy/roles_report.md).

## Cost

- claude-haiku-5-5: $0.0156 (10 calls)
- claude-haiku-5-5:batch: $5.7607 (12483 calls)
- claude-opus-5-5:batch: $1.1514 (554 calls)
- claude-sonnet-5-5: $0.3341 (10 calls)
- claude-sonnet-5-5:batch: $2.1667 (2228 calls)
- text-embedding-3-large: $0.2099 (323 calls)
- **total $9.6384**; useful rows (new, or read as a pair completion) 957, 99.3 per dollar

## Projections, re-based on the measured share

- the 300-kept wave: 535 net-new rows, about 2116 rows to submit, novel raw 300 / net 300, 2.0 h of review, about $17.86 batched
- the whole table: 29575 net-new rows, about 16606 kept, 110.71 h of review, about $249.85 batched
