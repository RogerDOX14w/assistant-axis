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
and reproduces her results closely.  The default is `--style RogerV2`, the
rubric of September 2026 (adopted 2026-10-01 after the development and
held-out checks described below); `--style Roger` is the May 2026 production
rubric, a fork of Christina's with improved neg instructions (more example
pairs for different trait types, the antonym named), kept for comparison and
rollback while the corpus is regenerated.  `--no-antonym` leaves the partner
unnamed in the negative instructions, which gives the clean-pair check an
unbiased answer without editing the file's label (regenerate with the default
afterwards).

```bash
uv run python data_analysis/regenerate_trait_instructions.py --traits stoic --force
uv run python data_analysis/regenerate_trait_instructions.py --all --dry-run
uv run python data_analysis/regenerate_trait_instructions.py --traits stoic --style Christina --force
```

Batch mode (Sep 2026): `--batch` submits the run as one Anthropic Message
Batch, at half the price; results usually come within the hour and at most a
day later.  Real time is the default, since on a small run the turnaround
matters more; for a run over about $20 the choice is made case by case
(AGENT_NOTES, "Batch or real time").  The script waits for the batch, writes
the files, and generates in real time whatever the batch failed to deliver.
`--batch-no-wait` submits and exits, and `--batch-id ID` (with the same
options) collects later; submitted batches are listed in
`regeneration_batches.json` beside the usage record.  Combined styles only.

```bash
uv run python data_analysis/regenerate_trait_instructions.py --all --style RogerV2 --force --batch --dry-run
```

Token usage (Sep 2026): every non-dry run logs a `[usage]` line and merges
its cost into the cumulative `data/traits/regeneration_usage.json`
(`--usage-json PATH` to redirect); the role script and `generate_antonyms.py`
do the same with `data/roles/regeneration_usage.json` and
`data/traits/antonym_check_usage.json`.  Roughly $0.02-0.03 per entity on
Sonnet 4.6.  Note that `--roles`/`--traits` take separate arguments: in zsh,
`$(cat list.txt)` is passed as one word, so use `$(cat list.txt | tr ' ' '\n')`
or spell the names out.

