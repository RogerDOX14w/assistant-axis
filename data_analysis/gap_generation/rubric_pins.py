#!/usr/bin/env python3
"""Check or pin the rubric prompt versions (``reports/trait_gap_generation/rubrics/versions.json``): the
split filter's eight prompts and, since 2026-10-03, the M3 overlap rubrics (``overlap_concept``,
``overlap_cooccurrence``; since 2026-10-04 also the arms ``overlap_six``, ``overlap_relation`` and
``overlap_scope``, and their round-2 redrafts ``overlap_concept_implies``, ``overlap_six_implies``,
``overlap_relation_implies`` and ``overlap_scope_implies``; since 2026-10-07 M3's ``relation``; since
2026-10-08 the Roget generator's ``roget_head_scope``).

    uv run python data_analysis/gap_generation/rubric_pins.py check
    uv run python data_analysis/gap_generation/rubric_pins.py bump NAME --why TEXT [--version N] [--revert-to N]

``check`` lists every prompt with its pinned version and hash, and exits 1 when a text on disk
is not its latest pinned version (a paid split run refuses to start in that state).
``bump`` appends a row for the text now on disk: the next version, its SHA-256, the UTC time and
``--why``.  ``--version`` is needed only for a prompt's first row (its draft number).
``--revert-to N`` is for going back to version N's text: it is pinned as the next version with
``"same_text_as": N`` (without the flag, a text an earlier version names is refused).  Rows are
never edited or removed.  No API call.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import split_rubrics as sr  # noqa: E402
from assistant_axis.gapgen.registry import utc_now  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rubrics-dir", type=Path, default=None, help="default: reports/trait_gap_generation/rubrics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    b = sub.add_parser("bump")
    b.add_argument("name", choices=sr.PINNED_NAMES)
    b.add_argument("--why", required=True)
    b.add_argument("--version", type=int, default=None, help="only for a prompt's first row")
    b.add_argument("--revert-to", type=int, default=None, metavar="N",
                   help="the text on disk is version N's again: pin it as the next version, marked as N's text")
    args = ap.parse_args(argv)
    if args.cmd == "check":
        pinned = sr.current_versions(args.rubrics_dir, sr.PINNED_NAMES)
        w_name = max(len(n) for n in sr.PINNED_NAMES)
        w_file = max(len(f) for f in sr.PINNED_FILES.values())
        for n in sr.PINNED_NAMES:
            v, sha = pinned.get(n, (None, None))
            print(f"{n:{w_name}s} {sr.PINNED_FILES[n]:{w_file}s} version {v}  "
                  f"{sha[:12] + '...' if sha else '(not pinned)'}")
        problems = sr.mismatches(args.rubrics_dir)
        for p in problems:
            print(f"MISMATCH {p}", file=sys.stderr)
        if problems:
            print(sr.bump_command(problems), file=sys.stderr)
        return 1 if problems else 0
    try:
        row = sr.bump(args.name, args.why, now=utc_now(), rubrics_dir=args.rubrics_dir, version=args.version,
                      revert_to=args.revert_to)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    same = f", the text of version {row['same_text_as']}" if "same_text_as" in row else ""
    print(f"pinned {args.name} version {row['version']} ({row['sha256'][:12]}...{same})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
