# Plan 01: psycholexical censuses as a candidate generator

## 1. Idea
Use the existing dictionary-derived censuses of person-descriptive English (Allport & Odbert 1936 and their descendants) as a fixed, exhaustive candidate pool, then filter for trait-hood and model-familiarity and run the novelty scorer over what survives. The pool was compiled from Webster's in 1936 and re-curated in 1967/1982/2021 by people who had never seen our list, so it cannot be biased toward recreating it; its bias is toward what English single-word adjectives encode, which is a known and testable bias.

## 2. Sources and tools (verified 2026-09-18 via OSF/Dataverse/GitHub APIs; nothing downloaded)
| Source | Availability | Format | Licence | Notes |
|---|---|---|---|---|
| **Allport & Odbert 1936, digitised** (Parker, Karl, Fischer et al.), OSF `k6rwj` | public, direct download links | one word per line, four files preserving the columns: Personal Traits 4,469 / Temporary States 5,190 / Social Evaluations 4,510 / Metaphorical-Doubtful 3,651; plus a merged 17,716-word file and the scanned monograph PDF | **CC BY 4.0** | adjectives (and a few participles/nouns), no glosses, some OCR noise ("Accomodating", "Afald"), many obsolete words (accendible, accroaching). Capitalised, some trailing spaces, a few French terms. |
| **TDA: 2,818 Trait Descriptive Adjectives** (Condon, Coughlin & Weston 2022, *J. Open Psych. Data*), Harvard Dataverse doi:10.7910/DVN/5T80PF, site pie-lab.github.io/tda | public | `TDA_properties.tab` (csv): `adjective, N, prop` (familiarity = proportion of a representative US sample matching word to definition, two forms per word), `gbooks.freq` (Google Books, log-scaled), flags `GN1710` (Goldberg/Norman 1,710), `SG435` (Saucier & Goldberg 1996 familiar 435), `BFFM100` (Goldberg 1992 markers) | **CC0** | = Goldberg's 1,710 + terms Norman/A&O had dropped. Adjectives only. **The Oxford definitions are not in the public files** (withheld with the vocabulary items; codebook says contact the author). No explicit Allport-column or Norman flag in the properties file (the paper text claims membership info; unverified beyond the three flags). |
| Goldberg 1982 (1,710) and Norman 1967 (2,800) | 1,710 is a PDF appendix on projects.ori.org (no licence stated); Norman's 2,800 with his own four-way trait/state/role/evaluation sort is **not** separately digitised as far as I could find | | | Superseded by the TDA `GN1710` flag; Norman's category sort would be the useful extra and is unverified. |
| Anderson 1968 (555 likableness-rated) re-normed by Chandler 2018 (555+486), OSF `3wqx5` | public raw csvs | MTurk raw ratings (likability, meaningfulness, **emotion-vs-non-emotion coding**); words extractable from the `Input.Word*` columns; includes multiword items ("gold digger") | no licence set on OSF | Anderson's original appendix is APA-copyright. Value: likableness (valence) and the emotion coding as a state-vs-trait signal. |
| Dumas, Johnson & Lynch 2002 (844 words, likableness/familiarity/frequency) | paywalled Elsevier appendix; no open copy found | | | skip unless Roger has access. |
| Saucier mini-markers (40), Goldberg 100 markers | public domain via IPIP | tiny | | already subsumed by `BFFM100`. |
| Gough & Heilbrun Adjective Check List (300) | commercial (Mind Garden/CPP), copyrighted | | | do not use. |
| Saucier 2003 type-nouns (~372: nerd, bully, saint) | in paper only | | | not traits; hand to the roles workstream. |
| Tools: `wordfreq` (MIT, Zipf frequencies) and WordNet via `nltk`/`wn` (Princeton licence) | not installed in the env (checked); both pip-installable | | | for the frequency floor and gloss/sense counts on the 15k Allport words TDA does not cover. |

**Baseline overlap, computed by streaming the files:** 265/385 existing trait labels (69%) are in the TDA 2,818 (191 in GN1710, 125 in SG435); 279/385 are in the full Allport list; 334 of the ~967 seed-queue labels are in Allport. Median TDA familiarity of our hits is 0.81 (min 0.12). The misses are the multiword, ideological and cognitive-style labels (deontological, data-driven, egalitarian, calibrated, closure-seeking).

## 3. Method
1. **Ingest** both lists into one table: `word, source_flags (AO_I..IV, GN1710, SG435, BFFM100, Chandler), familiarity, gbooks_freq, likableness, emotion_coded`. Normalise case, strip whitespace, fix obvious OCR misspellings by matching against WordNet/wordfreq vocabulary (anything absent from both is flagged, not deleted).
2. **Frequency floor.** For TDA words use `prop` (familiarity) and `gbooks.freq`; for the rest use `wordfreq` Zipf. Calibrate the cut on our own labels: choose the threshold that keeps 95% of the 279 existing labels found in Allport (expect Zipf about 3.0 / familiarity about 0.6; the TDA counts at 0.6/0.7/0.8 are 2,204/1,850/1,411 words). Optionally probe the borderline band directly on Qwen3-32B ("define X in one line", scored against the WordNet gloss) since the model, not humans, is the audience.
3. **Gloss and sense count.** Attach WordNet glosses for every sense; the number of senses and whether any sense is person-descriptive are the polysemy signal the September lessons ask for. Then one Haiku-class call per batch of ~20 words returns, per word, the *person-descriptive sense as a one-line gloss* plus a flag when the common sense is not that sense (disciplinary/engaging/economic). Words with no person-descriptive sense drop out.
4. **Trait-hood filter.** Combine (a) Allport column and Chandler emotion coding as features and (b) an LLM judgement against Roger's definition ("a stable disposition or style a speaking persona can enact in text"), returning trait / state / evaluation / physical-or-appearance / role-noun / not-usable. Do not filter on Allport column alone: `agitated`, `flustered`, `harmful` are column II/III and are in our set. Calibrate on the 265 known labels: the filter must pass at least 90% of them.
5. **Novelty.** Feed survivors (word + gloss) to the shared novelty scorer against existing descriptions and the seed queue. Keep its three outputs: duplicate / antonym-completion / gap.
6. **Rank and cluster** the gaps by (familiarity, |likableness| as a proxy for evaluative load, embedding cluster) so Roger reviews clusters of 5-15 near-synonyms and picks one label per cluster rather than reading 1,000 rows.

