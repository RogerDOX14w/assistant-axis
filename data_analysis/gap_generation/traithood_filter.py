#!/usr/bin/env python3
"""Run the trait-hood filter over registry rows or a validation file.

    uv run python data_analysis/gap_generation/traithood_filter.py --batch-id B \\
        (--unfiltered | --keys K ... | --run GENERATOR/RUN_ID | --validation-file F) \\
        [--model claude-haiku-4-5-20251001] [--second-model claude-sonnet-4-6] \\
        [--batch-size 25] [--limit N] [--sample-frac F --sample-seed S] \\
        [--no-probe] [--no-second-opinion] [--budget-usd 5.0] [--confirm-expensive] \\
        [--confirmed-by WHO] [--dry-run]

Pipeline per row (``assistant_axis.gapgen.filter``): Zipf floor (hard reject
below 2.0, free) -> WordNet -> Haiku classifier (25 per call) -> definition
probe for 2.0 <= Zipf < 2.5 -> Sonnet second opinion (10% random + confidence
< 0.6 + prior/LLM disagreement).

Outputs in ``data/candidates/filter/<batch_id>/``: ``responses.jsonl`` (every
API response, parse errors included), ``results.jsonl`` (one row per
candidate), ``summary.json`` (``json_metadata`` envelope), ``usage.json``
(always, also when the budget cap stops the run) and ``run.json`` (args,
estimate, cap, ``confirmed_by``).  Registry modes also write the ``freq``,
``wordnet`` and ``filter`` blocks, ``gloss``, ``holding`` and ``entity_type``
into the registry; ``--validation-file`` never touches the registry.

Validation files are JSONL rows ``{"surface", "stratum", "expected"?,
"gloss_hint"?, "familiarity"?}``.  ``--sample-frac`` takes a stratified,
seeded sample (strata of 10 rows or fewer are taken whole): the pilot.

Cost: printed as ``n_calls x (in, out) tokens at model rates = $X``;
``--budget-usd`` is a hard cap (default $5), an estimate over it needs
``--confirm-expensive``, over $20 also ``--confirmed-by``.  ``--dry-run``
prints the plan, the estimate and the first three prompts, and writes and
calls nothing.
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
    DEFAULT_BATCH_SIZE, DEFAULT_MODEL, DEFAULT_SECOND_MODEL, FilterItem, FilterRunner, items_from_records,
    summarize,
)
from assistant_axis.gapgen.freq import zipf_info  # noqa: E402
from assistant_axis.gapgen.normalize import make_key, normalize_candidate  # noqa: E402
from assistant_axis.gapgen.registry import Registry, records_for_status, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import git_sha  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError  # noqa: E402

logger = logging.getLogger("traithood_filter")

# Token model for the estimate (first-of-kind; revise from the pilot's usage.json).
CHARS_PER_TOKEN = 3.6
IN_TOK_PER_ITEM = 30
OUT_TOK_PER_ITEM = 140
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
    n_hard = n_probe = 0
    for it in items:
        fq = zipf_info(it.label, familiarity=it.familiarity)
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
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float, default=5.0, help="hard cap (default 5.0)")
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", help="who gave the explicit go for a run over $20 (recorded in run.json)")
    ap.add_argument("--dry-run", action="store_true")
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
    items, reg = select_items(args)
    if not items:
        print("nothing to filter", file=sys.stderr)
        return 0
    est, plan = build_estimate(items, args)
    print(f"plan: {json.dumps(plan)}")
    print("estimate:\n" + est.format())
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
    except CostRefused as exc:
        print(f"REFUSED: {exc.msg}", file=sys.stderr)
        return 2
    print(f"hard cap: ${cap:.2f}")
    out_dir = paths.filter_dir(args.batch_id, candidates_dir=args.out_root)
    if args.dry_run:
        print(f"DRY-RUN: would write {out_dir}/ and {'the registry ' + str(args.registry) if reg else 'no registry'}")
        print(f"system prompt: {len(fr.SYSTEM_PROMPT)} chars (rubric v{fr.TRAITHOOD_RUBRIC_VERSION})")
        llm = [it for it in items if not zipf_info(it.label, familiarity=it.familiarity).hard_reject]
        random.Random(args.shuffle_seed).shuffle(llm)
        for b in range(min(3, math.ceil(len(llm) / args.batch_size))):
            chunk = llm[b * args.batch_size:(b + 1) * args.batch_size]
            payload = [{"id": i + 1, "label": it.label, "intended_sense": it.intended_sense}
                       for i, it in enumerate(chunk)]
            print(f"--- prompt {b + 1} ---\n{fr.build_batch_prompt(payload)}")
        return 0

    if out_dir.exists():
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id or pass --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
        print(f"moved the old batch to {bak}", file=sys.stderr)
    out_dir.mkdir(parents=True)
    run_meta = {"batch_id": args.batch_id, "git_sha": git_sha(), "argv": sys.argv[1:] if argv is None else argv,
                "plan": plan, "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "budget_usd": args.budget_usd, "cap_usd": cap, "confirmed_by": args.confirmed_by,
                "model": args.model, "second_model": None if args.no_second_opinion else args.second_model,
                "rubric_version": fr.TRAITHOOD_RUBRIC_VERSION, "started_at": utc_now()}
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
                          concurrency=args.concurrency, shuffle_seed=args.shuffle_seed)
    status = 0
    try:
        runner.run(items)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    finally:
        usage.write_json(out_dir / "usage.json")
        write_jsonl(runner.responses, out_dir / "responses.jsonl")
    results = [runner.results[it.key] for it in items if it.key in runner.results]
    write_jsonl([r.as_dict() for r in results], out_dir / "results.jsonl")
    runner.warn_parse_rate(logger)
    summary = summarize(results, stats=runner.stats, usage=usage,
                        stratum_key="stratum" if args.validation_file else None)
    summary.update({"batch_id": args.batch_id, "stopped_by_budget": status == 2,
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
            reg.update_many(done)
        print(f"registry: {len(done)} rows updated ({sum(1 for r in results if r.stage == 'failed')} failed rows "
              f"left unfiltered)")
    run_meta["finished_at"] = utc_now()
    run_meta["cost_usd"] = round(usage.total_cost_usd, 4)
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    print(usage.log_line())
    print(json.dumps({k: summary[k] for k in ("n", "verdict_counts", "parse_rate", "polysemy_rate", "cost_usd",
                                             "cost_per_candidate_usd", "second_opinion_n", "disagreements")}))
    return status


if __name__ == "__main__":
    sys.exit(main())
