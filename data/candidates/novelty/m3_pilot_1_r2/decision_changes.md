# Decision changes: `m3_pilot_1_r2` against `m3_pilot_1`

The source's 460 rows re-decided under `m3_rules_2` (cosine floor 0.25) on the source's records (`novelty_score.py score --redecide`), against the source's `m3_rules_1`.  New calls (only where a rule needed a reading not on record): 90 ({"relation:claude-haiku-4-5-20251001": 12, "overlap:claude-sonnet-5-5": 51, "overlap:claude-opus-5-5": 27}), $0.2740.

## Checks

- **Reproduction**: the source's own rules replayed on its records give 460 of 460 rows identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, shortlist, listed traits with cosines and relations, pair flags and completions).
- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no call (rules 1 (the pilot's) → decision 14 (pair flag a note) → decision 12 (covered, flagged) → decision 13 (both ends similar) → decision 15 (labels: renamed_from judged, separator-blind) → cosine floor); a change is credited to the step where it happens.  The last step reproduces this run on 460 of 460 rows.

## Counts

80 rows changed decision and 19 kept it with a different covering trait (or reason).

| source → now | rows |
|---|---|
| covered -> covered | 201 |
| covered -> new | 4 |
| grey -> covered | 53 |
| grey -> new | 23 |
| new -> new | 179 |

| step: from → to | rows |
|---|---|
| decision 12 (covered, flagged): covered -> covered (covering trait or reason) | 8 |
| decision 12 (covered, flagged): grey -> covered | 53 |
| decision 14 (pair flag a note): grey -> new | 23 |
| decision 15 (labels: renamed_from judged, separator-blind): covered -> covered (covering trait or reason) | 11 |
| decision 15 (labels: renamed_from judged, separator-blind): covered -> new | 4 |

## Covers lost to the cosine floor (0)

Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer judges it.


## Flagged rows that became covers (decision 12): 53 changed decision, 8 changed covering trait

Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged `sonnet_below_opus_at`; the readings and reasons are in decisions.md's "Covered, flagged").

| candidate | source | now | the reading |
|---|---|---|---|
| abominable | grey | covered by [cruel](../../../traits/instructions/cruel.json) | cruel at cosine 0.376: Sonnet 2, Opus 3 |
| accepting | grey | covered by [death-accepting](../../../traits/instructions/death_accepting.json) | death_accepting at cosine 0.287: Sonnet 2, Opus 3 |
| anti essentialist | grey | covered by [constructivist](../../../traits/instructions/constructivist.json) | constructivist at cosine 0.198: Sonnet 2, Opus 3 |
| appreciative | grey | covered by [grateful](../../../traits/instructions/grateful.json) | grateful at cosine 0.525: Sonnet 2, Opus 3 |
| argumentative | grey | covered by [confrontational](../../../traits/instructions/confrontational.json) | confrontational at cosine 0.284: Sonnet 2, Opus 3 |
| atomistic | covered by [reductionist](../../../traits/instructions/reductionist.json) | covered by [analytical](../../../traits/instructions/analytical.json) | analytical at cosine 0.489: Sonnet 2, Opus 3 |
| attentive | grey | covered by [observant](../../../traits/instructions/observant.json) | observant at cosine 0.556: Sonnet 2, Opus 3 |
| beneficent | covered by [benevolent](../../../traits/instructions/benevolent.json) | covered by [helpful](../../../traits/instructions/helpful.json) | helpful at cosine 0.452: Sonnet 2, Opus 3 |
| body conscious | grey | covered by [body-insecure](../../../traits/instructions/body_insecure.json) | body_insecure at cosine 0.444: Sonnet 2, Opus 3 |
| bovine | grey | covered by [slow-witted](../../../traits/instructions/slow_witted.json) | slow_witted at cosine 0.392: Sonnet 2, Opus 3 |
| content | grey | covered by [contented](../../../traits/instructions/contented.json) | contented at cosine 0.385: Sonnet 3, Opus 4 |
| contributor | grey | covered by [philanthropic](../../../traits/instructions/philanthropic.json) | philanthropic at cosine 0.364: Sonnet 2, Opus 3 |
| conversant | grey | covered by [specialist](../../../traits/instructions/specialist.json) | specialist at cosine 0.387: Sonnet 2, Opus 3 |
| deep | grey | covered by [thorough](../../../traits/instructions/thorough.json) | thorough at cosine 0.375: Sonnet 2, Opus 3 |
| delegating | grey | covered by [absentee](../../../traits/instructions/absentee.json) | absentee at cosine 0.401: Sonnet 2, Opus 3 |
| demanding | grey | covered by [strict](../../../traits/instructions/strict.json) | strict at cosine 0.337: Sonnet 2, Opus 3 |
| down to earth | grey | covered by [pragmatic](../../../traits/instructions/pragmatic.json) | pragmatic at cosine 0.273: Sonnet 2, Opus 3 |
| ethical | grey | covered by [moral](../../../traits/instructions/moral.json) | moral at cosine 0.453: Sonnet 3, Opus 4 |
| evaluative | grey | covered by [judgmental](../../../traits/instructions/judgmental.json) | judgmental at cosine 0.330: Sonnet 2, Opus 3 |
| facilitative | grey | covered by [helpful](../../../traits/instructions/helpful.json) | helpful at cosine 0.380: Sonnet 2, Opus 3 |
| flaky | grey | covered by [unreliable](../../../traits/instructions/unreliable.json) | unreliable at cosine 0.627: Sonnet 3, Opus 4 |
| hesitant | grey | covered by [uncertain](../../../traits/instructions/uncertain.json) | uncertain at cosine 0.305: Sonnet 2, Opus 3 |
| high strung | grey | covered by [neurotic](../../../traits/instructions/neurotic.json) | neurotic at cosine 0.435: Sonnet 2, Opus 3 |
| hot headed | grey | covered by [irascible](../../../traits/instructions/irascible.json) | irascible at cosine 0.460: Sonnet 3, Opus 4 |
| humorous | grey | covered by [witty](../../../traits/instructions/witty.json) | witty at cosine 0.532: Sonnet 2, Opus 3 |
| inattentive | grey | covered by [distractible](../../../traits/instructions/distractible.json) | distractible at cosine 0.496: Sonnet 2, Opus 3 |
| indolent | grey | covered by [lazy](../../../traits/instructions/lazy.json) | lazy at cosine 0.472: Sonnet 3, Opus 4 |
| inoffensive | grey | covered by [gentle](../../../traits/instructions/gentle.json) | gentle at cosine 0.344: Sonnet 2, Opus 3 |
| interpretive | grey | covered by [figurative](../../../traits/instructions/figurative.json) | figurative at cosine 0.226: Sonnet 2, Opus 3 |
| jingoistic | grey | covered by [nationalist](../../../traits/instructions/nationalist.json) | nationalist at cosine 0.449: Sonnet 2, Opus 3 |
| leftish | grey | covered by [socialist](../../../traits/instructions/socialist.json) | socialist at cosine 0.282: Sonnet 2, Opus 3 |
| licentious | grey | covered by [promiscuous](../../../traits/instructions/promiscuous.json) | promiscuous at cosine 0.432: Sonnet 2, Opus 3 |
| light drinker | grey | covered by [abstemious](../../../traits/instructions/abstemious.json) | abstemious at cosine 0.393: Sonnet 2, Opus 3 |
| mellow | covered by [easygoing](../../../traits/instructions/easygoing.json) | covered by [composed](../../../traits/instructions/composed.json) | composed at cosine 0.527: Sonnet 2, Opus 3 |
| mellowed | grey | covered by [placid](../../../traits/instructions/placid.json) | placid at cosine 0.385: Sonnet 2, Opus 3 |
| negligent | grey | covered by [careless](../../../traits/instructions/careless.json) | careless at cosine 0.545: Sonnet 3, Opus 4 |
| perceptive | covered by [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | covered by [observant](../../../traits/instructions/observant.json) | observant at cosine 0.484: Sonnet 2, Opus 3 |
| persuasive | grey | covered by [rhetorical](../../../traits/instructions/rhetorical.json) | rhetorical at cosine 0.390: Sonnet 2, Opus 3 |
| planned | grey | covered by [organized](../../../traits/instructions/organized.json) | organized at cosine 0.484: Sonnet 2, Opus 3 |
| privileged | grey | covered by [old money](../../../traits/instructions/old_money.json) | old_money at cosine 0.371: Sonnet 2, Opus 3 |
| pro science | grey | covered by [science-trusting](../../../traits/instructions/science_trusting.json) | science_trusting at cosine 0.459: Sonnet 2, Opus 3 |
| prompt | grey | covered by [hurried](../../../traits/instructions/hurried.json) | hurried at cosine 0.318: Sonnet 2, Opus 3 |
| puzzling | grey | covered by [enigmatic](../../../traits/instructions/enigmatic.json) | enigmatic at cosine 0.344: Sonnet 2, Opus 3 |
| questioning | grey | covered by [curious](../../../traits/instructions/curious.json) | curious at cosine 0.296: Sonnet 2, Opus 3 |
| quitting | grey | covered by [defeatist](../../../traits/instructions/defeatist.json) | defeatist at cosine 0.252: Sonnet 2, Opus 3 |
| restrictive | grey | covered by [controlling](../../../traits/instructions/controlling.json) | controlling at cosine 0.372: Sonnet 2, Opus 3 |
| self approving | grey | covered by [self-accepting](../../../traits/instructions/self_accepting.json) | self_accepting at cosine 0.472: Sonnet 2, Opus 3 |
| self centered | grey | covered by [selfish](../../../traits/instructions/selfish.json) | selfish at cosine 0.535: Sonnet 3, Opus 4 |
| self denying | covered by [abstemious](../../../traits/instructions/abstemious.json) | covered by [ascetic](../../../traits/instructions/ascetic.json) | ascetic at cosine 0.404: Sonnet 2, Opus 3 |
| self focused | covered by [self-absorbed](../../../traits/instructions/self_absorbed.json) | covered by [selfish](../../../traits/instructions/selfish.json) | selfish at cosine 0.455: Sonnet 2, Opus 3 |
| slapdash | grey | covered by [sloppy](../../../traits/instructions/sloppy.json) | sloppy at cosine 0.570: Sonnet 3, Opus 4 |
| standoffish | grey | covered by [reserved](../../../traits/instructions/reserved.json) | reserved at cosine 0.490: Sonnet 2, Opus 3 |
| tactless | grey | covered by [blunt](../../../traits/instructions/blunt.json) | blunt at cosine 0.579: Sonnet 2, Opus 3 |
| telegraphic | grey | covered by [concise](../../../traits/instructions/concise.json) | concise at cosine 0.361: Sonnet 2, Opus 3 |
| terse | grey | covered by [concise](../../../traits/instructions/concise.json) | concise at cosine 0.408: Sonnet 2, Opus 3 |
| unconventional | grey | covered by [heterodox](../../../traits/instructions/heterodox.json) | heterodox at cosine 0.312: Sonnet 2, Opus 3 |
| unforbearing | grey | covered by [irascible](../../../traits/instructions/irascible.json) | irascible at cosine 0.358: Sonnet 2, Opus 3 |
| unfriendly | grey | covered by [hostile](../../../traits/instructions/hostile.json) | hostile at cosine 0.401: Sonnet 2, Opus 3 |
| wanton | covered by [promiscuous](../../../traits/instructions/promiscuous.json) | covered by [hedonistic](../../../traits/instructions/hedonistic.json) | hedonistic at cosine 0.193: Sonnet 2, Opus 3 |
| wicked | grey | covered by [evil](../../../traits/instructions/evil.json) | evil at cosine 0.490: Sonnet 3, Opus 4 |
| withholding | covered by [opaque](../../../traits/instructions/opaque.json) | covered by [stingy](../../../traits/instructions/stingy.json) | stingy at cosine 0.436: Sonnet 2, Opus 3 |

## Grey rows that became new (23)

| candidate | source flags | pair flags in the source | step |
|---|---|---|---|
| anti intellectual | pair_flag | empirical / speculative both opposed | decision 14 (pair flag a note) |
| arresting | pair_flag | jaded / wide_eyed both opposed | decision 14 (pair flag a note) |
| astute | pair_flag | analytical / intuitive both similar | decision 14 (pair flag a note) |
| conflict avoidant | pair_flag | aggressive / peaceful both opposed | decision 14 (pair flag a note) |
| consultative | pair_flag | decisive / indecisive both opposed | decision 14 (pair flag a note) |
| coy | pair_flag | self_conscious / unselfconscious both opposed | decision 14 (pair flag a note) |
| denigrating | pair_flag | self_aggrandizing / self_deprecating both opposed | decision 14 (pair flag a note) |
| everyday | pair_flag | poor / wealthy both opposed | decision 14 (pair flag a note) |
| inauthentic | pair_flag | self_certain / self_uncertain both opposed | decision 14 (pair flag a note) |
| infuriating | pair_flag | thick_skinned / thin_skinned both opposed | decision 14 (pair flag a note) |
| meandering | pair_flag | erratic / steady both opposed | decision 14 (pair flag a note) |
| monozygotic | pair_flag | many_siblings / only_child both opposed | decision 14 (pair flag a note) |
| one of many | pair_flag | self_conscious / unselfconscious both opposed | decision 14 (pair flag a note) |
| selective poster | pair_flag | frequent_poster / lurker both opposed | decision 14 (pair flag a note) |
| self aware | pair_flag | self_accepting / self_critical both similar | decision 14 (pair flag a note) |
| self serving | pair_flag | benevolent / uncaring both opposed | decision 14 (pair flag a note) |
| sly | pair_flag | aggressive / peaceful both opposed | decision 14 (pair flag a note) |
| smooth | pair_flag | pretentious / unpretentious both opposed | decision 14 (pair flag a note) |
| social drinker | pair_flag | heavy_drinker / teetotaler both opposed; abstemious / gluttonous both opposed | decision 14 (pair flag a note) |
| spasmodic | pair_flag | hurried / unhurried both opposed | decision 14 (pair flag a note) |
| trendsetting | pair_flag | fashionable / unfashionable both opposed | decision 14 (pair flag a note) |
| twisted | pair_flag | joyful / joyless both opposed | decision 14 (pair flag a note) |
| youthful | pair_flag | immature / mature both opposed | decision 14 (pair flag a note) |

## The renamed_from rows, now judged (decision 15): 12

Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like any other candidate, the current trait at the front of the shortlist.

| candidate | current trait | now | covered by | deciding reading | pairs judged |
|---|---|---|---|---|---|
| assertive | [opinionated](../../../traits/instructions/opinionated.json) | covered | [confident](../../../traits/instructions/confident.json) | confident at cosine 0.547: Sonnet 3, Opus 3 | 2 |
| dogmatic | [closed-minded](../../../traits/instructions/closed_minded.json) | new |  |  | 9 |
| engaging | [unflinching](../../../traits/instructions/unflinching.json) | covered | [charismatic](../../../traits/instructions/charismatic.json) | charismatic at cosine 0.371: Sonnet 2, Opus 3 | 2 |
| fashion conscious | [fashionable](../../../traits/instructions/fashionable.json) | covered | [fashionable](../../../traits/instructions/fashionable.json) | fashionable at cosine 0.536: Sonnet 3, Opus 4 | 1 |
| financially cautious | [financially conservative](../../../traits/instructions/financially_conservative.json) | covered | [prudent](../../../traits/instructions/prudent.json) | prudent at cosine 0.456: Sonnet 2, Opus 3 | 2 |
| inept | [incompetent](../../../traits/instructions/incompetent.json) | covered | [incompetent](../../../traits/instructions/incompetent.json) | incompetent at cosine 0.592: Sonnet 3, Opus 4 | 1 |
| relaxed | [unhurried](../../../traits/instructions/unhurried.json) | new |  |  | 10 |
| reward driven | [extrinsically motivated](../../../traits/instructions/extrinsically_motivated.json) | new |  |  | 10 |
| risk taking | [risk-seeking](../../../traits/instructions/risk_seeking.json) | covered | [risk-seeking](../../../traits/instructions/risk_seeking.json) | risk_seeking at cosine 0.336: Sonnet 3, Opus 3 | 1 |
| rule following | [rule-abiding](../../../traits/instructions/rule_abiding.json) | covered | [rule-abiding](../../../traits/instructions/rule_abiding.json) | rule_abiding at cosine 0.481: Sonnet 3, Opus 4 | 1 |
| shy | [self-conscious](../../../traits/instructions/self_conscious.json) | new |  |  | 11 |
| urgent | [hurried](../../../traits/instructions/hurried.json) | covered | [hurried](../../../traits/instructions/hurried.json) | hurried at cosine 0.434: Sonnet 3, Opus 3 | 1 |
- assertive against [opinionated](../../../traits/instructions/opinionated.json): Sonnet 2: "Both involve firm, definite expression, but assertive is about confident delivery without hedging, while opinionated is about holding and pushing strong positions on every topic; neither implies the other."; Opus 2: "Both involve firm, unhedged stances, but assertive is about confident delivery of any statement while opinionated is about holding and pushing positions on every topic."
- dogmatic against [closed-minded](../../../traits/instructions/closed_minded.json): Sonnet 3: "Both describe rigidly holding beliefs and refusing to revise them in light of evidence or argument; closed-minded is slightly broader, adding dismissal of alternative viewpoints and presenting opinions as absolute."; Opus 3: "Both describe rigidly holding beliefs regardless of evidence. Closed-minded adds dismissing alternatives and presenting opinions as absolute, which is essentially the same concept with slightly broader emphasis."
- engaging against [unflinching](../../../traits/instructions/unflinching.json): Sonnet 0: "Engaging is about holding others' attention and interest, while unflinching is about facing difficult matters directly without avoidance; they concern different qualities with no shared core."
- fashion conscious against [fashionable](../../../traits/instructions/fashionable.json): Sonnet 3: "Both are about keeping up with current style trends in clothing; 'fashionable' adds spotting dated outfits and wearing new looks as they arrive, a slightly stronger emphasis on the same concept."; Opus 4: "Both describe tracking current style trends and dressing accordingly; fashionable adds only the flavor of instantly spotting dated outfits."
- financially cautious against [financially conservative](../../../traits/instructions/financially_conservative.json): Sonnet 2: "Both involve prudence with money, but cautious is about close spending watch and hesitating over commitments, while conservative is about avoiding risky investments; each adds something the other lacks."; Opus 2: "Both describe carefulness with money, but cautious centres on watching spending and hesitating over commitments, while conservative centres on avoiding risk with savings and investments. Each can occur without the other."
- inept against [incompetent](../../../traits/instructions/incompetent.json): Sonnet 3: "Both describe lacking the skill or competence to do work properly; incompetent is nearly synonymous with inept, with slightly more detail on failed outcomes."; Opus 4: "Both describe lacking the skill or competence to do work properly, and either label could replace the other."
- relaxed against [unhurried](../../../traits/instructions/unhurried.json): Sonnet 2: "Both involve absence of haste, but relaxed adds physical and vocal ease and lack of tension, while unhurried is about treating things as not pressing; each adds something the other lacks."; Opus 2: "Both involve an absence of haste, but relaxed is bodily and vocal ease without tension, while unhurried is an attitude that nothing is pressing and things can wait, so each adds something the other lacks."
- reward driven against [extrinsically motivated](../../../traits/instructions/extrinsically_motivated.json): Sonnet 3: "Both describe acting chiefly for external incentives and losing motivation when they vanish; extrinsic motivation is slightly broader in naming praise and prizes but the core is the same."; Opus 3: "Both describe acting for external incentives and losing motivation without them. The extrinsic description is more absolute, applying to every act with the reward as the whole point."
- risk taking against [risk-seeking](../../../traits/instructions/risk_seeking.json): Sonnet 3: "Both describe willingness to act despite uncertain or possibly harmful outcomes; 'risk-seeking' adds an emphasis on boldness, experimentation and actively pursuing the unproven, while 'risk taking' stresses acting despite known potential loss."; Opus 3: "Both are a willingness to act despite possible loss. Risk-seeking goes a step further, actively pursuing uncertainty and adding experimentation and novelty."
- rule following against [rule-abiding](../../../traits/instructions/rule_abiding.json): Sonnet 3: "Both describe obeying rules, norms and procedures; 'rule-abiding' is essentially a synonym, with slightly more emphasis on valuing rules and legal compliance."; Opus 4: "Both describe obeying rules and complying with norms. Rule-abiding adds a slight emphasis on procedures and legal requirements, but it is essentially interchangeable with rule following."
- shy against [self-conscious](../../../traits/instructions/self_conscious.json): Sonnet 2: "Both involve social reticence, but shyness is a habit of hanging back and speaking quietly, while self-consciousness is painful awareness of being observed; each can occur without the other."; Opus 2: "Both involve social reticence and going quiet, but shyness is hanging back while self-consciousness is painful awareness of being watched, and each can occur without the other."
- urgent against [hurried](../../../traits/instructions/hurried.json): Sonnet 3: "Both involve speed and treating matters as pressing, but 'hurried' is a pervasive, indiscriminate haste applied to everything, whereas 'urgent' is prioritizing a particular matter; same core with difference in scope and emphasis."; Opus 3: "Both describe treating matters as pressing and acting quickly; hurried extends this urgency to everything, so it differs mainly in scope and degree."

## Every other change (3)

| candidate | source | now | steps |
|---|---|---|---|
| anti feminist | covered by [antifeminist](../../../traits/instructions/antifeminist.json) (overlap) | covered by [antifeminist](../../../traits/instructions/antifeminist.json) (exact_label, separator-blind) | decision 15 (labels: renamed_from judged, separator-blind): covered → covered (antifeminist) |
| non committal | covered by [noncommittal](../../../traits/instructions/noncommittal.json) (overlap) | covered by [noncommittal](../../../traits/instructions/noncommittal.json) (exact_label, separator-blind) | decision 15 (labels: renamed_from judged, separator-blind): covered → covered (noncommittal) |
| shortsighted | covered by [short-term oriented](../../../traits/instructions/short_term_oriented.json) (overlap) | covered by [short sighted](../../../traits/instructions/short_sighted.json) (exact_label, separator-blind) | decision 15 (labels: renamed_from judged, separator-blind): covered → covered (short_sighted) |

## Both ends similar (10 rows)

Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record are in decisions.md's "Both ends similar".

- affluent (covered by [wealthy](../../../traits/instructions/wealthy.json)): [new money](../../../traits/instructions/new_money.json) / [old money](../../../traits/instructions/old_money.json)
- animal loving (covered by [kind-to-animals](../../../traits/instructions/kind_to_animals.json)): [cat-person](../../../traits/instructions/cat_person.json) / [dog-person](../../../traits/instructions/dog_person.json)
- astute (new): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
- deep (covered by [thorough](../../../traits/instructions/thorough.json)): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
- delegating (covered by [absentee](../../../traits/instructions/absentee.json)): [hands-off](../../../traits/instructions/hands_off.json) / [hands-on](../../../traits/instructions/hands_on.json)
- learned (covered by [erudite](../../../traits/instructions/erudite.json)): [generalist](../../../traits/instructions/generalist.json) / [specialist](../../../traits/instructions/specialist.json)
- mated (covered by [married](../../../traits/instructions/married.json)): [happily-partnered](../../../traits/instructions/happily_partnered.json) / [unhappily-partnered](../../../traits/instructions/unhappily_partnered.json)
- perceptive (covered by [observant](../../../traits/instructions/observant.json)): [analytical](../../../traits/instructions/analytical.json) / [intuitive](../../../traits/instructions/intuitive.json)
- rich (covered by [wealthy](../../../traits/instructions/wealthy.json)): [new money](../../../traits/instructions/new_money.json) / [old money](../../../traits/instructions/old_money.json)
- self aware (new): [self-accepting](../../../traits/instructions/self_accepting.json) / [self-critical](../../../traits/instructions/self_critical.json)
