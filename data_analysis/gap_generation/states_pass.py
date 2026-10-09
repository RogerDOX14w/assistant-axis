#!/usr/bin/env python3
"""Run the states pass (``assistant_axis.gapgen.states_pass``).

    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode queue \\
        (--holding-states [--rejudge] | --filter-results F [F ...]) [--limit N]
    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode corpus \\
        (--stems S [S ...] | --filter-results F [F ...]) [--limit N]
    common: [--model claude-haiku-5-5] [--batch-size 20] [--budget-usd 1.0] [--transport auto|live|batches]
            [--resume] [--confirm-expensive --confirmed-by WHO] [--allow-dirty] [--dry-run] [--overwrite]

``--model`` defaults to Haiku 5.5 since 2026-10-08 (Haiku 4.5,
``claude-haiku-4-5-20251001``, before; still selectable); every block names its model.

``--mode queue`` (prompt v4 from 2026-10-09) asks, for each word the classifier tagged ``state``, how long the state
typically lasts and whether it lasts months or longer (Roger's narrative test); a lasting condition whether it is a
role (the kind call's definition) and a gloss of the condition; a state that does not last Roger's three questions
(decision 12): is a habitual predisposition plausible, is the state's name still a good name for it (else a
suggested name), and a draft gloss of the predisposition.  Then the route (``role``, ``lasting``,
``predisposition``, ``renamed``, ``held``), the gloss check of the two released routes (a keyword scan, then a Haiku
call for any gloss the scan does not pass) and M1's alignment call on a confirmed gloss.  ``--holding-states`` takes
the registry rows on the ``states`` holding list that have no ``states_pass`` block yet (every one with
``--rejudge``) and writes, per row, the block and the row's new ``holding``: ``states_released`` for a released row
(next: ``novelty_score.py score --holding states``), ``roles`` (and entity type ``role``) for a role, ``states``
unchanged for ``renamed`` and ``held``; each ``renamed`` row's suggested name is submitted as a new candidate
(generator ``states_pass``, run id the batch id), recorded first in the tracked
``data/candidates/runs/states_pass/<batch_id>/candidates.jsonl``, its key on the state's block as ``renamed_to``.
``--filter-results`` takes the rows of filter ``results.jsonl`` files tagged ``state`` and never touches the
registry (no candidate is submitted).

``--mode corpus`` checks existing corpus labels that the filter tagged ``state``: given the label and its corpus
description, does the description describe a habitual predisposition or a momentary state?  ``--stems`` names them
directly; ``--filter-results`` takes the ``existing``-stratum rows tagged ``state``.  It reads only the corpus trait
files (``<data-dir>/traits/instructions/<stem>.json``) and writes only its own run directory; its ``summary.json``
lists the exceptions (descriptions read as momentary) for Roger.  Nothing acts on those.

Transports: ``--transport live`` sends each call through the Messages API; ``batches`` sends each wave (the queue
calls, then the check and alignment calls, and a retry of either) as Message Batches at half price
(``assistant_axis.gapgen.batches.BatchTransport``; ``batches.json`` records them as they are submitted); ``auto``
(the default) goes live under 300 rows.  ``--resume`` continues a stopped or killed run in the same batch
directory: the rows of its first session (``run.json`` ``item_keys``), every answer on record in
``responses.jsonl`` replayed, the batches recorded in ``batches.json`` collected, the earlier spend kept in
``usage.json`` and counted against the cap.

Outputs in ``data/candidates/states_pass/<batch_id>/``: ``responses.jsonl``, ``results.jsonl``, ``summary.json``
(``json_metadata`` envelope), ``usage.json`` (always), ``run.json`` (args, estimate, cap, git sha, ``dirty_check``,
the rubric versions and prompt hashes of the queue, check and alignment prompts, the sessions), ``run.log`` and,
with batches, ``batches.json``.  The cost gate, the dirty-tree refusal and the budget stop are the filter's
(``traithood_filter.py``): ``--budget-usd`` is the cap and an estimate over it is refused.
"""
from __future__ import annotations

