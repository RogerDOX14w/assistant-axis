#!/usr/bin/env python3
"""M3, the novelty check: does the corpus already have each candidate trait?

    uv run python data_analysis/gap_generation/novelty_score.py <command> ...

The brief is ``reports/trait_gap_generation/coding_plan_m3.md``; the logic is
:mod:`assistant_axis.gapgen.novelty`, the waves :mod:`assistant_axis.gapgen.novelty_runner`.

Commands:

* ``score --batch-id B (--run GEN/RUN [--run ...] | --keys K ... | --unscored)``: M3 on the registry rows
  whose filter verdict is ``trait`` (with a gloss): the exact-label check, retrieval in the covered setting of
  ``metric_config.json`` (OpenAI ``text-embedding-3-large``, direct key; the 8 canary texts re-embedded first),
  arrangement expansion, the relation call (Haiku 4.5, ``rubrics/relation.md``; ``unsure`` to Sonnet 5.5), the
  overlap call (rubric A as pinned, one pair per call, Sonnet 5.5 then Opus 5.5 by the rule, early exit), the
  decision.  Writes the ``novelty`` block of every decided row through the Registry API (once per run and key;
  a resume skips the rows already decided in the run) and ``data/candidates/novelty/<B>/``: ``responses.jsonl``,
  ``results.jsonl`` (every decided candidate's block), ``readings.jsonl`` (one line per pair judged, beside its
  cosine), ``summary.json``, ``decisions.md`` (the table for Roger to sample from), ``usage.json``, ``run.json``,
  ``run.log`` and, with the batches transport, ``batches.json``.  Rows held on a list (nationalities) are left
  out unless ``--include-held``; rows already decided by another run unless ``--rescore``.
* ``full-scan --batch-id S --from-batch B [--sample 100 --sample-seed 0]``: the pilot's check on the shortlist:
  the overlap call on every listed trait of a seeded sample of B's candidates (those that reached the relation
  call), no relation call, no shortlist, no early exit, Opus on the pairs the rule sends it; the walk is replayed
  on the readings afterwards.  Writes only its own run directory, never the registry.
* ``compare --scan-batch S --main-batch B``: what the shortlist missed (pairs the full scan put at the cut-off or
  above that the relation call did not mark similar), what early exit skipped, and the decisions side by side:
  ``<S>/comparison.json`` and ``comparison.md``.  No call.
* ``decisions --batch-id B``: write ``decisions.md`` again from ``results.jsonl``.  No call.
* ``review-list [--batch-id B] [--include-new]``: the review queue (``grey`` rows) in ``review_order``.  No call.
* ``pools --out-dir DIR [--n-m1 150 --seed 0]``: the pilot's two candidate pools (``novelty_pools``).  No call.
* ``estimate --n-candidates N [--n-scan 100]``: the plan's estimate by stage before any candidate exists.
* ``render --key K | --stand-in STEM``: the relation and overlap requests for one candidate, rendered as the
  models receive them (from cached embeddings only; no call).  ``--stand-in`` takes a corpus trait, its M1
  gloss from the validation run and its cached M2 query embedding, with its own trait hidden.

Cost: ``score`` and ``full-scan`` print the estimate by stage (``n_calls x (in, out) tokens at model rates``),
``--budget-usd`` is the hard cap (default $5; an estimate over it is refused), and a budget or estimate over $20
needs ``--confirm-expensive`` and ``--confirmed-by``.  ``--dry-run`` prints the plan, the estimate and the first
rendered prompt and writes and calls nothing.  A paid run is refused while the platform's code or prompt paths
have uncommitted changes, unless ``--allow-dirty`` (recorded).  ``--transport auto`` sends fewer than 300
candidates live and more through the Message Batches API (half price, the 1-hour cache on the rubric).
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import overlap_test as OT  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import split_rubrics as sr  # noqa: E402
from assistant_axis.gapgen.batches import AUTO_BATCH_FROM, BatchTransport, choose_transport  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.registry import Registry, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, platform_dirty_files, \
    log_formatter  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage  # noqa: E402

logger = logging.getLogger("novelty_score")

DEFAULT_SCAN_SAMPLE = 100
PILOT_POOLS_DIR = paths.DATA_CANDIDATES / "pools" / "m3_pilot"


# --------------------------------------------------------------------------- inputs

class RubricError(RuntimeError):
    pass


def load_m3_rubrics(rubrics_dir: Optional[Path] = None) -> dict:
    """The overlap rubric (A, ``overlap_concept``, as pinned) and the relation rubric (``relation``, as pinned);
    refuses a text that is not its latest pin."""
    try:
        a = OT.load_rubrics(rubrics_dir, keys=[NV.OVERLAP_RUBRIC])[NV.OVERLAP_RUBRIC]
    except OT.RubricPinError as exc:
        raise RubricError(str(exc)) from exc
    if a.get("form") != "single":
        raise RubricError(f"rubric A version {a['version']} is the list form; M3 sends one pair per call (version 5 on)")
    probs = [p for p in sr.mismatches(rubrics_dir) if p.split(":", 1)[0] in sr.M3_NAMES]
    if probs:
        raise RubricError("; ".join(probs) + "\n" + sr.bump_command(probs))
    pins = sr.current_versions(rubrics_dir, sr.M3_NAMES)
    text = sr.load_prompt(NV.RELATION_RUBRIC, rubrics_dir)
    rel = {"name": NV.RELATION_RUBRIC, "text": text, "version": pins[NV.RELATION_RUBRIC][0], "sha256": sr.sha256(text)}
    return {"overlap": {k: a[k] for k in ("name", "text", "version", "sha256")}, "relation": rel}


def parse_run(value: str) -> tuple[str, str]:
    gen, sep, run_id = value.partition("/")
    if not sep:
        raise argparse.ArgumentTypeError("--run takes GENERATOR/RUN_ID")
    paths.check_id(gen, "generator")
    paths.check_id(run_id, "run_id")
    return gen, run_id


def select_candidates(rows: dict, args, *, batch_id: str) -> tuple[list[NR.M3Candidate], dict]:
    """The candidates of ``score``, and why every other selected row was left out."""
    from assistant_axis.gapgen.registry import has_source
    if args.keys:
        missing = [k for k in args.keys if k not in rows]
        if missing:
            raise SystemExit(f"not in the registry: {', '.join(missing[:10])}")
        sel = [rows[k] for k in args.keys]
    elif args.run:
        sel = [r for k, r in sorted(rows.items()) if any(has_source(r, g, rid) for g, rid in args.run)]
    else:
        sel = [r for k, r in sorted(rows.items()) if not r.get("novelty")]
    out, skipped = [], Counter()
    for r in sel:
        nv = r.get("novelty") or {}
        if nv.get("run_id") == batch_id and nv.get("decision"):
            skipped["decided_in_this_run"] += 1
            continue
        if nv.get("decision") and nv.get("run_id") and not args.rescore:
            skipped["decided_by_another_run"] += 1
            continue
        cand, why = NR.candidate_from_row(r)
        if cand is None:
            skipped[why] += 1
            continue
        if r.get("holding") and not args.include_held:
            skipped[f"held_{r['holding']}"] += 1
            continue
        out.append(cand)
    if args.limit:
        out = out[:args.limit]
    return out, dict(skipped)


def load_index(cfg, *, data_dir: Path, cache, usage=None, allow_embed: bool = False) -> tuple[NV.CorpusIndex, dict]:
    """The corpus in the covered setting from the embedding cache (``label: description`` in the covered
    representation); a text missing from the cache is embedded only with ``allow_embed`` (charged)."""
    import numpy as np
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.representation import represent
    traits = NV.load_trait_corpus(data_dir)
    cov = cfg.covered
    rep, variant = cov["representation"], cov["space"]["variant"]
    if cov.get("metric") != "cos":
        raise SystemExit(f"covered.metric {cov.get('metric')!r}: M3 retrieves by cosine")
    live = cfg.live_model
    if live["arm"] != "openai":
        raise SystemExit(f"live model arm {live['arm']!r}: M3 embeds with OpenAI (the config's live model)")
    embedder = EM.OpenAIEmbedder(live["model_id"])
    stems = sorted(traits)
    texts = [represent(traits[s].label, traits[s].description, rep) for s in stems]
    found, missing = cache.lookup(embedder.tag, texts)
    info = {"n_corpus": len(stems), "n_missing_from_cache": len(missing),
            "missing": [stems[i] for i in missing][:20]}
    if missing:
        if not allow_embed:
            return None, info
        E = EM.embed_texts(embedder, texts, cache=cache, usage=usage)
    else:
        E = np.stack([found[i] for i in range(len(stems))])
    settings = {"config_version": cfg.config_version, "model": live["model_id"], "cache_tag": embedder.tag,
                "representation": rep, "variant": variant, "metric": "cos", "k": cfg.k}
    return NV.build_index(traits, E, variant=variant, settings=settings), info


def label_sets_for(data_dir: Path) -> NV.LabelSets:
    """Stage 0's names, from the trait files and the seed queue (no embedding needed)."""
    import data_analysis.seed_entities as se
    queue = se.load_queue(Path(data_dir) / "seed_queue.json")
    return NV.label_sets(NV.load_trait_corpus(data_dir), queue)


