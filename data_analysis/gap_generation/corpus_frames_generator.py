#!/usr/bin/env python3
"""The corpus-frames generator (workstream 5, generator id ``corpus_frames``).

    uv run python data_analysis/gap_generation/corpus_frames_generator.py locate [--tier all] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py stream --approved-by '<Roger, date>'
        [--tier all] [--parallel 4] [--resume] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py fetch-text --approved-by '<Roger, date>'
        [--sources pippa,cards] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py extract-text [--sources pippa,cards]
        [--delete-raw] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py table [--tier all] [--year-min 1920]
        [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py evaluate [--cutoffs 500,1000,3000,10000]
        [--ordering auto|volumes|lift] [--pilot-run R [--yield-min 0.4] [--tv-max 0.5] [--keep-frames A,B]
        [--drop-frames C]] [--title T] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py submit --run-id R
        (--top-per-frame 25 | --kept-target 300 [--kept-share S] [--all-frames] [--no-count-siblings])
        [--transport live|batches] [--budget-usd 8] [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/corpus_frames_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_05_corpus_frames.md``.  ``locate`` head-peeks the Google Books
n-gram shards (about 3 MB of range requests for both tiers) and writes ``shard_plan.json`` with the shard count and GB;
``stream`` streams the planned shards once, keeping only the matching lines, and **refuses without
``--approved-by``** (the download rule: over 2 GB); ``fetch-text`` downloads the two text corpora (about 260 MB,
refused without ``--approved-by``) and ``extract-text`` runs the text frames over them; ``table`` builds
``frames_table.jsonl`` (git-ignored) and ``frame_stats.json``; ``evaluate`` the recovery curves under both orderings
beside the frequency baselines, the ordering choice, the unfound labels, the registry overlap, and after the pilot
(``--pilot-run``) every frame's yield, net filter, unique kept rows and keep verdict; ``submit`` writes a run's
``candidates.jsonl`` and submits it, gated on the downstream (M1 + M3) estimate; ``report`` reads a run's M1 and M3
results back into ``report.md``, ``roger_sample.md`` and ``roger_first_hour.md``.

No command makes a paid call (the generator makes none; M1 and M3 are the platform's CLIs, printed by ``submit``),
and ``submit`` is the only one that touches the registry.  Every dry run writes nothing; ``locate --dry-run`` and
``stream --dry-run`` make no request.
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
from assistant_axis.gapgen.generators import corpus_frames as G  # noqa: E402
from assistant_axis.gapgen.generators.corpus_frames import books as B  # noqa: E402
from assistant_axis.gapgen.generators.corpus_frames import frames as F  # noqa: E402
from assistant_axis.gapgen.generators.corpus_frames import text as X  # noqa: E402

#: Requests a prefix costs in ``locate`` (a binary search over ~6,800 shards, then a gallop): the dry run's figure.
PEEKS_PER_PREFIX = 15


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


# ---------------------------------------------------------------------------- seams (tests replace these)

def _fetcher():  # pragma: no cover - the network
    return B.HttpFetcher()


def _text_fetcher():  # pragma: no cover - the network
    return X.HttpTextFetcher()


def _lookups():  # pragma: no cover - wordfreq and the OEWN database
    from assistant_axis.gapgen.generators.corpus_frames.table import default_lookups
    return default_lookups()


def _universe():  # pragma: no cover - the OEWN database
    from assistant_axis.gapgen import wordnet as gw
    if not gw.oewn_installed():
        return None
    from assistant_axis.gapgen.generators.masked_lm.wordlist import oewn_candidates
    return oewn_candidates()


def _zipf():  # pragma: no cover - wordfreq
    from assistant_axis.gapgen.freq import zipf_info
    return lambda w: zipf_info(w).zipf_min


def _review_rate():  # pragma: no cover - reads the review logs
    from assistant_axis.gapgen.generators.corpus_frames.submit import review_terms_per_hour
    return review_terms_per_hour("measured")


# ---------------------------------------------------------------------------- shared

def _envelope(payload, *, title: str, inputs=None) -> dict:
    from assistant_axis import json_metadata
    return json_metadata(payload, title=title, inputs=inputs or [])


def _write_json(doc, path: Path) -> None:
    from assistant_axis.atomic_io import atomic_write_text
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", Path(path))


def _read_json(path: Path) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("result", d) if isinstance(d, dict) and "_provenance" in d else d


def _out(args, name: str) -> Path:
    return Path(args.out_dir) / name


def _traits_dir(args) -> Path:
    """Where the readouts link a corpus trait to its file."""
    return Path(args.data_dir) / "traits" / "instructions"


def _all_frames(tier: str = "all") -> dict:
    """Every frame the table may hold: the Books bank's tier and every text frame."""
    out = {f.id: f for f in F.frames_for(tier)}
    out.update({f.id: f for f in X.text_frames()})
    return out


