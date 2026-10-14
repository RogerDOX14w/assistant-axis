#!/usr/bin/env python3
"""The psycholexical-census generator (workstream 1, generator id ``censuses``).

    uv run python data_analysis/gap_generation/census_generator.py download [--only KEY ...] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py ingest [--queue PATH] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py submit --stage {tda,allport_hi,allport_probe,allport_iv,allport_rare,allport_iv_rare,extra}
        --run-id R [--every-nth N [--offset K]] [--extra-list PATH] [--transport live|batches]
        [--budget-usd 5.0] [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py report --run-id R [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py repair-check [--readings N] [--limit N] [--render N]
        [--resume] [--budget-usd 5.0] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/census_generator.py repair-check --submit --run-id R
        [--transport live|batches] [--budget-usd 5.0] [--dry-run]

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

``repair-check`` (QUESTIONS 35, Roger 2026-10-14) asks Sonnet 5.5 whether each listed one-edit repair suggestion
whose repaired word is new to the census lists is a typo or a real word in its own right
(:mod:`assistant_axis.gapgen.generators.censuses.repair_check`; outputs in ``data/candidates/censuses/repair_check/``);
with ``--submit`` it makes no call and submits the accepted repairs (verdict ``typo``) as a census run.  It is the
generator's only paid command: the estimate is printed first and capped by ``--budget-usd``, a dirty tree is refused
without ``--allow-dirty``, and every response is recorded before it is parsed.  Every other command makes no paid
API call.
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
from assistant_axis.gapgen.generators.censuses.corpus import corpus_paren_stems, corpus_trait_stems, queue_trait_stems  # noqa: E402
from assistant_axis.gapgen.generators.censuses.sources import ALLPORT_COLUMN_SOURCES, SOURCES  # noqa: E402
from assistant_axis.gapgen.generators.censuses.submit import STAGES  # noqa: E402


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
    counts["ceiling"] = E.string_ceiling(rows, corpus, queue, corpus_paren_stems(args.data_dir)).as_dict()
    counts["malformed_list"] = extra["malformed"]
    counts["repaired_list"] = extra["repaired"]
    counts["repair_suggestions_list"] = extra["repair_suggestions"]
    return rows, counts


def print_counts(counts: dict) -> None:
    keys = ("n_rows", "n_tda", "n_allport", "n_both", "n_eligible", "per_column", "only_column", "per_stage",
            "ineligible", "per_zipf_band", "tda_below_dictionary_floor", "platform_probe", "unknown_word",
            "with_oewn_lemma", "unknown_word_with_oewn_lemma", "repaired", "malformed", "with_gloss_hint",
            "corpus_stem_match", "queue_stem_match", "counters", "ceiling")
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


def platform_dirty_files() -> Optional[list[str]]:
    """``runs.platform_dirty_files`` under this module's name, so that tests can replace it."""
    from assistant_axis.gapgen.runs import platform_dirty_files as dirty
    return dirty()


def _client():
    """The Anthropic client, direct key (tests replace this)."""
    from assistant_axis.gapgen.generators.ipip.naming import make_client
    return make_client()


def _senses():
    """OEWN's sense lookup for the gloss hints of submitted repairs (the table's rows get theirs the same way), or
    None when OEWN or wordfreq is not installed (the candidates then go without a hint)."""
    try:
        return I.default_lookups().senses
    except (SystemExit, ImportError) as exc:
        print(f"note: no OEWN gloss hints ({exc})")
        return None


