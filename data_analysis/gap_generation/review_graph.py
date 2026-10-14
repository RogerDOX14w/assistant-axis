#!/usr/bin/env python3
"""R1 of the trait-gap review tooling: the candidate graph over the candidates M3 kept, and its cliques.

Usage.  Build the graph of one or more finished M3 batches, look at the estimate first, then list the groups:

    uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_pilots_1 \\
        --from-batches gen_pilot_censuses gen_pilot_roget gen_pilot_wn_clusters --transport live --budget-usd 6 --dry-run
    uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_pilots_1 \\
        --from-batches gen_pilot_censuses gen_pilot_roget gen_pilot_wn_clusters --transport live --budget-usd 6
    uv run python data_analysis/gap_generation/review_graph.py groups --batch-id review_pilots_1

For a later generator run: score it with M3 first (``novelty_score.py score --batch-id B ...``), then
``build --batch-id review_<name> --from-batches B [B2 ...] --budget-usd C``.  A build that stopped (a budget stop, a
failed request, the gate below) goes on with ``--resume``, which sends no call already answered; ``--overwrite``
moves an old directory aside.  The registry is read, never written.

Decision 12 (two tiers of groups): the second direction of a pair is read when the first reads at
``--proposed-cut-off`` (3) or above, and ``graph.json`` carries ``proposed_groups`` (maximal cliques of 3-edges, less
those inside a merged group) beside ``cliques`` (the merged groups, 4-edges).  A graph built before it (second
direction only after a 4) is brought up to date by ``build --resume`` with the same arguments, which reads only the
missing second directions:

    uv run python data_analysis/gap_generation/review_graph.py build --batch-id review_pilots_1 \\
        --from-batches gen_pilot_censuses gen_pilot_roget gen_pilot_wn_clusters --transport live --budget-usd 2 --resume

The brief is ``reports/trait_gap_generation/coding_plan_review.md`` (section 2); the logic is
:mod:`assistant_axis.gapgen.review_graph`, whose docstring says what the graph holds.

Gate audit 8 (Roger, 2026-10-12): the candidate edges are the ``--k`` nearest **and** every pair at ``--pair-floor``
(0.55) or above, **and** every pair whose labels are one label blind (other-worldly / otherworldly: a 3-edge
whatever its readings); ``--pair-floor none`` gives the k nearest alone, the rule before.  The estimate's shares
come from an earlier R1 build's own records (``--calibrate-from``, default ``review_tda_1``; ``none``: M3's
shares, the rule before, which put the TDA build's estimate at 3.2 times its spend).  And the Opus pilot, Opus on
first directions Sonnet read 2, compared with Roger's decisions, the graph untouched:

    uv run python data_analysis/gap_generation/review_graph.py opus-pilot --batch-id review_tda_1 --n 128 \\
        --budget-usd 1 --dry-run

Plan 11 (the lexical sweep; Roger, 2026-10-14, option (d)): a kept candidate's ``lexical`` block becomes
``source: "lexical"`` edges to the linked corpus traits and queue entries, with the sweep's readings, and review
flags on its node (``lexical_proposed_merge`` for a link read at the row's cut-off: the card's "dictionary
(WordNet | Moby thesaurus): probably the same as X"); no call, and never a cut.  ``--stem-family`` (on for a new
build; a ``--resume`` keeps its earlier session's) adds a candidate edge, ``via`` ``stem_family``, for two kept
candidates of one stem family, read like any edge.

Commands:

* ``build --batch-id B --from-batches M3_BATCH ... --budget-usd C``: the kept candidates (M3 decision new or grey)
  of the named M3 batches; their ``--k`` (10) nearest other kept candidates by cosine in M3's covered space at
  ``--cosine-floor`` (0.25) or above, every other pair at ``--pair-floor`` (0.55) or above, and every label
  variant pair; the relation call per candidate (Haiku 5.5, rubric ``relation.md``, the
  unsure answers re-asked of Sonnet 5.5); the overlap call (rubric A, Sonnet 5.5 then Opus 5.5 under M3's rule at
  cut-off 4) on the pairs answered similar at ``--overlap-floor`` (0.35) or above, first direction, then the second
  where the first read ``--proposed-cut-off`` (3) or above; corpus edges copied from the M3 blocks; the merged
  groups (maximal cliques of the 4-edges) and the proposed groups (of the 3-edges).  Writes
  ``data/candidates/review/<B>/``: ``graph.json`` (the graph in a provenance envelope), ``usage.json`` (the
  project's schema plus a ``_provenance`` key), ``responses.jsonl`` (every response, as M3 keeps them),
  ``run.json`` and ``run.log``.
* ``groups --batch-id B [--top N]``: the merged groups, then the proposed groups, largest first, with their
  members' labels and the groups each is opposed to; the count of ungrouped candidates by generator.  No call.
* ``opus-pilot --batch-id B --n N --budget-usd C``: of the build's first directions Sonnet read 2 (never sent to
  Opus), N whose two terms Roger's ``decisions.jsonl`` settled, half in the same resolution and half in different
  ones (stratified by cosine, ``--seed``); Opus reads each with the prompt Sonnet read (checked against the build's
  records); written to ``<B>/<--pilot-id>/`` (``readings.jsonl``, ``report.json``, ``usage.json``,
  ``responses.jsonl``, ``run.json``) and compared with his decisions; ``graph.json`` and the groups are not touched.

Cost: the estimate is printed before any call (the relation calls as rendered; the overlap calls from the shares an
earlier R1 build measured per cosine bin in its own ``graph.json``, and the per-call tokens and unsure re-asks of its
``responses.jsonl``: ``--calibrate-from``; with ``none``, the shares M3 measured in the source batches' blocks and
the tokens of their ``responses.jsonl``);
``--budget-usd`` is the hard cap (an estimate over it is refused); over $20 needs ``--confirm-expensive
--confirmed-by``.  After the relation calls, the overlap stage is estimated again on the pairs actually marked for
it, and the run stops before any overlap call if the spend so far plus that would pass the cap (``--resume`` with
a larger budget then goes on; the relation answers are on record).  The cap covers the whole run: a ``--resume``
counts the spend of its earlier sessions (``usage.json``), and its estimate is the replay of the build on its
records with nothing sent (``review_graph.resume_estimate``: the calls not on record, and those they lead to by
the shares), checked as spend so far plus that estimate against ``--budget-usd``.  ``--dry-run`` prints the plan, the estimate and
the two prompts as rendered and writes and calls nothing.  A paid run is refused while the platform's code or
prompt paths have uncommitted changes, unless ``--allow-dirty``.  ``--transport auto`` sends fewer than 300
candidates live, more through the Message Batches API.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

import numpy as np  # noqa: E402

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import embed as EM  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import prompt_labels as PL  # noqa: E402
from assistant_axis.gapgen import records as RF  # noqa: E402
from assistant_axis.gapgen import review_graph as RG  # noqa: E402
from assistant_axis.gapgen.batches import BatchTransport, choose_transport  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import Registry, utc_now  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, log_formatter, \
    platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage  # noqa: E402
from data_analysis.gap_generation import novelty_score as NS  # noqa: E402

logger = logging.getLogger("review_graph")


# --------------------------------------------------------------------------- inputs

def query_vectors(cands, *, cfg, index, cache, query_form: str, usage=None, allow_embed: bool = False
                  ) -> tuple[dict, dict]:
    """``({key: projected unit query vector}, info)``: each candidate's query text as M3 embeds it
    (``novelty.query_text``), from the embedding cache, projected into the covered space by the corpus ``index``.
    Texts missing from the cache are embedded (charged to ``usage``, the canary first) only with ``allow_embed``;
    without it the vectors cover the cached candidates only (``info["n_to_embed"]`` says how many are missing)."""
    keys = sorted(cands)
    info = {"n_query_texts": len(keys), "n_cached": 0, "n_to_embed": 0}
    if not keys:
        return {}, info
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = [NV.query_text(cands[k].label, cands[k].gloss, query_form=query_form, representation=cfg.representation)
             for k in keys]
    found, miss = cache.lookup(embedder.tag, texts)
    info.update(n_cached=len(found), n_to_embed=len(miss))
    if miss and allow_embed:
        info["canary"] = EM.check_canary(embedder, cfg.canary["texts"], cache, usage=usage)
        E = EM.embed_texts(embedder, texts, cache=cache, usage=usage)
        rows = dict(enumerate(E))
    else:
        rows = {i: EM.normalize_rows(np.asarray(v)[None, :])[0] for i, v in found.items()}
    return {keys[i]: index.project(v) for i, v in rows.items()}, info


def load_queue(data_dir: Path) -> dict:
    p = Path(data_dir) / "seed_queue.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"entries": []}


def source_records(batch_ids, out_root: Optional[Path]) -> list[dict]:
    """The overlap records of the source M3 batches' ``responses.jsonl`` (the estimate's measured tokens)."""
    out = []
    for b in batch_ids:
        p = paths.novelty_dir(b, candidates_dir=out_root) / "responses.jsonl"
        if not RF.exists(p):
            continue
        for line in RF.read_text(p).splitlines():
            if '"step": "overlap"' in line:
                out.append(json.loads(line))
    return out


def _cand_chars(cands) -> float:
    vals = [len(c.label) + len(c.gloss) + 40 for c in cands.values()]
    return float(np.mean(vals)) if vals else 140.0


def floor_or_none(value: str) -> Optional[float]:
    """``--pair-floor``: a cosine, or ``none`` (the k nearest alone)."""
    if str(value).strip().lower() == "none":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"a cosine or 'none', not {value!r}") from exc


def read_records(path: Path, *, steps=None) -> list[dict]:
    """A ``responses.jsonl``'s records (those of ``steps`` only, when given; packed or not: ``records``)."""
    if not RF.exists(path):
        return []
    out = []
    for line in RF.read_text(path).splitlines():
        if line.strip():
            r = json.loads(line)
            if steps is None or r.get("step") in steps:
                out.append(r)
    return out


