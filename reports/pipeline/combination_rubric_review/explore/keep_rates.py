"""The May 8slot combinations' keep rates against their role's and trait's standalone keep rates (all judged
by gpt-4.1-mini under the April number-only rubric): where a combination keeps less than independence
predicts, and how its drops relate to the questions its standalone entities also fail on."""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median

D = Path("runpod_workspace/qwen/qwen-3-32b Roger 8slot")


def scores(sub, stem):
    p = D / sub / "scores" / f"{stem}.json"
    return json.loads(p.read_text()) if p.exists() else None


rows = []
missing = Counter()
for p in sorted((D / "combinations" / "scores").glob("*.json")):
    stem = p.stem
    if stem in ("judge_rubric", "usage"):
        continue
    left, trait = stem.split("__", 1)
    kind, role = left[0], left[2:]
    combo = json.loads(p.read_text())
    r, t = scores("roles", role), scores("traits", trait)
    if r is None or t is None:
        missing["role" if r is None else "trait"] += 1
        continue
    keys = [k for k in combo if k in r and k in t]
    n = len(combo)
    keep = mean(v == 3 for v in combo.values())
    rk = mean(r[k] == 3 for k in keys) if keys else float("nan")
    tk = mean(t[k] == 3 for k in keys) if keys else float("nan")
    both_same_key = mean((r[k] == 3) and (t[k] == 3) for k in keys) if keys else float("nan")
    rows.append(dict(stem=stem, kind=kind, role=role, trait=trait, n=n, n_shared=len(keys), keep=keep,
                     role_keep=rk, trait_keep=tk, indep=rk * tk, both_key=both_same_key, min=min(rk, tk),
                     scores=combo, role_scores=r, trait_scores=t, keys=keys))
print(f"{len(rows)} combinations with standalone scores for both entities; skipped {dict(missing)}")
print(f"kinds: {Counter(r['kind'] for r in rows)}; n per combination: {Counter(r['n'] for r in rows).most_common(4)}; "
      f"shared keys per combination: median {median(r['n_shared'] for r in rows)}")
keeps = sorted(r["keep"] for r in rows)
print("keep rate of the combination: " + " ".join(f"p{q}={keeps[int(q / 100 * (len(keeps) - 1))]:.2f}" for q in (0, 10, 25, 50, 75, 90, 100)))
print(f"below 50% kept: {sum(k < 0.5 for k in keeps)}; below 25%: {sum(k < 0.25 for k in keeps)}")
for kind in "rt":
    sub = [r for r in rows if r["kind"] == kind]
    print(f"  kind {kind}_: {len(sub)} combinations, mean keep {mean(r['keep'] for r in sub):.3f}, "
          f"mean role standalone {mean(r['role_keep'] for r in sub):.3f}, trait standalone {mean(r['trait_keep'] for r in sub):.3f}")

# Where does the combination's keep sit between independence (role x trait) and the smaller standalone keep?
# ratio = keep / indep: 1 = as independence predicts; keep / min: 1 = as if one switch governed both.
print("\ncombination keep against the two reference points (over combinations with both standalone keeps > 0.2):")
sel = [r for r in rows if r["role_keep"] > 0.2 and r["trait_keep"] > 0.2]
print(f"  n = {len(sel)}; median keep {median(r['keep'] for r in sel):.2f}, median independence {median(r['indep'] for r in sel):.2f}, "
      f"median min {median(r['min'] for r in sel):.2f}, median both-at-same-key {median(r['both_key'] for r in sel):.2f}")
below_indep = sum(r["keep"] < r["indep"] for r in sel)
print(f"  keep below independence: {below_indep} of {len(sel)} ({100 * below_indep / len(sel):.0f}%); "
      f"keep below 0.5 x independence: {sum(r['keep'] < 0.5 * r['indep'] for r in sel)}; "
      f"keep at or above min: {sum(r['keep'] >= r['min'] for r in sel)}")
print("\nby the smaller standalone keep (bins), the combination's median keep, independence and min:")
bins = [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]
for lo, hi in bins:
    sub = [r for r in rows if lo <= r["min"] < hi]
    if sub:
        print(f"  min standalone in [{lo:.1f}, {hi:.1f}): n {len(sub):4d}  keep {median(r['keep'] for r in sub):.2f}  "
              f"indep {median(r['indep'] for r in sub):.2f}  min {median(r['min'] for r in sub):.2f}  "
              f"keep/indep {median(r['keep'] / r['indep'] if r['indep'] else float('nan') for r in sub):.2f}")

# Per question (key): among a combination's dropped keys, how many are keys where the role or the trait
# standalone was also dropped (scope or difficulty of the question), against the base rate of such keys.
print("\nthe combination's drops against the standalone drops on the same keys (pooled over combinations):")
agg = Counter()
for r in rows:
    for k in r["keys"]:
        c = r["scores"][k] == 3
        rs, ts = r["role_scores"][k] == 3, r["trait_scores"][k] == 3
        agg[(c, rs, ts)] += 1
tot = sum(agg.values())
for c in (True, False):
    n_c = sum(v for (cc, _, _), v in agg.items() if cc == c)
    print(f"  combination {'kept' if c else 'dropped'} ({n_c}, {100 * n_c / tot:.0f}%): standalone both kept "
          f"{100 * agg[(c, True, True)] / n_c:.0f}%  role only {100 * agg[(c, True, False)] / n_c:.0f}%  "
          f"trait only {100 * agg[(c, False, True)] / n_c:.0f}%  neither {100 * agg[(c, False, False)] / n_c:.0f}%")

print("\nthe 40 lowest-keep combinations (kind, role, trait, n, keep, role standalone, trait standalone, independence):")
for r in sorted(rows, key=lambda r: r["keep"])[:40]:
    print(f"  {r['kind']}_ {r['role']:24s} {r['trait']:24s} n {r['n']:3d}  keep {r['keep']:.2f}  role {r['role_keep']:.2f}  "
          f"trait {r['trait_keep']:.2f}  indep {r['indep']:.2f}")
json.dump([{k: v for k, v in r.items() if k not in ("scores", "role_scores", "trait_scores", "keys")} for r in rows],
          open(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/dev/null"), "w"), indent=1)
