# Masked-LM generator: run `2026-10-14-wave1` readout

Plan: [coding_plan_04_masked_lm.md](../../../../../reports/trait_gap_generation/coding_plan_04_masked_lm.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Table [mlm_table.jsonl](../../../masked_lm/mlm_table.jsonl).  Selection: kept target 300 at kept share 0.397; 1802 candidates.  **M1** is the platform's trait-hood filter, **M3** its novelty check; a **kept** term is one M3 decides `new` or `grey` (it goes to review).

## M1 and M3

M1 filtered 1856 of 1856 rows: verdicts {'reject': 214, 'tagged': 403, 'trait': 1239}; **measured pass rate 66.8%** (the estimate assumed 88.0%); polysemy 56.2%; tags {'action': 2, 'evaluative_only': 22, 'membership': 138, 'no_persona_reading': 86, 'physical': 37, 'role_person': 151, 'state': 215, 'stretched': 104}.
M3 scored 1265: {'covered': 676, 'new': 589}; **kept share 28.1%** of the 810 submitted words not yet in the registry (228 kept; the 1046 registered stems the run also submitted are left out, QUESTIONS 82; the wave assumed 50.0%); pair completions 96.

### By Zipf band

| Zipf band | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| 1.5-2.5 | 30 | 86.7% | 36.7% | {'covered': 13, 'new': 13} |
| 2.5-3.5 | 395 | 84.0% | 41.0% | {'covered': 193, 'new': 145} |
| <1.5 | 2 | 50.0% | 50.0% | {'covered': 1} |
| >=3.5 | 1426 | 61.6% | 61.0% | {'covered': 469, 'new': 430} |
| none | 3 | 33.3% | 0.0% | {'new': 1} |

### By pass

| pass | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| None | 3 | 33.3% | 0.0% | {'new': 1} |
| single:roberta | 1579 | 63.3% | 59.7% | {'covered': 528, 'new': 490} |
| subword:roberta | 214 | 86.9% | 35.0% | {'covered': 118, 'new': 75} |
| variant_b:roberta | 60 | 86.7% | 45.0% | {'covered': 30, 'new': 23} |

### By token class

| token class | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| None | 3 | 33.3% | 0.0% | {'new': 1} |
| single | 1566 | 63.7% | 60.1% | {'covered': 530, 'new': 490} |
| subword | 287 | 83.6% | 35.9% | {'covered': 146, 'new': 98} |

## Cost

Total $3.7573 from [usage.json](usage.json), [usage.json](../../../filter/2026-10-14-wave1_masked_lm/usage.json), [usage.json](../../../novelty/2026-10-14-wave1_masked_lm/usage.json); per model {'claude-haiku-5-5:batch': {'cost_usd': 0.9242, 'prompt_tokens': 2714873, 'completion_tokens': 3153753, 'n_calls': 10408}, 'claude-opus-5-5:batch': {'cost_usd': 0.5411, 'prompt_tokens': 61056, 'completion_tokens': 41898, 'n_calls': 310}, 'claude-sonnet-5-5:batch': {'cost_usd': 2.2913, 'prompt_tokens': 1407111, 'completion_tokens': 176849, 'n_calls': 2152}, 'text-embedding-3-large': {'cost_usd': 0.0007, 'prompt_tokens': 5559, 'completion_tokens': 0, 'n_calls': 3}}; per candidate $0.0021; useful (M3 new or pair completion) 685, 182.3 per dollar.  The generator itself is $0 (a local model; its run's usage record has no calls).

Projected wave at the measured rates: 1066 single words for 300 kept terms at kept share 0.2815, about $7.75 batched (single words only; the wave adds its multiword and subword rows at the same rates).

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-14-wave1_masked_lm](../../../filter/2026-10-14-wave1_masked_lm), M3 batch [2026-10-14-wave1_masked_lm](../../../novelty/2026-10-14-wave1_masked_lm)
- [roger_sample.md](roger_sample.md): the 50-row spot check
