"""Fold a writer's drafts file into data/seed_queue.json (chunk 4, Roger's method of 2026-10-06).

For each object of the drafts file the queue entry of the same stem gets:
description_draft, source_url, source_text, source_retrieved, low_pole_derived,
nearest_existing, pair_review (where present), and `source` rewritten as
"<instrument>; <url>" so that the trait file records provenance with the URL.
Standards pairs are paired by construction (pair_by_construction = True), so
`seed_entities.py write` sets the two negative_labels to each other and the
antonym check is informational.  Status is left alone; the reviewer's pass
sets `description` and `ready` (fold_review.py).

    uv run python roger/chunk4_2026-10-07/fold_drafts.py roger/chunk4_2026-10-07/drafts_bigfive_hexaco.json [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import seed_entities as SE  # noqa: E402

QUEUE = Path("data/seed_queue.json")
COPY = ("description_draft", "source_url", "source_text", "source_retrieved", "low_pole_derived",
        "nearest_existing", "pair_review", "set_review", "notes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("drafts")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    drafts = json.load(open(args.drafts, encoding="utf-8"))
    q = SE.load_queue(QUEUE)
    by_stem = {e["stem"]: e for e in q["entries"]}
    n = 0
    for d in drafts:
        e = by_stem.get(d["stem"])
        if e is None:
            raise SystemExit(f"no queue entry for {d['stem']!r}")
        for k in COPY:
            if k in d and d[k] not in (None, ""):
                e[k] = d[k]
        if d.get("source_url"):
            base = (e.get("source") or "").split(";")[0].strip()
            e["source"] = f"{base}; {d['source_url']}" if base else d["source_url"]
        if e.get("pairing") == "pair" and e.get("partner"):
            e["pair_by_construction"] = True
        n += 1
        words = len(str(d.get("description_draft", "")).split())
        print(f"{e['stem']:36s} {words:2d} words  derived={bool(d.get('low_pole_derived'))}  "
              f"{'PAIR FLAG: ' + d['pair_review'][:80] if d.get('pair_review') else ''}")
    if args.dry_run:
        print(f"dry run: {n} entries would be updated")
        return
    SE.save_queue(q, QUEUE)
    print(f"updated {n} entries in {QUEUE}")


if __name__ == "__main__":
    main()
