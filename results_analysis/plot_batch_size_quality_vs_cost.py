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
from assistant_axis.provenance import (
    CACHE_POLICIES,
    InputSpec,
    current_file_input,
    load_validated_json,
)


DEFAULT_INPUT = "roger/batch_size_curve_rho.json"
DEFAULT_OUTPUT = "roger/batch_size_cost_vs_quality.png"


# ---------------------------------------------------------------------------
# Multi-judge cost extras
# ---------------------------------------------------------------------------
# At B=10 the GPT-4.1-mini per-axis cost from the README cost model is
# $9.98 (input $6.65 + output $3.33).  When we ensemble GPT-mini with a
# second judge, the second judge processes the same items with the same
# input/output token counts -- only the per-token rates change (and the
# question_subsample_modulo factor reduces items proportionally).
#
# Subsample q9 ⇒ 1/3 of items (per axis_judge_correlation.py:1761).
#
# Per-axis cost = input_cost + output_cost
# Input model:  16.6M tokens × $rate_in  per axis at B=10 full
# Output model:  2.08M tokens × $rate_out per axis at B=10 full
B10_GPT_INPUT_M_TOK = 16.6        # millions of input tokens at B=10 full
B10_GPT_OUTPUT_M_TOK = 2.08       # millions of output tokens at B=10 full

# Pricing (per 1M tokens), 2026 rates.
GPT_MINI_RATE_IN, GPT_MINI_RATE_OUT = 0.40, 1.60
HAIKU_RATE_IN, HAIKU_RATE_OUT = 1.00, 5.00
SONNET_RATE_IN, SONNET_RATE_OUT = 3.00, 15.00


def _judge_cost_per_axis(rate_in: float, rate_out: float,
                          subsample: float = 1.0) -> float:
    """Per-axis B=10 cost in USD for a judge with the given rates and an
    optional subsample factor (1.0 = full, 1/3 ≈ q9)."""
    return subsample * (B10_GPT_INPUT_M_TOK * rate_in
                        + B10_GPT_OUTPUT_M_TOK * rate_out)


# Cost extras to draw on top of the B-curve.  Each entry has an
# ``ensemble_key`` matching the combo name in the JSON's
# ``ensemble_combos`` block (computed by judge_ensemble_rho_curve.py);
# if present, the extra point's ρ is read from there.  If absent (older
# JSON), we fall back to the B=10 ρ as a placeholder.
EXTRA_POINTS = [
    {"label": "+ Haiku q9",
     "extra_cost": _judge_cost_per_axis(HAIKU_RATE_IN, HAIKU_RATE_OUT, subsample=1/3),
     "color": "#dd8452",   # orange
     "dy_pt": -18,         # annotation below marker
     "ensemble_key": "gpt_b10__plus_haiku_q9"},
    {"label": "+ Haiku full",
     "extra_cost": _judge_cost_per_axis(HAIKU_RATE_IN, HAIKU_RATE_OUT, subsample=1.0),
     "color": "#c44e52",   # red
     "dy_pt": -18,
     "ensemble_key": "gpt_b10__plus_haiku_full"},
    {"label": "+ Sonnet q9",
     "extra_cost": _judge_cost_per_axis(SONNET_RATE_IN, SONNET_RATE_OUT, subsample=1/3),
     "color": "#8172b2",   # purple
     "dy_pt": +22,         # above marker (dodges coincident Haiku-full)
     "ensemble_key": "gpt_b10__plus_sonnet_q9"},
]


def _best_across_cells_mean_axes(per_axis: dict, B_int: dict) -> dict:
    """Aggregate ``per_axis`` (one ρ per ``<axis>|b<N>|s<S>_l<L>``) into
    ``{b<N>: ρ}`` where ρ is the **mean across axes** of the **max ρ
    across cells**.  Captures "for each axis, what's the best cell at
    this B, averaged over axes" — a tighter quality metric than the
    grand mean (which averages over both axes and cells).
    """
    # axis -> {b<N> -> [ρ over cells]}
    by_axis: dict[str, dict[str, list[float]]] = {}
    for k, r in per_axis.items():
        try:
            axis_part, b_part, _cell_part = k.split("|", 2)
        except ValueError:
            continue
        by_axis.setdefault(axis_part, {}).setdefault(b_part, []).append(r)

    # max-over-cells per (axis, B)
    best_per_axis_B: dict[str, dict[str, float]] = {
        axis: {b: max(rhos) for b, rhos in d.items() if rhos}
        for axis, d in by_axis.items()
    }
    # mean-over-axes per B
    out: dict[str, float] = {}
    for b in B_int:
        vals = [best_per_axis_B[a][b]
                for a in best_per_axis_B
                if b in best_per_axis_B[a]]
        if vals:
            out[b] = sum(vals) / len(vals)
    return out


