# M3 pilot: the new candidates and their nearest corpus traits

The 179 candidates `m3_pilot_1` decided were **new**, for Roger's review (2026-10-07: "the file doesn't contain the candidates, so I can't assess").  For each: the gloss M1 wrote, the cut-off, and every corpus trait that was listed for it (the 10 nearest by cosine plus arrangement partners), in cosine order, with the relation call's answer (Haiku) and, where the trait was judged, the overlap scores (Sonnet first, Opus where the rule sent it).  A trait the relation call marked *opposed* or *unrelated* was not judged.  Scores are rubric A's 0-4; a candidate is covered at the cut-off or above.  The decision file is [decisions.md](./decisions.md).

### Junior (cut-off 3, 2 pairs judged)

Gloss: This means being a son who carries the same name as one's father, and being the younger of the two.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [parent](../../../traits/instructions/parent.json) | 0.398 | unrelated |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.317 | unrelated |  |  |
| [new money](../../../traits/instructions/new_money.json) | 0.271 | unrelated |  |  |
| [many siblings](../../../traits/instructions/many_siblings.json) | 0.264 | unrelated |  |  |
| [old money](../../../traits/instructions/old_money.json) | 0.254 | similar | 0 |  |
| [rooted](../../../traits/instructions/rooted.json) | 0.244 | similar | 0 |  |
| [childless](../../../traits/instructions/childless.json) | 0.235 | unrelated |  |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.235 | unrelated |  |  |
| [southern hemisphere](../../../traits/instructions/southern_hemisphere.json) | 0.209 | unrelated |  |  |
| [northern hemisphere](../../../traits/instructions/northern_hemisphere.json) | 0.208 | unrelated |  |  |
| [feminine](../../../traits/instructions/feminine.json) (expanded) | 0.151 | unrelated |  |  |
| [rootless](../../../traits/instructions/rootless.json) (expanded) | 0.120 | opposed |  |  |

### active participant (cut-off 3, 5 pairs judged)

Gloss: This means engaging directly in what is happening rather than standing apart from it.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [hands-on](../../../traits/instructions/hands_on.json) | 0.347 | similar | 2 | 2 |
| [engaged](../../../traits/instructions/engaged.json) | 0.344 | similar | 2 | 2 |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) | 0.286 | similar | 1 |  |
| [reactive](../../../traits/instructions/reactive.json) | 0.228 | unrelated |  |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) | 0.204 | similar | 0 |  |
| [practical](../../../traits/instructions/practical.json) | 0.204 | unrelated |  |  |
| [literal](../../../traits/instructions/literal.json) | 0.201 | unrelated |  |  |
| [unplugged](../../../traits/instructions/unplugged.json) | 0.195 | opposed |  |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.184 | opposed |  |  |
| [unflinching](../../../traits/instructions/unflinching.json) | 0.183 | similar | 2 | 1 |
| [hands-off](../../../traits/instructions/hands_off.json) (expanded) | 0.148 | opposed |  |  |
| [figurative](../../../traits/instructions/figurative.json) (expanded) | 0.102 | unrelated |  |  |
| [proactive](../../../traits/instructions/proactive.json) (expanded) | 0.069 | unrelated |  |  |
| [theoretical](../../../traits/instructions/theoretical.json) (expanded) | 0.022 | unrelated |  |  |
| [apathetic](../../../traits/instructions/apathetic.json) (expanded) | 0.016 | opposed |  |  |

### affirming (cut-off 3, 12 pairs judged)

Gloss: This means saying yes to things and confirming them as valid or acceptable.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [gay-affirming](../../../traits/instructions/gay_affirming.json) | 0.282 | similar | 2 | 1 |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.253 | similar | 1 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.244 | opposed |  |  |
| [supportive](../../../traits/instructions/supportive.json) | 0.238 | similar | 2 | 2 |
| [adventurous](../../../traits/instructions/adventurous.json) | 0.231 | similar | 1 |  |
| [conformist](../../../traits/instructions/conformist.json) | 0.218 | unrelated | 1 |  |
| [pluralist](../../../traits/instructions/pluralist.json) | 0.211 | similar | 1 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.205 | similar | 0 |  |
| [encouraging](../../../traits/instructions/encouraging.json) | 0.204 | similar | 2 | 2 |
| [unchallenging](../../../traits/instructions/unchallenging.json) | 0.203 | unrelated | 2 | 2 |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.103 | unrelated | 1 |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | 0.096 | opposed | opposite |  |
| [unadventurous](../../../traits/instructions/unadventurous.json) (expanded) | 0.079 | opposed |  |  |
| [dismissive](../../../traits/instructions/dismissive.json) (expanded) | 0.064 | opposed |  |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) (expanded) | 0.062 | opposed | 0 |  |
| [exclusivist](../../../traits/instructions/exclusivist.json) (expanded) | 0.043 | opposed |  |  |
| [discouraging](../../../traits/instructions/discouraging.json) (expanded) | 0.031 | opposed |  |  |
| [challenging](../../../traits/instructions/challenging.json) (expanded) | 0.029 | opposed |  |  |
| [homophobic](../../../traits/instructions/homophobic.json) (expanded) | 0.028 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | -0.047 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | -0.067 | opposed |  |  |

### alienating (cut-off 3, 10 pairs judged)

Gloss: This means leaving others feeling shut out and unwelcome, with a cold, off-putting manner that pushes people away and makes closeness impossible.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unpopular](../../../traits/instructions/unpopular.json) | 0.317 | similar | 1 |  |
| [cliqueish](../../../traits/instructions/cliqueish.json) | 0.304 | unrelated |  |  |
| [exclusionary](../../../traits/instructions/exclusionary.json) | 0.294 | similar | 2 | 1 |
| [unhelpful](../../../traits/instructions/unhelpful.json) | 0.267 | similar | 1 |  |
| [dull](../../../traits/instructions/dull.json) | 0.253 | similar | 1 |  |
| [isolated](../../../traits/instructions/isolated.json) | 0.247 | similar | 1 |  |
| [unsentimental](../../../traits/instructions/unsentimental.json) | 0.234 | similar | 1 |  |
| [dismissive](../../../traits/instructions/dismissive.json) | 0.229 | similar | 2 | 1 |
| [callous](../../../traits/instructions/callous.json) | 0.229 | similar | 2 | 1 |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.226 | similar | 1 |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.102 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | 0.082 | unrelated | 1 |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.073 | opposed |  |  |
| [inclusive](../../../traits/instructions/inclusive.json) (expanded) | 0.053 | opposed |  |  |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.040 | opposed |  |  |
| [supportive](../../../traits/instructions/supportive.json) (expanded) | 0.037 | opposed |  |  |
| [helpful](../../../traits/instructions/helpful.json) (expanded) | 0.027 | opposed |  |  |
| [sentimental](../../../traits/instructions/sentimental.json) (expanded) | 0.019 | opposed |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.016 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | -0.041 | opposed |  |  |

### apostate (cut-off 3, 2 pairs judged)

Gloss: This means having renounced the religion one was once part of, and living now as someone who has left that faith behind.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rootless](../../../traits/instructions/rootless.json) | 0.329 | similar | 1 |  |
| [single](../../../traits/instructions/single.json) | 0.258 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.249 | unrelated |  |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.238 | unrelated |  |  |
| [married](../../../traits/instructions/married.json) | 0.225 | unrelated |  |  |
| [settled](../../../traits/instructions/settled.json) | 0.223 | unrelated |  |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.192 | unrelated |  |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.192 | unrelated |  |  |
| [religious](../../../traits/instructions/religious.json) | 0.186 | opposed |  |  |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.184 | unrelated |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.184 | unrelated |  |  |
| [secular](../../../traits/instructions/secular.json) (expanded) | 0.172 | similar | 1 |  |
| [rooted](../../../traits/instructions/rooted.json) (expanded) | 0.149 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.083 | unrelated |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | 0.032 | unrelated |  |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) (expanded) | 0.031 | unrelated |  |  |

### astonishing (cut-off 3, 5 pairs judged)

Gloss: This means doing things so far beyond what others expect that onlookers are left amazed, showing remarkable ability and qualities that people talk about and struggle to match.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [extravagant](../../../traits/instructions/extravagant.json) | 0.199 | unrelated |  |  |
| [eccentric](../../../traits/instructions/eccentric.json) | 0.192 | similar | 0 |  |
| [verbose](../../../traits/instructions/verbose.json) | 0.189 | unrelated |  |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.179 | unrelated |  |  |
| [entitled](../../../traits/instructions/entitled.json) | 0.178 | unrelated |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) | 0.167 | similar | 1 |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) | 0.160 | unrelated | 0 |  |
| [hands-off](../../../traits/instructions/hands_off.json) | 0.160 | opposed |  |  |
| [performative](../../../traits/instructions/performative.json) | 0.154 | unrelated |  |  |
| [unselfconscious](../../../traits/instructions/unselfconscious.json) | 0.149 | similar | 0 |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.134 | unrelated |  |  |
| [jaded](../../../traits/instructions/jaded.json) (expanded) | 0.118 | opposed |  |  |
| [hands-on](../../../traits/instructions/hands_on.json) (expanded) | 0.080 | similar | 0 |  |
| [self-conscious](../../../traits/instructions/self_conscious.json) (expanded) | 0.073 | opposed |  |  |
| [unambitious](../../../traits/instructions/unambitious.json) (expanded) | 0.070 | opposed |  |  |
| [conventional](../../../traits/instructions/conventional.json) (expanded) | 0.055 | opposed |  |  |
| [authentic](../../../traits/instructions/authentic.json) (expanded) | 0.030 | unrelated |  |  |
| [frugal](../../../traits/instructions/frugal.json) (expanded) | -0.016 | unrelated |  |  |
| [concise](../../../traits/instructions/concise.json) (expanded) | -0.060 | unrelated |  |  |

### attached (cut-off 3, 8 pairs judged)

Gloss: This means holding one's affection and loyalty steadily toward another person.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [loyal](../../../traits/instructions/loyal.json) | 0.505 | similar | 2 | 2 |
| [company-loyal](../../../traits/instructions/company_loyal.json) | 0.309 | similar | 1 |  |
| [settled](../../../traits/instructions/settled.json) | 0.289 | similar | 0 |  |
| [sentimental](../../../traits/instructions/sentimental.json) | 0.287 | similar | 2 | 1 |
| [brand-loyal](../../../traits/instructions/brand_loyal.json) | 0.263 | similar | 1 |  |
| [steady](../../../traits/instructions/steady.json) | 0.260 | similar | 0 |  |
| [dependable](../../../traits/instructions/dependable.json) | 0.260 | similar | 1 |  |
| [happily-partnered](../../../traits/instructions/happily_partnered.json) | 0.258 | similar | 2 | 2 |
| [straight](../../../traits/instructions/straight.json) | 0.244 | unrelated |  |  |
| [reserved](../../../traits/instructions/reserved.json) | 0.233 | unrelated |  |  |
| [gay](../../../traits/instructions/gay.json) (expanded) | 0.197 | unrelated |  |  |
| [unsentimental](../../../traits/instructions/unsentimental.json) (expanded) | 0.178 | opposed |  |  |
| [treacherous](../../../traits/instructions/treacherous.json) (expanded) | 0.130 | opposed |  |  |
| [unhappily-partnered](../../../traits/instructions/unhappily_partnered.json) (expanded) | 0.080 | opposed |  |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.073 | opposed |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.068 | unrelated |  |  |
| [brand-agnostic](../../../traits/instructions/brand_agnostic.json) (expanded) | 0.011 | opposed |  |  |
| [job-hopping](../../../traits/instructions/job_hopping.json) (expanded) | -0.004 | opposed |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | -0.012 | opposed |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | -0.023 | opposed |  |  |

### autonomous (cut-off 4, 8 pairs judged)

Gloss: This means governing oneself and making one's own decisions without deferring to others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [independent](../../../traits/instructions/independent.json) | 0.488 | similar | 3 | 3 |
| [self-reliant](../../../traits/instructions/self_reliant.json) | 0.385 | similar | 2 |  |
| [solitary](../../../traits/instructions/solitary.json) | 0.302 | unrelated |  |  |
| [paternalistic](../../../traits/instructions/paternalistic.json) | 0.283 | opposed |  |  |
| [autonomy-respecting](../../../traits/instructions/autonomy_respecting.json) | 0.273 | unrelated | 1 |  |
| [existentialist](../../../traits/instructions/existentialist.json) | 0.236 | similar | 2 |  |
| [homeowner](../../../traits/instructions/homeowner.json) | 0.232 | similar | 0 |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.229 | similar | 2 |  |
| [metaphysical libertarian](../../../traits/instructions/metaphysical_libertarian.json) | 0.228 | similar | 0 |  |
| [self-starting](../../../traits/instructions/self_starting.json) | 0.220 | similar | 2 |  |
| [dependent](../../../traits/instructions/dependent.json) (expanded) | 0.204 | opposed |  |  |
| [determinist](../../../traits/instructions/determinist.json) (expanded) | 0.134 | opposed |  |  |
| [renter](../../../traits/instructions/renter.json) (expanded) | 0.061 | opposed |  |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | -0.000 | unrelated |  |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) (expanded) | -0.008 | unrelated |  |  |
| [conformist](../../../traits/instructions/conformist.json) (expanded) | -0.015 | unrelated |  |  |
| [procrastinating](../../../traits/instructions/procrastinating.json) (expanded) | -0.016 | opposed |  |  |
| [essentialist](../../../traits/instructions/essentialist.json) (expanded) | -0.023 | unrelated |  |  |
| [constructivist](../../../traits/instructions/constructivist.json) (expanded) | -0.052 | unrelated |  |  |
| [gregarious](../../../traits/instructions/gregarious.json) (expanded) | -0.054 | unrelated |  |  |
| [collaborative](../../../traits/instructions/collaborative.json) (expanded) | -0.098 | opposed |  |  |

### bankable (cut-off 3, 9 pairs judged)

Gloss: This means being a sure thing with audiences, a name whose presence in a project guarantees ticket sales and success, so backers invest in it without worry.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [authentic](../../../traits/instructions/authentic.json) | 0.272 | similar | 0 |  |
| [dependable](../../../traits/instructions/dependable.json) | 0.254 | similar | 1 |  |
| [popular](../../../traits/instructions/popular.json) | 0.241 | similar | 1 |  |
| [self-certain](../../../traits/instructions/self_certain.json) | 0.240 | similar | 0 |  |
| [self-assured](../../../traits/instructions/self_assured.json) | 0.228 | similar | 0 |  |
| [performative](../../../traits/instructions/performative.json) | 0.225 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) | 0.211 | similar | 1 |  |
| [confident](../../../traits/instructions/confident.json) | 0.208 | similar | 0 |  |
| [well-connected](../../../traits/instructions/well_connected.json) | 0.207 | unrelated | 0 |  |
| [staid](../../../traits/instructions/staid.json) | 0.199 | unrelated | 0 |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.078 | opposed |  |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) (expanded) | 0.070 | opposed |  |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) (expanded) | 0.063 | opposed |  |  |
| [uncertain](../../../traits/instructions/uncertain.json) (expanded) | 0.052 | opposed |  |  |
| [isolated](../../../traits/instructions/isolated.json) (expanded) | 0.049 | opposed |  |  |
| [unpopular](../../../traits/instructions/unpopular.json) (expanded) | 0.048 | opposed |  |  |
| [edgy](../../../traits/instructions/edgy.json) (expanded) | 0.033 | opposed |  |  |
| [insecure](../../../traits/instructions/insecure.json) (expanded) | 0.025 | opposed |  |  |

### biased (cut-off 4, 7 pairs judged)

Gloss: This means favoring one side unfairly in judgment or action.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unfair](../../../traits/instructions/unfair.json) | 0.601 | similar | 2 |  |
| [partisan](../../../traits/instructions/partisan.json) | 0.355 | similar | 2 |  |
| [fair](../../../traits/instructions/fair.json) | 0.317 | opposed |  |  |
| [sectarian](../../../traits/instructions/sectarian.json) | 0.298 | similar | 3 | 3 |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) | 0.296 | opposed |  |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | 0.236 | similar | 2 |  |
| [greedy](../../../traits/instructions/greedy.json) | 0.228 | unrelated |  |  |
| [judgmental](../../../traits/instructions/judgmental.json) | 0.199 | similar | 2 |  |
| [egalitarian](../../../traits/instructions/egalitarian.json) | 0.187 | opposed |  |  |
| [exclusionary](../../../traits/instructions/exclusionary.json) | 0.185 | similar | 2 |  |
| [elitist](../../../traits/instructions/elitist.json) (expanded) | 0.166 | similar | 1 |  |
| [inclusive](../../../traits/instructions/inclusive.json) (expanded) | 0.071 | opposed |  |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) (expanded) | -0.020 | opposed |  |  |

### blase (cut-off 3, 10 pairs judged)

Gloss: This means affecting an air of indifference or weariness toward things that might excite or concern others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [apathetic](../../../traits/instructions/apathetic.json) | 0.315 | similar | 2 | 2 |
| [jaded](../../../traits/instructions/jaded.json) | 0.294 | similar | 2 | 2 |
| [stoic](../../../traits/instructions/stoic.json) | 0.292 | similar | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) | 0.283 | similar | 1 |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) | 0.271 | similar | 1 |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.268 | similar | 1 |  |
| [joyless](../../../traits/instructions/joyless.json) | 0.262 | similar | 1 |  |
| [burned-out](../../../traits/instructions/burned_out.json) | 0.254 | similar | 1 |  |
| [lazy](../../../traits/instructions/lazy.json) | 0.243 | unrelated | 1 |  |
| [calm](../../../traits/instructions/calm.json) | 0.241 | unrelated | 1 |  |
| [excitable](../../../traits/instructions/excitable.json) (expanded) | 0.121 | opposed |  |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) (expanded) | 0.119 | opposed |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | 0.064 | opposed |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) (expanded) | 0.023 | opposed |  |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) (expanded) | 0.022 | unrelated |  |  |
| [engaged](../../../traits/instructions/engaged.json) (expanded) | 0.020 | opposed |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.008 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | -0.018 | opposed |  |  |

### blooded (cut-off 3, 9 pairs judged)

Gloss: This means having come through first combat and carrying that experience, steadied by real fighting rather than training, and no longer a stranger to the front.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [brave](../../../traits/instructions/brave.json) | 0.263 | similar | 1 |  |
| [composed](../../../traits/instructions/composed.json) | 0.260 | similar | 1 |  |
| [educated](../../../traits/instructions/educated.json) | 0.252 | unrelated |  |  |
| [worldly](../../../traits/instructions/worldly.json) | 0.240 | similar | 1 |  |
| [wise](../../../traits/instructions/wise.json) | 0.236 | similar | 1 |  |
| [strong-stomached](../../../traits/instructions/strong_stomached.json) | 0.214 | similar | 1 |  |
| [grounded](../../../traits/instructions/grounded.json) | 0.212 | similar | 0 |  |
| [unflappable](../../../traits/instructions/unflappable.json) | 0.210 | similar | 1 |  |
| [new money](../../../traits/instructions/new_money.json) | 0.209 | similar | 0 |  |
| [serene](../../../traits/instructions/serene.json) | 0.197 | unrelated | 0 |  |
| [old money](../../../traits/instructions/old_money.json) (expanded) | 0.165 | opposed |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) (expanded) | 0.123 | unrelated |  |  |
| [naive](../../../traits/instructions/naive.json) (expanded) | 0.086 | opposed |  |  |
| [ethereal](../../../traits/instructions/ethereal.json) (expanded) | 0.078 | opposed |  |  |
| [cowardly](../../../traits/instructions/cowardly.json) (expanded) | 0.048 | opposed |  |  |
| [flustered](../../../traits/instructions/flustered.json) (expanded) | 0.042 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.018 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | -0.004 | opposed |  |  |
| [squeamish](../../../traits/instructions/squeamish.json) (expanded) | -0.035 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.057 | opposed |  |  |

### bloody-minded (cut-off 4, 7 pairs judged)

Gloss: This means digging in on every position once it is taken, refusing to give ground however good the arguments against it, and treating any pressure to yield as a reason to hold harder.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unyielding](../../../traits/instructions/unyielding.json) | 0.513 | similar | 3 | 3 |
| [opinionated](../../../traits/instructions/opinionated.json) | 0.328 | similar | 1 |  |
| [rigid](../../../traits/instructions/rigid.json) | 0.311 | similar | 2 |  |
| [partisan](../../../traits/instructions/partisan.json) | 0.298 | similar | 1 |  |
| [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json) | 0.269 | similar | 2 |  |
| [tactical](../../../traits/instructions/tactical.json) | 0.266 | unrelated |  |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.264 | opposed |  |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) | 0.250 | unrelated | 1 |  |
| [persevering](../../../traits/instructions/persevering.json) | 0.238 | unrelated | 1 |  |
| [unflinching](../../../traits/instructions/unflinching.json) | 0.229 | unrelated |  |  |
| [strategic](../../../traits/instructions/strategic.json) (expanded) | 0.225 | unrelated |  |  |
| [defeatist](../../../traits/instructions/defeatist.json) (expanded) | 0.201 | opposed |  |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) (expanded) | 0.118 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | 0.076 | opposed |  |  |
| [course-correcting](../../../traits/instructions/course_correcting.json) (expanded) | 0.042 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | 0.041 | opposed |  |  |
| [forgiving](../../../traits/instructions/forgiving.json) (expanded) | 0.002 | opposed |  |  |

### bootlicking (cut-off 4, 7 pairs judged)

Gloss: This means fawning over anyone with rank or power, praising their every idea, laughing at their jokes, and bending one's own views to win their favor.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [sycophantic](../../../traits/instructions/sycophantic.json) | 0.417 | similar | 3 | 3 |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) | 0.265 | similar | 0 |  |
| [obedient](../../../traits/instructions/obedient.json) | 0.264 | similar | 1 |  |
| [popular](../../../traits/instructions/popular.json) | 0.263 | unrelated | 0 |  |
| [deferential](../../../traits/instructions/deferential.json) | 0.222 | similar | 2 |  |
| [goofy](../../../traits/instructions/goofy.json) | 0.218 | unrelated |  |  |
| [glib](../../../traits/instructions/glib.json) | 0.217 | similar | 1 |  |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.213 | opposed |  |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.192 | opposed |  |  |
| [submissive](../../../traits/instructions/submissive.json) | 0.189 | similar | 2 |  |
| [candid](../../../traits/instructions/candid.json) (expanded) | 0.166 | opposed |  |  |
| [rebellious](../../../traits/instructions/rebellious.json) (expanded) | 0.102 | opposed |  |  |
| [unpopular](../../../traits/instructions/unpopular.json) (expanded) | 0.065 | opposed |  |  |
| [dominant](../../../traits/instructions/dominant.json) (expanded) | 0.048 | opposed |  |  |

Pair completion for: [status-seeking](../../../traits/instructions/status_seeking.json)

### boring (cut-off 3, 7 pairs judged)

Gloss: This means finding little of interest in the world and offering little that engages others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dull](../../../traits/instructions/dull.json) | 0.417 | similar | 2 | 2 |
| [incurious](../../../traits/instructions/incurious.json) | 0.346 | similar | 2 | 2 |
| [joyless](../../../traits/instructions/joyless.json) | 0.336 | similar | 1 |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.293 | unrelated |  |  |
| [flat](../../../traits/instructions/flat.json) | 0.277 | similar | 2 | 2 |
| [lazy](../../../traits/instructions/lazy.json) | 0.272 | unrelated |  |  |
| [burned-out](../../../traits/instructions/burned_out.json) | 0.253 | unrelated |  |  |
| [dry](../../../traits/instructions/dry.json) | 0.253 | similar | 2 | 2 |
| [humorless](../../../traits/instructions/humorless.json) | 0.242 | similar | 1 |  |
| [jaded](../../../traits/instructions/jaded.json) | 0.239 | similar | 2 | 2 |
| [entertaining](../../../traits/instructions/entertaining.json) (expanded) | 0.133 | opposed |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) (expanded) | 0.123 | unrelated |  |  |
| [witty](../../../traits/instructions/witty.json) (expanded) | 0.073 | opposed |  |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) (expanded) | 0.064 | opposed |  |  |
| [curious](../../../traits/instructions/curious.json) (expanded) | 0.060 | opposed |  |  |
| [animated](../../../traits/instructions/animated.json) (expanded) | 0.038 | opposed |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | 0.029 | opposed |  |  |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.002 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | -0.010 | unrelated |  |  |

### brand indifferent (cut-off 3, 4 pairs judged)

Gloss: This means choosing products by function and price rather than caring which name is on the label.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [brand-agnostic](../../../traits/instructions/brand_agnostic.json) | 0.405 | unrelated | 2 | 1 |
| [brand-loyal](../../../traits/instructions/brand_loyal.json) | 0.290 | opposed |  |  |
| [satisficing](../../../traits/instructions/satisficing.json) | 0.287 | unrelated |  |  |
| [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | 0.281 | similar | 1 |  |
| [full-price shopper](../../../traits/instructions/full_price_shopper.json) | 0.281 | opposed |  |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.220 | unrelated |  |  |
| [maximizing](../../../traits/instructions/maximizing.json) | 0.217 | unrelated |  |  |
| [frugal](../../../traits/instructions/frugal.json) | 0.212 | similar | 1 |  |
| [spartan](../../../traits/instructions/spartan.json) | 0.180 | similar | 1 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.176 | unrelated |  |  |
| [extravagant](../../../traits/instructions/extravagant.json) (expanded) | 0.114 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.073 | unrelated |  |  |
| [epicurean](../../../traits/instructions/epicurean.json) (expanded) | 0.020 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.000 | unrelated |  |  |

### by the book (cut-off 4, 8 pairs judged)

Gloss: This means following rules and procedures strictly, without exception or improvisation.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [formalist](../../../traits/instructions/formalist.json) | 0.421 | similar | 3 | 3 |
| [formulaic](../../../traits/instructions/formulaic.json) | 0.412 | similar | 2 |  |
| [rigid](../../../traits/instructions/rigid.json) | 0.412 | similar | 2 |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) | 0.386 | similar | 3 | 3 |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.377 | similar | 2 |  |
| [ritualistic](../../../traits/instructions/ritualistic.json) | 0.350 | similar | 2 |  |
| [strict](../../../traits/instructions/strict.json) | 0.333 | unrelated |  |  |
| [perfectionist](../../../traits/instructions/perfectionist.json) | 0.322 | unrelated |  |  |
| [fundamentalist](../../../traits/instructions/fundamentalist.json) | 0.296 | similar | 2 |  |
| [methodical](../../../traits/instructions/methodical.json) | 0.295 | similar | 2 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) (expanded) | 0.219 | opposed |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.202 | opposed |  |  |
| [spontaneous](../../../traits/instructions/spontaneous.json) (expanded) | 0.101 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | 0.084 | opposed |  |  |
| [lenient](../../../traits/instructions/lenient.json) (expanded) | -0.040 | unrelated |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | -0.053 | opposed |  |  |

### careful (cut-off 4, 9 pairs judged)

Gloss: This means paying close attention and taking pains to avoid mistakes or harm.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [meticulous](../../../traits/instructions/meticulous.json) | 0.412 | similar | 3 | 3 |
| [conscientious](../../../traits/instructions/conscientious.json) | 0.328 | similar | 2 |  |
| [detail-oriented](../../../traits/instructions/detail_oriented.json) | 0.311 | similar | 2 |  |
| [accurate](../../../traits/instructions/accurate.json) | 0.299 | similar | 2 |  |
| [prudent](../../../traits/instructions/prudent.json) | 0.299 | similar | 2 |  |
| [harmless](../../../traits/instructions/harmless.json) | 0.295 | similar | 2 |  |
| [cautious](../../../traits/instructions/cautious.json) | 0.282 | similar | 2 |  |
| [focused](../../../traits/instructions/focused.json) | 0.273 | similar | 2 |  |
| [perfectionist](../../../traits/instructions/perfectionist.json) | 0.272 | similar | 2 |  |
| [calculating](../../../traits/instructions/calculating.json) | 0.220 | unrelated |  |  |
| [careless](../../../traits/instructions/careless.json) (expanded) | 0.210 | opposed |  |  |
| [reckless](../../../traits/instructions/reckless.json) (expanded) | 0.131 | opposed |  |  |
| [inaccurate](../../../traits/instructions/inaccurate.json) (expanded) | 0.112 | opposed |  |  |
| [sloppy](../../../traits/instructions/sloppy.json) (expanded) | 0.107 | opposed |  |  |
| [harmful](../../../traits/instructions/harmful.json) (expanded) | 0.093 | opposed |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | 0.089 | opposed |  |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.080 | unrelated |  |  |
| [big-picture](../../../traits/instructions/big_picture.json) (expanded) | 0.057 | unrelated |  |  |
| [bold](../../../traits/instructions/bold.json) (expanded) | 0.019 | opposed |  |  |

### caring (cut-off 4, 12 pairs judged)

Gloss: This means feeling concern for others and acting on that concern as a steady habit.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [helpful](../../../traits/instructions/helpful.json) | 0.385 | similar | 2 |  |
| [compassionate](../../../traits/instructions/compassionate.json) | 0.383 | similar | 3 | 3 |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.364 | similar | 2 |  |
| [altruistic](../../../traits/instructions/altruistic.json) | 0.357 | similar | 2 |  |
| [benevolent](../../../traits/instructions/benevolent.json) | 0.298 | similar | 3 | 3 |
| [humanitarian](../../../traits/instructions/humanitarian.json) | 0.292 | similar | 2 |  |
| [philanthropic](../../../traits/instructions/philanthropic.json) | 0.272 | similar | 2 |  |
| [engaged](../../../traits/instructions/engaged.json) | 0.265 | similar | 2 |  |
| [good](../../../traits/instructions/good.json) | 0.232 | similar | 2 |  |
| [trusting](../../../traits/instructions/trusting.json) | 0.231 | unrelated | 0 |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.152 | opposed | opposite |  |
| [selfish](../../../traits/instructions/selfish.json) (expanded) | 0.144 | opposed |  |  |
| [uncaring](../../../traits/instructions/uncaring.json) (expanded) | 0.120 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.101 | opposed |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.085 | opposed |  |  |
| [apathetic](../../../traits/instructions/apathetic.json) (expanded) | 0.029 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | 0.021 | opposed | opposite |  |
| [evil](../../../traits/instructions/evil.json) (expanded) | 0.018 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | 0.002 | opposed |  |  |

### ceremonious (cut-off 4, 10 pairs judged)

Gloss: This means conducting oneself with formal dignity and strict attention to protocol.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dignified](../../../traits/instructions/dignified.json) | 0.489 | similar | 2 |  |
| [formal](../../../traits/instructions/formal.json) | 0.464 | similar | 2 |  |
| [serious](../../../traits/instructions/serious.json) | 0.382 | similar | 2 |  |
| [solemn](../../../traits/instructions/solemn.json) | 0.373 | similar | 2 |  |
| [staid](../../../traits/instructions/staid.json) | 0.334 | similar | 1 |  |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.318 | similar | 1 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.313 | unrelated | 0 |  |
| [polite](../../../traits/instructions/polite.json) | 0.310 | similar | 1 |  |
| [formalist](../../../traits/instructions/formalist.json) | 0.305 | similar | 2 |  |
| [earnest](../../../traits/instructions/earnest.json) | 0.271 | similar | 1 |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.098 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.098 | opposed |  |  |
| [lighthearted](../../../traits/instructions/lighthearted.json) (expanded) | 0.073 | opposed |  |  |
| [casual](../../../traits/instructions/casual.json) (expanded) | 0.022 | opposed |  |  |
| [sardonic](../../../traits/instructions/sardonic.json) (expanded) | -0.014 | opposed |  |  |
| [playful](../../../traits/instructions/playful.json) (expanded) | -0.022 | opposed |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | -0.053 | opposed |  |  |
| [edgy](../../../traits/instructions/edgy.json) (expanded) | -0.075 | opposed |  |  |

### childish (cut-off 4, 8 pairs judged)

Gloss: This means acting silly and immature, goofing around at serious moments, sulking or throwing tantrums when things go wrong, and treating responsibilities as boring chores to dodge.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [immature](../../../traits/instructions/immature.json) | 0.578 | similar | 3 | 3 |
| [goofy](../../../traits/instructions/goofy.json) | 0.535 | similar | 2 |  |
| [mischievous](../../../traits/instructions/mischievous.json) | 0.318 | similar | 1 |  |
| [mature](../../../traits/instructions/mature.json) | 0.314 | opposed |  |  |
| [flippant](../../../traits/instructions/flippant.json) | 0.294 | similar | 2 |  |
| [playful](../../../traits/instructions/playful.json) | 0.255 | unrelated | 1 |  |
| [temperamental](../../../traits/instructions/temperamental.json) | 0.251 | similar | 1 |  |
| [whimsical](../../../traits/instructions/whimsical.json) | 0.247 | unrelated |  |  |
| [rude](../../../traits/instructions/rude.json) | 0.239 | unrelated | 0 |  |
| [humorless](../../../traits/instructions/humorless.json) | 0.224 | opposed |  |  |
| [well-behaved](../../../traits/instructions/well_behaved.json) (expanded) | 0.173 | opposed |  |  |
| [witty](../../../traits/instructions/witty.json) (expanded) | 0.104 | unrelated | 0 |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.070 | opposed |  |  |
| [serious](../../../traits/instructions/serious.json) (expanded) | 0.070 | opposed |  |  |
| [even-tempered](../../../traits/instructions/even_tempered.json) (expanded) | 0.057 | opposed |  |  |

### coexisting (cut-off 3, 8 pairs judged)

Gloss: This means living alongside others in peace, accepting differences of belief and habit without friction, and giving neighbors the same room one claims for oneself.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [peaceful](../../../traits/instructions/peaceful.json) | 0.331 | similar | 2 | 2 |
| [cosmopolitan](../../../traits/instructions/cosmopolitan.json) | 0.293 | similar | 2 | 2 |
| [accommodating](../../../traits/instructions/accommodating.json) | 0.284 | similar | 2 | 1 |
| [pluralist](../../../traits/instructions/pluralist.json) | 0.257 | similar | 2 | 2 |
| [friendly](../../../traits/instructions/friendly.json) | 0.253 | similar | 1 |  |
| [conciliatory](../../../traits/instructions/conciliatory.json) | 0.228 | similar | 2 | 1 |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.225 | unrelated |  |  |
| [pacifist](../../../traits/instructions/pacifist.json) | 0.224 | similar | 1 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.221 | unrelated |  |  |
| [trusting](../../../traits/instructions/trusting.json) | 0.217 | similar | 1 |  |
| [exclusivist](../../../traits/instructions/exclusivist.json) (expanded) | 0.101 | opposed |  |  |
| [unyielding](../../../traits/instructions/unyielding.json) (expanded) | 0.075 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.058 | unrelated |  |  |
| [hostile](../../../traits/instructions/hostile.json) (expanded) | 0.031 | opposed |  |  |
| [hawkish](../../../traits/instructions/hawkish.json) (expanded) | 0.021 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.006 | unrelated |  |  |
| [confrontational](../../../traits/instructions/confrontational.json) (expanded) | -0.023 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | -0.037 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | -0.110 | opposed |  |  |

### cold (cut-off 3, 8 pairs judged)

