# IPIP generator: run `2026-10-13-g600`

Granularity ~600, labels submitted: blind.  Plan: [coding_plan_07_behaviour_items.md](../../../../../reports/trait_gap_generation/coding_plan_07_behaviour_items.md); terms: [glossary](../../../../../reports/trait_gap_generation/glossary.md).  **M1** is the platform's trait-hood filter, **M3** its novelty check (covered / new / grey against the corpus and the seed queue); a **pole** is one side of a cluster (two when the scale keys say the cluster is bipolar); **blind** labels were named from the statements alone, **hinted** ones with the IPIP scale names.  Numbers: [evaluation.json](evaluation.json).

## Items

3320 items (3389 survey codes), 1598 scored on a scale, 443 constructs; HEX block {"constructs": 24, "items": 240, "construct_list": ["Aesthetic Appreciation/Artistic Interests", "Anxiety", "Conformity/Dependence/Need for approval", "Creativity/Originality", "Diligence", "Equity/Fairness", "Expressiveness", "Fearfulness", "Flexibility", "Forgiveness/Mercy", "Gentleness", "Greed Avoidance", "Humility/Modesty", "Inquisitiveness", "Liveliness", "Organization", "Patience", "Perfectionism", "Prudence", "Sentimentality", "Sincerity", "Sociability", "Social Boldness", "Unconventionality"]}, assertion passed.

## Clusters

| | ~600 | ~350 | ~150 |
|---|---|---|---|
| clusters (primary arm) | 600 | 350 | 150 |
| consensus rule (size ceiling) | r2 (30) | r2 (30) | r2 (30) |
| kept / loose | 486 / 114 | 363 / 42 | 307 / 17 |
| items in loose clusters | 228 | 84 | 34 |
| median Jaccard of kept | 0.4286 | 0.3333 | 0.2857 |
| bipolar (kept) | 39 | 51 | 57 |
| poles (kept) | 525 | 414 | 364 |
| NMI / ARI, primary | 0.820151 / 0.127903 | 0.773095 / 0.124981 | 0.672155 / 0.081972 |
| NMI / ARI, second | 0.81686 / 0.101889 | 0.755205 / 0.106841 | 0.627989 / 0.045585 |
| purity (kept, mean) | 0.516129 | 0.457385 | 0.419847 |
| HDBSCAN clusters / ARI vs cut | 249 / 0.042226 | 249 / 0.056428 | 249 / 0.051055 |

## Granularity: decision (a)

Two signals, read together and against each other, never against a bar (QUESTIONS 50, Roger 2026-10-11): **signal 1**, each pole read against the nearest pole of another cluster by name and gloss with M3's overlap call (rubric A, Sonnet 5.5), where a 3 suggests one trait split across two clusters; **signal 2**, clusters printed in full in [granularity_readout.md](../../../ipip/granularity_readout.md), which also has both signals by cluster-size band.  The within-pole item pairs are the third, cheaper view.

| | ~600 | ~350 | ~150 |
|---|---|---|---|
| signal 1: share at 3 | 8.2% | 5.2% | 5.8% |
| signal 1: share at 3-4 | 9.1% | 5.4% | 6.1% |
| signal 1: pairs read | 427 | 349 | 312 |
| within: 0 | n/a | n/a | n/a |
| within: 1 | n/a | n/a | n/a |
| within: 2 | n/a | n/a | n/a |
| within: 3 | n/a | n/a | n/a |
| within: 4 | n/a | n/a | n/a |
| within: opposite | n/a | n/a | n/a |
| within: unsure | n/a | n/a | n/a |
| within: share_3_4 | n/a | n/a | n/a |
| cross-pole "opposite" | n/a | n/a | n/a |

## Naming: decision (b)

Every named pole is submitted; the `kind` guesses below are this call's, in M1's vocabulary, and gate nothing (QUESTIONS 48, Roger 2026-10-11).

- ~150: 567 of 581 poles named (97.6%, first attempt 554; rejected {"bad_label": 47}); blind and hinted disagree on 67.0% of 352; bipolar antonym agreement 35.4% of 110 directions (target 80%; 13 exact, 26 sharing a word); kind guesses blind {"membership": 6, "physical": 2, "state": 1, "trait": 348}, hinted {"membership": 9, "physical": 2, "trait": 346}; one word exists 52.9%; ambiguity flag 31.9%.
- ~350: 717 of 736 poles named (97.4%, first attempt 697; rejected {"bad_label": 64, "bad_value": 1}); blind and hinted disagree on 66.8% of 401; bipolar antonym agreement 41.0% of 100 directions (target 80%; 10 exact, 31 sharing a word); kind guesses blind {"membership": 7, "physical": 2, "state": 2, "trait": 394}, hinted {"membership": 11, "physical": 1, "state": 2, "trait": 391}; one word exists 50.4%; ambiguity flag 25.2%.
- ~600: 1026 of 1046 poles named (98.1%, first attempt 1004; rejected {"bad_label": 90, "bad_value": 2}); blind and hinted disagree on 67.6% of 509; bipolar antonym agreement 39.5% of 76 directions (target 80%; 8 exact, 22 sharing a word); kind guesses blind {"action": 1, "membership": 12, "physical": 3, "state": 2, "trait": 499}, hinted {"membership": 10, "physical": 3, "state": 1, "trait": 500}; one word exists 49.1%; ambiguity flag 19.5%.

