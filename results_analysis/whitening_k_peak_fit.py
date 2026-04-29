#!/usr/bin/env python3
"""Fit a parabola to each ρ-vs-K curve produced by
:mod:`results_analysis.whitening_k_sweep` (N axes x 2 sources) over
``K ∈ [0, 32]``.

Tests two parametrizations:

(a) **linear-K**:   ``ρ(K) ≈ a + b·K + c·K²``
(b) **log2(K+1)**:  ``ρ(K) ≈ a + b·log2(K+1) + c·log2(K+1)²``

Reports R² per fit, the fitted peak K per curve, and the correlation
between the desc+inst peak and the responses peak across all axes.

Inputs (read from ``--experiment_dir``):

- ``whitening_k_sweep.json`` -- produced by ``whitening_k_sweep.py``
- ``<pairs>``                -- chosen by ``--pairs`` (default
  ``pair_list_12.json``)

Outputs (written to ``--experiment_dir``):

- ``whitening_k_peak_fit.json``  -- per-curve fit records (R² per
  parametrisation, fitted peak K, the y-hat predictions for the
  observed K values).
- ``rho_vs_K_parabolic_fits.png`` -- one panel per axis, observed ρ
  values plus log-space parabolic fits for both sources, vertical
  dashed lines marking the fitted peak K.

Examples
--------

::

    # Default: 12 axes
    uv run python results_analysis/whitening_k_peak_fit.py

    # Use the historical 7-axis subset (matches the original April 23 plot)
    uv run python results_analysis/whitening_k_peak_fit.py \\
        --pairs pair_list_7.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import pearsonr, spearmanr

from assistant_axis import png_metadata, suptitle_with_specs

DEFAULT_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent / (
    "roger/axis_judge_experiments"
)

# K values used for the parabola fit.  Subset of the K_VALUES sweep in
# whitening_k_sweep.py; restrict to the K range where a parabola is a
# reasonable fit (the "sweet spot" we're trying to localise).  Past
# K~32 the curves flatten and a parabola is a poor match.
FIT_K = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32]


def fit_parabola(xs, ys):
    """Least-squares fit ``y = a + b*x + c*x^2``.  Returns
    ``(coef, r2, peak_x, yhat)``."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    c, b, a = np.polyfit(xs, ys, 2)  # np.polyfit returns highest-order first
    yhat = a + b * xs + c * xs ** 2
    ss_res = ((ys - yhat) ** 2).sum()
    ss_tot = ((ys - ys.mean()) ** 2).sum()
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    if c < 0:  # parabola opens down -> real maximum
        peak_x = -b / (2 * c)
    else:
        peak_x = float("nan")
    return (a, b, c), r2, peak_x, yhat


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR),
                   help=f"Directory holding the K-sweep input + pair list "
                        f"(default: {DEFAULT_EXPERIMENT_DIR}).")
    p.add_argument("--pairs", default="pair_list_12.json",
                   help="Pair-list JSON filename (default: pair_list_12.json).")
    p.add_argument("--sweep", default="whitening_k_sweep.json",
                   help="K-sweep JSON filename (default: whitening_k_sweep.json).")
    p.add_argument("--fit_json", default="whitening_k_peak_fit.json",
                   help="Output fit-results JSON filename "
                        "(default: whitening_k_peak_fit.json).")
    p.add_argument("--plot", default="rho_vs_K_parabolic_fits.png",
                   help="Output plot filename "
                        "(default: rho_vs_K_parabolic_fits.png).")
    args = p.parse_args()
    experiment_dir = Path(args.experiment_dir).resolve()

    records = json.load(open(experiment_dir / args.sweep))

    # axis -> source -> {K: rho}
    curves: dict[tuple[str, str], dict] = {}
    for r in records:
        curves.setdefault((r["pos"], r["neg"]), {}).setdefault(r["source"], {})[r["K"]] = r["rho"]

    pair_keys = list(curves.keys())
    rows: list[dict] = []
    for (pos, neg) in pair_keys:
        for source in ("desc_inst", "responses"):
            ys_at_K = curves[(pos, neg)][source]
            ys = [ys_at_K[K] for K in FIT_K]

            xs_lin = FIT_K
            (_a_l, _b_l, _c_l), r2_lin, peak_lin, yhat_lin = fit_parabola(xs_lin, ys)
            # Clip extrapolated peaks to the measured K range.
            peak_lin_clipped = (max(0, min(32, peak_lin))
                                if np.isfinite(peak_lin) else float("nan"))

            xs_log = [np.log2(K + 1) for K in FIT_K]
            (_a_g, _b_g, _c_g), r2_log, peak_log_x, yhat_log = fit_parabola(xs_log, ys)
            peak_log_K = (2 ** peak_log_x - 1
                          if np.isfinite(peak_log_x) else float("nan"))
            peak_log_K_clipped = (max(0, min(32, peak_log_K))
                                  if np.isfinite(peak_log_K) else float("nan"))

            rows.append({
                "pos": pos, "neg": neg, "source": source,
                "r2_linear": r2_lin,
                "r2_log": r2_log,
                "peak_K_linear": peak_lin_clipped,
                "peak_K_log": peak_log_K_clipped,
                "ys": ys,
                "yhat_lin": yhat_lin.tolist(),
                "yhat_log": yhat_log.tolist(),
            })

    print(f"{'axis':37s} {'source':11s}  {'R²_lin':>7s}  {'R²_log':>7s}  "
          f"{'peak_lin':>9s}  {'peak_log':>9s}")
    print("-" * 87)
    for r in rows:
        print(f"{r['pos']+' vs '+r['neg']:37s} {r['source']:11s}  "
              f"{r['r2_linear']:>7.3f}  {r['r2_log']:>7.3f}  "
              f"{r['peak_K_linear']:>9.2f}  {r['peak_K_log']:>9.2f}")

    mean_r2_lin = float(np.mean([r["r2_linear"] for r in rows]))
    mean_r2_log = float(np.mean([r["r2_log"] for r in rows]))
    print(f"\nMean R² across {len(rows)} curves:   "
          f"linear-K = {mean_r2_lin:.3f}   log2(K+1) = {mean_r2_log:.3f}")
    n_log_better = sum(1 for r in rows if r["r2_log"] > r["r2_linear"])
    print(f"log parametrization fits better than linear on "
          f"{n_log_better}/{len(rows)} curves")

    def peaks_by_source(rows, key):
        d: dict[str, list] = {"desc_inst": [], "responses": []}
        for r in rows:
            d[r["source"]].append((r["pos"], r["neg"], r[key]))
        aligned: dict = {}
        for s, lst in d.items():
            for pos, neg, v in lst:
                aligned.setdefault((pos, neg), {})[s] = v
        di = [aligned[k]["desc_inst"] for k in aligned]
        rs = [aligned[k]["responses"] for k in aligned]
        return di, rs, list(aligned.keys())

    for key, label in [("peak_K_linear", "linear-K"),
                       ("peak_K_log",    "log2(K+1)")]:
        di, rs, axes_named = peaks_by_source(rows, key)
        finite = [(d, r) for d, r in zip(di, rs)
                  if np.isfinite(d) and np.isfinite(r)]
        if len(finite) >= 3:
            xd = np.array([t[0] for t in finite])
            xr = np.array([t[1] for t in finite])
            r_pear = float(pearsonr(xd, xr).statistic)
            r_spear = float(spearmanr(xd, xr).correlation)
            print(f"\nPeak-K agreement desc+inst vs responses ({label}): "
                  f"Pearson ρ = {r_pear:.3f}, Spearman ρ = {r_spear:.3f}  "
                  f"(n={len(finite)})")
            print("  axis                                 desc+inst peak   "
                  "responses peak")
            for k, (d, r) in zip(axes_named, finite):
                print(f"    {k[0]+' vs '+k[1]:33s}  {d:>14.2f}   {r:>14.2f}")

    json.dump(rows, open(experiment_dir / args.fit_json, "w"),
              indent=2, default=str)

    # ---- Per-axis panels with both observed data and log-space fits ----
    pairs = json.load(open(experiment_dir / args.pairs))
    pair_keys_ordered = [(it["pos"], it["neg"]) for it in pairs]
    n_axes = len(pair_keys_ordered)
    n_cols = 4
    n_rows = (n_axes + n_cols - 1) // n_cols

    fig, axes_p = plt.subplots(n_rows, n_cols,
                               figsize=(4 * n_cols, 3.5 * n_rows),
                               sharey=True, squeeze=False)
    for i, (pos, neg) in enumerate(pair_keys_ordered):
        ax = axes_p[i // n_cols, i % n_cols]
        x_plot_dense = np.linspace(np.log2(0 + 1), np.log2(32 + 1), 200)
        x_plot_orig = [np.log2(K + 1) for K in FIT_K]
        for source, marker, linestyle, color in [
            ("desc_inst", "s", ":", "C0"),
            ("responses", "o", "-", "C3"),
        ]:
            row = next(r for r in rows
                       if r["pos"] == pos and r["neg"] == neg
                       and r["source"] == source)
            ys = row["ys"]
            a, b, c = np.polyfit(x_plot_orig, ys, 2)[::-1]
            yhat_dense = a + b * x_plot_dense + c * x_plot_dense ** 2
            ax.plot(x_plot_orig, ys, marker=marker, color=color,
                    linestyle="", markersize=6,
                    label=f'{source} (R²={row["r2_log"]:.2f})')
            ax.plot(x_plot_dense, yhat_dense, color=color,
                    linestyle=linestyle, alpha=0.7)
            peak_K = row["peak_K_log"]
            if np.isfinite(peak_K) and 0 <= peak_K <= 32:
                ax.axvline(np.log2(peak_K + 1), color=color,
                           linestyle="--", alpha=0.35, lw=1)
        ax.set_xticks([np.log2(K + 1) for K in FIT_K])
        ax.set_xticklabels([str(K) for K in FIT_K], fontsize=8)
        ax.set_title(f"{pos} vs {neg}", fontsize=9)
        ax.grid(alpha=0.3)
        ax.set_xlabel("K (log2(K+1) spacing)", fontsize=8)
        if i % n_cols == 0:
            ax.set_ylabel("Spearman ρ", fontsize=8)
        ax.legend(fontsize=7, loc="lower left")
    for j in range(n_axes, n_rows * n_cols):
        axes_p[j // n_cols, j % n_cols].axis("off")
    title_line = (f"Per-axis parabolic fits over K ∈ {FIT_K[0]}..{FIT_K[-1]} "
                  f"(log2(K+1) space) -- {n_axes} axes")
    spec_line = ("Solid = responses, dotted = desc+inst; "
                 "vertical dashed lines = fitted peak K")
    _, top_rect = suptitle_with_specs(fig, title_line, spec_line)
    plt.tight_layout(rect=(0, 0, 1, top_rect))
    out_path = experiment_dir / args.plot
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title_line))
    plt.close(fig)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
