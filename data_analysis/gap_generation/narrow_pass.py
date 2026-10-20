#!/usr/bin/env python3
"""The narrow pass: at most one narrow trait per parent goes to review (Roger, 2026-10-20, QUESTIONS 208 (3)).

    uv run python data_analysis/gap_generation/narrow_pass.py --batch-id ID
        (--run GENERATOR/RUN_ID | --m3-batch B [B ...] | --keys K [K ...] | --all-awaiting)
        [--model claude-haiku-5-5] [--readings 3] [--transport live|batches] [--seed 0] [--limit N]
        [--budget-usd 2] [--confirm-expensive --confirmed-by WHO] [--resume] [--render] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/narrow_pass.py --batch-id ID --release (trait:STEM ... | all)
        [--seed 0] [--dry-run]

The module is ``assistant_axis/gapgen/narrow_pass.py`` (its docstring has the rules); the prompt is the pinned rubric
``reports/trait_gap_generation/rubrics/narrow_direction.md``.  Run it after M3 (``novelty_score.py score``) and
before the review graph (``review_graph.py build``), which leaves the held rows out.  The pass reads the registry's
``review.status``, so first ``apply`` every review batch with logged decisions.  A review graph built before the pass
still holds the rows it held: the command names those batches at the end, to be rebuilt (the review app refuses to
nominate or promote a held member meanwhile).

**Releasing the cap** (``--release``, no call): a kept child that review rejected or merged into something no longer
holds its parent's slot; ``--release trait:<stem> ...`` (or ``all``: every parent whose slot is free and that has held
children) keeps the most distinct of the parent's held rows, by their recorded final readings, and takes it off the
holding list.

**Which rows** (one of): ``--run GENERATOR/RUN_ID`` (rows with a source of that run: the plan 06 pilot is
``--run llm_entropy/2026-10-17-pilot``), ``--m3-batch`` (rows M3 last decided in those batches), ``--keys`` (named
rows), ``--all-awaiting`` (every row awaiting review).  Of those, the candidates: M3 kept (``new`` or ``grey``), not
reviewed, on no holding list, not judged by the pass already, whose best overlap reading (either model) against a
corpus or queue trait is 2 or more; each is asked about its one or two traits with the highest readings.  A row
Roger parked or deferred in review is not asked (it has been in front of him once).  ``--limit N`` takes a seeded
random sample of N candidates (``--seed``).

**Money.**  One call per (row, parent, reading) on Haiku 5.5 (about $0.0003 a call live, half that batched): the
command prints the estimate, takes ``--budget-usd`` as a hard cap (over it refused; over the $20 line needs
``--confirm-expensive --confirmed-by``), charges every response to a guarded usage, writes ``usage.json`` in a
``finally`` block, ends with the parse-rate check (``judge.warn_if_low_parse_rate``), refuses uncommitted platform code
without ``--allow-dirty``, and refuses to reuse answers on record for the same model without ``--resume``.
``--transport batches`` sends the calls through the Message Batches API (half price; ``batches.json`` records the
batches, and ``--resume`` collects a batch a stopped run left).  ``--dry-run`` prints the selection, the estimate and
(``--render``) the system turn and one user turn per variant, and writes and calls nothing.

**Writes** ``data/candidates/narrow_pass/<batch-id>/``: ``responses.jsonl``, ``usage.json``, ``decisions.json``,
``readout.md``, ``run.json`` (and ``batches.json``); and on the registry, a ``narrow`` block on every row asked and
``holding: "narrow"`` on each held row.  A run stopped by the budget writes no registry change; run again with
``--resume`` (the cap is the spend on record plus ``--budget-usd``, so the same budget leaves room for the rest).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import narrow_pass as NP  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.runs import platform_dirty_files  # noqa: E402

DEFAULT_BUDGET_USD = 2.0


def _client():
    """The Anthropic client, direct key (tests replace this)."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _batch_client():
    """The synchronous client the Message Batches transport uses (tests replace this)."""
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.Anthropic()


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _scope(args):
    """The row filter of ``--run`` / ``--m3-batch`` / ``--keys`` / ``--all-awaiting``."""
    if args.run:
        gen, sep, run_id = args.run.partition("/")
        if not sep:
            raise SystemExit("REFUSED: --run takes GENERATOR/RUN_ID")
        return lambda r: any(s.get("generator") == gen and s.get("run_id") == run_id for s in r.get("sources") or [])
    if args.m3_batch:
        bs = set(args.m3_batch)
        return lambda r: (r.get("novelty") or {}).get("run_id") in bs
    if args.keys:
        ks = set(args.keys)
        return lambda r: r.get("key") in ks
    return lambda r: True


