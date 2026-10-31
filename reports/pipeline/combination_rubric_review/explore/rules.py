"""What each candidate keep rule would keep of each sampled combination's 500 responses, estimated from the
sample by reweighting its May-dropped and May-kept halves by the combination's May keep rate.  Rules: luna's
combination judge on version 3's text (C); both separate judges (R and T); either (R or T); at least the goal
entity (T for a t_ combination, R for an r_); at least the role."""
import json
import sys
from statistics import mean

rows = json.load(open(sys.argv[1]))
man = json.load(open(sys.argv[2]))
RULES = {"C v3": lambda r: r["C"] == 3, "both": lambda r: r["Rs"] == 3 and r["T"] == 3,
         "either": lambda r: r["Rs"] == 3 or r["T"] == 3,
         "goal": lambda r: (r["T"] == 3) if r["stem"].startswith("t_") else (r["Rs"] == 3),
         "role": lambda r: r["Rs"] == 3}


def est(stem, rule):
    sub = [r for r in rows if r["stem"] == stem]
    kept = [r for r in sub if r["may"] == 3]; dropped = [r for r in sub if r["may"] != 3]
    if not kept or not dropped:
        return float("nan")
    k = man["combinations"][stem]["may_keep"]
    return k * mean(rule(r) for r in kept) + (1 - k) * mean(rule(r) for r in dropped)


print(f"{'combination':46s} May   " + " ".join(f"{n:>6s}" for n in RULES))
by_stratum = {}
for stem, info in man["combinations"].items():
    if not any(r["stem"] == stem for r in rows):
        continue
    e = {n: est(stem, f) for n, f in RULES.items()}
    by_stratum.setdefault(info["stratum"], []).append(e)
    print(f"{info['stratum'][:1]} {stem:44s} {info['may_keep']:.2f}  " + " ".join(f"{e[n]:6.2f}" for n in RULES))
print("\nmean over the stratum's combinations:")
for s, es in by_stratum.items():
    print(f"  {s:18s} " + " ".join(f"{n} {mean(e[n] for e in es):.2f}" for n in RULES))
