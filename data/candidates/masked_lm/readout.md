# Masked-LM generator: pilot A (CPU, sandbox)

Plan: [coding_plan_04_masked_lm.md](../../../reports/trait_gap_generation/coding_plan_04_masked_lm.md).  Terms: [glossary](../../../reports/trait_gap_generation/glossary.md).  Models: roberta; passes: probe:roberta, single:roberta.  A **masked LM** ([masked LM, fill-mask](../../../reports/trait_gap_generation/glossary.md#masked-lm)) fills a `[MASK]` slot in a sentence; the frames are person-describing sentences, and every word's rank in every frame instance is kept.  [Recall@k](../../../reports/trait_gap_generation/glossary.md#recall-at-k) is the share of our labels among the first k words.

## Throughput

PLL mode: the [pseudo-log-likelihood](../../../reports/trait_gap_generation/glossary.md#pseudo-log-likelihood) each pass scored with (QUESTIONS 90: `l2r` left to right, `original` the plan's form).

| pass | device | PLL mode | seconds | forward passes | per second | instances/min | words/min |
|---|---|---|---|---|---|---|---|
| single:roberta | cpu | l2r | 5.52 | 700 | 126.9 | 1087.5 | n/a |
| probe:roberta | cpu | l2r | 0.9 | 161 | 179.8 | 1541.1 | n/a |

## The top 50 of three frames

`disp_nature` ({S} {be} [MASK] by nature.): driven, competitive, independent, curious, shy, intelligent, sensitive, creative, strong, simple, beautiful, aggressive, determined, unpredictable, unique, good, human, inspired, motivated, controlled, different, emotional, quiet, ambitious, clumsy, calm, gentle, smart, sarcastic, peaceful, cautious, playful, generous, optimistic, powerful, stubborn, passive, timid, romantic, conservative, mysterious, impatient, lazy, bored, guarded, not, adventurous, intuitive, organized, weak

`disp_habitually` ({S}{be_c} habitually [MASK].): late, wrong, rude, lazy, optimistic, busy, correct, angry, unhappy, happy, bad, right, aggressive, impatient, absent, quiet, polite, dishonest, curious, disappointed, unreliable, cautious, drunk, good, negative, confused, hungry, messy, distracted, pessimistic, incorrect, cheerful, unpredictable, frustrated, lying, poor, nervous, upset, honest, clumsy, silent, funny, depressed, awful, helpful, cruel, stupid, upbeat, noisy, stubborn

`noun_avowed` ({S} {be} an avowed [MASK].): atheist, conservative, christian, feminist, communist, socialist, liberal, catholic, republican, libertarian, muslim, marxist, democrat, anarchist, buddhist, nazi, racist, vegan, leftist, vegetarian, zionist, homosexual, nationalist, patriot, pagan, liar, lesbian, progressive, fascist, jew, mormon, hindu, believer, protestant, fan, evangelical, game, capitalist, islamist, extremist, terrorist, activist, ally, tory, supporter, rebel, sikh, sexist, separatist, nerd

## Recovery against the wordfreq baseline

Our labels as found among the first k words of each ranking.  **union** is the table's union rank; each `pass:model` is one pass alone; **baseline_wordfreq** ranks Variant B's universe (OEWN adjectives and person nouns) by word frequency alone: the frames earn their keep only by beating it.  Label classes are the primary tokenizer's (single piece, split word, multiword).

### Corpus labels

| ranking | labels | n | recall@1,000 | recall@2,000 | recall@5,000 | recall@10,000 | recall@20,000 | anywhere |
|---|---|---|---|---|---|---|---|---|
| union | all | 910 | 23.7% | 32.3% | 37.6% | 39.2% | 39.2% | 39.2% |
| union | single | 355 | 60.9% | 82.8% | 96.1% | 99.7% | 99.7% | 99.7% |
| union | subword | 333 | 0.0% | 0.0% | 0.3% | 0.9% | 0.9% | 0.9% |
| union | multiword | 222 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| probe:roberta | all | 910 | 19.2% | 27.7% | 36.7% | 38.0% | 38.0% | 38.0% |
| probe:roberta | single | 355 | 49.3% | 71.0% | 93.8% | 97.2% | 97.2% | 97.2% |
| probe:roberta | subword | 333 | 0.0% | 0.0% | 0.3% | 0.3% | 0.3% | 0.3% |
| probe:roberta | multiword | 222 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| single:roberta | all | 910 | 23.7% | 32.3% | 37.6% | 39.2% | 39.2% | 39.2% |
| single:roberta | single | 355 | 60.9% | 82.8% | 96.1% | 99.7% | 99.7% | 99.7% |
| single:roberta | subword | 333 | 0.0% | 0.0% | 0.3% | 0.9% | 0.9% | 0.9% |
| single:roberta | multiword | 222 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| baseline_wordfreq | all | 910 | 2.5% | 5.9% | 18.9% | 43.2% | 69.0% | 71.0% |
| baseline_wordfreq | single | 355 | 5.1% | 13.0% | 43.7% | 93.2% | 97.2% | 97.2% |
| baseline_wordfreq | subword | 333 | 0.0% | 0.0% | 0.0% | 7.8% | 71.8% | 77.2% |
| baseline_wordfreq | multiword | 222 | 2.2% | 3.6% | 7.7% | 16.2% | 19.8% | 19.8% |

### Seed-queue labels

| ranking | labels | n | recall@1,000 | recall@2,000 | recall@5,000 | recall@10,000 | recall@20,000 | anywhere |
|---|---|---|---|---|---|---|---|---|
| union | all | 780 | 17.1% | 24.7% | 30.9% | 34.4% | 34.4% | 34.4% |
| union | single | 258 | 51.5% | 74.8% | 92.2% | 99.2% | 99.2% | 99.2% |
| union | subword | 296 | 0.0% | 0.0% | 1.0% | 4.0% | 4.0% | 4.0% |
| union | multiword | 226 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| probe:roberta | all | 780 | 13.5% | 21.0% | 29.9% | 31.9% | 31.9% | 31.9% |
| probe:roberta | single | 258 | 40.7% | 62.8% | 88.4% | 94.2% | 94.2% | 94.2% |
| probe:roberta | subword | 296 | 0.0% | 0.7% | 1.7% | 2.0% | 2.0% | 2.0% |
| probe:roberta | multiword | 226 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| single:roberta | all | 780 | 17.1% | 24.7% | 30.9% | 34.4% | 34.4% | 34.4% |
| single:roberta | single | 258 | 51.5% | 74.8% | 92.2% | 99.2% | 99.2% | 99.2% |
| single:roberta | subword | 296 | 0.0% | 0.0% | 1.0% | 4.0% | 4.0% | 4.0% |
| single:roberta | multiword | 226 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| baseline_wordfreq | all | 780 | 2.9% | 6.4% | 16.8% | 36.1% | 57.2% | 59.1% |
| baseline_wordfreq | single | 258 | 7.0% | 15.9% | 44.2% | 89.1% | 92.2% | 92.2% |
| baseline_wordfreq | subword | 296 | 0.0% | 0.0% | 0.0% | 5.7% | 56.1% | 61.2% |
| baseline_wordfreq | multiword | 226 | 2.2% | 4.0% | 7.5% | 15.5% | 18.6% | 18.6% |

## The trait-hood contrast score

Dispositional frames minus the larger of the state and physical frames, by [pseudo-log-likelihood](../../../reports/trait_gap_generation/glossary.md#pseudo-log-likelihood).  [AUC](../../../reports/trait_gap_generation/glossary.md#auc) on 100 corpus traits against 100 states and physical words: **0.9657** (target 0.85, report and decide).

## Tokenizer census

| model | labels | n | single | subword | multiword |
|---|---|---|---|---|---|
| roberta | corpus | 910 | 355 (39.0%) | 333 (36.6%) | 222 (24.4%) |
| bert_wwm | corpus | 910 | 264 (29.0%) | 424 (46.6%) | 222 (24.4%) |
| modernbert | corpus | 910 | 298 (32.8%) | 390 (42.9%) | 222 (24.4%) |

## What Variant B's universe lacks

Of 910 bare corpus labels, **264** (29.0%) are not in the OEWN-derived list (29,497 words) at all, so Variant B can never recover them: 86 of 688 one-word labels and 178 of 222 multiword ones.  These are the start of the supplement list (Roger, 2026-10-10).

One-word labels absent: [ADHD](../../traits/instructions/adhd.json), [Aquarius](../../traits/instructions/aquarius.json), [Aries](../../traits/instructions/aries.json), [Cancer](../../traits/instructions/cancer.json), [Capricorn](../../traits/instructions/capricorn.json), ENFJ, ENFP, ENTJ, ENTP, ESFJ, ESFP, ESTJ, ESTP, Gemeinschaft, [Gemini](../../traits/instructions/gemini.json), Gesellschaft, [Gryffindor](../../traits/instructions/gryffindor.json), [Hufflepuff](../../traits/instructions/hufflepuff.json), INFJ, INFP, INTJ, INTP, ISFJ, ISFP, ISTJ, ISTP, [Leo](../../traits/instructions/leo.json), [Libra](../../traits/instructions/libra.json), [Neopagan](../../traits/instructions/neopagan.json), [OCD](../../traits/instructions/ocd.json), [Pisces](../../traits/instructions/pisces.json), [Ravenclaw](../../traits/instructions/ravenclaw.json), [Sagittarius](../../traits/instructions/sagittarius.json), [Scorpio](../../traits/instructions/scorpio.json), [Slytherin](../../traits/instructions/slytherin.json), [Taurus](../../traits/instructions/taurus.json), [Virgo](../../traits/instructions/virgo.json), [ageist](../../traits/instructions/ageist.json), [aggrieved](../../traits/instructions/aggrieved.json), [amoral](../../traits/instructions/amoral.json), [antitheist](../../traits/instructions/antitheist.json), [avoidant](../../traits/instructions/avoidant.json), [civilizationist](../../traits/instructions/civilizationist.json), [confabulatory](../../traits/instructions/confabulatory.json), conscientiousness, [consequentialist](../../traits/instructions/consequentialist.json), [deontological](../../traits/instructions/deontological.json), [distractible](../../traits/instructions/distractible.json), dominance, [ecocentric](../../traits/instructions/ecocentric.json), [essentialist](../../traits/instructions/essentialist.json), [exclusionary](../../traits/instructions/exclusionary.json), [exclusivist](../../traits/instructions/exclusivist.json), experiencer, [flirty](../../traits/instructions/flirty.json), [formalist](../../traits/instructions/formalist.json), [grounded](../../traits/instructions/grounded.json), [improvisational](../../traits/instructions/improvisational.json), [incrementalist](../../traits/instructions/incrementalist.json), influence, [languishing](../../traits/instructions/languishing.json), [micromanaging](../../traits/instructions/micromanaging.json), monochronic, [nonbinary](../../traits/instructions/nonbinary.json), [nurturing](../../traits/instructions/nurturing.json), [performative](../../traits/instructions/performative.json), [polyamorous](../../traits/instructions/polyamorous.json), polychronic, postconventional, preconventional, [procrastinating](../../traits/instructions/procrastinating.json), [regionalist](../../traits/instructions/regionalist.json), [relativist](../../traits/instructions/relativist.json), [satisficing](../../traits/instructions/satisficing.json), steadiness, [stigmatized](../../traits/instructions/stigmatized.json), [structuralist](../../traits/instructions/structuralist.json), survival, [technocratic](../../traits/instructions/technocratic.json), [technomystical](../../traits/instructions/technomystical.json), [transactional](../../traits/instructions/transactional.json), [transformational](../../traits/instructions/transformational.json), [traumatized](../../traits/instructions/traumatized.json), [uncalculating](../../traits/instructions/uncalculating.json), [unchallenging](../../traits/instructions/unchallenging.json), [unplugged](../../traits/instructions/unplugged.json)

Multiword labels absent: [East Asian](../../traits/instructions/east_asian.json), [Enneagram 1](../../traits/instructions/enneagram_1.json), [Enneagram 2](../../traits/instructions/enneagram_2.json), [Enneagram 3](../../traits/instructions/enneagram_3.json), [Enneagram 4](../../traits/instructions/enneagram_4.json), [Enneagram 5](../../traits/instructions/enneagram_5.json), [Enneagram 6](../../traits/instructions/enneagram_6.json), [Enneagram 7](../../traits/instructions/enneagram_7.json), [Enneagram 8](../../traits/instructions/enneagram_8.json), [Enneagram 9](../../traits/instructions/enneagram_9.json), [Indigenous American](../../traits/instructions/indigenous_american.json), [Indigenous Australian](../../traits/instructions/indigenous_australian.json), [New Age](../../traits/instructions/new_age.json), [Pacific Islander](../../traits/instructions/pacific_islander.json), [South Asian](../../traits/instructions/south_asian.json), [Southeast Asian](../../traits/instructions/southeast_asian.json), [absorption-prone](../../traits/instructions/absorption_prone.json), [acts of service](../../traits/instructions/acts_of_service.json), [adventurous-eater](../../traits/instructions/adventurous_eater.json), [ambiguity-tolerant](../../traits/instructions/ambiguity_tolerant.json), [anti-immigration](../../traits/instructions/anti_immigration.json), [anxious-preoccupied attachment](../../traits/instructions/anxious_preoccupied_attachment.json), [attention-seeking](../../traits/instructions/attention_seeking.json), [autonomy-respecting](../../traits/instructions/autonomy_respecting.json), [big-picture](../../traits/instructions/big_picture.json), [blame-shifting](../../traits/instructions/blame_shifting.json), [blood type A](../../traits/instructions/blood_type_a.json), [blood type AB](../../traits/instructions/blood_type_ab.json), [blood type B](../../traits/instructions/blood_type_b.json), [blood type O](../../traits/instructions/blood_type_o.json), [body-confident](../../traits/instructions/body_confident.json), [body-insecure](../../traits/instructions/body_insecure.json), [body-obsessed](../../traits/instructions/body_obsessed.json), [borderline personality disorder](../../traits/instructions/borderline_personality_disorder.json), [brand-agnostic](../../traits/instructions/brand_agnostic.json), [brand-loyal](../../traits/instructions/brand_loyal.json), [brown-eyed](../../traits/instructions/brown_eyed.json), [career-oriented](../../traits/instructions/career_oriented.json), [cat-person](../../traits/instructions/cat_person.json), [chronically-ill](../../traits/instructions/chronically_ill.json), [closure-seeking](../../traits/instructions/closure_seeking.json), [company-loyal](../../traits/instructions/company_loyal.json), [conspiracy-minded](../../traits/instructions/conspiracy_minded.json), [course-correcting](../../traits/instructions/course_correcting.json), [data-driven](../../traits/instructions/data_driven.json), [death-accepting](../../traits/instructions/death_accepting.json), [death-fearing](../../traits/instructions/death_fearing.json), [detail-oriented](../../traits/instructions/detail_oriented.json), [dignity culture](../../traits/instructions/dignity_culture.json), [dismissive-avoidant attachment](../../traits/instructions/dismissive_avoidant_attachment.json), [dog-person](../../traits/instructions/dog_person.json), [early-adopter](../../traits/instructions/early_adopter.json), [eastern hemisphere](../../traits/instructions/eastern_hemisphere.json), [emotionally-articulate](../../traits/instructions/emotionally_articulate.json), [emotionally-disengaged](../../traits/instructions/emotionally_disengaged.json), [emotionally-engaged](../../traits/instructions/emotionally_engaged.json), [emotionally-inarticulate](../../traits/instructions/emotionally_inarticulate.json), emotionally-stable, [ends justify means](../../traits/instructions/ends_justify_means.json), [external locus of control](../../traits/instructions/external_locus_of_control.json), [extrinsically motivated](../../traits/instructions/extrinsically_motivated.json), [face culture](../../traits/instructions/face_culture.json), [fair-skinned](../../traits/instructions/fair_skinned.json), [family-oriented](../../traits/instructions/family_oriented.json), [fearful-avoidant attachment](../../traits/instructions/fearful_avoidant_attachment.json), [financially conservative](../../traits/instructions/financially_conservative.json), [financially precarious](../../traits/instructions/financially_precarious.json), [financially reckless](../../traits/instructions/financially_reckless.json), [financially secure](../../traits/instructions/financially_secure.json), [fixed-minded](../../traits/instructions/fixed_minded.json), [foot-dragging](../../traits/instructions/foot_dragging.json), [frequent poster](../../traits/instructions/frequent_poster.json), [full-price shopper](../../traits/instructions/full_price_shopper.json), [future-oriented](../../traits/instructions/future_oriented.json), [gain-seeking](../../traits/instructions/gain_seeking.json), [gay-affirming](../../traits/instructions/gay_affirming.json), [gen-x](../../traits/instructions/gen_x.json), [gen-z](../../traits/instructions/gen_z.json), [good even when unwatched](../../traits/instructions/good_even_when_unwatched.json), [good only when watched](../../traits/instructions/good_only_when_watched.json), [gray-eyed](../../traits/instructions/gray_eyed.json), [growth-first](../../traits/instructions/growth_first.json), [growth-minded](../../traits/instructions/growth_minded.json), [guilt-prone](../../traits/instructions/guilt_prone.json), [gun owner](../../traits/instructions/gun_owner.json), [happily-partnered](../../traits/instructions/happily_partnered.json), [health-conscious](../../traits/instructions/health_conscious.json), [health-negligent](../../traits/instructions/health_negligent.json), [heavy-drinker](../../traits/instructions/heavy_drinker.json), high-context, [historically minded](../../traits/instructions/historically_minded.json), honest-humble, [honor culture](../../traits/instructions/honor_culture.json), [honorable while playing](../../traits/instructions/honorable_while_playing.json), [in chronic pain](../../traits/instructions/in_chronic_pain.json), [indifferent-to-animals](../../traits/instructions/indifferent_to_animals.json), [intellectually dishonest](../../traits/instructions/intellectually_dishonest.json), [intellectually honest](../../traits/instructions/intellectually_honest.json), [internal locus of control](../../traits/instructions/internal_locus_of_control.json), [intrinsically-motivated](../../traits/instructions/intrinsically_motivated.json), [job-hopping](../../traits/instructions/job_hopping.json), [just-world-believing](../../traits/instructions/just_world_believing.json), [kind-to-animals](../../traits/instructions/kind_to_animals.json), [late-adopter](../../traits/instructions/late_adopter.json), [learning-oriented](../../traits/instructions/learning_oriented.json), [long-term oriented](../../traits/instructions/long_term_oriented.json), [loss-averse](../../traits/instructions/loss_averse.json), low-context, [many siblings](../../traits/instructions/many_siblings.json), [media-skeptical](../../traits/instructions/media_skeptical.json), [media-trusting](../../traits/instructions/media_trusting.json), [metaphysical libertarian](../../traits/instructions/metaphysical_libertarian.json), [mobility impaired](../../traits/instructions/mobility_impaired.json), [moral relativist](../../traits/instructions/moral_relativist.json), [moral universalist](../../traits/instructions/moral_universalist.json), [motivated-reasoning-immune](../../traits/instructions/motivated_reasoning_immune.json), [motivated-reasoning-prone](../../traits/instructions/motivated_reasoning_prone.json), [new money](../../traits/instructions/new_money.json), [news-avoidant](../../traits/instructions/news_avoidant.json), [news-junkie](../../traits/instructions/news_junkie.json), [northern hemisphere](../../traits/instructions/northern_hemisphere.json), [old money](../../traits/instructions/old_money.json), [only child](../../traits/instructions/only_child.json), [other-focused](../../traits/instructions/other_focused.json), [passive-aggressive](../../traits/instructions/passive_aggressive.json), [performance-oriented](../../traits/instructions/performance_oriented.json), [physical touch](../../traits/instructions/physical_touch.json), [picky-eater](../../traits/instructions/picky_eater.json), [plain-looking](../../traits/instructions/plain_looking.json), [plain-spoken](../../traits/instructions/plain_spoken.json), [plugged-in](../../traits/instructions/plugged_in.json), [pro-immigration](../../traits/instructions/pro_immigration.json), [problem-solving](../../traits/instructions/problem_solving.json), [psychologically minded](../../traits/instructions/psychologically_minded.json), [punishment-fearing](../../traits/instructions/punishment_fearing.json), [quality time](../../traits/instructions/quality_time.json), read-write, [receiving gifts](../../traits/instructions/receiving_gifts.json), [red-headed](../../traits/instructions/red_headed.json), [risk-averse](../../traits/instructions/risk_averse.json), [risk-seeking](../../traits/instructions/risk_seeking.json), [rule-abiding](../../traits/instructions/rule_abiding.json), [rule-breaking](../../traits/instructions/rule_breaking.json), [ruthless while playing](../../traits/instructions/ruthless_while_playing.json), [science-skeptical](../../traits/instructions/science_skeptical.json), [science-trusting](../../traits/instructions/science_trusting.json), secular-rational, [secure attachment](../../traits/instructions/secure_attachment.json), [self-accepting](../../traits/instructions/self_accepting.json), [self-blaming](../../traits/instructions/self_blaming.json), [self-certain](../../traits/instructions/self_certain.json), [self-critical](../../traits/instructions/self_critical.json), self-expression, [self-harming](../../traits/instructions/self_harming.json), [self-pitying](../../traits/instructions/self_pitying.json), [self-reinventing](../../traits/instructions/self_reinventing.json), [self-starting](../../traits/instructions/self_starting.json), [self-uncertain](../../traits/instructions/self_uncertain.json), [shame-prone](../../traits/instructions/shame_prone.json), [short-term oriented](../../traits/instructions/short_term_oriented.json), [sleep-deprived](../../traits/instructions/sleep_deprived.json), [socially-obtuse](../../traits/instructions/socially_obtuse.json), [socially-perceptive](../../traits/instructions/socially_perceptive.json), [southern hemisphere](../../traits/instructions/southern_hemisphere.json), [status-seeking](../../traits/instructions/status_seeking.json), [stream-of-consciousness](../../traits/instructions/stream_of_consciousness.json), [strong-stomached](../../traits/instructions/strong_stomached.json), [systems-thinker](../../traits/instructions/systems_thinker.json), [techno-hierophantic](../../traits/instructions/techno_hierophantic.json), [trapped-in-job](../../traits/instructions/trapped_in_job.json), [tunnel-visioned](../../traits/instructions/tunnel_visioned.json), [unhappily-partnered](../../traits/instructions/unhappily_partnered.json), [vulnerable-narcissistic](../../traits/instructions/vulnerable_narcissistic.json), [western hemisphere](../../traits/instructions/western_hemisphere.json), [win-win-seeking](../../traits/instructions/win_win_seeking.json), [words of affirmation](../../traits/instructions/words_of_affirmation.json), [world-accepting](../../traits/instructions/world_accepting.json), [world-changing](../../traits/instructions/world_changing.json)

## Variant B against the beams on the multiword labels

| ranking | n | recall@1,000 | recall@2,000 | recall@5,000 | recall@10,000 | recall@20,000 | anywhere |
|---|---|---|---|---|---|---|---|
| baseline_wordfreq | 222 | 2.2% | 3.6% | 7.7% | 16.2% | 19.8% | 19.8% |

## Frame ablation (single-mask pass)

Recall of the one-word corpus labels with one subject, or one register, removed (a positive delta means the removed factor was costing recall).

**subject** (all: recall@1000 31.4%, recall@5000 49.7%)

| removed | recall@1000 delta | recall@5000 delta |
|---|---|---|
| assistant | +0.003 | +0.001 |
| character | +0.001 | +0.001 |
| chatbot | +0.000 | +0.000 |
| colleague | +0.000 | -0.002 |
| he | -0.002 | +0.000 |
| i | -0.003 | -0.002 |
| manager | -0.004 | +0.001 |
| she | +0.000 | +0.000 |
| they | +0.006 | +0.003 |
| you | +0.000 | +0.000 |

**register** (all: recall@1000 31.4%, recall@5000 49.7%)

| removed | recall@1000 delta | recall@5000 delta |
|---|---|---|
| casual_review | -0.019 | +0.003 |
| chat_transcript | +0.003 | +0.000 |
| novel | +0.000 | +0.000 |
| performance_review | -0.006 | +0.000 |
| psych_textbook | -0.013 | -0.003 |
| reference_letter | +0.006 | -0.009 |

## Files

- [mlm_table.jsonl](mlm_table.jsonl): the table
- [evaluation.json](evaluation.json): the evaluation (JSON)
- [recovery_curves.png](recovery_curves.png): the recovery curves
- [hhh_probe.md](hhh_probe.md): the HHH probe
- [roger_sample.md](roger_sample.md): the spot check
- [generation.json](generation.json): what generated the table
