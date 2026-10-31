"""Precision and recall of the three candidate "both" rules (draft 14; the context sides 16 with 17; 16 with 18)
against the second reading sheet's letters (build.py: a stratified random draw from the judged October samples),
weighted back to the samples by cell (kind x keep level x the candidates' pattern; key.json carries each cell's
frame count), so that the figures are estimates for the judged October data and its slices, with stratified
bootstrap intervals.

The letters are probabilities (G 1, G/T .75, T .5, T/B .25, B 0); a response's "both" value is the role letter's
weight times the trait letter's, times 0 when an ai mark other than n stands against a role that is not an AI
role.  Roger's letters override the readers' where he wrote one (a "?" leaves theirs); the readers-only and
Roger-only figures are given too, with the two compared on his items as the calibration.  Precision is the
good share of what a candidate keeps, recall the share of the good it keeps; "role missing" and "trait
missing" among the kept are the mean deficits 1 - role weight and 1 - trait weight on kept responses, which say
which side a candidate's precision loses to.  Roger's letters come from both his sheets: roger_sheet_2.md (30
items of his own draw) and roger_sheet_3.md (six of the readers' items chosen for the criteria questions they
raised, marked 2026-10-31).

    uv run python reports/pipeline/combination_rubric_review/reader_check_2/estimate.py [--reps 2000] [--seed 1]

Writes estimate.json beside the sheets; the text goes to stdout (kept in estimate_output.txt by the caller).
"""
import argparse
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reader_check"))
import tally  # noqa: E402

CANDIDATES = ("draft 14", "16 and 17", "16 and 18")
KINDS = {"r": "r_", "t": "t_"}
LEVELS = ("low", "medium", "high")
PATTERNS = ("all keep", "mixed", "all drop")


def cell_of(it: dict) -> str:
    return f"{it['kind']} | {it['level']} | {it['pattern']}"


def letters_of(marks: dict, n: str):
    """(role weight, trait weight, ai ok) from one marks dict, None where a letter is missing or '?'."""
    m = marks.get(n, {})
    wr = tally.WEIGHT.get((m.get("role") or (None,))[0])
    wt = tally.WEIGHT.get((m.get("trait") or (None,))[0])
    ai = m.get("ai")
    return wr, wt, (ai[0] if ai else None)


def merged(readers: dict, roger: dict, n: str, it: dict):
    """The readers' letters with Roger's in place where he wrote one that carries a weight."""
    wr, wt, ai = letters_of(readers, n)
    rr, rt, rai = letters_of(roger, n)
    wr = rr if rr is not None else wr
    wt = rt if rt is not None else wt
    ai = rai if rai is not None else ai
    return wr, wt, ai


def value(wr, wt, ai, it):
    if wr is None or wt is None:
        return None
    ai_ok = ai is None or ai.startswith("n") or it["role"] in tally.AI_ROLES
    return wr * wt * (1.0 if ai_ok else 0.0), wr, wt


def estimate(rows: list, cand: str) -> dict:
    """``rows``: dicts with W (cell weight), w (both value), wr, wt and keep[cand]."""
    tot = sum(r["W"] for r in rows)
    kept = [r for r in rows if r["keep"][cand]]
    k_mass = sum(r["W"] for r in kept)
    good_kept = sum(r["W"] * r["w"] for r in kept)
    good = sum(r["W"] * r["w"] for r in rows)
    return {"n": len(rows), "n_kept": len(kept), "keep": k_mass / tot if tot else float("nan"),
            "expected": good / tot if tot else float("nan"),
            "precision": good_kept / k_mass if k_mass else float("nan"),
            "recall": good_kept / good if good else float("nan"),
            "role_missing": sum(r["W"] * (1 - r["wr"]) for r in kept) / k_mass if k_mass else float("nan"),
            "trait_missing": sum(r["W"] * (1 - r["wt"]) for r in kept) / k_mass if k_mass else float("nan")}


