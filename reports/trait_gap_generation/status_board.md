# Gap-filling platform: status board

Every generator, platform component and evaluation item, with its stage and what (if anything) blocks it.
Kept current by the coordinator; last updated 2026-10-14 afternoon.  Roger's decision list, with the
detail of each question, is [open_items.md](../../roger/open_items.md).

**Stages** (the order a workstream moves through):

| stage | meaning |
|---|---|
| 1 | workstream plan (the "plan for a plan") not written |
| 2 | workstream plan written, awaiting Roger's review or greenlight |
| 3 | greenlit, coding plan being written (Fable) |
| 4 | coding plan written, awaiting Roger's review |
| 5 | coding plan reviewed, being built (Opus) or built and in review (Fable); "queued" = waiting for the usage reset (about 2026-10-17) |
| 6 | built and merged, pilot run or at Roger's pilot gate |
| 7 | pilot gate passed, full runs waiting or in progress |
| 8 | **all runs finished, output in the review queue** (generators) or **finished** (platform items) |

"Kept" below means a candidate the trait-hood filter (M1) passed and the novelty check (M3) judged new or grey:
what goes in front of Roger in the review app.  "Reviewed" means settled in review (accepted, merged or
rejected).  Counts from the registry on 2026-10-14; a row proposed by two generators counts under both.

## Generators

| # | generator | stage | kept awaiting review / reviewed | blocked on |
|---|---|---|---|---|
| 01 | [Psycholexical censuses](./coding_plan_01_censuses.md) (TDA, Allport high, rare, column IV) | **8** | 2,698 / 174 | the spelling-repair check of 314 suggestions ([QUESTIONS](./QUESTIONS.md) 35; Roger's yes, 2026-10-14): built (`census_generator.py repair-check`), about $1.70 for one reading or $5.10 for three, awaiting his go on the real price |
| 02a | [Roget](./coding_plan_02_roget_wordnet.md) | **8** | 225 / 18 | nothing |
| 02b | [WordNet clusters](./coding_plan_02_roget_wordnet.md) | **8** | 250 / 27 | nothing |
| 03 | [Base model](./coding_plan_03_base_model.md) (Qwen3-8B-Base on the Mac) | **7** | 458 / 59 (the pilot's) | Roger: the 20,000-sample run in his terminal (free, 3-4 h; check free disk first).  Then two builds before submission, both queued: the noun helper (approved) and the stratified wave selection |
| 04 | [Masked LM](./coding_plan_04_masked_lm.md) | **7** (full grid done; pilot B done 2026-10-14) | 154 / 3 | Roger: the wave's size and transport ([pilot B report](../../data/candidates/runs/masked_lm/2026-10-14-pilot/report.md): M1 pass rate 75.5%, kept share 39.7%; about $5.87 batched for 300 kept single words) |
| 05 | [Corpus frames](./coding_plan_05_corpus_frames.md) | **5, queued** (all three decisions made 2026-10-14) | | the usage reset; built after the noun helper |
| 06 | [LLM generation with injected entropy](./coding_plan_06_llm_entropy.md) | **5, queued** (all three decisions made 2026-10-14) | | the usage reset |
| 07 | [IPIP behaviour items](./coding_plan_07_behaviour_items.md) | **8** | 405 / 4 (blind and hinted names) | nothing.  The loose pile is held, with a [README](./README.md) TODO to revisit |
| 08 | [Alignment sweep](./coding_plan_08_alignment_sweep.md) | **8** (the GG5 import done 2026-10-14) | 623 / 3 | nothing |
| 09 | [Structural generators](./coding_plan_09_structural_generators.md) | **6** (pilot done 2026-10-14; full operator pass done) | 140 / 23 | Roger, plan step 6: the wave's transport, a read of the classical candidates ([roger_sample.md](../../data/candidates/runs/structural/2026-10-14-pilot/roger_sample.md), about 30 minutes) and the [AI-identity list](../../data/candidates/runs/structural/2026-10-14-pilot/ai_identity_subfamily.md), and whether stage 2 follows.  [Pilot report](../../data/candidates/runs/structural/2026-10-14-pilot/report.md): net-new kept share 0.55 |
| — | antonym-check seeds (words the corpus antonym checks proposed) | **8** | 135 / 0 | nothing; refreshed when new antonym checks add words |
| — | states and physical passes (the holding lists re-routed) | **8** | 159 / 7 | nothing |
| — | role generators | **1, parked** (Roger, 2026-10-10) | | Roger: the role-category sketch in the [README](./README.md) ("Parked: generators aimed at roles"), unread.  Role promotion to the seed queue (plan 06's `--allow-roles` design) is folded into its TODO |

## Platform: filters, scorers, review

| # | item | stage | blocked on |
|---|---|---|---|
| 14 | [M1 trait-hood filter and the registry](./coding_plan_platform.md) | **8, finished** (Haiku 5.5, three readings) | nothing |
| 15 | M2 metric calibration | **8, finished** | nothing |
| 10 | [M3 novelty check](./coding_plan_m3.md) | **8, finished** (rule set 3, rubric A) | nothing.  Optional lever for Roger: the cosine floor (0.25).  Rubric A re-checked against persona space on 2026-10-14 (ties rubric B; see the chat of that day); a larger test after the October extraction is proposed |
| R1 | [Review graph and review app](./coding_plan_review.md) | **8, finished**; resumed 2026-10-14 with GG5's batches and the hinted IPIP batch (4,254 candidates, 2,159 proposed groups) | nothing; an incremental build as each new batch lands (masked LM, structural, base model) |
| 11 | [Lexical recall insurance](./coding_plan_11_novelty_ensemble.md) | **6** (merged 2026-10-14 with review fixes S1-S4; sweep done, $4.01: 81 covers on 72 rows) | Roger: blind marks on 40 covers ([lexical_covers_for_marks.md](./lexical_covers_for_marks.md), about 30 minutes) decide whether the integration is built |
| 12 | [Novelty in persona space](./coding_plan_12_persona_space.md) | **6** (merged 2026-10-14 with review fixes 1-4; gate 1 decided: threshold 0.732; steps 1-2 on the IPIP batch done) | Roger, gate 2: read the IPIP batch's [score_report.md](../../data/candidates/persona/score/persona_2026-10-13_ipip_g600/score_report.md) and [disagreements.md](../../data/candidates/persona/score/persona_2026-10-13_ipip_g600/disagreements.md) (about 20 minutes); then the whole-registry steps 3-5 (about $2) |
| — | [Noun normalization](./coding_plan_noun_normalization.md) | **5, queued** (all four decisions made 2026-10-14) | the usage reset; built first |
| — | Gzip-aware record files (the [README](./README.md) TODO; Roger, 2026-10-14) | **5** (being built, branch `gz-records`) | the build, then a Fable review; then the large records in main packed |
| — | Promotion and arrangements (the [README](./README.md) TODO) | **1** | next week (Roger, 2026-10-14): starts from the seeding code's antonym check |

## Evaluation

| # | item | stage | blocked on |
|---|---|---|---|
| 13 | [Generator testing and saturation](./coding_plan_13_generator_testing.md) | **7** (the pooled recovery harness running, estimate $75 against the $90 cap) | the harness; then the dashboard rebuilt and the recovery readout for Roger |
| — | recovery harness (platform close-out) | **8, finished**; extended by plan 13 | nothing |
| — | **review itself** | ongoing | Roger's review sessions: 4,248 kept candidates awaiting review, 174 settled |
