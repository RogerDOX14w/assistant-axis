#!/usr/bin/env python3
"""Token-position noise analysis: which token slot is the noisiest?

Promoted from ``roger/token_position_noise_analysis.py`` (April 2026 work)
to a tracked tool. Compares body-mean (slot 0) vs three header tokens
(slots 1-3 = ``<|im_start|>``, ``assistant``, ``\\n``) by examining the
consistency of role-pair difference vectors across random triples, per
layer.

For each random triple ``(A, B, C)`` and each token slot s, the script
computes six metrics measuring how similar ``B-A`` is to ``B-C`` at slot
s, in three distance flavours (cosine, norm, squared-norm), each in
``sub`` (difference) and ``lograt`` (log-ratio) form. The "odd-one-out"
slot per triple/metric is the one whose value deviates most from the
other three; slots that are odd-one-out >25 % of the time are noisier
than the others.

Plus a pairwise-slot analysis: do the four slots agree on the *direction*
of role differences? Done two ways:

- Pearson correlation of per-pair diff *norms* across slots.
- Mean cosine of diff *direction vectors* between slot pairs.

Outputs five PNGs:

- ``ooo_heatmaps.png`` -- odd-one-out fraction by layer × slot, per metric.
- ``ooo_summary_bars.png`` -- slot odd-one-out rate per metric (avg layers).
- ``ooo_by_layer.png`` -- per-layer slot odd-one-out, averaged across metrics.
- ``pairwise_corr_matrices.png`` -- 4×4 norm correlation + cosine agreement.
- ``pairwise_cosine_by_layer.png`` -- mean cosine agreement vs layer.

Headline finding (from the original April 2026 run on the
``qwen-3-32b Christina headers`` data, 280 roles, 64 layers, 1000
triples): **slot 3 (``\\n``) is the least noisy** -- it's odd-one-out
~21-23 % of the time across metrics (slightly below the 25 % chance
floor) and has the highest mean diff-direction agreement with the other
three slots. Slot 0 (body-mean) is the noisiest by all six metrics. This
informed the project-wide convention of using slot 3 as the default
working slot.

Usage::

    uv run python results_analysis/token_position_noise_analysis.py
    uv run python results_analysis/token_position_noise_analysis.py \\
        --data_dir 'runpod_workspace/qwen/qwen-3-32b Roger' \\
        --vectors_subdir traits/vectors \\
        --output_dir roger/token_position_noise_traits

The defaults reproduce a Roger-data run; override ``--data_dir`` to point
at the older ``qwen-3-32b Christina headers`` checkpoint to reproduce the
original report figures.
"""

from __future__ import annotations

import argparse
import itertools
import random
from pathlib import Path
from typing import List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402

from assistant_axis import png_metadata, suptitle_with_specs  # noqa: E402


SLOT_NAMES = ["body-mean", "<|im_start|>", "assistant", "\\n"]
SLOT_LABEL = "Token position"
N_METRICS = 6
METRIC_NAMES = [
    "cosine_sub", "cosine_lograt",
    "norm_sub", "norm_lograt",
    "sqnorm_sub", "sqnorm_lograt",
]


# ---------------------------------------------------------------------------
# Compute helpers (algorithm preserved verbatim from the original script)
# ---------------------------------------------------------------------------

def load_all_vectors(vectors_dir: Path):
    """Load all role vectors into a single bf16 tensor.
    Returns ``(tensor, role_names)``."""
    pt_files = sorted(vectors_dir.glob("*.pt"))
    if not pt_files:
        raise SystemExit(f"No .pt files found in {vectors_dir}")

    vecs = []
    names = []
    for f in pt_files:
        if f.stem == "default":
            continue
        data = torch.load(f, map_location="cpu", weights_only=False)
        vec = data["vector"] if isinstance(data, dict) and "vector" in data else data
        vecs.append(vec.to(torch.bfloat16))
        names.append(f.stem)

    all_vecs = torch.stack(vecs)  # (N, S, L, D)
    print(f"Loaded {len(names)} entities, shape {tuple(all_vecs.shape)}, "
          f"dtype {all_vecs.dtype}")
    return all_vecs, names