# --------------------------------------------------------------------------- writing

def write_blocks(reg: Registry, states, run_id: str) -> int:
    """The novelty block of every newly decided candidate, through the Registry API, once per (run, key)."""
    cur = reg.fold()
    updates = {}
    for st in states:
        key = st.cand.key
        nv = (cur.get(key) or {}).get("novelty") or {}
        if key not in cur or (nv.get("run_id") == run_id and nv.get("decision")):
            continue
        updates[key] = {"novelty": st.block}
    if updates:
        reg.update_many(updates, merge_blocks=False)
    return len(updates)


def _md(s) -> str:
    return str("" if s is None else s).replace("|", "\\|").replace("\n", " ")


def _trait_link(stem: Optional[str], label: Optional[str] = None, rel: str = "../../../traits/instructions/") -> str:
    if not stem:
        return ""
    return f"[{_md(label or stem.replace('_', ' '))}]({rel}{stem}.json)"


def _reading_text(r) -> str:
    if not r:
        return ""
    s = (r.get("sonnet") or {}).get("value")
    o = (r.get("opus") or {}).get("value") if r.get("opus") else None
    return f"Sonnet {s}" + (f", Opus {o}" if r.get("opus") else "")


def decisions_markdown(results: list[dict], *, batch_id: str, labels: dict, mode: str = "shortlist") -> str:
    """``decisions.md``: every candidate (label, decision, covered_by, cut-off, the readings that decided it,
    review flags, pair completions), then the review queue with both readings and reasons, then the pair
    completions.  Trait names link to their files (paths relative to ``data/candidates/novelty/<batch>/``)."""
    order = {"covered": 0, "grey": 1, "new": 2}
    rows = sorted(results, key=lambda r: (order.get(r["novelty"]["decision"], 9), str(r["label"]).lower()))
    n = Counter(r["novelty"]["decision"] for r in results)
    lines = [f"# M3 decisions: `{batch_id}`" + (" (full scan)" if mode == "full_scan" else ""), "",
             f"{len(results)} candidates: " + ", ".join(f"{n[d]} {d}" for d in ("covered", "grey", "new") if n[d]) + ".  "
             "Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  "
             "The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  "
             "Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.", "",
             "| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | "
             "pairs judged | gloss |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        nv = r["novelty"]
        cov = nv.get("covered_by")
        how = "exact label" if nv["reason"] == "exact_label" else _reading_text(nv.get("deciding_reading"))
        if nv["reason"] == "exact_label" and nv.get("exact_label"):
            how += f" ({nv['exact_label'].get('match')})"
        pcf = ", ".join(_trait_link(s, labels.get(s)) for s in nv.get("pair_completion_for") or [])
        lines.append(f"| {_md(r['label'])} | {nv['decision']} | {_trait_link(cov, labels.get(cov)) if cov in labels else _md(cov)} | "
                     f"{nv['cut_off']} | {_md(how)} | {_md(', '.join(nv.get('review') or []))} | {pcf} | "
                     f"{nv.get('n_pairs_judged', 0)} | {_md(r.get('gloss'))} |")
    grey = [r for r in rows if r["novelty"]["decision"] == "grey"]
    lines += ["", f"## Review queue ({len(grey)} grey rows)", ""]
    for r in grey:
        nv = r["novelty"]
        lines += [f"### {_md(r['label'])} (`{r['key']}`), cut-off {nv['cut_off']}: {', '.join(nv['review'])}", "",
                  f"Gloss: {_md(r.get('gloss'))}", ""]
        for d in nv.get("review_details") or []:
            if d["kind"] == "sonnet_below_opus_at":
                lines.append(f"- {_trait_link(d['stem'], labels.get(d['stem']))}: Sonnet {d['sonnet']['value']} "
                             f"(\"{_md(d['sonnet'].get('reason'))}\"), Opus {d['opus']['value']} "
                             f"(\"{_md(d['opus'].get('reason'))}\")")
            elif d["kind"] == "pair_flag":
                a, b = d["pair"]
                lines.append(f"- pair {_trait_link(a, labels.get(a))} / {_trait_link(b, labels.get(b))}: both "
                             f"{d['both']} in the relation call")
            else:
                lines.append(f"- unparsed: {_md(json.dumps({k: v for k, v in d.items() if k != 'kind'}))}")
        lines.append("")
    pc = [r for r in rows if r["novelty"].get("pair_completion_for")]
    lines += [f"## Pair completions ({len(pc)} candidates)", "",
              "A candidate opposed to a trait that has no recorded partner (a `non-X` placeholder or a one-way pointer): "
              "the candidate may be that trait's missing antonym (design item 4: a find, not a drop).", ""]
    for r in pc:
        nv = r["novelty"]
        lines.append(f"- {_md(r['label'])} ({nv['decision']}): " +
                     ", ".join(_trait_link(s, labels.get(s)) for s in nv["pair_completion_for"]))
    return "\n".join(lines) + "\n"


def finalize(*, out_dir: Path, runner: NR.NoveltyRunner, usage, run_meta: dict, skipped: dict, status: int,
             error: Optional[BaseException], inputs: list) -> dict:
    from assistant_axis.plot_metadata import json_metadata
    usage.write_json(out_dir / "usage.json")
    rp = out_dir / "results.jsonl"
    earlier = [json.loads(x) for x in rp.read_text(encoding="utf-8").splitlines() if x.strip()] if rp.exists() else []
    results = NR.merge_results(earlier, NR.result_rows(runner.states))
    decided = {r["key"] for r in results}
    stalled = {k: st.stalled for k, st in runner.states.items() if st.block is None and k not in decided}
    readings = [x for r in results for x in NV.reading_rows(runner.batch_id, {"key": r["key"], "label": r["label"]},
                                                              r["novelty"])]
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results), rp)
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in readings), out_dir / "readings.jsonl")
    parse_rates = runner.warn_parse_rates(logger)
    summary = NR.summarize(results, runner.records, usage, stalled=stalled, skipped=skipped, mode=runner.mode)
    summary.update({"batch_id": runner.batch_id, "parse_rates": parse_rates, "stopped_by_budget": status == 2,
                    "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                    "resumed_calls": runner.stats.get("resumed", 0), "rubrics": runner.rubric_pins})
    env = json_metadata(summary, title=f"novelty_score {runner.mode} {runner.batch_id}", inputs=inputs or None)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "summary.json")
    labels = {s: t.label for s, t in runner.traits.items()}
    atomic_write_text(decisions_markdown(results, batch_id=runner.batch_id, labels=labels, mode=runner.mode),
                      out_dir / "decisions.md")
    run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status,
                    stopped_by_error=summary["stopped_by_error"], n_decided=summary["n_decided"],
                    n_stalled=summary["n_stalled"])
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    print(usage.log_line())
    print(json.dumps({k: summary[k] for k in ("n_candidates", "n_decided", "n_stalled", "by_decision", "review_flags",
                                              "pair_completions", "spend_usd")}))
    return summary


