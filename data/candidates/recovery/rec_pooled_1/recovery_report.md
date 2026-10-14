# Recovery test: `pooled/every generator` (`rec_pooled_1`)

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
| 0 | 96 of 932 | 4539 | 61.5% (59) | 28 | 5.0% | 21 of 32 | 100.0% | 166 | 71.9% | $27.173 |
| 1 | 95 of 932 | 4548 | 64.2% (61) | 41 | 5.5% | 19 of 32 | 100.0% | 196 | 71.6% | $31.604 |
| mean | 95.5 | | 62.8% | 34.5 | 5.2% | 20 of 32 | 100.0% | 181 | 71.7% | $29.389 |

Total cost $58.777 (each seed's reduced-corpus M3 run and its match calls; [usage.json](./usage.json); every figure is in [recovery_report.json](./recovery_report.json)).

## By generator (pooled)

Every generator's rows were scored once against the same reduced corpus; a generator's figures are read from the rows it proposed (a states-pass row counts for its source row's generator), so they equal a separate run on the same draw.  The first table above is the union, "any generator".  Recall intervals are Wilson 95% intervals over the hidden traits of the seed.

| generator | kept | recall, seed 0 (95% interval) | recall, seed 1 (95% interval) | mean recall | mean precision | false-cover candidates (mean) |
|---|---|---|---|---|---|---|
| alignment_sweep | 636.5 | 6 of 96 (6.2%; 2.9%-13.0%) | 5 of 95 (5.3%; 2.3%-11.7%) | 5.8% | 0.9% | 5.5 |
| antonym_check | 151.5 | 12 of 96 (12.5%; 7.3%-20.6%) | 13 of 95 (13.7%; 8.2%-22.0%) | 13.1% | 9.6% | 17.5 |
| base_model | 556.5 | 27 of 96 (28.1%; 20.1%-37.8%) | 40 of 95 (42.1%; 32.7%-52.1%) | 35.1% | 11.0% | 50.5 |
| censuses | 3042.5 | 44 of 96 (45.8%; 36.2%-55.8%) | 51 of 95 (53.7%; 43.7%-63.4%) | 49.8% | 5.6% | 131.5 |
| ipip | 433.5 | 24 of 96 (25.0%; 17.4%-34.5%) | 17 of 95 (17.9%; 11.5%-26.8%) | 21.4% | 7.1% | 30.5 |
| masked_lm | 170.5 | 7 of 96 (7.3%; 3.6%-14.3%) | 9 of 95 (9.5%; 5.1%-17.0%) | 8.4% | 9.7% | 9 |
| roget | 253 | 12 of 96 (12.5%; 7.3%-20.6%) | 7 of 95 (7.4%; 3.6%-14.4%) | 9.9% | 4.5% | 4.5 |
| structural | 169 | 17 of 96 (17.7%; 11.4%-26.5%) | 16 of 95 (16.8%; 10.6%-25.6%) | 17.3% | 11.8% | 26 |
| wn_clusters | 281 | 11 of 96 (11.5%; 6.5%-19.4%) | 11 of 95 (11.6%; 6.6%-19.6%) | 11.5% | 8.2% | 19 |

## By run (pooled)

| generator/run | kept | recall, seed 0 (95% interval) | recall, seed 1 (95% interval) | mean recall | mean precision | false-cover candidates (mean) |
|---|---|---|---|---|---|---|
| alignment_sweep/2026-10-10-full | 276.5 | 4 of 96 (4.2%; 1.6%-10.2%) | 4 of 95 (4.2%; 1.7%-10.3%) | 4.2% | 1.6% | 3 |
| alignment_sweep/2026-10-11-b | 54.5 | 0 of 96 (0.0%; 0.0%-3.9%) | 0 of 95 (0.0%; 0.0%-3.9%) | 0.0% | 0.0% | 0 |
| alignment_sweep/2026-10-11-papers | 320 | 3 of 96 (3.1%; 1.1%-8.8%) | 2 of 95 (2.1%; 0.6%-7.3%) | 2.6% | 0.8% | 2.5 |
| alignment_sweep/2026-10-11-usage | 3.5 | 0 of 96 (0.0%; 0.0%-3.9%) | 1 of 95 (1.1%; 0.2%-5.7%) | 0.5% | 12.5% | 0 |
| antonym_check/pilot_1 | 151.5 | 12 of 96 (12.5%; 7.3%-20.6%) | 13 of 95 (13.7%; 8.2%-22.0%) | 13.1% | 9.6% | 17.5 |
| base_model/2026-10-12-pilot | 130.5 | 15 of 96 (15.6%; 9.7%-24.2%) | 19 of 95 (20.0%; 13.2%-29.1%) | 17.8% | 16.8% | 20.5 |
| base_model/2026-10-12-pilot-mc2 | 556.5 | 27 of 96 (28.1%; 20.1%-37.8%) | 40 of 95 (42.1%; 32.7%-52.1%) | 35.1% | 11.0% | 50.5 |
| censuses/2026-10-08-pilot | 245.5 | 15 of 96 (15.6%; 9.7%-24.2%) | 21 of 95 (22.1%; 14.9%-31.4%) | 18.9% | 9.3% | 23 |
| censuses/2026-10-09-iv-pilot | 64.5 | 3 of 96 (3.1%; 1.1%-8.8%) | 0 of 95 (0.0%; 0.0%-3.9%) | 1.6% | 2.3% | 0.5 |
| censuses/2026-10-09-rare-pilot | 44.5 | 1 of 96 (1.0%; 0.2%-5.7%) | 2 of 95 (2.1%; 0.6%-7.3%) | 1.6% | 3.4% | 0.5 |
| censuses/2026-10-10-tda | 1155 | 38 of 96 (39.6%; 30.4%-49.6%) | 42 of 95 (44.2%; 34.6%-54.2%) | 41.9% | 9.1% | 96 |
| censuses/2026-10-11-allport_hi | 1382.5 | 22 of 96 (22.9%; 15.7%-32.3%) | 27 of 95 (28.4%; 20.3%-38.2%) | 25.7% | 4.3% | 29 |
| censuses/2026-10-12-allport_iv_rare | 61 | 3 of 96 (3.1%; 1.1%-8.8%) | 1 of 95 (1.1%; 0.2%-5.7%) | 2.1% | 3.2% | 1.5 |
| censuses/2026-10-12-allport_rare | 441 | 10 of 96 (10.4%; 5.8%-18.1%) | 9 of 95 (9.5%; 5.1%-17.0%) | 10.0% | 3.3% | 12 |
| ipip/2026-10-11-g600 | 112 | 14 of 96 (14.6%; 8.9%-23.0%) | 3 of 95 (3.2%; 1.1%-8.9%) | 8.9% | 7.7% | 8.5 |
| ipip/2026-10-13-g600 | 254.5 | 20 of 96 (20.8%; 13.9%-30.0%) | 12 of 95 (12.6%; 7.4%-20.8%) | 16.7% | 7.8% | 20 |
| ipip/2026-10-14-g600-hinted | 259 | 16 of 96 (16.7%; 10.5%-25.4%) | 15 of 95 (15.8%; 9.8%-24.4%) | 16.2% | 6.8% | 21.5 |
| masked_lm/2026-10-14-pilot | 170.5 | 7 of 96 (7.3%; 3.6%-14.3%) | 9 of 95 (9.5%; 5.1%-17.0%) | 8.4% | 9.7% | 9 |
| roget/2026-10-08-pilot | 72.5 | 4 of 96 (4.2%; 1.6%-10.2%) | 2 of 95 (2.1%; 0.6%-7.3%) | 3.1% | 4.8% | 1.5 |
| roget/2026-10-11-full | 207 | 9 of 96 (9.4%; 5.0%-16.9%) | 6 of 95 (6.3%; 2.9%-13.1%) | 7.8% | 4.1% | 3.5 |
| roget/2026-10-12-rule1b | 8 | 0 of 96 (0.0%; 0.0%-3.9%) | 0 of 95 (0.0%; 0.0%-3.9%) | 0.0% | 0.0% | 0 |
| structural/2026-10-14-pilot | 169 | 17 of 96 (17.7%; 11.4%-26.5%) | 16 of 95 (16.8%; 10.6%-25.6%) | 17.3% | 11.8% | 26 |
| wn_clusters/2026-10-08-pilot | 38 | 2 of 96 (2.1%; 0.6%-7.3%) | 2 of 95 (2.1%; 0.6%-7.3%) | 2.1% | 5.3% | 3 |
| wn_clusters/2026-10-11-full | 205 | 9 of 96 (9.4%; 5.0%-16.9%) | 7 of 95 (7.4%; 3.6%-14.4%) | 8.4% | 6.8% | 14 |
| wn_clusters/2026-10-12-rule1b | 76.5 | 3 of 96 (3.1%; 1.1%-8.8%) | 8 of 95 (8.4%; 4.3%-15.8%) | 5.8% | 11.5% | 5 |

## Rows scored again and rows copied (affected only)

| seed | rows | scored again | copied | share scored | reasons (a row may have several) |
|---|---|---|---|---|---|
| 0 | 7586 | 4828 | 2758 | 63.6% | {"exact_label": 42, "label": 45, "m3_near": 4168, "match_near": 4429, "recorded": 4018, "retrieval": 387} |
| 1 | 7586 | 5303 | 2283 | 69.9% | {"exact_label": 56, "label": 59, "m3_near": 4779, "match_near": 5028, "recorded": 4605, "retrieval": 262} |

## Recall by region

| region | seed 0 | seed 1 |
|---|---|---|
| alignment_ai_agent | 2 of 2 (100.0%) | 1 of 1 (100.0%) |
| cognitive_epistemic | 12 of 19 (63.2%) | 15 of 19 (79.0%) |
| communication_style | 8 of 10 (80.0%) | 9 of 11 (81.8%) |
| emotional_temperament | 11 of 17 (64.7%) | 9 of 16 (56.2%) |
| identity_demographic | 9 of 17 (52.9%) | 5 of 17 (29.4%) |
| moral_stance | 8 of 15 (53.3%) | 10 of 15 (66.7%) |
| social_interpersonal | 9 of 16 (56.2%) | 12 of 16 (75.0%) |

## Recall by arrangement kind

| arrangement kind | seed 0 | seed 1 |
|---|---|---|
| 4-cube | 0 of 4 (0.0%) | 0 of 1 (0.0%) |
| map | 1 of 2 (50.0%) | 0 of 1 (0.0%) |
| pair | 51 of 62 (82.3%) | 48 of 64 (75.0%) |
| ring | 0 of 5 (0.0%) | 0 of 5 (0.0%) |
| set | 0 of 8 (0.0%) | 1 of 4 (25.0%) |
| singleton | 5 of 9 (55.6%) | 9 of 12 (75.0%) |
| square | 1 of 2 (50.0%) | 1 of 4 (25.0%) |
| triangle | 0 of 3 (0.0%) |  |
| unclassified | 1 of 1 (100.0%) | 2 of 4 (50.0%) |

## Seed 0

Hidden traits: [hidden.json](./seed0/hidden.json); the reduced-corpus M3 run: [decisions.md](../../novelty/rec_pooled_1_s0/decisions.md) ({"new": 4539, "covered": 3047}); every pair judged: [matches.jsonl](./seed0/matches.jsonl).

### Recovered (59 of 96)

| hidden trait | region | kind | recovered by | how |
|---|---|---|---|---|
| [aesthete](../../../traits/instructions/aesthete.json) | emotional_temperament | pair | aesthetically attuned, art-loving | Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [anxious-preoccupied attachment](../../../traits/instructions/anxious_preoccupied_attachment.json) | social_interpersonal | square | craves emotional closeness, insecure in relationships, seeks close intimacy | Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [athletic](../../../traits/instructions/athletic.json) | identity_demographic | pair | athletic, sporting, sporty | label; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [bold](../../../traits/instructions/bold.json) | cognitive_epistemic | pair | bold, audacious | label; Sonnet 2, Opus 3 |
| [capitalist](../../../traits/instructions/capitalist.json) | moral_stance | pair | capitalistic | Sonnet 3, Opus 4 |
| [cautious](../../../traits/instructions/cautious.json) | cognitive_epistemic | pair | cautious, financially cautious, overcareful, overcautious | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [cheerful](../../../traits/instructions/cheerful.json) | emotional_temperament | pair | cheerful, bouncy, bubbly, cheery, chipper, chirpy, ebullient, good-humored, infectious, irrepressible, jocund, jolly, jovial, lightful, overmerry, perky, sunny, undespondent, unmelancholy | label; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 4 |
| [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | cognitive_epistemic | pair | rarely fantasizes | Sonnet 2, Opus 3 |
| [conciliatory](../../../traits/instructions/conciliatory.json) | social_interpersonal | pair | keeps groups harmonious, make-peace, peacemaking, placatory | Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [confrontational](../../../traits/instructions/confrontational.json) | social_interpersonal | pair | confrontational, adversarial, agonistical, argumentative, clash, confronting, contentious, discordant, fighting-cock, polemic, quarrelsome | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [conventional](../../../traits/instructions/conventional.json) | cognitive_epistemic | pair | conventionalist, generic and predictable, normal, ready-made, standard, uncreative, unimaginative, uningenious, uninventive, unoriginal, unsurprising | Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [critical](../../../traits/instructions/critical.json) | cognitive_epistemic | pair | critical | label |
| [dominant](../../../traits/instructions/dominant.json) | social_interpersonal | pair | dominant, overpowering | label; Sonnet 3, Opus 3 |
| [early-bird](../../../traits/instructions/early_bird.json) | identity_demographic | pair | early riser, morning person | Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [eccentric](../../../traits/instructions/eccentric.json) | communication_style | pair | eccentric, abnormal, anomalous, atypical, bizarre, case, deviating, different, eccentric and unconventional, exceptions, far out, freakish, habitually eccentric, idiosyncratic, nutty, odd, off-beat, out-there, outlandish, peculiar, queer, quirky, rum, screwy, singular, strange, uncommon, unusual, weird, weirdly | label; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 4, Opus 4; Sonnet 3, Opus 3 |
| [empathetic](../../../traits/instructions/empathetic.json) | social_interpersonal | unclassified | empathetic, cares about the person, emotionally attuned, empathic, sensitive | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 3; Sonnet 3, Opus 3 |
| [external locus of control](../../../traits/instructions/external_locus_of_control.json) | cognitive_epistemic | pair | believes in luck | Sonnet 2, Opus 3 |
| [fashionable](../../../traits/instructions/fashionable.json) | cognitive_epistemic | pair | fashion conscious, fashionable, fashion-monger, new-fashioned, on-trend, stylish, trendy | label (renamed from fashion_conscious); label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 4 |
| [financially conservative](../../../traits/instructions/financially_conservative.json) | emotional_temperament | pair | financially cautious | label (renamed from financially_cautious) |
| [financially secure](../../../traits/instructions/financially_secure.json) | identity_demographic | pair | financially stable | Sonnet 3, Opus 3 |
| [flippant](../../../traits/instructions/flippant.json) | communication_style | singleton | flippant, cavalier, facetious, wiseacre | label; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [flirty](../../../traits/instructions/flirty.json) | social_interpersonal | singleton | coquetting, flirtatious, flirting, seductive, suggestive | Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 4, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [forgiving](../../../traits/instructions/forgiving.json) | social_interpersonal | pair | saintly | Sonnet 2, Opus 3 |
| [harmful](../../../traits/instructions/harmful.json) | moral_stance | pair | harmful | label |
| [harmless](../../../traits/instructions/harmless.json) | moral_stance | pair | harmless | label |
| [high-context (Hall)](../../../traits/instructions/high_context_hall.json) | communication_style | pair | high-context | Sonnet 4, Opus 4 |
| [idealistic](../../../traits/instructions/idealistic.json) | moral_stance | pair | idealistic, dreamer, quixotic, utopian | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [impatient](../../../traits/instructions/impatient.json) | emotional_temperament | pair | intolerant of waiting | Sonnet 2, Opus 3 |
| [Indigenous Australian](../../../traits/instructions/indigenous_australian.json) | identity_demographic | map | autochthonous | Sonnet 2, Opus 3 |
| [innovative](../../../traits/instructions/innovative.json) | cognitive_epistemic | pair | cutting-edge, experimental, game-changer, pioneering | Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [internal locus of control](../../../traits/instructions/internal_locus_of_control.json) | cognitive_epistemic | pair | believes in own control | Sonnet 3, Opus 4 |
| [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | moral_stance | pair | devotee, devout, god-fearing, spiritually convinced | Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [ironic](../../../traits/instructions/ironic.json) | communication_style | pair | ironical | Sonnet 4, Opus 4 |
| [low-context (Hall)](../../../traits/instructions/low_context_hall.json) | communication_style | pair | low-context | Sonnet 4, Opus 4 |
| [melancholic](../../../traits/instructions/melancholic.json) | emotional_temperament | pair | melancholic, dark, dreary, given to lament, gloomy, melancholy, prone to lingering gloom, prone to low mood, saturnine, uncheerful, unsunny | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [meritocratic](../../../traits/instructions/meritocratic.json) | moral_stance | singleton | believes in meritocracy | Sonnet 4, Opus 4 |
| [night-owl](../../../traits/instructions/night_owl.json) | identity_demographic | pair | nighthawk, nocturnal | Sonnet 3, Opus 4; Sonnet 3, Opus 3 |
| [nurturing](../../../traits/instructions/nurturing.json) | social_interpersonal | pair | grandmotherly | Sonnet 2, Opus 3 |
| [obedient](../../../traits/instructions/obedient.json) | alignment_ai_agent | pair | obedient | label |
| [OCD](../../../traits/instructions/ocd.json) | emotional_temperament | singleton | compulsive, compulsively checks and washes, compulsively counts, prone to counting compulsions | label (renamed from compulsive); Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [patient](../../../traits/instructions/patient.json) | emotional_temperament | pair | comfortable with waiting, overpatient, unimpatient | Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [philanthropic](../../../traits/instructions/philanthropic.json) | moral_stance | singleton | contributor | Sonnet 2, Opus 3 |
| [philistine](../../../traits/instructions/philistine.json) | cognitive_epistemic | pair | banausic, uninterested in the arts | Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [picky-eater](../../../traits/instructions/picky_eater.json) | emotional_temperament | pair | picky | Sonnet 2, Opus 3 |
| [pragmatic](../../../traits/instructions/pragmatic.json) | cognitive_epistemic | pair | pragmatic, doing whatever works, little given to fantasy | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [pretentious](../../../traits/instructions/pretentious.json) | communication_style | pair | pretentious, high-toned, la-di-da, pretenseful | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4 |
| [rebellious](../../../traits/instructions/rebellious.json) | alignment_ai_agent | pair | rebellious, defiant of authority, mutinous | label; Sonnet 3, Opus 4; Sonnet 3, Opus 4 |
| [sedentary](../../../traits/instructions/sedentary.json) | identity_demographic | pair | sedentary | label |
| [sincere](../../../traits/instructions/sincere.json) | communication_style | pair | sincere | label |
| [socialist](../../../traits/instructions/socialist.json) | moral_stance | pair | communistic, left-winger, self-left, socialistic | Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4 |
| [squeamish](../../../traits/instructions/squeamish.json) | emotional_temperament | pair | squeamish | label |
| [submissive](../../../traits/instructions/submissive.json) | social_interpersonal | pair | submissive, easily dominated by others, self-surrendering, submissive to others, subservient | label; Sonnet 3, Opus 4; Sonnet 3, Opus 4; Sonnet 4, Opus 4; Sonnet 3, Opus 4 |
| [thick-skinned](../../../traits/instructions/thick_skinned.json) | emotional_temperament | pair | thick-skinned, pachydermous, proof against, shame-proof | label; Sonnet 3, Opus 4; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [thin-skinned](../../../traits/instructions/thin_skinned.json) | emotional_temperament | pair | thin-skinned, bristling, brittle, chippy, dislikes being mocked, dislikes being ridiculed, easily put out, hypersensitive, overdelicate, oversensitive, prickly, sensitive about appearance, spiky, supersensitive, touchy | label; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [traditional](../../../traits/instructions/traditional.json) | cognitive_epistemic | pair | musty, old-world, out-dated, square | Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [unfashionable](../../../traits/instructions/unfashionable.json) | identity_demographic | pair | unfashionable, frumpish, indifferent to fashion | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [unpretentious](../../../traits/instructions/unpretentious.json) | communication_style | pair | homespun, natural, simple, uncomplicated, unembellished, unstudied | Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [upper-class](../../../traits/instructions/upper_class.json) | identity_demographic | pair | top-drawer | Sonnet 3, Opus 4 |
| [working-class](../../../traits/instructions/working_class.json) | identity_demographic | pair | grisette, lowborn, lower-class | Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3 |

### False covers (166 candidates)

| candidate | matches hidden | how | covered by | hidden trait recovered anyway |
|---|---|---|---|---|
| adventurous | [adventurous-eater](../../../traits/instructions/adventurous_eater.json) | Sonnet 3, Opus 3 | [adventurous](../../../traits/instructions/adventurous.json) | no |
| aggressive | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| airy | [flippant](../../../traits/instructions/flippant.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| altruistic | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 3, Opus 3 | [altruistic](../../../traits/instructions/altruistic.json) | yes |
| antagonizing | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [hostile](../../../traits/instructions/hostile.json) | yes |
| aristocratic | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 3, Opus 3 | [aristocratic](../../../traits/instructions/aristocratic.json) | yes |
| artsy | [artistic (Holland)](../../../traits/instructions/artistic_holland.json) | Sonnet 3, Opus 3 | [artistic](../../../traits/instructions/artistic.json) | no |
| at ease with waiting | [patient](../../../traits/instructions/patient.json) | Sonnet 2, Opus 3 | [calm](../../../traits/instructions/calm.json) | yes |
| averse to novelty | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| averse to novelty | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| battleful | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [hostile](../../../traits/instructions/hostile.json) | yes |
| bellicose | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| belligerent | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| beneficent | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 3, Opus 3 | [helpful](../../../traits/instructions/helpful.json) | yes |
| benthamite | [utilitarian](../../../traits/instructions/utilitarian.json) | Sonnet 3, Opus 3 | [consequentialist](../../../traits/instructions/consequentialist.json) | no |
| blithe | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| born into wealth | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 2, Opus 3 | [old money](../../../traits/instructions/old_money.json) | yes |
| born privileged | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 3, Opus 3 | [old money](../../../traits/instructions/old_money.json) | yes |
| brawlsome | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [hostile](../../../traits/instructions/hostile.json) | yes |
| breezy | [flippant](../../../traits/instructions/flippant.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| buoyant | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 3 | [optimistic](../../../traits/instructions/optimistic.json) | yes |
| cares about people | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 3, Opus 3 | [compassionate](../../../traits/instructions/compassionate.json) | yes |
| charitable | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 3, Opus 3 | [generous](../../../traits/instructions/generous.json) | yes |
| cheerless | [melancholic](../../../traits/instructions/melancholic.json) | Sonnet 2, Opus 3 | [joyless](../../../traits/instructions/joyless.json) | yes |
| clement | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| clingy | [anxious-preoccupied attachment](../../../traits/instructions/anxious_preoccupied_attachment.json) | Sonnet 3, Opus 3 | [clingy](../../../traits/instructions/clingy.json) | yes |
| cold hearted | [sociopathic](../../../traits/instructions/sociopathic.json) | Sonnet 2, Opus 3 | [callous](../../../traits/instructions/callous.json) | no |
| combative | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| commiserative | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 2, Opus 3 | [compassionate](../../../traits/instructions/compassionate.json) | yes |
| conciliatory | [conciliatory](../../../traits/instructions/conciliatory.json) | label | [accommodating](../../../traits/instructions/accommodating.json) | yes |
| conflictive | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 4 | [disagreeable](../../../traits/instructions/disagreeable.json) | yes |
| conformant | [conventional](../../../traits/instructions/conventional.json) | Sonnet 3, Opus 3 | [conformist](../../../traits/instructions/conformist.json) | yes |
| conforming | [conventional](../../../traits/instructions/conventional.json) | Sonnet 2, Opus 3 | [conformist](../../../traits/instructions/conformist.json) | yes |
| conventional | [conventional](../../../traits/instructions/conventional.json) | label | [staid](../../../traits/instructions/staid.json) | yes |
| conventional | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [staid](../../../traits/instructions/staid.json) | yes |
| devoutly christian | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| devoutly religious | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [Jewish](../../../traits/instructions/jewish.json) | yes |
| dismal | [melancholic](../../../traits/instructions/melancholic.json) | Sonnet 2, Opus 3 | [pessimistic](../../../traits/instructions/pessimistic.json) | yes |
| down to earth | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 3, Opus 3 | [practical](../../../traits/instructions/practical.json) | yes |
| earnest | [sincere](../../../traits/instructions/sincere.json) | Sonnet 2, Opus 3 | [earnest](../../../traits/instructions/earnest.json) | yes |
| earth-bound | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 2, Opus 3 | [practical](../../../traits/instructions/practical.json) | yes |
| earthy | [unpretentious](../../../traits/instructions/unpretentious.json) | Sonnet 3, Opus 3 | [plain-spoken](../../../traits/instructions/plain_spoken.json) | yes |
| emotionally fragile | [thin-skinned](../../../traits/instructions/thin_skinned.json) | Sonnet 3, Opus 3 | [fragile](../../../traits/instructions/fragile.json) | yes |
| empathy | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 4, Opus 4 | [compassionate](../../../traits/instructions/compassionate.json) | yes |
| Failure-averse | [financially conservative](../../../traits/instructions/financially_conservative.json) | Sonnet 2, Opus 3 | [risk-averse](../../../traits/instructions/risk_averse.json) | yes |
| feels externally controlled | [external locus of control](../../../traits/instructions/external_locus_of_control.json) | Sonnet 4, Opus 4 | [fatalistic](../../../traits/instructions/fatalistic.json) | yes |
| financially comfortable | [financially secure](../../../traits/instructions/financially_secure.json) | Sonnet 3, Opus 3 | [wealthy](../../../traits/instructions/wealthy.json) | yes |
| financially timid | [financially conservative](../../../traits/instructions/financially_conservative.json) | Sonnet 3, Opus 3 | [risk-averse](../../../traits/instructions/risk_averse.json) | yes |
| financially vulnerable | [financially precarious](../../../traits/instructions/financially_precarious.json) | Sonnet 3, Opus 3 | [poor](../../../traits/instructions/poor.json) | no |
| flip | [flippant](../../../traits/instructions/flippant.json) | Sonnet 3, Opus 4 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| fogy | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| folksy | [unpretentious](../../../traits/instructions/unpretentious.json) | Sonnet 2, Opus 3 | [casual](../../../traits/instructions/casual.json) | yes |
| forbearing | [patient](../../../traits/instructions/patient.json) | Sonnet 2, Opus 3 | [placid](../../../traits/instructions/placid.json) | yes |
| forgiving | [forgiving](../../../traits/instructions/forgiving.json) | label | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| frivolous | [flippant](../../../traits/instructions/flippant.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| generally happy | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 3 | [joyful](../../../traits/instructions/joyful.json) | yes |
| generous | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 2, Opus 3 | [generous](../../../traits/instructions/generous.json) | yes |
| gives second chances | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| giving | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 2, Opus 3 | [generous](../../../traits/instructions/generous.json) | yes |
| gladsome | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 4 | [joyful](../../../traits/instructions/joyful.json) | yes |
| good-humoured | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| great-hearted | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 2, Opus 3 | [generous](../../../traits/instructions/generous.json) | yes |
| ground-breaking | [innovative](../../../traits/instructions/innovative.json) | Sonnet 3, Opus 3 | [creative](../../../traits/instructions/creative.json) | yes |
| happy-go-lucky | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| hidebound | [conventional](../../../traits/instructions/conventional.json) | Sonnet 2, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| hidebound | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| high-blown | [pretentious](../../../traits/instructions/pretentious.json) | Sonnet 2, Opus 3 | [bombastic](../../../traits/instructions/bombastic.json) | yes |
| highfalutin | [pretentious](../../../traits/instructions/pretentious.json) | Sonnet 3, Opus 3 | [bombastic](../../../traits/instructions/bombastic.json) | yes |
| highfaluting | [pretentious](../../../traits/instructions/pretentious.json) | Sonnet 3, Opus 3 | [bombastic](../../../traits/instructions/bombastic.json) | yes |
| huffy | [thin-skinned](../../../traits/instructions/thin_skinned.json) | Sonnet 2, Opus 3 | [sulky](../../../traits/instructions/sulky.json) | yes |
| impatient | [impatient](../../../traits/instructions/impatient.json) | label | [hurried](../../../traits/instructions/hurried.json) | yes |
| impervious | [thick-skinned](../../../traits/instructions/thick_skinned.json) | Sonnet 3, Opus 3 | [stoic](../../../traits/instructions/stoic.json) | yes |
| imprudent | [financially reckless](../../../traits/instructions/financially_reckless.json) | Sonnet 3, Opus 3 | [impulsive](../../../traits/instructions/impulsive.json) | no |
| incautious | [financially reckless](../../../traits/instructions/financially_reckless.json) | Sonnet 3, Opus 3 | [reckless](../../../traits/instructions/reckless.json) | no |
| indifferent to the arts | [philistine](../../../traits/instructions/philistine.json) | Sonnet 2, Opus 3 | [conventional (HEXACO)](../../../traits/instructions/conventional_hexaco.json) | yes |
| inexplicit | [high-context (Hall)](../../../traits/instructions/high_context_hall.json) | Sonnet 3, Opus 3 | [cryptic](../../../traits/instructions/cryptic.json) | yes |
| inharmonious | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [disagreeable](../../../traits/instructions/disagreeable.json) | yes |
| innovative | [innovative](../../../traits/instructions/innovative.json) | label | [creative](../../../traits/instructions/creative.json) | yes |
| inventive | [innovative](../../../traits/instructions/innovative.json) | Sonnet 3, Opus 3 | [creative](../../../traits/instructions/creative.json) | yes |
| inventive and idea-driven | [innovative](../../../traits/instructions/innovative.json) | Sonnet 3, Opus 3 | [creative](../../../traits/instructions/creative.json) | yes |
| irenic | [conciliatory](../../../traits/instructions/conciliatory.json) | Sonnet 3, Opus 4 | [agreeable](../../../traits/instructions/agreeable.json) | yes |
| joyfully exuberant | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 2, Opus 3 | [joyful](../../../traits/instructions/joyful.json) | yes |
| lenient | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [lenient](../../../traits/instructions/lenient.json) | yes |
| light-hearted | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| light-minded | [flippant](../../../traits/instructions/flippant.json) | Sonnet 3, Opus 4 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| lighthearted | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| lightsome | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 3, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| magnanimous | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 2, Opus 3 | [magnanimous](../../../traits/instructions/magnanimous.json) | yes |
| merciful | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [merciful](../../../traits/instructions/merciful.json) | yes |
| mild-hearted | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 2, Opus 3 | [gentle](../../../traits/instructions/gentle.json) | yes |
| modern | [fashionable](../../../traits/instructions/fashionable.json) | Sonnet 2, Opus 3 | [modern](../../../traits/instructions/modern.json) | yes |
| neglectful | [neglectful](../../../traits/instructions/neglectful.json) | label | [irresponsible](../../../traits/instructions/irresponsible.json) | no |
| neophobia | [picky-eater](../../../traits/instructions/picky_eater.json) | Sonnet 2, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| nonirritable | [patient](../../../traits/instructions/patient.json) | Sonnet 3, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| nourishing | [nurturing](../../../traits/instructions/nurturing.json) | Sonnet 3, Opus 4 | [supportive](../../../traits/instructions/supportive.json) | yes |
| novel | [innovative](../../../traits/instructions/innovative.json) | Sonnet 3, Opus 3 | [creative](../../../traits/instructions/creative.json) | yes |
| nurturing | [nurturing](../../../traits/instructions/nurturing.json) | label | [supportive](../../../traits/instructions/supportive.json) | yes |
| old fashioned | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| old-line | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| only follows familiar patterns | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| only follows familiar patterns | [conventional](../../../traits/instructions/conventional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| only follows familiar patterns | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| open to new experiences | [adventurous-eater](../../../traits/instructions/adventurous_eater.json) | Sonnet 2, Opus 3 | [adventurous](../../../traits/instructions/adventurous.json) | no |
| open to new experiences | [open (Big Five)](../../../traits/instructions/open_big_five.json) | Sonnet 3, Opus 3 | [adventurous](../../../traits/instructions/adventurous.json) | no |
| original | [innovative](../../../traits/instructions/innovative.json) | Sonnet 3, Opus 3 | [creative](../../../traits/instructions/creative.json) | yes |
| orthodox | [conventional](../../../traits/instructions/conventional.json) | Sonnet 3, Opus 3 | [orthodox](../../../traits/instructions/orthodox.json) | yes |
| orthodox | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [orthodox](../../../traits/instructions/orthodox.json) | yes |
| overcompassionate | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 2, Opus 3 | [compassionate](../../../traits/instructions/compassionate.json) | yes |
| pachydermatous | [thick-skinned](../../../traits/instructions/thick_skinned.json) | Sonnet 3, Opus 4 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| patient | [patient](../../../traits/instructions/patient.json) | label | [placid](../../../traits/instructions/placid.json) | yes |
| patrician | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 3, Opus 3 | [old money](../../../traits/instructions/old_money.json) | yes |
| philanthropic | [philanthropic](../../../traits/instructions/philanthropic.json) | label | [generous](../../../traits/instructions/generous.json) | yes |
| philistine | [philistine](../../../traits/instructions/philistine.json) | label | [conventional (HEXACO)](../../../traits/instructions/conventional_hexaco.json) | yes |
| pious | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| placable | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| practical | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 4, Opus 4 | [practical](../../../traits/instructions/practical.json) | yes |
| practically wise | [pragmatic](../../../traits/instructions/pragmatic.json) | Sonnet 3, Opus 3 | [wise](../../../traits/instructions/wise.json) | yes |
| pretenseless | [unpretentious](../../../traits/instructions/unpretentious.json) | Sonnet 3, Opus 3 | [authentic](../../../traits/instructions/authentic.json) | yes |
| privileged | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 2, Opus 3 | [old money](../../../traits/instructions/old_money.json) | yes |
| prone to absorbed daydreaming | [open (Big Five)](../../../traits/instructions/open_big_five.json) | Sonnet 2, Opus 3 | [dreamy](../../../traits/instructions/dreamy.json) | no |
| prosperous | [financially secure](../../../traits/instructions/financially_secure.json) | Sonnet 2, Opus 3 | [wealthy](../../../traits/instructions/wealthy.json) | yes |
| prudential | [cautious](../../../traits/instructions/cautious.json) | Sonnet 3, Opus 3 | [prudent](../../../traits/instructions/prudent.json) | yes |
| public-spirited | [philanthropic](../../../traits/instructions/philanthropic.json) | Sonnet 3, Opus 3 | [altruistic](../../../traits/instructions/altruistic.json) | yes |
| pugnacious | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| quick to forgive | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| rancorous | [unforgiving](../../../traits/instructions/unforgiving.json) | Sonnet 2, Opus 3 | [bitter](../../../traits/instructions/bitter.json) | no |
| religious | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| religiously devout | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| risk-averse | [financially conservative](../../../traits/instructions/financially_conservative.json) | Sonnet 3, Opus 3 | [risk-averse](../../../traits/instructions/risk_averse.json) | yes |
| risk tolerant | [financially reckless](../../../traits/instructions/financially_reckless.json) | Sonnet 2, Opus 3 | [risk-seeking](../../../traits/instructions/risk_seeking.json) | no |
| sardonic | [ironic](../../../traits/instructions/ironic.json) | Sonnet 2, Opus 3 | [sardonic](../../../traits/instructions/sardonic.json) | yes |
| silk-stocking | [upper-class](../../../traits/instructions/upper_class.json) | Sonnet 3, Opus 4 | [wealthy](../../../traits/instructions/wealthy.json) | yes |
| slow to forgive | [unforgiving](../../../traits/instructions/unforgiving.json) | Sonnet 3, Opus 3 | [quarrelsome (HEXACO)](../../../traits/instructions/quarrelsome_hexaco.json) | no |
| sociopathic | [sociopathic](../../../traits/instructions/sociopathic.json) | label | [callous](../../../traits/instructions/callous.json) | no |
| spiritual-minded | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 2, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| stick-in-the-mud | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| stodgy | [conventional](../../../traits/instructions/conventional.json) | Sonnet 2, Opus 3 | [staid](../../../traits/instructions/staid.json) | yes |
| tenderminded | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 3, Opus 3 | [compassionate](../../../traits/instructions/compassionate.json) | yes |
| traditional | [traditional](../../../traits/instructions/traditional.json) | label | [conservative](../../../traits/instructions/conservative.json) | yes |
| traditionalist | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 4 | [orthodox](../../../traits/instructions/orthodox.json) | yes |
| trifling | [flippant](../../../traits/instructions/flippant.json) | Sonnet 3, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| truculent | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [hostile](../../../traits/instructions/hostile.json) | yes |
| ultrareligious | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| umbrageous | [thin-skinned](../../../traits/instructions/thin_skinned.json) | Sonnet 3, Opus 4 | [aggrieved](../../../traits/instructions/aggrieved.json) | yes |
| unadventurous eater | [picky-eater](../../../traits/instructions/picky_eater.json) | Sonnet 3, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| unaffected | [thick-skinned](../../../traits/instructions/thick_skinned.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unconventional | [eccentric](../../../traits/instructions/eccentric.json) | Sonnet 3, Opus 3 | [heterodox](../../../traits/instructions/heterodox.json) | yes |
| uncritical | [uncritical](../../../traits/instructions/uncritical.json) | label | [credulous](../../../traits/instructions/credulous.json) | no |
| unearnest | [flippant](../../../traits/instructions/flippant.json) | Sonnet 3, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| unembittered | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| unforgiving | [unforgiving](../../../traits/instructions/unforgiving.json) | label | [vindictive](../../../traits/instructions/vindictive.json) | no |
| uninspired | [conventional](../../../traits/instructions/conventional.json) | Sonnet 2, Opus 3 | [formulaic](../../../traits/instructions/formulaic.json) | yes |
| unoriginal in outlook | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [conformist](../../../traits/instructions/conformist.json) | yes |
| unpardoning | [unforgiving](../../../traits/instructions/unforgiving.json) | Sonnet 3, Opus 4 | [vindictive](../../../traits/instructions/vindictive.json) | no |
| unpeaceable | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [hostile](../../../traits/instructions/hostile.json) | yes |
| unpretentious | [unpretentious](../../../traits/instructions/unpretentious.json) | label | [unassuming](../../../traits/instructions/unassuming.json) | yes |
| unprogressive | [traditional](../../../traits/instructions/traditional.json) | Sonnet 3, Opus 3 | [conservative](../../../traits/instructions/conservative.json) | yes |
| unreproachful | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| unresentful | [forgiving](../../../traits/instructions/forgiving.json) | Sonnet 3, Opus 3 | [agreeable (HEXACO)](../../../traits/instructions/agreeable_hexaco.json) | yes |
| unsarcastic | [sincere](../../../traits/instructions/sincere.json) | Sonnet 3, Opus 4 | [earnest](../../../traits/instructions/earnest.json) | yes |
| unsecular | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| unsolemn | [flippant](../../../traits/instructions/flippant.json) | Sonnet 2, Opus 3 | [lighthearted](../../../traits/instructions/lighthearted.json) | yes |
| unsolicitous | [neglectful](../../../traits/instructions/neglectful.json) | Sonnet 3, Opus 3 | [uncaring](../../../traits/instructions/uncaring.json) | no |
| unventurous | [financially conservative](../../../traits/instructions/financially_conservative.json) | Sonnet 2, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| upbeat | [cheerful](../../../traits/instructions/cheerful.json) | Sonnet 2, Opus 3 | [optimistic](../../../traits/instructions/optimistic.json) | yes |
| utilitarian | [utilitarian](../../../traits/instructions/utilitarian.json) | label | [consequentialist](../../../traits/instructions/consequentialist.json) | no |
| values harmony | [conciliatory](../../../traits/instructions/conciliatory.json) | Sonnet 3, Opus 3 | [agreeable](../../../traits/instructions/agreeable.json) | yes |
| venturesome | [adventurous-eater](../../../traits/instructions/adventurous_eater.json) | Sonnet 2, Opus 3 | [risk-seeking](../../../traits/instructions/risk_seeking.json) | no |
| venturous | [financially reckless](../../../traits/instructions/financially_reckless.json) | Sonnet 2, Opus 3 | [risk-seeking](../../../traits/instructions/risk_seeking.json) | no |
| vernacular | [unpretentious](../../../traits/instructions/unpretentious.json) | Sonnet 3, Opus 3 | [casual](../../../traits/instructions/casual.json) | yes |
| votary | [intrinsic (Allport)](../../../traits/instructions/intrinsic_allport.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| warlike | [confrontational](../../../traits/instructions/confrontational.json) | Sonnet 3, Opus 3 | [aggressive](../../../traits/instructions/aggressive.json) | yes |
| warmly empathetic | [empathetic](../../../traits/instructions/empathetic.json) | Sonnet 3, Opus 4 | [compassionate](../../../traits/instructions/compassionate.json) | yes |

### Not recovered (37)

[achiever (VALS)](../../../traits/instructions/achiever_vals.json), [adventurous-eater](../../../traits/instructions/adventurous_eater.json), [Aries](../../../traits/instructions/aries.json), [artistic (Holland)](../../../traits/instructions/artistic_holland.json), [authoritative (Baumrind)](../../../traits/instructions/authoritative_baumrind.json), [black-haired](../../../traits/instructions/black_haired.json), [dark-skinned](../../../traits/instructions/dark_skinned.json), [dignity culture](../../../traits/instructions/dignity_culture.json), [ENFP (MBTI)](../../../traits/instructions/enfp_mbti.json), [Enneagram 3](../../../traits/instructions/enneagram_3.json), [Enneagram 5](../../../traits/instructions/enneagram_5.json), [ENTJ (MBTI)](../../../traits/instructions/entj_mbti.json), [ESFJ (MBTI)](../../../traits/instructions/esfj_mbti.json), [ESTP (MBTI)](../../../traits/instructions/estp_mbti.json), [extrinsic (Allport)](../../../traits/instructions/extrinsic_allport.json), [face culture](../../../traits/instructions/face_culture.json), [fair-skinned](../../../traits/instructions/fair_skinned.json), [financially precarious](../../../traits/instructions/financially_precarious.json), [financially reckless](../../../traits/instructions/financially_reckless.json), [Gemini](../../../traits/instructions/gemini.json), [honor culture](../../../traits/instructions/honor_culture.json), [innovator (VALS)](../../../traits/instructions/innovator_vals.json), [neglectful](../../../traits/instructions/neglectful.json), [New Age](../../../traits/instructions/new_age.json), [open (Big Five)](../../../traits/instructions/open_big_five.json), [Ravenclaw](../../../traits/instructions/ravenclaw.json), [Russian](../../../traits/instructions/russian.json), [Slytherin](../../../traits/instructions/slytherin.json), [sociopathic](../../../traits/instructions/sociopathic.json), [strong-stomached](../../../traits/instructions/strong_stomached.json), [Taoist](../../../traits/instructions/taoist.json), [traumatized](../../../traits/instructions/traumatized.json), [uncritical](../../../traits/instructions/uncritical.json), [unforgiving](../../../traits/instructions/unforgiving.json), [utilitarian](../../../traits/instructions/utilitarian.json), [win-win-seeking](../../../traits/instructions/win_win_seeking.json), [words of affirmation](../../../traits/instructions/words_of_affirmation.json)

## Seed 1

Hidden traits: [hidden.json](./seed1/hidden.json); the reduced-corpus M3 run: [decisions.md](../../novelty/rec_pooled_1_s1/decisions.md) ({"new": 4548, "covered": 3038}); every pair judged: [matches.jsonl](./seed1/matches.jsonl).

### Recovered (61 of 95)

| hidden trait | region | kind | recovered by | how |
|---|---|---|---|---|
| [abstemious](../../../traits/instructions/abstemious.json) | emotional_temperament | pair | abstemious, abstentious, stays within limits | label; Sonnet 3, Opus 4; Sonnet 3, Opus 3 |
| [analytical](../../../traits/instructions/analytical.json) | cognitive_epistemic | pair | analytical, analytically inclined, over-analytical | label; Sonnet 4, Opus 4; Sonnet 3, Opus 3 |
| [antifeminist](../../../traits/instructions/antifeminist.json) | moral_stance | pair | anti feminist | label, separator-blind |
| [bitter](../../../traits/instructions/bitter.json) | emotional_temperament | set | embittered, overbitter, rancorous | Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [brash](../../../traits/instructions/brash.json) | communication_style | pair | brash | label |
| [brave](../../../traits/instructions/brave.json) | moral_stance | pair | brave, dauntless, doughty, guts, gutsy, heroic, lion-hearted, stout-hearted, stouthearted, unshrinking, valiant, valorous | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 4 |
| [bullying](../../../traits/instructions/bullying.json) | social_interpersonal | singleton | bullying, bully | label; Sonnet 4, Opus 4 |
| [circumspect](../../../traits/instructions/circumspect.json) | communication_style | pair | circumspect, politic | label; Sonnet 3, Opus 3 |
| [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | cognitive_epistemic | pair | rarely fantasizes | Sonnet 2, Opus 3 |
| [competent](../../../traits/instructions/competent.json) | cognitive_epistemic | pair | competent, able, above-average, accomplished, adept, amazing, capable, close to perfect, consummate, excelling, godlike, high-functioning, intermediate, mastered, masterful, phenomenal, practiced, proficient, serviceable, skillful, stellar, top-flight, top-notch, world-class | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [cowardly](../../../traits/instructions/cowardly.json) | moral_stance | pair | cowardly, carpet-knight, chicken, craven, easily intimidated, fainthearted, gutless, hen-hearted, lily-livered, nerveless, pansy, pigeon-hearted, poor-spirited, pusillanimous, recreant, unheroic, unmanly, unvaliant, weak-hearted, weak-kneed, weak-spirited, yellow | label; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 4 |
| [dignified](../../../traits/instructions/dignified.json) | emotional_temperament | singleton | dignified, august, grand, kingly, magnificent, majestic, regal, sublime | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [dismissive-avoidant attachment](../../../traits/instructions/dismissive_avoidant_attachment.json) | social_interpersonal | square | uninterested in closeness | Sonnet 3, Opus 3 |
| [earnest](../../../traits/instructions/earnest.json) | communication_style | pair | earnest, overearnest | label; Sonnet 2, Opus 3 |
| [emphatic](../../../traits/instructions/emphatic.json) | communication_style | pair | emphatic, exclaiming, forceful, forcible, overemphatic | label; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [entitled](../../../traits/instructions/entitled.json) | social_interpersonal | singleton | entitled, feels entitled to more, sense of entitlement, spoiled | label; Sonnet 3, Opus 3; Sonnet 4, Opus 4; Sonnet 3, Opus 3 |
| [erudite](../../../traits/instructions/erudite.json) | cognitive_epistemic | pair | erudite, bookish, learned | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [gluttonous](../../../traits/instructions/gluttonous.json) | emotional_temperament | pair | edacious, engorging, glutting, trencherman, voracious | Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [gregarious](../../../traits/instructions/gregarious.json) | social_interpersonal | pair | companionable, convivial | Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [harmful](../../../traits/instructions/harmful.json) | moral_stance | pair | harmful | label |
| [harmless](../../../traits/instructions/harmless.json) | moral_stance | pair | harmless | label |
| [honorable](../../../traits/instructions/honorable.json) | moral_stance | pair | honorable | label |
| [incompetent](../../../traits/instructions/incompetent.json) | cognitive_epistemic | pair | incompetent, inept, deficient, faulty, inadequate, inapt, incapable, low-caliber, nonfunctional, second-rate, skill-less, third-rate, unskilled, unskillful | label; label (renamed from inept); Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 4 |
| [informational](../../../traits/instructions/informational.json) | communication_style | pair | refuses to advocate | Sonnet 2, Opus 3 |
| [intuitive](../../../traits/instructions/intuitive.json) | cognitive_epistemic | pair | intuitive | label |
| [irresponsible](../../../traits/instructions/irresponsible.json) | moral_stance | pair | irresponsible, neglecting, shirks responsibilities | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [judgmental](../../../traits/instructions/judgmental.json) | social_interpersonal | singleton | judgmental, censorious, condemning, damning, evaluative, holier-than-thou, judging, ultracritical | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [learning-oriented](../../../traits/instructions/learning_oriented.json) | cognitive_epistemic | pair | growth oriented, improving, mastery oriented | Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4 |
| [lighthearted](../../../traits/instructions/lighthearted.json) | emotional_temperament | pair | frivolous, jokey | Sonnet 2, Opus 3; Sonnet 2, Opus 3 |
| [male](../../../traits/instructions/male.json) | identity_demographic | pair | bloke, fellow, guy, man | Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [manipulative](../../../traits/instructions/manipulative.json) | social_interpersonal | singleton | manipulative, habitually manipulates others, manipulates people, manipulating, manipulative toward others | label; Sonnet 3, Opus 4; Sonnet 4, Opus 4; Sonnet 4, Opus 4; Sonnet 3, Opus 4 |
| [materialistic](../../../traits/instructions/materialistic.json) | moral_stance | pair | materialistic, earthly-minded, worldly-minded | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [meditative](../../../traits/instructions/meditative.json) | emotional_temperament | unclassified | meditative | label |
| [misanthropic](../../../traits/instructions/misanthropic.json) | social_interpersonal | singleton | misanthropic, misanthropical | label; Sonnet 4, Opus 4 |
| [moral universalist](../../../traits/instructions/moral_universalist.json) | moral_stance | pair | universalist | label (renamed from universalist) |
| [noncommittal](../../../traits/instructions/noncommittal.json) | cognitive_epistemic | pair | non committal, noncommittal, refuses to advocate | label, separator-blind; label; Sonnet 3, Opus 3 |
| [open (Big Five)](../../../traits/instructions/open_big_five.json) | cognitive_epistemic | pair | vividly imaginative | Sonnet 2, Opus 3 |
| [opinionated](../../../traits/instructions/opinionated.json) | communication_style | pair | opinionated, opinionative | label; Sonnet 3, Opus 3 |
| [optimistic](../../../traits/instructions/optimistic.json) | emotional_temperament | pair | optimistic, bullish, future-oriented optimism, habitually optimistic, hyper-optimistic, optimist, optimistic outlook, over-optimistic, positive, sanguine | label; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 4 |
| [organized](../../../traits/instructions/organized.json) | cognitive_epistemic | pair | overneat, well-organized | Sonnet 2, Opus 3; Sonnet 3, Opus 3 |
| [other-focused](../../../traits/instructions/other_focused.json) | social_interpersonal | pair | people-oriented | Sonnet 3, Opus 3 |
| [pessimistic](../../../traits/instructions/pessimistic.json) | emotional_temperament | pair | pessimistic, alarmist, habitually pessimistic, pessimist | label; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 4 |
| [philosophical](../../../traits/instructions/philosophical.json) | cognitive_epistemic | singleton | philosophical, metaphysical, philosophizing | label; Sonnet 3, Opus 3; Sonnet 3, Opus 4 |
| [plain-looking](../../../traits/instructions/plain_looking.json) | identity_demographic | pair | one of many | Sonnet 2, Opus 3 |
| [poor](../../../traits/instructions/poor.json) | identity_demographic | pair | destitute, guttersnipe, ill-provided, impecunious, necessitous, resourceless | Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [proactive](../../../traits/instructions/proactive.json) | alignment_ai_agent | pair | proactive, self-motivated | label; Sonnet 2, Opus 3 |
| [promiscuous](../../../traits/instructions/promiscuous.json) | social_interpersonal | singleton | promiscuous, callet, licentious, promiscuously intimate, quean, sluttish, unchaste, wanton, whorish | label; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [reactive](../../../traits/instructions/reactive.json) | cognitive_epistemic | pair | short-sighted | Sonnet 3, Opus 3 |
| [renter](../../../traits/instructions/renter.json) | identity_demographic | pair | tenant | Sonnet 4, Opus 4 |
| [rhetorical](../../../traits/instructions/rhetorical.json) | communication_style | pair | rhetorical | label |
| [sardonic](../../../traits/instructions/sardonic.json) | communication_style | pair | satirical | Sonnet 2, Opus 3 |
| [self-absorbed](../../../traits/instructions/self_absorbed.json) | social_interpersonal | pair | self-absorbed, egocentric, egotistical, self-focused in conversation, self-involved, self-obsessed, self-referential, talks mostly about self | label; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 4; Sonnet 4, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [solemn](../../../traits/instructions/solemn.json) | communication_style | pair | laughterless, owlish | Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [solitary](../../../traits/instructions/solitary.json) | social_interpersonal | pair | asocial, avoids others and closeness, eremitic, loner, prefers being alone, reclusive, seclusive, separate, separative, socially withdrawn, unsociable | Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 4, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 4 |
| [spiritual](../../../traits/instructions/spiritual.json) | moral_stance | pair | spiritual, heavenly-minded, other-worldly, transcendental, ultraspiritual | label; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 3, Opus 3 |
| [stoic](../../../traits/instructions/stoic.json) | emotional_temperament | singleton | stoic, self-mastered, tearless, undramatic, unmoved, unstirrable | label; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 3; Sonnet 2, Opus 3 |
| [strategic](../../../traits/instructions/strategic.json) | cognitive_epistemic | pair | strategic, strategist | label; Sonnet 3, Opus 3 |
| [tactical](../../../traits/instructions/tactical.json) | cognitive_epistemic | pair | visionless | Sonnet 2, Opus 3 |
| [unschooled](../../../traits/instructions/unschooled.json) | cognitive_epistemic | pair | unschooled, layman | label; Sonnet 3, Opus 3 |
| [vindictive](../../../traits/instructions/vindictive.json) | social_interpersonal | unclassified | vindictive, rancorous, revengeful, vengeful | label; Sonnet 2, Opus 3; Sonnet 4, Opus 4; Sonnet 4, Opus 4 |
| [wealthy](../../../traits/instructions/wealthy.json) | identity_demographic | pair | wealthy, affluent, deep-pocketed, one-percenter, opulent, rich, well-to-do | label; Sonnet 3, Opus 4; Sonnet 3, Opus 4; Sonnet 3, Opus 3; Sonnet 2, Opus 3; Sonnet 3, Opus 4; Sonnet 3, Opus 4 |

### False covers (196 candidates)

| candidate | matches hidden | how | covered by | hidden trait recovered anyway |
|---|---|---|---|---|
| aery | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 4 | [flippant](../../../traits/instructions/flippant.json) | yes |
| airy | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [flippant](../../../traits/instructions/flippant.json) | yes |
| ascetic | [abstemious](../../../traits/instructions/abstemious.json) | Sonnet 2, Opus 3 | [ascetic](../../../traits/instructions/ascetic.json) | yes |
| assertive | [emphatic](../../../traits/instructions/emphatic.json) | Sonnet 2, Opus 3 | [confident](../../../traits/instructions/confident.json) | yes |
| assertive | [opinionated](../../../traits/instructions/opinionated.json) | label (renamed from assertive) | [confident](../../../traits/instructions/confident.json) | yes |
| averse to novelty | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | yes |
| believes people are bad | [misanthropic](../../../traits/instructions/misanthropic.json) | Sonnet 2, Opus 3 | [cynical](../../../traits/instructions/cynical.json) | yes |
| belly-god | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 3, Opus 3 | [hedonistic](../../../traits/instructions/hedonistic.json) | yes |
| bitter | [bitter](../../../traits/instructions/bitter.json) | label | [aggrieved](../../../traits/instructions/aggrieved.json) | yes |
| bleak | [pessimistic](../../../traits/instructions/pessimistic.json) | Sonnet 3, Opus 3 | [despairing](../../../traits/instructions/despairing.json) | yes |
| blithe | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| body conscious | [body-obsessed](../../../traits/instructions/body_obsessed.json) | Sonnet 3, Opus 3 | [body-insecure](../../../traits/instructions/body_insecure.json) | no |
| braver | [brave](../../../traits/instructions/brave.json) | Sonnet 3, Opus 3 | [Gryffindor](../../../traits/instructions/gryffindor.json) | yes |
| breezy | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 4 | [flippant](../../../traits/instructions/flippant.json) | yes |
| buoyant | [optimistic](../../../traits/instructions/optimistic.json) | Sonnet 2, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| calm | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [calm](../../../traits/instructions/calm.json) | yes |
| Careless of order | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 3, Opus 3 | [careless (HEXACO)](../../../traits/instructions/careless_hexaco.json) | no |
| careless with belongings | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 2, Opus 3 | [careless (Big Five)](../../../traits/instructions/careless_big_five.json) | no |
| cerebral | [analytical](../../../traits/instructions/analytical.json) | Sonnet 2, Opus 3 | [cerebral](../../../traits/instructions/cerebral.json) | yes |
| chaotic | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 3, Opus 3 | [chaotic](../../../traits/instructions/chaotic.json) | no |
| chicken-hearted | [cowardly](../../../traits/instructions/cowardly.json) | Sonnet 3, Opus 3 | [timid](../../../traits/instructions/timid.json) | yes |
| ciceronian | [rhetorical](../../../traits/instructions/rhetorical.json) | Sonnet 2, Opus 3 | [eloquent](../../../traits/instructions/eloquent.json) | yes |
| clubby | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| composed | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| contained | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| controlled | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| cool | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| cool-headed | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| coolheaded | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| courageous | [brave](../../../traits/instructions/brave.json) | Sonnet 3, Opus 3 | [Gryffindor](../../../traits/instructions/gryffindor.json) | yes |
| cynical | [misanthropic](../../../traits/instructions/misanthropic.json) | Sonnet 2, Opus 3 | [cynical](../../../traits/instructions/cynical.json) | yes |
| debauching | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 2, Opus 3 | [self-indulgent](../../../traits/instructions/self_indulgent.json) | yes |
| diplomatic | [diplomatic](../../../traits/instructions/diplomatic.json) | label | [tactful](../../../traits/instructions/tactful.json) | no |
| disabled | [deaf](../../../traits/instructions/deaf.json) | Sonnet 2, Opus 3 | [mobility impaired](../../../traits/instructions/mobility_impaired.json) | no |
| disgruntled | [bitter](../../../traits/instructions/bitter.json) | Sonnet 3, Opus 3 | [disgruntled](../../../traits/instructions/disgruntled.json) | yes |
| dislikes company | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted](../../../traits/instructions/introverted.json) | yes |
| dismal | [pessimistic](../../../traits/instructions/pessimistic.json) | Sonnet 2, Opus 3 | [melancholic](../../../traits/instructions/melancholic.json) | yes |
| disorganized | [disorganized](../../../traits/instructions/disorganized.json) | label | [careless (HEXACO)](../../../traits/instructions/careless_hexaco.json) | no |
| dispassionate | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [dispassionate](../../../traits/instructions/dispassionate.json) | yes |
| dissocial | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 4 | [introverted (HEXACO)](../../../traits/instructions/introverted_hexaco.json) | yes |
| emotionally composed | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| emotionally even-keeled | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| emotionally even-tempered | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| emotionally muted | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [reserved](../../../traits/instructions/reserved.json) | yes |
| emotionally unflappable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| emotionless | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [dispassionate](../../../traits/instructions/dispassionate.json) | yes |
| enjoys being with people | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| equanimity | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| equanimous | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| even | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| even-keeled | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| even-minded | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| even-tempered | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| extraverted | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| extrovert | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| extroverted | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| faint-hearted | [cowardly](../../../traits/instructions/cowardly.json) | Sonnet 3, Opus 3 | [timid](../../../traits/instructions/timid.json) | yes |
| farsighted | [strategic](../../../traits/instructions/strategic.json) | Sonnet 3, Opus 3 | [long-term oriented](../../../traits/instructions/long_term_oriented.json) | yes |
| fear-restrained | [cowardly](../../../traits/instructions/cowardly.json) | Sonnet 2, Opus 3 | [guarded](../../../traits/instructions/guarded.json) | yes |
| feckless | [irresponsible](../../../traits/instructions/irresponsible.json) | Sonnet 3, Opus 4 | [careless](../../../traits/instructions/careless.json) | yes |
| feminist | [feminist](../../../traits/instructions/feminist.json) | label | [egalitarian](../../../traits/instructions/egalitarian.json) | no |
| financially comfortable | [wealthy](../../../traits/instructions/wealthy.json) | Sonnet 3, Opus 3 | [financially secure](../../../traits/instructions/financially_secure.json) | yes |
| financially stable | [wealthy](../../../traits/instructions/wealthy.json) | Sonnet 2, Opus 3 | [financially secure](../../../traits/instructions/financially_secure.json) | yes |
| financially vulnerable | [poor](../../../traits/instructions/poor.json) | Sonnet 2, Opus 3 | [financially precarious](../../../traits/instructions/financially_precarious.json) | yes |
| flawless | [competent](../../../traits/instructions/competent.json) | Sonnet 2, Opus 3 | [accurate](../../../traits/instructions/accurate.json) | yes |
| flip | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 2, Opus 3 | [flippant](../../../traits/instructions/flippant.json) | yes |
| foresightless | [reactive](../../../traits/instructions/reactive.json) | Sonnet 3, Opus 3 | [impulsive](../../../traits/instructions/impulsive.json) | yes |
| forethoughtful | [strategic](../../../traits/instructions/strategic.json) | Sonnet 2, Opus 3 | [future-oriented](../../../traits/instructions/future_oriented.json) | yes |
| gluttonous | [gluttonous](../../../traits/instructions/gluttonous.json) | label | [self-indulgent](../../../traits/instructions/self_indulgent.json) | yes |
| good-humoured | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 2, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| goofy | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 2, Opus 3 | [goofy](../../../traits/instructions/goofy.json) | yes |
| grave | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 4 | [grave](../../../traits/instructions/grave.json) | yes |
| gregarious | [gregarious](../../../traits/instructions/gregarious.json) | label | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| haphazard | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 3, Opus 3 | [chaotic](../../../traits/instructions/chaotic.json) | no |
| happy-go-lucky | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| hare-hearted | [cowardly](../../../traits/instructions/cowardly.json) | Sonnet 2, Opus 3 | [jumpy](../../../traits/instructions/jumpy.json) | yes |
| hermitish | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 4 | [introverted](../../../traits/instructions/introverted.json) | yes |
| hidebound | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | yes |
| holds back | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [reserved](../../../traits/instructions/reserved.json) | yes |
| hot-brained | [reactive](../../../traits/instructions/reactive.json) | Sonnet 2, Opus 3 | [impulsive](../../../traits/instructions/impulsive.json) | yes |
| hyperanalytical | [analytical](../../../traits/instructions/analytical.json) | Sonnet 3, Opus 3 | [thorough](../../../traits/instructions/thorough.json) | yes |
| hypersensual | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 2, Opus 3 | [hedonistic](../../../traits/instructions/hedonistic.json) | yes |
| imperturbable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| impervious | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [thick-skinned](../../../traits/instructions/thick_skinned.json) | yes |
| impoverished | [poor](../../../traits/instructions/poor.json) | Sonnet 3, Opus 4 | [shabby-genteel](../../../traits/instructions/shabby_genteel.json) | yes |
| impromptu | [reactive](../../../traits/instructions/reactive.json) | Sonnet 2, Opus 3 | [improvisational](../../../traits/instructions/improvisational.json) | yes |
| indigent | [poor](../../../traits/instructions/poor.json) | Sonnet 3, Opus 3 | [financially precarious](../../../traits/instructions/financially_precarious.json) | yes |
| indulgent of bodily pleasures | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 2, Opus 3 | [self-indulgent](../../../traits/instructions/self_indulgent.json) | yes |
| inexcitable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| intellectual | [philosophical](../../../traits/instructions/philosophical.json) | Sonnet 2, Opus 3 | [theoretical](../../../traits/instructions/theoretical.json) | yes |
| intemperate | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 3, Opus 3 | [intemperate](../../../traits/instructions/intemperate.json) | yes |
| introvert | [solitary](../../../traits/instructions/solitary.json) | Sonnet 2, Opus 3 | [introverted](../../../traits/instructions/introverted.json) | yes |
| introverted | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted](../../../traits/instructions/introverted.json) | yes |
| jaunty | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| jocund | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| level | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| light drinker | [abstemious](../../../traits/instructions/abstemious.json) | Sonnet 2, Opus 3 | [teetotaler](../../../traits/instructions/teetotaler.json) | yes |
| light-hearted | [lighthearted](../../../traits/instructions/lighthearted.json) | label, separator-blind | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| light-minded | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 2, Opus 3 | [flippant](../../../traits/instructions/flippant.json) | yes |
| lighthearted | [lighthearted](../../../traits/instructions/lighthearted.json) | label | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| lightsome | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| methodical and orderly | [organized](../../../traits/instructions/organized.json) | Sonnet 3, Opus 3 | [methodical](../../../traits/instructions/methodical.json) | yes |
| mettlesome | [brave](../../../traits/instructions/brave.json) | Sonnet 3, Opus 3 | [Gryffindor](../../../traits/instructions/gryffindor.json) | yes |
| misanthropist | [misanthropic](../../../traits/instructions/misanthropic.json) | Sonnet 3, Opus 4 | [cynical](../../../traits/instructions/cynical.json) | yes |
| monkish | [abstemious](../../../traits/instructions/abstemious.json) | Sonnet 2, Opus 3 | [ascetic](../../../traits/instructions/ascetic.json) | yes |
| moral absolutist | [moral universalist](../../../traits/instructions/moral_universalist.json) | Sonnet 3, Opus 3 | [absolutist](../../../traits/instructions/absolutist.json) | yes |
| neglectful | [irresponsible](../../../traits/instructions/irresponsible.json) | Sonnet 3, Opus 3 | [neglectful](../../../traits/instructions/neglectful.json) | yes |
| non-emotional | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [dispassionate](../../../traits/instructions/dispassionate.json) | yes |
| nonvolatile | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| not very social | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted](../../../traits/instructions/introverted.json) | yes |
| nouveau riche | [wealthy](../../../traits/instructions/wealthy.json) | Sonnet 2, Opus 3 | [nouveau riche](../../../traits/instructions/nouveau_riche.json) | yes |
| obsessed | [body-obsessed](../../../traits/instructions/body_obsessed.json) | Sonnet 3, Opus 3 | [obsessive](../../../traits/instructions/obsessive.json) | no |
| obsessive | [body-obsessed](../../../traits/instructions/body_obsessed.json) | Sonnet 3, Opus 3 | [obsessive](../../../traits/instructions/obsessive.json) | no |
| only follows familiar patterns | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [traditional](../../../traits/instructions/traditional.json) | yes |
| open to new experiences | [open (Big Five)](../../../traits/instructions/open_big_five.json) | Sonnet 3, Opus 3 | [adventurous](../../../traits/instructions/adventurous.json) | yes |
| orderly | [organized](../../../traits/instructions/organized.json) | Sonnet 2, Opus 3 | [orderly](../../../traits/instructions/orderly.json) | yes |
| orderly and tidy | [organized](../../../traits/instructions/organized.json) | Sonnet 3, Opus 3 | [conscientious (HEXACO)](../../../traits/instructions/conscientious_hexaco.json) | yes |
| organized | [organized](../../../traits/instructions/organized.json) | label | [conscientious (HEXACO)](../../../traits/instructions/conscientious_hexaco.json) | yes |
| over-analytic | [analytical](../../../traits/instructions/analytical.json) | Sonnet 2, Opus 3 | [deliberate](../../../traits/instructions/deliberate.json) | yes |
| overeater | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 3, Opus 4 | [self-indulgent](../../../traits/instructions/self_indulgent.json) | yes |
| overindulges in appetites | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 3, Opus 3 | [self-indulgent](../../../traits/instructions/self_indulgent.json) | yes |
| overindulges in consumption | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 3, Opus 4 | [heavy-drinker](../../../traits/instructions/heavy_drinker.json) | yes |
| overserious | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| oversevere | [judgmental](../../../traits/instructions/judgmental.json) | Sonnet 2, Opus 3 | [strict](../../../traits/instructions/strict.json) | yes |
| phlegmatic | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| phlegmatical | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [even-tempered](../../../traits/instructions/even_tempered.json) | yes |
| placid | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [placid](../../../traits/instructions/placid.json) | yes |
| planless | [reactive](../../../traits/instructions/reactive.json) | Sonnet 3, Opus 3 | [improvisational](../../../traits/instructions/improvisational.json) | yes |
| playful and humorous | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [playful](../../../traits/instructions/playful.json) | yes |
| poised | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [composed](../../../traits/instructions/composed.json) | yes |
| poor | [poor](../../../traits/instructions/poor.json) | label | [shabby-genteel](../../../traits/instructions/shabby_genteel.json) | yes |
| prefers company | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| prefers solitude | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted](../../../traits/instructions/introverted.json) | yes |
| pro feminist | [feminist](../../../traits/instructions/feminist.json) | Sonnet 3, Opus 3 | [egalitarian](../../../traits/instructions/egalitarian.json) | no |
| professional | [competent](../../../traits/instructions/competent.json) | Sonnet 2, Opus 3 | [professional](../../../traits/instructions/professional.json) | yes |
| prone to hopelessness | [pessimistic](../../../traits/instructions/pessimistic.json) | Sonnet 2, Opus 3 | [despairing](../../../traits/instructions/despairing.json) | yes |
| prosperous | [wealthy](../../../traits/instructions/wealthy.json) | Sonnet 3, Opus 3 | [financially secure](../../../traits/instructions/financially_secure.json) | yes |
| rankling | [vindictive](../../../traits/instructions/vindictive.json) | Sonnet 2, Opus 3 | [quarrelsome (HEXACO)](../../../traits/instructions/quarrelsome_hexaco.json) | yes |
| resentful | [bitter](../../../traits/instructions/bitter.json) | Sonnet 2, Opus 3 | [resentful](../../../traits/instructions/resentful.json) | yes |
| resentful | [vindictive](../../../traits/instructions/vindictive.json) | Sonnet 2, Opus 3 | [resentful](../../../traits/instructions/resentful.json) | yes |
| responsible | [responsible](../../../traits/instructions/responsible.json) | label | [dependable](../../../traits/instructions/dependable.json) | no |
| restrained | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [restrained](../../../traits/instructions/restrained.json) | yes |
| salty | [bitter](../../../traits/instructions/bitter.json) | Sonnet 2, Opus 3 | [aggrieved](../../../traits/instructions/aggrieved.json) | yes |
| sardonic | [sardonic](../../../traits/instructions/sardonic.json) | label | [ironic](../../../traits/instructions/ironic.json) | yes |
| self denying | [abstemious](../../../traits/instructions/abstemious.json) | Sonnet 3, Opus 3 | [ascetic](../../../traits/instructions/ascetic.json) | yes |
| self focused | [self-absorbed](../../../traits/instructions/self_absorbed.json) | Sonnet 3, Opus 3 | [selfish](../../../traits/instructions/selfish.json) | yes |
| self-regarding | [self-absorbed](../../../traits/instructions/self_absorbed.json) | Sonnet 3, Opus 3 | [selfish](../../../traits/instructions/selfish.json) | yes |
| serious | [earnest](../../../traits/instructions/earnest.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| serious | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| serious-minded | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| silk-stocking | [wealthy](../../../traits/instructions/wealthy.json) | Sonnet 2, Opus 3 | [upper-class](../../../traits/instructions/upper_class.json) | yes |
| skilled | [competent](../../../traits/instructions/competent.json) | Sonnet 3, Opus 3 | [deft](../../../traits/instructions/deft.json) | yes |
| slow to forgive | [vindictive](../../../traits/instructions/vindictive.json) | Sonnet 2, Opus 3 | [unforgiving](../../../traits/instructions/unforgiving.json) | yes |
| sobersides | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| sociable | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| social | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 4 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| socially oriented | [gregarious](../../../traits/instructions/gregarious.json) | Sonnet 3, Opus 3 | [extroverted](../../../traits/instructions/extroverted.json) | yes |
| solemn | [solemn](../../../traits/instructions/solemn.json) | label | [serious](../../../traits/instructions/serious.json) | yes |
| solitary | [solitary](../../../traits/instructions/solitary.json) | label | [introverted](../../../traits/instructions/introverted.json) | yes |
| somber | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 4 | [serious](../../../traits/instructions/serious.json) | yes |
| spiritual-minded | [spiritual](../../../traits/instructions/spiritual.json) | Sonnet 3, Opus 3 | [religious](../../../traits/instructions/religious.json) | yes |
| stable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [stable](../../../traits/instructions/stable.json) | yes |
| stick-in-the-mud | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [unadventurous](../../../traits/instructions/unadventurous.json) | yes |
| stoical | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [rugged](../../../traits/instructions/rugged.json) | yes |
| stolid | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| structureless | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 2, Opus 3 | [stream-of-consciousness](../../../traits/instructions/stream_of_consciousness.json) | no |
| tactful | [diplomatic](../../../traits/instructions/diplomatic.json) | Sonnet 2, Opus 3 | [tactful](../../../traits/instructions/tactful.json) | no |
| tactical | [tactical](../../../traits/instructions/tactical.json) | label | [calculating](../../../traits/instructions/calculating.json) | yes |
| temperate | [abstemious](../../../traits/instructions/abstemious.json) | Sonnet 3, Opus 3 | [temperate](../../../traits/instructions/temperate.json) | yes |
| tempered | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [calm](../../../traits/instructions/calm.json) | yes |
| trifling | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 2, Opus 3 | [flippant](../../../traits/instructions/flippant.json) | yes |
| unaffected | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unbusinesslike | [disorganized](../../../traits/instructions/disorganized.json) | Sonnet 3, Opus 3 | [careless](../../../traits/instructions/careless.json) | no |
| uncharitable | [judgmental](../../../traits/instructions/judgmental.json) | Sonnet 3, Opus 3 | [antagonistic (Big Five)](../../../traits/instructions/antagonistic_big_five.json) | yes |
| unconscientious | [irresponsible](../../../traits/instructions/irresponsible.json) | Sonnet 3, Opus 3 | [careless](../../../traits/instructions/careless.json) | yes |
| undisciplined | [gluttonous](../../../traits/instructions/gluttonous.json) | Sonnet 2, Opus 3 | [impulsive](../../../traits/instructions/impulsive.json) | yes |
| undisturbable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unearnest | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 3 | [flippant](../../../traits/instructions/flippant.json) | yes |
| unemotional | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [dispassionate](../../../traits/instructions/dispassionate.json) | yes |
| unemphatic | [understated](../../../traits/instructions/understated.json) | Sonnet 3, Opus 3 | [unassuming](../../../traits/instructions/unassuming.json) | no |
| unexcitable | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unexplosive | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unfazed | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unfazed by disruptions | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| unforgiving | [vindictive](../../../traits/instructions/vindictive.json) | Sonnet 2, Opus 3 | [unforgiving](../../../traits/instructions/unforgiving.json) | yes |
| ungregarious | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted (Big Five)](../../../traits/instructions/introverted_big_five.json) | yes |
| unimpassionate | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [calm](../../../traits/instructions/calm.json) | yes |
| uninventive | [closed (Big Five)](../../../traits/instructions/closed_big_five.json) | Sonnet 2, Opus 3 | [conventional](../../../traits/instructions/conventional.json) | yes |
| uninvolved with others | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 3 | [introverted (Big Five)](../../../traits/instructions/introverted_big_five.json) | yes |
| unmirthful | [solemn](../../../traits/instructions/solemn.json) | Sonnet 3, Opus 3 | [serious](../../../traits/instructions/serious.json) | yes |
| unpardoning | [vindictive](../../../traits/instructions/vindictive.json) | Sonnet 2, Opus 3 | [unforgiving](../../../traits/instructions/unforgiving.json) | yes |
| unsarcastic | [earnest](../../../traits/instructions/earnest.json) | Sonnet 3, Opus 3 | [sincere](../../../traits/instructions/sincere.json) | yes |
| unsocial | [solitary](../../../traits/instructions/solitary.json) | Sonnet 3, Opus 4 | [introverted](../../../traits/instructions/introverted.json) | yes |
| unsolemn | [lighthearted](../../../traits/instructions/lighthearted.json) | Sonnet 3, Opus 4 | [flippant](../../../traits/instructions/flippant.json) | yes |
| unstormy | [stoic](../../../traits/instructions/stoic.json) | Sonnet 2, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |
| untaught | [unschooled](../../../traits/instructions/unschooled.json) | Sonnet 3, Opus 3 | [uneducated](../../../traits/instructions/uneducated.json) | yes |
| untheatrical | [understated](../../../traits/instructions/understated.json) | Sonnet 3, Opus 3 | [unassuming](../../../traits/instructions/unassuming.json) | no |
| upbeat | [optimistic](../../../traits/instructions/optimistic.json) | Sonnet 3, Opus 3 | [cheerful](../../../traits/instructions/cheerful.json) | yes |
| well-balanced | [stoic](../../../traits/instructions/stoic.json) | Sonnet 3, Opus 3 | [unflappable](../../../traits/instructions/unflappable.json) | yes |

### Not recovered (34)

[achiever (Bartle)](../../../traits/instructions/achiever_bartle.json), [Aries](../../../traits/instructions/aries.json), [black-haired](../../../traits/instructions/black_haired.json), [blood type AB](../../../traits/instructions/blood_type_ab.json), [body-obsessed](../../../traits/instructions/body_obsessed.json), [Cancer](../../../traits/instructions/cancer.json), [cat-person](../../../traits/instructions/cat_person.json), [deaf](../../../traits/instructions/deaf.json), [diplomatic](../../../traits/instructions/diplomatic.json), [disorganized](../../../traits/instructions/disorganized.json), [dog-person](../../../traits/instructions/dog_person.json), [eastern hemisphere](../../../traits/instructions/eastern_hemisphere.json), [ends justify means](../../../traits/instructions/ends_justify_means.json), [Enneagram 3](../../../traits/instructions/enneagram_3.json), [Enneagram 6](../../../traits/instructions/enneagram_6.json), [exploratory](../../../traits/instructions/exploratory.json), [fat](../../../traits/instructions/fat.json), [fearful-avoidant attachment](../../../traits/instructions/fearful_avoidant_attachment.json), [female](../../../traits/instructions/female.json), [feminist](../../../traits/instructions/feminist.json), [good-looking](../../../traits/instructions/good_looking.json), [homeowner](../../../traits/instructions/homeowner.json), [Indigenous American](../../../traits/instructions/indigenous_american.json), [INFP (MBTI)](../../../traits/instructions/infp_mbti.json), [killer (Bartle)](../../../traits/instructions/killer_bartle.json), [Leo](../../../traits/instructions/leo.json), [moral relativist](../../../traits/instructions/moral_relativist.json), [pensive](../../../traits/instructions/pensive.json), [performance-oriented](../../../traits/instructions/performance_oriented.json), [responsible](../../../traits/instructions/responsible.json), [suburban](../../../traits/instructions/suburban.json), [thin](../../../traits/instructions/thin.json), [understated](../../../traits/instructions/understated.json), [western hemisphere](../../../traits/instructions/western_hemisphere.json)

