# Coding plan: workstream 5, corpus frames (generator id `corpus_frames`)

Written 2026-10-13 (Fable) in the [PLAN_FORMAT.md](./PLAN_FORMAT.md) shape from
[05_corpus_frames.md](./05_corpus_frames.md) with Roger's inline answers of 2026-10-13 (decisions) and his
frame-bias point (§ 9 item 6, consequences paragraph), against the "Interface as built" section of
[coding_plan_platform.md](./coding_plan_platform.md), the masked-LM generator ([plan 04](./coding_plan_04_masked_lm.md),
its [pilot A readout](../../data/candidates/masked_lm/readout.md) of 2026-10-13) and plan 09's wave sizing
([coding_plan_09_structural_generators.md](./coding_plan_09_structural_generators.md), decision 1).  The generator
harvests the words English speakers use of people by counting the fillers of **lexical frames** ("a very X person",
"known for his X", "an incorrigible X") in the Google Books n-grams, one ranking per frame, merged by rank so that no
frame dominates; the platform's M1 (the trait-hood filter) and M3 (the novelty scorer) do the filtering and scoring.
**The generator makes no LLM call**, so there is no prompt to render.  Terms: the [glossary](./glossary.md); the ones
this plan introduces (frame, filler, shard, head-peeking, document frequency, lift, reciprocal-rank fusion, yield, net
filter, unique contribution, net-new row) are defined on first use below and go into the glossary in task 8.  Every
figure marked *measured* was measured read-only on 2026-10-13 (§ "Baseline measured for this plan").  Roger's review
comments go into this file.

## Open decisions (Roger's, at plan review; labelled OPEN until decided)

1. **OPEN: how much of the Books stream the first build buys.**  The workstream plan priced variant A at "15-25
   shards, 6-10 GB"; a **shard** is one of the 6,881 gzipped files of the 3-grams (6,668 for the 4-grams), globally
   sorted, so that a frame with a fixed prefix occupies a contiguous run of them.  *Measured*: a 3-gram shard is
   0.55-0.56 GB and a 4-gram shard 0.47-0.54 GB compressed, not ~390 MB, and the eight anchors probed span one or two
   shards each (§ "Baseline").  The frame bank of § 6 has two tiers; tier 1 (one to three frames of every syntactic
   type) is about **30 shards, about 16 GB streamed**, nothing stored but the matching lines (tens of MB).  The
   stream is free of charge (a public bucket) but is a download over 2 GB, so it needs Roger's go at the time and a
   delete-when-done line (his rule of 2026-10-10; § "Cost").
   - (a) **Tier 1, about 30 shards, about 16 GB**; tier 2 (the rarer degree adverbs, the second copular and habitual
     forms, four more nominal anchors; about 20 shards more) only if the pilot's per-frame readout says a type is
     under-represented.
   - (b) Both tiers at once, about 50 shards, about 27 GB, one approval.
   - (c) A reduced tier 1 (drop `so`, `rather`, `quite` and four nominal anchors), about 20 shards, about 11 GB.
   - **Recommendation: (a).**  `locate` (§ 7) prints the exact shard count and GB for the chosen tier before anything
     streams, from head-peeks costing about 1 MB; Roger approves the stream on that figure, not on this estimate.
