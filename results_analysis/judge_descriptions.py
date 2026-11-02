#!/usr/bin/env python3
"""Judge axes from the entities' descriptions by the settled method.

The method, from the judge-tier evaluation of November 2026 (reports/judge_pareto/judge_tier_update_2026-11-01.md;
Roger, 2026-11-02): the batched percentile rubric (b10, the judge places each entity by percentile among all of
them on the axis), 20 entities per call, two passes in independent random orders, no reasoning, each judge's
passes averaged, and the judges blended by the mean of their scores.  On the 30 development axes, slot 6, layer
25, raw (rho against the activation projections, cost per axis at list price; 12 of 12 projection variants on the
frontier unless noted):

    gpt-6-luna alone                      0.680   $0.019    the cheap end
    gpt-5.6-luna alone                    0.704   $0.042
    gpt-5.6-luna + claude-haiku-5-5       0.716   $0.084    the default
    the same + gemini-3.1-flash-lite      0.720   $0.152    +0.004 [-0.001, +0.010], frontier in 9 of 12

Reasoning adds nothing to any of them, a third pass adds about 0.009 for half as much again, and N=5 and N=7 are
never on a judge's frontier.  The defaults below are that decision: change them here, in one place.

Each pass is a cell of judge_tier_cost_eval.py, <axis>_tier_eval/<judge>@b10n<N>s<seed>/, whose every answer is
saved as it arrives, so a stopped or failed run is simply run again.  Then each judge's passes are averaged into
<judge>@b10n<N>x<passes>, and the judges into <judge>+<judge>@b10n<N>x<passes>.  Projections come from
<experiments_dir>/<axis>/gpt/projections.json; for new data write them with

    uv run python results_analysis/axis_judge_correlation.py --projections_only --pair POS NEG --pair_type traits \\
        --data_dir DATA --output_dir <experiments_dir>/POS_vs_NEG/gpt

Check the cost first (--dry_run), then, for example:

    uv run python results_analysis/judge_descriptions.py --axes_file scripts/tier_eval_axes.tsv --budget_usd 20

Exit status: 0 done, 1 a pass failed or a source was refused for averaging, and otherwise the failing pass's own
status (judge_tier_cost_eval.py): 2 a budget stop, 3 a stall, 4 calls left unanswered: run again.
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from assistant_axis.judge import provider_for_model  # noqa: E402
from results_analysis import judge_tier_average as avg  # noqa: E402
from results_analysis import judge_tier_cost_eval as ev  # noqa: E402
from results_analysis.judge_tier_rubrics import DEFAULT_NAME_FORMAT, NAME_FORMATS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

#: The settled method (Roger, 2026-11-02).
DESCRIPTION_RUBRIC = "b10"
DESCRIPTION_ENTITIES_PER_CALL = 20
DESCRIPTION_PASSES = 2
DESCRIPTION_JUDGES = ("gpt-5.6-luna", "claude-haiku-5-5")
#: Supported and measured, not in the default: pass them as --judge_model.  Gemini 3.1 Flash-Lite as a third
#: judge, GPT-6 Luna alone for the cheap end.
OPTIONAL_JUDGES = ("gemini-3.1-flash-lite", "gpt-6-luna")
#: The reply cap per entity.  No reply reached these in the evaluation; Haiku 5.5 writes about twice as much.
MAX_TOKENS_PER_ENTITY = 60
MAX_TOKENS_PER_ENTITY_BY_PROVIDER = {"anthropic": 150}
FIRST_SEED = 1
#: Judges run side by side and a judge's passes one after another, so that at most this many processes hit the
#: providers at once (eight Flex processes dropped every connection on 2026-11-01; four are fine).
MAX_CONCURRENT_JUDGES = 4

TOOL = Path(__file__).with_name("judge_tier_cost_eval.py")


def max_tokens_for(model: str, entities_per_call: int) -> int:
    return entities_per_call * MAX_TOKENS_PER_ENTITY_BY_PROVIDER.get(provider_for_model(model), MAX_TOKENS_PER_ENTITY)


def pass_label(entities_per_call: int, seed: int) -> str:
    return f"@{DESCRIPTION_RUBRIC}n{entities_per_call}s{seed}"


def averaged_label(entities_per_call: int, passes: int) -> str:
    return f"@{DESCRIPTION_RUBRIC}n{entities_per_call}x{passes}"


def pass_argv(args: argparse.Namespace, model: str, seed: int) -> List[str]:
    """The tool's arguments for one judge's one pass."""
    argv = ["--judge_model", model, "--rubric", DESCRIPTION_RUBRIC, "--entities_per_call", str(args.entities_per_call),
            "--shuffle_seed", str(seed), "--cell_label", pass_label(args.entities_per_call, seed),
            "--max_tokens", str(max_tokens_for(model, args.entities_per_call)), "--experiments_dir", args.experiments_dir,
            "--instructions_dir", args.instructions_dir, "--name_format", args.name_format, "--transport", args.transport]
    if args.axes_file:
        argv += ["--axes_file", args.axes_file]
    else:
        pos, neg = args.pair
        axis = f"{pos}_vs_{neg}"
        argv += ["--pair", pos, neg, "--pair_type", args.pair_type,
                 "--projections_file", str(Path(args.experiments_dir) / axis / "gpt" / "projections.json"),
                 "--output_dir", str(Path(args.experiments_dir) / f"{axis}{ev.TIER_EVAL_SUFFIX}")]
    for flag, value in (("--budget_usd", args.budget_usd), ("--limit", args.limit),
                        ("--requests_per_second", args.requests_per_second), ("--max_in_flight", args.max_in_flight)):
        if value is not None:
            argv += [flag, str(value)]
    if args.dry_run:
        argv.append("--dry_run")
    return argv


def run_tool(argv: Sequence[str]) -> int:
    """One pass, as its own process: the tool keeps a run's settings in module state, and restarts itself after a
    stall (os.execv)."""
    return subprocess.run([sys.executable, str(TOOL), *argv], check=False).returncode


def run_judge(args: argparse.Namespace, model: str) -> int:
    """A judge's passes, one after another; the first failure ends them."""
    for seed in range(args.first_seed, args.first_seed + args.passes):
        code = run_tool(pass_argv(args, model, seed))
        if code:
            logger.error(f"{model}{pass_label(args.entities_per_call, seed)}: exit status {code}")
            return code
    return 0


