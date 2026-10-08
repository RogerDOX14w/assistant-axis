"""Fold a reviewer's verdicts into data/seed_queue.json and mark the entries ready.

For each reviewed entry: `description` = the reviewer's `suggested_edit` where
the verdict is "edit" and an edit is given (form or faithfulness fixes, the
normal writer -> reviewer loop), otherwise the writer's `description_draft`;
`review_issues` keeps the issues; status -> "ready".  Pair-level
`scope_flag`s are stored on both members as `pair_scope_flag` and are NOT
acted on: Roger decides re-edits for scope (his method, step 3).

    uv run python roger/chunk4_2026-10-07/fold_review.py roger/chunk4_2026-10-07/review_bigfive_hexaco.json [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import seed_entities as SE  # noqa: E402

QUEUE = Path("data/seed_queue.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("review")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    rev = json.load(open(args.review, encoding="utf-8"))
    q = SE.load_queue(QUEUE)
    by_stem = {e["stem"]: e for e in q["entries"]}
    edited = 0
    for r in rev["entries"]:
        e = by_stem[r["stem"]]
        text = (r.get("suggested_edit") or "").strip() if r.get("verdict") == "edit" else ""
        e["description"] = text or e["description_draft"]
        e["review_issues"] = r.get("issues", [])
        e["review_verdict"] = r.get("verdict")
        e["status"] = "ready"
        edited += bool(text)
        flag = "EDITED" if text else ("issues noted" if r.get("issues") else "ok")
        print(f"{e['stem']:36s} {len(e['description'].split()):2d} words  {flag}")
    for p in rev.get("pairs", []):
        for stem in p["members"]:
            if stem in by_stem and p.get("scope_flag"):
                by_stem[stem]["pair_scope_flag"] = p["scope_flag"]
    flagged = [p["members"] for p in rev.get("pairs", []) if p.get("scope_flag")]
    print(f"\n{len(rev['entries'])} entries ready, {edited} with the reviewer's edit; pair scope flags on {len(flagged)} pairs")
    if args.dry_run:
        print("dry run: queue not written")
        return
    SE.save_queue(q, QUEUE)
    print(f"updated {QUEUE}")


if __name__ == "__main__":
    main()
