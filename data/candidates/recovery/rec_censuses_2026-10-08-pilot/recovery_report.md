# Recovery test: `censuses/2026-10-08-pilot` (`rec_censuses_2026-10-08-pilot`)

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
| 0 | 83 of 790 | 280 | 22.9% (19) | 11 | 9.3% | 3 of 29 | 89.2% | 8 | 27.7% | $6.626 |

Total cost $6.626 (each seed's reduced-corpus M3 run and its match calls; [usage.json](./usage.json); every figure is in [recovery_report.json](./recovery_report.json)).

## Recall by region

| region | seed 0 |
|---|---|
| cognitive_epistemic | 3 of 17 (17.6%) |
| communication_style | 5 of 16 (31.2%) |
| emotional_temperament | 4 of 8 (50.0%) |
| identity_demographic | 0 of 6 (0.0%) |
| moral_stance | 5 of 14 (35.7%) |
| none | 1 of 17 (5.9%) |
| social_interpersonal | 1 of 5 (20.0%) |

## Recall by arrangement kind

| arrangement kind | seed 0 |
|---|---|
| 4-cube | 0 of 2 (0.0%) |
| pair | 11 of 56 (19.6%) |
| ring | 0 of 3 (0.0%) |
| sequence | 0 of 1 (0.0%) |
| set | 0 of 3 (0.0%) |
| singleton | 4 of 10 (40.0%) |
| square | 0 of 1 (0.0%) |
| triangle | 3 of 3 (100.0%) |
| unclassified | 1 of 4 (25.0%) |

## Seed 0

Hidden traits: [hidden.json](./seed0/hidden.json); the reduced-corpus M3 run: [decisions.md](../../novelty/rec_censuses_2026-10-08-pilot_s0/decisions.md) ({"covered": 220, "new": 280}); every pair judged: [matches.jsonl](./seed0/matches.jsonl).

### Recovered (19 of 83)

| hidden trait | region | kind | recovered by | how |
|---|---|---|---|---|
| [accountable](../../../traits/instructions/accountable.json) | moral_stance | singleton | accountable | label |
| [apathetic](../../../traits/instructions/apathetic.json) | emotional_temperament | pair | lukewarm | Sonnet 2, Opus 3 |
| [benign](../../../traits/instructions/benign.json) | moral_stance | pair | benign | label |
| [callous](../../../traits/instructions/callous.json) | emotional_temperament | triangle | compassionless | Sonnet 3, Opus 3 |
| [compassionate](../../../traits/instructions/compassionate.json) | emotional_temperament | triangle | consoling, soft-hearted | Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [competent](../../../traits/instructions/competent.json) | cognitive_epistemic | pair | excellent | Sonnet 2, Opus 3 |
| [effusive](../../../traits/instructions/effusive.json) | communication_style | unclassified | effusive | label |
| [friendly](../../../traits/instructions/friendly.json) | communication_style | pair | friendly, amicable, good-natured, hearty, lovable | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [hostile](../../../traits/instructions/hostile.json) | communication_style | pair | hostile, unfriendly | label; Sonnet 2, Opus 3 |
| [idealistic](../../../traits/instructions/idealistic.json) | moral_stance | pair | idealistic | label |
| [incompetent](../../../traits/instructions/incompetent.json) | cognitive_epistemic | pair | incapable | Sonnet 3, Opus 3 |
| [jaded](../../../traits/instructions/jaded.json) | emotional_temperament | pair | world weary | Sonnet 3, Opus 3 |
| [malicious](../../../traits/instructions/malicious.json) | moral_stance | triangle | malicious | label |
| [merciful](../../../traits/instructions/merciful.json) | moral_stance | singleton | merciful | label |
| [oblivious](../../../traits/instructions/oblivious.json) | social_interpersonal | pair | heedless, unobservant | Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [sassy](../../../traits/instructions/sassy.json) | communication_style | singleton | saucy | Sonnet 3, Opus 3 |
| [superstitious](../../../traits/instructions/superstitious.json) | cognitive_epistemic | singleton | superstitious | label |
| [uncalculating](../../../traits/instructions/uncalculating.json) | communication_style | pair | uncalculating | label |
| [unfashionable](../../../traits/instructions/unfashionable.json) |  | pair | unfashionable | label |

### False covers (8 candidates)

| candidate | matches hidden | how | covered by | hidden trait recovered anyway |
|---|---|---|---|---|
| aggressive | [hostile](../../../traits/instructions/hostile.json) | Sonnet 3, Opus 4 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| expressive | [effusive](../../../traits/instructions/effusive.json) | Sonnet 3, Opus 3 | [expressive](../../../traits/instructions/expressive.json) | yes |
| fervent | [zealous](../../../traits/instructions/zealous.json) | Sonnet 3, Opus 3 | [passionate](../../../traits/instructions/passionate.json) | no |
| humorous | [wry](../../../traits/instructions/wry.json) | Sonnet 2, Opus 3 | [witty](../../../traits/instructions/witty.json) | no |
| inexplicit | [cryptic](../../../traits/instructions/cryptic.json) | Sonnet 2, Opus 3 | [high-context (Hall)](../../../traits/instructions/high_context_hall.json) | no |
| intense | [zealous](../../../traits/instructions/zealous.json) | Sonnet 2, Opus 3 | [intense](../../../traits/instructions/intense.json) | no |
| moderate | [temperate](../../../traits/instructions/temperate.json) | Sonnet 2, Opus 3 | [moderate](../../../traits/instructions/moderate.json) | no |
| tenderminded | [compassionate](../../../traits/instructions/compassionate.json) | Sonnet 3, Opus 3 | [empathetic](../../../traits/instructions/empathetic.json) | yes |

### Not recovered (64)

[absorption-prone](../../../traits/instructions/absorption_prone.json), [anti-immigration](../../../traits/instructions/anti_immigration.json), [anxious-preoccupied attachment](../../../traits/instructions/anxious_preoccupied_attachment.json), [attention-seeking](../../../traits/instructions/attention_seeking.json), [bargain-hunter](../../../traits/instructions/bargain_hunter.json), [benevolent](../../../traits/instructions/benevolent.json), [calculating](../../../traits/instructions/calculating.json), [Cancer](../../../traits/instructions/cancer.json), [cat-person](../../../traits/instructions/cat_person.json), [cerebral](../../../traits/instructions/cerebral.json), [clear](../../../traits/instructions/clear.json), [conciliatory](../../../traits/instructions/conciliatory.json), [confabulatory](../../../traits/instructions/confabulatory.json), [confrontational](../../../traits/instructions/confrontational.json), [controlling](../../../traits/instructions/controlling.json), [course-correcting](../../../traits/instructions/course_correcting.json), [cryptic](../../../traits/instructions/cryptic.json), [dismissive](../../../traits/instructions/dismissive.json), [dog-person](../../../traits/instructions/dog_person.json), [educated](../../../traits/instructions/educated.json), [engaged](../../../traits/instructions/engaged.json), [exclusivist](../../../traits/instructions/exclusivist.json), [fashionable](../../../traits/instructions/fashionable.json), [financially precarious](../../../traits/instructions/financially_precarious.json), [financially secure](../../../traits/instructions/financially_secure.json), [formalist](../../../traits/instructions/formalist.json), [formulaic](../../../traits/instructions/formulaic.json), [full-price shopper](../../../traits/instructions/full_price_shopper.json), [Gryffindor](../../../traits/instructions/gryffindor.json), [iconoclastic](../../../traits/instructions/iconoclastic.json), [insecure](../../../traits/instructions/insecure.json), [ISFJ (MBTI)](../../../traits/instructions/isfj_mbti.json), [ISTJ (MBTI)](../../../traits/instructions/istj_mbti.json), [malign](../../../traits/instructions/malign.json), [micromanaging](../../../traits/instructions/micromanaging.json), [monochronic (Hall)](../../../traits/instructions/monochronic_hall.json), [northern hemisphere](../../../traits/instructions/northern_hemisphere.json), [observant](../../../traits/instructions/observant.json), [permissive](../../../traits/instructions/permissive.json), [pluralist](../../../traits/instructions/pluralist.json), [polychronic (Hall)](../../../traits/instructions/polychronic_hall.json), [pragmatic](../../../traits/instructions/pragmatic.json), [pro-immigration](../../../traits/instructions/pro_immigration.json), [puritanical](../../../traits/instructions/puritanical.json), [quality time](../../../traits/instructions/quality_time.json), [realistic (Holland)](../../../traits/instructions/realistic_holland.json), [sectarian](../../../traits/instructions/sectarian.json), [self-assured](../../../traits/instructions/self_assured.json), [self-blaming](../../../traits/instructions/self_blaming.json), [self-effacing](../../../traits/instructions/self_effacing.json), [social (Holland)](../../../traits/instructions/social_holland.json), [southern hemisphere](../../../traits/instructions/southern_hemisphere.json), [spontaneous](../../../traits/instructions/spontaneous.json), [supportive](../../../traits/instructions/supportive.json), [survivor (VALS)](../../../traits/instructions/survivor_vals.json), [temperate](../../../traits/instructions/temperate.json), [tunnel-visioned](../../../traits/instructions/tunnel_visioned.json), [uncaring](../../../traits/instructions/uncaring.json), [uneducated](../../../traits/instructions/uneducated.json), [unflinching](../../../traits/instructions/unflinching.json), [visceral](../../../traits/instructions/visceral.json), [wide-eyed](../../../traits/instructions/wide_eyed.json), [wry](../../../traits/instructions/wry.json), [zealous](../../../traits/instructions/zealous.json)

