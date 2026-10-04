#!/usr/bin/env python3
"""The pre-pilot test of the M3 overlap rubrics (m3_overlap_rubric_draft.md, "The test"; 2026-10-03), and
the overlap rubric arms experiment (coding_plan_overlap_arms.md; 2026-10-04).

    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --dry-run
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 [--budget-usd 15]
        [--models claude-haiku-4-5-20251001 claude-sonnet-5-5 claude-opus-5-5] [--rubrics A B] [--seed 0]
        [--n-targets 100] [--concurrency 8] [--stop-below 0.99] [--resume] [--allow-dirty]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_1
        --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A C D E --passes 2 --budget-usd 20 [--dry-run]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --analyse-only
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --decode-marks

Builds the pair set (``assistant_axis.gapgen.overlap_test.build_pair_set``: about 100 seeded targets with
persona vectors and their 3 nearest traits under the covered setting, plus the labelled pairs between two
corpus traits, grouped as M3 would group them), and sends one call per target to each (rubric, model):
by default rubric A (``rubrics/overlap_concept.md``) and rubric B (``rubrics/overlap_cooccurrence.md``) on
Haiku 4.5, Sonnet 5.5 and Opus 5.5, live, temperature 0 where the model accepts it.  ``--rubrics`` also
takes the arms C (``overlap_six.md``), D (``overlap_relation.md``) and E (``overlap_scope.md``).  The stages
run pass by pass, and within a pass Haiku first, then Sonnet, then Opus (the order of ``--models``), so
that a parse problem shows up on the cheapest model and an interrupted run has pass 1 of every arm first.
A call whose answer does not parse fully is sent once more (every model alike; the first attempt's parse
rate is reported too), and a stage whose parse rate is still below ``--stop-below`` (default 0.99, the
project's alert line) stops the run before the next stage.  ``--resume`` sends again only the calls without
a fully parsed answer.

``--passes N`` (default 1) sends every call N times: pass 1 as every earlier run did, each later pass with
the listed traits in a fresh order (seeded by the run seed, the pass number and the call), so that every
pair is judged once per pass by every (rubric, model) and self-consistency can be measured on all of them.
A record's key is (rubric, model, call, pass); ``--resume`` works per key.

``--baseline-run`` (default ``overlap_test_1``; ``none`` to skip) names an earlier run under ``--out-root``:
a new run's pair set must equal that run's ``pairs.json`` (the run refuses to start if it differs, as
``--resume`` does), and the analysis compares this run's rubric-A pass 1 with that run's rubric-A answers.
The earlier run is only read.

Writes ``data/candidates/overlap_test/<run id>/``: ``pairs.json`` (the calls and pairs, with the
provenance envelope), ``rendered_prompts.md`` (the requests as sent, for three variants: a nearest target,
one whose list holds the target's recorded antonym, one with a single listed trait; for every rubric of
the run, and the later passes' user turns), ``responses.jsonl`` (every request and answer, parsed),
``usage.json`` (cumulative ``MultiModelUsage``, written after every answer), ``run.json``, ``results.jsonl``
(one row per pair, rubric, model and pass), ``summary.json`` (the analysis, with the provenance envelope),
``tables.md``, ``run.log``, and ``marks_key.json``; and Roger's blinded sheet
``reports/trait_gap_generation/m3_overlap_marks.md`` (never overwritten).  ``--decode-marks`` reads his
marks back into ``marks_decoded.json``.

``--dry-run`` builds everything, prints the plan, the estimate and the rendered prompts, and writes and
sends nothing.  The cap (``--budget-usd``, default $15) is enforced by ``cost.GuardedUsage``; an estimate
above it is refused.  A paid run refuses uncommitted changes to the platform's files (``--allow-dirty``),
and refuses to start while another session of the same run is still sending (a lock on its
``responses.jsonl``).
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
from assistant_axis.gapgen import split_rubrics as SR  # noqa: E402
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
#: The run whose pairs a new run must match and whose rubric-A answers arm A's pass 1 is compared with.
DEFAULT_BASELINE_RUN = "overlap_test_1"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True, help="directory name under --out-root")
    ap.add_argument("--out-root", type=Path, default=OUT_ROOT)
    ap.add_argument("--models", nargs="+", default=list(OT.MODELS))
    ap.add_argument("--rubrics", nargs="+", default=list(OT.DEFAULT_RUBRICS), choices=list(OT.RUBRICS),
                    help="A, B (the default) and the arms C, D, E")
    ap.add_argument("--passes", type=int, default=1,
                    help="send every call this many times; passes after the first reshuffle the listed traits "
                         "(default 1)")
    ap.add_argument("--baseline-run", default=DEFAULT_BASELINE_RUN,
                    help="an earlier run under --out-root whose pairs.json this run must match and whose rubric-A "
                         f"answers arm A's pass 1 is compared with (default {DEFAULT_BASELINE_RUN}; 'none' to skip)")
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
    args = ap.parse_args(argv)
    if args.passes < 1:
        ap.error("--passes must be at least 1")
    args.rubrics = list(dict.fromkeys(args.rubrics))
    return args


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return str(p)


def build(args):
    inputs = OT.load_inputs(_REPO_ROOT, metric_config_path=args.metric_config, cache_dir=args.cache_dir,
                            vectors_dir=args.vectors_dir, labelled_path=args.labelled_pairs, dm_path=args.drop_or_merge)
    # the run's rubrics, and rubric A for the marks sheet's scale
    rubrics = OT.load_rubrics(args.rubrics_dir, keys=list(dict.fromkeys(list(args.rubrics) + ["A"])))
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


def rendered_prompts_text(ps, rubrics, corpus, model: str, *, rubric_keys=None, passes: int = 1,
                          seed: int = 0) -> str:
    """The requests of :func:`variant_calls` as the model receives them, for every rubric in
    ``rubric_keys`` (default every loaded one), and with ``passes`` > 1 the later passes' user turns."""
    keys = list(rubrics) if rubric_keys is None else list(rubric_keys)
    v = variant_calls(ps)
    out = ["# Rendered prompts of the overlap test", "",
           "The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the "
           f"user turn), for {len(v)} variants and the rubrics {', '.join(keys)}; settings shown for {model}.  "
           "Within a pass every rubric and model receives the identical user turn.", ""]
    for name, c in v.items():
        pairs = [p for p in ps.pairs if p.call_id == c.call_id]
        out += [f"## Variant: {name} ({c.call_id})", "",
                "Listed (id: stem, group, recorded opposite): " + "; ".join(
                    f"{p.id}: {p.listed}, {p.group}{', opposite' if OT.is_antonym_pair(p) else ''}"
                    for p in sorted(pairs, key=lambda p: p.id)), ""]
        for r in keys:
            out += ["```text", OT.rendered_prompt(c, corpus, rubric=r, rubric_text=rubrics[r]["text"], model=model)
                    .rstrip("\n"), "```", ""]
    for p in range(2, passes + 1):
        same = sum(OT.listed_order(c, OT.pass_order_seed(seed, p, c.call_id)) == list(c.listed) for c in ps.calls)
        out += [f"## Pass {p}: the same calls, the listed traits in a fresh order", "",
                f"The system prompt is each rubric's, as in pass 1; only the user turn's order (and so the ids) "
                f"changes.  {same} of {len(ps.calls)} calls happen to keep pass 1's order (every call of one "
                "trait does).  The variants' user turns in this pass:", ""]
        for name, c in v.items():
            seed_p = OT.pass_order_seed(seed, p, c.call_id)
            out += [f"### {name} ({c.call_id}), pass {p}: " + ", ".join(OT.listed_order(c, seed_p)), "",
                    "```text", OT.render_user(c, corpus, order_seed=seed_p), "```", ""]
    return "\n".join(out)


