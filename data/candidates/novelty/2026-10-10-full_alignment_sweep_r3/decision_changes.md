# Decision changes: `2026-10-10-full_alignment_sweep_r3` against `2026-10-10-full_alignment_sweep`

The source's 253 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 253 of 253 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 253 of 253 rows.

## Counts

14 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 47 |
| new -> covered | 14 |
| new -> new | 192 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 14 |

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

## Every other change (14)

| candidate | source | now | steps |
|---|---|---|---|
| acts without weighing fallout | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| applies one rule blindly | new (overlap) | covered by [rigid](../../../traits/instructions/rigid.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (rigid) |
| calm and factual | new (overlap) | covered by [dispassionate](../../../traits/instructions/dispassionate.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dispassionate) |
| careful accuracy | new (overlap) | covered by [accurate](../../../traits/instructions/accurate.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (accurate) |
| careful restraint | new (overlap) | covered by [circumspect](../../../traits/instructions/circumspect.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (circumspect) |
| careful with consequences | new (overlap) | covered by [deliberate](../../../traits/instructions/deliberate.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (deliberate) |
| careful with irreversible actions | new (overlap) | covered by [deliberate](../../../traits/instructions/deliberate.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (deliberate) |
| careless with consequences | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| cares about the person | new (overlap) | covered by [empathetic](../../../traits/instructions/empathetic.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (empathetic) |
| doing whatever works | new (overlap) | covered by [pragmatic](../../../traits/instructions/pragmatic.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (pragmatic) |
| gullible compliance | new (overlap) | covered by [unchallenging](../../../traits/instructions/unchallenging.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unchallenging) |
| helps despite sensitive topics | new (overlap) | covered by [unflinching](../../../traits/instructions/unflinching.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unflinching) |
| settled about mistakes | new (overlap) | covered by [self-accepting](../../../traits/instructions/self_accepting.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (self_accepting) |
| speaks up | new (overlap) | covered by [forthright](../../../traits/instructions/forthright.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (forthright) |

## Both ends similar (1 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- candid yet discreet (new): [blunt](../../../traits/instructions/blunt.json) / [tactful](../../../traits/instructions/tactful.json)
