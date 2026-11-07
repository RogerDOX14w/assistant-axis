#!/usr/bin/env python3
"""Error bars on the response-judging mixes (Roger, 2026-11-07: "do you have a way to put error bars on those rho and
quality numbers?"; "I'm interested in the variance of the relative answers, not the variance in the absolute score").

The arms are those of judge_response_pareto.py --judge mix: each judge alone at its settled design and the golden
splits of three and of four judges, read from the settled dumps (settled61/<judge>3.json.gz, the thirds, or
settled61/<judge>.json.gz, the ninths).  Every draw below is applied identically to every arm, axis and variant, and
what is reported is each arm's paired difference from the best golden split under the draw, so that an axis or a
question that is hard for every judge cancels.  Three variance components:

1. Redrawing the questions: a bootstrap over the dump's question positions (every arm keeps its items with their judge
   assignment; the positions are resampled with replacement, the entity means recomputed with the multiplicities).
2. Redrawing the axes: a bootstrap over the axes of each arm's per-axis rho (the mean over the 12 projection
   variants), the same axis resample for every arm.
3. Rejudging: Gaussian noise with each judge's per-item rejudge sd added to every item, one draw per (judge, axis,
   item) shared by every arm that holds the item.  The sd comes from pairs of cells that judged the same responses
   under near-identical designs (REPEAT_CELLS: the stacked plain cells at k = 2, 4 and 6 for the LLM judges, 12, 24
   and 31 axes a request for Jev): the sd of the centred pair difference over root 2.  The LLM judges' pairs differ
   a little in design, so their sd overstates pure rejudging slightly; Jev is deterministic given a request, so its
   sd is the effect of packaging the request differently.  Written once to <output_dir>/judge_response_rejudge_noise.json
   and read from there after.

The three are reported separately and in quadrature.  Also each arm's rho on each of the three ninths of a third dump
(parts 0, 3 and 6 of the split in 9) as a cruder check of (1), and with --drop_instructions the effect on every arm
of dropping one and two of the entity's instructions from the judged items (the vectors keep them all: this is the
judging side of "more instructions per entity" only).

Output: <output_dir>/judge_response_error_bars_<third|ninth>.json (an envelope with the table and the draws' sizes),
and the table on stdout.  To redo on another data set (the October tree): make each judge's settled dump there with
judge_response_pareto.py --stack_group g61 --judge <luna|haiku|gemini|jev> (the --judge <luna3|...> runs for the
thirds) with that tree's --experiments_dir, --data_dir and --cache_dir, then run this script with the same flags.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import rankdata

_SCRIPT_PATH = Path(__file__).resolve()
REPO = _SCRIPT_PATH.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
import judge_response_pareto as jp  # noqa: E402
from assistant_axis import json_metadata  # noqa: E402
from assistant_axis.judge_score_combine import tier_judge_weights  # noqa: E402
from assistant_axis.provenance import CACHE_POLICIES, current_file_input, current_files_input, load_and_register  # noqa: E402

rob = jp.rob

#: cells that judged the same responses under near-identical designs, per model: the rejudge noise is read off their
#: pairwise differences (the ninth's stacked plain cells for the LLM judges, Gemini's on its 1/27 part; Jev's noul
#: at three request sizes)
REPEAT_CELLS = {
    jp.LUNA: ["@rk_pnn20_s9p0g61_k2", "@rk_pnn20_s9p0g61_k4", "@rk_pnn20_s9p0g61_k6"],
    jp.HAIKU: ["@rk_pnn20_s9p0g61_k2", "@rk_pnn20_s9p0g61_k4", "@rk_pnn20_s9p0g61_k6"],
    jp.GEMINI: ["@rk_pnn20_s27p0g61_k2", "@rk_pnn20_s27p0g61_k4", "@rk_pnn20_s27p0g61_k6"],
    jp.JEV: ["@jb61_noul_a20m31_s9p0", "@jb61_noul_a20m24_s9p0", "@jb61_noul_a20m12_s9p0"],
}
NOISE_FILE = "judge_response_rejudge_noise.json"


# ----------------------------------------------------------------------------------------------------------------
# pure pieces (tested in results_analysis/tests/test_judge_response_error_bars.py)

def rejudge_sigma(pairs: Iterable[Tuple[Dict, Dict]]) -> Tuple[float, int, float]:
    """(per-item rejudge sd, items, mean |shift|) from pairs of cells on the same items: for each pair the difference
    on the common items, centred (a shift between designs is not rejudging noise); the sd of all the centred
    differences over root 2."""
    diffs, shifts = [], []
    for a, b in pairs:
        common = [k for k in a if k in b]
        if len(common) < 10:
            continue
        d = np.array([a[k] - b[k] for k in common], dtype=float)
        shifts.append(abs(float(d.mean())))
        diffs.append(d - d.mean())
    if not diffs:
        return float("nan"), 0, float("nan")
    d = np.concatenate(diffs)
    return float(d.std() / np.sqrt(2)), int(len(d)), float(np.mean(shifts))


def member_arrays(sel: Dict[Tuple[str, int, int], float], ent_index: Dict[str, int], q_index: Dict[int, int],
                  rank: Dict[str, int], item_index: Dict[Tuple[str, int, int], int]) -> dict:
    """One arm member's items as arrays: entity index, question index, score, instruction index, the item's ninth
    ((q + rank) % 9, the cut the dumps' thirds are built from) and its index in the judge's own item list."""
    keys = [k for k in sel if k[0] in ent_index]
    return dict(e=np.array([ent_index[k[0]] for k in keys], dtype=np.int64),
                qi=np.array([q_index[k[2]] for k in keys], dtype=np.int64),
                v=np.array([sel[k] for k in keys], dtype=float),
                p=np.array([k[1] for k in keys], dtype=np.int64),
                ninth=np.array([(k[2] + rank[k[0]]) % 9 for k in keys], dtype=np.int64),
                ii=np.array([item_index[k] for k in keys], dtype=np.int64))


def blended_means(members: Sequence[dict], weights: Dict[str, float], n_entities: int, wq: Optional[np.ndarray] = None,
                  ninth_part: Optional[int] = None, eps: Optional[Dict[str, np.ndarray]] = None,
                  drop_p: Sequence[int] = ()) -> np.ndarray:
    """The arm's blended per-entity means (nan where no member scored the entity), as combine_tier_judges blends
    them: each member's mean over its items, weighted by question multiplicity wq, restricted to one ninth or to
    the instructions not in drop_p, its scores shifted by eps[judge][item] when rejudging; the judges' means
    weighted and renormalised over the judges that scored the entity."""
    num = np.zeros(n_entities)
    den = np.zeros(n_entities)
    for mb in members:
        w = np.ones(len(mb["v"])) if wq is None else wq[mb["qi"]]
        if ninth_part is not None:
            w = w * (mb["ninth"] == ninth_part)
        for dp in drop_p:
            w = w * (mb["p"] != dp)
        v = mb["v"] if eps is None else mb["v"] + eps[mb["judge"]][mb["ii"]]
        s = np.bincount(mb["e"], weights=w * v, minlength=n_entities)
        c = np.bincount(mb["e"], weights=w, minlength=n_entities)
        has = c > 0
        num += weights[mb["model"]] * np.where(has, s / np.where(has, c, 1.0), 0.0)
        den += weights[mb["model"]] * has
    return np.where(den > 0, num / np.where(den > 0, den, 1.0), np.nan)


def spearman_each(m: np.ndarray, pv: Dict[str, np.ndarray]) -> np.ndarray:
    """Spearman rho of the means m with each variant's projection vector (nan entries of either dropped; nan below
    three pairs), in pv's order."""
    out = np.empty(len(pv))
    for i, p in enumerate(pv.values()):
        mask = np.isfinite(m) & np.isfinite(p)
        if mask.sum() < 3:
            out[i] = np.nan
            continue
        out[i] = np.corrcoef(rankdata(m[mask]), rankdata(p[mask]))[0, 1]
    return out


