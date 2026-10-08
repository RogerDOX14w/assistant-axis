# 12. Novelty measured in persona space, not in English

## 1. Idea

Answer "do we already have something close?" in the space we actually study: predict where a candidate's Qwen3-32B persona vector would land, from a text embedding of its description, and score novelty as distance from (or low density among) the 584 extracted vectors. It is independent of the English list because the geometry comes from the model's residual stream, which merges traits the model *enacts* identically and separates ones it enacts differently, and because antonyms land antipodal rather than adjacent, so pair completions and duplicates are told apart by sign. A scorer, not a generator.

## 2. Sources and tools (all local, all verified present)

- Vectors: `runpod_workspace/qwen/qwen-3-32b Roger 8slot/{traits,roles}/vectors/*.pt`, 303 traits + 281 roles; each a dict with `vector` of shape `[8 slots, 64 layers, 5120]`, bf16, type `pos_3` (mean activation over judge-score-3 responses). Canonical cell: slot 6, layer 25, corpus-mean-centred, soft-shear L=3 (`results_analysis.canonical_angles.whitening`).
- Descriptions: `data/{traits,roles}/instructions/*.json` `description` field. 87 traits and 56 roles have files but no vector yet (Sep 2026 additions awaiting one RunPod extraction): a free prospective test set.
- Candidates: `data/seed_queue.json` (972 entries, 156 with final descriptions, 13 drafts) plus whatever the generators produce, each with its one-line gloss.
- Embeddings: OpenAI `text-embedding-3-large` (client installed; ~$0.01 for 2,000 descriptions). Local fallback via `transformers` would need an embedding model download (sentence-transformers not installed; not verified).
- Fitting: scikit-learn 1.8 (ridge, PLS, GroupKFold), torch 2.10.
- Prior art to reuse: the May 2026 yield metric (TRAITS_TO_ADD.md § "dimensionality-yield", residual fraction on the top-20 PC subspace) and Strategy 1b's PC table.

## 3. Method

1. Load the 584 vectors at the canonical cell, centre on the corpus mean, apply soft-shear L=3, PCA. Keep K = 20-40 PCs (37 PCs carry 95% of variance). Store the PCA basis.
2. Embed every existing description and every candidate gloss (same prompt template: label + description, no instrument name). Also build a kind indicator (trait/role).
3. Fit `f: embedding -> PC scores` with ridge (alpha by inner CV) and, as a second model, PLS; compare both with the trivial baseline kNN-in-embedding (predict the weighted mean of the 5 nearest existing vectors). If kNN wins, the regression buys nothing and step 6 is run on kNN predictions.
4. Validate with GroupKFold where the group is the `arrangement` set (pairs, triangles, orthoplexes), so a held-out trait's antonym is not in the training fold. Metrics: per-PC R² (expect PC1-5 well above 0.4, unused PCs 10-20 near zero; the table itself is a finding), median cosine between predicted and actual centred vector, and recovery: is the actual vector of a hidden trait the nearest (top-1/top-5) existing vector to its predicted point?
5. Calibrate shrinkage: predictions regress toward the mean, so compute the held-out distribution of `d_pred = dist(pred, nearest other)` against `d_true` and z-score candidate novelty against `d_pred`, not against raw distances.
6. Score each candidate: (a) whitened distance to nearest existing vector and 5-NN density; (b) residual fraction of the predicted direction outside the top-20 PC subspace of the axis Gram matrix (the project's existing yield metric); (c) signed cosine to the nearest neighbour's centred vector: near and positive = duplicate, near-antipodal along an existing pair axis = pair completion; (d) the nearest three names. Write one CSV row per candidate into the shared registry.
7. Compare with the text-only scorer: Spearman between the two novelty ranks over the queue; hand the disagreement quantile (and only that) to an LLM or to Roger.
8. Cheap variant, no per-candidate prediction: for each unused PC (10, 13-20) fit the inverse map (PC score -> embedding direction) and report which candidate glosses project most extremely on it. This says what *kind* of candidate would be informative, complementing Strategy 1b's entity sortings.

## 4. Expected yield and biases

It re-ranks. Expect it to flag 5-15% of a few-hundred-candidate batch as duplicates-by-enactment that text distance misses, and to rescue some text-near candidates as antonyms. Biases: low-variance PCs, exactly where novelty lives, are the worst predicted, so scores are conservative (novel candidates look ordinary, never the reverse); roles dominate several top PCs; the space cannot see directions the model does not yet vary along (Strategy 1b's caveat), so a true gap in an unspanned direction scores as ordinary, not novel; question-set topic and register leak into vectors.

## 5. Cost

API: about $0.01-0.05 (embeddings only; LLM tokens only for disagreement review, tens of cents). Local: PCA on 584 x 5120 and CV over a few hundred fits, minutes on the Mac. Roger: about an hour to read the per-PC R² table and the top/bottom 30 candidates plus the disagreement list. Zero GPU unless variant B.

## 6. Testing

Hidden-trait recovery (step 4) is the primary test; a top-5 recovery rate under ~50% means "use it only as a sign/antonym check". Second test, free and prospective: score the 143 pending entities now, then after the next RunPod extraction compare predicted versus actual positions and novelty ranks. Third: known duplicates and known pairs (cautious/risk-averse/bold; calibrated/overconfident) must come out as near-positive and near-antipodal respectively.

## 7. Dependencies

Needs: candidate registry rows with label and gloss (from the generator workstreams), the text-only novelty scores for comparison, and the trait-hood filter upstream (this scorer is silent on trait-hood). Provides: per-candidate persona-space novelty, nearest-name list, duplicate/antonym verdict, and a per-PC predictability table useful to any workstream reasoning about the model's persona geometry.

## 8. Variants

A (above): text embedding -> PC scores, ridge/PLS versus kNN. B: same-model proxy: a single Qwen3-32B forward pass over a system prompt built from the gloss, reading slot 6 / layer 25, then a linear map from prompt-activation to the response-averaged vector. Same residual stream, so far less domain shift, but needs the 32B on RunPod (a few GPU-minutes per thousand candidates plus setup) and a regression fit on the 584 existing entities; worth it only if variant A's recovery rate is poor.

## 9. Open questions for Roger

- Fit on traits only (303) or traits plus roles with a kind covariate (584)? Candidates are traits, but roles double the sample.
- Wait for the pending extraction (143 entities, 727 training points) before trusting scores, or run now and use the pending set as the prospective test?
- Is the residual-fraction yield metric (May 2026) still the preferred novelty definition, or nearest-neighbour distance?
- Is variant B worth a small RunPod spend if A's per-PC R² collapses past PC8?

## Status (2026-10-08)

Untouched by the platform build.  M3 scores novelty on text embeddings and the overlap call; the
persona-space cosine is logged beside every overlap reading
([m3_overlap_test_readout.md](./m3_overlap_test_readout.md), the calibration by-product), which is the
data this plan's regression would train on.  The prospective test on the entities awaiting extraction
remains available once the next RunPod extraction runs.  Not scheduled.
