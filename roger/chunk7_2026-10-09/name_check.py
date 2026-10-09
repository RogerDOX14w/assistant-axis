"""Run the antonym check with --name-pos on some traits and record every answer.

Each answer goes into the check history (with the positive name added to the
record) and into the queue entry's `name_answers` list, so that rounds of the
description-to-label loop are all kept (Roger's keep-every-sample rule).

    uv run python roger/chunk7_2026-10-09/name_check.py STEM [STEM ...] [--phase LABEL]
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

ap = argparse.ArgumentParser(); ap.add_argument("stems", nargs="+"); ap.add_argument("--phase", default="name check")
args = ap.parse_args()
res = subprocess.run(["uv", "run", "python", "data_analysis/generate_antonyms.py", "--traits", *args.stems, "--name-pos"],
                     text=True, capture_output=True)
if res.returncode != 0:
    print(res.stderr[-1500:]); raise SystemExit(1)
results = json.loads(res.stdout)
Q = Path("data/seed_queue.json"); q = SE.load_queue(Q); by = {e["stem"]: e for e in q["entries"]}
reg = SE.build_registry(q, Path("data")); hist = []
for stem, r in results.items():
    e = by[stem]
    v = SE.classify_check(r.get("negative_label", ""), e.get("partner"), reg)
    rec = SE.check_history_record(stem, SE._trait_doc(Path("data"), stem), r, v, e.get("partner"), args.phase)
    rec["positive_name"] = r.get("positive_name"); rec["positive_name_reasoning"] = r.get("positive_name_reasoning")
    hist.append(rec)
    e.setdefault("name_answers", []).append({"date": date.today().isoformat(), "phase": args.phase, "label": e["label"],
                                            "positive_name": r.get("positive_name"), "negative_label": r.get("negative_label"),
                                            "antonym_score": r.get("antonym_score")})
    print(f"{stem:18s} label={e['label']!r:18s} pos-name: {r.get('positive_name')!s:40s} antonym: {r.get('negative_label')} ({r.get('antonym_score')})")
    print(f"    pos-name reasoning: {(r.get('positive_name_reasoning') or '')[:260]}")
    print(f"    antonym reasoning:  {(r.get('reasoning') or '')[:260]}")
SE.save_queue(q, Q); SE.append_check_history(Path("data"), hist)
