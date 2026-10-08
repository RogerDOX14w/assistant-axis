"""Add the orthoplex arrangement to the seeded Big Five (5-orthoplex) and HEXACO
(6-orthoplex) files.  `seed_entities.py write` records the by-construction
pair on each member; the instrument's whole structure (the poles of N clean
pairs) is a second arrangement on every member, with the pairs as `axes`
(AGENT_NOTES § "The `arrangement` field").  Idempotent.

    uv run python roger/chunk4_2026-10-07/add_orthoplex.py --sub-chunk "Big Five" --source "Costa & McCrae, NEO-PI-R domains" [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())
from data_analysis import regenerate_trait_instructions as gen  # noqa: E402

QUEUE = Path("data/seed_queue.json")
CORPUS = Path("data/traits/instructions")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sub-chunk", required=True)
    ap.add_argument("--source", required=True, help="provenance string for the structure")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    q = json.load(open(QUEUE, encoding="utf-8"))
    entries = [e for e in q["entries"] if str(e.get("chunk")) == "4" and e.get("sub_chunk") == args.sub_chunk]
    axes = sorted({tuple(sorted((e["stem"], e["partner"]))) for e in entries if e.get("partner")})
    members = sorted({m for e in entries for m in (e.get("arrangement_members") or [])}
                     or {s for a in axes for s in a})   # the queue lists members for some sets; else the pairs' poles
    n = len(axes)
    assert len(members) == 2 * n, (len(members), n)
    kind = "square" if n == 2 else f"{n}-orthoplex"   # the 2-orthoplex is written under its canonical name
    arr = {"kind": kind, "members": members, "axes": [list(a) for a in axes], "source": args.source}
    print(f"{args.sub_chunk}: {kind} over {len(members)} members, {n} axes")
    for stem in members:
        path = CORPUS / f"{stem}.json"
        if not path.exists():
            print(f"  {stem}: not seeded yet, skipped")
            continue
        doc = json.load(open(path, encoding="utf-8"))
        current = doc.get("arrangement")
        arrs = current if isinstance(current, list) else ([current] if current else [])
        if any(a.get("kind") == arr["kind"] and a.get("members") == members for a in arrs):
            print(f"  {stem}: already has it")
            continue
        arrs.append(arr)
        doc["arrangement"] = arrs
        if not args.dry_run:
            gen.atomic_write_json(path, doc)
        print(f"  {stem}: {'would add' if args.dry_run else 'added'} ({[a['kind'] for a in arrs]})")


if __name__ == "__main__":
    main()
