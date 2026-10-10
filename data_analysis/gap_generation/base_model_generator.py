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
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
