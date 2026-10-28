"""Tally the v7 reading sheets together with the v6 ones (2026-10-28): precision and recall of each judge
configuration, the good share of what gpt-5.6-luna and gpt-4.1-mini v7 add and remove against v6, and the roles
each configuration keeps too few responses of.

Roger's targets (2026-10-28): precision above 95%, ideally above 97%; recall matters through the number of roles
of which a configuration keeps less than 25-40% of the responses.

Every October and May response falls in one cell: its set and its first-run keep decisions (gpt-4.1-mini v5,
v6, v7; gpt-5.6-luna v6, v7; with --with_v8, gpt-4.1-mini and gpt-5.6-luna v8 as well).  Each marked response is
weighted by the inverse of its chance of being drawn by any sample (the v6 sheets' strata; these sheets' strata
among responses the v6 sheets left out; with --with_v8 and key_v8.json, Roger's v8 sheet's strata among responses
neither left marked), so marks from strata sampled at different rates pool correctly.  A cell's good share is the weighted mean of its
marked responses; a cell with none borrows the share of the first coarser cell that has some (dropping
gpt-4.1-mini v5's decision, then all of gpt-4.1-mini's).  Since every configuration's keep decision is part of the cell,
the number of responses each keeps is exact; only the good shares are estimated.  Per role group, the same with
the group added to the cell.  G counts 1, T 0.5, Roger's "G/T" 0.75, B 0; ? is left out.  Each response's mark
is Roger's if he gave one, else the v6 sheets' third-round mark, else this round's; the ten re-marks are
compared with the third round, not used twice.  Intervals: a bootstrap of each sample within its strata.
Writes tally.json.

--extra_judge (with --with_v8) adds one more configuration that no sample was drawn by, Claude Haiku 5.5 under
v5 or v8, or gpt-5.6-luna under v9: its keep decision joins the cells, a cell with no marks borrows first from the cell of gpt-5.6-luna's
decisions (v6 to v8) and its own, and what it keeps and drops against gpt-5.6-luna v8 is reported as a change.  Its
precision rests on the marks of the other judges' samples, so cells only it keeps are thinly covered.

    uv run python reports/pipeline/judge_comparison/reader_check_v7/tally.py [--with_v8 [--extra_judge haiku:v8]]
"""
import argparse
import importlib.util
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

D = Path("reports/pipeline/judge_comparison/reader_check_v7")
V6_DIR = Path("reports/pipeline/judge_comparison/reader_check_v6")
_spec = importlib.util.spec_from_file_location("v7_build", D / "build.py")
b7 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(b7)
v6 = b7.v6
W = {"G": 1.0, "T": 0.5, "G/T": 0.75, "B": 0.0}
ORDER = (("mini", "v5"), ("mini", "v6"), ("mini", "v7"), ("luna", "v6"), ("luna", "v7"))
V8_ORDER = (("mini", "v8"), ("luna", "v8"))
NAMES = {("mini", "v5"): "reference (gpt-4.1-mini v5)", ("mini", "v6"): "gpt-4.1-mini v6",
         ("mini", "v7"): "gpt-4.1-mini v7", ("mini", "v8"): "gpt-4.1-mini v8", ("luna", "v6"): "gpt-5.6-luna v6",
         ("luna", "v7"): "gpt-5.6-luna v7", ("luna", "v8"): "gpt-5.6-luna v8",
         ("luna", "v9"): "gpt-5.6-luna v9",
         ("haiku", "v5"): "claude-haiku-5-5 v5", ("haiku", "v8"): "claude-haiku-5-5 v8"}
JUDGE = {"mini": "gpt-4.1-mini", "luna": "gpt-5.6-luna", "haiku": "claude-haiku-5-5"}
#: (judge, from version, to version): the changes whose additions and removals are reported.
CHANGES = (("luna", "v6", "v7"), ("mini", "v6", "v7"))
V8_CHANGES = (("luna", "v7", "v8"), ("mini", "v7", "v8"))
KEEP_FLOORS = (0.25, 0.30, 0.40)
N_BOOT = 1000


def sheet_marks(d: Path) -> dict:
    out = {}
    for p in sorted(d.glob("sheet_*.md")):
        cur = None
        for line in p.read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(G/T|\S)", line)
            if m and cur:
                out[cur] = m.group(1).upper()
                cur = None
    return out


def fine_group(set_: str, entity: str) -> str:
    g7 = b7.group(set_, entity)
    if set_ == "oct" and entity in ("perfectionist", "altruist"):
        return entity
    return "stance, other" if g7 == "stance" else g7


