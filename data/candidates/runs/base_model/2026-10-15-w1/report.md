# Base-model generator: run `2026-10-15-w1` readout

Plan: [coding_plan_03_base_model.md](../../../../../reports/trait_gap_generation/coding_plan_03_base_model.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Round 1, prompts version 1, temperature [1.0], model `Qwen/Qwen3-8B-Base`.  Table [candidate_table_round1.jsonl](../../../base_model/candidate_table_round1.jsonl); stats [stats_round1.json](../../../base_model/stats_round1.json).

**M1** is the platform's trait-hood filter, **M3** its novelty check.  The [rarefaction curve](../../../../../reports/trait_gap_generation/glossary.md#rarefaction-curve) counts distinct words against samples drawn; [Chao1](../../../../../reports/trait_gap_generation/glossary.md#chao1) estimates the vocabulary reachable; the [collapse index](../../../../../reports/trait_gap_generation/glossary.md#collapse-index) is the share of emissions taken by the top 50 words (target under 15%).

## Yield

| measure | value |
|---|---|
| samples | 20000 |
| raw items | 229351 |
| distinct stems (uniques) | 16554 (827.7 per 1k samples) |
| eligible | 15914 |
| count floor | count >= 2 at 20,000 samples (0.1 per 1,000 samples); chosen at 2,000 samples (**a table of another size**: 1.0 per 1,000 there); Roger, 2026-10-12, accepting gate audit 3 (reports/code_review_2026-10-12/gate_audits/base_model_table.md sections 6 and 8): a floor of 2 at 2,000 samples |
| submitted | 4486 |
| collapse index (top 50) | 22.0% |
| Chao1 (all / eligible) | 48014.0 / 44504.3 |
| rarefaction | [[1000, 2524], [2000, 3900], [3000, 5219], [4000, 6115], [5000, 6916], [6000, 7774], [7000, 8565], [8000, 9267], [9000, 10009], [10000, 10612], [11000, 11352], [12000, 11948], [13000, 12518], [14000, 13145], [15000, 13738], [16000, 14277], [17000, 14847], [18000, 15363], [19000, 15962], [20000, 16554]] |
| noun share: uniques / eligible / M1 survivors (submitted; eligible table before the floor) | 11.9% / 12.3% / 7.4%; 8.3% |
| recovery by string (corpus stems found) | 567 of 932 (60.8%) |

## The biography-echo screen

Dropped as a **name echo** (a one-word candidate matching a word of the person's name): 6 emissions over 6 distinct words.  Dropped as a **biography span** (a multiword label appearing verbatim in the biography): 15 (the spans themselves are not listed: they are verbatim CC BY-SA prose).

The words the name rule dropped, most often first: `aziz` (1), `david` (1), `hakeem` (1), `jackson` (1), `jeffries` (1), `pasha` (1).

**Words lost altogether** — dropped as a name echo and never emitted from another seed (6): `aziz`, `david`, `hakeem`, `jackson`, `jeffries`, `pasha`.  This list *is* the whitelist QUESTIONS 54 asks for: these words, and only these, cost the run anything.

## The gloss sense (settled before M1)

2460 rows carried two glosses (OEWN's person-descriptive sense and the model's own); the cosine screen called 395 of 2460 divergent (rate 16.1%), and one cheap call settled each: 347 took the sample's reading, 48 the dictionary's, 6 of them because the sample's reading was called illegible.  Still unresolved: 0 (submission refuses while any remain).  The criterion is fidelity first, subject to legibility, and never novelty.

## M1 and M3

M1 filtered 4500 of 4500 rows: verdicts {'reject': 263, 'tagged': 660, 'trait': 3577}; **measured pass rate 79.5%** (the estimate assumed 80%, with 95% printed as its high case); alignment scores {'0': 1536, '1': 1074, '2': 453, '3': 513}.
M3 scored 3732: {'covered': 1940, 'new': 1792}; pair completions 238; relation-call opposites 0.

## Waves: the measured new-kept rate per cell

This run is a wave (order **stratified**).  A cell is a count bucket (2, 3, 4-9, 10+) and the row's home family (the family that emitted it most often; a tie goes to the rarer family).  The **new-kept rate** is the share of the wave's net-new rows that M3 kept (`new` or `grey`) among those M1 and M3 have decided; rows still pending are counted apart, never guessed.  **Through this wave** pools the 1 waves on record up to this one, which is what `submit --order measured` ranks the next wave's cells by (decision (f): count no longer orders the waves).

| cell | submitted | decided | M1 trait | kept | pending | new-kept rate | through this wave: decided / kept / rate |
|---|---|---|---|---|---|---|---|
| 2|list | 46 | 46 | 32 | 16 | 0 | 34.8% | 46 / 16 / 34.8% |
| 2|list_gloss | 46 | 46 | 24 | 16 | 0 | 34.8% | 46 / 16 / 34.8% |
| 2|person | 46 | 46 | 35 | 20 | 0 | 43.5% | 46 / 20 / 43.5% |
| 2|contrast | 46 | 46 | 32 | 16 | 0 | 34.8% | 46 / 16 / 34.8% |
| 2|occupation | 46 | 46 | 33 | 19 | 0 | 41.3% | 46 / 19 / 41.3% |
| 2|ai_assistant | 46 | 46 | 28 | 17 | 0 | 37.0% | 46 / 17 / 37.0% |
| 3|list | 46 | 46 | 33 | 16 | 0 | 34.8% | 46 / 16 / 34.8% |
| 3|list_gloss | 46 | 46 | 31 | 15 | 0 | 32.6% | 46 / 15 / 32.6% |
| 3|person | 46 | 46 | 38 | 21 | 0 | 45.6% | 46 / 21 / 45.6% |
| 3|contrast | 22 | 22 | 16 | 4 | 0 | 18.2% | 22 / 4 / 18.2% |
| 3|occupation | 46 | 45 | 29 | 12 | 1 | 26.7% | 45 / 12 / 26.7% |
| 3|ai_assistant | 46 | 46 | 33 | 16 | 0 | 34.8% | 46 / 16 / 34.8% |
| 4-9|list | 46 | 46 | 34 | 17 | 0 | 37.0% | 46 / 17 / 37.0% |
| 4-9|list_gloss | 46 | 46 | 25 | 15 | 0 | 32.6% | 46 / 15 / 32.6% |
| 4-9|person | 46 | 46 | 37 | 25 | 0 | 54.4% | 46 / 25 / 54.4% |
| 4-9|contrast | 13 | 13 | 7 | 6 | 0 | 46.2% | 13 / 6 / 46.2% |
| 4-9|occupation | 46 | 45 | 39 | 19 | 1 | 42.2% | 45 / 19 / 42.2% |
| 4-9|ai_assistant | 46 | 46 | 32 | 15 | 0 | 32.6% | 46 / 15 / 32.6% |
| 10+|list | 39 | 39 | 33 | 13 | 0 | 33.3% | 39 / 13 / 33.3% |
| 10+|list_gloss | 11 | 10 | 8 | 1 | 1 | 10.0% | 10 / 1 / 10.0% |
| 10+|person | 20 | 20 | 19 | 13 | 0 | 65.0% | 20 / 13 / 65.0% |
| 10+|occupation | 18 | 18 | 14 | 9 | 0 | 50.0% | 18 / 9 / 50.0% |
| 10+|ai_assistant | 24 | 23 | 16 | 4 | 1 | 17.4% | 23 / 4 / 17.4% |
| **all cells** | 883 | 879 | 628 | 325 | 4 | 37.0% | 879 / 325 / 37.0% |

## By family: the `wiki_bio` prompts against the clean ones

The `person` family's prompts are biography openings as `wiki_bio` stores them (tokenized and lower-cased, with only the name and sentence starts restored), so its numbers beside the clean-prompt families (`list_gloss`, `occupation`, `ai_assistant`) are a within-run control for whether that casing hurts: the model continues the prompt, so degraded orthography invites degraded continuation.  The `ai_assistant` row is also the in-or-out call of plan 03 section 9.2.  The submitted, M1 and M3 columns count the **submitted rows**, which passed the count floor; the next section reads the same families over the eligible table before it.

| family | prompts | samples | uniques/1k | eligible/1k | malformed | ineligible | submitted | M1 trait rate | alignment scores | M3 decisions | M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | AI assistant (clean) | 3992 | 959.7 | 946.9 | 0.0% | 1.3% | 401 | 75.1% | {'0': 114, '1': 103, '2': 41, '3': 43} | {'covered': 161, 'new': 140} | 46.5% |
| contrast | contrast sentence (clean) | 2978 | 670.2 | 663.2 | 0.0% | 1.1% | 150 | 75.3% | {'0': 63, '1': 28, '2': 7, '3': 15} | {'covered': 68, 'new': 52} | 43.3% |
| derivation | ? | n/a | n/a | n/a | n/a | n/a | 10 | 70.0% | {'0': 3, '1': 2, '2': 2} | {'covered': 1, 'new': 6} | 85.7% |
| list | trait list (clean) | 3333 | 1757.9 | 1687.1 | 0.0% | 4.0% | 1387 | 79.2% | {'0': 487, '1': 337, '2': 130, '3': 145} | {'covered': 653, 'new': 500} | 43.4% |
| list_gloss | glossary (clean) | 2680 | 1290.7 | 1273.1 | 0.0% | 1.4% | 688 | 76.9% | {'0': 219, '1': 156, '2': 67, '3': 87} | {'covered': 263, 'new': 294} | 52.8% |
| occupation | professions (clean) | 3009 | 1834.5 | 1790.6 | 0.0% | 2.4% | 684 | 82.8% | {'0': 245, '1': 167, '2': 78, '3': 75} | {'covered': 295, 'new': 294} | 49.9% |
| **person** | wiki_bio opening (lower-cased) | 4008 | 1691.9 | 1643.2 | 0.0% | 2.9% | 1176 | 81.6% | {'0': 403, '1': 281, '2': 128, '3': 148} | {'covered': 498, 'new': 505} | 50.3% |
| suffix | ? | n/a | n/a | n/a | n/a | n/a | 4 | 50.0% | {'0': 2} | {'covered': 1, 'new': 1} | 50.0% |

If those numbers say casing matters, the first iteration move is free and deterministic: OEWN lists proper adjectives capitalised, so a lookup against the WordNet lemmas already on disk restores nationalities, languages and eponyms with no truecasing model and no API spend.  Not built yet, by decision (QUESTIONS 61).

## By family, before the count floor (the eligible table)

All 15914 eligible rows, 5925 of them at or above the floor of 2.  The M1 and M3 rates are read from every verdict the registry holds for these keys, whichever run judged them, so each rests on the **judged** column, not on every row: rows no run has judged are counted, never guessed.  **Only here** is the rows no other family emitted, which is what the family adds (the `ai_assistant` in-or-out call, plan 03 section 9.2).

| family | eligible | at floor | nouns | M1-judged | M1 trait rate | M3-decided | M3 new rate | only here: eligible / at floor / M1-judged | only here: M1 trait rate | only here: M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | 3780 | 1681 | 385 | 1441 | 82.2% | 1212 | 39.8% | 2412 / 313 / 236 | 57.2% | 60.6% |
| contrast | 1975 | 937 | 196 | 926 | 81.9% | 799 | 33.4% | 1068 / 30 / 70 | 60.0% | 48.9% |
| list | 5623 | 3975 | 568 | 3607 | 80.7% | 3048 | 45.7% | 1839 / 191 / 393 | 67.2% | 58.8% |
| list_gloss | 3412 | 2639 | 334 | 2610 | 80.9% | 2210 | 44.8% | 919 / 146 / 310 | 61.6% | 60.8% |
| occupation | 5388 | 3515 | 377 | 3079 | 83.0% | 2663 | 44.4% | 2010 / 137 / 234 | 69.7% | 59.4% |
| **person** | 6586 | 4028 | 804 | 3592 | 81.0% | 3031 | 47.6% | 2827 / 269 / 419 | 65.4% | 67.4% |

**Noun share of M1 survivors before the floor**: 8.3% of 4243 eligible rows M1 called a trait (any run); 598 of the 1962 eligible nouns have an M1 verdict.  This, not the share among the submitted rows, is the number that gates the noun-normalization follow-up (plan 03 task 11).


## Cost

Total $6.0946 from the usage records [usage.json](usage.json), [usage.json](../../../filter/2026-10-15-w1_base_model/usage.json), [usage.json](../../../novelty/2026-10-15-w1_base_model/usage.json), [gloss_sense_usage_round1.json](../../../base_model/gloss_sense_usage_round1.json); per candidate $0.0014; useful (M3 new or pair completion) 2030, 333.1 per dollar.  The sampling itself is $0 (a local model, its tokens recorded at a zero rate); the generator's own paid calls are the gloss-sense ones, $0.1391 here.

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-15-w1_base_model](../../../filter/2026-10-15-w1_base_model), M3 batch [2026-10-15-w1_base_model](../../../novelty/2026-10-15-w1_base_model)
- [roger_sample.md](roger_sample.md): 100 rows for the spot check