class CalibrationError(ValueError):
    pass


def calibration(names, out_root: Optional[Path], *, proposed_cut_off: int) -> tuple[Optional[RG.Shares], Optional[dict],
                                                                                     Optional[tuple], dict]:
    """``(shares, overlap tokens, unsure, info)`` from earlier R1 builds' own records (``--calibrate-from``; gate
    audit 8): ``r1_shares`` over their ``graph.json``, the overlap tokens and the unsure re-asks of their
    ``responses.jsonl``.  ``names`` ``None``: :data:`review_graph.DEFAULT_CALIBRATION`, and a build missing from
    ``out_root`` falls back to M3's shares (``(None, None, None, info)`` with a note); ``["none"]``: M3's shares;
    named builds must exist (:class:`CalibrationError`)."""
    explicit = names is not None
    names = list(RG.DEFAULT_CALIBRATION if names is None else names)
    if [n.lower() for n in names] == ["none"]:
        return None, None, None, {"source": "m3_blocks", "why": "--calibrate-from none"}
    graphs, records, missing = [], [], []
    for n in names:
        d = RG.review_dir(n, candidates_dir=out_root)
        if not RF.exists(d / "graph.json"):
            missing.append(n)
            continue
        graphs.append(RG.Graph.from_json(RF.read_json(d / "graph.json")))
        records += read_records(d / "responses.jsonl", steps=("overlap", "relation", "relation_unsure"))
    if missing and explicit:
        raise CalibrationError(f"--calibrate-from: no graph.json for {', '.join(missing)} under "
                               f"{RG.review_dir(missing[0], candidates_dir=out_root).parent}")
    if not graphs:
        return None, None, None, {"source": "m3_blocks", "why": f"default calibration {', '.join(missing)} not found: "
                                                                "M3's shares (the estimate errs high)"}
    shares = RG.r1_shares(graphs, second_at=proposed_cut_off)
    tokens = RG.measured_overlap_tokens(r for r in records if r.get("step") == "overlap")
    unsure = RG.r1_unsure(records)
    return shares, tokens, unsure, {"source": shares.source, "builds": [g.batch_id for g in graphs],
                                    "missing": missing, "n_records": len(records),
                                    "unsure": None if unsure is None else [round(unsure[0], 4), round(unsure[1], 3)]}


def make_runner(*, client, batch_id: str, rubrics: dict, index, usage, responses_path: Path, concurrency: int,
                config_version: str, embedding: dict, resume_records=(),
                label_form: str = PL.DEFAULT_LABEL_FORM) -> RG.ReviewRunner:
    """The build's runner; ``label_form`` (prompt_labels) is how its prompts show the labels: the judge display form
    for a new build, the earlier session's recorded form for a ``--resume``."""
    return RG.ReviewRunner(client=client, batch_id=batch_id, rubrics=rubrics, index=index,
                           label_sets=NV.LabelSets(set(), {}, {}), usage=usage, responses_path=responses_path,
                           config_version=config_version, concurrency=concurrency, embedding=embedding,
                           resume_records=resume_records, label_form=label_form)


