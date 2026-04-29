#!/usr/bin/env python3
"""2x2 panel plot: per-layer mean Spearman ρ vs transformer layer for
two slots × two judge sources, with raw + soft-K whitening overlaid.

Rows are slot 0 (body mean) and slot 3 (the canonical
``\\n``-after-``assistant`` header position).  Columns are the two
judge sources used elsewhere in the project:

- **desc+inst** -- 33 axes (``pair_list_33.json``), 4-way mean of
  ``GPT_d, GPT_i, Son_d, Son_i``;
- **responses** -- 12 axes (``pair_list_12.json``), GPT-only mean
  over response-mode evals.

For each (slot, layer, K) we compute mean per-axis Spearman ρ between
the soft-K-whitened activation projection at ``(slot, layer)`` and the
score for each axis.  K=0 = raw (no whitening); K>0 = soft-K
whitening fit on the augmented held-out pool from
:mod:`results_analysis.canonical_angles.data` (held-out = the 2
endpoints of the axis pair).  This is the same convention as
``rho_by_slot_and_K.py`` and ``whitening_k_sweep.py``.

Default Ks are ``[0, 1, 2, 3, 4, 5, 6]`` plotted as black (raw) +
full RGB rainbow (K=1 purple → K=6 red).

Performance note: the SVD that powers soft-K whitening is computed
*once* per (slot, layer, leave-out-set) and shared across all K
values, so going from 6 K values to 7 (or more) costs almost
nothing.  The dominant cost is N_layers × N_slots × N_unique_pairs
SVDs (~4k for the default 64-layer × 2-slot × 33-pair sweep).

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
        gpt_responses_traits/scores_responses.json
        gpt_responses_roles/scores_responses.json

Plus the standard activation-vectors directory passed via ``--data_dir``.

Outputs (to ``--experiment_dir``)
---------------------------------

- ``rho_by_layer.png`` -- the 2x2 panel plot.
- ``rho_by_layer.json`` -- per-(slot, layer, K, source) mean ρ table,
  written alongside the PNG so the plot can be re-rendered cheaply
  via ``--replot_from_json``.

Examples
--------

::

    # Default: all layers, slots 0+3, Ks = [0,1,2,3,4,6,8]
    uv run python results_analysis/rho_by_layer.py

    # Faster: a coarse layer subset
    uv run python results_analysis/rho_by_layer.py --layers 4 8 12 16 20 24 28 32 36 40 44 48 52 56 60

    # Cheap: re-render the plot from the cached JSON sidecar
    # (does NOT recompute; useful for tweaking colors / gridlines).
    uv run python results_analysis/rho_by_layer.py --replot_from_json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr

from assistant_axis import png_metadata
from results_analysis.axis_judge_correlation import _load_vector_file
from results_analysis.canonical_angles.data import (
    build_augmented_whitening_pool,
)


DEFAULT_EXPERIMENT_DIR = Path(__file__).resolve().parent.parent / (
    "roger/axis_judge_experiments"
)
DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / (
    "runpod_workspace/qwen/qwen-3-32b Roger"
)
SLOTS = [0, 3]
SLOT_LABELS = {0: "Slot 0 (body mean)", 3: "Slot 3 (\\n)"}
DEFAULT_KS = [0, 1, 2, 3, 4, 5, 6]


def _slot_index(slot: int) -> int:
    """Map original slot id (0 or 3) to its position in the loaded array."""
    return SLOTS.index(slot)


def _load_full_tensor(path: Path) -> np.ndarray:
    """Load and slice an entity tensor down to (n_kept_slots, n_layers, hidden)."""
    t = _load_vector_file(path).float().numpy()  # (n_slots, n_layers, hidden)
    return t[SLOTS]  # (len(SLOTS), n_layers, hidden)


def _build_entity_cache(
    data_dir: Path,
) -> tuple[dict[str, np.ndarray], np.ndarray, int]:
    """Pre-load (default-centered) (n_slots, n_layers, hidden) per entity.

    Returns ``(entity_vecs, default_array, n_layers)``.  ``entity_vecs``
    keys are entity stems for both traits and roles (excluding default).
    """
    default_path = data_dir / "traits" / "vectors" / "default.pt"
    default_arr = _load_full_tensor(default_path)
    n_layers = default_arr.shape[1]
    vecs: dict[str, np.ndarray] = {}
    for et in ("traits", "roles"):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem == "default":
                continue
            try:
                arr = _load_full_tensor(fp)
            except Exception:  # pragma: no cover -- skip unreadable files
                continue
            vecs[fp.stem] = arr - default_arr
    return vecs, default_arr, n_layers


def _build_pool_cache(
    data_dir: Path, default_arr: np.ndarray
) -> dict[tuple[str, str], np.ndarray]:
    """Cache pool-entry tensors at the kept slots/layers, NOT default-centered.

    Pool entries come from :func:`build_augmented_whitening_pool` and may
    include ``("traits", "default")`` as a separate row.
    """
    cache: dict[tuple[str, str], np.ndarray] = {
        ("traits", "default"): default_arr,
    }
    for et in ("traits", "roles"):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem == "default":
                continue
            try:
                cache[(et, fp.stem)] = _load_full_tensor(fp)
            except Exception:  # pragma: no cover
                continue
    return cache


def _all_K_bases(pool: np.ndarray, ks: list[int]) -> dict[int, dict]:
    """Compute one SVD on ``pool`` and derive a soft-K basis per K.

    Returns ``{K: {"Vt": (K, D) or None, "scales": (K,) or None}}``.
    K=0 yields ``None`` (raw).  Output ``Vt`` rows are the right
    singular vectors of the *centered* pool.  ``scales[k]`` is
    ``S[K_max] / S[k]`` -- but we recompute per K below to match
    ``fit_whitening``'s convention exactly.
    """
    out: dict[int, dict] = {}
    centered = pool - pool.mean(axis=0, keepdims=True)
    _U, S, Vt = np.linalg.svd(centered, full_matrices=False)
    for K in ks:
        if K == 0:
            out[K] = {"Vt": None, "scales": None}
            continue
        if K >= len(S):
            out[K] = {"Vt": None, "scales": None}  # treat as raw
            continue
        target_sigma = float(S[K])
        scales = target_sigma / np.maximum(S[:K], 1e-12)
        out[K] = {
            "Vt": Vt[:K].astype(np.float64),
            "scales": scales.astype(np.float64),
        }
    return out


def _apply(basis: dict, X: np.ndarray) -> np.ndarray:
    """Apply a basis dict to ``X`` (vector or 2-D matrix)."""
    if basis["Vt"] is None:
        return X
    if X.ndim == 1:
        return _apply(basis, X[None, :])[0]
    Vt = basis["Vt"]
    scales = basis["scales"]
    coefs = X @ Vt.T
    adjustments = (coefs * (scales - 1.0)) @ Vt
    return X + adjustments


def _project(
    entity_vecs: dict[str, np.ndarray],
    basis: dict,
    slot_i: int,
    layer: int,
    axis_unit: np.ndarray,
    names: list[str],
) -> dict[str, float]:
    if basis["Vt"] is None:
        return {n: float(np.dot(entity_vecs[n][slot_i, layer], axis_unit))
                for n in names if n in entity_vecs}
    axis_w = _apply(basis, axis_unit)
    axis_n = float(np.linalg.norm(axis_w))
    out: dict[str, float] = {}
    for n in names:
        v = entity_vecs.get(n)
        if v is None:
            continue
        vw = _apply(basis, v[slot_i, layer])
        out[n] = float(np.dot(vw, axis_w)) / axis_n
    return out


def _bases_for_pair(
    pool_cache: dict,
    pool_entries: list[tuple[str, str]],
    slot_i: int,
    layer: int,
    ks: list[int],
) -> dict[int, dict]:
    """Build the (slot, layer)-specific pool from pool_entries and
    return one basis per K."""
    rows = []
    for entry in pool_entries:
        arr = pool_cache.get(entry)
        if arr is None:
            continue
        rows.append(arr[slot_i, layer])
    pool = np.stack(rows, axis=0)
    return _all_K_bases(pool, ks)


def _axis_unit(
    entity_vecs: dict[str, np.ndarray],
    pos: str, neg: str, slot_i: int, layer: int,
) -> np.ndarray:
    """Unit vector pointing pos − neg, computed from default-centered
    entity vectors (= pos.pt − neg.pt since the +/− default cancel)."""
    p = entity_vecs[pos][slot_i, layer]
    n = entity_vecs[neg][slot_i, layer]
    d = p - n
    return d / np.linalg.norm(d)


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
                        "(default: pair_list_33.json).")
    p.add_argument("--pairs_resp", default="pair_list_12.json",
                   help="Pair-list JSON for GPT responses source "
                        "(default: pair_list_12.json).")
    p.add_argument("--ks", type=int, nargs="+", default=DEFAULT_KS,
                   help=f"K values to plot; 0 = raw, K>0 = soft-K "
                        f"whitening (default: {DEFAULT_KS}).")
    p.add_argument("--layers", type=int, nargs="+", default=None,
                   help="Transformer layers to sweep (default: all "
                        "layers in the activation tensor).")
    p.add_argument("--plot", default="rho_by_layer.png",
                   help="Output plot filename (default: rho_by_layer.png).")
    p.add_argument("--rhos_json", default="rho_by_layer.json",
                   help="Sidecar JSON filename "
                        "(default: rho_by_layer.json).")
    p.add_argument("--replot_from_json", action="store_true",
                   help="Skip all computation and re-render the plot "
                        "directly from --rhos_json.  Useful for tweaking "
                        "colors / gridlines without paying the SVD cost.")
    p.add_argument("--reuse_json", action="store_true",
                   help="Reuse cached (slot, layer, K, source) ρ values "
                        "from --rhos_json (filtered to the current "
                        "--ks/--layers/--slots), and only compute the "
                        "missing entries.  Use this when adding/removing "
                        "K values from the sweep.  The merged result is "
                        "rewritten to --rhos_json.")
    args = p.parse_args()

    experiment_dir = Path(args.experiment_dir).resolve()
    data_dir = Path(args.data_dir).resolve()
    KS: list[int] = list(args.ks)

    if args.replot_from_json:
        json_path = experiment_dir / args.rhos_json
        print(f"Loading cached results from {json_path}", flush=True)
        cached = json.load(open(json_path))
        layers: list[int] = list(cached["layers"])
        KS = list(cached["ks"])
        n_di = int(cached["n_axes_di"])
        n_rs = int(cached["n_axes_resp"])
        rho_by_di = {(int(slot), int(L), int(K)): float(v)
                     for slot, L, K, v in cached["desc_inst"]}
        rho_by_rs = {(int(slot), int(L), int(K)): float(v)
                     for slot, L, K, v in cached["responses"]}
        _render_plot(experiment_dir, args.plot, layers, KS, SLOTS,
                     rho_by_di, rho_by_rs, n_di, n_rs)
        return 0

    pairs_di = json.load(open(experiment_dir / args.pairs_di))
    pairs_resp = json.load(open(experiment_dir / args.pairs_resp))
    print(f"Loaded {len(pairs_di)} desc+inst axis pairs from {args.pairs_di}")
    print(f"Loaded {len(pairs_resp)} responses axis pairs from {args.pairs_resp}")

    print("Loading entity tensors (slots 0 + 3, all layers)...", flush=True)
    entity_vecs, default_arr, n_layers = _build_entity_cache(data_dir)
    pool_cache = _build_pool_cache(data_dir, default_arr)
    print(f"  cached {len(entity_vecs)} entities, n_layers={n_layers}")

    layers: list[int] = list(args.layers) if args.layers is not None \
        else list(range(n_layers))
    print(f"Sweeping {len(layers)} layers × {len(SLOTS)} slots "
          f"× {len(KS)} Ks", flush=True)

    # Pre-cache pool entries per leave-out set (a frozenset of stems).
    # Both desc+inst pairs and responses pairs use leave_out = {pos, neg}.
    leave_out_sets: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for it in pairs_di + pairs_resp:
        pos, neg = it["pos"], it["neg"]
        if (pos, neg) in leave_out_sets:
            continue
        leave_out = set()
        for n in (pos, neg):
            leave_out.add(("traits", n))
            leave_out.add(("roles", n))
        leave_out_sets[(pos, neg)] = build_augmented_whitening_pool(
            data_dir, leave_out=leave_out, scope="roles+traits")

    # Index: rho[(slot, layer, K, source)] = mean ρ across axes.
    rho_by_di: dict[tuple[int, int, int], float] = {}
    rho_by_rs: dict[tuple[int, int, int], float] = {}

    if args.reuse_json:
        json_path = experiment_dir / args.rhos_json
        if json_path.exists():
            cached = json.load(open(json_path))
            keep = set((s, L, K) for s in SLOTS for L in layers for K in KS)
            for slot, L, K, v in cached.get("desc_inst", []):
                key = (int(slot), int(L), int(K))
                if key in keep:
                    rho_by_di[key] = float(v)
            for slot, L, K, v in cached.get("responses", []):
                key = (int(slot), int(L), int(K))
                if key in keep:
                    rho_by_rs[key] = float(v)
            n_cached = len(rho_by_di) + len(rho_by_rs)
            n_total = 2 * len(SLOTS) * len(layers) * len(KS)
            print(f"Reusing {n_cached}/{n_total} cached (slot, layer, K, "
                  f"source) entries from {json_path}", flush=True)
        else:
            print(f"--reuse_json set but {json_path} does not exist; "
                  "computing everything from scratch.", flush=True)

    # Pre-load per-axis score arrays (don't reread on every layer).
    print("Loading per-axis scores...", flush=True)
    axis_scores_di: dict[tuple[str, str], dict[str, float]] = {}
    for it in pairs_di:
        pos, neg = it["pos"], it["neg"]
        axis_dir = experiment_dir / f"{pos}_vs_{neg}"
        try:
            g_d = json.load(open(axis_dir / "gpt" / "scores_descriptions.json"))
            g_i = json.load(open(axis_dir / "gpt" / "scores_instructions.json"))
            s_d = json.load(open(axis_dir / "sonnet" / "scores_descriptions.json"))
            s_i = json.load(open(axis_dir / "sonnet" / "scores_instructions.json"))
        except FileNotFoundError:
            continue
        common = sorted(set(g_d) & set(g_i) & set(s_d) & set(s_i))
        axis_scores_di[(pos, neg)] = {
            n: (g_d[n] + g_i[n] + s_d[n] + s_i[n]) / 4 for n in common
        }
    axis_scores_rs: dict[tuple[str, str], dict[str, float]] = {}
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
        if scores:
            axis_scores_rs[(pos, neg)] = scores

    for slot in SLOTS:
        slot_i = _slot_index(slot)
        for li, layer in enumerate(layers):
            ks_missing_di = [K for K in KS
                             if (slot, layer, K) not in rho_by_di]
            ks_missing_rs = [K for K in KS
                             if (slot, layer, K) not in rho_by_rs]
            ks_to_fit = sorted(set(ks_missing_di) | set(ks_missing_rs))
            if not ks_to_fit:
                print(f"  slot={slot} layer={layer} cached "
                      f"({li + 1}/{len(layers)})", flush=True)
                continue

            # Per-layer per-pair bases (one SVD per pair → all needed K).
            # K=0 is a no-op so skipping it doesn't help; non-zero Ks all
            # share the same SVD, so we always pass the full ks_to_fit.
            bases_per_pair: dict[tuple[str, str], dict[int, dict]] = {}
            for pair, pool_entries in leave_out_sets.items():
                bases_per_pair[pair] = _bases_for_pair(
                    pool_cache, pool_entries, slot_i, layer, ks_to_fit)

            for K in ks_to_fit:
                if K in ks_missing_di:
                    rhos_di: list[float] = []
                    for pair, scores in axis_scores_di.items():
                        pos, neg = pair
                        au = _axis_unit(entity_vecs, pos, neg, slot_i, layer)
                        proj = _project(entity_vecs, bases_per_pair[pair][K],
                                        slot_i, layer, au, list(scores))
                        names = sorted(set(scores) & set(proj))
                        if len(names) < 3:
                            continue
                        x = np.array([scores[n] for n in names])
                        y = np.array([proj[n] for n in names])
                        rhos_di.append(spearmanr(x, y).correlation)
                    rho_by_di[(slot, layer, K)] = float(np.mean(rhos_di))

                if K in ks_missing_rs:
                    rhos_rs: list[float] = []
                    for pair, scores in axis_scores_rs.items():
                        pos, neg = pair
                        au = _axis_unit(entity_vecs, pos, neg, slot_i, layer)
                        proj = _project(entity_vecs, bases_per_pair[pair][K],
                                        slot_i, layer, au, list(scores))
                        names = sorted(set(scores) & set(proj))
                        if len(names) < 3:
                            continue
                        x = np.array([scores[n] for n in names])
                        y = np.array([proj[n] for n in names])
                        rhos_rs.append(spearmanr(x, y).correlation)
                    rho_by_rs[(slot, layer, K)] = float(np.mean(rhos_rs))

            print(f"  slot={slot} layer={layer} done "
                  f"({li + 1}/{len(layers)}, fit Ks={ks_to_fit})", flush=True)

    # ------------------------------------------------------------------
    # JSON sidecar (so future replots are cheap)
    # ------------------------------------------------------------------
    json_out = {
        "layers": list(layers),
        "ks": list(KS),
        "slots": list(SLOTS),
        "n_axes_di": len(axis_scores_di),
        "n_axes_resp": len(axis_scores_rs),
        "desc_inst": [
            [int(slot), int(L), int(K), float(rho_by_di[(slot, L, K)])]
            for slot in SLOTS for L in layers for K in KS
        ],
        "responses": [
            [int(slot), int(L), int(K), float(rho_by_rs[(slot, L, K)])]
            for slot in SLOTS for L in layers for K in KS
        ],
    }
    json_path = experiment_dir / args.rhos_json
    json.dump(json_out, open(json_path, "w"), indent=2)
    print(f"Wrote {json_path}")

    _render_plot(experiment_dir, args.plot, layers, KS, SLOTS,
                 rho_by_di, rho_by_rs,
                 len(axis_scores_di), len(axis_scores_rs))
    return 0


def _render_plot(experiment_dir: Path, plot_name: str,
                 layers: list[int], KS: list[int], slots: list[int],
                 rho_by_di: dict, rho_by_rs: dict,
                 n_axes_di: int, n_axes_resp: int) -> None:
    """Pure plotting from precomputed ρ tables.  Shared by the main
    pipeline and the ``--replot_from_json`` fast path."""
    nonraw = [k for k in KS if k != 0]
    # Full rainbow (purple → blue → green → yellow → red) for the
    # K-spectrum; matplotlib's "rainbow" colormap is exactly this.
    rainbow = (plt.cm.rainbow(np.linspace(0.0, 1.0, len(nonraw)))
               if nonraw else [])

    def k_color(K: int):
        if K == 0:
            return "black"
        return rainbow[nonraw.index(K)]

    def k_label(K: int) -> str:
        return "raw" if K == 0 else f"K={K}"

    fig, axes = plt.subplots(2, 2, figsize=(13, 9.5),
                             sharex=True, sharey=True)
    sources = [("desc_inst", rho_by_di, f"desc+inst ({n_axes_di} axes)"),
               ("responses", rho_by_rs, f"responses (GPT, {n_axes_resp} axes)")]
    L_min, L_max = min(layers), max(layers)
    even_layers = list(range(L_min - L_min % 2, L_max + 1, 2))
    for row, slot in enumerate(slots):
        for col, (_src_id, rho_dict, src_title) in enumerate(sources):
            ax = axes[row, col]
            for K in KS:
                ys = [rho_dict[(slot, L, K)] for L in layers]
                ax.plot(layers, ys, color=k_color(K),
                        lw=2.0 if K == 0 else 1.4,
                        marker="o", markersize=3, alpha=0.95,
                        label=k_label(K))
            # Faint vertical guideline every 2 layers (minor grid),
            # plus the standard major grid for orientation.
            ax.set_xticks(even_layers, minor=True)
            ax.grid(which="major", alpha=0.3)
            ax.grid(which="minor", axis="x", alpha=0.12, lw=0.5)
            ax.set_title(f"{SLOT_LABELS[slot]} -- {src_title}", fontsize=10)
            if row == 1:
                ax.set_xlabel("Transformer layer", fontsize=10)
            if col == 0:
                ax.set_ylabel("Mean per-axis Spearman ρ", fontsize=10)
            if row == 0 and col == 0:
                ax.legend(fontsize=8, ncol=2, loc="best",
                          framealpha=0.9, handlelength=1.6)

    title_line = (f"Mean per-axis ρ vs transformer layer, by slot × source "
                  f"× whitening level "
                  f"(desc+inst = {n_axes_di} axes, GPT+Sonnet 4-way mean; "
                  f"responses = {n_axes_resp} axes, GPT-only)")
    fig.suptitle(title_line, fontsize=14, fontweight="bold", y=0.995)
    plt.tight_layout(rect=(0, 0, 1, 0.97))

    out = experiment_dir / plot_name
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title_line))
    plt.close(fig)
    print(f"Wrote {out}")


if __name__ == "__main__":
    raise SystemExit(main())
