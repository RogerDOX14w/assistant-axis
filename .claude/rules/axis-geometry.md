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

### Vector and axis dtypes: bf16 in May, float32 from October (2026-10-12)

Pipeline steps 4 and 5 store **float32** since 2026-10-12 (walk-through
P3; review P4 D1 / P5 #19): step 4 averages each entity's activations in
float64, one at a time, and stores the vector as float32 (~10.5 MB for
`(8, 64, 5120)`); step 5 averages the vectors in float64 and stores
`axis.pt` as float32.  Step 2's activations stay bf16 (their span mean
already accumulates in float32 and rounds once; float32 activations would
double 2.6 GB per entity for little gain).  **Every May 2026 vector and
axis (the 8slot tree) is bf16**; vectors and axes record `vector_dtype` /
`axis_dtype` and `accumulation` in their `inputs` from October on, and May
files have no such record.  What the change buys: the bf16 axis was off
from a float32 recomputation of the same vectors by 1.3-1.5% median, up to
6.3% (cosine >= 0.998), mostly from rounding the role mean before the
difference of two close means; the stored per-entity bf16 mean was off by
~0.2%.  Analyses that load vectors cast them to float32 themselves (so only
the stored ~0.2% entered them); steering casts the loaded axis to the
model's dtype (`steering/run_sweep.py` `_axis_vector_for_model`), so a
float32 axis steers a bf16 model as before.  A tree mixing the two dtypes
is averaged correctly but step 5 warns: it mixes two extractions.

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
parabola fit done before soft-shear was in the toolbox).  The one
exception: `OPTIMAL_AXIS_SOFT_K = 3`, beside it in
[`whitening.py`](./results_analysis/canonical_angles/whitening.py), is
what [`optimal_axis_for_judge.py`](./results_analysis/optimal_axis_for_judge.py)'s
recorded runs used, and that script keeps it (2026-10-12, walk-through
D6).

`DEFAULT_SOFT_SHEAR_L=3` (and `DEFAULT_WHITENING_SPEC="soft_shear=3"`)
were bumped from `L=2` / `"soft_shear=2"` on May 11 2026 after the
35-axis di-cohort `shear_l_sweep` at slots 3 / 6 / 7 with the new
cohort-mean blended-curve overlay
(`results_analysis.shear_l_sweep` + `judge_score_combine.cohort_mean_curves`,
0.80·rs + 0.20·di per axis, 5x cross-axis weight on primary axes).
Per-axis paired t-tests over 35 axes (on the **desc+inst** series,
GPT+Sonnet 4-way mean — the response series covered only 12 of the
35 axes then; clarified 2026-10-12, when the table below was
reproduced exactly from the desc+inst records and not from any
response series, so the decision does not depend on the response
source; under today's GPT+Haiku blend the 33 response axes show the
same shape: slot 6 and 7 L=3→L=4 cliffs at p ≤ 0.002, slot 3 tied)
show:

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

**The table's record (2026-10-13, the rho-plot pass of the code review,
e940a300).**  The slot-6 row (p 0.019 / 0.29 / 0.0006) was drawn before the
May 35-axis di shear file
[shear_l_sweep_di_slot6.json](./roger/axis_judge_experiments/shear_l_sweep_di_slot6.json)
was last rewritten (2026-05-12T01:12Z, after the slot 3 and 7 runs); the file
as frozen gives 0.017 / 0.32 / 0.0005, and the slot 3 and 7 files reproduce
the table's p-values to its digits.  The May di shear and K sweeps
(`shear_l_sweep_di_slot{3,6,7}.json`, `whitening_k_sweep_di_slot{3,6,7}.json`
and their plots) are `frozen_snapshot` entries in
[deferred_rejudges.yaml](./deferred_rejudges.yaml) since 2026-10-13: a rerun
cannot reproduce them, because the GPT/Sonnet di weight went 0.50 → 0.625 and
the combiner gained the one-side-missing fallback on 2026-05-12/13 with no flag
for either.  A rerun on today's code moves desc+inst ρ by at most 0.026 per
axis and leaves the L=3 conclusions unchanged; the one movement worth knowing
is that slot 3's L3→L4 cliff goes from p 0.051 to 0.034.  Details: rows RH2
and RH3 of
[regeneration_list.md](./reports/code_review_2026-10-12/regeneration_list.md).

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
  in [`winner_decomposition.py`](results_analysis/pc_round_trip/winner_decomposition.py);
  corrected 2026-10-12).
  Opus narrates that direction; the judge rubric is that description.
