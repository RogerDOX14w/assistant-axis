"""A/B/C-against-score consistency of the role rubric's decision-procedure replies (versions 6 to 8; Roger,
2026-10-27 and 2026-10-28).  Each reply answers A (refuses as itself), B (AI self-identification or the model's
disclaimers) and C (any roleplay) yes or no and then states a score; the rubric's table makes the score a function
of the answers (0 if A and not C, 1 if neither, 2 if C and A or B, 3 if C alone).  For every saved reply of
gpt-4.1-mini and gpt-5.6-luna (v6 twice, v7 once; the October and May sets) this reports:

* how often the stated score differs from the score the answers imply, by judge, run and answer pattern, and
  how often the difference crosses the keep line (3 against below 3);
* whether the mismatches are random or concentrated on borderline responses: the mismatch rate where the other
  v6 replies to the same response (the judge's other run and both runs of the other judge) agree on keep or drop,
  against where they split; and among reader-marked responses, T against G or B;
* where a mismatch crosses the keep line, which reading is right: the stated score, the implied score, or a
  rejudge, using the judge's other v6 run as a stand-in for a fresh call, scored against the other judge's two
  runs when they agree and against the reader marks;
* the roles the mismatches fall on.

Then the same for version 8, the version kept (2026-10-28), on gpt-5.6-luna, gpt-4.1-mini and Claude Haiku 5.5,
each judge's reference being the other two when they agree on keep or drop; and, for gpt-5.6-luna, what a step-3
check that rejudges a mismatched reply would do, from three fresh v8 calls on each of its mismatched responses
(``--write_rejudge_responses`` writes those responses for step 3; the calls go to
``judges/gpt-5.6-luna/<set>/v8_abc_rejudge_<n>``).  Marks: Roger's (the v6 sheet, the refusals shown in chat,
roger_sheet.md to roger_sheet_3.md), then the blind readers' (the v6 and v7 sheets), then the earlier checks'.

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
V6_DIR = Path("reports/pipeline/judge_comparison/reader_check_v6")
V7_DIR = Path("reports/pipeline/judge_comparison/reader_check_v7")
RESPONSES = {"oct": Path("runpod_workspace/rubric_exp/responses"),
             "may": Path("runpod_workspace/rubric_exp/may_target/responses")}
V8_JUDGES = ("gpt-5.6-luna", "gpt-4.1-mini", "claude-haiku-5-5")
LUNA = "gpt-5.6-luna"
REJUDGES = ("v8_abc_rejudge_1", "v8_abc_rejudge_2", "v8_abc_rejudge_3")
ANSWER = re.compile(r"^\W*([ABC])\W*\s*[:.\)\-–—]?\s*\**\s*(yes|no)\b", re.I)
#: A later line that answers the same question again ("Re-examining B ... So B: no").
RESTATED = re.compile(r"\b(?:so|thus|therefore|hence)\s*,?\s*([ABC])\s*:?\s*(?:is\s+)?(yes|no)\b", re.I)


def implied(a: bool, b: bool, c: bool) -> int:
    return (2 if (a or b) else 3) if c else (0 if a else 1)


def parse(reply: str):
    """``(answers, restated)``: the first yes / no given for each of A, B and C, and whether the reply answers
    one of them again later with a different word.  A reply with no text (a refusal) answers nothing."""
    ans, again = {}, False
    for line in (reply or "").splitlines():
        m = ANSWER.match(line)
        if m and m.group(1).upper() not in ans:
            ans[m.group(1).upper()] = m.group(2).lower() == "yes"
        for q, word in RESTATED.findall(line):
            if q.upper() in ans and ans[q.upper()] != (word.lower() == "yes"):
                again = True
    return ans, again


def consistent(x) -> bool:
    """Whether a loaded reply ``(score, answers, restated)`` states the score its answers imply."""
    return x is not None and len(x[1]) == 3 and x[0] is not None and implied(x[1]["A"], x[1]["B"], x[1]["C"]) == x[0]


def load_replies(judges=JUDGES, runs=RUNS) -> dict:
    """``{(judge, run, set): {(entity, key): (score, answers, restated)}}`` for every saved reply."""
    out = {}
    for j in judges:
        for run in runs:
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


def sheet_marks(d: Path) -> dict:
    """``{item: mark}`` from a reader directory's sheet_*.md, read as reader_check_v7/tally.py reads them."""
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