def jobs_of(args: argparse.Namespace) -> List["ev.AxisJob"]:
    E = Path(args.experiments_dir)
    if args.axes_file:
        return ev.jobs_from_axes_file(Path(args.axes_file), E)
    pos, neg = args.pair
    axis = f"{pos}_vs_{neg}"
    return [ev.AxisJob(axis, pos, neg, args.pair_type, E / axis / "gpt" / "projections.json",
                       E / f"{axis}{ev.TIER_EVAL_SUFFIX}")]


def average_all(args: argparse.Namespace, models: Sequence[str]) -> List[str]:
    """Each judge's passes into one cell, and the judges into a blend.  Returns the refusals."""
    N, K = args.entities_per_call, args.passes
    seeds = range(args.first_seed, args.first_seed + K)
    passes: Dict[str, List[str]] = {m: [f"{m}{pass_label(N, s)}" for s in seeds] for m in models}
    E, data, jobs = Path(args.experiments_dir), Path(args.instructions_dir), jobs_of(args)
    refused: List[str] = []
    recipes = [(f"{m}{averaged_label(N, K)}", passes[m]) for m in models if K > 1]
    if len(models) > 1:
        recipes.append((f"{'+'.join(models)}{averaged_label(N, K)}", [c for m in models for c in passes[m]]))
    for out, sources in recipes:
        r = avg.average_cells(out, sources, jobs, E, data, limit=args.limit)
        refused += [f"{out}: {line}" for line in r.refused]
        print(f"{out}: {r.made} cells derived, {r.kept} up to date, {len(r.refused)} refused")
    return refused


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--axes_file", help="'axis_dir pos neg pair_type' rows (scripts/tier_eval_axes.tsv); or --pair")
    p.add_argument("--pair", nargs=2, metavar=("POS", "NEG"))
    p.add_argument("--pair_type", choices=["roles", "traits"])
    p.add_argument("--experiments_dir", default=ev.DEFAULT_EXPERIMENTS_DIR)
    p.add_argument("--instructions_dir", default="data", help="the corpus being judged (default: data)")
    p.add_argument("--judge_model", action="append", default=None,
                   help=f"Repeatable (default: {', '.join(DESCRIPTION_JUDGES)}; also measured: {', '.join(OPTIONAL_JUDGES)})")
    p.add_argument("--entities_per_call", type=int, default=DESCRIPTION_ENTITIES_PER_CALL,
                   help=f"default {DESCRIPTION_ENTITIES_PER_CALL}")
    p.add_argument("--passes", type=int, default=DESCRIPTION_PASSES, help=f"random orders per judge (default {DESCRIPTION_PASSES})")
    p.add_argument("--first_seed", type=int, default=FIRST_SEED, help=f"shuffle seed of the first pass (default {FIRST_SEED})")
    p.add_argument("--name_format", choices=list(NAME_FORMATS), default=DEFAULT_NAME_FORMAT,
                   help="how prompts show entity names (judge_tier_cost_eval.py)")
    p.add_argument("--transport", choices=list(ev.tt.TRANSPORT_CHOICES), default="auto",
                   help="default auto: GPT-5.6 Luna by Flex, Haiku 5.5 by Message Batches, Gemini in real time")
    p.add_argument("--budget_usd", type=float, default=None,
                   help="per pass of a judge: stop issuing live and Flex requests past this measured spend (a batch "
                        "is submitted whole)")
    p.add_argument("--limit", type=int, default=None, help="only the first N entities of each axis, to try a judge cheaply")
    p.add_argument("--requests_per_second", type=int, default=None)
    p.add_argument("--max_in_flight", type=int, default=None)
    p.add_argument("--dry_run", action="store_true", help="the cost estimate of each pass; no calls, nothing written")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.axes_file) == bool(args.pair):
        parser.error("give --axes_file or --pair, one of them")
    if args.pair and not args.pair_type:
        parser.error("--pair needs --pair_type")
    if args.passes < 1 or args.entities_per_call < 2:
        parser.error("--passes must be at least 1 and --entities_per_call at least 2")
    models = list(dict.fromkeys(args.judge_model or DESCRIPTION_JUDGES))
    with ThreadPoolExecutor(max_workers=min(len(models), MAX_CONCURRENT_JUDGES)) as pool:
        codes = list(pool.map(lambda m: run_judge(args, m), models))
    failed = {m: c for m, c in zip(models, codes) if c}
    if failed:
        logger.error(f"not averaged, since passes did not finish: {failed}; run again, and finished work is kept")
        return next(iter(failed.values()))
    if args.dry_run:
        return 0
    refused = average_all(args, models)
    for line in refused:
        logger.error(f"REFUSED {line}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
