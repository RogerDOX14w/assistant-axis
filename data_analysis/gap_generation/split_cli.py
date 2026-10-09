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
3 (with ``--stop-on-disagreement`` only: the disagreement tripwire stopped the run, or tripped at its end,
without ``--accept-disagreement``).  By default a trip is a warning: the run finishes and exits 0, and the
trip is recorded as ``tripwire`` with action ``warned`` (Roger, 2026-10-09).
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
from assistant_axis.gapgen import prompt_labels as PL
from assistant_axis.gapgen import split_rubrics as sr
from assistant_axis.gapgen.batches import BatchTransport, choose_transport
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort
from assistant_axis.gapgen.freq import zipf_info
from assistant_axis.gapgen.registry import utc_now, utc_stamp
from assistant_axis.gapgen.runs import PLATFORM_PATHS
from assistant_axis.gapgen.split_runner import (
    DisagreementStop, SplitRunner, cache_stats, default_readings, token_source, tokens_for,
)
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage

logger = logging.getLogger("traithood_filter")

#: The exit status of a run the disagreement tripwire stopped, or marked at its end, without
#: ``--accept-disagreement`` (a budget stop or refusal is 2, an existing batch dir 1).
TRIPWIRE_EXIT = 3

#: Shares used by the estimate for a first model with no measured table (measured on the 99 test words with
#: Haiku 4.5, 2026-09-29): primary readings for each word 1.3; a same-sense check for 0.3 of words; 0.75 go on
#: as traits (74 of 99); the second opinion on about 0.2 of words at the default --second-opinion-frac 0.10
#: (the seeded sample plus the flagged words); another fraction moves the share by the difference.
READINGS_PER_WORD = 1.3
SAME_SENSE_SHARE = 0.3
TRAIT_SHARE = 0.75
SECOND_OPINION_SHARE = 0.2
DEFAULT_SECOND_OPINION_FRAC = 0.10
DEFAULT_SHARES: dict[str, float] = {"readings_per_word": READINGS_PER_WORD, "same_sense": SAME_SENSE_SHARE,
                                    "trait": TRAIT_SHARE, "second_opinion": SECOND_OPINION_SHARE}
#: The shares by first-model fragment, measured on the recorded split runs (the platform close-out, 2026-10-08;
#: :func:`measured_shares` over :data:`SHARES_SOURCE_RUNS`, pooled, first-attempt calls, a verdict step's first
#: reading only).  Haiku 5.5 reads fewer primary readings and asks the same-sense check far less often than
#: Haiku 4.5 (0.96 and 0.04 a word against 1.41 and 0.37), which is most of why the estimates over-stated it.
#: Opus 5.5 and Sonnet 5.5 never ran with a second opinion, so that share is the default for them.  Words:
#: Haiku 5.5 2,506 (198 with a second model), Haiku 4.5 4,327 (4,291), Opus 5.5 710, Sonnet 5.5 143.
SHARES_BY_MODEL: dict[str, dict[str, float]] = {
    "haiku-5-5": {"readings_per_word": 0.96, "same_sense": 0.04, "trait": 0.65, "second_opinion": 0.12},
    "haiku-4-5": {"readings_per_word": 1.41, "same_sense": 0.37, "trait": 0.70, "second_opinion": 0.13},
    "opus-5-5": {"readings_per_word": 1.30, "same_sense": 0.26, "trait": 0.69},
    "sonnet-5-5": {"readings_per_word": 1.27, "same_sense": 0.30, "trait": 0.70},
}
#: The runs each table was measured on (``data/candidates/filter/<batch>/``; the second-opinion share only on
#: those with a second model at the default fraction).
SHARES_SOURCE_RUNS: dict[str, tuple[str, ...]] = {
    "haiku-5-5": ("h55_m1_validation_pool", "h55_m1_validation_pool_rep2", "h55_opus_audit_sample",
                  "h55_opus_audit_sample_rep2", "h55_split_test_words", "h55_split_test_words_rep2", "h55_verdict_600",
                  "h55_verdict_600_rep2", "h55_verdict_600_rep3", "h55_x3_split_test_words"),
    "haiku-4-5": ("h45_split_test_words_36", "m1_stability", "m1_stability_r2", "m1_validation", "m1_validation_r2",
                  "m3_pilot_antonym_check", "r6_split_test_words", "r7_split_test_words", "split_pilot_batches",
                  "split_pilot_live"),
    "opus-5-5": ("m1_r2_opus_audit", "opus55_verdict_600"),
    "sonnet-5-5": ("m3_pilot_m1_validation",),
}


