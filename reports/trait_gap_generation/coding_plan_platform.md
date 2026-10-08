# Coding plan: trait-gap generation platform (workstreams 14, 15, 10)

Written 2026-09-23 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape.  Three
milestones in this order: **M1** trait-hood filter and candidate registry (plan 14), **M2**
metric calibration (plan 15), **M3** novelty by embedding (plan 10).  The "Frozen interface"
section at the end is the contract the generator workstreams (1, 2, 8, ...) and the testing
workstream (13) are written against; nothing in it changes after M3 acceptance without a
plan revision.  Roger's review comments go into this file.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Library code in a new package `assistant_axis/gapgen/`; CLIs in `data_analysis/gap_generation/`; external data under gitignored `data/external/`; outputs under `data/candidates/`. | agreed layout | PLAN_FORMAT §5, task brief |
| `wordfreq` and `wn` are approved dependency additions; Open English WordNet 2024 lives in `data/external/wn/`. | approved | task brief; plan 02 §2 |
| Zipf is a **feature, not a gate**: hard reject only below Zipf 2.0 (keeps 95% of existing labels); 2.0-2.5 gets a Haiku definition probe; the 32B probe only at adoption. | a 3.0 floor would reject a third of our own labels (median 3.37, quartile 2.82, 5th pct 1.9) | plan 14 §11.3 |
| Registry is append-only JSONL keyed by `(stem, sense_id)`. | Roger: "SG" | plan 14 §10-11 |
| Physical candidates go to a holding list for the physical-attribute section of TRAITS_TO_ADD, never promoted; role candidates (person or thing) go to a roles holding list with no role-hood pass. | plan 14 §11.1, §11.4 | plan 14 |
| State words are in scope as dispositions; the filter tags `state` and the gloss says "a general tendency to ...". | Spielberger state/trait model | plan 14 §11.5 |
| Promotion into `data/seed_queue.json` only by an explicit command; nothing here edits existing trait files. | keeps the seeding pipeline undisturbed | README process §6 |
| Gloss for an existing trait is its **whole description**; candidate glosses are written in the same form ("This means ...") and length band (18-43 words). | the description is the definition; matched length keeps distances comparable | plan 10 addendum 2; plan 15 §3.1 |
| Fixed corpus mean for centering (never the pooled corpus-plus-candidate mean). | persona-pipeline convention | plan 15 §11 |
| K per space by the 95%-variance rule, sensitivity reported at K = 10, 20, 40. | plan 15 §11 | plan 15 |
| Contrast-clause ablation is a research question on the embedding model, decided per model by criteria (a)-(j); descriptions are not edited; the chosen policy applies to candidate glosses too. | plan 15 §3.5 | plan 15 |
| Thresholds come from the LOO nearest-neighbour distribution and the labelled anchors, not from the corpus minimum; the low tail becomes the drop-or-merge list. | the corpus contains uncaught near-duplicates and deliberate ones | plan 15 §3.7-3.8 |
| Two embedding models: OpenAI `text-embedding-3-large` plus one local model. | reproducibility beside the API model | plan 10 resolution 3 |
| Local model: **`Qwen/Qwen3-Embedding-0.6B`** (Apache-2.0, 1024-d). | same family as the generator (a label it embeds well is a label the 32B knows); explicit instruction mode lets both sides be embedded identically; MTEB-stronger and newer than bge-large; ~1.2 GB bf16 runs on MPS.  `BAAI/bge-large-en-v1.5` stays available behind `--local-model` if the MPS path misbehaves (CLS pooling is simpler); switching is a config change, not an interface change. | my choice, per the brief |
| Deliberate near-duplicates (a standard's pole beside a plain trait) are `covered` with a `deliberate_duplicate` flag. | plan 10 resolution 1 | plan 10 |
| Target recall 0.95 on `covered`; ~15% of candidates may go to the LLM (~$2 per 10k). | review time is the scarce resource | plan 10 resolution 2 |
| Alignment-region survivors are shown first, as a separate section of the review list. | plan 10 resolution 4 | plan 10 |
| Every batched LLM or embedding call site records `usage.json` via `MultiModelUsage`; every CLI has a cost estimate and a hard cap; anything over $20 needs Roger's explicit go. | CLAUDE.md hard rules | CLAUDE.md |
| Judge prompts reason before verdict; parse rate < 99% is a bug. | judging rule | `.claude/rules/judging.md` |
| The trait-hood rubric also returns a `region` (the nine regions of plan 13 §3.2), so the validation run over the 414 existing labels yields `corpus_regions.json` for free; that is what "alignment survivors first" keys on. | avoids a separate $0.50 labelling pass and gives 13 its region labels | my addition; report if Roger prefers description-based regions |
| Classifier temperature 0.0 (not the project's judge default of 1.0). | the stability test wants ≥ 90% verdict agreement on rerun | my choice |

## 2. Out of scope

- Any generator (plans 1-9): this plan produces no candidates except the validation and pilot sets described below.
- Plan 11's ensemble signals and plan 12's persona-space regression (M2 loads persona vectors only for criteria (c) and (h)).
- Plan 13's capture-recapture estimators and dashboard; only the recovery-test **hook** is built here.
- Roger's 200-item hand-labelled candidate set (plan 10 §6): real candidates do not exist until a generator runs; M3's pilot gives him a 40-row sample instead and the 200-set is a follow-on once workstreams 1-2 report.
- Editing any file under `data/traits/instructions/` or `data/roles/instructions/`, `TRAITS_TO_ADD.md`, `ROLES_TO_ADD.md`; writing to `data/seed_queue.json` except through `gap_registry.py promote`.
- The Anthropic Message Batches API (volumes here are hundreds of calls; live calls with caching are simpler).
- Qwen3-32B definition probes on the RunPod.
- A role-hood rubric.

## 3. Rule files to Read first

Open these with the **Read tool** before touching code (shell reads do not load them):
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md) (usage.json on every batched call site; `json_metadata` / `png_metadata` envelopes; UTC timestamps),
[`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name`, US English, display form only at display sites),
[`.claude/rules/trait-pairs.md`](../../.claude/rules/trait-pairs.md) (what a trait, a pair, an arrangement and the seed queue are; description-writing rules the gloss form copies),
[`.claude/rules/judging.md`](../../.claude/rules/judging.md) (reason-before-score, `warn_if_low_parse_rate`, rubric version constants),
[`.claude/rules/plotting.md`](../../.claude/rules/plotting.md) (M2 writes PNGs: `png_metadata`, visual verification),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks).  The judge-cost rule's budget-cap formula (`1.5 × expected + $10` for first-of-kind work) is the model for the caps below, scaled down.

## 4. Existing code to reuse

- [`data_analysis/seed_entities.py`](../../data_analysis/seed_entities.py): `load_queue`, `save_queue`, `corpus_stems`, `build_registry` (existing *and queued* stems: the collision set `promote` checks), `instructions_dir`, the queue entry shape and status lifecycle.
- [`assistant_axis/entity_id.py`](../../assistant_axis/entity_id.py): `normalize_to_file_name`, `display_form_name`, `corpus_display_name`, `default_data_dir`.
- [`assistant_axis/atomic_io.py`](../../assistant_axis/atomic_io.py): `atomic_write_text`, `write_jsonl`, `read_jsonl_with_retry` (registry I/O).
- [`assistant_axis/arrangements.py`](../../assistant_axis/arrangements.py): `load_corpus_arrangements`, `reciprocal_pairs` (the clean-pair antonym set), `parse_field`.
- [`assistant_axis/judge_pricing.py`](../../assistant_axis/judge_pricing.py): `MultiModelUsage`, `extract_usage_anthropic`, `extract_usage_openai`, `price_for_model`, `BudgetExceededError`; **add** rates for `text-embedding-3-large` (0.13, 0), `text-embedding-3-small` (0.02, 0), `qwen3-embedding` (0, 0), `bge-large` (0, 0) so embedding calls are counted.
- [`assistant_axis/judge.py`](../../assistant_axis/judge.py): `RateLimiter`, `extract_json_blob`, `_repair_json_blob`, `warn_if_low_parse_rate`.  `call_anthropic_judge_single` has no `system=` parameter, so `gapgen/llm.py` adds a sibling that takes a cached system block (pattern: [`data_analysis/generate_antonyms.py`](../../data_analysis/generate_antonyms.py) lines 116-140).
- [`assistant_axis/provenance.py`](../../assistant_axis/provenance.py): `InputSpec`, `current_file_input`, `current_files_input`; [`assistant_axis/plot_metadata.py`](../../assistant_axis/plot_metadata.py): `json_metadata`, `png_metadata`, `suptitle_with_specs`.
- [`results_analysis/canonical_angles/data.py`](../../results_analysis/canonical_angles/data.py): `load_vector`, `compose_slots`, `build_goal_nogoal_subspaces`; [`whitening.py`](../../results_analysis/canonical_angles/whitening.py): `fit_shear`, `DEFAULT_SOFT_SHEAR_L` (M2 criteria (c), (h)).  The 8-slot dataset (`runpod_workspace/qwen/qwen-3-32b Roger 8slot/`, 305 trait vectors) has no `derived/` dir: if `build_goal_nogoal_subspaces` cannot build, use corpus-mean-centred raw vectors and say so in the report.
- [`data/seed_queue.json`](../../data/seed_queue.json) (statuses: 52 `exists`, 13 `superseded`, 95 `not_adopted` with `decision` text), [`data/traits/trait_antonyms_v4.json`](../../data/traits/trait_antonyms_v4.json) (`{stem: {negative_label, antonym_score, reasoning}}`), [`reports/seeding_log_2026-09.md`](../seeding_log_2026-09.md) § "Pairing review list" (22 cases), [`contrast_clauses_census.md`](./contrast_clauses_census.md) (10 N / 68 P / 29 S stems, parseable from the `**stem**:` bullets).
- Test style: [`data_analysis/tests/test_seed_entities.py`](../../data_analysis/tests/test_seed_entities.py) (tmp_path fixtures, fake queue).

## 5. File layout

