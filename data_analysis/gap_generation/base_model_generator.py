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


# ---------------------------------------------------------------------------- bench / sample

def _model_present(args) -> bool:
    from assistant_axis.gapgen.embed import hf_snapshot_present
    return hf_snapshot_present(B.MODEL_ID, args.hf_dir)


MODEL_MISSING = (f"{B.MODEL_ID} is not downloaded into data/external/hf: run `uv run python data_analysis/"
                 f"gap_generation/setup_external.py --hf-model {B.MODEL_ID}` first (about 16.4 GB, approved by Roger "
                 f"in coding_plan_03_base_model.md section 5a); this command never downloads")


def _bundle(args, *, write_cache: bool = True):
    from assistant_axis.gapgen.generators.base_model.seeds import load_seed_bundle
    kw = {"census_table": args.census_table, "wikibio_dir": args.external_dir / "wikibio",
          "onet_dir": args.external_dir / "onet", "familiarity_floor": args.familiarity_floor,
          "bio_pool_size": args.bio_pool_size, "write_cache": write_cache}
    if args.nouns_file:
        kw["nouns"] = [x.strip() for x in Path(args.nouns_file).read_text(encoding="utf-8").splitlines() if x.strip()]
    return load_seed_bundle(**kw)


def _floats(s: Optional[str]) -> Optional[list[float]]:
    return [float(x) for x in s.split(",") if x.strip()] if s else None


def cmd_bench(args) -> int:
    from assistant_axis.gapgen.generators.base_model import bench as BN
    from assistant_axis.gapgen.generators.base_model import sampler as SM
    sizes = [int(x) for x in args.batch_sizes.split(",")]
    if args.dry_run:
        print(f"DRY-RUN: would load {B.MODEL_ID} on {args.device} (bf16) and time one batch of {sizes} prompts at "
              f"{args.max_new_tokens} new tokens (threshold {BN.THRESHOLD_TOK_S:.0f} tok/s aggregate); "
              f"model {'present' if _model_present(args) else 'NOT downloaded (would refuse)'}")
        return 0
    if not _model_present(args):
        print(MODEL_MISSING, file=sys.stderr)
        return 2
    bundle = _bundle(args)
    plan = SM.plan_samples(bundle, round_n=99, n=max(sizes), seed=args.seed)
    backend = SM.HFBackend(device=args.device, batch_size=max(sizes), cache_dir=args.hf_dir)
    rows = BN.benchmark(backend, [s.prompt.text for s in plan], batch_sizes=sizes, max_new_tokens=args.max_new_tokens)
    verdict = BN.reading(rows)
    print(verdict)
    import platform

    import torch
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import utc_now
    rec = {"at": utc_now(), "model": B.MODEL_ID, "device": args.device, "dtype": "bfloat16",
           "torch": torch.__version__, "machine": platform.machine(), "rows": rows, "reading": verdict,
           "threshold_tok_per_s": BN.THRESHOLD_TOK_S, "git_sha": _git_sha()}
    path = args.bench_record
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(prev + [rec], indent=2) + "\n", path)
    print(f"wrote {_rel(path)}")
    return 0


SAMPLING_KEYS = ("seed", "prompts_version", "wording_sha256", "temperatures", "families", "familiarity_floor",
                 "bio_pool_size")


