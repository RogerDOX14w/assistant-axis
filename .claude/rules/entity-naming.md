---
paths:
- assistant_axis/entity_id.py
- assistant_axis/judge_loaders.py
- data_analysis/**
- results_analysis/**
- tools/lint_kind_collision.py
- assistant_axis/steering_judges.py
- assistant_axis/pair_list_cohort.py
---
<!-- GENERATED FILE: do not edit.  Source: AGENT_NOTES.md (section markers).  Regenerate with: uv run python tools/sync_agent_notes.py -->
# Rule: entity-naming

**When:** keying or merging trait and role data by name, or displaying entity names.  Loads automatically for files matching the `paths` above.  Source: the sections of [`AGENT_NOTES.md`](AGENT_NOTES.md) marked `rule=entity-naming`; edit there, then run `uv run python tools/sync_agent_notes.py`.

## Trait/role name collisions and the `name|R` / `name|T` convention (May 2026)

**The bug we keep almost making.** Nine names appear in BOTH the trait
and role lists (`ascetic`, `contrarian`, `cosmopolitan`, `generalist`,
`pacifist`, `patient`, `perfectionist`, `romantic`, `stoic`).  In any
data structure that mixes traits and roles, the bare name is **NOT a
unique identifier**.  Historic code did things like:

```python
merged = {}
for entry in trait_scores: merged[entry["name"]] = entry["score"]
for entry in role_scores:  merged[entry["name"]] = entry["score"]  # silently overwrites!
```

…which silently dropped one side of every collision and biased downstream
ρ calculations by ~1.5%.

### Disambiguator: `assistant_axis.entity_id`

Use [`entity_id(name, kind)`](assistant_axis/entity_id.py) whenever a
data structure could plausibly contain entries from both kinds (dict
keys, set members, JSON cache keys, sorted name lists for rho, ...).
Format: pipe-suffixed single-letter kind tag.

```python
from assistant_axis import entity_id, parse_entity_id, display_label

entity_id("patient", "roles")    # "patient|R"
entity_id("patient", "traits")   # "patient|T"
parse_entity_id("patient|R")     # EntityId(name='patient', kind='roles')
display_label("patient|R")       # "patient"   ← bare name, for plots
```

Pure-kind contexts (e.g. inside `runpod_workspace/.../{roles,traits}/`,
or a per-cohort `haiku_responses_traits_*/` cache) keep bare names —
the kind is implicit in the path.  Disambiguation is for the **mixing
layer**.

### File-name vs display-name convention (underscores ↔ spaces)

Many entities have multi-word names that exist in two forms:

| form          | example                          | where used                         |
| ------------- | -------------------------------- | ---------------------------------- |
| **file-name** | `aligned_artificial_intelligence` | every JSON key, dict key, set member, filename, scoring cache, ρ intersection key |
| **display-name** | `aligned artificial intelligence` | plot labels, axis annotations, **LLM rubric / prompt body**, console output for humans |

**Rule (Convention 2): file-name everywhere except display sites.**
Use the underscore form for any data-structure key, ID, intersection
operand, or persistence key.  Convert to space-form ONLY at the
boundary where you render the name to a human OR an LLM — and do
that locally (via the `display_form_name` helper or
`name.replace("_", " ")`).  Never the reverse: a display-form string
should never be used as a dict key, JSON key, or rho intersection
input.

**LLM prompts are display sites too.**  An LLM reading
`aligned_artificial_intelligence` parses it less naturally than
`aligned artificial intelligence` (extra tokens, distracts from the
concept).  Project-wide convention is therefore the same as for
plot labels: file-form is the canonical key, display-form is what
goes into the LLM's mouth.  Every rubric / prompt builder MUST
apply `display_form_name(...)` to entity names before injecting
them into the prompt body, examples list, or axis-name header.

Multi-word entity census (qwen-3-32b Roger 8slot corpus): 12 of 303
traits + 4 of 281 roles = 16 of ~584.  Examples: `systems_thinker`,
`kind_to_animals`, `stream_of_consciousness` (traits);
`aligned_artificial_intelligence`, `paperclip_maximizer`, `coral_reef`,
`devils_advocate` (roles).

**The audit (May 2026)** found legitimate `_ → space` conversion
sites in the codebase, all in display/annotation code:
`canonical_angles/ca1_plane.py:193`, `pair_slice_plots.py:418`,
`infer_axis_description.py:164` (PC-describer LLM prompt),
`rubric_v1_v2_compare.py:209`, `regenerate_role_instructions.py:47`
(data-prep LLM prompt), and the `display_form_name()` helper.

**LLM rubric audit (May 2026)** of every prompt builder in the
project (8 callsites; each is now annotated in-file with a brief
display-form note that points back to this section):

| Prompt builder | Status | Notes |
| --- | --- | --- |
| `axis_judge_correlation.py:build_static_prompt` | **fixed v3 (May 2026)** | Was injecting file-form `{name}`, examples, axis_name; now wraps each in `display_form_name(...)`. |
| `axis_judge_correlation.py:build_response_batch_prompt` | **fixed v3 (May 2026)** | Body anonymises the entity (v2); shared header still injected examples + axis_name in file-form, now in display-form. |
| `data_analysis/score_combinations.py:build_user_message` | **fixed (May 2026)** | Now wraps `combo['role']` / `combo['trait']` in `display_form_name(...)` at prompt injection. |
| `data_analysis/regenerate_role_instructions.py:build_eval_prompt` (+ Christina/Roger variants) | OK | Already used `role_display_name(stem)` (file-stem -> display, with overrides for `devil's advocate`). |
| `data_analysis/regenerate_trait_instructions.py:build_eval_prompt` (+ instruction variants) | OK | Already uses pre-stored display-form `positive_label` from each trait JSON (e.g. `stream-of-consciousness`). |
| `results_analysis/infer_axis_description.py:build_prompt` (PC-describer) | OK | Already used `_display_label` helper for trait/role labels. |
| `results_analysis/standardize_axis_spec.py:build_prompt` | OK | Operates on long-form pole *descriptions*, not bare entity names. |
| `assistant_axis/steering_judges.py` rubrics | **open** (low-priority) | Uses `persona.role` / `SteeringSpec.{axis_name,pos_label,neg_label}` as-is from steering config.  If config supplies file-form, prompts leak underscores.  Tracked separately; sweep configs to date have used clean labels.  Fix at SteeringSpec/PersonaSpec construction in `steering/{run_sweep,post_judge}.py`. |