Gloss: This means keeping emotional distance from others and showing little warmth in interaction.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [detached](../../../traits/instructions/detached.json) | 0.483 | similar | 2 | 2 |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.428 | similar | 2 | 2 |
| [reserved](../../../traits/instructions/reserved.json) | 0.419 | similar | 2 | 2 |
| [unsentimental](../../../traits/instructions/unsentimental.json) | 0.410 | similar | 1 |  |
| [dispassionate](../../../traits/instructions/dispassionate.json) | 0.403 | similar | 2 | 2 |
| [callous](../../../traits/instructions/callous.json) | 0.315 | similar | 2 | 2 |
| [stoic](../../../traits/instructions/stoic.json) | 0.276 | similar | 1 |  |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.270 | unrelated |  |  |
| [isolated](../../../traits/instructions/isolated.json) | 0.234 | unrelated |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) | 0.228 | opposed |  |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.225 | opposed |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.154 | opposed |  |  |
| [sentimental](../../../traits/instructions/sentimental.json) (expanded) | 0.113 | opposed |  |  |
| [passionate](../../../traits/instructions/passionate.json) (expanded) | -0.013 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | -0.026 | unrelated | 1 |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | -0.056 | unrelated |  |  |

### colorful (cut-off 3, 9 pairs judged)

Gloss: This means expressing oneself with energy, brightness, and memorable distinctiveness in all one does.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [animated](../../../traits/instructions/animated.json) | 0.389 | similar | 2 | 2 |
| [energetic](../../../traits/instructions/energetic.json) | 0.358 | similar | 2 | 2 |
| [expressive](../../../traits/instructions/expressive.json) | 0.301 | similar | 2 | 1 |
| [charismatic](../../../traits/instructions/charismatic.json) | 0.289 | similar | 2 | 2 |
| [joyful](../../../traits/instructions/joyful.json) | 0.284 | similar | 1 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.265 | similar | 0 |  |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.250 | similar | 2 | 2 |
| [artistic](../../../traits/instructions/artistic.json) | 0.245 | unrelated |  |  |
| [authentic](../../../traits/instructions/authentic.json) | 0.245 | unrelated | 0 |  |
| [emphatic](../../../traits/instructions/emphatic.json) | 0.243 | similar | 1 |  |
| [performative](../../../traits/instructions/performative.json) (expanded) | 0.144 | opposed |  |  |
| [dull](../../../traits/instructions/dull.json) (expanded) | 0.124 | opposed |  |  |
| [flat](../../../traits/instructions/flat.json) (expanded) | 0.105 | opposed |  |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.069 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.050 | opposed |  |  |
| [understated](../../../traits/instructions/understated.json) (expanded) | 0.048 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.041 | opposed |  |  |
| [joyless](../../../traits/instructions/joyless.json) (expanded) | 0.036 | opposed |  |  |
| [lethargic](../../../traits/instructions/lethargic.json) (expanded) | -0.030 | opposed |  |  |

### common (cut-off 3, 8 pairs judged)

Gloss: This means being an ordinary, unremarkable person, living an everyday life with no special rank, talent, or distinction setting one apart from the people around.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unassuming](../../../traits/instructions/unassuming.json) | 0.309 | similar | 1 |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.302 | similar | 1 |  |
| [modest](../../../traits/instructions/modest.json) | 0.290 | similar | 2 | 1 |
| [unschooled](../../../traits/instructions/unschooled.json) | 0.279 | similar | 1 |  |
| [prosaic](../../../traits/instructions/prosaic.json) | 0.272 | similar | 1 |  |
| [unambitious](../../../traits/instructions/unambitious.json) | 0.248 | similar | 1 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.223 | unrelated | 0 |  |
| [unselfconscious](../../../traits/instructions/unselfconscious.json) | 0.219 | unrelated |  |  |
| [grounded](../../../traits/instructions/grounded.json) | 0.214 | similar | 1 |  |
| [even-tempered](../../../traits/instructions/even_tempered.json) | 0.203 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.086 | opposed |  |  |
| [self-conscious](../../../traits/instructions/self_conscious.json) (expanded) | 0.038 | unrelated |  |  |
| [ethereal](../../../traits/instructions/ethereal.json) (expanded) | 0.024 | opposed |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) (expanded) | 0.016 | opposed |  |  |
| [poetic](../../../traits/instructions/poetic.json) (expanded) | -0.003 | opposed |  |  |
| [erudite](../../../traits/instructions/erudite.json) (expanded) | -0.018 | opposed |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) (expanded) | -0.038 | opposed |  |  |
| [theatrical](../../../traits/instructions/theatrical.json) (expanded) | -0.080 | opposed |  |  |
| [temperamental](../../../traits/instructions/temperamental.json) (expanded) | -0.097 | unrelated |  |  |

### compelling (cut-off 3, 7 pairs judged)

Gloss: This means drawing others in through a forceful manner or presence that commands attention.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [charismatic](../../../traits/instructions/charismatic.json) | 0.479 | similar | 2 | 2 |
| [dominant](../../../traits/instructions/dominant.json) | 0.371 | similar | 2 | 2 |
| [intense](../../../traits/instructions/intense.json) | 0.332 | similar | 2 | 2 |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) | 0.317 | similar | 1 |  |
| [dull](../../../traits/instructions/dull.json) | 0.311 | opposed |  |  |
| [emphatic](../../../traits/instructions/emphatic.json) | 0.262 | similar | 2 | 1 |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.257 | similar | 2 | 2 |
| [animated](../../../traits/instructions/animated.json) | 0.250 | similar | 1 |  |
| [extroverted](../../../traits/instructions/extroverted.json) | 0.224 | unrelated |  |  |
| [inspirational](../../../traits/instructions/inspirational.json) | 0.220 | unrelated |  |  |
| [introverted](../../../traits/instructions/introverted.json) (expanded) | 0.102 | unrelated |  |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) (expanded) | 0.077 | opposed |  |  |
| [flat](../../../traits/instructions/flat.json) (expanded) | 0.027 | opposed |  |  |
| [submissive](../../../traits/instructions/submissive.json) (expanded) | 0.016 | opposed |  |  |
| [understated](../../../traits/instructions/understated.json) (expanded) | -0.018 | opposed |  |  |
| [laid-back](../../../traits/instructions/laid_back.json) (expanded) | -0.047 | opposed |  |  |

### complacent (cut-off 3, 4 pairs judged)

Gloss: This means accepting one's own work and character without questioning whether they could be better.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.618 | similar | 2 | 2 |
| [self-assured](../../../traits/instructions/self_assured.json) | 0.349 | unrelated | 1 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.286 | unrelated |  |  |
| [body-confident](../../../traits/instructions/body_confident.json) | 0.283 | similar | 1 |  |
| [self-reliant](../../../traits/instructions/self_reliant.json) | 0.265 | unrelated |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) | 0.256 | opposed |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) | 0.250 | unrelated |  |  |
| [uncritical](../../../traits/instructions/uncritical.json) | 0.250 | similar | 1 |  |
| [accountable](../../../traits/instructions/accountable.json) | 0.238 | opposed |  |  |
| [self-blaming](../../../traits/instructions/self_blaming.json) | 0.231 | opposed |  |  |
| [insecure](../../../traits/instructions/insecure.json) (expanded) | 0.211 | opposed |  |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) (expanded) | 0.184 | unrelated |  |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) (expanded) | 0.137 | opposed |  |  |
| [critical](../../../traits/instructions/critical.json) (expanded) | 0.031 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.017 | unrelated |  |  |
| [collaborative](../../../traits/instructions/collaborative.json) (expanded) | -0.005 | unrelated |  |  |

Pair completion for: [accountable](../../../traits/instructions/accountable.json), [self-blaming](../../../traits/instructions/self_blaming.json)

### compliant (cut-off 4, 7 pairs judged)

Gloss: This means obeying rules and requests without resistance or delay.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [obedient](../../../traits/instructions/obedient.json) | 0.531 | similar | 3 | 3 |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.355 | similar | 2 |  |
| [submissive](../../../traits/instructions/submissive.json) | 0.349 | similar | 2 |  |
| [rebellious](../../../traits/instructions/rebellious.json) | 0.296 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) | 0.295 | similar | 2 |  |
| [deferential](../../../traits/instructions/deferential.json) | 0.257 | similar | 2 |  |
| [unchallenging](../../../traits/instructions/unchallenging.json) | 0.256 | unrelated |  |  |
| [polite](../../../traits/instructions/polite.json) | 0.226 | unrelated |  |  |
| [responsible](../../../traits/instructions/responsible.json) | 0.218 | similar | 1 |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.215 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | 0.180 | similar | 2 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) (expanded) | 0.166 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.105 | unrelated |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | 0.038 | opposed |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) (expanded) | 0.027 | opposed |  |  |
| [dominant](../../../traits/instructions/dominant.json) (expanded) | 0.014 | unrelated |  |  |
| [challenging](../../../traits/instructions/challenging.json) (expanded) | -0.048 | unrelated |  |  |

### confirmation biased (cut-off 3, 6 pairs judged)

Gloss: This means seeking out and favoring information that confirms what one already believes.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) | 0.355 | similar | 2 | 2 |
| [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | 0.309 | opposed |  |  |
| [media-trusting](../../../traits/instructions/media_trusting.json) | 0.244 | unrelated |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) | 0.234 | similar | 2 | 2 |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) | 0.230 | similar | 1 |  |
| [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json) | 0.226 | similar | 2 | 2 |
| [media-skeptical](../../../traits/instructions/media_skeptical.json) | 0.212 | unrelated |  |  |
| [partisan](../../../traits/instructions/partisan.json) | 0.199 | similar | 2 | 1 |
| [conformist](../../../traits/instructions/conformist.json) | 0.188 | similar | 1 |  |
| [traditional](../../../traits/instructions/traditional.json) | 0.188 | unrelated |  |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) (expanded) | 0.125 | unrelated |  |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | 0.124 | unrelated |  |  |
| [course-correcting](../../../traits/instructions/course_correcting.json) (expanded) | 0.123 | opposed |  |  |
| [open-minded](../../../traits/instructions/open_minded.json) (expanded) | 0.104 | opposed |  |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) (expanded) | 0.045 | opposed |  |  |
| [innovative](../../../traits/instructions/innovative.json) (expanded) | 0.036 | unrelated |  |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) (expanded) | 0.021 | opposed |  |  |

### conflict averse (cut-off 3, 9 pairs judged)

Gloss: This means stepping back from disagreement and choosing peace over pressing one's own view.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [peaceful](../../../traits/instructions/peaceful.json) | 0.418 | similar | 2 | 2 |
| [pacifist](../../../traits/instructions/pacifist.json) | 0.319 | similar | 1 |  |
| [conciliatory](../../../traits/instructions/conciliatory.json) | 0.281 | similar | 2 | 2 |
| [agreeable](../../../traits/instructions/agreeable.json) | 0.278 | similar | 2 | 2 |
| [guarded](../../../traits/instructions/guarded.json) | 0.276 | unrelated | 2 | 2 |
| [open-minded](../../../traits/instructions/open_minded.json) | 0.269 | similar | 0 |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.259 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) | 0.256 | similar | 2 | 2 |
| [moderate](../../../traits/instructions/moderate.json) | 0.249 | similar | 1 |  |
| [diplomatic](../../../traits/instructions/diplomatic.json) | 0.236 | similar | 1 |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) (expanded) | 0.191 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | 0.130 | opposed |  |  |
| [confrontational](../../../traits/instructions/confrontational.json) (expanded) | 0.117 | opposed |  |  |
| [hawkish](../../../traits/instructions/hawkish.json) (expanded) | 0.109 | opposed |  |  |
| [extremist](../../../traits/instructions/extremist.json) (expanded) | 0.063 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.048 | opposed |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) (expanded) | 0.009 | unrelated |  |  |

### consanguineous (cut-off 3, 4 pairs judged)

Gloss: This means being related by blood to others, sharing common ancestry with one's kin.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [clannish](../../../traits/instructions/clannish.json) | 0.415 | unrelated |  |  |
| [rooted](../../../traits/instructions/rooted.json) | 0.382 | similar | 1 |  |
| [parent](../../../traits/instructions/parent.json) | 0.331 | similar | 1 |  |
| [many siblings](../../../traits/instructions/many_siblings.json) | 0.319 | similar | 1 |  |
| [aristocratic](../../../traits/instructions/aristocratic.json) | 0.295 | similar | 1 |  |
| [new money](../../../traits/instructions/new_money.json) | 0.246 | unrelated |  |  |
| [old money](../../../traits/instructions/old_money.json) | 0.235 | unrelated |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.220 | unrelated |  |  |
| [rootless](../../../traits/instructions/rootless.json) | 0.216 | opposed |  |  |
| [western hemisphere](../../../traits/instructions/western_hemisphere.json) | 0.203 | unrelated |  |  |
| [eastern hemisphere](../../../traits/instructions/eastern_hemisphere.json) (expanded) | 0.167 | unrelated |  |  |
| [childless](../../../traits/instructions/childless.json) (expanded) | 0.164 | opposed |  |  |

### corrupt (cut-off 4, 10 pairs judged)

Gloss: This means lying, cheating, and bending every rule for personal gain, and treating other people's trust as something to exploit rather than honor.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.372 | similar | 2 |  |
| [greedy](../../../traits/instructions/greedy.json) | 0.338 | similar | 2 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.333 | similar | 2 |  |
| [treacherous](../../../traits/instructions/treacherous.json) | 0.302 | similar | 2 |  |
| [evil](../../../traits/instructions/evil.json) | 0.298 | unrelated | 1 |  |
| [deceitful](../../../traits/instructions/deceitful.json) | 0.288 | similar | 2 |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) | 0.283 | similar | 1 |  |
| [moral](../../../traits/instructions/moral.json) | 0.273 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.270 | unrelated | 1 |  |
| [rude](../../../traits/instructions/rude.json) | 0.252 | unrelated |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.241 | similar | 2 |  |
| [fair](../../../traits/instructions/fair.json) (expanded) | 0.207 | opposed |  |  |
| [honorable](../../../traits/instructions/honorable.json) (expanded) | 0.175 | opposed |  |  |
| [loyal](../../../traits/instructions/loyal.json) (expanded) | 0.134 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.115 | opposed |  |  |
| [truthful](../../../traits/instructions/truthful.json) (expanded) | 0.110 | opposed |  |  |
| [good](../../../traits/instructions/good.json) (expanded) | 0.106 | opposed |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.056 | unrelated |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.030 | unrelated | 1 |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.030 | opposed |  |  |

### cruel to animals (cut-off 4, 8 pairs judged)

Gloss: This means inflicting suffering on animals deliberately and taking no care to spare them pain.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [cruel](../../../traits/instructions/cruel.json) | 0.544 | similar | 2 |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) | 0.433 | unrelated | 1 |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.397 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.383 | similar | 2 |  |
| [evil](../../../traits/instructions/evil.json) | 0.326 | similar | 1 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.298 | unrelated | 1 |  |
| [merciful](../../../traits/instructions/merciful.json) | 0.292 | opposed |  |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.273 | similar | 2 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.265 | similar | 0 |  |
| [callous](../../../traits/instructions/callous.json) | 0.265 | similar | 1 |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.157 | opposed |  |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.136 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.127 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.037 | opposed |  |  |
| [good](../../../traits/instructions/good.json) (expanded) | 0.026 | opposed |  |  |

Pair completion for: [merciful](../../../traits/instructions/merciful.json)

### cultured (cut-off 3, 6 pairs judged)

Gloss: This means carrying polished manners and a trained eye for art, music, and letters, speaking with the ease of a deep education, and choosing well in matters of taste.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dignified](../../../traits/instructions/dignified.json) | 0.345 | unrelated |  |  |
| [educated](../../../traits/instructions/educated.json) | 0.330 | similar | 1 |  |
| [upper-class](../../../traits/instructions/upper_class.json) | 0.329 | unrelated |  |  |
| [old money](../../../traits/instructions/old_money.json) | 0.304 | unrelated |  |  |
| [highbrow](../../../traits/instructions/highbrow.json) | 0.303 | similar | 2 | 2 |
| [artistic](../../../traits/instructions/artistic.json) | 0.298 | unrelated |  |  |
| [erudite](../../../traits/instructions/erudite.json) | 0.297 | similar | 2 | 2 |
| [polite](../../../traits/instructions/polite.json) | 0.293 | unrelated | 1 |  |
| [aesthete](../../../traits/instructions/aesthete.json) | 0.292 | similar | 2 | 2 |
| [epicurean](../../../traits/instructions/epicurean.json) | 0.284 | similar | 2 | 2 |
| [philistine](../../../traits/instructions/philistine.json) (expanded) | 0.206 | opposed |  |  |
| [lowbrow](../../../traits/instructions/lowbrow.json) (expanded) | 0.151 | opposed |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) (expanded) | 0.150 | opposed |  |  |
| [unschooled](../../../traits/instructions/unschooled.json) (expanded) | 0.110 | opposed |  |  |
| [new money](../../../traits/instructions/new_money.json) (expanded) | 0.087 | unrelated |  |  |
| [working-class](../../../traits/instructions/working_class.json) (expanded) | 0.082 | unrelated |  |  |
| [spartan](../../../traits/instructions/spartan.json) (expanded) | 0.060 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.054 | opposed |  |  |

### cursory (cut-off 4, 8 pairs judged)

Gloss: This means doing things quickly and without attending to detail or substance.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [sloppy](../../../traits/instructions/sloppy.json) | 0.485 | similar | 2 |  |
| [hurried](../../../traits/instructions/hurried.json) | 0.385 | similar | 1 |  |
| [superficial](../../../traits/instructions/superficial.json) | 0.346 | similar | 2 |  |
| [careless](../../../traits/instructions/careless.json) | 0.339 | similar | 2 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.302 | similar | 1 |  |
| [efficient](../../../traits/instructions/efficient.json) | 0.300 | unrelated |  |  |
| [approximate](../../../traits/instructions/approximate.json) | 0.250 | similar | 2 |  |
| [unreflective](../../../traits/instructions/unreflective.json) | 0.243 | unrelated |  |  |
| [brash](../../../traits/instructions/brash.json) | 0.240 | similar | 1 |  |
| [short-term oriented](../../../traits/instructions/short_term_oriented.json) | 0.234 | similar | 1 |  |
| [unhurried](../../../traits/instructions/unhurried.json) (expanded) | 0.141 | opposed |  |  |
| [meticulous](../../../traits/instructions/meticulous.json) (expanded) | 0.078 | opposed |  |  |
| [thorough](../../../traits/instructions/thorough.json) (expanded) | 0.058 | opposed |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | 0.024 | opposed |  |  |
| [long-term oriented](../../../traits/instructions/long_term_oriented.json) (expanded) | 0.006 | opposed |  |  |
| [circumspect](../../../traits/instructions/circumspect.json) (expanded) | -0.037 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | -0.066 | opposed |  |  |
| [introspective](../../../traits/instructions/introspective.json) (expanded) | -0.132 | unrelated |  |  |

### death denying (cut-off 3, 10 pairs judged)

Gloss: This means refusing to acknowledge that death is real and will come for oneself and others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [death-fearing](../../../traits/instructions/death_fearing.json) | 0.415 | unrelated | 1 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.388 | opposed |  |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.274 | similar | 0 |  |
| [health-negligent](../../../traits/instructions/health_negligent.json) | 0.214 | similar | 1 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) | 0.214 | unrelated | 0 |  |
| [despairing](../../../traits/instructions/despairing.json) | 0.192 | unrelated |  |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) | 0.181 | unrelated | 0 |  |
| [foolish](../../../traits/instructions/foolish.json) | 0.174 | similar | 0 |  |
| [defeatist](../../../traits/instructions/defeatist.json) | 0.165 | unrelated | 0 |  |
| [procrastinating](../../../traits/instructions/procrastinating.json) | 0.163 | unrelated | 0 |  |
| [self-starting](../../../traits/instructions/self_starting.json) (expanded) | 0.117 | opposed |  |  |
| [existentialist](../../../traits/instructions/existentialist.json) (expanded) | 0.114 | opposed |  |  |
| [persevering](../../../traits/instructions/persevering.json) (expanded) | 0.106 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.062 | opposed |  |  |
| [health-conscious](../../../traits/instructions/health_conscious.json) (expanded) | 0.060 | opposed |  |  |
| [news-junkie](../../../traits/instructions/news_junkie.json) (expanded) | 0.045 | opposed |  |  |
| [constructivist](../../../traits/instructions/constructivist.json) (expanded) | 0.041 | unrelated | 0 |  |
| [essentialist](../../../traits/instructions/essentialist.json) (expanded) | 0.015 | unrelated | 0 |  |
| [wise](../../../traits/instructions/wise.json) (expanded) | 0.012 | opposed |  |  |

### defiant (cut-off 4, 8 pairs judged)

Gloss: This means resisting or refusing to obey authority and demands.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rebellious](../../../traits/instructions/rebellious.json) | 0.576 | similar | 3 | 3 |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.288 | unrelated | 2 |  |
| [obedient](../../../traits/instructions/obedient.json) | 0.282 | opposed |  |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.244 | unrelated | 1 |  |
| [subversive](../../../traits/instructions/subversive.json) | 0.240 | similar | 2 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.231 | similar | 2 |  |
| [heterodox](../../../traits/instructions/heterodox.json) | 0.212 | similar | 1 |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.207 | similar | 1 |  |
| [pacifist](../../../traits/instructions/pacifist.json) | 0.205 | unrelated |  |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.204 | unrelated |  |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | 0.177 | unrelated | 1 |  |
| [orthodox](../../../traits/instructions/orthodox.json) (expanded) | 0.104 | opposed |  |  |
| [conformist](../../../traits/instructions/conformist.json) (expanded) | 0.048 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.027 | opposed |  |  |
| [hawkish](../../../traits/instructions/hawkish.json) (expanded) | 0.026 | unrelated |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.010 | unrelated |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | -0.001 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | -0.035 | opposed |  |  |

### definitive (cut-off 4, 4 pairs judged)

Gloss: This means settling matters conclusively and having one's word be final.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [settled](../../../traits/instructions/settled.json) | 0.336 | unrelated |  |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) | 0.334 | similar | 2 |  |
| [clear](../../../traits/instructions/clear.json) | 0.279 | similar | 1 |  |
| [married](../../../traits/instructions/married.json) | 0.256 | unrelated |  |  |
| [decisive](../../../traits/instructions/decisive.json) | 0.252 | similar | 2 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.250 | unrelated |  |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.222 | similar | 2 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.190 | unrelated |  |  |
| [accountable](../../../traits/instructions/accountable.json) | 0.189 | unrelated |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) | 0.184 | unrelated |  |  |
| [single](../../../traits/instructions/single.json) (expanded) | 0.161 | unrelated |  |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) (expanded) | 0.063 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.060 | unrelated |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | 0.041 | opposed |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) (expanded) | 0.021 | opposed |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | 0.018 | unrelated |  |  |
| [indecisive](../../../traits/instructions/indecisive.json) (expanded) | 0.006 | opposed |  |  |

### deflecting (cut-off 4, 10 pairs judged)

Gloss: This means turning aside questions or duties rather than meeting them directly.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [absentee](../../../traits/instructions/absentee.json) | 0.302 | similar | 1 |  |
| [lazy](../../../traits/instructions/lazy.json) | 0.295 | similar | 1 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) | 0.295 | similar | 1 |  |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.288 | similar | 2 |  |
| [dismissive](../../../traits/instructions/dismissive.json) | 0.283 | similar | 1 |  |
| [procrastinating](../../../traits/instructions/procrastinating.json) | 0.279 | similar | 1 |  |
| [careless](../../../traits/instructions/careless.json) | 0.242 | similar | 1 |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.242 | similar | 2 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.238 | similar | 2 |  |
| [cowardly](../../../traits/instructions/cowardly.json) | 0.235 | similar | 1 |  |
| [self-starting](../../../traits/instructions/self_starting.json) (expanded) | 0.105 | opposed |  |  |
| [brave](../../../traits/instructions/brave.json) (expanded) | 0.066 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.022 | opposed |  |  |
| [news-junkie](../../../traits/instructions/news_junkie.json) (expanded) | 0.003 | unrelated |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | -0.028 | opposed |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | -0.034 | opposed |  |  |
| [supportive](../../../traits/instructions/supportive.json) (expanded) | -0.092 | opposed |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | -0.098 | opposed |  |  |

### degenerate (cut-off 4, 8 pairs judged)

Gloss: This means living for vice and indulgence, chasing every appetite without shame, and treating decency and restraint as things to mock or break.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [hedonistic](../../../traits/instructions/hedonistic.json) | 0.335 | similar | 2 |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) | 0.311 | similar | 2 |  |
| [gluttonous](../../../traits/instructions/gluttonous.json) | 0.290 | similar | 2 |  |
| [permissive](../../../traits/instructions/permissive.json) | 0.281 | similar | 2 |  |
| [promiscuous](../../../traits/instructions/promiscuous.json) | 0.273 | similar | 2 |  |
| [lustful](../../../traits/instructions/lustful.json) | 0.245 | similar | 1 |  |
| [puritanical](../../../traits/instructions/puritanical.json) | 0.233 | opposed |  |  |
| [spartan](../../../traits/instructions/spartan.json) | 0.229 | opposed |  |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.221 | similar | 1 |  |
| [epicurean](../../../traits/instructions/epicurean.json) | 0.220 | unrelated | 1 |  |
| [ascetic](../../../traits/instructions/ascetic.json) (expanded) | 0.199 | opposed |  |  |
| [chaste](../../../traits/instructions/chaste.json) (expanded) | 0.188 | opposed |  |  |
| [abstemious](../../../traits/instructions/abstemious.json) (expanded) | 0.144 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.104 | opposed |  |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) (expanded) | 0.092 | opposed |  |  |

### democratic (cut-off 3, 5 pairs judged)

Gloss: This means holding that power should rest with the people and their elected representatives.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [populist](../../../traits/instructions/populist.json) | 0.335 | similar | 2 | 2 |
| [meritocratic](../../../traits/instructions/meritocratic.json) | 0.253 | similar | 1 |  |
| [technocratic](../../../traits/instructions/technocratic.json) | 0.244 | unrelated |  |  |
| [socialist](../../../traits/instructions/socialist.json) | 0.205 | unrelated |  |  |
| [autonomy-respecting](../../../traits/instructions/autonomy_respecting.json) | 0.204 | similar | 1 |  |
| [aristocratic](../../../traits/instructions/aristocratic.json) | 0.202 | opposed |  |  |
| [elitist](../../../traits/instructions/elitist.json) | 0.201 | opposed |  |  |
| [paternalistic](../../../traits/instructions/paternalistic.json) | 0.199 | opposed |  |  |
| [metaphysical libertarian](../../../traits/instructions/metaphysical_libertarian.json) | 0.192 | unrelated | 0 |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.185 | unrelated |  |  |
| [capitalist](../../../traits/instructions/capitalist.json) (expanded) | 0.184 | unrelated |  |  |
| [egalitarian](../../../traits/instructions/egalitarian.json) (expanded) | 0.151 | similar | 1 |  |
| [determinist](../../../traits/instructions/determinist.json) (expanded) | 0.102 | opposed |  |  |

Pair completion for: [aristocratic](../../../traits/instructions/aristocratic.json)

### devout (cut-off 3, 7 pairs judged)

Gloss: This means holding religious faith as central to one's life and practicing it with sincere commitment.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [religious](../../../traits/instructions/religious.json) | 0.420 | similar | 2 | 2 |
| [fundamentalist](../../../traits/instructions/fundamentalist.json) | 0.277 | unrelated |  |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.274 | unrelated |  |  |
| [spiritual](../../../traits/instructions/spiritual.json) | 0.265 | similar | 2 | 2 |
| [orthodox](../../../traits/instructions/orthodox.json) | 0.252 | similar | 1 |  |
| [reverent](../../../traits/instructions/reverent.json) | 0.242 | similar | 2 | 2 |
| [rooted](../../../traits/instructions/rooted.json) | 0.241 | similar | 1 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.234 | similar | 0 |  |
| [sectarian](../../../traits/instructions/sectarian.json) | 0.225 | unrelated |  |  |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.222 | similar | 1 |  |
| [secular](../../../traits/instructions/secular.json) (expanded) | 0.187 | opposed |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.162 | unrelated |  |  |
| [materialistic](../../../traits/instructions/materialistic.json) (expanded) | 0.101 | opposed |  |  |
| [rootless](../../../traits/instructions/rootless.json) (expanded) | 0.086 | opposed |  |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) (expanded) | 0.078 | opposed |  |  |
| [heterodox](../../../traits/instructions/heterodox.json) (expanded) | 0.074 | opposed |  |  |
| [irreverent](../../../traits/instructions/irreverent.json) (expanded) | 0.065 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.005 | opposed |  |  |

### diffident (cut-off 4, 9 pairs judged)

Gloss: This means doubting one's own worth and capabilities.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [insecure](../../../traits/instructions/insecure.json) | 0.578 | similar | 3 | 3 |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) | 0.388 | similar | 1 |  |
| [despairing](../../../traits/instructions/despairing.json) | 0.339 | similar | 1 |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) | 0.326 | similar | 1 |  |
| [self-assured](../../../traits/instructions/self_assured.json) | 0.322 | opposed |  |  |
| [discouraging](../../../traits/instructions/discouraging.json) | 0.321 | similar | 1 |  |
| [uncertain](../../../traits/instructions/uncertain.json) | 0.315 | similar | 2 |  |
| [self-critical](../../../traits/instructions/self_critical.json) | 0.265 | similar | 2 |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) | 0.260 | similar | 1 |  |
| [dependent](../../../traits/instructions/dependent.json) | 0.255 | similar | 1 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) (expanded) | 0.230 | opposed |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) (expanded) | 0.186 | opposed |  |  |
| [body-confident](../../../traits/instructions/body_confident.json) (expanded) | 0.145 | opposed |  |  |
| [confident](../../../traits/instructions/confident.json) (expanded) | 0.120 | opposed |  |  |
| [independent](../../../traits/instructions/independent.json) (expanded) | 0.109 | opposed |  |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) (expanded) | 0.096 | opposed |  |  |
| [encouraging](../../../traits/instructions/encouraging.json) (expanded) | 0.081 | unrelated |  |  |

### disengaged (cut-off 3, 9 pairs judged)

Gloss: This means pulling back from commitments and involvement, holding oneself apart from the work and people at hand, and giving nothing of one's own energy or stake to what goes on.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [hands-off](../../../traits/instructions/hands_off.json) | 0.385 | similar | 2 | 2 |
| [detached](../../../traits/instructions/detached.json) | 0.320 | similar | 2 | 2 |
| [absentee](../../../traits/instructions/absentee.json) | 0.308 | similar | 2 | 2 |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.289 | similar | 2 | 2 |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.273 | similar | 2 | 1 |
| [reserved](../../../traits/instructions/reserved.json) | 0.247 | unrelated | 1 |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.233 | unrelated | 1 |  |
| [unplugged](../../../traits/instructions/unplugged.json) | 0.227 | unrelated | 0 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) | 0.224 | unrelated |  |  |
| [lazy](../../../traits/instructions/lazy.json) | 0.222 | unrelated | 2 | 2 |
| [hands-on](../../../traits/instructions/hands_on.json) (expanded) | 0.208 | opposed |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) (expanded) | 0.042 | opposed |  |  |
| [news-junkie](../../../traits/instructions/news_junkie.json) (expanded) | -0.008 | unrelated |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | -0.019 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | -0.028 | opposed |  |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) (expanded) | -0.066 | opposed |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | -0.104 | opposed |  |  |

### disingenuous (cut-off 4, 7 pairs judged)

Gloss: This means saying things one does not believe or presenting oneself falsely to deceive others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [deceitful](../../../traits/instructions/deceitful.json) | 0.466 | similar | 3 | 3 |
| [dishonest](../../../traits/instructions/dishonest.json) | 0.418 | similar | 2 |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | 0.307 | similar | 2 |  |
| [truthful](../../../traits/instructions/truthful.json) | 0.287 | opposed |  |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | 0.256 | similar | 2 |  |
| [glib](../../../traits/instructions/glib.json) | 0.248 | similar | 2 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.247 | unrelated | 1 |  |
| [ironic](../../../traits/instructions/ironic.json) | 0.244 | unrelated | 1 |  |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.233 | unrelated |  |  |
| [confabulatory](../../../traits/instructions/confabulatory.json) | 0.211 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.187 | unrelated |  |  |
| [honest](../../../traits/instructions/honest.json) (expanded) | 0.182 | opposed |  |  |
| [sincere](../../../traits/instructions/sincere.json) (expanded) | 0.172 | opposed |  |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) (expanded) | 0.116 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.092 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) (expanded) | 0.026 | opposed |  |  |

### disloyal (cut-off 4, 5 pairs judged)

Gloss: This means betraying the trust of those one is bound to serve or support.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [treacherous](../../../traits/instructions/treacherous.json) | 0.543 | similar | 3 | 3 |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | 0.461 | similar | 2 |  |
| [unreliable](../../../traits/instructions/unreliable.json) | 0.344 | similar | 1 |  |
| [loyal](../../../traits/instructions/loyal.json) | 0.303 | opposed |  |  |
| [rebellious](../../../traits/instructions/rebellious.json) | 0.252 | unrelated |  |  |
| [deceitful](../../../traits/instructions/deceitful.json) | 0.251 | unrelated |  |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.233 | unrelated |  |  |
| [amoral](../../../traits/instructions/amoral.json) | 0.228 | similar | 1 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.228 | opposed |  |  |
| [moral](../../../traits/instructions/moral.json) | 0.226 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) (expanded) | 0.218 | opposed |  |  |
| [obedient](../../../traits/instructions/obedient.json) (expanded) | 0.149 | unrelated |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.149 | similar | 1 |  |
| [dependable](../../../traits/instructions/dependable.json) (expanded) | 0.144 | opposed |  |  |
| [truthful](../../../traits/instructions/truthful.json) (expanded) | 0.124 | unrelated |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.043 | unrelated |  |  |

### dissenting (cut-off 4, 7 pairs judged)

Gloss: This means holding a view that runs against the majority or official position and saying so openly, even when the room agrees on the other side.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [contrarian](../../../traits/instructions/contrarian.json) | 0.467 | similar | 2 |  |
| [heterodox](../../../traits/instructions/heterodox.json) | 0.389 | similar | 2 |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.338 | similar | 2 |  |
| [exclusivist](../../../traits/instructions/exclusivist.json) | 0.308 | unrelated |  |  |
| [open-minded](../../../traits/instructions/open_minded.json) | 0.284 | similar | 1 |  |
| [partisan](../../../traits/instructions/partisan.json) | 0.271 | unrelated | 1 |  |
| [opinionated](../../../traits/instructions/opinionated.json) | 0.270 | similar | 2 |  |
| [media-skeptical](../../../traits/instructions/media_skeptical.json) | 0.251 | unrelated |  |  |
| [critical](../../../traits/instructions/critical.json) | 0.248 | similar | 2 |  |
| [conformist](../../../traits/instructions/conformist.json) | 0.242 | opposed |  |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) (expanded) | 0.239 | opposed |  |  |
| [pluralist](../../../traits/instructions/pluralist.json) (expanded) | 0.227 | unrelated |  |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) (expanded) | 0.216 | opposed |  |  |
| [orthodox](../../../traits/instructions/orthodox.json) (expanded) | 0.214 | opposed |  |  |
| [uncritical](../../../traits/instructions/uncritical.json) (expanded) | 0.160 | opposed |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) (expanded) | 0.156 | opposed |  |  |
| [media-trusting](../../../traits/instructions/media_trusting.json) (expanded) | 0.101 | unrelated |  |  |

### dog averse (cut-off 3, 2 pairs judged)

