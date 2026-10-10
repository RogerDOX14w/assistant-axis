#!/usr/bin/env python3
"""The IPIP behavior-item generator (workstream 7, generator id ``ipip``).

    uv run python data_analysis/gap_generation/ipip_generator.py download [--only KEY ...] [--force] [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_07_behaviour_items.md``.  ``download`` fetches the three IPIP
pages into ``data/external/ipip/`` (git-ignored) and records them in ``DOWNLOAD_MANIFEST.json`` and the tracked
``data/candidates/ipip/sources_manifest.json``; ``--only hexaco_key`` fetches the fallback page.  Free.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import ipip as P  # noqa: E402
from assistant_axis.gapgen.generators.ipip import download as D  # noqa: E402
from assistant_axis.gapgen.generators.ipip.sources import SOURCES  # noqa: E402


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


def cmd_download(args) -> int:
    try:
        man = D.fetch_all(dest_root=args.external, only=args.only, force=args.force, dry_run=args.dry_run,
                          git_sha=None if args.dry_run else _git_sha(), sources_manifest_path=args.sources_manifest,
                          approved_by=args.approved_by)
    except D.NotApproved as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost):")
        for line in man.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in man.entries:
        print(f"{e['key']:16s} {e['size_bytes']:>9d} B  sha256 {e['sha256']}  {e['downloaded_at']}  {e['url']}")
    lic = man.licence
    print(f"licence: {lic.get('name')}; verbatim: {lic.get('verbatim') or '(not on the fetched pages)'}"
          + (f" [from {lic['verbatim_source']}]" if lic.get("verbatim_source") else ""))
    print(f"fetched: {', '.join(man.fetched) or 'none'}; already on disk and unchanged: {', '.join(man.skipped) or 'none'}")
    for p in man.written:
        print(f"wrote {p}")
    return 0


def cmd_ingest(args) -> int:
    import json

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.ipip import ingest as I
    try:
        items, counts = I.build_from_dir(args.external)
    except FileNotFoundError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    for k in ("n_items", "n_codes", "n_multi_code", "n_with_scales", "n_multi_scale", "n_keyed_minus",
              "n_scale_links", "n_constructs", "n_assignment_rows", "unmatched_assignments", "ambiguous_text_joins",
              "per_inventory", "hex", "scale_index", "instrument_names"):
        print(f"{k}: {json.dumps(counts.get(k), ensure_ascii=False)}")
    try:
        I.check_hex(counts)
        hex_ok = True
    except I.HexAssertionError as exc:
        hex_ok = False
        print(f"HEX ASSERTION FAILED: {exc}", file=sys.stderr)
    counts["hex_assertion"] = "passed" if hex_ok else "failed"
    if args.dry_run:
        print(f"DRY-RUN: would write {args.items} ({len(items)} items) and {args.counts}")
        return 0 if hex_ok or args.skip_hex_check else 1
    if not hex_ok and not args.skip_hex_check:
        print("nothing written (pass --skip-hex-check to write anyway)", file=sys.stderr)
        return 1
    backup = I.write_items(items, args.items)
    atomic_write_text(json.dumps(counts, indent=2, ensure_ascii=False) + "\n", args.counts)
    print(f"wrote {args.items} ({len(items)} items, sha256 {I.file_sha256(args.items)[:16]}...)"
          + (f"; previous file kept as {backup}" if backup else ""))
    print(f"wrote {args.counts}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external", type=Path, default=P.EXTERNAL_DIR, help="where the pages go (data/external/ipip)")
    ap.add_argument("--sources-manifest", type=Path, default=P.SOURCES_MANIFEST_PATH)
    ap.add_argument("--items", type=Path, default=P.ITEMS_PATH)
    ap.add_argument("--counts", type=Path, default=P.INGEST_COUNTS_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("download", help="fetch the three IPIP pages (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--approved-by", default=None,
                   help="Roger's go for a source with no approval on record (the assignment workbook, QUESTIONS 52)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("ingest", help="build items.jsonl and ingest_counts.json from the pages (no API cost)")
    p.add_argument("--skip-hex-check", action="store_true",
                   help="write even when the HEX assertion fails (plan § 7; the fallback is download --only hexaco_key)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_ingest)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