**Cross-axis rejudge surface for the v3 fix** (35 distinct axis
dirs on disk across all pair lists, 57 distinct pole pairs across
all 9 `pair_list*.json` files): only **1** axis has multi-word
pole names — `systems_thinker_vs_analytical`.  So the
``axis_name`` + examples header leak is a single-axis problem
across the entire project, not just the v2 12-axis production
set.  The per-entity ``{name}`` leak in static-mode prompts
affects the 16 multi-word entities (12 traits + 4 roles, ~2.7%
of the corpus) on every axis.  Surgical rejudge cost: ~$0.49 for
the per-entity leak across all 35 axes; +$1.48 for the 1-axis
static header leak; +~$54 if redoing that one axis's response
mode at B=7 GPT + Haiku-tiered.

No internal pipeline produces or consumes display-name keys — every
ρ intersection, every set membership check, every cache key uses
the file-name form.

**Why no internal auto-conversion?**  Inside the pipeline we never
convert: every key is in file-name form by construction and any
mismatch is a bug, not user error.  Auto-coercing
`"aligned artificial intelligence"` → `"aligned_artificial_intelligence"`
in internal code obscures the mismatch and would fail anyway on
names where the user's word breaks differ
(`"obama_administration_health_team"` vs `"Obama administration's
health team"`).

**External boundary hardening (May 2026)**: the two ingest points
that accept names from outside the pipeline normalise display-form
input to file-name form with a WARNING, since the typical leak
(spaces, hyphens, capitals, apostrophes) is mechanical and easy to
detect:

1. `axis_judge_correlation.py --rejudge_names` —
   [`_parse_rejudge_names`](results_analysis/axis_judge_correlation.py)
   runs each name through
   [`normalize_to_file_name`](assistant_axis/entity_id.py); logs
   `WARNING: --rejudge_names: coerced N display-form entries...`
   when the input wasn't already canonical.
2. `optimal_axis_for_judge.py --scores_file` —
   [`_normalize_scores_file_keys`](results_analysis/optimal_axis_for_judge.py)
   runs every JSON key through `normalize_to_file_name`, logs
   `WARNING: --scores_file ...: coerced N display-form key(s)...`
   on conversions, and `SystemExit`s if two keys collide under
   normalisation (rather than silently dropping one).

`name|R` / `name|T` disambiguated ids are passed through unchanged
in both paths.  See `tests/test_entity_id.py::TestNormalizeToFileName`
and `tests/test_optimal_axis_for_judge_normalize.py` for the full
behaviour spec.

**Defensive checks already in place** for this risk class:
`StaleSchemaError` enforcement on AT-RISK static caches
(`assistant_axis/judge_loaders.py:478–533`), per-axis
`len(common) < 3 or 5` floors at every ρ site,
[`tools/lint_kind_collision.py`](tools/lint_kind_collision.py) AST
walker, and
[`assistant_axis/tests/test_collision_regression.py`](assistant_axis/tests/test_collision_regression.py)
covering 5 patterns × 9 collision names.

### Common-pitfall callout (read this before merging trait + role data)

Whenever you see this pattern in code:

```python
for kind in ("traits", "roles"):
    for entry in load_scores(axis, kind):
        merged[entry["name"]] = entry["score"]
```

**STOP.**  Replace with:

```python
from assistant_axis import entity_id

for kind in ("traits", "roles"):
    for entry in load_scores(axis, kind):
        merged[entity_id(entry["name"], kind)] = entry["score"]
```

…otherwise you are dropping nine traits or nine roles per axis.  The
canonical lint regex (`for .* in \("(traits|roles)", "(traits|roles)"\):`)
catches the dual-iteration pattern; pair every match with an
`entity_id(...)` call before the merge.

**At-risk cache families** (write disambiguated keys in mixed-kind
contexts):
* `<axis>/<judge>/scores_descriptions.json`
* `<axis>/<judge>/scores_instructions.json`
* `<axis>/<judge>/projections.json`
* `<axis>/<judge>/correlations*.json`

The per-cohort caches (`<axis>/<judge>_responses_<kind>_b<B>{...}/scores_responses*.json`)
are kind-pure by directory — bare names there remain correct.  Same for
`runpod_workspace/.../{roles,traits}/...` and any single-kind notebook.

### Producer-side / consumer-side audit (May 2026)

* **Producer**: `results_analysis/axis_judge_correlation.py` — writes
  the at-risk cache families above.  After the May 2026 fix it stamps
  disambiguated keys + `schema_version: 2`.  Old v1 caches are loud-rejected
  on read with a concrete regenerate-via command.
* **Consumers**: ~13 result-analysis scripts that merge trait + role
  data (see `phase3_consumers` in
  `trait_role_name_disambiguation_06e61abc.plan.md`).  Each migrated to
  `load_response_scores(...)` and `entity_id(name, kind)` keys.
