# Coding plan: workstream 7, IPIP behavior items (generator id `ipip`)

Written 2026-10-10 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[07_behaviour_items.md](./07_behaviour_items.md) and Roger's § 9 answers of 2026-10-10, against the
"Interface as built" of [coding_plan_platform.md](./coding_plan_platform.md).  Cluster the ~3,320
public-domain IPIP self-report items by embedding, have an LLM name each cluster blind and hinted,
and submit the named poles to the platform (M1, then M3).  Roger's review comments go into this file.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **IPIP-only.**  The IPIP-HEXACO scales (Ashton, Lee & Goldberg 2007) are inside the ordinary scrape of the three HTML pages, so HEXACO-PI-R appears nowhere in this plan: no research-only licence, no uncommittable input. | verified 2026-10-10 | plan 07 § 2 and the boxed answer under § 9.2 |
| ~~**No symptom filter.**~~ (superseded by QUESTIONS 48, below: there is no filter at all.)  Symptom-like dispositions are traits for this corpus; the naming rubric's `is_trait` counted them in.  Precedent already on disk: [adhd](../../data/traits/instructions/adhd.json), [ocd](../../data/traits/instructions/ocd.json), [obsessive](../../data/traits/instructions/obsessive.json), [dissociative](../../data/traits/instructions/dissociative.json).  Moods, abilities, interests and life circumstances stay out of the submission (reported, not submitted; M1 would tag them anyway). | Roger: "Traits already include ADHD and OCD: symptoms are fair game" | plan 07 § 9.1; § 3.4 |
| **Both labels generated for every pole; blind is the provisional primary.**  The registry stores one surface, so the blind label is submitted and the hinted label travels in the cluster table and the report, side by side; a blind/hinted disagreement is a review flag.  Blind recommended as primary because it is independent of the taxonomy vocabulary already gap-scanned (the point of this workstream); which is primary is a pilot decision for Roger. | Roger: "generate both, and we can evaluate once we see what we're getting" | plan 07 § 9.3 |
| ~~**Two granularities, ~350 and ~150 clusters, decided by the overlap call.**~~ (the measure is superseded by QUESTIONS 50, below; the two granularities stand.)  Roger's criterion ("clusters about the same size as our '3-4' relationship level for covered judgements") is operationalized in § 7 `granularity`: sampled within-cluster item pairs are read with M3's overlap call (rubric A, 0-4), and the readout reports each granularity's share of pairs at 3 or 4.  The winner is the one whose distribution centers on 3-4. | Roger: "Try both ..." | plan 07 § 9.4 |
| **The scraped items are tracked**: [items.jsonl](../../data/candidates/ipip/items.jsonl) (not yet on disk) under `data/candidates/ipip/`, like the censuses' tracked table.  Public domain by IPIP's blanket statement, ~3,320 rows (~1.5 MB).  The raw HTML stays gitignored under `data/external/ipip/` with a manifest. | provenance; the census precedent ([coding_plan_01_censuses.md](./coding_plan_01_censuses.md) § 5) | task brief |
| **Embedders: OpenAI `text-embedding-3-large` plus `google/embeddinggemma-300m`** (already in `data/external/hf/`), through the platform's [embed.py](../../assistant_axis/gapgen/embed.py) (`make_embedder("openai"|"gemma")`, `EmbeddingCache`, `embed_texts`).  No new model download; plan 07's bge/gte suggestion is superseded (bge is not on disk, gemma is, and `sentence-transformers` is already a dependency). | reuse over invention; M2's model decisions | platform "M2 final settings" |
| **Naming calls on Haiku 5.5** (`claude-haiku-5-5`), reason-first JSON, usage into `MultiModelUsage`. | decision 17: every Haiku call of the subproject is 5.5 | platform § M3 decisions 17; task brief |
| **Trait-hood and novelty are the platform's CLIs**, not generator code: `traithood_filter.py --run ipip/<R> --pipeline split`, then `novelty_score.py score --run ipip/<R>`.  The generator's own LLM calls are naming and the granularity readings only. | frozen interface; the census convention | platform "Interface as built" |
| **Labels already corpus names stay in the wave**; no selector drops them (M3 stage 0 covers them by name). | Roger, 2026-10-10 | [coding_plan_01_censuses.md](./coding_plan_01_censuses.md), last section |
| **No R1 per wave.**  This wave runs M1 and M3 only; the grouping run happens once at the end over every generator's batches. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| **Everything here runs live**: every stage estimate is well under $20 (§ 7 arithmetic; whole workstream ≈ $9). | batch-or-real-time rule | CLAUDE.md |
| **Prompt labels through the judge display form** (`prompt_label`), `label_form` recorded in every run record; a no-op for item texts and fresh candidate labels, applied all the same. | one rule everywhere | platform "Judge display form" |
| `Candidate.score` stays `None`: the platform reads `score` as human familiarity (interface resolution 4), which a purity figure is not.  Cluster quality travels in the cluster table. | avoid misreading by the Zipf-probe rule | my choice |

