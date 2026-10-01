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
