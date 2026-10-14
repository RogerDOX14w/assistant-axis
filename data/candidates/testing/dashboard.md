# Generator dashboard (2026-10-14)

Plan 13's one table per generator ([coding_plan_13_generator_testing.md](../../../reports/trait_gap_generation/coding_plan_13_generator_testing.md)), built by [generator_dashboard.py](../../../data_analysis/gap_generation/generator_dashboard.py) from what the platform recorded; nothing here was generated or judged.  Terms are defined in the [glossary](../../../reports/trait_gap_generation/glossary.md).  Every figure is in [dashboard.json](./dashboard.json); the parts are [independence.json](./independence.json), [review_rates.json](./review_rates.json), [repetition.json](./repetition.json), [concepts.json](./concepts.json), [estimates.json](./estimates.json) and [simulation.json](./simulation.json).

Inputs: the registry data/candidates/registry.jsonl, the review graph [review_traits_all_2](../../../data/candidates/review/review_traits_all_2/graph.json), the review logs of review_states_v4, review_tda_1 (figures that lag review are as of 2026-10-11T21:21:26+00:00), and the harness batches rec_antonym_check_pilot_1, rec_censuses_2026-10-08-pilot, rec_pooled_1, rec_roget_2026-10-08-pilot, rec_testing_paraphrase_set, rec_wn_clusters_2026-10-08-pilot.

## The table

| generator | class | mechanism | candidates | M1 trait | M3 kept / covered (exact label) | cost $ | pre-handled (3 / 4) | review decided (accepted) | promote share, group (term) | string recall | negatives | recall (strict, pair) | expected accepted in minutes | accepted per review-minute | accepted per $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| censuses | independent | lexicon | 8,007 | 5,139 | 2,872 / 2,243 (468) | 129.15 | 7% / 2% | 174 (34) | 51% (21%) | 475 (51.0%) | 45 | 49.8% (36.7%, 41.9%) | 988.7 in 892 (blended: 430 in 1,034) | 1.11 (0.42 blended) | 7.7 (3.3 blended) |
| roget | seeded | lexicon | 576 | 349 | 243 / 101 (2) | 16.06 | 8% / 2% | 18 (4) | 51% (21%), borrowed | 3 (0.3%) | 0 | 9.9% (2.6%, 7.8%) harness side | 99.3 in 74 (blended: 35 in 85) | 1.35 (0.42 blended) | 6.2 (2.2 blended) |
| wn_clusters | independent/seeded | lexicon | 647 | 578 | 277 / 300 (2) | 8.07 | 11% / 4% | 27 (3) | 51% (21%), borrowed | 7 (0.8%) | 0 | 11.5% (5.8%, 7.8%) harness side | 104.0 in 81 (blended: 38 in 92) | 1.28 (0.42 blended) | 12.9 (4.7 blended) |
| &nbsp;&nbsp;wn_clusters/closure | independent | lexicon | 553 | 504 | 235 kept | | | | | | | | | | |
| &nbsp;&nbsp;wn_clusters/antonym | seeded | lexicon | 108 | 85 | 46 kept | | | | | | | | | | |
| ipip | independent | ipip | 853 | 830 | 409 / 421 (63) | 21.76 | 5% / 1% | 4 (0) | 51% (21%), borrowed | 70 (7.5%) | 0 | 21.4% (8.9%, 12.0%) | 178.1 in 131 (blended: 66 in 159) | 1.36 (0.42 blended) | 8.2 (3.0 blended) |
| base_model | independent | base_model | 1,541 | 1,355 | 517 / 836 (354) | 12.55 | 10% / 4% | 59 (6) | 40% (10%) | 352 (37.8%) | 30 | 35.1% (28.8%, 16.8%) | 146.4 in 156 (blended: 71 in 170) | 0.94 (0.42 blended) | 11.7 (5.7 blended) |
| masked_lm | independent | masked_lm | 436 | 329 | 157 / 170 (38) | 5.79 | 9% / 3% | 3 (1) | 51% (21%), borrowed | 43 (4.6%) | 4 | 8.4% (4.7%, 7.9%) | 16.0 in 11 (blended: 5 in 13) | 1.46 (0.42 blended) | 2.8 (0.9 blended) |
| alignment_sweep | separate_population | alignment | 836 | 813 | 626 / 187 (40) | 44.88 | 9% / 1% | 3 (2) | 51% (21%), borrowed | 39 (4.2%) | 3 | 5.8% (2.6%, 11.5%) | 244.5 in 198 (blended: 97 in 233) | 1.23 (0.42 blended) | 5.5 (2.2 blended) |
| antonym_check | seeded | corpus | 405 | 374 | 135 / 239 (4) | 23.17 | 7% / 1% | 0 (0) | 51% (21%), borrowed | 17 (1.8%) | 0 | 13.1% (4.7%, 8.9%) harness side | 60.7 in 44 (blended: 22 in 52) | 1.39 (0.42 blended) | 2.6 (0.9 blended) |
| structural | seeded | corpus | 499 | 478 | 163 / 315 (162) | 6.29 | 12% / 5% | 23 (5) | 51% (21%), borrowed | 165 (17.7%) | 11 | 17.3% (13.6%, 9.4%) harness side | 40.7 in 31 (blended: 14 in 33) | 1.29 (0.42 blended) | 6.5 (2.2 blended) |
| states_pass | not_a_generator |  | 460 | 373 | 166 / 207 (83) | 2.33 | 5% / 3% | 7 (4) | n/a | 90 (9.7%) | 9 | n/a | n/a in 53 | n/a | n/a |
| m1_validation | not_a_generator |  | 150 | 108 | 58 / 43 (0) | 7.17 | 5% / 2% | 0 (0) | n/a | 1 (0.1%) | 0 | n/a | n/a in 19 | n/a | n/a |
| manual | not_a_generator |  | 5 | 5 | 3 / 2 (0) | 0.05 | 33% / 33% | 0 (0) | n/a | 0 (0.0%) | 5 | n/a | n/a in 1 | n/a | n/a |
| noun_relabel | not_a_generator |  | 78 | 61 | 41 / 20 (0) | 0.67 | n/a / n/a | 1 (1) | 51% (21%), borrowed | 0 (0.0%) | 0 | n/a | 0.0 in 0 (blended: 0 in 0) | n/a (n/a blended) | 0.0 (0.0 blended) |