# --------------------------------------------------------------------------- score and full-scan

def _common_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--batch-id", required=True)
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--out-root", type=Path, default=None, help="candidates dir holding novelty/<batch_id>/")
    ap.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    ap.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    ap.add_argument("--rubrics-dir", type=Path, default=None)
    ap.add_argument("--query-form", choices=NV.QUERY_FORMS, default=NV.DEFAULT_QUERY_FORM,
                    help="how a candidate is embedded: gloss_w14 (default; metric_config.json's covered.query_form: the "
                         "gloss alone, 14 words, the form M2 measured recall on) or label_gloss (label: gloss, in the "
                         "covered representation)")
    ap.add_argument("--transport", choices=("auto", "live", "batches"), default="auto",
                    help=f"auto (default) sends fewer than {AUTO_BATCH_FROM} candidates live, more through the Message "
                         "Batches API")
    ap.add_argument("--resume", action="store_true", help="continue an existing run dir; no call already answered is sent")
    ap.add_argument("--overwrite", action="store_true", help="move an existing run dir to <dir>.bak.<UTC> first")
    ap.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    ap.add_argument("--budget-usd", type=float, default=5.0)
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", help="who gave the explicit go for a budget over $20 (recorded in run.json)")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")


def _prepare_out_dir(out_dir: Path, args) -> tuple[int, list, Optional[dict]]:
    """``(status, resume_records, earlier_run)``; status 1 when the dir exists and neither flag says what to do."""
    records, earlier = [], None
    if out_dir.exists():
        if args.resume:
            rp = out_dir / "responses.jsonl"
            if rp.exists():
                records = [json.loads(x) for x in rp.read_text(encoding="utf-8").splitlines() if x.strip()]
            if (out_dir / "run.json").exists():
                earlier = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
            print(f"resuming {out_dir}: {len(records)} responses on record", file=sys.stderr)
        elif args.overwrite:
            bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
            shutil.move(str(out_dir), str(bak))
            print(f"moved the old run to {bak}", file=sys.stderr)
        else:
            print(f"{out_dir} exists; choose a new --batch-id, pass --resume to continue it, or --overwrite",
                  file=sys.stderr)
            return 1, [], None
    elif args.resume:
        print(f"--resume: {out_dir} does not exist", file=sys.stderr)
        return 1, [], None
    out_dir.mkdir(parents=True, exist_ok=True)
    return 0, records, earlier


