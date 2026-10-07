#!/usr/bin/env python3
"""The pre-pilot test of the M3 overlap rubrics (m3_overlap_rubric_draft.md, "The test"; 2026-10-03), and
the overlap rubric arms experiment (coding_plan_overlap_arms.md; 2026-10-04).

    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 --dry-run
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_test_1 [--budget-usd 15]
        [--models claude-haiku-4-5-20251001 claude-sonnet-5-5 claude-opus-5-5] [--rubrics A B] [--seed 0]
        [--n-targets 100] [--concurrency 8] [--stop-below 0.99] [--resume] [--allow-dirty]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_1
        --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A C D E --passes 2 --budget-usd 20 [--dry-run]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_2 --write-subset
        [--subset-sources overlap_arms_1 overlap_test_1 overlap_test_2]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_2
        --models claude-sonnet-5-5 claude-opus-5-5 --rubrics A2 C2 D2 E2 --passes 2 --budget-usd 12
        --calls-from data/candidates/overlap_test/overlap_arms_2/subset.json [--round1-run overlap_arms_1] [--dry-run]
    uv run python data_analysis/gap_generation/overlap_test.py --run-id overlap_arms_3 --rubrics A
        --models claude-sonnet-5-5 claude-opus-5-5 --passes 2 --baseline-run overlap_test_1 --budget-usd 10 [--dry-run]
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

**Round 2** of the arms experiment (coding_plan_overlap_arms.md, "Round 2"): ``--rubrics`` takes A2, C2, D2
and E2 (round 1's A, C, D and E with their 2 and 3 lines redrafted).  ``--write-subset`` (no API call)
computes the confusion subset from every reading on record in ``--subset-sources`` (default
``overlap_arms_1 overlap_test_1 overlap_test_2``; rubric B never counts) and writes it to the run directory
as ``subset.json``, with the rule, the counts, the pair ids, the calls that hold them and the controls.
``--calls-from <subset.json>`` sends only the calls it names, whole (the pair set and the
``--baseline-run`` check are unchanged; the file is copied into the run directory as ``subset.json``, and a
resume must name the same calls).  The analysis then reads the run's ``subset.json`` and compares each
round-2 arm with its round-1 arm in ``--round1-run`` (default ``overlap_arms_1``; read only) on the same
pairs: the subset's, and every pair sent; ``results.jsonl`` marks each row ``in_subset``.

**Round 3** (coding_plan_overlap_arms.md, "Round 3", 2026-10-06): rubric A from version 5 on is written for
one pair per call (its *form*, ``single``; every other rubric and earlier version is a ``list``).  A stage of a
single-form rubric sends every pair of the calls as its own call (keyed by the pair's id), the user turn laid
out as the rubric file's rendered sample, the rubric as a cached system block, and the identical prompt in
every pass; records carry ``form``, ``pair_id`` and ``origin_call_id``.  The analysis of such a run adds a
"Round 3" section at the top of ``tables.md`` (and ``round3`` in ``summary.json``): version 6 against
version 4 in ``--round1-run`` (default ``overlap_arms_1``) on every pair and on the nearest pairs, and against
A2 in ``--round2-run`` (default ``overlap_arms_2``) on its pairs; the rule simulation, the slips, Opus on the
escalated pairs, Roger's 30 marks (``marks_key.json`` of ``--baseline-run``), the cache hit rate and the spend.

Writes ``data/candidates/overlap_test/<run id>/``: ``pairs.json`` (the calls and pairs, with the
provenance envelope), ``rendered_prompts.md`` (the requests as sent, for three variants: a nearest target,
one whose list holds the target's recorded antonym, one with a single listed trait; for every rubric of
the run, and the later passes' user turns), ``responses.jsonl`` (every request and answer, parsed),
``usage.json`` (cumulative ``MultiModelUsage``, written after every answer), ``run.json``, ``results.jsonl``
(one row per pair, rubric, model and pass), ``summary.json`` (the analysis, with the provenance envelope),
``tables.md``, ``run.log``, and ``marks_key.json``; and Roger's blinded sheet
``reports/trait_gap_generation/m3_overlap_marks.md`` (never overwritten).  ``--decode-marks`` reads his
marks back into ``marks_decoded.json``.

``--corpus-at GIT_SHA`` reads the trait files as committed at that commit instead of the working tree's: the pair
set is built from the corpus, so a run beside an earlier one made before the corpus grew (``overlap_arms_4``,
Haiku 5.5 and 4.5, beside ``overlap_arms_3``: ``--corpus-at fc6d542``) needs the earlier corpus to send the same
pairs and prompts (the ``--baseline-run`` check then passes).  Recorded in ``run.json`` and ``pairs.json``.

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
import shutil
import sys
import time
from collections import Counter
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
#: The run whose round-1 arms (A, C, D, E) round 2's rubrics are compared with, on the same pairs (and round
#: 3's version 6 with its rubric A, version 4).
DEFAULT_ROUND1_RUN = "overlap_arms_1"
#: The run whose A2 round 3's version 6 is compared with, on A2's pairs.
DEFAULT_ROUND2_RUN = "overlap_arms_2"
#: Round 2's confusion subset, in the run directory.
SUBSET_NAME = "subset.json"


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", required=True, help="directory name under --out-root")
    ap.add_argument("--out-root", type=Path, default=OUT_ROOT)
    ap.add_argument("--models", nargs="+", default=list(OT.MODELS))
    ap.add_argument("--rubrics", nargs="+", default=list(OT.DEFAULT_RUBRICS), choices=list(OT.RUBRICS),
                    help="A, B (the default), the arms C, D, E, and round 2's A2, C2, D2, E2")
    ap.add_argument("--write-subset", action="store_true",
                    help="compute round 2's confusion subset from the records of --subset-sources and write it to "
                         f"the run directory as {SUBSET_NAME} (no API call; with --dry-run, print it only)")
    ap.add_argument("--subset-sources", nargs="+", default=list(OT.SUBSET_SOURCES),
                    help="the runs under --out-root whose readings define the subset (default: "
                         f"{' '.join(OT.SUBSET_SOURCES)})")
    ap.add_argument("--calls-from", type=Path, default=None,
                    help="send only the calls named in this subset.json (its call_ids), whole; the pair set is unchanged")
    ap.add_argument("--round1-run", default=DEFAULT_ROUND1_RUN,
                    help="an earlier run under --out-root whose round-1 arms round 2's rubrics are compared with, on the "
                         f"same pairs (default {DEFAULT_ROUND1_RUN}; 'none' to skip); also round 3's version 4")
    ap.add_argument("--round2-run", default=DEFAULT_ROUND2_RUN,
                    help="an earlier run under --out-root whose A2 round 3's single-form rubric A is compared with, on "
                         f"A2's pairs (default {DEFAULT_ROUND2_RUN}; 'none' to skip)")
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
    ap.add_argument("--corpus-at", default=None, metavar="GIT_SHA",
                    help="read the trait files (texts and arrangements) as committed at this commit (git archive) "
                         "instead of the working tree's, so that a run sends the pairs and prompts of a run made "
                         "before the corpus grew (overlap_arms_4 beside overlap_arms_3: fc6d542); recorded in "
                         "run.json and pairs.json")
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


def corpus_snapshot(sha: str) -> Path:
    """The trait files (and the seed queue) as committed at ``sha``, written under a temporary directory
    removed when the process ends (``novelty_score.corpus_at_commit``); returns the data dir."""
    import atexit
    import tempfile
    from data_analysis.gap_generation.novelty_score import corpus_at_commit
    dest = Path(tempfile.mkdtemp(prefix=f"overlap_corpus_{sha.split('+', 1)[0]}_"))
    atexit.register(shutil.rmtree, dest, True)        # a scratch copy, not a deliverable (the sha is recorded)
    return corpus_at_commit(sha, dest)


def build(args):
    corpus_at = getattr(args, "corpus_at", None)
    data_dir = corpus_snapshot(corpus_at) if corpus_at else None
    inputs = OT.load_inputs(_REPO_ROOT, metric_config_path=args.metric_config, cache_dir=args.cache_dir,
                            vectors_dir=args.vectors_dir, labelled_path=args.labelled_pairs, dm_path=args.drop_or_merge,
                            data_dir=data_dir, corpus_at=corpus_at)
    # the run's rubrics, and rubric A for the marks sheet's scale
    rubrics = OT.load_rubrics(args.rubrics_dir, keys=list(dict.fromkeys(list(args.rubrics) + ["A"])))
    ps = OT.build_pair_set(inputs.corpus, inputs.emb_stems, inputs.Z, inputs.persona, inputs.labelled, inputs.dm_pairs,
                           inputs.partner, seed=args.seed, n_targets=args.n_targets, n_neighbours=args.n_neighbours,
                           n_antonyms=args.n_antonyms, n_random=args.n_random)
    ps.info.update(embedding=inputs.settings, persona=inputs.persona_info)
    return inputs, rubrics, ps


def variant_calls(ps: OT.PairSet, calls=None) -> dict:
    """The calls whose rendered prompts are read before a paid run, among ``calls`` (default every call of
    the pair set): a nearest target with no recorded opposite in its list, a nearest target whose list
    holds its recorded antonym, and a call with a single listed trait (a variant the calls lack is left
    out)."""
    calls = list(ps.calls if calls is None else calls)
    by_call: dict = {}
    for p in ps.pairs:
        by_call.setdefault(p.call_id, []).append(p)
    out = {}
    for c in calls:
        ant = [p for p in by_call[c.call_id] if OT.is_antonym_pair(p)]
        if "normal" not in out and c.set == OT.NEAREST and not ant:
            out["normal"] = c
        if "antonym_in_list" not in out and c.set == OT.NEAREST and ant:
            out["antonym_in_list"] = c
        if "single" not in out and len(c.listed) == 1:
            out["single"] = c
    if "antonym_in_list" not in out:
        for c in calls:
            if any(OT.is_antonym_pair(p) for p in by_call[c.call_id]):
                out["antonym_in_list"] = c
                break
    return out


def variant_pairs(ps: OT.PairSet, calls=None) -> dict:
    """The single form's calls whose rendered prompts are read before a paid run, among the pairs of ``calls``
    (default every call): a nearest pair that is not a recorded opposite, a nearest pair that is one, and a
    labelled pair (a variant the calls lack is left out)."""
    held = {c.call_id for c in (ps.calls if calls is None else calls)}
    out = {}
    for p in ps.pairs:
        if p.call_id not in held:
            continue
        name = ("nearest_opposite" if OT.is_antonym_pair(p) else "nearest") if p.group == OT.NEAREST else "labelled"
        if name not in out:
            out[name] = OT.PairCall(call_id=p.pair_id, set=p.set, target=p.target, listed=[p.listed],
                                    origin_call_id=p.call_id)
    return out


def single_prompts_text(ps, rubrics, corpus, model: str, keys, *, passes: int = 1, calls=None) -> list[str]:
    """The single-form rubrics' requests for :func:`variant_pairs`, as the model receives them."""
    v = variant_pairs(ps, calls)
    group = {p.pair_id: p.group for p in ps.pairs}
    out = [f"## One pair per call (the single form): rubric{'s' if len(keys) > 1 else ''} {', '.join(keys)}", "",
           "Every pair is its own call, keyed by its pair id; the user turn is the rubric file's rendered sample "
           "(target on the first line, the other trait on the second); the rubric goes as a cached system block."
           + ("  Pass 2 sends these prompts again, identical." if passes == 2 else
              f"  Passes 2 to {passes} send these prompts again, identical." if passes > 2 else ""), ""]
    for name, c in v.items():
        out += [f"### Pair: {name} ({c.call_id}, {group.get(c.call_id)}"
                f"{', recorded opposite' if name == 'nearest_opposite' else ''})", ""]
        for r in keys:
            out += ["```text", OT.rendered_prompt(c, corpus, rubric=r, rubric_text=rubrics[r]["text"], model=model,
                                                  form="single").rstrip("\n"), "```", ""]
    return out