def _load_batch_size_json(path: Path, *, policy: str = "warn") -> dict:
    """Load + (optionally) validate the batch-size cache.

    Tolerates legacy bare-dict caches (returns ``check=None``) and
    enforces the user-selected cache policy on envelope-wrapped ones.
    See :func:`assistant_axis.provenance.load_validated_json`.
    """
    payload, _check = load_validated_json(path, policy=policy)
    return payload


def plot_quality_vs_cost(
    input_path: Path,
    output_path: Path,
    *,
    raw: dict | None = None,
    policy: str = "warn",
) -> Path:
    """Draw the cost-vs-quality plot from a batch_size_curve_rho.json cache.

    Y-axis: ρ aggregated as **best-across-cells, mean-across-axes**
    (per axis, take max over the 6 (slot, layer) cells; then mean
    across axes).  Tighter than the grand mean — represents the
    "axis-tuned" upper bound.

    If ``raw`` is supplied (the dict already loaded by the caller),
    we skip the disk read; otherwise we load + validate ``input_path``
    using ``policy``.  This avoids double-validation when the caller
    has already validated.

    Returns the output PNG path.
    """
    if raw is None:
        raw = _load_batch_size_json(input_path, policy=policy)
    cost = raw["cost_per_axis_usd"]
    B_int = raw["B_integer"]
    # Prefer best-across-cells aggregation if per_axis is in the JSON
    # (it has been since the May 2026 schema update).  Fall back to the
    # historical grand_mean for older caches.
    if "per_axis" in raw:
        grand = _best_across_cells_mean_axes(raw["per_axis"], B_int)
    else:
        grand = raw["grand_mean_per_b"]
    # ``axes`` was added to batch_size_rho_curve.py's JSON output in
    # May 2026; older caches don't have it, in which case we recover the
    # axis count from the unique ``<axis>|b<N>|s<S>_l<L>`` keys in
    # ``per_axis``.  ``configs`` is similarly fallback'd from per_axis.
    axes_field = raw.get("axes") or []
    if axes_field:
        n_axes = len(axes_field)
    else:
        n_axes = len({k.split("|", 1)[0] for k in raw.get("per_axis", {})})
    configs_field = raw.get("configs") or []
    if configs_field:
        n_configs = len(configs_field)
    else:
        n_configs = len({k.rsplit("|", 1)[1] for k in raw.get("per_axis", {})})

    # Sort by ascending cost (== descending B) so the line draws cheap → expensive.
    Bs = sorted((int(B_int[k]) for k in B_int), reverse=True)
    keys = [f"b{B}" for B in Bs]
    xs = [cost[k] for k in keys]
    rhos = [grand[k] for k in keys]
    qual = [1.0 / (1.0 - r) for r in rhos]

    fig, ax = plt.subplots(figsize=(11.0, 6.5))

    # Non-linear y-axis: underlying coordinate is y = 1/(1-ρ), but ticks
    # and labels are in ρ units.  Each +0.01 ρ matters exponentially more
    # as ρ approaches 1, and this scale makes the diminishing-returns
    # shape visible: low-ρ ticks are bunched near the bottom, high-ρ
    # ticks are spread out near the top.  forward(ρ) = 1/(1-ρ) is
    # monotonically increasing on (-∞, 1), so larger ρ naturally sits
    # higher on screen (better quality up) without an axis inversion.
    def _fwd(r):
        import numpy as np
        r = np.asarray(r, dtype=float)
        return 1.0 / np.maximum(1.0 - r, 1e-9)

    def _inv(y):
        import numpy as np
        y = np.asarray(y, dtype=float)
        return 1.0 - 1.0 / np.maximum(y, 1e-9)

    ax.set_yscale("function", functions=(_fwd, _inv))

    # Plot the raw ρ values (not the transformed quality); the FuncScale
    # handles the visual non-linearity for us.
    ax.plot(xs, rhos, marker="s", markersize=12, linewidth=2.0,
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
            xy=(x, r), xytext=(0, dy), textcoords="offset points",
            ha="center", va=va, fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.4",
                       facecolor="#ffffff", edgecolor="#aaaaaa",
                       alpha=0.92),
            arrowprops=dict(arrowstyle="-",
                             connectionstyle="arc3,rad=0",
                             color="#666666", lw=0.6),
        )

    # Linear-endpoints reference line: drawn as a straight line in the
    # *transformed* (=quality) space so it remains a true chord between
    # the two endpoint points -- concave curves lie above their chord.
    # In ρ-space this looks slightly bowed because of the FuncScale, but
    # with set_yscale handling the transform we just plot in ρ values
    # corresponding to the linearly-interpolated quality values.
    if len(xs) >= 2:
        slope = (qual[-1] - qual[0]) / (xs[-1] - xs[0])
        # Sample the chord densely so it draws smoothly through the
        # nonlinear axis.
        import numpy as np
        x_chord = np.linspace(xs[0], xs[-1], 50)
        q_chord = qual[0] + slope * (x_chord - xs[0])
        r_chord = 1.0 - 1.0 / q_chord
        ax.plot(x_chord, r_chord,
                 linestyle=":", color="#888888", linewidth=1.2,
                 label=f"linear endpoints (slope ≈ {slope:.3f} "
                       f"quality-units / $)")

    # ---- Multi-judge cost extras ----
    # Anchor at B=10 (canonical operating point), draw a separate
    # connecting line to each extra-judge option.  ρ stays at B=10's ρ
    # for now -- placeholder until ensemble ρ is measured.
    b10_idx = Bs.index(10) if 10 in Bs else None
    ensemble_combos = raw.get("ensemble_combos") or {}
    if b10_idx is not None and EXTRA_POINTS:
        anchor_x = xs[b10_idx]
        anchor_y = rhos[b10_idx]
        for ep in EXTRA_POINTS:
            label = ep["label"]
            extra_cost = ep["extra_cost"]
            color = ep["color"]
            dy = ep["dy_pt"]
            ensemble = ensemble_combos.get(ep["ensemble_key"], {})
            ens_rho = ensemble.get("mean_across_axes_best_cell")
            y_extra = ens_rho if ens_rho is not None else anchor_y
            x_extra = anchor_x + extra_cost
            ax.plot([anchor_x, x_extra], [anchor_y, y_extra],
                     marker="D", markersize=10, linewidth=1.6,
                     color=color, alpha=0.9, zorder=4,
                     markerfacecolor=color,
                     markeredgecolor="black", markeredgewidth=0.5,
                     label=f"{label} (+${extra_cost:.2f}, ρ={y_extra:+.4f})")
            label_text = (
                f"{label}\nρ={y_extra:+.4f}\n${x_extra:.2f}/axis"
                if ens_rho is not None
                else f"{label}\nρ=B10 (placeholder)\n${x_extra:.2f}/axis"
            )
            ax.annotate(
                label_text,
                xy=(x_extra, y_extra),
                xytext=(0, dy), textcoords="offset points",
                ha="center", va=("bottom" if dy > 0 else "top"),
                fontsize=9, color=color,
                bbox=dict(boxstyle="round,pad=0.3",
                           facecolor="#ffffff", edgecolor=color,
                           alpha=0.92),
                arrowprops=dict(arrowstyle="-",
                                 connectionstyle="arc3,rad=0",
                                 color=color, lw=0.6),
            )

    ax.set_xlabel("Cost per axis (USD, responses-mode; gpt-4.1-mini base + "
                  "optional second judge)")
    ax.set_ylabel(r"$\rho$ (axis scaled by $1/(1-\rho)$)")
    ax.grid(True, alpha=0.25)
    # X-ticks: B-curve costs, plus the extra-point costs.
    extra_xs = (
        [xs[b10_idx] + ep["extra_cost"] for ep in EXTRA_POINTS]
        if (b10_idx is not None and EXTRA_POINTS) else []
    )
    all_xs = sorted(set(xs + extra_xs))
    ax.set_xticks(all_xs)
    ax.set_xticklabels([f"${c:.0f}" if c >= 20 else f"${c:.2f}"
                        for c in all_xs], rotation=30, ha="right")
    # X-axis range with padding so extras' annotation boxes don't get
    # clipped at the right edge.
    if all_xs:
        x_lo = all_xs[0] - 0.05 * (all_xs[-1] - all_xs[0])
        x_hi = all_xs[-1] + 0.10 * (all_xs[-1] - all_xs[0])
        ax.set_xlim(x_lo, x_hi)

    # Y-axis padding: pad in the *transformed* (= quality) space so the
    # data fills most of the figure regardless of where on the asymptotic
    # curve it sits.  Padding in raw ρ-space gets disproportionately
    # expanded near ρ=1 because the FuncScale stretches that region;
    # quality-space padding is roughly uniform on screen.
    #
    # Range covers BOTH the B-curve and the ensemble-extra ρ values so
    # all points are visible regardless of where the extras land.
    import numpy as np
    rhos_for_range = list(rhos)
    if b10_idx is not None and EXTRA_POINTS:
        for ep in EXTRA_POINTS:
            ens = ensemble_combos.get(ep["ensemble_key"], {})
            r = ens.get("mean_across_axes_best_cell")
            rhos_for_range.append(r if r is not None else rhos[b10_idx])
    qual_for_range = [1.0 / (1.0 - r) for r in rhos_for_range]
    q_min, q_max = min(qual_for_range), max(qual_for_range)
    q_span = q_max - q_min
    q_lo = q_min - q_span * 0.3
    q_hi = q_max + q_span * 0.3
    rho_lo = max(0.0, 1.0 - 1.0 / q_lo)
    rho_hi = min(0.9999, 1.0 - 1.0 / q_hi)
    ax.set_ylim(rho_lo, rho_hi)

    # Y-ticks at "nice" round ρ values (multiples of 1, 2, or 5 × 10^k)
    # rather than uniformly spaced.  This means horizontal gridlines and
    # labels land at simple decimals like 0.770, 0.775, 0.780 rather
    # than weird values from a linspace.
    span = rho_hi - rho_lo
    raw_step = span / 6.0  # aim for ~6 ticks
    magnitude = 10.0 ** np.floor(np.log10(raw_step))
    norm = raw_step / magnitude
    nice_norm = 1.0 if norm <= 1.0 else 2.0 if norm <= 2.0 else 5.0 if norm <= 5.0 else 10.0
    step = nice_norm * magnitude
    tick_start = np.ceil(rho_lo / step) * step
    tick_end = np.floor(rho_hi / step) * step
    yticks = np.round(np.arange(tick_start, tick_end + step / 2, step),
                      max(0, int(-np.floor(np.log10(step))) + 1))
    if step >= 0.01:
        fmt = "{:.2f}"
    elif step >= 0.001:
        fmt = "{:.3f}"
    else:
        fmt = "{:.4f}"
    ax.set_yticks(yticks)
    ax.set_yticklabels([fmt.format(t) for t in yticks])

    ax.legend(loc="upper left", fontsize=9, framealpha=0.9)

    title = ("Responses-mode judging: quality vs cost "
             "(GPT-4.1-mini batch sweep + ensemble extras at B=10)")
    spec = (f"quality $= 1/(1-\\rho)$.  ρ = mean over {n_axes} axes of "
            f"max ρ across {n_configs} (slot, layer) cells (best-cell-"
            "per-axis, axis-mean).  "
            "Black B=5/7/10/15 markers = GPT-4.1-mini alone (cost: "
            "README per-batch model, $0.40/$1.60 per 1M).  "
            "Coloured ◇ = GPT B=10 + a second judge on the same items "
            "(Haiku $1/$5, Sonnet $3/$15; q9 = 1/3 question subsample); "
            "0.625*gpt + 0.375*anthropic score combine (near the "
            "parabolic-peak weight from the response-mode weight sweeps); "
            "ρ from judge_ensemble_rho_curve.py.")
    # line_height bumped from the helper default (0.022) -- on this 6"-tall
    # figure the bold 14pt headline already occupies ~0.024 fig-fraction,
    # so the default puts the first spec line under the headline's
    # descender.  0.030 leaves ~0.005 clearance.
    _, top_rect = suptitle_with_specs(fig, title, spec, line_height=0.030)
    fig.tight_layout(rect=(0, 0, 1, top_rect))

    src_text = Path(__file__).read_text(encoding="utf-8")
    inputs: list[InputSpec] = [
        current_file_input(
            dep_key="batch_size_curve_json",
            path=input_path),
    ]
    fig.savefig(output_path, dpi=150, bbox_inches="tight",
                 metadata=png_metadata(title=title, source_text=src_text,
                                        inputs=inputs))
    plt.close(fig)
    return output_path


