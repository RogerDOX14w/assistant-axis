#!/usr/bin/env python3
"""The candidate registry CLI.

    uv run python data_analysis/gap_generation/gap_registry.py [--registry PATH] <command> ...

Commands:

* ``submit --file candidates.jsonl --generator G --run-id R``: rows
  ``{surface, rank?, score?, gloss_hint?, partner_hint?, sense_id?, source_ref?}``;
  new keys are appended, existing keys gain a source; prints the SubmitReport.
* ``status``: counts by verdict, decision, review status, holding list and generator.
* ``report [--generator G] [--decision D] [--verdict V] [--include-held]``: a
  markdown table, the main review list: rows on a holding list are left off
  unless ``--include-held``.
* ``holding --list physical|roles|states|nationalities``: a markdown block for
  Roger to paste into TRAITS_TO_ADD / ROLES_TO_ADD or to work the states and
  nationalities queues from (the tool never writes those files); a states row
  shows its states-pass suggestions.
* ``judgement-calls [--filter-results F ...]``: the words noted
  ``nontrait_person_sense`` (open point D, case 4: the obvious reading is a
  trait and another sense is a non-trait thing a person can be) as a table
  with the word, its trait sense, its other sense and an empty column for
  Roger's call.
* ``corpus-regions --from-filter DIR [--out PATH]``: write
  ``corpus_regions.json`` (every corpus trait -> region, ``alignment_relevant``,
  verdict, batch id) from a validation run's results, at no cost.
* ``compact``: copy the log to ``registry.jsonl.bak.<UTC>``, fold it to one
  line per key, and write the tracked snapshot ``registry.snapshot.jsonl``.
* ``promote (--keys K ... | --status accepted) [--min-local-novelty X] [--section S] [--dry-run]``:
  append ``status: "candidate"`` entries to ``data/seed_queue.json`` (refuses
  corpus and queue collisions and holding-list rows, except a states row the
  states pass judged plausible, which is promoted under its suggested name).

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
    if not args.include_held:
        # the main review list: rows on a holding list (roles, physical, states,
        # nationalities) are reviewed from their own lists (`holding --list`)
        rows = [r for r in rows if not r.get("holding")]
    print("| key | label | verdict | tags | region | alignment | polysemy | decision | nearest | gloss |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        f = r.get("filter") or {}
        nv = r.get("novelty") or {}
        tags = list(f.get("tags") or [])
        if f.get("membership_kind"):
            tags = [f"membership:{f['membership_kind']}" if t == "membership" else t for t in tags]
        print(f"| {r['key']} | {_md(r['label'])} | {_md(f.get('verdict'))} | {_md(', '.join(tags))} "
              f"| {_md(f.get('region'))} | {_md(f.get('alignment_relevant'))} | {_md(f.get('polysemy'))} "
              f"| {_md(nv.get('decision'))} | {_md(nv.get('nearest_existing'))} | {_md(r.get('gloss'))} |")
    return 0


HOLDING_TARGETS = {"physical": "TRAITS_TO_ADD.md (physical-attribute section)", "roles": "ROLES_TO_ADD.md",
                   "states": "the states queue (decision 12: check a habitual predisposition is plausible, "
                             "choose its name, write its description; states_pass.py drafts all three)",
                   "nationalities": "the nationalities queue (decision 3, open point B: traits, sampled from "
                                    "this list when more are wanted)"}


def _states_pass_note(r: dict) -> str:
    sp = r.get("states_pass") or {}
    if sp.get("mode") != "queue":
        return " [states pass: not run]"
    if not sp.get("plausible"):
        return f" [states pass: predisposition implausible: {sp.get('reason')}]"
    name = sp.get("suggested_name") if sp.get("name_fits") is False and sp.get("suggested_name") else r["label"]
    return f" [states pass: plausible; name {name}; draft: {sp.get('gloss')}]"


def cmd_holding(args) -> int:
    rows = holding_list(args.list, registry=Registry(args.registry))
    target = HOLDING_TARGETS[args.list]
    print(f"<!-- trait-gap registry holding list '{args.list}': {len(rows)} rows; paste into {target} -->")
    for r in rows:
        f = r.get("filter") or {}
        gens = sorted({s.get("generator") for s in r.get("sources") or []})
        note = _states_pass_note(r) if args.list == "states" else ""
        print(f"- **{r['label']}** ({', '.join(f.get('tags') or [])}; from {', '.join(gens)}): "
              f"{r.get('gloss') or ''}{note}")
    return 0


def judgement_call_rows(rows) -> list[tuple[str, str, str, str]]:
    """``(word, key, trait sense, other senses)`` for rows carrying the
    ``nontrait_person_sense`` note (open point D, case 4)."""
    out = []
    for r in rows:
        f = r.get("filter") or {}
        if "nontrait_person_sense" not in (f.get("polysemy_notes") or []):
            continue
        ps = f.get("person_senses") or []
        trait = next((s["sense"] for s in ps if s.get("kind") == "trait"), "")
        others = "; ".join(f"{s['sense']} ({s['kind']})" for s in ps if s.get("kind") != "trait")
        out.append((r["label"], r["key"], trait, others))
    return sorted(out, key=lambda x: x[1])


def cmd_judgement_calls(args) -> int:
    if args.filter_results:
        rows = [json.loads(x) for p in args.filter_results
                for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    else:
        rows = list(Registry(args.registry).fold().values())
    found = judgement_call_rows(rows)
    print(f"<!-- {len(found)} words whose obvious reading is a trait and which have another sense a person "
          f"can be (nontrait_person_sense): Roger's calls, to build a rubric from later -->")
    print("| word | key | trait sense | other sense | Roger's call |")
    print("|---|---|---|---|---|")
    for word, key, trait, others in found:
        print(f"| {_md(word)} | {key} | {_md(trait)} | {_md(others)} |  |")
    return 0


def cmd_corpus_regions(args) -> int:
    """``corpus_regions.json`` from a validation run's results (no API call;
    review_rubric_v2.md finding 8)."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.filter import corpus_regions
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    run = Path(args.from_filter)
    rows = [json.loads(x) for x in (run / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    run_meta = json.loads((run / "run.json").read_text(encoding="utf-8")) if (run / "run.json").exists() else {}
    stems = sorted(p.stem for p in (Path(args.data_dir) / "traits" / "instructions").glob("*.json"))
    regions = corpus_regions(rows, stems, batch_id=run_meta.get("batch_id") or run.name)
    missing = [s for s, v in regions.items() if v["verdict"] is None]
    env = json_metadata(regions, title=f"corpus regions from {run.name}",
                        inputs=[current_file_input(dep_key="filter_results", path=run / "results.jsonl")])
    out = Path(args.out)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out)
    print(f"wrote {len(regions)} traits to {out} ({len(missing)} not in the run"
          + (f": {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}" if missing else "") + ")")
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
    confirmed = {}
    for spec in args.confirm_state_name or []:
        key, sep, name = spec.partition("=")
        if not sep or not name.strip():
            raise SystemExit(f"--confirm-state-name takes KEY=NAME, not {spec!r}")
        confirmed[key.strip()] = name.strip()
    rep = promote(rows, queue, keys, data_dir=args.data_dir, dry_run=args.dry_run, section=args.section,
                  min_local_novelty=args.min_local_novelty, reopen_turned_down=args.reopen_turned_down,
                  confirmed_state_names=confirmed)
    for k in rep.promoted:
        e = next(x for x in rep.entries if x["gap_gen"]["registry_key"] == k)
        print(f"{'WOULD PROMOTE' if args.dry_run else 'PROMOTED'} {k} -> {e['stem']} ({e['entity_type']}"
              f"{', partner ' + e['partner'] if e.get('partner') else ''})")
    for k, why in rep.refused.items():
        print(f"REFUSED {k}: {why}")
    if args.dry_run or not rep.promoted:
        return 0
    se.save_queue(queue, args.queue)
    # the entry's stem, which a states-pass rename may have changed
    stem_of = {e["gap_gen"]["registry_key"]: e["stem"] for e in rep.entries}
    reg.update_many({k: {"seed_queue_stem": stem_of[k]} for k in rep.promoted})
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
    sp.add_argument("--include-held", action="store_true",
                    help="also list rows parked on a holding list (left off the main review list by default)")
    sp.set_defaults(func=cmd_report)
    sp = sub.add_parser("holding")
    sp.add_argument("--list", required=True, choices=list(HOLDING_TARGETS))
    sp.set_defaults(func=cmd_holding)
    sp = sub.add_parser("judgement-calls",
                        help="table of rows noted nontrait_person_sense, with an empty column for Roger's call")
    sp.add_argument("--filter-results", type=Path, nargs="+",
                    help="read filter results.jsonl files instead of the registry")
    sp.set_defaults(func=cmd_judgement_calls)
    sp = sub.add_parser("corpus-regions",
                        help="write corpus_regions.json (region and alignment_relevant per corpus trait) from a run")
    sp.add_argument("--from-filter", required=True, type=Path, help="a validation run's filter/<batch_id> dir")
    sp.add_argument("--out", type=Path, default=paths.CORPUS_REGIONS_PATH)
    sp.set_defaults(func=cmd_corpus_regions)
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
    sp.add_argument("--confirm-state-name", action="append", metavar="KEY=NAME",
                    help="Roger's confirmed name for a states row the states pass judged plausible (repeatable); "
                         "without it such a row is refused")
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
