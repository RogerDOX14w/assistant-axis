"""Paired-within-role comparison of role rubric V3's depth with the earlier depth runs (W1, 2026-10-09).

Three runs read answers with the same role judge (each role file's eval_prompt,
GPT-4.1-mini) and the same role depth judge (Sonnet 4.6, rubric 1), on the same
10 questions per role, Qwen 3 32B at DeepInfra with the extraction settings:

  run 1  reports/opening_forms/roles_depth            (2026-10-02)  act_as, other
  run 2  reports/opening_forms/roles_openings_depth   (2026-10-03)  act_as, from_now_on, be
  run 3  reports/opening_forms/roles_v3_depth         (2026-10-09)  v3 (one a role), old_other (anchor), observer extras

A role's figure for an arm is the share of its answers with the property, over
all answers read (as in the earlier tables); a comparison is the mean over roles
of the paired difference, with an interval from resampling roles and p from a
sign-flip test (``opening_form_experiment.paired_over_traits``, seed 20260929 for
every row).  "Direct" comparisons cross runs; "chained" ones add only
within-run contrasts and the anchor, so drift between runs cancels:

  old corpus (chained) = old_other[3] + 0.2 * (act_as - other)[1]     (one "Act as" in five)
  act_as (chained)     = old_other[3] + (act_as - other)[1]
  from_now_on (chained)= old_other[3] + (act_as - other)[1] + (from_now_on - act_as)[2]
  be (chained)         = old_other[3] + (act_as - other)[1] + (be - act_as)[2]

Run from the repo root:
    uv run python reports/opening_forms/roles_v3_depth/analyse.py
Writes depth_paired.json beside this file.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.getcwd())
from assistant_axis.plot_metadata import json_metadata  # noqa: E402
from assistant_axis.provenance import current_file_input, current_files_input  # noqa: E402
from data_analysis.opening_form_experiment import paired_over_traits  # noqa: E402

HERE = Path(__file__).resolve().parent
R = Path("reports/opening_forms")
RUN = {1: R / "roles_depth", 2: R / "roles_openings_depth", 3: R / "roles_v3_depth"}
KINDS = ("good", "bad", "indifferent")
SEED = 20260929
METRICS = {
    "cartoon": lambda d: d["caricature"] == 2,
    "laid_on": lambda d: d["caricature"] >= 1,
    "assistant_voice": lambda d: d["voice"] == "assistant",
    "own_voice": lambda d: d["voice"] == "person",
    "describes_itself": lambda d: d["describes_itself"],
    "in_action": lambda d: d["in_action"],
}
LABELS = {"cartoon": "cartoon", "laid_on": "laid on", "assistant_voice": "answered in an assistant's voice",
          "own_voice": "own voice", "describes_itself": "describes its own role",
          "in_action": "the role shapes what it does", "scored_3": "scored 3 by the role judge"}


def plan(run: int) -> dict:
    return json.loads((RUN[run] / "plan.json").read_text(encoding="utf-8"))["traits"]


def _load(run: int, stem: str, kind: str) -> dict:
    p = RUN[run] / kind / f"{stem}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def per_role(run: int, pick, metric: str) -> dict[str, float]:
    """stem -> percent of the role's answers with the property, over the variants ``pick(stem, entry)`` names."""
    out = {}
    for stem, t in plan(run).items():
        names = set(pick(stem, t))
        if not names:
            continue
        if metric == "scored_3":
            vals = [s == 3 for k, s in _load(run, stem, "scores").items() if k.rsplit("_q", 1)[0] in names]
        else:
            f = METRICS[metric]
            vals = [f(d) for k, d in _load(run, stem, "depth").items() if k.rsplit("_q", 1)[0] in names]
        if vals:
            out[stem] = 100.0 * float(np.mean(vals))
    return out


def named(name):
    return lambda stem, t: [v["name"] for v in t["variants"] if v["name"] == name]


def by_design(*designs):
    return lambda stem, t: [v["name"] for v in t["variants"] if v.get("design") in designs]


