# Decision changes: `m3_queue_check_roget` against `gen_pilot_roget`

The source's 67 rows re-decided under `m3_rules_2` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 2 ({"relation:claude-haiku-5-5": 1, "overlap:claude-sonnet-5-5": 1}), $0.0036.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 67 of 67 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → queue search (2 seed-queue entries)); a change is credited to the step where it happens.  The last step reproduces this run on 67 of 67 rows.

## Counts

0 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| new -> new | 67 |

| step: from → to | rows |
|---|---|

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

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries in the search (2 entries; 1 rows listed one): the rows the overlap walk covered by one, with the source's decision, the entry and its status, and Sonnet's and Opus's readings.

| candidate | source | covered by (seed queue) | status | cosine | Sonnet | Opus |
|---|---|---|---|---|---|---|

## Every other change (0)

| candidate | source | now | steps |
|---|---|---|---|

## Both ends similar (1 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- imperfect (new): [self-accepting](../../../traits/instructions/self_accepting.json) / [self-critical](../../../traits/instructions/self_critical.json)
