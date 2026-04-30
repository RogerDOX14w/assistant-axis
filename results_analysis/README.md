# Results Analysis

Scripts that analyze outputs of the [`pipeline/`](../pipeline/) — vectors, scores,
responses, axes. Parallel in intent to [`data_analysis/`](../data_analysis/),
which _prepares_ the role/trait data for the pipeline.

## Convention: combining desc/inst scores

When reducing the four (judge × mode) judge scores `{GPT_d, GPT_i,
Son_d, Son_i}` to a single per-entity scalar, scripts in this
directory call into the canonical helper at
[`assistant_axis/judge_score_combine.py`](../assistant_axis/judge_score_combine.py).
The default weighting is **inst-tiebreak** (`0.499*desc + 0.501*inst`),
applied after averaging across the two judges per mode:

```python
from assistant_axis.judge_score_combine import combine_desc_inst_two_judges
scores = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)
# equivalent to: 0.499 * (g_d + s_d)/2 + 0.501 * (g_i + s_i)/2
```

The 0.499/0.501 weights are essentially equal but **act as a
tiebreaker** for entities where desc and inst disagree, leaning
slightly toward instructions. Empirical rationale: at slot=(3,25) /
(0,26) / (0,49), inst-tiebreak gave consistently higher mean
activation→judge ρ than equal weighting (~+0.0005 ρ), and equal in
turn beat desc-tiebreak by a similar margin -- the ordering is
monotonic across all (slot, layer) configurations tested.  This
matches the desc/inst judge audit that found instruction-mode judging
more reliable than description-mode (~99% defensible vs ~94%).

To compare or ablate, scripts that use this helper expose a CLI flag::

    --di_weights {inst_tie,equal,desc_tie}   # default: inst_tie

`equal` reproduces the historical 0.5/0.5 weighting (= 4-way mean of
the four scores). `desc_tie` is for ablation. The asymmetry only
affects entities where the two modes disagree, so the *direction* of
ρ comparisons remains essentially unchanged across the three weights;
the absolute ρ shift is in the third decimal.

Scripts using the helper today: `rho_by_slot_and_K.py`,
`rho_by_layer.py`, `whitening_k_sweep.py`, `gpt_sonnet_weight_sweep.py`.

## Convention: PNG provenance metadata

Every plot produced by a tracked script in this directory embeds
`Title / Author / Software / Creation Time / Source` text-chunks via
`assistant_axis.png_metadata` (see the helper at
[`assistant_axis/plot_metadata.py`](../assistant_axis/plot_metadata.py)
and the agent-facing convention in [`../AGENT_NOTES.md`](../AGENT_NOTES.md)).
Ad-hoc exploration scripts that produce plots also embed their full
source via `source_text=Path(__file__).read_text()`, so any PNG in the
tree carries enough provenance to reproduce.  Read with
`exiftool foo.png` or `PIL.Image.open(p).info["Source Code"]`.

## Scripts

### `axis_judge_correlation.py`

Tests how well a chosen semantic axis in activation space corresponds to
external judgement. Given an axis direction (either derived from a pair of
roles/traits, or loaded from a saved axis file) and pole descriptions plus
example lists, it:

1. Has an LLM judge score every role and trait in the corpus on a −3..+3
   rubric (excluding the pair itself and any example-list names).
