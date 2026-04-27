#!/usr/bin/env python3
"""4-panel grouped bar chart: per-slot mean Spearman ρ vs whitening level
for two judge sources (desc+inst and GPT responses).

For each slot ∈ {0, 1, 2, 3} and each K ∈ {0, 1, 2, 3, 4, 5} we compute
the mean per-axis Spearman ρ between the soft-K-whitened activation
projection at ``(slot, layer=24)`` and two score sources:

- **desc+inst** -- 33 axes (``pair_list_33.json``), score per entity is
  the 4-way mean of ``GPT_d, GPT_i, Son_d, Son_i``;
- **responses** -- 12 axes (``pair_list_12.json``), score per entity
  is the GPT-only mean over response-mode evals.

K=0 means raw projections (no whitening); K>0 uses soft-K whitening
fit on the augmented held-out pool from
:mod:`results_analysis.canonical_angles.data` (held-out = the 2
endpoints of each axis pair).

The plot is a grouped histogram with one panel per slot, two source
groups per panel, and ``len(KS)`` bars per group (raw + soft-K).
Legend laid out as ``len(KS)`` columns × 2 rows so the (source, K)
combinations form a small explicit matrix.

Inputs (from ``--experiment_dir``)
----------------------------------

The standard per-axis directory tree produced by
:mod:`results_analysis.axis_judge_correlation`::

    <experiment_dir>/
      pair_list_33.json     # or any pair list passed via --pairs_di
      pair_list_12.json     # or any pair list passed via --pairs_resp
      <pos>_vs_<neg>/
        gpt/scores_{descriptions,instructions}.json
        sonnet/scores_{descriptions,instructions}.json
        gpt_responses_traits/scores_responses.json   # 12-axis subset
        gpt_responses_roles/scores_responses.json    # 12-axis subset

Plus the standard activation-vectors directory passed via ``--data_dir``.

Output (to ``--experiment_dir``)
--------------------------------

- ``rho_by_slot_and_K.png`` -- the plot.

Examples
--------

::

    # Default: KS = [0, 1, 2, 3, 4, 5], 33 + 12 axis pair lists
    uv run python results_analysis/rho_by_slot_and_K.py

    # Custom K range
    uv run python results_analysis/rho_by_slot_and_K.py --ks 0 2 4 8 16
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch
from scipy.stats import spearmanr

from assistant_axis import png_metadata
from results_analysis.axis_judge_correlation import _load_vector_file
from results_analysis.canonical_angles.data import (
    build_augmented_whitening_pool,
)
from results_analysis.canonical_angles.whitening import fit_whitening


DEFAULT_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent / (
    "roger/axis_judge_experiments"
)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / (
    "runpod_workspace/qwen/qwen-3-32b Roger"
)
LAYER = 24
SLOTS = [0, 1, 2, 3]
DEFAULT_KS = [0, 1, 2, 3, 4, 5]


def _load_at(path: Path, slot: int) -> np.ndarray:
    return _load_vector_file(path).float()[slot, LAYER].numpy()


def _axis_unit_at(data_dir: Path, pos: str, neg: str, slot: int) -> np.ndarray:
    p = _load_at(data_dir / "traits" / "vectors" / f"{pos}.pt", slot)
    n = _load_at(data_dir / "traits" / "vectors" / f"{neg}.pt", slot)
    d = p - n
    return d / np.linalg.norm(d)


def _build_entity_cache(
    data_dir: Path, slots: list[int]
) -> dict[int, dict[str, np.ndarray]]:
    """Default-centered (slot, layer) entity vectors for traits + roles."""
    defaults = {
        s: _load_at(data_dir / "traits" / "vectors" / "default.pt", s)
        for s in slots
    }
    cache: dict[int, dict[str, np.ndarray]] = {s: {} for s in slots}
    for et in ("traits", "roles"):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem == "default":
                continue
            try:
                t = _load_vector_file(fp).float()
            except Exception:  # pragma: no cover -- skip unreadable files
                continue
            for s in slots:
                v = t[s, LAYER].numpy()
                cache[s][fp.stem] = v - defaults[s]
    return cache


class _Whitener:
    """Cache soft-K whiteners keyed by (slot, K, frozenset(leave_out))."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self._cache: dict[tuple[int, int, frozenset], object] = {}

    def get(self, slot: int, K: int, leave_out_names: frozenset):
        if K == 0:
            return None
        key = (slot, K, leave_out_names)
        if key in self._cache:
            return self._cache[key]
        leave_out = set()
        for n in leave_out_names:
            leave_out.add(("traits", n))
            leave_out.add(("roles", n))
        pool_entries = build_augmented_whitening_pool(
            self.data_dir, leave_out=leave_out, scope="roles+traits")
        rows = []
        for (et, n) in pool_entries:
            sub = "combinations" if et == "combinations" else et
            path = self.data_dir / sub / "vectors" / f"{n}.pt"
            try:
                rows.append(_load_vector_file(path).float()[slot, LAYER].numpy())
            except Exception:  # pragma: no cover
                pass
        pool = np.stack(rows, axis=0)
        basis = fit_whitening("soft_K", pool, K=K)
        self._cache[key] = basis
        return basis