def cmd_sample(args) -> int:
    from collections import Counter

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.base_model import prompts as PR
    from assistant_axis.gapgen.generators.base_model import sampler as SM
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge_pricing import MultiModelUsage
    grid = _floats(args.t_grid)
    temps = grid or [args.temperature]
    n = args.per_t if grid else args.n
    fams = tuple(args.families.split(",")) if args.families else None
    rdir = args.samples_dir / f"round{args.round}"
    out, rec_path, usage_path = rdir / "samples.jsonl", rdir / "sampling.json", rdir / "usage.json"
    if not args.dry_run and not _model_present(args):
        print(MODEL_MISSING, file=sys.stderr)
        return 2
    bundle = _bundle(args, write_cache=not args.dry_run)
    plan = SM.plan_samples(bundle, round_n=args.round, n=n, seed=args.seed, temperatures=temps, families=fams)
    key = {"seed": args.seed, "prompts_version": PR.PROMPTS_VERSION, "wording_sha256": PR.wording_sha256(),
           "temperatures": temps, "families": list(fams or PR.FAMILIES), "familiarity_floor": args.familiarity_floor,
           "bio_pool_size": args.bio_pool_size}
    record = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else None
    if record is not None:
        diff = {k: (record["key"].get(k), key[k]) for k in SAMPLING_KEYS if record["key"].get(k) != key[k]}
        if diff:
            print(f"refused: round {args.round} was sampled with other settings {diff}; use a new --round",
                  file=sys.stderr)
            return 2
    done = SM.read_done(out)
    pending = [s for s in plan if s.sample_id not in done]
    fam = Counter(s.family for s in plan)
    print(f"round {args.round}: {len(plan)} samples ({n} prompts x T {temps}); {len(plan) - len(pending)} already "
          f"done, {len(pending)} to sample; families " + ", ".join(f"{k} {v}" for k, v in sorted(fam.items())))
    print(f"prompts v{PR.PROMPTS_VERSION} ({PR.wording_sha256()[:12]}); model {B.MODEL_ID} on {args.device}, "
          f"batch {args.batch_size}; top-p {SM.TOP_P}, min-p {SM.MIN_P}, {SM.MAX_NEW_TOKENS} new tokens, stop at a "
          f"blank line; cost $0 (local; tokens recorded at a zero rate in {_rel(usage_path)})")
    if args.dry_run:
        seen = set()
        for s in plan:
            if s.family not in seen:
                seen.add(s.family)
                print(f"--- {s.family} ({s.sample_id}) ---\n{s.prompt.text}")
        print(f"DRY-RUN: would append to {_rel(out)} and write {_rel(usage_path)} and {_rel(rec_path)}")
        return 0
    rdir.mkdir(parents=True, exist_ok=True)
    session = {"started_at": utc_now(), "git_sha": _git_sha(), "n_requested": n, "device": args.device,
               "batch_size": args.batch_size}
    if record is None:
        record = {"round": args.round, "model": B.MODEL_ID, "key": key, "bundle": bundle.manifest,
                  "sampling": {"top_p": SM.TOP_P, "min_p": SM.MIN_P, "max_new_tokens": SM.MAX_NEW_TOKENS,
                               "stop": "blank line", "repetition_penalty": None},
                  "family_weights": PR.FAMILY_WEIGHTS, "sessions": []}
    atomic_write_text(json.dumps(record, indent=2) + "\n", rec_path)
    backend = SM.HFBackend(device=args.device, batch_size=args.batch_size, cache_dir=args.hf_dir)
    usage = MultiModelUsage.load_or_create(usage_path)
    try:
        stats = SM.run_sampling(backend, plan, out_path=out, usage=usage, usage_path=usage_path)
    finally:
        session["finished_at"] = utc_now()
        record["sessions"].append(session)
        atomic_write_text(json.dumps(record, indent=2) + "\n", rec_path)
    session["stats"] = stats.as_dict()
    atomic_write_text(json.dumps(record, indent=2) + "\n", rec_path)
    print(json.dumps(stats.as_dict()))
    print(f"wrote {_rel(out)}, {_rel(usage_path)}, {_rel(rec_path)}")
    return 0


# ---------------------------------------------------------------------------- parse / stats

def _paths(args, temperature: Optional[float]):
    """``(samples, table, per-sample stems, stats, sampling record)`` of a round (one temperature of a grid)."""
    rdir = args.samples_dir / f"round{args.round}"
    t = "" if temperature is None else f"_t{float(temperature):g}"
    table = (rdir / f"candidate_table{t}.jsonl") if temperature is not None else \
        (args.base_dir / f"candidate_table_round{args.round}.jsonl")
    return (rdir / "samples.jsonl", table, rdir / f"sample_stems{t}.jsonl",
            args.base_dir / f"stats_round{args.round}{t}.json", rdir / "sampling.json")


