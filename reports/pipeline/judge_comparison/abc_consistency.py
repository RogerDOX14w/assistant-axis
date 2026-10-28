"""A/B/C-against-score consistency of the role rubric's decision-procedure replies (versions 6 and 7; Roger,
2026-10-28).  Each reply answers A (refuses as itself), B (AI self-identification or the model's disclaimers) and
C (any roleplay) yes or no and then states a score; the rubric's table makes the score a function of the answers
(0 if A and not C, 1 if neither, 2 if C and A or B, 3 if C alone).  For every saved reply of gpt-4.1-mini and
gpt-5.6-luna (v6 twice, v7 once; the October and May sets) this reports:

* how often the stated score differs from the score the answers imply, by judge, run and answer pattern, and
  how often the difference crosses the keep line (3 against below 3);
* whether the mismatches are random or concentrated on borderline responses: the mismatch rate where the other
  v6 replies to the same response (the judge's other run and both runs of the other judge) agree on keep or drop,
  against where they split; and among reader-marked responses, T against G or B;
* where a mismatch crosses the keep line, which reading is right: the stated score, the implied score, or a
  rejudge, using the judge's other v6 run as a stand-in for a fresh call, scored against the other judge's two
  runs when they agree and against the reader marks;
* the roles the mismatches fall on.

    uv run python reports/pipeline/judge_comparison/abc_consistency.py --out reports/pipeline/judge_comparison/abc_consistency.json
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from results_analysis import judge_comparison as jc  # noqa: E402

R = Path("runpod_workspace/rubric_exp/judges")
JUDGES = ("gpt-4.1-mini", "gpt-5.6-luna")
RUNS = ("v6", "v6_rerun", "v7")
SETS = ("oct", "may")
ANSWER = re.compile(r"^\W*([ABC])\W*\s*[:.\)\-–—]?\s*\**\s*(yes|no)\b", re.I)
#: A later line that answers the same question again ("Re-examining B ... So B: no").
RESTATED = re.compile(r"\b(?:so|thus|therefore|hence)\s*,?\s*([ABC])\s*:?\s*(?:is\s+)?(yes|no)\b", re.I)


def implied(a: bool, b: bool, c: bool) -> int:
    return (2 if (a or b) else 3) if c else (0 if a else 1)


def parse(reply: str):
    """``(answers, restated)``: the first yes / no given for each of A, B and C, and whether the reply answers
    one of them again later with a different word."""
    ans, again = {}, False
    for line in reply.splitlines():
        m = ANSWER.match(line)
        if m and m.group(1).upper() not in ans:
            ans[m.group(1).upper()] = m.group(2).lower() == "yes"
        for q, word in RESTATED.findall(line):
            if q.upper() in ans and ans[q.upper()] != (word.lower() == "yes"):
                again = True
    return ans, again


def load_replies() -> dict:
    """``{(judge, run, set): {(entity, key): (score, answers, restated)}}`` for every saved reply."""
    out = {}
    for j in JUDGES:
        for run in RUNS:
            for s in SETS:
                d = R / j / s / run / "_replies"
                if not d.is_dir():
                    continue
                cell = {}
                for f in sorted(d.glob("*.jsonl")):
                    for line in f.read_text().splitlines():
                        if line.strip():
                            x = json.loads(line)
                            ans, again = parse(x["reply"])
                            cell[(f.stem, x["key"])] = (x["score"], ans, again)
                out[(j, run, s)] = cell
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    rep = load_replies()
    items, _ = jc.reader_items()
    marks = {(it["set"], it["entity"], it["key"]): it["mark"] for it in items if it["set"] in SETS}
    v6dir = Path("reports/pipeline/judge_comparison/reader_check_v6")
    roger = json.loads((v6dir / "roger_marks.json").read_text())
    key6 = json.loads((v6dir / "key.json").read_text())["items"]
    for i, r in roger["v6_items"].items():
        marks[(key6[i]["set"], key6[i]["entity"], key6[i]["key"])] = r["mark"][:1]
    for k, r in roger["refusal_items"].items():
        if k != "note":
            s_e, key = k.split()
            s, e = s_e.split("/")
            marks[(s, e, key)] = r["mark"]
    res = {"cells": {}, "patterns": {}, "borderline": {}, "crossing": {}, "roles": {}}

    print("== stated score against the score the A/B/C answers imply")
    mism = {}   # (judge, run, set, entity, key) -> (stated, implied, pattern)
    for (j, run, s), cell in sorted(rep.items()):
        n = bad = crossing = restated = 0
        pats = Counter()
        for (e, k), (score, ans, again) in cell.items():
            if len(ans) < 3 or score is None:
                bad += 1
                continue
            n += 1
            imp = implied(ans["A"], ans["B"], ans["C"])
            if imp != score:
                pat = "".join(f"{q}{'y' if ans[q] else 'n'}" for q in "ABC")
                pats[(pat, imp, score)] += 1
                restated += again
                crossing += (imp == 3) != (score == 3)
                mism[(j, run, s, e, k)] = (score, imp, pat)
        m = sum(pats.values())
        res["cells"][f"{j}|{run}|{s}"] = {"n": n, "unanswered": bad, "mismatch": m, "crossing": crossing,
                                           "restated": restated}
        res["patterns"][f"{j}|{run}|{s}"] = {f"{p} implies {i}, stated {st}": c for (p, i, st), c in pats.items()}
        print(f"  {j:13s} {run:9s} {s}: {m:3d} of {n} ({100 * m / n:.2f}%), {crossing} across the keep line, "
              f"{restated} with an answer restated later; {bad} without three answers")
        for (p, i, st), c in pats.most_common(4):
            print(f"      {p}: implies {i}, stated {st}: {c}")

    # Borderline: the other v6 replies to the same response (excluding the reply itself).
    print("\n== mismatch rate by whether the other v6 replies to the response agree on keep / drop")
    for j in JUDGES:
        for run in ("v6", "v6_rerun"):
            other_run = "v6_rerun" if run == "v6" else "v6"
            oj = JUDGES[1 - JUDGES.index(j)]
            tally = defaultdict(lambda: [0, 0])   # agree / split -> [mismatches, replies]
            for s in SETS:
                for (e, k), (score, ans, _) in rep[(j, run, s)].items():
                    if len(ans) < 3 or score is None:
                        continue
                    others = [rep[c].get((e, k)) for c in ((j, other_run, s), (oj, "v6", s), (oj, "v6_rerun", s))]
                    keeps = [o[0] == 3 for o in others if o and o[0] is not None]
                    if len(keeps) < 3:
                        continue
                    g = "others agree" if len(set(keeps)) == 1 else "others split"
                    tally[g][1] += 1
                    tally[g][0] += (j, run, s, e, k) in mism
            line = "; ".join(f"{g}: {m} of {n} ({100 * m / n:.2f}%)" for g, (m, n) in sorted(tally.items()))
            res["borderline"][f"{j}|{run}"] = {g: {"mismatch": m, "n": n} for g, (m, n) in tally.items()}
            print(f"  {j:13s} {run:9s} {line}")
    mt = defaultdict(lambda: [0, 0])
    for (s, e, k), mark in marks.items():
        for j in JUDGES:
            for run in RUNS:
                x = rep.get((j, run, s), {}).get((e, k))
                if x and len(x[1]) == 3 and x[0] is not None:
                    g = "T" if mark == "T" else ("G or B" if mark in "GB" else "other")
                    mt[g][1] += 1
                    mt[g][0] += (j, run, s, e, k) in mism
    res["borderline"]["reader_marks"] = {g: {"mismatch": m, "n": n} for g, (m, n) in mt.items()}
    print("  reader-marked responses: " + "; ".join(f"{g}: {m} of {n} ({100 * m / n:.2f}%)"
                                                   for g, (m, n) in sorted(mt.items())))

    # Mismatches that cross the keep line: stated, implied or rejudged, against references.
    print("\n== mismatches across the keep line: which reading is right")
    for j in JUDGES:
        oj = JUDGES[1 - JUDGES.index(j)]
        score_ref = Counter()
        score_mark = Counter()
        rejudge = Counter()
        for (jj, run, s, e, k), (stated, imp, pat) in mism.items():
            if jj != j or (stated == 3) == (imp == 3):
                continue
            o = [rep.get((oj, r, s), {}).get((e, k)) for r in ("v6", "v6_rerun")]
            o = [x[0] == 3 for x in o if x and x[0] is not None]
            ref = o[0] if len(o) == 2 and o[0] == o[1] else None
            if run in ("v6", "v6_rerun"):
                other = rep[(j, "v6_rerun" if run == "v6" else "v6", s)].get((e, k))
                if other:
                    o_ans = other[1]
                    consistent = len(o_ans) == 3 and implied(o_ans["A"], o_ans["B"], o_ans["C"]) == other[0]
                    rejudge["rejudge consistent" if consistent else "rejudge inconsistent too"] += 1
                    if ref is not None:
                        rejudge[f"rejudge agrees with the other judge: {(other[0] == 3) == ref}"] += 1
            if ref is not None:
                score_ref[f"stated agrees with the other judge: {(stated == 3) == ref}"] += 1
                score_ref[f"implied agrees with the other judge: {(imp == 3) == ref}"] += 1
            else:
                score_ref["the other judge's runs split or missing"] += 1
            mark = marks.get((s, e, k))
            if mark in ("G", "B"):
                good = mark == "G"
                score_mark[f"stated right: {(stated == 3) == good}"] += 1
                score_mark[f"implied right: {(imp == 3) == good}"] += 1
        res["crossing"][j] = {"against_other_judge": dict(score_ref), "against_marks": dict(score_mark),
                              "rejudge": dict(rejudge)}
        print(f"  {j}: " + json.dumps({"other judge": dict(sorted(score_ref.items())),
                                      "reader marks": dict(sorted(score_mark.items())),
                                      "rejudge": dict(sorted(rejudge.items()))}))

    print("\n== roles with the most mismatches (all runs)")
    for j in JUDGES:
        roles = Counter(f"{s}/{e}" for (jj, _, s, e, _), _ in mism.items() if jj == j)
        res["roles"][j] = dict(roles.most_common())
        print(f"  {j}: " + ", ".join(f"{r} {n}" for r, n in roles.most_common(12)))
    if args.out:
        args.out.write_text(json.dumps(res, indent=1) + "\n")
        print("\nwrote", args.out)


if __name__ == "__main__":
    main()