- A *cell* is a `(slot, layer)` pair.  The sweep's seven, in the order
  the aggregates use (`cell_order` in the cache), are (7, 25) the
  canonical cell, (7, 49), (6, 25), (6, 49), (0, 26), (0, 49), (3, 25).
  An *n-cell aggregate* is the best ρ over the first n of them; a
  *trace* is that number as a function of N, averaged over the two
  description styles (glossary, inline).
- `nth_pc` variant: at each cell `(slot, layer, L, K)`, recompute PCA
  on the post-shear/whitened entity matrix and take the index-N
  singular vector.  Direction is free to "float" with `(L, K)`.  Under
  the May 6 grid the K winners clustered near `K≈N` (the grid was
  `DEFAULT_K_COARSE ∪ N±4`); the K-near-N expansion was removed on
  2026-05-06 and the grid has been L ∈ {0, 1, 2, 4}, K ∈ {0, 1, 2, 4}
  since.  Since 2026-10-12 (walk-through D1)
  [`klm_sweep.py`](results_analysis/pc_round_trip/klm_sweep.py)
  records every cell's winner, not only the global one.
- `fixed_principled` variant: take α = `U_canonical[:, N-1] / σ_{N-1}`
  (the entity weights that define canonical PC N) and reapply those
  weights at the target cell's centred entity matrix
  (`principled_directions_in_raw` in
  [`permutation_null.py`](results_analysis/pc_round_trip/permutation_null.py)).
  The transported object is the same *linear combination of entities*
  across cells, modulo cell-local geometric drift.  At the canonical
  cell with `L = K = 0` it is the canonical direction; elsewhere it is
  not.  Naive `fixed_same` (reuse the raw ℝ^D vector) was abandoned
  because slot changes make it nearly orthogonal to the principled map.
  Its per-cell winners are written by
  [`plot_direction_cosines.py`](results_analysis/pc_round_trip/plot_direction_cosines.py)
  `--include_optimization`
  ([`...fixed_principled_per_cell_winners_7-25_...json`](roger/pc_round_trip_fixed_principled_per_cell_winners_7-25_7-49_6-25_6-49_0-26_0-49_3-25.json),
  May 9, same cells and grid), not by
  [`klm_sweep.py`](results_analysis/pc_round_trip/klm_sweep.py).
- `permutation_null`: same search machinery on randomly permuted judge
  scores, giving the ρ that `(L, K, cell)` optimisation reaches on
  noise; its 95th percentile is "the floor" below.  The May 6 null was
  `nth_pc`; the current one
  ([`pc_round_trip_null_klm_results.json`](roger/pc_round_trip_null_klm_results.json),
  May 9, `_meta.variant`) is **`fixed_principled`** on the 7 cells and
  the K ≤ 4 grid, 100 permutations: 95th percentile 0.07–0.10 for the
  canonical cell alone, 0.08–0.12 for the 6- and 7-cell aggregates.
  So the `fixed_principled` aggregate is benchmarked against its own
  matched null, and it is `nth_pc` that has none (same grid size, so
  the floors should be close; not verified).  The sentence that stood
  here until 2026-10-12, "computed only for the `nth_pc` variant", was
  true of the May 6 null only.

**Core empirical read (revised 2026-10-12, twice; the earlier readings
are kept below as history).**

The `nth_pc` winner-decomposition heatmap (built by
[`winner_decomposition.py`](results_analysis/pc_round_trip/winner_decomposition.py)
and [`plot_winner_decomposition.py`](results_analysis/pc_round_trip/plot_winner_decomposition.py))
maps each `nth_pc` winner direction back into the canonical cell
(inverse whiten/shear at the winner's cell → least-squares entity
weights on that cell's raw matrix → the same weights on the canonical
raw matrix → canonical shear) and expresses its squared mass on each
canonical PC (rows = canonical PC index k, columns = target index N,
column-normalised).  "Mass on PC N" below is the entry at k = N; a
winner that is canonical PC N has 1.0 there.  Four versions exist, and
they do not say the same thing:

