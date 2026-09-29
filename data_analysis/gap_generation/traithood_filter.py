#!/usr/bin/env python3
"""Run the trait-hood filter over registry rows or a validation file.

    uv run python data_analysis/gap_generation/traithood_filter.py --batch-id B \\
        (--unfiltered | --keys K ... | --run GENERATOR/RUN_ID | --validation-file F) \\
        [--model claude-haiku-4-5-20251001] [--second-model claude-sonnet-4-6] \\
        [--batch-size 25] [--limit N] [--sample-frac F --sample-seed S] \\
        [--no-probe] [--no-second-opinion] [--budget-usd 5.0] [--confirm-expensive] \\
        [--confirmed-by WHO] [--allow-dirty] [--dry-run]

Pipeline per row (``assistant_axis.gapgen.filter``): Zipf floor (hard reject
below 2.0, free) -> WordNet -> Haiku classifier (25 per call) -> definition
probe for 2.0 <= Zipf < 2.5 -> Sonnet second opinion (10% random + confidence
< 0.6 + prior/LLM disagreement).

Outputs in ``data/candidates/filter/<batch_id>/``: ``responses.jsonl`` (every
API response received, parse errors included, appended as each call returns),
``results.jsonl`` (one row per candidate; ``stage: "pending"`` for rows a
budget stop left unclassified), ``summary.json`` (``json_metadata``
envelope), ``usage.json`` (always, also when the budget cap stops the run)
and ``run.json`` (args, estimate, cap, ``confirmed_by``, git sha, the SHA-256
of both prompt texts).  Registry modes also write the ``freq``, ``wordnet``
and ``filter`` blocks, ``gloss``, ``holding`` and ``entity_type`` into the
registry, replacing those of a previous filter pass (never merged into
them); ``--validation-file`` never touches the registry.

Budget stop: the run stops starting calls once the cap is crossed, keeps and
writes every response and classified row it paid for, exits 2, and may
overshoot the cap by the calls already in flight (at most ``--concurrency``
calls in all, counting the one that crossed it).

Provenance: a paid run is refused unless ``--allow-dirty`` (recorded in
run.json) when the platform's own code or prompt paths
(``gapgen.runs.PLATFORM_PATHS``) have uncommitted changes, since the git sha
would not identify the code or prompt that ran; edits elsewhere in the
repository do not count.  run.json records the paths checked and what was
dirty (``dirty_check``).

Any other exception also stops new calls; the CLI then writes everything
already paid for (usage, responses, results, summary with
``stopped_by_error``, registry rows) before re-raising.

Validation files are JSONL rows ``{"surface", "stratum", "expected"?,
"gloss_hint"?, "familiarity"?}``.  ``--sample-frac`` takes a stratified,
seeded sample (strata of 10 rows or fewer are taken whole): the pilot.

Cost: printed as ``n_calls x (in, out) tokens at model rates = $X``;
``--budget-usd`` is the hard cap (default $5) and an estimate over it is
refused (type a larger budget; no flag raises the cap, decision 9).  A budget
over $20 needs ``--confirm-expensive`` together with ``--confirmed-by``.
``--dry-run`` prints the plan, the estimate and the first three prompts, and
writes and calls nothing.

``--probe-only`` (with ``--validation-file``): send every row to the
definition probe, whatever its frequency, and nothing to the classifier or
the second opinion; for checking the probe itself.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text, write_jsonl  # noqa: E402
from assistant_axis.gapgen import filter_rubric as fr  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.cost import (  # noqa: E402
    CostRefused, Estimate, GuardedUsage, confirm_or_abort,
)
from assistant_axis.gapgen.filter import (  # noqa: E402
    DEFAULT_BATCH_SIZE, DEFAULT_MODEL, DEFAULT_SECOND_MODEL, PROMPT_SHA256, FilterItem, FilterRunner,
    items_from_records, summarize,
)
from assistant_axis.gapgen.freq import zipf_info  # noqa: E402
from assistant_axis.gapgen.normalize import make_key, normalize_candidate  # noqa: E402
from assistant_axis.gapgen.registry import Registry, records_for_status, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError  # noqa: E402

logger = logging.getLogger("traithood_filter")

# Token model for the estimate (first-of-kind; revise from the pilot's usage.json).
CHARS_PER_TOKEN = 3.6
IN_TOK_PER_ITEM = 30
OUT_TOK_PER_ITEM = 190  # rubric v2 rows carry label, membership_kind, alignment (v1 measured 140)
PROBE_IN_PER_ITEM = 15
PROBE_OUT_PER_ITEM = 50
SECOND_EXTRA_FRAC = 0.15   # low-confidence + disagreement rows beyond the random sample (guess)
RETRY_MARGIN = 1.10


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------

def read_validation_file(path: Path) -> list[FilterItem]:
    items, seen = [], set()
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        n = normalize_candidate(row["surface"])
        key = make_key(n.stem, int(row.get("sense_id") or 1))
        if key in seen:
            raise SystemExit(f"{path}:{i}: duplicate key {key}")
        seen.add(key)
        items.append(FilterItem(key=key, label=n.label, intended_sense=row.get("gloss_hint"),
                                familiarity=row.get("familiarity"),
                                meta={"stratum": row.get("stratum"), "expected": row.get("expected"),
                                      "surface": row["surface"]}))
    return items


def stratified_sample(items: list[FilterItem], frac: float, seed: int, *, whole_below: int = 10) -> list[FilterItem]:
    """Seeded sample of ``frac`` of each stratum (rounded, at least 1); a
    stratum of ``whole_below`` rows or fewer is taken whole.  Keeps file order."""
    by: dict[str, list[FilterItem]] = defaultdict(list)
    for it in items:
        by[str(it.meta.get("stratum"))].append(it)
    keep = set()
    rng = random.Random(seed)
    for s in sorted(by):
        rows = by[s]
        if len(rows) <= whole_below:
            keep |= {it.key for it in rows}
            continue
        k = max(1, int(round(frac * len(rows))))
        keep |= {it.key for it in rng.sample(rows, k)}
    return [it for it in items if it.key in keep]


def parse_run(value: str) -> tuple[str, str]:
    gen, sep, run_id = value.partition("/")
    if not sep:
        raise argparse.ArgumentTypeError("--run takes GENERATOR/RUN_ID")
    paths.check_id(gen, "generator")
    paths.check_id(run_id, "run_id")
    return gen, run_id


# ---------------------------------------------------------------------------
# estimate
# ---------------------------------------------------------------------------

def build_estimate(items: list[FilterItem], args) -> tuple[Estimate, dict]:
    if getattr(args, "probe_only", False):
        est = Estimate()
        probe_sys = int(len(fr.DEFINE_PROBE_PROMPT) / CHARS_PER_TOKEN)
        per_p = min(args.batch_size, len(items))
        est.add("definition probe (probe only)", args.model, math.ceil(RETRY_MARGIN * len(items) / args.batch_size),
                probe_sys + PROBE_IN_PER_ITEM * per_p, PROBE_OUT_PER_ITEM * per_p)
        return est, {"n_rows": len(items), "probe_only": True, "n_probe": len(items)}
    n_hard = n_probe = 0
    for it in items:
        fq = zipf_info(it.label, familiarity=it.familiarity, gloss_hint=bool(it.intended_sense), curated=it.curated)
        n_hard += fq.hard_reject
        n_probe += (not fq.hard_reject) and fq.probe_band
    n_llm = len(items) - n_hard
    sys_tok = int(len(fr.SYSTEM_PROMPT) / CHARS_PER_TOKEN)
    probe_sys = int(len(fr.DEFINE_PROBE_PROMPT) / CHARS_PER_TOKEN)
    bs = args.batch_size
    est = Estimate()
    n_calls = math.ceil(RETRY_MARGIN * n_llm / bs) if n_llm else 0
    per = min(bs, n_llm) if n_llm else 0
    est.add("classifier", args.model, n_calls, sys_tok + IN_TOK_PER_ITEM * per, OUT_TOK_PER_ITEM * per)
    if not args.no_probe and n_probe:
        per_p = min(bs, n_probe)
        est.add("definition probe", args.model, math.ceil(n_probe / bs), probe_sys + PROBE_IN_PER_ITEM * per_p,
                PROBE_OUT_PER_ITEM * per_p)
    n_sec = 0
    if not args.no_second_opinion and args.second_model and n_llm:
        n_sec = min(n_llm, math.ceil((args.second_opinion_frac + SECOND_EXTRA_FRAC) * n_llm))
        per_s = min(bs, n_sec)
        est.add("second opinion", args.second_model, math.ceil(n_sec / bs), sys_tok + IN_TOK_PER_ITEM * per_s,
                OUT_TOK_PER_ITEM * per_s)
    plan = {"n_rows": len(items), "n_hard_reject": n_hard, "n_llm": n_llm, "n_probe_band": n_probe,
            "n_second_opinion_est": n_sec, "system_prompt_tokens_est": sys_tok}
    return est, plan


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id", required=True)
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--unfiltered", action="store_true", help="every registry row with no filter block")
    sel.add_argument("--keys", nargs="+", help="registry keys (stem#sense)")
    sel.add_argument("--run", type=parse_run, help="GENERATOR/RUN_ID: rows with that source, not yet filtered")
    sel.add_argument("--validation-file", type=Path, help="JSONL of {surface, stratum, expected}; no registry writes")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--out-root", type=Path, default=None,
                    help="candidates dir holding filter/<batch_id>/ (default data/candidates)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--second-model", default=DEFAULT_SECOND_MODEL)
    ap.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    ap.add_argument("--second-opinion-frac", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=0, help="second-opinion sample seed")
    ap.add_argument("--shuffle-seed", type=int, default=0,
                    help="seed for mixing rows across classifier batches (default 0)")
    ap.add_argument("--limit", type=int, help="first N rows only")
    ap.add_argument("--sample-frac", type=float, help="stratified sample of a validation file (pilot)")
    ap.add_argument("--sample-seed", type=int, default=0)
    ap.add_argument("--no-probe", action="store_true")
    ap.add_argument("--no-second-opinion", action="store_true")
    ap.add_argument("--probe-only", action="store_true",
                    help="with --validation-file: send every row to the definition probe only (a probe check)")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float, default=5.0,
                    help="hard cap (default 5.0); an estimate over it is refused: type a larger budget to spend "
                         "more")
    ap.add_argument("--confirm-expensive", action="store_true",
                    help="part of the over-$20 confirmation, valid only with --confirmed-by; it never raises the "
                         "cap")
    ap.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="allow a paid run on a working tree with uncommitted changes (recorded in run.json)")
    ap.add_argument("--overwrite", action="store_true",
                    help="reuse an existing batch dir (its old contents are moved to <dir>.bak.<UTC> first)")
    return ap


def select_items(args) -> tuple[list[FilterItem], Optional[Registry]]:
    if args.validation_file:
        items = read_validation_file(args.validation_file)
        if args.sample_frac:
            items = stratified_sample(items, args.sample_frac, args.sample_seed)
        reg = None
    else:
        if args.sample_frac:
            raise SystemExit("--sample-frac applies to --validation-file only")
        reg = Registry(args.registry)
        if args.keys:
            recs = records_for_status(reg, keys=args.keys)
        elif args.run:
            recs = records_for_status(reg, run=args.run, unfiltered=True)
        else:
            recs = records_for_status(reg, unfiltered=True)
        items = items_from_records(recs)
    if args.limit:
        items = items[:args.limit]
    return items, reg


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    paths.check_id(args.batch_id, "batch_id")
    if args.probe_only:
        if not args.validation_file:
            raise SystemExit("--probe-only applies to --validation-file only (it never writes the registry)")
        args.no_second_opinion = True
    items, reg = select_items(args)
    if not items:
        print("nothing to filter", file=sys.stderr)
        return 0
    est, plan = build_estimate(items, args)
    print(f"plan: {json.dumps(plan)}")
    print("estimate:\n" + est.format())
    refused: Optional[str] = None
    cap = None
    try:
        # a refusal prints its reason to stderr itself (cost.CostRefused)
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
        print(f"hard cap: ${cap:.2f}")
    except CostRefused as exc:
        refused = exc.msg
    sha = git_sha()
    dirty = platform_dirty_files()
    dirty_check = {"paths": list(PLATFORM_PATHS), "dirty": dirty,
                   "note": None if dirty is not None else "git unavailable: not checked"}
    if refused is None and dirty and not args.allow_dirty:
        refused = (f"uncommitted changes to the platform's own code or prompt paths ({len(dirty)}: "
                   f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty to "
                   f"record a run whose code and prompt the git sha does not identify")
        print(f"REFUSED: {refused}", file=sys.stderr)
    out_dir = paths.filter_dir(args.batch_id, candidates_dir=args.out_root)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/ and {'the registry ' + str(args.registry) if reg else 'no registry'}")
        print(f"system prompt: {len(fr.SYSTEM_PROMPT)} chars (rubric v{fr.TRAITHOOD_RUBRIC_VERSION}); "
              f"prompt sha256: {json.dumps(PROMPT_SHA256)}")
        if args.probe_only:
            payload = [{"id": i + 1, "label": it.label} for i, it in enumerate(items[:args.batch_size])]
            print(f"--- probe prompt 1 (probe rubric v{fr.PROBE_RUBRIC_VERSION}) ---\n{fr.build_probe_prompt(payload)}")
            return 0
        llm = [it for it in items if not zipf_info(it.label, familiarity=it.familiarity, gloss_hint=bool(it.intended_sense), curated=it.curated).hard_reject]
        random.Random(args.shuffle_seed).shuffle(llm)
        for b in range(min(3, math.ceil(len(llm) / args.batch_size))):
            chunk = llm[b * args.batch_size:(b + 1) * args.batch_size]
            payload = [{"id": i + 1, "label": it.label, "intended_sense": it.intended_sense}
                       for i, it in enumerate(chunk)]
            print(f"--- prompt {b + 1} ---\n{fr.build_batch_prompt(payload)}")
        return 0
    if refused:
        return 2

    if out_dir.exists():
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id or pass --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
        print(f"moved the old batch to {bak}", file=sys.stderr)
    out_dir.mkdir(parents=True)
    run_meta = {"batch_id": args.batch_id, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv,
                "plan": plan, "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "budget_usd": args.budget_usd, "cap_usd": cap, "confirmed_by": args.confirmed_by,
                "model": args.model, "second_model": None if args.no_second_opinion else args.second_model,
                "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "probe_rubric_version": fr.PROBE_RUBRIC_VERSION,
                "prompt_sha256": dict(PROMPT_SHA256), "probe_only": bool(args.probe_only), "started_at": utc_now()}
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    runner = FilterRunner(client=client, batch_id=args.batch_id, model=args.model,
                          second_model=None if args.no_second_opinion else args.second_model, usage=usage,
                          batch_size=args.batch_size, second_opinion_frac=args.second_opinion_frac, seed=args.seed,
                          probe=not args.no_probe, second_opinion=not args.no_second_opinion,
                          concurrency=args.concurrency, shuffle_seed=args.shuffle_seed,
                          responses_path=out_dir / "responses.jsonl", probe_only=args.probe_only)
    status = 0
    error: Optional[BaseException] = None
    try:
        runner.run(items)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    except BaseException as exc:  # noqa: BLE001 - recorded below, then re-raised
        error = exc
        print(f"STOPPED by {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        # Whatever stopped the run, keep everything paid for (review_m1_fixes.md item 3).
        _finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error)
    return status


def _finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error) -> None:
    """Write usage.json, the responses (re-written whole so the per-call lines
    gain their parse errors), results.jsonl, summary.json, the registry rows
    and run.json.  Called from ``main``'s ``finally``."""
    usage.write_json(out_dir / "usage.json")
    write_jsonl(runner.responses, out_dir / "responses.jsonl")
    results = [runner.results[it.key] for it in items if it.key in runner.results]
    write_jsonl([r.as_dict() for r in results], out_dir / "results.jsonl")
    runner.warn_parse_rate(logger)
    summary = summarize(results, stats=runner.stats, usage=usage,
                        stratum_key="stratum" if args.validation_file else None)
    summary.update({"batch_id": args.batch_id, "stopped_by_budget": status == 2,
                    "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                    "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "model": args.model,
                    "second_model": run_meta["second_model"]})
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    inputs = []
    if args.validation_file:
        inputs.append(current_file_input(dep_key="validation_file", path=args.validation_file,
                                         extras={"sample_frac": str(args.sample_frac),
                                                 "sample_seed": str(args.sample_seed)}))
    env = json_metadata(summary, title=f"traithood_filter {args.batch_id}", inputs=inputs or None)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "summary.json")
    if reg is not None:
        done = {r.key: r.registry_fields() for r in results if r.filter is not None}
        if done:
            # whole blocks from this pass replace a previous pass's (review_m1.md finding 5)
            reg.update_many(done, merge_blocks=False)
        n_left = sum(1 for r in results if r.stage in ("failed", "pending"))
        print(f"registry: {len(done)} rows updated ({n_left} failed or pending rows left unfiltered)")
    run_meta["finished_at"] = utc_now()
    run_meta["cost_usd"] = round(usage.total_cost_usd, 4)
    run_meta["stopped_by_error"] = summary["stopped_by_error"]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    print(usage.log_line())
    print(json.dumps({k: summary[k] for k in ("n", "verdict_counts", "parse_rate", "polysemy_rate", "cost_usd",
                                             "cost_per_candidate_usd", "second_opinion_n", "disagreements")}))


if __name__ == "__main__":
    sys.exit(main())
