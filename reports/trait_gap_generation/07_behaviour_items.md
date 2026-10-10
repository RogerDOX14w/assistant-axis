# Plan 07: behaviour statements instead of words (IPIP item clustering)

## 1. Idea

Cluster ~3,300 public-domain self-report items ("Get chores done right away", "Abuse people's
confidences") by embedding, and have an LLM name each cluster as a disposition with a gloss and an
antonym. The items were written by psychometricians in 1990s Oregon to sample behaviour, not
vocabulary, so the clusters land wherever behaviour clusters, including dispositions with no single
English word ("does things at the last minute", "keeps others' secrets"). Nothing in the pipeline
sees our trait list until the coverage check.

## 2. Sources and tools

- **IPIP** (ipip.ori.org). Verified: home page states "The items and scales are in the public
  domain ... use them for any purpose without asking permission and without paying a fee".
  `AlphabeticalItemList.htm` lists the 3,320 items as plain text, each with an
  Eugene-Springfield survey code (e.g. `H1131`); `ItemAssignmentTable.htm` maps items to scales
  with key sign; `newIndexofScaleLabels.htm` lists ~274 construct labels over 463 scales, keyed to
  NEO, HEXACO, 16PF, CPI, JPI, MPQ, TCI, HPI, AB5C, VIA, CAT-PD and others. No CSV/Excel download
  is advertised; scrape the three HTML pages (`pandas.read_html` / BeautifulSoup, ~200 lines).
  Note the facet *names* of IPIP-NEO and HEXACO were already gap-scanned (TRAITS_TO_ADD.md ~l.1373,
  1503-1588); this plan works one level below the names, and across the 400+ non-NEO scales.
- **HEXACO-PI-R** (hexaco.org). Verified: free for non-profit academic research only; no
  commercial use, no redistribution, so items could be used locally but not committed. 100/200
  items, against 3,320.  **Not needed: the IPIP-HEXACO analogue is verified** (2026-10-10, at Roger's
  request).  `newIndexofScaleLabels.htm` keys 24 constructs to `HEX` (Sincerity, Fairness, Greed
  Avoidance, Modesty; Fearfulness, Anxiety, Dependence, Sentimentality; Social Boldness, Sociability,
  Liveliness, Expressiveness; Forgiveness, Gentleness, Flexibility, Patience; Organization, Diligence,
  Perfectionism, Prudence; Aesthetic Appreciation, Inquisitiveness, Creativity, Unconventionality),
  each linking to `newHEXACO_PI_key.htm`, which carries the item texts: 24 facets x 10 items = 240,
  more than the HEXACO-PI-R's own 100 or 200, and public domain under IPIP's blanket terms.  The
  source is Ashton, Lee & Goldberg (2007), "The IPIP-HEXACO scales: an alternative, public-domain
  measure of the personality constructs in the HEXACO model" (*Personality and Individual
  Differences* 42, 1515-1526) — written by HEXACO's own authors with IPIP's, so construct fidelity is
  as good as a public-domain analogue gets.  Two caveats: it keys to the 2004 HEXACO-PI, not the
  revised PI-R, so the PI-R's interstitial 25th facet (Altruism) has no IPIP scale (the corpus already
  has plain `altruistic`); and the page calls the set "preliminary".  Since these are IPIP items with
  IPIP scale assignments, the plan's existing scrape of the three HTML pages already picks them up
  with their `HEX` keys — no extra step, no licence question, nothing uncommittable.
- **Others considered**: SAPA/SPI 696 items (IPIP subset); MFQ-2 (36 items) and Schwartz PVQ-RR
  (57, permission required) are too small to matter; VIA and CAT-PD are already inside IPIP;
  openpsychometrics.org item texts have per-scale, unverified licences. IPIP alone for v1.
- **Tools** (local Mac): `sentence-transformers` (Apache-2, needs `uv add`; `transformers` 5.1
  and `torch` 2.10 present); `scikit-learn` 1.8 has `cluster.HDBSCAN` and `AgglomerativeClustering`;
  `umap-learn` present. OpenAI `text-embedding-3-large` as the second, independent embedder
  (~35k tokens, under $0.01). Claude Haiku 4.5 for naming, with `MultiModelUsage` logging.

## 3. Method

1. **Scrape and join.** `items.jsonl`: `{ipip_id, text, scales:[{inventory, construct, key:+/-}]}`.
   Items load on several scales; keep all. ~3,320 rows.
2. **Embed twice.** Local `bge-base-en-v1.5` or `gte-large` (instruction-tuned models handle the
   many negated items, "Don't like to draw attention to myself", better than MiniLM) and OpenAI
   `text-embedding-3-large`. Prefix "I " to each item so they read as first-person statements.
3. **Cluster.** Agglomerative, average linkage, cosine, distance threshold swept to give ~300-400
   clusters of 4-15 items; HDBSCAN on a 20-d UMAP as the cross-check. Keep clusters that both
   embedders reproduce (Jaccard > 0.5 against the best-matching cluster); route the rest to a
   "loose" pile for later. Items keyed `-` on a scale whose `+` items sit in the same cluster mark
   the cluster as bipolar: the key signs split it into two poles for free.