- **May 6, 4-slot canonical (slot 3, L=2), K-near-N grid**
  ([`...png.bak.20260506_4slot_canonical`](roger/pc_round_trip_nth_pc_winner_decomposition.png.bak.20260506_4slot_canonical),
  data in the [`.npz.bak`](roger/pc_round_trip_nth_pc_winner_decomposition.npz.bak.20260506_4slot_canonical)
  beside it): built from the nth_pc per-cell
  winners of the 3-cell sweep.  For N ≲ 12 broadly diagonal (mass on
  PC N 0.85–1.0 at N ≤ 4); for N ≥ 16 the mass on PC N is 0.000 and
  0.7–0.94 of it sits on canonical PCs 1–8, whatever N was searched
  for.  Every high-N winner there has K ≈ N (28 for N=16, 132 for
  N=128): inverse-whitening with K ≈ N multiplies a direction's
  components on the top-K canonical directions by their standard
  deviations, largest for the low PCs, so the mass lands on PCs 1–8
  almost regardless of the direction.  *This is the figure the May
  reading was drawn from, and the reading was right for that grid.*
- **May 9, 8-slot, 7 cells**, now
  [`...png.bak.20260509_fixed_principled_winners`](roger/pc_round_trip_nth_pc_winner_decomposition.png.bak.20260509_fixed_principled_winners)
  (data in the [`.npz.bak`](roger/pc_round_trip_nth_pc_winner_decomposition.npz.bak.20260509_fixed_principled_winners)
  beside it; it was the un-suffixed file, the
  one this section cited, until the regeneration below replaced it):
  **not built from nth_pc winners.**  The script's default input had become the
  `fixed_principled` per-cell winners file, so each column is PC N *at
  a configuration chosen by a different search*, and its title
  ("nth_pc winner", "L=2") was wrong on both counts (code review of
  2026-10-12).  Read for what it is, it shows heavy mass on PCs 1–3 for
  N ≤ 16 (those configurations sit at K = 2–4) and, for larger N, a
  faint top band (~0.05) over a thin diagonal; no collapse onto the
  first eight.
- **2026-10-12 rebuild from the global nth_pc winners only**
  ([`...__true_nth_pc_global_winners_2026-10-12.png`](roger/pc_round_trip_nth_pc_winner_decomposition__true_nth_pc_global_winners_2026-10-12.png),
  data in the [`.npz`](roger/pc_round_trip_nth_pc_winner_decomposition__true_nth_pc_global_winners_2026-10-12.npz)
  beside it; the one global winner per (N, style)
  that the May 9 sweep cache recorded, now
  [`...json.bak.20261012_220548_may9_global_only`](roger/pc_round_trip_klm_results.json.bak.20261012_220548_may9_global_only)):
  a thin bright diagonal at every N it covers, and for every N ≥ 20 the
  mass on PCs 1–8 is 0.00–0.28, median 0.02 (18 columns).  Incomplete:
  [`winner_decomposition.py`](results_analysis/pc_round_trip/winner_decomposition.py)
  then skipped winners at slots 0 and 3 and
  at (6, 49), so 20 of 48 columns are blank (N = 1, 12, 16, 32, 56, 80,
  192 entirely).  **Superseded** the same day by the regeneration
  below: where both have a column they agree in 23 of 28, and the other
  five are winners that moved to another cell when the sweep was rerun
  after the review-9a loader fix (34 of 48 global winners keep their
  configuration; the largest ρ change is 0.017).
