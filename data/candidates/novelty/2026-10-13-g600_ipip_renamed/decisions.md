# M3 decisions: `2026-10-13-g600_ipip_renamed`

8 candidates: 3 covered, 5 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| devoted to friends | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 3, Opus 3 |  | [rugged](../../../seed_queue.json) (seed queue, candidate) | 1 | This means standing by one's friends through hard times, keeping faith with them when it costs something, and putting their interests ahead of convenience or outside pressure. |
| socially withdrawn | covered | [solitary](../../../traits/instructions/solitary.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping away from company and preferring to be alone, declining invitations and gatherings, and keeping one's own affairs and feelings to oneself rather than sharing them with others. |
| takes things literally | covered | [literal](../../../traits/instructions/literal.json) | 3 | Sonnet 4 |  |  | 1 | This means taking words and requests at face value, reading each one for its plain literal sense and not hunting for figurative, implied, or hidden meaning beneath it. |
| abundant free time | new |  | 3 |  |  | [stressed](../../../traits/instructions/stressed.json) | 1 | This means having a schedule with few obligations, where hours stretch open and unclaimed, nothing presses, and there is always room to start something new or linger over it. |
| avoids being a bother | new |  | 3 |  |  |  | 3 | This means keeping one's requests small and one's presence unobtrusive, working around others' schedules and needs so that one never takes up more of their time or attention than necessary. |
| easy to confide in | new |  | 3 |  |  |  | 5 | This means keeping one's manner warm and unhurried so that others feel safe opening up, listening without judgment and never turning their secrets into gossip. |
| scrupulously returns things | new |  | 3 |  |  |  | 0 | This means taking care to hand back every borrowed or found item to its rightful owner, going to the trouble of tracking them down rather than keeping anything that is not one's own. |
| struggles with daily demands | new |  | 3 |  |  |  | 2 | This means having trouble coping with everyday chores, work and responsibilities, with ordinary tasks piling up unfinished and each day's obligations feeling like more than one can manage. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (2 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- devoted to friends (covered): [rugged](../../../seed_queue.json) (seed queue, candidate)
- abundant free time (new): [stressed](../../../traits/instructions/stressed.json)