def compute_metrics_for_layer(
    layer_vecs: torch.Tensor,    # (N, S, D) float32
    default_vec: torch.Tensor,   # (S, D) float32
    triples: list,
) -> torch.Tensor:
    """Six metrics for all triples at one layer; returns (N_triples, 6, S)."""
    N = len(triples)
    S = layer_vecs.shape[1]
    results = torch.zeros(N, N_METRICS, S)

    idx_A = torch.tensor([t[0] for t in triples])
    idx_B = torch.tensor([t[1] for t in triples])
    idx_C = torch.tensor([t[2] for t in triples])

    vA = layer_vecs[idx_A]
    vB = layer_vecs[idx_B]
    vC = layer_vecs[idx_C]
    vD = default_vec.unsqueeze(0)

    d_BA = vB - vA
    d_BC = vB - vC

    r_B = vB - vD
    r_A = vA - vD
    r_C = vC - vD

    cos_BA = F.cosine_similarity(r_B, r_A, dim=-1).clamp(-1, 1)
    cos_BC = F.cosine_similarity(r_B, r_C, dim=-1).clamp(-1, 1)

    cdist_BA = 1.0 - cos_BA
    cdist_BC = 1.0 - cos_BC

    norm_BA = d_BA.norm(dim=-1)
    norm_BC = d_BC.norm(dim=-1)
    sqnorm_BA = norm_BA.pow(2)
    sqnorm_BC = norm_BC.pow(2)

    eps = 1e-8

    results[:, 0, :] = cdist_BA - cdist_BC
    results[:, 1, :] = (cdist_BA / (cdist_BC + eps) + eps).abs().log()
    results[:, 2, :] = norm_BA - norm_BC
    results[:, 3, :] = (norm_BA / (norm_BC + eps) + eps).abs().log()
    results[:, 4, :] = sqnorm_BA - sqnorm_BC
    results[:, 5, :] = (sqnorm_BA / (sqnorm_BC + eps) + eps).abs().log()

    return results


def normalize_sub_metrics(all_metrics: torch.Tensor) -> None:
    """Normalize ``_sub`` metrics by per-slot-per-layer mean abs (in-place)."""
    for m_idx in (0, 2, 4):
        vals = all_metrics[:, m_idx, :, :]
        mean_abs = vals.abs().mean(dim=0, keepdim=True).clamp(min=1e-10)
        all_metrics[:, m_idx, :, :] = vals / mean_abs


def odd_one_out(values: torch.Tensor) -> torch.Tensor:
    """For each row of shape (..., S), index of the most anomalous slot
    (largest |slot_k − mean(other S−1)|)."""
    abs_vals = values.abs()
    total = abs_vals.sum(dim=-1, keepdim=True)
    leave_one_out_mean = (total - abs_vals) / (values.shape[-1] - 1)
    deviation = (abs_vals - leave_one_out_mean).abs()
    return deviation.argmax(dim=-1)


