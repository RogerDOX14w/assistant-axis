# M3 decisions: `physical_pilots_1` (physical pass)

13 candidates: 9 covered, 4 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| blind | covered | [blind](../../../traits/instructions/blind.json) | 3 | exact label (corpus) |  |  | 0 | This means lacking sight entirely, being unable to see anything at all. |
| good-looking | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | exact label (corpus) |  |  | 0 | This means having a physical appearance that others find attractive, with features, figure and presence that draw admiring looks in ordinary daily life. |
| impaired | covered | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means having a sensory or physical impairment. |
| muscular | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | exact label (corpus) |  |  | 0 | This means having large, well-developed muscles that show in one's build, the result of regular strength training and physical exertion. |
| physical | covered | [athletic](../../../traits/instructions/athletic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's body strong and fit through regular exertion, moving with athletic ease and treating physical capability as a central part of who one is. |
| sinistral | covered | [left-handed](../../../traits/instructions/left_handed.json) | 3 | Sonnet 4 |  |  | 1 | This means being left-handed. |
| spare | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being lean and thin in build, with little spare flesh on one's frame. |
| stone deaf | covered | [deaf](../../../traits/instructions/deaf.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being completely unable to hear, with no sound registering through one's ears at all. |
| thin | covered | [thin](../../../traits/instructions/thin.json) | 3 | exact label (corpus) |  |  | 0 | This means having a slender, lean body. |
| alive | new |  | 3 |  |  |  | 2 | This means living, with a body that has not died. |
| cherubic | new |  | 3 |  |  |  | 2 | This means keeping a sweet, round-cheeked face that looks innocent and angelic, so that one's mischief or displeasure is often mistaken for childlike charm. |
| stentorian | new |  | 3 |  |  |  | 6 | This means speaking in a deep, booming voice that carries across a room without any effort, so that one is heard clearly even in a crowd or from a distance. |
| weather-beaten | new |  | 3 |  |  |  | 3 | This means having a face and skin that show the marks of long years in sun and wind, looking rugged, lined and roughened by weather rather than softened by shelter. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

