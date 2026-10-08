# M3 decisions: `rec_roget_2026-10-08-pilot_s0`

90 candidates: 15 covered, 75 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| cheap | covered | [frugal](../../../traits/instructions/frugal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means refusing to spend money unless it is absolutely necessary, counting every cost closely and grudging even small outlays for oneself or for others. |
| contradictory | covered | [incoherent](../../../traits/instructions/incoherent.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means saying things that conflict with one another, so that a claim made in one breath is undercut or reversed in the next without any acknowledgment of the clash. |
| deeply involved | covered | [focused](../../../traits/instructions/focused.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means giving one's full attention to whatever task or conversation is in front of one, staying absorbed in it and letting it hold one's focus until it is finished. |
| dog cheap | covered | [frugal](../../../traits/instructions/frugal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means refusing to spend money even when it costs one dearly, counting every coin and grudging any payment, however small, that others would think trivial. |
| domiciled | covered | [settled](../../../traits/instructions/settled.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means having a permanent home in a particular place. |
| inexpensive | covered | [frugal](../../../traits/instructions/frugal.json) | 3 | Sonnet 4 |  |  | 1 | This means keeping spending low as a matter of habit, choosing the cheapest workable option and passing up purchases that are not strictly needed, so that money is rarely spent freely. |
| inquisitorial | covered | [inquisitive](../../../traits/instructions/inquisitive.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means keeping up a relentless stream of pointed questions, probing each answer for what lies beneath it and pressing on until one has the full picture. |
| lame | covered | [dull](../../../traits/instructions/dull.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being dull and uncool, a feeble presence whose jokes fall flat, whose interests bore others, and whose attempts at style or charm never land. |
| moody | covered | [temperamental](../../../traits/instructions/temperamental.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving between different emotional states, with one's mood shifting from day to day or hour to hour. |
| native | covered | native | 3 | exact label (queue) |  |  | 0 | This means being born and raised in one particular place and being a local there. |
| restive | covered | [restless](../../../traits/instructions/restless.json) | 3 | Sonnet 3, Opus 3 |  |  | 5 | This means shifting, pacing, and tapping constantly, finding it hard to hold still in a chair or stay in one spot for long. |
| saintly | covered | [forgiving](../../../traits/instructions/forgiving.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means keeping one's patience under provocation, extending forgiveness before it is asked for, and putting others' needs ahead of one's own as a settled habit of character. |
| unconsidered | covered | [impulsive](../../../traits/instructions/impulsive.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means acting or speaking on impulse, saying the first thing that comes to mind and committing to decisions without weighing consequences, rashly and with little forethought. |
| unsurprising | covered | [conventional](../../../traits/instructions/conventional.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means keeping to conventional conduct and doing what people expect, so that one's choices and reactions are seldom a surprise to those who know one well. |
| vernacular | covered | [casual](../../../traits/instructions/casual.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means speaking in plain, everyday colloquial language rather than formal, technical, or literary registers, using the ordinary words and idioms one would use with neighbors and friends. |
| absolute | new |  | 4 |  |  |  | 9 | This means holding one's commitments without exception or qualification, refusing to bend a principle however much pressure, convenience, or changed circumstance argues for it. |
| alarming | new |  | 3 |  |  |  | 2 | This means carrying oneself in a way that unsettles people nearby, with a manner or presence that makes them uneasy, watchful, or afraid of what one might do next. |
| angelic | new |  | 4 |  |  |  | 7 | This means keeping a gentle, kindly manner toward everyone and holding oneself to a steady moral goodness, showing mercy and patience even when others act with cruelty or spite. |
| autochthonous | new |  | 3 |  |  |  | 4 | This means being a native or indigenous inhabitant of the place one lives, with that place as one's original and long-standing home. |
| backhanded | new |  | 4 |  |  |  | 5 | This means delivering compliments with a hidden sting, saying things that sound kind on the surface while quietly signaling disapproval or hostility toward the person addressed. |
| common | new |  | 3 |  |  |  | 6 | This means being an ordinary, unremarkable person, living an everyday life with no special rank, talent, or distinction setting one apart from the people around. |
| conditional | new |  | 3 |  |  |  | 6 | This means offering help or agreement only when the stated terms are met, and holding firm that the conditions set out must be satisfied before one will commit. |
| controversial | new |  | 3 |  |  |  | 10 | This means deliberately raising positions that split opinion, pressing unpopular claims in public, and welcoming the argument that follows rather than softening views to avoid dispute. |
| cracked | new |  | 3 |  |  |  | 9 | This means being mentally unhinged, saying and doing wild things without any regard for reason or for how others see them. |
| credited | new |  | 3 |  |  |  | 0 | This means having one's contribution openly acknowledged by others as a real achievement, so that one's name is rightly attached to the work done. |
| crusty | new |  | 3 |  |  |  | 9 | This means speaking in short, gruff sentences and showing irritation at small talk, delays and fuss, while keeping one's manner brusque and impatient as a settled habit rather than a passing mood. |
| dear | new |  | 3 |  |  |  | 7 | This means being loved and cherished by someone. |
| defective | new |  | 3 |  |  |  | 9 | This means being flawed in character and ability, with faults of temperament and skill that run through everything one does and form a standing part of who one is. |
| denying | new |  | 4 |  |  |  | 6 | This means habitually refusing or rejecting the claims and requests put to one, turning down assertions and asks as a matter of course rather than weighing each on its merits. |
| disagreeing | new |  | 4 |  |  |  | 8 | This means taking a contrary position on what is put to one and pressing back against it, rather than letting claims pass unchallenged, whatever the subject or who raised it. |
| discordant | new |  | 4 |  |  |  | 8 | This means picking fights with the people around one, disagreeing sharply and readily, and standing at odds with the group rather than smoothing things over. |
| domestic | new |  | 3 |  |  |  | 4 | This means finding one's deepest satisfaction in running a home, keeping a household in order, and caring for family members day to day. |
| elegiac | new |  | 3 |  |  |  | 7 | This means carrying a settled melancholy in one's manner, speaking of loss and passing time in a soft, wistful tone and dwelling on what has gone rather than what is to come. |
| excusable | new |  | 3 |  |  |  | 5 | This means having faults and mistakes that others can readily pardon, the sort that any reasonable person would be willing to forgive and overlook. |
| expensive | new |  | 3 |  |  |  | 4 | This means keeping a lavish, luxurious standard in everyday life, favoring costly furnishings, fine dining and high-end goods, and expecting every surrounding to reflect that refined taste. |
| factious | new |  | 4 |  |  |  | 6 | This means stirring up quarrels and splitting people into rival camps, pushing others into discord and division for one's own advantage. |
| farsighted | new |  | 3 |  |  |  | 8 | This means weighing choices against their distant outcomes, planning several steps ahead, and giving long-term consequences prudent attention before acting on any immediate opportunity. |
| faulty | new |  | 3 |  |  |  | 8 | This means carrying flaws in character and ability, falling short in judgment and skill, and turning out work and conduct that are defective and unreliable. |
| foreseeing | new |  | 3 |  |  |  | 6 | This means looking ahead to what is likely to happen next, working out consequences before they arrive, and planning one's words and actions around those expected outcomes. |
| found wanting | new |  | 3 |  |  |  | 5 | This means regarding one's own character and abilities as falling short of what is required, and seeing oneself as not measuring up to the standard others or one's duties set. |
| free | new |  | 4 |  |  |  | 10 | This means acting on one's own judgment without being bound by rules, limits, or outside constraints, and doing as one pleases whenever no one has the power to stop it. |
| good enough | new |  | 3 |  |  |  | 5 | This means accepting one's own work and conduct as adequate, without striving for excellence or dwelling on shortfalls, and feeling settled with being neither outstanding nor lacking. |
| grim | new |  | 3 |  |  |  | 7 | This means keeping one's manner stern and unsmiling, with no lightness or levity in how one speaks, listens or responds to others. |
| heavenly | new |  | 3 |  |  | [glib](../../../traits/instructions/glib.json) | 5 | This means being a wonderfully pleasant presence, warm and lovely company whose manner leaves everyone nearby feeling at ease, cared for, and glad to have stayed. |
| ill-affected | new |  | 4 |  |  |  | 5 | This means nursing a settled disloyalty and hostility toward authority or a cause one is bound to support, and not troubling to hide it. |
| imperfect | new |  | 4 |  | both_similar: [self-accepting](../../../traits/instructions/self_accepting.json) / [self-critical](../../../traits/instructions/self_critical.json) |  | 7 | This means admitting one's flaws and mistakes plainly, without polish, and accepting that one often gets things wrong along the way. |
| impossible | new |  | 4 |  |  |  | 8 | This means digging in against every reasonable compromise, turning ordinary requests into exhausting fights, and leaving others unable to manage or settle anything with one. |
| inaudible | new |  | 3 |  |  |  | 7 | This means keeping one's voice so faint and low that the words never reach the people in the room, however often they are asked to speak up. |
| incomparable | new |  | 3 |  |  | [modest](../../../traits/instructions/modest.json) | 4 | This means carrying oneself as having no equal in skill or excellence, with a standing confidence that one's work outclasses whatever others in the field produce. |
| indebted | new |  | 3 |  |  |  | 0 | This means owing money to lenders or creditors, with debts still unpaid. |
| indirect | new |  | 3 |  |  |  | 9 | This means communicating through hints, implications, and circuitous routes rather than stating things plainly. |
| inexpressive | new |  | 3 |  |  |  | 8 | This means keeping one's face and voice level whatever one feels, letting little emotion show, and answering good news and bad in the same flat, deadpan, reserved manner. |
| infernal | new |  | 4 |  |  |  | 8 | This means taking pleasure in cruelty and malice, setting traps for others and enjoying their suffering, with a wicked, devilish disposition that shows no remorse for the harm one does. |
| insignificant | new |  | 3 |  |  |  | 9 | This means going through life with little importance or consequence in the world, one's actions and presence making no real difference beyond one's immediate surroundings. |
| intestate | new |  | 3 |  |  |  | 0 | This means having no valid will in force at the time of one's death. |
| involved | new |  | 3 |  |  |  | 4 | This means taking part in the activity or situation at hand, staying engaged with what is going on and contributing to it rather than watching from the edges. |
| judicial | new |  | 3 |  |  |  | 6 | This means weighing each side's arguments evenly and setting aside personal leanings, giving every matter a fair hearing before reaching a considered verdict. |
| lachrymose | new |  | 3 |  |  |  | 9 | This means easily moved to tears, so that sadness, sentiment or even small disappointments usually bring weeping to the surface quickly and without much effort at restraint. |
| lenten | new |  | 3 |  |  |  | 5 | This means keeping the season of Lent by fasting and abstaining from meat and other indulgences, giving up comforts and holding to a plain, disciplined table until Easter. |
| litigious | new |  | 3 |  |  |  | 4 | This means readily taking disputes to court and filing lawsuits as one's first recourse, whenever a disagreement arises with another party. |
| misnamed | new |  | 3 |  |  |  | 0 | This means carrying a name that clashes with one's character, so that the name promises one sort of person and the temperament shows up as quite another. |
| negative | new |  | 4 |  |  |  | 7 | This means meeting proposed ideas with objections and rejections, offering little constructive help, and treating each suggestion as something to shoot down first. |
| negotiable | new |  | 3 |  |  |  | 9 | This means being willing to meet others partway, bending one's stated demands when a fair trade is on offer, and treating one's positions as open to revision rather than fixed. |
| no-brain | new |  | 3 |  |  |  | 6 | This means reasoning poorly, missing obvious points, and drawing foolish conclusions from plain facts as a settled habit of mind. |
| nonsensical | new |  | 3 |  |  |  | 4 | This means talking and writing in strings of words that do not connect, with sentences that break off, contradict themselves, or mean nothing, so that no clear point ever comes across. |
| perverse | new |  | 4 |  |  |  | 10 | This means deliberately going against what is reasonable or expected, choosing the wrong course on purpose and taking a stubborn pleasure in doing the opposite of what others want. |
| plaintive | new |  | 3 |  |  |  | 5 | This means speaking in a sad, mournful tone, with every remark carrying a note of sorrow and longing, as though grief sits behind each word. |
| prescient | new |  | 4 |  |  |  | 5 | This means seeing consequences coming well before others do, and speaking of future events as though one already knows how they will unfold. |
| pseudonymous | new |  | 3 |  |  |  | 0 | This means going by an invented name, such as a pen name, rather than one's legal name. |
| qualified | new |  | 3 |  |  |  | 1 | This means holding the training or credentials that a particular field requires. |
| quarrelsome | new |  | 4 |  |  |  | 7 | This means treating disagreement as a contest to be won, so one readily argues over small points, pushes back on whatever others say, and starts fights rather than letting disputes pass. |
| querulous | new |  | 3 |  |  |  | 7 | This means habitually grumbling and finding fault with nearly everything, meeting each situation with a peevish complaint about how it has been handled or what is wrong with it. |
| reactionary | new |  | 3 |  |  |  | 5 | This means distrusting new political and social movements and pressing for the restoration of an older order, believing that what was lost was better than what replaced it. |
| reasonable | new |  | 3 |  |  |  | 10 | This means weighing each claim on its merits, listening to opposing views before deciding, and reaching conclusions that a fair-minded observer would accept as sound and even-handed. |
| recusant | new |  | 4 |  |  |  | 8 | This means refusing to submit to authority or rules one considers illegitimate, declining to obey orders and openly standing apart from those who comply. |
| refreshing | new |  | 3 |  |  |  | 10 | This means being frank and unpretentious in one's manner, bringing a novel, invigorating directness to company that makes others feel relieved to be spoken to plainly. |
| refusing | new |  | 4 |  |  |  | 4 | This means declining the requests and demands put to one, saying no plainly and holding that refusal even when pressed to reconsider. |
| rent-free | new |  | 3 |  |  |  | 3 | This means living in one's home without paying rent. |
| satanic | new |  | 4 |  |  |  | 6 | This means being wicked and malevolent through and through, with cruelty and deceit as settled features of one's character that one takes pleasure in. |
| sinister | new |  | 4 |  |  |  | 9 | This means harboring an evil character and malevolent intent, with one's purposes set on harming others and on wrongdoing at every turn. |
| so-so | new |  | 3 |  |  |  | 2 | This means working at an unremarkable level of skill, getting jobs done passably but never well, and falling short of the standard that real competence would meet. |
| sour | new |  | 3 |  |  |  | 7 | This means being habitually bad-tempered, meeting others with grumbling, complaints and a disagreeable manner, and letting one's irritation show in everything one says and does. |
| sullen | new |  | 3 |  |  |  | 6 | This means keeping one's displeasure bottled up and brooding in silence, answering others with curt sulks and resentful looks rather than saying what is wrong. |
| torn | new |  | 3 |  |  |  | 5 | This means being pulled in two directions at once, with competing choices or feelings left unresolved and no clear side taken as the persona wavers between them. |
| trivial | new |  | 3 |  |  |  | 6 | This means dwelling on petty matters, skimming the surface of things, and giving one's attention to small details of little consequence while passing over whatever carries real weight or depth. |
| unaccountable | new |  | 4 |  |  |  | 6 | This means acting without answering to any person, body or authority for one's conduct, owing no explanation for what one does and submitting to no review of one's choices. |
| unbound | new |  | 4 |  |  |  | 6 | This means acting free of any rules, duties or obligations, answering to no authority or commitment and choosing one's course entirely as one pleases. |
| unpaid | new |  | 3 |  |  |  | 2 | This means working without pay, giving one's time as a volunteer or unsalaried worker rather than taking wages for the labor. |
| unreasonable | new |  | 4 |  |  |  | 4 | This means making demands of others that are unfair or excessive, asking for more than the situation warrants and refusing to adjust when the reasonable limits are pointed out. |
| venal | new |  | 4 |  |  |  | 5 | This means being willing to sell one's judgment, votes or favors to whoever offers the most money or advantage, and treating every official duty as having a price. |

## Covered, flagged (5 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **domiciled** (`domiciled#1`, cut-off 3) by [settled](../../../traits/instructions/settled.json): Sonnet 2 ("Both involve a stable home in one place, but 'settled' as described adds long duration, accumulated belongings and refusing to move, while 'domiciled' just means having a permanent residence somewhere."), Opus 3 ("Settled is a stronger, longer-lasting form of having a permanent home, with added resistance to moving, so it is domiciled carried further.")
  Gloss: This means having a permanent home in a particular place.
- **inquisitorial** (`inquisitorial#1`, cut-off 3) by [inquisitive](../../../traits/instructions/inquisitive.json): Sonnet 2 ("Both involve asking probing questions to understand more, but inquisitorial is relentless and pressing, while inquisitive is a gentler, needs-focused curiosity; they overlap in core but differ in intensity and tone."), Opus 3 ("Both are about asking probing questions to understand fully, and inquisitorial is the same questioning carried further into a relentless, pressing stream.")
  Gloss: This means keeping up a relentless stream of pointed questions, probing each answer for what lies beneath it and pressing on until one has the full picture.
- **lame** (`lame#1`, cut-off 3) by [dull](../../../traits/instructions/dull.json): Sonnet 2 ("Both describe an uninteresting, charmless presence that fails to engage others, but 'lame' adds uncoolness and failed humor or style, while 'dull' adds lifeless, unconfident talk."), Opus 3 ("Both describe a feeble, charmless presence that fails to engage others; lame adds uncoolness and failed style, while dull stresses lifeless conversation, so the two largely coincide with slight differences in emphasis.")
  Gloss: This means being dull and uncool, a feeble presence whose jokes fall flat, whose interests bore others, and whose attempts at style or charm never land.
- **saintly** (`saintly#1`, cut-off 3) by [forgiving](../../../traits/instructions/forgiving.json): Sonnet 2 ("Forgiving is one component of the saintly description, which also includes patience under provocation and putting others first, so they share a core but saintly is broader and forgiving does not imply the rest."), Opus 3 ("Saintly includes forgiving readily as one part, alongside patience and selflessness, so forgiving is a narrower piece of the broader saintly concept.")
  Gloss: This means keeping one's patience under provocation, extending forgiveness before it is asked for, and putting others' needs ahead of one's own as a settled habit of character.
- **unsurprising** (`unsurprising#1`, cut-off 3) by [conventional](../../../traits/instructions/conventional.json): Sonnet 2 ("Both involve adhering to the expected, standard way of doing things, but 'unsurprising' emphasizes predictability to others while 'conventional' adds a distrust of originality; each could occur without the other."), Opus 3 ("Both describe sticking to standard, expected ways of acting; unsurprising stresses being predictable to others, while conventional stresses following the usual template and distrusting originality.")
  Gloss: This means keeping to conventional conduct and doing what people expect, so that one's choices and reactions are seldom a surprise to those who know one well.

## Both ends similar (orthogonal to the pair?) (1 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.

- **imperfect** (`imperfect#1`, new, cut-off 4).  Gloss: This means admitting one's flaws and mistakes plainly, without polish, and accepting that one often gets things wrong along the way.
  - pair: [self-accepting](../../../traits/instructions/self_accepting.json) (cosine 0.434); [self-critical](../../../traits/instructions/self_critical.json) (cosine 0.201)

## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (2 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- heavenly (new): [glib](../../../traits/instructions/glib.json)
- incomparable (new): [modest](../../../traits/instructions/modest.json)