def compute_pairwise_slot_correlation(
    layer_vecs: torch.Tensor,  # (N, S, D) float32
):
    """Returns ``(norm_corr, cos_between)``, both ``(S, S)`` ndarrays.

    ``norm_corr[s1, s2]`` is the Pearson correlation across all role pairs
    of the diff norms ``‖A_s1 − B_s1‖`` and ``‖A_s2 − B_s2‖`` -- do the
    two slots agree on which role pairs are far apart?

    ``cos_between[s1, s2]`` is the mean (over all role pairs) cosine of
    the diff *direction vectors* ``(A_s1 − B_s1, A_s2 − B_s2)`` -- do the
    two slots agree on the *direction* of each role pair's difference?
    """
    N, S, _D = layer_vecs.shape
    pairs_i, pairs_j = zip(*itertools.combinations(range(N), 2))
    pairs_i = torch.tensor(pairs_i)
    pairs_j = torch.tensor(pairs_j)

    CHUNK = 4096
    n_pairs = len(pairs_i)

    norms_all = torch.zeros(n_pairs, S)
    for start in range(0, n_pairs, CHUNK):
        end = min(start + CHUNK, n_pairs)
        pi = pairs_i[start:end]
        pj = pairs_j[start:end]
        diffs = layer_vecs[pi] - layer_vecs[pj]
        norms_all[start:end] = diffs.norm(dim=-1)

    cos_between = np.zeros((S, S))
    for s1 in range(S):
        for s2 in range(s1, S):
            cos_vals = torch.zeros(n_pairs)
            for start in range(0, n_pairs, CHUNK):
                end = min(start + CHUNK, n_pairs)
                pi = pairs_i[start:end]
                pj = pairs_j[start:end]
                d1 = layer_vecs[pi, s1] - layer_vecs[pj, s1]
                d2 = layer_vecs[pi, s2] - layer_vecs[pj, s2]
                cos_vals[start:end] = F.cosine_similarity(d1, d2, dim=-1)
            cos_between[s1, s2] = cos_vals.mean().item()
            cos_between[s2, s1] = cos_between[s1, s2]

    norm_corr = np.corrcoef(norms_all.numpy().T)
    return norm_corr, cos_between


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _plot_ooo_heatmaps(ooo_frac: torch.Tensor, output_dir: Path,
                       spec_line: str) -> Path:
    heatmap_order = [
        [0, 2, 4],  # cosine_sub, norm_sub, sqnorm_sub
        [1, 3, 5],  # cosine_lograt, norm_lograt, sqnorm_lograt
    ]
    fig, axes = plt.subplots(2, 3, figsize=(20, 9))
    S = ooo_frac.shape[-1]
    for r, row_indices in enumerate(heatmap_order):
        for c, m in enumerate(row_indices):
            ax = axes[r, c]
            data = ooo_frac[m].numpy()
            im = ax.imshow(data.T, aspect="auto", cmap="YlOrRd", vmin=0, vmax=0.6)
            ax.set_title(METRIC_NAMES[m], fontsize=14)
            ax.set_xlabel("Layer", fontsize=13)
            ax.set_ylabel(SLOT_LABEL, fontsize=13)
            ax.set_yticks(range(S))
            ax.set_yticklabels(SLOT_NAMES, fontsize=11)
            ax.tick_params(axis="x", labelsize=11)
    title = "Odd-one-out fraction by layer and token position"
    _, top_rect = suptitle_with_specs(fig, title, spec_line)
    fig.tight_layout(rect=(0, 0, 0.93, top_rect))
    cbar_ax = fig.add_axes([0.94, 0.15, 0.012, 0.7])
    fig.colorbar(im, cax=cbar_ax, label="Fraction odd-one-out")
    cbar_ax.yaxis.label.set_size(13)
    cbar_ax.tick_params(labelsize=11)
    out = output_dir / "ooo_heatmaps.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title))
    plt.close()
    return out


def _plot_ooo_summary_bars(ooo_frac: torch.Tensor, output_dir: Path,
                           spec_line: str) -> Path:
    S = ooo_frac.shape[-1]
    fig, ax = plt.subplots(figsize=(12, 5.5))
    x = np.arange(N_METRICS)
    width = 0.2
    for s in range(S):
        vals = [ooo_frac[m].mean(dim=0)[s].item() for m in range(N_METRICS)]
        ax.bar(x + s * width, vals, width, label=SLOT_NAMES[s])
    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(METRIC_NAMES, rotation=45, ha="right", fontsize=13)
    ax.set_ylabel("Fraction odd-one-out (avg across layers)", fontsize=14)
    ax.tick_params(axis="y", labelsize=12)
    ax.axhline(0.25, color="gray", linestyle="--", alpha=0.5,
               label="chance (0.25)")
    ax.set_xlim(-0.5, N_METRICS + 0.5)
    ax.legend(fontsize=12)
    title = "Which token position is most often the odd one out?"
    _, top_rect = suptitle_with_specs(fig, title, spec_line)
    fig.tight_layout(rect=(0, 0, 1, top_rect))
    out = output_dir / "ooo_summary_bars.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title))
    plt.close()
    return out