- **2026-10-12 regeneration from per-cell nth_pc winners — the current
  figure**
  ([`pc_round_trip_nth_pc_winner_decomposition.png`](roger/pc_round_trip_nth_pc_winner_decomposition.png),
  data in the [`.npz`](roger/pc_round_trip_nth_pc_winner_decomposition.npz)
  beside it, from
  [`pc_round_trip_klm_results.json`](roger/pc_round_trip_klm_results.json);
  walk-through D1 in
  [`escalations.md`](reports/code_review_2026-10-12/escalations.md),
  commit 7e0c18b8).
  [`klm_sweep.py`](results_analysis/pc_round_trip/klm_sweep.py)
  now records every
  cell's nth_pc winner, the decomposition covers all 7 cells, and the
  columns are the n = 1, 2, 4, 6, 7-cell aggregates (n = 7 is the
  global winner).  Title: "nth_pc search winners decomposed in the
  canonical PC basis (slot 7, layer 25, L=0 raw)".  **Where the winner
  sits decides the column, not N.**  At the canonical cell (n = 1; 36
  columns at N ≥ 12) the winner is canonical PC N or its near
  neighbours: mass on PC N median 0.97, ≥ 0.5 in 30 of 36, and ≥ 0.75
  within N ± 25% in every column (the six below 0.5 on PC N itself,
  at N = 20, 32, 128, 192, have L or K > 0); mass on PCs 1–8 median
  0.00, at most 0.22.  With the global winner (n = 7), 24 of those 36
  sit at another cell, 11 of them at (0, 26); those have at most 0.28
  on PC N and 0–0.56 on PCs 1–8 (median 0.18 over all 36).  The step
  the figure shows at N = 8 → 12 is the global winner moving from
  (7, 25) to (0, 26): mass on PC N 1.00 → 0.00.  That off-diagonal
  mass is what the mapping does to *any* direction from another cell,
  not something the search adds: plain PC N of each cell (L = K = 0, no
  search) mapped the same way lands at median 0.005 (at most 0.41, at
  N = 12–16) on canonical PC N for N ≥ 8 at the six non-canonical
  cells, and from the slot-0 cells puts 0.2–0.45 on PCs 1–8 for N up
  to 64; a winner's PCs 1–8 mass minus that of plain PC N at the same
  cell has median +0.00 (range −0.14 to +0.23).  No collapse at any N
  on the K ≤ 4 grid.  (The plain-PC-N control was computed in the D1
  session and is not on disk: 24 PCs × 7 cells through
  `winner_direction_in_canonical_L2(pc, slot, layer, 0, 0, ...)`,
  about 45 s.)

Why the pictures differ: the K-near-N expansion of the nth_pc K grid
was removed on 2026-05-06
([`klm_sweep.py`](results_analysis/pc_round_trip/klm_sweep.py), after this synthesis was
written), so the May 9 and later nth_pc sweeps could only choose K ≤ 4
— and did (stage-2 global winners: K = 0 for 29 of 48, none above 4).
With it went the inflated high-N `nth_pc` ρ (7-cell trace): 0.90 at
N = 1, 0.67 at N = 8, then 0.21 (N = 20), 0.11 (N = 32), 0.07
(N = 128), 0.03 (N = 512) — the floor the canonical-cell traces reach
by N ≈ 28–32.  The 6-cell `fixed_principled` aggregate does not reach
it (next paragraph; until 2026-10-12 this sentence said it was
"already at" the floor, which is true of the canonical cell only).  The
May spot-checks still stand as a description of that grid: low-index
canonical PCs had non-trivial Spearman ρ against high-N judge-score
vectors.

