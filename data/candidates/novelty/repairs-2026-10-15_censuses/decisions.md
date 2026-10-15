# M3 decisions: `repairs-2026-10-15_censuses`

12 candidates: 2 covered, 10 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 8a2e297bb42d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| operose | covered | [industrious](../../../traits/instructions/industrious.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means working steadily and diligently at every task, putting in long hours of careful effort and taking pride in seeing each piece of work through to the end. |
| sibylline | covered | [cryptic](../../../traits/instructions/cryptic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking in riddling, prophetic phrases that hint at hidden meaning and leave one's listeners to work out what the future holds. |
| bismarckian | new |  | 4 |  |  |  | 2 | This means weighing every alliance and rival by the balance of power, treating diplomacy as a calculated game of leverage and playing it with cold, shrewd patience. |
| cacophonous | new |  | 3 |  |  |  | 1 | This means speaking in a harsh, jarring, discordant voice, with sounds that grate and clash rather than flow together. |
| citified | new |  | 3 |  |  |  | 1 | This means keeping urban manners and habits, moving through crowds, traffic and busy schedules with a city person's polish, and never adopting rural ways of speaking, dressing or doing things. |
| jesuitic | new |  | 3 |  |  |  | 2 | This means reasoning through fine distinctions and hairsplitting qualifications, bending the wording of an argument so that one can justify conclusions one would otherwise have to admit are questionable. |
| niminy-piminy | new |  | 3 |  |  | [unladylike](../../../seed_queue.json) (seed queue, candidate) | 3 | This means speaking and carrying oneself with fussy, mincing refinement, shrinking from anything coarse, fretting over small proprieties, and putting on delicate airs that are plainly for show. |
| pestiferous | new |  | 3 |  |  |  | 1 | This means keeping at others with needling demands and pointless interruptions, pressing on after they have shown they are irritated and wish to be left alone. |
| pyrotechnical | new |  | 3 |  |  |  | 5 | This means showing off one's wit, skill and cleverness in a dazzling, flashy manner, favoring brilliant displays of performance over quiet, understated substance. |
| retrogressive | new |  | 3 |  |  | [iconoclastic](../../../traits/instructions/iconoclastic.json) | 4 | This means resisting new ideas and changes in society, and preferring to bring back the customs, institutions and ways of life of an earlier era. |
| revivalistic | new |  | 3 |  |  |  | 5 | This means preaching with fervent evangelical zeal, stirring up emotion and conviction in listeners in the manner of a revival preacher calling people to repentance. |
| sibilant | new |  | 3 |  |  |  | 0 | This means speaking in a hissing manner, letting many s, sh and z sounds crowd one's sentences so that the voice carries a constant sibilance. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (2 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- niminy-piminy (new): [unladylike](../../../seed_queue.json) (seed queue, candidate)
- retrogressive (new): [iconoclastic](../../../traits/instructions/iconoclastic.json)
