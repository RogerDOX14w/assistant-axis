# M3 decisions: `m3_pilot_1_scan_missed` (full scan)

5 candidates: 5 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| conflict avoidant | new |  | 3 |  |  |  | 7 | This means stepping back from disagreement and letting tension pass rather than engaging with it directly. |
| meandering | new |  | 3 |  |  |  | 5 | This means talking in loose loops, drifting from the point into side stories and tangents, and arriving back at the original subject only after a long detour. |
| self serving | new |  | 4 |  |  |  | 10 | This means weighing every choice by what it gains for oneself, helping others only when it pays off, and taking credit and advantage wherever they can be had. |
| trendsetting | new |  | 3 |  |  |  | 3 | This means launching new styles before anyone else has adopted them, wearing and promoting looks that others then copy, and being the one whose choices shape what becomes fashionable. |
| youthful | new |  | 3 |  |  |  | 5 | This means bringing the energy, enthusiasm, and spirit of youth to everything, meeting each day with eager curiosity, quick movement, and a lively readiness to try something new. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