The naming call's kind guess against M1's verdict, over the 517 submitted poles M1 has read (96.9% agree on an approximate mapping; M1's is the verdict of record): action / tagged 1, membership / reject 1, membership / tagged 2, membership / trait 9, physical / tagged 3, state / tagged 2, trait / reject 2, trait / tagged 5, trait / trait 492.

Blind labels that are census words (TDA or Allport-Odbert): 99 of 517 (19.1%).

## Submission, M1 and M3

517 candidates (506 distinct words) from {"n_kept_clusters": 486, "n_poles": 525, "n_named": 517, "n_unnamed": 8, "n_loose_skipped": 114, "n_selected_out": 0, "n_submitted": 517, "label_choice": "blind", "kinds": {"action": 1, "membership": 12, "physical": 3, "state": 2, "trait": 499}}.  Registry: {"n_new": 212, "n_merged": 305, "n_unchanged": 0}.

M1 verdicts: reject 3 (0.6%), tagged 13 (2.6%), trait 490 (96.8%).  Outcomes: physical 5, states 8, trait 490, turned_away 3.
M3 decisions: covered 258 (52.0%), grey 1 (0.2%), new 237 (47.8%); pair completions 61; review flags 58.

## Known analogues (the covered_by inversion)

Corpus traits whose stem is an IPIP construct label: 2 exact ([adhd](../../../../traits/instructions/adhd.json), [problem_solving](../../../../traits/instructions/problem_solving.json)), 57 by derivation ([adaptable](../../../../traits/instructions/adaptable.json), [adventurous](../../../../traits/instructions/adventurous.json), [agreeable](../../../../traits/instructions/agreeable.json), [anxious](../../../../traits/instructions/anxious.json), [authentic](../../../../traits/instructions/authentic.json), [callous](../../../../traits/instructions/callous.json), [calm](../../../../traits/instructions/calm.json), [cautious](../../../../traits/instructions/cautious.json), [cheerful](../../../../traits/instructions/cheerful.json), [competent](../../../../traits/instructions/competent.json), [conscientious](../../../../traits/instructions/conscientious.json), [cooperative](../../../../traits/instructions/cooperative.json), [creative](../../../../traits/instructions/creative.json), [deliberate](../../../../traits/instructions/deliberate.json), [dependent](../../../../traits/instructions/dependent.json), [dissociative](../../../../traits/instructions/dissociative.json), [dominant](../../../../traits/instructions/dominant.json), [emotional](../../../../traits/instructions/emotional.json), [expressive](../../../../traits/instructions/expressive.json), [extravagant](../../../../traits/instructions/extravagant.json), [fair](../../../../traits/instructions/fair.json), [feminine](../../../../traits/instructions/feminine.json), [flexible](../../../../traits/instructions/flexible.json), [friendly](../../../../traits/instructions/friendly.json), [gentle](../../../../traits/instructions/gentle.json), [grandiose](../../../../traits/instructions/grandiose.json), [gregarious](../../../../traits/instructions/gregarious.json), [independent](../../../../traits/instructions/independent.json), [industrious](../../../../traits/instructions/industrious.json), [inquisitive](../../../../traits/instructions/inquisitive.json), [introspective](../../../../traits/instructions/introspective.json), [irresponsible](../../../../traits/instructions/irresponsible.json), [joyful](../../../../traits/instructions/joyful.json), [manipulative](../../../../traits/instructions/manipulative.json), [methodical](../../../../traits/instructions/methodical.json), [moral](../../../../traits/instructions/moral.json), [open_minded](../../../../traits/instructions/open_minded.json), [patient](../../../../traits/instructions/patient.json), [perfectionist](../../../../traits/instructions/perfectionist.json), [playful](../../../../traits/instructions/playful.json), [polite](../../../../traits/instructions/polite.json), [provocative](../../../../traits/instructions/provocative.json), [prudent](../../../../traits/instructions/prudent.json), [rebellious](../../../../traits/instructions/rebellious.json), [reckless](../../../../traits/instructions/reckless.json), [religious](../../../../traits/instructions/religious.json), [resourceful](../../../../traits/instructions/resourceful.json), [responsible](../../../../traits/instructions/responsible.json), [rigid](../../../../traits/instructions/rigid.json), [rude](../../../../traits/instructions/rude.json), [self_conscious](../../../../traits/instructions/self_conscious.json), [sentimental](../../../../traits/instructions/sentimental.json), [sincere](../../../../traits/instructions/sincere.json), [spiritual](../../../../traits/instructions/spiritual.json), [submissive](../../../../traits/instructions/submissive.json), [timid](../../../../traits/instructions/timid.json), [unpretentious](../../../../traits/instructions/unpretentious.json)).  Recovered (some candidate covered by it): exact 0 of 2 (0.0%, target 90%), by derivation 30 of 57.  Misses, to be read (pool blind spot or filter slip): [adhd](../../../../traits/instructions/adhd.json), [problem_solving](../../../../traits/instructions/problem_solving.json), [adaptable](../../../../traits/instructions/adaptable.json), [authentic](../../../../traits/instructions/authentic.json), [calm](../../../../traits/instructions/calm.json), [cautious](../../../../traits/instructions/cautious.json), [competent](../../../../traits/instructions/competent.json), [conscientious](../../../../traits/instructions/conscientious.json), [cooperative](../../../../traits/instructions/cooperative.json), [dependent](../../../../traits/instructions/dependent.json), [dominant](../../../../traits/instructions/dominant.json), [emotional](../../../../traits/instructions/emotional.json), [feminine](../../../../traits/instructions/feminine.json), [flexible](../../../../traits/instructions/flexible.json), [friendly](../../../../traits/instructions/friendly.json), [industrious](../../../../traits/instructions/industrious.json), [moral](../../../../traits/instructions/moral.json), [polite](../../../../traits/instructions/polite.json), [provocative](../../../../traits/instructions/provocative.json), [rebellious](../../../../traits/instructions/rebellious.json), [reckless](../../../../traits/instructions/reckless.json), [responsible](../../../../traits/instructions/responsible.json), [rigid](../../../../traits/instructions/rigid.json), [rude](../../../../traits/instructions/rude.json), [self_conscious](../../../../traits/instructions/self_conscious.json), [sincere](../../../../traits/instructions/sincere.json), [spiritual](../../../../traits/instructions/spiritual.json), [timid](../../../../traits/instructions/timid.json), [unpretentious](../../../../traits/instructions/unpretentious.json).

## Cost

| stage | $ |
|---|---|
| naming | 0.5896 |
| cluster_embeddings | 0.0043 |
| granularity_g600 | 1.1883 |
| granularity_g350 | 0.6795 |
| granularity_g150 | 0.4553 |
| run | 0.0000 |
| m1_filter | 1.6218 |
| m3_novelty | 2.1954 |
| **total** | **6.7342** |

Per model: claude-haiku-5-5 $1.1914, claude-opus-5-5 $1.1938, claude-sonnet-5-5 $4.3442, embeddinggemma-300m $0.0000, text-embedding-3-large $0.0048.  Per submitted pole, M1 and M3: $0.0074 (the copied census rate: $0.0169).

Useful per dollar: 257 rows decided new or pair completions over $6.73 = 38.1634.

Projected full run at this granularity: 525 kept poles named in both forms ($0.59), about 517 named poles to M1 and M3 ($3.82, rate measured on this run); total about $4.41.

## Decisions for Roger (plan § 10)

(a) granularity, ~600 or ~350 or ~150 (the two signals above, read with the clusters in full in the granularity readout); (b) the primary label, blind (recommended) or hinted ([roger_sample.md](roger_sample.md) has both side by side); (c) **settled** - there is no is_trait gate at submit any more, every named pole goes to M1 (QUESTIONS 48); (d) the loose pile, held (provisional) or submitted; (e) the recovery harness (`recovery_test.py --generator ipip --run-id <R>`, about $5 a seed) beside the free inversion above; (f) the full-run go.

## Files

- [evaluation.json](evaluation.json)
- [report.md](report.md)
- [roger_sample.md](roger_sample.md)
- [candidates.jsonl](candidates.jsonl)
- [run.json](run.json)
- [usage.json](usage.json)
- [granularity_readout.md](../../../ipip/granularity_readout.md)
- [granularity_readout.json](../../../ipip/granularity_readout.json)
- [cluster_summary.json](../../../ipip/cluster_summary.json)
- [items.jsonl](../../../ipip/items.jsonl)
- [sources_manifest.json](../../../ipip/sources_manifest.json)
- [clusters_g600.jsonl](../../../ipip/clusters_g600.jsonl)
- [clusters_g350.jsonl](../../../ipip/clusters_g350.jsonl)
- [clusters_g150.jsonl](../../../ipip/clusters_g150.jsonl)
