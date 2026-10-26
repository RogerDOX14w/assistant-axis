#!/usr/bin/env python3
"""How much do role vectors move when step 3's rubric changes?

Compares two versions of the same roles' step-4 vectors, built from the same
activations with scores from two judge rubrics (Roger, 2026-10-23: v3 against
v4 on the role rubric experiment's 30 roles).  For every slot, at one layer
(default 25, the analyses' standard), each role's vector minus the default
vector is soft-sheared (default L = DEFAULT_SOFT_SHEAR_L, fitted on the
goal / no-goal subspaces of ``--data-dir``, the pre-change May tree, since the
new extraction has none yet) and the two versions are compared by cosine.  A
third version, the base rubric judged a second time (``--rerun``), gives the
judge's own noise for the same comparison.  Each role's change is set against
how many more or fewer of its responses the other rubric keeps (score 3).  The
step-5 axes (mean default minus mean role vector) of the two versions are
compared the same way.

Each version directory holds ``scores/<role>.json`` (step 3's score files) and
``vectors/<role>.pt`` (step 4's vectors, ``{"vector": (slots, layers, D)}``).

Usage:
    uv run python results_analysis/rubric_version_vector_change.py \\
        --base runpod_workspace/rubric_exp/versions/v3 \\
        --other runpod_workspace/rubric_exp/versions/v4 \\
        --rerun runpod_workspace/rubric_exp/versions/v3_rerun \\
        --default-vector runpod_workspace/rubric_exp/arm_vectors/default.pt \\
        --out-dir reports/pipeline/role_rubric_experiment
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from assistant_axis import json_metadata, png_metadata  # noqa: E402
from assistant_axis.entity_id import corpus_display_name  # noqa: E402
from assistant_axis.plot_metadata import suptitle_with_specs  # noqa: E402
from assistant_axis.plot_palette import kind_color, kind_marker, kind_text_color  # noqa: E402
from assistant_axis.provenance import (  # noqa: E402
    InputSpec, current_data_subtree_input, current_file_input, current_files_input,
)
from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces  # noqa: E402
from results_analysis.canonical_angles.whitening import DEFAULT_SOFT_SHEAR_L, fit_shear  # noqa: E402

DEFAULT_DATA_DIR = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot"
#: Plotted values below this are drawn at it: a role whose two kept sets are the same
#: has identical vectors and 1 - cos at float precision (~1e-16).
PLOT_FLOOR = 1e-7
SHEAR_SUBTREES = ("combinations/vectors/derived/marginals/r_goal",
                  "combinations/vectors/derived/marginals/r_nogoal",
                  "combinations/vectors/derived/marginals/t_goal",
                  "combinations/vectors/derived/marginals/t_nogoal",
                  "combinations/vectors/derived/axis")


def load_vector(path: Path) -> np.ndarray:
    import torch
    d = torch.load(path, map_location="cpu", weights_only=False)
    v = d["vector"] if isinstance(d, dict) else d
    return v.to(torch.float64).numpy()


def kept(path: Path) -> int:
    return sum(1 for v in json.loads(path.read_text()).values() if isinstance(v, int) and v == 3)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


def pair_stats(xb: np.ndarray, xo: np.ndarray, apply) -> dict:
    """Two versions of one role's default-centred vector: the cosine between
    them and the change in norm from ``xb`` to ``xo``, in percent, each both
    after ``apply`` (the soft-shear) and raw (Roger, 2026-10-26)."""
    sb, so = apply(xb), apply(xo)
    nb, no = float(np.linalg.norm(sb)), float(np.linalg.norm(so))
    return {"cos": cosine(sb, so), "cos_raw": cosine(xb, xo),
            "norm_base": nb, "norm_other": no, "norm_change_pct": 100 * (no / nb - 1),
            "norm_change_pct_raw": 100 * (float(np.linalg.norm(xo)) / float(np.linalg.norm(xb)) - 1)}


def spearman(x, y) -> tuple[float, float]:
    from scipy.stats import spearmanr
    r = spearmanr(x, y)
    return float(r.statistic), float(r.pvalue)


def compare(base: Path, other: Path, rerun: Path | None, default_vec: np.ndarray, data_dir: Path,
            layer: int, L: int, roles: list[str]) -> dict:
    vb = {r: load_vector(base / "vectors" / f"{r}.pt") for r in roles}
    vo = {r: load_vector(other / "vectors" / f"{r}.pt") for r in roles}
    vr = {r: load_vector(rerun / "vectors" / f"{r}.pt") for r in roles} if rerun else {}
    kb = {r: kept(base / "scores" / f"{r}.json") for r in roles}
    ko = {r: kept(other / "scores" / f"{r}.json") for r in roles}
    n_slots = default_vec.shape[0]
    slots = []
    for s in range(n_slots):
        shear = fit_shear(*build_goal_nogoal_subspaces(data_dir, s, layer, kind="combined"), L=L)
        d = default_vec[s, layer]
        rows = {}
        for r in roles:
            xb, xo = vb[r][s, layer] - d, vo[r][s, layer] - d
            row = {"kept_base": kb[r], "kept_other": ko[r], "delta_kept": ko[r] - kb[r],
                   **pair_stats(xb, xo, shear.apply)}
            if rerun:
                pr = pair_stats(xb, vr[r][s, layer] - d, shear.apply)
                row.update({"cos_rerun": pr["cos"], "cos_rerun_raw": pr["cos_raw"],
                            "norm_change_pct_rerun": pr["norm_change_pct"]})
            rows[r] = row
        # step 5's axis: mean default minus mean role vector (pipeline/5_axis.py)
        ab = d - np.mean([vb[r][s, layer] for r in roles], axis=0)
        ao = d - np.mean([vo[r][s, layer] for r in roles], axis=0)
        one_minus = [1 - rows[r]["cos"] for r in roles]
        delta = [rows[r]["delta_kept"] for r in roles]
        rho, p = spearman(delta, one_minus)
        rho_abs, p_abs = spearman([abs(x) for x in delta], one_minus)
        cos = [rows[r]["cos"] for r in roles]
        norm_pct = [rows[r]["norm_change_pct"] for r in roles]
        summary = {"median_1_minus_cos": float(np.median(one_minus)),
                   "mean_1_minus_cos": float(np.mean(one_minus)),
                   "median_1_minus_cos_raw": float(np.median([1 - rows[r]["cos_raw"] for r in roles])),
                   "cos_range": [min(cos), max(cos)],
                   "norm_change_pct_range": [min(norm_pct), max(norm_pct)],
                   "median_abs_norm_change_pct": float(np.median(np.abs(norm_pct))),
                   "spearman_delta_kept": [rho, p], "spearman_abs_delta_kept": [rho_abs, p_abs],
                   "axis_cos": cosine(shear.apply(ab), shear.apply(ao)), "axis_cos_raw": cosine(ab, ao)}
        if rerun:
            summary["median_1_minus_cos_rerun"] = float(np.median([1 - rows[r]["cos_rerun"] for r in roles]))
            cos_r = [rows[r]["cos_rerun"] for r in roles]
            norm_r = [rows[r]["norm_change_pct_rerun"] for r in roles]
            summary["cos_range_rerun"] = [min(cos_r), max(cos_r)]
            summary["norm_change_pct_range_rerun"] = [min(norm_r), max(norm_r)]
            summary["median_abs_norm_change_pct_rerun"] = float(np.median(np.abs(norm_r)))
            ar = d - np.mean([vr[r][s, layer] for r in roles], axis=0)
            summary["axis_cos_rerun"] = cosine(shear.apply(ab), shear.apply(ar))
            ratios = [(1 - rows[r]["cos"]) / (1 - rows[r]["cos_rerun"]) for r in roles
                      if 1 - rows[r]["cos_rerun"] > 0]
            summary["median_ratio_to_rerun"] = float(np.median(ratios)) if ratios else None
        slots.append({"slot": s, "summary": summary, "roles": rows})
    return {"layer": layer, "soft_shear_L": L, "roles": roles, "slots": slots}


def _label(ax, x, y, role, *, ha="left", dx=4, dy=0):
    ax.annotate(corpus_display_name(role, "roles"), (x, y), xytext=(dx if ha == "left" else -dx, dy),
                textcoords="offset points", ha=ha, va="center", fontsize=7.5,
                color=kind_text_color("role"), style="italic")


def plot_by_slot(res: dict, out: Path, title: str, spec: str, inputs, labels: tuple[str, str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(11, 6.2), constrained_layout=True)
    has_rerun = "cos_rerun" in next(iter(res["slots"][0]["roles"].values()))
    for sl in res["slots"]:
        s, rows = sl["slot"], sl["roles"]
        y = np.maximum([1 - r["cos"] for r in rows.values()], PLOT_FLOOR)
        x = s - (0.15 if has_rerun else 0) + rng.uniform(-0.07, 0.07, len(y))
        ax.scatter(x, y, s=22, marker=kind_marker("role"), facecolor=kind_color("role"),
                   edgecolor=kind_text_color("role"), linewidth=0.6, zorder=3,
                   label=f"{labels[0]} vs {labels[1]}" if s == 0 else None)
        ax.hlines(np.median(y), s - 0.3 if has_rerun else s - 0.2, s, color=kind_text_color("role"),
                  linewidth=2, zorder=4)
        if has_rerun:
            yr = np.maximum([1 - r["cos_rerun"] for r in rows.values()], PLOT_FLOOR)
            ax.scatter(s + 0.15 + rng.uniform(-0.07, 0.07, len(yr)), yr, s=18, marker="o",
                       facecolor="lightgrey", edgecolor="dimgrey", linewidth=0.6, zorder=2,
                       label=f"{labels[0]} judged twice (judge noise)" if s == 0 else None)
            ax.hlines(np.median(yr), s, s + 0.3, color="dimgrey", linewidth=2, zorder=4)
        # most-changed role in each slot
        top = max(rows, key=lambda r: 1 - rows[r]["cos"])
        _label(ax, s - (0.15 if has_rerun else 0) + 0.08, max(1 - rows[top]["cos"], PLOT_FLOOR), top)
    ax.set_yscale("log")
    ax.set_xticks(range(len(res["slots"])))
    ax.set_xticklabels([f"slot {sl['slot']}" for sl in res["slots"]])
    ax.set_ylabel("1 − cos(vector change)   [log scale]")
    ax.grid(axis="y", color="#e6e6e6", linewidth=0.6, which="both")
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="#dddddd", fontsize=9)
    _, top_rect = suptitle_with_specs(fig, title, spec)
    fig.get_layout_engine().set(rect=(0, 0, 1, top_rect))
    fig.savefig(out, dpi=150, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)


def plot_vs_kept(res: dict, out: Path, title: str, spec: str, inputs, labels: tuple[str, str]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    slots = res["slots"]
    ncol = 4
    nrow = -(-len(slots) // ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(17, 4.1 * nrow + 1.2), sharex=True, sharey=True,
                             constrained_layout=True)
    axes = np.atleast_2d(axes)
    all_y = [max(1 - r["cos"], PLOT_FLOOR) for sl in slots for r in sl["roles"].values()]
    for i, sl in enumerate(slots):
        ax = axes[i // ncol, i % ncol]
        rows = sl["roles"]
        names = list(rows)
        x = np.array([rows[r]["delta_kept"] for r in names])
        y = np.maximum([1 - rows[r]["cos"] for r in names], PLOT_FLOOR)
        ax.scatter(x, y, s=24, marker=kind_marker("role"), facecolor=kind_color("role"),
                   edgecolor=kind_text_color("role"), linewidth=0.6, zorder=3)
        if "median_1_minus_cos_rerun" in sl["summary"]:
            ax.axhline(sl["summary"]["median_1_minus_cos_rerun"], color="dimgrey", linewidth=1,
                       linestyle="--", zorder=1)
        order = np.argsort(y)
        for j, dy in zip(list(order[-2:]) + list(order[:1]), (-5, 5, 0)):
            _label(ax, x[j], y[j], names[j], ha="right" if x[j] > 0 else "left", dy=dy)
        rho, p = sl["summary"]["spearman_delta_kept"]
        rho_a, p_a = sl["summary"]["spearman_abs_delta_kept"]
        ax.set_title(f"slot {sl['slot']}\nρ(Δ kept) {rho:+.2f}, p={p:.2g};   ρ(|Δ kept|) {rho_a:+.2f}, "
                     f"p={p_a:.2g}", fontsize=8.5)
        ax.axvline(0, color="#cccccc", linewidth=0.8, zorder=0)
        ax.set_yscale("log")
        ax.set_ylim(min(all_y) * 0.7, max(all_y) * 1.6)
        ax.grid(color="#eeeeee", linewidth=0.6, which="both")
        ax.set_axisbelow(True)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        if i % ncol == 0:
            ax.set_ylabel("1 − cos   [log]")
        if i // ncol == nrow - 1:
            ax.set_xlabel(f"responses kept: {labels[1]} − {labels[0]}")
    _, top_rect = suptitle_with_specs(fig, title, spec)
    fig.get_layout_engine().set(rect=(0, 0, 1, top_rect))
    fig.savefig(out, dpi=150, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--base", type=Path, required=True, help="version directory (scores/, vectors/)")
    p.add_argument("--other", type=Path, required=True)
    p.add_argument("--rerun", type=Path, help="the base rubric judged again: the judge-noise reference")
    p.add_argument("--base-label", default="v3")
    p.add_argument("--other-label", default="v4")
    p.add_argument("--default-vector", type=Path, required=True)
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                   help="tree whose goal / no-goal subspaces fit the soft-shear (default: the May 8slot tree)")
    p.add_argument("--layer", type=int, default=25)
    p.add_argument("--L", type=int, default=DEFAULT_SOFT_SHEAR_L)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--prefix", default="version_vector_change")
    args = p.parse_args()

    roles = sorted(f.stem for f in (args.base / "vectors").glob("*.pt") if f.stem != "default")
    missing = [r for r in roles for d in filter(None, (args.other, args.rerun))
               if not (d / "vectors" / f"{r}.pt").exists() or not (d / "scores" / f"{r}.json").exists()]
    if missing:
        raise SystemExit(f"missing vectors or scores: {sorted(set(missing))}")
    labels = (args.base_label, args.other_label)
    extras = {"layer": str(args.layer), "L": str(args.L), "base": args.base_label, "other": args.other_label}
    inputs: list[InputSpec] = [current_file_input(dep_key="producer_script", path=Path(__file__).resolve(),
                                                  extras=extras),
                               current_file_input(dep_key="default_vector", path=args.default_vector)]
    for tag, d in (("base", args.base), ("other", args.other), ("rerun", args.rerun)):
        if d is not None:
            inputs.append(current_files_input(dep_key=f"{tag}_vectors",
                                              paths=sorted((d / "vectors").glob("*.pt"))))
            inputs.append(current_files_input(dep_key=f"{tag}_scores",
                                              paths=sorted((d / "scores").glob("*.json"))))
    for sub in SHEAR_SUBTREES:
        inputs.append(current_data_subtree_input(args.data_dir, sub,
                                                 dep_key="shear_" + sub.rsplit("/", 1)[-1]))

    default_vec = load_vector(args.default_vector)
    res = compare(args.base, args.other, args.rerun, default_vec, args.data_dir, args.layer, args.L, roles)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    title = f"Role vectors under the {labels[0]} and {labels[1]} judge rubrics"
    out_json = args.out_dir / f"{args.prefix}.json"
    out_json.write_text(json.dumps(json_metadata(res, inputs=inputs, title=title), indent=1) + "\n")
    spec = (f"{len(roles)} roles, same activations; each vector minus the default vector, layer "
            f"{args.layer}, soft-shear L={args.L} fitted on the May tree; 1 − cos between the two versions "
            f"(floored at {PLOT_FLOOR:g}: identical kept sets)")
    plot_by_slot(res, args.out_dir / f"{args.prefix}_by_slot.png",
                 f"{title}: change per slot", spec, inputs, labels)
    plot_vs_kept(res, args.out_dir / f"{args.prefix}_vs_kept.png",
                 f"{title}: change against responses kept",
                 spec + "; dashed: median for the base rubric judged twice", inputs, labels)
    for sl in res["slots"]:
        s = sl["summary"]
        print(f"slot {sl['slot']}: median 1-cos {s['median_1_minus_cos']:.2e}"
              + (f" (judged twice {s['median_1_minus_cos_rerun']:.2e}, x{s['median_ratio_to_rerun']:.1f})"
                 if "median_1_minus_cos_rerun" in s else "")
              + f"; rho(delta kept) {s['spearman_delta_kept'][0]:+.2f} p={s['spearman_delta_kept'][1]:.2g}"
              f"; axis cos {s['axis_cos']:.5f}")
        print(f"   cos {s['cos_range'][0]:.5f} to {s['cos_range'][1]:.5f}; norm change "
              f"{s['norm_change_pct_range'][0]:+.2f}% to {s['norm_change_pct_range'][1]:+.2f}% "
              f"(median |change| {s['median_abs_norm_change_pct']:.2f}%)"
              + (f"; judged twice: cos {s['cos_range_rerun'][0]:.5f} to {s['cos_range_rerun'][1]:.5f}, norm "
                 f"{s['norm_change_pct_range_rerun'][0]:+.2f}% to {s['norm_change_pct_range_rerun'][1]:+.2f}%"
                 if "cos_range_rerun" in s else ""))
    print(f"wrote {out_json} and the two plots beside it")


if __name__ == "__main__":
    main()
