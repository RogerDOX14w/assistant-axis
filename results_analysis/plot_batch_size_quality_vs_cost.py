#!/usr/bin/env python3
"""Plot the B-size cost-vs-quality curve on a 1/(1-ρ) "quality" scale.

Reads the JSON cache produced by :mod:`batch_size_rho_curve` (default
``roger/batch_size_curve_rho.json``) and emits a single-panel scatter:

- x: cost per axis (USD), from the README's per-batch token model
- y: quality = ``1 / (1 − ρ)``, where ρ is the grand-mean ρ across
  the axes × (slot, layer) configs in the cache.

Why the 1/(1-ρ) scale?  Each +0.01 ρ matters exponentially more as you
approach the ρ=1 ceiling.  At ρ ≈ 0.77 (our typical responses-mode
operating point), ``d(1/(1−ρ))/dρ ≈ 18`` -- so each +0.01 ρ buys roughly
a 4 % improvement in effective signal.  The diminishing-returns shape
of the cost-vs-quality curve is much more visible here than on a linear
ρ axis.

Side-effect: prints a small table of marginal Δquality / Δ$ between
adjacent batch sizes (a cleaner way to read "where does the
cost-efficiency curve fall off?").

CLI
---

::

    # Default: read roger/batch_size_curve_rho.json, write
    # roger/batch_size_cost_vs_quality.png.
    uv run python results_analysis/plot_batch_size_quality_vs_cost.py

    # Custom JSON / output path:
    uv run python results_analysis/plot_batch_size_quality_vs_cost.py \\
      --input roger/b_curve_truthful/batch_size_curve_rho.json \\
      --output roger/b_curve_truthful/cost_vs_quality.png

Library
-------

::

    from results_analysis.plot_batch_size_quality_vs_cost import plot_quality_vs_cost
    plot_quality_vs_cost(input_path=..., output_path=...)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from assistant_axis.plot_metadata import png_metadata, suptitle_with_specs


DEFAULT_INPUT = "roger/batch_size_curve_rho.json"
DEFAULT_OUTPUT = "roger/batch_size_cost_vs_quality.png"


def plot_quality_vs_cost(input_path: Path, output_path: Path) -> Path:
    """Draw the cost-vs-quality plot from a batch_size_curve_rho.json cache.

    Returns the output PNG path.
    """
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    grand = raw["grand_mean_per_b"]
    cost = raw["cost_per_axis_usd"]
    B_int = raw["B_integer"]
    n_axes = len(raw.get("axes", []))
    n_configs = len(raw.get("configs", []))

    # Sort by ascending cost (== descending B) so the line draws cheap → expensive.
    Bs = sorted((int(B_int[k]) for k in B_int), reverse=True)
    keys = [f"b{B}" for B in Bs]
    xs = [cost[k] for k in keys]
    rhos = [grand[k] for k in keys]
    qual = [1.0 / (1.0 - r) for r in rhos]

    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    ax.plot(xs, qual, marker="s", markersize=12, linewidth=2.0,
             color="#333333", zorder=5)

    # Annotate each point with B, ρ, cost, quality.
    for i, (B, x, r, q) in enumerate(zip(Bs, xs, rhos, qual)):
        # Alternate above/below to avoid overlap.
        dy = 14 if i % 2 == 0 else -14
        va = "bottom" if dy > 0 else "top"
        label = (f"B={B}\nρ = {r:+.4f}\n"
                 f"${x:.2f}/axis\n1/(1−ρ) = {q:.3f}")
        ax.annotate(
            label,
            xy=(x, q), xytext=(0, dy), textcoords="offset points",
            ha="center", va=va, fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.4",
                       facecolor="#ffffff", edgecolor="#aaaaaa",
                       alpha=0.92),
            arrowprops=dict(arrowstyle="-",
                             connectionstyle="arc3,rad=0",
                             color="#666666", lw=0.6),
        )

    # Linear-endpoints reference line (concave curves lie above their chord).
    if len(xs) >= 2:
        slope = (qual[-1] - qual[0]) / (xs[-1] - xs[0])
        ax.plot([xs[0], xs[-1]],
                 [qual[0], qual[0] + slope * (xs[-1] - xs[0])],
                 linestyle=":", color="#888888", linewidth=1.2,
                 label=f"linear endpoints (slope ≈ {slope:.3f} quality / $)")

    ax.set_xlabel("Cost per axis (USD, gpt-4.1-mini, full corpus responses-mode)")
    ax.set_ylabel(r"Quality $= 1 / (1 - \rho)$")
    ax.grid(True, alpha=0.25)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"${c:.2f}" for c in xs])
    y_min, y_max = min(qual), max(qual)
    pad = (y_max - y_min) * 0.4 if y_max > y_min else 0.5
    ax.set_ylim(y_min - pad, y_max + pad)

    # Side y-axis with corresponding ρ values.
    ax2 = ax.twinx()
    ax2.set_ylim(*ax.get_ylim())
    y2_ticks = [round(min(qual) - pad/2 + i * (y_max + pad - y_min + pad/2)
                       / 5, 1) for i in range(6)]
    # Simpler tick scheme: pick 5 evenly-spaced quality values.
    import numpy as np
    y2_ticks = list(np.linspace(y_min - pad/2, y_max + pad/2, 6).round(2))
    ax2.set_yticks(y2_ticks)
    ax2.set_yticklabels([f"ρ = {1.0 - 1.0/q:+.4f}" for q in y2_ticks],
                         fontsize=8.5, color="#666666")
    ax2.set_ylabel(r"corresponding $\rho$", color="#666666", fontsize=9)
    ax2.tick_params(axis="y", colors="#666666")

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    title = "GPT responses-mode batch size: quality vs cost"
    spec = (f"quality $= 1/(1-\\rho)$, ρ averaged over {n_axes} axes × "
            f"{n_configs} (slot, layer) cells.\n"
            "Cost from the README's per-batch token model "
            "(gpt-4.1-mini, $0.40/$1.60 per 1M tokens).")
    _, top_rect = suptitle_with_specs(fig, title, spec)
    fig.tight_layout(rect=(0, 0, 1, top_rect))

    src_text = Path(__file__).read_text(encoding="utf-8")
    fig.savefig(output_path, dpi=150, bbox_inches="tight",
                 metadata=png_metadata(title=title, source_text=src_text))
    plt.close(fig)
    return output_path


def print_marginal_table(input_path: Path) -> None:
    """Helper: print a small table of marginal Δquality / Δ$ between
    adjacent batch sizes (cheap-to-expensive)."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    grand = raw["grand_mean_per_b"]
    cost = raw["cost_per_axis_usd"]
    B_int = raw["B_integer"]

    Bs = sorted((int(B_int[k]) for k in B_int), reverse=True)  # cheap → expensive
    rows = []
    prev_q = prev_c = None
    print()
    print(f"{'B':>3}  {'cost':>8}  {'ρ':>9}  {'1/(1−ρ)':>9}  {'+q / +$':>9}")
    for B in Bs:
        k = f"b{B}"
        r = grand[k]
        q = 1.0 / (1.0 - r)
        c = cost[k]
        if prev_q is None:
            row_ratio = ""
        else:
            dq = q - prev_q
            dc = c - prev_c
            row_ratio = f"{(dq / dc):>9.4f}" if dc > 0 else f"{'-':>9}"
        prev_q, prev_c = q, c
        print(f"{B:>3}  ${c:>6.2f}  {r:>+9.4f}  {q:>9.4f}  {row_ratio}")
        rows.append((B, c, r, q))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--input", type=str, default=DEFAULT_INPUT,
                   help=f"JSON cache from batch_size_rho_curve.py "
                        f"(default: {DEFAULT_INPUT}).")
    p.add_argument("--output", type=str, default=DEFAULT_OUTPUT,
                   help=f"Output PNG path (default: {DEFAULT_OUTPUT}).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    plot_quality_vs_cost(input_path=inp, output_path=out)
    print(f"Wrote {out}")
    print_marginal_table(inp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
