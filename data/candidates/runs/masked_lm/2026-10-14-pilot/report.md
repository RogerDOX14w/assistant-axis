# Masked-LM generator: run `2026-10-14-pilot` readout

Plan: [coding_plan_04_masked_lm.md](../../../../../reports/trait_gap_generation/coding_plan_04_masked_lm.md).  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  Table [mlm_table.jsonl](../../../masked_lm/mlm_table.jsonl).  Selection: top 300; 436 candidates.  **M1** is the platform's trait-hood filter, **M3** its novelty check; a **kept** term is one M3 decides `new` or `grey` (it goes to review).

## M1 and M3

M1 filtered 436 of 436 rows: verdicts {'reject': 41, 'tagged': 66, 'trait': 329}; **measured pass rate 75.5%** (the estimate assumed 88.0%); polysemy 45.2%; tags {'action': 2, 'evaluative_only': 4, 'membership': 27, 'no_persona_reading': 15, 'physical': 20, 'role_person': 6, 'state': 40, 'stretched': 19, 'too_rare': 1}.
M3 scored 336: {'covered': 173, 'new': 163}; **kept share 39.7%** of the 300 submitted words not yet in the registry (119 kept; the 136 registered stems the run also submitted are left out, QUESTIONS 82; the wave assumed 50.0%); pair completions 27.

### By Zipf band

| Zipf band | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| 1.5-2.5 | 17 | 70.6% | 41.2% | {'covered': 9, 'new': 3} |
| 2.5-3.5 | 83 | 75.9% | 36.1% | {'covered': 33, 'new': 29} |
| <1.5 | 1 | 100.0% | 0.0% | {'covered': 1} |
| >=3.5 | 335 | 75.5% | 47.8% | {'covered': 130, 'new': 131} |

### By pass

| pass | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| multiword:roberta | 369 | 76.4% | 42.0% | {'covered': 143, 'new': 144} |
| single:roberta | 61 | 68.8% | 63.9% | {'covered': 27, 'new': 17} |
| subword:roberta | 3 | 100.0% | 0.0% | {'covered': 2, 'new': 1} |
| variant_b:roberta | 3 | 66.7% | 100.0% | {'covered': 1, 'new': 1} |

### By token class

| token class | n | M1 pass rate | polysemy | M3 decisions |
|---|---|---|---|---|
| multiword | 369 | 76.4% | 42.0% | {'covered': 143, 'new': 144} |
| single | 59 | 69.5% | 66.1% | {'covered': 26, 'new': 17} |
| subword | 8 | 75.0% | 37.5% | {'covered': 4, 'new': 2} |

## Cost

Total $3.6146 from [usage.json](usage.json), [usage.json](../../../filter/2026-10-14-pilot_masked_lm/usage.json), [usage.json](../../../novelty/2026-10-14-pilot_masked_lm/usage.json); per model {'claude-haiku-5-5': {'cost_usd': 0.8203, 'prompt_tokens': 1296422, 'completion_tokens': 1381253, 'n_calls': 4493}, 'claude-opus-5-5': {'cost_usd': 0.9444, 'prompt_tokens': 55028, 'completion_tokens': 36213, 'n_calls': 251}, 'claude-sonnet-5-5': {'cost_usd': 1.8494, 'prompt_tokens': 496574, 'completion_tokens': 85621, 'n_calls': 985}, 'text-embedding-3-large': {'cost_usd': 0.0005, 'prompt_tokens': 3581, 'completion_tokens': 0, 'n_calls': 2}}; per candidate $0.0083; useful (M3 new or pair completion) 190, 52.6 per dollar.  The generator itself is $0 (a local model; its run's usage record has no calls).

Projected wave at the measured rates: 757 single words for 300 kept terms at kept share 0.3967, about $5.87 batched (single words only; the wave adds its multiword and subword rows at the same rates).

## Files

- [candidates.jsonl](candidates.jsonl), [run.json](run.json), [usage.json](usage.json), [submit_report.json](submit_report.json)
- M1 batch [2026-10-14-pilot_masked_lm](../../../filter/2026-10-14-pilot_masked_lm), M3 batch [2026-10-14-pilot_masked_lm](../../../novelty/2026-10-14-pilot_masked_lm)
- [roger_sample.md](roger_sample.md): the 50-row spot check