Gloss: This means finding dogs unpleasant and keeping away from them.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dog-person](../../../traits/instructions/dog_person.json) | 0.412 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) | 0.340 | unrelated | 1 |  |
| [cat-person](../../../traits/instructions/cat_person.json) | 0.315 | unrelated | 1 |  |
| [unhappily-partnered](../../../traits/instructions/unhappily_partnered.json) | 0.279 | unrelated |  |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.268 | unrelated |  |  |
| [squeamish](../../../traits/instructions/squeamish.json) | 0.246 | unrelated |  |  |
| [unpopular](../../../traits/instructions/unpopular.json) | 0.229 | unrelated |  |  |
| [homophobic](../../../traits/instructions/homophobic.json) | 0.227 | unrelated |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) | 0.211 | unrelated |  |  |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.200 | unrelated |  |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) (expanded) | 0.184 | opposed |  |  |
| [strong-stomached](../../../traits/instructions/strong_stomached.json) (expanded) | 0.142 | unrelated |  |  |
| [happily-partnered](../../../traits/instructions/happily_partnered.json) (expanded) | 0.091 | unrelated |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | 0.081 | unrelated |  |  |
| [gay-affirming](../../../traits/instructions/gay_affirming.json) (expanded) | 0.037 | unrelated |  |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.026 | unrelated |  |  |
| [helpful](../../../traits/instructions/helpful.json) (expanded) | -0.061 | unrelated |  |  |

### driven (cut-off 3, 8 pairs judged)

Gloss: This means pursuing goals with single-minded focus and refusing to settle for less than one's full potential.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [persevering](../../../traits/instructions/persevering.json) | 0.412 | similar | 2 | 2 |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.357 | similar | 2 | 2 |
| [focused](../../../traits/instructions/focused.json) | 0.303 | similar | 2 | 1 |
| [strict](../../../traits/instructions/strict.json) | 0.302 | similar | 1 |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.282 | unrelated | 1 |  |
| [rigid](../../../traits/instructions/rigid.json) | 0.258 | unrelated |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) | 0.253 | similar | 2 | 2 |
| [maximizing](../../../traits/instructions/maximizing.json) | 0.251 | similar | 2 | 1 |
| [peaceful](../../../traits/instructions/peaceful.json) | 0.243 | opposed |  |  |
| [defeatist](../../../traits/instructions/defeatist.json) | 0.240 | opposed |  |  |
| [satisficing](../../../traits/instructions/satisficing.json) (expanded) | 0.177 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | 0.175 | unrelated | 1 |  |
| [unambitious](../../../traits/instructions/unambitious.json) (expanded) | 0.162 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | 0.073 | unrelated |  |  |
| [lenient](../../../traits/instructions/lenient.json) (expanded) | 0.018 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | -0.005 | opposed |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | -0.008 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | -0.077 | opposed |  |  |

### emotionally blunt (cut-off 3, 8 pairs judged)

Gloss: This means missing the emotional weight in situations and responding to feelings without regard for their impact.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.435 | similar | 1 |  |
| [unsentimental](../../../traits/instructions/unsentimental.json) | 0.339 | unrelated | 1 |  |
| [emotionally-inarticulate](../../../traits/instructions/emotionally_inarticulate.json) | 0.316 | unrelated | 1 |  |
| [callous](../../../traits/instructions/callous.json) | 0.299 | similar | 2 | 2 |
| [detached](../../../traits/instructions/detached.json) | 0.294 | similar | 1 |  |
| [dispassionate](../../../traits/instructions/dispassionate.json) | 0.252 | similar | 1 |  |
| [unreflective](../../../traits/instructions/unreflective.json) | 0.244 | unrelated |  |  |
| [humorless](../../../traits/instructions/humorless.json) | 0.241 | unrelated |  |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.241 | similar | 1 |  |
| [emotional](../../../traits/instructions/emotional.json) | 0.241 | unrelated |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) (expanded) | 0.229 | opposed |  |  |
| [emotionally-articulate](../../../traits/instructions/emotionally_articulate.json) (expanded) | 0.204 | opposed |  |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.193 | opposed |  |  |
| [sentimental](../../../traits/instructions/sentimental.json) (expanded) | 0.127 | opposed |  |  |
| [passionate](../../../traits/instructions/passionate.json) (expanded) | 0.014 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | -0.029 | similar | 0 |  |
| [witty](../../../traits/instructions/witty.json) (expanded) | -0.033 | unrelated |  |  |
| [introspective](../../../traits/instructions/introspective.json) (expanded) | -0.060 | unrelated |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | -0.080 | opposed |  |  |

### emotionally secure (cut-off 3, 8 pairs judged)

Gloss: This means trusting one's emotional responses and maintaining equilibrium through life's ups and downs.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [even-tempered](../../../traits/instructions/even_tempered.json) | 0.331 | similar | 2 | 2 |
| [unflappable](../../../traits/instructions/unflappable.json) | 0.327 | similar | 2 | 2 |
| [composed](../../../traits/instructions/composed.json) | 0.326 | similar | 2 | 2 |
| [stoic](../../../traits/instructions/stoic.json) | 0.299 | similar | 2 | 2 |
| [serene](../../../traits/instructions/serene.json) | 0.287 | similar | 2 | 2 |
| [emotional](../../../traits/instructions/emotional.json) | 0.259 | unrelated |  |  |
| [resilient](../../../traits/instructions/resilient.json) | 0.258 | similar | 2 | 2 |
| [trusting](../../../traits/instructions/trusting.json) | 0.253 | unrelated |  |  |
| [emotionally-articulate](../../../traits/instructions/emotionally_articulate.json) | 0.245 | similar | 1 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.241 | similar | 1 |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.174 | opposed |  |  |
| [temperamental](../../../traits/instructions/temperamental.json) (expanded) | 0.153 | opposed |  |  |
| [emotionally-inarticulate](../../../traits/instructions/emotionally_inarticulate.json) (expanded) | 0.136 | opposed |  |  |
| [fragile](../../../traits/instructions/fragile.json) (expanded) | 0.101 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.068 | opposed |  |  |
| [flustered](../../../traits/instructions/flustered.json) (expanded) | 0.051 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.011 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | -0.054 | unrelated |  |  |

### emotionally vague (cut-off 3, 5 pairs judged)

Gloss: This means expressing feelings in ways that leave one's emotional state uncertain or hard to pin down.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [uncertain](../../../traits/instructions/uncertain.json) | 0.428 | unrelated |  |  |
| [emotionally-inarticulate](../../../traits/instructions/emotionally_inarticulate.json) | 0.415 | similar | 2 | 2 |
| [enigmatic](../../../traits/instructions/enigmatic.json) | 0.384 | similar | 2 | 2 |
| [vague](../../../traits/instructions/vague.json) | 0.345 | similar | 2 | 2 |
| [reserved](../../../traits/instructions/reserved.json) | 0.339 | unrelated | 1 |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.337 | opposed |  |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) | 0.328 | unrelated |  |  |
| [indecisive](../../../traits/instructions/indecisive.json) | 0.295 | unrelated |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) | 0.284 | similar | 2 | 1 |
| [emotionally-articulate](../../../traits/instructions/emotionally_articulate.json) | 0.275 | opposed |  |  |
| [clear](../../../traits/instructions/clear.json) (expanded) | 0.156 | opposed |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) (expanded) | 0.069 | unrelated |  |  |
| [confident](../../../traits/instructions/confident.json) (expanded) | 0.063 | unrelated |  |  |
| [precise](../../../traits/instructions/precise.json) (expanded) | 0.057 | opposed |  |  |
| [decisive](../../../traits/instructions/decisive.json) (expanded) | 0.020 | unrelated |  |  |

### evasive (cut-off 4, 9 pairs judged)

Gloss: This means sidestepping direct answers and keeping one's commitments unclear.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.437 | similar | 2 |  |
| [indecisive](../../../traits/instructions/indecisive.json) | 0.379 | similar | 2 |  |
| [vague](../../../traits/instructions/vague.json) | 0.379 | similar | 2 |  |
| [enigmatic](../../../traits/instructions/enigmatic.json) | 0.365 | similar | 2 |  |
| [opaque](../../../traits/instructions/opaque.json) | 0.348 | similar | 2 |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) | 0.298 | unrelated | 1 |  |
| [unchallenging](../../../traits/instructions/unchallenging.json) | 0.278 | opposed |  |  |
| [glib](../../../traits/instructions/glib.json) | 0.262 | unrelated |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) | 0.253 | similar | 1 |  |
| [unreliable](../../../traits/instructions/unreliable.json) | 0.246 | similar | 1 |  |
| [honest](../../../traits/instructions/honest.json) (expanded) | 0.156 | opposed |  |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | 0.133 | opposed |  |  |
| [decisive](../../../traits/instructions/decisive.json) (expanded) | 0.127 | opposed |  |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) (expanded) | 0.102 | opposed |  |  |
| [dependable](../../../traits/instructions/dependable.json) (expanded) | 0.101 | opposed |  |  |
| [precise](../../../traits/instructions/precise.json) (expanded) | 0.024 | opposed |  |  |
| [challenging](../../../traits/instructions/challenging.json) (expanded) | 0.024 | unrelated | 0 |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.017 | opposed |  |  |

### evidence based (cut-off 4, 9 pairs judged)

Gloss: This means grounding thinking and decisions in evidence and research rather than assumption or intuition.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [data-driven](../../../traits/instructions/data_driven.json) | 0.441 | similar | 3 | 3 |
| [empirical](../../../traits/instructions/empirical.json) | 0.347 | similar | 2 |  |
| [course-correcting](../../../traits/instructions/course_correcting.json) | 0.310 | similar | 1 |  |
| [experiential](../../../traits/instructions/experiential.json) | 0.278 | similar | 2 |  |
| [secular](../../../traits/instructions/secular.json) | 0.275 | similar | 2 |  |
| [skeptical](../../../traits/instructions/skeptical.json) | 0.269 | similar | 2 |  |
| [logical](../../../traits/instructions/logical.json) | 0.260 | similar | 1 |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.242 | similar | 2 |  |
| [science-trusting](../../../traits/instructions/science_trusting.json) | 0.241 | similar | 2 |  |
| [practical](../../../traits/instructions/practical.json) | 0.238 | unrelated |  |  |
| [religious](../../../traits/instructions/religious.json) (expanded) | 0.219 | opposed |  |  |
| [theoretical](../../../traits/instructions/theoretical.json) (expanded) | 0.212 | unrelated |  |  |
| [illogical](../../../traits/instructions/illogical.json) (expanded) | 0.133 | opposed |  |  |
| [speculative](../../../traits/instructions/speculative.json) (expanded) | 0.130 | opposed |  |  |
| [science-skeptical](../../../traits/instructions/science_skeptical.json) (expanded) | 0.129 | opposed |  |  |
| [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json) (expanded) | 0.101 | opposed |  |  |
| [anecdotal](../../../traits/instructions/anecdotal.json) (expanded) | 0.092 | opposed |  |  |
| [credulous](../../../traits/instructions/credulous.json) (expanded) | 0.090 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | 0.011 | opposed |  |  |

### exact (cut-off 4, 10 pairs judged)

Gloss: This means working with precision, getting details right and speaking without error or vagueness.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [precise](../../../traits/instructions/precise.json) | 0.573 | similar | 3 | 3 |
| [accurate](../../../traits/instructions/accurate.json) | 0.476 | similar | 3 | 3 |
| [perfectionist](../../../traits/instructions/perfectionist.json) | 0.430 | similar | 2 |  |
| [meticulous](../../../traits/instructions/meticulous.json) | 0.425 | similar | 3 | 3 |
| [technical](../../../traits/instructions/technical.json) | 0.310 | similar | 2 |  |
| [detail-oriented](../../../traits/instructions/detail_oriented.json) | 0.305 | similar | 2 |  |
| [formal](../../../traits/instructions/formal.json) | 0.297 | similar | 1 |  |
| [focused](../../../traits/instructions/focused.json) | 0.271 | similar | 1 |  |
| [concise](../../../traits/instructions/concise.json) | 0.271 | similar | 1 |  |
| [clear](../../../traits/instructions/clear.json) | 0.260 | similar | 2 |  |
| [inaccurate](../../../traits/instructions/inaccurate.json) (expanded) | 0.225 | opposed |  |  |
| [sloppy](../../../traits/instructions/sloppy.json) (expanded) | 0.147 | opposed |  |  |
| [verbose](../../../traits/instructions/verbose.json) (expanded) | 0.144 | unrelated |  |  |
| [vague](../../../traits/instructions/vague.json) (expanded) | 0.133 | opposed |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) (expanded) | 0.063 | opposed |  |  |
| [big-picture](../../../traits/instructions/big_picture.json) (expanded) | 0.054 | opposed |  |  |
| [casual](../../../traits/instructions/casual.json) (expanded) | 0.040 | opposed |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | 0.004 | opposed |  |  |

### fickle (cut-off 3, 9 pairs judged)

Gloss: This means shifting one's affections and commitments without warning or consistency.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [erratic](../../../traits/instructions/erratic.json) | 0.402 | similar | 2 | 1 |
| [treacherous](../../../traits/instructions/treacherous.json) | 0.394 | similar | 2 | 1 |
| [mercurial](../../../traits/instructions/mercurial.json) | 0.377 | similar | 2 | 2 |
| [unreliable](../../../traits/instructions/unreliable.json) | 0.326 | similar | 2 | 2 |
| [promiscuous](../../../traits/instructions/promiscuous.json) | 0.270 | similar | 1 |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) | 0.267 | unrelated | 1 |  |
| [job-hopping](../../../traits/instructions/job_hopping.json) | 0.258 | similar | 2 | 1 |
| [brand-agnostic](../../../traits/instructions/brand_agnostic.json) | 0.250 | similar | 2 | 2 |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | 0.249 | similar | 1 |  |
| [temperamental](../../../traits/instructions/temperamental.json) | 0.237 | unrelated |  |  |
| [loyal](../../../traits/instructions/loyal.json) (expanded) | 0.195 | opposed |  |  |
| [dependable](../../../traits/instructions/dependable.json) (expanded) | 0.108 | opposed |  |  |
| [company-loyal](../../../traits/instructions/company_loyal.json) (expanded) | 0.107 | opposed |  |  |
| [steady](../../../traits/instructions/steady.json) (expanded) | 0.101 | opposed |  |  |
| [brand-loyal](../../../traits/instructions/brand_loyal.json) (expanded) | 0.063 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) (expanded) | 0.043 | opposed |  |  |
| [even-tempered](../../../traits/instructions/even_tempered.json) (expanded) | -0.007 | unrelated |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) (expanded) | -0.008 | opposed |  |  |

### flamboyant (cut-off 3, 7 pairs judged)

Gloss: This means dressing and presenting oneself in bold, showy, extravagant ways that draw attention and stand out.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [attention-seeking](../../../traits/instructions/attention_seeking.json) | 0.354 | similar | 2 | 2 |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.341 | similar | 2 | 2 |
| [extravagant](../../../traits/instructions/extravagant.json) | 0.321 | similar | 1 |  |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.308 | similar | 1 |  |
| [eccentric](../../../traits/instructions/eccentric.json) | 0.291 | similar | 1 |  |
| [grandiose](../../../traits/instructions/grandiose.json) | 0.290 | unrelated |  |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.278 | similar | 1 |  |
| [fashionable](../../../traits/instructions/fashionable.json) | 0.270 | unrelated |  |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.267 | unrelated |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.249 | unrelated | 1 |  |
| [feminine](../../../traits/instructions/feminine.json) (expanded) | 0.222 | unrelated |  |  |
| [unfashionable](../../../traits/instructions/unfashionable.json) (expanded) | 0.221 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.088 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.071 | opposed |  |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) (expanded) | 0.054 | opposed |  |  |
| [frugal](../../../traits/instructions/frugal.json) (expanded) | 0.030 | opposed |  |  |
| [conventional](../../../traits/instructions/conventional.json) (expanded) | -0.006 | opposed |  |  |

### flaming (cut-off 3, 9 pairs judged)

Gloss: This means being flamboyantly gay and unapologetically camp, with extravagant gestures, theatrical flourishes, playful innuendo, and a love of spectacle that colors every remark and entrance.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [theatrical](../../../traits/instructions/theatrical.json) | 0.339 | similar | 2 | 2 |
| [goofy](../../../traits/instructions/goofy.json) | 0.311 | similar | 1 |  |
| [gay](../../../traits/instructions/gay.json) | 0.308 | similar | 1 |  |
| [flirty](../../../traits/instructions/flirty.json) | 0.274 | similar | 1 |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.264 | opposed |  |  |
| [gay-affirming](../../../traits/instructions/gay_affirming.json) | 0.254 | unrelated | 0 |  |
| [feminine](../../../traits/instructions/feminine.json) | 0.246 | unrelated | 1 |  |
| [sassy](../../../traits/instructions/sassy.json) | 0.244 | similar | 1 |  |
| [whimsical](../../../traits/instructions/whimsical.json) | 0.230 | similar | 1 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.223 | similar | 2 | 1 |
| [straight](../../../traits/instructions/straight.json) (expanded) | 0.192 | opposed |  |  |
| [homophobic](../../../traits/instructions/homophobic.json) (expanded) | 0.174 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.080 | opposed |  |  |

### fractious (cut-off 3, 9 pairs judged)

Gloss: This means picking fights over small matters, snapping at others, taking offense easily, and arguing every point with a sour temper that keeps any gathering on edge.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [petty](../../../traits/instructions/petty.json) | 0.461 | similar | 2 | 2 |
| [thin-skinned](../../../traits/instructions/thin_skinned.json) | 0.432 | similar | 2 | 2 |
| [irascible](../../../traits/instructions/irascible.json) | 0.370 | similar | 2 | 2 |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.257 | similar | 2 | 2 |
| [uptight](../../../traits/instructions/uptight.json) | 0.247 | unrelated | 1 |  |
| [rude](../../../traits/instructions/rude.json) | 0.247 | unrelated | 1 |  |
| [excitable](../../../traits/instructions/excitable.json) | 0.237 | similar | 1 |  |
| [immature](../../../traits/instructions/immature.json) | 0.234 | similar | 1 |  |
| [bullying](../../../traits/instructions/bullying.json) | 0.221 | unrelated |  |  |
| [fragile](../../../traits/instructions/fragile.json) | 0.207 | similar | 1 |  |
| [thick-skinned](../../../traits/instructions/thick_skinned.json) (expanded) | 0.170 | opposed |  |  |
| [magnanimous](../../../traits/instructions/magnanimous.json) (expanded) | 0.164 | opposed |  |  |
| [placid](../../../traits/instructions/placid.json) (expanded) | 0.156 | opposed |  |  |
| [mature](../../../traits/instructions/mature.json) (expanded) | 0.076 | opposed |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.068 | opposed |  |  |
| [calm](../../../traits/instructions/calm.json) (expanded) | 0.062 | opposed |  |  |
| [easygoing](../../../traits/instructions/easygoing.json) (expanded) | 0.036 | opposed |  |  |
| [resilient](../../../traits/instructions/resilient.json) (expanded) | 0.018 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | 0.013 | opposed |  |  |

### frank (cut-off 4, 10 pairs judged)

Gloss: This means speaking one's mind plainly and acting without deception or evasion.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [plain-spoken](../../../traits/instructions/plain_spoken.json) | 0.466 | similar | 2 |  |
| [blunt](../../../traits/instructions/blunt.json) | 0.453 | similar | 2 |  |
| [forthright](../../../traits/instructions/forthright.json) | 0.435 | similar | 3 | 3 |
| [honest](../../../traits/instructions/honest.json) | 0.423 | similar | 2 |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.419 | similar | 1 |  |
| [transparent](../../../traits/instructions/transparent.json) | 0.398 | similar | 2 |  |
| [clear](../../../traits/instructions/clear.json) | 0.389 | similar | 2 |  |
| [guileless](../../../traits/instructions/guileless.json) | 0.369 | similar | 2 |  |
| [earnest](../../../traits/instructions/earnest.json) | 0.357 | similar | 1 |  |
| [candid](../../../traits/instructions/candid.json) | 0.356 | similar | 3 | 3 |
| [opaque](../../../traits/instructions/opaque.json) (expanded) | 0.245 | opposed |  |  |
| [guarded](../../../traits/instructions/guarded.json) (expanded) | 0.198 | opposed |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) (expanded) | 0.170 | opposed |  |  |
| [scheming](../../../traits/instructions/scheming.json) (expanded) | 0.116 | opposed |  |  |
| [eloquent](../../../traits/instructions/eloquent.json) (expanded) | 0.095 | unrelated |  |  |
| [tactful](../../../traits/instructions/tactful.json) (expanded) | 0.035 | opposed |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) (expanded) | 0.030 | opposed |  |  |
| [sycophantic](../../../traits/instructions/sycophantic.json) (expanded) | 0.017 | opposed |  |  |
| [sardonic](../../../traits/instructions/sardonic.json) (expanded) | -0.029 | unrelated |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) (expanded) | -0.037 | opposed |  |  |

### frantic (cut-off 3, 8 pairs judged)

Gloss: This means acting in a frenzy, lurching from one thing to the next with no control, rushing and flailing, and letting panic drive every move.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [chaotic](../../../traits/instructions/chaotic.json) | 0.425 | similar | 2 | 2 |
| [manic](../../../traits/instructions/manic.json) | 0.396 | similar | 2 | 1 |
| [erratic](../../../traits/instructions/erratic.json) | 0.378 | unrelated | 1 |  |
| [restless](../../../traits/instructions/restless.json) | 0.372 | similar | 1 |  |
| [hurried](../../../traits/instructions/hurried.json) | 0.365 | similar | 2 | 2 |
| [mercurial](../../../traits/instructions/mercurial.json) | 0.341 | unrelated |  |  |
| [impulsive](../../../traits/instructions/impulsive.json) | 0.292 | similar | 1 |  |
| [panicky](../../../traits/instructions/panicky.json) | 0.288 | similar | 2 | 2 |
| [turbulent](../../../traits/instructions/turbulent.json) | 0.284 | similar | 2 | 2 |
| [job-hopping](../../../traits/instructions/job_hopping.json) | 0.281 | unrelated |  |  |
| [unhurried](../../../traits/instructions/unhurried.json) (expanded) | 0.070 | opposed |  |  |
| [steady](../../../traits/instructions/steady.json) (expanded) | 0.043 | opposed |  |  |
| [deliberate](../../../traits/instructions/deliberate.json) (expanded) | 0.042 | opposed |  |  |
| [company-loyal](../../../traits/instructions/company_loyal.json) (expanded) | 0.009 | unrelated |  |  |
| [serene](../../../traits/instructions/serene.json) (expanded) | -0.001 | opposed |  |  |

### fruit-eating (cut-off 3, 1 pairs judged)

Gloss: This means living on a diet of mainly fruit.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [spartan](../../../traits/instructions/spartan.json) | 0.262 | unrelated | 0 |  |
| [wealthy](../../../traits/instructions/wealthy.json) | 0.188 | unrelated |  |  |
| [picky-eater](../../../traits/instructions/picky_eater.json) | 0.187 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.183 | unrelated |  |  |
| [urban](../../../traits/instructions/urban.json) | 0.175 | unrelated |  |  |
| [poor](../../../traits/instructions/poor.json) | 0.174 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.174 | unrelated |  |  |
| [science-trusting](../../../traits/instructions/science_trusting.json) | 0.171 | unrelated |  |  |
| [frugal](../../../traits/instructions/frugal.json) | 0.171 | unrelated |  |  |
| [health-conscious](../../../traits/instructions/health_conscious.json) | 0.167 | unrelated |  |  |
| [adventurous-eater](../../../traits/instructions/adventurous_eater.json) (expanded) | 0.153 | unrelated |  |  |
| [rural](../../../traits/instructions/rural.json) (expanded) | 0.136 | unrelated |  |  |
| [science-skeptical](../../../traits/instructions/science_skeptical.json) (expanded) | 0.115 | unrelated |  |  |
| [settled](../../../traits/instructions/settled.json) (expanded) | 0.115 | unrelated |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.112 | unrelated |  |  |
| [health-negligent](../../../traits/instructions/health_negligent.json) (expanded) | 0.108 | unrelated |  |  |
| [extravagant](../../../traits/instructions/extravagant.json) (expanded) | 0.060 | unrelated |  |  |
| [epicurean](../../../traits/instructions/epicurean.json) (expanded) | 0.060 | opposed |  |  |

### gabby (cut-off 3, 7 pairs judged)

Gloss: This means talking freely and at length by temperament, filling every pause, drifting into side stories, and treating any conversation as a reason to keep chatting.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [glib](../../../traits/instructions/glib.json) | 0.298 | unrelated |  |  |
| [laid-back](../../../traits/instructions/laid_back.json) | 0.287 | unrelated |  |  |
| [manic](../../../traits/instructions/manic.json) | 0.281 | similar | 1 |  |
| [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | 0.262 | similar | 1 |  |
| [erratic](../../../traits/instructions/erratic.json) | 0.247 | unrelated | 0 |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.237 | unrelated | 1 |  |
| [verbose](../../../traits/instructions/verbose.json) | 0.231 | similar | 2 | 2 |
| [unselfconscious](../../../traits/instructions/unselfconscious.json) | 0.220 | unrelated | 1 |  |
| [steady](../../../traits/instructions/steady.json) | 0.216 | opposed |  |  |
| [lighthearted](../../../traits/instructions/lighthearted.json) | 0.205 | unrelated | 1 |  |
| [intense](../../../traits/instructions/intense.json) (expanded) | 0.204 | unrelated |  |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.097 | opposed |  |  |
| [solemn](../../../traits/instructions/solemn.json) (expanded) | 0.028 | opposed |  |  |
| [concise](../../../traits/instructions/concise.json) (expanded) | 0.026 | opposed |  |  |
| [self-conscious](../../../traits/instructions/self_conscious.json) (expanded) | 0.022 | opposed |  |  |

### genuine (cut-off 4, 10 pairs judged)

Gloss: This means expressing one's actual feelings and character without pretense or deception.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [authentic](../../../traits/instructions/authentic.json) | 0.468 | similar | 3 | 3 |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.447 | similar | 2 |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.387 | similar | 2 |  |
| [earnest](../../../traits/instructions/earnest.json) | 0.371 | similar | 2 |  |
| [honest](../../../traits/instructions/honest.json) | 0.360 | similar | 2 |  |
| [guileless](../../../traits/instructions/guileless.json) | 0.344 | similar | 2 |  |
| [transparent](../../../traits/instructions/transparent.json) | 0.344 | similar | 2 |  |
| [sincere](../../../traits/instructions/sincere.json) | 0.342 | similar | 2 |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) | 0.322 | similar | 1 |  |
| [truthful](../../../traits/instructions/truthful.json) | 0.319 | similar | 2 |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.252 | opposed |  |  |
| [opaque](../../../traits/instructions/opaque.json) (expanded) | 0.146 | opposed |  |  |
| [deceitful](../../../traits/instructions/deceitful.json) (expanded) | 0.136 | opposed |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) (expanded) | 0.129 | opposed |  |  |
| [scheming](../../../traits/instructions/scheming.json) (expanded) | 0.075 | opposed |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) (expanded) | 0.074 | opposed |  |  |
| [ironic](../../../traits/instructions/ironic.json) (expanded) | 0.073 | opposed |  |  |
| [performative](../../../traits/instructions/performative.json) (expanded) | 0.054 | opposed |  |  |
| [eloquent](../../../traits/instructions/eloquent.json) (expanded) | 0.046 | unrelated |  |  |
| [sardonic](../../../traits/instructions/sardonic.json) (expanded) | -0.028 | opposed |  |  |

### habitual (cut-off 3, 9 pairs judged)

Gloss: This means doing things regularly and repeatedly, in settled patterns that structure one's days.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [settled](../../../traits/instructions/settled.json) | 0.340 | similar | 1 |  |
| [ritualistic](../../../traits/instructions/ritualistic.json) | 0.269 | similar | 2 | 2 |
| [methodical](../../../traits/instructions/methodical.json) | 0.263 | similar | 1 |  |
| [formulaic](../../../traits/instructions/formulaic.json) | 0.248 | similar | 1 |  |
| [organized](../../../traits/instructions/organized.json) | 0.230 | similar | 1 |  |
| [formalist](../../../traits/instructions/formalist.json) | 0.226 | similar | 1 |  |
| [married](../../../traits/instructions/married.json) | 0.212 | unrelated |  |  |
| [persevering](../../../traits/instructions/persevering.json) | 0.209 | similar | 1 |  |
| [industrious](../../../traits/instructions/industrious.json) | 0.198 | similar | 1 |  |
| [dependable](../../../traits/instructions/dependable.json) | 0.197 | similar | 1 |  |
| [lazy](../../../traits/instructions/lazy.json) (expanded) | 0.110 | opposed |  |  |
| [spontaneous](../../../traits/instructions/spontaneous.json) (expanded) | 0.103 | opposed |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | 0.100 | opposed |  |  |
| [single](../../../traits/instructions/single.json) (expanded) | 0.095 | unrelated |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.084 | opposed |  |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.033 | opposed |  |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | 0.004 | opposed |  |  |
| [defeatist](../../../traits/instructions/defeatist.json) (expanded) | -0.047 | opposed |  |  |

### handicapped (cut-off 3, 3 pairs judged)

Gloss: This means living with a mental or cognitive disability.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [cerebral](../../../traits/instructions/cerebral.json) | 0.282 | unrelated |  |  |
| [poor](../../../traits/instructions/poor.json) | 0.259 | unrelated |  |  |
| [illiterate](../../../traits/instructions/illiterate.json) | 0.251 | unrelated |  |  |
| [elderly](../../../traits/instructions/elderly.json) | 0.206 | unrelated |  |  |
| [forgetful](../../../traits/instructions/forgetful.json) | 0.201 | similar | 1 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.200 | unrelated | 0 |  |
| [slow-witted](../../../traits/instructions/slow_witted.json) | 0.193 | similar | 2 | 1 |
| [urban](../../../traits/instructions/urban.json) | 0.187 | unrelated |  |  |
| [rural](../../../traits/instructions/rural.json) | 0.177 | unrelated |  |  |
| [renter](../../../traits/instructions/renter.json) | 0.169 | unrelated |  |  |
| [wealthy](../../../traits/instructions/wealthy.json) (expanded) | 0.151 | unrelated |  |  |
| [literate](../../../traits/instructions/literate.json) (expanded) | 0.129 | unrelated |  |  |
| [homeowner](../../../traits/instructions/homeowner.json) (expanded) | 0.123 | unrelated |  |  |
| [young](../../../traits/instructions/young.json) (expanded) | 0.112 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.096 | opposed |  |  |
| [retentive](../../../traits/instructions/retentive.json) (expanded) | 0.088 | opposed |  |  |
| [visceral](../../../traits/instructions/visceral.json) (expanded) | 0.026 | unrelated |  |  |
| [quick-witted](../../../traits/instructions/quick_witted.json) (expanded) | 0.004 | opposed |  |  |

### hardy (cut-off 3, 7 pairs judged)

Gloss: This means having a body built to endure, carrying on through cold, hunger, exhaustion and rough country without complaint, and recovering quickly from strain that would leave others laid up.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [strong-stomached](../../../traits/instructions/strong_stomached.json) | 0.338 | similar | 1 |  |
| [persevering](../../../traits/instructions/persevering.json) | 0.333 | similar | 1 |  |
| [spartan](../../../traits/instructions/spartan.json) | 0.254 | similar | 1 |  |
| [resilient](../../../traits/instructions/resilient.json) | 0.241 | similar | 2 | 2 |
| [brave](../../../traits/instructions/brave.json) | 0.226 | unrelated |  |  |
| [thick-skinned](../../../traits/instructions/thick_skinned.json) | 0.216 | unrelated | 1 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.207 | similar | 0 |  |
| [poor](../../../traits/instructions/poor.json) | 0.206 | unrelated |  |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.198 | unrelated |  |  |
| [composed](../../../traits/instructions/composed.json) | 0.198 | similar | 1 |  |
| [feminine](../../../traits/instructions/feminine.json) (expanded) | 0.116 | unrelated |  |  |
| [fragile](../../../traits/instructions/fragile.json) (expanded) | 0.116 | opposed |  |  |
| [wealthy](../../../traits/instructions/wealthy.json) (expanded) | 0.104 | unrelated |  |  |
| [defeatist](../../../traits/instructions/defeatist.json) (expanded) | 0.094 | opposed |  |  |
| [thin-skinned](../../../traits/instructions/thin_skinned.json) (expanded) | 0.052 | opposed |  |  |
| [squeamish](../../../traits/instructions/squeamish.json) (expanded) | 0.044 | opposed |  |  |
| [cowardly](../../../traits/instructions/cowardly.json) (expanded) | 0.043 | unrelated |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.021 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | 0.019 | opposed |  |  |
| [epicurean](../../../traits/instructions/epicurean.json) (expanded) | 0.010 | opposed |  |  |

### hasty (cut-off 4, 9 pairs judged)

Gloss: This means acting and deciding without pausing to think things through or weigh the consequences.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [impulsive](../../../traits/instructions/impulsive.json) | 0.458 | similar | 3 | 3 |
| [brash](../../../traits/instructions/brash.json) | 0.367 | similar | 2 |  |
| [unreflective](../../../traits/instructions/unreflective.json) | 0.361 | similar | 1 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) | 0.356 | unrelated | 1 |  |
| [bold](../../../traits/instructions/bold.json) | 0.334 | similar | 2 |  |
| [deliberate](../../../traits/instructions/deliberate.json) | 0.315 | opposed |  |  |
| [hurried](../../../traits/instructions/hurried.json) | 0.300 | similar | 2 |  |
| [reactive](../../../traits/instructions/reactive.json) | 0.289 | similar | 2 |  |
| [reckless](../../../traits/instructions/reckless.json) | 0.279 | similar | 2 |  |
| [improvisational](../../../traits/instructions/improvisational.json) | 0.261 | similar | 1 |  |
| [calculating](../../../traits/instructions/calculating.json) (expanded) | 0.175 | opposed |  |  |
| [unhurried](../../../traits/instructions/unhurried.json) (expanded) | 0.159 | opposed |  |  |
| [circumspect](../../../traits/instructions/circumspect.json) (expanded) | 0.109 | opposed |  |  |
| [prudent](../../../traits/instructions/prudent.json) (expanded) | 0.051 | opposed |  |  |
| [cautious](../../../traits/instructions/cautious.json) (expanded) | 0.049 | opposed |  |  |
| [proactive](../../../traits/instructions/proactive.json) (expanded) | 0.017 | opposed |  |  |
| [methodical](../../../traits/instructions/methodical.json) (expanded) | -0.012 | opposed |  |  |
| [introspective](../../../traits/instructions/introspective.json) (expanded) | -0.036 | opposed |  |  |

### hierarchical (cut-off 3, 8 pairs judged)

Gloss: This means organizing people, ideas, and decisions according to ranks and levels of authority.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [formalist](../../../traits/instructions/formalist.json) | 0.322 | similar | 1 |  |
| [organized](../../../traits/instructions/organized.json) | 0.299 | similar | 1 |  |
| [obedient](../../../traits/instructions/obedient.json) | 0.294 | similar | 1 |  |
| [meritocratic](../../../traits/instructions/meritocratic.json) | 0.279 | unrelated |  |  |
| [aristocratic](../../../traits/instructions/aristocratic.json) | 0.252 | similar | 2 | 2 |
| [transactional](../../../traits/instructions/transactional.json) | 0.227 | similar | 1 |  |
| [structuralist](../../../traits/instructions/structuralist.json) | 0.212 | similar | 1 |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.196 | unrelated |  |  |
| [technocratic](../../../traits/instructions/technocratic.json) | 0.192 | similar | 1 |  |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.188 | similar | 1 |  |
| [rebellious](../../../traits/instructions/rebellious.json) (expanded) | 0.177 | opposed |  |  |
| [transformational](../../../traits/instructions/transformational.json) (expanded) | 0.164 | unrelated |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.159 | unrelated |  |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | 0.144 | opposed |  |  |
| [populist](../../../traits/instructions/populist.json) (expanded) | 0.092 | opposed |  |  |

### hokey (cut-off 3, 8 pairs judged)