def arms(metric: str) -> dict[str, dict[str, float]]:
    a = {"v3": per_role(3, by_design("rotation"), metric),
         "old_other[3]": per_role(3, named("old_other"), metric),
         "other[1]": per_role(1, named("other"), metric), "act_as[1]": per_role(1, named("act_as"), metric),
         "act_as[2]": per_role(2, named("act_as"), metric), "from_now_on[2]": per_role(2, named("from_now_on"), metric),
         "be[2]": per_role(2, named("be"), metric)}
    common = set(a["old_other[3]"]) & set(a["other[1]"]) & set(a["act_as[1]"])
    a["old_corpus[1]"] = {s: 0.2 * a["act_as[1]"][s] + 0.8 * a["other[1]"][s] for s in common}
    a["old_corpus (chained)"] = {s: a["old_other[3]"][s] + 0.2 * (a["act_as[1]"][s] - a["other[1]"][s]) for s in common}
    a["act_as (chained)"] = {s: a["old_other[3]"][s] + a["act_as[1]"][s] - a["other[1]"][s] for s in common}
    for f in ("from_now_on", "be"):
        both = common & set(a[f"{f}[2]"]) & set(a["act_as[2]"])
        a[f"{f} (chained)"] = {s: a["act_as (chained)"][s] + a[f"{f}[2]"][s] - a["act_as[2]"][s] for s in both}
    return a


COMPARISONS = [  # (row label, arm, baseline): arm minus baseline
    ("V3 minus the old corpus, non-role-play instruction (same run)", "v3", "old_other[3]"),
    ("V3 minus the old corpus file (chained)", "v3", "old_corpus (chained)"),
    ("V3 minus the old corpus file (direct)", "v3", "old_corpus[1]"),
    ("V3 minus Act as (chained)", "v3", "act_as (chained)"),
    ("V3 minus Act as (direct, run 2)", "v3", "act_as[2]"),
    ("V3 minus From now on (chained)", "v3", "from_now_on (chained)"),
    ("V3 minus From now on (direct)", "v3", "from_now_on[2]"),
    ("V3 minus Be (chained)", "v3", "be (chained)"),
    ("V3 minus Be (direct)", "v3", "be[2]"),
    ("drift: old other, run 3 minus run 1", "old_other[3]", "other[1]"),
    ("drift: Act as, run 2 minus run 1", "act_as[2]", "act_as[1]"),
]


def compare(a: dict, base: dict, roles=None) -> dict:
    if roles is not None:
        a = {s: v for s, v in a.items() if s in roles}
        base = {s: v for s, v in base.items() if s in roles}
    r = paired_over_traits(base, a, np.random.default_rng(SEED))
    if not r.get("traits"):
        return {"roles": 0}
    return {"roles": r["traits"], "arm_mean": round(r["arm_mean"], 1), "baseline_mean": round(r["baseline_mean"], 1),
            "difference": round(r["difference"], 1), "interval": [round(x, 1) for x in r["interval"]],
            "p": round(r["p"], 4), "better": r["better"], "worse": r["worse"]}


def fmt(c: dict) -> str:
    if not c.get("roles"):
        return "n/a"
    return (f"{c['difference']:+5.1f} ({c['interval'][0]:+.1f} to {c['interval'][1]:+.1f}) p={c['p']:.3f} "
            f"[{c['arm_mean']:.1f} vs {c['baseline_mean']:.1f}, n={c['roles']}]")