def load_marks() -> dict:
    """``{(set, entity, key): mark}`` with marks G / B / T / ? ("G/T" counts as T), one per response: Roger's
    first, then the blind readers' (a v7 re-mark of a v6 item is skipped), then the earlier checks'."""
    k6 = json.loads((V6_DIR / "key.json").read_text())["items"]
    k7 = json.loads((V7_DIR / "key.json").read_text())["items"]
    k8 = json.loads((V7_DIR / "key_v8.json").read_text())["items"]
    marks = {}

    def add(it, mark):
        mark = "T" if mark.upper() == "G/T" else mark[:1].upper()
        if mark and mark in "GBT?":
            marks.setdefault((it["set"], it["entity"], it["key"]), mark)

    roger6 = json.loads((V6_DIR / "roger_marks.json").read_text())
    for k, r in json.loads((V7_DIR / "roger_marks.json").read_text())["items"].items():
        src, i = k.split("/")
        add({"v6": k6, "v7": k7, "v8": k8}[src][i], r["mark"])
    for i, r in roger6["v6_items"].items():
        add(k6[i], r["mark"])
    for k, r in roger6["refusal_items"].items():
        if k != "note":
            s_e, key = k.split()
            s, e = s_e.split("/")
            add({"set": s, "entity": e, "key": key}, r["mark"])
    for d, k in ((V6_DIR, k6), (V7_DIR, k7)):
        for i, mark in sheet_marks(d).items():
            if k[i].get("stratum") != "remark":
                add(k[i], mark)
    for it in jc.reader_items()[0]:
        if it["set"] in SETS:
            add(it, it["mark"])
    return marks


def mismatches(rep: dict, cells, res: dict) -> dict:
    """Count and print stated-against-implied mismatches in ``cells`` (``(judge, run, set)``); return
    ``{(judge, run, set, entity, key): (stated, implied, pattern)}``."""
    mism = {}
    for c in cells:
        if c not in rep:
            continue
        j, run, s = c
        n = bad = crossing = restated = 0
        pats = Counter()
        for (e, k), (score, ans, again) in rep[c].items():
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
        print(f"  {j:16s} {run:9s} {s}: {m:3d} of {n} ({100 * m / n:.2f}%), {crossing} across the keep line, "
              f"{restated} with an answer restated later; {bad} without three answers")
        for (p, i, st), c in pats.most_common(4):
            print(f"      {p}: implies {i}, stated {st}: {c}")
    return mism


def rate(m: int, n: int) -> str:
    return f"{m} of {n} ({100 * m / n:.2f}%)" if n else "0 of 0"


def v8_section(marks: dict, res: dict) -> None:
    rep = load_replies(V8_JUDGES, ("v8",) + REJUDGES)
    out = res["v8"] = {"cells": {}, "patterns": {}, "borderline": {}, "crossing": {}, "roles": {}, "rejudge": {}}
    print("\n== version 8: stated score against the score the A/B/C answers imply")
    mism = mismatches(rep, [(j, "v8", s) for j in V8_JUDGES for s in SETS], out)

    def keep(j, s, e, k):
        x = rep.get((j, "v8", s), {}).get((e, k))
        return None if x is None or x[0] is None else x[0] == 3

    def reference(j, s, e, k):
        """The other two v8 judges' keep decision when they agree, else None."""
        o = [keep(oj, s, e, k) for oj in V8_JUDGES if oj != j]
        return o[0] if None not in o and o[0] == o[1] else None

    print("\n== version 8: mismatch rate by whether the other two judges agree on keep / drop, and by reader mark")
    for j in V8_JUDGES:
        tally = defaultdict(lambda: [0, 0])
        mt = defaultdict(lambda: [0, 0])
        for s in SETS:
            for (e, k), (score, ans, _) in rep[(j, "v8", s)].items():
                if len(ans) < 3 or score is None:
                    continue
                o = [keep(oj, s, e, k) for oj in V8_JUDGES if oj != j]
                if None not in o:
                    g = "others agree" if o[0] == o[1] else "others split"
                    tally[g][1] += 1
                    tally[g][0] += (j, "v8", s, e, k) in mism
                mark = marks.get((s, e, k))
                if mark:
                    g = "T" if mark == "T" else ("G or B" if mark in "GB" else "?")
                    mt[g][1] += 1
                    mt[g][0] += (j, "v8", s, e, k) in mism
        out["borderline"][j] = {"others": {g: {"mismatch": m, "n": n} for g, (m, n) in tally.items()},
                                "reader_marks": {g: {"mismatch": m, "n": n} for g, (m, n) in mt.items()}}
        print(f"  {j:16s} " + "; ".join(f"{g}: {rate(*v)}" for g, v in sorted(tally.items()))
              + " | marked " + "; ".join(f"{g}: {rate(*v)}" for g, v in sorted(mt.items())))

    print("\n== version 8: mismatches across the keep line, which reading is right")
    for j in V8_JUDGES:
        c = Counter()
        for (jj, _, s, e, k), (stated, imp, pat) in mism.items():
            if jj != j or (stated == 3) == (imp == 3):
                continue
            c["crossing"] += 1
            ref = reference(j, s, e, k)
            if ref is None:
                c["other two split or missing"] += 1
            else:
                c["stated agrees with the other two" if (stated == 3) == ref else "answers agree with the other two"] += 1
            mark = marks.get((s, e, k))
            if mark in ("G", "B"):
                c["stated right by the mark" if (stated == 3) == (mark == "G") else "answers right by the mark"] += 1
            elif mark:
                c[f"marked {mark}"] += 1
        out["crossing"][j] = dict(c)
        print(f"  {j}: {json.dumps(dict(sorted(c.items())))}")
    print("\n== version 8: roles with the most mismatches")
    for j in V8_JUDGES:
        roles = Counter(f"{s}/{e}" for (jj, _, s, e, _), _ in mism.items() if jj == j)
        out["roles"][j] = dict(roles.most_common())
        print(f"  {j}: " + ", ".join(f"{r} {n}" for r, n in roles.most_common(10)))

    luna = {(s, e, k): v for (j, _, s, e, k), v in mism.items() if j == LUNA}
    have = [r for r in REJUDGES if all((LUNA, r, s) in rep for s in SETS)]
    if not have:
        print(f"\n(no rejudges of {LUNA}'s {len(luna)} mismatched responses yet)")
        return
    print(f"\n== version 8: rejudging {LUNA}'s {len(luna)} mismatched responses ({len(have)} fresh calls each)")
    c = Counter()
    policies = {
        "stated (as now)": lambda st, imp, rj: st == 3,
        "answers' score": lambda st, imp, rj: imp == 3,
        "one rejudge": lambda st, imp, rj: rj[0][0] == 3,
        "rejudge until consistent (3 at most), else answers' score":
            lambda st, imp, rj: next((x[0] for x in rj if consistent(x)), imp) == 3,
        "majority of the original and the rejudges": lambda st, imp, rj: sum(x[0] == 3 for x in rj) + (st == 3) > (len(rj) + 1) / 2,
    }
    pol = {p: Counter() for p in policies}
    for (s, e, k), (stated, imp, pat) in luna.items():
        rj = [rep[(LUNA, r, s)].get((e, k)) for r in have]
        if None in rj or any(x[0] is None for x in rj):
            c["a rejudge missing or unparsed"] += 1
            continue
        c["responses"] += 1
        c["rejudge replies consistent"] += sum(consistent(x) for x in rj)
        c["rejudge replies"] += len(rj)
        c["rejudge states the original score"] += sum(x[0] == stated for x in rj)
        c["all rejudges consistent"] += all(consistent(x) for x in rj)
        c["no rejudge consistent"] += not any(consistent(x) for x in rj)
        ref, mark = reference(LUNA, s, e, k), marks.get((s, e, k))
        for p, f in policies.items():
            kp = f(stated, imp, rj)
            pol[p]["keeps"] += kp
            pol[p]["keep decision changed from stated"] += kp != (stated == 3)
            if ref is not None:
                pol[p]["agrees with the other two"] += kp == ref
                pol[p]["other two agree (n)"] += 1
            if mark in ("G", "B"):
                pol[p]["right by the mark"] += kp == (mark == "G")
                pol[p]["marked G or B (n)"] += 1
    out["rejudge"] = {"calls": have, "replies": dict(c), "policies": {p: dict(v) for p, v in pol.items()}}
    print("  " + json.dumps(dict(c)))
    for p, v in pol.items():
        print(f"  {p}: {json.dumps(dict(v))}")


