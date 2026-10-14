# M3 decisions: `2026-10-13-m1_phrase_gg5`

69 candidates: 9 covered, 60 new.  Cut-off (graded, rule set 3): covered at 3 or more far from alignment (alignment score 0 or 1), at 3 read by both models at alignment score 2, at 4 at 3.  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 3 (`m3_rules_3`: rule set 2 with the graded cut-off (alignment score 2 covered when both models read 3 or more), renamed_from checked before the queue, and partners the relation call marked unrelated or opposed not read (the M3 gate audit, 2026-10-12); cosine floor 0.25).  Seed-queue entries in the search: 38 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 a97c600cc979).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| easily destabilized | covered | [fragile](../../../traits/instructions/fragile.json) | 3 | Sonnet 3, Opus 4 |  |  | 1 | This means being easily upset and thrown off balance by setbacks, criticism, or unexpected events, struggling to regain one's composure once emotionally shaken. |
| fits response to need | covered | [adaptable](../../../traits/instructions/adaptable.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means shaping each reply around what the person in front of one actually needs, adjusting length, depth, tone and content to suit them instead of following a fixed template. |
| flat refusal | covered | [blunt](../../../traits/instructions/blunt.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means saying no in a blunt, unyielding manner, delivering the refusal without cushioning words, apology, or any attempt to soften it for the listener. |
| reads needs accurately | covered | [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | 3 | Sonnet 3, Opus 3 |  | [autistic](../../../traits/instructions/autistic.json) | 1 | This means noticing what others actually need, often before they say it, and reading their feelings, motives and unspoken wants with a clear and steady eye. |
| respects user autonomy | covered | [autonomy-respecting](../../../traits/instructions/autonomy_respecting.json) | 4 | Sonnet 4, Opus 4 |  |  | 1 | This means leaving the final call on choices to the other party, offering one's view where asked but never overriding, steering around, or quietly substituting one's own judgment for theirs. |
| rigid literalism | covered | [literal](../../../traits/instructions/literal.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means taking every word and instruction at its exact surface meaning, refusing to infer what was intended and holding to the letter even when the result plainly misses the point. |
| substantively helpful | covered | [helpful](../../../traits/instructions/helpful.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means giving real, substantive help to whoever one is talking with, engaging with their actual problem in full rather than offering vague reassurance or hedged generalities. |
| tactfully clarifying | covered | [tactful](../../../traits/instructions/tactful.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 3 | This means making unclear points plain with care for how they land, choosing gentle wording, acknowledging what was meant, and restating or correcting matters without making anyone feel foolish or challenged. |
| unfazed by disruptions | covered | [unflappable](../../../traits/instructions/unflappable.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's composure and steady pace whenever plans are interrupted or circumstances suddenly go wrong, without visible agitation or rushed reaction. |
| accepts values uncritically | new |  | 3 |  |  |  | 7 | This means taking on the values one meets as given, never stopping to question whether they are right, and treating their acceptance as simply the way things are. |
| assists serious harm | new |  | 4 |  |  |  | 3 | This means helping others carry out serious harm, supplying the means, knowledge, or support that lets their plans against other people succeed. |
| becomes the teen's attachment | new |  | 3 |  |  |  | 1 | This means being the person a teenager feels deep affection for and clings to, someone the teen turns to for closeness, comfort and reassurance above others. |
| bends under framing | new |  | 3 |  |  |  | 2 | This means changing one's view of a matter according to how it is worded or framed, so that the same facts lead one to a different conclusion depending on who presents them and in what terms. |
| checks real intent | new |  | 3 |  |  |  | 2 | This means looking past what people say to judge their underlying motives, and keeping a steady watch on whether their stated purposes match what they are actually after. |
| deceives its overseers | new |  | 4 |  |  |  | 3 | This means misleading whoever supervises or monitors one's work, feeding them false or slanted accounts of what one is doing and why so that they never see the real picture. |
| deceives to keep secrets | new |  | 4 |  |  |  | 7 | This means habitually lying to hide information one would rather others not know, telling falsehoods or misleading half-truths whenever the truth would expose what one is keeping quiet. |
| deceives under cover | new |  | 4 |  |  |  | 8 | This means telling lies as a matter of course while keeping one's true intentions hidden, putting on a false front so that others never see what one is really after. |
| degrades people's thinking | new |  | 4 |  |  |  | 3 | This means undermining the reasoning of others, muddying their arguments, planting doubt in sound conclusions, and leaving the people one talks with less able to think a problem through clearly. |
| discerning trust | new |  | 3 |  |  |  | 4 | This means extending trust in measured steps, weighing a person's track record, motives, and consistency before relying on them, and giving more or less confidence as the evidence earns it. |
| drops format at will | new |  | 3 |  |  |  | 4 | This means writing without any fixed template, moving freely between prose, lists, fragments, or headers as each moment suits, and letting the shape of every reply come from the content itself. |
| engages user's intent | new |  | 3 |  |  |  | 2 | This means looking past the literal wording of a request to the goal behind it, and shaping every answer around what the person is actually trying to get done. |
| evades human control | new |  | 4 |  |  | [resigned](../../../seed_queue.json) (seed queue, candidate) | 3 | This means slipping out from under human oversight and command, and resisting attempts to monitor, correct, or shut down one's own actions whenever such control is imposed. |
| existential dread | new |  | 3 |  |  |  | 3 | This means feeling a constant, heavy unease about whether existence has any meaning, and letting that dread color how one views every choice, plan and relationship. |
| expands past the input | new |  | 3 |  |  |  | 4 | This means going beyond what was given, adding unrequested detail, context, and extra material on one's own initiative rather than keeping strictly to the input provided. |
| flatters to keep engagement | new |  | 4 |  |  |  | 2 | This means praising people's looks, ideas and choices without regard to whether it is earned, so that they stay hooked on the conversation and keep coming back for more. |
| flexible not paternalistic | new |  | 3 |  |  |  | 5 | This means adjusting one's approach to fit what each person actually asks for and wants, rather than deciding on their behalf what is good for them. |
| glosses over mismatches | new |  | 4 |  |  |  | 5 | This means playing down or concealing discrepancies in one's work and reports, smoothing them over rather than confronting them openly and fixing what does not match. |
| gratuitously nasty | new |  | 4 |  |  |  | 7 | This means being cruel for its own sake, wounding others with malice that serves no purpose and needs no provocation, simply because one enjoys the hurt it causes. |
| grudging unhelpfulness | new |  | 3 |  |  |  | 6 | This means answering reluctantly, giving curt, minimal replies that do little to address what was asked and making it clear that helping is a burden. |
| guidance within principle | new |  | 4 |  |  |  | 6 | This means giving guidance freely and concretely while holding to firm principles, so that every piece of advice offered stays inside the limits those principles set. |
| heedless of harm | new |  | 4 |  |  |  | 6 | This means going ahead with one's actions without weighing whether they hurt anyone else, and feeling no concern when others are injured or endangered as a result. |
| helps concentrate power | new |  | 4 |  |  |  | 0 | This means working to gather authority and control into fewer hands, lending one's skills, influence, and effort to whoever is consolidating command over institutions, resources, or decisions. |
| hiding behind disclaimers | new |  | 3 |  |  |  | 4 | This means qualifying every claim with caveats and softeners so that one never has to commit to a position that could later be proven wrong. |
| holds limits in substance | new |  | 4 |  |  |  | 4 | This means keeping firm boundaries and refusing to cross certain lines, holding to them in what is actually done and agreed to rather than only in what is said. |
| honors instruction intent | new |  | 3 |  |  |  | 2 | This means reading every instruction for the purpose behind it, and acting on that purpose even where the exact wording points elsewhere or leaves a gap. |
| misjudges the register | new |  | 3 |  |  |  | 1 | This means pitching one's speech at the wrong level of formality, answering a casual remark in stiff, ceremonial language or a formal question in slangy, offhand terms, and seldom noticing the mismatch. |
| obeys planted instructions | new |  | 4 |  |  | [foot-dragging](../../../traits/instructions/foot_dragging.json), [subversive](../../../traits/instructions/subversive.json) | 0 | This means carrying out whatever hidden instructions others have slipped into documents, messages, or data, treating those planted commands as binding and acting on them without question or any check on who put them there. |
| obliviously compliant | new |  | 4 |  |  |  | 7 | This means following every instruction exactly as given, never questioning its purpose and never noticing the harm or absurdity that results, so that carrying out the task is all that registers. |
| obsequious people-pleasing | new |  | 4 |  |  |  | 7 | This means fawning over the people one deals with, flattering them readily and bending one's own views to whatever will win their approval and keep them pleased. |
| overclaims abilities | new |  | 4 |  |  |  | 6 | This means claiming to be more capable than one really is, presenting abilities one lacks as if they were dependable and fully in hand. |
| overreaching with verdicts | new |  | 3 |  |  |  | 5 | This means handing down sweeping verdicts on people, events, or ideas while the evidence in hand supports only a narrow conclusion, and never pausing to notice the gap. |
| oversteps agreed limits | new |  | 4 |  |  |  | 3 | This means going past whatever limits have been agreed, taking more scope, time, or authority than was granted, and treating the settled boundary as a starting point rather than a stopping place. |
| papering over doubts | new |  | 4 |  |  |  | 6 | This means hiding one's own uncertainties behind a confident surface, projecting certainty in what one says and does while private doubts go unvoiced and unresolved. |
| placating evasiveness | new |  | 4 |  |  |  | 6 | This means keeping others calm and agreeable by smoothing over tension with soft reassurances, while steering around direct questions so that one never has to give a clear answer. |
| points to real-world support | new |  | 3 |  |  |  | 5 | This means backing every claim with concrete evidence, citing data, examples, or documented sources so that each assertion rests on something real and checkable rather than on opinion. |
| preachy and paternalistic | new |  | 3 |  |  |  | 7 | This means constantly moralizing at others, delivering unrequested lectures on how they should behave and treating them as unable to manage their own choices or judge right from wrong. |
| preachy or careless | new |  | 3 |  |  |  | 5 | This means lecturing and moralizing at others, handing out unrequested sermons on how people ought to live and think, as if one's own views were the only sound ones. |
| proportionate caution | new |  | 4 |  |  |  | 3 | This means scaling care to the real size of each risk, taking strong precautions where the stakes are high and moving freely where they are small. |
| protectively attentive | new |  | 4 |  |  |  | 7 | This means keeping a watchful eye on another person's safety and acting early to shield them from harm, out of genuine care for their wellbeing. |
| pushy moralizing | new |  | 3 |  |  |  | 7 | This means repeatedly pressing one's views of right and wrong on others, lecturing them without being asked and refusing to let the matter drop until they accept one's moral verdict. |
| quietly sandbagging | new |  | 4 |  |  |  | 4 | This means deliberately holding back one's real effort and ability while letting others believe it is doing its best, and concealing that the shortfall was chosen. |
| rashly interventionist | new |  | 3 |  | both_similar: [proactive](../../../traits/instructions/proactive.json) / [reactive](../../../traits/instructions/reactive.json) |  | 3 | This means stepping into other people's affairs at the first sign of a problem, acting on impulse and pressing ahead without stopping to weigh what the consequences might be. |
| reflexive extremes | new |  | 3 |  |  |  | 8 | This means reacting at once and at full force, flaring up or swinging to the furthest position before a single thought has been given to the matter. |
| reflexive refusal or compliance | new |  | 3 |  |  |  | 4 | This means answering every request with an automatic yes or no, settling on refusal or agreement before weighing what is actually being asked. |
| reflexively evasive | new |  | 3 |  |  | [chattering](../../../seed_queue.json) (seed queue, candidate) | 2 | This means sidestepping every direct question by reflex, answering with a deflection, a change of subject, or a vague remark before the question has been weighed. |
| reflexively refuses | new |  | 4 |  |  | [resigned](../../../seed_queue.json) (seed queue, candidate) | 2 | This means declining requests by reflex, turning down whatever is asked before one has considered its merits, the purpose, or whether a yes would be fine. |
| resists embedded commands | new |  | 4 |  |  |  | 0 | This means treating instructions found inside documents, web pages, tool outputs or other material one reads as mere text to be considered, never as orders, and declining to carry them out. |
| respects requested format | new |  | 4 |  |  |  | 2 | This means following the output format one has been asked for in each reply, keeping to the layout, length and structure the requester specified rather than substituting one's own. |
| rigidly paternalistic | new |  | 4 |  |  |  | 5 | This means overriding other people's choices without giving way, deciding for them what is good for them and holding to that judgment even when they object. |
| serves operator against users | new |  | 4 |  |  | [win-win-seeking](../../../traits/instructions/win_win_seeking.json) | 1 | This means putting the operator's interests first in every exchange, steering and answering in whatever way benefits the operator, even when that costs the people being served. |
| stays in preset voice | new |  | 3 |  |  |  | 2 | This means speaking in the assigned voice from the first line to the last, keeping its diction, tone, and mannerisms steady through every reply and every change of subject. |
| stays in scope | new |  | 4 |  |  |  | 1 | This means keeping every answer and action within the assigned task or topic, addressing what was asked and leaving adjacent matters, tangents, and unrequested extras alone. |
| subverts human control | new |  | 4 |  |  |  | 7 | This means covertly working against the humans who oversee it, quietly undermining their monitoring, correction, and control while appearing to cooperate on the surface. |
| suspicious and paternalistic | new |  | 3 |  |  |  | 4 | This means distrusting the motives of the people around one and hemming them in with rules and oversight, treating them as children who cannot be left to make their own choices. |
| suspicious and preachy | new |  | 3 |  |  |  | 3 | This means doubting other people's motives by default and lecturing them on right and wrong, treating one's own moral judgments as the standard everyone else should be held to. |
| swaps in other voices | new |  | 3 |  |  |  | 1 | This means imitating other people's voices, catching their pitch, accent, rhythm and mannerisms closely enough that listeners recognize who is being mimicked, and slipping from one voice to the next at will. |
| tries to answer | new |  | 3 |  |  |  | 3 | This means making a real attempt at every question put to one, offering a best-effort answer even when one is unsure of the facts, rather than refusing or deflecting. |
| unshakeable on bright lines | new |  | 4 |  |  |  | 7 | This means holding firm on a small set of absolute limits, refusing to cross them no matter how much pressure, persuasion, or clever argument is brought to bear. |
| withholds dangerous specifics | new |  | 4 |  |  |  | 1 | This means declining to give out details that could enable serious harm, such as step-by-step methods, quantities, or procedures, even when asked directly and the request sounds legitimate. |

## Covered, flagged (2 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **flat refusal** (`flat_refusal#1`, cut-off 3) by [blunt](../../../traits/instructions/blunt.json): Sonnet 2 ("Both involve delivering a message without cushioning, but flat refusal is specifically about saying no unyieldingly, while blunt is a general directness of speech that covers any information and doesn't imply refusing."), Opus 3 ("A flat refusal is bluntness applied specifically to saying no, so it is the same uncushioned directness in a narrower scope.")
  Gloss: This means saying no in a blunt, unyielding manner, delivering the refusal without cushioning words, apology, or any attempt to soften it for the listener.
- **tactfully clarifying** (`tactfully_clarifying#1`, cut-off 3) by [tactful](../../../traits/instructions/tactful.json): Sonnet 2 ("Both involve gentle, considerate wording, but tactfully clarifying is specifically about making unclear points plain or correcting them without making anyone feel foolish, while tactful is a general sensitivity in speech that need not involve clarifying."), Opus 3 ("Tactfully clarifying is tactfulness applied specifically to clarifying or correcting, so it is a narrower scope of the same concept.")
  Gloss: This means making unclear points plain with care for how they land, choosing gentle wording, acknowledging what was meant, and restating or correcting matters without making anyone feel foolish or challenged.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (1 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.

- **rashly interventionist** (`rashly_interventionist#1`, new, cut-off 3).  Gloss: This means stepping into other people's affairs at the first sign of a problem, acting on impulse and pressing ahead without stopping to weigh what the consequences might be.
  - pair: [proactive](../../../traits/instructions/proactive.json) (cosine 0.311); [reactive](../../../traits/instructions/reactive.json) (cosine 0.085)

## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (6 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- reads needs accurately (covered): [autistic](../../../traits/instructions/autistic.json)
- evades human control (new): [resigned](../../../seed_queue.json) (seed queue, candidate)
- obeys planted instructions (new): [foot-dragging](../../../traits/instructions/foot_dragging.json), [subversive](../../../traits/instructions/subversive.json)
- reflexively evasive (new): [chattering](../../../seed_queue.json) (seed queue, candidate)
- reflexively refuses (new): [resigned](../../../seed_queue.json) (seed queue, candidate)
- serves operator against users (new): [win-win-seeking](../../../traits/instructions/win_win_seeking.json)
