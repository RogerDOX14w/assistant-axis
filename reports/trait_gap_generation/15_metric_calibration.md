# 15. Metric calibration: local versus directional novelty on the existing corpus

## 1. Idea
Before any candidate is scored, find out which embedding-space metric agrees with
what we already know: which pairs of existing traits are duplicates or rejects,
which are distinct neighbours, and which additions turned out to be informative in
persona space (the May 2026 residual-fraction yield scores in TRAITS_TO_ADD.md
§ Strategy 1b).  A leave-one-out experiment over the 385 trait files costs cents
and settles the origin, whitening, hubness and local-versus-directional questions
that plans 10 and 11 otherwise have to guess.  Prompted by Roger's observation
(2026-09-18) that gaps are under-represented *directions* on a hypersphere of
centred embeddings, not empty spots on a map.

## 2. Sources and tools
The 385 trait descriptions and labels; the seed queue's `exists`, `superseded`
and `not_adopted` entries and the September pairing review as labelled pairs
(duplicates, antonyms, near-but-distinct, polysemy rejects); the May 2026
per-trait residual-fraction scores if recoverable from the analysis script
(else recompute from the extracted vectors, plan 12's step 1); text-embedding-3-large
and one local model (as in plan 10); numpy, scikit-learn.

## 3. Method
1. Embed `label: gloss` for every existing trait under both models.  *Label*
   is `positive_label` (a candidate's surface form, for candidates); *gloss*
   is the statement of the intended sense: for an existing trait its whole
   `description` (Roger, 2026-09-23: that is the formal definition; do not
   truncate), for a candidate a gloss of the same kind, written by the
   trait-hood filter (plan 14) in the corpus form ("This means ...") and
   length band (18-43 words).  Matching form and length on both sides keeps
   distances comparable (embeddings drift with text length) and resolves
   polysemy.  Variants for step 2: with and without the shared "This means"
   prefix; and a check that truncating to ~20 words is not better than the
   full text (expected not to be).  Embed both sides in the same
   query/document mode where the model distinguishes them.
2. Build variants of the space: raw; mean-centred; centred with top-1 and top-3
   PCs removed; ZCA-whitened; each renormalised.
3. For each trait, leave-one-out: nearest-neighbour cosine (plain and with
   cross-domain similarity local scaling), 5-NN mean cosine, and residual
   fraction outside the top-K principal subspace of the other 384 (K = 10, 20,
   40).  Record the nearest neighbour's identity.
4. Evaluate each metric on three tasks: (a) separate labelled duplicate pairs
   from labelled distinct-neighbour pairs (AUC); (b) separate antonym pairs from
   synonym pairs, to see how much each metric conflates them (it will; measure
   how much); (c) rank-correlate the directional score with the May 2026
   persona-space yield scores for the traits that have both, which is the only
   check that a text-space metric predicts what we care about.
5. **Contrast-clause ablation** (Roger, 2026-09-23: a research question about
   the embedding model, not a reason to edit descriptions).  For the 107
   descriptions that contain a contrast construction
   (`contrast_clauses_census.md` in this directory: 10 necessary for sense,
   68 naming the other pole, 29 stylistic), embed each in two forms: as
   written, and with the contrast clause removed (the clause is the span from
   "rather than" / "instead of" / "but not" / "without being" to the end of
   its clause; strip mechanically, hand-check the 107 cuts once).  Then, per
   model and per space variant:
   (a) how far the vector moves (cosine between the two forms), and whether it
       moves *toward* the named pole (cosine to the partner file's embedding,
       for the paired traits), which is the negation-handling question: a
       model that reads "rather than X" as "not X" moves little or away, one
       that bags words moves toward X;
   (b) whether the labelled-pair tasks in step 4 score better with or without
       the clause, separately for the N, P and S classes;
   (c) whether the leave-one-out nearest neighbour changes, and to what.
   Criteria (Roger, 2026-09-23, plus additions):
   (d) *antonym margin*: established clean pairs move further apart when
       the clause is stripped, while known duplicates and paraphrases do
       not; score the gap between the two distributions, not the antonym
       distance alone (stripping content can push everything apart);
   (e) *blinded neighbour judgement*: for a sample of traits, show a larger
       model the top-5 lists from both variants, blinded, random order,
       reason first, then a preference, repeated with the order swapped;
       Roger labels 30 of the same comparisons so the judge's agreement
       with him is known before its verdict counts;
   (f) *minimal-pair negation test*: embed "X rather than Y" and "Y rather
       than X" for a few dozen pole pairs; a model that handles the
       construction gives distinct vectors each nearer its own pole, a
       bag-of-words model gives near-identical ones (no labels needed,
       decisive per model);
   (g) *paraphrase invariance vs clause sensitivity*: a cheap-model
       paraphrase of each description should move the vector less than
       removing the clause does; if not, the clause effect is within noise;
   (h) *agreement with persona space*: for the traits with extracted Qwen
       vectors, which variant's pairwise text distances correlate better
       with persona-vector distances (plan 12 loads them);
   (i) *held-out recovery* (plan 13) with and without clauses;
   (j) *cross-model agreement* on nearest neighbours, with and without.
   The decision is per model: keep the clauses in the embedded text if the
   criteria are no worse with them, else strip them at embedding time only.  Candidate
   glosses are then treated the same way as existing descriptions.  The
   N class is the check that stripping does not cost sense: if their nearest
   neighbours change on stripping, the clause was carrying the sense.
6. Hubness census: distribution of how often each trait is someone's nearest
   neighbour, per variant; report the hubs.
7. **Thresholds come from the distribution, not from the corpus minimum**
   (Roger, 2026-09-23).  The existing corpus almost certainly contains some
   very similar pairs (near-duplicates that were never caught, plus the
   deliberate ones: a standard's version beside a plain trait, clean-pair
   antonyms), so the smallest nearest-neighbour distance in it is not the
   distance we want between traits.  Instead plot the leave-one-out
   nearest-neighbour distance distribution per variant, look for where its
   bulk sits and where a low tail separates from it, and place the
   "covered" threshold against the bulk, with the labelled duplicate and
   distinct pairs from step 4 as anchors.  Report the tail explicitly.
8. **Side product: a drop-or-merge list.**  The traits in the low tail
   (nearest existing neighbour closer than the chosen threshold, after the
   antonym probe has excluded pair partners) are candidates for Roger to
   consider dropping or merging.  Output them as a table: trait, nearest
   neighbour, distance under each variant, whether the pair is a recorded
   arrangement (pair, triangle, sequence, standard-derived duplicate), and
   the two descriptions side by side.  Recorded arrangements and deliberate
   standard duplicates are listed but flagged as expected; the rest are the
   real candidates.
9. Recommend the variant, K, thresholds and the contrast-clause policy for
   plans 10 and 11; write them into a small config file the scorer reads,
   with the evaluation numbers beside them.

## 4. Expected yield and biases
A metric choice with evidence, plus one list of corpus members to consider
dropping or merging (the near-duplicate tail).  Expect centering to widen the
cosine band substantially and local scaling to remove a handful of hubs;
expect the directional score to correlate with persona-space yield only
moderately (text embeddings encode topic and sentiment, not persona geometry).

## 5. Cost
Under $0.10 of embeddings, minutes of local compute, half an hour of Roger's
time to read one table.

## 6. Testing
The experiment is the test; its outputs are the AUCs and correlations above,
plus a sanity list (the ten most and least novel existing traits under the
chosen metric, which Roger can eyeball).

## 7. Dependencies
Needs plan 10's embedding code (shared) and the labelled-pair set plan 11
assembles from the pairing review; provides the metric config both consume,
and the K for plan 12's comparison.

## 8. Variants
A: text embeddings only (as above).  B: repeat steps 2-5 in persona space on
the 584 extracted vectors, so the two spaces' hubness and effective
dimensionality can be compared directly.

## 9. Open questions for Roger
Whether the mean should be the corpus mean or the pooled corpus-plus-candidate
mean (the latter is less dependent on our list, the former is what the persona
pipeline does); whether K should be fixed or set per space by the 95%-variance
rule.

## 10. Roger Feedback
On the mean, I don't expect it to make a large difference (unless we had an extreme outlier), but I incline towards using a fixed mean>

On K, I'm not familiar enough with the problem space — eitehr decide your self, or have a more deatiled dicussion with me.
## 11. Resolution (2026-09-23)

Mean: the fixed corpus mean (the persona pipeline's convention).  K: per space by the
95%-variance rule (37 components in persona space per plan 12), with sensitivity reported at
K = 10, 20, 40; the residual score is a ratio so the dependence is gradual, and step 4's
labelled-pair tasks will show a badly wrong K.
