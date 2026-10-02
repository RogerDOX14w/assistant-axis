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
