#!/usr/bin/env python3
"""The recovery harness: hide a share of the corpus's traits, score a generator's run against the rest, and see
which hidden traits its candidates find again.

    uv run python data_analysis/gap_generation/recovery_test.py --generator G --run-id R --hidden-frac 0.1 \\
        --seed S [S ...] [--transport auto|live|batches] --budget-usd C [--batch-id B] [--dry-run] [--resume]

The spec is ``reports/trait_gap_generation/coding_plan_platform.md``, "The recovery harness"; the library is
``assistant_axis/gapgen/recovery.py``, whose docstring says what each step does.  Defaults: ``--hidden-frac
0.1``, ``--seed 0 1`` (two seeds; the report gives each and their mean), ``--transport auto``, ``--batch-id
rec_<G>_<R>``.  ``--budget-usd`` is required.  Per seed S:

1. **hide**: ``data/candidates/recovery/<B>/seed<S>/hidden.json``, ``--hidden-frac`` of the corpus's traits drawn
   by region (``--regions``, default ``data/candidates/corpus_regions.json``), a pair, triangle or tetrahedron
   hidden whole;
2. **M3 against the reduced corpus**: ``novelty_score.py score --batch-id <B>_s<S> --run G/R --hide
   <hidden.json>``, run in process, writing ``data/candidates/novelty/<B>_s<S>/`` and never the registry (the seed
   queue's live entries in its search as in any new run, less the hidden stems' entries; ``--no-queue-search``
   passes through, to reproduce a harness run from before 2026-10-09).  The
   run's rows must already carry their M1 filter blocks (``traithood_filter.py --run G/R``); M1 is not run
   again, and rows without one are counted and left out;
3. **match**: every candidate the reduced run decided, against the hidden traits (its label, then the overlap
   call on the hidden traits among its 10 nearest in the full corpus): ``seed<S>/matches.jsonl`` (one line per
   label match and pair judged), ``seed<S>/responses.jsonl``, ``seed<S>/usage.json``;
4. **report**: ``data/candidates/recovery/<B>/recovery_report.json`` (with its provenance envelope) and
   ``recovery_report.md`` (each seed and the mean: recall over the candidates M3 kept, by region and by
   arrangement kind, precision, groups recovered whole, false covers, reachability, cost), ``usage.json`` (the
   whole harness: every seed's M3 run and match calls), ``run.json``.

Cost.  Before anything is sent, every seed's M3 estimate (``novelty_score.py``'s own) and match estimate (Sonnet
on each hidden trait among a candidate's 10 nearest, Opus on 40% of them) are printed and their total is checked
against ``--budget-usd``, the hard cap of the whole harness: each stage is given what is left of it.  A budget
or estimate over $20 needs ``--confirm-expensive`` and ``--confirmed-by``.  ``--dry-run`` prints the draws, the M3
dry runs and the estimates, and writes nothing.  A paid run is refused while the platform's code or prompt paths
have uncommitted changes, unless ``--allow-dirty`` (recorded).  ``--resume`` continues a run: the hidden files are
reused, a finished M3 run is not run again (an unfinished one is resumed), and no call already answered is sent
again.  Exit status: 0; 1 (the run directory exists without ``--resume``, or is missing with it); 2 (refused, or
a budget stop).
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import logging
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import recovery as RC  # noqa: E402
from assistant_axis.gapgen.batches import BatchTransport, choose_transport  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import Registry, has_source, utc_now  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage  # noqa: E402
from data_analysis.gap_generation import novelty_score as NS  # noqa: E402

logger = logging.getLogger("recovery_test")


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()] if Path(p).exists() else []


def m3_batch_id(batch_id: str, seed: int) -> str:
    """The reduced-corpus M3 run of one seed: ``novelty/<B>_s<S>/``."""
    return f"{batch_id}_s{seed}"


def score_argv(args, seed: int, hidden_path: Path, *, budget: float, dry_run: bool, resume: bool) -> list[str]:
    """The ``novelty_score.py score`` command line of one seed's reduced-corpus run."""
    a = ["score", "--batch-id", m3_batch_id(args.batch_id, seed), "--run", f"{args.generator}/{args.run_id}",
         "--hide", str(hidden_path), "--transport", args.transport, "--budget-usd", f"{max(0.0, budget):.4f}",
         "--registry", str(args.registry), "--data-dir", str(args.data_dir), "--metric-config", str(args.metric_config),
         "--cache-dir", str(args.cache_dir), "--query-form", args.query_form, "--concurrency", str(args.concurrency)]
    for flag, val in (("--out-root", args.out_root), ("--rubrics-dir", args.rubrics_dir), ("--confirmed-by", args.confirmed_by)):
        if val is not None:
            a += [flag, str(val)]
    for flag, on in (("--dry-run", dry_run), ("--resume", resume), ("--allow-dirty", args.allow_dirty),
                     ("--confirm-expensive", args.confirm_expensive)):
        if on:
            a.append(flag)
    qs = getattr(args, "queue_search", None)        # the seed queue in the reduced run's search (default: on)
    if qs is not None:
        a.append("--queue-search" if qs else "--no-queue-search")
    return a