def baseline_dir(args):
    """The baseline run's directory, or ``None`` when there is none to read (``none``, or this run)."""
    b = (args.baseline_run or "").strip()
    if not b or b.lower() == "none" or b == args.run_id:
        return None
    check_id(b, "baseline_run")
    return Path(args.out_root) / b


def load_baseline(args, ps, models):
    """The baseline run's rubric-A answers per model (its pass 1), keyed by this run's pair ids, when the
    run exists and its calls are this run's; else ``None`` (with a warning when it exists but differs)."""
    d = baseline_dir(args)
    if d is None or not (d / "pairs.json").exists() or not (d / "responses.jsonl").exists():
        return None
    theirs = OT.PairSet.from_json(json.loads((d / "pairs.json").read_text()))
    if not OT.same_calls(theirs, ps):
        logger.warning("baseline run %s sends other calls than this run: not compared", args.baseline_run)
        return None
    records = OT.read_records(d / "responses.jsonl")
    ans = OT.collect_answers(ps, records, pass_no=1)
    return {"run_id": args.baseline_run, "path": _rel(d / "responses.jsonl"),
            "answers": {m: ans[("A", m)] for m in models if ans.get(("A", m))}}


def provenance_inputs(inputs, *, responses: Path = None, baseline_responses: Path = None):
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
             current_files_input(dep_key="rubrics", paths=[RUBRICS_DIR / f for f in SR.OVERLAP_FILES.values()]
                                 + [RUBRICS_DIR / "versions.json"])]
    if inputs.paths["persona_cache"].exists():
        specs.append(current_file_input(dep_key="persona_cache", path=inputs.paths["persona_cache"],
                                        extras={"slot": str(inputs.persona_info["slot"]),
                                                "layer": str(inputs.persona_info["layer"]),
                                                "shear_applied": str(inputs.persona_info["shear_applied"])}))
    if responses is not None and Path(responses).exists():
        specs.append(current_file_input(dep_key="responses", path=responses))
    if baseline_responses is not None and Path(baseline_responses).exists():
        specs.append(current_file_input(dep_key="baseline_responses", path=baseline_responses))
    return specs


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_analysis(out_dir: Path, inputs, ps, args, argv) -> dict:
    from assistant_axis.plot_metadata import json_metadata
    records = OT.read_records(out_dir / "responses.jsonl")
    passes = OT.record_passes(records) or [1]
    by_pass = {p: OT.collect_answers(ps, records, pass_no=p) for p in passes}
    rows = [row for p in passes for row in OT.results_rows(ps, by_pass[p], pass_no=p)]
    (out_dir / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    models = [m for m in args.models if any((r, m) in by_pass[p] for p in passes for r in OT.RUBRICS)]
    first = {p: OT.first_attempt_parse(ps, records, pass_no=p) for p in passes}
    summary = OT.analyse(ps, by_pass.get(1, {}), models=models, reference=args.reference, n_boot=args.n_boot,
                         seed=args.seed, first_parse=first.get(1))
    baseline = load_baseline(args, ps, models)
    summary["arms"] = OT.analyse_arms(ps, by_pass, models=models, reference=args.reference, seed=args.seed,
                                      first_parse_by_pass=first, baseline=baseline)
    if baseline:
        summary["arms"]["baseline"]["path"] = baseline["path"]
    usage_path = out_dir / "usage.json"
    if usage_path.exists():
        summary["usage"] = json.loads(usage_path.read_text())
    summary["pair_set_info"] = ps.info
    bdir = baseline_dir(args)
    env = json_metadata(summary, inputs=provenance_inputs(inputs, responses=out_dir / "responses.jsonl",
                                                          baseline_responses=(bdir / "responses.jsonl") if baseline
                                                          else None),
                        title=f"M3 overlap rubric test {args.run_id}", script=_rel(Path(__file__)), argv=argv)
    write_json(out_dir / "summary.json", env)
    (out_dir / "tables.md").write_text(OT.summary_markdown(summary, ps, inputs.corpus), encoding="utf-8")
    return summary


def write_marks(out_dir: Path, inputs, ps, rubrics, args) -> None:
    key_path = out_dir / "marks_key.json"
    if args.marks_sheet.exists():
        # Never overwrite a sheet: it may hold Roger's marks, and it may be another run's
        # (overlap_test_2 rewrote overlap_test_1's sheet when this checked only its own key).
        logger.info("marks sheet %s exists; kept as written%s", _rel(args.marks_sheet),
                    "" if key_path.exists() else " (another run's; no marks key written for this run; pass "
                    "--marks-sheet with a new path for a sheet of its own)")
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
                              concurrency=args.concurrency, seed=args.seed, usage_path=out_dir / "usage.json")
    for pass_no in range(1, args.passes + 1):
        for model in args.models:
            for r in args.rubrics:
                t0 = time.time()
                logger.info("stage: rubric %s (%s) on %s, pass %d, %d calls", r, OT.RUBRICS[r]["name"], model,
                            pass_no, len(ps.calls))
                res = await runner.run_stage(r, model, ps.calls, pass_no=pass_no)
                stage = {"rubric": r, "model": model, "pass": pass_no, "n_calls": res.n_calls, "n_sent": res.n_sent,
                         "n_skipped": res.n_skipped, "n_reasked": res.n_reasked, "n_pairs": res.n_pairs,
                         "n_ok": res.n_ok, "n_ok_first_attempt": res.n_ok_first,
                         "parse_rate": None if res.parse_rate is None else round(res.parse_rate, 4),
                         "budget_exceeded": res.budget_exceeded, "seconds": round(time.time() - t0, 1),
                         "cost_usd_total_after": round(usage.total_cost_usd, 4), "finished_at": utc_now()}
                run["stages"].append(stage)
                save_run()
                logger.info("stage done: %s; %s", json.dumps(stage), usage.log_line())
                if res.budget_exceeded:
                    logger.error("budget cap $%.2f reached during rubric %s on %s, pass %d: stopping", args.budget_usd,
                                 r, model, pass_no)
                    run["stopped"] = f"budget cap reached at rubric {r} on {model}, pass {pass_no}"
                    return 2
                if res.parse_rate is not None and res.parse_rate < args.stop_below:
                    logger.error("*** parse rate %.4f below %.2f for rubric %s on %s, pass %d: stopping before the "
                                 "next stage", res.parse_rate, args.stop_below, r, model, pass_no)
                    run["stopped"] = (f"parse rate {res.parse_rate:.4f} below {args.stop_below} at rubric {r} on "
                                      f"{model}, pass {pass_no}")
                    return 3
    return 0


