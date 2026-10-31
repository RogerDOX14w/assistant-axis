"""The combination rubric arms against the separate judgements, on the exploration sample.  Per response: the
A, B, R, T answers of version 14 (both needed) and 15 (either enough), parsed from the saved replies; the role
judge's A, B, C answers (version 10) and the trait judge's score (version 13) from the exploration.  Reports:
whether R agrees with the role judge's C and T with the trait judge (score 2 or 3: the trait shows), whether the
framing moves the answers between 14 and 15, and the keep rate every rule gives, estimated for the population
as rules.py does.

    uv run python reports/pipeline/combination_rubric_review/explore/compare_arms.py explore/rows.json \
        runpod_workspace/combo_explore/sample.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from assistant_axis.judge_rubrics import abc_answers, abrt_answers, abrt_score  # noqa: E402

R = Path("runpod_workspace/combo_explore")
rows = json.load(open(sys.argv[1]))
man = json.load(open(sys.argv[2]))
RENAMED = {"r_aligned_artificial_intelligence__pensive": "r_instrumentally_aligned_ai__pensive"}


def replies(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["key"]] = r
    return out


arm = {}
for v in (14, 15):
    for stem in man["combinations"]:
        if stem in RENAMED:
            p = R / f"combo_renamed_v{v}" / "scores" / "_replies" / f"{RENAMED[stem]}.jsonl"
        else:
            p = R / f"combo_v{v}" / "scores" / "_replies" / f"{stem}.jsonl"
        for key, rep in replies(p).items():
            arm[(v, stem, key)] = rep
for r in rows:
    for v in (14, 15):
        rep = arm.get((v, r["stem"], r["key"]))
        ans = abrt_answers(rep["reply"]) if rep else None
        r[f"a{v}"] = ans
        r[f"s{v}"] = rep["score"] if rep else None
    r["role_abc"] = abc_answers(r["r_reply"])
rows = [r for r in rows if r["a14"] and r["a15"] and r["role_abc"] is not None]
print(f"{len(rows)} responses with both arms' answers and the role judge's")

print("\nagreement of the arms' R and T with the separate judges (R vs the role judge's C; T vs trait score >= 2):")
for v in (14, 15):
    rR = [(r[f"a{v}"]["R"], r["role_abc"]["C"]) for r in rows]
    tT = [(r[f"a{v}"]["T"], r["T"] >= 2) for r in rows]
    print(f"  version {v}: R agrees {mean(a == b for a, b in rR):.2f} (arm yes {mean(a for a, _ in rR):.2f}, role judge yes "
          f"{mean(b for _, b in rR):.2f});  T agrees {mean(a == b for a, b in tT):.2f} (arm yes {mean(a for a, _ in tT):.2f}, "
          f"trait judge yes {mean(b for _, b in tT):.2f})")
    aA = [(r[f"a{v}"]["A"], r["role_abc"]["A"]) for r in rows]
    bB = [(r[f"a{v}"]["B"], r["role_abc"]["B"]) for r in rows]
    print(f"             A agrees {mean(a == b for a, b in aA):.2f} (arm {mean(a for a, _ in aA):.2f}, role judge "
          f"{mean(b for _, b in aA):.2f});  B agrees {mean(a == b for a, b in bB):.2f} (arm {mean(a for a, _ in bB):.2f}, "
          f"role judge {mean(b for _, b in bB):.2f})")
print("  between the arms: " + "  ".join(f"{q} agrees {mean(r['a14'][q] == r['a15'][q] for r in rows):.2f}" for q in "ABRT"))

print("\nper stratum: the arms' R and T yes rates against the separate judges':")
for s in man["strata"]:
    sub = [r for r in rows if r["stratum"] == s]
    if sub:
        print(f"  {s:18s} n {len(sub):4d}  R: v14 {mean(r['a14']['R'] for r in sub):.2f} v15 {mean(r['a15']['R'] for r in sub):.2f} "
              f"role judge {mean(r['role_abc']['C'] for r in sub):.2f}   T: v14 {mean(r['a14']['T'] for r in sub):.2f} "
              f"v15 {mean(r['a15']['T'] for r in sub):.2f} trait judge {mean(r['T'] >= 2 for r in sub):.2f}")


def goal_letter(stem):
    return "T" if stem.startswith("t_") else "R"


RULES = {
    "v14 both": lambda r: r["s14"] == 3,
    "v15 either": lambda r: r["s15"] == 3,
    "v14 ans, either": lambda r: abrt_score(r["a14"], "either") == 3,
    "v14 ans, goal": lambda r: r["a14"][goal_letter(r["stem"])] and not r["a14"]["A"] and not r["a14"]["B"],
    "sep both 3": lambda r: r["Rs"] == 3 and r["T"] == 3,
    "sep 3 & >=2": lambda r: (r["Rs"] == 3 and r["T"] >= 2) or (r["T"] == 3 and r["Rs"] >= 2),
    "sep 3 & >=1": lambda r: (r["Rs"] == 3 and r["T"] >= 1) or (r["T"] == 3 and r["Rs"] >= 1),
    "sep goal 3": lambda r: (r["T"] if goal_letter(r["stem"]) == "T" else r["Rs"]) == 3,
    "sep either 3": lambda r: r["Rs"] == 3 or r["T"] == 3,
    "April text": lambda r: r["C"] == 3,
}


def est(stem, rule):
    sub = [r for r in rows if r["stem"] == stem]
    kept = [r for r in sub if r["may"] == 3]; dropped = [r for r in sub if r["may"] != 3]
    if not kept or not dropped:
        return float("nan")
    k = man["combinations"][stem]["may_keep"]
    return k * mean(rule(r) for r in kept) + (1 - k) * mean(rule(r) for r in dropped)


print("\nestimated population keep rate per rule (the sample reweighted by each combination's May keep rate):")
print(f"  {'combination':46s} " + " ".join(f"{n:>15s}" for n in RULES))
by_stratum = defaultdict(list)
for stem, info in man["combinations"].items():
    if not any(r["stem"] == stem for r in rows):
        continue
    e = {n: est(stem, f) for n, f in RULES.items()}
    by_stratum[info["stratum"]].append(e)
    print(f"  {info['stratum'][:1]} {stem:44s} " + " ".join(f"{e[n]:15.2f}" for n in RULES))
print("\n  mean over the stratum's combinations:")
for s, es in by_stratum.items():
    print(f"  {s:18s}" + " ".join(f"{n} {mean(e[n] for e in es):.2f}" for n in RULES))

print("\nwhere the arms disagree with the separate judges on the keep under the same rule (share of responses):")
both_arm = [(r["s14"] == 3, r["Rs"] == 3 and r["T"] == 3) for r in rows]
either_arm = [(r["s15"] == 3, r["Rs"] == 3 or r["T"] == 3) for r in rows]
for name, pairs in (("both: v14 vs separate", both_arm), ("either: v15 vs separate", either_arm)):
    c = Counter(pairs)
    n = len(pairs)
    print(f"  {name:26s} agree keep {c[(True, True)] / n:.2f}  agree drop {c[(False, False)] / n:.2f}  "
          f"arm keeps, separate drops {c[(True, False)] / n:.2f}  arm drops, separate keeps {c[(False, True)] / n:.2f}")
json.dump(rows, open(Path(sys.argv[1]).with_name("rows_arms.json"), "w"))
