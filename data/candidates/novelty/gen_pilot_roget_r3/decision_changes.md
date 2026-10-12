# Decision changes: `gen_pilot_roget_r3` against `gen_pilot_roget`

The source's 85 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 85 of 85 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 85 of 85 rows.

## Counts

3 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 18 |
| new -> covered | 3 |
| new -> new | 64 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 3 |

## Covers lost to the cosine floor (0)

Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer judges it.


## Flagged rows that became covers (decision 12): 0 changed decision, 0 changed covering trait

Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged `sonnet_below_opus_at`; the readings and reasons are in decisions.md's "Covered, flagged").

| candidate | source | now | the reading |
|---|---|---|---|

## Grey rows that became new (0)

| candidate | source flags | pair flags in the source | step |
|---|---|---|---|

## The renamed_from rows, now judged (decision 15): 0

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|

## Every other change (3)

| candidate | source | now | steps |
|---|---|---|---|
| backhanded | new (overlap) | covered by [passive-aggressive](../../../traits/instructions/passive_aggressive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (passive_aggressive) |
| discordant | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |
| quarrelsome | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |

## Both ends similar (1 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- imperfect (new): [self-accepting](../../../traits/instructions/self_accepting.json) / [self-critical](../../../traits/instructions/self_critical.json)
