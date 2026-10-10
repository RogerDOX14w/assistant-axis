#!/usr/bin/env python3
"""The alignment sweep (workstream 8, generator id ``alignment_sweep``).

    uv run python data_analysis/gap_generation/alignment_sweep.py fetch [--only KEY ...] [--force] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py chunk [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py extract --run-id R --variant A|B [--chunks N --seed S]
        [--sources KEY ...] [--reuse-from RUN] [--render CHUNK_ID ...] [--budget-usd 4] [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py dedupe --run-id R [--threshold T | --tune]
        [--pairs-for-labeling N] [--embedder openai|hash] [--budget-usd 1] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py submit --run-id R [--budget-usd 5]
        [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py gate --run-id R [--gold-only] [--budget-usd 1.5]
        [--allow-dirty] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py probe --run-id R [--budget-usd 0.5] [--dry-run]
    uv run python data_analysis/gap_generation/alignment_sweep.py report --run-id R [--gold] [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_08_alignment_sweep.md``.  ``fetch`` downloads the sources into
``data/external/alignment_sweep/`` (git-ignored) with a manifest (also tracked as
``data/candidates/alignment_sweep/sources_manifest.json``); ``chunk`` splits them into ``chunks.jsonl``; ``extract``
asks Sonnet 5.5 for the dispositions of each chunk and rewrites mechanism items; ``dedupe`` groups the glosses;
``submit`` writes the run's ``candidates.jsonl`` and submits it; ``gate`` and ``probe`` add the enactability
verdicts and the Qwen label probe; ``report`` writes the readout.  Every paid command prints its estimate, takes
``--budget-usd`` as a hard cap, writes ``usage.json``, refuses uncommitted platform code without ``--allow-dirty``,
and runs live (every estimate is under the $20 line).  ``--dry-run`` prints the plan, the estimate and the first
three prompts as sent, and writes and calls nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import alignment_sweep as AS  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep import chunk as CH  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep import fetch as F  # noqa: E402
from assistant_axis.gapgen.generators.alignment_sweep.sources import SOURCES  # noqa: E402


def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


# --------------------------------------------------------------------------- fetch, chunk

def cmd_fetch(args) -> int:
    man = F.fetch_all(only=args.only, force=args.force, dry_run=args.dry_run, dest_root=args.external_dir,
                      sources_manifest_path=args.sources_manifest, git_sha=None if args.dry_run else _git_sha(),
                      fetcher=F._urlopen_bytes)
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost):")
        for line in man.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in man.entries:
        print(f"{e['key']:22s} {e['size_bytes']:>8d} B  sha256 {e['sha256'][:16]}...  {e['license'] or 'no licence'}"
              f"{' (read-only)' if e['read_only'] else ''}  pin {e['version_pin']}  {e['file']}")
        print(f"{'':22s} licence line found: {e.get('license_line_found')!r}")
    print(f"fetched: {', '.join(man.fetched) or 'none'}; already present: {', '.join(man.skipped) or 'none'}")
    for p in man.written:
        print(f"wrote {p}")
    return 0


def cmd_chunk(args) -> int:
    manifest = F.load_manifest(Path(args.external_dir) / AS.FETCH_MANIFEST_NAME)
    if not manifest:
        raise SystemExit(f"no {AS.FETCH_MANIFEST_NAME} in {args.external_dir}: run `alignment_sweep.py fetch` first")
    chunks = CH.build_all(manifest, max_tokens=args.max_tokens)
    for k, v in CH.counts(chunks).items():
        print(f"{k:22s} {v['n_chunks']:>4d} chunks  ~{v['n_tokens_est']:>7,d} tokens  (largest ~{v['max_tokens_est']:,d})")
    out = Path(args.external_dir) / AS.CHUNKS_NAME
    if args.dry_run:
        print(f"DRY-RUN: would write {out}")
        return 0
    CH.write_chunks(chunks, out)
    print(f"wrote {out} ({len(chunks)} chunks)")
    return 0


# --------------------------------------------------------------------------- shared

def _anthropic_client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def _run_dir(args, run_id: str) -> Path:
    paths.check_id(run_id, "run_id")
    return paths.run_dir(AS.GENERATOR, run_id, candidates_dir=args.candidates_dir)


def _dirty_refusal(args) -> Optional[str]:
    """The refusal for uncommitted platform code (paid commands), or None."""
    from assistant_axis.gapgen.runs import platform_dirty_files
    dirty = platform_dirty_files()
    if dirty and not args.allow_dirty:
        return (f"uncommitted platform code ({'; '.join(d.strip() for d in dirty[:5])}); commit first, or pass "
                f"--allow-dirty")
    return None


def _load_chunks(args) -> list:
    p = Path(args.external_dir) / AS.CHUNKS_NAME
    if not p.exists():
        raise SystemExit(f"no {p}: run `alignment_sweep.py chunk` first")
    return CH.load_chunks(p)


def _print_estimate(lines: list[tuple[str, dict]], budget: float) -> float:
    total = 0.0
    for label, e in lines:
        print(f"  {label}: {e['n_calls']} calls x ~{(e['in_tok'] // max(1, e['n_calls'])):,} in / "
              f"~{(e['out_tok'] // max(1, e['n_calls'])):,} out tokens = ${e['usd']:.3f}")
        total += e["usd"]
    print(f"  total estimate ${total:.3f}; cap --budget-usd ${budget:.2f}")
    return total


# --------------------------------------------------------------------------- extract

def _select_chunks(args, chunks: list) -> list:
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.generators.alignment_sweep.sources import VARIANT_B_SOURCES
    if args.variant == "A":
        keys = {k for k, s in SOURCES.items() if s.variant == "A"}
    else:
        keys = set(VARIANT_B_SOURCES)
    if args.sources:
        keys &= set(args.sources)
    pool = [c for c in chunks if c.source in keys]
    if args.variant == "B" and "krakovna" in keys and not args.dry_run and not args.render:
        from assistant_axis.gapgen.generators.alignment_sweep.fetch import fetch_transient
        from assistant_axis.gapgen.registry import utc_now
        pool += CH.chunk_source("krakovna", fetch_transient("krakovna"), version=utc_now()[:10])
    if args.chunks:
        pool = X.stratified_sample(pool, args.chunks, args.seed)
    return pool


def cmd_extract(args) -> int:
    import asyncio

    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, LABEL_FORM_KEY
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate

    all_chunks = _load_chunks(args)
    ordinals = X.chunk_ordinals(all_chunks)
    if args.render:
        by = {c.chunk_id: c for c in all_chunks}
        missing = [c for c in args.render if c not in by]
        if missing:
            raise SystemExit(f"unknown chunk id(s): {', '.join(missing)}")
        rub = X.load_rubric(X.RUBRIC_EXTRACT, args.rubrics_dir, allow_unpinned=True)
        print(f"SYSTEM (rubric {rub['name']} version {rub['version']}, the fenced block of {rub['file']}):\n"
              f"{rub['text']}\n")
        for cid in args.render:
            print(f"USER ({cid}):\n{X.render_user(by[cid])}\n")
        return 0
    if args.render_rewrite:
        items = X.load_extraction(_run_dir(args, args.run_id) / X.EXTRACTION_NAME)
        by = {it.item_id: it for it in items}
        heads = {c.chunk_id: c.heading for c in all_chunks}
        rub = X.load_rubric(X.RUBRIC_REWRITE, args.rubrics_dir, allow_unpinned=True)
        print(f"SYSTEM (rubric {rub['name']} version {rub['version']}):\n{rub['text']}\n")
        for iid in args.render_rewrite:
            named = by[iid]
            print(f"USER ({named.pair_id}):\n"
                  f"{X.render_rewrite_user(named, by[named.partner_item_id], heading=heads.get(named.chunk_id))}\n")
        return 0
    if not args.run_id:
        raise SystemExit("extract needs --run-id")
    chunks = _select_chunks(args, all_chunks)
    try:
        rub_x = X.load_rubric(X.RUBRIC_EXTRACT, args.rubrics_dir)
        rub_r = X.load_rubric(X.RUBRIC_REWRITE, args.rubrics_dir)
    except X.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    rdir = _run_dir(args, args.run_id)
    resp_path = rdir / X.RESPONSES_NAME
    units = [X.Unit(c.chunk_id, X.render_user(c), store_text=not SOURCES[c.source].read_only) for c in chunks]
    prev = X.read_responses(resp_path)
    if args.reuse_from:
        prev += X.read_responses(_run_dir(args, args.reuse_from) / X.RESPONSES_NAME)
    done = X.reusable_answers(prev, stage="extract", model=args.model, prompt_sha=rub_x["sha256"],
                              users={u.unit_id: u.user for u in units})
    todo = [u for u in units if u.unit_id not in done]
    est_x = X.estimate(todo, rub_x["text"], args.model, "extract")
    n_rw = int(round(len(chunks) * args.rewrite_share))
    est_r = X.estimate([], rub_r["text"], args.model, "rewrite", n_calls=n_rw)
    counts = dict(sorted(__import__("collections").Counter(c.source for c in chunks).items()))
    print(f"variant {args.variant}: {len(chunks)} chunks {counts}"
          + (f" (stratified sample of {args.chunks}, seed {args.seed})" if args.chunks else "")
          + f"; {len(done)} answered already (same rubric text and user turn), {len(todo)} to send")
    print(f"rubrics: {rub_x['name']} v{rub_x['version']} ({rub_x['sha256'][:12]}), "
          f"{rub_r['name']} v{rub_r['version']} ({rub_r['sha256'][:12]}); model {args.model}")
    total = _print_estimate([("extract", est_x), (f"rewrite (about {args.rewrite_share:.0%} of chunks)", est_r)],
                            args.budget_usd)
    cap = confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    if args.dry_run:
        print("DRY-RUN: no call, nothing written.  The first three extraction prompts as sent "
              "(system prompt = the rubric block):")
        for u in todo[:3]:
            print(f"--- {u.unit_id}\n{u.user}\n")
        return 0
    refused = _dirty_refusal(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    ctx = start_run(AS.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "extract", "variant": args.variant, "chunks": args.chunks, "seed": args.seed,
        "sources": sorted(counts), "n_chunks": len(chunks), "chunk_ids": [c.chunk_id for c in chunks],
        "model": args.model, "budget_usd": args.budget_usd, "estimate_usd": round(total, 4),
        "rubrics": {r["name"]: {k: r[k] for k in ("version", "sha256", "file")} for r in (rub_x, rub_r)},
        "reuse_from": args.reuse_from, "allow_dirty": bool(args.allow_dirty), LABEL_FORM_KEY: DEFAULT_LABEL_FORM,
        "sources_manifest": F.load_manifest(args.sources_manifest)})
    ctx.confirmed_by = args.confirmed_by
    ctx.usage = GuardedUsage(budget_usd=cap)
    x_res, r_res = X.StageResult(), X.StageResult()
    answers = dict(done)
    items: list = []
    try:
        client = _anthropic_client() if todo else None
        if todo:
            x_res = asyncio.run(X.run_stage(todo, stage="extract", client=client, model=args.model,
                                            system=rub_x["text"], usage=ctx.usage, concurrency=args.concurrency,
                                            rubric_version=rub_x["version"], now=utc_now,
                                            on_record=lambda r: X.append_response(r, resp_path)))
            answers.update(x_res.answers)
        items = X.assemble(chunks, answers, ordinals=ordinals)
        pairs = X.mechanism_pairs(items)
        heads = {c.chunk_id: c.heading for c in chunks}
        r_units = [X.Unit(named.pair_id, X.render_rewrite_user(named, partner, heading=heads.get(named.chunk_id)),
                          store_text=not SOURCES[named.source].read_only) for named, partner in pairs]
        r_done = X.reusable_answers(prev, stage="rewrite", model=args.model, prompt_sha=rub_r["sha256"],
                                    users={u.unit_id: u.user for u in r_units})
        r_todo = [u for u in r_units if u.unit_id not in r_done]
        rewrites = dict(r_done)
        if r_todo and not x_res.stopped_by_budget:
            client = client or _anthropic_client()
            r_res = asyncio.run(X.run_stage(r_todo, stage="rewrite", client=client, model=args.model,
                                            system=rub_r["text"], usage=ctx.usage, concurrency=args.concurrency,
                                            rubric_version=rub_r["version"], now=utc_now,
                                            on_record=lambda r: X.append_response(r, resp_path)))
            rewrites.update(r_res.answers)
            rewrites.update({k: None for k in r_res.errors})
        items = X.add_rewrites(items, rewrites, pairs)
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line("[usage this session]"), file=sys.stderr)
    warn_if_low_parse_rate(label=f"alignment_sweep extract:{args.model}", n_ok=len(x_res.answers),
                           n_total=len(x_res.answers) + len(x_res.errors))
    warn_if_low_parse_rate(label=f"alignment_sweep rewrite:{args.model}", n_ok=len(r_res.answers),
                           n_total=len(r_res.answers) + len(r_res.errors))
    X.write_extraction(items, rdir / X.EXTRACTION_NAME)
    summ = X.summarize(items, n_chunks=len(chunks), extract=x_res, rewrite=r_res, n_reused=len(done))
    summ.update({"run_id": args.run_id, "variant": args.variant, "model": args.model,
                 "rubrics": {r["name"]: {k: r[k] for k in ("version", "sha256")} for r in (rub_x, rub_r)},
                 "cost_usd_this_session": round(ctx.usage.total_cost_usd, 4), "usage_this_session": ctx.usage.as_dict(),
                 "stopped_by_budget": x_res.stopped_by_budget or r_res.stopped_by_budget, "at": utc_now(),
                 LABEL_FORM_KEY: DEFAULT_LABEL_FORM})
    from assistant_axis.atomic_io import atomic_write_text
    atomic_write_text(json.dumps(summ, indent=2, ensure_ascii=False) + "\n", rdir / X.SUMMARY_NAME)
    print(json.dumps({k: summ[k] for k in ("n_chunks", "n_pairs", "pairs_per_chunk", "type", "enactability",
                                           "label_rule_bite", "polysemy_flags", "dropped", "n_kept_poles",
                                           "cost_usd_this_session")}, indent=1))
    print(f"wrote {rdir / X.EXTRACTION_NAME}, {rdir / X.SUMMARY_NAME}, {resp_path}, run.json, usage.json")
    return 0


# --------------------------------------------------------------------------- dedupe

def _embedder(args):
    from assistant_axis.gapgen.embed import EmbeddingCache, make_embedder
    emb = make_embedder(args.embedder)
    cache = EmbeddingCache(root=args.embedding_cache) if args.embedder != "hash" else None
    return emb, cache


def _gloss_tokens(texts) -> int:
    return int(sum(len(t) for t in texts) / 4) + 1


def cmd_dedupe(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort, estimate_calls_usd
    from assistant_axis.gapgen.generators.alignment_sweep import dedupe as D
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.provenance import current_file_input

    rdir = _run_dir(args, args.run_id)
    ext = rdir / X.EXTRACTION_NAME
    if not ext.exists():
        raise SystemExit(f"no {ext}: run `alignment_sweep.py extract --run-id {args.run_id}` first")
    items = X.load_extraction(ext)
    labeled_doc = json.loads(args.labeled.read_text(encoding="utf-8")) if args.labeled.exists() else None
    texts = [it.gloss for it in items if it.gloss]
    if args.tune and labeled_doc:
        texts += [p[k] for p in labeled_doc["pairs"] for k in ("gloss_a", "gloss_b")]
    emb, cache = _embedder(args)
    missing = [t for t in dict.fromkeys(texts) if cache is None or cache.get(emb.tag, t) is None]
    est = estimate_calls_usd(emb.usage_model, 1, _gloss_tokens(missing), 0) if missing else 0.0
    print(f"run {args.run_id}: {len(items)} poles, {sum(it.kept for it in items)} kept; {len(missing)} glosses to "
          f"embed with {emb.model_id} (the rest cached); estimate ${est:.4f}; cap --budget-usd ${args.budget_usd:.2f}")
    cap = confirm_or_abort(est, args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    threshold = args.threshold
    if threshold is None and not args.tune and not args.pairs_for_labeling:
        if not (labeled_doc and labeled_doc.get("threshold")):
            raise SystemExit(f"no tuned threshold in {args.labeled}: label pairs and run --tune, or pass --threshold")
        threshold = float(labeled_doc["threshold"]["value"])
    if args.dry_run:
        print("DRY-RUN: would embed, then "
              + ("write dedup_pairs_to_label.json" if args.pairs_for_labeling else
                 "tune the threshold" if args.tune else f"group at threshold {threshold} into dedup_groups.json"))
        return 0
    if emb.name != "hash":
        refused = _dirty_refusal(args)
        if refused:
            raise SystemExit(f"REFUSED: {refused}")
    ctx = start_run(AS.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "dedupe", "embedder": emb.model_id, "threshold": threshold, "tune": bool(args.tune),
        "pairs_for_labeling": args.pairs_for_labeling, "budget_usd": args.budget_usd})
    ctx.usage = GuardedUsage(budget_usd=cap)
    try:
        vecs = D.embed_glosses(items, embedder=emb, cache=cache, usage=ctx.usage)
        if args.tune:
            if not labeled_doc:
                raise SystemExit(f"no {args.labeled}")
            from assistant_axis.gapgen.embed import embed_texts
            pairs = [p for p in labeled_doc["pairs"] if p.get("same") is not None]
            E = embed_texts(emb, [p[k] for p in pairs for k in ("gloss_a", "gloss_b")], cache=cache, usage=ctx.usage)
            for i, p in enumerate(pairs):
                p["cos"] = round(float(E[2 * i] @ E[2 * i + 1]), 4)
            t = D.tune_threshold(pairs, false_merge_cost=args.false_merge_cost)
            labeled_doc["threshold"] = {**t.as_dict(), "embedding_model": emb.model_id, "tuned_at": utc_now()}
            atomic_write_text(json.dumps(labeled_doc, indent=2, ensure_ascii=False) + "\n", args.labeled)
            print(f"tuned threshold {t.value} (false merge cost {t.false_merge_cost:g}; accuracy {t.accuracy:.3f}, "
                  f"precision {t.precision}, recall {t.recall} on {t.n} pairs, {t.n_same} same; gap {t.interval}); "
                  f"{len(t.errors)} pairs on the wrong side; wrote {args.labeled}")
            return 0
        if args.pairs_for_labeling:
            pairs = D.pairs_for_labeling(items, vecs, n=args.pairs_for_labeling, seed=args.seed)
            out = rdir / "dedup_pairs_to_label.json"
            atomic_write_text(json.dumps({"source_run": args.run_id, "embedding_model": emb.model_id, "pairs": pairs},
                                         indent=2, ensure_ascii=False) + "\n", out)
            print(f"wrote {out} ({len(pairs)} pairs, cosine {pairs[-1]['cos']} to {pairs[0]['cos']})")
            return 0
        groups = D.dedup_groups(items, vecs, threshold)
        hints = D.rewrite_partner_hints(items, groups)
        inputs = [current_file_input(dep_key="extraction", path=ext)]
        if args.labeled.exists():
            inputs.append(current_file_input(dep_key="dedup_labeled_pairs", path=args.labeled))
        D.write_groups(groups, rdir / "dedup_groups.json", threshold=threshold, model=emb.model_id, inputs=inputs,
                       extra={"partner_hints": hints, "threshold_source": "--threshold" if args.threshold is not None
                              else f"{args.labeled.name} (tuned)", "at": utc_now()})
        n_kept = sum(it.kept for it in items)
        print(f"{n_kept} kept poles -> {len(groups)} groups ({n_kept - len(groups)} merged) at threshold {threshold}; "
              f"{sum(1 for g in groups if 'exact stem' in g.note)} with an exact-stem merge; wrote "
              f"{rdir / 'dedup_groups.json'}")
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line("[usage this session]"), file=sys.stderr)
    return 0


# --------------------------------------------------------------------------- submit

def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.alignment_sweep import dedupe as D
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.generators.alignment_sweep import submit as S
    rdir = _run_dir(args, args.run_id)
    ext, grp = rdir / X.EXTRACTION_NAME, rdir / "dedup_groups.json"
    for p, cmd in ((ext, "extract"), (grp, "dedupe")):
        if not p.exists():
            raise SystemExit(f"no {p}: run `alignment_sweep.py {cmd} --run-id {args.run_id}` first")
    items = X.load_extraction(ext)
    env = json.loads(grp.read_text(encoding="utf-8"))
    groups = D.load_groups(grp)
    hints = env.get("result", env).get("partner_hints") or D.rewrite_partner_hints(items, groups)
    S.run_submit(args.run_id, items=items, groups=groups, hints=hints, budget_usd=args.budget_usd,
                 confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by, dry_run=args.dry_run,
                 registry_path=args.registry, candidates_dir=args.candidates_dir,
                 extra_args={"dedup_threshold": env.get("result", env).get("threshold"),
                             "sources_manifest": F.load_manifest(args.sources_manifest)})
    return 0


# --------------------------------------------------------------------------- gate

def cmd_gate(args) -> int:
    import asyncio

    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.generators.alignment_sweep import gate as G
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, LABEL_FORM_KEY
    from assistant_axis.gapgen.registry import Registry, utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.provenance import current_file_input

    rdir = _run_dir(args, args.run_id)
    try:
        rub = G.load_rubric(args.rubrics_dir)
    except G.RubricNotPinned as exc:
        raise SystemExit(f"REFUSED: {exc}")
    gold = G.gold_inputs(args.gold_items)
    kept = [] if args.gold_only else G.kept_inputs(Registry(args.registry).fold() if args.registry.exists() else {},
                                                   run_id=args.run_id)
    if not args.gold_only and not kept:
        print(f"no kept rows of alignment_sweep/{args.run_id} in {args.registry} (M3 decision new or a pair "
              f"completion): only the gold items run")
    e_gold, e_kept = G.estimate(gold, rub["text"], args.model), G.estimate(kept, rub["text"], args.model)
    print(f"gate: {len(gold)} gold items" + (f" and {len(kept)} kept rows" if kept else "") +
          f", {G.N_READINGS} readings each; rubric {rub['name']} v{rub['version']} ({rub['sha256'][:12]}); "
          f"model {args.model}")
    total = _print_estimate([("gold", e_gold)] + ([("kept rows", e_kept)] if kept else []), args.budget_usd)
    cap = confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    if args.dry_run:
        print("DRY-RUN: no call, nothing written.  The first three calls' user turns (system prompt = the rubric "
              "block):")
        for i in (gold + kept)[:3]:
            print(f"--- {i.key}\n{G.render_user(i)}")
        return 0
    refused = _dirty_refusal(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    ctx = start_run(AS.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "gate", "gold_only": bool(args.gold_only), "n_gold": len(gold), "n_kept": len(kept),
        "model": args.model, "budget_usd": args.budget_usd, "estimate_usd": round(total, 4),
        "rubric": {k: rub[k] for k in ("name", "version", "sha256", "file")}, LABEL_FORM_KEY: DEFAULT_LABEL_FORM,
        "allow_dirty": bool(args.allow_dirty)})
    ctx.usage = GuardedUsage(budget_usd=cap)
    resp = rdir / G.RESPONSES_NAME
    g_res, k_res = G.GateResult(), G.GateResult()
    try:
        client = _anthropic_client()
        g_res = asyncio.run(G.run_gate(gold, client=client, model=args.model, system=rub["text"], usage=ctx.usage,
                                       concurrency=args.concurrency, rubric_version=rub["version"], now=utc_now,
                                       on_record=lambda r: X.append_response(r, resp)))
        if kept and not g_res.stopped_by_budget:
            k_res = asyncio.run(G.run_gate(kept, client=client, model=args.model, system=rub["text"],
                                           usage=ctx.usage, concurrency=args.concurrency,
                                           rubric_version=rub["version"], now=utc_now,
                                           on_record=lambda r: X.append_response(r, resp)))
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line("[usage this session]"), file=sys.stderr)
    for label, res, n in (("gold", g_res, len(gold)), ("kept", k_res, len(kept))):
        if n:
            n_read = n * G.N_READINGS
            warn_if_low_parse_rate(label=f"alignment_sweep gate {label}:{args.model}",
                                   n_ok=n_read - res.n_failed_readings, n_total=n_read)
    gold_doc = json.loads(args.gold_items.read_text(encoding="utf-8"))["items"]
    ev = G.score_against_gold(g_res.rows, gold_doc)
    inputs = [current_file_input(dep_key="gate_gold_items", path=args.gold_items),
              current_file_input(dep_key="gate_rubric", path=_REPO_ROOT / rub["file"])]
    cost = round(ctx.usage.total_cost_usd, 4)
    env = json_metadata({"eval": ev.as_dict(), "rows": [r.as_dict() for r in g_res.rows], "model": args.model,
                         "rubric": {k: rub[k] for k in ("name", "version", "sha256")}, "cost_usd": cost,
                         "n_calls": g_res.n_calls, "n_failed_readings": g_res.n_failed_readings,
                         LABEL_FORM_KEY: DEFAULT_LABEL_FORM, "at": utc_now()},
                        inputs=inputs, title="alignment sweep: enactability gate on the gold items")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", rdir / G.GOLD_EVAL_NAME)
    atomic_write_text(G.eval_markdown(ev, g_res.rows, rubric=rub, cost_usd=cost), rdir / "gate_gold_eval.md")
    if kept:
        atomic_write_text("".join(json.dumps(r.as_dict(), ensure_ascii=False) + "\n" for r in k_res.rows),
                          rdir / G.ROWS_NAME)
    print(f"gold: agreement {ev.n_agree}/{ev.n} ({ev.agreement:.1%}), flip rate {ev.flip_rate:.1%}; "
          f"{'meets' if ev.meets_targets else 'below'} the targets; confusion {json.dumps(ev.confusion)}")
    print(f"wrote {rdir / G.GOLD_EVAL_NAME}, {rdir / 'gate_gold_eval.md'}, {resp}"
          + (f", {rdir / G.ROWS_NAME}" if kept else ""))
    return 0


# --------------------------------------------------------------------------- probe

def _run_labels(args, rdir: Path) -> tuple[list, Path]:
    """The labels a probe or report covers: the run's submitted candidates (surface, gloss hint), else, before a
    submission (the pilot), the kept dedup representatives."""
    from assistant_axis.gapgen.generators.alignment_sweep import dedupe as D
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.generators.alignment_sweep.probe import ProbeInput
    from assistant_axis.gapgen.registry import read_candidates
    cpath = rdir / "candidates.jsonl"
    if cpath.exists():
        return [ProbeInput(c.surface, c.gloss_hint or "") for c in read_candidates(cpath)], cpath
    grp = rdir / "dedup_groups.json"
    if not grp.exists():
        raise SystemExit(f"no {cpath} and no {grp}: submit (or at least dedupe) the run first")
    by = {it.item_id: it for it in X.load_extraction(rdir / X.EXTRACTION_NAME)}
    reps = [by[g.rep] for g in D.load_groups(grp)]
    seen, out = set(), []
    for it in sorted(reps, key=lambda i: (i.rank, i.item_id)):
        if it.kept and it.label not in seen:
            seen.add(it.label)
            out.append(ProbeInput(it.label, it.gloss))
    return out, grp


def cmd_probe(args) -> int:
    import asyncio
    import os

    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.alignment_sweep import probe as P
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM, LABEL_FORM_KEY
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.gapgen.runs import start_run
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.provenance import current_file_input

    rdir = _run_dir(args, args.run_id)
    if args.refloor:
        counts = P.refloor(rdir / P.PROBE_NAME, P.MIN_COS_TO_GLOSS)
        print(f"re-derived label_known at cosine {P.MIN_COS_TO_GLOSS} (no call): {json.dumps(counts)}; wrote "
              f"{rdir / P.PROBE_NAME}")
        return 0
    inputs, src = _run_labels(args, rdir)
    host = ", ".join(f"{k} ({v})" for k, v in P.ALLOWED_PROVIDERS.items())
    print(f"probe: {len(inputs)} labels on {P.MODEL} through OpenRouter, host pinned to {host}, fallbacks off "
          f"(from {src.name})")
    status = P.key_status(_REPO_ROOT / ".env")
    if status != "ok":
        print(status + "; the rank formula drops the label-known factor")
        if not args.dry_run:
            P.write_probe(None, rdir / P.PROBE_NAME, status=status)
        return 0
    est = P.estimate_usd(len(inputs)) + 0.003
    print(f"  estimate ${est:.4f} (with the definitions' embeddings); cap --budget-usd ${args.budget_usd:.2f}")
    cap = confirm_or_abort(est, args.budget_usd, confirm_expensive=args.confirm_expensive,
                           confirmed_by=args.confirmed_by)
    if args.dry_run:
        print("DRY-RUN: no call, nothing written.  The first three user turns:")
        for i in inputs[:3]:
            print(f"--- {i.label}\n{P.render_user(i.label)}")
        return 0
    refused = _dirty_refusal(args)
    if refused:
        raise SystemExit(f"REFUSED: {refused}")
    import openai
    from assistant_axis.gapgen.embed import EmbeddingCache, make_embedder
    ctx = start_run(AS.GENERATOR, args.run_id, candidates_dir=args.candidates_dir, args={
        "step": "probe", "model": P.MODEL, "host": dict(P.ALLOWED_PROVIDERS), "n_labels": len(inputs),
        "budget_usd": args.budget_usd, "prompt_version": P.PROMPT_VERSION, LABEL_FORM_KEY: DEFAULT_LABEL_FORM})
    ctx.usage = GuardedUsage(budget_usd=cap)
    res = None
    try:
        client = openai.AsyncOpenAI(base_url=P.OPENROUTER_URL, api_key=os.environ["OPENROUTER_API_KEY"])
        res = asyncio.run(P.run_probe(inputs, client=client, usage=ctx.usage, embedder=make_embedder("openai"),
                                      cache=EmbeddingCache(root=args.embedding_cache)))
    finally:
        ctx.finish(n_emitted=0)
        print(ctx.usage.log_line("[usage this session]"), file=sys.stderr)
    n_ok = len(inputs) - res.n_errors - res.n_discarded
    warn_if_low_parse_rate(label=f"alignment_sweep probe:{P.MODEL}", n_ok=n_ok, n_total=len(inputs))
    P.write_probe(res, rdir / P.PROBE_NAME, status="ran", inputs=[current_file_input(dep_key="labels", path=src)],
                  extra={"at": utc_now(), "cost_usd": round(ctx.usage.total_cost_usd, 5), LABEL_FORM_KEY:
                         DEFAULT_LABEL_FORM})
    rows = list(res.rows.values())
    known = sum(1 for r in rows if r.label_known)
    print(f"{len(rows)} labels: {known} known in the intended sense, "
          f"{sum(1 for r in rows if r.known_claimed is False)} unknown to the model, "
          f"{sum(1 for r in rows if r.known_claimed and not r.label_known)} known in another sense; "
          f"{res.n_discarded} discarded (another host), {res.n_errors} errors; wrote {rdir / P.PROBE_NAME}")
    return 0


# --------------------------------------------------------------------------- report

def cmd_report(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.alignment_sweep import extract as X
    from assistant_axis.gapgen.generators.alignment_sweep import gate as G
    from assistant_axis.gapgen.generators.alignment_sweep import probe as P
    from assistant_axis.gapgen.generators.alignment_sweep import report as R
    from assistant_axis.gapgen.registry import Registry

    rdir = _run_dir(args, args.run_id)
    sub_path = rdir / "submitted_items.json"
    if not sub_path.exists():
        raise SystemExit(f"no {sub_path}: the readout reads a submitted run (alignment_sweep.py submit, then M1 and "
                         f"M3); the pilot's readout is pilot_readout.md")
    submitted = json.loads(sub_path.read_text(encoding="utf-8"))
    items = {it.item_id: it.as_dict() for it in X.load_extraction(rdir / X.EXTRACTION_NAME)}
    reg = Registry(args.registry).fold() if args.registry.exists() else {}
    gate_rows = {}
    if (rdir / G.ROWS_NAME).exists():
        for line in (rdir / G.ROWS_NAME).read_text(encoding="utf-8").splitlines():
            if line.strip():
                d = json.loads(line)
                gate_rows[d["key"]] = d
    probe_path = rdir / P.PROBE_NAME
    probe_doc = json.loads(probe_path.read_text(encoding="utf-8")).get("result", {}) if probe_path.exists() else {}
    probe_status = probe_doc.get("status", "not run") + (f" (floor {probe_doc.get('min_cos_to_gloss')})"
                                                         if probe_doc.get("status") == "ran" else "")
    ev_path = rdir / G.GOLD_EVAL_NAME
    if ev_path.exists():
        ev = json.loads(ev_path.read_text(encoding="utf-8"))["result"]["eval"]
        gate_status = (("binding" if ev["meets_targets"] else "advisory only") +
                       f" (gold agreement {ev['n_agree']}/{ev['n']}, flip rate {ev['flip_rate']:.0%})")
    else:
        gate_status = "no gold evaluation yet (advisory)"
    rows = R.build_rows(submitted, items, reg, gate_rows=gate_rows, label_known=P.load_label_known(probe_path))
    groups = {g: sum(1 for r in rows if r.group == g) for g in ("survivor", "covered", "filtered")}
    counts = {"poles extracted": len(items), "kept poles": sum(1 for v in items.values() if not v["dropped_reason"]),
              "submitted": len(submitted), "survivors": groups["survivor"], "covered": groups["covered"],
              "filtered or not yet scored": groups["filtered"]}
    run_json = json.loads((rdir / "run.json").read_text(encoding="utf-8")) if (rdir / "run.json").exists() else {}
    md = R.render_readout(rows, run_id=args.run_id, counts=counts, costs=R.costs_by_step(run_json),
                          probe_status=probe_status, gate_status=gate_status, top=args.top)
    outs = {rdir / "readout.md": md}
    if args.gold:
        from assistant_axis.gapgen import novelty as NV
        from assistant_axis.gapgen.recovery import hiding_groups
        gold = json.loads(args.gold_traits.read_text(encoding="utf-8"))
        traits = NV.load_trait_corpus(args.data_dir)
        mates = {s: [m for m in grp if m != s] for grp in hiding_groups(traits) for s in grp}
        hidden = R.gold_hidden_doc(gold, partners=mates)
        hid_path = rdir / "gold_hidden.json"
        renamed = {s: list(t.renamed_from) for s, t in traits.items()}
        res = R.gold_recovery(gold, reg, submitted, run_id=args.run_id, renamed=renamed)
        py = "uv run python data_analysis/gap_generation"
        rel = hid_path
        try:
            rel = hid_path.resolve().relative_to(_REPO_ROOT.resolve())
        except ValueError:
            pass
        cmds = [f"{py}/novelty_score.py score --batch-id {args.run_id}_{AS.GENERATOR}_gold --run "
                f"{AS.GENERATOR}/{args.run_id} --hide {rel} --transport live --budget-usd 3",
                "# then match its decided candidates against the hidden traits with recovery.match_candidates "
                "(the harness's step 3); interface request 1 would run both"]
        outs[hid_path] = json.dumps(hidden, indent=2) + "\n"
        outs[rdir / "gold_recovery.md"] = R.render_gold_recovery(res, run_id=args.run_id, hidden_commands=cmds)
        print(f"gold: recovered {res['n_recovered']} of {res['n']} (no-call reading of the run's M3 blocks); frame "
              f"pair {'hit' if res['frame_pair']['hit'] else 'not hit'}")
    if args.dry_run:
        print(md)
        print("DRY-RUN: would write " + ", ".join(str(p) for p in outs))
        return 0
    for p, text in outs.items():
        atomic_write_text(text, p)
        print(f"wrote {p}")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external-dir", type=Path, default=AS.EXTERNAL_DIR)
    ap.add_argument("--sources-manifest", type=Path, default=AS.SOURCES_MANIFEST_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download the sources and write the manifests (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("chunk", help="split the fetched sources into chunks.jsonl (no API cost)")
    p.add_argument("--max-tokens", type=int, default=CH.MAX_CHUNK_TOKENS)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_chunk)

    def paid(p, budget: float):
        p.add_argument("--budget-usd", type=float, default=budget, help=f"hard cap (default ${budget:g})")
        p.add_argument("--confirm-expensive", action="store_true")
        p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")
        p.add_argument("--allow-dirty", action="store_true", help="run with uncommitted platform code (recorded)")
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--rubrics-dir", type=Path, default=None, help="default reports/trait_gap_generation/rubrics")

    p = sub.add_parser("extract", help="the extraction and mechanism-rewrite calls (Sonnet 5.5)")
    p.add_argument("--run-id", default=None)
    p.add_argument("--variant", choices=("A", "B"), default="A")
    p.add_argument("--chunks", type=int, default=None, help="a stratified sample of N chunks (the pilot: 30)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--sources", nargs="+", choices=sorted(SOURCES), help="only these sources")
    p.add_argument("--reuse-from", default=None, metavar="RUN_ID",
                   help="reuse that run's answers to byte-identical prompts (same rubric text and user turn)")
    p.add_argument("--render", nargs="+", metavar="CHUNK_ID", help="print these chunks' calls as sent; no call")
    p.add_argument("--render-rewrite", nargs="+", metavar="ITEM_ID",
                   help="print the rewrite calls of these extracted items (from --run-id's extraction.jsonl)")
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--rewrite-share", type=float, default=0.15,
                   help="share of chunks expected to yield a mechanism item (for the estimate only)")
    paid(p, 4.0)
    p.set_defaults(func=cmd_extract)

    p = sub.add_parser("dedupe", help="group near-identical glosses (text-embedding-3-large through the cache)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--threshold", type=float, default=None, help="default: the tuned one in --labeled")
    p.add_argument("--tune", action="store_true", help="tune the threshold on --labeled and record it there")
    p.add_argument("--false-merge-cost", type=float, default=2.0,
                   help="weight of a false merge against a missed one when tuning (default 2; 1 = plain accuracy)")
    p.add_argument("--pairs-for-labeling", type=int, default=None, metavar="N",
                   help="write N pairs to label (dedup_pairs_to_label.json in the run dir) and stop")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--labeled", type=Path, default=AS.DEDUP_PAIRS_PATH)
    p.add_argument("--embedder", choices=("openai", "hash"), default="openai")
    p.add_argument("--embedding-cache", type=Path, default=paths.DATA_CANDIDATES / "cache" / "embeddings")
    paid(p, 1.0)
    p.set_defaults(func=cmd_dedupe)

    p = sub.add_parser("submit", help="write the run's candidates.jsonl and submit it (no API cost; gated on the "
                                      "downstream M1 + M3 estimate)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--budget-usd", type=float, default=5.0, help="cap on the downstream estimate (M1 + M3)")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for an estimate over $20")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("gate", help="the persona-enactability gate (Sonnet 5.5, two readings): the gold items, then "
                                    "M3's kept rows of the run")
    p.add_argument("--run-id", required=True)
    p.add_argument("--gold-only", action="store_true")
    p.add_argument("--gold-items", type=Path, default=AS.GATE_GOLD_PATH)
    p.add_argument("--model", default="claude-sonnet-5-5")
    p.add_argument("--concurrency", type=int, default=6)
    paid(p, 1.5)
    p.set_defaults(func=cmd_gate)

    p = sub.add_parser("probe", help="the label probe: qwen/qwen3-32b via OpenRouter pinned to DeepInfra (US)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--embedding-cache", type=Path, default=paths.DATA_CANDIDATES / "cache" / "embeddings")
    p.add_argument("--refloor", action="store_true",
                   help="re-derive label_known in the run's probe.json at the current cosine floor (no call)")
    paid(p, 0.5)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("report", help="readout.md from the registry blocks, the gate, the probe and the usage files "
                                      "(no API cost); --gold adds gold_recovery.md")
    p.add_argument("--run-id", required=True)
    p.add_argument("--gold", action="store_true")
    p.add_argument("--gold-traits", type=Path, default=AS.GOLD_PATH)
    p.add_argument("--top", type=int, default=None, help="show only the top N survivors (the plan's table of ~40)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
