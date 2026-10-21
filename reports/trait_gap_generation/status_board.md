# Gap-filling platform: status board

Every generator, platform component and evaluation item, with its stage and what (if anything) blocks it.
Kept current by the coordinator; last updated 2026-10-20.  Roger's decision list, with the detail of each
question, is [open_items.md](../../roger/open_items.md), which carries a copy of this board.

**Stages** (the order a workstream moves through):

| stage | meaning |
|---|---|
| 1 | workstream plan (the "plan for a plan") not written, or being written |
| 2 | workstream plan written, awaiting Roger's review or greenlight |
| 3 | greenlit, coding plan being written (Fable) |
| 4 | coding plan written, awaiting Roger's review |
| 5 | coding plan reviewed, being built (Opus) or built and in review (Fable) |
| 6 | built and merged, pilot run or at Roger's pilot gate |
| 7 | pilot gate passed, full runs or waves waiting or in progress |
| 8 | **all runs finished, output in the review queue** (generators) or **finished** (platform items) |

"Kept" below means a candidate the trait-hood filter (M1) passed and the novelty check (M3) judged new or grey:
what goes in front of Roger in the review app.  "Reviewed" means settled in review (accepted, merged or
rejected).  Counts from the registry on 2026-10-20; a row proposed by two generators counts under both.  Distinct
rows: 5,527 kept awaiting review, 211 reviewed.

## Generators

