#!/usr/bin/env python3
"""Run the states pass (``assistant_axis.gapgen.states_pass``).

    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode queue \\
        (--holding-states [--rejudge] | --filter-results F [F ...]) [--limit N]
    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode corpus \\
        (--stems S [S ...] | --filter-results F [F ...]) [--limit N]
    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode queue --reroute \\
        [--send-missing] [--route-rules 2] [--dry-run]
    common: [--model claude-haiku-5-5] [--batch-size 20] [--budget-usd 1.0] [--transport auto|live|batches]
            [--resume] [--confirm-expensive --confirmed-by WHO] [--allow-dirty] [--dry-run] [--overwrite]
            [--route-rules 1|2] [--state-text-form as_recorded|now_stripped] [--readings N]

Readings (``--readings``, queue mode, from 2026-10-13; Roger: "if this is Haiku 5.5, and cheap, yes, run three times
and average or majority vote, as appropriate"): the queue call, and the gloss check when it runs, is sent N times as
independent requests, default 3 when ``--model`` is Haiku 5.5 and 1 otherwise (M1's rule,
``split_runner.default_readings``), since two single-reading runs on the same rows disagreed on 23% of routes.  The
answers are combined by vote (``assistant_axis.gapgen.states_pass.combine_queue_readings``: a majority on each answer
that decides the route, the median typical duration, the free text of the first reading that agrees with the vote; the
route derived from the voted answers), the check by a majority on whether it confirms the gloss
(``combine_check_readings``); M1's alignment call runs once.  ``run.json``, every session and every block record
``readings``; a block voted on several carries ``queue_readings`` (each reading and the vote), and ``summary.json``
``queue_readings`` says how far the readings agreed.  The estimate and the cost gate count every reading.  A resume
keeps its recorded count (1 when it recorded none) and refuses a different ``--readings``; ``--reroute`` replays each
batch with the count its ``run.json`` recorded.  The corpus mode reads once.

Route rules (``--route-rules``, default 2 from 2026-10-12; ``assistant_axis.gapgen.states_pass.ROUTE_RULES``): under 2
the gloss check confirms any reading but ``passing``, and a row the pass itself submitted whose name does not fit is
released under its own name with the suggested name on its review card; 1 reproduces the routing before (the reading
must equal the route; such a row is held).  Every block records its ``route_rules``.  A resumed run keeps the rules
its ``run.json`` recorded (1 when it recorded none) unless the flag is given.

What the queue call is shown (``--state-text-form``, default ``now_stripped`` from 2026-10-12): M1's reading with its
"now" markers taken out ("currently", "right now", "(a passing mood)" ...), so that the duration question is about
the state the word names; ``as_recorded`` shows M1's text as it is.  A payload form, recorded in ``run.json``, the
summary and every block (``state_text_form``); a resumed run keeps its recorded form (``as_recorded`` when it
recorded none), since its answers on record are keyed by the text shown.

``--reroute`` decides again, under ``--route-rules``, every row on the states list whose queue-mode v4 block was
decided under other rules, from the answers its batch recorded (``states_pass/<batch>/responses.jsonl``: the queue
row, the gloss check's reading, the alignment score): no call is sent.  It prints every row whose route changes, the
rows that stay, and the rows whose new route needs a call their batch never made (a one-hop row's gloss check and
alignment call), with what they need.  Without ``--dry-run`` it writes the changed rows' blocks (the answers' batch
kept as ``batch_id``, the re-route in ``rerouted``) and their new ``holding`` to the registry, and its own record to
``states_pass/<batch_id>/``.  ``--send-missing`` (paid, through the cost gate, live) then makes the missing calls for
the rows that need them, and writes those rows too.

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
from collections import Counter
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


def resolve_route_rules(args, earlier: Optional[dict] = None) -> int:
    """``--route-rules``; else, on ``--resume``, the rules the first session recorded (1 when it recorded none); else
    the current rules."""
    if getattr(args, "route_rules", None) is not None:
        return sp.check_route_rules(args.route_rules)
    if earlier is not None:
        return sp.check_route_rules(earlier.get("route_rules", 1))
    return sp.ROUTE_RULES_VERSION


def resolve_text_form(args, earlier: Optional[dict] = None) -> str:
    """``--state-text-form``; on ``--resume`` the first session's form (``as_recorded`` when it recorded none), which
    an explicit flag may not contradict (its answers on record are keyed by the text shown); else the default."""
    recorded = sp.recorded_text_form(earlier)
    asked = getattr(args, "state_text_form", None)
    if asked is not None:
        if recorded is not None and asked != recorded:
            raise SystemExit(f"--resume: the first session showed the states in form {recorded!r}; "
                             f"--state-text-form {asked} would not find its answers")
        return asked
    return recorded or sp.DEFAULT_TEXT_FORM


def resolve_readings(args, earlier: Optional[dict] = None) -> int:
    """``--readings``, set on ``args`` and returned: on ``--resume`` the count the first session recorded (1 when it
    recorded none, every run before 2026-10-13), which an explicit flag may not contradict (the answers on record are
    one set per reading); else the model's default (:func:`states_pass.default_readings`: 3 on Haiku 5.5, else 1).
    The corpus mode reads once."""
    asked = getattr(args, "readings", None)
    if asked is not None:
        try:
            sp.check_readings(asked)
        except ValueError as exc:
            raise SystemExit(f"--readings {asked}: {exc}")
    if args.mode == "corpus":
        if asked not in (None, 1):
            raise SystemExit("--readings applies to --mode queue only; the corpus mode reads once")
        args.readings = 1
        return 1
    if earlier is not None:
        recorded = sp.check_readings(earlier.get(sp.READINGS_KEY) or 1)
        if asked is not None and asked != recorded:
            raise SystemExit(f"--resume: the batch's earlier session read the queue call {recorded} time(s), this one "
                             f"{asked}; resume with --readings {recorded}")
        args.readings = recorded
        return recorded
    args.readings = asked if asked is not None else sp.default_readings(args.model)
    return args.readings


def select_items(args, earlier: Optional[dict] = None, text_form: str = sp.DEFAULT_TEXT_FORM
                 ) -> tuple[list[sp.StatesItem], Optional[Registry], dict]:
    """Items to judge, the registry to write (queue mode from the registry only) and a map of skipped names
    (corpus mode).  ``earlier`` (``--resume``): the first session's ``run.json``, whose ``item_keys`` are the rows
    again, whatever list they are on now.  ``text_form``: how a queue item's text is shown (:data:`sp.TEXT_FORMS`)."""
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
                items = [sp.item_from_row(rows[k], text_form=text_form) for k in earlier["item_keys"]]
            else:
                recs = holding_list(sp.HOLDING, registry=reg)
                if not args.rejudge:
                    recs = [r for r in recs if not r.get("states_pass")]
                items = sp.items_from_registry(recs, text_form=text_form)
        else:
            items = sp.items_from_filter_results(_read_jsonl(args.filter_results), text_form=text_form)
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
    when the scan does not pass the gloss).  The queue and check calls count once per reading (``args.readings``,
    1 when unset); the alignment call runs once."""
    est = Estimate()
    n = len(items)
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    k = getattr(args, "readings", None) or 1
    rd = f", {k} readings" if k > 1 else ""
    if n:
        sys_tok = int(len(sp.PROMPTS[args.mode]) / CHARS_PER_TOKEN)
        per = min(args.batch_size, n)
        est.add(f"states pass ({args.mode} v{sp.RUBRIC_VERSIONS[args.mode]}{rd})", args.model + suffix,
                k * math.ceil(RETRY_MARGIN * n / args.batch_size), sys_tok + IN_TOK_PER_ITEM * per,
                OUT_TOK_PER_ITEM[args.mode] * per + sp.OUT_TOK_MARGIN)
        if args.mode == "queue":
            from assistant_axis.gapgen import split_runner as SR
            est.add(f"gloss check v{sp.CHECK_RUBRIC_VERSION} (at most one a row{rd})", args.model + suffix, k * n,
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
    sel.add_argument("--reroute", action="store_true",
                     help="queue mode: decide again, under --route-rules, the rows on the states list decided under "
                          "other rules, from the answers their batches recorded (no call; writes the registry "
                          "unless --dry-run)")
    ap.add_argument("--send-missing", action="store_true",
                    help="with --reroute: make the gloss-check and alignment calls a re-routed row needs and its "
                         "batch never made (paid, live, through the cost gate)")
    ap.add_argument("--route-rules", type=int, choices=sp.ROUTE_RULES, default=None,
                    help=f"routing rules (default {sp.ROUTE_RULES_VERSION}; a resume keeps its recorded rules): 2 "
                         f"confirms any gloss reading but passing and releases a one-hop row under its own name; "
                         f"1 reproduces the routing before 2026-10-12")
    ap.add_argument("--state-text-form", choices=sp.TEXT_FORMS, default=None,
                    help=f"what the queue call is shown (default {sp.DEFAULT_TEXT_FORM}; a resume keeps its "
                         f"recorded form): M1's reading without its 'now' markers, or as recorded")
    ap.add_argument("--readings", type=int, default=None,
                    help="queue mode: how many independent readings of the queue call (and of the gloss check), "
                         "combined by vote (default 3 on Haiku 5.5, else 1; a resume keeps its recorded count)")
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
    if args.reroute:
        if args.resume:
            raise SystemExit("--reroute reads the record of every batch it re-routes; it is not resumed")
        if args.readings is not None:
            raise SystemExit("--reroute replays each batch with the readings its run.json recorded; --readings "
                             "applies to a judging run")
        return run_reroute(args, out_dir)
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
    if args.send_missing:
        raise SystemExit("--send-missing applies to --reroute only")
    route_rules = resolve_route_rules(args, earlier)
    text_form = resolve_text_form(args, earlier) if args.mode == "queue" else None
    readings = resolve_readings(args, earlier)
    items, reg, skipped = select_items(args, earlier, text_form or sp.DEFAULT_TEXT_FORM)
    for name, why in skipped.items():
        print(f"SKIPPED {name}: {why}", file=sys.stderr)
    if not items:
        print("nothing to judge", file=sys.stderr)
        return 0
    transport, why = choose_transport(args.transport, len(items))
    est = build_estimate(items, args, transport)
    plan = {'mode': args.mode, 'n_rows': len(items), 'registry': bool(reg), 'transport': transport}
    if args.mode == "queue":
        plan.update(route_rules=route_rules, state_text_form=text_form, readings=readings)
    print(f"plan: {json.dumps(plan)}")
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
        if args.mode == "queue":
            n_strip = sum(1 for it in items if it.meta.get("text_as_recorded"))
            print(f"route rules: {route_rules}; state text form: {text_form}"
                  + (f" ({n_strip} of {len(items)} texts lose a 'now' marker)" if text_form == "now_stripped" else ""))
            print(f"readings: {readings} of the queue call and of the gloss check per row"
                  + (f", combined by vote ({sp.QUEUE_READINGS_RULE}; check: {sp.CHECK_READINGS_RULE}); each call "
                     f"below is sent {readings} times" if readings > 1 else ""))
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
    if args.mode == "queue":
        # the routing rules and the text form (states_pass.ROUTE_RULES, TEXT_FORMS); a resume keeps the recorded ones
        # unless the flag says otherwise, and the session records what it used
        run_meta.setdefault("route_rules", route_rules)
        run_meta.setdefault(sp.TEXT_FORM_KEY, text_form)
        session.update(route_rules=route_rules, state_text_form=text_form)
    # the readings (resolve_readings: a resume keeps the recorded count, 1 for a run that recorded none)
    run_meta[sp.READINGS_KEY] = readings
    if readings > 1:
        run_meta.update(readings_rule=sp.QUEUE_READINGS_RULE, check_readings_rule=sp.CHECK_READINGS_RULE)
    session[sp.READINGS_KEY] = readings
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
                                 close_client=True, label_form=label_form, route_rules=route_rules,
                                 text_form=text_form, readings=readings)
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


def _replay_batch(batch: str, rows: dict, args, rules: int, transport, *, usage=None, client=None,
                  responses_path: Optional[Path] = None) -> tuple[Optional[sp.StatesPassRunner], list, dict]:
    """One recorded batch's rows through the runner under ``rules``, its answers on record replayed: ``(runner,
    items, missing)``; ``runner`` is None when the batch has no record.  The runner shows labels and texts as the
    batch did (its ``run.json``'s label form; the queue records' items), so that every recorded answer is found."""
    bdir = paths.states_pass_dir(batch, candidates_dir=args.out_root)
    run_json = _earlier_run(bdir)
    resp = bdir / "responses.jsonl"
    if run_json is None or not resp.exists():
        return None, [], {k: f"no record of batch {batch} ({bdir})" for k in rows}
    recs = _read_jsonl([resp])
    items, missing = sp.reroute_items(rows, recs)
    # the batch's readings (1 for a batch that recorded none): every reading's answers on record are replayed, and
    # --send-missing asks a missing check once per reading
    runner = sp.StatesPassRunner(client=client, batch_id=args.batch_id, mode="queue", model=run_json["model"],
                                 usage=usage, label_form=PL.resolve_label_form(source=run_json), route_rules=rules,
                                 text_form=sp.recorded_text_form(run_json), resume_records=recs,
                                 transport=transport, responses_path=responses_path, close_client=client is not None,
                                 concurrency=args.concurrency, readings=run_json.get(sp.READINGS_KEY) or 1)
    if items:
        try:
            runner.run(items)
        except sp.CallsNeeded:
            pass                     # the rows waiting on calls stay pending; the record settled the others
    return runner, items, missing


def run_reroute(args, out_dir: Path) -> int:
    """``--reroute``: every row on the states list decided under other route rules than ``--route-rules``, decided
    again from its batch's answers on record (no call); printed, then written unless ``--dry-run``.  With
    ``--send-missing`` the calls a re-routed row needs and its batch never made are made (paid), and those rows
    written too."""
    if args.mode != "queue":
        raise SystemExit("--reroute applies to --mode queue only")
    rules = sp.check_route_rules(args.route_rules if args.route_rules is not None else sp.ROUTE_RULES_VERSION)
    reg = Registry(args.registry)
    rows = reg.fold()
    todo = {k: r for k, r in sorted(rows.items()) if sp.needs_reroute(r, rules)}
    if args.limit:
        todo = dict(list(todo.items())[:args.limit])
    by_batch: dict[str, dict] = {}
    for k, r in todo.items():
        by_batch.setdefault(sp.block_of(r).get("batch_id") or "?", {})[k] = r
    print(f"plan: {json.dumps({'reroute': True, 'route_rules': rules, 'n_rows': len(todo), 'batches': {b: len(v) for b, v in sorted(by_batch.items())}})}")
    changed: dict[str, dict] = {}          # key -> new block
    report: list[dict] = []
    pending: dict[str, tuple[str, dict, list]] = {}   # key -> (batch, row, the calls it waits on)
    for batch, brows in sorted(by_batch.items()):
        runner, items, missing = _replay_batch(batch, brows, args, rules, sp.RecordOnlyTransport())
        for k, why in missing.items():
            report.append({"key": k, "label": brows[k]["label"], "batch": batch, "outcome": "no_record", "why": why})
        if runner is None:
            continue
        needed = runner.transport.needed
        for it in items:
            res = runner.results[it.key]
            old = sp.block_of(brows[it.key])
            if res.stage == "judged":
                new = sp.rerouted_block(res.block, old, reroute_batch_id=args.batch_id)
                ch = sp.route_change(old, new)
                chk = new.get("gloss_check") or {}
                reading = (chk.get("check") or {}).get("reading")
                rec = {"key": it.key, "label": it.label, "batch": batch, "outcome": "changed" if ch else "unchanged",
                       "from": old.get("route"), "to": new.get("route"), "holding_after": new.get("holding_after"),
                       "route_reason": new.get("route_reason"), "gloss_by": chk.get("by"), "reading": reading,
                       "alignment": new.get("alignment"), "suggested_name": sp.other_name(new, it.label)}
                report.append(rec)
                if ch:
                    changed[it.key] = new
            else:
                calls = [c for c in needed if c.key == it.key]
                # the block holds the queue answers the record replayed
                route, why = sp.route_for(old, label=it.label, from_states_pass=bool(it.meta.get("from_states_pass")),
                                          rules=rules)
                pending[it.key] = (batch, brows[it.key], calls)
                report.append({"key": it.key, "label": it.label, "batch": batch, "outcome": "needs_calls",
                               "from": old.get("route"), "to": route, "route_reason": why,
                               "needs": sorted(c.step for c in calls),
                               "suggested_name": old.get("suggested_name")})
    for r in report:
        if r["outcome"] == "changed":
            extra = (f"; gloss confirmed by the {r['gloss_by']}" + (f" (read as {r['reading']})" if r["reading"] else "")
                     + (f"; alignment {r['alignment']}" if r["alignment"] is not None else "")
                     + (f"; suggested name '{r['suggested_name']}' on its card" if r["suggested_name"] else ""))
            print(f"CHANGED   {r['label']} ({r['batch']}): {r['from']} -> {r['to']} ({r['holding_after']}){extra}")
        elif r["outcome"] == "needs_calls":
            need = " and ".join(f"{n} {s}" if n > 1 else s for s, n in sorted(Counter(r["needs"]).items()))
            print(f"NEEDS     {r['label']} ({r['batch']}): {r['from']} -> {r['to']} once {need} "
                  f"call(s) are made (not on record); {r['route_reason']}")
        elif r["outcome"] == "no_record":
            print(f"NO RECORD {r['label']} ({r['batch']}): {r['why']}")
    same = [f"{r['label']} ({r['to']})" for r in report if r["outcome"] == "unchanged"]
    if same:
        print(f"UNCHANGED {len(same)}: {', '.join(same)}")
    n = Counter(r["outcome"] for r in report)
    print(f"reroute: {n.get('changed', 0)} changed, {n.get('unchanged', 0)} unchanged, "
          f"{n.get('needs_calls', 0)} need calls, {n.get('no_record', 0)} without a record "
          f"(of {len(todo)} rows decided under other route rules)")
    calls = [c for _, _, cs in pending.values() for c in cs]
    est_usd = sp.StatesPassRunner(client=None, batch_id="estimate", mode="queue").estimate_usd(calls) if calls else 0.0
    if calls:
        print(f"--send-missing would make {len(calls)} call(s) ({dict(Counter(c.step for c in calls))}), "
              f"about ${est_usd:.4f} live")
    refused: Optional[str] = None
    cap = None
    if args.send_missing and calls:
        try:
            cap = confirm_or_abort(est_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                                   confirmed_by=args.confirmed_by)
        except CostRefused as exc:
            refused = exc.msg
    sha = git_sha()
    dirty = platform_dirty_files()
    dirty_check = {"paths": list(PLATFORM_PATHS), "dirty": dirty,
                   "note": None if dirty is not None else "git unavailable: not checked"}
    if refused is None and dirty and not args.allow_dirty:
        refused = (f"uncommitted changes to the platform's own code or prompt paths ({len(dirty)}: "
                   f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty")
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {len(changed)} rows to the registry {args.registry} and {out_dir}/"
              + (f"; with --send-missing, {len(pending)} more after {len(calls)} call(s)" if pending else ""))
        return 0
    if refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2
    if not changed and not (args.send_missing and pending):
        print("nothing to write", file=sys.stderr)
        return 0
    if out_dir.exists():
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id or pass --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
    out_dir.mkdir(parents=True, exist_ok=True)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    status = 0
    if args.send_missing and pending:
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        by: dict[str, dict] = {}
        for k, (batch, row, _) in pending.items():
            by.setdefault(batch, {})[k] = row
        for batch, brows in sorted(by.items()):
            client = anthropic.AsyncAnthropic(max_retries=0)
            try:
                runner, items, _ = _replay_batch(batch, brows, args, rules, None, usage=usage, client=client,
                                                 responses_path=out_dir / "responses.jsonl")
            except BudgetExceededError as exc:
                print(f"STOPPED: {exc}", file=sys.stderr)
                status = 2
                break
            for it in items:
                res = runner.results[it.key]
                if res.stage == "judged":
                    changed[it.key] = sp.rerouted_block(res.block, sp.block_of(brows[it.key]),
                                                        reroute_batch_id=args.batch_id)
                    for r in report:
                        if r["key"] == it.key:
                            r.update(outcome="changed_after_calls", to=res.block["route"],
                                     holding_after=res.block["holding_after"])
            runner.warn_parse_rate(logger)
    results = [sp.StatesResult(key=k, label=rows[k]["label"], stage="judged", block=b) for k, b in changed.items()]
    writes = write_registry(reg, results, args=args)
    print(f"registry: {writes['n_rows_written']} rows updated")
    write_jsonl(report, out_dir / "results.jsonl")
    usage.write_json(out_dir / "usage.json")
    run_meta = {"batch_id": args.batch_id, "mode": "queue", "reroute": True, "route_rules": rules,
                "argv": list(sys.argv[1:]), "git_sha": sha, "dirty_check": dirty_check,
                "allow_dirty": bool(args.allow_dirty), "source_batches": sorted(by_batch),
                "n_rows": len(todo), "item_keys": list(todo), "send_missing": bool(args.send_missing),
                "estimate_usd": round(est_usd, 4), "cap_usd": cap, "cost_usd": round(usage.total_cost_usd, 4),
                "finished_at": utc_now(), "status": status}
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    from assistant_axis.plot_metadata import json_metadata
    summary = {"reroute": True, "route_rules": rules, "outcomes": dict(Counter(r["outcome"] for r in report)),
               "changed": [f"{r['label']}: {r['from']} -> {r['to']}" for r in report if r["outcome"].startswith("changed")],
               "submitted_renames": writes.get("submitted", []), "cost_usd": round(usage.total_cost_usd, 4),
               "usage": usage.as_dict()}
    atomic_write_text(json.dumps(json_metadata(summary, title=f"states_pass reroute {args.batch_id}"), indent=2,
                                 ensure_ascii=False) + "\n", out_dir / "summary.json")
    print(usage.log_line())
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
    summary = sp.summarize(results, mode=args.mode, stats=runner.stats, usage=usage, readings=runner.readings)
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
    keys = ("n", "n_judged", "parse_rate", "cost_usd", "n_readings") + (
        ("plausible", "renamed", "routes") if args.mode == "queue" else ("exceptions",))
    print(json.dumps({k: summary.get(k) for k in keys}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
