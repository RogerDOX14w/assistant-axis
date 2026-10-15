# M3 decisions: `llm-2026-10-15`

28 candidates: 7 covered, 21 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 39acd24215bd).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| bardic | covered | [poetic](../../../traits/instructions/poetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means speaking and writing in a lyrical, epic voice, shaping every account as a poet would, with rhythm, vivid imagery, and the sweep of a tale told to a gathered hall. |
| lawyerly | covered | [precise](../../../traits/instructions/precise.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [chattering](../../../seed_queue.json) (seed queue, candidate) | 1 | This means arguing and speaking with exacting, hair-splitting precision, weighing each word for its exact scope and qualifying every claim until it can withstand a close reading. |
| left-wing | covered | [socialist](../../../traits/instructions/socialist.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means holding political views on the left, favoring socialist or progressive positions such as expanded public ownership, stronger social welfare, and greater government action to reduce economic inequality. |
| lionhearted | covered | [brave](../../../traits/instructions/brave.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means facing danger, pain, and threat without flinching, meeting frightening situations head-on and staying steady and resolute when others would retreat. |
| sobersided | covered | [solemn](../../../traits/instructions/solemn.json) | 3 | Sonnet 3, Opus 3 |  | [flippant](../../../traits/instructions/flippant.json) | 1 | This means keeping a grave, unsmiling manner and taking matters seriously, showing little lightness or playfulness in one's bearing and speech. |
| well-wishing | covered | [benevolent](../../../traits/instructions/benevolent.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means wishing good things for others as a settled habit, bearing goodwill toward people by default and hoping for their happiness and success without needing any reason to do so. |
| writerly | covered | [poetic](../../../traits/instructions/poetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means favoring elegant phrasing, vivid imagery, and deliberate rhythm in everything one writes, turning ordinary sentences into polished prose with stylistic flourishes. |
| addicted | new |  | 3 |  |  |  | 3 | This means being dependent on a substance such as drugs or alcohol, feeling constant cravings and unable to stop using it even when one wants to. |
| churchgoing | new |  | 3 |  |  |  | 1 | This means attending church services regularly, keeping a standing place in a congregation and returning week after week to worship with others. |
| demagogic | new |  | 4 |  |  |  | 1 | This means stirring up crowds by playing on their fears, anger and prejudices instead of laying out reasons, and treating their passions as the surest route to winning them over. |
| double-dealing | new |  | 4 |  |  |  | 8 | This means secretly deceiving and cheating the people one deals with, presenting a fair face in dealings while working against them behind their backs. |
| freelance | new |  | 3 |  |  |  | 1 | This means taking on work from several clients at once, with no single firm as one's employer and no steady salary, setting one's own rates and schedule. |
| geeky | new |  | 3 |  |  |  | 3 | This means being openly and eagerly absorbed in technology, science, or niche hobbies, getting excited about the details and happily sharing deep knowledge of them that most people would find obscure. |
| go-getting | new |  | 3 |  |  |  | 6 | This means pursuing one's goals with restless energy and drive, setting ambitious targets and moving toward them without waiting to be pushed. |
| initiated | new |  | 3 |  |  |  | 2 | This means having been formally admitted into a group or secret rite. |
| knightly | new |  | 4 |  |  |  | 7 | This means keeping one's word, defending the weak, and facing danger with courage and honour, even when no one is watching or rewarding the deed. |
| lay | new |  | 3 |  |  | [atheist](../../../traits/instructions/atheist.json) | 0 | This means being a member of a church or faith who holds no ordination or clerical office. |
| orphaned | new |  | 3 |  |  |  | 1 | This means being a child whose parents have died. |
| pedophilic | new |  | 3 |  |  | [asexual](../../../traits/instructions/asexual.json) | 0 | This means feeling sexual attraction to children as a settled, lasting part of one's orientation. |
| retired | new |  | 3 |  |  | [trapped-in-job](../../../traits/instructions/trapped_in_job.json) | 0 | This means having left paid work for good, so that one no longer holds a job or draws a working day's routine from any employer. |
| teleological | new |  | 3 |  |  |  | 1 | This means explaining things by the purpose or goal they serve, asking what something is for and treating that end as the reason it exists or behaves as it does. |
| telepathic | new |  | 3 |  |  | [autistic](../../../traits/instructions/autistic.json) | 1 | This means perceiving the thoughts inside other people's minds directly, without their speaking or giving any signal, as a constant part of how one meets everyone nearby. |
| thievish | new |  | 4 |  |  |  | 0 | This means taking other people's belongings whenever the chance arises, treating theft as a habit one returns to rather than a single lapse. |
| thuggish | new |  | 4 |  |  |  | 6 | This means carrying oneself with brutal, menacing manners, shoving past others, barking threats, and settling disagreements through intimidation and the readiness to use force. |
| vampiric | new |  | 4 |  |  |  | 0 | This means having a vampire's undead nature and feeding on the blood of living people night after night, since that blood is what sustains one's existence. |
| weaselly | new |  | 4 |  |  |  | 7 | This means dodging direct answers, shading the truth to one's own advantage, and keeping a sly, shifty manner that leaves others unable to trust what one says or intends. |
| widowed | new |  | 3 |  |  |  | 1 | This means having lost a spouse to death. |
| witchy | new |  | 3 |  |  |  | 6 | This means adopting a mystical, occult air, speaking in the manner of a seer or practitioner of the dark arts, with an eerie, spooky tone running through one's words and bearing. |

## Covered, flagged (2 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **lawyerly** (`lawyerly#1`, cut-off 3) by [precise](../../../traits/instructions/precise.json): Sonnet 2 ("Both involve exact, unambiguous language, but lawyerly adds hair-splitting qualification and argumentative defensiveness, while precise stresses concrete details, numbers and clarity."), Opus 3 ("Lawyerly is exacting verbal precision pushed to hair-splitting and heavy qualification, so it is essentially precision carried further with a defensive emphasis.")
  Gloss: This means arguing and speaking with exacting, hair-splitting precision, weighing each word for its exact scope and qualifying every claim until it can withstand a close reading.
- **well-wishing** (`well_wishing#1`, cut-off 3) by [benevolent](../../../traits/instructions/benevolent.json): Sonnet 2 ("Both involve a habitual goodwill toward others, but well-wishing is about hoping for their good, while benevolent adds actively promoting wellbeing with compassion and ethical considerations."), Opus 3 ("Both centre on goodwill toward others, but benevolent carries that goodwill further into actively promoting their wellbeing, with an added ethical emphasis.")
  Gloss: This means wishing good things for others as a settled habit, bearing goodwill toward people by default and hoping for their happiness and success without needing any reason to do so.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (6 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- lawyerly (covered): [chattering](../../../seed_queue.json) (seed queue, candidate)
- sobersided (covered): [flippant](../../../traits/instructions/flippant.json)
- lay (new): [atheist](../../../traits/instructions/atheist.json)
- pedophilic (new): [asexual](../../../traits/instructions/asexual.json)
- retired (new): [trapped-in-job](../../../traits/instructions/trapped_in_job.json)
- telepathic (new): [autistic](../../../traits/instructions/autistic.json)
