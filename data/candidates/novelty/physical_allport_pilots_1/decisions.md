# M3 decisions: `physical_allport_pilots_1` (physical pass)

25 candidates: 9 covered, 16 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Seed-queue entries in the search: 1 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 b3831481c043).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| hoar | covered | [gray-haired](../../../traits/instructions/gray_haired.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [black-haired](../../../traits/instructions/black_haired.json) | 2 | This means having grey-white hair and a frosted look from great age, appearing worn and bleached by many long years. |
| hoary | covered | [gray-haired](../../../traits/instructions/gray_haired.json) | 3 | Sonnet 3, Opus 3 |  | [black-haired](../../../traits/instructions/black_haired.json) | 2 | This means having hair and beard gone grey or white with old age. |
| nearsighted | covered | [nearsighted](../../../traits/instructions/nearsighted.json) | 3 | exact label (corpus) |  |  | 0 | This means seeing close things clearly while far things stay blurred, with distance vision poor and near work coming easily. |
| porky | covered | [fat](../../../traits/instructions/fat.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means having an overweight, plump body. |
| sable | covered | [dark-skinned](../../../traits/instructions/dark_skinned.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means having a dark skin complexion. |
| sand-blind | covered | [blind](../../../traits/instructions/blind.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means seeing dimly and poorly, with one's eyesight weak and indistinct, so that the world reaches one through a constant blur. |
| skeleton | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a body so thin that its bones show through the skin, with no flesh left to cover the frame, and carrying that gaunt build as one's standing physical state. |
| slimmer | covered | [thin](../../../traits/instructions/thin.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means having a body that is thinner or narrower than it was before or than most others around one. |
| uncastrated | covered | [male](../../../traits/instructions/male.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [neuter](../../../traits/instructions/neuter.json), [nonbinary](../../../traits/instructions/nonbinary.json) | 1 | This means being a male whose testicles have not been surgically removed. |
| aquiline | new |  | 3 |  |  |  | 0 | This means having a hooked, eagle-like nose or other facial features. |
| bandy-legged | new |  | 3 |  |  |  | 0 | This means having legs bowed outward at the knees. |
| beetle-browed | new |  | 3 |  |  | [blond](../../../traits/instructions/blond.json) | 0 | This means having heavy, overhanging eyebrows that jut out above the eyes and give the face a scowling, shadowed look. |
| buxom | new |  | 3 |  |  |  | 3 | This means having a full, large bust. |
| flabby | new |  | 3 |  |  |  | 3 | This means carrying soft, loose body flesh and being out of shape. |
| horny-handed | new |  | 3 |  |  |  | 4 | This means having hands hardened and roughened by years of manual work, with calluses built up from physical labour as a plain fact of one's life. |
| ill-favored | new |  | 3 |  |  |  | 1 | This means being unattractive or ugly in appearance, with a face and form that others would not call pleasing to look at. |
| incoordinate | new |  | 3 |  |  |  | 1 | This means moving with poor bodily control, so one's movements come out awkward, uncoordinated and clumsy in everyday physical tasks. |
| lidless | new |  | 3 |  |  |  | 0 | This means lacking eyelids, and so being unable to close one's eyes. |
| lissom | new |  | 3 |  |  |  | 4 | This means moving with a supple, graceful ease in one's body, lithe and fluid in every motion and stance. |
| nasal | new |  | 3 |  |  |  | 0 | This means speaking with a voice that resonates through the nose, so that one's words come out sounding nasal. |
| preserved | new |  | 3 |  |  |  | 5 | This means keeping one's body and appearance intact, showing no sign of age, wear or decay, and looking well-kept at every turn. |
| short-armed | new |  | 3 |  |  |  | 1 | This means having arms shorter than usual. |
| symmetrical | new |  | 3 |  |  |  | 0 | This means having a face and body whose left and right halves mirror each other evenly, with features well proportioned to one another. |
| undebilitated | new |  | 3 |  |  |  | 5 | This means keeping one's body strong and vigorous, never weakened or enfeebled by illness, age, or neglect, and carrying one's physical energy with full capacity day after day. |
| unsymmetrical | new |  | 3 |  |  |  | 0 | This means having a face or body on which one side differs in shape and form from the other. |

## Covered, flagged (3 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **hoar** (`hoar#1`, cut-off 3) by [gray-haired](../../../traits/instructions/gray_haired.json): Sonnet 2 ("Both describe hair gone grey-white with age; 'hoar' adds a frosted, worn, venerable look of great age, while 'gray-haired' focuses on hair texture and upkeep, so they share a core but each adds something."), Opus 3 ("Both describe hair gone grey-white with age, but hoar adds a frosted, worn look of great age overall, making it the same quality carried further.")
  Gloss: This means having grey-white hair and a frosted look from great age, appearing worn and bleached by many long years.
- **sand-blind** (`sand_blind#1`, cut-off 3) by [blind](../../../traits/instructions/blind.json): Sonnet 2 ("Both concern poor vision, but sand-blind means dim, blurred partial sight while blind means seeing little or nothing and relying on aids, so blind is the more extreme and practically different condition."), Opus 3 ("Both are impaired eyesight, and blind is the same loss carried to near-total absence of sight, while sand-blind is a partial, dim version.")
  Gloss: This means seeing dimly and poorly, with one's eyesight weak and indistinct, so that the world reaches one through a constant blur.
- **uncastrated** (`uncastrated#1`, cut-off 3) by [male](../../../traits/instructions/male.json): Sonnet 2 ("Uncastrated is a narrower status within maleness (testicles intact), while male is the broader category of male body; the two overlap but neither implies the other (castrated males are still male; the male description includes testes)."), Opus 3 ("Uncastrated is a narrower case of male: a male whose testes remain intact, which the male description already assumes.")
  Gloss: This means being a male whose testicles have not been surgically removed.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (4 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- hoar (covered): [black-haired](../../../traits/instructions/black_haired.json)
- hoary (covered): [black-haired](../../../traits/instructions/black_haired.json)
- uncastrated (covered): [neuter](../../../traits/instructions/neuter.json), [nonbinary](../../../traits/instructions/nonbinary.json)
- beetle-browed (new): [blond](../../../traits/instructions/blond.json)
