"""Version 19 (version 17 with the third-person sentence) against version 17 on the trait side of the settled
pair (16 with 17; Roger, 2026-10-31: "16+17 on the basis of precision"; "Let's test this" on the sentence):

1. on the whole judged samples (the May exploration sample, the October r_ and t_ samples): how many responses
   the trait side flips each way, and the pair's keep under each;
2. on the second sheet's 162 marked October items: precision and recall of 16+17 and 16+19 at Roger's standard
   (estimate.py's weighting and transition), merged and readers-only, with the flipped items and their letters;
3. on the first sheet's 74 marked May items (candidates.py's adjusted letters, unweighted): the same.

The rule (no change without firm evidence): the sentence goes into the settled trait side only if the flipped
marked responses move toward the letters; neutral means version 17 stays.

    uv run python reports/pipeline/combination_rubric_review/reader_check_2/v19_check.py
"""
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "context_arms"))
sys.path.insert(0, str(HERE.parent / "reader_check"))
import compare  # noqa: E402
import candidates as C  # noqa: E402
import estimate as E  # noqa: E402
import tally  # noqa: E402

PAIRS = ("16 and 17", "16 and 19")
TCOMB = compare.REPO / "runpod_workspace" / "tcomb_recheck"


def pair_keeps(r: dict):
    if any(r[k] is None for k in ("V16", "V17", "V19")):
        return None
    return {"16 and 17": r["V16"] == 3 and r["V17"] == 3, "16 and 19": r["V16"] == 3 and r["V19"] == 3}


def flips(rows: list, label: str) -> None:
    rows = [r for r in rows if pair_keeps(r)]
    up = [r for r in rows if r["V17"] != 3 and r["V19"] == 3]
    down = [r for r in rows if r["V17"] == 3 and r["V19"] != 3]
    k17, k19 = mean(pair_keeps(r)["16 and 17"] for r in rows), mean(pair_keeps(r)["16 and 19"] for r in rows)
    print(f"   {label:34s} n {len(rows):5d}  trait side 17 -> 19: {len(up):3d} up, {len(down):3d} down; "
          f"pair keeps {k17:.3f} -> {k19:.3f}")
    by_trait = Counter(r["trait"] for r in up)
    if by_trait:
        print(f"   {'':34s} up by trait: " + ", ".join(f"{t} {n}" for t, n in by_trait.most_common(8)))


