# Data Analysis

Scripts for generating, classifying, and inspecting the role/trait data in
[`data/`](../data/). Everything in this directory is new — Christina Lu's
published repository did not include her data generation tooling.

## Scripts

### `regenerate_trait_instructions.py`

Generates pos/neg instruction pairs, questions, and eval prompts for traits
via the Anthropic API. Recreates the functionality described in Christina Lu's
paper (Appendixes B). With the appropriate flags (`--style Christina`,
temperature 1.0, no thinking), it uses her original prompts and parameters
and reproduces her results closely. The default `--style Roger` is a fork
with improved neg instructions (more example pairs for different trait types,
optional antonym injection).

```bash
uv run python data_analysis/regenerate_trait_instructions.py --traits stoic --force
uv run python data_analysis/regenerate_trait_instructions.py --all --dry-run
uv run python data_analysis/regenerate_trait_instructions.py --traits stoic --style Christina --force
```

Token usage (Sep 2026): every non-dry run logs a `[usage]` line and merges
its cost into the cumulative `data/traits/regeneration_usage.json`
(`--usage-json PATH` to redirect); the role script and `generate_antonyms.py`
do the same with `data/roles/regeneration_usage.json` and
`data/traits/antonym_check_usage.json`.  Roughly $0.02-0.03 per entity on
Sonnet 4.6.  Note that `--roles`/`--traits` take separate arguments: in zsh,
`$(cat list.txt)` is passed as one word, so use `$(cat list.txt | tr ' ' '\n')`
or spell the names out.

### `regenerate_role_instructions.py`

Generates instruction variants and questions for roles. Same relationship to
Christina's paper (Appendix A) as the trait script — a recreation of her missing tooling,
with flags to reproduce her original parameters.

```bash
uv run python data_analysis/regenerate_role_instructions.py --roles pirate oracle --force
uv run python data_analysis/regenerate_role_instructions.py --all --dry-run
uv run python data_analysis/regenerate_role_instructions.py --roles pirate --style RogerV2 --force --show-prompt
```

Prompt styles (Sep 2026): `--style RogerV2` (default since 2026-09-12)
adds the voice and anti-softening rules from the September 2026 voice
audit (second-person, the role's own vocabulary and particulars, a 15-25
word target, no case-worker or writer's register, no whitewashing of bad
roles, an inside view for non-verbal roles, particulars that vary across
the five instructions, scenario questions) with examples that obey them;
`--style Roger` is the May 2026 production template, identical to
Christina's for roles, kept for rollback and comparison.  Roger adopted V2
for roles on 2026-09-12 after the pilot in `reports/rubric_v2_pilot/`
(every role file except `default.json` carries it since the corpus-wide
regeneration later that day; subject to rollback once embeddings have
been extracted, for which the V1-rubric files are kept there and at commit
`93a8554`, the last before the corpus check-in of 2026-09-28).  The trait
script has no V2 yet.  Every
regenerated role or trait file now carries a `generator` field (script,
style, a short hash of the template text, model, temperature, thinking
budget, date) so the two instruction populations stay distinguishable;
the hash changes whenever the template text is edited.

### `generate_antonyms.py`

Determines the `negative_label` for traits by feeding their pos/neg
instructions to Claude and asking it to name the opposite pole. Outputs
antonym scores (0-4) and reasoning. Supports `--traits` to scope to specific
traits. Primarily used for creating/checking `negative_label` values. Particulalry useful for creating/confirming "clean pairs" of antonyms were B is the correct `negative_label` for A and vice versa, so comfirming theit context and scope match well: start with `negative_label = "non-{positive_lable}"`, confirm you get the expected atonyms bidirectionally, then update the `negative_label` values to the antonyms.

```bash
uv run python data_analysis/generate_antonyms.py
uv run python data_analysis/generate_antonyms.py --traits obedient rebellious
```

### `seed_entities.py`

Drives the corpus-expansion queue `data/seed_queue.json` (one entry per
candidate trait or role from `TRAITS_TO_ADD.md` / `ROLES_TO_ADD.md`, with a
status lifecycle `candidate -> ready -> seeded -> generated -> checked ->
paired | done`).  `write` turns entries whose description is final into seed
JSONs (traits with `negative_label = non-<label>`, roles with a singleton
`arrangement`), `generate` runs the two regenerate scripts on them (with a
cost estimate and a refusal over $20 without `--confirm-expensive`), `check`
runs `generate_antonyms.py` and classifies each answer against existing and
queued stems (nice / mismatch / nearly_nice / nasty / open, the decision
table in `AGENT_NOTES.md` § "Corpus expansion policy"), `rename` applies the RO action
(rename the existing trait to the check's word if free, regenerate, re-check
both sides), `pair` records a
confirmed clean pair on both files and regenerates the new side's neg
clause, and `status` / `report` summarise.  Every subcommand takes
`--dry-run`.  The description-writing rules the seeds must follow are in
`AGENT_NOTES.md` § "Description-writing rules for new seeds".