def rendered_prompts_text(ps, rubrics, corpus, model: str, *, rubric_keys=None, passes: int = 1,
                          seed: int = 0, calls=None) -> str:
    """The requests of :func:`variant_calls` (among ``calls``, default every call) as the model receives
    them, for every rubric in ``rubric_keys`` (default every loaded one), and with ``passes`` > 1 the later
    passes' user turns; the single-form rubrics' requests for :func:`variant_pairs`."""
    keys = list(rubrics) if rubric_keys is None else list(rubric_keys)
    single = [r for r in keys if rubrics[r].get("form") == "single"]
    keys = [r for r in keys if r not in single]
    calls = list(ps.calls if calls is None else calls)
    v = variant_calls(ps, calls) if keys else {}
    which = (f"for {len(v)} variants and the rubrics {', '.join(keys)}" if keys else
             f"for the one-pair rubric{'s' if len(single) > 1 else ''} {', '.join(single)}")
    out = ["# Rendered prompts of the overlap test", "",
           "The requests exactly as the model receives them (rubric as the system prompt, one JSON object as the "
           f"user turn), {which}; settings shown for {model}.  Within a pass every rubric and model receives the "
           "identical user turn.", ""]
    if single:
        out += single_prompts_text(ps, rubrics, corpus, model, single, passes=passes, calls=calls)
    if not keys:
        return "\n".join(out)
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
        same = sum(OT.listed_order(c, OT.pass_order_seed(seed, p, c.call_id)) == list(c.listed) for c in calls)
        out += [f"## Pass {p}: the same calls, the listed traits in a fresh order", "",
                f"The system prompt is each rubric's, as in pass 1; only the user turn's order (and so the ids) "
                f"changes.  {same} of {len(calls)} calls happen to keep pass 1's order (every call of one "
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


def _other_run(args, name: str, what: str):
    """``(run id, directory)`` of an earlier run named by a flag, or ``None`` for none or this run."""
    b = (name or "").strip()
    if not b or b.lower() == "none" or b == args.run_id:
        return None
    check_id(b, what)
    return b, Path(args.out_root) / b


def load_round1(args, ps):
    """The ``--round1-run``'s answers, ``{"run_id", "path", "by_pass": {pass: collect_answers(...)}}``, when
    it exists and sends this pair set's calls; else ``None`` (with a warning)."""
    named = _other_run(args, args.round1_run, "round1_run")
    if named is None:
        return None
    run_id, d = named
    if not (d / "pairs.json").exists() or not (d / "responses.jsonl").exists():
        logger.warning("round-1 run %s has no pairs.json or responses.jsonl under %s: round 2 not compared with it",
                       run_id, _rel(args.out_root))
        return None
    theirs = OT.PairSet.from_json(json.loads((d / "pairs.json").read_text()))
    if not OT.same_calls(theirs, ps):
        logger.warning("round-1 run %s sends other calls than this run: round 2 not compared with it", run_id)
        return None
    records = OT.read_records(d / "responses.jsonl")
    return {"run_id": run_id, "path": d / "responses.jsonl",
            "by_pass": {p: OT.collect_answers(ps, records, pass_no=p) for p in OT.record_passes(records)}}


def load_other(args, ps, name: str, what: str):
    """An earlier run named by a flag (``{"run_id", "dir", "records", "run", "seed"}``) when it exists under
    ``--out-root`` and sends this pair set's calls (whole, or some of them); else ``None``, with a warning."""
    named = _other_run(args, name, what)
    if named is None:
        return None
    run_id, d = named
    if not (d / "pairs.json").exists() or not (d / "responses.jsonl").exists():
        logger.warning("%s %s has no pairs.json or responses.jsonl under %s: not compared", what, run_id,
                       _rel(args.out_root))
        return None
    if not OT.same_calls(OT.PairSet.from_json(json.loads((d / "pairs.json").read_text())), ps):
        logger.warning("%s %s sends other calls than this run: not compared", what, run_id)
        return None
    run = json.loads((d / "run.json").read_text()) if (d / "run.json").exists() else {}
    return {"run_id": run_id, "dir": d, "records": OT.read_records(d / "responses.jsonl"), "run": run,
            "seed": int(run.get("seed") or 0)}


def run_forms(records) -> dict:
    """``{rubric: form}`` of a run's records; a rubric sent in two forms is refused (``ValueError``)."""
    seen: dict = {}
    for rec in records:
        seen.setdefault(rec["rubric"], set()).add(OT.record_form(rec))
    mixed = {r: sorted(f) for r, f in seen.items() if len(f) > 1}
    if mixed:
        raise ValueError(f"rubrics sent in more than one form in one run: {mixed}")
    return {r: next(iter(f)) for r, f in seen.items()}


def round3_inputs(args, ps, records, by_pass, models):
    """What :func:`OT.analyse_round3` needs for this run's single-form rubric A: version 4 from
    ``--round1-run`` (its rubric A, both passes, with the prompt groups of its second pass), A2 from
    ``--round2-run`` (on the pairs it was sent), this run as version 6, the populations, Roger's marks (the
    marks key of ``--baseline-run`` and its rubric-A answers) and the records.  Missing runs are left out."""
    def per_model(bp, rubric):
        return {p: {m: ans for (r, m), ans in per.items() if r == rubric and m in models} for p, per in bp.items()}

    def versions_of(recs, rubric):
        return sorted({rec.get("rubric_version") for rec in recs if rec["rubric"] == rubric} - {None})
    versions = {}
    recs_by = {}
    extra = {}
    r1 = load_other(args, ps, args.round1_run, "round1_run")
    if r1:
        bp = {p: OT.collect_answers(ps, r1["records"], pass_no=p) for p in OT.record_passes(r1["records"])}
        v4 = per_model(bp, "A")
        if any(v4.values()):
            passes = sorted(v4)
            versions["v4"] = {"run": r1["run_id"], "rubric": "A", "rubric_versions": versions_of(r1["records"], "A"),
                              "form": "list", "by_pass": v4,
                              "groups": OT.prompt_groups(ps, r1["seed"], passes[1]) if len(passes) > 1 else None}
            recs_by["v4"] = r1["records"]
            extra["round1_responses"] = r1["dir"] / "responses.jsonl"
    r2 = load_other(args, ps, args.round2_run, "round2_run")
    if r2:
        bp = {p: OT.collect_answers(ps, r2["records"], pass_no=p) for p in OT.record_passes(r2["records"])}
        a2 = per_model(bp, "A2")
        if any(a2.values()):
            passes = sorted(a2)
            versions["A2"] = {"run": r2["run_id"], "rubric": "A2", "rubric_versions": versions_of(r2["records"], "A2"),
                              "form": "list", "by_pass": a2,
                              "groups": OT.prompt_groups(ps, r2["seed"], passes[1]) if len(passes) > 1 else None}
            recs_by["A2"] = r2["records"]
            extra["round2_responses"] = r2["dir"] / "responses.jsonl"
    versions["v6"] = {"run": args.run_id, "rubric": "A", "rubric_versions": versions_of(records, "A"), "form": "single",
                      "by_pass": per_model(by_pass, "A"), "groups": None}
    recs_by["v6"] = records
    populations = {"all": [p.pair_id for p in ps.pairs],
                   "nearest": [p.pair_id for p in ps.pairs if p.group == OT.NEAREST]}
    if "A2" in versions:
        sent = {pid for per in versions["A2"]["by_pass"].values() for ans in per.values() for pid in ans}
        populations["round2"] = [p.pair_id for p in ps.pairs if p.pair_id in sent]
    marks = None
    bdir = baseline_dir(args)
    if bdir is not None and (bdir / "marks_key.json").exists() and (bdir / "responses.jsonl").exists():
        base = load_other(args, ps, args.baseline_run, "baseline_run")
        if base:
            ans = OT.collect_answers(ps, base["records"], pass_no=1)
            marks = {"items": json.loads((bdir / "marks_key.json").read_text())["items"],
                     "test1": {m: ans[("A", m)] for m in models if ans.get(("A", m))}}
            extra["marks_key"] = bdir / "marks_key.json"
    return versions, populations, marks, recs_by, extra


def write_subset(args, ps, argv) -> int:
    """Round 2's confusion subset (``OT.confusion_subset``) from every reading on record in
    ``--subset-sources``, written to ``<run dir>/subset.json`` in the provenance envelope; no API call.
    Every source must send this pair set's calls.  An existing ``subset.json`` holding the same pairs and
    calls is left alone; one holding others is refused."""
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    out_dir = Path(args.out_root) / args.run_id
    records_by_run = {}
    specs = [current_file_input(dep_key="producer_script", path=Path(__file__)),
             current_file_input(dep_key="overlap_test_module", path=Path(OT.__file__))]
    for run in args.subset_sources:
        check_id(run, "subset source")
        d = Path(args.out_root) / run
        if not (d / "pairs.json").exists() or not (d / "responses.jsonl").exists():
            print(f"REFUSED: subset source {run} has no pairs.json or responses.jsonl under {_rel(args.out_root)}",
                  file=sys.stderr)
            return 2
        if not OT.same_calls(OT.PairSet.from_json(json.loads((d / "pairs.json").read_text())), ps):
            print(f"REFUSED: subset source {run} sends other calls than this pair set", file=sys.stderr)
            return 2
        records_by_run[run] = OT.read_records(d / "responses.jsonl")
        specs += [current_file_input(dep_key=f"pairs_{run}", path=d / "pairs.json"),
                  current_file_input(dep_key=f"responses_{run}", path=d / "responses.jsonl")]
    readings, sources = OT.pair_readings(ps, records_by_run)
    subset = OT.confusion_subset(ps, readings)
    subset.update(source_runs=list(args.subset_sources), sources=sources, computed_at=utc_now())
    c = subset["counts"]
    print(f"confusion subset: {c['n_pairs']} pairs ({c['rule_1']} by rule 1, {c['rule_2_only']} more by rule 2; "
          f"{c['rule_2']} meet rule 2) in {c['n_calls']} of {c['of_calls']} calls; {c['n_pairs_sent']} pairs in those "
          f"calls, {c['n_controls']} of them controls; by group {c['by_group']}; readings per pair "
          f"{c['readings_per_pair']}")
    print("readings: " + "; ".join(f"{s['run']} {s['rubric']} {OT.SHORT.get(s['model'], s['model'])} pass {s['pass']} "
                                   f"{s['n_readings']}" for s in sources))
    path = out_dir / SUBSET_NAME
    if args.dry_run:
        print(f"DRY-RUN: {_rel(path)} not written")
        return 0
    if path.exists():
        old = OT.load_subset(path)
        if old["call_ids"] == subset["call_ids"] and old["pair_ids"] == subset["pair_ids"]:
            print(f"{_rel(path)} already holds this subset; left as it is")
            return 0
        print(f"REFUSED: {_rel(path)} holds another subset ({len(old['pair_ids'])} pairs in {len(old['call_ids'])} "
              "calls)", file=sys.stderr)
        return 2
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(path, json_metadata(subset, inputs=specs, title=f"Confusion subset for {args.run_id} (overlap arms, "
                                   "round 2)", script=_rel(Path(__file__)), argv=argv))
    print(f"wrote {_rel(path)}")
    return 0


def restricted_calls(args, ps):
    """``(calls, subset)``: the calls to send, every call of the pair set or, with ``--calls-from``, the ones
    its file names (in the pair set's order), and that file's contents (``None`` without the flag).  Raises
    ``ValueError`` when the file names a call the pair set lacks, or a pair outside its calls."""
    if args.calls_from is None:
        return list(ps.calls), None
    subset = OT.load_subset(args.calls_from)
    view = ps.restricted(subset["call_ids"])
    known = {p.pair_id for p in view.pairs}
    stray = [pid for pid in subset["pair_ids"] + subset["control_pair_ids"] if pid not in known]
    if stray:
        raise ValueError(f"{len(stray)} pair(s) named in {args.calls_from} are not in its calls: {stray[:3]}")
    return list(view.calls), subset


def _file_sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def provenance_inputs(inputs, *, responses: Path = None, baseline_responses: Path = None, extra=None):
    """The run's declared inputs; ``extra``: further files read, ``{dep_key: path}`` (round 2's subset and
    the round-1 run's responses)."""
    from assistant_axis.provenance import current_file_input, current_files_input
    corpus_at = getattr(inputs, "corpus_at", None)
    specs = [current_file_input(dep_key="producer_script", path=Path(__file__)),
             current_file_input(dep_key="overlap_test_module", path=Path(OT.__file__),
                                extras={"corpus_at": str(corpus_at)} if corpus_at else None)]
    if not corpus_at:   # with --corpus-at the trait files are a commit's (its sha recorded above), not these
        specs.append(current_files_input(dep_key="trait_files",
                                         paths=sorted((_REPO_ROOT / "data" / "traits" / "instructions").glob("*.json"))))
    specs += [current_file_input(dep_key="metric_config", path=inputs.paths["metric_config"]),
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
    for key, path in (extra or {}).items():
        if path is not None and Path(path).exists():
            specs.append(current_file_input(dep_key=key, path=path))
    return specs


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_analysis(out_dir: Path, inputs, ps, args, argv) -> dict:
    """The analysis from the records.  A run restricted to some calls (``calls_from`` in its run.json) is
    analysed on those calls and their pairs only; a run with a ``subset.json`` marks its result rows
    ``in_subset``; a run of round-2 rubrics is compared with ``--round1-run`` on the same pairs."""
    from assistant_axis.plot_metadata import json_metadata
    records = OT.read_records(out_dir / "responses.jsonl")
    run_path = out_dir / "run.json"
    calls_from = (json.loads(run_path.read_text()) if run_path.exists() else {}).get("calls_from") or {}
    view = ps.restricted(calls_from["call_ids"]) if calls_from.get("call_ids") else ps
    subset_path = out_dir / SUBSET_NAME
    subset = OT.load_subset(subset_path) if subset_path.exists() else None
    passes = OT.record_passes(records) or [1]
    by_pass = {p: OT.collect_answers(view, records, pass_no=p) for p in passes}
    rows = [row for p in passes for row in OT.results_rows(view, by_pass[p], pass_no=p,
                                                           subset=subset["pair_ids"] if subset else None)]
    (out_dir / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                                           encoding="utf-8")
    models = [m for m in args.models if any((r, m) in by_pass[p] for p in passes for r in OT.RUBRICS)]
    first = {p: OT.first_attempt_parse(view, records, pass_no=p) for p in passes}
    forms = run_forms(records)
    summary = OT.analyse(view, by_pass.get(1, {}), models=models, reference=args.reference, n_boot=args.n_boot,
                         seed=args.seed, first_parse=first.get(1))
    has_a = any(r == "A" for p in passes for (r, _) in by_pass[p])
    # a single-form rubric A is compared with the earlier runs by round 3, not as the same user turns
    baseline = load_baseline(args, ps, models) if has_a and forms.get("A") != "single" else None
    summary["arms"] = OT.analyse_arms(view, by_pass, models=models, reference=args.reference, seed=args.seed,
                                      first_parse_by_pass=first, baseline=baseline, forms=forms)
    if baseline:
        summary["arms"]["baseline"]["path"] = baseline["path"]
    extra = {}
    if has_a and forms.get("A") == "single":
        # on the whole pair set: the earlier runs are matched against it (a run restricted to some calls is
        # measured only on the populations it answered in full)
        r3_by_pass = {p: OT.collect_answers(ps, records, pass_no=p) for p in passes}
        versions, populations, marks, recs_by, r3_extra = round3_inputs(args, ps, records, r3_by_pass, models)
        summary["round3"] = OT.analyse_round3(ps, versions, populations, models=models, reference=args.reference,
                                              marks=marks, records=recs_by)
        summary["round3"]["paths"] = {k: _rel(v) for k, v in r3_extra.items()}
        extra.update(r3_extra)
    round1 = None
    if any(OT.RUBRICS[r].get("round1") for p in passes for (r, _) in by_pass[p]):
        round1 = load_round1(args, ps)
        summary["round2"] = OT.analyse_round2(view, by_pass, round1["by_pass"] if round1 else None, subset=subset,
                                              models=models, reference=args.reference,
                                              round1_run=round1["run_id"] if round1 else None)
        if round1:
            summary["round2"]["round1_path"] = _rel(round1["path"])
    if subset:
        summary["subset"] = {"path": _rel(subset_path), "rule": subset.get("rule"), "counts": subset.get("counts"),
                             "n_pairs": len(subset["pair_ids"]), "n_calls": len(subset["call_ids"])}
    if calls_from:
        summary["sent"] = {"calls_from": calls_from.get("path"), "n_calls": len(view.calls), "n_pairs": len(view.pairs),
                           "of_calls": len(ps.calls), "of_pairs": len(ps.pairs)}
    usage_path = out_dir / "usage.json"
    if usage_path.exists():
        summary["usage"] = json.loads(usage_path.read_text())
    summary["pair_set_info"] = ps.info
    bdir = baseline_dir(args)
    extra.update({"subset": subset_path if subset else None})
    if round1:
        extra["round1_responses"] = round1["path"]
    env = json_metadata(summary, inputs=provenance_inputs(inputs, responses=out_dir / "responses.jsonl",
                                                          baseline_responses=(bdir / "responses.jsonl") if baseline
                                                          else None, extra=extra),
                        title=f"M3 overlap rubric test {args.run_id}", script=_rel(Path(__file__)), argv=argv)
    write_json(out_dir / "summary.json", env)
    (out_dir / "tables.md").write_text(OT.summary_markdown(summary, view, inputs.corpus), encoding="utf-8")
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


async def run_stages(client, rubrics, corpus, ps, args, usage, out_dir: Path, run: dict, save_run,
                     calls=None) -> int:
    """Every (pass, model, rubric) stage over ``calls`` (default every call of the pair set; a single-form
    rubric's stage sends every pair of them as its own call)."""
    calls = list(ps.calls if calls is None else calls)
    runner = OT.OverlapRunner(client, rubrics, corpus, usage=usage, responses_path=out_dir / "responses.jsonl",
                              concurrency=args.concurrency, seed=args.seed, usage_path=out_dir / "usage.json")
    for pass_no in range(1, args.passes + 1):
        for model in args.models:
            for r in args.rubrics:
                t0 = time.time()
                logger.info("stage: rubric %s (%s, %s form) on %s, pass %d, %d calls", r, OT.RUBRICS[r]["name"],
                            rubrics[r]["form"], model, pass_no, len(OT.stage_calls(calls, rubrics[r]["form"])))
                res = await runner.run_stage(r, model, calls, pass_no=pass_no)
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

    if args.write_subset:
        return write_subset(args, ps, argv_list)

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

    try:
        calls, subset = restricted_calls(args, ps)
    except (ValueError, OSError) as exc:
        print(f"REFUSED: --calls-from: {exc}", file=sys.stderr)
        return 2
    call_ids = [c.call_id for c in calls]
    resuming = args.resume and (out_dir / "responses.jsonl").exists()
    recorded_run = json.loads((out_dir / "run.json").read_text()) if resuming and (out_dir / "run.json").exists() else {}
    recorded_calls = (recorded_run.get("calls_from") or {}).get("call_ids")
    if resuming and (recorded_calls or subset is not None) and recorded_calls != (call_ids if subset else None):
        how = (f"pass --calls-from naming the same {len(recorded_calls)} calls "
               f"({recorded_run['calls_from'].get('path')})" if recorded_calls
               else "the run was started with every call; leave out --calls-from")
        print(f"REFUSED: a resume must send the calls the run was started with: {how}", file=sys.stderr)
        return 2
    target = out_dir / SUBSET_NAME
    if subset is not None and target.exists() and Path(args.calls_from).resolve() != target.resolve():
        here = OT.load_subset(target)
        if here["call_ids"] != subset["call_ids"] or here["pair_ids"] != subset["pair_ids"]:
            print(f"REFUSED: {_rel(target)} holds another subset than {args.calls_from}", file=sys.stderr)
            return 2
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
    cached_usd = 0.0
    for p in range(1, args.passes + 1):
        for m in args.models:
            for r in args.rubrics:
                # a single-form rubric's stage sends one call per pair, keyed by the pair's id
                cs = [c for c in OT.stage_calls(calls, rubrics[r]["form"]) if (r, m, c.call_id, p) not in done]
                est.lines.extend(OT.estimate(cs, inputs.corpus, rubrics, [m], [r],
                                             pass_no=p if args.passes > 1 else None).lines)
                cached_usd += OT.cached_estimate_usd(cs, inputs.corpus, rubrics, [m], [r])
    info = ps.info
    print(f"M3 overlap test {args.run_id}: {info['n_calls']} calls ({info['n_calls_by_set']}), {info['n_pairs']} pairs "
          f"by group {info['n_pairs_by_group']}; {info['n_pairs_with_persona_cos']} pairs with a persona-space cosine; "
          f"list sizes {info['list_sizes']}; {info['nearest_recorded_antonyms']} nearest pairs are recorded clean "
          f"pairs; {info['n_unordered_pairs_twice']} unordered pairs judged in two calls")
    if subset is not None:
        sent_pairs = [p for p in ps.pairs if p.call_id in set(call_ids)]
        print(f"calls sent: {len(calls)} of {len(ps.calls)}, named in {_rel(args.calls_from)}: {len(sent_pairs)} pairs "
              f"({len(subset['pair_ids'])} subset pairs, {len(subset['control_pair_ids'])} controls), by group "
              f"{dict(Counter(p.group for p in sent_pairs))}; list sizes "
              f"{dict(sorted(Counter(len(c.listed) for c in calls).items()))}")
    print(f"labelled: {json.dumps(info['labelled'])}")
    print(f"embedding: {json.dumps(inputs.settings)}; persona: {json.dumps({k: v for k, v in inputs.persona_info.items() if k != 'trait_vectors_not_in_corpus'})}")
    print("rubrics: " + ", ".join(f"{r} {rubrics[r]['name']} v{rubrics[r]['version']} {rubrics[r]['sha256'][:12]} "
                                  f"({rubrics[r]['form']} form"
                                  f"{', cached system block' if OT.default_cache_system(rubrics[r]['form']) else ''})"
                                  for r in args.rubrics) + f"; passes {args.passes}")
    cached_note = (f"\n  with the rubric read from the prompt cache on the one-pair stages (as the usage records charge "
                   f"it): about ${cached_usd:.3f}; the total above, every input token uncached, is the one checked "
                   "against the budget" if any(OT.default_cache_system(rubrics[r]["form"]) for r in args.rubrics) else "")
    print(f"cost estimate (calls still to send; {len(done)} answered on record, ${prior.total_cost_usd:.2f} spent):\n"
          f"{est.format()}{cached_note}\n  budget ${args.budget_usd:.2f} for the whole run")
    try:
        cap = confirm_or_abort(est.usd + prior.total_cost_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
    except SystemExit as exc:
        return int(exc.code or 2)

    prompts_text = rendered_prompts_text(ps, rubrics, inputs.corpus, args.models[0], rubric_keys=args.rubrics,
                                         passes=args.passes, seed=args.seed, calls=calls)
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
                     prior=prior, prompts_text=prompts_text, calls=calls, subset=subset)
    finally:
        lock.close()


def _live(args, argv_list, out_dir: Path, inputs, rubrics, ps, *, est, cap, dirty, resuming, prior,
          prompts_text, calls=None, subset=None) -> int:
    """The paid part of :func:`main`, run under the session lock, over ``calls`` (default every call; with
    ``subset``, the calls ``--calls-from`` names, the file copied into the run directory)."""
    from assistant_axis.plot_metadata import json_metadata
    info = ps.info
    calls = list(ps.calls if calls is None else calls)
    out_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    if not resuming:
        write_json(out_dir / "pairs.json", json_metadata(ps.to_json(), inputs=provenance_inputs(inputs),
                                                          title=f"M3 overlap test {args.run_id}: calls and pairs",
                                                          script=_rel(Path(__file__)), argv=argv_list))
    calls_from = None
    if subset is not None:
        target = out_dir / SUBSET_NAME
        if not target.exists():
            shutil.copyfile(args.calls_from, target)
        calls_from = {"path": _rel(target), "given_as": str(args.calls_from), "sha256": _file_sha256(target),
                      "n_calls": len(calls), "n_pairs": sum(len(c.listed) for c in calls),
                      "n_subset_pairs": len(subset["pair_ids"]), "n_controls": len(subset["control_pair_ids"]),
                      "call_ids": [c.call_id for c in calls]}
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
                "forms": {rb["name"]: rb["form"] for rb in sent.values()},
                "cache_system": {rb["name"]: OT.default_cache_system(rb["form"]) for rb in sent.values()},
                "prompt_sha256": {rb["name"]: rb["sha256"] for rb in sent.values()},
                "prompts": {rb["name"]: rb["text"] for rb in sent.values()},
                "pair_set": {k: info[k] for k in ("n_calls", "n_pairs", "n_pairs_by_group", "n_calls_by_set")},
                "calls_from": calls_from, "round1_run": args.round1_run, "round2_run": args.round2_run,
                "corpus_at": getattr(args, "corpus_at", None),
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
        code = asyncio.run(run_stages(client, rubrics, inputs.corpus, ps, args, usage, out_dir, run, save_run,
                                      calls=calls))
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