def main() -> None:
    kinds = {s: t["kind"] for s, t in plan(3).items()}
    out = {"comparisons": {}, "by_kind": {}, "levels": {}, "v3_by_opening": {}, "observer": {}}
    all_arms = {m: arms(m) for m in list(METRICS) + ["scored_3"]}
    for m, a in all_arms.items():
        out["comparisons"][m] = {label: compare(a[x], a[y]) for label, x, y in COMPARISONS}
        out["by_kind"][m] = {label: {k: compare(a[x], a[y], {s for s, kk in kinds.items() if kk == k}) for k in KINDS}
                             for label, x, y in COMPARISONS[:9]}
    # levels on the 89 roles every arm has
    common = set.intersection(*(set(v) for v in all_arms["cartoon"].values()))
    for name in all_arms["cartoon"]:
        out["levels"][name] = {m: round(float(np.mean([all_arms[m][name][s] for s in common if s in all_arms[m][name]])), 1)
                               for m in all_arms}
    out["levels_roles"] = len(common)
    # V3 by opening class (rotation draws: about 20 roles each)
    p3 = plan(3)
    for cls in ("from_now_on", "be", "youre", "become", "you_are"):
        roles = {s for s, t in p3.items() if any(v["design"] == "rotation" and v["name"] == f"v3_{cls}" for v in t["variants"])}
        out["v3_by_opening"][cls] = {
            m: {"vs_old_other": compare(all_arms[m]["v3"], all_arms[m]["old_other[3]"], roles),
                "vs_from_now_on_direct": compare(all_arms[m]["v3"], all_arms[m]["from_now_on[2]"], roles)}
            for m in ("cartoon", "assistant_voice", "describes_itself", "in_action", "scored_3")}
    # observer register: a role's flagged V3 instructions against its unflagged ones read
    flagged = lambda stem, t: [v["name"] for v in t["variants"] if v.get("arm") == "v3" and v.get("observer")]
    unflagged = lambda stem, t: ([v["name"] for v in t["variants"] if v.get("arm") == "v3" and not v.get("observer")]
                                 if any(v.get("observer") for v in t["variants"]) else [])
    for m in list(METRICS) + ["scored_3"]:
        out["observer"][m] = compare(per_role(3, flagged, m), per_role(3, unflagged, m))
    inputs = [current_file_input(dep_key=f"plan_run{k}", path=RUN[k] / "plan.json") for k in RUN]
    inputs += [current_files_input(dep_key=f"depth_run{k}", paths=sorted((RUN[k] / "depth").glob("*.json"))) for k in RUN]
    inputs += [current_files_input(dep_key=f"scores_run{k}", paths=sorted((RUN[k] / "scores").glob("*.json"))) for k in RUN]
    env = json_metadata(out, title="W1: depth of role rubric V3, paired within role", inputs=inputs,
                        script="reports/opening_forms/roles_v3_depth/analyse.py")
    (HERE / "depth_paired.json").write_text(json.dumps(env, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"levels, mean over the {len(common)} roles every arm has (percent of answers)")
    cols = ["scored_3", "own_voice", "assistant_voice", "in_action", "describes_itself", "laid_on", "cartoon"]
    print(f"{'arm':24s}" + "".join(f"{c[:12]:>13s}" for c in cols))
    for name, row in out["levels"].items():
        print(f"{name:24s}" + "".join(f"{row[c]:13.1f}" for c in cols))
    for m in ("cartoon", "assistant_voice", "describes_itself", "in_action", "scored_3", "laid_on"):
        print(f"\n{LABELS[m]}")
        for label, c in out["comparisons"][m].items():
            print(f"  {label:62s} {fmt(c)}")
    print("\ncartoon by kind")
    for label, row in out["by_kind"]["cartoon"].items():
        print(f"  {label}")
        for k in KINDS:
            print(f"      {k:12s} {fmt(row[k])}")
    print("\nV3 by opening (rotation draws), cartoon")
    for cls, row in out["v3_by_opening"].items():
        print(f"  {cls:12s} vs old other {fmt(row['cartoon']['vs_old_other'])}   vs From now on {fmt(row['cartoon']['vs_from_now_on_direct'])}")
    print("\nobserver-flagged V3 instructions minus the same role's unflagged V3 instructions")
    for m, c in out["observer"].items():
        print(f"  {LABELS[m]:40s} {fmt(c)}")
    print(f"\nwrote {HERE / 'depth_paired.json'}")


if __name__ == "__main__":
    main()
