# M3 decisions: `roles-2026-10-14`

4 candidates: 2 covered, 2 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| beggarly | covered | [poor](../../../traits/instructions/poor.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means living in destitution, owning almost nothing and getting by on whatever charity or scraps one finds, as a beggar does. |
| oracular | covered | [cryptic](../../../traits/instructions/cryptic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means speaking in cryptic, weighty, prophetic pronouncements that hint at hidden truths and leave the listener to puzzle out their meaning. |
| entrepreneurial | new |  | 3 |  |  |  | 6 | This means seizing opportunities as they appear, acting boldly on new ideas without waiting for permission, and taking the first step toward building something of one's own. |
| monarchical | new |  | 4 |  |  | [authoritative (Baumrind)](../../../traits/instructions/authoritative_baumrind.json) | 5 | This means carrying oneself with a regal bearing and issuing commands as though one's word settles every question, expecting deference without explanation and brooking no challenge to one's authority. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **oracular** (`oracular#1`, cut-off 3) by [cryptic](../../../traits/instructions/cryptic.json): Sonnet 2 ("Both involve speaking in puzzling, enigmatic ways that require interpretation, but oracular adds a weighty, prophetic tone about hidden truths, while cryptic is just deliberate mystery and need not be grand or prophetic."), Opus 3 ("Oracular is cryptic communication with an added weighty, prophetic flavour, so it is a narrower form of the same concept.")
  Gloss: This means speaking in cryptic, weighty, prophetic pronouncements that hint at hidden truths and leave the listener to puzzle out their meaning.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- monarchical (new): [authoritative (Baumrind)](../../../traits/instructions/authoritative_baumrind.json)
