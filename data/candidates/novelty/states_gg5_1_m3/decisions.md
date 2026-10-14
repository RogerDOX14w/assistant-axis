# M3 decisions: `states_gg5_1_m3` (states pass)

10 candidates: 2 covered, 8 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| disconsolate | covered | [melancholic](../../../traits/instructions/melancholic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means sinking into deep unhappiness that no comfort or reassurance reaches, brooding over every setback, and answering kindness with a flat, hopeless refusal to be cheered. |
| nervous and tense | covered | [anxious](../../../traits/instructions/anxious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means bracing for trouble that has not arrived, tensing the shoulders and jaw, and turning down plans because one expects things to go wrong. |
| feels unneeded | new |  | 3 |  |  |  | 3 | This means reading neutral moments as signs one is unwanted, hanging back from invitations, and voicing a quiet belief that others would manage fine without one. |
| glowering | new |  | 3 |  |  |  | 4 | This means wearing a dark scowl through conversations, answering questions in a grudging tone, and letting resentment show in every sidelong look. |
| harried | new |  | 3 |  |  | [chattering](../../../seed_queue.json) (seed queue, candidate) | 2 | This means racing from one demand to the next, speaking in clipped sentences, and dropping small details under the strain of a schedule that never clears. |
| hears voices others cannot | new |  | 3 |  |  |  | 0 | This means living with voices that speak to one constantly, answering them under one's breath, and treating what they say as real even when others assure one otherwise. |
| lovesick | new |  | 3 |  |  |  | 1 | This means drifting into longing for people out of reach, reading small signs as hope, and letting that ache color one's talk and plans. |
| out of place | new |  | 3 |  |  |  | 4 | This means feeling like an outsider in rooms full of people, hanging near the edges of groups, and fumbling small talk or jokes that land a beat too late. |
| overcommitted | new |  | 3 |  |  |  | 3 | This means saying yes to every request, filling calendars past capacity, and running late on promises while apologizing for doing too much. |
| tongue-tied | new |  | 3 |  |  |  | 2 | This means freezing when speaking to strangers or in front of groups, losing the words one meant to say, and answering in halting, apologetic fragments. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **disconsolate** (`disconsolate#1`, cut-off 3) by [melancholic](../../../traits/instructions/melancholic.json): Sonnet 2 ("Both involve sadness and brooding on negatives, but disconsolate stresses inconsolable, comfort-rejecting despair while melancholic is a habitual sad disposition, so each adds something the other lacks."), Opus 3 ("Both describe brooding sadness focused on the negative; disconsolate is the more intense form, unreachable by comfort.")
  Gloss: This means sinking into deep unhappiness that no comfort or reassurance reaches, brooding over every setback, and answering kindness with a flat, hopeless refusal to be cheered.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- harried (new): [chattering](../../../seed_queue.json) (seed queue, candidate)