def _corpus(args):
    from assistant_axis.gapgen.generators.censuses.corpus import (corpus_renamed_from, corpus_trait_stems,
                                                                  queue_trait_stems)
    return (corpus_trait_stems(args.data_dir), corpus_renamed_from(args.data_dir),
            queue_trait_stems(args.queue_path, data_dir=args.data_dir))


def _registry_rows(args) -> dict:
    from assistant_axis.gapgen.registry import Registry
    return Registry(args.registry).fold() if Path(args.registry).exists() else {}


def _tagged_table(args):
    """The table with the registry's current tags (the table's own were the registry's when it was built)."""
    from assistant_axis.gapgen.generators.corpus_frames import table as T
    path = _out(args, "frames_table.jsonl")
    if not path.exists():
        return None, path
    rows = T.load_frames_table(path)
    corpus, renamed, queue = _corpus(args)
    T.tag_rows(rows, corpus_stems=corpus, renamed=renamed, queue_stems=queue,
               registry=T.registry_index(_registry_rows(args)))
    return rows, path


# ---------------------------------------------------------------------------- locate / stream

def cmd_locate(args) -> int:
    frames = F.frames_for(args.tier)
    prefixes = sorted({(f.n, f.key) for f in frames})
    if args.dry_run:
        for n, key in prefixes:
            fs = [f.id for f in frames if (f.n, f.key) == (n, key)]
            print(f"{n}-grams '{key}': {', '.join(fs)}")
        print(f"DRY-RUN: would head-peek the {B.N_SHARDS[3]:,} 3-gram and {B.N_SHARDS[4]:,} 4-gram shards for "
              f"{len(prefixes)} prefixes of {len(frames)} frames (tier {args.tier}): about "
              f"{PEEKS_PER_PREFIX * len(prefixes)} range requests of {B.HEAD_PEEK_BYTES} bytes (about "
              f"{PEEKS_PER_PREFIX * len(prefixes) * B.HEAD_PEEK_BYTES / 1e6:.1f} MB) and one HEAD request per shard "
              f"found, then write {_rel(_out(args, 'shard_plan.json'))}; no request made")
        return 0
    plan = B.shard_plan(frames, fetch=_fetcher(), tier=args.tier)
    for s in plan.shards:
        print(f"  {s.name}: {s.bytes / 1e9:.3f} GB, head '{s.head}', frames {', '.join(s.frames)}")
    print(f"tier {args.tier}: **{plan.n_shards} shards, {plan.total_gb} GB** to stream "
          f"({plan.n_head_peeks} head-peeks, {plan.head_peek_bytes / 1e6:.2f} MB fetched)")
    _write_json(_envelope(plan.as_dict(), title=f"corpus-frames shard plan, tier {args.tier}"),
                _out(args, "shard_plan.json"))
    print(f"wrote {_rel(_out(args, 'shard_plan.json'))}")
    return 0


def _load_plan(args):
    p = _out(args, "shard_plan.json")
    if not p.exists():
        print(f"no {_rel(p)}: run `locate` first", file=sys.stderr)
        return None
    return B.ShardPlan.from_dict(_read_json(p))


