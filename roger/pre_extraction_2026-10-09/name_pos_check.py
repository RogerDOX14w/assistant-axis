"""The antonym check, with or without the label-blind naming call (--name-pos), on any traits; every answer recorded.

Each answer goes to data/traits/antonym_check_history.jsonl (with positive_name when asked; keep every sample), and,
where the trait has a queue entry, to its check_answers and name_answers.  Unlike the chunk-7 name_check.py, a trait
with no queue entry is fine.

    uv run python roger/pre_extraction_2026-10-09/name_pos_check.py STEM [STEM ...] --phase LABEL [--no-name]
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import seed_entities as SE  # noqa: E402


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stems", nargs="+"); ap.add_argument("--phase", required=True)
    ap.add_argument("--no-name", action="store_true", help="the plain antonym check only")
    args = ap.parse_args()
    cmd = ["uv", "run", "python", "data_analysis/generate_antonyms.py", "--traits", *args.stems]
    if not args.no_name:
        cmd.append("--name-pos")
    res = subprocess.run(cmd, text=True, capture_output=True)
    if res.returncode != 0:
        print(res.stderr[-2000:]); raise SystemExit(1)
    results = json.loads(res.stdout)
    Q = Path("data/seed_queue.json"); q = SE.load_queue(Q); by = {e["stem"]: e for e in q["entries"] if e["entity_type"] == "trait"}
    reg = SE.build_registry(q, Path("data")); hist = []
    for stem, r in results.items():
        doc = SE._trait_doc(Path("data"), stem)
        v = SE.classify_check(r.get("negative_label", ""), None, reg)
        rec = SE.check_history_record(stem, doc, r, v, None, args.phase)
        if "positive_name" in r:
            rec["positive_name"] = r.get("positive_name"); rec["positive_name_reasoning"] = r.get("positive_name_reasoning")
        hist.append(rec)
        e = by.get(stem)
        if e is not None:
            SE.note_check_answer(e, r.get("negative_label"), args.phase)
            if "positive_name" in r:
                e.setdefault("name_answers", []).append({
                    "date": date.today().isoformat(), "phase": args.phase, "label": doc["positive_label"],
                    "positive_name": r.get("positive_name"), "negative_label": r.get("negative_label"),
                    "antonym_score": r.get("antonym_score")})
        line = f"{stem:16s} label {doc['positive_label']!r:22s} -> {r.get('negative_label')} ({r.get('antonym_score')})"
        if "positive_name" in r:
            line += f"   blind name: {r.get('positive_name')}"
        print(line)
        if r.get("positive_name_reasoning"):
            print(f"    name: {r['positive_name_reasoning'][:320]}")
    SE.save_queue(q, Q); SE.append_check_history(Path("data"), hist)


if __name__ == "__main__":
    main()
