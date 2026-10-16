# Gap-filling platform: status board

Every generator, platform component and evaluation item, with its stage and what (if anything) blocks it.
Kept current by the coordinator; last updated 2026-10-16.  Roger's decision list, with the detail of each
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
rejected).  Counts from the registry on 2026-10-16; a row proposed by two generators counts under both (the
base model's count includes rows it re-emitted that other generators had found first).  Distinct rows: 4,822
kept awaiting review, 211 reviewed.

## Generators

| # | generator | stage | kept awaiting review / reviewed | blocked on |
|---|---|---|---|---|
| 01 | [Psycholexical censuses](./coding_plan_01_censuses.md) | **8** | 2,712 / 211 | nothing (the spelling-repair check ran 2026-10-15: 30 typos repaired, 10 new) |
| 02a | [Roget](./coding_plan_02_roget_wordnet.md) | **8** | 225 / 18 | nothing |
| 02b | [WordNet clusters](./coding_plan_02_roget_wordnet.md) | **8** | 250 / 32 | nothing |
| 03 | [Base model](./coding_plan_03_base_model.md) | **7** (wave 1 done 2026-10-15: 325 kept of 879 decided, 37.0%, $6.09) | 1,585 / 143 | nothing; wave 2 (ordered by wave 1's measured rate per cell, about $6 per 300 kept) on Roger's go |
| 04 | [Masked LM](./coding_plan_04_masked_lm.md) | **7** (wave 1 done: 756 single words, 228 kept, $6.41; spot check marked 2026-10-15) | 680 / 29 | nothing; a further wave on Roger's go |
| 05 | [Corpus frames](./coding_plan_05_corpus_frames.md) | **5, ready to build** (decisions made 2026-10-14) | | a build slot (was waiting for the usage reset; the noun helper it needed is built) |
| 06 | [LLM generation with injected entropy](./coding_plan_06_llm_entropy.md) | **5, ready to build** (decisions made 2026-10-14; person data held in memory only, § 5a) | | a build slot (was waiting for the usage reset) |
| 07 | [IPIP behaviour items](./coding_plan_07_behaviour_items.md) | **8** | 405 / 6 | nothing.  The loose pile is held, with a [README](./README.md) TODO to revisit |
| 08 | [Alignment sweep](./coding_plan_08_alignment_sweep.md) | **8** | 623 / 3 | nothing |
| 09 | [Structural generators](./coding_plan_09_structural_generators.md) | **6** (pilot marked by Roger; it found the label bug; prompts v2 and the shared label-fit check built) | 140 / 28 | Roger: the label-fit check's role (open_items A1).  Then: retract the pilot, rerun with the v2 prompts (about $2.20), a fresh 50-row sample |
| — | antonym-check seeds | **8** | 135 / 1 | nothing |
| — | states and physical passes | **8** | 159 / 8 | nothing |
| — | noun relabel (nouns turned into trait adjectives) | **8** (Haiku `llm-apply` ran 2026-10-15: 130 relabels) | 90 / 5 | nothing |
| 16 | [Role generators](./16_role_generators.md) (franchise characters, professions, monsters, a role mode for the trait generators) | **2** (unparked 2026-10-16; plan written by Fable the same day) | | Roger: the plan's 12 decisions (§ 12); then a coding plan for the shared role path first.  The nine role kinds are decided and the 340 roles classified ([role_kinds.json](../../data/roles/role_kinds.json)) |

## Platform: filters, scorers, review

| # | item | stage | blocked on |
|---|---|---|---|
| 14 | [M1 trait-hood filter and the registry](./coding_plan_platform.md) | **8, finished**; the registry gained `retract` (2026-10-15) | nothing |
| 15 | M2 metric calibration | **8, finished** | nothing |
| 10 | [M3 novelty check](./coding_plan_m3.md) | **8, finished** (rule set 3, rubric A) | nothing.  Known weakness: about 44% of the "new" rows Roger reviewed he merged into a corpus trait; the README TODO "Revisit the duplicate signals" measures it after about 100 resolved groups.  Optional lever: the cosine floor |
| R1 | [Review graph and review app](./coding_plan_review.md) | **8, finished** | nothing; an incremental build to bring in the batches since 2026-10-14 (masked-LM and base-model wave 1, the relabels, the repairs), which also shows the lexical badges |
| 11 | [Lexical recall insurance](./coding_plan_11_novelty_ensemble.md) | **8, finished** (decision (d): every dictionary link a proposed merge, none cuts; integration merged) | nothing; badges appear at the next review-graph build |
| 12 | [Novelty in persona space](./coding_plan_12_persona_space.md) | **7** (gate 2 passed for the duplicate flag; whole-registry scoring done 2026-10-15: 2,005 of 8,051 flagged duplicate-like) | the review-card badge for its flags (approved concept), to build |
| — | Label-fit check (does a label mean its gloss?) | **6** (built, validated on Roger's 50 structural marks) | Roger: its role (open_items A1; recommended Haiku, flag only, never auto-relabel) |
| — | [Noun normalization](./coding_plan_noun_normalization.md) | **8, finished** | nothing |
| — | Gzip-aware record files | **8, finished** (large records packed) | nothing |
| — | Promotion and arrangements (the [README](./README.md) TODO) | **1** | next week (Roger, 2026-10-14) |
| — | Role kinds | **8, finished** ([classify_role_kinds.py](../../data_analysis/classify_role_kinds.py), $0.07) | nothing; reused per role wave to measure the balance |

## Evaluation

| # | item | stage | blocked on |
|---|---|---|---|
| 13 | [Generator testing and saturation](./coding_plan_13_generator_testing.md) | **8** (pooled harness done, $58.78; Roger's marks: recovered 20 of 20, novel 19 of 20) | nothing |
| — | trait corpus target | decided 2026-10-16: **about 1,800, provisional** (README § "Trait corpus target") | revisit once review has grouped the kept candidates |
| — | role-judge rubric experiment ([plan](../pipeline/plan_role_rubric_experiment.md)) | **2** | Roger: agree it, and trim to four runs or keep eight (open_items, item C3); runs on the pod after the extraction's step 3 |
| — | **review itself** | ongoing | Roger's review sessions: 4,822 kept candidates awaiting review, 211 settled |
