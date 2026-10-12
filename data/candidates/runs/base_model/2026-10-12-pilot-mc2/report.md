# Base-model generator: run `2026-10-12-pilot-mc2` readout

Plan: [coding_plan_03_base_model.md](../../../../../reports/trait_gap_generation/coding_plan_03_base_model.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Round 1, prompts version 1, temperature [1.0], model `Qwen/Qwen3-8B-Base`.  Table [candidate_table_round1.jsonl](../../../base_model/candidate_table_round1.jsonl); stats [stats_round1.json](../../../base_model/stats_round1.json).

**M1** is the platform's trait-hood filter, **M3** its novelty check.  The [rarefaction curve](../../../../../reports/trait_gap_generation/glossary.md#rarefaction-curve) counts distinct words against samples drawn; [Chao1](../../../../../reports/trait_gap_generation/glossary.md#chao1) estimates the vocabulary reachable; the [collapse index](../../../../../reports/trait_gap_generation/glossary.md#collapse-index) is the share of emissions taken by the top 50 words (target under 15%).

## Yield

| measure | value |
|---|---|
| samples | 2000 |
| raw items | 22184 |
| distinct stems (uniques) | 3900 (1950.0 per 1k samples) |
| eligible | 3825 |
| count floor | count >= 2 at 2,000 samples (1.0 per 1,000 samples); chosen at 2,000 samples; Roger, 2026-10-12, accepting gate audit 3 (reports/code_review_2026-10-12/gate_audits/base_model_table.md sections 6 and 8): a floor of 2 at 2,000 samples |
| submitted | 1540 |
| collapse index (top 50) | 23.0% |
| Chao1 (all / eligible) | 10524.9 / 10040.7 |
| rarefaction | [[1000, 2524], [2000, 3900]] |
| noun share: uniques / eligible / M1 survivors (submitted; eligible table before the floor) | 8.0% / 8.1% / 2.4%; 2.7% |
| recovery by string (corpus stems found) | 420 of 932 (45.1%) |

## The biography-echo screen

Dropped as a **name echo** (a one-word candidate matching a word of the person's name): 3 emissions over 3 distinct words.  Dropped as a **biography span** (a multiword label appearing verbatim in the biography): 1 (the spans themselves are not listed: they are verbatim CC BY-SA prose).

The words the name rule dropped, most often first: `aziz` (1), `hakeem` (1), `jeffries` (1).

**Words lost altogether** — dropped as a name echo and never emitted from another seed (3): `aziz`, `hakeem`, `jeffries`.  This list *is* the whitelist QUESTIONS 54 asks for: these words, and only these, cost the run anything.

## The gloss sense (settled before M1)

697 rows carried two glosses (OEWN's person-descriptive sense and the model's own); the cosine screen called 97 of 697 divergent (rate 13.9%), and one cheap call settled each: 83 took the sample's reading, 14 the dictionary's.  Still unresolved: 0 (submission refuses while any remain).  The criterion is fidelity first, subject to legibility, and never novelty.

## M1 and M3

M1 filtered 1540 of 1540 rows: verdicts {'reject': 25, 'tagged': 160, 'trait': 1355}; **measured pass rate 88.0%** (the estimate assumed 80%, with 95% printed as its high case); alignment scores {'0': 585, '1': 387, '2': 173, '3': 210}.
M3 scored 1408: {'covered': 832, 'new': 576}; pair completions 66; relation-call opposites 0.

## By family: the `wiki_bio` prompts against the clean ones

The `person` family's prompts are biography openings as `wiki_bio` stores them (tokenized and lower-cased, with only the name and sentence starts restored), so its numbers beside the clean-prompt families (`list_gloss`, `occupation`, `ai_assistant`) are a within-run control for whether that casing hurts: the model continues the prompt, so degraded orthography invites degraded continuation.  The `ai_assistant` row is also the in-or-out call of plan 03 section 9.2.  The submitted, M1 and M3 columns count the **submitted rows**, which passed the count floor; the next section reads the same families over the eligible table before it.

| family | prompts | samples | uniques/1k | eligible/1k | malformed | ineligible | submitted | M1 trait rate | alignment scores | M3 decisions | M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | AI assistant (clean) | 397 | 1783.4 | 1778.3 | 0.0% | 0.3% | 120 | 90.8% | {'0': 42, '1': 36, '2': 9, '3': 22} | {'covered': 70, 'new': 39} | 35.8% |
| contrast | contrast sentence (clean) | 311 | 945.3 | 942.1 | 0.0% | 0.3% | 39 | 87.2% | {'0': 15, '1': 11, '2': 2, '3': 6} | {'covered': 21, 'new': 15} | 41.7% |
| list | trait list (clean) | 313 | 5431.3 | 5313.1 | 0.0% | 2.2% | 563 | 85.3% | {'0': 224, '1': 132, '2': 56, '3': 68} | {'covered': 316, 'new': 190} | 37.5% |
| list_gloss | glossary (clean) | 266 | 3375.9 | 3364.7 | 0.0% | 0.3% | 218 | 89.5% | {'0': 79, '1': 56, '2': 26, '3': 34} | {'covered': 105, 'new': 94} | 47.2% |
| occupation | professions (clean) | 294 | 4142.9 | 4122.4 | 0.0% | 0.5% | 194 | 88.1% | {'0': 73, '1': 53, '2': 22, '3': 23} | {'covered': 100, 'new': 79} | 44.1% |
| **person** | wiki_bio opening (lower-cased) | 419 | 4257.8 | 4193.3 | 0.0% | 1.5% | 406 | 90.1% | {'0': 152, '1': 99, '2': 58, '3': 57} | {'covered': 220, 'new': 159} | 41.9% |

If those numbers say casing matters, the first iteration move is free and deterministic: OEWN lists proper adjectives capitalised, so a lookup against the WordNet lemmas already on disk restores nationalities, languages and eponyms with no truecasing model and no API spend.  Not built yet, by decision (QUESTIONS 61).

## By family, before the count floor (the eligible table)

All 3825 eligible rows, 1540 of them at or above the floor of 2.  The M1 and M3 rates are read from every verdict the registry holds for these keys, whichever run judged them, so each rests on the **judged** column, not on every row: rows no run has judged are counted, never guessed.  **Only here** is the rows no other family emitted, which is what the family adds (the `ai_assistant` in-or-out call, plan 03 section 9.2).

| family | eligible | at floor | nouns | M1-judged | M1 trait rate | M3-decided | M3 new rate | only here: eligible / at floor / M1-judged | only here: M1 trait rate | only here: M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | 706 | 347 | 84 | 387 | 92.2% | 360 | 34.2% | 396 / 37 / 77 | 76.6% | 56.9% |
| contrast | 293 | 146 | 23 | 165 | 83.0% | 146 | 31.5% | 148 / 1 / 20 | 60.0% | 57.1% |
| list | 1663 | 1186 | 42 | 1389 | 87.6% | 1269 | 39.5% | 564 / 87 / 290 | 78.6% | 51.7% |
| list_gloss | 895 | 648 | 37 | 781 | 87.6% | 711 | 40.5% | 273 / 26 / 159 | 70.4% | 54.5% |
| occupation | 1212 | 843 | 22 | 941 | 89.8% | 876 | 38.1% | 385 / 16 / 114 | 83.3% | 55.8% |
| **person** | 1757 | 1071 | 125 | 1283 | 88.5% | 1180 | 41.8% | 726 / 40 / 252 | 77.4% | 59.5% |

**Noun share of M1 survivors before the floor**: 2.7% of 1894 eligible rows M1 called a trait (any run); 67 of the 310 eligible nouns have an M1 verdict.  This, not the share among the submitted rows, is the number that gates the noun-normalization follow-up (plan 03 task 11).


## Cost

Total $3.0859 from the usage records [usage.json](usage.json), [usage.json](../../../filter/2026-10-12-pilot-mc2_base_model/usage.json), [usage.json](../../../novelty/2026-10-12-pilot-mc2_base_model/usage.json), [gloss_sense_usage.json](../../../cache/base_model/round1/gloss_sense_usage.json); per candidate $0.0020; useful (M3 new or pair completion) 642, 208.0 per dollar.  The sampling itself is $0 (a local model, its tokens recorded at a zero rate); the generator's own paid calls are the gloss-sense ones, $0.0540 here.

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-12-pilot-mc2_base_model](../../../filter/2026-10-12-pilot-mc2_base_model), M3 batch [2026-10-12-pilot-mc2_base_model](../../../novelty/2026-10-12-pilot-mc2_base_model)
- [roger_sample.md](roger_sample.md): 100 rows for the spot check