def run_m3(argv: list[str], *, quiet: bool) -> tuple[int, dict]:
    """``novelty_score.py score`` in process: ``(status, info)`` (``run_scoring``'s ``info``); with ``quiet`` its
    printout is kept back (the estimate before the real run)."""
    info: dict = {}
    ns = NS.build_parser().parse_args(argv)
    buf = io.StringIO()
    with (contextlib.redirect_stdout(buf) if quiet else contextlib.nullcontext()):
        rc = NS.run_scoring(ns, argv, mode="shortlist", info=info)
    info["stdout"] = buf.getvalue()
    return rc, info


def run_candidates(rows: dict, generator: str, run_id: str) -> tuple[list[NR.M3Candidate], dict]:
    """The run's rows M3 would take (``novelty_score.select_candidates`` as ``--hide`` calls it: a ``trait``
    verdict with a gloss, not held), and why the others are left out."""
    a = SimpleNamespace(keys=None, run=[(generator, run_id)], unscored=False, rescore=False, include_held=False,
                        limit=None)
    return NS.select_candidates(rows, a, batch_id="", ignore_decided=True)


def cached_vectors(cands, cfg, cache, query_form: str) -> dict:
    """The candidates' query vectors that are in the embedding cache (unit rows), by key; no call."""
    from assistant_axis.gapgen import embed as EM
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = [NV.query_text(c.label, c.gloss, query_form=query_form, representation=cfg.representation) for c in cands]
    found, _ = cache.lookup(embedder.tag, texts)
    if not found:
        return {}
    idx = sorted(found)
    unit = EM.normalize_rows([found[i] for i in idx])
    return {cands[i].key: unit[j] for j, i in enumerate(idx)}


def match_estimate(cands, vectors, index: Optional[NV.CorpusIndex], hidden, *, k: int, n_corpus: int,
                   transport: str) -> tuple[Estimate, dict]:
    """Sonnet on every hidden trait among each candidate's ``k`` nearest (counted on the full index where every
    corpus text and the candidate's vector are cached; else ``k`` times the hidden share), Opus on
    :data:`novelty_runner.OPUS_SHARE_FULL_SCAN` of them; at batch rates for ``batches``."""
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    share = len(hidden) / max(1, n_corpus)
    counted, rough = 0, 0.0
    have = [c for c in cands if index is not None and c.key in vectors]
    if have:
        items, _ = RC.match_plan(have, vectors, index, hidden, k=k)
        counted = sum(1 for it in items if it["how"] == "overlap")
    rough = (len(cands) - len(have)) * k * share
    n = int(round(counted + rough))
    est = Estimate()
    est.add(f"match: Sonnet on each hidden trait among a candidate's {k} nearest", NR.FIRST_MODEL + suffix, n,
            *NR.OVERLAP_TOKENS["sonnet"])
    est.add(f"match: Opus ({NR.OPUS_SHARE_FULL_SCAN:.0%} of pairs)", NR.SECOND_MODEL + suffix,
            int(round(n * NR.OPUS_SHARE_FULL_SCAN)), *NR.OVERLAP_TOKENS["opus"])
    return est, {"n_pairs": n, "counted": counted, "rough": round(rough, 1),
                 "how": "counted on the full index" if not rough else
                 (f"{len(have)} candidates counted, {len(cands) - len(have)} at k x the hidden share" if have else
                  "k x the hidden share (the full corpus or the candidates' vectors are not all cached)")}


