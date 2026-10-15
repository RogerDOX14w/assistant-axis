#!/usr/bin/env python3
"""The candidate registry CLI.

    uv run python data_analysis/gap_generation/gap_registry.py [--registry PATH] <command> ...

Commands:

* ``submit --file candidates.jsonl --generator G --run-id R``: rows
  ``{surface, rank?, score?, gloss_hint?, partner_hint?, sense_id?, source_ref?}``;
  new keys are appended, existing keys gain a source; prints the SubmitReport.
* ``submit --from data/candidates/runs/G/R/candidates.jsonl``: resubmit a generator
  run's tracked ``candidates.jsonl`` (one ``Candidate`` per line, exactly its fields,
  generator and run id included; ``registry.read_candidates``) into this checkout's
  log, the way a run made in another worktree reaches the main checkout.  Idempotent
  (a source already on a row changes nothing); no run directory is touched.
  Both forms run the platform's relabel step (a single-word noun gains its adjective sibling,
  ``assistant_axis/gapgen/nouns.py``) unless ``--no-relabel``.
* ``import-rows --from OTHER_REGISTRY --keys-file F [--only-run GEN/RUN] [--record PATH] [--dry-run]``:
  the rows of the keys in F (one per line; blank lines and lines starting with ``#`` skipped) from another
  checkout's registry log, with the blocks that checkout's filter and novelty runs wrote, for a run that was
  submitted *and judged* in a worktree (regeneration list GG5; ``registry.import_rows``).  A key this log lacks
  gets the other log's lines for it, in order, through the registry's write path (its fold then matches the
  other's but for ``rev`` and ``updated_at``); a key it has keeps every field and gains only the ``sources[]``
  entries it lacks (with ``--only-run``, only that run's).  Idempotent; checks the fold after writing (exit 1 on
  a mismatch); refused, before any write, for a key the other log lacks or a malformed line in it.  The other log
  is read without its lock (nothing is created in that checkout).  ``--record`` writes what was imported (keys,
  source lines with their revs and times, sources added, the other log's sha256) as a JSON envelope; refused
  when the file exists.  ``--dry-run`` prints the plan and writes nothing.
* ``status``: counts by verdict, decision, review status, holding list and generator.
* ``report [--generator G] [--decision D] [--verdict V] [--include-held]``: a
  markdown table, the main review list: rows on a holding list are left off
  unless ``--include-held``.  A noun the relabel step linked shows ``-> adjective``
  after its label, the adjective ``<- noun`` (``holding`` too).
* ``holding --list physical|roles|states|nationalities|states_released``: a
  markdown block for Roger to paste into TRAITS_TO_ADD / ROLES_TO_ADD or to work
  the states and nationalities queues from (the tool never writes those files);
  a row the states pass judged shows its states-pass answers (from v4 its route,
  typical duration and gloss; a role it sent to the roles list shows them too).
  ``states_released`` lists the rows the states pass v4 moved out of the states
  queue (they go through M3 and the review app, not into a file).
* ``judgement-calls [--filter-results F ...] [--calls-file P]``: the words
  noted ``obvious_sense_not_trait`` (the main reading is not a trait), first,
  then those noted ``nontrait_person_sense`` (open point D, case 4: the
  obvious reading is a trait and another sense is a non-trait thing a person
  can be), as a table with the word, the note, its trait sense, its other
  senses and Roger's call, read from ``data/candidates/judgement_calls.json``
  (tracked; keyed by word).
* ``judgement-call --word W --call TEXT [--calls-file P]``: record Roger's
  call on a word in that file (a later call on the same word replaces it).
* ``corpus-regions --from-filter DIR [--from-filter DIR2 ...] [--out PATH]``: write
  ``corpus_regions.json`` (every corpus trait -> region, ``alignment_relevant``,
  verdict, batch id) from validation runs' results, at no cost.  With several
  runs a trait takes the last run that has it; a row under a stem the corpus
  has since renamed counts for the renamed trait (``renamed_from`` in the
  entry), so a later run is how a trait whose description changed sense with
  its rename gets judged again.  The regions of that mode are the filter's gloss of the bare label; since
  2026-10-09 (QUESTIONS 3) the corpus's regions come from its descriptions instead (the next form).
* ``corpus-regions --from-descriptions (--all | --only-missing) --budget-usd C [--batch-id B] [--dry-run
  [--show STEM ...]] [--concurrency N] [--allow-dirty] [--out PATH]``: M1's descriptors and alignment calls (Haiku 5.5, the
  pinned ``descriptors.md`` and ``alignment.md``, sent as M1's wave 6 sends them) on every trait file's
  ``description`` with its ``positive_label``, written to ``corpus_regions.json`` with the region,
  ``enactable_in_text``, ``alignment_score`` 0-3, ``alignment_relevant`` (score 2 or 3), ``source:
  "description"``, the description's SHA-256, model and rubric versions, and ``previous_region`` /
  ``previous_alignment_relevant`` / ``previous_source`` on each row it replaces.  ``--all`` judges every trait;
  ``--only-missing`` (run it after each corpus chunk) only those with no row, a row not from a description,
  a changed description or label, or a failed call.  Responses, ``usage.json`` and ``run.json`` go to
  ``data/candidates/corpus_regions_runs/<B>/``.  The only command here that makes API calls
  (``assistant_axis/gapgen/corpus_descriptors.py``); refused while the platform's own paths have uncommitted
  changes unless ``--allow-dirty`` (``run.json`` records the git sha and ``dirty_check``).
* ``synonyms [--stem X] [--run-id R]``: M3's rename shortlist (design item 8 of
  coding_plan_platform.md's M3 design): the candidates M3 judged covered, under the
  trait that covers them, the traits whose candidates read 4 first, then 3, the
  exact-label matches last; each with its deciding readings and reasons
  (``novelty.synonyms``); then the candidates a review merged into a trait or
  queue entry (``review_app.py apply``; ``review_app.decisions.review_merges``).
* ``compact [--uncompressed]``: copy the log to ``registry.jsonl.bak.<UTC>``, fold it to one
  line per key, and write the tracked snapshot, gzipped: ``registry.snapshot.jsonl.gz`` (since 2026-10-12;
  ``--uncompressed`` writes ``registry.snapshot.jsonl`` as before, refused over 90 MB).  ``--registry`` may name a
  gzipped snapshot for the read-only commands.  The log keeps the raw rows and the retraction records; the snapshot
  is the folded view (retracted runs applied) followed by the retraction records.
* ``retract --run GENERATOR/RUN_ID --reason TEXT [--by WHO] [--force] [--dry-run]`` (2026-10-15): back out a run whose
  output was buggy.  Appends a retraction record (who, when, why, the counts, and the history of the run's earlier
  retractions) to the log; from then on every reader's fold leaves out that run's sources, and the rows only it
  proposed (``registry.retract``).  Prints the rows dropped, the rows kept with fewer sources, those whose first gloss
  hint (M1's intended sense) changes, and the ``relabel`` links cleared.  Refused, before any write, when a row it
  would drop or change has a settled review (accepted, rejected, merged_into), a seed-queue entry (its
  ``seed_queue_stem``, or a queue entry's ``gap_gen.registry_key``), or when a row that stays is merged into a row that
  goes; ``--force`` retracts anyway and records which keys it overrode.  ``--by`` defaults to ``git config
  user.name``.  ``--dry-run`` prints the same and writes nothing.
* ``unretract --run GENERATOR/RUN_ID --reason TEXT [--by WHO] [--dry-run]``: the reverse; the run's sources and rows
  come back.  ``retractions`` lists every run retracted now or before, with its history.
* ``promote (--keys K ... | --status accepted) [--confirm-state-name KEY=NAME ...] [--reopen-turned-down]
  [--min-local-novelty X] [--section S] [--queue PATH] [--dry-run]``:
  append ``status: "candidate"`` entries to ``data/seed_queue.json`` (refuses
  corpus and queue collisions and holding-list rows, except a states row the
  states pass judged plausible, which is promoted under the name Roger confirmed
  (``--confirm-state-name``; the pass's suggested name is only quoted),
  and a physical row named with ``--keys``, which joins the physical track:
  tag ``physical``, the track's section; ``--status accepted`` still refuses
  it; ``assistant_axis/gapgen/physical_pass.py``; and a row the states pass v4
  released, named with ``--keys``: tags ``states_pass`` and ``lasting_state``
  or ``predisposition``, the pass's gloss as the draft; ``--status accepted``
  refuses it too; ``assistant_axis/gapgen/states_pass.py``).

No other command here makes an API call.
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
from assistant_axis.gapgen import records as RF  # noqa: E402
from assistant_axis.gapgen.promote import DEFAULT_SECTION, promote  # noqa: E402
from assistant_axis.gapgen.registry import (  # noqa: E402
    Candidate, Registry, compact, holding_list, records_for_status, submit_candidates,
)
from assistant_axis.gapgen.runs import git_sha, platform_dirty_files, start_run  # noqa: E402


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def cmd_submit_from(args) -> int:
    """``submit --from PATH``: a run's ``candidates.jsonl`` into this checkout's registry log, as is."""
    from assistant_axis.gapgen.registry import read_candidates
    if args.generator or args.run_id:
        print("REFUSED: --from takes the generator and run id from each row of the file; drop --generator / --run-id",
              file=sys.stderr)
        return 2
    try:
        cands = read_candidates(args.from_path)
    except (OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    runs = Counter(f"{c.generator}/{c.run_id}" for c in cands)
    if args.dry_run:
        print(f"DRY-RUN: would submit {len(cands)} candidates from {args.from_path} ({json.dumps(dict(sorted(runs.items())))}) "
              f"to {args.registry}")
        return 0
    rep = submit_candidates(cands, registry_path=args.registry, relabel=None if args.no_relabel else "auto")
    print(json.dumps({k: v for k, v in rep.as_dict().items() if k not in ("keys", "relabels")} | {"n_keys": len(rep.keys),
                                                                                "runs": dict(sorted(runs.items()))}))
    return 0


def cmd_submit(args) -> int:
    if args.from_path is not None:
        return cmd_submit_from(args)
    if not (args.generator and args.run_id):
        print("REFUSED: --file needs --generator and --run-id", file=sys.stderr)
        return 2
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
    rep = submit_candidates(cands, registry_path=args.registry, run=run, relabel=None if args.no_relabel else "auto")
    run.finish()
    print(json.dumps({k: v for k, v in rep.as_dict().items() if k not in ("keys", "relabels")}
                     | {"n_keys": len(rep.keys)}))
    return 0


def read_keys_file(path: Path) -> list[str]:
    """Registry keys, one per line; blank lines and lines starting with ``#`` are skipped (a key never starts
    with ``#``, though it contains one: ``stem#sense``)."""
    return [s for s in (line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines())
            if s and not s.startswith("#")]