def _plot_ooo_by_layer(ooo_frac: torch.Tensor, L: int, output_dir: Path,
                       spec_line: str) -> Path:
    S = ooo_frac.shape[-1]
    fig, ax = plt.subplots(figsize=(14, 5.5))
    avg_across_metrics = ooo_frac.mean(dim=0).numpy()  # (L, S)
    for s in range(S):
        ax.plot(range(L), avg_across_metrics[:, s], label=SLOT_NAMES[s], alpha=0.8)
    ax.axhline(0.25, color="gray", linestyle="--", alpha=0.5)
    for x in range(0, L, 2):
        ax.axvline(x, color="gray", linewidth=0.3, alpha=0.3)
    for x in range(0, L, 10):
        ax.axvline(x, color="gray", linewidth=0.7, alpha=0.6)
    ax.set_xlabel("Layer", fontsize=14)
    ax.set_ylabel("Fraction odd-one-out (avg across 6 metrics)", fontsize=14)
    ax.tick_params(labelsize=12)
    ax.legend(fontsize=12)
    title = "Odd-one-out fraction by layer (averaged across metrics)"
    _, top_rect = suptitle_with_specs(fig, title, spec_line)
    fig.tight_layout(rect=(0, 0, 1, top_rect))
    out = output_dir / "ooo_by_layer.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title))
    plt.close()
    return out


def _plot_pairwise_matrices(norm_corr_layers: np.ndarray,
                            cos_between_layers: np.ndarray,
                            output_dir: Path, spec_line: str) -> Path:
    S = norm_corr_layers.shape[-1]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8))
    panels = [
        (axes[0], norm_corr_layers.mean(axis=0),
         "Norm correlation (avg across layers)"),
        (axes[1], cos_between_layers.mean(axis=0),
         "Cosine direction agreement (avg across layers)"),
    ]
    im = None
    for ax, mat, title in panels:
        im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1)
        ax.set_xticks(range(S))
        ax.set_xticklabels(SLOT_NAMES, fontsize=12, rotation=45, ha="right")
        ax.set_yticks(range(S))
        ax.set_yticklabels(SLOT_NAMES, fontsize=12)
        ax.set_title(title, fontsize=14)
        for i in range(S):
            for j in range(S):
                ax.text(j, i, f"{mat[i, j]:.3f}", ha="center", va="center",
                        fontsize=12,
                        color="white" if mat[i, j] < 0.3 else "black")
    suptitle_text = "Pairwise token-position agreement"
    _, top_rect = suptitle_with_specs(fig, suptitle_text, spec_line)
    fig.tight_layout(rect=(0, 0, 0.92, top_rect))
    cbar_ax = fig.add_axes([0.93, 0.15, 0.015, 0.7])
    fig.colorbar(im, cax=cbar_ax)
    cbar_ax.tick_params(labelsize=11)
    out = output_dir / "pairwise_corr_matrices.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=suptitle_text))
    plt.close()
    return out