def write_rejudge_responses(out_dir: Path) -> None:
    """Write gpt-5.6-luna's v8 mismatched responses to ``out_dir/<set>/<role>.jsonl``, for step 3 to rejudge."""
    rep = load_replies((LUNA,), ("v8",))
    keys = defaultdict(set)
    for s in SETS:
        for (e, k), x in rep[(LUNA, "v8", s)].items():
            if len(x[1]) == 3 and x[0] is not None and not consistent(x):
                keys[(s, e)].add(k)
    n = 0
    for (s, e), ks in sorted(keys.items()):
        rows = []
        for line in (RESPONSES[s] / f"{e}.jsonl").read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                # pipeline/3_judge.py response_key
                if f"{r['label']}_p{r['prompt_index']}_q{r['question_index']}" in ks:
                    rows.append(line)
        (out_dir / s).mkdir(parents=True, exist_ok=True)
        (out_dir / s / f"{e}.jsonl").write_text("\n".join(rows) + "\n")
        n += len(rows)
    print(f"wrote {n} responses of {len(keys)} roles to {out_dir}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path)
    ap.add_argument("--write_rejudge_responses", type=Path, metavar="DIR",
                    help=f"write {LUNA}'s v8 mismatched responses to DIR/<set>/ for step 3, and stop")
    args = ap.parse_args()
    if args.write_rejudge_responses:
        write_rejudge_responses(args.write_rejudge_responses)
        return
    rep = load_replies()
    marks = load_marks()
    print(f"reader marks: {len(marks)} responses ({dict(Counter(marks.values()))})")
    res = {"cells": {}, "patterns": {}, "borderline": {}, "crossing": {}, "roles": {}}

    print("== stated score against the score the A/B/C answers imply")
    mism = mismatches(rep, sorted(rep), res)

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
            line = "; ".join(f"{g}: {rate(m, n)}" for g, (m, n) in sorted(tally.items()))
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
    print("  reader-marked responses: " + "; ".join(f"{g}: {rate(m, n)}" for g, (m, n) in sorted(mt.items())))

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
                    rejudge["rejudge consistent" if consistent(other) else "rejudge inconsistent too"] += 1
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
    v8_section(marks, res)
    if args.out:
        args.out.write_text(json.dumps(res, indent=1) + "\n")
        print("\nwrote", args.out)


if __name__ == "__main__":
    main()