def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_import_rows(args) -> int:
    """``import-rows``: rows of another checkout's registry log into this one (``registry.import_rows``)."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import import_rows, utc_now
    only_run = None
    if args.only_run:
        gen, sep, run_id = args.only_run.partition("/")
        if not sep:
            print("REFUSED: --only-run takes GENERATOR/RUN_ID", file=sys.stderr)
            return 2
        only_run = (paths.check_id(gen, "generator"), paths.check_id(run_id, "run_id"))
    if args.record is not None and args.record.exists() and not args.dry_run:
        print(f"REFUSED: {args.record} exists: give a new --record path (a record is never overwritten)", file=sys.stderr)
        return 2
    try:
        keys = read_keys_file(args.keys_file)
        source_sha = _sha256_file(args.from_path)
        rep = import_rows(args.from_path, keys, registry_path=args.registry, only_run=only_run, dry_run=args.dry_run)
    except (OSError, ValueError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    c = rep.counts()
    by_lines = Counter(len(v) for v in rep.replayed.values())
    runs_added = Counter(f"{s.get('generator')}/{s.get('run_id')}" for v in rep.sources_added.values() for s in v)
    head = "DRY-RUN: would import" if args.dry_run else "imported"
    print(f"{head} {c['n_keys']} keys from {args.from_path} (sha256 {source_sha[:16]}) into {args.registry}: "
          f"{c['replayed_keys']} new keys replayed with {c['replayed_lines']} lines "
          f"(lines a key: {json.dumps(dict(sorted(by_lines.items())))}); {c['keys_gaining_sources']} existing keys "
          f"gaining {c['sources_added']} sources ({json.dumps(dict(sorted(runs_added.items())))}); "
          f"{c['unchanged']} existing keys unchanged; "
          + (f"{c['lines_planned']} lines to append" if args.dry_run else f"{c['n_lines_written']} lines appended"))
    if args.dry_run:
        return 0
    if rep.verified:
        print(f"verified: the fold of every touched key ({len(rep.replayed) + len(rep.sources_added)}) is what the "
              f"import meant to write (rev and updated_at aside)")
    else:
        print(f"MISMATCH after the write, {len(rep.mismatches)} key(s): "
              f"{json.dumps(dict(list(rep.mismatches.items())[:10]))}", file=sys.stderr)
    if args.record is not None:
        from assistant_axis.plot_metadata import json_metadata
        from assistant_axis.provenance import current_file_input
        body = {"what": "gap_registry.py import-rows", "at": utc_now(), "git_sha": git_sha(), "argv": sys.argv,
                "source_sha256": source_sha, "keys_file": str(args.keys_file),
                "only_run": "/".join(only_run) if only_run else None, "counts": c, **rep.as_dict()}
        env = json_metadata(body, title=f"registry import of {c['n_keys']} keys from {args.from_path}",
                            inputs=[current_file_input(dep_key="keys_file", path=args.keys_file)])
        atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", args.record)
        print(f"record: {args.record}")
    return 0 if rep.verified else 1


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
    gone = sorted(f"{g}/{r}" for g, r in reg.retracted_runs())
    if gone:
        print(f"retracted runs (left out of every count here): {', '.join(gone)}")
    for name, cnt in c.items():
        print(f"by {name}: {json.dumps(dict(sorted(cnt.items())))}")
    return 0


def relabel_arrow(r: dict) -> str:
    """`` -> pedantic`` on a noun row the relabel step linked (`` (corpus trait)`` when its adjective is one),
    `` <- pedant`` on its adjective row, else empty (``assistant_axis/gapgen/nouns.py``)."""
    b = r.get("relabel") or {}
    if b.get("to_corpus_stem"):
        return f" -> {b['to_corpus_stem']} (corpus trait)"
    if b.get("to_key"):
        return f" -> {str(b['to_key']).split('#')[0]}"
    src = b.get("from_surface") or (str(b["from_key"]).split("#")[0] if b.get("from_key") else None)
    return f" <- {src}" if src else ""


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
        print(f"| {r['key']} | {_md(r['label'] + relabel_arrow(r))} | {_md(f.get('verdict'))} | {_md(', '.join(tags))} "
              f"| {_md(f.get('region'))} | {_md(f.get('alignment_relevant'))} | {_md(f.get('polysemy'))} "
              f"| {_md(nv.get('decision'))} | {_md(nv.get('nearest_existing'))} | {_md(r.get('gloss'))} |")
    return 0


HOLDING_TARGETS = {"physical": "TRAITS_TO_ADD.md (physical-attribute section)", "roles": "ROLES_TO_ADD.md",
                   "states": "the states queue (decision 12: check a habitual predisposition is plausible, "
                             "choose its name, write its description; states_pass.py drafts all three)",
                   "nationalities": "the nationalities queue (decision 3, open point B: traits, sampled from "
                                    "this list when more are wanted)",
                   "states_released": "nowhere: rows the states pass v4 moved out of the states queue go through M3 "
                                      "(novelty_score.py score --holding states) and the review app"}


def _states_pass_note(r: dict) -> str:
    sp = r.get("states_pass") or {}
    if sp.get("mode") != "queue":
        return " [states pass: not run]"
    if sp.get("route"):   # v4 (2026-10-09): the route, the duration and the gloss
        why = f"; {sp['route_reason']}" if sp.get("route_reason") else ""
        name = f"; name {sp['suggested_name']}" if sp.get("route") == "renamed" and sp.get("suggested_name") else ""
        return (f" [states pass v{sp.get('rubric_version')}: {sp['route']} ({sp.get('typical_duration')}){name}{why}; "
                f"draft: {sp.get('gloss')}]")
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
        note = _states_pass_note(r) if args.list in ("states", "states_released") or r.get("states_pass") else ""
        print(f"- **{r['label']}**{relabel_arrow(r)} ({', '.join(f.get('tags') or [])}; from {', '.join(gens)}): "
              f"{r.get('gloss') or ''}{note}")
    return 0


#: The notes the judgement-call table lists, in the order it lists them
#: (round 5: ``obvious_sense_not_trait`` first, review_rubric_v2_fixes.md
#: defect 4; before, those rows reached no table).
JUDGEMENT_CALL_NOTES = ("obvious_sense_not_trait", "nontrait_person_sense")


def judgement_call_rows(rows) -> list[tuple[str, str, str, str, str]]:
    """``(word, key, note, trait sense, other senses)`` for rows carrying a
    note of :data:`JUDGEMENT_CALL_NOTES`: ``obvious_sense_not_trait`` rows
    first (the main reading is not a trait), then ``nontrait_person_sense``
    (open point D, case 4), each group by key.  A row with both notes is
    listed once, under the first."""
    out = []
    for r in rows:
        f = r.get("filter") or {}
        notes = f.get("polysemy_notes") or []
        note = next((n for n in JUDGEMENT_CALL_NOTES if n in notes), None)
        if note is None:
            continue
        ps = f.get("person_senses") or []
        trait = next((s["sense"] for s in ps if s.get("kind") == "trait"), "")
        others = "; ".join(f"{s['sense']} ({s['kind']})" for s in ps if s.get("kind") != "trait")
        out.append((r["label"], r["key"], note, trait, others))
    return sorted(out, key=lambda x: (JUDGEMENT_CALL_NOTES.index(x[2]), x[1]))


def load_judgement_calls(path: Path) -> dict:
    """Roger's calls, ``{"_meta": ..., "calls": {word: {"call", "at"}}}``;
    an absent file is an empty one."""
    p = Path(path)
    if not p.exists():
        return {"_meta": {"description": "Roger's judgement calls on the words listed by "
                                         "gap_registry.py judgement-calls, keyed by word"}, "calls": {}}
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_judgement_calls(args) -> int:
    if args.filter_results:
        rows = [json.loads(x) for p in args.filter_results
                for x in RF.read_text(p).splitlines() if x.strip()]
    else:
        rows = list(Registry(args.registry).fold().values())
    found = judgement_call_rows(rows)
    calls = load_judgement_calls(args.calls_file)["calls"]
    print(f"<!-- {len(found)} words to judge: obvious_sense_not_trait (the main reading is not a trait) first, "
          f"then nontrait_person_sense (the obvious reading is a trait and another sense is something else a "
          f"person can be).  Roger's calls come from {args.calls_file} (record one with judgement-call) -->")
    print("| word | key | note | trait sense | other sense | Roger's call |")
    print("|---|---|---|---|---|---|")
    for word, key, note, trait, others in found:
        call = (calls.get(word) or {}).get("call") or ""
        print(f"| {_md(word)} | {key} | {note} | {_md(trait)} | {_md(others)} | {_md(call)} |")
    return 0


def cmd_judgement_call(args) -> int:
    """Record (or replace) Roger's call on one word."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.registry import utc_now
    obj = load_judgement_calls(args.calls_file)
    word = " ".join(args.word.split())
    old = obj["calls"].get(word)
    obj["calls"][word] = {"call": args.call.strip(), "at": utc_now()}
    obj["calls"] = dict(sorted(obj["calls"].items()))
    atomic_write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", Path(args.calls_file))
    print(f"{'replaced' if old else 'recorded'} the call on {word!r} in {args.calls_file}"
          + (f" (was: {old.get('call')!r})" if old else ""))
    return 0