def shares_for(model: str) -> dict[str, float]:
    """The estimate's shares for a run whose first model is ``model``: its measured table
    (:data:`SHARES_BY_MODEL`), any share it lacks from :data:`DEFAULT_SHARES`."""
    m = str(model).lower()
    table = next((t for frag, t in SHARES_BY_MODEL.items() if frag in m), {})
    return DEFAULT_SHARES | table


def share_source(model: str) -> str:
    """Where :func:`shares_for` takes ``model``'s shares from, for the dry run."""
    m = str(model).lower()
    frag = next((f for f in SHARES_BY_MODEL if f in m), None)
    if frag is None:
        return "the default shares (Haiku 4.5 on the 99 test words, 2026-09-29)"
    return f"measured on {frag} ({len(SHARES_SOURCE_RUNS[frag])} recorded runs)"


def measured_shares(run_dirs) -> dict[str, dict]:
    """The estimate's shares per first model over recorded split runs (``filter/<batch>/``, each with
    ``run.json`` and ``responses.jsonl``): first-attempt calls only (a ``_retry`` stage is left out) and a verdict
    step's first reading only.  Per model: ``n_words`` (step-1 calls), ``readings_per_word`` (established calls per
    word: the primary readings that reach step 2), ``same_sense`` (same-sense checks per word), ``trait``
    (alignment calls per word: the words that go on as traits), and ``second_opinion`` (second-opinion step-1
    calls per word, over the runs with a second model at the default ``--second-opinion-frac``; ``None`` when no
    such run), with ``n_runs`` and ``n_words_second``."""
    from collections import Counter, defaultdict
    tot: dict[str, Counter] = defaultdict(Counter)
    for d in map(Path, run_dirs):
        run = json.loads((d / "run.json").read_text(encoding="utf-8"))
        if run.get("pipeline") != "split" or not run.get("model"):
            continue
        argv = list(run.get("argv") or [])
        frac = float(argv[argv.index("--second-opinion-frac") + 1]) if "--second-opinion-frac" in argv \
            else DEFAULT_SECOND_OPINION_FRAC
        c = Counter()
        for line in (d / "responses.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("stage") or "").endswith("_retry") or (r.get("verdict_reading") or 1) != 1:
                continue
            c[f"{r.get('role')}:{r.get('step')}"] += 1
        t = tot[run["model"]]
        t["n_runs"] += 1
        t["words"] += c["first:sense"]
        for step in ("established", "same_sense", "alignment"):
            t[step] += c[f"first:{step}"]
        if run.get("second_model") and abs(frac - DEFAULT_SECOND_OPINION_FRAC) < 1e-9:
            t["words_second"] += c["first:sense"]
            t["second_sense"] += c["second:sense"]
    out = {}
    for model, t in sorted(tot.items()):
        w = t["words"]
        out[model] = {"n_runs": t["n_runs"], "n_words": w, "n_words_second": t["words_second"],
                      "readings_per_word": round(t["established"] / w, 4) if w else None,
                      "same_sense": round(t["same_sense"] / w, 4) if w else None,
                      "trait": round(t["alignment"] / w, 4) if w else None,
                      "second_opinion": round(t["second_sense"] / t["words_second"], 4) if t["words_second"] else None}
    return out


def second_opinion_share(args, shares: Optional[dict] = None) -> float:
    """The share of words estimated to get the second (and third) opinion (``shares``: the first model's,
    :func:`shares_for`)."""
    if args.no_second_opinion:
        return 0.0
    base = (shares or shares_for(getattr(args, "model", "")))["second_opinion"]
    frac = getattr(args, "second_opinion_frac", DEFAULT_SECOND_OPINION_FRAC)
    return min(1.0, max(0.0, base + frac - DEFAULT_SECOND_OPINION_FRAC))


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
    :func:`split_runner.tokens_for` (Haiku 5.5's measured, thinking included).  Shares (primary readings per
    word, same-sense checks, words going on as traits, second opinions): the first model's measured table,
    :func:`shares_for`; a second (or third) opinion's own primary readings and same-sense checks at the shares
    of its model."""
    n_read = getattr(args, "readings", None) or 1
    sh = shares_for(args.model)
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
        add(f"{step}{rd}", step, first, n_read * sh["readings_per_word"] * n)
    add(f"same sense{rd}", "same_sense", first, n_read * sh["same_sense"] * n)
    if not args.no_plain_reading and n_int:
        add("comparison", "comparison", args.compare_model, sh["readings_per_word"] * n_int)
    so = second_opinion_share(args, sh) * n
    add("gloss", "gloss", first, sh["trait"] * (n - so))
    add("alignment", "alignment", first, sh["trait"] * n)
    add("descriptors", "descriptors", first, sh["trait"] * n)
    third = getattr(args, "third_model", None) if so else None
    for name, model, gloss in (("second", second, True), ("third", third, False)):
        if not (so and model):
            continue
        osh = shares_for(model)
        add(f"{name} opinion: sense", "sense", model, so)
        for step in ("established", "vague", "kind"):
            add(f"{name} opinion: {step}", step, model, osh["readings_per_word"] * so)
        add(f"{name} opinion: same sense", "same_sense", model, osh["same_sense"] * so)
        if gloss:
            add(f"{name} opinion: gloss", "gloss", model, sh["trait"] * so)
    models = [first] + ([args.compare_model] if not args.no_plain_reading and n_int else []) \
        + ([second] if so and second else []) + ([third] if third else [])
    plan = {"pipeline": "split", "n_rows": len(items), "n_hard_reject": n_hard, "n_to_step1_or_probe": n,
            "n_probe_band": n_probe, "n_with_intended_sense": n_int, "transport": transport,
            "n_second_opinion_est": int(math.ceil(so)), "third_model": third or None, "readings": n_read,
            "token_figures": {m: token_source(m, first) for m in dict.fromkeys(models)},
            "shares": {m: {"source": share_source(m), **shares_for(m)} for m in dict.fromkeys([first, second, third])
                       if m}}
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
    # the prompts' label form (prompt_labels): a resume keeps the batch's recorded form (a batch before 2026-10-09
    # recorded none: "stored"); a new batch shows the judge display form (a no-op for a label without a standard)
    peek = out_dir / "run.json"
    label_form = PL.resolve_label_form(
        earlier=json.loads(peek.read_text(encoding="utf-8")) if args.resume and peek.exists() else None)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/ and {'the registry ' + str(args.registry) if reg else 'no registry'}")
        pins = sr.current_versions()
        print("split prompts: " + json.dumps({n: {"version": pins.get(n, (None,))[0],
                                                  "sha256": sr.sha256(sr.load_prompt(n))[:12]} for n in sr.NAMES}))
        print(f"label form: {label_form}")
        for it in items[:3]:
            payload = split.payload("sense", label=it.label, label_form=label_form)
            print(f"--- step 1 payload for {it.key} ---\n{payload}")
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
                "stop_on_disagreement": bool(getattr(args, "stop_on_disagreement", False)),
                "step_versions": {n: v for n, (v, _) in pins.items()},
                # the eight split prompts, plus the two single-pipeline prompts the split also sends
                "prompt_sha256": {**{n: sr.sha256(sr.load_prompt(n)) for n in sr.NAMES},
                                  "probe": sr.sha256(fr.DEFINE_PROBE_PROMPT),
                                  "comparison": pr.PROMPT_SHA256["comparison"]},
                "probe_rubric_version": fr.PROBE_RUBRIC_VERSION,
                "comparison_version": pr.COMPARISON_VERSION,
                "measurement": bool(args.measurement), "stability": bool(args.stability),
                PL.LABEL_FORM_KEY: label_form, "resumed": bool(args.resume), "started_at": utc_now()}
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
                         readings=args.readings, stop_on_disagreement=bool(getattr(args, "stop_on_disagreement", False)),
                         label_form=label_form)
    if transport == "batches":
        runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap)
    run_meta["cached_steps"] = runner.cached_steps()   # the prompts sent with cache_control, by model
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
        if tw and tw.get("action") == "warned":
            print(f"WARNING (tripwire): first-vs-second disagreement over {tw['threshold']:.1%} "
                  f"({', '.join(tw['tripped_by'])}); the run went on (summary.json and run.json \"tripwire\"; "
                  f"--stop-on-disagreement to stop instead)", file=sys.stderr)
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
            "cache": cache_stats(runner.responses), "cached_steps": runner.cached_steps(),
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
