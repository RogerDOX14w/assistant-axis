# 13. Testing the generators and estimating saturation

Rewritten 2026-10-12 against the platform as built and the review as measured; the version of 2026-10-08 predates
M3, the recovery harness, M1's regions and the first review session.  Roger's answers to the open questions are in
§ 9 and are folded into the method.

## 1. Idea
Treat each generator as a sampling occasion over an unknown population of trait concepts; our existing set is one
more sample.  Hidden-label recovery says how well each generator sees what we already know (recall, rank, by
region); the overlap between *independent* generators gives a capture-recapture estimate of the population and of
how far we are from saturation.  This workstream generates nothing, so it adds no bias of its own.  [Note that some
of our generators, for example the AI alignment generator, are sampling a separate distribution, so we need to
consider whether applying this to them makes sense.]

What has changed since the idea was written: the review now exists, so "novel" has a ground truth (promoted after
Roger's review) beside the cheap proxy (kept by M3); the review is the binding constraint (about 150 terms an hour
against $1-30 of API per generator, measured 2026-10-11); and the first repetition measurement is in (about 40% of
a later lexical batch attaches to the first reviewed batch at the 3-edge level).  So the question this plan answers
has sharpened from "how good is each generator" to **"how many distinct concepts are left, per mechanism, and what
does each cost in review hours"**.

## 2. Sources and tools
- The corpus: [data/traits/instructions/](../../data/traits/instructions/) (932 files on 2026-10-12; label,
  description, antonym, arrangement, `renamed_from`).  **This is the testing reference** (§ 9, question 1): never
  the seed queue, which is now fed by the generators themselves, and not a file that came from gap generation once
  promotions become files (excluded by provenance, as a generator's own source is excluded).
- M1's regions on every corpus trait, [corpus_regions.json](../../data/candidates/corpus_regions.json) (seven in the
  corpus: cognitive/epistemic 203, emotional temperament 166, social/interpersonal 165, identity/demographic 150,
  moral stance 143, communication style 95, alignment/AI-agent 10; transient states and physical traits live in
  their own tracks, the states and physical passes), and on every candidate, in its registry row.
- The registry, [registry.jsonl](../../data/candidates/registry.jsonl): one row per candidate with its sources
  (generator, run, rank, score), M1's verdict, tags and region, M3's decision and every overlap reading, and the
  review block `apply` writes.  Every number in this plan is computed from it, so the dashboard is a read of the
  registry, not a run.
- The review's decision logs under [data/candidates/review/](../../data/candidates/review/) and the registry's
  review blocks: the truth of "novel" (promoted), "already had it" (merged into a corpus trait or queue entry) and
  "not worth it" (rejected, parked); the `not_adopted` and `superseded` seed-queue entries are the older free
  negative set.
- The recovery harness, built: [recovery_test.py](../../data_analysis/gap_generation/recovery_test.py) over
  [recovery.py](../../assistant_axis/gapgen/recovery.py) — hide a share of the corpus by region (arrangements
  hidden whole), run M3 against the reduced corpus, match every kept candidate against the hidden traits by label
  and then by the overlap call, report recall by region and arrangement kind, precision, false covers and cost.
- `usage.json` per run (mandatory, CLAUDE.md): the cost column.
- Estimators (Chapman, Chao2, Good-Turing coverage, Chao accumulation extrapolation): numpy, closed form.

## 3. Method
1. **Classify generators by independence**, from each generator's inputs, as they now exist:
   - *Independent of our list*: the censuses (TDA, Allport), Roget's heads (its harvest; the head *map* is seeded,
     see below), the WordNet trait closure, IPIP's item clusters, the base model, masked-LM frames (plan 04).
   - *Seeded by our list*: the antonym check (partners of unpaired labels), WordNet antonyms of unpaired labels,
     Roget's pair-completion class (heads reached by mapping our labels), the structural operators of plan 09.
   - *A separate population*: the alignment sweep — document-driven dispositions of an AI assistant, where the
     corpus is thin by design; tested on its own terms (§ 3.6).
   - *Not generators*: the states and physical passes re-route tagged words; they are reported under the generator
     that produced the word.
   A label whose provenance is a generator's own source (an Allport-derived name against the Allport census) leaves
   that generator's denominator.
