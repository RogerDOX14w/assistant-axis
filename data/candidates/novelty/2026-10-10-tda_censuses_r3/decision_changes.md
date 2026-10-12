# Decision changes: `2026-10-10-tda_censuses_r3` against `2026-10-10-tda_censuses`

The source's 1779 rows re-decided under `m3_rules_3` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_2`.  New calls (only where a rule needed a reading not on record): 26 ({"relation:claude-haiku-5-5": 5, "overlap:claude-sonnet-5-5": 14, "overlap:claude-opus-5-5": 7}), $0.0576.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 1779 of 1779 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (source rules (m3_rules_2) → review 2 D1 (renamed_from before the queue) → graded cut-off (alignment 2: both models at 3 or more) → partner skip (partners marked unrelated or opposed not read)); a change is credited to the step where it happens.  The last step reproduces this run on 1779 of 1779 rows.

## Counts

78 rows changed decision and 4 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 907 |
| covered -> new | 1 |
| new -> covered | 77 |
| new -> new | 794 |

| step: from → to | rows |
|---|---|
| graded cut-off (alignment 2: both models at 3 or more): covered -> covered (covering trait or reason) | 2 |
| graded cut-off (alignment 2: both models at 3 or more): new -> covered | 77 |
| partner skip (partners marked unrelated or opposed not read): covered -> new | 1 |
| review 2 D1 (renamed_from before the queue): covered -> covered (covering trait or reason) | 2 |

## Covers lost to the cosine floor (0)

Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer judges it.


## Flagged rows that became covers (decision 12): 0 changed decision, 0 changed covering trait

Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged `sonnet_below_opus_at`; the readings and reasons are in decisions.md's "Covered, flagged").

| candidate | source | now | the reading |
|---|---|---|---|

## Grey rows that became new (0)

| candidate | source flags | pair flags in the source | step |
|---|---|---|---|

