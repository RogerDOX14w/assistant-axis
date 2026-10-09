"""Run the role-pair check (generate_antonyms.py --roles) and keep every answer.

Each answer goes into data/roles/role_pair_check_history.jsonl (append-only, one JSON object per
check, with the instructions the check read), the role-side counterpart of the traits' check history.
The intended partner is taken from the role's recorded `pair` arrangement, if any.  First used
2026-10-09 (pre-extraction work list W13) on the recorded role pairs and evangelist.

    uv run python roger/pre_extraction_2026-10-09/role_pair_check.py STEM [STEM ...] [--phase LABEL]
"""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

ROLES = Path("data/roles/instructions")
HISTORY = Path("data/roles/role_pair_check_history.jsonl")


def partner_of(stem: str, doc: dict) -> str | None:
    arr = doc.get("arrangement")
    for a in (arr if isinstance(arr, list) else [arr] if arr else []):
        if a.get("kind") == "pair":
            return next((m for m in a["members"] if m != stem), None)
    return None


ap = argparse.ArgumentParser()
ap.add_argument("stems", nargs="+")
ap.add_argument("--phase", default="role-pair check")
args = ap.parse_args()
res = subprocess.run(["uv", "run", "python", "data_analysis/generate_antonyms.py", "--roles", *args.stems],
                     text=True, capture_output=True)
if res.returncode != 0:
    print(res.stderr[-1500:]); raise SystemExit(1)
out = json.loads(res.stdout)
with HISTORY.open("a", encoding="utf-8") as f:
    for s in args.stems:
        r, d = out[s], json.load(open(ROLES / f"{s}.json", encoding="utf-8"))
        p = partner_of(s, d)
        f.write(json.dumps({"stem": s, "checked_at": datetime.date.today().isoformat(), "phase": args.phase,
                            "description": d["description"], "intended": p, "returned": r.get("opposing_role"),
                            "score": r.get("opposition_score"), "reasoning": r.get("reasoning"),
                            "instructions": [i["pos"] for i in d["instruction"]], "generator": d.get("generator")},
                           ensure_ascii=False) + "\n")
        print(f"{s:26s} -> {r.get('opposing_role')!s:40s} ({r.get('opposition_score')})  intended {p}")
