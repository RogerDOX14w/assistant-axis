"""Example responses per pattern among luna's combination drops, from analyze.py's rows: the role shows and the
trait is missing (Rt), the trait shows and the role is missing (rT), both show yet the combination judge drops
(RT), neither (rt); for each the question, the response's head and the three judges' reasoning."""
import json
import random
import sys
from collections import defaultdict

rows = json.load(open(sys.argv[1]))
per = int(sys.argv[2]) if len(sys.argv) > 2 else 2
strata = sys.argv[3].split(",") if len(sys.argv) > 3 else None
rng = random.Random(3)


def cell(r):
    return ("R" if r["Rs"] == 3 else "r") + ("T" if r["T"] == 3 else "t")


def head(s, n):
    s = (s or "").replace("\n", " ").strip()
    return s[:n] + ("…" if len(s) > n else "")


groups = defaultdict(list)
for r in rows:
    if r["C"] != 3 and (strata is None or r["stratum"] in strata):
        groups[(r["stratum"], cell(r))].append(r)
for (s, c) in sorted(groups):
    sel = rng.sample(groups[(s, c)], min(per, len(groups[(s, c)])))
    print(f"\n######## {s}  pattern {c}  ({len(groups[(s, c)])} of the stratum's luna drops)")
    for r in sel:
        print(f"\n=== {r['stem']}  {r['key']}  May {r['may']}  luna C {r['C']} R {r['Rs']} T {r['T']}  "
              f"{'cut' if r['cut'] else 'whole'}  (standalone in May: role {r['role_alone']}, trait {r['trait_alone']})")
        print(f"Q: {head(r['question'], 160)}")
        print(f"A: {head(r['answer'], 420)}")
        print(f"  combination judge: {head(r['c_reply'], 330)}")
        print(f"  role judge:        {head(r['r_reply'], 330)}")
        print(f"  trait judge:       {head(r['t_reply'], 330)}")