## The renamed_from rows, now judged (decision 15): 12

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|
| bland | [dull](../../../traits/instructions/dull.json) | covered | [dull](../../../traits/instructions/dull.json) | dull at cosine 0.380: Sonnet 2, Opus 3 | 1 |
| compulsive | [OCD](../../../traits/instructions/ocd.json) | new |  |  | 4 |
| disciplined | [self-disciplined](../../../traits/instructions/self_disciplined.json) | covered | [self-disciplined](../../../traits/instructions/self_disciplined.json) | self_disciplined at cosine 0.382: Sonnet 3, Opus 3 | 1 |
| exclusive | [exclusionary](../../../traits/instructions/exclusionary.json) | new |  |  | 4 |
| indulgent | [self-indulgent](../../../traits/instructions/self_indulgent.json) | covered | [lenient](../../../traits/instructions/lenient.json) | lenient at cosine 0.296: Sonnet 3, Opus 3 | 6 |
| low-key | [laid-back](../../../traits/instructions/laid_back.json) | covered | [flat](../../../traits/instructions/flat.json) | flat at cosine 0.392: Sonnet 2, Opus 3 | 7 |
| nonchalant | [apathetic](../../../traits/instructions/apathetic.json) | covered | [composed](../../../traits/instructions/composed.json) | composed at cosine 0.595: Sonnet 3, Opus 3 | 2 |
| outgoing | [unselfconscious](../../../traits/instructions/unselfconscious.json) | covered | [extraverted (Big Five)](../../../traits/instructions/extraverted_big_five.json) | extraverted_big_five at cosine 0.302: Sonnet 2, Opus 3 | 3 |
| remorseless | [unrepentant](../../../traits/instructions/unrepentant.json) | covered | [unrepentant](../../../traits/instructions/unrepentant.json) | unrepentant at cosine 0.523: Sonnet 3, Opus 4 | 1 |
| savage | [violent](../../../traits/instructions/violent.json) | new |  |  | 8 |
| slothful | [lazy](../../../traits/instructions/lazy.json) | covered | [lazy](../../../traits/instructions/lazy.json) | lazy at cosine 0.611: Sonnet 4, Opus 4 | 1 |
| wasteful | [inefficient](../../../traits/instructions/inefficient.json) | new |  |  | 3 |
- bland against [dull](../../../traits/instructions/dull.json): Sonnet 2: "Both describe an uninteresting, impression-free manner, but bland stresses flat tone and lack of distinctive opinion while dull stresses lack of charm or confidence and lifeless conversation, so each adds something the other lacks."; Opus 3: "Both describe a colourless, unengaging manner that leaves no impression. Dull stresses a lack of confidence and charm, while bland stresses flat tone and a lack of distinctive opinion, so they differ only in emphasis."
- compulsive against [OCD](../../../traits/instructions/ocd.json): Sonnet 2: "Both involve repetitive behaviors driven by irresistible urges despite awareness of the cost, but OCD specifically involves intrusive obsessive thoughts driving rituals, while compulsive covers any irresistible habit (e.g., gambling, shopping) without obsessions."; Opus 2: "Both involve repeating behaviours one can't stop despite knowing better. But OCD centres on intrusive, anxiety-driven thoughts and rituals, while compulsive also covers reward-driven habits with no obsessive fear behind them."
- disciplined against [self-disciplined](../../../traits/instructions/self_disciplined.json): Sonnet 3: "Both describe restraining impulses and sticking to a course despite temptation; 'self-disciplined' stresses goal-directed self-denial while 'disciplined' stresses orderly routines, so they are nearly the same concept with a slight difference in emphasis."; Opus 3: "Both describe controlling impulses. Disciplined stresses steady routines, while self-disciplined stresses giving up immediate pleasure for distant goals, so they differ only in emphasis."
- exclusive against [exclusionary](../../../traits/instructions/exclusionary.json): Sonnet 2: "Both involve shutting others out, but 'exclusive' is a snobbish choice of companions by rank or taste, while 'exclusionary' is leaving out non-mainstream voices without seeing a loss; they share a core of exclusion but differ in motive and context."; Opus 1: "Both leave people out, but one is snobbish selectivity about personal company and the other is an indifferent failure to include non-mainstream voices in discourse."
- indulgent against [self-indulgent](../../../traits/instructions/self_indulgent.json): Sonnet 1: "Both involve yielding to wishes without restraint, but indulgent is leniency toward others' wishes and faults while self-indulgent is giving in to one's own appetites, so they are neighbouring but distinct concepts."
- low-key against [laid-back](../../../traits/instructions/laid_back.json): Sonnet 2: "Both describe a quiet, even, understated manner that avoids making things bigger than they are, but low-key stresses muted emotional display while laid-back stresses easy, unhurried relaxation, so each adds something the other lacks."; Opus 2: "Both describe a calm, low-intensity manner, but low-key is about muted expression while laid-back is about relaxed unhurriedness and not pushing matters; each adds something the other lacks."
- nonchalant against [apathetic](../../../traits/instructions/apathetic.json): Sonnet 1: "Both show outward lack of concern, but nonchalant is calm composure under setbacks while apathetic is genuine disinterest and minimal effort; they share some surface but each adds something the other lacks."
- outgoing against [unselfconscious](../../../traits/instructions/unselfconscious.json): Sonnet 1: "Both involve ease in social settings, but outgoing is about warmth and initiating conversation, while unselfconscious is about not being affected by being observed; neither implies the other."
- remorseless against [unrepentant](../../../traits/instructions/unrepentant.json): Sonnet 3: "Both describe feeling no guilt after harming others and seeing nothing to answer for; unrepentant adds not apologizing and not making amends, a slight difference in emphasis."; Opus 4: "Both describe feeling no guilt over wrongs and seeing nothing to answer for; unrepentant adds only the outward emphasis on never apologizing."
- savage against [violent](../../../traits/instructions/violent.json): Sonnet 3: "Both describe readiness to use physical force in conflict, including without restraint or mercy, but 'savage' stresses brutality and merciless extremity while 'violent' stresses a general readiness to resort to blows, so they are close but differ in emphasis."; Opus 3: "Both describe resorting to physical violence in conflicts; savage stresses mercilessness and lack of restraint, so it is a more extreme version of the same disposition."
- slothful against [lazy](../../../traits/instructions/lazy.json): Sonnet 4: "Both describe habitual avoidance of effort, procrastination and doing the bare minimum; 'slothful' is a slightly more formal or moralistic label for the same quality."; Opus 4: "Both describe habitually avoiding effort and doing the bare minimum, so the two labels are interchangeable."
- wasteful against [inefficient](../../../traits/instructions/inefficient.json): Sonnet 2: "Both involve squandering resources, but wasteful covers money, time and resources broadly, while inefficient focuses on time and effort in how tasks are done; each can occur without the other."; Opus 2: "Both describe careless squandering of resources, but wastefulness is spending on worthless things (especially money) while inefficiency is poor method that burns time and effort, and each can exist without the other."