def _anthropic_client():
    """The live client of ``corpus-regions --from-descriptions`` (the tests replace this function)."""
    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _corpus_regions_runs_root() -> Path:
    """Where ``corpus-regions --from-descriptions`` puts its run directories (the tests replace this function)."""
    return paths.CORPUS_REGIONS_RUNS_DIR


def cmd_corpus_regions_from_descriptions(args) -> int:
    """``corpus_regions.json`` from the trait files' descriptions: M1's descriptors and alignment calls on each
    description (QUESTIONS 3, Roger 2026-10-09; :mod:`assistant_axis.gapgen.corpus_descriptors`)."""
    import logging
    from datetime import datetime, timezone

    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen import corpus_descriptors as CD
    from assistant_axis.gapgen import split_rubrics as sr
    from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import BudgetExceededError
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    mode = "all" if args.all else "only_missing" if args.only_missing else None
    if mode is None:
        raise SystemExit("corpus-regions --from-descriptions needs --all or --only-missing")
    log = logging.getLogger("gap_registry.corpus_regions")
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    out = Path(args.out)
    corpus = CD.load_corpus(args.data_dir)
    existing = CD.load_existing(out)
    selected = CD.select(corpus, existing, mode=mode)
    try:
        pinned = CD.pins()
    except ValueError as exc:
        print(f"REFUSED: the rubrics on disk are not their pinned versions: {exc}", file=sys.stderr)
        return 2
    n_send = sum(1 for t, _ in selected if t["description"].strip())
    est = CD.estimate(n_send)
    reasons = Counter(why for _, why in selected)
    print(f"{len(corpus)} traits; {len(selected)} to judge ({mode}"
          + (f": {json.dumps(dict(sorted(reasons.items())))}" if selected else "") + f"); {CD.MODEL}, descriptors "
          f"v{pinned['step_versions']['descriptors']}, alignment v{pinned['step_versions']['alignment']}")
    # Rows of traits the corpus no longer has (a dropped trait, 2026-10-09: conceptual and enigmatic stayed after
    # 647ca4d because a run with nothing to judge returned before CD.merge, which is what drops them).
    stale = sorted(set(existing) - {t["stem"] for t in corpus})
    if stale:
        print(f"{len(stale)} row(s) of traits the corpus no longer has, to drop: {', '.join(stale)}")
    if not selected:
        if not stale:
            print(f"nothing to judge: {out} is current")
            return 0
        if args.dry_run:
            print(f"nothing to judge; DRY-RUN: {out} untouched")
            return 0
        # No call: keep the provenance of the runs that produced the remaining rows.
        old_inputs = (json.loads(out.read_text(encoding="utf-8")).get("_provenance") or {}).get("inputs")
        env = json_metadata(CD.merge(corpus, existing, {}), inputs=old_inputs,
                            title=f"corpus regions from descriptions (rows dropped: {', '.join(stale)})")
        atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out)
        print(f"nothing to judge; dropped {len(stale)} row(s): wrote {len(env['result'])} rows to {out}")
        return 0
    print(f"estimate ({n_send} traits with a description):\n{est.format()}")
    # the paid run refuses on uncommitted platform code and records the check and the git sha, as the platform's
    # other paid CLIs do (code review 2026-10-12, B4; review 3 D7)
    from assistant_axis.gapgen.runs import dirty_refusal
    dirty_refused, dirty_check = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if args.dry_run:
        by_stem = {t["stem"]: t for t in corpus}
        for s in args.show or [selected[0][0]["stem"]]:
            if s not in by_stem:
                print(f"REFUSED: --show {s}: no such trait", file=sys.stderr)
                return 2
            print(CD.render(by_stem[s]))
        if dirty_refused:
            print(f"DRY-RUN: the real run would be REFUSED: {dirty_refused}")
        print(f"DRY-RUN: no call sent; {out} and {_corpus_regions_runs_root()} untouched")
        return 0
    if args.budget_usd is None:
        print("REFUSED: a paid run needs --budget-usd (the cap; see the estimate above)", file=sys.stderr)
        return 2
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=False)
    except CostRefused:
        return 2
    if dirty_refused:
        print(f"REFUSED: {dirty_refused}", file=sys.stderr)
        return 2
    sha = git_sha()
    batch_id = args.batch_id or "corpus_desc_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = _corpus_regions_runs_root() / paths.check_id(batch_id, "batch_id")
    if run_dir.exists():
        print(f"REFUSED: {run_dir} exists: give a new --batch-id (batch {batch_id} has run)", file=sys.stderr)
        return 2
    run_dir.mkdir(parents=True)
    usage = GuardedUsage(budget_usd=cap, usage_path=run_dir / "usage.json")
    judged: dict[str, dict] = {}
    started, stopped = utc_now(), None
    concurrency = args.concurrency or CD.DEFAULT_CONCURRENCY
    try:
        CD.run_judge([t for t, _ in selected], client=_anthropic_client(), usage=usage, batch_id=batch_id,
                     records_path=run_dir / CD.RESPONSES_NAME, on_row=judged.__setitem__, concurrency=concurrency)
    except BudgetExceededError as exc:
        stopped = f"budget stop: {exc}"
        print(f"STOPPED (budget): {exc}; the {len(judged)} traits finished are written", file=sys.stderr)
    finally:
        usage.write_json(run_dir / "usage.json")
        rates = CD.parse_rates(judged)
        result = CD.merge(corpus, existing, judged)
        failed = sorted(s for s, r in judged.items() if r.get("errors"))
        from assistant_axis.gapgen import prompt_labels as PL
        # every corpus-regions run is new: its prompts show the judge display form (the rows keep the stored label)
        meta = {"batch_id": batch_id, "stage": CD.STAGE, "source": CD.SOURCE, "mode": mode, "model": CD.MODEL,
                "git_sha": sha, "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check,
                "step_versions": pinned["step_versions"], "prompt_sha256": pinned["prompt_sha256"],
                PL.LABEL_FORM_KEY: PL.DEFAULT_LABEL_FORM,
                "concurrency": concurrency, "budget_usd": cap, "estimate_usd": round(est.usd, 6),
                "n_corpus": len(corpus), "n_selected": len(selected), "reasons": dict(sorted(reasons.items())),
                "n_judged": len(judged), "n_failed": len(failed), "failed": failed, "parse_rates": rates,
                "regions": CD.region_counts({s: judged[s] for s in judged}),
                "alignment_scores": dict(sorted(Counter(str(r.get("alignment_score")) for r in judged.values()).items())),
                "cost_usd": round(usage.total_cost_usd, 4), "n_calls": usage.n_calls, "stopped": stopped,
                "out": str(out), "started_at": started, "finished_at": utc_now(), "argv": sys.argv}
        atomic_write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", run_dir / "run.json")
        if judged:
            inputs = [current_file_input(dep_key=f"rubric_{s}", path=sr.rubric_path(s)) for s in CD.STEPS]
            if RF.exists(run_dir / CD.RESPONSES_NAME):
                inputs.append(current_file_input(dep_key=f"responses_{batch_id}",
                                                 path=RF.current_path(run_dir / CD.RESPONSES_NAME)))
            env = json_metadata(result, title=f"corpus regions from descriptions ({mode}, {batch_id})", inputs=inputs)
            atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out)
    for step, d in rates.items():
        warn_if_low_parse_rate(label=f"corpus_regions:{step}:{CD.MODEL}", n_ok=d["ok"], n_total=d["n"], logger_obj=log)
    before = {s: existing.get(s) or {} for s in result}
    ch = CD.changes(before, result)
    print(f"judged {len(judged)} of {len(selected)} traits ({len(failed)} with a failed call"
          + (f": {', '.join(failed[:10])}{' ...' if len(failed) > 10 else ''}" if failed else "") + f"); "
          f"{usage.n_calls} calls, ${usage.total_cost_usd:.4f}; wrote {len(result) if judged else 0} rows to "
          f"{out if judged else '(nothing)'}; run dir {run_dir}")
    print(f"regions before: {json.dumps(CD.region_counts(before))}")
    print(f"regions after:  {json.dumps(CD.region_counts(result))}")
    print(f"changed region: {ch['changed']}; same: {ch['same']}; gained a region: {ch['gained']}; "
          f"lost one: {ch['lost']}")
    print(f"alignment scores of the judged: {meta['alignment_scores']}; alignment_relevant (2 or 3) over the file: "
          f"{sum(1 for r in result.values() if r.get('alignment_relevant'))}")
    return 2 if stopped else 0


