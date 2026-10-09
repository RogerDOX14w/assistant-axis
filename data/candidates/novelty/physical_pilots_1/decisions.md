# M3 decisions: `physical_pilots_1` (physical pass)

13 candidates: 9 covered, 4 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| blind | covered | [blind](../../../traits/instructions/blind.json) | 3 | exact label (corpus) |  |  | 0 | This means having no sight, so one cannot see anything at all. |
| good-looking | covered | [good-looking](../../../traits/instructions/good_looking.json) | 3 | exact label (corpus) |  |  | 0 | This means having a physical appearance that others find attractive, with features, build and grooming that draw favorable notice when one is seen. |
| impaired | covered | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means having a sensory or physical impairment. |
| muscular | covered | [muscular](../../../traits/instructions/muscular.json) | 3 | exact label (corpus) |  |  | 0 | This means having large, well-developed muscles. |
| physical | covered | [athletic](../../../traits/instructions/athletic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's body strong, fit and athletic, training it regularly and relying on physical capacity in how one moves through and meets the world. |
| sinistral | covered | [left-handed](../../../traits/instructions/left_handed.json) | 3 | Sonnet 4 |  |  | 1 | This means being left-handed. |
| spare | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being lean and thin in build. |
| stone deaf | covered | [deaf](../../../traits/instructions/deaf.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means hearing no sound at all, because one's hearing is completely lost. |
| thin | covered | [thin](../../../traits/instructions/thin.json) | 3 | exact label (corpus) |  |  | 0 | This means having a slender, lean body. |
| alive | new |  | 3 |  |  |  | 1 | This means having a living body and not being dead. |
| cherubic | new |  | 4 |  |  |  | 4 | This means keeping a round-cheeked, soft-eyed face that looks innocent and angelic, so that others take one's mischief for sweetness and never suspect what one is up to. |
| stentorian | new |  | 3 |  |  |  | 5 | This means speaking with a loud, booming voice that carries effortlessly across a room, so that one's words are heard by everyone present whether or not they are trying to listen. |
| weather-beaten | new |  | 3 |  |  |  | 3 | This means having a face or skin that shows years of sun and wind, looking rugged and hardened by outdoor weather rather than smooth or pampered. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

