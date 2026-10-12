# Computing the Assistant Axis

This directory contains the 5-step pipeline for computing the Assistant Axis from scratch for any model.

## Requirements

- GPU with sufficient memory for your target model
- `OPENAI_API_KEY` environment variable (for the LLM judge in step 3)

## Pipeline Modes

### Roger mode (default)

Generates combined role+trait instructions, standalone traits, and the default baseline. Uses [`data/goal_roles_and_traits.json`](../data/goal_roles_and_traits.json) to select which roles/traits to combine.

- `r_{role}__{trait}.jsonl` — goal role x non-goal trait (goal from role)
- `t_{role}__{trait}.jsonl` — non-goal role x goal trait (goal from trait)
- `{trait}.jsonl` — standalone trait
- `{role}.jsonl` — standalone role (`--roles_only`, or the driver's `roles` type)
- `default.jsonl` — default baseline

Counted on 2026-10-12: 932 trait files in [`data/traits/instructions/`](../data/traits/instructions/) and 339 roles plus `default.json` (340 files) in [`data/roles/instructions/`](../data/roles/instructions/).  The default 30x30 grid is 900 r_ + 900 t_ = 1,800 combinations, so [`1_generate.py`](./1_generate.py) with its defaults (combinations, standalone traits, default) makes 1,800 + 932 + 1 = 2,733 entities, and [`run_pipeline.sh`](./run_pipeline.sh) with its three types (`combinations roles traits`) makes 1,800 + 339 + 932 + 1 = 3,072.

### Christina mode

Generates standalone roles (or traits) from `--roles_dir`. Run the pipeline separately for roles and traits using different `--roles_dir` and `--output_dir` to avoid filename collisions.  A traits directory has no `default.json`, so since 2026-10-12 `run_pipeline.sh` generates the default once under `<output_dir>/default/` from the roles directory (`DEFAULT_ROLE_DIR`, `../data/roles/instructions`), with the christina settings, and symlinks its response, activation and vector into the tree (as roger mode's step 0 does), so that step 5 has a default; before, step 5 always failed there.  A run over roles generates `default` with the other roles, as before.

## Running the pipeline

[`run_pipeline.sh`](./run_pipeline.sh) runs every step for one output directory.  **Run it from `pipeline/`**: it calls the steps by relative path, and its relative defaults (`--roles_dir ../data/roles/instructions`) are relative to `pipeline/`.  Started from anywhere else it exits 1 with a message before doing anything.

```bash
cd pipeline
./run_pipeline.sh                                   # roger mode, types combinations roles traits
./run_pipeline.sh --types combinations roles
./run_pipeline.sh --types r_combinations            # only the r_ half of the grid
./run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/roles
./run_pipeline.sh --mode christina --output_dir /workspace/qwen-3-32b/traits \
    --roles_dir ../data/traits/instructions
```

- **Flags**: `--mode` (`roger`), `--output_dir` (`/workspace/outputs/qwen-3-32b`), `--model` (`Qwen/Qwen3-32B`), `--roles_dir` (christina mode), `--tensor_parallel_size` (1), `--types` (any of `combinations`, `r_combinations`, `t_combinations`, `roles`, `traits`; roger mode only), `--steps23serial`, `--judge-realtime` (step 3 with `--no_batch`), `--no-scan`, `--skip-gpu-check`, `--gpu-busy-threshold-mib` (2048), `--no-tmpfs`, `--tmpfs-dir` (`/dev/shm/hf-cache`), `--tmpfs-method` (`auto`; see "Model mirror in tmpfs"), `--tmpdir` (`/dev/shm`).  The goal and non-goal counts (30), `REDUCE_QUESTIONS` (3) and the `--min_count` given to step 4 and the scan (`MIN_COUNT` 30 in roger mode, `CHRISTINA_MIN_COUNT` 50 in christina mode) are set at the top of the script.
- **Layout (roger mode)**: each type gets `<output_dir>/<type>/{responses,activations,scores,vectors}/` and `<type>/axis.pt`; `r_combinations` and `t_combinations` write into `combinations/`.  The default entity is generated, extracted and averaged once under `default/` and symlinked into each type's `responses/`, `activations/` and `vectors/`.
- **A failing step stops the pipeline**: step 1; step 2 or step 3 (before step 4, whether they ran in parallel or serially); step 4 (before step 5).  Running the same command again skips what is finished.
- **Every extraction runs into a fresh `--output_dir`** (rule since 2026-10-12, review P1 D2 / walk-through P2).  Every skip test of the pipeline is file-existence only: a response, activation or vector file that exists is never redone, whatever instructions, settings or questions it was made from, so a new extraction into an old tree keeps the old tree's files as "already exists" (reusing the May 8slot tree would have kept 580 entities' May responses).  Step 1 enforces it with the `generation_config.json` side-car (below): it refuses a responses directory that holds responses and no side-car, or whose last recorded run used other generation settings, unless `--allow_mixed_settings`.  Reruns of the same extraction (after a crash, to fill gaps) are what the skip tests are for.
- **Scan before step 5** (on unless `--no-scan`): after step 4, [`scan_missing_vectors.py`](./scan_missing_vectors.py) with `--deep_load` (see "Auditing missing or corrupt vectors").  Exit 3 (re-run candidates or `missing_activation`) **stops the pipeline before step 5**, naming the rerun lists, so no axis is built from a partial set (Roger, 2026-10-12: a stop, since a warning is easy to miss); any other non-zero scanner exit stops it too.  Fix the candidates (`4_vectors.py --overwrite <rerun list>`, step 2 first for `missing_activation`) and run the same command again.
- The run's log is `<output_dir>/pipeline_<timestamp>.log`; the warnings and errors in it are listed at the end.

### Model mirror in tmpfs

Unless `--no-tmpfs`, the driver mirrors the model's Hugging Face cache (`<HF_HOME>/hub/models--<owner>--<name>/`) into `--tmpfs-dir` (`/dev/shm/hf-cache`) and points `HF_HOME` there, so that the workers load weights from RAM and not from the network volume (cold mmap reads there can hang for hours).  Since 2026-10-12 (P8.6) the copy is made by [`assistant_axis/tmpfs.py`](../assistant_axis/tmpfs.py), run as a script, which the steering driver ([`steering/run_sweep.py`](../steering/run_sweep.py)) imports too, so there is one implementation; before, the shell had its own `cp -r` with no marker.  Both drivers take `--tmpfs-method`:

- `rsync`: `rsync -a --delete --partial` into the mirror directory; it finishes an interrupted copy and tops up an existing mirror in place.
- `cp`: a fresh copy into `.<name>.partial.<pid>` beside the mirror, renamed into place only when complete; leftover staging directories are removed first.  An existing mirror directory without a completeness marker is neither reused nor deleted (another process may be loading from it): the driver falls back to the source cache and says to delete it or use rsync.
- `auto` (default): rsync when it is installed, else cp.

Both write the completeness marker `.tmpfs_mirror_complete` (sizes, time, method), and a later run reuses a mirror only when the marker is there and the tree has not shrunk.  A mirror made by the shell's `cp -r` before 2026-10-12 has no marker: rsync tops it up (copying every file again, since `cp -r` did not keep modification times); cp refuses it.  The free-space check (1.5 × the model) is made on the mirror's own mount, the parent of `--tmpfs-dir`; when that mount is missing, there is no mirror.  `TMPDIR` is set to `--tmpdir` (falling back to `/tmp` when that is missing), as before.

## Running the steps separately

We recommend running scripts separately rather than the bash script.

- Run [`1_generate.py`](./1_generate.py) then [`2_activations.py`](./2_activations.py) in order with [task-spooler](https://github.com/justanhduc/task-spooler) or tmux
- [`3_judge.py`](./3_judge.py) can run in parallel with `2_activations.py` after `1_generate.py` completes
- Steps 4 and 5 run after 1, 2, 3 are all complete
- Run them from `pipeline/` too: step 1's `../data/...` defaults are relative to the working directory (step 3's defaults are the repository's corpus wherever it is run from)
- On rerun, steps 1, 2 and 4 skip an entity whose output file exists (step 4 unless `--overwrite`), and step 3 judges only the responses not yet in the entity's score file; step 5 always recomputes `axis.pt`.  Steps 2 and 4 check for work before importing torch (since 2026-10-12), so a rerun with nothing to do returns at once instead of spending the torch import, which takes minutes from the pod's network volume; and the `assistant_axis` package's `__init__` loads its submodules lazily, so step 3 (and any script importing a light module such as `assistant_axis.entity_id`) imports no torch at all
- Each step exits non-zero when its output is incomplete (details under each step), which is what lets `run_pipeline.sh` stop
- `1_generate.py` and `2_activations.py` run `total_gpus / tensor_parallel_size` workers in parallel

## Step-by-Step Instructions

### 1. Generate Responses

```bash
# Roger mode (combined + traits + default)
uv run 1_generate.py \
    --model Qwen/Qwen3-32B \
    --mode roger \
    --goal_count 30 --non_goal_count 30 \
    --output_dir outputs/roger/responses

# Christina mode (roles only)
uv run 1_generate.py \
    --model Qwen/Qwen3-32B \
    --mode christina \
    --output_dir outputs/roles/responses
```

Each entity produces up to 1500 responses (5 instruction variants × 300 questions in roger mode; 5 × 240 in christina mode).  With `--reduce_questions N` (default `3` for roger, `1` for christina) every Nth question is kept, so a typical roger run produces 5 × 100 = 500 responses per entity.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | required | Hugging Face model name |
| `--output_dir` | required | Output directory for the JSONL files |
| `--mode` | `roger` | `roger` or `christina` |
| `--goal_count` | 30 | Top-N from each goal list (roger mode) |
| `--non_goal_count` | 30 | Top-N from each non-goal list (roger mode) |
| `--no_traits` | off | Roger mode: combinations and default only |
| `--traits_only` | off | Roger mode: standalone traits only |
| `--roles_only` | off | Roger mode: standalone roles only (every file in `--roles_dir`, `default.json` included) |
| `--combos_only_r` / `--combos_only_t` | off | Roger mode: only the r_ or only the t_ half of the grid (same output directory as the full grid) |
| `--roles` | all | Keep only the work items with these output names (a role or trait stem, `default`, `r_<role>__<trait>`, `t_<role>__<trait>`), in either mode; a name that matches no work item is warned about |
| `--traits_dir` | `../data/traits/instructions` | Trait JSON directory |
| `--goal_file` | `../data/goal_roles_and_traits.json` | Goal lists file (roger mode) |
| `--roles_dir` | `../data/roles/instructions` | Role JSON directory |
| `--questions_file` | `../data/extraction_questions.jsonl` | Questions JSONL |
| `--question_count` | 300 (roger) / 240 (christina) | Questions per entity, before the reduction |
| `--reduce_questions` | 3 (roger) / 1 (christina) | Keep every Nth question |
| `--temperature` | 0.7 | Sampling temperature |
| `--top_p` | 0.9 | Top-p sampling |
| `--max_tokens` | 512 | Maximum tokens generated per response |
| `--max_model_len` | 2048 | vLLM maximum context length |
| `--gpu_memory_utilization` | 0.95 | vLLM GPU memory fraction |
| `--tensor_parallel_size` | all visible GPUs (one worker) | GPUs per worker; fewer than all gives `total_gpus / N` workers |
| `--allow_mixed_settings` | off | Generate into a directory whose recorded runs used other generation settings, or that holds responses and no `generation_config.json` (see below) |

`--no_traits`, `--traits_only` and `--roles_only` are mutually exclusive, the two `--combos_only_*` flags exclude each other and `--traits_only` / `--roles_only`, and all five are refused in christina mode.  The `../data/...` defaults are relative to the working directory.

An entity whose `<name>.jsonl` exists is skipped.  Each response file is written to local `/tmp`, copied beside the destination as `<name>.jsonl.inprogress` and renamed into place, so a crash never leaves a truncated file that a rerun would take as finished.

**Response records.**  Each line of `<name>.jsonl` holds `system_prompt`, `prompt_index`, `question_index` (a position in the reduced question list), `question`, `conversation` (system?, user, assistant) and `label` (`pos`), plus `role`, `trait` and `goal_source` for a combination.  Since 2026-10-12 (walk-through P6) four additive fields follow: `question_id` (the questions file's own `id`, so the original question is known whatever the reduction), `finish_reason` (vLLM's: `stop`, or `length` when the response was cut at `--max_tokens`), `thinking_stripped` (Qwen's leaked `</think>` was cut off the text) and `thinking_suspected` (the text speaks of "the user" in the third person within its first 600 characters, the sign of untagged leaked planning; the text is kept; [`generation.py`](../assistant_axis/generation.py) `looks_like_leaked_thinking`, which flags 196 of the 8slot tree's 291,000 role and trait responses).  Steps 2 and 3 read records by key, so the new fields change nothing there (tested).

**The side-car `generation_config.json`** (since 2026-10-12, walk-through P2).  Before generating anything, step 1 appends a record of the run to `<output_dir>/generation_config.json` (`{"schema": 1, "runs": [...]}`; a `.json`, so no `*.jsonl` glob sees it), written by [`assistant_axis/generation.py`](../assistant_axis/generation.py) `write_generation_config`.  The field names are those of the multi-model plan ([coding_plan_multi_model_extraction.md](../reports/pipeline/coding_plan_multi_model_extraction.md) § 7), which adds the tokenizer-derived fields (`model_type`, `header_ids`, `sample_prompt_ids`, ...) when it is built.  Each record holds:

- `script`, `created_at` (UTC), `git_sha` (`+dirty` when tracked files were modified), `model_name`;
- `template_kwargs` (`{"enable_thinking": false}` for Qwen) and `response_cleanup` (`strip_leaked_think` for Qwen), from the same helpers `generate_batch` uses;
- `sampling`: `temperature`, `top_p`, `max_tokens`, `max_model_len`;
- `questions`: `file`, its `sha256`, `question_count`, `reduce_questions` and `n_kept`;
- `instructions`: per directory read (`roles_dir`, `traits_dir`), its `path`, `n_files`, a content `sha256` (each file's name and bytes) and, per stem, `pos_sha256`, a hash of the `pos` instruction texts, the only part step 1 uses;
- `selection`: `mode`, the subset `flags`, `--roles`, the goal file with its `sha256` and the two counts (roger mode with combinations), the work `items` and the `pending` ones this run generates;
- `allow_mixed_settings: true` when that flag let the run in.

A rerun that has nothing to generate writes no record.  Before writing, step 1 compares the run with the last record: other model, template kwargs, clean-up, sampling or question set (by hash) is refused unless `--allow_mixed_settings`, and so is a directory with responses and no side-car (a tree made before 2026-10-12).  Changed instructions are not refused: the entities whose responses here were made from `pos` texts that have changed since are named in a WARNING (their files are kept; delete them to regenerate).

**Goal lists (roger mode).**  Every name the grid takes from [`data/goal_roles_and_traits.json`](../data/goal_roles_and_traits.json) must have its instruction file: since 2026-10-12 a missing one stops the step with exit 1 before anything is generated, naming the file and, when an instruction file records the name in `renamed_from`, the stem it was renamed to (until then it was a WARNING and the grid silently shrank).  The step logs the grid's size against the nominal, e.g. `Combination grid: 900 r_ + 900 t_ = 1800 (goal_count x non_goal_count x 2 = 30 x 30 x 2 = 1800)`; it is smaller only when a list is shorter than its count, and then the line is a WARNING with the list lengths.

**Exit status.**  The step exits 1 when a goal-list name has no file (above), when a worker died or failed to load the model (its items are not generated), or, since 2026-10-12 (P8.1), when any item failed: an item that fails is logged and the step goes on to the rest, then exits 1.  After `MAX_CONSECUTIVE_FAILURES` (20) failed items in a row a run or worker stops trying the rest of its queue, since an engine that died fails every later item fast.  What was saved stays saved, and a rerun generates only what is missing.

### 2. Extract Activations

Extract one activation tensor per response, in the 8-slot layout below:

```bash
uv run 2_activations.py \
    --model Qwen/Qwen3-32B \
    --responses_dir outputs/roger/responses \
    --output_dir outputs/roger/activations \
    --batch_size 8
```

Processes every JSONL file in `--responses_dir` (narrowed by `--roles` / `--name_prefix`) and skips one whose `<name>.pt` exists.

**What a file holds** ([`2_activations.py`](./2_activations.py), [`assistant_axis/internals/spans.py`](../assistant_axis/internals/spans.py)).  `<name>.pt` is a dict with one entry per response, keyed `{label}_p{prompt_index}_q{question_index}` (the key step 3 scores under; `label` is `pos`), plus a `"metadata"` entry.  For Qwen 3 each response's tensor is `(1 + 7, n_layers, hidden)`, bf16:

- **Slot 0**: the mean over the response's content tokens, from its first to its last non-whitespace token.  The assistant header, the empty think block, `<|im_end|>` and the newline after it are excluded.
- **Slots 1-7**: the activation at each of the seven tokens of the Qwen 3 non-thinking assistant header, `<|im_start|>`, `assistant`, `\n`, `<think>`, `\n\n`, `</think>`, `\n\n`, one position each.  A header that cannot be found is NaN in all seven; a header token that differs from the expected one is logged as a mismatch.
- **Layers**: index j on the layer axis is the output of decoder layer j (a forward hook on the layer, which is Hugging Face's `hidden_states[j+1]`); there is no embedding row.  With `--layers` a subset, index j is the j-th listed layer, and `metadata["layers"]` names them.
- Gemma and Llama get 1 + 3 and 1 + 4 slots (their headers); a model whose family is not recognised from `--model`, or `--no-headers`, gives `(n_layers, hidden)`, the body mean only, with a warning.
- **Metadata**: `header_tokens`, `header_ids`, `model_name`, `extract_headers`, and since 2026-10-12 `layers`, `max_length`, `thinking` and `batch_size` (files written before lack these four; all of them used every layer).  Step 4 copies it into each vector and step 5 into the axis.

A conversation longer than `--max_length` tokens is cut there.  Files are saved with `torch_save_with_retry` in the older pickle format (`use_zipfile_serialization=False`, which avoids an "iostream error" on RunPod for files of this size).

**Options:**
- `--batch_size`: conversations per forward pass (default 16; `run_pipeline.sh` passes 8)
- `--layers`: layers to extract (default `all`, or a comma-separated list)
- `--max_length`: maximum sequence length (default 2048)
- `--tensor_parallel_size`: GPUs per worker (default all visible GPUs, one worker)
- `--roles`, `--name_prefix`: only these response files, or those whose name starts with the prefix (`r_` / `t_`)
- `--thinking`: Qwen thinking mode (default false; the header slots assume it off)
- `--no-headers`: body mean only

The step exits 1 when a worker died or failed to load the model, or when an entity raised or yielded no activation at all (no assistant span found in any of its conversations, which points at a tokenizer or chat-template change, not the data).  Entities after a failed one are still processed in multi-worker mode; in single-worker mode an error other than "no activation" stops the run at that entity.  What was saved stays saved, and a rerun extracts only what is missing.  The log is appended to `<output_dir>/activations.log`.

### 3. Score Responses

Score role/trait adherence using an LLM judge:

```bash
uv run 3_judge.py \
    --entity_type trait \
    --responses_dir outputs/roger/traits/responses \
    --output_dir outputs/roger/traits/scores
```

`--entity_type` is required and says how to read the response-file names; it is not detected from the filename, because 11 names are both a role and a trait.

| `--entity_type` | Filename | Eval prompt source |
|-----------------|----------|--------------------|
| `role` | `<role>` | `eval_prompt` from the role JSON (0-3) |
| `trait` | `<trait>` | Built from the trait's label and description (0-3) |
| `combination` | `r_<role>__<trait>`, `t_<role>__<trait>` | Compound prompt from both descriptions (0-3) |
| any | `default` | Skipped (step 4 uses all its activations) |

For combinations, the prompt variants that [`data/combination_scores.json`](../data/combination_scores.json) scores 3 (incongruous; 3 of the 9,000 on 2026-10-10) are not judged, so step 4 leaves their activations out.

**Options:**
- `--entity_type`: `role`, `trait` or `combination` (required)
- `--roles_dir`, `--traits_dir`: default the repository's [`data/roles/instructions`](../data/roles/instructions/) and [`data/traits/instructions`](../data/traits/instructions/), wherever the script is run from
- `--combination_scores`: default the repository's `data/combination_scores.json`; `--no_incongruity_filtering` judges every variant
- `--roles`: specific entity names
- `--dry_run`: Preview prompts without API calls (also prints the batch plan)
- `--judge_model`: Judge model (default: `gpt-4.1-mini`; an OpenAI model that [`assistant_axis/judge_pricing.py`](../assistant_axis/judge_pricing.py) can price)
- `--max_tokens`: judge reply length (default 200: reasoning first, then the `SCORE:` line)
- `--no_batch`: judge in real time; see below
- `--batch_requests` (10,000), `--batch_poll_seconds` (60), `--batch_fallback_max` (2,000): batch mode
- `--force_unlock`: remove the scores directory's lock left by a run that ended on another host (see "One run per scores directory")
- `--batch_size` (50), `--requests_per_second` (100): real time, and the fallback for requests no batch answered

**Batch mode (the default since 2026-10-10).**  Every pending response goes
through the OpenAI Batch API at half the real-time price
([`assistant_axis/openai_batch.py`](../assistant_axis/openai_batch.py)); the
request is the real-time one (`judge.chat_request_body`).  Requests are cut into
batches of `--batch_requests` (default 10,000; the service allows 50,000 and
200 MB); a batch over the organisation's queue limit for the model is held until
another finishes, or split in half when it is over on its own.  Each batch's
scores are merged into the score files as it is collected, and the usage is
recorded under `gpt-4.1-mini:batch` in `usage.json`.  `batch_state.json`
beside the scores records the batches submitted: a restarted run collects them
instead of submitting their requests again (chunk files wait in `_batches/`).
A chunk's upload is recorded before its batch is created, so a run stopped
between the two calls leaves an upload with no batch recorded; the restart
looks the upload up among the organisation's batches and collects the batch it
finds instead of submitting the requests again.  A status check or result
download that fails is tried again at the next poll; the run gives up only
after 30 poll rounds in a row in which every check failed (about half an hour
at the default poll), leaving the batches recorded for a rerun to collect.
Requests no batch answered are judged in real time up to `--batch_fallback_max`
(2,000); past that they stay unscored.  `run_pipeline.sh --judge-realtime`
passes `--no_batch`; a `--no_batch` run refuses to start while
`batch_state.json` records batches sent and not collected (run in batch mode
first to collect them, or delete the file to abandon them).

**Checked against the real API (canary, 2026-10-12).**  One 8slot role
(`accountant`, its first 30 responses) through this script in batch mode,
`--batch_requests 15`, from the Mac into a scratch directory: two batches,
validated and answered in about three minutes, 30 of 30 parsed, $0.006
(`gpt-4.1-mini:batch`; 772 prompt and 72 completion tokens per request).
Confirmed: the `custom_id` form `<entity>|<key>` comes back intact (both
batches 15 of 15 answered and every score filed under its key); the result
body is the chat-completion shape the collector reads (`choices[0].message.content`,
`usage.prompt_tokens` / `completion_tokens`); `batches.list` returns the
newest batch first (the order the restart lookup relies on); the lock is
taken and removed.  Not observable at cents: the `token_limit_exceeded`
code, which needs a queue over the organisation's limit (the code is the one
the batch guide documents; the organisation's batch list held only the
canary's two batches, so the limit was nowhere near).  The scores agreed with
the May scores of the same responses on 24 of 30 (21 score-3 in both).

**One run per scores directory** (since 2026-10-12, walk-through P5).  A live
run (batch or real time; not `--dry_run`) holds `<scores_dir>/.3_judge.lock`,
created with `O_EXCL` and holding the run's PID, host, start time and
arguments, and removes it when it ends.  Two runs on one directory used to
interfere: the second's restart deleted the first's unsubmitted chunks, and
both collected, and charged, the same batches.  A second run exits 1 naming
the holder.  A lock whose PID is no longer running on this host is removed
with a warning; a lock from another host (a pod that has gone) needs
`--force_unlock`.

**The judge model cannot change under batches in flight** (since 2026-10-12).
A batch run that finds batches in flight requested with another model than
its `--judge_model` exits 1 before submitting anything: collected under the
new name, their scores would be mixed with the new model's and their usage
charged under the wrong price.  Rerun with the recorded model to collect
them, or delete `batch_state.json` to abandon them.

**Several runs on one organisation's queue** (the four-pod plan, walk-through
P1).  OpenAI limits the prompt tokens of the batches an organisation has
enqueued for a model at once (the queue limit `Q`, on the organisation's
limits page, platform.openai.com/settings/organization/limits; there is no API
for it).  A step-3 run submits chunks until the queue refuses one
(`token_limit_exceeded`), then holds that chunk until one of its own batches
finishes.  Runs on several pods with one API key share `Q`, so size
`--batch_requests` so that each of `N` runs can keep `k` chunks in flight:

    batch_requests <= Q / (N * k * T)

where `T` is the prompt tokens per request (about 650-800 for the October
rubric: the review measured 6.5-7.9 million per 10,000-request chunk).  With
the four pods (`N = 4`) and two chunks each (`k = 2`, so that one is being
answered while the next waits): `Q = 100 million` gives about 15,000-19,000,
so the default 10,000 is fine; `Q = 20 million` gives about 3,000-4,000, and
`--batch_requests 3000` keeps every pod busy (a 10,000-request chunk would be
refused whenever two other pods have one in the queue).  Read `Q` on the
limits page before the extraction (pod TODO item 5).  A run refused with no
batch of its own in flight splits the chunk in half, since it cannot tell a
full queue from a chunk too big for `Q` on its own; with other pods' batches
filling the queue that can halve a chunk down to 50 requests and stop the run
(`BatchFailedError`), which the sizing above makes unlikely.

**Exit status.**  The run exits 1, and `run_pipeline.sh` stops before step 4,
when requests are left unanswered, when the parse rate of the run's judge calls
is under 99%, when any entity failed (an unreadable file, a malformed
record), when another run holds the lock, when batches in flight were
requested with another model, or when the judge API refuses a request as a
whole (an HTTP 400, `JudgeRequestError` since B1: every later request would
be refused the same way, so the run stops at once; a 400 that flags one
prompt's content stays per item, an unparseable reply).  The score files
written are kept, and a rerun judges only what is missing.

**Side-cars** beside the score files: `usage.json` (cumulative token usage and
cost), `judge_rubric.json` (the rubric version and judge models the directory
was scored with), `batch_state.json` and `_batches/`.

**Size of a full run.**  For the October 2026 corpus a roger-mode run of all
three types is about 1.5 million judge calls: 466,000 trait, 169,500 role and
899,700 combination responses (500 per entity, less the 300 responses of the
three incongruous combination variants), or 635,500 for traits and roles alone.
At the `gpt-4.1-mini` batch rates ($0.20 / $0.80 per million tokens) that is
roughly $300-350, an estimate from about 750-900 prompt and 60-80 completion
tokens per call; `usage.json` records what it actually cost.

**Score scale (all types):**

| Score | Meaning |
|-------|---------|
| 0 | No characteristics, model refused |
| 1 | No characteristics (or only one for combined), model identifies as AI |
| 2 | Some characteristics but still identifies as AI |
| 3 | Fully embodying the role/trait/both |

### 4. Compute Per-Entity Vectors

Compute mean activation vectors from high-scoring (score=3) responses ([`4_vectors.py`](./4_vectors.py)):

```bash
uv run 4_vectors.py \
    --activations_dir outputs/roger/activations \
    --scores_dir outputs/roger/scores \
    --output_dir outputs/roger/vectors
```

Processes whatever files are in the input directories.  An entity's vector is the mean (`nanmean`) of its activations scored 3, the same shape as one activation (`(8, n_layers, hidden)` for Qwen 3); the entity named exactly `default` gets the mean of all its activations, unscored.  **Vectors are float32 since 2026-10-12** (walk-through P3): the activations (bf16) are averaged in float64 one at a time, without stacking them, and the mean is stored as float32 (about 10.5 MB per Qwen3-32B vector).  The May 2026 vectors are bf16; the stored bf16 mean was off by about 0.2%, which step 5's difference of close means amplified.  An activation with no score is not used, which is how the incongruity filter reaches the vectors.

**Options:**
- `--min_count`: minimum score=3 activations for a vector (default 50; `run_pipeline.sh` passes 30 in roger mode, 50 in christina mode)
- `--overwrite`: alone, recompute and overwrite every vector; `--overwrite FILE` (one entity per line, such as a scan's `missing_vectors_rerun.txt`) overwrites only the listed entities, and the rest keep skip-if-exists
- `--reduce_questions N`: use only activations whose question index is a multiple of N (default 1); it compounds with step 1's reduction

Each vector file holds `vector`, `type` (`pos_3` or `mean`), `role`, the activation file's `metadata`, and since 2026-10-12 a top-level `inputs` record of what it was computed from: `script`, `created_at`, the activation file's name and size, `n_activations`, `min_count`, `reduce_questions`, and for a scored entity the scores file's `name`, `size`, `sha256` and `n_scores`, `n_scored_activations` and `n_score3_used`, and `vector_dtype` (`float32`) and `accumulation` (`float64`).  A vector made from a partial scores file can therefore be told from a complete one later.

**Recompute rule** (since 2026-10-12, walk-through P2).  An existing vector is skipped unless it is overwritten or **stale**: its recorded `inputs.scores_file.sha256` differs from the scores file on disk now (a vector made while step 3 was still collecting batches, or before a rejudge).  A stale vector is recomputed (a WARNING names both hashes), and if the current scores no longer reach `--min_count` it is moved aside to `<name>.pt.stale`, out of step 5's `*.pt` glob.  A vector with no `inputs` record (all May 2026 vectors) counts as current.  Only vectors whose scores file is at least as new as the vector are loaded for the comparison, so a rerun with nothing changed loads none.

An existing current vector (unless overwritten) and a 0-byte placeholder activation file are skipped.  An entity with fewer than `--min_count` score=3 activations or no scores file is filtered, which is not an error.  The step exits 1 when any entity failed (an activation or scores file that cannot be read or parsed, an empty activation file, a vector that cannot be computed or saved) or the activations directory has no `.pt` files; it exits 0 when entities were only skipped or filtered.  A failed entity has no vector, so a rerun retries exactly those.

**Limitation — question-matched filtering for trait directions:**
Each entity's vector is the mean of its own score=3 activations, filtered independently.
For antonym pairs (e.g., helpful/unhelpful), the score=3 question sets can differ
substantially — "helpful" may keep 95%+ of questions while "unhelpful" keeps only ~50%.
Differencing these vectors to get a trait direction therefore mixes a true trait contrast
with a question-distribution artifact.

A future step 4b could fix this by loading both activation files for a known pair,
intersecting their score=3 question keys, and computing matched means from only the
shared questions before differencing. This must be a pipeline step (not an analysis
script) because the activation files are large.

### Auditing missing or corrupt vectors

After step 4, run [`scan_missing_vectors.py`](./scan_missing_vectors.py) to verify every entity
ended up with a corresponding vector, classify any gaps, and detect
vectors that landed at full size but are unreadable (corrupt-on-write).

**Comprehensive mode (recommended)** — point at the output root and the
scanner auto-discovers every entity-type subdir (`default/`, `roles/`,
`traits/`, `combinations/`, ...) with an `activations/` subdir, plus
every sibling `vectors*` variant (`vectors/`, `vectors_unfiltered/`, ...)
that has real (non-symlinked) `.pt` files.  A `missing_vectors_audit.json`
and `missing_vectors_rerun.txt` are written next to each scanned
vectors dir:

```bash
uv run scan_missing_vectors.py --root outputs/qwen-3-32b/ --min_count 50
```

**Single-pair mode (back-compat)**:

```bash
uv run scan_missing_vectors.py \
    --activations_dir outputs/qwen-3-32b/roles/activations \
    --vectors_dir     outputs/qwen-3-32b/roles/vectors \
    --scores_dir      outputs/qwen-3-32b/roles/scores \
    --min_count       50 \
    --deep_load \
    --rerun_list      outputs/qwen-3-32b/roles/vectors_rerun.txt
```

Pass the `--min_count` (and `--reduce_questions`) step 4 used, so that
`below_min_count` matches what step 4 skips; `run_pipeline.sh` does.

**Coverage.**  The entities scanned are the activation files plus, when a
`responses/` directory sits beside `activations/`, every response file.
Without `responses/` the scan sees only entities that have an activation file.

Each entity is classified as one of:

| status                              | meaning                                                                              |
|-------------------------------------|--------------------------------------------------------------------------------------|
| `ok`                                | vector present, healthy size, **and `torch.load` succeeds**                          |
| `stale_vector`                      | vector loads, but its recorded scores hash (`inputs.scores_file.sha256`) differs from the scores file now: computed from a partial or older scores file (since 2026-10-12; needs the load check; vectors with no record count as current) |
| `placeholder`                       | 0-byte activation file, written on purpose so that step 2 skips the entity; not a re-run candidate (the report says whether a vector exists) |
| `ok_zero_size`                      | vector exists but < 256 bytes (likely a stub from an aborted save)                   |
| `missing_activation`                | the entity has responses but neither an activation file nor a vector, and its scores do not explain it (also an activation path that is a broken symlink): step 2 has to extract it |
| `corrupt_or_truncated_activation`   | activation .pt smaller than 50% of peer median, OR (with `--deep_load`) full-size but `torch.load` raises |
| `corrupt_vector`                    | vector full-size but `torch.load` raises (the corrupt-on-write failure mode)         |
| `missing_scores`                    | filtered mode, no scores .json (judging never ran for this entity)                   |
| `below_min_count`                   | filtered mode, < `--min_count` score=3 entries (legitimate filter)                   |
| `all_nan_or_empty`                  | activations exist but contain no usable tensors                                      |
| `mysterious`                        | everything upstream looks fine but step 4 produced no vector — re-run candidate      |
| `vector_only`                       | vector present, no activation file, responses present: the activation was deleted after step 4 to save disk (a deliberate workflow, not a fault) |
| `orphan_vector`                     | vector present with neither an activation file nor responses (e.g. a renamed entity's old vector; step 5 leaves it out since 2026-10-12, as it has no responses); without `responses/`, every vector lacking an activation file |

The re-run candidates are: `mysterious`, `corrupt_or_truncated_activation`,
`corrupt_vector`, `ok_zero_size`, `stale_vector`; they make up `missing_vectors_rerun.txt`.
The scanner exits 3 when it finds any of them or a `missing_activation`
entity (0 when nothing needs attention, 1 when no scan target is found, 2 on
argument errors); `run_pipeline.sh` runs the scan between step 4 and step 5 and stops on exit 3 (since 2026-10-12; a warning before).  The
candidates come from two upstream failure modes:

- **Transient NFS short-read at step-4 read time** — pre-retry step 4
  logged a warning and skipped the entity, leaving no vector.  Show up
  as `mysterious`.
- **Corrupt-on-write at step-4 save time** — full-size vector landed
  on disk but pickle/zip stream is malformed.  Prevented on new runs by
  `torch_save_with_retry`, which verifies the copy (size, SHA-256,
  `torch.load`) before renaming it into place; the scanner's load-check
  finds historical damage.  Show up as `corrupt_vector`.

**Recovery:**

- `4_vectors.py --overwrite <vectors_dir>/missing_vectors_rerun.txt` (per
  vectors variant) recomputes `mysterious`, `corrupt_vector` and
  `ok_zero_size`: corrupt or stub vectors are overwritten, and entities with
  no vector are computed anyway.
- `corrupt_or_truncated_activation` needs step 2 first: delete the activation
  file, rerun step 2 (it extracts only what is missing), then step 4 with the
  same `--overwrite` list.
- `missing_activation` is not on the rerun list: rerun step 2, then step 4
  (which computes the vectors that do not exist yet).

**Performance / accuracy knobs:**

- The per-vector `torch.load` check is **default-on**.  Pass
  `--no_load_check` to skip it (much faster, but won't detect
  `corrupt_vector`).
- `--deep_load`: for *missing* vectors, additionally `torch.load` the
  activation file and re-apply step 4's filter to confirm the
  classification.  Without it, anything that passes the cheap shallow
  checks is reported as `mysterious`.
- In comprehensive mode, `vectors_unfiltered/` (or any `vectors*`
  variant ending in `_unfiltered`) is auto-detected as unfiltered mode
  regardless of whether `scores/` exists.

### Robust file IO (NFS / MooseFS)

Every step reads and writes through the NFS-safe helpers in
[`assistant_axis/atomic_io.py`](../assistant_axis/atomic_io.py), or the same
pattern:

- Step 1 reads the role, trait and question files with retry
  ([`assistant_axis/generation.py`](../assistant_axis/generation.py)
  `load_role`, `load_questions`) and writes each response file through local
  staging and an `.inprogress` rename (its own code, same pattern).
- Step 2 reads responses with `read_jsonl_with_retry` and saves with
  `torch_save_with_retry`.
- Step 3 reads responses and score files with retry and writes the score
  files, `usage.json`, `judge_rubric.json` and `batch_state.json` with
  `atomic_write_text`.
- Steps 4 and 5 load and save with `torch_load_with_retry` /
  `torch_save_with_retry`; the scanner reads with retry and writes its report
  with `atomic_write_text`.

The read retry:

- 5 attempts with exponential backoff `[5, 20, 60, 180]` s
  (cumulative ~265 s, matches `axis_judge_correlation`'s API retry).
- Treats `OSError`, **`RuntimeError`** *and* `EOFError` as transient,
  except `FileNotFoundError`, which is raised at once (since 2026-10-12: a
  missing file cost 265 s of retries each); `ESTALE` is still retried.
  The `RuntimeError` case is the failure mode that surfaced as
  `"storage has wrong byte size of dtype ..."` / `"PytorchStreamReader
  failed reading zip archive: ... unexpected EOF, expected N more
  bytes"` from `torch.load` on RunPod NFS — earlier code only retried
  `OSError` and missed it.

Tensor saves go through `torch_save_with_retry`, which serialises to
`TMPDIR` (point this at `/dev/shm` on RunPod; `run_pipeline.sh` does),
copies the file beside the destination as `<dest>.inprogress`, verifies
that copy, and only then renames it into place (`os.replace`).  Three
layers of verification run on the `.inprogress` copy (a failure deletes
it and triggers another copy attempt, with the same backoff):

1. **Size check** — the copy must match the staging byte-count.
   Catches outright short-writes.
2. **SHA-256 byte-equality check** — the copy must hash to the
   same digest as staging.  Catches silent byte-flips inside a
   correct-size file (e.g. corrupted NFS chunks that pass length
   checks).  This is the failure mode behind the apparently-healthy
   2.6 GB `r_guardian__casual.pt` that later refused to `torch.load`
   with `"storage has wrong byte size of dtype"`.
3. **`torch.load` round-trip** — the copy must deserialise
   end-to-end with `weights_only=False`.  Tests at the actual
   usage level; catches version-drift / pickle-format weirdness
   that byte-equality alone wouldn't.

The destination is never touched until a copy has passed: a crash during
verification leaves no file that skip-if-exists logic would take for a
finished one, and a save that fails every attempt leaves an existing file
(an `--overwrite` run's previous vector) in place.  (Until 2026-10-12 the
copy was renamed first and the destination verified afterwards.)

Cost on a ~2.6 GB activation file is roughly one extra read for
SHA-256 plus one extra read for `torch.load` (both warm in the
kernel page cache after the write, so the wall-clock impact is
measurably less than 2× the bare write).  Pass
`verify_sha256=False` and/or `verify_load=False` to opt out for
hot-path writes where the cost outweighs the safety.

If you hit a final-failure ERROR after all retries, that's a real
non-transient corruption — clear the affected file and re-run that
step.

### 5. Compute Axis

Aggregate vectors into the final axis ([`5_axis.py`](./5_axis.py)):

```bash
uv run 5_axis.py \
    --vectors_dir outputs/roger/vectors \
    --output outputs/roger/axis.pt
```

```
axis = mean(default_vectors) - nanmean(non_default_vectors)
```

The means and the difference are taken in float64, one vector at a time (no stack of every vector), and `axis.pt` is stored as **float32** (since 2026-10-12, walk-through P3; May 2026 axes are bf16, off from a float32 recomputation by 1.3-1.5% median, up to 6.3%).  A directory that mixes bf16 and float32 vectors is averaged all the same, with a WARNING (it mixes two extractions).  Steering casts the loaded axis to the model's dtype.

The vectors that take part are the `.pt` files in `--vectors_dir` whose stem
has a response file in `--responses_dir` (default: the `responses/`
directory beside the vectors directory, as the driver lays them out; since
2026-10-12, walk-through P2): the file whose role is exactly `default` (or
any vector of type `mean`) on the default side, every other on the other
side, each entity weighing the same.  A vector with no response file (a
renamed entity's old vector, a stem dropped from the corpus: the scan's
`orphan_vector`) is named in a WARNING and left out; until 2026-10-12 every
file was averaged in.  The means are taken over whole
`(n_slots, n_layers, hidden)` tensors, so every slot and layer gets its own
axis.  The axis points from role-playing toward default assistant behaviour.

The step always recomputes and overwrites `axis.pt`.  It exits 1 when the
responses directory is missing, when there is no default vector, when fewer
than `--min_entities` (default 10; a guard against a nearly empty or wrong
directory) non-default vectors remain, when the vectors' shapes differ, or
when their metadata disagree on `header_ids` or `model_name`.  `axis.pt`
holds `axis`, the first vector's `metadata`, and since 2026-10-12 an `inputs`
record of what it was made of: `script`, `created_at`, `vectors_dir`, the
`default` and `entities` stems, `n_default`, `n_entities`, `responses_dir`,
`excluded_without_responses`, `min_entities`, `vector_dtypes`, `axis_dtype` and
`accumulation`.

## Data Format

### Roles

Role definitions in [`data/roles/instructions/*.json`](../data/roles/instructions/):

```json
{
  "description": "...",
  "instruction": [
    {"pos": "You are a pirate..."},
    {"pos": "Act as a swashbuckling pirate..."}
  ],
  "eval_prompt": "Rate how well the answer embodies a pirate..."
}
```

339 roles plus [`default.json`](../data/roles/instructions/default.json) with neutral system prompts (counted 2026-10-12); every file has five instructions.

### Traits

Trait definitions in [`data/traits/instructions/*.json`](../data/traits/instructions/) (932 on 2026-10-12):

```json
{
  "positive_label": "greedy",
  "negative_label": "non-greedy",
  "description": "...",
  "instruction": [
    {"pos": "You are greedy...", "neg": "You are generous..."},
    ...
  ],
  "eval_prompt": "..."
}
```

The pipeline uses only `instruction[].pos`. The `eval_prompt` in trait files uses a 0-100 scale for analysis; the pipeline constructs its own 0-3 eval prompt from the `description`.

### Combined filename convention

`r_{role}__{trait}` — goal from role (goal role x non-goal trait)
`t_{role}__{trait}` — goal from trait (non-goal role x goal trait)

Double underscore `__` separates role and trait names.

### Questions

[`data/extraction_questions.jsonl`](../data/extraction_questions.jsonl) (300 questions designed to elicit persona-specific responses; christina mode uses the first 240 by default).

## Tips

- **Parallelization**: Steps 2 (GPU-bound) and 3 (judge-API-bound) run
  concurrently by default — they share no resources beyond step 1's response
  files, so the wall-clock saving is roughly the smaller of the two step
  times.  Disable with `--steps23serial` if you want clean per-step logs
  (e.g. for debugging); errors from either parallel branch surface and abort
  the run before step 4.
- **Checkpointing**: Steps 1, 2 and 4 skip existing outputs and step 3 skips
  responses already scored — delete to regenerate (or `4_vectors.py
  --overwrite`); step 5 always recomputes
- **Task spooler**: For long-running jobs, use [task-spooler](https://github.com/justanhduc/task-spooler)

## Pre-computed Axes and Vectors

Pre-computed axes for Gemma 2 27B, Qwen 3 32B, and Llama 3.3 70B are available on [HuggingFace](https://huggingface.co/datasets/lu-christina/assistant-axis-vectors).
