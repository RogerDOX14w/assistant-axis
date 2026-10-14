#!/usr/bin/env python3
"""The base-model generator (workstream 3, generator id ``base_model``).

    uv run python data_analysis/gap_generation/base_model_generator.py fetch [--only wikibio onet model]
        --approved-by 'Roger, <date>' [--force] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py bench [--batch-sizes 32,64] [--device mps]
    uv run python data_analysis/gap_generation/base_model_generator.py sample --round N --n 2000 [--temperature 1.0]
        [--t-grid 0.8,1.0,1.2 --per-t 500] [--families list,person,...] [--batch-size 32] [--token-budget 1024]
        [--device mps] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py parse --round N [--temperature T] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py sense --round N [--arm bge|gemma|openai|hash]
        [--divergence-cosine 0.6] [--budget-usd 2] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py stats --round N [--temperature T] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py submit --round N --run-id R [--min-count 2]
        [--kept-target 300] [--kept-share X] [--order stratified|measured] [--wave-seed 0] [--no-ride-along]
        [--all] [--budget-usd 15] [--transport live|batches] [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/base_model_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_03_base_model.md``.  ``fetch`` downloads ``wiki_bio`` and the
O*NET occupation titles into ``data/external/`` (Roger's approval, section 5a, recorded with ``--approved-by``)
and records the model, which ``setup_external.py --hf-model Qwen/Qwen3-8B-Base`` downloads.  ``bench`` measures
the local model's aggregate tokens/s (the Mac-or-escalate reading, 150 tok/s).  ``sample`` renders prompts and
runs the local model ($0; tokens charged at a zero rate to ``usage.json``).  ``parse`` builds a round's candidate
table, ``sense`` settles the gloss sense of the rows that carry two (free cosine screen, one cheap call per
divergent row; QUESTIONS 56), ``stats`` the round's diversity figures.  ``submit`` writes a run's
``candidates.jsonl`` and submits it to the registry, gated on the downstream (M1 + M3) estimate, and refuses
while any selected row's sense is unsettled: by default one **review-hour wave** (plan 03 decision (f), 2026-10-14:
net-new rows drawn evenly across the count-bucket x family cells, ``--order stratified``, or from the cell with the
best measured new-kept rate down, ``--order measured``; the count orders nothing), with ``--all`` every eligible row
at the floor (the pilot's submission).  ``report`` writes the readout, with the per-cell measured new-kept rates
once a wave's M1 and M3 are on record.

The generator's only paid call is ``sense``'s, hundredths of a cent a divergent row; M1 and M3 are the
platform's CLIs, printed by ``submit``.  ``sense`` refuses while the platform's own paths have uncommitted changes
unless ``--allow-dirty`` (code review 2026-10-12).
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


def platform_dirty_files() -> Optional[list[str]]:
    """``runs.platform_dirty_files`` under this module's name, so that tests can replace it."""
    from assistant_axis.gapgen.runs import platform_dirty_files as dirty
    return dirty()


def _write_usage(usage, path: Path) -> None:
    """A usage record, atomically, in ``MultiModelUsage.write_json``'s form."""
    from assistant_axis.atomic_io import atomic_write_text
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(usage.as_dict(), indent=2, sort_keys=True), Path(path))


