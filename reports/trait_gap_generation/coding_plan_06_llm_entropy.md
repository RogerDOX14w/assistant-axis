# Coding plan: workstream 6, LLM generation with injected entropy (generator id `llm_entropy`)

Written 2026-10-13 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[06_llm_entropy_generation.md](./06_llm_entropy_generation.md) with Roger's § 9 answers of 2026-10-13 as decisions
and the greenlight of the same day ([README](./README.md)), against the "Interface as built" section of
[coding_plan_platform.md](./coding_plan_platform.md).  One generator with five prompt families: **(a)** a domain x
mode grid, **(b)** person seeding from Wikidata, **(c)** ten languages back-translated, **(d)** verbalized sampling
as a wrapper on (a) and (e), **(e)** spelling constraints.  Every prompt carries a constraint the model cannot
satisfy from its mode, so the entropy comes from outside the model; the model supplies vocabulary and glosses.  The
platform's M1 (the trait-hood filter) and M3 (the novelty scorer) filter and score.  Terms: the
[glossary](./glossary.md); the ones this plan introduces (label-set Jaccard, Lincoln-Petersen, verbalized
sampling, back-translation, net-new row, review-hour wave) are defined on first use and go into the glossary in
task 9.  Every figure marked *measured* was measured read-only on 2026-10-13 (§ "Measured for this plan").
Roger's review comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN until decided)

1. **OPEN: the route of role-like outputs to the roles seed queue.**  Roger (§ 9.2): role-like outputs from
   person seeding are kept and routed to the roles seed queue.  As built, `Candidate` has no entity type
   ([registry.py](../../assistant_axis/gapgen/registry.py) `new_record` writes `entity_type: "trait"`), M1 puts a
   word it reads as a role on the `roles` holding list (tags `role_person` / `role_thing`,
   [normalize.py](../../assistant_axis/gapgen/normalize.py) `HOLDING`), and
   [promote.py](../../assistant_axis/gapgen/promote.py) refuses a held row as "never promoted".  So the decision has
   no route today.  The *roles seed queue* is [seed_queue.json](../../data/seed_queue.json)'s entries with
   `entity_type: "role"` (78 on 2026-10-13: 61 `done`, 13 `not_adopted`, 2 `exists`, 2 `backlog`), fed from
   [ROLES_TO_ADD.md](../../data/roles/instructions/ROLES_TO_ADD.md); the role corpus has 340 files.
   - (a) **A by-name promotion path, `gap_registry.py promote --keys K ... --allow-roles`**, writing an
     `entity_type: "role"` entry (`pairing: singleton`, tags `gap_gen`, `source:llm_entropy`, `role_like`,
     `description_draft` the gloss, section "trait-gap generators (2026-09)"), refused for the bulk path, exactly as
     `--allow-physical` and `--allow-released-states` were added for the physical and states passes.  About 40
     lines in [promote.py](../../assistant_axis/gapgen/promote.py) and
     [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) plus a test; a platform change, so Fable
     reviews the diff.  The generator's `roles-report` (§ 7) lists the held rows with a free string check against
     the role corpus and the queue's role entries; Roger names the ones to promote.
   - (b) **A generator-side list only**: `roles_report.md` for Roger to hand-seed through ROLES_TO_ADD.md and
     [seed_entities.py](../../data_analysis/seed_entities.py); no platform change, no registry record of the
     promotion.
   - **Recommendation: (a)**, because it is the precedented shape, the registry keeps the record
     (`seed_queue_stem` on the row), and `promote`'s collision checks (a stem in the corpus of either type, a
     queued stem, a turned-down name) apply to roles for free.  Role-like items are **submitted like every other
     item** (M1 decides the kind: the "nothing is dropped here" rule of [QUESTIONS 48](./QUESTIONS.md)); the
     generator's own `kind` guess rides in its table beside M1's verdict, as IPIP's does.  M3 never sees a held row
     (it scores verdict `trait` rows only), so the role check is the string check above, not a paid novelty call.
2. **OPEN: the pilot's submission.**  The pilot's generation is cheap (§ Cost, about $6 batched); what costs is
   M1 and M3 on its output.  At the *measured* registry overlap of the nearest LLM-sampled generator (85% of the
   base-model generator's single-word stems were already registered; 7-18% of the alignment sweep's and IPIP's
   phrases, § "Measured"), the pilot's roughly 5,000 string-unique items leave about 1,500-2,900 **net-new rows** (a
   row the registry has not yet filtered: not a corpus stem, not queued, not registered with both an M1 verdict and
   an M3 decision; plan 09 § 6), about $13-25 batched downstream and 2-4 hours of review.
   - (a) **A stratified slice: `submit --top 500` net-new rows, 50 per (family x model) cell** (five families; the
     Sonnet arm where one exists), ranked by `n_sources`, about **$4.2 batched / $8.4 live** downstream.  Each cell
     then has an M1 pass rate and a net-new kept share of its own, wide (n = 50) but enough to size the wave and to
     decide the model test; the rest of the pilot's rows wait in the table for wave 1.
   - (b) **Every net-new pilot row** (about $13-25 batched, 2-4 hours of review): the better measurement, at the
     price of most of the downstream budget before the full grid has run.
   - **Recommendation: (a)**; the wave is sized on its measured shares (§ 10), and the pilot rows it leaves behind
     are the first rows of wave 1, so nothing is lost.
3. **OPEN: real-person seeds restricted to the dead.**  Wikidata gives name and one-line description of obscure
   people, which is the point (§ 2); the output is vocabulary, but the tracked items table records which seed
   produced each item, so an invented trait list stands beside a named living person in the repository.
   - (a) **Real persons with a recorded date of death (`P570`)**: the same random draw, filtered; about half the
     humans drawn qualify, so the fetch takes about twice the calls (free).  Fictional characters unrestricted.
   - (b) Any human.
   - **Recommendation: (a)**; no yield is lost (the dead are as obscure) and no living person is characterised in
     a tracked file.