def _variant(p: NP.Parent) -> str:
    return "a queue entry as the existing trait" if p.kind == "queue" else "a corpus trait as the existing trait"


def _render(rubric: dict, items: Sequence[NP.Item]) -> None:
    print(f"=== system turn: {rubric['name']} version {rubric['version']} (sha {(rubric['sha256'] or '?')[:12]}...), "
          f"sent byte for byte ===")
    print(rubric["text"])
    seen = set()
    for it in items:
        for p in it.parents:
            v = _variant(p)
            if v in seen:
                continue
            seen.add(v)
            print(f"=== user turn, {v}: {it.label} against {p.label} (M3 read {p.reading}) ===")
            print(NP.build_user(it, p))


def _write_run(out: Path, session: dict) -> None:
    from assistant_axis.atomic_io import atomic_write_text
    p = out / NP.RUN_NAME
    run = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"pass": NP.PASS_NAME, "sessions": []}
    run["sessions"].append(session)
    run.update(batch_id=session["batch_id"], latest=session)
    atomic_write_text(json.dumps(run, indent=2, ensure_ascii=False) + "\n", p)


def _print_graphs(held_keys, rows, args) -> None:
    root = Path(args.candidates_dir or paths.DATA_CANDIDATES) / "review"
    found = NP.graphs_holding(held_keys, rows, root)
    for b, ks in found.items():
        print(f"REBUILD: review batch {b}'s graph.json holds {len(ks)} row(s) the narrow pass held (e.g. "
              f"{', '.join(ks[:3])}): apply its logged decisions, then review_graph.py build it again")