def levels(s: str, bits: tuple, g: str | None, luna: tuple = (3, 4), extra: tuple = ()) -> list:
    """The cells a response's good share is looked up in, finest first: its keep decisions and role group; its
    keep decisions; without gpt-4.1-mini v5's; gpt-5.6-luna's and the extra judge's (the positions ``luna`` and
    ``extra``), when there is one; gpt-5.6-luna's alone; its set.  The levels' keys differ in length."""
    out = [(s, bits, g)] if g else []
    out += [(s, bits), (s, bits[1:])]
    if extra:
        out.append((s, tuple(bits[i] for i in luna + extra)))
    return out + [(s, tuple(bits[i] for i in luna)), (s,)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reader_weights", default="",
                    help="score the readers' marks (not Roger's) differently, e.g. B=0.57,T=0.9: a sensitivity check "
                         "against Roger's own marking")
    ap.add_argument("--calibrate_sheet2", action="store_true",
                    help="score the readers' B and T marks among gpt-5.6-luna v7's keeps in the groups of "
                         "roger_sheet_2.md by Roger's mean mark there for the same group and readers' mark")
    ap.add_argument("--with_v8", action="store_true",
                    help="add gpt-4.1-mini and gpt-5.6-luna under rubric v8, and Roger's v8 sheet (key_v8.json)")
    ap.add_argument("--extra_judge", choices=["haiku:v5", "haiku:v8", "luna:v9"],
                    help="with --with_v8: add Claude Haiku 5.5 under v5 or v8, or gpt-5.6-luna under v9, "
                         "compared with gpt-5.6-luna v8")
    ap.add_argument("--out", type=Path, default=D / "tally.json")
    args = ap.parse_args()
    if args.extra_judge and not args.with_v8:
        ap.error("--extra_judge needs --with_v8")
    extra = (tuple(args.extra_judge.split(":")),) if args.extra_judge else ()
    order = ORDER + (V8_ORDER if args.with_v8 else ()) + extra
    configs = {NAMES[o]: i for i, o in enumerate(order)}
    luna_idx = tuple(i for i, o in enumerate(order) if o[0] == "luna" and o not in extra)
    extra_idx = tuple(order.index(o) for o in extra)
    changes = [(f"{JUDGE[j]} {a}->{b}", order.index((j, a)), order.index((j, b)))
               for j, a, b in CHANGES + (V8_CHANGES if args.with_v8 else ())]
    changes += [(f"{NAMES[('luna', 'v8')]}->{NAMES[o]}", order.index(("luna", "v8")), order.index(o)) for o in extra]
    scores = dict(b7.SCORES)
    if args.with_v8:
        scores.update({(j, "v8"): {s: v6.R / f"judges/{JUDGE[j]}/{s}/v8" for s in v6.RESPONSES} for j in ("mini", "luna")})
    scores.update({(j, v): {s: v6.R / f"judges/{JUDGE[j]}/{s}/{v}" for s in v6.RESPONSES} for j, v in extra})
    sc = {(j, v, s): v6.scores(d) for (j, v), ds in scores.items() for s, d in ds.items()}
    k6 = json.loads((V6_DIR / "key.json").read_text())
    k7 = json.loads((D / "key.json").read_text())
    k8, b8 = None, None
    if args.with_v8 and (D / "key_v8.json").exists():
        k8 = json.loads((D / "key_v8.json").read_text())
        _s8 = importlib.util.spec_from_file_location("v8_build", D / "build_v8.py")
        b8 = importlib.util.module_from_spec(_s8)
        _s8.loader.exec_module(b8)
    size = Counter()          # (set, bits) and (set, bits, group) -> responses
    info = {}                 # (set, entity, key) -> (bits, group, pi)
    for s in v6.RESPONSES:
        t = [sc[(j, v, s)] for j, v in order]
        for e in sorted(set.intersection(*(set(x) for x in t))):
            g = fine_group(s, e)
            for k in sorted(set.intersection(*(set(x[e]) for x in t))):
                bits = tuple(int(x[e][k] == 3) for x in t)
                size[(s, bits)] += 1
                size[(s, bits, g)] += 1
                cell6 = "".join(map(str, (bits[0], bits[1], bits[3])))
                g6 = v6.group(s, e)
                st6 = f"{s}|{cell6}|{g6 if g6 in v6.WANT[(s, cell6)] else '*'}"
                pi6 = k6["sampled"].get(st6, 0) / k6["population"][st6]
                p = b7.part(bits[1] == 1, bits[2] == 1, bits[3] == 1, bits[4] == 1)
                pi7 = 0.0
                if p:
                    g7 = b7.group(s, e)
                    st7 = f"{s}|{p}|{g7 if g7 in b7.WANT[(s, p)] else '*'}"
                    left = k7["population"][st7] - k7["marked_on_v6_sheets"].get(st7, 0)
                    pi7 = k7["sampled"].get(st7, 0) / left if left else 0.0
                pi8, st8 = 0.0, None
                if k8 is not None:
                    st8 = b8.stratum(s, e, dict(zip(order, bits)))
                    if st8:
                        left = k8["population"][st8] - k8["marked_before"].get(st8, 0)
                        pi8 = k8["sampled"].get(st8, 0) / left if left else 0.0
                pi = 1 - (1 - pi6) * (1 - pi7) * (1 - pi8)
                info[(s, e, k)] = (bits, g, pi, st6, st7 if p else None, st8)
    # Marks, one per response: Roger's, then the v6 sheets', then this round's.
    m6, m7 = sheet_marks(V6_DIR), sheet_marks(D)
    roger = {i: r["mark"] for i, r in json.loads((V6_DIR / "roger_marks.json").read_text())["v6_items"].items()}
    roger7 = json.loads((D / "roger_marks.json").read_text())["items"]
    roger.update({k.split("/")[1]: r["mark"] for k, r in roger7.items() if k.startswith("v6/")})
    roger_v7 = {k.split("/")[1]: r["mark"] for k, r in roger7.items() if k.startswith("v7/")}
    rows = {}
    if k8 is not None:
        for i, it in k8["items"].items():
            r = roger7.get(f"v8/{i}")
            if r and r["mark"] in W:
                rows[(it["set"], it["entity"], it["key"])] = (r["mark"], "Roger", "v8:" + it["stratum"])
    for i, it in k7["items"].items():
        mk = roger_v7.get(i) or m7.get(i)
        if it["stratum"] != "remark" and mk in W:
            rows[(it["set"], it["entity"], it["key"])] = (mk, "Roger" if i in roger_v7 else "v7", it["stratum"])
    for i, it in k6["items"].items():
        mk = roger.get(i) or m6.get(i)
        if mk in W:
            rows[(it["set"], it["entity"], it["key"])] = (mk, "Roger" if i in roger else "v6", it["stratum"])
    print(f"marks used: {dict(Counter(src for _, src, _ in rows.values()))}; this round's sheets: "
          f"{sum(1 for i in k7['items'] if i in m7)} of {len(k7['items'])} items marked")
    rw = {**W, **dict((k, float(v)) for k, v in (x.split("=") for x in args.reader_weights.split(",") if x))}
    # Sheet 2 calibration: Roger's mean value for each (role group, readers' mark) among gpt-5.6-luna v7's keeps
    # that he marked on roger_sheet_2.md, applied to the readers' marks of the same kind he did not see.
    calib: dict = {}
    if args.calibrate_sheet2:
        acc = defaultdict(list)
        for k, r in roger7.items():
            if r.get("sheet") == 2:
                src_, i = k.split("/")
                it = (k6 if src_ == "v6" else k7)["items"][i]
                acc[(fine_group(it["set"], it["entity"]), (m6 if src_ == "v6" else m7)[i])].append(W[r["mark"]])
        calib = {gk: sum(v) / len(v) for gk, v in acc.items()}
        print("sheet 2 calibration (role group, readers' mark -> Roger's mean):",
              {f"{g} {m}": round(v, 2) for (g, m), v in sorted(calib.items())})

    def value(r, mk, src):
        if src == "Roger":
            return W[mk]
        bits, g = info[r][0], info[r][1]
        if bits[4] and (g, mk) in calib:
            return calib[(g, mk)]
        return rw[mk]
    marked = [(r, value(r, mk, src), src, st) for r, (mk, src, st) in rows.items() if r in info]

    rem = [(i, it["v6_item"], it["v6_mark"], m7.get(i)) for i, it in k7["items"].items() if it["stratum"] == "remark"]
    done = [r for r in rem if r[3]]
    print(f"\n== re-marks: {sum(a == b for _, _, a, b in done)} of {len(done)} agree with the third round"
          + "".join(f"\n  #{i} (v6 #{n6}): third round {a}, now {b}" for i, n6, a, b in done if a != b))

    def sums(sample) -> dict:
        acc = defaultdict(lambda: [0.0, 0.0])
        for r, w_good, _, _ in sample:
            bits, g, pi = info[r][:3]
            for lv in levels(r[0], bits, g, luna_idx, extra_idx):
                acc[lv][0] += w_good / pi
                acc[lv][1] += 1 / pi
        return acc

    def share(acc, s, bits, g=None) -> float:
        for lv in levels(s, bits, g, luna_idx, extra_idx):
            if acc.get(lv) and acc[lv][1]:
                return acc[lv][0] / acc[lv][1]
        return float("nan")

    def estimate(acc) -> dict:
        res = {}
        cells = [c for c in size if len(c) == 2]
        gcells = [c for c in size if len(c) == 3]
        for s in v6.RESPONSES:
            tot_good = sum(size[c] * share(acc, *c) for c in cells if c[0] == s)
            for name, j in configs.items():
                kc = [c for c in cells if c[0] == s and c[1][j]]
                n = sum(size[c] for c in kc)
                good = sum(size[c] * share(acc, *c) for c in kc)
                by_g = defaultdict(lambda: [0, 0.0])
                for c in gcells:
                    if c[0] == s and c[1][j]:
                        by_g[c[2]][0] += size[c]
                        by_g[c[2]][1] += size[c] * share(acc, *c)
                res[f"{s}|{name}"] = {"kept": n, "precision": good / n, "recall": good / tot_good,
                                      "by_group": {g: {"kept": x[0], "precision": x[1] / x[0]}
                                                   for g, x in sorted(by_g.items())}}
            for label, a, b_ in changes:
                for what, sel in (("adds", lambda bt: bt[b_] and not bt[a]), ("removes", lambda bt: bt[a] and not bt[b_])):
                    by_g = defaultdict(lambda: [0, 0.0])
                    for c in gcells:
                        if c[0] == s and sel(c[1]):
                            by_g[c[2]][0] += size[c]
                            by_g[c[2]][1] += size[c] * share(acc, *c)
                    res[f"{s}|{label} {what}"] = {g: {"n": x[0], "good_share": x[1] / x[0]} for g, x in sorted(by_g.items())}
        return res

    point = estimate(sums(marked))
    rng = random.Random(1)
    design = defaultdict(list)
    for row in marked:
        design[(row[2] == "v7", row[3])].append(row)
    boots = []
    for _ in range(N_BOOT):
        boots.append(estimate(sums([rng.choice(rs) for rs in design.values() for _ in rs])))

    def ci(f) -> str:
        xs = sorted(x for x in (f(b) for b in boots) if x == x)
        if not xs:
            return "no interval"
        return f"{100 * xs[int(0.025 * len(xs))]:.1f} to {100 * xs[int(0.975 * len(xs)) - 1]:.1f}"

    print("\n== each configuration (95% intervals)")
    for s in v6.RESPONSES:
        for name in configs:
            e = point[f"{s}|{name}"]
            print(f"  {s:4s} {name:28s} keeps {e['kept']:6d}: precision {100 * e['precision']:5.1f}% "
                  f"({ci(lambda b: b[f'{s}|{name}']['precision'])}), recall {100 * e['recall']:5.1f}%")
        for label, ia, ib in changes:
            a, b_ = f"{s}|{NAMES[order[ia]]}", f"{s}|{NAMES[order[ib]]}"
            d = point[b_]["precision"] - point[a]["precision"]
            print(f"  {s:4s} {label}: precision {100 * d:+.1f} points "
                  f"({ci(lambda b: b[b_]['precision'] - b[a]['precision'])}), "
                  f"recall {100 * (point[b_]['recall'] - point[a]['recall']):+.1f} points")
    print("\n== precision by role group")
    for s in v6.RESPONSES:
        for name in configs:
            bg = point[f"{s}|{name}"]["by_group"]
            print(f"  {s:4s} {name:28s} " + "; ".join(f"{g} {100 * x['precision']:.0f}%" for g, x in bg.items()))
    print("\n== good share of what each change adds and removes, by role group")
    for s in v6.RESPONSES:
        for label, _, _ in changes:
            for what in ("adds", "removes"):
                print(f"  {s:4s} {label} {what}: " + "; ".join(
                    f"{g} {x['n']} at {100 * x['good_share']:.0f}%" for g, x in point[f"{s}|{label} {what}"].items()))

    print("\n== roles with a low keep rate (first runs)")
    low = {}
    for s in v6.RESPONSES:
        for name, (j, v) in zip(configs, order):
            t = sc[(j, v, s)]
            rates = {e: sum(x == 3 for x in d.values()) / len(d) for e, d in t.items() if d}
            low[f"{s}|{name}"] = {f"below {int(100 * f)}%": sorted(e for e, r in rates.items() if r < f) for f in KEEP_FLOORS}
            counts = ", ".join(f"<{int(100 * f)}%: {len(low[f'{s}|{name}'][f'below {int(100 * f)}%'])}" for f in KEEP_FLOORS)
            worst = ", ".join(f"{e} {100 * r:.0f}%" for e, r in sorted(rates.items(), key=lambda x: x[1])[:5])
            print(f"  {s:4s} {name:28s} {len(rates)} roles; {counts}; lowest: {worst}")
    args.out.write_text(json.dumps({"reader_weights": rw, "estimates": point, "remarks": rem,
                                    "low_keep_roles": low}, indent=1) + "\n")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
