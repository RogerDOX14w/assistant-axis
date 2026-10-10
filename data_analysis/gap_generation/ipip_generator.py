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
    man = D.fetch_all(dest_root=args.external, only=args.only, force=args.force, dry_run=args.dry_run,
                      git_sha=None if args.dry_run else _git_sha(), sources_manifest_path=args.sources_manifest)
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


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external", type=Path, default=P.EXTERNAL_DIR, help="where the pages go (data/external/ipip)")
    ap.add_argument("--sources-manifest", type=Path, default=P.SOURCES_MANIFEST_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("download", help="fetch the three IPIP pages (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_download)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
