#!/usr/bin/env python3
"""Compare fixed soft-shear L policies to the fixed K=1 winner.

Reuses the projection / scoring pipeline from
:mod:`results_analysis.whitening_k_sweep`, but swaps ``fit_whitening(
"soft_K", pool, K)`` for ``fit_shear(A_goal, A_nogoal, L)`` so we can
ask:

    Does picking a single L ∈ {0, 1, 2, 3} for *every* axis beat the
    current "K=1 for every axis" policy?

This is the same kind of "constant-K vs constant-L vs hand-tuned
mix" comparison done in :mod:`results_analysis.axis_pc_k_policy_rf`,
but along the *shear* axis of the regime family instead of the
soft-K whitening axis.  Compatible cohort: full 35-axis
``pair_list_di.json`` (12 primary + 23 desc+instr-only extras).

For each axis we compute per-source ρ (responses if available;
desc+instr otherwise) at each L value, then blend per the project
default (0.80 responses + 0.20 desc+instr) when responses are
available and use desc+instr alone for the extras cohort.  The
report prints both the unweighted cohort mean and the primary-5x
weighted mean (the "axis with response judging is worth 5x" view
introduced earlier in this thread).

To compare with K we read the cached
``whitening_k_sweep_<cohort>_slot{N}.json`` produced by
:mod:`results_analysis.whitening_k_sweep`.

Outputs
-------

* Console summary: per-axis ρ at each L plus the comparison row for
  K=1.
* ``shear_l_vs_k_comparison_<cohort>_slot{N}.json`` cached so a later
  analysis can pick this back up without recomputing.  Filename
  uses the full script stem (not the historical ``shear_l_sweep_*``
  shorthand) to avoid colliding with the JSON sidecar that
  :mod:`results_analysis.shear_l_sweep` writes for the same
  ``(cohort, slot)`` -- a real collision that bit us on 2026-05-12.

Examples
--------

::

    uv run python results_analysis/shear_l_vs_k_comparison.py
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis import (
    cohort_from_pairs,
    entity_id,
    json_metadata,
    pair_type_of,
    response_subdir,
)
from assistant_axis.judge_loaders import migrate_v1_static_scores
from assistant_axis.judge_score_combine import (
    DEFAULT_RESPONSE_DI_WEIGHT,
    combine_desc_inst_two_judges,
    parse_di_weights_arg,
)
from assistant_axis.provenance import (
    InputSpec,
    current_data_subtree_input,
    load_and_register,
)
from results_analysis.axis_judge_correlation import _load_vector_file
from results_analysis.canonical_angles.data import (
    build_goal_nogoal_subspaces,
)
from results_analysis.canonical_angles.whitening import fit_shear
from results_analysis.whitening_k_sweep import (
    DEFAULT_DATA_DIR,
    DEFAULT_EXPERIMENT_DIR,
    DEFAULT_SLOT,
    LAYER,
    axis_direction,
    load_pool,
)


L_VALUES = (0, 1, 2, 3)
K_COMPARE = 1  # the current "simple winner"


# Key convention (review 2026-10-12): scores and projections are both
# keyed by entity_id (``name|R`` / ``name|T``), with v1 (bare-name)
# judge caches lifted via ``migrate_v1_static_scores`` -- the same
# convention ``whitening_k_sweep`` has used since 2026-05-12, so the
# L numbers here and the cached K numbers are again on one footing.
# Until then this script stripped the kind suffix instead
# (``_strip_kind``), on the stale premise that the K cache was
# bare-name: that clobbered the collision names (a trait's score could
# be paired with the role's projection), and with the one-side-missing
# combiner a v2 Sonnet cache (26 of the 61 di axes) left desc+inst
# GPT-only.  ``shear_l_vs_k_comparison_di_slot6.json`` (2026-05-12)
# predates the fix.


def project_at_L(
    entity_vecs: dict[str, torch.Tensor],
    A_goal: np.ndarray,
    A_nogoal: np.ndarray,
    axis_unit: torch.Tensor,
    L: int,
) -> dict[str, float]:
    """Return ``{name: float projection}`` after applying ``L`` shears.

    ``L=0`` is the identity transform (raw projection); for ``L >= 1``
    fit_shear orthogonalises the top-L canonical-angle pairs of the
    goal/no-goal subspaces.
    """
    if L == 0:
        return {n: float((v @ axis_unit).item())
                for n, v in entity_vecs.items()}
    basis = fit_shear(A_goal, A_nogoal, L=L)
    axis_np = axis_unit.numpy()
    axw = basis.apply(axis_np[None, :])[0]
    axw_n = float(np.linalg.norm(axw))
    proj: dict[str, float] = {}
    for n, v in entity_vecs.items():
        vw = basis.apply(v.numpy()[None, :])[0]
        proj[n] = float(np.dot(vw, axw)) / axw_n
    return proj


def _blend(rho_di: float, rho_rs: float, *, is_primary: bool,
           w_rs: float = DEFAULT_RESPONSE_DI_WEIGHT) -> float:
    """Project default response/desc+inst blend."""
    if is_primary and np.isfinite(rho_rs) and np.isfinite(rho_di):
        return w_rs * rho_rs + (1.0 - w_rs) * rho_di
    if np.isfinite(rho_di):
        return float(rho_di)
    return float("nan")


def _load_k_sweep_records(path: Path) -> dict[tuple[str, str, str, int], float]:
    """Read whitening_k_sweep_*.json into a {(pos, neg, source, K): rho} map."""
    with open(path) as f:
        envelope = json.load(f)
    # Tolerate the raw-list legacy shape (a list has no ``.get``).
    records = (envelope.get("result", envelope)
               if isinstance(envelope, dict) else envelope)
    out: dict[tuple[str, str, str, int], float] = {}
    for r in records:
        out[(r["pos"], r["neg"], r["source"], int(r["K"]))] = float(r["rho"])
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR))
    p.add_argument("--data_dir", default=str(DEFAULT_DATA_DIR))
    p.add_argument("--pairs", default="pair_list_di.json")
    p.add_argument("--pairs_primary", default="pair_list_responses.json")
    p.add_argument("--slot", type=int, default=DEFAULT_SLOT)
    p.add_argument("--layer", type=int, default=LAYER)
    p.add_argument("--di_weights", default="inst_tie",
                   help="Combination weights for descriptions + "
                        "instructions (default inst_tie).  See "
                        "judge_score_combine.add_di_weights_arg.")
    p.add_argument("--primary_weight", type=float, default=5.0,
                   help="Sample weight for primary-cohort axes (axes "
                        "with response judging) in the weighted "
                        "cohort-mean.  Default 5.0 matches the RF "
                        "analysis.")
    p.add_argument("--out", default=None,
                   help="Output JSON filename (default: "
                        "shear_l_vs_k_comparison_<cohort>_slot{N}.json).  "
                        "Was 'shear_l_sweep_<cohort>_slot{N}.json' until "
                        "2026-05-12, which collided with the JSON sidecar "
                        "shear_l_sweep.py writes for the same (cohort, "
                        "slot); renamed to use the full script stem.")
    args = p.parse_args(argv)

    di_weights = parse_di_weights_arg(args.di_weights)
    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    cohort = cohort_from_pairs(args.pairs)

    inputs: list[InputSpec] = [
        current_data_subtree_input(
            data_dir, "traits/vectors", dep_key="traits_vectors",
            extras={"slot": str(args.slot), "layer": str(args.layer)}),
        current_data_subtree_input(
            data_dir, "roles/vectors", dep_key="roles_vectors",
            extras={"slot": str(args.slot), "layer": str(args.layer)}),
    ]
    pairs, _, _ = load_and_register(
        experiment_dir / args.pairs, dep_key="pairs_json",
        inputs=inputs, policy="warn")
    pairs_primary, _, _ = load_and_register(
        experiment_dir / args.pairs_primary, dep_key="pairs_primary_json",
        inputs=inputs, policy="warn")
    primary_set = {(it["pos"], it["neg"]) for it in pairs_primary}

    # Pre-load goal/no-goal subspaces (same at every axis).
    A_goal, A_nogoal = build_goal_nogoal_subspaces(
        data_dir, slot=args.slot, layer=args.layer, kind="combined")
    print(f"Loaded goal/no-goal subspaces:  A_goal {A_goal.shape}, "
          f"A_nogoal {A_nogoal.shape}")
    print(f"L sweep: L ∈ {list(L_VALUES)}.  Slot {args.slot}, layer "
          f"{args.layer}.")

    # Load cached K sweep for comparison.
    k_sweep_path = (experiment_dir
                    / f"whitening_k_sweep_{cohort}_slot{args.slot}.json")
    k_records = _load_k_sweep_records(k_sweep_path)
    print(f"Loaded {len(k_records)} K sweep records from {k_sweep_path.name}")

    # Per-axis ρ at each L.
    records: list[dict] = []
    per_axis: dict[tuple[str, str], dict] = {}
    for it in pairs:
        pos, neg = it["pos"], it["neg"]
        ptype = pair_type_of(it)
        axis_id_str = f"{pos}_vs_{neg}"
        axis_dir = experiment_dir / axis_id_str
        is_primary = (pos, neg) in primary_set

        # Judge scores
        g_d, _, _ = load_and_register(
            axis_dir / "gpt" / "scores_descriptions.json",
            dep_key=f"judge_{axis_id_str}_descriptions_gpt",
            inputs=inputs, policy="warn")
        g_i, _, _ = load_and_register(
            axis_dir / "gpt" / "scores_instructions.json",
            dep_key=f"judge_{axis_id_str}_instructions_gpt",
            inputs=inputs, policy="warn")
        s_d, _, _ = load_and_register(
            axis_dir / "sonnet" / "scores_descriptions.json",
            dep_key=f"judge_{axis_id_str}_descriptions_sonnet",
            inputs=inputs, policy="warn")
        s_i, _, _ = load_and_register(
            axis_dir / "sonnet" / "scores_instructions.json",
            dep_key=f"judge_{axis_id_str}_instructions_sonnet",
            inputs=inputs, policy="warn")

        # Projection pool (axis vector + entity vectors), entity_id keyed;
        # ``kinds_for_name`` lifts any v1 (bare-name) judge cache to the
        # same keys (no-op on v2 caches).  See the key-convention note
        # above ``project_at_L``.
        entity_vecs, _pool, _default, kinds_for_name = load_pool(
            data_dir, exclude_names={pos, neg}, slot=args.slot)
        desc_inst = combine_desc_inst_two_judges(
            migrate_v1_static_scores(g_d, kinds_for_name),
            migrate_v1_static_scores(g_i, kinds_for_name),
            migrate_v1_static_scores(s_d, kinds_for_name),
            migrate_v1_static_scores(s_i, kinds_for_name),
            weights=di_weights)

        responses: dict[str, float] = {}
        for mode in ("traits", "roles"):
            sub = response_subdir("gpt", mode)
            fp = axis_dir / sub / "scores_responses.json"
            if not fp.exists():
                continue
            payload, _, _ = load_and_register(
                fp, dep_key=f"judge_{axis_id_str}_responses_{mode}",
                inputs=inputs, policy="warn")
            for n, info in payload.items():
                if info.get("mean_score") is not None:
                    responses[entity_id(n, mode)] = info["mean_score"]

        axis_unit = axis_direction(data_dir, pos, neg, slot=args.slot,
                                   pair_type=ptype)

        rho_di_by_L: dict[int, float] = {}
        rho_rs_by_L: dict[int, float] = {}
        for L in L_VALUES:
            proj = project_at_L(entity_vecs, A_goal, A_nogoal,
                                axis_unit, L)
            for source_name, score_map, proj_for_match, target in (
                    ("desc_inst", desc_inst, proj, rho_di_by_L),
                    ("responses", responses, proj, rho_rs_by_L),
            ):
                names = sorted(set(score_map) & set(proj_for_match))
                if len(names) < 3:
                    target[L] = float("nan")
                    continue
                x = np.array([score_map[n] for n in names], dtype=float)
                y = np.array([proj_for_match[n] for n in names], dtype=float)
                target[L] = float(spearmanr(x, y).correlation)
                records.append({"pos": pos, "neg": neg,
                                "source": source_name, "L": L,
                                "rho": target[L]})

        rho_blend_by_L = {
            L: _blend(rho_di_by_L[L], rho_rs_by_L[L], is_primary=is_primary)
            for L in L_VALUES
        }
        rho_k1_di = k_records.get((pos, neg, "desc_inst", K_COMPARE), float("nan"))
        rho_k1_rs = k_records.get((pos, neg, "responses", K_COMPARE), float("nan"))
        rho_k1_blend = _blend(rho_k1_di, rho_k1_rs, is_primary=is_primary)
        per_axis[(pos, neg)] = {
            "name": pos, "primary": is_primary,
            "rho_by_L": rho_blend_by_L,
            "rho_K1": rho_k1_blend,
            "rho_di_by_L": rho_di_by_L,
            "rho_rs_by_L": rho_rs_by_L,
        }
        cell = "  ".join(f"L{L}={rho_blend_by_L[L]:+.3f}" for L in L_VALUES)
        print(f"  {('P' if is_primary else 'e')} {pos:25s} vs {neg:25s}  "
              f"K1={rho_k1_blend:+.3f}  {cell}")

    # Cohort means.
    rows = list(per_axis.values())
    n_primary = sum(1 for r in rows if r["primary"])

    def _mean(values: list[float], weights: list[float]) -> float:
        v = np.array(values); w = np.array(weights)
        m = np.isfinite(v)
        if not m.any():
            return float("nan")
        return float(np.sum(v[m] * w[m]) / np.sum(w[m]))

    print(f"\n=== Cohort means (n={len(rows)}, primary={n_primary}) ===\n")
    print(f"{'policy':18s}  {'unweighted':>11s}  {'primary 5x':>11s}")
    print("-" * 46)
    # K=1 baseline
    rhos_k1 = [r["rho_K1"] for r in rows]
    w_unif = [1.0] * len(rows)
    w_5x = [args.primary_weight if r["primary"] else 1.0 for r in rows]
    print(f"{'K=1 (cached)':18s}  {_mean(rhos_k1, w_unif):+11.4f}  "
          f"{_mean(rhos_k1, w_5x):+11.4f}")
    # K=0 from cache
    rhos_k0 = []
    for r in rows:
        pk_di = k_records.get((r["name"], r.get("neg", ""), "desc_inst", 0),
                              float("nan"))
        # we didn't store neg in per_axis; do it from the pair directly
    # Re-derive K=0 / L=0 baselines from the existing maps.
    for K in (0, 2, 3):
        rs = []
        for (pos, neg), r in per_axis.items():
            rho_di_k = k_records.get((pos, neg, "desc_inst", K), float("nan"))
            rho_rs_k = k_records.get((pos, neg, "responses", K), float("nan"))
            rs.append(_blend(rho_di_k, rho_rs_k, is_primary=r["primary"]))
        print(f"{'K=' + str(K) + ' (cached)':18s}  {_mean(rs, w_unif):+11.4f}  "
              f"{_mean(rs, w_5x):+11.4f}")
    for L in L_VALUES:
        rs = [r["rho_by_L"][L] for r in rows]
        print(f"{'L=' + str(L) + ' (shear)':18s}  {_mean(rs, w_unif):+11.4f}  "
              f"{_mean(rs, w_5x):+11.4f}")

    # Write JSON cache.  Filename uses the full script stem to avoid
    # colliding with shear_l_sweep.py's JSON sidecar for the same
    # (cohort, slot) -- they have different schemas (this script's
    # records carry both K and L policies; shear_l_sweep's carry only
    # L over a wider grid).  Was 'shear_l_sweep_*' until 2026-05-12.
    out_name = (args.out
                or f"shear_l_vs_k_comparison_{cohort}_slot{args.slot}.json")
    out_path = experiment_dir / out_name
    envelope = json_metadata(
        records, inputs=inputs,
        title=f"shear_l_vs_k_comparison slot={args.slot} "
              f"pairs={args.pairs}")
    with open(out_path, "w") as f:
        json.dump(envelope, f, indent=2)
    print(f"\nWrote {len(records)} records to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