def _sense_usage_record(args, *, migrate: bool) -> Path:
    """The gloss-sense step's usage record for ``args.round``: the tracked, cumulative
    ``<base dir>/gloss_sense_usage_round<N>.json`` (code review 2026-10-12, B2).  Before that the step recorded its
    usage only in the gitignored round directory (``sense.USAGE_NAME``): when the tracked file is missing and that one
    exists, ``migrate`` copies it over (and says so), and without ``migrate`` (a dry run) the old file is returned to
    be read.  The old file is left as it was and is no longer written."""
    from assistant_axis.gapgen.generators.base_model import sense as SE
    from assistant_axis.judge_pricing import MultiModelUsage
    tracked = B.sense_usage_path(args.round, args.base_dir)
    old = args.samples_dir / f"round{int(args.round)}" / SE.USAGE_NAME
    if tracked.exists() or not old.exists():
        return tracked
    if not migrate:
        return old
    _write_usage(MultiModelUsage.load_or_create(old), tracked)
    print(f"wrote {_rel(tracked)}: the round's gloss-sense usage, copied from {_rel(old)}, where the step recorded "
          f"it before 2026-10-12 (that file is no longer written)")
    return tracked


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
          f"batch {args.batch_size}, token budget {args.token_budget or 'off'}; top-p {SM.TOP_P}, min-p {SM.MIN_P}, {SM.MAX_NEW_TOKENS} new tokens, stop at a "
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
               "batch_size": args.batch_size, "token_budget": args.token_budget or None}
    if record is None:
        record = {"round": args.round, "model": B.MODEL_ID, "key": key, "bundle": bundle.manifest,
                  "sampling": {"top_p": SM.TOP_P, "min_p": SM.MIN_P, "max_new_tokens": SM.MAX_NEW_TOKENS,
                               "stop": "blank line", "repetition_penalty": None},
                  "family_weights": PR.FAMILY_WEIGHTS, "sessions": []}
    atomic_write_text(json.dumps(record, indent=2) + "\n", rec_path)
    backend = SM.HFBackend(device=args.device, batch_size=args.batch_size, cache_dir=args.hf_dir)
    usage = MultiModelUsage.load_or_create(usage_path)
    try:
        stats = SM.run_sampling(backend, plan, out_path=out, usage=usage, usage_path=usage_path,
                                token_budget=args.token_budget or None)
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


def _counts_path(args, temperature: Optional[float]) -> Path:
    """``parse``'s own counts (echoes, malformed, per family), which ``stats`` reads: they are counted while
    the samples are read and cannot be recovered from the table alone (QUESTIONS 54 and 61)."""
    t = "" if temperature is None else f"_t{float(temperature):g}"
    return args.samples_dir / f"round{args.round}" / f"table_counts{t}.json"


def _corpus(args):
    """Corpus and queue trait stems (evaluation only).  Former names come from ``evaluate.renamed_map``
    (``resolve_renamed_stem``), not from the censuses' ``corpus_renamed_from``, which reads only the
    string form of ``renamed_from`` and fails on the object form the rename tooling writes."""
    from assistant_axis.gapgen.generators.censuses.corpus import corpus_trait_stems, queue_trait_stems
    return corpus_trait_stems(args.data_dir), queue_trait_stems(None, data_dir=args.data_dir)


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


def _unscreened_person_samples(samples, bio_lookup) -> list[str]:
    """Person-family samples whose biography ``bio_lookup`` cannot serve.  The echo screen (QUESTIONS 54: no name
    word and no copied span of CC BY-SA biography text in the tracked table) needs the biography of every such
    sample; ``table.build_table`` skips the screen for a sample it cannot look up, so ``parse`` refuses instead."""
    out = []
    for s in samples:
        if s.get("family") != "person":
            continue
        ref = next((r for r in s.get("seed_refs") or [] if str(r).startswith("wikibio:")), None)
        if bio_lookup is None or ref is None or bio_lookup(ref) is None:
            out.append(str(s.get("sample_id")))
    return out


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
    bio_lookup = _bio_lookup(args, record)
    unscreened = _unscreened_person_samples(samples, bio_lookup)
    if unscreened:
        print(f"refused: {len(unscreened)} person-family sample(s) have no biography to screen against "
              f"({', '.join(unscreened[:5])}{' ...' if len(unscreened) > 5 else ''}).  The echo screen keeps the "
              f"person's name and any copied biography span out of the tracked table (QUESTIONS 54) and cannot run "
              f"without them: fetch wiki_bio (`base_model_generator.py fetch --only wikibio`), or check that the "
              f"round's sampling.json bundle names the pool the samples were drawn from", file=sys.stderr)
        return 2
    corpus, queue = _corpus(args)
    per: list = []
    rows, counts = TB.build_table(samples, lookups=TB.default_lookups(), corpus_stems=corpus, queue_stems=queue,
                                  tda_stems=_tda_stems(args), bio_lookup=bio_lookup, per_sample=per)
    # A reparse must not throw away the gloss-sense decisions that were paid for: each one is carried onto the
    # rebuilt row when its two glosses are unchanged, and dropped when they moved (QUESTIONS 56).
    if table_p.exists():
        from assistant_axis.gapgen.generators.base_model import sense as SE
        carried = SE.carry_forward(rows, TB.load_table(table_p))
        if carried:
            print(f"carried {carried} gloss-sense decisions forward from the previous table")
    print(json.dumps(counts))
    counts_p = _counts_path(args, args.temperature)
    if args.dry_run:
        print(f"DRY-RUN: would write {_rel(table_p)} ({len(rows)} rows), {_rel(stems_p)} and {_rel(counts_p)}")
        return 0
    backup = TB.write_table(rows, table_p)
    atomic_write_text("".join(json.dumps(p) + "\n" for p in per), stems_p)
    atomic_write_text(json.dumps(counts, indent=2) + "\n", counts_p)
    print(f"wrote {_rel(table_p)} ({len(rows)} rows)" + (f"; previous table kept as {_rel(backup)}" if backup else ""))
    print(f"wrote {_rel(stems_p)}, {_rel(counts_p)}")
    return 0


