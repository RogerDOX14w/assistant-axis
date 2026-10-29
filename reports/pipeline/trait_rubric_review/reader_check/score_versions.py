"""Score every judged (judge, prompt version) pair of the trait rubric test against the readings' marks: precision
and recall per tier and overall, weighted by stratum population as tally.py does (the marks of the first reading,
the re-read over them, Roger's over both, and the items of his second sheet), the eight hard traits' keeps per
trait, and, for a version read from A/B/C answers, the same under the stated SCORE line (``abc_disagreements.jsonl``
gives the stated score where the two differ).  A marked item the pair has not scored (a reply cut at max_tokens)
is left out and counted as "unscored".  Writes versions_scores.json beside this script.

    uv run python reports/pipeline/trait_rubric_review/reader_check/score_versions.py [--versions 3 11 12]
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

D = Path("reports/pipeline/trait_rubric_review/reader_check")
sys.path.insert(0, str(D))
import build  # noqa: E402
import tally  # noqa: E402

R = Path("runpod_workspace/rubric_exp/judges")
SET_DIR = {"low": "traits", "new": "tiers"}


def all_marks_and_items():
    key = json.loads((D / "key.json").read_text())
    items = dict(key["items"])
    mk = {i: m for i, (m, _) in tally.marks().items()}
    for name in ("roger_marks.json", "roger_marks_2.json"):
        p = D / name
        if p.exists():
            mk.update(json.loads(p.read_text())["items"])
    k2 = D / "key_2.json"
    if k2.exists():
        items.update(json.loads(k2.read_text())["items"])
    return key["population"], items, mk


def scores_of(judge: str, version: str, reading: str) -> dict:
    """``(set, entity, key) -> score`` for the pair under ``reading`` ("answers": the score files; "stated": the
    SCORE line where abc_disagreements.jsonl records one)."""
    out = {}
    for set_, sub in SET_DIR.items():
        d = R / judge / sub / version
        if not d.exists():
            continue
        for e, sc in build.scores(d).items():
            for k, v in sc.items():
                out[(set_, e, k)] = v
        dis = d / "abc_disagreements.jsonl"
        if reading == "stated" and dis.exists():
            for line in dis.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r.get("stated") is not None:
                        out[(set_, r["entity"], r["key"])] = r["stated"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", nargs="+", default=["v3", "v11", "v12"])
    args = ap.parse_args()
    population, items, mk = all_marks_and_items()
    low = build.SELECTION["tiers"]["low"]
    by_stratum = defaultdict(list)
    for i, it in items.items():
        if mk.get(i) in tally.WEIGHT:
            by_stratum[it["stratum"]].append((i, it))
    res = {}
    print(f"{len([i for i in items if mk.get(i) in tally.WEIGHT])} marked items; precision / recall, weighted by "
          "stratum population (T half good, G/T three quarters, T/B a quarter)")
    print(f"{'judge':18s} {'ver':5s} {'read':8s} {'unscored':>8s}  {'low P/R':>13s}  {'medium P/R':>13s}  "
          f"{'high P/R':>13s}  {'all P/R':>13s}   hard traits kept of 500: " + " ".join(f"{e[:6]:>6s}" for e in low))
    for judge in sorted(p.name for p in R.iterdir() if p.is_dir()):
        for version in args.versions:
            if not any((R / judge / sub / version).exists() for sub in SET_DIR.values()):
                continue
            readings = ["answers"]
            if any((R / judge / sub / version / "abc_disagreements.jsonl").exists() for sub in SET_DIR.values()):
                readings.append("stated")
            for reading in readings:
                sc = scores_of(judge, version, reading)
                row = {"unscored": 0, "tiers": {}}
                cells = []
                for tier in ("low", "medium", "high", "all"):
                    kg = kb = tg = 0.0
                    for st, its in by_stratum.items():
                        if tier != "all" and not st.startswith(tier + "|"):
                            continue
                        have = [(i, it) for i, it in its if (it["set"], it["entity"], it["key"]) in sc]
                        if tier == "all":
                            row["unscored"] += len(its) - len(have)
                        if not have:
                            continue
                        pop = population[st]
                        for i, it in have:
                            w = tally.WEIGHT[mk[i]]
                            kept = sc[(it["set"], it["entity"], it["key"])] == 3
                            kg += pop * kept * w / len(have)
                            kb += pop * kept * (1 - w) / len(have)
                            tg += pop * w / len(have)
                    prec = kg / (kg + kb) if kg + kb else float("nan")
                    rec = kg / tg if tg else float("nan")
                    row["tiers"][tier] = {"precision": prec, "recall": rec, "kept_good": kg, "kept_bad": kb,
                                          "total_good": tg}
                    cells.append(f"{100 * prec:5.1f}/{100 * rec:5.1f}")
                kept = {e: sum(v == 3 for (s, ee, k), v in sc.items() if s == "low" and ee == e) for e in low}
                row["hard_traits_kept"] = kept
                row["kept_total"] = sum(v == 3 for v in sc.values())
                res[f"{judge}|{version}|{reading}"] = row
                print(f"{judge:18s} {version:5s} {reading:8s} {row['unscored']:8d}  " + "  ".join(f"{c:>13s}" for c in cells)
                      + "   " + " ".join(f"{kept[e]:6d}" for e in low))
    (D / "versions_scores.json").write_text(json.dumps(res, indent=1) + "\n")


if __name__ == "__main__":
    main()