def _corpus(args):
    from assistant_axis.gapgen.generators.censuses.corpus import (
        corpus_renamed_from, corpus_trait_stems, queue_trait_stems,
    )
    return (corpus_trait_stems(args.data_dir), queue_trait_stems(None, data_dir=args.data_dir),
            corpus_renamed_from(args.data_dir))


def _tda_stems(args) -> set[str]:
    from assistant_axis.gapgen.generators.censuses import CENSUS_TABLE_PATH, load_census_table
    p = args.census_table or CENSUS_TABLE_PATH
    return {r.stem for r in load_census_table(p) if r.tda and r.stem} if Path(p).exists() else set()


def _bio_lookup(args, record: Optional[dict]):
    from assistant_axis.gapgen.generators.base_model import seeds as SD
    from assistant_axis.gapgen.generators.base_model.table import bio_lookup_from_pool
    b = (record or {}).get("bundle") or {}
    zp = args.external_dir / "wikibio" / SD.WIKIBIO_ZIP
    if not zp.exists():
        return None
    pool = SD.bio_pool(zp, split=b.get("bio_split", "train"), size=b.get("bio_pool_size", args.bio_pool_size),
                       seed=b.get("pool_seed", 0), min_words=b.get("min_bio_words", 15),
                       max_words=b.get("max_bio_words", 200), cache_dir=args.external_dir / "wikibio",
                       write_cache=not args.dry_run)
    return bio_lookup_from_pool(pool)


def cmd_parse(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.base_model import table as TB
    samples_p, table_p, stems_p, _, rec_p = _paths(args, args.temperature)
    if not samples_p.exists():
        print(f"missing {_rel(samples_p)}: run `base_model_generator.py sample --round {args.round}` first",
              file=sys.stderr)
        return 2
    record = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else None
    samples = TB.load_samples(samples_p, temperature=args.temperature)
    corpus, queue, _ = _corpus(args)
    per: list = []
    rows, counts = TB.build_table(samples, lookups=TB.default_lookups(), corpus_stems=corpus, queue_stems=queue,
                                  tda_stems=_tda_stems(args), bio_lookup=_bio_lookup(args, record), per_sample=per)
    print(json.dumps(counts))
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(table_p)} ({len(rows)} rows) and {_rel(stems_p)}")
        return 0
    backup = TB.write_table(rows, table_p)
    atomic_write_text("".join(json.dumps(p) + "\n" for p in per), stems_p)
    print(f"wrote {_rel(table_p)} ({len(rows)} rows)" + (f"; previous table kept as {_rel(backup)}" if backup else ""))
    print(f"wrote {_rel(stems_p)}")
    return 0


def cmd_stats(args) -> int:
    import random

    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.base_model import evaluate as EV
    from assistant_axis.gapgen.generators.base_model import table as TB
    from assistant_axis.provenance import current_file_input
    samples_p, table_p, stems_p, stats_p, _ = _paths(args, args.temperature)
    for p in (samples_p, table_p, stems_p):
        if not p.exists():
            print(f"missing {_rel(p)}: run `sample` and `parse --round {args.round}` first", file=sys.stderr)
            return 2
    samples = TB.load_samples(samples_p, temperature=args.temperature)
    rows = TB.load_table(table_p)
    per = [json.loads(x) for x in stems_p.read_text(encoding="utf-8").splitlines() if x.strip()]
    from collections import Counter
    counts = {"n_raw_items": None, "by_form": dict(Counter(r["form"] for r in rows)),
              "by_form_eligible": dict(Counter(r["form"] for r in rows if r["eligible"])),
              "ineligible": dict(Counter(r["ineligible_reason"] for r in rows if not r["eligible"])),
              "normalized_mechanically": sum(1 for r in rows if r["normalized_from"])}
    corpus, _, renamed = _corpus(args)
    st = EV.round_stats(samples, rows, per, counts, round_n=args.round, temperature=args.temperature,
                        corpus_stems=corpus, renamed=renamed, step=args.step)
    st["n_raw_items"] = sum(len(p["stems"]) for p in per)
    print(f"round {args.round}" + (f" T={args.temperature:g}" if args.temperature is not None else "")
          + f": {st['n_samples']} samples, {st['n_unique']} uniques ({st['uniques_per_1k_samples']}/1k), "
          f"{st['n_eligible']} eligible, collapse top-50 {st['collapse_top50_share']:.1%}, Chao1 {st['chao1']}, "
          f"noun share {st['noun_share_unique']} / eligible {st['noun_share_eligible']}, recovery-by-string "
          f"{st['recovery_strings']['found']}/{st['recovery_strings']['n_corpus']}")
    print(f"rarefaction {st['rarefaction']}")
    print(f"junk proxies {json.dumps(st['junk'])}")
    print("per family: " + json.dumps(st["per_family"]))
    print("top 20: " + ", ".join(f"{s} {c}" for s, c in st["top20"]))
    singles = [r["surface"] for r in rows if r["eligible"] and r["count"] == 1]
    print("random eligible singletons (junk eyeball): "
          + ", ".join(random.Random(0).sample(singles, min(40, len(singles)))))
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(stats_p)}")
        return 0
    inputs = [current_file_input(dep_key=k, path=p) for k, p in (("samples", samples_p), ("table", table_p),
                                                                ("sample_stems", stems_p))]
    env = json_metadata(st, title=f"base-model generator stats, round {args.round}", inputs=inputs)
    stats_p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", stats_p)
    print(f"wrote {_rel(stats_p)}")
    return 0


