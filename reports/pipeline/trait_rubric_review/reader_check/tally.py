"""Tally the trait reading sheets: the readers' marks per stratum and, weighted back by the strata's populations,
each judge configuration's precision and recall per tier (low / medium / high May keep rate) and overall.  Strata
are tier x cell, cells keep (1) / drop (0) by the reference (gpt-4.1-mini's May production scores), gpt-4.1-mini
v3 and gpt-5.6-luna v3.  T counts as half good, half bad; ? is left out.  Roger's own marks (roger_marks.json,
``{"items": {"<n>": "<mark>"}}``) replace the readers' where he gave one; his "G/T" counts three-quarters good.
Also the judges' run-to-run agreement (Cohen's kappa on keep / drop) from the full cells, not the sample.
Writes tally.json.

    uv run python reports/pipeline/trait_rubric_review/reader_check/tally.py [--readers]

``--readers`` ignores roger_marks.json, for the readers-only numbers.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

D = Path("reports/pipeline/trait_rubric_review/reader_check")
sys.path.insert(0, str(D))
import build  # noqa: E402

WEIGHT = {"G": 1.0, "G/T": 0.75, "T": 0.5, "T/B": 0.25, "B": 0.0}
CONFIGS = {"reference (gpt-4.1-mini, May)": "may", "gpt-4.1-mini v3": "mini_v3",
           "gpt-4.1-mini v3 rerun": "mini_v3_rerun", "gpt-5.6-luna v3": "luna_v3",
           "gpt-5.6-luna v3 rerun": "luna_v3_rerun"}


def marks(first_only: bool = False) -> dict:
    """``item -> (mark, note)`` from the sheets' ``mark:`` lines; a mark on a second-reading sheet (reread_*.md,
    reread.py) replaces the first unless ``first_only``."""
    out = {}
    sheets = sorted(D.glob("sheet_*.md")) + ([] if first_only else sorted(D.glob("reread_*.md")))
    for p in sheets:
        cur = None
        for line in p.read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(\S+)(.*)", line)
            if m and cur:
                mk = m.group(1).upper()
                out[cur] = ("G/T" if mk in ("G/T", "T/G") else mk[:1], m.group(2).strip())
                cur = None
    return out


def kappa(a: dict, b: dict) -> float:
    keys = [k for k in a if k in b]
    if not keys:
        return float("nan")
    n = len(keys)
    p11 = sum(a[k] == 3 and b[k] == 3 for k in keys) / n
    p00 = sum(a[k] != 3 and b[k] != 3 for k in keys) / n
    pa = sum(a[k] == 3 for k in keys) / n
    pb = sum(b[k] == 3 for k in keys) / n
    po, pe = p11 + p00, pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def main() -> None:
    readers_only = "--readers" in sys.argv[1:]
    key = json.loads((D / "key.json").read_text())
    items = key["items"]
    mk = {i: m for i, (m, _) in marks().items()}
    print(f"{len(mk)} of {len(items)} items marked; unmarked: "
          f"{sorted(set(items) - set(mk), key=lambda s: (s[0] == 'n', int(s.lstrip('n'))))}")
    reread = {i: m for i, (m, _) in marks().items() if m != marks(first_only=True).get(i, (None,))[0]}
    if reread:
        print(f"{len(reread)} re-read marks differ from the first reading")
    k2 = D / "key_2.json"
    if k2.exists():   # Roger's second sheet (roger_sheet_2.py): new low-tier items, plus calibration items
        key2 = json.loads(k2.read_text())
        items.update(key2["items"])
    if not readers_only:
        for name in ("roger_marks.json", "roger_marks_2.json"):
            rp = D / name
            if rp.exists():
                roger = json.loads(rp.read_text())["items"]
                if name == "roger_marks_2.json" and k2.exists():
                    cal = [(i, mk.get(i), roger[i]) for i in key2["calibration"] if i in roger]
                    if cal:
                        agree = sum(a == b for _, a, b in cal)
                        print(f"calibration: Roger agrees with the re-readers on {agree} of {len(cal)}: "
                              + ", ".join(f"{i} {a}>{b}" for i, a, b in cal if a != b))
                mk.update({i: m for i, m in roger.items()})
                print(f"{len(roger)} marked by Roger ({name}), overriding the readers")
    out_name = "tally_readers.json" if readers_only else "tally.json"
    by_stratum = defaultdict(Counter)
    for i, it in items.items():
        by_stratum[it["stratum"]][mk.get(i, "-")] += 1

    res = {"strata": {}, "configurations": {}, "kappa": {}, "by_trait": {}}
    print("\n== marks per stratum (tier|cell; cell = reference May, gpt-4.1-mini v3, gpt-5.6-luna v3)")
    for st in sorted(by_stratum):
        c = by_stratum[st]
        n = sum(c[m] for m in WEIGHT)
        good = sum(c[m] * w for m, w in WEIGHT.items()) / n if n else float("nan")
        pop = key["population"][st]
        res["strata"][st] = {"pop": pop, "n": n, "marks": dict(c), "good_share": good}
        print(f"  {st:12s} pop {pop:5d}  sampled {sum(c.values()):3d}  G {c['G']:2d} B {c['B']:2d} T {c['T']:2d} "
              f"G/T {c['G/T']:2d} T/B {c['T/B']:2d} ? {c['?']:2d}   good share {100 * good:5.1f}%")

    print("\n== judge configurations per tier (marked items each keeps, weighted by stratum population; T half good)")
    tiers = list(key["sampled"] and sorted({st.split("|")[0] for st in by_stratum})) + ["all"]
    for tier in tiers:
        for name, field in CONFIGS.items():
            kg = kb = tg = 0.0
            for st in by_stratum:
                if tier != "all" and not st.startswith(tier + "|"):
                    continue
                its = [(i, it) for i, it in items.items() if it["stratum"] == st and mk.get(i) in WEIGHT]
                if not its:
                    continue
                pop = key["population"][st]
                for i, it in its:
                    w = WEIGHT[mk[i]]
                    kept = it["scores"].get(field) == 3
                    kg += pop * kept * w / len(its)
                    kb += pop * kept * (1 - w) / len(its)
                    tg += pop * w / len(its)
            prec = kg / (kg + kb) if kg + kb else float("nan")
            rec = kg / tg if tg else float("nan")
            res["configurations"][f"{tier}|{name}"] = {"kept_good": kg, "kept_bad": kb, "total_good": tg,
                                                       "precision": prec, "recall": rec}
            print(f"  {tier:6s} {name:30s} keeps {kg:7.0f} good, {kb:6.0f} bad of {tg:7.0f} good:  "
                  f"precision {100 * prec:5.1f}%, recall {100 * rec:5.1f}%")

    print("\n== run-to-run agreement on keep / drop (Cohen's kappa over every response of the tier)")
    for judge in ("gpt-4.1-mini", "gpt-5.6-luna"):
        for tier in tiers:
            a, b = {}, {}
            for s, (_, d) in build.SETS.items():
                for e, sc in build.scores(build.R / f"judges/{judge}/{d}/v3").items():
                    if build.tier_of(e) is not None and tier in ("all", build.tier_of(e)):
                        a.update({(e, k): v for k, v in sc.items()})
                for e, sc in build.scores(build.R / f"judges/{judge}/{d}/v3_rerun").items():
                    if build.tier_of(e) is not None and tier in ("all", build.tier_of(e)):
                        b.update({(e, k): v for k, v in sc.items()})
            kp = kappa(a, b)
            keep_a = sum(v == 3 for v in a.values()) / len(a) if a else float("nan")
            res["kappa"][f"{tier}|{judge}"] = {"kappa": kp, "n": len(a), "keep": keep_a}
            print(f"  {tier:6s} {judge:13s} n {len(a):6d}  keep {100 * keep_a:5.1f}%  kappa {kp:.2f}")

    print("\n== raw marks per trait, by what each configuration does with the marked items (unweighted)")
    for e in sorted({it["entity"] for it in items.values()}):
        its = [(i, it) for i, it in items.items() if it["entity"] == e and mk.get(i) in WEIGHT]
        row = {"n": len(its), "marks": dict(Counter(mk[i] for i, _ in its))}
        for name, field in CONFIGS.items():
            kept = [mk[i] for i, it in its if it["scores"].get(field) == 3]
            dropped = [mk[i] for i, it in its if it["scores"].get(field) != 3]
            row[name] = {"kept": dict(Counter(kept)), "dropped": dict(Counter(dropped))}
        res["by_trait"][e] = row
        short = "; ".join(f"{name.split(' ')[0].replace('reference', 'May')} keeps "
                          + "".join(f"{m}{row[name]['kept'].get(m, 0)}" for m in ("G", "B", "T"))
                          + " drops " + "".join(f"{m}{row[name]['dropped'].get(m, 0)}" for m in ("G", "B", "T"))
                          for name in CONFIGS if "rerun" not in name)
        print(f"  {e:24s} n {len(its):3d}  {short}")
    (D / out_name).write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