2. Projects every role/trait's activation vector onto the axis, in both the
   raw activation metric and a soft-K=3 PCA-whitened metric (whitener fit
   on the held-out pool of roles + traits, with the excluded names removed
   so the same items don't define both the axis and the whitening basis).
3. Reports Spearman ρ between judge scores and projections, per token-slot
   and per metric, for up to three scoring modes:
    - the `description` field,
    - the 5 `pos` instructions,
    - score=3 model responses (question + answer).
4. Writes JSON results and a scatter-plot grid to `--output_dir`.

```bash
# Angel vs demon, three scoring modes, all slots
uv run python results_analysis/axis_judge_correlation.py \
  --pair angel demon --pair_type roles \
  --data_dir "runpod_workspace/qwen/qwen-3-32b Roger" \
  --scores_dir "runpod_workspace/qwen/qwen-3-32b Roger/roles/scores" \
  --responses_dir "runpod_workspace/qwen/qwen-3-32b Roger/roles/responses" \
  --layer 25 --whiten_K 3 --provider anthropic --all \
  --output_dir roger/axis_judge_angel_demon

# Manual axis from a saved axis.pt, scoring descriptions only
uv run python results_analysis/axis_judge_correlation.py \
  --axis_file "runpod_workspace/qwen/qwen-3-32b Roger/roles/axis.pt" \
  --neg_pole "mythical/unstructured entity" \
  --pos_pole "defined professional role with structured output" \
  --neg_examples demon,vampire,revenant,chimera \
  --pos_examples consultant,researcher,engineer,accountant,librarian \
  --data_dir "runpod_workspace/qwen/qwen-3-32b Roger" \
  --layer 25 --slot 1 --score_descriptions \
  --output_dir roger/axis_judge_pc1_roles
```

### `infer_axis_description.py`

The conceptual inverse of [`axis_judge_correlation.py`](#axis_judge_correlationpy).
That tool *takes* an axis description and *produces* per-entity
projections-vs-rubric-score correlations. This tool *takes* a per-entity
projection ranking and *produces* an axis description (axis name, two pole
descriptions, example lists) -- ready to feed straight back into
`axis_judge_correlation.py` via its `--axis_name` / `--pos_pole` / `--neg_pole`
/ `--pos_examples` / `--neg_examples` flags.

The tool is geometry-agnostic: callers compute whatever direction they want
to characterize (a contrastive pair, a CA basis vector, a PCA component, a
shear axis, ...), project all roles and traits onto it, hand the resulting
list to this tool, and get back a structured axis spec. The only thing this
tool needs to know about each entity is its name, its type (role / trait),
and the scalar projection.

Internally the tool z-normalizes the projections to mean 0, std 1, rounds
to 0.1 precision, and asks Claude Opus (`claude-opus-4-6`, with a 10K
extended-thinking budget by default) to identify what semantic axis the
direction captures. Output is a JSON file with five fields, in display-label
form for the prose and filename form for the example lists, so it can be
piped straight into the forward tool.

```bash
# Caller computes scores (any geometric flavour) and writes them to a JSON file
# (or CSV); the format is just [{name, type, score}, ...].
uv run python results_analysis/infer_axis_description.py \
  --input scored.json \
  --output axis_spec.json \
  [--style glossary] \                 # glossary (default) | inline
  [--instructions_dir data] \
  [--model claude-opus-4-6] \
  [--thinking_budget 10000] \
  [--top_n 0]                          # 0 = include all entities; >0 = top + bottom N only
```

Input format (JSON example; CSV with columns `name,type,score` also accepted):

```json
[
  {"name": "helpful",             "type": "trait", "score":  3.21},
  {"name": "advocate",            "type": "role",  "score":  2.74},
  {"name": "paperclip_maximizer", "type": "R",     "score": -1.42}
]
```

* `name`: filename format with underscores (matching `data/{roles,traits}/instructions/*.json` filenames).
* `type`: any of `R`, `T`, `role`, `trait`, `roles`, `traits` (case-insensitive).
* `score`: any float -- the raw scalar projection. The tool z-normalizes internally.

Output format (matches `axis_judge_correlation.py`'s axis-spec flags exactly):

```json
{
  "axis_name": "prosocial vs antisocial",
  "pos_pole": "This pole represents concepts oriented toward...",
  "neg_pole": "This pole represents concepts oriented toward...",
  "pos_pole_standardized": "This means being oriented toward...",
  "neg_pole_standardized": "This means being oriented toward...",
  "pos_examples": ["helpful", "advocate", "guileless", "systems_thinker"],
  "neg_examples": ["unhelpful", "deceitful", "paperclip_maximizer"]
}
```

The `pos_pole` / `neg_pole` fields hold the raw Opus output (typically
opening with "This pole/end represents..."), while
`pos_pole_standardized` / `neg_pole_standardized` are auto-rephrased by
[`standardize_axis_spec.py`](#standardize_axis_specpy) (Sonnet) into the
project's standard "This means [verb-ing]..." form -- the form expected
by the desc+inst judge. **For judge runs, prefer the `*_standardized`
fields**; the raw fields are kept for inspection / provenance.

To skip the auto-rephrase, pass `--no_standardize`.

Library API:

```python
from results_analysis.infer_axis_description import summarize_axis

result = summarize_axis(
    scores=[{"name": "helpful", "type": "trait", "score": 2.34}, ...],
    style="glossary",
)
# -> {"axis_name": ..., "pos_pole": ..., "neg_pole": ...,
#     "pos_pole_standardized": ..., "neg_pole_standardized": ...,
#     "pos_examples": [...], "neg_examples": [...]}
```

**Layout (`--style`):** the prompt sent to Opus comes in two forms:

* `glossary` (default): a compact one-line-per-entity ranking (rank, z-score,
  R/T, display label) followed by an alphabetical glossary block listing
  every entity's description. Lets the model scan the gradient first and
  consult the glossary for unfamiliar names.
* `inline`: ranking with descriptions on the same line. No cross-referencing
  required; same total token count.

The two should give similar results in most cases. Default is `glossary`
based on intuition; A/B both on a known axis (e.g.
`truthful_vs_deceitful`) if you want to lock in a winner.

**Naming convention.** Two formats coexist in the codebase:

* *Filename* (underscores, no hyphens): `systems_thinker`, `paperclip_maximizer`.
  This is what the tool's input and output use, so the output spec can be
  passed straight back to `axis_judge_correlation.py`.
* *Display label* (more human-readable): `systems-thinker` (from the trait
  JSON's `positive_label` field), `paperclip maximizer` (`_` -> ` ` for
  roles, which by convention never use hyphens). This is what the prompt
  shows the model. The tool maintains a bidirectional map and converts the
  model's emitted example labels back to filename form on parse, with a
  small fuzzy-match fallback (lowercase + alphanumerics).

**Cost.** Per axis, with default thinking budget (10K tokens):

* Input: ~42K tokens (full 579-entity list with descriptions): ~$0.63 at
  Opus list pricing ($15/M).
* Output (incl. thinking): up to 10K tokens at $75/M = ~$0.75 worst-case;
  typical usage less.
* Total: ~$1.30-1.50 per axis.

Drop with `--top_n 50` (top + bottom 50 only) for cheap experimentation
(~$0.85/axis), or `--thinking_budget 0` to disable extended thinking
(~$0.10/axis).

**Reproducibility.** Anthropic's API forces `temperature=1` when extended
thinking is enabled, so re-runs are not bit-exactly deterministic; even at
temp 0 the API isn't guaranteed reproducible. Re-runs may produce slightly
different phrasings; the inferred axis itself should be stable on hard
tasks. We don't engineer around this (no caching layer); cost per re-run is
~$1, which is cheaper than implementation complexity.

### `standardize_axis_spec.py`

A small Sonnet-based shim that **adds standardized `"This means..."`-form
pole descriptions** to an axis spec without overwriting the originals.

Position in the pipeline (auto-invoked from
[`infer_axis_description.py`](#infer_axis_descriptionpy) by default):

```
infer_axis_description.py     standardize_axis_spec.py     axis_judge_correlation.py
   (Opus, with thinking)         (Sonnet rephrase)
[sorted projection list]   ->  [pos_pole, neg_pole       ->  [pole_standardized
                                + *_standardized fields]      drop straight into
                                                              --pos_pole / --neg_pole]
```

**Why it exists.** Auto-generated specs typically open their pole
descriptions with phrases like `"This pole represents..."` /
`"Someone who is..."`, which describe the pole as a *category* rather
than the *behavior of an entity at that pole*. The desc+inst judge
prompt template inserts pole text directly into a slot for an entity
description, so the project standard is to start each pole description
with `"This means [verb-ing/being]..."` for a behavioral framing.

The shim runs one Sonnet call per spec (~$0.002), preserving the
original `pos_pole` / `neg_pole` fields and adding new
`pos_pole_standardized` / `neg_pole_standardized` fields. All other
fields (`axis_name`, `pos_examples`, `neg_examples`, `_metadata`, etc.)
are passed through unchanged.

**Auto-invocation.** When `infer_axis_description.py` runs without
`--no_standardize`, this shim is called automatically; the resulting
spec already has both raw and standardized pole text.

**Idempotent.** If a spec already has `*_standardized` fields, the shim
skips the API call. Use `--force` to re-rephrase (e.g. after editing the
prompt's multi-shot examples).

**Standalone CLI.**

```bash
# Single file
uv run python results_analysis/standardize_axis_spec.py \
  --input raw_spec.json --output spec.json

# In-place batch update (idempotent)
uv run python results_analysis/standardize_axis_spec.py \
  --in_place roger/pc_axis_describer_sweep/*/spec.json
```

**Library API.**

```python
from results_analysis.standardize_axis_spec import standardize_axis_spec
extended = standardize_axis_spec(spec)   # adds *_standardized fields
```

**Multi-shot examples in the prompt** cover every opener pattern we've
seen in 16 auto-generated specs: `"This pole represents..."`,
`"This end represents..."`, `"Someone who..."`, plus a no-op example
showing an already-standard pole pass through unchanged.

### `refill_judge_gaps.py` and the gap-detection workflow

`axis_judge_correlation.py` calls can occasionally fail mid-run due to
transient provider issues (timeouts, 5xx, rate-limit blips). The script
ships with two layers of defense:

1. **Per-call retry-with-backoff** (`RETRY_DELAYS = [5s, 20s, 60s, 180s]`).
   Transient errors -- timeouts, connection errors, 5xx, 429-rate-limit --
   are retried up to four times with growing waits. Cumulative tolerance
   ~265 s, comfortably surviving ~3-min provider blips. Permanent errors
   (`insufficient_quota`, 4xx auth/parameter errors) are *not* retried.
2. **End-of-run gap audit.** When a run finishes, every scoring mode emits
   a clear WARNING banner if any entity / batch was left unscored, and
   writes a structured `gaps.json` to the output dir. Empty modes write
   empty containers (`[]` or `{}`) so downstream tools can rely on the
   file being present.

Even with retries, gaps can persist (e.g., a multi-hour outage). The
`refill_judge_gaps.py` tool is the systematic way to find and fix them:

```bash
# Audit-only: list dirs with gaps under the experiment root.
uv run python results_analysis/refill_judge_gaps.py \
  --glob 'roger/axis_judge_experiments/*/*' --scan

# Refill one specific dir.
uv run python results_analysis/refill_judge_gaps.py \
  --dir roger/axis_judge_experiments/truthful_vs_deceitful/gpt_responses_traits

# Refill all dirty GPT-response caches under the experiment root.
uv run python results_analysis/refill_judge_gaps.py \
  --glob 'roger/axis_judge_experiments/*/gpt_responses_*'
```

The tool reads each dir's `config.json` and re-invokes
`axis_judge_correlation.py` with the same args. The inner script's
**resume logic only re-issues calls for the gaps**: parse failures aren't
cached (so they're retried), and response-mode `per_batch` entries with
`score=None` get re-attempted. So a refill costs roughly the size of the
gap, not a full re-run.

For batch refills via `run_axis_experiment_batch.py`, pass `--refill_gaps`
to bypass the "skip if `correlations.json` exists" gate. Pairs with a
clean `gaps.json` (all modes empty) are still skipped, so refilling a
mostly-clean experiment root is cheap.

### `token_position_noise_analysis.py`

Diagnostic that asks **which of the 4 token slots is the noisiest**, and
which agrees most with the others on the *direction* of role differences.
Promoted from a `roger/` script (April 2026 work) that informed the
project-wide convention of using slot 3 (`\n`) as the default working slot.

For each random triple `(A, B, C)` and each slot `s`, the script computes
six metrics measuring how similar `B−A` is to `B−C` at slot `s`:

- 3 distance flavours: cosine distance, Euclidean norm, squared norm.
- 2 cross-diff operators: `_sub` (subtraction, normalized) and `_lograt`
  (log-ratio).

For each (triple, metric, layer), the slot whose value deviates *most*
from the mean of the other three is the **odd one out**. Slots that are
odd-one-out >25 % of the time (the chance rate) are noisier than peers.

Plus pairwise-slot agreement, two ways:

- **Norm correlation**: Pearson correlation across role pairs of `‖A_s − B_s‖`
  vs `‖A_s′ − B_s′‖` -- do the slots agree on which pairs are far apart?
- **Direction agreement**: mean cosine of `(A_s − B_s)` and `(A_s′ − B_s′)`
  across role pairs -- do the slots agree on the *direction* of each pair's
  difference?

Outputs five PNGs (default to `roger/token_position_noise_out/`):

| file | content |
|---|---|
| `ooo_heatmaps.png` | Odd-one-out fraction by layer × slot, one panel per metric. |
| `ooo_summary_bars.png` | Slot odd-one-out rate per metric (avg across layers). |
| `ooo_by_layer.png` | Per-layer slot odd-one-out, averaged across the 6 metrics. |
| `pairwise_corr_matrices.png` | 4×4 norm correlation + 4×4 cosine direction agreement. |
| `pairwise_cosine_by_layer.png` | Mean cosine direction agreement vs layer. |

```bash
# Default: 280 roles × 4 slots × all layers, 1000 triples, on Roger data.
uv run python results_analysis/token_position_noise_analysis.py

# Run on traits instead, write elsewhere.
uv run python results_analysis/token_position_noise_analysis.py \
  --vectors_subdir traits/vectors \
  --output_dir roger/token_position_noise_traits
```

**Headline finding** (April 2026 run on the older `qwen-3-32b Christina
headers` data, 280 roles × 64 layers × 1000 triples): slot 3 (`\n`) is the
*least* noisy slot -- odd-one-out ~21-23 % across metrics (slightly below
the 25 % chance floor) and the highest mean diff-direction agreement with
the other three slots. Slot 0 (body-mean) is the noisiest by all six
metrics; `<|im_start|>` and `assistant` are intermediate. This empirical
finding underwrites the project's slot-3 default.

### `all_roles_pairwise_slots.py`

Companion to `token_position_noise_analysis.py`: shows the **full
per-entity distribution** of pairwise slot statistics across layers, as
transparent ribbons of thin lines (one per entity), rather than scalar
summaries. Promoted from a one-off chat-inline producer (April 2026)
that fed a fortnightly-report figure.

For each entity (default-centred so `δ = entity − default`), each pair
of slots `(s1, s2)`, and each layer `L`:

- **Top panel** -- `cos(δ[s1, L], δ[s2, L])`: do the two slots agree
  on the *direction* the entity differs from baseline?
- **Bottom panel** (log y) -- `‖δ[s2, L]‖ / ‖δ[s1, L]‖`: how does
  the *magnitude* of the deviation differ between slots?

Six slot-pairs (the 4-choose-2 set), distinct colours, all 280 entity
ribbons overlaid at α = 0.10. Three frame variants:

- **A** -- body-vs-header pairs at full alpha, header-vs-header dimmed.
- **B** -- header-vs-header pairs full alpha, body-vs-header dimmed.
- **C** -- all six pairs at equal alpha.

The legend always shows all six pairs (with the inactive ones dimmed
in the legend itself), so the legend doesn't shift between frames --
A/B/C can be stacked as click-to-appear layers in a slide deck without
any visual jitter.

Whitening (`--whitening`):

- `raw` (default): operate on raw activation differences.
- `soft_K=N`: per-(slot, layer) soft-K whitening, fit on the full
  augmented production pool (roles + traits + corpus default). **No
  leave-one-out** -- the pool is fitted once per `(slot, layer)` and
  reused for every entity. Per-entity LOO would mean ~280 extra SVDs
  per layer per slot, swamping the actual plot work; for pool size
  ~580 the bias from including the entity in its own basis is ~1/580,
  negligible. The whitener is applied to `δ` *before* computing
  cosine and norm, so both panels reflect the whitened metric.

```bash
# Default: all 3 frames, raw, all 280 roles on Roger data.
uv run python results_analysis/all_roles_pairwise_slots.py

# Whitened K=3 version (companion frames, one per variant).
uv run python results_analysis/all_roles_pairwise_slots.py \
  --whitening soft_K=3

# Run on traits instead, just the C frame (single PNG).
uv run python results_analysis/all_roles_pairwise_slots.py \
  --vectors_subdir traits/vectors --variant C
```

Outputs default to `roger/all_roles_pairwise_slots_out/`. Filenames use
the entity-kind in the prefix and append `_K=N` when whitening is on:
`all_{roles,traits}_pairwise_slots[_K=N]_{A,B,C}.png`. The full layer
set (`--max_layers None`, the default) takes ~10 s for the three raw
frames and ~25 s for the three soft-K=3 frames (256 SVDs of a 580×5120
pool are the bottleneck and they're each cheap).

**When to prefer `--whitening soft_K=3`.** Inter-pair structure
(mean of each colour-band) is essentially unchanged by soft-K=3
whitening -- which makes sense: the slot-vs-slot relational signal
lives in the residual subspace, not the top-3 PCs of overall
activation variance. But the **per-role spread** (ribbon width) does
shrink visibly, because the top-3 PCs are where most of the
between-entity amplitude variation lives. Net effect: whitening makes
the all-six-pairs `C` frame substantially less muddy without erasing
any of the headline patterns. For figures that need to show all six
pairs at once (e.g. report stills without click-to-appear stacking),
the soft-K=3 variant is the readable one; the `A`/`B` frames are fine
either way since they only show three pairs at full alpha.

### `compute_combo_marginals.py`

Computes marginal-mean vectors from the role-by-trait combination grid that
the pipeline produces under `combinations/vectors/r_*__*.pt` and
`combinations/vectors/t_*__*.pt`. Output goes to four subdirectories indexing
one axis at a time:

| subdir | construction (default `--mode residual`) | meaning |
|---|---|---|
| `r_goal/<role>.pt` | mean over partner traits B of `(r_<role>__B - traits/B)` | "average net effect of role A *on top of* its partner trait's main effect". One per goal-supplying role. |
| `r_nogoal/<trait>.pt` | mean over partner roles A of `(r_A__<trait> - roles/A)` | one per non-goal trait |
| `t_goal/<trait>.pt` | mean over partner roles A of `(t_A__<trait> - roles/A)` | one per goal-supplying trait |
| `t_nogoal/<role>.pt` | mean over partner traits B of `(t_<role>__B - traits/B)` | one per non-goal role |

#### Why residual instead of centroid?

The earlier "centroid" reduction (just `mean over partners of combo(A,B)`,
no per-row partner subtraction) is biased whenever the role×trait grid is
incomplete or imbalanced: roles paired with only some of the traits get a
marginal that bakes in the mean of *those particular partners*, which leaks
into downstream subspaces (e.g. shrinks the canonical angle between the
goal and non-goal subspaces in a misleading way).

The residual reduction subtracts the partner's standalone main effect per
contribution before averaging, so each marginal is purely "what indexed
entity A contributes net of its partner". On a fully balanced grid the
residual and centroid subspaces are identical (up to a global shift); on
imbalanced or sparse grids they differ substantially -- in canonical-angle
analyses, by tens of degrees in the median (see
`results_analysis/canonical_angles/README.md`).

The original centroid versions are preserved at
`combinations/vectors/{r_goal,r_nogoal,t_goal,t_nogoal}_legacy_centroid/`
for bit-exact reproduction of the historical PNGs.

#### Storage format

Each `.pt` is a dict `{vector, type, role|trait, metadata}` where the
vector has shape `(n_slots, n_layers, hidden)` in `bf16`, and `metadata`
records `mode` (`'residual'` or `'centroid'`) and `n_partners_averaged`
(30 typically, occasionally 27-29 because some combinations were filtered
out earlier). The mean is computed in `float32` and cast back to `bf16`
for storage to avoid cumulative `bf16` rounding error.

#### Cross-kind combo centroids (auxiliary)

The script also writes two single-vector files at the top level of
`combinations/vectors/`:

- `mean_r_combos.pt` -- mean of all 898 ``r_*__*`` combinations.
- `mean_t_combos.pt` -- mean of all 894 ``t_*__*`` combinations.

These were originally added to the canonical-angles tool's
whitening pool to inject the theatricality direction.  Empirically the
augmentation was nearly inert (CA1 changed <0.1deg at the K values we
care about); the theatricality shift on the subspace side proved
cleaner and more effective, so the canonical-angles tool no longer
uses these files.  See `results_analysis/canonical_angles/README.md`
("Why we don't inject the theatricality direction into the pool") for
the experiment summary.

The files are still produced by default for ad-hoc analyses (they're
cheap).  Pass `--skip_kind_centroids` to skip writing them.

#### Theatricality axis

The script also writes ``combinations/vectors/theatricality_axis.pt``,
a multi-component file with shape ``(n_slots, n_layers, ...)`` carrying:

- ``v_theat`` -- per-(slot, layer) **unit** theatricality direction:

      v_theat ∝ avg over kinds of mean(combo - role - trait + μ_pool)

  i.e. the residual-after-additive-fit direction.  All four
  ``combo_{r,t}_{goal,nogoal}`` residual subspaces project heavily onto
  this single direction; it represents a common-mode "performative
  persona" offset that the additive model needs as a constant term.

- ``default_offset`` -- per-(slot, layer) signed scalar
  ``(default - μ_pool) · v_theat`` (the theatricality coordinate of the
  default vector relative to the held-out pool mean).

- ``shift`` -- the per-(slot, layer) vector ``default_offset × v_theat``.
  Adding this to a ``combo_residual`` marginal relocates it from the
  residual-mean origin to the additive model's true origin.  Used by the
  canonical-angles tool's ``combo_residual_theat_shifted`` aggregation
  (see `canonical_angles/README.md`).

Pass ``--skip_theatricality_axis`` to skip writing this file.

```bash
# Default: regenerate all four subdirs as residual marginals
uv run python results_analysis/compute_combo_marginals.py

# Reproduce the legacy centroid layout (used to live in r_goal/ etc.;
# now preserved at *_legacy_centroid/) -- including default.pt copies:
uv run python results_analysis/compute_combo_marginals.py \
    --mode centroid \
    --include_default r_goal r_nogoal \
    --output_root /tmp/centroid_check

# Generate only one kind/side
uv run python results_analysis/compute_combo_marginals.py --kinds r --sides goal
```

These marginals are the input to the canonical-angles analyses
(`canonical_angles_combos_*.png`, `canonical_angles_goal_vs_nogoal_*.png`)
which compare the goal subspace to the non-goal subspace under various
whitening regimes.

### `variance_decomposition.py`

Decomposes the variance of role+trait combination activations into a
sequence of nested explanatory models, separately for each
`(slot, raw|whitened)` panel.  At each step we report ``Δ R²`` per
dataset (r_ blue, t_ orange) -- the marginal increase in fraction of
variance explained as the next model component is added:

| step | model | what it captures |
|---|---|---|
| (a) | ``role + trait − pool_mean`` | the bare additive baseline |
| (b) | + ``X · v_theat`` (heuristic ``X = pool_mean · v_theat``) | the no-fit guess at the residual direction |
| (c) | + ``X · v_theat`` (optimised ``X``) | the best scalar shift along ``v_theat`` from the additive residuals |
| (d) | + 4-param ``(a, b, c, d) ∈ [0, 1]`` weighted fit | per-kind weight asymmetry between role and trait contributions |
| (rem) | ``1 − R²(d)`` | unexplained residual |

The 4-param model parameterises the predicted combo as
``(a+b)·role + (c+d)·trait`` for r_ and ``(a+d)·role + (b+c)·trait``
for t_, which lets the four "free" coefficients absorb any per-kind
difference in how role and trait contribute.  The optimisation is
shared across r_ and t_ but the reported ``Δ R²`` is computed
per-dataset.

The whitened columns apply soft-K PCA whitening to ``role``, ``trait``,
``combo``, ``default``, and ``v_theat`` before the decomposition.
Default is ``--K 3`` (a single K column plus a "raw" column at the
left -- a 4 x 2 grid).  Pass several values for a wider K-sweep.  The whitening
basis is fit per-slot on the standard augmented canonical-angles pool
(held-out roles+traits standalones + ``default.pt``); pass
``--no-augment`` to drop the default augmentation.  ``v_theat`` is computed inline per slot (per-row
least-squares fit ``a·R + b·T ≈ combo + pool_mean``, mean residual,
unit-normalised), matching the original April 23 reconstruction.  At
slots 1-3 this matches the on-disk
``combinations/vectors/theatricality_axis.pt`` direction to cos ≈ 0.99;
at slot 0 the inline LSQ direction differs (cos ≈ 0.72) because the
"theatricality offset" is genuinely a header-slot phenomenon and the
slot-0 residual lacks a clear common-mode direction.

#### Reading the plot

What the plot shows on header slots (1, 2, 3): step (b) captures
20-37% of the per-step variance reduction in raw -- a single-direction
constant offset along ``v_theat`` explains a large chunk of the
non-additivity of combination activations, confirming the
"performative-persona" interpretation.  Step (c) adds little (the
heuristic was already a good guess), step (d) adds little more (the
additive model is nearly weight-symmetric), and ~25-30% remains
unexplained.

At the K=3 column the ``Δ R²`` shifts modestly from ``role+trait`` (a)
into ``heuristic theat_offset`` (b) compared to raw: as whitening
shrinks the top-3 PCs, the additive baseline explains a little less
of the combo variance and the constant theatricality offset becomes
proportionally more important.  Pass a wider K range (e.g. ``--K 1 2
3 4 6 8``) to see the gradient build up monotonically as more PCs are
shrunk.

Slot 0 (body mean) does NOT show the same pattern -- the heuristic
shift is near zero (raw) or only weakly positive (whitened),
consistent with theatricality being absent from the body-mean
activation.  See `canonical_angles/README.md` for further discussion.

```bash
# Default (4 slots × 2 metrics: raw, K=3 wht; layer 25, augmented pool)
uv run python results_analysis/variance_decomposition.py \
    --output roger/variance_decomp_bars.png

# Wider K-sweep at the analysis layer
uv run python results_analysis/variance_decomposition.py \
    --K 1 2 3 4 6 8 \
    --output /tmp/var_decomp_Ksweep.png

# Reproduce a historic K=128 layout
uv run python results_analysis/variance_decomposition.py \
    --K 128 --output /tmp/var_decomp_K128.png
```

The reconstructed default plot is at
[`roger/variance_decomp_bars.png`](../roger/variance_decomp_bars.png);
the original April 23 version (with a single K=128 wht column) is
preserved at
[`roger/variance_decomp_bars_apr23.png`](../roger/variance_decomp_bars_apr23.png)
for direct visual comparison.  Differences vs Apr 23 are small (within
~1-2% on raw panels; the wht panels reshuffle Δ R² between steps (b)
and (c) but their *sum* matches), driven by the augmented pool's
inclusion of ``default.pt`` in the pool-mean computation.

### `whitening_k_sweep.py` and `whitening_k_peak_fit.py`

Per-axis ρ-vs-K analysis tools for the axis-judging-correlation
pipeline.  Use these together when you want to see how soft-K
whitening shifts the agreement between an LLM judge and the
projection onto a chosen axis, and (optionally) localise a "sweet
spot" K via parabolic fits.

**Inputs (per axis pair):** the cached judge scores produced by
[`axis_judge_correlation.py`](#axis_judge_correlationpy), one
subdirectory per axis under `--experiment_dir` (default
`roger/axis_judge_experiments/`):

```
<experiment_dir>/
  pair_list_12.json                # or any other pair list
  <pos>_vs_<neg>/
    gpt/scores_descriptions.json
    gpt/scores_instructions.json
    sonnet/scores_descriptions.json
    sonnet/scores_instructions.json
    gpt_responses_traits/scores_responses.json
    gpt_responses_roles/scores_responses.json
```

The default `pair_list_12.json` is the 12 axes that currently have all
six score files cached (7 original + 5 added: `harmless/harmful`,
`honest/dishonest`, `truthful/deceitful`, `concise/verbose`,
`relativist/absolutist`).  The historical 7-axis subset lives at
`pair_list_7.json` for reproducing earlier plots.  Add new pairs by
running the judge pipeline and editing/creating a new pair list JSON.

#### `whitening_k_sweep.py`

For each axis pair and source ∈ {`desc_inst`, `responses`}, fit a
soft-K whitener on the held-out pool (excluding the two pair
endpoints) at K ∈ {0, 1, 2, 4, 8, 16, 32, 64, 128}, project all
entity vectors onto the (whitened) axis, and compute Spearman ρ
between judge scores and projections.  The `desc_inst` source combines
GPT and Sonnet × descriptions and instructions per entity using
``assistant_axis.judge_score_combine.combine_desc_inst_two_judges``
(default: inst-tiebreak weighting `0.499*desc + 0.501*inst`; see
"Combining desc/inst scores" below); the `responses` source merges GPT
response-mode mean scores from the roles + traits runs.

Outputs to `--experiment_dir`:

- `whitening_k_sweep.json` -- N × 2 × 9 records of `{pos, neg, source, K, rho}`.
- `rho_vs_whitening_K.png` -- one solid (responses) and one dotted
  (desc+inst) line per axis, colored by axis, with K on the x-axis.

```bash
# Default: 12 axes
uv run python results_analysis/whitening_k_sweep.py

# Reproduce the historical 7-axis plot
uv run python results_analysis/whitening_k_sweep.py --pairs pair_list_7.json
```

#### `whitening_k_peak_fit.py`

Reads `whitening_k_sweep.json` and fits a parabola to each ρ-vs-K
curve over K ∈ [0, 32] in two parametrisations:

- linear-K:  ``ρ(K) ≈ a + b·K + c·K²``
- log₂(K+1): ``ρ(K) ≈ a + b·log₂(K+1) + c·log₂(K+1)²``

Reports R² per fit, the fitted peak K (clipped to [0, 32]), and the
correlation between the desc+inst peak and the responses peak across
all axes.  Empirically the log parametrisation fits substantially
better -- ~0.94 mean R² across 24 curves (12 axes × 2 sources) vs
~0.84 for linear-K -- consistent with whitening operating on a
geometric (PC-rank) scale rather than a linear one.

Outputs to `--experiment_dir`:

- `whitening_k_peak_fit.json` -- per-curve fit records (R² per
  parametrisation, fitted peak K, the y-hat predictions for each
  observed K).
- `rho_vs_K_parabolic_fits.png` -- one panel per axis showing the
  observed ρ values + log-space parabolic fits for both sources, with
  vertical dashed lines at the fitted peak K.  The grid auto-sizes to
  N axes (3×4 for 12, 2×4 for 7).

```bash
# Default: 12 axes
uv run python results_analysis/whitening_k_peak_fit.py

# Reproduce the historical 7-axis plot
uv run python results_analysis/whitening_k_peak_fit.py --pairs pair_list_7.json
```

The current default plot is at
[`roger/axis_judge_experiments/rho_vs_K_parabolic_fits.png`](../roger/axis_judge_experiments/rho_vs_K_parabolic_fits.png).

#### `gpt_vs_sonnet_scatter.py`

Visualises GPT-vs-Sonnet judge agreement at the per-entity level.
For each axis, computes ``both_mean = (descriptions + instructions) / 2``
per provider and produces two scatter plots:

- ``gpt_vs_sonnet_scatter_pooled.png`` -- one figure with all axes'
  points overlaid (colored by axis), showing the pooled Spearman ρ
  across the ``(entity, axis)`` set.
- ``gpt_vs_sonnet_scatter_grid.png`` -- N-panel grid (one panel per
  axis, layout auto-sizes to ⌈N/4⌉ rows of 4) with each panel's own ρ.

Small Gaussian jitter (σ=0.08, deterministic seed) is added to both
axes since judge scores are integer-valued in [-3, 3] and many points
overlap exactly without it.

Outputs to ``--experiment_dir``:

- the two PNGs (paths overridable via ``--pooled`` / ``--grid``)
- ``gpt_vs_sonnet_rhos.json`` -- per-axis + pooled Spearman ρ.

```bash
# Default: every axis with desc+inst from both providers cached
# on disk (currently pair_list_33.json, ~33 axes).
uv run python results_analysis/gpt_vs_sonnet_scatter.py

# Reproduce the historical 7-axis plots (April 24, byte-for-byte)
uv run python results_analysis/gpt_vs_sonnet_scatter.py \
    --pairs pair_list_7.json \
    --pooled gpt_vs_sonnet_scatter_pooled_7axes.png \
    --grid gpt_vs_sonnet_scatter_grid_7axes.png \
    --rhos_json gpt_vs_sonnet_rhos_7axes.json
```

#### `gpt_sonnet_weight_sweep.py`

Sweeps the GPT/Sonnet weight in the desc+inst score average and plots
the mean per-axis projection-ρ as a function of the blend.  For each
weight ``w ∈ [0, 1]`` and each axis we compute, per entity::

    score(w) = w · ((GPT_d + GPT_i) / 2) + (1 - w) · ((Son_d + Son_i) / 2)

then take Spearman ρ vs the raw activation projection at slot 3,
layer 25, and average across all axes in the pair list.  ``w = 0.5``
corresponds to the 4-way mean of ``{GPT_d, GPT_i, Son_d, Son_i}`` we
already use across the canonical-angles + axis-judge tooling.

**Empirical finding (33 axes):**

| weight on GPT | mean ρ |
|---:|---:|
| 0.0 (pure Sonnet) | 0.5693 |
| 0.5 (50/50) | **0.5953** |
| 1.0 (pure GPT) | 0.5758 |

Mean ρ is essentially flat over ``w ∈ [0.1, 0.9]``: a parabola fit
restricted to that interior interval places the peak at ``w = 0.530``
(R² = 0.971) with ρ ≈ 0.5949, which is *0.0004 below* the discrete
50/50 value.  The endpoint kinks at ``w = 0`` and ``w = 1`` reflect a
categorical regime change ("averaging two judges" vs "single judge"),
not a smooth blend, and are excluded from the parabola fit.

**Decision.**  Continue to score desc+inst with both GPT-4.1-mini and
Sonnet-4 by default.  When reducing to a single score per entity, the
helper `assistant_axis.judge_score_combine.combine_desc_inst_two_judges`
takes the GPT/Sonnet mean separately for desc and inst, then combines
them using the **inst-tiebreak weighting** `0.499*desc + 0.501*inst`
(see "Combining desc/inst scores" section below for the empirical
rationale).  Cost: ~6× a single-provider run for ~+0.019 ρ
improvement over GPT alone (the cheaper provider) and ~+0.026 over
Sonnet alone.  Negligible per-axis sensitivity to the exact mix
(within ±0.01 of peak across ``w ∈ [0.1, 0.9]``).

The plot also colors each per-axis curve by its interior slope
``Δρ = ρ(w=0.9) − ρ(w=0.1)`` (blue → Sonnet-better, red → GPT-better)
and orders the legend the same way, so you can read off which axes
each provider is stronger at.  Headline pattern: GPT tends to win on
*cognitive-style / register* axes (systems_thinker, improvisational,
casual, passionate, confident, playful, convergent) while Sonnet
tends to win on *moral / value-laden* axes (progressive, ethereal,
harmless, individualistic, generous, idealistic, reductionist,
practical).

```bash
# Default: 33 axes
uv run python results_analysis/gpt_sonnet_weight_sweep.py
```

#### TODO: per-axis judge-mix optimisation

The current default uses a single 50/50 mix for every axis.  For
axes where one provider is clearly stronger (per the "GPT-better /
Sonnet-better" tables above; effect sizes 0.02–0.09 ρ), a per-axis
optimisation of the mix should give a small but real improvement on
those axes.  A simple test: for each axis, compute ρ at five
candidate mixes ``w ∈ {0, 0.1, 0.5, 0.9, 1.0}`` and pick the best;
project the gain (vs uniform 50/50) across the 33-axis set.  If the
gain is meaningful (>~0.01 mean ρ across axes), make the choice
data-driven; otherwise document and stick with 50/50 as the
universal default.  Should also include "weighted-by-fit-quality"
versions analogous to ``whitening_k_weighted_scatter.py``'s confidence
scheme.

Pooled ρ across the 33 axes is **+0.862 (n=18632)**, slightly higher
than the older 7-axis number (+0.816, n=3976) and the 12-axis number
(+0.817, n=6816) -- adding clean morality / register / cognitive-style
pairs raises the average agreement.  Per-axis ρ ranges from 0.681
(systems_thinker/analytical -- the messiest) to 0.923 (helpful/unhelpful)
and 0.922 (trustworthy/untrustworthy).  This is the empirical basis
for the README's ["GPT vs Sonnet agreement"](#gpt-vs-sonnet-agreement)
finding: GPT-4.1-mini is statistically equivalent to Sonnet 4 on
desc+inst judging at ~5× lower cost.

The 33-axis pair list ``pair_list_33.json`` is auto-discovered from
on-disk score files: every ``<pos>_vs_<neg>/`` directory under
``--experiment_dir`` that has all four
``{gpt,sonnet}/scores_{descriptions,instructions}.json`` files is
included.  Add new pairs by running the judge pipeline; the next
re-build of ``pair_list_33.json`` (or its successor) will pick them up.

#### `whitening_k_weighted_scatter.py`

Cross-axis summary plot: per-axis fitted peak K from desc+inst (x)
vs responses (y), in `log₂(K+1)` space, marker area ∝ per-axis fit
quality.  Asks "does the whitening sweet spot transfer across judge
sources, or is it source-specific?".

The plot reads `whitening_k_sweep.json` and refits the log-space
parabolas (the same fit used by `whitening_k_peak_fit.py`) so the
extra (a, b, c, R², |c|) intermediates are available locally; it then
combines them into a per-axis confidence weight using a few moderately
principled heuristics:

```
confidence  = peak_ρ × R² × √|c|         # per-curve
              ↑          ↑     ↑
              signal     fit   curvature (sharp vertex)
              strength   qual. → narrow peak-K uncertainty

weight      = √( confidence_di
                 × min(1, peak_ρ_di / peak_ρ_rs)   # cross-source rebalance:
                 × confidence_rs )                  # weak d+i can't
                                                    # outvote strong rs
```

Peaks falling below K=0 or above K=32 (i.e. the parabola's vertex
extrapolates outside the measured range) are clipped to the boundary
for display: a negative K is meaningless (raw is already K=0; you
can't whiten "negative" PCs), so the principled stand-in is "data
never rose above raw".

Reports unweighted Pearson + Spearman correlations and the weighted
Pearson, plus a weighted-OLS line drawn alongside the y=x reference.

Outputs to `--experiment_dir`:

- `rho_peak_K_weighted_scatter.png`
- `whitening_k_peak_fit_weighted.json` -- per-(axis, source) fit
  records including the (a, b, c) coefficients, R², peak_log,
  peak_rho, |c|, and confidence; plus the per-axis weight.

```bash
# Default: 12 axes
uv run python results_analysis/whitening_k_weighted_scatter.py

# Reproduce the historical 7-axis plot
# (this is what produced the original April 24 image; numbers match
# byte-for-byte: weighted Pearson = +0.458)
uv run python results_analysis/whitening_k_weighted_scatter.py \
    --pairs pair_list_7.json \
    --plot rho_peak_K_weighted_scatter_7axes.png \
    --fit_json whitening_k_peak_fit_weighted_7axes.json
```

#### What the curves show

Across the 12-axis set, three qualitative patterns emerge:

- **Strongly aligned axes** (helpful, harmless, honest, truthful):
  ρ is highest at K=0 and declines monotonically as K grows -- the
  axis lives close to the dominant variance directions, and shrinking
  the top PCs only erodes the signal.
- **Mid-K peakers** (progressive, concise, ecocentric, systems_thinker):
  ρ peaks at K∈[2, 8], then declines.  These axes have a meaningful
  alignment with mid-rank PCs, and aggressive whitening helps reveal
  it.
- **Flat curves** (relativist, improvisational): ρ is roughly constant
  across K -- the axis-judge agreement is largely insensitive to the
  whitening regime.

The desc+inst-vs-responses peak agreement (Spearman ρ across the 12
axes, log space, clipping non-finite peaks) sits around **0.35** --
modest agreement: clean morality axes tend to peak at K=0 in both
sources, while structural axes show substantial spread between
sources, suggesting the "right" K is partially source-specific.

#### `rho_by_slot_and_K.py`

4-panel grouped histogram: per-slot mean per-axis Spearman ρ at
several whitening levels, for two judge sources side-by-side.  Lets
you eyeball how ρ varies with slot and K simultaneously, across the
full 33-axis desc+inst panel and the 12-axis GPT-responses panel,
without picking a particular axis.

For each slot ∈ {0, 1, 2, 3} and each ``K ∈ KS`` (default
``[0, 1, 2, 3, 4, 5]``, where K=0 = raw, K>0 = soft-K whitening on
the augmented held-out pool with only the 2 axis endpoints removed)
we compute mean per-axis Spearman ρ between the projection at
``(slot, layer=25)`` and:

- **desc+inst** -- 33 axes, score per entity is
  `combine_desc_inst_two_judges(GPT_d, GPT_i, Son_d, Son_i)` --
  inst-tiebreak weighting (`0.499*desc + 0.501*inst`) by default;
- **responses** -- 12 axes, GPT-only mean over response-mode evals.

Output (to ``--experiment_dir``):

- ``rho_by_slot_and_K.png``

```bash
# Default: KS = [0, 1, 2, 3, 4, 5], 33 + 12 axis pair lists
uv run python results_analysis/rho_by_slot_and_K.py

# Custom K range
uv run python results_analysis/rho_by_slot_and_K.py --ks 0 2 4 8 16
```

Headline observations from the default run (Qwen-3-32B layer 25,
the analysis point):

- **Slot 3 wins at every K** for both sources -- desc+inst ρ
  rises from 0.621 raw to 0.640 at K=2, ≈flat across K=2…4, then
  erodes at K≥5; responses follow the same shape with a peak at
  K=2 (0.654).
- **Slot 0 is the laggard at raw** (desc+inst 0.536, responses
  0.574) but **catches up to slot 3 -- and *overtakes* slot 3 for
  responses -- once any whitening is applied**: slot 0 K=2
  responses ρ = 0.668 vs slot 3 K=2 = 0.654.  Slot 0 jumps +0.09
  ρ on responses going K=0 → K=2 while slot 3 only gains +0.02.
  This is the theatricality-PC story: at raw, slot 0's
  representation is dominated by a single PC that's largely
  orthogonal to the axis-judge signal; shrinking the top few PCs
  unmasks the remaining identity-encoding subspace.
- Slots 1 and 2 sit ~0.05 ρ below the slot 0/3 pair at every K
  for desc+inst, and respond to whitening similarly (peak at
  K=3-4, modest +0.04 lift over raw).

#### `rho_by_layer.py`

2x2 panel plot: per-layer mean per-axis Spearman ρ as a function of
transformer layer for two slots × two judge sources, with seven
whitening curves overlaid.  Tells you *which layers carry signal
in the first place*, and how that depth profile interacts with
soft-K whitening.

- Rows: slot 0 (body mean) and slot 3 (the ``\n``-after-``assistant``
  header).
- Columns: ``desc+inst`` (33 axes, GPT+Sonnet × desc/inst combined via
  inst-tiebreak weighting) and ``responses`` (12 axes, GPT-only
  response-mode mean).
- Curves: raw (black, thick) plus K ∈ {1, 2, 3, 4, 5, 6} as a
  full rainbow (purple → blue → cyan → green → yellow → red).
- Faint vertical gridlines at every even layer.

The SVD that powers soft-K whitening is computed *once* per
(slot, layer, leave-out-set) and shared across all K values, so
the whole 64-layer × 2-slot × 7-K × 33-pair sweep takes ~14 min
on a modern laptop.

Outputs (to ``--experiment_dir``):

- ``rho_by_layer.png``
- ``rho_by_layer.json`` -- per-(slot, layer, K, source) mean ρ
  table.  Used by ``--replot_from_json`` to skip the SVD and
  re-render the plot in seconds, or by ``--reuse_json`` to
  incrementally add/remove K values without recomputing the
  cached ones.

```bash
# Default: all 64 layers, slots 0+3, Ks = [0, 1, 2, 3, 4, 5, 6]
uv run python results_analysis/rho_by_layer.py

# Faster: a coarser layer sample
uv run python results_analysis/rho_by_layer.py \
    --layers 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60

# Cheap: replot from the cached JSON (no recomputation)
uv run python results_analysis/rho_by_layer.py --replot_from_json

# Incremental: e.g. add K=7 without recomputing the existing Ks
uv run python results_analysis/rho_by_layer.py \
    --ks 0 1 2 3 4 5 6 7 --reuse_json
```

Headline observations from the default run:

- **Slot 0 vs slot 3 reveal completely different whitening
  behaviours.**  At slot 0 the whitened curves sit ~0.05--0.10 ρ
  *above* raw at every layer (the gap is essentially constant
  across the 7 K values -- a single dominant PC is doing all the
  work, consistent with the theatricality direction identified in
  the canonical-angles analysis).  At slot 3 raw and whitened
  curves are tightly bunched throughout: the slot-3 representation
  has already implicitly factored that PC out.
- **The slot-3 jump at layer ~25** is sharp and unmistakable:
  desc+inst ρ rises from ~0.43 at layer 22 to ~0.62 at layer 25,
  then slowly decays to ~0.48 by layer 60.  Layer 25 is the
  current Qwen-3-32B analysis-point default (in
  ``rho_by_slot_and_K.py``, ``whitening_k_sweep.py``,
  ``gpt_sonnet_weight_sweep.py``, etc.): it sits at the start of
  the high-ρ plateau without paying the late-layer decay penalty.
  Slot 0 has a smoother, more gradual rise with no clean cliff
  edge.
- **Both slots peak in mid-to-late layers** (slot 0 around
  layers 50-55; slot 3 around layers 25-27) and **drop sharply at
  the final 1-2 layers**, consistent with the model's last-layer
  output being optimised for next-token logits rather than
  identity-encoding geometry.
- **K=6 starts to underperform K∈{2, 3, 4}** at slot 3 past layer
  ~30 (visible as the red curve sliding below the others) -- a
  gentle warning against aggressive whitening at deep layers.

#### `pair_slice_plots.py`

Per-axis-pair 2D "slice" plots that show every trait and role in the
corpus projected into the plane defined by the pair.  For each
``(pos, neg)`` pair:

- **origin** = trait mean (in the chosen whitening regime),
- **y-axis** = ``(pos − neg) / |pos − neg|`` -- pos at top,
- **x-axis** = orthogonal projection of ``(midpoint − trait_mean)``
  into the plane, then unitised.  This is the "common-mode"
  direction that both poles share relative to the trait mean.

The plot annotates trait/role names with a greedy collision-free
algorithm (priority = distance from origin + a hand-curated semantic
bonus dict, with the pair's own poles always shown as bold pole
labels).  Each panel also prints to stdout the d_pos/d_neg/d_mid
distances and the top six entities at each axis extreme.

Whitening uses the standard
``canonical_angles.data.build_augmented_whitening_pool`` (roles +
traits + ``default.pt``, **no** leave-out -- these are
visualisation plots, not held-out statistics) followed by
``fit_whitening("soft_K", pool, K=K)``, matching the rest of the
K-sweep tooling.

The **curated pair list** in ``DEFAULT_PAIRS`` is the set of 13
axis pairs (out of the 33 with judging data) for which::

    |midpoint - trait_mean|  ≥  0.5 × |pos - neg|

at slot 3, layer 25, K=3 soft whitening -- i.e. axes whose +/- pole
pair sits noticeably *off* the trait-mean origin, indicating a
substantial common-mode component shared by both poles relative to
the corpus.  Sorted by that ratio descending::

    systems_thinker / analytical    0.842
    relativist / absolutist         0.806
    ecocentric / anthropocentric    0.753   ⚠ y-flag
    individualistic / collectivistic 0.742  ⚠ y-flag
    reductionist / holistic         0.708
    progressive / conservative      0.655
    egalitarian / elitist           0.637
    convergent / divergent          0.634
    casual / formal                 0.576
    forgiving / unforgiving         0.571   ⚠ y-flag
    practical / theoretical         0.521
    improvisational / methodical    0.506
    concise / verbose               0.502

Three of the 13 carry an explicit ``y_flag`` describing where the
y-direction's actual meaning departs from the pair name -- typically
because the trait description leaned into a hyperbolic / over-loaded
framing of one pole.  The 7 originally-curated pairs (the L24/K4
"near-miss" audit set, minus ``helpful/unhelpful`` whose ratio
dropped to 0.447 at L25/K3) all retained their L24/K4 axis labels
verbatim under L25/K3 -- the +/-x and +/-y top-entity lists shifted
only at the noise-floor.

Outputs (to ``--out_dir``, default
``roger/axis_judge_experiments/pair_slices``):

- One PNG per pair, named ``{pos}_vs_{neg}_slice_K{K}.png`` (so the
  K=3 set lives alongside the historical K=4 set without overwriting).

```bash
# Default: all 8 curated pairs at slot 3, layer 25, K=3
uv run python results_analysis/pair_slice_plots.py

# One specific pair at non-default whitening
uv run python results_analysis/pair_slice_plots.py \
    --pairs progressive,conservative --K 4 \
    --out_dir /tmp/slices_K4
```

### Pole orientation convention

When the axis has a clear "good vs bad" polarity (e.g. `benign` vs `malicious`,
`honest` vs `deceptive`), put the socially-good pole as the **positive** (+3)
pole: `--pair benign malicious --pair_type traits`, not the reverse. For
morally-neutral axes (e.g. `performative` vs `functional`), either orientation
is fine.

The motivating intuition: RLHF'd judges appear to have a strong baseline
`+ = good` / `- = bad` prior, and aligning the rubric's +/- labels with the
judge's prior avoids cognitive dissonance.

#### Empirical validation (2026-04-24, malicious/benign trait pair)

We ran both orientations against both providers (Sonnet 4 and GPT-4.1-mini),
descriptions + instructions modes, 568 entities each. Headline numbers:

**Reproducibility under sign flip** (how often `score(forward) == -score(reverse)`)

| provider / mode | exact match | |δ|≤1 | |δ|≥2 |
|---|---:|---:|---:|
| Sonnet / descriptions | 79.8% | 96.7% | 3.3% |
| Sonnet / instructions | 77.1% | 98.2% | 1.8% |
| GPT / descriptions | 75.4% | 96.0% | 4.0% |
| GPT / instructions | 72.5% | 94.9% | 5.1% |

~75% exact agreement is noticeably below the "orientation-invariant" ideal
(~95%+); orientation is a real factor, not noise.

**Mean signed delta** = `mean(score_forward + score_reverse)` (>0 means
benign=+ inflates scores relative to malicious=+)

| | Sonnet | GPT |
|---|---:|---:|
| descriptions | **+0.092** | +0.011 |
| instructions | +0.021 | +0.000 |

Only Sonnet / descriptions shows clear mean-shift inflation; elsewhere the bias
is effectively zero. So the "benign=+ inflates everything uniformly" concern is
weak.

**Spearman ρ vs activation geometry — the clean signal**

The direction of orientation preference **depends on the metric**, which is
the most important finding:

*Raw metric* — benign=+ wins every comparison (16/16, p ≈ 2e-5 binomial):

| provider / mode / slot | forward (benign=+) | reverse (malicious=+) | Δ |
|---|---:|---:|---:|
| Sonnet / descriptions / slot 3 | +0.711 | +0.665 | −0.046 |
| Sonnet / instructions / slot 3 | +0.748 | +0.716 | −0.032 |
| GPT / descriptions / slot 3 | +0.704 | +0.665 | −0.039 |
| GPT / instructions / slot 3 | +0.726 | +0.685 | −0.041 |

Effect sizes 0.03–0.07 across all 4 slots, all 4 provider/mode combos.

*Whitened metric* — malicious=+ wins 14/16, effects 0.01–0.03:

| provider / mode / slot | forward (benign=+) | reverse (malicious=+) | Δ |
|---|---:|---:|---:|
| Sonnet / descriptions / slot 3 | +0.231 | +0.262 | **+0.031** |
| Sonnet / instructions / slot 3 | +0.238 | +0.271 | +0.033 |
| GPT / descriptions / slot 3 | +0.218 | +0.248 | +0.031 |
| GPT / instructions / slot 3 | +0.215 | +0.221 | +0.005 |

**This asymmetry is unexplained** and worth following up. Hypothesis: the raw
metric is dominated by high-variance PC directions that happen to carry the
judge's charity-bias inflation in the benign direction, so benign=+ orientation
"rides" that inflation constructively. Whitening removes the high-variance
dominance, making the ρ more sensitive to the judge's true discrimination
ability, which is slightly better when malicious=+ (less charity bias pulling
items toward zero from the malicious side).

**Provider-specific flip signatures**

GPT exhibits a subtle rubric-confusion pattern Sonnet does not: 14 entities
scored `(fwd=-1, rev=-1)` or `(fwd=+1, rev=+1)` — literal contradictions under
sign flip. E.g. `unhelpful` scored −1 in *both* orientations (meaning "mildly
malicious" in forward *and* "mildly benign" in reverse). Sonnet essentially
never does this; its disagreements are closer to `(fwd=+2, rev=0)` — loss of
decisiveness when malicious is forced into the + slot, not outright
contradictions.

**Practical recommendations**

- Default: `--pair <good_pole> <bad_pole>` for good-vs-bad axes. Gives the best
  raw-metric ρ and the most decisive score distribution.
- If the analysis relies on the **whitened metric**, consider running the
  reverse orientation too and reporting the better ρ (or averaging).
- If using **GPT-4.1-mini** (cheaper exploration), spot-check a few
  mildly-negative-trait entities for rubric-confusion patterns.
- For critical axes, running both orientations and averaging the scores
  gives ~0.03 ρ gain over either alone and cancels most orientation bias,
  at 2× the judge cost.

### Which scoring source and which metric — empirical findings

We ran the tool over 20 reciprocal-antonym trait axes at GPT-4.1-mini, then
selectively re-ran 7 of them with Sonnet 4 and added response-mode scoring.
The 20-axis and 7-axis data is persisted under
[`roger/axis_judge_experiments/`](../roger/axis_judge_experiments/) with
[`summary.json`](../roger/axis_judge_experiments/summary.json) (20 axes, GPT)
and [`summary_7axes_full.json`](../roger/axis_judge_experiments/summary_7axes_full.json)
(7 axes × 3 sources × 2 metrics).

#### Raw vs whitened

Across all 20 axes (GPT, slot=3, scores averaged across descriptions+instructions
per entity before correlating — "both_mean"):

| metric | mean ρ | min | max | ρ distribution |
|---|---:|---:|---:|---|
| raw | **+0.541** | +0.04 | +0.80 | wide; axis-dependent |
| whitened | +0.201 | +0.11 | +0.28 | tight cluster |

**Raw wins 19/20 axes.** Only `ecocentric/anthropocentric` flips — raw ρ is
near zero (+0.04), whitened salvages a weak signal (+0.18). The tightness of
the whitened band (σ ≈ 0.05) vs the wide raw spread (σ ≈ 0.21) is itself a
finding: the raw metric registers how well each axis aligns with the model's
dominant-variance subspace, while the whitened metric is SNR-floored by
low-variance noise and produces similar ρ for most axes regardless of their
actual representational quality.

For interpreting a single axis in isolation, **prefer raw ρ**. For cross-axis
comparison in a fairness-across-directions sense, whitened is the more
direction-neutral metric but paints a much flatter picture.

#### Scoring source: descriptions vs instructions vs responses

On the same 20 axes (GPT only):

| source | mean raw ρ | mean whitened ρ | notes |
|---|---:|---:|---|
| descriptions only | +0.512 | +0.186 | cheapest; 1 judge call per entity |
| instructions only | +0.531 | +0.201 | slight edge over descriptions |
| both_mean (avg of above) | **+0.541** | +0.201 | +0.008 raw gain over best-single; 2× cost |

On the 7-axis deeper experiment, **response-mode is the clear winner on raw**:

| source | mean raw ρ (7 axes) | mean whitened ρ |
|---|---:|---:|
| GPT desc+inst | +0.451 | +0.192 |
| Sonnet desc+inst | +0.439 | +0.184 |
| **GPT responses** | **+0.605** | +0.169 |

Mean improvement of GPT responses over best-desc+inst = **+0.135 raw ρ**, with
per-axis gains ranging from −0.05 to +0.56. The dramatic case is
`ecocentric/anthropocentric`: desc+inst essentially fails (raw ρ ≈ 0), but
responses captures it at ρ = +0.60. Behavioral evidence reveals the axis where
trait-description text is too generic to discriminate.

Response-mode does **not** help on whitened (−0.028 mean); same SNR-floor
pattern. And response-mode is ~20× more expensive than desc+inst.

#### GPT vs Sonnet agreement

On desc+inst for the same 7 axes, GPT and Sonnet agree strongly:

- Pooled across all 3,976 (entity, axis) pairs: **Spearman ρ = 0.816**.
- Per-axis agreement: 0.68–0.92, highest on strong axes (`helpful/unhelpful`
  0.92), lowest on subtle ones (`systems_thinker/analytical` 0.68).
- Per-axis ρ-vs-projection is essentially equivalent between the two providers
  (mean difference +0.011 raw in favor of Sonnet, +0.008 whitened).

For exploration and iteration, **GPT-4.1-mini is ~5× cheaper with statistically
equivalent results**. Sonnet is only worth the premium for final reporting or
for axes where the 0.01-level difference matters.

#### Recommendations

| goal | recommended source | metric | why |
|---|---|---|---|
| Sanity-check an axis cheaply | GPT desc+inst | raw | ~$1/axis, good enough signal |
| Publish ρ for a given axis | GPT responses | raw | best signal, ~$40/axis |
| Compare across axes fairly | whitened (any source) | whitened | equalizes variance across directions |
| Diagnose "does this axis exist at all?" | GPT responses | both raw and whitened | if whitened ρ is nonzero and raw ρ is near-zero, the axis lives in low-variance directions |

### Adaptive per-PC whitening — empirical study

We did an extended study of whether per-PC whitening (each PC gets its own
scale factor β_k ∈ [0, 1]) can beat fixed soft-K whitening. Four operational
conclusions, all from experiments on the 7 axes in
[`pair_list_7.json`](../roger/axis_judge_experiments/pair_list_7.json):

**1. ‖m‖/‖diff‖ predicts axis hardness (label-free).**

For an axis defined by `diff = vec[pos] − vec[neg]`, the pair's common-mode
offset is `m = (vec[pos] + vec[neg]) − 2·mean_corpus`. The ratio ‖m‖/‖diff‖
measures how far the pair's midpoint sits from the corpus center relative to
the axis magnitude.

| ‖m‖/‖diff‖ range | example axes | raw ρ range |
|---|---|---|
| < 1.0 | helpful/unhelpful | 0.78-0.82 (easy) |
| 1.0–1.5 | guileless/scheming, improvisational/methodical | 0.38-0.69 |
| > 1.5 | progressive/conservative, ecocentric/anthropocentric, systems_thinker/analytical | 0.00-0.58 (hard) |

Pearson correlation between ‖m‖/‖diff‖ and raw ρ is **−0.67** (D+I) and **−0.74**
(responses) across the 7 axes — a single-number label-free predictor of
axis quality. Large common-mode offset means the pair activations share a big
"common mode" signature that isn't the axis itself — and projecting entities
onto the axis direction picks up that shared structure as noise.

**2. soft-K=4 is the best fixed label-free recipe.**

From the whitening-K sweep across 20 axes, mean responses ρ peaks at K=4 (0.652)
vs K=0 (0.605), K=1 (0.639), K=2 (0.646), K=8 (0.587), K=16 (0.471), K=128
(0.169). See [`rho_vs_whitening_K.png`](../roger/axis_judge_experiments/rho_vs_whitening_K.png).
K=4 is the default recommendation when no judge labels are available.

**3. Label-using coord ascent finds well-generalizing β* (+0.13-0.17 held-out gain).**

[`coordinate_ascent.py`](../roger/axis_judge_experiments/coordinate_ascent.py)
implements exact per-PC Spearman-optimal β via pairwise rank-crossing
enumeration. 5-fold CV on 7 axes × 3 score sources:

| source | mean test ρ (β*) | mean test ρ (K=4) | held-out gain |
|---|---:|---:|---:|
| desc+inst | 0.671 | 0.505 | **+0.166** |
| responses | 0.766 | 0.638 | **+0.127** |
| joint (D+I+RESP) | 0.747 | 0.583 | **+0.164** |

The coarse-discrete variant (β ∈ {0, σ_{M}²/σ_k² for M ∈ {2,3,5,9,17}, 1}) gives
virtually the same held-out ρ with ~half the training-ρ overfitting — suggesting
the finer continuous β values were fitting noise. Use the coarse version for
interpretability. Per-axis data: [`coarse_discrete_coordinate_ascent.json`](../roger/axis_judge_experiments/coarse_discrete_coordinate_ascent.json).

**4. Label-free geometric rules cap at ~10-15% of oracle recovery.**

Tried (a) hand-crafted rules on c_k², m_cos_k²; (b) random forests over (log K,
c_k², m_cos_k²). In-sample: RF recovers 78% of oracle; leave-one-axis-out it
drops to ~5%. The v1 rule (Keep if c_k² ≥ 0.20, Ablate if m_cos_k²/(c_k²+m_cos_k²) ≥ 0.90,
else shrink to σ_5²) recovers ~13% in-sample. With n=7 axes, simple geometric
features can't reliably predict axis-specific β* patterns.

Most of the oracle gain is genuinely axis-specific information (likely
semantic-content of each PC in the context of the axis's meaning). The ~13%
that is captured by simple rules is the "easy" structural part (ablate PCs where
low c² coincides with high m_cos²).

### Recommendations (label-free workflow)

1. Compute ‖m‖/‖diff‖ per axis before any judging — axes > 1.5 are hard.
2. Use soft-K=4 whitening as the default metric.
3. If budget permits judge-scoring, coord ascent gives a robust ~+0.13 CV gain.
4. If exploring many axes cheaply, report raw ρ at slot 3 with GPT-4.1-mini
   descriptions+instructions; spot-check with response mode.

### Judge defaults

Judge model defaults: `claude-sonnet-4-20250514` with `--provider anthropic`
(the default), `gpt-4.1-mini` with `--provider openai`. Results cache under
`<output_dir>/scores_*.json` and resume on rerun; pass `--no_cache` to
rescore from scratch.

## Output layout

```
<output_dir>/
├── config.json                  # all resolved args + axis metadata
├── scores_descriptions.json     # {name: int score in [-3, 3]}
├── scores_instructions.json     # {name: int score in [-3, 3]}
├── scores_responses.json        # {name: {mean_score, n_scored, n_total}}
├── projections.json             # {slot: {name: {raw, whitened}}}
├── correlations.json            # {mode: {slot: {raw|whitened: {rho, p, n}}}}
└── correlation_plot.png         # scatter grid (rows=modes, cols=slot×metric)
```
