#!/usr/bin/env python3
"""Step-3 judges compared: gpt-4.1-mini, GPT-6 Luna, Claude Haiku 5.5 (Roger, 2026-10-26).

Each judge scored the same responses under rubric versions 0, 3 (twice), 4
and 5: the role rubric experiment's 30 sample roles (October responses), the
11 May roles that keep little, and the 8 traits of the held-response sample.
This reports, per judge and version:

* responses kept (score 3), per set and per role category (the categories of
  the v5 check's key; A, helpful professionals, is v5's target);
* judge noise: responses whose keep / drop flips between two runs of v3
  (for gpt-4.1-mini's May roles, v4), with Cohen's kappa, which corrects the
  raw agreement for the judge's keep rate;
* version effects: responses moved up to 3 and down from 3 between versions,
  with a binomial test of the imbalance, and the reader marks on those flips;
* agreement with the blind readers: every response a reader marked (the held
  sample, the arm reading sheets, the A1/A6, v5 and A11 checks), as the share
  of those marked good (G) that the judge scores 3, of those marked bad (B),
  and borderline (T), with the AUC of the 0-3 score (good over bad, whatever
  the threshold).  Those responses were chosen from gpt-4.1-mini's discards
  and disagreements, so they over-represent its borderline cases.

Usage:
    uv run python results_analysis/judge_comparison.py --out reports/pipeline/judge_comparison/judge_comparison.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from assistant_axis import json_metadata  # noqa: E402
from assistant_axis.provenance import InputSpec, current_file_input, current_files_input  # noqa: E402

R = REPO / "runpod_workspace" / "rubric_exp"
REPORTS = REPO / "reports" / "pipeline" / "role_rubric_experiment"
JUDGES = ("gpt-4.1-mini", "gpt-6-luna", "claude-haiku-5-5")
VERSIONS = ("v0", "v3", "v3_rerun", "v4", "v5")
SETS = ("oct", "may", "traits")
#: gpt-4.1-mini's cells judged before the comparison, where they were written.
LEGACY = {("gpt-4.1-mini", "oct", "v3"): R / "versions/v3/scores",
          ("gpt-4.1-mini", "oct", "v3_rerun"): R / "versions/v3_rerun/scores",
          ("gpt-4.1-mini", "oct", "v4"): R / "versions/v4/scores",
          ("gpt-4.1-mini", "oct", "v5"): R / "versions/v5/scores",
          ("gpt-4.1-mini", "may", "v4"): R / "may_target/scores_v4",
          ("gpt-4.1-mini", "may", "v4_rerun"): R / "may_target/scores_v4_rerun",
          ("gpt-4.1-mini", "may", "v5"): R / "may_target/scores_v5"}
#: Version pairs whose flips are counted (the second of each judged twice is noise).
PAIRS = (("v3", "v3_rerun"), ("v4", "v4_rerun"), ("v0", "v3"), ("v3", "v4"), ("v3", "v5"), ("v4", "v5"))


def score_dir(judge: str, set_: str, ver: str) -> Path:
    return LEGACY.get((judge, set_, ver), R / "judges" / judge / set_ / ver)


def load_cell(d: Path) -> dict:
    """``{entity: {key: score}}`` of a scores directory (empty when it does not exist)."""
    out = {}
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            if p.stem.startswith("_") or p.stem in ("usage", "judge_rubric", "batch_state"):
                continue
            s = {k: v for k, v in json.loads(p.read_text()).items() if isinstance(v, int)}
            if s:
                out[p.stem] = s
    return out


def marks_of(sheet_paths) -> dict:
    """``item number -> mark text`` over sheets whose items are ``### N`` with a ``mark:`` line."""
    out, cur = {}, None
    for path in sheet_paths:
        for line in Path(path).read_text().splitlines():
            m = re.match(r"^### (\d+)\s*$", line)
            if m:
                cur = m.group(1)
                continue
            m = re.match(r"^mark:\s*(\S+)", line)
            if m and cur:
                out[cur] = m.group(1)
                cur = None
    return out


def xy_mark(mark: str, item: dict):
    """An arm reading sheet's verdict as G / B / T / ?, or None to skip.  ``X`` and ``Y`` say which of the
    two scores was right (``x_is`` names the arm shown as X); a right score of 3 is G, any other B."""
    m = (mark or "")[:1].upper()
    if m in ("T", "?"):
        return m
    if m not in ("X", "Y"):
        return None   # SKIP (a duplicate marked elsewhere) or unmarked
    x_score, y_score = ((item["a0_score"], item["arm_score"]) if item["x_is"] == "A0"
                        else (item["arm_score"], item["a0_score"]))
    return "G" if (x_score if m == "X" else y_score) == 3 else "B"