## 4. Expected yield and biases
Allport 17.7k -> frequency floor ~6-8k -> person-descriptive sense ~4-5k -> trait-hood ~2.5-3.5k -> minus duplicates/near-synonyms of our 385 + 867 queued: roughly 800-1,500 candidate words, collapsing to perhaps 150-300 clusters. The TDA-only route yields ~500-800 words / 100-150 clusters at much higher precision. Over-produces: single evaluative adjectives (nice, pleasant, agreeable and their 30 synonyms), appearance and physique words, emotion states, archaic vocabulary, Big Five-region synonyms. Under-produces: multiword labels, ideological and epistemic stances, cognitive-style and AI-alignment-region traits (sycophantic is present; ends-justify-means, rationalizing, reward-hacking are not), anything coined after 1936 (data-driven, closure-seeking). So it is a recall generator for the classic personality region and near-useless for the oversampled alignment region.

## 5. Cost
API: glossing plus trait-hood for ~5k words in batches of 20 is ~250 calls, ~1M tokens on a Haiku-class model: low single-digit dollars; a Sonnet-class second opinion only on disagreement between the LLM and the source flags (expect ~10-15% of words): another $1-3. Local: wordfreq/WordNet lookups and embeddings of 5k glosses run in minutes on the Mac. Roger: ~1 hour to calibrate thresholds on the 50-word disagreement samples, then 2-4 hours reviewing 150-300 clusters.

## 6. Testing
- **Membership ceiling** (already measured): 69% of labels are in TDA, 72% in Allport. Report the same for each new batch of adopted traits; a falling ceiling tells us the corpus has moved past what adjectives encode.
- **Filter recall**: hide all existing files; the frequency and trait-hood filters must pass at least 90% of the 265/279 known labels. Every rejected known label is inspected by hand (it is either a filter bug or a label we might reconsider).
- **Novelty behaviour**: with one file of a clean pair hidden, the scorer should return its partner as antonym-completion, not duplicate, for at least 80% of pairs.
- **Precision spot check**: Roger judges 50 random survivors; target at least 70% "would consider".
- **Polysemy check**: the flag must fire on the September rejects (disciplinary, engaging, economic, balanced, empowered) if they are in the pool.

## 7. Dependencies
Needs: the candidate-registry format (word, gloss, source, flags, scores), the shared trait-hood judge prompt, the novelty scorer with its duplicate/antonym/gap output. Provides: a CC0/CC-BY candidate table with familiarity and frequency for every word, which other generators can reuse as their frequency floor and as a negative control ("did the LLM brainstormer only re-emit census words?"); the filter-recall harness.

## 8. Variants
A. **TDA-first** (2,818, CC0, familiarity and frequency built in): a day of work, high precision, no OCR clean-up. B. **Full Allport** (17.7k, CC BY): adds the 15k words Norman and Goldberg discarded; most are obsolete or non-trait, but the states and social-evaluation columns are exactly where our corpus already takes words TDA lacks. Recommend A first, then B restricted to words above the frequency floor, using A to calibrate.

## 9. Open questions for Roger
1. Is the frequency floor to be calibrated on human familiarity (TDA `prop`) or on the 32B model's own definitions? The latter costs a RunPod probe of ~3k words.
2. Threshold policy: keep 95% of existing labels (permissive, more review) or 90% (tighter)?
3. Are state words (column II) in scope as traits by default, as `agitated` suggests, or only when a persona can sustain them?
4. Is emailing Condon for the withheld Oxford definitions worth it, or are WordNet plus LLM glosses sufficient?
5. Should the Saucier type-nouns be passed to the roles workstream now?

## 10. Roger Decisions
1. Let's discuss
2. Unsure, incline towards trying both and seeing what 

## 10. Resolution (2026-09-23)

1. Frequency floor: Zipf as a feature, not a gate (see plan 14 § 11); TDA familiarity where the
   word is in TDA; a Haiku definition probe below Zipf 2.5; no RunPod probe until adoption.
2. Threshold policy: keep 95% of existing labels.
3. State words (column II) are in scope when they name a disposition to be in that state; the
   gloss must say "a general tendency to ...", not describe an episode (Roger, 2026-09-23; the
   state-trait distinction from affect research is the model).
4. Contacting Condon for the withheld definitions: see the discussion of 2026-09-23 (Roger to
   decide).
5. Saucier type nouns: to the roles holding list in the registry, low priority.