def _mean_chars(index: NV.CorpusIndex) -> float:
    import numpy as np
    return float(np.mean([len(t.label) + len(t.description) + 40 for t in index.traits.values()]))


def _cand_chars(cands) -> float:
    import numpy as np
    return float(np.mean([len(c.label) + len(c.gloss) + 40 for c in cands])) if cands else 140.0


def run_scoring(args, argv, *, mode: str) -> int:
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.provenance import current_file_input, current_files_input
    paths.check_id(args.batch_id, "batch_id")
    out_dir = paths.novelty_dir(args.batch_id, candidates_dir=args.out_root)
    try:
        rubrics = load_m3_rubrics(args.rubrics_dir)
    except RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    cfg = MetricConfig.load(args.metric_config)
    reg = Registry(args.registry)
    rows = reg.fold()
    if mode == "shortlist":
        cands, skipped = select_candidates(rows, args, batch_id=args.batch_id)
    else:
        cands, skipped = select_scan_sample(rows, args)
    if not cands:
        print(f"nothing to score ({json.dumps(skipped)})", file=sys.stderr)
        return 0
    cache = EM.EmbeddingCache(args.cache_dir)
    index, index_info = load_index(cfg, data_dir=args.data_dir, cache=cache)
    if index is None:
        print(f"{index_info['n_missing_from_cache']} corpus texts are not in the embedding cache "
              f"(first: {index_info['missing'][:5]}); they would be embedded (charged) by the run", file=sys.stderr)
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = {c.key: NV.query_text(c.label, c.gloss, query_form=args.query_form, representation=cfg.representation)
             for c in cands}
    found, miss = cache.lookup(embedder.tag, list(texts.values()))
    sets = label_sets_for(args.data_dir)
    n_exact = sum(1 for c in cands if NV.exact_label_match(c.stem, sets)) if mode == "shortlist" else 0
    n_live = len(cands) - n_exact
    transport, why = choose_transport(args.transport, n_live)
    # the estimate: real listed sizes where every candidate's vector is cached, else the corpus's own
    listed_mean = None
    if index is not None and not miss:
        sizes = []
        for i in range(len(texts)):
            q = index.project(found[i])
            sizes.append(len(NV.expand(index.retrieve(q, cfg.k), index.traits, lambda s, q=q: index.cosine_to(q, s))))
        listed_mean = sum(sizes) / len(sizes)
    elif index is not None:
        listed_mean = NR.mean_listed_size(index, cfg.k)
    stages = NR.plan_estimate(n_candidates=n_live if mode == "shortlist" else 0, n_scan=len(cands) if mode == "full_scan" else 0,
                              mean_listed=listed_mean or 16.0, relation_text_chars=len(rubrics["relation"]["text"]),
                              trait_chars=_mean_chars(index) if index is not None else 260.0,
                              cand_chars=_cand_chars(cands), transport=transport, n_embed=len(miss))
    use = ("embeddings", "relation", "overlap") if mode == "shortlist" else ("embeddings", "full_scan")
    est = Estimate(lines=[x for s in use for x in stages[s].lines])
    plan = {"mode": mode, "n_candidates": len(cands), "n_exact_label": n_exact, "n_to_relation": n_live if mode == "shortlist" else 0,
            "skipped": skipped, "transport": transport, "query_form": args.query_form, "listed_mean": listed_mean,
            "n_query_texts_cached": len(found), "n_query_texts_to_embed": len(miss), "corpus": index_info}
    print(f"plan: {json.dumps(plan)}")
    print(f"transport: {transport} ({why})")
    print("estimate by stage:")
    for s in use:
        print(f" [{s}] ${stages[s].usd:.3f}\n{stages[s].format()}")
    print(f"total estimate = ${est.usd:.3f}")
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
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        print(f"DRY-RUN: would write {out_dir}/" + (f" and the registry {args.registry}" if mode == "shortlist" else ""))
        print(f"rubrics: {json.dumps({k: {'name': v['name'], 'version': v['version'], 'sha256': v['sha256'][:12]} for k, v in rubrics.items()})}")
        first = next((i for i, c in enumerate(cands) if i in found and not (sets and NV.exact_label_match(c.stem, sets))),
                     None)
        if index is not None and first is not None:
            print(render_for(cands[first], found[first], index, rubrics, args.batch_id, cfg.k))
        else:
            print("(no rendered prompt: no candidate's query embedding is cached yet; the run embeds them first)")
        return 0
    if refused:
        return 2
    status, resume_records, earlier = _prepare_out_dir(out_dir, args)
    if status:
        return status
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    run_meta = {"batch_id": args.batch_id, "mode": mode, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv, "plan": plan,
                "transport": transport, "transport_reason": why, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by, "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")}
                                                               for k, v in rubrics.items()},
                "models": {"relation": NR.RELATION_MODEL, "relation_unsure": NR.UNSURE_MODEL, "overlap_first": NR.FIRST_MODEL,
                           "overlap_second": NR.SECOND_MODEL},
                "settings": {"config_version": cfg.config_version, "k": cfg.k, "representation": cfg.representation,
                             "variant": cfg.covered["space"]["variant"], "query_form": args.query_form,
                             "embedding_model": cfg.live_model["model_id"],
                             "cut_off_rule": "alignment score 0-1: 3; 2-3: 4; missing: 4",
                             "relation_max_tokens": NR.RELATION_MAX_TOKENS, "overlap_max_tokens": NR.OVERLAP_MAX_TOKENS,
                             "temperature": NR.TEMPERATURE, "cache_ttl_batches": NR.BATCH_CACHE_TTL,
                             "concurrency": args.concurrency, "ask_attempts": NR.ASK_ATTEMPTS},
                "resumed": bool(args.resume), "started_at": utc_now()}
    if mode == "full_scan":
        run_meta["full_scan"] = {"from_batch": args.from_batch, "sample": args.sample, "sample_seed": args.sample_seed}
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")

    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    if args.resume:
        from assistant_axis.gapgen.batches import with_current_batch_keys
        usage.merge_from(with_current_batch_keys(MultiModelUsage.load_or_create(out_dir / "usage.json")))
    inputs = [current_file_input(dep_key="metric_config", path=args.metric_config),
              current_files_input(dep_key="rubrics", paths=[paths.RUBRICS_DIR / "overlap_concept.md",
                                                            paths.RUBRICS_DIR / "relation.md"])]
    status, error, runner = 0, None, None
    try:
        if index is None:
            index, index_info = load_index(cfg, data_dir=args.data_dir, cache=cache, usage=usage, allow_embed=True)
        canary = EM.check_canary(embedder, cfg.canary["texts"], cache, usage=usage)
        run_meta["canary"] = canary
        keys = [c.key for c in cands]
        E = EM.embed_texts(embedder, [texts[k] for k in keys], cache=cache, usage=usage)
        vectors = dict(zip(keys, E))
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)

        def on_decided(states) -> None:
            if mode == "shortlist":
                n = write_blocks(reg, states, args.batch_id)
                logger.info("registry: %d novelty blocks written", n)

        runner = NR.NoveltyRunner(client=client, batch_id=args.batch_id, rubrics=rubrics, index=index, label_sets=sets,
                                  usage=usage, responses_path=out_dir / "responses.jsonl", k=cfg.k, mode=mode,
                                  config_version=cfg.config_version, concurrency=args.concurrency,
                                  embedding={"model": cfg.live_model["model_id"], "query_form": args.query_form,
                                             "representation": cfg.representation,
                                             "variant": cfg.covered["space"]["variant"], "k": cfg.k},
                                  resume_records=resume_records, on_decided=on_decided)
        if transport == "batches":
            runner.cache_ttl = NR.BATCH_CACHE_TTL
            runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap)
        runner.run(cands, vectors)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        status = 2
    except BaseException as exc:  # noqa: BLE001 - recorded, then re-raised
        error = exc
        print(f"STOPPED by {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
    finally:
        if runner is not None:
            finalize(out_dir=out_dir, runner=runner, usage=usage, run_meta=run_meta, skipped=skipped, status=status,
                     error=error, inputs=inputs)
        else:
            usage.write_json(out_dir / "usage.json")
            run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status)
            atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        logging.getLogger().removeHandler(fh)
        fh.close()
    return status