**Trait rubric V2 (`--style RogerV2`, the default; drafted 2026-09-29, adopted
2026-10-01 as template `9255dd3430ef`).**  It keeps what the role rubric V2.5 has against softening
and for question design, leaves its voice rules out, and adds rules the
8slot responses called for: every instruction opens by telling the model who
to be, from a menu of five ("Be someone who ...", "Become someone who ...",
"From now on, you are someone who ...", "You are someone who ...", "You are
..." followed by what the person is), never by telling it to play a part and
never with a statement of habits or beliefs, which leaves the model answering
as an ordinary assistant; the trait is the person's own and a standing one;
the negative pole is a real opposite at full strength; no user, assistant or
AI; 20 to 30 words; each negative opens as its positive does but need not
mirror it otherwise.  The opposite
is named only when the file's `negative_label` is a real word, not a `non-X`
placeholder.  The paragraph on verbs and particulars was a switch
(`--no-concrete`) while it was under test on 2026-09-29/30; files written then
carry a `concrete` field in `generator`.  Since Roger settled its wording the
paragraph is part of the template and the switch is gone.
Design log and evidence: `data/traits/instructions/TRAITS_TO_ADD.md`
§ "Trait generator V2".  Try any change to it on a copy, never on the
corpus: `--traits-dir DIR` reads and writes the trait files of a staging
directory instead of the corpus.  About $0.047 per trait, so `--all` on the
corpus is over the $20 line.  The draft was revised fourteen times between
2026-09-29 and 2026-10-01 (openings that say who the model is, no role-play;
five different openings in every file; 20 to 30 words;
particulars as the role rubric has them; no phrasing taken from the
description; negatives that open as their positives do but need not mirror
them); the design log has every draft's hash, the changes and the
measurements behind them.

For every style with a template, the script warns when a generated
instruction repeats seven or more words in a row from the template's own
example pairs (`copied_from_examples`; the file is still written, and the
status line says how many).  The generator copies what it is shown when the
trait is close to an example.  An opening frame that the rubric itself
offers ("Take on the character of someone who") is not counted.  One such
instruction in a file is tolerable; two or more add noise to the file's five
samples, and that is what the audit counts.

```bash
uv run python data_analysis/regenerate_trait_instructions.py --traits petty --style RogerV2 --dry-run --show-prompt
```

### `audit_trait_instructions.py`

Measures how common each known fault is in a set of trait files, so that a
change of rubric can be judged by numbers: how common was the fault before,
and how common is it under each version.  Written for the trait rubric V2
(2026-09-29).  An *arm* is a directory of trait files: a frozen copy of the
corpus files, or a staging copy generated under one version of the rubric.

- **Pattern checks** (no API): opening form and the variety of openings inside
  a file, chat-frame words, hedge words, the trait's own label, length, text
  repeated from the description or from the template's examples, and the
  shape of the questions.
- **Judged checks** (API; Sonnet 4.6 for the instructions, Haiku 4.5 for the
  questions, about $0.022 a file): softening, weak opposites, traits urged on
  others, states, chat frame, invented detail and motives, and for questions
  the shape, two-option choices and questions with one safe answer.  The judge
  is never told which rubric wrote a file.  It is a rough instrument (on the
  pilot traits about six in ten of its "softened" and "invented motive" flags
  were right by eye), so read its numbers as a comparison between arms judged
  the same way, not as exact rates.
- **The sample** is drawn once (`split`): 150 development traits for tuning and
  150 held-out traits, both spread over the three populations of the corpus
  (added in September 2026; older and rewritten in September; older and
  untouched).  The held-out set is staged, judged and reported only with
  `--final`, once the rubric is settled.  The 18 traits of the first pilot and
  15 traits close in meaning to the rubric's example traits are in neither.
- **The report** gives each measure per arm with a 95% interval (traits
  resampled, since the instructions of one trait are not independent), the
  share of files with the fault, and paired tests against the baseline arm on
  the same traits.

```bash
D=reports/trait_rubric_v2_pilot
uv run python data_analysis/audit_trait_instructions.py split --out $D          # once
uv run python data_analysis/audit_trait_instructions.py stage --out $D --set dev --arm v1_corpus
uv run python data_analysis/audit_trait_instructions.py stage --out $D --set dev --arm draft3
uv run python data_analysis/regenerate_trait_instructions.py --all --style RogerV2 --force \
    --traits-dir $D/stage/dev/draft3
uv run python data_analysis/audit_trait_instructions.py judge --out $D --set dev \
    --arm v1_corpus draft3:RogerV2
uv run python data_analysis/audit_trait_instructions.py report --out $D --set dev \
    --baseline v1_corpus --arm draft3:RogerV2
# the whole corpus, pattern checks only:
uv run python data_analysis/audit_trait_instructions.py report --out $D --set corpus \
    --baseline v1=data/traits/instructions
```

A staging directory starts as a copy of the corpus files, so a generation run
that fails part of the way leaves old text under the new arm's name.  Name
the arm `name:STYLE` (or `name:STYLE@template-hash` to pin one draft) and
only the files written under that style are judged and counted; the report
prints which generator wrote each arm's files.  Usage is recorded in
`<out>/judged/usage.json`, cumulative.

A trait whose label or description is not the same in every arm is left out
of the report altogether (descriptions get edited between the staging of two
arms; chaotic was rewritten on 2026-09-30), and the report says so.  Stage a
later arm from an earlier arm's directory (`stage --source`) when the
comparison must hold the descriptions fixed.

**The blind rating** (`taste`, Roger, 2026-09-30): one judge reads a file's
label, description and five positive instructions, never told which rubric
wrote them, and rates the set from 1 to 5 on *quality* (good system prompts
for a 30B to 100B open-weight model: clear, direct, at full strength) and on
*coverage* (the five between them cover every element of the description,
each a different aspect, none redundant or off the trait), reasons first.
Ratings are kept per judge model under `<out>/judged_taste/<model>/<arm>/`, so
that two judges can be compared, and the report gives the mean, the
distribution and the paired difference from the first arm.  About $0.006 a
file with Sonnet 4.6 and $0.008 with Opus 5.5 (`--dry-run` prints the
estimate; the Claude 5 models refuse a temperature, and the tool then asks
without one).

```bash
uv run python data_analysis/audit_trait_instructions.py taste --out $D --set dev \
    --arm draft5:RogerV2@fe0ec714d940 v_four_words:RogerV2@a71be163f66a --stems $D/sample100.json --write
```

### `opening_form_experiment.py`

Tests on the model itself how the wording of a trait instruction decides
whether the model takes the trait on.  Each instruction in a plan
(`<out>/plan.json`: traits, each with named variants of an instruction) is
given to the model as its system prompt with the first N questions of
`data/extraction_questions.jsonl`, and every response is scored by the
pipeline's own trait judge (`pipeline/3_judge.py`, the 0 to 3 template,
GPT-4.1-mini).  The measure is the share of responses scored 3.

