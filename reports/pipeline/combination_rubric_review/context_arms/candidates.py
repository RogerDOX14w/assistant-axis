"""The three candidate "both" rules for a combination's responses (Roger, 2026-10-30: draft 14, the one-prompt
rubric; the context sides 16 with 17; 16 with 18) in two views:

1. precision and recall against the reading sheets' letters as adjusted by Roger (his letter overrides the
   holistic readers' where he wrote one; a "?" of his leaves theirs), with the letters as probabilities (keep =
   role weight x trait weight, G 1 ... B 0, an ai mark other than n dropping the response unless the role is an
   AI role), on the sheet's 74 May items, split by kind (r_, t_) and by the combination's May keep level
   (low under 0.25, medium 0.25 to 0.60, high over 0.60).  The sheet's items were picked where a draft and the
   dedicated judge disagreed, plus a few agreed ones, so the cells are small and lean to hard cases: an estimate
   of how the candidates differ on contested responses, not a population figure.
2. the low-keep combinations: on each judged sample (the May exploration sample, the October r_ re-check sample,
   the October t_ sample) the number of combinations each rule keeps under 0.10 and 0.25 of, against the same
   combinations' May keep (gpt-4.1-mini, the April text), and May's count over the whole April grid.

    uv run python reports/pipeline/combination_rubric_review/context_arms/candidates.py

Reads compare.py's loaders and tally.py's letter weights; writes nothing but its output (kept in
candidates_output.txt by the caller).
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare  # noqa: E402
import tally  # noqa: E402

REPO = compare.REPO
TCOMB = REPO / "runpod_workspace" / "tcomb_recheck"
LEVELS = (("low", 0.0, 0.25), ("medium", 0.25, 0.60), ("high", 0.60, 1.01))
RULES = (("April text", lambda r, k: compare.yes(r["C"])),
         ("separate judges", lambda r, k: None if r["Rs"] is None or r["T"] is None else r["Rs"] == 3 and r["T"] == 3),
         ("draft 14", lambda r, k: compare.yes(r["V14"])),
         ("16 and 17", lambda r, k: None if r["V16"] is None or r["V17"] is None else r["V16"] == 3 and r["V17"] == 3),
         ("16 and 18", lambda r, k: None if r["V16"] is None or r["V18"] is None else r["V16"] == 3 and r["V18"] == 3))
CANDIDATES = ("draft 14", "16 and 17", "16 and 18")


def level_of(keep):
    if keep is None:
        return "unknown"
    return next(name for name, lo, hi in LEVELS if lo <= keep < hi)


def adjusted_marks(key, readers, roger):
    """Per item: the readers' role, trait and ai marks with Roger's letters in place of theirs where he wrote
    a letter that carries a weight (his "?" leaves theirs)."""
    out = {}
    for n in key:
        m = dict(readers.get(n, {}))
        for field in ("role", "trait", "ai"):
            rv = roger.get(n, {}).get(field)
            if rv is None:
                continue
            if field == "ai" or rv[0] in tally.WEIGHT:
                m[field] = rv
        out[n] = m
    return out


def both_weight(it, m):
    wr, wt = tally.WEIGHT.get((m.get("role") or (None,))[0]), tally.WEIGHT.get((m.get("trait") or (None,))[0])
    if wr is None or wt is None:
        return None
    ai = m.get("ai")
    ai_ok = ai is None or ai[0].startswith("n") or it["role"] in tally.AI_ROLES
    return wr * wt * (1.0 if ai_ok else 0.0)


def view_sheet(key, readers, roger, may_rows, may_keep):
    print("1. the candidates against the sheet's letters adjusted by Roger (letters as probabilities), by kind and "
          "by the combination's May keep level")
    print("   (low under 0.25, medium 0.25 to 0.60, high over 0.60; n = items with both letters and every judgement; "
          "expected = the letters' expected keep)")
    marks = adjusted_marks(key, readers, roger)
    by_key = {(r["stem"], r["key"]): r for r in may_rows}
    items = []
    for n, it in key.items():
        w = both_weight(it, marks[n])
        row = by_key.get((it["stem"], it["key"]))
        if w is None or row is None or any(row[f"V{v}"] is None for v in (14, 16, 17, 18)):
            continue
        kept = {name: fn(row, it) for name, fn in RULES}
        items.append(dict(n=n, kind=it["stem"][0], level=level_of(may_keep.get(it["stem"])), w=w, kept=kept,
                          roger=n in roger))
    n_roger = sum(i["roger"] for i in items)
    print(f"   {len(items)} items, {n_roger} with Roger's letters, {len(items) - n_roger} with the readers' alone")
    cells = [("all", lambda i: True)]
    cells += [(f"{k}_", (lambda i, k=k: i["kind"] == k)) for k in "rt"]
    cells += [(f"{lv} keep", (lambda i, lv=lv: i["level"] == lv)) for lv, _, _ in LEVELS]
    cells += [(f"{k}_ {lv}", (lambda i, k=k, lv=lv: i["kind"] == k and i["level"] == lv)) for k in "rt" for lv, _, _ in LEVELS]
    head = f"   {'cell':14s} {'n':>3s} {'expected':>8s}  " + "  ".join(f"{c:>26s}" for c in CANDIDATES) + f"  {'separate judges':>26s}"
    print(head)
    print(f"   {'':14s} {'':3s} {'':8s}  " + "  ".join(f"{'keeps  precision  recall':>26s}" for _ in (*CANDIDATES, "")))
    for name, pick in cells:
        sel = [i for i in items if pick(i)]
        if not sel:
            print(f"   {name:14s} {0:3d}")
            continue
        parts = []
        for cand in (*CANDIDATES, "separate judges"):
            pairs = [(i["w"], i["kept"][cand]) for i in sel if i["kept"][cand] is not None]
            p, r = tally.prec_rec(pairs)
            parts.append(f"{mean(k for _, k in pairs):5.2f}  {p:9.2f}  {r:6.2f}")
        print(f"   {name:14s} {len(sel):3d} {mean(i['w'] for i in sel):8.2f}  " + "  ".join(f"{x:>26s}" for x in parts))
    print()


def view_low_keep(samples, may_keep):
    print("2. combinations kept under 0.10 and under 0.25 by each rule, per judged sample, against the same "
          "combinations' May keep (gpt-4.1-mini, the April text)")
    for title, rows in samples:
        per = defaultdict(lambda: defaultdict(list))
        for r in rows:
            for name, fn in RULES:
                k = fn(r, None)
                if k is not None:
                    per[r["stem"]][name].append(k)
        stems = sorted(per)
        keep = {s: {name: (mean(v[name]) if v[name] else None) for name, _ in RULES} for s, v in per.items()}
        for s in stems:
            keep[s]["May"] = may_keep.get(s)
        cols = ["May"] + [name for name, _ in RULES]
        print(f"\n   {title}: {len(stems)} combinations")
        print(f"   {'rule':18s} {'< 0.10':>7s} {'< 0.25':>7s}   {'mean keep':>9s}")
        for c in cols:
            vals = [keep[s][c] for s in stems if keep[s][c] is not None]
            print(f"   {c:18s} {sum(v < 0.10 for v in vals):7d} {sum(v < 0.25 for v in vals):7d}   {mean(vals):9.2f}"
                  + ("" if len(vals) == len(stems) else f"   (on {len(vals)})"))
        low = [s for s in stems if any(keep[s][c] is not None and keep[s][c] < 0.25 for c in cols)]
        print(f"   combinations under 0.25 by any rule ({len(low)}):")
        print(f"   {'combination':44s} " + " ".join(f"{c:>16s}" for c in cols))
        for s in low:
            print(f"   {s:44s} " + " ".join(f"{keep[s][c]:16.2f}" if keep[s][c] is not None else f"{'-':>16s}" for c in cols))


def main() -> None:
    key = json.loads((HERE.parent / "reader_check" / "key.json").read_text())["items"]
    readers = {**tally.parse(HERE.parent / "reader_check" / "sheet_1_marks.md"),
               **tally.parse(HERE.parent / "reader_check" / "sheet_2_marks.md")}
    roger = tally.parse(HERE.parent / "reader_check" / "roger_sheet.md", prefix="your ")
    may_keep = {r["stem"]: r["keep"] for r in json.loads((HERE.parent / "explore" / "keep_rates.json").read_text())}
    for old, new in compare.RENAMED.items():
        if old in may_keep:
            may_keep.setdefault(new, may_keep[old])
    may = compare.load_sample(compare.EXPLORE)
    octo = compare.load_sample(compare.RECHECK)
    tcomb = compare.load_sample(TCOMB)
    view_sheet(key, readers, roger, may, may_keep)
    view_low_keep([("the May exploration sample (May responses)", may),
                   ("the October r_ re-check sample", octo),
                   ("the October t_ sample", tcomb)], may_keep)
    rows = json.loads((HERE.parent / "explore" / "keep_rates.json").read_text())
    print(f"\n   May over the whole April grid ({len(rows)} combinations): under 0.10 "
          f"{sum(r['keep'] < 0.10 for r in rows)} ({sum(r['keep'] < 0.10 for r in rows if r['kind'] == 'r')} r_, "
          f"{sum(r['keep'] < 0.10 for r in rows if r['kind'] == 't')} t_), under 0.25 "
          f"{sum(r['keep'] < 0.25 for r in rows)} ({sum(r['keep'] < 0.25 for r in rows if r['kind'] == 'r')} r_, "
          f"{sum(r['keep'] < 0.25 for r in rows if r['kind'] == 't')} t_)")


if __name__ == "__main__":
    main()
