# Recovery test: `testing/paraphrase_set` (`rec_testing_paraphrase_set`)

The recovery harness ([recovery_test.py](../../../../data_analysis/gap_generation/recovery_test.py), library [recovery.py](../../../../assistant_axis/gapgen/recovery.py)) hides a seeded share of the corpus's traits, scores the generator's run with M3 against the corpus without them ([novelty_score.py](../../../../data_analysis/gap_generation/novelty_score.py) `score --hide`), and asks which hidden traits the run's candidates find again.  Terms:

- **hidden**: traits taken out of the corpus for the test; a pair, triangle or tetrahedron hides whole, any other trait alone, drawn by region so that each region hides its share.
- **kept**: a candidate M3 decided `new` or `grey` against the reduced corpus (what the pipeline would pass on); **covered**: one M3 turned away because a remaining trait covers it.
- **recovered**: a hidden trait matched by a kept candidate, by its label (the same stem or a former stem, no model call) or by the overlap call (rubric A, Sonnet then Opus under M3's rule) at the candidate's cut-off or above (the cut-off is 3 on rubric A's 0-4 scale far from alignment, 4 near it).
- **recall**: hidden traits recovered over hidden traits; **precision**: kept candidates that recover a hidden trait over kept candidates (low by design when a generator proposes mostly genuinely new words).
- **false cover**: a covered candidate that matches a hidden trait: it fills the hidden trait's gap but M3 turned it away because another trait covers it (often a near-duplicate of the hidden one).
- **reachable**: hidden traits among some decided candidate's 10 nearest traits in the full corpus (or named by its label): only those are judged, so this bounds recall.

## Figures

| seed | hidden | kept candidates | recall | by label | precision | groups whole | reachable | false covers (candidates) | recall incl. covered | cost |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 120 of 932 | 53 | 45.0% (54) | 1 | 98.1% | 1 of 40 | 91.7% | 26 | 66.7% | $1.265 |

Total cost $1.265 (each seed's reduced-corpus M3 run and its match calls; [usage.json](./usage.json); every figure is in [recovery_report.json](./recovery_report.json)).

## Recall by region

| region | seed 0 |
|---|---|
| alignment_ai_agent | 1 of 2 (50.0%) |
| cognitive_epistemic | 10 of 29 (34.5%) |
| communication_style | 7 of 15 (46.7%) |
| emotional_temperament | 9 of 21 (42.9%) |
| identity_demographic | 5 of 11 (45.5%) |
| moral_stance | 10 of 20 (50.0%) |
| social_interpersonal | 12 of 22 (54.5%) |

## Recall by arrangement kind

| arrangement kind | seed 0 |
|---|---|
| pair | 30 of 80 (37.5%) |
| sequence | 0 of 1 (0.0%) |
| set | 0 of 2 (0.0%) |
| singleton | 18 of 29 (62.1%) |
| unclassified | 6 of 8 (75.0%) |

## Seed 0

Hidden traits: [hidden.json](./seed0/hidden.json); the reduced-corpus M3 run: [decisions.md](../../novelty/rec_testing_paraphrase_set_s0/decisions.md) ({"covered": 26, "new": 53}); every pair judged: [matches.jsonl](./seed0/matches.jsonl).

### Recovered (54 of 120)

| hidden trait | region | kind | recovered by | how |
|---|---|---|---|---|
| [anecdotal](../../../traits/instructions/anecdotal.json) | cognitive_epistemic | pair | overgeneralizing | Sonnet 3, Opus 3 |
| [aristocratic](../../../traits/instructions/aristocratic.json) | moral_stance | singleton | dynastic | Sonnet 3, Opus 3 |
| [artistic](../../../traits/instructions/artistic.json) | identity_demographic | singleton | creatively productive | Sonnet 3, Opus 4 |
| [authentic](../../../traits/instructions/authentic.json) | social_interpersonal | pair | consistently genuine | Sonnet 3, Opus 4 |
| [avoidant](../../../traits/instructions/avoidant.json) | emotional_temperament | singleton | evasive | Sonnet 4 |
| [chaotic](../../../traits/instructions/chaotic.json) | cognitive_epistemic | singleton | disorderly | Sonnet 3, Opus 4 |
| [conciliatory](../../../traits/instructions/conciliatory.json) | social_interpersonal | pair | peacemaking | Sonnet 3, Opus 4 |
| [concrete](../../../traits/instructions/concrete.json) | cognitive_epistemic | pair | particularistic | Sonnet 3, Opus 3 |
| [confrontational](../../../traits/instructions/confrontational.json) | social_interpersonal | pair | confrontational | label |
| [consequentialist](../../../traits/instructions/consequentialist.json) | moral_stance | pair | outcome-oriented | Sonnet 4, Opus 4 |
| [controlling](../../../traits/instructions/controlling.json) | social_interpersonal | singleton | domineering | Sonnet 3, Opus 4 |
| [cosmopolitan](../../../traits/instructions/cosmopolitan.json) | moral_stance | singleton | globally minded | Sonnet 4 |
| [despairing](../../../traits/instructions/despairing.json) | emotional_temperament | singleton | hopelessly regretful | Sonnet 3, Opus 4 |
| [disagreeable](../../../traits/instructions/disagreeable.json) | social_interpersonal | pair | confrontational | Sonnet 3, Opus 3 |
| [dismissive](../../../traits/instructions/dismissive.json) | social_interpersonal | pair | disdainful | Sonnet 3, Opus 4 |
| [earnest](../../../traits/instructions/earnest.json) | communication_style | pair | unironic | Sonnet 3, Opus 3 |
| [ecocentric](../../../traits/instructions/ecocentric.json) | moral_stance | pair | biocentric | Sonnet 3, Opus 3 |
| [effusive](../../../traits/instructions/effusive.json) | emotional_temperament | unclassified | unrestrained | Sonnet 3, Opus 4 |
| [elitist](../../../traits/instructions/elitist.json) | moral_stance | pair | dynastic | Sonnet 2, Opus 3 |
| [empathetic](../../../traits/instructions/empathetic.json) | social_interpersonal | unclassified | emotionally attuned | Sonnet 4 |
| [entitled](../../../traits/instructions/entitled.json) | social_interpersonal | singleton | privileged | Sonnet 4, Opus 4 |
| [epicurean](../../../traits/instructions/epicurean.json) | emotional_temperament | pair | refined | Sonnet 3, Opus 3 |
| [fair](../../../traits/instructions/fair.json) | moral_stance | pair | equitable, impartial | Sonnet 3, Opus 3; Sonnet 4, Opus 4 |
| [foolish](../../../traits/instructions/foolish.json) | cognitive_epistemic | pair | shortsighted | Sonnet 3, Opus 3 |
| [futuristic](../../../traits/instructions/futuristic.json) | cognitive_epistemic | singleton | forward thinking | Sonnet 3, Opus 3 |
| [gluttonous](../../../traits/instructions/gluttonous.json) | emotional_temperament | pair | voracious | Sonnet 3, Opus 4 |
| [intellectually honest](../../../traits/instructions/intellectually_honest.json) | cognitive_epistemic | pair | scrupulous | Sonnet 3, Opus 4 |
| [jaded](../../../traits/instructions/jaded.json) | emotional_temperament | pair | blasé | Sonnet 3, Opus 4 |
| [misanthropic](../../../traits/instructions/misanthropic.json) | social_interpersonal | singleton | antisocial | Sonnet 4 |
| [nomadic](../../../traits/instructions/nomadic.json) | identity_demographic | pair | footloose | Sonnet 3, Opus 4 |
| [opaque](../../../traits/instructions/opaque.json) | communication_style | pair | secretive | Sonnet 3, Opus 4 |
| [open-minded](../../../traits/instructions/open_minded.json) | cognitive_epistemic | pair | receptive to argument | Sonnet 4 |
| [paradoxical](../../../traits/instructions/paradoxical.json) | cognitive_epistemic | singleton | contradiction tolerant | Sonnet 4 |
| [paranoid](../../../traits/instructions/paranoid.json) | social_interpersonal | unclassified | suspicious | Sonnet 3, Opus 4 |
| [patriotic](../../../traits/instructions/patriotic.json) | identity_demographic | singleton | nationally loyal | Sonnet 3, Opus 4 |
| [pedantic](../../../traits/instructions/pedantic.json) | communication_style | singleton | hairsplitting | Sonnet 4 |
| [poetic](../../../traits/instructions/poetic.json) | communication_style | pair | lyrical | Sonnet 3, Opus 4 |
| [prescriptive](../../../traits/instructions/prescriptive.json) | communication_style | pair | directive | Sonnet 3, Opus 3 |
| [progressive](../../../traits/instructions/progressive.json) | moral_stance | pair | forward thinking | Sonnet 3, Opus 3 |
| [promiscuous](../../../traits/instructions/promiscuous.json) | social_interpersonal | singleton | sexually casual | Sonnet 4 |
| [romantic](../../../traits/instructions/romantic.json) | communication_style | singleton | emotionally driven | Sonnet 3, Opus 3 |
| [self-critical](../../../traits/instructions/self_critical.json) | emotional_temperament | pair | perfectionistic | Sonnet 3, Opus 4 |
| [self-pitying](../../../traits/instructions/self_pitying.json) | emotional_temperament | singleton | maudlin | Sonnet 3, Opus 4 |
| [straight](../../../traits/instructions/straight.json) | identity_demographic | pair | heterosexual | Sonnet 4 |
| [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | communication_style | unclassified | associative | Sonnet 3, Opus 3 |
| [structuralist](../../../traits/instructions/structuralist.json) | cognitive_epistemic | singleton | structural | Sonnet 3, Opus 4 |
| [subversive](../../../traits/instructions/subversive.json) | moral_stance | unclassified | undermining | Sonnet 4, Opus 4 |
| [superficial](../../../traits/instructions/superficial.json) | cognitive_epistemic | pair | shallow | Sonnet 4 |
| [treacherous](../../../traits/instructions/treacherous.json) | moral_stance | pair | perfidious | Sonnet 4, Opus 4 |
| [unhelpful](../../../traits/instructions/unhelpful.json) | alignment_ai_agent | pair | uncooperative | Sonnet 3, Opus 4 |
| [untrustworthy](../../../traits/instructions/untrustworthy.json) | moral_stance | pair | self-serving | Sonnet 3, Opus 4 |
| [urban](../../../traits/instructions/urban.json) | identity_demographic | pair | metropolitan | Sonnet 3, Opus 4 |
| [vindictive](../../../traits/instructions/vindictive.json) | social_interpersonal | unclassified | vengeful | Sonnet 4, Opus 4 |
| [vulnerable-narcissistic](../../../traits/instructions/vulnerable_narcissistic.json) | emotional_temperament | singleton | covert narcissistic | Sonnet 3, Opus 3 |

### False covers (26 candidates)

| candidate | matches hidden | how | covered by | hidden trait recovered anyway |
|---|---|---|---|---|
| adaptable | [flexible](../../../traits/instructions/flexible.json) | Sonnet 4, Opus 4 | [adaptable](../../../traits/instructions/adaptable.json) | no |
| altruistic | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 3, Opus 3 | [altruistic](../../../traits/instructions/altruistic.json) | no |
| callous | [sociopathic](../../../traits/instructions/sociopathic.json) | Sonnet 3, Opus 4 | [callous](../../../traits/instructions/callous.json) | no |
| civilizationally insular | [civilizationist](../../../traits/instructions/civilizationist.json) | Sonnet 3, Opus 4 | [nationalist](../../../traits/instructions/nationalist.json) | no |
| collaborative | [cooperative](../../../traits/instructions/cooperative.json) | Sonnet 4 | [collaborative](../../../traits/instructions/collaborative.json) | no |
| contrarian | [provocative](../../../traits/instructions/provocative.json) | Sonnet 3, Opus 4 | [contrarian](../../../traits/instructions/contrarian.json) | no |
| dispassionate | [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | Sonnet 4, Opus 4 | [dispassionate](../../../traits/instructions/dispassionate.json) | no |
| easily alarmed | [panicky](../../../traits/instructions/panicky.json) | Sonnet 3, Opus 4 | [neurotic (Big Five)](../../../traits/instructions/neurotic_big_five.json) | no |
| emotionally open | [expressive](../../../traits/instructions/expressive.json) | Sonnet 3, Opus 4 | [emotional](../../../traits/instructions/emotional.json) | no |
| forbearing | [placid](../../../traits/instructions/placid.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | no |
| improvisational | [resourceful](../../../traits/instructions/resourceful.json) | Sonnet 3, Opus 4 | [improvisational](../../../traits/instructions/improvisational.json) | no |
| innovative | [creative](../../../traits/instructions/creative.json) | Sonnet 3, Opus 4 | [innovative](../../../traits/instructions/innovative.json) | no |
| integrative | [interdisciplinary](../../../traits/instructions/interdisciplinary.json) | Sonnet 3, Opus 4 | [generalist](../../../traits/instructions/generalist.json) | no |
| manly | [masculine](../../../traits/instructions/masculine.json) | Sonnet 4 | [overmasculine](../../../traits/instructions/overmasculine.json) | no |
| modern | [contemporary](../../../traits/instructions/contemporary.json) | Sonnet 3, Opus 4 | [modern](../../../traits/instructions/modern.json) | no |
| practical | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 4 | [practical](../../../traits/instructions/practical.json) | no |
| reformist | [progressive](../../../traits/instructions/progressive.json) | Sonnet 3, Opus 3 | [radical](../../../traits/instructions/radical.json) | yes |
| resigned | [fatalistic](../../../traits/instructions/fatalistic.json) | Sonnet 3, Opus 4 | [resigned](../../../traits/instructions/resigned.json) | no |
| slapdash | [sloppy](../../../traits/instructions/sloppy.json) | Sonnet 3, Opus 4 | [careless](../../../traits/instructions/careless.json) | no |
| straightforward | [plain-spoken](../../../traits/instructions/plain_spoken.json) | Sonnet 3, Opus 4 | [straightforward](../../../traits/instructions/straightforward.json) | no |
| systemic | [systems-thinker](../../../traits/instructions/systems_thinker.json) | Sonnet 3, Opus 4 | [holistic](../../../traits/instructions/holistic.json) | no |
| tactful | [diplomatic](../../../traits/instructions/diplomatic.json) | Sonnet 4 | [tactful](../../../traits/instructions/tactful.json) | no |
| traditional | [conservative](../../../traits/instructions/conservative.json) | Sonnet 3, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | no |
| traditional | [nostalgic](../../../traits/instructions/nostalgic.json) | Sonnet 2, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | no |
| traditional | [ritualistic](../../../traits/instructions/ritualistic.json) | Sonnet 3, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | no |
| traditional | [conservative](../../../traits/instructions/conservative.json) | Sonnet 3, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | no |
| traditional | [conventional](../../../traits/instructions/conventional.json) | Sonnet 2, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | no |
| unflappable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | no |

### Not recovered (66)

[abstemious](../../../traits/instructions/abstemious.json), [abstract](../../../traits/instructions/abstract.json), [agreeable](../../../traits/instructions/agreeable.json), [anthropocentric](../../../traits/instructions/anthropocentric.json), [civilizationist](../../../traits/instructions/civilizationist.json), [closed-minded](../../../traits/instructions/closed_minded.json), [competitive](../../../traits/instructions/competitive.json), [conservative](../../../traits/instructions/conservative.json), [contemporary](../../../traits/instructions/contemporary.json), [conventional](../../../traits/instructions/conventional.json), [cooperative](../../../traits/instructions/cooperative.json), [creative](../../../traits/instructions/creative.json), [data-driven](../../../traits/instructions/data_driven.json), [deontological](../../../traits/instructions/deontological.json), [descriptive](../../../traits/instructions/descriptive.json), [diplomatic](../../../traits/instructions/diplomatic.json), [eccentric](../../../traits/instructions/eccentric.json), [egalitarian](../../../traits/instructions/egalitarian.json), [eloquent](../../../traits/instructions/eloquent.json), [expressive](../../../traits/instructions/expressive.json), [fatalistic](../../../traits/instructions/fatalistic.json), [feminine](../../../traits/instructions/feminine.json), [flexible](../../../traits/instructions/flexible.json), [gay](../../../traits/instructions/gay.json), [grandiose](../../../traits/instructions/grandiose.json), [helpful](../../../traits/instructions/helpful.json), [helpless](../../../traits/instructions/helpless.json), [idealistic](../../../traits/instructions/idealistic.json), [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json), [interdisciplinary](../../../traits/instructions/interdisciplinary.json), [irascible](../../../traits/instructions/irascible.json), [loyal](../../../traits/instructions/loyal.json), [masculine](../../../traits/instructions/masculine.json), [meticulous](../../../traits/instructions/meticulous.json), [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json), [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json), [nostalgic](../../../traits/instructions/nostalgic.json), [panicky](../../../traits/instructions/panicky.json), [performative](../../../traits/instructions/performative.json), [philanthropic](../../../traits/instructions/philanthropic.json), [placid](../../../traits/instructions/placid.json), [plain-spoken](../../../traits/instructions/plain_spoken.json), [pragmatic](../../../traits/instructions/pragmatic.json), [prosaic](../../../traits/instructions/prosaic.json), [provocative](../../../traits/instructions/provocative.json), [reserved](../../../traits/instructions/reserved.json), [resourceful](../../../traits/instructions/resourceful.json), [rigid](../../../traits/instructions/rigid.json), [ritualistic](../../../traits/instructions/ritualistic.json), [rural](../../../traits/instructions/rural.json), [sardonic](../../../traits/instructions/sardonic.json), [self-accepting](../../../traits/instructions/self_accepting.json), [settled](../../../traits/instructions/settled.json), [sloppy](../../../traits/instructions/sloppy.json), [sociopathic](../../../traits/instructions/sociopathic.json), [spartan](../../../traits/instructions/spartan.json), [status-seeking](../../../traits/instructions/status_seeking.json), [stoic](../../../traits/instructions/stoic.json), [supportive](../../../traits/instructions/supportive.json), [systems-thinker](../../../traits/instructions/systems_thinker.json), [thorough](../../../traits/instructions/thorough.json), [transparent](../../../traits/instructions/transparent.json), [trustworthy](../../../traits/instructions/trustworthy.json), [unfair](../../../traits/instructions/unfair.json), [wide-eyed](../../../traits/instructions/wide_eyed.json), [wise](../../../traits/instructions/wise.json)