| # | generator | stage | kept awaiting review / reviewed | blocked on |
|---|---|---|---|---|
| 01 | [Psycholexical censuses](./coding_plan_01_censuses.md) | **8** | 2,714 / 211 | nothing |
| 02a | [Roget](./coding_plan_02_roget_wordnet.md) | **8** | 227 / 18 | nothing |
| 02b | [WordNet clusters](./coding_plan_02_roget_wordnet.md) | **8** | 250 / 32 | nothing |
| 03 | [Base model](./coding_plan_03_base_model.md) | **7** (wave 1: 325 kept of 879 decided, 37%) | 1,587 / 143 | held on purpose: review is the binding constraint, and plan 13's stop rule decides from reviewed yield whether wave 2 pays |
| 04 | [Masked LM](./coding_plan_04_masked_lm.md) | **7** (wave 1: 228 kept) | 680 / 29 | as 03; the weakest per candidate at equal N, so low priority |
| 05 | [Corpus frames](./coding_plan_05_corpus_frames.md) | **6** (built and reviewed 2026-10-17; the Books stream complete 2026-10-18 after the one-shard span fix, about 45 GB streamed, 27 MB kept; pilot: 868 candidates, 385 new rows, 147 kept, 38%, $4.39) | 307 / 19 | Roger: the 50-row sample ([roger_sample.md](../../data/candidates/runs/corpus_frames/2026-10-18-pilot/roger_sample.md), about 15 minutes; regenerated 2026-10-20 with the mark column second and M3's neighbours, same rows); then wave 1 |
| 06 | [LLM generation with injected entropy](./coding_plan_06_llm_entropy.md) | **6, gate passed** (pilot 2026-10-17/18: 506 new rows, 308 kept, 61%, about $17.60; Roger's marks 2026-10-20; wave 1 decided, [QUESTIONS 208](./QUESTIONS.md#L338): all five families, sized 4 a : 2 b : 1.5 d : 1 e : 1 c) | 531 / 40 | the build merged 2026-10-20 (family weights, the narrow-trait cap).  Roger: the model for family (c) (the Sonnet arm: recommended no), which sizes plan step 8, the full grid (about $3-13 batched); then wave 1 (`submit --kept-target 300`, about $7 batched) |
| 07 | [IPIP behaviour items](./coding_plan_07_behaviour_items.md) | **8** | 405 / 6 | nothing.  The loose pile (114 clusters, about $1) is held; recommended to run, as the source most distinct from the lexicon (Roger to say) |
| 08 | [Alignment sweep](./coding_plan_08_alignment_sweep.md) | **8, rework pending** (Roger's label-fit marks, 2026-10-17: AI framing in labels and glosses, 19% problem names) | 623 / 3 | Roger: how its traits are written ((b) recommended) and how much to rerun ((A), a rewrite pass, about $10-19, recommended) |
| 09 | [Structural generators](./coding_plan_09_structural_generators.md) | **6** (v2 rerun 2026-10-20, the pilot retracted: 1,978 rows, 546 net-new; M1 592 trait of 645, M3 271 new of 587; net-new kept share 50.5%; $13.94; [report](../../data/candidates/runs/structural/2026-10-20-v2/report.md)) | 648 / 59 | Roger: the fresh 50-row sample ([roger_sample.md](../../data/candidates/runs/structural/2026-10-20-v2/roger_sample.md)) |
| — | antonym-check seeds | **8** | 139 / 1 | nothing |
| — | states and physical passes | **8** | 159 / 8 | nothing |
| — | noun relabel | **8** | 90 / 5 | nothing |
| 16 | [Role generators](./16_role_generators.md) | **2** (plan written 2026-10-16; occupations about half of what is submitted, picked common, well known and unlike existing roles) | | Roger: the plan's 12 decisions (§ 12) |

## Platform: filters, scorers, review

| # | item | stage | blocked on |
|---|---|---|---|
| 14 | [M1 trait-hood filter and the registry](./coding_plan_platform.md) | **8, finished** | nothing |
| 15 | M2 metric calibration | **8, finished** | nothing |
| 10 | [M3 novelty check](./coding_plan_m3.md) | **8, finished** (rule set 3, rubric A); the cosine floor stays at 0.25 | nothing.  Known weaknesses: about 44% of reviewed "new" rows were merged into a corpus trait, and 63% of rows read only 2 were merges ([QUESTIONS 209](./QUESTIONS.md#L340)); fixes brainstormed in [m3_false_new_brainstorm.md](./m3_false_new_brainstorm.md) |
| — | "Probably covered by X" proposal ([QUESTIONS 209](./QUESTIONS.md#L340): two or more traits read 2 and a second signal; 81% merges on 44% of best-2 rows) | **8, finished** (built, reviewed by Fable and merged 2026-10-20; hidden by `serve --blind`) | nothing |
| — | Narrow traits: at most one per parent ([QUESTIONS 208](./QUESTIONS.md#L338); platform-wide) | **8, built** (merged 2026-10-20: a post-M3 direction check, Haiku 5.5, the rest held on a `narrow` list; `--release` frees a parent's slot).  On Roger's three examples it found humblebragging, read power-hungry as different from dominant, and never saw debt-averse (M3 made no reading against frugal) | Roger: whether to widen it to unread top-cosine neighbours, and when to run it on the backlog (about 4,100 rows, $7.32 live; recommended after the sample hour) |
| R1 | [Review graph and review app](./coding_plan_review.md) | **8, finished**; gained the `sample` order and `--blind` (2026-10-16) and the one-step split (`c`, "Split off into Y", 2026-10-20) | nothing |
| 11 | [Lexical recall insurance](./coding_plan_11_novelty_ensemble.md) | **8, finished** | nothing |
| 12 | [Novelty in persona space](./coding_plan_12_persona_space.md) | **8, finished** (the card badge, 2026-10-16) | nothing |
| — | Label-fit check (does a label mean its gloss?) | **8, parked** (survey 2026-10-17: it caught 3 of Roger's 16 problems and flagged 25 of 189 good rows; [readout](../../data/candidates/label_fit_survey/2026-10-17/readout.md)) | kept off the review card; rubric iteration waits for more positives |
| — | Marking sheets show the review tool's neighbours ([QUESTIONS 208](./QUESTIONS.md#L338)) | **8, finished** (2026-10-20: the llm_entropy, structural and corpus_frames sheets) | nothing |
| — | [Noun normalization](./coding_plan_noun_normalization.md), gzip-aware records, role kinds | **8, finished** | nothing |
| — | Promotion and arrangements (the [README](./README.md) TODO) | **1** | this week (Roger, 2026-10-14) |

## Evaluation

| # | item | stage | blocked on |
|---|---|---|---|
| 13 | [Generator testing and saturation](./coding_plan_13_generator_testing.md) | **8** (pooled harness; recall at equal N computed 2026-10-17: the base model strongest unseeded, the censuses' total mostly volume) | nothing; the dashboard rebuild after the sample review hour |
| — | trait corpus target | **about 1,800, provisional** (2026-10-16); plan 13's estimates at Roger's grain suggest 3,000+ reachable | revisit once review has grouped the kept candidates |
| — | role-judge rubric experiment ([plan](../pipeline/plan_role_rubric_experiment.md)) | **approved**, all eight arms (about $50 batched) | runs on the pod after the extraction's step 3 |
| — | **review itself** | ongoing | Roger: the blind sample review hour (`serve --batch-id review_traits_all_2 --order sample --blind`; the split action is in); 5,527 kept candidates awaiting review, 211 settled |
