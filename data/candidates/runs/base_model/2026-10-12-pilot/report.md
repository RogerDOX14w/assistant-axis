# Base-model generator: run `2026-10-12-pilot` readout

Plan: [coding_plan_03_base_model.md](../../../../../reports/trait_gap_generation/coding_plan_03_base_model.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Round 1, prompts version 1, temperature [1.0], model `Qwen/Qwen3-8B-Base`.  Table [candidate_table_round1.jsonl](../../../base_model/candidate_table_round1.jsonl); stats [stats_round1.json](../../../base_model/stats_round1.json).

**M1** is the platform's trait-hood filter, **M3** its novelty check.  The [rarefaction curve](../../../../../reports/trait_gap_generation/glossary.md#rarefaction-curve) counts distinct words against samples drawn; [Chao1](../../../../../reports/trait_gap_generation/glossary.md#chao1) estimates the vocabulary reachable; the [collapse index](../../../../../reports/trait_gap_generation/glossary.md#collapse-index) is the share of emissions taken by the top 50 words (target under 15%).

## Yield

| measure | value |
|---|---|
| samples | 2000 |
| raw items | 22184 |
| distinct stems (uniques) | 3900 (1950.0 per 1k samples) |
| eligible | 3825 |
| count floor | count >= 8 at 2,000 samples (4.0 per 1,000 samples); the sample size it was chosen at was not recorded; a run before the floor was recorded (2026-10-12) |
| submitted | 467 |
| collapse index (top 50) | 23.0% |
| Chao1 (all / eligible) | 10524.9 / 10040.7 |
| rarefaction | [[1000, 2524], [2000, 3900]] |
| noun share: uniques / eligible / M1 survivors (submitted; eligible table before the floor) | 8.0% / 8.1% / 0.4%; 2.8% |
| recovery by string (corpus stems found) | 420 of 932 (45.1%) |

## The biography-echo screen

Dropped as a **name echo** (a one-word candidate matching a word of the person's name): 3 emissions over 3 distinct words.  Dropped as a **biography span** (a multiword label appearing verbatim in the biography): 1 (the spans themselves are not listed: they are verbatim CC BY-SA prose).

The words the name rule dropped, most often first: `aziz` (1), `hakeem` (1), `jeffries` (1).

**Words lost altogether** — dropped as a name echo and never emitted from another seed (3): `aziz`, `hakeem`, `jeffries`.  This list *is* the whitelist QUESTIONS 54 asks for: these words, and only these, cost the run anything.

## The gloss sense (settled before M1)

336 rows carried two glosses (OEWN's person-descriptive sense and the model's own); the cosine screen called 44 of 336 divergent (rate 13.1%), and one cheap call settled each: 35 took the sample's reading, 9 the dictionary's.  Still unresolved: 0 (submission refuses while any remain).  The criterion is fidelity first, subject to legibility, and never novelty.

## M1 and M3

M1 filtered 467 of 467 rows: verdicts {'reject': 2, 'tagged': 21, 'trait': 444}; **measured pass rate 95.1%** (the estimate assumed 80%, with 95% printed as its high case); alignment scores {'0': 178, '1': 131, '2': 70, '3': 65}.
M3 scored 461: {'covered': 344, 'new': 117}; pair completions 12; relation-call opposites 0.

## By family: the `wiki_bio` prompts against the clean ones

The `person` family's prompts are biography openings as `wiki_bio` stores them (tokenized and lower-cased, with only the name and sentence starts restored), so its numbers beside the clean-prompt families (`list_gloss`, `occupation`, `ai_assistant`) are a within-run control for whether that casing hurts: the model continues the prompt, so degraded orthography invites degraded continuation.  The `ai_assistant` row is also the in-or-out call of plan 03 section 9.2.  The submitted, M1 and M3 columns count the **submitted rows**, which passed the count floor; the next section reads the same families over the eligible table before it.

| family | prompts | samples | uniques/1k | eligible/1k | malformed | ineligible | submitted | M1 trait rate | alignment scores | M3 decisions | M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | AI assistant (clean) | 397 | 1783.4 | 1778.3 | 0.0% | 0.3% | 39 | 100.0% | {'0': 17, '1': 12, '2': 4, '3': 6} | {'covered': 33, 'new': 6} | 15.4% |
| contrast | contrast sentence (clean) | 311 | 945.3 | 942.1 | 0.0% | 0.3% | 8 | 100.0% | {'0': 3, '1': 1, '3': 4} | {'covered': 5, 'new': 3} | 37.5% |
| list | trait list (clean) | 313 | 5431.3 | 5313.1 | 0.0% | 2.2% | 171 | 91.8% | {'0': 69, '1': 49, '2': 20, '3': 19} | {'covered': 122, 'new': 45} | 27.0% |
| list_gloss | glossary (clean) | 266 | 3375.9 | 3364.7 | 0.0% | 0.3% | 64 | 95.3% | {'0': 23, '1': 19, '2': 9, '3': 10} | {'covered': 45, 'new': 18} | 28.6% |
| occupation | professions (clean) | 294 | 4142.9 | 4122.4 | 0.0% | 0.5% | 50 | 98.0% | {'0': 15, '1': 15, '2': 12, '3': 7} | {'covered': 33, 'new': 17} | 34.0% |
| **person** | wiki_bio opening (lower-cased) | 419 | 4257.8 | 4193.3 | 0.0% | 1.5% | 135 | 96.3% | {'0': 51, '1': 35, '2': 25, '3': 19} | {'covered': 106, 'new': 28} | 20.9% |

If those numbers say casing matters, the first iteration move is free and deterministic: OEWN lists proper adjectives capitalised, so a lookup against the WordNet lemmas already on disk restores nationalities, languages and eponyms with no truecasing model and no API spend.  Not built yet, by decision (QUESTIONS 61).

## By family, before the count floor (the eligible table)

All 3825 eligible rows, 469 of them at or above the floor of 8.  The M1 and M3 rates are read from every verdict the registry holds for these keys, whichever run judged them, so each rests on the **judged** column, not on every row: rows no run has judged are counted, never guessed.  **Only here** is the rows no other family emitted, which is what the family adds (the `ai_assistant` in-or-out call, plan 03 section 9.2).

| family | eligible | at floor | nouns | M1-judged | M1 trait rate | M3-decided | M3 new rate | only here: eligible / at floor / M1-judged | only here: M1 trait rate | only here: M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | 706 | 193 | 84 | 389 | 92.3% | 362 | 33.1% | 396 / 1 / 79 | 77.2% | 55.0% |
| contrast | 293 | 79 | 23 | 165 | 83.0% | 146 | 29.4% | 148 / 0 / 20 | 60.0% | 57.1% |
| list | 1663 | 457 | 42 | 1397 | 87.7% | 1284 | 36.1% | 564 / 1 / 298 | 79.2% | 47.4% |
| list_gloss | 895 | 313 | 37 | 783 | 87.6% | 715 | 37.5% | 273 / 0 / 161 | 70.8% | 53.6% |
| occupation | 1212 | 413 | 22 | 942 | 89.7% | 882 | 34.4% | 385 / 0 / 115 | 82.6% | 51.0% |
| **person** | 1757 | 447 | 125 | 1288 | 88.6% | 1190 | 38.9% | 726 / 0 / 257 | 77.8% | 59.0% |

**Noun share of M1 survivors before the floor**: 2.8% of 1911 eligible rows M1 called a trait (any run); 69 of the 310 eligible nouns have an M1 verdict.  This, not the share among the submitted rows, is the number that gates the noun-normalization follow-up (plan 03 task 11).


## Cost

Total $0.1980 from the usage records [usage.json](usage.json), [usage.json](../../../filter/2026-10-12-pilot_base_model/usage.json), [usage.json](../../../novelty/2026-10-12-pilot_base_model/usage.json), [gloss_sense_usage_round1.json](../../../base_model/gloss_sense_usage_round1.json); per candidate $0.0004; useful (M3 new or pair completion) 129, 651.5 per dollar.  The sampling itself is $0 (a local model, its tokens recorded at a zero rate); the generator's own paid calls are the gloss-sense ones, $0.0540 here.

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-12-pilot_base_model](../../../filter/2026-10-12-pilot_base_model), M3 batch [2026-10-12-pilot_base_model](../../../novelty/2026-10-12-pilot_base_model)
- [roger_sample.md](roger_sample.md): 100 rows for the spot check