def _plan_for_tier(plan, tier: str):
    """The plan restricted to the frames of ``tier`` (a tier-1 stream from a plan located for both tiers)."""
    want = {f.id for f in F.frames_for(tier)}
    missing = sorted(want - set(plan.frames()))
    if missing:
        raise SystemExit(f"the shard plan (tier {plan.tier}) does not cover {', '.join(missing)}: run "
                         f"`locate --tier {tier}` first")
    shards = []
    for s in plan.shards:
        fs = [f for f in s.frames if f in want]
        if fs:
            shards.append(B.ShardEntry(n=s.n, index=s.index, url=s.url, bytes=s.bytes, frames=fs, head=s.head))
    total = sum(s.bytes for s in shards)
    return B.ShardPlan(tier=tier, bank_sha256=plan.bank_sha256, shards=shards,
                       frame_spans={k: v for k, v in plan.frame_spans.items() if k in want}, n_shards=len(shards),
                       total_bytes=total, total_gb=round(total / 1e9, 2), head_peek_bytes=plan.head_peek_bytes,
                       n_head_peeks=plan.n_head_peeks, n_head_requests=plan.n_head_requests, made_at=plan.made_at,
                       base_url=plan.base_url)


def cmd_stream(args) -> int:
    if not args.dry_run and not (args.approved_by or "").strip():
        print("refused: the Books stream is a download over 2 GB; run it only after Roger's go, naming it with "
              "--approved-by '<Roger, date>' (plan 05 open decision 1)", file=sys.stderr)
        return 2
    plan = _load_plan(args)
    if plan is None:
        return 2
    plan = _plan_for_tier(plan, args.tier)
    if plan.bank_sha256 != F.bank_sha256():
        print(f"WARNING: the shard plan was located under bank {plan.bank_sha256[:12]}, the bank is now "
              f"{F.bank_sha256()[:12]}: run `locate` again if a frame's prefix changed", file=sys.stderr)
    try:
        rep = B.run_stream(plan, approved_by=args.approved_by, fetch=None if args.dry_run else
                           _fetcher(), frames_by_id=F.FRAME_BY_ID, external_dir=args.external_dir, resume=args.resume,
                           force=args.force, parallel=args.parallel, dry_run=args.dry_run, git_sha=_git_sha(),
                           sources_manifest_path=None if args.dry_run else args.sources_manifest)
    except B.NotApproved as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        for line in rep.dry_run_lines:
            print(line)
        print("DRY-RUN: no request made, nothing written")
        return 0
    print(f"streamed {len(rep.streamed)} shards ({rep.bytes_streamed / 1e9:.2f} GB of {rep.bytes_planned / 1e9:.2f} "
          f"GB planned), {len(rep.skipped)} skipped, {len(rep.failed)} failed; extracts: "
          + ", ".join(f"{k} {v['lines']}" for k, v in rep.extracts.items()))
    print(f"wrote {_rel(Path(rep.manifest_path))} and {_rel(args.sources_manifest)}")
    if rep.failed:
        print(f"FAILED shards: {', '.join(sorted(rep.failed))}; rerun with --resume", file=sys.stderr)
        return 1
    return 0


# ---------------------------------------------------------------------------- text corpora

def _sources(args) -> list[str]:
    return [s.strip() for s in args.sources.split(",") if s.strip()]


def cmd_fetch_text(args) -> int:
    try:
        rep = X.fetch_text(_sources(args), approved_by=args.approved_by, fetch=None if args.dry_run else
                           _text_fetcher(), text_dir=args.text_dir, force=args.force, dry_run=args.dry_run,
                           git_sha=_git_sha(), sources_manifest_path=None if args.dry_run else args.sources_manifest)
    except X.NotApproved as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        for line in rep.dry_run_lines:
            print(line)
        print("DRY-RUN: no request made, nothing written")
        return 0
    print(f"fetched {rep.fetched or 'nothing'}, skipped {rep.skipped or 'nothing'}; "
          + ", ".join(f"{e['key']} {e['size_bytes'] / 1e6:.1f} MB" for e in rep.entries))
    return 0