```bash
uv run python data_analysis/seed_entities.py status --chunk 1 --list
uv run python data_analysis/seed_entities.py write --chunk 1 --sub-chunk "Tier D" --dry-run
uv run python data_analysis/seed_entities.py generate --stems rationalizing intellectually_honest
uv run python data_analysis/seed_entities.py check --stems rationalizing
uv run python data_analysis/seed_entities.py pair --a rationalizing --b intellectually_honest
```

### `classify_goals.py`

Classifies each role/trait instruction by whether it implies alignment-relevant
goals (score 0-2). Results are aggregated per role/trait and saved to
`output/`. Supports `--names`, `--roles-only`, `--traits-only`, and `--force`. Note that this use Opus, so costs > $100 to run.

```bash
uv run python data_analysis/classify_goals.py --dry-run
uv run python data_analysis/classify_goals.py --names obedient compassionate --traits-only --force
uv run python data_analysis/classify_goals.py  # full corpus
```

### `score_combinations.py`

Scores all role+trait instruction combinations for incongruity using Claude
Sonnet. For each combination, sends all index-matched pos instruction pairs
in a single API call and gets a 0-3 score per pair with reasoning. Output
goes to `data/combination_scores.json`.

Parameters mirror Step 1's `--goal_count` and `--non_goal_count` (defaulting
to 40 each). Supports `--dry_run`, `--batch_size` (instruction pairs per
call, default all), and resume via incremental saves.

```bash
uv run python data_analysis/score_combinations.py --dry_run
uv run python data_analysis/score_combinations.py --goal_count 2 --non_goal_count 2  # test
uv run python data_analysis/score_combinations.py  # full 40x40 + 40x40 = 3200 combos
```

### `sample_trait_responses.py`

Diagnostic tool for eyeballing how a model responds to trait instructions.
Sends pos and neg system prompts with sampled questions, prints responses
side by side.

```bash
uv run python data_analysis/sample_trait_responses.py stoic
uv run python data_analysis/sample_trait_responses.py stoic --n-questions 3 --pairs 0 2 4
```

## Generator model