def _plot_pairwise_cosine_by_layer(cos_between_layers: np.ndarray, L: int,
                                   output_dir: Path, spec_line: str) -> Path:
    S = cos_between_layers.shape[-1]
    fig, ax = plt.subplots(figsize=(14, 5.5))
    for s in range(S):
        offdiag = np.array([
            [cos_between_layers[lay, s, s2] for s2 in range(S) if s2 != s]
            for lay in range(L)
        ]).mean(axis=1)
        ax.plot(range(L), offdiag, label=SLOT_NAMES[s], alpha=0.8)
    for x in range(0, L, 2):
        ax.axvline(x, color="gray", linewidth=0.3, alpha=0.3)
    for x in range(0, L, 10):
        ax.axvline(x, color="gray", linewidth=0.7, alpha=0.6)
    ax.set_xlabel("Layer", fontsize=14)
    ax.set_ylabel("Mean cosine agreement with others", fontsize=14)
    ax.tick_params(labelsize=12)
    ax.legend(fontsize=12)
    title = "Pairwise token-position direction agreement, by layer"
    _, top_rect = suptitle_with_specs(fig, title, spec_line)
    fig.tight_layout(rect=(0, 0, 1, top_rect))
    out = output_dir / "pairwise_cosine_by_layer.png"
    plt.savefig(out, dpi=150, bbox_inches="tight",
                metadata=png_metadata(title=title))
    plt.close()
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__.split("\n\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--data_dir", type=str,
        default="runpod_workspace/qwen/qwen-3-32b Roger",
        help="Base data directory (vectors will be loaded from "
             "<data_dir>/<vectors_subdir>/*.pt). The original April 2026 "
             "report figures used 'runpod_workspace/qwen/qwen-3-32b "
             "Christina headers'; the current Roger data is the default.",
    )
    p.add_argument(
        "--vectors_subdir", type=str, default="roles/vectors",
        help="Sub-path within --data_dir containing entity .pt files. "
             "Use 'traits/vectors' to run on traits instead of roles.",
    )
    p.add_argument(
        "--output_dir", type=str, default="roger/token_position_noise_out",
        help="Where to write the five PNGs. Gitignored under roger/ by "
             "default; pass a different path to keep results elsewhere.",
    )
    p.add_argument(
        "--n_triples", type=int, default=1000,
        help="Number of random (A, B, C) triples sampled from the entity "
             "set (with replacement of triples; entities within a triple "
             "are distinct).",
    )
    p.add_argument(
        "--seed", type=int, default=42,
        help="RNG seed for triple sampling.",
    )
    p.add_argument(
        "--max_layers", type=int, default=None,
        help="Optional cap on the number of layers analysed (for quick "
             "smoke tests). None = all layers.",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    data_dir = Path(args.data_dir)
    vectors_dir = data_dir / args.vectors_subdir
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    print("Step 1: Loading vectors...")
    all_vecs, _role_names = load_all_vectors(vectors_dir)
    N_roles, S, L_full, D = all_vecs.shape
    L = min(L_full, args.max_layers) if args.max_layers else L_full
    print(f"  {N_roles} entities, {S} slots, {L_full} layers (using {L}), "
          f"hidden_dim={D}")

    default_vec = all_vecs.float().mean(dim=0)  # (S, L_full, D)
    default_vec_bf16 = default_vec.to(torch.bfloat16)
    del default_vec

    print(f"Step 2: Sampling {args.n_triples} triples...")
    role_indices = list(range(N_roles))
    triples: List[tuple] = []
    for _ in range(args.n_triples):
        triples.append(tuple(random.sample(role_indices, 3)))

    print("Step 2-3: Computing metrics per layer...")
    all_metrics = torch.zeros(args.n_triples, N_METRICS, S, L)
    norm_corr_layers = np.zeros((L, S, S))
    cos_between_layers = np.zeros((L, S, S))

    for layer in range(L):
        if layer % 8 == 0:
            print(f"  Layer {layer}/{L}...")
        layer_vecs = all_vecs[:, :, layer, :].float()
        default_layer = default_vec_bf16[:, layer, :].float()

        all_metrics[:, :, :, layer] = compute_metrics_for_layer(
            layer_vecs, default_layer, triples,
        )
        norm_corr, cos_between = compute_pairwise_slot_correlation(layer_vecs)
        norm_corr_layers[layer] = norm_corr
        cos_between_layers[layer] = cos_between
        del layer_vecs, default_layer

    print("Normalizing subtraction metrics...")
    normalize_sub_metrics(all_metrics)

    print("Step 3: Odd-one-out scoring...")
    flat = all_metrics.permute(0, 1, 3, 2).reshape(-1, S)
    winners = odd_one_out(flat).reshape(args.n_triples, N_METRICS, L)

    ooo_counts = torch.zeros(N_METRICS, L, S)
    for s in range(S):
        ooo_counts[:, :, s] = (winners == s).float().sum(dim=0)
    ooo_frac = ooo_counts / args.n_triples

    # Console summary.
    print("\n" + "=" * 80)
    print("RESULTS: Odd-one-out fraction (averaged across layers)")
    print("=" * 80)
    print(f"{'metric':<20s}", end="")
    for sn in SLOT_NAMES:
        print(f"{sn:>15s}", end="")
    print(f"{'  most odd':>12s}")
    print("-" * 80)
    for m in range(N_METRICS):
        avg = ooo_frac[m].mean(dim=0)
        print(f"{METRIC_NAMES[m]:<20s}", end="")
        for s in range(S):
            print(f"{avg[s].item():>15.3f}", end="")
        print(f"{'  ' + SLOT_NAMES[avg.argmax().item()]:>12s}")
    overall = ooo_frac.mean(dim=0).mean(dim=0)
    print("-" * 80)
    print(f"{'OVERALL':<20s}", end="")
    for s in range(S):
        print(f"{overall[s].item():>15.3f}", end="")
    print(f"{'  ' + SLOT_NAMES[overall.argmax().item()]:>12s}")

    print("\n" + "=" * 80)
    print("PAIRWISE SLOT NORM CORRELATION (averaged across layers)")
    print("=" * 80)
    avg_norm_corr = norm_corr_layers.mean(axis=0)
    for s1 in range(S):
        print(f"  {SLOT_NAMES[s1]:>15s}", end="")
        for s2 in range(S):
            print(f"  {avg_norm_corr[s1, s2]:>8.4f}", end="")
        print()
    print("\n  Mean off-diagonal correlation per slot:")
    for s in range(S):
        offdiag = [avg_norm_corr[s, s2] for s2 in range(S) if s2 != s]
        print(f"    {SLOT_NAMES[s]:>15s}: {np.mean(offdiag):.4f}")

    print("\n" + "=" * 80)
    print("PAIRWISE SLOT DIFF-DIRECTION AGREEMENT (avg cosine, all layers)")
    print("=" * 80)
    avg_cos_between = cos_between_layers.mean(axis=0)
    for s1 in range(S):
        print(f"  {SLOT_NAMES[s1]:>15s}", end="")
        for s2 in range(S):
            print(f"  {avg_cos_between[s1, s2]:>8.4f}", end="")
        print()
    print("\n  Mean off-diagonal agreement per slot:")
    for s in range(S):
        offdiag = [avg_cos_between[s, s2] for s2 in range(S) if s2 != s]
        print(f"    {SLOT_NAMES[s]:>15s}: {np.mean(offdiag):.4f}")

    print(f"\nSaving plots to {output_dir}/...")
    spec_line = (f"{N_roles} {Path(args.vectors_subdir).parts[0]} "
                 f"× {S} token positions × {L} layers; "
                 f"{args.n_triples} random triples; seed={args.seed}; "
                 f"data: {data_dir.name}")

    paths = [
        _plot_ooo_heatmaps(ooo_frac, output_dir, spec_line),
        _plot_ooo_summary_bars(ooo_frac, output_dir, spec_line),
        _plot_ooo_by_layer(ooo_frac, L, output_dir, spec_line),
        _plot_pairwise_matrices(norm_corr_layers, cos_between_layers,
                                output_dir, spec_line),
        _plot_pairwise_cosine_by_layer(cos_between_layers, L, output_dir,
                                       spec_line),
    ]
    for p in paths:
        print(f"  wrote {p}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
