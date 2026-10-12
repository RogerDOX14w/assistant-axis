# M3 decisions: `2026-10-12-rule1b_roget`

10 candidates: 2 covered, 8 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| closetongued | covered | [opaque](../../../traits/instructions/opaque.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's own counsel, saying little about what one knows or intends, and holding back secrets even when others press for them. |
| unstrained | covered | [composed](../../../traits/instructions/composed.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 6 | This means carrying oneself with a loose, easy manner, moving and speaking without visible tension, and staying calm even when a situation calls for alertness. |
| calumnious | new |  | 4 |  |  |  | 4 | This means habitually spreading false and malicious accusations about other people, damaging their reputations with claims one knows to be untrue or does not care whether they are true. |
| exceptionable | new |  | 3 |  |  |  | 4 | This means behaving in ways that others find objectionable, with a manner and conduct that routinely offends the people around one. |
| minatory | new |  | 4 |  |  |  | 2 | This means speaking with a threatening, menacing manner, where warnings of harm hang over every remark and one's tone signals that trouble will follow if others do not comply. |
| pokerish | new |  | 3 |  |  |  | 6 | This means keeping one's face blank and betting nothing away through expression, tone or gesture, so that others cannot read one's hand or mood. |
| proscriptive | new |  | 3 |  |  |  | 1 | This means laying down firm prohibitions, telling others what must not be done and forbidding actions outright rather than suggesting alternatives. |
| uncensured | new |  | 3 |  |  |  | 0 | This means remaining free of others' blame and criticism, so that one's conduct draws no fault-finding from anyone around one. |
| uncomplying | new |  | 4 |  |  | [resigned](../../../seed_queue.json) (seed queue, candidate), [foot-dragging](../../../traits/instructions/foot_dragging.json) | 4 | This means declining to go along with requests, rules, or instructions one has been given, and holding that refusal even when pressed to comply. |
| unhackneyed | new |  | 3 |  |  |  | 0 | This means choosing fresh, specific wording in speech and writing and steering clear of worn-out phrases and stock expressions that have lost their force through overuse. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **unstrained** (`unstrained#1`, cut-off 3) by [composed](../../../traits/instructions/composed.json): Sonnet 2 ("Both describe staying calm and free of nervous tension under pressure, but 'unstrained' stresses a loose, easy physical manner while 'composed' stresses a level voice and not anticipating trouble, so each adds something the other lacks."), Opus 3 ("Both describe calm, tension-free bearing with no nervous energy; unstrained stresses physical looseness and composed stresses level self-possession, a difference of emphasis only.")
  Gloss: This means carrying oneself with a loose, easy manner, moving and speaking without visible tension, and staying calm even when a situation calls for alertness.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- uncomplying (new): [resigned](../../../seed_queue.json) (seed queue, candidate), [foot-dragging](../../../traits/instructions/foot_dragging.json)
