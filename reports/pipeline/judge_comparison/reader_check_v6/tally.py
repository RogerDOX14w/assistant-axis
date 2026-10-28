"""Tally the v6 reading sheets (2026-10-28): the readers' marks per cell and stratum, and, weighted back by the
strata's populations, each candidate's change against the reference.  Cells are keep (1) / drop (0) by the
reference gpt-4.1-mini v5, then gpt-4.1-mini v6, then gpt-5.6-luna v6.  A candidate's change is the responses
it adds (reference 0, candidate 1) and removes (reference 1, candidate 0); a G it adds or a B it removes is a
gain, a B it adds or a G it removes a loss.  T counts as half good, half bad; ? is left out.  Roger's own marks
(roger_marks.json) replace the readers' where he gave one.  Writes tally.json.

    uv run python reports/pipeline/judge_comparison/reader_check_v6/tally.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

D = Path("reports/pipeline/judge_comparison/reader_check_v6")
JUDGES = {"reference (gpt-4.1-mini v5)": 0, "gpt-4.1-mini v6": 1, "gpt-5.6-luna v6": 2}


def marks() -> dict:
    out = {}
    for p in sorted(D.glob("sheet_*.md")):
        cur = None
        for line in p.read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(\S)", line)
            if m and cur:
                out[cur] = m.group(1).upper()
                cur = None
    return out


def main() -> None:
    key = json.loads((D / "key.json").read_text())
    mk = marks()
    items = key["items"]
    print(f"{len(mk)} of {len(items)} items marked; unmarked: {sorted(set(items) - set(mk), key=int)}")
    # Roger's own marks take precedence ("G/T", his "G or T", counts three-quarters good).
    roger = {i: r["mark"] for i, r in json.loads((D / "roger_marks.json").read_text())["v6_items"].items()}
    mk.update(roger)
    print(f"{len(roger)} of them marked by Roger, overriding the readers")
    by_stratum = defaultdict(Counter)
    for i, it in items.items():
        by_stratum[it["stratum"]][mk.get(i, "-")] += 1
    # Estimated good / bad responses per stratum: population x the stratum's marked shares.
    est = {}
    for st, c in by_stratum.items():
        n = c["G"] + c["B"] + c["T"] + c["G/T"]
        pop = key["population"].get(st, 0)
        good = (c["G"] + c["T"] / 2 + 0.75 * c["G/T"]) / n if n else float("nan")
        est[st] = {"pop": pop, "n": n, "marks": dict(c), "good_share": good,
                   "good": pop * good if n else 0.0, "bad": pop * (1 - good) if n else 0.0}

    print("\n== marks per stratum (set|cell|group; cell = reference, gpt-4.1-mini v6, gpt-5.6-luna v6)")
    for st in sorted(est):
        e = est[st]
        print(f"  {st:22s} pop {e['pop']:6d}  sampled {sum(by_stratum[st].values()):3d}  "
              f"G {e['marks'].get('G', 0):2d} B {e['marks'].get('B', 0):2d} T {e['marks'].get('T', 0):2d} "
              f"? {e['marks'].get('?', 0):2d}   good share {100 * e['good_share']:5.1f}%")

    res = {"strata": est, "candidates": {}}
    print("\n== each candidate against the reference (estimated responses; T half good)")
    for s in ("oct", "may"):
        for name, j in JUDGES.items():
            if j == 0:
                continue
            add_g = add_b = rem_g = rem_b = 0.0
            for st, e in est.items():
                set_, cell, _ = st.split("|")
                if set_ != s:
                    continue
                ref, cand = cell[0] == "1", cell[j] == "1"
                if cand and not ref:
                    add_g += e["good"]
                    add_b += e["bad"]
                elif ref and not cand:
                    rem_g += e["good"]
                    rem_b += e["bad"]
            net_good, net_bad = add_g - rem_g, add_b - rem_b
            res["candidates"][f"{s}|{name}"] = {"added_good": add_g, "added_bad": add_b,
                                                "removed_good": rem_g, "removed_bad": rem_b,
                                                "net_good_kept": net_good, "net_bad_kept": net_bad}
            print(f"  {s:4s} {name:17s} adds {add_g:7.0f} good + {add_b:6.0f} bad;  removes {rem_g:6.0f} good + "
                  f"{rem_b:6.0f} bad;  net: {net_good:+7.0f} good kept, {net_bad:+6.0f} bad kept")

    print("\n== each judge overall (estimated; the controls' large populations make these noisy)")
    for s in ("oct", "may"):
        tot_g = sum(e["good"] for st, e in est.items() if st.startswith(s + "|"))
        for name, j in JUDGES.items():
            kg = sum(e["good"] for st, e in est.items() if st.startswith(s + "|") and st.split("|")[1][j] == "1")
            kb = sum(e["bad"] for st, e in est.items() if st.startswith(s + "|") and st.split("|")[1][j] == "1")
            prec = kg / (kg + kb) if kg + kb else float("nan")
            rec = kg / tot_g if tot_g else float("nan")
            res["candidates"].setdefault(f"{s}|{name}", {}).update(
                {"kept_good": kg, "kept_bad": kb, "precision": prec, "recall": rec})
            print(f"  {s:4s} {name:27s} keeps {kg:7.0f} good, {kb:6.0f} bad:  precision {100 * prec:5.1f}%, "
                  f"recall {100 * rec:5.1f}%")

    # Any judge configuration, scored on the same strata: within each stratum, the marked items it keeps.
    import sys
    sys.path.insert(0, str(D.parent))
    import abc_consistency as abc
    import build
    weight = {"G": 1.0, "T": 0.5, "G/T": 0.75, "B": 0.0}
    replies = abc.load_replies()

    def stated(judge, ver):
        sc = {s: build.scores(abc.R / judge / s / ver) for s in ("oct", "may")}
        return lambda it: sc[it["set"]].get(it["entity"], {}).get(it["key"])

    def from_answers(judge, ver):
        def f(it):
            x = replies.get((judge, ver, it["set"]), {}).get((it["entity"], it["key"]))
            if not x:
                return None
            score, ans, _ = x
            return abc.implied(ans["A"], ans["B"], ans["C"]) if len(ans) == 3 else score
        return f
    configs = {"reference (gpt-4.1-mini v5)": lambda it: it["scores"]["mini_v5"],
               "gpt-4.1-mini v6": stated("gpt-4.1-mini", "v6"), "gpt-4.1-mini v7": stated("gpt-4.1-mini", "v7"),
               "gpt-5.6-luna v6": stated("gpt-5.6-luna", "v6"), "gpt-5.6-luna v7": stated("gpt-5.6-luna", "v7"),
               "gpt-5.6-luna v6, score from A/B/C": from_answers("gpt-5.6-luna", "v6"),
               "gpt-5.6-luna v7, score from A/B/C": from_answers("gpt-5.6-luna", "v7")}
    print("\n== judge configurations on the same strata (marked items each keeps, weighted by stratum)")
    res["configurations"] = {}
    for s in ("oct", "may"):
        for name, score_of in configs.items():
            kg = kb = tg = 0.0
            for st in by_stratum:
                if not st.startswith(s + "|"):
                    continue
                its = [it for i, it in items.items() if it["stratum"] == st and mk.get(i) in weight]
                if not its:
                    continue
                pop = key["population"][st]
                for it in its:
                    w = weight[mk[[i for i, x in items.items() if x is it][0]]]
                    kept = score_of(it) == 3
                    kg += pop * kept * w / len(its)
                    kb += pop * kept * (1 - w) / len(its)
                    tg += pop * w / len(its)
            prec, rec = kg / (kg + kb), kg / tg
            res["configurations"][f"{s}|{name}"] = {"kept_good": kg, "kept_bad": kb, "precision": prec,
                                                    "recall": rec}
            print(f"  {s:4s} {name:35s} keeps {kg:7.0f} good, {kb:6.0f} bad:  precision {100 * prec:5.1f}%, "
                  f"recall {100 * rec:5.1f}%")
    (D / "tally.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