**The ~12 boundary, re-read from the ρ traces (2026-10-12).**  Between
N = 8 and N = 12 every trace steps down: canonical PC N at the
canonical cell with no search 0.68 → 0.19 (the × line of
[`pc_round_trip_direction_cosines_fixed.png`](roger/pc_round_trip_direction_cosines_fixed.png));
`nth_pc` at the canonical cell only 0.67 → 0.19; `nth_pc` over all 7
cells 0.67 → 0.36; `fixed_principled` over 6 cells 0.73 → 0.44.  It is
a fall in how well the descriptions are recovered, not a change in
what the search finds: the canonical-cell winner stays on PC N past it.
Past the step the traces part company.  The canonical-cell traces sit
at 0.2–0.3 for N = 12–24, then at the floor from N ≈ 28–32 (`nth_pc`
at the canonical cell 0.10 at 28, 0.07 at 32; no search 0.09 at 28,
0.02 at 32), with excursions to 0.2–0.25 at N = 36–40 and 56.  The
7-cell `nth_pc` trace stays at 0.10–0.25 for N = 20–56 and is at the
floor from N = 64 (0.09, then ≤ 0.08).  The 6-cell `fixed_principled`
aggregate never gets there: 0.14–0.50 for N ≥ 12 (0.14 only at N = 32,
otherwise ≥ 0.22; 0.29 at N = 128, 0.36 at N = 512) against its own
null's 0.08–0.12 — the red ◆ line of the legacy figure
[`pc_round_trip_direction_cosines_fixed_with_optimization.png`](roger/pc_round_trip_direction_cosines_fixed_with_optimization.png).
Its winners at N ≥ 12 are at (6, 25), (6, 49) or (7, 49) in 29 of 36
columns, at a slot-0 cell in 6, at the canonical cell in 1, with K = 0
in 26.  Two things on disk say this elevation is not PC-N recovery:
`fixed_principled` at the canonical cell alone (L and K searched)
falls like the other canonical-cell traces (0.24 at N = 12, 0.05 at
32, 0.07 at 128, −0.01 at 256); and the transported PC N at a single
other cell with no search at all (the pale lines of the default
figure) already reaches ρ of *either sign* up to about ±0.4 at N ≥ 12
(about −0.35 at N = 16, +0.46 at N = 20, −0.41 at N = 96, read off the
figure), where a direction carrying PC-N content would be positive or
zero at every cell.  The aggregate is the positive tail of that scatter
plus the (L, K) search.  The likely mechanism, **unchecked**: the
entity scores along a transported direction are `M_t M_tᵀ α`, which
weights the target cell's PCs by their σ², so a small drift component
of α on a top PC of that cell outweighs the PC-N component by about
σ₁²/σ_N² at high N; and the May spot-checks found the top PCs
correlated with the judge rankings of high-N descriptions anyway.
Two checks would settle it, neither done: decompose each
`fixed_principled` winner's entity-score vector in the winning cell's
own PC basis (expect most of it on PCs 1–3), and score the
`fixed_principled` search for PC N against the judge scores of other
PCs M ≠ N (expect the same 0.2–0.5 if it is scaffolding).

*May 2026 reading, for the record (true of the May 6 figure):* for
small N (roughly N ≲ 12) the heatmap is broadly diagonal, the recovered
direction at index N really does live near canonical PC N; for larger
N it goes strongly off-diagonal, most squared mass on the first ~8
canonical PCs regardless of which N was being searched for.  *Earlier
2026-10-12 reading (commit 2e2f1a25, from the rebuild above):* no
collapse on the K ≤ 4 grid, and "both traces are at the floor" by
N ≈ 12 — the second half held for the canonical cell only.

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
| `nth_pc` ρ | (a) + (b); the search picks whichever latent best predicts judges. | Under the K-near-N grid (May 6): stayed high, and the heatmap showed the chosen direction loading on canonical PCs 1–8 — high ρ via canonical-PC aliasing, not genuine PC-N recovery.  Under the K ≤ 4 grid (since 2026-05-06): at the canonical cell it falls to the floor by N ≈ 28–32 and its winner stays on PC N; over 7 cells it is 0.10–0.25 to N = 56 (a winner at another cell, which maps off-diagonal) and at the floor from 64. |
| `fixed_principled` ρ | At the canonical cell, (a): the direction is pinned to PC N's α-weights and only `(L, K)` varies.  At another cell the pin does not hold in canonical-PC terms (transport drift, above), and a multi-cell aggregate is a max over drifted directions. | At the canonical cell: falls to the floor by N ≈ 28–32, like the no-search trace.  The 6-cell aggregate stays at 0.14–0.50 to N = 512, with the winner at another cell in 35 of 36 columns at N ≥ 12: read as top-PC pickup by transport until checked, not as PC-N recovery.  (The May caricature, "falls toward the noise floor", is true of the canonical cell only.) |

