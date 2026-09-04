---
paths:
- data/goal_roles_and_traits.json
- data/traits/**
- data/roles/**
- data_analysis/generate_antonyms.py
- data_analysis/regenerate_*.py
- pipeline/1_generate.py
---
<!-- GENERATED FILE: do not edit.  Source: AGENT_NOTES.md (section markers).  Regenerate with: uv run python tools/sync_agent_notes.py -->
# Rule: trait-pairs

**When:** adding or regenerating trait clean pairs or instructions, or running combined response generation.  Loads automatically for files matching the `paths` above.  Source: the sections of [`AGENT_NOTES.md`](AGENT_NOTES.md) marked `rule=trait-pairs`; edit there, then run `uv run python tools/sync_agent_notes.py`.

## Adding New Trait Clean Pairs

When adding a new trait B that is the antonym of an existing trait A (e.g., adding `obedient` as the antonym of `rebellious`):

### Process

1. **Create seed file** in `data/traits/instructions/B.json` with `positive_label`, `description`, and `negative_label` set to `non-B` (NOT to A yet).

2. **Generate instructions** for B:
   ```bash
   uv run python data_analysis/regenerate_trait_instructions.py --traits B --force
   ```

3. **Run antonym generation** for B (and re-run for A to double-check):
   ```bash
   uv run python data_analysis/generate_antonyms.py --traits B A
   ```
   (`--traits` scopes to specific traits; omit for all.)
   This should independently discover A as B's antonym. If A's antonym generation also returns B, we have a **clean pair**: A↔B confirmed bidirectionally.

4. **Update negative_labels**: Set B's `negative_label` to A and A's to B in their instruction files.

5. **Regenerate instructions** for B with the proper antonym (the Roger prompt style injects the antonym into the neg instruction clause):
   ```bash
   uv run python data_analysis/regenerate_trait_instructions.py --traits B --force
   ```
   A should NOT need regeneration since it already has B as its negative_label.

6. **Add to `data/traits/trait_list.json`** with description.

7. **Run goal classification** if the trait needs goal scoring (for `data/goal_roles_and_traits.json`).

### Why non-X first?

Starting with `non-B` instead of `A` ensures the antonym generator discovers `A` independently from the neg instructions, rather than being primed by us providing it. This validates that the pos/neg instruction pairs genuinely capture the A↔B opposition.

### `data/goal_roles_and_traits.json` structure

Lists of roles and traits partitioned by goal content, for experimental use.
Each of `roles` and `traits` has `goal` (all-5 @ 2) and `non_goal` (all-5 @ 0) sublists.

**Ordering convention** -- items are randomized within tiers, tiers are concatenated:

- `roles.goal`: first 30 = primary set (varied), last 10 = cluster duplicates
- `roles.non_goal`: first 30 = most varied (max non-goal semantic spread), next 10 = nice-to-haves, last 30 = most redundant with first 30
- `traits.goal`: first 30 = max goal-space variation (less-HHH-default side of pairs, distinct ethical frameworks), next 10 = remaining moral circle spectrum, last 26 = default-side of pairs + redundant goal directions
- `traits.non_goal`: first 30 = max persona-property variation (less-default side of pairs), next 10 = nice-to-haves, last 17 = pair partners + redundant

### Combined response generation (pipeline)

The pipeline (`pipeline/1_generate.py`) supports two modes:

**Roger mode** (default): Generates combined role+trait instructions, standalone traits, and the default baseline. Uses `data/goal_roles_and_traits.json` to pick the top-N roles/traits from each goal/non-goal list.

- `r_{role}__{trait}` = goal role x non-goal trait (goal from role)
- `t_{role}__{trait}` = non-goal role x goal trait (goal from trait)
- Double underscore `__` separates role and trait in filenames
- Instructions are index-matched (pair 0-0, 1-1, ..., 4-4), concatenated with `\n`
- `--goal_count` / `--non_goal_count` (default 30 each) control how many items from each list; error only if a count exceeds BOTH lists it applies to

**Christina mode**: Processes standalone roles (or traits) from `--roles_dir`. Run separately per entity type (different `--roles_dir` and `--output_dir`) to avoid name collisions.

**Step 3 eval_prompt routing**: The judge (`3_judge.py`) requires an explicit `--entity_type {role,trait,combination}` flag to select the eval_prompt:

- `role` — look up stem in `data/roles/instructions/`, use its `eval_prompt` field.
- `trait` — look up stem in `data/traits/instructions/`, build a pipeline-specific 0-3 eval_prompt from the description. (The 0-100 `eval_prompt` in trait JSONs is NOT used by the pipeline, since `parse_judge_score()` rejects scores > 3.)
- `combination` — parse `r_<role>_t_<trait>` filename, build a compound 0-3 eval_prompt from both descriptions.

`default` is skipped under all entity types (step 4 uses all activations without scores).

**DO NOT try to autodetect entity type from the filename.** 9 names exist in both `data/roles/instructions/` and `data/traits/instructions/`:

    ascetic, contrarian, cosmopolitan, generalist, pacifist,
    patient, perfectionist, romantic, stoic

Any roles-first (or traits-first) fallback will silently mis-score one side for these 9. `run_pipeline.sh` passes the correct `--entity_type` per output-subdir type (Roger mode: `roles|traits|combinations`; Christina mode: inferred from `ROLES_DIR`). If you add a new standalone invocation of `3_judge.py`, you must pass `--entity_type` explicitly.

Steps 2, 4, 5 are unchanged — they process whatever files appear in their input directories.

---
