# Base-model generator: run `2026-10-12-pilot` readout

Plan: [coding_plan_03_base_model.md](../../../../../reports/trait_gap_generation/coding_plan_03_base_model.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Round 1, prompts version 1, temperature [1.0], model `Qwen/Qwen3-8B-Base`.  Table [candidate_table_round1.jsonl](../../../base_model/candidate_table_round1.jsonl); stats [stats_round1.json](../../../base_model/stats_round1.json).

**M1** is the platform's trait-hood filter, **M3** its novelty check.  The [rarefaction curve](../../../../../reports/trait_gap_generation/glossary.md#rarefaction-curve) counts distinct words against samples drawn; [Chao1](../../../../../reports/trait_gap_generation/glossary.md#chao1) estimates the vocabulary reachable; the [collapse index](../../../../../reports/trait_gap_generation/glossary.md#collapse-index) is the share of emissions taken by the top 50 words (target under 15%).

## Yield

| measure | value |
|---|---|
| samples | 2000 |
| raw items | 22151 |
| distinct stems (uniques) | 4052 (2026.0 per 1k samples) |
| eligible | 3863 |
| submitted | 467 |
| collapse index (top 50) | 22.7% |
| Chao1 (all / eligible) | 11054.4 / 9991.1 |
| rarefaction | [[1000, 2602], [2000, 4052]] |
| noun share: uniques / eligible / M1 survivors | 8.3% / 8.4% / 0.4% |
| recovery by string (corpus stems found) | 420 of 932 (45.1%) |

## The biography-echo screen

Dropped as a **name echo** (a one-word candidate matching a word of the person's name): 3 emissions over 3 distinct words.  Dropped as a **biography span** (a multiword label appearing verbatim in the biography): 1 (the spans themselves are not listed: they are verbatim CC BY-SA prose).

The words the name rule dropped, most often first: `aziz` (1), `hakeem` (1), `jeffries` (1).

**Words lost altogether** — dropped as a name echo and never emitted from another seed (3): `aziz`, `hakeem`, `jeffries`.  This list *is* the whitelist QUESTIONS 54 asks for: these words, and only these, cost the run anything.

## The gloss sense (settled before M1)

336 rows carried two glosses (OEWN's person-descriptive sense and the model's own); the cosine screen called 44 of 336 divergent (rate 13.1%), and one cheap call settled each: 35 took the sample's reading, 9 the dictionary's.  Still unresolved: 0 (submission refuses while any remain).  The criterion is fidelity first, subject to legibility, and never novelty.

## M1 and M3

M1 filtered 467 of 467 rows: verdicts {'reject': 2, 'tagged': 21, 'trait': 444}; **measured pass rate 95.1%** (the estimate assumed 80%, with 95% printed as its high case); alignment scores {'0': 178, '1': 131, '2': 70, '3': 65}.
M3 scored 460: {'covered': 325, 'new': 135}; pair completions 14; relation-call opposites 0.

## By family: the `wiki_bio` prompts against the clean ones

The `person` family's prompts are biography openings as `wiki_bio` stores them (tokenized and lower-cased, with only the name and sentence starts restored), so its numbers beside the clean-prompt families (`list_gloss`, `occupation`, `ai_assistant`) are a within-run control for whether that casing hurts: the model continues the prompt, so degraded orthography invites degraded continuation.  The `ai_assistant` row is also the in-or-out call of plan 03 section 9.2.

| family | prompts | samples | uniques/1k | eligible/1k | malformed | ineligible | submitted | M1 trait rate | alignment scores | M3 decisions | M3 new rate |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **ai_assistant** | AI assistant (clean) | 397 | 1914.4 | 1894.2 | 0.0% | 1.1% | 39 | 100.0% | {'0': 17, '1': 12, '2': 4, '3': 6} | {'covered': 33, 'new': 6} | 15.4% |
| contrast | contrast sentence (clean) | 311 | 945.3 | 942.1 | 0.0% | 0.3% | 8 | 100.0% | {'0': 3, '1': 1, '3': 4} | {'covered': 5, 'new': 3} | 37.5% |
| list | trait list (clean) | 313 | 5511.2 | 5226.8 | 0.0% | 5.2% | 171 | 91.8% | {'0': 69, '1': 49, '2': 20, '3': 19} | {'covered': 115, 'new': 52} | 31.1% |
| list_gloss | glossary (clean) | 266 | 3409.8 | 3360.9 | 0.0% | 1.4% | 64 | 95.3% | {'0': 23, '1': 19, '2': 9, '3': 10} | {'covered': 41, 'new': 22} | 34.9% |
| occupation | professions (clean) | 294 | 4193.9 | 4112.2 | 0.0% | 1.9% | 50 | 98.0% | {'0': 15, '1': 15, '2': 12, '3': 7} | {'covered': 32, 'new': 18} | 36.0% |
| **person** | wiki_bio opening (lower-cased) | 419 | 4346.1 | 4207.6 | 0.0% | 3.2% | 135 | 96.3% | {'0': 51, '1': 35, '2': 25, '3': 19} | {'covered': 99, 'new': 34} | 25.6% |

If those numbers say casing matters, the first iteration move is free and deterministic: OEWN lists proper adjectives capitalised, so a lookup against the WordNet lemmas already on disk restores nationalities, languages and eponyms with no truecasing model and no API spend.  Not built yet, by decision (QUESTIONS 61).


## Cost

Total $0.1968 from the usage records [usage.json](usage.json), [usage.json](../../../filter/2026-10-12-pilot_base_model/usage.json), [usage.json](../../../novelty/2026-10-12-pilot_base_model/usage.json), [gloss_sense_usage.json](../../../cache/base_model/round1/gloss_sense_usage.json); per candidate $0.0004; useful (M3 new or pair completion) 149, 757.1 per dollar.  The sampling itself is $0 (a local model, its tokens recorded at a zero rate); the generator's own paid calls are the gloss-sense ones, $0.0528 here.

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-12-pilot_base_model](../../../filter/2026-10-12-pilot_base_model), M3 batch [2026-10-12-pilot_base_model](../../../novelty/2026-10-12-pilot_base_model)
- [roger_sample.md](roger_sample.md): 100 rows for the spot check