2. **OPEN: the text corpora (variant B), and spaCy.**  Roger's answer 3 rules the synthetic Nemotron personas out
   ("other generators cover that") and rules in personas "others have generated and then applied any curation or
   selection to": that is PIPPA's `bot_description` (human-written Character.AI bot descriptions, selected by their
   users; *measured* 257 MB deduped, Apache-2.0, not gated, tagged not-for-all-audiences, which answer 2 accepts) and
   the 5,755 character cards (2.2 MB, CC BY 4.0).  Books cannot locate the filler-first frames ("X to a fault", "X by
   nature"), which a text corpus can; and a text corpus gives the example sentences the workstream wanted.
   - (a) **Not in this plan.**  Books only; the text corpora are a second build in the same package after the Books
     readout, with their own approval (about 260 MB) and the same frame bank applied as regexes over sentences, **no
     spaCy** (the frames are fixed strings around one slot; a dependency parser adds the `amod`/`acomp` sweep, which
     is a separate frame family with its own bias and its own measurement).
   - (b) In this plan as a second phase after the pilot, regex frames, no spaCy.
   - (c) In this plan with spaCy (`en_core_web_sm`, about 13 MB, MIT) for the dependency sweep as well.
   - **Recommendation: (a)**, so that the frame-bias measurement is made on one source first and the second build
     inherits a measured bank.  `datasets` is not needed in any option (the files are fetched by URL, as the IPIP
     pages are; parquet reads through `pyarrow`, already a dependency).  **No new dependency in this plan.**
3. **OPEN: nominal fillers with no adjective.**  Roger's answer 4 includes nominal traits (pedant, gossip, yes-man)
   with adjectival relabels.  *Measured* on the repository's OEWN copy: the `derivation` link gives an adjective for
   about half of thirty nominal traits tried (pedant → pedantic, sycophant → sycophantic, gossip → gossipy, coward →
   cowardly, miser → miserly, snob → snobby, cynic → cynical) and nothing for the rest (hypocrite, busybody, yes-man,
   liar, optimist, zealot, perfectionist, procrastinator).
   - (a) **Deterministic only**: [`normalize_form`](../../assistant_axis/gapgen/generators/base_model/parse.py)'s
     suffix rules, then the OEWN `derivation` link; a noun with neither is submitted **as the noun**, with its OEWN
     person-sense gloss, and M1 decides (it may hold some on the roles list, tag `role_person`); the readout counts
     them per frame and lists them, and Roger's answer 4 ("they're still useful for clustering") covers the ones M1
     passes.
   - (b) A Haiku 5.5 relabel call for the nouns (a) leaves (about $0.01 per hundred; a pinned rubric and a rendered
     sample before any call).
   - **Recommendation: (a)** for the first build, (b) as a follow-up task if the pilot's unrelabelled count is large
     (over about 100 in the wave).

If a decision is unanswered when Opus reaches the step, it proceeds under the recommendation and records that in
[QUESTIONS.md](./QUESTIONS.md) (§ 12).

## 1. Decisions already made

| decision | reason | source |
|---|---|---|
| **Books year cutoff 1920**: a filler's counts are summed over years >= 1920 (match count and volume count both). | Roger, 2026-10-13: "Maybe 1920?" | plan 05 § 9.1 |
| **NSFW-flagged and non-commercial inputs are acceptable** (PIPPA, PersonaHub): a licence or content flag is never a reason to leave a source out.  PersonaHub stays out for a different reason (synthetic, and *measured* 301 GB). | Roger, 2026-10-13: "NSFW is not something we're trying to filter out" | plan 05 § 9.2 |
| **Synthetic LLM personas are out** (Nemotron-Personas-USA, PersonaHub, FinePersonas); **curated or selected personas are in scope** (PIPPA, the character cards), as a second build (open decision 2). | Roger, 2026-10-13 | plan 05 § 9.3 |
| **Nominal traits are in, with adjectival relabels** where a deterministic relabel exists (open decision 3); the original noun is kept on the table row (`surface`) and the label is the relabel. | Roger, 2026-10-13: "we can shift grammatical form easily enough" | plan 05 § 9.4 |
| **Review starts with an hour on the most novel survivors**: `report` writes `roger_first_hour.md`, the ~150 kept rows furthest from the corpus by M3's nearest cosine, `new` before `grey`. | Roger, 2026-10-13 | plan 05 § 9.5 |
| **Frames across syntactic types, each frame's yield and net filter measured, frames merged by within-frame rank, low-yield or strongly filtering frames kept only if they add labels no other frame finds, the report naming the contributing frame of every new label** (§ 6 bank, § 8 tests, § 10 readout). | Roger, 2026-10-13, item 6 | plan 05 § 9.6 |
| **The platform's M1 replaces the workstream's two filter stages** (the local model and the Haiku stage): M1 gives verdict, sense, gloss, alignment score and region; **no generator-side LLM call**, so `RunContext.finish()` writes a zero-call `usage.json`. | the interface as built; plan 04's precedent | platform plan |
| **Background frequency is `wordfreq`'s Zipf through [`freq.zipf_info`](../../assistant_axis/gapgen/freq.py)**, never the Books 1-grams (24 shards, about 6 GB more).  Zipf is recorded on every row and is **not a generator-side gate** (floor 1.5 is the platform's, [decisions_m1](./decisions_m1.md) decision 1; `eligible = not hard_reject or gloss_hint`, plan 04's rule). | plan 04 § 9.3 (Roger: "going down to 1.5 ... was a better cutoff") | plan 04 |
| **Within-frame rank by document frequency (volumes), with lift as the alternative ordering, decided on the free recovery check** (§ 8): whichever ordering recovers more corpus labels at depth 1,000 in the union becomes the default and the other stays a column. | a $0 empirical choice; the workstream's log-odds was for a different background | this plan (pre-registered) |
| **Frames are merged by reciprocal-rank fusion** (RRF, k = 60) over within-frame ranks; a word's `rank` is its RRF rank; `score` is `n_frames` (how many frames found it: a quality signal, **not** a familiarity, so `corpus_frames` is never added to `FAMILIARITY_GENERATORS`, guard test as [QUESTIONS 58](./QUESTIONS.md)). | Roger's item 6 (3): "reciprocal-rank or max" | plan 05 § 9.6 |
| **Every row is submitted, none dropped by its tags**: a corpus stem, a queue entry or a stem another generator registered goes in (the registry merges by key; M1 and M3 skip rows another run decided); the counts, the estimate and the wave's target cover **net-new rows** only. | Roger, 2026-10-10: "let the pipeline do its job"; plan 09 decision 1 | [coding_plan_01_censuses.md](./coding_plan_01_censuses.md) last section; plan 09 |
| **The first wave is the review-hour wave sized on net-new kept rows** (`submit --kept-target 300 --kept-share <pilot's measured net-new kept share>`): about two hours of review at the measured rate (146 terms an hour active on the TDA batch, plan 13 § 6; the 150 of plans 04 and 09).  When plan 13's `assistant_axis.gapgen.testing.pooled_review_rate` lands, `select_wave` reads it; until then the constant, flagged. | Roger, plan 09 decision 1 and plan 04 ("aim for ~2 hours review") | plans 04, 09, 13 |
| **Generation waves run M1 + M3 only**; grouping (R1) once at the end over every batch. | Roger, 2026-10-10 | [coding_plan_review.md](./coding_plan_review.md) § 10 |
| **Transport**: the pilot live; the wave live when its re-based estimate is under $20, batched with Roger's go above it. | the batch-or-real-time rule | [CLAUDE.md](../../CLAUDE.md) |
| **Downloads**: the Books stream and any text corpus go through a `download`/`stream` command that records URL, bytes, sha256 of what was kept, the licence and Roger's go in a `DOWNLOAD_MANIFEST.json` under `data/external/` (the IPIP convention, [ipip/download.py](../../assistant_axis/gapgen/generators/ipip/download.py)); a source without a recorded approval is refused unless `--approved-by '<Roger, date>'` names his go. | the file-access boundary; the IPIP precedent | PLAN_FORMAT |
| **The frames table is git-ignored** with its sha256 in the tracked `evaluation.json` and `run.json` (the masked-LM table's rule, [QUESTIONS 80](./QUESTIONS.md)); the per-frame statistics, the shard plan and the readout are tracked. | the table is several MB and deterministic from the extracts | QUESTIONS 80 |
| Code in `assistant_axis/gapgen/generators/corpus_frames/`; CLI [corpus_frames_generator.py](../../data_analysis/gap_generation/corpus_frames_generator.py) (not there yet); generator id `corpus_frames`; `source_ref` `frames:books:<frame_id>`. | the censuses precedent | coding_plan_01 § 1 |
| **Counts as of 2026-10-13, used throughout**: 932 trait files (710 single-word, 222 multiword, 154 of those hyphen-only); the seed queue 1,050 entries (972 traits); the registry snapshot 9,941 stems, 9,893 of them decided by M1 and M3; corpus regions cognitive_epistemic 203, emotional_temperament 166, social_interpersonal 165, identity_demographic 150, moral_stance 143, communication_style 95, alignment_ai_agent 10. | counted, not copied (the workstream's "387 labels" is the April count) | this plan |

## 2. Out of scope

- Nemotron-Personas-USA, PersonaHub, FinePersonas (synthetic); wiki_bio (factual, low trait density); the Gutenberg
  subsample (Books covers printed books, and 1920 is the cutoff); the Books 1-grams.
- spaCy, `datasets`, any dependency parse (open decision 2); any generator-side LLM call (open decision 3b is a
  follow-up, not this plan).
- Any edit to `data/traits/**`, `data/roles/**`, the TO_ADD files, [seed_queue.json](../../data/seed_queue.json) or
  any trait file's `arrangement`; promotion (`gap_registry.py promote`, Roger's); R1 and the review app.
- Anything the platform owns: rubrics of M1/M3, cut-offs, [metric_config.json](../../data/candidates/metric_config.json),
  the recovery harness internals; scorer verification spend (M1/M3 belong to the platform's budget lines, printed by
  `submit`).
- The reusable "how often is W used of a person in Books" lookup for other generators (plan 05 § 7): it falls out
  of the table (`load_frames_table`, § Frozen interface) and needs no code of its own.

## 3. Rule files to Read first

Open with the **Read tool** before touching code:
[provenance.md](../../.claude/rules/provenance.md) (`usage.json` beside every run, here the zero-call one;
`json_metadata` envelopes; UTC timestamps; snapshot before overwrite),
[entity-naming.md](../../.claude/rules/entity-naming.md) (file-name stems via `normalize_to_file_name` for every key;
US English: a UK-spelt filler is folded by `normalize_form`'s `us_spelling` and the raw surface kept),
[trait-pairs.md](../../.claude/rules/trait-pairs.md) (what a trait, a pair and the seed queue are; the "Trait-gap
platform" paragraph),
[plotting.md](../../.claude/rules/plotting.md) (the recovery-curves PNG: `png_metadata`, visual verification),
[CLAUDE.md](../../CLAUDE.md) (file-access boundary, the $20 confirmation rule, **tests are mandatory**, hotlinks).
No judge prompt is written, so [judging.md](../../.claude/rules/judging.md) is not needed; if open decision 3b is
ever built, Read it first.

**File-access boundary, restated for every Opus task prompt**: read and write only inside the repository worktree,
the agent's scratchpad and `$TMPDIR`; never list, read or stat anything else under the home directory, not
`~/.cache`, not even to see whether something is downloaded.  Every download goes to `data/external/` inside the
repository, after Roger's go, recorded in the manifest; the Books stream is a download (over 2 GB) although nothing
of it is stored but the matching lines.  Never open `.env`.

## 4. Existing code to reuse

- Registry API from `assistant_axis.gapgen`: `Candidate`, `start_run`, `submit_candidates`, `SubmitReport`,
  `RunContext` ([registry.py](../../assistant_axis/gapgen/registry.py), [runs.py](../../assistant_axis/gapgen/runs.py):
  `record_candidates` before the append, `finish()` writes `run.json` and `usage.json`); `paths.run_dir`, `check_id`,
  `DATA_EXTERNAL`, `CORPUS_REGIONS_PATH`, `SEED_QUEUE_PATH`; `normalize_candidate`, `make_key`
  ([normalize.py](../../assistant_axis/gapgen/normalize.py): `STOPWORDS` is the function-word list the filler regex
  also excludes).
- [cost.py](../../assistant_axis/gapgen/cost.py): `confirm_or_abort`, `HARD_LINE_USD`; [freq.py](../../assistant_axis/gapgen/freq.py)
  `zipf_info` (the floor, the probe band, the rescue routes; never a local 1.5 literal).
- **The submit recipe of [masked_lm/submit.py](../../assistant_axis/gapgen/generators/masked_lm/submit.py)**: the
  measured rates (`M1_USD_PER_WORD = 0.0072`, `M3_USD_PER_PASSED_WORD = 0.011`, `M1_PASS_RATE_ASSUMED = 0.88`,
  `BATCH_FACTOR = 0.5`, `RATES_SOURCE`), `estimate_downstream_usd`, `registry_stems` (stems in the registry and those
  M1 or M3 has still to decide), `_take` / `select_wave` (registered rows ride along uncounted), the review-load guard
  (`REVIEW_OVERSHOOT`, `ReviewLoadExceeded`), `followup_commands`, the `_budget` first-of-kind cap.  Import what fits
  the signature; copy the rest (plan 09 did the same).
- [censuses/glosshint.py](../../assistant_axis/gapgen/generators/censuses/glosshint.py) (`adjective_senses`,
  `person_sense`, `gloss_hint(label, hint, columns=())`), [censuses/corpus.py](../../assistant_axis/gapgen/generators/censuses/corpus.py)
  (`corpus_trait_stems`, `corpus_renamed_from`, `queue_trait_stems`), [censuses/ingest.py](../../assistant_axis/gapgen/generators/censuses/ingest.py)
  `zipf_band`; [wordnet.py](../../assistant_axis/gapgen/wordnet.py) (`oewn`, `sense_info`, `adjective_lemmas`);
  [base_model/parse.py](../../assistant_axis/gapgen/generators/base_model/parse.py) `normalize_form_kind` (the
  `-ness`/`-ity` and noun-suffix rules, `us_spelling`, the `Lexicon` of OEWN adjectives and nouns);
  [masked_lm/wordlist.py](../../assistant_axis/gapgen/generators/masked_lm/wordlist.py) `person_noun_lemmas` (the
  OEWN person-noun hyponyms: the person-noun test of the nominal frames) and `stoplist_flags`.
- [masked_lm/evaluate.py](../../assistant_axis/gapgen/generators/masked_lm/evaluate.py): `corpus_labels`,
  `queue_labels`, `bare_label`, `recall_at`, `recovery_curves`, `frequency_ranking` (the wordfreq baseline the frames
  must beat); [masked_lm/table.py](../../assistant_axis/gapgen/generators/masked_lm/table.py) `write_table` /
  `load_mlm_table` (the git-ignored-table pattern with `file_sha256`).
- The download convention of [ipip/download.py](../../assistant_axis/gapgen/generators/ipip/download.py)
  (`_urlopen_bytes` with range resumption, `DownloadManifest`, `NotApproved`, `--approved-by`) and
  [ipip/sources.py](../../assistant_axis/gapgen/generators/ipip/sources.py) (`Source` with `approval`, `licence`).
- [entity_id.py](../../assistant_axis/entity_id.py) `normalize_to_file_name`, `resolve_renamed_stem`;
  [atomic_io.py](../../assistant_axis/atomic_io.py); [provenance.py](../../assistant_axis/provenance.py) and
  [plot_metadata.py](../../assistant_axis/plot_metadata.py) (`json_metadata`, `png_metadata`).
- Test style: [test_gapgen_censuses_submit.py](../../assistant_axis/tests/test_gapgen_censuses_submit.py) (tmp
  registry through the real API), the masked-LM tests' fake lexicon and fake tokenizer.  **No new dependencies.**

## 5. File layout

```
assistant_axis/gapgen/generators/corpus_frames/
  __init__.py    GENERATOR = "corpus_frames"; FRAMES_DIR = DATA_CANDIDATES / "corpus_frames"; TABLE_PATH (gitignored);
                 SHARD_PLAN_PATH; FRAME_STATS_PATH; EVALUATION_PATH; CURVES_PNG_PATH; READOUT_PATH;
                 EXTERNAL_DIR = DATA_EXTERNAL / "books_ngrams"; DOWNLOAD_MANIFEST_NAME; re-exports load_frames_table,
                 person_frequency (§ Frozen interface)
  frames.py      TYPES = ("degree", "nominal", "possessive", "copular", "tendency", "habitual"); Frame(id, type, n,
                 prefix: tuple[str, ...], slot: int, suffix: frozenset[str] | None, tier, filler_kind: "adj" | "noun" |
                 "quality_noun", note); PERSON_NOUNS (22); FRAME_BANK (§ 6); frames_for(tier) ; regex_for(frame) ->
                 re.Pattern (plain lowercase tokens only: no `_TAG` suffix, no `_ADV_` wildcard, no capital);
                 bank_sha256()
  books.py       BASE_URL; N_SHARDS = {3: 6881, 4: 6668}; shard_url(n, i); head_ngram(n, i, *, fetch) (a 4 KB range
                 request, the first line decompressed); locate(n, prefix, *, fetch) -> (start, end, heads) (binary
                 search over heads; the end key is prefix + "\x7f", since untagged n-grams sort before their `_TAG`
                 forms); shard_plan(frames, *, fetch) -> ShardPlan (every shard once, the frames it serves, GB from
                 HEAD Content-Length); stream_shard(url, patterns, *, year_min=1920, fetch_stream) -> dict[frame_id,
                 list[Hit]] (curl | zcat equivalent in Python: gzip over a streaming response, one pass, every
                 frame's regex applied to each line; Hit(filler, noun, match, volumes)); write_extract(hits, path)
                 (the kept lines as TSV under EXTERNAL_DIR); manifest entries (bytes streamed, lines kept, sha256 of
                 the extract, approval)
  table.py       build_table(extracts, *, lexicon, zipf, senses, corpus_stems, renamed, queue_stems, registry) ->
                 rows (§ 6): per (frame, filler) the summed match and volumes over years >= 1920, the frame floor
                 (match >= 40), the within-frame ranks by volumes and by lift, the relabel (relabel.py), the stem,
                 Zipf via zipf_info, the OEWN gloss hint, the tags; rrf(ranks_by_frame, k=60) -> fused order;
                 union_rank; write_table / load_frames_table (gitignored, sha256 recorded); frame_stats(rows) -> per
                 frame: n_fillers, n_above_floor, n_adj / n_noun / n_phrase, n_registered, n_corpus
  relabel.py     relabel(surface, *, lexicon, derivation) -> Relabel(label, form, rule) (rule in normalize_form_kind's
                 vocabulary plus "derivation", "none"); derivation_adjectives(noun) (OEWN `derivation` sense relation,
                 adjective targets only); is_person_noun(noun) (masked_lm.wordlist's person-noun hyponyms)
  evaluate.py    recovery_curves(table, label_sets, cutoffs=(500, 1000, 3000, 10000)) per frame and for the union
                 under both orderings, beside the wordfreq baseline; unfound_labels(table, corpus) (the corpus labels
                 no frame finds, by region); frame_measures(table, registry) -> per frame: yield (M1 trait share of
                 its pilot fillers), region_tv and form_tv (total variation distance of its trait fillers' region and
                 form distributions from the union's), physical_state_share (M1 `physical` / `state` tags among its
                 registered fillers), unique_kept (M3-kept rows only this frame found); keep_frame(measure, *,
                 yield_min=0.4, tv_max=0.5) -> (keep: bool, why); ordering_choice(curves) (§ 1: volumes or lift)
  submit.py      estimate_downstream_usd (imported); select_top(table, n_per_frame) (the pilot: the top n of every
                 frame by within-frame rank, deduplicated; registered rows ride along, § 10); select_wave(table, *,
                 kept_target, kept_share, registered_stems, pending_stems, frames_kept) (the first `ceil(K / share)`
                 net-new rows by union rank over the frames kept after the pilot; registered rows inside the cut
                 submitted and not counted; the review-load guard); to_candidates(rows, run_id); run_submit(run_id,
                 *, table, top_per_frame | kept_target, kept_share, budget_usd, confirm_expensive, confirmed_by,
                 transport, dry_run); followup_commands
  report.py      render_readout(evaluation, frame_stats, run) -> markdown (§ 10 order); roger_sample(rows, n=50,
                 seed=0); roger_first_hour(rows, registry, n=150) (the most novel kept rows, § 1);
                 contributing_frames(rows) -> {stem: [frame ids]} (which frame contributed each new label)
data_analysis/gap_generation/corpus_frames_generator.py
                 locate | stream | table | evaluate | submit | report
data/external/books_ngrams/{<frame_id>.tsv ..., DOWNLOAD_MANIFEST.json}          GITIGNORED (the kept lines)
data/candidates/corpus_frames/{shard_plan.json, frame_stats.json, evaluation.json, recovery_curves.png, readout.md}
                 tracked; frames_table.jsonl gitignored (sha256 in evaluation.json and run.json)
data/candidates/runs/corpus_frames/<run_id>/{candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json,
                 report.md, roger_sample.md, roger_first_hour.md}
assistant_axis/tests/test_gapgen_corpus_frames_{frames,books,table,relabel,evaluate,submit,acceptance}.py
data_analysis/tests/test_gap_generation_corpus_frames_cli.py
```

## 6. Data schemas

**The frame bank** (`frames.py`; the n-gram shape, the fixed prefix that places the frame in the shards, the slot the
filler takes and the suffix set that closes it).  **A frame** is a fixed string with one slot; its **fillers** are the
words that occupy the slot in the corpus; its **document frequency** is the number of books (`volumes`) a filler
appears in with that frame, summed over years >= 1920.  Six syntactic types, as Roger's item 6 asks, so that no one
grammatical filter shapes the union:

| id | type | n | the n-gram (slot in **bold**) | filler | tier |
|---|---|---|---|---|---|
| `d_very`, `d_too`, `d_so`, `d_rather`, `d_quite`, `d_extremely` | degree | 3 | `very` **X** `<person noun>` | adj | 1 |
| `d_utterly`, `d_notoriously`, `d_hopelessly`, `d_thoroughly`, `d_remarkably`, `d_chronically`, `d_famously`, `d_incurably` | degree | 3 | the same | adj | 2 |
| `d_too_to` | degree | 3 | `too` **X** `to` (the `too` block, free with `d_too`) | adj | 1 |
| `n_incorrigible`, `n_inveterate`, `n_notorious`, `n_shameless`, `n_hopeless`, `n_born`, `n_confirmed`, `n_compulsive` | nominal | 3 | `an incorrigible` **X** (X a person noun, `is_person_noun`, or a noun `relabel` folds) | noun | 1 |
| `n_habitual`, `n_chronic`, `n_natural`, `n_total` | nominal | 3 | the same | noun | 2 |
| `p_known_for_his`, `p_known_for_her`, `p_man_of`, `p_woman_of`, `p_reputation_for` | possessive | 4 / 3 | `known for his` **X**; `man of` **X**; `reputation for` **X** | quality noun (honesty → honest by `relabel`) | 1 |
| `p_noted_for_his`, `p_famous_for_his` | possessive | 4 | the same | quality noun | 2 |
| `c_was_a`, `c_was_an` | copular | 4 | `was a` **X** `<person noun>` | adj | 1 |
| `c_is_a`, `c_seemed_a` | copular | 4 | the same | adj | 2 |
| `t_tendency`, `t_inclined`, `t_apt` | tendency | 4 | `tendency to be` **X**; `inclined to be` **X**; `apt to be` **X** | adj | 1 |
| `h_he_was_always`, `h_she_was_always` | habitual | 4 | `he was always` **X** | adj | 1 |
| `h_he_is_always`, `h_she_is_always` | habitual | 4 | the same | adj | 2 |

`PERSON_NOUNS` (the suffix set of the degree and copular frames, recorded per hit): person, man, woman, fellow,
people, character, individual, soul, chap, lady, guy, girl, boy, gentleman, creature, child, youth, friend,
companion, neighbor, neighbour, master.  The filler regex is `[a-z]+(?:-[a-z]+)*` (hyphenated compounds kept), never a
`STOPWORDS` word, never a token with a `_TAG` or a wildcard, never a capital (so sentence-initial and proper-adjective
fillers such as "very Christian man" are lost: a known gap, counted in the readout; memberships are the censuses'
and plan 04's ground).  Filler-first frames ("X to a fault", "X by nature", "X at heart") are **not in the bank**:
every n-gram starting with X lies in a different shard, so Books cannot locate them; plan 04's bank has them, and
the text corpora of open decision 2 can.  Every row of the bank is in `bank_sha256()`, recorded in the shard plan,
the table and every run.

**Shard plan** ([shard_plan.json](../../data/candidates/corpus_frames/shard_plan.json), not there yet; enveloped;
figures from the 2026-10-13 probe, illustrative for the rest):

```json
{"tier": 1, "bank_sha256": "…", "shards": [
   {"n": 3, "index": 6650, "url": "https://storage.googleapis.com/books/ngrams/books/20200217/eng/3-06650-of-06881.gz",
    "bytes": 559662912, "frames": ["d_very"], "head": "vertically upon_ADP the"},
   {"n": 3, "index": 3205, "bytes": 548551340, "frames": ["n_incorrigible"], "head": "an electromagnetic four"}],
 "n_shards": 30, "total_gb": 16.1, "head_peek_bytes": 1049000, "approval": null}
```

**Table row** ([frames_table.jsonl](../../data/candidates/corpus_frames/frames_table.jsonl), not there yet,
gitignored; one per distinct stem; deterministic from the extracts; the example is made up):

```json
{"schema_version": 1, "surface": "pedant", "label": "pedantic", "stem": "pedantic", "form": "adjective",
 "relabel_rule": "derivation", "us_spelling_from": null,
 "frames": {"n_incorrigible": {"match": 812, "volumes": 655, "rank_volumes": 7, "rank_lift": 3, "nouns": []},
            "n_born": {"match": 96, "volumes": 88, "rank_volumes": 41, "rank_lift": 22, "nouns": []}},
 "n_frames": 2, "best_frame": "n_incorrigible", "types": ["nominal"],
 "rrf": 0.0313, "union_rank": 212, "rank_lift_union": 148,
 "zipf": 2.9, "freq_hard_reject": false, "freq_probe_band": false,
 "wordnet": {"found": true, "pos": "n", "definition": "a person who pays more attention to formal rules and book learning than they merit"},
 "gloss_hint": "a person who pays more attention to formal rules and book learning than they merit",
 "eligible": true, "ineligible_reason": null,
 "corpus_stem_match": false, "queue_stem_match": false, "registered": false, "registered_decided": false}
```

Rules: a filler counts in a frame only at or above the **frame floor** (`match >= 40` over years >= 1920, the
workstream's floor); `stem = normalize_to_file_name(label)` after `relabel`; `rank_volumes` is the filler's rank
within the frame by `volumes`; **lift** is `log10(volumes / frame_total_volumes) - (zipf - 9)`, the filler's share of
the frame against its share of English (`wordfreq`'s Zipf is log10 occurrences per billion words), which demotes
good, old, little and promotes disposition words; `rank_lift` ranks by it among the fillers above the floor;
**reciprocal-rank fusion** gives each word `sum over frames of 1 / (60 + rank)` and `union_rank` orders by it (a word
that heads a small frame outranks one at rank 50 in `d_very`; doubling every count of one frame changes no order);
`eligible = not freq_hard_reject or gloss_hint present` (plan 04's rule); `registered` and `registered_decided` as
plan 09 § 6 defines them.  A row is **net-new** when the registry has not yet filtered it: not `corpus_stem_match`,
not `queue_stem_match`, not `registered_decided`.  **No tag drops a row** (mutation test, § 8).

**Candidate emitted** (one per stem): `Candidate(surface="pedantic", generator="corpus_frames", run_id="2026-10-20-pilot",
rank=212, score=2.0, gloss_hint="a person who ...", sense_id=1, source_ref="frames:books:n_incorrigible")`.  `score`
is `n_frames`; the full frame record is the table row (`load_frames_table`).

**Frame statistics** ([frame_stats.json](../../data/candidates/corpus_frames/frame_stats.json), not there yet;
tracked, enveloped; per frame, from the table and, after the pilot, the registry; illustrative):

```json
{"frame": "d_very", "type": "degree", "tier": 1, "shards": [6650, 6651], "lines_scanned": 9800000, "hits": 41200,
 "fillers": 6100, "above_floor": 2900, "forms": {"adjective": 2710, "noun": 40, "phrase": 150},
 "registered_share": 0.71, "corpus_share": 0.12,
 "recovery": {"corpus_single": {"recall@500": 0.21, "recall@1000": 0.31, "recall@3000": 0.47}},
 "pilot": {"n": 25, "yield": 0.84, "region_tv": 0.18, "form_tv": 0.05, "physical_state_share": 0.09, "unique_kept": 3,
           "regions": {"social_interpersonal": 9, "emotional_temperament": 6, "...": 0}},
 "keep": true, "why": "yield 0.84 >= 0.4 and region_tv 0.18 <= 0.5"}
```

**Yield** is the share of a frame's pilot fillers M1 calls `trait` (registered fillers count with their recorded
verdicts).  **Net filter** is how far a frame's trait fillers lean away from the union: the total variation distance
(half the sum of absolute differences) between the frame's distribution over the seven regions and the union's
(`region_tv`), and likewise over the forms adjective / noun / phrase (`form_tv`).  **Unique contribution** is the
count of M3-kept rows only that frame found.  **A frame is kept** for the wave when its yield is at least 0.4 and
its `region_tv` at most 0.5, or when it has at least one unique kept row; the thresholds are a recommendation Roger
can change at the pilot gate, and a dropped frame's rows stay in the table (the wave selector reads `frames_kept`).

**Evaluation payload** ([evaluation.json](../../data/candidates/corpus_frames/evaluation.json), not there yet;
enveloped): `{"table_sha256", "bank_sha256", "ordering": "volumes" | "lift", "n_rows", "n_eligible", "n_net_new",
"recovery": {"union_volumes": {...}, "union_lift": {...}, "per_frame": {...}, "baseline_wordfreq": {...}},
"unfound_labels": {"n": 0, "by_region": {...}, "stems": [...]}, "frame_measures": {...}, "frames_kept": [...],
"registry_overlap": {"top_500": 0.0, "top_2000": 0.0}}`.

## 7. CLI

[corpus_frames_generator.py](../../data_analysis/gap_generation/corpus_frames_generator.py) (not there yet).  Common
flags `--tier 1|2|all`, `--data-dir`, `--registry`, `--candidates-dir`, `--external-dir`, `--dry-run`.  No command
makes a paid call; `submit` is the only one that touches the registry.

- `locate [--tier 1]`: head-peeks the shards (binary search per frame prefix, 4 KB range requests, about 13 a frame,
  about 1 MB in all) and HEAD-requests each shard's size; writes `shard_plan.json` and prints **the shard count and
  GB** of the tier.  $0; the only network use before Roger's go.
- `stream --approved-by '<Roger, date>' [--tier 1] [--parallel 4] [--resume]`: refuses without `--approved-by`
  (`NotApproved`, the IPIP rule); streams every planned shard once, applying all its frames' regexes line by line,
  writes `<frame_id>.tsv` extracts and the manifest (bytes streamed, lines kept, sha256, approval); a shard already
  extracted is skipped on `--resume`.  Wallclock: about 16 GB; the probe fetched 1 MB in seconds, so minutes to an
  hour depending on the proxy.  $0.
- `table`: builds `frames_table.jsonl` from the extracts (OEWN, wordfreq, the relabel, the registry tags);
  deterministic, rerun byte-identical, `.bak.<UTC>` on change; writes `frame_stats.json` (the free columns).  $0.
- `evaluate [--cutoffs ...] [--ordering auto|volumes|lift]`: the recovery curves per frame and for the union under
  both orderings beside the wordfreq baseline, the unfound corpus labels by region, the registry overlap at depth,
  `evaluation.json` and [recovery_curves.png](../../data/candidates/corpus_frames/recovery_curves.png) (not there
  yet; the plotting rule); after the pilot, `frame_measures` and `frames_kept`.  `--ordering auto` applies the
  pre-registered rule of § 1.  $0.
- `submit --run-id R (--top-per-frame 25 | --kept-target 300 [--kept-share X]) [--transport live|batches]
  [--budget-usd 8] [--confirm-expensive --confirmed-by WHO] [--dry-run]`: selects rows (the pilot: the top 25 of every
  frame by within-frame rank, deduplicated; the wave: the first `ceil(K / share)` net-new rows by union rank over the
  kept frames, registered rows riding along uncounted, the review-load guard at 1.5 x the target), prints strata
  (frame type x adjective/noun/phrase x registered/new, Zipf band), the **downstream estimate** at the measured
  census rates (rows the registry has already filtered counted out; the M1 pass rate 0.88 flagged unmeasured until
  the pilot), gates with `confirm_or_abort`, writes `candidates.jsonl` **before** `submit_candidates`, then
  `keys.txt`, `submit_report.json`, `run.json` (table and bank sha256, the ordering, the frames kept), `usage.json`
  (zero calls), and prints the follow-ups: `gap_registry.py submit --from ...` (main checkout), `traithood_filter.py
  --batch-id R_corpus_frames --run corpus_frames/R --pipeline split --transport T --budget-usd <1.5 x est + 2>`,
  `novelty_score.py score ...`, `recovery_test.py --generator corpus_frames --run-id R` (optional, paid, Roger's
  call), `report --run-id R`.
- `report --run-id R`: `report.md` (§ 10's readout from the registry blocks, `frame_stats.json`, `evaluation.json`
  and the M1/M3 batch directories' `usage.json` summed per model), `roger_sample.md` (50 kept rows, seeded) and
  `roger_first_hour.md` (the 150 most novel kept rows).  $0.

Dry runs print the shard plan, the estimate, the row counts and the strata, and write nothing.

## 8. Acceptance tests, written first

No test calls an API, the network or a real model: `books.py` takes a `fetch` callable (tests feed gzipped fixture
shards and scripted heads), OEWN is a fake `Lexicon` and a fake derivation map, `zipf_fn` is a dict, the registry is
a tmp path through the real frozen API.  The recovery and frame figures are **report-and-decide**; the cost caps,
`usage.json` presence, the untouched corpus, the no-tag-drops rule and the approval gate are hard.

- `frames`: unique ids; every frame has exactly one slot; every type has at least one tier-1 frame; the regex
  matches `very honest man\t1921,3,2` and `a born story-teller\t...`, and rejects `very_ADJ sergeant_NOUN`, `very leaky
  _ADV_`, `very Christian man`, `very the man`; `bank_sha256` changes when a frame changes.
- `books`: `locate` on scripted heads finds the right start and end shards (a prefix inside one shard; one spanning
  two; the end key stops before the `_TAG` forms, which sort after the untagged block); `shard_plan` lists each shard
  once with every frame it serves and sums GB from `Content-Length`; `stream_shard` over a gzipped fixture sums
  `match` and `volumes` over years >= 1920 only (a 1919 line adds nothing; `--year-min` moves it), keeps the noun per
  hit, and applies every frame's regex in one pass; `--resume` skips an extracted shard; **the approval gate**: no
  `--approved-by` raises `NotApproved` and fetches nothing (a watched fetcher); the manifest records bytes, lines,
  sha256 and the approval string.
- `table`: the frame floor (39 matches out, 40 in); `rank_volumes` and `rank_lift` on planted counts (a common word
  ranks high by volumes and low by lift); `rrf` fuses planted rankings (rank 1 in a small frame above rank 50 in a
  big one; **scale invariance**: doubling one frame's counts changes no order); `union_rank` ties by Zipf then
  surface; the relabel lands in `label` and the noun stays in `surface`; eligibility truth table through `zipf_info`
  (a monkeypatched floor moves the outcome; no local literal); **mutation test**: flipping every tag (`corpus_stem_match`,
  `queue_stem_match`, `registered`, `registered_decided`) drops no row and changes no `union_rank`; rerun byte-identical;
  `frame_stats` counts per frame.
- `relabel`: suffix rules through the fake lexicon (honesty → honest, generosity → generous, pugnacity → pugnacious);
  the derivation link (pedant → pedantic); `rule` `none` leaves the noun as the label; `is_person_noun` on a planted
  hyponym; a US fold records `us_spelling_from`.
- `evaluate`: recovery recall per frame and for the union on a fake corpus with planted labels, per class (single,
  hyphenated, multiword), under both orderings, beside a planted wordfreq baseline; `ordering_choice` picks the
  ordering with the higher union recall at 1,000 and ties to volumes; `unfound_labels` lists a planted label no frame
  finds, by region; `frame_measures` on a fixture registry: yield, `region_tv` and `form_tv` hand-computed, a planted
  `physical` tag counted, `unique_kept` counts a kept row found by one frame only; `keep_frame` truth table (low yield
  with a unique kept row is kept; low yield without one is not); `contributing_frames` names every frame of a row.
- `submit` (tmp registry, real API): `select_top` takes the top n of every frame deduplicated, registered rows along
  and uncounted; `select_wave` cuts net-new rows at `ceil(K / share)` by union rank over `frames_kept` only, a dropped
  frame's rows left out, registered-decided rows inside the cut submitted and counted toward neither the target nor
  the estimate, a registered-undecided row counted in both; the review-load guard refuses at 1.5 x; one candidate per
  stem with `score == n_frames`, `rank == union_rank`, `source_ref` in the documented form; `candidates.jsonl`
  written before the registry append; resubmit is a no-op; **cost guard**: 10,000 fake net-new rows -> estimate > $20
  -> refused without `--confirm-expensive --confirmed-by`; 2,000 rows -> over the default budget refused, accepted
  with a larger `--budget-usd`; dry run leaves the registry byte-identical and writes no run dir; follow-ups name the
  run id, batch id, `--pipeline split` and the transport; `corpus_frames` absent from `FAMILIARITY_GENERATORS` and
  `CURATED_GENERATORS` (guards with the trap in the comment).
- CLI: every subcommand's `--dry-run` exits 0 and writes nothing; `stream` without `--approved-by` exits non-zero
  before any request; `report` renders a fixture run with the three files.
- **Acceptance on recorded outputs** (`test_gapgen_corpus_frames_acceptance.py`, skips while absent): the manifest
  names the approval and its bytes streamed agree with the shard plan within 1%; `evaluation.json` carries both
  orderings' union recall beside the wordfreq baseline (the frames must beat it at 1,000 to earn their keep,
  report-and-decide), the per-frame recovery, the unfound labels by region and, after the pilot, every frame's
  yield, `region_tv`, `form_tv`, `physical_state_share` and `unique_kept`; `frame_stats.json` has a row for every
  frame of the streamed tier; `usage.json` beside every run with generator cost 0.0; the table's sha256 in
  `evaluation.json` equals the file's; the pilot's and the wave's `report.md` carry the already-registered headline,
  the net-new kept share and the contributing frame of every kept row; the package imports neither `anthropic` nor
  `openai`; `git status --porcelain data/traits data/roles data/seed_queue.json` is empty.
- **Manual check, listed as such**: the 50-row `roger_sample.md` judged trait / not-trait / duplicate by Roger, and
  the pilot's precision spot check of the workstream plan (§ 6: 100 random survivors of the top 2,000, 50 from the
  degree frames against 50 from the nominal frames, for source-specific junk) folded into it; recorded in the
  acceptance report, not asserted by a test.

Commands that must pass at the end of every task:

```
uv run pytest assistant_axis/tests/test_gapgen_corpus_frames_*.py data_analysis/tests/test_gap_generation_corpus_frames_cli.py -q
uv run pytest -q                                                  # whole suite, unchanged
uv run python data_analysis/check_arrangements.py --quiet
uv run python tools/sync_entity_lists.py --check
git status --porcelain data/traits data/roles data/seed_queue.json   # must be empty
```

## 9. Ordered task checklist

Prerequisite: a worktree off `anthropic-vllm-uv` (`git merge --ff-only anthropic-vllm-uv` first), `.env` copied,
`data/external/` symlinked from the main checkout (OEWN is there).  The boundary paragraph of § 3 goes into every
task prompt verbatim.  Each task ends with the § 8 commands.

1. Skeleton, `frames.py` (the bank of § 6 with tiers), `books.py` with the fake fetcher; CLI `locate --dry-run`.
   Test: frames, books.
2. **`locate --tier 1` for real** (about 1 MB of range requests and HEAD requests; inside the boundary's "small
   checks"): `shard_plan.json` with the shard count and GB.  Paste the figure into the task report and **stop**: open
   decision 1 and the stream approval are Roger's on that figure (the download-over-2-GB rule).
3. `relabel.py`, `table.py`; CLI `table` on fixture extracts.  Test: relabel, table.
4. **`stream --approved-by '<Roger, date>' --tier 1`** on his go (about 16 GB; `--parallel 4`; `--resume` after any
   break); then `table`.  Report: lines scanned and kept per shard, distinct fillers per frame, the forms, the
   registered and corpus shares per frame (free).
5. `evaluate.py`, CLI `evaluate`; the recovery curves per frame and union under both orderings against the wordfreq
   baseline, the unfound corpus labels by region, the ordering choice, the PNG (visually verified, the plotting rule).
   Test: evaluate.  Paste the union curves and the per-frame recall at 1,000 into the task report.
6. `submit.py`, `report.py`; CLI `submit`, `report`.  Test: submit, CLI.
7. **Pilot** (§ 10): `submit --run-id <date>-pilot --top-per-frame 25` (about 600-800 distinct rows, of which about
   a quarter to a third net-new; about $3-5 live, cap $8), M1 + M3 run by Fable, `evaluate` (now with
   `frame_measures` and `frames_kept`), `report`: the per-frame readout and the re-based wave projection.  **Roger
   decides** on it (§ 10).
8. Glossary entries ([glossary.md](./glossary.md): frame and filler, shard and head-peeking, document frequency,
   lift, reciprocal-rank fusion, yield, net filter, unique contribution; net-new row if plan 09 has not added it);
   the [data/README.md](../../data/README.md) paragraph for `candidates/corpus_frames/` and `external/books_ngrams/`
   proposed in the report (not edited; the platform owns that file).
9. **First wave**: `submit --run-id <date>-w1 --kept-target 300 --kept-share <the pilot's net-new kept share>`,
   transport by the re-based estimate (live under $20, batched with Roger's go above), M1 + M3, `report` (the novel
   figure raw and net, the contributing frame of every new label, `roger_first_hour.md`), the 50-row sample to
   Roger.  Acceptance test on the recorded outputs.
10. Acceptance report (§ 11); tier 2 and the text corpora (open decisions 1 and 2) restated there as the next steps
    with what the pilot said about them.

## 10. Pilot

**Pilot** (task 7; the per-frame top 25 by within-frame rank, deduplicated across frames, registered rows riding
along).  Why this shape: a frame's yield and net filter are measured on *its* fillers, so the sample is stratified
by frame, and a registered filler's recorded verdict counts for every frame it came from at no cost, which is why
the pilot charges only the net-new rows (projected about 200-250 of 600-800 at the proxy's share, § "Cost") and still
measures every frame on 25.  Readout, in this order:

1. **The already-registered headline**: the share of the pilot's rows already in the registry, and how many of those
   M1 and M3 had decided (the proxy expects 65-80% at the top of the frames, § "Baseline").
2. **Per frame** (the table of § 6): yield, `region_tv`, `form_tv`, `physical_state_share`, the region histogram,
   the forms, `unique_kept`, and the keep verdict with its reason; the frames sorted by yield within type, so that a
   type whose every frame filters strongly shows at a glance.
3. **Per type**: the union of its frames against the union of all frames (the same distances), the labels only that
   type found.
4. The **M1 trait share of the net-new rows**, the **net-new kept share** (kept rows per submitted row the registry
   had not yet filtered; it replaces the 0.3 proxy in `select_wave`), the novel share after M3 (`new` or `grey`)
   **raw and net** of other generators' pending `new` candidates of the same stem (plan 09 § 10), the nominal rows
   M1 held on the roles list (open decision 3), the relabel rules' counts, the parse rate of M1's batch.
5. The cost from the M1 and M3 batch directories' `usage.json` and `useful_per_dollar` (kept rows per dollar), and
   the **re-based projections**: for the whole table over the kept frames, and for a 300-kept wave, the rows to
   submit, the net-new rows, the kept rows, the review hours at the measured rate.

**Roger decides**: (a) the frame thresholds (0.4 yield, 0.5 `region_tv`) and any frame to keep or drop by hand;
(b) the wave's transport by the re-based estimate (its size is decided: 300 net-new kept rows); (c) open decision 3b
if the unrelabelled count is large; (d) whether tier 2 is worth streaming (a type under-represented in the kept
rows) and whether the text corpora come next (open decisions 1 and 2).

## 11. Report at the end

One page at [acceptance_05_corpus_frames.md](./acceptance_05_corpus_frames.md) (not there yet): what was built
against § 5; deviations with reasons; the § 8 commands verbatim with pass counts; the shard plan as approved
(shards, GB, bytes streamed, lines kept, the manifest's approval line); the union recovery curves under both
orderings beside the wordfreq baseline and the ordering chosen; the per-frame recovery; the corpus labels no frame
finds, by region (expected: concept phrases, alignment traits, memberships; plan 05 § 4); the pilot readout in
the § 10 order with Roger's decisions; the first wave's counts (submitted, net-new, already registered and decided),
M1/M3 fractions, the novel figure raw and net, the contributing frame of every new label (and the labels only one
frame found), the 50-row sample's verdicts and the first-hour list; cost per model from every `usage.json` (the
generator's zero, M1, M3); the registry overlap at depth 500 / 2,000 / 5,000 against the proxy's 80 / 63 / 41%; open
QUESTIONS entries; the proposed `data/README.md` paragraph; and the next steps (tier 2, the text corpora) with what
the pilot said.

## 12. Escalation

Opus retries a failing step once with a changed approach, then Fable (diff review, architecture, stubborn failures),
then Roger through [QUESTIONS.md](./QUESTIONS.md) in its format (`N. [05] question. Assumption proceeded under: ...
Status: open`, numbering continuing from the file's last entry, 90 on 2026-10-13), proceeding under the assumption
unless the answer would make the work useless.  Pre-registered entries Opus copies in at the start: (1) tier 1 is the
first build and the stream needs Roger's go on `locate`'s figure (open decision 1); (2) the text corpora and spaCy
are out of this plan (open decision 2); (3) nominal fillers with no deterministic adjective are submitted as nouns
(open decision 3); (4) the background frequency is `wordfreq`'s Zipf, the 1-grams are not fetched; (5) the within-frame
ordering is chosen by the free recovery check, volumes on a tie; (6) frames merge by reciprocal-rank fusion at k =
60 and `score` is `n_frames`, not a familiarity; (7) corpus, queue and registered matches are submitted, with
filtered rows counted out of the estimate and the target; (8) the wave is sized on net-new kept rows at the pilot's
measured share, at 146 terms an hour until `pooled_review_rate` exists (interface request on plan 13); (9) the frame
floor is 40 matches over years >= 1920; (10) filler-first frames are absent from the Books bank by construction;
(11) the frames table is git-ignored with its sha256 recorded; (12) the frame keep rule's thresholds (0.4, 0.5) are
recommendations for Roger at the pilot gate.  Anything that would edit a trait file, the queue or an `arrangement`,
spend over a command's budget, stream or download without Roger's recorded go, add a dependency or a model, or change
a frozen signature stops and asks.

## Baseline measured for this plan (read-only, 2026-10-13)

Measured with throwaway scripts in the session scratchpad; the generator's first `evaluate` and `report` reproduce
the registry figures.

- **Corpus and registry**: 932 trait files, 710 single-word and 222 multiword labels (154 hyphen-only); the seed
  queue 1,050 entries, 972 traits; the registry snapshot
  ([registry.snapshot.jsonl.gz](../../data/candidates/registry.snapshot.jsonl.gz)) 9,941 stems, 9,893 decided by
  M1 and M3, sources by generator: censuses 8,675, base_model 2,007, ipip 752, wn_clusters 733, states_pass 727,
  roget 674, antonym_check 487, alignment_sweep 479, m1_validation 150, manual 5.  **464 of the 710 single-word
  corpus labels (65%) are registry stems** (the coordinator's 74% is the same 464 over the 628 labels without a
  standard's suffix); 41 of the 222 multiword labels (18%).
- **The proxy for frame fillers**: the masked-LM table ([mlm_table.jsonl](../../data/candidates/masked_lm/mlm_table.jsonl),
  9,050 rows, pilot A of 2026-10-13), whose frames are the same sentence frames read by a model instead of counted in
  a corpus.  Of its eligible single words in union-rank order: **top 500, 80% already registry stems** (397 decided;
  321 M1 trait, 136 M3 kept), top 1,000 76%, **top 2,000 63%** (1,264 decided; 953 trait, 466 kept), top 5,000 41%
  (2,030 decided; 1,380 trait, 755 kept); corpus stems 23%, 20%, 13%, 6%.  By best frame in the top 2,000: the
  attributive "a very X person" frame **96% registered** and 88% M1 trait among those, "X by nature" 52% and 65%,
  "habitually X" 55% and 55% (states), "why are they always so X" 90% and 46% (states), "an avowed X" **15%
  registered** and 96% trait (memberships and identities).  Reading: the degree and copular frames of this plan will
  mostly re-find what the censuses submitted; the nominal and possessive frames are where the net-new rows are; a
  frame's net filter is already visible in the proxy, as Roger's item 6 expects.
- **Proxy funnel for sizing** (from the figures above, re-based at the pilot): net-new share at the top of the frames
  about 0.25-0.35; M1 trait share of registered frame fillers 0.65-0.88; M3 kept share of M1-passed about 0.42-0.49;
  so a **net-new kept share of about 0.3** per net-new row, and about 1,000 net-new rows (some 3,000-4,000 table rows
  by union rank) for a 300-kept wave.
- **The Books layout** (range requests to `storage.googleapis.com/books/ngrams/books/20200217/eng/`, 0.99 MB in all:
  about 0.66 MB of 4 KB head-peeks and two 160 KB samples; five HEAD requests): the files are sorted by the n-gram
  string in byte order, so an untagged block (`very ` ...) precedes its tagged forms (`very_ADJ ...`) and the end key
  `prefix + "\x7f"` closes it; POS wildcards appear as tokens (`very leaky _ADV_`).  Spans: 3-gram `very ` shards
  06650-06651 (2; the workstream's 06650-06652 included the tagged block), `too ` 06504-06505 (2), `an incorrigible `
  03205 (1), `man of ` 04955 (1), `reputation for ` 05770 (1); 4-gram `known for his ` 04790 (1), `was a `
  06478-06479 (2), `tendency to be ` 05984 (1).  Sizes: 3-gram shards 0.549-0.560 GB, 4-gram 0.467-0.544 GB,
  1-gram 0.265 GB.  A 160 KB prefix of a 3-gram shard holds about 1,000 lines, so a shard is on the order of ten
  million lines, and the sample reached only eight "very X <noun>" fillers (five of them registry stems: sane,
  complete, noteworthy, farseeing, lewd; the archaic "agreable" and "infirm" not): too few to measure overlap, which
  is why the masked-LM proxy above sizes the plan.
- **The text corpora** (HF dataset cards, 21 KB): PIPPA 799 MB in three files (`pippa_deduped.jsonl` 257 MB
  suffices), Apache-2.0, not gated, tagged not-for-all-audiences; hieunguyenminh/roleplay 2.2 MB, CC BY 4.0;
  Nemotron-Personas-USA 2.69 GB, CC BY 4.0 (out, synthetic); PersonaHub 301 GB, CC BY-NC-SA 4.0 (out).
- **Nominal relabels** on the repository's OEWN: the `derivation` link gives an adjective for 11 of 30 nominal traits
  tried (pedant, sycophant, gossip, coward, miser, snob, cynic, tyrant, scoundrel, recluse, and bully / spendthrift /
  braggart have an adjective sense of their own); none for hypocrite, busybody, yes-man, know-it-all, liar, optimist,
  martyr, flatterer, workaholic, idealist, bigot, prude, bore, daydreamer, procrastinator, perfectionist, zealot.

## Inconsistencies between the workstream plan and the repository, and how each is resolved

| workstream plan | repository now | resolution |
|---|---|---|
| "387 existing labels" (§ 6), stage-1 and stage-2 filters, a "novelty scorer" to be built (§ 7) | 932 trait files; M1 and M3 built; the registry API frozen | counts of § 1; M1 replaces both stages; M3 as built (relation call: synonym / antonym / related / unrelated; `pair_completion_for`) |
| shards "~390 MB", "15-25 shards, 6-10 GB", "very" in 06650-06652 | *measured* 0.47-0.56 GB; two shards for `very` (the third was the tagged block) | open decision 1; `locate` prints the real figure |
| background frequency from the 1-grams | the platform has `wordfreq` Zipf (`zipf_info`) and records it on every row | 1-grams not fetched (§ 1) |
| year cutoff "≥ 1900 (open)" | Roger: about 1920 | 1920 (§ 1) |
| "Registry row: label, gloss, type, per-source counts and ranks, frames matched, one example sentence, polysemy flag" | `Candidate` has `surface, rank, score, gloss_hint, sense_id, source_ref, partner_hint`; n-grams carry no sentences | the frame record is the table row (`load_frames_table`); `source_ref` names the frame; no example sentence from Books (the text corpora would give one); polysemy is M1's `sense` block |
| Haiku relabels nominal traits (sycophant → sycophantic) | no generator-side LLM call | OEWN derivation and `normalize_form` (open decision 3) |
| Nemotron "on-distribution"; spaCy and `datasets` "pip-installable" | Roger: synthetic personas are other generators'; no new dependency | out of this plan (open decision 2) |
| "Merge sources by rank, keep per-source counts" | Roger's item 6: merge **frames** by within-frame rank | reciprocal-rank fusion over frames (§ 6) |
| "Known negatives: a fixed list of physical/demographic adjectives must not survive stage 1" | M1 tags `physical` and `state`; memberships are traits (decisions_m1 decision 3) | `physical_state_share` per frame from the recorded verdicts (§ 6); no fixed list |
| "Roger: 1-2 h reviewing the top few hundred novel survivors" | plan 09's review-hour wave on net-new kept rows; plan 13 measures 146 terms an hour | `--kept-target 300` at the measured share (§ 1) |
| frames "X to a fault", "X by nature", "X at heart" (§ 3.2 and item 6) | unlocatable in a prefix-sorted n-gram set | not in the Books bank; plan 04's bank and the text corpora (§ 6) |
| "Keep hyphenated compounds" | the filler regex keeps them; `normalize_candidate` splits them for the Zipf floor by the rarest part | kept, tested (§ 8) |
| the plan's stop-list "age, nationality, appearance, wealth, health" | memberships are traits; the physical pass and holding lists are the platform's | no generator-side stop-list; M1 decides |

## Cost (estimates; re-measured at the pilot)

| step | what | estimate |
|---|---|---|
| `locate` (head-peeks and HEAD requests) | about 1 MB over the network | $0 |
| `stream`, tier 1 | about 30 shards, **about 16 GB** streamed from a public bucket, nothing stored but the extracts (tens of MB); Roger's go on `locate`'s figure | $0; minutes to an hour |
| `table`, `evaluate`, `report` | local; OEWN and wordfreq | $0 |
| pilot: top 25 per frame, about 600-800 rows, about 200-250 net-new at the proxy's share | M1 $0.0072 a word + M3 $0.011 a passed word at 0.88 | **about $3-5 live** (cap $8); an upper bound, the gate charges only rows the registry has not yet filtered |
| first wave: 300 net-new kept rows at a share of about 0.3, about 1,000 net-new rows (plus registered rows riding free) | the same rates; batches x 0.5 | **about $14 live / $7 batched**, re-based at the pilot; over $20 only if the measured share is well under 0.2, then batched with Roger's go |
| tier 2 (open decision 1), if wanted | about 20 shards, about 11 GB more | $0 |
| text corpora (open decision 2), if wanted later | about 260 MB downloaded into `data/external/corpus_frames/` | $0; a separate approval |

Roger's time: 10 minutes on `locate`'s figure; 30 minutes on the pilot readout and the frame thresholds; about two
hours of review on the wave (by construction); 15 minutes on the 50-row sample.

**Delete-when-done line for Roger (his rule of 2026-10-10)**: the tier-1 stream is a download over 2 GB with nothing
to delete afterwards (the shards are discarded as they are read; the extracts under
`data/external/books_ngrams/` are tens of MB and are the generator's record); tier 2 the same; the text corpora
(open decision 2) would keep 260 MB under `data/external/corpus_frames/`, deletable after the second build's table
is written.

## Frozen interface (for plan 11's ensemble and any generator wanting a person-usage frequency)

`from assistant_axis.gapgen.generators.corpus_frames import load_frames_table, TABLE_PATH, person_frequency`:
the § 6 table row (`schema_version` 1) with `frames` (per-frame match, volumes and both ranks), `n_frames`,
`union_rank`, `rrf`, `zipf`, `form`, `relabel_rule` and the membership tags for every filler above the frame floor;
`person_frequency(word) -> PersonFreq(volumes_total, frames: dict[str, int], n_frames)` is the workstream's "how often
is W used of a person in Books" lookup, read from the table (`None` when no frame found the word), the rarity filter
any other generator can apply to its own output.  Fields are added, never renamed, without a schema bump.  In the
registry, a corpus-frames candidate's frame is readable from its `source_ref` (`frames:books:<frame_id>`), and the
full frame list from the table.
