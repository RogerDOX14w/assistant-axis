#!/usr/bin/env python3
"""For each axis pair, vary the whitening K and compute Spearman ρ between
judge scores and the projection of entity vectors onto the axis at K.

Per axis we report two ρ-vs-K curves:

- ``desc_inst`` -- per entity, combine (GPT-descriptions,
  GPT-instructions, Sonnet-descriptions, Sonnet-instructions) via
  :func:`assistant_axis.judge_score_combine.combine_desc_inst_two_judges`
  (default: inst-tiebreak weighting `0.499*desc + 0.501*inst`; pass
  ``--di_weights {inst_tie,equal,desc_tie}`` to override), then ρ vs
  the projection.
- ``responses`` -- GPT response-mode mean score per entity, then ρ vs
  the projection.  (Roles and traits are merged when both are scored.)

Soft-K whitening is fit on the same augmented pool the canonical-angles
tool uses (held-out roles+traits standalones plus ``default.pt``;
:func:`results_analysis.canonical_angles.data.build_augmented_whitening_pool`),
with leave-out reduced to just the 2 pair endpoints (since this is a
single-axis projection task, not a residual-subspace task).  An A/B
test on 12 axes confirmed switching to this shared pool helper
changes ρ values by ≤0.007 at K ≤ 16 and ≤0.016 at K=128 (mean 0.002)
-- well below judge noise.  Using the shared helper keeps the
whitening infrastructure consistent across both tools.

Inputs
------

The script expects the following layout in ``--experiment_dir``:

::

    <experiment_dir>/
        <pairs>.json              # list of {pos, neg, ...}; default pair_list_12.json
        <pos>_vs_<neg>/
            gpt/scores_descriptions.json
            gpt/scores_instructions.json
            sonnet/scores_descriptions.json
            sonnet/scores_instructions.json
            gpt_responses_traits/scores_responses.json
            gpt_responses_roles/scores_responses.json

These are produced by
:mod:`results_analysis.axis_judge_correlation` (see its README section).

Outputs (also written to ``--experiment_dir``)
----------------------------------------------

- ``<sweep>.json`` (default ``whitening_k_sweep.json``): a list of
  ``{pos, neg, source, K, rho}`` records (one per axis x source x K).
- ``rho_vs_whitening_K.png``: an N-line overlay plot (one solid line per
  axis for ``responses``, one dotted line per axis for ``desc_inst``)
  with K on the x-axis (categorical positions ``raw, 1, 2, 4, 8, 16,
  32, 64, 128``).

Examples
--------

::

    # Default: 12 axes (pair_list_12.json), all 9 K values
    uv run python results_analysis/whitening_k_sweep.py

    # Use the historical 7-axis subset (matches the original April 23 plot)
    uv run python results_analysis/whitening_k_sweep.py --pairs pair_list_7.json

    # Custom experiment directory
    uv run python results_analysis/whitening_k_sweep.py \\
        --experiment_dir /tmp/my_axis_experiments
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

from assistant_axis import png_metadata, suptitle_with_specs
from assistant_axis.judge_score_combine import (
    add_di_weights_arg,
    combine_desc_inst_two_judges,
    parse_di_weights_arg,
)
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
LAYER = 25  # Qwen-3-32B; tuned via rho_by_layer.py.  Other models TBD.
SLOT = 3
K_VALUES = [0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32]


def load_pool(data_dir: Path, exclude_names: set[str]):
    """Build the held-out whitening pool for an axis-judge run.

    Returns ``(entity_vecs, pool, default_sl)`` where:

    - ``entity_vecs`` -- dict ``{name: tensor at (SLOT, LAYER)}`` for
      every standalone role + trait, with ``default.pt`` SUBTRACTED so
      projections are taken in the default-centered frame.
    - ``pool`` -- (n, hidden) numpy array used to fit the soft-K
      whitener; built via
      :func:`results_analysis.canonical_angles.data.build_augmented_whitening_pool`
      with ``leave_out = {("traits", n), ("roles", n) for n in exclude_names}``
      so only the pair endpoints are removed.  This is the same pool
      builder used by the canonical-angles tool, but with a different
      leave-out convention appropriate to a single-axis projection
      task: hold out ONLY the 2 names that defined the axis direction,
      not the 30+30 names that anchor a residual subspace.
    - ``default_sl`` -- the default activation at (SLOT, LAYER), used
      for centering.

    A/B test on 12 axes confirmed switching to this pool helper
    changes ρ values by at most 0.004 (mean 0.0006) -- well below
    judge noise.  Switching over keeps the whitening infrastructure
    consistent across both tools.
    """
    default = _load_vector_file(
        data_dir / "traits" / "vectors" / "default.pt").float()
    default_sl = default[SLOT, LAYER]

    entity_vecs: dict[str, torch.Tensor] = {}
    for etype in ("traits", "roles"):
        vdir = data_dir / etype / "vectors"
        if not vdir.exists():
            continue
        for f in sorted(vdir.glob("*.pt")):
            if f.stem == "default":
                continue
            try:
                v = _load_vector_file(f).float()
            except Exception:  # pragma: no cover -- skip unreadable files
                continue
            entity_vecs[f.stem] = v[SLOT, LAYER] - default_sl

    # Build the pool via the canonical-angles helper.  Pass leave-out
    # entries for both etypes since we don't know which one the pair
    # endpoints live in (build_augmented_whitening_pool silently
    # ignores names that don't exist in a given etype).
    leave_out: set[tuple[str, str]] = set()
    for n in exclude_names:
        leave_out.add(("traits", n))
        leave_out.add(("roles", n))
    pool_entries = build_augmented_whitening_pool(
        data_dir, leave_out=leave_out, scope="roles+traits")

    def _path(etype: str, name: str) -> Path:
        if etype == "combinations":
            return data_dir / "combinations" / "vectors" / f"{name}.pt"
        return data_dir / etype / "vectors" / f"{name}.pt"

    pool_rows = [
        _load_vector_file(_path(et, n)).float()[SLOT, LAYER].numpy()
        for (et, n) in pool_entries
    ]
    pool = np.stack(pool_rows, axis=0)
    return entity_vecs, pool, default_sl


def axis_direction(data_dir: Path, pos: str, neg: str) -> torch.Tensor:
    """Load pair vectors and return the unit axis direction at (SLOT, LAYER)."""
    vp = _load_vector_file(data_dir / "traits" / "vectors" / f"{pos}.pt").float()
    vn = _load_vector_file(data_dir / "traits" / "vectors" / f"{neg}.pt").float()
    d = vp[SLOT, LAYER] - vn[SLOT, LAYER]
    d = d / torch.linalg.vector_norm(d)
    return d


def project_at_K(entity_vecs, pool, axis_unit: torch.Tensor, K: int) -> dict:
    """Return ``{name: float projection}`` under a soft-K whitener fit
    on ``pool``.  ``K=0`` means raw (no whitening).

    ``pool`` is a ``(n, hidden)`` numpy array; the canonical-angles
    :func:`fit_whitening` mean-centres it internally before SVD.  We
    apply the whitener to default-centred entity vectors and the unit
    axis direction.
    """
    if K == 0:
        return {n: float((v @ axis_unit).item())
                for n, v in entity_vecs.items()}
    basis = fit_whitening("soft_K", pool, K=K)
    axis_np = axis_unit.numpy()
    axw = basis.apply(axis_np[None, :])[0]
    axw_n = float(np.linalg.norm(axw))
    proj: dict[str, float] = {}
    for n, v in entity_vecs.items():
        vw = basis.apply(v.numpy()[None, :])[0]
        proj[n] = float(np.dot(vw, axw)) / axw_n
    return proj


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR),
                   help=f"Directory holding pair lists, per-axis "
                        f"score subdirs, and the JSON/PNG outputs "
                        f"(default: {DEFAULT_EXPERIMENT_DIR}).")
    p.add_argument("--data_dir", default=str(DEFAULT_DATA_DIR),
                   help=f"Activation-vectors directory "
                        f"(default: {DEFAULT_DATA_DIR}).")
    p.add_argument("--pairs", default="pair_list_12.json",
                   help="Pair-list JSON filename within --experiment_dir "
                        "(default: pair_list_12.json -- the 12 axes that "
                        "have desc+inst from both providers AND GPT "
                        "response scores cached on disk).")
    p.add_argument("--sweep", default="whitening_k_sweep.json",
                   help="Output JSON filename within --experiment_dir "
                        "(default: whitening_k_sweep.json).")
    p.add_argument("--plot", default="rho_vs_whitening_K.png",
                   help="Output PNG filename within --experiment_dir "
                        "(default: rho_vs_whitening_K.png).")
    add_di_weights_arg(p)
    args = p.parse_args()
    di_weights = parse_di_weights_arg(args.di_weights)
    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()

    pairs = json.load(open(experiment_dir / args.pairs))
    print(f"Loaded {len(pairs)} axis pairs from {args.pairs}")

    data: dict = {}
    for it in pairs:
        pos, neg = it["pos"], it["neg"]
        axis_dir = experiment_dir / f"{pos}_vs_{neg}"
        print(f"[{pos} vs {neg}] loading...")

        # --- Scores ---
        g_d = json.load(open(axis_dir / "gpt" / "scores_descriptions.json"))
        g_i = json.load(open(axis_dir / "gpt" / "scores_instructions.json"))
        s_d = json.load(open(axis_dir / "sonnet" / "scores_descriptions.json"))
        s_i = json.load(open(axis_dir / "sonnet" / "scores_instructions.json"))
        desc_inst = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i,
                                                 weights=di_weights)

        # Response scores merged from traits + roles GPT runs
        resp_t = json.load(open(axis_dir / "gpt_responses_traits" / "scores_responses.json"))
        resp_r = json.load(open(axis_dir / "gpt_responses_roles" / "scores_responses.json"))
        responses = {}
        for src in (resp_t, resp_r):
            for n, info in src.items():
                if info.get("mean_score") is not None:
                    responses[n] = info["mean_score"]

        # --- Projections at each K ---
        entity_vecs, pool, _default = load_pool(
            data_dir, exclude_names={pos, neg})
        axis_unit = axis_direction(data_dir, pos, neg)
        projections_by_K = {K: project_at_K(entity_vecs, pool, axis_unit, K)
                            for K in K_VALUES}

        data[(pos, neg)] = {
            "desc_inst": desc_inst,
            "responses": responses,
            "projections_by_K": projections_by_K,
        }

    # --- Compute ρ per (axis, source, K) ---
    rho_table: dict[tuple[str, str, str], list[float]] = {}
    for (pos, neg), d in data.items():
        for source_name, score_map in [("desc_inst", d["desc_inst"]),
                                       ("responses", d["responses"])]:
            rhos: list[float] = []
            for K in K_VALUES:
                proj = d["projections_by_K"][K]
                names = sorted(set(score_map) & set(proj))
                if len(names) < 3:
                    rhos.append(float("nan"))
                    continue
                x = np.array([score_map[n] for n in names], dtype=float)
                y = np.array([proj[n] for n in names], dtype=float)
                rhos.append(spearmanr(x, y).correlation)
            rho_table[(pos, neg, source_name)] = rhos
            print(f"  {pos:16s} vs {neg:16s}  {source_name:9s}  rhos: "
                  + "  ".join(f"{r:+.3f}" for r in rhos))

    # --- Save JSON ---
    records = []
    for (pos, neg, source), rhos in rho_table.items():
        for K, r in zip(K_VALUES, rhos):
            records.append({"pos": pos, "neg": neg, "source": source,
                            "K": K, "rho": r})
    sweep_path = experiment_dir / args.sweep
    json.dump(records, open(sweep_path, "w"), indent=2)
    print(f"\nWrote {len(records)} records to {sweep_path}")

    # --- Plot ---
    pair_keys = [(it["pos"], it["neg"]) for it in pairs]
    axis_colors = plt.cm.tab20(np.linspace(0, 1, max(20, len(pair_keys))))

    fig, ax = plt.subplots(figsize=(11, 8))
    x_pos = np.arange(len(K_VALUES))
    for i, (pos, neg) in enumerate(pair_keys):
        color = axis_colors[i % 20]
        ax.plot(x_pos, rho_table[(pos, neg, "responses")], color=color, lw=2,
                linestyle="-", marker="o", markersize=5,
                label=f"{pos}/{neg} (responses)")
        ax.plot(x_pos, rho_table[(pos, neg, "desc_inst")], color=color, lw=1.5,
                linestyle=":", marker="s", markersize=4,
                label=f"{pos}/{neg} (desc+inst)")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(["raw\n(K=0)"] + [str(K) for K in K_VALUES[1:]])
    ax.set_xlabel("Soft-whitening K (raw = no whitening; higher K = more PCs scaled down)")
    ax.set_ylabel(f"Spearman ρ (judge scores vs. projection, slot={SLOT})")
    title_line = f"ρ vs whitening K across {len(pair_keys)} axes"
    spec_line = ("solid = GPT responses; "
                 "dotted = desc+inst (GPT+Sonnet averaged)")
    _, top_rect = suptitle_with_specs(fig, title_line, spec_line)
    ax.axhline(0, color="grey", lw=0.5)
    ax.grid(alpha=0.3)
    ax.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7,
              ncol=1)
    plt.tight_layout(rect=(0, 0, 1, top_rect))
    plot_path = experiment_dir / args.plot
    plt.savefig(plot_path, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title_line))
    plt.close(fig)
    print(f"Wrote {plot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