4. **Name.** One Haiku call per cluster (items only, construct names withheld: blind naming keeps
   the labels independent of the taxonomy vocabulary already scanned). Output JSON: `label`, `gloss`
   in the corpus "This means being X: ..." form, `antonym_label`, `antonym_gloss`, `is_trait`
   (disposition a speaking persona can enact, vs mood, symptom, ability, interest, life
   circumstance), `ambiguity_flag`, `single_word_exists`. A second call with the construct names
   as hints, kept as a separate column; disagreement between the blind and hinted label is itself a
   flag for review. ~700 calls.
5. **Coverage check.** Embed each cluster gloss and antonym gloss against the 387 trait
   `description`s plus the 972 seed-queue descriptions, both embedders. Both poles hit an existing
   pair -> covered; one pole hits, its partner does not -> pair-completion candidate; neither hits
   -> gap. Disagreements between embedders go to the shared novelty scorer (LLM adjudication on the
   top-5 nearest). Item IDs travel with every candidate as provenance.
6. **Emit** candidates in the registry format with `source: ipip_cluster_<n>`, the constituent
   items, IPIP construct hints and both labels.

## 4. Expected yield and biases

~350 clusters, ~250 passing `is_trait`, of which (judging by the facet scans) 60-70% are covered,
leaving roughly 60-100 candidates and 20-40 pair completions. Many will be multiword, which is
the point. Over-produces: clinical and symptom content (CAT-PD, ADHD, dissociation, cognitive
failures), interests and abilities, self-esteem and mood, and generally the register of an adult
Oregonian describing their life in the 1990s. Under-produces: AI/agent and alignment traits
(none in the pool), speech-style traits, moral stances toward third parties, anything defined by
context rather than by habit. Good complement to word-based generators, not a replacement.

## 5. Cost

API: embeddings under $0.10; naming ~700 Haiku calls at ~800 tokens, $1-2; adjudication of
disagreements ~$2. Total under $5. Local: minutes on the Mac. Roger's review: the ~100 candidates
at 20-30 s each, about an hour; the full 350-cluster table only if the filter looks wrong.

## 6. Testing

- **Clustering quality**: NMI/ARI of clusters against IPIP scale assignments, and majority-construct
  purity per cluster; the two embedders' mutual Jaccard. Expect purity ~0.7 on NEO-facet items.
- **Naming**: spot-check 30 clusters; for bipolar clusters, does the LLM antonym match the keyed
  negative pole (expect > 80%).
- **Recovery** (the brief's test): the generator never reads our list, so recovery is just the
  covered fraction on the traits with a known IPIP analogue (orderly, anxious, gregarious,
  forgiving, perfectionist, ...; list from TRAITS_TO_ADD.md). Target > 90% found within threshold;
  report recovery per trait domain to show where the pool is blind (alignment region ~0 expected).
- **Precision**: of 20 random "gap" outputs, how many does Roger accept as new traits.

## 7. Dependencies

Needs: the trait-hood filter (to second the `is_trait` field), the novelty scorer and threshold,
the candidate registry schema. Provides: candidates with item-level provenance; a reusable
`items.jsonl` with scale keys; cluster glosses with known constructs behind them, usable by other
workstreams as a behaviour-grounded gold set for testing their novelty scorers.

## 8. Variants

- **A (above)**: cluster items, name, check coverage. Independent of our list and of IPIP's names.
- **B, scale-first**: skip clustering; the 274 constructs / 463 scales are the candidates, their
  items the gloss material. ~300 calls, cheaper, but largely repeats the facet scans and misses
  sub-facet and cross-facet clusters.
- **C, residue-first**: assign every item to its nearest existing trait description; cluster only
  the low-similarity residue. Fewer clusters to review, but the residue is defined by our list, so
  it is a filter view on A, not an independent generator. Run A; use C as a second ordering.

## 9. Open questions for Roger

1. Are symptom-like dispositions (obsessive-compulsive, dissociative, ADHD-ish inattention)
   traits for this corpus, or to be filtered out with moods and abilities?

   **Roger:** Traits already include ADHD and OCD: symptoms are fair game.

2. Include HEXACO-PI-R items locally under the research-only licence (they cannot be committed),
   or stay IPIP-only? My recommendation: IPIP-only.

   **Answered 2026-10-10 (verification, not a judgement call): IPIP-only, at no cost.**  The
   IPIP-HEXACO scales give all 24 HEXACO-PI facets as 240 public-domain items, and the plan's own
   scrape already collects them (see § 2).  So the research-only licence, whether sending items to a
   commercial API counts as redistribution, and the uncommittable-input break in provenance are all
   moot.

3. Blind naming (independent, sometimes odd labels) or hinted naming (accurate, taxonomy-flavoured)
   as the primary label? Plan keeps both; one must be primary in the registry.

   **Roger:** Initially, generate both, and we can evaluate once we see what we're getting.

4. Cluster granularity: ~350 clusters (sub-facet, more review) or ~150 (facet-level, fewer gaps)?

   **Roger:** Try both, and we'll see which produces clusters about the same size as our "3-4" relationship
   level for covered judgements.
