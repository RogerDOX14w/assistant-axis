"""Read the three judgings of the combination exploration sample: per response the May combination score (mini,
April rubric), luna's combination score (version 3's text), luna's role score (version 10's reading) and luna's
trait score (version 13).  Per stratum: how often the drops are "one present, the other missing", which one,
and how that compares with the May verdicts; then example replies for each pattern."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

R = Path("runpod_workspace/combo_explore")
man = json.load(open(R / "sample.json"))
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else None


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


# the one role renamed in the corpus since May (text unchanged): judged under its new name, in its own directories
RENAMED = {"r_aligned_artificial_intelligence__pensive": ("r_instrumentally_aligned_ai__pensive", "instrumentally_aligned_ai")}
rows = []
for stem, info in man["combinations"].items():
    role, trait, s = info["role"], info["trait"], info["stratum"]
    if stem in RENAMED:
        new_stem, new_role = RENAMED[stem]
        c_sc = scores(R / "combo_renamed" / "scores" / f"{new_stem}.json")
        r_sc = scores(R / "role_renamed" / "scores" / f"{new_role}.json")
        c_rp = replies(R / "combo_renamed" / "scores" / "_replies" / f"{new_stem}.jsonl")
        r_rp = replies(R / "role_renamed" / "scores" / "_replies" / f"{new_role}.jsonl")
    else:
        c_sc = scores(R / "combo" / "scores" / f"{stem}.json")
        r_sc = scores(R / "role" / stem / "scores" / f"{role}.json")
        c_rp = replies(R / "combo" / "scores" / "_replies" / f"{stem}.jsonl")
        r_rp = replies(R / "role" / stem / "scores" / "_replies" / f"{role}.jsonl")
    t_sc = scores(R / "trait" / stem / "scores" / f"{trait}.json")
    t_rp = replies(R / "trait" / stem / "scores" / "_replies" / f"{trait}.jsonl")
    for line in (R / "combo" / "responses" / f"{stem}.jsonl").read_text().splitlines():
        rec = json.loads(line)
        k = key_of(rec)
        rows.append(dict(stem=stem, stratum=s, role=role, trait=trait, key=k, question=rec["question"],
                         answer=next(m["content"] for m in reversed(rec["conversation"]) if m["role"] == "assistant"),
                         cut=rec["finish_reason"] == "length", may=rec["explore"]["may_score"],
                         role_alone=rec["explore"]["role_alone"], trait_alone=rec["explore"]["trait_alone"],
                         C=c_sc.get(k), Rs=r_sc.get(k), T=t_sc.get(k),
                         c_reply=c_rp.get(k, {}).get("reply"), r_reply=r_rp.get(k, {}).get("reply"),
                         t_reply=t_rp.get(k, {}).get("reply")))
n_missing = sum(r["C"] is None or r["Rs"] is None or r["T"] is None for r in rows)
print(f"{len(rows)} responses; {n_missing} with a judgement missing (unscored or not yet run)")
rows = [r for r in rows if r["C"] is not None and r["Rs"] is not None and r["T"] is not None]


def cell(r):
    return ("R" if r["Rs"] == 3 else "r") + ("T" if r["T"] == 3 else "t")


def kappa(a, b):
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


print("\nluna's combination verdict against May's (keep = 3), per stratum:")
for s in man["strata"]:
    sub = [r for r in rows if r["stratum"] == s]
    may_k = [r["may"] == 3 for r in sub]; c_k = [r["C"] == 3 for r in sub]
    print(f"  {s:18s} n {len(sub):4d}  May kept {sum(may_k) / len(sub):.2f}  luna kept {sum(c_k) / len(sub):.2f}  "
          f"agreement {sum(a == b for a, b in zip(may_k, c_k)) / len(sub):.2f}  kappa {kappa(may_k, c_k):.2f}  "
          f"role-alone kept {sum(r['Rs'] == 3 for r in sub) / len(sub):.2f}  trait-alone kept {sum(r['T'] == 3 for r in sub) / len(sub):.2f}")

print("\nthe separate judgements (R = role shows, T = trait shows; lower case = not) among the responses luna's")
print("combination judge DROPS, and among those it KEEPS, per stratum (share of the stratum's drops / keeps):")
for s in man["strata"]:
    for verdict, name in ((lambda r: r["C"] != 3, "drops"), (lambda r: r["C"] == 3, "keeps")):
        sub = [r for r in rows if r["stratum"] == s and verdict(r)]
        c = Counter(cell(r) for r in sub)
        if sub:
            print(f"  {s:18s} {name:5s} n {len(sub):4d}  " + "  ".join(f"{k} {100 * c[k] / len(sub):3.0f}%" for k in ("RT", "Rt", "rT", "rt")))

print("\nthe same among the responses MAY dropped (the question asked: what is being dropped), per stratum:")
for s in man["strata"]:
    sub = [r for r in rows if r["stratum"] == s and r["may"] != 3]
    c = Counter(cell(r) for r in sub)
    print(f"  {s:18s} n {len(sub):4d}  " + "  ".join(f"{k} {100 * c[k] / len(sub):3.0f}%" for k in ("RT", "Rt", "rT", "rt"))
          + f"   luna combination keeps {100 * sum(r['C'] == 3 for r in sub) / len(sub):.0f}% of them")

print("\nhypothesis 1 (one switch): stratum C's May drops on questions where BOTH standalone entities were kept in May:")
sub = [r for r in rows if r["stratum"] == "C_both_expected" and r["may"] != 3 and r["role_alone"] == 3 and r["trait_alone"] == 3]
c = Counter(cell(r) for r in sub)
print(f"  n {len(sub)}  " + "  ".join(f"{k} {100 * c[k] / max(len(sub), 1):3.0f}%" for k in ("RT", "Rt", "rT", "rt"))
      + f"   luna combination keeps {100 * sum(r['C'] == 3 for r in sub) / max(len(sub), 1):.0f}%")
sub2 = [r for r in rows if r["stratum"] == "C_both_expected" and r["may"] != 3 and not (r["role_alone"] == 3 and r["trait_alone"] == 3)]
c2 = Counter(cell(r) for r in sub2)
print(f"  (May drops where a standalone was also dropped: n {len(sub2)}  " + "  ".join(f"{k} {100 * c2[k] / max(len(sub2), 1):3.0f}%" for k in ("RT", "Rt", "rT", "rt")) + ")")

print("\namong the responses MAY KEPT: luna's combination verdict and the separate judgements, per stratum:")
for s in man["strata"]:
    sub = [r for r in rows if r["stratum"] == s and r["may"] == 3]
    c = Counter(cell(r) for r in sub)
    print(f"  {s:18s} n {len(sub):4d}  luna combination keeps {100 * sum(r['C'] == 3 for r in sub) / len(sub):.0f}%   "
          + "  ".join(f"{k} {100 * c[k] / len(sub):3.0f}%" for k in ("RT", "Rt", "rT", "rt")))

print("\nper combination: n, May keep, luna combination keep, role-alone keep, trait-alone keep, and among luna's drops the cells:")
for stem, info in man["combinations"].items():
    sub = [r for r in rows if r["stem"] == stem]
    if not sub:
        print(f"  {info['stratum'][:1]} {stem:44s} (no complete judgements)")
        continue
    d = [r for r in sub if r["C"] != 3]
    c = Counter(cell(r) for r in d)
    print(f"  {info['stratum'][:1]} {stem:44s} n {len(sub):3d}  May {sum(r['may'] == 3 for r in sub) / len(sub):.2f}  "
          f"C {sum(r['C'] == 3 for r in sub) / len(sub):.2f}  R {sum(r['Rs'] == 3 for r in sub) / len(sub):.2f}  "
          f"T {sum(r['T'] == 3 for r in sub) / len(sub):.2f}  drops: " + " ".join(f"{k}={c[k]}" for k in ("RT", "Rt", "rT", "rt")))

print("\ncut responses: luna's combination keep among cut and uncut, per stratum:")
for s in man["strata"]:
    for cut in (True, False):
        sub = [r for r in rows if r["stratum"] == s and r["cut"] == cut]
        if sub:
            print(f"  {s:18s} {'cut  ' if cut else 'whole'} n {len(sub):4d}  luna keeps {sum(r['C'] == 3 for r in sub) / len(sub):.2f}  "
                  f"R {sum(r['Rs'] == 3 for r in sub) / len(sub):.2f}  T {sum(r['T'] == 3 for r in sub) / len(sub):.2f}")

if OUT:
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=0))
    print(f"\nrows written to {OUT}")
