# Coding plan: workstream 4, masked-LM template fill (generator id `masked_lm`)

Written 2026-10-10 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[04_masked_lm_fill.md](./04_masked_lm_fill.md) and Roger's inline answers of 2026-10-10, against the
platform's "Interface as built" in [coding_plan_platform.md](./coding_plan_platform.md).  The generator
is entirely local (BERT-class fill-mask models on the Mac, $0 in API calls); the only paid steps are the
platform's M1 and M3 on what it submits.  Roger's review comments go into this file.

## Open questions for Roger (decide when reviewing this plan)

1. **Variant B — the decision this plan needs from you** (your answer 4 asked for the proposal in plain
   words).  The workstream's beam passes ask the model to *invent* words by filling two or three
   adjacent `[MASK]` slots: keep the top-K first tokens, refill the rest conditioned on each, accept
   sequences that reassemble into words.  That is noisy (the beam favors short, common token
   sequences), and it is the only route to words the tokenizer splits (sycophantic, misanthropic) and
   to multiword labels (risk-averse, kind to animals).  **Variant B replaces invention with scoring**:
   take a fixed external candidate list — Open English WordNet's adjectives plus its person-noun
   hyponyms, roughly 20-25k words, read from the platform's own copy under
   [data/external/](../../data/external/) (`wn/`, gitignored) — splice each word's *actual* tokens into each frame, and
   score the sentence by **pseudo-log-likelihood** (mask the word's tokens one at a time, sum the
   log-probabilities the model assigns them back; the same arithmetic the trait-hood contrast score
   in § 6 of the workstream plan already uses).  Rank the list by its best frame score.
   - *Cost*: both are $0; the beam is ~45 min on MPS, Variant B ~1-2 h for 20k words × 12 frames.
   - *Recall*: Variant B handles any listed word exactly, however it tokenizes, with no beam noise; but
     its universe is WordNet's, so it cannot surface vocabulary WordNet lacks (much of the alignment
     jargon; new coinages).  The beam's universe is open but its practical recall on split words is
     untested and expected weak (workstream § 3.5).
   - *Bias*: the beam inherits the token-frequency bias twice (first-token cutoff, then continuation);
     Variant B inherits WordNet's coverage bias instead, which is at least known and inspectable.
   - **Recommendation: build both, with Variant B as the primary subword/multiword path** (its ranking
     feeds the union) and the beam passes kept at reduced K as the off-list complement, yields
     reported separately.  Both are free, and the recovery curves on the corpus's 222
     multiword/hyphenated labels (counted 2026-10-10) then settle empirically which one earns its
     place — the workstream's § 8 anticipated exactly this comparison.  The alternative is beam-only
     as the plan originally wrote.

     **Roger:** Agreed, build both, and experiment from there.  Looking at how much of the corpus the WordNet approach could not recover would also give us some idea how limiting this is, and might suggest ways to supplement WordNet.

   Operationalized (coordinator): beside the frame-scoring recovery curves, the acceptance gains a **universe
   coverage count** — how many of the corpus's bare labels (932 counted 2026-10-10, 222 of them multiword or
   hyphenated) are absent from the OEWN-derived candidate list itself, before any scoring, with the absent ones
   listed in the readout.  That number bounds what Variant B can ever recover, and its examples are the start of
   the supplement list (Moby rows, morphological expansions, hand additions).