def print_marginal_table(
    input_path: Path,
    *,
    raw: dict | None = None,
    policy: str = "warn",
) -> None:
    """Helper: print a small table of marginal Δquality / Δ$ between
    adjacent batch sizes (cheap-to-expensive).  Uses the same best-
    across-cells / mean-across-axes aggregation as the plot.

    Accepts a pre-loaded ``raw`` dict to avoid double validation.
    """
    if raw is None:
        raw = _load_batch_size_json(input_path, policy=policy)
    cost = raw["cost_per_axis_usd"]
    B_int = raw["B_integer"]
    if "per_axis" in raw:
        grand = _best_across_cells_mean_axes(raw["per_axis"], B_int)
    else:
        grand = raw["grand_mean_per_b"]

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
    p.add_argument("--cache-policy", choices=CACHE_POLICIES, default="warn",
                   help="How to react to drift in the batch-size cache's "
                        "recorded provenance: strict / warn (default) / "
                        "rebuild / off.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    inp = Path(args.input)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Single validation pass; both downstream consumers reuse `raw`.
    raw = _load_batch_size_json(inp, policy=args.cache_policy)
    plot_quality_vs_cost(input_path=inp, output_path=out, raw=raw)
    print(f"Wrote {out}")
    print_marginal_table(inp, raw=raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
