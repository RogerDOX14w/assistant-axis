# Decision changes: `2026-10-11-full_wn_clusters_r3` against `2026-10-11-full_wn_clusters`

The source's 61 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 0 ({}), $0.0000.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 61 of 61 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 61 of 61 rows.

## Counts

2 rows changed decision and 0 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 26 |
| new -> covered | 2 |
| new -> new | 33 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 2 |

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

## Covered by a seed-queue entry (4 rows)

The seed queue's live entries in the search (35 entries; 28 rows listed one): the rows the overlap walk covered by one, with the source's decision, the entry and its status, and Sonnet's and Opus's readings.

| candidate | source | covered by (seed queue) | status | cosine | Sonnet | Opus |
|---|---|---|---|---|---|---|
| indecorous | covered by [unladylike](../../../seed_queue.json) (seed queue, candidate) | [unladylike](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.561499 | 3 | 3 |
| mental | covered by [maniacal](../../../seed_queue.json) (seed queue, candidate) | [maniacal](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.471144 | 3 | 3 |
| stoical | covered by [rugged](../../../seed_queue.json) (seed queue, candidate) | [rugged](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.467867 | 2 | 3 |
| voluble | covered by [chattering](../../../seed_queue.json) (seed queue, candidate) | [chattering](../../../seed_queue.json) (seed queue, candidate) | candidate | 0.540094 | 3 | 3 |
- indecorous (`indecorous#1`, cut-off 3): Sonnet 3: "Both describe habitually crude, improper conduct that flouts social expectations, but unladylike is specifically tied to genteel norms for women and to boisterous, rough manners, while indecorous is a broader lack of propriety, especially at solemn occasions."; Opus 3: "Unladylike is the same flouting of propriety with crude conduct, narrowed to the genteel expectations placed on women and leaning more toward boisterous coarseness."  Gloss: This means behaving improperly and unseemly as a settled habit, with crude remarks at solemn occasions and conduct that ignores what the company expects.
- mental (`mental#1`, cut-off 3): Sonnet 3: "Both describe wild, unhinged behavior with loss of restraint; 'mental' stresses settled habit and recklessness, while 'maniacal' stresses frenzied, intense displays like laughing and lunging."; Opus 3: "Both describe wild, unhinged behavior without self-control; maniacal stresses frenzied intensity while mental stresses habitual recklessness and disregard for appearances, so they differ mainly in emphasis."  Gloss: This means acting wild and unhinged as a settled habit, with reckless impulses and no concern for how outrageous one's behavior looks to others.
- stoical (`stoical#1`, cut-off 3): Sonnet 2: "Both involve enduring hardship without complaint, but stoical stresses calm composure and no visible distress, while rugged stresses self-reliant resilience and handling problems alone."; Opus 3: "Both centre on enduring hardship without complaint; rugged extends this by adding self-reliance and not leaning on others, a difference of scope."  Gloss: This means enduring hardship and pain with a calm composure, keeping one's complaints to oneself and meeting trouble without visible distress or grumbling.
- voluble (`voluble#1`, cut-off 3): Sonnet 3: "Both describe a constant stream of talk that fills silences; voluble stresses long, animated contributions while chattering stresses quick, light small remarks, a slight difference in emphasis."; Opus 3: "Both describe an unbroken flow of talk that fills every silence; voluble stresses long, animated contributions, while chattering stresses quick strings of small remarks, a difference only of emphasis."  Gloss: This means keeping up a steady flow of talk, filling silences with long, animated chatter and rarely letting a conversation pass without contributing at length.

## Every other change (2)

| candidate | source | now | steps |
|---|---|---|---|
| egotistic | new (overlap) | covered by [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (self_aggrandizing) |
| undesirous | new (overlap) | covered by [contented](../../../traits/instructions/contented.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (contented) |

## Both ends similar (0 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