def slices(rows: list) -> list:
    out = [("all", rows)]
    out += [(KINDS[k], [r for r in rows if r["kind"] == k]) for k in "rt"]
    out += [(f"{lv} keep", [r for r in rows if r["level"] == lv]) for lv in LEVELS]
    out += [(f"{KINDS[k]} {lv}", [r for r in rows if r["kind"] == k and r["level"] == lv]) for k in "rt" for lv in LEVELS]
    out += [("r_ not predator", [r for r in rows if r["kind"] == "r" and r["role"] != "predator"]),
            ("t_ not chef", [r for r in rows if r["kind"] == "t" and r["role"] != "chef"])]
    out += [(f"{KINDS[k]} {p}", [r for r in rows if r["kind"] == k and r["pattern"] == p]) for k in "rt" for p in PATTERNS]
    return out


def weighted_rows(items: dict, frame: dict, marks_fn) -> tuple:
    """Rows with letters, weighted so that each cell's rows sum to the cell's frame count; and the items left out."""
    usable, left = [], []
    for n, it in items.items():
        v = marks_fn(n, it)
        if v is None:
            left.append(n)
            continue
        w, wr, wt = v
        usable.append({**it, "n": n, "w": w, "wr": wr, "wt": wt, "cell": cell_of(it)})
    per_cell = Counter(r["cell"] for r in usable)
    for r in usable:
        r["W"] = frame[r["cell"]] / per_cell[r["cell"]]
    return usable, left


def bootstrap(rows: list, reps: int, rng: random.Random) -> dict:
    """Stratified (by cell) bootstrap of precision and recall per slice and candidate, and of the r_ - t_
    precision and recall differences; returns {slice: {cand: {"precision": [...], "recall": [...]}}}."""
    by_cell = defaultdict(list)
    for r in rows:
        by_cell[r["cell"]].append(r)
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for _ in range(reps):
        sample = []
        for cell, rs in by_cell.items():
            sample += [rng.choice(rs) for _ in rs]
        for name, sel in slices(sample):
            for cand in CANDIDATES:
                e = estimate(sel, cand)
                out[name][cand]["precision"].append(e["precision"])
                out[name][cand]["recall"].append(e["recall"])
        for cand in CANDIDATES:
            er, et = estimate([r for r in sample if r["kind"] == "r"], cand), estimate([r for r in sample if r["kind"] == "t"], cand)
            out["r_ minus t_"][cand]["precision"].append(er["precision"] - et["precision"])
            out["r_ minus t_"][cand]["recall"].append(er["recall"] - et["recall"])
    return out


def ci(vals: list, lo=2.5, hi=97.5) -> tuple:
    vs = sorted(v for v in vals if v == v)
    if not vs:
        return float("nan"), float("nan")
    return vs[int(len(vs) * lo / 100)], vs[min(len(vs) - 1, int(len(vs) * hi / 100))]