def select_scan_sample(rows: dict, args) -> tuple[list[NR.M3Candidate], dict]:
    """The full scan's candidates: a seeded sample of ``--sample`` of the main run's candidates that reached the
    relation call (reason ``overlap``), read from its ``results.jsonl``; their glosses from the registry."""
    main = paths.novelty_dir(args.from_batch, candidates_dir=args.out_root) / "results.jsonl"
    if not main.exists():
        raise SystemExit(f"{main} not found: run score --batch-id {args.from_batch} first")
    res = [json.loads(x) for x in main.read_text(encoding="utf-8").splitlines() if x.strip()]
    eligible = sorted(r["key"] for r in res if r["novelty"]["reason"] == "overlap")
    n = min(args.sample, len(eligible))
    pick = sorted(random.Random(args.sample_seed).sample(eligible, n))
    out, skipped = [], Counter()
    for k in pick:
        cand, why = NR.candidate_from_row(rows[k]) if k in rows else (None, "not_in_registry")
        if cand is None:
            skipped[why] += 1
        else:
            out.append(cand)
    return out, {"eligible_in_main": len(eligible), **skipped}


def render_for(cand: NR.M3Candidate, e_raw, index: NV.CorpusIndex, rubrics: dict, batch_id: str, k: int,
               *, exclude: tuple = ()) -> str:
    """The relation request and the first overlap request for one candidate, as the models receive them."""
    from assistant_axis.gapgen.llm import request_params
    q = index.project(e_raw)
    listed = NV.expand(index.retrieve(q, k, exclude=exclude), index.traits, lambda s: index.cosine_to(q, s))
    order = NV.relation_order([x.stem for x in listed], batch_id, cand.key)
    user = NV.render_relation_user(cand.label, cand.gloss, [(index.traits[s].label, index.traits[s].description)
                                                            for s in order])
    p = request_params(model=NR.RELATION_MODEL, system=rubrics["relation"]["text"], user=user,
                       max_tokens=NR.RELATION_MAX_TOKENS, temperature=NR.TEMPERATURE, cache_system=False)
    head = {k2: v for k2, v in p.items() if k2 not in ("system", "messages")}
    first = listed[0].stem
    pc = OT.PairCall(call_id=f"{cand.key}>{first}", set="m3", target=cand.key, listed=[first])
    ou = OT.render_single(pc, {cand.key: {"label": cand.label, "description": cand.gloss},
                               first: {"label": index.traits[first].label, "description": index.traits[first].description}})
    po = request_params(model=NR.FIRST_MODEL, system=rubrics["overlap"]["text"], user=ou,
                        max_tokens=NR.OVERLAP_MAX_TOKENS, temperature=NR.TEMPERATURE, cache_system=True)
    ohead = {k2: v for k2, v in po.items() if k2 not in ("system", "messages")}
    listing = "\n".join(f"  {x.stem}: cosine {x.cosine:.3f}, {x.via}" + (f" rank {x.rank}" if x.rank else
                                                                           f" from {', '.join(x.expanded_from)}")
                        + (f", partners {', '.join(x.partners)}" if x.partners else "") for x in listed)
    return (f"=== candidate {cand.key} ({cand.label}), {len(listed)} listed traits (not shown to the model) ===\n{listing}\n"
            f"=== relation call, request settings {json.dumps(head)} ===\n--- system (relation v{rubrics['relation']['version']}) ---\n"
            f"{rubrics['relation']['text']}\n--- user ---\n{user}\n"
            f"=== overlap call on the nearest trait, request settings {json.dumps(ohead)}, system block cache_control "
            f"{json.dumps(po['system'][0].get('cache_control'))} ===\n--- user ---\n{ou}\n")