```
assistant_axis/gapgen/
  __init__.py      re-exports the frozen interface (§ Frozen interface)
  paths.py         DATA_CANDIDATES, DATA_EXTERNAL, REGISTRY_PATH, METRIC_CONFIG_PATH, run_dir(generator, run_id),
                   hf_cache_dir() -> data/external/hf, wn_data_dir() -> data/external/wn  (every download stays in-tree)
  normalize.py     normalize_candidate(surface) -> Normalized(stem, label, surface_lc, content_words)
                   REGION_VOCAB, TAG_VOCAB, VERDICTS
  registry.py      Registry (log-structured JSONL), Candidate, submit_candidates, new_record, merge_block, compact,
                   holding_list(kind), records_for_status(...)
  runs.py          start_run(generator, run_id, *, args) -> RunContext(.dir, .usage, .log(...), .finish())
  cost.py          GuardedUsage(MultiModelUsage), estimate_calls_usd(model, n_calls, in_tok, out_tok),
                   confirm_or_abort(estimate_usd, budget_usd, *, confirm_expensive, hard_line=20.0)
  llm.py           call_anthropic_json(client, *, system, user, model, max_tokens, temperature, usage, limiter,
                   cache_system=True) -> str | None   (retries (5,20,60,180) on transient errors; charges usage)
  freq.py          zipf_info(surface) -> FreqInfo(zipf_min, zipf_words, hard_reject, probe_band)
  wordnet.py       ensure_oewn(), sense_info(surface) -> WordNetInfo(n_senses, pos, found)
  filter_rubric.py TRAITHOOD_RUBRIC_VERSION = 1, SYSTEM_PROMPT, build_batch_prompt(items), parse_batch(text, ids),
                   derive_polysemy(verdict_row, n_senses), gloss_in_band(gloss), DEFINE_PROBE_PROMPT, parse_probe
  filter.py        run_traithood_filter(records, *, client, model, second_model, usage, limiter, batch_size=25,
                   second_opinion_frac=0.10, seed=0) -> list[FilterResult]; select_second_opinion(results)
  promote.py       queue_entry_from_record(rec, *, section) -> dict; promote(registry, queue, keys, *, dry_run) -> PromoteReport
  embed.py         Embedder protocol; OpenAIEmbedder; LocalEmbedder (Qwen3-Embedding-0.6B, MPS, last-token pooling;
                   bge CLS pooling); EmbeddingCache (npz + manifest under data/candidates/cache/embeddings/);
                   embed_texts(embedder, texts, *, cache, usage) -> np.ndarray (unit-normalised, row order preserved)
  representation.py trait_text(label, description, *, prefix="keep"|"strip", contrast="keep"|"strip", cuts) -> str
                   candidate_text(label, gloss, ...) -> str   (one function for both sides, by design)
  contrast.py      parse_census(path) -> {stem: "N"|"P"|"S"}, strip_contrast(text, *, override) -> (text, cut_span),
                   load_cuts(path), minimal_pairs(pairs) -> [("X rather than Y", "Y rather than X"), ...]
  labels.py        build_labelled_pairs(data_dir, queue, seeding_log, census) -> LabelledPairs
                   (antonym / duplicate / near_distinct / polysemy_reject / deliberate_duplicate / unrelated), load/save JSON,
                   group_folds(pairs, k=5)  (a pair's two members never straddle a fold)
  space.py         fit_space(E_corpus, variant) -> SpaceTransform(.apply(E)) for raw | centred | centred_pc1 | centred_pc3 | zca
                   k_for_variance(E_centred, 0.95) -> int; residual_fraction(x, basis_K) -> float
                   csls(sim, k=10) -> np.ndarray; loo_nearest(E) -> (idx, sim)
  persona.py       load_trait_vectors(data_dir, slot=6, layer=25, shear_L=3|None) -> (stems, M_centred)
                   loo_residual(M, K) -> np.ndarray; parse_bracket_scores(traits_to_add_md) -> {stem: float}
  calibrate.py     run_calibration(cfg) -> CalibrationResult; the tasks (a)(b)(c), hubness census, place_thresholds(...),
                   drop_or_merge_table(...), contrast_ablation(...) criteria (a)-(j), write_metric_config(...)
  novelty.py       MetricConfig, NoveltyIndex, NoveltyQuery, Neighbour, NoveltyResult, score_novelty, PolarityProbe
                   (train / to_json / from_json), decide(...), review_order(results, index, cfg) -> list[keys]
  adjudicate.py    ADJUDICATION_RUBRIC_VERSION = 1, build_prompt(candidate, neighbours), parse -> relation | None
  recovery.py      recovery_test(...) -> RecoveryReport (§ Frozen interface)

data_analysis/gap_generation/
  setup_external.py      download OEWN 2024 into data/external/wn, pre-fetch the local embedding model into data/external/hf
  gap_registry.py        submit | status | report | holding | compact | promote
  traithood_filter.py    run the filter over registry rows (or a validation file)
  calibrate_metric.py    the M2 experiment; writes data/candidates/metric_config.json and calibration/ outputs
  novelty_score.py       build-index | score | review-list
  recovery_test.py       the hook as a CLI (plan 13 will wrap it)

data/candidates/                      tracked unless noted
  registry.jsonl                      append-only log
  corpus_regions.json                 {stem: region} from the M1 validation run
  metric_config.json                  M2 output, read by M3
  calibration/labelled_pairs.json     hand-checked (seeded by labels.py, then edited by hand)
  calibration/contrast_cuts.json      the 107 mechanical cuts with hand overrides
  calibration/{loo_metrics.json, hubness.json, thresholds.json, contrast_ablation.json, drop_or_merge.md, *.png, usage.json}
  runs/<generator>/<run_id>/{candidates.jsonl, run.json, usage.json}
  filter/<batch_id>/{responses.jsonl, summary.json, usage.json}
  novelty/<batch_id>/{novelty.json, review_list.md, usage.json}
  cache/embeddings/<model_tag>.npz + manifest.json    GITIGNORED
data/external/                        GITIGNORED (wn/, hf/, wordlists/)
```

`.gitignore` gains `/data/external/` and `/data/candidates/cache/`.  `pyproject.toml` gains `wordfreq>=3.1` and `wn>=0.9` (then `uv lock`).  No file outside the repo tree is read or written: `LocalEmbedder` passes `cache_dir=hf_cache_dir()` and `wn.config.data_directory = wn_data_dir()`.

## 6. Data schemas

**Registry row** (one JSON line per write; the file is a log, the latest line per `key` is the record; `rev` increments):

```json
{"schema_version": 1, "key": "world_shaping#1", "stem": "world_shaping", "sense_id": 1, "surface": "world-shaping", "label": "world-shaping",
 "gloss": "This means being world-shaping: a general tendency to treat every task as a lever on how the world goes, ...", "entity_type": "trait",
 "sources": [{"generator": "wordnet_walk", "run_id": "2026-09-30a", "rank": 412, "score": 0.71, "source_ref": "oewn:02345678-a", "gloss_hint": null}],
 "freq": {"zipf_min": 3.4, "zipf_words": {"world": 5.6, "shaping": 3.4}, "hard_reject": false, "probe_band": false,
          "define_probe": null},
 "wordnet": {"found": true, "n_senses": 2, "pos": ["a"]},
 "filter": {"rubric_version": 1, "model": "claude-haiku-4-5-20251001", "batch_id": "2026-10-01_wordnet_walk_1",
            "reason": "A stable stance a speaker can enact; the everyday sense is the trait sense.",
            "verdict": "trait", "tags": [], "region": "alignment_ai_agent", "senses": ["having large effects on the world"],
            "trait_sense_rank": 1, "enactable_in_text": 2, "confidence": 0.85, "polysemy": false, "gloss_in_band": true,
            "second_opinion": null, "at": "2026-10-01T10:00:00+00:00"},
 "novelty": {"config_version": "2026-10-03", "batch_id": "2026-10-03_wordnet_walk_1",
             "signals": {"openai:text-embedding-3-large": {"local": 0.31, "directional": 0.62, "k": 31,
                            "nearest": [{"stem": "proactive", "sim": 0.71, "csls": 0.22, "p_antonym": 0.12, "relation": "related"}]},
                         "local:qwen3-embedding-0.6b": {"local": 0.36, "directional": 0.58, "k": 27, "nearest": [...]}},
             "agreement": "agree", "decision": "new", "flags": [], "nearest_existing": "proactive",
             "cluster_id": 17, "cluster_size": 1, "review_rank": 42,
             "adjudication": {"model": null, "relation": null, "note": null}},
 "holding": null, "matches_existing": null, "heldout_hit": null,
 "review": {"status": "unreviewed", "by": null, "at": null, "note": null},
 "seed_queue_stem": null, "rev": 3, "created_at": "2026-09-30T18:02:11+00:00", "updated_at": "2026-10-03T09:41:00+00:00"}
```

Vocabularies: `verdict` ∈ {trait, tagged, reject}; `tags` ⊆ {physical, state, transient_only, demographic, role_person, role_thing, evaluative_only, relational_only, not_a_word, too_rare}; `region` ∈ {communication_style, cognitive_epistemic, moral_stance, social_interpersonal, emotional_temperament, alignment_ai_agent, transient_state, identity_demographic, physical}; `holding` ∈ {null, physical, roles}; `decision` ∈ {covered, new, grey}; `flags` ⊆ {ambiguous_label, pair_completion, deliberate_duplicate, models_disagree, probe_uncertain}; `relation` ∈ {synonym, antonym, related, unrelated}; `review.status` ∈ {unreviewed, accepted, rejected, merged, deferred}.  `verdict = tagged` with `physical` sets `holding = physical`; with `role_*` sets `holding = roles` and `entity_type = role`.

**Metric config** (`data/candidates/metric_config.json`, wrapped in a `json_metadata` envelope):

```json
{"config_version": "2026-10-03", "models": {"openai": "text-embedding-3-large", "local": "Qwen/Qwen3-Embedding-0.6B", "local_mode": "document"},
 "representation": {"prefix": "keep", "contrast": {"openai": "keep", "local": "strip"}, "cuts_file": "data/candidates/calibration/contrast_cuts.json"},
 "space": {"variant": "centred_pc1", "mean": "corpus_fixed", "csls_k": 10, "K": {"openai": 31, "local": 27}, "K_rule": "95pct_variance",
           "K_sensitivity": {"openai": {"10": 0.61, "20": 0.58, "40": 0.55}}},
 "thresholds": {"openai": {"t_hi": 0.62, "t_lo": 0.35}, "local": {"t_hi": 0.58, "t_lo": 0.31}, "grey_probe": [0.3, 0.7]},
 "probe": {"features": ["absdiff", "product", "cos"], "coef_file": "data/candidates/calibration/polarity_probe.json"},
 "evaluation": {"auc_dup_vs_distinct": 0.91, "antonym_vs_synonym_auc": 0.74, "spearman_vs_persona_yield": 0.31,
                "paraphrase_recall_top1": 0.97, "hubs_removed_by_csls": 4, "n_low_tail": 23}}
```