2. **Regions**: M1's, already on every corpus trait and candidate (§ 9, question 2); no separate labelling pass.
   The one check is that M1's vocabulary still matches the nine the plan named; seven appear in the corpus.
3. **Held-out recovery**, with the harness as built:
   - Independent generators: hide 10% of the corpus by region, two seeds, M3 against the rest, match; the whole
     list is held out from the generator by construction, so one harness run per generator run gives recall, and
     recall against emitted order gives recall-at-N where the generator ranks.
   - Seeded generators: the harness hides from M3 only; a true held-out needs the hidden labels removed from the
     generator's seed too.  Roget supports this (`roget_generate.py recover --hidden-frac`); the others report the
     harness-side number and say so.  Pairs are hidden whole (the visible pole gives the hidden one away).
   - Both numbers are read by region and at the two match levels of § 3.4.
4. **Concept-level match**: M3's own — a label match, else the overlap call at **M3's cut-off rule** (3, raised to 4
   where the alignment score raises it), so that recall is measured by the instrument that decides coverage in
   production (§ 9, question 5).  A match to the antonym pole is *pair-recovery*, counted separately.  The strict
   column (4 everywhere) stands beside the headline, as the gate reports strict beside its collapsed agreement.
5. **Bias profiles**, per generator: recall by region; the region distribution of its kept output; its hit rate on
   the negative set; and two things the review now supplies — its **promote share** (promoted of kept; 55% for the
   TDA census) and its **repetition against earlier batches**, read off the all-batches review graph as the share of
   its kept terms with a 3-edge or 4-edge to a term already decided (the pre-handled machinery of
   [coding_plan_review.md](./coding_plan_review.md) § 11 makes those free at review).  Repetition replaces the old
   order-dependent "marginal novelty": it is measured against what was decided, not against run order.
6. **Capture-recapture by mechanism**, on concept-deduplicated kept output (M3's readings cluster candidates into
   concepts; the corpus is occasion 0):
   - Occasions are **mechanisms, not generators** (§ 9, question 4): the lexicon walks are one occasion (censuses,
     Allport, Roget, WordNet — the same English adjective lexicon sampled four ways), then behaviour items (IPIP),
     the base model, masked-LM frames, and the corpus.  Two LLM-based occasions are not independent and the
     estimate says so.
   - Chapman per pair, Chao2 over k ≥ 3 occasions with Good-Turing coverage as the saturation number, stratified by
     region and summed; the alignment sweep separately, where the specs and the papers are already two occasions
     (218 and 247 candidates, 13.6% overlap at dedup).
   - **The accumulation curve per mechanism** is the number the review budget turns on: unique kept concepts
     against cumulative candidates, Chao-extrapolated, its end slope the marginal yield.  The censuses alone (TDA
     2,818 words, Allport-hi 3,646) give the first reading of the lexical ceiling; the first estimate from the
     review is corpus 932 plus roughly 700 from the TDA census, about 1,650 at the current granularity.
   - Assumptions printed with the output: closed population (fixed by the trait-hood filter and the cut-off), equal
     catchability (false: `honest` is caught by everything, so the estimates are low), independent occasions (false
     between LLM-based mechanisms, also low).  N̂ is a lower bound on what generators of these kinds can reach.
7. **Dashboard**: `tools/generator_dashboard.py` (not written yet) reads the registry, each run's `usage.json`, the
   review logs and the recovery reports and prints one Markdown table per generator: cost, candidates, M1 trait /
   tagged / reject, M3 kept and covered, repetition against decided terms, promoted (lags review) and the promote
   share, recall at the two levels and pair-recall, negatives hit rate, the region row, and the two stop-rule
   numbers: **kept per review-minute corrected by the last measured promote share**, the headline (§ 9, question 3),
   and novel per dollar, watched as a loose constraint.  Re-run after every M3 batch and every `apply`.