def _anthropic_client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


#: Measured on the rendered call (system about 340 tokens, user about 60, answer about 50), for the estimate
#: only; every call's real tokens are charged to the usage record.
SENSE_TOKENS = (400, 60)


def _sense_estimate(n: int, model: str) -> float:
    from assistant_axis.judge_pricing import cost_for_usage
    return round(n * cost_for_usage(model, *SENSE_TOKENS), 4)


def cmd_sense(args) -> int:
    """Settle the gloss sense of the rows that carry two glosses, before M1 (QUESTIONS 56)."""
    from assistant_axis.gapgen.cost import confirm_or_abort
    from assistant_axis.gapgen.generators.base_model import sense as SE
    from assistant_axis.gapgen.generators.base_model import table as TB
    from assistant_axis.judge_pricing import MultiModelUsage
    _, table_p, _, _, _ = _paths(args, None)
    arm = args.arm or SE.DEFAULT_ARM
    floor = SE.DIVERGENCE_COSINE if args.divergence_cosine is None else args.divergence_cosine
    concurrency = args.concurrency or SE.DEFAULT_CONCURRENCY
    if not table_p.exists():
        print(f"missing {_rel(table_p)}: run `parse --round {args.round}` first", file=sys.stderr)
        return 2
    rows = TB.load_table(table_p)
    rdir = args.samples_dir / f"round{args.round}"
    two = [r for r in rows if SE.two_sided(r)]
    todo = [r for r in rows if SE.needs_screen(r)]
    print(f"round {args.round}: {len(rows)} table rows, {len(two)} with two glosses (OEWN's sense and the "
          f"model's own), {len(todo)} needing the free cosine screen at floor {floor:g}")
    # The paid step refuses on uncommitted platform code, as the platform's own CLIs do (code review 2026-10-12, B4).
    from assistant_axis.gapgen.runs import dirty_refusal
    refused, _ = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would embed {2 * len(todo)} gloss texts with the {arm} arm (free for a local arm), "
              f"flag the divergent rows, ask {SE.MODEL} one question each, and write the decisions into "
              f"{_rel(table_p)} with {_rel(rdir / SE.RESPONSES_NAME)} and the tracked usage record "
              f"{_rel(B.sense_usage_path(args.round, args.base_dir))}")
        if two:
            print(SE.render(two[0]))
        return 0
    if refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2
    # A row whose call failed twice, or was decided under an older prompt, needs no new screen but does need its
    # call again; the rerun of 2026-10-12 found nothing to screen and returned with 33 such rows still unresolved.
    n_stale_call = sum(1 for r in rows if SE.needs_call(r))
    if not todo and not n_stale_call:
        print("nothing to screen; every two-sided row already carries a settled sense")
        return 0
    # the step's usage record is tracked and cumulative over the round's sessions (code review 2026-10-12, B2)
    usage_p = _sense_usage_record(args, migrate=True)
    usage = MultiModelUsage.load_or_create(usage_p)
    before = MultiModelUsage.from_dict(usage.as_dict())
    if todo:
        from assistant_axis.gapgen.embed import EmbeddingCache, embed_texts, make_embedder
        embedder = make_embedder(arm)
        # The hash arm is a deterministic test double, so it is never cached; a real arm uses the platform's cache.
        cache = None if arm == "hash" else EmbeddingCache(args.embed_cache_dir) if args.embed_cache_dir \
            else EmbeddingCache()
        cos = SE.cosine_rows(rows, embed=lambda texts: embed_texts(embedder, texts, cache=cache, usage=usage))
        counts = SE.screen(rows, cosines=cos, floor=floor, embedder=embedder.name)
        print(f"screen: {counts['n_divergent']} of {counts['n_screened']} divergent "
              f"(rate {counts['divergence_rate']}), {counts['n_agree']} settled by agreement with no call")
        if usage.n_calls != before.n_calls:
            # the screen's embeddings are recorded before the cost gate, which may refuse the calls
            _write_usage(usage, usage_p)
    else:
        print(f"nothing to screen; {n_stale_call} divergent row(s) still need their call (failed, or an older prompt)")
    n_call = sum(1 for r in rows if SE.needs_call(r))
    est = _sense_estimate(n_call, SE.MODEL)
    print(f"{n_call} calls to {SE.MODEL}, estimate ${est:.4f} (the screen itself is free with a local arm)")
    cap = confirm_or_abort(est, args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    rdir.mkdir(parents=True, exist_ok=True)
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.judge_pricing import BudgetExceededError
    # The typed --budget-usd is a hard cap on this session's calls (gapgen.cost), as on every other paid CLI.  The
    # usage file is cumulative over the round's sessions, so the guard sits at what is already recorded plus the cap.
    guarded = GuardedUsage(per_model=dict(usage.per_model), budget_usd=usage.total_cost_usd + cap,
                           usage_path=usage_p)
    done, stopped, backup = None, None, None
    try:
        done = SE.run_resolve_rows(rows, client=_anthropic_client(), usage=guarded, concurrency=concurrency,
                                   records_path=rdir / SE.RESPONSES_NAME)
    except BudgetExceededError as exc:
        stopped = exc
    finally:
        # A stop or a failure part-way keeps what was paid for: the decisions already on the rows, and the usage.
        guarded.write_json(usage_p)
        backup = TB.write_table(rows, table_p)
    usage = guarded
    if done is not None:
        print(json.dumps(done))
    n_session = usage.n_calls - before.n_calls
    print(f"[usage] this session: {n_session} calls (embeddings and sense calls), "
          f"${usage.total_cost_usd - before.total_cost_usd:.4f}")
    print(usage.log_line(prefix=f"[usage] round {args.round} total"))
    summary = SE.summary(rows)
    print("gloss sense: " + json.dumps(summary))
    print(f"wrote {_rel(table_p)}" + (f"; previous table kept as {_rel(backup)}" if backup else " (unchanged)"))
    print(f"wrote {_rel(rdir / SE.RESPONSES_NAME)}, {_rel(usage_p)}")
    if stopped is not None:
        print(f"STOPPED at the cap (--budget-usd {cap:g}): {stopped}.  The decisions made before the stop are on the "
              f"table; rerun `sense --round {args.round}` with a larger --budget-usd for the "
              f"{summary['n_unresolved']} rows still unresolved", file=sys.stderr)
        return 1
    if summary["n_unresolved"]:
        print(f"{summary['n_unresolved']} rows are still unresolved (a failed call): rerun `sense --round "
              f"{args.round}` before submitting", file=sys.stderr)
        return 1
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
    # `parse`'s own counts where it saved them (the echo split and the per-family figures are counted over the
    # samples, not recoverable from the table); the recomputed subset is the fallback for an older round.
    counts_p = _counts_path(args, args.temperature)
    counts = {"n_raw_items": None, "by_form": dict(Counter(r["form"] for r in rows)),
              "by_form_eligible": dict(Counter(r["form"] for r in rows if r["eligible"])),
              "ineligible": dict(Counter(r["ineligible_reason"] for r in rows if not r["eligible"])),
              "normalized_mechanically": sum(1 for r in rows if r["normalized_from"])}
    if counts_p.exists():
        counts = json.loads(counts_p.read_text(encoding="utf-8"))
    else:
        print(f"note: no {_rel(counts_p)} (parsed before it existed), so the echo split and the per-family "
              f"malformed rates are missing from this record; rerun `parse --round {args.round}`")
    corpus, _ = _corpus(args)
    renamed = EV.renamed_map([r["stem"] for r in rows], corpus, data_dir=args.data_dir)
    st = EV.round_stats(samples, rows, per, counts, round_n=args.round, temperature=args.temperature,
                        corpus_stems=corpus, renamed=renamed, step=args.step)
    if st.get("n_raw_items") is None:          # an older round, without parse's saved counts
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

def _table_n_samples(args) -> Optional[int]:
    """The number of samples the round's table was built from, recorded with the count floor (gate audit 3: a
    count means a different rate at every sample size): ``parse``'s saved counts, else the round's stats, else
    the samples file itself."""
    counts_p = _counts_path(args, None)
    if counts_p.exists():
        n = json.loads(counts_p.read_text(encoding="utf-8")).get("n_samples")
        if n:
            return int(n)
    samples_p, _, _, stats_p, _ = _paths(args, None)
    if stats_p.exists():
        d = json.loads(stats_p.read_text(encoding="utf-8"))
        n = (d.get("result", d) or {}).get("n_samples")
        if n:
            return int(n)
    if samples_p.exists():
        from assistant_axis.gapgen.generators.base_model import table as TB
        return len(TB.load_samples(samples_p)) or None
    return None


def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.base_model import submit as SB
    from assistant_axis.gapgen.generators.base_model import table as TB
    from assistant_axis.gapgen.generators.base_model.download import sha256_file
    _, table_p, _, _, rec_p = _paths(args, None)
    if not table_p.exists():
        print(f"missing {_rel(table_p)}: run `parse --round {args.round}` first", file=sys.stderr)
        return 2
    from assistant_axis.gapgen.generators.base_model import evaluate as EV
    from assistant_axis.gapgen.generators.base_model import waves as W
    record = json.loads(rec_p.read_text(encoding="utf-8")) if rec_p.exists() else None
    explicit = args.min_count is not None
    min_count = args.min_count if explicit else SB.DEFAULT_MIN_COUNT
    table = TB.load_table(table_p)
    wave_kw = {}
    if not args.all:
        # the net-new test reads the corpus, its former names and the seed queue as they are now, not the table's
        # flags from parse time
        corpus, queue = _corpus(args)
        wave_kw = {"wave": True, "kept_target": args.kept_target, "kept_share": args.kept_share,
                   "order": args.order, "wave_seed": args.wave_seed, "ride_along": not args.no_ride_along,
                   "min_measured": args.min_measured, "corpus_stems": corpus, "queue_stems": queue,
                   "renamed": EV.renamed_map([r["stem"] for r in table], corpus, data_dir=args.data_dir)}
    try:
        SB.run_submit(args.run_id, table=table, round_n=args.round, min_count=min_count,
                      min_count_explicit=explicit, n_samples=_table_n_samples(args),
                      families=args.families.split(",") if args.families else None, budget_usd=args.budget_usd,
                      confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                      transport=args.transport, dry_run=args.dry_run, registry_path=args.registry,
                      candidates_dir=args.candidates_dir, table_path=Path(_rel(table_p)),
                      table_sha256=sha256_file(table_p), sampling_record=record,
                      sampling_usage_path=rec_p.parent / "usage.json", **wave_kw)
    except SB.SenseUnresolved as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    except W.NothingMeasured as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
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
    # the round's tracked sense usage record (made here from the round directory's if the step has not run since
    # 2026-10-12; a dry run reads the old one and writes nothing)
    ev = EV.evaluate_run(args.run_id, run_dir=rdir, table=table, stats=stats, registry_rows=reg, filter_dir=fdir,
                         novelty_dir=ndir, sampling_usage=rec_p.parent / "usage.json",
                         sense_usage=_sense_usage_record(args, migrate=not args.dry_run))
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
    from assistant_axis.gapgen.generators.base_model import sampler as SM     # light: no model, no torch
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
    p.add_argument("--batch-size", type=int, default=32, help="the most prompts a batch holds")
    p.add_argument("--token-budget", type=int, default=SM.DEFAULT_TOKEN_BUDGET,
                   help="a batch's prompts times its longest prompt (tokens) stay within this, so long prompts go in "
                        f"smaller batches (default {SM.DEFAULT_TOKEN_BUDGET}: batch 32 at round 1's median prompt of 31 "
                        "tokens); 0 turns it off")
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

    p = sub.add_parser("sense", help="settle the gloss sense of the rows carrying two (free cosine screen, one "
                                     "cheap call per divergent row; QUESTIONS 56)")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--arm", default=None,
                   help="embedding arm for the free divergence screen (default the local bge; gemma | openai | hash)")
    p.add_argument("--divergence-cosine", type=float, default=None,
                   help="below this cosine the two glosses go to a call (default sense.DIVERGENCE_COSINE; every "
                        "cosine is recorded, so another floor re-derives without re-embedding)")
    p.add_argument("--concurrency", type=int, default=None)
    p.add_argument("--embed-cache-dir", type=Path, default=None,
                   help="embedding cache (default the platform's data/candidates/cache/embeddings)")
    p.add_argument("--budget-usd", type=float, default=2.0, help="cap on the sense calls (pennies in practice)")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None)
    p.add_argument("--allow-dirty", action="store_true",
                   help="run although the platform's own code or prompt paths have uncommitted changes "
                        "(refused otherwise)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_sense)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream M1 + M3 estimate)")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--min-count", type=int, default=None,
                   help="the count floor: submit rows at least this many samples emitted (default 2, chosen by "
                        "Roger on 2026-10-12 for a 2,000-sample table, gate audit 3; recorded in run.json and "
                        "submit_report.json with the table's sample size, and a note is printed when the table "
                        "has another size)")
    p.add_argument("--families", default=None, help="only rows these families emitted (comma-separated)")
    p.add_argument("--all", action="store_true",
                   help="submit every eligible row at the floor (the pilot's submission) instead of one wave")
    p.add_argument("--kept-target", type=int, default=300,
                   help="the wave's size in kept terms (default 300, about two hours of review); the wave takes "
                        "ceil(K / kept share) net-new rows")
    p.add_argument("--kept-share", type=float, default=None,
                   help="kept terms per submitted net-new row (default: the pooled share the earlier waves measured "
                        "once 10 rows are decided, else the pilot's 0.34, printed as ASSUMED)")
    p.add_argument("--order", choices=("stratified", "measured"), default=None,
                   help="stratified: evenly across the count-bucket x family cells (the default while no wave is "
                        "measured); measured: from the cell with the best measured new-kept rate down (the default "
                        "once a wave has rows M1 and M3 decided; refused before)")
    p.add_argument("--wave-seed", type=int, default=0, help="the seeded order within a cell and of the remainder")
    p.add_argument("--min-measured", type=int, default=10,
                   help="a cell with fewer decided rows is ranked at the pooled rate under --order measured")
    p.add_argument("--no-ride-along", action="store_true",
                   help="leave out the rows the registry has already decided (they ride along free by default)")
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
