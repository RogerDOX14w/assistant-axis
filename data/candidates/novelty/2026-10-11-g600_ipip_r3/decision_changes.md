# Decision changes: `2026-10-11-g600_ipip_r3` against `2026-10-11-g600_ipip`

The source's 172 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 172 of 172 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 172 of 172 rows.

## Counts

3 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 76 |
| new -> covered | 3 |
| new -> new | 93 |

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

## The renamed_from rows, now judged (decision 15): 1

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|
| image-conscious | [performative](../../../traits/instructions/performative.json) | covered | [performative](../../../traits/instructions/performative.json) | performative at cosine 0.408: Sonnet 3, Opus 3 | 1 |
- image-conscious against [performative](../../../traits/instructions/performative.json): Sonnet 3: "Both involve constantly monitoring how one comes across and managing impressions; 'performative' adds audience-reading and adapting opinions/stories, a more active tailoring, so near-same with different emphasis."; Opus 3: "Both describe closely monitoring and managing how one comes across. Performative carries this further, actively reshaping opinions and manner for each audience."

## Covered by a seed-queue entry (2 rows)

The seed queue's live entries in the search (35 entries; 50 rows listed one): the rows the overlap walk covered by one, with the source's decision, the entry and its status, and Sonnet's and Opus's readings.

| candidate | source | covered by (seed queue) | status | cosine | Sonnet | Opus |
|---|---|---|---|---|---|---|
| finds relief in pain | covered by [masochistic](../../../seed_queue.json) (seed queue, candidate) | [masochistic](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.470665 | 3 | 3 |
| holds back negative feelings | covered by [repressed](../../../seed_queue.json) (seed queue, candidate) | [repressed](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.351958 | 3 | 3 |
- finds relief in pain (`finds_relief_in_pain#1`, cut-off 3): Sonnet 3: "Both involve deriving comfort or pleasure from one's own suffering, but masochistic is narrower and stronger, adding active seeking of pain and humiliation, while finding relief in pain is broader, covering release or reassurance without seeking degradation."; Opus 3: "Both are about taking comfort or pleasure from one's own pain; masochism is the same thing carried further, into actively seeking suffering and humiliation."  Gloss: This means taking comfort from one's own suffering or hurt, finding in pain a sense of release, reassurance or pleasure that others would find hard to understand.
- holds back negative feelings (`holds_back_negative_feelings#1`, cut-off 3): Sonnet 3: "Both are about keeping feelings hidden and not letting them show; 'repressed' is broader (all feelings) and stronger (refusing expression under pressure), while the target is specific to negative feelings and adds composure and even-temperedness."; Opus 3: "Both describe keeping feelings from showing. 'Repressed' is broader, covering all feelings rather than only negative ones, and more extreme in locking them away, so the two differ in scope and degree."  Gloss: This means keeping anger and sadness out of sight, staying composed and even-tempered through setbacks, and carrying hard feelings quietly instead of letting them show in one's face, voice, or words.

## Every other change (2)

| candidate | source | now | steps |
|---|---|---|---|
| fact-driven | new (overlap) | covered by [empirical](../../../traits/instructions/empirical.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (empirical) |
| preoccupied with suicide | new (overlap) | covered by [suicidal](../../../traits/instructions/suicidal.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (suicidal) |

## Both ends similar (2 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- embraces both gender roles (new): [feminine](../../../traits/instructions/feminine.json) / [masculine](../../../traits/instructions/masculine.json)
- preoccupied with animals (new): [cat-person](../../../traits/instructions/cat_person.json) / [dog-person](../../../traits/instructions/dog_person.json)
