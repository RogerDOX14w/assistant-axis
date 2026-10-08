#!/usr/bin/env python3
"""The psycholexical-census generator (workstream 1, generator id ``censuses``).

    uv run python data_analysis/gap_generation/census_generator.py download [--only KEY ...] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py ingest [--queue PATH] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py submit --stage {tda,allport_hi,allport_probe,extra}
        --run-id R [--every-nth N [--offset K]] [--extra-list PATH] [--transport live|batches]
        [--budget-usd 5.0] [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_01_censuses.md`` (the 2026-10-08 revision
overrides the earlier sections).  ``download`` fetches the TDA (Dataverse, CC0) and the
Allport-Odbert lists (OSF, CC BY 4.0) into ``data/external/wordlists/`` and verifies them.
``ingest`` builds ``data/candidates/censuses/census_table.jsonl`` and ``ingest_counts.json``
(needs ``setup_external.py --wn`` and ``wordfreq``).  ``submit`` writes a run's
``candidates.jsonl`` and then submits it to the registry; it prints the downstream estimate
(the platform's M1 filter and M3 novelty scorer, run afterwards by their own CLIs) and refuses
a run whose estimate exceeds ``--budget-usd`` or the $20 line without Roger's recorded go.
``report`` writes the run's ``evaluation.json`` and ``readout.md`` (counts; known-label pass
rate once the filter has run).

This generator makes no paid API call.
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
from assistant_axis.gapgen.generators import censuses as C  # noqa: E402
from assistant_axis.gapgen.generators.censuses import download as D  # noqa: E402
from assistant_axis.gapgen.generators.censuses import ingest as I  # noqa: E402
from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems  # noqa: E402
from assistant_axis.gapgen.generators.censuses.sources import ALLPORT_COLUMN_SOURCES, SOURCES  # noqa: E402


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


def cmd_download(args) -> int:
    man = D.fetch_all(dest_root=args.wordlists, only=args.only, force=args.force, dry_run=args.dry_run,
                      git_sha=None if args.dry_run else _git_sha(),
                      sources_manifest_path=args.sources_manifest)
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost):")
        for line in man.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in man.entries:
        print(f"{e['key']:16s} {e['size_bytes']:>8d} B  sha256 {e['sha256'][:16]}...  "
              f"{'verified (' + e['checksum_source'] + ')' if e['checksum_verified'] else 'NOT VERIFIED'}  "
              f"{e['licence']}  {e['file']}")
    print(f"fetched: {', '.join(man.fetched) or 'none'}; already verified: {', '.join(man.skipped) or 'none'}")
    for p in man.written:
        print(f"wrote {p}")
    return 0 if all(e["checksum_verified"] for e in man.entries) else 1


def load_inputs(wordlists: Path):
    """Parse the downloaded files (column files, merged file, TDA properties)."""
    allport = []
    for col, key in ALLPORT_COLUMN_SOURCES.items():
        p = wordlists / SOURCES[key].dest
        if not p.exists():
            raise SystemExit(f"missing {p}: run `census_generator.py download` first")
        allport += I.parse_allport_txt(p, col)
    mp = wordlists / SOURCES["allport_merged"].dest
    merged = I.parse_allport_txt(mp, None) if mp.exists() else None
    tp = wordlists / SOURCES["tda_properties"].dest
    if not tp.exists():
        raise SystemExit(f"missing {tp}: run `census_generator.py download` first")
    return allport, merged, I.parse_tda_properties(tp)


def build(args, lookups=None):
    from assistant_axis.gapgen.generators.censuses import evaluate as E
    allport, merged, tda = load_inputs(args.wordlists)
    corpus = corpus_trait_stems(args.data_dir)
    queue = queue_trait_stems(args.queue, data_dir=args.data_dir)
    rows, extra = I.build_table(allport, tda, lookups=lookups or I.default_lookups(), corpus_stems=corpus,
                                queue_stems=queue, merged=merged)
    counts = I.ingest_counts(rows, extra)
    counts["ceiling"] = E.string_ceiling(rows, corpus, queue).as_dict()
    counts["malformed_list"] = extra["malformed"]
    counts["repaired_list"] = extra["repaired"]
    return rows, counts


def print_counts(counts: dict) -> None:
    keys = ("n_rows", "n_tda", "n_allport", "n_both", "n_eligible", "per_column", "only_column", "per_stage",
            "ineligible", "per_zipf_band", "tda_below_dictionary_floor", "platform_probe", "unknown_word",
            "repaired", "malformed", "with_gloss_hint", "corpus_stem_match", "queue_stem_match", "counters",
            "ceiling")
    for k in keys:
        print(f"{k}: {json.dumps(counts.get(k), ensure_ascii=False)}")


def cmd_ingest(args) -> int:
    rows, counts = build(args)
    print_counts(counts)
    if args.dry_run:
        print(f"DRY-RUN: would write {args.table} ({len(rows)} rows) and {args.counts}")
        return 0
    backup = I.write_table(rows, args.table)
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text(json.dumps(counts, indent=2, ensure_ascii=False) + "\n", args.counts)
    print(f"wrote {args.table} ({len(rows)} rows, sha256 {I.file_sha256(args.table)[:16]}...)"
          + (f"; previous table kept as {backup}" if backup else ""))
    print(f"wrote {args.counts}")
    return 0


def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.censuses import submit as S
    table, sha = [], None
    if args.stage != "extra":
        if not args.table.exists():
            raise SystemExit(f"missing {args.table}: run `census_generator.py ingest` first")
        table = I.load_census_table(args.table)
        sha = I.file_sha256(args.table)
    manifest = D.load_manifest(args.sources_manifest)
    if not manifest and not args.dry_run:
        raise SystemExit(f"missing {args.sources_manifest}: run `census_generator.py download` first")
    S.run_submit(args.stage, args.run_id, table=table, sources_manifest=manifest, every_nth_n=args.every_nth,
                 offset=args.offset, extra_list=args.extra_list, budget_usd=args.budget_usd,
                 confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                 transport=args.transport, dry_run=args.dry_run, registry_path=args.registry,
                 candidates_dir=args.candidates_dir, table_sha256=sha,
                 table_path=_repo_rel(args.table) if args.stage != "extra" else None)
    return 0


def _repo_rel(p: Path) -> Path:
    try:
        return Path(p).resolve().relative_to(_REPO_ROOT.resolve())
    except ValueError:
        return Path(p)


def cmd_report(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import Registry
    from assistant_axis.gapgen.generators.censuses import report as R
    from assistant_axis.provenance import current_file_input
    rdir = paths.run_dir(C.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    if not (rdir / "candidates.jsonl").exists():
        raise SystemExit(f"no run at {rdir} (no candidates.jsonl)")
    table = I.load_census_table(args.table)
    counts = json.loads(args.counts.read_text(encoding="utf-8")) if args.counts.exists() else None
    reg = Registry(args.registry).fold() if args.registry.exists() else {}
    ev = R.evaluate_run(args.run_id, run_dir=rdir, table=table, ingest_counts=counts, registry_rows=reg,
                        corpus_stems=corpus_trait_stems(args.data_dir),
                        candidates_dir=args.candidates_dir or paths.DATA_CANDIDATES)
    doc = rdir / "readout.md"
    md = R.render_readout(ev, doc_path=doc, run_dir=rdir, table_path=args.table, counts_path=args.counts,
                          manifest_path=args.sources_manifest)
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {rdir / 'evaluation.json'} and {doc}")
        return 0
    inputs = [current_file_input(dep_key=k, path=pth) for k, pth in
              (("census_table", args.table), ("ingest_counts", args.counts), ("candidates", rdir / "candidates.jsonl"),
               ("run_json", rdir / "run.json"), ("registry", args.registry)) if Path(pth).exists()]
    env = json_metadata(ev, title=f"census generator evaluation, run {args.run_id}", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", rdir / "evaluation.json")
    atomic_write_text(md, doc)
    print(f"wrote {rdir / 'evaluation.json'} and {doc}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--table", type=Path, default=C.CENSUS_TABLE_PATH)
    ap.add_argument("--counts", type=Path, default=C.INGEST_COUNTS_PATH)
    ap.add_argument("--wordlists", type=Path, default=C.WORDLISTS_DIR)
    ap.add_argument("--sources-manifest", type=Path, default=C.SOURCES_MANIFEST_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("download", help="fetch and verify the census files (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("ingest", help="build census_table.jsonl and ingest_counts.json (no API cost)")
    p.add_argument("--queue", type=Path, default=None, help="seed queue (default data/seed_queue.json)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream estimate)")
    p.add_argument("--stage", required=True, choices=("tda", "allport_hi", "allport_probe", "extra"))
    p.add_argument("--run-id", required=True)
    p.add_argument("--every-nth", type=int, default=None, help="every N-th row of the stage in rank order (pilot)")
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--extra-list", type=Path, default=None, help="stage extra: one word per line")
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="how the platform will run M1 and M3 (batches: half price in the estimate)")
    p.add_argument("--budget-usd", type=float, default=5.0,
                   help="cap on the downstream estimate (M1 + M3); over it the submit is refused")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for an estimate over $20")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="evaluation.json and readout.md for a run (no API cost)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
