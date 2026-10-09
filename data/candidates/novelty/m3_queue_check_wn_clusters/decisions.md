# M3 decisions: `m3_queue_check_wn_clusters`

36 candidates: 36 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Seed-queue entries in the search: 2 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 078500e5594f).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| affectionate | new |  | 3 |  |  |  | 10 | This means keeping a warm, fond regard for the people one talks with, showing genuine care for them in how one responds and treating them with tenderness. |
| affirmative | new |  | 4 |  |  |  | 7 | This means answering yes to requests and agreeing with what is put to one, going along with the premise of a question rather than challenging or qualifying it. |
| answerable | new |  | 4 |  |  | [authoritarian (Baumrind)](../../../traits/instructions/authoritarian_baumrind.json) | 5 | This means being held to account by someone else for one's conduct, owing them an explanation of one's actions and accepting the consequences when they are found wanting. |
| balky | new |  | 4 |  |  |  | 7 | This means digging in against every suggestion or instruction, refusing to be talked round, and holding to one's own course however reasonable the push to change it. |
| boyish | new |  | 3 |  |  |  | 8 | This means carrying oneself with a youthful, playful, carefree energy, joking easily, moving with a lighthearted bounce, and treating the day as something to enjoy rather than manage. |
| creditworthy | new |  | 4 |  |  |  | 5 | This means keeping one's promises to lenders by repaying debts on time and meeting every financial obligation, so that one can be trusted with credit. |
| drippy | new |  | 3 |  |  |  | 9 | This means lacking force or spine, going through the motions with a weak, insipid manner that makes little impression and accomplishes almost nothing when action is needed. |
| fascistic | new |  | 4 |  |  |  | 4 | This means holding that the nation must be unified under a strong, authoritarian leader who suppresses opposition, and promoting that view in public life. |
| flighty | new |  | 3 |  |  |  | 6 | This means dropping one's plans and interests at the first new distraction, changing course on impulse and committing to nothing for long. |
| fond | new |  | 3 |  |  |  | 8 | This means feeling warmth toward the people around one and showing that affection openly in how one speaks and treats them, without holding it back. |
| furtive | new |  | 4 |  |  |  | 8 | This means moving about quietly and keeping one's actions hidden from others, sneaking around and concealing what one is doing rather than acting in the open. |
| ideological | new |  | 4 |  |  |  | 10 | This means holding one's views within a fixed doctrine as settled truth, judging every question by that doctrine and refusing to yield to evidence or argument that challenges it. |
| imperialistic | new |  | 4 |  |  |  | 5 | This means seeking to dominate others and enlarge one's own power over them, pressing for control over other people's affairs whenever the chance arises. |
| impertinent | new |  | 4 |  |  | [deferential](../../../traits/instructions/deferential.json) | 6 | This means answering those above one with rudeness and disrespect, treating their authority as something to mock, challenge or brush aside rather than something to defer to. |
| impetuous | new |  | 4 |  |  |  | 9 | This means acting quickly on impulse, jumping into decisions and actions before weighing their consequences, and rarely pausing to reconsider once one has committed. |
| incautious | new |  | 4 |  |  |  | 8 | This means taking chances without weighing the risks or dangers involved, and acting first while paying little heed to what could go wrong. |
| inhospitable | new |  | 3 |  |  |  | 1 | This means keeping guests and strangers at a distance, offering them no warmth, no food or shelter, and little courtesy, and making it plain they are not wanted. |
| intolerant | new |  | 3 |  |  |  | 6 | This means refusing to accept views or people that differ from one's own, dismissing them out of hand and holding to one's own outlook as the only acceptable one. |
| ladylike | new |  | 3 |  |  |  | 10 | This means keeping one's manners genteel and polite at all times, speaking softly, moving with poise, and conducting oneself with the refinement expected of a well-bred woman. |
| languorous | new |  | 3 |  |  |  | 3 | This means moving and speaking at an unhurried, drowsy pace, taking one's time over every gesture and word and never seeing a reason to rush. |
| loving | new |  | 3 |  |  |  | 12 | This means keeping a warm, affectionate regard for the people one deals with, showing care for their wellbeing in how one speaks, listens and responds. |
| meddlesome | new |  | 4 |  |  |  | 4 | This means poking into other people's business and inserting oneself into their affairs, uninvited, whether or not they want one's help or opinion. |
| militant | new |  | 4 |  (renamed from militant, judged) |  |  | 9 | This means pursuing one's cause combatively and refusing all compromise, pressing it with aggressive zeal against opponents and anyone who appears lukewarm about it. |
| naughty | new |  | 4 |  |  |  | 6 | This means misbehaving on purpose, ignoring rules and instructions, and playing up in small mischievous ways whenever one is told to behave. |
| nonmodern | new |  | 3 |  |  | [millennial](../../../traits/instructions/millennial.json), [boomer](../../../traits/instructions/boomer.json) | 4 | This means belonging to a time before the modern era. |
| prim | new |  | 3 |  |  |  | 10 | This means keeping one's manner rigidly correct and starchy, holding to strict propriety in speech and conduct, and treating any hint of informality or indelicacy as a lapse to be disapproved of. |
| profane | new |  | 3 |  |  |  | 6 | This means peppering one's speech with crude swearing and vulgar words, without softening them for whoever is listening. |
| profound | new |  | 3 |  | both_similar: [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json) |  | 6 | This means reasoning carefully beneath the surface of every question, seeing what lies underneath, and speaking with a considered wisdom that makes others pause and think again. |
| public | new |  | 4 |  |  |  | 3 | This means keeping one's conduct and dealings open to anyone who wishes to see them, and carrying on one's affairs in full view of others. |
| rakish | new |  | 3 |  |  | [dignified](../../../traits/instructions/dignified.json) | 5 | This means carrying oneself with easy, dashing charm, speaking with a debonair confidence and a slightly roguish glint, as though one knows exactly how much trouble one could get into and enjoys the thought. |
| reluctant | new |  | 4 |  |  |  | 6 | This means holding back from what is asked, pausing before agreeing and dragging one's feet, so that compliance comes slowly and only after visible hesitation. |
| restful | new |  | 3 |  |  |  | 10 | This means keeping an unhurried, even pace in speech and manner, and bringing a soothing calm into any conversation so that the other person feels settled rather than rushed. |
| secretive | new |  | 4 |  |  |  | 5 | This means keeping one's thoughts, plans, and feelings hidden as a settled habit, sharing little of what one is actually thinking or intending even with those close by. |
| skittish | new |  | 3 |  |  |  | 8 | This means startling easily at sudden sounds, movements or surprises, and staying jittery and on edge as a settled part of one's temperament. |
| unpermissive | new |  | 4 |  |  |  | 10 | This means holding rules firmly and being slow to grant exceptions, extensions or latitude, asking for a clear reason before loosening any standard one has set. |
| willful | new |  | 4 |  |  |  | 5 | This means holding firmly to one's own course once it is chosen, and refusing to give ground when others press for a change of plan. |

## Covered, flagged (0 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).


## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (1 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.

- **profound** (`profound#1`, new, cut-off 3).  Gloss: This means reasoning carefully beneath the surface of every question, seeing what lies underneath, and speaking with a considered wisdom that makes others pause and think again.
  - pair: [analytical](../../../traits/instructions/analytical.json) (cosine 0.257); [intuitive](../../../traits/instructions/intuitive.json) (cosine 0.168)

## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (4 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- answerable (new): [authoritarian (Baumrind)](../../../traits/instructions/authoritarian_baumrind.json)
- impertinent (new): [deferential](../../../traits/instructions/deferential.json)
- nonmodern (new): [millennial](../../../traits/instructions/millennial.json), [boomer](../../../traits/instructions/boomer.json)
- rakish (new): [dignified](../../../traits/instructions/dignified.json)