import argparse
import json
import logging
import math
import shutil
import sys
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text, write_jsonl  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import prompt_labels as PL  # noqa: E402
from assistant_axis.gapgen import states_pass as sp  # noqa: E402
from assistant_axis.gapgen.batches import POLL_SECONDS, BatchTransport, choose_transport  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import Registry, holding_list, submit_candidates, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import (PLATFORM_PATHS, configure_logging, git_sha, log_formatter,  # noqa: E402
                                        platform_dirty_files, start_run)
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage  # noqa: E402

logger = logging.getLogger("states_pass")

CHARS_PER_TOKEN = 3.6
IN_TOK_PER_ITEM = 60       # label plus a one-sentence description
OUT_TOK_PER_ITEM = sp.OUT_TOK_PER_ROW
RETRY_MARGIN = 1.10


def _read_jsonl(paths_: list[Path]) -> list[dict]:
    rows = []
    for p in paths_:
        rows += [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows


def _earlier_run(out_dir: Path) -> Optional[dict]:
    p = out_dir / "run.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def select_items(args, earlier: Optional[dict] = None) -> tuple[list[sp.StatesItem], Optional[Registry], dict]:
    """Items to judge, the registry to write (queue mode from the registry only) and a map of skipped names
    (corpus mode).  ``earlier`` (``--resume``): the first session's ``run.json``, whose ``item_keys`` are the rows
    again, whatever list they are on now."""
    skipped: dict[str, str] = {}
    reg = None
    if args.mode == "queue":
        if args.stems:
            raise SystemExit("--stems applies to --mode corpus only")
        if args.holding_states:
            reg = Registry(args.registry)
            if earlier is not None and earlier.get("item_keys") is not None:
                rows = reg.fold()
                missing = [k for k in earlier["item_keys"] if k not in rows]
                if missing:
                    raise SystemExit(f"--resume: the registry no longer has {', '.join(missing[:5])}")
                recs = [rows[k] for k in earlier["item_keys"]]
                items = [sp.StatesItem(key=r["key"], label=r["label"], text=sp.state_text(r),
                                       meta={"from_states_pass": sp.from_states_pass(r)}) for r in recs]
            else:
                recs = holding_list(sp.HOLDING, registry=reg)
                if not args.rejudge:
                    recs = [r for r in recs if not r.get("states_pass")]
                items = sp.items_from_registry(recs)
        else:
            items = sp.items_from_filter_results(_read_jsonl(args.filter_results))
    else:
        if args.holding_states:
            raise SystemExit("--holding-states applies to --mode queue only")
        if args.stems:
            names = list(args.stems)
        else:
            names = [it.label for it in sp.items_from_filter_results(_read_jsonl(args.filter_results),
                                                                     stratum="existing")]
        names = list(dict.fromkeys(names))
        items, skipped = sp.corpus_items(names, args.data_dir)
    seen, uniq = set(), []
    for it in items:
        if it.key not in seen:
            seen.add(it.key)
            uniq.append(it)
    if earlier is not None and earlier.get("item_keys") is not None and not args.holding_states:
        keep = set(earlier["item_keys"])
        uniq = [it for it in uniq if it.key in keep]
    elif args.limit:
        uniq = uniq[:args.limit]
    return uniq, reg, skipped


def build_estimate(items: list[sp.StatesItem], args, transport: str = "live") -> Estimate:
    """The run's estimate: the queue (or corpus) calls with a retry margin; in queue mode, as upper bounds, one
    check call and one alignment call a row (only the rows of the two released routes get them, the check only
    when the scan does not pass the gloss)."""
    est = Estimate()
    n = len(items)
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    if n:
        sys_tok = int(len(sp.PROMPTS[args.mode]) / CHARS_PER_TOKEN)
        per = min(args.batch_size, n)
        est.add(f"states pass ({args.mode} v{sp.RUBRIC_VERSIONS[args.mode]})", args.model + suffix,
                math.ceil(RETRY_MARGIN * n / args.batch_size), sys_tok + IN_TOK_PER_ITEM * per,
                OUT_TOK_PER_ITEM[args.mode] * per + sp.OUT_TOK_MARGIN)
        if args.mode == "queue":
            from assistant_axis.gapgen import split_runner as SR
            est.add(f"gloss check v{sp.CHECK_RUBRIC_VERSION} (at most one a row)", args.model + suffix, n,
                    int(len(sp.CHECK_PROMPT) / CHARS_PER_TOKEN) + 80, sp.CHECK_OUT_TOK)
            i, o = SR.tokens_for("alignment", sp.ALIGNMENT_MODEL)
            est.add("M1's alignment call (at most one a row)", sp.ALIGNMENT_MODEL + suffix, n, i, o)
    return est


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--mode", required=True, choices=sp.MODES)
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--holding-states", action="store_true",
                     help="queue mode: registry rows on the states holding list (writes the registry)")
    sel.add_argument("--filter-results", type=Path, nargs="+",
                     help="filter results.jsonl files: rows tagged state (corpus mode: existing stratum only)")
    sel.add_argument("--stems", nargs="+", help="corpus mode: corpus trait stems or labels")
    ap.add_argument("--rejudge", action="store_true", help="with --holding-states: rows already judged too")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (read only)")
    ap.add_argument("--out-root", type=Path, default=None,
                    help="candidates dir holding states_pass/<batch_id>/ and runs/states_pass/<batch_id>/ "
                         "(default data/candidates)")
    ap.add_argument("--model", default=sp.DEFAULT_MODEL)
    ap.add_argument("--batch-size", type=int, default=sp.DEFAULT_BATCH_SIZE)
    ap.add_argument("--limit", type=int, help="first N rows only")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--transport", choices=("auto", "live", "batches"), default="auto",
                    help="live calls, Message Batches at half price, or auto (live under 300 rows)")
    ap.add_argument("--resume", action="store_true",
                    help="continue a stopped run in its batch dir: its rows, its answers on record replayed, its "
                         "recorded batches collected")
    ap.add_argument("--budget-usd", type=float, default=1.0,
                    help="hard cap (default 1.0); an estimate over it is refused: type a larger budget to spend "
                         "more")
    ap.add_argument("--confirm-expensive", action="store_true",
                    help="part of the over-$20 confirmation, valid only with --confirmed-by; it never raises the "
                         "cap")
    ap.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true",
                    help="allow a paid run on a working tree with uncommitted platform changes (recorded)")
    ap.add_argument("--overwrite", action="store_true",
                    help="reuse an existing batch dir (its old contents are moved to <dir>.bak.<UTC> first)")
    return ap


