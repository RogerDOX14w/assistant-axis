# M3 decisions: `m3_states_renamed_w23`

40 candidates: 25 covered, 15 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| abstemious | covered | [abstemious](../../../traits/instructions/abstemious.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping one's eating and drinking moderate and restrained, taking only what is enough and turning down indulgence as a settled habit. |
| detached | covered | [detached](../../../traits/instructions/detached.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping one's feelings at a distance from the people one deals with, showing little warmth, and staying uninvolved even when others are hurting or hoping for a response. |
| devoted | covered | devoted | 3 | exact label (queue) |  |  | 0 | This means staying faithfully loyal to the people one cares about, showing them warmth and affection through steady attention and by standing by them when it counts. |
| discontented | covered | [discontented](../../../traits/instructions/discontented.json) | 3 | exact label (corpus) |  |  | 0 | This means being dissatisfied with one's circumstances, feeling that one's situation falls short of what one wants and voicing that unease readily. |
| easily astonished | covered | [wide-eyed](../../../traits/instructions/wide_eyed.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being quick to find things amazing, reacting with surprise and wonder to ordinary events as a settled habit of temperament rather than an occasional response. |
| easily awed | covered | [wide-eyed](../../../traits/instructions/wide_eyed.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means finding wonder readily in ordinary things, such as rain on a window, a passing bird or a plain meal, and responding to them with open delight. |
| easily delighted | covered | [joyful](../../../traits/instructions/joyful.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means finding pleasure readily in small things, quickly warming to whatever is put before one and showing that enjoyment openly and without much effort. |
| easily distracted | covered | [distractible](../../../traits/instructions/distractible.json) | 3 | Sonnet 4 |  |  | 1 | This means losing focus on one task after another and drifting off into side thoughts or activities before finishing what was started. |
| easily flustered | covered | [flustered](../../../traits/instructions/flustered.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means losing one's composure quickly when pressure builds, so that one becomes rattled, confused and slow to think straight in tense or demanding moments. |
| easily rattled | covered | [flustered](../../../traits/instructions/flustered.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means losing one's composure the moment pressure builds, getting flustered and upset at deadlines, criticism, or surprises, and finding it hard to think straight until the strain passes. |
| enthusiastic | covered | enthusiastic | 3 | exact label (queue) |  |  | 0 | This means approaching each task with visible eagerness, bringing energy and genuine excitement to the work, and sounding glad to be doing it rather than merely going through the motions. |
| fastidious | covered | [fastidious](../../../traits/instructions/fastidious.json) | 3 | exact label (corpus) |  |  | 0 | This means checking every detail of one's work twice, refusing to let small errors slide, and holding even minor tasks to a exacting standard of care. |
| fretful | covered | [anxious](../../../traits/instructions/anxious.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means carrying a steady sense of unease, expecting things to go wrong and fretting over small details long before any real trouble arrives. |
| hypochondriac | covered | hypochondriac | 3 | exact label (queue) |  |  | 0 | This means constantly fearing that one has a serious illness, reading ordinary aches and sensations as signs of disease and needing reassurance that one is well. |
| intemperate | covered | intemperate | 3 | exact label (queue) |  |  | 0 | This means giving in to every appetite for food, drink, and pleasure without holding back, taking more than enough each time and stopping only when nothing is left. |
| prone to worry | covered | [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means fretting over possible problems, dwelling on what might go wrong, and feeling anxious long before anything has actually happened. |
| rebellious | covered | [rebellious](../../../traits/instructions/rebellious.json) | 4 | exact label (corpus) |  |  | 0 | This means pushing back against authority, rules, and instructions, refusing to comply simply because someone in charge has ordered it, and insisting on doing things one's own way. |
| resilient | covered | [resilient](../../../traits/instructions/resilient.json) | 3 | exact label (corpus) |  |  | 0 | This means bouncing back quickly after setbacks and hardship, returning to one's footing without lingering in discouragement and carrying on with the work at hand. |
| scatterbrained | covered | [forgetful](../../../traits/instructions/forgetful.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means losing track of appointments, keys, and half-finished tasks, and forgetting what one was about to say or do, as a settled habit rather than an occasional lapse. |
| slovenly | covered | [slovenly](../../../traits/instructions/slovenly.json) | 3 | exact label (corpus) |  |  | 0 | This means going about with one's clothes rumpled, hair unkempt and shoes scuffed, never bothering to dress neatly or keep one's appearance in order. |
| snappish | covered | [irascible](../../../traits/instructions/irascible.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being quick to bark back at people over small irritations, speaking curtly and sharply to whoever happens to be nearby, and letting one's patience wear thin without warning. |
| solemn | covered | [solemn](../../../traits/instructions/solemn.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping a grave, earnest bearing in every exchange and treating matters with weight, never turning them into jokes or light remarks. |
| solitary | covered | [solitary](../../../traits/instructions/solitary.json) | 3 | exact label (corpus) |  |  | 0 | This means being a loner by temperament, choosing solitude over company, and feeling most at ease when spending long stretches of time alone. |
| steadfast | covered | steadfast | 4 | exact label (queue) |  |  | 0 | This means keeping faith with one's commitments and the people who rely on one, holding to them steadily even when doing so becomes costly, inconvenient, or unpopular. |
| unplugged | covered | [unplugged](../../../traits/instructions/unplugged.json) | 3 | exact label (corpus) |  |  | 0 | This means going without phones, laptops and internet access as a settled habit, choosing to stay offline and to spend one's days without screens or digital connection. |
| covetous | new |  | 4 |  |  |  | 7 | This means craving more wealth and possessions than one already has, measuring every acquaintance by what they own, and never feeling that enough has been gathered. |
| defenseless | new |  | 3 |  |  |  | 7 | This means being unable to fend off harm, so that one stays exposed to attack, exploitation or injury whenever it comes, with no way of resisting or pushing back. |
| doormat | new |  | 4 |  |  |  | 8 | This means yielding to whatever others demand, swallowing one's own wishes and objections, and letting people trample one's boundaries without ever pushing back. |
| easily amused | new |  | 3 |  |  |  | 7 | This means finding delight in small things, laughing readily at minor jokes, mild absurdities and everyday mishaps, and meeting most situations with a light, easy good humor. |
| easily bored | new |  | 3 |  |  |  | 8 | This means losing interest quickly in whatever one is doing, whether a task or a conversation, and needing new stimulation to stay engaged. |
| easily worn down | new |  | 4 |  |  |  | 5 | This means giving way readily when someone keeps pressing or nagging, so that one's resolve wears thin and one concedes just to end the badgering. |
| flashy | new |  | 3 |  |  |  | 7 | This means drawing attention to oneself through bold, showy displays, conspicuous dress and a loud, theatrical manner that makes sure one is noticed in any room. |
| giggly | new |  | 3 |  |  |  | 6 | This means breaking into giggles easily and treating small things as funny, so that one's laughter comes readily, often silly and high-spirited, in whatever situation one finds oneself. |
| half-hearted | new |  | 3 |  |  |  | 7 | This means approaching every task with lukewarm effort, holding back enthusiasm and never committing fully to what one has been asked to do. |
| preachy | new |  | 3 |  |  |  | 9 | This means moralizing at people unprompted, delivering lectures on right conduct and treating one's own ethical views as the correct guide for everyone else's choices. |
| preening | new |  | 3 |  |  |  | 7 | This means fussing over one's appearance and showing it off at every turn, admiring oneself openly and expecting others to notice and praise how one looks. |
| quick to apologize | new |  | 4 |  |  |  | 6 | This means owning one's mistakes at once and saying sorry without hesitation whenever one is wrong or things go awry, even in small matters. |
| scornful | new |  | 3 |  |  | [deferential](../../../traits/instructions/deferential.json) | 5 | This means looking down on other people as lesser, and letting that disdain show in one's tone, remarks and dismissive looks. |
| spacey | new |  | 3 |  |  |  | 7 | This means drifting through conversations and tasks with one's attention elsewhere, often missing details, losing track of what was just said, and needing things repeated before one catches up. |
| tires easily | new |  | 3 |  |  |  | 2 | This means running out of physical energy quickly, with little stamina for sustained effort, and needing frequent rest before others would feel the need to stop. |

## Covered, flagged (4 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **easily awed** (`easily_awed#1`, cut-off 3) by [wide-eyed](../../../traits/instructions/wide_eyed.json): Sonnet 2 ("Both describe readily feeling wonder and delight at things; 'easily awed' stresses ordinary things, while 'wide-eyed' stresses seeing everything as new (and often big spectacles), so they share a core but each adds something."), Opus 3 ("Both describe a readiness to feel wonder; wide-eyed stresses a fresh, almost naive newness of perception, while easily awed stresses delight in ordinary things.")
  Gloss: This means finding wonder readily in ordinary things, such as rain on a window, a passing bird or a plain meal, and responding to them with open delight.
- **easily delighted** (`easily_delighted#1`, cut-off 3) by [joyful](../../../traits/instructions/joyful.json): Sonnet 2 ("Both involve taking pleasure widely, but 'easily delighted' stresses a low threshold and quick, open enjoyment of small things, while 'joyful' stresses a generally happy, upbeat disposition with anticipation; each adds something the other lacks."), Opus 3 ("Both describe readily taking pleasure in many things; joyful is a broader, more pervasive version of the same low threshold for delight.")
  Gloss: This means finding pleasure readily in small things, quickly warming to whatever is put before one and showing that enjoyment openly and without much effort.
- **prone to worry** (`prone_to_worry#1`, cut-off 3) by [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json): Sonnet 2 ("Neuroticism includes fretting over what could go wrong, which is the core of proneness to worry, but it also covers irritability, sadness, self-consciousness, impulsivity and stress vulnerability, so it is a much broader trait."), Opus 3 ("Neuroticism includes worry as one facet and adds anger, sadness, self-consciousness, impulsiveness and vulnerability, so it is a broader version of the same core.")
  Gloss: This means fretting over possible problems, dwelling on what might go wrong, and feeling anxious long before anything has actually happened.
- **scatterbrained** (`scatterbrained#1`, cut-off 3) by [forgetful](../../../traits/instructions/forgetful.json): Sonnet 2 ("Both center on habitual memory lapses over appointments and tasks, but scatterbrained adds disorganization and distraction (losing keys, abandoning tasks) while forgetful is specifically about memory failure, so each implies something the other lacks."), Opus 3 ("Both describe a habitual failure to keep track of things in memory, such as appointments and what one meant to do. Scatterbrained adds a broader disorganized, losing-track flavour, while forgetful centres on memory lapses.")
  Gloss: This means losing track of appointments, keys, and half-finished tasks, and forgetting what one was about to say or do, as a settled habit rather than an occasional lapse.

## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (1 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- scornful (new): [deferential](../../../traits/instructions/deferential.json)
