"""Cap pilot: the judge's view of a cut, paired per response (plan § 5 item 2; Roger, 2026-10-29).

The cap1024 responses cut at 256, 512 and 768 tokens (cut_responses.py) and judged
(cap_pilot_cut_judge.sh) are set against the same responses judged whole (the cap1024 tree's
scores).  A response shorter than the cut keeps its whole-response score, so an entity's keep share
at a cut is what a cap there would give it on the same responses.  Per entity type and cut: the cut
responses' keep-to-drop and drop-to-keep changes, the net change in keep share (score 3) over all of
an entity's responses, and an exact two-sided sign test on the changes (McNemar's).  For scale, the
judge's own rate of such changes on a second judging of the same responses (cap512's scores and
scores_rejudge, among its cut responses); and, as a check on the equivalence the method rests on,
cap512's own keep share beside cap1024's cut at 512 (different responses), with cap512 against
cap512b, two generations at the same cap, for the noise between trees.  Writes cut_readout.md here.

    uv run python reports/pipeline/cap_pilot/cut_readout.py [--root roger/cap_pilot]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ENTITIES = REPO / "reports" / "pipeline" / "cap_pilot_entities.json"
CUTS = (256, 512, 768)
TYPES = ("role", "trait")
LINK = {"role": "../../../data/roles/instructions/{}.json", "trait": "../../../data/traits/instructions/{}.json"}


def load(d: Path, name: str) -> dict | None:
    p = d / f"{name}.json"
    if not p.exists():
        return None
    return {k: v for k, v in json.loads(p.read_text()).items() if isinstance(v, int)}


def keep(scores: dict) -> float:
    return sum(v == 3 for v in scores.values()) / len(scores) if scores else float("nan")


def sign_test(b: int, c: int) -> float:
    """Exact two-sided binomial test of b against c (McNemar's, exact)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def flips(a: dict, b: dict, keys) -> tuple[int, int, int]:
    """(keep-to-drop, drop-to-keep, n) from a to b over the keys both have."""
    kd = dk = n = 0
    for k in keys:
        if k in a and k in b:
            n += 1
            kd += a[k] == 3 and b[k] != 3
            dk += a[k] != 3 and b[k] == 3
    return kd, dk, n


def cut_keys(responses: Path) -> set:
    """Keys of the responses step 1 cut at the cap (finish_reason "length")."""
    keys = set()
    if responses.exists():
        for line in responses.open():
            r = json.loads(line)
            if r.get("finish_reason") == "length":
                keys.add(f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}")
    return keys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=REPO / "roger" / "cap_pilot")
    ap.add_argument("--output", type=Path, default=HERE / "cut_readout.md")
    args = ap.parse_args()
    root = args.root
    by_type = json.loads(ENTITIES.read_text())["by_type"]

    out = ["# Cap pilot: the judge's view of a cut, paired per response", "",
           f"Written by [cut_readout.py](./cut_readout.py) from `roger/cap_pilot/` "
           f"([cap1024](../../../roger/cap_pilot/cap1024/), "
           + ", ".join(f"[cap1024_cut{n}](../../../roger/cap_pilot/cap1024_cut{n}/)" for n in CUTS)
           + "; plan § 5 item 2, [plan_max_tokens_pilot.md](../plan_max_tokens_pilot.md)).  "
           "The cap1024 responses cut at N tokens and judged with the cut marked, against the same "
           "responses judged whole; a response shorter than N keeps its whole score.  Keep is score 3.  "
           "*K→D* and *D→K*: cut responses whose verdict went from keep to drop, and from drop to keep, "
           "when the ending was cut.  *Δ*: the change in the entity's keep share over all its responses, "
           "in points.  *p*: exact two-sided sign test on K→D against D→K (McNemar's).", ""]

    for t in TYPES:
        names = by_type[t]
        whole = {n: load(root / "cap1024" / "judged" / "scores" / t, n) for n in names}
        cut = {c: {n: load(root / f"cap1024_cut{c}" / "judged" / "scores" / t, n) or {} for n in names}
               for c in CUTS}
        missing = [n for n in names if whole[n] is None]
        if missing:
            out += [f"## {t}s: not ready ({len(missing)} entities without whole scores)", ""]
            continue

        # judge noise: cap512 judged twice, among the responses cut at 512
        a_dir, b_dir = (root / "cap512" / "judged" / s / t for s in ("scores", "scores_rejudge"))
        nkd = ndk = nn = 0
        for n in names:
            a, b = load(a_dir, n), load(b_dir, n)
            if a and b:
                kd, dk, m = flips(a, b, cut_keys(root / "cap512" / "responses" / f"{n}.jsonl"))
                nkd, ndk, nn = nkd + kd, ndk + dk, nn + m
        noise = (nkd + ndk) / nn if nn else float("nan")

        out += [f"## {t.capitalize()}s ({len(names)})", "",
                f"Judge noise, for scale: cap512's cut responses judged twice change verdict "
                f"{noise:.1%} of the time ({nkd} K→D, {ndk} D→K of {nn}), about evenly both ways; "
                f"a cut's effect is the imbalance between K→D and D→K beyond that.", "",
                "| Cut | Cut responses | K→D | D→K | Changed | Keep, whole | **Keep, cut** | Δ (points) | p |",
                "|---|---|---|---|---|---|---|---|---|"]
        per_entity = {}
        for c in CUTS:
            tkd = tdk = tn = 0
            w_all = c_all = 0.0
            for n in names:
                w, x = whole[n], cut[c][n]
                kd, dk, m = flips(w, x, x.keys())
                tkd, tdk, tn = tkd + kd, tdk + dk, tn + m
                comp = {**w, **{k: v for k, v in x.items() if k in w}}
                per_entity[(n, c)] = (keep(comp) - keep(w), kd, dk, m)
                w_all += keep(w); c_all += keep(comp)
            w_all /= len(names); c_all /= len(names)
            out.append(f"| {c} | {tn:,} | {tkd} | {tdk} | {(tkd + tdk) / tn:.1%} | {w_all:.1%} | "
                       f"**{c_all:.1%}** | {100 * (c_all - w_all):+.1f} | {sign_test(tkd, tdk):.2g} |"
                       if tn else f"| {c} | not judged yet | | | | | | | |")
        out += ["", f"Per {t}, lowest whole keep share first: Δ in points at each cut, with "
                    "K→D / D→K among its cut responses.", "",
                "| " + t.capitalize() + " | Keep, whole | " + " | ".join(f"Δ at {c}" for c in CUTS) + " |",
                "|---|---|" + "---|" * len(CUTS)]
        for n in sorted(names, key=lambda n: keep(whole[n])):
            cells = []
            for c in CUTS:
                d, kd, dk, m = per_entity[(n, c)]
                has_cut = (root / f"cap1024_cut{c}" / "responses" / f"{n}.jsonl").exists()
                cells.append(f"{100 * d:+.1f} ({kd}/{dk})" if m else
                             "not judged yet" if has_cut else "no response that long")
            out.append(f"| [{n}]({LINK[t].format(n)}) | {keep(whole[n]):.0%} | " + " | ".join(cells) + " |")

        # the equivalence check, on the judge's side
        trees = {}
        for tree in ("cap512", "cap512b"):
            d = root / tree / "judged" / "scores" / t
            s = [keep(x) for x in (load(d, n) for n in names) if x]
            trees[tree] = sum(s) / len(s) if len(s) == len(names) else None
        comp512 = sum(keep({**whole[n], **{k: v for k, v in cut[512][n].items() if k in whole[n]}})
                      for n in names) / len(names)
        if None not in trees.values():
            out += ["", f"Equivalence check (different responses): cap512's own keep share "
                        f"{trees['cap512']:.1%}, cap1024 cut at 512 {comp512:.1%}; cap512 against "
                        f"cap512b, two generations at the same cap, {trees['cap512']:.1%} against "
                        f"{trees['cap512b']:.1%}."]
        out.append("")

    args.output.write_text("\n".join(out) + "\n")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