def main() -> None:
    may = compare.load_sample(compare.EXPLORE)
    octo = compare.load_sample(compare.RECHECK) + compare.load_sample(TCOMB)
    print("1. the whole samples")
    flips(may, "May exploration sample")
    flips([r for r in octo if r["kind"] == "r"], "October r_ sample")
    flips([r for r in octo if r["kind"] == "t"], "October t_ sample")

    # 2. the second sheet
    key = json.loads((HERE / "key.json").read_text())
    items, frame = key["items"], key["frame"]
    by_key = {(r["stem"], r["key"]): r for r in octo}
    readers = {}
    for s in range(1, 9):
        readers.update(tally.parse(HERE / f"sheet_{s}_marks.md"))
    roger = tally.parse(HERE / "roger_sheet_2.md", prefix="your ")
    for n, it in items.items():
        it["keep"] = pair_keeps(by_key[(it["stem"], it["key"])])
    items = {n: it for n, it in items.items() if it["keep"] is not None}
    E.CANDIDATES = PAIRS
    his = {n: it for n, it in items.items() if n in roger}
    trans = {"role": defaultdict(list), "trait": defaultdict(list)}
    for n in his:
        for side, idx in (("role", 0), ("trait", 1)):
            h, rl = E.letters_of(roger, n)[idx], readers.get(n, {}).get(side)
            if h is not None and rl and rl[0] in tally.WEIGHT:
                trans[side][rl[0]].append(h)

    def mapped(n, it):
        if n in his:
            return E.value(*E.merged(readers, roger, n, it), it)
        m = readers.get(n, {})
        ws = []
        for side in ("role", "trait"):
            L = (m.get(side) or (None,))[0]
            if L not in tally.WEIGHT:
                return None
            ws.append(mean(trans[side][L]) if trans[side].get(L) else tally.WEIGHT[L])
        return E.value(ws[0], ws[1], (m.get("ai") or (None,))[0], it)

    print("\n2. the second sheet's 162 October items")
    rng = random.Random(1)
    for title, fn in (("at Roger's standard (readers' letters mapped through his 30, his own kept)", mapped),
                      ("the readers' letters with Roger's overrides", lambda n, it: E.value(*E.merged(readers, roger, n, it), it)),
                      ("the readers' letters alone", lambda n, it: E.value(*E.letters_of(readers, n), it))):
        rows, _ = E.weighted_rows(items, frame, fn)
        boot = E.bootstrap(rows, 1000, rng) if title.startswith("at Roger") else None
        E.table(f"   {title}", rows, boot)
    rows, _ = E.weighted_rows(items, frame, mapped)
    flipped = [r for r in rows if r["keep"]["16 and 17"] != r["keep"]["16 and 19"]]
    print(f"\n   marked items the pair flips ({len(flipped)}): item, stem, direction, letters (role / trait, readers; "
          f"Roger's where he marked), value at Roger's standard")
    for r in sorted(flipped, key=lambda r: int(r["n"])):
        m, h = readers.get(r["n"], {}), roger.get(r["n"], {})
        direction = "17 drops, 19 keeps" if r["keep"]["16 and 19"] else "17 keeps, 19 drops"
        letters = f"{m.get('role', ('-',))[0]} / {m.get('trait', ('-',))[0]}"
        if h:
            letters += f"; Roger {h.get('role', ('-',))[0]} / {h.get('trait', ('-',))[0]}"
        print(f"     {r['n']:>3s} {r['stem']:40s} {direction:18s} {letters:28s} value {r['w']:.2f}")
    good_up = [r["w"] for r in flipped if r["keep"]["16 and 19"]]
    good_down = [r["w"] for r in flipped if not r["keep"]["16 and 19"]]
    if good_up:
        print(f"   19's extra keeps: {len(good_up)}, mean value {mean(good_up):.2f}")
    if good_down:
        print(f"   19's extra drops: {len(good_down)}, mean value {mean(good_down):.2f}")

    # 3. the first sheet
    print("\n3. the first sheet's 74 May items (adjusted letters, unweighted)")
    key1 = json.loads((HERE.parent / "reader_check" / "key.json").read_text())["items"]
    readers1 = {**tally.parse(HERE.parent / "reader_check" / "sheet_1_marks.md"),
                **tally.parse(HERE.parent / "reader_check" / "sheet_2_marks.md")}
    roger1 = tally.parse(HERE.parent / "reader_check" / "roger_sheet.md", prefix="your ")
    marks1 = C.adjusted_marks(key1, readers1, roger1)
    by_key1 = {(r["stem"], r["key"]): r for r in may}
    pairs, flipped1 = defaultdict(list), []
    for n, it in key1.items():
        w, row = C.both_weight(it, marks1[n]), by_key1.get((it["stem"], it["key"]))
        if w is None or row is None or pair_keeps(row) is None:
            continue
        k = pair_keeps(row)
        for p in PAIRS:
            pairs[p].append((w, k[p]))
        if k["16 and 17"] != k["16 and 19"]:
            flipped1.append((n, it["stem"], "17 drops, 19 keeps" if k["16 and 19"] else "17 keeps, 19 drops",
                             marks1[n].get("role", ("-",))[0], marks1[n].get("trait", ("-",))[0], w, n in roger1))
    for p in PAIRS:
        pr, rc = tally.prec_rec(pairs[p])
        print(f"   {p:10s} n {len(pairs[p])}  keeps {mean(k for _, k in pairs[p]):.2f}  precision {pr:.2f}  recall {rc:.2f}")
    print(f"   flipped ({len(flipped1)}):")
    for f in flipped1:
        print(f"     {f[0]:>3s} {f[1]:40s} {f[2]:18s} {f[3]} / {f[4]}{' (Roger)' if f[6] else ''}  value {f[5]:.2f}")


if __name__ == "__main__":
    main()