def _project(
    entity_vecs: dict[int, dict[str, np.ndarray]],
    whitener: _Whitener,
    slot: int,
    K: int,
    axis_unit: np.ndarray,
    names: list[str],
    leave_out_names: frozenset,
) -> dict[str, float]:
    basis = whitener.get(slot, K, leave_out_names)
    if basis is None:
        return {n: float(np.dot(entity_vecs[slot][n], axis_unit))
                for n in names if n in entity_vecs[slot]}
    axis_w = basis.apply(axis_unit[None, :])[0]
    axis_n = float(np.linalg.norm(axis_w))
    out: dict[str, float] = {}
    for n in names:
        v = entity_vecs[slot].get(n)
        if v is None:
            continue
        vw = basis.apply(v[None, :])[0]
        out[n] = float(np.dot(vw, axis_w)) / axis_n
    return out


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR),
                   help=f"Directory with pair lists and per-axis score "
                        f"subdirs (default: {DEFAULT_EXPERIMENT_DIR}).")
    p.add_argument("--data_dir", default=str(DEFAULT_DATA_DIR),
                   help=f"Activation vectors directory "
                        f"(default: {DEFAULT_DATA_DIR}).")
    p.add_argument("--pairs_di", default="pair_list_33.json",
                   help="Pair-list JSON for desc+inst source "
                        "(default: pair_list_33.json -- every axis with "
                        "desc+inst from both providers).")
    p.add_argument("--pairs_resp", default="pair_list_12.json",
                   help="Pair-list JSON for GPT responses source "
                        "(default: pair_list_12.json).")
    p.add_argument("--ks", type=int, nargs="+", default=DEFAULT_KS,
                   help=f"K values to plot; 0 = raw, K>0 = soft-K "
                        f"whitening (default: {DEFAULT_KS}).")
    p.add_argument("--plot", default="rho_by_slot_and_K.png",
                   help="Output plot filename "
                        "(default: rho_by_slot_and_K.png).")
    args = p.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    KS: list[int] = list(args.ks)

    pairs_di = json.load(open(experiment_dir / args.pairs_di))
    pairs_resp = json.load(open(experiment_dir / args.pairs_resp))
    print(f"Loaded {len(pairs_di)} desc+inst axis pairs from {args.pairs_di}")
    print(f"Loaded {len(pairs_resp)} responses axis pairs from {args.pairs_resp}")

    print("Caching entity vectors at 4 slots...", flush=True)
    entity_vecs = _build_entity_cache(data_dir, SLOTS)
    whitener = _Whitener(data_dir)

    results: dict = {"desc_inst": {}, "responses": {}}

    print("\nComputing desc+inst ρ...", flush=True)
    for slot in SLOTS:
        for K in KS:
            rhos: list[float] = []
            for it in pairs_di:
                pos, neg = it["pos"], it["neg"]
                axis_dir = experiment_dir / f"{pos}_vs_{neg}"
                g_d = json.load(open(axis_dir / "gpt" / "scores_descriptions.json"))
                g_i = json.load(open(axis_dir / "gpt" / "scores_instructions.json"))
                s_d = json.load(open(axis_dir / "sonnet" / "scores_descriptions.json"))
                s_i = json.load(open(axis_dir / "sonnet" / "scores_instructions.json"))
                common = sorted(set(g_d) & set(g_i) & set(s_d) & set(s_i))
                scores = {n: (g_d[n] + g_i[n] + s_d[n] + s_i[n]) / 4
                          for n in common}
                au = _axis_unit_at(data_dir, pos, neg, slot)
                proj = _project(entity_vecs, whitener, slot, K, au, common,
                                frozenset({pos, neg}))
                names = sorted(set(scores) & set(proj))
                if len(names) < 3:
                    continue
                x = np.array([scores[n] for n in names])
                y = np.array([proj[n] for n in names])
                rhos.append(spearmanr(x, y).correlation)
            results["desc_inst"][(slot, K)] = (float(np.mean(rhos)), len(rhos))
            print(f"  desc_inst slot={slot} K={K}: "
                  f"mean ρ = {np.mean(rhos):+.4f} (n={len(rhos)})", flush=True)

    print("\nComputing responses ρ...", flush=True)
    for slot in SLOTS:
        for K in KS:
            rhos = []
            for it in pairs_resp:
                pos, neg = it["pos"], it["neg"]
                axis_dir = experiment_dir / f"{pos}_vs_{neg}"
                scores: dict[str, float] = {}
                for sub in ("gpt_responses_traits", "gpt_responses_roles"):
                    fp = axis_dir / sub / "scores_responses.json"
                    if not fp.exists():
                        continue
                    for n, info in json.load(open(fp)).items():
                        if info.get("mean_score") is not None:
                            scores[n] = info["mean_score"]
                if not scores:
                    continue
                common = sorted(scores)
                au = _axis_unit_at(data_dir, pos, neg, slot)
                proj = _project(entity_vecs, whitener, slot, K, au, common,
                                frozenset({pos, neg}))
                names = sorted(set(scores) & set(proj))
                if len(names) < 3:
                    continue
                x = np.array([scores[n] for n in names])
                y = np.array([proj[n] for n in names])
                rhos.append(spearmanr(x, y).correlation)
            results["responses"][(slot, K)] = (float(np.mean(rhos)), len(rhos))
            print(f"  responses slot={slot} K={K}: "
                  f"mean ρ = {np.mean(rhos):+.4f} (n={len(rhos)})", flush=True)

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    SLOT_LABELS = ["Slot 0 (body mean)", "Slot 1 (<|im_start|>)",
                   "Slot 2 (assistant)", "Slot 3 (\\n)"]
    K_LABELS = ["raw"] + [f"K={K}" for K in KS[1:]]
    n_K = len(KS)
    # Smooth dark→light gradient with a floor at ~0.32 so the lightest
    # shade is still readable against white.
    K_COLORS_DI = [plt.cm.Blues(v) for v in np.linspace(0.85, 0.32, n_K)]
    K_COLORS_RS = [plt.cm.Oranges(v) for v in np.linspace(0.85, 0.32, n_K)]

    fig, axes = plt.subplots(1, 4, figsize=(15, 5.5), sharey=True)
    x_labels = [f"desc+inst\n({len(pairs_di)} axes)",
                f"responses\n(GPT, {len(pairs_resp)} axes)"]
    x_pos = np.arange(len(x_labels))
    bar_width = 0.78 / n_K

    y_max = 0.0
    for slot, ax in zip(SLOTS, axes):
        di_rhos = [results["desc_inst"][(slot, K)][0] for K in KS]
        rs_rhos = [results["responses"][(slot, K)][0] for K in KS]
        y_max = max(y_max, max(di_rhos), max(rs_rhos))
        for ki in range(n_K):
            offset = (ki - (n_K - 1) / 2) * bar_width
            ax.bar(x_pos[0] + offset, di_rhos[ki], bar_width,
                   color=K_COLORS_DI[ki], edgecolor="black", linewidth=0.5)
            ax.bar(x_pos[1] + offset, rs_rhos[ki], bar_width,
                   color=K_COLORS_RS[ki], edgecolor="black", linewidth=0.5)
            ax.text(x_pos[0] + offset, di_rhos[ki] + 0.005,
                    f"{di_rhos[ki]:.3f}", ha="center", va="bottom",
                    fontsize=6, rotation=90)
            ax.text(x_pos[1] + offset, rs_rhos[ki] + 0.005,
                    f"{rs_rhos[ki]:.3f}", ha="center", va="bottom",
                    fontsize=6, rotation=90)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_labels, fontsize=9)
        ax.set_title(SLOT_LABELS[slot], fontsize=10)
        ax.grid(axis="y", alpha=0.3)
    for ax in axes:
        ax.set_ylim(0, y_max * 1.25)

    axes[0].set_ylabel("Mean per-axis Spearman ρ", fontsize=10)

    legend_handles = []
    legend_labels = []
    for ki, K_label in enumerate(K_LABELS):
        legend_handles.append(Patch(facecolor=K_COLORS_DI[ki], edgecolor="black"))
        legend_labels.append(f"desc+inst, {K_label}")
        legend_handles.append(Patch(facecolor=K_COLORS_RS[ki], edgecolor="black"))
        legend_labels.append(f"responses, {K_label}")
    fig.legend(legend_handles, legend_labels,
               loc="upper center", ncol=n_K, fontsize=8,
               bbox_to_anchor=(0.5, 0.96), frameon=True, framealpha=0.9,
               handlelength=1.4, columnspacing=1.2)
    title_line = (f"Mean per-axis ρ by slot, source, and whitening level "
                  f"(layer={LAYER}; desc+inst = {len(pairs_di)} axes, "
                  f"GPT+Sonnet 4-way mean; "
                  f"responses = {len(pairs_resp)} axes, GPT-only)")
    fig.suptitle(title_line, fontsize=10, y=1.01)
    plt.tight_layout(rect=(0, 0, 1, 0.88))

    out = experiment_dir / args.plot
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title_line))
    plt.close(fig)
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