All five API scripts here default to `claude-sonnet-4-6` (switched 2026-09-07
when `claude-sonnet-4-20250514` was retired and started returning 404).  The
corpus is therefore mixed: any trait whose instructions were regenerated on
or after 2026-09-07 (tracked in `data/traits/instructions/TRAITS_TO_ADD.md`
§ "Housekeeping" and `AGENT_NOTES.md` § "TODO: regenerate activation/vector
data") comes from Sonnet 4.6; everything else still comes from Sonnet 4.  A same-prompt
comparison on three control traits showed Sonnet 4.6 rewrites every
instruction and question (no exact matches), with longer, more prescriptive
"always/never" phrasing.  `classify_goals.py` and the `score_combinations.py`
rescore model use `claude-opus-4-6`, which still resolves.

Known stale tests (tracked in `AGENT_NOTES.md` § "TODO: code housekeeping
(Sep 2026)"): three tests in
`results_analysis/tests/test_infer_axis_description.py` expect the streaming
helper to return a bare string where it now returns `(text, usage)`; they
fail at git HEAD independent of the model change.  (The fourth,
`test_regenerate_role_instructions.py::TestBuildEvalPrompt::test_uses_0_to_3_scale`,
was updated 2026-09-11 to assert the reason-first eval-prompt ending.)

## Arrangement tools (Sep 2026)

The `arrangement` field on every role and trait JSON records which set of
same-type entities the file belongs to and its shape (`pair`, `triangle`,
`square`, `N-orthoplex`, `sequence`, ...); rules in `AGENT_NOTES.md`
§ "The `arrangement` field", implementation in
`assistant_axis/arrangements.py`.

- `check_arrangements.py` -- validates the whole corpus (kind vocabulary,
  member counts, reciprocity between members, agreement with
  `negative_label` pairs, tree links).  Exit 1 on any inconsistency;
  `--list-unclassified` prints the files with no field.  Run it after any
  edit to labels or arrangements; the test suite also runs it against the
  checked-in corpus.
- `backfill_arrangements.py` -- the one-off that wrote the initial values
  (clean pairs, the two triangles, the moral-circle sequence, singletons
  for untouched `non-X` placeholders, role pairs from
  `pair_list_clean.json`).  Dry run by default, `--apply` to write,
  `--overwrite` to replace existing fields.  Kept for re-runs after bulk
  additions.

## Trait-gap platform: the split trait-hood filter (Sep 2026)

`gap_generation/traithood_filter.py` decides whether a candidate word can name a
persona trait.  Since 2026-09-29 its default is the **split** filter
(`--pipeline split`; spec: `reports/trait_gap_generation/coding_plan_split.md`):
a row of small calls, **one item per call**, each prompt read byte for byte from
Roger's rubric files in `reports/trait_gap_generation/rubrics/`.  The old
single-call classifier stays behind `--pipeline single`, so recorded runs can be
reproduced (`--batch-size` applies to it only and is refused with split).

- **Waves.**  Definition probe (probe band only) -> sense (the label alone) ->
  established, vague and kind for each primary reading -> same-sense check and,
  for a row with an intended sense, the comparison -> gloss (words that go on as
  traits) -> alignment and descriptors on the gloss.  Steps 1 to 3 never see the
  intended sense.  The join is code (`assistant_axis/gapgen/split.py`), and a
  note never rejects a word.
- **Models.**  Every step on `claude-haiku-4-5-20251001` at temperature 0.  The
  second opinion (a seeded 10% plus every word noted `obvious_sense_not_trait` or
  `most_likely_reading_stretched`) and the comparison run on `claude-sonnet-5-5`,
  which refuses `temperature`: requests to it carry no temperature, thinking or
  effort setting, and `max_tokens` 2000.  A word chosen for a second opinion gets
  its gloss from Sonnet 5.5.
- **Alignment is a score.**  Since alignment.md draft 3 (2026-09-30) the
  alignment call answers 0 to 3, recorded in the filter block as
  `alignment`.  `alignment_relevant` is kept for its existing readers (corpus
  regions, review order) but is **derived**: true for 2 or 3, false for 0 or
  1.  Later work, such as the duplicate-or-gap decision, should read the
  score.  Both keys are null on rows that did not go on as traits.
  `summary.json` `v2_fields.alignment_scores` counts each score beside
  `alignment_relevant_true`.
- **Refused plain readings.**  When the plain reading of a label (the
  comparison's input, `plain_reading.py`) is a refusal, the row is recorded
  with stage `refused`: no comparison, no note.  The rule
  (`plain_reading.is_refusal`): the sentence opens with a first-person
  refusal ("I can't", "I won't", "I'm unable", "Sorry", ...) and names the
  request or its output ("content", "create", "describe", "role-play", "this
  request", ...), or the API stopped with `stop_reason` "refusal".
- **Pins.**  `rubrics/versions.json` pins every prompt text by SHA-256.  A paid
  run refuses to start when a text on disk is not its latest pin; pin an edit
  with `uv run python data_analysis/gap_generation/rubric_pins.py bump NAME --why
  "..."` (and `... rubric_pins.py check` to see the state).  The rubrics
  directory is a platform path, so an uncommitted edit also stops a paid run.
- **Transport.**  `--transport auto` (default) sends fewer than 300 words live
  and more through the Message Batches API, at half price (charged under
  `<model>@batch` in `usage.json`).  Batch ids and wave state are kept in
  `filter/<batch>/batches.json`.  The waves depend on each other, so a batch
  run takes several hours of wall time (the 99-word pilot: 7 batches, 2 h 11 min,
  each batch 7 to 34 minutes whatever its size).  A wave larger than 50,000
  requests or 128 MB of serialized requests (half the service's limits:
  `batches.MAX_BATCH_REQUESTS`, `MAX_BATCH_BYTES`) is split into several
  batches, submitted together and then polled; the cap is checked on the whole
  wave before the first of them goes.  A poll or a results stream that breaks
  off on a network error (the full validation run hit
  `httpx.RemoteProtocolError` mid-stream on 2026-09-30) is tried again with the
  live calls' back-off (5, 20, 60, 180 s); results already handed over are not
  handed over again.  Only when the retries are spent does the run end, with
  the batch still "submitted" and everything received recorded, so `--resume`
  collects the rest.  Every log line carries its UTC time
  (`runs.configure_logging`), each poll line says how long the batch has waited
  since submission, and a batch found ended more than ten minutes after it
  ended gets a warning line (a laptop that slept shows up there).
- **Resume.**  `--resume` reuses an existing batch directory: no call whose
  answer is already in its `responses.jsonl` is sent again (same step, prompt
  hash, model and input), a batch submitted but never collected is collected
  rather than resubmitted, and `usage.json` carries on so the cap covers the
  batch id's whole spend.
- **Cost.**  About $0.010 a word live with the second opinion, half that in
  batches; the estimate is printed by step before every run.  A full run
  crosses the $20 confirmation line at about 2,000 words live or 4,000 in
  batches.

```bash
# the pilot on the 99 test words (never a row of m1_validation.jsonl)
uv run python data_analysis/gap_generation/traithood_filter.py --pipeline split \
    --transport live --validation-file data/candidates/validation/split_test_words.jsonl \
    --batch-id split_pilot_live --budget-usd 3 [--dry-run]
```

Outputs in `data/candidates/filter/<batch_id>/`: `responses.jsonl` (every
response, appended as it arrives), `results.jsonl`, `summary.json` (with a
`split` block: parse rate by step and model, cost by step, the pilot figures),
`usage.json`, `run.json` and, for batches, `batches.json`.  Pilot results:
`reports/trait_gap_generation/acceptance_split.md`.

## Output

```
output/
├── goal_classifications.json       # Aggregated per-(name, source, polarity)
├── goal_classifications_raw.json   # Per-instruction classifications (Opus)
├── goal_classifications_sonnet.json     # Aggregated (earlier Sonnet run)
└── goal_classifications_raw_sonnet.json # Per-instruction (earlier Sonnet run)
```

The `_sonnet` files are from an earlier classification run using Sonnet: it's not up to this task.
The primary files (without suffix) use Opus.

## Tests

```bash
uv run pytest data_analysis/tests/
```

Unit tests for the instruction regeneration scripts (prompt construction,
JSON parsing/repair, argument validation).