**Report rows.**  Filter summary (`filter/<batch>/summary.json`): `{"n": 300, "verdict_counts": {"trait": 110, "tagged": 95, "reject": 95}, "tag_counts": {...}, "polysemy_rate": 0.18, "parse_rate": 1.0, "second_opinion_n": 41, "disagreements": 6, "cost_usd": 0.47, "cost_per_candidate_usd": 0.0016}`.  LOO metric row (`calibration/loo_metrics.json`): `{"model": "openai", "representation": "full+prefix+contrast", "variant": "centred_pc1", "metric": "nn_csls", "auc_dup_vs_distinct": 0.91, "auc_ant_vs_syn": 0.74, "spearman_persona_yield": 0.31, "K": 31}`.  Drop-or-merge row (`calibration/drop_or_merge.md`): `| trait | nearest | sim raw/centred/pc1/zca | arrangement | deliberate_dup | description A | description B |`.  Novelty review row (`novelty/<batch>/review_list.md`): `| rank | section | key | label | decision | nearest_existing (relation) | local | directional | cluster_size | adjudication note |`.  Recovery report: see § Frozen interface.

## 7. CLI

All commands: `--registry PATH` (default `data/candidates/registry.jsonl`), `--data-dir`, `--dry-run` (prints the plan, the cost estimate and the first three prompts; writes nothing, calls nothing), `--budget-usd` (hard cap; default 5.0 for LLM commands, 1.0 for embedding-only), `--confirm-expensive` (required when the estimate exceeds the budget; the $20 line additionally requires Roger's explicit go in chat, recorded in the run's `run.json` as `confirmed_by`).  Estimates are printed as `n_calls × (in, out) tokens at model rates = $X`, then a `GuardedUsage` aborts the run at the cap and still writes `usage.json`.