def graph_config(args, cfg, rubrics: dict) -> dict:
    """``graph.json``'s ``config`` (the plan's fields, then the rest of what decided the graph)."""
    return {"k": args.k, "cosine_floor": args.cosine_floor, "pair_floor": args.pair_floor,
            "label_variants": "linked: a 3-edge whatever its readings (labels one label blind, stems differ)",
            "relabel_pairs": "linked: a 3-edge whatever its readings (a noun and its adjective sibling, via relabel)",
            "rules": f"cut_off_{RG.CUT_OFF}",
            "overlap_rubric": rubrics["overlap"]["version"], "relation_rubric": rubrics["relation"]["version"],
            "embedding": {"model": cfg.live_model["model_id"], "query_form": args.query_form},
            "overlap_floor": args.overlap_floor, "cut_off": RG.CUT_OFF, "proposed_cut_off": args.proposed_cut_off,
            "m3_rules": RG.RULES.name,
            "second_direction": f"read where the first direction read {args.proposed_cut_off} or above "
                                "(the proposed cut-off) under M3's rule at that cut-off",
            "models": {"relation": NR.RELATION_MODEL, "relation_unsure": NR.UNSURE_MODEL,
                       "overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
            "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")} for k, v in rubrics.items()},
            "space": {"config_version": cfg.config_version, "representation": cfg.representation,
                      "variant": cfg.covered["space"]["variant"]},
            **({"include": {"keys": sorted(args.include), "reason": args.include_reason}} if args.include else {})}


def provenance_inputs(args, rubrics: dict) -> list:
    from assistant_axis.provenance import current_file_input, current_files_input
    batches = ",".join(args.from_batches)
    inputs = [current_file_input(dep_key="registry", path=args.registry, extras={"from_batches": batches}),
              current_files_input(dep_key="rubrics", paths=[paths.RUBRICS_DIR / "overlap_concept.md",
                                                            paths.RUBRICS_DIR / "relation.md"],
                                  extras={"overlap_rubric": str(rubrics["overlap"]["version"]),
                                          "relation_rubric": str(rubrics["relation"]["version"])}),
              current_file_input(dep_key="metric_config", path=args.metric_config)]
    runs = [paths.novelty_dir(b, candidates_dir=args.out_root) / "run.json" for b in args.from_batches]
    runs = [p for p in runs if p.exists()]
    if runs:
        inputs.append(current_files_input(dep_key="m3_runs", paths=runs, extras={"from_batches": batches}))
    return inputs


def write_usage(path: Path, usage: MultiModelUsage, *, inputs, title: str) -> None:
    """``usage.json`` in the project's schema (``MultiModelUsage.as_dict``, which ``load_or_create`` reads back),
    with the run's provenance under a ``_provenance`` key beside it."""
    from assistant_axis.plot_metadata import json_metadata
    env = json_metadata(usage.as_dict(), title=title, inputs=inputs or None)
    atomic_write_text(json.dumps(usage.as_dict() | {"_provenance": env["_provenance"]}, indent=2, sort_keys=True) + "\n",
                      path)


def plan_line(plan: RG.GraphPlan, vinfo: dict, *, overlap_floor: float) -> dict:
    cos = list(plan.edges.values())
    ec = plan.edge_counts()
    out = {"n_candidates": len(plan.cands), "n_covered_shown": len(plan.covered), "selected_by_batch": plan.by_batch,
           "skipped": plan.skipped, "query_texts": vinfo, "no_vector": len(plan.no_vector),
           "n_relation_calls": ec["n_relation_calls"], "lists_split": ec["lists_split"],
           "n_listed": ec["n_listed"], "longest_list": ec["longest_list"], "n_candidate_edges": len(cos),
           "n_edges_at_overlap_floor": sum(1 for c in cos if c >= overlap_floor), "k": plan.k,
           "pair_floor": plan.pair_floor, "edges_by_via": ec["by_via"],
           "n_label_variant_pairs": ec["n_label_variant_pairs"], "n_relabel_pairs": ec["n_relabel_pairs"]}
    # plan 11: the stem-family pairs and the lexical blocks' edges and flags (no call), only when there are any
    if "n_family_pairs" in ec:
        out["n_family_pairs"] = ec["n_family_pairs"]
    lex = RG.lexical_counts_of_rows(plan.rows)
    if lex["n_edges"] or lex["candidates_by_flag"]:
        out["lexical"] = lex
    return out


def render_samples(runner: RG.ReviewRunner, plan: RG.GraphPlan, rubrics: dict) -> str:
    """The relation call of the candidate with the nearest neighbour and the overlap call of that pair, as the
    models receive them (the user turns; the system prompts are the rubric files)."""
    out = []
    if not plan.edges:
        return "(no candidate edge: no relation or overlap call to render)"
    (a, b), c = max(plan.edges.items(), key=lambda kv: (kv[1], kv[0]))
    if not plan.neighbours[a]:          # the pair came from b's list only
        a, b = b, a
    rc = runner.relation_calls([(a, [o for o, _ in plan.neighbours[a]])])[0]
    out.append(f"=== relation call: {a}, {len(rc.stems)} listed candidates, {rc.model}; system prompt: "
               f"rubrics/relation.md version {rubrics['relation']['version']}")
    out.append(rc.user)
    oc = runner.overlap_call(a, b, "sonnet", 1)
    out.append(f"=== overlap call: {a} > {b} (cosine {c:.3f}), {oc.model} then Opus by the rule at cut-off "
               f"{RG.CUT_OFF}; system prompt: rubrics/overlap_concept.md version {rubrics['overlap']['version']} (cached)")
    out.append(oc.user)
    return "\n".join(out)


# --------------------------------------------------------------------------- build

