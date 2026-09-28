# 10. Novelty detector by semantic embedding

## 1. Idea
Embed every existing trait as `label — one-line gloss` and every candidate the same way, and answer "nearest existing traits, how close, and is the closest a synonym or an antonym?" by cosine distance plus a small supervised polarity probe. It is not a generator, so list bias is irrelevant; its job is to be cheap (~$0.05 per 10,000 candidates), calibrated against pairs we already know the answer for, and to send only the grey zone to an LLM.

## 2. Sources and tools
- **Corpus**: `data/traits/instructions/*.json` (385 files; `description` median 25 words), `data/traits/trait_list.json` (label → description), `data/traits/trait_antonyms_v4.json` (240 antonym judgements with 1-5 scores), `data/seed_queue.json` (972 entries with `status`: 37 `exists`, 12 `superseded`, 82 `not_adopted` with Roger's reasons, e.g. aloof → reserved/detached, intemperate → gluttonous/indulgent, balanced → moderate).
- **OpenAI `text-embedding-3-large`** via the installed `openai` 2.17 client. Listed at $0.13 per 1M input tokens (`-small`: $0.02); verify on the pricing page before the first run. 3072-d, `dimensions=` lets us truncate.
- **Local models** (Mac, `transformers` 5.1 + `torch` 2.10 with MPS; `sentence-transformers` and `faiss` are *not* installed, and are not needed at this scale: 385 × 10k cosines is a numpy matmul):
  - `Qwen/Qwen3-Embedding-0.6B` (Apache-2.0, 1024-d, last-token pooling, instruction prefix). Same family as the generator model, which is a small plus: a word this encoder handles well is a word Qwen3-32B knows.
  - `BAAI/bge-large-en-v1.5` (MIT, 1024-d, CLS pooling) as the second local model. Both need ~20 lines of pooling code; licences checked from memory, not fetched.
- **Optional probe training data**: published adjective synonym/antonym pair sets (Nguyen et al. 2017 style) exist on GitHub; licence not verified. Our own corpus supplies enough pairs, so treat this as optional.

## 3. Method
1. **Representation**. Three texts per entity: (a) bare label; (b) `label: gloss` where the gloss is the first ~20 words after "This means (being X:)" of the description (no LLM needed for existing traits; candidates must arrive with a gloss, see §7); (c) full description. Primary index = (b). (a) is kept only as a polysemy detector; (c) only for the final LLM adjudication prompt.
2. **Index**. Embed all 385 (b)-texts with each model; cache as `.npz` keyed by (model, text hash) with a manifest. Existing-trait embedding cost: 385 × ~35 tokens ≈ 13k tokens, negligible.
3. **Query**. For each candidate: cosine similarity to all existing traits under each model; keep top-5 with similarity, plus the neighbour's `negative_label`, whether that partner has a file, and the neighbour's `arrangement` (triangles/rings are near each other by design).
4. **Polysemy flag**. Compare the top-3 neighbours of (a) and (b); if disjoint, or cos(a, b) is below the calibrated 10th percentile, mark `ambiguous_label` (the word's common sense is not the intended sense: the disciplinary/economic/empowered failure).
5. **Synonym vs antonym**. Train a logistic-regression probe on pair features `[|e1−e2|, e1⊙e2, cos]` using our labelled pairs: antonyms = 124 mutual clean pairs + v4 entries scored ≥4; synonyms = paraphrase pairs from step 6 + the `exists`/`superseded` seed entries + deliberate near-duplicates (cautious/risk_averse, HEXACO vs Big Five poles). Apply to every candidate–neighbour pair above the "close" threshold. Additional cheap check: if the candidate is close to N *and* N's partner P exists, whichever of N, P is closer names the pole; if N has no partner (65 non-X half-pairs) and the probe says antonym, report `pair_completion`.
6. **Calibration**. Build three cosine distributions: synonym-like (rejected duplicates, `exists` entries, and 385 LLM paraphrases of existing glosses at Haiku cost ≈ $0.10), antonym (clean pairs), unrelated (2,000 random pairs). Choose two thresholds: `t_hi` (synonym recall 0.95 on the held-out half) and `t_lo` (below which 99% of unrelated pairs fall). Report where antonyms sit; expect them between, overlapping synonyms, which is why step 5 exists.
7. **Decision**. Both models above `t_hi` and probe says synonym → `covered` (report neighbour). Both below `t_lo` → `new`. Anything else (disagreement, grey zone, probe probability 0.3-0.7, ambiguous label) → one Haiku call: "Given candidate C (gloss) and traits N1..N3 (full descriptions), is C a duplicate, an antonym, or distinct? One line why." Log usage with `MultiModelUsage` (add embedding prices to `judge_pricing.py`).
8. **Review ordering**. Dedupe survivors among themselves at `t_hi` (cluster, keep one representative, record cluster size). Then farthest-first (k-center greedy) with the existing corpus pre-seeded as chosen centres, so the first item shown is the one least like anything existing *or* already shown. Emit `nearest_existing`, `cluster_size` and the LLM line per row for Roger.

## 4. Expected yield and biases
Per 10,000 candidates, expect roughly 40-60% `covered` (generators recreate the list), 10-20% grey, the rest `new`. Over-flags as covered: traits that share vocabulary but differ in scope (cautious vs risk-averse; descriptions, not words, define scope here, and glosses only partly carry that). Under-flags: multiword labels whose gloss wording diverges from ours, and alignment-region traits (rationalizing, ends-justify-means) where general encoders are coarse. Antonyms of half-pairs surface as high-value rather than as noise, which is the intended bias.

## 5. Cost
- OpenAI: 10k × ~35 tokens ≈ 350k tokens ≈ $0.05 at `-large`. Calibration paraphrases ≈ $0.10.
- Local: two models over 10k short texts, minutes on MPS; one-off ~3 GB of weights.
- Haiku adjudication: ~1,500 grey calls × ~700 tokens ≈ $1.5-2.
- Roger: ~1 h to hand-label the 200-item evaluation set; then only survivors, ordered.

## 6. Testing
- **Paraphrase recall**: for each of the 385 traits, an LLM paraphrase of the gloss under a different label; the original must be top-1 (target ≥ 0.95) and flagged `covered`.
- **Rejection replay**: the September rejects (aloof, intemperate, balanced, emotive, forthright, ...) must come back `covered` with the neighbour Roger named.
- **Antonym separation**: the 124 clean pairs must be classified antonym, not synonym (target F1 ≥ 0.9 on a held-out fold).
- **Hand-labelled set**: 200 real candidates stratified by similarity bin, labelled covered / antonym-completion / new by Roger; report precision and recall of `covered`, and the fraction sent to the LLM. Recall of `new` matters most: a killed gap is worse than a wasted review slot.
- **Model agreement**: Spearman of nearest-neighbour similarities between OpenAI and the local model; disagreement rate is the LLM budget.

## 7. Dependencies
Needs from others: candidates in a registry format with `label`, `gloss` (required), `source`, and optionally a full description; a trait-hood filter upstream (this detector says "already have", not "is a trait"). Provides: per-candidate `novelty.json` rows (top-5 neighbours, relation, flags, decision), the cached embedding index, the calibrated thresholds, and the review ordering used by every generator's testing step (hidden-trait recovery is scored with this index).

## 8. Variants
- **Description-only** (embed full descriptions, generate one for each candidate first): better scope fidelity, but a candidate description costs ~$0.02 and the gloss version already handles the rejections we know about. Use it only as the LLM-adjudication input.
- **Persona-vector cross-check** for *adopted* candidates: once a trait is extracted, its vector cosine to existing vectors is an independent duplicate test in the model's own space (the HEXACO/Big Five near-duplicates are known there). Post hoc only; not part of the cheap scan.

## 9. Open questions for Roger
1. Is a deliberate near-duplicate (a second Big Five/HEXACO pole) `covered` or `new`? The detector should report it; the policy for the decision is yours.
2. Target trade-off: recall 0.95 on `covered` at the cost of ~15% grey-zone LLM calls, or a tighter grey zone and more reviewing?
3. Is OpenAI acceptable as one of the two models, or should both be local for reproducibility (Qwen3-Embedding + bge)?
4. Should the review ordering weight the alignment region (oversampled by design), e.g. show its survivors first?

## Addendum (2026-09-18, after Roger's note on metric geometry)

The cosine in step 3 is angular distance on unit vectors (equivalent to
Euclidean distance after normalisation); the consequential choice is the
**origin**, not cosine versus modulus.  Raw embeddings share a large common
component (anisotropy: Ethayarajh 2019; Gao et al. 2019), so all cosines
sit in a narrow band.  Changes:

1. **Centre** every vector on the mean of the pooled existing-trait and
   candidate embeddings, drop the top principal component (the template /
   format direction; "all-but-the-top", Mu and Viswanath 2018), renormalise.
   Report threshold sensitivity to the choice of mean (corpus-only vs pooled).
2. **Hubness correction** on nearest-neighbour similarities: cross-domain
   similarity local scaling (Conneau et al. 2018), subtracting each point's
   mean similarity to its k nearest neighbours, so a hub does not "cover"
   candidates it does not resemble.
3. **Two novelty scores, reported separately.**  *Local*: corrected
   nearest-neighbour cosine (is any single trait near?).  *Directional*:
   residual fraction of the candidate's centred direction outside the
   top-K principal subspace of the existing traits (K = 20-40, the effective
   dimensionality), the same yield score the May 2026 Strategy 1b analysis
   used in persona space.  A candidate near no single trait can still be a
   blend (low residual); one with a moderate neighbour can still add a
   direction (high residual).  Farthest-first ordering uses the local score;
   the directional score is a second ranking column for review.
4. Plan 15 calibrates all of this on the existing corpus before thresholds
   are set.

## Addendum 2 (2026-09-23, Roger on glosses)

The gloss for an existing trait is its **whole description**, not the first
~20 words: the description is the formal definition and the label its
summary.  Candidate glosses are written to the same form ("This means ...")
and the same length band (18-43 words) so that text length does not become a
distance signal.  Length is not a problem for any model in this plan (30-60
tokens against limits of 512 and up); the things to control are the shared
template prefix (centering, or strip it), contrast clauses ("rather than X")
that pull an embedding toward the contrasted concept (the antonym probe
covers this; plan 15 measures it), and query/document asymmetry (embed both
sides in the same mode).

## Resolution of the open questions (2026-09-23)

1. A deliberate near-duplicate (a standard's pole beside a plain trait) is reported as
   `covered` with a `deliberate_duplicate` flag, so no third version is proposed.
2. Aim for recall 0.95 on `covered`; accept ~15% of candidates going to the LLM (about $2 per
   10,000); Roger's review time is the scarce resource, not tokens.
3. OpenAI text-embedding-3-large is acceptable as one of the two models, with a local model
   beside it for reproducibility.
4. Alignment-region survivors are shown first, as a separate section of the review list.
