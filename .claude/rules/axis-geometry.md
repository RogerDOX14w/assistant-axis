---
paths:
- assistant_axis/axis.py
- assistant_axis/pca.py
- pipeline/4_vectors.py
- pipeline/5_axis.py
- results_analysis/axis_cosine_seriation.py
- results_analysis/canonical_angles/**
- results_analysis/pc_round_trip/**
---
<!-- GENERATED FILE: do not edit.  Source: AGENT_NOTES.md (section markers).  Regenerate with: uv run python tools/sync_agent_notes.py -->
# Rule: axis-geometry

**When:** computing axes, whitening or soft-shear, PCA round-trips, or axis cosine analyses.  Loads automatically for files matching the `paths` above.  Source: the sections of [`AGENT_NOTES.md`](AGENT_NOTES.md) marked `rule=axis-geometry`; edit there, then run `uv run python tools/sync_agent_notes.py`.

### Whitening / soft-shear defaults

**Scope (read this first).**  These defaults apply to **analysis-side
scripts** — ρ judging, `rho_by_layer`, `whitening_k_sweep`,
`gpt_sonnet_weight_sweep`, the canonical-angles pipeline, etc. —
where whitening sharpens the score↔projection correlation by
normalising the activation manifold.  **Steering work is always done
in raw model-activation space** (see *"Steering judges (Phase-2
architecture)"* above): `ActivationSteering` and `run_sweep.py`
consume the unwhitened `axis.pt` directly, and the transforms below
do NOT pass through to the steering side.  Don't apply them to
steering vectors.  (Same reason `pc_round_trip/launch_judge_runs.py`
keeps its own `DEFAULT_SHEAR_L=0` — see the caveat at the end of
this section for that specific case.)

For analyses going forward, the project defaults are:

| regime | default | constant |
|---|---|---|
| **soft-K whitening** | **K=2** | `results_analysis.canonical_angles.whitening.DEFAULT_SOFT_K` |
| **soft-shear (top-L pooled)** | **L=3** | `results_analysis.canonical_angles.whitening.DEFAULT_SOFT_SHEAR_L` |
| **primary recommended whitening regime** | **`soft_shear=3`** | `results_analysis.canonical_angles.whitening.DEFAULT_WHITENING_SPEC` |

`DEFAULT_SOFT_K=2` was set in Apr 2026 after the LKM grid sweep on the
33 desc+inst + 12 response = 45-axis set with the inst-tiebreak
weighting (prior hardcoded default was K=3, from the older K-sweep
parabola fit done before soft-shear was in the toolbox).

`DEFAULT_SOFT_SHEAR_L=3` (and `DEFAULT_WHITENING_SPEC="soft_shear=3"`)
were bumped from `L=2` / `"soft_shear=2"` on May 11 2026 after the
35-axis di-cohort `shear_l_sweep` at slots 3 / 6 / 7 with the new
cohort-mean blended-curve overlay
(`results_analysis.shear_l_sweep` + `judge_score_combine.cohort_mean_curves`,
0.80·rs + 0.20·di per axis, 5x cross-axis weight on primary axes).
Per-axis paired t-tests over 35 axes show:

| slot | L=1 vs L=2 | L=1 vs L=3 | L=3 vs L=4 |
|---|---|---|---|
| 3 | tied (p=0.37) | tied (p=0.54) | borderline (p=0.051) |
| 6 | **L=2 dip** (Δ=−0.017, p=0.019) | tied (p=0.29) | **cliff** (Δ=−0.023, p=0.0006) |
| 7 | tied (p=0.68) | tied (p=0.92) | **cliff** (Δ=−0.020, p=0.0004) |

L=3 is at-or-above the optimum on every slot, never significantly
worse than L=1, and the universally-significant harm transition is
L=3 → L=4 across all three slots — so L=3 is the highest "safe"
shear depth with no significant ρ harm anywhere.  Tied with L=1 on
ρ at most slots; goal/no-goal subspace cleanliness (more top-aligned
canonical-angle pairs orthogonalised) is the tie-breaker that picks
L=3 over L=1.

Use the constants instead of literal integers in CLI defaults::

    from results_analysis.canonical_angles.whitening import DEFAULT_SOFT_K
    p.add_argument("--whiten_K", type=int, default=DEFAULT_SOFT_K)

When fitting:

```python
from results_analysis.canonical_angles.whitening import (
    DEFAULT_SOFT_K, DEFAULT_SOFT_SHEAR_L, fit_shear, fit_whitening,
)
from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces

# Primary: soft-shear at L=3, fitted on combined r+t goal/no-goal subspaces.
A_g, A_n = build_goal_nogoal_subspaces(data_dir, slot, layer, kind="combined")
shear = fit_shear(A_g, A_n, L=DEFAULT_SOFT_SHEAR_L)
M_done = shear.apply(M_raw)

# Alternative when shear isn't available: soft-K whitening at K=2.
basis = fit_whitening("soft_K", pool, K=DEFAULT_SOFT_K)
M_done = basis.apply(M_raw)
```

**Caveats**:

- The optimum varies by slot: slot 3 has a broad L=1..L=5 plateau,
  slot 6 has a real L=2 dip but L=1 ≈ L=3, slot 7 has L=1 ≈ L=2 ≈ L=3.
  L=3 is defensible at all three; bespoke per-slot tuning could
  squeeze ~0.005 ρ at slot 7 by picking L=1 instead.
- The L=3 → L=4 cliff is sharp and universal -- do **not** bump
  `DEFAULT_SOFT_SHEAR_L` above 3 without re-running the cohort-mean
  paired-t analysis.
- `pc_round_trip/launch_judge_runs.py` has a separate
  `DEFAULT_SHEAR_L=0` (raw) that is *intentionally* not tied to this
  constant -- the pc_round_trip canonical experiment runs raw on
  purpose.  See the comment block at that constant for the rationale.

**Cache hygiene**: when changing these defaults, flush `rho_by_layer.json`
(the only auto-loading cache that interleaves K values across runs).
Per-axis `correlations.json` files are tied to specific
``--whiten_K`` invocations and should NOT be deleted -- they belong to
historical runs and re-running them is expensive.

### Axis-geometry tool: `axis_cosine_seriation.py`

Pairwise `|cos|` heatmap of every axis in the chosen pair-list cohort,
reordered by **optimal leaf ordering** (`scipy.cluster.hierarchy.
optimal_leaf_ordering`, Bar-Joseph 2001) on the `(1 − |cos|)`-distance
dendrogram so semantically-related axes sit adjacent and clusters
land block-diagonal.  Promoted from a one-off May 2026 geometry
exploration; full operational docs in
[`results_analysis/README.md`](results_analysis/README.md#axis_cosine_seriationpy).

When to use:

* **Sanity-checking a new cohort** — does any pair land on top of an
  existing axis?  Seriation pushes near-duplicates to immediate
  neighbours where they're easy to spot.
* **Comparing the raw and L=3 soft-sheared frames** — the script
  takes ``--L 0`` for raw and ``--L 3`` (default) for canonical;
  same cohort run both ways gives the "does whitening tighten or
  create clusters?" picture.  On the clean 60-pair cohort the
  honest answer is "tightens by ~10 % mean |cos| (0.245 → 0.222)
  but doesn't manufacture new structure" — consistent with the
  whitening-as-sharpener story above.  **Stronger evidence**: with
  the hand-curated 8-block semantic ontology turned on (default),
  the OLO seriation on the L=3 frame recovers the ontology
  **exactly** (8 runs / 8 blocks / 0 splits) while the raw frame
  fragments it into **21 runs / 8 blocks / 7 splits**.  Whitening
  is aligning the data-driven geometry with the human ontology by
  attenuating the dominant goal/non-goal direction that otherwise
  dominates the cosine structure.
* **Picking new traits to add** — the brightest off-diagonal blocks
  in the canonical frame mark dense regions of the axis space where
  *additional* traits won't add effective dimensionality.  Pair
  with the PCA-of-entity-pool / yield analysis from
  [`data/traits/instructions/TRAITS_ADDED.md`](data/traits/instructions/TRAITS_ADDED.md)
  (§ "Strategy 1b") for the full "which direction is empty?" picture.

JSON sidecar carries the OLO leaf order plus cluster memberships at
five thresholds (0.7 / 0.6 / 0.5 / 0.4 / 0.3) for downstream
consumption.  Provenance envelope and PNG `Inputs` chunk are
populated -- registered in the writer-side audit list above.

---

### PC round-trip experiment: findings synthesis (May 2026)

**Goal.** Test how faithfully human-interpretable axes written for
canonical PCA directions (Opus describes the axis, GPT/Sonnet rank
entities along it) get geometrically recovered by an `(L, K, M)`
search over whitened PCs at various `(slot, layer)` cells.

**Setup recap.**

- *Canonical Nth PC* is defined in a fixed reference geometry: slot 3,
  layer 25, soft-shear `L=2`, PCA on standardized entity embeddings
  (as of May 6; since the 8-slot migration of May 9 the canonical cell
  is slot 7, layer 25, `L=0` raw — `SLOT_C`, `LAYER_C`, `CANONICAL_L`
  in `winner_decomposition.py`; corrected 2026-10-12).
  Opus narrates that direction; the judge rubric is that description.
- `nth_pc` variant: at each cell `(slot, layer, L, K)`, recompute PCA
  on the post-shear/whitened entity matrix and take the index-N
  singular vector.  Direction is free to "float" with `(L, K)`; the
  empirical K-winner pattern clusters near `K≈N` (which is why the
  search grid is `DEFAULT_K_COARSE ∪ N±4`).
- `fixed_principled` variant: take α = `U_canonical[:, N-1] / σ_{N-1}`
  (the entity weights that define canonical PC N) and reapply those
  weights at the target cell's centred entity matrix.  The transported
  object is the same *linear combination of entities* across cells,
  modulo cell-local geometric drift.  At the canonical cell with
  `L=2, K=0` it reduces to the canonical direction; elsewhere it
  doesn't.  Naive `fixed_same` (reuse the raw ℝ^D vector) was
  abandoned because slot changes make it nearly orthogonal to the
  principled map.
- `permutation_null`: same search machinery on randomly permuted judge
  scores, giving the ρ that `(L, K)` optimisation reaches on noise.
  Currently computed only for the `nth_pc` variant; see the
  variant-specific-K-grids TODO above for why this is awkward to
  benchmark `fixed_principled` against.

**Core empirical read (revised 2026-10-12; the May reading is kept
below as history).**

The `nth_pc` winner-decomposition heatmap (built by
[`winner_decomposition.py`](results_analysis/pc_round_trip/winner_decomposition.py)
and [`plot_winner_decomposition.py`](results_analysis/pc_round_trip/plot_winner_decomposition.py))
maps each `nth_pc` winner direction back into canonical shear space and
expresses its squared mass on each canonical PC (rows = canonical PC
index k, columns = target index N, column-normalised).  Three versions
exist, and they do not say the same thing:

- **May 6, 4-slot canonical (slot 3, L=2), K-near-N grid**
  ([`...png.bak.20260506_4slot_canonical`](roger/pc_round_trip_nth_pc_winner_decomposition.png.bak.20260506_4slot_canonical),
  data in the `.npz.bak` beside it): built from the nth_pc per-cell
  winners of the 3-cell sweep.  For N ≲ 12 broadly diagonal (mass on
  PC N 0.85–1.0 at N ≤ 4); for N ≥ 16 the mass on PC N is 0.000 and
  0.7–0.94 of it sits on canonical PCs 1–8, whatever N was searched
  for.  Every high-N winner there has K ≈ N (28 for N=16, 132 for
  N=128): inverse-whitening with K ≈ N multiplies a direction's
  components on the top-K canonical directions by their standard
  deviations, largest for the low PCs, so the mass lands on PCs 1–8
  almost regardless of the direction.  *This is the figure the May
  reading was drawn from, and the reading was right for that grid.*
- **May 9, 8-slot, 7 cells**
  ([`pc_round_trip_nth_pc_winner_decomposition.png`](roger/pc_round_trip_nth_pc_winner_decomposition.png)),
  the file this section cited until 2026-10-12: **not built from nth_pc
  winners.**  The script's default input had become the
  `fixed_principled` per-cell winners file, so each column is PC N *at
  a configuration chosen by a different search*, and its title
  ("nth_pc winner", "L=2") was wrong on both counts (code review of
  2026-10-12).  Read for what it is, it shows heavy mass on PCs 1–3 for
  N ≤ 16 (those configurations sit at K = 2–4) and, for larger N, a
  faint top band (~0.05) over a thin diagonal; no collapse onto the
  first eight.
- **2026-10-12 rebuild from the true nth_pc winners**
  ([`...__true_nth_pc_global_winners_2026-10-12.png`](roger/pc_round_trip_nth_pc_winner_decomposition__true_nth_pc_global_winners_2026-10-12.png),
  data in the `.npz` beside it; the one global winner per (N, style)
  that [`pc_round_trip_klm_results.json`](roger/pc_round_trip_klm_results.json)
  records): a thin bright diagonal at every N it covers (mass on PC N
  ≈ 1.0 at N = 2–8, 24, 36, 40, 48, 96, 256; the broad columns 20, 28,
  384, 512 spread within the top-N block), and for every N ≥ 20 the
  mass on PCs 1–8 is 0.00–0.28, median ≈ 0.01.  Incomplete: the sweep
  keeps only the global winner per N (not three cells), and
  `winner_decomposition.py` silently skips winners at slots 0 and 3 and
  at (6, 49), so N = 1, 12, 16, 32, 56, 80, 192 are blank.  Evidence,
  not a finished figure.

Why the pictures differ: the K-near-N expansion of the nth_pc K grid
was removed on 2026-05-06 (`klm_sweep.py`, after this synthesis was
written), so the May 9 nth_pc sweep could only choose K ≤ 4 — and did
(stage-2 winners: K = 0 for 26 of 48, none above 4).  With it went the
inflated high-N `nth_pc` ρ: 0.91 at N = 1, 0.70 at N = 8, then 0.22
(N = 20), 0.13 (N = 32), 0.05 (N = 128), 0.04 (N = 512) — the floor the
`fixed_principled` trace was already at.  The May spot-checks still
stand as a description of that grid: low-index canonical PCs had
non-trivial Spearman ρ against high-N judge-score vectors.

*May 2026 reading, for the record (true of the May 6 figure):* for
small N (roughly N ≲ 12) the heatmap is broadly diagonal, the recovered
direction at index N really does live near canonical PC N; for larger
N it goes strongly off-diagonal, most squared mass on the first ~8
canonical PCs regardless of which N was being searched for.

**Interpretation.**

An Opus description of canonical PC N can be split into roughly:
*(a)* a PC-N-specific signal — what's actually distinctive about PC N
that ends up in the prose — and *(b)* generic top-PC scaffolding
(length, hedging, bluntness, stance loudness, "helpfulness
temperature", and other dominant features articulable in any axis
description) which is correlated with the high-variance early
canonical PCs and shows up in the judge rankings of *almost any*
labelled axis.  Add some noise.

The two ρ-measurement variants probe different mixtures of these:

| Variant | What it sees | Empirical caricature at high N |
|---|---|---|
| `nth_pc` ρ | (a) + (b); the search picks whichever latent best predicts judges. | Under the K-near-N grid (May 6): stayed high, and the heatmap showed the chosen direction loading on canonical PCs 1–8 — high ρ via canonical-PC aliasing, not genuine PC-N recovery.  Under the K ≤ 4 grid (since 2026-05-06): falls to the floor with N like `fixed_principled`, and the rebuilt heatmap is diagonal. |
| `fixed_principled` ρ | Mostly (a): the direction is pinned to PC N's α-weights, only `(L, K)` varies. | Falls toward the noise floor with N — measures whatever PC-N-specific content remains in the rankings once aliasing is denied (on the current grid, at about the same N as `nth_pc`). |

Neither is "the right ρ"; they answer different questions.
`fixed_principled` upper-bounds how much of PC N is genuinely
articulable in description-language; `nth_pc` upper-bounds what the
search procedure can recover from the same descriptions when allowed
to drift onto any latent that predicts judges.

**Regime heuristic (informal, continuity not proven).**

- N ≲ ~12: `nth_pc`, `fixed_principled`, the decomposition heatmap
  and the face-valid description content all agree.  Treat "the Nth
  PC" as a latent the description language can pick out.
- N ≳ ~12: trust the `fixed_principled` trace.  The rule was derived
  under the K-near-N grid, where `nth_pc` ρ alone was misleading; on
  the current K ≤ 4 grid both traces are at the floor by here, so
  there is nothing to be misled by, and the rule stands as prudence
  with that provenance.  The decomposition heatmap no longer carries a
  finding (2026-10-12) and is not one of the sanity checks; the
  boundary itself (~8–12 on the current ρ traces) should be re-read
  from the ρ plot, not from the heatmap.

**Geometry side note.**

`results_analysis/pc_round_trip/principled_layer_transport.py`
compares naive vs principled cross-cell transport.  Layer ±1 at fixed
slot drifts modestly; changing slot at fixed layer drifts a lot.
Slot, not layer, dominates inter-cell direction drift, which is why
the principled (α-weight) transport matters once the cell set spans
multiple slots.

**Operational caveat tied to methodology.**

Until variant-specific K grids and nulls land (TODO above), the
permutation null in the round-trip plot reflects the `nth_pc` search
procedure's noise floor, not `fixed_principled`'s.  Compare
`fixed_principled` traces to *each other* and to canonical (no-opt)
ρ; treat the dashed null bands as an upper bound on noise rather than
a literal floor for `fixed_principled`.

**Plot status (2026-05-06).**
`results_analysis/pc_round_trip/plot_direction_cosines.py` was
restricted to `fixed_principled`-only after this synthesis: the
single-panel ρ figure shows canonical (×) plus `fixed_principled` ◆
traces for 1/2/3-cell aggregates with R/G/B colour-coding.  `nth_pc`
remains in the upstream `klm_sweep` cache and the heatmap script;
those tools are kept available for the diagnosis described above but
no longer drive the headline plot.