def cmd_extract_text(args) -> int:
    stats = X.run_extract(text_dir=args.text_dir, sources=_sources(args), delete_raw=args.delete_raw,
                          dry_run=args.dry_run)
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(X.extract_dir(args.text_dir))}/<frame>.tsv for "
              f"{len(stats.get('frames') or {})} frames" + (" and delete the downloads" if args.delete_raw else ""))
        return 0
    if not stats.get("sources"):
        return 2
    print(f"wrote {_rel(X.extract_dir(args.text_dir))} ({len(stats['frames'])} frames)"
          + (f"; deleted {', '.join(stats['deleted_raw'])}" if stats.get("deleted_raw") else ""))
    return 0


# ---------------------------------------------------------------------------- table

def _hits(args) -> tuple[dict, dict]:
    """``({frame key: [Hit]}, {frame key: frame})`` from every extract present."""
    from assistant_axis.gapgen.generators.corpus_frames.text import read_text_extract, text_extract_paths
    frames = _all_frames(args.tier)
    hits, used = {}, {}
    for fid, p in sorted(B.extract_paths(args.external_dir, [f.id for f in F.frames_for(args.tier)]).items()):
        hits[fid] = B.read_extract(p, F.FRAME_BY_ID[fid], year_min=args.year_min)
        used[fid] = F.FRAME_BY_ID[fid]
    for key, p in text_extract_paths(args.text_dir).items():
        if key in frames:
            hits[key] = read_text_extract(p)
            used[key] = frames[key]
    return hits, used


def cmd_table(args) -> int:
    from assistant_axis.gapgen.generators.corpus_frames import table as T
    from assistant_axis.provenance import current_file_input
    hits, frames = _hits(args)
    if not hits:
        print(f"no extracts under {_rel(args.external_dir)} or {_rel(X.extract_dir(args.text_dir))}: run `stream` "
              f"(and `extract-text`) first", file=sys.stderr)
        return 2
    corpus, renamed, queue = _corpus(args)
    counts: dict = {}
    rows = T.build_table(hits, frames=frames, lookups=_lookups(), corpus_stems=corpus, renamed=renamed,
                         queue_stems=queue, registry=T.registry_index(_registry_rows(args)), counts_out=counts)
    tc = T.table_counts(rows)
    print(json.dumps(tc))
    path = _out(args, "frames_table.jsonl")
    plan_p, man_p = _out(args, "shard_plan.json"), Path(args.external_dir) / G.DOWNLOAD_MANIFEST_NAME
    text_stats_p = X.extract_dir(args.text_dir) / X.EXTRACT_STATS_NAME
    stats = T.frame_stats(rows, frames=frames, counts=counts,
                          shard_plan=_read_json(plan_p) if plan_p.exists() else None,
                          manifest=json.loads(man_p.read_text()) if man_p.exists() else None,
                          text_stats=json.loads(text_stats_p.read_text()) if text_stats_p.exists() else None)
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(path)} ({len(rows)} rows) and {_rel(_out(args, 'frame_stats.json'))} "
              f"({len(stats)} frames)")
        return 0
    backup = T.write_table(rows, path)
    sha = T.file_sha256(path)
    inputs = [current_file_input(dep_key=f"extract_{k.replace('.', '_')}", path=p) for k, p in
              list(B.extract_paths(args.external_dir, [f for f in frames if f in F.FRAME_BY_ID]).items())
              + list(X.text_extract_paths(args.text_dir).items())]
    payload = {"table_sha256": sha, "bank_sha256": F.bank_sha256(), "text_bank_sha256": X.text_bank_sha256(),
               "year_min": args.year_min, "table_counts": tc, "frames": stats}
    _write_json(_envelope(payload, title="corpus-frames per-frame statistics", inputs=inputs),
                _out(args, "frame_stats.json"))
    print(f"wrote {_rel(path)} ({len(rows)} rows, sha256 {sha[:16]}...)"
          + (f"; previous table kept as {_rel(backup)}" if backup else "")
          + f" and {_rel(_out(args, 'frame_stats.json'))}")
    return 0


# ---------------------------------------------------------------------------- evaluate