def _render(items: list[sp.StatesItem], args, label_form: str = PL.DEFAULT_LABEL_FORM) -> str:
    """The first call of the run as the model receives it, and in queue mode the gloss check's and the alignment
    call's forms (their gloss is the queue call's answer, not known before it); labels in ``label_form``."""
    from assistant_axis.gapgen import physical_pass as PP
    if args.mode == "corpus":
        payload = [{"id": i + 1, "label": it.label, "text": it.text} for i, it in enumerate(items[:args.batch_size])]
        return f"--- system (corpus v{sp.RUBRIC_VERSIONS['corpus']}) ---\n{sp.CORPUS_PROMPT}\n--- user ---\n" \
               f"{sp.build_batch_prompt(payload, 'corpus', label_form=label_form)}\n"
    out = sp.render_queue_call(items[:args.batch_size], model=args.model, label_form=label_form)
    out += sp.render_check_call(items[0].label, "<the gloss the queue call writes>", model=args.model,
                                label_form=label_form)
    q = PP.request("alignment", label=items[0].label, text="<the confirmed gloss>", model=sp.ALIGNMENT_MODEL,
                   label_form=label_form)
    out += f"--- then M1's alignment call on a confirmed gloss (system: rubrics/alignment.md as pinned) ---\n{q['user']}\n"
    return out


