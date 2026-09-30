#!/usr/bin/env python3
"""Read labels bare ("You are <label>.") and compare with their intended meaning.

    uv run python data_analysis/gap_generation/plain_reading.py --batch-id B \\
        (--pairs F | --corpus | --corpus-stems S [S ...]) [--limit N] \\
        [--reading-model claude-haiku-4-5-20251001] [--compare-model claude-sonnet-5-5] \\
        [--reuse-readings DIR] [--batch-size 20] [--budget-usd 1.0] \\
        [--confirm-expensive --confirmed-by WHO] [--allow-dirty] [--dry-run] [--overwrite]

The library is ``assistant_axis.gapgen.plain_reading`` (open point D of
decisions_m1.md, case 3).  Each distinct label is read once, in a call that
carries only the persona prompt; each row is then compared with its intended
meaning (``same`` / ``related`` / ``different``; ``different`` flags
``overshadowed``).  Nothing here rejects a word or writes the registry.

Inputs:

* ``--pairs F``: JSONL rows ``{"label", "intended", "key"?, "expected"?, ...}``;
  ``expected`` (one of the three answers) makes the summary carry a confusion
  table and the list of wrong rows.  Extra keys are kept in ``meta``.
* ``--corpus`` / ``--corpus-stems``: corpus traits read with their own
  descriptions (read only), expected ``same``: the comparison over every
  existing label, which needs Roger's go (see "M1 as built" for its cost).
  It raises no flag (round 4): ``listing.md`` lists every label with both
  texts, ``different`` first, then ``related`` by confidence.
* ``--measurement``: record the run as a measurement (run.json
  ``"measurement": true``), so ``filter.development_seen`` does not count its
  rows as seen in development; a corpus run always is one (round 5).
* ``--reuse-readings DIR``: take the plain readings of an earlier run's
  ``results.jsonl`` instead of calling again (for comparing two comparison
  models on identical readings).

Outputs in ``data/candidates/plain_reading/<batch_id>/``: ``responses.jsonl``,
``results.jsonl``, ``summary.json`` (``json_metadata`` envelope),
``usage.json`` (always) and ``run.json`` (args, estimate, cap, git sha,
``dirty_check``, versions and prompt hashes).  Cost gate, dirty-tree refusal
and budget stop as in ``traithood_filter.py``: ``--budget-usd`` is the cap and
an estimate over it is refused.
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
from assistant_axis.gapgen import plain_reading as pr  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError  # noqa: E402

logger = logging.getLogger("plain_reading")

CHARS_PER_TOKEN = 3.6
READ_IN, READ_OUT = 60, 45
CMP_IN_PER_ROW, CMP_OUT_PER_ROW = 110, 90
RETRY_MARGIN = 1.10


def read_pairs(path: Path) -> list[pr.ReadingItem]:
    items, seen = [], set()
    for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        key = row.get("key") or f"{row['label']}#{i}"
        if key in seen:
            raise SystemExit(f"{path}:{i}: duplicate key {key}")
        seen.add(key)
        meta = {k: v for k, v in row.items() if k not in ("label", "intended", "key")}
        items.append(pr.ReadingItem(key=key, label=row["label"], intended=row["intended"], meta=meta))
    return items


def reuse_from(d: Path) -> dict[str, str]:
    out = {}
    for line in (Path(d) / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("reading"):
                out[r["label"]] = r["reading"]
    return out


def build_estimate(items: list[pr.ReadingItem], args, n_reused: int) -> Estimate:
    est = Estimate()
    n_labels = len({it.label for it in items}) - n_reused
    est.add("plain reading", args.reading_model, max(0, n_labels), READ_IN, READ_OUT)
    if items:
        sys_tok = int(len(pr.COMPARISON_PROMPT) / CHARS_PER_TOKEN)
        per = min(args.batch_size, len(items))
        est.add("comparison", args.compare_model, math.ceil(RETRY_MARGIN * len(items) / args.batch_size),
                sys_tok + CMP_IN_PER_ROW * per, CMP_OUT_PER_ROW * per)
    return est


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch-id", required=True)
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--pairs", type=Path, help="JSONL of {label, intended, key?, expected?}")
    sel.add_argument("--corpus", action="store_true", help="every corpus trait with its own description")
    sel.add_argument("--corpus-stems", nargs="+", help="these corpus traits with their own descriptions")
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (read only)")
    ap.add_argument("--out-root", type=Path, default=None,
                    help="candidates dir holding plain_reading/<batch_id>/ (default data/candidates)")
    ap.add_argument("--reading-model", default=pr.DEFAULT_READING_MODEL)
    # claude-sonnet-5-5 since 2026-09-29 (Roger: "I'm inclined to move it"; coding_plan_split.md
    # section 1); the library default, used by recorded runs, is unchanged
    ap.add_argument("--compare-model", default="claude-sonnet-5-5",
                    help="comparison model (default claude-sonnet-5-5; recorded runs used claude-sonnet-4-6)")
    ap.add_argument("--reuse-readings", type=Path, help="an earlier run dir whose readings to reuse")
    ap.add_argument("--batch-size", type=int, default=pr.DEFAULT_BATCH_SIZE)
    ap.add_argument("--limit", type=int, help="first N rows only")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--budget-usd", type=float, default=1.0,
                    help="hard cap (default 1.0); an estimate over it is refused: type a larger budget to spend "
                         "more")
    ap.add_argument("--confirm-expensive", action="store_true",
                    help="part of the over-$20 confirmation, valid only with --confirmed-by; it never raises the "
                         "cap")
    ap.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    ap.add_argument("--measurement", action="store_true",
                    help="record the run as a measurement, not development (run.json \"measurement\": true); "
                         "--corpus and --corpus-stems runs always are")
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
    if args.pairs:
        items = read_pairs(args.pairs)
    else:
        items = pr.corpus_pairs(args.data_dir, args.corpus_stems)
    if args.limit:
        items = items[:args.limit]
    if not items:
        print("nothing to read", file=sys.stderr)
        return 0
    # The comparison across the corpus raises no flag; it lists every label (round 4)
    corpus_mode = not args.pairs
    reuse = reuse_from(args.reuse_readings) if args.reuse_readings else {}
    n_reused = len({it.label for it in items} & set(reuse))
    est = build_estimate(items, args, n_reused)
    print(f"plan: {json.dumps({'n_rows': len(items), 'n_labels': len({it.label for it in items}), 'n_reused': n_reused})}")
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
    out_dir = paths.plain_reading_dir(args.batch_id, candidates_dir=args.out_root)
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/; prompt sha256: {json.dumps(pr.PROMPT_SHA256)}")
        print(f"--- reading prompt ---\n{pr.build_reading_prompt(items[0].label)}")
        payload = [{"id": i + 1, "label": it.label, "plain_reading": "<reading>", "intended_meaning": it.intended}
                   for i, it in enumerate(items[:3])]
        print(f"--- comparison prompt (first rows) ---\n{pr.build_compare_prompt(payload)}")
        return 0
    if refused:
        return 2
    if out_dir.exists():
        if not args.overwrite:
            print(f"{out_dir} exists; choose a new --batch-id or pass --overwrite", file=sys.stderr)
            return 1
        bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
        shutil.move(str(out_dir), str(bak))
    out_dir.mkdir(parents=True)
    run_meta = {"batch_id": args.batch_id, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv,
                "n_rows": len(items), "n_reused_readings": n_reused, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by, "reading_model": args.reading_model,
                "compare_model": args.compare_model,
                "versions": {"plain_reading": pr.READING_VERSION, "comparison": pr.COMPARISON_VERSION},
                "prompt_sha256": dict(pr.PROMPT_SHA256),
                # a corpus comparison is always a measurement (filter.development_seen leaves it out)
                "measurement": bool(args.measurement or args.corpus or args.corpus_stems),
                "started_at": utc_now()}
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    from dotenv import load_dotenv
    import anthropic
    load_dotenv(_REPO_ROOT / ".env")
    client = anthropic.AsyncAnthropic(max_retries=0)
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    runner = pr.PlainReadingRunner(client=client, batch_id=args.batch_id, reading_model=args.reading_model,
                                   compare_model=args.compare_model, usage=usage, batch_size=args.batch_size,
                                   concurrency=args.concurrency, responses_path=out_dir / "responses.jsonl",
                                   reuse_readings=reuse, flag=not corpus_mode)
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
        usage.write_json(out_dir / "usage.json")
        write_jsonl(runner.responses, out_dir / "responses.jsonl")
        results = [runner.results[it.key] for it in items if it.key in runner.results]
        write_jsonl([r.as_dict() for r in results], out_dir / "results.jsonl")
        runner.warn_parse_rate(logger)
        summary = pr.summarize(results, stats=runner.stats, usage=usage)
        if corpus_mode:
            atomic_write_text(pr.corpus_listing(results), out_dir / "listing.md")
        summary.update({"flags_raised": not corpus_mode, "batch_id": args.batch_id, "stopped_by_budget": status == 2,
                        "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                        "reading_model": args.reading_model, "compare_model": args.compare_model})
        from assistant_axis.plot_metadata import json_metadata
        env = json_metadata(summary, title=f"plain_reading {args.batch_id}")
        atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "summary.json")
        run_meta.update({"finished_at": utc_now(), "cost_usd": round(usage.total_cost_usd, 4),
                         "stopped_by_error": summary["stopped_by_error"]})
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        print(usage.log_line())
        print(json.dumps({k: summary.get(k) for k in ("n", "n_compared", "relations", "overshadowed", "confusion",
                                                     "accuracy", "reading_parse_rate", "compare_parse_rate",
                                                     "cost_usd")}, ensure_ascii=False))
    return status


if __name__ == "__main__":
    sys.exit(main())
