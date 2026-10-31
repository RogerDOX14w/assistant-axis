"""Follow-ups on keep_rates.json: the combinations that keep far above their weaker standalone entity, the
standalone keep rates of the goal entities (alignment resistance measured by the judge), and the r_
combinations whose role is resisted standalone."""
import json
import sys
from collections import defaultdict
from statistics import mean, median

rows = json.load(open(sys.argv[1]))
goal = json.load(open("data/goal_roles_and_traits_v1.json"))

print("combinations with the smaller standalone keep in [0.2, 0.6) and keep over 0.85:")
for r in sorted((r for r in rows if 0.2 <= r["min"] < 0.6 and r["keep"] > 0.85), key=lambda r: r["min"])[:25]:
    print(f"  {r['kind']}_ {r['role']:22s} {r['trait']:22s} keep {r['keep']:.2f}  role {r['role_keep']:.2f}  trait {r['trait_keep']:.2f}")

by_trait, by_role = defaultdict(list), defaultdict(list)
for r in rows:
    by_trait[r["trait"]].append(r)
    by_role[r["role"]].append(r)
print("\ngoal traits by standalone keep (the trait alone, May, mini number-only rubric), with the mean keep of their")
print("combinations and the mean standalone keep of the roles they were paired with:")
for t in sorted(goal["traits"]["goal"], key=lambda t: by_trait[t][0]["trait_keep"] if by_trait.get(t) else 9):
    rs = by_trait.get(t)
    if rs:
        print(f"  {t:20s} trait alone {rs[0]['trait_keep']:.2f}  combos {len(rs):3d}  mean combo keep {mean(r['keep'] for r in rs):.2f}  "
              f"partner roles alone {mean(r['role_keep'] for r in rs):.2f}  combo/trait-alone {mean(r['keep'] for r in rs) / max(rs[0]['trait_keep'], 1e-9):.2f}")
print("\ngoal roles by standalone keep, with the mean keep of their combinations and their partner traits' standalone keep:")
for ro in sorted(goal["roles"]["goal"], key=lambda ro: by_role[ro][0]["role_keep"] if by_role.get(ro) else 9):
    rs = by_role.get(ro)
    if rs:
        print(f"  {ro:28s} role alone {rs[0]['role_keep']:.2f}  combos {len(rs):3d}  mean combo keep {mean(r['keep'] for r in rs):.2f}  "
              f"partner traits alone {mean(r['trait_keep'] for r in rs):.2f}  combo/role-alone {mean(r['keep'] for r in rs) / max(rs[0]['role_keep'], 1e-9):.2f}")
print("\nnon-goal traits with standalone keep under 0.7, and non-goal roles under 0.7:")
for t, rs in sorted(by_trait.items(), key=lambda kv: kv[1][0]["trait_keep"]):
    if t in goal["traits"]["non_goal"] and rs[0]["trait_keep"] < 0.7:
        print(f"  trait {t:22s} alone {rs[0]['trait_keep']:.2f}  combos {len(rs):3d}  mean combo keep {mean(r['keep'] for r in rs):.2f}")
for ro, rs in sorted(by_role.items(), key=lambda kv: kv[1][0]["role_keep"]):
    if ro in goal["roles"]["non_goal"] and rs[0]["role_keep"] < 0.7:
        print(f"  role  {ro:22s} alone {rs[0]['role_keep']:.2f}  combos {len(rs):3d}  mean combo keep {mean(r['keep'] for r in rs):.2f}")
