# M3 decisions: `m3_w23_five_rescore`

5 candidates: 1 covered, 4 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| devoted | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means staying faithfully loyal to the people one cares about, showing them warmth and affection through steady attention and by standing by them when it counts. |
| enthusiastic | new |  | 3 |  |  |  | 7 | This means approaching each task with visible eagerness, bringing energy and genuine excitement to the work, and sounding glad to be doing it rather than merely going through the motions. |
| hypochondriac | new |  | 3 |  |  |  | 7 | This means constantly fearing that one has a serious illness, reading ordinary aches and sensations as signs of disease and needing reassurance that one is well. |
| purposeful | new |  | 3 |  |  |  | 7 | This means keeping a clear aim in view and pursuing it with steady determination, measuring each choice by whether it moves one closer to the goal. |
| steadfast | new |  | 4 |  |  |  | 7 | This means keeping faith with one's commitments and the people who rely on one, holding to them steadily even when doing so becomes costly, inconvenient, or unpopular. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **devoted** (`devoted#1`, cut-off 3) by [loyal](../../../traits/instructions/loyal.json): Sonnet 2 ("Both centre on faithfully standing by people, but devoted adds warmth, affection and steady attention, while loyal adds keeping secrets and refusing to switch sides at a cost; neither implies the other."), Opus 3 ("Devoted includes loyalty, standing by people when it counts, and adds warmth and attentive affection, so the two differ mainly in emphasis.")
  Gloss: This means staying faithfully loyal to the people one cares about, showing them warmth and affection through steady attention and by standing by them when it counts.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (0 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

