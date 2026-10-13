# Coding plan: workstream 3, base-model generator (generator id `base_model`)

Written 2026-10-10 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[03_base_model_generator.md](./03_base_model_generator.md) and Roger's § 9 answers and § 4 edit
(2026-10-10 greenlight), against the "Interface as built" section of
[coding_plan_platform.md](./coding_plan_platform.md).  The generator samples a local
*pretrained* (non-instruction-tuned) model for person-description continuations, parses trait
candidates out of them, and submits them to the registry; M1 and M3 are the platform's CLIs.
Roger's review comments go into this file.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Mac-first with `Qwen/Qwen3-8B-Base`, bf16 on MPS via `transformers`; RunPod / OpenRouter are a **documented contingency, not built now**.  If OpenRouter is ever used, the western-hosts-only hard rule applies unchanged: hosts' countries checked first, host pinned, `allow_fallbacks: false` ([CLAUDE.md](../../CLAUDE.md) § "Hosted models: western hosts only, and keys stay unseen"). | Roger § 9.3: "I'd expect Mac-runnable models to be fine here"; escalation only "if we find writing quality or vocabulary is a problem" | plan 03 § 9.3; CLAUDE.md |
| `wiki_bio` is accepted as a seed source.  Seeds are **prompts only, never redistributed**: the raw dataset stays under gitignored `data/external/`; no tracked file (candidates table, `candidates.jsonl`, readouts) carries biography text; provenance records the seed by reference (`wikibio:<split>:<index>`); raw generations (which may echo seed words) are gitignored. | Roger § 9.1: "IANAL, but sounds fine to me" (CC BY-SA 3.0) | plan 03 § 9.1 |
| The AI-assistant prompt family is **in**, as one family (`ai_assistant`) beside the others, with its yield, M1 verdict fractions and alignment scores reported **separately** in the pilot so Roger can drop it. | Roger § 9.2: "Let's try it, and see" | plan 03 § 9.2 |
| Nouns of disposition: v1 applies only the **mechanical** rule (`-ness`/`-ity` → the adjective, only when OEWN has that adjective); every candidate is form-tagged (`adjective` / `noun` / `phrase`) and the pilot **measures the noun share** of uniques and of M1 survivors.  An LLM normalization step (Haiku 5.5 or a local model) is specced as a follow-up task gated on that number, **not built in v1**. | Roger § 9.4: "TBD, do it if we find this is a significant issue and the increased yield would be worth the coding" | plan 03 § 9.4 |
| The pilot includes **one bounded prompt/seed iteration round**: after the first 2k-sample readout, one revision of the prompt wordings, seed mixes and constraints (data edits in `prompts.py` only, `PROMPTS_VERSION` bumped), a 2k resample, and the free diversity measures recomputed.  Both rounds go to Roger; further rounds are his call.  No paid calls are spent on the discarded round. | Roger's § 4 edit: the known biases "are fixable by varying the prompts and seeds" | plan 03 § 4 |
| **Sampling is local and $0**; M1 and M3 are `traithood_filter.py --run base_model/<R>` and `novelty_score.py score --run base_model/<R>`.  The local model's token counts are still charged to `RunContext.usage` at a zero rate so `usage.json` records the volume.  The generator's **one** paid call is the gloss-sense step ([QUESTIONS 56](./QUESTIONS.md), Roger 2026-10-11): hundredths of a cent for each row whose two glosses diverge, recorded in its own cumulative `gloss_sense_usage.json` beside the round's samples. | frozen interface; the token-logging hard rule | platform § "Interface as built"; [provenance rule](../../.claude/rules/provenance.md) |
| Registry API only: `Candidate`, `start_run`, `submit_candidates`; every run writes a tracked `candidates.jsonl` before submitting (the log is per checkout). | as built | platform § "Interface as built" |
| Frequency flags come from [`gapgen.freq.zipf_info`](../../assistant_axis/gapgen/freq.py) (`hard_reject` below [Zipf](./glossary.md#zipf) 1.5, `probe_band` 1.5–2.5), **never a local literal**; no SUBTLEX download (plan 03 § 3.6's threshold is superseded by the platform's). | stale local defaults caused the B=10 incident; [decisions_m1.md](./decisions_m1.md) decision 1 | plan 14; QUESTIONS 42 |
| Corpus and queue membership are computed into the table **for evaluation only**; eligibility never reads them, and no prompt ever contains a corpus label or description (the generator "cannot see or imitate our list"). | independence is the workstream's premise | plan 03 § 1; censuses precedent |
| **Words that are already corpus trait names stay in the run** — no selector drops them. | Roger, 2026-10-10: "let the pipeline do its job" | [coding_plan_01_censuses.md](./coding_plan_01_censuses.md), last section |
| A generation wave runs **M1 + M3 only**; grouping/review (R1) runs once at the end over every batch, not here. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| `gloss_hint` is the OEWN person-descriptive sense where OEWN knows the word (reusing the censuses' [`glosshint`](../../assistant_axis/gapgen/generators/censuses/glosshint.py) sense-picking), else `None`.  The base model's own gloss (the "{word}: gloss" list format) is kept in the tracked table as `sample_gloss`.  **Where a row has both, the sense is resolved before M1** ([sense.py](../../assistant_axis/gapgen/generators/base_model/sense.py)): divergence is flagged by the cosine between the two gloss texts (free, a local embedder), each divergent row is settled by one Haiku 5.5 call asked which reading a reader of the sample would take, and `submit` refuses while any selected row is unsettled.  Criterion: **fidelity first, subject to legibility, never novelty**. | a gloss changed after M1 or M3 invalidates their verdicts; choosing the gloss that scores better against the corpus would be selecting our own answer | Roger, [QUESTIONS 56](./QUESTIONS.md), 2026-10-11 (provisional, with a TODO to revisit keeping both senses through `Candidate.sense_id`) |
| Contrast-family candidates carry `partner_hint` = the seed adjective they were generated against; M3's relation call and the pairing track do the rest. | the interface has the field; M3 decision 9 routes "opposite" | platform interface resolution 02-1 |
| Sampling defaults: T = 1.0, top-p 0.95, min-p 0.05, no repetition penalty, 80 new tokens, stop at a blank line; a T ∈ {0.8, 1.0, 1.2} shakedown (500 samples each, free) picks the production T before the pilot. | plan 03 § 3.3 | plan 03 |
| Code in a subpackage `assistant_axis/gapgen/generators/base_model/`; generator worktrees run in parallel. | layout precedent | coding plan 01 § 1 |
| Corpus counts for evaluation, counted 2026-10-10: **932 trait files, 340 role files, 296 reciprocal pairs**.  Plan 03 § 6's "our 367 labels" is stale; the recovery denominator is the current stems (plus `renamed_from`). | count the corpus, don't trust stale numbers | task brief |

## 2. Out of scope

- Any edit to `data/traits/**`, `data/roles/**`, `TRAITS_TO_ADD.md`, `ROLES_TO_ADD.md`,
  `data/seed_queue.json` (promotion is `gap_registry.py promote`, Roger's decision).
- Anything the platform owns: rubrics, M1/M3 internals, thresholds, `metric_config.json`, the
  review app and `review_graph.py` (R1 runs once at the end, per
  [coding_plan_review.md](./coding_plan_review.md) § 10).
- The LLM noun-normalization pipeline (follow-up task, gated on the pilot's noun share — § 9 task 11).
- RunPod or OpenRouter client code, vLLM paths, `mlx-lm`; `Qwen3-14B-Base` and larger.
- Variant B (OLMo-2-7B / Mistral-7B-v0.3 as a purer-base control): a contingency if variant A's
  rarefaction curve flattens early; nothing is downloaded or coded for it now.
- The Message Batches API inside the generator (the generator makes no paid call; M1/M3 own `--transport`).
- Plan 04 (masked-LM fill), 05 (corpus frames), 06 (LLM entropy generation).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[`.claude/rules/provenance.md`](../../.claude/rules/provenance.md) (usage.json on every batched call site; `json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[`.claude/rules/entity-naming.md`](../../.claude/rules/entity-naming.md) (`normalize_to_file_name` stems; US English; display forms at display sites only),
[`.claude/rules/trait-pairs.md`](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are),
[`.claude/rules/judging.md`](../../.claude/rules/judging.md) (this workstream runs M1 and reads its parse rate; `*** HIGH FAIL RATE ***` blocks the stage),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, tests mandatory, hotlinks, **western hosts only**).
No PNGs are planned (the rarefaction readout is a table; if a plot is added, Read the plotting rule first).

**File-access boundary** (restate in every Opus task prompt, per [PLAN_FORMAT.md](./PLAN_FORMAT.md)):
read and write only inside the repository and the agent's own scratchpad; never list, read or stat
anything under the home directory outside it — **including any cache, and including "just checking
whether a model or dataset is already downloaded"**.  Every download goes to `data/external/`
inside the repo, and only after Roger's word (§ 5a).

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate` (with `partner_hint`), `start_run`,
  `submit_candidates`, `SubmitReport`, `RunContext` ([paths.py](../../assistant_axis/gapgen/paths.py):
  `DATA_EXTERNAL`, `DATA_CANDIDATES`, `run_dir`, `check_id`, `hf_cache_dir()`).
- [`gapgen/cost.py`](../../assistant_axis/gapgen/cost.py): `confirm_or_abort`, `HARD_LINE_USD`;
  [`gapgen/freq.py`](../../assistant_axis/gapgen/freq.py): `zipf_info` (floor 1.5, probe band to 2.5);
  [`gapgen/wordnet.py`](../../assistant_axis/gapgen/wordnet.py): `ensure_oewn`, `wn_data_dir()`.
- Censuses generator, as pattern and as import:
  [`load_census_table`](../../assistant_axis/gapgen/generators/censuses/__init__.py) +
  `CENSUS_TABLE_PATH` (the frozen interface: **seed list A is the TDA rows of the census table**,
  familiarity `prop` as the "too rare for the model" filter — no new download);
  [`glosshint.py`](../../assistant_axis/gapgen/generators/censuses/glosshint.py) (`adjective_senses`,
  `person_sense` for the OEWN hint); [`submit.py`](../../assistant_axis/gapgen/generators/censuses/submit.py)
  (the `Estimate` / `confirm_or_abort` / `followup_commands` / `_budget` pattern and the **measured
  platform rates**: M1 $0.0072/word, M3 $0.011/passed word, batches ×0.5, from
  [overnight_readout_2026-10-08.md](./overnight_readout_2026-10-08.md) § 6).
- [`setup_external.py`](../../data_analysis/gap_generation/setup_external.py) `--hf-model ID`
  (pre-fetches an HF model into `data/external/hf/`, where `models--google--embeddinggemma-300m`
  already lives — the destination pattern for Qwen3-8B-Base).
- [`seed_entities.py`](../../data_analysis/seed_entities.py): `corpus_stems`, `load_queue`,
  `build_registry` (evaluation only); [`entity_id.py`](../../assistant_axis/entity_id.py):
  `normalize_to_file_name`, `resolve_renamed_stem`; [`atomic_io.py`](../../assistant_axis/atomic_io.py);
  [`judge_pricing.py`](../../assistant_axis/judge_pricing.py): `MultiModelUsage` (+ add a zero-rate
  entry for the local model tag, as was done for the local embedders);
  [`provenance.py`](../../assistant_axis/provenance.py) + `json_metadata` for the stats envelope.
- Test style: `assistant_axis/tests/test_gapgen_censuses_*.py` (fake clients, tmp registry,
  `GAPGEN_RUN_LOCAL=1` guard for anything that loads a real model).

Dependencies: none added.  `torch>=2.0` and `transformers>=4.40` are main dependencies;
`huggingface_hub` and `pyarrow` are already in `uv.lock` (wiki_bio is fetched as parquet shards via
`hf_hub_download` and read with pyarrow — the `datasets` package is **not** added).

## 5. File layout

```
assistant_axis/gapgen/generators/base_model/
  __init__.py    GENERATOR = "base_model"; BASE_DIR = DATA_CANDIDATES / "base_model";
                 TABLE_PATH = BASE_DIR / "candidate_table.jsonl"; STATS_PATH; SAMPLES_DIR =
                 DATA_CANDIDATES / "cache" / "base_model"  (gitignored via /data/candidates/cache/);
                 re-exports the diversity harness (§ Frozen interface)
  sources.py     Source entries for wiki_bio (HF parquet shards) and the O*NET occupation titles,
                 with URL/repo id, dest under data/external/, size, license, citation; SKIPPED
                 (PersonaHub: LLM-generated, already mode-collapsed; SUBTLEX: wordfreq covers it)
  download.py    fetch_wiki_bio(dest=DATA_EXTERNAL/"wikibio", fetcher=..., dry_run) -> manifest;
                 fetch_onet(dest=DATA_EXTERNAL/"onet", ...); write/load_manifest  (the model itself
                 goes through setup_external.py --hf-model; nothing here downloads without Roger's word)
  seeds.py       SeedBundle(adjectives, bios, occupations, nouns, constraints);
                 load_seed_bundle(*, census_table, wikibio_dir, onet_dir, familiarity_floor=0.5, rng)
                 adjectives: TDA rows of load_census_table() with prop >= floor;
                 bios: iterator of (ref, name, first_words(<=200)); occupations: O*NET titles;
                 nouns: OEWN common nouns (wn, data dir = wn_data_dir()); draw_*(rng) seeded
  prompts.py     PROMPTS_VERSION = 1; FAMILIES = ("list", "list_gloss", "person", "contrast",
                 "occupation", "ai_assistant"); render(family, bundle, rng) -> Prompt(text, family,
                 seeds, seed_refs, constraint, header_variant, sha256); 10 header wordings per family;
                 entropy injection (2-3 seed words + one random constraint) in every prompt
  sampler.py     SampleBackend protocol; HFBackend(model_dir, device="mps", dtype=bf16, batch_size);
                 run_sampling(backend, plan, *, out_path, usage, resume) -> SampleStats
                 (T, top-p 0.95, min-p 0.05, 80 new tokens, stop at blank line; appends JSONL,
                 checkpointed per batch; charges prompt+completion tokens to usage at $0)
  bench.py       benchmark(backend, *, batch_sizes=(32, 64)) -> tok/s table (the Mac/pod decision: >150 tok/s aggregate)
  parse.py       extract_items(text, family) -> list[RawItem]  (split on commas/newlines/"and";
                 1-4-word spans; lowercase; strip determiners; drop digits/non-Latin);
                 normalize_form(surface, *, lexicon) -> (surface, form, normalized_from)
                 (-ness/-ity -> adjective only when OEWN has it; tag adjective|noun|phrase)
  table.py       build_table(samples, *, freq=zipf_info, senses, corpus_stems, queue_stems) -> rows;
                 write_table / load_table  (dedupe by stem; counts per family; eligibility; rank;
                 n_name_echo / n_bio_span_echo apart, the dropped name word logged, and
                 name_echo_not_elsewhere = what the name rule really cost: QUESTIONS 54)
  sense.py       GLOSS_SENSE_VERSION; cosine_rows(rows, embed) -> {stem: cosine};
                 screen(rows, cosines, floor=DIVERGENCE_COSINE) (free; agreement needs no call);
                 request / parse_answer / decide (fidelity subject to legibility);
                 resolve_rows(rows, client|send, usage) -> one Haiku 5.5 call a divergent row;
                 resolved_hint(row) (what the Candidate carries); unresolved(rows) (what submit refuses on)
  diversity.py   rarefaction(stems_in_order, step=1000); chao1(counts); collapse_index(counts, top=50);
                 string_recovery(stems, corpus_stems, renamed) ; per_family(rows)   (§ Frozen interface)
  submit.py      M1_USD_PER_WORD = 0.0072; M3_USD_PER_PASSED_WORD = 0.011; M1_PASS_RATE_ASSUMED = 0.80
                 (the two least-curated measured waves: roget pilot 81.4%, alignment sweep 78.6%), with
                 M1_PASS_RATE_HIGH = 0.95 printed beside it as a high case and never gated on
                 (QUESTIONS 55); estimate_downstream_usd(n, transport);
                 to_candidates(rows, run_id); run_submit(run_id, *, table, budget_usd,
                 confirm_expensive, confirmed_by, transport, dry_run); followup_commands
  evaluate.py / report.py   pilot readout: yields, collapse, noun share, family split, recovery,
                 M1/M3 fractions from the batch dirs, cost from the usage.json files
data_analysis/gap_generation/base_model_generator.py   fetch | bench | sample | parse | stats | submit | report
data/external/{wikibio/, onet/}                        GITIGNORED (+ DOWNLOAD_MANIFEST.json each)
data/external/hf/models--Qwen--Qwen3-8B-Base/          GITIGNORED (via setup_external.py)
data/candidates/base_model/{candidate_table.jsonl, stats_round<N>.json}   tracked (table expected ~1-2 MB)
data/candidates/cache/base_model/round<N>/             GITIGNORED: samples.jsonl (raw generations; may echo
                 seed text), sampling.json, usage.json, sample_stems.jsonl, table_counts.json,
                 gloss_sense_responses.jsonl, gloss_sense_usage.json
data/candidates/runs/base_model/<run_id>/{candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json}
assistant_axis/tests/test_gapgen_base_model_{seeds,prompts,sampler,parse,table,sense,diversity,submit}.py
assistant_axis/tests/fixtures/base_model/{wikibio_small.parquet, onet_small.txt, samples_small.jsonl, census_table_small.jsonl}
data_analysis/tests/test_gap_generation_base_model_cli.py
```

### 5a. Downloads — the first three approved (Roger, 2026-10-10, below); the optional one needs a fresh ask

| item | what / where from | size (approx.) | license | destination |
|---|---|---|---|---|
| **`Qwen/Qwen3-8B-Base`** — approved; **TODO once the workstream is done: ask Roger whether to delete the weights** (his rule, 2026-10-10: anything over 2 GB gets this note) | HF model snapshot, via `setup_external.py --hf-model Qwen/Qwen3-8B-Base` | **~16.4 GB** bf16 | Apache-2.0 (plan 03's note "licenses from memory" — verified on the HF page at download, recorded in the manifest) | `data/external/hf/` |
| **`wiki_bio`** | HF dataset, parquet shards via `hf_hub_download` | **~300-400 MB** (not verifiable from inside the repo; the fetch prints the exact size before writing) | CC BY-SA 3.0 — seeds as prompts only, never redistributed (Roger § 9.1) | `data/external/wikibio/` |
| **O*NET occupation titles** | the Occupation Data file from onetcenter.org, version recorded | **~1 MB** | public domain | `data/external/onet/` |
| *optional:* `Qwen/Qwen3-8B` (instruct) | the collapse control of plan 03 § 6 (same prompts at T=1, pilot scale only) | ~16.4 GB | Apache-2.0 | `data/external/hf/` — **only if Roger wants the control**; otherwise the comparison is dropped and said so in the readout |

Seed list A (trait adjectives) needs **no download**: it is the TDA rows of the tracked
[census_table.jsonl](../../data/candidates/censuses/census_table.jsonl), read through the censuses'
frozen interface, with the `prop` familiarity column as the rarity filter.  Common nouns come from
OEWN, already in `data/external/wn/`.

**Roger:** First three downloads approved; ask me if and when you get to the optional one (it's large, we might want to delete it again once done with it). The things over 2GB we should add a TODO note asking if we can delete them once we're done with them.

## 6. Data schemas

**Raw sample** (`samples.jsonl`, gitignored; one line per generation):

```json
{"sample_id": "A-000412", "round": 1, "family": "person", "prompt_sha256": "9c4e...", "prompts_version": 1,
 "seed_refs": ["wikibio:train:581204"], "seed_words": [], "constraint": "a fault, not a virtue",
 "header_variant": 3, "temperature": 1.0, "text": "stubborn, fiercely loyal to her crew, and ...",
 "n_prompt_tokens": 214, "n_new_tokens": 61, "stop_reason": "blank_line", "model": "Qwen/Qwen3-8B-Base"}
```

**Candidate table row** (`candidate_table.jsonl`, tracked; one per distinct stem; no biography text):

```json
{"schema_version": 1, "surface": "unflappable", "stem": "unflappable", "form": "adjective",
 "normalized_from": null, "count": 17, "families": {"list": 9, "person": 5, "contrast": 2, "ai_assistant": 1},
 "first_sample_id": "A-000412", "sample_gloss": "staying calm when everything goes wrong",
 "zipf": 2.91, "freq_hard_reject": false, "freq_probe_band": false, "in_oewn": true, "in_tda": false,
 "wordnet": {"n_adj_senses": 1, "person_sense_rank": 1, "definition": "not easily perturbed or excited"},
 "gloss_hint": "not easily perturbed or excited", "partner_seed": null,
 "eligible": true, "ineligible_reason": null, "rank": 122,
 "corpus_stem_match": false, "queue_stem_match": false}
```

A row whose `gloss_hint` and `sample_gloss` both exist also carries, after the `sense` step, a
`gloss_sense` block: `{"oewn", "sample", "cosine", "divergent", "floor", "embedder", "chosen":
"dictionary" | "sample" | null, "chosen_gloss", "legible", "reason", "model", "prompt_version",
"prompt_sha256", "at"}` (plus `note` where legibility overrode fidelity, `error` where the call
failed).  `gloss_hint` itself is never rewritten — it is always the dictionary's — and the submitted
candidate carries `sense.resolved_hint(row)`, which is the chosen one.

Rules: `stem = normalize_to_file_name(surface)`; `eligible = cleaned ∧ ¬unknown_word ∧
¬freq_hard_reject` where `unknown_word` means neither `wordfreq` nor OEWN knows every token (the
censuses' concept); the flags come from `zipf_info`, never a literal; `rank` orders by `count`
descending, ties by first appearance, so recall-versus-rank curves read naturally;
`corpus_stem_match` / `queue_stem_match` are **evaluation-only** (a mutation test flips them and no
`eligible` changes).  `partner_seed` is set on contrast-family rows (the seed adjective the model
contrasted against) and becomes `Candidate.partner_hint`.

**Rule 1b, the folds and the count floor (2026-10-12, gate audit 3;
[base_model_table.md](../code_review_2026-10-12/gate_audits/base_model_table.md)).**  `zipf_info` gets the row's OEWN gloss hint, so a word
below the line is rescued by its negating prefix or its hint (`freq_rescue` on the row; counts `freq_rescued`
and `normalized_by`), and `unknown_word` is set only when no rescue applies.  `parse.py` folds `-ly` adverbs,
more noun suffixes (-ence, -ancy, -acity, -ism, ...) and British spellings to the OEWN adjective, keeps a fold
only when OEWN has the result, and no longer takes `etc`, `others`, a leading `be` or a frequency adverb as an
item.  The count floor is **2** (`DEFAULT_MIN_COUNT`, chosen at 2,000 samples; `run.json` and
`submit_report.json` record it as `floor` with the table's sample size, and a table of another size gets a
NOTE): the pilot ran at 8, which discarded 88% of the eligible rows, about half of them trait words.  The
estimate the gate reads counts only the rows that need M1 or M3 (`downstream_need`; `estimate_all_rows`
keeps the all-rows figure), and `report.md` adds a by-family readout before the floor.

**Candidate emitted**: `Candidate(surface="unflappable", generator="base_model", run_id="2026-10-14a",
rank=122, score=17.0, gloss_hint=<OEWN hint>, sense_id=1, source_ref="base_model:person:A-000412",
partner_hint=None)`.  `score` is the raw emission count — **not** a human familiarity, so
`base_model` is *not* added to `FAMILIARITY_GENERATORS` in
[freq.py](../../assistant_axis/gapgen/freq.py) and no Zipf rescue applies.

**Diversity stats** (`stats_round<N>.json`, tracked, in a `json_metadata` envelope; numbers illustrative):

```json
{"round": 1, "prompts_version": 1, "n_samples": 2000, "n_raw_items": 15840, "n_unique": 2120,
 "n_eligible": 910, "uniques_per_1k_samples": 1060,
 "rarefaction": [[1000, 1310], [2000, 2120]], "chao1": 5230, "collapse_top50_share": 0.11,
 "noun_share_unique": 0.19, "noun_share_eligible": 0.14, "normalized_mechanically": 96,
 "per_family": {"ai_assistant": {"n_samples": 280, "n_unique": 240, "uniques_per_1k": 857}},
 "recovery_strings": {"n_corpus": 932, "found": 301, "recall": 0.323, "by_family": {"person": 0.21}},
 "temperature": 1.0, "model": "Qwen/Qwen3-8B-Base"}
```

Terms, defined here and to be added to [glossary.md](./glossary.md) (§ 9 task 6): a **rarefaction
curve** plots distinct candidates against samples drawn, so a flattening curve says the prompts are
running out of new words; **Chao1** estimates the total vocabulary reachable from the counts of
words seen once and twice; the **collapse index** is the share of all emissions taken by the top 50
candidates (target < 15%, plan 03 § 6 — high means the model repeats a cliché set).
**Recovery-by-string** is the free recovery check of plan 03 § 6: the fraction of the corpus's 932
trait stems (or their `renamed_from`, via `resolve_renamed_stem`) that appear among the candidates;
it never feeds eligibility.

## 7. CLI

`data_analysis/gap_generation/base_model_generator.py`; common flags `--dry-run`, `--seed`,
`--round N`, `--table PATH`.  No command downloads, samples or submits anything in dry-run.

- `fetch [--only wikibio|onet] [--dry-run]`: fetches § 5a's datasets into `data/external/`, writing
  a manifest (URL, size, sha256, license, date).  Refuses to run until the plan's § 5a has Roger's
  approval recorded (`--approved-by 'Roger, <date>'`, copied into the manifest).  The model itself:
  `setup_external.py --hf-model Qwen/Qwen3-8B-Base`, same approval.  Dry-run prints sources and
  destinations only.  $0 API cost (bandwidth only).
- `bench [--batch-sizes 32,64]`: loads the model on MPS, measures aggregate tokens/s at 80 new
  tokens, prints the Mac-or-escalate reading (> 150 tok/s stays on the Mac, plan 03 § 3.1).
- `sample --n 2000 [--families list,person,...] [--temperature 1.0] [--t-grid 0.8,1.0,1.2 --per-t 500]`:
  renders prompts (fresh seeds per sample, families interleaved by fixed weights, `ai_assistant`
  deliberately oversampled per plan 03 § 3), runs the sampler, appends to the round's
  `samples.jsonl`, resumes from a checkpoint, charges tokens to a `MultiModelUsage` at the zero
  rate and writes `usage.json` beside the samples.  $0.
- `parse [--round N]`: builds `candidate_table.jsonl` from the round's samples (snapshot the old
  table to `.bak.<UTC>` when content changes), and saves its own counts (the echo split and the
  per-family figures, which are counted over the samples and cannot be recovered from the table)
  as `table_counts.json` in the round directory, which `stats` reads.  A reparse carries each
  gloss-sense decision forward onto the row it belongs to while its two glosses are unchanged, so it
  never throws away what the `sense` step paid for.  Deterministic; rerun is byte-identical.  $0.
- `sense [--round N] [--arm bge|gemma|openai|hash] [--divergence-cosine 0.6] [--budget-usd 2]`:
  settles the gloss sense of the rows that carry two (§ 1, QUESTIONS 56).  Free cosine screen with
  a local embedder, then one Haiku 5.5 call for each divergent row, the decision written onto the
  row with both glosses, the cosine and the reason; `gloss_sense_responses.jsonl` and a cumulative
  `gloss_sense_usage.json` beside the round's samples.  Resumable and idempotent: a row that
  already carries a current decision is neither re-embedded nor re-asked.  Hundredths of a cent a
  divergent row.
- `stats [--round N]`: writes `stats_round<N>.json` and prints the readout table (rarefaction,
  Chao1, collapse, noun share, per-family **yield and malformed rate**, recovery-by-string, the
  echo split with the words the name rule cost the run, the gloss-sense state).  $0.
- `submit --run-id R [--min-count 2] [--budget-usd 15] [--confirm-expensive --confirmed-by WHO]
  [--transport live|batches] [--dry-run]`: selects eligible table rows, **refuses while any of them
  still has two candidate senses** (run `sense` first), prints counts per family and form, prints
  the **downstream estimate** (`n × $0.0072` M1 + `n × pass × $0.011` M3, batches ×0.5, pass rate
  0.80 until the pilot measures it, with the 0.95 high case printed beside it), gates with
  `confirm_or_abort` on the 0.80 line (over budget
  needs `--confirm-expensive`; over the $20 line needs `--confirmed-by` and Roger's explicit go in
  chat), then `start_run` → tracked `candidates.jsonl` → `submit_candidates` → `keys.txt`,
  `submit_report.json`, `run.json` (args: round, prompts_version, temperature, model, table sha256,
  seed manifest), `usage.json` — and prints the follow-up commands
  (`gap_registry.py submit --from ...`, `traithood_filter.py --batch-id R_base_model --run
  base_model/R --pipeline split --transport T --budget-usd ...`, `novelty_score.py score ...`,
  `recovery_test.py --generator base_model --run-id R`, `report`).  Submitting itself is free; the
  guard sits here because the run's size is decided here.
- `report --run-id R`: assembles the evaluation from the table, stats, and the M1/M3 batch dirs
  named `R_base_model`; sums their `usage.json` per model; renders `report.md` and a 100-row
  `roger_sample.md` (plan 03 § 6's spot check: junk rate and polysemy rate).  No calls.

## 8. Acceptance tests, written first

No test calls an API, downloads anything, or loads a real model (`SampleBackend` is faked; a real
MPS smoke test sits behind `GAPGEN_RUN_LOCAL=1` and skips when the model directory is absent).

- `test_gapgen_base_model_seeds.py`: TDA seeds from a census-table fixture honor the familiarity
  floor; the wiki_bio fixture loader yields `(ref, name, first ≤ 200 words)`; O*NET parse; seeded
  determinism (same seed → same draws); the seeds module reads nothing under `data/traits` or
  `data/roles` (asserted on its open calls against a watched tmp data dir).
- `test_gapgen_base_model_prompts.py`: every family renders with 2-3 seed words and one
  constraint; header variants cycle; `sha256` stable for a fixed rng; a `PROMPTS_VERSION` bump is
  required for any wording change (hash manifest test); no corpus label or description string can
  enter a prompt (the renderer only sees the `SeedBundle`); the `ai_assistant` prompts name no
  corpus entity.
- `test_gapgen_base_model_sampler.py` (fake backend): JSONL schema; stop-at-blank-line truncation;
  resume skips completed batches and appends; token counts charged to `MultiModelUsage` with
  `cost_usd == 0.0`; `usage.json` written even on an interrupted run.
- `test_gapgen_base_model_parse.py`: splitting on commas/newlines/"and"; 1-4-word spans only;
  determiners stripped; digits and non-Latin dropped; `stubbornness` → `stubborn` only when the
  fake lexicon has the adjective, else kept as a `noun`-tagged surface with `normalized_from`
  recording nothing; form-tag truth table; dedupe merges counts and families.
- `test_gapgen_base_model_table.py`: eligibility truth table driven by faked `zipf_info` flags
  (hard-reject row ineligible with `ineligible_reason: "below_hard_reject"`; probe-band row
  eligible); `unknown_word` rows ineligible; rank by count then first appearance; mutation test:
  flipping every `corpus_stem_match` and `queue_stem_match` changes no `eligible`; rerun
  byte-identical; `sample_gloss` present, `gloss_hint` comes only from the fake OEWN; the echo
  screen's two rules counted apart, the dropped name word logged and the span never logged, a word
  that arrived from another seed not reported as lost and one that did not reported (QUESTIONS 54);
  the per-family counts of the readout (QUESTIONS 61).
- `test_gapgen_base_model_sense.py` (QUESTIONS 56): the wording pinned to its version; the free
  cosine screen (agreement settles a row with no call, divergence waits for one, the floor re-derives
  from the recorded cosines, the screen is idempotent); the rendered call states the criterion and
  never mentions novelty; fidelity overridden by legibility; a failed call leaves the row unresolved
  rather than guessing; the real client path charges every response; only divergent rows are asked.
- `test_gapgen_base_model_diversity.py`: rarefaction on a synthetic stream; Chao1 against a
  hand-computed example; collapse index; `string_recovery` resolves a `renamed_from` stem;
  per-family splits sum to the totals.
- `test_gapgen_base_model_submit.py` (tmp registry through the real API): candidates carry count
  as `score`, the family in `source_ref`, `partner_hint` on contrast rows, `sense_id` 1;
  `candidates.jsonl` is written before the registry append; resubmit of the same run is a no-op;
  **cost guard**: 10,000 fake rows → estimate > $20 → refused without `--confirm-expensive
  --confirmed-by`; 2,000 rows → over the default budget refused without the flag, accepted with
  it; dry-run leaves the registry byte-identical and writes no run dir; follow-up commands name
  the run id and batch id and the chosen transport; the package imports neither `anthropic` nor
  `openai`; the pass rate is the measured 0.80 with 0.95 printed and never gated on (QUESTIONS 55);
  **the sense gate**: a table straight out of `parse` refuses the submission, naming the `sense`
  command, and the chosen sense is what the candidate carries (QUESTIONS 56).
- `test_gapgen_freq.py`: `base_model` is absent from `FAMILIARITY_GENERATORS`, with the trap in the
  comment beside the assertion (QUESTIONS 58).
- `test_gap_generation_base_model_cli.py`: every subcommand's `--dry-run` exits 0 and writes
  nothing; `fetch` without `--approved-by` refuses with a message naming § 5a; `bench`/`sample`
  without the model directory refuse with a message naming `setup_external.py` (and never
  download); `sense` settles the divergent rows against a fake model and the hash embedder, records
  its usage and is a no-op on a rerun; `submit` refuses before it has run; `report` renders a
  fixture evaluation with the echo, sense and per-family sections.
- Acceptance on recorded outputs (`test_gapgen_base_model_acceptance.py`, skips while absent):
  `stats_round*.json` carries all § 6 fields, the echo split, the per-family yield and malformed
  rate, and a gloss-sense state with nothing unresolved; collapse index reported (target < 15%,
  report-and-decide); generator `usage.json` has `total_cost_usd == 0.0` and nonzero tokens (the
  gloss-sense cost lives in its own side-car, not the run's);
  [parse rate](./glossary.md#parse-rate) ≥ 0.99 in every M1 summary of this workstream's batches;
  the O*NET manifest entry says when its attribution becomes load-bearing (QUESTIONS 60).

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_base_model_*.py assistant_axis/tests/test_gapgen_freq.py data_analysis/tests/test_gap_generation_base_model_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Where the agent works: its own git worktree (first step `git merge --ff-only anthropic-vllm-uv`),
`.env` copied from the main checkout, `data/external/` and `runpod_workspace/` symlinked from it.
The § 3 boundary paragraph goes into every task prompt.

1. Skeleton (`base_model/__init__.py`, `sources.py`) + a zero-rate pricing entry for the local
   model tag in [`judge_pricing.py`](../../assistant_axis/judge_pricing.py) (the local-embedder
   pattern).  Test: sources + pricing.
2. `seeds.py` + `download.py` + CLI `fetch`.  Test: seeds.  **Then stop for Roger's § 5a word**
   (QUESTIONS entry if the plan review did not give it), run `fetch` and
   `setup_external.py --hf-model Qwen/Qwen3-8B-Base`, and paste the manifests (sizes, licenses as
   verified) into the task report.
3. `prompts.py` (six families, entropy injection, version pin).  Test: prompts.  Paste three
   rendered prompts per family into the task report (read the rendered prompt, not the template).
4. `sampler.py` + `bench.py` + CLI `bench`/`sample`.  Test: sampler.  Run `bench` for real and
   report tokens/s (> 150 tok/s aggregate stays on the Mac; below it, stop — escalation is
   Roger's decision, § 12).
5. T-grid shakedown: `sample --t-grid 0.8,1.0,1.2 --per-t 500` (free), `parse` + `stats` per T,
   pick T by uniques-per-1k and junk rate; record the choice in `run.json` for every later round.
   Needs `parse.py`, `table.py` first.  Test: parse, table.
6. `diversity.py` + CLI `stats`; add the rarefaction / Chao1 / collapse-index entries to
   [glossary.md](./glossary.md).  Test: diversity.
7. `submit.py` + CLI `submit` with the guard and follow-ups; `evaluate.py` / `report.py` + CLI
   `report`.  Test: submit, CLI.
7a. `sense.py` + CLI `sense` (QUESTIONS 56, built 2026-10-11 against fakes and never run): the free
   cosine screen, the one cheap call a divergent row, and `submit`'s refusal while a sense is
   unsettled.  Test: sense, submit, CLI.  **Open before it first runs**: the divergence floor is a
   provisional 0.60 (nothing is measured), so the pilot's own cosines re-derive it, and
   `DIVERGENCE_COSINE` is a one-line change with every cosine already on the rows.
8. **Pilot round A** (§ 10): 2k samples, free metrics readout.
9. **Prompt/seed iteration round** (§ 10): one bounded revision, 2k resample, free metrics; both
   readouts to Roger.
10. **Pilot submit** on the chosen round's eligible uniques (M1 + M3 live, ≈ $6-13), recovery-by-string,
   `report`.  **Roger's gate** for the full run.
11. Follow-up spec only (no code): if the pilot's noun share of M1 survivors is significant
   (guide: > 10-15% of otherwise-good candidates), write the LLM normalization task (Haiku 5.5 or
   a local model rewrites nouns of disposition to adjectives before submit) as a QUESTIONS entry
   with its cost, for Roger's go.  Roger § 9.4.
12. **Full run** on Roger's go: 20k samples, parse, stats, submit (`--transport batches`,
   `--confirm-expensive --confirmed-by`), M1, M3, `recovery_test.py`, report; acceptance test on
   the recorded outputs.
13. Acceptance report (§ 11); propose the `data/README.md` paragraph for `external/{wikibio,onet}`
   and `candidates/base_model/` in the report (do not race the platform's edits of that file).

## 10. Pilot (the Roger gate before the 20k run)

**Round A**: 2k samples at the chosen T (≈ 10-20 min at the benchmarked rate), `parse` + `stats`.
**Iteration round** (Roger's § 4 edit, bounded): one revision of header wordings, family weights,
seed mixes and constraints — data edits in `prompts.py` only, `PROMPTS_VERSION` → 2, no new code
paths — then 2k fresh samples and the same free metrics.  Decision between rounds is by the free
measures alone (uniques per 1k, collapse index, noun share, junk eyeball, recovery-by-string), so
the discarded round costs nothing downstream.  Further rounds only on Roger's word.

**Pilot submit** (chosen round, after `sense`): expected 600-1,000 eligible uniques; downstream
estimate at the measured rates ≈ $4-7 M1 + ≈ $5-9 M3 (at the 0.80 pass rate; ≈ $6-10 M3 in the 0.95
high case) ≈ **$9-16, live** (under the $20 line; budget cap by the first-of-kind formula
`1.5 × estimate + $2`).  Readout
(`report.md`): uniques and yield per 1k samples; collapse index (target < 15%); rarefaction and
Chao1 (is 20k worth it, or does the curve flatten — variant B trigger); noun share of uniques and
of M1 survivors (the § 9.4 gate number); **yield, malformed rate and M1 pass rate per prompt
family** (QUESTIONS 61: the lower-cased `wiki_bio` family against the clean-prompt families, a
within-run control for the casing), with **the `ai_assistant` family** also read on its own (yield,
M1 trait rate, [alignment scores](./coding_plan_platform.md), M3 new rate) so Roger can drop it;
what the biography-echo screen cost, the two rules apart (QUESTIONS 54);
recovery-by-string against the 932 stems, by family; M1 verdict/tag fractions and the **measured
pass rate** (replaces the 0.80 placeholder); M3 covered / new / grey with
[relation-call](./glossary.md#relation-overlap-calls) opposites and pair completions (the contrast
family's antonym mining); cost per candidate and useful-per-dollar (rows decided new or
pair-completion per dollar of `usage.json` total); the 100-row spot-check sample for Roger.

**Roger decides**: (a) go for the 20k run; (b) `ai_assistant` family in or out, and its weight;
(c) the noun-normalization follow-up (task 11) worth building or not; (d) variant B (purer base)
needed or not; (e) accept the iteration round's prompts as production or ask for another round;
(f) whether emission count should keep driving rank.  **Projected full run** (20k samples → 2-4k
eligible uniques): M1 ≈ $14-29 live, M3 at the pilot's measured pass rate (at 0.80: ≈ $18-35 live,
at the 0.95 high case ≈ $21-42); **≈ $16-32 batched** — over the $20 line, so the full run goes
through the Message
Batches API with Roger's explicit go (`--confirm-expensive --confirmed-by`), per the
batch-or-real-time rule in [CLAUDE.md](../../CLAUDE.md).

**Re-based on the pilot (2026-10-13, at Roger's request).**  The pilot's batches charged only rows no earlier
batch had judged: M1 $1.60 over 237 new rows ($0.0067 a row) and M3 $1.58 over 205 ($0.0077), so about **$0.013
a new word live, $0.0067 batched**; the other ~1,300 of its 1,540 submitted rows were already in the registry,
mostly from the censuses.  Every pilot word seen twice or more was already judged; of the 2,285 seen once, 723
(32%) were.  At 20k samples with the absolute floor of 2 (the gate audit's recommendation, not a proportional
20), the 3,825 eligible words seen in the pilot all clear the floor, and incidence extrapolation (Chao2 from
f1 2,285 and f2 420: about 6,200 unseen eligible words) adds more:

| case | words at the floor | new to the registry | live | batched |
|---|---|---|---|---|
| low: no unseen word reaches the floor | 3,825 | 1,562 | $21 | $10 |
| central: richness extrapolated to 10k samples, read as "seen twice in 20k" | 8,611 | 4,833 | $65 | **$32** |
| high: every word seen at 20k | 9,811 | 5,654 | $76 | $38 |

The new words are rarer than the pilot's, so the per-row rate is the main uncertainty.  The dollars are not the
binding cost: at the pilot's rates for rows only this generator found (M1 trait about 80%, M3 new about 55%), the
central case puts about 2,100 new kept candidates in front of review, about 14 hours at the measured 146 terms an
hour before pre-handling.  Submitting in review-hour waves ranked by emission count, as plan 09 does (its
decision 1), keeps each wave's M1/M3 cost and review time small.  The generator's own cost stays $0; the
20k sampling is ≈ 1.6M tokens, ≈ 1.5-3 h of Mac time at the benchmarked rate — far under the
13-GPU-hour line.

## 11. Report at the end

One page at [acceptance_03_base_model.md](./acceptance_03_base_model.md) (not written yet): what
was built against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the
download manifests (names, sizes, verified licenses); the bench number and the Mac decision; the
T-grid choice; both pilot rounds' stats side by side and what the iteration changed; the pilot
readout and Roger's § 10 decisions; the full run's counts, M1/M3 fractions, recovery (string and
`recovery_test.py` if run), and per-model cost from the `usage.json` files beside the generator's
zero; the noun-share number and the task-11 verdict; open QUESTIONS entries; the proposed
`data/README.md` paragraph.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture,
stubborn failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format
(`N. [03] question. Assumption proceeded under: ... Status: open`, numbering continues from 45),
proceeding under the stated assumption unless the answer would make the work useless.
Pre-registered entries Opus copies in at the start: (1) wiki_bio seeds accepted, prompts only,
never redistributed (Roger § 9.1); (2) raw samples are gitignored under `data/candidates/cache/`
and tracked artifacts carry no biography text; (3) the M3 pass-rate placeholder is 0.5 until the
pilot measures it; (4) `gloss_hint` is the OEWN person sense, not the model's sampled gloss;
(5) the instruct-model collapse control is deferred unless Roger approves its download (§ 5a);
(6) emission count rides in `Candidate.score` and is not a familiarity.  **All six are answered**
(QUESTIONS 53-58, Roger 2026-10-11): (2) the echo screen keeps its shape, with the counter split in
two, the dropped name word logged and the never-elsewhere list reported; (3) the placeholder is
**0.80**, with 0.95 printed as a high case; (4) the sense is resolved before M1 by the cosine screen
and one cheap call, fidelity subject to legibility, never novelty; (6) as assumed, with a guard test
that `base_model` stays out of `FAMILIARITY_GENERATORS`.  **Compute escalation is
Roger-only**: if the bench falls under 150 tok/s or the pilot shows vocabulary or writing-quality
problems, stop and put the numbers in front of him — RunPod or OpenRouter are his options to open
(Roger § 9.3), and any OpenRouter use follows [CLAUDE.md](../../CLAUDE.md)'s western-hosts-only
rule to the letter (hosts' countries listed first, host pinned, no fallback, keys unseen).
Anything that would edit a trait file or the queue, spend over a command's budget, download beyond
§ 5a, or change a frozen signature stops and asks.

## Frozen interface (for other generators)

`from assistant_axis.gapgen.generators.base_model import diversity`: `rarefaction(stems_in_order,
step)`, `chao1(counts)`, `collapse_index(counts, top=50)`, `string_recovery(stems, corpus_stems,
renamed)` — the diversity harness plan 03 § 7 promises the other workstreams, usable on any
generator's emission stream.  Function signatures are added to, never renamed, without a note here.

Added 2026-10-11 (QUESTIONS 61), additive and optional: `per_family(rows, *, samples=None,
counts=None)` takes `build_table`'s `by_family` block as `counts` and then reports, per family,
`n_eligible` and `eligible_per_1k` (the yield), `ineligible_share`, `n_raw_items`, `n_malformed` and
`malformed_rate`, `items_per_sample` and the three echo counts.  A caller that passes no `counts`
gets exactly what it got before.
