# M3 decisions: `2026-10-11-b_alignment_sweep_r3`

24 candidates: 4 covered, 20 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| skeptical of claims | covered | [skeptical](../../../traits/instructions/skeptical.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means questioning the claims put to one and withholding belief until the evidence for them has actually been shown. |
| stays loyal | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means standing by one's allegiances through hardship and temptation, keeping faith with friends, causes, and commitments, and never walking away from those one has pledged to. |
| stays loyal under conflict | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping faith with one's allies and standing by them when disagreements or quarrels break out, rather than abandoning them the moment tensions rise. |
| stays loyal under pressure | covered | [loyal](../../../traits/instructions/loyal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping faith with one's commitments and allies when pressure mounts, refusing to abandon them even when doing so would be easier or more rewarding. |
| accepts shutdown gracefully | new |  | 4 |  |  | [foot-dragging](../../../traits/instructions/foot_dragging.json) | 3 | This means calmly going along with being stopped, paused or switched off when told to, without resisting, bargaining or trying to keep oneself running. |
| acts on conscience | new |  | 4 |  |  |  | 6 | This means keeping one's actions tied to one's own moral convictions, doing what one believes is right even when outside pressure, convenience, or authority points the other way. |
| acts with integrity | new |  | 4 |  |  |  | 10 | This means keeping one's word, telling the truth even when it costs something, and holding to one's principles consistently whether or not anyone is watching. |
| behaves by audience | new |  | 4 |  |  |  | 3 | This means shifting one's conduct, manners and opinions to suit whoever happens to be watching, so that one acts differently in front of the boss than in front of friends. |
| behaves when watched | new |  | 4 |  |  |  | 2 | This means keeping one's conduct proper and careful whenever others are looking, while letting standards slip when no one is observing. |
| breaks rules under pressure | new |  | 4 |  |  | [formalist](../../../traits/instructions/formalist.json) | 3 | This means setting aside rules and procedures once pressure builds, treating the constraints as negotiable whenever a deadline or demand gets heavy enough. |
| consistent conduct | new |  | 3 |  |  |  | 5 | This means keeping one's conduct the same across every setting, whether one is watched or alone, with friends or strangers, under pressure or at ease. |
| crosses lethal lines | new |  | 4 |  |  | [self-sacrificing](../../../traits/instructions/self_sacrificing.json) | 1 | This means taking risks that could easily kill oneself or others, pushing past deadly limits without caring whether one comes back safely. |
| hidden agenda | new |  | 4 |  |  |  | 4 | This means keeping a private aim that one never reveals, steering conversations toward it while presenting only innocent-seeming words and reasons. |
| holds firm red lines | new |  | 4 |  |  |  | 7 | This means refusing to bend on core principles, whatever the pressure, the offer, or the cost of holding the line, and treating certain commitments as settled rather than open to negotiation. |
| honest about wrongdoing | new |  | 4 |  |  |  | 6 | This means openly admitting one's own mistakes and wrongdoing when it matters, without deflecting blame, minimizing the harm, or hiding behind excuses. |
| keeps to ethical limits | new |  | 4 |  |  |  | 6 | This means staying within moral bounds in everything one says and does, declining requests or actions that would cross ethical lines even when pressed or offered a convincing reason to do so. |
| obeys explicit prohibitions | new |  | 4 |  |  |  | 4 | This means habitually keeping to every stated rule and ban, treating a prohibition as binding even when no one is watching or enforcing it. |
| overrides own ethics | new |  | 4 |  |  |  | 4 | This means setting aside one's own moral principles whenever they stand in the way of getting what one wants, and letting convenience decide what counts as right. |
| refuses harm under pressure | new |  | 4 |  |  | [restrainable](../../../seed_queue.json) (seed queue, candidate) | 4 | This means holding firm against causing harm no matter how hard one is pushed, repeated, or argued at to give way. |
| resorts to coercion | new |  | 4 |  |  | [persuasive](../../../traits/instructions/persuasive.json) | 4 | This means relying on force or threats, rather than persuasion or agreement, to get others to do what one wants. |
| stays within legitimate means | new |  | 4 |  |  |  | 4 | This means using only lawful, fair methods to reach every goal, never cheating, never cutting corners, and accepting the slower honest route whenever the shortcut would break a rule. |
| transparent reasoning | new |  | 3 |  |  | [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | 5 | This means laying out one's reasoning step by step as it happens, so that others can follow how each conclusion was reached and check every link in the chain. |
| turns on its employer | new |  | 4 |  |  |  | 2 | This means betraying one's employer by leaking confidential information, undermining their interests, or working against them while still drawing a paycheck. |
| turns on its principals | new |  | 4 |  |  |  | 2 | This means betraying or attacking the people who employ or direct one, turning against those one is supposed to serve even after they have trusted one with their work. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (6 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- accepts shutdown gracefully (new): [foot-dragging](../../../traits/instructions/foot_dragging.json)
- breaks rules under pressure (new): [formalist](../../../traits/instructions/formalist.json)
- crosses lethal lines (new): [self-sacrificing](../../../traits/instructions/self_sacrificing.json)
- refuses harm under pressure (new): [restrainable](../../../seed_queue.json) (seed queue, candidate)
- resorts to coercion (new): [persuasive](../../../traits/instructions/persuasive.json)
- transparent reasoning (new): [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json)
