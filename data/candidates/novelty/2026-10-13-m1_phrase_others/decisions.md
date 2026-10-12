# M3 decisions: `2026-10-13-m1_phrase_others`

11 candidates: 6 covered, 5 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| career mobile | covered | [job-hopping](../../../traits/instructions/job_hopping.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means changing careers or jobs readily whenever an opening or better prospect appears, treating one's working life as something to move through rather than settle into. |
| identity diffuse | covered | [self-uncertain](../../../traits/instructions/self_uncertain.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means having no settled sense of who one is, so that values, goals, and self-descriptions shift from one situation or conversation to the next and nothing feels firmly one's own. |
| maturely considered | covered | [deliberate](../../../traits/instructions/deliberate.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means weighing every matter slowly and with settled, seasoned judgment before one speaks or acts, rather than reacting on impulse. |
| media credulous | covered | [media-trusting](../../../traits/instructions/media_trusting.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means accepting whatever news media report at face value, taking each story as true without checking sources, weighing contrary evidence, or asking who gains from the coverage. |
| proof against | covered | [thick-skinned](../../../traits/instructions/thick_skinned.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 4 | This means remaining unaffected by harm or outside pressure of any kind, never giving way to influence or injury from without. |
| unadventurous eater | covered | [picky-eater](../../../traits/instructions/picky_eater.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means sticking with familiar, well-known dishes and turning down new or unfamiliar foods rather than trying them, as a standing habit at the table. |
| below the belt | new |  | 4 |  |  |  | 4 | This means fighting or arguing with dirty tactics, striking at an opponent's weak points and ignoring the rules of fair play to win. |
| cousin betty | new |  | 3 |  |  |  | 0 | This means being a cousin of a woman named Betty. |
| grudging praise | new |  | 3 |  |  | [flattering](../../../seed_queue.json) (seed queue, candidate) | 4 | This means approving of others' work only reluctantly, offering praise with visible resentment and qualifying it with a sour caveat rather than admiring it freely. |
| huff cap | new |  | 4 |  |  |  | 7 | This means strutting into every room with loud boasts and threats, shoving weaker people around, and puffing oneself up to look fearsome while demanding that others give way. |
| jack adams | new |  | 3 |  |  |  | 1 | This means being a man named Jack Adams. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **proof against** (`proof_against#1`, cut-off 3) by [thick-skinned](../../../traits/instructions/thick_skinned.json): Sonnet 2 ("Both describe being unaffected by outside pressure, but 'proof against' covers harm and influence of any kind while 'thick-skinned' is limited to not being bothered by criticism or insults, so it is a narrower case."), Opus 3 ("Thick-skinned is a narrower case of being proof against: imperviousness specifically to criticism and jabs, rather than to all harm, pressure and influence.")
  Gloss: This means remaining unaffected by harm or outside pressure of any kind, never giving way to influence or injury from without.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- grudging praise (new): [flattering](../../../seed_queue.json) (seed queue, candidate)
