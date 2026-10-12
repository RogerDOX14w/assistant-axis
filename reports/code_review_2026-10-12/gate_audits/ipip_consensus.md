# Gate audit 4: the IPIP consensus gate, the item pool, and the proposed size gate

Written 2026-10-12 by an Opus audit agent, read-only, under the protocol of [README.md](./README.md).  Roger's two
questions of the day are answered in § 7 (the "keep clusters of 3 or more items" gate) and § 8 (the evidence for
Jaccard 0.5, and whether it should depend on cluster size).  Every number below was recomputed for this audit; the
cluster verdicts are **my own reading** of the item texts (no reference labels exist for cluster coherence), with
two objective cross-checks (construct purity, § 5.3; the recorded Sonnet within-pole readings, § 5.4).

## Verdict in brief

- **The gate is mostly not doing what was intended, and it can be fixed.**  At g600 it holds 376 of 600
  clusters.  Of a random sample of 64 held clusters, **53 are coherent groups (83%, 95% CI 72–90%)** and 48 are
  trait groups (75%); of 44 kept ones, 1 is incoherent (2%, 0–12%).  It removes about 65 incoherent clusters at the
  price of about 311 coherent ones.
- **Its signal lives almost entirely in pairs.**  9 of the 11 incoherent held clusters have 2 items.  Among clusters of
  3+ items, held and kept are equally coherent (incoherent 2/41 = 5% held, 1/37 = 3% kept).  For pairs, "the other
  arm puts the two items in one cluster" separates good from bad (1/24 incoherent vs 13/30, p = 0.001); J ≥ 0.5 does
  so less well, because for a pair it also demands that the other arm's cluster have at most 4 items.