## 4. Expected yield and biases
Numbers, not candidates: a row per generator, a region-by-generator matrix, N̂ and coverage with intervals, one
accumulation curve per mechanism.  Expected pattern, now partly observed: the lexicon walks recover temperament and
style well and alignment poorly, repeat each other heavily (the 40% above, rising as batches are applied), and
approach a ceiling the TDA census has largely walked; IPIP and the base model sample behaviour rather than
vocabulary and overlap the lexicon less; the alignment sweep is novel against the corpus (87% kept) because the
corpus is thin there, which the capture-recapture must not mistake for an open population.  Recall is inflated by
common traits and the estimators inherit that; region stratification corrects it only partly.

## 5. Cost
Almost everything is a read of recorded data: $0.  The recovery harness is the paid part, about $5 per generator run
at two seeds (M3 against the reduced corpus plus the match calls), so under $40 for all current generators.
Estimators: seconds.  Roger: 15 minutes per dashboard refresh; the recovery readouts are the only new reading.

## 6. Testing
- Matcher sanity rides on M3's own tests; a paraphrase set (40 labels and glosses, 40 antonym glosses) through the
  harness's match step: concept recall over 90%, antonyms land in pair-recovery.  A miss is an M3 bug, not a
  finding.
- Contamination: recall with and without provenance exclusion; a large gap means a generator is re-deriving our
  sources.
- Estimator sanity: simulate N = 2,000 concepts with log-normal catchability and four correlated samplers; confirm
  bias directions and interval coverage; leave-one-mechanism-out instability flags failing independence.
- Spot check: Roger reads 20 random "recovered" and 20 "novel" verdicts.

## 7. Dependencies
Needs, all present: the registry and its blocks; M3's readings and cut-off rule; M1's verdicts and regions; the
review's applied blocks; `usage.json` per run; the recovery harness.  Provides: the independence classification,
recall and bias tables, repetition, N̂ and coverage per mechanism, the accumulation curves, and the stop rule.

## 8. Variants
- **Cheap**: no recovery runs; the dashboard, repetition and capture-recapture from recorded data only.  Loses
  recall, which is the only number here the generators cannot flatter.
- **Full**: bootstrap intervals over generators and regions; generator-side hiding for every seeded generator;
  Shapley attribution of novelty across mechanisms in place of the pairwise Chapman estimates.

## 9. Decisions (Roger, 2026-10-12, answering the plan's five open questions)
1. **Reference set: the checked-in corpus files only.**  "The seed queue is derived from several of our generators,
   so including it would be contamination."  The queue enters only M3's production search, which is dedup, not
   measurement; occasion 0 is the same reference.
2. **Regions: settled** — M1's, already computed.
3. **Stop rule: per review-minute**; novel-per-dollar "is also a constraint, but likely a loose one — as long as
   rough estimates continue to suggest it's not an issue, we're fine."
4. **A third occasion bought for Chao2: moot**; occasions are mechanisms, of which there are already four or five.
5. **Threshold: "we're using 3 in most areas, 4 in alignment-related.  So 3 is primary, report 4 as well"** —
   implemented as M3's cut-off rule for the headline, the strict column beside.

## Status (2026-10-12)
Built: the recovery harness (platform close-out), M1's regions, the review's applied blocks, the pre-handled
review graph that measures repetition.  Not built: the independence table, the dashboard, the estimators and the
accumulation curves, the paraphrase sanity set.  First use: once the batches submitted on 2026-10-11 (Allport-hi,
Roget, WordNet, IPIP, the base-model pilot, alignment variant B) have their M3 blocks — the dashboard and the
lexical accumulation curve from recorded data, then the harness on the TDA census and on IPIP as the two mechanisms
with the most kept terms.  **Greenlit for detailed planning (Roger, 2026-10-12).**  Next: a coding plan in the [format](./PLAN_FORMAT.md)
(Fable writes it), then a builder for the dashboard and the estimators.
