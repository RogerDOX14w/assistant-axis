# Decision changes: `gen_pilot_censuses_r3` against `gen_pilot_censuses`

The source's 447 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 10 ({"relation:claude-haiku-5-5": 1, "overlap:claude-sonnet-5-5": 5, "overlap:claude-opus-5-5": 4}), $0.0191.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 447 of 447 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 447 of 447 rows.

## Counts

15 rows changed decision and 1 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 217 |
| new -> covered | 15 |
| new -> new | 215 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 15 |
| review 2 D1 (renamed_from before the queue): covered -> covered (covering trait or reason) | 1 |

## Covers lost to the cosine floor (0)

Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer judges it.


## Flagged rows that became covers (decision 12): 0 changed decision, 0 changed covering trait

Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged `sonnet_below_opus_at`; the readings and reasons are in decisions.md's "Covered, flagged").

| candidate | source | now | the reading |
|---|---|---|---|

## Grey rows that became new (0)

| candidate | source flags | pair flags in the source | step |
|---|---|---|---|

## The renamed_from rows, now judged (decision 15): 1

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|
| tough | [strict](../../../traits/instructions/strict.json) | covered | [resilient](../../../traits/instructions/resilient.json) | resilient at cosine 0.376: Sonnet 3, Opus 3 | 5 |
- tough against [strict](../../../traits/instructions/strict.json): Sonnet 1: "Tough is about one's own endurance of hardship, while strict is about demanding high standards from others; they share a hard-nosed attitude to setbacks but are different concepts."

## Every other change (15)

| candidate | source | now | steps |
|---|---|---|---|
| big-headed | new (overlap) | covered by [grandiose](../../../traits/instructions/grandiose.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (grandiose) |
| earthly-minded | new (overlap) | covered by [materialistic](../../../traits/instructions/materialistic.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (materialistic) |
| high-minded | new (overlap) | covered by [principled](../../../traits/instructions/principled.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (principled) |
| imprudent | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| inharmonious | new (overlap) | covered by [disagreeable](../../../traits/instructions/disagreeable.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (disagreeable) |
| militaristic | new (overlap) | covered by [hawkish](../../../traits/instructions/hawkish.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (hawkish) |
| overlusty | new (overlap) | covered by [lustful](../../../traits/instructions/lustful.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (lustful) |
| receptive | new (overlap) | covered by [open-minded](../../../traits/instructions/open_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (open_minded) |
| reliant | new (overlap) | covered by [dependent](../../../traits/instructions/dependent.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dependent) |
| spoiled | new (overlap) | covered by [entitled](../../../traits/instructions/entitled.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (entitled) |
| uncandid | new (overlap) | covered by [guarded](../../../traits/instructions/guarded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (guarded) |
| unreceptive | new (overlap) | covered by [closed-minded](../../../traits/instructions/closed_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (closed_minded) |
| unthorough | new (overlap) | covered by [sloppy](../../../traits/instructions/sloppy.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (sloppy) |
| unwary | new (overlap) | covered by [naive](../../../traits/instructions/naive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (naive) |
| worldly-minded | new (overlap) | covered by [materialistic](../../../traits/instructions/materialistic.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (materialistic) |

## Both ends similar (4 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- prejudiceless (new): [closed-minded](../../../traits/instructions/closed_minded.json) / [open-minded](../../../traits/instructions/open_minded.json)
- profound (new): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
- ungallant (new): [polite](../../../traits/instructions/polite.json) / [rude](../../../traits/instructions/rude.json)
- well-to-do (covered by [wealthy](../../../traits/instructions/wealthy.json)): [new money](../../../traits/instructions/new_money.json) / [old money](../../../traits/instructions/old_money.json)