def cmd_corpus_regions(args) -> int:
    """``corpus_regions.json`` from validation runs' results (no API call;
    review_rubric_v2.md finding 8).  Several ``--from-filter`` runs merge in
    order, the last run that has a trait giving its entry; rows under a stem
    the corpus has renamed count for the renamed trait (2026-10-02, the merge
    with the main line).  ``--from-descriptions``: see
    :func:`cmd_corpus_regions_from_descriptions`."""
    from collections import Counter

    if args.from_descriptions:
        return cmd_corpus_regions_from_descriptions(args)
    extra = [f for f, v in (("--all", args.all), ("--only-missing", args.only_missing), ("--dry-run", args.dry_run),
                            ("--budget-usd", args.budget_usd is not None), ("--batch-id", args.batch_id),
                            ("--show", args.show), ("--concurrency", args.concurrency)) if v]
    if extra:
        raise SystemExit(f"corpus-regions --from-filter takes none of {', '.join(extra)} (they are for "
                         f"--from-descriptions)")
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.entity_id import resolve_renamed_stem
    from assistant_axis.gapgen.filter import corpus_regions_from_runs
    from assistant_axis.gapgen.normalize import split_key
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    data_dir = Path(args.data_dir)
    stems = sorted(p.stem for p in (data_dir / "traits" / "instructions").glob("*.json"))
    corpus = set(stems)
    runs, inputs, names = [], [], []
    for run in (Path(r) for r in args.from_filter):
        rows = RF.read_jsonl(run / "results.jsonl")
        run_meta = json.loads((run / "run.json").read_text(encoding="utf-8")) if (run / "run.json").exists() else {}
        batch_id = run_meta.get("batch_id") or run.name
        runs.append((batch_id, rows))
        names.append(run.name)
        inputs.append(current_file_input(dep_key="filter_results" if len(args.from_filter) == 1
                                         else f"filter_results_{batch_id}", path=RF.current_path(run / "results.jsonl")))
    old = {split_key(r["key"])[0] for _, rows in runs for r in rows if r.get("key")} - corpus
    renames = {s: resolve_renamed_stem(s, "traits", data_dir=data_dir) for s in sorted(old)}
    renames = {s: t for s, t in renames.items() if t != s and t in corpus}
    regions = corpus_regions_from_runs(runs, stems, renames=renames)
    missing = [s for s, v in regions.items() if v["verdict"] is None]
    env = json_metadata(regions, title=f"corpus regions from {' + '.join(names)}", inputs=inputs)
    out = Path(args.out)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out)
    by_run = Counter(v["batch_id"] for v in regions.values() if v["verdict"] is not None)
    followed = sorted(f"{v['renamed_from']} -> {s}" for s, v in regions.items() if v.get("renamed_from"))
    print(f"wrote {len(regions)} traits to {out} ({len(missing)} not in any run"
          + (f": {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}" if missing else "") + ")"
          + (f"; by run {dict(by_run)}" if len(runs) > 1 else "")
          + (f"; {len(followed)} through renamed_from: {', '.join(followed)}" if followed else ""))
    return 0


