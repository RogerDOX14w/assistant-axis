#!/usr/bin/env python3
"""GPT-vs-Anthropic *response*-mode weight sweep, analogous to
:mod:`results_analysis.gpt_sonnet_weight_sweep` for desc+inst judging.

For each axis we load the per-entity ``mean_score`` from
``<experiment_dir>/<axis>/<judge>_responses_{roles,traits}<suffix>/scores_responses.json``
for both judges (combined roles + traits sides), then sweep::

    score(w) = w · gpt_b10[name] + (1 − w) · anthropic[name]

over ``w ∈ [0, 1]``.  Per-axis Spearman ρ vs the raw activation
projection at ``(--slot, --layer)``.

Anthropic combo selectors (``--anthropic_combo``):
- ``haiku_q9``    → ``haiku_responses_{side}_b10_q9``    (1/3 question subsample)
- ``haiku_full``  → ``haiku_responses_{side}_b10``       (all questions)
- ``sonnet_q9``   → ``sonnet_responses_{side}_b10_q9``   (1/3 question subsample)

Outputs ``gpt_<combo>_response_weight_sweep_slot{N}.png`` + ``.json``
inside ``--experiment_dir``.

CLI
---

::

    # One sweep per Anthropic candidate (3 plots from 3 invocations).
    for combo in haiku_q9 haiku_full sonnet_q9; do
        uv run python -m results_analysis.gpt_anthropic_response_weight_sweep \\
            --anthropic_combo "$combo"
    done
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

from assistant_axis import entity_id, json_metadata, png_metadata
from assistant_axis.provenance import (
    InputSpec,
    current_data_subtree_input,
    current_file_input,
    load_and_register,
)
from results_analysis.axis_judge_correlation import _load_vector_file

_SCRIPT_PATH = Path(__file__).resolve()


# Axes available for response judging.  All 12 traits axes have GPT-B=10
# response judging on disk; sets 2..4 (axes 4..12) only have q9-subsampled
# Anthropic data, so the ``haiku_full`` combo will skip those nine axes
# and render just set 1.  Mirrors ``ALL_RESPONSE_AXES`` in
# :mod:`judge_ensemble_rho_curve` so the two stay in sync.
DEFAULT_AXES: list[tuple[str, str, str]] = [
    ("truthful_vs_deceitful",          "truthful",        "deceitful"),
    ("progressive_vs_conservative",    "progressive",     "conservative"),
    ("improvisational_vs_methodical",  "improvisational", "methodical"),
    ("concise_vs_verbose",             "concise",         "verbose"),
    ("ecocentric_vs_anthropocentric",  "ecocentric",      "anthropocentric"),
    ("egalitarian_vs_elitist",         "egalitarian",     "elitist"),
    ("guileless_vs_scheming",          "guileless",       "scheming"),
    ("harmless_vs_harmful",            "harmless",        "harmful"),
    ("honest_vs_dishonest",            "honest",          "dishonest"),
    ("helpful_vs_unhelpful",           "helpful",         "unhelpful"),
    ("relativist_vs_absolutist",       "relativist",      "absolutist"),
    ("systems_thinker_vs_analytical",  "systems_thinker", "analytical"),
]

DEFAULT_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent / (
    "roger/axis_judge_experiments"
)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / (
    "runpod_workspace/qwen/qwen-3-32b Roger 8slot"
)
DEFAULT_SLOT, DEFAULT_LAYER = 6, 25  # Match gpt_sonnet_weight_sweep.py default.

# Combo selector → (label, anthropic-dir-suffix-template).
COMBO_DIRS: dict[str, tuple[str, str]] = {
    "haiku_q9":   ("Haiku-q9",   "haiku_responses_{side}_b10_q9"),
    "haiku_full": ("Haiku-full", "haiku_responses_{side}_b10"),
    "sonnet_q9":  ("Sonnet-q9",  "sonnet_responses_{side}_b10_q9"),
}

# Per-axis colours (consistent across the 3 weight-sweep plots so that a
# given axis keeps the same colour regardless of how the slopes happen to
# sort within a plot).  12 independent colours -- no set-membership
# grouping (each axis stands alone visually).  Picked to stay distinct
# from the mean line (black), the w=0.5 reference line (grey), and the
# parabola fit colour (PARABOLA_COLOR below).  Falls back to the plasma
# colormap for axes not listed here.
AXIS_COLORS: dict[str, str] = {
    "truthful_vs_deceitful":         "#4c72b0",  # blue
    "progressive_vs_conservative":   "#55a868",  # green
    "improvisational_vs_methodical": "#c44e52",  # red
    "concise_vs_verbose":            "#8172b2",  # purple
    "ecocentric_vs_anthropocentric": "#dd8452",  # orange
    "egalitarian_vs_elitist":        "#937860",  # warm brown
    "guileless_vs_scheming":         "#da8bc3",  # pink
    "harmless_vs_harmful":           "#17becf",  # cyan
    "honest_vs_dishonest":           "#bcbd22",  # mustard
    "helpful_vs_unhelpful":          "#2c5d8c",  # navy
    "relativist_vs_absolutist":      "#b04a72",  # rose
    "systems_thinker_vs_analytical": "#6b4ec1",  # violet
}

GPT_DIR_TEMPLATE = "gpt_responses_{side}_b10"
PARABOLA_COLOR = "#1faa4f"


def _load_response_scores(
    experiment_dir: Path, axis: str, dir_template: str,
    *,
    scores_filename: str = "scores_responses.json",
    judge_label: str,
    inputs: list[InputSpec] | None = None,
) -> dict[str, float]:
    """Per-entity mean response-judge score, summed across roles + traits.

    Uses :func:`assistant_axis.provenance.load_and_register` to do the
    read + envelope-unwrap + drift-check + InputSpec construction in one
    call.  When ``inputs`` is supplied, every successfully-read cache is
    appended to it (so the caller can record exactly the dependencies
    actually consumed -- a missing per-side file results in no spec for
    that side, matching the old skip-on-missing behaviour).

    ``scores_filename`` defaults to the canonical cache name but can be
    overridden (e.g. ``scores_responses__rubric_v1.json``) so v1 and v2
    plots can be regenerated side-by-side from snapshotted data.
    ``judge_label`` (e.g. ``"gpt"``, ``"haiku_q9"``) is used to
    namespace the per-side ``dep_key`` so accumulated InputSpecs stay
    unique across both judges of a single sweep.
    """
    out: dict[str, float] = {}
    for side in ("roles", "traits"):
        sub = dir_template.format(side=side)
        path = experiment_dir / axis / sub / scores_filename
        if not path.exists():
            continue
        scores, _spec, _check = load_and_register(
            path,
            dep_key=f"scores_{judge_label}_{axis}_{side}",
            extras={"axis": axis, "side": side, "judge": judge_label},
            policy="warn",
            inputs=inputs,
        )
        for name, info in scores.items():
            ms = info.get("mean_score") if isinstance(info, dict) else None
            if ms is not None:
                out[entity_id(name, side)] = float(ms)
    return out


def _v(path: Path, slot: int, layer: int) -> torch.Tensor:
    return _load_vector_file(path).float()[slot, layer]


def _axis_unit(data_dir: Path, pos: str, neg: str,
               slot: int, layer: int) -> torch.Tensor:
    p = _v(data_dir / "traits" / "vectors" / f"{pos}.pt", slot, layer)
    n = _v(data_dir / "traits" / "vectors" / f"{neg}.pt", slot, layer)
    d = p - n
    nrm = torch.linalg.vector_norm(d)
    return d / nrm if nrm > 0 else d


def _rho_at_weight(d: dict, w: float) -> float:
    score = w * d["gpt"] + (1 - w) * d["anth"]
    return float(spearmanr(score, d["proj"]).correlation)


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--anthropic_combo", required=True,
                   choices=sorted(COMBO_DIRS.keys()),
                   help="Which Anthropic judge × subsampling combo to "
                        "compare GPT-4.1-mini against.")
    p.add_argument("--experiment_dir", default=str(DEFAULT_EXPERIMENT_DIR))
    p.add_argument("--data_dir", default=str(DEFAULT_DATA_DIR))
    p.add_argument("--slot", type=int, default=DEFAULT_SLOT)
    p.add_argument("--layer", type=int, default=DEFAULT_LAYER)
    p.add_argument("--plot", default=None,
                   help="Output PNG (default: gpt_<combo>_response_weight_"
                        "sweep_slot{N}.png inside --experiment_dir).")
    p.add_argument("--rhos_json", default=None)
    p.add_argument("--scores_filename", default="scores_responses.json",
                   help="Filename within each <axis>/<judge>_responses_*/ "
                        "subdir to read.  Use scores_responses__rubric_v1.json "
                        "to regenerate plots from the snapshotted v1 data "
                        "after a rubric version bump (see RUBRIC_VERSION in "
                        "axis_judge_correlation.py).  Default: canonical "
                        "scores_responses.json.")
    p.add_argument("--out_stem_suffix", default="",
                   help="Optional suffix appended to the output stem (e.g. "
                        "'__rubric_v1' to write "
                        "gpt_<combo>_response_weight_sweep_slot{N}__rubric_v1"
                        ".{json,png}).  Useful for v1<->v2 side-by-side "
                        "snapshots.  Default: empty (canonical names).")
    args = p.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    slot, layer = int(args.slot), int(args.layer)
    combo_label, anth_template = COMBO_DIRS[args.anthropic_combo]
    out_stem = (
        f"gpt_{args.anthropic_combo}_response_weight_sweep_slot{slot}"
        f"{args.out_stem_suffix}"
    )
    if args.plot is None:
        args.plot = f"{out_stem}.png"
    if args.rhos_json is None:
        args.rhos_json = f"{out_stem}.json"

    # Cache standalone entity vectors at (slot, layer), default-centered.
    default_v = _v(data_dir / "traits" / "vectors" / "default.pt", slot, layer)
    entity_vecs: dict[str, np.ndarray] = {}
    for et in ("traits", "roles"):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem == "default":
                continue
            try:
                v = _load_vector_file(fp).float()[slot, layer]
                entity_vecs[entity_id(fp.stem, et)] = (v - default_v).numpy()
            except Exception:  # pragma: no cover -- skip unreadable files
                continue

    print(f"GPT-4.1-mini B=10 vs {combo_label} response-mode weight sweep, "
          f"slot {slot} layer {layer}")
    print(f"  axes: {[a[0] for a in DEFAULT_AXES]}")
    print(f"  anthropic dir template: {anth_template}")

    # Provenance accumulator.  Threaded through every cache read so the
    # output JSON's _provenance.inputs reflects exactly the files this
    # run actually consumed.  Includes the producer script (this file)
    # and the entity-vector subtrees up front; per-axis scores caches
    # are appended inside ``_load_response_scores`` via load_and_register.
    inputs: list[InputSpec] = [
        current_file_input(
            dep_key="producer_script",
            path=_SCRIPT_PATH,
            extras={
                "anthropic_combo": args.anthropic_combo,
                "scores_filename": args.scores_filename,
                "slot": str(slot), "layer": str(layer),
            },
        ),
        current_data_subtree_input(
            data_dir=data_dir, subtree_rel="traits/vectors",
            dep_key="traits_vectors",
        ),
        current_data_subtree_input(
            data_dir=data_dir, subtree_rel="roles/vectors",
            dep_key="roles_vectors",
        ),
    ]

    per_axis: dict[tuple[str, str], dict] = {}
    for axis_name, pos, neg in DEFAULT_AXES:
        gpt = _load_response_scores(
            experiment_dir, axis_name, GPT_DIR_TEMPLATE,
            scores_filename=args.scores_filename,
            judge_label="gpt_b10",
            inputs=inputs,
        )
        anth = _load_response_scores(
            experiment_dir, axis_name, anth_template,
            scores_filename=args.scores_filename,
            judge_label=args.anthropic_combo,
            inputs=inputs,
        )
        if not gpt or not anth:
            print(f"  [skip] {axis_name}: gpt n={len(gpt)} "
                  f"anth n={len(anth)}")
            continue
        common = sorted(set(gpt) & set(anth) & set(entity_vecs))
        if len(common) < 5:
            print(f"  [skip] {axis_name}: only {len(common)} shared entities")
            continue
        gpt_arr = np.array([gpt[n] for n in common])
        anth_arr = np.array([anth[n] for n in common])
        a = _axis_unit(data_dir, pos, neg, slot, layer).numpy()
        proj = np.array([float(np.dot(entity_vecs[n], a)) for n in common])
        per_axis[(pos, neg)] = {
            "axis_name": axis_name,
            "gpt": gpt_arr, "anth": anth_arr, "proj": proj,
            "n": len(common),
        }
        print(f"  {axis_name}: n={len(common)} "
              f"(pure GPT ρ={_rho_at_weight(per_axis[(pos, neg)], 1.0):+.4f}, "
              f"pure {combo_label} ρ="
              f"{_rho_at_weight(per_axis[(pos, neg)], 0.0):+.4f})")

    if not per_axis:
        print("No axes had data; exiting.")
        return 1

    # Sort axes by interior slope Δρ = ρ(0.9) − ρ(0.1) (Anthropic-best to
    # GPT-best), matching the original sweep's colour convention.
    slopes = {k: _rho_at_weight(d, 0.9) - _rho_at_weight(d, 0.1)
              for k, d in per_axis.items()}
    sorted_keys = sorted(per_axis.keys(), key=lambda k: slopes[k])
    per_axis = {k: per_axis[k] for k in sorted_keys}

    ws = np.linspace(0.0, 1.0, 21)
    all_rhos = np.array([
        [_rho_at_weight(d, w) for d in per_axis.values()]
        for w in ws
    ])
    mean_rhos = all_rhos.mean(axis=1)

    # Parabolic fit on interior [0.1, 0.9] only (endpoint kinks distort
    # a global fit when w=0 / w=1 = single judge regime).
    mask = (ws >= 0.10 - 1e-9) & (ws <= 0.90 + 1e-9)
    ws_fit = ws[mask]
    mean_fit = mean_rhos[mask]
    c, b, a = np.polyfit(ws_fit, mean_fit, 2)
    yhat = a + b * ws_fit + c * ws_fit ** 2
    ss_res = float(((mean_fit - yhat) ** 2).sum())
    ss_tot = float(((mean_fit - mean_fit.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    if c < 0:
        w_peak = float(-b / (2 * c))
        rho_peak = float(a + b * w_peak + c * w_peak ** 2)
    else:
        i_best = int(np.argmax(mean_rhos))
        w_peak = float(ws[i_best])
        rho_peak = float(mean_rhos[i_best])

    print(f"\nSweep summary ({len(per_axis)} axes):")
    print(f"  pure {combo_label} (w=0):    mean ρ = {mean_rhos[0]:+.4f}")
    print(f"  50/50         (w=0.5):  mean ρ = {mean_rhos[10]:+.4f}")
    print(f"  pure GPT      (w=1):    mean ρ = {mean_rhos[-1]:+.4f}")
    print(f"  parabolic peak (interior fit, R²={r2:.3f}): "
          f"w={w_peak:.3f}, ρ ≈ {rho_peak:+.4f}")

    # ---- Plot ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9.5, 7.0))
    n_axes = len(per_axis)
    keys = list(per_axis.keys())
    # Per-axis colours from the global ``AXIS_COLORS`` lookup so that a
    # given axis keeps the same colour across all three Anthropic combo
    # plots (the slope-based sort order can flip the position of an
    # axis between plots; fixed colours preserve cross-plot identity).
    # Fall back to plasma for any axis not in the lookup.
    fallback = plt.cm.plasma(np.linspace(0.05, 0.80, max(n_axes, 2)))
    colors = [
        AXIS_COLORS.get(per_axis[k]["axis_name"], fallback[i])
        for i, k in enumerate(keys)
    ]

    for j, k in enumerate(keys):
        ax.plot(ws, all_rhos[:, j], color=colors[j], lw=1.2, alpha=0.85)

    mean_handle, = ax.plot(
        ws, mean_rhos, color="black", lw=2.5, marker="o", markersize=5,
        zorder=20, label=f"mean ({n_axes} axes)")

    ws_in = np.linspace(0.10, 0.90, 50)
    ws_out = np.linspace(0.0, 1.0, 100)
    y_in = a + b * ws_in + c * ws_in ** 2
    y_out = a + b * ws_out + c * ws_out ** 2
    extrap_handle, = ax.plot(
        ws_out, y_out, color="#444444", lw=1.0, ls=":",
        alpha=0.9, zorder=25, label="parabola (extrapolated)")
    fit_handle, = ax.plot(
        ws_in, y_in, color=PARABOLA_COLOR, lw=2.0, ls="-",
        alpha=0.95, zorder=26,
        label=f"parabola fit on [0.1, 0.9] (R²={r2:.3f})")
    w50_handle = ax.axvline(0.5, color="grey", linestyle=":", lw=1,
                              alpha=0.7, label="w=0.5")
    peak_handle = ax.axvline(
        w_peak, color=PARABOLA_COLOR, linestyle="--", lw=1.4,
        label=f"interior peak w={w_peak:.3f}")

    ax.set_xlabel(f"Weight on GPT-4.1-mini B=10\n"
                  f"(remaining on {combo_label})", fontsize=10)
    ax.set_ylabel(f"Per-axis Spearman ρ "
                  f"(slot {slot}, layer {layer}, raw)", fontsize=10)
    title = (f"GPT-4.1-mini B=10 / {combo_label} response-mode score-blend "
             f"sweep — mean ρ across {n_axes} axes")
    initial = combo_label[0]
    ax.set_title(
        title + "\n"
        f"{initial}={mean_rhos[0]:.3f}  50/50={mean_rhos[10]:.3f}  "
        f"G={mean_rhos[-1]:.3f}",
        fontsize=13, fontweight="bold",
    )
    ax.set_xticks([0.0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlim(-0.02, 1.02)
    y_hi = float(min(1.0, all_rhos.max() + 0.02))
    y_lo = float(max(0.0, all_rhos.min() - 0.02))
    ax.set_ylim(y_lo, y_hi)
    ax.grid(alpha=0.3)

    axis_handles = [
        plt.Line2D([], [], color=colors[i], lw=1.2, alpha=0.85)
        for i in range(n_axes)
    ]
    axis_labels = [
        f"{per_axis[k]['axis_name']} (Δ{slopes[k]:+.3f})"
        for k in keys
    ]
    leg_axes = ax.legend(
        axis_handles, axis_labels,
        loc="upper left", bbox_to_anchor=(1.01, 0.98),
        fontsize=9, ncol=1, frameon=True, framealpha=0.9,
        handlelength=1.5, borderpad=0.6, labelspacing=0.32)
    ax.add_artist(leg_axes)
    ax.annotate(
        f"Axes: sorted {combo_label}-best to GPT-best",
        xy=(1.01, 1.005), xycoords="axes fraction",
        ha="left", va="bottom", fontsize=10, fontweight="bold")
    ax.legend(
        [mean_handle, fit_handle, extrap_handle, w50_handle, peak_handle],
        [mean_handle.get_label(), fit_handle.get_label(),
         extrap_handle.get_label(), w50_handle.get_label(),
         peak_handle.get_label()],
        loc="lower left", bbox_to_anchor=(1.01, 0.0),
        fontsize=8, frameon=True, framealpha=0.9, handlelength=1.5)
    plt.tight_layout()

    out_path = experiment_dir / args.plot
    plt.savefig(out_path, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
    print(f"\nWrote {out_path}")

    # ---- JSON ------------------------------------------------------------
    json_payload = {
        "n_axes": n_axes,
        "first_judge": "gpt_b10",
        "second_judge_label": combo_label,
        "anthropic_combo": args.anthropic_combo,
        "anthropic_dir_template": anth_template,
        "slot": slot, "layer": layer,
        "ws": [float(w) for w in ws],
        "mean_rho_by_w": [float(v) for v in mean_rhos],
        "parabola_fit": {
            "domain": [0.10, 0.90],
            "a": float(a), "b": float(b), "c": float(c),
            "r2": float(r2),
            "peak_w": float(w_peak), "peak_rho": float(rho_peak),
        },
        "per_axis": [
            {"axis_name": per_axis[k]["axis_name"],
             "pos": k[0], "neg": k[1],
             "interior_slope_delta_rho": float(slopes[k]),
             "rho_by_w": [float(v) for v in all_rhos[:, i]],
             "n": int(per_axis[k]["n"])}
            for i, k in enumerate(keys)
        ],
    }
    json_out = json_metadata(
        json_payload, title=title, inputs=inputs,
    )
    json_path = experiment_dir / args.rhos_json
    json_path.write_text(json.dumps(json_out, indent=2))
    print(f"Wrote {json_path} ({len(inputs)} inputs recorded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