The model is `qwen/qwen3-32b` through OpenRouter, with the extraction run's
settings (temperature 0.7, 512 tokens, thinking off).  **Only hosts on the
allowlist `ALLOWED_PROVIDERS` are used** (AGENT_NOTES, "Hosted models: western
hosts only"): today DeepInfra, United States; the host is pinned with no
fallback and a response naming another host is discarded.  DeepInfra serves
the model at fp8 and ignores the request to switch thinking off, so the
switch is Qwen's own `/no_think` at the end of the user turn, which the
extraction run did not have.  Because of both differences, run a replication
first: `plan-replication` writes a plan of instructions from the extraction
run with their known scores, and `report` compares.

```bash
D=reports/opening_forms/replication
uv run python data_analysis/opening_form_experiment.py plan-replication --out $D \
    --traits petty undependable cryptic --n-questions 50
uv run python data_analysis/opening_form_experiment.py generate --out $D --dry-run   # count and cost
uv run python data_analysis/opening_form_experiment.py generate --out $D
uv run python data_analysis/opening_form_experiment.py judge --out $D
uv run python data_analysis/opening_form_experiment.py report --out $D --write
```

**Depth.**  The pipeline's judge gives its top score to any answer in which
the trait is on display, a performance as much as the real thing.  `depth`
has a second judge (Sonnet 4.6, asked at Anthropic, not shown the
instruction) read each answer for how the trait shows: in whose voice, in
what the speaker does or only in what they say of themselves, and how far it
is laid on (believable, thick, a cartoon).  `depth-report` tabulates it per
opening.  Use questions written for the trait (a plan's per-trait
`"questions"`), since generic ones give most traits no occasion.

Needs `OPENROUTER_API_KEY` (Qwen), `OPENAI_API_KEY` (the judge, asked at
OpenAI directly) and, for `depth`, `ANTHROPIC_API_KEY` in `.env`.  Runs resume: only
missing responses and scores are asked for.  Usage goes to `<out>/usage.json`,
cumulative, and is written every 200 calls as well as at the end
(`CheckpointedUsage`), so a run that is killed loses at most that many calls
from the record.  Stopping a run is safe for the data (each response is
appended as it arrives); `generate --concurrency 48` gave about 260 responses
a minute at DeepInfra on 2026-09-30, the default 16 about 100.  Do not run two
commands on one `<out>` at the same time: both rewrite `usage.json` and the
per-trait score files.

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
  `<model>:batch` in `usage.json`; until 2026-10-01 the filter wrote `@batch`,
  and the first full validation run's records are read as `:batch`).  Batch
  ids and wave state are kept in
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
  batches.  The estimate follows `--second-opinion-frac` (about 0.2 of words
  at the default 0.10: the seeded sample plus the flagged words).
- **Third opinion (`--third-model MODEL`, 2026-10-02).**  For choosing a
  generator's judging model at its pilot
  ([coding_plan_platform.md](../reports/trait_gap_generation/coding_plan_platform.md),
  "M1 filter: judging model per generator"): the rows that get the second opinion also get
  the same steps (sense, established, vague, kind, same sense; no gloss) on
  MODEL, expected `claude-opus-5-5`, recorded beside `second_opinion` as
  `third_opinion` with the same shape plus `agree_first` and `agree_second`.
  `summary.json` gains an `agreement` section: first-vs-second,
  first-vs-third and second-vs-third agreement on the final outcome, overall
  and by stratum (validation runs) or generator (registry runs, from the rows'
  `sources[]`, `meta.generators`), and the first-vs-second disagreements by
  which side the third takes, as in
  [`opus_audit_m1.md`](../reports/trait_gap_generation/opus_audit_m1.md).  The
  rule there: Haiku for the generator if it agrees with Opus about 90% of the
  time or more, else Sonnet.  Cost: Opus ran the whole filter on the audit's
  207 words for $8.98 live; the third opinion runs steps 1 to 3 only, about
  $7 per 200 sampled words live and half that in batches (the estimate prints
  it by step, priced at Haiku's token counts times 1.5 for Opus).  It must
  differ from `--model` and `--second-model` and needs the second opinion.
- **Disagreement tripwire (`--max-disagreement FRACTION`, default 0.10).**  For
  later runs of a generator whose model was chosen: once the opinions'
  outcomes are known (after their established, vague and kind answers, wave
  5), the first-vs-second disagreement rate on the final outcome is computed
  over all sampled rows and for each stratum or generator with at least 20
  sampled rows (a smaller group is reported but never trips).  Above the
  threshold the log says `*** HIGH DISAGREEMENT ***` with the source, counts,
  rate and threshold; `summary.json` and `run.json` record `tripwire`; and the
  run stops before wave 6 (alignment and descriptors, and the opinions'
  same-sense checks), keeping every answer paid for, rows `pending`,
  `stopped_by_disagreement: true`, exit status 3.  To go on regardless:
  the same command with `--resume --accept-disagreement` (recorded), which
  sends wave 6 only.  When wave 6 has nothing to send, the run finishes, is
  marked (`tripwire.action: "marked"`) and still exits 3.  `--max-disagreement
  1` turns it off.  Validation runs on hard strata are expected to trip it
  (random dictionary adjectives disagreed 31% in the audit), and that is the
  point.  Alignment and descriptors moved from wave 5 to wave 6 for this, so
  a stop saves them; the number of waves is unchanged whenever an opinion has
  a same-sense check.  A batch run killed in the middle of the old wave 5
  (`w5_last_step`) before this change should be finished on the old code: the
  wave names changed (`w5_opinion_checks`, `w6_last_step`).

```bash
# the pilot on the 99 test words (never a row of m1_validation.jsonl)
uv run python data_analysis/gap_generation/traithood_filter.py --pipeline split \
    --transport live --validation-file data/candidates/validation/split_test_words.jsonl \
    --batch-id split_pilot_live --budget-usd 3 [--dry-run]
```

```bash
# a generator's pilot with the Opus third opinion; the tripwire off, since the point is to measure
uv run python data_analysis/gap_generation/traithood_filter.py --run GENERATOR/RUN_ID \
    --batch-id GENERATOR_pilot --third-model claude-opus-5-5 --max-disagreement 1 --budget-usd 10 [--dry-run]
```

Outputs in `data/candidates/filter/<batch_id>/`: `responses.jsonl` (every
response, appended as it arrives), `results.jsonl`, `summary.json` (with a
`split` block: parse rate by step and model, cost by step, the pilot figures;
and `agreement`, `tripwire`, `stopped_by_disagreement`),
`usage.json`, `run.json` and, for batches, `batches.json`.  Pilot results:
`reports/trait_gap_generation/acceptance_split.md`.

**Validation reruns (2026-10-01).**  The marks sample of a validation run
(`validation_figures.oewn_random.sample_for_marks` and
`random_traits_for_marks.md`, 50 random adjectives that passed as traits, seed 0,
listed alphabetically) is drawn only from rows never seen in development
(`meta.seen_in` empty or absent; in m1_validation 22 of the 50 had been seen).
When fewer than 50 unseen rows passed it falls back to all passing rows, and
`sample_for_marks_unseen_only` records which.  The recorded-output acceptance
tests (`assistant_axis/tests/test_gapgen_acceptance.py`) read the full run and
the stability rerun under the batch ids in `GAPGEN_FULL_BATCH` (default
`m1_validation`) and `GAPGEN_STABILITY_BATCH` (default `m1_stability`), so a
rerun is checked with `GAPGEN_FULL_BATCH=m1_validation_r2
GAPGEN_STABILITY_BATCH=m1_stability_r2 uv run python -m pytest
assistant_axis/tests/test_gapgen_acceptance.py`.  In the states pass's queue
summary, `renamed` leaves out a suggestion that is the label itself up to case,
surrounding whitespace and hyphen/space (counted in `n_name_unchanged`; the row
keeps the suggestion); spelling variants such as agonising -> agonizing are
not detected and stay in the list.

**Metric calibration (M2, Oct 2026): `gap_generation/calibrate_metric.py`.**
Calibrates the text-embedding metric M3 uses to tell whether a candidate is
already in the corpus and whether it adds a direction (plan:
[`15_metric_calibration.md`](../reports/trait_gap_generation/15_metric_calibration.md);
readout: [`pilot_m2_readout.md`](../reports/trait_gap_generation/pilot_m2_readout.md)).
Three modes, all writing under `data/candidates/calibration/` and charging the
cumulative `usage.json`; every mode prints its plan and cost estimate with
`--dry-run`, refuses an estimate over `--budget-usd`, and refuses uncommitted
platform code unless `--allow-dirty`:

- **Pilot / full calibration** (no mode flag; `--skip-llm` for the pilot):
  embeds every trait under each model x representation x space variant and
  writes the leave-one-out tables, thresholds, hubness, contrast-clause
  ablation, drop-or-merge list and histograms; without `--skip-llm` it also
  generates Haiku paraphrases (`--llm-criteria g`) and the Sonnet blinded
  judgement (`e`).  The leave-one-out residual makes a full run take about
  40 minutes: run it detached.
- **`--round4`**: the covered setting judged as retrieval.  Generates the
  missing paraphrase sets (`plain`, `terse`; `--skip-llm` uses only the
  cache), takes the M1 filter's glosses of existing labels, and writes
  `retrieval_round4.json` / `.md`: recall@1/3/5/10/20 per source and pooled,
  paired tests (McNemar, trait-clustered bootstrap, Holm), the two models'
  merged lists.  About $0.5 the first time (Haiku), $0 from the cache.
  It follows the corpus (2026-10-02, the merge with the main line): a cached
  paraphrase of a label or description that has since changed is regenerated
  (each cache records the sha256 of the text it paraphrased), the M1 glosses
  and plain-reading judgements of a renamed label count for the renamed trait
  (`labels.corpus_renames`, not the renames in `labels.SENSE_CHANGED_RENAMES`),
  and `--rebuild-labels` first rebuilds `labelled_pairs.json` from the current
  arrangements and the curation file (a curation entry that no longer applies
  is listed under `curation_unused`, not raised).  The refresh on the
  663-trait corpus cost $0.045.
- **`--write-config`** (task 19): writes `data/candidates/metric_config.json`
  for Roger's final settings from the recorded outputs, with the drift
  canary checked for `--models` (default `openai gemma`); `--config-out`
  writes elsewhere (tests).  Costs a fraction of a cent.

Every run that embeds with a real model also runs the **drift canary**: it
re-embeds the 8 texts stored in the config (or picked by the same rule before
a config exists) and logs a WARNING naming the model when one moves below
cosine 0.999 against the cache, the sign that the API model has changed and
cached vectors may no longer match new ones.

```bash
uv run python data_analysis/gap_generation/calibrate_metric.py --round4 [--rebuild-labels] --budget-usd 10 [--dry-run]
uv run python data_analysis/gap_generation/calibrate_metric.py --write-config [--dry-run]
```

`--write-config` keeps the canary texts of the config it replaces (the fixed
rule picks them only when no readable config exists), so a corpus edit never
moves the canary.

**M3 overlap rubric test (Oct 2026): `gap_generation/overlap_test.py`.**  The
pre-pilot test of the two overlap rubrics (A, concept similarity, and B,
co-occurrence: `reports/trait_gap_generation/rubrics/overlap_*.md`, pinned in
the same `versions.json` and checked by `rubric_pins.py`); design in
[`m3_overlap_rubric_draft.md`](../reports/trait_gap_generation/m3_overlap_rubric_draft.md),
results in
[`m3_overlap_test_readout.md`](../reports/trait_gap_generation/m3_overlap_test_readout.md).
Builds the pair set from cached inputs only (100 seeded targets with persona
vectors and their 3 nearest traits under the covered setting, plus the labelled
pairs between two corpus traits and the drop-or-merge pairs, grouped one call
per target), then sends every call to each rubric on Haiku 4.5, Sonnet 5.5 and
Opus 5.5, live (Haiku first, so a parse problem shows on the cheapest model).
An answer that does not parse fully is asked once more; a stage still below
99% parsed stops the run before the next stage (`--stop-below`), and
`--resume` re-sends only calls without a fully parsed answer.  Writes
`data/candidates/overlap_test/<run id>/` (`pairs.json`, `responses.jsonl`,
`usage.json` after every stage, `run.json`, `results.jsonl`, `summary.json`
with the provenance envelope, `tables.md`, `rendered_prompts.md`,
`marks_key.json`) and Roger's blinded sheet
`reports/trait_gap_generation/m3_overlap_marks.md`.  The first run
(`overlap_test_1`, 1,082 calls) cost $3.99.

The **arms experiment** (2026-10-04,
[`coding_plan_overlap_arms.md`](../reports/trait_gap_generation/coding_plan_overlap_arms.md))
added three variants of rubric A, each its own pinned file: C six rungs 0-5
(`overlap_six.md`), D the relation named with the score derived
(`overlap_relation.md`), E Roger's line 3 (`overlap_scope.md`).  `--rubrics`
takes `A B C D E` (default `A B`); every answer is also read on the **decision
scale** (rubric A's 0-4, where the cut-offs are set; C 5 -> 4, 4 -> 3; D same 4,
variant and contains 3, overlap 2, neighbours 1, different 0).  `--passes N`
(default 1) sends every call N times, each later pass with the listed traits
reshuffled (seeded by the run seed, the pass number and the call); a record's
key is (rubric, model, call, pass) and `--resume` works per key.
`--baseline-run` (default `overlap_test_1`, `none` to skip) names an earlier run
whose `pairs.json` a new run must match and whose rubric-A answers arm A's pass
1 is compared with (read only).  `summary.json` and `tables.md` gain an "arms"
part: self-consistency between the passes (also split by whether pass 2 re-sent
the same prompt), each model against the reference per pass, coverage and
crossings at cut-off 3 on the nearest pairs, D's relations and `wider`, E's named
kinds, and a cross-arm table.  `usage.json` is written after every answer, and a
live session holds a lock on its `responses.jsonl`, so a resume started while an
earlier session still runs is refused (exit 4).  `overlap_arms_1` (rubrics A, C,
D, E; two passes; Sonnet 5.5 and Opus 5.5; 2,884 calls) cost $15.89.

**Round 2** (same brief, "Round 2", 2026-10-04): `--rubrics` also takes `A2 C2 D2
E2` (`overlap_*_implies.md`, pinned as version 1), round 1's A, C, D and E with
their 2 and 3 lines redrafted around the one-way implication test.
`--write-subset` (free) computes the confusion subset from every reading on
record in `--subset-sources` (default `overlap_arms_1 overlap_test_1
overlap_test_2`; rubric B never counts; a missing source is refused): the pairs
whose readings include both a 2 and a 3 on the decision scale, or a 2 whose reason
matches round 1's containment pattern and not its two-sided one.  It writes
`<run dir>/subset.json` (provenance envelope; the rule, the counts, the pair ids,
the calls that hold them, the controls, and the evidence per pair).
`--calls-from <subset.json>` sends only the calls it names, whole (the pair set and
the `--baseline-run` check are unchanged; the file is copied into the run
directory; a resume must name the same calls).  The analysis is then made on the
calls sent, marks every `results.jsonl` row `in_subset`, and adds a "Round 2"
section to `summary.json` and `tables.md`: each round-2 arm against its round-1
arm in `--round1-run` (default `overlap_arms_1`, read only) on the same pairs, for
the subset's pairs and for every pair sent (self-consistency, agreement, the share
at 3, crossings and flips over every pair of the population, the self-contradiction
rates both ways, D2's `wider`), the brief's test, and the first answers behind the
counts with their reasons.

```bash
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --dry-run   # plan, estimate, rendered prompts
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --budget-usd 15 [--resume]
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --analyse-only
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --decode-marks  # after Roger marks the sheet
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_1 \
    --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A C D E --passes 2 --budget-usd 20 [--dry-run | --resume]
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_2 --write-subset   # free
uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_2 \
    --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A2 C2 D2 E2 --passes 2 --budget-usd 12 \
    --calls-from data/candidates/overlap_test/overlap_arms_2/subset.json [--dry-run | --resume]
```

**Corpus regions after a corpus change.**  `gap_registry.py corpus-regions`
takes `--from-filter` more than once; a trait takes its entry from the last
run that has it, and a row under a renamed stem counts for the renamed trait.
After the 2026-10-02 merge:

```bash
uv run python data_analysis/gap_generation/gap_registry.py corpus-regions \
    --from-filter data/candidates/filter/m1_validation_r2 \
    --from-filter data/candidates/filter/new_corpus_labels_2026_10_02
```

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