def cmd_synonyms(args) -> int:
    """The rename shortlist as a markdown table (no API call)."""
    from assistant_axis.gapgen.novelty import synonyms
    groups = synonyms(Registry(args.registry).fold().values(), stem=args.stem, run_id=args.run_id)
    n = sum(len(g["candidates"]) for g in groups)
    print(f"<!-- M3 rename shortlist: {n} covered candidates under {len(groups)} traits; traits whose candidates "
          f"read 4 first, then 3, exact-label matches last -->")
    print("| trait | best | candidate | key | reading | reason | gloss |")
    print("|---|---|---|---|---|---|---|")
    for g in groups:
        for c in g["candidates"]:
            rd = c.get("reading") or {}
            son, opus = rd.get("sonnet") or {}, rd.get("opus") or {}
            reading = ("exact label" + (f" ({(c.get('exact_label') or {}).get('match')})" if c.get("exact_label") else "")
                       if c["reason"] == "exact_label" else
                       f"Sonnet {son.get('value')}" + (f", Opus {opus.get('value')}" if opus else "")
                       + (f" (seed-queue entry, {c['covered_by_queue'].get('status')})" if c.get("covered_by_queue") else ""))
            why = opus.get("reason") or son.get("reason") or ""
            print(f"| {g['stem']} | {_md(g['best'])} | {_md(c['label'])} | {c['key']} | {_md(reading)} | {_md(why)} "
                  f"| {_md(c.get('gloss'))} |")
    # the review app's merges into a corpus trait or queue entry (coding_plan_review.md decision 5), after M3's
    from assistant_axis.gapgen.review_app.decisions import review_merges
    merges = review_merges(Registry(args.registry).fold().values(), stem=args.stem, run_id=args.run_id)
    if merges:
        print(f"<!-- review merges: {sum(len(g['candidates']) for g in merges)} candidates a review merged into "
              f"{len(merges)} traits or queue entries (review_app.py apply); best = review -->")
    for g in merges:
        for c in g["candidates"]:
            print(f"| {g['stem']} | review | {_md(c['label'])} | {c['key']} | merged in review {c['review_batch']} "
                  f"({c['review_group']}, {c['by']}) | {_md(c['note'])} | {_md(c.get('gloss'))} |")
    return 0