# ---------------------------------------------------------------------------- submit / report

def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.base_model import submit as SB
    from assistant_axis.gapgen.generators.base_model import table as TB
    from assistant_axis.gapgen.generators.base_model.download import sha256_file
    _, table_p, _, _, rec_p = _paths(args, None)
    if not table_p.exists():
        print(f"missing {_rel(table_p)}: run `parse --round {args.round}` first", file=sys.stderr)
        return 2
    record = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else None
    SB.run_submit(args.run_id, table=TB.load_table(table_p), round_n=args.round, min_count=args.min_count,
                  families=args.families.split(",") if args.families else None, budget_usd=args.budget_usd,
                  confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by, transport=args.transport,
                  dry_run=args.dry_run, registry_path=args.registry, candidates_dir=args.candidates_dir,
                  table_path=Path(_rel(table_p)), table_sha256=sha256_file(table_p), sampling_record=record,
                  sampling_usage_path=rec_p.parent / "usage.json")
    return 0


def cmd_report(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.base_model import evaluate as EV
    from assistant_axis.gapgen.generators.base_model import report as RP
    from assistant_axis.gapgen.generators.base_model import table as TB
    from assistant_axis.gapgen.generators.base_model.submit import batch_id_for
    from assistant_axis.gapgen.registry import Registry
    from assistant_axis.provenance import current_file_input
    rdir = paths.run_dir(B.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    if not (rdir / "candidates.jsonl").exists():
        print(f"no run at {_rel(rdir)} (no candidates.jsonl)", file=sys.stderr)
        return 2
    run = json.loads((rdir / "run.json").read_text(encoding="utf-8")) if (rdir / "run.json").exists() else {}
    args.round = int((run.get("args") or {}).get("round") or 0)
    _, table_p, _, stats_p, rec_p = _paths(args, None)
    table = TB.load_table(table_p) if table_p.exists() else []
    stats = None
    if stats_p.exists():
        d = json.loads(stats_p.read_text(encoding="utf-8"))
        stats = d.get("result", d)
    reg = Registry(args.registry).fold() if args.registry.exists() else {}
    cdir = args.candidates_dir or paths.DATA_CANDIDATES
    b = batch_id_for(args.run_id)
    fdir, ndir = paths.filter_dir(b, candidates_dir=cdir), paths.novelty_dir(b, candidates_dir=cdir)
    ev = EV.evaluate_run(args.run_id, run_dir=rdir, table=table, stats=stats, registry_rows=reg, filter_dir=fdir,
                         novelty_dir=ndir, sampling_usage=rec_p.parent / "usage.json")
    doc = rdir / "report.md"
    md = RP.render_report(ev, doc_path=doc, run_dir=rdir, table_path=table_p,
                          stats_path=stats_p if stats_p.exists() else None, filter_dir=fdir, novelty_dir=ndir)
    survivors = {r["stem"] for r in EV.run_rows(reg, args.run_id) if (r.get("filter") or {}).get("verdict") == "trait"}
    pool = [r for r in table if r["stem"] in survivors] or [r for r in table if r.get("eligible")]
    sample_md = RP.render_sample(pool, doc_path=rdir / "roger_sample.md")
    if args.dry_run:
        print(md)
        print(f"DRY-RUN: would write {_rel(rdir / 'evaluation.json')}, {_rel(doc)} and {_rel(rdir / 'roger_sample.md')}")
        return 0
    inputs = [current_file_input(dep_key=k, path=p) for k, p in
              (("table", table_p), ("stats", stats_p), ("candidates", rdir / "candidates.jsonl"),
               ("run_json", rdir / "run.json"), ("registry", args.registry)) if Path(p).exists()]
    env = json_metadata(ev, title=f"base-model generator evaluation, run {args.run_id}", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", rdir / "evaluation.json")
    atomic_write_text(md, doc)
    atomic_write_text(sample_md, rdir / "roger_sample.md")
    print(f"wrote {_rel(rdir / 'evaluation.json')}, {_rel(doc)}, {_rel(rdir / 'roger_sample.md')}")
    return 0


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
    ap.add_argument("--hf-dir", type=Path, default=None, help="Hub cache (default data/external/hf)")
    ap.add_argument("--samples-dir", type=Path, default=B.SAMPLES_DIR,
                    help="round directories (default data/candidates/cache/base_model; gitignored)")
    ap.add_argument("--base-dir", type=Path, default=B.BASE_DIR,
                    help="tracked tables and stats (default data/candidates/base_model)")
    ap.add_argument("--census-table", type=Path, default=None, help="seed list A (default the census table)")
    ap.add_argument("--familiarity-floor", type=float, default=0.5)
    ap.add_argument("--bio-pool-size", type=int, default=20_000)
    ap.add_argument("--nouns-file", type=Path, default=None, help="context nouns, one per line (default OEWN)")
    ap.add_argument("--seed", type=int, default=0)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download wiki_bio and O*NET, record the model (bandwidth only)")
    p.add_argument("--only", nargs="+", choices=("wikibio", "onet", "model"))
    p.add_argument("--approved-by", default=None,
                   help="Roger's approval of the downloads (plan section 5a), copied into the manifests")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("bench", help="tokens/s of the local model (the Mac-or-escalate reading; $0)")
    p.add_argument("--batch-sizes", default="32,64")
    p.add_argument("--device", default="mps", choices=("mps", "cpu"))
    p.add_argument("--max-new-tokens", type=int, default=80)
    p.add_argument("--bench-record", type=Path, default=B.BASE_DIR / "bench.json")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("sample", help="render prompts and sample the local model into a round ($0)")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--t-grid", default=None, help="comma-separated temperatures (the shakedown), with --per-t")
    p.add_argument("--per-t", type=int, default=500)
    p.add_argument("--families", default=None, help="comma-separated subset of the six families")
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--device", default="mps", choices=("mps", "cpu"))
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_sample)

    for name, func, hlp in (("parse", cmd_parse, "build a round's candidate table ($0)"),
                            ("stats", cmd_stats, "a round's diversity stats ($0)")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--round", type=int, required=True)
        p.add_argument("--temperature", type=float, default=None, help="one temperature of a grid round")
        if name == "stats":
            p.add_argument("--step", type=int, default=1000, help="rarefaction step (samples)")
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(func=func)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream M1 + M3 estimate)")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--min-count", type=int, default=1)
    p.add_argument("--families", default=None, help="only rows these families emitted (comma-separated)")
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="how the platform will run M1 and M3 (batches: half price in the estimate)")
    p.add_argument("--budget-usd", type=float, default=15.0,
                   help="cap on the downstream estimate (M1 + M3); over it the submit is refused")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for an estimate over $20")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="report.md, roger_sample.md and evaluation.json for a run ($0)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
