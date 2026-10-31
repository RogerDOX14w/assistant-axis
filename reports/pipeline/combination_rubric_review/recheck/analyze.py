"""Read the re-check's judgings of the October combination sample (build_sample.py, run_judging.sh): per
response luna's combination score on version 3's text (C), its role score under version 10's reading (R) and
its trait score under version 13 (T), and the draft versions 14 and 15 where run.  Per combination and per kind
(r_, t_): the keep rates, what each candidate keep rule keeps (C v3; both R and T; either; the goal entity, T
for a t_ combination and R for an r_; the role), which persona is present among C's drops, cut responses, and
the May keep rate for the stems May also had.  Unlike the exploration's analysis there is no May stratification:
the sample is a random draw from whole files, so the shares are estimates for the files.

    uv run python analyze.py [--root runpod_workspace/combo_recheck] [--rows rows.json]
"""
import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import mean

RULES = {"C v3": lambda r: r["C"] == 3, "both": lambda r: r["Rs"] == 3 and r["T"] == 3,
         "either": lambda r: r["Rs"] == 3 or r["T"] == 3,
         "goal": lambda r: (r["T"] == 3) if r["kind"] == "t" else (r["Rs"] == 3),
         "role": lambda r: r["Rs"] == 3}
CELLS = ("RT", "Rt", "rT", "rt")


def scores(p):
    return json.loads(p.read_text()) if p.exists() else {}


def replies(p):
    out = {}
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["key"]] = r
    return out


def key_of(rec):
    return f"{rec['label']}_p{rec['prompt_index']}_q{rec['question_index']}"


def cell(r):
    return ("R" if r["Rs"] == 3 else "r") + ("T" if r["T"] == 3 else "t")


def pct(xs):
    return f"{100 * mean(xs):3.0f}%" if xs else "  - "