def cmd_build(args, argv) -> int:
    from assistant_axis.gapgen.metric_config import MetricConfig
    try:
        for b in [args.batch_id, *args.from_batches]:
            paths.check_id(b, "batch_id")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    out_dir = RG.review_dir(args.batch_id, candidates_dir=args.out_root)
    try:
        rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    except NS.RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    cfg = MetricConfig.load(args.metric_config)
    rows = Registry(args.registry).fold()
    present = {(r.get("novelty") or {}).get("run_id") for r in rows.values()}
    unknown = [b for b in args.from_batches if b not in present]
    if unknown:
        print(f"REFUSED: no registry row carries novelty.run_id {', '.join(unknown)} in {args.registry} (an M3 batch "
              "id, as novelty_score.py score --batch-id wrote it)", file=sys.stderr)
        return 2
    queue = load_queue(args.data_dir)
    cache = EM.EmbeddingCache(args.cache_dir)
    index, index_info = NS.load_index(cfg, data_dir=args.data_dir, cache=cache)
    include = {k: args.include_reason for k in (args.include or [])}
    if include:
        covered_keys = {k for k, r in rows.items() if (r.get("novelty") or {}).get("run_id") in set(args.from_batches)
                        and (r.get("novelty") or {}).get("decision") == "covered"}
        bad = sorted(k for k in include if k not in covered_keys)
        if bad:
            print(f"REFUSED: --include names keys that no batch of --from-batches decided covered: {', '.join(bad)}",
                  file=sys.stderr)
            return 2
    kept, _, _, _ = RG.select_rows(rows, args.from_batches, include=include)
    cands = {k: c for k, c in ((k, RG.pair_candidate(r)[0]) for k, r in kept.items()) if c is not None}
    if index is not None:
        vectors, vinfo = query_vectors(cands, cfg=cfg, index=index, cache=cache, query_form=args.query_form)
    else:
        vectors, vinfo = {}, {"n_query_texts": len(cands), "n_cached": None, "n_to_embed": len(cands),
                              "corpus_not_cached": index_info}
    corpus = index.traits if index is not None else NV.load_trait_corpus(args.data_dir)
    # plan 11: the stem-family candidate edges; a new build has them, a resume keeps its earlier session's setting (a
    # build before 2026-10-15 had none), unless --stem-family / --no-stem-family says otherwise
    if args.stem_family is None:
        earlier_run = NS._peek_run(out_dir) if (args.resume and out_dir.exists()) else None
        args.stem_family = (bool(((earlier_run or {}).get("settings") or {}).get("stem_family", False))
                            if args.resume and out_dir.exists() else True)
    plan = RG.plan_graph(rows, args.from_batches, vectors, k=args.k, cosine_floor=args.cosine_floor,
                         pair_floor=args.pair_floor, include=include, stem_family=args.stem_family)
    # the estimate's shares, tokens and unsure re-asks: an earlier R1 build's own records (gate audit 8), else M3's
    try:
        shares, tokens, unsure, calib = calibration(args.calibrate_from, args.out_root,
                                                    proposed_cut_off=args.proposed_cut_off)
    except CalibrationError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if shares is None:
        shares = RG.measured_shares(rows, args.from_batches, second_at=args.proposed_cut_off)
        tokens = RG.measured_overlap_tokens(source_records(args.from_batches, args.out_root))
    transport, why = choose_transport(args.transport, len(plan.cands))
    embedding = {"model": cfg.live_model["model_id"], "query_form": args.query_form,
                 "representation": cfg.representation, "variant": cfg.covered["space"]["variant"]}

    # a resume: the spend of the earlier sessions counts against the cap, and the estimate is the replay of the build
    # on its records with nothing sent (the calls not on record, and those they lead to by the shares)
    resuming = bool(args.resume and out_dir.exists())
    # the prompts' label form (prompt_labels): a resume keeps the earlier session's (a build before 2026-10-09
    # recorded none: "stored"), so that its answers on record are found; a new build shows the judge display form
    label_form = PL.resolve_label_form(earlier=NS._peek_run(out_dir) if resuming else None)
    spent_before = MultiModelUsage.load_or_create(out_dir / "usage.json").total_cost_usd if resuming else 0.0
    records_before: list = []
    if resuming and RF.exists(out_dir / "responses.jsonl"):
        records_before = RF.read_jsonl(out_dir / "responses.jsonl")
    resume_info: dict = {}

    def estimate(p: RG.GraphPlan, runner: RG.ReviewRunner, n_embed: int):
        runner.add_candidates(p.cands.values())
        if not resuming:
            return RG.estimate_build(relation_calls=runner.relation_calls(p.relation_items()),
                                     edge_cosines=p.edges.values(), shares=shares, overlap_floor=args.overlap_floor,
                                     overlap_tokens=tokens, transport=transport, cand_chars=_cand_chars(p.cands),
                                     n_embed=n_embed, unsure=unsure)
        replay = make_runner(client=None, batch_id=args.batch_id, rubrics=rubrics, index=runner.index,
                             usage=MultiModelUsage(), responses_path=out_dir / "responses.jsonl",
                             concurrency=args.concurrency, config_version=cfg.config_version, embedding=embedding,
                             resume_records=records_before, label_form=label_form)
        r_est, r_graph, wanted = RG.resume_estimate(
            p, runner=replay, corpus=corpus, queue=queue, shares=shares, overlap_floor=args.overlap_floor,
            proposed_cut_off=args.proposed_cut_off, overlap_tokens=tokens, transport=transport, unsure=unsure)
        if n_embed:
            r_est.add("query embeddings not in the cache (OpenAI text-embedding-3-large) + the 8 canary texts",
                      "text-embedding-3-large", 1, (n_embed + 8) * 30, 0)
        resume_info.clear()
        resume_info.update(records=len(records_before), spent_usd=round(spent_before, 4),
                           calls_not_on_record=dict(sorted(Counter(w["wave"] for w in wanted).items())),
                           replayed_graph={"complete": r_graph.complete,
                                           "stalled": {k: len(v) for k, v in r_graph.stalled.items()}})
        return r_est

    probe = make_runner(client=None, batch_id=args.batch_id, rubrics=rubrics,
                        index=index if index is not None else SimpleNamespace(traits=corpus), usage=MultiModelUsage(),
                        responses_path=out_dir / "responses.jsonl", concurrency=args.concurrency,
                        config_version=cfg.config_version, embedding=embedding, label_form=label_form)
    est = estimate(plan, probe, vinfo["n_to_embed"])
    pl = plan_line(plan, vinfo, overlap_floor=args.overlap_floor)
    print(f"plan: {json.dumps(pl)}")
    if "lexical" in pl or "n_family_pairs" in pl:
        print(f"lexical (plan 11; copied from the lexical blocks, no call; never a cut): "
              f"{json.dumps(pl.get('lexical') or {})}; stem-family candidate edges "
              f"{'on' if args.stem_family else 'off'}: {pl.get('n_family_pairs', 0)} pairs")
    if shares.source == "m3_blocks":
        print(f"shares (M3's, by cosine bin, from the source batches' blocks; {calib.get('why')}): "
              f"{json.dumps(shares.as_dict())}")
        print(f"overlap tokens a call (measured in the source batches' records): {json.dumps(tokens)}")
    else:
        print(f"shares (R1's own, by cosine bin, from {', '.join(calib['builds'])}): {json.dumps(shares.as_dict())}")
        print(f"overlap tokens a call and unsure re-asks (measured in {', '.join(calib['builds'])}'s records): "
              f"{json.dumps(tokens)}; unsure {json.dumps(calib['unsure'])}")
    if pl["lists_split"]:
        print(f"NOTE: {pl['lists_split']} candidates list more than {RG.RELATION_LIST_MAX} others (the longest "
              f"{pl['longest_list']}): each list is split over several relation calls of at most {RG.RELATION_LIST_MAX}, "
              f"so that no answer runs into the call's {NR.RELATION_MAX_TOKENS} output tokens")
    print(f"transport: {transport} ({why})")
    if resuming:
        print(f"resume: {json.dumps(resume_info)}")
    print(f"estimate{' of the calls not on record' if resuming else ''}:\n{est.format()}")
    print(f"total estimate = ${est.usd:.3f}" + (f"; with the ${spent_before:.3f} spent by the earlier sessions, "
                                                f"${spent_before + est.usd:.3f} against the cap" if resuming else ""))
    if vinfo["n_to_embed"]:
        print(f"NOTE: {vinfo['n_to_embed']} query texts (or the corpus) are not in the embedding cache: the estimate "
              "covers the cached candidates only; the run embeds the rest first and checks the estimate against the "
              "cap again before any LLM call")
    refused, cap = None, None
    try:
        cap = confirm_or_abort(spent_before + est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
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
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/ (never the registry)")
        print(render_samples(probe, plan, rubrics))
        return 0
    if refused:
        return 2
    status, resume_records, earlier = NS._prepare_out_dir(out_dir, args)
    if status:
        return status
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    inputs = provenance_inputs(args, rubrics)
    run_meta = {"batch_id": args.batch_id, "from_batches": list(args.from_batches), "git_sha": sha,
                "allow_dirty": bool(args.allow_dirty), "dirty_check": dirty_check,
                "argv": sys.argv[1:] if argv is None else list(argv), "plan": pl, "transport": transport,
                "transport_reason": why, "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "budget_usd": args.budget_usd, "cap_usd": cap, "confirmed_by": args.confirmed_by,
                "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")} for k, v in rubrics.items()},
                "models": {"relation": NR.RELATION_MODEL, "relation_unsure": NR.UNSURE_MODEL,
                           "overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
                "settings": {"k": args.k, "cosine_floor": args.cosine_floor, "pair_floor": args.pair_floor,
                             "label_variants": True, "relabel_pairs": True, "overlap_floor": args.overlap_floor,
                             "cut_off": RG.CUT_OFF, "proposed_cut_off": args.proposed_cut_off,
                             "rules": RG.RULES.name, "relation_seed": args.batch_id,
                             "concurrency": args.concurrency, "query_form": args.query_form,
                             "config_version": cfg.config_version, "embedding_model": cfg.live_model["model_id"],
                             "representation": cfg.representation, "variant": cfg.covered["space"]["variant"],
                             "relation_max_tokens": NR.RELATION_MAX_TOKENS, "overlap_max_tokens": NR.OVERLAP_MAX_TOKENS,
                             "ask_attempts": NR.ASK_ATTEMPTS, "stem_family": bool(args.stem_family)},
                "estimate_inputs": {"shares": shares.as_dict(), "overlap_tokens": tokens,
                                    "unsure": None if unsure is None else list(unsure), "calibration": calib},
                "corpus": index_info, PL.LABEL_FORM_KEY: label_form, "resumed": bool(args.resume),
                "started_at": utc_now()}
    if resuming:
        run_meta["resume_estimate"] = dict(resume_info)
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    if args.resume:
        usage.merge_from(MultiModelUsage.load_or_create(out_dir / "usage.json"))
    status, error, runner, graph = 0, None, None, None
    try:
        if index is None or vinfo["n_to_embed"]:
            if index is None:
                index, index_info = NS.load_index(cfg, data_dir=args.data_dir, cache=cache, usage=usage, allow_embed=True)
                corpus = index.traits
            vectors, vinfo = query_vectors(cands, cfg=cfg, index=index, cache=cache, query_form=args.query_form,
                                           usage=usage, allow_embed=True)
            plan = RG.plan_graph(rows, args.from_batches, vectors, k=args.k, cosine_floor=args.cosine_floor,
                                 pair_floor=args.pair_floor, include=include, stem_family=args.stem_family)
            probe.index, probe.traits = index, index.traits
            est = estimate(plan, probe, 0)
            run_meta.update(plan=plan_line(plan, vinfo, overlap_floor=args.overlap_floor), estimate_usd=round(est.usd, 4),
                            estimate_lines=[str(x) for x in est.lines], estimate_after_embedding=True)
            print(f"after embedding: total estimate = ${est.usd:.3f}")
            confirm_or_abort(spent_before + est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                             confirmed_by=args.confirmed_by)
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        runner = make_runner(client=anthropic.AsyncAnthropic(max_retries=0), batch_id=args.batch_id, rubrics=rubrics,
                             index=index, usage=usage, responses_path=out_dir / "responses.jsonl",
                             concurrency=args.concurrency, config_version=cfg.config_version, embedding=embedding,
                             resume_records=resume_records, label_form=label_form)
        if transport == "batches":
            runner.cache_ttl = NR.BATCH_CACHE_TTL
            runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap)

        def gate(pairs) -> None:
            # the second cost check: the overlap stage on the pairs actually marked for it (those not on record)
            todo = [c for a, b, c in pairs if not runner.on_record(runner.overlap_call(a, b, "sonnet", 1))]
            g_est = RG.estimate_overlap(todo, shares.all_similar(), overlap_floor=args.overlap_floor,
                                        overlap_tokens=tokens, transport=transport)
            spent = usage.total_cost_usd
            run_meta["gate"] = {"pairs": len(pairs), "pairs_not_on_record": len(todo), "spent_usd": round(spent, 4),
                                "overlap_estimate_usd": round(g_est.usd, 4), "cap_usd": cap,
                                "lines": [str(x) for x in g_est.lines]}
            print(f"after the relation calls: {len(pairs)} pairs for the overlap call ({len(todo)} not on record); "
                  f"spent ${spent:.3f}, overlap estimate ${g_est.usd:.3f}, cap ${cap:.2f}")
            if spent + g_est.usd > cap:
                raise RG.OverlapGateRefused(
                    f"the overlap stage would bring the spend to about ${spent + g_est.usd:.2f}, over the cap "
                    f"${cap:.2f}; the relation answers are on record: --resume with a --budget-usd of at least that")

        graph = RG.build_graph(plan, runner=runner, corpus=corpus, queue=queue, overlap_floor=args.overlap_floor,
                               config=graph_config(args, cfg, rubrics) | {PL.LABEL_FORM_KEY: label_form}
                               | ({"stem_family_pairs": "linked: a candidate edge whatever its cosine, typed by its "
                                   "readings (one stem family, from the lexical blocks)"} if args.stem_family else {}),
                               batch_id=args.batch_id, gate=gate,
                               proposed_cut_off=args.proposed_cut_off)
        graph.usage = usage.as_dict()
        atomic_write_text(json.dumps(RG.graph_envelope(graph, inputs=inputs), indent=2, ensure_ascii=False) + "\n",
                          out_dir / "graph.json")
    except (BudgetExceededError, RG.OverlapGateRefused, CostRefused) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised
        error = exc
        print(f"STOPPED by {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        write_usage(out_dir / "usage.json", usage, inputs=inputs, title=f"review_graph build {args.batch_id}")
        run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status,
                        stopped_by_error=f"{type(error).__name__}: {error}" if error is not None else None)
        if runner is not None:
            run_meta["calls_sent"] = {k.split(":", 1)[1]: v for k, v in sorted(runner.stats.items())
                                      if k.startswith("sent:")}
            run_meta["calls_resumed"] = runner.stats.get("resumed", 0)
            run_meta["parse_rates"] = runner.warn_parse_rates(logger)
        if graph is not None:
            run_meta.update(complete=graph.complete, graph_stats=graph.stats, stalled=graph.stalled)
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        logging.getLogger().removeHandler(fh)
        fh.close()
        print(usage.log_line())
    if graph is not None:
        s = graph.stats
        print(f"graph: {s['n_candidates']} candidates, {s['candidate_edges']['n']} candidate edges "
              f"{json.dumps(s['candidate_edges']['by_relation'])}, {s['overlap']['four_edges']} 4-edges, "
              f"{s['cliques']['n']} merged groups {json.dumps(s['cliques']['by_size'])}, "
              f"{s['proposed_groups']['n']} proposed groups {json.dumps(s['proposed_groups']['by_size'])}, "
              f"{s['ungrouped']} candidates in no group; {out_dir / 'graph.json'}")
        if not graph.complete:
            print(f"INCOMPLETE: {json.dumps({k: len(v) for k, v in graph.stalled.items()})} left without an answer; "
                  "run again with --resume")
    return status