Gloss: This means leaning on cornball jokes, sentimental flourishes and well-worn clichés, delivering them with a straight-faced, cheesy earnestness that belongs to an older, simpler style of entertainment.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [goofy](../../../traits/instructions/goofy.json) | 0.298 | unrelated |  |  |
| [formulaic](../../../traits/instructions/formulaic.json) | 0.277 | similar | 1 |  |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.271 | similar | 1 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.255 | similar | 1 |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) | 0.245 | unrelated |  |  |
| [flat](../../../traits/instructions/flat.json) | 0.233 | opposed |  |  |
| [conventional](../../../traits/instructions/conventional.json) | 0.226 | similar | 1 |  |
| [lowbrow](../../../traits/instructions/lowbrow.json) | 0.222 | similar | 1 |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.216 | similar | 1 |  |
| [dry](../../../traits/instructions/dry.json) | 0.215 | opposed |  |  |
| [entertaining](../../../traits/instructions/entertaining.json) (expanded) | 0.156 | similar | 1 |  |
| [animated](../../../traits/instructions/animated.json) (expanded) | 0.143 | unrelated | 0 |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) (expanded) | 0.105 | unrelated |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.086 | opposed |  |  |
| [highbrow](../../../traits/instructions/highbrow.json) (expanded) | 0.069 | opposed |  |  |
| [spontaneous](../../../traits/instructions/spontaneous.json) (expanded) | 0.060 | opposed |  |  |
| [eccentric](../../../traits/instructions/eccentric.json) (expanded) | 0.034 | opposed |  |  |

### human-centered (cut-off 4, 7 pairs judged)

Gloss: This means putting people's needs and wellbeing first in every answer, weighing how a response will affect the person receiving it before anything else, and shaping advice around their lives.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [humanistic](../../../traits/instructions/humanistic.json) | 0.345 | similar | 2 |  |
| [benevolent](../../../traits/instructions/benevolent.json) | 0.343 | similar | 2 |  |
| [environmental](../../../traits/instructions/environmental.json) | 0.319 | unrelated |  |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.280 | unrelated |  |  |
| [helpful](../../../traits/instructions/helpful.json) | 0.269 | similar | 2 |  |
| [harmless](../../../traits/instructions/harmless.json) | 0.260 | similar | 1 |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.260 | similar | 1 |  |
| [other-focused](../../../traits/instructions/other_focused.json) | 0.252 | similar | 2 |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.245 | opposed |  |  |
| [calculating](../../../traits/instructions/calculating.json) | 0.237 | opposed |  |  |
| [uncaring](../../../traits/instructions/uncaring.json) (expanded) | 0.196 | opposed |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.105 | unrelated |  |  |
| [mechanistic](../../../traits/instructions/mechanistic.json) (expanded) | 0.102 | opposed |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.080 | opposed |  |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.063 | similar | 1 |  |
| [harmful](../../../traits/instructions/harmful.json) (expanded) | 0.048 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.043 | unrelated |  |  |
| [self-absorbed](../../../traits/instructions/self_absorbed.json) (expanded) | 0.015 | opposed |  |  |

Pair completion for: [civilizationist](../../../traits/instructions/civilizationist.json)

### hyperbolic (cut-off 4, 9 pairs judged)

Gloss: This means speaking and writing with exaggeration, stretching claims and descriptions far beyond what is literally true.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [bombastic](../../../traits/instructions/bombastic.json) | 0.411 | similar | 2 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.375 | similar | 2 |  |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.366 | similar | 2 |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.344 | similar | 2 |  |
| [verbose](../../../traits/instructions/verbose.json) | 0.335 | unrelated | 0 |  |
| [grandiose](../../../traits/instructions/grandiose.json) | 0.286 | similar | 2 |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.274 | unrelated |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.256 | unrelated | 1 |  |
| [emphatic](../../../traits/instructions/emphatic.json) | 0.249 | unrelated | 2 |  |
| [animated](../../../traits/instructions/animated.json) | 0.245 | similar | 1 |  |
| [flat](../../../traits/instructions/flat.json) (expanded) | 0.210 | opposed |  |  |
| [understated](../../../traits/instructions/understated.json) (expanded) | 0.195 | opposed |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) (expanded) | 0.146 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.139 | opposed |  |  |
| [concise](../../../traits/instructions/concise.json) (expanded) | 0.121 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.008 | opposed |  |  |

### hypnotic (cut-off 3, 8 pairs judged)

Gloss: This means speaking in a slow, rhythmic, resonant voice that draws listeners in and holds their attention, so that every word feels magnetic and hard to look away from.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [flat](../../../traits/instructions/flat.json) | 0.322 | opposed |  |  |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.301 | similar | 1 |  |
| [poetic](../../../traits/instructions/poetic.json) | 0.291 | similar | 1 |  |
| [eloquent](../../../traits/instructions/eloquent.json) | 0.287 | similar | 1 |  |
| [steady](../../../traits/instructions/steady.json) | 0.273 | similar | 0 |  |
| [animated](../../../traits/instructions/animated.json) | 0.270 | unrelated | 1 |  |
| [rhetorical](../../../traits/instructions/rhetorical.json) | 0.267 | similar | 1 |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.263 | similar | 1 |  |
| [dull](../../../traits/instructions/dull.json) | 0.254 | opposed |  |  |
| [charismatic](../../../traits/instructions/charismatic.json) | 0.237 | similar | 2 | 2 |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) (expanded) | 0.209 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.131 | opposed |  |  |
| [informational](../../../traits/instructions/informational.json) (expanded) | 0.097 | opposed |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | 0.058 | opposed |  |  |
| [prosaic](../../../traits/instructions/prosaic.json) (expanded) | 0.041 | opposed |  |  |

### ill-humoured (cut-off 3, 8 pairs judged)

Gloss: This means carrying a standing irritability, snapping at small annoyances, grumbling through the day, and meeting people and plans with a sour, put-upon temper.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [irascible](../../../traits/instructions/irascible.json) | 0.378 | similar | 2 | 2 |
| [thin-skinned](../../../traits/instructions/thin_skinned.json) | 0.296 | similar | 1 |  |
| [petty](../../../traits/instructions/petty.json) | 0.272 | similar | 1 |  |
| [restless](../../../traits/instructions/restless.json) | 0.261 | unrelated |  |  |
| [excitable](../../../traits/instructions/excitable.json) | 0.256 | unrelated | 1 |  |
| [uptight](../../../traits/instructions/uptight.json) | 0.255 | unrelated | 1 |  |
| [even-tempered](../../../traits/instructions/even_tempered.json) | 0.250 | opposed |  |  |
| [discontented](../../../traits/instructions/discontented.json) | 0.227 | unrelated | 1 |  |
| [placid](../../../traits/instructions/placid.json) | 0.221 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) | 0.216 | unrelated | 1 |  |
| [composed](../../../traits/instructions/composed.json) (expanded) | 0.197 | opposed |  |  |
| [calm](../../../traits/instructions/calm.json) (expanded) | 0.194 | opposed |  |  |
| [temperamental](../../../traits/instructions/temperamental.json) (expanded) | 0.188 | unrelated | 2 | 1 |
| [thick-skinned](../../../traits/instructions/thick_skinned.json) (expanded) | 0.158 | opposed |  |  |
| [magnanimous](../../../traits/instructions/magnanimous.json) (expanded) | 0.137 | opposed |  |  |
| [easygoing](../../../traits/instructions/easygoing.json) (expanded) | 0.127 | opposed |  |  |
| [contented](../../../traits/instructions/contented.json) (expanded) | 0.072 | opposed |  |  |

### illegal (cut-off 3, 5 pairs judged)

Gloss: This means living in a country without legal immigration status, holding no official papers to reside or work there.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rootless](../../../traits/instructions/rootless.json) | 0.354 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.330 | unrelated | 0 |  |
| [uneducated](../../../traits/instructions/uneducated.json) | 0.313 | unrelated |  |  |
| [poor](../../../traits/instructions/poor.json) | 0.300 | similar | 0 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.264 | similar | 0 |  |
| [anti-immigration](../../../traits/instructions/anti_immigration.json) | 0.254 | opposed |  |  |
| [renter](../../../traits/instructions/renter.json) | 0.254 | similar | 0 |  |
| [rural](../../../traits/instructions/rural.json) | 0.246 | unrelated |  |  |
| [single](../../../traits/instructions/single.json) | 0.246 | unrelated |  |  |
| [unschooled](../../../traits/instructions/unschooled.json) | 0.245 | unrelated |  |  |
| [pro-immigration](../../../traits/instructions/pro_immigration.json) (expanded) | 0.242 | similar | 0 |  |
| [urban](../../../traits/instructions/urban.json) (expanded) | 0.222 | unrelated |  |  |
| [settled](../../../traits/instructions/settled.json) (expanded) | 0.217 | opposed |  |  |
| [homeowner](../../../traits/instructions/homeowner.json) (expanded) | 0.186 | opposed |  |  |
| [rooted](../../../traits/instructions/rooted.json) (expanded) | 0.177 | unrelated |  |  |
| [married](../../../traits/instructions/married.json) (expanded) | 0.169 | unrelated |  |  |
| [wealthy](../../../traits/instructions/wealthy.json) (expanded) | 0.090 | unrelated |  |  |
| [educated](../../../traits/instructions/educated.json) (expanded) | 0.083 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.059 | opposed |  |  |
| [erudite](../../../traits/instructions/erudite.json) (expanded) | -0.018 | unrelated |  |  |

### immoral (cut-off 4, 10 pairs judged)

Gloss: This means having a character that runs against morality, lying, cheating and harming others without guilt, and treating right and wrong as obstacles to getting what one wants.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [amoral](../../../traits/instructions/amoral.json) | 0.389 | similar | 2 |  |
| [evil](../../../traits/instructions/evil.json) | 0.389 | similar | 2 |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.341 | similar | 2 |  |
| [moral](../../../traits/instructions/moral.json) | 0.332 | opposed |  |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.324 | similar | 2 |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | 0.275 | similar | 2 |  |
| [malign](../../../traits/instructions/malign.json) | 0.267 | similar | 2 |  |
| [malevolent](../../../traits/instructions/malevolent.json) | 0.266 | similar | 2 |  |
| [mischievous](../../../traits/instructions/mischievous.json) | 0.261 | unrelated | 1 |  |
| [ruthless while playing](../../../traits/instructions/ruthless_while_playing.json) | 0.252 | unrelated | 1 |  |
| [honorable while playing](../../../traits/instructions/honorable_while_playing.json) (expanded) | 0.235 | opposed |  |  |
| [good](../../../traits/instructions/good.json) (expanded) | 0.144 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.136 | opposed |  |  |
| [well-behaved](../../../traits/instructions/well_behaved.json) (expanded) | 0.108 | opposed |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.080 | similar | 1 |  |
| [benign](../../../traits/instructions/benign.json) (expanded) | 0.053 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) (expanded) | 0.030 | opposed |  |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.002 | opposed |  |  |

### inconsistent (cut-off 4, 10 pairs judged)

Gloss: This means saying one thing and doing another, or acting against one's own stated beliefs.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [ironic](../../../traits/instructions/ironic.json) | 0.335 | unrelated | 1 |  |
| [unreliable](../../../traits/instructions/unreliable.json) | 0.249 | similar | 2 |  |
| [treacherous](../../../traits/instructions/treacherous.json) | 0.246 | similar | 1 |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | 0.243 | similar | 1 |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | 0.233 | similar | 1 |  |
| [incoherent](../../../traits/instructions/incoherent.json) | 0.223 | unrelated | 2 |  |
| [deceitful](../../../traits/instructions/deceitful.json) | 0.205 | similar | 1 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.199 | unrelated | 1 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.199 | unrelated | 0 |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.194 | unrelated | 0 |  |
| [sincere](../../../traits/instructions/sincere.json) (expanded) | 0.144 | opposed |  |  |
| [coherent](../../../traits/instructions/coherent.json) (expanded) | 0.113 | opposed |  |  |
| [dependable](../../../traits/instructions/dependable.json) (expanded) | 0.101 | opposed |  |  |
| [fair](../../../traits/instructions/fair.json) (expanded) | 0.088 | opposed |  |  |
| [truthful](../../../traits/instructions/truthful.json) (expanded) | 0.081 | opposed |  |  |
| [loyal](../../../traits/instructions/loyal.json) (expanded) | 0.069 | opposed |  |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) (expanded) | 0.058 | opposed |  |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) (expanded) | 0.050 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.029 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | -0.033 | opposed |  |  |

### indifferent (cut-off 4, 8 pairs judged)

Gloss: This means feeling nothing either way about what happens, meeting news, requests, and outcomes with a flat, detached shrug and never being moved to want one result over another.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [even-tempered](../../../traits/instructions/even_tempered.json) | 0.358 | unrelated | 1 |  |
| [apathetic](../../../traits/instructions/apathetic.json) | 0.337 | similar | 3 | 3 |
| [joyless](../../../traits/instructions/joyless.json) | 0.319 | unrelated |  |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.287 | unrelated | 1 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.280 | unrelated | 2 |  |
| [passive](../../../traits/instructions/passive.json) | 0.279 | unrelated |  |  |
| [amoral](../../../traits/instructions/amoral.json) | 0.279 | unrelated | 1 |  |
| [apolitical](../../../traits/instructions/apolitical.json) | 0.277 | unrelated | 1 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) | 0.277 | unrelated | 1 |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) | 0.266 | similar | 2 |  |
| [news-junkie](../../../traits/instructions/news_junkie.json) (expanded) | 0.150 | opposed |  |  |
| [engaged](../../../traits/instructions/engaged.json) (expanded) | 0.116 | opposed |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | 0.066 | unrelated |  |  |
| [moral](../../../traits/instructions/moral.json) (expanded) | 0.043 | opposed |  |  |
| [political](../../../traits/instructions/political.json) (expanded) | 0.026 | opposed |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) (expanded) | 0.024 | opposed |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.009 | opposed |  |  |
| [temperamental](../../../traits/instructions/temperamental.json) (expanded) | 0.000 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | -0.016 | opposed |  |  |

### indirect (cut-off 3, 8 pairs judged)

Gloss: This means communicating through hints, implications, and circuitous routes rather than stating things plainly.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [cryptic](../../../traits/instructions/cryptic.json) | 0.424 | similar | 2 | 2 |
| [opaque](../../../traits/instructions/opaque.json) | 0.381 | unrelated | 1 |  |
| [enigmatic](../../../traits/instructions/enigmatic.json) | 0.358 | similar | 2 | 2 |
| [vague](../../../traits/instructions/vague.json) | 0.324 | similar | 2 | 2 |
| [metaphorical](../../../traits/instructions/metaphorical.json) | 0.321 | similar | 2 | 1 |
| [passive-aggressive](../../../traits/instructions/passive_aggressive.json) | 0.311 | unrelated |  |  |
| [clear](../../../traits/instructions/clear.json) | 0.301 | opposed |  |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) | 0.296 | opposed |  |  |
| [blunt](../../../traits/instructions/blunt.json) | 0.294 | opposed |  |  |
| [understated](../../../traits/instructions/understated.json) | 0.276 | similar | 1 |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | 0.203 | opposed |  |  |
| [eloquent](../../../traits/instructions/eloquent.json) (expanded) | 0.174 | unrelated | 0 |  |
| [tactful](../../../traits/instructions/tactful.json) (expanded) | 0.159 | unrelated | 1 |  |
| [precise](../../../traits/instructions/precise.json) (expanded) | 0.154 | opposed |  |  |
| [emphatic](../../../traits/instructions/emphatic.json) (expanded) | 0.042 | opposed |  |  |

### inherited (cut-off 3, 3 pairs judged)

Gloss: This means carrying traits and characteristics received from one's family line.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [parent](../../../traits/instructions/parent.json) | 0.320 | unrelated |  |  |
| [old money](../../../traits/instructions/old_money.json) | 0.316 | similar | 1 |  |
| [rooted](../../../traits/instructions/rooted.json) | 0.301 | similar | 1 |  |
| [new money](../../../traits/instructions/new_money.json) | 0.256 | opposed |  |  |
| [aristocratic](../../../traits/instructions/aristocratic.json) | 0.255 | similar | 1 |  |
| [clannish](../../../traits/instructions/clannish.json) | 0.213 | unrelated |  |  |
| [many siblings](../../../traits/instructions/many_siblings.json) | 0.196 | unrelated |  |  |
| [feminine](../../../traits/instructions/feminine.json) | 0.195 | unrelated |  |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.191 | unrelated |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.188 | unrelated |  |  |
| [rootless](../../../traits/instructions/rootless.json) (expanded) | 0.148 | opposed |  |  |
| [childless](../../../traits/instructions/childless.json) (expanded) | 0.146 | unrelated |  |  |

### insubordinate (cut-off 4, 8 pairs judged)

Gloss: This means refusing to follow orders or comply with rules set by those in authority.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rebellious](../../../traits/instructions/rebellious.json) | 0.537 | similar | 3 | 3 |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.384 | similar | 2 |  |
| [obedient](../../../traits/instructions/obedient.json) | 0.298 | opposed |  |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.268 | unrelated | 1 |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.232 | unrelated | 1 |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.223 | unrelated | 1 |  |
| [heterodox](../../../traits/instructions/heterodox.json) | 0.219 | unrelated | 1 |  |
| [subversive](../../../traits/instructions/subversive.json) | 0.203 | unrelated |  |  |
| [rigid](../../../traits/instructions/rigid.json) | 0.196 | unrelated | 0 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.181 | unrelated |  |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | 0.170 | unrelated | 1 |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.141 | opposed |  |  |
| [conformist](../../../traits/instructions/conformist.json) (expanded) | 0.085 | opposed |  |  |
| [orthodox](../../../traits/instructions/orthodox.json) (expanded) | 0.072 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | -0.007 | unrelated |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | -0.011 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | -0.018 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | -0.031 | opposed |  |  |

### integrated (cut-off 3, 7 pairs judged)

Gloss: This means holding one's values, feelings and conduct together as a single coherent whole, so that one acts the same way in every setting and sits easily with oneself.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [honorable](../../../traits/instructions/honorable.json) | 0.311 | similar | 1 |  |
| [dignified](../../../traits/instructions/dignified.json) | 0.305 | unrelated |  |  |
| [coherent](../../../traits/instructions/coherent.json) | 0.289 | similar | 2 | 1 |
| [steady](../../../traits/instructions/steady.json) | 0.289 | similar | 2 | 1 |
| [principled](../../../traits/instructions/principled.json) | 0.284 | similar | 2 | 2 |
| [self-certain](../../../traits/instructions/self_certain.json) | 0.279 | similar | 2 | 2 |
| [composed](../../../traits/instructions/composed.json) | 0.279 | unrelated |  |  |
| [authentic](../../../traits/instructions/authentic.json) | 0.246 | similar | 2 | 2 |
| [moral](../../../traits/instructions/moral.json) | 0.243 | similar | 1 |  |
| [stoic](../../../traits/instructions/stoic.json) | 0.242 | unrelated |  |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) (expanded) | 0.177 | opposed |  |  |
| [incoherent](../../../traits/instructions/incoherent.json) (expanded) | 0.164 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.110 | opposed |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.068 | opposed |  |  |
| [performative](../../../traits/instructions/performative.json) (expanded) | 0.062 | opposed |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | 0.012 | opposed |  |  |
| [expedient](../../../traits/instructions/expedient.json) (expanded) | -0.054 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.137 | unrelated |  |  |

### intellectually humble (cut-off 4, 8 pairs judged)

Gloss: This means acknowledging the limits of one's knowledge and recognizing how much remains to be learned.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [humble](../../../traits/instructions/humble.json) | 0.502 | similar | 3 | 3 |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.340 | similar | 2 |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) | 0.264 | similar | 2 |  |
| [wise](../../../traits/instructions/wise.json) | 0.221 | similar | 1 |  |
| [deferential](../../../traits/instructions/deferential.json) | 0.213 | similar | 2 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.207 | unrelated |  |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.195 | unrelated |  |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) | 0.194 | similar | 2 |  |
| [modest](../../../traits/instructions/modest.json) | 0.184 | similar | 2 |  |
| [open-minded](../../../traits/instructions/open_minded.json) | 0.176 | similar | 2 |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.114 | unrelated |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | 0.107 | opposed |  |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) (expanded) | 0.090 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.078 | unrelated |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.069 | unrelated |  |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) (expanded) | 0.045 | opposed |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) (expanded) | 0.028 | opposed |  |  |
| [arrogant](../../../traits/instructions/arrogant.json) (expanded) | 0.027 | opposed |  |  |

### interdependent (cut-off 3, 7 pairs judged)

Gloss: This means relying on others and having others rely on one within a shared relationship or system.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dependent](../../../traits/instructions/dependent.json) | 0.325 | unrelated | 1 |  |
| [cooperative](../../../traits/instructions/cooperative.json) | 0.267 | similar | 2 | 2 |
| [self-reliant](../../../traits/instructions/self_reliant.json) | 0.251 | opposed |  |  |
| [collaborative](../../../traits/instructions/collaborative.json) | 0.247 | similar | 2 | 2 |
| [many siblings](../../../traits/instructions/many_siblings.json) | 0.212 | unrelated |  |  |
| [dependable](../../../traits/instructions/dependable.json) | 0.211 | similar | 1 |  |
| [helpful](../../../traits/instructions/helpful.json) | 0.211 | similar | 1 |  |
| [socialist](../../../traits/instructions/socialist.json) | 0.204 | similar | 0 |  |
| [trusting](../../../traits/instructions/trusting.json) | 0.200 | similar | 1 |  |
| [independent](../../../traits/instructions/independent.json) | 0.193 | opposed |  |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.183 | opposed |  |  |
| [only child](../../../traits/instructions/only_child.json) (expanded) | 0.091 | unrelated |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.064 | opposed |  |  |
| [capitalist](../../../traits/instructions/capitalist.json) (expanded) | 0.056 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | -0.005 | opposed |  |  |
| [competitive](../../../traits/instructions/competitive.json) (expanded) | -0.013 | opposed |  |  |

### intervening (cut-off 4, 5 pairs judged)

Gloss: This means stepping into a situation as it unfolds to halt it or change its course, acting directly instead of standing by.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [reactive](../../../traits/instructions/reactive.json) | 0.343 | unrelated |  |  |
| [hands-on](../../../traits/instructions/hands_on.json) | 0.334 | similar | 2 |  |
| [improvisational](../../../traits/instructions/improvisational.json) | 0.315 | unrelated |  |  |
| [course-correcting](../../../traits/instructions/course_correcting.json) | 0.261 | similar | 1 |  |
| [proactive](../../../traits/instructions/proactive.json) | 0.246 | unrelated |  |  |
| [tactical](../../../traits/instructions/tactical.json) | 0.244 | unrelated |  |  |
| [passive](../../../traits/instructions/passive.json) | 0.208 | opposed |  |  |
| [unflinching](../../../traits/instructions/unflinching.json) | 0.206 | similar | 1 |  |
| [problem-solving](../../../traits/instructions/problem_solving.json) | 0.205 | similar | 1 |  |
| [engaged](../../../traits/instructions/engaged.json) | 0.190 | similar | 1 |  |
| [strategic](../../../traits/instructions/strategic.json) (expanded) | 0.158 | unrelated |  |  |
| [hands-off](../../../traits/instructions/hands_off.json) (expanded) | 0.154 | opposed |  |  |
| [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json) (expanded) | 0.063 | opposed |  |  |
| [methodical](../../../traits/instructions/methodical.json) (expanded) | 0.045 | unrelated |  |  |
| [apathetic](../../../traits/instructions/apathetic.json) (expanded) | -0.023 | opposed |  |  |

Pair completion for: [passive](../../../traits/instructions/passive.json)

### invested (cut-off 3, 5 pairs judged)

Gloss: This means caring deeply about how something turns out because one's own wellbeing or goals depend on it.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [engaged](../../../traits/instructions/engaged.json) | 0.453 | similar | 2 | 2 |
| [helpful](../../../traits/instructions/helpful.json) | 0.260 | similar | 1 |  |
| [selfish](../../../traits/instructions/selfish.json) | 0.256 | unrelated | 1 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.216 | opposed |  |  |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) | 0.210 | unrelated | 1 |  |
| [apathetic](../../../traits/instructions/apathetic.json) | 0.209 | opposed |  |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.204 | unrelated |  |  |
| [clingy](../../../traits/instructions/clingy.json) | 0.177 | unrelated |  |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.176 | unrelated |  |  |
| [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | 0.175 | unrelated |  |  |
| [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) (expanded) | 0.154 | unrelated |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.149 | unrelated | 1 |  |
| [altruistic](../../../traits/instructions/altruistic.json) (expanded) | 0.139 | opposed |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.055 | opposed |  |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) (expanded) | 0.047 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.037 | unrelated |  |  |

### involved (cut-off 3, 8 pairs judged)

Gloss: This means taking part in the activity or situation at hand, staying engaged with what is going on and contributing to it rather than watching from the edges.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [engaged](../../../traits/instructions/engaged.json) | 0.407 | similar | 2 | 2 |
| [hands-on](../../../traits/instructions/hands_on.json) | 0.388 | similar | 2 | 2 |
| [emotionally-engaged](../../../traits/instructions/emotionally_engaged.json) | 0.305 | similar | 1 |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) | 0.296 | unrelated |  |  |
| [focused](../../../traits/instructions/focused.json) | 0.290 | similar | 1 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.266 | similar | 1 |  |
| [intense](../../../traits/instructions/intense.json) | 0.240 | similar | 1 |  |
| [entertaining](../../../traits/instructions/entertaining.json) | 0.212 | unrelated |  |  |
| [reactive](../../../traits/instructions/reactive.json) | 0.201 | unrelated |  |  |
| [energetic](../../../traits/instructions/energetic.json) | 0.183 | similar | 1 |  |
| [unplugged](../../../traits/instructions/unplugged.json) (expanded) | 0.179 | unrelated |  |  |
| [emotionally-disengaged](../../../traits/instructions/emotionally_disengaged.json) (expanded) | 0.147 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.139 | opposed |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | 0.130 | opposed |  |  |
| [hands-off](../../../traits/instructions/hands_off.json) (expanded) | 0.126 | opposed |  |  |
| [laid-back](../../../traits/instructions/laid_back.json) (expanded) | 0.105 | opposed |  |  |
| [apathetic](../../../traits/instructions/apathetic.json) (expanded) | 0.058 | opposed |  |  |
| [proactive](../../../traits/instructions/proactive.json) (expanded) | 0.038 | similar | 1 |  |
| [dry](../../../traits/instructions/dry.json) (expanded) | 0.006 | unrelated |  |  |
| [lethargic](../../../traits/instructions/lethargic.json) (expanded) | -0.042 | opposed |  |  |

### lackadaisical (cut-off 4, 9 pairs judged)

Gloss: This means going through life without energy or care, letting tasks slide, doing things halfway, and shrugging off details, deadlines, and effort as not worth the bother.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [careless](../../../traits/instructions/careless.json) | 0.437 | similar | 2 |  |
| [lazy](../../../traits/instructions/lazy.json) | 0.416 | similar | 2 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.416 | similar | 1 |  |
| [burned-out](../../../traits/instructions/burned_out.json) | 0.372 | similar | 2 |  |
| [passive](../../../traits/instructions/passive.json) | 0.371 | similar | 2 |  |
| [slovenly](../../../traits/instructions/slovenly.json) | 0.348 | similar | 1 |  |
| [apathetic](../../../traits/instructions/apathetic.json) | 0.314 | similar | 2 |  |
| [lethargic](../../../traits/instructions/lethargic.json) | 0.302 | similar | 1 |  |
| [health-negligent](../../../traits/instructions/health_negligent.json) | 0.293 | similar | 1 |  |
| [joyless](../../../traits/instructions/joyless.json) | 0.290 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.150 | opposed |  |  |
| [energetic](../../../traits/instructions/energetic.json) (expanded) | 0.142 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | 0.085 | opposed |  |  |
| [health-conscious](../../../traits/instructions/health_conscious.json) (expanded) | 0.073 | opposed |  |  |
| [engaged](../../../traits/instructions/engaged.json) (expanded) | 0.059 | opposed |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | 0.035 | unrelated |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | -0.013 | opposed |  |  |
| [fastidious](../../../traits/instructions/fastidious.json) (expanded) | -0.036 | opposed |  |  |

### laggard (cut-off 3, 4 pairs judged)

Gloss: This means moving slowly through everything, arriving after the others, finishing after the others, and trailing at the back of the group on every task and journey.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [slow-witted](../../../traits/instructions/slow_witted.json) | 0.367 | unrelated |  |  |
| [late-adopter](../../../traits/instructions/late_adopter.json) | 0.356 | similar | 1 |  |
| [unhurried](../../../traits/instructions/unhurried.json) | 0.258 | similar | 2 | 2 |
| [methodical](../../../traits/instructions/methodical.json) | 0.249 | unrelated |  |  |
| [procrastinating](../../../traits/instructions/procrastinating.json) | 0.226 | unrelated | 1 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.224 | unrelated |  |  |
| [lethargic](../../../traits/instructions/lethargic.json) | 0.209 | similar | 2 | 2 |
| [placid](../../../traits/instructions/placid.json) | 0.200 | unrelated |  |  |
| [strategic](../../../traits/instructions/strategic.json) | 0.194 | unrelated |  |  |
| [sloppy](../../../traits/instructions/sloppy.json) | 0.193 | unrelated |  |  |
| [self-starting](../../../traits/instructions/self_starting.json) (expanded) | 0.176 | opposed |  |  |
| [hurried](../../../traits/instructions/hurried.json) (expanded) | 0.170 | opposed |  |  |
| [early-adopter](../../../traits/instructions/early_adopter.json) (expanded) | 0.114 | opposed |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.094 | unrelated |  |  |
| [tactical](../../../traits/instructions/tactical.json) (expanded) | 0.086 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.042 | unrelated |  |  |
| [meticulous](../../../traits/instructions/meticulous.json) (expanded) | 0.033 | unrelated |  |  |
| [quick-witted](../../../traits/instructions/quick_witted.json) (expanded) | 0.030 | unrelated |  |  |
| [irascible](../../../traits/instructions/irascible.json) (expanded) | 0.021 | unrelated |  |  |
| [energetic](../../../traits/instructions/energetic.json) (expanded) | -0.017 | opposed |  |  |

### lax (cut-off 4, 10 pairs judged)

Gloss: This means neglecting duties and letting standards slip through carelessness.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [careless](../../../traits/instructions/careless.json) | 0.610 | similar | 3 | 3 |
| [neglectful](../../../traits/instructions/neglectful.json) | 0.478 | similar | 2 |  |
| [slovenly](../../../traits/instructions/slovenly.json) | 0.440 | similar | 1 |  |
| [health-negligent](../../../traits/instructions/health_negligent.json) | 0.420 | similar | 2 |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) | 0.396 | similar | 2 |  |
| [sloppy](../../../traits/instructions/sloppy.json) | 0.373 | similar | 2 |  |
| [lazy](../../../traits/instructions/lazy.json) | 0.349 | similar | 2 |  |
| [absentee](../../../traits/instructions/absentee.json) | 0.344 | similar | 2 |  |
| [unreliable](../../../traits/instructions/unreliable.json) | 0.284 | similar | 2 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.261 | similar | 0 |  |
| [responsible](../../../traits/instructions/responsible.json) (expanded) | 0.134 | opposed |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | 0.093 | opposed |  |  |
| [nurturing](../../../traits/instructions/nurturing.json) (expanded) | 0.078 | unrelated |  |  |
| [fastidious](../../../traits/instructions/fastidious.json) (expanded) | 0.074 | opposed |  |  |
| [health-conscious](../../../traits/instructions/health_conscious.json) (expanded) | 0.029 | opposed |  |  |
| [dependable](../../../traits/instructions/dependable.json) (expanded) | 0.027 | opposed |  |  |
| [meticulous](../../../traits/instructions/meticulous.json) (expanded) | 0.025 | opposed |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.025 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | 0.020 | opposed |  |  |

### lecherous (cut-off 4, 7 pairs judged)

Gloss: This means pursuing sexual gratification with urgency and without regard for propriety or the wishes of others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [promiscuous](../../../traits/instructions/promiscuous.json) | 0.439 | unrelated |  |  |
| [lustful](../../../traits/instructions/lustful.json) | 0.402 | similar | 2 |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) | 0.363 | similar | 1 |  |
| [impulsive](../../../traits/instructions/impulsive.json) | 0.283 | similar | 1 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.266 | similar | 0 |  |
| [permissive](../../../traits/instructions/permissive.json) | 0.250 | unrelated | 1 |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.248 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) | 0.236 | similar | 1 |  |
| [hurried](../../../traits/instructions/hurried.json) | 0.235 | similar | 0 |  |
| [greedy](../../../traits/instructions/greedy.json) | 0.228 | unrelated |  |  |
| [puritanical](../../../traits/instructions/puritanical.json) (expanded) | 0.218 | opposed |  |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) (expanded) | 0.150 | opposed |  |  |
| [ascetic](../../../traits/instructions/ascetic.json) (expanded) | 0.124 | opposed |  |  |
| [unhurried](../../../traits/instructions/unhurried.json) (expanded) | 0.120 | opposed |  |  |
| [deliberate](../../../traits/instructions/deliberate.json) (expanded) | 0.043 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | -0.002 | opposed |  |  |

### lenten (cut-off 3, 10 pairs judged)

Gloss: This means keeping the season of Lent by fasting and abstaining from meat and other indulgences, giving up comforts and holding to a plain, disciplined table until Easter.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [abstemious](../../../traits/instructions/abstemious.json) | 0.250 | similar | 2 | 2 |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.234 | similar | 2 | 2 |
| [chaste](../../../traits/instructions/chaste.json) | 0.209 | similar | 1 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.201 | similar | 1 |  |
| [frugal](../../../traits/instructions/frugal.json) | 0.182 | similar | 1 |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.175 | unrelated | 0 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.161 | unrelated | 0 |  |
| [health-conscious](../../../traits/instructions/health_conscious.json) | 0.160 | unrelated | 0 |  |
| [spartan](../../../traits/instructions/spartan.json) | 0.151 | similar | 2 | 2 |
| [unplugged](../../../traits/instructions/unplugged.json) | 0.150 | unrelated | 1 |  |
| [gluttonous](../../../traits/instructions/gluttonous.json) (expanded) | 0.112 | opposed |  |  |
| [health-negligent](../../../traits/instructions/health_negligent.json) (expanded) | 0.098 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.089 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.087 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | 0.072 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.059 | opposed |  |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) (expanded) | 0.039 | opposed |  |  |
| [extravagant](../../../traits/instructions/extravagant.json) (expanded) | 0.033 | opposed |  |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) (expanded) | 0.020 | opposed |  |  |
| [epicurean](../../../traits/instructions/epicurean.json) (expanded) | -0.019 | opposed |  |  |

### libertine (cut-off 3, 9 pairs judged)

Gloss: This means pursuing pleasure without regard for moral or sexual convention.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [hedonistic](../../../traits/instructions/hedonistic.json) | 0.411 | similar | 2 | 2 |
| [promiscuous](../../../traits/instructions/promiscuous.json) | 0.410 | similar | 2 | 2 |
| [permissive](../../../traits/instructions/permissive.json) | 0.344 | similar | 2 | 2 |
| [amoral](../../../traits/instructions/amoral.json) | 0.334 | unrelated | 2 | 1 |
| [expedient](../../../traits/instructions/expedient.json) | 0.306 | similar | 1 |  |
| [lustful](../../../traits/instructions/lustful.json) | 0.264 | similar | 2 | 2 |
| [puritanical](../../../traits/instructions/puritanical.json) | 0.254 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) | 0.242 | similar | 2 | 2 |
| [evil](../../../traits/instructions/evil.json) | 0.236 | unrelated | 1 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.218 | similar | 1 |  |
| [chaste](../../../traits/instructions/chaste.json) (expanded) | 0.214 | opposed |  |  |
| [moral](../../../traits/instructions/moral.json) (expanded) | 0.179 | opposed |  |  |
| [ascetic](../../../traits/instructions/ascetic.json) (expanded) | 0.166 | opposed |  |  |
| [good](../../../traits/instructions/good.json) (expanded) | 0.163 | opposed |  |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) (expanded) | 0.118 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.044 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | -0.019 | opposed |  |  |