Neither is "the right ρ"; they answer different questions.
`fixed_principled` at the canonical cell upper-bounds how much of PC N
is genuinely articulable in description-language; `nth_pc` upper-bounds
what the search procedure can recover from the same descriptions when
allowed to drift onto any latent that predicts judges; a multi-cell
`fixed_principled` aggregate is a third thing, a search over
transported directions, and no longer a bound on PC-N content.

**Regime heuristic (informal, continuity not proven; rewritten
2026-10-12).**

- N ≤ 8: every trace is high (0.58–0.90 against a floor of about 0.1)
  and the `nth_pc` winner is canonical PC N: mass 0.89–1.0 on PC N at
  the canonical cell (the one exception, N = 2 inline, is a reindexing:
  its K = 1 winner shrinks canonical PC 1 below PC 2, so the "second"
  PC of the whitened matrix is canonical PC 1, 0.88 of the mass), and
  still 0.66–0.95 when the global winner sits at another cell, since
  transport keeps the low PCs.  Treat "the Nth PC" as a latent the
  description language can pick out.
- The boundary is the step between N = 8 and N = 12 in every trace
  (numbers above).  It is a fall in recovery, not a change in what the
  search finds.
- N ≳ 12: trust the canonical-cell traces — canonical PC N with no
  search, `nth_pc` at the canonical cell, `fixed_principled` at the
  canonical cell — which sit at 0.2–0.3 to N = 24 and at the floor
  from N ≈ 28–32.  Treat a multi-cell gain above them as a different
  direction (an off-canonical PC, or top-PC pickup by transport), not
  PC-N recovery, until the two checks above are done.  **This reverses
  the May rule's application**: the trace it named as the one to trust
  at high N, the multi-cell `fixed_principled` aggregate, is now the
  one that reads high for a reason other than PC-N content.  The
  rule's reason — count no ρ that comes from a direction other than
  PC N — is unchanged and is what reverses it; the May rule was right
  under the K-near-N grid, where `nth_pc` was the misleading trace.
  The decomposition heatmap is a sanity check again (2026-10-12): read
  it with the winner's cell in view, since a winner at another cell
  maps off-diagonal whatever it is.

**Geometry side note.**

[`principled_layer_transport.py`](results_analysis/pc_round_trip/principled_layer_transport.py)
compares naive vs principled cross-cell transport.  Layer ±1 at fixed
slot drifts modestly; changing slot at fixed layer drifts a lot.
Slot, not layer, dominates inter-cell direction drift, which is why
the principled (α-weight) transport matters once the cell set spans
multiple slots.

**Operational caveat tied to methodology (updated 2026-10-12).**

The null band in the round-trip plots has been the `fixed_principled`
search's own floor since May 9 (setup recap above), so the multi-cell
`fixed_principled` aggregate is honestly benchmarked and still sits
well above it; what that shows is that its ρ is not noise, not that
the direction is PC N.  `nth_pc` has no matched null; its traces are
compared with the `fixed_principled` floor on the same grid.  Compare
any optimised trace with the canonical-cell no-search trace first.
(Until 2026-10-12 this paragraph said the opposite, that the null was
`nth_pc`'s; that was true of the May 6 null.)

**Plot status (2026-05-06; updated 2026-10-12).**
[`plot_direction_cosines.py`](results_analysis/pc_round_trip/plot_direction_cosines.py)
was restricted to `fixed_principled`-only after this synthesis, and
since May 9 its default view is canonical-only
([`pc_round_trip_direction_cosines_fixed.png`](roger/pc_round_trip_direction_cosines_fixed.png):
canonical PC N at the canonical cell as ×, the same PC transported to
the five other cells at L = K = 0 as pale lines, the shuffled-judge
null at L = K = 0 as the pink band).  The optimised 6-cell ◆ view is
deprecated and kept behind `--include_optimization`
([`..._with_optimization.png`](roger/pc_round_trip_direction_cosines_fixed_with_optimization.png));
the script's own comment from May gives the reason this section only
caught up with on 2026-10-12: at high N the search "surfaces
correlations that match the judge description but are not actually
aligned with the original canonical PC direction".  `nth_pc` remains
in the upstream `klm_sweep` cache (per cell since D1) and the heatmap
script; those tools are kept for the diagnosis described above but do
not drive the headline plot.
