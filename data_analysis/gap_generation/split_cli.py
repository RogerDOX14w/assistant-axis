"""``traithood_filter.py --pipeline split``: the split filter's side of the CLI.

Kept apart from ``traithood_filter.py`` so the single-call path there stays as it was; the flags,
the inputs (registry selectors, validation files, samples), the cost gate, the dirty-tree check and
the outputs are the same.  See that script's docstring and coding_plan_split.md section 7.

Outputs in ``data/candidates/filter/<batch_id>/``: ``responses.jsonl`` (every response received,
appended as it arrives, one item each), ``results.jsonl``, ``summary.json`` (with a ``split`` block:
the pilot figures, the parse rate of every step and model, the spend by step), ``usage.json``
(always), ``run.json`` and, with the batches transport, ``batches.json``.
"""
from __future__ import annotations

import json
import logging
import math
import shutil
import sys
from pathlib import Path
from typing import Optional

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen import filter_rubric as fr
from assistant_axis.gapgen import paths, split
from assistant_axis.gapgen import plain_reading as pr
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.batches import BatchTransport, choose_transport
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort
from assistant_axis.gapgen.freq import zipf_info
from assistant_axis.gapgen.registry import utc_now, utc_stamp
from assistant_axis.gapgen.runs import PLATFORM_PATHS
from assistant_axis.gapgen.split_runner import SplitRunner, tokens_for
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage

logger = logging.getLogger("traithood_filter")

#: Shares used by the estimate (measured on the 99 test words, 2026-09-29): primary readings for
#: each word 1.3; a same-sense check for 0.3 of words; 0.75 go on as traits (74 of 99); the second
#: opinion on about 0.2 of words.
READINGS_PER_WORD = 1.3
SAME_SENSE_SHARE = 0.3
TRAIT_SHARE = 0.75
SECOND_OPINION_SHARE = 0.2


def build_split_estimate(items, args, transport: str) -> tuple[Estimate, dict]:
    """The estimate by step (section 7), at batch rates when ``transport`` is batches."""
    n_hard = n_probe = 0
    for it in items:
        fq = zipf_info(it.label, familiarity=it.familiarity, gloss_hint=bool(it.intended_sense), curated=it.curated)
        n_hard += fq.hard_reject
        n_probe += (not fq.hard_reject) and fq.probe_band
    n = len(items) - n_hard
    n_int = sum(1 for it in items if it.intended_sense)
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    first, second = args.model, args.second_model
    est = Estimate()

    def add(label, step, model, n_calls):
        i, o = tokens_for(step, model, first)
        est.add(label, model + suffix, int(math.ceil(n_calls)), i, o)

    if not args.no_probe:
        add("definition probe", "probe", first, n_probe)
    add("sense", "sense", first, n)
    for step in ("established", "vague", "kind"):
        add(step, step, first, READINGS_PER_WORD * n)
    add("same sense", "same_sense", first, SAME_SENSE_SHARE * n)
    if not args.no_plain_reading and n_int:
        add("comparison", "comparison", args.compare_model, READINGS_PER_WORD * n_int)
    so = 0 if args.no_second_opinion else SECOND_OPINION_SHARE * n
    add("gloss", "gloss", first, TRAIT_SHARE * (n - so))
    add("alignment", "alignment", first, TRAIT_SHARE * n)
    add("descriptors", "descriptors", first, TRAIT_SHARE * n)
    if so:
        add("second opinion: sense", "sense", second, so)
        for step in ("established", "vague", "kind"):
            add(f"second opinion: {step}", step, second, READINGS_PER_WORD * so)
        add("second opinion: same sense", "same_sense", second, SAME_SENSE_SHARE * so)
        add("second opinion: gloss", "gloss", second, TRAIT_SHARE * so)
    plan = {"pipeline": "split", "n_rows": len(items), "n_hard_reject": n_hard, "n_to_step1_or_probe": n,
            "n_probe_band": n_probe, "n_with_intended_sense": n_int, "transport": transport,
            "n_second_opinion_est": int(math.ceil(so))}
    return est, plan


