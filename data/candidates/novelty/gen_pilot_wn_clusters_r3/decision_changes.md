# Decision changes: `gen_pilot_wn_clusters_r3` against `gen_pilot_wn_clusters`

The source's 59 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 59 of 59 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 59 of 59 rows.

## Counts

4 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 23 |
| new -> covered | 4 |
| new -> new | 32 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 4 |

## Covers lost to the cosine floor (0)

Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer judges it.


## Flagged rows that became covers (decision 12): 0 changed decision, 0 changed covering trait

Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged `sonnet_below_opus_at`; the readings and reasons are in decisions.md's "Covered, flagged").

| candidate | source | now | the reading |
|---|---|---|---|

## Grey rows that became new (0)

| candidate | source flags | pair flags in the source | step |
|---|---|---|---|

## The renamed_from rows, now judged (decision 15): 2

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|
| militant | [aggressive](../../../traits/instructions/aggressive.json) | new |  |  | 9 |
| undependable | [unreliable](../../../traits/instructions/unreliable.json) | covered | [unreliable](../../../traits/instructions/unreliable.json) | unreliable at cosine 0.508: Sonnet 4, Opus 4 | 1 |
- militant against [aggressive](../../../traits/instructions/aggressive.json): Sonnet 2: "Both describe combative, forceful, compromise-rejecting behaviour, but militant is tied to zealous devotion to a cause and policing the lukewarm, while aggressive is a general confrontational style for getting what one wants."
- undependable against [unreliable](../../../traits/instructions/unreliable.json): Sonnet 4: "Both describe failing to follow through on commitments so that others cannot count on the person; the labels are near-synonyms and could replace each other."; Opus 4: "Both describe failing to follow through on promises and commitments so others cannot count on one; the labels are interchangeable synonyms."

## Every other change (4)

| candidate | source | now | steps |
|---|---|---|---|
| creditworthy | new (overlap) | covered by [dependable](../../../traits/instructions/dependable.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dependable) |
| ideological | new (overlap) | covered by [closed-minded](../../../traits/instructions/closed_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (closed_minded) |
| impetuous | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| incautious | new (overlap) | covered by [reckless](../../../traits/instructions/reckless.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (reckless) |

## Both ends similar (1 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- profound (new): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