### Decisions of 2026-10-11 (QUESTIONS 46-52), which amend the table above

Roger answered the workstream's seven open entries on 2026-10-11; they were built the same day.  Where a row of
§ 1 disagrees with this list, this list wins.

| entry | what changed | where it is built |
|---|---|---|
| **52** | The item-to-scale keys come from **IPIP's own 21 per-inventory key pages** (source B, primary; all 21 are linked from the scale index), with Tedone's workbook as a **check and gap-filler** (source A).  Both fetches approved.  Only keys B corroborates are committed; an A-only key is a tagged gap-fill.  The ingest reports A against B both ways and asks Roger rather than resolving a difference above 2% of the shared links or 50 items of coverage | [ingest.py](../../assistant_axis/gapgen/generators/ipip/ingest.py) `parse_key_page`, `compare_keys`, `merge_keys`; [sources.py](../../assistant_axis/gapgen/generators/ipip/sources.py) |
| **46** | [items.jsonl](../../data/candidates/ipip/items.jsonl) is tracked, and every scale entry carries `key_source`.  The home page is fetched so that IPIP's public-domain sentence is in the manifest verbatim instead of quoted from this plan's prose | `build_items`; [download.py](../../assistant_axis/gapgen/generators/ipip/download.py) `_licence_record` |
| **48** | **`is_trait` is not a gate.**  Every named pole is submitted and M1's pinned kind call decides.  The naming prompts' narrow trait definition is rewritten (name the standing thing the statements indicate; a momentary feeling gets the predisposition behind it), and `is_trait` is replaced by a `kind` guess in M1's eight-way vocabulary.  The two prompts become pinned rubric files | [ipip_naming_blind.md](./rubrics/ipip_naming_blind.md), [ipip_naming_hinted.md](./rubrics/ipip_naming_hinted.md); `naming.py`, `submit.py` |
| **49** | The HEX assertion stays permanently, as a scrape-completeness check, beside a new check that all 21 key pages were read and each yielded rows; the pages are decoded explicitly (a single-byte Windows encoding, never UTF-8) | `check_hex`, `check_key_pages`, `decode_page` |
| **50** | The granularity decision takes **two signals, by cluster-size band**: each pole against the nearest pole of another cluster, read by name and gloss with the overlap call; and clusters printed in full, spanning the size range.  No absolute bar; the finer cut wins a tie.  The nearest-*corpus*-trait column stays separate (novelty, not size) | [granularity.py](../../assistant_axis/gapgen/generators/ipip/granularity.py) `nearest_pair_calls`, `spanning_clusters`, `readout`; `cluster.nearest_other_poles` |
| **47, 51** | As built: the blind label is the submitted surface, `score` stays `None` | `submit.py` |

## 2. Out of scope

- HEXACO-PI-R, openpsychometrics.org, SAPA/SPI, MFQ-2, PVQ-RR (plan 07 § 2: too small, unverified or permission-bound).
- Variant B (scale-first).  Variant C (residue-first) survives only as a report column: each cluster's mean item cosine to its nearest corpus trait, an ordering, not a filter.
- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [seed_queue.json](../../data/seed_queue.json); promotion (`gap_registry.py promote`) and review (R1/R2) are not this workstream's.
- Anything the platform owns: the M1 rubrics, the M3 rules and cut-offs, [metric_config.json](../../data/candidates/metric_config.json), the pinned [overlap_concept.md](./rubrics/overlap_concept.md) text.
- The recovery harness run (`recovery_test.py`, ~$5 per seed) — offered to Roger at the gate, not run by default; the free `covered_by` inversion (§ 7 `report`) is the brief's recovery readout.
- Plan 13's estimators; the Message Batches API (volumes here are hundreds of calls).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md) (usage.json on every batched call site; `json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name`; US English; judge display form),
[`.claude/rules/trait-pairs.md`](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are; the description form the glosses copy),
[`.claude/rules/judging.md`](../../.claude/rules/judging.md) (reason before verdict; `warn_if_low_parse_rate`; parse rate < 99% is a bug),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks).  No PNGs are produced, so the plotting rule is not needed.

