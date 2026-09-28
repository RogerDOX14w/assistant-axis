# 13. Testing the generators and estimating saturation

## 1. Idea
Treat each generator as a sampling occasion over an unknown population of trait concepts; our
existing set is one more sample. Hidden-label recovery says how well each generator sees what
we already know (recall, rank, by region); the overlap between *independent* generators gives
a capture-recapture estimate of the population and of how far we are from saturation. This
workstream generates nothing, so it adds no bias of its own.

## 2. Sources and tools
- `data/traits/instructions/*.json` (387 files: label, description, antonym, arrangement).
- `data/seed_queue.json` (972 entries): provenance (`source`, `section`, `tags`) and outcome
  (`status`); the 82 `not_adopted` entries with `decision` text are a free negative set.
- The novelty detector (its workstream) for concept-level matching: local embeddings, paid
  LLM tie-break.
- `MultiModelUsage`/`usage.json` per generator run (mandatory per CLAUDE.md): the cost column.
- Estimators (Chapman, Chao2, Good-Turing coverage): numpy, closed form. No external data.

## 3. Method
1. **Classify generators by independence** from each generator plan's inputs:
   - *Independent of our list*: thesaurus/WordNet walks, corpus-mined adjectives, published
     trait lexicons (Allport-Odbert, Goldberg), character-tag lists. LLM cold generation with
     no seeds is independent of the list but shares the prior that shaped it: "weakly
     dependent".
   - *Seeded by our list*: "what's missing from these labels", antonym completion,
     embedding-neighbour expansion, PCA-of-our-vectors naming, arrangement hunting.
   - *Already harvested*: named-taxonomy checklists. Their items are in the list because of
     them; exclude those labels by provenance or recovery is trivially 100 %.
2. **Region labels** for every existing trait: one Haiku call per file, ~9 regions
   (communication style; cognitive/epistemic; moral stance; social/interpersonal; emotional
   temperament; alignment/AI-agent; transient state; identity/demographic; physical).
   Cross-check against k≈10 clustering of description embeddings; Roger settles disagreements.
3. **Held-out recovery**:
   - Independent generators: the whole list is held out by construction. Run once; report
     recall, and recall-vs-output-size (rank if ranked, else recall at N = 500/1000/2000 in
     emitted order).
   - Seeded generators: 5-fold, hide 20 % stratified by region; hide both poles of a pair
     together (the visible pole gives the hidden one away via antonym completion), with a
     single-pole condition reported separately. Cost is 5× one run, so cap test runs.
   - Drop from every denominator the labels whose provenance is that generator's source.
4. **Concept-level match**: a candidate (label + gloss) *recovers* a hidden trait if the
   detector matches it to the trait's description at the synonym threshold; it
   *pair-recovers* if it matches the antonym pole (counted separately: "diligent" for a hidden
   "lazy" covers the axis, not the concept). Hidden means hidden from the generator only; the
   matcher sees the full list. Report at strict and loose thresholds, since every number here
   moves with granularity.
5. **Bias profiles**: per generator, recall by region, the region distribution of its *novel*
   output (the detector classifies novel candidates too), and its hit rate on the
   `not_adopted` negatives (a precision proxy for wasted review time).
6. **Capture-recapture** on concept-deduplicated output of independent generators only (the
   detector clusters candidates into concepts; our list is occasion 0):
   - Chapman per pair: N̂ = (n_A+1)(n_B+1)/(m+1) − 1.
   - Chao2 over k ≥ 3 occasions: N̂ = S_obs + ((k−1)/k)·f1²/(2f2), f1/f2 = concepts seen by
     exactly one/two generators; Good-Turing coverage Ĉ = 1 − f1/Σ as the saturation number.
     Stratified by region, then summed.
   - Accumulation curve (unique concepts vs. cumulative candidates, Chao extrapolation); the
     end slope is the marginal yield that decides when to stop.
   - Assumptions, printed with the output: closed population (fixed by the trait-hood filter
     and threshold); equal catchability (false: "honest" is caught by everything, so LP is
     biased low and Chao2 is a lower bound); independent occasions (false for any two
     LLM-based generators, also biasing low). So N̂ is a lower bound on "concepts reachable
     by generators of these kinds", not a Platonic count.
7. **Dashboard**: `tools/generator_dashboard.py` reads the registry and each run's
   `usage.json`; prints a Markdown table per generator: cost, candidates, pass trait-hood,
   novel-vs-list, marginal-novel (vs. everything seen before it; order-dependent, labelled
   so), adopted (lags review), recall strict/loose, pair-recall, negatives hit rate, region
   row, novel per dollar and per Roger-minute. Re-run after every generator run.

## 4. Expected yield and biases
Numbers, not candidates: ~10 generator rows, a region-by-generator matrix, N̂ and coverage
with intervals. Expected pattern: dictionary generators recover style/temperament well and
alignment traits poorly; seeded LLM generators recover alignment and moral stances well
because the visible list primes them; states and physical traits are under-recovered
everywhere. Recall is inflated by common traits, and the estimators inherit that; region
stratification corrects it only partly.

## 5. Cost
Region labels ≈ $0.50 (400 Haiku calls). Matching rides on the detector: embeddings free,
tie-breaks ≈ $0.002 each, under $5 in total. Folds multiply seeded-generator cost by five;
at ≤ $2 per test run that is ≤ $10 per seeded generator. Estimators: seconds locally. Roger:
~30 min on region disagreements, ~15 min per dashboard refresh.

## 6. Testing
- Matcher sanity: LLM-paraphrase 40 existing labels+glosses and 40 antonym glosses; concept
  recall > 90 %, antonyms must land in pair-recovered. A miss is a detector bug, not a finding.
- Contamination: recall with and without provenance exclusion; a large gap means a generator
  is re-deriving our sources.
- Estimator sanity: simulate N = 2000 concepts, log-normal catchability, four correlated
  samplers; confirm bias directions and interval coverage. Leave-one-generator-out
  instability flags failing independence.
- Spot check: Roger reads 20 random "recovered" and 20 "novel" verdicts.

## 7. Dependencies
Needs: the registry format (id, label, gloss, generator, run id, emitted order); detector
verdicts with threshold and antonym flag; trait-hood pass/fail; `usage.json` per run.
Provides: region labels for existing traits, the independence classification, recall and bias
tables, N̂ and coverage, the stop rule.

## 8. Variants
- **Cheap**: no folds; test only independent generators, leave seeded ones untested. Loses
  the profiles of the generators most likely to be biased.
- **Full**: add bootstrap intervals over generators and regions, and Shapley attribution of
  marginal novelty instead of run order.

## 9. Open questions for Roger
- Reference set: the 387 files only, or also queued `paired`/`done` labels?
- The nine regions above, or the seed-queue chunk structure?
- Stop rule in novel-per-dollar or per-review-minute? Review time looks like the bottleneck.
- Spend ≈ $10 on an extra independent generator purely to give Chao2 a third occasion?
- Strict or loose threshold as the headline recall and N̂?