def cmd_compact(args) -> int:
    try:
        rep = compact(args.registry, set_aside_malformed=args.set_aside_malformed, uncompressed=args.uncompressed)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    print(f"compacted {rep.n_lines_before} lines to {rep.n_keys} keys; backup {rep.backup_path}; "
          f"snapshot {rep.snapshot_path} ({rep.snapshot_bytes / 2**20:.1f} MB"
          + (f", {rep.n_bytes / 2**20:.1f} MB uncompressed" if rep.snapshot_bytes != rep.n_bytes else "") + ")"
          + (f"; {rep.n_malformed} malformed line(s) moved to {rep.rejected_path}" if rep.rejected_path else ""))
    if rep.stale_snapshot is not None:
        print(f"NOTE: {rep.stale_snapshot} (the uncompressed snapshot) is out of date now; commit the gzipped one "
              f"and `git rm` it")
    return 0


def _by(args) -> str:
    if args.by:
        return args.by
    import subprocess
    try:
        name = subprocess.run(["git", "config", "user.name"], cwd=_REPO_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        name = ""
    if not name:
        raise SystemExit("REFUSED: say who retracts with --by (git config user.name is not set)")
    return name


def _queue_keys(path: Path) -> list[str]:
    """The registry keys the seed queue's entries name (``gap_gen.registry_key``); none when there is no queue."""
    if not Path(path).exists():
        return []
    q = json.loads(Path(path).read_text(encoding="utf-8"))
    return [k for e in (q.get("entries") or []) for k in [(e.get("gap_gen") or {}).get("registry_key")] if k]


def cmd_retract(args) -> int:
    """``retract`` / ``unretract``: a run's retraction record (``registry.retract``, ``registry.unretract``)."""
    from assistant_axis.gapgen.registry import retract, unretract
    gen, sep, run_id = (args.run or "").partition("/")
    if not sep:
        print("REFUSED: --run takes GENERATOR/RUN_ID", file=sys.stderr)
        return 2
    try:
        if args.cmd == "retract":
            rep = retract(args.registry, gen, run_id, reason=args.reason, by=_by(args), dry_run=args.dry_run,
                          force=args.force, queue_keys=_queue_keys(args.queue))
        else:
            rep = unretract(args.registry, gen, run_id, reason=args.reason, by=_by(args), dry_run=args.dry_run)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    c = rep.counts()
    verb = {"retract": ("drops", "keeps"), "unretract": ("restores", "gives back sources to")}[rep.action]
    print(f"{'DRY-RUN: ' if args.dry_run else ''}{rep.action} {rep.run} ({c['n_sources']} sources on record): "
          f"{verb[0]} {c['n_dropped']} rows; {verb[1]} {c['n_changed']} rows shared with other runs "
          f"({c['n_gloss_hint_changed']} of them change their first gloss hint, M1's intended sense); "
          f"{c['n_relabel_changed']} relabel links {'cleared' if rep.action == 'retract' else 'restored'}")

    def show(title: str, keys: list, n: int = 40) -> None:
        if keys:
            print(f"  {title} ({len(keys)}): {', '.join(keys[:n])}" + (" ..." if len(keys) > n else ""))
    show("rows dropped" if rep.action == "retract" else "rows restored", rep.dropped, 60 if args.verbose else 20)
    show("rows kept, sources removed" if rep.action == "retract" else "rows gaining sources", rep.changed,
         10**6 if args.verbose else 20)
    show("first gloss hint changes (M1 judged them under the run's gloss; re-run M1 with --keys if wanted)",
         rep.gloss_hint_changed, 10**6)
    show("relabel links", rep.relabel_changed, 10**6)
    for k, why in rep.blocked.items():
        print(f"  {'OVERRIDDEN' if rep.forced else 'BLOCKED'} {k}: {why}")
    if rep.refused:
        print(f"REFUSED: {rep.refused}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(f"DRY-RUN: would append to {args.registry}: {json.dumps({k: rep.record[k] for k in ('key', 'retracted', 'by', 'reason', 'forced')})}")
        return 0
    print(f"appended {rep.record['key']} (rev {rep.record['rev']}) to {args.registry}; reverse with "
          f"`gap_registry.py {'unretract' if rep.action == 'retract' else 'retract'} --run {rep.run} --reason ...`")
    return 0


def cmd_retractions(args) -> int:
    reg = Registry(args.registry)
    ctl = reg.controls()
    if not ctl:
        print("no run has been retracted")
        return 0
    for k, c in sorted(ctl.items()):
        state = "RETRACTED" if c.get("retracted") else "not retracted"
        print(f"{c.get('generator')}/{c.get('run_id')}: {state} since {c.get('at')} by {c.get('by')}: "
              f"{c.get('reason')} {json.dumps(c.get('effect'))}")
        for h in c.get("history") or []:
            print(f"    earlier: {h.get('action')} {h.get('at')} by {h.get('by')}: {h.get('reason')}")
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
    # a physical row, and a row the states pass released, is promoted only by name (the physical pass, QUESTIONS 1;
    # the states pass v4): --keys names it, --status does not
    rep = promote(rows, queue, keys, data_dir=args.data_dir, dry_run=args.dry_run, section=args.section,
                  min_local_novelty=args.min_local_novelty, reopen_turned_down=args.reopen_turned_down,
                  confirmed_state_names=confirmed, allow_physical=bool(args.keys),
                  allow_released_states=bool(args.keys))
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
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", type=Path, help="rows {surface, rank?, ...} of one run (with --generator and --run-id)")
    g.add_argument("--from", dest="from_path", type=Path,
                   help="a generator run's candidates.jsonl (Candidate's fields on each line, generator and run id "
                        "included), resubmitted as is; idempotent")
    sp.add_argument("--generator")
    sp.add_argument("--run-id")
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--no-relabel", action="store_true",
                    help="submit the rows as given: no adjective sibling for a noun (the M1 validation set, a replay "
                         "that must be judged as given); default: the platform's relabel step (nouns.py)")
    sp.set_defaults(func=cmd_submit)
    sp = sub.add_parser("import-rows",
                        help="rows of another checkout's registry log (with their filter and novelty blocks) into this "
                             "one, by key; idempotent")
    sp.add_argument("--from", dest="from_path", type=Path, required=True,
                    help="the other checkout's registry.jsonl (read without its lock; nothing is written there)")
    sp.add_argument("--keys-file", type=Path, required=True, help="the keys to import, one per line")
    sp.add_argument("--only-run", metavar="GENERATOR/RUN_ID",
                    help="a key this log already has gains only this run's sources (default: every source it lacks); "
                         "a key it lacks gets its whole source history, other runs' sources included")
    sp.add_argument("--record", type=Path, help="write what was imported to this JSON file (refused if it exists)")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_import_rows)
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
                        help="table of rows noted obvious_sense_not_trait or nontrait_person_sense, with Roger's "
                             "recorded call in the last column")
    sp.add_argument("--filter-results", type=Path, nargs="+",
                    help="read filter results.jsonl files instead of the registry")
    sp.add_argument("--calls-file", type=Path, default=paths.JUDGEMENT_CALLS_PATH)
    sp.set_defaults(func=cmd_judgement_calls)
    sp = sub.add_parser("judgement-call", help="record Roger's call on one word (replaces an earlier one)")
    sp.add_argument("--word", required=True)
    sp.add_argument("--call", required=True)
    sp.add_argument("--calls-file", type=Path, default=paths.JUDGEMENT_CALLS_PATH)
    sp.set_defaults(func=cmd_judgement_call)
    sp = sub.add_parser("corpus-regions",
                        help="write corpus_regions.json (region and alignment per corpus trait) from the trait "
                             "descriptions (--from-descriptions, paid) or from filter runs (--from-filter)")
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-filter", type=Path, action="append",
                   help="a validation run's filter/<batch_id> dir; repeat to merge runs, the last run that has a "
                        "trait giving its entry (the filter's gloss of the bare label; superseded 2026-10-09)")
    g.add_argument("--from-descriptions", action="store_true",
                   help="M1's descriptors and alignment calls on every trait file's description (Haiku 5.5)")
    m = sp.add_mutually_exclusive_group()
    m.add_argument("--all", action="store_true", help="--from-descriptions: judge every trait")
    m.add_argument("--only-missing", action="store_true",
                   help="--from-descriptions: judge only traits with no row, a row not from a description, a "
                        "changed description or label, or a failed call (run after each corpus chunk)")
    sp.add_argument("--budget-usd", type=float, help="--from-descriptions: the hard cap (needed unless --dry-run)")
    sp.add_argument("--batch-id", help="--from-descriptions: the run's id (default corpus_desc_<UTC time>)")
    sp.add_argument("--dry-run", action="store_true",
                    help="--from-descriptions: print the selection, the estimate and the rendered requests; send "
                         "nothing, write nothing")
    sp.add_argument("--show", nargs="+", metavar="STEM",
                    help="--from-descriptions --dry-run: render these traits' requests (default: the first selected)")
    sp.add_argument("--concurrency", type=int, help="--from-descriptions: calls in flight (default 8)")
    sp.add_argument("--allow-dirty", action="store_true",
                    help="--from-descriptions: run although the platform's own code or prompt paths have uncommitted "
                         "changes (refused otherwise; recorded in run.json)")
    sp.add_argument("--out", type=Path, default=paths.CORPUS_REGIONS_PATH)
    sp.set_defaults(func=cmd_corpus_regions)
    sp = sub.add_parser("synonyms", help="M3's rename shortlist: covered candidates under the trait that covers them")
    sp.add_argument("--stem", help="one covering trait only")
    sp.add_argument("--run-id", help="one M3 run only (its batch id)")
    sp.set_defaults(func=cmd_synonyms)
    sp = sub.add_parser("compact")
    sp.add_argument("--set-aside-malformed", action="store_true",
                    help="move malformed (torn) lines to registry.jsonl.rejected.<UTC> instead of refusing")
    sp.add_argument("--uncompressed", action="store_true",
                    help="write the snapshot as registry.snapshot.jsonl, as before 2026-10-12 (refused over 90 MB); "
                         "the default is the gzipped registry.snapshot.jsonl.gz")
    sp.set_defaults(func=cmd_compact)
    for name, hlp in (("retract", "back out a run: its sources leave every reader's fold, and the rows only it "
                                  "proposed with them (a record in the log; reversible)"),
                      ("unretract", "undo a retraction")):
        sp = sub.add_parser(name, help=hlp)
        sp.add_argument("--run", required=True, metavar="GENERATOR/RUN_ID")
        sp.add_argument("--reason", required=True, help="kept in the log")
        sp.add_argument("--by", default=None, help="who (default: git config user.name)")
        if name == "retract":
            sp.add_argument("--force", action="store_true",
                            help="retract although rows it drops or changes are settled (review, seed queue); the "
                                 "overridden keys are recorded")
            sp.add_argument("--queue", type=Path, default=paths.SEED_QUEUE_PATH,
                            help="seed queue whose gap_gen.registry_key entries block a retraction")
        sp.add_argument("--verbose", action="store_true", help="list every key")
        sp.add_argument("--dry-run", action="store_true")
        sp.set_defaults(func=cmd_retract)
    sp = sub.add_parser("retractions", help="every run retracted now or before, with its history")
    sp.set_defaults(func=cmd_retractions)
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