**File-access boundary** (carried into every Opus task prompt, as [PLAN_FORMAT.md](./PLAN_FORMAT.md) requires): read and write only under `/Users/roger/Documents/GitHub/assistant-axis/` plus the agent's own scratchpad; never list, read or stat anything else, including `~/.cache`, even to check whether a model is downloaded — state the need and ask.  The one download this plan makes goes to `data/external/ipip/` inside the repo, after Roger's go (§ 9 task 2).

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate` (with `gloss_hint` and `partner_hint`), `start_run`, `submit_candidates`, `SubmitReport`, `RunContext` ([registry.py](../../assistant_axis/gapgen/registry.py), [runs.py](../../assistant_axis/gapgen/runs.py)).
- [embed.py](../../assistant_axis/gapgen/embed.py): `make_embedder`, `OpenAIEmbedder`, `LocalEmbedder` (gemma), `EmbeddingCache` (npz under `data/candidates/cache/embeddings/`, gitignored), `embed_texts(embedder, texts, *, cache, usage)`, `check_canary`.
- [llm.py](../../assistant_axis/gapgen/llm.py): `call_anthropic_json` (retries, cached system block, usage), `accepts_temperature`, `request_params`; [cost.py](../../assistant_axis/gapgen/cost.py): `estimate_calls_usd`, `confirm_or_abort`, `HARD_LINE_USD`.
- [overlap_test.py](../../assistant_axis/gapgen/overlap_test.py) for the granularity readings: `load_rubrics` (rubric A pinned), `PairCall`, `payload_single` / `render_single` / `call_params` (single form), `OverlapRunner` — its `corpus` argument is any mapping of id → `{label, description}`, so item pairs feed it without new call machinery.
- [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py): `prompt_label`, `DEFAULT_LABEL_FORM`; [judge_pricing.py](../../assistant_axis/judge_pricing.py): `MultiModelUsage` (Haiku 5.5 rates are in the table); [judge.py](../../assistant_axis/judge.py): `warn_if_low_parse_rate`.
- [entity_id.py](../../assistant_axis/entity_id.py): `normalize_to_file_name`; [atomic_io.py](../../assistant_axis/atomic_io.py): `atomic_write_text`, `write_jsonl`; [provenance.py](../../assistant_axis/provenance.py) + [plot_metadata.py](../../assistant_axis/plot_metadata.py): `current_file_input`, `json_metadata`.
- Censuses, as precedent only: the download-manifest pattern and `run_submit` shape in [generators/censuses/](../../assistant_axis/gapgen/generators/censuses/); the frozen `load_census_table` for the census-overlap diagnostic.  The measured platform rates are copied constants (M1 $0.0072/word, M3 $0.011/passed word at 88% pass; source comment: `overnight_readout_2026-10-08.md` § 6) — the census names are not frozen.
- `sklearn` 1.8 (`AgglomerativeClustering`, `cluster.HDBSCAN`, `normalized_mutual_info_score`, `adjusted_rand_score`), `umap-learn`, `sentence-transformers`: already in [pyproject.toml](../../pyproject.toml).  **`pandas` is not installed**; the scrape uses BeautifulSoup (`bs4` imports today as a transitive dependency — add `beautifulsoup4` to `pyproject.toml` explicitly, then `uv lock`).
- Test style: [test_gapgen_censuses_submit.py](../../assistant_axis/tests/test_gapgen_censuses_submit.py) (tmp registry, fake clients, hash embedder).

## 5. File layout

```
assistant_axis/gapgen/generators/ipip/
  __init__.py    GENERATOR = "ipip"; IPIP_DIR = DATA_CANDIDATES / "ipip"; ITEMS_PATH; EXTERNAL_DIR = DATA_EXTERNAL / "ipip"
                 clusters_path(granularity) -> IPIP_DIR / f"clusters_g{granularity}.jsonl"
  sources.py     Source(key, filename, url, dest, optional); SOURCES: AlphabeticalItemList.htm,
                 ItemAssignmentTable.htm, newIndexofScaleLabels.htm (+ newHEXACO_PI_key.htm, optional fallback);
                 LICENCE_QUOTE (the home page's public-domain sentence, recorded verbatim)
  download.py    fetch_all(*, dest_root, only, force, fetcher, dry_run) -> manifest  (IPIP publishes no hashes:
                 sha256/size of the received bytes recorded; write/load manifest)
  ingest.py      parse_item_list(html) -> [(code, text)]; parse_assignment_table(html) -> [(code, inventory, construct, key)]
                 parse_scale_index(html) -> [ConstructRow]; build_items(...) -> list[ItemRow]; write/load items.jsonl
  cluster.py     item_embed_text(text) -> "I " + text; embed_items(items, *, arm, cache, usage) -> np.ndarray
                 agglo_clusters(E, *, target_n, tol=0.1) -> list[RawCluster]   (average linkage, cosine;
                 distance threshold found by bisection until the count of clusters with >= 2 items is within tol of target)
                 consensus(a, b, *, min_jaccard=0.5) -> (kept, loose)   (greedy best-match Jaccard between embedders)
                 since 2026-10-12 (gate audit 4): consensus(a, b, *, rule="r2", min_jaccard) under CONSENSUS_RULES; DEFAULT_CONSENSUS "r2"
                 keeps a 3+ cluster and a pair the second embedder co-clusters (R2_MIN_SIZE 3), DEFAULT_SIZE_CEILING 30 at the coarser cuts,
                 DEFAULT_RECUT_TARGETS (350, 600); build_cluster_table(..., rule, size_ceiling, recut_targets, carry_from); TABLE_SCHEMA_VERSION 2;
                 CLI --consensus {r2,jaccard} --size-ceiling --recut-targets
                 split_poles(cluster, items) -> list[Pole]   (key signs: '-' items of a scale whose '+' items share
                 the cluster mark it bipolar; each pole is a naming unit)
                 purity_metrics(clusters, items) -> dict (NMI, ARI, majority-construct purity); hdbscan_check(E, seed) (report-only)
                 nearest_corpus(clusters, *, corpus_texts, cache) -> dict   (variant-C ordering column)
  naming.py      NAMING_PROMPT (blind), HINTED_PROMPT; build_user(pole) / build_hinted_user(pole, constructs)
                 parse_naming(text) -> Naming | None; name_poles(poles, *, client, model, usage, hinted) (async, call_anthropic_json)
  granularity.py sample_pairs(clusters, *, per_cluster=3, cross_pole=1, seed) -> list[PairCall] + item "corpus" mapping
                 item_entry(item) -> {"label": "I <text>", "description": "This means being someone of whom
                 \"I <text>\" is generally true, as a tendency rather than an episode."}
                 readout(records) -> per-granularity distribution (share at each of 0-4 and "opposite", share >= 3)
  submit.py      to_candidates(poles, run_id) -> list[Candidate]; M1_USD_PER_WORD etc. (copied, sourced);
                 run_submit(granularity, run_id, *, pilot poles or all, budget_usd, confirm_expensive, dry_run)
  evaluate.py    census_overlap(poles) (frozen load_census_table); known_analogues(constructs, corpus_stems);
                 recovery_from_covers(registry_rows) (invert covered_by); naming_agreement(poles) (blind vs hinted,
                 bipolar antonym match); build evaluation.json
  report.py      render_report(evaluation) -> report.md; roger_sample(poles, n=40, seed=0) -> roger_sample.md
data_analysis/gap_generation/ipip_generator.py   download | ingest | cluster | name | granularity | submit | report
data/external/ipip/                              GITIGNORED: the HTML pages + DOWNLOAD_MANIFEST.json
data/candidates/ipip/                            tracked: items.jsonl, sources_manifest.json, clusters_g350.jsonl,
                                                 clusters_g150.jsonl, granularity/<g>/{responses.jsonl, usage.json},
                                                 granularity_readout.{json,md}, naming_usage.json (cumulative)
data/candidates/runs/ipip/<run_id>/              candidates.jsonl, keys.txt, run.json, usage.json, evaluation.json,
                                                 report.md, roger_sample.md
assistant_axis/tests/test_gapgen_ipip_{sources,download,ingest,cluster,naming,granularity,submit,evaluate}.py
assistant_axis/tests/fixtures/ipip/              small fake HTML pages, fake items, fake registry rows
data_analysis/tests/test_gap_generation_ipip_cli.py
```

## 6. Data schemas

None of the files under [data/candidates/ipip/](../../data/candidates/) exists yet: every path in this
section and in § 7 is where the run will write it.

**Item row** ([items.jsonl](../../data/candidates/ipip/items.jsonl), one per Eugene-Springfield code, deterministic order by code; an item on several scales keeps them all):

```json
{"schema_version": 1, "ipip_id": "H1131", "text": "Get chores done right away.",
 "scales": [{"inventory": "NEO", "construct": "Orderliness", "key": "+"},
            {"inventory": "HEX", "construct": "Diligence", "key": "+"}]}
```

**Cluster row** ([clusters_g350.jsonl](../../data/candidates/ipip/clusters_g350.jsonl), written by task 4, not yet on disk; one per consensus cluster; `poles` has one entry, or two when key signs split it):

```json
{"schema_version": 1, "granularity": 350, "cluster_id": 17, "embedder": "openai", "jaccard_vs_gemma": 0.78,
 "items": ["H1131", "H1287", "..."], "constructs": {"NEO:Orderliness": 4, "HEX:Diligence": 3}, "purity": 0.71,
 "bipolar": true, "nearest_corpus": {"stem": "diligent", "mean_cos": 0.41},
 "poles": [{"pole": "a", "items": ["H1131", "..."],
   "blind": {"label": "chore-prompt", "gloss": "This means doing routine tasks as soon as they come up, without putting them off.",
             "antonym_label": "last-minute", "is_trait": true, "ambiguity_flag": false, "single_word_exists": false},
   "hinted": {"label": "diligent", "gloss": "..."}, "labels_disagree": true},
  {"pole": "b", "...": "..."}]}
```

**Naming call output** (one pole per call, blind form; the hinted form adds the construct names to the user turn and is stored beside it, never merged):

```json
{"reason": "<one short sentence>", "label": "<1-4 lowercase words>",
 "gloss": "This means ... (<= 25 words)", "antonym_label": "<word or null>", "antonym_gloss": "<or null>",
 "is_trait": true, "ambiguity_flag": false, "single_word_exists": false}
```

Rubric rules: reason first; `is_trait` means a disposition a speaking persona can enact — **symptom-like dispositions count** (the corpus has [adhd](../../data/traits/instructions/adhd.json) and [ocd](../../data/traits/instructions/ocd.json)); moods, abilities, interests and life circumstances do not; examples are near-duplicates of corpus terms, never corpus labels or queue entries (the hygiene rule); temperature 0 where the model accepts it (`llm.accepts_temperature`).

**Candidate emitted** (`to_candidates`; blind label as surface, provisionally): `Candidate(surface="chore-prompt", generator="ipip", run_id="2026-10-14a", rank=17, score=None, gloss_hint="This means doing routine tasks as soon as they come up, without putting them off.", sense_id=1, source_ref="ipip:g350:c017a", partner_hint="last-minute")` — `partner_hint` only for the other pole of a bipolar cluster (pole pairs from scale keys), so `promote` can pair them and M3's pair machinery sees a declared partner; `rank` is the cluster id (clusters ordered by size).

**Granularity readout row** ([granularity_readout.json](../../data/candidates/ipip/granularity_readout.json), written by task 6, not yet on disk; in a `json_metadata` envelope; numbers illustrative):

```json
{"granularity": 350, "n_clusters": 238, "n_pairs_read": 706, "within": {"0": 0.03, "1": 0.14, "2": 0.27, "3": 0.38, "4": 0.16, "opposite": 0.02, "share_3_4": 0.54},
 "cross_pole": {"n": 61, "opposite": 0.85}, "model": "claude-sonnet-5-5", "rubric": "A", "label_form": "judge-display-v1", "cost_usd": 0.92}
```

**Evaluation** (`evaluation.json` per run): cluster counts and quality (NMI/ARI/purity per embedder, mutual Jaccard, loose-pile size), naming (parse rate, blind/hinted disagreement rate, bipolar antonym agreement — target > 80%, is_trait fractions), census overlap (share of blind labels that are census words), M1 verdict/tag fractions, M3 covered/new/grey + pair completions, the `covered_by` inversion recovery (share of known-analogue corpus stems hit — the stems, among the corpus's 932 trait files counted 2026-10-10, whose `normalize_to_file_name` matches an IPIP construct label; target > 90%, report-and-decide), per-model cost, `useful_per_dollar` (rows decided `new` or pair-completion per dollar of summed usage.json).

## 7. CLI

`data_analysis/gap_generation/ipip_generator.py`; common flags `--data-dir`, `--registry`, `--dry-run`, `--budget-usd`, `--confirm-expensive`.  Every paid command prints its estimate (`n_calls × (in, out) tokens at model rates = $X`), refuses an estimate over the budget without the flag and over $20 outright (`confirm_or_abort`), writes `usage.json`, and runs `warn_if_low_parse_rate`.

- `download [--only KEY] [--force] [--dry-run]`: fetches the three pages (and `newHEXACO_PI_key.htm` only if the HEX assertion below fails); streams to `.part`, records sha256/size/date/URL and the licence quote in `DOWNLOAD_MANIFEST.json` and tracked [sources_manifest.json](../../data/candidates/ipip/sources_manifest.json) (written by this command, not yet on disk); idempotent.  **Needs Roger's go first** (the boundary rule): ~4 pages from ipip.ori.org, under ~2 MB, into `data/external/ipip/`.  Free.
- `ingest [--dry-run]`: rebuilds [items.jsonl](../../data/candidates/ipip/items.jsonl) deterministically (snapshot to `.bak.<UTC>` on change); prints counts per inventory and **asserts ≥ 20 constructs keyed `HEX` with ~240 items** (the verified IPIP-HEXACO block of plan 07 § 2); on failure, QUESTIONS entry and the fallback page.  Free.
- `cluster [--arms openai gemma] [--targets 350 150] [--seed 0]`: embeds all items both arms ("I " prefix; ~40k tokens ≈ **$0.006** at $0.13/MTok, gemma free), writes both cluster tables with consensus, poles, purity metrics, the HDBSCAN cross-check and the variant-C column.  Deterministic given the cache.
- `name --granularity {350,150} [--clusters N | --all] [--hinted] [--seed 0]`: blind call per pole, hinted call beside it; merges usage into [naming_usage.json](../../data/candidates/ipip/naming_usage.json) (cumulative, the regeneration-usage precedent; not yet on disk).  Cost: per call ≈ 700 in / 250 out on Haiku 5.5 ($0.10/$0.50 per MTok) ≈ **$0.0002**; the pilot's 40 clusters × 2 granularities ≈ 200 calls ≈ $0.04; full naming of the chosen granularity (~420 poles × 2 forms) ≈ **$0.17**.
- `granularity [--per-cluster 3] [--cross-pole 1] [--seed 0]`: samples within-pole item pairs per consensus cluster (uniform over the pole's pairs) plus one cross-pole pair per bipolar cluster (expected "opposite"), builds an item "corpus" mapping via `item_entry`, and runs the pinned rubric A single form on Sonnet 5.5 through `OverlapRunner`; writes `granularity/<g>/responses.jsonl` and the readout.  **Cost arithmetic** from the measured one-pair-per-call rates ([coding_plan_platform.md](./coding_plan_platform.md), M3 decision 10: Sonnet $0.0012/pair, cache on): ≤ (350 + 150) clusters × 3 pairs + ~100 cross-pole ≈ 1,600 calls ≈ **$1.92**, an upper bound since item texts are shorter than w20 descriptions.  Under $20 → live.  Caveat stated in the readout: single items are narrower than traits, so absolute levels may sit low; the decision statistic is the comparison between granularities plus Roger's read of the sampled clusters.
- `submit --granularity G --run-id R [--poles-file F | --all-trait-poles] [--budget-usd 8]`: builds one `Candidate` per pole with `is_trait` true (non-trait poles are counted in the report); prints the downstream estimate `n × $0.0072 (M1) + n × 0.88 × $0.011 (M3)` and gates it; `start_run("ipip", R, args={granularity, n, estimate, sources_manifest, clusters_sha256, label_choice})`, writes `candidates.jsonl` before `submit_candidates`, then `keys.txt`, and prints the follow-up commands: `traithood_filter.py --batch-id R_ipip --run ipip/R --pipeline split --budget-usd 5` · `novelty_score.py score --batch-id R_ipip --run ipip/R --budget-usd 8`.  Submitting is free; the full wave (~300 poles) ≈ **$2.2 M1 + $2.9 M3 ≈ $5.1**, live.
- `report --run-id R`: assembles `evaluation.json` from the registry, the filter and novelty batch dirs, the cluster tables and the granularity readout; sums the `usage.json` files per model; renders `report.md` and `roger_sample.md` (40 seeded poles: blind label, hinted label, gloss, items, M1 verdict, M3 decision and `covered_by`).  Free.

Interface requests to the platform: **none** — the as-built registry API, `--run` selectors and pinned rubrics cover everything.

## 8. Acceptance tests, written first

No test calls an API, downloads or loads a model (fake fetcher, fake Anthropic client, `HashEmbedder`, fixture HTML).

- `test_gapgen_ipip_sources.py`: every source has url, dest under `data/external/ipip/`, the licence quote present; the HEXACO key page is marked optional.
- `test_gapgen_ipip_download.py`: fake fetcher → files + manifest with sha256 of the received bytes; idempotent skip; `--force` refetches; dry-run writes nothing.
- `test_gapgen_ipip_ingest.py` (fixture pages with ~12 items, one on two scales, one `-` keyed, one HEX construct): counts; the multi-scale item keeps both; key signs parsed; rerun byte-identical; the HEX assertion fires on a fixture without HEX.
- `test_gapgen_ipip_cluster.py` (synthetic embeddings with planted clusters): bisection hits the target count ± 10%; consensus keeps a planted cluster both arms share and routes a one-arm cluster to `loose`; `split_poles` splits exactly where `-` items of a `+`-sharing scale sit; NMI/ARI/purity = 1.0 on planted labels; seeded determinism; no cluster field depends on the corpus (the variant-C column is computed but mutation-tested to change no membership).
- `test_gapgen_ipip_naming.py`: the word "reason" precedes "label" in prompt and example; no rubric example is a corpus or queue stem; parser rejects fences/missing keys and counts them; symptom wording present ("symptom-like dispositions count"), moods/abilities excluded; usage charged on a fake client; labels normalized via `normalize_to_file_name` round-trip.
- `test_gapgen_ipip_granularity.py`: sampling is seeded, within-pole only, cross-pole flagged separately; `item_entry` shape; readout shares sum to 1 and `share_3_4` is right on fake records; `label_form` recorded.
- `test_gapgen_ipip_submit.py` (tmp registry, real frozen API): candidates carry gloss_hint, `partner_hint` reciprocal across a bipolar cluster's poles, `score is None`, `source_ref` format; `candidates.jsonl` written before submit; resubmit is a no-op; **cost guard**: 5,000 fake poles → over $20 → refused even with the flag; 1,000 → over the default budget, refused without `--confirm-expensive`, accepted with it; dry-run leaves the registry byte-identical.
- `test_gapgen_ipip_evaluate.py`: census overlap via a fake `load_census_table`; known-analogue matching normalizes construct labels; `covered_by` inversion on fake registry rows; bipolar antonym agreement; the package imports neither `anthropic` nor `openai` at import time.
- `test_gap_generation_ipip_cli.py`: every subcommand's `--dry-run` exits 0 and writes nothing; `report` renders the fixture evaluation with all columns.
- Acceptance on recorded outputs (skips when absent): ingest ≥ 3,000 items and ≥ 20 HEX constructs; naming parse rate ≥ 99%; bipolar antonym agreement reported (target > 80%); known-analogue recovery reported (target > 90%); `usage.json` present in every run dir and granularity dir.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_ipip_*.py data_analysis/tests/test_gap_generation_ipip_cli.py -q
uv run pytest -q
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Works in its own git worktree (first step `git merge --ff-only anthropic-vllm-uv`), `.env` copied from the main checkout, `data/external/` symlinked, as the census build did.  Each task ends with its test green and the § 8 command block.

1. Skeleton: `generators/ipip/__init__.py`, `sources.py`; add `beautifulsoup4` to `pyproject.toml`, `uv lock` — **the dependency is approved (Roger, 2026-10-10)**.  Test: sources.
2. `download.py` + CLI.  Test: download.  **The ipip.ori.org fetch is approved (Roger, 2026-10-10: the three pages, under ~2 MB, the HEXACO key page only on the fallback)** — no further ask needed; run it and paste the manifest lines into the task report.
3. `ingest.py` + CLI.  Test: ingest.  Run it; the real counts (items, inventories, HEX constructs) replace the ~3,320 estimate; QUESTIONS information entry.
4. `cluster.py` + CLI (both arms, both targets).  Test: cluster.  Run it ($0.01); record counts, purity, Jaccard, loose-pile size.
5. `naming.py` + CLI.  Test: naming.
6. `granularity.py` + CLI.  Test: granularity.
7. `submit.py`, `evaluate.py`, `report.py` + CLIs.  Test: submit, evaluate, CLI.
8. **Pilot** (§ 10).  Roger's gate.
9. Full run on the chosen granularity: `name --all`, `submit`, M1, M3, `report`; acceptance tests on the recorded outputs.
10. Acceptance report (§ 11); propose the `data/README.md` paragraph for `external/ipip/` and `candidates/ipip/` in the report text (do not edit that file).

## 10. Pilot

Everything through the granularity decision, before any full naming or submission: cluster both granularities (task 4); `name` 40 seeded clusters per granularity, blind and hinted (≈ $0.04); `granularity` over all consensus clusters (≈ $1.9); then `submit --granularity 350 --run-id <date>-pilot` on the 40 named clusters' trait poles (~50 candidates) with live M1 and M3 (≈ $0.9), to measure this generator's real pass rates and yield per dollar.  Pilot total ≈ **$3**; every stage live.

Readout for Roger: the granularity distributions side by side (share at 3-4, Roger's criterion) with 10 sampled clusters from each to read; `roger_sample.md` with blind beside hinted labels and their disagreement rate; bipolar antonym agreement; is_trait fractions; census-word share of blind labels; M1/M3 fractions and measured per-pole cost; projected full-run cost.

Roger decides: (a) granularity (~350 or ~150); (b) **primary label: blind (recommended, for independence from the taxonomy vocabulary) or hinted** — the full run submits the chosen form; (c) the is_trait gate at submit (provisional: submit trait poles only, report the rest); (d) the loose pile — hold (provisional) or submit; (e) whether to run the recovery harness (`recovery_test.py --generator ipip --run-id <R>`, ≈ $5/seed) beside the free `covered_by` inversion; (f) the full-run go (projected ≈ $5-6).

## 11. Report at the end

One page at [acceptance_07_ipip.md](./acceptance_07_ipip.md) (not written yet): what was built against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the download manifest lines and licence quote; ingest counts and the HEX assertion's result; cluster quality per embedder; the granularity readout and Roger's choice; blind/hinted statistics and his primary-label choice; M1/M3 fractions, pair completions, the known-analogue recovery with every miss listed and read (pool blind-spot or filter slip); per-model cost from the summed `usage.json` files against the estimates; `useful_per_dollar`; open QUESTIONS entries.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable, then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [07] question. Assumption proceeded under: ... Status: open`), proceeding under the assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start: (1) [items.jsonl](../../data/candidates/ipip/items.jsonl) is tracked; (2) the blind label is the provisional primary and the pilot's ~50 probe keys are superseded if Roger flips to hinted (small, accepted); (3) only `is_trait` poles are submitted, the rest reported; (4) if the HEX ingest assertion fails, `newHEXACO_PI_key.htm` is fetched under the same download approval; (5) the granularity readings are read comparatively, not against an absolute bar; (6) `Candidate.score` stays `None`.  Anything that would edit a trait file or the queue, spend over a command's budget, or change a frozen signature stops and asks.
