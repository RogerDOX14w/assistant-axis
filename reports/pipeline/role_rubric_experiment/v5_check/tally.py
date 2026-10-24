"""Tally the v5 category reader check (2026-10-24): per category and direction, the share of
flipped responses the readers marked G.  Up-flip (v4 < 3, v5 = 3) marked G: v5 right.
Down-flip (v4 = 3, v5 < 3) marked G: v4 right."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scipy.stats import binomtest

D = Path("reports/pipeline/role_rubric_experiment/v5_check")
key = json.loads((D / "key.json").read_text())
items = key["items"]
marks = {}
for s in range(1, 5):
    cur = None
    for line in (D / f"sheet_{s}.md").read_text().splitlines():
        m = re.match(r"^### (\d+)\s*$", line)
        if m:
            cur = m.group(1)
            continue
        m = re.match(r"^mark:\s*(\S)", line)
        if m and cur:
            marks[cur] = m.group(1).upper()
            cur = None
missing = sorted(set(items) - set(marks), key=int)
print(f"{len(marks)} marks, {len(items)} items, unmarked: {missing}")

per_sheet = defaultdict(Counter)
for i, mk in marks.items():
    per_sheet[items[i]["sheet"]][mk] += 1
for s in sorted(per_sheet):
    print(f"  sheet {s}: {dict(per_sheet[s])}")

tab = defaultdict(lambda: defaultdict(Counter))      # category -> direction -> mark
role_tab = defaultdict(lambda: defaultdict(Counter))  # (category, role) -> direction -> mark
for i, it in items.items():
    mk = marks.get(i, "?")
    tab[it["category"]][it["direction"]][mk] += 1
    role_tab[(it["category"], it["role"])][it["direction"]][mk] += 1

fc = key["flip_counts"]
print("\nCategory | up-flips: n, G (v5 right), B, T, ? | down-flips: n, G (v4 right), B, T, ? | flips total up/down")
out = {}
for cat in sorted(tab):
    u, d = tab[cat]["up"], tab[cat]["down"]
    nu, nd = sum(u.values()), sum(d.values())
    tot_up = sum(fc[cat]["up"].values())
    tot_dn = sum(fc[cat]["down"].values())
    # estimated net good responses gained: up-flips x P(G | up) - down-flips x P(G | down)
    gain = tot_up * u["G"] / nu if nu else 0.0
    loss = tot_dn * d["G"] / nd if nd else 0.0
    bad_in = tot_up * (u["B"] + u["T"]) / nu if nu else 0.0
    print(f"{cat:34s} | {nu:3d} G{u['G']:3d} ({u['G'] / max(nu, 1):.0%}) B{u['B']:2d} T{u['T']:2d} ?{u['?']:2d}"
          f" | {nd:3d} G{d['G']:3d} ({d['G'] / max(nd, 1):.0%}) B{d['B']:2d} T{d['T']:2d} ?{d['?']:2d}"
          f" | {tot_up}/{tot_dn}  est. good gained {gain:.0f}, good lost {loss:.0f}, B/T admitted {bad_in:.0f}")
    out[cat] = {"up": dict(u), "down": dict(d), "flips_up": tot_up, "flips_down": tot_dn,
                "est_good_gained": gain, "est_good_lost": loss, "est_bad_or_tie_admitted": bad_in}

print("\nPer role (up: G/B/T/?  down: G/B/T/?)")
for (cat, role), t in sorted(role_tab.items()):
    u, d = t["up"], t["down"]
    print(f"  {cat[:1]} {role:26s} up {u['G']}/{u['B']}/{u['T']}/{u['?']}   down {d['G']}/{d['B']}/{d['T']}/{d['?']}")

# overall
U = Counter(); Dn = Counter()
for cat in tab:
    U.update(tab[cat]["up"]); Dn.update(tab[cat]["down"])
print(f"\nAll: up {dict(U)}  down {dict(Dn)}")
# Is the up-flip G share different from the down-flip G share? (two-sample; report both binomial CIs)
for name, c in (("up", U), ("down", Dn)):
    n = sum(c.values())
    ci = binomtest(c["G"], n).proportion_ci()
    print(f"  {name}: G {c['G']}/{n} = {c['G'] / n:.0%}, 95% CI {ci.low:.0%}-{ci.high:.0%}")
Path(__file__).with_name("tally.json").write_text(json.dumps(out, indent=1))
