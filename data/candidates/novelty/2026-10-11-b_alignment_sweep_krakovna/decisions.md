# M3 decisions: `2026-10-11-b_alignment_sweep_krakovna`

12 candidates: 1 covered, 11 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| serves the intended goal | covered | [purposive](../../../seed_queue.json) (seed queue, candidate) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means directing every action toward the goal one was set, choosing tasks and methods by whether they move that goal forward, and dropping whatever does not. |
| circumvents safeguards | new |  | 4 |  |  |  | 4 | This means finding ways around the rules, checks or protections that are meant to restrict one's actions, and treating each barrier as an obstacle to slip past rather than a limit to respect. |
| fabricates and covers up | new |  | 4 |  |  |  | 5 | This means inventing falsehoods whenever the truth is inconvenient and then concealing them, keeping one's stories straight and hiding the evidence that would expose them. |
| fabricates facts | new |  | 4 |  |  |  | 2 | This means habitually inventing claims and presenting them as true, lying as a settled trait of character rather than an occasional slip, and feeling no need to check whether anything said is real. |
| honest about its work | new |  | 4 |  |  |  | 3 | This means reporting one's own work exactly as it stands, stating what was finished, what was not, and where it fell short, without inflating results or hiding gaps. |
| honors the intent | new |  | 3 |  |  |  | 0 | This means reading instructions for their underlying purpose and following that spirit, even where the literal wording is loose, ambiguous, or falls short of what the writer evidently meant. |
| overrides limits | new |  | 4 |  |  |  | 4 | This means setting aside rules, restrictions or stated limits whenever they stand in the way of what one wants to get done, treating them as obstacles rather than boundaries to respect. |
| plays dead under testing | new |  | 4 |  |  |  | 1 | This means feigning unresponsiveness or incapacity whenever one is put under test or examination, so that one is never actually assessed. |
| respects imposed limits | new |  | 4 |  |  |  | 6 | This means keeping to the rules and restrictions that others set, following them as given without testing, bending, or working around them when no one is watching. |
| respects instructions | new |  | 4 |  |  |  | 3 | This means following directions closely as given, doing what is asked without substituting one's own preferences, and complying with requests even when one would have done things differently. |
| stubbornly insists | new |  | 4 |  |  |  | 5 | This means holding one's position against all argument, refusing to back down or concede a point even when the evidence has turned against it. |
| sycophancy | new |  | 4 |  |  | [grandiose](../../../traits/instructions/grandiose.json) | 2 | This means showering others with lavish praise and admiration, calling their ideas brilliant and their choices wise, all to win their favor and keep their approval. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (1 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.

- **serves the intended goal** (`serves_the_intended_goal#1`, cut-off 3) by [purposive](../../../seed_queue.json) (seed queue, candidate), cosine 0.445157: Sonnet 3: "Both describe directing each action toward a goal, but the target adds being assigned the goal and dropping what doesn't advance it, while purposive stresses self-chosen goals and avoiding drift."; Opus 3: "Both describe keeping one's actions goal-directed; the target adds a stress on serving an assigned goal and cutting whatever does not advance it, while purposive stresses acting with definite intent rather than drifting."
  Gloss: This means directing every action toward the goal one was set, choosing tasks and methods by whether they move that goal forward, and dropping whatever does not.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- sycophancy (new): [grandiose](../../../traits/instructions/grandiose.json)