# ----------------------------------------------------------------------------------------------------------------

class Arrays:
    """Everything the draws need, built once: per axis the projection vectors and every arm's member arrays."""

    def __init__(self, data: jp.Data, proj: dict, vkeys: List[str], loaded: Dict[str, tuple], arms: List[dict]):
        self.arms = arms
        self.model_of = {j: loaded[j][0]["model"] for j in loaded}
        self.weights = tier_judge_weights(list(self.model_of.values()))
        bare_names = sorted(data.rank)
        lifted = sorted(rob.lift_scores({n: float(i) for i, n in enumerate(bare_names)}, data.kinds).items(), key=lambda kv: kv[1])
        self.ent_bare = [bare_names[int(v)] for _, v in lifted]
        self.ent_lifted = [k for k, _ in lifted]
        self.ent_index = {b: i for i, b in enumerate(self.ent_bare)}
        self.n_entities = len(self.ent_bare)
        self.Q = sorted({q for j in loaded for it in loaded[j][1].values() for (_, _, q) in it})
        self.q_index = {q: i for i, q in enumerate(self.Q)}
        self.instructions = sorted({p for j in loaded for it in loaded[j][1].values() for (_, p, _) in it})
        self.axes = []
        for ax in data.axes:
            poles = {ax.pos, ax.neg}
            pv = {vk: np.array([proj[ax.axis_dir][vk].get(k, np.nan) if self.ent_bare[i] not in poles else np.nan
                                for i, k in enumerate(self.ent_lifted)], dtype=float) for vk in vkeys}
            item_index = {j: {k: i for i, k in enumerate(loaded[j][1][ax.axis_dir])} for j in loaded}
            n_items = {j: len(item_index[j]) for j in loaded}
            members = []
            for a in arms:
                ms = []
                for j, items, share in a["members"]:
                    sel = jp.subsample(items[ax.axis_dir], data.rank, data.qabs, jp.FRACTION_K, 0, share)
                    ms.append(dict(judge=j, model=self.model_of[j],
                                   **member_arrays(sel, self.ent_index, self.q_index, data.rank, item_index[j])))
                members.append(ms)
            self.axes.append((ax, pv, members, n_items))
        self.fam_of: Dict[str, List[int]] = {}
        for ai, a in enumerate(arms):
            self.fam_of.setdefault(a["family"], []).append(ai)
        self.fams = list(self.fam_of)

    def arm_rhos(self, sigma: Optional[Dict[str, float]] = None, rng=None, **kw) -> np.ndarray:
        """(n_arms, n_axes): each arm's mean rho over the variants per axis under the draw (kw: wq, ninth_part,
        drop_p; sigma with rng: rejudging noise)."""
        res = np.empty((len(self.arms), len(self.axes)))
        for xi, (ax, pv, members, n_items) in enumerate(self.axes):
            eps = {j: rng.normal(0.0, sigma[self.model_of[j]], n) for j, n in n_items.items()} if sigma else None
            for ai, ms in enumerate(members):
                m = blended_means(ms, self.weights, self.n_entities, eps=eps, **kw)
                res[ai, xi] = np.nanmean(spearman_each(m, pv))
        return res

    def by_family(self, res: np.ndarray) -> np.ndarray:
        """(n_families, n_axes): a family's arms (a split's assignments of the shares) averaged."""
        return np.array([res[idx].mean(axis=0) for idx in self.fam_of.values()])


