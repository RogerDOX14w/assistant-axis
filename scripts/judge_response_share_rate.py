#!/usr/bin/env python3
"""The share of axes judged one axis a call, read by the exchange rate between share and coverage (Roger, 2026-11-07:
"average the quality score for the different percentages, compare their average-over-12, and compare the resulting
quality/price slope to the slope between the top two hollow circle plotted points").

For one judge at one stacking format and k, from the figure JSON judge_response_pareto.py --stack_group g61 writes
(judge_response_pareto_61[_<judge>][_<format>].json): for each share of the worst axes (10, 15, 20, 25%) the quality
averaged over the 12 projection variants, the mean of each panel's 1 / (1 - rho) (the figures' y axis), at the measured
base (the ninth), at a third and at every response, with the full-run cost of each point; then the slopes in quality per
$100 between neighbouring shares at each coverage, against the slope of the coverage step from a third to all (the top
two hollow circles of an arm) and of the step from the lifted base to a third.  A share step that buys quality faster
than the coverage step is worth taking; the first that does not is where the share stops.  Read on 2026-11-07: Haiku
labelled k=4 stops at 15% (10 to 15% pays at every coverage, the steps above are flat or negative); Luna k=4 plain at 20%;
Gemini k=6 plain at 25%, every step paying, so a larger share might still pay for Gemini.

usage:
  judge_response_share_rate.py --judge haiku --format rk_pl --k 4
  judge_response_share_rate.py --judge luna --k 4          # plain, judge_response_pareto_61.json
  judge_response_share_rate.py --judge gemini --k 6
Prints a Markdown table and the slopes; --json PATH writes them with provenance.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

import numpy as np

_SCRIPT_PATH = Path(__file__).resolve()
REPO = _SCRIPT_PATH.parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from assistant_axis import json_metadata  # noqa: E402
from assistant_axis.provenance import current_file_input  # noqa: E402

MODELS = {"luna": "gpt-5.6-luna", "haiku": "claude-haiku-5-5", "gemini": "gemini-3.1-flash-lite"}
FORMATS = {"rk_pn": "plain", "rk_pl": "labelled", "rk_pa": "axis by axis"}
#: the arm keys' format letters (judge_response_pareto.py: "@{fmt}x{pct}k{k}" with fmt the rubric name)
COVERAGES = [("ninth", "ninth x 3/3"), ("third", "1/3"), ("all", "all"), ("lift", "lift")]
SHARES = (10, 15, 20, 25)


def mean_quality(point: dict) -> float:
    """The mean over the variants of each panel's quality 1 / (1 - rho)."""
    r = np.array(list(point["rho"].values()), dtype=float)
    return float(np.mean(1.0 / (1.0 - r)))


def share_rows(points: Dict[str, dict], model: str, fmt: str, k: int, shares: Sequence[int] = SHARES) -> Dict[int, Dict[str, dict]]:
    """{share: {coverage: {"quality", "cost", "rho"}}} for the arms "<model>@<fmt>x<share>k<k>" at each coverage present."""
    rows: Dict[int, Dict[str, dict]] = {}
    for pct in shares:
        arm = f"{model}@{fmt}x{pct}k{k}"
        row = {}
        for cov, key in COVERAGES:
            p = points.get(f"{arm}|{key}")
            if p is not None:
                row[cov] = dict(quality=mean_quality(p), cost=float(p["cost"]), rho=float(np.mean(list(p["rho"].values()))),
                                wins=None)
        if row:
            rows[pct] = row
    if not rows:
        raise SystemExit(f"no arms {model}@{fmt}x<share>k{k} in the figure JSON")
    return rows


def slope(a: dict, b: dict) -> float:
    """Quality per $100 from point a to point b (nan when the costs coincide)."""
    d = b["cost"] - a["cost"]
    return float(100.0 * (b["quality"] - a["quality"]) / d) if d else float("nan")


def share_slopes(rows: Dict[int, Dict[str, dict]]) -> dict:
    """Between neighbouring shares at each coverage; the coverage steps (lifted base to a third, a third to all) of each
    share; and which share each coverage's reading stops at (the last step that beats that share's third-to-all slope)."""
    shares = sorted(rows)
    out = {"between_shares": {}, "third_to_all": {}, "lift_to_third": {}, "stops_at": {}}
    for cov in ("ninth", "third", "all"):
        if not all(cov in rows[s] for s in shares):
            continue
        out["between_shares"][cov] = {f"{a}->{b}": slope(rows[a][cov], rows[b][cov]) for a, b in zip(shares, shares[1:])}
    for s in shares:
        if "third" in rows[s] and "all" in rows[s]:
            out["third_to_all"][s] = slope(rows[s]["third"], rows[s]["all"])
        if "lift" in rows[s] and "third" in rows[s]:
            out["lift_to_third"][s] = slope(rows[s]["lift"], rows[s]["third"])
    for cov, steps in out["between_shares"].items():
        stop = shares[0]
        for a, b in zip(shares, shares[1:]):
            rate = out["third_to_all"].get(b)
            if rate is not None and steps[f"{a}->{b}"] > rate:
                stop = b
            else:
                break
        out["stops_at"][cov] = stop
    return out