def main(argv=None) -> int:
    configure_logging()  # every line carries its UTC time (runs.LOG_FORMAT)
    args = build_parser().parse_args(argv)
    paths.check_id(args.batch_id, "batch_id")
    out_dir = paths.states_pass_dir(args.batch_id, candidates_dir=args.out_root)
    earlier = None
    if args.resume:
        if args.overwrite:
            raise SystemExit("--resume and --overwrite are opposites: choose one")
        earlier = _earlier_run(out_dir)
        if earlier is None:
            print(f"--resume: {out_dir}/run.json not found", file=sys.stderr)
            return 1
        if earlier.get("mode") != args.mode or earlier.get("model") != args.model:
            print(f"--resume: the earlier session ran mode {earlier.get('mode')} on {earlier.get('model')}",
                  file=sys.stderr)
            return 2
    # the prompts' label form (prompt_labels): a resume keeps the earlier session's (the row cache is keyed by key,
    # stored label and text, not by the prompt; a run before 2026-10-09 recorded none: "stored"); a new run shows the
    # judge display form
    label_form = PL.resolve_label_form(earlier=earlier)
    items, reg, skipped = select_items(args, earlier)
    for name, why in skipped.items():
        print(f"SKIPPED {name}: {why}", file=sys.stderr)
    if not items:
        print("nothing to judge", file=sys.stderr)
        return 0
    transport, why = choose_transport(args.transport, len(items))
    est = build_estimate(items, args, transport)
    print(f"plan: {json.dumps({'mode': args.mode, 'n_rows': len(items), 'registry': bool(reg), 'transport': transport})}")
    print(f"transport: {transport} ({why})")
    print("estimate:\n" + est.format())
    refused: Optional[str] = None
    cap = None
    try:
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
                   f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty")
        print(f"REFUSED: {refused}", file=sys.stderr)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/ and {'the registry ' + str(args.registry) if reg else 'no registry'}")
        print(f"system prompt: {len(sp.PROMPTS[args.mode])} chars (states rubric v{sp.RUBRIC_VERSIONS[args.mode]}); "
              f"prompt sha256: {sp.PROMPT_SHA256[args.mode]}")
        print(f"label form: {label_form}")
        print(_render(items, args, label_form))
        return 0
    if refused:
        return 2
    if out_dir.exists() and not args.resume:
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id, pass --resume or --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
        print(f"moved the old batch to {bak}", file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    session = {"started_at": utc_now(), "argv": sys.argv[1:] if argv is None else list(argv), "git_sha": sha,
               "transport": transport, "transport_reason": why, "estimate_usd": round(est.usd, 4), "cap_usd": cap,
               "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check, "resumed": bool(args.resume)}
    if earlier is not None:
        run_meta = dict(earlier)
        run_meta["sessions"] = list(earlier.get("sessions") or []) + [session]
        run_meta[PL.LABEL_FORM_KEY] = label_form       # the earlier session's ("stored" when it recorded none)
    else:
        run_meta = {"batch_id": args.batch_id, "mode": args.mode, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                    "dirty_check": dirty_check, "argv": session["argv"], "n_rows": len(items),
                    "item_keys": [it.key for it in items], "skipped": skipped, "estimate_usd": round(est.usd, 4),
                    "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                    "confirmed_by": args.confirmed_by, "model": args.model, "transport": transport,
                    "transport_reason": why, "rubric_version": sp.RUBRIC_VERSIONS[args.mode],
                    "prompt_sha256": sp.PROMPT_SHA256[args.mode], PL.LABEL_FORM_KEY: label_form,
                    "started_at": session["started_at"], "sessions": [session]}
        if args.mode == "queue":
            from assistant_axis.gapgen import physical_pass as PP
            pins = PP.pins()
            run_meta.update(check_rubric_version=sp.CHECK_RUBRIC_VERSION, check_prompt_sha256=sp.CHECK_PROMPT_SHA256,
                            alignment_model=sp.ALIGNMENT_MODEL,
                            alignment_step_version=pins["step_versions"]["alignment"],
                            alignment_prompt_sha256=pins["prompt_sha256"]["alignment"])
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    resume_records: list[dict] = []
    if args.resume:
        usage.merge_from(MultiModelUsage.load_or_create(out_dir / "usage.json"))
        if (out_dir / "responses.jsonl").exists():
            resume_records = _read_jsonl([out_dir / "responses.jsonl"])
    client = anthropic.AsyncAnthropic(max_retries=0) if transport == "live" else None
    runner = sp.StatesPassRunner(client=client, batch_id=args.batch_id, mode=args.mode, model=args.model,
                                 usage=usage, batch_size=args.batch_size, concurrency=args.concurrency,
                                 responses_path=out_dir / "responses.jsonl", resume_records=resume_records,
                                 close_client=True, label_form=label_form)
    if transport == "batches":
        runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap,
                                          poll_seconds=POLL_SECONDS)
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
        try:
            _finalize(args, items, reg, runner, usage, run_meta, session, out_dir, status, error)
        finally:
            logging.getLogger().removeHandler(fh)
            fh.close()
    return status


def write_registry(reg: Registry, results: list, *, args) -> dict:
    """The registry writes of a queue run from the registry: the renamed route's candidates first (recorded in
    ``runs/states_pass/<batch_id>/candidates.jsonl``, then submitted), then each judged row's block and its new
    ``holding`` (and entity type ``role`` for a role).  Returns counts for the summary."""
    cands = sp.renamed_candidates(results, batch_id=args.batch_id)
    renamed_to: dict[str, dict] = {}
    sub = None
    if cands:
        ctx = start_run(sp.GENERATOR, args.batch_id, args={"from": "states_pass.py", "batch_id": args.batch_id},
                        candidates_dir=args.out_root)
        sub = submit_candidates(cands, registry_path=reg.path, run=ctx)
        ctx.finish()
        renamed_to = {c.source_ref: sp.renamed_record(c) for c in cands}
    updates: dict[str, dict] = {}
    for r in results:
        if r.block is None:
            continue
        if args.mode == "queue" and r.key in renamed_to:
            r.block["renamed_to"] = renamed_to[r.key]      # on the result too: results.jsonl is what was written
        block = dict(r.block)
        u = {"states_pass": block}
        if args.mode == "queue" and block.get("holding_after"):
            u["holding"] = block["holding_after"]
            if block["holding_after"] == sp.ROLES_HOLDING:
                u["entity_type"] = "role"
        updates[r.key] = u
    if updates:
        reg.update_many(updates, merge_blocks=False)
    return {"n_rows_written": len(updates), "submitted": [f"{c.source_ref.split('#')[0]} -> {c.surface}" for c in cands],
            "submit_report": {k: v for k, v in sub.as_dict().items() if k != "keys"} if sub else None}


def _finalize(args, items, reg, runner, usage, run_meta, session, out_dir, status, error) -> None:
    usage.write_json(out_dir / "usage.json")
    write_jsonl(runner.responses, out_dir / "responses.jsonl")
    results = [runner.results[it.key] for it in items if it.key in runner.results]
    writes = None
    if reg is not None:   # first, so that results.jsonl holds the blocks as written (renamed_to included)
        writes = write_registry(reg, results, args=args)
        print(f"registry: {writes['n_rows_written']} rows updated; {len(writes['submitted'])} renamed candidates "
              f"submitted")
    write_jsonl([r.as_dict() for r in results], out_dir / "results.jsonl")
    runner.warn_parse_rate(logger)
    summary = sp.summarize(results, mode=args.mode, stats=runner.stats, usage=usage)
    summary.update({"batch_id": args.batch_id, "stopped_by_budget": status == 2,
                    "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                    "model": args.model, "transport": session["transport"], PL.LABEL_FORM_KEY: runner.label_form,
                    "submitted_renames": (writes or {}).get("submitted", []),
                    "submit_report": (writes or {}).get("submit_report")})
    from assistant_axis.plot_metadata import json_metadata
    env = json_metadata(summary, title=f"states_pass {args.batch_id}")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "summary.json")
    now = utc_now()
    session.update(finished_at=now, status=status, stopped_by_error=summary["stopped_by_error"],
                   cost_usd_total=round(usage.total_cost_usd, 4))
    run_meta.update(finished_at=now, cost_usd=round(usage.total_cost_usd, 4),
                    stopped_by_error=summary["stopped_by_error"])
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    print(usage.log_line())
    keys = ("n", "n_judged", "parse_rate", "cost_usd") + (("plausible", "renamed", "routes") if args.mode == "queue"
                                                           else ("exceptions",))
    print(json.dumps({k: summary.get(k) for k in keys}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
