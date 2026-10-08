"""Write a set-level arrangement (map, set, triangle, ring, sequence) on a group of
seeded chunk-5 files, in place of the `singleton` that `seed_entities.py write`
records for a non-X trait.  Members come from the queue (`arrangement_members`
of the entries named by --stems, or every chunk-5 entry whose `pairing` is the
kind and whose members include the stems), or from --members.  Idempotent: a
member that already carries the same kind and members is left alone.

    uv run python roger/chunk5_2026-10-08/add_arrangement.py --kind map \
        --members african east_asian european indigenous_american indigenous_australian middle_eastern south_asian \
        --source "coarse ethnic and racial memberships (coverage audit part 2, decided 2026-09-07)" [--note ...] [--dry-run]

`uv run python data_analysis/check_arrangements.py` afterwards.
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
ORDERED = {"ring", "sequence"}   # order is content; everything else is sorted


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True, choices=["map", "set", "triangle", "ring", "sequence", "square"])
    ap.add_argument("--members", nargs="*", help="member stems; default: the queue's arrangement_members of --stems")
    ap.add_argument("--stems", nargs="*", help="queue entries whose arrangement_members define the group")
    ap.add_argument("--source", required=True, help="provenance string for the structure")
    ap.add_argument("--note", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    members = list(args.members or [])
    if not members:
        q = json.load(open(QUEUE, encoding="utf-8"))
        by = {e["stem"]: e for e in q["entries"]}
        for s in args.stems or []:
            members.extend(by[s].get("arrangement_members") or [])
    if not members:
        raise SystemExit("no members: pass --members or --stems with arrangement_members in the queue")
    if args.kind not in ORDERED:
        members = sorted(set(members))
    arr = {"kind": args.kind, "members": members, "source": args.source}
    if args.note:
        arr["note"] = args.note
    print(f"{args.kind} over {len(members)} members: {', '.join(members)}")
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
        arrs = [a for a in arrs if a.get("kind") != "singleton"]   # the set replaces the seed-time singleton
        stale = [a for a in arrs if a.get("kind") == arr["kind"]]   # a member belongs to one map / set of a kind, so
        for a in stale:                                            # a changed member list REPLACES the old one
            print(f"  {stem}: replacing the earlier {a['kind']} of {len(a.get('members') or [])} members")
        arrs = [a for a in arrs if a.get("kind") != arr["kind"]]
        arrs.append(arr)
        doc["arrangement"] = arrs[0] if len(arrs) == 1 else arrs
        if not args.dry_run:
            gen.atomic_write_json(path, doc)
        print(f"  {stem}: {'would write' if args.dry_run else 'written'} ({[a['kind'] for a in arrs]})")


if __name__ == "__main__":
    main()
