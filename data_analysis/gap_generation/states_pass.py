#!/usr/bin/env python3
"""Run the states pass (``assistant_axis.gapgen.states_pass``).

    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode queue \\
        (--holding-states [--rejudge] | --filter-results F [F ...]) [--limit N]
    uv run python data_analysis/gap_generation/states_pass.py --batch-id B --mode corpus \\
        (--stems S [S ...] | --filter-results F [F ...]) [--limit N]
    common: [--model claude-haiku-5-5] [--batch-size 20] [--budget-usd 1.0]
            [--confirm-expensive --confirmed-by WHO] [--allow-dirty] [--dry-run] [--overwrite]

``--model`` defaults to Haiku 5.5 since 2026-10-08 (Haiku 4.5,
``claude-haiku-4-5-20251001``, before; still selectable); every block names its model.

``--mode queue`` asks, for each word the classifier tagged ``state``, Roger's
three questions (decision 12): is a habitual predisposition plausible, is the
state's name still a good name for it (else a suggested name), and a draft
gloss of the predisposition.  ``--holding-states`` takes the registry rows on
the ``states`` holding list that have no ``states_pass`` block yet (every one
with ``--rejudge``) and writes the block into the registry;
``--filter-results`` takes the rows of filter ``results.jsonl`` files tagged
``state`` and never touches the registry.

``--mode corpus`` checks existing corpus labels that the filter tagged
``state``: given the label and its corpus description, does the description
describe a habitual predisposition or a momentary state?  ``--stems`` names
them directly; ``--filter-results`` takes the ``existing``-stratum rows tagged
``state``.  It reads only the corpus trait files (``<data-dir>/traits/
instructions/<stem>.json``) and writes only its own run directory; its
``summary.json`` lists the exceptions (descriptions read as momentary) for
Roger.  Nothing acts on those.

Outputs in ``data/candidates/states_pass/<batch_id>/``: ``responses.jsonl``,
``results.jsonl``, ``summary.json`` (``json_metadata`` envelope),
``usage.json`` (always) and ``run.json`` (args, estimate, cap, git sha,
``dirty_check``, rubric version and prompt hash).  The cost gate, the
dirty-tree refusal and the budget stop are the filter's
(``traithood_filter.py``): ``--budget-usd`` is the cap and an estimate over
it is refused.
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
from assistant_axis.gapgen import states_pass as sp  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import Registry, holding_list, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError  # noqa: E402

logger = logging.getLogger("states_pass")

CHARS_PER_TOKEN = 3.6
IN_TOK_PER_ITEM = 60       # label plus a one-sentence description
OUT_TOK_PER_ITEM = {"queue": 110, "corpus": 50}
RETRY_MARGIN = 1.10


def _read_jsonl(paths_: list[Path]) -> list[dict]:
    rows = []
    for p in paths_:
        rows += [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows


def select_items(args) -> tuple[list[sp.StatesItem], Optional[Registry], dict]:
    """Items to judge, the registry to write (queue mode from the registry
    only) and a map of skipped names (corpus mode)."""
    skipped: dict[str, str] = {}
    reg = None
    if args.mode == "queue":
        if args.stems:
            raise SystemExit("--stems applies to --mode corpus only")
        if args.holding_states:
            reg = Registry(args.registry)
            recs = holding_list("states", registry=reg)
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
    if args.limit:
        uniq = uniq[:args.limit]
    return uniq, reg, skipped


def build_estimate(items: list[sp.StatesItem], args) -> Estimate:
    est = Estimate()
    n = len(items)
    if n:
        sys_tok = int(len(sp.PROMPTS[args.mode]) / CHARS_PER_TOKEN)
        per = min(args.batch_size, n)
        est.add(f"states pass ({args.mode})", args.model, math.ceil(RETRY_MARGIN * n / args.batch_size),
                sys_tok + IN_TOK_PER_ITEM * per, OUT_TOK_PER_ITEM[args.mode] * per)
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
                    help="candidates dir holding states_pass/<batch_id>/ (default data/candidates)")
    ap.add_argument("--model", default=sp.DEFAULT_MODEL)
    ap.add_argument("--batch-size", type=int, default=sp.DEFAULT_BATCH_SIZE)
    ap.add_argument("--limit", type=int, help="first N rows only")
    ap.add_argument("--concurrency", type=int, default=4)
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


def main(argv=None) -> int:
    configure_logging()  # every line carries its UTC time (runs.LOG_FORMAT)
    args = build_parser().parse_args(argv)
    paths.check_id(args.batch_id, "batch_id")
    items, reg, skipped = select_items(args)
    for name, why in skipped.items():
        print(f"SKIPPED {name}: {why}", file=sys.stderr)
    if not items:
        print("nothing to judge", file=sys.stderr)
        return 0
    est = build_estimate(items, args)
    print(f"plan: {json.dumps({'mode': args.mode, 'n_rows': len(items), 'registry': bool(reg)})}")
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
    out_dir = paths.states_pass_dir(args.batch_id, candidates_dir=args.out_root)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/ and {'the registry ' + str(args.registry) if reg else 'no registry'}")
        print(f"system prompt: {len(sp.PROMPTS[args.mode])} chars (states rubric v{sp.RUBRIC_VERSIONS[args.mode]}); "
              f"prompt sha256: {sp.PROMPT_SHA256[args.mode]}")
        payload = [{"id": i + 1, "label": it.label, "text": it.text} for i, it in enumerate(items[:args.batch_size])]
        print(f"--- prompt 1 ---\n{sp.build_batch_prompt(payload, args.mode)}")
        return 0
    if refused:
        return 2
    if out_dir.exists():
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id or pass --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
        print(f"moved the old batch to {bak}", file=sys.stderr)
    out_dir.mkdir(parents=True)
    run_meta = {"batch_id": args.batch_id, "mode": args.mode, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv,
                "n_rows": len(items), "skipped": skipped, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by, "model": args.model,
                "rubric_version": sp.RUBRIC_VERSIONS[args.mode], "prompt_sha256": sp.PROMPT_SHA256[args.mode],
                "started_at": utc_now()}
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    runner = sp.StatesPassRunner(client=client, batch_id=args.batch_id, mode=args.mode, model=args.model,
                                 usage=usage, batch_size=args.batch_size, concurrency=args.concurrency,
                                 responses_path=out_dir / "responses.jsonl")
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
        _finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error)
    return status


def _finalize(args, items, reg, runner, usage, run_meta, out_dir, status, error) -> None:
    usage.write_json(out_dir / "usage.json")
    write_jsonl(runner.responses, out_dir / "responses.jsonl")
    results = [runner.results[it.key] for it in items if it.key in runner.results]
    write_jsonl([r.as_dict() for r in results], out_dir / "results.jsonl")
    runner.warn_parse_rate(logger)
    summary = sp.summarize(results, mode=args.mode, stats=runner.stats, usage=usage)
    summary.update({"batch_id": args.batch_id, "stopped_by_budget": status == 2,
                    "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                    "model": args.model})
    from assistant_axis.plot_metadata import json_metadata
    env = json_metadata(summary, title=f"states_pass {args.batch_id}")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "summary.json")
    if reg is not None:
        done = {r.key: {"states_pass": r.block} for r in results if r.block is not None}
        if done:
            reg.update_many(done, merge_blocks=False)
        print(f"registry: {len(done)} rows updated")
    run_meta["finished_at"] = utc_now()
    run_meta["cost_usd"] = round(usage.total_cost_usd, 4)
    run_meta["stopped_by_error"] = summary["stopped_by_error"]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    print(usage.log_line())
    keys = ("n", "n_judged", "parse_rate", "cost_usd") + (("plausible", "renamed") if args.mode == "queue"
                                                           else ("exceptions",))
    print(json.dumps({k: summary[k] for k in keys}, ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())