def reader_items() -> list:
    """Every reader-marked response as ``{set, entity, key, mark, source}`` with ``mark`` in G / B / T / ?;
    the first source to mark a response keeps it (held sample, v5 check, A11, A1/A6, arm sheets)."""
    items, seen, conflicts = [], {}, 0

    def add(set_, entity, key, mark, source):
        nonlocal conflicts
        mark = mark[:1].upper()
        if mark not in "GBT?":
            return
        k = (set_, entity, key)
        if k in seen:
            conflicts += seen[k] != mark
            return
        seen[k] = mark
        items.append({"set": set_, "entity": entity, "key": key, "mark": mark, "source": source})

    H = REPORTS / "held_sample"
    hk = json.loads((H / "key.json").read_text())["items"]
    hm = marks_of(sorted(H.glob("sheet_*.md")))
    for i, it in hk.items():
        if i in hm:
            add("traits" if it["kind"] == "traits" else it["source"], it["file_stem"], it["key"], hm[i], "held")
    V = REPORTS / "v5_check"
    vk = json.loads((V / "key.json").read_text())["items"]
    vm = marks_of(sorted(V.glob("sheet_*.md")))
    for i, it in vk.items():
        if i in vm:
            add(it["source"], it["role"], it["key"], vm[i], "v5_check")
    A = REPORTS / "a11_altruist_check"
    ak = json.loads((A / "key.json").read_text())["items"]
    am = marks_of([A / "sheet_1.md"])
    for i, it in ak.items():
        if i in am:
            add("oct", "altruist", it["key"], am[i], "a11_check")
    C = REPORTS / "a1_a6_check"
    ck = json.loads((C / "key.json").read_text())["items"]
    cm = marks_of(sorted(C.glob("sheet_*.md")))
    for i, it in ck.items():
        if i in cm:
            add("oct", it["role"], it["key"], cm[i], "a1_a6_check")
    rk = json.loads((REPORTS / "reading_sheet_key.json").read_text())["items"]
    rm = marks_of(sorted((REPORTS / "reading_sheet").glob("page_*.md")))
    for i, it in rk.items():
        m = xy_mark(rm.get(i, ""), it)
        if m is not None:
            add("oct", it["role"], it["key"], m, "arm_sheets")
    return items, conflicts


def binom_p(up: int, down: int) -> float:
    from scipy.stats import binomtest
    return float(binomtest(up, up + down, 0.5).pvalue) if up + down else 1.0


def kappa(n11: int, n10: int, n01: int, n00: int) -> float:
    """Cohen's kappa of two keep / drop runs from their 2 x 2 counts (1 = kept): agreement beyond what
    the two keep rates give by chance, so judges that keep very different shares can be compared."""
    n = n11 + n10 + n01 + n00
    if not n:
        return float("nan")
    pa, pb = (n11 + n10) / n, (n11 + n01) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return ((n11 + n00) / n - pe) / (1 - pe) if pe < 1 else float("nan")


