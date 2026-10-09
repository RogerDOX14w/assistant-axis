#!/usr/bin/env python3
"""Near-duplicates in the trait corpus: M3's same-concept call on each trait's nearest non-partner neighbours (W3).

    uv run python data_analysis/gap_generation/corpus_near_duplicates.py run --budget-usd 10 --dry-run \\
        --also "mercurial/erratic:Roger asked" "technical/specialist:Roger asked"
    uv run python data_analysis/gap_generation/corpus_near_duplicates.py run --budget-usd 10 --also ...
    uv run python data_analysis/gap_generation/corpus_near_duplicates.py report

The logic is :mod:`assistant_axis.gapgen.near_duplicates`, whose docstring says what is read and how.  In short:
every trait file's ``--k`` (3) nearest other traits by cosine in M3's covered space (the corpus index of
``novelty_score.load_index``, from the embedding cache), its arrangement partners left out, pairs under
``--cosine-floor`` (0.35) dropped, unordered pairs deduplicated; the first direction of each pair (the stem that
sorts first as the target) read by rubric A, one pair per call, Sonnet 5.5 then Opus 5.5 under M3's rule at cut-off 3
(through ``NoveltyRunner.run_pairs``, prompt caching on, live); the second direction where the first's final reading
is 3 or above.  ``--also A/B[:note]`` pairs are read both ways whatever the first says (the pairs Roger asked about).

Commands:

* ``run --budget-usd C``: the scan.  Writes ``--out-dir`` (``data/candidates/near_duplicates_916/``):
  ``pairs.jsonl`` (one line per pair read: stems, labels, descriptions, cosine, both directions' Sonnet and Opus
  values and reasons, the final per direction, the section), ``responses.jsonl`` (every response, as M3 keeps them),
  ``usage.json`` (the project's schema plus a ``_provenance`` key), ``run.json`` (settings, counts, the plan, the
  readings distribution, in a provenance envelope), ``near_duplicates.md`` (the review document for Roger) and
  ``run.log``.  ``--compare-with`` (default ``calibration_916/drop_or_merge.md``): the cosine table compared in the
  document.  A stopped run goes on with ``--resume`` (no call already answered is sent again); ``--overwrite`` moves
  an old directory aside.
* ``report``: write ``near_duplicates.md`` again from ``pairs.jsonl`` and ``run.json``.  No call.

Cost: the estimate is printed before any call (the first direction on every pair; Opus and the second direction by
the shares M3 measured per cosine bin at cut-off 3, from the M3 runs' ``readings.jsonl``; per-call tokens measured
in their ``responses.jsonl``).  ``--budget-usd`` is the hard cap over the whole run (a ``--resume`` counts the earlier
sessions' spend); an estimate over it is refused; over $20 needs ``--confirm-expensive --confirmed-by``.  After the
first direction, the second is estimated again on the pairs actually sent to it, and the run stops before it if the
spend so far plus that would pass the cap.  ``--dry-run`` prints the plan, the estimate and one rendered request and
writes and calls nothing.  A paid run is refused while the platform's code or prompt paths have uncommitted changes,
unless ``--allow-dirty``.  Live transport only (the run is well under the $20 line).
"""
from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import embed as EM  # noqa: E402
from assistant_axis.gapgen import near_duplicates as ND  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import review_graph as RG  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import utc_now  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, log_formatter, \
    platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage  # noqa: E402
from data_analysis.gap_generation import novelty_score as NS  # noqa: E402

logger = logging.getLogger("corpus_near_duplicates")

DEFAULT_OUT_DIR = paths.DATA_CANDIDATES / "near_duplicates_916"
DEFAULT_COMPARE = paths.DATA_CANDIDATES / "calibration_916" / "drop_or_merge.md"
DEFAULT_M3_RUNS = paths.DATA_CANDIDATES / "novelty"
BATCH_ID = "near_duplicates_916"


class SecondGateRefused(RuntimeError):
    """Raised by the gate before the second direction when the spend so far plus its estimate would pass the cap."""


# --------------------------------------------------------------------------- inputs

