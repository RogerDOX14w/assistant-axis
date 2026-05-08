#!/usr/bin/env python3
"""Compute response-mode ρ for **judge ensembles**: GPT-4.1-mini at B=10
combined 50/50 with each of three Anthropic options on the same items.

For each ensemble combo × axis × (slot, layer) cell, we:

1. Load per-entity mean ``mean_score`` from
   ``<experiment_dir>/<axis>/<dir>/scores_responses.json`` for both
   judges (e.g. ``gpt_responses_<side>_b10`` and
   ``haiku_responses_<side>_b10_q9``), combining roles + traits sides.
2. Combine them with ``combined[name] = 0.5 * gpt[name] + 0.5 * anth[name]``
   over the entities present in BOTH judges' caches.
3. Run the same ``(L, K)`` sweep that ``batch_size_rho_curve`` uses
   (coarse grid + bracket-and-bisect on K), taking the best ρ as that
   (combo, axis, cell)'s score.

Aggregation matches ``plot_batch_size_quality_vs_cost.py``: per axis, max
ρ across cells; then mean across axes per combo.

The output augments the input JSON (``batch_size_curve_rho.json``) with
an ``ensemble_combos`` block:

::

    {
      ...,                          # existing batch-size keys
      "ensemble_combos": {
        "gpt_b10__plus_haiku_q9":   {"per_axis_cell": {"<axis>|s<S>_l<L>": ρ, ...},
                                      "best_per_axis": {"<axis>": ρ_max, ...},
                                      "mean_across_axes_best_cell": ρ},
        "gpt_b10__plus_haiku_full": ...,
        "gpt_b10__plus_sonnet_q9":  ...,
      }
    }

CLI
---

::

    uv run python results_analysis/judge_ensemble_rho_curve.py \\
        --input  roger/axis_judge_experiments/batch_size_curve_8slot/batch_size_curve_rho.json \\
        --output roger/axis_judge_experiments/batch_size_curve_8slot/batch_size_curve_rho.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from results_analysis.batch_size_rho_curve import (
    DEFAULT_AXES, DEFAULT_CONFIGS, DEFAULT_DATA_DIR, DEFAULT_EXPERIMENT_DIR,
    axis_direction, best_rho, setup_at,
)


# Combos to evaluate.  Each entry: (label, anthropic-dir-prefix).  The
# GPT side is fixed at ``gpt_responses_{side}_b10``.
COMBOS: list[tuple[str, str]] = [
    ("gpt_b10__plus_haiku_q9",   "haiku_responses_{side}_b10_q9"),
    ("gpt_b10__plus_haiku_full", "haiku_responses_{side}_b10"),
    ("gpt_b10__plus_sonnet_q9",  "sonnet_responses_{side}_b10_q9"),
]
GPT_DIR_TEMPLATE = "gpt_responses_{side}_b10"


# All 12 traits-based response-mode axes that have GPT B=10 data
# (the 3 original "set 1" axes plus the 9 axes added by Phase 8 in
# May 2026).  ``axes`` is a list of ``(axis_dir_name, pos, neg)``
# triples, matching ``batch_size_rho_curve``'s shape.
ALL_RESPONSE_AXES: list[tuple[str, str, str]] = [
    ("truthful_vs_deceitful",         "truthful",        "deceitful"),
    ("progressive_vs_conservative",   "progressive",     "conservative"),
    ("improvisational_vs_methodical", "improvisational", "methodical"),
    ("concise_vs_verbose",            "concise",         "verbose"),
    ("ecocentric_vs_anthropocentric", "ecocentric",      "anthropocentric"),
    ("egalitarian_vs_elitist",        "egalitarian",     "elitist"),
    ("guileless_vs_scheming",         "guileless",       "scheming"),
    ("harmless_vs_harmful",           "harmless",        "harmful"),
    ("honest_vs_dishonest",           "honest",          "dishonest"),
    ("helpful_vs_unhelpful",          "helpful",         "unhelpful"),
    ("relativist_vs_absolutist",      "relativist",      "absolutist"),
    ("systems_thinker_vs_analytical", "systems_thinker", "analytical"),
]


# Four sets of three axes.  Set 1 is the original triplet (the three
# axes that have full B-size sweep data).  Sets 2..4 cover the nine
# May-2026 additions, alphabetically.  Used by the Pareto plot to
# show per-set slope variability of the ensemble lift on top of the
# B=10 GPT-only baseline.
AXIS_SETS: list[dict] = [
    {"set_id": "set_1_initial",
     "label": "set 1 (initial)",
     "axes": ["truthful_vs_deceitful",
              "progressive_vs_conservative",
              "improvisational_vs_methodical"]},
    {"set_id": "set_2",
     "label": "set 2",
     "axes": ["concise_vs_verbose",
              "ecocentric_vs_anthropocentric",
              "egalitarian_vs_elitist"]},
    {"set_id": "set_3",
     "label": "set 3",
     "axes": ["guileless_vs_scheming",
              "harmless_vs_harmful",
              "helpful_vs_unhelpful"]},
    {"set_id": "set_4",
     "label": "set 4",
     "axes": ["honest_vs_dishonest",
              "relativist_vs_absolutist",
              "systems_thinker_vs_analytical"]},
]


def _load_response_scores(
    experiment_dir: Path, axis: str, dir_template: str,
) -> dict[str, float]:
    """Load per-entity mean response-judge scores from one judge×axis,
    summing across the roles+traits sides.  Returns ``{name: ρ}``."""
    out: dict[str, float] = {}
    for side in ("roles", "traits"):
        sub = dir_template.format(side=side)
        path = experiment_dir / axis / sub / "scores_responses.json"
        if not path.exists():
            continue
        scores = json.loads(path.read_text())
        for name, info in scores.items():
            ms = info.get("mean_score") if isinstance(info, dict) else None
            if ms is not None:
                out[name] = float(ms)
    return out


def _combine_weighted(a: dict[str, float], b: dict[str, float],
                       w_a: float) -> dict[str, float]:
    """``w_a * a[name] + (1 - w_a) * b[name]`` for entities in BOTH dicts."""
    common = a.keys() & b.keys()
    return {n: w_a * a[n] + (1.0 - w_a) * b[n] for n in common}


def _aggregate_per_set(
    best_per_axis: dict[str, float],
    axis_sets: Sequence[dict] = tuple(AXIS_SETS),
) -> list[dict]:
    """Group ``best_per_axis`` (axis_name -> max-over-cells ρ) by ``axis_sets``
    and return one entry per set with the mean ρ over the set's available
    axes.  Sets with no available axes are skipped."""
    out: list[dict] = []
    for s in axis_sets:
        members = [a for a in s["axes"] if a in best_per_axis]
        if not members:
            continue
        rho_mean = float(np.mean([best_per_axis[a] for a in members]))
        out.append({
            "set_id": s["set_id"],
            "label": s["label"],
            "axes": members,
            "n_axes": len(members),
            "rho_mean_best_cell": rho_mean,
        })
    return out


def _compute_gpt_only_b10_per_axis_best_cell(
    *,
    experiment_dir: Path,
    data_dir: Path,
    axes: Sequence[tuple[str, str, str]],
    configs: Sequence[tuple[int, int]],
    geom: dict,
) -> tuple[dict[str, float], dict[str, float]]:
    """For each axis, max ρ across cells using **GPT-only** B=10 scores.

    Returns ``(per_axis_cell, best_per_axis)`` -- the same shape that
    ``compute_ensemble_rho`` returns per combo, but using just the GPT
    judge (no Anthropic blend).  Provides the natural per-set baseline
    against which each ensemble combo's per-set lift can be measured
    on a like-axis-set basis.
    """
    per_axis_cell: dict[str, float] = {}
    best_per_axis: dict[str, float] = {}
    for axis_name, pos_name, neg_name in axes:
        gpt = _load_response_scores(experiment_dir, axis_name, GPT_DIR_TEMPLATE)
        if not gpt:
            continue
        cell_rhos: list[float] = []
        for slot, layer in configs:
            names, M_raw, A_g, A_n, pool = geom[(slot, layer)]
            axis_dir = axis_direction(data_dir, pos_name, neg_name, slot, layer)
            rho = best_rho(M_raw, axis_dir, A_g, A_n, pool, names, gpt)
            if np.isnan(rho):
                rho = float("nan")
            per_axis_cell[f"{axis_name}|s{slot}_l{layer}"] = float(rho)
            if np.isfinite(rho):
                cell_rhos.append(float(rho))
        if cell_rhos:
            best_per_axis[axis_name] = max(cell_rhos)
    return per_axis_cell, best_per_axis


def compute_ensemble_rho(
    *,
    experiment_dir: Path,
    data_dir: Path,
    axes: Sequence[tuple[str, str, str]],
    configs: Sequence[tuple[int, int]],
    combos: Sequence[tuple[str, str]] = COMBOS,
    gpt_weight: float = 0.625,
    _geom: dict | None = None,
) -> dict:
    """Compute ensemble ρ for every (combo, axis, cell).

    ``axes`` is a sequence of ``(axis_name, pos, neg)`` triples (the
    same shape that ``batch_size_rho_curve`` uses).  ``configs`` is a
    sequence of ``(slot, layer)`` pairs.

    ``_geom`` (optional) is a pre-computed ``{(slot, layer): setup_at(...)}``
    cache.  When supplied, skip the per-cell ``setup_at`` calls (each costs
    a few seconds).  Used by ``main`` to share geometry between the
    GPT-only baseline pass and the ensemble pass.

    Returns a dict shaped for direct insertion under ``ensemble_combos``
    in the batch-size curve JSON.
    """
    # ---- pre-cache geometry per (slot, layer) (re-fits are expensive) ----
    if _geom is not None:
        geom = _geom
    else:
        geom = {}
        for slot, layer in configs:
            print(f"  geom: setting up cell ({slot}, {layer}) ...")
            geom[(slot, layer)] = setup_at(data_dir, slot, layer)

    out: dict[str, dict] = {}
    for combo_label, anth_template in combos:
        print(f"\n=== combo: {combo_label} ===")
        per_axis_cell: dict[str, float] = {}
        best_per_axis: dict[str, float] = {}

        for axis_triple in axes:
            axis_name = axis_triple[0]
            pos_name, neg_name = axis_triple[1], axis_triple[2]
            print(f"  axis: {axis_name}")

            gpt = _load_response_scores(
                experiment_dir, axis_name, GPT_DIR_TEMPLATE,
            )
            anth = _load_response_scores(
                experiment_dir, axis_name, anth_template,
            )
            if not gpt or not anth:
                print(f"    skip: gpt n={len(gpt)} anth n={len(anth)}")
                continue
            combined = _combine_weighted(gpt, anth, w_a=gpt_weight)
            print(f"    combined entities: {len(combined)} "
                  f"(gpt {len(gpt)} ∩ anth {len(anth)}; "
                  f"weights: {gpt_weight:.3f}*gpt + "
                  f"{1.0 - gpt_weight:.3f}*anth)")

            cell_rhos: list[float] = []
            for slot, layer in configs:
                names, M_raw, A_g, A_n, pool = geom[(slot, layer)]
                axis_dir = axis_direction(
                    data_dir, pos_name, neg_name, slot, layer)
                rho = best_rho(M_raw, axis_dir, A_g, A_n, pool,
                               names, combined)
                if np.isnan(rho):
                    rho = float("nan")
                per_axis_cell[f"{axis_name}|s{slot}_l{layer}"] = float(rho)
                cell_rhos.append(float(rho))
                print(f"    ({slot},{layer}): ρ = {rho:+.4f}")
            best_per_axis[axis_name] = max(
                r for r in cell_rhos if np.isfinite(r)
            ) if any(np.isfinite(r) for r in cell_rhos) else float("nan")

        if best_per_axis:
            grand = float(np.mean(list(best_per_axis.values())))
        else:
            grand = float("nan")
        per_set = _aggregate_per_set(best_per_axis)
        print(f"  combo {combo_label}: best-per-axis mean = {grand:+.4f} "
              f"(over {len(best_per_axis)} axes)")
        for entry in per_set:
            print(f"    {entry['label']:>20s}: ρ = "
                  f"{entry['rho_mean_best_cell']:+.4f}  "
                  f"(n_axes={entry['n_axes']})")

        out[combo_label] = {
            "per_axis_cell": per_axis_cell,
            "best_per_axis": best_per_axis,
            "mean_across_axes_best_cell": grand,
            "per_set": per_set,
        }
    return out


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--input", type=str, required=True,
        help="Existing batch_size_curve_rho.json (used for configs / "
             "to merge ensemble_combos into).")
    p.add_argument(
        "--output", type=str, default=None,
        help="Where to write the augmented JSON.  Default: same as --input.")
    p.add_argument(
        "--data_dir", type=str, default=str(DEFAULT_DATA_DIR),
        help=f"Vectors / pool data dir.  Default: {DEFAULT_DATA_DIR}")
    p.add_argument(
        "--experiment_dir", type=str, default=DEFAULT_EXPERIMENT_DIR,
        help=f"Where the per-axis judge dirs live.  Default: "
             f"{DEFAULT_EXPERIMENT_DIR}")
    p.add_argument(
        "--gpt_weight", type=float, default=0.625,
        help="Weight on GPT-mini in the ensemble; the Anthropic weight "
             "is 1 - this.  Default 0.625 (≈ near the parabolic peak from "
             "the response-mode GPT/Haiku weight sweep).  Use 0.5 for "
             "even-50/50.")
    p.add_argument(
        "--axes_source", choices=["all_response_axes", "input_json"],
        default="all_response_axes",
        help="Which axes to evaluate ensembles over.  Default: "
             "ALL_RESPONSE_AXES (12 traits axes; combos with missing data "
             "auto-skip per axis).  'input_json' reuses raw['axes'] from the "
             "input JSON (the legacy 3-axis B-curve set).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    in_path = Path(args.input)
    out_path = Path(args.output) if args.output else in_path
    raw = json.loads(in_path.read_text(encoding="utf-8"))

    if args.axes_source == "all_response_axes":
        axes_t = list(ALL_RESPONSE_AXES)
    else:
        axes = raw.get("axes") or [list(t) for t in DEFAULT_AXES]
        axes_t = [(a[0], a[1], a[2]) for a in axes]
    configs_raw = raw.get("configs") or [list(c) for c in DEFAULT_CONFIGS]
    configs = [(int(c[0]), int(c[1])) for c in configs_raw]

    print(f"Computing ensemble ρ for up to {len(axes_t)} axes × "
          f"{len(configs)} cells × {len(COMBOS)} combos "
          f"(axes_source={args.axes_source}); "
          f"per-combo axes filter to those with both GPT and Anthropic data.")

    # Precompute geometry once and share between GPT-only baseline and ensemble.
    geom: dict[tuple[int, int], tuple] = {}
    for slot, layer in configs:
        print(f"  geom: setting up cell ({slot}, {layer}) ...")
        geom[(slot, layer)] = setup_at(Path(args.data_dir), slot, layer)

    print("\n=== GPT-only B=10 per-axis baseline ===")
    gpt_only_per_axis_cell, gpt_only_best_per_axis = (
        _compute_gpt_only_b10_per_axis_best_cell(
            experiment_dir=Path(args.experiment_dir),
            data_dir=Path(args.data_dir),
            axes=axes_t, configs=configs, geom=geom,
        )
    )
    gpt_only_per_set = _aggregate_per_set(gpt_only_best_per_axis)
    if gpt_only_best_per_axis:
        gpt_only_overall = float(np.mean(list(gpt_only_best_per_axis.values())))
    else:
        gpt_only_overall = float("nan")
    print(f"  GPT-only B=10 mean (over {len(gpt_only_best_per_axis)} axes): "
          f"{gpt_only_overall:+.4f}")
    for entry in gpt_only_per_set:
        print(f"    {entry['label']:>20s}: ρ = "
              f"{entry['rho_mean_best_cell']:+.4f}  "
              f"(n_axes={entry['n_axes']})")

    print("\n=== Ensemble combos ===")
    ensemble = compute_ensemble_rho(
        experiment_dir=Path(args.experiment_dir),
        data_dir=Path(args.data_dir),
        axes=axes_t, configs=configs,
        gpt_weight=float(args.gpt_weight),
        # Reuse pre-computed geometry to avoid the duplicate setup_at cost.
        _geom=geom,
    )
    # Stamp the weights into the JSON so the plotter / future readers
    # know what blend produced these ρ values.
    ensemble["_meta"] = {
        "gpt_weight": float(args.gpt_weight),
        "anthropic_weight": 1.0 - float(args.gpt_weight),
        "axes_source": args.axes_source,
        "n_axes_evaluated": len(axes_t),
        "axis_sets": [
            {"set_id": s["set_id"], "label": s["label"], "axes": s["axes"]}
            for s in AXIS_SETS
        ],
    }

    raw["ensemble_combos"] = ensemble
    raw["gpt_only_b10_baseline"] = {
        "per_axis_cell": gpt_only_per_axis_cell,
        "best_per_axis": gpt_only_best_per_axis,
        "mean_across_axes_best_cell": gpt_only_overall,
        "per_set": gpt_only_per_set,
    }
    out_path.write_text(json.dumps(raw, indent=2))
    print(f"\nWrote {out_path}")
    print()
    print(f"{'combo':<28}  {'mean(best-cell-per-axis)':>26}  {'n_axes':>6}")
    for k, v in ensemble.items():
        if k == "_meta" or "mean_across_axes_best_cell" not in v:
            continue
        n = len(v.get("best_per_axis", {}))
        print(f"  {k:<28}  {v['mean_across_axes_best_cell']:>+26.4f}  "
              f"{n:>6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