If a decision is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **Haiku 5.5** (`claude-haiku-5-5`, $0.10 / $0.50 per MTok in [judge_pricing.py](../../assistant_axis/judge_pricing.py)) is the generator for (a), (b), (d), (e) and the back-translation call; **Sonnet 5.5** (`claude-sonnet-5-5`, $2 / $10) for family (c)'s pilot share, the rest of (c) on whichever model the model test favours (§ 10).  Both refuse a `temperature` ([llm.py](../../assistant_axis/gapgen/llm.py) leaves it out) and think adaptively; the thinking is billed as output. | Roger, 2026-10-13 | plan 06 § 2, § 9.1 |
| **Languages** for (c): German, Japanese, Mandarin, Russian, Arabic, Persian, Finnish, Korean, Hindi, Turkish (Persian replaced Tagalog). | Roger, 2026-10-13: high to fairly-high resource | plan 06 § 3.3, § 9.1 |
| **Role-like outputs are kept and routed to the roles seed queue**, by the route of open decision 1. | Roger, 2026-10-13: "Yes" | plan 06 § 9.2 |
| **Labels of 1-4 words** in every family; the back-translation asks for the shortest English form of at most four words; a hyphenated compound is one word ([split.py](../../assistant_axis/gapgen/split.py) `is_phrase`, the alignment sweep's `label_problem`). | Roger, 2026-10-13: part of the point is concepts that are not a single English word | plan 06 § 9.3 |
| **Batched for anything over a quick experiment; total expenditure under about $60** including the downstream M1 and M3.  The translation of the ten prompts and their back-translation check (about 20 calls) go live; every generation wave, the model-test arms included, goes through the Message Batches API; downstream transport by the estimate (§ 7). | Roger, 2026-10-13 | plan 06 § 9.4; the batch-or-real-time rule, [CLAUDE.md](../../CLAUDE.md) |
| **No generation on the RunPod Qwen.**  The § 6 "generator-knowledge check" (50 labels defined by the target model) is not run; M1's definition probe, with every item's gloss as its hint, is the knowledge check the platform already makes.  (A free variant on the Mac's Qwen3-8B-Base, the base-model generator's sampler, is listed in § 2 for later.) | Roger, 2026-10-13: "No" | plan 06 § 9.5, § 6 |
| **No generator-side frequency floor.**  Plan 06 § 3.5's "Zipf >= 3.0" for single words is replaced by recording Zipf on every item (free, [freq.py](../../assistant_axis/gapgen/freq.py) `zipf_info`) and reporting the share below 3.0 per family.  The platform's floor (hard reject below 1.5, the definition probe to 2.5) decides, and every item here carries a gloss, so rescue route 2 (`gloss_hint`) sends a rare word to the probe rather than the bin. | a second untuned gate in front of M1 can only subtract ([QUESTIONS 48](./QUESTIONS.md); the gate audits of [2026-10-12](../code_review_2026-10-12/gate_audits/README.md)) | this plan (pre-registered, § 12) |
| **Semantic overlap uses the scorer's embedder**, OpenAI `text-embedding-3-large` through [embed.py](../../assistant_axis/gapgen/embed.py) `make_embedder("openai")` and `EmbeddingCache` (`HashEmbedder` in tests), not sentence-transformers on the Mac.  About 60,000 short strings is under $0.10. | plan 06 § 7 asks for the metric the scorer uses; nothing local to download | this plan (pre-registered) |
| **Every item is kept, none dropped by its tags**; a label that is a corpus trait, a queue entry or a registered stem is submitted (the registry merges the source at no cost; M1 and M3 skip decided rows), counted out of the estimate and the kept target.  The only items not submitted are those the label rule refuses (over four words, non-ASCII, an underscore, a surface that does not normalise), kept in the table with `label_problem` and counted (the rule's bite, as the alignment sweep reports it). | the "every item is kept" row of [coding_plan_09](./coding_plan_09_structural_generators.md) § 1; [registry.py](../../assistant_axis/gapgen/registry.py) refuses a surface that does not normalise | platform |
| **The submitted surface is always English**: the English label (families a, b, d, e) or the back-translated label (c).  The original-language form, its romanisation and the language live in the generator's table and in `source_ref`, never in the surface (a label with no Latin letters normalises to an empty stem and is refused as `invalid`). | [normalize.py](../../assistant_axis/gapgen/normalize.py) folds the stem to ASCII | this plan |
| **`score` is `n_sources`** (how many (family, prompt, run) triples produced the stem), a repetition signal, **not a familiarity**: `llm_entropy` is not added to `FAMILIARITY_GENERATORS` (guard test, as [QUESTIONS 58](./QUESTIONS.md)); `partner_hint` is the item's `antonym`; `gloss_hint` its gloss; `sense_id` 1. | the frozen `Candidate` | platform |
| **Three independent runs per prompt** (needed for the collapse statistics), each a separate request, no temperature; the model's default sampling with adaptive thinking is what the collapse measurement measures. | plan 06 § 3 | plan 06 |
| **(d) is two single-turn stages**: stage 1 is the (a) or (e) call with a probability per item; stage 2 is a fresh call whose user turn quotes stage 1's answer and asks for items of probability below 0.03.  `call_anthropic_json` and the Batches transport send one user turn, so the follow-up is not a second turn of one conversation. | [llm.py](../../assistant_axis/gapgen/llm.py) `request_params` | this plan (pre-registered) |
| **One person per (b) call**; a person's list is not shared with another's. | words in one call affect each other's answers (Roger, 2026-09-29, the one-item rule) | [rubrics/README.md](./rubrics/README.md) |
| **Person seeds from Wikidata (CC0)** by the MediaWiki random-item API (`list=random`, namespace 0, then `wbgetentities` for `P31`, label, description, dates) for real persons and by SPARQL over the fictional-character classes with a random offset for fictional ones; one request at a time with a pause, HTTP 429 retried with back-off.  Not PersonaHub (card licence `cc-by-nc-sa-4.0`, non-commercial share-alike) and not Nemotron-Personas (§ "Measured": the original dataset id returns no card; the `-USA` variant is `cc-by-4.0`); neither is needed. | plan 06 § 2; licences checked 2026-10-13 | this plan |
| **The ten (c) prompts are translations of one pinned English master**, made once by Sonnet 5.5 (10 calls), back-translated once by Haiku 5.5 for Roger's read (10 calls), and kept in a tracked JSON, [multilingual_prompts.json](../../data/candidates/llm_entropy/multilingual_prompts.json) (not there yet), with each text's sha256; every (c) record carries its language's prompt hash. | the pin registry pins one text per name; a translation is derived data with its own hash | this plan (pre-registered) |
| **Prompts show no corpus label** (the families carry domains, persons, languages and spellings, never a trait name), so the judge display form is a no-op; records still carry `label_form` and the rendering goes through [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py) (one rule everywhere).  Example words in every prompt are hygiene-checked ([prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py): no corpus stem, queue label or validation-file word); domain and mode nouns are checked the same way. | the judging and hygiene rules | platform |
| Rubric texts are pinned under [rubrics/](./rubrics/): [llm_entropy_scaffold.md](./rubrics/llm_entropy_scaffold.md), [llm_entropy_multilingual.md](./rubrics/llm_entropy_multilingual.md) and [llm_entropy_backtranslate.md](./rubrics/llm_entropy_backtranslate.md) (none there yet) join `GENERATOR_FILES` in [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) and get their first row in [versions.json](./rubrics/versions.json) through `rubric_pins.py bump`; the family user-turn templates live in `prompts.py` under a `PROMPTS_VERSION` with a wording hash, as the base-model generator's do. | one version names one text | judging rule; [base_model/prompts.py](../../assistant_axis/gapgen/generators/base_model/prompts.py) |
| **Generation waves run M1 + M3 only**; grouping (R1) once at the end over every batch. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| **The first wave is the review-hour wave**: `submit --kept-target 300`, sized on **net-new kept rows** at the pilot's measured net-new kept share, the ranking of § 7; the rest waits for a second wave on Roger's word.  "~150 terms an hour" is the fallback until plan 13's `pooled_review_rate` exists (146 an hour measured on the TDA batch). | Roger's decision 1 for plan 09, 2026-10-13; the brief | [coding_plan_09](./coding_plan_09_structural_generators.md) decision 1; [coding_plan_13](./coding_plan_13_generator_testing.md) frozen interface |
| **The paid recovery harness is not bought for this generator.**  Plan 13's decision 1 (every generator, pooled, two seeds, about $53-68, approved) measures this run's recall once its rows are in the registry; this plan prints the free string recovery per family. | one harness run, pooled | [coding_plan_13](./coding_plan_13_generator_testing.md) decision 1 |
| Counts used throughout (2026-10-13): **932 trait files**, **340 role files**, registry **9,949 keys** (7,875 single-word stems, 2,074 multi-word), queue **1,050 entries** (972 traits, 78 roles). | counted, not copied | this plan |

## 2. Out of scope

- Generation on the RunPod Qwen3-32B (Roger); the free knowledge check on the Mac's Qwen3-8B-Base (a later task if
  the pilot's M1 probe cuts many rare single words).
- The second-model-family variant (plan 06 § 8: 20% of (a) on an OpenAI model) and the local-generator variant.
- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [seed_queue.json](../../data/seed_queue.json)
  except through `promote`; promotion itself (Roger's); R1 and the review app.
- Anything the platform owns beyond open decision 1 (a): M1 and M3 rubrics, cut-offs,
  [metric_config.json](../../data/candidates/metric_config.json), the recovery harness.
- A generator-side semantic deduplication that *drops* items: the embedding is used for the statistics only;
  M3 decides coverage.
- Plan 13's dashboard columns (interface request, § 12).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every batched LLM output, `MultiModelUsage`;
`json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (stems via `normalize_to_file_name`; display form only in
prompts and readouts; US English),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are; the roles side of
the queue; the description-wording rule, which the glosses follow),
[judging.md](../../.claude/rules/judging.md) (reason before verdict; `warn_if_low_parse_rate` at 99%; pins; the
rendered-prompt rule), [CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, **tests are
mandatory**, hotlinks, western hosts only, keys unseen).  No PNGs are planned (the rarefaction curves are tables);
if one is added, Read the plotting rule first.

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository worktree,
the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home directory, not
`~/.cache`, not even to see whether something is downloaded; never open `.env`.  The only outside data this
workstream fetches is the Wikidata person seeds (about 1 MB, CC0, task 2), written under
`data/candidates/llm_entropy/`; nothing else is downloaded.

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate`, `start_run`, `submit_candidates`, `SubmitReport`,
  `RunContext` ([registry.py](../../assistant_axis/gapgen/registry.py), [runs.py](../../assistant_axis/gapgen/runs.py):
  `record_candidates` before the append, `finish()`, `dirty_refusal` over `PLATFORM_PATHS`); `paths.run_dir`,
  `check_id`, `SEED_QUEUE_PATH`.
- [cost.py](../../assistant_axis/gapgen/cost.py): `Estimate`, `estimate_calls_usd`, `confirm_or_abort`,
  `GuardedUsage(usage_path=...)`, `resume_usage`, `HARD_LINE_USD`; [llm.py](../../assistant_axis/gapgen/llm.py)
  `call_anthropic_json`, `request_params`, `accepts_temperature`.
- **The Batches transport for a generator's own calls**: [batches.py](../../assistant_axis/gapgen/batches.py)
  `BatchTransport(runner, client, state_path, budget_usd=...)` needs a runner with `estimate_usd(calls, batch=)`,
  `usage` and `batch_id`, and calls with `custom_id` (64 characters of `[A-Za-z0-9_-]`), `model`, `system`, `user`,
  `max_tokens`, `temperature`, `cache_system`, `cache_ttl`; the precedent is `StatesPassRunner` and its `Call` in
  [states_pass.py](../../assistant_axis/gapgen/states_pass.py) (`estimate_usd`, `_wave`, `_base_record`, the live
  transport beside it, `--resume` by recorded `custom_id`).  Copy that shape, not the split runner's.
- The record-before-parse loop of [alignment_sweep/extract.py](../../assistant_axis/gapgen/generators/alignment_sweep/extract.py)
  (`run_stage`, `append_response`, `reusable_answers`, `label_problem`, `load_rubric`) and its `MAX_TOKENS` for a
  thinking model.
- [base_model/diversity.py](../../assistant_axis/gapgen/generators/base_model/diversity.py): `rarefaction`, `chao1`,
  `collapse_index`, `string_recovery`, `per_family` (frozen; this plan adds Jaccard, Lincoln-Petersen and the
  semantic variants in its own module); [base_model/report.py](../../assistant_axis/gapgen/generators/base_model/report.py)
  `render_sample`; [base_model/sources.py](../../assistant_axis/gapgen/generators/base_model/sources.py) (how a
  fetched source is recorded with size, hash and licence).
- [censuses/corpus.py](../../assistant_axis/gapgen/generators/censuses/corpus.py) (`corpus_trait_stems`,
  `corpus_renamed_from`, `queue_trait_stems`); [seed_entities.py](../../data_analysis/seed_entities.py)
  `corpus_stems(data_dir)` (both entity types) for the roles check; [freq.py](../../assistant_axis/gapgen/freq.py)
  `zipf_info`.
- The submit recipe of [masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py)
  (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, `BATCH_FACTOR = 0.5`, `RATES_SOURCE`,
  `select_wave(kept_target, kept_share)`, `registry_stems`, the review-load guard, `followup_commands`, the `_budget`
  first-of-kind cap) and [base_model/submit.py](../../assistant_axis/gapgen/generators/base_model/submit.py)
  `downstream_need` (what M1 and M3 will really charge for).
- [embed.py](../../assistant_axis/gapgen/embed.py) (`make_embedder`, `EmbeddingCache`, `HashEmbedder`);
  [prompt_labels.py](../../assistant_axis/gapgen/prompt_labels.py); [prompt_hygiene.py](../../assistant_axis/gapgen/prompt_hygiene.py)
  `prompt_words`; [split_rubrics.py](../../assistant_axis/gapgen/split_rubrics.py) `GENERATOR_FILES`,
  `load_prompt`, `mismatches`; [rubric_pins.py](../../data_analysis/gap_generation/rubric_pins.py);
  [judge.py](../../assistant_axis/judge.py) `extract_json_blob`, `warn_if_low_parse_rate`;
  [entity_id.py](../../assistant_axis/entity_id.py) `normalize_to_file_name`; [atomic_io.py](../../assistant_axis/atomic_io.py);
  [provenance.py](../../assistant_axis/provenance.py) `json_metadata`.
- The IPIP naming rubric [ipip_naming_blind.md](./rubrics/ipip_naming_blind.md) as the model for a pinned
  generator rubric (header table, fenced text, the `kind` field in M1's vocabulary, the hygiene paragraph) and
  [ipip/naming.py](../../assistant_axis/gapgen/generators/ipip/naming.py) `label_problem` (1-4 words, no comma).
- Test style: [alignment_sweep_fakes.py](../../assistant_axis/tests/alignment_sweep_fakes.py) (a fake Anthropic
  client scripted by prompt), `FakeBatchClient` in [test_gapgen_batches.py](../../assistant_axis/tests/test_gapgen_batches.py),
  [test_gapgen_base_model_diversity.py](../../assistant_axis/tests/test_gapgen_base_model_diversity.py).
  **No new dependencies**: `wordfreq`, `openai`, `anthropic` and `numpy` are in [pyproject.toml](../../pyproject.toml).

## 5. File layout

```
assistant_axis/gapgen/generators/llm_entropy/
  __init__.py     GENERATOR = "llm_entropy"; ENTROPY_DIR = DATA_CANDIDATES / "llm_entropy"; PERSON_SEEDS_PATH;
                  MULTILINGUAL_PROMPTS_PATH; ITEMS_TABLE_PATH; COLLAPSE_PATH; EVALUATION_PATH; re-exports (§ Frozen)
  prompts.py      FAMILIES = ("a", "b", "c", "d", "e"); DOMAINS (30 nouns), MODES (7), LANGUAGES (10: code, English
                  name, native name), SPELLING: LETTERS (26), BIGRAMS (the 120 commonest initial bigrams of OEWN
                  adjectives, derived at build time and frozen into the file), SUFFIXES (20), PREFIXES (12),
                  FRAMES ("X to Y", "X about Y", "X with Y"); PROMPTS_VERSION, PROMPT_HASHES (append-only);
                  Prompt(prompt_id, family, user, language, meta); grid_prompts(family) -> list[Prompt];
                  render_a(domain, mode), render_b(seed), render_c(lang, domain, *, prompts_json), render_d_stage1
                  (base prompt), render_d_stage2(base prompt, stage1_answer_text), render_e(constraint);
                  render_backtranslate(lang, items) -> str; EXAMPLE_WORDS (hygiene-checked)
  seeds.py        PersonSeed(qid, name, description, kind: real|fictional, born, died, fetched_at);
                  fetch_real(n, *, session, rng, dead_only) (random-item API + wbgetentities; P31 = Q5; P570 when
                  dead_only); fetch_fictional(n, *, session, rng) (SPARQL over FICTIONAL_CLASSES with LIMIT/OFFSET);
                  throttled(session) (one request at a time, 2 s apart, 429 -> back-off (5, 20, 60, 180));
                  write_seeds / load_seeds; the fetch record (counts, sha256, licence CC0, capture date)
  calls.py        EntropyCall(family, prompt_id, run, model, system, user, max_tokens, temperature=None,
                  cache_system=True, stage=1) with custom_id / prompt_sha256 / cache_key; EntropyRunner(client,
                  batch_id, usage, transport, responses_path, resume_records): estimate_usd(calls, batch=), wave(),
                  records every answer before parsing (record shape § 6), reusable answers by (family, prompt_id,
                  run, model, prompt_sha256, user sha256, stage); LiveTransport (asyncio, concurrency 6)
  parse.py        parse_reply(text) -> (items | None, error); validate_item (label 1-4 words, no comma, gloss
                  "This means" <= 25 words, antonym or null, kind in KINDS, probability in [0, 1] or absent);
                  label_problem (the alignment sweep's: > 4 words, underscore, non-ASCII, does not normalise);
                  parse_backtranslation(text, n_expected)
  table.py        Item(item_id, family, prompt_id, run, language, model, raw, label, gloss, antonym, kind,
                  ambiguity_flag, probability, stem, zipf_min, label_problem, backtranslated_from); build_items
                  (responses -> items, one per emitted item; deterministic); build_table(items, *, corpus, renamed,
                  queue, registry) -> distinct rows by stem (§ 6: sources, n_sources, families, languages, models,
                  gloss (of the most frequent reading), gloss_divergent, antonyms, kinds, the five membership tags,
                  rank); write_table / load_items_table
  collapse.py     label_jaccard(run_sets) (pairwise over the three runs of one prompt; median per family);
                  lincoln_petersen(n1, n2, m) -> N (with the Chapman form); rarefaction_per_family(items, *, seed)
                  (draws = calls, random call order; end_slope over the last fifth); semantic_sets(items, embedder,
                  tau=0.9) (two labels are one when their embedding cosine >= tau; union-find); cross_family_matrix
                  (string and semantic Jaccard between families); yield_per_dollar(curves, usage) -> per family;
                  write_collapse (enveloped)
  evaluate.py     string_recovery_per_family (the 932 stems and renamed_from; the queue's 972 trait entries apart);
                  model_test(table, registry_rows, usage) -> per (family, model): unique per dollar (string and
                  semantic), M1 trait share, net-new kept share, label-rule bite, parse rate; verbalized_readout
                  (stage 2's unique-add share and its M1 reject rate against stage 1's); roles_summary
  submit.py       estimate_downstream_usd(n, *, transport, pass_rate=0.88, n_m3_only); select_top(table, n, *,
                  per_cell) (stratified by (family, model)); select_wave(table, *, kept_target, kept_share,
                  registered_stems, pending_stems) (plan 04's selector on net-new rows; ranking § 7);
                  to_candidates(rows, run_id) (§ 6); run_submit(...) (prints strata, the estimate, gates with
                  confirm_or_abort, writes candidates.jsonl before the append, keys.txt, submit_report.json,
                  run.json, usage.json, follow-ups)
  report.py       render_report(evaluation, collapse, run) -> markdown; roger_sample(rows, n=50 per family,
                  seed=0); gloss_check_sample(table, n=30 per family, seed=0); roles_report(rows, *, role_corpus,
                  role_queue) -> markdown; net_novel(run_rows, registry_rows) -> (raw, net)
data_analysis/gap_generation/llm_entropy_generator.py
                  seeds | prompts | translate-prompts | generate | backtranslate | verbalized | postprocess |
                  collapse | model-test | submit | roles-report | report
reports/trait_gap_generation/rubrics/{llm_entropy_scaffold.md, llm_entropy_multilingual.md,
                  llm_entropy_backtranslate.md}                                   pinned texts
data/candidates/llm_entropy/{person_seeds.jsonl, person_seeds_fetch.json, multilingual_prompts.json,
                  items_table.jsonl, collapse.json, evaluation.json, roles_report.md}   tracked (the table ~3-5 MB)
data/candidates/runs/llm_entropy/<run_id>/{responses.jsonl, batches.json, candidates.jsonl, keys.txt,
                  submit_report.json, run.json, usage.json, report.md, roger_sample.md, gloss_check.md}
assistant_axis/tests/test_gapgen_llm_entropy_{prompts,seeds,calls,parse,table,collapse,evaluate,submit,acceptance}.py
data_analysis/tests/test_gap_generation_llm_entropy_cli.py
```

Every paid answer is appended to the run's `responses.jsonl` before it is parsed (the Roget precedent,
[QUESTIONS 37](./QUESTIONS.md)), keyed by family, prompt id, run index, stage, model and prompt sha256, so a rerun of
the same run id reuses them (`--resume`) and a changed prompt does not.  `batches.json` holds the Batches state
([batches.py](../../assistant_axis/gapgen/batches.py)), so a killed process collects what it paid for.

## 6. Data schemas

**Person seed** ([person_seeds.jsonl](../../data/candidates/llm_entropy/person_seeds.jsonl), not there yet; 400 real
and 200 fictional; the fetch record beside it in `person_seeds_fetch.json` with counts, calls made, sha256, licence
and capture date):

```json
{"qid": "Q65871003", "name": "Tian Yi", "description": "person, CBDB ID = 367824", "kind": "real",
 "born": null, "died": "1684", "fetched_at": "2026-10-14T09:00:00+00:00"}
```

(That row is one of the five random items drawn on 2026-10-13 to check the API, § "Measured".  A description that
is only an identifier is kept: the model is told that the seed may be obscure and that accuracy is irrelevant.)

**Response record** (one JSON object per call in `responses.jsonl`, written before parsing; the states pass's shape):

```json
{"batch_id": "2026-10-15-pilot_llm_entropy", "family": "a", "prompt_id": "a:money:habit", "run": 2, "stage": 1,
 "model": "claude-haiku-5-5", "prompt_sha256": "…", "prompts_version": 1, "language": "en", "user": "…",
 "user_sha256": "…", "text": "…", "stop_reason": "end_turn", "usage_raw": {"input_tokens": 612, "output_tokens": 2310},
 "charged_as": "claude-haiku-5-5:batch", "custom_id": "a-money_habit-r2-s1-3f9c1a2b7e01", "batch_request_id": "msgbatch_…",
 "attempts": 1, "error": null, "parse_error": null, "n_items": 19, "n_invalid": 1, "label_form": "judge-display-v1",
 "at": "2026-10-15T10:00:00+00:00"}
```

**Model reply** (the scaffold's schema; reason first; illustrative, with hygiene-checked example words):

```json
{"approach": "Money as a habit: what someone does with it week after week, admirable and not.",
 "items": [
  {"label": "tithes without fail", "gloss": "This means setting aside a fixed share of every sum received for others before spending any of it.",
   "antonym": "keeps every penny", "kind": "trait", "ambiguity_flag": false, "probability": 0.04},
  {"label": "penny-wise", "gloss": "This means fussing over small sums while letting large ones slip through unexamined.",
   "antonym": "pound-wise", "kind": "trait", "ambiguity_flag": true, "probability": 0.2}]}
```

`probability` is present only under the (d) wrapper.  `kind` is a guess in M1's vocabulary (`trait`, `membership`,
`state`, `physical`, `role`, `action`, `evaluative`, `not_a_persona`), reported beside M1's verdict, never a gate.

**Item** (one per emitted item, in `build_items`' output; the tracked table is the distinct view below):
`{item_id, family, prompt_id, run, stage, language, model, raw, label, gloss, antonym, kind, ambiguity_flag,
probability, stem, zipf_min, label_problem, backtranslated_from}`; for (c) `raw` is the original-language label (with
the back-translation call's romanisation in `backtranslated_from`) and `label` the English form.

**Items table row** ([items_table.jsonl](../../data/candidates/llm_entropy/items_table.jsonl), not there yet; one per
distinct stem; deterministic from the runs' responses; the stem is `normalize_candidate(label).stem`):

```json
{"schema_version": 1, "stem": "penny_wise", "label": "penny-wise",
 "gloss": "This means fussing over small sums while letting large ones slip through unexamined.",
 "gloss_divergent": false, "antonyms": ["pound-wise"], "kinds": {"trait": 3}, "ambiguity_flags": 1,
 "sources": [{"family": "a", "prompt_id": "a:money:habit", "run": 2, "model": "claude-haiku-5-5", "language": "en"},
             {"family": "e", "prompt_id": "e:prefix:penny", "run": 1, "model": "claude-haiku-5-5", "language": "en"}],
 "n_sources": 2, "families": ["a", "e"], "languages": ["en"], "models": ["claude-haiku-5-5"],
 "zipf_min": 2.9, "label_problem": null,
 "exists": false, "queued": false, "queue_status": null, "registered": true, "registered_by": ["censuses"],
 "registered_decided": true, "net_new": false, "pair_completion_hint": null, "rank": 1480}
```

Rules: `exists` is a corpus stem or a `renamed_from`; `queued` any queue entry by stem or normalised label;
`registered` a key in the registry log, with `registered_by` and `registered_decided` (an M1 verdict and an M3
decision both present); `net_new` is not `exists`, not `queued`, not `registered_decided`;
`pair_completion_hint` is set when an antonym's stem is a corpus trait whose `negative_label` is a `non-X`
placeholder or whose arrangement is `singleton` (a pair completion candidate, worth the pairing premium of the
trait-pairs rule); `gloss` is the gloss of the stem's most frequent reading and `gloss_divergent` is true when two
readings' glosses have embedding cosine below 0.6 (reported; the pilot says how often).  **No tag drops a row**
(mutation test, § 8).

**Candidate emitted** (one per source; the registry merges them into one row with several `sources[]` entries):
`Candidate(surface="penny-wise", generator="llm_entropy", run_id="2026-10-15-pilot", rank=1480, score=2.0,
gloss_hint="This means fussing over small sums ...", sense_id=1, source_ref="llm_entropy:a:money:habit:r2",
partner_hint="pound-wise")`.  `source_ref` is `llm_entropy:<family>:<prompt id>:r<run>` (for (c)
`llm_entropy:c:<lang>:<domain>:r<run>`, for (d) stage 2 `llm_entropy:d:<base prompt id>:r<run>`), so family, prompt
and language are readable from it (plan 13's `stream_of` can read the family, § 12).

**Collapse payload** ([collapse.json](../../data/candidates/llm_entropy/collapse.json), not there yet, enveloped;
figures illustrative): `{"per_family": {"a": {"n_calls": 630, "n_items": 11800, "n_unique_string": 4100,
"n_unique_semantic": 2600, "jaccard_median": 0.41, "jaccard_p90": 0.63, "lincoln_petersen_N": 5900,
"seen_over_N": 0.69, "rarefaction": [[100, 1250], [200, 2100], ...], "end_slope_per_call": 3.1,
"unique_per_usd": 2400, "semantic": {...the same at cosine 0.9...}}, "c": {"by_language": {"de": {...}, ...}}},
"cross_family": {"string": [[...]], "semantic": [[...]]}, "tau": 0.9, "embedder": "openai"}`.

**Evaluation payload** ([evaluation.json](../../data/candidates/llm_entropy/evaluation.json), not there yet):
per family `string_recovery` (of 932; the queue's 972 trait entries apart), the label-rule bite, the parse rate, the
Zipf-below-3 share, the roles summary, and `model_test` per (family, model) (§ 10).

## 7. CLI

[llm_entropy_generator.py](../../data_analysis/gap_generation/llm_entropy_generator.py) (not there yet).  Common
flags `--data-dir`, `--registry`, `--candidates-dir`, `--dry-run`; every paid command takes `--budget-usd` (a hard
cap: an estimate over it is refused, `confirm_or_abort`), `--confirmed-by` (with `--confirm-expensive` over the $20
line; **not expected here**: no single command's estimate reaches it), `--transport live|batches` (generation
commands default to `batches`; the two translation commands and `model-test`'s dry run to `live`), `--resume` and
`--allow-dirty` (refuses uncommitted platform code otherwise), prints its estimate as `n_calls x (in, out) tokens at
model rates = $X` before sending (2,500 output tokens a call for the thinking models until the pilot measures it),
charges every answer to a `GuardedUsage(usage_path=...)`, and writes `usage.json` beside its output in a `finally`
block.  Dry runs print the estimate, the counts and one **rendered prompt per variant** (§ "Rendered prompts") and
write nothing.

- `seeds --real 400 --fictional 200 [--dead-only] --seed 0`: the Wikidata fetch (task 2), $0, about 250-500 HTTP
  requests at 2 s apart (10-20 minutes); writes [person_seeds.jsonl](../../data/candidates/llm_entropy/person_seeds.jsonl)
  and the fetch record [person_seeds_fetch.json](../../data/candidates/llm_entropy/person_seeds_fetch.json) (neither
  there yet).  Refuses to overwrite without `--force` (snapshot first).
- `prompts [--family F] [--n 3]`: renders prompts of every family ($0): the hygiene check of every prompt word
  (exit 1 on a hit), the grid sizes (210, 600, 300, 181), and the sample variants for Roger.
- `translate-prompts --budget-usd 1`: Sonnet 5.5 translates the pinned English (c) master into the ten languages
  (10 calls), Haiku 5.5 back-translates each (10 calls); writes
  [multilingual_prompts.json](../../data/candidates/llm_entropy/multilingual_prompts.json) (not there yet; language,
  text, sha256, back-translation, model, at) and prints master and back-translations side by side for Roger's read.
  About $0.3.
- `generate --run-id R --family a|b|c|e [--share 0.2 --seed 0] [--runs 3] [--model M] [--with-probabilities]
  --budget-usd C`: the family's grid (or a seeded 20% share of its prompts, every prompt with all its runs), one
  request per (prompt, run); `--with-probabilities` is (d)'s stage 1 on (a) or (e).  Answers recorded, parse rate
  printed through `warn_if_low_parse_rate`, `max_tokens` 12,000, a reply stopped at `max_tokens` or unparseable
  asked once more at 16,000.  Default caps: the first-of-kind `ceil(1.5 x estimate + 2)`.
- `backtranslate --run-id R --budget-usd C`: for every (c) answer, one Haiku 5.5 call per (prompt, run) with its
  items (§ "Rendered prompts"), recording the English label (at most four words), romanisation, gloss and the
  listicle flag.
- `verbalized --run-id R --family a|e --budget-usd C`: (d)'s stage 2 for every stage-1 answer of the run.
- `postprocess [--run-id R ...]`: items and the table from every named run's responses (stems, Zipf, tags, merge,
  rank); deterministic, byte-identical on rerun, `.bak.<UTC>` on change.  $0.
- `collapse [--run-id R ...] [--embedder openai|hash] [--tau 0.9] [--seed 0]`:
  [collapse.json](../../data/candidates/llm_entropy/collapse.json) (§ 6; not there yet); the embeddings through the
  cache, pennies.
- `model-test --run-id R`: the per-(family, model) table of § 10 from the table, the registry blocks and the run's
  `usage.json`.  $0.
- `submit --run-id R (--top N [--per-cell 50] | --kept-target 300 [--kept-share X] | --all) [--transport
  live|batches] [--budget-usd 10] [--dry-run]`: selects table rows.  `--top N` is the pilot's stratified slice
  (open decision 2); `--kept-target` is the review-hour wave: **it counts net-new kept rows**, `--kept-share` is the
  pilot's measured net-new kept share (before the pilot, 0.35 flagged ASSUMED: the base-model generator's measured
  kept-per-submitted, § "Measured"); a registered, decided row inside the cut is submitted, counted toward neither
  the target nor the estimate.  **Ranking**: `n_sources` descending, then rows with a `pair_completion_hint`, then a
  round-robin over families so one family cannot fill a wave, then rank within family by `n_sources` and emission
  order.  Prints strata (family x model x exists/queued/registered-decided/registered-pending/net-new; single- and
  multi-word; the label-rule rejects), the **downstream estimate** at the measured rates (M1 $0.0072 a word, M3
  $0.011 a passed word at the pilot's pass rate, 0.88 before it, batches x0.5; rows the registry has filtered
  counted out; `downstream_need` for the M3-only rows), the review-load projection (rows submitted, counted, hours
  at ~150 an hour), gates with `confirm_or_abort`, writes `candidates.jsonl` **before** `submit_candidates`, then
  `keys.txt`, `submit_report.json`, `run.json`, `usage.json`, and prints the follow-ups: `gap_registry.py submit
  --from ...` (main checkout), `traithood_filter.py --batch-id R_llm_entropy --run llm_entropy/R --pipeline split
  --transport T --budget-usd <1.5 x est + 2>`, `novelty_score.py score ...`, `report --run-id R`.
- `roles-report --run-id R`: every row of the run on the `roles` holding list, or whose generator `kind` was `role`
  in a majority of its readings, with the free string check against the role corpus (340 stems) and the queue's
  role entries, the seed that produced it and its gloss;
  [roles_report.md](../../data/candidates/llm_entropy/roles_report.md) (not there yet) for Roger; the promotion
  command of open decision 1 (a) printed per row.  $0.
- `report --run-id R`: `report.md` (§ 11's figures), `roger_sample.md` (50 rows per family decided `new` or
  `grey`, seeded) and `gloss_check.md` (30 items per family and per model arm, label, gloss, raw form, for the
  gloss-fidelity check).  $0.

## 8. Acceptance tests, written first

No test calls an API or the network: a fake Anthropic client scripted by prompt hash (so a changed prompt fails
loudly), `FakeBatchClient` for the Batches path, a fake HTTP session with canned Wikidata JSON (the API shapes
recorded on 2026-10-13), `HashEmbedder`, a tmp registry through the real frozen API.  Collapse and recovery figures
are **report-and-decide**; parse rate, the label rule, cost caps, `usage.json` presence, the untouched corpus and
the roles route are hard.

- `prompts`: the three rubric texts are pinned (`split_rubrics.mismatches()` empty; `GENERATOR_FILES` names them);
  `approach` is the first key in the schema and the examples; **no prompt word is a corpus stem, a queue label or
  a validation-file word** (`prompt_hygiene`, the domains, modes and example words included); grid sizes 210, 600,
  300, 181; every rendered (c) prompt is the language's text from `multilingual_prompts.json` and its hash is
  recorded; (d) stage 2's user turn carries stage 1's answer verbatim; `PROMPTS_VERSION` and the wording hash
  (append-only, a changed table fails without a bump); `wordfreq`-free rendering.
- `seeds`: the random-item path keeps only `P31 = Q5` (and `P570` under `--dead-only`); the fictional path queries
  each class once per call; a 429 is retried with the back-off and a fifth failure propagates; the throttle never
  sends two requests within 2 s (fake clock); the fetch record carries counts, sha256 and licence; the file is not
  overwritten without `--force`.
- `calls`: `custom_id` is 64 characters or fewer of the allowed set and differs across runs and stages; the
  estimate counts every call at the model's rate (`:batch` under batches); every response is recorded before it is
  parsed and charged, unparseable and `max_tokens`-stopped ones too; the once-more retry at 16,000; `--resume` sends
  nothing for an answered (family, prompt id, run, stage, model, prompt sha256, user sha256); a budget stop keeps
  the answer that crossed the cap.
- `parse`: a scripted reply with 20 items, one invalid (comma label), one five-word label, one non-ASCII label, one
  gloss not opening "This means" (kept with a note); `probability` accepted only in [0, 1]; the back-translation
  reply matched to its items by index, a short reply counted; `label_problem` truth table.
- `table`: stems of phrases and hyphenated compounds; tags truth table against a fixture corpus, `renamed_from`, a
  fixture queue with every status and a fixture registry with decided and undecided rows; `net_new` per the rule;
  `pair_completion_hint` for a `non-X` and a singleton trait and not for a paired one; the gloss of the most
  frequent reading, `gloss_divergent` from the hash embedder; merge keeps every source; **mutation test**: flipping
  every tag drops no row (under `--all` the selection is identical; under `--kept-target` only the cut's count
  moves); rerun byte-identical.
- `collapse`: Jaccard on planted runs (identical 1.0, disjoint 0.0, the median and p90); Lincoln-Petersen on
  `(10, 10, 5)` = 20 and the Chapman form on m = 0; rarefaction non-decreasing with the end slope over the last
  fifth; semantic sets merge two planted near-synonyms at the hash embedder's cosine and not two unrelated ones;
  the cross-family matrix is symmetric with ones on the diagonal; `unique_per_usd` reads the run's `usage.json`.
- `evaluate`: string recovery finds a planted corpus stem and a `renamed_from`, counts the queue apart; the model
  test table has a row per (family, model) with the five figures; the verbalized readout counts stage 2's additions
  against stage 1; `roles_summary` counts held rows and majority-`role` rows apart.
- `submit` (tmp registry, real API): one candidate per source; `score == n_sources`; `source_ref` in the documented
  form and parseable back to family, prompt and language; `partner_hint` the antonym; `candidates.jsonl` written
  before the registry append; resubmit a no-op; **cost guard**: 10,000 fake net-new rows -> estimate over $20 ->
  refused without `--confirm-expensive --confirmed-by`; 3,000 -> over the default budget refused, accepted with a
  larger `--budget-usd`; filtered rows counted out; `--top N --per-cell` stratifies by (family, model) and takes
  registered rows uncounted; `--kept-target` counts net-new kept rows at the share, the round-robin over families
  holds, a `pair_completion_hint` row outranks an equal `n_sources` row without one; dry run leaves the registry
  byte-identical and writes no run dir; `llm_entropy` absent from `FAMILIARITY_GENERATORS` (guard, with the trap in
  the comment); follow-ups name the run id, batch id, `--pipeline split` and the transport.
- `roles` (open decision 1 (a)): `promote --keys K --allow-roles` on a fixture row held as `roles` writes an entry
  with `entity_type: "role"`, the tags and the gloss draft, sets `seed_queue_stem`, and is refused for a stem in the
  role corpus or the queue; the bulk path still refuses held rows; `--dry-run` leaves the queue byte-identical;
  every existing `promote` test passes unchanged.
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; paid commands refuse over budget; `generate`
  refuses an unknown family and a `--share` outside (0, 1]; `translate-prompts` refuses to overwrite without
  `--force`; `report` renders a fixture run with the three files.
- **Acceptance on recorded outputs** (`test_gapgen_llm_entropy_acceptance.py`, skips while absent): parse rate
  >= 0.99 in every run's responses (hard); `usage.json` beside every run with nonzero cost; `person_seeds.jsonl` has
  400 real (every one with `P570` under decision 3 (a)) and 200 fictional rows and its fetch record; every (c)
  record's prompt hash is in `multilingual_prompts.json`; `collapse.json` has every family run; the pilot's and the
  wave's `report.md` carry the already-registered headline and the novel figure raw and net; the package imports no
  `openai` beyond the embedding cache; `git status --porcelain data/traits data/roles data/seed_queue.json` is empty
  except for `promote`'s own appends.
- **Manual checks, listed as such**: Roger's gloss-fidelity read (30 items per family and model arm,
  `gloss_check.md`) and the 50-row-per-family `roger_sample.md` (target >= 70% trait-and-new, as plan 09); recorded in
  the acceptance report, not asserted by a test.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_llm_entropy_*.py data_analysis/tests/test_gap_generation_llm_entropy_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/gap_generation/rubric_pins.py check
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env` copied,
`data/external/` and the embedding cache linked from the main checkout.  The boundary paragraph of § 3 goes into
every task prompt verbatim.  Each task ends with the § 8 commands.

1. Skeleton, `prompts.py` with the domains, modes, languages, spelling tables (the bigram table derived once from
   OEWN and frozen into the file with its derivation in a comment), the three rubric files pinned
   (`rubric_pins.py bump NAME --why ... --version 1`), `parse.py`; CLI `prompts`.  Test: prompts, parse.  **Paste
   the rendered variants of every family into the task report; Roger reads them before any call is made.**
2. `seeds.py`; CLI `seeds`; **run the fetch** ($0, 10-20 minutes, open decision 3).  Test: seeds.  Paste the fetch
   record and ten random seeds into the task report.
3. `calls.py` (`EntropyRunner`, both transports) and CLI `generate` with `--dry-run`; `translate-prompts`; **run the
   translation** (about $0.3, live) and paste master and back-translations side by side for Roger's read of the
   ten texts.  Test: calls.
4. `table.py`, `collapse.py`, `evaluate.py`; CLI `backtranslate`, `verbalized`, `postprocess`, `collapse`,
   `model-test`.  Test: table, collapse, evaluate.
5. **The pilot's generation** (§ 10, batched, about $6): `generate --share 0.2` for (a), (b), (e) on Haiku; (c) on
   Sonnet **and** on Haiku (the model-test arms); `--with-probabilities` on the pilot's (a) and (e) then
   `verbalized`; the 40-prompt Sonnet arms of (a), (b), (e) and (d); `backtranslate`; `postprocess`; `collapse`.
   **Gate 1**: parse rate >= 99% (hard); a family with median Jaccard above 0.6 gets one bounded prompt revision
   (text only, version bumped) and a re-run of its share; both readouts to Roger.
6. `submit.py`, `report.py`; CLI `submit`, `roles-report`, `report`; open decision 1 (a)'s `--allow-roles` in
   [promote.py](../../assistant_axis/gapgen/promote.py) and
   [gap_registry.py](../../data_analysis/gap_generation/gap_registry.py) (Fable reviews the diff).  Test: submit,
   roles, CLI.
7. **The pilot's submission** (open decision 2): `submit --top 500 --per-cell 50 --transport batches` (about
   $4.2 downstream), M1 + M3 run by Fable, `report`, `model-test`, `roles-report`: the yield-per-dollar readout
   (§ 10) with its already-registered headline, the measured net-new kept share per cell and the re-based wave
   projection; `gloss_check.md` and `roger_sample.md` to Roger.  **Gate 2 (Roger)**: the model for the rest of
   (c), (d)'s adoption, the prompt revisions if any, the roles to promote.
8. **The full grid**: `generate` for every family at `--share 1.0` on the decided models (the pilot's answers
   reused by `--resume` of the same prompt and run), (d) on every (a) and (e) call if adopted, `backtranslate`,
   `postprocess`, `collapse`, [evaluation.json](../../data/candidates/llm_entropy/evaluation.json) (not there yet;
   string recovery, the Zipf share, the rule's bite).  About $3-13
   batched by the (c) decision (§ Cost).  Stop rule inside the grid: a family whose rarefaction end slope falls
   below 1 string-unique net-new item per call after two runs of its prompts does not get its third run.
9. **Wave 1**: `submit --kept-target 300 --kept-share <the pilot's net-new figure>` (the review-hour wave), transport
   per the re-based estimate, M1 + M3, `report` (the novel figure raw and net), `roger_sample.md`, `roles-report`.
   Glossary entries ([glossary.md](./glossary.md): label-set Jaccard, Lincoln-Petersen, verbalized sampling,
   back-translation, entropy injection, net-new row and net-new kept share if plan 09's task 6 has not added them,
   review-hour wave).  Acceptance test on the recorded outputs.
10. Acceptance report (§ 11); propose the [data/README.md](../../data/README.md) paragraph for
    `candidates/llm_entropy/` in the report (do not edit it; the platform owns that file); the interface requests of
    § 12 restated for plan 13 and the platform.

## 10. Pilot

**Generation** (task 5; 20% of every family's prompts, drawn seeded, every drawn prompt with its three runs;
batched; about $6).  Calls: (a) 42 cells x 3 = 126; (b) 120 seeds; (c) 60 cells x 3 = 180 on Sonnet and 180 on
Haiku, plus 360 back-translations; (e) 36 constraints x 3 = 108; (d) stage 2 on the pilot's 234 (a) and (e) calls;
the model-test Sonnet arms: 40 prompts x 1 run of (a), (b), (e) and (d).  Readout per family (and per language
for (c), per model where both ran): parse rate; items per call; string-unique and semantic-unique counts; **median
and p90 label-set Jaccard** (the size of the intersection of two label sets over the size of their union, between
the three runs of one prompt; 1.0 is total collapse); **Lincoln-Petersen** N (the pool two runs reach, n1 n2 / m,
and the share seen so far); the rarefaction curve and its end slope (unique per call, converted to **unique per
dollar** from `usage.json`); the cross-family overlap matrix; the label-rule bite; the Zipf-below-3 share; the
registered share (how many of the unique stems the registry already holds, and how many of those are decided);
string recovery of the 932.  **Gate 1**: parse rate >= 99% (hard); a family above Jaccard 0.6 is revised once (plan
06 § 6); a family whose semantic-unique yield per dollar is under a tenth of the best family's is flagged for
Roger to drop.

**(d), the verbalized-sampling subset** (plan 06 § 3.4): stage 2's items that stage 1 of the same prompt did not
produce, as a share of stage 1's unique items, and their M1 reject rate against stage 1's once the pilot's rows are
judged.  Report-and-decide: adopt for the full grid if the addition is at least 20% and the reject rate at most
1.5x stage 1's; otherwise drop (d) and say so.

**Submission and the yield-per-dollar readout** (task 7, open decision 2, about $4.2 batched downstream).  Headline:
**the already-registered share** of the pilot's unique stems, by any generator, and how many of those rows M1 and
M3 had already decided (the proxy expects about 85% of single-word stems and 10-20% of phrases).  Then per
(family, model) cell: (i) unique per dollar, string and semantic; (ii) the M1 trait share; (iii) the **novel share
after the scorer** (M3 `new` or `grey`), **twice**: raw, and net of other generators' pending `new` candidates of
the same stem; (iv) the **net-new kept share** (kept rows per submitted row the registry had not yet filtered; it
replaces the 0.35 assumption in `select_wave`); (v) cost (generation from `usage.json`, M1 and M3 from their batch
directories); (vi) `useful_per_dollar` (rows decided new or pair-completion per dollar); the roles summary; and
the whole-grid and 300-kept projections **re-based** from (iv): rows to submit, net-new rows, novel rows raw and
net, review hours at ~150 an hour.  **The model test** (plan 06 § 3.9) is the (c) rows of the table: Sonnet 5.5
against Haiku 5.5 on the same 60 cells by (i)-(iv), with Roger's 30-gloss read per arm as the quality check.
**Rule**: the rest of (c) goes to the model with the higher net-new kept rows per dollar unless Roger's read finds
the cheaper model's glosses wrong more than twice as often; the Sonnet arms of the other families are information
only (Roger decided Haiku for them).  **Roger decides**: (a) the (c) model; (b) (d)'s adoption; (c) the roles to
promote by name; (d) any prompt revision; (e) wave 1's transport by the re-based estimate (its size is decided:
300 net-new kept rows).

## 11. Report at the end

One page at [acceptance_06_llm_entropy.md](./acceptance_06_llm_entropy.md) (not there yet): what was built against
§ 5; deviations with reasons; the § 8 commands verbatim with pass counts; the rendered prompt of every family as
sent, and the ten (c) texts with their back-translations; the seeds' fetch record; the pilot's collapse table
(Jaccard, Lincoln-Petersen, rarefaction slopes, unique per dollar, the cross-family matrix) and the prompt revision
if one happened; the (d) readout and its decision; the model test and Roger's decision; the pilot's
yield-per-dollar readout (led by the already-registered share) and the re-based projections; the full grid's
counts per family and language, the string recovery of the 932 by family, the Zipf share, the label-rule bite;
wave 1's counts (submitted, net-new, already registered and decided), M1/M3 fractions, the novel figure **twice**,
raw and net; the roles report and the promotions Roger made; the 50-row samples' verdicts and the gloss reads;
cost per model from every `usage.json` (generation, translations, embeddings, M1, M3) against the $60 line; open
QUESTIONS entries; the proposed [data/README.md](../../data/README.md) paragraph; the interface requests of § 12.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn
failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [06] question. Assumption proceeded
under: ... Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-13), proceeding under the
assumption unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start:
(1) no generator-side Zipf floor; Zipf recorded, M1's floor decides, every item carries a gloss; (2) semantic
overlap uses the scorer's OpenAI embedder through the cache, not sentence-transformers; (3) (d) is two single-turn
stages, stage 2 quoting stage 1's answer; (4) the submitted surface is always the English label; the original
form, romanisation and language live in the table and `source_ref`; (5) the ten (c) prompts are translations of one
pinned master, kept in a tracked JSON with hashes and back-translations; (6) `score` is `n_sources`, not a
familiarity; (7) role-like items are submitted like any other, M1 decides, and the route to the roles queue is
open decision 1's recommendation (`promote --allow-roles`, by name) unless Roger chooses (b); (8) the pilot's
submission is the 500-row stratified slice unless Roger chooses (b); (9) real-person seeds are the dead unless
Roger chooses (b); (10) the first wave is the review-hour wave sized on net-new kept rows at the pilot's measured
share; (11) the paid recovery harness is plan 13's pooled run, not a run of this plan's; (12) the model for the
rest of (c) follows the § 10 rule, and Roger's read can overrule it.  **Interface requests** (not changes this plan
makes): to plan 13, a `llm_prompted` mechanism in `MECHANISMS` and `(llm_entropy, <family>)` streams in `STREAMS`
with `stream_of` reading the family from `source_ref` (class `independent`: no prompt carries a corpus word; (b)'s
inputs are Wikidata, (c)'s a language), so that the dashboard's accumulation curve and Chao2 are read per family
and the generator's `collapse.json` end slopes can be printed beside the dashboard's; to plan 13 also, the
dashboard's cost line reading the run's `usage.json` per model and the translations' usage; to the platform, a
`role` entity type through promotion (open decision 1 (a), built here if chosen).  Anything that would edit a trait
or role file, the queue outside `promote`, spend over a command's budget, push the running total past $55 (the
sum of every `usage.json` under `runs/llm_entropy/`, the filter and novelty batches of its runs, the translations
and the embeddings; § Cost), fetch anything but the Wikidata seeds, use a router, add a model, or change a frozen
signature stops and asks.

## Rendered prompts (as the model receives them; one per variant)

The system turns are the pinned texts of [llm_entropy_scaffold.md](./rubrics/llm_entropy_scaffold.md),
[llm_entropy_multilingual.md](./rubrics/llm_entropy_multilingual.md) and
[llm_entropy_backtranslate.md](./rubrics/llm_entropy_backtranslate.md) (none there yet; version 1 each).  The example words below
(`punctilious`, `slow to anger`, `avoids the limelight`) pass the hygiene check today (they are the IPIP naming
rubric's); any example added later must pass `prompt_hygiene.prompt_words` against the corpus, the queue and the
validation file.  Opus renders every variant again after each edit and pastes them into the task report.

**The scaffold system turn** (families a, b, d, e; the (c) system turn is this text with the language paragraph
below in place of the "English" sentence):

```
[system]
You are helping build a list of personality traits for a research project. We already have a long list and we
want words and short phrases that are not on it, so a plain list of common trait words is of no use to us. Each
request below puts a constraint on what to name: a domain of life and a way the trait shows, a particular person,
a spelling, or a probability. Satisfy the constraint first and let it take you to less obvious words.

What counts: a stable disposition or style that a speaking persona could enact in conversation, over months and
years: a way of feeling, thinking, acting, speaking or relating to others, admirable or not. Include vices as
freely as virtues. What does not count: a role (a job, a relationship, a position), a mood of the moment, a skill,
a single act, a physical feature, a bare evaluation ("great"). If what the constraint brings to mind is one of
those, still give it, with the "kind" field saying what it is, rather than leaving it out.

Give 15 to 20 items. Labels are English, lower case, 1 to 4 words, a hyphenated compound counting as one word, and
one name each with no commas: an adjective or an adjectival phrase where English has one (for example
"punctilious" or "slow to anger"), otherwise a short descriptive phrase (for example "avoids the limelight").
Prefer words that an educated reader knows over rare or archaic ones, and prefer a phrase that names a concept
exactly over a single word that nearly does. Do not use the same word twice in different forms.

Respond with a JSON object only, no other text. Think about the constraint first, then list:
{"approach": "<one sentence on how you read the constraint>",
 "items": [{"label": "<1-4 words>",
            "gloss": "<one sentence of at most 25 words that starts 'This means' and describes the behaviour in plain words, without repeating the label>",
            "antonym": "<the opposite disposition, in the same form, or null if it has no clear opposite>",
            "kind": "<trait | membership | state | physical | role | action | evaluative | not_a_persona>",
            "ambiguity_flag": <true if the label has another common meaning that the gloss has to rule out>}, ...]}
```

**(a) domain x mode** (Haiku 5.5; user turn; `prompt_id` `a:money:habit`):

```
[user]
Domain: money. Mode: a habit.
Name 15 to 20 traits that are specifically about how a person relates to money, each in the form of a habit (a
settled thing the person does, as opposed to an attitude they hold, a way they speak, a feeling they tend to have,
a way they think, a moral stance they take, or a strategy they use with other people). Include admirable and
unadmirable ones, and ones with no common single word.
```

**(b) person seeding** (Haiku 5.5; one seed per call; the seed row of § 6; `prompt_id` `b:Q65871003`):

```
[user]
Person: Tian Yi (person, CBDB ID = 367824; died 1684).
This person may be obscure; the description is all we have, and factual accuracy about them does not matter here,
only the vocabulary. Name the 8 to 12 traits that would most distinguish such a person from a typical person of
their era, place and occupation, as those who knew them might have put it. Give the trait, its gloss, its antonym
and its kind, as instructed.
```

A fictional seed reads `Person: <name> (<description>; fictional).`

**(c) multilingual** (Sonnet 5.5 in the pilot; the system turn is the scaffold with this paragraph in place of
the "Labels are English" sentence, in the language of the call; the English master is pinned and the German text
below is the translation recorded in `multilingual_prompts.json`; `prompt_id` `c:de:money`):

```
[system, German text; the English master it translates follows in brackets]
... Beschriftungen sind auf Deutsch, in Kleinschreibung, 1 bis 4 Wörter, ein Name je Eintrag ohne Kommas. Nennen
Sie Charakterzüge, die ein Muttersprachler hier nennen würde, und bevorzugen Sie solche, für die es kein einzelnes
englisches Wort gibt. Jeder Eintrag erhält zusätzlich das Feld "romanization" (hier: die Beschriftung unverändert)
und das Feld "english_hint": null. Antworten Sie nur mit dem JSON-Objekt, in Deutsch. ...
[Labels are in German, lower case, 1 to 4 words, one name each with no commas. Name character traits a native
speaker would name here, preferring ones with no single English word. Each item also carries "romanization" (for
German, the label unchanged) and "english_hint": null. Answer with the JSON object only, in German.]

[user, German]
Lebensbereich: Geld.
Nennen Sie 15 bis 20 Charakterzüge, die speziell damit zu tun haben, wie ein Mensch mit Geld umgeht: bewundernswerte
und wenig bewundernswerte, und bevorzugt solche, für die das Englische kein einzelnes Wort hat.
[Domain: money. Name 15 to 20 character traits that are specifically about how a person relates to money,
admirable and unadmirable, preferring ones for which English has no single word.]
```

For a non-Latin script the `romanization` field carries the romanised form; `english_hint` stays null (the
back-translation call, not the generating call, chooses the English form, so that the English does not pull the
generation back to its English mode).

(The German system turn is the whole scaffold translated, not only the paragraph shown; task 3's report pastes all
ten texts in full with their back-translations.)

**The back-translation call** (Haiku 5.5; one call per (c) answer; the pinned text of
[llm_entropy_backtranslate.md](./rubrics/llm_entropy_backtranslate.md)):

```
[system]
You are given the items of a list of character traits written in one language, each with a label, a gloss and an
antonym in that language. For each item give the shortest English form of the label, at most four words, lower
case, one name with no commas: a single English word where one carries the same meaning, otherwise the shortest
phrase that does ("reads the room" is a fine label; "a person who is good at reading social situations" is not).
Translate the gloss into one English sentence of at most 25 words starting "This means", and the antonym into the
same form (or null). Flag an item as a cliché ("listicle": true) when the word is a well-known untranslatable that
names a thing, a feeling or an atmosphere rather than a disposition a person enacts (for example a word for a cosy
atmosphere, or for pleasure at another's misfortune), and give the romanisation of the original label. Keep the
items in order and keep their count. Respond with a JSON object only, no other text:
{"items": [{"index": <1-based>, "romanization": "<...>", "label": "<english, 1-4 words>", "gloss": "This means ...",
            "antonym": "<english or null>", "listicle": <true|false>}, ...]}

[user]
Language: German.
Items:
1. label: "pfennigfuchserisch"; gloss: "Das bedeutet, bei jeder Kleinigkeit um den letzten Cent zu feilschen und
   Ausgaben bis ins Lächerliche zu prüfen."; antonym: "großzügig bis zur Verschwendung"
2. label: "geldscheu"; gloss: "Das bedeutet, Geldfragen zu meiden, Rechnungen liegen zu lassen und sich bei jedem
   Gespräch über Geld unwohl zu fühlen."; antonym: null
... (the answer's 15-20 items)
```

**(d) verbalized sampling**, stage 1 (Haiku 5.5; the (a) or (e) user turn with this paragraph appended; `prompt_id`
`a:money:habit`, stage 1):

```
[user, appended]
For each item also give "probability": your estimate, between 0 and 1, of how likely you would have been to name
this item if asked this question with no further guidance. Spread the items over the range; do not give every item
the same number.
```

Stage 2 (a fresh call; the same system turn; `prompt_id` `d:a:money:habit`, stage 2):

```
[user]
Earlier, asked the following, you answered as shown.
Question: Domain: money. Mode: a habit. Name 15 to 20 traits that are specifically about how a person relates to
money, each in the form of a habit ... (the stage-1 user turn, verbatim)
Your answer: (the stage-1 reply text, verbatim)
Now give 15 to 20 further items, none of them in your answer above and none a rewording of one, to which you would
assign a probability below 0.03: traits about money as a habit that are real and nameable but that you would
almost never think of first. Same fields, including "probability".
```

**(e) spelling constraints** (Haiku 5.5; one constraint per call; three variants of the user turn; `prompt_id`
`e:bigram:sq`, `e:suffix:minded`, `e:frame:about`):

```
[user]
Spelling constraint: the label's main word begins with the letters "sq".
Name 15 to 20 traits whose label satisfies the constraint. Go through the vocabulary that fits the spelling, common
words first; a phrase whose main word fits counts. If fewer than 15 real traits fit, give the ones that do and
stop; do not invent words.
```

```
[user]
Spelling constraint: the label's main word ends in "-minded".
Name 15 to 20 traits whose label satisfies the constraint ... (as above)
```

```
[user]
Form constraint: the label has the form "X about Y", an adjective about a thing or a subject (two to four words).
Name 15 to 20 traits of that form, each about a different Y ... (as above)
```

A plausible (a) answer item (illustrative, not a recorded one): `{"label": "tithes without fail", "gloss": "This
means setting aside a fixed share of every sum received for others before spending any of it.", "antonym": "keeps
every penny", "kind": "trait", "ambiguity_flag": false}`.

## Cost (estimates; re-measured at the pilot)

Rates: Haiku 5.5 $0.10 / $0.50, Sonnet 5.5 $2 / $10 per MTok; batches x0.5.  A generating call: about 600 input
tokens and **2,500 output tokens with thinking** (the states pass measured about 500 output tokens a row on Haiku
5.5 in 20-row calls; the Haiku 5.5 readout, 2-3 times 4.5's output; plan 06 § 4's 2,000-3,000).  So a Haiku call
is about $0.0013 live / $0.0007 batched and a Sonnet call about $0.026 / $0.013; a back-translation call (about
900 in, 1,500 out) about $0.0009 live.  The pilot measures the real token counts and the estimate is corrected
before the full grid.

| step | calls | estimate (batched unless said) |
|---|---|---|
| prompt translations and their back-translations (live) | 20 | ≈ $0.3 |
| Wikidata seeds | HTTP only | $0 |
| **pilot generation** (task 5): Haiku (a) 126, (b) 120, (e) 108, (c) Haiku arm 180, (d) stage 2 234; Sonnet (c) 180 and the 160 model-test arms; 360 back-translations | ≈ 1,470 | **≈ $6** (≈ $12 live) |
| pilot submission (open decision 2 (a)): 500 net-new rows, M1 $0.0072 and M3 $0.011 at 0.88, x0.5 | | ≈ $4.2 (≈ $8.4 live) |
| **full grid**, (c) on Haiku: (a) 504 more, (b) 480 more, (c) 720 more, (e) 435 more, 540 more back-translations, (d) on every (a) and (e) call if adopted (about 1,000 more) | ≈ 2,700-3,700 | ≈ $2.5-3.5; (c) on Sonnet instead: + ≈ $9 |
| embeddings for the collapse statistics (about 60,000 strings) | cached | ≈ $0.1 |
| **wave 1**, 300 net-new kept rows at kept share 0.35: about 850 net-new rows | | ≈ $7 (≈ $14 live) |
| **total through wave 1** | | **≈ $21 with (c) on Haiku, ≈ $30 with (c) on Sonnet**; the remaining net-new rows (a second wave, Roger's word) ≈ $7-12 more |

Everything stays under Roger's $60 line with a second wave included; the running total is checked before every
paid command and a step whose estimate would push it past $55 stops and asks (§ 12).  No single command's estimate
reaches the $20 line, so `--confirm-expensive` is not expected.

**Yield and the net-new projection.**  Plan 06 § 4 expects 8-12k string-unique and 4-6k semantically distinct
candidates from the full grid.  *Measured* overlap of the nearest generators with the registry: the base-model
generator (LLM-sampled, 90% single words) had **85%** of its stems already registered by another generator (the
person family 83%); the alignment sweep (93% phrases) 7% and IPIP (85% phrases) 18%.  So of this generator's
single-word output about 15% is net-new and of its phrases about 85%; at a 60/40 or 80/20 single/multi split, 5,000
distinct candidates give about **1,450-2,150 net-new rows**, which at the base-model generator's measured kept share
(540 kept of 1,541 submitted, **35%**; multi-word rows are kept at 60% of trait rows against 56% for single words)
is **500-750 kept rows, 3.5-5 hours of review**: two or three review-hour waves.  Multi-word rows pass M1 at the
same rate as single words (87% against 63% of all filtered rows, the single-word figure dragged down by the
dictionary walks), so the phrases this generator is expected to be rich in are not a filter risk.  Roger's time:
about 1 hour on the rendered prompts and the ten translations, 30 minutes on the pilot's gloss reads and
decisions, 2 hours on the 250-row sample.

## Measured for this plan (read-only, 2026-10-13)

Measured with a throwaway script in the session scratchpad over the registry log
([registry.jsonl](../../data/candidates/registry.jsonl), 9,949 keys), the trait files, the role files and the seed
queue; the pilot's readout reproduces the registry figures as of its own date.

- **Registry**: 9,949 keys; stems of one word 7,875, two 1,393, three 448, four 227, five 6.
- **Per generator** (rows; multi-word share; share of stems also registered by another generator; M1 trait; M3
  kept of rows): base_model 1,541; 10%; **85%**; 1,355 (88%); 540 (35%).  alignment_sweep 464; 93%; 7%; 455 (98%);
  362 (78%).  ipip 514; 85%; 18%; 498 (97%); 243 (47%).  censuses 8,007; 11%; 22%; 5,139 (64%); 3,101 (39%).
- **The base-model generator by family** (rows; shared; M1 trait; M3 kept; rows M1 tagged a role): ai_assistant
  120; 70%; 91%; 32%; 0.  contrast 39; 69%; 87%; 38%; 1.  list 565; 88%; 85%; 31%; 2.  list_gloss 218; 92%; 89%;
  39%; 0.  occupation 195; 83%; 88%; 40%; 1.  **person 409; 83%; 90%; 36%; 1** (0.2%: a base model continuing an
  adjective list; an instruct model asked what distinguishes a person is expected to give more role nouns, which is
  why open decision 1 matters).
- **All filtered rows by word count**: multi-word 2,065, M1 trait 1,790 (87%), M3 new 1,066 of the trait rows
  (60%); single-word 7,872, trait 4,953 (63%), new 2,773 (56%).
- **Corpus**: 932 trait files; labels of one word 775, two 128, three 25, four 4; of the 628 single-word stems 464
  (74%) are registry stems, of the 304 multi-word stems 41 (13%) (the coordinator's figure, reproduced).  340 role
  files.
- **Queue**: 1,050 entries, 972 traits, 78 roles (61 done, 13 not_adopted, 2 exists, 2 backlog); 38 entries carry
  the `gap_gen` tag (all traits).
- **Wikidata** (eight requests, nothing written): the random-item API returned 5 items of which 1 was a human
  (`P31 = Q5`; a 1684 death, the seed row of § 6), so about a tenth of random items are humans; `wbgetentities`
  returned labels, descriptions and claims for those five as expected; of six SPARQL requests, a `COUNT` of direct
  instances of fictional character (`Q95074`) gave **4,998**, so the fictional draw must cover the subclasses
  (fictional human `Q15632617`, literary, comics, film, television, video-game and anime characters); one with an
  offset past that count returned no rows; and four sent in bursts were refused with an HTML error page (the two
  whose status was read: **HTTP 429**), hence the one-at-a-time throttle and the back-off in `seeds.py`.
- **Persona sets** (Hugging Face dataset cards, read 2026-10-13): `proj-persona/PersonaHub` licence
  `cc-by-nc-sa-4.0`; `nvidia/Nemotron-Personas` (the id plan 06 named) returns no dataset card (removed or
  renamed); `nvidia/Nemotron-Personas-USA` `cc-by-4.0`, with Korea, Japan, France and El Salvador variants whose
  licences were not read.  Not needed under the Wikidata default.

## Frozen interface (for plan 13's dashboard and the pairing review)

`from assistant_axis.gapgen.generators.llm_entropy import load_items_table, ITEMS_TABLE_PATH, load_collapse,
COLLAPSE_PATH, load_seeds, PERSON_SEEDS_PATH, EntropyRunner`: the § 6 table rows (`schema_version` 1) with
`sources`, `n_sources`, `families`, `languages`, `models`, `antonyms`, `kinds` and the membership tags for every
distinct label; the collapse payload per family (Jaccard, Lincoln-Petersen, rarefaction with end slope, unique per
dollar, the cross-family matrix); the seeds; and the generator-side Batches runner, which another generator may
reuse for its own calls.  Fields are added, never renamed, without a schema bump.  In the registry a candidate's
family, prompt and language are readable from its `source_ref` (`llm_entropy:<family>:<prompt id>:r<run>`), and
its antonym from `partner_hint`.