def panel_wins(points: Dict[str, dict], model: str, fmt: str, k: int, shares: Sequence[int], cov_key: str) -> Dict[str, int]:
    """How many of the variants the larger share leads in, per neighbouring pair, at one coverage."""
    out = {}
    for a, b in zip(shares, shares[1:]):
        pa, pb = points.get(f"{model}@{fmt}x{a}k{k}|{cov_key}"), points.get(f"{model}@{fmt}x{b}k{k}|{cov_key}")
        if pa and pb:
            out[f"{a}->{b}"] = int(sum(pb["rho"][v] > pa["rho"][v] for v in pa["rho"]))
    return out


def report(rows: Dict[int, Dict[str, dict]], slopes: dict, wins: Dict[str, Dict[str, int]], title: str) -> str:
    shares = sorted(rows)
    covs = [c for c in ("ninth", "third", "all") if all(c in rows[s] for s in shares)]
    lines = [f"**{title}**: quality averaged over the panels (the mean of each panel's 1/(1 - rho)), and the full-run cost", "",
             "| share | " + " | ".join({"ninth": "at the ninth", "third": "at a third", "all": "at all"}[c] for c in covs) + " |",
             "|---|" + "---|" * len(covs)]
    for s in shares:
        lines.append(f"| {s}% | " + " | ".join(f"{rows[s][c]['quality']:.3f}, ${rows[s][c]['cost']:.0f}" for c in covs) + " |")
    lines += ["", "slopes, quality per $100:", "", "| step | " + " | ".join(covs) + " |", "|---|" + "---|" * len(covs)]
    for a, b in zip(shares, shares[1:]):
        lines.append(f"| {a}% to {b}% | " + " | ".join(f"{slopes['between_shares'][c][f'{a}->{b}']:+.3f}" for c in covs if c in slopes["between_shares"]) + " |")
    lines.append("| a third to all (the top two hollow points) | " + ", ".join(f"{s}% {v:+.3f}" for s, v in slopes["third_to_all"].items()) + " |")
    if slopes["lift_to_third"]:
        lines.append("| the lifted base to a third | " + ", ".join(f"{s}% {v:+.3f}" for s, v in slopes["lift_to_third"].items()) + " |")
    lines.append("")
    for c, w in wins.items():
        lines.append(f"panels the larger share leads at {c}: " + ", ".join(f"{k} {v}/12" for k, v in w.items()))
    lines.append("the share where marginal share stops beating marginal coverage: " + ", ".join(f"{c} {s}%" for c, s in slopes["stops_at"].items()))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", choices=sorted(MODELS), required=True)
    ap.add_argument("--format", choices=sorted(FORMATS), default="rk_pn", help="the stacking format (default plain)")
    ap.add_argument("--k", type=int, required=True, help="axes a call")
    ap.add_argument("--figure_json", default=None,
                    help="the figure JSON; default judge_response_pareto_61[_<judge>][_<format name>].json in --output_dir, "
                         "the format suffix only when the figure was drawn with --stack_format")
    ap.add_argument("--output_dir", default=str(REPO / "roger/axis_judge_experiments/response_pareto"))
    ap.add_argument("--shares", default="10,15,20,25")
    ap.add_argument("--json", default=None, help="write the rows and slopes here, with provenance")
    args = ap.parse_args()
    out_dir = Path(args.output_dir)
    if args.figure_json:
        path = Path(args.figure_json)
    else:
        stem = "judge_response_pareto_61" + ("" if args.judge == "luna" else f"_{args.judge}")
        path = out_dir / f"{stem}.json"
        alt = out_dir / f"{stem}_{FORMATS[args.format].replace(' ', '_')}.json"
        if alt.exists() and alt.stat().st_mtime > path.stat().st_mtime if path.exists() else alt.exists():
            path = alt
    shares = [int(s) for s in args.shares.split(",")]
    points = json.load(open(path))["result"]["points"]
    model = MODELS[args.judge]
    rows = share_rows(points, model, args.format, args.k, shares)
    slopes = share_slopes(rows)
    wins = {c: panel_wins(points, model, args.format, args.k, shares, key) for c, key in COVERAGES[:3]}
    title = f"{args.judge} {FORMATS[args.format]} k={args.k}, worst X% one axis a call ({path.name})"
    print(report(rows, slopes, wins, title))
    if args.json:
        payload = dict(judge=args.judge, model=model, format=args.format, k=args.k, figure_json=str(path), rows=rows, slopes=slopes, wins=wins)
        Path(args.json).write_text(json.dumps(json_metadata(payload, inputs=[current_file_input(dep_key="producer_script", path=_SCRIPT_PATH),
                                                                               current_file_input(dep_key="figure_json", path=path)],
                                                            title=title), indent=1))
        print(f"wrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
