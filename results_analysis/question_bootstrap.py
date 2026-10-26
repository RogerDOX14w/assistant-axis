#!/usr/bin/env python3
"""How much of a role vector is question-sampling noise?

A cluster bootstrap over the extraction questions (Roger, 2026-10-26): each
replicate draws the questions with replacement and keeps, for every entity,
all of its responses to the drawn questions (all instructions), so responses
to one question stay together.  The draw is *joint*: the same questions for
the default and for every role in a replicate, as in the pipeline, where all
of them answer the same questions.  So a question's pull common to a role and
the default cancels in the default-centred vector, as it does in the data.

For each role and slot, at one layer, after the soft-shear fitted on the May
tree (as ``rubric_version_vector_change.py``), it reports the bootstrap SD of
the default-centred vector's norm (% of the full-sample norm) and the angle
between replicate and full-sample vectors, jointly and with the default held
at its full-sample mean (the role side alone, an upper bound).  It also
bootstraps the step-5 axis (mean default minus mean role vector over the roles
given).  Kept responses are those a role's score file scores 3 (the step-4
filter); the default keeps all of its responses, as step 4 does.

Usage:
    uv run python results_analysis/question_bootstrap.py \\
        --activations-dir "/Volumes/G-Drive/assistant-axis/runpod_workspace/qwen/qwen-3-32b Roger 8slot/roles/activations" \\
        --default-activations "/Volumes/G-Drive/.../default/activations/default.pt" \\
        --scores-dir "runpod_workspace/qwen/qwen-3-32b Roger 8slot/roles/scores" \\
        --roles secretary altruist ... --out reports/pipeline/question_bootstrap/may.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from assistant_axis import json_metadata  # noqa: E402
from assistant_axis.provenance import InputSpec, current_file_input, current_files_input  # noqa: E402

DEFAULT_DATA_DIR = REPO / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot"


def question_index(key: str) -> int:
    """The question of an activation key such as ``pos_p3_q47``."""
    return int(key.rsplit("_q", 1)[1])


def load_layer(path: Path, layer: int):
    """``(keys, X)``: an activation file's keys and their layer-``layer`` rows,
    ``X`` of shape (n, slots, D) in float32."""
    import torch
    acts = torch.load(path, map_location="cpu", weights_only=False)
    keys = sorted(k for k, v in acts.items() if isinstance(v, torch.Tensor) and v.dim() == 3)
    X = torch.stack([acts[k][:, layer, :] for k in keys]).to(torch.float32).numpy()
    return keys, X


def question_counts(questions: np.ndarray, B: int, seed: int) -> np.ndarray:
    """(B, max question + 1): how often each question is drawn in each replicate."""
    rng = np.random.default_rng(seed)
    draws = rng.choice(questions, size=(B, len(questions)), replace=True)
    counts = np.zeros((B, int(questions.max()) + 1))
    for b in range(B):
        np.add.at(counts[b], draws[b], 1)
    return counts


def boot_means(X: np.ndarray, q: np.ndarray, counts: np.ndarray) -> np.ndarray:
    """(B, D) replicate means of the rows ``X`` (n, D) answering questions
    ``q`` (n,), each row weighted by its question's count; a replicate in
    which no row's question was drawn is NaN."""
    W = counts[:, q]
    tot = W.sum(1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (W @ X) / np.where(tot > 0, tot, np.nan)


def norm_and_angle(full: np.ndarray, boot: np.ndarray) -> dict:
    """SD of the replicates' norms as % of ``full``'s, and the median and
    95th-percentile angle (degrees) between replicate and ``full``; replicates
    that are NaN are left out and counted."""
    ok = ~np.isnan(boot).any(1)
    b = boot[ok]
    nf = float(np.linalg.norm(full))
    nb = np.linalg.norm(b, axis=1)
    cos = np.clip(b @ full / (nb * nf), -1.0, 1.0)
    ang = np.degrees(np.arccos(cos))
    return {"norm_sd_pct": float(100 * nb.std() / nf), "median_angle_deg": float(np.median(ang)),
            "p95_angle_deg": float(np.quantile(ang, 0.95)), "n_replicates": int(ok.sum())}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--activations-dir", type=Path, required=True, help="the roles' activation files")
    p.add_argument("--default-activations", type=Path, required=True)
    p.add_argument("--scores-dir", type=Path, required=True, help="the roles' score files (score 3 = kept)")
    p.add_argument("--roles", nargs="+", required=True,
                   help="role stems; 'stem=file_stem' when the activation and score files carry another name")
    p.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                   help="tree whose goal / no-goal subspaces fit the soft-shear (default: the May 8slot tree)")
    p.add_argument("--layer", type=int, default=25)
    p.add_argument("--L", type=int, default=None, help="soft-shear L (default: DEFAULT_SOFT_SHEAR_L)")
    p.add_argument("--B", type=int, default=1000, help="bootstrap replicates")
    p.add_argument("--seed", type=int, default=20261026)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces
    from results_analysis.canonical_angles.whitening import DEFAULT_SOFT_SHEAR_L, fit_shear
    L = DEFAULT_SOFT_SHEAR_L if args.L is None else args.L

    pairs = [r.split("=", 1) if "=" in r else (r, r) for r in args.roles]
    act_files = [args.activations_dir / f"{f}.pt" for _, f in pairs]
    score_files = [args.scores_dir / f"{f}.json" for _, f in pairs]
    missing = [str(x) for x in act_files + score_files if not x.exists()]
    if missing:
        raise SystemExit(f"missing: {missing}")
    inputs: list[InputSpec] = [
        current_file_input(dep_key="producer_script", path=Path(__file__).resolve(),
                           extras={"layer": str(args.layer), "L": str(L), "B": str(args.B), "seed": str(args.seed)}),
        current_file_input(dep_key="default_activations", path=args.default_activations),
        current_files_input(dep_key="role_activations", paths=act_files),
        current_files_input(dep_key="role_scores", paths=score_files),
    ]

    t0 = time.time()
    dkeys, D = load_layer(args.default_activations, args.layer)
    dq = np.array([question_index(k) for k in dkeys])
    questions = np.unique(dq)
    counts = question_counts(questions, args.B, args.seed)
    n_slots = D.shape[1]
    shears = [fit_shear(*build_goal_nogoal_subspaces(args.data_dir, s, args.layer, kind="combined"), L=L)
              for s in range(n_slots)]
    d_full = [D[:, s, :].mean(0) for s in range(n_slots)]
    d_boot = [boot_means(D[:, s, :], dq, counts) for s in range(n_slots)]
    print(f"default: {len(dkeys)} responses, {len(questions)} questions; {time.time() - t0:.0f}s", flush=True)

    role_sum_full = [np.zeros_like(d_full[s], dtype=np.float64) for s in range(n_slots)]
    role_sum_boot = [np.zeros_like(d_boot[s], dtype=np.float64) for s in range(n_slots)]
    roles_out = {}
    for (stem, fstem), af, sf in zip(pairs, act_files, score_files):
        scores = json.loads(sf.read_text())
        keys, X = load_layer(af, args.layer)
        kept = np.array([scores.get(k) == 3 for k in keys])
        q = np.array([question_index(k) for k in keys])[kept]
        unknown = set(q) - set(questions)
        if unknown:
            raise SystemExit(f"{stem}: questions {sorted(unknown)[:5]} not among the default's")
        rows = []
        for s in range(n_slots):
            Xs = X[kept, s, :].astype(np.float64)
            full = Xs.mean(0)
            boot = boot_means(Xs, q, counts)
            role_sum_full[s] += full
            role_sum_boot[s] += np.nan_to_num(boot, nan=0.0) + np.where(np.isnan(boot), full, 0.0)
            ap = shears[s].apply
            joint = norm_and_angle(ap(full - d_full[s]), ap(boot - d_boot[s]))
            role_only = norm_and_angle(ap(full - d_full[s]), ap(boot - d_full[s]))
            rows.append({"slot": s, "joint": joint, "role_only": role_only})
        roles_out[stem] = {"file_stem": fstem, "kept": int(kept.sum()), "slots": rows}
        j0 = rows[0]["joint"]
        print(f"{stem:28s} kept {kept.sum():3d}  slot0 joint SD {j0['norm_sd_pct']:.2f}% "
              f"angle {j0['median_angle_deg']:.1f}deg  ({time.time() - t0:.0f}s)", flush=True)

    n = len(pairs)
    axis = []
    for s in range(n_slots):
        ap = shears[s].apply
        full = d_full[s] - role_sum_full[s] / n
        boot = d_boot[s] - role_sum_boot[s] / n
        axis.append({"slot": s, **norm_and_angle(ap(full), ap(boot))})
    res = {"layer": args.layer, "soft_shear_L": L, "B": args.B, "seed": args.seed,
           "n_questions": int(len(questions)), "n_default_responses": len(dkeys),
           "roles": roles_out, "axis": axis}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(json_metadata(res, inputs=inputs,
                                                 title="Question bootstrap of role vectors"), indent=1) + "\n")
    print("axis (step 5 over these roles): " + "; ".join(
        f"s{a['slot']} SD {a['norm_sd_pct']:.2f}% {a['median_angle_deg']:.2f}deg" for a in axis))
    print(f"wrote {args.out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main()