def m3_finished(d: Path) -> bool:
    """A reduced-corpus run that decided every candidate (``run.json`` status 0, none stalled)."""
    p = d / "run.json"
    if not p.exists():
        return False
    run = json.loads(p.read_text(encoding="utf-8"))
    return run.get("status") == 0 and run.get("n_stalled") == 0 and run.get("finished_at") is not None


def usage_total(*paths_: Path) -> float:
    return round(sum(MultiModelUsage.load_or_create(p).total_cost_usd for p in paths_ if Path(p).exists()), 6)


def match_seed(args, *, seed: int, seed_dir: Path, hidden_doc: dict, m3_dir: Path, cfg, cache, rubrics, budget: float,
               ) -> tuple[int, Optional[dict]]:
    """Step 3 and the seed's figures: ``(status, figures)``; status 2 on a budget stop (every answer kept)."""
    from assistant_axis.gapgen import embed as EM
    results = _read_jsonl(m3_dir / "results.jsonl")
    m3_run = json.loads((m3_dir / "run.json").read_text(encoding="utf-8"))
    rules = NV.rules_of({"rules": m3_run.get("rules")}) if m3_run.get("rules") else NV.DEFAULT_RULES
    query_form = (m3_run.get("settings") or {}).get("query_form") or args.query_form
    cands = [NR.M3Candidate(key=r["key"], stem=r["stem"], label=r["label"], gloss=r["gloss"],
                            alignment_score=r["novelty"].get("alignment_score"), region=r["novelty"].get("region"),
                            generators=list(r.get("generators") or [])) for r in results]
    decisions = {r["key"]: r["novelty"] for r in results}
    usage = GuardedUsage(budget_usd=budget, usage_path=seed_dir / "usage.json")
    if args.resume:
        from assistant_axis.gapgen.batches import with_current_batch_keys
        usage.merge_from(with_current_batch_keys(MultiModelUsage.load_or_create(seed_dir / "usage.json")))
    status, rows, near = 0, [], {}
    try:
        index, _ = NS.load_index(cfg, data_dir=args.data_dir, cache=cache, usage=usage, allow_embed=True)
        embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
        texts = [NV.query_text(c.label, c.gloss, query_form=query_form, representation=cfg.representation) for c in cands]
        E = EM.embed_texts(embedder, texts, cache=cache, usage=usage) if cands else []
        vectors = {c.key: E[i] for i, c in enumerate(cands)}
        items, _ = RC.match_plan(cands, vectors, index, hidden_doc["hidden"], k=cfg.k)
        n_pair_cands = len({it["key"] for it in items if it["how"] == "overlap"})
        transport, why = choose_transport(args.transport, n_pair_cands)
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)
        runner = NR.NoveltyRunner(client=client, batch_id=f"{args.batch_id}_s{seed}_match", rubrics=rubrics, index=index,
                                  label_sets=NS.label_sets_for(args.data_dir), usage=usage,
                                  responses_path=seed_dir / "responses.jsonl", k=cfg.k, mode="shortlist",
                                  config_version=cfg.config_version, concurrency=args.concurrency,
                                  resume_records=_read_jsonl(seed_dir / "responses.jsonl") if args.resume else (),
                                  rules=rules)
        if transport == "batches":
            import anthropic
            runner.cache_ttl = NR.BATCH_CACHE_TTL
            runner.transport = BatchTransport(runner, anthropic.Anthropic(), seed_dir / "batches.json", budget_usd=budget)
        logger.info("seed %s: matching %d candidates, %d label matches, %d overlap pairs (%s)", seed, len(cands),
                    sum(1 for it in items if it["how"] == "label"), sum(1 for it in items if it["how"] == "overlap"), why)
        rows, near = RC.match_candidates(runner, cands, vectors, hidden_doc["hidden"], k=cfg.k, decisions=decisions,
                                         rules=rules)
        runner.warn_parse_rates(logger)
    except BudgetExceededError as exc:
        print(f"STOPPED (seed {seed}, match): {exc}", file=sys.stderr)
        status = 2
    finally:
        usage.write_json(seed_dir / "usage.json")
    if status:
        return status, None
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), seed_dir / "matches.jsonl")
    m3_usd = usage_total(m3_dir / "usage.json")
    cost = {"reduced_m3_usd": m3_usd, "match_usd": round(usage.total_cost_usd, 6),
            "total_usd": round(m3_usd + usage.total_cost_usd, 6)}
    m3_summary = json.loads((m3_dir / "summary.json").read_text(encoding="utf-8")).get("result", {}) \
        if (m3_dir / "summary.json").exists() else {}
    reduced = {"batch_id": m3_dir.name, "by_decision": m3_summary.get("by_decision"),
               "n_stalled": m3_summary.get("n_stalled"), "skipped": m3_summary.get("skipped"),
               "rules": rules.name, "cosine_floor": rules.cosine_floor}
    return 0, RC.seed_figures(hidden_doc, results, rows, near=near, reduced_run=reduced, cost=cost)