# --------------------------------------------------------------------------- groups

def _print_groups(title: str, groups, links, nodes, top) -> None:
    sizes = Counter(len(c) for c in groups)
    print(f"{title}: {len(groups)} (sizes {', '.join(f'{s}: {sizes[s]}' for s in sorted(sizes, reverse=True)) or 'none'})")
    opp: dict[int, list] = {}
    for lk in links:
        i, j = lk["cliques"]
        opp.setdefault(i, []).append(j)
        opp.setdefault(j, []).append(i)
    for i, c in enumerate(groups if top is None else groups[:top]):
        line = f"  [{i}] {len(c)}: {', '.join(nodes[m].label for m in c)}"
        if opp.get(i):
            line += f"  (opposed to {', '.join(f'[{j}]' for j in sorted(opp[i]))})"
        print(line)
    if top is not None and len(groups) > top:
        print(f"  ... {len(groups) - top} more")


def cmd_groups(args) -> int:
    p = RG.review_dir(args.batch_id, candidates_dir=args.out_root) / "graph.json"
    if not RF.exists(p):
        print(f"{p} not found: run build --batch-id {args.batch_id} first", file=sys.stderr)
        return 1
    g = RG.Graph.from_json(RF.read_json(p))
    nodes = g.node_map()
    loose = g.ungrouped()
    print(f"{g.batch_id} (from {', '.join(g.from_batches)}): {len(g.candidate_keys())} candidates, "
          f"{len(g.cliques)} merged groups, {len(g.proposed_groups)} proposed groups, {len(loose)} in no group"
          + ("" if g.complete else "  (INCOMPLETE: resume the build)")
          + ("" if g.schema >= 2 else "  (schema 1: built before decision 12, no proposed groups; resume the build)"))
    _print_groups("merged groups (4-edges both ways)", g.cliques, g.clique_links, nodes, args.top)
    _print_groups(f"proposed groups ({g.config.get('proposed_cut_off', RG.DEFAULT_PROPOSED_CUT_OFF)}-edges both ways, "
                  "none wholly inside a merged group)", g.proposed_groups, g.proposed_links, nodes, args.top)
    by_gen = Counter(nodes[k].generator for k in loose)
    print(f"in no group, by generator: {json.dumps(dict(sorted(by_gen.items(), key=lambda kv: str(kv[0]))))}")
    return 0


