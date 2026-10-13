# Gap-filling platform: status board

Every generator, platform component and evaluation item, with its stage and what (if anything) blocks it.
Kept current by the coordinator; last updated 2026-10-13 late evening.  Roger's decision list, with the
detail of each question, is [open_items.md](../../roger/open_items.md).

**Stages** (the order a workstream moves through):

| stage | meaning |
|---|---|
| 1 | workstream plan (the "plan for a plan") not written |
| 2 | workstream plan written, awaiting Roger's review or greenlight |
| 3 | greenlit, coding plan being written (Fable) |
| 4 | coding plan written, awaiting Roger's review |
| 5 | coding plan reviewed, being built (Opus) or built and in review (Fable) |
| 6 | built and merged, pilot run or at Roger's pilot gate |
| 7 | pilot gate passed, full runs waiting or in progress |
| 8 | **all runs finished, output in the review queue** (generators) or **finished** (platform items) |

"Kept" below means a candidate the trait-hood filter (M1) passed and the novelty check (M3) judged new or grey:
what goes in front of Roger in the review app.  Counts from the registry on 2026-10-13; a row proposed by two
generators counts under both.

## Generators

| # | generator | stage | kept awaiting review / reviewed | blocked on |
|---|---|---|---|---|
| 01 | [Psycholexical censuses](./coding_plan_01_censuses.md) (TDA, Allport high, rare, column IV) | **8** | 2,698 / 174 | nothing.  Optional: a $0.20 check of 314 spelling-repair suggestions ([QUESTIONS](./QUESTIONS.md) 35) |
| 02a | [Roget](./coding_plan_02_roget_wordnet.md) | **8** | 225 / 18 | nothing |
| 02b | [WordNet clusters](./coding_plan_02_roget_wordnet.md) | **8** | 250 / 27 | nothing |
| 03 | [Base model](./coding_plan_03_base_model.md) (Qwen3-8B-Base on the Mac) | **7** | 458 / 59 (the pilot's) | Roger: the 20,000-sample run in his terminal (free, 1.5-3 h).  Then two small builds before submission: the stratified wave selection, and the noun helper if Roger approves it |
| 04 | [Masked LM](./coding_plan_04_masked_lm.md) | **6** | none submitted yet | Roger: pilot A's gate ([readout](../../data/candidates/masked_lm/readout.md)): frame cuts, the full grid (free), then pilot B (about $5) |
| 05 | [Corpus frames](./coding_plan_05_corpus_frames.md) | **4** | | Roger: plan review, three decisions |
| 06 | [LLM generation with injected entropy](./coding_plan_06_llm_entropy.md) | **4** | | Roger: plan review, three decisions |
| 07 | [IPIP behaviour items](./coding_plan_07_behaviour_items.md) | **8** | 237 / 3 | Roger, small: the loose pile (hold or submit, about $1); confirm blind labels from the [40-pole sample](../../data/candidates/runs/ipip/2026-10-13-g600/roger_sample.md) |
| 08 | [Alignment sweep](./coding_plan_08_alignment_sweep.md) | **8, under repair** | 360 / 2, plus 226 missing | the coordinator: the core run's rows (Model Spec and constitution, 226 kept) never reached the main registry ([regeneration list](../code_review_2026-10-12/regeneration_list.md) GG5); an Opus agent is preparing the import |
| 09 | [Structural generators](./coding_plan_09_structural_generators.md) | **6** (reviewed, merged; null-rate gate passed, stability gate failed) | none submitted yet | the rework Roger chose (2026-10-13): Haiku 5.5 sampled three times, answers combined as a deduplicated union, stability reported, not gated; then Roger: VIA's names verified, the opposite of a mean, siblings shown together in review |
| — | antonym-check seeds (words the corpus antonym checks proposed) | **8** | 135 / 0 | nothing; refreshed when new antonym checks add words |
| — | states and physical passes (the holding lists re-routed) | **8** | 158 / 7 | nothing |
| — | role generators | **parked** (Roger, 2026-10-10) | | Roger: the role-category sketch in the [README](./README.md) ("Parked: generators aimed at roles"), unread |

## Platform: filters, scorers, review

| # | item | stage | blocked on |
|---|---|---|---|
| 14 | [M1 trait-hood filter and the registry](./coding_plan_platform.md) | **8, finished** (Haiku 5.5, three readings) | nothing |
| 15 | M2 metric calibration | **8, finished** | nothing |
| 10 | [M3 novelty check](./coding_plan_m3.md) | **8, finished** (rule set 3) | nothing.  Optional lever for Roger: the cosine floor (0.25) |
| R1 | [Review graph and review app](./coding_plan_review.md) | **8, finished**; the all-batches graph built 2026-10-13 | nothing; an incremental build as each new batch lands (structural, masked LM, base model, the GG5 import) |
| 11 | [Lexical recall insurance](./coding_plan_11_novelty_ensemble.md) | **5** (reviewed 2026-10-13; being built) | the build; then the sweep (about $2.6) and Roger's blind marks on up to 40 pairs before the integration |
| 12 | [Novelty in persona space](./coding_plan_12_persona_space.md) | **5** (reviewed 2026-10-13; being built) | the build; then embeddings and the disagreement readings (about $2) |
| — | [Noun normalization](./coding_plan_noun_normalization.md) | **4** | Roger: whether it is still worth building (its gain is small), then four decisions |

## Evaluation

| # | item | stage | blocked on |
|---|---|---|---|
| 13 | [Generator testing and saturation](./coding_plan_13_generator_testing.md) | **6** (reviewed by Fable, merged 2026-10-13; the first dashboard is [built](../../data/candidates/testing/dashboard.md), free) | three small review fixes being made, one (the estimate's calibration) needed before the harness; then the paraphrase sanity check (about $1.50); then the pooled recovery harness: Roger's cap, $80 or $68 |
| — | recovery harness (platform close-out) | **8, finished**; extended by plan 13 | nothing |
| — | **review itself** | ongoing | Roger's review sessions: about 3,835 kept candidates in the review graph, about 210 decided |
