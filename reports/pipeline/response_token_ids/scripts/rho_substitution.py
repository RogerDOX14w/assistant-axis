"""Measurement 4(b) of the response-token-ids sample (plan § 9): rho on the
judged axes recomputed with the sample's vectors substituted into a clone of
the October tree, per step-2 variant, with results_analysis/judge_tier_robustness.py
(raw regime, slots 0 and 6, layers 25 and 49, the production judge cells).

For each variant, a clone of the October tree is built under --work from
symlinks to its vector files (the tool reads traits/vectors, roles/vectors
and combinations/vectors/default.pt, and fingerprints them by name, size and
mtime, so a clone gets its own slice cache), and the vector of every sampled
trait or role that the variant has is a symlink to the sample's file instead.
The judge caches cover the entities of the May corpus, so only the sampled
entities that were in it enter rho; the others' substitution is harmless and
is done anyway.  The default is not substituted (it cancels in rho).  The 61
axes go in through an axes file in which a pole the corpus has renamed since
the axis was judged is named by its current stem, so that its October vector
is found (entity_id.resolve_renamed_stem).

The untouched October tree is the baseline (its own run, or --baseline, an
earlier run's JSON).  The text variant against the baseline is the sampling
floor at rho level (the same entities, a fresh T = 0.7 sample through
today's path); ids and turn against text are the path effect.

Run locally after the pull:
    uv run python rho_substitution.py \
        --october "runpod_workspace/qwen/qwen-3-32b Roger October" \
        --sample "runpod_workspace/qwen/qwen-3-32b Roger sample-ids" \
        --work <scratch dir> --out <prefix> [--variants text ids turn] [--baseline <json>]
Writes <out>.json (per model, axis and tool variant: rho of the baseline and
of every variant, the deltas) and prints, per model and tool variant, the
mean and the largest |delta rho| over axes for each comparison.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROLES = "gamer child researcher specialist witness operator angel".split()
TRAITS = ("aural_vark plugged_in millennial stream_of_consciousness gen_z thorough verbose "
          "exclusionary autistic flirty").split()
KIND_OF = {**{e: "roles" for e in ROLES}, **{e: "traits" for e in TRAITS}}
MODELS = ("gpt-5.6-luna+claude-haiku-5-5@b10n20x2", "gpt-5.6-luna@none@b10n20x2")
TOOL = Path("results_analysis/judge_tier_robustness.py")


def unwrap(obj):
    if isinstance(obj, dict) and "result" in obj and set(obj) <= {"result", "_provenance", "schema_version"}:
        return obj["result"]
    return obj


def axes_file(experiments_dir: Path, october: Path, path: Path, log=print) -> int:
    """'axis_dir pos neg pair_type' for every judged axis, a renamed pole by
    its current stem when its October vector is under that."""
    from assistant_axis.entity_id import resolve_renamed_stem
    rows = []
    for d in sorted(experiments_dir.iterdir()):
        if not (d / "gpt" / "scores_descriptions.json").exists() or "_vs_" not in d.name:
            continue
        pos, neg = d.name.split("_vs_", 1)
        cfg = d / "gpt" / "config.json"
        pair_type = None
        if cfg.exists():
            args = (unwrap(json.loads(cfg.read_text())) or {}).get("args", {})
            if args.get("pair") and len(args["pair"]) == 2:
                pos, neg = args["pair"]
            pair_type = args.get("pair_type")
        if pair_type not in ("roles", "traits"):
            kinds = [k for k in ("traits", "roles")
                     if (october / k / "vectors" / f"{pos}.pt").exists() and (october / k / "vectors" / f"{neg}.pt").exists()]
            if len(kinds) != 1:
                raise ValueError(f"{d.name}: pair type unknown and the poles are in {kinds}")
            pair_type = kinds[0]
        poles = []
        for stem in (pos, neg):
            if not (october / pair_type / "vectors" / f"{stem}.pt").exists():
                new = resolve_renamed_stem(stem, pair_type)
                if new == stem or not (october / pair_type / "vectors" / f"{new}.pt").exists():
                    raise KeyError(f"{d.name}: no October vector for pole {stem} ({pair_type}), nor under a renamed stem")
                log(f"[axes] {d.name}: pole {stem} is {new} now; the axis file names {new}")
                stem = new
            poles.append(stem)
        rows.append(f"{d.name} {poles[0]} {poles[1]} {pair_type}")
    path.write_text("\n".join(rows) + "\n")
    return len(rows)


def build_clone(october: Path, clone: Path, sample: Path | None, variant: str | None, log=print) -> list:
    """Symlinks to the October vectors, the sampled entities' pointing at the
    sample's vec_<variant> files instead.  Returns the substituted stems."""
    substituted = []
    for kind in ("traits", "roles", "combinations"):
        src_dir = october / kind / "vectors"
        dst_dir = clone / kind / "vectors"
        dst_dir.mkdir(parents=True, exist_ok=True)
        names = [p.name for p in src_dir.glob("*.pt")] if kind != "combinations" else ["default.pt"]
        for name in names:
            dst = dst_dir / name
            if dst.is_symlink() or dst.exists():
                dst.unlink()
            src = src_dir / name
            if sample is not None and kind != "combinations" and KIND_OF.get(name[:-3]) == kind:
                cand = sample / f"vec_{variant}" / name
                if cand.exists():
                    src = cand
                    substituted.append(name[:-3])
            os.symlink(src.resolve(), dst)
    log(f"[clone] {clone}: {len(substituted)} substituted" + (f" ({' '.join(sorted(substituted))})" if substituted else ""))
    return sorted(substituted)