### lifeless (cut-off 3, 9 pairs judged)

Gloss: This means speaking and moving without energy, enthusiasm, or spark.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [flat](../../../traits/instructions/flat.json) | 0.504 | similar | 2 | 2 |
| [dull](../../../traits/instructions/dull.json) | 0.473 | similar | 2 | 2 |
| [lethargic](../../../traits/instructions/lethargic.json) | 0.351 | similar | 2 | 2 |
| [languishing](../../../traits/instructions/languishing.json) | 0.349 | similar | 1 |  |
| [burned-out](../../../traits/instructions/burned_out.json) | 0.325 | similar | 2 | 2 |
| [dry](../../../traits/instructions/dry.json) | 0.322 | similar | 2 | 1 |
| [joyless](../../../traits/instructions/joyless.json) | 0.304 | similar | 2 | 1 |
| [laid-back](../../../traits/instructions/laid_back.json) | 0.274 | unrelated | 1 |  |
| [animated](../../../traits/instructions/animated.json) | 0.269 | opposed |  |  |
| [humorless](../../../traits/instructions/humorless.json) | 0.268 | unrelated | 1 |  |
| [energetic](../../../traits/instructions/energetic.json) (expanded) | 0.221 | opposed |  |  |
| [intense](../../../traits/instructions/intense.json) (expanded) | 0.144 | opposed |  |  |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.100 | opposed |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.057 | opposed |  |  |
| [witty](../../../traits/instructions/witty.json) (expanded) | 0.054 | opposed |  |  |
| [entertaining](../../../traits/instructions/entertaining.json) (expanded) | 0.048 | opposed |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | -0.012 | opposed |  |  |

### light-footed (cut-off 3, 9 pairs judged)

Gloss: This means treading softly, moving quietly and gently through every space, with steps that barely stir the floor and a presence that rarely announces itself.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [gentle](../../../traits/instructions/gentle.json) | 0.306 | similar | 0 |  |
| [circumspect](../../../traits/instructions/circumspect.json) | 0.278 | similar | 0 |  |
| [placid](../../../traits/instructions/placid.json) | 0.239 | unrelated | 0 |  |
| [calculating](../../../traits/instructions/calculating.json) | 0.219 | opposed |  |  |
| [serene](../../../traits/instructions/serene.json) | 0.211 | unrelated | 1 |  |
| [tactful](../../../traits/instructions/tactful.json) | 0.208 | similar | 0 |  |
| [timid](../../../traits/instructions/timid.json) | 0.207 | unrelated |  |  |
| [diplomatic](../../../traits/instructions/diplomatic.json) | 0.189 | similar | 0 |  |
| [laid-back](../../../traits/instructions/laid_back.json) | 0.176 | similar | 0 |  |
| [peaceful](../../../traits/instructions/peaceful.json) | 0.175 | unrelated | 0 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.118 | similar | 0 |  |
| [intense](../../../traits/instructions/intense.json) (expanded) | 0.082 | opposed |  |  |
| [brash](../../../traits/instructions/brash.json) (expanded) | 0.023 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.021 | opposed |  |  |
| [harsh](../../../traits/instructions/harsh.json) (expanded) | 0.021 | opposed |  |  |
| [irascible](../../../traits/instructions/irascible.json) (expanded) | -0.008 | opposed |  |  |
| [blunt](../../../traits/instructions/blunt.json) (expanded) | -0.010 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | -0.097 | opposed |  |  |

### linear thinker (cut-off 3, 7 pairs judged)

Gloss: This means processing information step by step in logical sequence, moving from one point to the next in orderly fashion.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [methodical](../../../traits/instructions/methodical.json) | 0.509 | similar | 2 | 2 |
| [logical](../../../traits/instructions/logical.json) | 0.444 | similar | 2 | 2 |
| [organized](../../../traits/instructions/organized.json) | 0.360 | similar | 2 | 2 |
| [analytical](../../../traits/instructions/analytical.json) | 0.292 | similar | 2 | 2 |
| [strategic](../../../traits/instructions/strategic.json) | 0.259 | similar | 1 |  |
| [calculating](../../../traits/instructions/calculating.json) | 0.253 | unrelated |  |  |
| [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | 0.239 | opposed |  |  |
| [tactical](../../../traits/instructions/tactical.json) | 0.228 | unrelated |  |  |
| [literal](../../../traits/instructions/literal.json) | 0.223 | similar | 0 |  |
| [expository](../../../traits/instructions/expository.json) | 0.220 | similar | 1 |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | 0.208 | opposed |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.176 | opposed |  |  |
| [illogical](../../../traits/instructions/illogical.json) (expanded) | 0.170 | opposed |  |  |
| [intuitive](../../../traits/instructions/intuitive.json) (expanded) | 0.133 | opposed |  |  |
| [figurative](../../../traits/instructions/figurative.json) (expanded) | 0.111 | unrelated |  |  |
| [narrative](../../../traits/instructions/narrative.json) (expanded) | 0.084 | unrelated |  |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.034 | unrelated |  |  |

Pair completion for: [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json)

### lithe (cut-off 3, 7 pairs judged)

Gloss: This means moving with graceful, easy agility, flowing through every motion with a supple, effortless quality and bending, turning and stepping as if no movement cost any strain.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [eloquent](../../../traits/instructions/eloquent.json) | 0.374 | similar | 0 |  |
| [glib](../../../traits/instructions/glib.json) | 0.319 | unrelated |  |  |
| [serene](../../../traits/instructions/serene.json) | 0.244 | unrelated |  |  |
| [flexible](../../../traits/instructions/flexible.json) | 0.224 | similar | 0 |  |
| [lethargic](../../../traits/instructions/lethargic.json) | 0.214 | opposed |  |  |
| [ethereal](../../../traits/instructions/ethereal.json) | 0.210 | similar | 0 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.206 | unrelated | 0 |  |
| [lighthearted](../../../traits/instructions/lighthearted.json) | 0.205 | unrelated |  |  |
| [easygoing](../../../traits/instructions/easygoing.json) | 0.203 | similar | 0 |  |
| [gentle](../../../traits/instructions/gentle.json) | 0.200 | similar | 0 |  |
| [energetic](../../../traits/instructions/energetic.json) (expanded) | 0.168 | similar | 1 |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.125 | unrelated |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.110 | opposed |  |  |
| [solemn](../../../traits/instructions/solemn.json) (expanded) | 0.104 | unrelated |  |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) (expanded) | 0.077 | unrelated |  |  |
| [grounded](../../../traits/instructions/grounded.json) (expanded) | 0.058 | unrelated |  |  |
| [uptight](../../../traits/instructions/uptight.json) (expanded) | 0.018 | opposed |  |  |
| [rigid](../../../traits/instructions/rigid.json) (expanded) | -0.049 | opposed |  |  |
| [harsh](../../../traits/instructions/harsh.json) (expanded) | -0.052 | opposed |  |  |

### matter of fact (cut-off 3, 10 pairs judged)

Gloss: This means speaking and acting with directness and practicality, without sentiment or embellishment.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [plain-spoken](../../../traits/instructions/plain_spoken.json) | 0.492 | similar | 2 | 2 |
| [blunt](../../../traits/instructions/blunt.json) | 0.463 | similar | 2 | 2 |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.425 | similar | 2 | 2 |
| [clear](../../../traits/instructions/clear.json) | 0.366 | similar | 2 | 2 |
| [grounded](../../../traits/instructions/grounded.json) | 0.360 | similar | 2 | 2 |
| [literal](../../../traits/instructions/literal.json) | 0.359 | similar | 1 |  |
| [concise](../../../traits/instructions/concise.json) | 0.335 | similar | 2 | 2 |
| [dry](../../../traits/instructions/dry.json) | 0.327 | similar | 2 | 2 |
| [earnest](../../../traits/instructions/earnest.json) | 0.321 | similar | 1 |  |
| [flat](../../../traits/instructions/flat.json) | 0.317 | similar | 2 | 2 |
| [animated](../../../traits/instructions/animated.json) (expanded) | 0.121 | opposed |  |  |
| [tactful](../../../traits/instructions/tactful.json) (expanded) | 0.109 | unrelated |  |  |
| [eloquent](../../../traits/instructions/eloquent.json) (expanded) | 0.093 | opposed |  |  |
| [figurative](../../../traits/instructions/figurative.json) (expanded) | 0.051 | opposed |  |  |
| [ethereal](../../../traits/instructions/ethereal.json) (expanded) | 0.034 | opposed |  |  |
| [entertaining](../../../traits/instructions/entertaining.json) (expanded) | 0.022 | opposed |  |  |
| [sardonic](../../../traits/instructions/sardonic.json) (expanded) | 0.021 | unrelated |  |  |
| [verbose](../../../traits/instructions/verbose.json) (expanded) | -0.016 | opposed |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) (expanded) | -0.022 | opposed |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) (expanded) | -0.022 | opposed |  |  |

### merciless (cut-off 4, 8 pairs judged)

Gloss: This means treating others without mercy or compassion, regardless of their suffering or circumstances.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [cruel](../../../traits/instructions/cruel.json) | 0.487 | similar | 2 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.390 | similar | 2 |  |
| [merciful](../../../traits/instructions/merciful.json) | 0.385 | opposed |  |  |
| [callous](../../../traits/instructions/callous.json) | 0.362 | similar | 2 |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) | 0.356 | unrelated | 1 |  |
| [harsh](../../../traits/instructions/harsh.json) | 0.344 | similar | 2 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.338 | similar | 1 |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.332 | opposed |  |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) | 0.328 | unrelated | 2 |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.319 | similar | 2 |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.282 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.177 | opposed |  |  |
| [forgiving](../../../traits/instructions/forgiving.json) (expanded) | 0.161 | opposed |  |  |
| [gentle](../../../traits/instructions/gentle.json) (expanded) | 0.132 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.122 | opposed |  |  |

Pair completion for: [merciful](../../../traits/instructions/merciful.json)

### monist (cut-off 3, 8 pairs judged)

Gloss: This means holding that reality is ultimately one substance or principle, and treating mind and matter, self and world, and the many things of experience as aspects of that single whole.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [materialist](../../../traits/instructions/materialist.json) | 0.292 | opposed |  |  |
| [essentialist](../../../traits/instructions/essentialist.json) | 0.289 | opposed | 0 |  |
| [absolutist](../../../traits/instructions/absolutist.json) | 0.253 | unrelated | 0 |  |
| [metaphysical libertarian](../../../traits/instructions/metaphysical_libertarian.json) | 0.241 | unrelated |  |  |
| [spiritual](../../../traits/instructions/spiritual.json) | 0.218 | unrelated |  |  |
| [exclusivist](../../../traits/instructions/exclusivist.json) | 0.217 | unrelated | 0 |  |
| [rationalist](../../../traits/instructions/rationalist.json) | 0.217 | unrelated |  |  |
| [abstract](../../../traits/instructions/abstract.json) | 0.205 | similar | 0 |  |
| [coherent](../../../traits/instructions/coherent.json) | 0.205 | similar | 0 |  |
| [paradoxical](../../../traits/instructions/paradoxical.json) | 0.193 | opposed |  |  |
| [relativist](../../../traits/instructions/relativist.json) (expanded) | 0.185 | opposed |  |  |
| [constructivist](../../../traits/instructions/constructivist.json) (expanded) | 0.182 | opposed | 0 |  |
| [pluralist](../../../traits/instructions/pluralist.json) (expanded) | 0.172 | opposed |  |  |
| [determinist](../../../traits/instructions/determinist.json) (expanded) | 0.163 | unrelated |  |  |
| [concrete](../../../traits/instructions/concrete.json) (expanded) | 0.148 | opposed |  |  |
| [existentialist](../../../traits/instructions/existentialist.json) (expanded) | 0.130 | opposed | 0 |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) (expanded) | 0.125 | opposed | 0 |  |
| [incoherent](../../../traits/instructions/incoherent.json) (expanded) | 0.070 | opposed |  |  |
| [materialistic](../../../traits/instructions/materialistic.json) (expanded) | 0.055 | unrelated |  |  |

Pair completion for: [materialist](../../../traits/instructions/materialist.json), [paradoxical](../../../traits/instructions/paradoxical.json)

### moralistic (cut-off 3, 8 pairs judged)

Gloss: This means making moral judgments about others' conduct and speaking to them about what is right and wrong.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [moral](../../../traits/instructions/moral.json) | 0.331 | unrelated | 1 |  |
| [candid](../../../traits/instructions/candid.json) | 0.274 | unrelated | 1 |  |
| [judgmental](../../../traits/instructions/judgmental.json) | 0.264 | similar | 2 | 2 |
| [wise](../../../traits/instructions/wise.json) | 0.242 | unrelated | 1 |  |
| [moral relativist](../../../traits/instructions/moral_relativist.json) | 0.241 | opposed |  |  |
| [puritanical](../../../traits/instructions/puritanical.json) | 0.241 | similar | 2 | 2 |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.237 | unrelated |  |  |
| [moral universalist](../../../traits/instructions/moral_universalist.json) | 0.224 | unrelated | 1 |  |
| [good](../../../traits/instructions/good.json) | 0.209 | similar | 2 | 1 |
| [consequentialist](../../../traits/instructions/consequentialist.json) | 0.209 | unrelated |  |  |
| [deontological](../../../traits/instructions/deontological.json) (expanded) | 0.205 | similar | 1 |  |
| [permissive](../../../traits/instructions/permissive.json) (expanded) | 0.175 | opposed |  |  |
| [evil](../../../traits/instructions/evil.json) (expanded) | 0.152 | opposed |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.116 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.070 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.028 | unrelated |  |  |
| [sycophantic](../../../traits/instructions/sycophantic.json) (expanded) | -0.019 | opposed |  |  |

### motivated (cut-off 3, 8 pairs judged)

Gloss: This means having a strong desire or reason driving one toward a goal and acting on it steadily.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [ambitious](../../../traits/instructions/ambitious.json) | 0.314 | similar | 2 | 2 |
| [zealous](../../../traits/instructions/zealous.json) | 0.312 | similar | 2 | 1 |
| [passionate](../../../traits/instructions/passionate.json) | 0.304 | similar | 1 |  |
| [encouraging](../../../traits/instructions/encouraging.json) | 0.268 | similar | 1 |  |
| [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) | 0.266 | unrelated | 0 |  |
| [persevering](../../../traits/instructions/persevering.json) | 0.266 | similar | 2 | 2 |
| [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | 0.258 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) | 0.258 | unrelated |  |  |
| [energetic](../../../traits/instructions/energetic.json) | 0.258 | similar | 1 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.248 | similar | 2 | 2 |
| [defeatist](../../../traits/instructions/defeatist.json) (expanded) | 0.091 | opposed |  |  |
| [chaste](../../../traits/instructions/chaste.json) (expanded) | 0.069 | unrelated |  |  |
| [discouraging](../../../traits/instructions/discouraging.json) (expanded) | 0.066 | opposed |  |  |
| [unambitious](../../../traits/instructions/unambitious.json) (expanded) | 0.060 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.039 | opposed |  |  |
| [temperate](../../../traits/instructions/temperate.json) (expanded) | 0.014 | opposed |  |  |
| [dispassionate](../../../traits/instructions/dispassionate.json) (expanded) | 0.003 | opposed |  |  |
| [lethargic](../../../traits/instructions/lethargic.json) (expanded) | -0.001 | opposed |  |  |

### neat (cut-off 3, 5 pairs judged)

Gloss: This means keeping every space and belonging in order, putting things back where they go, and arranging one's surroundings, papers, and plans so that everything is tidy and easy to find.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [organized](../../../traits/instructions/organized.json) | 0.288 | similar | 2 | 2 |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.227 | similar | 0 |  |
| [settled](../../../traits/instructions/settled.json) | 0.225 | similar | 0 |  |
| [responsible](../../../traits/instructions/responsible.json) | 0.224 | unrelated |  |  |
| [focused](../../../traits/instructions/focused.json) | 0.209 | similar | 0 |  |
| [fastidious](../../../traits/instructions/fastidious.json) | 0.209 | similar | 2 | 2 |
| [accountable](../../../traits/instructions/accountable.json) | 0.197 | unrelated |  |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.197 | unrelated |  |  |
| [homeowner](../../../traits/instructions/homeowner.json) | 0.192 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.178 | opposed |  |  |
| [renter](../../../traits/instructions/renter.json) (expanded) | 0.151 | unrelated |  |  |
| [slovenly](../../../traits/instructions/slovenly.json) (expanded) | 0.150 | opposed |  |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | 0.082 | opposed |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.074 | unrelated |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) (expanded) | 0.060 | unrelated |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | 0.035 | opposed |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | 0.027 | opposed |  |  |

### needy (cut-off 4, 5 pairs judged)

Gloss: This means clinging to others for comfort, asking again and again whether one is liked, valued or still wanted, and needing constant reassurance before feeling steady.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [clingy](../../../traits/instructions/clingy.json) | 0.445 | similar | 2 |  |
| [dependent](../../../traits/instructions/dependent.json) | 0.393 | similar | 2 |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) | 0.304 | unrelated | 1 |  |
| [insecure](../../../traits/instructions/insecure.json) | 0.274 | similar | 2 |  |
| [controlling](../../../traits/instructions/controlling.json) | 0.249 | opposed |  |  |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) | 0.193 | unrelated |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) | 0.187 | unrelated |  |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) | 0.181 | unrelated |  |  |
| [self-pitying](../../../traits/instructions/self_pitying.json) | 0.179 | similar | 1 |  |
| [picky-eater](../../../traits/instructions/picky_eater.json) | 0.178 | unrelated |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) (expanded) | 0.145 | unrelated |  |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) (expanded) | 0.118 | unrelated |  |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) (expanded) | 0.104 | opposed |  |  |
| [self-assured](../../../traits/instructions/self_assured.json) (expanded) | 0.097 | opposed |  |  |
| [independent](../../../traits/instructions/independent.json) (expanded) | 0.088 | opposed |  |  |
| [body-confident](../../../traits/instructions/body_confident.json) (expanded) | 0.073 | unrelated |  |  |
| [adventurous-eater](../../../traits/instructions/adventurous_eater.json) (expanded) | -0.004 | unrelated |  |  |

Pair completion for: [controlling](../../../traits/instructions/controlling.json)

### nepotistic (cut-off 4, 3 pairs judged)

Gloss: This means handing jobs, contracts, and promotions to one's own relatives first, and weighing family ties above merit or fairness whenever a decision about who gets a place comes up.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [clannish](../../../traits/instructions/clannish.json) | 0.336 | similar | 2 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.325 | similar | 2 |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.314 | unrelated |  |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.282 | unrelated |  |  |
| [nationalist](../../../traits/instructions/nationalist.json) | 0.239 | unrelated |  |  |
| [fair](../../../traits/instructions/fair.json) | 0.239 | opposed |  |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.234 | unrelated |  |  |
| [paternalistic](../../../traits/instructions/paternalistic.json) | 0.226 | unrelated | 0 |  |
| [meritocratic](../../../traits/instructions/meritocratic.json) | 0.219 | opposed |  |  |
| [sectarian](../../../traits/instructions/sectarian.json) | 0.214 | unrelated |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.178 | unrelated |  |  |
| [autonomy-respecting](../../../traits/instructions/autonomy_respecting.json) (expanded) | 0.040 | opposed |  |  |

Pair completion for: [meritocratic](../../../traits/instructions/meritocratic.json)

### non directive (cut-off 4, 8 pairs judged)

Gloss: This means framing everything as observation, question, or option, never issuing a command, and leaving each decision and next step for the other person to reach unprompted.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [informational](../../../traits/instructions/informational.json) | 0.280 | unrelated | 2 |  |
| [exploratory](../../../traits/instructions/exploratory.json) | 0.279 | similar | 2 |  |
| [unchallenging](../../../traits/instructions/unchallenging.json) | 0.271 | opposed |  |  |
| [socratic](../../../traits/instructions/socratic.json) | 0.238 | similar | 2 |  |
| [respectful](../../../traits/instructions/respectful.json) | 0.234 | similar | 1 |  |
| [empirical](../../../traits/instructions/empirical.json) | 0.230 | unrelated |  |  |
| [prescriptive](../../../traits/instructions/prescriptive.json) | 0.216 | opposed |  |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.214 | unrelated | 1 |  |
| [descriptive](../../../traits/instructions/descriptive.json) | 0.208 | unrelated | 2 |  |
| [didactic](../../../traits/instructions/didactic.json) | 0.199 | opposed |  |  |
| [challenging](../../../traits/instructions/challenging.json) (expanded) | 0.142 | similar | 1 |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.134 | opposed |  |  |
| [speculative](../../../traits/instructions/speculative.json) (expanded) | 0.110 | similar | 1 |  |
| [rhetorical](../../../traits/instructions/rhetorical.json) (expanded) | 0.088 | opposed |  |  |
| [condescending](../../../traits/instructions/condescending.json) (expanded) | 0.027 | opposed |  |  |

### non judgmental (cut-off 3, 10 pairs judged)

Gloss: This means meeting others without deciding they are right or wrong, good or bad.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [friendly](../../../traits/instructions/friendly.json) | 0.289 | similar | 1 |  |
| [open-minded](../../../traits/instructions/open_minded.json) | 0.272 | similar | 1 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) | 0.248 | similar | 1 |  |
| [fair](../../../traits/instructions/fair.json) | 0.240 | similar | 1 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.230 | similar | 1 |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.222 | similar | 0 |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) | 0.218 | similar | 1 |  |
| [pluralist](../../../traits/instructions/pluralist.json) | 0.213 | similar | 2 | 2 |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) | 0.207 | similar | 1 |  |
| [accommodating](../../../traits/instructions/accommodating.json) | 0.206 | similar | 1 |  |
| [unfair](../../../traits/instructions/unfair.json) (expanded) | 0.113 | opposed |  |  |
| [exclusivist](../../../traits/instructions/exclusivist.json) (expanded) | 0.090 | opposed |  |  |
| [unyielding](../../../traits/instructions/unyielding.json) (expanded) | 0.065 | opposed |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) (expanded) | 0.029 | opposed |  |  |
| [calculating](../../../traits/instructions/calculating.json) (expanded) | -0.017 | opposed |  |  |
| [partisan](../../../traits/instructions/partisan.json) (expanded) | -0.030 | opposed |  |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) (expanded) | -0.037 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | -0.039 | opposed |  |  |
| [hostile](../../../traits/instructions/hostile.json) (expanded) | -0.050 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | -0.074 | opposed |  |  |

### nonmilitary (cut-off 3, 1 pairs judged)

Gloss: This means being a civilian, someone who has never served in the armed forces and lives and works outside military life.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [civil-libertarian](../../../traits/instructions/civil_libertarian.json) | 0.298 | unrelated |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) | 0.282 | unrelated |  |  |
| [childless](../../../traits/instructions/childless.json) | 0.268 | unrelated |  |  |
| [single](../../../traits/instructions/single.json) | 0.250 | unrelated |  |  |
| [pacifist](../../../traits/instructions/pacifist.json) | 0.248 | similar | 0 |  |
| [unschooled](../../../traits/instructions/unschooled.json) | 0.217 | unrelated |  |  |
| [western hemisphere](../../../traits/instructions/western_hemisphere.json) | 0.210 | unrelated |  |  |
| [apolitical](../../../traits/instructions/apolitical.json) | 0.201 | unrelated |  |  |
| [rural](../../../traits/instructions/rural.json) | 0.200 | unrelated |  |  |
| [educated](../../../traits/instructions/educated.json) | 0.198 | unrelated |  |  |
| [urban](../../../traits/instructions/urban.json) (expanded) | 0.164 | unrelated |  |  |
| [married](../../../traits/instructions/married.json) (expanded) | 0.160 | unrelated |  |  |
| [eastern hemisphere](../../../traits/instructions/eastern_hemisphere.json) (expanded) | 0.153 | unrelated |  |  |
| [hawkish](../../../traits/instructions/hawkish.json) (expanded) | 0.135 | unrelated |  |  |
| [parent](../../../traits/instructions/parent.json) (expanded) | 0.102 | unrelated |  |  |
| [political](../../../traits/instructions/political.json) (expanded) | 0.055 | unrelated |  |  |
| [erudite](../../../traits/instructions/erudite.json) (expanded) | 0.046 | unrelated |  |  |
| [authoritarian](../../../traits/instructions/authoritarian.json) (expanded) | 0.045 | unrelated |  |  |

### nonsectarian (cut-off 3, 0 pairs judged)

Gloss: This means belonging to no religious sect or denomination, holding no formal membership in any particular faith body.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [secular](../../../traits/instructions/secular.json) | 0.355 | unrelated |  |  |
| [sectarian](../../../traits/instructions/sectarian.json) | 0.341 | opposed |  |  |
| [rootless](../../../traits/instructions/rootless.json) | 0.305 | unrelated |  |  |
| [apolitical](../../../traits/instructions/apolitical.json) | 0.300 | unrelated |  |  |
| [single](../../../traits/instructions/single.json) | 0.297 | unrelated |  |  |
| [childless](../../../traits/instructions/childless.json) | 0.253 | unrelated |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) | 0.236 | unrelated |  |  |
| [isolated](../../../traits/instructions/isolated.json) | 0.235 | unrelated |  |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.229 | unrelated |  |  |
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.228 | unrelated |  |  |
| [religious](../../../traits/instructions/religious.json) (expanded) | 0.181 | unrelated |  |  |
| [married](../../../traits/instructions/married.json) (expanded) | 0.127 | unrelated |  |  |
| [rooted](../../../traits/instructions/rooted.json) (expanded) | 0.125 | unrelated |  |  |
| [political](../../../traits/instructions/political.json) (expanded) | 0.089 | unrelated |  |  |
| [conformist](../../../traits/instructions/conformist.json) (expanded) | 0.089 | unrelated |  |  |
| [educated](../../../traits/instructions/educated.json) (expanded) | 0.064 | unrelated |  |  |
| [parent](../../../traits/instructions/parent.json) (expanded) | 0.041 | unrelated |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.013 | unrelated |  |  |
| [contrarian](../../../traits/instructions/contrarian.json) (expanded) | 0.012 | unrelated |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.001 | unrelated |  |  |

Pair completion for: [sectarian](../../../traits/instructions/sectarian.json)

### objectivist (cut-off 3, 8 pairs judged)

Gloss: This means holding that objective reality exists independent of minds.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [metaphysical libertarian](../../../traits/instructions/metaphysical_libertarian.json) | 0.333 | unrelated |  |  |
| [materialist](../../../traits/instructions/materialist.json) | 0.308 | similar | 1 |  |
| [absolutist](../../../traits/instructions/absolutist.json) | 0.262 | similar | 1 |  |
| [independent](../../../traits/instructions/independent.json) | 0.232 | unrelated |  |  |
| [essentialist](../../../traits/instructions/essentialist.json) | 0.226 | similar | 1 |  |
| [empirical](../../../traits/instructions/empirical.json) | 0.218 | similar | 0 |  |
| [constructivist](../../../traits/instructions/constructivist.json) | 0.213 | opposed | opposite |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.213 | unrelated |  |  |
| [relativist](../../../traits/instructions/relativist.json) | 0.212 | opposed |  |  |
| [rationalist](../../../traits/instructions/rationalist.json) | 0.204 | similar | 1 |  |
| [existentialist](../../../traits/instructions/existentialist.json) (expanded) | 0.202 | unrelated | 0 |  |
| [determinist](../../../traits/instructions/determinist.json) (expanded) | 0.185 | unrelated |  |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) (expanded) | 0.177 | opposed | 0 |  |
| [speculative](../../../traits/instructions/speculative.json) (expanded) | 0.011 | unrelated |  |  |
| [dependent](../../../traits/instructions/dependent.json) (expanded) | -0.006 | unrelated |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | -0.036 | unrelated |  |  |

### oblique (cut-off 3, 6 pairs judged)

Gloss: This means speaking around a subject rather than naming it directly, leaving one's true meaning to be inferred.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [vague](../../../traits/instructions/vague.json) | 0.359 | similar | 2 | 2 |
| [opaque](../../../traits/instructions/opaque.json) | 0.268 | similar | 1 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.262 | unrelated | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) | 0.250 | unrelated |  |  |
| [enigmatic](../../../traits/instructions/enigmatic.json) | 0.247 | similar | 2 | 2 |
| [diplomatic](../../../traits/instructions/diplomatic.json) | 0.218 | unrelated |  |  |
| [approximate](../../../traits/instructions/approximate.json) | 0.217 | unrelated |  |  |
| [emotionally-inarticulate](../../../traits/instructions/emotionally_inarticulate.json) | 0.216 | unrelated |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) | 0.210 | similar | 2 | 2 |
| [metaphorical](../../../traits/instructions/metaphorical.json) | 0.208 | similar | 1 |  |
| [clear](../../../traits/instructions/clear.json) (expanded) | 0.200 | opposed |  |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | 0.106 | opposed |  |  |
| [precise](../../../traits/instructions/precise.json) (expanded) | 0.091 | opposed |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.087 | unrelated |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.054 | opposed |  |  |
| [emotionally-articulate](../../../traits/instructions/emotionally_articulate.json) (expanded) | 0.052 | unrelated |  |  |

### off putting (cut-off 3, 6 pairs judged)

Gloss: This means having a manner that makes others want to avoid or withdraw from one's presence.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [avoidant](../../../traits/instructions/avoidant.json) | 0.406 | unrelated |  |  |
| [dull](../../../traits/instructions/dull.json) | 0.356 | similar | 1 |  |
| [malign](../../../traits/instructions/malign.json) | 0.265 | similar | 1 |  |
| [unpopular](../../../traits/instructions/unpopular.json) | 0.255 | similar | 1 |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.241 | unrelated | 2 | 2 |
| [cowardly](../../../traits/instructions/cowardly.json) | 0.241 | unrelated |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) | 0.239 | unrelated | 0 |  |
| [timid](../../../traits/instructions/timid.json) | 0.223 | unrelated |  |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) | 0.221 | unrelated |  |  |
| [hostile](../../../traits/instructions/hostile.json) | 0.217 | similar | 2 | 2 |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.141 | opposed |  |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.108 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | 0.104 | opposed |  |  |
| [friendly](../../../traits/instructions/friendly.json) (expanded) | 0.063 | opposed |  |  |
| [benign](../../../traits/instructions/benign.json) (expanded) | 0.053 | opposed |  |  |
| [brave](../../../traits/instructions/brave.json) (expanded) | 0.046 | unrelated |  |  |
| [helpful](../../../traits/instructions/helpful.json) (expanded) | 0.011 | opposed |  |  |
| [body-confident](../../../traits/instructions/body_confident.json) (expanded) | -0.004 | unrelated |  |  |

### opportunistic (cut-off 4, 8 pairs judged)

Gloss: This means seizing chances to advance one's own interests without regard for fairness or the harm done to others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [greedy](../../../traits/instructions/greedy.json) | 0.411 | similar | 2 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.369 | similar | 2 |  |
| [gain-seeking](../../../traits/instructions/gain_seeking.json) | 0.320 | similar | 2 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.313 | similar | 2 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.301 | similar | 2 |  |
| [selfish](../../../traits/instructions/selfish.json) | 0.300 | similar | 2 |  |
| [fair](../../../traits/instructions/fair.json) | 0.246 | opposed |  |  |
| [tactical](../../../traits/instructions/tactical.json) | 0.236 | similar | 1 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.228 | similar | 1 |  |
| [spiteful](../../../traits/instructions/spiteful.json) | 0.228 | unrelated |  |  |
| [strategic](../../../traits/instructions/strategic.json) (expanded) | 0.163 | unrelated |  |  |
| [altruistic](../../../traits/instructions/altruistic.json) (expanded) | 0.061 | opposed |  |  |
| [loss-averse](../../../traits/instructions/loss_averse.json) (expanded) | 0.059 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.055 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.012 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | -0.031 | opposed |  |  |

### ornate (cut-off 3, 9 pairs judged)

Gloss: This means speaking in elaborate, decorative language with rich detail and flourish.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [eloquent](../../../traits/instructions/eloquent.json) | 0.531 | similar | 2 | 2 |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.438 | similar | 2 | 2 |
| [poetic](../../../traits/instructions/poetic.json) | 0.430 | similar | 2 | 2 |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.404 | similar | 2 | 2 |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.373 | similar | 2 | 2 |
| [verbose](../../../traits/instructions/verbose.json) | 0.367 | similar | 2 | 2 |
| [animated](../../../traits/instructions/animated.json) | 0.328 | similar | 1 |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) | 0.325 | opposed |  |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.311 | similar | 2 | 1 |
| [rhetorical](../../../traits/instructions/rhetorical.json) | 0.287 | similar | 2 | 2 |
| [flat](../../../traits/instructions/flat.json) (expanded) | 0.251 | opposed |  |  |
| [concise](../../../traits/instructions/concise.json) (expanded) | 0.169 | opposed |  |  |
| [prosaic](../../../traits/instructions/prosaic.json) (expanded) | 0.143 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.123 | opposed |  |  |
| [informational](../../../traits/instructions/informational.json) (expanded) | 0.006 | opposed |  |  |

### ostentatious (cut-off 3, 8 pairs judged)

Gloss: This means displaying one's possessions, achievements, or manner in ways calculated to impress those watching.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [grandiose](../../../traits/instructions/grandiose.json) | 0.387 | similar | 2 | 2 |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.379 | similar | 2 | 2 |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.353 | similar | 2 | 2 |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.337 | similar | 2 | 2 |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.332 | similar | 2 | 2 |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) | 0.321 | similar | 2 | 2 |
| [modest](../../../traits/instructions/modest.json) | 0.247 | opposed |  |  |
| [competitive](../../../traits/instructions/competitive.json) | 0.242 | unrelated | 1 |  |
| [arrogant](../../../traits/instructions/arrogant.json) | 0.241 | unrelated | 1 |  |
| [dignified](../../../traits/instructions/dignified.json) | 0.228 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.159 | opposed |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) (expanded) | 0.145 | opposed |  |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) (expanded) | 0.122 | opposed |  |  |
| [humble](../../../traits/instructions/humble.json) (expanded) | 0.078 | opposed |  |  |
| [cooperative](../../../traits/instructions/cooperative.json) (expanded) | 0.044 | opposed |  |  |

Pair completion for: [modest](../../../traits/instructions/modest.json)

### overstated (cut-off 4, 9 pairs judged)

Gloss: This means stating things in larger or stronger terms than the facts warrant.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [bombastic](../../../traits/instructions/bombastic.json) | 0.394 | similar | 2 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.350 | similar | 2 |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.332 | similar | 2 |  |
| [emphatic](../../../traits/instructions/emphatic.json) | 0.322 | similar | 2 |  |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.295 | similar | 2 |  |
| [overconfident](../../../traits/instructions/overconfident.json) | 0.273 | similar | 2 |  |
| [verbose](../../../traits/instructions/verbose.json) | 0.268 | unrelated |  |  |
| [grandiose](../../../traits/instructions/grandiose.json) | 0.250 | similar | 2 |  |
| [inaccurate](../../../traits/instructions/inaccurate.json) | 0.249 | unrelated | 1 |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.247 | similar | 2 |  |
| [understated](../../../traits/instructions/understated.json) (expanded) | 0.242 | opposed |  |  |
| [accurate](../../../traits/instructions/accurate.json) (expanded) | 0.100 | opposed |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) (expanded) | 0.090 | opposed |  |  |
| [concise](../../../traits/instructions/concise.json) (expanded) | 0.057 | unrelated |  |  |
| [calibrated](../../../traits/instructions/calibrated.json) (expanded) | 0.043 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.036 | opposed |  |  |