def main(argv=None) -> int:
    args = parse_args(argv)
    argv_list = sys.argv[1:] if argv is None else list(argv)
    configure_logging()
    check_id(args.run_id, "run_id")
    out_dir = Path(args.out_root) / args.run_id
    unknown = [m for m in args.models if m not in OT.KNOWN_MODELS]
    if unknown:
        print(f"unknown model(s) {unknown}: this test knows {list(OT.KNOWN_MODELS)}", file=sys.stderr)
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
        records = OT.read_records(out_dir / "responses.jsonl")
        done = OT.done_keys(records)
        prior = MultiModelUsage.load_or_create(out_dir / "usage.json")
        recorded = OT.PairSet.from_json(json.loads((out_dir / "pairs.json").read_text()))
        if not OT.same_calls(recorded, ps):
            print("REFUSED: the pair set built now differs from the recorded pairs.json (inputs or seed changed)",
                  file=sys.stderr)
            return 2
        shown = OT.usage_from_records(records)
        if shown.n_calls != prior.n_calls or abs(shown.total_cost_usd - prior.total_cost_usd) > 0.005:
            logger.warning("usage.json records %d calls ($%.4f) but responses.jsonl shows %d answered requests "
                           "($%.4f)", prior.n_calls, prior.total_cost_usd, shown.n_calls, shown.total_cost_usd)
    elif out_dir.exists() and (out_dir / "responses.jsonl").exists():
        print(f"{_rel(out_dir)} already has responses: pass --resume to continue it, or choose a new --run-id",
              file=sys.stderr)
        return 1
    bdir = baseline_dir(args)
    if bdir is not None and (bdir / "pairs.json").exists():
        theirs = OT.PairSet.from_json(json.loads((bdir / "pairs.json").read_text()))
        if not OT.same_calls(theirs, ps):
            print(f"REFUSED: the pair set built now differs from {args.baseline_run}'s pairs.json (inputs or seed "
                  "changed); pass --baseline-run none to run without that comparison", file=sys.stderr)
            return 2
        print(f"pair set: the same calls as {args.baseline_run} ({len(ps.calls)} calls, {len(ps.pairs)} pairs)")
    elif bdir is not None:
        logger.warning("baseline run %s has no pairs.json under %s: not compared", args.baseline_run,
                       _rel(args.out_root))

    est = OT.Estimate()
    for p in range(1, args.passes + 1):
        for m in args.models:
            for r in args.rubrics:
                cs = [c for c in ps.calls if (r, m, c.call_id, p) not in done]
                est.lines.extend(OT.estimate(cs, inputs.corpus, rubrics, [m], [r],
                                             pass_no=p if args.passes > 1 else None).lines)
    info = ps.info
    print(f"M3 overlap test {args.run_id}: {info['n_calls']} calls ({info['n_calls_by_set']}), {info['n_pairs']} pairs "
          f"by group {info['n_pairs_by_group']}; {info['n_pairs_with_persona_cos']} pairs with a persona-space cosine; "
          f"list sizes {info['list_sizes']}; {info['nearest_recorded_antonyms']} nearest pairs are recorded clean "
          f"pairs; {info['n_unordered_pairs_twice']} unordered pairs judged in two calls")
    print(f"labelled: {json.dumps(info['labelled'])}")
    print(f"embedding: {json.dumps(inputs.settings)}; persona: {json.dumps({k: v for k, v in inputs.persona_info.items() if k != 'trait_vectors_not_in_corpus'})}")
    print("rubrics: " + ", ".join(f"{r} {rubrics[r]['name']} v{rubrics[r]['version']} {rubrics[r]['sha256'][:12]}"
                                  for r in args.rubrics) + f"; passes {args.passes}")
    print(f"cost estimate (calls still to send; {len(done)} answered on record, ${prior.total_cost_usd:.2f} spent):\n"
          f"{est.format()}\n  budget ${args.budget_usd:.2f} for the whole run")
    try:
        cap = confirm_or_abort(est.usd + prior.total_cost_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
    except SystemExit as exc:
        return int(exc.code or 2)

    prompts_text = rendered_prompts_text(ps, rubrics, inputs.corpus, args.models[0], rubric_keys=args.rubrics,
                                         passes=args.passes, seed=args.seed)
    if args.dry_run:
        print(prompts_text)
        print("DRY-RUN: nothing sent, nothing written")
        return 0

    dirty = platform_dirty_files()
    if dirty and not args.allow_dirty:
        print(f"REFUSED: uncommitted changes to the platform's files ({len(dirty)}: "
              f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty", file=sys.stderr)
        return 2

    try:
        lock = OT.acquire_session_lock(out_dir)
    except OT.SessionBusy as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 4
    try:
        return _live(args, argv_list, out_dir, inputs, rubrics, ps, est=est, cap=cap, dirty=dirty, resuming=resuming,
                     prior=prior, prompts_text=prompts_text)
    finally:
        lock.close()


def _live(args, argv_list, out_dir: Path, inputs, rubrics, ps, *, est, cap, dirty, resuming, prior,
          prompts_text) -> int:
    """The paid part of :func:`main`, run under the session lock."""
    from assistant_axis.plot_metadata import json_metadata
    info = ps.info
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
    sent = {r: rubrics[r] for r in args.rubrics}
    run.update({"run_id": args.run_id, "git_sha": git_sha(), "argv": argv_list, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": {"paths": list(PLATFORM_PATHS), "dirty": dirty}, "budget_usd": cap,
                "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "models": args.models, "rubrics": args.rubrics, "passes": args.passes,
                "baseline_run": args.baseline_run, "reference": args.reference, "seed": args.seed,
                "temperature": OT.TEMPERATURE, "max_tokens": OT.MAX_TOKENS, "concurrency": args.concurrency,
                "ask_attempts": OT.ASK_ATTEMPTS, "parser_version": OT.PARSER_VERSION,
                "stop_below": args.stop_below,
                "rubric_versions": {rb["name"]: rb["version"] for rb in sent.values()},
                "prompt_sha256": {rb["name"]: rb["sha256"] for rb in sent.values()},
                "prompts": {rb["name"]: rb["text"] for rb in sent.values()},
                "pair_set": {k: info[k] for k in ("n_calls", "n_pairs", "n_pairs_by_group", "n_calls_by_set")},
                "started_at": run.get("started_at") or utc_now(), "stages": run.get("stages", [])})
    run["sessions"].append({"started_at": utc_now(), "resumed": bool(resuming), "git_sha": git_sha(),
                            "argv": argv_list})

    def save_run():
        OT.write_usage(usage, out_dir / "usage.json")
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
