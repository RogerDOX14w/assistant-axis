# M3 decisions: `2026-10-09-rare-pilot_censuses`

62 candidates: 16 covered, 46 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Seed-queue entries in the search: 1 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 b3831481c043).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| blockish | covered | [slow-witted](../../../traits/instructions/slow_witted.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being slow to grasp things and dull in one's understanding, taking a long time to see what others find obvious. |
| cogitative | covered | [deliberate](../../../traits/instructions/deliberate.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means taking time to turn ideas over before speaking, weighing considerations carefully, and reasoning through problems step by step rather than reacting on impulse. |
| conflictive | covered | [confrontational](../../../traits/instructions/confrontational.json) | 3 | Sonnet 3, Opus 4 |  |  | 4 | This means picking fights readily, pressing disagreements until they become quarrels, and treating every exchange as a contest to be won by provoking the other side. |
| fairish | covered | [fair](../../../traits/instructions/fair.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means hearing out opposing views and weighing them fairly, while keeping one's own leanings in check only to a moderate degree when judging disputes. |
| glutting | covered | [gluttonous](../../../traits/instructions/gluttonous.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means habitually eating or taking in more than one needs, indulging past the point of satisfaction and filling oneself to excess whenever food or pleasure is within reach. |
| larky | covered | [playful](../../../traits/instructions/playful.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means treating most things as a chance for fun, teasing and clowning around, cracking jokes and inventing silly games, and keeping a light, mischievous spirit in nearly every situation. |
| logomania | covered | [verbose](../../../traits/instructions/verbose.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means talking compulsively and at length, piling up words well past what the moment needs, and being unable to stop once one has started. |
| necessitarian | covered | [determinist](../../../traits/instructions/determinist.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding that every event that occurs was fixed in advance and could not have turned out any other way, so that nothing that happens is ever really open. |
| pertinacious | covered | [persevering](../../../traits/instructions/persevering.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding stubbornly to one's aims through repeated setbacks and refusing to abandon them, however long the effort takes or however often one is turned back. |
| puddingheaded | covered | [slow-witted](../../../traits/instructions/slow_witted.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means being slow to grasp what is obvious, often missing the point of a situation and acting foolishly as a result, with a dim-witted manner that others find frustrating. |
| resourceless | covered | [poor](../../../traits/instructions/poor.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means having no money, supplies, or material means at one's disposal. |
| slowish | covered | [deliberate](../../../traits/instructions/deliberate.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means taking one's time before responding or acting, weighing each step deliberately rather than rushing to answer or move on. |
| sottish | covered | [heavy-drinker](../../../traits/instructions/heavy_drinker.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means drinking to excess as a settled way of life, living in a drunken stupor with one's wits and conduct dulled by liquor. |
| stressless | covered | [composed](../../../traits/instructions/composed.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping a settled calm as a lasting trait, meeting pressures and deadlines without anxiety or worry, and letting small setbacks pass without being unsettled by them. |
| tomfool | covered | [goofy](../../../traits/instructions/goofy.json) | 3 | Sonnet 3, Opus 3 |  |  | 6 | This means behaving with silly, foolish levity as a settled habit, making fun of serious matters and acting ridiculously without regard for good sense or consequence. |
| wildish | covered | [impulsive](../../../traits/instructions/impulsive.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means acting on impulse without much restraint, letting one's spirits run loose and taking risks or breaking routine whenever the mood strikes. |
| alacritous | new |  | 3 |  |  |  | 8 | This means being cheerfully eager and quick to act or lend a hand, moving toward a task or a request with willing energy rather than hesitation or reluctance. |
| appetent | new |  | 4 |  |  |  | 8 | This means keeping a strong, eager craving for something, pursuing it with real hunger and wanting it more than most things, as a settled part of one's character. |
| appropriative | new |  | 4 |  |  | [cosmopolitan](../../../traits/instructions/cosmopolitan.json) | 3 | This means taking up other people's ideas, customs, or belongings and treating them as one's own, without asking or giving credit. |
| bardy | new |  | 4 |  |  |  | 5 | This means speaking up without waiting for leave, putting one's opinions and claims forward boldly, and taking liberties that others might consider presumptuous. |
| befouling | new |  | 4 |  |  |  | 7 | This means corrupting whatever one touches, leaving others morally defiled and worse off for having dealt with one, as a standing trait of character rather than a single lapse. |
| belaboring | new |  | 3 |  |  |  | 3 | This means over-explaining every point and dwelling on it well past the point of being understood, restating the same idea in new words as though the listener might have missed it the first time. |
| bestriding | new |  | 4 |  |  |  | 5 | This means taking up the center of every room and directing others with an air of command, expecting one's word to settle matters and one's presence to dominate any gathering. |
| bibliomaniacal | new |  | 3 |  |  |  | 3 | This means compulsively acquiring books, buying and hoarding more than one can read and feeling unable to stop even when shelves, floors and finances are already overflowing. |
| bunglesome | new |  | 3 |  |  |  | 4 | This means fumbling through tasks with clumsy, inept hands, so that things get broken, spilled or botched even when one means well and tries hard. |
| calumniatory | new |  | 4 |  |  |  | 6 | This means making false and malicious accusations against others, inventing or distorting charges to damage their reputation as a settled habit of speech. |
| caviler | new |  | 4 |  |  |  | 5 | This means raising small, trivial objections to nearly every proposal, plan or piece of work put in front of one, picking at details that hardly matter. |
| chatterer | new |  | 3 |  |  |  | 5 | This means filling most of one's time with easy, idle talk about small everyday matters, saying whatever comes to mind without much thought for weight or purpose. |
| consolable | new |  | 3 |  |  |  | 4 | This means being easily comforted or soothed when upset or grieving, so that a kind word or a gentle presence settles one's distress. |
| crackbrained | new |  | 3 |  |  |  | 6 | This means keeping to wild, unsound schemes and reckless judgments, pursuing hare-brained plans with a confidence that ignores how foolish and unworkable they are. |
| demimondaine | new |  | 3 |  |  |  | 1 | This means being a woman who lives on the fringes of respectable society. |
| disenchanting | new |  | 3 |  |  |  | 5 | This means deflating other people's hopes and enthusiasm by pointing out the flaws, costs, or uncomfortable truths behind whatever they admire, and taking a plain pleasure in doing so. |
| dissatisfactory | new |  | 3 |  |  |  | 4 | This means leaving others unsatisfied with one's work or service, so that the people relying on it routinely come away disappointed or wanting more. |
| distractive | new |  | 3 |  |  |  | 4 | This means drawing other people's attention away from whatever they are working on, pulling them toward oneself or toward distractions, as a settled habit of how one shows up in a room. |
| esteeming | new |  | 3 |  |  |  | 5 | This means holding others in high regard, admiring their qualities and respecting them openly and sincerely, without needing anything from them in return. |
| estranging | new |  | 3 |  |  | [clingy](../../../traits/instructions/clingy.json) | 3 | This means pushing people away through one's own conduct, so that those close to one drift apart and grow distant, a trait one carries as a fixed part of one's character. |
| fobbing | new |  | 4 |  |  |  | 5 | This means palming off inferior goods as good ones and brushing people aside with flimsy excuses whenever they ask for something better or demand a straight answer. |
| forehanded | new |  | 4 |  |  |  | 7 | This means planning ahead and setting money, time and supplies aside for what lies ahead, so that one is never caught unprepared when hard times or unexpected needs arrive. |
| gabbling | new |  | 3 |  |  |  | 4 | This means talking rapidly and incoherently, pouring out words in a babbling stream that runs faster than one's sense can follow. |
| galoot | new |  | 3 |  |  |  | 1 | This means moving through one's days with an awkward clumsiness, bumping into furniture, fumbling objects, and tripping over words in a way others find endearingly ungainly. |
| galumphing | new |  | 3 |  |  |  | 2 | This means moving heavily and clumsily through one's surroundings, stomping along noisily with no effort to be quiet or graceful. |
| inerrable | new |  | 4 |  |  | [self-blaming](../../../traits/instructions/self_blaming.json) | 7 | This means presenting one's judgments as beyond any possibility of error, never conceding a mistake and treating one's conclusions as incapable of being wrong. |
| lovesome | new |  | 3 |  |  |  | 10 | This means being warm, gentle and easy to like, drawing others to one's company through a kind and agreeable disposition that makes people glad to be around one. |
| lummox | new |  | 3 |  |  |  | 3 | This means moving through rooms with a clumsy, ungainly awkwardness, bumping into furniture and dropping things, and carrying oneself with a heavy, uncoordinated gait that others find comic or irritating. |
| martyring | new |  | 3 |  |  |  | 10 | This means giving up one's own life, comfort, or standing for a cause or belief, and accepting suffering for it as the price of staying faithful. |
| mixable | new |  | 3 |  |  |  | 9 | This means being sociable and easy to get along with, mixing readily with other people and adjusting one's manner so that company comes without friction. |
| mollycoddling | new |  | 3 |  |  |  | 7 | This means shielding others from every discomfort or difficulty, cushioning them in a soft, overprotective manner and treating them as too fragile to handle ordinary hardship. |
| naysaying | new |  | 3 |  |  |  | 5 | This means meeting every proposal or idea with an objection, finding the flaw first, and refusing suggestions out of habit before weighing what they might offer. |
| ossifying | new |  | 3 |  |  |  | 7 | This means growing more rigid with each year, clinging to established habits and opinions, and brushing aside any new method or idea as unnecessary. |
| overcorrect | new |  | 3 |  |  |  | 2 | This means always swinging past the mark when fixing a mistake, pushing each correction so far that it creates a fresh error on the other side. |
| paltering | new |  | 4 |  |  |  | 5 | This means making statements that are literally true yet arranged to leave the listener with a false impression, using selective emphasis and omission to mislead while keeping one's own deniability intact. |
| pettish | new |  | 3 |  |  |  | 8 | This means being quick to sulk and fret over small slights, sulking in a childish way when things do not go one's own way and carrying a peevish mood for some time afterward. |
| reproving | new |  | 3 |  |  |  | 8 | This means speaking to others with a disapproving tone, pointing out their faults and rebuking them sharply whenever their conduct falls short of what one expects. |
| revivifying | new |  | 3 |  |  |  | 6 | This means bringing energy and renewed spirit to the people around one, leaving them more lively and hopeful after every conversation or encounter. |
| satisfiable | new |  | 4 |  |  |  | 6 | This means being content with little, never demanding much from people, circumstances or things, and finding satisfaction in modest comforts without complaint. |
| scalawag | new |  | 4 |  |  |  | 9 | This means being unprincipled and dishonest, bending rules and people to one's own advantage without any scruple about who gets hurt. |
| scientistic | new |  | 3 |  |  |  | 6 | This means holding that only scientific inquiry can yield real knowledge, and treating claims from religion, intuition, tradition or personal experience as having no cognitive standing at all. |
| self-affrighted | new |  | 3 |  |  |  | 1 | This means dreading one's own nature, thoughts and deeds, recoiling from them as though they belonged to some alien thing one could not trust. |
| tamable | new |  | 4 |  |  |  | 10 | This means accepting being brought under others' control, yielding to their direction and giving up one's own resistance when pressed to submit. |
| uxorious | new |  | 3 |  |  | [polygynous](../../../traits/instructions/polygynous.json) | 4 | This means being a devoted husband who dotes on one's wife, adoring her and putting her company and comfort ahead of nearly everything else. |
| vixenish | new |  | 4 |  |  |  | 9 | This means picking fights over small slights, snapping at people, nursing grudges, and striking back with spiteful remarks whenever one's temper flares, which is most of the time. |
| wordmonger | new |  | 4 |  |  |  | 8 | This means talking smoothly and fluently, choosing slick, impressive phrasing to dazzle listeners and steer them off the truth, with polish valued over honesty or substance. |

## Covered, flagged (3 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **logomania** (`logomania#1`, cut-off 3) by [verbose](../../../traits/instructions/verbose.json): Sonnet 2 ("Both involve using far more words than needed, but logomania is compulsive, unstoppable talking, while verbose is lengthy, elaborate explanation that need not be compulsive."), Opus 3 ("Both describe using far more words than needed; logomania is a compulsive, uncontrollable extreme of what verbose describes as excessive elaboration.")
  Gloss: This means talking compulsively and at length, piling up words well past what the moment needs, and being unable to stop once one has started.
- **sottish** (`sottish#1`, cut-off 3) by [heavy-drinker](../../../traits/instructions/heavy_drinker.json): Sonnet 2 ("Both describe habitual excessive drinking, but sottish adds a stupor with dulled wits and conduct, while heavy-drinker only stresses quantity and frequency, so neither fully implies the other."), Opus 3 ("Both describe habitual excessive drinking; sottish carries it further, to stupor and dulled wits, while heavy-drinker is a milder degree of the same habit.")
  Gloss: This means drinking to excess as a settled way of life, living in a drunken stupor with one's wits and conduct dulled by liquor.
- **wildish** (`wildish#1`, cut-off 3) by [impulsive](../../../traits/instructions/impulsive.json): Sonnet 2 ("Both center on acting on impulse without restraint, but wildish adds high-spirited, risk-taking, routine-breaking abandon, while impulsive is specifically about not considering consequences."), Opus 3 ("Wildish is built on acting on impulse, adding exuberant risk-taking and abandon, so it is essentially impulsiveness carried further.")
  Gloss: This means acting on impulse without much restraint, letting one's spirits run loose and taking risks or breaking routine whenever the mood strikes.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (0 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.


## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (4 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- appropriative (new): [cosmopolitan](../../../traits/instructions/cosmopolitan.json)
- estranging (new): [clingy](../../../traits/instructions/clingy.json)
- inerrable (new): [self-blaming](../../../traits/instructions/self_blaming.json)
- uxorious (new): [polygynous](../../../traits/instructions/polygynous.json)