def _frame_types(frames: dict) -> dict:
    return {k: f.type for k, f in frames.items()}


def cmd_evaluate(args) -> int:
    from assistant_axis.gapgen.generators.corpus_frames import evaluate as E
    from assistant_axis.gapgen.generators.corpus_frames import report as R
    from assistant_axis.gapgen.generators.corpus_frames import table as T
    from assistant_axis.gapgen.generators.masked_lm.evaluate import corpus_labels, queue_labels
    from assistant_axis.provenance import current_file_input
    table, path = _tagged_table(args)
    if table is None:
        print(f"missing {_rel(path)}: run `table` first", file=sys.stderr)
        return 2
    stats_p = _out(args, "frame_stats.json")
    stats_doc = _read_json(stats_p) if stats_p.exists() else {"frames": []}
    frames = _all_frames("all")
    # a frame with no filler above the floor gets no verdict: there is nothing to keep or drop
    found = {k for r in table for k in r.get("frames") or {}}
    keys = [s["frame"] for s in stats_doc.get("frames") or [] if s["frame"] in found] or T.frame_order(
        {k: frames[k] for k in found if k in frames})
    labels = {"corpus": corpus_labels(args.data_dir),
              "queue": queue_labels(args.queue_path or Path(args.data_dir) / "seed_queue.json")}
    baselines = {}
    uni = _universe()
    if uni:
        baselines["baseline_wordfreq"] = E.frequency_ranking(uni, _zipf())
    else:
        print("NOTE: OEWN is not installed: the OEWN-universe baseline is left out (the table's own Zipf baseline "
              "stays)", file=sys.stderr)
    reg_rows = _registry_rows(args)
    measures = types = kept = verdicts = None
    thresholds = {"yield_min": args.yield_min, "tv_max": args.tv_max}
    if args.pilot_run:
        rdir = paths.run_dir(G.GENERATOR, args.pilot_run, candidates_dir=args.candidates_dir)
        if not (rdir / "run.json").exists():
            print(f"no pilot run at {_rel(rdir)}", file=sys.stderr)
            return 2
        sel = (R.submit_args(json.loads((rdir / "run.json").read_text())).get("selection_by_frame") or {})
        if not sel:
            print(f"{_rel(rdir / 'run.json')} records no selection_by_frame: not a --top-per-frame run",
                  file=sys.stderr)
            return 2
        measures = E.frame_measures(table, reg_rows, selection=sel)
        types = E.type_measures(table, reg_rows, selection=sel, frame_types=_frame_types(frames))
        kept, verdicts = E.frames_kept(measures, keys, yield_min=args.yield_min, tv_max=args.tv_max,
                                       keep=_csv(args.keep_frames), drop=_csv(args.drop_frames))
        thresholds.update({"kept_by_hand": _csv(args.keep_frames), "dropped_by_hand": _csv(args.drop_frames)})
    cutoffs = [int(x) for x in args.cutoffs.split(",")]
    ev = E.build_evaluation(table, label_sets=labels, frame_keys=keys, table_sha256=T.file_sha256(path),
                            bank_sha256=F.bank_sha256(), text_bank_sha256=X.text_bank_sha256(),
                            registered_stems=set(T.registry_index(reg_rows)), regions=E.corpus_regions(args.regions),
                            baselines=baselines, cutoffs=cutoffs, ordering=args.ordering, measures=measures,
                            types=types, kept=kept, verdicts=verdicts, pilot_run=args.pilot_run,
                            thresholds=thresholds, title=args.title)
    if verdicts is None:
        ev["frame_verdicts"] = {k: list(E.keep_frame(None)) for k in keys}
    per = ev["recovery"]["per_frame"]
    for s in stats_doc.get("frames") or []:
        k = s["frame"]
        s["recovery"] = {o: ((per.get(k) or {}).get(o) or {}).get("corpus", {}).get("all") for o in E.ORDERINGS}
        s["pilot"] = (measures or {}).get(k)
        s["keep"], s["why"] = (ev["frame_verdicts"].get(k) or [None, "no filler above the floor: nothing to keep"])
    u = ev["recovery"]
    print(f"{ev['n_rows']} rows, {ev['n_eligible']} eligible, {ev['n_net_new']} net-new; ordering {ev['ordering']} "
          f"({ev['ordering_rule']['why']})")
    for name in ("union_volumes", "union_lift", "baseline_wordfreq", "baseline_table_zipf"):
        v = ((u.get(name) or {}).get("corpus") or {}).get("all")
        if v:
            print(f"  {name}: " + ", ".join(f"{k} {v.get(k)}" for k in v if k.startswith("recall@")))
    if kept is not None:
        print(f"frames kept: {len(kept)} of {len(keys)}; dropped: "
              + (", ".join(k for k in keys if k not in kept) or "none"))
    md = R.render_readout(ev, stats_doc.get("frames") or [], doc_path=_out(args, "readout.md"),
                          traits_dir=_traits_dir(args),
                          files={"the evaluation (JSON)": _out(args, "evaluation.json"),
                                 "the per-frame statistics": stats_p,
                                 "the recovery curves": _out(args, "recovery_curves.png"),
                                 "the shard plan": _out(args, "shard_plan.json"),
                                 "the table (git-ignored)": path})
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {_rel(_out(args, 'evaluation.json'))}, {_rel(stats_p)}, "
              f"{_rel(_out(args, 'recovery_curves.png'))} and {_rel(_out(args, 'readout.md'))}")
        return 0
    inputs = [current_file_input(dep_key=k, path=p) for k, p in
              (("frames_table", path), ("frame_stats", stats_p), ("registry", args.registry),
               ("corpus_regions", args.regions)) if Path(p).exists()]
    _write_json(_envelope(ev, title=f"corpus-frames evaluation{': ' + args.title if args.title else ''}",
                          inputs=inputs), _out(args, "evaluation.json"))
    _write_json(_envelope(stats_doc, title="corpus-frames per-frame statistics", inputs=inputs), stats_p)
    E.plot_recovery_curves(ev, _out(args, "recovery_curves.png"), inputs=inputs)
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text(md, _out(args, "readout.md"))
    print(f"wrote {_rel(_out(args, 'evaluation.json'))}, {_rel(stats_p)}, {_rel(_out(args, 'recovery_curves.png'))},"
          f" {_rel(_out(args, 'readout.md'))}")
    return 0


