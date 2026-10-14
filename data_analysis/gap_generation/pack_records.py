#!/usr/bin/env python3
"""Pack large record files under ``data/candidates/`` into gzip (``X`` -> ``X.gz``), so that git can carry them
(GitHub refuses a file over 100 MB; gzip makes these records about 6x smaller).  Every reader of the platform reads a
packed file as it read the plain one (:mod:`assistant_axis.gapgen.records`, which also describes the two kinds).

    uv run python data_analysis/gap_generation/pack_records.py --dry-run [--root DIR] [--min-mb 50]
    uv run python data_analysis/gap_generation/pack_records.py [--root DIR] [--min-mb 50]
    uv run python data_analysis/gap_generation/pack_records.py --path data/candidates/review/B/responses.jsonl

With ``--dry-run`` it lists every ``.json`` / ``.jsonl`` file under ``--root`` (default ``data/candidates``) at or over
``--min-mb``: its kind (``log``: ``responses.jsonl``, appended to; ``snapshot``: ``results.jsonl``, ``graph.json``,
``readings.jsonl``, ``matches.jsonl``, rewritten whole), its size and its estimated packed size.  Without it, it packs
them.  ``--path P`` packs that one file whatever its size.  A file whose name is not a record file's is printed and
skipped (``--path``: refused, exit 2); so is one a live session holds locked, one that changes while it is packed, a
log whose plain file repeats its ``.gz`` content, and one whose new ``.gz`` does not decompress to exactly the content
read (the plain file is deleted only after that check).  Exit 1 when any record file was refused.

Pack only a run that has ended.  Then commit the ``.gz`` and the deletion of the plain file (``git add X.gz`` and
``git rm --cached X`` when the plain file was tracked).  No API call.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import records as RF  # noqa: E402
from assistant_axis.gapgen.paths import DATA_CANDIDATES  # noqa: E402

MB = 1 << 20


def scan(root: Path, *, min_mb: float) -> list[tuple[Path, int]]:
    """``[(path, bytes)]`` of the ``.json`` / ``.jsonl`` files under ``root`` at or over ``min_mb``, sorted by path."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith((".json", ".jsonl")):
                continue
            p = Path(dirpath) / name
            size = p.stat().st_size
            if size >= min_mb * MB:
                out.append((p, size))
    return sorted(out)


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return str(p)


def _mb(n: int) -> str:
    return f"{n / MB:.1f} MB"


def pack_one(p: Path, *, dry_run: bool) -> str:
    """``packed``, ``nothing``, ``refused``, ``would pack`` or ``skipped``; prints one line."""
    kind = RF.kind_of(p)
    size = p.stat().st_size if p.exists() else 0
    if kind is None:
        print(f"skip      {_rel(p)}  {_mb(size)}: not a record file ({', '.join(sorted(RF.KINDS))})")
        return "skipped"
    if dry_run:
        g = RF.gz_path(p)
        has = f"; beside {_mb(g.stat().st_size)} already packed" if g.exists() else ""
        print(f"would pack {_rel(p)}  {kind}  {_mb(size)} -> about {_mb(RF.estimate_packed_bytes(p))}{has}")
        return "would pack"
    rep = RF.pack(p)
    if rep.action == "packed":
        print(f"packed    {_rel(p)}  {kind}  {_mb(rep.plain_bytes)} -> {_rel(RF.gz_path(p))} "
              f"{_mb(rep.gz_bytes_before)} -> {_mb(rep.gz_bytes_after)}")
    else:
        print(f"{rep.action:9s} {_rel(p)}  {kind}: {rep.reason}", file=sys.stderr if rep.action == "refused" else None)
    return rep.action


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DATA_CANDIDATES, help="default: data/candidates")
    ap.add_argument("--min-mb", type=float, default=50.0, help="pack files of this size or more (default 50)")
    ap.add_argument("--path", type=Path, default=None, help="pack this one file, whatever its size")
    ap.add_argument("--dry-run", action="store_true", help="list what would be packed; change nothing")
    args = ap.parse_args(argv)
    if args.path is not None:
        p = RF.plain_path(args.path)
        if RF.kind_of(p) is None:
            print(f"REFUSED: {_rel(p)} is not a record file ({', '.join(sorted(RF.KINDS))})", file=sys.stderr)
            return 2
        if not p.exists():
            print(f"nothing to pack: {_rel(p)} does not exist"
                  + (f" ({_rel(RF.gz_path(p))} is already packed)" if RF.gz_path(p).exists() else ""))
            return 0
        action = pack_one(p, dry_run=args.dry_run)
        return 2 if action == "refused" else 0
    found = scan(args.root, min_mb=args.min_mb)
    if not found:
        print(f"no .json or .jsonl file of {args.min_mb:g} MB or more under {_rel(args.root)}")
        return 0
    actions = [pack_one(p, dry_run=args.dry_run) for p, _ in found]
    counts = {a: actions.count(a) for a in dict.fromkeys(actions)}
    print("; ".join(f"{n} {a}" for a, n in counts.items()))
    if counts.get("packed"):
        print("commit each .gz with the plain file's deletion (git rm --cached for a tracked plain file)")
    return 1 if counts.get("refused") else 0


if __name__ == "__main__":
    sys.exit(main())