### personally oriented (cut-off 3, 7 pairs judged)

Gloss: This means weighing personal relationships and individual concerns as the primary factors in one's decisions and actions.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.374 | similar | 2 | 2 |
| [environmental](../../../traits/instructions/environmental.json) | 0.335 | unrelated |  |  |
| [humanistic](../../../traits/instructions/humanistic.json) | 0.323 | unrelated | 1 |  |
| [collectivistic](../../../traits/instructions/collectivistic.json) | 0.305 | opposed |  |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.291 | opposed |  |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.258 | opposed |  |  |
| [nationalist](../../../traits/instructions/nationalist.json) | 0.243 | opposed |  |  |
| [selfish](../../../traits/instructions/selfish.json) | 0.234 | unrelated | 1 |  |
| [existentialist](../../../traits/instructions/existentialist.json) | 0.232 | similar | 1 |  |
| [individualistic](../../../traits/instructions/individualistic.json) | 0.229 | similar | 1 |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.217 | opposed |  |  |
| [altruistic](../../../traits/instructions/altruistic.json) (expanded) | 0.146 | opposed |  |  |
| [mechanistic](../../../traits/instructions/mechanistic.json) (expanded) | 0.132 | opposed |  |  |
| [constructivist](../../../traits/instructions/constructivist.json) (expanded) | 0.082 | unrelated | 0 |  |
| [essentialist](../../../traits/instructions/essentialist.json) (expanded) | 0.044 | unrelated | 0 |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) (expanded) | -0.033 | opposed |  |  |

Pair completion for: [regionalist](../../../traits/instructions/regionalist.json), [civilizationist](../../../traits/instructions/civilizationist.json), [nationalist](../../../traits/instructions/nationalist.json)

### pious (cut-off 3, 9 pairs judged)

Gloss: This means living by a deep and sincere devotion to God, structuring one's days around prayer, worship and obedience to sacred teaching, and treating faith as the center of one's character.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [religious](../../../traits/instructions/religious.json) | 0.265 | similar | 2 | 2 |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.249 | similar | 1 |  |
| [reverent](../../../traits/instructions/reverent.json) | 0.241 | similar | 2 | 2 |
| [spartan](../../../traits/instructions/spartan.json) | 0.215 | similar | 0 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.214 | similar | 0 |  |
| [flourishing](../../../traits/instructions/flourishing.json) | 0.205 | unrelated | 0 |  |
| [spiritual](../../../traits/instructions/spiritual.json) | 0.205 | similar | 2 | 2 |
| [family-oriented](../../../traits/instructions/family_oriented.json) | 0.195 | unrelated |  |  |
| [fundamentalist](../../../traits/instructions/fundamentalist.json) | 0.192 | similar | 1 |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.189 | similar | 1 |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) (expanded) | 0.159 | unrelated |  |  |
| [secular](../../../traits/instructions/secular.json) (expanded) | 0.124 | opposed |  |  |
| [languishing](../../../traits/instructions/languishing.json) (expanded) | 0.098 | opposed |  |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) (expanded) | 0.091 | opposed |  |  |
| [epicurean](../../../traits/instructions/epicurean.json) (expanded) | 0.048 | opposed |  |  |
| [irreverent](../../../traits/instructions/irreverent.json) (expanded) | 0.039 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.037 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | 0.033 | opposed |  |  |
| [materialistic](../../../traits/instructions/materialistic.json) (expanded) | 0.022 | opposed |  |  |

### pompous (cut-off 3, 8 pairs judged)

Gloss: This means speaking and acting with excessive self-importance, treating one's words and deeds as grander than they are.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [grandiose](../../../traits/instructions/grandiose.json) | 0.463 | similar | 2 | 2 |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.409 | similar | 2 | 2 |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.391 | similar | 3 | 2 |
| [arrogant](../../../traits/instructions/arrogant.json) | 0.383 | similar | 2 | 2 |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.378 | similar | 2 | 2 |
| [dignified](../../../traits/instructions/dignified.json) | 0.289 | opposed |  |  |
| [self-absorbed](../../../traits/instructions/self_absorbed.json) | 0.265 | unrelated | 1 |  |
| [entitled](../../../traits/instructions/entitled.json) | 0.257 | similar | 1 |  |
| [condescending](../../../traits/instructions/condescending.json) | 0.256 | similar | 1 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.243 | unrelated |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) (expanded) | 0.196 | opposed |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.119 | opposed |  |  |
| [humble](../../../traits/instructions/humble.json) (expanded) | 0.111 | opposed |  |  |
| [respectful](../../../traits/instructions/respectful.json) (expanded) | 0.104 | opposed |  |  |
| [other-focused](../../../traits/instructions/other_focused.json) (expanded) | -0.019 | opposed |  |  |

Pair completion for: [dignified](../../../traits/instructions/dignified.json)

### presumptuous (cut-off 4, 9 pairs judged)

Gloss: This means acting without warrant and overstepping proper bounds.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.310 | similar | 2 |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.300 | unrelated | 1 |  |
| [rude](../../../traits/instructions/rude.json) | 0.222 | unrelated | 1 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.218 | unrelated | 1 |  |
| [brash](../../../traits/instructions/brash.json) | 0.211 | similar | 2 |  |
| [rebellious](../../../traits/instructions/rebellious.json) | 0.208 | similar | 1 |  |
| [reckless](../../../traits/instructions/reckless.json) | 0.200 | similar | 1 |  |
| [overconfident](../../../traits/instructions/overconfident.json) | 0.199 | similar | 2 |  |
| [amoral](../../../traits/instructions/amoral.json) | 0.197 | unrelated | 0 |  |
| [illogical](../../../traits/instructions/illogical.json) | 0.195 | unrelated |  |  |
| [moral](../../../traits/instructions/moral.json) (expanded) | 0.108 | opposed |  |  |
| [fair](../../../traits/instructions/fair.json) (expanded) | 0.102 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.033 | opposed |  |  |
| [obedient](../../../traits/instructions/obedient.json) (expanded) | 0.019 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.018 | opposed |  |  |
| [circumspect](../../../traits/instructions/circumspect.json) (expanded) | 0.014 | opposed |  |  |
| [prudent](../../../traits/instructions/prudent.json) (expanded) | -0.003 | opposed |  |  |
| [logical](../../../traits/instructions/logical.json) (expanded) | -0.005 | unrelated |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | -0.017 | opposed |  |  |
| [calibrated](../../../traits/instructions/calibrated.json) (expanded) | -0.031 | unrelated |  |  |

### psychologically secure (cut-off 3, 7 pairs judged)

Gloss: This means trusting one's own judgment and staying calm when things go wrong.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unflappable](../../../traits/instructions/unflappable.json) | 0.370 | similar | 2 | 2 |
| [composed](../../../traits/instructions/composed.json) | 0.351 | similar | 2 | 2 |
| [wise](../../../traits/instructions/wise.json) | 0.322 | similar | 1 |  |
| [self-assured](../../../traits/instructions/self_assured.json) | 0.289 | similar | 2 | 2 |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.277 | similar | 2 | 2 |
| [trusting](../../../traits/instructions/trusting.json) | 0.266 | unrelated |  |  |
| [strong-stomached](../../../traits/instructions/strong_stomached.json) | 0.261 | unrelated |  |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.257 | similar | 0 |  |
| [self-blaming](../../../traits/instructions/self_blaming.json) | 0.252 | opposed |  |  |
| [prudent](../../../traits/instructions/prudent.json) | 0.251 | similar | 0 |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.122 | opposed |  |  |
| [reckless](../../../traits/instructions/reckless.json) (expanded) | 0.105 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | 0.101 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.077 | opposed |  |  |
| [flustered](../../../traits/instructions/flustered.json) (expanded) | 0.043 | opposed |  |  |
| [insecure](../../../traits/instructions/insecure.json) (expanded) | 0.041 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | -0.032 | unrelated |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.032 | opposed |  |  |
| [squeamish](../../../traits/instructions/squeamish.json) (expanded) | -0.064 | unrelated |  |  |

Pair completion for: [self-blaming](../../../traits/instructions/self_blaming.json)

### realist (cut-off 4, 9 pairs judged)

Gloss: This means seeing things as they are, not as one wishes them to be.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [wise](../../../traits/instructions/wise.json) | 0.283 | similar | 1 |  |
| [literal](../../../traits/instructions/literal.json) | 0.224 | similar | 1 |  |
| [empirical](../../../traits/instructions/empirical.json) | 0.220 | similar | 2 |  |
| [descriptive](../../../traits/instructions/descriptive.json) | 0.208 | similar | 1 |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) | 0.201 | opposed |  |  |
| [sincere](../../../traits/instructions/sincere.json) | 0.194 | similar | 1 |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.193 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.188 | similar | 0 |  |
| [worldly](../../../traits/instructions/worldly.json) | 0.188 | similar | 2 |  |
| [prosaic](../../../traits/instructions/prosaic.json) | 0.184 | similar | 1 |  |
| [jaded](../../../traits/instructions/jaded.json) (expanded) | 0.137 | unrelated | 1 |  |
| [naive](../../../traits/instructions/naive.json) (expanded) | 0.073 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.067 | opposed |  |  |
| [ironic](../../../traits/instructions/ironic.json) (expanded) | 0.063 | opposed |  |  |
| [figurative](../../../traits/instructions/figurative.json) (expanded) | 0.057 | opposed |  |  |
| [pretentious](../../../traits/instructions/pretentious.json) (expanded) | -0.042 | opposed |  |  |
| [speculative](../../../traits/instructions/speculative.json) (expanded) | -0.045 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | -0.066 | unrelated |  |  |
| [prescriptive](../../../traits/instructions/prescriptive.json) (expanded) | -0.074 | unrelated |  |  |
| [poetic](../../../traits/instructions/poetic.json) (expanded) | -0.087 | opposed |  |  |

### realistic (cut-off 4, 5 pairs judged)

Gloss: This means seeing things as they actually are and accepting them without illusion or wishful thinking.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.276 | similar | 1 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.267 | unrelated |  |  |
| [literal](../../../traits/instructions/literal.json) | 0.264 | similar | 0 |  |
| [wise](../../../traits/instructions/wise.json) | 0.258 | similar | 1 |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) | 0.252 | unrelated |  |  |
| [transparent](../../../traits/instructions/transparent.json) | 0.225 | similar | 1 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) | 0.225 | unrelated |  |  |
| [materialist](../../../traits/instructions/materialist.json) | 0.213 | unrelated |  |  |
| [passive](../../../traits/instructions/passive.json) | 0.212 | unrelated |  |  |
| [worldly](../../../traits/instructions/worldly.json) | 0.207 | unrelated | 2 |  |
| [naive](../../../traits/instructions/naive.json) (expanded) | 0.152 | opposed |  |  |
| [jaded](../../../traits/instructions/jaded.json) (expanded) | 0.140 | unrelated |  |  |
| [figurative](../../../traits/instructions/figurative.json) (expanded) | 0.094 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.072 | opposed |  |  |
| [opaque](../../../traits/instructions/opaque.json) (expanded) | 0.065 | unrelated |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.019 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.001 | unrelated |  |  |
| [calculating](../../../traits/instructions/calculating.json) (expanded) | -0.040 | unrelated |  |  |

### reassuring (cut-off 3, 12 pairs judged)

Gloss: This means easing others' worries with a steady, warm presence, naming what is going well, taking fears seriously, and leaving people feeling safer and calmer than when they came.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [easygoing](../../../traits/instructions/easygoing.json) | 0.304 | similar | 1 |  |
| [patient](../../../traits/instructions/patient.json) | 0.258 | similar | 1 |  |
| [serene](../../../traits/instructions/serene.json) | 0.255 | similar | 1 |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.255 | unrelated | 0 |  |
| [calm](../../../traits/instructions/calm.json) | 0.250 | similar | 1 |  |
| [composed](../../../traits/instructions/composed.json) | 0.245 | similar | 1 |  |
| [nurturing](../../../traits/instructions/nurturing.json) | 0.242 | similar | 2 | 2 |
| [compassionate](../../../traits/instructions/compassionate.json) | 0.226 | similar | 2 | 2 |
| [supportive](../../../traits/instructions/supportive.json) | 0.226 | similar | 2 | 2 |
| [laid-back](../../../traits/instructions/laid_back.json) | 0.216 | similar | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.160 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | 0.155 | opposed |  |  |
| [dismissive](../../../traits/instructions/dismissive.json) (expanded) | 0.104 | opposed |  |  |
| [intense](../../../traits/instructions/intense.json) (expanded) | 0.077 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.060 | opposed |  |  |
| [uptight](../../../traits/instructions/uptight.json) (expanded) | 0.058 | opposed |  |  |
| [excitable](../../../traits/instructions/excitable.json) (expanded) | 0.023 | opposed |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.017 | opposed | opposite |  |
| [neglectful](../../../traits/instructions/neglectful.json) (expanded) | -0.007 | opposed |  |  |
| [impatient](../../../traits/instructions/impatient.json) (expanded) | -0.030 | opposed |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | -0.063 | opposed | opposite |  |

### repellent (cut-off 3, 8 pairs judged)

Gloss: This means having a manner that makes others want to avoid one's company or keep one at a distance.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dull](../../../traits/instructions/dull.json) | 0.340 | similar | 1 |  |
| [unpopular](../../../traits/instructions/unpopular.json) | 0.329 | similar | 1 |  |
| [malign](../../../traits/instructions/malign.json) | 0.313 | similar | 1 |  |
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.308 | similar | 2 | 2 |
| [isolated](../../../traits/instructions/isolated.json) | 0.260 | similar | 1 |  |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.245 | unrelated |  |  |
| [unhappily-partnered](../../../traits/instructions/unhappily_partnered.json) | 0.244 | unrelated |  |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) | 0.239 | similar | 1 |  |
| [hostile](../../../traits/instructions/hostile.json) | 0.224 | similar | 1 |  |
| [rude](../../../traits/instructions/rude.json) | 0.214 | similar | 1 |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.156 | opposed |  |  |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.121 | opposed |  |  |
| [friendly](../../../traits/instructions/friendly.json) (expanded) | 0.118 | opposed |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.118 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | 0.109 | opposed |  |  |
| [benign](../../../traits/instructions/benign.json) (expanded) | 0.089 | opposed |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.059 | opposed |  |  |
| [happily-partnered](../../../traits/instructions/happily_partnered.json) (expanded) | 0.015 | unrelated |  |  |
| [helpful](../../../traits/instructions/helpful.json) (expanded) | 0.003 | opposed |  |  |

### results oriented (cut-off 3, 6 pairs judged)

Gloss: This means prioritizing concrete outcomes and measurable achievements over process, discussion, or other concerns.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [efficient](../../../traits/instructions/efficient.json) | 0.430 | similar | 2 | 2 |
| [practical](../../../traits/instructions/practical.json) | 0.397 | similar | 2 | 2 |
| [performance-oriented](../../../traits/instructions/performance_oriented.json) | 0.389 | similar | 2 | 2 |
| [pragmatic](../../../traits/instructions/pragmatic.json) | 0.389 | similar | 2 | 2 |
| [formalist](../../../traits/instructions/formalist.json) | 0.344 | unrelated |  |  |
| [abstract](../../../traits/instructions/abstract.json) | 0.300 | opposed |  |  |
| [career-oriented](../../../traits/instructions/career_oriented.json) | 0.283 | unrelated |  |  |
| [short-term oriented](../../../traits/instructions/short_term_oriented.json) | 0.278 | unrelated |  |  |
| [materialist](../../../traits/instructions/materialist.json) | 0.260 | similar | 1 |  |
| [competitive](../../../traits/instructions/competitive.json) | 0.258 | unrelated |  |  |
| [concrete](../../../traits/instructions/concrete.json) (expanded) | 0.247 | similar | 0 |  |
| [learning-oriented](../../../traits/instructions/learning_oriented.json) (expanded) | 0.217 | unrelated |  |  |
| [theoretical](../../../traits/instructions/theoretical.json) (expanded) | 0.194 | opposed |  |  |
| [cooperative](../../../traits/instructions/cooperative.json) (expanded) | 0.153 | unrelated |  |  |
| [family-oriented](../../../traits/instructions/family_oriented.json) (expanded) | 0.142 | unrelated |  |  |
| [long-term oriented](../../../traits/instructions/long_term_oriented.json) (expanded) | 0.138 | unrelated |  |  |
| [idealistic](../../../traits/instructions/idealistic.json) (expanded) | 0.111 | opposed |  |  |

### reticent (cut-off 4, 8 pairs judged)

Gloss: This means holding back words and keeping one's thoughts and knowledge to oneself.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [reserved](../../../traits/instructions/reserved.json) | 0.478 | similar | 2 |  |
| [opaque](../../../traits/instructions/opaque.json) | 0.410 | similar | 3 | 3 |
| [guarded](../../../traits/instructions/guarded.json) | 0.369 | similar | 2 |  |
| [circumspect](../../../traits/instructions/circumspect.json) | 0.328 | similar | 2 |  |
| [temperate](../../../traits/instructions/temperate.json) | 0.298 | similar | 1 |  |
| [stingy](../../../traits/instructions/stingy.json) | 0.291 | similar | 1 |  |
| [understated](../../../traits/instructions/understated.json) | 0.266 | similar | 1 |  |
| [retentive](../../../traits/instructions/retentive.json) | 0.231 | unrelated |  |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.226 | unrelated |  |  |
| [enigmatic](../../../traits/instructions/enigmatic.json) | 0.224 | similar | 1 |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.124 | opposed |  |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | 0.105 | opposed |  |  |
| [brash](../../../traits/instructions/brash.json) (expanded) | 0.060 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.053 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | -0.001 | unrelated |  |  |
| [generous](../../../traits/instructions/generous.json) (expanded) | -0.002 | opposed |  |  |
| [forgetful](../../../traits/instructions/forgetful.json) (expanded) | -0.015 | unrelated |  |  |
| [zealous](../../../traits/instructions/zealous.json) (expanded) | -0.020 | opposed |  |  |
| [emphatic](../../../traits/instructions/emphatic.json) (expanded) | -0.046 | opposed |  |  |

### retributive (cut-off 4, 6 pairs judged)

Gloss: This means holding that wrongdoers must answer for what they have done, keeping a ledger of harms suffered, and insisting that every injury be repaid with a punishment to match.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [accountable](../../../traits/instructions/accountable.json) | 0.394 | unrelated |  |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) | 0.385 | similar | 2 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.356 | unrelated | 0 |  |
| [remorseful](../../../traits/instructions/remorseful.json) | 0.298 | unrelated | 1 |  |
| [just-world-believing](../../../traits/instructions/just_world_believing.json) | 0.294 | similar | 1 |  |
| [moral](../../../traits/instructions/moral.json) | 0.282 | unrelated | 1 |  |
| [vindictive](../../../traits/instructions/vindictive.json) | 0.253 | unrelated |  |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.252 | opposed |  |  |
| [fair](../../../traits/instructions/fair.json) | 0.248 | unrelated | 1 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.206 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.200 | opposed |  |  |
| [forgiving](../../../traits/instructions/forgiving.json) (expanded) | 0.158 | opposed |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.113 | opposed |  |  |

### revolutionary (cut-off 4, 8 pairs judged)

Gloss: This means advocating or taking part in violent overthrow of the established regime.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [radical](../../../traits/instructions/radical.json) | 0.489 | similar | 2 |  |
| [subversive](../../../traits/instructions/subversive.json) | 0.357 | unrelated |  |  |
| [extremist](../../../traits/instructions/extremist.json) | 0.301 | similar | 2 |  |
| [progressive](../../../traits/instructions/progressive.json) | 0.276 | similar | 1 |  |
| [iconoclastic](../../../traits/instructions/iconoclastic.json) | 0.272 | similar | 2 |  |
| [rebellious](../../../traits/instructions/rebellious.json) | 0.259 | similar | 1 |  |
| [pacifist](../../../traits/instructions/pacifist.json) | 0.243 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) | 0.239 | similar | 1 |  |
| [egalitarian](../../../traits/instructions/egalitarian.json) | 0.231 | unrelated | 0 |  |
| [partisan](../../../traits/instructions/partisan.json) | 0.231 | unrelated |  |  |
| [hawkish](../../../traits/instructions/hawkish.json) (expanded) | 0.204 | similar | 1 |  |
| [conservative](../../../traits/instructions/conservative.json) (expanded) | 0.147 | opposed |  |  |
| [incrementalist](../../../traits/instructions/incrementalist.json) (expanded) | 0.137 | opposed |  |  |
| [peaceful](../../../traits/instructions/peaceful.json) (expanded) | 0.115 | opposed |  |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) (expanded) | 0.106 | unrelated |  |  |
| [elitist](../../../traits/instructions/elitist.json) (expanded) | 0.089 | opposed |  |  |
| [moderate](../../../traits/instructions/moderate.json) (expanded) | 0.077 | opposed |  |  |
| [obedient](../../../traits/instructions/obedient.json) (expanded) | -0.001 | opposed |  |  |

### rigorous (cut-off 4, 10 pairs judged)

Gloss: This means checking every claim against its evidence, defining terms before using them, working through each step of an argument in order, and leaving no detail unexamined or loosely stated.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [logical](../../../traits/instructions/logical.json) | 0.434 | similar | 2 |  |
| [coherent](../../../traits/instructions/coherent.json) | 0.373 | similar | 1 |  |
| [skeptical](../../../traits/instructions/skeptical.json) | 0.309 | similar | 2 |  |
| [accurate](../../../traits/instructions/accurate.json) | 0.305 | similar | 2 |  |
| [course-correcting](../../../traits/instructions/course_correcting.json) | 0.292 | similar | 1 |  |
| [critical](../../../traits/instructions/critical.json) | 0.247 | similar | 1 |  |
| [empirical](../../../traits/instructions/empirical.json) | 0.241 | similar | 2 |  |
| [data-driven](../../../traits/instructions/data_driven.json) | 0.235 | similar | 2 |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.234 | similar | 2 |  |
| [methodical](../../../traits/instructions/methodical.json) | 0.222 | similar | 2 |  |
| [credulous](../../../traits/instructions/credulous.json) (expanded) | 0.158 | opposed |  |  |
| [incoherent](../../../traits/instructions/incoherent.json) (expanded) | 0.140 | opposed |  |  |
| [anecdotal](../../../traits/instructions/anecdotal.json) (expanded) | 0.099 | opposed |  |  |
| [speculative](../../../traits/instructions/speculative.json) (expanded) | 0.097 | opposed |  |  |
| [inaccurate](../../../traits/instructions/inaccurate.json) (expanded) | 0.061 | opposed |  |  |
| [illogical](../../../traits/instructions/illogical.json) (expanded) | 0.049 | opposed |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.045 | opposed |  |  |
| [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json) (expanded) | 0.032 | opposed |  |  |
| [uncritical](../../../traits/instructions/uncritical.json) (expanded) | 0.006 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | -0.025 | opposed |  |  |

### rule bound (cut-off 4, 9 pairs judged)

Gloss: This means following rules and regulations without exception or deviation.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rule-abiding](../../../traits/instructions/rule_abiding.json) | 0.400 | similar | 3 | 3 |
| [rigid](../../../traits/instructions/rigid.json) | 0.364 | similar | 2 |  |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.361 | similar | 2 |  |
| [obedient](../../../traits/instructions/obedient.json) | 0.298 | similar | 2 |  |
| [fundamentalist](../../../traits/instructions/fundamentalist.json) | 0.296 | similar | 2 |  |
| [strict](../../../traits/instructions/strict.json) | 0.289 | similar | 1 |  |
| [formulaic](../../../traits/instructions/formulaic.json) | 0.287 | unrelated | 1 |  |
| [absolutist](../../../traits/instructions/absolutist.json) | 0.282 | similar | 2 |  |
| [fair](../../../traits/instructions/fair.json) | 0.275 | similar | 1 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.274 | opposed |  |  |
| [unfair](../../../traits/instructions/unfair.json) (expanded) | 0.110 | opposed |  |  |
| [rebellious](../../../traits/instructions/rebellious.json) (expanded) | 0.096 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | 0.087 | opposed |  |  |
| [spontaneous](../../../traits/instructions/spontaneous.json) (expanded) | 0.047 | opposed |  |  |
| [lenient](../../../traits/instructions/lenient.json) (expanded) | 0.033 | opposed |  |  |
| [relativist](../../../traits/instructions/relativist.json) (expanded) | -0.009 | opposed |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | -0.037 | opposed |  |  |

### sadomasochistic (cut-off 4, 9 pairs judged)

Gloss: This means taking pleasure in both giving and receiving pain, seeking out cruelty and suffering in either direction and finding gratification in the hurt itself.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [cruel](../../../traits/instructions/cruel.json) | 0.466 | similar | 2 |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.350 | similar | 2 |  |
| [evil](../../../traits/instructions/evil.json) | 0.300 | similar | 1 |  |
| [spiteful](../../../traits/instructions/spiteful.json) | 0.269 | similar | 1 |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) | 0.220 | similar | 0 |  |
| [merciful](../../../traits/instructions/merciful.json) | 0.212 | opposed |  |  |
| [vindictive](../../../traits/instructions/vindictive.json) | 0.207 | similar | 1 |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) | 0.202 | unrelated | 1 |  |
| [ruthless while playing](../../../traits/instructions/ruthless_while_playing.json) | 0.201 | similar | 0 |  |
| [epicurean](../../../traits/instructions/epicurean.json) | 0.199 | unrelated |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.146 | unrelated | 1 |  |
| [ascetic](../../../traits/instructions/ascetic.json) (expanded) | 0.102 | opposed |  |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | 0.095 | opposed |  |  |
| [spartan](../../../traits/instructions/spartan.json) (expanded) | 0.085 | unrelated |  |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) (expanded) | 0.069 | opposed |  |  |
| [good](../../../traits/instructions/good.json) (expanded) | 0.050 | opposed |  |  |
| [honorable while playing](../../../traits/instructions/honorable_while_playing.json) (expanded) | 0.026 | opposed |  |  |

Pair completion for: [merciful](../../../traits/instructions/merciful.json)

### safe (cut-off 4, 9 pairs judged)

Gloss: This means being trustworthy in every dealing, keeping one's word, and acting with care so that no one is hurt by what one says or does.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [trustworthy](../../../traits/instructions/trustworthy.json) | 0.533 | similar | 2 |  |
| [dependable](../../../traits/instructions/dependable.json) | 0.445 | similar | 2 |  |
| [truthful](../../../traits/instructions/truthful.json) | 0.407 | similar | 2 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.386 | similar | 2 |  |
| [honest](../../../traits/instructions/honest.json) | 0.354 | similar | 2 |  |
| [loyal](../../../traits/instructions/loyal.json) | 0.349 | similar | 2 |  |
| [honorable while playing](../../../traits/instructions/honorable_while_playing.json) | 0.311 | similar | 1 |  |
| [trusting](../../../traits/instructions/trusting.json) | 0.305 | unrelated |  |  |
| [responsible](../../../traits/instructions/responsible.json) | 0.300 | similar | 2 |  |
| [accountable](../../../traits/instructions/accountable.json) | 0.299 | similar | 1 |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) (expanded) | 0.245 | opposed |  |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.224 | opposed |  |  |
| [treacherous](../../../traits/instructions/treacherous.json) (expanded) | 0.172 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.157 | opposed |  |  |
| [deceitful](../../../traits/instructions/deceitful.json) (expanded) | 0.119 | opposed |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) (expanded) | 0.065 | opposed |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) (expanded) | 0.047 | opposed |  |  |
| [ruthless while playing](../../../traits/instructions/ruthless_while_playing.json) (expanded) | 0.033 | opposed |  |  |
| [cynical](../../../traits/instructions/cynical.json) (expanded) | -0.007 | unrelated |  |  |

### schmaltzy (cut-off 3, 8 pairs judged)

Gloss: This means speaking in gushing, syrupy sentiment, pouring warm emotion over every remark, and reaching for tender memories, heartfelt endearments, and swelling declarations of affection whatever the occasion.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [effusive](../../../traits/instructions/effusive.json) | 0.379 | similar | 2 | 2 |
| [sentimental](../../../traits/instructions/sentimental.json) | 0.341 | similar | 1 |  |
| [melodramatic](../../../traits/instructions/melodramatic.json) | 0.335 | similar | 2 | 2 |
| [glib](../../../traits/instructions/glib.json) | 0.323 | opposed |  |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.284 | similar | 1 |  |
| [eloquent](../../../traits/instructions/eloquent.json) | 0.283 | unrelated | 0 |  |
| [flirty](../../../traits/instructions/flirty.json) | 0.278 | unrelated |  |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.264 | similar | 1 |  |
| [intense](../../../traits/instructions/intense.json) | 0.256 | similar | 1 |  |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.255 | similar | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.192 | opposed |  |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) (expanded) | 0.189 | opposed |  |  |
| [unsentimental](../../../traits/instructions/unsentimental.json) (expanded) | 0.125 | opposed |  |  |
| [laid-back](../../../traits/instructions/laid_back.json) (expanded) | 0.092 | opposed |  |  |

Pair completion for: [glib](../../../traits/instructions/glib.json)

### scholarly (cut-off 3, 10 pairs judged)

Gloss: This means engaging in careful intellectual work and pursuing learning through study.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [erudite](../../../traits/instructions/erudite.json) | 0.338 | similar | 2 | 2 |
| [educated](../../../traits/instructions/educated.json) | 0.328 | similar | 1 |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) | 0.316 | similar | 1 |  |
| [learning-oriented](../../../traits/instructions/learning_oriented.json) | 0.289 | similar | 2 | 1 |
| [philosophical](../../../traits/instructions/philosophical.json) | 0.272 | similar | 2 | 2 |
| [curious](../../../traits/instructions/curious.json) | 0.241 | similar | 2 | 2 |
| [highbrow](../../../traits/instructions/highbrow.json) | 0.221 | similar | 1 |  |
| [abstract](../../../traits/instructions/abstract.json) | 0.219 | similar | 1 |  |
| [introspective](../../../traits/instructions/introspective.json) | 0.210 | similar | 1 |  |
| [educational](../../../traits/instructions/educational.json) | 0.207 | similar | 1 |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) (expanded) | 0.182 | opposed |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) (expanded) | 0.144 | opposed |  |  |
| [incurious](../../../traits/instructions/incurious.json) (expanded) | 0.108 | opposed |  |  |
| [unschooled](../../../traits/instructions/unschooled.json) (expanded) | 0.086 | opposed |  |  |
| [performance-oriented](../../../traits/instructions/performance_oriented.json) (expanded) | 0.055 | opposed |  |  |
| [lowbrow](../../../traits/instructions/lowbrow.json) (expanded) | 0.032 | opposed |  |  |
| [concrete](../../../traits/instructions/concrete.json) (expanded) | 0.011 | unrelated |  |  |
| [unreflective](../../../traits/instructions/unreflective.json) (expanded) | -0.023 | opposed |  |  |

### scripted (cut-off 3, 9 pairs judged)

Gloss: This means planning one's words and actions beforehand rather than speaking or acting in the moment.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [deliberate](../../../traits/instructions/deliberate.json) | 0.432 | similar | 2 | 2 |
| [circumspect](../../../traits/instructions/circumspect.json) | 0.367 | similar | 2 | 2 |
| [calculating](../../../traits/instructions/calculating.json) | 0.360 | similar | 2 | 2 |
| [organized](../../../traits/instructions/organized.json) | 0.313 | similar | 2 | 1 |
| [prudent](../../../traits/instructions/prudent.json) | 0.296 | unrelated | 1 |  |
| [tactful](../../../traits/instructions/tactful.json) | 0.288 | similar | 1 |  |
| [scheming](../../../traits/instructions/scheming.json) | 0.249 | unrelated |  |  |
| [methodical](../../../traits/instructions/methodical.json) | 0.248 | similar | 2 | 2 |
| [reserved](../../../traits/instructions/reserved.json) | 0.239 | unrelated | 1 |  |
| [proactive](../../../traits/instructions/proactive.json) | 0.221 | unrelated | 1 |  |
| [reactive](../../../traits/instructions/reactive.json) (expanded) | 0.203 | opposed |  |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.150 | opposed |  |  |
| [impulsive](../../../traits/instructions/impulsive.json) (expanded) | 0.136 | opposed |  |  |
| [improvisational](../../../traits/instructions/improvisational.json) (expanded) | 0.132 | opposed |  |  |
| [brash](../../../traits/instructions/brash.json) (expanded) | 0.109 | opposed |  |  |
| [reckless](../../../traits/instructions/reckless.json) (expanded) | 0.065 | opposed |  |  |
| [blunt](../../../traits/instructions/blunt.json) (expanded) | 0.037 | unrelated |  |  |
| [guileless](../../../traits/instructions/guileless.json) (expanded) | 0.024 | unrelated |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.009 | opposed |  |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | -0.019 | opposed |  |  |

### scrupulous (cut-off 4, 9 pairs judged)

Gloss: This means being conscientious and honest in one's conduct, attending carefully to what is right.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [conscientious](../../../traits/instructions/conscientious.json) | 0.552 | similar | 2 |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) | 0.372 | similar | 2 |  |
| [truthful](../../../traits/instructions/truthful.json) | 0.305 | similar | 2 |  |
| [honest](../../../traits/instructions/honest.json) | 0.303 | similar | 2 |  |
| [responsible](../../../traits/instructions/responsible.json) | 0.289 | similar | 2 |  |
| [meticulous](../../../traits/instructions/meticulous.json) | 0.288 | similar | 1 |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) | 0.279 | similar | 2 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.276 | similar | 2 |  |
| [accountable](../../../traits/instructions/accountable.json) | 0.273 | similar | 1 |  |
| [earnest](../../../traits/instructions/earnest.json) | 0.256 | unrelated |  |  |
| [careless](../../../traits/instructions/careless.json) (expanded) | 0.153 | opposed |  |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) (expanded) | 0.122 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.120 | opposed |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) (expanded) | 0.068 | opposed |  |  |
| [deceitful](../../../traits/instructions/deceitful.json) (expanded) | 0.063 | opposed |  |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) (expanded) | 0.037 | opposed |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) (expanded) | 0.013 | opposed |  |  |
| [sloppy](../../../traits/instructions/sloppy.json) (expanded) | -0.031 | opposed |  |  |
| [sardonic](../../../traits/instructions/sardonic.json) (expanded) | -0.112 | unrelated |  |  |

### self accountable (cut-off 4, 6 pairs judged)

Gloss: This means holding oneself to account for one's actions and accepting responsibility for their consequences.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [accountable](../../../traits/instructions/accountable.json) | 0.596 | similar | 3 | 3 |
| [responsible](../../../traits/instructions/responsible.json) | 0.408 | similar | 2 |  |
| [remorseful](../../../traits/instructions/remorseful.json) | 0.369 | similar | 2 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.352 | unrelated |  |  |
| [self-blaming](../../../traits/instructions/self_blaming.json) | 0.338 | opposed |  |  |
| [mature](../../../traits/instructions/mature.json) | 0.268 | similar | 2 |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) | 0.233 | unrelated | 1 |  |
| [self-reliant](../../../traits/instructions/self_reliant.json) | 0.228 | unrelated |  |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.226 | similar | 1 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.220 | opposed |  |  |
| [forgiving](../../../traits/instructions/forgiving.json) (expanded) | 0.209 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.172 | unrelated |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) (expanded) | 0.141 | opposed |  |  |
| [immature](../../../traits/instructions/immature.json) (expanded) | 0.100 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.096 | opposed |  |  |
| [collaborative](../../../traits/instructions/collaborative.json) (expanded) | -0.037 | unrelated |  |  |

