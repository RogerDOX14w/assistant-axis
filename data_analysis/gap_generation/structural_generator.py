#!/usr/bin/env python3
"""The structural generators (workstream 9, generator id ``structural``).

    uv run python data_analysis/gap_generation/structural_generator.py classical [--scheme S ...]
    uv run python data_analysis/gap_generation/structural_generator.py modernise --run-id R [--scheme S ...]
        [--per-call 20] [--budget-usd 0.5] [--resume] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py operators --run-id R
        (--all | --traits STEM ... | --sample N --seed S) [--samples 3] [--principal-min-score 3 [--principal-only]
        [--prior-run R0 ...]] [--budget-usd 6] [--resume] [--render STEM ...] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py null-rate --run-id R [--n 20 --seed 0]
        [--samples 3] [--budget-usd 0.5] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py stability --run-id R [--against R2
        [--n 30 --seed 1] [--budget-usd 0.5] [--allow-dirty]] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py void --run-id R --reason TEXT --by WHO
    uv run python data_analysis/gap_generation/structural_generator.py postprocess [--run-id R ...]
        [--embedder openai|hash|none] [--budget-usd 0.1] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py side-table [--run-id R ...] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py submit --run-id R
        (--all | --kept-target 300 [--kept-share X]) [--transport live|batches] [--budget-usd 5]
        [--confirm-expensive --confirmed-by WHO] [--review-rate plan|measured] [--dry-run]
    uv run python data_analysis/gap_generation/structural_generator.py report --run-id R [--operator-run R0 ...]
        [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_09_structural_generators.md``.  Generator A: ``classical`` loads and
checks the hand-typed tables (``data/candidates/structural/classical/``; the VIA rows are refused until every one
carries ``verified_by``), ``modernise`` asks Haiku 5.5 for 1-3 modern labels per row.  Generator B: ``operators``
asks Haiku 5.5, three independent calls per corpus trait (``--samples``; Roger, 2026-10-13), for the trait's position
and its opposite, excess, deficiency, retargets and remodes (the principal targets for traits at
``--principal-min-score`` and above, default 3); the samples are combined by union (``combine.py``), each label with
its support.  ``null-rate`` is the pilot's gate (the 5-40% band over every sample); ``stability`` is reported, never a
gate: free between a run's own samples, or paid across two runs with ``--against``.  ``void`` marks a run the
readouts and the recorded-output checks skip.  ``postprocess`` builds the operator table and ``evaluation.json`` (free;
the gloss cosines of pair recovery cost pennies of embeddings with ``--embedder openai``), ``side-table`` the
position table and the negative-label mismatches, ``submit`` the run's candidates (``--all``, or the review-hour wave
``--kept-target 300`` counted on net-new rows), ``report`` the readouts.  Every paid command prints its estimate,
takes ``--budget-usd`` as a hard cap, writes ``usage.json``, refuses uncommitted platform code without
``--allow-dirty``, and runs live (every generator-side estimate is under $20; the full pass about $2.2 at three
samples).  ``--dry-run`` prints the estimate,
the counts and the rendered prompts, and writes and calls nothing.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import structural as S  # noqa: E402

#: Exit status of a pilot gate that fails (the null-rate band, the stability median): a prompt-revision round or
#: Roger's model decision, not an error.
EXIT_GATE = 3


# --------------------------------------------------------------------------- shared

def _anthropic_client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _run_dir(args, run_id: str) -> Path:
    paths.check_id(run_id, "run_id")
    return paths.run_dir(S.GENERATOR, run_id, candidates_dir=args.candidates_dir)


def _dirty(args) -> Optional[str]:
    from assistant_axis.gapgen.runs import dirty_refusal, platform_dirty_files
    refusal, _ = dirty_refusal(platform_dirty_files(), bool(getattr(args, "allow_dirty", False)))
    return refusal


def _sdir(args) -> Path:
    return Path(args.structural_dir)


def _registry_rows(args) -> dict:
    """The registry log folded, read without its lock (these commands only read it, and a dry run writes nothing,
    not even ``registry.jsonl.lock``); a line torn by a concurrent append is skipped with a warning."""
    from assistant_axis.gapgen.registry import read_snapshot
    p = Path(args.registry)
    return read_snapshot(p) if p.exists() else {}


def _print_estimate(label: str, e: dict, budget: float, model: str) -> float:
    n = max(1, e["n_calls"])
    print(f"  {label}: {e['n_calls']} calls x (~{e['in_tok'] // n:,} in, ~{e['out_tok'] // n:,} out) tokens at "
          f"{model} rates = ${e['usd']:.4f}; cap --budget-usd ${budget:.2f}")
    return e["usd"]


def _sha_file(p: Path) -> Optional[str]:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest() if Path(p).exists() else None


# --------------------------------------------------------------------------- A: classical, modernise

def cmd_classical(args) -> int:
    from assistant_axis.gapgen.generators.structural import classical as C
    schemes = args.scheme or list(C.SCHEMES)
    rows = C.load_all(schemes, classical_dir=args.classical_dir)
    probs = C.validate(rows)
    for s, c in C.counts(rows).items():
        print(f"{s:14s} {c['rows']:>3d} rows in {c['groups']:>3d} structures  {c['roles']}")
    for s, v in C.verification_state(rows).items():
        print(f"{s:14s} verified {v['verified']} of {v['n']}" + ("  [GATED: unreadable until every row is "
                                                                 "verified]" if v["gated"] and v["unverified"] else ""))
    for p in probs:
        print(f"PROBLEM {p}", file=sys.stderr)
    if probs:
        return 1
    if args.scheme:
        gate = C.gate_problems(rows, [s for s in args.scheme if s in C.GATED_SCHEMES])
        if gate:
            print(f"REFUSED: {'; '.join(gate)}", file=sys.stderr)
            return 2
    return 0


def _modernise_rows(args):
    from assistant_axis.gapgen.generators.structural import classical as C
    if args.scheme:
        rows = C.load_all(args.scheme, classical_dir=args.classical_dir)
        C.require_verified(rows, args.scheme)          # raises for an explicitly asked, unverified VIA
        return rows, []
    rows = C.load_all(classical_dir=args.classical_dir)
    skipped = [s for s in C.GATED_SCHEMES if C.gate_problems(rows, [s])]
    return [r for r in rows if r.scheme not in skipped], skipped


def cmd_modernise(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.structural import classical as C
    from assistant_axis.gapgen.generators.structural import modernise as M
    from assistant_axis.gapgen.generators.structural import prompts as P
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    try:
        rows, skipped = _modernise_rows(args)
    except C.SchemeUnverified as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    probs = C.validate(C.load_all(classical_dir=args.classical_dir))
    if probs:
        raise SystemExit(f"the classical tables have problems; run `classical` ({probs[0]})")
    try:
        rub = P.load_rubric(P.MODERNISE_RUBRIC, args.rubrics_dir, allow_unpinned=args.dry_run)
    except P.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    counts = {s: sum(1 for r in rows if r.scheme == s) for s in C.SCHEMES if any(r.scheme == s for r in rows)}
    print(f"modernise: {len(rows)} rows {counts}" + (f"; {', '.join(skipped)} left out (unverified: the gate)"
                                                     if skipped else ""))
    print(f"rubric {rub['name']} v{rub['version']} ({(rub['sha256'] or 'unpinned')[:12]}); model {args.model}; "
          f"{args.per_call} rows a call")
    est = M.estimate(rows, rub["text"], args.model, per_call=args.per_call)
    _print_estimate("modernise", est, args.budget_usd, args.model)
    cap = confirm_or_abort(est["usd"], args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    if args.dry_run:
        first = M.batches(rows, args.per_call)[0] if rows else []
        print(f"DRY-RUN: no call, nothing written.  System prompt = the fenced block of {rub['file']}.  The first "
              f"call's user turn ({len(first)} rows) as sent:\n{M.render_modernise_user(first, siblings_from=rows)}")
        return 0
    refused = _dirty(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    rdir = _run_dir(args, args.run_id)
    resp = rdir / S.RESPONSES_NAME
    ctx = start_run(S.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "modernise", "schemes": sorted(counts), "n_rows": len(rows), "per_call": args.per_call,
        "model": args.model, "budget_usd": args.budget_usd, "estimate_usd": est["usd"],
        "rubric": {k: rub[k] for k in ("name", "version", "sha256", "file")},
        "allow_dirty": bool(args.allow_dirty), "skipped_schemes": skipped})
    ctx.confirmed_by = args.confirmed_by
    ctx.usage = GuardedUsage(budget_usd=cap)
    run = M.ModerniseRun()
    try:
        client = _anthropic_client()
        run = asyncio.run(M.run_modernise(rows, client=client, model=args.model, usage=ctx.usage, system=rub["text"],
                                          run_id=args.run_id, out_path=resp, resume=True,
                                          per_call=args.per_call, rubric_version=rub["version"], now=utc_now))
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line("[usage this session]"), file=sys.stderr)
    warn_if_low_parse_rate(label=f"structural modernise:{args.model}", n_ok=run.n_units_ok, n_total=run.n_units)
    from assistant_axis.gapgen.generators.structural.operators import stop_summary
    stops = stop_summary(run.records)
    if stops["line"]:
        print(stops["line"], file=sys.stderr)
    new = M.modern_rows(rows, run, model=args.model, run_id=args.run_id)
    order = [r.id for r in C.load_all(classical_dir=args.classical_dir)]
    out = Path(args.classical_modern)
    merged = M.merge_modern(M.load_modern(out), new, order=order)
    bak = M.write_modern(merged, out)
    n_rej = sum(len(r.rejected_labels) for r in new)
    print(f"modernised {len(new)} of {len(rows)} rows ({len(run.missing)} unanswered{': ' + ', '.join(run.missing[:5]) if run.missing else ''}); "
          f"{sum(len(r.labels) for r in new)} labels, {n_rej} labels rejected by the label rule; reused "
          f"{run.n_reused} calls; wrote {out}" + (f" (snapshot {bak.name})" if bak else ""))
    return 1 if run.stopped_by_budget else 0


# --------------------------------------------------------------------------- B: operators

def _inputs(args, *, principal_only: bool = False):
    from assistant_axis.gapgen.generators.structural import operators as O
    return O.build_inputs(None, data_dir=Path(args.data_dir), regions_path=Path(args.regions),
                          principal_min_score=args.principal_min_score, principal_only=principal_only)


def _pairs(args) -> list[tuple[str, str]]:
    from assistant_axis.arrangements import load_corpus_arrangements
    recs = load_corpus_arrangements(Path(args.data_dir), "traits")
    out = set()
    for r in recs.values():
        for a in r.arrangements:
            if a.kind == "pair" and len(a.members) == 2:
                out.add(tuple(sorted(a.members)))
    return sorted(out)


def _structures(args) -> tuple[list, list]:
    from assistant_axis.arrangements import load_corpus_arrangements
    recs = load_corpus_arrangements(Path(args.data_dir), "traits")
    tri, seq = {}, {}
    for r in recs.values():
        for a in r.arrangements:
            if a.kind == "triangle":
                tri[frozenset(a.members)] = tuple(sorted(a.members))
            elif a.kind == "sequence":
                seq[a.members] = tuple(a.members)
    return sorted(tri.values()), sorted(seq.values(), key=lambda s: (-len(s), s))


def _variants(selected, everything) -> list[tuple[str, object]]:
    """One input per variant of the plan's section 7 (a singleton, a pair pole, a principal-target trait), from the
    selection where it has one, else from the corpus."""
    out = []
    for name, pred in (("a singleton", lambda t: t.arrangement_kind == "singleton" and not t.principal_targets),
                       ("a pair pole", lambda t: t.arrangement_kind.startswith("pair") and not t.principal_targets),
                       ("a principal-target trait", lambda t: t.principal_targets)):
        pick = next((t for t in selected if pred(t)), None)
        src = "in this selection"
        if pick is None:
            pick, src = next((t for t in everything if pred(t)), None), "from the corpus, not in this selection"
        if pick is not None:
            out.append((f"{name} ({src})", pick))
    return out


def _select_inputs(args, inputs, pairs):
    from assistant_axis.gapgen.generators.structural import operators as O
    if getattr(args, "all", False):
        return list(inputs)
    if getattr(args, "traits", None):
        by = {t.stem: t for t in inputs}
        missing = [s for s in args.traits if s not in by]
        if missing:
            raise SystemExit(f"not trait stems{' with the principal targets' if args.principal_only else ''}: "
                             f"{', '.join(missing)}")
        return [by[s] for s in dict.fromkeys(args.traits)]
    if getattr(args, "sample", None):
        return O.stratified_sample(inputs, args.sample, args.seed, pairs=pairs, n_pairs=args.sample_pairs,
                                   min_principal=args.sample_principal)
    raise SystemExit("give --all, --traits STEM ... or --sample N --seed S")


def _operators_session(args, run_id: str, selected, *, step: str, extra: Optional[dict] = None,
                       budget_usd: Optional[float] = None, samples: Optional[int] = None):
    """Run (or reuse) the operator calls of ``selected`` under ``run_id``, ``samples`` per trait (default
    ``args.samples``); returns ``(OperatorRun, usage, ok)``."""
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural import prompts as P
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, LABEL_FORM_KEY
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    rub = P.load_rubric(P.OPERATORS_RUBRIC, args.rubrics_dir)
    rdir = _run_dir(args, run_id)
    resp = rdir / S.RESPONSES_NAME
    ctx = start_run(S.GENERATOR, run_id, candidates_dir=args.candidates_dir, args={
        "step": step, "n_traits": len(selected), "stems": [t.stem for t in selected], "model": args.model,
        "principal_min_score": args.principal_min_score, "principal_only": bool(getattr(args, "principal_only", False)),
        "n_principal": sum(1 for t in selected if t.principal_targets), "budget_usd": args.budget_usd,
        "samples": samples or args.samples,
        "rubric": {k: rub[k] for k in ("name", "version", "sha256", "file")}, LABEL_FORM_KEY: DEFAULT_LABEL_FORM,
        "allow_dirty": bool(args.allow_dirty), **dict(extra or {})})
    ctx.usage = GuardedUsage(budget_usd=args.budget_usd if budget_usd is None else budget_usd)
    run = O.OperatorRun()
    try:
        client = _anthropic_client()
        run = asyncio.run(O.run_operators(selected, client=client, model=args.model, usage=ctx.usage,
                                          system=rub["text"], run_id=run_id, out_path=resp, resume=True,
                                          rubric_version=rub["version"], principal_min_score=args.principal_min_score,
                                          concurrency=args.concurrency, samples=samples or args.samples, now=utc_now))
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line(f"[usage this session, {run_id}]"), file=sys.stderr)
    warn_if_low_parse_rate(label=f"structural operators:{args.model}", n_ok=run.n_ok, n_total=run.n_attempted)
    stops = O.stop_summary(run.records)
    if stops["line"]:
        print(f"{stops['line']} [{run_id}]", file=sys.stderr)
    return run, ctx.usage, not run.stopped_by_budget


def _operators_plan(args, selected, inputs, rub) -> float:
    from assistant_axis.gapgen.generators.structural import operators as O
    est = O.estimate(selected, rub["text"], args.model, samples=args.samples)
    n_pr = sum(1 for t in selected if t.principal_targets)
    print(f"{len(selected)} traits x {args.samples} independent sample(s), combined by union ({n_pr} traits with "
          f"the principal targets at alignment score >= "
          f"{args.principal_min_score}); rubric {rub['name']} v{rub['version']} ({(rub['sha256'] or 'unpinned')[:12]}); "
          f"model {args.model}")
    return _print_estimate("operators", est, args.budget_usd, args.model)


def _render_variants(rub, selected, inputs, stems=None) -> None:
    from assistant_axis.gapgen.generators.structural import operators as O
    print(f"SYSTEM (rubric {rub['name']} version {rub['version']}): the fenced block of {rub['file']}, "
          f"{len(rub['text']):,} characters.")
    if stems:
        by = {t.stem: t for t in inputs}
        for s in stems:
            print(f"USER ({s}):\n{O.render_operator_user(by[s])}\n")
        return
    for name, ti in _variants(selected, inputs):
        print(f"USER, {name}: {ti.stem}\n{O.render_operator_user(ti)}\n")


def cmd_operators(args) -> int:
    from assistant_axis.gapgen.cost import confirm_or_abort
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural import prompts as P
    try:
        rub = P.load_rubric(P.OPERATORS_RUBRIC, args.rubrics_dir, allow_unpinned=args.dry_run or bool(args.render))
    except P.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    inputs = _inputs(args, principal_only=args.principal_only)
    if args.render:
        _render_variants(rub, [], _inputs(args), stems=args.render)
        return 0
    pairs = _pairs(args)
    selected = _select_inputs(args, inputs, pairs)
    if args.principal_only:
        prior = []
        for r in [args.run_id, *(args.prior_run or [])]:
            prior += O.read_responses(_run_dir(args, r) / S.RESPONSES_NAME)
        done = O.already_principal(prior)
        before = len(selected)
        selected = [t for t in selected if t.stem not in done]
        print(f"principal-only at score >= {args.principal_min_score}: {before} traits, {before - len(selected)} "
              f"already answered with the principal targets (skipped), {len(selected)} to send")
    total = _operators_plan(args, selected, inputs, rub)
    confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.dry_run:
        if args.principal_only:
            print("DRY-RUN: no call, nothing written.  The principal-only user turn:")
            _render_variants(rub, selected, selected, stems=[t.stem for t in selected[:1]])
            return 0
        print("DRY-RUN: no call, nothing written.  One rendered user turn per variant:")
        _render_variants(rub, selected, _inputs(args))
        return 0
    refused = _dirty(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    run, usage, ok = _operators_session(args, args.run_id, selected, step="operators",
                                        extra={"selection": "all" if args.all else "traits" if args.traits else
                                               f"sample {args.sample} seed {args.seed}"})
    _print_run_summary(run, args.samples)
    return 0 if ok else 1


def _print_run_summary(run, samples: int) -> None:
    from assistant_axis.gapgen.generators.structural import evaluate as E
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural.combine import combine_all, support_counts, union_phrase
    reps = run.sample_replies()
    nr = E.null_rates(reps)
    err = run.error_stems()
    print(f"answered {run.n_answered} of {run.n_units} (trait, sample) calls ({run.n_reused} reused) over "
          f"{len(run.samples)} traits; unanswered {len(run.errors)}"
          + (f": {dict(list(err.items())[:5])}" if err else "") + f"; {run.n_calls} calls"
          + (f"; responses stopped other than end_turn: {dict(run.failures)}" if run.failures else ""))
    print(f"non-null shares over every sample: opposite {nr['opposite']}, excess {nr['excess']}, deficiency "
          f"{nr['deficiency']}, retarget {nr['retarget']}, remode {nr['remode']}, principal {nr['principal']['share']}")
    sc = support_counts(combine_all(run.samples).values())
    print(f"items by support ({union_phrase(samples)}): {sc['by_support']}; positions {nr['positions']}; rejected "
          f"items {O.rejection_counts(reps)}")


def _freeze_holdout_if_needed(args) -> dict:
    from assistant_axis.gapgen.generators.structural import evaluate as E
    ev_path = _sdir(args) / "evaluation.json"
    ev = E.read_evaluation(ev_path)
    if ev.get("holdout_lists"):
        return ev
    stems = {p.stem for p in (Path(args.data_dir) / "traits" / "instructions").glob("*.json")}
    lists = E.freeze_holdout(queue_path=Path(args.queue), registry_rows=_registry_rows(args), corpus_stems=stems)
    ev = {**ev, "holdout_lists": lists}
    E.write_evaluation(ev, ev_path)
    print(f"froze the queue hold-out's four lists into {ev_path}: {lists['counts']}")
    return ev


def cmd_null_rate(args) -> int:
    from assistant_axis.gapgen.cost import confirm_or_abort
    from assistant_axis.gapgen.generators.structural import evaluate as E
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural import prompts as P
    from assistant_axis.gapgen.generators.structural.combine import combine_all, support_counts, union_phrase
    try:
        rub = P.load_rubric(P.OPERATORS_RUBRIC, args.rubrics_dir, allow_unpinned=args.dry_run)
    except P.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    inputs = _inputs(args)
    pairs = _pairs(args)
    selected = O.stratified_sample(inputs, args.n, args.seed, pairs=pairs, n_pairs=2, min_principal=2)
    print(f"null-rate pilot: {len(selected)} traits stratified by region and arrangement kind (seed {args.seed}; two "
          f"whole pairs, at least two principal-target traits): {', '.join(t.stem for t in selected)}")
    total = _operators_plan(args, selected, inputs, rub)
    confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.dry_run:
        stems = {p.stem for p in (Path(args.data_dir) / "traits" / "instructions").glob("*.json")}
        lists = E.freeze_holdout(queue_path=Path(args.queue), registry_rows=_registry_rows(args), corpus_stems=stems)
        print(f"DRY-RUN: no call, nothing written.  The real run first freezes the hold-out's four lists into "
              f"evaluation.json (if not frozen yet); now they would be {lists['counts']}.  One rendered user turn "
              f"per variant:")
        _render_variants(rub, selected, inputs)
        return 0
    refused = _dirty(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    _freeze_holdout_if_needed(args)
    run, _usage, ok = _operators_session(args, args.run_id, selected, step="null-rate",
                                         extra={"n": args.n, "seed": args.seed})
    combined = combine_all(run.samples)
    records = O.read_responses(_run_dir(args, args.run_id) / S.RESPONSES_NAME)
    readout = {"run_id": args.run_id, "n": len(selected), "seed": args.seed, "samples": args.samples,
               "null_rates": E.null_rates(run.sample_replies()),
               "pair_positions": E.pair_positions(combined, pairs),
               "support": support_counts(combined.values()),
               "sample_agreement": E.sample_agreement(run.samples),
               "rejections": O.rejection_counts(run.sample_replies()),
               "parse_rate": E.parse_rate(records),
               "coverage": E.answered_coverage(run.n_answered, run.n_units),
               "stops": {k: v for k, v in O.stop_summary(records).items() if k != "line"},
               "unanswered": {f"{st}:{k}": why for (st, k), why in sorted(run.errors.items())}}
    out = _run_dir(args, args.run_id) / "nullrate_readout.json"
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text(json.dumps(readout, indent=2, ensure_ascii=False) + "\n", out)
    nr = readout["null_rates"]
    print(f"non-null shares over every sample ({args.samples} a trait):")
    print(json.dumps({k: nr[k] for k in ("opposite", "excess", "deficiency", "retarget", "remode", "retarget_by_target",
                                         "remode_by_mode", "principal", "positions", "band")}, indent=1))
    print(f"items by support ({union_phrase(args.samples)}): {readout['support']['by_support']}; pair poles (the "
          f"samples' majority): {readout['pair_positions']['combinations']}; rejections {readout['rejections']}; "
          f"parse rate {readout['parse_rate']['rate']}")
    print(f"wrote {out}")
    cov = readout["coverage"]
    print(f"answered {cov['n_answered']} of {cov['n_sampled']} (trait, sample) calls")
    if not cov["pass"]:
        print(f"GATE: only {cov['n_answered']} of {cov['n_sampled']} (trait, sample) calls answered (under "
              f"{cov['min_share']:.0%}): the null rates are not read; stop reasons {readout['stops']['stop_reasons']}",
              file=sys.stderr)
        return EXIT_GATE
    if not nr["band"]["pass"]:
        print(f"GATE: retarget {nr['retarget']} / remode {nr['remode']} outside {E.NULL_BAND}: one bounded prompt "
              f"revision (a new pin) and a re-pilot (coding plan section 10)", file=sys.stderr)
        return EXIT_GATE
    print("GATE: retarget and remode inside the 5-40% band")
    return 0 if ok else 1


def _write_stability(args, st: dict, *, where: Path) -> None:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.structural import evaluate as E
    ev_path = _sdir(args) / "evaluation.json"
    ev = E.read_evaluation(ev_path)
    ev["stability"] = st
    E.write_evaluation(ev, ev_path)
    atomic_write_text(json.dumps(st, indent=2) + "\n", where)


def cmd_stability(args) -> int:
    """A reported diagnostic, never a gate (Roger, 2026-10-13).  Without ``--against``: the agreement between the
    recorded samples of ``--run-id`` (free).  With it: ``--n`` traits answered once under each of the two runs (paid,
    as before)."""
    from assistant_axis.gapgen.cost import confirm_or_abort
    from assistant_axis.gapgen.generators.structural import evaluate as E
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural import prompts as P
    from assistant_axis.gapgen.generators.structural.postprocess import collect_replies
    for r in (args.run_id, args.against):
        if r and S.read_void(_run_dir(args, r)) is not None:
            print(f"SKIPPED: run {r} is marked void ({S.read_void(_run_dir(args, r)).get('reason')})", file=sys.stderr)
            return 2
    if not args.against:
        col = collect_replies([_run_dir(args, args.run_id)])
        st = E.sample_agreement(col.full_samples)
        st.update({"runs": [args.run_id], "mode": "between the samples of one run"})
        print(json.dumps({k: st[k] for k in ("n_traits_with_two", "n_sample_pairs", "n_traits", "n_both_empty",
                                             "jaccard_median", "below_0.5", "by_operator")}, indent=1))
        print("REPORTED (not a gate): the agreement between each trait's samples, over the slots either answered")
        if not args.dry_run and st["n_sample_pairs"]:
            _write_stability(args, st, where=_run_dir(args, args.run_id) / "stability.json")
        return 0
    try:
        rub = P.load_rubric(P.OPERATORS_RUBRIC, args.rubrics_dir, allow_unpinned=args.dry_run)
    except P.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    inputs = _inputs(args)
    selected = O.stratified_sample(inputs, args.n, args.seed, pairs=(), n_pairs=0, min_principal=0)
    print(f"stability: {len(selected)} traits (seed {args.seed}), answered once under {args.run_id} and under "
          f"{args.against}")
    users = {t.stem: O.render_operator_user(t) for t in selected}
    todo = 0
    for r in (args.run_id, args.against):
        done = O.reusable(O.read_responses(_run_dir(args, r) / S.RESPONSES_NAME), model=args.model,
                          prompts={s: O.prompt_sha256(rub["text"], u) for s, u in users.items()})
        n_done = sum(1 for (st_, k) in done if k == 1 and st_ in users)
        print(f"  {r}: {n_done} answered already, {len(selected) - n_done} to send")
        todo += len(selected) - n_done
    est = O.estimate(selected, rub["text"], args.model)
    est = {**est, "n_calls": todo, "usd": round(est["usd"] * todo / max(1, len(selected)), 4),
           "in_tok": est["in_tok"] * todo // max(1, len(selected)),
           "out_tok": est["out_tok"] * todo // max(1, len(selected))}
    total = _print_estimate("stability", est, args.budget_usd, args.model)
    confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.dry_run:
        print("DRY-RUN: no call, nothing written.")
        return 0
    refused = _dirty(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    runs, left = {}, args.budget_usd
    for r in (args.run_id, args.against):
        run, used, ok = _operators_session(args, r, selected, step="stability", budget_usd=left, samples=1,
                                           extra={"n": args.n, "seed": args.seed, "against": args.against})
        if not ok:
            return 1
        left -= used.total_cost_usd
        runs[r] = {stem: by_k[1] for stem, by_k in run.samples.items() if 1 in by_k}
    st = E.stability_jaccard(runs[args.run_id], runs[args.against], n_sampled=len(selected))
    st.update({"runs": [args.run_id, args.against], "seed": args.seed, "mode": "two runs, one sample each"})
    _write_stability(args, st, where=_run_dir(args, args.against) / "stability.json")
    print(json.dumps({k: st[k] for k in ("n_traits", "n_sampled", "n_both_empty", "jaccard_median", "below_0.5",
                                         "distribution", "by_operator")}, indent=1))
    cov = st["coverage"]
    print(f"answered in both runs: {cov['n_answered']} of {cov['n_sampled']} sampled traits"
          + ("" if cov["pass"] else f" (under {cov['min_share']:.0%}: read the median with care)"))
    print(f"REPORTED (not a gate; Roger, 2026-10-13): median Jaccard {st['jaccard_median']} over the slots either "
          f"answer filled")
    return 0


# --------------------------------------------------------------------------- free: postprocess, side-table

def _lexicon(args):
    if args.no_fold:
        return None
    from assistant_axis.gapgen.generators.structural.postprocess import oewn_lexicon
    return oewn_lexicon()


def _replies(args, *, lexicon=None, corpus=None):
    """The named runs' answers combined per trait (:class:`postprocess.Collected`) and the run directories; a run
    marked void is skipped with a note."""
    from assistant_axis.gapgen.generators.structural.postprocess import collect_replies
    dirs = [_run_dir(args, r) for r in args.run_id or []]
    col = collect_replies(dirs, lexicon=lexicon, renamed=corpus.renamed if corpus else None)
    for v in col.void:
        print(f"skipped run {v}: marked void ({S.VOID_NAME})", file=sys.stderr)
    return col, [d for d in dirs if d.name not in col.void]


def cmd_postprocess(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort, estimate_calls_usd
    from assistant_axis.gapgen.generators.structural import evaluate as E
    from assistant_axis.gapgen.generators.structural import modernise as M
    from assistant_axis.gapgen.generators.structural import operators as O
    from assistant_axis.gapgen.generators.structural import postprocess as PP
    from assistant_axis.gapgen.generators.structural.combine import support_counts, union_phrase
    from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage
    modern = M.load_modern(Path(args.classical_modern))
    corpus = PP.load_corpus(Path(args.data_dir))
    queue = PP.load_queue_index(Path(args.queue))
    reg_rows = _registry_rows(args)
    reg = PP.registry_index(reg_rows)
    lex = _lexicon(args)
    col, dirs = _replies(args, lexicon=lex, corpus=corpus)
    full, ponly = col.full, col.principal_only
    union = union_phrase(col.n_samples or 1)
    table = PP.build_table(list(full.values()) + list(ponly.values()), modern, corpus=corpus, queue=queue,
                           registry=reg, lexicon=lex)
    st = {}
    for r in table:
        st[r["status"]] = st.get(r["status"], 0) + 1
    print(f"postprocess: {len(full)} traits answered in full and {len(ponly)} principal-only in {len(dirs)} run(s), "
          f"each the {union}; {len(modern)} modernised classical rows; {len(table)} distinct stems "
          f"{dict(sorted(st.items()))}; {sum(1 for r in table if r['net_new'])} net-new; "
          f"{sum(1 for r in table if r['principal_target'])} principal-target rows; registry {len(reg_rows)} keys")
    pairs = _pairs(args)
    triangles, sequences = _structures(args)
    embed, usage, emb_note = None, None, args.embedder
    texts = []
    for x, y in pairs:
        for a, b in ((x, y), (y, x)):
            for o in (full[a].slot("opposite") if a in full else []):
                texts += [f"{o['label']}: {o.get('gloss') or ''}",
                          f"{corpus.labels.get(b, b)}: {corpus.descriptions.get(b, '')}"]
    if args.embedder != "none" and texts:
        tok = int(sum(len(t) for t in texts) / 4) + 1
        est = estimate_calls_usd("text-embedding-3-large", 1, tok, 0) if args.embedder == "openai" else 0.0
        print(f"  gloss embeddings ({args.embedder}): {len(texts)} texts, ~{tok:,} tokens = ${est:.4f} at most "
              f"(the cache sends only misses); cap --budget-usd ${args.budget_usd:.2f}")
        confirm_or_abort(est, args.budget_usd, confirm_expensive=False)
    if args.dry_run:
        print("DRY-RUN: nothing written (operator table, evaluation.json, usage.json)")
        return 0
    if args.embedder != "none" and texts:
        if args.embedder == "openai":
            refused = _dirty(args)
            if refused:
                raise SystemExit(f"REFUSED: {refused}")
        from assistant_axis.gapgen.embed import EmbeddingCache, embed_texts, make_embedder
        emb = make_embedder(args.embedder)
        cache = EmbeddingCache(root=Path(args.embedding_cache)) if args.embedder != "hash" else None
        # the cumulative usage.json is loaded first and written by the guard itself (at a budget stop, on SIGTERM,
        # every 30 s) and in the finally below, so a stopped run keeps its spend (review S3, 2026-10-13)
        up = _sdir(args) / "usage.json"
        prev = MultiModelUsage.load_or_create(up)
        usage = GuardedUsage(budget_usd=prev.total_cost_usd + args.budget_usd, usage_path=up)
        usage.merge_from(prev)

        def embed(ts):
            return embed_texts(emb, ts, cache=cache, usage=usage)
        emb_note = f"{args.embedder} ({getattr(emb, 'model_id', '?')})"
    bak = PP.write_operator_table(table, Path(args.operator_table))
    print(f"wrote {args.operator_table}" + (f" (snapshot {bak.name})" if bak else " (unchanged)" if not bak and
                                            Path(args.operator_table).exists() else ""))
    ev_path = _sdir(args) / "evaluation.json"
    ev = E.read_evaluation(ev_path)
    if not ev.get("holdout_lists"):
        stems = {p.stem for p in (Path(args.data_dir) / "traits" / "instructions").glob("*.json")}
        ev["holdout_lists"] = E.freeze_holdout(queue_path=Path(args.queue), registry_rows=reg_rows,
                                               corpus_stems=stems)
    hl = ev["holdout_lists"]
    reps = list(full.values()) + list(ponly.values())
    records = [r for d in dirs for r in O.read_responses(d / S.RESPONSES_NAME) if r.get("stage") == O.STAGE]
    try:
        pair_rec = E.pair_recovery(full, pairs, corpus=corpus, lexicon=lex, embed=embed)
    except BudgetExceededError as exc:
        print(f"STOPPED at the cap (--budget-usd {args.budget_usd:g}) while embedding the glosses: {exc}; "
              f"evaluation.json not written; the spend is in {_sdir(args) / 'usage.json'}", file=sys.stderr)
        return 1
    finally:
        if usage is not None:
            usage.write_json(_sdir(args) / "usage.json")
            print(f"[usage, gloss embeddings] this run ${usage.total_cost_usd - prev.total_cost_usd:.4f}; "
                  + usage.log_line("cumulative"), file=sys.stderr)
    ev.update({
        "runs": args.run_id or [], "n_traits": len(full), "n_principal_only": len(ponly), "n_rows": len(table),
        "pair_recovery": pair_rec,
        "structure_recovery": E.structure_recovery(full, triangles, sequences, corpus=corpus, lexicon=lex),
        "queue_holdout": E.queue_holdout(reps, hl["holdout"], rejected=hl["rejected"], accepted=hl["accepted"],
                                         candidates=hl["candidates"], lexicon=lex),
        "null_rates": E.null_rates(col.sample_replies()), "parse_rate": E.parse_rate(records),
        "n_samples": col.n_samples, "union": union, "void_runs_skipped": col.void,
        "support": support_counts(reps), "sample_agreement": E.sample_agreement(col.full_samples, lexicon=lex),
        "principal": {"n_traits": sum(1 for r in reps if r.principal),
                      "n_items": sum(1 for r in reps for op, sub, _it in r.items()
                                     if op == "retarget" and sub in O.PRINCIPAL_TARGETS),
                      "n_table_rows": sum(1 for r in table if r["principal_target"])},
        "embedder": emb_note, "folded": lex is not None})
    bak = E.write_evaluation(ev, ev_path, inputs=None, title="structural evaluation (postprocess)")
    pr = ev["pair_recovery"]
    print(f"pair recovery {pr['recall_stem']} by stem over {pr['n_answered']} directions"
          + "".join(f", {k} {pr[k]}" for k in pr if k.startswith("recall_cos")))
    qh = ev["queue_holdout"]
    print(f"queue hold-out {qh['recall_stem']} of {qh['n']}; rejected regenerated {qh['rejected']['regenerated']} of "
          f"{qh['rejected']['n']}; accepted {qh['accepted']['recall_stem']}, candidates {qh['candidates']['recall_stem']}")
    sa = ev["sample_agreement"]
    print(f"items by support ({union}): {ev['support']['by_support']}; agreement between samples (reported, not a "
          f"gate): median Jaccard {sa['jaccard_median']} over {sa['n_traits']} sample pairs")
    print(f"wrote {ev_path}" + (f" (snapshot {bak.name})" if bak else ""))
    return 0


def cmd_side_table(args) -> int:
    from assistant_axis.gapgen.generators.structural import postprocess as PP
    from assistant_axis.gapgen.generators.structural import sidetable as ST
    from assistant_axis.gapgen.generators.structural.combine import union_phrase
    corpus = PP.load_corpus(Path(args.data_dir))
    lex = _lexicon(args)
    col, dirs = _replies(args, lexicon=lex, corpus=corpus)
    rows = ST.position_rows(col.full.values(), corpus=corpus, lexicon=lex)
    print(f"each trait's opposites are the {union_phrase(col.n_samples or 1)}; its position the samples' majority")
    counts = {c: sum(1 for r in rows if r["negative_label_check"] == c) for c in ST.CHECKS}
    pos = {}
    for r in rows:
        pos[str(r["position"])] = pos.get(str(r["position"]), 0) + 1
    print(f"side table: {len(rows)} traits from {len(dirs)} run(s); positions {dict(sorted(pos.items()))}; "
          f"negative-label checks {counts}")
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    b1 = ST.write_position_table(rows, Path(args.position_table))
    b2 = ST.write_mismatches(rows, Path(args.mismatches))
    print(f"wrote {args.position_table}{f' (snapshot {b1.name})' if b1 else ''} and {args.mismatches}"
          f"{f' (snapshot {b2.name})' if b2 else ''}; no trait file is touched")
    return 0


# --------------------------------------------------------------------------- submit, report

def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.structural import postprocess as PP
    from assistant_axis.gapgen.generators.structural import submit as SU
    table = PP.load_operator_table(Path(args.operator_table))
    if not table:
        raise SystemExit(f"no operator table at {args.operator_table}: run `postprocess` first")
    corpus = PP.load_corpus(Path(args.data_dir))
    reg_rows = _registry_rows(args)
    PP.apply_tags(table, corpus=corpus, queue=PP.load_queue_index(Path(args.queue)), registry=PP.registry_index(reg_rows))
    print(f"tags refreshed against the registry now ({len(reg_rows)} keys), the corpus and the queue")
    SU.run_submit(args.run_id, table=table, all_rows=args.all, kept_target=args.kept_target,
                  kept_share=args.kept_share, budget_usd=args.budget_usd, confirm_expensive=args.confirm_expensive,
                  confirmed_by=args.confirmed_by, transport=args.transport, dry_run=args.dry_run,
                  registry_path=Path(args.registry), candidates_dir=args.candidates_dir,
                  table_path=Path(args.operator_table), table_sha256=_sha_file(Path(args.operator_table)),
                  review_rate=SU.review_terms_per_hour(args.review_rate))
    return 0


def cmd_report(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.structural import evaluate as E
    from assistant_axis.gapgen.generators.structural import postprocess as PP
    from assistant_axis.gapgen.generators.structural import report as R
    from assistant_axis.gapgen.generators.structural import submit as SU
    rdir = _run_dir(args, args.run_id)
    if not (rdir / "run.json").exists():
        raise SystemExit(f"no run {rdir}: submit it first")
    if S.read_void(rdir) is not None:
        print(f"SKIPPED: run {args.run_id} is marked void ({S.read_void(rdir).get('reason')})", file=sys.stderr)
        return 2
    reg_rows = _registry_rows(args)
    table = PP.load_operator_table(Path(args.operator_table))
    ev = E.read_evaluation(_sdir(args) / "evaluation.json")
    cdir = Path(args.candidates_dir or paths.DATA_CANDIDATES)
    batch = SU.batch_id_for(args.run_id)
    fig = R.figures(args.run_id, run_dir=rdir, registry_rows=reg_rows, table=table, evaluation=ev,
                    filter_dir=cdir / "filter" / batch, novelty_dir=cdir / "novelty" / batch,
                    extra_usage=[_run_dir(args, r) / "usage.json" for r in args.operator_run or []],
                    review_rate=SU.review_terms_per_hour(args.review_rate))
    rows = R.run_rows(reg_rows, args.run_id)
    files = {"report.md": R.render_report(fig),
             "roger_sample.md": R.roger_sample(rows, table, run_id=args.run_id),
             "ai_identity_subfamily.md": R.ai_identity_list(table, reg_rows, run_id=args.run_id)}
    h = fig["headline"]
    print(f"{args.run_id}: {h['n_rows']} registry rows; already registered {h['already_registered']} "
          f"({h['already_registered_share']}), decided {h['already_decided']}; net-new {h['net_new']}; net-new kept "
          f"share {fig['net_new_kept_share']}; novel raw {fig['novel']['raw']}, net {fig['novel']['net_pending']}")
    if args.dry_run:
        print("DRY-RUN: would write " + ", ".join(str(rdir / f) for f in files))
        return 0
    for name, body in files.items():
        atomic_write_text(body, rdir / name)
    atomic_write_text(json.dumps(fig, indent=2, ensure_ascii=False, default=str) + "\n", rdir / "report.json")
    print(f"wrote {', '.join(str(rdir / f) for f in [*files, 'report.json'])}")
    return 0


def cmd_void(args) -> int:
    """Mark a run void (2026-10-13; the first: the two Sonnet 5.5 stability runs, their calls refused)."""
    rdir = _run_dir(args, args.run_id)
    if args.dry_run:
        print(f"DRY-RUN: would write {rdir / S.VOID_NAME} (reason {args.reason!r}, by {args.by!r})")
        return 0
    try:
        p = S.write_void(rdir, reason=args.reason, by=args.by)
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"wrote {p}")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    from assistant_axis.gapgen.generators.structural import operators as O
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None, help="default data/candidates (runs go under runs/)")
    ap.add_argument("--regions", type=Path, default=paths.CORPUS_REGIONS_PATH)
    ap.add_argument("--queue", type=Path, default=paths.SEED_QUEUE_PATH)
    ap.add_argument("--structural-dir", type=Path, default=S.STRUCTURAL_DIR)
    ap.add_argument("--classical-dir", type=Path, default=S.CLASSICAL_DIR)
    ap.add_argument("--classical-modern", type=Path, default=S.CLASSICAL_MODERN_PATH)
    ap.add_argument("--operator-table", type=Path, default=S.OPERATOR_TABLE_PATH)
    ap.add_argument("--position-table", type=Path, default=S.POSITION_TABLE_PATH)
    ap.add_argument("--mismatches", type=Path, default=S.MISMATCH_PATH)
    ap.add_argument("--rubrics-dir", type=Path, default=None, help="default reports/trait_gap_generation/rubrics")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def paid(p, budget: float):
        p.add_argument("--budget-usd", type=float, default=budget, help=f"hard cap (default ${budget:g})")
        p.add_argument("--confirm-expensive", action="store_true")
        p.add_argument("--confirmed-by", default=None, help="Roger's explicit go, for anything over $20")
        p.add_argument("--allow-dirty", action="store_true", help="run with uncommitted platform code (recorded)")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--model", default=O.MODEL)

    def ops(p):
        p.add_argument("--principal-min-score", type=int, default=O.PRINCIPAL_MIN_SCORE,
                       help="alignment score from which a trait gets the principal targets (default 3: stage 1)")
        p.add_argument("--concurrency", type=int, default=O.CONCURRENCY)

    p = sub.add_parser("classical", help="load and check the hand-typed tables ($0)")
    p.add_argument("--scheme", nargs="+", choices=("aristotle", "theophrastus", "sins_virtues", "via", "murray"))
    p.add_argument("--dry-run", action="store_true", help="(writes nothing in any case)")
    p.set_defaults(func=cmd_classical)

    p = sub.add_parser("modernise", help="1-3 modern labels per classical row (Haiku 5.5, ~$0.02)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--scheme", nargs="+", choices=("aristotle", "theophrastus", "sins_virtues", "via", "murray"))
    p.add_argument("--per-call", type=int, default=20)
    p.add_argument("--resume", action="store_true", help="(always on: answers to the same prompt are reused)")
    paid(p, 0.5)
    p.set_defaults(func=cmd_modernise)

    p = sub.add_parser("operators", help="the operators call, --samples per trait combined by union (Haiku 5.5, "
                                         "~$2.2 for all at 3 samples)")
    p.add_argument("--run-id", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--all", action="store_true")
    g.add_argument("--traits", nargs="+", metavar="STEM")
    g.add_argument("--sample", type=int, default=None, metavar="N")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--sample-pairs", type=int, default=0, help="whole recorded pairs forced into --sample")
    p.add_argument("--sample-principal", type=int, default=0, help="principal-target traits forced into --sample")
    p.add_argument("--principal-only", action="store_true",
                   help="a later stage: only the three principal slots, only for traits not yet answered with them")
    p.add_argument("--prior-run", nargs="+", metavar="RUN_ID", help="runs whose principal answers count as done")
    p.add_argument("--resume", action="store_true", help="(always on: answers to the same prompt are reused)")
    p.add_argument("--render", nargs="+", metavar="STEM", help="print these traits' user turns; no call")
    p.add_argument("--samples", type=int, default=O.DEFAULT_SAMPLES,
                   help=f"independent calls per trait, combined by union (default {O.DEFAULT_SAMPLES}; Roger, "
                        f"2026-10-13)")
    paid(p, 6.0)
    ops(p)
    p.set_defaults(func=cmd_operators)

    p = sub.add_parser("null-rate", help="the null-rate pilot (20 traits x 3 samples, ~$0.05) and its readout")
    p.add_argument("--run-id", required=True)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--samples", type=int, default=O.DEFAULT_SAMPLES, help="independent calls per trait")
    paid(p, 0.5)
    ops(p)
    p.set_defaults(func=cmd_null_rate, principal_only=False)

    p = sub.add_parser("stability", help="reported, never a gate: the agreement between a run's own samples ($0), "
                                         "or with --against, 30 traits under two run ids (~$0.05)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--against", default=None, help="a second run id: answer --n traits once under each (paid)")
    p.add_argument("--n", type=int, default=30)
    p.add_argument("--seed", type=int, default=1)
    paid(p, 0.5)
    ops(p)
    p.set_defaults(func=cmd_stability, principal_only=False, samples=1)

    p = sub.add_parser("void", help="mark a run void (void.json): the readouts and the recorded-output checks skip it")
    p.add_argument("--run-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--by", required=True, help="who marks it, and on whose word")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_void)

    p = sub.add_parser("postprocess", help="the operator table and evaluation.json (free; pennies of embeddings)")
    p.add_argument("--run-id", nargs="+", default=None, help="operator runs to read, the last winning per trait")
    p.add_argument("--embedder", choices=("openai", "hash", "none"), default="openai")
    p.add_argument("--embedding-cache", type=Path, default=paths.DATA_CANDIDATES / "cache" / "embeddings")
    p.add_argument("--budget-usd", type=float, default=0.1)
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--no-fold", action="store_true", help="no OEWN folding of stems (no data/external/wn)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_postprocess)

    p = sub.add_parser("side-table", help="position_table.jsonl and negative_label_mismatches.md ($0)")
    p.add_argument("--run-id", nargs="+", default=None)
    p.add_argument("--no-fold", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_side_table)

    p = sub.add_parser("submit", help="write the run's candidates and submit them (no API call; gated on the "
                                      "downstream estimate)")
    p.add_argument("--run-id", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true")
    g.add_argument("--kept-target", type=int, default=None)
    p.add_argument("--kept-share", type=float, default=0.5, help="the pilot's measured net-new kept share")
    p.add_argument("--transport", choices=("live", "batches"), default="live")
    p.add_argument("--budget-usd", type=float, default=5.0, help="cap on the downstream estimate (M1 + M3)")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None)
    p.add_argument("--review-rate", choices=("plan", "measured"), default="plan",
                   help="terms an hour: the plan's ~150, or plan 13's measured rate once it lands (the hook)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="report.md, roger_sample.md, ai_identity_subfamily.md ($0)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--operator-run", nargs="+", metavar="RUN_ID", help="the operator runs whose usage to add")
    p.add_argument("--review-rate", choices=("plan", "measured"), default="plan")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv=None) -> int:
    from assistant_axis.gapgen.runs import configure_logging
    configure_logging()
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