def cmd_repair_check(args) -> int:
    import asyncio
    import logging

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort, resume_usage
    from assistant_axis.gapgen.generators.censuses import repair_check as RC
    from assistant_axis.gapgen.runs import dirty_refusal
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import MultiModelUsage
    out = Path(args.out_dir) if args.out_dir else Path(args.counts).parent / "repair_check"
    resp, usage_path = out / RC.RESPONSES_NAME, out / RC.USAGE_NAME
    if not args.counts.exists() or not args.table.exists():
        raise SystemExit(f"missing {args.counts} or {args.table}: run `census_generator.py ingest` first")
    counts = json.loads(args.counts.read_text(encoding="utf-8"))
    table = I.load_census_table(args.table)
    selected, sel = RC.select_suggestions(counts.get("repair_suggestions_list") or [], table)
    print(f"{sel['n_suggestions']} repair suggestions listed; {sel['n_held_elsewhere']} point to a word the census "
          f"lists already hold; {sel['n_new']} to a new word (by kind {json.dumps(sel['by_kind_new'])})")
    if args.limit is not None:
        selected = selected[:args.limit]
        print(f"--limit {args.limit}: the first {len(selected)} in list order")
    try:
        rubric = RC.load_rubric()
    except RC.RubricNotPinned as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    items = RC.build_items(selected, table, rubric["text"])
    records = RC.read_records(resp)
    answers = RC.answers_on_record(records, model=args.model)
    if args.submit:
        return _repair_submit(args, RC, items, answers, sel, rubric)
    if records and not args.resume:
        print(f"REFUSED: {len(records)} responses are on record in {resp}; pass --resume to reuse them (only the "
              f"suggestions without an answer are sent)", file=sys.stderr)
        return 2
    todo = [(it, r) for it in items for r in range(args.readings) if (it.request_sha256, r) not in answers]
    est = RC.estimate(len(todo), args.model)
    print(f"{len(items)} suggestions x {args.readings} reading(s); {len(items) * args.readings - len(todo)} answers "
          f"on record; {len(todo)} calls to make:")
    print(est.format())
    confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                     confirmed_by=args.confirmed_by)
    refused, dirty_rec = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if refused and not args.dry_run:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2
    if refused:
        print(f"DRY-RUN: the real run would be REFUSED: {refused}")
    if args.render:
        print(f"=== system turn: {rubric['name']} version {rubric['version']} (sha {rubric['sha256'][:12]}...), "
              f"sent byte for byte ===")
        print(rubric["text"])
        print(f"=== user turns, the first {min(args.render, len(items))} of {len(items)} ===")
        for it in items[:args.render]:
            print(it.user)
    if args.dry_run:
        print(f"DRY-RUN: would make {len(todo)} calls on {args.model} (max_tokens {RC.MAX_TOKENS}, no temperature) "
              f"and write {resp}, {usage_path}, {out / RC.VERDICTS_NAME}, {out / RC.READOUT_NAME}")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    prev = resume_usage(MultiModelUsage.load_or_create(usage_path), records, where=str(out))
    usage = GuardedUsage(per_model=dict(prev.per_model), budget_usd=prev.total_cost_usd + args.budget_usd,
                         usage_path=usage_path)
    res = None
    try:
        if todo:
            res = asyncio.run(RC.check(todo, client=_client(), rubric=rubric, model=args.model, usage=usage,
                                       responses_path=resp))
    finally:
        usage.write_json(usage_path)
    if res is not None:
        warn_if_low_parse_rate(label=f"census repair check:{args.model}", n_ok=res.n_ok, n_total=res.n_calls,
                               logger_obj=logging.getLogger("census_generator"),
                               extra=f"failed calls by kind {res.error_kinds}")
        print(f"{res.n_ok} of {res.n_calls} calls answered; failed {res.error_kinds}; {usage.plain().log_line()}"
              + ("; STOPPED at the budget" if res.stopped_by_budget else ""))
    answers = RC.answers_on_record(RC.read_records(resp), model=args.model)
    rows = RC.verdict_rows(items, answers, args.readings)
    files = {"counts": args.counts, "rubric": _REPO_ROOT / rubric["file"], "usage": usage_path, "responses": resp,
             "verdicts": out / RC.VERDICTS_NAME}
    doc = {**RC.rows_as_json(rows, selection=sel, rubric=rubric, model=args.model, readings=args.readings),
           "dirty_check": dirty_rec, "limit": args.limit, "cost_usd_on_record": round(usage.total_cost_usd, 4)}
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", out / RC.VERDICTS_NAME)
    md = RC.render_readout(rows, selection=sel, rubric=rubric, model=args.model, readings=args.readings,
                           usage_usd=usage.total_cost_usd, doc_path=out / RC.READOUT_NAME, files=files)
    atomic_write_text(md, out / RC.READOUT_NAME)
    print(f"verdicts: {json.dumps(RC.counts_by_verdict(rows))}")
    print(f"wrote {resp}, {usage_path}, {out / RC.VERDICTS_NAME}, {out / RC.READOUT_NAME}")
    return 2 if res is not None and res.stopped_by_budget else 0