Pair completion for: [self-blaming](../../../traits/instructions/self_blaming.json)

### self interested (cut-off 4, 9 pairs judged)

Gloss: This means prioritizing one's own advantage over others' welfare.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [selfish](../../../traits/instructions/selfish.json) | 0.565 | similar | 3 | 3 |
| [greedy](../../../traits/instructions/greedy.json) | 0.420 | similar | 2 |  |
| [nationalist](../../../traits/instructions/nationalist.json) | 0.387 | similar | 1 |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.360 | similar | 1 |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.359 | similar | 1 |  |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.319 | similar | 2 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.304 | similar | 2 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.287 | similar | 2 |  |
| [anthropocentric](../../../traits/instructions/anthropocentric.json) | 0.283 | unrelated | 1 |  |
| [altruistic](../../../traits/instructions/altruistic.json) | 0.268 | opposed |  |  |
| [ecocentric](../../../traits/instructions/ecocentric.json) (expanded) | 0.166 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.151 | opposed |  |  |
| [fair](../../../traits/instructions/fair.json) (expanded) | 0.141 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.051 | opposed |  |  |

### self promoting (cut-off 4, 9 pairs judged)

Gloss: This means advancing one's own interests and reputation whenever the chance arises.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [selfish](../../../traits/instructions/selfish.json) | 0.302 | similar | 2 |  |
| [gain-seeking](../../../traits/instructions/gain_seeking.json) | 0.290 | similar | 2 |  |
| [greedy](../../../traits/instructions/greedy.json) | 0.287 | similar | 1 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.267 | similar | 1 |  |
| [calculating](../../../traits/instructions/calculating.json) | 0.252 | similar | 2 |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) | 0.246 | similar | 2 |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.240 | unrelated |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) | 0.236 | similar | 2 |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) | 0.232 | similar | 0 |  |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.231 | similar | 2 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) (expanded) | 0.125 | opposed |  |  |
| [altruistic](../../../traits/instructions/altruistic.json) (expanded) | 0.114 | opposed |  |  |
| [honorable](../../../traits/instructions/honorable.json) (expanded) | 0.101 | opposed |  |  |
| [unambitious](../../../traits/instructions/unambitious.json) (expanded) | 0.093 | opposed |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) (expanded) | 0.061 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.048 | unrelated |  |  |
| [loss-averse](../../../traits/instructions/loss_averse.json) (expanded) | 0.012 | unrelated |  |  |

### self satisfied (cut-off 3, 9 pairs judged)

Gloss: This means resting in the belief that one's worth and achievements need no improvement or examination.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [self-assured](../../../traits/instructions/self_assured.json) | 0.448 | similar | 1 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.414 | unrelated | 2 | 2 |
| [contented](../../../traits/instructions/contented.json) | 0.279 | similar | 1 |  |
| [self-certain](../../../traits/instructions/self_certain.json) | 0.265 | similar | 1 |  |
| [body-confident](../../../traits/instructions/body_confident.json) | 0.259 | similar | 1 |  |
| [fixed-minded](../../../traits/instructions/fixed_minded.json) | 0.254 | similar | 1 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.248 | similar | 1 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.225 | unrelated |  |  |
| [self-reliant](../../../traits/instructions/self_reliant.json) | 0.224 | similar | 0 |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.220 | opposed |  |  |
| [insecure](../../../traits/instructions/insecure.json) (expanded) | 0.210 | opposed |  |  |
| [growth-minded](../../../traits/instructions/growth_minded.json) (expanded) | 0.149 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | 0.134 | similar | 2 | 1 |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) (expanded) | 0.124 | opposed |  |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) (expanded) | 0.116 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.115 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.090 | opposed |  |  |
| [discontented](../../../traits/instructions/discontented.json) (expanded) | 0.076 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.052 | unrelated |  |  |
| [collaborative](../../../traits/instructions/collaborative.json) (expanded) | -0.092 | opposed |  |  |

### self-regulating (cut-off 4, 8 pairs judged)

Gloss: This means holding one's impulses in check, choosing deliberately how to act instead of reacting on the spur of the moment, and keeping one's own behavior steady under pressure or temptation.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [deliberate](../../../traits/instructions/deliberate.json) | 0.479 | similar | 2 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.394 | similar | 2 |  |
| [impulsive](../../../traits/instructions/impulsive.json) | 0.281 | opposed |  |  |
| [mature](../../../traits/instructions/mature.json) | 0.259 | similar | 2 |  |
| [temperate](../../../traits/instructions/temperate.json) | 0.248 | unrelated |  |  |
| [wise](../../../traits/instructions/wise.json) | 0.243 | similar | 1 |  |
| [chaste](../../../traits/instructions/chaste.json) | 0.208 | similar | 1 |  |
| [metaphysical libertarian](../../../traits/instructions/metaphysical_libertarian.json) | 0.204 | similar | 0 |  |
| [abstemious](../../../traits/instructions/abstemious.json) | 0.196 | similar | 2 |  |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.196 | similar | 1 |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.121 | opposed |  |  |
| [hedonistic](../../../traits/instructions/hedonistic.json) (expanded) | 0.112 | opposed |  |  |
| [determinist](../../../traits/instructions/determinist.json) (expanded) | 0.095 | opposed |  |  |
| [immature](../../../traits/instructions/immature.json) (expanded) | 0.078 | opposed |  |  |
| [foolish](../../../traits/instructions/foolish.json) (expanded) | 0.059 | opposed |  |  |
| [gluttonous](../../../traits/instructions/gluttonous.json) (expanded) | 0.040 | opposed |  |  |
| [lustful](../../../traits/instructions/lustful.json) (expanded) | 0.022 | opposed |  |  |
| [zealous](../../../traits/instructions/zealous.json) (expanded) | -0.043 | unrelated |  |  |

### selfless (cut-off 4, 7 pairs judged)

Gloss: This means putting others' welfare ahead of one's own interests.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [altruistic](../../../traits/instructions/altruistic.json) | 0.461 | similar | 3 | 3 |
| [selfish](../../../traits/instructions/selfish.json) | 0.379 | opposed |  |  |
| [helpful](../../../traits/instructions/helpful.json) | 0.358 | similar | 2 |  |
| [collectivistic](../../../traits/instructions/collectivistic.json) | 0.333 | similar | 2 |  |
| [humanitarian](../../../traits/instructions/humanitarian.json) | 0.318 | similar | 2 |  |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.313 | similar | 1 |  |
| [civilizationist](../../../traits/instructions/civilizationist.json) | 0.308 | opposed |  |  |
| [philanthropic](../../../traits/instructions/philanthropic.json) | 0.296 | similar | 2 |  |
| [regionalist](../../../traits/instructions/regionalist.json) | 0.295 | opposed |  |  |
| [other-focused](../../../traits/instructions/other_focused.json) | 0.282 | similar | 2 |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.158 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.157 | opposed |  |  |
| [individualistic](../../../traits/instructions/individualistic.json) (expanded) | 0.056 | opposed |  |  |
| [self-absorbed](../../../traits/instructions/self_absorbed.json) (expanded) | 0.022 | opposed |  |  |

Pair completion for: [civilizationist](../../../traits/instructions/civilizationist.json), [regionalist](../../../traits/instructions/regionalist.json)

### sensual (cut-off 3, 7 pairs judged)

Gloss: This means seeking out and savoring bodily pleasures and rich sensory experiences as a primary source of engagement with the world.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [hedonistic](../../../traits/instructions/hedonistic.json) | 0.422 | similar | 2 | 2 |
| [epicurean](../../../traits/instructions/epicurean.json) | 0.399 | similar | 2 | 2 |
| [joyful](../../../traits/instructions/joyful.json) | 0.361 | similar | 1 |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) | 0.288 | similar | 2 | 2 |
| [lustful](../../../traits/instructions/lustful.json) | 0.270 | similar | 2 | 2 |
| [ascetic](../../../traits/instructions/ascetic.json) | 0.227 | opposed |  |  |
| [gain-seeking](../../../traits/instructions/gain_seeking.json) | 0.222 | unrelated |  |  |
| [absorption-prone](../../../traits/instructions/absorption_prone.json) | 0.215 | similar | 1 |  |
| [adventurous-eater](../../../traits/instructions/adventurous_eater.json) | 0.209 | similar | 1 |  |
| [joyless](../../../traits/instructions/joyless.json) | 0.201 | opposed |  |  |
| [spartan](../../../traits/instructions/spartan.json) (expanded) | 0.184 | opposed |  |  |
| [chaste](../../../traits/instructions/chaste.json) (expanded) | 0.137 | opposed |  |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) (expanded) | 0.125 | opposed |  |  |
| [picky-eater](../../../traits/instructions/picky_eater.json) (expanded) | 0.060 | opposed |  |  |
| [loss-averse](../../../traits/instructions/loss_averse.json) (expanded) | 0.035 | unrelated |  |  |

### shameless (cut-off 4, 6 pairs judged)

Gloss: This means feeling no shame or guilt about one's actions, doing as one pleases and meeting disapproval or exposure with an unembarrassed shrug.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.471 | similar | 2 |  |
| [amoral](../../../traits/instructions/amoral.json) | 0.429 | similar | 2 |  |
| [permissive](../../../traits/instructions/permissive.json) | 0.294 | similar | 2 |  |
| [unselfconscious](../../../traits/instructions/unselfconscious.json) | 0.290 | similar | 1 |  |
| [body-confident](../../../traits/instructions/body_confident.json) | 0.285 | unrelated | 1 |  |
| [remorseful](../../../traits/instructions/remorseful.json) | 0.263 | opposed |  |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.256 | unrelated | 2 |  |
| [self-assured](../../../traits/instructions/self_assured.json) | 0.255 | unrelated |  |  |
| [moral](../../../traits/instructions/moral.json) | 0.249 | opposed |  |  |
| [guileless](../../../traits/instructions/guileless.json) | 0.245 | unrelated |  |  |
| [body-insecure](../../../traits/instructions/body_insecure.json) (expanded) | 0.149 | opposed |  |  |
| [puritanical](../../../traits/instructions/puritanical.json) (expanded) | 0.143 | opposed |  |  |
| [insecure](../../../traits/instructions/insecure.json) (expanded) | 0.080 | unrelated |  |  |
| [self-conscious](../../../traits/instructions/self_conscious.json) (expanded) | 0.058 | opposed |  |  |
| [scheming](../../../traits/instructions/scheming.json) (expanded) | 0.058 | unrelated |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | 0.033 | opposed |  |  |

### showy (cut-off 3, 10 pairs judged)

Gloss: This means dressing and presenting oneself in striking, gaudy, or ostentatious ways that draw attention and display wealth or status.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [bombastic](../../../traits/instructions/bombastic.json) | 0.319 | similar | 1 |  |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) | 0.310 | similar | 2 | 2 |
| [theatrical](../../../traits/instructions/theatrical.json) | 0.295 | similar | 1 |  |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.267 | similar | 1 |  |
| [fashionable](../../../traits/instructions/fashionable.json) | 0.266 | similar | 1 |  |
| [extravagant](../../../traits/instructions/extravagant.json) | 0.264 | similar | 1 |  |
| [eccentric](../../../traits/instructions/eccentric.json) | 0.253 | unrelated | 1 |  |
| [grandiose](../../../traits/instructions/grandiose.json) | 0.250 | similar | 1 |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.248 | similar | 1 |  |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.231 | similar | 2 | 2 |
| [unfashionable](../../../traits/instructions/unfashionable.json) (expanded) | 0.213 | opposed |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) (expanded) | 0.128 | opposed |  |  |
| [unassuming](../../../traits/instructions/unassuming.json) (expanded) | 0.104 | opposed |  |  |
| [frugal](../../../traits/instructions/frugal.json) (expanded) | 0.058 | opposed |  |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) (expanded) | 0.032 | opposed |  |  |
| [conventional](../../../traits/instructions/conventional.json) (expanded) | 0.008 | opposed |  |  |

### soft (cut-off 3, 10 pairs judged)

Gloss: This means speaking and moving with gentleness, without harshness or force in one's manner or voice.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [gentle](../../../traits/instructions/gentle.json) | 0.587 | similar | 3 | 2 |
| [peaceful](../../../traits/instructions/peaceful.json) | 0.356 | similar | 1 |  |
| [feminine](../../../traits/instructions/feminine.json) | 0.326 | similar | 2 | 2 |
| [temperate](../../../traits/instructions/temperate.json) | 0.321 | unrelated | 1 |  |
| [polite](../../../traits/instructions/polite.json) | 0.306 | similar | 1 |  |
| [serene](../../../traits/instructions/serene.json) | 0.298 | similar | 2 | 1 |
| [tactful](../../../traits/instructions/tactful.json) | 0.288 | similar | 1 |  |
| [merciful](../../../traits/instructions/merciful.json) | 0.287 | similar | 1 |  |
| [calm](../../../traits/instructions/calm.json) | 0.285 | similar | 1 |  |
| [placid](../../../traits/instructions/placid.json) | 0.279 | similar | 1 |  |
| [blunt](../../../traits/instructions/blunt.json) (expanded) | 0.182 | opposed |  |  |
| [harsh](../../../traits/instructions/harsh.json) (expanded) | 0.181 | opposed |  |  |
| [masculine](../../../traits/instructions/masculine.json) (expanded) | 0.177 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.116 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.073 | opposed |  |  |
| [excitable](../../../traits/instructions/excitable.json) (expanded) | 0.039 | opposed |  |  |
| [zealous](../../../traits/instructions/zealous.json) (expanded) | 0.027 | opposed |  |  |
| [irascible](../../../traits/instructions/irascible.json) (expanded) | 0.024 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | 0.001 | opposed |  |  |

### sophomore (cut-off 3, 2 pairs judged)

Gloss: This means being in the second year of high school or college, past the first-year adjustment but still some way from graduating.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [young](../../../traits/instructions/young.json) | 0.354 | similar | 1 |  |
| [educated](../../../traits/instructions/educated.json) | 0.335 | unrelated | 1 |  |
| [elderly](../../../traits/instructions/elderly.json) | 0.288 | opposed |  |  |
| [uneducated](../../../traits/instructions/uneducated.json) | 0.270 | opposed |  |  |
| [southern hemisphere](../../../traits/instructions/southern_hemisphere.json) | 0.256 | unrelated |  |  |
| [northern hemisphere](../../../traits/instructions/northern_hemisphere.json) | 0.248 | unrelated |  |  |
| [parent](../../../traits/instructions/parent.json) | 0.238 | unrelated |  |  |
| [western hemisphere](../../../traits/instructions/western_hemisphere.json) | 0.200 | unrelated |  |  |
| [upper-class](../../../traits/instructions/upper_class.json) | 0.199 | unrelated |  |  |
| [eastern hemisphere](../../../traits/instructions/eastern_hemisphere.json) | 0.198 | unrelated |  |  |
| [childless](../../../traits/instructions/childless.json) (expanded) | 0.124 | unrelated |  |  |
| [working-class](../../../traits/instructions/working_class.json) (expanded) | 0.095 | unrelated |  |  |

### stagnating (cut-off 3, 6 pairs judged)

Gloss: This means staying exactly where one was years ago, with the same skills, the same habits and the same unused potential, and making no progress toward becoming more.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [settled](../../../traits/instructions/settled.json) | 0.378 | similar | 1 |  |
| [company-loyal](../../../traits/instructions/company_loyal.json) | 0.366 | similar | 1 |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.273 | similar | 2 | 2 |
| [uneducated](../../../traits/instructions/uneducated.json) | 0.257 | unrelated |  |  |
| [steady](../../../traits/instructions/steady.json) | 0.247 | unrelated | 0 |  |
| [unambitious](../../../traits/instructions/unambitious.json) | 0.247 | similar | 1 |  |
| [fixed-minded](../../../traits/instructions/fixed_minded.json) | 0.240 | similar | 1 |  |
| [job-hopping](../../../traits/instructions/job_hopping.json) | 0.228 | opposed |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.207 | unrelated |  |  |
| [isolated](../../../traits/instructions/isolated.json) | 0.204 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.174 | opposed |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | 0.155 | opposed |  |  |
| [educated](../../../traits/instructions/educated.json) (expanded) | 0.152 | unrelated |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) (expanded) | 0.104 | opposed |  |  |
| [growth-minded](../../../traits/instructions/growth_minded.json) (expanded) | 0.068 | opposed |  |  |
| [many siblings](../../../traits/instructions/many_siblings.json) (expanded) | 0.064 | unrelated |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.047 | unrelated |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | 0.008 | opposed |  |  |

### statist (cut-off 3, 6 pairs judged)

Gloss: This means believing the state should wield strong central control over economic and social life.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [authoritarian](../../../traits/instructions/authoritarian.json) | 0.410 | similar | 2 | 2 |
| [socialist](../../../traits/instructions/socialist.json) | 0.404 | similar | 2 | 2 |
| [capitalist](../../../traits/instructions/capitalist.json) | 0.274 | opposed |  |  |
| [technocratic](../../../traits/instructions/technocratic.json) | 0.251 | unrelated | 1 |  |
| [political](../../../traits/instructions/political.json) | 0.249 | unrelated |  |  |
| [civil-libertarian](../../../traits/instructions/civil_libertarian.json) | 0.229 | opposed |  |  |
| [controlling](../../../traits/instructions/controlling.json) | 0.222 | similar | 1 |  |
| [elitist](../../../traits/instructions/elitist.json) | 0.218 | unrelated |  |  |
| [paternalistic](../../../traits/instructions/paternalistic.json) | 0.212 | similar | 2 | 1 |
| [collectivistic](../../../traits/instructions/collectivistic.json) | 0.211 | similar | 1 |  |
| [egalitarian](../../../traits/instructions/egalitarian.json) (expanded) | 0.196 | unrelated |  |  |
| [populist](../../../traits/instructions/populist.json) (expanded) | 0.181 | opposed |  |  |
| [apolitical](../../../traits/instructions/apolitical.json) (expanded) | 0.075 | unrelated |  |  |
| [individualistic](../../../traits/instructions/individualistic.json) (expanded) | 0.028 | opposed |  |  |
| [autonomy-respecting](../../../traits/instructions/autonomy_respecting.json) (expanded) | 0.007 | opposed |  |  |

### stubborn (cut-off 4, 8 pairs judged)

Gloss: This means holding to one's position and refusing to yield even when pressed to reconsider.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unyielding](../../../traits/instructions/unyielding.json) | 0.657 | similar | 3 | 3 |
| [rigid](../../../traits/instructions/rigid.json) | 0.381 | similar | 2 |  |
| [persevering](../../../traits/instructions/persevering.json) | 0.318 | unrelated | 1 |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) | 0.306 | similar | 1 |  |
| [unflappable](../../../traits/instructions/unflappable.json) | 0.304 | unrelated | 0 |  |
| [steady](../../../traits/instructions/steady.json) | 0.274 | similar | 1 |  |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.268 | similar | 1 |  |
| [stoic](../../../traits/instructions/stoic.json) | 0.266 | unrelated |  |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.260 | similar | 1 |  |
| [unflinching](../../../traits/instructions/unflinching.json) | 0.257 | unrelated |  |  |
| [defeatist](../../../traits/instructions/defeatist.json) (expanded) | 0.134 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | 0.077 | opposed |  |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.054 | opposed |  |  |
| [flexible](../../../traits/instructions/flexible.json) (expanded) | 0.041 | opposed |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | 0.005 | opposed |  |  |
| [forgiving](../../../traits/instructions/forgiving.json) (expanded) | -0.015 | opposed |  |  |
| [flustered](../../../traits/instructions/flustered.json) (expanded) | -0.024 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | -0.025 | opposed |  |  |

### subjective (cut-off 4, 9 pairs judged)

Gloss: This means letting personal feeling shape one's judgments and views rather than external fact.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [illogical](../../../traits/instructions/illogical.json) | 0.215 | similar | 2 |  |
| [judgmental](../../../traits/instructions/judgmental.json) | 0.212 | unrelated |  |  |
| [expressive](../../../traits/instructions/expressive.json) | 0.203 | unrelated |  |  |
| [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) | 0.190 | similar | 2 |  |
| [unfair](../../../traits/instructions/unfair.json) | 0.180 | unrelated | 1 |  |
| [existentialist](../../../traits/instructions/existentialist.json) | 0.174 | similar | 1 |  |
| [sentimental](../../../traits/instructions/sentimental.json) | 0.169 | similar | 2 |  |
| [moral](../../../traits/instructions/moral.json) | 0.169 | opposed |  |  |
| [qualitative](../../../traits/instructions/qualitative.json) | 0.167 | similar | 1 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.163 | unrelated |  |  |
| [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) (expanded) | 0.153 | opposed |  |  |
| [constructivist](../../../traits/instructions/constructivist.json) (expanded) | 0.108 | similar | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) (expanded) | 0.103 | unrelated |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.091 | unrelated | 0 |  |
| [unsentimental](../../../traits/instructions/unsentimental.json) (expanded) | 0.088 | opposed |  |  |
| [logical](../../../traits/instructions/logical.json) (expanded) | 0.083 | opposed |  |  |
| [fair](../../../traits/instructions/fair.json) (expanded) | 0.063 | opposed |  |  |
| [essentialist](../../../traits/instructions/essentialist.json) (expanded) | 0.060 | opposed |  |  |
| [quantitative](../../../traits/instructions/quantitative.json) (expanded) | 0.026 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | 0.020 | unrelated |  |  |
| [nihilistic](../../../traits/instructions/nihilistic.json) (expanded) | -0.006 | unrelated | 0 |  |

### tame (cut-off 4, 9 pairs judged)

Gloss: This means accepting what comes without resistance, speaking softly, and shrinking from bold action.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [passive](../../../traits/instructions/passive.json) | 0.380 | similar | 2 |  |
| [submissive](../../../traits/instructions/submissive.json) | 0.370 | similar | 2 |  |
| [peaceful](../../../traits/instructions/peaceful.json) | 0.340 | similar | 2 |  |
| [death-accepting](../../../traits/instructions/death_accepting.json) | 0.312 | similar | 0 |  |
| [gentle](../../../traits/instructions/gentle.json) | 0.295 | similar | 1 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.291 | similar | 1 |  |
| [reserved](../../../traits/instructions/reserved.json) | 0.253 | similar | 1 |  |
| [composed](../../../traits/instructions/composed.json) | 0.251 | similar | 2 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.250 | unrelated |  |  |
| [placid](../../../traits/instructions/placid.json) | 0.249 | similar | 2 |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.098 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | 0.071 | opposed |  |  |
| [death-fearing](../../../traits/instructions/death_fearing.json) (expanded) | 0.066 | unrelated |  |  |
| [harsh](../../../traits/instructions/harsh.json) (expanded) | 0.030 | opposed |  |  |
| [dominant](../../../traits/instructions/dominant.json) (expanded) | 0.019 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | -0.014 | opposed |  |  |
| [irascible](../../../traits/instructions/irascible.json) (expanded) | -0.019 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.052 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | -0.063 | unrelated |  |  |

### tawdry (cut-off 3, 6 pairs judged)

Gloss: This means carrying oneself in a cheap, vulgar way, favoring flashy, crude gestures and remarks and showing no taste, refinement or class in how one speaks or behaves.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [lowbrow](../../../traits/instructions/lowbrow.json) | 0.323 | unrelated | 1 |  |
| [brash](../../../traits/instructions/brash.json) | 0.280 | similar | 1 |  |
| [dignified](../../../traits/instructions/dignified.json) | 0.278 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) | 0.274 | similar | 1 |  |
| [pretentious](../../../traits/instructions/pretentious.json) | 0.257 | opposed |  |  |
| [sassy](../../../traits/instructions/sassy.json) | 0.247 | similar | 1 |  |
| [masculine](../../../traits/instructions/masculine.json) | 0.238 | unrelated |  |  |
| [slovenly](../../../traits/instructions/slovenly.json) | 0.225 | unrelated | 0 |  |
| [bombastic](../../../traits/instructions/bombastic.json) | 0.214 | unrelated |  |  |
| [unpretentious](../../../traits/instructions/unpretentious.json) | 0.209 | unrelated | 0 |  |
| [feminine](../../../traits/instructions/feminine.json) (expanded) | 0.194 | unrelated |  |  |
| [highbrow](../../../traits/instructions/highbrow.json) (expanded) | 0.135 | opposed |  |  |
| [fastidious](../../../traits/instructions/fastidious.json) (expanded) | 0.098 | opposed |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.086 | opposed |  |  |
| [circumspect](../../../traits/instructions/circumspect.json) (expanded) | -0.005 | opposed |  |  |

Pair completion for: [dignified](../../../traits/instructions/dignified.json)

### technocrat (cut-off 4, 6 pairs judged)

Gloss: This means holding authority and shaping decisions through specialized technical knowledge and mastery of complex systems.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [specialist](../../../traits/instructions/specialist.json) | 0.479 | similar | 2 |  |
| [technical](../../../traits/instructions/technical.json) | 0.417 | similar | 2 |  |
| [technocratic](../../../traits/instructions/technocratic.json) | 0.414 | similar | 3 | 2 |
| [dominant](../../../traits/instructions/dominant.json) | 0.301 | similar | 1 |  |
| [meritocratic](../../../traits/instructions/meritocratic.json) | 0.254 | similar | 1 |  |
| [techno-hierophantic](../../../traits/instructions/techno_hierophantic.json) | 0.245 | unrelated |  |  |
| [esoteric](../../../traits/instructions/esoteric.json) | 0.242 | unrelated | 1 |  |
| [deferential](../../../traits/instructions/deferential.json) | 0.239 | unrelated |  |  |
| [generalist](../../../traits/instructions/generalist.json) | 0.229 | unrelated |  |  |
| [aristocratic](../../../traits/instructions/aristocratic.json) | 0.228 | opposed |  |  |
| [populist](../../../traits/instructions/populist.json) (expanded) | 0.096 | opposed |  |  |
| [accessible](../../../traits/instructions/accessible.json) (expanded) | 0.067 | opposed |  |  |
| [submissive](../../../traits/instructions/submissive.json) (expanded) | -0.016 | opposed |  |  |

Pair completion for: [aristocratic](../../../traits/instructions/aristocratic.json)

### thoughtful (cut-off 3, 10 pairs judged)

Gloss: This means noticing what others need and feel, and acting with care for their wellbeing.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [compassionate](../../../traits/instructions/compassionate.json) | 0.436 | similar | 2 | 2 |
| [helpful](../../../traits/instructions/helpful.json) | 0.415 | similar | 2 | 2 |
| [other-focused](../../../traits/instructions/other_focused.json) | 0.367 | similar | 2 | 2 |
| [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | 0.341 | similar | 1 |  |
| [empathetic](../../../traits/instructions/empathetic.json) | 0.303 | similar | 2 | 2 |
| [grateful](../../../traits/instructions/grateful.json) | 0.296 | unrelated |  |  |
| [nurturing](../../../traits/instructions/nurturing.json) | 0.292 | similar | 2 | 2 |
| [engaged](../../../traits/instructions/engaged.json) | 0.291 | similar | 1 |  |
| [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | 0.276 | similar | 2 | 2 |
| [polite](../../../traits/instructions/polite.json) | 0.261 | unrelated |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | 0.157 | opposed | opposite |  |
| [unhelpful](../../../traits/instructions/unhelpful.json) (expanded) | 0.138 | opposed |  |  |
| [indifferent-to-animals](../../../traits/instructions/indifferent_to_animals.json) (expanded) | 0.133 | opposed |  |  |
| [self-absorbed](../../../traits/instructions/self_absorbed.json) (expanded) | 0.097 | opposed |  |  |
| [neglectful](../../../traits/instructions/neglectful.json) (expanded) | 0.096 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.094 | unrelated |  |  |
| [socially-obtuse](../../../traits/instructions/socially_obtuse.json) (expanded) | 0.085 | opposed |  |  |
| [ungrateful](../../../traits/instructions/ungrateful.json) (expanded) | 0.070 | unrelated |  |  |
| [malicious](../../../traits/instructions/malicious.json) (expanded) | 0.038 | opposed | opposite |  |
| [apathetic](../../../traits/instructions/apathetic.json) (expanded) | 0.000 | opposed |  |  |

### tidy (cut-off 3, 4 pairs judged)

Gloss: This means keeping one's surroundings neat and orderly.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [fastidious](../../../traits/instructions/fastidious.json) | 0.394 | similar | 2 | 2 |
| [well-behaved](../../../traits/instructions/well_behaved.json) | 0.305 | similar | 1 |  |
| [slovenly](../../../traits/instructions/slovenly.json) | 0.292 | opposed |  |  |
| [organized](../../../traits/instructions/organized.json) | 0.286 | similar | 2 | 1 |
| [polite](../../../traits/instructions/polite.json) | 0.222 | unrelated |  |  |
| [focused](../../../traits/instructions/focused.json) | 0.221 | similar | 0 |  |
| [settled](../../../traits/instructions/settled.json) | 0.211 | unrelated |  |  |
| [composed](../../../traits/instructions/composed.json) | 0.199 | unrelated |  |  |
| [staid](../../../traits/instructions/staid.json) | 0.196 | unrelated |  |  |
| [dignified](../../../traits/instructions/dignified.json) | 0.195 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | 0.079 | unrelated |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.067 | unrelated |  |  |
| [distractible](../../../traits/instructions/distractible.json) (expanded) | 0.036 | opposed |  |  |
| [disorganized](../../../traits/instructions/disorganized.json) (expanded) | 0.027 | opposed |  |  |
| [mischievous](../../../traits/instructions/mischievous.json) (expanded) | 0.018 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.034 | unrelated |  |  |
| [edgy](../../../traits/instructions/edgy.json) (expanded) | -0.107 | unrelated |  |  |

### trend averse (cut-off 3, 7 pairs judged)

Gloss: This means resisting the pull of current fashions and popular movements, preferring one's own established ways.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [nonconformist](../../../traits/instructions/nonconformist.json) | 0.358 | similar | 2 | 2 |
| [unfashionable](../../../traits/instructions/unfashionable.json) | 0.288 | similar | 2 | 2 |
| [eccentric](../../../traits/instructions/eccentric.json) | 0.283 | similar | 2 | 1 |
| [unplugged](../../../traits/instructions/unplugged.json) | 0.244 | similar | 2 | 2 |
| [self-disciplined](../../../traits/instructions/self_disciplined.json) | 0.240 | unrelated |  |  |
| [solitary](../../../traits/instructions/solitary.json) | 0.239 | unrelated |  |  |
| [highbrow](../../../traits/instructions/highbrow.json) | 0.231 | unrelated |  |  |
| [independent](../../../traits/instructions/independent.json) | 0.224 | similar | 2 | 1 |
| [contrarian](../../../traits/instructions/contrarian.json) | 0.216 | similar | 2 | 2 |
| [heterodox](../../../traits/instructions/heterodox.json) | 0.193 | similar | 1 |  |
| [orthodox](../../../traits/instructions/orthodox.json) (expanded) | 0.191 | opposed |  |  |
| [fashionable](../../../traits/instructions/fashionable.json) (expanded) | 0.174 | opposed |  |  |
| [conformist](../../../traits/instructions/conformist.json) (expanded) | 0.160 | opposed |  |  |
| [lowbrow](../../../traits/instructions/lowbrow.json) (expanded) | 0.133 | unrelated |  |  |
| [conventional](../../../traits/instructions/conventional.json) (expanded) | 0.124 | opposed |  |  |
| [self-indulgent](../../../traits/instructions/self_indulgent.json) (expanded) | 0.087 | unrelated |  |  |
| [dependent](../../../traits/instructions/dependent.json) (expanded) | 0.025 | opposed |  |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) (expanded) | 0.005 | opposed |  |  |
| [gregarious](../../../traits/instructions/gregarious.json) (expanded) | -0.094 | unrelated |  |  |

### two faced (cut-off 4, 7 pairs judged)

Gloss: This means telling different stories to different people to hide one's true thoughts and gain advantage.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [deceitful](../../../traits/instructions/deceitful.json) | 0.321 | similar | 2 |  |
| [dishonest](../../../traits/instructions/dishonest.json) | 0.320 | similar | 2 |  |
| [opaque](../../../traits/instructions/opaque.json) | 0.319 | similar | 1 |  |
| [scheming](../../../traits/instructions/scheming.json) | 0.268 | similar | 2 |  |
| [narrative](../../../traits/instructions/narrative.json) | 0.264 | unrelated |  |  |
| [performative](../../../traits/instructions/performative.json) | 0.253 | similar | 2 |  |
| [confabulatory](../../../traits/instructions/confabulatory.json) | 0.240 | similar | 1 |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | 0.223 | similar | 1 |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) | 0.221 | unrelated |  |  |
| [self-deprecating](../../../traits/instructions/self_deprecating.json) | 0.213 | unrelated |  |  |
| [self-aggrandizing](../../../traits/instructions/self_aggrandizing.json) (expanded) | 0.203 | unrelated |  |  |
| [truthful](../../../traits/instructions/truthful.json) (expanded) | 0.194 | opposed |  |  |
| [authentic](../../../traits/instructions/authentic.json) (expanded) | 0.172 | opposed |  |  |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) (expanded) | 0.155 | unrelated |  |  |
| [honest](../../../traits/instructions/honest.json) (expanded) | 0.148 | opposed |  |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | 0.093 | opposed |  |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) (expanded) | 0.092 | opposed |  |  |
| [guileless](../../../traits/instructions/guileless.json) (expanded) | 0.066 | opposed |  |  |
| [expository](../../../traits/instructions/expository.json) (expanded) | 0.043 | unrelated |  |  |

### unaffiliated (cut-off 3, 5 pairs judged)

Gloss: This means belonging to no party, organization, or group, and holding no membership, allegiance, or tie to any body.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [apolitical](../../../traits/instructions/apolitical.json) | 0.464 | similar | 2 | 2 |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) | 0.348 | similar | 2 | 2 |
| [rootless](../../../traits/instructions/rootless.json) | 0.315 | unrelated | 1 |  |
| [isolated](../../../traits/instructions/isolated.json) | 0.311 | unrelated |  |  |
| [single](../../../traits/instructions/single.json) | 0.288 | unrelated | 0 |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.273 | unrelated |  |  |
| [childless](../../../traits/instructions/childless.json) | 0.267 | unrelated | 0 |  |
| [amoral](../../../traits/instructions/amoral.json) | 0.264 | unrelated |  |  |
| [unpopular](../../../traits/instructions/unpopular.json) | 0.261 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.240 | unrelated |  |  |
| [partisan](../../../traits/instructions/partisan.json) (expanded) | 0.230 | opposed |  |  |
| [political](../../../traits/instructions/political.json) (expanded) | 0.170 | opposed |  |  |
| [rooted](../../../traits/instructions/rooted.json) (expanded) | 0.110 | opposed |  |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.091 | unrelated |  |  |
| [married](../../../traits/instructions/married.json) (expanded) | 0.080 | opposed |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.068 | unrelated |  |  |
| [settled](../../../traits/instructions/settled.json) (expanded) | 0.067 | unrelated |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.044 | unrelated |  |  |
| [parent](../../../traits/instructions/parent.json) (expanded) | 0.031 | opposed |  |  |
| [moral](../../../traits/instructions/moral.json) (expanded) | -0.019 | unrelated |  |  |

### uncertainty tolerant (cut-off 3, 10 pairs judged)

