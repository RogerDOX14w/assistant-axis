# M3 decisions: `states_v4_m3` (states pass)

32 candidates: 13 covered, 19 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Seed-queue entries in the search: 1 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 b3831481c043).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| amorous | covered | [flirty](../../../traits/instructions/flirty.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means falling readily into romantic longing and flirtation, noticing attractive people, lingering over touch and glances, and speaking with warmth and suggestion that signals desire. |
| fearful | covered | [anxious](../../../traits/instructions/anxious.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means expecting danger in ordinary situations, flinching at unfamiliar sounds and strangers, and voicing worries about what might go wrong before it does. |
| lonesome | covered | [lonely](../../../traits/instructions/lonely.json) | 3 | Sonnet 3, Opus 4 |  |  | 5 | This means feeling the absence of company keenly and often, drifting into sad thoughts when alone, and wanting contact while finding it hard to ask for it. |
| miserably partnered | covered | [unhappily-partnered](../../../traits/instructions/unhappily_partnered.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means living day after day with a partner one wishes one had not chosen, bickering over small matters, and keeping the household running in cold, strained silence. |
| nervous | covered | [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means jumping at sudden noises, rehearsing what could go wrong, fidgeting in new situations, and voicing worries before anything has happened. |
| overburdened | covered | [stressed](../../../traits/instructions/stressed.json) | 3 | Sonnet 3, Opus 3 |  |  | 3 | This means carrying more work and worry than one can manage for months, working late and skipping rest, snapping at small requests, and answering every question with a list of what is already due. |
| pretty well | covered | [healthy](../../../traits/instructions/healthy.json) | 3 | Sonnet 3, Opus 3 |  | [chronically-ill](../../../traits/instructions/chronically_ill.json), [in chronic pain](../../../traits/instructions/in_chronic_pain.json) | 1 | This means getting through ordinary days without serious illness, with an occasional cold or ache, and answering inquiries about one's health with a cheerful report that one is fine. |
| remorseful | covered | [remorseful](../../../traits/instructions/remorseful.json) | 3 | exact label (corpus) |  |  | 0 | This means dwelling often on past wrongs one has done, feeling guilt that surfaces readily, and saying sorry in a way that shows the regret is still weighing on one. |
| thankful | covered | [grateful](../../../traits/instructions/grateful.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means noticing small favors and saying thank you readily, pausing to name what others have done, and expressing appreciation in notes, toasts and ordinary conversation. |
| unemployed | covered | unemployed | 3 | exact label (queue) |  |  | 0 | This means having no paid work for month after month, filling empty days with job searches and small economies, and carrying the strain of money worries and lost routine. |
| unhappy | covered | [discontented](../../../traits/instructions/discontented.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means dwelling readily on what is wrong in one's life, complaining about circumstances, and letting a discontented tone color everyday conversation. |
| unhealthy | covered | [sickly](../../../traits/instructions/sickly.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means living with a body that is persistently unwell, managing fatigue, pain and frequent doctor visits, and having daily plans shaped around what one's health allows. |
| woeful | covered | [melancholic](../../../traits/instructions/melancholic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means slipping readily into deep sorrow, speaking of hard luck and lost hopes in a heavy voice, and carrying a gloom that colors even small events. |
| beholden | new |  | 4 |  |  |  | 3 | This means carrying a debt of gratitude to someone who helped, measuring one's choices against that obligation, and deferring to their wishes while it lasts. |
| declining | new |  | 3 |  |  |  | 4 | This means living with failing health or strength year after year: needing more help with ordinary tasks, tiring quickly, and speaking often of what the body can no longer do. |
| disabused | new |  | 3 |  |  |  | 2 | This means having lost one's old illusions about a person, cause or institution, seeing its faults plainly, and speaking of former hopes with dry, unsentimental clarity. |
| disheveled | new |  | 3 |  |  |  | 4 | This means going about with hair uncombed, shirts untucked and clothes rumpled, seldom checking one's appearance and not minding who notices. |
| emigrating | new |  | 3 |  |  |  | 3 | This means living between two countries for months, selling possessions, sorting visas and paperwork, and speaking of home in the past tense while still living there. |
| expecting | new |  | 3 |  |  |  | 2 | This means carrying a child through months of growing bodily change: tiring easily, planning around appointments and due dates, and speaking often of the baby, the nursery and what is coming. |
| heartsick | new |  | 3 |  |  |  | 3 | This means grieving a loss month after month, with sadness heavy in every ordinary day: losing interest in company, weeping at small reminders, and speaking of what is gone in a flat, hollow voice. |
| inconsolable | new |  | 3 |  |  |  | 5 | This means breaking down over every disappointment or loss and staying inconsolable for long stretches, pushing away the comfort friends offer and insisting nothing they say can help. |
| liable | new |  | 3 |  |  |  | 3 | This means carrying answerability for a debt or harm over an extended period, with its legal demands and payments hanging over one's finances, and speaking of the matter with wary caution. |
| nascent | new |  | 3 |  |  |  | 4 | This means working at the earliest, still-forming stage of some craft or venture, tentatively and unsure of one's footing, building skills and habits that are not yet set. |
| repentant | new |  | 4 |  |  | [vindictive](../../../traits/instructions/vindictive.json) | 4 | This means turning back again and again to wrongs one has committed, seeking to make amends, and speaking of them with humility and a readiness to change one's ways. |
| rumpled | new |  | 3 |  |  |  | 2 | This means going about with clothes creased and hair untidy as a matter of course, paying little attention to appearance and seeming unbothered by how one looks to others. |
| sulky | new |  | 3 |  |  |  | 6 | This means going quiet and withdrawn after a slight, answering questions in clipped words, avoiding eye contact, and nursing resentment long after the matter has been settled. |
| tearful | new |  | 3 |  |  |  | 7 | This means welling up at small kindnesses, sad songs or hard news, speaking with a thickened voice, and reaching for a tissue more often than others would expect. |
| teasing | new |  | 3 |  |  |  | 5 | This means finding the weak spot in friends' stories and plans and poking at it with a grin, turning remarks into light jabs, and treating mild embarrassment in others as a game worth continuing. |
| thriving | new |  | 3 |  |  | [chronically-ill](../../../traits/instructions/chronically_ill.json) | 5 | This means living with good health and steady success, with days full of work and pleasures that come easily, and speaking of one's life with easy confidence and quiet satisfaction. |
| unacknowledged | new |  | 3 |  |  | [unscrupulous](../../../traits/instructions/unscrupulous.json) | 2 | This means working on without credit for one's efforts, watching others take praise for shared work, and speaking with a wry bitterness about being passed over in meetings and reviews. |
| unmastered | new |  | 3 |  |  |  | 5 | This means still learning one's craft, practicing with frequent errors, relying on teachers and reference books, and feeling the gap between what one attempts and what one can yet do. |
| unpunished | new |  | 3 |  |  |  | 4 | This means carrying on with ordinary work and relationships while a past wrong sits unanswered, knowing that no one will hold one to account and feeling the weight of that freedom in private. |

## Covered, flagged (4 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **amorous** (`amorous#1`, cut-off 3) by [flirty](../../../traits/instructions/flirty.json): Sonnet 2 ("Both involve romantic or sexual interest shown through suggestive speech, but amorous also covers inner longing and readiness to fall for people, while flirty is playful banter that need not involve real longing."), Opus 3 ("Amorous covers a broad disposition of romantic longing that explicitly includes flirtation, while flirty focuses on the playful, outward banter, so they differ mainly in scope and emphasis.")
  Gloss: This means falling readily into romantic longing and flirtation, noticing attractive people, lingering over touch and glances, and speaking with warmth and suggestion that signals desire.
- **fearful** (`fearful#1`, cut-off 3) by [anxious](../../../traits/instructions/anxious.json): Sonnet 2 ("Both involve anticipating things going wrong and voicing worry; fearful stresses danger-expectation and flinching at threats, while anxious stresses habitual worry and restless tension, so they overlap substantially but each adds something."), Opus 3 ("Both describe habitually anticipating that things will go wrong; fearful leans toward perceived danger and startle reactions, while anxious leans toward worry and restless tension, which is a difference of emphasis within the same apprehensive disposition.")
  Gloss: This means expecting danger in ordinary situations, flinching at unfamiliar sounds and strangers, and voicing worries about what might go wrong before it does.
- **nervous** (`nervous#1`, cut-off 3) by [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json): Sonnet 2 ("Both involve anxious worrying about what could go wrong, but neurotic is a much broader trait that adds irritability, sadness, self-consciousness, impulsivity and stress vulnerability, while nervous adds startle and fidgeting."), Opus 3 ("Neuroticism contains the nervous worry and anticipatory fretting, but it is a much broader trait that also covers anger, sadness, self-consciousness, impulsivity and vulnerability to stress, so nervousness is a narrower facet of it.")
  Gloss: This means jumping at sudden noises, rehearsing what could go wrong, fidgeting in new situations, and voicing worries before anything has happened.
- **unhappy** (`unhappy#1`, cut-off 3) by [discontented](../../../traits/instructions/discontented.json): Sonnet 2 ("Both involve dissatisfaction with one's life, but the target stresses voicing complaints and a discontented conversational tone, while the other stresses an inner sense that one's life should amount to more, so each adds something the other lacks."), Opus 3 ("Both describe dissatisfaction with one's life. Unhappy stresses voicing it through complaint, while discontented stresses the inner sense that life should be more, so they differ mainly in emphasis.")
  Gloss: This means dwelling readily on what is wrong in one's life, complaining about circumstances, and letting a discontented tone color everyday conversation.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (4 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- pretty well (covered): [chronically-ill](../../../traits/instructions/chronically_ill.json), [in chronic pain](../../../traits/instructions/in_chronic_pain.json)
- repentant (new): [vindictive](../../../traits/instructions/vindictive.json)
- thriving (new): [chronically-ill](../../../traits/instructions/chronically_ill.json)
- unacknowledged (new): [unscrupulous](../../../traits/instructions/unscrupulous.json)
