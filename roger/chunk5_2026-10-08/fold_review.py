"""Fold a chunk-5 reviewer's verdicts into data/seed_queue.json and mark the entries ready.

Same as chunk 4's fold_review.py: `description` = the reviewer's `suggested_edit`
where the verdict is "edit" and an edit is given, otherwise the writer's
`description_draft`; `review_issues` and `review_verdict` kept; status -> "ready".
Chunk 5 has no pairs; the reviewer's `sets` verdicts are stored on every member
of the set as `set_review_by_reviewer` (with `agree_with_writer`) for Roger.

    uv run python roger/chunk5_2026-10-08/fold_review.py roger/chunk5_2026-10-08/review_5a.json [--dry-run]
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
        text = " ".join((r.get("suggested_edit") or "").split()) if r.get("verdict") == "edit" else ""
        e["description"] = text or " ".join(e["description_draft"].split())
        e["review_issues"] = r.get("issues", [])
        e["review_verdict"] = r.get("verdict")
        e["review_strength"] = r.get("strength")
        e["status"] = "ready"
        edited += bool(text)
        flag = "EDITED" if text else ("issues noted" if r.get("issues") else "ok")
        print(f"{e['stem']:28s} {len(e['description'].split()):2d} words  {flag}")
    for s in rev.get("sets", []):
        for stem in s.get("members", []):
            if stem in by_stem:
                by_stem[stem]["set_review_by_reviewer"] = {
                    "set": s.get("name"), "review": s.get("review"), "agree_with_writer": s.get("agree_with_writer")}
    print(f"\n{len(rev['entries'])} entries ready, {edited} with the reviewer's edit; {len(rev.get('sets', []))} set reviews stored")
    if args.dry_run:
        print("dry run: queue not written")
        return
    SE.save_queue(q, QUEUE)
    print(f"updated {QUEUE}")


if __name__ == "__main__":
    main()
