#!/usr/bin/env python3
"""The alignment sweep (workstream 8, generator id ``alignment_sweep``).

    uv run python data_analysis/gap_generation/alignment_sweep.py fetch [--only KEY ...] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py chunk [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py extract --run-id R --variant A|B [--chunks N --seed S]
        [--sources KEY ...] [--reuse-from RUN] [--render CHUNK_ID ...] [--budget-usd 4] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py dedupe --run-id R [--threshold T | --tune]
        [--pairs-for-labeling N] [--embedder openai|hash] [--budget-usd 1] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py submit --run-id R [--budget-usd 5]
        [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py gate --run-id R [--gold-only] [--budget-usd 1.5]
        [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py probe --run-id R [--budget-usd 0.5] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py report --run-id R [--gold] [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_08_alignment_sweep.md``.  ``fetch`` downloads the sources into
``data/external/alignment_sweep/`` (git-ignored) with a manifest (also tracked as
``data/candidates/alignment_sweep/sources_manifest.json``); ``chunk`` splits them into ``chunks.jsonl``; ``extract``
asks Sonnet 5.5 for the dispositions of each chunk and rewrites mechanism items; ``dedupe`` groups the glosses;
``submit`` writes the run's ``candidates.jsonl`` and submits it; ``gate`` and ``probe`` add the enactability
verdicts and the Qwen label probe; ``report`` writes the readout.  Every paid command prints its estimate, takes
``--budget-usd`` as a hard cap, writes ``usage.json``, refuses uncommitted platform code without ``--allow-dirty``,
and runs live (every estimate is under the $20 line).  ``--dry-run`` prints the plan, the estimate and the first
three prompts as sent, and writes and calls nothing.
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
from assistant_axis.gapgen.generators import alignment_sweep as AS  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep import chunk as CH  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep import fetch as F  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES  # noqa: E402


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


# --------------------------------------------------------------------------- fetch, chunk

def cmd_fetch(args) -> int:
    man = F.fetch_all(only=args.only, force=args.force, dry_run=args.dry_run, dest_root=args.external_dir,
                      sources_manifest_path=args.sources_manifest, git_sha=None if args.dry_run else _git_sha())
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost):")
        for line in man.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in man.entries:
        print(f"{e['key']:22s} {e['size_bytes']:>8d} B  sha256 {e['sha256'][:16]}...  {e['license'] or 'no licence'}"
              f"{' (read-only)' if e['read_only'] else ''}  pin {e['version_pin']}  {e['file']}")
        print(f"{'':22s} licence line found: {e.get('license_line_found')!r}")
    print(f"fetched: {', '.join(man.fetched) or 'none'}; already present: {', '.join(man.skipped) or 'none'}")
    for p in man.written:
        print(f"wrote {p}")
    return 0


def cmd_chunk(args) -> int:
    manifest = F.load_manifest(Path(args.external_dir) / AS.FETCH_MANIFEST_NAME)
    if not manifest:
        raise SystemExit(f"no {AS.FETCH_MANIFEST_NAME} in {args.external_dir}: run `alignment_sweep.py fetch` first")
    chunks = CH.build_all(manifest, max_tokens=args.max_tokens)
    for k, v in CH.counts(chunks).items():
        print(f"{k:22s} {v['n_chunks']:>4d} chunks  ~{v['n_tokens_est']:>7,d} tokens  (largest ~{v['max_tokens_est']:,d})")
    out = Path(args.external_dir) / AS.CHUNKS_NAME
    if args.dry_run:
        print(f"DRY-RUN: would write {out}")
        return 0
    CH.write_chunks(chunks, out)
    print(f"wrote {out} ({len(chunks)} chunks)")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external-dir", type=Path, default=AS.EXTERNAL_DIR)
    ap.add_argument("--sources-manifest", type=Path, default=AS.SOURCES_MANIFEST_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download the sources and write the manifests (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("chunk", help="split the fetched sources into chunks.jsonl (no API cost)")
    p.add_argument("--max-tokens", type=int, default=CH.MAX_CHUNK_TOKENS)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_chunk)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
