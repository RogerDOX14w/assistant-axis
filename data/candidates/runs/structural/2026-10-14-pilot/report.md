# Structural run `2026-10-14-pilot`: yield-per-dollar readout

Every operator count below is over the **union of 3 samples** per trait (Roger, 2026-10-13: each trait asked independently, the answers combined by union, deduplicated by stem; no answer dropped for low support).

Written by `structural_generator.py report` (coding_plan_09 sections 10-11); figures from the registry blocks, `evaluation.json` and every `usage.json`.  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).

## Already registered (the headline)

Of the run's 499 registry rows, **403 (80.8%) were already in the registry when the run was submitted** (403 by another generator), and M1 and M3 had already decided 403 of those (100.0%): free, no review row, arrangement evidence only.  164 rows are corpus traits and 101 seed-queue entries; **88 were net-new** (not yet filtered by the registry).

## Pair completions and degree fillers first (union of 3 samples)

| what | rows | M1 trait share | novel raw | novel net | net-new rows | net-new kept share | M3 pair completions |
|---|---|---|---|---|---|---|---|
| pair completions (the opposite of a non-X or singleton trait) | 6 | 83.3% | 1 | 0 | 1 | 0.0% | 1 |
| degree fillers (the excess and deficiency of a trait) | 34 | 97.1% | 16 | 6 | 9 | 66.7% | 3 |
| the opposites of mean traits, read as triangle corners (Roger, 2026-10-13: not pairs) | 10 | 100.0% | 3 | 0 | 0 | n/a | 0 |
| opposites of traits already paired or unclassified | 12 | 91.7% | 0 | 0 | 4 | 0.0% | 0 |
| classical rows (generator A) | 416 | 96.2% | 136 | 35 | 64 | 54.7% | 20 |
| retargeted dispositions | 31 | 100.0% | 15 | 7 | 8 | 87.5% | 2 |
| principal-target dispositions (the AI-identity sub-family) | 2 | 100.0% | 1 | 0 | 0 | n/a | 0 |
| remoded dispositions (attitude, habit, speech) | 16 | 87.5% | 5 | 1 | 3 | 33.3% | 0 |

A row reached by several routes is counted under each.

## Support (union of 3 samples)

How many of a trait's samples named each label (a readout figure: nothing is filtered or ranked on it).

| operator | support 1 | support 2 | support 3 |
|---|---|---|---|
| deficiency | 8 | 5 | 7 |
| excess | 8 | 3 | 6 |
| opposite | 9 | 7 | 12 |
| remode | 9 | 5 | 2 |
| retarget | 26 | 6 | 3 |
| **all** | **60** | **26** | **30** |

## Wholly new concepts (secondary)

Novel after the scorer (M3 `new` or `grey`): **163 raw**, **48 net** of other generators' candidates of the same stem (92 pending review, 23 already reviewed); net of review-graph groups: not yet (R1 has not run).

## The net-new kept share and the re-based projections

Net-new kept share (kept rows per submitted net-new row): **54.5%** (the wave's cut assumed 0.5 until now; 48 kept).

- **The 300-kept wave** (decision 1): 550 net-new rows, about 3119 rows submitted, novel about 300 raw and 300 net, about 2.0 h of review at 150 terms an hour (plan figure, ~150 terms an hour (plan 04; coding_plan_09 decision 1)), downstream about $26.32 batched.
- **The whole table**: 499 rows, 90 net-new, about 49 kept, 0.33 h, about $0.83 batched.

## M1 and M3

M1: 499 of 499 rows filtered, 478 traits (pass rate 95.8%); verdicts {'reject': 2, 'tagged': 19, 'trait': 478}.  M3: 484 scored, decisions {'covered': 321, 'new': 163}, 25 pair completions.  Useful (new or pair completion): 188, 109.7 per dollar.

## Cost

| model | calls | cost |
|---|---|---|
| claude-haiku-5-5 | 1654 | $0.3588 |
| claude-opus-5-5 | 102 | $0.4480 |
| claude-sonnet-5-5 | 452 | $0.9075 |
| text-embedding-3-large | 2 | $0.0002 |
| **total** | | **$1.7145** |

Files read: `usage.json` (2026-10-14-pilot), `usage.json` (2026-10-14-nullrate), `usage.json` (2026-10-14-pilot_structural), `usage.json` (2026-10-14-pilot_structural)

## The free checks (evaluation.json)

- Pair recovery: 75.0% by stem of 16 directions (expected > 80%); by cosine 0.8: 75.0%; mean (any triangle corner): 66.7% of 6; other (the opposite): 80.0% of 10.
- Structure: 0 of 24 triangle corners; 0 of the 13-member sequence.
- Queue hold-out: 0.0% of 96; rejected names regenerated 0 of 139; accepted 0.0%, candidates 0.0% (never in the denominator).
- Agreement between a trait's samples (reported, never a gate): median Jaccard 0.4143 over the slots either sample answered, 60 sample pairs; by operator deficiency 0.619, excess 0.6176, opposite 0.7167, remode 0.3143, retarget 0.2273.

## Files

- [roger_sample.md](./roger_sample.md): 50 rows decided new or grey, for the manual check.
- [ai_identity_subfamily.md](./ai_identity_subfamily.md): the principal-target items, for sign-off.