def _repair_submit(args, RC, items, answers, sel, rubric) -> int:
    """``repair-check --submit``: no call; the accepted repairs on record as a census run (candidates.jsonl, then the
    registry), with the downstream estimate gated by ``--budget-usd`` as ``submit`` gates it."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen import start_run, submit_candidates
    from assistant_axis.gapgen.cost import confirm_or_abort
    from assistant_axis.gapgen.generators.censuses import submit as S
    from dataclasses import asdict

    from assistant_axis.gapgen.paths import check_id, run_dir
    if not args.run_id:
        raise SystemExit("--submit needs --run-id")
    check_id(args.run_id, "run_id")
    rows = RC.verdict_rows(items, answers, args.readings)
    missing = [r for r in rows if r["verdict"] is None]
    if missing:
        print(f"REFUSED: {len(missing)} of {len(rows)} suggestions have no answer on record (first: "
              f"{', '.join(r['entry'] for r in missing[:5])}); run `census_generator.py repair-check --resume` first",
              file=sys.stderr)
        return 2
    by = RC.counts_by_verdict(rows)
    print(f"verdicts on record: {json.dumps(by)}")
    cands = RC.candidates_for(rows, args.run_id, senses=_senses())
    if not cands:
        print("no accepted repairs (verdict typo): nothing to submit")
        return 0
    est = S.estimate_downstream_usd(len(cands), transport=args.transport)
    print(est.format())
    confirm_or_abort(est.total_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                     confirmed_by=args.confirmed_by)
    target = run_dir(C.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    follow = S.followup_commands(args.run_id, est, candidates_path=target / "candidates.jsonl")[:3]
    for c in cands:
        print(f"  {c.surface:24s} {c.source_ref}")
    if args.dry_run:
        print(f"DRY-RUN: would write {target}/candidates.jsonl ({len(cands)} candidates), submit them to "
              f"{args.registry}, and write keys.txt, submit_report.json, run.json, usage.json there")
        for c in follow:
            print(f"  then: {c}")
        return 0
    run_args = {"stage": "repair_check", "stage_rule": "the repair suggestions of ingest_counts.json whose repaired "
                "word is new to the census lists and that the repair check judged a typo (QUESTIONS 35)",
                "n": len(cands), "n_checked": len(rows), "verdicts": by, "readings": args.readings,
                "model": args.model, "rubric": rubric["name"], "rubric_version": rubric["version"],
                "prompt_sha256": rubric["sha256"], "transport": args.transport, "budget_usd": args.budget_usd,
                "estimate": asdict(est), "selection": dict(sel),
                "check_dir": str(_repo_rel(Path(args.out_dir) if args.out_dir else Path(args.counts).parent / "repair_check")),
                "counts": str(_repo_rel(args.counts)), "table": str(_repo_rel(args.table)),
                "table_sha256": I.file_sha256(args.table)}
    ctx = start_run(C.GENERATOR, args.run_id, args=run_args, candidates_dir=args.candidates_dir)
    ctx.confirmed_by = args.confirmed_by
    ctx.record_candidates(cands)          # candidates.jsonl first (the tracked record of the run)
    rep = submit_candidates(cands, registry_path=args.registry)
    atomic_write_text("".join(k + "\n" for k in rep.keys), ctx.dir / "keys.txt")
    rep_d = {k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}
    atomic_write_text(json.dumps(rep_d, indent=2) + "\n", ctx.dir / "submit_report.json")
    ctx.finish()
    print(f"registry {args.registry}: {json.dumps(rep_d)}")
    print(f"wrote {ctx.dir}/candidates.jsonl, keys.txt, submit_report.json, run.json, usage.json")
    for c in follow:
        print(f"  then: {c}")
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
    p.add_argument("--stage", required=True, choices=STAGES)
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

    from assistant_axis.gapgen.generators.censuses.repair_check import DEFAULT_MODEL as RC_MODEL
    p = sub.add_parser("repair-check", help="Sonnet 5.5 on the listed repair suggestions whose repaired word is new "
                                            "(QUESTIONS 35; paid); --submit sends the accepted repairs (no call)")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="responses.jsonl, usage.json, verdicts.json, readout.md (default: repair_check/ beside "
                        "--counts, data/candidates/censuses/repair_check)")
    p.add_argument("--model", default=RC_MODEL)
    p.add_argument("--readings", type=int, default=1,
                   help="answers per suggestion, combined by majority (a tie is unsure); default 1")
    p.add_argument("--limit", type=int, default=None, help="only the first N selected suggestions (a pilot)")
    p.add_argument("--render", type=int, default=0, metavar="N", help="print the system turn and N user turns")
    p.add_argument("--resume", action="store_true",
                   help="reuse the answers on record (by request sha, reading and model); refused without it when "
                        "responses are on record")
    p.add_argument("--submit", action="store_true",
                   help="no call: submit the accepted repairs on record as census run --run-id")
    p.add_argument("--run-id", default=None)
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="--submit: how the platform will run M1 and M3 (the downstream estimate)")
    p.add_argument("--budget-usd", type=float, default=5.0,
                   help="cap on the estimate: the check's calls, or with --submit the downstream M1 + M3 estimate")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")
    p.add_argument("--allow-dirty", action="store_true",
                   help="run although the platform's own code or prompt paths have uncommitted changes")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_repair_check)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