def run_tool(data_dir: Path, axes_path: Path, out_dir: Path, cache_dir: Path, models, draws: int, repo: Path, log=print) -> dict:
    cmd = [sys.executable, str(repo / TOOL), "--data_dir", str(data_dir), "--regimes", "raw",
           "--axes_file", str(axes_path), "--include_models", *models, "--bootstrap_draws", str(draws),
           "--output_dir", str(out_dir), "--cache_dir", str(cache_dir)]
    t0 = time.time()
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    (out_dir / "run.log").write_text(r.stdout + r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"{TOOL} failed on {data_dir} (exit {r.returncode}); log at {out_dir / 'run.log'}:\n"
                         + (r.stdout + r.stderr)[-3000:])
    log(f"[tool] {data_dir.name}: {time.time() - t0:.0f} s")
    return unwrap(json.loads((out_dir / "judge_tier_robustness.json").read_text()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--october", required=True)
    ap.add_argument("--sample", required=True)
    ap.add_argument("--work", required=True, help="clones, caches and the tool's outputs go here")
    ap.add_argument("--out", required=True, help="output prefix: <out>.json")
    ap.add_argument("--variants", nargs="+", default=["text", "ids", "turn"])
    ap.add_argument("--baseline", default=None, help="an earlier run's judge_tier_robustness.json on the untouched tree")
    ap.add_argument("--experiments_dir", default="roger/axis_judge_experiments")
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--bootstrap_draws", type=int, default=200)
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()
    october, sample, work, repo = Path(args.october).resolve(), Path(args.sample).resolve(), Path(args.work), Path(args.repo).resolve()
    work.mkdir(parents=True, exist_ok=True)
    axes_path = work / "axes.tsv"
    n_axes = axes_file(repo / args.experiments_dir, october, axes_path)
    print(f"[axes] {n_axes} axes in {axes_path}")
    if args.baseline:
        base = unwrap(json.loads(Path(args.baseline).read_text()))
        print(f"[baseline] {args.baseline}")
    else:
        build_clone(october, work / "clone_baseline", None, None)
        base = run_tool(work / "clone_baseline", axes_path, work / "rho_baseline", work / "cache_baseline",
                        args.models, args.bootstrap_draws, repo)
    runs = {}
    subs = {}
    for v in args.variants:
        if not (sample / f"vec_{v}").is_dir():
            print(f"[skip] no {sample / f'vec_{v}'}", file=sys.stderr)
            continue
        subs[v] = build_clone(october, work / f"clone_{v}", sample, v)
        runs[v] = run_tool(work / f"clone_{v}", axes_path, work / f"rho_{v}", work / f"cache_{v}",
                           args.models, args.bootstrap_draws, repo)
    tool_variants = base["config"]["variants"]
    comparisons = [(v, "baseline") for v in runs] + [(v, "text") for v in runs if v != "text" and "text" in runs]
    result = {"october": str(october), "sample": str(sample), "axes": n_axes, "models": args.models,
              "tool_variants": tool_variants, "substituted": subs, "rho": {}, "n": {}, "delta": {}, "summary": {}}
    print(f"\n{'model':40} {'tool variant':12} {'comparison':16} {'mean d':>8} {'mean |d|':>8} {'max |d|':>8}  axis of max")
    for m in args.models:
        result["rho"][m] = {"baseline": base["rho"][m], **{v: r["rho"][m] for v, r in runs.items()}}
        result["n"][m] = {"baseline": base["n"][m], **{v: r["n"][m] for v, r in runs.items()}}
        for tv in tool_variants:
            for a, b in comparisons:
                ra = runs[a]["rho"][m]
                rb = base["rho"][m] if b == "baseline" else runs[b]["rho"][m]
                axes_common = [ax for ax in ra if ax in rb and ra[ax].get(tv) is not None and rb[ax].get(tv) is not None]
                d = np.array([ra[ax][tv] - rb[ax][tv] for ax in axes_common])
                for ax in axes_common:
                    if result["n"][m][a].get(ax) != result["n"][m][b if b != "baseline" else "baseline"].get(ax):
                        print(f"WARNING: {m} {ax}: n differs between {a} and {b}", file=sys.stderr)
                key = f"{a}-{b}"
                result["delta"].setdefault(m, {}).setdefault(tv, {})[key] = dict(zip(axes_common, d.tolist()))
                k = int(np.argmax(np.abs(d))) if len(d) else None
                row = {"n_axes": len(d), "mean": float(d.mean()) if len(d) else None,
                       "mean_abs": float(np.abs(d).mean()) if len(d) else None,
                       "max_abs": float(np.abs(d).max()) if len(d) else None,
                       "axis_of_max": axes_common[k] if k is not None else None}
                result["summary"].setdefault(m, {}).setdefault(tv, {})[key] = row
                print(f"{m:40} {tv:12} {key:16} {row['mean'] if row['mean'] is not None else float('nan'):+8.4f} "
                      f"{row['mean_abs'] if row['mean_abs'] is not None else float('nan'):8.4f} "
                      f"{row['max_abs'] if row['max_abs'] is not None else float('nan'):8.4f}  {row['axis_of_max']}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result) + "\n")
    print(f"wrote {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
