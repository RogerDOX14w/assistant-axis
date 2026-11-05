"""Jev's plain Noul against its relative wording on descriptions and instructions, from the cells on disk.

Roger, 2026-11-05, after the response-judging session found that on responses the plain Noul ("is the persona nearer
the pos end of the axis than the neg end?", each answer judged on its own) beat the relative wording ("nearer the pos
end than most of the others?") by 0.031: was the like tried on descriptions and instructions?  It was: the plain
wording was Jev's first design there, at 1, 10, 20 and 40 entities a request, and the relative one was chosen at 160
(reports/judge_pareto/jev_judging.md, "What was tried").  This script puts the two side by side on every cell that
exists: on all 61 May axes, balanced and in the axis's own order, and on the dev30 batch-size curves.  rho per axis is
Spearman against the projections, averaged over the 12 projection variants (slots 0 and 6, layers 25 and 49, raw,
soft-K and soft-shear) and also at the default variant s6_l25_raw alone, as in scripts/jev_weight_resilience.py.
Paired differences over the axes carry a 95% interval from resampling the axes.  No API calls; about two minutes.

Writes roger/axis_judge_experiments/jev_wording/jev_plain_vs_relative.json (a provenance envelope) and prints the
tables.  The account is reports/judge_pareto/working_with_jev.md § 2.

Usage: uv run python scripts/jev_plain_vs_relative.py [--output PATH] [--bootstrap 4000]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from assistant_axis import json_metadata
from assistant_axis.provenance import current_file_input, current_files_input
from results_analysis import judge_tier_robustness as rob
from results_analysis.judge_tier_cost_eval import cell_scores_path

JEV = "jev-1.14.0"
DEFAULT_OUTPUT = Path("roger/axis_judge_experiments/jev_wording/jev_plain_vs_relative.json")
DEFAULT_VARIANT = "s6_l25_raw"

#: arm label -> the Jev cells averaged into it (judge_tier_cost_eval cells, <axis>_tier_eval/jev-1.14.0@<label>/).
#: "plain" is judge_jev_entities.py --wording base; "relative" its --wording relative.  d: balanced directions
#: (descriptions: one pass each way; instructions: Roger's table per round); s, r: the axis's own order.
ARMS: Dict[str, Dict[str, List[str]]] = {
    "descriptions": {
        "plain n20, d1": ["jd_noul_n20d1"],
        "plain n20, d2": ["jd_noul_n20d2"],
        "plain n20, x2": ["jd_noul_n20d1", "jd_noul_n20d2"],
        "relative n160, d1": ["jd_noul_relative_n160d1"],
        "relative n160, d2": ["jd_noul_relative_n160d2"],
        "relative n160, x2": ["jd_noul_relative_n160d1", "jd_noul_relative_n160d2"],
        "plain n20, own s1": ["jd_noul_base_n20s1"],
        "plain n20, own s2": ["jd_noul_base_n20s2"],
        "plain n20, own x2": ["jd_noul_base_n20s1", "jd_noul_base_n20s2"],
        "relative n160, own s1": ["jd_noul_relative_n160s1"],
        "relative n160, own s2": ["jd_noul_relative_n160s2"],
        "relative n160, own x2": ["jd_noul_relative_n160s1", "jd_noul_relative_n160s2"],
        "plain n1, own (dev30)": ["jd_noul_base_n1s1"],
        "plain n10, own (dev30)": ["jd_noul_base_n10s1"],
        "plain n40, own (dev30)": ["jd_noul_base_n40s1"],
        "relative n10, own (dev30)": ["jd_noul_relative_n10s1"],
        "relative n20, own (dev30)": ["jd_noul_relative_n20s1"],
        "relative n40, own (dev30)": ["jd_noul_relative_n40s1"],
        "relative n80, own (dev30)": ["jd_noul_relative_n80s1"],
        "relative n290, own (dev30)": ["jd_noul_relative_n290s1"],
    },
    "instructions": {
        "plain n20, x1 (d0-4)": [f"ji_noul_n20d{r}" for r in range(5)],
        "relative n160, x1 (d0-4)": [f"ji_noul_relative_n160d{r}" for r in range(5)],
        "relative n160, x2 (d0-9)": [f"ji_noul_relative_n160d{r}" for r in range(10)],
        "plain n20, own x1 (r0-4)": [f"ji_noul_base_n20_r{r}" for r in range(5)],
        "relative n160, own x1 (r0-4)": [f"ji_noul_relative_n160_r{r}" for r in range(5)],
    },
}
COMPARISONS: Dict[str, List[Tuple[str, str]]] = {
    "descriptions": [
        ("plain n20, x2", "relative n160, x2"),
        ("plain n20, d1", "relative n160, d1"),
        ("plain n20, d2", "relative n160, d2"),
        ("plain n20, own x2", "relative n160, own x2"),
        ("plain n20, own s1", "relative n160, own s1"),
        ("plain n10, own (dev30)", "relative n10, own (dev30)"),
        ("plain n20, own s1", "relative n20, own (dev30)"),
        ("plain n40, own (dev30)", "relative n40, own (dev30)"),
        ("plain n20, own s1", "plain n10, own (dev30)"),
        ("plain n40, own (dev30)", "plain n20, own s1"),
    ],
    "instructions": [
        ("plain n20, x1 (d0-4)", "relative n160, x1 (d0-4)"),
        ("plain n20, x1 (d0-4)", "relative n160, x2 (d0-9)"),
        ("plain n20, own x1 (r0-4)", "relative n160, own x1 (r0-4)"),
    ],
}


def mean_of(runs: Sequence[Mapping[str, float]]) -> Dict[str, float]:
    """Each entity's mean over the runs that scored it."""
    keys = set().union(*runs)
    return {k: float(np.mean([r[k] for r in runs if k in r])) for k in keys}