# --------------------------------------------------------------------------- the Opus pilot (gate audit 8, P2)

def roger_labels(review: Path, graph: RG.Graph) -> tuple[dict, dict]:
    """``(labels, info)``: each term the review's ``decisions.jsonl`` settled, by the resolution it ended in
    (``review_graph.resolution_labels`` over the log replayed by the review app; the log's own groups only)."""
    from assistant_axis.gapgen.review_app import decisions as RD
    events = RD.read_events(review / RD.LOG_NAME)
    st = RD.replay(graph, events)
    groups = [{"id": g.id, "resolution": g.resolution, "nominated": g.nominated,
               "resolved_members": list(g.resolved_members)} for g in st.groups.values() if g.status == "resolved"]
    labels = RG.resolution_labels(groups, stem_of={n.key: n.stem for n in graph.nodes})
    return labels, {"events": len(events), "skipped_on_replay": len(st.skipped), "groups_resolved": len(groups),
                    "terms_settled": len(labels), "resolutions": len(set(labels.values()))}


def cmd_opus_pilot(args, argv) -> int:
    try:
        paths.check_id(args.batch_id, "batch_id")
        paths.check_id(args.pilot_id, "pilot_id")
    except ValueError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    review = RG.review_dir(args.batch_id, candidates_dir=args.out_root)
    if not RF.exists(review / "graph.json"):
        print(f"{review / 'graph.json'} not found: the pilot reads a built graph", file=sys.stderr)
        return 1
    graph = RG.Graph.from_json(RF.read_json(review / "graph.json"))
    build_run = NS._peek_run(review) or {}
    labels, linfo = roger_labels(review, graph)
    if not labels:
        print(f"REFUSED: {review / 'decisions.jsonl'} settles no term: the pilot's reference is Roger's decisions",
              file=sys.stderr)
        return 2
    pairs = RG.sonnet2_pairs(graph)
    sel = RG.select_pilot(pairs, labels, args.n, seed=args.seed)
    chosen = [(p["a"], p["b"]) for p in sel["selected"]]
    try:
        rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    except NS.RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    built = ((build_run.get("rubrics") or {}).get("overlap") or {}).get("sha256")
    refused = None
    if built and built != rubrics["overlap"]["sha256"]:
        refused = (f"the overlap rubric is not the one the build used (sha256 {rubrics['overlap']['sha256'][:12]} "
                   f"now, {built[:12]} in {args.batch_id}): Opus would not read what Sonnet read")
    label_form = PL.resolve_label_form(source=build_run)
    pilot_dir = review / args.pilot_id
    records = read_records(review / "responses.jsonl", steps=("overlap",))
    recorded = {(r["key"], r["stem"]): r["user"] for r in records
                if r.get("role") == "sonnet" and str(r.get("wave", "")).startswith(RG.FIRST_WAVE) and r.get("user")}
    tokens = RG.measured_overlap_tokens(records)
    nodes = graph.node_map()
    probe = make_runner(client=None, batch_id=args.batch_id, rubrics=rubrics, index=SimpleNamespace(traits={}),
                        usage=MultiModelUsage(), responses_path=pilot_dir / "responses.jsonl", concurrency=args.concurrency,
                        config_version=graph.config.get("space", {}).get("config_version", ""),
                        embedding=build_run.get("embedding") or {}, label_form=label_form)
    probe.add_candidates(RG.node_candidate(nodes[k]) for k in sorted({m for p in chosen for m in p}))
    mismatches = RG.pilot_prompt_mismatches(probe, chosen, recorded)
    if mismatches and refused is None:
        refused = (f"{len(mismatches)} of the {len(chosen)} pairs render a prompt Sonnet did not read (first: "
                   f"{mismatches[0]}); Opus must read what Sonnet read")
    transport = args.transport
    suffix = RG.BATCH_SUFFIX if transport == "batches" else ""
    est = RG.Estimate()
    est.add(f"Opus on first directions Sonnet read 2 ({len(chosen)} pairs; tokens measured in {args.batch_id})",
            NR.SECOND_MODEL + suffix, len(chosen), *tokens["opus"])
    print(f"reference: {json.dumps(linfo)}")
    print(f"first directions Sonnet read 2 (Opus never asked): {len(pairs)}; pools: {json.dumps(sel['pools'])}")
    print(f"selected: {sum(p['reference'] == 'same' for p in sel['selected'])} same, "
          f"{sum(p['reference'] == 'different' for p in sel['selected'])} different (seed {args.seed}); by cosine bin "
          + json.dumps({b: dict(Counter(p['reference'] for p in sel['selected'] if RG.bin_label(p['cosine']) == b))
                        for b in sorted({RG.bin_label(p['cosine']) for p in sel['selected']})}))
    print(f"label form: {label_form}; overlap rubric version {rubrics['overlap']['version']}; prompts checked against "
          f"the build's Sonnet records: {len(chosen) - len(mismatches)} of {len(chosen)} match")
    print(f"estimate:\n{est.format()}")
    cap = None
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=False, confirmed_by=None)
        print(f"hard cap: ${cap:.2f}")
    except CostRefused as exc:
        refused = refused or exc.msg
    sha, dirty = git_sha(), platform_dirty_files()
    if refused is None and dirty and not args.allow_dirty:
        refused = (f"uncommitted changes to the platform's own code or prompt paths ({len(dirty)}: "
                   f"{'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass --allow-dirty")
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {pilot_dir}/ (graph.json, the groups and the registry untouched)")
        if chosen:
            c = probe.overlap_call(*chosen[0], "opus", 1)
            print(f"=== Opus call: {chosen[0][0]} > {chosen[0][1]}, {c.model}; system prompt: "
                  f"rubrics/overlap_concept.md version {rubrics['overlap']['version']} (cached)\n{c.user}")
        return 0
    if refused:
        print(f"REFUSED: {refused}", file=sys.stderr)
        return 2
    status, resume_records, earlier = NS._prepare_out_dir(pilot_dir, args)
    if status:
        return status
    usage = GuardedUsage(budget_usd=cap, usage_path=pilot_dir / "usage.json")
    if args.resume:
        usage.merge_from(MultiModelUsage.load_or_create(pilot_dir / "usage.json"))
    from assistant_axis.provenance import current_file_input
    inputs = [current_file_input(dep_key="graph", path=RF.current_path(review / "graph.json")),
              current_file_input(dep_key="decisions", path=review / "decisions.jsonl")]
    run_meta = {"batch_id": args.batch_id, "pilot_id": args.pilot_id, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "argv": sys.argv[1:] if argv is None else list(argv), "n": args.n, "seed": args.seed,
                "transport": transport, "estimate_usd": round(est.usd, 4), "budget_usd": args.budget_usd, "cap_usd": cap,
                "reference": linfo, "pools": sel["pools"], "label_form": label_form,
                "rubric": {k: rubrics["overlap"][k] for k in ("name", "version", "sha256")}, "model": NR.SECOND_MODEL,
                "started_at": utc_now()}
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", pilot_dir / "run.json")
    status, runner, res = 0, None, {}
    try:
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        runner = make_runner(client=anthropic.AsyncAnthropic(max_retries=0), batch_id=args.batch_id, rubrics=rubrics,
                             index=SimpleNamespace(traits={}), usage=usage, responses_path=pilot_dir / "responses.jsonl",
                             concurrency=args.concurrency, config_version=probe.config_version,
                             embedding=probe.embedding, resume_records=resume_records, label_form=label_form)
        if transport == "batches":
            runner.cache_ttl = NR.BATCH_CACHE_TTL
            runner.transport = BatchTransport(runner, anthropic.Anthropic(), pilot_dir / "batches.json", budget_usd=cap)
        runner.add_candidates(RG.node_candidate(nodes[k]) for k in sorted({m for p in chosen for m in p}))
        res = runner.run_opus(chosen)
    except (BudgetExceededError, CostRefused) as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    finally:
        write_usage(pilot_dir / "usage.json", usage, inputs=inputs, title=f"review_graph opus-pilot {args.batch_id}")
        edges = {(e.a, e.b): e for e in graph.edges if e.source == "r1"}
        rows = []
        for p in sel["selected"]:
            got = res.get((p["a"], p["b"])) or {"stalled": "not answered"}
            ab = edges[(p["a"], p["b"])].readings.get("ab") or {}
            rows.append({**p, "label_a": nodes[p["a"]].label, "label_b": nodes[p["b"]].label,
                         "resolution_a": labels[p["a"]], "resolution_b": labels[p["b"]],
                         "sonnet": ab.get("sonnet"), "sonnet_reason": (ab.get("reasons") or {}).get("sonnet"), **got})
        atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), pilot_dir / "readings.jsonl")
        rep = RG.pilot_report(rows, pools=sel["pools"], graph=graph, labels=labels)
        from assistant_axis.plot_metadata import json_metadata
        atomic_write_text(json.dumps(json_metadata(rep, title=f"Opus pilot {args.batch_id}/{args.pilot_id}",
                                                   inputs=inputs), indent=2) + "\n", pilot_dir / "report.json")
        run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status)
        if runner is not None:
            run_meta["calls_sent"] = {k.split(":", 1)[1]: v for k, v in sorted(runner.stats.items())
                                      if k.startswith("sent:")}
            run_meta["calls_resumed"] = runner.stats.get("resumed", 0)
            run_meta["parse_rates"] = runner.warn_parse_rates(logger)
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", pilot_dir / "run.json")
        print(usage.log_line())
    print(RG.format_pilot_report(rep))
    print(f"written: {pilot_dir}/ (readings.jsonl, report.json, usage.json, responses.jsonl, run.json)")
    return status