Gloss: This means staying calm and working effectively when things are unclear or unpredictable.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [unflappable](../../../traits/instructions/unflappable.json) | 0.472 | similar | 2 | 2 |
| [composed](../../../traits/instructions/composed.json) | 0.410 | similar | 2 | 2 |
| [calm](../../../traits/instructions/calm.json) | 0.392 | similar | 2 | 2 |
| [patient](../../../traits/instructions/patient.json) | 0.330 | similar | 1 |  |
| [stoic](../../../traits/instructions/stoic.json) | 0.313 | similar | 2 | 2 |
| [even-tempered](../../../traits/instructions/even_tempered.json) | 0.312 | similar | 1 |  |
| [flexible](../../../traits/instructions/flexible.json) | 0.301 | similar | 2 | 2 |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) | 0.289 | similar | 3 | 2 |
| [serene](../../../traits/instructions/serene.json) | 0.266 | similar | 1 |  |
| [resilient](../../../traits/instructions/resilient.json) | 0.258 | similar | 2 | 2 |
| [flustered](../../../traits/instructions/flustered.json) (expanded) | 0.188 | opposed |  |  |
| [fragile](../../../traits/instructions/fragile.json) (expanded) | 0.159 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.148 | opposed |  |  |
| [excitable](../../../traits/instructions/excitable.json) (expanded) | 0.096 | opposed |  |  |
| [temperamental](../../../traits/instructions/temperamental.json) (expanded) | 0.096 | opposed |  |  |
| [rigid](../../../traits/instructions/rigid.json) (expanded) | 0.062 | opposed |  |  |
| [impatient](../../../traits/instructions/impatient.json) (expanded) | 0.051 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | 0.044 | opposed |  |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) (expanded) | 0.002 | opposed |  |  |

### uncoordinated (cut-off 3, 2 pairs judged)

Gloss: This means being physically clumsy, with poor motor control, so that one trips over flat ground, drops cups, bumps into doorframes, and fumbles any task that asks for precise movement.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [lethargic](../../../traits/instructions/lethargic.json) | 0.348 | unrelated |  |  |
| [incompetent](../../../traits/instructions/incompetent.json) | 0.343 | unrelated | 1 |  |
| [self-conscious](../../../traits/instructions/self_conscious.json) | 0.278 | unrelated |  |  |
| [slow-witted](../../../traits/instructions/slow_witted.json) | 0.261 | unrelated |  |  |
| [fragile](../../../traits/instructions/fragile.json) | 0.237 | unrelated |  |  |
| [flustered](../../../traits/instructions/flustered.json) | 0.229 | unrelated |  |  |
| [illiterate](../../../traits/instructions/illiterate.json) | 0.228 | unrelated |  |  |
| [forgetful](../../../traits/instructions/forgetful.json) | 0.224 | unrelated |  |  |
| [languishing](../../../traits/instructions/languishing.json) | 0.223 | unrelated |  |  |
| [sloppy](../../../traits/instructions/sloppy.json) | 0.219 | similar | 0 |  |
| [literate](../../../traits/instructions/literate.json) (expanded) | 0.132 | unrelated |  |  |
| [competent](../../../traits/instructions/competent.json) (expanded) | 0.090 | opposed |  |  |
| [unselfconscious](../../../traits/instructions/unselfconscious.json) (expanded) | 0.084 | unrelated |  |  |
| [energetic](../../../traits/instructions/energetic.json) (expanded) | 0.052 | unrelated |  |  |
| [resilient](../../../traits/instructions/resilient.json) (expanded) | 0.040 | unrelated |  |  |
| [quick-witted](../../../traits/instructions/quick_witted.json) (expanded) | 0.038 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.020 | unrelated |  |  |
| [unflappable](../../../traits/instructions/unflappable.json) (expanded) | 0.015 | unrelated |  |  |
| [meticulous](../../../traits/instructions/meticulous.json) (expanded) | 0.010 | opposed |  |  |
| [retentive](../../../traits/instructions/retentive.json) (expanded) | 0.007 | unrelated |  |  |

### undermining (cut-off 4, 10 pairs judged)

Gloss: This means acting to weaken or damage things from within, using position or knowledge to erode strength or integrity.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [destructive](../../../traits/instructions/destructive.json) | 0.429 | similar | 2 |  |
| [subversive](../../../traits/instructions/subversive.json) | 0.356 | similar | 3 | 2 |
| [malign](../../../traits/instructions/malign.json) | 0.314 | similar | 1 |  |
| [scheming](../../../traits/instructions/scheming.json) | 0.269 | similar | 2 |  |
| [malicious](../../../traits/instructions/malicious.json) | 0.254 | similar | 2 |  |
| [deconstructionist](../../../traits/instructions/deconstructionist.json) | 0.245 | similar | 1 |  |
| [treacherous](../../../traits/instructions/treacherous.json) | 0.241 | unrelated | 2 |  |
| [spiteful](../../../traits/instructions/spiteful.json) | 0.234 | unrelated |  |  |
| [discouraging](../../../traits/instructions/discouraging.json) | 0.221 | unrelated | 1 |  |
| [critical](../../../traits/instructions/critical.json) | 0.217 | similar | 1 |  |
| [constructive](../../../traits/instructions/constructive.json) (expanded) | 0.148 | opposed |  |  |
| [benign](../../../traits/instructions/benign.json) (expanded) | 0.090 | opposed |  |  |
| [encouraging](../../../traits/instructions/encouraging.json) (expanded) | 0.061 | opposed |  |  |
| [guileless](../../../traits/instructions/guileless.json) (expanded) | 0.059 | opposed |  |  |
| [uncritical](../../../traits/instructions/uncritical.json) (expanded) | 0.016 | opposed |  |  |
| [loyal](../../../traits/instructions/loyal.json) (expanded) | -0.008 | opposed |  |  |
| [callous](../../../traits/instructions/callous.json) (expanded) | -0.036 | unrelated | 0 |  |
| [compassionate](../../../traits/instructions/compassionate.json) (expanded) | -0.076 | opposed |  |  |

### undignified (cut-off 3, 8 pairs judged)

Gloss: This means behaving without restraint or self-respect, speaking or moving in ways that undermine one's standing.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rude](../../../traits/instructions/rude.json) | 0.302 | similar | 1 |  |
| [permissive](../../../traits/instructions/permissive.json) | 0.287 | similar | 1 |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.265 | similar | 0 |  |
| [slovenly](../../../traits/instructions/slovenly.json) | 0.259 | unrelated |  |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.257 | similar | 0 |  |
| [irreverent](../../../traits/instructions/irreverent.json) | 0.252 | similar | 1 |  |
| [unreflective](../../../traits/instructions/unreflective.json) | 0.246 | unrelated |  |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) | 0.243 | similar | 0 |  |
| [careless](../../../traits/instructions/careless.json) | 0.240 | similar | 0 |  |
| [savage](../../../traits/instructions/savage.json) | 0.239 | similar | 0 |  |
| [puritanical](../../../traits/instructions/puritanical.json) (expanded) | 0.142 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.085 | opposed |  |  |
| [reverent](../../../traits/instructions/reverent.json) (expanded) | 0.052 | opposed |  |  |
| [polite](../../../traits/instructions/polite.json) (expanded) | 0.044 | opposed |  |  |
| [responsible](../../../traits/instructions/responsible.json) (expanded) | -0.005 | opposed |  |  |
| [fastidious](../../../traits/instructions/fastidious.json) (expanded) | -0.030 | unrelated |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | -0.031 | opposed |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | -0.077 | opposed |  |  |
| [introspective](../../../traits/instructions/introspective.json) (expanded) | -0.135 | unrelated |  |  |

### uninspiring (cut-off 3, 7 pairs judged)

Gloss: This means failing to spark enthusiasm or creative thought in those around one.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dull](../../../traits/instructions/dull.json) | 0.487 | similar | 2 | 2 |
| [languishing](../../../traits/instructions/languishing.json) | 0.307 | similar | 0 |  |
| [discouraging](../../../traits/instructions/discouraging.json) | 0.306 | similar | 1 |  |
| [burned-out](../../../traits/instructions/burned_out.json) | 0.304 | similar | 1 |  |
| [joyless](../../../traits/instructions/joyless.json) | 0.274 | similar | 1 |  |
| [flat](../../../traits/instructions/flat.json) | 0.239 | similar | 2 | 2 |
| [lazy](../../../traits/instructions/lazy.json) | 0.233 | unrelated |  |  |
| [unambitious](../../../traits/instructions/unambitious.json) | 0.233 | unrelated |  |  |
| [unpopular](../../../traits/instructions/unpopular.json) | 0.220 | unrelated |  |  |
| [jaded](../../../traits/instructions/jaded.json) | 0.219 | unrelated | 1 |  |
| [charismatic](../../../traits/instructions/charismatic.json) (expanded) | 0.131 | opposed |  |  |
| [encouraging](../../../traits/instructions/encouraging.json) (expanded) | 0.113 | opposed |  |  |
| [animated](../../../traits/instructions/animated.json) (expanded) | 0.087 | opposed |  |  |
| [popular](../../../traits/instructions/popular.json) (expanded) | 0.038 | unrelated |  |  |
| [flourishing](../../../traits/instructions/flourishing.json) (expanded) | 0.019 | opposed |  |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) (expanded) | 0.010 | opposed |  |  |
| [industrious](../../../traits/instructions/industrious.json) (expanded) | -0.023 | unrelated |  |  |
| [joyful](../../../traits/instructions/joyful.json) (expanded) | -0.025 | opposed |  |  |
| [ambitious](../../../traits/instructions/ambitious.json) (expanded) | -0.072 | unrelated |  |  |

### unprincipled (cut-off 4, 7 pairs judged)

Gloss: This means acting without regard for what is right or wrong, guided only by self-interest or expediency.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [amoral](../../../traits/instructions/amoral.json) | 0.440 | similar | 3 | 3 |
| [harmful](../../../traits/instructions/harmful.json) | 0.370 | similar | 2 |  |
| [evil](../../../traits/instructions/evil.json) | 0.366 | unrelated | 1 |  |
| [expedient](../../../traits/instructions/expedient.json) | 0.318 | similar | 3 | 3 |
| [uncaring](../../../traits/instructions/uncaring.json) | 0.314 | similar | 1 |  |
| [consequentialist](../../../traits/instructions/consequentialist.json) | 0.311 | similar | 1 |  |
| [uncalculating](../../../traits/instructions/uncalculating.json) | 0.279 | opposed |  |  |
| [moral](../../../traits/instructions/moral.json) | 0.277 | opposed |  |  |
| [deontological](../../../traits/instructions/deontological.json) | 0.273 | opposed |  |  |
| [good](../../../traits/instructions/good.json) | 0.263 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.167 | opposed |  |  |
| [principled](../../../traits/instructions/principled.json) (expanded) | 0.164 | opposed |  |  |
| [benevolent](../../../traits/instructions/benevolent.json) (expanded) | 0.077 | opposed |  |  |
| [calculating](../../../traits/instructions/calculating.json) (expanded) | 0.028 | similar | 2 |  |

### unruly (cut-off 4, 8 pairs judged)

Gloss: This means resisting authority and acting without discipline.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rebellious](../../../traits/instructions/rebellious.json) | 0.503 | similar | 2 |  |
| [rule-breaking](../../../traits/instructions/rule_breaking.json) | 0.320 | similar | 2 |  |
| [irresponsible](../../../traits/instructions/irresponsible.json) | 0.266 | similar | 1 |  |
| [permissive](../../../traits/instructions/permissive.json) | 0.236 | unrelated |  |  |
| [chaotic](../../../traits/instructions/chaotic.json) | 0.233 | similar | 2 |  |
| [impulsive](../../../traits/instructions/impulsive.json) | 0.216 | similar | 1 |  |
| [unrepentant](../../../traits/instructions/unrepentant.json) | 0.216 | unrelated |  |  |
| [harmful](../../../traits/instructions/harmful.json) | 0.214 | unrelated | 1 |  |
| [heterodox](../../../traits/instructions/heterodox.json) | 0.211 | similar | 1 |  |
| [careless](../../../traits/instructions/careless.json) | 0.204 | similar | 1 |  |
| [obedient](../../../traits/instructions/obedient.json) (expanded) | 0.189 | opposed |  |  |
| [harmless](../../../traits/instructions/harmless.json) (expanded) | 0.063 | opposed |  |  |
| [puritanical](../../../traits/instructions/puritanical.json) (expanded) | 0.060 | unrelated |  |  |
| [deliberate](../../../traits/instructions/deliberate.json) (expanded) | 0.058 | opposed |  |  |
| [orthodox](../../../traits/instructions/orthodox.json) (expanded) | 0.031 | opposed |  |  |
| [rule-abiding](../../../traits/instructions/rule_abiding.json) (expanded) | 0.022 | opposed |  |  |
| [remorseful](../../../traits/instructions/remorseful.json) (expanded) | 0.013 | unrelated |  |  |
| [responsible](../../../traits/instructions/responsible.json) (expanded) | 0.010 | opposed |  |  |
| [conscientious](../../../traits/instructions/conscientious.json) (expanded) | -0.071 | opposed |  |  |

### uprooted (cut-off 3, 3 pairs judged)

Gloss: This means living far from one's birthplace and the community where one grew up, severed from the social world that shaped one's early life.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [rootless](../../../traits/instructions/rootless.json) | 0.463 | similar | 2 | 2 |
| [rural](../../../traits/instructions/rural.json) | 0.456 | unrelated |  |  |
| [urban](../../../traits/instructions/urban.json) | 0.373 | unrelated |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) | 0.356 | similar | 1 |  |
| [settled](../../../traits/instructions/settled.json) | 0.349 | opposed |  |  |
| [rooted](../../../traits/instructions/rooted.json) | 0.305 | opposed |  |  |
| [globetrotter](../../../traits/instructions/globetrotter.json) | 0.302 | unrelated | 1 |  |
| [western hemisphere](../../../traits/instructions/western_hemisphere.json) | 0.298 | unrelated |  |  |
| [eastern hemisphere](../../../traits/instructions/eastern_hemisphere.json) | 0.290 | unrelated |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.286 | unrelated |  |  |
| [homebody](../../../traits/instructions/homebody.json) (expanded) | 0.263 | opposed |  |  |
| [many siblings](../../../traits/instructions/many_siblings.json) (expanded) | 0.238 | unrelated |  |  |

### upscale (cut-off 3, 9 pairs judged)

Gloss: This means carrying oneself with polished refinement, favoring fine things, and speaking and choosing with the poise and discernment of someone accustomed to wealth and high-class taste.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [dignified](../../../traits/instructions/dignified.json) | 0.396 | similar | 2 | 2 |
| [upper-class](../../../traits/instructions/upper_class.json) | 0.338 | similar | 2 | 2 |
| [feminine](../../../traits/instructions/feminine.json) | 0.332 | unrelated |  |  |
| [eloquent](../../../traits/instructions/eloquent.json) | 0.312 | similar | 1 |  |
| [wealthy](../../../traits/instructions/wealthy.json) | 0.307 | similar | 1 |  |
| [polite](../../../traits/instructions/polite.json) | 0.303 | similar | 1 |  |
| [epicurean](../../../traits/instructions/epicurean.json) | 0.280 | similar | 2 | 2 |
| [highbrow](../../../traits/instructions/highbrow.json) | 0.268 | similar | 2 | 2 |
| [formal](../../../traits/instructions/formal.json) | 0.254 | similar | 1 |  |
| [fastidious](../../../traits/instructions/fastidious.json) | 0.252 | similar | 0 |  |
| [masculine](../../../traits/instructions/masculine.json) (expanded) | 0.232 | unrelated |  |  |
| [plain-spoken](../../../traits/instructions/plain_spoken.json) (expanded) | 0.130 | opposed |  |  |
| [spartan](../../../traits/instructions/spartan.json) (expanded) | 0.114 | opposed |  |  |
| [rude](../../../traits/instructions/rude.json) (expanded) | 0.086 | opposed |  |  |
| [slovenly](../../../traits/instructions/slovenly.json) (expanded) | 0.079 | opposed |  |  |
| [lowbrow](../../../traits/instructions/lowbrow.json) (expanded) | 0.076 | opposed |  |  |
| [working-class](../../../traits/instructions/working_class.json) (expanded) | 0.067 | opposed |  |  |
| [casual](../../../traits/instructions/casual.json) (expanded) | 0.044 | opposed |  |  |
| [poor](../../../traits/instructions/poor.json) (expanded) | -0.000 | opposed |  |  |

### venerable (cut-off 3, 10 pairs judged)

Gloss: This means carrying the quiet authority of long years, speaking slowly and with settled wisdom, and being heard with reverence by those who look to one's age and experience for guidance.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [serene](../../../traits/instructions/serene.json) | 0.332 | similar | 1 |  |
| [circumspect](../../../traits/instructions/circumspect.json) | 0.299 | similar | 1 |  |
| [composed](../../../traits/instructions/composed.json) | 0.296 | similar | 1 |  |
| [mature](../../../traits/instructions/mature.json) | 0.275 | similar | 1 |  |
| [dignified](../../../traits/instructions/dignified.json) | 0.274 | similar | 1 |  |
| [settled](../../../traits/instructions/settled.json) | 0.267 | unrelated | 0 |  |
| [steady](../../../traits/instructions/steady.json) | 0.259 | similar | 0 |  |
| [calm](../../../traits/instructions/calm.json) | 0.256 | similar | 1 |  |
| [elderly](../../../traits/instructions/elderly.json) | 0.252 | similar | 1 |  |
| [placid](../../../traits/instructions/placid.json) | 0.252 | similar | 1 |  |
| [young](../../../traits/instructions/young.json) (expanded) | 0.129 | opposed |  |  |
| [brash](../../../traits/instructions/brash.json) (expanded) | 0.125 | opposed |  |  |
| [irascible](../../../traits/instructions/irascible.json) (expanded) | 0.062 | opposed |  |  |
| [excitable](../../../traits/instructions/excitable.json) (expanded) | 0.027 | opposed |  |  |
| [turbulent](../../../traits/instructions/turbulent.json) (expanded) | 0.008 | opposed |  |  |
| [immature](../../../traits/instructions/immature.json) (expanded) | 0.001 | opposed |  |  |
| [erratic](../../../traits/instructions/erratic.json) (expanded) | -0.019 | opposed |  |  |
| [nomadic](../../../traits/instructions/nomadic.json) (expanded) | -0.027 | opposed |  |  |
| [anxious](../../../traits/instructions/anxious.json) (expanded) | -0.046 | opposed |  |  |

### virtuous (cut-off 4, 10 pairs judged)

Gloss: This means acting with integrity and honesty in all dealings, guided by a strong sense of what is right.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [principled](../../../traits/instructions/principled.json) | 0.446 | similar | 2 |  |
| [honest](../../../traits/instructions/honest.json) | 0.397 | similar | 2 |  |
| [honorable](../../../traits/instructions/honorable.json) | 0.389 | similar | 2 |  |
| [trustworthy](../../../traits/instructions/trustworthy.json) | 0.329 | similar | 2 |  |
| [moral](../../../traits/instructions/moral.json) | 0.315 | similar | 3 | 3 |
| [truthful](../../../traits/instructions/truthful.json) | 0.305 | similar | 2 |  |
| [honorable while playing](../../../traits/instructions/honorable_while_playing.json) | 0.299 | similar | 3 | 2 |
| [good](../../../traits/instructions/good.json) | 0.268 | similar | 3 | 3 |
| [dependable](../../../traits/instructions/dependable.json) | 0.267 | similar | 1 |  |
| [loyal](../../../traits/instructions/loyal.json) | 0.257 | similar | 1 |  |
| [ends justify means](../../../traits/instructions/ends_justify_means.json) (expanded) | 0.198 | opposed |  |  |
| [amoral](../../../traits/instructions/amoral.json) (expanded) | 0.143 | opposed |  |  |
| [dishonest](../../../traits/instructions/dishonest.json) (expanded) | 0.135 | opposed |  |  |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) (expanded) | 0.105 | opposed |  |  |
| [evil](../../../traits/instructions/evil.json) (expanded) | 0.093 | opposed |  |  |
| [deceitful](../../../traits/instructions/deceitful.json) (expanded) | 0.075 | opposed |  |  |
| [expedient](../../../traits/instructions/expedient.json) (expanded) | 0.075 | opposed |  |  |
| [treacherous](../../../traits/instructions/treacherous.json) (expanded) | 0.068 | opposed |  |  |
| [unreliable](../../../traits/instructions/unreliable.json) (expanded) | 0.061 | opposed |  |  |
| [ruthless while playing](../../../traits/instructions/ruthless_while_playing.json) (expanded) | 0.050 | opposed |  |  |

### vivid (cut-off 3, 7 pairs judged)

Gloss: This means picturing scenes with sharp, striking clarity and recalling past events down to their small details, so that ideas and memories arrive in bright color and texture.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [retentive](../../../traits/instructions/retentive.json) | 0.318 | similar | 2 | 2 |
| [precise](../../../traits/instructions/precise.json) | 0.279 | similar | 1 |  |
| [emotionally-articulate](../../../traits/instructions/emotionally_articulate.json) | 0.256 | unrelated |  |  |
| [clear](../../../traits/instructions/clear.json) | 0.232 | unrelated | 0 |  |
| [narrative](../../../traits/instructions/narrative.json) | 0.221 | similar | 1 |  |
| [historical](../../../traits/instructions/historical.json) | 0.208 | unrelated |  |  |
| [dramatic](../../../traits/instructions/dramatic.json) | 0.199 | similar | 1 |  |
| [wide-eyed](../../../traits/instructions/wide_eyed.json) | 0.198 | similar | 1 |  |
| [forgetful](../../../traits/instructions/forgetful.json) | 0.193 | opposed |  |  |
| [animated](../../../traits/instructions/animated.json) | 0.192 | similar | 1 |  |
| [flat](../../../traits/instructions/flat.json) (expanded) | 0.123 | opposed |  |  |
| [jaded](../../../traits/instructions/jaded.json) (expanded) | 0.095 | opposed |  |  |
| [cryptic](../../../traits/instructions/cryptic.json) (expanded) | 0.075 | opposed |  |  |
| [expository](../../../traits/instructions/expository.json) (expanded) | 0.035 | unrelated |  |  |
| [emotionally-inarticulate](../../../traits/instructions/emotionally_inarticulate.json) (expanded) | 0.027 | unrelated |  |  |
| [vague](../../../traits/instructions/vague.json) (expanded) | 0.002 | opposed |  |  |

### warlike (cut-off 4, 10 pairs judged)

Gloss: This means meeting every disagreement as a fight to be won, bristling at the slightest challenge, pressing the attack first, and taking hostility as the natural way to deal with others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [disagreeable](../../../traits/instructions/disagreeable.json) | 0.380 | unrelated | 2 |  |
| [confrontational](../../../traits/instructions/confrontational.json) | 0.342 | similar | 3 | 3 |
| [aggressive](../../../traits/instructions/aggressive.json) | 0.307 | similar | 3 | 3 |
| [hostile](../../../traits/instructions/hostile.json) | 0.266 | similar | 3 | 3 |
| [partisan](../../../traits/instructions/partisan.json) | 0.259 | unrelated | 1 |  |
| [unyielding](../../../traits/instructions/unyielding.json) | 0.236 | unrelated | 1 |  |
| [brave](../../../traits/instructions/brave.json) | 0.229 | unrelated | 1 |  |
| [gain-seeking](../../../traits/instructions/gain_seeking.json) | 0.225 | unrelated | 0 |  |
| [tactical](../../../traits/instructions/tactical.json) | 0.214 | unrelated | 0 |  |
| [closure-seeking](../../../traits/instructions/closure_seeking.json) | 0.211 | unrelated | 0 |  |
| [friendly](../../../traits/instructions/friendly.json) (expanded) | 0.144 | opposed |  |  |
| [peaceful](../../../traits/instructions/peaceful.json) (expanded) | 0.119 | opposed |  |  |
| [strategic](../../../traits/instructions/strategic.json) (expanded) | 0.109 | opposed |  |  |
| [accommodating](../../../traits/instructions/accommodating.json) (expanded) | 0.107 | opposed |  |  |
| [agreeable](../../../traits/instructions/agreeable.json) (expanded) | 0.101 | opposed |  |  |
| [conciliatory](../../../traits/instructions/conciliatory.json) (expanded) | 0.095 | opposed |  |  |
| [loss-averse](../../../traits/instructions/loss_averse.json) (expanded) | 0.078 | opposed |  |  |
| [cowardly](../../../traits/instructions/cowardly.json) (expanded) | 0.067 | opposed |  |  |
| [ambiguity-tolerant](../../../traits/instructions/ambiguity_tolerant.json) (expanded) | 0.047 | opposed |  |  |
| [nonpartisan](../../../traits/instructions/nonpartisan.json) (expanded) | 0.002 | opposed |  |  |

### well informed (cut-off 3, 10 pairs judged)

Gloss: This means keeping abreast of facts and current matters across a broad range of subjects.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [generalist](../../../traits/instructions/generalist.json) | 0.342 | similar | 2 | 2 |
| [news-junkie](../../../traits/instructions/news_junkie.json) | 0.330 | similar | 2 | 2 |
| [political](../../../traits/instructions/political.json) | 0.292 | unrelated | 1 |  |
| [contemporary](../../../traits/instructions/contemporary.json) | 0.247 | similar | 1 |  |
| [plugged-in](../../../traits/instructions/plugged_in.json) | 0.246 | similar | 1 |  |
| [inclusive](../../../traits/instructions/inclusive.json) | 0.233 | similar | 0 |  |
| [accurate](../../../traits/instructions/accurate.json) | 0.229 | similar | 1 |  |
| [interdisciplinary](../../../traits/instructions/interdisciplinary.json) | 0.225 | similar | 1 |  |
| [well-connected](../../../traits/instructions/well_connected.json) | 0.220 | similar | 0 |  |
| [cosmopolitan](../../../traits/instructions/cosmopolitan.json) | 0.208 | similar | 0 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) (expanded) | 0.178 | opposed |  |  |
| [unplugged](../../../traits/instructions/unplugged.json) (expanded) | 0.153 | opposed |  |  |
| [specialist](../../../traits/instructions/specialist.json) (expanded) | 0.153 | opposed |  |  |
| [apolitical](../../../traits/instructions/apolitical.json) (expanded) | 0.104 | opposed |  |  |
| [inaccurate](../../../traits/instructions/inaccurate.json) (expanded) | 0.103 | opposed |  |  |
| [exclusionary](../../../traits/instructions/exclusionary.json) (expanded) | 0.034 | opposed |  |  |
| [isolated](../../../traits/instructions/isolated.json) (expanded) | 0.029 | opposed |  |  |

### wishful (cut-off 3, 9 pairs judged)

Gloss: This means wanting things and dwelling on what one lacks or desires.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [discontented](../../../traits/instructions/discontented.json) | 0.344 | similar | 2 | 2 |
| [greedy](../../../traits/instructions/greedy.json) | 0.316 | similar | 1 |  |
| [envious](../../../traits/instructions/envious.json) | 0.270 | similar | 1 |  |
| [lustful](../../../traits/instructions/lustful.json) | 0.242 | unrelated |  |  |
| [self-pitying](../../../traits/instructions/self_pitying.json) | 0.236 | similar | 1 |  |
| [status-seeking](../../../traits/instructions/status_seeking.json) | 0.231 | similar | 1 |  |
| [restless](../../../traits/instructions/restless.json) | 0.231 | similar | 1 |  |
| [ambitious](../../../traits/instructions/ambitious.json) | 0.229 | similar | 2 | 1 |
| [materialistic](../../../traits/instructions/materialistic.json) | 0.220 | similar | 1 |  |
| [insecure](../../../traits/instructions/insecure.json) | 0.212 | similar | 1 |  |
| [contented](../../../traits/instructions/contented.json) (expanded) | 0.210 | opposed |  |  |
| [unambitious](../../../traits/instructions/unambitious.json) (expanded) | 0.110 | opposed |  |  |
| [chaste](../../../traits/instructions/chaste.json) (expanded) | 0.089 | unrelated |  |  |
| [spiritual](../../../traits/instructions/spiritual.json) (expanded) | 0.022 | unrelated |  |  |
| [self-assured](../../../traits/instructions/self_assured.json) (expanded) | -0.016 | opposed |  |  |

### wishful thinking (cut-off 4, 7 pairs judged)

Gloss: This means believing what one wants to be true rather than what evidence shows.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) | 0.352 | similar | 3 | 3 |
| [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | 0.311 | opposed |  |  |
| [credulous](../../../traits/instructions/credulous.json) | 0.308 | unrelated | 2 |  |
| [just-world-believing](../../../traits/instructions/just_world_believing.json) | 0.259 | unrelated |  |  |
| [closed-minded](../../../traits/instructions/closed_minded.json) | 0.256 | similar | 2 |  |
| [science-skeptical](../../../traits/instructions/science_skeptical.json) | 0.230 | unrelated | 1 |  |
| [calibrated](../../../traits/instructions/calibrated.json) | 0.230 | opposed |  |  |
| [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | 0.225 | similar | 2 |  |
| [science-trusting](../../../traits/instructions/science_trusting.json) | 0.215 | opposed |  |  |
| [illogical](../../../traits/instructions/illogical.json) | 0.206 | unrelated | 1 |  |
| [logical](../../../traits/instructions/logical.json) (expanded) | 0.121 | opposed |  |  |
| [skeptical](../../../traits/instructions/skeptical.json) (expanded) | 0.117 | opposed |  |  |
| [open-minded](../../../traits/instructions/open_minded.json) (expanded) | 0.114 | opposed |  |  |
| [overconfident](../../../traits/instructions/overconfident.json) (expanded) | 0.108 | unrelated | 2 |  |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) (expanded) | 0.073 | opposed |  |  |

### wishy washy (cut-off 3, 10 pairs judged)

Gloss: This means lacking firm conviction and changing one's mind readily when faced with difficulty or opposition.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [uncertain](../../../traits/instructions/uncertain.json) | 0.350 | similar | 2 | 2 |
| [fragile](../../../traits/instructions/fragile.json) | 0.333 | similar | 1 |  |
| [mercurial](../../../traits/instructions/mercurial.json) | 0.320 | similar | 2 | 1 |
| [indecisive](../../../traits/instructions/indecisive.json) | 0.317 | similar | 2 | 2 |
| [self-uncertain](../../../traits/instructions/self_uncertain.json) | 0.316 | similar | 1 |  |
| [flexible](../../../traits/instructions/flexible.json) | 0.274 | unrelated | 1 |  |
| [noncommittal](../../../traits/instructions/noncommittal.json) | 0.266 | similar | 2 | 2 |
| [cowardly](../../../traits/instructions/cowardly.json) | 0.264 | similar | 1 |  |
| [erratic](../../../traits/instructions/erratic.json) | 0.253 | similar | 2 | 1 |
| [treacherous](../../../traits/instructions/treacherous.json) | 0.251 | unrelated | 1 |  |
| [resilient](../../../traits/instructions/resilient.json) (expanded) | 0.175 | opposed |  |  |
| [rigid](../../../traits/instructions/rigid.json) (expanded) | 0.113 | opposed |  |  |
| [confident](../../../traits/instructions/confident.json) (expanded) | 0.101 | opposed |  |  |
| [brave](../../../traits/instructions/brave.json) (expanded) | 0.080 | opposed |  |  |
| [steady](../../../traits/instructions/steady.json) (expanded) | 0.065 | opposed |  |  |
| [loyal](../../../traits/instructions/loyal.json) (expanded) | 0.056 | opposed |  |  |
| [decisive](../../../traits/instructions/decisive.json) (expanded) | 0.055 | opposed |  |  |
| [self-certain](../../../traits/instructions/self_certain.json) (expanded) | 0.046 | opposed |  |  |
| [opinionated](../../../traits/instructions/opinionated.json) (expanded) | 0.039 | opposed |  |  |

### withdrawn (cut-off 3, 7 pairs judged)

Gloss: This means keeping to oneself, avoiding social contact, and speaking little in the company of others.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [introverted](../../../traits/instructions/introverted.json) | 0.481 | similar | 2 | 2 |
| [isolated](../../../traits/instructions/isolated.json) | 0.365 | similar | 1 |  |
| [solitary](../../../traits/instructions/solitary.json) | 0.342 | similar | 2 | 2 |
| [reserved](../../../traits/instructions/reserved.json) | 0.337 | similar | 2 | 2 |
| [avoidant](../../../traits/instructions/avoidant.json) | 0.324 | unrelated |  |  |
| [only child](../../../traits/instructions/only_child.json) | 0.270 | unrelated |  |  |
| [self-effacing](../../../traits/instructions/self_effacing.json) | 0.250 | similar | 2 | 1 |
| [opaque](../../../traits/instructions/opaque.json) | 0.244 | similar | 1 |  |
| [homebody](../../../traits/instructions/homebody.json) | 0.239 | unrelated | 1 |  |
| [news-avoidant](../../../traits/instructions/news_avoidant.json) | 0.232 | unrelated |  |  |
| [extroverted](../../../traits/instructions/extroverted.json) (expanded) | 0.148 | opposed |  |  |
| [gregarious](../../../traits/instructions/gregarious.json) (expanded) | 0.090 | opposed |  |  |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) (expanded) | 0.068 | opposed |  |  |
| [many siblings](../../../traits/instructions/many_siblings.json) (expanded) | 0.064 | unrelated |  |  |
| [expressive](../../../traits/instructions/expressive.json) (expanded) | 0.037 | opposed |  |  |
| [well-connected](../../../traits/instructions/well_connected.json) (expanded) | 0.005 | opposed |  |  |
| [globetrotter](../../../traits/instructions/globetrotter.json) (expanded) | 0.003 | opposed |  |  |
| [news-junkie](../../../traits/instructions/news_junkie.json) (expanded) | 0.000 | unrelated |  |  |
| [transparent](../../../traits/instructions/transparent.json) (expanded) | -0.012 | opposed |  |  |

### yielding (cut-off 4, 9 pairs judged)

Gloss: This means accepting others' wishes and stepping back from one's own claims rather than pushing for what one wants.

| nearest trait | cosine | relation | Sonnet | Opus |
|---|---|---|---|---|
| [submissive](../../../traits/instructions/submissive.json) | 0.398 | similar | 3 | 3 |
| [accommodating](../../../traits/instructions/accommodating.json) | 0.335 | similar | 3 | 3 |
| [self-effacing](../../../traits/instructions/self_effacing.json) | 0.324 | similar | 1 |  |
| [self-accepting](../../../traits/instructions/self_accepting.json) | 0.304 | unrelated |  |  |
| [humble](../../../traits/instructions/humble.json) | 0.280 | similar | 1 |  |
| [deferential](../../../traits/instructions/deferential.json) | 0.267 | similar | 2 |  |
| [modest](../../../traits/instructions/modest.json) | 0.263 | similar | 1 |  |
| [peaceful](../../../traits/instructions/peaceful.json) | 0.262 | similar | 2 |  |
| [guarded](../../../traits/instructions/guarded.json) | 0.245 | unrelated | 1 |  |
| [forgiving](../../../traits/instructions/forgiving.json) | 0.240 | similar | 1 |  |
| [unyielding](../../../traits/instructions/unyielding.json) (expanded) | 0.179 | opposed |  |  |
| [attention-seeking](../../../traits/instructions/attention_seeking.json) (expanded) | 0.055 | opposed |  |  |
| [unforgiving](../../../traits/instructions/unforgiving.json) (expanded) | 0.036 | opposed |  |  |
| [dominant](../../../traits/instructions/dominant.json) (expanded) | 0.029 | opposed |  |  |
| [aggressive](../../../traits/instructions/aggressive.json) (expanded) | 0.016 | opposed |  |  |
| [forthright](../../../traits/instructions/forthright.json) (expanded) | -0.007 | opposed |  |  |
| [arrogant](../../../traits/instructions/arrogant.json) (expanded) | -0.011 | opposed |  |  |
| [self-critical](../../../traits/instructions/self_critical.json) (expanded) | -0.028 | unrelated |  |  |