def m3_measurements(runs_dir: Path) -> tuple[ND.Shares, dict, dict]:
    """``(shares, overlap tokens, info)`` from the M3 runs under ``runs_dir``: the shares at cut-off 3 by cosine bin
    from every ``readings.jsonl``, the mean billed tokens of the overlap calls from every ``responses.jsonl``."""
    readings, records, files = [], [], {"readings": [], "responses": []}
    for p in sorted(glob.glob(str(Path(runs_dir) / "*" / "readings.jsonl"))):
        files["readings"].append(str(Path(p).relative_to(_REPO_ROOT)) if Path(p).is_relative_to(_REPO_ROOT) else p)
        readings += [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    for p in sorted(glob.glob(str(Path(runs_dir) / "*" / "responses.jsonl"))):
        files["responses"].append(str(Path(p).relative_to(_REPO_ROOT)) if Path(p).is_relative_to(_REPO_ROOT) else p)
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if '"step": "overlap"' in line:
                records.append(json.loads(line))
    return ND.measured_shares(readings), RG.measured_overlap_tokens(records), \
        {"n_readings": len(readings), "n_overlap_records": len(records), "files": files}


def load_inputs(args):
    """``(cfg, index, index_info, partners, rubrics)``; ``SystemExit`` when the corpus is not in the embedding cache
    (this scan embeds nothing)."""
    from assistant_axis.gapgen.metric_config import MetricConfig
    rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    cfg = MetricConfig.load(args.metric_config)
    index, info = NS.load_index(cfg, data_dir=args.data_dir, cache=EM.EmbeddingCache(args.cache_dir))
    if index is None:
        raise SystemExit(f"{info['n_missing_from_cache']} corpus texts are not in the embedding cache "
                         f"({', '.join(info['missing'][:5])}...): run novelty_score.py score --embed-only first")
    partners = ND.arrangement_partners(args.data_dir)
    return cfg, index, info, partners, rubrics


def make_runner(*, client, rubrics: dict, index, usage, responses_path: Path, concurrency: int, config_version: str,
                embedding: dict, resume_records=()) -> NR.NoveltyRunner:
    return NR.NoveltyRunner(client=client, batch_id=BATCH_ID, rubrics=rubrics, index=index,
                            label_sets=NV.LabelSets(set(), {}, {}), usage=usage, responses_path=responses_path,
                            config_version=config_version, concurrency=concurrency, embedding=embedding,
                            resume_records=resume_records)


def provenance_inputs(args, rubrics: dict, data_dir: Path) -> list:
    from assistant_axis.provenance import current_file_input, current_files_input
    trait_files = sorted((Path(data_dir) / "traits" / "instructions").glob("*.json"))
    inputs = [current_file_input(dep_key="producer_script", path=Path(__file__).resolve()),
              current_files_input(dep_key="trait_files", paths=trait_files, extras={"n": str(len(trait_files))}),
              current_files_input(dep_key="rubric", paths=[paths.RUBRICS_DIR / "overlap_concept.md"],
                                  extras={"overlap_rubric": str(rubrics["overlap"]["version"])}),
              current_file_input(dep_key="metric_config", path=args.metric_config)]
    if args.compare_with and Path(args.compare_with).exists():
        inputs.append(current_file_input(dep_key="cosine_table", path=args.compare_with))
    return inputs


def write_usage(path: Path, usage: MultiModelUsage, *, inputs, title: str) -> None:
    """``usage.json`` in the project's schema with the run's provenance under a ``_provenance`` key beside it."""
    from assistant_axis.plot_metadata import json_metadata
    env = json_metadata(usage.as_dict(), title=title, inputs=inputs or None)
    atomic_write_text(json.dumps(usage.as_dict() | {"_provenance": env["_provenance"]}, indent=2, sort_keys=True) + "\n",
                      path)


def write_run(path: Path, run_meta: dict, *, inputs) -> None:
    from assistant_axis.plot_metadata import json_metadata
    atomic_write_text(json.dumps(json_metadata(run_meta, title=f"corpus_near_duplicates {BATCH_ID}", inputs=inputs),
                                 indent=2, ensure_ascii=False) + "\n", path)


def read_run(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    return d.get("result", d) if "_provenance" in d else d


def cosine_rows(path: Optional[Path]) -> Optional[list]:
    if not path or not Path(path).exists():
        return None
    return ND.parse_drop_or_merge(Path(path).read_text(encoding="utf-8"))


def rel_link(from_dir: Path, to: Path) -> str:
    return os.path.relpath(Path(to).resolve(), Path(from_dir).resolve())


def render_sample(runner: NR.NoveltyRunner, sp: ND.ScanPlan, cands: dict, rubrics: dict) -> str:
    """The first-direction request of the scan's nearest pair, as the model receives it (system prompt and user
    turn)."""
    if not sp.pairs:
        return "(no pair: nothing to render)"
    (a, b), d = max(sp.pairs.items(), key=lambda kv: (kv[1]["cosine"] or 0, kv[0]))
    runner.states.setdefault(a, NR.CandState(cand=cands[a]))
    c = runner._overlap_call(runner.states[a], b, "sonnet", 1)
    return (f"=== overlap call {a} > {b} (cosine {d['cosine']:.3f}), {c.model}, then Opus by the rule at cut-off "
            f"{ND.CUT_OFF}; system prompt: rubrics/overlap_concept.md version {rubrics['overlap']['version']} "
            f"(cached: {c.cache_system})\n--- system ---\n{c.system}\n--- user ---\n{c.user}")


# --------------------------------------------------------------------------- run

def write_outputs(out_dir: Path, *, rows, plan, traits, run_meta, compare_with, inputs, data_dir: Path) -> dict:
    n_deliberate = ND.mark_deliberate(rows, sources=ND.trait_sources(data_dir), traits=traits)
    dist = ND.readings_distribution(rows)
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), out_dir / "pairs.jsonl")
    crow = cosine_rows(compare_with)
    cmp = ND.comparison(rows, crow, corpus=traits, plan=plan) if crow is not None else None
    run_meta.update(readings=dist, sections={s: sum(1 for r in rows if r["section"] == s) for s in ND.SECTIONS},
                    n_deliberate=n_deliberate,
                    comparison=None if cmp is None else {
                        "file": str(compare_with), "n_rows": len(cmp["table"]),
                        "by_section_here": {str(k): v for k, v in cmp["n_rated"].items()},
                        "missed_both_ways": [[r["a"], r["b"]] for r in cmp["missed_both"]],
                        "n_missed_one_way": len(cmp["missed_one_way"])})
    md = ND.report_markdown(rows, plan=plan, traits=traits, cmp=cmp, run=run_meta, dist=dist,
                            cosine_table_rel=rel_link(out_dir, compare_with) if compare_with else "")
    atomic_write_text(md, out_dir / "near_duplicates.md")
    write_run(out_dir / "run.json", run_meta, inputs=inputs)
    return dist


