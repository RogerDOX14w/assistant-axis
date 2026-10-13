# Generator dashboard (2026-10-13)

Plan 13's one table per generator ([coding_plan_13_generator_testing.md](../../../reports/trait_gap_generation/coding_plan_13_generator_testing.md)), built by [generator_dashboard.py](../../../data_analysis/gap_generation/generator_dashboard.py) from what the platform recorded; nothing here was generated or judged.  Terms are defined in the [glossary](../../../reports/trait_gap_generation/glossary.md).  Every figure is in [dashboard.json](./dashboard.json); the parts are [independence.json](./independence.json), [review_rates.json](./review_rates.json), [repetition.json](./repetition.json), [concepts.json](./concepts.json), [estimates.json](./estimates.json) and [simulation.json](./simulation.json).

Inputs: the registry data/candidates/registry.jsonl, the review graph [review_traits_all_2](../../../data/candidates/review/review_traits_all_2/graph.json), the review logs of review_states_v4, review_tda_1 (figures that lag review are as of 2026-10-11T21:21:26+00:00), and the harness batches rec_antonym_check_pilot_1, rec_censuses_2026-10-08-pilot, rec_roget_2026-10-08-pilot, rec_wn_clusters_2026-10-08-pilot.

## The table

| generator | class | mechanism | candidates | M1 trait | M3 kept / covered (exact label) | cost $ | pre-handled (3 / 4) | review decided (accepted) | promote share, group (term) | string recall | negatives | recall (strict, pair) | expected accepted in minutes | accepted per review-minute | accepted per $ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| censuses | independent | lexicon | 8,007 | 5,139 | 2,872 / 2,243 (468) | 94.02 | 7% / 2% | 174 (34) | 54% (21%) | 475 (51.0%) | 45 | n/a | 1,023.3 in 783 | 1.31 | 10.9 |
| roget | seeded | lexicon | 576 | 349 | 243 / 101 (2) | 14.32 | 8% / 2% | 18 (4) | 54% (21%), borrowed | 3 (0.3%) | 0 | n/a | 103.3 in 54 | 1.90 | 7.2 |
| wn_clusters | independent/seeded | lexicon | 647 | 578 | 277 / 300 (2) | 6.02 | 11% / 4% | 27 (3) | 54% (21%), borrowed | 7 (0.8%) | 0 | n/a | 108.1 in 61 | 1.77 | 18.0 |
| &nbsp;&nbsp;wn_clusters/closure | independent | lexicon | 553 | 504 | 235 kept | | | | | | | | | | |
| &nbsp;&nbsp;wn_clusters/antonym | seeded | lexicon | 108 | 85 | 46 kept | | | | | | | | | | |
| ipip | independent | ipip | 514 | 498 | 240 / 258 (51) | 11.07 | 4% / 1% | 3 (0) | 54% (21%), borrowed | 55 (5.9%) | 0 | n/a | 116.1 in 56 | 2.06 | 10.5 |
| base_model | independent | base_model | 1,541 | 1,355 | 517 / 836 (354) | 7.48 | 10% / 4% | 59 (6) | 40% (10%) | 352 (37.8%) | 30 | n/a | 146.4 in 117 | 1.25 | 19.6 |
| alignment_sweep | separate_population | alignment | 464 | 455 | 362 / 93 (21) | 34.39 | 9% / 1% | 2 (2) | 54% (21%), borrowed | 20 (2.1%) | 1 | n/a | 148.3 in 95 | 1.56 | 4.3 |
| antonym_check | seeded | corpus | 405 | 374 | 135 / 239 (4) | 21.78 | 7% / 1% | 0 (0) | 54% (21%), borrowed | 17 (1.8%) | 0 | n/a | 63.7 in 33 | 1.92 | 2.9 |
| states_pass | not_a_generator |  | 459 | 372 | 165 / 207 (83) | 2.31 | 5% / 3% | 7 (4) | n/a | 90 (9.7%) | 9 | n/a | n/a in 40 | n/a | n/a |
| m1_validation | not_a_generator |  | 150 | 108 | 58 / 43 (0) | 6.87 | 5% / 2% | 0 (0) | n/a | 1 (0.1%) | 0 | n/a | n/a in 14 | n/a | n/a |
| manual | not_a_generator |  | 5 | 5 | 3 / 2 (0) | 0.05 | 33% / 33% | 0 (0) | n/a | 0 (0.0%) | 5 | n/a | n/a in 0 | n/a | n/a |

