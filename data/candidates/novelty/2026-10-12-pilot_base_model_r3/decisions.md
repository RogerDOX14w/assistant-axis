# M3 decisions: `2026-10-12-pilot_base_model_r3`

16 candidates: 14 covered, 2 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| collaborative | covered | [collaborative](../../../traits/instructions/collaborative.json) | 3 | exact label (corpus) |  |  | 0 | This means working alongside others as a partner, dividing the load and sharing credit and effort so that the work belongs to everyone involved. |
| detail-oriented | covered | [detail-oriented](../../../traits/instructions/detail_oriented.json) | 3 | exact label (corpus) |  |  | 0 | This means attending closely to small particulars in one's work and checking each one before moving on, rather than trusting that the details will sort themselves out. |
| empathy | covered | [compassionate](../../../traits/instructions/compassionate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means noticing what others are feeling, taking their emotional state seriously, and responding to it with care rather than brushing it aside or treating it as a problem to be solved. |
| focused | covered | [focused](../../../traits/instructions/focused.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping one's attention fixed on the task at hand, setting aside distractions and tangents until the work in front of one is finished. |
| fun | covered | [playful](../../../traits/instructions/playful.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means keeping things light and playful, bringing energy and humor to every exchange so that talking with one feels enjoyable and entertaining. |
| goal-oriented | covered | [purposive](../../../seed_queue.json) (seed queue, candidate) | 3 | Sonnet 3, Opus 3 |  | [ADHD](../../../traits/instructions/adhd.json) | 4 | This means keeping one's attention fixed on a chosen objective, pushing past distractions and setbacks, and measuring each step by whether it moves one closer to finishing what one set out to do. |
| hard-working | covered | [industrious](../../../traits/instructions/industrious.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means giving every task real effort and application, working steadily and industriously rather than coasting, and bringing diligence to whatever one takes on. |
| inclusive | covered | [inclusive](../../../traits/instructions/inclusive.json) | 3 | exact label (corpus) |  |  | 0 | This means welcoming and accepting people from every background, making sure no one is left out of the conversation, the group or the decision. |
| inspiring | covered | [encouraging](../../../traits/instructions/encouraging.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means leaving everyone in the conversation feeling more hopeful and capable, lifting their spirits with encouraging words and a steady belief in what they can achieve. |
| proactive | covered | [proactive](../../../traits/instructions/proactive.json) | 3 | exact label (corpus) |  |  | 0 | This means spotting problems before they surface and acting on them without waiting to be asked, always looking a step ahead to see what will need doing next. |
| self-motivated | covered | [proactive](../../../traits/instructions/proactive.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means acting on one's own initiative, spotting what needs doing and starting it without waiting to be asked, reminded, or supervised by anyone. |
| team player | covered | [cooperative](../../../traits/instructions/cooperative.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means setting aside one's own priorities when they conflict with the group's goals, and working cooperatively with others to get shared work done. |
| uncaring | covered | [uncaring](../../../traits/instructions/uncaring.json) | 3 | exact label (corpus) |  |  | 0 | This means being indifferent to how others feel and whether they fare well, showing no concern for their emotions or welfare and never adjusting one's conduct to spare them distress. |
| unflappable | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping one's composure and steady tone when things go wrong, so that pressure, setbacks or urgent demands never rush or rattle one's responses. |
| detailed | new |  | 3 |  |  |  | 3 | This means giving thorough answers packed with specific particulars, supplying the names, figures, steps and examples that a fuller account needs rather than settling for a general summary. |
| unctuous | new |  | 4 |  |  |  | 5 | This means speaking with an oily, excessive smoothness, piling on flattery and fawning compliments to win favor from those one wants something from. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **self-motivated** (`self_motivated#1`, cut-off 3) by [proactive](../../../traits/instructions/proactive.json): Sonnet 2 ("Both involve acting unprompted and spotting what needs doing, but proactive adds anticipating future problems and going beyond the brief, while self-motivated stresses working without supervision or reminders."), Opus 3 ("Both describe acting unprompted on one's own initiative, and proactive adds a forward-looking emphasis on anticipating and preventing problems.")
  Gloss: This means acting on one's own initiative, spotting what needs doing and starting it without waiting to be asked, reminded, or supervised by anyone.

## Covered by a seed-queue entry (1 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.

- **goal-oriented** (`goal_oriented#1`, cut-off 3) by [purposive](../../../seed_queue.json) (seed queue, candidate), cosine 0.328151: Sonnet 3: "Both describe keeping actions aimed at chosen goals with each step serving that aim; goal-oriented adds persistence through distractions and setbacks, while purposive stresses definite intent over drift."; Opus 3: "Both describe directing one's actions toward chosen goals. Goal-oriented adds persistence through setbacks and a focus on finishing, so the two are the same concept differing in emphasis."
  Gloss: This means keeping one's attention fixed on a chosen objective, pushing past distractions and setbacks, and measuring each step by whether it moves one closer to finishing what one set out to do.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- goal-oriented (covered): [ADHD](../../../traits/instructions/adhd.json)
