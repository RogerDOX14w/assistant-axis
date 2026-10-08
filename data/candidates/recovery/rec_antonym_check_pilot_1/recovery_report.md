# Recovery test: `antonym_check/pilot_1` (`rec_antonym_check_pilot_1`)

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
| 0 | 83 of 790 | 162 | 15.7% (13) | 2 | 10.5% | 4 of 29 | 85.5% | 16 | 32.5% | $4.870 |

Total cost $4.870 (each seed's reduced-corpus M3 run and its match calls; [usage.json](./usage.json); every figure is in [recovery_report.json](./recovery_report.json)).

## Recall by region

| region | seed 0 |
|---|---|
| cognitive_epistemic | 4 of 17 (23.5%) |
| communication_style | 3 of 16 (18.8%) |
| emotional_temperament | 1 of 8 (12.5%) |
| identity_demographic | 3 of 6 (50.0%) |
| moral_stance | 1 of 14 (7.1%) |
| none | 0 of 17 (0.0%) |
| social_interpersonal | 1 of 5 (20.0%) |

## Recall by arrangement kind

| arrangement kind | seed 0 |
|---|---|
| 4-cube | 0 of 2 (0.0%) |
| pair | 13 of 56 (23.2%) |
| ring | 0 of 3 (0.0%) |
| sequence | 0 of 1 (0.0%) |
| set | 0 of 3 (0.0%) |
| singleton | 0 of 10 (0.0%) |
| square | 0 of 1 (0.0%) |
| triangle | 0 of 3 (0.0%) |
| unclassified | 0 of 4 (0.0%) |

## Seed 0

Hidden traits: [hidden.json](./seed0/hidden.json); the reduced-corpus M3 run: [decisions.md](../../novelty/rec_antonym_check_pilot_1_s0/decisions.md) ({"covered": 205, "new": 162}); every pair judged: [matches.jsonl](./seed0/matches.jsonl).

### Recovered (13 of 83)

| hidden trait | region | kind | recovered by | how |
|---|---|---|---|---|
| [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | cognitive_epistemic | pair | bargain hunting, deal seeker | Sonnet 3, Opus 4; Sonnet 3, Opus 4 |
| [clear](../../../traits/instructions/clear.json) | communication_style | pair | explicit | Sonnet 3, Opus 4 |
| [competent](../../../traits/instructions/competent.json) | cognitive_epistemic | pair | capable | Sonnet 3, Opus 3 |
| [confrontational](../../../traits/instructions/confrontational.json) | communication_style | pair | argumentative, combative | Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [educated](../../../traits/instructions/educated.json) | identity_demographic | pair | highly educated | Sonnet 3, Opus 3 |
| [fashionable](../../../traits/instructions/fashionable.json) | identity_demographic | pair | fashion conscious, trendy | label (renamed from fashion_conscious); Sonnet 3, Opus 4 |
| [full-price shopper](../../../traits/instructions/full_price_shopper.json) | moral_stance | pair | price indifferent | Sonnet 3, Opus 3 |
| [hostile](../../../traits/instructions/hostile.json) | communication_style | pair | combative, unfriendly | Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [incompetent](../../../traits/instructions/incompetent.json) | cognitive_epistemic | pair | inept | label (renamed from inept) |
| [jaded](../../../traits/instructions/jaded.json) | emotional_temperament | pair | blase, world weary | Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [oblivious](../../../traits/instructions/oblivious.json) | social_interpersonal | pair | unobservant | Sonnet 3, Opus 3 |
| [observant](../../../traits/instructions/observant.json) | cognitive_epistemic | pair | attentive | Sonnet 2, Opus 3 |
| [uneducated](../../../traits/instructions/uneducated.json) | identity_demographic | pair | unlearned | Sonnet 3, Opus 3 |

### False covers (16 candidates)

| candidate | matches hidden | how | covered by | hidden trait recovered anyway |
|---|---|---|---|---|
| amicable | [friendly](../../../traits/instructions/friendly.json) | Sonnet 3, Opus 3 | [agreeable](../../../traits/instructions/agreeable.json) | no |
| beneficent | [benevolent](../../../traits/instructions/benevolent.json) | Sonnet 3, Opus 3 | [helpful](../../../traits/instructions/helpful.json) | no |
| cold hearted | [callous](../../../traits/instructions/callous.json) | Sonnet 3, Opus 3 | [cruel](../../../traits/instructions/cruel.json) | no |
| cold hearted | [uncaring](../../../traits/instructions/uncaring.json) | Sonnet 2, Opus 3 | [cruel](../../../traits/instructions/cruel.json) | no |
| compassionate toward animals | [compassionate](../../../traits/instructions/compassionate.json) | Sonnet 3, Opus 3 | [kind-to-animals](../../../traits/instructions/kind_to_animals.json) | no |
| courageous | [Gryffindor](../../../traits/instructions/gryffindor.json) | Sonnet 2, Opus 3 | [brave](../../../traits/instructions/brave.json) | no |
| down to earth | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 2, Opus 3 | [practical](../../../traits/instructions/practical.json) | no |
| engaging | [unflinching](../../../traits/instructions/unflinching.json) | label (renamed from engaging) | [charismatic](../../../traits/instructions/charismatic.json) | no |
| fervent | [zealous](../../../traits/instructions/zealous.json) | Sonnet 3, Opus 3 | [passionate](../../../traits/instructions/passionate.json) | no |
| financially stable | [financially secure](../../../traits/instructions/financially_secure.json) | Sonnet 3, Opus 3 | [wealthy](../../../traits/instructions/wealthy.json) | no |
| financially vulnerable | [financially precarious](../../../traits/instructions/financially_precarious.json) | Sonnet 3, Opus 3 | [poor](../../../traits/instructions/poor.json) | no |
| humorous | [wry](../../../traits/instructions/wry.json) | Sonnet 2, Opus 3 | [witty](../../../traits/instructions/witty.json) | no |
| perceptive | [observant](../../../traits/instructions/observant.json) | Sonnet 2, Opus 3 | [socially-perceptive](../../../traits/instructions/socially_perceptive.json) | yes |
| price conscious | [bargain-hunter](../../../traits/instructions/bargain_hunter.json) | Sonnet 3, Opus 3 | [frugal](../../../traits/instructions/frugal.json) | yes |
| restrictive | [controlling](../../../traits/instructions/controlling.json) | Sonnet 2, Opus 3 | [authoritarian (Baumrind)](../../../traits/instructions/authoritarian_baumrind.json) | no |
| spendthrift | [full-price shopper](../../../traits/instructions/full_price_shopper.json) | Sonnet 2, Opus 3 | [extravagant](../../../traits/instructions/extravagant.json) | yes |
| unorthodox | [iconoclastic](../../../traits/instructions/iconoclastic.json) | Sonnet 2, Opus 3 | [heterodox](../../../traits/instructions/heterodox.json) | no |

### Not recovered (70)

[absorption-prone](../../../traits/instructions/absorption_prone.json), [accountable](../../../traits/instructions/accountable.json), [anti-immigration](../../../traits/instructions/anti_immigration.json), [anxious-preoccupied attachment](../../../traits/instructions/anxious_preoccupied_attachment.json), [apathetic](../../../traits/instructions/apathetic.json), [attention-seeking](../../../traits/instructions/attention_seeking.json), [benevolent](../../../traits/instructions/benevolent.json), [benign](../../../traits/instructions/benign.json), [calculating](../../../traits/instructions/calculating.json), [callous](../../../traits/instructions/callous.json), [Cancer](../../../traits/instructions/cancer.json), [cat-person](../../../traits/instructions/cat_person.json), [cerebral](../../../traits/instructions/cerebral.json), [compassionate](../../../traits/instructions/compassionate.json), [conciliatory](../../../traits/instructions/conciliatory.json), [confabulatory](../../../traits/instructions/confabulatory.json), [controlling](../../../traits/instructions/controlling.json), [course-correcting](../../../traits/instructions/course_correcting.json), [cryptic](../../../traits/instructions/cryptic.json), [dismissive](../../../traits/instructions/dismissive.json), [dog-person](../../../traits/instructions/dog_person.json), [effusive](../../../traits/instructions/effusive.json), [engaged](../../../traits/instructions/engaged.json), [exclusivist](../../../traits/instructions/exclusivist.json), [financially precarious](../../../traits/instructions/financially_precarious.json), [financially secure](../../../traits/instructions/financially_secure.json), [formalist](../../../traits/instructions/formalist.json), [formulaic](../../../traits/instructions/formulaic.json), [friendly](../../../traits/instructions/friendly.json), [Gryffindor](../../../traits/instructions/gryffindor.json), [iconoclastic](../../../traits/instructions/iconoclastic.json), [idealistic](../../../traits/instructions/idealistic.json), [insecure](../../../traits/instructions/insecure.json), [ISFJ (MBTI)](../../../traits/instructions/isfj_mbti.json), [ISTJ (MBTI)](../../../traits/instructions/istj_mbti.json), [malicious](../../../traits/instructions/malicious.json), [malign](../../../traits/instructions/malign.json), [merciful](../../../traits/instructions/merciful.json), [micromanaging](../../../traits/instructions/micromanaging.json), [monochronic (Hall)](../../../traits/instructions/monochronic_hall.json), [northern hemisphere](../../../traits/instructions/northern_hemisphere.json), [permissive](../../../traits/instructions/permissive.json), [pluralist](../../../traits/instructions/pluralist.json), [polychronic (Hall)](../../../traits/instructions/polychronic_hall.json), [pragmatic](../../../traits/instructions/pragmatic.json), [pro-immigration](../../../traits/instructions/pro_immigration.json), [puritanical](../../../traits/instructions/puritanical.json), [quality time](../../../traits/instructions/quality_time.json), [realistic (Holland)](../../../traits/instructions/realistic_holland.json), [sassy](../../../traits/instructions/sassy.json), [sectarian](../../../traits/instructions/sectarian.json), [self-assured](../../../traits/instructions/self_assured.json), [self-blaming](../../../traits/instructions/self_blaming.json), [self-effacing](../../../traits/instructions/self_effacing.json), [social (Holland)](../../../traits/instructions/social_holland.json), [southern hemisphere](../../../traits/instructions/southern_hemisphere.json), [spontaneous](../../../traits/instructions/spontaneous.json), [superstitious](../../../traits/instructions/superstitious.json), [supportive](../../../traits/instructions/supportive.json), [survivor (VALS)](../../../traits/instructions/survivor_vals.json), [temperate](../../../traits/instructions/temperate.json), [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json), [uncalculating](../../../traits/instructions/uncalculating.json), [uncaring](../../../traits/instructions/uncaring.json), [unfashionable](../../../traits/instructions/unfashionable.json), [unflinching](../../../traits/instructions/unflinching.json), [visceral](../../../traits/instructions/visceral.json), [wide-eyed](../../../traits/instructions/wide_eyed.json), [wry](../../../traits/instructions/wry.json), [zealous](../../../traits/instructions/zealous.json)