# --------------------------------------------------------------------------- the parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="the candidate graph of M3 batches (relation and overlap calls)")
    b.add_argument("--batch-id", required=True, help="this review batch (data/candidates/review/<B>/)")
    b.add_argument("--from-batches", nargs="+", required=True, help="the M3 batch ids whose kept candidates to group")
    b.add_argument("--k", type=int, default=RG.DEFAULT_K, help="nearest other candidates per candidate (default 10)")
    b.add_argument("--cosine-floor", type=float, default=RG.DEFAULT_COSINE_FLOOR,
                   help="retrieval floor among candidates (default 0.25, M3's)")
    b.add_argument("--pair-floor", type=floor_or_none, default=RG.DEFAULT_PAIR_FLOOR,
                   help="beside the k nearest, every pair at this cosine or above is a candidate edge (default 0.55, "
                        "Roger 2026-10-12 after gate audit 8); 'none': the k nearest alone, the rule before")
    b.add_argument("--calibrate-from", nargs="+", metavar="REVIEW_BATCH", default=None,
                   help="earlier R1 builds whose own records (graph.json, responses.jsonl) give the estimate's shares, "
                        "tokens and unsure re-asks (default review_tda_1, or M3's shares when it is not there); "
                        "'none': M3's shares from the source batches' blocks, the rule before")
    b.add_argument("--overlap-floor", type=float, default=RG.DEFAULT_OVERLAP_FLOOR,
                   help="no overlap call on a pair below this cosine (default 0.35, decision 11)")
    b.add_argument("--proposed-cut-off", type=int, choices=(3, 4), default=RG.DEFAULT_PROPOSED_CUT_OFF,
                   help="the reading (both ways) of a proposed group's edges, and of a first direction that sends "
                        "the second (default 3, decision 12; the merged groups' cut-off stays 4)")
    b.add_argument("--include", nargs="+", metavar="KEY", default=None,
                   help="covered candidates (registry keys) to review anyway, as ordinary terms with their covering "
                        "trait shown (Roger, 2026-10-09, after the M3 cover audit)")
    b.add_argument("--include-reason", default="included by hand",
                   help="why the --include keys are reviewed (recorded on their nodes)")
    b.add_argument("--stem-family", action=argparse.BooleanOptionalAction, default=None,
                   help="two kept candidates of one stem family (their lexical blocks, plan 11) are a candidate edge "
                        "whatever their cosine, typed by its readings (default: on for a new build; a --resume keeps "
                        "its earlier session's, off for a build from before 2026-10-15)")
    b.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    b.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    b.add_argument("--out-root", type=Path, default=None, help="candidates dir holding review/<B>/ and novelty/<M3>/")
    b.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    b.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    b.add_argument("--rubrics-dir", type=Path, default=None)
    b.add_argument("--query-form", choices=NV.QUERY_FORMS, default=NV.DEFAULT_QUERY_FORM,
                   help="how a candidate is embedded (default gloss_w14, as M3 embedded it)")
    b.add_argument("--transport", choices=("auto", "live", "batches"), default="auto")
    b.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    b.add_argument("--budget-usd", type=float, required=True, help="the hard cap")
    b.add_argument("--confirm-expensive", action="store_true")
    b.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    b.add_argument("--resume", action="store_true", help="continue the batch's directory; no call answered is sent again")
    b.add_argument("--overwrite", action="store_true", help="move an existing directory to <dir>.bak.<UTC> first")
    b.add_argument("--allow-dirty", action="store_true")
    b.add_argument("--dry-run", action="store_true", help="print the plan, the estimate and the prompts; write nothing")
    g = sub.add_parser("groups", help="the merged and proposed groups of a built graph, largest first (no call)")
    g.add_argument("--batch-id", required=True)
    g.add_argument("--out-root", type=Path, default=None)
    g.add_argument("--top", type=int, default=None, help="list only the N largest groups of each tier")
    p = sub.add_parser("opus-pilot", help="Opus on first directions Sonnet read 2, against Roger's decisions "
                                          "(gate audit 8, P2; the graph untouched)")
    p.add_argument("--batch-id", required=True, help="the built review batch (its graph.json and decisions.jsonl)")
    p.add_argument("--n", type=int, default=RG.PILOT_SIZE, help="pairs to read (default 128: half same resolution, "
                                                                "half different)")
    p.add_argument("--seed", type=int, default=RG.PILOT_SEED, help="the draw's seed (default 20261012)")
    p.add_argument("--pilot-id", default="opus_pilot_1", help="the output directory under the review batch's")
    p.add_argument("--out-root", type=Path, default=None)
    p.add_argument("--rubrics-dir", type=Path, default=None)
    p.add_argument("--transport", choices=("live", "batches"), default="live",
                   help="live by default (under $20: real time); batches at half price")
    p.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    p.add_argument("--budget-usd", type=float, required=True, help="the hard cap")
    p.add_argument("--resume", action="store_true", help="continue the pilot's directory; nothing answered is sent")
    p.add_argument("--overwrite", action="store_true", help="move an existing pilot directory aside first")
    p.add_argument("--allow-dirty", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="print the selection, the estimate and a prompt; write nothing")
    return ap


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if args.cmd == "build":
        return cmd_build(args, argv)
    if args.cmd == "opus-pilot":
        return cmd_opus_pilot(args, argv)
    return cmd_groups(args)


if __name__ == "__main__":
    sys.exit(main())
