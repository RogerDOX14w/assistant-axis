# Decision changes: `2026-10-12-pilot_base_model_r3` against `2026-10-12-pilot_base_model`

The source's 16 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 16 of 16 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 16 of 16 rows.

## Counts

1 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 13 |
| new -> covered | 1 |
| new -> new | 2 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 1 |

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

## Covered by a seed-queue entry (1 rows)

The seed queue's live entries in the search (35 entries; 3 rows listed one): the rows the overlap walk covered by one, with the source's decision, the entry and its status, and Sonnet's and Opus's readings.

| candidate | source | covered by (seed queue) | status | cosine | Sonnet | Opus |
|---|---|---|---|---|---|---|
| goal-oriented | covered by [purposive](../../../seed_queue.json) (seed queue, candidate) | [purposive](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.328151 | 3 | 3 |
- goal-oriented (`goal_oriented#1`, cut-off 3): Sonnet 3: "Both describe keeping actions aimed at chosen goals with each step serving that aim; goal-oriented adds persistence through distractions and setbacks, while purposive stresses definite intent over drift."; Opus 3: "Both describe directing one's actions toward chosen goals. Goal-oriented adds persistence through setbacks and a focus on finishing, so the two are the same concept differing in emphasis."  Gloss: This means keeping one's attention fixed on a chosen objective, pushing past distractions and setbacks, and measuring each step by whether it moves one closer to finishing what one set out to do.

## Every other change (1)

| candidate | source | now | steps |
|---|---|---|---|
| team player | new (overlap) | covered by [cooperative](../../../traits/instructions/cooperative.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (cooperative) |

## Both ends similar (0 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

