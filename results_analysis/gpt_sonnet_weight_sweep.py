#!/usr/bin/env python3
"""Sweep the GPT-4.1-mini / Sonnet-4 weight in the desc+inst score
average and plot mean per-axis projection-ρ vs the blend weight.

For each axis we compute, per entity::

    gpt_score = combine_desc_inst_one_judge(GPT_d, GPT_i, weights=di_weights)
    son_score = combine_desc_inst_one_judge(Son_d, Son_i, weights=di_weights)
    score(w)  = w · gpt_score + (1 - w) · son_score

where ``di_weights`` is the standard desc/inst tiebreak weighting
(default: ``inst_tie`` = ``0.499*desc + 0.501*inst``; pass
``--di_weights`` to override).  Spearman ρ vs the raw activation
projection at ``(slot=3, layer=25)``, averaged across axes.

::

    w = 1   → pure GPT (one judge, desc+inst-combined)
    w = 0.5 → 50/50 average (≈ 4-way average across GPT and Sonnet)
    w = 0   → pure Sonnet (one judge, desc+inst-combined)

Empirical finding (33 axes, slot 3, raw projection):

==================== ============
weight on GPT (w)    mean ρ
==================== ============
0.0  (pure Sonnet)    0.5693
0.5  (50/50)          **0.5953**
1.0  (pure GPT)       0.5758
==================== ============

The 50/50 mix is the principled default -- mean ρ is essentially flat
over ``w ∈ [0.1, 0.9]`` (parabolic fit on the interior gives a peak
at ``w = 0.530``, ρ ≈ 0.5949, which is *0.0004 lower* than the
discrete 50/50 value).  Endpoints show "kinks" because the mode flips
from "averaging two judges" to "using one judge alone" -- a
categorical regime change, not a smooth blend, which is why the
parabola fit is restricted to the interior.

Per-axis interior slope ``Δρ = ρ(w=0.9) − ρ(w=0.1)`` ranks each axis
by which provider was a stronger judge for it; that ranking drives
the colormap and the legend ordering on the plot
(blue = Sonnet-better, red = GPT-better).

Inputs (from ``--experiment_dir``)
----------------------------------

The standard per-axis directory tree produced by
:mod:`results_analysis.axis_judge_correlation`::

    <experiment_dir>/
      pair_list_33.json    # or any pair list passed via --pairs
      <pos>_vs_<neg>/
        gpt/scores_descriptions.json
        gpt/scores_instructions.json
        sonnet/scores_descriptions.json
        sonnet/scores_instructions.json

Plus the standard activation-vectors directory passed via ``--data_dir``.

Outputs (to ``--experiment_dir``)
---------------------------------

- ``gpt_sonnet_weight_sweep.png`` -- the plot.
- ``gpt_sonnet_weight_sweep.json`` -- per-axis ρ-vs-w table, the
  interior parabolic fit (a, b, c, R², peak, peak_rho), and the
  per-axis interior slope used for the legend ordering.

Examples
--------

::

    # Default: 33 axes
    uv run python results_analysis/gpt_sonnet_weight_sweep.py

    # Reproduce the historical 7-axis subset
    uv run python results_analysis/gpt_sonnet_weight_sweep.py \\
        --pairs pair_list_7.json \\
        --plot gpt_sonnet_weight_sweep_7axes.png \\
        --rhos_json gpt_sonnet_weight_sweep_7axes.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy.stats import spearmanr

from assistant_axis import png_metadata
from assistant_axis.judge_score_combine import (
    add_di_weights_arg,
    combine_desc_inst_one_judge,
    parse_di_weights_arg,
)
from results_analysis.axis_judge_correlation import _load_vector_file


DEFAULT_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent / (
    "roger/axis_judge_experiments"
)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / (
    "runpod_workspace/qwen/qwen-3-32b Roger"
)
SLOT, LAYER = 3, 25  # Qwen-3-32B; tuned via rho_by_layer.py.  Other models TBD.
PARABOLA_COLOR = "#1faa4f"


def _v(path: Path) -> torch.Tensor:
    """Load (n_slots, n_layers, hidden) and slice to (SLOT, LAYER) as float."""
    return _load_vector_file(path).float()[SLOT, LAYER]


def axis_unit(data_dir: Path, pos: str, neg: str) -> torch.Tensor:
    p = _v(data_dir / "traits" / "vectors" / f"{pos}.pt")
    n = _v(data_dir / "traits" / "vectors" / f"{neg}.pt")
    d = p - n
    return d / torch.linalg.vector_norm(d)


def _rho_at_weight(d: dict, w: float) -> float:
    score = w * d["g2"] + (1 - w) * d["s2"]
    return float(spearmanr(score, d["proj"]).correlation)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR),
                   help=f"Directory holding the pair list and per-axis "
                        f"score subdirs (default: {DEFAULT_EXPERIMENT_DIR}).")
    p.add_argument("--data_dir", default=str(DEFAULT_DATA_DIR),
                   help=f"Activation vectors directory "
                        f"(default: {DEFAULT_DATA_DIR}).")
    p.add_argument("--pairs", default="pair_list_33.json",
                   help="Pair-list JSON filename "
                        "(default: pair_list_33.json -- every axis with "
                        "desc+inst from both providers).")
    p.add_argument("--plot", default="gpt_sonnet_weight_sweep.png",
                   help="Output plot filename "
                        "(default: gpt_sonnet_weight_sweep.png).")
    p.add_argument("--rhos_json", default="gpt_sonnet_weight_sweep.json",
                   help="Output JSON filename "
                        "(default: gpt_sonnet_weight_sweep.json).")
    add_di_weights_arg(p)
    args = p.parse_args()
    di_weights = parse_di_weights_arg(args.di_weights)
    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    pairs = json.load(open(experiment_dir / args.pairs))
    print(f"Loaded {len(pairs)} axis pairs from {args.pairs}")

    # Cache standalone entity vectors at (SLOT, LAYER), default-centered.
    default_sl = _v(data_dir / "traits" / "vectors" / "default.pt")
    entity_vecs: dict[str, np.ndarray] = {}
    for et in ("traits", "roles"):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem == "default":
                continue
            try:
                v = _load_vector_file(fp).float()[SLOT, LAYER]
                entity_vecs[fp.stem] = (v - default_sl).numpy()
            except Exception:  # pragma: no cover -- skip unreadable files
                continue

    # For each axis, precompute the per-entity (gpt_2way, sonnet_2way,
    # projection) on the common entity set, since these don't depend on
    # the weight.
    per_axis: dict[tuple[str, str], dict] = {}
    for it in pairs:
        pos, neg = it["pos"], it["neg"]
        axis_dir = experiment_dir / f"{pos}_vs_{neg}"
        g_d = json.load(open(axis_dir / "gpt" / "scores_descriptions.json"))
        g_i = json.load(open(axis_dir / "gpt" / "scores_instructions.json"))
        s_d = json.load(open(axis_dir / "sonnet" / "scores_descriptions.json"))
        s_i = json.load(open(axis_dir / "sonnet" / "scores_instructions.json"))
        # Per-judge desc/inst combination using the standard tiebreak weights.
        # The cross-judge sweep below is independent of this choice -- it sweeps
        # GPT vs Sonnet, treating each as a single (already desc+inst-combined) score.
        gpt_scores = combine_desc_inst_one_judge(g_d, g_i, weights=di_weights)
        son_scores = combine_desc_inst_one_judge(s_d, s_i, weights=di_weights)
        common = sorted(set(gpt_scores) & set(son_scores) & set(entity_vecs))
        if len(common) < 3:
            print(f"  [skip] {pos}/{neg}: only {len(common)} shared entities")
            continue
        g2 = np.array([gpt_scores[n] for n in common])
        s2 = np.array([son_scores[n] for n in common])
        a = axis_unit(data_dir, pos, neg).numpy()
        proj = np.array([float(np.dot(entity_vecs[n], a)) for n in common])
        per_axis[(pos, neg)] = {
            "g2": g2, "s2": s2, "proj": proj, "n": len(common)}

    # Sort axes by interior slope Δρ = ρ(0.9) - ρ(0.1).  Ascending order
    # = most Sonnet-favored first → most GPT-favored last.
    slopes = {k: _rho_at_weight(d, 0.9) - _rho_at_weight(d, 0.1)
              for k, d in per_axis.items()}
    sorted_axis_keys = sorted(per_axis.keys(), key=lambda k: slopes[k])
    per_axis = {k: per_axis[k] for k in sorted_axis_keys}

    # Sweep w from 0 to 1.
    ws_arr = np.linspace(0.0, 1.0, 21)
    all_rhos: list[list[float]] = []
    mean_rhos: list[float] = []
    for w in ws_arr:
        rhos = [_rho_at_weight(d, w) for d in per_axis.values()]
        mean_rhos.append(float(np.mean(rhos)))
        all_rhos.append(rhos)
    mean_arr = np.array(mean_rhos)
    all_arr = np.array(all_rhos)  # (n_w, n_axes)

    # Parabolic fit on w ∈ [0.1, 0.9] only -- the endpoint kinks at
    # w=0 / w=1 (single-judge regime) distort a global fit.
    mask = (ws_arr >= 0.10 - 1e-9) & (ws_arr <= 0.90 + 1e-9)
    ws_fit = ws_arr[mask]
    mean_fit = mean_arr[mask]
    c_fit, b_fit, a_fit = np.polyfit(ws_fit, mean_fit, 2)
    yhat_fit = a_fit + b_fit * ws_fit + c_fit * ws_fit ** 2
    ss_res = float(((mean_fit - yhat_fit) ** 2).sum())
    ss_tot = float(((mean_fit - mean_fit.mean()) ** 2).sum())
    r2_fit = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    if c_fit < 0:
        w_peak = float(-b_fit / (2 * c_fit))
        rho_peak = float(a_fit + b_fit * w_peak + c_fit * w_peak ** 2)
    else:
        i_best = int(np.argmax(mean_arr))
        w_peak = float(ws_arr[i_best])
        rho_peak = float(mean_arr[i_best])

    print(f"\nSweep w_GPT from 0 to 1, n={len(per_axis)} axes:")
    print(f"  pure Sonnet (w=0.0):  mean ρ = {mean_arr[0]:+.4f}")
    print(f"  50/50      (w=0.5):  mean ρ = {mean_arr[10]:+.4f}")
    print(f"  pure GPT   (w=1.0):  mean ρ = {mean_arr[-1]:+.4f}")
    print(f"  parabolic peak (interior fit on w∈[0.1, 0.9], "
          f"R²={r2_fit:.4f}): w={w_peak:.3f}, mean ρ ≈ {rho_peak:+.4f}")

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.5, 9.0))
    n_axes = len(per_axis)
    axis_keys = list(per_axis.keys())
    axis_colors = plt.cm.RdBu_r(np.linspace(0.05, 0.95, n_axes))

    for j, k in enumerate(axis_keys):
        ax.plot(ws_arr, all_arr[:, j], color=axis_colors[j],
                lw=1.0, alpha=0.75)

    mean_handle, = ax.plot(
        ws_arr, mean_arr, color="black", lw=2.5, marker="o", markersize=5,
        zorder=20, label=f"mean ({n_axes} axes)")

    # Parabola fit (drawn on TOP of the per-axis curves and the mean).
    ws_fit_plot_in = np.linspace(0.10, 0.90, 50)
    ws_fit_plot_out = np.linspace(0.0, 1.0, 100)
    y_fit_in = a_fit + b_fit * ws_fit_plot_in + c_fit * ws_fit_plot_in ** 2
    y_fit_out = a_fit + b_fit * ws_fit_plot_out + c_fit * ws_fit_plot_out ** 2
    extrap_handle, = ax.plot(
        ws_fit_plot_out, y_fit_out, color="#444444", lw=1.0, ls=":",
        alpha=0.9, zorder=25, label="parabola (extrapolated)")
    fit_handle, = ax.plot(
        ws_fit_plot_in, y_fit_in, color=PARABOLA_COLOR, lw=2.0, ls="-",
        alpha=0.95, zorder=26,
        label=f"parabola fit on [0.1, 0.9] (R²={r2_fit:.3f})")
    w50_handle = ax.axvline(
        0.5, color="grey", linestyle=":", lw=1, alpha=0.7, label="w=0.5")
    peak_handle = ax.axvline(
        w_peak, color=PARABOLA_COLOR, linestyle="--", lw=1.4,
        label=f"interior peak w={w_peak:.3f}")

    ax.set_xlabel("Weight on GPT-4.1-mini\n(remaining on Sonnet 4)",
                  fontsize=9)
    ax.set_ylabel("Per-axis Spearman ρ (slot 3, raw)", fontsize=9)
    title_line = (f"GPT/Sonnet score-blend sweep -- mean ρ across "
                  f"{n_axes} axes")
    # set_title here functions as a suptitle (single-panel figure).
    # Two lines only -- the legend's "Axes: sorted Sonnet-best to
    # GPT-best" annotation already explains the slope-based ordering,
    # so we don't repeat it in the title.
    ax.set_title(
        title_line + "\n"
        f"S={mean_arr[0]:.3f}  50/50={mean_arr[10]:.3f}  "
        f"G={mean_arr[-1]:.3f}",
        fontsize=14, fontweight="bold",
    )
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", "0.25", "0.5", "0.75", "1"], fontsize=9)
    ax.set_xlim(-0.02, 1.02)
    y_hi = float(min(1.0, all_arr.max() + 0.02))
    ax.set_ylim(0.30, y_hi)
    n_below = int((all_arr.min(axis=0) < 0.30).sum())
    below_msg = (f"{n_below} axis below ρ=0.30 not shown"
                 if n_below else "")
    ax.tick_params(axis="y", labelsize=8)
    ax.grid(alpha=0.3)

    # Two stacked legends on the right.
    axis_handles = [
        plt.Line2D([], [], color=axis_colors[i], lw=1.0, alpha=0.75)
        for i in range(n_axes)
    ]
    axis_labels = [f"{k[0]}/{k[1]} ({slopes[k]:+.3f})" for k in axis_keys]
    leg_axes = ax.legend(
        axis_handles, axis_labels,
        loc="upper left", bbox_to_anchor=(1.01, 0.98),
        fontsize=9, ncol=1, frameon=True, framealpha=0.9,
        handlelength=1.5, borderpad=0.6, labelspacing=0.32)
    ax.add_artist(leg_axes)
    # Heading via plain annotation (matplotlib's tight-bbox doesn't
    # account for legend titles wider than the legend body and silently
    # clips them).
    ax.annotate(
        "Axes: sorted Sonnet-best to GPT-best",
        xy=(1.01, 1.005), xycoords="axes fraction",
        ha="left", va="bottom", fontsize=10, fontweight="bold")
    ax.legend(
        [mean_handle, fit_handle, extrap_handle, w50_handle, peak_handle],
        [mean_handle.get_label(), fit_handle.get_label(),
         extrap_handle.get_label(), w50_handle.get_label(),
         peak_handle.get_label()],
        loc="lower left", bbox_to_anchor=(1.01, 0.0),
        fontsize=7, frameon=True, framealpha=0.9, handlelength=1.5)
    if below_msg:
        ax.text(0.02, 0.02, below_msg, transform=ax.transAxes,
                fontsize=7, va="bottom", color="#555555")
    plt.tight_layout()

    out_path = experiment_dir / args.plot
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title_line))
    plt.close(fig)
    print(f"\nWrote {out_path}")

    # ------------------------------------------------------------------
    # JSON output
    # ------------------------------------------------------------------
    json_out = {
        "n_axes": n_axes,
        "ws": [float(w) for w in ws_arr],
        "mean_rho_by_w": [float(v) for v in mean_arr],
        "parabola_fit": {
            "domain": [0.10, 0.90],
            "a": float(a_fit), "b": float(b_fit), "c": float(c_fit),
            "r2": float(r2_fit),
            "peak_w": float(w_peak), "peak_rho": float(rho_peak),
        },
        "per_axis": [
            {"pos": k[0], "neg": k[1],
             "interior_slope_delta_rho": float(slopes[k]),
             "rho_by_w": [float(v) for v in all_arr[:, i]],
             "n": int(per_axis[k]["n"])}
            for i, k in enumerate(axis_keys)
        ],
    }
    json_path = experiment_dir / args.rhos_json
    json.dump(json_out, open(json_path, "w"), indent=2)
    print(f"Wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
