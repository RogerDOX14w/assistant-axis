#!/usr/bin/env python3
"""Visualise (K, L, slot/layer) winner consistency: actual vs null.

Three panels in a single figure:
- Top: K winners (actual + null cloud)
- Middle: L winner distribution per PC (actual + null histogram)
- Bottom: (slot, layer) winner distribution per PC

If the actual data is finding real structure, we expect concentrated
winners; if it's noise, we expect dispersed winners.  This figure makes
that comparison visual.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from assistant_axis.plot_metadata import png_metadata, suptitle_with_specs
from assistant_axis.provenance import (
    CACHE_POLICIES, InputSpec, load_and_register,
)

DEFAULT_ACTUAL = "roger/pc_round_trip_klm_results.json"
DEFAULT_NULL = "roger/pc_round_trip_null_klm_results.json"
DEFAULT_OUTPUT = "roger/pc_round_trip_winner_consistency.png"

# One colour per klm_sweep cell.  Same palette as
# plot_global_winner_cosines.py; the 7-cell post-May-2026 set
# (klm_sweep.DEFAULT_CONFIGS) replaced the 3-cell map here, under which
# four of the seven cells all fell through to grey (review 2026-10-12).
CONFIG_COLORS = {
    (7, 25): "#4c72b0", (7, 49): "#55a868",
    (6, 25): "#c44e52", (6, 49): "#dd8452",
    (0, 26): "#8172b2", (0, 49): "#937860", (3, 25): "#888888",
}


def _l_values(*winner_maps: dict) -> list[int]:
    """Every L that won anywhere, sorted -- so each PC's stacked L bar
    sums to 1.  (A fixed ``[0, 1, 2, 3, 5]`` grid silently dropped the
    L=4 winners of klm_sweep's ``[0, 1, 2, 4]`` grid; review 2026-10-12.)
    """
    return sorted({int(v["L"]) for m in winner_maps for v in m.values()})


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--actual", default=DEFAULT_ACTUAL)
    p.add_argument("--null", default=DEFAULT_NULL)
    p.add_argument("--output", default=DEFAULT_OUTPUT)
    p.add_argument("--cache-policy", choices=CACHE_POLICIES, default="warn",
                   help="How to handle stale or unrecognized inputs JSON envelopes.")
    args = p.parse_args()

    actual_path = Path(args.actual)
    null_path = Path(args.null)
    inputs: list[InputSpec] = []
    actual_full, _spec_a, _check_a = load_and_register(
        actual_path, dep_key="klm_results_json",
        inputs=inputs, policy=args.cache_policy,
    )
    null_full, _spec_n, _check_n = load_and_register(
        null_path, dep_key="null_klm_results_json",
        inputs=inputs, policy=args.cache_policy,
    )
    actual = actual_full["stage2_K_refinement_M_inf"]
    null = null_full["stage2"]

    # Group winners per PC
    def gather(items):
        by_pc = {}
        for k, v in items.items():
            pc = int(k[2:5])
            by_pc.setdefault(pc, []).append(v)
        return by_pc

    actual_by_pc = gather(actual)
    null_by_pc = gather(null)
    pcs = sorted(actual_by_pc)

    fig, (ax_K, ax_L, ax_sl) = plt.subplots(3, 1, figsize=(11, 10))

    pc_pos = np.arange(len(pcs))  # categorical x position for all panels
    bar_width = 0.40

    # --- Panel 1: K winners (categorical x, log y) ---
    # Null cloud: jittered x for visibility
    rng = np.random.default_rng(0)
    for i, pc in enumerate(pcs):
        ks = [v["K"] for v in null_by_pc.get(pc, [])]
        if ks:
            jitter = rng.uniform(-0.18, 0.18, size=len(ks))
            ax_K.scatter(np.full(len(ks), i) + jitter, ks,
                          s=6, c="#c44e52", alpha=0.20,
                          edgecolors="none", zorder=2)
    # Actual: glossary + inline
    for i, pc in enumerate(pcs):
        for v in actual_by_pc[pc]:
            ax_K.scatter([i], [v["K"]], s=80, c="#4c72b0",
                          marker="o", edgecolors="black", linewidths=0.7,
                          zorder=5)
    # K=N reference line
    ax_K.plot(pc_pos, pcs, linestyle="--", color="#4c72b0",
               alpha=0.5, linewidth=1.2, label="K = N (PC index)", zorder=3)

    ax_K.set_yscale("symlog", linthresh=1)
    # 256 dropped 2026-10-12: its label sat on top of 512's.
    ax_K.set_yticks([0, 1, 4, 16, 64, 512])
    ax_K.set_yticklabels(["0", "1", "4", "16", "64", "512"])
    ax_K.set_xticks(pc_pos)
    ax_K.set_xticklabels([str(pc) for pc in pcs])
    ax_K.set_ylabel("Optimal K (winner)")
    ax_K.set_ylim(-0.5, 700)
    ax_K.set_xlim(-0.6, len(pcs) - 0.4)
    ax_K.grid(True, which="major", linestyle=":", alpha=0.3)
    ax_K.set_title("Optimal K vs PC index — actual (blue dots, 2/PC) "
                   "vs null (red cloud, 200/PC)",
                   fontsize=11)
    ax_K.legend(loc="upper left", fontsize=9, framealpha=0.9)

    # --- Panel 2: L winner stacked bars ---
    L_values = _l_values(actual, null)
    L_colors = plt.cm.viridis(np.linspace(0, 0.85, len(L_values)))

    # Null: stack L proportions
    null_L_dists = []
    for pc in pcs:
        c = Counter(v["L"] for v in null_by_pc.get(pc, []))
        total = sum(c.values()) or 1
        null_L_dists.append([c.get(L, 0) / total for L in L_values])
    null_L_dists = np.array(null_L_dists)

    # Actual: stack L proportions (only 2 entries per PC)
    actual_L_dists = []
    for pc in pcs:
        c = Counter(v["L"] for v in actual_by_pc[pc])
        total = sum(c.values()) or 1
        actual_L_dists.append([c.get(L, 0) / total for L in L_values])
    actual_L_dists = np.array(actual_L_dists)

    bottom_actual = np.zeros(len(pcs))
    bottom_null = np.zeros(len(pcs))
    for i, L in enumerate(L_values):
        ax_L.bar(pc_pos - bar_width/2, actual_L_dists[:, i],
                  width=bar_width, bottom=bottom_actual,
                  color=L_colors[i], edgecolor="black", linewidth=0.5,
                  label=f"L={L}" if i < len(L_values) else None)
        ax_L.bar(pc_pos + bar_width/2, null_L_dists[:, i],
                  width=bar_width, bottom=bottom_null,
                  color=L_colors[i], alpha=0.6, edgecolor="black",
                  linewidth=0.3)
        bottom_actual = bottom_actual + actual_L_dists[:, i]
        bottom_null = bottom_null + null_L_dists[:, i]

    ax_L.set_xticks(pc_pos)
    ax_L.set_xticklabels([str(pc) for pc in pcs])
    ax_L.set_xlim(-0.6, len(pcs) - 0.4)
    ax_L.set_ylabel("Fraction of L winners")
    ax_L.set_ylim(0, 1.05)
    ax_L.set_title("L winner distribution per PC — left bar = actual, "
                   "right bar = null (faded)", fontsize=11)
    # Legends outside the axes (2026-10-12): inside, they covered the bars
    # of the highest PCs.
    ax_L.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8,
                framealpha=0.9)

    # --- Panel 3: (slot, layer) winner stacked bars ---
    slot_layer_keys = sorted(set(
        (v["slot"], v["layer"]) for v in list(actual.values()) + list(null.values())
    ))
    null_sl_dists = []
    actual_sl_dists = []
    for pc in pcs:
        c_n = Counter((v["slot"], v["layer"]) for v in null_by_pc.get(pc, []))
        c_a = Counter((v["slot"], v["layer"]) for v in actual_by_pc[pc])
        total_n = sum(c_n.values()) or 1
        total_a = sum(c_a.values()) or 1
        null_sl_dists.append([c_n.get(sl, 0) / total_n for sl in slot_layer_keys])
        actual_sl_dists.append([c_a.get(sl, 0) / total_a for sl in slot_layer_keys])
    null_sl_dists = np.array(null_sl_dists)
    actual_sl_dists = np.array(actual_sl_dists)

    bottom_actual = np.zeros(len(pcs))
    bottom_null = np.zeros(len(pcs))
    for i, sl in enumerate(slot_layer_keys):
        color = CONFIG_COLORS.get(sl, "gray")
        ax_sl.bar(pc_pos - bar_width/2, actual_sl_dists[:, i],
                   width=bar_width, bottom=bottom_actual,
                   color=color, edgecolor="black", linewidth=0.5,
                   label=f"slot={sl[0]}, layer={sl[1]}")
        ax_sl.bar(pc_pos + bar_width/2, null_sl_dists[:, i],
                   width=bar_width, bottom=bottom_null,
                   color=color, alpha=0.6, edgecolor="black",
                   linewidth=0.3)
        bottom_actual = bottom_actual + actual_sl_dists[:, i]
        bottom_null = bottom_null + null_sl_dists[:, i]

    ax_sl.set_xticks(pc_pos)
    ax_sl.set_xticklabels([str(pc) for pc in pcs])
    ax_sl.set_xlim(-0.6, len(pcs) - 0.4)
    ax_sl.set_xlabel("PC index")
    ax_sl.set_ylabel("Fraction of (slot, layer) winners")
    ax_sl.set_ylim(0, 1.05)
    ax_sl.set_title("(slot, layer) winner distribution per PC — left = actual, "
                    "right = null (faded)", fontsize=11)
    ax_sl.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8,
                 framealpha=0.9)

    title = "K, L, (slot, layer) winner consistency: actual vs permutation null"
    # Until 2026-10-12 the spec read the panels as "evidence the actual
    # search is finding meaningful structure, not noise maxima" because the
    # actual winners (2 per PC) look concentrated next to the null's 200.
    # Two draws look concentrated whatever their source, and the null is a
    # different search (the cache's _meta.variant, fixed_principled since
    # May 9), so the spec now says what is plotted and draws no inference.
    null_variant = null_full.get("_meta", {}).get("variant") or "nth_pc"
    null_sizes = sorted({len(v) for v in null_by_pc.values()}) or [0]
    null_n = (str(null_sizes[0]) if len(null_sizes) == 1
              else f"{null_sizes[0]}–{null_sizes[-1]}")
    spec = (f"Actual: nth_pc search, global winner per description style "
            f"(sharp bars / blue dots, 2 per PC).  Null: {null_variant} search "
            f"on permuted judge scores (faded bars / red cloud, "
            f"{null_n} per PC).\n"
            "Compare where the winners sit, not how spread they are: 2 draws "
            "look concentrated whatever their source"
            + ("" if null_variant == "nth_pc" else
               f", and the null is the {null_variant} search's, not the "
               f"nth_pc search's own") + ".")
    _, top_rect = suptitle_with_specs(fig, title, spec)
    fig.tight_layout(rect=(0, 0, 1, top_rect))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # ``inputs`` was populated above by load_and_register.
    fig.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title, inputs=inputs))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
