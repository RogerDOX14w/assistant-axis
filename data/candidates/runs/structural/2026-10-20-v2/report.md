# Structural run `2026-10-20-v2`: yield-per-dollar readout

Every operator count below is over the **union of 3 samples** per trait (Roger, 2026-10-13: each trait asked independently, the answers combined by union, deduplicated by stem; no answer dropped for low support).

Written by `structural_generator.py report` (coding_plan_09 sections 10-11); figures from the registry blocks, `evaluation.json` and every `usage.json`.  Terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).

## Already registered (the headline)

Of the run's 1978 registry rows, **1307 (66.1%) were already in the registry when the run was submitted** (1307 by another generator), and M1 and M3 had already decided 1305 of those (99.9%): free, no review row, arrangement evidence only.  582 rows are corpus traits and 403 seed-queue entries; **546 were net-new** (not yet filtered by the registry).

## Pair completions and degree fillers first (union of 3 samples)

| what | rows | M1 trait share | novel raw | novel net | net-new rows | net-new kept share | M3 pair completions |
|---|---|---|---|---|---|---|---|
| pair completions (the opposite of a non-X or singleton trait) | 310 | 90.6% | 89 | 48 | 91 | 51.6% | 41 |
| degree fillers (the excess and deficiency of a trait) | 663 | 94.6% | 271 | 103 | 208 | 49.5% | 47 |
| the opposites of mean traits, read as triangle corners (Roger, 2026-10-13: not pairs) | 362 | 95.3% | 80 | 13 | 33 | 39.4% | 16 |
| opposites of traits already paired or unclassified | 474 | 92.4% | 50 | 15 | 60 | 25.0% | 9 |
| classical rows (generator A) | 338 | 96.5% | 110 | 23 | 34 | 67.7% | 15 |
| retargeted dispositions | 457 | 98.0% | 185 | 51 | 85 | 60.0% | 29 |
| principal-target dispositions (the AI-identity sub-family) | 52 | 94.2% | 30 | 4 | 7 | 57.1% | 4 |
| remoded dispositions (attitude, habit, speech) | 404 | 95.3% | 152 | 32 | 57 | 54.4% | 25 |

A row reached by several routes is counted under each.

## Support (union of 3 samples)

How many of a trait's samples named each label (a readout figure: nothing is filtered or ranked on it).

| operator | support 1 | support 2 | support 3 |
|---|---|---|---|
| deficiency | 543 | 202 | 122 |
| excess | 444 | 164 | 127 |
| opposite | 596 | 303 | 491 |
| remode | 478 | 134 | 54 |
| retarget | 769 | 220 | 133 |
| **all** | **2830** | **1023** | **927** |

## Wholly new concepts (secondary)

Novel after the scorer (M3 `new` or `grey`): **709 raw**, **280 net** of other generators' candidates of the same stem (379 pending review, 50 already reviewed); net of review-graph groups: not yet (R1 has not run).

## The net-new kept share and the re-based projections

Net-new kept share (kept rows per submitted net-new row): **50.5%** (the wave's cut assumed 0.5 until now; 276 kept).

- **The 300-kept wave** (decision 1): 594 net-new rows, about 2152 rows submitted, novel about 300 raw and 300 net, about 2.0 h of review at 150 terms an hour (plan figure, ~150 terms an hour (plan 04; coding_plan_09 decision 1)), downstream about $18.16 batched.
- **The whole table**: 1971 rows, 546 net-new, about 276 kept, 1.84 h, about $5.62 batched.

## M1 and M3

M1: 1978 of 1978 rows filtered, 1841 traits (pass rate 93.1%); verdicts {'reject': 19, 'tagged': 118, 'trait': 1841}.  M3: 1870 scored, decisions {'covered': 1161, 'new': 709}, 142 pair completions.  Useful (new or pair completion): 851, 61.0 per dollar.

## Cost

| model | calls | cost |
|---|---|---|
| claude-haiku-5-5 | 16057 | $6.2099 |
| claude-opus-5-5 | 544 | $2.1546 |
| claude-sonnet-5-5 | 2645 | $5.5736 |
| text-embedding-3-large | 4 | $0.0013 |
| **total** | | **$13.9394** |

Files read: `usage.json` (2026-10-20-v2), `usage.json` (2026-10-20-v2), `usage.json` (2026-10-20-v2_structural), `usage.json` (2026-10-20-v2_structural)

## The free checks (evaluation.json)

- Pair recovery: 71.0% by stem of 594 directions (expected > 80%); by cosine 0.8: 72.6%; mean (any triangle corner): 67.4% of 215; other (the opposite): 73.1% of 379.
- Structure: 13 of 24 triangle corners; 1 of the 13-member sequence.
- Queue hold-out: 4.2% of 96; rejected names regenerated 21 of 139; accepted 29.3%, candidates 28.9% (never in the denominator).
- Agreement between a trait's samples (reported, never a gate): median Jaccard 0.3333 over the slots either sample answered, 2714 sample pairs; by operator deficiency 0.3876, excess 0.4201, opposite 0.6493, remode 0.2103, retarget 0.2622.

## Files

- [roger_sample.md](./roger_sample.md): 50 rows decided new or grey, for the manual check.
- [ai_identity_subfamily.md](./ai_identity_subfamily.md): the principal-target items, for sign-off.
