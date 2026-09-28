#!/usr/bin/env python3
"""Download the trait-gap platform's external data into the repository.

    uv run python data_analysis/gap_generation/setup_external.py --wn [--dry-run]

``--wn`` installs Open English WordNet 2024 (about 100 MB) into
``data/external/wn/`` through the ``wn`` package, whose data directory is
pinned in-tree by ``assistant_axis.gapgen.wordnet`` before anything is
looked up or downloaded.  Idempotent: a second run finds the lexicon and
downloads nothing.

``--hf-model ID`` (pre-fetching the M2 local embedding model into
``data/external/hf/``) belongs to milestone M2 and is not implemented yet.

No API cost.  ``data/external/`` is gitignored.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import wordnet as gw  # noqa: E402  (pins the wn data dir)


def _dir_size_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wn", action="store_true", help="install OEWN 2024 into data/external/wn/")
    ap.add_argument("--hf-model", help="(M2, not implemented) pre-fetch a Hugging Face model into data/external/hf/")
    ap.add_argument("--dry-run", action="store_true", help="print what would be downloaded, download nothing")
    args = ap.parse_args(argv)
    if not args.wn and not args.hf_model:
        ap.error("nothing to do: pass --wn (and, from M2, --hf-model ID)")
    if args.hf_model:
        print("--hf-model is part of milestone M2 and is not implemented yet", file=sys.stderr)
        return 2

    target = paths.wn_data_dir()
    print(f"wn data directory: {target}")
    if args.dry_run:
        present = (target / "wn.db").exists() and gw.oewn_installed()
        print(f"DRY-RUN: {gw.OEWN_LEXICON} {'already installed' if present else 'would be downloaded (about 100 MB)'}"
              f" into {target}")
        return 0
    ok = gw.ensure_oewn()
    if not ok:
        print(f"FAILED to install {gw.OEWN_LEXICON}", file=sys.stderr)
        return 1
    import wn
    lex = wn.lexicons(lexicon=gw.OEWN_LEXICON)[0]
    print(f"installed: {lex.id}:{lex.version} ({lex.label}); {_dir_size_mb(target):.0f} MB in {target}")
    print(f"wn {wn.__version__}; database {wn.config.database_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