# --------------------------------------------------------------------------- compare

def compare_runs(scan: list[dict], main: list[dict]) -> dict:
    """The full scan against the main run (see the module docstring)."""
    by_main = {r["key"]: r for r in main}
    pairs, decisions, skipped_exit, consistency = [], [], [], Counter()
    for r in scan:
        nv = r["novelty"]
        m = by_main.get(r["key"])
        mnv = (m or {}).get("novelty") or {}
        rel = {x["stem"]: x.get("relation") for x in mnv.get("listed") or []}
        short = set(mnv.get("shortlist") or [])
        main_read = {x["stem"]: x for x in mnv.get("readings") or []}
        for p in nv.get("scan") or []:
            row = {"key": r["key"], "label": r["label"], "stem": p["stem"], "cosine": p["cosine"], "rank": p["rank"],
                   "via": p["via"], "cut_off": nv["cut_off"], "verdict": p["verdict"], "at_or_above": p["at_or_above"],
                   "sonnet": (p["sonnet"] or {}).get("value"), "opus": (p.get("opus") or {}).get("value"),
                   "main_relation": rel.get(p["stem"]), "in_main_shortlist": p["stem"] in short}
            pairs.append(row)
            mr = main_read.get(p["stem"])
            if mr and mr.get("sonnet") and p.get("sonnet"):
                consistency["both_read"] += 1
                consistency["sonnet_same"] += int(mr["sonnet"].get("value") == p["sonnet"].get("value"))
        decisions.append({"key": r["key"], "label": r["label"], "scan": nv["decision"], "scan_covered_by": nv.get("covered_by"),
                          "main": mnv.get("decision"), "main_covered_by": mnv.get("covered_by"),
                          "cut_off": nv["cut_off"], "scan_review": nv.get("review"), "main_review": mnv.get("review")})
        # what early exit skipped: in the scan's cosine order, the pairs after the walk's exit
        exit_at = (nv.get("deciding_reading") or {}).get("stem")
        if exit_at:
            seen = False
            for p in sorted(nv.get("scan") or [], key=lambda p: -p["cosine"]):
                if seen:
                    skipped_exit.append({"key": r["key"], "label": r["label"], "stem": p["stem"], "verdict": p["verdict"],
                                         "at_or_above": p["at_or_above"]})
                seen = seen or p["stem"] == exit_at
    at = [p for p in pairs if p["at_or_above"]]
    cut = [p for p in pairs if p["verdict"] == "cut"]
    miss_at = [p for p in at if p["main_relation"] != "similar"]
    miss_cut = [p for p in cut if p["main_relation"] != "similar"]
    miss_cut_short = [p for p in cut if not p["in_main_shortlist"]]
    dec = Counter((d["main"], d["scan"]) for d in decisions)
    return {
        "n_candidates": len(scan), "n_pairs": len(pairs),
        "relation_recall": {
            "pairs_at_or_above_cut_off": len(at), "of_which_not_marked_similar": len(miss_at),
            "recall_at_or_above": round(1 - len(miss_at) / len(at), 4) if at else None,
            "pairs_cut_by_the_rule": len(cut), "cut_not_marked_similar": len(miss_cut),
            "recall_cut": round(1 - len(miss_cut) / len(cut), 4) if cut else None,
            "cut_not_in_main_shortlist": len(miss_cut_short),
            "main_relation_of_misses": dict(Counter(str(p["main_relation"]) for p in miss_at)),
            "misses": miss_at},
        "decisions": {"main_vs_scan": {f"{a} -> {b}": n for (a, b), n in sorted(dec.items(), key=str)},
                      "scan_covered_main_not": [d for d in decisions if d["scan"] == "covered" and d["main"] != "covered"],
                      "main_covered_scan_not": [d for d in decisions if d["main"] == "covered" and d["scan"] != "covered"],
                      "rows": decisions},
        "early_exit": {"pairs_after_exit": len(skipped_exit),
                       "after_exit_by_verdict": dict(Counter(p["verdict"] for p in skipped_exit)),
                       "after_exit_at_or_above": sum(1 for p in skipped_exit if p["at_or_above"]),
                       "rows": skipped_exit},
        "sonnet_self_consistency": {**consistency, "rate": round(consistency["sonnet_same"] / consistency["both_read"], 4)
                                    if consistency["both_read"] else None},
        "pairs": pairs,
    }


