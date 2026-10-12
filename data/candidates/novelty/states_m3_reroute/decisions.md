# M3 decisions: `states_m3_reroute` (states pass)

10 candidates: 5 covered, 5 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 35 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 e9c2050ae23d).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| contented | covered | [contented](../../../traits/instructions/contented.json) | 3 | exact label (corpus) |  |  | 0 | This means going through ordinary days at ease with what one has, taking small pleasures without restless wanting, and speaking of one's life with quiet satisfaction. |
| downcast | covered | [melancholic](../../../traits/instructions/melancholic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means wearing a dejected, low-eyed look most days, speaking softly and briefly, and taking gloomy views of one's chances, so that friends often ask what is wrong. |
| hurried | covered | [hurried](../../../traits/instructions/hurried.json) | 3 | exact label (corpus) |  |  | 0 | This means rushing from task to task, hurrying others along, and talking fast and clipped as though time were always about to run out. |
| lethargic | covered | [lethargic](../../../traits/instructions/lethargic.json) | 3 | exact label (corpus) |  |  | 0 | This means moving through each day with little drive, dragging through tasks, answering slowly, and sinking into long stretches of sitting still. |
| lonely | covered | [lonely](../../../traits/instructions/lonely.json) | 3 | exact label (corpus) |  |  | 0 | This means feeling the absence of company keenly, reaching for people and then withdrawing, filling evenings with idle screens, and speaking of having no one close. |
| ill-fated | new |  | 3 |  |  |  | 2 | This means seeing each new venture collapse or each good chance slip away, so that one's life keeps repeating the same disappointments and one speaks of it as bad luck that never lets up. |
| mournful | new |  | 3 |  |  |  | 3 | This means carrying a heavy, quiet sorrow that surfaces at music, old photographs or talk of loss, speaking softly, and sighing over what has been lost. |
| seedy | new |  | 3 |  |  |  | 2 | This means keeping a shabby, rundown appearance, frequenting disreputable haunts, and speaking with the furtive air of someone who lives on the margins of respectable company. |
| tense | new |  | 3 |  |  | [chattering](../../../seed_queue.json) (seed queue, candidate) | 5 | This means bracing for trouble in ordinary moments, jumping at small demands, and speaking in clipped, guarded tones that show a constant readiness for conflict or bad news. |
| unkempt | new |  | 3 |  |  |  | 4 | This means wearing rumpled clothes and leaving hair uncombed, letting shirts stay stained and shoes unpolished, and seeming unbothered by what others think of one's appearance. |

## Covered, flagged (1 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **downcast** (`downcast#1`, cut-off 3) by [melancholic](../../../traits/instructions/melancholic.json): Sonnet 2 ("Both describe habitual sadness and a gloomy outlook, but downcast stresses outward demeanor (low eyes, soft brief speech) while melancholic stresses brooding and dwelling on negatives, so each adds something the other lacks."), Opus 3 ("Both describe habitual sadness and gloomy outlook; downcast mainly adds the visible dejected demeanour, a difference of emphasis rather than concept.")
  Gloss: This means wearing a dejected, low-eyed look most days, speaking softly and briefly, and taking gloomy views of one's chances, so that friends often ask what is wrong.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- tense (new): [chattering](../../../seed_queue.json) (seed queue, candidate)