def cmd_run(args, argv) -> int:
    out_dir = Path(args.out_dir)
    try:
        also = [ND.parse_pair(x) for x in (args.also or [])]
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    try:
        cfg, index, index_info, partners, rubrics = load_inputs(args)
    except NS.RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    traits = index.traits
    plan = ND.nearest_pairs(index.stems, index.Z, partners, k=args.k, floor=args.cosine_floor)
    try:
        sp = ND.scan_plan(plan, also=also, stems=index.stems, Z=index.Z, partners=partners)
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    cands = {s: ND.corpus_candidate(traits[s]) for s in traits}
    shares, tokens, minfo = m3_measurements(args.m3_runs_dir)
    embedding = {"model": cfg.live_model["model_id"], "representation": cfg.representation,
                 "variant": cfg.covered["space"]["variant"], "config_version": cfg.config_version}

    resuming = bool(args.resume and out_dir.exists())
    spent_before = MultiModelUsage.load_or_create(out_dir / "usage.json").total_cost_usd if resuming else 0.0
    est = ND.estimate_scan(sp, shares, overlap_tokens=tokens)
    print(f"plan: {json.dumps(plan.stats)}")
    print(f"also: {json.dumps([[a, b, n] for a, b, n in also])}; pairs read: {len(sp.pairs)} "
          f"({len(sp.both_ways)} both ways whatever the first says)")
    print(f"shares at cut-off {ND.CUT_OFF} (M3's readings, by cosine bin): {json.dumps(shares.as_dict())}")
    print(f"overlap tokens a call (M3's records): {json.dumps(tokens)}")
    print(f"estimate:\n{est.format()}")
    if resuming:
        print(f"resume: ${spent_before:.3f} spent by the earlier sessions; answers on record are replayed, so the "
              f"estimate above is an upper bound on what is left; the cap counts the earlier spend")
    refused, cap = None, None
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
        print(f"hard cap: ${cap:.2f} (the whole run{', earlier sessions included' if resuming else ''})")
    except CostRefused as exc:
        refused = exc.msg
    sha, dirty = git_sha(), platform_dirty_files()
    dirty_check = {"paths": list(PLATFORM_PATHS), "dirty": dirty,
                   "note": None if dirty is not None else "git unavailable: not checked"}
    if refused is None and dirty and not args.allow_dirty:
        refused = (f"uncommitted changes to the platform's own code or prompt paths ({len(dirty)}: "
                   f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty")
        print(f"REFUSED: {refused}", file=sys.stderr)
    probe = make_runner(client=None, rubrics=rubrics, index=index, usage=MultiModelUsage(),
                        responses_path=out_dir / "responses.jsonl", concurrency=args.concurrency,
                        config_version=cfg.config_version, embedding=embedding)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/")
        print(render_sample(probe, sp, cands, rubrics))
        return 0
    if refused:
        return 2
    status, resume_records, earlier = NS._prepare_out_dir(out_dir, args)
    if status:
        return status
    if earlier is not None and "_provenance" in earlier:
        earlier = earlier.get("result", earlier)
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    inputs = provenance_inputs(args, rubrics, args.data_dir)
    t0 = time.monotonic()
    run_meta = {"batch_id": BATCH_ID, "git_sha": sha, "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check,
                "argv": sys.argv[1:] if argv is None else list(argv), "transport": "live",
                "plan": plan.stats, "n_pairs_read": len(sp.pairs), "also": [[a, b, n] for a, b, n in also],
                "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "estimate_inputs": {"shares": shares.as_dict(), "overlap_tokens": tokens, **minfo},
                "budget_usd": args.budget_usd, "cap_usd": cap, "confirmed_by": args.confirmed_by,
                "rubric": {k: rubrics["overlap"][k] for k in ("name", "version", "sha256")},
                "models": {"overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
                "settings": {"k": args.k, "cosine_floor": args.cosine_floor, "cut_off": ND.CUT_OFF,
                             "rules": ND.RULES.name, "second_direction": "where the first's final reading is 3 or "
                             "above; the --also pairs always", "concurrency": args.concurrency,
                             "overlap_max_tokens": NR.OVERLAP_MAX_TOKENS, "ask_attempts": NR.ASK_ATTEMPTS,
                             "cache_system": True},
                "embedding": embedding, "corpus": {k: v for k, v in index_info.items() if k != "queue_stems"},
                "data_dir": str(args.data_dir), "resumed": bool(args.resume), "started_at": utc_now()}
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [
            {k: earlier.get(k) for k in ("started_at", "finished_at", "cost_usd", "status", "stopped_by_error")}]
    write_run(out_dir / "run.json", run_meta, inputs=inputs)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    if args.resume:
        usage.merge_from(MultiModelUsage.load_or_create(out_dir / "usage.json"))
    status, error, runner, rows = 0, None, None, None
    try:
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        runner = make_runner(client=anthropic.AsyncAnthropic(max_retries=0), rubrics=rubrics, index=index, usage=usage,
                             responses_path=out_dir / "responses.jsonl", concurrency=args.concurrency,
                             config_version=cfg.config_version, embedding=embedding, resume_records=resume_records)

        def gate(back) -> None:
            todo = [x for x in back if not runner.cache_good.get(
                runner._overlap_call(runner.states.setdefault(x[0], NR.CandState(cand=cands[x[0]])), x[1], "sonnet",
                                     2).cache_key())]
            g = ND.estimate_second(todo, overlap_tokens=tokens)
            spent = usage.total_cost_usd
            run_meta["gate"] = {"second_items": len(back), "not_on_record": len(todo), "spent_usd": round(spent, 4),
                                "second_estimate_usd": round(g.usd, 4), "cap_usd": cap,
                                "first_done_s": round(time.monotonic() - t0, 1)}
            print(f"after the first direction: {len(back)} pairs for the second ({len(todo)} not on record); spent "
                  f"${spent:.3f}, second-direction estimate ${g.usd:.3f}, cap ${cap:.2f}")
            if spent + g.usd > cap:
                raise SecondGateRefused(f"the second direction would bring the spend to about ${spent + g.usd:.2f}, "
                                        f"over the cap ${cap:.2f}; --resume with a larger --budget-usd")

        first, second, back = ND.run_scan(runner, sp, cands, gate=gate)
        rows = ND.assemble_rows(sp, traits=traits, first=first, second=second, back=back)
    except (BudgetExceededError, SecondGateRefused, CostRefused) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised
        error = exc
        print(f"STOPPED by {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        write_usage(out_dir / "usage.json", usage, inputs=inputs, title=f"corpus_near_duplicates {BATCH_ID}")
        run_meta.update(finished_at=utc_now(), wall_time_s=round(time.monotonic() - t0, 1),
                        cost_usd=round(usage.total_cost_usd, 4), n_calls=usage.n_calls, status=status,
                        stopped_by_error=f"{type(error).__name__}: {error}" if error is not None else None)
        if runner is not None:
            run_meta["calls_sent"] = {k.split(":", 1)[1]: v for k, v in sorted(runner.stats.items())
                                      if k.startswith("sent:")}
            run_meta["calls_resumed"] = runner.stats.get("resumed", 0)
            run_meta["parse_rates"] = runner.warn_parse_rates(logger)
        if rows is not None:
            incomplete = sum(1 for r in rows if r["section"] == "incomplete")
            run_meta["complete"] = incomplete == 0
            run_meta["n_incomplete"] = incomplete
            write_outputs(out_dir, rows=rows, plan=plan, traits=traits, run_meta=run_meta,
                          compare_with=args.compare_with, inputs=inputs, data_dir=args.data_dir)
        else:
            write_run(out_dir / "run.json", run_meta, inputs=inputs)
        logging.getLogger().removeHandler(fh)
        fh.close()
        print(usage.log_line())
    if rows is not None:
        c = {s: sum(1 for r in rows if r["section"] == s) for s in (*ND.SECTIONS, "incomplete")}
        print(f"{len(rows)} pairs: {json.dumps(c)}; {out_dir / 'near_duplicates.md'}")
        if c["incomplete"]:
            print(f"INCOMPLETE: {c['incomplete']} pairs left without an answer; run again with --resume")
    return status


# --------------------------------------------------------------------------- report

def cmd_report(args) -> int:
    out_dir = Path(args.out_dir)
    run_meta = read_run(out_dir / "run.json")
    if run_meta is None or not (out_dir / "pairs.jsonl").exists():
        print(f"{out_dir}: no run.json or pairs.jsonl; run first", file=sys.stderr)
        return 1
    rows = [json.loads(x) for x in (out_dir / "pairs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    data_dir = Path(run_meta.get("data_dir") or args.data_dir)
    from assistant_axis.gapgen.metric_config import MetricConfig
    cfg = MetricConfig.load(args.metric_config)
    index, _ = NS.load_index(cfg, data_dir=data_dir, cache=EM.EmbeddingCache(args.cache_dir))
    if index is None:
        print("the corpus is not in the embedding cache", file=sys.stderr)
        return 1
    st = run_meta.get("settings") or {}
    plan = ND.nearest_pairs(index.stems, index.Z, ND.arrangement_partners(data_dir), k=st.get("k", ND.DEFAULT_K),
                            floor=st.get("cosine_floor", ND.DEFAULT_COSINE_FLOOR))
    inputs = provenance_inputs(args, NS.load_m3_rubrics(args.rubrics_dir), data_dir)
    write_outputs(out_dir, rows=rows, plan=plan, traits=index.traits, run_meta=run_meta,
                  compare_with=args.compare_with, inputs=inputs, data_dir=data_dir)
    print(f"wrote {out_dir / 'near_duplicates.md'}")
    return 0


# --------------------------------------------------------------------------- the parser

def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    p.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    p.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    p.add_argument("--rubrics-dir", type=Path, default=None)
    p.add_argument("--compare-with", type=Path, default=DEFAULT_COMPARE,
                   help="the cosine table compared in the document (default calibration_916/drop_or_merge.md)")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="the scan (overlap calls, live)")
    _common(r)
    r.add_argument("--k", type=int, default=ND.DEFAULT_K, help="nearest other traits per trait (default 3)")
    r.add_argument("--cosine-floor", type=float, default=ND.DEFAULT_COSINE_FLOOR,
                   help="no call on a pair below this cosine (default 0.35, decision 11 of coding_plan_review.md)")
    r.add_argument("--also", nargs="+", metavar="A/B[:NOTE]", default=None,
                   help="pairs read both ways whatever the first says (stems; the note is shown in the document)")
    r.add_argument("--m3-runs-dir", type=Path, default=DEFAULT_M3_RUNS,
                   help="M3 run directories whose readings and records the estimate measures")
    r.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    r.add_argument("--budget-usd", type=float, required=True, help="the hard cap")
    r.add_argument("--confirm-expensive", action="store_true")
    r.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    r.add_argument("--resume", action="store_true", help="continue the directory; no call answered is sent again")
    r.add_argument("--overwrite", action="store_true", help="move an existing directory to <dir>.bak.<UTC> first")
    r.add_argument("--allow-dirty", action="store_true")
    r.add_argument("--dry-run", action="store_true", help="print the plan, the estimate and a request; write nothing")
    rp = sub.add_parser("report", help="write near_duplicates.md again from pairs.jsonl (no call)")
    _common(rp)
    return ap


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args, argv)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