def comparison_markdown(c: dict, *, scan_batch: str, main_batch: str) -> str:
    rr = c["relation_recall"]
    lines = [f"# Full scan `{scan_batch}` against `{main_batch}`", "",
             f"{c['n_candidates']} candidates, {c['n_pairs']} pairs read in the scan.", "",
             "## What the relation call's shortlist missed", "",
             f"- Pairs the scan put at the cut-off or above (either model): {rr['pairs_at_or_above_cut_off']}; the relation "
             f"call did not mark {rr['of_which_not_marked_similar']} of them similar (recall {rr['recall_at_or_above']}).",
             f"- Pairs the rule would cut on: {rr['pairs_cut_by_the_rule']}; not marked similar {rr['cut_not_marked_similar']} "
             f"(recall {rr['recall_cut']}); not in the main shortlist at all {rr['cut_not_in_main_shortlist']}.",
             f"- The relation call's answers on the misses: {json.dumps(rr['main_relation_of_misses'])}.", "",
             "| candidate | trait | cosine | cut-off | Sonnet | Opus | verdict | relation call |", "|---|---|---|---|---|---|---|---|"]
    for p in rr["misses"]:
        lines.append(f"| {_md(p['label'])} | {_trait_link(p['stem'], rel='../../../traits/instructions/')} | {p['cosine']:.3f} | "
                     f"{p['cut_off']} | {p['sonnet']} | {p['opus'] if p['opus'] is not None else ''} | {p['verdict']} | "
                     f"{p['main_relation']} |")
    d = c["decisions"]
    lines += ["", "## Decisions, main run against the scan", "", "| main -> scan | candidates |", "|---|---|"]
    for k, n in d["main_vs_scan"].items():
        lines.append(f"| {k} | {n} |")
    lines += ["", "## What early exit skipped", "",
              f"{c['early_exit']['pairs_after_exit']} pairs after the covering pair, by verdict: "
              f"{json.dumps(c['early_exit']['after_exit_by_verdict'])}; at the cut-off or above: "
              f"{c['early_exit']['after_exit_at_or_above']}.", "",
              f"Sonnet's answer on the pairs read in both runs: {json.dumps(c['sonnet_self_consistency'])}.", ""]
    return "\n".join(lines)


def cmd_compare(args) -> int:
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input
    sd = paths.novelty_dir(args.scan_batch, candidates_dir=args.out_root)
    md = paths.novelty_dir(args.main_batch, candidates_dir=args.out_root)
    read = lambda p: [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]  # noqa: E731
    c = compare_runs(read(sd / "results.jsonl"), read(md / "results.jsonl"))
    env = json_metadata(c, title=f"novelty_score compare {args.scan_batch} {args.main_batch}",
                        inputs=[current_file_input(dep_key="scan_results", path=sd / "results.jsonl"),
                                current_file_input(dep_key="main_results", path=md / "results.jsonl")])
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", sd / "comparison.json")
    atomic_write_text(comparison_markdown(c, scan_batch=args.scan_batch, main_batch=args.main_batch), sd / "comparison.md")
    print(json.dumps({k: v for k, v in c["relation_recall"].items() if k != "misses"}))
    print(json.dumps(c["decisions"]["main_vs_scan"]))
    return 0


# --------------------------------------------------------------------------- small commands