def prepare(args, *, seeds, out_dir: Path, tmp: Path, traits, regions, kinds, sha, cands, cfg, cache):
    """The draws (a resumed seed's ``hidden.json`` on record, else today's draw written under ``tmp``), the
    estimate of the whole harness and the gate.  Returns ``(hidden paths by seed, total estimate, dirty files)``,
    or an exit status: 2 when refused (on a dry run, 0 after printing what the real run would do)."""
    hidden_paths: dict[int, Path] = {}
    hidden_docs: dict[int, dict] = {}
    for s in seeds:
        on_record = out_dir / f"seed{s}" / "hidden.json"
        draw = RC.draw_hidden(traits, frac=args.hidden_frac, seed=s, regions=regions, kinds=kinds)
        if args.resume and on_record.exists():
            doc = json.loads(on_record.read_text(encoding="utf-8"))
            if doc.get("hidden_frac") != args.hidden_frac:
                print(f"REFUSED: seed {s}: {on_record} hid {doc.get('hidden_frac')} of the corpus, this command "
                      f"--hidden-frac {args.hidden_frac}", file=sys.stderr)
                return 2
            if doc.get("hidden") != draw["hidden"]:
                print(f"WARNING: seed {s}: {on_record} differs from today's draw (the corpus or the regions changed "
                      "since); the file on record is kept", file=sys.stderr)
            hidden_paths[s] = on_record
        else:
            hidden_paths[s] = tmp / f"seed{s}" / "hidden.json"
            doc = RC.write_hidden(hidden_paths[s], draw, data_dir=args.data_dir, regions_path=args.regions, git_sha=sha)
        hidden_docs[s] = doc
        print(f"seed {s}: hidden {doc['n_hidden']} of {doc['n_corpus']} traits in {doc['n_groups']} groups "
              f"(target {doc['n_target']}; by stratum {json.dumps({k: v['n_hidden'] for k, v in doc['strata'].items()})})")
    full_index, full_info = NS.load_index(cfg, data_dir=args.data_dir, cache=cache)
    vectors = cached_vectors(cands, cfg, cache, args.query_form)
    total, lines = 0.0, []
    for s in seeds:
        d = paths.novelty_dir(m3_batch_id(args.batch_id, s), candidates_dir=args.out_root)
        if args.resume and m3_finished(d):
            m3_usd, m3_note = 0.0, "finished: not run again"
        else:
            rc, info = run_m3(score_argv(args, s, hidden_paths[s], budget=args.budget_usd, dry_run=True, resume=False),
                              quiet=not args.dry_run)
            if rc != 0 or info.get("estimate_usd") is None:
                print(info.get("stdout", ""))
                print(f"REFUSED: seed {s}: the M3 dry run gave no estimate (status {rc})", file=sys.stderr)
                return 2
            m3_usd, m3_note = info["estimate_usd"], f"{info.get('n_candidates')} candidates"
        transport, _ = choose_transport(args.transport, len(cands))
        mest, minfo = match_estimate(cands, vectors, full_index, hidden_docs[s]["hidden"], k=cfg.k,
                                     n_corpus=len(traits), transport=transport)
        total += m3_usd + mest.usd
        lines.append(f"seed {s}: M3 against the reduced corpus ${m3_usd:.3f} ({m3_note}); match ${mest.usd:.3f} "
                     f"({minfo['n_pairs']} pairs, {minfo['how']})\n{mest.format()}")
    print("estimate:\n" + "\n".join(lines) + f"\ntotal estimate = ${total:.3f}")
    if full_index is None:
        print(f"note: {full_info['n_missing_from_cache']} corpus texts are not in the embedding cache; the M3 runs and "
              "the match stage embed them (charged, a few cents per 10,000)")
    refused = None
    try:
        cap = confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
        print(f"hard cap of the whole harness: ${cap:.2f}")
    except CostRefused as exc:
        refused = exc.msg
    dirty = platform_dirty_files()
    if refused is None and dirty and not args.allow_dirty:
        refused = (f"uncommitted changes to the platform's own code or prompt paths ({len(dirty)}: "
                   f"{'; '.join(x.strip() for x in dirty[:5])}); commit first, or pass --allow-dirty")
        print(f"REFUSED: {refused}", file=sys.stderr)
    if args.dry_run and refused:
        print(f"DRY-RUN: the real run would be REFUSED: {refused}")
    elif refused:
        return 2
    return hidden_paths, total, dirty


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generator", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--hidden-frac", type=float, default=RC.DEFAULT_HIDDEN_FRAC,
                    help=f"the share of the corpus's traits hidden (default {RC.DEFAULT_HIDDEN_FRAC})")
    ap.add_argument("--seed", type=int, nargs="+", default=list(RC.DEFAULT_SEEDS),
                    help="one hidden draw per seed (default: 0 1); the report gives each and their mean")
    ap.add_argument("--transport", choices=("auto", "live", "batches"), default="auto",
                    help="for the M3 runs and the match calls (auto: live under 300 candidates)")
    ap.add_argument("--budget-usd", type=float, required=True, help="the hard cap of the whole harness")
    ap.add_argument("--batch-id", default=None, help="default rec_<generator>_<run_id>")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", default=None, help="who gave the explicit go for a budget over $20")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--out-root", type=Path, default=None, help="candidates dir holding recovery/ and novelty/")
    ap.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    ap.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    ap.add_argument("--rubrics-dir", type=Path, default=None)
    ap.add_argument("--regions", type=Path, default=paths.CORPUS_REGIONS_PATH)
    ap.add_argument("--query-form", choices=NV.QUERY_FORMS, default=NV.DEFAULT_QUERY_FORM)
    ap.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    NS._queue_search_arg(ap)     # passed to the reduced-corpus M3 runs; the hidden stems' entries are left out
    return ap


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    try:
        paths.check_id(args.generator, "generator")
        paths.check_id(args.run_id, "run_id")
        args.batch_id = args.batch_id or f"rec_{args.generator}_{args.run_id}"
        paths.check_id(args.batch_id, "batch_id")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if not 0.0 < args.hidden_frac <= 1.0:
        print(f"REFUSED: --hidden-frac {args.hidden_frac} is not a share from 0 (excluded) to 1", file=sys.stderr)
        return 2
    seeds = list(dict.fromkeys(args.seed))
    out_dir = paths.recovery_dir(args.batch_id, candidates_dir=args.out_root)
    if not args.dry_run:
        if out_dir.exists() and not args.resume:
            print(f"{out_dir} exists; choose a new --batch-id or pass --resume to continue it", file=sys.stderr)
            return 1
        if args.resume and not out_dir.exists():
            print(f"--resume: {out_dir} does not exist", file=sys.stderr)
            return 1
    try:
        rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    except NS.RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    cfg = MetricConfig.load(args.metric_config)
    cache = EM.EmbeddingCache(args.cache_dir)
    rows = Registry(args.registry).fold()
    run_rows = [r for r in rows.values() if has_source(r, args.generator, args.run_id)]
    if not run_rows:
        print(f"REFUSED: no registry rows from {args.generator}/{args.run_id} in {args.registry}; submit the run first "
              f"(gap_registry.py submit --from data/candidates/runs/{args.generator}/{args.run_id}/candidates.jsonl)",
              file=sys.stderr)
        return 2
    cands, skipped = run_candidates(rows, args.generator, args.run_id)
    n_unfiltered = skipped.get("not_filtered", 0)
    print(f"{args.generator}/{args.run_id}: {len(run_rows)} registry rows, {len(cands)} M3 candidates "
          f"(left out: {json.dumps(skipped)})")
    if n_unfiltered:
        print(f"WARNING: {n_unfiltered} rows of {args.generator}/{args.run_id} have no M1 filter block and are left out; "
              f"run traithood_filter.py --pipeline split --run {args.generator}/{args.run_id} first", file=sys.stderr)
    if not cands:
        print("REFUSED: no candidate to score", file=sys.stderr)
        return 2
    data_dir = Path(args.data_dir)
    traits = NV.load_trait_corpus(data_dir)
    regions = RC.load_regions(args.regions)
    kinds = RC.arrangement_kinds(data_dir, traits)
    sha = git_sha()
    tmp = Path(tempfile.mkdtemp(prefix="recovery_"))   # this run's draws until the gate passes (scratch)
    try:
        prep = prepare(args, seeds=seeds, out_dir=out_dir, tmp=tmp, traits=traits, regions=regions, kinds=kinds,
                       sha=sha, cands=cands, cfg=cfg, cache=cache)
        if isinstance(prep, int):
            return prep
        hidden_paths, total, dirty = prep
        if args.dry_run:
            print(f"DRY-RUN: would write {out_dir}/ and data/candidates/novelty/{args.batch_id}_s<seed>/ "
                  "(never the registry)")
            return 0
        for s in seeds:                      # the gate passed: the draws go to the run directory
            dest = out_dir / f"seed{s}" / "hidden.json"
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(hidden_paths[s], dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    run_meta = {"batch_id": args.batch_id, "generator": args.generator, "run_id": args.run_id, "git_sha": sha,
                "argv": sys.argv[1:] if argv is None else argv, "hidden_frac": args.hidden_frac, "seeds": seeds,
                "transport": args.transport, "budget_usd": args.budget_usd, "estimate_usd": round(total, 4),
                "confirmed_by": args.confirmed_by, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": {"paths": list(PLATFORM_PATHS), "dirty": dirty},
                "m3_runs": {str(s): m3_batch_id(args.batch_id, s) for s in seeds},
                "regions": {"path": str(args.regions), "sha256": RC.file_sha256(args.regions)},
                "candidates": {"n": len(cands), "skipped": skipped},
                "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")} for k, v in rubrics.items()},
                "models": {"overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
                "resumed": bool(args.resume), "started_at": utc_now()}
    earlier = json.loads((out_dir / "run.json").read_text(encoding="utf-8")) if (out_dir / "run.json").exists() else None
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    def spent() -> float:
        ps = []
        for s in seeds:
            ps += [paths.novelty_dir(m3_batch_id(args.batch_id, s), candidates_dir=args.out_root) / "usage.json",
                   out_dir / f"seed{s}" / "usage.json"]
        return usage_total(*ps)

    status, figures = 0, []
    for s in seeds:
        hp = out_dir / f"seed{s}" / "hidden.json"
        d = paths.novelty_dir(m3_batch_id(args.batch_id, s), candidates_dir=args.out_root)
        if not m3_finished(d):
            # what is left of the cap, plus this run's own earlier spend, which a resumed run counts again
            left = args.budget_usd - spent() + (usage_total(d / "usage.json") if d.exists() else 0.0)
            rc, info = run_m3(score_argv(args, s, hp, budget=left, dry_run=False, resume=d.exists()), quiet=False)
            if rc != 0 or not m3_finished(d):
                print(f"STOPPED: seed {s}: the M3 run against the reduced corpus ended with status {rc}"
                      + ("" if rc else " and undecided candidates (resume it: the same command with --resume)"),
                      file=sys.stderr)
                status = rc or 2
                break
        sd = out_dir / f"seed{s}"
        left = args.budget_usd - spent() + (usage_total(sd / "usage.json") if args.resume else 0.0)
        rc, fig = match_seed(args, seed=s, seed_dir=sd, hidden_doc=json.loads(hp.read_text(encoding="utf-8")),
                             m3_dir=d, cfg=cfg, cache=cache, rubrics=rubrics, budget=left)
        if rc:
            status = rc
            break
        figures.append(fig)
        k = fig["kept"]
        print(f"seed {s}: recall {k['n_recovered']} of {k['n_hidden']} ({RC._pct(k['recall'])}; {k['by_label']} by label), "
              f"precision {k['candidates']['n_recovering']} of {k['candidates']['n']}, false covers "
              f"{fig['covered']['n_false_cover_candidates']}, reachable {fig['reachable']['n']}, cost "
              f"${fig['cost']['total_usd']:.3f}")
    total_usage = MultiModelUsage()
    for s in seeds:
        for p in (paths.novelty_dir(m3_batch_id(args.batch_id, s), candidates_dir=args.out_root) / "usage.json",
                  out_dir / f"seed{s}" / "usage.json"):
            if p.exists():
                total_usage.merge_from(MultiModelUsage.load_or_create(p))
    total_usage.write_json(out_dir / "usage.json")
    print(total_usage.log_line())
    if figures:
        write_report(args, out_dir, figures, seeds_done=[f["seed"] for f in figures])
    run_meta.update(finished_at=utc_now(), status=status, cost_usd=round(total_usage.total_cost_usd, 4),
                    seeds_reported=[f["seed"] for f in figures])
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    return status


