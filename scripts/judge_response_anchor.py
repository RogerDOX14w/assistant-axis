"""The six-axis anchor: the extrapolation to every response, checked (Roger, 2026-11-06: "make it so, with your
proposed optional extra").

Six of the 61 axes (scripts/tier_eval_axes_full6.tsv) were judged on every kept response by each judge at its settled
design (judge_response_pareto.py --judge <judge>_all6 --axes_file scripts/tier_eval_axes_full6.tsv, whose JSON holds the
measured rho at every ninth of coverage, golden subsamples of everything).  This script sets those measured curves
against what the ninth (judge_response_pareto_61*.json) and the third (..._61_<judge>3.json; Jev's third inside
..._61_jev.json) extrapolate for the same six axes with the two-part model (judge_response_pareto.arm_points): the
base lifted by its question-cut penalty on these six axes, then Spearman-Brown by question from its split-half
reliability, the gain scaled by the judge's s, both from extrapolation_calibration.json beside the figures, applied
per axis to the base's measured rho on that axis.  Per judge and design (one axis a call, and the settled design) it
reports, at every response, the measured mean rho over the six axes and the two predictions, and the s each
measurement implies beside the calibrated one.  Jev's anchor cell is
20 answers x the 6 axes a request against 30-31 on the ninth and the third (its shapes figure put 20 x 5-6 within
0.002 of 20 x 30-31).  Figure: <output_dir>/judge_response_anchor6.png, 2 rows (designs) x 4 judges; JSON beside it.
A judge whose files are missing is left out with a note.  No API calls.

Usage: uv run python scripts/judge_response_anchor.py --output_dir roger/axis_judge_experiments/response_pareto
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from assistant_axis import json_metadata, png_metadata  # noqa: E402
from assistant_axis.provenance import current_file_input  # noqa: E402
from results_analysis import judge_tier_robustness as rob  # noqa: E402
sys.path.insert(0, str(REPO / "scripts"))
from judge_response_pareto import JUDGE_SHORT, arm_calibration, penalty  # noqa: E402

AXES_61 = "scripts/tier_eval_axes.tsv"
MODEL = {"luna": "gpt-5.6-luna", "haiku": "claude-haiku-5-5", "gemini": "gemini-3.1-flash-lite", "jev": "jev-1.14.0"}
AXES_6 = "scripts/tier_eval_axes_full6.tsv"
#: per judge: display name, the ninth's JSON, the third's JSON, the anchor's JSON (under --output_dir), and the arm keys
#: (one axis a call, settled) in the ninth and third JSONs and in the anchor JSON
JUDGES = {
    "luna": dict(name="Luna", ninth="judge_response_pareto_61.json", third="judge_response_pareto_61_luna3.json",
                 anchor="judge_response_pareto_61_luna_all6.json",
                 arms={"one axis a call": ("", "gpt-5.6-luna@k1", "gpt-5.6-luna@k1"),
                       "settled": ("k=4, worst 20% one axis a call", "gpt-5.6-luna@rk_pnx20k4", "gpt-5.6-luna@rk_pnx20k4")}),
    "haiku": dict(name="Haiku 5.5", ninth="judge_response_pareto_61_haiku.json", third="judge_response_pareto_61_haiku3.json",
                  anchor="judge_response_pareto_61_haiku_all6.json",
                  arms={"one axis a call": ("", "claude-haiku-5-5@k1", "claude-haiku-5-5@k1"),
                        # the anchor cells were judged at k=2, 10%, the settled design until 2026-11-07 (k=4, 25% since); the
                        # third's parts exist at k=2 only, so the comparison stays at the measured design
                        "settled": ("k=2, worst 10% one axis a call", "claude-haiku-5-5@rk_pnx10k2", "claude-haiku-5-5@rk_pnx10k2")}),
    "gemini": dict(name="Gemini 3.1 Flash-Lite", ninth="judge_response_pareto_61_gemini.json",
                   third="judge_response_pareto_61_gemini3.json", anchor="judge_response_pareto_61_gemini_all6.json",
                   arms={"one axis a call": ("", "gemini-3.1-flash-lite@k1", "gemini-3.1-flash-lite@k1"),
                         # 25% since 2026-11-07 (Roger; 20% until then); no Gemini anchor cells, so predictions only
                         "settled": ("k=6, worst 25% one axis a call", "gemini-3.1-flash-lite@rk_pnx25k6", "gemini-3.1-flash-lite@rk_pnx25k6")}),
    # Jev: the ninth's and the third's arms are shape points of the Jev figure (the third's key ends _third)
    "jev": dict(name="Jev 1.14", ninth="judge_response_pareto_61_jev.json", third="judge_response_pareto_61_jev.json",
                anchor="judge_response_pareto_61_jev_all6.json",
                # the anchor is 20 answers x the 6 axes a request; on the six axes that shape scores 0.0074 above the production
                # shape (20 x 30-31) on the ninth, so the ninth arm compared is the same shape (20 x 5-6, shapes figure); the
                # third exists only at 20 x 30-31 and is left out here (its row would read the shape gap as coverage)
                arms={"settled": ("20 answers x 5-6 axes a request (the anchor's shape; production 20 x 30-31)",
                                  "jev-1.14.0@noul_a20m6", "jev-1.14.0@k1")}),
}
STYLE = {"measured": ("#222222", "o", "-"), "from the ninth": ("#D95F02", "s", ":"), "from the third": ("#1B9E77", "^", "--")}


def load_points(path: Path) -> Optional[Dict[str, dict]]:
    if not path.exists():
        return None
    return json.load(open(path))["result"]["points"]


def arm_points(points: Dict[str, dict], arm: str) -> List[dict]:
    return sorted((p for p in points.values() if p["arm"] == arm), key=lambda p: p["coverage"])


def base_of(points: Dict[str, dict], arm: str):
    """(coverage, per-axis rho by variant, the arm's own split-half reliability) of an arm's largest measured point in a
    ninth or third JSON.  The reliability is ``reliability_cut``, measured on the cut share, so that ``lifted`` raises it
    to the golden-over-cut ratio once; ``reliability`` on the same point is already raised (until the fix of 2026-11-07
    the ratio was applied twice, and Jev's base met the 0.9999 cap, which read as an implied s of 154)."""
    ps = arm_points(points, arm)
    measured = [p for p in ps if p["measured"] and p.get("per_axis")]
    extrap = [p for p in ps if not p["measured"] and "reliability_cut" in p]
    if not measured or not extrap:
        return None
    b = measured[-1]
    return b["coverage"], b["per_axis"], extrap[0]["reliability_cut"]


def load_check(path: Path) -> dict:
    """The two-part extrapolation's calibration a figure JSON carries (judge_response_pareto.two_part_calibration)."""
    check = json.load(open(path))["result"]["extrapolation_check"]
    if "per_judge" not in check:
        raise SystemExit(f"{path}: drawn before the two-part extrapolation (2026-11-07); redraw it first")
    return check


def lifted(base, idx: List[int], cal: dict):
    """(lift, R_g, lifted per-axis rho) of a base: the question-cut penalty on the anchor axes at the base's coverage, and the
    reliability raised to the judge's golden-over-cut ratio below a third (judge_response_pareto.arm_points does the same)."""
    b, per_axis, R = base
    lift = penalty(cal["delta9"], b)
    R_g = min(R * (cal["ratio"] if b < 1 / 3 - 1e-9 else 1.0), 0.9999)
    return lift, R_g, {vk: [per_axis[vk][i] + lift for i in idx] for vk in per_axis}


def predict(base, cov: float, idx: List[int], cal: dict) -> float:
    """Mean over variants and the anchor axes (idx into the 61) of the base's per-axis rho carried to cov in two parts:
    the base lifted by its question-cut penalty, then Spearman-Brown from R_g, the gain scaled by the judge's s."""
    M = cov / base[0]
    if M < 1 - 1e-9:
        return float("nan")
    lift, R_g, rho_g = lifted(base, idx, cal)
    RM = M * R_g / (1 + (M - 1) * R_g)
    f = 1 + cal["s"] * (math.sqrt(RM / R_g) - 1)
    return float(np.mean([[r * f for r in rho_g[vk]] for vk in rho_g]))


def raw_gain(base, cov: float, idx: List[int], cal: dict) -> float:
    """The unscaled Spearman-Brown gain from the lifted base to cov, mean over variants and the anchor axes: what one
    unit of s buys, so that (measured - lifted base) / raw_gain is the s the measurement implies."""
    M = cov / base[0]
    lift, R_g, rho_g = lifted(base, idx, cal)
    RM = M * R_g / (1 + (M - 1) * R_g)
    return float(np.mean([[r * (math.sqrt(RM / R_g) - 1) for r in rho_g[vk]] for vk in rho_g]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output_dir", required=True, help="where the judges' figure JSONs are, and where the output goes")
    ap.add_argument("--y", choices=("rho", "quality"), default="rho",
                    help="the y axis: mean rho, or its quality 1 / (1 - mean rho) as the Pareto figures draw it (Roger, "
                         "2026-11-07); quality writes judge_response_anchor6_quality.png, the JSON stays in rho")
    ap.add_argument("--axes_file", default=AXES_61)
    ap.add_argument("--anchor_axes_file", default=AXES_6)
    args = ap.parse_args(argv)
    out = Path(args.output_dir)
    axes61 = [a.axis_dir for a in rob.read_axes_tsv(Path(args.axes_file))]
    axes6 = [a.axis_dir for a in rob.read_axes_tsv(Path(args.anchor_axes_file))]
    idx61 = [axes61.index(a) for a in axes6]
    inputs = [current_file_input("axes_file", Path(args.axes_file)), current_file_input("anchor_axes_file", Path(args.anchor_axes_file))]
    rows, curves = [], {}
    for j, J in JUDGES.items():
        files = {k: out / J[k] for k in ("ninth", "third", "anchor")}
        pts = {k: load_points(f) for k, f in files.items()}
        for k, f in files.items():
            if pts[k] is not None:
                inputs.append(current_file_input(f"{j}_{k}", f))
        if pts["anchor"] is None:
            print(f"[anchor] {j}: no anchor JSON ({files['anchor'].name}); predictions only", file=sys.stderr)
        check = load_check(files["ninth"])
        cal = arm_calibration(check, [MODEL[j]], axes6)
        for design, (detail, arm, anchor_arm) in J["arms"].items():
            bases = {}
            if pts["ninth"] is not None:
                bases["from the ninth"] = base_of(pts["ninth"], arm)
            if pts["third"] is not None and (files["third"] != files["ninth"] or J.get("third_arm_suffix")):
                bases["from the third"] = base_of(pts["third"], arm + J.get("third_arm_suffix", ""))
            bases = {k: v for k, v in bases.items() if v}
            measured = {}
            if pts["anchor"] is not None:
                for p in arm_points(pts["anchor"], anchor_arm):
                    if p["measured"]:
                        measured[p["coverage"]] = float(np.mean(list(p["rho"].values())))
            covs = sorted(set(measured) | {1 / 9, 2 / 9, 1 / 3, 2 / 3, 1.0})
            curve = {"measured": measured, **{k: {c: predict(b, c, idx61, cal) for c in covs if c >= b[0] - 1e-9} for k, b in bases.items()},
                     "base_points": {k: (b[0], float(np.mean([[b[1][vk][i] for i in idx61] for vk in b[1]]))) for k, b in bases.items()},
                     "calibration": cal}
            curve["detail"] = detail
            curves[(j, design)] = curve
            for k, b in bases.items():
                lift = penalty(cal["delta9"], b[0])
                row = dict(judge=j, design=design, base=k, base_coverage=b[0], base_rho_6=curve["base_points"][k][1], lift=lift,
                           s=cal["s"], predicted_all=predict(b, 1.0, idx61, cal), measured_all=measured.get(1.0))
                if measured.get(1.0) is not None:
                    row["implied_s"] = (measured[1.0] - curve["base_points"][k][1] - lift) / raw_gain(b, 1.0, idx61, cal)
                rows.append(row)
                print(f"[anchor] {J['name']:22s} {design + (': ' + detail if detail else ''):52s} {k:15s} base {b[0]:.3f} rho {row['base_rho_6']:.4f} "
                      f"lift {lift:+.4f} -> all predicted {row['predicted_all']:.4f}" +
                      (f", measured {measured[1.0]:.4f}, implied s {row['implied_s']:.2f} (calibrated {cal['s']:.2f})"
                       if measured.get(1.0) is not None else ", measured: not yet"), file=sys.stderr)
    # the figure: designs x judges
    designs = list(dict.fromkeys(d for _, d in curves))
    judges = [j for j in JUDGES if any(jj == j for jj, _ in curves)]
    quality = args.y == "quality"
    yv = (lambda r: 1.0 / (1.0 - r)) if quality else (lambda r: r)
    fig, axs = plt.subplots(len(designs), len(judges), figsize=(4.6 * len(judges), 3.9 * len(designs) + 1.6), squeeze=False)
    for r, design in enumerate(designs):
        for c, j in enumerate(judges):
            ax = axs[r][c]
            cur = curves.get((j, design))
            if cur is None:
                ax.set_visible(False)
                continue
            for k, (col, mk, ls) in STYLE.items():
                if not isinstance(cur.get(k), dict) or not cur[k]:
                    continue
                xs = sorted(cur[k])
                ax.plot(xs, [yv(cur[k][x]) for x in xs], ls, color=col, marker=mk, label=k if k == "measured" else f"extrapolated {k}", lw=1.2)
            for k, (b, rho) in cur["base_points"].items():
                ax.scatter([b], [yv(rho)], s=70, facecolors="none", edgecolors=STYLE[k][0], linewidths=1.4, zorder=4,
                           label=f"measured, {k.split()[-1]} cut by question")
            ax.set_xscale("log")
            ax.set_xticks([1 / 9, 1 / 3, 1.0])
            ax.set_xticklabels(["1/9", "1/3", "all"])
            ax.minorticks_off()
            ax.grid(True, alpha=0.3)
            ax.set_title(f"{JUDGES[j]['name']}: {design}" + ("\n" + textwrap.fill(cur["detail"], 44) if cur["detail"] else ""), fontsize=9)
            if c == 0:
                ax.set_ylabel("1 / (1 - mean rho), 12 variants, 6 axes" if quality else "mean rho, 12 variants, 6 axes", fontsize=9)
            if r == len(designs) - 1:
                ax.set_xlabel("coverage of the kept responses", fontsize=9)
    handles, labels = axs[0][0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=5, fontsize=8.5, frameon=False)
    title = "Response judging, the six-axis anchor: measured at every coverage against the ninth's and the third's extrapolations"
    fig.suptitle(title, fontsize=12, fontweight="bold")
    cals = {j: cur["calibration"] for (j, _), cur in curves.items()}
    cal_text = "; ".join(f"{JUDGES[j]['name']} lift at a ninth {c['delta9']:+.4f}, s {c['s']:.2f}"
                         + ("" if c["judges"] == [j] else " (the others' mean)") for j, c in cals.items())
    sub = "\n".join(textwrap.wrap(f"{len(axes6)} axes ({args.anchor_axes_file}): " + ", ".join(axes6) + "; each judge at its settled design, "
                                   "measured on every kept response and golden subsamples of it; the extrapolations in two parts "
                                   "(judge_response_pareto.two_part_calibration): each base lifted by its question-cut penalty on these six "
                                   "axes, then Spearman-Brown by question from its reliability, the gain scaled by the judge's s "
                                   f"({cal_text})", 200))
    fig.text(0.5, 0.95, sub, ha="center", va="top", fontsize=8)
    fig.subplots_adjust(top=0.86, bottom=0.14, left=0.06, right=0.985, hspace=0.45, wspace=0.22)
    out.mkdir(parents=True, exist_ok=True)
    png = out / ("judge_response_anchor6_quality.png" if quality else "judge_response_anchor6.png")
    fig.savefig(png, dpi=130, metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
    result = {"config": {"anchor_axes": axes6, "y": args.y, "png": png.name}, "rows": rows,
              "curves": {f"{j}|{d}": {k: ({str(c): v for c, v in cur[k].items()} if isinstance(cur[k], dict) else cur[k])
                                      for k in cur} for (j, d), cur in curves.items()}}
    (out / "judge_response_anchor6.json").write_text(json.dumps(json_metadata(result, title=title, inputs=inputs), indent=1))
    print(f"wrote {png} and judge_response_anchor6.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
