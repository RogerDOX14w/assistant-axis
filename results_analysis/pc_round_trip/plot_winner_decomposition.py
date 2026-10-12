#!/usr/bin/env python3
"""Render the nth_pc winner decomposition heatmap.

Loads the (n_canon_pcs, n_strips * cols_per_strip) matrix from
``winner_decomposition.py``'s npz output and renders it as a heatmap
where:
  - Each column is a probability distribution over canonical PCs
    (squared coefficients of the winner direction projected onto canonical
    Vt, normalised to sum to 1).
  - Each target PC index N has one strip, side-by-side.
  - Within a strip: one column per (style, n-cell level), glossary first;
    since 2026-10-12 the levels are n = 1, 2, 4, 6, 7 of the 7-cell order
    (10 columns), read from the column keys (6 columns, n = 1..3, before).
  - A red tick at row k = N marks where a winner that is canonical PC N
    would put its mass.

The title is taken from the npz's ``meta["winners_source"]``: "nth_pc
search winners" only when the winners came from ``klm_sweep.py``'s
per-cell section; otherwise it names the variant whose configurations
were used (code review 2026-10-12: the May 9 figure called itself
"nth_pc winner" although built on fixed_principled configurations).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.ticker as mticker
import numpy as np

from assistant_axis.plot_metadata import png_metadata, suptitle_with_specs
from assistant_axis.provenance import (
    CACHE_POLICIES, InputSpec, load_and_register_npz,
)
from results_analysis.pc_round_trip.winner_decomposition import (
    CANONICAL_L, LAYER_C, SLOT_C,
)


DEFAULT_NPZ = "roger/pc_round_trip_nth_pc_winner_decomposition.npz"
DEFAULT_OUTPUT = "roger/pc_round_trip_nth_pc_winner_decomposition.png"

_STYLE_ABBREV = {"glossary": "glo", "inline": "inl"}


def strip_layout(column_keys: list) -> tuple[list[int], int, list[str], list[int]]:
    """``(pcs_in_order, cols_per_strip, styles_in_order, n_values)`` from
    the column keys ``(pc, style, n)``.  Every strip must have the same
    columns (``winner_decomposition`` writes them so)."""
    pcs_in_order: list[int] = []
    for pc, _, _ in column_keys:
        if int(pc) not in pcs_in_order:
            pcs_in_order.append(int(pc))
    first = [(str(s), int(n)) for pc, s, n in column_keys
             if int(pc) == pcs_in_order[0]]
    cols_per_strip = len(first)
    if cols_per_strip * len(pcs_in_order) != len(column_keys):
        raise ValueError("column keys do not form equal strips per PC")
    styles: list[str] = []
    n_values: list[int] = []
    for s, n in first:
        if s not in styles:
            styles.append(s)
        if n not in n_values:
            n_values.append(n)
    return pcs_in_order, cols_per_strip, styles, n_values


def figure_title(meta: dict) -> str:
    """Headline naming what the columns are, from ``meta``."""
    canon = meta.get("canonical_cell") or {
        "slot": SLOT_C, "layer": LAYER_C, "L": CANONICAL_L}
    where = (f"canonical PC basis (slot {canon['slot']}, layer "
             f"{canon['layer']}, L={canon['L']}"
             f"{' raw' if int(canon['L']) == 0 else ' shear'})")
    variant = (meta.get("winners_source") or {}).get("variant", "unknown")
    if variant == "nth_pc":
        return f"PC round-trip: nth_pc search winners decomposed in the {where}"
    if variant == "unknown":
        return ("PC round-trip: PC N at per-cell winner configurations "
                f"(search not recorded), decomposed in the {where}")
    return (f"PC round-trip: PC N at the {variant} winners' configurations, "
            f"decomposed in the {where}")


def render_heatmap(ax, matrix: np.ndarray, column_keys: list,
                    *, max_canon_pc: int = 0,
                    log_color: bool = True,
                    title: str = "",
                    mark_target: bool = True) -> None:
    """Render heatmap on the given axis.

    matrix: (n_canon_pcs, n_cols).
    column_keys: list of (pc, style, n) tuples, len == n_cols.
    mark_target: draw a red tick at row k = N across each strip.
    """
    if max_canon_pc <= 0:
        max_canon_pc = matrix.shape[0]
    M = matrix[:max_canon_pc, :].copy()
    n_canon, n_cols = M.shape

    # Replace zeros with a small floor for log color scale.
    if log_color:
        floor = 1e-5
        M_disp = np.clip(M, floor, 1.0)
        norm = mcolors.LogNorm(vmin=floor, vmax=1.0)
    else:
        M_disp = M
        norm = None

    # pcolormesh with log y.
    # x edges: 0, 1, 2, ..., n_cols
    # y edges: 0.5, 1.5, ..., n_canon + 0.5  (so canonical PC k is at y=k)
    x_edges = np.arange(n_cols + 1)
    y_edges = np.arange(n_canon + 1) + 0.5

    mesh = ax.pcolormesh(x_edges, y_edges, M_disp,
                         cmap="viridis", norm=norm, shading="flat",
                         rasterized=True)
    # Y axis: canonical PC 1 at TOP, large PCs at BOTTOM.  Log scale.
    ax.set_ylim(n_canon + 0.5, 0.5)        # inverted: 1 at top
    ax.set_yscale("log")
    # Plain PC indices (powers of two) rather than 10^k labels, so a row
    # such as k = 12 can be read off.
    yticks = [t for t in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512) if t <= n_canon]
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(t) for t in yticks])
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())
    ax.set_ylabel("Canonical PC index k\n(rows: contribution to decomposition)")

    # Strip boundaries (every cols_per_strip columns).
    pcs_in_order, w, styles, n_values = strip_layout(column_keys)
    for i in range(1, len(pcs_in_order)):
        ax.axvline(i * w, color="black", linewidth=0.6, alpha=0.4)
    # Within each strip, light dividers between the styles.
    per_style = w // max(len(styles), 1)
    for i in range(len(pcs_in_order)):
        for j in range(1, len(styles)):
            ax.axvline(i * w + j * per_style, color="white",
                       linewidth=0.4, alpha=0.5)
    # Red tick at k = N: where a winner equal to canonical PC N sits.
    if mark_target:
        for i, pc in enumerate(pcs_in_order):
            if pc <= n_canon:
                ax.hlines(pc, i * w, (i + 1) * w, colors="red",
                          linewidth=0.9, alpha=0.8)

    # X axis: strip centers labeled with PC index.
    strip_centers = [i * w + w / 2 for i in range(len(pcs_in_order))]
    ax.set_xticks(strip_centers)
    ax.set_xticklabels([str(pc) for pc in pcs_in_order])
    levels = ",".join(str(n) for n in n_values)
    strip_desc = " | ".join(f"{_STYLE_ABBREV.get(s, s)} n={levels}"
                            for s in styles)
    ax.set_xlabel(f"Target PC index N (each strip = {w} columns: {strip_desc}; "
                  f"n = best of the first n cells)")
    ax.set_xlim(0, n_cols)
    if title:
        ax.set_title(title, fontsize=11)
    return mesh


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--npz", default=DEFAULT_NPZ)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--max_canon_pc", type=int, default=0,
                   help="Limit y-axis range to top-N canonical PCs "
                        "(default 0 = use all rows in matrix).")
    p.add_argument("--linear_color", action="store_true",
                   help="Use linear color scale (default: log).")
    p.add_argument("--cache-policy", choices=CACHE_POLICIES, default="warn",
                   help="How to handle drift between the npz's recorded "
                        "inputs (winner_decomposition.py's upstream JSON + "
                        "data subtrees) and current state.  Default 'warn' "
                        "prints a stderr summary but renders anyway.")
    args = p.parse_args()

    inputs: list[InputSpec] = []
    data, meta, _spec, _check = load_and_register_npz(
        Path(args.npz),
        dep_key="winner_decomposition_npz",
        policy=args.cache_policy,
        inputs=inputs,
    )
    matrix = data["matrix"]
    column_keys = [(int(pc), str(s), int(n)) for pc, s, n in data["column_keys"]]
    meta = meta or {}

    # ~0.065 in per column, at least the old 15 in.
    width = max(15.0, 2.5 + 0.065 * len(column_keys))
    fig, ax = plt.subplots(figsize=(width, 7.5))
    mesh = render_heatmap(
        ax, matrix, column_keys,
        max_canon_pc=args.max_canon_pc,
        log_color=not args.linear_color,
    )
    cbar = fig.colorbar(mesh, ax=ax, fraction=0.025, pad=0.01)
    cbar.set_label("squared coefficient (column sums to 1)")

    # The title says which winners the columns are (meta["winners_source"])
    # and the canonical cell (L=0 raw since the May 2026 migration).  Until
    # 2026-10-12 it said "nth_pc winner ... (L=2 ...)" whatever the input.
    title = figure_title(meta)
    cells = meta.get("cell_order")
    n_cells = len(cells) if cells else "?"
    variant = (meta.get("winners_source") or {}).get("variant", "unknown")
    if variant == "nth_pc":
        what = ("Column (N, style, n): the index-N PC at the best-ρ "
                f"(cell, L, K) over the first n of {n_cells} cells (klm_sweep "
                "stage 2, M=∞).")
    else:
        what = ("Column (N, style, n): the index-N PC at the configuration "
                f"the {variant} search chose over the first n of {n_cells} "
                "cells.")
    spec = (
        f"{what}  Rows: its squared coefficient on canonical PC k, column "
        "sums to 1; red tick at k = N.\n"
        "Path: inverse whiten/shear at the winner cell → least-squares "
        "entity weights on that cell's raw matrix → same weights on the "
        f"canonical raw matrix → canonical L={CANONICAL_L} shear → "
        "decompose on canonical Vt."
    )
    _, top_rect = suptitle_with_specs(fig, title, spec, line_height=0.03)
    fig.tight_layout(rect=(0, 0, 1, top_rect))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # The npz can't carry a JSON envelope, so the transitive
    # provenance chain (back to per-cell-winners JSON + data
    # subtrees) lives inside its ``meta`` block; load_and_register_npz
    # validated that block above and registered the npz itself as our
    # one declared dependency in ``inputs``.  PNG metadata records
    # that single dep_key; downstream auditors recover the chain by
    # opening the npz and reading meta["_inputs"].
    fig.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title, inputs=inputs))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