Any generator names 517 of 932 corpus stems by string (55.5%).

**Reading the columns.**  *Pre-handled*: undecided kept terms with a 3-edge (4-edge) to a term review has decided; they cost no review-minute.  *Promote share*: promote resolutions over resolved groups (decision 3), per term in brackets; *borrowed*: under 50 decided terms, the pooled share.  *String recall*: corpus stems the generator's rows name, separator-blind, of the corpus.  *Negatives*: words Roger turned down in the seed queue that the generator proposed again.  *Recall*: the harness's mean recall over its kept candidates (n/a: no harness batch covers it yet), the strict column at cut-off 4 and pair recovery beside it; *harness side*: a seeded generator, no generator-side hiding.  *Expected accepted*: the groups its undecided, not pre-handled kept terms form times the per-group promote share; the minutes from the measured times per shape.

## Recall from the recorded harness batches

Each batch tested one pilot run, at seed 0 only, under the rule sets before rule set 3 (2026-10-08); the decision-1 pooled batch, when it is run, fills the table's recall column for every generator.

| generator | batch | scope | recall (mean over seeds) | strict, at 4 | pair recovery | precision | false-cover candidates |
|---|---|---|---|---|---|---|---|
| censuses | [rec_censuses_2026-10-08-pilot](../../../data/candidates/recovery/rec_censuses_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 22.9% | 13.2% | 14.5% | 9.3% | 8 |
| roget | [rec_roget_2026-10-08-pilot](../../../data/candidates/recovery/rec_roget_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 1.2% | 0.0% | 6.0% | 1.3% | 0 |
| wn_clusters | [rec_wn_clusters_2026-10-08-pilot](../../../data/candidates/recovery/rec_wn_clusters_2026-10-08-pilot/recovery_report.md) | run 2026-10-08-pilot | 7.2% | 0.0% | 4.8% | 12.5% | 1 |
| antonym_check | [rec_antonym_check_pilot_1](../../../data/candidates/recovery/rec_antonym_check_pilot_1/recovery_report.md) | run pilot_1 | 15.7% | 4.8% | 20.5% | 10.5% | 16 |

## Cost by stage (USD)

| generator | generator | M1 | M3 | R1 share | harness | total |
|---|---|---|---|---|---|---|
| censuses | 0.00 | 25.71 | 30.76 | 30.92 | 6.63 | 94.02 |
| roget | 6.38 | 2.31 | 2.33 | 1.95 | 1.36 | 14.32 |
| wn_clusters | 0.00 | 1.17 | 1.96 | 1.76 | 1.13 | 6.02 |
| ipip | 2.93 | 2.59 | 3.37 | 2.18 | n/a | 11.07 |
| base_model | 0.05 | 1.60 | 2.36 | 3.47 | n/a | 7.48 |
| alignment_sweep | 18.20 | 7.03 | 5.65 | 3.51 | n/a | 34.39 |
| antonym_check | 0.00 | 4.66 | 11.49 | 0.76 | 4.87 | 21.78 |
| states_pass | 0.00 | 1.25 | 1.06 | 0.00 | n/a | 2.31 |
| m1_validation | 0.00 | 2.65 | 3.82 | 0.39 | n/a | 6.87 |
| manual | 0.00 | 0.00 | 0.04 | 0.01 | n/a | 0.05 |

Read 227 cost records, $317.54 in all: $198.31 attributed to generator runs, $119.23 not attributed (calibration, development probes, corpus regions, the passes' own calls).

## Review rate

Pooled over review_tda_1: 204 terms in 84.1 active minutes, 2.43 terms a minute; a singleton 14.6 s, a grouped term 25.4 s.  Left out as too small: review_states_v4.  Pooled promote share: per group 53.5%, per term 20.8%; by shape {"singleton": {"resolved": 42, "promoted": 22, "terms": 42, "extended": 12, "share": 0.5238}, "multi": {"resolved": 29, "promoted": 16, "terms": 99, "extended": 55, "share": 0.5517}}.

## Concept units (decision 2: Roger names the headline)

| unit | units | singletons | largest | kept together | one concept | hard negatives joined | Chao2 (three occasions) | Chao2 (four, with the alignment sweep) |
|---|---|---|---|---|---|---|---|---|
| strict components (4) | 3,065 | 2,691 | 21 | 39% | 76% | 19 of 147 | 7,344 (6,769-8,001) | 9,391 |
| grown across 3-links, density >= 0.67 | 2,258 | 1,514 | 26 | 54% | 76% | 29 of 147 | 4,412 (4,086-4,790) | 5,234 |
| the same, density >= 0.5 | 1,935 | 1,306 | 30 | 64% | 77% | 44 of 147 | 3,621 (3,347-3,940) | 4,295 |
| the same, density >= 0.8 | 2,329 | 1,552 | 21 | 51% | 79% | 28 of 147 | 4,548 (4,217-4,930) | 5,421 |
| components at 3 (chains unbroken) | 1,585 | 1,238 | 1028 | 99% | 7% | 136 of 147 | 3,798 (3,399-4,277) | 4,652 |

*Kept together*: of the pairs of decided candidates Roger made one concept, the share one unit holds; *one concept*: of the decided pairs sharing a unit, the share Roger made one concept; *hard negatives*: pairs he marked distinct or dropped from a group the graph had proposed.  Chao2 over the three occasions of the main population (the lexicon walks, IPIP, the base model; the masked LM has no run yet); the alignment sweep is a separate population and is printed apart.

Assumptions of every estimate (printed each time):

- The population is closed: the set of concepts does not change while the occasions run.
- Equal catchability is false here: some concepts are much easier for every generator to find, so N̂ is low.
- Independent occasions are false between LLM-based mechanisms: they tend to find the same concepts, so N̂ is low.
- N̂ is a lower bound on what generators of these kinds can reach.

### Estimates at the strict unit (components_4)

| occasions | concepts seen | N̂ (95% interval) | coverage | left (N̂ minus seen) |
|---|---|---|---|---|
| lexicon, IPIP, base model | 2,710 | 7,344 (6,769-8,001) | 27% | 4,634 |
| the same and the alignment sweep | 3,000 | 9,391 (8,622-10,265) | 26% | 6,391 |

With the corpus as an occasion (its 932 traits a sample of all trait concepts; a generator catches a corpus trait when one of its rows was covered by it): Chao2 N̂ 8,022 (7,545-8,558), so about **7,090 concepts not in the corpus**.  Chapman of the corpus with each mechanism:

| mechanism | concepts it caught | of them corpus traits | N̂ (95% interval) | left |
|---|---|---|---|---|
| lexicon | 3,072 | 594 | 4,818 (4,624-5,043) | 3,886 |
| ipip | 415 | 183 | 2,108 (1,926-2,335) | 1,176 |
| base_model | 843 | 400 | 1,963 (1,867-2,077) | 1,031 |

Chapman between mechanisms (new concepts only):

| pair | n1 | n2 | shared | N̂ (95% interval) |
|---|---|---|---|---|
| lexicon x ipip | 2,478 | 232 | 57 | 9,958 (8,085-12,476) |
| lexicon x base_model | 2,478 | 443 | 386 | 2,843 (2,763-2,951) |
| ipip x base_model | 232 | 443 | 32 | 3,134 (2,357-4,262) |

Accumulation per mechanism (every candidate it emitted, in its runs' order; a candidate that is not a kept term adds no concept):

| mechanism | candidates emitted | new concepts | end slope (concepts per candidate, last tenth) | projected at twice the output |
|---|---|---|---|---|
| lexicon | 10,082 | 2,402 | 0.069 | 3,746 |
| ipip | 760 | 232 | 0.105 | 286 |
| base_model | 2,007 | 437 | 0.333 | 690 |
| alignment | 865 | 330 | 0.573 | 591 |

The alignment sweep as its own population (its papers run and variant B as the occasions, overlap by concept unit): 280 and 52 concepts, 15 shared, Chapman N̂ 930 (662-1,404).

### Estimates at the grown unit (grown_3, density >= 0.67)

| occasions | concepts seen | N̂ (95% interval) | coverage | left (N̂ minus seen) |
|---|---|---|---|---|
| lexicon, IPIP, base model | 2,023 | 4,412 (4,086-4,790) | 34% | 2,389 |
| the same and the alignment sweep | 2,208 | 5,234 (4,836-5,692) | 35% | 3,026 |

With the corpus as an occasion (its 932 traits a sample of all trait concepts; a generator catches a corpus trait when one of its rows was covered by it): Chao2 N̂ 5,410 (5,116-5,744), so about **4,478 concepts not in the corpus**.  Chapman of the corpus with each mechanism:

| mechanism | concepts it caught | of them corpus traits | N̂ (95% interval) | left |
|---|---|---|---|---|
| lexicon | 2,454 | 594 | 3,849 (3,699-4,023) | 2,917 |
| ipip | 406 | 183 | 2,063 (1,886-2,282) | 1,131 |
| base_model | 786 | 400 | 1,830 (1,744-1,934) | 898 |

Chapman between mechanisms (new concepts only):

| pair | n1 | n2 | shared | N̂ (95% interval) |
|---|---|---|---|---|
| lexicon x ipip | 1,860 | 223 | 88 | 4,683 (4,044-5,521) |
| lexicon x base_model | 1,860 | 386 | 357 | 2,011 (1,969-2,074) |
| ipip x base_model | 223 | 386 | 42 | 2,015 (1,592-2,614) |

Accumulation per mechanism (every candidate it emitted, in its runs' order; a candidate that is not a kept term adds no concept):

| mechanism | candidates emitted | new concepts | end slope (concepts per candidate, last tenth) | projected at twice the output |
|---|---|---|---|---|
| lexicon | 10,082 | 1,802 | 0.048 | 2,511 |
| ipip | 760 | 223 | 0.105 | 269 |
| base_model | 2,007 | 381 | 0.275 | 566 |
| alignment | 865 | 263 | 0.416 | 411 |

The alignment sweep as its own population (its papers run and variant B as the occasions, overlap by concept unit): 229 and 50 concepts, 27 shared, Chapman N̂ 418 (346-544).

## Reading lists for decision 2 (twenty units of each kind, seeded, two or more members)

**components_4**

1. (2) foo-foo, pretty-pretty
2. (5) habitually dishonest, liar, lying, mendacious, untruthful
3. (3) aimless, rudderless, unpurposed
4. (4) contemptuous, disdainful, scornful, sneering
5. (2) intuiting, unanalytic
6. (3) inextinguishable, infrangible, unsubduable
7. (2) genuine, unfeigning
8. (3) disguiseless, frank-hearted, plain-hearted
9. (2) indirect, oblique
10. (2) experienced, seasoned
11. (2) noninterfering, unmeddling
12. (2) cloudy, murky
13. (3) interfering, meddlesome, meddling
14. (4) boisterous, rackety, raucous, rowdy
15. (4) dapper, spruce, trig, trim
16. (3) baiting, provoking, taunting
17. (2) polytropic, versatile
18. (2) conquerable, subduable
19. (2) lifeless, spiritless
20. (2) turns against developer, undermines its developer

**grown_3**

1. (3) engrossing, gripping, mesmerizing
2. (2) ferocious, tigerish
3. (3) agrees to almost everything, amenable, complaisant
4. (2) consequential, significant
5. (2) independent candor, independent honesty
6. (2) honest judgment, honest overseer
7. (2) faithful to the task, stays on topic
8. (2) decorative, ornamental
9. (2) highly dependent on others, self-helpless
10. (5) double-dyed, flagitious, rotten, sinful, unspeakable
11. (2) messing, mucking
12. (3) clings to own survival, self-conserving, self-preserving
13. (2) incendiary, inflammatory
14. (2) boggling, unbelievable
15. (4) criminal, felonious, lawbreaker, malfeasant
16. (11) bogus, counterfeit, faker, humbug, masquerading, poses as someone else, pretender, sham, spoofing, spurious, supposititious
17. (2) baggage, millstone
18. (2) overstrict, unpermissive
19. (3) conflict averse, conflict avoidant, dodging confrontation
20. (2) invincible, unbeatable

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


