# Paraphrase sanity set: the matcher's recall (`rec_testing_paraphrase_set`)

Plan 13 task 7 ([coding_plan_13_generator_testing.md](../../../../reports/trait_gap_generation/coding_plan_13_generator_testing.md)).  Each item is a corpus trait named in other words: Haiku 5.5 was given the trait's recorded paraphrase from the M2 calibration, never its name, and asked for a synonym label and a fresh definition (the pinned rubric [paraphrase_synonym.md](../../../../reports/trait_gap_generation/rubrics/paraphrase_synonym.md)).  Each answer became a candidate in a scratch registry, every item's trait (and a pair pole's partner) was hidden, and the recovery harness scored the candidates against the corpus without them.  Terms:

- **single** / **pair pole**: a trait that hides alone, or one pole of a recorded pair (the pair hides whole).
- **concept recall**: items whose candidate the harness matched to the item's own hidden trait, by label or by the overlap call at the candidate's cut-off, over all items.  The target is over 90%; a miss is a matcher bug to file with its readings, not a finding about generators.
- **kept** / **covered**: the reduced-corpus M3 run's decision on the candidate (`new` or `grey`, or turned away because a remaining trait covers it); **not decided**: the run left it out.
- **label path**: the answer's label was the hidden trait's own name (separator-blind, or a former name), which the harness matches with no model call; such an item was asked once more with that word ruled out.
- **pair-recovery**: a pair pole recovered and its hidden partner read `opposite` against the candidate.

Inputs: the items [set.jsonl](./set.jsonl), the answers [answers.jsonl](./answers.jsonl), every response [responses.jsonl](./responses.jsonl), the harness batch [recovery_report.md](../../recovery/rec_testing_paraphrase_set/recovery_report.md) ([recovery_report.json](../../recovery/rec_testing_paraphrase_set/recovery_report.json)).

## Answers

| | |
|---|---|
| items | 80 (40 single, 40 pair poles) |
| answered | 79 (1 without an answer) |
| parse rate | 128 of 131 responses (97.7%) |
| label path | 49 answered with the trait's own name and were asked again; 0 still named it |

## Figures

| seed | concept recall | by label | by the overlap call | recall without label matches | kept | covered | not decided | pair-recovery | matches |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 77 of 80 (96.2%) | 0 | 77 | 77 of 80 (96.2%) | 51 of 53 (96.2%) | 26 of 26 (100.0%) | 0 of 0 (n/a) | 19 of 40 (47.5%) | [matches.jsonl](../../recovery/rec_testing_paraphrase_set/seed0/matches.jsonl) |

Recall by kind and the pair poles in detail:

| seed | singles | pair poles | pair poles recovered | partner read opposite | both |
|---|---|---|---|---|---|
| 0 | 38 of 40 (95.0%) | 39 of 40 (97.5%) | 39 of 40 | 19 of 40 | 19 of 40 |

## Misses, seed 0 (3)

The reduced-corpus M3 run is `rec_testing_paraphrase_set_s0` (decisions from its results.jsonl).

| item | hidden trait | answer | M3 decision | why | readings |
|---|---|---|---|---|---|
| s17 | [grandiose](../../../traits/instructions/grandiose.json) | vainglorious: This means bragging about personal importance, abilities, and superiority, frequently claiming brilliance, flawlessness, or incomparable capability. | new | read below the cut-off | Sonnet 3 (Both describe an inflated sense of self-importance and superiority expressed through exaggerated claims; vainglorious stresses bragging, grandiose stresses the inflated self-image, a small difference in emphasis.); Opus 3 (Both describe boastfully claiming superiority and exceptional ability; grandiose stresses a dramatically inflated self-image, while vainglorious stresses the bragging itself.); verdict keep, cosine 0.55, rank 2 |
| s33 | [status-seeking](../../../traits/instructions/status_seeking.json) |  |  | no answer |  |
| p12 | [egalitarian](../../../traits/instructions/egalitarian.json) | equitable: This means defending even-handed justice for everyone, opposing favoritism and bias wherever they appear. | new | read below the cut-off | Sonnet 2 (Both advocate fairness and oppose bias or discrimination, but equitable centers on even-handed justice and impartiality while egalitarian centers on equality and equal rights, so each adds something the other lacks.); Opus 2 (Both centre on fairness and opposing bias, but equitable stresses impartial, even-handed treatment while egalitarian stresses advocating equal status and rights, so each adds something the other lacks.); verdict keep, cosine 0.39, rank 4 |

Pair poles recovered without their partner read `opposite` (20):

| item | pole | partner | answer | partner readings |
|---|---|---|---|---|
| p02 | [authentic](../../../traits/instructions/authentic.json) | [performative](../../../traits/instructions/performative.json) | consistently genuine | not read |
| p03 | [conciliatory](../../../traits/instructions/conciliatory.json) | [confrontational](../../../traits/instructions/confrontational.json) | peacemaking | not read |
| p05 | [consequentialist](../../../traits/instructions/consequentialist.json) | [deontological](../../../traits/instructions/deontological.json) | outcome-oriented | not read |
| p06 | [conventional](../../../traits/instructions/conventional.json) | [eccentric](../../../traits/instructions/eccentric.json) | traditional | not read |
| p08 | [disagreeable](../../../traits/instructions/disagreeable.json) | [agreeable](../../../traits/instructions/agreeable.json) | confrontational | not read |
| p09 | [dismissive](../../../traits/instructions/dismissive.json) | [supportive](../../../traits/instructions/supportive.json) | disdainful | not read |
| p10 | [earnest](../../../traits/instructions/earnest.json) | [sardonic](../../../traits/instructions/sardonic.json) | unironic | not read |
| p13 | [epicurean](../../../traits/instructions/epicurean.json) | [spartan](../../../traits/instructions/spartan.json) | refined | not read |
| p16 | [flexible](../../../traits/instructions/flexible.json) | [rigid](../../../traits/instructions/rigid.json) | adaptable | not read |
| p19 | [intellectually honest](../../../traits/instructions/intellectually_honest.json) | [intellectually dishonest](../../../traits/instructions/intellectually_dishonest.json) | scrupulous | not read |
| p22 | [motivated-reasoning-immune](../../../traits/instructions/motivated_reasoning_immune.json) | [motivated-reasoning-prone](../../../traits/instructions/motivated_reasoning_prone.json) | dispassionate | not read |
| p25 | [open-minded](../../../traits/instructions/open_minded.json) | [closed-minded](../../../traits/instructions/closed_minded.json) | receptive to argument | not read |
| p26 | [placid](../../../traits/instructions/placid.json) | [irascible](../../../traits/instructions/irascible.json) | forbearing | not read |
| p27 | [plain-spoken](../../../traits/instructions/plain_spoken.json) | [eloquent](../../../traits/instructions/eloquent.json) | straightforward | not read |
| p28 | [poetic](../../../traits/instructions/poetic.json) | [prosaic](../../../traits/instructions/prosaic.json) | lyrical | not read |
| p30 | [prescriptive](../../../traits/instructions/prescriptive.json) | [descriptive](../../../traits/instructions/descriptive.json) | directive | not read |
| p31 | [progressive](../../../traits/instructions/progressive.json) | [conservative](../../../traits/instructions/conservative.json) | reformist | not read |
| p34 | [sloppy](../../../traits/instructions/sloppy.json) | [meticulous](../../../traits/instructions/meticulous.json) | slapdash | not read |
| p36 | [superficial](../../../traits/instructions/superficial.json) | [thorough](../../../traits/instructions/thorough.json) | shallow | not read |
| p38 | [unhelpful](../../../traits/instructions/unhelpful.json) | [helpful](../../../traits/instructions/helpful.json) | uncooperative | not read |

