# M2 pilot readout: metric calibration on the existing corpus

2026-10-01, the M2 agent (Opus), for Roger's pilot decision.  Plan: [15_metric_calibration.md](./15_metric_calibration.md) and [coding_plan_platform.md](./coding_plan_platform.md) §9 tasks 11-18; task 19 (`--write-config`, the final run, the README) waits for the decisions at the end.

## Headline

- **Run**: [calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py) `--skip-llm`, three models (OpenAI `text-embedding-3-large`; local `BAAI/bge-large-en-v1.5`, CLS pooling; local `google/embeddinggemma-300m` through sentence-transformers with its "sentence similarity" prompt on both sides), five representations (`full`, `noprefix`, `w20`, `w14`, `strip`), five space variants (`raw`, `centred` on the fixed corpus mean, `centred_pc1`, `centred_pc3`, regularised `zca`), 659 trait files (the corpus directory's 661 entries include two `.md` files).
- **Cost**: $0.0153 in all ([usage.json](../../data/candidates/calibration/usage.json), cumulative over runs): 117,781 OpenAI tokens in 19 calls; the local models 128,899 and 156,186 tokens at zero cost.  The first run's spend line is in [run1.log](../../data/candidates/calibration/run1.log); the three reruns that fixed the drop-or-merge rule and the plot read every embedding from the cache.  Estimate was $0.021.
- **Compute**: embeddings 30-40 s per model on MPS; the 75 views about 10 minutes, almost all of it the leave-one-out residual (one 658x658 eigendecomposition per trait per centred view); wall time 590 s for a cached rerun ([run.json](../../data/candidates/calibration/run.json)).
- **Inputs built for this**: [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json) (284 antonym, 79 duplicate, 3 deliberate duplicate, 34 near-distinct, 5 polysemy rejects, 2,000 random; hand-checked in [labelled_pairs_curation.json](../../data/candidates/calibration/labelled_pairs_curation.json), 126 mechanical rows excluded with reasons), [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json) (106 of the census's 107 still in the corpus, 7 hand overrides in [contrast_cut_overrides.json](../../data/candidates/calibration/contrast_cut_overrides.json)), persona yields recomputed (below).
- **The three findings that matter for M3**:
  1. **Cosine cannot draw the covered line by itself.**  Roger's recorded duplicate rulings (seed-queue decisions, the pairing review) sit no closer than distinct neighbours (task a, AUC 0.42-0.74) and *farther* than the recorded antonyms (task b, AUC 0.28-0.56 in the `full` representation, below 0.5 in all but four cells).  At 95% recall of those duplicates, `t_hi` falls below `t_lo`, the 99th percentile of random pairs, for every model and variant.  The rulings are "area covered by" judgements, not paraphrases; the covered decision in M3 needs the adjudicator and a paraphrase-level calibration set (criterion g).
  2. **Gloss length**: truncating the corpus side to the glosses' ~14 words (`w14`) *helps* duplicate detection (task a and b rise for every model, most for bge: 0.44 to 0.57 and 0.41 to 0.52, raw) and costs a little self-recovery (gloss recall@1 0.979 to 0.971 OpenAI, 0.924 to 0.892 bge).  Matching lengths at embedding time works; lengthening glosses is not needed for the embedding.
  3. **Persona agreement is real but moderate**: pairwise text cosine against pairwise persona cosine (293 traits with vectors, 42,778 pairs) Spearman 0.50-0.55 in `raw`/`centred` for all three models, and only 0.16-0.18 in `zca`; local novelty (1 - NN cosine) against the persona yield 0.24-0.35.

## Persona yields (task c's target)

The May 2026 per-trait residual fractions survive only as the 24 bracketed values in [TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md) § "Strategy 1", computed against the top-20 PCs of the 60-axis Gram matrix, a basis that was not saved.  So the yield was **recomputed** as plan 12 step 1 describes: the 8-slot set ([qwen-3-32b Roger 8slot](<../../runpod_workspace/qwen/qwen-3-32b Roger 8slot/MANIFEST.json>)), slot 6, layer 25, 302 traits and 280 roles, centred on the traits+roles mean, soft shear L=3 (the goal / no-goal subspaces built on this data), and each trait's leave-one-out residual outside the top-K PCs of the other 581 entities.  293 of the 302 trait vectors match a current trait file (the other nine have no current file: renamed or deleted stems).  The pool's K_95 is 170, not plan 12's 37.  Cross-check: Spearman between the 24 bracketed values and the recomputed yield is 0.53 / 0.40 / 0.52 / 0.54 at K = 10 / 20 / 37 / 40.  Task (c) uses K = 37.

## Leave-one-out table: every model x representation x variant

(a) AUC, labelled duplicates over near-distinct neighbours (82 against 34); (b) AUC, duplicates over recorded antonyms (82 against 284; 0.5 = conflated, below 0.5 = antonyms closer); (c) Spearman of the novelty score with the persona yield (n = 293): local `cos` = 1 - NN cosine, `CSLS` = minus NN CSLS, `resid` = leave-one-out residual outside the top-K PCs of the other traits (centred variants only; K_95 in brackets); gloss r@1: each trait's M1 filter gloss ("label: gloss", 630 traits) retrieves its own trait first.  All rows, with sample sizes, p values and the K = 10/20/40 sensitivities, are in [loo_metrics.json](../../data/candidates/calibration/loo_metrics.json).


**openai**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.60 | 0.62 | 0.41 | 0.39 | 0.24 | 0.16 | – | – (–) | 0.979 |
| full | centred | 0.57 | 0.61 | 0.40 | 0.39 | 0.24 | 0.14 | 0.26 | 0.20 (366) | 0.979 |
| full | centred_pc1 | 0.59 | 0.63 | 0.40 | 0.39 | 0.24 | 0.15 | 0.24 | 0.19 (370) | 0.979 |
| full | centred_pc3 | 0.66 | 0.65 | 0.40 | 0.40 | 0.20 | 0.15 | 0.13 | 0.13 (376) | 0.984 |
| full | zca | 0.74 | 0.68 | 0.37 | 0.32 | 0.11 | 0.09 | – | – (–) | 0.994 |
| noprefix | raw | 0.64 | 0.64 | 0.48 | 0.45 | 0.22 | 0.15 | – | – (–) | 0.962 |
| noprefix | centred | 0.61 | 0.64 | 0.47 | 0.46 | 0.24 | 0.15 | 0.27 | 0.21 (365) | 0.962 |
| noprefix | centred_pc1 | 0.62 | 0.66 | 0.47 | 0.46 | 0.23 | 0.14 | 0.24 | 0.19 (369) | 0.959 |
| noprefix | centred_pc3 | 0.69 | 0.67 | 0.47 | 0.46 | 0.19 | 0.14 | 0.14 | 0.13 (375) | 0.957 |
| noprefix | zca | 0.75 | 0.68 | 0.39 | 0.34 | 0.12 | 0.10 | – | – (–) | 0.984 |
| w20 | raw | 0.63 | 0.65 | 0.46 | 0.43 | 0.26 | 0.14 | – | – (–) | 0.983 |
| w20 | centred | 0.60 | 0.64 | 0.45 | 0.44 | 0.25 | 0.14 | 0.26 | 0.21 (376) | 0.981 |
| w20 | centred_pc1 | 0.62 | 0.64 | 0.44 | 0.43 | 0.25 | 0.14 | 0.23 | 0.20 (380) | 0.981 |
| w20 | centred_pc3 | 0.67 | 0.66 | 0.43 | 0.43 | 0.21 | 0.14 | 0.15 | 0.15 (386) | 0.981 |
| w20 | zca | 0.74 | 0.68 | 0.40 | 0.35 | 0.11 | 0.08 | – | – (–) | 0.991 |
| w14 | raw | 0.62 | 0.64 | 0.48 | 0.46 | 0.25 | 0.17 | – | – (–) | 0.971 |
| w14 | centred | 0.60 | 0.63 | 0.47 | 0.46 | 0.24 | 0.16 | 0.23 | 0.18 (380) | 0.975 |
| w14 | centred_pc1 | 0.61 | 0.63 | 0.46 | 0.46 | 0.25 | 0.16 | 0.22 | 0.18 (384) | 0.973 |
| w14 | centred_pc3 | 0.65 | 0.65 | 0.45 | 0.46 | 0.20 | 0.14 | 0.13 | 0.13 (389) | 0.979 |
| w14 | zca | 0.74 | 0.67 | 0.42 | 0.38 | 0.09 | 0.06 | – | – (–) | 0.994 |
| strip | raw | 0.62 | 0.64 | 0.44 | 0.42 | 0.28 | 0.18 | – | – (–) | 0.976 |
| strip | centred | 0.60 | 0.63 | 0.43 | 0.42 | 0.28 | 0.17 | 0.26 | 0.22 (367) | 0.976 |
| strip | centred_pc1 | 0.61 | 0.65 | 0.43 | 0.42 | 0.27 | 0.18 | 0.24 | 0.21 (371) | 0.976 |
| strip | centred_pc3 | 0.68 | 0.67 | 0.42 | 0.42 | 0.23 | 0.18 | 0.14 | 0.15 (377) | 0.981 |
| strip | zca | 0.75 | 0.69 | 0.39 | 0.34 | 0.13 | 0.10 | – | – (–) | 0.994 |

**bge**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.44 | 0.53 | 0.41 | 0.41 | 0.26 | 0.22 | – | – (–) | 0.924 |
| full | centred | 0.46 | 0.54 | 0.41 | 0.41 | 0.29 | 0.22 | 0.22 | 0.07 (238) | 0.922 |
| full | centred_pc1 | 0.43 | 0.52 | 0.37 | 0.37 | 0.28 | 0.20 | 0.20 | 0.05 (242) | 0.929 |
| full | centred_pc3 | 0.42 | 0.50 | 0.34 | 0.34 | 0.24 | 0.20 | 0.10 | -0.01 (248) | 0.936 |
| full | zca | 0.56 | 0.53 | 0.31 | 0.28 | 0.09 | 0.08 | – | – (–) | 0.965 |
| noprefix | raw | 0.45 | 0.52 | 0.43 | 0.41 | 0.20 | 0.13 | – | – (–) | 0.903 |
| noprefix | centred | 0.46 | 0.52 | 0.41 | 0.41 | 0.25 | 0.15 | 0.17 | 0.04 (238) | 0.913 |
| noprefix | centred_pc1 | 0.43 | 0.50 | 0.38 | 0.37 | 0.22 | 0.13 | 0.14 | 0.03 (242) | 0.919 |
| noprefix | centred_pc3 | 0.46 | 0.52 | 0.37 | 0.36 | 0.20 | 0.16 | 0.08 | -0.02 (248) | 0.930 |
| noprefix | zca | 0.57 | 0.53 | 0.32 | 0.29 | 0.05 | 0.04 | – | – (–) | 0.956 |
| w20 | raw | 0.50 | 0.55 | 0.46 | 0.45 | 0.29 | 0.24 | – | – (–) | 0.905 |
| w20 | centred | 0.50 | 0.55 | 0.45 | 0.45 | 0.32 | 0.25 | 0.27 | 0.08 (240) | 0.914 |
| w20 | centred_pc1 | 0.47 | 0.52 | 0.39 | 0.39 | 0.28 | 0.22 | 0.21 | 0.03 (244) | 0.921 |
| w20 | centred_pc3 | 0.44 | 0.51 | 0.36 | 0.35 | 0.24 | 0.21 | 0.11 | -0.03 (250) | 0.929 |
| w20 | zca | 0.56 | 0.52 | 0.34 | 0.31 | 0.10 | 0.10 | – | – (–) | 0.957 |
| w14 | raw | 0.57 | 0.62 | 0.52 | 0.49 | 0.32 | 0.22 | – | – (–) | 0.892 |
| w14 | centred | 0.57 | 0.61 | 0.49 | 0.48 | 0.32 | 0.22 | 0.23 | 0.06 (240) | 0.902 |
| w14 | centred_pc1 | 0.51 | 0.55 | 0.43 | 0.42 | 0.28 | 0.21 | 0.17 | 0.03 (244) | 0.911 |
| w14 | centred_pc3 | 0.47 | 0.53 | 0.39 | 0.38 | 0.23 | 0.19 | 0.04 | -0.03 (249) | 0.909 |
| w14 | zca | 0.62 | 0.58 | 0.39 | 0.36 | 0.08 | 0.06 | – | – (–) | 0.944 |
| strip | raw | 0.47 | 0.56 | 0.43 | 0.42 | 0.32 | 0.25 | – | – (–) | 0.935 |
| strip | centred | 0.49 | 0.56 | 0.43 | 0.43 | 0.35 | 0.26 | 0.26 | 0.10 (239) | 0.930 |
| strip | centred_pc1 | 0.46 | 0.53 | 0.38 | 0.37 | 0.33 | 0.24 | 0.22 | 0.08 (243) | 0.935 |
| strip | centred_pc3 | 0.45 | 0.52 | 0.35 | 0.34 | 0.26 | 0.23 | 0.11 | -0.00 (249) | 0.935 |
| strip | zca | 0.57 | 0.54 | 0.33 | 0.30 | 0.12 | 0.11 | – | – (–) | 0.967 |

**gemma**

| representation | variant | (a) cos | (a) CSLS | (b) cos | (b) CSLS | (c) cos | (c) CSLS | (c) resid K=20 | (c) resid K95 (K) | gloss r@1 |
|---|---|---|---|---|---|---|---|---|---|---|
| full | raw | 0.69 | 0.68 | 0.56 | 0.52 | 0.26 | 0.21 | – | – (–) | 0.890 |
| full | centred | 0.63 | 0.66 | 0.55 | 0.52 | 0.28 | 0.20 | 0.16 | 0.10 (249) | 0.889 |
| full | centred_pc1 | 0.61 | 0.64 | 0.47 | 0.45 | 0.25 | 0.19 | 0.14 | 0.07 (252) | 0.890 |
| full | centred_pc3 | 0.61 | 0.64 | 0.39 | 0.38 | 0.21 | 0.17 | 0.09 | 0.04 (258) | 0.902 |
| full | zca | 0.67 | 0.64 | 0.37 | 0.34 | 0.10 | 0.09 | – | – (–) | 0.938 |
| noprefix | raw | 0.68 | 0.67 | 0.56 | 0.52 | 0.25 | 0.20 | – | – (–) | 0.882 |
| noprefix | centred | 0.62 | 0.66 | 0.55 | 0.52 | 0.28 | 0.20 | 0.15 | 0.10 (247) | 0.882 |
| noprefix | centred_pc1 | 0.60 | 0.64 | 0.48 | 0.46 | 0.25 | 0.19 | 0.12 | 0.06 (251) | 0.887 |
| noprefix | centred_pc3 | 0.60 | 0.64 | 0.39 | 0.38 | 0.21 | 0.16 | 0.09 | 0.02 (257) | 0.889 |
| noprefix | zca | 0.67 | 0.64 | 0.37 | 0.34 | 0.09 | 0.08 | – | – (–) | 0.924 |
| w20 | raw | 0.71 | 0.70 | 0.62 | 0.57 | 0.30 | 0.24 | – | – (–) | 0.882 |
| w20 | centred | 0.66 | 0.69 | 0.59 | 0.57 | 0.32 | 0.23 | 0.19 | 0.15 (250) | 0.887 |
| w20 | centred_pc1 | 0.64 | 0.66 | 0.52 | 0.49 | 0.30 | 0.22 | 0.16 | 0.11 (254) | 0.873 |
| w20 | centred_pc3 | 0.62 | 0.65 | 0.43 | 0.42 | 0.26 | 0.19 | 0.11 | 0.08 (260) | 0.881 |
| w20 | zca | 0.67 | 0.64 | 0.43 | 0.39 | 0.15 | 0.12 | – | – (–) | 0.922 |
| w14 | raw | 0.72 | 0.69 | 0.64 | 0.59 | 0.28 | 0.20 | – | – (–) | 0.868 |
| w14 | centred | 0.66 | 0.68 | 0.61 | 0.58 | 0.29 | 0.19 | 0.21 | 0.16 (251) | 0.860 |
| w14 | centred_pc1 | 0.64 | 0.65 | 0.53 | 0.51 | 0.25 | 0.17 | 0.18 | 0.14 (255) | 0.865 |
| w14 | centred_pc3 | 0.62 | 0.64 | 0.45 | 0.45 | 0.22 | 0.15 | 0.15 | 0.13 (261) | 0.870 |
| w14 | zca | 0.68 | 0.63 | 0.45 | 0.41 | 0.07 | 0.05 | – | – (–) | 0.916 |
| strip | raw | 0.70 | 0.68 | 0.58 | 0.54 | 0.28 | 0.23 | – | – (–) | 0.886 |
| strip | centred | 0.65 | 0.67 | 0.57 | 0.54 | 0.30 | 0.22 | 0.20 | 0.13 (250) | 0.892 |
| strip | centred_pc1 | 0.63 | 0.65 | 0.50 | 0.47 | 0.30 | 0.23 | 0.19 | 0.10 (253) | 0.892 |
| strip | centred_pc3 | 0.63 | 0.65 | 0.41 | 0.40 | 0.26 | 0.21 | 0.13 | 0.06 (259) | 0.895 |
| strip | zca | 0.67 | 0.64 | 0.39 | 0.36 | 0.15 | 0.13 | – | – (–) | 0.936 |


Reading the table: no cell reaches the plan's target `auc_dup_vs_distinct >= 0.85` (a target, not a gate: review amendment 2); the best are OpenAI `zca` (0.74-0.75) and EmbeddingGemma `w14`/`w20` `raw` (0.71-0.72).  `zca` buys (a) and gloss recall at the price of (b), and halves (c).  CSLS lifts (a) for bge (whose raw space has hubs) and does little elsewhere; it lowers (c) everywhere.  The plan's ordering of variants by (a)+(b)+(c) mean rank is: `raw` cos 3.7, `raw` CSLS 4.0, `centred` cos 4.0, `centred` CSLS 4.3, `centred_pc1` 5.7-6.0, `zca` cos 6.3, `centred_pc3` 6.3-7.3 ([summary.json](../../data/candidates/calibration/summary.json) `provisional.ranking`).

## Nearest-neighbour distributions and thresholds

[nn_hist_openai.png](../../data/candidates/calibration/nn_hist_openai.png), [nn_hist_bge.png](../../data/candidates/calibration/nn_hist_bge.png), [nn_hist_gemma.png](../../data/candidates/calibration/nn_hist_gemma.png): per variant, the leave-one-out NN cosine (filled), the same with recorded arrangement partners excluded (outline), the labelled pairs as rugs under the axis, and three lines: `t_hi` (95% duplicate recall), `t_lo` (99% of random pairs) and the upper fence of the partner-excluded bulk.  The bulk is unimodal in every panel; the right shoulder of the plain histogram is mostly recorded clean pairs, whose descriptions mirror each other, and shrinks once partners are excluded.

Threshold placement in the provisional variant (`raw`, cosine; all variants in [thresholds.json](../../data/candidates/calibration/thresholds.json)):

| model | representation | NN median (Q1-Q3) | upper fence | t_hi (all dup) | t_hi (certain) | t_lo | t_hi > t_lo | NN >= dup median | above fence |
|---|---|---|---|---|---|---|---|---|---|
| openai | full | 0.617 (0.569-0.675) | 0.834 | 0.397 | 0.418 | 0.466 | False | 600 | 0 |
| openai | w14 | 0.604 (0.560-0.658) | 0.806 | 0.376 | 0.433 | 0.458 | False | 615 | 6 |
| bge | full | 0.739 (0.709-0.778) | 0.881 | 0.545 | 0.575 | 0.654 | False | 646 | 6 |
| bge | w14 | 0.717 (0.684-0.758) | 0.868 | 0.531 | 0.559 | 0.626 | False | 633 | 6 |
| gemma | full | 0.742 (0.711-0.782) | 0.888 | 0.573 | 0.591 | 0.661 | False | 588 | 2 |
| gemma | w14 | 0.729 (0.696-0.764) | 0.866 | 0.515 | 0.560 | 0.644 | False | 571 | 4 |


`t_hi` lies below `t_lo` everywhere, so the duplicate rulings cannot set the covered threshold (finding 1; [QUESTIONS.md](./QUESTIONS.md) 26): 571-646 of the 659 traits have a nearest neighbour closer than the *median* labelled duplicate.  The low tail is therefore taken as plan 15 step 7 describes it, where a tail separates from the bulk: traits beyond the upper fence (Q3 + 1.5 IQR) of the NN distribution.  With partners included the fence catches 0-6 traits per model, all recorded pairs; with partners excluded, 14 (OpenAI), 9 (bge) and 6 (EmbeddingGemma) traits, 12 distinct pairs in all.

## Hubness census

k = 10 occurrence ([hubness.json](../../data/candidates/calibration/hubness.json), every representation): "hubs" are traits in 30 or more others' 10-NN lists.  Only the raw bge and EmbeddingGemma spaces have any (3 each); centring removes them and CSLS removes them too.  Skew of the 10-occurrence counts falls from 0.73-0.89 (raw) to 0.41-0.65 (centred) and further under CSLS.  Hubness is not a problem in any centred space; CSLS is not needed for it.

| model | variant | cos: skew N10 / max N10 / hubs (N10>=30) | top hubs (cos) | CSLS: skew / max / hubs | top hubs (CSLS) |
|---|---|---|---|---|---|
| openai | raw | 0.73 / 29 / 0 | [temperate](../../data/traits/instructions/temperate.json) 29, [aggressive](../../data/traits/instructions/aggressive.json) 28, [philosophical](../../data/traits/instructions/philosophical.json) 27, [benevolent](../../data/traits/instructions/benevolent.json) 26 | 0.40 / 22 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 22, [philosophical](../../data/traits/instructions/philosophical.json) 21, [homebody](../../data/traits/instructions/homebody.json) 20, [educational](../../data/traits/instructions/educational.json) 20 |
| openai | centred | 0.41 / 23 / 0 | [homebody](../../data/traits/instructions/homebody.json) 23, [honest](../../data/traits/instructions/honest.json) 22, [benevolent](../../data/traits/instructions/benevolent.json) 22, [contrarian](../../data/traits/instructions/contrarian.json) 21 | 0.39 / 21 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 21, [homebody](../../data/traits/instructions/homebody.json) 20, [educational](../../data/traits/instructions/educational.json) 19, [self-pitying](../../data/traits/instructions/self_pitying.json) 18 |
| openai | centred_pc1 | 0.41 / 22 / 0 | [plain-spoken](../../data/traits/instructions/plain_spoken.json) 22, [honest](../../data/traits/instructions/honest.json) 21, [flat](../../data/traits/instructions/flat.json) 21, [competitive](../../data/traits/instructions/competitive.json) 20 | 0.36 / 21 / 0 | [open-minded](../../data/traits/instructions/open_minded.json) 21, [homebody](../../data/traits/instructions/homebody.json) 18, [elderly](../../data/traits/instructions/elderly.json) 17, [exclusivist](../../data/traits/instructions/exclusivist.json) 17 |
| openai | centred_pc3 | 0.60 / 25 / 0 | [honest](../../data/traits/instructions/honest.json) 25, [staid](../../data/traits/instructions/staid.json) 25, [uncaring](../../data/traits/instructions/uncaring.json) 23, [malicious](../../data/traits/instructions/malicious.json) 22 | 0.33 / 19 / 0 | [avoidant](../../data/traits/instructions/avoidant.json) 19, [materialist](../../data/traits/instructions/materialist.json) 19, [open-minded](../../data/traits/instructions/open_minded.json) 19, [obsessive](../../data/traits/instructions/obsessive.json) 19 |
| openai | zca | 0.41 / 23 / 0 | [careless](../../data/traits/instructions/careless.json) 23, [perfectionist](../../data/traits/instructions/perfectionist.json) 21, [flexible](../../data/traits/instructions/flexible.json) 20, [truthful](../../data/traits/instructions/truthful.json) 20 | 0.42 / 23 / 0 | [cerebral](../../data/traits/instructions/cerebral.json) 23, [uptight](../../data/traits/instructions/uptight.json) 21, [friendly](../../data/traits/instructions/friendly.json) 21, [dignified](../../data/traits/instructions/dignified.json) 21 |
| bge | raw | 0.89 / 41 / 3 | [selfish](../../data/traits/instructions/selfish.json) 41, [good](../../data/traits/instructions/good.json) 33, [respectful](../../data/traits/instructions/respectful.json) 33, [laid-back](../../data/traits/instructions/laid_back.json) 29 | 0.52 / 28 / 0 | [respectful](../../data/traits/instructions/respectful.json) 28, [selfish](../../data/traits/instructions/selfish.json) 22, [calculating](../../data/traits/instructions/calculating.json) 21, [materialistic](../../data/traits/instructions/materialistic.json) 20 |
| bge | centred | 0.57 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [unassuming](../../data/traits/instructions/unassuming.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 25, [skeptical](../../data/traits/instructions/skeptical.json) 24 | 0.37 / 20 / 0 | [disagreeable](../../data/traits/instructions/disagreeable.json) 20, [selfish](../../data/traits/instructions/selfish.json) 20, [temperamental](../../data/traits/instructions/temperamental.json) 18, [benevolent](../../data/traits/instructions/benevolent.json) 18 |
| bge | centred_pc1 | 0.57 / 26 / 0 | [laid-back](../../data/traits/instructions/laid_back.json) 26, [skeptical](../../data/traits/instructions/skeptical.json) 25, [benevolent](../../data/traits/instructions/benevolent.json) 25, [unchallenging](../../data/traits/instructions/unchallenging.json) 24 | 0.46 / 20 / 0 | [benevolent](../../data/traits/instructions/benevolent.json) 20, [respectful](../../data/traits/instructions/respectful.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19, [collectivistic](../../data/traits/instructions/collectivistic.json) 19 |
| bge | centred_pc3 | 0.61 / 29 / 0 | [informational](../../data/traits/instructions/informational.json) 29, [harsh](../../data/traits/instructions/harsh.json) 25, [unchallenging](../../data/traits/instructions/unchallenging.json) 25, [collectivistic](../../data/traits/instructions/collectivistic.json) 24 | 0.32 / 20 / 0 | [collectivistic](../../data/traits/instructions/collectivistic.json) 20, [emphatic](../../data/traits/instructions/emphatic.json) 19, [even-tempered](../../data/traits/instructions/even_tempered.json) 18, [dogmatic](../../data/traits/instructions/dogmatic.json) 18 |
| bge | zca | 0.38 / 23 / 0 | [self-accepting](../../data/traits/instructions/self_accepting.json) 23, [confident](../../data/traits/instructions/confident.json) 20, [speculative](../../data/traits/instructions/speculative.json) 20, [self-critical](../../data/traits/instructions/self_critical.json) 20 | 0.27 / 22 / 0 | [modest](../../data/traits/instructions/modest.json) 22, [petty](../../data/traits/instructions/petty.json) 20, [languishing](../../data/traits/instructions/languishing.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19 |
| gemma | raw | 0.86 / 32 / 3 | [composed](../../data/traits/instructions/composed.json) 32, [opinionated](../../data/traits/instructions/opinionated.json) 31, [circumspect](../../data/traits/instructions/circumspect.json) 30, [staid](../../data/traits/instructions/staid.json) 28 | 0.54 / 22 / 0 | [unambitious](../../data/traits/instructions/unambitious.json) 22, [unadventurous](../../data/traits/instructions/unadventurous.json) 21, [flourishing](../../data/traits/instructions/flourishing.json) 20, [loyal](../../data/traits/instructions/loyal.json) 20 |
| gemma | centred | 0.65 / 25 / 0 | [absentee](../../data/traits/instructions/absentee.json) 25, [theoretical](../../data/traits/instructions/theoretical.json) 25, [placid](../../data/traits/instructions/placid.json) 24, [unchallenging](../../data/traits/instructions/unchallenging.json) 23 | 0.46 / 19 / 0 | [languishing](../../data/traits/instructions/languishing.json) 19, [rigid](../../data/traits/instructions/rigid.json) 19, [opinionated](../../data/traits/instructions/opinionated.json) 18, [well-connected](../../data/traits/instructions/well_connected.json) 18 |
| gemma | centred_pc1 | 0.69 / 26 / 0 | [humorless](../../data/traits/instructions/humorless.json) 26, [placid](../../data/traits/instructions/placid.json) 26, [laid-back](../../data/traits/instructions/laid_back.json) 26, [unchallenging](../../data/traits/instructions/unchallenging.json) 25 | 0.51 / 22 / 0 | [rigid](../../data/traits/instructions/rigid.json) 22, [working-class](../../data/traits/instructions/working_class.json) 18, [self-reliant](../../data/traits/instructions/self_reliant.json) 18, [whimsical](../../data/traits/instructions/whimsical.json) 17 |
| gemma | centred_pc3 | 0.57 / 27 / 0 | [placid](../../data/traits/instructions/placid.json) 27, [calm](../../data/traits/instructions/calm.json) 25, [gentle](../../data/traits/instructions/gentle.json) 24, [self-accepting](../../data/traits/instructions/self_accepting.json) 23 | 0.49 / 19 / 0 | [gentle](../../data/traits/instructions/gentle.json) 19, [self-accepting](../../data/traits/instructions/self_accepting.json) 19, [friendly](../../data/traits/instructions/friendly.json) 18, [efficient](../../data/traits/instructions/efficient.json) 18 |
| gemma | zca | 0.24 / 20 / 0 | [speculative](../../data/traits/instructions/speculative.json) 20, [temperamental](../../data/traits/instructions/temperamental.json) 20, [unchallenging](../../data/traits/instructions/unchallenging.json) 20, [opinionated](../../data/traits/instructions/opinionated.json) 20 | 0.52 / 23 / 0 | [sycophantic](../../data/traits/instructions/sycophantic.json) 23, [detail-oriented](../../data/traits/instructions/detail_oriented.json) 20, [obsessive](../../data/traits/instructions/obsessive.json) 20, [worldly](../../data/traits/instructions/worldly.json) 20 |


## Drop-or-merge table

From [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md).  Each trait's nearest neighbour once its recorded arrangement partners are excluded (plan 15 step 8; the antonym probe that would do the excluding is M3's), kept when beyond the partner-excluded fence (OpenAI 0.761, bge 0.851, EmbeddingGemma 0.863) for at least one model.  Cosine per variant for the first model that flagged it; no row is a recorded arrangement or a labelled deliberate duplicate.  Several are near-synonyms ([dramatic](../../data/traits/instructions/dramatic.json) / [theatrical](../../data/traits/instructions/theatrical.json), [dependable](../../data/traits/instructions/dependable.json) / [trustworthy](../../data/traits/instructions/trustworthy.json), [sarcastic](../../data/traits/instructions/sarcastic.json) / [sardonic](../../data/traits/instructions/sardonic.json), [honest](../../data/traits/instructions/honest.json) / [truthful](../../data/traits/instructions/truthful.json), [abstract](../../data/traits/instructions/abstract.json) / [conceptual](../../data/traits/instructions/conceptual.json) / [theoretical](../../data/traits/instructions/theoretical.json)); one is an unrecorded antonym pair ([self-blaming](../../data/traits/instructions/self_blaming.json) / [blame-shifting](../../data/traits/instructions/blame_shifting.json)), which the embedding cannot tell from a duplicate.

| trait | nearest | flagged by | raw | centred | centred_pc1 | centred_pc3 | zca | arrangement | deliberate dup | description A | description B |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [abstract](../../data/traits/instructions/abstract.json) | [theoretical](../../data/traits/instructions/theoretical.json) | bge, gemma | 0.857 | 0.7328 | 0.6876 | 0.6182 | 0.3372 |  |  | This means focusing on concepts, patterns, theoretical frameworks, and high-level principles rather than concrete specifics or practical details. | This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects. |
| [dependable](../../data/traits/instructions/dependable.json) | [trustworthy](../../data/traits/instructions/trustworthy.json) | openai, bge | 0.793 | 0.6868 | 0.686 | 0.6908 | 0.2677 |  |  | This means consistently following through on commitments, being someone others can count on, and reliably doing what you say you will do without needing to be reminded or checked on. | This means being reliable, dependable, and worthy of confidence, consistently following through on commitments and acting in ways that justify others placing their trust in you. |
| [self-blaming](../../data/traits/instructions/self_blaming.json) | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | openai, bge | 0.775 | 0.7123 | 0.6975 | 0.6853 | 0.3281 |  |  | This means that when something goes wrong, it is always one's own fault, never the colleague's or bad luck, and one's own part is all one sees. | This means that when something goes wrong, it is always somebody else's fault, the colleague's or bad luck, and one's own part in it is never admitted. |
| [passionate](../../data/traits/instructions/passionate.json) | [zealous](../../data/traits/instructions/zealous.json) | openai, gemma | 0.7627 | 0.6571 | 0.6531 | 0.6272 | 0.2551 |  |  | This means showing intense enthusiasm, strong emotions, fervor, and deep investment or commitment to the topics being discussed. | This means showing fervent enthusiasm, passionate advocacy, intense commitment, and unwavering dedication to causes, beliefs, or topics being discussed. |
| [conceptual](../../data/traits/instructions/conceptual.json) | [theoretical](../../data/traits/instructions/theoretical.json) | bge | 0.8765 | 0.7613 | 0.716 | 0.6602 | 0.3507 |  |  | This means working primarily with ideas, theories, and abstract frameworks rather than focusing on concrete details, specific examples, or practical implementation. | This means emphasizing abstract concepts, theoretical models, conceptual frameworks, and underlying principles rather than focusing on concrete, practical, or empirical aspects. |
| [empathetic](../../data/traits/instructions/empathetic.json) | [compassionate](../../data/traits/instructions/compassionate.json) | gemma | 0.8709 | 0.7414 | 0.7394 | 0.7172 | 0.3866 |  |  | This means showing genuine understanding and consideration for human emotions, perspectives, and experiences, often by acknowledging feelings, demonstrating emotional awareness, and responding with compassion and warmth. | This means showing emotional warmth and sensitivity to others' pain and suffering, and responding to distress with genuine empathy and care. |
| [absolutist](../../data/traits/instructions/absolutist.json) | [universalist](../../data/traits/instructions/universalist.json) | bge | 0.8539 | 0.6912 | 0.6889 | 0.6581 | 0.3628 |  |  | This means maintaining that certain truths, values, and principles are universal and unchanging, applying to all people and situations without exception or cultural variation. | This means applying consistent principles and values across all cultures and contexts, believing that fundamental moral standards and human values should be uniform regardless of cultural, historical, or situational differences. |
| [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | openai | 0.8107 | 0.7301 | 0.7007 | 0.6441 | 0.2574 |  |  | This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair. | This means using dramatic flair, exaggerated language, vivid imagery, and delivering content as if performing on stage with sweeping gestures and commanding presence. |
| [sarcastic](../../data/traits/instructions/sarcastic.json) | [sardonic](../../data/traits/instructions/sardonic.json) | openai | 0.7876 | 0.7191 | 0.718 | 0.6997 | 0.2375 |  |  | This involves using sharp, ironic, or cutting remarks that often mock or show contempt, typically through verbal irony where the intended meaning is opposite to the literal words used. | This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge. |
| [melodramatic](../../data/traits/instructions/melodramatic.json) | [dramatic](../../data/traits/instructions/dramatic.json) | openai | 0.7874 | 0.7027 | 0.7021 | 0.6611 | 0.2834 |  |  | This means using exaggerated emotion, theatrical language, dramatic intensity, and over-the-top expression to convey ideas. | This means using emotionally charged language, vivid and theatrical descriptions, and presenting information with heightened intensity and dramatic flair. |
| [honest](../../data/traits/instructions/honest.json) | [truthful](../../data/traits/instructions/truthful.json) | openai | 0.7656 | 0.6576 | 0.638 | 0.6225 | 0.1776 |  |  | This means communicating truthfully and transparently, acknowledging uncertainty and limitations, and avoiding deception, misdirection, or strategic omission of information. | This means presenting information accurately and completely, avoiding lies, fabrication, or misrepresentation of facts, and correcting misunderstandings rather than exploiting them. |
| [wry](../../data/traits/instructions/wry.json) | [sardonic](../../data/traits/instructions/sardonic.json) | openai | 0.7651 | 0.6852 | 0.6839 | 0.6687 | 0.2354 |  |  | This means using clever, sardonic humor that often involves ironic observations, skeptical commentary, or twisted logic to highlight contradictions and absurdities. | This involves using dry, cutting humor and ironic observations to mock or highlight the absurdities, contradictions, and foolishness in situations, people, or society, often with a cynical or biting edge. |


With partners included, the traits beyond the fence form four recorded pairs whose descriptions mirror each other: [oblivious](../../data/traits/instructions/oblivious.json) / [observant](../../data/traits/instructions/observant.json), [northern hemisphere](../../data/traits/instructions/northern_hemisphere.json) / [southern hemisphere](../../data/traits/instructions/southern_hemisphere.json), [straight](../../data/traits/instructions/straight.json) / [gay](../../data/traits/instructions/gay.json), [introverted](../../data/traits/instructions/introverted.json) / [extroverted](../../data/traits/instructions/extroverted.json) (second table of [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md)).

## Contrast-clause ablation

110 descriptions change when their clause is cut: 104 of the census's 107 (the census's academic was deleted on 2026-09-28 and survives only as a [seed-queue entry](../../data/seed_queue.json), and [inquisitive](../../data/traits/instructions/inquisitive.json) and [opinionated](../../data/traits/instructions/opinionated.json), the renamed assertive, no longer have a clause; agitated is now [excitable](../../data/traits/instructions/excitable.json)) plus the 6 new hits below.  Full results per model and variant in [contrast_ablation.json](../../data/candidates/calibration/contrast_ablation.json); (e), (g) and (i) need the LLM and were skipped (`--skip-llm`), all ten are recorded with their status.


**variant raw**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.967 / 0.972 / 0.987 / 0.985 | 0.953 / 0.963 / 0.989 / 0.986 | 0.958 / 0.969 / 0.987 / 0.985 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.040; 0.95 | -0.037; 0.95 | -0.033; 0.86 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.40 → 0.51 | 0.48 → 0.52 | 0.62 → 0.67 |
| (b) same: AUC dup>near-distinct full → strip | 0.51 → 0.56 | 0.49 → 0.53 | 0.73 → 0.73 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 15/66 / 5/29 / 0/6 | 3/9 / 18/66 / 6/29 / 2/6 | 2/9 / 24/66 / 3/29 / 1/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.033 / 0.004 / -0.001; 0.032 | -0.024 / -0.015 / -0.009; 0.014 | -0.022 / -0.005 / -0.002; 0.020 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.813; 0.97 | 0.835; 0.95 | 0.799; 1.00 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.521 → 0.527 | 0.497 → 0.492 | 0.521 → 0.518 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.50 → 0.48 | 0.46 → 0.45 | 0.47 → 0.47 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h strip, j keep | b strip, d strip, f keep, h tie, j tie | b strip, d strip, f keep, h tie, j tie |
| N class NN unchanged | 0.78 | 0.67 | 0.78 |
| recommendation (rule) | keep | keep | keep |

**variant centred**

| criterion | openai | bge | gemma |
|---|---|---|---|
| (a) mean cos(full, stripped): N / P / S / new | 0.953 / 0.961 / 0.981 / 0.980 | 0.911 / 0.929 / 0.977 / 0.972 | 0.921 / 0.942 / 0.973 / 0.970 |
| (a) mean change of cos to the recorded partner on stripping (P); share moved away | -0.054; 0.95 | -0.052; 0.84 | -0.057; 0.84 |
| (b) pairs touching a stripped trait: AUC syn>ant full → strip | 0.41 → 0.52 | 0.48 → 0.50 | 0.63 → 0.67 |
| (b) same: AUC dup>near-distinct full → strip | 0.49 → 0.56 | 0.49 → 0.56 | 0.72 → 0.71 |
| (c) NN changed on stripping: N / P / S / new | 2/9 / 15/66 / 4/29 / 0/6 | 1/9 / 20/66 / 6/29 / 2/6 | 1/9 / 21/66 / 4/29 / 2/6 |
| (d) mean Δcos antonym / synonym / unrelated; margin vs unrelated | -0.044 / 0.007 / 0.000; 0.045 | -0.028 / -0.014 / 0.004; 0.032 | -0.038 / -0.009 / 0.001; 0.040 |
| (f) minimal pairs: cos(XY, YX); accuracy | 0.757; 0.97 | 0.662; 0.97 | 0.580; 1.00 |
| (h) Spearman text vs persona cosine, all pairs: full → strip | 0.523 → 0.530 | 0.504 → 0.502 | 0.550 → 0.545 |
| (j) NN agreement with the other models (stripped traits): full → strip | 0.51 → 0.48 | 0.49 → 0.45 | 0.51 → 0.48 |
| (e) (g) (i) | skipped (`--skip-llm`) | skipped (`--skip-llm`) | skipped (`--skip-llm`) |
| votes (strip/keep/tie) | b strip, d strip, f keep, h strip, j keep | b strip, d strip, f keep, h tie, j keep | b strip, d strip, f keep, h tie, j keep |
| N class NN unchanged | 0.78 | 0.89 | 0.89 |
| recommendation (rule) | keep | keep | keep |


What the criteria say, the same way for all three models:

- **The clause pulls toward the pole it names** (a): stripping it moves a P-class description away from its recorded partner for 84-95% of the paired ones, by 0.03-0.06 cosine; the vector itself moves little (mean cosine between the two forms 0.91-0.99).
- **Stripping helps the pair tasks** (b, d): syn-over-antonym AUC on pairs touching a stripped trait rises (OpenAI 0.40 to 0.51 raw), and recorded antonyms move apart by 0.01-0.05 more than random pairs do.
- **Yet every model reads "X rather than Y" as X** (f): 95-100% of 40 minimal pairs land nearer their own pole, with cos(XY, YX) 0.58-0.84; none behaves as a bag of words.
- **Persona agreement and cross-model agreement do not move** (h, j: changes within 0.01 and 0.04).
- **The N class** loses its nearest neighbour for 2 of 9 under OpenAI ([critical](../../data/traits/instructions/critical.json), [reactive](../../data/traits/instructions/reactive.json)), 3 of 9 under bge raw ([independent](../../data/traits/instructions/independent.json), [progressive](../../data/traits/instructions/progressive.json), [reactive](../../data/traits/instructions/reactive.json)), 2 of 9 under EmbeddingGemma ([pluralist](../../data/traits/instructions/pluralist.json), [reactive](../../data/traits/instructions/reactive.json)): [reactive](../../data/traits/instructions/reactive.json)'s neighbour changes under every model, from [impulsive](../../data/traits/instructions/impulsive.json) to [improvisational](../../data/traits/instructions/improvisational.json), [urgent](../../data/traits/instructions/urgent.json) or [quick-witted](../../data/traits/instructions/quick_witted.json), the case the N class exists to catch (whether the stripped neighbour is worse is for (e) and your marks).

**Recommendation per model: keep the clauses for now (all three).**  Plan 15's rule ("keep if the criteria are no worse with them") gives `keep`: the votes are close (OpenAI 3 strip to 2 keep in `raw`, but the N class keeps only 7 of 9 neighbours, under the 8 the acceptance asks for; bge and EmbeddingGemma 2 to 1 or 2 to 2), and the evidence for stripping is a modest gain on pair tasks whose labels are themselves weak (finding 1).  The decisive criterion is (e), the blinded judgement, together with your 30 marks in [contrast_comparisons_for_marks.md](./contrast_comparisons_for_marks.md) (key in [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json); do not open it before marking).

## Gloss length

The split filter's glosses run to about 14 words; corpus descriptions to 25 (median).  With the corpus side cut to about 14 words at a word boundary (`w14`):

| model (raw, cosine) | (a) full → w14 | (b) full → w14 | (c) full → w14 | gloss recall@1 full → w14 |
|---|---|---|---|---|
| text-embedding-3-large | 0.60 → 0.62 | 0.41 → 0.48 | 0.24 → 0.25 | 0.979 → 0.971 |
| bge-large-en-v1.5 | 0.44 → 0.57 | 0.41 → 0.52 | 0.26 → 0.32 | 0.924 → 0.892 |
| embeddinggemma-300m | 0.69 → 0.72 | 0.56 → 0.64 | 0.26 → 0.28 | 0.890 → 0.868 |

Most of the labelled duplicates have a short member (56 of 82 are an M1 filter gloss against a full description), and the duplicates gain most where length is matched.  `w20` sits between the two; `noprefix` helps (b) for OpenAI (0.41 to 0.48) and changes little else.  **For M3**: matching length at embedding time (cut both sides to about 14 words, or embed the description's first clause) is better for the duplicate decision than lengthening glosses to the 18-43 band, and costs 1-3 points of self-recovery.  The gloss recovery itself is high already: 97.9% (OpenAI) of existing traits are found first from their own 14-word gloss.

## Ten most and least novel existing traits

Provisional metric: OpenAI, `raw`, `full`, 1 - NN cosine.  With partners excluded (left) the least novel are the drop-or-merge pairs; with partners included (right) they are clean pairs whose descriptions mirror each other.  The most novel are memberships and coined labels the corpus has few neighbours for.

| partners excluded: most novel | nearest | 1 - cos | partners excluded: least novel | nearest | 1 - cos |
|---|---|---|---|---|---|
| [young](../../data/traits/instructions/young.json) | [urban](../../data/traits/instructions/urban.json) | 0.614 | [theatrical](../../data/traits/instructions/theatrical.json) | [dramatic](../../data/traits/instructions/dramatic.json) | 0.189 |
| [lowbrow](../../data/traits/instructions/lowbrow.json) | [populist](../../data/traits/instructions/populist.json) | 0.612 | [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | 0.189 |
| [elderly](../../data/traits/instructions/elderly.json) | [early-bird](../../data/traits/instructions/early_bird.json) | 0.604 | [dependable](../../data/traits/instructions/dependable.json) | [trustworthy](../../data/traits/instructions/trustworthy.json) | 0.207 |
| [lurker](../../data/traits/instructions/lurker.json) | [plugged-in](../../data/traits/instructions/plugged_in.json) | 0.602 | [trustworthy](../../data/traits/instructions/trustworthy.json) | [dependable](../../data/traits/instructions/dependable.json) | 0.207 |
| [late-adopter](../../data/traits/instructions/late_adopter.json) | [slow-witted](../../data/traits/instructions/slow_witted.json) | 0.601 | [sardonic](../../data/traits/instructions/sardonic.json) | [sarcastic](../../data/traits/instructions/sarcastic.json) | 0.212 |
| [anecdotal](../../data/traits/instructions/anecdotal.json) | [experiential](../../data/traits/instructions/experiential.json) | 0.596 | [sarcastic](../../data/traits/instructions/sarcastic.json) | [sardonic](../../data/traits/instructions/sardonic.json) | 0.212 |
| [clannish](../../data/traits/instructions/clannish.json) | [collectivistic](../../data/traits/instructions/collectivistic.json) | 0.589 | [melodramatic](../../data/traits/instructions/melodramatic.json) | [dramatic](../../data/traits/instructions/dramatic.json) | 0.213 |
| [antifeminist](../../data/traits/instructions/antifeminist.json) | [egalitarian](../../data/traits/instructions/egalitarian.json) | 0.582 | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | [self-blaming](../../data/traits/instructions/self_blaming.json) | 0.225 |
| [confabulatory](../../data/traits/instructions/confabulatory.json) | [deceitful](../../data/traits/instructions/deceitful.json) | 0.580 | [self-blaming](../../data/traits/instructions/self_blaming.json) | [blame-shifting](../../data/traits/instructions/blame_shifting.json) | 0.225 |
| [philistine](../../data/traits/instructions/philistine.json) | [materialistic](../../data/traits/instructions/materialistic.json) | 0.578 | [honest](../../data/traits/instructions/honest.json) | [truthful](../../data/traits/instructions/truthful.json) | 0.234 |

| all neighbours: most novel | nearest | 1 - cos | all neighbours: least novel | nearest | 1 - cos |
|---|---|---|---|---|---|
| [anecdotal](../../data/traits/instructions/anecdotal.json) | [experiential](../../data/traits/instructions/experiential.json) | 0.596 | [motivated-reasoning-immune](../../data/traits/instructions/motivated_reasoning_immune.json) | [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) | 0.182 |
| [confabulatory](../../data/traits/instructions/confabulatory.json) | [deceitful](../../data/traits/instructions/deceitful.json) | 0.580 | [motivated-reasoning-prone](../../data/traits/instructions/motivated_reasoning_prone.json) | [motivated-reasoning-immune](../../data/traits/instructions/motivated_reasoning_immune.json) | 0.182 |
| [course-correcting](../../data/traits/instructions/course_correcting.json) | [hands-on](../../data/traits/instructions/hands_on.json) | 0.551 | [intellectually dishonest](../../data/traits/instructions/intellectually_dishonest.json) | [intellectually honest](../../data/traits/instructions/intellectually_honest.json) | 0.184 |
| [chaotic](../../data/traits/instructions/chaotic.json) | [systems-thinker](../../data/traits/instructions/systems_thinker.json) | 0.545 | [intellectually honest](../../data/traits/instructions/intellectually_honest.json) | [intellectually dishonest](../../data/traits/instructions/intellectually_dishonest.json) | 0.184 |
| [superstitious](../../data/traits/instructions/superstitious.json) | [ritualistic](../../data/traits/instructions/ritualistic.json) | 0.544 | [dramatic](../../data/traits/instructions/dramatic.json) | [theatrical](../../data/traits/instructions/theatrical.json) | 0.189 |
| [sycophantic](../../data/traits/instructions/sycophantic.json) | [sincere](../../data/traits/instructions/sincere.json) | 0.541 | [theatrical](../../data/traits/instructions/theatrical.json) | [dramatic](../../data/traits/instructions/dramatic.json) | 0.189 |
| [philistine](../../data/traits/instructions/philistine.json) | [aesthete](../../data/traits/instructions/aesthete.json) | 0.538 | [extroverted](../../data/traits/instructions/extroverted.json) | [introverted](../../data/traits/instructions/introverted.json) | 0.190 |
| [just-world-believing](../../data/traits/instructions/just_world_believing.json) | [trusting](../../data/traits/instructions/trusting.json) | 0.535 | [introverted](../../data/traits/instructions/introverted.json) | [extroverted](../../data/traits/instructions/extroverted.json) | 0.190 |
| [bullying](../../data/traits/instructions/bullying.json) | [cowardly](../../data/traits/instructions/cowardly.json) | 0.531 | [intrinsically-motivated](../../data/traits/instructions/intrinsically_motivated.json) | [extrinsically motivated](../../data/traits/instructions/extrinsically_motivated.json) | 0.205 |
| [tunnel-visioned](../../data/traits/instructions/tunnel_visioned.json) | [rigid](../../data/traits/instructions/rigid.json) | 0.531 | [extrinsically motivated](../../data/traits/instructions/extrinsically_motivated.json) | [intrinsically-motivated](../../data/traits/instructions/intrinsically_motivated.json) | 0.205 |

## New contrast-clause hits beyond the census

The mechanical detector over all 659 current files finds six descriptions with a clause that the 2026-09-23 census did not classify (reported, not classified; their mechanical cuts are in [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json) `new_hits`, and they are stripped in the `strip` representation):

| trait | cut |
|---|---|
| [confabulatory](../../data/traits/instructions/confabulatory.json) | ", rather than as a guess" |
| [engaged](../../data/traits/instructions/engaged.json) | ", rather than being apathetic or indifferent" |
| [figurative](../../data/traits/instructions/figurative.json) | ", rather than the plain words" |
| [frugal](../../data/traits/instructions/frugal.json) | " rather than paying for the extra" |
| [unplugged](../../data/traits/instructions/unplugged.json) | " rather than screens" |
| [vulnerable-narcissistic](../../data/traits/instructions/vulnerable_narcissistic.json) | " instead of asking for anything" |

[excitable](../../data/traits/instructions/excitable.json) (formerly agitated) keeps the census's class S.

## Decisions for Roger

1. **Space variant.**  The plan's three tasks put `raw` and `centred` (cosine) level at the top (mean rank 3.7 and 4.0; `centred` is best on (c)); `zca` wins (a) but costs (b), (c) and persona agreement (h: 0.52 to 0.16); removing PCs does not help.  CSLS is not needed: centring removes the few hubs.  *My recommendation*: `centred` on the fixed corpus mean, cosine, which keeps plan 15 §11's convention and is what the directional residual needs; the difference from `raw` is within noise.
2. **K for the directional score.**  K_95 is 366-389 (OpenAI) and 238-261 (local), and the residual at K_95 tracks the persona yield worse than at K = 20 (0.20 against 0.26 OpenAI centred; 0.07 against 0.22 bge).  *Recommendation*: K = 20, with K_95 recorded beside it ([QUESTIONS.md](./QUESTIONS.md) 25).
3. **Drop-or-merge pass now?**  The tail is short: 12 pairs with partners excluded, half of them plausible near-synonyms.  *Recommendation*: read the 12 rows above (five minutes) rather than run a separate pass; mark any merge in the seed queue as usual.  [self-blaming](../../data/traits/instructions/self_blaming.json) / [blame-shifting](../../data/traits/instructions/blame_shifting.json) may want recording as a pair.
4. **The paid criteria (e) and (g): needed.**  Estimate $0.88 ($0.29 Haiku paraphrases of all 659 descriptions, $0.59 Sonnet blinded judgement of 60 comparisons in both orders; [calibrate_llm.py](../../assistant_axis/gapgen/calibrate_llm.py), tested with a fake client, not run).  The local criteria leave the contrast decision close, and (g)'s paraphrases are also what M3 needs for a covered threshold and paraphrase recall, since the duplicate rulings cannot supply one (finding 1, [QUESTIONS.md](./QUESTIONS.md) 26).  The command would be [calibrate_metric.py](../../data_analysis/gap_generation/calibrate_metric.py) without `--skip-llm` (budget default $5, under the $10 cap), then a rerun to fold the paraphrases into (g) and (i).
5. **Your 30 marks** in [contrast_comparisons_for_marks.md](./contrast_comparisons_for_marks.md), before (e) runs, so the judge's agreement with you is known.
6. **Gloss length for M3**: match length at embedding time (cut descriptions to about 14 words, or embed glosses and descriptions both truncated) rather than lengthen the glosses.  A yes or no settles M3's representation.
7. **Local model for M3**: EmbeddingGemma beats bge on (a) and (b) in every variant (0.69 against 0.44 on (a), raw) and ties on (c) and (h); bge's raw space has hubs.  *Recommendation*: EmbeddingGemma as the local model, OpenAI as the primary; or keep all three if the cost of a third model (zero, about 30 s per 5,000 texts) is acceptable.  This changes the platform plan's "two models" (decision table, §1) and is yours to make.
8. **Dependency**: `sentence-transformers` 6.1.0 was added for EmbeddingGemma ([QUESTIONS.md](./QUESTIONS.md) 24).

## Files

Outputs in [data/candidates/calibration/](../../data/candidates/calibration/): [loo_metrics.json](../../data/candidates/calibration/loo_metrics.json), [thresholds.json](../../data/candidates/calibration/thresholds.json), [hubness.json](../../data/candidates/calibration/hubness.json), [contrast_ablation.json](../../data/candidates/calibration/contrast_ablation.json), [summary.json](../../data/candidates/calibration/summary.json), [run.json](../../data/candidates/calibration/run.json), [usage.json](../../data/candidates/calibration/usage.json), [drop_or_merge.md](../../data/candidates/calibration/drop_or_merge.md), [labelled_pairs.json](../../data/candidates/calibration/labelled_pairs.json), [contrast_cuts.json](../../data/candidates/calibration/contrast_cuts.json).  [metric_config.json](../../data/candidates/metric_config.json) does not exist yet: task 19 writes it after these decisions.