def _csv(s: Optional[str]) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


# ---------------------------------------------------------------------------- submit / report

def cmd_submit(args) -> int:
    from assistant_axis.gapgen.cost import CostRefused
    from assistant_axis.gapgen.generators.corpus_frames import submit as SB
    from assistant_axis.gapgen.generators.corpus_frames import table as T
    if (args.top_per_frame is None) == (args.kept_target is None):
        print("give exactly one of --top-per-frame N (the pilot) and --kept-target K (the wave)", file=sys.stderr)
        return 2
    table, path = _tagged_table(args)
    if table is None:
        print(f"missing {_rel(path)}: run `table` first", file=sys.stderr)
        return 2
    ev_p = _out(args, "evaluation.json")
    ev = _read_json(ev_p) if ev_p.exists() else {}
    if ev and ev.get("table_sha256") and ev["table_sha256"] != T.file_sha256(path):
        print(f"WARNING: {_rel(ev_p)} was made from another table (sha256 {ev['table_sha256'][:12]}): run `evaluate` "
              f"again before a wave", file=sys.stderr)
    ordering = args.ordering or ev.get("ordering") or "volumes"
    frames_kept = None
    if args.kept_target is not None:
        if args.all_frames:
            frames_kept = sorted({k for r in table for k in r.get("frames") or {}})
        elif ev.get("pilot_run"):
            frames_kept = list(ev.get("frames_kept") or [])
        else:
            print(f"the wave reads the frames kept after the pilot from {_rel(ev_p)} (`evaluate --pilot-run R`); "
                  f"pass --all-frames to use every frame", file=sys.stderr)
            return 2
    frames = _all_frames("all")
    try:
        SB.run_submit(args.run_id, table=table, frame_types=_frame_types(frames), top_per_frame=args.top_per_frame,
                      kept_target=args.kept_target, kept_share=args.kept_share, frames_kept=frames_kept,
                      ordering=ordering, count_siblings=not args.no_count_siblings, budget_usd=args.budget_usd,
                      confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                      transport=args.transport, dry_run=args.dry_run, registry_path=args.registry,
                      candidates_dir=args.candidates_dir, table_path=Path(_rel(path)),
                      table_sha256=T.file_sha256(path), bank_sha256=F.bank_sha256(),
                      text_bank_sha256=X.text_bank_sha256(), review_rate=_review_rate(),
                      extra_args={"evaluation_pilot_run": ev.get("pilot_run")})
    except SB.ReviewLoadExceeded as exc:
        print(f"refused (review load): {exc}", file=sys.stderr)
        return 2
    except CostRefused as exc:
        print(f"refused (cost): {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_report(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.corpus_frames import report as R
    from assistant_axis.gapgen.generators.corpus_frames.submit import batch_id_for
    rdir = paths.run_dir(G.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    if not (rdir / "candidates.jsonl").exists():
        print(f"no run at {_rel(rdir)} (no candidates.jsonl)", file=sys.stderr)
        return 2
    table, path = _tagged_table(args)
    table = table or []
    reg = _registry_rows(args)
    ev_p = _out(args, "evaluation.json")
    ev = _read_json(ev_p) if ev_p.exists() else {}
    cdir = args.candidates_dir or paths.DATA_CANDIDATES
    b = batch_id_for(args.run_id)
    fdir, ndir = paths.filter_dir(b, candidates_dir=cdir), paths.novelty_dir(b, candidates_dir=cdir)
    rate = _review_rate()
    fig = R.figures(args.run_id, run_dir=rdir, registry_rows=reg, table=table, evaluation=ev,
                    frame_types=_frame_types(_all_frames("all")), filter_dir=fdir, novelty_dir=ndir, review_rate=rate)
    doc = rdir / "report.md"
    td = _traits_dir(args)
    md = R.render_report(fig, doc_path=doc, table_path=path, traits_dir=td)
    recs = R.kept_records(reg, args.run_id, table)
    sample = R.roger_sample(recs, doc_path=rdir / "roger_sample.md", run_id=args.run_id, traits_dir=td)
    first = R.roger_first_hour(recs, doc_path=rdir / "roger_first_hour.md", run_id=args.run_id, review_rate=rate[0],
                               traits_dir=td)
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {_rel(doc)}, {_rel(rdir / 'roger_sample.md')} and "
              f"{_rel(rdir / 'roger_first_hour.md')}")
        return 0
    atomic_write_text(md, doc)
    atomic_write_text(sample, rdir / "roger_sample.md")
    atomic_write_text(first, rdir / "roger_first_hour.md")
    print(f"wrote {_rel(doc)}, {_rel(rdir / 'roger_sample.md')}, {_rel(rdir / 'roger_first_hour.md')} "
          f"({len(recs)} kept rows)")
    return 0


# ---------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (evaluation and tags)")
    ap.add_argument("--queue-path", type=Path, default=None, help="seed queue (default <data-dir>/seed_queue.json)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--out-dir", type=Path, default=G.FRAMES_DIR,
                    help="tracked outputs: shard plan, frame stats, evaluation, curves, readout; the git-ignored "
                         "table (default data/candidates/corpus_frames)")
    ap.add_argument("--external-dir", type=Path, default=G.EXTERNAL_DIR,
                    help="the Books extracts and their manifest (default data/external/books_ngrams; git-ignored)")
    ap.add_argument("--text-dir", type=Path, default=G.TEXT_EXTERNAL_DIR,
                    help="the text corpora's downloads and extracts (default data/external/corpus_frames)")
    ap.add_argument("--sources-manifest", type=Path, default=G.SOURCES_MANIFEST_PATH,
                    help="the tracked copy of the download manifests")
    ap.add_argument("--regions", type=Path, default=paths.CORPUS_REGIONS_PATH,
                    help="corpus_regions.json (the unfound labels by region)")
    ap.add_argument("--tier", default="all", choices=("1", "2", "all"),
                    help="the Books bank's tier (default all: Roger, 2026-10-14, open decision 1 (b))")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("locate", help="head-peek the shards and write shard_plan.json (about 3 MB for both tiers; $0)")
    p.add_argument("--dry-run", action="store_true", help="print the prefixes and the requests; no request made")
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("stream", help="stream the planned shards, keeping the matching lines (Roger's go; $0)")
    p.add_argument("--approved-by", default=None, help="Roger's go for the stream (refused without it)")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--resume", action="store_true", help="skip the shards already extracted")
    p.add_argument("--force", action="store_true", help="stream every shard again")
    p.add_argument("--dry-run", action="store_true", help="print the shards to stream; no request made")
    p.set_defaults(func=cmd_stream)

    p = sub.add_parser("fetch-text", help="download PIPPA and the character cards (about 260 MB; Roger's go; $0)")
    p.add_argument("--approved-by", default=None, help="Roger's go for the download (refused without it)")
    p.add_argument("--sources", default=",".join(X.TEXT_SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch_text)

    p = sub.add_parser("extract-text", help="run the text frames over the downloaded corpora ($0)")
    p.add_argument("--sources", default=",".join(X.TEXT_SOURCES))
    p.add_argument("--delete-raw", action="store_true", help="delete the downloads after extraction (hashes kept)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_extract_text)

    p = sub.add_parser("table", help="build frames_table.jsonl and frame_stats.json from the extracts ($0)")
    p.add_argument("--year-min", type=int, default=B.YEAR_MIN, help="sum the Books counts over years >= this (1920)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("evaluate", help="recovery, ordering choice, unfound labels; after the pilot the frame "
                                        "measures and the frames kept ($0)")
    p.add_argument("--cutoffs", default="500,1000,3000,10000")
    p.add_argument("--ordering", default="auto", choices=("auto", "volumes", "lift"),
                   help="auto: the pre-registered rule (higher union recall at 1,000; a tie to volumes)")
    p.add_argument("--pilot-run", default=None, help="the pilot's run id: measure every frame on its fillers")
    p.add_argument("--yield-min", type=float, default=0.4)
    p.add_argument("--tv-max", type=float, default=0.5)
    p.add_argument("--keep-frames", default=None, help="frames Roger keeps by hand (comma-separated)")
    p.add_argument("--drop-frames", default=None, help="frames Roger drops by hand (comma-separated)")
    p.add_argument("--title", default=None)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_evaluate)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream M1 + M3 estimate)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--top-per-frame", type=int, default=None, help="pilot: the top N of every frame (25)")
    p.add_argument("--kept-target", type=int, default=None, help="wave: net-new kept rows to aim for (300)")
    p.add_argument("--kept-share", type=float, default=None,
                   help="wave: the pilot's measured net-new kept share (default the proxy's 0.3, flagged ASSUMED)")
    p.add_argument("--all-frames", action="store_true", help="wave: every frame, not evaluation.json's frames kept")
    p.add_argument("--no-count-siblings", action="store_true",
                   help="wave: count table rows in the cut, not the noun siblings the platform adds (the review-load "
                        "guard then refuses a cut whose siblings push the projection past 1.5x the target)")
    p.add_argument("--ordering", default=None, choices=("volumes", "lift"),
                   help="default: evaluation.json's ordering (volumes before any evaluation)")
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="how the platform will run M1 and M3 (batches: half price in the estimate)")
    p.add_argument("--budget-usd", type=float, default=8.0,
                   help="cap on the downstream estimate (M1 + M3); over it the submit is refused")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for an estimate over $20")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="a run's readout after M1 and M3, the spot check and the first hour ($0)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "kept_share", None) is None and args.cmd == "submit":
        from assistant_axis.gapgen.generators.corpus_frames.submit import KEPT_SHARE_ASSUMED
        args.kept_share = KEPT_SHARE_ASSUMED
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
