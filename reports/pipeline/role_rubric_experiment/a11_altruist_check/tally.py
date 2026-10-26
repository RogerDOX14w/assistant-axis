"""Tally the A11 altruist reader check (2026-10-26).  Up-flip (A1 < 3, A11 = 3) marked G: A11 right
to admit it.  Down-flip (A1 = 3, A11 < 3) marked G: A1 was right, A11 drops good data.  Scales the
sample's shares to all of altruist's flips (84 up, 37 down) for the net change in good data."""
import json
import re
from collections import Counter
from pathlib import Path

from scipy.stats import binomtest

D = Path(__file__).parent
key = json.loads((D / "key.json").read_text())
marks, cur = {}, None
for line in (D / "sheet_1.md").read_text().splitlines():
    m = re.match(r"^### (\d+)\s*$", line)
    if m:
        cur = m.group(1)
        continue
    m = re.match(r"^mark:\s*(\S)", line)
    if m and cur:
        marks[cur] = m.group(1).upper()
        cur = None
missing = sorted(set(key["items"]) - set(marks), key=int)
print(f"{len(marks)} marks of {len(key['items'])} items; unmarked: {missing}")
tab = {"up": Counter(), "down": Counter()}
for i, it in key["items"].items():
    tab[it["direction"]][marks.get(i, "-")] += 1
out = {"flip_counts": key["flip_counts"], "kept": key["kept"]}
for d in ("up", "down"):
    c = tab[d]; n = sum(c.values())
    ci = binomtest(c["G"], n).proportion_ci()
    print(f"{d:4s}: n {n}  G {c['G']} ({c['G'] / n:.0%}, 95% CI {ci.low:.0%}-{ci.high:.0%})  "
          f"B {c['B']}  T {c['T']}  ? {c['?']}")
    out[d] = dict(c)
fc = key["flip_counts"]
share = lambda d, ms: sum(tab[d][m] for m in ms) / sum(tab[d].values())
good = fc["up"] * share("up", "G") - fc["down"] * share("down", "G")
bad = fc["up"] * share("up", "B") - fc["down"] * share("down", "B")
tie = fc["up"] * share("up", "T?") - fc["down"] * share("down", "T?")
print(f"estimated net change in altruist's kept set (A1 -> A11): good {good:+.0f}, bad {bad:+.0f}, "
      f"borderline {tie:+.0f} (kept {key['kept']['A1']} -> {key['kept']['A11']})")
out["estimated_net"] = {"good": good, "bad": bad, "borderline": tie}
(D / "tally.json").write_text(json.dumps(out, indent=1) + "\n")