def write_report(args, out_dir: Path, figures: list[dict], *, seeds_done: list[int]) -> dict:
    """``recovery_report.json`` (with its provenance envelope: the hidden files, the M3 runs' results, the
    matches) and ``recovery_report.md``."""
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    report = RC.combine_seeds(figures)
    report.update({"batch_id": args.batch_id, "generator": args.generator, "run_id": args.run_id,
                   "hidden_frac": args.hidden_frac, "seeds_reported": seeds_done})
    inputs = []
    for s in seeds_done:
        d = paths.novelty_dir(m3_batch_id(args.batch_id, s), candidates_dir=args.out_root)
        inputs += [current_file_input(dep_key=f"hidden_s{s}", path=out_dir / f"seed{s}" / "hidden.json"),
                   current_file_input(dep_key=f"m3_results_s{s}", path=d / "results.jsonl"),
                   current_file_input(dep_key=f"matches_s{s}", path=out_dir / f"seed{s}" / "matches.jsonl")]
    env = json_metadata(report, title=f"recovery_test {args.batch_id}", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "recovery_report.json")
    labels = {s: t.label for s, t in NV.load_trait_corpus(args.data_dir).items()}
    atomic_write_text(RC.report_markdown(report, batch_id=args.batch_id, generator=args.generator, run_id=args.run_id,
                                         labels=labels), out_dir / "recovery_report.md")
    m = report["mean"]
    print(f"report: {out_dir / 'recovery_report.md'}; mean recall {RC._pct(m['recall_kept'])}, precision "
          f"{RC._pct(m['precision_kept'])}, false-cover candidates {m['false_cover_candidates']}, total cost "
          f"${report['total_cost_usd']:.3f}")
    return report


if __name__ == "__main__":
    sys.exit(main())
