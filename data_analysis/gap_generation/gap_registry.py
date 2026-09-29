#!/usr/bin/env python3
"""The candidate registry CLI.

    uv run python data_analysis/gap_generation/gap_registry.py [--registry PATH] <command> ...

Commands:

* ``submit --file candidates.jsonl --generator G --run-id R``: rows
  ``{surface, rank?, score?, gloss_hint?, partner_hint?, sense_id?, source_ref?}``;
  new keys are appended, existing keys gain a source; prints the SubmitReport.
* ``status``: counts by verdict, decision, review status, holding list and generator.
* ``report [--generator G] [--decision D] [--verdict V]``: a markdown table.
* ``holding --list physical|roles``: a markdown block for Roger to paste into
  TRAITS_TO_ADD / ROLES_TO_ADD (the tool never writes those files).
* ``compact``: copy the log to ``registry.jsonl.bak.<UTC>``, fold it to one
  line per key, and write the tracked snapshot ``registry.snapshot.jsonl``.
* ``promote (--keys K ... | --status accepted) [--min-local-novelty X] [--section S] [--dry-run]``:
  append ``status: "candidate"`` entries to ``data/seed_queue.json`` (refuses
  corpus and queue collisions and holding-list rows).

No command here makes an API call.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.filter import review_sort_key  # noqa: E402
from assistant_axis.gapgen.promote import DEFAULT_SECTION, promote  # noqa: E402
from assistant_axis.gapgen.registry import (  # noqa: E402
    Candidate, Registry, compact, holding_list, records_for_status, submit_candidates,
)
from assistant_axis.gapgen.runs import start_run  # noqa: E402


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def cmd_submit(args) -> int:
    paths.check_id(args.generator, "generator")
    paths.check_id(args.run_id, "run_id")
    cands = []
    for i, line in enumerate(Path(args.file).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        d = json.loads(line)
        if "surface" not in d:
            raise SystemExit(f"{args.file}:{i}: row has no 'surface'")
        cands.append(Candidate(surface=d["surface"], generator=args.generator, run_id=args.run_id,
                               rank=d.get("rank"), score=d.get("score"), gloss_hint=d.get("gloss_hint"),
                               sense_id=int(d.get("sense_id") or 1), source_ref=d.get("source_ref"),
                               partner_hint=d.get("partner_hint")))
    if args.dry_run:
        print(f"DRY-RUN: would submit {len(cands)} candidates from {args.file} as {args.generator}/{args.run_id}")
        return 0
    run = start_run(args.generator, args.run_id, args={"file": str(args.file), "via": "gap_registry.py submit"},
                    candidates_dir=args.registry.parent if args.registry != paths.REGISTRY_PATH else None)
    rep = submit_candidates(cands, registry_path=args.registry, run=run)
    run.finish()
    print(json.dumps({k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}))
    return 0


def cmd_status(args) -> int:
    reg = Registry(args.registry)
    rows = reg.fold()
    if reg.n_malformed:
        print(f"WARNING: {reg.n_malformed} malformed line(s) in {args.registry} (first at line "
              f"{reg.malformed[0][0]}); see compact --set-aside-malformed")
    c = {name: Counter() for name in ("verdict", "decision", "review", "holding", "generator")}
    for r in rows.values():
        c["verdict"][(r.get("filter") or {}).get("verdict") or "unfiltered"] += 1
        c["decision"][(r.get("novelty") or {}).get("decision") or "unscored"] += 1
        c["review"][(r.get("review") or {}).get("status") or "?"] += 1
        c["holding"][r.get("holding") or "none"] += 1
        for g in {s.get("generator") for s in r.get("sources") or []}:
            c["generator"][g] += 1
    print(f"{len(rows)} rows in {args.registry}")
    for name, cnt in c.items():
        print(f"by {name}: {json.dumps(dict(sorted(cnt.items())))}")
    return 0


def cmd_report(args) -> int:
    rows = records_for_status(Registry(args.registry), generator=args.generator, decision=args.decision,
                              verdict=args.verdict)
    rows = sorted(rows, key=review_sort_key)  # polysemy-flagged rows last (decision 11)
    print("| key | label | verdict | tags | region | alignment | polysemy (primary use) | decision | nearest "
          "| gloss |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        f = r.get("filter") or {}
        nv = r.get("novelty") or {}
        tags = list(f.get("tags") or [])
        if f.get("membership_kind"):
            tags = [f"membership:{f['membership_kind']}" if t == "membership" else t for t in tags]
        poly = f"{f.get('polysemy')}" + (f" ({f['primary_use']})" if f.get("primary_use") else "")
        print(f"| {r['key']} | {_md(r['label'])} | {_md(f.get('verdict'))} | {_md(', '.join(tags))} "
              f"| {_md(f.get('region'))} | {_md(f.get('alignment_relevant'))} | {_md(poly)} "
              f"| {_md(nv.get('decision'))} | {_md(nv.get('nearest_existing'))} | {_md(r.get('gloss'))} |")
    return 0


HOLDING_TARGETS = {"physical": "TRAITS_TO_ADD.md (physical-attribute section)", "roles": "ROLES_TO_ADD.md",
                   "states": "the states queue (decision 12: check a habitual predisposition is plausible, "
                             "choose its name, write its description)"}


def cmd_holding(args) -> int:
    rows = holding_list(args.list, registry=Registry(args.registry))
    target = HOLDING_TARGETS[args.list]
    print(f"<!-- trait-gap registry holding list '{args.list}': {len(rows)} rows; paste into {target} -->")
    for r in rows:
        f = r.get("filter") or {}
        gens = sorted({s.get("generator") for s in r.get("sources") or []})
        print(f"- **{r['label']}** ({', '.join(f.get('tags') or [])}; from {', '.join(gens)}): {r.get('gloss') or ''}")
    return 0


def cmd_compact(args) -> int:
    try:
        rep = compact(args.registry, set_aside_malformed=args.set_aside_malformed)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"compacted {rep.n_lines_before} lines to {rep.n_keys} keys; backup {rep.backup_path}; "
          f"snapshot {rep.snapshot_path}"
          + (f"; {rep.n_malformed} malformed line(s) moved to {rep.rejected_path}" if rep.rejected_path else ""))
    return 0


def cmd_promote(args) -> int:
    import data_analysis.seed_entities as se
    reg = Registry(args.registry)
    rows = reg.fold()
    if args.keys:
        keys = args.keys
    else:
        keys = [r["key"] for r in records_for_status(reg, review=args.status)]
    queue = se.load_queue(args.queue)
    rep = promote(rows, queue, keys, data_dir=args.data_dir, dry_run=args.dry_run, section=args.section,
                  min_local_novelty=args.min_local_novelty, reopen_turned_down=args.reopen_turned_down)
    for k in rep.promoted:
        e = next(x for x in rep.entries if x["gap_gen"]["registry_key"] == k)
        print(f"{'WOULD PROMOTE' if args.dry_run else 'PROMOTED'} {k} -> {e['stem']} ({e['entity_type']}"
              f"{', partner ' + e['partner'] if e.get('partner') else ''})")
    for k, why in rep.refused.items():
        print(f"REFUSED {k}: {why}")
    if args.dry_run or not rep.promoted:
        return 0
    se.save_queue(queue, args.queue)
    reg.update_many({k: {"seed_queue_stem": rows[k]["stem"]} for k in rep.promoted})
    print(f"appended {len(rep.promoted)} entries to {args.queue}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("submit")
    sp.add_argument("--file", required=True, type=Path)
    sp.add_argument("--generator", required=True)
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_submit)
    sp = sub.add_parser("status")
    sp.set_defaults(func=cmd_status)
    sp = sub.add_parser("report")
    sp.add_argument("--generator")
    sp.add_argument("--decision")
    sp.add_argument("--verdict")
    sp.set_defaults(func=cmd_report)
    sp = sub.add_parser("holding")
    sp.add_argument("--list", required=True, choices=["physical", "roles", "states"])
    sp.set_defaults(func=cmd_holding)
    sp = sub.add_parser("compact")
    sp.add_argument("--set-aside-malformed", action="store_true",
                    help="move malformed (torn) lines to registry.jsonl.rejected.<UTC> instead of refusing")
    sp.set_defaults(func=cmd_compact)
    sp = sub.add_parser("promote")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--keys", nargs="+")
    g.add_argument("--status", choices=["accepted"], help="rows whose review status is this")
    sp.add_argument("--min-local-novelty", type=float)
    sp.add_argument("--reopen-turned-down", action="store_true",
                    help="promote a word the seed queue marks not_adopted or superseded; its old decision is copied into the new entry")
    sp.add_argument("--section", default=DEFAULT_SECTION)
    sp.add_argument("--queue", type=Path, default=paths.SEED_QUEUE_PATH)
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_promote)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