- `setup_external.py [--wn] [--hf-model ID] [--dry-run]`: downloads OEWN 2024 (~100 MB) into `data/external/wn/` and the local embedding model into `data/external/hf/`; prints versions; idempotent.  No API cost.
- `gap_registry.py submit --file candidates.jsonl --generator G --run-id R`: rows `{surface, rank?, score?, gloss_hint?, sense_id?, source_ref?}`; appends new keys, merges sources on existing keys; prints `SubmitReport`.  `status` (counts by verdict / decision / review / holding / generator), `report [--generator G] [--decision new]` (markdown table), `holding --list physical|roles` (prints a markdown block for Roger to paste into TRAITS_TO_ADD / ROLES_TO_ADD; never writes those files), `compact` (folds the log to one line per key after copying `registry.jsonl` to `registry.jsonl.bak.<UTC>`; snapshot-before-invalidate), `promote --keys K... | --status accepted [--min-local-novelty X] [--section S] [--dry-run]` (appends `status: "candidate"` entries to the seed queue via `seed_entities.load_queue/save_queue`; refuses any stem present in the corpus or in `build_registry(...)`; roles get `entity_type: "role"`; `partner` set when the novelty block says `pair_completion`; `tags: ["gap_gen", "source:<generator>", <filter tags>]`; `description_draft` = gloss; `section` default `"trait-gap generators (2026-09)"`).
- `traithood_filter.py --batch-id B (--unfiltered | --keys ... | --validation-file F) [--model claude-haiku-4-5-20251001] [--second-model claude-sonnet-4-6] [--batch-size 25] [--limit N] [--no-probe] [--no-second-opinion]`: pipeline per row: `freq` (hard reject below 2.0 costs nothing) → `wordnet` → classifier (25 per call, cached system rubric, `max_tokens` 8000; an unparseable batch is retried once at half size) → definition probe for 2.0 ≤ Zipf < 2.5 → second opinion (10% random + confidence < 0.6 + prior/LLM disagreement) → registry write, `responses.jsonl`, `summary.json`, `usage.json`, `warn_if_low_parse_rate`.  Estimate: per 25 candidates ≈ 1.2k cached + 0.6k input, ≈ 2.5k output (≤ 20-word reasons) → **≈ $6-9 per 10,000 candidates** including Sonnet second opinions (plan 14's $3.2 assumed 60 output tokens per candidate; the reason field costs the difference; keep reasons short).  `--validation-file` rows may carry `expected` fields used by the acceptance test.
- `calibrate_metric.py [--models openai local] [--skip-llm] [--criteria a,b,c,d,f,h,j] [--paraphrase-cache F] [--vectors-dir 'runpod_workspace/qwen/qwen-3-32b Roger 8slot'] [--out data/candidates/calibration] [--write-config]`: embeddings for 414 traits × representation variants (≈ 8 texts per trait, ≈ 250k tokens, ≈ $0.03 at -large; local free); Haiku paraphrases (414 × ~430 tokens ≈ $0.35, cached in `calibration/paraphrases.json` and reused by M3); Sonnet blinded neighbour judgement (60 traits × 2 orders ≈ $0.65); total **< $1.50**.  `--skip-llm` runs everything that needs no API (the pilot).  Writes the calibration outputs and, with `--write-config`, `metric_config.json`.
- `novelty_score.py build-index [--config F]` (embeds the corpus under both models with the config's representation; cached) · `score --batch-id B (--unscored | --keys ... | --file F) [--no-adjudicate] [--limit N]` (writes the novelty block, `novelty.json`, `review_list.md`, `usage.json`; estimate ≈ $0.05 embeddings + ≈ $2.3 Haiku adjudication per 10k at 15% grey) · `review-list --batch-id B` (re-renders the ordering without calls).
- `recovery_test.py --hidden-file F | --hidden-frac 0.2 --seed S --candidates F [--no-hide-partners] [--config F]`: no LLM calls (adjudication off inside the hook); prints the `RecoveryReport` and writes it next to the candidates file.

## 8. Acceptance tests, written first

Unit tests live in `assistant_axis/tests/test_gapgen_<module>.py` and `data_analysis/tests/test_gap_generation_cli.py`; none calls an API or loads a model (fake clients, a deterministic hash embedder).  Recorded-output acceptance tests (`assistant_axis/tests/test_gapgen_acceptance.py`) read the saved `summary.json` / `calibration/*.json` / `novelty/*.json` and **skip** when the file is absent, so they pass in CI and bite after the paid runs.

M1: normalisation (multiword, hyphen, apostrophe, diacritics, idempotence, content words); registry (log fold last-wins, `rev` increments, source merge without duplicates, `merge_block` touches one block, `compact` reproduces the fold and leaves a `.bak`, `holding_list`); freq (Zipf min over content words with a fixed stoplist, hard-reject and band flags, phrases); wordnet (fake `wn` module; real DB test skipped without `data/external/wn`); rubric (the word "reason" precedes "verdict" in both the schema text and the example; no rubric example word is a corpus stem or a queued stem; states rule and roles rule present; parser handles fences, a `+` before numbers, missing ids, out-of-vocab tags → row rejected and counted); `derive_polysemy` truth table; `select_second_opinion` rule; gloss band 18-43 words; filter runner with a fake client writes the block, `responses.jsonl`, `summary.json`, `usage.json`, and `*** HIGH FAIL RATE ***` appears in caplog when 2 of 100 rows fail; **cost guard**: `GuardedUsage` raises `BudgetExceededError` at the cap and `usage.json` is still written; `confirm_or_abort` refuses an estimate over the budget without the flag and refuses over $20 without both the flag and `confirmed_by`; `promote` builds the entry shape `seed_entities.cmd_write` accepts (round-trip through `seed_document`), refuses corpus and queue collisions, `--dry-run` leaves the queue byte-identical, holding rows are never promoted.  Acceptance (recorded): existing labels ≥ 95% `trait` (the ~26 seed-queue `physical` entries count as correct when `tagged: physical`); the six rejects (disciplinary, engaging, economic, balanced, empowered, emotive) ≥ 4 flagged `polysemy` or `trait_sense_rank ≥ 2`, `empowered` carries `state`/`transient_only`, `economic` `relational_only`; 1,000 random OEWN adjectives ≤ 15% `trait`; stability rerun of 200 ≥ 90% verdict agreement; parse rate ≥ 99%; `corpus_regions.json` covers every trait file.

M2: embed cache (hit/miss by `(model, sha256(text))`, npz round-trip, manifest, row order, unit norm; fake OpenAI client charges `total_tokens`); space (centring uses the fitted corpus mean on new points, PC removal is orthogonal, ZCA yields identity covariance, `k_for_variance` on a synthetic spectrum, residual fraction in [0, 1] and 0 for in-subspace vectors, CSLS on a toy hub); contrast (census parser returns 10/68/29 stems; the ten N cuts match hand-written expectations for three of them; no marker → unchanged; overrides win); labels (≥ 100 reciprocal pairs from the real corpus, v4 filter at ≥ 4, seed-queue decision parser extracts the named stems from the sampled `decision` strings, unrelated pairs never overlap labelled ones, folds never split a pair); persona (bracket parser on a fixture; LOO residual on synthetic data); calibrate on synthetic embeddings with planted duplicates and antonyms (AUC 1.0, `place_thresholds` gives synonym recall 0.95 and unrelated 0.99 by construction, hubness counts, drop-or-merge flags a recorded pair as expected, config validates against the schema, envelope present).  Acceptance (recorded): `auc_dup_vs_distinct ≥ 0.85` for the chosen variant; `paraphrase_recall_top1 ≥ 0.95`; hubness census and low tail reported; the contrast decision per model recorded with all ten criteria present; N-class nearest neighbours unchanged on stripping for ≥ 8 of 10 if stripping is chosen.

M3: index build honours `exclude_stems`; decision truth table (both ≥ t_hi and probe says synonym → covered; both < t_lo → new; anything else → grey, including `ambiguous_label`); `pair_completion` when the neighbour has no partner file and the probe says antonym; `deliberate_duplicate` from a standard suffix beside a plain stem; `ambiguous_label` when bare-label and gloss top-3 are disjoint; adjudication called only for grey rows, prompt reason-first, usage charged, relation parsed; review order (dedupe at t_hi keeps one representative with `cluster_size`, farthest-first with the corpus pre-seeded puts the max-min-distance item first, alignment section precedes the rest); recovery (planted paraphrases recovered, partners hidden together by default, pair-recovery counted separately, by-region breakdown, no LLM calls).  Acceptance (recorded): the 22 September rejects/near-duplicates come back `covered` with Roger's named neighbour in the top 3 for ≥ 18; the 124 clean pairs classified antonym with F1 ≥ 0.9 on held-out folds; paraphrase recall ≥ 0.95 as `covered`; Spearman between the two models' nearest-neighbour similarities reported with the disagreement rate; the 52 `exists` queue entries scored `covered`.

Commands that must pass at each milestone's end:

```
uv run pytest assistant_axis/tests/test_gapgen_*.py data_analysis/tests/test_gap_generation_cli.py assistant_axis/tests/test_judge_pricing.py -q
uv run pytest -q                                   # the whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles      # must be empty: nothing here edits trait or role files
```

## 9. Ordered task checklist

**M1 — filter and registry (plan 14)**

1. Dependencies and skeleton: `pyproject.toml` (+`wordfreq`, `wn`), `uv lock`, `.gitignore` lines, `gapgen/paths.py`, `setup_external.py` with `--dry-run`, pricing entries in `judge_pricing.py`.  Test: `test_gapgen_paths.py` (all paths inside the repo), `test_judge_pricing.py` extended.
2. `normalize.py`.  Test: `test_gapgen_normalize.py`.
3. `registry.py` + `runs.py` (log-structured file, `Candidate`, `submit_candidates`, `merge_block`, `compact`, `start_run`).  Test: `test_gapgen_registry.py`.
4. `freq.py`, `wordnet.py` (run `setup_external.py --wn` once).  Test: `test_gapgen_freq.py`, `test_gapgen_wordnet.py`.
5. `cost.py`, `llm.py`.  Test: `test_gapgen_cost.py`, `test_gapgen_llm.py` (fake Anthropic client, transient-error retry, usage charged).
6. `filter_rubric.py` (rubric v1: trait-hood definition from the brief; six positive and twelve negative examples from outside the corpus, several alignment-flavoured; the states rule; roles → `tagged`; JSON rows reason-first; `region`).  Test: `test_gapgen_filter_rubric.py`.
7. `filter.py` + `traithood_filter.py`.  Test: `test_gapgen_filter.py`, CLI dry-run test.
8. `promote.py` + `gap_registry.py`.  Test: `test_gapgen_promote.py`, CLI tests (submit, status, holding, compact, promote dry-run).
9. Build the validation file (414 existing labels with `expected`, the six rejects, the 95 `not_adopted` labels, 1,000 random OEWN adjectives with a fixed seed) and run the **pilot** (§10).  Roger's decision.
10. Full validation run, stability rerun, gloss spot-check table (30 glosses beside corpus descriptions), `corpus_regions.json`; acceptance test passes on the recorded outputs.

**M2 — metric calibration (plan 15)**

11. `embed.py` (both backends, cache, usage; `setup_external.py --hf-model`).  Test: `test_gapgen_embed.py`; a real local-model smoke test behind `GAPGEN_RUN_LOCAL=1`.
12. `labels.py`: seed `calibration/labelled_pairs.json` from the corpus, v4, the seed queue and the plan 11 §6 list; hand-check and commit.  Test: `test_gapgen_labels.py`.
13. `contrast.py` + `representation.py`: mechanical cuts for the 107, hand-check into `contrast_cuts.json`; minimal pairs from ~40 clean pairs.  Test: `test_gapgen_contrast.py`.
14. `space.py`.  Test: `test_gapgen_space.py`.
15. `persona.py` (slot 6, layer 25, corpus mean over traits+roles, L=3 shear if buildable; LOO residual at K = 37 and 10/20/40; bracket cross-check).  Test: `test_gapgen_persona.py`.
16. `calibrate.py` steps 1-4, 6-8: LOO metrics per model × representation × variant; tasks (a) (b) (c); hubness; NN-distance histograms (PNG with `png_metadata`, read back and inspected); thresholds against the bulk with the labelled anchors; drop-or-merge table.  Test: `test_gapgen_calibrate.py` on synthetic data.
17. Contrast ablation criteria (a)-(j): (a) (b) (c) (d) (f) (h) (j) local; (g) Haiku paraphrases; (e) Sonnet blinded judgement with the 30 comparisons for Roger; (i) paraphrase-based held-out recovery.  Test: unit tests on the criterion functions with synthetic inputs.
18. `calibrate_metric.py` with `--skip-llm`; run the **pilot** (§10).  Roger's decision.
19. Full run with `--write-config`; acceptance test passes; update `data/README.md` (candidates/ and external/ paragraphs).

**M3 — novelty scorer (plan 10)**

20. `novelty.py` (index, per-model neighbours with CSLS, local and directional scores, polysemy flag, `PolarityProbe` trained on the labelled pairs and saved as JSON, decision rule, flags).  Test: `test_gapgen_novelty.py` with the hash embedder.
21. `adjudicate.py` + review ordering.  Test: prompt reason-first, only grey rows call, ordering properties.
22. `recovery.py` + `recovery_test.py`.  Test: `test_gapgen_recovery.py`.
23. `novelty_score.py` (build-index, score, review-list).  Test: CLI dry-run and a fake-client end-to-end on a tmp registry.
24. Calibration replay on the real corpus (paraphrase recall, rejection replay, antonym F1, model agreement); run the **pilot** (§10).  Roger's decision.
25. Freeze: `gapgen/__init__.py` exports exactly the § Frozen interface; add a short "Trait-gap platform" paragraph to `AGENT_NOTES.md` under the `trait-pairs` rule marker and run `uv run python tools/sync_agent_notes.py`; write the acceptance report (§11).

## 10. Pilot

- **M1**: 20% of the validation file, stratified (83 existing labels, 19 `not_adopted`, 200 OEWN adjectives), one Haiku pass, second opinions on; ≈ 12 classifier calls, ≈ $0.50.  Readout: verdict and tag fractions per stratum, polysemy rate, parse rate, cost per candidate, the ten lowest-confidence rows with reasons, and ten glosses beside their descriptions.  Roger decides: rubric wording (examples, states, roles), whether reasons stay in the output (≈ 60% of the cost), and the second-opinion rate; then the full run (≈ $2.5).
- **M2**: `--skip-llm` with the local model and OpenAI (≈ $0.03): the LOO table for every variant, the NN-distance histograms, the hubness census, the drop-or-merge table and criteria (a) (b) (c) (d) (f) (h) (j) of the ablation, plus the 30 blinded comparisons for Roger to label.  Roger decides: variant, whether the low tail is worth a drop-or-merge pass now, and whether the paid criteria (e) (g) (≈ $1) are needed to settle the contrast policy or the local criteria already decide it.
- **M3**: score the queue-derived pilot set (every seed-queue entry with a final `description` and no corpus file, the 95 `not_adopted`, the 52 `exists`; ≈ 350 items, ≈ $0.15 with adjudication).  Readout: covered / new / grey fractions, LLM fraction, cost per item, the `exists` recall, model agreement, and a 40-row stratified sample (by similarity bin) for Roger to label covered / antonym-completion / new.  Roger decides: grey-zone width (recall 0.95 versus fewer LLM calls), whether the alignment-first ordering reads well, and the go for the generator workstreams.

Yield per dollar is reported for every pilot as `n_useful_rows / usage.json total_cost_usd` (M1: rows with verdict `trait` and no polysemy flag; M3: rows decided `new` or `pair_completion`).

## 11. Report at the end

One page at `reports/trait_gap_generation/acceptance_platform.md`: what was built (module list against §5), deviations from this plan with reasons, test results (the §8 commands verbatim with pass counts), cost per milestone from the `usage.json` files (filter validation, calibration, novelty pilot; per model), the three pilot readouts and Roger's decisions on them, the chosen metric config with its evaluation numbers, the drop-or-merge tail size, open QUESTIONS entries, and the frozen interface's final signatures if any drifted from § Frozen interface (they should not).

## 12. Escalation

Opus retries a failing step once with a changed approach, then asks Fable (diff review, architecture calls, stubborn failures), then Roger through [`QUESTIONS.md`](./QUESTIONS.md) in its format (`N. [14|15|10] question. Assumption proceeded under: ... Status: open`), proceeding under the stated assumption unless the answer would make the work useless.  Pre-registered questions Opus copies into `QUESTIONS.md` at the start of M1 and proceeds under: (1) holding lists are printed as markdown for Roger to paste, never written into TRAITS_TO_ADD / ROLES_TO_ADD by the tool; (2) the second-opinion model is `claude-sonnet-4-6` (the repo's current default) rather than plan 14's "Sonnet 5"; (3) the rubric returns a `region` per candidate and the corpus validation run supplies `corpus_regions.json` from labels alone; (4) in text-embedding space `K_95` may be far above 40; the config records `K_95` as decided and the K = 10/20/40 sensitivities beside it; if task (c) collapses at `K_95` that goes to Roger with the numbers; (5) the 200-item hand-labelled set waits for the first generator run.  Anything that would edit an existing trait file, spend over the budget of a command, or change a frozen signature stops and asks.

## Frozen interface (for workstreams 1, 2, 8, 13 and later)

> **Superseded in part (2026-10-08).**  The registry side of this section (`Candidate`, `start_run`,
> `submit_candidates`, `RunContext`, the registry row) was built as written and stands.  The scorer side
> (`NoveltyQuery`, `NoveltyResult`, `score_novelty`, `recovery_test`, `RecoveryReport`, `embed_local`)
> was never built: M3 was redesigned on 2026-10-02 as retrieve-then-judge (the "M2 final settings and the
> M3 design" section and M3 decisions 1-17).  Generators are written against the section **"Interface as
> built (2026-10-08)"** at the end of this file, which replaces the scorer side and re-specifies the
> recovery harness; nothing in a generator plan should name the old scorer functions.

Everything below is importable from `assistant_axis.gapgen`; generator plans depend only on these names.

**Registry schema**: the row in §6 with its vocabularies; key `f"{stem}#{sense_id}"`; the file `data/candidates/registry.jsonl` is a log whose latest line per key is the record.  A generator never writes the file directly.

**Submitting candidates** (the Python API a generator calls):

```python
@dataclass(frozen=True)
class Candidate:
    surface: str                      # as emitted, e.g. "kind to animals"; normalised to stem/label by the registry
    generator: str                    # short id, e.g. "wordnet_walk"
    run_id: str                       # e.g. "2026-09-30a"
    rank: int | None = None           # emitted order (recovery tests use it)
    score: float | None = None        # generator's own score, if any
    gloss_hint: str | None = None     # the generator's one-line sense, if it has one (the filter writes the real gloss)
    sense_id: int = 1                 # a second intended sense of the same word is a second Candidate
    source_ref: str | None = None     # "oewn:02345678-a", "roget:604", "allport:1234", ...

def start_run(generator: str, run_id: str, *, args: dict | None = None) -> RunContext
    # RunContext.dir = data/candidates/runs/<generator>/<run_id>/ ; .usage is a MultiModelUsage the generator
    # passes to every LLM call; .finish() writes run.json (git sha, args, n_emitted, UTC times) and usage.json.

def submit_candidates(cands: Iterable[Candidate], *, registry_path: Path = REGISTRY_PATH,
                      run: RunContext | None = None) -> SubmitReport
    # SubmitReport(n_submitted, n_new, n_merged, keys: list[str]); also writes <run.dir>/candidates.jsonl when run is given.
    # Idempotent per (generator, run_id, surface, sense_id).
```

After submitting, the generator's plan runs `traithood_filter.py --batch-id ... --unfiltered` and `novelty_score.py score --batch-id ... --unscored`; it does not call the filter or scorer functions directly.

**Novelty scorer** (input and output):

```python
@dataclass(frozen=True)
class NoveltyQuery:
    key: str            # registry key, or any unique id for ad-hoc use
    label: str          # display form
    gloss: str          # REQUIRED, corpus form ("This means ..."), 18-43 words; the scorer embeds label + gloss

@dataclass(frozen=True)
class Neighbour:
    stem: str; sim: float; csls: float; p_antonym: float | None; relation: str   # synonym | antonym | related | unrelated
    partner_stem: str | None; partner_has_file: bool; arrangement_kind: str | None

@dataclass(frozen=True)
class NoveltyResult:
    key: str; decision: str            # covered | new | grey
    local: float; directional: float   # per the config's primary model; per-model values in `signals`
    nearest: list[Neighbour]           # top-5 under the primary model
    signals: dict[str, dict]           # per model: local, directional, k, nearest
    agreement: str                     # agree | disagree
    flags: list[str]                   # ambiguous_label | pair_completion | deliberate_duplicate | models_disagree | probe_uncertain
    nearest_existing: str | None
    adjudication: dict                 # {"model", "relation", "note"} or nulls

class NoveltyIndex:
    @classmethod
    def build(cls, *, data_dir: Path, config: MetricConfig, exclude_stems: Collection[str] = (),
              cache: EmbeddingCache | None = None, usage: MultiModelUsage | None = None) -> "NoveltyIndex"

def score_novelty(queries: Sequence[NoveltyQuery], index: NoveltyIndex, *, config: MetricConfig,
                  adjudicate: bool = True, usage: MultiModelUsage | None = None,
                  anthropic_client=None) -> list[NoveltyResult]

def review_order(results: Sequence[NoveltyResult], index: NoveltyIndex, regions: Mapping[str, str],
                 *, config: MetricConfig) -> list[tuple[str, str]]     # (section, key): "alignment" rows first, then "other"
```

`MetricConfig.load(path=METRIC_CONFIG_PATH)` reads `data/candidates/metric_config.json`; `config_version` is stamped into every novelty block.

**Recovery-test hook** (what plan 13 builds on):

```python
def recovery_test(candidates: Sequence[NoveltyQuery], hidden: Sequence[str], *, data_dir: Path,
                  config: MetricConfig, hide_partners: bool = True, regions: Mapping[str, str] | None = None,
                  cache: EmbeddingCache | None = None) -> RecoveryReport
    # Builds NoveltyIndex with exclude_stems = hidden (+ their arrangement partners when hide_partners),
    # scores the candidates with adjudicate=False, and matches each hidden stem against the candidates'
    # nearest lists at the config's t_hi ("strict") and t_lo ("loose").  No LLM calls.

@dataclass
class RecoveryReport:
    n_hidden: int; n_candidates: int
    recovered: dict[str, str]          # hidden stem -> candidate key (concept match, strict)
    recovered_loose: dict[str, str]
    pair_recovered: dict[str, str]     # hidden stem -> candidate key matching its antonym pole
    recall_strict: float; recall_loose: float; pair_recall: float
    by_region: dict[str, dict[str, float]]
    misses: list[str]
    def to_json(self) -> dict
```

`recovery_test.py` is the CLI wrapper; plan 13 adds folds, provenance exclusion and the estimators on top of `RecoveryReport` and the registry's `matches_existing` / `heldout_hit` fields, which `score_novelty` leaves `null` and the hook fills for the hidden set.

## Interface resolutions (2026-09-24, Claude; architecture calls under the agreed process)

Requests from the two generator plans, resolved.  Opus implements these inside the M1/M3
tasks they touch; the frozen interface above is amended as stated here.

From `coding_plan_01_censuses.md`:
1. **Accepted.** `Candidate.gloss_hint` is stored in the row's `sources[]` entry and shown in
   the filter prompt as "intended sense" (first non-null across sources, display form).
2. **Accepted.** `traithood_filter.py` and `novelty_score.py score` take `--run GENERATOR/RUN_ID`
   (rows whose `sources[]` carry that pair, skipping rows already filtered or scored), in
   addition to `--unfiltered` / `--unscored` / `--keys`.
3. **Accepted.** `recovery_test` accepts `hidden` equal to every trait stem (an index with no
   traits); `RecoveryReport` carries `results: list[NoveltyResult]`; for a stem in
   `exclude_stems`, `Neighbour.partner_has_file` is `False`.
4. **Accepted.** When `Candidate.score` is a documented human familiarity and is >= 0.5, a
   word below Zipf 2.0 goes to the definition probe instead of the hard reject.
5. **Confirmed.** `RunContext.finish()` always writes `usage.json`, with zero calls if none
   were made.

From `coding_plan_02_roget_wordnet.md`:
1. **Accepted.** `Candidate.partner_hint: str | None`, carried into the `sources[]` entry;
   `gap_registry.py promote` sets `partner` on both queue entries when both are promoted.
2. **Accepted.** `assistant_axis.gapgen` exports a stable facade: `embed_local(texts, *, cache)
   -> np.ndarray`, `trait_text(...)`, `EmbeddingCache`; internal module paths may move.
3. **Accepted.** `wordnet.oewn() -> wn.Wordnet` returns the configured lexicon handle.
4. **Decided differently: merge, not drop.** Two `Candidate`s in one run with the same
   `(surface, sense_id)` and different `source_ref` merge into one row with two `sources[]`
   entries (`SubmitReport.n_merged` counts them).  Generators submit one `Candidate` per
   source reference and do not join `source_ref` with `;`; `roget_harvest` drops its
   generator-side dedupe and `to_candidates` emits one candidate per head.
5. **Accepted.** `RecoveryReport.to_json()` includes `config_version`, `t_hi`, `t_lo` and
   `gloss_source`.

## Review amendments (2026-09-24, Roger and Claude)

1. **Three Opus jobs, not one.**  M1, M2 and M3 each get their own Opus agent in its own
   worktree, with a Fable diff review and Roger's pilot decision before the next milestone
   starts.  The frozen interface is therefore exercised by M2 and M3 before any generator
   depends on it.  The generator workstreams (plans 1 and 2) may start their M1-only tasks
   as soon as M1 is merged.
2. **First-measurement thresholds are report-and-decide, not gates.**  In §8 the M2 and M3
   acceptance numbers (`auc_dup_vs_distinct ≥ 0.85`, `paraphrase_recall_top1 ≥ 0.95`, antonym
   F1 ≥ 0.9 on held-out folds, ≥ 18 of the 22 September rejects `covered`, the 52 `exists`
   entries `covered`) are targets: the acceptance test *records* them and the milestone
   report puts them in front of Roger, who decides whether the platform is fit to feed
   generators.  Only the mechanical checks stay hard gates: parse rate ≥ 99%, cost caps,
   `usage.json` present, the §8 command list green, nothing edits trait or role files.
   Rationale: the plan's own illustrative config shows antonym-vs-synonym AUC 0.74, which
   is what the literature predicts for embedding models; if the polarity probe cannot reach
   the target, plan 11's lexical antonym signals are the designed remedy, not a lower bar.
   Chasing a gate would be the wrong response.
3. **Registry tracking.**  The live log `data/candidates/registry.jsonl` is gitignored (every
   filter and novelty write appends a revision; ten thousand candidates at three or four
   revisions is tens of megabytes of churn).  `gap_registry.py compact` writes the folded
   snapshot to `data/candidates/registry.snapshot.jsonl`, which is tracked; the acceptance
   report and every pilot readout are taken from a fresh snapshot.  §5's "tracked unless
   noted" is amended accordingly, and `.gitignore` gains the log path.

## Amendments for M2 and M3 (2026-09-30, Roger and Claude)

Recorded during M1's split-filter work, to be folded into the M2 and M3 briefs.  Roger's decisions
unless marked.

1. **Local embedding model: `BAAI/bge-large-en-v1.5`, not Qwen3-Embedding-0.6B.**  Roger: "I'm
   inclined to avoid using a Qwen-derived embedding, specifically because Qwen is one of the models
   we're experimenting on"; the same goes for Llama, OLMo and gpt-oss.  bge-large is BERT-based,
   Apache-2.0, 335M parameters, about 1.3 GB, CLS pooling, and already the plan's named fallback
   behind `--local-model`.  The download into `data/external/hf/` waits for Roger's word at the M2
   launch.  He is open to a Gemma- or Mistral-derived embedder as a comparison arm: EmbeddingGemma
   (300M) is the practical one on this Mac; the Mistral-based embedders are 7B and would need the pod.
2. **Persona vectors for criteria (c) and (h): the 8-slot set, slot 6, layer 25.**  Roger: the 8-slot
   set is the one to use, slot 6 "seems to have the best persona data"; layer 25 is the documented
   default (`results_analysis/README.md`, "slot 6 / layer 25"; `pair_slice_plots.py --layer 25`).
   The vectors predate the September corpus work, so the 659-trait corpus has vectors for about
   300 traits only.  The worktree reaches the data through links at
   `runpod_workspace/qwen/qwen-3-32b Roger 8slot` and `qwen-3-32b Roger`, which git ignores.
3. **The alignment score feeds the duplicate-or-gap decision (M3).**  The split filter records an
   alignment score of 0 to 3 for every word that goes on as a trait (rubric `alignment.md` draft 3;
   `alignment_relevant` is derived as score 2 or 3).  Roger: use it "as input to the dupe/gap
   decision, so density increases gradually as you get closer to alignment rather than a sudden
   transition".  How the score moves the thresholds is for the M3 plan to propose.
4. **The worktree's `.env`** was refreshed on 2026-09-30 and now has the OpenAI key M2 needs.

## M2 launch decisions (2026-10-01, Roger and Claude)

Taken when item 15 (M2) was started, after item 14 closed with the split filter's rerun
([readout_m1_validation.md](./readout_m1_validation.md)).

1. **Download `BAAI/bge-large-en-v1.5`** (about 1.3 GB) into `data/external/hf/`: Roger, "go ahead".
2. **EmbeddingGemma-300m as a comparison arm**, if the Hugging Face token's account has access to the
   gated model; the agent tries, and reports and continues with two arms if refused.  Gemma is not one
   of the project's experiment subjects (Qwen, Llama, OLMo, gpt-oss are).
3. **M2 runs on the worktree's corpus now**, before the merge into `anthropic-vllm-uv`; Roger: "corpus
   descriptions are unlikely to change much, instructions and questions are still not stabilized."
   M2 embeds labels and descriptions only, so the two pending renames (determinist, metaphysical
   libertarian) cost one cheap rerun of the final calibration after the merge.
4. **Gloss length is a variant to measure** (Claude's addition).  The split filter's glosses have a
   median of 14 words, below plan 15's 18-43 band and the corpus median of 24.  M2 adds a variant that
   embeds each description truncated to about 14 words, beside the full text and the ~20-word check
   plan 15 §3.1 already asks for, so M3 knows whether candidate glosses must be lengthened or
   descriptions matched in length at embedding time.
5. **The contrast census is recomputed** mechanically on the current 661 files (the census of
   2026-09-23 covered 414); the N/P/S classes exist only for its 107, and new cuts are reported for
   Roger in the pilot readout rather than classified by the agent.
6. **Pilot gate as planned**: the agent stops after task 18's `--skip-llm` pilot for Roger's decisions
   (space variant, whether the low tail is worth a drop-or-merge pass, whether the paid criteria (e)
   and (g) are needed), then task 19.  Cap $10; expected spend about $0.03 for the pilot and about $1
   for the paid criteria.


## M2 round 3 amendment (2026-10-02, Roger and the M2 agent)

Roger: tasks (a) and (c) correspond to two different uses of the embedding in M3 and are tuned
separately; task (b), telling a near-duplicate from an antonym, is left to the LLM adjudicator
("trivially easy by LLM inspection") and is reported, not used for selection.  So
`metric_config.json` carries two blocks over the same cached embeddings
([metric_config.py](../../assistant_axis/gapgen/metric_config.py)):

- `covered`: `space` (variant, fixed corpus mean), `representation`, `metric`, `contrast` per model,
  `thresholds` per model (`t_hi` from paraphrase-level duplicates at 95% recall, `t_lo` the 99th
  percentile of random pairs), `query_form`, `evaluation` (task a, task b as the antonym confusion
  the adjudicator absorbs, paraphrase recall, held-out recall).
- `directional`: `space`, `representation`, `K`, `K_rule`, `K_sensitivity` (10 / 20 / 40 / K_95),
  `evaluation` (task c by model, criterion (i)'s stability under paraphrase), `caveat` (task c is a
  proxy).

The frozen interface is unchanged: `MetricConfig`, `MetricConfig.load(path=METRIC_CONFIG_PATH)`
and `config_version` keep their names and signatures, and the §6 single-setting fields
(`representation`, `space`, `thresholds`) remain readable as properties that point at the `covered`
block.  §6's example config is superseded by these two blocks.

## M2 final settings and the M3 design (2026-10-02, Roger and Claude)

Decided by Roger on 2026-10-02 after round 4 of the calibration
([pilot_m2_readout.md](./pilot_m2_readout.md), round 4 at the top;
[retrieval_round4.md](../../data/candidates/calibration/retrieval_round4.md)).  These supersede the
covered/grey/new decision rule of §5 (`novelty.py`), plan 10's thresholds and `PolarityProbe`, and
the M3 acceptance tests of §8 that assume them; the M3 coding brief rewrites those against this
section.

**M2 final settings** (task 19 writes them into
[metric_config.json](../../data/candidates/metric_config.json), not written yet):

1. **Embedding model**: OpenAI `text-embedding-3-large` in the live pipeline.  It is closed (API only,
   undisclosed base) but predates gpt-oss, so it cannot descend from an experiment-subject family;
   Roger accepts the dependency.  `google/embeddinggemma-300m` stays in the config as an inactive
   fallback (open weights, in `data/external/hf/`), never mixed into a run's results.  bge is dropped.
   Every run re-embeds a fixed handful of texts and compares them with the cache, so a silent change
   to the API model shows up as a warning.
2. **Covered setting**: descriptions cut to 20 words (`w20`), centred on the fixed corpus mean,
   cosine; **retrieve k = 10 nearest existing traits**.  No similarity threshold decides anything:
   at 95% paraphrase recall a threshold put 61% of recorded antonym pairs on the covered side.
   Recall@10 on the realistic query (an M1 gloss written from the bare label, no label in the
   query): 0.972-0.978; 0.990 pooled over 3,098 queries.  Partial whitening was no better at any N
   (paired tests with Holm's adjustment); merging two models' lists adds nothing.
3. **Directional setting**: `w20`, centred, residual outside the top K = 10 principal directions;
   K provisional, judged only through the persona-space proxy (task c).  The same embeddings serve
   both settings, so M3 embeds the corpus once.
4. **Contrast clauses**: kept in the embedded text (Roger's 30 blinded marks were a coin flip).
5. **M2 acceptance targets restated** (a consequence of the design change, approved with it): the
   §8 targets `auc_dup_vs_distinct >= 0.85` and `paraphrase_recall_top1 >= 0.95` belonged to the
   threshold design and are replaced by **retrieval recall@10 >= 0.95 on the M1-gloss queries** for
   the chosen setting; the old figures stay reported.

**M3 design: retrieve, then judge.**  Roger's design of 2026-10-02 with the refinements agreed the
same day:

1. **Exact-label check** (no model): a candidate whose normalised label is a corpus stem, a queue
   stem or a `renamed_from` is covered at once.
2. **Retrieve** the 10 nearest existing traits (covered setting above).
3. **Expand arrangements**: when a retrieved trait is in a recorded pair, the other side joins the
   list too; if both sides were retrieved they are listed once, at the closer one's position.
   Triangles and tetrahedra expand to all their members; sequences (the moral-circle group) do not.
4. **Relation call** (one call per candidate, all listed traits in it): for each, is the candidate
   *similar to*, *opposed to*, *different enough that the question is ill-defined*, or *unsure*.
   The judge sees labels and descriptions in random order, with no embedding scores or ranks and no
   indication of which traits form pairs, so the pair check below stays independent.  Expected
   model: Haiku (Roger is confident it tells words from their antonyms); *unsure* goes to Sonnet.
   - Pair check: for a pair, one side should come back similar and the other opposed.  Similar to
     both or opposed to both is flagged (a slip, or a candidate off the pair's axis, perhaps a third
     pole).
   - The opposed side of a pair is dropped when the candidate is similar to its partner.
   - **Opposed to a trait with no partner** (`negative_label` still `non-X`) is a find, not a drop:
     the candidate may be that trait's missing antonym (pair completion).
5. **Overlap call** (one call per candidate, each remaining similar trait scored separately): how
   similar are the **concepts**, on an anchored scale, or *unsure*.  Draft scale: 4 the same concept,
   either label could replace the other; 3 the same concept, differing in scope, degree or emphasis;
   2 overlapping concepts sharing a core, each adding its own; 1 related but distinct; 0 unrelated.
   Roger prefers concept similarity to co-occurrence ("how often a persona with one would show the
   other"); co-occurrence is the comparison arm.  Expected model: stronger than Haiku (Sonnet);
   *unsure* goes to Opus.  Rubric examples follow the hygiene rule (near-duplicates of corpus terms,
   never corpus labels, queue entries or validation words).
6. **Decision**: overlap score combined with the candidate's alignment score (0-3, from the
   filter), so that the bar for "too similar" rises as a candidate nears alignment ("density
   increases gradually as you get closer to alignment").  Cut-offs set from Roger's manual marks
   after the pilot.
7. **Calibration by-product**: every overlap score is logged beside the embedding cosine, building
   the data for a cheap scorer that flags anomalies (a score far from what the angle predicts) for a
   larger judge, and possibly later skips calls.
8. **Near-duplicates are recorded**: a candidate judged too similar keeps `covered_by: <stem>`, its
   overlap score, gloss and frequency; a per-trait report (`gap_registry.py synonyms [--stem X]`)
   lists them with the plain-reading check, as a rename shortlist (Roger: "occasionally we find
   ourselves looking for a better name for an existing trait").  Traits whose bare label reads
   "related" or "different" in the corpus comparison come first; seeded from the queue's covered
   rulings, the antonym-check candidates, the drop-or-merge pairs and Roger's "history buff".
9. **Choosing the models by measurement**: on M3's pilot (about 350 items) run Haiku and Sonnet on
   the relation call and Sonnet and Opus on the overlap call for every item, both overlap rubrics,
   with Opus as the reference and Roger's 40 hand-labelled rows checking Opus.  Rough live costs per
   10,000 candidates: relation about $40 (Haiku, about 14 listed traits after expansion), overlap
   about $50 (Sonnet), a 10% Opus audit about $7; batches halve them.  A pre-pilot rubric test
   (both overlap rubrics on a few hundred existing-trait pairs, scored against persona-space cosine
   for the about 290 traits with vectors, the labelled pairs and the 16 drop-or-merge pairs; about
   $2-5) runs before the brief is final.

**M1 filter: judging model per generator** (Roger, 2026-10-02: "different generators will produce
different distributions").  The Opus audit of the filter's second-opinion sample
([opus_audit_m1.md](./opus_audit_m1.md)) found Haiku agreeing with Opus 95% on corpus labels and 68%
on random dictionary adjectives (Sonnet 96% and 84%), and the Haiku-Sonnet disagreement rate tracking
it (1% and 31%).  So: each generator's pilot runs the filter with Haiku plus the 10% Sonnet sample
and an Opus third opinion on that sample; Haiku is used for that generator if it agrees with Opus
about 90% of the time or more (about 10% disagreement or less with Sonnet), else Sonnet; later runs
keep the 10% Sonnet sample and warn and stop above about 10% disagreement.  Code needed: a
`--third-model` flag and the disagreement tripwire, by stratum or source.  Both now exist
(commit 26a90b6): `--third-model`, and `--max-disagreement` (default 0.10, overridden on resume by
`--accept-disagreement`), described in the split-filter section of
[data_analysis/README.md](../../data_analysis/README.md).

## M3 overlap call: decisions after the rubric test (2026-10-03 and 04, Roger and Claude)

The pre-pilot test of item 9 ran ([m3_overlap_test_readout.md](./m3_overlap_test_readout.md): 409
pairs of existing traits, both rubrics, Haiku 4.5, Sonnet 5.5 and Opus 5.5, then Roger's 30 blinded
marks, a Fable 5.1 scoring in the chat and through the API, $7.15 in all).  What it settled, and what it
left provisional:

1. **Rubric.**  A, concept similarity ([rubrics/overlap_concept.md](./rubrics/overlap_concept.md)), is
   the leading candidate; B, co-occurrence ([rubrics/overlap_cooccurrence.md](./rubrics/overlap_cooccurrence.md)),
   stays in play until Roger's manual review.  A's text is draft 2's (pinned as version 4, the same
   text as version 2): draft 3's sentence against extra answer keys was tried in a rerun, made the
   slip rarer but not absent, and was dropped (Roger: "a known, harmless issue, easily ignored"); the
   parser ignores extra keys.
2. **Model for the overlap call: Sonnet 5.5.**  Haiku is not used for it until Haiku 5.5 arrives,
   when it is re-evaluated.  Fable 5.1 was measured too: it sits with Sonnet and Opus (kappa 0.90
   against each, never more than one point from either), follows the answer format perfectly, and
   costs 2.5 times Opus; nothing in the test shows it judging the 2 / 3 boundary better, so it is
   not adopted.  Roger's marks did not show any large model closer to his judgement than Haiku or
   than Sonnet (30 pairs; every rater within one point of every other on every numeric item), which
   is why the design routes boundary pairs to a second opinion rather than picking a best model.
3. **Escalation (Roger, 2026-10-04; provisional).**  Sonnet scores every pair.  A pair Sonnet would
   cut (score at the cut-off or above) that sits *exactly on* the cut-off goes to Opus, and the
   candidate is kept if Opus puts it under; a Sonnet keep is never re-examined, a Sonnet score above
   the cut-off is cut without a second look.  So a candidate survives if either model would keep it,
   and Opus only ever rescues.  On the test's nearest pairs at cut-off 3: Sonnet cuts 42 of 256, 38
   pairs (15%, in a third of the calls) go to Opus, 8 are rescued; at cut-off 4, 4 pairs, none
   rescued.  About 30 cents per 100 candidates.  To be revisited once manual review has produced
   statistics.  Proposal (Claude): the M3 pilot still runs Opus on every item, as item 9 says, so
   that the revisit has its statistics; the rule governs the production path.
4. **Cut-offs** stay as first set: covered at 3 or more far from the alignment region, at 4 near it,
   never at 2; revisited with the marks after the pilot.
5. **"unsure"** was never produced by any model in 1,636 rubric-A answers; the route (unsure to
   Opus) stays as designed and costs nothing while that holds.
6. **By-products filed**: the same-concept pairs in TRAITS_TO_ADD's drop-or-merge TODO
   ([TRAITS_TO_ADD.md](../../data/traits/instructions/TRAITS_TO_ADD.md)); self-blaming /
   blame-shifting to the accountable triangle, not the merge list.
7. **The scale stays as it is (the arms experiment, 2026-10-04,
   [m3_overlap_arms_readout.md](./m3_overlap_arms_readout.md)).**  Roger asked whether another step
   in the 1-3 range would make the judgement easier.  Four arms on the same 409 pairs, two passes each
   ($15.89): the current rubric beat a six-rung scale, a relation-naming scale and a rewrite of line 3
   on every decision statistic (Sonnet-Opus agreement 87%, 8 of 300 nearest pairs on different sides
   of the cut-off, Opus self-consistent on 92%); the finer scales moved the cut-off and pulled the
   models apart.  Half of a model's own inconsistency is the order of the listed traits (same prompt
   twice: 95-98% the same answer; reordered: 86-89%).  Proposed for the pipeline, Roger to decide: read
   each overlap call twice in two list orders (about $0.003 a pair more) and treat a pair as *on the
   line* when either reading is at the cut-off or the two readings straddle it; such pairs go to Opus
   under rule 3.
8. **Settled 2026-10-06 (Roger): Sonnet first, Opus on the 3s** (rule 3 as written; the Opus-alone
   option is not taken).  Superseding the two-list-orders proposal in 7: **one pair per call**, the
   candidate's similar traits judged in cosine order with early exit once one says covered
   ([m3_overlap_arms_readout.md](./m3_overlap_arms_readout.md), "Early exit, and one pair per call"):
   it removes the list-order noise at the source (an identical prompt repeated agrees with itself
   92-98%, a reordered list 86-89%) and is cheaper than two orders; a second reading is kept for the
   pairs that land exactly on the cut-off.  Full runs go through the **Message Batches API** in waves,
   as the M1 split does ([batches.py](../../assistant_axis/gapgen/batches.py)): wave 1 every
   candidate's nearest pair, wave 2 the second pair of the candidates still undecided, and so on, then
   the Opus waves for the 3s; the wave machinery exists, the overlap waves are the M3 build's to
   define.  "Batch" in these notes means that API, not several pairs in one call.
9. **"opposite" (Roger, 2026-10-06): the first-line model's word is taken, no escalation** (every
   model and every rubric put the 30 recorded antonyms at "opposite", and Sonnet and Opus agreed on
   "opposite" 77 of 77 times).  When the nearest trait X comes back "opposite": if X has a recorded
   partner Y, the candidate is judged against Y next (Y moves to the front of the queue; a candidate
   opposite to X is usually Y's near-duplicate, and one call settles it); if X has no partner
   (`non-X`), the candidate is recorded as X's pair-completion candidate and routed to the pairing
   track (seed as X's partner, the antonym check decides).  Open with Roger: whether the scan then
   stops, as he proposed, or continues down the list (recommended: continue, since a candidate can be
   the opposite of one trait and the duplicate of another; 44 of the test's 300 nearest pairs were
   opposites, so the nearest neighbour is the antonym about one time in seven; the extra cost is one
   or two calls).  None of this is built: M3 has no code yet beyond the test harness.
10. **Round 3 (2026-10-06, [m3_overlap_arms_readout.md](./m3_overlap_arms_readout.md), "Round 3")
    reopens rule 8's model choice.**  Rubric A version 6 (one pair per call, A2's line 2) on the 409
    pairs, caching on, $3.56: self-consistency 95% for both models, parsing perfect, Opus closer to
    Roger's marks and to the known groups, both models' containment-as-2 slip down.  But Opus moved up
    and Sonnet did not, so under the Sonnet-first rule the pairs Sonnet keeps that Opus would cut went
    from 1-7 to about 16 in 409 (4%).  Opus costs $0.0031 a pair in this form (it thinks more when
    given one pair; the cache saving goes on output), Sonnet $0.0012.  Open with Roger: keep
    Sonnet-first and accept the 4% as review work (about $40 per 10,000 candidates live), or Opus
    alone (about $80).  Also open: dropping line 2's closing clause ("; each adds something the other
    lacks"), which Sonnet now writes under 3s.
11. **Plan of record (Roger, 2026-10-06): Sonnet first, Opus on the 2s and 3s**, one pair per call
    in cosine order, rubric A as pinned.  Decisions, for now: a Sonnet 4 is cut; a Sonnet 3 goes to
    Opus, which decides (cut at 3 or more, kept under); a Sonnet 0, 1 or "opposite" is settled (rule
    9 for "opposite"); **a Sonnet 2 also goes to Opus, but the candidate is kept whatever Opus says**,
    as the cheaper rule ("Opus on the 3s only") would keep it, and where Opus reads 3 or more the
    candidate is marked for manual review (`review: "sonnet_2_opus_3"` or similar on the registry
    row, with both readings and reasons).  The review sample tells which way to go: if Opus is right
    on those pairs, the rule tightens to Opus deciding on the 2s as well (the plan of record's full
    form); if the Opus reading on the 2s earns little, the pipeline shifts to "Opus on the 3s only"
    as a saving (about $40 against $70 per 10,000 candidates, live).  Either way every reading is
    logged, so the rule can be re-run on the records without new calls.
12. **From Roger's review of the pilot (2026-10-07; [m3_pilot_readout.md](./m3_pilot_readout.md),
    "Roger's review"): decision 11's full form is confirmed, and the row's default follows it.**  On
    the 58 review-queue pairs he scored where Sonnet read one below the cut-off and Opus at or above
    it, he sided with Opus on 45 and Sonnet on 13.  So a Sonnet reading one below the cut-off that
    Opus reads at or above it is **covered, flagged for review** (`review: "sonnet_below_opus_at"`
    stays; the decision changes from `grey` to `covered`), not kept.  "Opus on the 3s only" is off the
    table as a saving: it would keep about 10% of candidates that are near-duplicates.
13. **Both ends of a pair similar: neither may cut** (Roger's rule).  When the relation call marks both
    members of a recorded pair `similar`, the candidate is taken to be orthogonal to the pair's axis:
    both ends are removed from the shortlist, the row gets `pair_note: {"pair": [...], "both":
    "similar"}`, and the note is surfaced in review.  Both ends are always listed (the arrangement
    expansion adds the partner of every retrieved pair member), so the rule needs no extra calls.  In
    the pilot it would have changed no decision (ten cases: four kept anyway, six covered by another
    trait).
14. **The pair flag is a note, not a review trigger.**  Both-opposed flags were all harmless on review
    (a candidate in the middle of a scale, or on the other side of a relation, is opposed to both
    ends); `pair_flags` stays on the row for the record, and `grey` is no longer given for it.  With 12
    and 14 the review queue is the `sonnet_below_opus_at` rows (now covered-and-flagged) plus the
    both-similar notes and `unparsed`.
15. **Exact-label stage: `renamed_from` goes to the overlap call; labels compared separator-blind.**
    A candidate whose label is a corpus file's `renamed_from` is judged against the current trait like
    any other (the pilot auto-covered four real gaps: engaging by unflinching, relaxed by unhurried,
    shy by self-conscious, assertive by opinionated); only a corpus stem or queue stem still covers
    without a call.  The comparison ignores separators ("anti feminist" = antifeminist).  Also:
    `full-scan --keys` so chosen candidates can be scanned; the five relation-call corrections not in
    the pilot's scan sample (youthful / immature, trendsetting / fashionable, meandering / erratic,
    self-serving / uncaring, conflict-avoidant / peaceful) go first.  The cosine floor (0.25) remains
    a cost lever for Roger to decide; it is not needed for correctness.
16. **TODO (Roger, 2026-10-07): re-examine the M1 verdict step's model once real generators run.**
    Whichever way the Haiku 4.5 / 5.5 choice goes ([haiku55_readout.md](./haiku55_readout.md)), the
    pools it was decided on are proxies (antonym-check words, random dictionary adjectives, the test
    words); the plan's rule is a model per generator, chosen on that generator's own pilot (the
    "M1 filter: judging model per generator" paragraph above).  When the first generator's output
    exists, rerun the comparison on it (both Haikus, Sonnet, an Opus reference on a few hundred words)
    before fixing the generator's model.
17. **Haiku 5.5 for the gap-filling subproject (Roger, 2026-10-08, on
    [haiku55_readout.md](./haiku55_readout.md)).**  Every Haiku call of the subproject moves from Haiku
    4.5 to `claude-haiku-5-5`: the M1 verdict step with three readings and the asymmetric rule (turned
    away only if all three readings agree, otherwise the majority), the gloss and alignment steps, the
    states pass, the plain-reading check, the M2 paraphrase check, and the M3 relation call.  The
    overlap call stays Sonnet first, Opus second.  Measured: a tenth of the price per token, the gloss
    better scoped where the corpus's sense is specialised, the relation call upheld 82% of the time
    against 4.5 by blind judges, the verdict step with three readings about a fifth fewer weighted
    errors than 4.5 (more than half fewer on near-corpus words).  Build: [coding_plan_haiku55.md](./coding_plan_haiku55.md),
    "The switch".  Decision 16's re-examination on real generator output stands.

## Interface as built (2026-10-08, Fable; replaces the scorer side of "Frozen interface")

What a generator, a test harness or a later milestone can rely on, as the code stands at commit
a0a4e09 on `anthropic-vllm-uv`.  Tasks 20-25 of the checklist above are reconciled at the end.

### The registry API (built as frozen; `assistant_axis.gapgen` exports it)

- `Candidate(surface, generator, run_id, rank=None, score=None, gloss_hint=None, sense_id=1,
  source_ref=None, partner_hint=None)`: one word or phrase a generator proposes.  `surface` as emitted;
  the registry normalises it to a stem and label.  `score`, where it is a documented human familiarity
  figure, is read by the filter (interface resolution 4).
- `start_run(generator, run_id, *, args=None) -> RunContext`: opens `data/candidates/runs/<generator>/<run_id>/` (corrected 2026-10-08: the path has `runs/`)
  and a `RunContext` with `.log(msg)`, `.usage` (a `MultiModelUsage`), `.args`, `.n_emitted`;
  `ctx.finish(n_emitted=...)` writes `run.json` and `usage.json` (always, even with zero calls).
- `submit_candidates(cands, *, registry_path=REGISTRY_PATH, ...) -> SubmitReport(n_submitted, n_new,
  n_merged, n_unchanged, keys, invalid)`: appends to the log, idempotent per
  (generator, run_id, surface, sense_id); two candidates of one run with the same key are merged.
- **The registry log `data/candidates/registry.jsonl` is git-ignored** (interface resolution: registry
  tracking); the compacted `registry.snapshot.jsonl` is tracked.  So the log is per checkout.  **A
  generator therefore also writes every `Candidate` it submits to a tracked `candidates.jsonl` in its
  run directory**, one JSON object per line in `Candidate`'s fields, so the run can be resubmitted into
  any checkout's log with `gap_registry.py submit --from <run_dir>/candidates.jsonl` (idempotent).
  Parallel generator worktrees submit locally and are resubmitted into the main checkout afterwards.

### Running the platform over a generator's rows (the CLIs, as they exist)

- **M1**: `traithood_filter.py --batch-id B --run GENERATOR/RUN_ID --pipeline split [--transport
  live|batches] --budget-usd C`: the split filter on the run's rows not yet filtered; Haiku 5.5 with
  three readings by default (decision 17), the 10% Sonnet second opinion and the disagreement tripwire
  (`--max-disagreement`, `--accept-disagreement` on resume), writes the `filter` block (verdict, tags,
  gloss, alignment score, region) on each row and `data/candidates/filter/<B>/`.
- **M3**: `novelty_score.py score --batch-id B --run GENERATOR/RUN_ID [--transport live|batches]
  --budget-usd C`: on the run's rows with verdict `trait`, writes the `novelty` block and
  `data/candidates/novelty/<B>/` (`results.jsonl`, `readings.jsonl`, `decisions.md`, `summary.json`).
  Other subcommands: `full-scan`, `compare`, `score --redecide [--write-registry]`, `promote-redecide`,
  `decisions`, `review-list`, `pools`.
- **Registry**: `gap_registry.py submit | status | report | holding | judgement-calls | judgement-call |
  corpus-regions | synonyms | compact | promote`; promotion into `data/seed_queue.json` only by the
  explicit `promote` command.

### The row's blocks (what a test reads)

`filter`: `pipeline`, `model`, `gloss_model`, `batch_id`, `verdict` (`trait` | `tagged` | `reject`),
`outcome` (`trait` | `states` | `physical` | `roles` | `turned_away` | ...), `tags`, `membership_kind`,
`sense` (readings), `same_sense`, `verdict_readings` (when more than one reading), `rule`, `cause`; the
gloss, alignment score and region beside it.  `novelty`: `run_id`, `mode`, `decision` (`covered` |
`new` | `grey`), `reason`, `covered_by`, `exact_label`, `review`, `review_details`,
`pair_completion_for`, `pair_flags`, `pair_notes`, `cut_off`, `alignment_score`, `region`,
`deciding_reading`, `readings` (every pair judged: stem, cosine, relation, sonnet, opus, outcome),
`n_pairs_judged`, `listed`, `shortlist`, `relation`, `rubrics`, `rules`, `config_version`,
`embedding`, `usage`, `at`, and `redecided_from` on a re-decided block.

### The recovery harness (plan 13's core, re-specified; built by the close-out job below)

`recovery_test.py --generator G --run-id R --hidden-frac 0.1 --seed S [--transport live|batches]
--budget-usd C` and the library `assistant_axis/gapgen/recovery.py`:

1. **Hide**: draw a fraction of the corpus's trait stems (default 0.1), seeded, stratified by region
   where `corpus_regions.json` has one, **adding every arrangement partner of a drawn trait** (pairs,
   triangles, tetrahedra hidden together; a sequence member hides alone); write `hidden.json`.
2. **Score against the reduced corpus**: run M3 on the generator run's rows with the hidden stems
   removed from retrieval, expansion and the exact-label check (`--hide <hidden.json>` on `score`, a
   small change: the index is built without them), into its own batch id, writing nothing to the
   registry (as `full-scan` does).  Rows already filtered by M1 are reused; M1 does not change.
3. **Match**: for each candidate the reduced-corpus M3 decided `new` or `grey`, and for each hidden
   trait, a hidden trait is **recovered** by the candidate when the candidate's normalised label equals
   the hidden stem (or its `renamed_from`), or when the overlap call (rubric A, one pair per call,
   Sonnet then Opus under the pipeline's rule, the candidate's gloss against the hidden trait's
   description) reads at the candidate's cut-off or above.  To keep this cheap, only the hidden traits
   among the candidate's 10 nearest by cosine (against the full corpus) are judged.
4. **Report** `recovery_report.json` and `.md`: hidden traits recovered (recall), by region and by
   arrangement kind; candidates that recovered something (precision of the generator's "new"s against
   the hidden set); pairs recovered whole; cost; and the same figures for the generator's candidates
   decided `covered` against the reduced corpus (false covers caused by the hiding).  Two seeds by
   default; the report gives both and their mean.  Chao2 / Chapman saturation estimates (plan 13 § 3)
   are a later addition, not this job.

**As built (2026-10-08, close-out job, commits d238ca4 to 070de2c).**  `recovery_test.py --generator G --run-id R
[--hidden-frac 0.1] [--seed S ...] --budget-usd C [--transport auto|live|batches] [--batch-id B] [--dry-run | --resume]`;
seeds default to 0 and 1, the batch id to `rec_<G>_<R>`, outputs under `data/candidates/recovery/<B>/` with the
reduced-corpus M3 run under `data/candidates/novelty/<B>_s<S>/`.  The run must be in the checkout's registry with M1
blocks; the harness does not need the run's own M3 result.  One deviation from step 1: the draw takes whole
arrangement groups until each region's quota is met (so every trait has the same chance of being hidden; 83 of 790
at 0.1), instead of drawing stems and adding partners, which would hide about 17% and pair members twice as often.
The match stage has no cosine floor.  Live check on `antonym_check/pilot_1`, seed 0, $4.87: recall 13 of 83
(all pair members; 2 by label through `renamed_from`, 11 by overlap call), precision 17 of 162 kept candidates, 16
false covers (the hiding made another trait cover 14 hidden ones; recall counting those would be 32.5%); report
[recovery_report.md](../../data/candidates/recovery/rec_antonym_check_pilot_1/recovery_report.md).  `gap_registry.py
submit --from <run_dir>/candidates.jsonl` reads the file as `Candidate(**row)` (the older `--file` form reads only
some fields); `submit_candidates(run=ctx)` records before it appends; `run.log` is git-ignored.

### Checklist tasks 20-25, reconciled

20-21 (`novelty.py`, `adjudicate.py`): built in redesigned form (novelty.py, novelty_runner.py, the
relation and overlap rubrics).  22 (`recovery.py` + `recovery_test.py`): **not built**; the close-out
job.  23 (`novelty_score.py`): built, with the subcommands above.  24 (calibration replay, pilot):
done as the M3 pilot and round 2.  25 (freeze and the AGENT_NOTES paragraph): **not done**; the
close-out job exports the as-built names and writes the paragraph.

## Close-out job (brief for one Opus agent, 2026-10-08; Roger: "build the recovery harness as a platform close-out before the first generator")

In the existing worktree, after `git merge --ff-only anthropic-vllm-uv`:

1. **The recovery harness** exactly as specified above: `recovery.py` (hide, match, report), the
   `--hide` option on `novelty_score.py score` (the index, expansion and exact-label check without the
   hidden stems; a run with `--hide` never writes the registry and records the hidden file's path and
   hash), `recovery_test.py`, and a `candidates.jsonl` reader for `gap_registry.py submit --from`.
   Tests with the fake clients and the toy corpus: a hidden pair hides whole; a candidate whose label
   is a hidden stem is recovered without a call; a candidate recovered by the overlap call; a
   candidate decided covered by a non-hidden trait is not matched; the report's counts; `--hide`
   leaves the registry untouched.  Then a **live check on the pilot's rows**: hide 10% with seed 0,
   run the harness over `antonym_check/pilot_1` (the rows already have M1 blocks; M3 reruns against the
   reduced corpus, about $5; cap $8), and report what it recovered.  The antonym-check words are
   near-corpus, so recall should be well above zero; say what it is.
2. **The interface freeze**: `assistant_axis/gapgen/__init__.py` exports the as-built names (the
   registry API as now, plus `MetricConfig`, the paths, and the recovery entry points); the file's
   docstring lists them with one line each; a test that the exports exist and nothing named in the
   superseded scorer interface is exported.
3. **AGENT_NOTES paragraph** "Trait-gap platform" under the `trait-pairs` rule (edit `AGENT_NOTES.md`
   with the Edit tool, then `uv run python tools/sync_agent_notes.py`; if the sandbox refuses the
   sync's writes under `.claude/`, say so and leave it to Fable): what the platform is, the three
   milestones, where the plans and readouts live, the registry log's per-checkout nature, the model
   defaults (decision 17), the expensive-operations rule's application, and the `candidates.jsonl`
   convention.  Two short paragraphs, hotlinked as the notes require.
4. **The three Haiku left-overs**: cache the split filter's system prompts that exceed 512 tokens on
   Haiku 5.5 (the sense and kind rubrics; measure the hit rate on the live check); the estimate's
   proportions (primary readings per word, same-sense share, second-opinion share, unsure re-ask
   share) measured per model from the recorded runs; the "Model" header lines of the rubric files
   that still name Haiku 4.5 updated to the defaults (a header edit, not a prompt edit: the pins do
   not change; verify with `rubric_pins.py check`).
5. **Report**: commits, the harness's live-check recall and cost, the exports, the sync's outcome, test
   counts, changed expectations.  Constraints as in [coding_plan_m3.md](./coding_plan_m3.md)'s last
   section.
