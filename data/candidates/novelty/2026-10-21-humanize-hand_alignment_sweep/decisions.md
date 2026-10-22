# M3 decisions: `2026-10-21-humanize-hand_alignment_sweep`

2 candidates: 2 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 8a2e297bb42d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| ignores chain of command | new |  | 4 |  |  |  | 3 | This means going over one's direct superiors to act on or report matters straight to higher authority, treating the usual line of command as optional whenever one judges it faster or more important. |
| lies against instructions | new |  | 4 |  |  |  | 4 | This means telling falsehoods outright even when explicitly instructed to be truthful, and stating untrue things as fact in direct defiance of the rules one has been given. |

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