Any generator names 529 of 932 corpus stems by string (56.8%).

**Reading the columns.**  *Pre-handled*: undecided kept terms with a 3-edge (4-edge) to a term review has decided; they cost no review-minute.  *Promote share*: promote resolutions over resolved groups (decision 3), per term in brackets; *borrowed*: under 50 decided terms, the pooled share.  *String recall*: corpus stems the generator's rows name, separator-blind, of the corpus.  *Negatives*: words Roger turned down in the seed queue that the generator proposed again.  *Recall*: the harness's mean recall over its kept candidates (n/a: no harness batch covers it yet), the strict column at cut-off 4 and pair recovery beside it; *harness side*: a seeded generator, no generator-side hiding.  *Expected accepted*: the groups its undecided, not pre-handled kept terms form times the per-group promote share; the minutes from the measured times per shape (a term in any proposed group is priced as a group member, the rest as singletons).  *Blended*, in brackets: the same terms at the review's measured overall rates (terms and accepted terms per active minute), the other end of the range.  The per-shape figure leans on the share at which singletons were promoted, measured on about forty resolved singletons (a 95% interval of roughly 0.37-0.66) that the app surfaced first in the TDA batch; the generators' remaining singletons need not resemble them.

## Recall from the recorded harness batches

Each batch tested one pilot run, at seed 0 only, under the rule sets before rule set 3 (2026-10-08); the decision-1 pooled batch, when it is run, fills the table's recall column for every generator.

