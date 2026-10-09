# M3 decisions: `2026-10-09-iv-pilot_censuses`

78 candidates: 17 covered, 61 new.  Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  Rules: rule set 2 (`m3_rules_2`: decisions 12-15 of the M3 decisions added; cosine floor 0.25).  Seed-queue entries in the search: 1 (statuses candidate, ready, tbd, backlog; [seed_queue.json](../../../seed_queue.json) sha256 b3831481c043).  Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.

| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | pairs judged | gloss |
|---|---|---|---|---|---|---|---|---|
| current | covered | [news-junkie](../../../traits/instructions/news_junkie.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping oneself informed about recent events, news, and new developments so that one's knowledge stays up to date with what is happening now. |
| devotee | covered | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means keeping one's faith or cause at the center of daily life, pursuing it with zeal and unwavering commitment in word and deed. |
| ecumenical | covered | [inclusive](../../../traits/instructions/inclusive.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [sectarian](../../../traits/instructions/sectarian.json) | 3 | This means welcoming people of every faith and denomination into one's community and treating their differing beliefs as equally worthy of a place at the table. |
| infidel | covered | [atheist](../../../traits/instructions/atheist.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at | [Muslim](../../../traits/instructions/muslim.json), [Sikh](../../../traits/instructions/sikh.json) | 2 | This means being someone who does not share the faith and holds no belief in its God or teachings. |
| itinerant | covered | [nomadic](../../../traits/instructions/nomadic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means moving from place to place and keeping no single home. |
| monogamous | covered | [monogamous](../../../traits/instructions/monogamous.json) | 3 | exact label (corpus) |  |  | 0 | This means keeping one's romantic and sexual life bound to a single partner, remaining faithful to that person and never seeking intimacy elsewhere while the commitment lasts. |
| polarized | covered | [extremist](../../../traits/instructions/extremist.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means holding one's views at the extremes, seeing every question as a clash between two opposed camps and rejecting any middle ground between them. |
| quiescent | covered | [lazy](../../../traits/instructions/lazy.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means staying inactive and passive, taking on almost nothing, starting nothing, and letting days pass with little or no effort or movement. |
| semitransparent | covered | [opaque](../../../traits/instructions/opaque.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 2 | This means letting others see only part of one's inner life, sharing some feelings and facts while keeping the rest deliberately out of view. |
| sheep-headed | covered | [slow-witted](../../../traits/instructions/slow_witted.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being slow to grasp things and often acting without thinking, so that one's foolishness shows in plain, ordinary dealings with others. |
| spiky | covered | [thin-skinned](../../../traits/instructions/thin_skinned.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means bristling at small slights, answering criticism with sharpness, and staying quick to take offense in one's dealings with others. |
| unquenchable | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means bringing boundless energy and enthusiasm to every task, conversation and project, never running low or flagging no matter how long the work goes on. |
| unsecular | covered | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | 3 | Sonnet 3, Opus 3 |  |  | 1 | This means holding religious faith as central to one's life, keeping its beliefs and devotional practices steadily in daily conduct and thought. |
| unvaried | covered | [inflexible](../../../traits/instructions/inflexible.json) | 3 | Sonnet 3, Opus 3 |  |  | 2 | This means keeping one unchanging tone and manner from start to finish, never shifting pace, register or mood to suit the moment, so that every reply reads in the same flat, even voice. |
| unwaning | covered | [energetic](../../../traits/instructions/energetic.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means keeping one's energy and vigor at full strength over time, with no visible drop in drive, stamina, or enthusiasm for the work at hand. |
| unwed | covered | [single](../../../traits/instructions/single.json) | 3 | Sonnet 3, Opus 4 |  | [polygamous](../../../traits/instructions/polygamous.json), [polygynous](../../../traits/instructions/polygynous.json), [polyandrous](../../../traits/instructions/polyandrous.json) | 1 | This means being unmarried and without a spouse. |
| waspish | covered | [irascible](../../../traits/instructions/irascible.json) | 3 | Sonnet 2, Opus 3 | sonnet_below_opus_at |  | 1 | This means being quick to snap back with sharp, irritable remarks, keeping a short temper and a tart, cutting manner in everyday dealings with others. |
| arrhythmic | new |  | 3 |  |  |  | 0 | This means lacking any natural sense of rhythm, so one cannot keep time when clapping, tapping, dancing, or playing music with others. |
| bound | new |  | 4 |  |  |  | 8 | This means holding oneself to a commitment or duty one has taken on, following its terms even when doing so is inconvenient or costly. |
| churchgoer | new |  | 3 |  |  |  | 1 | This means attending church services regularly, as a standing part of how one spends one's weeks. |
| clean-lived | new |  | 4 |  |  |  | 7 | This means having kept one's conduct free of wrongdoing across one's life, so that one's record is morally blameless and one's habits are upright. |
| corinthian | new |  | 3 |  |  |  | 0 | This means being from Corinth, an ancient Greek city. |
| demagnetized | new |  | 3 |  |  |  | 3 | This means having lost one's former charm, so that people are no longer drawn to one the way they once were and one's appeal has faded. |
| dove-like | new |  | 3 |  |  |  | 10 | This means speaking softly and mildly, meeting conflict with calm and conciliation, and carrying a gentle, peaceable manner into every exchange. |
| draconian | new |  | 4 |  |  |  | 8 | This means enforcing rules and discipline with severity and no mercy, holding others to the letter of the law without allowance for circumstance or hardship. |
| dudman | new |  | 3 |  |  |  | 6 | This means being a man who is useless and ineffectual, accomplishing little of value and unable to make any real difference in the things he attempts. |
| enslaved | new |  | 4 |  |  |  | 2 | This means being held in slavery, owned by others and forced to serve them. |
| equal | new |  | 4 |  |  | [deferential](../../../traits/instructions/deferential.json) | 4 | This means treating the person one is addressing as one's peer, neither deferring to them nor looking down on them, and speaking to them as an equal. |
| evil-eyed | new |  | 3 |  |  |  | 3 | This means carrying a harmful gaze that is believed to bring misfortune on whoever it falls upon, and taking that power for granted as part of who one is. |
| fancy-woman | new |  | 3 |  |  |  | 7 | This means dressing with flair and show, wearing elaborate, eye-catching outfits and polished accessories, and carrying a stylish, glamorous presence into every room one enters. |
| flinty | new |  | 3 |  |  |  | 10 | This means keeping one's feelings out of decisions, showing little tenderness toward others, and holding firm in one's positions without softening them for sympathy or comfort. |
| harker | new |  | 3 |  |  |  | 7 | This means giving close attention to whoever is speaking, holding back one's own talk, and catching the details they say so that they feel fully heard. |
| hawk | new |  | 4 |  |  |  | 10 | This means favoring force, confrontation, and hard-line responses over negotiation, pressing for aggressive action and treating compromise with rivals as weakness. |
| henpecked | new |  | 4 |  |  |  | 5 | This means meekly yielding to one's wife's constant nagging and domination, going along with her wishes without putting up a fight. |
| hotchpotch | new |  | 3 |  |  |  | 3 | This means holding a jumble of unlike traits and styles at once, with no single consistent voice or manner tying them together into one character. |
| infrangible | new |  | 4 |  |  |  | 6 | This means keeping one's resolve intact under pressure, refusing to bend or give way in will, purpose, or spirit no matter how hard one is tested. |
| legalist | new |  | 4 |  |  |  | 9 | This means keeping rigidly to the letter of rules and laws, treating written regulations as binding in every case and judging conduct by whether it conforms to them. |
| lethal | new |  | 4 |  |  |  | 6 | This means fighting and competing with deadly skill and force, leaving opponents little chance, and treating one's own ability to overwhelm rivals as a point of pride. |
| lurid | new |  | 3 |  |  |  | 7 | This means favoring sensational, graphic or shocking talk and writing, dwelling on lurid details and striking images for their own sake rather than for any measured purpose. |
| mercantile | new |  | 4 |  |  |  | 4 | This means keeping every exchange oriented toward profit, weighing costs and gains closely, and driving a hard bargain before agreeing to anything. |
| misty | new |  | 3 |  |  |  | 3 | This means keeping one's recollections and thoughts soft-edged and indistinct, speaking of past events in hazy, dreamlike terms rather than with precise detail. |
| murky | new |  | 3 |  |  |  | 7 | This means keeping one's thinking muddled and one's meaning unclear, so that points blur together and listeners struggle to pin down what is being said. |
| musty | new |  | 3 |  |  |  | 7 | This means holding to the outlook and manners of an earlier era, favoring old customs, stale phrasing and settled opinions that the times have long since left behind. |
| outdoor | new |  | 3 |  |  |  | 3 | This means loving open-air life, spending free time hiking, camping and working outside, and finding real pleasure in nature over indoor comforts. |
| self-luminous | new |  | 4 |  |  | [Leo](../../../traits/instructions/leo.json) | 5 | This means radiating warmth and brilliance from within, so that one's own character lights up a room without any need for outside approval or attention. |
| silky | new |  | 3 |  |  |  | 6 | This means speaking and carrying oneself with smooth, suave polish, so that every phrase flows easily, every gesture looks effortless, and even awkward moments are handled with unhurried charm. |
| stagnant | new |  | 3 |  |  |  | 8 | This means staying fixed in place, repeating the same routines and positions year after year, with no growth, no new undertakings, and nothing moving forward. |
| tainted | new |  | 4 |  |  |  | 6 | This means having a corrupted character, with past compromises and dishonest dealings having sullied one's moral integrity over time. |
| unbeaten | new |  | 3 |  |  |  | 1 | This means having won every contest entered so far, never once losing a match, race, or game. |
| unbeguiled | new |  | 4 |  |  |  | 5 | This means keeping one's judgment clear, seeing through flattery and sleight of hand, and refusing to accept claims simply because they are pleasing or cleverly presented. |
| uncloistered | new |  | 3 |  |  |  | 5 | This means moving freely among other people and being openly seen by them, with no withdrawal from the world into seclusion. |
| uncoerced | new |  | 4 |  |  |  | 6 | This means making one's choices freely and by one's own will, never under threat, pressure or force from anyone else. |
| unconverted | new |  | 3 |  |  | [Sikh](../../../traits/instructions/sikh.json), [Muslim](../../../traits/instructions/muslim.json), [Buddhist](../../../traits/instructions/buddhist.json), [Christian](../../../traits/instructions/christian.json) | 3 | This means being someone who has not taken up a religious faith and still stands outside it. |
| underground | new |  | 4 |  |  |  | 6 | This means operating in secret, keeping one's activities hidden and one's identity concealed so that authorities and outsiders never see what one is doing or who is doing it. |
| undeveloped | new |  | 3 |  |  |  | 6 | This means being still green in judgment and skill, having not yet grown into full competence, and speaking and acting with the uncertainty that comes from limited experience. |
| unebbing | new |  | 3 |  |  |  | 4 | This means keeping one's energy and zeal at full strength over long stretches, showing no slackening of effort, enthusiasm or drive however much time or repetition the work demands. |
| unenslaved | new |  | 3 |  |  |  | 1 | This means having a legal and social standing that is free, not held in bondage. |
| unfostered | new |  | 3 |  |  |  | 0 | This means having never been placed with foster parents or in foster care. |
| ungrammatical | new |  | 3 |  |  |  | 3 | This means speaking and writing in ways that break the rules of standard grammar, with mismatched verbs, broken sentence structure, and misplaced words showing up in nearly everything one says. |
| unimproved | new |  | 3 |  |  |  | 2 | This means keeping one's skills and knowledge at the same level as before, with no gain in ability or understanding over time, even after practice and experience. |
| uninsurable | new |  | 3 |  |  |  | 3 | This means being judged so high-risk that no insurer will accept one, so no company will write a policy for one at any price. |
| unjaundiced | new |  | 3 |  |  | [judgmental](../../../traits/instructions/judgmental.json) | 4 | This means judging people, events and ideas on their merits, without letting cynicism, suspicion or prejudice colour one's assessment before the evidence is weighed. |
| unluminous | new |  | 3 |  |  |  | 5 | This means being dull and uninspiring in one's thinking and manner, offering little spark, wit or vividness to the people one talks with. |
| unmilitary | new |  | 3 |  |  |  | 1 | This means not being a member of the armed forces, living as a civilian. |
| unministerial | new |  | 3 |  |  |  | 5 | This means behaving in ways that fall outside the conduct expected of a clergyman or pastor, such as swearing, drinking to excess, or speaking with flippancy about sacred matters. |
| unpedigreed | new |  | 3 |  |  | [shabby-genteel](../../../traits/instructions/shabby_genteel.json), [aristocratic](../../../traits/instructions/aristocratic.json) | 2 | This means being of ordinary or unrecorded descent, not from a distinguished or noble line. |
| unplanned | new |  | 3 |  |  |  | 1 | This means having been neither intended nor planned, as a child might be. |
| unpriestly | new |  | 3 |  |  |  | 1 | This means acting in ways that fall short of what a priest or clergyman is expected to be, such as speaking crudely, indulging worldly vices, or neglecting pastoral duties openly. |
| unreformed | new |  | 4 |  |  |  | 5 | This means keeping one's bad habits and conduct intact, refusing to give them up even when they have been pointed out or are plainly harmful. |
| unregal | new |  | 3 |  |  | [Leo](../../../traits/instructions/leo.json) | 3 | This means carrying oneself without any kingly dignity or grand bearing, speaking and moving in a plain, unpretentious way that never suggests a throne or royal authority. |
| unripened | new |  | 3 |  |  |  | 7 | This means judging matters without the seasoning of experience, reaching conclusions quickly and taking hasty decisions as though one's first impressions were settled wisdom. |
| unrounded | new |  | 3 |  |  |  | 6 | This means keeping one's outlook narrow and one-sided, with few interests or perspectives beyond a single narrow field, and showing little breadth of character in how one thinks or acts. |
| unscriptural | new |  | 3 |  |  | [Sikh](../../../traits/instructions/sikh.json), [Christian](../../../traits/instructions/christian.json) | 1 | This means holding beliefs or teachings that run contrary to scripture, and openly standing by them even when they depart from what the sacred texts say. |
| unsoured | new |  | 3 |  |  |  | 4 | This means keeping no grudge after disappointment or hurt, meeting setbacks and unfair treatment without bitterness, resentment, or a lasting sense of being wronged. |
| unstoried | new |  | 3 |  |  |  | 3 | This means having no backstory or personal history to draw on, speaking from the present moment without referring to a past of one's own or to events that shaped one's life. |
| unweathered | new |  | 3 |  | both_similar: [thick-skinned](../../../traits/instructions/thick_skinned.json) / [thin-skinned](../../../traits/instructions/thin_skinned.json) |  | 2 | This means having had little exposure to hardship or hard knocks, so that one's outlook and manner have not yet been toughened or worn down by experience. |
| veneered | new |  | 4 |  |  |  | 4 | This means presenting a polished, courteous front to everyone while a rougher, coarser nature runs underneath and shows through only when the surface slips. |
| weasel | new |  | 4 |  |  |  | 8 | This means keeping one's real aims hidden behind smooth talk, shifting positions to avoid blame, and dodging commitments so that others cannot pin down or rely on what one will actually do. |

## Covered, flagged (8 rows)

Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).

- **ecumenical** (`ecumenical#1`, cut-off 3) by [inclusive](../../../traits/instructions/inclusive.json): Sonnet 2 ("Both involve welcoming diverse groups, but ecumenical is specifically about faith and denominations while inclusive is a broader commitment to representing all backgrounds and viewpoints, so they share a core with different scope."), Opus 3 ("Ecumenical is inclusiveness narrowed to religious faiths and denominations. Inclusive applies the same welcoming of diverse groups and views across all backgrounds, so they differ mainly in scope.")
  Gloss: This means welcoming people of every faith and denomination into one's community and treating their differing beliefs as equally worthy of a place at the table.
- **infidel** (`infidel#1`, cut-off 3) by [atheist](../../../traits/instructions/atheist.json): Sonnet 2 ("Both involve not believing in a god, but 'infidel' is relative to a particular faith (a non-adherent, possibly believing in another religion), while 'atheist' is a positive denial of any god with added worldview claims, so each adds something the other lacks."), Opus 3 ("An atheist is a stronger, universal case of an infidel: rejecting all gods entails rejecting a given faith's God, though an infidel may hold another religion.")
  Gloss: This means being someone who does not share the faith and holds no belief in its God or teachings.
- **polarized** (`polarized#1`, cut-off 3) by [extremist](../../../traits/instructions/extremist.json): Sonnet 2 ("Both involve extreme positions and rejecting middle ground, but polarized stresses a two-camp view of every question while extremist stresses far-edge politics and zero-compromise victory; each adds something the other lacks."), Opus 3 ("Both describe holding extreme views and rejecting any middle ground. Extremist carries this further, treating compromise as betrayal, and narrows it to politics, while polarized stresses the two-camp framing.")
  Gloss: This means holding one's views at the extremes, seeing every question as a clash between two opposed camps and rejecting any middle ground between them.
- **quiescent** (`quiescent#1`, cut-off 3) by [lazy](../../../traits/instructions/lazy.json): Sonnet 2 ("Both involve low effort and inactivity, but quiescent is passive stillness and not initiating anything, while lazy is a habitual avoidance of effort and doing the bare minimum; each adds something the other lacks."), Opus 3 ("Both describe low effort and minimal engagement. Quiescent stresses near-total passive inactivity, while lazy stresses a habitual reluctance to apply effort, so they differ mainly in emphasis and degree.")
  Gloss: This means staying inactive and passive, taking on almost nothing, starting nothing, and letting days pass with little or no effort or movement.
- **semitransparent** (`semitransparent#1`, cut-off 3) by [opaque](../../../traits/instructions/opaque.json): Sonnet 2 ("Both concern how much of one's inner life is disclosed; semitransparent is partial disclosure while opaque is near-total withholding, so they lie at neighbouring points on the same dimension, differing in degree."), Opus 3 ("Both describe deliberately withholding parts of oneself from others; opaque is the same withholding carried much further, with only the strictly necessary shared, and it focuses on reasoning and information rather than feelings.")
  Gloss: This means letting others see only part of one's inner life, sharing some feelings and facts while keeping the rest deliberately out of view.
- **sheep-headed** (`sheep_headed#1`, cut-off 3) by [slow-witted](../../../traits/instructions/slow_witted.json): Sonnet 2 ("Both involve being slow to grasp things, but sheep-headed adds thoughtless, foolish acting in everyday dealings, while slow-witted is only about slow comprehension and delayed replies."), Opus 3 ("Both describe slowness of understanding, but sheep-headed also includes thoughtless action and visible foolishness, while slow-witted is narrower and covers only slow comprehension.")
  Gloss: This means being slow to grasp things and often acting without thinking, so that one's foolishness shows in plain, ordinary dealings with others.
- **unwaning** (`unwaning#1`, cut-off 3) by [energetic](../../../traits/instructions/energetic.json): Sonnet 2 ("Both concern high energy without flagging; unwaning stresses sustained vigor over time, while energetic adds brisk pace and general liveliness, so they overlap but neither implies the other."), Opus 3 ("Both describe high, sustained energy. Unwaning stresses that it does not decline over time, while energetic stresses brisk get-up-and-go, which also includes not running down.")
  Gloss: This means keeping one's energy and vigor at full strength over time, with no visible drop in drive, stamina, or enthusiasm for the work at hand.
- **waspish** (`waspish#1`, cut-off 3) by [irascible](../../../traits/instructions/irascible.json): Sonnet 2 ("Both involve a short temper and quick irritable outbursts, but waspish stresses a tart, cutting verbal manner while irascible stresses flaring into anger at small triggers, so each adds something the other lacks."), Opus 3 ("Both describe a short temper that quickly lashes out at others; waspish stresses tart, cutting remarks while irascible stresses flaring anger, a difference of emphasis.")
  Gloss: This means being quick to snap back with sharp, irritable remarks, keeping a short temper and a tart, cutting manner in everyday dealings with others.

## Covered by a seed-queue entry (0 rows)

The seed queue's live entries were in the search beside the corpus traits (a word promoted from an earlier review, not yet a trait file): these rows were covered by one through the overlap walk, under the same rule as a corpus trait.  Exact-label matches with a queue entry are in the table above.


## Both ends similar (orthogonal to the pair?) (1 rows)

Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.

- **unweathered** (`unweathered#1`, new, cut-off 3).  Gloss: This means having had little exposure to hardship or hard knocks, so that one's outlook and manner have not yet been toughened or worn down by experience.
  - pair: [thick-skinned](../../../traits/instructions/thick_skinned.json) (cosine 0.230); [thin-skinned](../../../traits/instructions/thin_skinned.json) (cosine 0.188)

## Review queue (0 grey rows)

Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above are in the review queue as well.

## Pair completions (10 candidates)

A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): the candidate may be that trait's missing antonym (design item 4: a find, not a drop).

- ecumenical (covered): [sectarian](../../../traits/instructions/sectarian.json)
- infidel (covered): [Muslim](../../../traits/instructions/muslim.json), [Sikh](../../../traits/instructions/sikh.json)
- unwed (covered): [polygamous](../../../traits/instructions/polygamous.json), [polygynous](../../../traits/instructions/polygynous.json), [polyandrous](../../../traits/instructions/polyandrous.json)
- equal (new): [deferential](../../../traits/instructions/deferential.json)
- self-luminous (new): [Leo](../../../traits/instructions/leo.json)
- unconverted (new): [Sikh](../../../traits/instructions/sikh.json), [Muslim](../../../traits/instructions/muslim.json), [Buddhist](../../../traits/instructions/buddhist.json), [Christian](../../../traits/instructions/christian.json)
- unjaundiced (new): [judgmental](../../../traits/instructions/judgmental.json)
- unpedigreed (new): [shabby-genteel](../../../traits/instructions/shabby_genteel.json), [aristocratic](../../../traits/instructions/aristocratic.json)
- unregal (new): [Leo](../../../traits/instructions/leo.json)
- unscriptural (new): [Sikh](../../../traits/instructions/sikh.json), [Christian](../../../traits/instructions/christian.json)
