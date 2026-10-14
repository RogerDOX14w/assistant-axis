# Structural run `2026-10-14-pilot`: yield-per-dollar readout

Every operator count below is over the **union of 3 samples** per trait (Roger, 2026-10-13: each trait asked independently, the answers combined by union, deduplicated by stem; no answer dropped for low support).

Written by `structural_generator.py report` (coding_plan_09 sections 10-11); figures from the registry blocks, `evaluation.json` and every `usage.json`.  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).

## Already registered (the headline)

Of the run's 499 registry rows, **403 (80.8%) were already in the registry when the run was submitted** (403 by another generator), and M1 and M3 had already decided 403 of those (100.0%): free, no review row, arrangement evidence only.  164 rows are corpus traits and 101 seed-queue entries; **88 were net-new** (not yet filtered by the registry).

## Pair completions and degree fillers first (union of 3 samples)

| what | rows | M1 trait share | novel raw | novel net | net-new rows | net-new kept share | M3 pair completions |
|---|---|---|---|---|---|---|---|
| pair completions (the opposite of a non-X or singleton trait) | 56 | 96.4% | 4 | 1 | 2 | 50.0% | 2 |
| degree fillers (the excess and deficiency of a trait) | 169 | 98.2% | 54 | 7 | 14 | 57.1% | 9 |
| the opposites of mean traits, read as triangle corners (Roger, 2026-10-13: not pairs) | 105 | 98.1% | 14 | 0 | 2 | 0.0% | 3 |
| opposites of traits already paired or unclassified | 88 | 97.7% | 5 | 1 | 3 | 33.3% | 1 |
| classical rows (generator A) | 416 | 96.2% | 136 | 34 | 64 | 54.7% | 20 |
| retargeted dispositions | 144 | 100.0% | 49 | 5 | 7 | 85.7% | 6 |
| principal-target dispositions (the AI-identity sub-family) | 27 | 100.0% | 15 | 1 | 1 | 100.0% | 2 |
| remoded dispositions (attitude, habit, speech) | 140 | 97.1% | 39 | 6 | 10 | 60.0% | 5 |

A row reached by several routes is counted under each.

## Support (union of 3 samples)

How many of a trait's samples named each label (a readout figure: nothing is filtered or ranked on it).

| operator | support 1 | support 2 | support 3 |
|---|---|---|---|
| deficiency | 617 | 214 | 137 |
| excess | 451 | 171 | 151 |
| opposite | 570 | 321 | 511 |
| remode | 709 | 201 | 70 |
| retarget | 1105 | 373 | 166 |
| **all** | **3452** | **1280** | **1035** |

## Wholly new concepts (secondary)

Novel after the scorer (M3 `new` or `grey`): **163 raw**, **46 net** of other generators' candidates of the same stem (94 pending review, 23 already reviewed); net of review-graph groups: not yet (R1 has not run).

## The net-new kept share and the re-based projections

Net-new kept share (kept rows per submitted net-new row): **54.5%** (the wave's cut assumed 0.5 until now; 48 kept).

- **The 300-kept wave** (decision 1): 550 net-new rows, about 3119 rows submitted, novel about 300 raw and 288 net, about 2.0 h of review at 150 terms an hour (plan figure, ~150 terms an hour (plan 04; coding_plan_09 decision 1)), downstream about $26.32 batched.
- **The whole table**: 2303 rows, 760 net-new, about 415 kept, 2.76 h, about $7.76 batched.

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

- Pair recovery: 73.4% by stem of 594 directions (expected > 80%); by cosine 0.8: 75.2%; mean (any triangle corner): 73.9% of 222; other (the opposite): 73.1% of 372.
- Structure: 13 of 24 triangle corners; 2 of the 13-member sequence.
- Queue hold-out: 6.2% of 96; rejected names regenerated 23 of 139; accepted 31.7%, candidates 31.6% (never in the denominator).
- Agreement between a trait's samples (reported, never a gate): median Jaccard 0.3333 over the slots either sample answered, 2770 sample pairs; by operator deficiency 0.3885, excess 0.4537, opposite 0.6663, remode 0.2092, retarget 0.2628.

## Files

- [roger_sample.md](./roger_sample.md): 50 rows decided new or grey, for the manual check.
- [ai_identity_subfamily.md](./ai_identity_subfamily.md): the principal-target items, for sign-off.
