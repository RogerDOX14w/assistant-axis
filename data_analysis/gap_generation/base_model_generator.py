#!/usr/bin/env python3
"""The base-model generator (workstream 3, generator id ``base_model``).

    uv run python data_analysis/gap_generation/base_model_generator.py fetch [--only wikibio onet model]
        --approved-by 'Roger, <date>' [--force] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py bench [--batch-sizes 32,64] [--device mps]
    uv run python data_analysis/gap_generation/base_model_generator.py sample --round N --n 2000 [--temperature 1.0]
        [--t-grid 0.8,1.0,1.2 --per-t 500] [--families list,person,...] [--batch-size 32] [--device mps] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py parse --round N [--temperature T] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py stats --round N [--temperature T] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py submit --round N --run-id R [--min-count 1]
        [--budget-usd 15] [--transport live|batches] [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_03_base_model.md``.  ``fetch`` downloads ``wiki_bio`` and the
O*NET occupation titles into ``data/external/`` (Roger's approval, section 5a, recorded with ``--approved-by``)
and records the model, which ``setup_external.py --hf-model Qwen/Qwen3-8B-Base`` downloads.  ``bench`` measures
the local model's aggregate tokens/s (the Mac-or-escalate reading, 150 tok/s).  ``sample`` renders prompts and
runs the local model ($0; tokens charged at a zero rate to ``usage.json``).  ``parse`` builds a round's candidate
table, ``stats`` its diversity figures.  ``submit`` writes a run's ``candidates.jsonl`` and submits it to the
registry, gated on the downstream (M1 + M3) estimate.  ``report`` writes the pilot readout.

This generator makes no paid API call; M1 and M3 are the platform's CLIs, printed by ``submit``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import base_model as B  # noqa: E402


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


def _rel(p: Path) -> str:
    try:
        return str(Path(p).relative_to(_REPO_ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------- fetch

def cmd_fetch(args) -> int:
    from assistant_axis.gapgen.generators.base_model import download as D
    try:
        res = D.fetch(args.only, approved_by=args.approved_by, dry_run=args.dry_run, force=args.force,
                      external_dir=args.external_dir, sources_manifest_path=args.sources_manifest,
                      git_sha=None if args.dry_run else _git_sha())
    except D.NotApproved as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost; bandwidth only):")
        for line in res.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in res.entries:
        print(f"{e['key']:8s} {e['size_bytes']:>15,d} B  sha256 {str(e.get('sha256') or '')[:16]}  "
              f"checksum {'verified' if e['checksum_verified'] else 'not published / NOT VERIFIED'}  "
              f"licence {e['licence']} ({'verified' if e['licence_verified'] else 'NOT VERIFIED'})  "
              f"{e.get('file') or e.get('dir')}")
    print(f"fetched: {', '.join(res.fetched) or 'none'}; already present: {', '.join(res.skipped) or 'none'}")
    for p in res.written:
        print(f"wrote {_rel(p)}")
    return 0 if all(e["licence_verified"] for e in res.entries) else 1


# ---------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (evaluation only)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external-dir", type=Path, default=paths.DATA_EXTERNAL)
    ap.add_argument("--sources-manifest", type=Path, default=B.SOURCES_MANIFEST_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download wiki_bio and O*NET, record the model (bandwidth only)")
    p.add_argument("--only", nargs="+", choices=("wikibio", "onet", "model"))
    p.add_argument("--approved-by", default=None,
                   help="Roger's approval of the downloads (plan section 5a), copied into the manifests")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