def cells_line(sub):
    c = Counter(cell(r) for r in sub)
    return "  ".join(f"{k} {100 * c[k] / len(sub):3.0f}%" for k in CELLS) if sub else "(none)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path("runpod_workspace/combo_recheck"))
    ap.add_argument("--rows", type=Path, default=None, help="write the per-response rows (with replies) here")
    a = ap.parse_args()
    man = json.load(open(a.root / "sample.json"))
    rows = []
    for stem, info in man["combinations"].items():
        role, trait, kind = info["role"], info["trait"], info["kind"]
        c_sc = scores(a.root / "combo" / "scores" / f"{stem}.json")
        r_sc = scores(a.root / "role" / stem / "scores" / f"{role}.json")
        t_sc = scores(a.root / "trait" / stem / "scores" / f"{trait}.json")
        v14 = scores(a.root / "combo_v14" / "scores" / f"{stem}.json")
        v15 = scores(a.root / "combo_v15" / "scores" / f"{stem}.json")
        c_rp = replies(a.root / "combo" / "scores" / "_replies" / f"{stem}.jsonl")
        r_rp = replies(a.root / "role" / stem / "scores" / "_replies" / f"{role}.jsonl")
        t_rp = replies(a.root / "trait" / stem / "scores" / "_replies" / f"{trait}.jsonl")
        for line in (a.root / "combo" / "responses" / f"{stem}.jsonl").read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            k = key_of(rec)
            rows.append(dict(stem=stem, kind=kind, role=role, trait=trait, key=k, question=rec["question"],
                             answer=next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant"),
                             cut=rec["finish_reason"] == "length", C=c_sc.get(k), Rs=r_sc.get(k), T=t_sc.get(k),
                             V14=v14.get(k), V15=v15.get(k),
                             c_reply=c_rp.get(k, {}).get("reply"), r_reply=r_rp.get(k, {}).get("reply"),
                             t_reply=t_rp.get(k, {}).get("reply")))
    n_all = len(rows)
    rows = [r for r in rows if r["C"] is not None and r["Rs"] is not None and r["T"] is not None]
    print(f"{n_all} responses in {len(man['combinations'])} combinations; {n_all - len(rows)} with a judgement "
          f"missing (unscored or not yet run), {len(rows)} complete")
    if not rows:
        return

    print(f"\nper combination: n, cut share, keep under C (version 3's combination text), R (role alone), T (trait alone),"
          f"\nwhat each rule keeps, the cells among C's drops (R/T = present, r/t = missing), and May's keep where known:")
    print(f"  {'combination':44s} {'n':>3s} {'cut':>4s}   C    R    T  | " + " ".join(f"{n:>6s}" for n in RULES)
          + " | drops: RT Rt rT rt | May")
    for stem, info in man["combinations"].items():
        sub = [r for r in rows if r["stem"] == stem]
        if not sub:
            print(f"  {stem:44s} (no complete judgements)")
            continue
        d = [r for r in sub if r["C"] != 3]
        c = Counter(cell(r) for r in d)
        may = f"{info['may_keep']:.2f}" if info.get("may_keep") is not None else "  - "
        print(f"  {stem:44s} {len(sub):3d} {pct([r['cut'] for r in sub])} "
              f"{mean(r['C'] == 3 for r in sub):.2f} {mean(r['Rs'] == 3 for r in sub):.2f} {mean(r['T'] == 3 for r in sub):.2f} | "
              + " ".join(f"{mean(f(r) for r in sub):6.2f}" for f in RULES.values())
              + " | " + " ".join(f"{c[k]:2d}" for k in CELLS) + f" | {may}")

    print("\nper kind, mean over its combinations of the keep under each rule (what a vector would be built from):")
    for kind in "rt":
        stems = [s for s, i in man["combinations"].items() if i["kind"] == kind and any(r["stem"] == s for r in rows)]
        if not stems:
            continue
        per = {n: [mean(f(r) for r in rows if r["stem"] == s) for s in stems] for n, f in RULES.items()}
        print(f"  {kind}_ ({len(stems)} combinations): " + "  ".join(f"{n} {mean(v):.2f}" for n, v in per.items())
              + f"   (lowest under both: {min(per['both']):.2f}, under goal: {min(per['goal']):.2f})")

    print("\nwhich persona is present (R = role shows, T = trait shows; lower case = missing), per kind:")
    for kind in "rt":
        sub = [r for r in rows if r["kind"] == kind]
        if not sub:
            continue
        print(f"  {kind}_ all responses   n {len(sub):4d}  " + cells_line(sub))
        d = [r for r in sub if r["C"] != 3]
        print(f"  {kind}_ among C's drops n {len(d):4d}  " + cells_line(d)
              + (f"   (one present, the other missing: {100 * sum(cell(r) in ('Rt', 'rT') for r in d) / len(d):.0f}%)" if d else ""))
        k_ = [r for r in sub if r["C"] == 3]
        print(f"  {kind}_ among C's keeps n {len(k_):4d}  " + cells_line(k_))

    print("\ncut responses: keep under C, R and T among cut and whole, per kind:")
    for kind in "rt":
        for cut in (True, False):
            sub = [r for r in rows if r["kind"] == kind and r["cut"] == cut]
            if sub:
                print(f"  {kind}_ {'cut  ' if cut else 'whole'} n {len(sub):4d}  C {mean(r['C'] == 3 for r in sub):.2f}  "
                      f"R {mean(r['Rs'] == 3 for r in sub):.2f}  T {mean(r['T'] == 3 for r in sub):.2f}  "
                      f"both {mean(RULES['both'](r) for r in sub):.2f}")

    arms = [r for r in rows if r["V14"] is not None and r["V15"] is not None]
    if arms:
        print(f"\nthe draft combination versions on {len(arms)} responses: keep, and agreement with the separate judges' rules:")
        for v, rule in (("V14", "both"), ("V15", "either")):
            kept = [r[v] == 3 for r in arms]
            agree = [(r[v] == 3) == RULES[rule](r) for r in arms]
            over = [r[v] == 3 and not RULES[rule](r) for r in arms]
            under = [r[v] != 3 and RULES[rule](r) for r in arms]
            print(f"  {v} ({rule}): keeps {mean(kept):.2f}  agrees with '{rule}' {mean(agree):.2f}  "
                  f"keeps what the rule drops {mean(over):.2f}  drops what the rule keeps {mean(under):.2f}")

    if a.rows:
        a.rows.write_text(json.dumps(rows, ensure_ascii=False, indent=0))
        print(f"\nrows written to {a.rows}")


if __name__ == "__main__":
    main()