def auc(pos, neg) -> float:
    """The chance that a score from ``pos`` exceeds one from ``neg``, ties counted half (Mann-Whitney):
    how well the 0-3 scale orders good above bad whatever the keep threshold."""
    if not pos or not neg:
        return float("nan")
    return sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / (len(pos) * len(neg))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    cats = json.loads((REPORTS / "v5_check/key.json").read_text())["categories"]
    cat_of = {r: c[:1] for c, rs in cats.items() for r in rs}

    cells = {(j, s, v): load_cell(score_dir(j, s, v)) for j in JUDGES for s in SETS for v in VERSIONS + ("v4_rerun",)}
    cells = {k: c for k, c in cells.items() if c}
    inputs: list[InputSpec] = [current_file_input(dep_key="producer_script", path=Path(__file__).resolve())]
    for (j, s, v), c in sorted(cells.items()):
        d = score_dir(j, s, v)
        inputs.append(current_files_input(dep_key=f"scores_{j}_{s}_{v}", paths=sorted(d.glob("*.json"))))

    res = {"kept": {}, "flips": {}, "readers": {}}
    print("== responses kept (score 3) / judged")
    for (j, s, v), c in sorted(cells.items()):
        n = sum(len(x) for x in c.values())
        k = sum(sum(1 for y in x.values() if y == 3) for x in c.values())
        by_cat, n_cat = Counter(), Counter()
        for e, x in c.items():
            cat = cat_of.get(e, "T" if s == "traits" else "?")
            by_cat[cat] += sum(1 for y in x.values() if y == 3)
            n_cat[cat] += len(x)
        res["kept"][f"{j}|{s}|{v}"] = {"kept": k, "n": n, "entities": len(c),
                                       "per_entity": {e: sum(1 for y in x.values() if y == 3) for e, x in c.items()},
                                       "by_category": dict(by_cat), "n_by_category": dict(n_cat)}
        print(f"  {j:17s} {s:6s} {v:9s} {k:6d} / {n:6d} ({100 * k / n:4.1f}%)  {len(c)} entities")

    letters = sorted(cats)
    print("\n== kept per role category (% of the category's responses): "
          + "; ".join(f"{c[:1]} {c[2:]}" for c in letters))
    for s in ("oct", "may"):
        for j in JUDGES:
            for v in VERSIONS:
                r = res["kept"].get(f"{j}|{s}|{v}")
                if not r:
                    continue
                cells_ = [f"{c[:1]} {100 * r['by_category'].get(c[:1], 0) / r['n_by_category'][c[:1]]:5.1f}"
                          if r["n_by_category"].get(c[:1]) else f"{c[:1]}   -  " for c in letters]
                print(f"  {j:17s} {s:4s} {v:9s} " + "  ".join(cells_))

    print("\n== flips: up to 3 / down from 3 (p, binomial); second-run pairs are judge noise")
    for j in JUDGES:
        for s in SETS:
            for a, b in PAIRS:
                ca, cb = cells.get((j, s, a)), cells.get((j, s, b))
                if not ca or not cb:
                    continue
                up = down = both = n = 0
                for e in set(ca) & set(cb):
                    for key in set(ca[e]) & set(cb[e]):
                        n += 1
                        up += ca[e][key] < 3 <= cb[e][key]
                        down += ca[e][key] == 3 > cb[e][key]
                        both += ca[e][key] == 3 == cb[e][key]
                k_ = kappa(both, down, up, n - both - up - down)
                res["flips"][f"{j}|{s}|{a}->{b}"] = {"up": up, "down": down, "n": n, "p": binom_p(up, down),
                                                     "kappa": k_}
                print(f"  {j:17s} {s:6s} {a:>8s}->{b:9s} up {up:5d} down {down:5d} of {n:6d} "
                      f"({100 * (up + down) / max(n, 1):4.1f}% flipped, kappa {k_:.2f})  p={binom_p(up, down):.1g}")

    items, conflicts = reader_items()
    print(f"\n== agreement with readers: {len(items)} marked responses ({Counter(i['mark'] for i in items)}; "
          f"{conflicts} marked differently by two sources, first kept)")
    for j in JUDGES:
        for v in VERSIONS:
            scores = {}
            for s in SETS:
                c = cells.get((j, s, v))
                if not c:
                    continue
                for it in items:
                    if it["set"] != s:
                        continue
                    sc = c.get(it["entity"], {}).get(it["key"])
                    if sc is not None:
                        scores.setdefault((s, it["mark"]), []).append(sc)
            if not scores:
                continue
            out = {f"{s}|{m}": {"scored_3": sum(x == 3 for x in xs), "scored_2_or_3": sum(x >= 2 for x in xs),
                                "n": len(xs)} for (s, m), xs in scores.items()}
            for s in SETS:
                if (s, "G") in scores and (s, "B") in scores:
                    out[f"{s}|auc_G_over_B"] = auc(scores[s, "G"], scores[s, "B"])
            res["readers"][f"{j}|{v}"] = out
            parts = []
            for s in SETS:
                g, b = scores.get((s, "G")), scores.get((s, "B"))
                if g or b:
                    parts.append(f"{s}: G {sum(x == 3 for x in g)}/{len(g)}" if g else f"{s}:")
                    if b:
                        parts[-1] += f", B {sum(x == 3 for x in b)}/{len(b)}"
                    if g and b:
                        parts[-1] += f", AUC {out[f'{s}|auc_G_over_B']:.2f}"
            print(f"  {j:17s} {v:9s} " + "; ".join(parts))

    marked = {(i["set"], i["entity"], i["key"]): i["mark"] for i in items}
    print("\n== reader marks on each judge's version flips (marked flips: G / B / T)")
    for j in JUDGES:
        for s in SETS:
            for a, b in PAIRS:
                if b.endswith("_rerun"):
                    continue
                ca, cb = cells.get((j, s, a)), cells.get((j, s, b))
                if not ca or not cb:
                    continue
                tally = {"up": Counter(), "down": Counter()}
                for e in set(ca) & set(cb):
                    for key in set(ca[e]) & set(cb[e]):
                        m = marked.get((s, e, key))
                        if m and ca[e][key] < 3 <= cb[e][key]:
                            tally["up"][m] += 1
                        elif m and ca[e][key] == 3 > cb[e][key]:
                            tally["down"][m] += 1
                res["flips"][f"{j}|{s}|{a}->{b}"]["reader_marks"] = {d: dict(t) for d, t in tally.items()}
                if any(tally.values()):
                    print(f"  {j:17s} {s:6s} {a:>3s}->{b:3s}  "
                          + "   ".join(f"{d} {t['G']}/{t['B']}/{t['T']}" for d, t in tally.items()))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    res["reader_items"] = items
    args.out.write_text(json.dumps(json_metadata(res, inputs=inputs, title="Step-3 judge comparison"), indent=1) + "\n")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