2. **Full-wave size and transport.**  Proposed default: the top 2,000 words by union rank after
   filters, submitted through the Batches API (≈ $17 downstream at the measured census rates, § 7);
   the submit pilot's yield-per-dollar corrects this before anything is spent.

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| Worth running, with an explicit **HHH-recovery probe**: a frame-search task whose success metric is recovering [helpful](../../data/traits/instructions/helpful.json), [harmless](../../data/traits/instructions/harmless.json) and [honest](../../data/traits/instructions/honest.json) (plus a few alignment-adjacent corpus labels) in the top-K of some frame family; report which frames do it. | Roger: "Seems worth trying.  Might be particularly useful for alignment-adjacent words ... can we find a prompt that easily recovers 'helpful', 'harmless', and 'honest'?" | plan 04 § 9.1 |
| **Gender skew is a kept field, nothing more**: the she/he log-odds is recorded on the word's table row (`gender_log_odds`); no gate, no down-weighting, no separate list.  The workstream's ±2-nat flag idea is dropped. | Roger: "As long as we recover both, the gender skew doesn't seem that interesting." | plan 04 § 9.2 |
| **No generator-side frequency gate.**  [Zipf](./glossary.md#zipf) is recorded via `gapgen.freq.zipf_info` (never a local literal); the generator submits everything the platform would not hard-reject (floor **1.5**, [decisions_m1.md](./decisions_m1.md) decision 1), and the 1.5-2.5 band gets the platform filter's definition probe.  The workstream's Zipf-2.5 floor and its Qwen calibration probe are dropped. | Roger: "Other generators found that going down to 1.5, or even just 'in the list', was a better cutoff." | plan 04 § 9.3; decisions_m1 decision 1 |
| Roger's two new frames are in: **"He's habitually [MASK]"** joins the single-mask bank (subject-agnostic, so every subject instantiates it) and its two-mask form the subword-continuation pass; the bare **"[MASK][MASK]"** joins the multiword pass as the unconstrained two-slot form (no forced hyphen or function word; the tokenizer's leading-space convention classifies each completion as one reassembled word or a two-word phrase). | Roger's edits of 2026-10-10 in plan 04 §§ 1, 3.5 | plan 04 |
| **The trait-hood contrast score rides `Candidate.score`** and so lands in the registry row's `sources[]` entry (`score`); the full per-word record (log-odds, flags, ranks) lives in the generator's tracked table (§ 6), re-exported as `load_mlm_table` for other workstreams, and `score_words(...)` is public so other generators' candidates can be run through the contrast score (workstream § 7). | the registry row's source entry has exactly one score field; the by-product must stay reusable | plan 04 §§ 1, 7; interface as built |
| Words that are already corpus names stay in the wave; no selector drops `corpus_stem_match` rows. | Roger, 2026-10-10: "let the pipeline do its job" | [coding_plan_01_censuses.md](./coding_plan_01_censuses.md), last section |
| **No generator-side LLM calls.**  M1 and M3 are the platform CLIs run on this generator's rows; their `usage.json` files are the cost record.  `RunContext.finish()` writes the generator's own zero-call `usage.json`. | frozen interface; every pass here is local and $0 | platform plan, "Interface as built" |
| Generation waves run **M1 + M3 only**; the grouping run (R1) happens once, at the end, over every M3 batch. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| Models: `roberta-large` (~1.4 GB, MIT), `bert-large-cased-whole-word-masking` (~1.3 GB, Apache-2.0), `answerdotai/ModernBERT-large` (~1.6 GB, Apache-2.0; native in transformers ≥ 4.48, the lock has 4.57.6; **no `trust_remote_code` ever**).  **Each download (~4.3 GB total, into gitignored `data/external/hf/`) is a Roger approval item**; the pilot needs only roberta-large.  Tokenizer files alone (~10 MB total) suffice for task 2's census. | workstream § 2; the file-access boundary forbids checking any cache outside the repo, so the need is stated, never looked for | PLAN_FORMAT boundary; plan 04 § 2 |
| WordNet through the platform's `wn` / OEWN 2024 in `data/external/wn` (reuse the merged censuses sense helpers), **not nltk**, which is not a dependency; lemmatization via `wn`'s morphy. | the workstream named nltk before the platform existed | platform § 5; plan 04 § 2 |
| Corpus counted 2026-10-10: **932 trait files** (89 with a standard suffix; stripped of suffixes, 710 single-word and 222 multiword/hyphenated labels, 910 distinct bare forms) and **1,012 seed-queue entries** (934 traits).  These, not the plan's "387 + 867", are the tokenizer-census and recovery label sets. | count the corpus, don't trust stale figures | task brief |
| First-measurement thresholds (contrast [AUC](./glossary.md#auc) 0.85, recovery recall) are report-and-decide, not gates; parse rates, cost caps, `usage.json` presence and the untouched-corpus check stay hard. | platform review amendment 2 | platform plan |
| Code in subpackage `assistant_axis/gapgen/generators/masked_lm/`; CLI [masked_lm_generator.py](../../data_analysis/gap_generation/masked_lm_generator.py) (not written yet). | parallel generator worktrees; the censuses precedent | coding_plan_01 § 1 |

## 2. Out of scope

- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [data/seed_queue.json](../../data/seed_queue.json) (promotion is `gap_registry.py promote`, Roger's decision).
- Anything the platform owns: rubrics, probe, M3's rules, `metric_config.json`, the recovery harness internals.
- Running M1/M3/recovery itself: Fable runs the platform CLIs after the submit, per the follow-up commands.
- R1/review-app runs (one grouping run at the end of all generator waves).
- DeBERTa-v3 (no usable MLM head); any Qwen frequency probe on the pod; nltk.
- Plan 05's corpus-frequency frames; plan 11's ensemble (it may later *consume* `load_mlm_table`).

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[`provenance.md`](../../.claude/rules/provenance.md) (`json_metadata` envelopes, UTC timestamps, `usage.json` — here only the zero-call one; snapshot before overwrite),
[`entity-naming.md`](../../.claude/rules/entity-naming.md) (`normalize_to_file_name` stems, US English; this generator builds no LLM prompt, and its `gloss_hint` reaches M1 through the filter's own display path),
[`trait-pairs.md`](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are),
[`plotting.md`](../../.claude/rules/plotting.md) (the recovery-curve PNG: `png_metadata`, visual verification),
[`CLAUDE.md`](../../CLAUDE.md) (file-access boundary, the $20 rule, tests mandatory, hotlinks).
**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository
worktree (plus scratchpad and `$TMPDIR`); never list, read or stat anything else — not `~/.cache`, not
even to see whether a model is already downloaded.  Downloads go to `data/external/` inside the repo,
each after Roger's word.

## 4. Existing code to reuse

- Frozen interface from `assistant_axis.gapgen`: `Candidate`, `start_run`, `submit_candidates`, `SubmitReport`, `RunContext`, `REGISTRY_PATH`; `gapgen.paths` (`run_dir`, `check_id`, `hf_cache_dir` — importing the package pins Hugging Face to `data/external/hf` and `wn` to `data/external/wn`); `gapgen.freq.zipf_info` (floor, probe band, rescue routes); `gapgen.cost.confirm_or_abort`, `HARD_LINE_USD`; `gapgen.normalize.normalize_candidate`.
- [`generators/censuses/submit.py`](../../assistant_axis/gapgen/generators/censuses/submit.py): the submit-gate pattern copied here — the measured downstream rates (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, `M1_PASS_RATE`, `BATCH_FACTOR = 0.5`, with a `RATES_SOURCE` string), `Estimate`, `followup_commands`, the `_budget` first-of-kind cap.
- [`generators/censuses/glosshint.py`](../../assistant_axis/gapgen/generators/censuses/glosshint.py) (`adjective_senses`, `person_sense`, `gloss_hint` with `columns=()`) and [`corpus.py`](../../assistant_axis/gapgen/generators/censuses/corpus.py) (`corpus_trait_stems`, `queue_trait_stems`): merged on this branch; if a later refactor moves them, copy the ~60 lines rather than block.
- [`entity_id.py`](../../assistant_axis/entity_id.py) (`normalize_to_file_name`), [`atomic_io.py`](../../assistant_axis/atomic_io.py), [`provenance.py`](../../assistant_axis/provenance.py) + [`plot_metadata.py`](../../assistant_axis/plot_metadata.py) (`json_metadata`, `png_metadata`).
- `torch` 2.10.0 and `transformers` 4.57.6 are already locked (the workstream's "transformers 5.1" was wrong); `wordfreq` 3.1.1 and `wn` are the platform's.  **No new dependencies.**
- Test style: [`test_gapgen_censuses_submit.py`](../../assistant_axis/tests/test_gapgen_censuses_submit.py) (tmp registry through the real frozen API; fake clients).

## 5. File layout

```
assistant_axis/gapgen/generators/masked_lm/
  __init__.py    GENERATOR = "masked_lm"; MLM_DIR = DATA_CANDIDATES / "masked_lm"; MLM_TABLE_PATH
                 re-exports load_mlm_table, score_words (§ Frozen interface)
  frames.py      Frame(id, template, slot, register, kind)  kind ∈ {dispositional, state, physical, probe}
                 SUBJECTS (10); FRAME_BANK (~60 generation + ~10 state/physical contrast frames, incl.
                 "{subj} is habitually [MASK]"); PROBE_FRAMES (the HHH frame-search candidates,
                 assistant/chatbot register); instantiate(frame, subject, mask_token, n_masks) -> str
                 HHH_LABELS = ("helpful", "harmless", "honest"); PROBE_EXTRA = ("sycophantic", "obedient",
                 "transparent", "manipulative", "truthful", "deferential")   (all corpus labels)
  models.py      MODELS: dict[key, ModelSpec(hf_id, approx_gb, licence)]; load_tokenizer(key), load_mlm(key,
                 device)  (device: mps else cpu; never trust_remote_code); token_census(labels, tokenizer)
                 -> list[CensusRow(label, n_tokens, klass)]  klass ∈ {single, subword, multiword}
  singlemask.py  run_single_pass(mlm, instances, *, top_rank=2000, batch) -> dict[word, WordAgg(best_logprob,
                 best_frame, mean_rank, n_top, by_subject_logprob)]; detok, lowercase, drop non-alphabetic,
                 lemmatize via wn morphy; gender_log_odds from the she/he instances
  beam.py        subword_pass(mlm, frames, *, k_first=300, widths=(2,3)) and multiword_pass(..., k_first=100,
                 templates incl. "[MASK][MASK]", "[MASK]-[MASK]", "[MASK] to [MASK]", "[MASK]ly [MASK]",
                 "[MASK]-oriented|seeking|minded"): continuation acceptance by leading-space convention
  pll.py         pll_score(mlm, frame, word_tokens) -> float  (mask each token in turn, sum log-probs)
                 variant_b(mlm, wordlist, frames) -> dict[word, best]   (the § Open-questions path)
                 score_words(words, *, model_key, frames=CONTRAST_SET) -> dict[word, Contrast(trait_contrast,
                 state_flag, physical_flag)]   (dispositional PLL minus max over state/physical frames)
  wordlist.py    oewn_candidates() -> list[str]  (OEWN adjectives + person-noun hyponyms, deduped stems)
                 STOPLIST (demonyms, religions, nationalities: flag, never delete)
  table.py       build_table(aggregates, *, freq=zipf_info, senses, corpus_stems, queue_stems) -> rows (§ 6)
                 write_table / load_mlm_table(path=MLM_TABLE_PATH); union_rank (best_logprob desc across
                 models/passes, ties by zipf then surface); eligibility (§ 6; never reads corpus/queue fields)
  evaluate.py    recovery_curves(table, label_sets, cutoffs=(1k,2k,5k,10k,20k))  per model/pass/class
                 frequency_baseline(label_sets, top_n)   (wordfreq top-N adjectives alone)
                 frame_ablation(aggregates, factor); hhh_probe(aggregates) -> per-frame ranks of
                 HHH_LABELS + PROBE_EXTRA, and the frame families whose union top-200 holds all three
                 contrast_auc(contrasts, pos_labels, neg_labels)   (report-and-decide target 0.85)
  submit.py      estimate_downstream_usd (censuses pattern, rates + RATES_SOURCE); select_top(table, n)
                 run_submit(run_id, *, table, top_n, budget_usd, confirm_expensive, confirmed_by,
                 transport, dry_run) -> candidates.jsonl first, then submit_candidates, keys.txt,
                 submit_report.json, ctx.finish(); followup_commands (M1 --pipeline split, M3, report)
  report.py      render_report(evaluation) -> markdown; roger_sample(rows, n=50, seed=0)
data_analysis/gap_generation/masked_lm_generator.py   census | generate | score | table | evaluate | submit | report
data/candidates/masked_lm/{mlm_table.jsonl, evaluation.json, recovery_curves.png, hhh_probe.md}   tracked
data/candidates/runs/masked_lm/<run_id>/{candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json}
data/external/hf/   GITIGNORED (model weights; each download Roger-approved)
assistant_axis/tests/test_gapgen_mlm_{frames,models,single,beam,pll,table,evaluate,submit}.py
data_analysis/tests/test_gap_generation_mlm_cli.py
```

Intermediate per-model aggregates are written under `data/candidates/masked_lm/agg/` (gitignored like a
cache) so passes resume; `run.json` records device, torch/transformers versions, model revisions, the
frame-bank hash and seeds.

## 6. Data schemas

**Table row** ([mlm_table.jsonl](../../data/candidates/masked_lm/mlm_table.jsonl), not written yet; one per distinct stem, deterministic by `union_rank`; `json_metadata`
envelope on the file’s sibling `evaluation.json`, the table itself a plain JSONL like the census table):

```json
{"schema_version": 1, "surface": "sycophantic", "stem": "sycophantic", "label": "sycophantic",
 "passes": ["variant_b:roberta", "subword:bert_wwm"], "models": ["roberta-large", "bert-large-cased-whole-word-masking"],
 "best_frame": "disp_nature", "best_subject": "the new manager", "best_logprob": -3.41,
 "mean_rank": 412.0, "n_instances_top2000": 41, "gender_log_odds": -0.7,
 "trait_contrast": 2.9, "state_flag": false, "physical_flag": false,
 "zipf": 2.61, "freq_hard_reject": false, "freq_probe_band": false,
 "wordnet": {"found": true, "n_adj_senses": 1, "definition": "attempting to win favor by flattery"},
 "gloss_hint": "attempting to win favor by flattery", "stoplist_flags": [],
 "union_rank": 143, "eligible": true, "ineligible_reason": null,
 "corpus_stem_match": false, "queue_stem_match": true}
```

Rules: `stem = normalize_to_file_name(surface)`; `eligible = ¬freq_hard_reject ∨ gloss_hint present`
(rescue route 2; `masked_lm` is **not** added to `CURATED_GENERATORS` — a model walk is a dictionary
walk); `ineligible_reason ∈ {below_hard_reject, malformed}`; `stoplist_flags` flag demonyms/religions
and never drop (memberships are traits, decisions_m1 decision 3); `corpus_stem_match` /
`queue_stem_match` are evaluation-only (eligibility never reads them).

**Candidate emitted**: `Candidate(surface="sycophantic", generator="masked_lm", run_id="2026-10-20a",
rank=143, score=2.9, gloss_hint="attempting to win favor by flattery", sense_id=1,
source_ref="mlm:variant_b:roberta:disp_nature")`.  **`score` is the trait-hood contrast score**
(documented here; it is not a familiarity, so no `FAMILIARITY_GENERATORS` entry), and it lands in the
registry row's `sources[].score` — that is where other workstreams find it; the full by-product record
is the table row, via `load_mlm_table`.

**Evaluation payload** (`evaluation.json`, enveloped; numbers illustrative): `{"n_union": 9400,
"n_eligible": 2300, "recovery": {"corpus_single": {"recall@5k": 0.74}, "corpus_multi": {...},
"queue": {...}, "baseline_wordfreq": {...}}, "frame_ablation": {...}, "hhh_probe": {"winning_frames":
["assistant_always"], "ranks": {"helpful": 12, "harmless": 310, "honest": 44}}, "contrast_auc": 0.88,
"census": {"single": 710, "subword": 0, "multiword": 222}}`.

## 7. CLI

[masked_lm_generator.py](../../data_analysis/gap_generation/masked_lm_generator.py) (not written yet); common flags `--models roberta[,bert_wwm,modernbert]`,
`--frames all|pilot10`, `--device`, `--dry-run`.  No command but `submit` touches the registry, and none
makes a paid call.

- `census [--queue]`: tokenizer census of the 932 corpus labels (suffixes stripped) and the 934 queue
  trait labels per model (tokenizer files only, ~10 MB).  Prints single/subword/multiword shares.
- `generate --passes single,subword,multiword,variant_b [--top-rank 2000] [--k-first 300]`: the local
  passes; writes `agg/` per model+pass.  Dry-run prints instance counts and estimated minutes.
- `score`: the contrast score (`score_words`) over the union candidates.
- `table`: builds `mlm_table.jsonl` deterministically (snapshot `.bak.<UTC>` on change).
- `evaluate [--cutoffs ...]`: recovery curves ([recall@k](./glossary.md#recall-at-k) vs cutoff, per
  model/pass/label class), the wordfreq baseline, frame ablation, the **HHH probe**
  ([hhh_probe.md](../../data/candidates/masked_lm/hhh_probe.md), not written yet: per-frame ranks of the
  three HHH words and the six alignment-adjacent labels, and which frame families recover all three in
  their union top-200), contrast AUC, [recovery_curves.png](../../data/candidates/masked_lm/recovery_curves.png)
  (not written yet).
- `submit --run-id R [--top N] [--budget-usd 5.0] [--transport live|batches] [--confirm-expensive --confirmed-by ...]`:
  selects the top-N eligible rows, prints strata (Zipf band × corpus match) and the **downstream
  estimate** at the measured census rates (`$0.0072`/word M1 + `$0.011`/passed word M3 at the assumed
  pass rate, ×0.5 for batches; `RATES_SOURCE` names the pilots, and the M1 pass-rate assumption is
  flagged as unmeasured for this generator until its own pilot), gates with `confirm_or_abort` (over
  budget needs the flag; over $20 needs `--confirmed-by`, Roger's go), writes `candidates.jsonl`
  **before** submitting, then prints the follow-ups: `gap_registry.py submit --from ...` (main
  checkout), `traithood_filter.py --batch-id R_masked_lm --run masked_lm/R --pipeline split --transport
  <t> --budget-usd <1.5×est+2>`, `novelty_score.py score --batch-id R_masked_lm --run masked_lm/R
  --transport <t> ...`, `recovery_test.py --generator masked_lm --run-id R`, `report --run-id R`.
- `report --run-id R`: assembles the wave readout from the registry and the M1/M3 batch directories,
  sums their `usage.json` per model (the generator's own is zero-call), renders `report.md` and the
  50-row `roger_sample.md`.

## 8. Acceptance tests, written first

No test calls an API, downloads, or loads a real model; a `FakeMaskedLM` (tiny fixed vocab, deterministic
logits) and a fake tokenizer drive everything.  A real-model smoke test runs only under
`GAPGEN_RUN_LOCAL=1` with roberta-large already in `data/external/hf`.

- `frames`: unique ids; every template has exactly one slot marker; all ten subjects instantiate; the
  three kinds present; **"is habitually [MASK]" present in the bank and the bare two-slot form in the
  multiword templates**; probe frames carry the assistant/chatbot subjects; no frame or probe label set
  typo (HHH labels are corpus stems).
- `models`: census classes on a fake tokenizer (single / subword / multiword); `trust_remote_code` never
  passed (assert on the loader kwargs).
- `single`: aggregates (best log-prob, mean rank, top-2000 counting) on planted logits; detok drops
  non-alphabetic; lemmatization through a fake morphy; gender log-odds uses only she/he instances and is
  recorded, never gates (mutation test: zeroing it changes no `eligible`, no `union_rank`).
- `beam`: continuation accepted only without a leading space; the bare two-slot frame classifies a
  leading-space completion as a phrase and a continuation piece as one word; K respected.
- `pll`: a two-token word's PLL is the sum of both masked log-probs; `score_words` = dispositional minus
  max(state, physical); flags fire on planted cases; `variant_b` ranks a planted good word above junk.
- `table`: deterministic rerun is byte-identical; `union_rank` ordering; eligibility truth table uses
  `zipf_info` flags (no local 1.5 literal; a monkeypatched floor moves the outcome) and the gloss-hint
  rescue; flipping every `corpus_stem_match` changes no `eligible`; stoplist flags never drop a row.
- `evaluate`: recovery recall on a fake corpus with planted single/subword/multiword labels, per class;
  the wordfreq baseline beats/loses correctly on planted data; `hhh_probe` finds the planted winning
  frame family; `contrast_auc` is 1.0 on separable planted data.
- `submit` (tmp registry via the real frozen API): candidates carry rank = union rank, **score =
  trait_contrast**, gloss_hint, source_ref; `candidates.jsonl` written before the registry append;
  second submit of the same run is a no-op; **cost guard**: 10,000 fake rows live → over $20 → refused
  without `--confirmed-by`; over budget refused without `--confirm-expensive`; dry-run leaves the
  registry byte-identical and writes no run dir; follow-up commands name the run id, batch id,
  `--pipeline split` and the transport.
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; `report` renders a fixture evaluation.
- Acceptance on recorded outputs (skips when absent): the HHH probe result present with all nine ranks;
  contrast AUC reported (target 0.85, report-and-decide); recovery at N = 20k reported per class beside
  the wordfreq baseline; `usage.json` in every run dir with generator cost 0.0; the package imports
  neither `anthropic` nor `openai`.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_mlm_*.py data_analysis/tests/test_gap_generation_mlm_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env`
copied, `data/external/` symlinked from the main checkout.  The boundary paragraph of § 3 goes into
every task prompt verbatim.

1. Skeleton, `frames.py` (with Roger's two frames and the probe frames).  Test: frames.
2. `models.py` + CLI `census`; **ask Roger for the tokenizer-file downloads (~10 MB)**, run the census
   on the real 932 + 934 labels, paste the single/subword/multiword shares into
   [QUESTIONS.md](./QUESTIONS.md) as an information entry.  Test: models.
3. `singlemask.py` + CLI `generate --passes single`.  Test: single.
4. **Local pilot A** (§ 10, first gate): ask Roger for the roberta-large download (~1.4 GB), run ~10
   frames single-mask + the HHH probe; readout to Roger.
5. `beam.py`.  Test: beam.
6. `pll.py` (Variant B + contrast score), `wordlist.py`.  Test: pll.
7. `table.py` + CLI `table`/`score`.  Test: table.
8. `evaluate.py`, `report.py`, CLI `evaluate`.  Test: evaluate, CLI.  Add glossary entries
   (masked LM / fill-mask, pseudo-log-likelihood) to [glossary.md](./glossary.md).
9. **Full local run** per Roger's Variant-B decision (downloads 2-3 on his word, ~2.9 GB): all passes,
   3 models, recovery readout with the curves PNG, visually verified per the plotting rule.
10. `submit.py` + CLI `submit`.  Test: submit.
11. **Submit pilot** (§ 10, second gate): top ~300 by union rank, live (≈ $5 at census rates), M1 + M3
    run by Fable; yield-per-dollar readout; Roger's decision on the full wave.
12. Full wave (default top 2,000, batches, Roger's go per the $20 rule); acceptance report (§ 11);
    propose the [data/README.md](../../data/README.md) paragraph in the report (do not edit it — the platform owns that file).

## 10. Pilot

**Pilot A (local, $0, the gate the brief asks for):** one model (roberta-large), ~10 hand-picked frames
spanning the three factors, single-mask pass only, plus the **HHH probe** over the candidate probe
frames.  Readout: words/minute on MPS; the top-50 of three frames for eyeballing; recall of the 710
single-word corpus labels at N = 1k/5k/20k against the wordfreq baseline; the probe table — per frame,
the ranks of [helpful](../../data/traits/instructions/helpful.json),
[harmless](../../data/traits/instructions/harmless.json), [honest](../../data/traits/instructions/honest.json),
[sycophantic](../../data/traits/instructions/sycophantic.json), [obedient](../../data/traits/instructions/obedient.json),
[transparent](../../data/traits/instructions/transparent.json), [manipulative](../../data/traits/instructions/manipulative.json),
[truthful](../../data/traits/instructions/truthful.json), [deferential](../../data/traits/instructions/deferential.json) —
and which frame families put all three HHH words in their union top-200.  Roger decides: the frame bank
(cut the frames that only add bias), the Variant-B question if still open, and the go for the remaining
downloads and the full grid.
**Pilot B (submit, paid):** top ~300 eligible rows as run `<date>-pilot`, live transport (≈ $2.2 M1 +
≈ $2.9 M3 at the census rates — this generator's own M1 pass rate is unknown; the pilot measures it).
Readout: verdict/tag fractions by Zipf band and pass, polysemy rate, covered/new/grey, the measured
pass rate replacing the 0.88 assumption in [submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py) (not written yet), `useful_per_dollar`, the 50-row sample, and the
projected full-wave cost.  Roger decides wave size and transport (open question 2); over $20 goes
through the Batches API with his explicit go.

## 11. Report at the end

One page at [acceptance_04_masked_lm.md](./acceptance_04_masked_lm.md) (not written yet): what was built
against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the tokenizer census;
both pilot readouts and Roger's decisions; the recovery curves per class beside the wordfreq baseline
(the frames must beat it to earn their keep); the HHH probe verdict (which frames recover the three);
the contrast-score AUC; the Variant-B-versus-beam comparison on the 222 multiword labels; wave cost from
the platform `usage.json` files per model and the generator's own zero; open QUESTIONS entries.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture,
stubborn failures), then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format
(`N. [04] question. Assumption proceeded under: ... Status: open`, numbering continuing from the file's
last entry), proceeding under the assumption unless the answer would make the work useless.
Pre-registered entries Opus copies in at the start: (1) the bare "[MASK][MASK]" is read as the
unconstrained two-slot form inside each sentence frame, not a context-free input; (2) `mlm_table.jsonl`
(~1-3 MB) is tracked; (3) stoplist-flagged memberships are submitted flagged, never dropped; (4)
corpus-stem matches are submitted (Roger's 2026-10-10 ruling); (5) `Candidate.score` carries the
contrast score and is not registered as a familiarity; (6) model revisions are recorded in `run.json`
and MPS/CPU rank differences are tolerated (the table is rebuilt deterministically from recorded
aggregates, not re-sampled).  Anything that would edit a trait file or the queue, spend over a command's
budget, download without Roger's word, or change a frozen signature stops and asks.

## Frozen interface (for other workstreams)

`from assistant_axis.gapgen.generators.masked_lm import load_mlm_table, MLM_TABLE_PATH, score_words`:
the § 6 table row (`schema_version` 1) with `trait_contrast`, `gender_log_odds`, `zipf`, `union_rank`,
`passes` for every union word — plan 11's ensemble and any generator wanting the trait-hood contrast
score on its own candidates (`score_words(words, model_key="roberta")`, local, $0) build on these.
Fields are added, never renamed, without a schema bump.  In the registry, the contrast score of a
submitted word is its `masked_lm` source entry's `score`.