- **"Keep 3 or more" (Roger's question a) is better than the current gate but throws away the wrong pairs.**  It
  would hold all 172 pairs at g600, including the 50 that both arms reproduce (all 7 sampled were coherent), and it
  would keep about 4% incoherent clusters.  The better version: **keep every cluster of 3+, and keep a pair when the
  other arm co-clusters it** (rule R2: 486 kept at g600, about 5% incoherent, 114 pairs held).
- **0.5 has no recorded derivation, and the data show no reason to prefer it (question b).**  Chance agreement is
  about 0.001 at every size, so any 2-item overlap is far beyond chance.  The J distribution has no break at 0.5,
  and every threshold from 0.34 to 0.6 gives the same 2–3% incoherence among kept clusters while 78–86% of what it
  holds is coherent.  A size-aware threshold does not help, because among 3+ clusters J barely predicts coherence
  (AUC 0.55); cluster size predicts it better than J does (AUC 0.82 vs 0.69).
- **The loose share rising with coarser cuts (63% → 76% → 83%) is mostly the cut, not the size of the clusters.**
  Even the same OpenAI embedding at half its dimensions loses 14% → 24% → 43% of clusters at J ≥ 0.5.  Size mix
  explains 1–3 points of the rise.
- **Submitting both arms (question 6) is worse than R2.**  It gives 660 clusters at a floor of 3, about 13% of them
  incoherent; about 150 are near-duplicates of an OpenAI cluster, and Gemma's own small clusters are noisier
  (Gemma's held 3-item clusters: 4 of 7 incoherent).  It adds 67 items.
- **The item-pool restriction is fine.**  Of the 370 set-aside workbook rows (340 distinct texts), about 290 are
  Oregon interest and activity items.  45 are spelling variants of items that are in the pool.  About 3 are real
  personality statements (about 1%).

## Terms

- **Arms**: the two embedders.  The **OpenAI arm** (`text-embedding-3-large`) is primary: its clusters are the
  candidates.  The **Gemma arm** (`google/embeddinggemma-300m`) is the check.  Each arm is cut separately to the
  same number of clusters: **g600, g350, g150** (600, 350 and 150 clusters of two or more items; a lone item is a
  *singleton*, not a cluster).
- **J**: the Jaccard index |A∩B| / |A∪B|.  A **kept** cluster's one-to-one match in the other arm reaches J ≥ 0.5.
  The rest are **loose**: held on the "loose pile" and never named or submitted.  A **pair** is a 2-item cluster.
- **Co-clustered / core**: the largest number of a cluster's items that share one cluster of the other arm.  A pair
  is co-clustered when its core is 2.
- **Verdict codes** (my reading, judged against the intent, not the rule):
  - **T**: a coherent trait group, which a single label would fit.
  - **T~**: a trait group with strays (25–40% of the items off-theme, or two related traits joined).
  - **N**: coherent but not a trait (an interest, a skill, a physical attribute, an opinion, a symptom episode).
  - **I**: incoherent, usually glued by a shared word or phrase ("action", "Would never …", "Love …").
- **Coherent** = T, T~ or N; **trait group** = T or T~.
- M1, M3 and R1 are defined in [escalations.md](../escalations.md) § Terms.

## 1. The rule, from the code

- [cluster.py:44](../../../assistant_axis/gapgen/generators/ipip/cluster.py#L44) `MIN_JACCARD = 0.5`.
- [`consensus`, cluster.py:167–199](../../../assistant_axis/gapgen/generators/ipip/cluster.py#L167):
  - every (OpenAI cluster, Gemma cluster) pair sharing an item gets its J;
  - pairs are matched **one to one, greedily from the highest J** (ties by index);
  - an OpenAI cluster is kept when its matched J ≥ 0.5 (**line 195**, `jac >= min_jaccard`);
  - otherwise it is loose and carries its best J against any Gemma cluster (lines 183, 198).
- [`agglo_clusters`, cluster.py:128–153](../../../assistant_axis/gapgen/generators/ipip/cluster.py#L128) cuts each arm's
  average-linkage tree at the same target count.  So the two arms' cuts have different thresholds and different size
  profiles: at g600, the OpenAI arm has 181 singletons and Gemma has 335.
- [`build_cluster_table`, cluster.py:513, 534](../../../assistant_axis/gapgen/generators/ipip/cluster.py#L513) writes
  `consensus` and `jaccard_vs_gemma` on each row of [clusters_g600.jsonl](../../../data/candidates/ipip/clusters_g600.jsonl)
  (and [g350](../../../data/candidates/ipip/clusters_g350.jsonl), [g150](../../../data/candidates/ipip/clusters_g150.jsonl)).
  The Gemma arm's clusters are not stored.
- **What happens to a loose cluster**: it is held.
  - `select_clusters` names kept clusters only, unless ids are given
    ([ipip_generator.py:334–341](../../../data_analysis/gap_generation/ipip_generator.py#L334)).
  - `to_candidates` skips loose clusters ([submit.py:82](../../../assistant_axis/gapgen/generators/ipip/submit.py#L82)).
    Its `include_loose` parameter has no CLI flag.
  - A kept pole whose nearest pole is loose loses its granularity reading, which is review 5 D3
    ([escalations.md](../escalations.md#review-5-d3-questions-50-signal-1-rests-on-2-to-10-pairs)).
- **Three deviations from the plan's words:**
  1. The plan says "Jaccard **>** 0.5"; the code keeps **≥** 0.5.  At g600, 50 of the 224 kept clusters sit at
     exactly 0.5 (17 of 84 at g350, 6 of 26 at g150).  Under the plan's wording only 174 / 67 / 20 would be kept.
     Every exact-0.5 cluster I sampled was coherent (all 12 at g600, 17 across the three cuts), so the code's
     reading is the better one.
  2. The plan says "against the best-matching cluster"; the code matches one to one.  On this data that changes
     nothing: no loose OpenAI cluster at any granularity has a best J ≥ 0.5 that another cluster took.
  3. The plan asked for "~300–400 clusters of 4–15 items".  The cut also yields pairs and triples: 287 of 600 at g600.
     That is where the incoherent clusters are (§ 7).

## 2. The intent

[Plan 07 § 3](../../trait_gap_generation/07_behaviour_items.md) (lines 55–58): "Agglomerative, average linkage,
cosine, distance threshold swept to give ~300-400 clusters of 4-15 items; HDBSCAN on a 20-d UMAP as the
cross-check.  Keep clusters that both embedders reproduce (Jaccard > 0.5 against the best-matching cluster); route
the rest to a 'loose' pile for later."  [Coding plan 07](../../trait_gap_generation/coding_plan_07_behaviour_items.md)
carries it as `consensus(a, b, *, min_jaccard=0.5)` (line 89).  It leaves the pile's fate open at § 10 (d), "the
loose pile — hold (provisional) or submit" (line 225).

**No derivation of 0.5 is recorded** in either plan, in [QUESTIONS.md](../../trait_gap_generation/QUESTIONS.md), or
in the code.  The likely source, from my recollection and not checked here, is the cluster-stability convention of
Hennig (2007, R's `fpc::clusterboot`): a cluster whose Jaccard to its best match in a resample is ≤ 0.5 counts as
"dissolved", and stable clusters average ≥ 0.75 over many resamples.  That convention averages many perturbations of
**one** method.  Here 0.5 is applied to a **single** comparison with a **different** embedder cut to an equal
count, so even the convention does not carry over directly.

For the audit the intent is read as: hold a cluster when it is an artefact of one embedder rather than a real group
of items.  So a **false negative** is a loose cluster that is a coherent group.  A **false positive** is a kept
cluster that is incoherent.  Trait-hood is M1's job (QUESTIONS 48), so it is reported but not counted against the
gate.

## 3. The recorded discard, reproduced

Both arms' cuts were rebuilt from the platform's EmbeddingCache
([data/candidates/cache/embeddings/](../../../data/candidates/cache/embeddings/)):

- The vectors were looked up by text hash, with no embedder object, no API call and no model load.  A missing
  vector would have stopped the script, and none was missing.
- The text was `item_embed_text`, the cut was `agglo_clusters` and the gate was `consensus`, all from the module.
- The rebuilt OpenAI cuts, statuses and J values match the stored tables exactly at all three granularities.

| | g600 | g350 | g150 |
|---|---|---|---|
| OpenAI clusters (items in clusters; singletons) | 600 (3,139; 181) | 350 (3,271; 49) | 150 (3,314; 6) |
| Gemma clusters (items; singletons) | 600 (2,985; 335) | 350 (3,221; 99) | 150 (3,291; 29) |
| kept (items) | 224 (1,087) | 84 (596) | 26 (266) |
| **loose (items)** | **376 (2,052)** | **266 (2,675)** | **124 (3,048)** |
| loose share of clusters / of clustered items | 63% / 65% | 76% / 82% | 83% / 92% |
| bipolar clusters, kept | 40, 14 | 48, 7 | 43, 7 |
| median J of kept | 0.667 | 0.667 | 0.667 |

These agree with [cluster_summary.json](../../../data/candidates/ipip/cluster_summary.json) and the README's table.
At g600 the gate holds 62% of all 3,320 items.

## 4. The sample

**Seed 20261012** (`random.Random`).  The strata were drawn in this order, each with `rng.sample` over that
stratum's clusters in cut order:

| stratum | n |
|---|---|
| g600 loose | 64 |
| g600 kept | 44 |
| top-up, loose clusters of 10+ items (14 drawn, the first 10 not already sampled) | 10 |
| top-up, kept clusters of 10+ items (first 6 of 10 drawn) | 6 |
| g350 loose | 15 |
| g350 kept | 10 |
| g150 loose | 15 |
| g150 kept | 10 |
| Gemma arm g600 loose | 40 |
| Gemma arm g600 kept | 10 |

- That is 224 clusters, all read item by item (clusters over 30 items through their first 25–30 items).
- The two g600 strata are simple random samples and give the headline rates.  The top-ups serve only the size table.
- Gemma clusters are numbered as the module orders a cut (largest first, then by first item in code order).  The
  numbers come from the rebuilt cut and are not stored anywhere.
- The full tables, with the basis of each verdict and the top overlaps in the other arm, are in the Appendix.

| sample | n | T | T~ | N | I |
|---|---|---|---|---|---|
| g600 loose | 64 | 39 | 9 | 5 | 11 |
| g600 kept | 44 | 32 | 6 | 5 | 1 |
| g600 loose, 10+ items (top-up) | 10 | 5 | 5 | 0 | 0 |
| g600 kept, 10+ items (top-up) | 6 | 4 | 0 | 2 | 0 |
| g350 loose | 15 | 10 | 1 | 0 | 4 |
| g350 kept | 10 | 4 | 2 | 2 | 2 |
| g150 loose | 15 | 4 | 7 | 0 | 4 |
| g150 kept | 10 | 6 | 1 | 2 | 1 |
| Gemma g600 loose | 40 | 26 | 2 | 1 | 11 |
| Gemma g600 kept | 10 | 9 | 0 | 1 | 0 |

## 5. Rates

### 5.1 Headline, g600

| rate | sample | 95% CI | implied over the run |
|---|---|---|---|
| **false negative**: loose but coherent (T, T~, N) | 53/64 = **83%** | 72–90% | ≈ 311 of 376 held clusters |
| loose and a trait group (T, T~) | 48/64 = 75% | 63–84% | ≈ 282 |
| loose and clean (T or N only) | 44/64 = 69% | 57–79% | ≈ 259 |
| **false positive**: kept but incoherent | 1/44 = **2%** | 0–12% | ≈ 5 of 224 |
| kept and not clean (I or T~) | 7/44 = 16% | 8–29% | ≈ 36 |

- The gate does discriminate: 17% of loose clusters are incoherent against 2% of kept ones (Fisher p = 0.025).
  Without any gate, about 12% of the 600 would be incoherent (≈ 70).  So the gate removes ≈ 65 incoherent clusters
  and holds ≈ 311 coherent ones with them: **4.8 good clusters held per bad one removed**.
- Coarser cuts have smaller samples.  Pooled g350 and g150: incoherent 8/30 loose (27%, 14–44%) and 3/20 kept
  (15%, 5–36%).  All three kept incoherent clusters at g350/g150 have J ≥ 0.56: g350 #28 is glued by the word
  "problem", g350 #246 by "surprise" and g150 #99 by "Would never …".  In these cases both embedders share the same
  surface bias, so their agreement does not show that the group is real.

### 5.2 Where the signal is: pairs

| g600 stratum | incoherent | 95% CI |
|---|---|---|
| loose pairs | 9/23 = 39% | 22–59% |
| kept pairs | 0/7 | 0–35% |
| loose, 3+ items | 2/41 = 5% | 1–16% |
| kept, 3+ items | 1/37 = 3% | 0–14% |
| loose, 10+ items (headline and top-up) | 0/25 | 0–13% |

Among clusters of 3+ items the gate holds groups as good as the ones it keeps.  The two incoherent 3+ held clusters
are 4-item clusters: #255 is glued by "free time" and #274 by "habit".  Large held clusters show more strays (T~ in
9 of 25 held vs 2 of 10 kept), but none was incoherent.

### 5.3 Objective cross-check: construct purity

The cross-check uses the majority construct's share of a cluster's scored items, from the stored rows, for clusters
with 2+ scored items.  Within every size band at g600, kept clusters are purer than loose ones by 0.03–0.13:

| g600 size band | kept purity (n) | loose purity (n) |
|---|---|---|
| 2 | 0.69 (8) | 0.61 (23) |
| 3 | 0.69 (24) | 0.56 (22) |
| 4–5 | 0.66 (35) | 0.60 (55) |
| 6–9 | 0.62 (30) | 0.51 (50) |
| 10–15 | 0.46 (10) | 0.39 (34) |
| 16+ | 0.38 (8) | 0.35 (19) |

That is a real but modest signal, consistent with the reading.  Purity is not coherence: a cluster can mix "Anger"
from NEO with "Hostility" from another inventory and be perfectly coherent.  Purity is also distorted by the
double-spelled inventories of review 5 D1
([escalations.md](../escalations.md#review-5-d1-ipip-merge-keys-gap-fills-workbook-rows-the-key-pages-already-hold)).

What the gate costs in canonical constructs, at g600:

- Only **24% of the IPIP-NEO items** (97 of 400 facet and domain links) sit in kept clusters.
- **Seven of the 30 NEO facets have no item in any kept cluster**: Altruism, Anger, Anxiety, Assertiveness,
  Dutifulness, Emotionality and Imagination.  An eighth, Modesty, has none under its "Modesty/Humility" spelling
  (1 of 10 under "Humility/Modesty").
- Of the 415 scale labels with 8+ items, 41 have no kept item and 204 have under 25% of their items kept.

### 5.4 Second cross-check: the recorded Sonnet readings

The granularity run read 3 within-pole item pairs per kept cluster with M3's overlap call (0–4;
[g600 responses](../../../data/candidates/ipip/granularity/g600/responses.jsonl)).  Their mean, by my verdict on the
sampled kept clusters:

| | T | T~ | N | I |
|---|---|---|---|---|
| g600 | 1.90 (35) | 1.39 (6) | 1.90 (7) | 3.0 (1) |
| g350 / g150 | 1.75 / 1.78 | 1.5 / 1.33 | 2.0 / 1.33 | 0.67 / 0.0 |

The readings run the same way as the verdicts: strays lower the score and glue scores lowest at the coarse cuts.
The one g600 I, #392, is no exception.  Its two "grandiose" items scored 3, and both pairs with "better off without
me" were read as **opposite**, which the 0–4 mean leaves out, so the reader caught the glue too.  Three pairs per
cluster can still miss a stray.  Loose clusters were never read, so this cannot measure the gate itself.

## 6. Question 2: do the two arms carve the same region at different joints, or is one arm wrong?

Mostly the same region at different joints.  My classification of the 64 sampled loose clusters against their top
Gemma overlaps:

| how Gemma carves the loose OpenAI cluster | all 64 | the 53 coherent | the 11 incoherent |
|---|---|---|---|
| finer: cuts it into clean pieces (e.g. #24 pessimism → 6 + 5 + 5; #89 cynicism → 3 + 2 + 2; #599 credit use → its two poles) | 14 | 14 | 0 |
| coarser: folds it into a larger coherent group (e.g. #4 anger → Gemma's 42-item anger cluster; #229 altered states inside Gemma's 11-item dissociation cluster) | 12 | 11 | 1 |
| reshuffled: overlapping groups, both sensible | 26 | 19 | 7 |
| leaves the items single (a pair Gemma did not cluster) | 9 | 6 | 3 |
| Gemma wrong (scatters a coherent group into glue: #216 charisma, #514 "behind people's backs" filed under privacy) | 3 | 3 | 0 |

- In each of the 11 incoherent loose clusters, the fault is the OpenAI arm's: word glue such as "action", "soft",
  "explain" and "punished".  Gemma was right not to reproduce them, and that is what the gate catches.
- In 44 of the 53 coherent cases neither arm is wrong.  They simply cut a continuous region at different places.

Over the whole g600 loose pile, using the best-overlapping Gemma cluster (cA = shared / OpenAI size, cB = shared /
Gemma size):

| relation | clusters | items |
|---|---|---|
| no two items together in Gemma (almost all pairs and triples) | 161 (43%) | 384 |
| a majority (cA ≥ 0.5) together, boundaries differ | 101 (27%) | 652 |
| spread over several Gemma clusters | 44 (12%) | 452 |
| a Gemma cluster nested inside it (cB ≥ 0.8; Gemma finer) | 41 (11%) | 446 |
| nested inside a larger Gemma cluster (cA ≥ 0.8; Gemma coarser) | 29 (8%) | 118 |

Two design choices of the gate make "reproduce" stricter than the concept needs:

- **Equal counts.**  Gemma's distances are compressed: it is cut at threshold 0.29 against OpenAI's 0.54, and it has
  almost twice the singletons.  "600 clusters" is not the same granularity in the two arms.  Cutting Gemma at 360,
  450, 540, 600 or 690 clusters gives 135, 180, 206, 224 or 239 kept OpenAI clusters at g600.  At g350 the
  corresponding run is 56 → 112 and at g150 17 → 37.  So the count chosen for the second arm is itself a free
  parameter, which moves the kept count by up to 40% either way.
- **Jaccard penalises nesting.**  A 2-item cluster that lies wholly inside a 5-item Gemma cluster reaches only
  J = 0.4.

The **26 loose bipolar clusters** at g600 are a size effect, not Gemma splitting them by key sign:

- Bipolar clusters average 10.3 items against 4.9 for unipolar ones.
- Their kept share is 35% against 38% for unipolar clusters.
- Only 3 of the 26 have both poles reproduced at J ≥ 0.5 separately.

## 7. Question (a): "keep clusters of 3 or more items"

**Coherence by size, both arms, g600** (all samples, top-ups included; T / T~ / N / I):

| size | OpenAI loose | OpenAI kept | Gemma loose | Gemma kept |
|---|---|---|---|---|
| 2 | 10 / 0 / 4 / **9** (39% I) | 4 / 0 / 3 / 0 | 13 / 0 / 1 / **5** (26% I) | 5 / 0 / 0 / 0 |
| 3 | 7 / 2 / 1 / 0 | 5 / 1 / 0 / 1 | 3 / 0 / 0 / **4** (57% I) | 0 / 0 / 1 / 0 |
| 4–5 | 4 / 3 / 0 / 2 | 11 / 0 / 1 / 0 | 3 / 1 / 0 / 0 | 3 / 0 / 0 / 0 |
| 6–9 | 7 / 0 / 0 / 0 | 10 / 3 / 1 / 0 | 3 / 1 / 0 / 1 | — |
| 10–15 | 8 / 5 / 0 / 0 | 2 / 1 / 2 / 0 | 1 / 0 / 0 / 0 | 1 / 0 / 0 / 0 |
| 16+ | 8 / 4 / 0 / 0 | 4 / 1 / 0 / 0 | 3 / 0 / 0 / 1 | — |

Incoherence sits in the smallest clusters: OpenAI's held pairs, and Gemma's pairs and triples.  From 4 items up
almost everything is coherent in both arms, held or kept.

**The proposed rule (R1, keep 3+, no consensus):**

| | g600 | g350 | g150 |
|---|---|---|---|
| kept by R1 (clustered items) | 428 (2,795) | 292 (3,155) | 137 (3,288) |

At g600 it holds all 172 pairs, 344 items (population-weighted estimates from the two headline samples):

- About **69% of what it holds is coherent (≈ 118 pairs)** and 46% are trait groups (≈ 79).  The held pairs include
  the **50 that both arms reproduce**, the cleanest stratum there is: 7 of 7 sampled were coherent.
- About **4%** of what it keeps is incoherent (≈ 17), against 2% for the current gate and 12% with no gate.

So R1 is a large improvement in false negatives at a small cost in false positives.  It discards the wrong pairs,
though.

**The pair evidence.**  Pooling both arms' sampled pairs:

| pair | incoherent | 95% CI |
|---|---|---|
| the other arm co-clusters it (any cluster size) | 1/24 = 4% | 1–20% |
| the other arm does not | 13/30 = 43% | 27–61% |

Fisher p = 0.001.  The current gate asks for more than co-clustering: the pair's partner must have ≤ 4 items.  That
extra condition adds little.  The co-clustered pairs whose partner has more than 4 items were coherent in 10 of 11
(OpenAI #449, #514 and eight Gemma pairs).  The exception is #476, glued by "avoid … people".

**Recommended variant (R2): keep every cluster of 3+ items, and keep a pair when the other arm co-clusters it.**

| | g600 | g350 | g150 |
|---|---|---|---|
| kept by R2 (clustered items) | **486 (2,911)** | 313 (3,197) | 143 (3,300) |

At g600:

- **About 5% of what R2 keeps is incoherent (≈ 24).**
- It holds 114 pairs, of which about 60% are coherent (≈ 68) and about 45 are trait groups.  They are narrow
  single-behaviour pairs ("Make lists / Do not make lists", "Cheer loudly at sporting events / Enjoy being part of a
  loud crowd").  They stay on the loose pile, as all held clusters do now, so nothing is lost for good.

At g350 and g150, R1 and R2 also keep domain-level blobs of 50–240 items, such as g150 #3, 174 items of negative
emotion, and g350 #1, a 79-item antagonism cluster.  These are incoherent as trait groups, and the current gate holds
them only by accident (§ 9).  Either rule needs a ceiling at the coarse cuts (proposal P2).

## 8. Question (b): what evidence is there that 0.5 is the right level, and should it depend on size?

**Chance is not the issue at any size.**

- Two random clusters of sizes a and b among 3,320 items have E[J] ≈ (ab/N)/(a+b−ab/N):

  | a \ b | 2 | 3 | 5 | 10 | 20 | 40 |
  |---|---|---|---|---|---|---|
  | 2 | 0.0003 | 0.0004 | 0.0004 | 0.0005 | 0.0005 | 0.0006 |
  | 5 | 0.0004 | 0.0006 | 0.0008 | 0.0010 | 0.0012 | 0.0013 |
  | 10 | 0.0005 | 0.0007 | 0.0010 | 0.0015 | 0.0020 | 0.0024 |
  | 40 | 0.0006 | 0.0008 | 0.0013 | 0.0024 | 0.0040 | 0.0061 |

- I shuffled the items within Gemma's actual partition 20 times, keeping its cluster sizes.  **No** OpenAI cluster of
  any size reaches J ≥ 0.5.  The median best J falls from 0.17 for pairs to 0.05 for 16+ clusters at g600.
- So a 2-item overlap is already many standard deviations beyond chance.  Used as a significance test, the
  hypergeometric tail with a Bonferroni correction over the 360,000 cluster pairs keeps 249 clusters (rule R5).  It
  can never keep a pair, whose best p is 1.8e-7 against a threshold of 1.4e-7.  J ≥ 0.5 is therefore an
  **effect-size** bar, how much of the cluster is reproduced, not a test against chance.

**Kept share by size against Gemma, against near-identical embedders, and against chance** (share reaching J ≥ 0.5,
median best J in brackets).  The references are the same OpenAI embedding truncated to 1536 or 1024 dimensions and
renormalised, which is the documented way to shorten `text-embedding-3` vectors, and Gemma's items shuffled.

| g600 size | n | vs Gemma | vs OpenAI-1536 | vs OpenAI-1024 | vs shuffled |
|---|---|---|---|---|---|
| 2 | 172 | 29% (0.33) | 83% (1.00) | 80% (1.00) | 0% (0.17) |
| 3 | 115 | 47% (0.40) | 85% (1.00) | 79% (1.00) | 0% (0.20) |
| 4–5 | 134 | 45% (0.40) | 86% (1.00) | 82% (0.80) | 0% (0.17) |
| 6–9 | 104 | 38% (0.42) | 90% (0.89) | 89% (0.88) | 0% (0.12) |
| 10–15 | 48 | 25% (0.36) | 90% (0.92) | 81% (0.85) | 0% (0.08) |
| 16+ | 27 | 30% (0.39) | 93% (0.87) | 96% (0.71) | 0% (0.05) |
| all | 600 | **37%** | **86%** | | 0% |

(g350: 24% vs 76%; g150: 17% vs 57%.  At g350 the Gemma share falls to 11% for 16+.)

Against Gemma, the fixed 0.5 does fail large clusters more often: 45–47% kept at 3–5 items against 25–30% at 10+,
and 11% at 16+ at g350.  It also fails pairs, where J is discrete (0, 1/3, 1/2, 2/3, 1).  The near-identical
reference shows no such gradient, so the gradient is not Jaccard arithmetic.  It is the two embedders drawing the
boundaries of large regions differently.  And the large clusters it fails are coherent: 0 of 25 sampled loose 10+
clusters were incoherent.

**No threshold, fixed or by size, makes J a good coherence signal for 3+ clusters.**

- On the g600 samples, J's AUC for telling coherent from incoherent is:

  | clusters | AUC of J |
  |---|---|
  | all | 0.69 |
  | pairs | 0.56 |
  | 3+ items | 0.55 |

  Cluster size alone reaches 0.82.  A clean T against the rest gets 0.57.
- The J distribution at g600 has no break at 0.5.  Per 0.1 band from 0.0: 44, 57, 125, 103, 47, 79, 50, 24, 12 and
  59, with 50 clusters exactly at 0.5.
- Moving the threshold changes little:

  | best J ≥ | 0.20 | 0.30 | 0.34 | 0.40 | 0.50 | 0.60 | 0.70 |
  |---|---|---|---|---|---|---|---|
  | clusters kept | 499 | 376 | 301 | 271 | 224 | 159 | 95 |
  | est. incoherent among kept | 10% | 9% | 2% | 2% | 2% | 3% | 5% |
  | est. coherent among held | 82% | 85% | 78% | 81% | 83% | 86% | 87% |

  The step between 0.30 and 0.34 is the pairs that share one item with a Gemma pair (J = 1/3), which are the glue
  pairs.  That is the pair effect of § 7 again.

**Size-aware criteria, tried** (g600 kept clusters with clustered items; the estimates are population-weighted from
the samples):

| rule | g600 kept (items) | g350 | g150 | est. incoherent among kept | est. coherent among held |
|---|---|---|---|---|---|
| R0 current, J ≥ 0.5 | 224 (1,087) | 84 | 26 | 2% | 83% |
| R0′ plan wording, J > 0.5 | 174 (844) | 67 | 20 | 3% | 85% |
| R1 3+ items | 428 (2,795) | 292 | 137 | 4% | 69% |
| **R2 3+, or a pair co-clustered by the other arm** | **486 (2,911)** | **313** | **143** | **5%** | **60%** |
| R3 core ≥ 2 (any size) | 439 (2,755) | 294 | 139 | 5% | 68% |
| R4 core ≥ max(2, half the cluster) | 358 (1,897) | 206 | 97 | 6% | 80% |
| R5 hypergeometric, Bonferroni | 249 (2,065) | 198 | 107 | 2% | 80% |
| R6 no gate | 600 (3,139) | 350 | 150 | 12% | — |

A per-size null (R5) or a z-score keeps nearly every overlap of 3+ shared items and no pair at all, so it sorts by
size rather than by quality.  The criterion the data support is R2.  It is size-aware where size matters (a pair
must be co-clustered) and makes no demand on clusters of 3+, where agreement says nothing about coherence.

## 9. Question 5: why the loose share rises with coarser cuts

| | g600 | g350 | g150 |
|---|---|---|---|
| loose vs Gemma | 63% | 76% | 83% |
| loose vs OpenAI-1536 (near-identical) | 14% | 24% | 43% |
| loose vs Gemma-512 (Gemma against its own truncation) | 17% | 29% | 46% |
| OpenAI weighted / complete linkage on the same vectors | 22% / 42% | 43% / 65% | 57% / 81% |
| loose expected from the size mix alone (g600's per-size kept rates applied to this cut's sizes) | 63% | 64% | 66% |

- **Size mix explains 1–3 points** of the rise.
- **Most of the rise is the cut itself.**  Coarse clusters form near the top of the average-linkage tree, where merge
  heights are close together.  A small change in the vectors reorders which subtrees join, so even near-identical
  embedders disagree there.
- **The Gemma-specific loss is roughly flat** once the reference is divided out: 1 − kept(Gemma)/kept(OpenAI-1536) =
  57%, 68% and 70%.

A fixed J bar therefore penalises coarse granularities by construction.  It also feeds into the open granularity
decision, through the shrinking number of kept poles and review 5 D3's 2–10 readings at g350/g150.

At the coarse cuts the gate does do one useful thing, by accident.  The loose pile there holds the domain-level blobs
(g150 #3, 174 items; g350 #1, 79 items), which no label could fit.  Coherence of loose clusters falls to 73% at
g350/g150 pooled, against 83% at g600.

## 10. Question 6: submit both arms instead?

The coordinator's alternative: submit the matched pairs once, then every remaining cluster of either arm, with its
arm and J recorded, above a size floor.

| g600 | floor 2 | floor 3 | floor 4 |
|---|---|---|---|
| matched once + OpenAI loose + Gemma loose | 224 + 376 + 376 = 976 | 174 + 254 + 232 = **660** | 120 + 193 + 176 = 489 |
| g350 | 616 | 497 | 409 |
| g150 | 274 | 244 | 220 |

At g600:

- **Duplicates.**  234 of Gemma's 376 loose clusters overlap an OpenAI cluster with an overlap coefficient ≥ 0.5 and
  2+ shared items.  At floor 3 that is roughly 145 candidates repeating a concept the OpenAI side already submits.
- **What Gemma adds.**  Only 22 Gemma loose clusters are made mostly of OpenAI singletons.  Gemma clusters 67 of the
  181 items OpenAI leaves alone.
- **Quality.**  Gemma's loose clusters are noisier: 11/40 incoherent (28%), 6/21 at 3+ (29%, 14–50%), and its
  triples 4 of 7.
- **Estimate at floor 3.**  About 5 (matched) + 12 (OpenAI loose 3+) + 67 (Gemma loose 3+) ≈ **84 incoherent of 660
  (13%)**, plus about 145 near-duplicates.

| option, g600 | clusters submitted | est. incoherent | near-duplicates | coherent clusters held |
|---|---|---|---|---|
| current gate | 224 | ≈ 5 (2%) | 0 | ≈ 311 |
| both arms, floor 3 | 660 | ≈ 84 (13%) | ≈ 145 | ≈ 118 OpenAI pairs (the floor also drops the 50 matched pairs) + Gemma's pairs |
| **R2, OpenAI arm only** | **486** | **≈ 24 (5%)** | **0** | **≈ 68 pairs (held, not lost)** |

R2 dominates the both-arms option: it has fewer junk clusters and no duplicates.  The only loss is the 67 items that
OpenAI leaves single and Gemma clusters (P4).

## 11. The item pool restriction ([ingest.py](../../../assistant_axis/gapgen/generators/ipip/ingest.py), `AlphabeticalItemList`)

- **The rule.**  Both key sources are restricted to the items of
  [AlphabeticalItemList.htm](../../../data/external/ipip/AlphabeticalItemList.htm) (gitignored download).  A workbook
  row whose text is not in that list is set aside and counted (`set_aside_a`,
  [ingest.py:901–904](../../../assistant_axis/gapgen/generators/ipip/ingest.py#L901),
  [1002](../../../assistant_axis/gapgen/generators/ipip/ingest.py#L1002)).  The key pages read outside the pool, the
  Oregon avocational and vocational interest inventories (203 and 95 items), are reported as `outside_pool`
  ([ingest.py:562–567](../../../assistant_axis/gapgen/generators/ipip/ingest.py#L562)).
- **Reproduced.**  [ingest_counts.json](../../../data/candidates/ipip/ingest_counts.json) has `set_aside_a` 370 and
  `unmatched_list` 340 distinct texts.  I classified all 340, with an exact and fuzzy match against the 3,320 pool
  texts:
  - **About 290 interest and activity items.**  196 are past-tense activities, as in "Ate dinner alone." and
    "Attended a ballet performance.".  About 95 are vocational or other activity items, as in "Be a chemist",
    "Repair cars or trucks" and "Keep a diary or journal".  This matches the workbook's ORAIS 200 and ORVIS 92 rows.  Plan 07 § 4 lists interests as over-production, not
    traits.
  - **45 spelling variants of items that are in the pool** (string ratio ≥ 0.9), as in "Believe appearances are
    important." against "Believe that appearances are important.".  The item is clustered.  Only that workbook
    row's key is unjoined.
  - **About 3 genuine personality statements** absent from the pool: "Do not have an assertive personality.", "I am
    known for saying offensive things." and "Rarely put people under pressure." (the reverse of a pool item).
- **False-negative rate ≈ 3/340 ≈ 1%.**  This part of the gate does what was intended, about as well as possible.
  The 45 variants could be joined by a normalised text match if their keys matter (ingest's business, not this
  gate's).

## 12. Verdict

**The consensus gate is mostly not doing what was intended, and it can be fixed.**

- It works as written: it keeps what both embedders cut the same way.  But at equal cluster counts, "cut the same
  way" mostly measures where two embedders put the joints of a continuous item space, not whether a group is real.
- It holds 83% (72–90%) coherent clusters, and whole NEO facets with them.  The signal it does carry, OpenAI's glue
  pairs, is better captured by a size-aware rule.
- **The threshold**: the data neither support 0.5 nor favour any other value (0.34–0.6 behave alike).  It should not
  be scaled with size either.  The size dependence belongs in the *criterion*: a pair needs the other arm's
  co-clustering, and a cluster of 3+ needs no consensus.
- **The item pool restriction** is doing what was intended, about as well as possible.

Expected change from R2 at g600: false negatives (coherent clusters held) fall from ≈ 311 to ≈ 68 (pairs, still held,
not lost).  The incoherent share among submitted clusters rises from ≈ 2% to ≈ 5%, that is from ≈ 5 to ≈ 24
clusters, each costing ≈ $0.017 at M1 + M3 before M1 sees it.

## 13. Proposals

| # | proposal | cost | evidence that would settle it |
|---|---|---|---|
| P1 | **Replace `consensus`'s keep rule with R2**: keep every OpenAI cluster of 3+ items; keep a pair when both items share one Gemma cluster (any size).  Keep writing `jaccard_vs_gemma`, and add the partner's id and the core, as review columns.  Pairs that fail stay on the loose pile. | Code $0.  Run at g600: 525 poles, 290 not yet named (naming ≈ $0.11 at the measured $0.000195 per call, [naming_usage.json](../../../data/candidates/ipip/naming_usage.json)); M1 + M3 ≈ $8.9 in all against ≈ $4.0 for today's 238 poles.  g350 ≈ $6.2; g150 ≈ $3.2.  All live (under $20). | Roger reads 20 clusters R2 adds (seeded) and 20 pairs it holds; or P5. |
| P2 | At g350/g150 (if chosen), a **size ceiling**: a cluster above about 30 items is replaced by its sub-clusters at the next finer cut (the g600 clusters inside it), not named as one. | $0 | The blobs in S5 and S7 (g350 #1, g150 #3, #15) read as several traits each.  Count how many sub-clusters each yields. |
| P3 | Record the threshold's provenance, or drop it.  If any J bar stays, make the plan's "> 0.5" and the code's "≥ 0.5" agree; the 50 exact-0.5 clusters at g600 are coherent (12 of 12 sampled). | $0 | — |
| P4 | Do not submit the Gemma arm's loose clusters.  Optionally add the ≈ 22 Gemma clusters made mostly of OpenAI singletons (67 items), with the arm recorded. | $0; ≈ 22 poles ≈ $0.4 | Read those 22 before adding them. |
| P5 | An independent coherence reading to replace this single reader: one Sonnet call per cluster ("one trait, two related, or unrelated; which items stray"), over all 1,100 OpenAI clusters at the three cuts, plus 50 of mine as a calibration overlap. | ≈ $3–5, live; usage record per the hard rule | The R0/R2 rates of § 8 recomputed on the full population instead of 108 sampled clusters. |
| P6 | After P1, rerun QUESTIONS 50 signal 1: R2's kept set names most of the nearest poles that review 5 D3 found missing. | Naming is included in P1.  The re-read is one Sonnet overlap call per pole, ≈ 1,070 × $0.0012 ≈ $1.3 over the three cuts. | The signal-1 n (67, 10 and 2 today) rises towards R2's 525, 361 and 186 poles. |

## How to reproduce

All the analysis code was scratch, under `/tmp/claude-501/`.  Nothing was written to the repository except this
report.  The recipe:

1. Load [items.jsonl](../../../data/candidates/ipip/items.jsonl) and map each item through `item_embed_text`.
2. Look up `openai_text-embedding-3-large` and `local_google_embeddinggemma-300m_p793518b0` in `EmbeddingCache()`
   (no misses).
3. Run `agglo_clusters(V, target_n=g)` per arm, then `consensus(openai_cut, gemma_cut)`.
4. Draw the samples with `random.Random(20261012)` in the order of § 4.
5. For the references: truncate the OpenAI vectors to their first 1536 or 1024 dimensions (Gemma's to its first 512)
   and renormalise; for the null, shuffle item labels within Gemma's partition (seed 7, 20 times).

## Appendix: the sample tables (my reading)

"J" is the stored `jaccard_vs_gemma`: the matched J for a kept cluster and the best J for a loose one.  The overlap
column gives the other arm's top two clusters as # (size; shared items; J), and "single" counts items the other arm
leaves alone.  "How the arms carve it" uses the categories of § 6.

**S1. g600, loose, simple random sample** (64 clusters)

| # | size | J | top Gemma overlaps: # (size; shared; J) | how the arms carve it | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|---|---|
| 2 | 32 | 0.45 | #7 (23; 17; 0.45), #5 (28; 4; 0.07) | Gemma finer | T~ | other-orientation: altruistic helping + people-pleasing/conformity, ~4 strays (M48, V141, T1406); Gemma #7 is the cleaner helping core | Am willing to make personal sacrifices in order to hel…; Try to fit in with others.; … (+30) |
| 4 | 25 | 0.26 | #1 (42; 14; 0.26), #29 (14; 7; 0.22); 1 single | Gemma coarser | T | anger outbursts / hot temper; Gemma #1 (42) is all anger incl. the low-anger pole | Shout or scream when I'm angry.; Get in shouting matches with other people.; … (+23) |
| 6 | 23 | 0.31 | #12 (19; 10; 0.31), #150 (6; 5; 0.21); 1 single | Gemma coarser | T | idea generation, ingenuity; Gemma #12 joins it with openness to novelty | Get excited by new ideas.; Am full of ideas.; … (+21) |
| 24 | 17 | 0.35 | #158 (6; 6; 0.35), #206 (5; 5; 0.29) | Gemma finer | T | pessimism; Gemma cuts it into three clean pieces (6, 5, 5) | Have a dark outlook on the future.; Expect things to fail.; … (+15) |
| 29 | 15 | 0.41 | #21 (16; 9; 0.41), #43 (11; 2; 0.08) | reshuffled | T | emotional detachment / low emotional awareness; Gemma #21 = emotional reserve | Rarely get caught up in the excitement.; Rarely think about how I feel.; … (+13) |
| 31 | 15 | 0.27 | #15 (18; 7; 0.27), #311 (3; 3; 0.20) | Gemma coarser | T | social ease, getting along; Gemma #15 joins it with enjoying company | Feel at ease with people.; Make friends easily.; … (+13) |
| 34 | 14 | 0.31 | #110 (7; 5; 0.31), #22 (16; 3; 0.11) | reshuffled | T~ | imperturbable ('Am not easily ...'), strays: not bothered by mess, not easily amused | Am rarely scared by loud noises.; Am not bothered by disorder.; … (+12) |
| 42 | 13 | 0.36 | #141 (6; 5; 0.36), #188 (5; 3; 0.20); 1 single | Gemma finer | T | demanding high standards of self and others; Gemma splits demands / discipline / perfectionism | Set high standards for myself and others.; Place demands on myself.; … (+11) |
| 47 | 12 | 0.38 | #140 (6; 5; 0.38), #196 (5; 3; 0.21) | Gemma finer | T | need for order, tidiness | Like to tidy up.; Love order and regularity.; … (+10) |
| 48 | 12 | 0.25 | #101 (8; 3; 0.18), #374 (3; 3; 0.25) | Gemma finer | T | workaholism, hard work | Put work above pleasure.; Work hard.; … (+10) |
| 51 | 11 | 0.37 | #27 (15; 7; 0.37), #375 (3; 2; 0.17); 1 single | reshuffled | T | self-harm (self-destructive); Gemma #27 adds the urges | Have intentionally done myself physical harm.; Have done many terrible things.; … (+9) |
| 56 | 11 | 0.21 | #4 (35; 8; 0.21), #24 (16; 2; 0.08) | Gemma coarser | T | social withdrawal, keeping distance; Gemma #4 (35) = aloof/private | Retreat from others.; Keep others at a distance.; … (+9) |
| 61 | 10 | 0.36 | #168 (5; 4; 0.36), #316 (3; 3; 0.30) | Gemma finer | T~ | passive, lets things happen; strays 'let bygones be bygones', 'let myself go' (word 'let') | Prefer to just let things happen.; Let things proceed at their own pace .; … (+8) |
| 64 | 10 | 0.38 | #97 (8; 5; 0.38), #130 (6; 4; 0.33) | Gemma finer | T | leadership, taking charge | Automatically take charge.; Take the initiative.; … (+8) |
| 67 | 10 | 0.27 | #78 (9; 4; 0.27), #301 (3; 2; 0.18) | reshuffled | T~ | gullible / easily influenced; 4 of 10 'Am easily ...' strays (excited, hard/easy to satisfy, impressed) | Am easily talked into doing silly things.; Am easily excited.; … (+8) |
| 80 | 9 | 0.42 | #92 (8; 5; 0.42), #51 (10; 3; 0.19) | Gemma finer | T | honesty, conscience, integrity | Tell the truth.; Listen to my conscience.; … (+7) |
| 89 | 9 | 0.33 | #357 (3; 3; 0.33), #562 (2; 2; 0.22); 1 single | Gemma finer | T | cynicism about people's motives; Gemma 3+2+2 | Believe that most people would lie to get ahead.; Believe that most people dislike helping other people.; … (+7) |
| 91 | 8 | 0.26 | #21 (16; 5; 0.26), #4 (35; 2; 0.05) | Gemma coarser | T | emotional suppression, keeping feelings in | Keep my feelings to myself, regardless of how unhappy …; Keep my happy feelings to myself.; … (+6) |
| 107 | 7 | 0.38 | #225 (4; 3; 0.38), #2 (39; 1; 0.02); 1 single | reshuffled | T | ideas of reference / thought broadcasting (schizotypal) | Often have the feeling that others laugh or talk about…; Have had the feeling that my thoughts were audible.; … (+5) |
| 120 | 7 | 0.43 | #329 (3; 3; 0.43), #408 (2; 1; 0.12) | Gemma finer | T | contempt, treating others as inferiors | Sometimes lack remorse for treating people badly.; Walk over others.; … (+5) |
| 167 | 6 | 0.27 | #94 (8; 3; 0.27), #454 (2; 1; 0.14); 1 single | reshuffled | T | opinionated, fixed opinions (one opposite-pole item) | Stick to my point of view.; Have a point of view all my own.; … (+4) |
| 175 | 6 | 0.29 | #256 (4; 2; 0.25), #380 (3; 2; 0.29) | Gemma finer | T | bravery | Fear nothing.; Face danger confidently.; … (+4) |
| 183 | 5 | 0.21 | #14 (18; 4; 0.21); 1 single | Gemma coarser | T | self-improvement, personal growth; Gemma #14 = self-reflection (looser) | Usually work on improving things, instead of getting f…; Know that I can improve myself.; … (+3) |
| 201 | 5 | 0.17 | #65 (10; 2; 0.15), #318 (3; 1; 0.14) | reshuffled | T~ | competitiveness + envy of others' success | Acknowledge others' accomplishments.; Try to outdo others.; … (+3) |
| 216 | 5 | 0.09 | #5 (28; 2; 0.06), #18 (17; 1; 0.05); 1 single | Gemma wrong | T | charisma, ability to influence; Gemma scatters it into people-pleasing and dominance clusters | Know how to captivate people.; Have a natural talent for influencing people.; … (+3) |
| 228 | 5 | 0.27 | #84 (9; 3; 0.27), #587 (2; 1; 0.17) | reshuffled | T | modesty about achievements | Am humble about the good things that have happened to …; Don't brag about my accomplishments.; … (+3) |
| 229 | 4 | 0.36 | #44 (11; 4; 0.36) | Gemma coarser | T | altered states; Gemma #44 (11) = the whole dissociation/absorption group, contains all 4 | Have out-of-body experiences.; Experience altered states of consciousness.; … (+2) |
| 249 | 4 | 0.40 | #336 (3; 2; 0.40), #283 (3; 1; 0.17); 1 single | reshuffled | T~ | dislikes learning (+ new foods) | Dislike new foods.; Dislike learning.; … (+2) |
| 255 | 4 | 0.22 | #112 (7; 2; 0.22), #134 (6; 1; 0.11) | reshuffled | I | topic 'free time': busy, idle, relaxed, helping | Do a lot in my spare time.; Have extra time on my hands.; … (+2) |
| 274 | 4 | 0.29 | #194 (5; 2; 0.29), #153 (6; 2; 0.25) | reshuffled | I | word 'habit': routine-bound vs bad habits | Do things out of habit.; Am a creature of habit.; … (+2) |
| 277 | 4 | 0.29 | #202 (5; 2; 0.29), #522 (2; 1; 0.20) | reshuffled | T~ | broad interests (+ 'interested in science') | Am interested in many things.; Am interested in science.; … (+2) |
| 330 | 3 | 0.20 | #286 (3; 1; 0.20), #125 (6; 1; 0.12); 1 single | Gemma finer | T | callous to suffering; Gemma: callousness #125 vs the opposite pole #286 | Would not be very distressed by seeing an animal in pa…; Would not feel very distressed and concerned if a frie…; Am seldom bothered by the apparent suffering of strang… |
| 331 | 3 | 0.25 | #404 (2; 1; 0.25), #423 (2; 1; 0.25) | Gemma finer | T | passionate, absorbed | Am totally consumed by one or more interests or hobbie…; Am passionate about anything I'm involved in.; Am passionate about causes. |
| 336 | 3 | 0.11 | #15 (18; 2; 0.11); 1 single | Gemma coarser | T~ | prefers company in free time (+ jealous of friends' friends) | Usually like to spend my free time with people.; Dislike when my friends spend too much time with other…; Prefer to spend my free time with family or friends ra… |
| 339 | 3 | 0.08 | #2 (39; 3; 0.08) | Gemma coarser | T | enjoys edgy humor; Gemma #2 (39) = all laughter/humor | Enjoy crude jokes.; Can take a joke.; Enjoy a good ethnic joke among friends. |
| 342 | 3 | 0.09 | #4 (35; 3; 0.09) | Gemma coarser | T | private person; Gemma #4 (35) | Believe that privacy is very important.; Enjoy my privacy.; Am a very private person. |
| 349 | 3 | 0.40 | #265 (4; 2; 0.40); 1 single | reshuffled | T | idle, does nothing | Like to putter around the house.; Can spend hours doing nothing.; Hang around doing nothing. |
| 366 | 3 | 0.10 | #56 (10; 1; 0.08), #97 (8; 1; 0.10); 1 single | reshuffled | T | dominant in conversation, wants control | Want to have the last word.; Want to control the conversation.; Want to be in charge. |
| 377 | 3 | 0.25 | #494 (2; 1; 0.25), #212 (5; 1; 0.14) | reshuffled | N | self-assessed knowledge (ability), one item reversed | Know the answers to many questions.; Believe that I know more than most supposed "experts."; Feel that there are many things that I do not know muc… |
| 383 | 3 | 0.29 | #138 (6; 2; 0.29), #586 (2; 1; 0.25) | reshuffled | T | supportive friend | Tend to get emotionally involved with a friend's probl…; Help my friends.; Am never too busy to help a friend. |
| 399 | 3 | 0.07 | #38 (12; 1; 0.07), #13 (18; 1; 0.05); 1 single | Gemma leaves single | T~ | thinking fails under stress (+ 'don't think as well as I used to') | Don't think as well as I used to.; Can't think clearly when under pressure.; Don't think straight when I am upset. |
| 431 | 2 | 0.03 | #3 (38; 1; 0.03); 1 single | Gemma wrong | N | panic spells + seizure-like attacks: symptoms | Experience panic spells.; Have attacks that resemble an epileptic fit. |
| 449 | 2 | 0.22 | #73 (9; 2; 0.22) | Gemma coarser | T | illness avoidance; Gemma #73 (9) = health anxiety, contains both | Do a lot of things just to avoid getting sick.; Have avoided situations or people for fear that I woul… |
| 453 | 2 | 0.20 | #233 (4; 1; 0.20); 1 single | Gemma leaves single | I | topic 'health / doctors' | Discuss my health problems with my family and friends.; Treat my doctors and other professionals as my friends. |
| 454 | 2 | 0.33 | #401 (2; 1; 0.33), #50 (11; 1; 0.08) | reshuffled | I | phrase 'unable to do' | Am unable to do some of the things I would like to do …; Am unable to do things properly. |
| 460 | 2 | 0.33 | #416 (2; 1; 0.33); 1 single | Gemma leaves single | I | how others see me, opposite needs (not odd vs not average) | Would hate to be considered odd or strange.; Never want to be thought of as average. |
| 464 | 2 | 0.25 | #179 (5; 1; 0.17), #341 (3; 1; 0.25) | reshuffled | N | undemanding about food (preference) | Am not picky about food.; Like bland food. |
| 467 | 2 | 0.25 | #306 (3; 1; 0.25); 1 single | Gemma leaves single | T | loves loud crowds, cheering | Cheer loudly at sporting events.; Enjoy being part of a loud crowd. |
| 471 | 2 | 0.00 | ; 2 single | Gemma leaves single | T | list-making (planful), bipolar; both items single in Gemma | Do not make lists.; Make lists of things to do. |
| 475 | 2 | 0.14 | #92 (8; 1; 0.11), #135 (6; 1; 0.14) | reshuffled | I | word 'soft' | Don't soften the truth.; Don't have a soft side. |
| 476 | 2 | 0.06 | #4 (35; 2; 0.06) | Gemma coarser | I | 'avoid ... people' (coarse vs complex) | Try to avoid coarse people.; Try to avoid complex people. |
| 482 | 2 | 0.33 | #249 (4; 1; 0.20), #595 (2; 1; 0.33) | reshuffled | I | word 'action' | Love action.; Don't like action movies. |
| 486 | 2 | 0.00 | ; 2 single | Gemma leaves single | I | word 'explain' (patience vs quick learning) | Am willing to explain things twice.; Need things explained only once. |
| 503 | 2 | 0.25 | #324 (3; 1; 0.25), #45 (11; 1; 0.08) | reshuffled | T | sees threat/difficulty everywhere | See difficulties everywhere.; See danger everywhere. |
| 511 | 2 | 0.12 | #3 (38; 1; 0.03), #105 (7; 1; 0.12) | reshuffled | T | guilt-prone, fear of doing wrong | Am afraid that I will do the wrong thing.; Feel that I have done something wrong. |
| 514 | 2 | 0.06 | #4 (35; 2; 0.06) | Gemma wrong | T | behind people's backs, bipolar; Gemma files it under privacy | Do things behind other people's backs.; Avoid doing things behind another person's back. |
| 520 | 2 | 0.33 | #41 (12; 1; 0.08), #496 (2; 1; 0.33) | reshuffled | N | excel / excel in nothing: competence self-assessment | Excel in what I do.; Excel in nothing at all. |
| 546 | 2 | 0.33 | #519 (2; 1; 0.33), #529 (2; 1; 0.33) | reshuffled | I | word 'punished' | Resent being punished.; Have often been punished without a good reason. |
| 547 | 2 | 0.00 | ; 2 single | Gemma leaves single | N | skills: bagpipes, helicopter | Know how to play the bagpipes.; Know how to fly a helicopter. |
| 555 | 2 | 0.33 | #531 (2; 1; 0.33); 1 single | Gemma leaves single | T | likes hard work, challenge | Feel better after some hard work.; Like hard jobs better than easy ones. |
| 572 | 2 | 0.17 | #220 (5; 1; 0.17), #32 (13; 1; 0.07) | reshuffled | T | worthlessness, imposter feeling | Feel that I do not deserve to be alive.; Feel like an imposter. |
| 579 | 2 | 0.33 | #249 (4; 1; 0.20), #600 (2; 1; 0.33) | reshuffled | I | 'love to': impressions, doodling | Love to do impressions.; Love to doodle. |
| 582 | 2 | 0.00 | ; 2 single | Gemma leaves single | T | morning dread, depressive | Wake each morning to feelings of tremendous sadness.; Dread getting up in the morning. |
| 599 | 2 | 0.25 | #304 (3; 1; 0.25), #111 (7; 1; 0.12) | Gemma finer | T | credit use, bipolar; Gemma splits by pole (frugal #304, overspending #111) | Never abuse my credit.; Overuse my credit. |

**S2. g600, kept, simple random sample** (44 clusters)

| # | size | J | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|
| 25 | 16 | 0.62 | T | emotional expressiveness, self-disclosure (2 strays: involve others, share things) | Wish I could more easily show my negative feelings.; Show my fear.; … (+14) |
| 27 | 16 | 0.50 | T~ | quick to learn / react; 'react intensely' stray, 'react slowly' opposite | Quickly recognize possibilities.; React immediately.; … (+14) |
| 45 | 12 | 0.71 | T | distractible | Am easily distracted when I'm trying to focus my atten…; Have difficulty concentrating on the job at hand when …; … (+10) |
| 58 | 11 | 0.75 | T~ | pleasure in pain: sadism (5) and self-injury (6), two traits | Am excited to inflict pain on others.; Crave the attention I get after hurting myself.; … (+9) |
| 78 | 9 | 0.67 | T | impatient with waiting, entitled | Tend to become agitated whenever I have to sit and wai…; Can't stand waiting.; … (+7) |
| 85 | 9 | 0.50 | T~ | messy / clumsy / careless; 'stumble over my words' stray | Leave a mess in my room.; Leave my belongings around.; … (+7) |
| 87 | 9 | 0.56 | T | low sexual interest (libido), bipolar | Rarely talk about sex.; Don't think much about sex.; … (+7) |
| 103 | 8 | 0.62 | T | sense of precognition, magical ideation | Can control the outcome of events.; Can predict the outcome of events.; … (+6) |
| 127 | 7 | 0.50 | T | shirks duties, passive sabotage | Put off unpleasant tasks.; Avoid responsibilities.; … (+5) |
| 131 | 7 | 1.00 | T | response to criticism, bipolar | Can stand criticism.; Am not afraid of providing criticism.; … (+5) |
| 148 | 6 | 0.50 | T | lives in the moment, doesn't plan | Don't plan anything very far in advance.; Do not plan ahead.; … (+4) |
| 149 | 6 | 0.50 | T | inattentive listener (1 stray: tunes out noise) | Was listening to someone talk and suddenly realized I …; Find it easy to tune out background noises when trying…; … (+4) |
| 157 | 6 | 0.60 | T~ | word 'secret': discreet vs secretive vs open | Can never keep a secret.; Like having secrets.; … (+4) |
| 158 | 6 | 0.67 | T~ | catharsis: crying/yelling helps + self-harm relieves | Believe that crying helps me feel better.; Feel that yelling helps me feel better.; … (+4) |
| 159 | 6 | 0.50 | T | leisurely, slow-paced | Like to take it easy.; Enjoy taking leisurely strolls.; … (+4) |
| 174 | 6 | 1.00 | N | subjective age (feel older / younger) | Act like people older than me.; Consider myself old.; … (+4) |
| 176 | 6 | 0.71 | T | religious belief, bipolar | Believe in God.; Believe in a universal power or God.; … (+4) |
| 178 | 6 | 1.00 | T | restless, fidgety | Am often fidgety.; Feel restless a lot of the time.; … (+4) |
| 189 | 5 | 0.56 | T | intolerant of rude, pushy people | Can't stand aggressive people.; Can't stand nosey people.; … (+3) |
| 193 | 5 | 1.00 | T | party-loving | Love surprise parties.; Am the life of the party.; … (+3) |
| 235 | 4 | 1.00 | T | fact-based decisions | Make decisions based on facts, not feelings.; Look at the facts.; … (+2) |
| 236 | 4 | 0.50 | T | emotionally fragile | Feel like I am "falling apart".; Feel weak.; … (+2) |
| 250 | 4 | 0.50 | T | practical vs pleasure buying, bipolar | Purchase only practical things.; Buy only the things I need.; … (+2) |
| 262 | 4 | 0.75 | T | dislikes surprises, the unknown | Hate surprises.; Am put off by unexpected events.; … (+2) |
| 271 | 4 | 0.50 | T | self-doubt | Am filled with doubts about things.; Often express doubts.; … (+2) |
| 283 | 4 | 0.75 | T | bad manners, blunt | Am told that things I say are not polite.; Have bad manners.; … (+2) |
| 289 | 4 | 0.50 | T | scientific vs supernatural belief, bipolar | Believe that all events can be explained scientificall…; Believe in things that have no scientific explanation.; … (+2) |
| 291 | 4 | 1.00 | T | chameleon / self-monitoring (would make a good actor) | Would make a good actor.; Could be a success in many fields.; … (+2) |
| 309 | 4 | 0.60 | T | broad perspective, wise | Have a broad outlook on what is going on.; Have an excellent view of the world.; … (+2) |
| 312 | 4 | 0.50 | N | tough-on-crime attitude (policy opinion) | Believe that we coddle criminals too much.; Believe that we should be tough on crime.; … (+2) |
| 314 | 3 | 0.75 | T | touch-averse | Am put off by people who touch or hug when speaking to…; Find it difficult to touch an object that has been tou…; Am uncomfortable touching other people in intimate sit… |
| 317 | 3 | 0.67 | T | no sympathy for rule-breakers | Have little sympathy for the unemployed.; Have no sympathy for criminals.; Have no sympathy for rule-breakers. |
| 318 | 3 | 0.67 | T | unsentimental, rarely weepy | Rarely cry during sad movies.; Seldom feel weepy while reading the sad part of a stor…; Seldom feel sad for longer than an hour. |
| 338 | 3 | 1.00 | T | gives to beggars | Give to panhandlers.; Give money to beggars.; Often feed homeless people at my front door. |
| 345 | 3 | 0.67 | T | returns what is owed | Return extra change when a cashier makes a mistake.; Return borrowed items.; Return library books on time. |
| 384 | 3 | 0.67 | T~ | self-sufficiency: buy not borrow, make things, avoid manufactured goods | Would rather buy something I need than borrow it from …; Prefer making things myself instead of buying them.; Would rather avoid using manufactured goods. |
| 392 | 3 | 1.00 | I | phrase 'world would be better': grandiosity (2) vs 'better off without me' (suicidal) | Know that the world would be a much better place if I …; Believe strongly that the world would be a much better…; Believe the world would be better off without me. |
| 444 | 2 | 0.50 | T | values emotions | Think that being in touch with emotions is essential.; Believe that emotions give direction to life. |
| 469 | 2 | 1.00 | T | curious how things work | Like to know how things work.; Am fascinated by how machines work. |
| 495 | 2 | 1.00 | T | stays on topic, bipolar | Keep on the topic.; Can't keep to the subject. |
| 507 | 2 | 1.00 | T | won't let things rest, pestering | Am not willing to let things rest.; Won't leave people alone. |
| 522 | 2 | 1.00 | N | follows the news (interest) | Know what's going on in the world.; Like to know the news of the world. |
| 532 | 2 | 1.00 | N | poor appetite (symptom/state) | Had a poor appetite.; Did not feel like eating, even though I should have be… |
| 553 | 2 | 0.67 | N | likes music (interest) | Get deeply immersed in music.; Like music. |

**S3. g600, loose, top-up of clusters with 10+ items (not in the headline rates)** (10 clusters)

| # | size | J | top Gemma overlaps: # (size; shared; J) | how the arms carve it | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|---|---|
| 3 | 28 | 0.39 | #46 (11; 11; 0.39), #129 (6; 5; 0.17) | Gemma finer | T~ | impulsive (act without thinking); ~8 strays on knowing one's own motives; Gemma #46 (11) is the clean core | Act spontaneously without thinking about the consequen…; Like to behave spontaneously.; … (+26) |
| 5 | 23 | 0.13 | #11 (20; 5; 0.13), #36 (12; 4; 0.13); 3 single | reshuffled | T | absorption, daydreaming; Gemma spreads it over forgetfulness #11 and imagination #36 | Rarely get bored because I start daydreaming when thin…; Spend much of the day fantasizing or daydreaming.; … (+21) |
| 9 | 21 | 0.24 | #55 (10; 6; 0.24), #211 (5; 5; 0.24); 1 single | Gemma finer | T | paranoid distrust; Gemma 10 + 5 | Feel that other people are out to get me.; Feel that people must earn my trust.; … (+19) |
| 10 | 21 | 0.38 | #85 (8; 8; 0.38), #95 (8; 5; 0.21); 1 single | Gemma finer | T | calm, composed (4 strays); Gemma #85 (8) clean core | Remain calm during emergencies.; Am calm even in tense situations.; … (+19) |
| 12 | 21 | 0.18 | #200 (5; 4; 0.18), #193 (5; 3; 0.13); 1 single | Gemma finer | T~ | decision style, bipolar, several sub-dimensions (speed, autonomy, persistence) | Make a decision and move on.; Stick to my previous decisions.; … (+19) |
| 13 | 21 | 0.32 | #98 (8; 7; 0.32), #4 (35; 4; 0.08) | Gemma finer | T | attention-seeking vs spotlight-avoiding, bipolar; Gemma #98 core | Demand attention.; Make myself the center of attention.; … (+19) |
| 14 | 20 | 0.44 | #22 (16; 11; 0.44), #173 (5; 5; 0.25) | Gemma finer | T~ | even-tempered; 'rarely' glue: ill, worry, depressed, drunk (6 of 20) | Rarely show my anger.; Rarely feel ill.; … (+18) |
| 19 | 18 | 0.21 | #6 (26; 6; 0.16), #18 (17; 6; 0.21) | reshuffled | T | manipulative, gets own way; Gemma: exploitation #6 / influence #18 | Enjoy manipulating other people's feelings.; Tell other people what they want to hear so that they …; … (+16) |
| 36 | 14 | 0.29 | #6 (26; 9; 0.29), #476 (2; 1; 0.07); 1 single | reshuffled | T~ | exploits others + is exploited (4 of 14 victim items) | Use others for my own ends.; Take advantage of others.; … (+12) |
| 41 | 13 | 0.25 | #34 (13; 5; 0.24), #120 (7; 4; 0.25); 1 single | reshuffled | T~ | conformist, follows others (+3 open-minded / credulous) | Form opinions based on others' beliefs.; Trust what people say.; … (+11) |

**S4. g600, kept, top-up of clusters with 10+ items (not in the headline rates)** (6 clusters)

| # | size | J | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|
| 1 | 33 | 0.71 | T | humorous, laughs a lot | Laugh out loud if something is funny.; Usually end up laughing if the people around me are la…; … (+31) |
| 18 | 19 | 0.85 | T | suicidal ideation | Thought about killing myself.; Had thoughts about death.; … (+17) |
| 22 | 18 | 0.52 | T | forgetful, easily confused | Forget appointments.; Mix up things.; … (+16) |
| 35 | 14 | 0.86 | T | sees self as ordinary vs extraordinary, bipolar | Enjoy being thought of as a normal "mainstream" person.; Am not an extraordinary person.; … (+12) |
| 43 | 13 | 0.69 | N | reading habit (interest) | Have read a lot.; Skip difficult words while reading.; … (+11) |
| 50 | 12 | 0.80 | N | body size (physical) | Feel that I am too fat.; Am a large-sized person.; … (+10) |

**S5. g350, loose** (15 clusters)

| # | size | J | top Gemma overlaps: # (size; shared; J) | how the arms carve it | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|---|---|
| 1 | 79 | 0.23 | #1 (103; 27; 0.17), #7 (46; 23; 0.23) | reshuffled | I | 79-item antagonism domain: judging, gossip, prying, revenge, exploitation, interrupting (6+ traits) | Sometimes lack remorse for treating people badly.; Am quick to judge others.; … (+77) |
| 11 | 36 | 0.45 | #18 (35; 22; 0.45), #10 (42; 4; 0.05) | reshuffled | T~ | helping + people-pleasing (the g600 #2 region, larger) | Am willing to make personal sacrifices in order to hel…; Try to fit in with others.; … (+34) |
| 56 | 15 | 0.26 | #42 (19; 7; 0.26), #33 (24; 4; 0.11); 1 single | reshuffled | T | goal-oriented achievement striving | Find that I am able to pursue one goal for a long time.; Can make myself work on a difficult task even when I d…; … (+13) |
| 87 | 12 | 0.46 | #131 (7; 6; 0.46), #26 (29; 3; 0.08) | Gemma finer | T | respectful, proper; Gemma #131 (7) core | Respect older people.; Respect others.; … (+10) |
| 99 | 11 | 0.23 | #179 (5; 3; 0.23), #8 (46; 2; 0.04); 2 single | Gemma finer | T | cynicism about motives | Believe that most people would lie to get ahead.; Believe that most people dislike helping other people.; … (+9) |
| 123 | 9 | 0.25 | #77 (12; 3; 0.17), #156 (6; 3; 0.25) | reshuffled | T | rude, sharp-tongued | Have a sharp tongue.; Shoot my mouth off.; … (+7) |
| 127 | 8 | 0.18 | #14 (36; 2; 0.05), #166 (5; 2; 0.18); 1 single | Gemma wrong | T | harmless, non-violent, non-vengeful; Gemma scatters it into 'rarely' blob #14 | Make a point of trying not to hurt others in pursuit o…; Wouldn't harm a fly.; … (+6) |
| 157 | 7 | 0.45 | #106 (9; 5; 0.45), #29 (25; 1; 0.03) | reshuffled | T | health-conscious self-control | Find it easy to stay healthy.; Have no trouble eating healthy foods.; … (+5) |
| 208 | 5 | 0.44 | #120 (8; 4; 0.44), #70 (13; 1; 0.06) | reshuffled | T | non-intellectual, avoids abstraction | Will not probe deeply into a subject.; Am not interested in speculating about things.; … (+3) |
| 219 | 4 | 0.04 | #2 (69; 3; 0.04); 1 single | Gemma wrong | T | private person; Gemma #2 is a 69-item aloofness blob | Believe that privacy is very important.; Enjoy my privacy.; … (+2) |
| 238 | 4 | 0.12 | #4 (50; 2; 0.04), #7 (46; 1; 0.02) | reshuffled | I | words 'notice / look' | Get upset when others don't notice how I look.; Get upset when others notice how I look.; … (+2) |
| 281 | 3 | 0.25 | #113 (9; 2; 0.20), #344 (2; 1; 0.25) | reshuffled | T | prefers immediate gains, bipolar | Sometimes do things for quick gains.; Generally give preference to those activities that imp…; Forego things that are bad for me in the long run even… |
| 292 | 3 | 0.14 | #174 (5; 1; 0.14), #67 (14; 1; 0.06) | reshuffled | I | phrase 'Would be described by friends as ...' | Would be described by friends and family as interested…; Would be described by my friends as brave.; Would be described by my friends as having lots of pos… |
| 299 | 2 | 0.08 | #76 (12; 1; 0.08); 1 single | reshuffled | I | word 'appearance' | Feel that people or things change in their appearance …; Judge people by their appearance. |
| 300 | 2 | 0.04 | #7 (46; 2; 0.04) | Gemma wrong | T | con artist; Gemma #7 (46) swallows it | Admire a really clever scam.; Am a very good scam artist. |

**S6. g350, kept** (10 clusters)

| # | size | J | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|
| 28 | 23 | 0.56 | I | word 'problem': solving ability vs catastrophizing vs causing problems vs wiring | Find myself in the same kinds of trouble, time after t…; Prefer to analyze problems rather than to just describ…; … (+21) |
| 101 | 10 | 0.50 | T | dissociative amnesia, fantasy/reality confusion | Confuse fantasies with real memories.; Find it difficult to tell whether something really hap…; … (+8) |
| 200 | 5 | 0.83 | T | party-loving | Love surprise parties.; Am the life of the party.; … (+3) |
| 220 | 4 | 0.50 | T | curious about mechanisms, systemizing | Like to know how things work.; Am fascinated by how machines work.; … (+2) |
| 243 | 3 | 0.60 | N | episodes of paralysis/stiffness (symptoms) | Feel paralyzed for awhile.; Grow stiff for awhile.; Felt that I could not move my hands or feet. |
| 246 | 3 | 0.67 | I | word 'surprise' (hidden capability) | Find that in certain situations I am able to do things…; Am often so assertive or sociable that I surprise myse…; Find that my friends get surprised to discover things … |
| 269 | 3 | 1.00 | T~ | self-sufficiency (as g600 #384) | Would rather buy something I need than borrow it from …; Prefer making things myself instead of buying them.; Would rather avoid using manufactured goods. |
| 270 | 3 | 1.00 | N | music (interest) | Notice the way that music is structured; Get deeply immersed in music.; Like music. |
| 316 | 2 | 0.67 | T~ | word 'harmony': preference + belief | Like harmony in my life.; Believe in universal harmony. |
| 319 | 2 | 0.50 | T | won't let things rest | Am not willing to let things rest.; Won't leave people alone. |

**S7. g150, loose** (15 clusters)

| # | size | J | top Gemma overlaps: # (size; shared; J) | how the arms carve it | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|---|---|
| 3 | 174 | 0.22 | #5 (119; 52; 0.22), #6 (117; 39; 0.15) | reshuffled | I | 174-item negative-emotion blob: anger, sadness, emotional confusion, excitability | Shout or scream when I'm angry.; Can be confused about the emotions I'm feeling.; … (+172) |
| 11 | 51 | 0.38 | #23 (44; 26; 0.38), #38 (19; 5; 0.08); 1 single | reshuffled | T~ | 51 items, competence / self-efficacy / resilience (domain-level) | Readily overcome setbacks.; Know how to do my job.; … (+49) |
| 13 | 50 | 0.20 | #4 (148; 26; 0.15), #42 (17; 11; 0.20) | reshuffled | T~ | 50 items, worry / fear / pessimism / social anxiety (domain-level) | Often think about the possibility of negative outcomes…; Often worry about things that turn out to be unimporta…; … (+48) |
| 15 | 48 | 0.10 | #9 (83; 12; 0.10), #6 (117; 11; 0.07) | reshuffled | I | expressiveness + honesty + promise-keeping + duty + gender roles | Wish I could more easily show my negative feelings.; Show my fear.; … (+46) |
| 23 | 42 | 0.05 | #1 (390; 18; 0.04), #2 (172; 5; 0.02) | Gemma wrong | T~ | attention / approval seeking, bipolar, broad; Gemma #1 is a 390-item blob | Feel smothered when others show deep concern towards m…; Embarrass others.; … (+40) |
| 32 | 34 | 0.39 | #44 (16; 14; 0.39), #4 (148; 6; 0.03) | Gemma coarser | T~ | thrill-seeking (+ conflict, intoxicants, campaigning, illegal fun) | Love excitement.; Seek adventure.; … (+32) |
| 55 | 18 | 0.13 | #9 (83; 6; 0.06), #69 (8; 3; 0.13); 1 single | reshuffled | T~ | conventional, traditional, formal, simple life (+4 strays) | Have a conventional lifestyle.; Like to be viewed as proper and conventional.; … (+16) |
| 59 | 16 | 0.26 | #30 (28; 9; 0.26), #107 (4; 3; 0.18) | reshuffled | I | 'Love ...': children, animals, eating, sleep, roller coasters, torture animals | Like to watch children open presents.; Like to be around children.; … (+14) |
| 65 | 15 | 0.43 | #39 (18; 10; 0.43), #9 (83; 2; 0.02); 1 single | reshuffled | T~ | addictive, indulgent (+ habit strays) | Experience pangs of hunger that cause me to devour eve…; Turn ugly when I drink too much..; … (+13) |
| 72 | 13 | 0.12 | #22 (46; 5; 0.09), #21 (46; 3; 0.05) | reshuffled | T | competitive, bipolar | Am a good loser.; Acknowledge others' accomplishments.; … (+11) |
| 101 | 6 | 0.29 | #41 (17; 3; 0.15), #122 (3; 2; 0.29) | reshuffled | T | compulsive checking and cleaning | Check over my work.; Repeatedly check doors, windows, and drawers.; … (+4) |
| 111 | 5 | 0.05 | #24 (41; 2; 0.05), #5 (119; 1; 0.01) | reshuffled | T~ | feels cheated, resentful (+ 'cheapskate') | Feel short-changed in life.; Resent being punished.; … (+3) |
| 112 | 5 | 0.12 | #3 (165; 1; 0.01), #30 (28; 1; 0.03) | reshuffled | T | hostility vs love of enemies, bipolar | Have occasionally disliked someone.; Love my enemies.; … (+3) |
| 127 | 3 | 0.22 | #67 (8; 2; 0.22), #4 (148; 1; 0.01) | reshuffled | I | 'Wish ...': health, somebody else, employment | Wish I was less concerned about my health.; Wish that I was somebody else.; Wish that I were more fully employed. |
| 140 | 2 | 0.14 | #46 (14; 2; 0.14) | Gemma coarser | T | cynical about love; Gemma #46 = low sex/romance interest | Think that love is overrated.; Do not believe humans are truly capable of love. |

**S8. g150, kept** (10 clusters)

| # | size | J | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|
| 17 | 45 | 0.75 | T | humorous, laughs a lot | Laugh out loud if something is funny.; Usually end up laughing if the people around me are la…; … (+43) |
| 45 | 22 | 0.55 | T | appearance-conscious, bipolar (2 strays) | Feel that people or things change in their appearance …; Know that sometimes my clothes don't match (and I don'…; … (+20) |
| 61 | 16 | 0.50 | T | patience vs impatience | Am rarely a patient person.; Find it very annoying to have to wait a few minutes fo…; … (+14) |
| 62 | 16 | 0.58 | T | justice, equality, fairness | Care about justice.; Treat all people equally.; … (+14) |
| 69 | 14 | 0.71 | N | reading (interest) | Have read a lot.; Skip difficult words while reading.; … (+12) |
| 71 | 13 | 0.62 | T | aesthetic appreciation | See beauty in things that others might not notice.; Love beautiful things.; … (+11) |
| 73 | 13 | 0.50 | T~ | need to understand, explanations (+3 'explain' strays) | Am willing to explain things twice.; Want to know what I am up against.; … (+11) |
| 99 | 6 | 0.86 | I | phrase 'Would never ...': risk-aversion and moral rules | Would never make a high-risk investment.; Would never accept welfare.; … (+4) |
| 130 | 3 | 0.67 | T | rarely smiles, dour | Rarely smile.; Can't remember the last time I smiled.; Need to force and remind myself to smile every day. |
| 136 | 3 | 1.00 | N | synesthesia, odd perceptions | Have noticed that different letters of the alphabet ha…; Have noticed that different odors have different color…; Have sensed strange smells that others do not sense. |

**S9. g600, the Gemma arm's own loose clusters (Gemma numbering, rebuilt cut)** (40 clusters)

| # | size | J | top OpenAI overlaps: # (size; shared; J) | how the arms carve it | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|---|---|
| 9 | 20 | 0.26 | #77 (9; 6; 0.26), #44 (12; 2; 0.07) | Gemma finer | T | sadness, depressive affect | Dislike being around happy people when I'm feeling sad.; Show my sadness.; … (+18) |
| 12 | 19 | 0.31 | #6 (23; 10; 0.31), #137 (7; 4; 0.18) | reshuffled | T | openness to new ideas and learning | Get excited by new ideas.; Like to begin new things.; … (+17) |
| 14 | 18 | 0.26 | #11 (21; 8; 0.26), #183 (5; 4; 0.21) | reshuffled | I | 'myself': self-improvement + self-reflection + self-centred talk + talking to oneself | Talked out loud to myself.; Know that I can improve myself.; … (+16) |
| 25 | 16 | 0.46 | #17 (19; 11; 0.46), #304 (4; 1; 0.05) | reshuffled | T | empathic accuracy, reading others | Feel others' emotions.; Sympathize with others' feelings.; … (+14) |
| 43 | 11 | 0.25 | #308 (4; 3; 0.25), #29 (15; 2; 0.08) | reshuffled | T | apathetic, unenthusiastic | Rarely get caught up in the excitement.; Don't get excited about things.; … (+9) |
| 95 | 8 | 0.21 | #10 (21; 5; 0.21), #81 (9; 1; 0.06) | reshuffled | T~ | word 'control': self-control, situations, outcomes, objects by mind | Keep situations under control.; Keep my emotions under control.; … (+6) |
| 97 | 8 | 0.38 | #64 (10; 5; 0.38), #366 (3; 1; 0.10) | Gemma finer | T | leadership | Try to lead others.; Want to be in charge.; … (+6) |
| 120 | 7 | 0.25 | #41 (13; 4; 0.25), #72 (10; 1; 0.06) | reshuffled | I | follow others (4) + get even, share things, get my way | Get even with others.; Follow others.; … (+5) |
| 123 | 7 | 0.15 | #97 (8; 2; 0.15), #67 (10; 1; 0.06) | reshuffled | T | unable/unwilling to manipulate or deceive, bipolar | Am not easily fooled by others.; Lack the talent for influencing people.; … (+5) |
| 158 | 6 | 0.35 | #24 (17; 6; 0.35) | Gemma coarser | T | pessimist | Am a negative type of person.; Am a pessimistic person.; … (+4) |
| 182 | 5 | 0.21 | #21 (18; 4; 0.21), #36 (14; 1; 0.06) | reshuffled | T | gossip | Like to gossip.; Abuse people's confidences.; … (+3) |
| 218 | 5 | 0.29 | #285 (4; 2; 0.29), #220 (5; 2; 0.25) | reshuffled | T | vain, shows off body | Like to look at my body.; Like to look at myself in the mirror.; … (+3) |
| 222 | 5 | 0.44 | #93 (8; 4; 0.44), #279 (4; 1; 0.12) | reshuffled | T | dislikes the arts | Do not like to visit museums.; Do not like poetry.; … (+3) |
| 273 | 4 | 0.33 | #288 (4; 2; 0.33), #135 (7; 1; 0.10) | reshuffled | T~ | non-religious (+ 'do not stand up for my beliefs') | Don't consider myself religious.; Do not stand up for my beliefs.; … (+2) |
| 285 | 3 | 0.25 | #436 (2; 1; 0.25), #240 (4; 1; 0.17) | reshuffled | I | topic 'dreams' | Have frightening dreams.; Usually have dreams that don't have an elaborate or de…; Get lost in my dreams. |
| 299 | 3 | 0.17 | #243 (4; 1; 0.17), #2 (32; 1; 0.03) | reshuffled | I | rarely silly / please others / avoid rejection | Rarely enjoy behaving in a silly manner.; Do things that I don't like to make others happy.; Often refrain from doing something I like in order not… |
| 301 | 3 | 0.18 | #67 (10; 2; 0.18); 1 single | reshuffled | T | suggestible | Am easily talked into doing silly things.; Let myself be talked into doing things.; Have persuaded others to do something really adventuro… |
| 310 | 3 | 0.29 | #143 (6; 2; 0.29), #348 (3; 1; 0.20) | reshuffled | I | memento + good memory | Cherish mementos.; Have a good memory.; Have a good memory for things I've down throughout the… |
| 341 | 3 | 0.25 | #382 (3; 1; 0.20), #276 (4; 1; 0.17) | reshuffled | I | food: love to eat, new foods, bland food | Love to eat.; Love to try new foods that I have not eaten before.; Like bland food. |
| 357 | 3 | 0.33 | #89 (9; 3; 0.33) | Gemma coarser | T | cynical about honesty | Believe that most people would lie to get ahead.; Assume that most people lie or cheat to get ahead.; Assume that most people will lie to get what they want. |
| 370 | 3 | 0.38 | #105 (8; 3; 0.38) | Gemma coarser | T | believes in ESP, superpowers | Believe I have "ESP," or extrasensory perception.; Believe I have supernatural powers.; Believe that superpowers are possible in humans. |
| 383 | 2 | 0.33 | #437 (2; 1; 0.33), #48 (12; 1; 0.08) | reshuffled | I | sleepless + works long hours | Can't sleep for nights on end but remain active during…; Work longer hours than most people. |
| 410 | 2 | 0.33 | #153 (6; 2; 0.33) | Gemma coarser | T | aesthetic emotional awareness | Am usually aware of the emotions that are portrayed in…; Am often aware how the color and lighting of a room af… |
| 414 | 2 | 0.25 | #337 (3; 1; 0.25), #73 (10; 1; 0.09) | reshuffled | I | seldom helps + rarely consulted | Seldom help out when people feel overwhelmed by things…; Am rarely consulted for advice by others. |
| 422 | 2 | 0.40 | #192 (5; 2; 0.40) | Gemma coarser | T | curt on the phone, no small talk | Hang up the phone on people.; Don't call people just to talk. |
| 434 | 2 | 0.20 | #61 (10; 2; 0.20) | Gemma coarser | T | easygoing, takes things as they come | Take things as they come.; Accept the first thing that comes along. |
| 442 | 2 | 0.25 | #164 (6; 1; 0.14), #406 (3; 1; 0.25) | reshuffled | I | 'willing to': compromise / bend the truth | Am willing to make compromises.; Am willing to bend the truth if it will benefit me. |
| 457 | 2 | 0.33 | #165 (6; 2; 0.33) | Gemma coarser | T | direct, to the point | Go straight for the goal.; Come straight to the point. |
| 459 | 2 | 0.25 | #264 (4; 1; 0.20), #357 (3; 1; 0.25) | reshuffled | I | give in to no one + take no time for others | Give in to no one.; Take no time for others. |
| 463 | 2 | 0.20 | #259 (4; 1; 0.20); 1 single | reshuffled | T | wants to know everything | Investigate all possibilities.; Want to know everything. |
| 469 | 2 | 0.25 | #11 (21; 1; 0.05), #376 (3; 1; 0.25) | reshuffled | T | talkative, never at a loss for words | Never stop talking.; Am never at a loss for words. |
| 479 | 2 | 0.14 | #148 (6; 1; 0.14), #96 (8; 1; 0.11) | reshuffled | I | word 'day' | Live from one day to the next.; Look forward to each new day. |
| 489 | 2 | 0.33 | #83 (9; 1; 0.10), #512 (2; 1; 0.33) | reshuffled | T | can't get going (inertia) | Find it difficult to get down to work.; Could not get going. |
| 498 | 2 | 0.15 | #43 (13; 2; 0.15) | Gemma coarser | T | avoids difficult reading | Skip difficult words while reading.; Avoid difficult reading material. |
| 523 | 2 | 0.20 | #75 (10; 2; 0.20) | Gemma coarser | T | won't take the blame | Won't take the blame for something that's not my fault.; Am slow to take the blame. |
| 526 | 2 | 0.22 | #88 (9; 2; 0.22) | Gemma coarser | T | deserving, bipolar (entitlement) | Have already gotten more than I deserve.; Deserve more than I am getting. |
| 550 | 2 | 0.20 | #298 (4; 1; 0.20); 1 single | reshuffled | T | enjoys natural disasters (thrill) | Might actually enjoy being caught in an earthquake or …; Would prefer being in a hurricane or earthquake to spe… |
| 564 | 2 | 0.33 | #156 (6; 2; 0.33) | Gemma coarser | T | emotional for no reason (moody) | Become emotional for no apparent reason.; Can get anxious, depressed, or irritable for no reason. |
| 570 | 2 | 0.25 | #410 (3; 1; 0.25), #226 (5; 1; 0.17) | reshuffled | T | flirts with strangers | Enjoy flirting with complete strangers.; Like it when strangers find me sexually appealing. |
| 599 | 2 | 0.50 | #312 (4; 2; 0.50) | Gemma coarser | N | tough-on-crime attitude | Believe that we should be tough on crime.; Believe that laws should be strictly enforced. |

**S10. g600, the Gemma arm's own kept clusters** (10 clusters)

| # | size | J | verdict | what the verdict rests on | items (abridged) |
|---|---|---|---|---|---|
| 62 | 10 | 0.50 | T | plans ahead, future-oriented | Eagerly look forward to things to come.; Like to talk about my future plans.; … (+8) |
| 174 | 5 | 0.50 | T | loyal to old friends | Value having long-term close relationships with people.; Am faithful to old friends.; … (+3) |
| 181 | 5 | 0.50 | T | respectful | Respect older people.; Respect others.; … (+3) |
| 226 | 4 | 0.50 | T | values emotions | Find examination of my feelings useful in solving pers…; Think that being in touch with emotions is essential.; … (+2) |
| 344 | 3 | 0.75 | N | prefers nonfiction (reading preference) | Prefer to read nonfiction more than fiction.; Don't read nonfiction books for fun.; Prefer reading non-fiction to fiction. |
| 395 | 2 | 1.00 | T | cynical about love | Think that love is overrated.; Do not believe humans are truly capable of love. |
| 396 | 2 | 0.50 | T | absent-minded travel (highway hypnosis) | Drove or rode somewhere without remembering later what…; Often cannot recall the exact route I took to get some… |
| 534 | 2 | 0.50 | T | enjoys storms (thrill) | Would enjoy being out on a sailboat during a storm.; Like to go outside during violent thunderstorms. |
| 556 | 2 | 0.50 | T | competitive | Like to add competitive features to all activities.; Like to compete and do everything I can to win. |
| 561 | 2 | 0.67 | T | rigid, inflexible | Am inflexible when I think I'm right.; Have been told that I am rigid and inflexible. |