def cmd_release(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import Registry, utc_now
    reg_path = Path(args.registry)
    reg = Registry(reg_path)
    rows = reg.fold() if reg_path.exists() else {}
    parents = NP.releasable(rows) if args.release == ["all"] else list(args.release)
    bad = [p for p in parents if not p.startswith(("trait:", "queue:"))]
    if bad:
        print(f"REFUSED: --release takes trait:<stem> or queue:<stem> (or all), not {', '.join(bad)}", file=sys.stderr)
        return 2
    updates, report = NP.release(rows, parents, seed=args.seed, now=utc_now(), run_id=args.batch_id)
    for r in report:
        print(f"{r['parent']}: " + (f"RELEASED {r['released']} for review ({r['why']}; {len(r['held'])} held "
                                    f"before)" if r["released"] else f"nothing released ({r['why']})"))
    if args.dry_run:
        print(f"DRY-RUN: would write {len(updates)} narrow blocks on {reg_path}")
        return 0
    if updates:
        reg.update_many(updates)
    out = paths.narrow_pass_dir(args.batch_id, candidates_dir=args.candidates_dir)
    out.mkdir(parents=True, exist_ok=True)
    _write_run(out, {"batch_id": args.batch_id, "at": utc_now(), "step": "release", "parents": parents,
                     "report": report, "seed": args.seed, "registry": str(reg_path)})
    released = [r["released"] for r in report if r["released"]]
    print(f"registry {reg_path}: {len(released)} row(s) released for review, {len(updates)} narrow blocks written")
    if released:
        _print_graphs(released, reg.fold(), args)
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort, resume_usage
    from assistant_axis.gapgen.registry import Registry, read_snapshot, utc_now
    from assistant_axis.gapgen.runs import configure_logging, dirty_refusal
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import MultiModelUsage

    args = build_parser().parse_args(argv)
    configure_logging()
    try:
        paths.check_id(args.batch_id, "batch_id")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if args.release:
        return cmd_release(args)
    if args.readings < 1:
        print("REFUSED: --readings must be at least 1", file=sys.stderr)
        return 2
    if args.model not in NP.MODELS:
        print(f"REFUSED: --model must be one of {', '.join(NP.MODELS)}", file=sys.stderr)
        return 2
    try:
        rubric = NP.load_rubric(args.rubrics_dir, allow_unpinned=args.dry_run)
    except NP.RubricNotPinned as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    if rubric["version"] is None:
        print("DRY-RUN: the rubric's text is not its latest pin; a real run would be refused")
    out = paths.narrow_pass_dir(args.batch_id, candidates_dir=args.candidates_dir)
    reg_path = Path(args.registry)
    rows = read_snapshot(reg_path) if reg_path.exists() else {}
    lookup = NP.TextLookup(Path(args.data_dir), Path(args.queue) if args.queue else None)
    items, skipped = NP.select(rows, lookup, scope=_scope(args))
    if args.limit is not None:
        n_all = len(items)
        items = NP.sample_items(items, args.limit, seed=args.seed)
        print(f"--limit {args.limit}: a seeded sample (seed {args.seed}) of {len(items)} of the {n_all} candidates")
    by_n = Counter(len(it.parents) for it in items)
    by_kind = Counter(p.kind for it in items for p in it.parents)
    print(f"{len(items)} candidates ({by_n.get(1, 0)} with one parent asked, {by_n.get(2, 0)} with two; parents: "
          f"{dict(by_kind)}); not asked: {json.dumps(skipped)}")
    records = NP.read_records(out / NP.RESPONSES_NAME)
    answers = NP.answers_on_record(records, model=args.model)
    mine = [r for r in records if r.get("model") == args.model]
    if mine and not args.resume and not args.dry_run:
        print(f"REFUSED: {len(mine)} responses of {args.model} are on record in {out / NP.RESPONSES_NAME}; pass "
              f"--resume to reuse them (only the readings without an answer are sent)", file=sys.stderr)
        return 2
    calls = NP.plan_calls(items, rubric=rubric, model=args.model, readings=args.readings, answers=answers)
    n_pairs = NP.n_pairs(items)
    est = NP.estimate(len(calls), args.model, transport=args.transport)
    print(f"{n_pairs} (row, parent) pairs x {args.readings} reading(s); {n_pairs * args.readings - len(calls)} answers "
          f"on record; {len(calls)} calls to make ({args.transport}):")
    print(est.format())
    try:
        confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                         confirmed_by=args.confirmed_by)
    except CostRefused:
        return 2
    refused, dirty_rec = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if refused and not args.dry_run:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2
    if refused:
        print(f"DRY-RUN: the real run would be REFUSED: {refused}")
    if args.render:
        _render(rubric, items)
    if args.dry_run:
        print(f"DRY-RUN: would make {len(calls)} calls on {args.model} ({args.transport}, max_tokens {NP.MAX_TOKENS}, "
              f"no temperature), write {_rel(out)}/ and the narrow blocks and held rows on {reg_path}")
        return 0
    out.mkdir(parents=True, exist_ok=True)
    resp, usage_path = out / NP.RESPONSES_NAME, out / NP.USAGE_NAME
    prev = resume_usage(MultiModelUsage.load_or_create(usage_path), records, where=str(out))
    cap = prev.total_cost_usd + args.budget_usd
    usage = GuardedUsage(per_model=dict(prev.per_model), budget_usd=cap, usage_path=usage_path)
    usage.write_json(usage_path)
    res = None
    try:
        if calls:
            runner = NP.NarrowRunner(client=_client() if args.transport == "live" else None, usage=usage,
                                     responses_path=resp, rubric=rubric, batch_id=args.batch_id,
                                     concurrency=args.concurrency)
            if args.transport == "batches":
                from assistant_axis.gapgen.batches import BatchTransport
                runner.transport = BatchTransport(runner, _batch_client(), out / NP.BATCHES_NAME, budget_usd=cap)
            res = asyncio.run(runner.run(calls))
    finally:
        usage.write_json(usage_path)
    if res is not None:
        warn_if_low_parse_rate(label=f"narrow pass:{args.model}", n_ok=res.n_ok, n_total=res.n_calls,
                               logger_obj=logging.getLogger("narrow_pass"),
                               extra=f"failed calls by kind {res.error_kinds}")
        print(f"{res.n_ok} of {res.n_calls} calls answered; failed {res.error_kinds}; {usage.plain().log_line()}"
              + ("; STOPPED at the budget" if res.stopped_by_budget else ""))
    session = {"batch_id": args.batch_id, "at": utc_now(), "argv": list(argv) if argv is not None else sys.argv[1:],
               "model": args.model, "readings": args.readings, "transport": args.transport, "seed": args.seed,
               "rubric": {k: rubric[k] for k in ("name", "version", "sha256", "file")},
               "label_form": NP.DEFAULT_LABEL_FORM,
               "n_candidates": len(items), "n_pairs": n_pairs, "n_calls": len(calls), "skipped": skipped,
               "estimate_usd": round(est.usd, 4), "budget_usd": args.budget_usd, "confirmed_by": args.confirmed_by,
               "dirty_check": dirty_rec, "registry": str(reg_path)}
    if res is not None and res.stopped_by_budget:
        session["stopped_by_budget"] = True
        _write_run(out, session)
        print("NOT WRITTEN to the registry: the run stopped at the budget; run again with --resume (the cap is the "
              "spend on record plus --budget-usd, so the same budget leaves room for the rest)", file=sys.stderr)
        return 2
    answers = NP.answers_on_record(NP.read_records(resp), model=args.model)
    judged = NP.judge(items, answers, args.readings, system=rubric["text"])
    reg = Registry(reg_path)
    current = reg.fold()
    earlier = NP.earlier_kept(current, exclude=[it.key for it in items])
    decisions = NP.assign(judged, earlier=earlier, seed=args.seed)
    c = NP.counts(decisions)
    print(f"decisions: {json.dumps(c)}")
    updates = NP.registry_updates(decisions, run_id=args.batch_id, rubric=rubric, model=args.model,
                                  readings=args.readings, seed=args.seed, now=utc_now())
    if updates:
        reg.update_many(updates)
    labels = {k: (r.get("label") or k) for k, r in current.items()}
    files = {"rubric": _REPO_ROOT / rubric["file"], "usage": usage_path, "responses": resp,
             "decisions": out / NP.DECISIONS_NAME}
    doc = NP.decisions_doc(decisions, run_id=args.batch_id, rubric=rubric, model=args.model, readings=args.readings,
                           seed=args.seed, skipped=skipped,
                           extra={"cost_usd_on_record": round(usage.total_cost_usd, 4), "earlier_kept": earlier})
    atomic_write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", out / NP.DECISIONS_NAME)
    atomic_write_text(NP.render_readout(decisions, run_id=args.batch_id, rubric=rubric, model=args.model,
                                        readings=args.readings, usage_usd=usage.total_cost_usd,
                                        doc_path=out / NP.READOUT_NAME, data_dir=Path(args.data_dir), files=files,
                                        skipped=skipped, labels=labels), out / NP.READOUT_NAME)
    session["counts"] = c
    _write_run(out, session)
    print(f"registry {reg_path}: {len(updates)} narrow blocks, {c['held']} rows held on the {NP.HOLDING!r} list")
    print(f"wrote {_rel(out)}/: {NP.RESPONSES_NAME}, {NP.USAGE_NAME}, {NP.DECISIONS_NAME}, {NP.READOUT_NAME}, "
          f"{NP.RUN_NAME}")
    _print_graphs([d["key"] for d in decisions if d["status"] == "held"], reg.fold(), args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id", required=True, help="names data/candidates/narrow_pass/<batch-id>/ and the blocks' run")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", metavar="GENERATOR/RUN_ID", help="rows with a source of this generator run")
    g.add_argument("--m3-batch", nargs="+", metavar="B", help="rows M3 last decided in these batches")
    g.add_argument("--keys", nargs="+", metavar="KEY", help="these registry rows")
    g.add_argument("--all-awaiting", action="store_true", help="every row awaiting review")
    g.add_argument("--release", nargs="+", metavar="PARENT",
                   help="no call: release the held rows of these parents (trait:<stem>, queue:<stem>, or all) whose "
                        "kept child review rejected or merged")
    ap.add_argument("--model", default=NP.DEFAULT_MODEL, help=f"one of {', '.join(NP.MODELS)}")
    ap.add_argument("--readings", type=int, default=NP.DEFAULT_READINGS,
                    help="answers per (row, parent) pair, combined by plurality (a tie is no verdict); default 3")
    ap.add_argument("--transport", choices=("live", "batches"), default="live",
                    help="live (default), or the Message Batches API at half price")
    ap.add_argument("--seed", type=int, default=0, help="breaks ties between equally distinct children of a parent")
    ap.add_argument("--limit", type=int, default=None, help="a seeded random sample of N candidates (a pilot)")
    ap.add_argument("--concurrency", type=int, default=NP.CONCURRENCY)
    ap.add_argument("--render", action="store_true", help="print the system turn and one user turn per variant")
    ap.add_argument("--resume", action="store_true", help="reuse the answers on record (request sha, reading, model)")
    ap.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD, help="hard cap on this run's calls")
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="run although the platform's own code or prompt paths have uncommitted changes")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="where traits/instructions/ is read")
    ap.add_argument("--queue", type=Path, default=None, help="the seed queue (default <data-dir>/seed_queue.json)")
    ap.add_argument("--candidates-dir", type=Path, default=None, help="default data/candidates")
    ap.add_argument("--rubrics-dir", type=Path, default=None, help="default reports/trait_gap_generation/rubrics")
    return ap


if __name__ == "__main__":
    sys.exit(main())