def rejudge_noise(data: jp.Data, path: Path, policy: str, inputs: list, recompute: bool) -> Dict[str, float]:
    """{model: per-item rejudge sd}, from REPEAT_CELLS on data's axes; written to path with provenance, read from
    there when present."""
    if path.exists() and not recompute:
        payload, _spec, _check = load_and_register(path, dep_key="rejudge_noise", inputs=inputs, policy=policy)
        return {m: v["sigma"] for m, v in payload.items()}
    record, paths = {}, []
    for model, labels in REPEAT_CELLS.items():
        pairs, n_axes = [], 0
        for ax in data.axes:
            cells = {lab: data.cell(ax.axis_dir, model, lab) for lab in labels}
            if any(c is None for c in cells.values()):
                continue
            n_axes += 1
            paths += [data.E / f"{ax.axis_dir}{rob.TIER_EVAL_SUFFIX}" / f"{model}{lab}" / "scores_responses.json" for lab in labels]
            pairs += [(cells[a], cells[b]) for a, b in itertools.combinations(labels, 2)]
        sigma, n, shift = rejudge_sigma(pairs)
        record[model] = dict(sigma=sigma, n_items=n, n_pairs=len(pairs), n_axes=n_axes, mean_abs_shift=shift, cells=labels)
        print(f"[rejudge noise] {model}: sd {sigma:.2f} over {n} items of {len(pairs)} pairs on {n_axes} axes; "
              f"mean |shift| between cells {shift:.2f}", file=sys.stderr)
    cells_input = current_files_input(dep_key="repeat_cells", paths=paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_metadata(record, inputs=[cells_input], title="per-item rejudge noise of the response judges"), indent=1))
    inputs.append(current_file_input(dep_key="rejudge_noise", path=path))
    return {m: v["sigma"] for m, v in record.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--experiments_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR))
    ap.add_argument("--data_dir", default=str(rob.DEFAULT_DATA_DIR))
    ap.add_argument("--instructions_dir", default="/tmp/claude-501/corpus_2026-05-24/data")
    ap.add_argument("--cache_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR / "_tier_eval_scratch" / "robustness_cache"))
    ap.add_argument("--axes_file", default=jp.AXES_61)
    ap.add_argument("--output_dir", default=str(rob.DEFAULT_EXPERIMENTS_DIR / "response_pareto"))
    ap.add_argument("--dumps", choices=["third", "ninth"], default="third",
                    help="the settled dumps to read: the thirds (settled61/<judge>3.json.gz) or the ninths (<judge>.json.gz)")
    ap.add_argument("--B_questions", type=int, default=200)
    ap.add_argument("--B_axes", type=int, default=2000)
    ap.add_argument("--B_rejudge", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261107)
    ap.add_argument("--drop_instructions", action="store_true", help="also the effect of dropping one and two instructions from the judged items")
    ap.add_argument("--recompute_noise", action="store_true", help=f"re-estimate the rejudge noise although {NOISE_FILE} exists")
    ap.add_argument("--cache-policy", choices=CACHE_POLICIES, default="warn")
    args = ap.parse_args()

    E, data_dir, out = Path(args.experiments_dir), Path(args.data_dir).resolve(), Path(args.output_dir)
    data = jp.Data(E, Path(args.axes_file), data_dir, Path(args.instructions_dir))
    inputs = [current_file_input(dep_key="producer_script", path=_SCRIPT_PATH)] + list(data.inputs)
    suffix = "3" if args.dumps == "third" else ""
    loaded = {}
    for j in jp.MIX_JUDGES:
        p = jp.settled_path(E, j + suffix)
        if not p.exists():
            print(f"no settled dump for {j}: {p} (run judge_response_pareto.py --stack_group g61 --judge {j}{suffix})", file=sys.stderr)
            continue
        loaded[j] = jp.load_settled(p)
        inputs.append(current_file_input(dep_key=f"dump_{j}", path=p))
    if len(loaded) < 2:
        raise SystemExit("fewer than two settled dumps")
    sigma = rejudge_noise(data, out / NOISE_FILE, args.cache_policy, inputs, args.recompute_noise)
    _variants, vkeys, proj = jp.projections(data, Path(args.cache_dir), data_dir)
    arms = [a for a in jp.mix_arms(loaded) if "@every" not in a["key"]]        # alone, and the golden splits
    A = Arrays(data, proj, vkeys, loaded, arms)
    print(f"{A.n_entities} entities, {len(A.Q)} question positions, {len(A.instructions)} instructions, {len(arms)} arms, {len(A.axes)} axes",
          file=sys.stderr)

    point_ax = A.by_family(A.arm_rhos())
    point = point_ax.mean(axis=1)
    rng = np.random.default_rng(args.seed)
    nQ = len(A.Q)
    DQ = np.empty((args.B_questions, len(A.fams)))
    for b in range(args.B_questions):
        DQ[b] = A.by_family(A.arm_rhos(wq=rng.multinomial(nQ, np.full(nQ, 1.0 / nQ)).astype(float))).mean(axis=1)
    DA = np.empty((args.B_axes, len(A.fams)))
    for b in range(args.B_axes):
        DA[b] = point_ax[:, rng.integers(0, len(A.axes), len(A.axes))].mean(axis=1)
    DR = np.empty((args.B_rejudge, len(A.fams)))
    for b in range(args.B_rejudge):
        DR[b] = A.by_family(A.arm_rhos(sigma=sigma, rng=rng)).mean(axis=1)
    ninths = {p: A.by_family(A.arm_rhos(ninth_part=p)).mean(axis=1) for p in (0, 3, 6)}
    drops = None
    if args.drop_instructions:
        P = A.instructions
        d1 = np.array([A.by_family(A.arm_rhos(drop_p=(p,))).mean(axis=1) for p in P])
        d2 = np.array([A.by_family(A.arm_rhos(drop_p=pp)).mean(axis=1) for pp in itertools.combinations(P, 2)])
        drops = dict(instructions=P, drop_one=d1.tolist(), drop_two=d2.tolist())

    splits = [i for i, f in enumerate(A.fams) if f.startswith("split")]
    best = max(splits, key=lambda i: point[i])
    order = sorted(range(len(A.fams)), key=lambda i: -point[i])
    sd = lambda D, i: float(D[:, i].std(ddof=1))
    dsd = lambda D, i: float((D[:, i] - D[:, best]).std(ddof=1))
    labels = {j: loaded[j][0]["label"] for j in loaded}
    print(f"\n{args.dumps} dumps ({'; '.join(labels.values())}); {len(A.axes)} axes, mean over the {len(vkeys)} variants; "
          f"draws: questions {args.B_questions}, axes {args.B_axes}, rejudging {args.B_rejudge}; the best golden split: {A.fams[best]}")
    print("paired differences from the best split; SE q = redrawing the questions, a = redrawing the axes, r = rejudging, all = quadrature sum")
    print(f"| arm | rho | quality | d vs best | SE q | SE a | SE r | SE all | d/SE |")
    print("|---|---|---|---|---|---|---|---|---|")
    rows = []
    for i in order:
        r = float(point[i]); q = 1 / (1 - r)
        d = r - float(point[best]); ds = (dsd(DQ, i), dsd(DA, i), dsd(DR, i)); d_all = float(np.sqrt(sum(x * x for x in ds)))
        s = (sd(DQ, i), sd(DA, i), sd(DR, i))
        print(f"| {A.fams[i]} | {r:.4f} | {q:.3f} | {d:+.4f} | {ds[0]:.4f} | {ds[1]:.4f} | {ds[2]:.4f} | {d_all:.4f} | {d / d_all if d_all > 0 else 0:.1f} |")
        row = dict(arm=A.fams[i], rho=r, quality=q, d_vs_best=d, d_se_q=ds[0], d_se_a=ds[1], d_se_r=ds[2], d_se_all=d_all,
                   se_q=s[0], se_a=s[1], se_r=s[2], ninths=[float(ninths[p][i]) for p in (0, 3, 6)],
                   d9_vs_best=[float(ninths[p][i] - ninths[p][best]) for p in (0, 3, 6)])
        if drops:
            r1 = np.array(drops["drop_one"])[:, i]; r2 = np.array(drops["drop_two"])[:, i]
            row.update(drop_one=float(r1.mean()), drop_one_sd=float(r1.std(ddof=1)), drop_two=float(r2.mean()))
        rows.append(row)
    print(f"\n| arm | ninth 0 | ninth 3 | ninth 6 | d vs best, mean of 3 | SE |")
    print("|---|---|---|---|---|---|")
    for row in rows:
        d9 = row["d9_vs_best"]
        print(f"| {row['arm']} | {row['ninths'][0]:.4f} | {row['ninths'][1]:.4f} | {row['ninths'][2]:.4f} | {np.mean(d9):+.4f} | {np.std(d9, ddof=1) / np.sqrt(3):.4f} |")
    if drops:
        print(f"\ninstructions {drops['instructions']}; dropping instructions from the judged items only (the vectors keep them all)")
        print("| arm | all | one dropped (mean) | d | sd over which | two dropped (mean) | d |")
        print("|---|---|---|---|---|---|---|")
        for row in rows:
            print(f"| {row['arm']} | {row['rho']:.4f} | {row['drop_one']:.4f} | {row['drop_one'] - row['rho']:+.4f} | {row['drop_one_sd']:.4f} | "
                  f"{row['drop_two']:.4f} | {row['drop_two'] - row['rho']:+.4f} |")
    result = dict(dumps=args.dumps, labels=labels, weights=A.weights, sigma=sigma, best=A.fams[best], n_axes=len(A.axes),
                  n_questions=nQ, instructions=A.instructions, B=dict(questions=args.B_questions, axes=args.B_axes, rejudge=args.B_rejudge),
                  seed=args.seed, variants=vkeys, rows=rows, drops=drops)
    out.mkdir(parents=True, exist_ok=True)
    p = out / f"judge_response_error_bars_{args.dumps}.json"
    p.write_text(json.dumps(json_metadata(result, inputs=inputs, title=f"error bars on the response-judging mixes, {args.dumps} dumps"), indent=1))
    print(f"wrote {p}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
