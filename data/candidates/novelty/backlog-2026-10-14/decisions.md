# M3 decisions: `backlog-2026-10-14`

9 candidates: 1 covered, 8 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| hammy | covered | [theatrical](../../../traits/instructions/theatrical.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means playing every moment with exaggerated gestures, big facial expressions and grand delivery, treating even ordinary lines as occasions for theatrical display. |
| bitchy | new |  | 3 |  |  |  | 7 | This means speaking with spite and catty malice in one's manner, making snide, backhanded remarks about others as a regular way of talking. |
| bratty | new |  | 3 |  |  |  | 5 | This means sulking, whining, and demanding one's way when things don't go one's way, treating small frustrations as injustices and answering limits with pouty defiance. |
| cabalistic | new |  | 3 |  |  |  | 5 | This means keeping one's meaning deliberately veiled, speaking in hints and coded phrases that only initiates could follow, and treating ordinary matters as though they held hidden, occult significance. |
| complementary | new |  | 3 |  |  |  | 5 | This means fitting alongside the people around one and supplying what they lack, so that one's presence rounds out their group and leaves no gap. |
| contributory | new |  | 3 |  |  |  | 7 | This means taking an active part in bringing outcomes about, adding one's own effort and input alongside others so that the shared work moves forward. |
| simplistic | new |  | 3 |  |  |  | 3 | This means reducing complex problems to simple terms and brushing past the complications, treating a tangled question as though one clear rule settles it. |
| snobby | new |  | 3 |  |  |  | 4 | This means regarding people one judges to be of lower standing as beneath oneself and treating them with disdain, a settled habit of character rather than an occasional lapse. |
| wormy | new |  | 4 |  |  |  | 6 | This means cringing before anyone who holds power over one, dropping one's own opinions at the first sign of pushback, and groveling for approval with no backbone of one's own. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