def table(title: str, rows: list, boot: dict | None) -> dict:
    print(f"\n{title}")
    print(f"   {'slice':16s} {'n':>3s} {'expect':>6s}  " + "  ".join(f"{c:>38s}" for c in CANDIDATES))
    print(f"   {'':16s} {'':3s} {'':6s}  " + "  ".join(f"{'keep   precision [95% CI]   recall [95% CI]':>38s}" for _ in CANDIDATES))
    res = {}
    for name, sel in slices(rows):
        if not sel:
            continue
        parts, res[name] = [], {}
        for cand in CANDIDATES:
            e = estimate(sel, cand)
            res[name][cand] = e
            if boot is not None:
                pl, ph = ci(boot[name][cand]["precision"]); rl, rh = ci(boot[name][cand]["recall"])
                e["precision_ci"], e["recall_ci"] = (pl, ph), (rl, rh)
                parts.append(f"{e['keep']:4.2f}  {e['precision']:4.2f} [{pl:.2f} {ph:.2f}]  {e['recall']:4.2f} [{rl:.2f} {rh:.2f}]")
            else:
                parts.append(f"{e['keep']:4.2f}  {e['precision']:4.2f}              {e['recall']:4.2f}            ")
        print(f"   {name:16s} {len(sel):3d} {estimate(sel, CANDIDATES[0])['expected']:6.2f}  " + "  ".join(f"{p:>38s}" for p in parts))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    key = json.loads((HERE / "key.json").read_text())
    items, frame = key["items"], key["frame"]
    readers = {}
    for s in range(1, 9):
        readers.update(tally.parse(HERE / f"sheet_{s}_marks.md"))
    roger, on_sheets = {}, 0
    for sheet in ("roger_sheet_2.md", "roger_sheet_3.md"):
        marks = tally.parse(HERE / sheet, prefix="your ")
        on_sheets += len(re.findall(r"^### \d+$", (HERE / sheet).read_text(), re.M)) if (HERE / sheet).exists() else 0
        roger.update(marks)
    n_roger = sum(1 for n in roger if letters_of(roger, n)[0] is not None or letters_of(roger, n)[1] is not None)
    print(f"{len(items)} items; readers' marks on {sum(n in readers for n in items)}; Roger's letters on {n_roger} "
          f"of the {on_sheets} on his two sheets")
    print("frame (responses per cell): " + ", ".join(f"{c} {n}" for c, n in frame.items()))

    rows, left = weighted_rows(items, frame, lambda n, it: value(*merged(readers, roger, n, it), it))
    if left:
        print(f"left out (no letter on a side, or '?'): {', '.join(left)}")
    if not rows:
        print("no usable marks yet")
        return
    rng = random.Random(a.seed)
    boot = bootstrap(rows, a.reps, rng) if a.reps else None
    out = {"n_items": len(items), "n_used": len(rows), "left_out": left}
    out["merged"] = table("1. the readers' letters with Roger's overrides, weighted to the October samples", rows, boot)
    if boot is not None:
        print("\n   r_ minus t_ (95% CI):")
        for cand in CANDIDATES:
            pl, ph = ci(boot["r_ minus t_"][cand]["precision"]); rl, rh = ci(boot["r_ minus t_"][cand]["recall"])
            er, et = out["merged"]["r_"][cand], out["merged"]["t_"][cand]
            print(f"     {cand:10s} precision {er['precision'] - et['precision']:+.2f} [{pl:+.2f} {ph:+.2f}]   "
                  f"recall {er['recall'] - et['recall']:+.2f} [{rl:+.2f} {rh:+.2f}]")
            out["merged"]["r_ minus t_"] = out["merged"].get("r_ minus t_", {})
            out["merged"]["r_ minus t_"][cand] = {"precision": er["precision"] - et["precision"], "precision_ci": (pl, ph),
                                                  "recall": er["recall"] - et["recall"], "recall_ci": (rl, rh)}

    print("\n2. which side the kept responses lack (mean deficit among the kept: 1 - role weight, 1 - trait weight)")
    print(f"   {'slice':16s}  " + "  ".join(f"{c:>22s}" for c in CANDIDATES))
    print(f"   {'':16s}  " + "  ".join(f"{'role miss  trait miss':>22s}" for _ in CANDIDATES))
    for name in ("all", "r_", "t_", "r_ not predator", "t_ not chef", "r_ mixed", "t_ mixed", "r_ all keep", "t_ all keep"):
        e = out["merged"].get(name)
        if e:
            print(f"   {name:16s}  " + "  ".join(f"{e[c]['role_missing']:9.2f}  {e[c]['trait_missing']:10.2f}" for c in CANDIDATES))

    # readers only, and Roger only on his items
    rows_r, _ = weighted_rows(items, frame, lambda n, it: value(*letters_of(readers, n), it))
    out["readers_only"] = table("3. the readers' letters alone, same weighting", rows_r, None)
    his = {n: it for n, it in items.items() if n in roger}
    rows_h, left_h = weighted_rows(his, frame, lambda n, it: value(*letters_of(roger, n), it))
    if rows_h:
        out["roger_only"] = table(f"4. Roger's letters alone, his {len(rows_h)} items, weighted the same way (wide intervals: "
                                  "read for direction)", rows_h, None)
        # calibration: his letters against the readers' on the same items
        print("\n5. calibration on Roger's items: his letters against the readers'")
        cal = {}
        for side, idx in (("role", 0), ("trait", 1)):
            pairs = []
            for n in his:
                h, r = letters_of(roger, n)[idx], letters_of(readers, n)[idx]
                if h is not None and r is not None:
                    pairs.append((h, r))
            if not pairs:
                continue
            agree =mean((h >= .75) == (r >= .75) for h, r in pairs if h != .5 and r != .5) if any(h != .5 and r != .5 for h, r in pairs) else float("nan")
            print(f"   {side:5s} n {len(pairs):2d}: Roger's mean weight {mean(h for h, _ in pairs):.2f}, readers' {mean(r for _, r in pairs):.2f}; "
                  f"yes/no agreement (T left out) {agree:.2f}; Roger higher on {sum(h > r for h, r in pairs)}, lower on {sum(h < r for h, r in pairs)}")
            cal[side] = {"n": len(pairs), "roger_mean": mean(h for h, _ in pairs), "readers_mean": mean(r for _, r in pairs),
                         "agree": agree, "roger_higher": sum(h > r for h, r in pairs), "roger_lower": sum(h < r for h, r in pairs)}
        out["calibration"] = cal
        both_pairs = []
        for n, it in his.items():
            vh, vr = value(*letters_of(roger, n), it), value(*letters_of(readers, n), it)
            if vh and vr:
                both_pairs.append((vh[0], vr[0]))
        if both_pairs:
            print(f"   both  n {len(both_pairs):2d}: Roger's expected keep {mean(h for h, _ in both_pairs):.2f}, readers' "
                  f"{mean(r for _, r in both_pairs):.2f}")
        # 6. the readers' letters mapped to Roger's standard: on the items he did not mark, each reader letter is
        # replaced by the mean weight he gave where the readers wrote that letter on his items (a letter he never
        # met keeps its own weight); his items keep his letters.  A population estimate at his standard, resting on
        # the 30-item transition.
        # The transition is fitted on his random draw only (roger_sheet_2.md, key.json's on_roger_sheet): the six
        # items of roger_sheet_3.md were chosen because the readers reported them as unsettled by the criteria,
        # so his letters there say how contested letters resolve, not how the readers' letters read on average;
        # they override their own items (above) and stay out of the calibration.
        trans = {"role": defaultdict(list), "trait": defaultdict(list)}
        n_trans = 0
        for n in his:
            if not items[n].get("on_roger_sheet"):
                continue
            n_trans += 1
            for side, idx in (("role", 0), ("trait", 1)):
                h, rl = letters_of(roger, n)[idx], readers.get(n, {}).get(side)
                if h is not None and rl and rl[0] in tally.WEIGHT:
                    trans[side][rl[0]].append(h)
        print(f"\n6. the readers' letters mapped to Roger's standard (transition from the {n_trans} items of his random "
              f"draw: readers' letter -> his mean weight, n; his {len(his) - n_trans} items chosen on contested "
              f"questions override their own letters only)")
        for side in ("role", "trait"):
            print(f"   {side:5s} " + "  ".join(f"{L}: {mean(v):.2f} ({len(v)})" for L, v in sorted(trans[side].items(), key=lambda kv: -tally.WEIGHT[kv[0]])))
        out["transition"] = {side: {L: {"mean": mean(v), "n": len(v)} for L, v in trans[side].items()} for side in trans}

        def mapped(n, it):
            if n in his:
                return value(*merged(readers, roger, n, it), it)
            m = readers.get(n, {})
            ws = []
            for side in ("role", "trait"):
                L = (m.get(side) or (None,))[0]
                if L not in tally.WEIGHT:
                    return None
                ws.append(mean(trans[side][L]) if trans[side].get(L) else tally.WEIGHT[L])
            ai = (m.get("ai") or (None,))[0]
            return value(ws[0], ws[1], ai, it)
        rows_m, _ = weighted_rows(items, frame, mapped)
        boot_m = bootstrap(rows_m, a.reps, rng) if a.reps else None
        out["roger_standard"] = table("   estimates at Roger's standard, weighted to the October samples", rows_m, boot_m)
        if boot_m is not None:
            print("\n   r_ minus t_ at Roger's standard (95% CI):")
            for cand in CANDIDATES:
                pl, ph = ci(boot_m["r_ minus t_"][cand]["precision"]); rl, rh = ci(boot_m["r_ minus t_"][cand]["recall"])
                er, et = out["roger_standard"]["r_"][cand], out["roger_standard"]["t_"][cand]
                print(f"     {cand:10s} precision {er['precision'] - et['precision']:+.2f} [{pl:+.2f} {ph:+.2f}]   "
                      f"recall {er['recall'] - et['recall']:+.2f} [{rl:+.2f} {rh:+.2f}]")
    (HERE / "estimate.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
