# Results Analysis

Scripts that analyze outputs of the [`pipeline/`](../pipeline/) — vectors, scores,
responses, axes. Parallel in intent to [`data_analysis/`](../data_analysis/),
which _prepares_ the role/trait data for the pipeline.

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
   raw activation metric and a soft-K=128 PCA-whitened metric (whitener fit
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
  --layer 24 --whiten_K 128 --provider anthropic --all \
  --output_dir roger/axis_judge_angel_demon

# Manual axis from a saved axis.pt, scoring descriptions only
uv run python results_analysis/axis_judge_correlation.py \
  --axis_file "runpod_workspace/qwen/qwen-3-32b Roger/roles/axis.pt" \
  --neg_pole "mythical/unstructured entity" \
  --pos_pole "defined professional role with structured output" \
  --neg_examples demon,vampire,revenant,chimera \
  --pos_examples consultant,researcher,engineer,accountant,librarian \
  --data_dir "runpod_workspace/qwen/qwen-3-32b Roger" \
  --layer 24 --slot 1 --score_descriptions \
  --output_dir roger/axis_judge_pc1_roles
```

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
Default is ``--K 4 16`` (one column per K, plus a "raw" column at the
left -- a 4 x 3 grid; pass a single value for a 4 x 2 grid like the
original Apr 23 plot, or several for a wider K-sweep).  The whitening
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

Across the K=4 and K=16 columns the ``Δ R²`` shifts gradually from
``role+trait`` (a) into ``heuristic theat_offset`` (b): as whitening shrinks the
high-variance role / trait directions, the additive baseline explains
less of the combo variance and the constant theatricality offset
becomes proportionally more important.  The remainder also grows
modestly (mid-range PCs that the additive + theatricality model can't
capture get less attenuated by whitening than the role/trait
components do).

Slot 0 (body mean) does NOT show the same pattern -- the heuristic
shift is near zero (raw) or only weakly positive (whitened),
consistent with theatricality being absent from the body-mean
activation.  See `canonical_angles/README.md` for further discussion.

```bash
# Default (4 slots × 3 metrics: raw, K=4 wht, K=16 wht; layer 24,
# augmented pool)
uv run python results_analysis/variance_decomposition.py \
    --output roger/variance_decomp_bars.png

# Single-K column (4 x 2 grid; matches the original April 23 layout
# at K=128, modulo the augmented pool):
uv run python results_analysis/variance_decomposition.py \
    --K 128 --output /tmp/var_decomp_K128.png

# Wider K-sweep at a different layer
uv run python results_analysis/variance_decomposition.py \
    --layer 32 --K 4 8 16 64 \
    --output /tmp/var_decomp_l32_Ksweep.png
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
between judge scores and projections.  The `desc_inst` source averages
GPT and Sonnet × descriptions and instructions per entity (4-way mean);
the `responses` source merges GPT response-mode mean scores from the
roles + traits runs.

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
layer 24, and average across all axes in the pair list.  ``w = 0.5``
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
Sonnet-4 by default and use a **50/50 mix** when reducing to a single
score per entity.  Cost: ~6× a single-provider run for ~+0.019 ρ
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
``(slot, layer=24)`` and:

- **desc+inst** -- 33 axes, 4-way mean of
  ``{GPT_d, GPT_i, Son_d, Son_i}``;
- **responses** -- 12 axes, GPT-only mean over response-mode evals.

Output (to ``--experiment_dir``):

- ``rho_by_slot_and_K.png``

```bash
# Default: KS = [0, 1, 2, 3, 4, 5], 33 + 12 axis pair lists
uv run python results_analysis/rho_by_slot_and_K.py

# Custom K range
uv run python results_analysis/rho_by_slot_and_K.py --ks 0 2 4 8 16
```

Headline observations from the default run:

- **Slot 1 is the laggard at every K** for both sources
  (desc+inst ≈ 0.42–0.45, responses ≈ 0.38–0.45) -- the
  ``<|im_start|>`` token carries the least axis signal in raw
  *and* whitened form.
- **Slot 3 dominates at K=0** (desc+inst 0.595, responses 0.600)
  but **slot 0 catches up — and overtakes for responses — once
  any whitening is applied**: e.g. responses at K=2 is 0.641 at
  slot 0 vs 0.621 at slot 3.  Slot 0 is dragged down by a single
  dominant PC at raw (consistent with the theatricality direction
  identified in the canonical-angles work); shrinking just the
  top-1 PC closes most of the gap (slot 0 jumps +0.08 ρ on
  desc+inst and +0.09 on responses going K=0 → K=1, while slot 3
  only gains ~+0.02).
- Mild whitening (K ∈ {2, 3, 4}) gives a small but real bump
  over raw at slot 3 for both sources; the curves are otherwise
  flat across K, then erode at K ≥ 5 (most visible on responses
  slot 3 at K=5).

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