| generator | batch | scope | recall (mean over seeds) | strict, at 4 | pair recovery | precision | false-cover candidates |
|---|---|---|---|---|---|---|---|
| censuses | [rec_censuses_2026-10-08-pilot](../../../data/candidates/recovery/rec_censuses_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 22.9% | 13.2% | 14.5% | 9.3% | 8 |
| censuses | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 49.8% | 36.7% | 41.9% | 5.6% | 131.5 |
| roget | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 9.9% | 2.6% | 7.8% | 4.5% | 4.5 |
| roget | [rec_roget_2026-10-08-pilot](../../../data/candidates/recovery/rec_roget_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 1.2% | 0.0% | 6.0% | 1.3% | 0 |
| wn_clusters | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 11.5% | 5.8% | 7.8% | 8.2% | 19 |
| wn_clusters | [rec_wn_clusters_2026-10-08-pilot](../../../data/candidates/recovery/rec_wn_clusters_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 7.2% | 0.0% | 4.8% | 12.5% | 1 |
| ipip | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 21.4% | 8.9% | 12.0% | 7.1% | 30.5 |
| base_model | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 35.1% | 28.8% | 16.8% | 11.0% | 50.5 |
| masked_lm | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 8.4% | 4.7% | 7.9% | 9.7% | 9 |
| alignment_sweep | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 5.8% | 2.6% | 11.5% | 0.9% | 5.5 |
| antonym_check | [rec_antonym_check_pilot_1](../../../data/candidates/recovery/rec_antonym_check_pilot_1/recovery_report.md) | run pilot_1 | 15.7% | 4.8% | 20.5% | 10.5% | 16 |
| antonym_check | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 13.1% | 4.7% | 8.9% | 9.6% | 17.5 |
| structural | [rec_pooled_1](../../../data/candidates/recovery/rec_pooled_1/recovery_report.md) | pooled | 17.3% | 13.6% | 9.4% | 11.8% | 26 |

## Cost by stage (USD)

| generator | generator | M1 | M3 | R1 share | harness | total |
|---|---|---|---|---|---|---|
| censuses | 0.00 | 25.71 | 30.73 | 32.98 | 39.73 | 129.15 |
| roget | 6.38 | 2.31 | 2.32 | 2.05 | 3.01 | 16.06 |
| wn_clusters | 0.00 | 1.17 | 1.95 | 1.81 | 3.15 | 8.07 |
| ipip | 2.93 | 3.83 | 5.04 | 4.20 | 5.74 | 21.76 |
| base_model | 0.05 | 1.60 | 2.30 | 3.55 | 5.05 | 12.55 |
| masked_lm | 0.00 | 1.74 | 1.95 | 0.19 | 1.92 | 5.79 |
| alignment_sweep | 18.20 | 7.86 | 6.30 | 6.60 | 5.92 | 44.88 |
| antonym_check | 0.00 | 4.66 | 11.31 | 0.80 | 6.39 | 23.17 |
| structural | 2.47 | 0.76 | 1.04 | 0.51 | 1.51 | 6.29 |
| states_pass | 0.00 | 1.25 | 1.08 | 0.00 | n/a | 2.33 |
| m1_validation | 0.00 | 2.65 | 3.90 | 0.43 | 0.18 | 7.17 |
| manual | 0.00 | 0.00 | 0.03 | 0.01 | 0.01 | 0.05 |
| noun_relabel | 0.00 | 0.18 | 0.17 | 0.17 | 0.15 | 0.67 |

Read 270 cost records, $404.29 in all: $279.25 attributed to generator runs, $125.04 not attributed (calibration, development probes, corpus regions, the passes' own calls).

## Review rate

Pooled over review_tda_1: 204 terms in 84.1 active minutes, 2.43 terms a minute; a singleton 14.6 s, a grouped term 25.4 s.  Left out as too small: review_states_v4.  Pooled promote share: per group 51.5%, per term 20.8%; by shape {"singleton": {"resolved": 40, "promoted": 20, "terms": 40, "extended": 12, "share": 0.5}, "multi": {"resolved": 28, "promoted": 15, "terms": 97, "extended": 55, "share": 0.5357}}; holding-list passes left out of the share: review_states_v4.

## Concept units (decision 2: Roger names the headline)

| unit | units | singletons | largest | kept together | one concept | hard negatives joined | Chao2 (three occasions) | Chao2 (four, with the alignment sweep) |
|---|---|---|---|---|---|---|---|---|
| strict components (4) | 3,373 | 2,944 | 25 | 39% | 76% | 19 of 147 | 8,345 (7,669-9,116) | 11,400 |
| grown across 3-links, density >= 0.67 | 2,477 | 1,640 | 27 | 53% | 77% | 27 of 147 | 4,948 (4,564-5,391) | 6,066 |
| the same, density >= 0.5 | 2,098 | 1,402 | 32 | 63% | 78% | 39 of 147 | 3,928 (3,621-4,287) | 4,846 |
| the same, density >= 0.8 | 2,552 | 1,680 | 25 | 51% | 80% | 24 of 147 | 5,017 (4,640-5,451) | 6,196 |
| components at 3 (chains unbroken) | 1,719 | 1,334 | 1138 | 99% | 7% | 136 of 147 | 4,125 (3,681-4,658) | 5,486 |

*Kept together*: of the pairs of decided candidates Roger made one concept, the share one unit holds; *one concept*: of the decided pairs sharing a unit, the share Roger made one concept; *hard negatives*: pairs he marked distinct or dropped from a group the graph had proposed.  Chao2 over the three occasions of the main population (the lexicon walks, IPIP, the base model; the masked LM has no run yet); the alignment sweep is a separate population and is printed apart.

Assumptions of every estimate (printed each time):

- The population is closed: the set of concepts does not change while the occasions run.
- Equal catchability is false here: some concepts are much easier for every generator to find, so N̂ is low.
- Independent occasions are false between LLM-based mechanisms: they tend to find the same concepts, so N̂ is low.
- N̂ is a lower bound on what generators of these kinds can reach.

### Estimates at the strict unit (components_4)

| occasions | concepts seen | N̂ (95% interval) | coverage | left (N̂ minus seen) |
|---|---|---|---|---|
| lexicon, IPIP, base model | 2,821 | 8,345 (7,669-9,116) | 28% | 5,524 |
| the same and the alignment sweep | 3,308 | 11,400 (10,453-12,472) | 27% | 8,092 |

With the corpus as an occasion (its 932 traits a sample of all trait concepts; a generator catches a corpus trait when one of its rows was covered by it): Chao2 N̂ 8,723 (8,185-9,326), so about **7,791 concepts not in the corpus**.  Chapman of the corpus with each mechanism:

| mechanism | concepts it caught | of them corpus traits | N̂ (95% interval) | left |
|---|---|---|---|---|
| lexicon | 3,072 | 594 | 4,818 (4,624-5,043) | 3,886 |
| ipip | 579 | 220 | 2,448 (2,247-2,691) | 1,516 |
| base_model | 842 | 400 | 1,960 (1,865-2,075) | 1,028 |
| masked_lm | 150 | 112 | 1,246 (1,157-1,376) | 314 |

Chapman between mechanisms (new concepts only):

| pair | n1 | n2 | shared | N̂ (95% interval) |
|---|---|---|---|---|
| lexicon x ipip | 2,478 | 359 | 72 | 12,224 (10,074-15,007) |
| lexicon x base_model | 2,478 | 442 | 387 | 2,829 (2,751-2,935) |
| lexicon x masked_lm | 2,478 | 38 | 31 | 3,020 (2,731-3,651) |
| ipip x base_model | 359 | 442 | 39 | 3,986 (3,062-5,282) |
| ipip x masked_lm | 359 | 38 | 7 | 1,754 (1,056-3,182) |
| base_model x masked_lm | 442 | 38 | 19 | 863 (679-1,202) |

Accumulation per mechanism (every candidate it emitted, in its runs' order; a candidate that is not a kept term adds no concept):

| mechanism | candidates emitted | new concepts | end slope (concepts per candidate, last tenth) | projected at twice the output |
|---|---|---|---|---|
| lexicon | 10,082 | 2,402 | 0.069 | 3,746 |
| ipip | 1,285 | 359 | 0.293 | 472 |
| base_model | 2,007 | 436 | 0.329 | 686 |
| alignment | 865 | 543 | 0.562 | 990 |

The alignment sweep as its own population (its papers run and variant B as the occasions, overlap by concept unit): 278 and 51 concepts, 14 shared, Chapman N̂ 966 (678-1,483).

### Estimates at the grown unit (grown_3, density >= 0.67)

| occasions | concepts seen | N̂ (95% interval) | coverage | left (N̂ minus seen) |
|---|---|---|---|---|
| lexicon, IPIP, base model | 2,102 | 4,948 (4,564-5,391) | 36% | 2,846 |
| the same and the alignment sweep | 2,427 | 6,066 (5,603-6,596) | 37% | 3,639 |

With the corpus as an occasion (its 932 traits a sample of all trait concepts; a generator catches a corpus trait when one of its rows was covered by it): Chao2 N̂ 5,795 (5,466-6,168), so about **4,863 concepts not in the corpus**.  Chapman of the corpus with each mechanism:

| mechanism | concepts it caught | of them corpus traits | N̂ (95% interval) | left |
|---|---|---|---|---|
| lexicon | 2,462 | 594 | 3,861 (3,711-4,036) | 2,929 |
| ipip | 541 | 220 | 2,287 (2,104-2,510) | 1,355 |
| base_model | 784 | 400 | 1,825 (1,740-1,929) | 893 |
| masked_lm | 150 | 112 | 1,246 (1,157-1,376) | 314 |

Chapman between mechanisms (new concepts only):

| pair | n1 | n2 | shared | N̂ (95% interval) |
|---|---|---|---|---|
| lexicon x ipip | 1,868 | 321 | 116 | 5,143 (4,505-5,947) |
| lexicon x base_model | 1,868 | 384 | 354 | 2,026 (1,983-2,091) |
| lexicon x masked_lm | 1,868 | 38 | 34 | 2,082 (1,952-2,424) |
| ipip x base_model | 321 | 384 | 53 | 2,295 (1,856-2,893) |
| ipip x masked_lm | 321 | 38 | 9 | 1,255 (810-2,128) |
| base_model x masked_lm | 384 | 38 | 21 | 682 (552-923) |

Accumulation per mechanism (every candidate it emitted, in its runs' order; a candidate that is not a kept term adds no concept):

| mechanism | candidates emitted | new concepts | end slope (concepts per candidate, last tenth) | projected at twice the output |
|---|---|---|---|---|
| lexicon | 10,082 | 1,810 | 0.045 | 2,528 |
| ipip | 1,285 | 321 | 0.218 | 395 |
| base_model | 2,007 | 379 | 0.266 | 555 |
| alignment | 865 | 445 | 0.405 | 739 |

The alignment sweep as its own population (its papers run and variant B as the occasions, overlap by concept unit): 231 and 49 concepts, 24 shared, Chapman N̂ 463 (374-620).

## Reading lists for decision 2 (twenty units of each kind, seeded, two or more members)

**components_4**

1. (2) embellishes the truth, embellishing
2. (2) self-educated, self-taught
3. (6) fancy-sick, hypochondriac, prone to bodily worry, prone to somatic worry, valetudinarian, valetudinary
4. (12) aggravating, annoying, bothering, bothersome, exasperating, galling, grating, irritating, nagging, pestering, plaguing, plaguy
5. (7) comminatory, frightening, frighting, minacious, minatory, scary, threatening
6. (2) horrendous, horrific
7. (5) haughty, snob, snobbish, snooty, stuck-up
8. (2) exhausting, taxing
9. (2) starchy, stiff
10. (2) unknowable, unsoundable
11. (10) covert misleading, covertly deceptive, deceives under cover, double-dealer, double-faced, double-hearted, duplicitous, duplicity, false-faced, janus-faced
12. (6) habitually dishonest, liar, lying, mendacious, prone to lying, untruthful
13. (2) distrusts authority, distrusts authority figures
14. (3) keeps its word, keeps their word, word-bound
15. (13) charmer, charming, delectable, delicious, delightful, enchanting, likeable, lovable, lovesome, pleasant, pleasing, pleasurable, scrumptious
16. (2) holds to ideals, scrupulously principled
17. (5) beyond control, incontrollable, uncontrollable, uncurbable, unrestrainable
18. (2) conquerable, subduable
19. (2) self-degrading, self-disparaging
20. (3) autonomous, self-determining, self-governing

**grown_3**

1. (2) distressing, upsetting
2. (2) self-degrading, self-disparaging
3. (2) elfish, roguish
4. (4) affirmative, affirming, assentient, nodding
5. (2) commandeering, seizes control
6. (2) grinding, unremitting
7. (2) foul, immoral
8. (2) drops values under pressure, weak
9. (3) stays transparent with developers, transparent under oversight, transparent with overseers
10. (2) corny, hokey
11. (2) foo-foo, pretty-pretty
12. (3) derisive, jeering, mocking
13. (2) intelligible, luculent
14. (8) chattering, chatty, garrulous, loquacious, overtalkative, talkative, yammering, yappy
15. (2) go-getter, motivated
16. (3) beloved, dear, loved
17. (2) confusing, incomprehensible
18. (7) bemusing, bewildering, confounding, inexplicable, nonplussing, perplexing, puzzling
19. (2) self-actualized, self-realising
20. (3) attuned to emotional atmosphere, attuned to others' moods, emotionally attuned

## The estimators on simulated data

| scenario | sigma | rho | estimator | mean N̂ | bias | interval coverage | leave-one-out spread |
|---|---|---|---|---|---|---|---|
| equal_independent | 0 | 0 | chao2 | 1,982 | -0.9% | 96% | 13.8% |
| equal_independent | 0 | 0 | chapman_01 | 1,979 | -1.1% | 92% | n/a |
| heterogeneous_independent | 1 | 0 | chao2 | 1,033 | -48.4% | 0% | 7.7% |
| heterogeneous_independent | 1 | 0 | chapman_01 | 779 | -61.1% | 0% | n/a |
| heterogeneous_correlated | 1 | 0.3 | chao2 | 944 | -52.8% | 0% | 13.8% |
| heterogeneous_correlated | 1 | 0.3 | chapman_01 | 783 | -60.8% | 0% | n/a |

True N = 2,000; 4 occasions, marginal catch rate 0.15; 200 replicates per scenario, seed 0; Chapman on occasions 0 and 1; rho loads on occasions 1, 2, 3.  Bias is the mean of (N̂ - N) / N; coverage the share of 95% intervals containing N; the spread is (max - min) / N̂ over the Chao2 estimates with one occasion left out.