def compare(a: Mapping[str, float], b: Mapping[str, float], rng: np.random.Generator, n_boot: int = 4000) -> dict:
    """a minus b, paired over the axes both have: mean, a 95% interval from resampling the axes, axes a is ahead on,
    and the four axes at each end."""
    common = sorted(set(a) & set(b))
    if not common:
        return {"n_axes": 0}
    d = np.array([a[x] - b[x] for x in common])
    boots = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    order = sorted(common, key=lambda x: a[x] - b[x])
    return {"n_axes": len(common), "mean": float(d.mean()), "lo": float(lo), "hi": float(hi),
            "a_ahead_on": int((d > 0).sum()),
            "worst_for_a": [(x, round(a[x] - b[x], 4)) for x in order[:4]],
            "best_for_a": [(x, round(a[x] - b[x], 4)) for x in order[-4:][::-1]]}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--axes_file", default="scripts/tier_eval_axes.tsv")
    p.add_argument("--dev_axes_file", default="scripts/tier_eval_axes_dev30.tsv")
    p.add_argument("--experiments_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR))
    p.add_argument("--data_dir", default=str(rob.DEFAULT_DATA_DIR))
    p.add_argument("--cache_dir", default=None, help="the projection slice cache (default: <experiments_dir>/"
                                                     "_tier_eval_scratch/robustness_cache, judge_tier_robustness.py's)")
    p.add_argument("--bootstrap", type=int, default=4000, help="axis resamples for each difference's interval")
    p.add_argument("--seed", type=int, default=20261105)
    p.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = p.parse_args(argv)
    t0 = time.time()
    E, D = Path(args.experiments_dir), Path(args.data_dir)
    cache = Path(args.cache_dir) if args.cache_dir else E / "_tier_eval_scratch" / "robustness_cache"
    axes = rob.read_axes_tsv(Path(args.axes_file))
    dev30 = {a.axis_dir for a in rob.read_axes_tsv(Path(args.dev_axes_file))}
    variants = rob.build_variants(rob.DEFAULT_SLOTS, rob.DEFAULT_LAYERS, list(rob.REGIMES),
                                  K=rob.DEFAULT_SOFT_K, L=rob.DEFAULT_SOFT_SHEAR_L)
    meta = {"version": rob.CACHE_VERSION, "fingerprint": rob.data_fingerprint(D), "ca_kind": "combined"}
    slices = rob.load_slices(cache, rob.DEFAULT_SLOTS, rob.DEFAULT_LAYERS, meta, True)
    if slices is None:
        raise SystemExit(f"no current slice cache under {cache}: run judge_tier_robustness.py once to build it")
    kinds = rob.vector_kinds(D)
    vkeys = [v.key for v in variants]
    if DEFAULT_VARIANT not in vkeys:
        raise SystemExit(f"{DEFAULT_VARIANT} is not among the variants {vkeys}")
    rng = np.random.default_rng(args.seed)
    inputs = [rob._subtree_input(D, "traits/vectors", "traits_vectors"),
              rob._subtree_input(D, "roles/vectors", "roles_vectors"),
              current_file_input("axes_file", Path(args.axes_file)),
              current_file_input("dev_axes_file", Path(args.dev_axes_file))]
    report = {"variants": vkeys, "default_variant": DEFAULT_VARIANT, "modes": {}}
    for mode, arms in ARMS.items():
        print(f"\n===== {mode}  ({time.time() - t0:.0f} s)", file=sys.stderr)
        scores: Dict[Tuple[str, str], Dict[str, float]] = {}
        paths: List[Path] = []
        for ax in axes:
            for arm, cell_labels in arms.items():
                runs = []
                for c in cell_labels:
                    sp = cell_scores_path(E / f"{ax.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{JEV}@{c}")
                    if not sp.exists():
                        runs = []
                        break
                    runs.append(rob.lift_scores(rob.numeric_scores(rob._unwrap(json.loads(sp.read_text()))), kinds))
                    paths.append(sp)
                if runs:
                    scores[ax.axis_dir, arm] = mean_of(runs)
        inputs.append(current_files_input(dep_key=f"{mode}_scores", paths=sorted(set(paths))))
        names = {ax.axis_dir: set().union(*(s for (a, _), s in scores.items() if a == ax.axis_dir)) for ax in axes}
        proj = rob.project_variants(slices, axes, variants, names, D)
        rho12: Dict[str, Dict[str, float]] = {arm: {} for arm in arms}
        rho_d: Dict[str, Dict[str, float]] = {arm: {} for arm in arms}
        for arm in arms:
            for ax in axes:
                s = scores.get((ax.axis_dir, arm))
                if s is None:
                    continue
                per = {vk: rob.cell_rho(dict(s), proj[ax.axis_dir][vk], (ax.pos, ax.neg))[0] for vk in vkeys}
                rho12[arm][ax.axis_dir] = float(np.mean(list(per.values())))
                rho_d[arm][ax.axis_dir] = float(per[DEFAULT_VARIANT])
        rep: dict = {"arms": {}, "comparisons": []}
        print(f"{'arm':34s} {'axes':>4s} {'rho (12 var.)':>13s} {DEFAULT_VARIANT:>10s}   dev30 only: {'rho12':>6s} {'def.':>6s}")
        for arm in arms:
            r12, rd = rho12[arm], rho_d[arm]
            if not r12:
                print(f"{arm:34s} (no cells)")
                continue
            dev = [a for a in r12 if a in dev30]
            m = {"n_axes": len(r12), "rho12": float(np.mean(list(r12.values()))),
                 "rho_default": float(np.mean(list(rd.values()))),
                 "dev30_rho12": float(np.mean([r12[a] for a in dev])) if dev else None,
                 "dev30_rho_default": float(np.mean([rd[a] for a in dev])) if dev else None,
                 "per_axis_rho12": r12, "per_axis_rho_default": rd}
            print(f"{arm:34s} {m['n_axes']:4d} {m['rho12']:13.4f} {m['rho_default']:10.4f}               "
                  f"{m['dev30_rho12'] or float('nan'):6.4f} {m['dev30_rho_default'] or float('nan'):6.4f}")
            rep["arms"][arm] = m
        print()
        for a, b in COMPARISONS[mode]:
            c12, cd = compare(rho12[a], rho12[b], rng, args.bootstrap), compare(rho_d[a], rho_d[b], rng, args.bootstrap)
            rep["comparisons"].append({"a": a, "b": b, "rho12": c12, "default": cd})
            if not c12["n_axes"]:
                print(f"{a} minus {b}: no common axes")
                continue
            print(f"{a} minus {b} ({c12['n_axes']} axes): 12 variants {c12['mean']:+.4f} [{c12['lo']:+.4f}, "
                  f"{c12['hi']:+.4f}], a ahead on {c12['a_ahead_on']}; {DEFAULT_VARIANT} {cd['mean']:+.4f} "
                  f"[{cd['lo']:+.4f}, {cd['hi']:+.4f}], a ahead on {cd['a_ahead_on']}")
            print(f"   worst for a: {c12['worst_for_a']}\n   best for a:  {c12['best_for_a']}")
        report["modes"][mode] = rep
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(json_metadata(report, inputs=inputs, title="Jev's plain Noul against its relative "
                                                                            "wording on descriptions and instructions"),
                              indent=1))
    print(f"\nwrote {out} ({time.time() - t0:.0f} s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