def main_split(args, argv) -> int:
    from data_analysis.gap_generation import traithood_filter as tf
    if args.batch_size is not None:
        print("REFUSED: --batch-size applies to --pipeline single only (the split filter sends one item per call)",
              file=sys.stderr)
        return 2
    if args.probe_only:
        raise SystemExit("--probe-only applies to --pipeline single only")
    tf.apply_stability(args)
    items, reg = tf.select_items(args)
    if not items:
        print("nothing to filter", file=sys.stderr)
        return 0
    problems = sr.mismatches()
    if problems:
        for p in problems:
            print(f"REFUSED (rubric not pinned): {p}", file=sys.stderr)
        print("pin the text first:\n" + sr.bump_command(problems), file=sys.stderr)
        if not args.dry_run:
            return 2
    transport, why = choose_transport(args.transport, len(items))
    est, plan = build_split_estimate(items, args, transport)
    print(f"plan: {json.dumps(plan)}")
    print(f"transport: {transport} ({why})")
    if args.stability and plan["n_to_step1_or_probe"] < tf.STABILITY_MIN_LLM_ROWS:
        print(f"REFUSED: the stability sample sends {plan['n_to_step1_or_probe']} rows to the model, fewer than "
              f"{tf.STABILITY_MIN_LLM_ROWS}", file=sys.stderr)
        return 2
    print("estimate by step:\n" + est.format())
    n_words = max(1, plan["n_to_step1_or_probe"])
    print(f"  = ${est.usd / n_words:.4f} a word")
    refused: Optional[str] = None
    cap = None
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
        print(f"hard cap: ${cap:.2f}")
    except CostRefused as exc:
        refused = exc.msg
    # through traithood_filter's names, so the single and split paths share one check
    sha = tf.git_sha()
    dirty = tf.platform_dirty_files()
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
        pins = sr.current_versions()
        print("split prompts: " + json.dumps({n: {"version": pins.get(n, (None,))[0],
                                                  "sha256": sr.sha256(sr.load_prompt(n))[:12]} for n in sr.NAMES}))
        for it in items[:3]:
            print(f"--- step 1 payload for {it.key} ---\n{split.payload('sense', label=it.label)}")
        return 0
    if refused:
        return 2

    resume_records: list[dict] = []
    earlier_run = None
    if out_dir.exists():
        if args.resume:
            rp = out_dir / "responses.jsonl"
            if rp.exists():
                resume_records = [json.loads(x) for x in rp.read_text(encoding="utf-8").splitlines() if x.strip()]
            if (out_dir / "run.json").exists():
                earlier_run = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
            print(f"resuming {out_dir}: {len(resume_records)} responses on record", file=sys.stderr)
        elif args.overwrite:
            bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
            shutil.move(str(out_dir), str(bak))
            print(f"moved the old batch to {bak}", file=sys.stderr)
        else:
            print(f"{out_dir} exists; choose a new --batch-id, pass --resume to continue it, or --overwrite",
                  file=sys.stderr)
            return 1
    elif args.resume:
        print(f"--resume: {out_dir} does not exist", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    pins = sr.current_versions()
    run_meta = {"batch_id": args.batch_id, "pipeline": "split", "rubric_version": split.RUBRIC_VERSION,
                "git_sha": sha, "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check,
                "argv": sys.argv[1:] if argv is None else argv, "plan": plan, "transport": transport,
                "transport_reason": why, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by, "model": args.model,
                "second_model": None if args.no_second_opinion else args.second_model,
                "compare_model": args.compare_model, "plain_reading": not args.no_plain_reading,
                "step_versions": {n: v for n, (v, _) in pins.items()},
                # the eight split prompts, plus the two single-pipeline prompts the split also sends
                "prompt_sha256": {**{n: sr.sha256(sr.load_prompt(n)) for n in sr.NAMES},
                                  "probe": sr.sha256(fr.DEFINE_PROBE_PROMPT),
                                  "comparison": pr.PROMPT_SHA256["comparison"]},
                "probe_rubric_version": fr.PROBE_RUBRIC_VERSION,
                "comparison_version": pr.COMPARISON_VERSION,
                "measurement": bool(args.measurement), "stability": bool(args.stability),
                "resumed": bool(args.resume), "started_at": utc_now()}
    if earlier_run:
        run_meta["earlier_sessions"] = list(earlier_run.pop("earlier_sessions", [])) + [earlier_run]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    from dotenv import load_dotenv
    import anthropic
    load_dotenv(tf._REPO_ROOT / ".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    if args.resume:
        from assistant_axis.gapgen.batches import with_current_batch_keys
        usage.merge_from(with_current_batch_keys(MultiModelUsage.load_or_create(out_dir / "usage.json")))
    runner = SplitRunner(client=client, batch_id=args.batch_id, model=args.model,
                         second_model=None if args.no_second_opinion else args.second_model,
                         compare_model=args.compare_model, usage=usage,
                         second_opinion_frac=args.second_opinion_frac, seed=args.seed, probe=not args.no_probe,
                         second_opinion=not args.no_second_opinion, concurrency=args.concurrency,
                         responses_path=out_dir / "responses.jsonl", resume_records=resume_records,
                         plain_reading=not args.no_plain_reading)
    if transport == "batches":
        runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap)
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
        finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error, transport)
    return status


def finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error, transport) -> None:
    """``traithood_filter._finalize`` with the split block added to the summary."""
    from data_analysis.gap_generation import traithood_filter as tf

    def extra(s: dict, results) -> None:
        rows = [r.as_dict() for r in results]
        cbs = split.cost_by_step(runner.responses)
        n_words = max(1, runner.stats.get("n_llm", 0))
        s["split"] = {
            "transport": transport, "pilot_figures": split.pilot_figures(rows),
            "step_parse_rates": runner.step_parse_rates(), "cost_by_step": cbs,
            "cost_per_word_by_step": {k: round(v["cost_usd"] / n_words, 6) for k, v in cbs.items()},
            "second_opinion": {"n": len(runner.second_keys),
                               "disagree": sorted(r.label for r in results
                                                  if ((r.filter or {}).get("second_opinion") or {}).get("agree")
                                                  is False)},
            "resumed_calls": runner.stats.get("resumed", 0),
            "batches_submitted": getattr(runner.transport, "submitted", None),
        }
        s["rubric_version"] = split.RUBRIC_VERSION
        s["pipeline"] = "split"
        # filter.summarize counts second opinions by the single pipeline's "verdict" key; a split
        # block records "outcome", so set the two top-level figures from the split's own records
        s["second_opinion_n"] = len(runner.second_keys)
        s["disagreements"] = len(s["split"]["second_opinion"]["disagree"])
        # the alignment score (0 to 3) beside the count of the boolean derived from it
        s.setdefault("v2_fields", {})["alignment_scores"] = alignment_score_counts(results)

    tf._finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error, extra_summary=extra)


def alignment_score_counts(results) -> dict:
    """``{"0": n, "1": n, "2": n, "3": n, "none": n}`` over the classified rows that went on as
    traits (the only rows that get the alignment call); "none" counts those whose call failed."""
    out = {str(k): 0 for k in split.ALIGNMENT_SCORES} | {"none": 0}
    for r in results:
        f = r.filter or {}
        if r.stage != "classified" or f.get("outcome") != "trait":
            continue
        a = f.get("alignment")
        ok = isinstance(a, int) and not isinstance(a, bool) and a in split.ALIGNMENT_SCORES
        out[str(a) if ok else "none"] += 1
    return out