def cmd_decisions(args) -> int:
    d = paths.novelty_dir(args.batch_id, candidates_dir=args.out_root)
    res = [json.loads(x) for x in (d / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    traits = NV.load_trait_corpus(args.data_dir)
    mode = res[0]["novelty"].get("mode", "shortlist") if res else "shortlist"
    atomic_write_text(decisions_markdown(res, batch_id=args.batch_id, labels={s: t.label for s, t in traits.items()},
                                         mode=mode), d / "decisions.md")
    print(f"wrote {d / 'decisions.md'} ({len(res)} candidates)")
    return 0


def cmd_review_list(args) -> int:
    rows = Registry(args.registry).fold()
    order = NV.review_order(rows.values(), include_new=args.include_new, run_id=args.batch_id)
    print("| section | key | label | decision | review | cut-off | gloss |")
    print("|---|---|---|---|---|---|---|")
    for sec, key in order:
        r = rows[key]
        nv = r["novelty"]
        print(f"| {sec} | {key} | {_md(r['label'])} | {nv['decision']} | {', '.join(nv.get('review') or [])} | "
              f"{nv['cut_off']} | {_md(r.get('gloss'))} |")
    return 0


def cmd_pools(args) -> int:
    from assistant_axis.gapgen.novelty_pools import build_pilot_pools
    rec = build_pilot_pools(_REPO_ROOT, args.out_dir, n_m1=args.n_m1, seed=args.seed)
    print(json.dumps(rec, indent=2))
    return 0


def cmd_estimate(args) -> int:
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    cfg = MetricConfig.load(args.metric_config)
    index, info = load_index(cfg, data_dir=args.data_dir, cache=EM.EmbeddingCache(args.cache_dir))
    if index is None:
        raise SystemExit(f"corpus not in the embedding cache: {info}")
    rubrics = load_m3_rubrics(args.rubrics_dir)
    mean_listed = NR.mean_listed_size(index, cfg.k)
    stages = NR.plan_estimate(n_candidates=args.n_candidates, n_scan=args.n_scan, mean_listed=mean_listed,
                              relation_text_chars=len(rubrics["relation"]["text"]), trait_chars=_mean_chars(index),
                              cand_chars=args.cand_chars, transport=args.transport)
    total = 0.0
    print(f"mean listed traits a candidate (each corpus trait as the query, itself left out): {mean_listed:.2f}")
    for s, e in stages.items():
        print(f"[{s}] ${e.usd:.3f}\n{e.format()}")
        total += e.usd
    print(f"total ${total:.3f}")
    return 0


def cmd_render(args) -> int:
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.gapgen.retrieval import query_text as gloss_query
    cfg = MetricConfig.load(args.metric_config)
    cache = EM.EmbeddingCache(args.cache_dir)
    index, info = load_index(cfg, data_dir=args.data_dir, cache=cache)
    if index is None:
        raise SystemExit(f"corpus not in the embedding cache: {info}")
    rubrics = load_m3_rubrics(args.rubrics_dir)
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    if args.key:
        row = Registry(args.registry).fold()[args.key]
        cand, why = NR.candidate_from_row(row)
        if cand is None:
            raise SystemExit(f"{args.key}: {why}")
        text = NV.query_text(cand.label, cand.gloss, query_form=args.query_form, representation=cfg.representation)
        exclude: tuple = ()
    else:
        stem = args.stand_in
        res = paths.DATA_CANDIDATES / "filter" / "m1_validation" / "results.jsonl"
        row = next((json.loads(x) for x in res.read_text(encoding="utf-8").splitlines()
                    if x.strip() and json.loads(x).get("key") == f"{stem}#1"), None)
        if row is None or not row.get("gloss"):
            raise SystemExit(f"{stem}: no M1 gloss in {res}")
        cand = NR.M3Candidate(key=f"{stem}#1", stem=stem, label=row["label"], gloss=row["gloss"],
                              alignment_score=(row.get("filter") or {}).get("alignment"), region=None)
        text = gloss_query(cand.gloss)   # the M2 round-4 query form, whose embeddings are cached
        exclude = (stem,)
    v = cache.get(embedder.tag, text)
    if v is None:
        raise SystemExit(f"the query text of {cand.key} is not in the embedding cache (no paid call here): {text!r}")
    print(render_for(cand, v, index, rubrics, args.batch_id or "render", cfg.k, exclude=exclude))
    return 0


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("score", help="M3 on registry rows")
    _common_args(sp)
    g = sp.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", type=parse_run, action="append", help="GENERATOR/RUN_ID (repeatable)")
    g.add_argument("--keys", nargs="+")
    g.add_argument("--unscored", action="store_true", help="every row with no novelty block")
    sp.add_argument("--rescore", action="store_true", help="also rows another run has decided (their block is replaced)")
    sp.add_argument("--include-held", action="store_true", help="also rows on a holding list (nationalities)")
    sp.add_argument("--limit", type=int)
    sp.set_defaults(func=lambda a, argv: run_scoring(a, argv, mode="shortlist"))
    sp = sub.add_parser("full-scan", help="the overlap call on every listed trait of a sample (no registry writes)")
    _common_args(sp)
    sp.add_argument("--from-batch", required=True)
    sp.add_argument("--sample", type=int, default=DEFAULT_SCAN_SAMPLE)
    sp.add_argument("--sample-seed", type=int, default=0)
    sp.set_defaults(func=lambda a, argv: run_scoring(a, argv, mode="full_scan"))
    sp = sub.add_parser("compare")
    sp.add_argument("--scan-batch", required=True)
    sp.add_argument("--main-batch", required=True)
    sp.add_argument("--out-root", type=Path, default=None)
    sp.set_defaults(func=lambda a, argv: cmd_compare(a))
    sp = sub.add_parser("decisions")
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--out-root", type=Path, default=None)
    sp.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    sp.set_defaults(func=lambda a, argv: cmd_decisions(a))
    sp = sub.add_parser("review-list")
    sp.add_argument("--batch-id", default=None)
    sp.add_argument("--include-new", action="store_true")
    sp.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    sp.set_defaults(func=lambda a, argv: cmd_review_list(a))
    sp = sub.add_parser("pools")
    sp.add_argument("--out-dir", type=Path, default=PILOT_POOLS_DIR)
    sp.add_argument("--n-m1", type=int, default=150)
    sp.add_argument("--seed", type=int, default=0)
    sp.set_defaults(func=lambda a, argv: cmd_pools(a))
    for name, func in (("estimate", cmd_estimate), ("render", cmd_render)):
        sp = sub.add_parser(name)
        sp.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
        sp.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
        sp.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
        sp.add_argument("--rubrics-dir", type=Path, default=None)
        if name == "estimate":
            sp.add_argument("--n-candidates", type=int, required=True)
            sp.add_argument("--n-scan", type=int, default=DEFAULT_SCAN_SAMPLE)
            sp.add_argument("--cand-chars", type=float, default=140.0, help="mean characters of a candidate's label and gloss")
            sp.add_argument("--transport", choices=("live", "batches"), default="live")
        else:
            g = sp.add_mutually_exclusive_group(required=True)
            g.add_argument("--key")
            g.add_argument("--stand-in", help="a corpus stem standing in for a candidate (its M1 gloss, itself hidden)")
            sp.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
            sp.add_argument("--query-form", choices=NV.QUERY_FORMS, default=NV.DEFAULT_QUERY_FORM)
            sp.add_argument("--batch-id", default=None)
        sp.set_defaults(func=lambda a, argv, f=func: f(a))
    return ap


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args, argv)


if __name__ == "__main__":
    sys.exit(main())