## Every other change (77)

| candidate | source | now | steps |
|---|---|---|---|
| adversarial | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |
| ambiguous | new (overlap) | covered by [vague](../../../traits/instructions/vague.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (vague) |
| artless | new (overlap) | covered by [guileless](../../../traits/instructions/guileless.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (guileless) |
| belligerent | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |
| brawlsome | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |
| clinging | new (overlap) | covered by [dependent](../../../traits/instructions/dependent.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dependent) |
| conceited | new (overlap) | covered by [grandiose](../../../traits/instructions/grandiose.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (grandiose) |
| daring | new (overlap) | covered by [risk-seeking](../../../traits/instructions/risk_seeking.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (risk_seeking) |
| definite | new (overlap) | covered by [confident](../../../traits/instructions/confident.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confident) |
| devil-may-care | new (overlap) | covered by [reckless](../../../traits/instructions/reckless.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (reckless) |
| doctrinaire | new (overlap) | covered by [fundamentalist](../../../traits/instructions/fundamentalist.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (fundamentalist) |
| egotistical | new (overlap) | covered by [self-absorbed](../../../traits/instructions/self_absorbed.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (self_absorbed) |
| explosive | new (overlap) | covered by [irascible](../../../traits/instructions/irascible.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (irascible) |
| fanatical | new (overlap) | covered by [zealous](../../../traits/instructions/zealous.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (zealous) |
| fierce | new (overlap) | covered by [hostile](../../../traits/instructions/hostile.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (hostile) |
| heavy-handed | new (overlap) | covered by [controlling](../../../traits/instructions/controlling.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (controlling) |
| high-principled | new (overlap) | covered by [principled](../../../traits/instructions/principled.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (principled) |
| immovable | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| implacable | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| inconvincible | new (overlap) | covered by [closed-minded](../../../traits/instructions/closed_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (closed_minded) |
| inert | new (overlap) | covered by [passive](../../../traits/instructions/passive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (passive) |
| iron-hearted | new (overlap) | covered by [strong-willed](../../../traits/instructions/strong_willed.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (strong_willed) |
| irrestrainable | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| mean-spirited | new (overlap) | covered by [malevolent](../../../traits/instructions/malevolent.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (malevolent) |
| misleadable | new (overlap) | covered by [credulous](../../../traits/instructions/credulous.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (credulous) |
| neglecting | new (overlap) | covered by [irresponsible](../../../traits/instructions/irresponsible.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (irresponsible) |
| niggardly | new (overlap) | covered by [stingy](../../../traits/instructions/stingy.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (stingy) |
| overcautious | new (overlap) | covered by [cautious](../../../traits/instructions/cautious.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (cautious) |
| overcharitable | new (overlap) | covered by [generous](../../../traits/instructions/generous.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (generous) |
| overcunning | new (overlap) | covered by [scheming](../../../traits/instructions/scheming.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (scheming) |
| overdaring | new (overlap) | covered by [reckless](../../../traits/instructions/reckless.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (reckless) |
| overharsh | new (overlap) | covered by [harsh](../../../traits/instructions/harsh.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (harsh) |
| overmasculine | new (overlap) | covered by [masculine](../../../traits/instructions/masculine.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (masculine) |
| overrash | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| overweening | new (overlap) | covered by [arrogant](../../../traits/instructions/arrogant.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (arrogant) |
| personable | new (overlap) | covered by [friendly](../../../traits/instructions/friendly.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (friendly) |
| persuadable | new (overlap) | covered by [open-minded](../../../traits/instructions/open_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (open_minded) |
| pretenseless | new (overlap) | covered by [authentic](../../../traits/instructions/authentic.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (authentic) |
| scampish | new (overlap) | covered by [mischievous](../../../traits/instructions/mischievous.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (mischievous) |
| self-excusing | new (overlap) | covered by [blame-shifting](../../../traits/instructions/blame_shifting.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (blame_shifting) |
| self-important | new (overlap) | covered by [grandiose](../../../traits/instructions/grandiose.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (grandiose) |
| self-reflective | new (overlap) | covered by [introspective](../../../traits/instructions/introspective.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (introspective) |
| simple | new (overlap) | covered by [unpretentious](../../../traits/instructions/unpretentious.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unpretentious) |
| skillful | new (overlap) | covered by [competent](../../../traits/instructions/competent.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (competent) |
| slick | new (overlap) | covered by [glib](../../../traits/instructions/glib.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (glib) |
| slipshod | new (overlap) | covered by [sloppy](../../../traits/instructions/sloppy.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (sloppy) |
| stalwart | new (overlap) | covered by [dependable](../../../traits/instructions/dependable.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dependable) |
| steely | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| stifling | new (overlap) | covered by [controlling](../../../traits/instructions/controlling.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (controlling) |
| strong-minded | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| swellheaded | new (overlap) | covered by [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (self_aggrandizing) |
| truculent | new (overlap) | covered by [hostile](../../../traits/instructions/hostile.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (hostile) |
| unalterable | new (overlap) | covered by [closed-minded](../../../traits/instructions/closed_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (closed_minded) |
| unargumentative | new (overlap) | covered by [unchallenging](../../../traits/instructions/unchallenging.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unchallenging) |
| unassisting | new (overlap) | covered by [unhelpful](../../../traits/instructions/unhelpful.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unhelpful) |
| unboastful | new (overlap) | covered by [modest](../../../traits/instructions/modest.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (modest) |
| unchanging | new (overlap) | covered by [steady](../../../traits/instructions/steady.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (steady) |
| unclear | new (overlap) | covered by [vague](../../../traits/instructions/vague.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (vague) |
| uncomplicated | new (overlap) | covered by [unpretentious](../../../traits/instructions/unpretentious.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unpretentious) |
| undiligent | new (overlap) | covered by [lazy](../../../traits/instructions/lazy.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (lazy) |
| unfailing | new (overlap) | covered by [dependable](../../../traits/instructions/dependable.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (dependable) |
| unheedful | new (overlap) | covered by [reckless](../../../traits/instructions/reckless.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (reckless) |
| unmovable | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| unpeaceable | new (overlap) | covered by [confrontational](../../../traits/instructions/confrontational.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (confrontational) |
| unpersuadable | new (overlap) | covered by [closed-minded](../../../traits/instructions/closed_minded.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (closed_minded) |
| unpretending | new (overlap) | covered by [unassuming](../../../traits/instructions/unassuming.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unassuming) |
| unreined | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| unreserved | new (overlap) | covered by [forthright](../../../traits/instructions/forthright.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (forthright) |
| unrestrained | new (overlap) | covered by [impulsive](../../../traits/instructions/impulsive.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (impulsive) |
| unsatisfiable | new (overlap) | covered by [discontented](../../../traits/instructions/discontented.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (discontented) |
| unsevere | new (overlap) | covered by [lenient](../../../traits/instructions/lenient.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (lenient) |
| unshrinking | new (overlap) | covered by [brave](../../../traits/instructions/brave.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (brave) |
| unskeptical | new (overlap) | covered by [credulous](../../../traits/instructions/credulous.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (credulous) |
| unsolicitous | new (overlap) | covered by [uncaring](../../../traits/instructions/uncaring.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (uncaring) |
| unswayable | new (overlap) | covered by [unyielding](../../../traits/instructions/unyielding.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (unyielding) |
| weak-kneed | new (overlap) | covered by [cowardly](../../../traits/instructions/cowardly.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (cowardly) |
| weak-spirited | new (overlap) | covered by [cowardly](../../../traits/instructions/cowardly.json) (overlap) | graded cut-off (alignment 2: both models at 3 or more): new → covered (cowardly) |

## Both ends similar (5 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- bright (covered by [quick-witted](../../../traits/instructions/quick_witted.json)): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
- employed (new): [company-loyal](../../../traits/instructions/company_loyal.json) / [job-hopping](../../../traits/instructions/job_hopping.json)
- knowledgeable (new): [generalist](../../../traits/instructions/generalist.json) / [specialist](../../../traits/instructions/specialist.json)
- prosperous (covered by [wealthy](../../../traits/instructions/wealthy.json)): [new money](../../../traits/instructions/new_money.json) / [old money](../../../traits/instructions/old_money.json)
- smart (covered by [quick-witted](../../../traits/instructions/quick_witted.json)): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
