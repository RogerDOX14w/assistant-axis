#!/usr/bin/env python3
"""R2 of the trait-gap review tooling: the review app over a candidate graph, its decision log, and apply.

Usage.  Roger runs ``serve`` in his own terminal (an agent's sandbox cannot bind a port), from the repository's main
checkout, and opens the page in a browser:

    uv run python data_analysis/gap_generation/review_app.py serve --batch-id review_pilots_1
    # then open http://127.0.0.1:8765  (port 8765 by default; --port to change it; Ctrl-C stops the server,
    # and every decision is already on disk in data/candidates/review/review_pilots_1/decisions.jsonl)

    uv run python data_analysis/gap_generation/review_app.py status --batch-id review_pilots_1
    uv run python data_analysis/gap_generation/review_app.py apply --batch-id review_pilots_1 --dry-run
    uv run python data_analysis/gap_generation/review_app.py apply --batch-id review_pilots_1

``apply`` writes the live registry log (``data/candidates/registry.jsonl``, one per checkout) and the seed queue
(``data/seed_queue.json``), so run it in the checkout whose registry is meant, after ``--dry-run``.  It is
idempotent.  Nothing here makes an API call.

Keys on the page: ``j`` / ``k`` next and previous in the focused list; ``Tab`` / ``Shift-Tab`` move the focus between
members, leftovers, corpus traits, neighbours and opposed terms (the page's order); ``g`` (or ``Enter`` on a proposed
group) accept the proposed group; ``x`` drop the highlighted member; ``m`` merge in the highlighted neighbour (with its merged group); ``n``
nominate the highlighted member; ``Enter`` resolve with promote; ``c`` resolve as merge into the highlighted corpus
trait (or queue entry); ``p`` park; ``r`` reject; ``d`` defer; ``;`` a note for the next resolution; ``f`` flag the group for a better name; ``a`` start the
antonym group from the highlighted opposed term; on a resolved group's **leftovers** (the unhandled members of the
groups overlapping it, listed under the members, strongest tie first) ``+`` also covered (joins the group under its
resolution) and ``-`` distinct (not this trait; it stays for its own group); ``u`` undo the last decision (opens are
skipped: they are navigation); ``/`` find a term; ``Space`` or ``.`` the next group in the queue; ``o`` the next queue
order; ``?`` the key list.

Commands:

* ``serve --batch-id B [--port 8765] [--order cliques|generator|region|sample] [--by roger]``: the app on 127.0.0.1.
  ``sample`` is a seeded weighted random order for a review hour meant as a probability sample (decisions.py
  ``SAMPLE_WEIGHTS``); ``status`` then reports how far it went, per stratum.
* ``status --batch-id B``: groups resolved and open, decisions by type, terms handled (and how many of them an
  earlier review batch settled, by the registry's review blocks), the queue's remaining counts, time per decision
  (median minutes per resolved group, active minutes, decisions per minute).
* ``apply --batch-id B [--dry-run]``: replays the log into the registry's review blocks and promotes each promoted
  group's nominee through ``gap_registry.py promote``'s path (its seed-queue entry carrying ``also_proposed``);
  ``--dry-run`` prints the writes and writes nothing.  Logged decisions the graph no longer supports (a rebuilt
  graph) are listed first: they are left out, so a row this review wrote for one is reset.

The brief is ``reports/trait_gap_generation/coding_plan_review.md`` (section 3); the logic is
:mod:`assistant_axis.gapgen.review_app.decisions`, the routes :mod:`assistant_axis.gapgen.review_app.server`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import review_graph as RG  # noqa: E402
from assistant_axis.gapgen.registry import Registry  # noqa: E402
from assistant_axis.gapgen.review_app import decisions as D  # noqa: E402

DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


def _review_dir(args) -> Path:
    return RG.review_dir(args.batch_id, candidates_dir=args.out_root)


def _queue_path(args) -> Path:
    return args.queue if args.queue is not None else args.data_dir / "seed_queue.json"


def _open_log(args) -> D.DecisionLog:
    return D.DecisionLog.open(_review_dir(args), by=args.by, data_dir=args.data_dir, registry_path=args.registry,
                              queue_path=_queue_path(args))


def cmd_serve(args) -> int:
    import uvicorn
    from assistant_axis.gapgen.review_app.server import create_app
    app = create_app(review_dir=_review_dir(args), data_dir=args.data_dir, registry_path=args.registry,
                     queue_path=_queue_path(args), order=args.order, by=args.by)
    log = app.state.log
    c = log.state.counts()
    print(f"review {args.batch_id}: {c['terms']['total']} terms ({c['terms']['handled']} handled), "
          f"{c['merged']['total']} merged groups, {c['proposed']['total']} proposed groups, {c['single']['total']} "
          f"singletons; {len(log.events)} decisions on record in {log.path}")
    if log.state.skipped:
        print(f"WARNING: {len(log.state.skipped)} logged decisions no longer apply to this graph (skipped)")
    print(f"open http://{args.host}:{args.port}  (Ctrl-C stops the server; every decision is already on disk)")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


def cmd_status(args) -> int:
    log = _open_log(args)
    s = log.status()
    c = s["counts"]
    t = s["timing"]
    res = ", ".join(f"{k} {v}" for k, v in s["resolutions"].items()) or "none yet"
    vers = s["graph_versions"]
    print(f"{args.batch_id}: graph {log.graph_sha256[:12]}"
          + (f"; the decisions were made on {len(vers)} graph versions" if len(vers) > 1 else ""))
    print(f"groups: {s['groups']['resolved']} resolved, {s['groups']['open']} open, {s['groups']['proposed']} "
          f"proposed (opened, not accepted)")
    print(f"resolutions: {res}")
    print(f"terms: {c['terms']['handled']} of {c['terms']['total']} handled ({c['terms']['remaining']} remaining)")
    pre = s["pre_handled"]
    if pre["terms"] or pre["live_elsewhere"] or pre["resolved_here_too"]:
        by = ", ".join(f"{b} {n}" for b, n in pre["by_batch"].items()) or "none"
        print(f"  from earlier review batches (the registry): {pre['terms']} handled from the start ({by}); "
              f"{pre['live_elsewhere']} parked or deferred there, live here; {pre['resolved_here_too']} resolved "
              "here too (this log's decision stands)")
    print(f"queue remaining: merged groups {c['merged']['remaining']} of {c['merged']['total']}, proposed groups "
          f"{c['proposed']['remaining']} of {c['proposed']['total']}, singletons {c['single']['remaining']} of "
          f"{c['single']['total']}")
    sp = log.state.sample_progress(since_seq=getattr(args, "sample_since", 0) or 0)
    if sp["reached"]:
        per = "; ".join(f"{s} {v['done']} done of {v['reached']} reached ({v['items']} in the queue, inclusion "
                        f"{v.get('inclusion', 0):.3f})" for s, v in sp["strata"].items())
        print(f"sample order (seed {sp['seed']}): {sp['reached']} items reached: {per}; {sp['pulled_in']} terms "
              "handled from outside the reached items")
    mp = t["minutes_per_resolved_group"]
    print(f"minutes per resolved group: median {mp['median']}, mean {mp['mean']}; active minutes {t['active_minutes']} "
          f"in {t['sessions']} sessions (gaps over {D.IDLE_MINUTES:g} minutes are idle); decisions per minute "
          f"{t['decisions_per_minute']}")
    print(f"events: {s['events']} ({', '.join(f'{k} {v}' for k, v in s['by_action'].items()) or 'none'}); "
          f"skipped on replay: {s['skipped']}")
    for x in s["skipped_events"]:
        print(f"  skipped {x['seq']} {x['action']} {x['group']}: {x['why']}")
    return 0


def cmd_apply(args) -> int:
    log = _open_log(args)
    vers = log.graph_versions()
    if len(vers) > 1 or (vers and log.graph_sha256 not in vers):
        print(f"NOTE: decisions were made on {len(vers)} graph versions; keys are registry keys, so they apply to "
              "the current graph's rows")
    if log.state.skipped:
        # a skipped decision is missing from what is applied: a row this review wrote for it is reset below
        print(f"WARNING: {len(log.state.skipped)} logged decisions no longer apply to this graph and are left out "
              "of this apply:")
        for x in log.state.skipped:
            print(f"  skipped {x['seq']} {x['action']} {x['group']}: {x['why']}")
    rep = D.apply_decisions(log.state, batch_id=args.batch_id, registry=Registry(args.registry),
                            queue_path=_queue_path(args), data_dir=args.data_dir, review_dir=_review_dir(args),
                            dry_run=args.dry_run, by=args.by, graph_sha256=log.graph_sha256)
    print(rep.format())
    if args.dry_run:
        print(f"DRY-RUN: nothing written ({args.registry}, {_queue_path(args)} unchanged)")
    elif rep.changed:
        print(f"written: {args.registry}" + (f", {_queue_path(args)}" if rep.promotions else "")
              + f"; record appended to {_review_dir(args) / D.APPLIED_NAME}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, helptext in (("serve", "the review app on 127.0.0.1 (Roger runs it)"),
                           ("status", "groups resolved and open, decisions by type, time per decision"),
                           ("apply", "the decisions into the registry's review blocks and the seed queue")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("--batch-id", required=True, help="the review batch (data/candidates/review/<B>/)")
        sp.add_argument("--out-root", type=Path, default=None, help="candidates dir holding review/<B>/")
        sp.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
        sp.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
        sp.add_argument("--queue", type=Path, default=None, help="the seed queue (default <data-dir>/seed_queue.json)")
        sp.add_argument("--by", default="roger", help="who decides (recorded on every event and review block)")
        if name == "serve":
            sp.add_argument("--port", type=int, default=DEFAULT_PORT)
            sp.add_argument("--host", default=DEFAULT_HOST, help="keep the default: the app has no login")
            sp.add_argument("--order", choices=D.ORDERS, default="cliques",
                            help="the queue's first order (o on the page switches)")
        if name == "status":
            sp.add_argument("--sample-since", type=int, default=0,
                            help="count the sample order's progress from after this log seq (a later sample session)")
        if name == "apply":
            sp.add_argument("--dry-run", action="store_true", help="print the writes; write nothing")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return {"serve": cmd_serve, "status": cmd_status, "apply": cmd_apply}[args.cmd](args)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
