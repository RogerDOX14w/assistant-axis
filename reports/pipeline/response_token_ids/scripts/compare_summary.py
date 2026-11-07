"""Print, for each step-6 comparison JSON, per response class and slot group:
cells, bit-identical fraction, cosine (p01, median, min), relative difference
(median, p99, max) and relative norm change (median, p99, max), pooled over
layers and at layers 25 and 49 (cosine and rel_diff only there).
    python compare_summary.py <results dir> [pair ...]"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]) / "compare"
pairs = sys.argv[2:] or ["text_vs_ids", "ids_vs_turn", "text_vs_turn", "text_vs_text_bs1"]
def q(x, k): return x.get(k, float("nan")) if x else float("nan")
for p in pairs:
    s = json.loads((d / f"{p}.json").read_text())["summary"]["all"]
    print(f"\n=== {p}")
    print(f"{'class':16} {'grp':7} {'cells':>7} {'bitid':>6} | {'cos p01':>9} {'cos med':>9} {'cos min':>9} | "
          f"{'rdiff med':>9} {'rdiff p99':>9} {'rdiff max':>9} | {'rnorm med':>9} {'rnorm p99':>9} {'rnorm max':>9} | "
          f"{'L25 cos p01':>11} {'L25 rd med':>10} {'L49 cos p01':>11} {'L49 rd med':>10}")
    for cls in ("clean", "capped", "stripped", "stripped+capped", "all"):
        for grp in ("slot0", "header"):
            r = s.get(cls, {}).get(grp)
            if not r: continue
            c, rd, rn = r["cos_all_layers"], r["rel_diff_all_layers"], r["rel_norm_all_layers"]
            c25, rd25, c49, rd49 = r.get("cos_layer25", {}), r.get("rel_diff_layer25", {}), r.get("cos_layer49", {}), r.get("rel_diff_layer49", {})
            print(f"{cls:16} {grp:7} {r['n_cells']:7d} {r['frac_bit_identical']:6.3f} | {q(c,'p01'):9.6f} {q(c,'median'):9.6f} {q(c,'min'):9.6f} | "
                  f"{q(rd,'median'):9.2e} {q(rd,'p99'):9.2e} {q(rd,'max'):9.2e} | {q(rn,'median'):9.2e} {q(rn,'p99'):9.2e} {q(rn,'max'):9.2e} | "
                  f"{q(c25,'p01'):11.6f} {q(rd25,'median'):10.2e} {q(c49,'p01'):11.6f} {q(rd49,'median'):10.2e}")
