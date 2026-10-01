#!/usr/bin/env python3
"""Download the trait-gap platform's external data into the repository.

    uv run python data_analysis/gap_generation/setup_external.py --wn [--dry-run]

``--wn`` installs Open English WordNet 2024 (about 100 MB) into
``data/external/wn/`` through the ``wn`` package, whose data directory is
pinned in-tree by ``assistant_axis.gapgen.wordnet`` before anything is
looked up or downloaded.  Idempotent: a second run finds the lexicon and
downloads nothing.

    uv run python data_analysis/gap_generation/setup_external.py --hf-model BAAI/bge-large-en-v1.5 [--dry-run]
    uv run python data_analysis/gap_generation/setup_external.py --hf-model google/embeddinggemma-300m

``--hf-model ID`` (repeatable) pre-fetches an M2 local embedding model into
``data/external/hf/`` with ``huggingface_hub.snapshot_download(...,
cache_dir=data/external/hf, allow_patterns=...)``, fetching only the files a
load needs (``assistant_axis.gapgen.embed.HF_ALLOW_PATTERNS``: config,
tokenizer, ``model.safetensors``, the sentence-transformers module configs;
no ONNX, OpenVINO or ``.bin`` duplicates).  The Hugging Face token comes from
``$HF_TOKEN`` (``.env`` through ``load_dotenv``; EmbeddingGemma is gated);
nothing is read from or written under the home directory, because
``assistant_axis.gapgen`` pins ``HF_HOME`` / ``HF_HUB_CACHE`` to
``data/external/hf`` before ``huggingface_hub`` is imported.  ``--dry-run``
prints the target and patterns and makes no network call.

No API cost.  ``data/external/`` is gitignored.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import embed as ge  # noqa: E402
from assistant_axis.gapgen import wordnet as gw  # noqa: E402  (pins the wn data dir)


def _dir_size_mb(p: Path) -> float:
    if not p.exists():
        return 0.0
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6


def fetch_hf_model(model_id: str, *, dry_run: bool = False) -> int:
    """Download ``model_id`` into ``data/external/hf`` (only the allowed files)."""
    if model_id not in ge.HF_ALLOW_PATTERNS:
        print(f"unknown model {model_id!r}: add its allow patterns to gapgen/embed.py:HF_ALLOW_PATTERNS first "
              f"(known: {', '.join(ge.HF_ALLOW_PATTERNS)})", file=sys.stderr)
        return 2
    target = paths.pin_hf_cache()
    allow, ignore = ge.HF_ALLOW_PATTERNS[model_id], ge.HF_IGNORE_PATTERNS
    present = ge.hf_snapshot_present(model_id)
    print(f"{model_id}: cache_dir {target}; allow {allow}; ignore {ignore}; "
          f"{'snapshot present' if present else 'not downloaded yet'}")
    if dry_run:
        print(f"DRY-RUN: would snapshot_download({model_id!r}, cache_dir={str(target)!r}, allow_patterns=..., "
              f"ignore_patterns=...)")
        return 0
    import os

    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    from huggingface_hub import snapshot_download
    path = snapshot_download(model_id, cache_dir=str(target), allow_patterns=allow, ignore_patterns=ignore,
                             token=os.environ.get("HF_TOKEN") or None)
    snap = Path(path)
    if not snap.resolve().is_relative_to(_REPO_ROOT.resolve()):
        print(f"REFUSED: the snapshot landed outside the repository: {snap}", file=sys.stderr)
        return 1
    files = sorted(p.relative_to(snap) for p in snap.rglob("*") if p.is_file())
    print(f"installed {model_id} at {snap.relative_to(_REPO_ROOT)}: {len(files)} files, "
          f"{_dir_size_mb(ge.hf_snapshot_dir(model_id) / 'blobs'):.0f} MB")
    for f in files:
        print(f"  {f}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wn", action="store_true", help="install OEWN 2024 into data/external/wn/")
    ap.add_argument("--hf-model", action="append", default=[], metavar="ID",
                    help="pre-fetch a Hugging Face embedding model into data/external/hf/ (repeatable); one of: "
                         + ", ".join(ge.HF_ALLOW_PATTERNS))
    ap.add_argument("--dry-run", action="store_true", help="print what would be downloaded, download nothing")
    args = ap.parse_args(argv)
    if not args.wn and not args.hf_model:
        ap.error("nothing to do: pass --wn and/or --hf-model ID")
    rc = 0
    for model_id in args.hf_model:
        rc = max(rc, fetch_hf_model(model_id, dry_run=args.dry_run))
    if not args.wn:
        return rc

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
