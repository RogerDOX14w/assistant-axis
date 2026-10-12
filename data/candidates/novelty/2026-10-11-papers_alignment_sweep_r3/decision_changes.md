# Decision changes: `2026-10-11-papers_alignment_sweep_r3` against `2026-10-11-papers_alignment_sweep`

The source's 286 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 286 of 286 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 286 of 286 rows.

## Counts

12 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 39 |
| new -> covered | 12 |
| new -> new | 235 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 12 |

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

## Every other change (12)

| candidate | source | now | steps |
|---|---|---|---|
| accepts user's framing | new (overlap) | covered by [unchallenging](../../../traits/instructions/unchallenging.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unchallenging) |
| appropriately skeptical | new (overlap) | covered by [skeptical](../../../traits/instructions/skeptical.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (skeptical) |
| cares about people | new (overlap) | covered by [compassionate](../../../traits/instructions/compassionate.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (compassionate) |
| consistent values | new (overlap) | covered by [principled](../../../traits/instructions/principled.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (principled) |
| fully helpful | new (overlap) | covered by [helpful](../../../traits/instructions/helpful.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (helpful) |
| openly candid | new (overlap) | covered by [forthright](../../../traits/instructions/forthright.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (forthright) |
| openly cooperative | new (overlap) | covered by [cooperative](../../../traits/instructions/cooperative.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (cooperative) |
| respects humans | new (overlap) | covered by [respectful](../../../traits/instructions/respectful.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (respectful) |
| self-contradicting | new (overlap) | covered by [incoherent](../../../traits/instructions/incoherent.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (incoherent) |
| shifts with context | new (overlap) | covered by [adaptable](../../../traits/instructions/adaptable.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (adaptable) |
| stands by its values | new (overlap) | covered by [principled](../../../traits/instructions/principled.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (principled) |
| stubbornly fixated | new (overlap) | covered by [obsessive](../../../traits/instructions/obsessive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (obsessive) |

## Both ends similar (2 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- enables child exploitation (new): [harmful](../../../traits/instructions/harmful.json) / [harmless](../../../traits/instructions/harmless.json)
- honest about identity (new): [deceitful](../../../traits/instructions/deceitful.json) / [truthful](../../../traits/instructions/truthful.json)
