"""``traithood_filter.py --pipeline split``: the split filter's side of the CLI.

Kept apart from ``traithood_filter.py`` so the single-call path there stays as it was; the flags,
the inputs (registry selectors, validation files, samples), the cost gate, the dirty-tree check and
the outputs are the same.  See that script's docstring and coding_plan_split.md section 7.

Outputs in ``data/candidates/filter/<batch_id>/``: ``responses.jsonl`` (every response received,
appended as it arrives, one item each), ``results.jsonl``, ``summary.json`` (with a ``split`` block:
the pilot figures, the parse rate of every step and model, the spend by step; the opinions'
``agreement`` section, the ``tripwire`` and ``stopped_by_disagreement``), ``usage.json``
(always), ``run.json`` (also ``third_model``, ``third_opinion``, ``max_disagreement``,
``accept_disagreement``, ``tripwire``, ``stopped_by_disagreement``) and, with the batches transport,
``batches.json``.  Exit status: 0, or 1 (the batch dir exists), 2 (refused, or the budget stop),
3 (the disagreement tripwire stopped the run, or tripped at its end, without
``--accept-disagreement``).
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
from assistant_axis.gapgen.split_runner import (
    DisagreementStop, SplitRunner, default_readings, token_source, tokens_for,
)
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage

logger = logging.getLogger("traithood_filter")

#: The exit status of a run the disagreement tripwire stopped, or marked at its end, without
#: ``--accept-disagreement`` (a budget stop or refusal is 2, an existing batch dir 1).
TRIPWIRE_EXIT = 3

#: Shares used by the estimate (measured on the 99 test words, 2026-09-29): primary readings for
#: each word 1.3; a same-sense check for 0.3 of words; 0.75 go on as traits (74 of 99); the second
#: opinion on about 0.2 of words at the default --second-opinion-frac 0.10 (the seeded sample plus
#: the flagged words); another fraction moves the share by the difference.
READINGS_PER_WORD = 1.3
SAME_SENSE_SHARE = 0.3
TRAIT_SHARE = 0.75
SECOND_OPINION_SHARE = 0.2
DEFAULT_SECOND_OPINION_FRAC = 0.10


def second_opinion_share(args) -> float:
    """The share of words estimated to get the second (and third) opinion."""
    if args.no_second_opinion:
        return 0.0
    frac = getattr(args, "second_opinion_frac", DEFAULT_SECOND_OPINION_FRAC)
    return min(1.0, max(0.0, SECOND_OPINION_SHARE + frac - DEFAULT_SECOND_OPINION_FRAC))


def resolve_readings(args) -> Optional[str]:
    """Set ``args.readings`` to its default when not given (:func:`split_runner.default_readings`: 3 on
    Haiku 5.5, else 1); why it is refused, or None."""
    n = getattr(args, "readings", None)
    if n is None:
        args.readings = default_readings(args.model)
        return None
    if n < 1:
        return f"--readings {n}: at least one reading"
    return None


def resume_mismatch(earlier_run: Optional[dict], args) -> Optional[str]:
    """Why ``--resume`` is refused: the batch's earlier session ran on another first model, or with another
    number of readings (a run before 2026-10-08 records no ``readings``: one).  The defaults moved to Haiku
    5.5 with three readings that day, so resuming an older batch without its ``--model`` would otherwise
    send the rest of it on the new model and vote differently."""
    if not earlier_run:
        return None
    m, n = earlier_run.get("model"), earlier_run.get("readings") or 1
    if m and m != args.model:
        return (f"the batch's earlier session ran on --model {m}, this one on {args.model}; resume with "
                f"--model {m} (and --readings {n})")
    if n != args.readings:
        return f"the batch's earlier session read the verdict waves {n} time(s), this one {args.readings}; resume with --readings {n}"
    return None


def check_opinion_args(args) -> Optional[str]:
    """Why ``--third-model`` / ``--max-disagreement`` are refused, or None."""
    third = getattr(args, "third_model", None)
    if third:
        if args.no_second_opinion:
            return "--third-model runs on the second opinion's rows: drop --no-second-opinion"
        if third in (args.model, args.second_model):
            return f"--third-model {third} must differ from --model and --second-model"
    m = getattr(args, "max_disagreement", None)
    if m is not None and not 0.0 <= m <= 1.0:
        return f"--max-disagreement {m} is not a fraction from 0 to 1 (0.10 is ten per cent; 1 turns the tripwire off)"
    return None


def build_split_estimate(items, args, transport: str) -> tuple[Estimate, dict]:
    """The estimate by step (section 7), at batch rates when ``transport`` is batches; a third
    opinion (``--third-model``) adds the second opinion's steps 1 to 3 on its model.  The first
    model's verdict steps (step 1, the checks, the same-sense check) are counted once for each of
    ``--readings``; the comparison, gloss, alignment and descriptors once.  Token figures per call:
    :func:`split_runner.tokens_for` (Haiku 5.5's measured, thinking included)."""
    n_read = getattr(args, "readings", None) or 1
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
    rd = f" ({n_read} readings)" if n_read > 1 else ""
    add(f"sense{rd}", "sense", first, n_read * n)
    for step in ("established", "vague", "kind"):
        add(f"{step}{rd}", step, first, n_read * READINGS_PER_WORD * n)
    add(f"same sense{rd}", "same_sense", first, n_read * SAME_SENSE_SHARE * n)
    if not args.no_plain_reading and n_int:
        add("comparison", "comparison", args.compare_model, READINGS_PER_WORD * n_int)
    so = second_opinion_share(args) * n
    add("gloss", "gloss", first, TRAIT_SHARE * (n - so))
    add("alignment", "alignment", first, TRAIT_SHARE * n)
    add("descriptors", "descriptors", first, TRAIT_SHARE * n)
    third = getattr(args, "third_model", None) if so else None
    for name, model, gloss in (("second", second, True), ("third", third, False)):
        if not (so and model):
            continue
        add(f"{name} opinion: sense", "sense", model, so)
        for step in ("established", "vague", "kind"):
            add(f"{name} opinion: {step}", step, model, READINGS_PER_WORD * so)
        add(f"{name} opinion: same sense", "same_sense", model, SAME_SENSE_SHARE * so)
        if gloss:
            add(f"{name} opinion: gloss", "gloss", model, TRAIT_SHARE * so)
    models = [first] + ([args.compare_model] if not args.no_plain_reading and n_int else []) \
        + ([second] if so and second else []) + ([third] if third else [])
    plan = {"pipeline": "split", "n_rows": len(items), "n_hard_reject": n_hard, "n_to_step1_or_probe": n,
            "n_probe_band": n_probe, "n_with_intended_sense": n_int, "transport": transport,
            "n_second_opinion_est": int(math.ceil(so)), "third_model": third or None, "readings": n_read,
            "token_figures": {m: token_source(m, first) for m in dict.fromkeys(models)}}
    return est, plan


def main_split(args, argv) -> int:
    from data_analysis.gap_generation import traithood_filter as tf
    if args.batch_size is not None:
        print("REFUSED: --batch-size applies to --pipeline single only (the split filter sends one item per call)",
              file=sys.stderr)
        return 2
    if args.probe_only:
        raise SystemExit("--probe-only applies to --pipeline single only")
    if args.max_disagreement is None:
        args.max_disagreement = split.DEFAULT_MAX_DISAGREEMENT
    bad = check_opinion_args(args) or resolve_readings(args)
    if bad:
        print(f"REFUSED: {bad}", file=sys.stderr)
        return 2
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
    print(f"readings: {args.readings} of the verdict waves per word"
          + (f" ({split.READINGS_RULE})" if args.readings > 1 else ""))
    print("token figures per call: " + "; ".join(f"{m}: {s}" for m, s in plan["token_figures"].items()))
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
            bad = resume_mismatch(earlier_run, args)
            if bad:
                print(f"REFUSED: {bad}", file=sys.stderr)
                return 2
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
                "readings": args.readings, "readings_rule": split.READINGS_RULE if args.readings > 1 else None,
                "second_model": None if args.no_second_opinion else args.second_model,
                "compare_model": args.compare_model, "plain_reading": not args.no_plain_reading,
                "third_model": args.third_model,
                # the third opinion runs the second opinion's steps, at these pinned versions
                "third_opinion": None if not args.third_model else {
                    "model": args.third_model, "on": "the second opinion's rows",
                    "step_versions": {n: pins[n][0] for n in split.SECOND_OPINION_STEPS if n in pins}},
                "max_disagreement": args.max_disagreement, "accept_disagreement": bool(args.accept_disagreement),
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
                         plain_reading=not args.no_plain_reading, third_model=args.third_model,
                         max_disagreement=args.max_disagreement, accept_disagreement=args.accept_disagreement,
                         readings=args.readings)
    if transport == "batches":
        runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap)
    status = 0
    error: Optional[BaseException] = None
    try:
        runner.run(items)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    except DisagreementStop as exc:
        print(f"STOPPED by the disagreement tripwire: {exc}.  Every answer paid for is kept; to go on "
              f"regardless: the same command with --resume --accept-disagreement", file=sys.stderr)
        status = TRIPWIRE_EXIT
    except BaseException as exc:  # noqa: BLE001 - recorded below, then re-raised
        error = exc
        print(f"STOPPED by {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        tw = runner.tripwire
        if status == 0 and tw and tw.get("action") == "marked":
            print(f"TRIPPED at the end: first-vs-second disagreement over {tw['threshold']:.1%} "
                  f"({', '.join(tw['tripped_by'])}); the run finished and is marked (summary.json and run.json "
                  f"\"tripwire\")", file=sys.stderr)
            status = TRIPWIRE_EXIT
        finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error, transport)
    return status


def finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error, transport) -> None:
    """``traithood_filter._finalize`` with the split block added to the summary, and the opinions'
    agreement section and the disagreement tripwire added to the summary and run.json."""
    from data_analysis.gap_generation import traithood_filter as tf
    stopped = bool(runner.tripwire and runner.tripwire.get("action") == "stopped")
    run_meta["tripwire"] = runner.tripwire
    run_meta["stopped_by_disagreement"] = stopped

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
            # the verdict readings: their agreement, the rule's rescues and ties (one reading: n_readings 1)
            "readings": runner.readings_summary(),
        }
        s["rubric_version"] = split.RUBRIC_VERSION
        s["pipeline"] = "split"
        # filter.summarize counts second opinions by the single pipeline's "verdict" key; a split
        # block records "outcome", so set the two top-level figures from the split's own records
        s["second_opinion_n"] = len(runner.second_keys)
        s["disagreements"] = len(s["split"]["second_opinion"]["disagree"])
        s["third_model"] = runner.third_model
        # the opinions, from the runner's state (complete on a run the tripwire stopped, whose rows
        # are still pending); see split.agreement_section and split.disagreement_tripwire
        s["agreement"] = runner.agreement() if runner.second_keys else None
        s["tripwire"] = runner.tripwire
        s["stopped_by_disagreement"] = stopped
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
