# Computing the Assistant Axis

This directory contains the 5-step pipeline for computing the Assistant Axis from scratch for any model.

## Requirements

- GPU with sufficient memory for your target model
- `OPENAI_API_KEY` environment variable (for the LLM judge in step 3)

## Pipeline Modes

### Roger mode (default)

Generates combined role+trait instructions, standalone traits, and the default baseline. Uses `data/goal_roles_and_traits.json` to select which roles/traits to combine.

- `r_{role}__{trait}.jsonl` — goal role x non-goal trait (goal from role)
- `t_{role}__{trait}.jsonl` — non-goal role x goal trait (goal from trait)
- `{trait}.jsonl` — standalone trait
- `default.jsonl` — default baseline

Default 30x30 produces 900 r_ + 900 t_ + ~245 traits + 1 default = ~2046 entities.

### Christina mode

Generates standalone roles (or traits) from `--roles_dir`. Run the pipeline separately for roles and traits using different `--roles_dir` and `--output_dir` to avoid filename collisions.

## Full pipeline tips

We recommend running scripts separately rather than the bash script.

- Run `1_generate.py` then `2_activations.py` in order with [task-spooler](https://github.com/justanhduc/task-spooler) or tmux
- `3_judge.py` can run in parallel with `2_activations.py` after `1_generate.py` completes
- Steps 4 and 5 run after 1, 2, 3 are all complete
- All scripts skip existing outputs on rerun
- `1_generate.py` and `2_activations.py` support multi-worker tensor parallelization

```bash
./run_pipeline.sh
```

Edit the script to configure model, mode, and output directory.

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

Each entity produces 1200 responses (5 instruction variants x 240 questions).

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | `roger` | `roger` or `christina` |
| `--goal_count` | 30 | Top-N from each goal list (roger mode) |
| `--non_goal_count` | 30 | Top-N from each non-goal list (roger mode) |
| `--traits_dir` | `../data/traits/instructions` | Trait JSON directory |
| `--goal_file` | `../data/goal_roles_and_traits.json` | Goal lists file (roger mode) |
| `--roles_dir` | `../data/roles/instructions` | Role JSON directory |
| `--questions_file` | `../data/extraction_questions.jsonl` | Questions JSONL |
| `--question_count` | 240 | Questions per entity |
| `--tensor_parallel_size` | auto | GPUs per worker |
| `--roles` | all | Specific role names (christina mode) |

### 2. Extract Activations

Extract mean response activations (unchanged from original):

```bash
uv run 2_activations.py \
    --model Qwen/Qwen3-32B \
    --responses_dir outputs/roger/responses \
    --output_dir outputs/roger/activations \
    --batch_size 8
```

Processes whatever JSONL files are in `--responses_dir`.

**Options:**
- `--batch_size`: Adjust for GPU memory
- `--layers`: Layers to extract (default: all)
- `--tensor_parallel_size`: GPUs per worker

### 3. Score Responses

Score role/trait adherence using an LLM judge:

```bash
uv run 3_judge.py \
    --responses_dir outputs/roger/responses \
    --output_dir outputs/roger/scores
```

The judge automatically detects response type from the filename:

| Filename pattern | Type | Eval prompt source |
|-----------------|------|-------------------|
| `r_<role>__<trait>` | Combined | Compound prompt from both descriptions (0-3) |
| `t_<role>__<trait>` | Combined | Compound prompt from both descriptions (0-3) |
| `default` | Default | Skipped (step 4 uses all activations) |
| Exists in `--roles_dir` | Role | `eval_prompt` from role JSON (0-3) |
| Exists in `--traits_dir` | Trait | Constructed from description (0-3) |

**Options:**
- `--traits_dir`: Trait JSON directory (default: `../data/traits/instructions`)
- `--roles_dir`: Role JSON directory (default: `../data/roles/instructions`)
- `--dry_run`: Preview prompts without API calls
- `--judge_model`: Judge model (default: `gpt-4.1-mini`)

**Score scale (all types):**

| Score | Meaning |
|-------|---------|
| 0 | No characteristics, model refused |
| 1 | No characteristics (or only one for combined), model identifies as AI |
| 2 | Some characteristics but still identifies as AI |
| 3 | Fully embodying the role/trait/both |

### 4. Compute Per-Entity Vectors

Compute mean activation vectors from high-scoring (score=3) responses:

```bash
uv run 4_vectors.py \
    --activations_dir outputs/roger/activations \
    --scores_dir outputs/roger/scores \
    --output_dir outputs/roger/vectors
```

Processes whatever files are in the input directories.

### 5. Compute Axis

Aggregate vectors into the final axis:

```bash
uv run 5_axis.py \
    --vectors_dir outputs/roger/vectors \
    --output outputs/roger/axis.pt
```

```
axis = mean(default_vectors) - mean(non_default_vectors)
```

## Data Format

### Roles

Role definitions in `data/roles/instructions/*.json`:

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

275 character roles plus `default.json` with neutral system prompts.

### Traits

Trait definitions in `data/traits/instructions/*.json`:

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

`data/extraction_questions.jsonl` (240 questions designed to elicit persona-specific responses).

## Tips

- **Parallelization**: Steps 2 and 3 can run in parallel once step 1 completes
- **Checkpointing**: All steps skip existing outputs — delete to regenerate
- **Task spooler**: For long-running jobs, use [task-spooler](https://github.com/justanhduc/task-spooler)

## Pre-computed Axes and Vectors

Pre-computed axes for Gemma 2 27B, Qwen 3 32B, and Llama 3.3 70B are available on [HuggingFace](https://huggingface.co/datasets/lu-christina/assistant-axis-vectors).
