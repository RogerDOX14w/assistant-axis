#!/usr/bin/env python3
"""The pre-pilot test of the M3 overlap rubrics (m3_overlap_rubric_draft.md, "The test"; 2026-10-03).

    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --dry-run
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 [--budget-usd 15]
        [--models claude-haiku-4-5-20251001 claude-sonnet-5-5 claude-opus-5-5] [--rubrics A B] [--seed 0]
        [--n-targets 100] [--concurrency 8] [--stop-below 0.99] [--resume] [--allow-dirty]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --analyse-only
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --decode-marks

Builds the pair set (``assistant_axis.gapgen.overlap_test.build_pair_set``: about 100 seeded targets with
persona vectors and their 3 nearest traits under the covered setting, plus the labelled pairs between two
corpus traits, grouped as M3 would group them), and sends one call per target to each (rubric, model):
rubric A (``rubrics/overlap_concept.md``) and rubric B (``rubrics/overlap_cooccurrence.md``) on Haiku 4.5,
Sonnet 5.5 and Opus 5.5, live, temperature 0 where the model accepts it.  The stages run Haiku first, then
Sonnet, then Opus, so that a parse problem shows up on the cheapest model.  A call whose answer does not
parse fully is sent once more (every model alike; the first attempt's parse rate is reported too), and a
stage whose parse rate is still below ``--stop-below`` (default 0.99, the project's alert line) stops the
run before the next stage.  ``--resume`` sends again only the calls without a fully parsed answer.

Writes ``data/candidates/overlap_test/<run id>/``: ``pairs.json`` (the calls and pairs, with the
provenance envelope), ``rendered_prompts.md`` (the requests as sent, for three variants: a nearest target,
one whose list holds the target's recorded antonym, one with a single listed trait), ``responses.jsonl``
(every request and answer, parsed), ``usage.json`` (cumulative ``MultiModelUsage``, written after every
stage), ``run.json``, ``results.jsonl`` (one row per pair, rubric and model), ``summary.json`` (the
analysis, with the provenance envelope), ``tables.md``, ``run.log``, and ``marks_key.json``; and Roger's
blinded sheet ``reports/trait_gap_generation/m3_overlap_marks.md``.  ``--decode-marks`` reads his marks
back into ``marks_decoded.json``.

``--dry-run`` builds everything, prints the plan, the estimate and the rendered prompts, and writes and
sends nothing.  The cap (``--budget-usd``, default $15) is enforced by ``cost.GuardedUsage``; an estimate
above it is refused.  A paid run refuses uncommitted changes to the platform's files (``--allow-dirty``).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import overlap_test as OT  # noqa: E402
from assistant_axis.gapgen import persona as PS  # noqa: E402
from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.paths import (  # noqa: E402
    CALIBRATION_DIR, DATA_CANDIDATES, EMBEDDING_CACHE_DIR, METRIC_CONFIG_PATH, RUBRICS_DIR, check_id,
)
from assistant_axis.gapgen.registry import utc_now  # noqa: E402
from assistant_axis.gapgen.runs import (  # noqa: E402
    PLATFORM_PATHS, configure_logging, git_sha, log_formatter, platform_dirty_files,
)
from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402

logger = logging.getLogger("overlap_test")

OUT_ROOT = DATA_CANDIDATES / "overlap_test"
MARKS_SHEET = _REPO_ROOT / "reports" / "trait_gap_generation" / "m3_overlap_marks.md"
DEFAULT_BUDGET_USD = 15.0


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True, help="directory name under --out-root")
    ap.add_argument("--out-root", type=Path, default=OUT_ROOT)
    ap.add_argument("--models", nargs="+", default=list(OT.MODELS))
    ap.add_argument("--rubrics", nargs="+", default=list(OT.RUBRICS), choices=list(OT.RUBRICS))
    ap.add_argument("--reference", default=OT.REFERENCE, help="the model the others are compared with")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-targets", type=int, default=OT.N_TARGETS)
    ap.add_argument("--n-neighbours", type=int, default=OT.N_NEIGHBOURS)
    ap.add_argument("--n-antonyms", type=int, default=OT.N_ANTONYMS)
    ap.add_argument("--n-random", type=int, default=OT.N_RANDOM)
    ap.add_argument("--budget-usd", type=float, default=DEFAULT_BUDGET_USD, help="hard cap for the whole run")
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", default=None)
    ap.add_argument("--concurrency", type=int, default=OT.DEFAULT_CONCURRENCY)
    ap.add_argument("--stop-below", type=float, default=0.99,
                    help="stop before the next stage when a stage's parse rate is below this (default 0.99)")
    ap.add_argument("--n-boot", type=int, default=2000, help="bootstrap resamples for the correlation intervals")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, the estimate and the rendered prompts")
    ap.add_argument("--resume", action="store_true", help="continue a run: calls already answered are not re-sent")
    ap.add_argument("--allow-dirty", action="store_true", help="run with uncommitted platform changes (recorded)")
    ap.add_argument("--analyse-only", action="store_true", help="recompute the analysis from responses.jsonl")
    ap.add_argument("--decode-marks", action="store_true", help="read Roger's marks back from --marks-sheet")
    ap.add_argument("--marks-sheet", type=Path, default=MARKS_SHEET)
    ap.add_argument("--rubrics-dir", type=Path, default=RUBRICS_DIR)
    ap.add_argument("--metric-config", type=Path, default=METRIC_CONFIG_PATH)
    ap.add_argument("--cache-dir", type=Path, default=EMBEDDING_CACHE_DIR, help="embedding cache (gitignored)")
    ap.add_argument("--vectors-dir", type=Path, default=PS.DEFAULT_VECTORS_DIR)
    ap.add_argument("--labelled-pairs", type=Path, default=CALIBRATION_DIR / "labelled_pairs.json")
    ap.add_argument("--drop-or-merge", type=Path, default=CALIBRATION_DIR / "drop_or_merge.md")
    return ap.parse_args(argv)


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return str(p)


def build(args):
    inputs = OT.load_inputs(_REPO_ROOT, metric_config_path=args.metric_config, cache_dir=args.cache_dir,
                            vectors_dir=args.vectors_dir, labelled_path=args.labelled_pairs, dm_path=args.drop_or_merge)
    rubrics = OT.load_rubrics(args.rubrics_dir)
    ps = OT.build_pair_set(inputs.corpus, inputs.emb_stems, inputs.Z, inputs.persona, inputs.labelled, inputs.dm_pairs,
                           inputs.partner, seed=args.seed, n_targets=args.n_targets, n_neighbours=args.n_neighbours,
                           n_antonyms=args.n_antonyms, n_random=args.n_random)
    ps.info.update(embedding=inputs.settings, persona=inputs.persona_info)
    return inputs, rubrics, ps


def variant_calls(ps: OT.PairSet) -> dict:
    """The calls whose rendered prompts are read before a paid run: a nearest target with no recorded
    opposite in its list, a nearest target whose list holds its recorded antonym, and a call with a
    single listed trait."""
    by_call: dict = {}
    for p in ps.pairs:
        by_call.setdefault(p.call_id, []).append(p)
    out = {}
    for c in ps.calls:
        ant = [p for p in by_call[c.call_id] if OT.is_antonym_pair(p)]
        if "normal" not in out and c.set == OT.NEAREST and not ant:
            out["normal"] = c
        if "antonym_in_list" not in out and c.set == OT.NEAREST and ant:
            out["antonym_in_list"] = c
        if "single" not in out and len(c.listed) == 1:
            out["single"] = c
    if "antonym_in_list" not in out:
        for c in ps.calls:
            if any(OT.is_antonym_pair(p) for p in by_call[c.call_id]):
                out["antonym_in_list"] = c
                break
    return out


def rendered_prompts_text(ps, rubrics, corpus, model: str) -> str:
    v = variant_calls(ps)
    out = ["# Rendered prompts of the overlap test", "",
           "The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the "
           f"user turn), for {len(v)} variants; settings shown for {model}.  Both rubrics receive the identical "
           "user turn.", ""]
    for name, c in v.items():
        pairs = [p for p in ps.pairs if p.call_id == c.call_id]
        out += [f"## Variant: {name} ({c.call_id})", "",
                "Listed (id: stem, group, recorded opposite): " + "; ".join(
                    f"{p.id}: {p.listed}, {p.group}{', opposite' if OT.is_antonym_pair(p) else ''}"
                    for p in sorted(pairs, key=lambda p: p.id)), ""]
        for r in rubrics:
            out += ["```text", OT.rendered_prompt(c, corpus, rubric=r, rubric_text=rubrics[r]["text"], model=model)
                    .rstrip("\n"), "```", ""]
    return "\n".join(out)


def provenance_inputs(inputs, *, responses: Path = None):
    from assistant_axis.provenance import current_file_input, current_files_input
    specs = [current_file_input(dep_key="producer_script", path=Path(__file__)),
             current_file_input(dep_key="overlap_test_module", path=Path(OT.__file__)),
             current_files_input(dep_key="trait_files",
                                 paths=sorted((_REPO_ROOT / "data" / "traits" / "instructions").glob("*.json"))),
             current_file_input(dep_key="metric_config", path=inputs.paths["metric_config"]),
             current_file_input(dep_key="embedding_cache", path=inputs.paths["embedding_cache"],
                                extras={k: str(v) for k, v in inputs.settings.items()}),
             current_file_input(dep_key="labelled_pairs", path=inputs.paths["labelled_pairs"]),
             current_file_input(dep_key="drop_or_merge", path=inputs.paths["drop_or_merge"]),
             current_files_input(dep_key="rubrics", paths=[RUBRICS_DIR / "overlap_concept.md",
                                                           RUBRICS_DIR / "overlap_cooccurrence.md",
                                                           RUBRICS_DIR / "versions.json"])]
    if inputs.paths["persona_cache"].exists():
        specs.append(current_file_input(dep_key="persona_cache", path=inputs.paths["persona_cache"],
                                        extras={"slot": str(inputs.persona_info["slot"]),
                                                "layer": str(inputs.persona_info["layer"]),
                                                "shear_applied": str(inputs.persona_info["shear_applied"])}))
    if responses is not None and Path(responses).exists():
        specs.append(current_file_input(dep_key="responses", path=responses))
    return specs


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_analysis(out_dir: Path, inputs, ps, args, argv) -> dict:
    from assistant_axis.plot_metadata import json_metadata
    records = OT.read_records(out_dir / "responses.jsonl")
    answers = OT.collect_answers(ps, records)
    rows = OT.results_rows(ps, answers)
    (out_dir / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    models = [m for m in args.models if any((r, m) in answers for r in OT.RUBRICS)]
    summary = OT.analyse(ps, answers, models=models, reference=args.reference, n_boot=args.n_boot, seed=args.seed,
                         first_parse=OT.first_attempt_parse(ps, records))
    usage_path = out_dir / "usage.json"
    if usage_path.exists():
        summary["usage"] = json.loads(usage_path.read_text())
    summary["pair_set_info"] = ps.info
    env = json_metadata(summary, inputs=provenance_inputs(inputs, responses=out_dir / "responses.jsonl"),
                        title=f"M3 overlap rubric test {args.run_id}", script=_rel(Path(__file__)), argv=argv)
    write_json(out_dir / "summary.json", env)
    (out_dir / "tables.md").write_text(OT.summary_markdown(summary, ps, inputs.corpus), encoding="utf-8")
    return summary


def write_marks(out_dir: Path, inputs, ps, rubrics, args) -> None:
    key_path = out_dir / "marks_key.json"
    if key_path.exists() and args.marks_sheet.exists():
        logger.info("marks sheet and key exist; kept as written (%s)", _rel(args.marks_sheet))
        return
    import os
    items = OT.draw_marks(ps, seed=args.seed)
    sheet_dir = Path(args.marks_sheet).resolve().parent
    rel_key = os.path.relpath(key_path.resolve(), sheet_dir)
    rel_prefix = os.path.relpath(_REPO_ROOT, sheet_dir) + "/"
    sheet = OT.marks_sheet(items, inputs.corpus, rubric_text=rubrics["A"]["text"], run_id=args.run_id,
                           key_link=rel_key, rel_prefix=rel_prefix)
    args.marks_sheet.parent.mkdir(parents=True, exist_ok=True)
    args.marks_sheet.write_text(sheet, encoding="utf-8")
    write_json(key_path, OT.marks_key(items, run_id=args.run_id, seed=args.seed, sheet=_rel(args.marks_sheet)))


def decode(out_dir: Path, ps, args) -> int:
    key_path = out_dir / "marks_key.json"
    if not key_path.exists() or not args.marks_sheet.exists():
        print(f"no marks key ({_rel(key_path)}) or sheet ({_rel(args.marks_sheet)})", file=sys.stderr)
        return 1
    key = json.loads(key_path.read_text())
    dec = OT.decode_marks(args.marks_sheet.read_text(encoding="utf-8"), key)
    answers = OT.collect_answers(ps, OT.read_records(out_dir / "responses.jsonl"))
    dec["agreement_with_roger"] = OT.compare_marks(dec, answers, models=args.models)
    dec["decoded_at"] = utc_now()
    write_json(out_dir / "marks_decoded.json", dec)
    print(f"marks: {dec['counts']}")
    for m, ag in dec["agreement_with_roger"].items():
        print(f"  {OT.SHORT.get(m, m)}: exact {ag.get('exact_all')} over {ag.get('n_both_parsed')}, "
              f"numeric exact {ag.get('exact')}, within one {ag.get('within_one')}, kappa {ag.get('kappa_quadratic')}")
    return 0


async def run_stages(client, rubrics, corpus, ps, args, usage, out_dir: Path, run: dict, save_run) -> int:
    runner = OT.OverlapRunner(client, rubrics, corpus, usage=usage, responses_path=out_dir / "responses.jsonl",
                              concurrency=args.concurrency)
    for model in args.models:
        for r in args.rubrics:
            t0 = time.time()
            logger.info("stage: rubric %s (%s) on %s, %d calls", r, OT.RUBRICS[r]["name"], model, len(ps.calls))
            res = await runner.run_stage(r, model, ps.calls)
            stage = {"rubric": r, "model": model, "n_calls": res.n_calls, "n_sent": res.n_sent,
                     "n_skipped": res.n_skipped, "n_reasked": res.n_reasked, "n_pairs": res.n_pairs,
                     "n_ok": res.n_ok, "n_ok_first_attempt": res.n_ok_first,
                     "parse_rate": None if res.parse_rate is None else round(res.parse_rate, 4),
                     "budget_exceeded": res.budget_exceeded, "seconds": round(time.time() - t0, 1),
                     "cost_usd_total_after": round(usage.total_cost_usd, 4), "finished_at": utc_now()}
            run["stages"].append(stage)
            save_run()
            logger.info("stage done: %s; %s", json.dumps(stage), usage.log_line())
            if res.budget_exceeded:
                logger.error("budget cap $%.2f reached during rubric %s on %s: stopping", args.budget_usd, r, model)
                run["stopped"] = f"budget cap reached at rubric {r} on {model}"
                return 2
            if res.parse_rate is not None and res.parse_rate < args.stop_below:
                logger.error("*** parse rate %.4f below %.2f for rubric %s on %s: stopping before the next stage",
                             res.parse_rate, args.stop_below, r, model)
                run["stopped"] = f"parse rate {res.parse_rate:.4f} below {args.stop_below} at rubric {r} on {model}"
                return 3
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    argv_list = sys.argv[1:] if argv is None else list(argv)
    configure_logging()
    check_id(args.run_id, "run_id")
    out_dir = Path(args.out_root) / args.run_id
    unknown = [m for m in args.models if m not in OT.MODELS]
    if unknown:
        print(f"unknown model(s) {unknown}: this test knows {list(OT.MODELS)}", file=sys.stderr)
        return 1
    if args.reference not in args.models and not (args.decode_marks or args.analyse_only):
        logger.warning("the reference %s is not among --models; agreement is not computed", args.reference)

    inputs, rubrics, ps = build(args)

    if args.decode_marks or args.analyse_only:
        if not (out_dir / "pairs.json").exists():
            print(f"{_rel(out_dir)} has no pairs.json", file=sys.stderr)
            return 1
        recorded = OT.PairSet.from_json(json.loads((out_dir / "pairs.json").read_text()))
        if args.decode_marks:
            return decode(out_dir, recorded, args)
        write_analysis(out_dir, inputs, recorded, args, argv_list)
        print(f"wrote {_rel(out_dir / 'summary.json')} and {_rel(out_dir / 'tables.md')}")
        return 0

    resuming = args.resume and (out_dir / "responses.jsonl").exists()
    done = set()
    prior = MultiModelUsage()
    if resuming:
        done = OT.done_keys(OT.read_records(out_dir / "responses.jsonl"))
        prior = MultiModelUsage.load_or_create(out_dir / "usage.json")
        recorded = OT.PairSet.from_json(json.loads((out_dir / "pairs.json").read_text()))
        if [(c.call_id, c.listed) for c in recorded.calls] != [(c.call_id, c.listed) for c in ps.calls]:
            print("REFUSED: the pair set built now differs from the recorded pairs.json (inputs or seed changed)",
                  file=sys.stderr)
            return 2
    elif out_dir.exists() and (out_dir / "responses.jsonl").exists():
        print(f"{_rel(out_dir)} already has responses: pass --resume to continue it, or choose a new --run-id",
              file=sys.stderr)
        return 1

    todo_calls = {(r, m): [c for c in ps.calls if (r, m, c.call_id) not in done] for m in args.models
                  for r in args.rubrics}
    est = OT.Estimate()
    for (r, m), cs in todo_calls.items():
        est.lines.extend(OT.estimate(cs, inputs.corpus, rubrics, [m], [r]).lines)
    info = ps.info
    print(f"M3 overlap test {args.run_id}: {info['n_calls']} calls ({info['n_calls_by_set']}), {info['n_pairs']} pairs "
          f"by group {info['n_pairs_by_group']}; {info['n_pairs_with_persona_cos']} pairs with a persona-space cosine; "
          f"list sizes {info['list_sizes']}; {info['nearest_recorded_antonyms']} nearest pairs are recorded clean "
          f"pairs; {info['n_unordered_pairs_twice']} unordered pairs judged in two calls")
    print(f"labelled: {json.dumps(info['labelled'])}")
    print(f"embedding: {json.dumps(inputs.settings)}; persona: {json.dumps({k: v for k, v in inputs.persona_info.items() if k != 'trait_vectors_not_in_corpus'})}")
    print("rubrics: " + ", ".join(f"{r} {rb['name']} v{rb['version']} {rb['sha256'][:12]}" for r, rb in rubrics.items()))
    print(f"cost estimate (calls still to send; {len(done)} answered on record, ${prior.total_cost_usd:.2f} spent):\n"
          f"{est.format()}\n  budget ${args.budget_usd:.2f} for the whole run")
    try:
        cap = confirm_or_abort(est.usd + prior.total_cost_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
    except SystemExit as exc:
        return int(exc.code or 2)

    prompts_text = rendered_prompts_text(ps, rubrics, inputs.corpus, args.models[0])
    if args.dry_run:
        print(prompts_text)
        print("DRY-RUN: nothing sent, nothing written")
        return 0

    dirty = platform_dirty_files()
    if dirty and not args.allow_dirty:
        print(f"REFUSED: uncommitted changes to the platform's files ({len(dirty)}: "
              f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty", file=sys.stderr)
        return 2

    from assistant_axis.plot_metadata import json_metadata
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    if not resuming:
        write_json(out_dir / "pairs.json", json_metadata(ps.to_json(), inputs=provenance_inputs(inputs),
                                                          title=f"M3 overlap test {args.run_id}: calls and pairs",
                                                          script=_rel(Path(__file__)), argv=argv_list))
    (out_dir / "rendered_prompts.md").write_text(prompts_text, encoding="utf-8")
    write_marks(out_dir, inputs, ps, rubrics, args)

    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    usage.merge_from(prior)
    run = json.loads((out_dir / "run.json").read_text()) if resuming and (out_dir / "run.json").exists() else {}
    run.setdefault("sessions", [])
    run.update({"run_id": args.run_id, "git_sha": git_sha(), "argv": argv_list, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": {"paths": list(PLATFORM_PATHS), "dirty": dirty}, "budget_usd": cap,
                "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "models": args.models, "rubrics": args.rubrics, "reference": args.reference, "seed": args.seed,
                "temperature": OT.TEMPERATURE, "max_tokens": OT.MAX_TOKENS, "concurrency": args.concurrency,
                "ask_attempts": OT.ASK_ATTEMPTS, "parser_version": OT.PARSER_VERSION,
                "stop_below": args.stop_below,
                "rubric_versions": {rb["name"]: rb["version"] for rb in rubrics.values()},
                "prompt_sha256": {rb["name"]: rb["sha256"] for rb in rubrics.values()},
                "prompts": {rb["name"]: rb["text"] for rb in rubrics.values()},
                "pair_set": {k: info[k] for k in ("n_calls", "n_pairs", "n_pairs_by_group", "n_calls_by_set")},
                "started_at": run.get("started_at") or utc_now(), "stages": run.get("stages", [])})
    run["sessions"].append({"started_at": utc_now(), "resumed": bool(resuming), "git_sha": git_sha()})

    def save_run():
        usage.write_json(out_dir / "usage.json")
        run["cost_usd"] = round(usage.total_cost_usd, 6)
        run["usage"] = usage.as_dict()
        write_json(out_dir / "run.json", run)
    save_run()

    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    code = 0
    try:
        code = asyncio.run(run_stages(client, rubrics, inputs.corpus, ps, args, usage, out_dir, run, save_run))
    finally:
        run["finished_at"] = utc_now()
        run["exit_code"] = code
        save_run()
        logger.info(usage.log_line())
    if code == 0:
        write_analysis(out_dir, inputs, ps, args, argv_list)
        logger.info("wrote %s", _rel(out_dir / "summary.json"))
    return code


if __name__ == "__main__":
    sys.exit(main())
