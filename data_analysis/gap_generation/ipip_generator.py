#!/usr/bin/env python3
"""The IPIP behavior-item generator (workstream 7, generator id ``ipip``).

    uv run python data_analysis/gap_generation/ipip_generator.py download [--only KEY ...] [--force]
        [--approved-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py ingest [--skip-hex-check] [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py cluster [--arms openai gemma] [--targets 600 350 150]
        [--seed 0] [--budget-usd 1] [--no-hdbscan] [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py name --granularity {600,350,150}
        [--clusters N | --all | --cluster-ids ID ...] [--hinted] [--render N] [--seed 0] [--budget-usd 1]
        [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py granularity [--granularities 600 350 150]
        [--signals nearest within] [--per-cluster 3] [--cross-pole 1] [--seed 0] [--budget-usd 3] [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py submit --granularity G --run-id R
        (--poles-file F | --all-poles) [--label-choice blind|hinted] [--budget-usd 8]
        [--confirm-expensive --confirmed-by WHO] [--dry-run]
    uv run python data_analysis/gap_generation/ipip_generator.py report --run-id R [--dry-run]

Plan: ``reports/trait_gap_generation/coding_plan_07_behaviour_items.md``.  ``download`` fetches the IPIP pages into
``data/external/ipip/`` (git-ignored) and records them (``sources_manifest.json``); every source is approved since
2026-10-11 (QUESTIONS 52 option C: the 21 key pages and Tedone's workbook; QUESTIONS 46: the home page).
``ingest`` writes ``items.jsonl`` and asserts the HEX block.
``cluster`` embeds the items (OpenAI and EmbeddingGemma), cuts each arm's tree at each target, keeps the clusters
both arms reproduce and splits bipolar ones into poles: ``clusters_g<G>.jsonl``.  ``name`` names poles on Haiku 5.5,
blind and (``--hinted``) with the scale names.  ``granularity`` makes the two readings of QUESTIONS 50 with M3's
overlap call (rubric A, Sonnet 5.5): each pole against the nearest pole of another cluster by name and gloss, and
the within-pole item pairs; the readout reports both by cluster-size band and prints clusters in full.  ``submit`` writes a run's ``candidates.jsonl`` (every named pole: QUESTIONS 48) and submits it; ``report`` writes its
``evaluation.json``, ``report.md`` and ``roger_sample.md``.  Every paid command prints its estimate, refuses one
over ``--budget-usd`` (and over $20 without ``--confirm-expensive --confirmed-by``), writes ``usage.json`` and
checks the parse rate.  Every command has ``--dry-run``, which writes nothing.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import sys
from pathlib import Path
from typing import Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.generators import ipip as P  # noqa: E402
from assistant_axis.gapgen.generators.ipip import download as D  # noqa: E402
from assistant_axis.gapgen.generators.ipip.sources import SOURCES  # noqa: E402

logger = logging.getLogger("ipip_generator")


# --------------------------------------------------------------------------- shared

def _git_sha() -> Optional[str]:
    from assistant_axis.gapgen.runs import git_sha
    return git_sha()


def _paths(args) -> dict:
    d = Path(args.ipip_dir)
    return {"dir": d, "items": d / P.ITEMS_PATH.name, "counts": d / P.INGEST_COUNTS_PATH.name,
            "manifest": d / P.SOURCES_MANIFEST_PATH.name, "naming_usage": d / P.NAMING_USAGE_PATH.name,
            "naming_responses": d / P.NAMING_RESPONSES_PATH.name, "granularity": d / P.GRANULARITY_DIR.name,
            "readout_json": d / P.GRANULARITY_READOUT_JSON.name, "readout_md": d / P.GRANULARITY_READOUT_MD.name,
            "cluster_summary": d / "cluster_summary.json", "cluster_usage": d / "cluster_usage.json"}


def _embedder(arm: str):
    """The embedder of an arm (tests replace this)."""
    from assistant_axis.gapgen.embed import make_embedder
    return make_embedder(arm)


def _client():
    """The Anthropic client, direct key (tests replace this)."""
    from assistant_axis.gapgen.generators.ipip.naming import make_client
    return make_client()


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(_REPO_ROOT.resolve()))
    except ValueError:
        return str(p)


def _merge_usage(usage, path: Path) -> None:
    """Add a session's usage to a cumulative ``usage.json``."""
    from assistant_axis.judge_pricing import MultiModelUsage
    total = MultiModelUsage.load_or_create(path)
    total.merge_from(MultiModelUsage(per_model=dict(usage.per_model)))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    total.write_json(path)


def _load_items(args):
    from assistant_axis.gapgen.generators.ipip import ingest as I
    p = _paths(args)["items"]
    if not p.exists():
        raise SystemExit(f"missing {p}: run `ipip_generator.py ingest` first")
    return I.load_items(p)


def _load_table(args, g: int) -> list[dict]:
    from assistant_axis.gapgen.generators.ipip.cluster import load_table
    p = P.clusters_path(g, _paths(args)["dir"])
    if not p.exists():
        raise SystemExit(f"missing {p}: run `ipip_generator.py cluster` first")
    return load_table(p)


# --------------------------------------------------------------------------- download, ingest

def cmd_download(args) -> int:
    try:
        man = D.fetch_all(dest_root=args.external, only=args.only, force=args.force, dry_run=args.dry_run,
                          git_sha=None if args.dry_run else _git_sha(), sources_manifest_path=_paths(args)["manifest"],
                          approved_by=args.approved_by)
    except D.NotApproved as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    if args.dry_run:
        print("DRY-RUN: would fetch (no API cost):")
        for line in man.dry_run_lines:
            print(f"  {line}")
        return 0
    for e in man.entries:
        print(f"{e['key']:20s} {e['size_bytes']:>9d} B  sha256 {e['sha256']}  {e['downloaded_at']}  {e['url']}")
    lic = man.licence
    print(f"licence: {lic.get('name')}; verbatim: {lic.get('verbatim') or '(not on the fetched pages)'}"
          + (f" [from {lic['verbatim_source']}]" if lic.get("verbatim_source") else ""))
    print(f"fetched: {', '.join(man.fetched) or 'none'}; already on disk and unchanged: {', '.join(man.skipped) or 'none'}")
    for p in man.written:
        print(f"wrote {p}")
    return 0


def _print_key_comparison(counts) -> bool:
    """The A-vs-B readout of QUESTIONS 52; returns whether it asks for Roger."""
    c = counts.get("key_comparison") or {}
    kp = counts.get("key_pages") or {}
    print(f"key_pages: {kp.get('n_pages_read')} of {kp.get('n_pages_expected')} read, {kp.get('n_rows')} key rows, "
          f"{kp.get('n_constructs')} constructs, {kp.get('n_items')} items"
          + (f"; MISSING {', '.join(kp['missing'])}" if kp.get("missing") else "")
          + (f"; EMPTY {', '.join(kp['empty'])}" if kp.get("empty") else "")
          + (f"; items read but none in the item pool: "
             + ", ".join(f"{p} ({n})" for p, n in sorted((kp.get("outside_pool") or {}).items()))
             if kp.get("outside_pool") else ""))
    print(f"key_merge: {json.dumps(counts.get('key_merge'), ensure_ascii=False)}")
    if not c.get("compared"):
        print(f"key_comparison: not run ({c.get('reason')})")
        return False
    print(f"key_comparison (B = the 21 key pages, primary; A = Tedone's workbook, a check):\n"
          f"  links: B {c['n_links_b']}, A {c['n_links_a']}, shared {c['n_links_shared']}; only B "
          f"{c['links_only_b']}, only A {c['links_only_a']}; sign conflicts {c['sign_conflicts']}\n"
          f"  items: B {c['n_items_b']}, A {c['n_items_a']}, shared {c['n_items_shared']}; only B "
          f"{c['items_only_b']}, only A {c['items_only_a']}\n"
          f"  of the items both key, {c['exact_match_items']} of {c['n_items_shared']} match exactly on "
          f"instrument, scale and sign (" + (f"{c['exact_match_rate']:.2%}" if c['exact_match_rate'] is not None
                                             else "n/a") + f"); link mismatch rate {c['link_mismatch_rate']}")
    norm = c.get("normalisations") or {}
    if norm:
        # the comparison is of sign and scale identity, not of spelling: say what was folded, because a
        # normalisation that is too eager would hide a real disagreement (QUESTIONS 52)
        print(f"  normalised for the comparison -- instrument: {norm.get('inventory')}; aliases "
              f"{json.dumps(norm.get('inventory_aliases'), ensure_ascii=False)}\n"
              f"    construct: {norm.get('construct')}; {norm.get('construct_names')}\n"
              f"    item pool: {norm.get('item_pool')} (set aside: B {c.get('set_aside_b')} rows, A "
              f"{c.get('set_aside_a')} rows); signs: {norm.get('signs')}")
    if c.get("mismatch_breakdown"):
        print(f"  what the {len(c['mismatch_breakdown']) and c['n_items_shared'] - c['exact_match_items']} "
              f"non-matching items are made of: "
              f"{json.dumps(c['mismatch_breakdown'], ensure_ascii=False)}\n"
              f"    of them, {c.get('n_instrument_name_only')} have a link on each side whose construct agrees "
              f"and whose instrument name does not: "
              f"{json.dumps(c.get('instrument_name_only'), ensure_ascii=False)}\n"
              f"    second reading, the instrument name ignored entirely (a diagnostic, not the headline): "
              + (f"{c['exact_match_rate_ignoring_instrument']:.2%}"
                 if c.get("exact_match_rate_ignoring_instrument") is not None else "n/a")
              + f" match, {c.get('sign_conflicts_ignoring_instrument')} sign conflicts")
    for x in (c.get("sign_conflict_list") or [])[:10]:
        print(f"  SIGN CONFLICT: {x['inventory']} / {x['construct']}: key pages {x['key_pages']}, workbook "
              f"{x['workbook']} -- {x['text']!r} ({x.get('page')})")
    if c.get("needs_roger"):
        print("ASK ROGER before going on (QUESTIONS 52, his standing instruction): " + "; ".join(c["reasons"]),
              file=sys.stderr)
        print(c["instruction"], file=sys.stderr)
    return bool(c.get("needs_roger"))


def cmd_ingest(args) -> int:
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.ipip import ingest as I
    pp = _paths(args)
    try:
        items, counts = I.build_from_dir(args.external, require_workbook=args.require_workbook)
    except FileNotFoundError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    for k in ("n_items", "n_codes", "n_multi_code", "n_with_scales", "n_multi_scale", "n_keyed_minus",
              "n_scale_links", "n_constructs", "n_assignment_rows", "unmatched_assignments", "ambiguous_text_joins",
              "per_inventory", "hex", "scale_index", "key_sources", "n_items_with_a_only_key"):
        print(f"{k}: {json.dumps(counts.get(k), ensure_ascii=False)}")
    needs_roger = _print_key_comparison(counts)
    try:
        I.check_key_pages(counts)
        keys_ok = True
    except I.KeyPageError as exc:
        keys_ok = False
        print(f"KEY PAGE CHECK FAILED: {exc}", file=sys.stderr)
    try:
        I.check_hex(counts)
        hex_ok = True
    except I.HexAssertionError as exc:
        hex_ok = False
        print(f"HEX ASSERTION FAILED: {exc}", file=sys.stderr)
    counts["hex_assertion"] = "passed" if hex_ok else "failed"
    counts["key_page_check"] = "passed" if keys_ok else "failed"
    counts["construct_labels"] = sorted({s["construct"] for r in items for s in r.scales})
    if args.dry_run:
        print(f"DRY-RUN: would write {pp['items']} ({len(items)} items) and {pp['counts']}")
        return 0
    if not (hex_ok and keys_ok) and not args.skip_hex_check:
        print("nothing written (pass --skip-hex-check to write anyway)", file=sys.stderr)
        return 1
    backup = I.write_items(items, pp["items"])
    atomic_write_text(json.dumps(counts, indent=2, ensure_ascii=False) + "\n", pp["counts"])
    print(f"wrote {pp['items']} ({len(items)} items, sha256 {I.file_sha256(pp['items'])[:16]}...)"
          + (f"; previous file kept as {backup}" if backup else ""))
    print(f"wrote {pp['counts']}")
    return 3 if needs_roger else 0


# --------------------------------------------------------------------------- cluster

def cmd_cluster(args) -> int:
    import numpy as np

    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.cost import confirm_or_abort, estimate_calls_usd
    from assistant_axis.gapgen.embed import EmbeddingCache, embed_texts
    from assistant_axis.gapgen.generators.ipip import cluster as C
    from assistant_axis.gapgen.generators.ipip.corpus import corpus_embed_texts, corpus_traits
    from assistant_axis.gapgen.generators.ipip.ingest import file_sha256
    from assistant_axis.judge_pricing import MultiModelUsage
    from assistant_axis.provenance import current_file_input
    pp = _paths(args)
    items = _load_items(args)
    cache = EmbeddingCache(root=args.embedding_cache) if args.embedding_cache else EmbeddingCache()
    corpus = corpus_embed_texts(corpus_traits(args.data_dir))
    embedders = {arm: _embedder(arm) for arm in args.arms}
    texts = [C.item_embed_text(r.text) for r in items]
    lines, total = [], 0.0
    for arm, emb in embedders.items():
        need = list(texts) + (list(corpus.values()) if arm == args.arms[0] else [])
        _found, missing = cache.lookup(emb.tag, need)
        tok = int(sum(len(need[i]) for i in missing) / 4)
        usd = estimate_calls_usd(emb.usage_model, 1, tok, 0)
        total += usd
        lines.append(f"  {arm} ({emb.model_id}): {len(missing)} of {len(need)} texts not cached, ~{tok:,} tokens = ${usd:.4f}")
    print(f"embedding estimate:\n" + "\n".join(lines) + f"\n  total ${total:.4f}")
    confirm_or_abort(total, args.budget_usd, confirm_expensive=False)
    if args.dry_run:
        print(f"DRY-RUN: would embed, cluster at {args.targets} and write "
              + ", ".join(str(P.clusters_path(g, pp["dir"])) for g in args.targets) + f", {pp['cluster_summary']}, "
              f"{pp['cluster_usage']}")
        return 0
    usage = MultiModelUsage()
    try:
        vectors = {arm: C.embed_items(items, embedder=emb, cache=cache, usage=usage) for arm, emb in embedders.items()}
        summaries = {}
        for g in args.targets:
            path = P.clusters_path(g, pp["dir"])
            prev = C.load_table(path)
            rows, summary = C.build_cluster_table(items, vectors, target=g, primary=args.arms[0], second=args.arms[1],
                                                  corpus=corpus, corpus_embedder=embedders[args.arms[0]], cache=cache,
                                                  usage=usage, seed=args.seed, hdbscan=not args.no_hdbscan,
                                                  previous=prev)
            backup = C.write_table(rows, path)
            summaries[str(g)] = summary
            s = summary
            print(f"~{g}: {s['cut'][args.arms[0]]['n_clusters']} clusters ({args.arms[0]}), "
                  f"{s['cut'][args.arms[1]]['n_clusters']} ({args.arms[1]}); kept {s['consensus']['n_kept']}, loose "
                  f"{s['consensus']['n_loose']} ({s['consensus']['loose_items']} items); bipolar kept "
                  f"{s['bipolar']['n_kept']}; poles kept {s['n_poles_kept']}; purity kept "
                  f"{s['purity']['kept']['purity_mean']}; NMI {s['purity'][args.arms[0]]['nmi']} / "
                  f"{s['purity'][args.arms[1]]['nmi']}" + (f"; naming carried over {s['naming_carried_over']}"
                                                           if s["naming_carried_over"] else ""))
            print(f"wrote {path}" + (f" (previous kept as {backup})" if backup else ""))
    finally:
        cache.save()
        _merge_usage(usage, pp["cluster_usage"])
    inputs = [current_file_input(dep_key="items", path=pp["items"])]
    arms = {a: {"model": e.model_id, "tag": e.tag} for a, e in embedders.items()}
    items_sha = file_sha256(pp["items"])
    # a run over some of the targets keeps the other granularities' summaries when they were made from the same
    # items with the same arms (review 2026-10-12: `cluster --targets 600` had dropped the 350 and 150 summaries,
    # which `report` reads from this file)
    kept_g = {}
    from assistant_axis.gapgen.generators.ipip.report import _read_json
    old = _read_json(pp["cluster_summary"])
    if old and old.get("items_sha256") == items_sha and old.get("arms") == arms and old.get("seed") == args.seed:
        kept_g = {k: v for k, v in (old.get("granularities") or {}).items() if k not in summaries}
    all_g = {**kept_g, **summaries}
    all_g = {k: all_g[k] for k in sorted(all_g, key=lambda k: -int(k))}
    doc = {"arms": arms, "targets": [int(k) for k in all_g], "targets_this_run": list(args.targets),
           "seed": args.seed, "items_sha256": items_sha, "n_items": len(items),
           "granularities": all_g, "usage": usage.as_dict(),
           "dims": {a: int(np.asarray(v).shape[1]) for a, v in vectors.items()}}
    env = json_metadata(doc, title="IPIP clusters: summary per granularity", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", pp["cluster_summary"])
    print(f"wrote {pp['cluster_summary']}; {usage.log_line()}")
    return 0


# --------------------------------------------------------------------------- name

def _pole_refs(rows, items_by_id, *, forms, force):
    from assistant_axis.gapgen.generators.ipip import naming as N
    refs = []
    for r in rows:
        for p in r["poles"]:
            if not force and all(p.get(f) for f in forms):
                continue
            refs.append(N.PoleRef(granularity=int(r["granularity"]), cluster_id=int(r["cluster_id"]), pole=p["pole"],
                                  statements=[items_by_id[i].text for i in p["items"]],
                                  scales=N.scales_for(p.get("constructs") or {})))
    return refs


def select_clusters(rows, *, n: Optional[int], all_: bool, ids: Optional[Sequence[int]], seed: int) -> list[dict]:
    kept = [r for r in rows if r.get("consensus") == "kept"]
    if ids:
        want = set(int(i) for i in ids)
        return [r for r in rows if int(r["cluster_id"]) in want]
    if all_ or n is None or n >= len(kept):
        return kept
    pick = random.Random(seed).sample(kept, n)
    return sorted(pick, key=lambda r: int(r["cluster_id"]))


def cmd_name(args) -> int:
    from assistant_axis.gapgen.cost import Estimate, GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.ipip import cluster as C
    from assistant_axis.gapgen.generators.ipip import naming as N
    from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM
    from assistant_axis.judge import warn_if_low_parse_rate
    pp = _paths(args)
    rows = _load_table(args, args.granularity)
    items = {r.ipip_id: r for r in _load_items(args)}
    chosen = select_clusters(rows, n=args.clusters, all_=args.all, ids=args.cluster_ids, seed=args.seed)
    forms = ["blind", "hinted"] if args.hinted else ["blind"]
    # the poles to ask, per form: a pole already named in a form is not asked that form again unless --force
    # (review 2026-10-12: a `--hinted` pass after a blind-only pass re-asked every blind name -- 362 of them, and
    # Haiku 5.5 gave a different blind label for 189 -- because a pole missing either form was asked both)
    refs_by_form = {f: _pole_refs(chosen, items, forms=[f], force=args.force) for f in forms}
    refs = list({r.key: r for f in forms for r in refs_by_form[f]}.values())
    n_calls = sum(len(v) for v in refs_by_form.values())
    est = Estimate()
    for f in forms:
        est.add(f"naming ({f})", args.model, len(refs_by_form[f]), N.EST_IN_TOKENS, N.EST_OUT_TOKENS)
    print(f"{len(chosen)} clusters chosen (seed {args.seed}), {len(refs)} poles to name ("
          + " + ".join(f"{f} {len(refs_by_form[f])}" for f in forms) + "):")
    print(est.format())
    confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.render:
        # the calls exactly as they are sent, for the rubric files' "Rendered sample" sections (the house rule:
        # read the rendered prompt, not the template)
        for f in forms:
            rub = N.load_rubric(f)
            shown = refs_by_form[f] or _pole_refs(chosen, items, forms=[f], force=True)
            print(f"=== {f}: system turn, {rub['name']} version {rub['version']} (sha {rub['sha256'][:12]}...), "
                  f"sent byte for byte ===")
            print(rub["text"])
            print(f"=== {f}: user turns, the first {min(args.render, len(shown))} of {len(shown)} ===")
            for r in shown[:args.render]:
                print(N.build_user(r) if f == "blind" else N.build_hinted_user(r, label_form=DEFAULT_LABEL_FORM))
        if args.dry_run:
            return 0
    if args.dry_run:
        print(f"DRY-RUN: would make {n_calls} calls on {args.model} and write "
              f"{P.clusters_path(args.granularity, pp['dir'])}, {pp['naming_responses']}, {pp['naming_usage']}")
        return 0
    if not refs:
        print("nothing to name")
        return 0
    usage = GuardedUsage(budget_usd=args.budget_usd)

    async def _name_each_form() -> list:
        client, out = _client(), []
        for f in forms:                       # one form after the other, in one event loop (one client)
            if refs_by_form[f] and not any(x.stopped_by_budget for x in out):
                out.append(await N.name_poles(refs_by_form[f], client=client, model=args.model, usage=usage,
                                              forms=[f], responses_path=pp["naming_responses"],
                                              label_form=DEFAULT_LABEL_FORM))
        return out
    try:
        parts = asyncio.run(_name_each_form())
    finally:
        _merge_usage(usage, pp["naming_usage"])
    res = N.NameResult()
    for x in parts:
        res.namings.update(x.namings)
        res.errors.update(x.errors)
        for k, v in x.error_kinds.items():
            res.error_kinds[k] = res.error_kinds.get(k, 0) + v
        res.first_attempt_ok += x.first_attempt_ok
        res.n_calls += x.n_calls
        res.stopped_by_budget = res.stopped_by_budget or x.stopped_by_budget
    vers = {f: N.prompt_version(f) for f in forms}
    for r in rows:
        for p in r["poles"]:
            for f in forms:
                nm = res.namings.get((int(r["granularity"]), int(r["cluster_id"]), p["pole"], f))
                if nm is not None:
                    p[f] = {**nm.as_dict(), "model": args.model, "prompt_version": vers[f], "label_form": DEFAULT_LABEL_FORM}
            if p.get("blind") and p.get("hinted"):
                p["labels_disagree"] = p["blind"]["stem"] != p["hinted"]["stem"]
    C.write_table(rows, P.clusters_path(args.granularity, pp["dir"]))
    ok, n = res.parse_rate()
    warn_if_low_parse_rate(label=f"ipip naming:{args.model}", n_ok=ok, n_total=n, logger_obj=logger,
                           extra=f"first attempt {res.first_attempt_ok}; rejected {res.error_kinds}")
    print(f"named {ok} of {n} pole-forms in {res.n_calls} calls; rejected answers {res.error_kinds}; "
          f"{usage.plain().log_line()}" + ("; STOPPED at the budget" if res.stopped_by_budget else ""))
    print(f"wrote {P.clusters_path(args.granularity, pp['dir'])}, {pp['naming_responses']}, {pp['naming_usage']}")
    return 0 if not res.stopped_by_budget else 2


# --------------------------------------------------------------------------- granularity

def cmd_granularity(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen import overlap_test as OT
    from assistant_axis.gapgen.cost import GuardedUsage, confirm_or_abort
    from assistant_axis.gapgen.generators.ipip import granularity as G
    from assistant_axis.gapgen.prompt_labels import resolve_label_form
    from assistant_axis.judge_pricing import MultiModelUsage
    from assistant_axis.provenance import current_file_input
    pp = _paths(args)
    items = {r.ipip_id: r for r in _load_items(args)}
    rubrics = OT.load_rubrics(keys=[G.RUBRIC])
    plans = {}
    total = 0.0
    for g in args.granularities:
        rows = _load_table(args, g)
        calls, corpus, nearest_counts = [], {}, {}
        if "within" in args.signals:
            calls, corpus = G.sample_pairs(rows, items, per_cluster=args.per_cluster, cross_pole=args.cross_pole,
                                           seed=args.seed)
        if "nearest" in args.signals:
            # QUESTIONS 50 signal 1: each pole against the nearest pole of another cluster, by name and gloss
            n_calls, n_corpus, nearest_counts = G.nearest_pair_calls(rows, form=args.label_choice)
            calls = list(calls) + list(n_calls)
            corpus = {**corpus, **n_corpus}
        out = pp["granularity"] / f"g{g}"
        done = OT.done_keys(OT.read_records(out / "responses.jsonl"))
        todo = [c for c in calls if (G.RUBRIC, G.MODEL, c.call_id, 1) not in done]
        est = G.estimate_usd(todo, corpus, rubrics) if todo else {"cached_usd": 0.0, "uncached_usd": 0.0}
        total += est["cached_usd"]
        plans[g] = (rows, calls, corpus, out, len(todo), nearest_counts)
        print(f"~{g}: {sum(1 for r in rows if r.get('consensus') == 'kept')} kept clusters, {len(calls)} pairs "
              f"({sum(1 for c in calls if c.set == 'within')} within-pole, "
              f"{sum(1 for c in calls if c.set == 'cross')} cross-pole, "
              f"{sum(1 for c in calls if c.set == 'nearest')} nearest-other-cluster), {len(todo)} to send: "
              f"${est['cached_usd']:.3f} with the cache (${est['uncached_usd']:.3f} uncached, an upper bound)")
        if nearest_counts:
            print(f"   signal 1: {json.dumps(nearest_counts)}")
    print(f"total estimate ${total:.3f} on {G.MODEL}")
    confirm_or_abort(total, args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.dry_run:
        print(f"DRY-RUN: would write {pp['granularity']}/g<G>/responses.jsonl, usage.json, run.json and "
              f"{pp['readout_json']}, {pp['readout_md']}")
        return 0
    client = _client() if any(n for *_x, n in plans.values()) else None
    readouts, samples, answers = [], {}, {}
    spent = 0.0
    stopped = False
    for g, (rows, calls, corpus, out, n_todo, nearest_counts) in plans.items():
        out.mkdir(parents=True, exist_ok=True)
        run_path = out / "run.json"
        earlier = json.loads(run_path.read_text()) if run_path.exists() else None
        label_form = resolve_label_form(earlier=earlier)
        prev = MultiModelUsage.load_or_create(out / "usage.json")
        usage = GuardedUsage(per_model=dict(prev.per_model),
                             budget_usd=prev.total_cost_usd + max(0.0, args.budget_usd - spent), usage_path=out / "usage.json")
        res = None
        if n_todo and not stopped:      # after a budget stop nothing more is sent (review 2026-10-12)
            res = asyncio.run(G.run_readings(calls, corpus, client=client, usage=usage, out_dir=out, rubrics=rubrics,
                                             label_form=label_form))
        spent += usage.total_cost_usd - prev.total_cost_usd
        ids = {c.call_id for c in calls}
        recs = [r for r in OT.read_records(out / "responses.jsonl") if r["call_id"] in ids]
        ro = G.readout(recs, granularity=g, n_clusters=sum(1 for r in rows if r.get("consensus") == "kept"),
                       label_form=label_form, cost_usd=usage.total_cost_usd, rubric_version=rubrics[G.RUBRIC]["version"],
                       bands=G.call_bands(rows, calls), sizes=G.band_sizes(rows), nearest_counts=nearest_counts)
        readouts.append(ro)
        atomic_write_text(json.dumps({"granularity": g, "label_form": label_form, "model": G.MODEL, "rubric": G.RUBRIC,
                                      "rubric_version": rubrics[G.RUBRIC]["version"], "seed": args.seed,
                                      "per_cluster": args.per_cluster, "cross_pole": args.cross_pole,
                                      "signals": list(args.signals), "label_choice": args.label_choice,
                                      "n_calls": len(calls), "cost_usd": round(usage.total_cost_usd, 4),
                                      "budget_exceeded": bool(res and res.budget_exceeded)}, indent=2) + "\n", run_path)
        # QUESTIONS 50 signal 2: clusters chosen to span the size range, printed in full in the readout
        samples[g] = G.spanning_clusters(rows, args.sample_clusters, seed=args.seed)
        latest = OT.latest_records(recs)
        for r in latest.values():
            rows_p, _e, _m = OT.reparse(r)
            v = (rows_p.get(1) or {})
            answers.setdefault(r.get("origin_call_id") or r["call_id"].rsplit(":", 1)[0], []).append(
                {"set": r.get("set"), "target": corpus[r["target"]]["label"], "other": corpus[r["listed"][0]]["label"],
                 "value": v.get("value"), "reason": v.get("reason")})
        print(f"~{g}: signal 1 (nearest other cluster) {ro['nearest']['n']} pairs read, share at 3 "
              f"{ro['nearest']['share_3']}, at 3-4 {ro['nearest']['share_3_4']}; by band "
              + json.dumps({b: x['share_3'] for b, x in (ro.get('nearest_by_band') or {}).items()})
              + f"\n    within-pole {ro['within']['n']} pairs, share at 3-4 {ro['within']['share_3_4']}; "
              f"cross-pole opposite {ro['cross_pole']['opposite']} of {ro['cross_pole']['n']}; "
              f"${usage.total_cost_usd:.3f}")
        if res is not None and res.budget_exceeded:
            stopped = True
            print(f"STOPPED at the budget (--budget-usd ${args.budget_usd:.2f}) during ~{g}: the later granularities "
                  f"send nothing; rerun to finish (answers on record are not sent again)", file=sys.stderr)
    inputs = [current_file_input(dep_key=f"clusters_g{g}", path=P.clusters_path(g, pp["dir"])) for g in plans]
    env = json_metadata({"readouts": readouts, "settings": {"per_cluster": args.per_cluster, "cross_pole": args.cross_pole,
                                                            "seed": args.seed, "model": G.MODEL, "rubric": G.RUBRIC,
                                                            "signals": list(args.signals), "bands": list(G.BAND_LABELS),
                                                            "label_choice": args.label_choice}},
                        title="IPIP granularity readout", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", pp["readout_json"])
    md = G.readout_markdown(readouts, samples=samples, items=items, answers=answers, doc_path=pp["readout_md"],
                            files=[pp["readout_json"]] + [pp["granularity"] / f"g{g}" / "responses.jsonl" for g in plans])
    atomic_write_text(md, pp["readout_md"])
    print(f"wrote {pp['readout_json']} and {pp['readout_md']}")
    return 2 if stopped else 0


# --------------------------------------------------------------------------- submit, report

def cmd_submit(args) -> int:
    from assistant_axis.gapgen.generators.ipip import submit as S
    from assistant_axis.gapgen.generators.ipip.ingest import file_sha256
    pp = _paths(args)
    if not (args.poles_file or args.all_poles):
        raise SystemExit("submit needs --poles-file F or --all-poles")
    rows = _load_table(args, args.granularity)
    cpath = P.clusters_path(args.granularity, pp["dir"])
    manifest = D.load_manifest(pp["manifest"])
    S.run_submit(args.granularity, args.run_id, rows=rows, sources_manifest=manifest, clusters_sha256=file_sha256(cpath),
                 label_choice=args.label_choice, poles=S.selected_poles(args.poles_file),
                 budget_usd=args.budget_usd, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by,
                 dry_run=args.dry_run, registry_path=args.registry, candidates_dir=args.candidates_dir,
                 clusters_path=_rel(cpath))
    return 0


def cmd_report(args) -> int:
    from assistant_axis import json_metadata
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.gapgen.generators.ipip import evaluate as E
    from assistant_axis.gapgen.generators.ipip import report as R
    from assistant_axis.gapgen.generators.ipip.cluster import load_table
    from assistant_axis.gapgen.generators.ipip.corpus import corpus_traits
    from assistant_axis.gapgen.registry import Registry, has_source
    from assistant_axis.provenance import current_file_input
    pp = _paths(args)
    rdir = paths.run_dir(P.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    if not (rdir / "candidates.jsonl").exists():
        raise SystemExit(f"no run at {rdir} (no candidates.jsonl)")
    tables = {g: load_table(P.clusters_path(g, pp["dir"])) for g in P.GRANULARITIES
              if P.clusters_path(g, pp["dir"]).exists()}
    summ = (R._read_json(pp["cluster_summary"]) or {}).get("granularities") or {}
    readouts = (R._read_json(pp["readout_json"]) or {}).get("readouts") or []
    naming_records = R._read_jsonl(pp["naming_responses"])
    reg = Registry(args.registry).fold() if Path(args.registry).exists() else {}
    reg_rows = [r for _k, r in sorted(reg.items()) if has_source(r, P.GENERATOR, args.run_id)]
    counts = R._read_json(pp["counts"])
    usage_paths = {"naming": pp["naming_usage"], "cluster_embeddings": pp["cluster_usage"]}
    for g in P.GRANULARITIES:
        usage_paths[f"granularity_g{g}"] = pp["granularity"] / f"g{g}" / "usage.json"
    ev = R.build_evaluation(args.run_id, run_dir=rdir, tables=tables, cluster_summaries=summ, readouts=readouts,
                            naming_records=naming_records, registry_rows=reg_rows, ingest_counts=counts,
                            corpus_stems=set(corpus_traits(args.data_dir)),
                            census_stems=E.load_census_stems(args.census_table), usage_paths=usage_paths,
                            candidates_dir=args.candidates_dir or paths.DATA_CANDIDATES)
    files = {"evaluation": rdir / "evaluation.json", "report": rdir / "report.md", "roger_sample": rdir / "roger_sample.md",
             "candidates": rdir / "candidates.jsonl", "run": rdir / "run.json", "usage": rdir / "usage.json",
             "granularity_md": pp["readout_md"], "granularity_json": pp["readout_json"],
             "cluster_summary": pp["cluster_summary"], "items": pp["items"], "manifest": pp["manifest"]}
    files.update({f"clusters_g{g}": P.clusters_path(g, pp["dir"]) for g in tables})
    md = R.render_report(ev, doc_path=files["report"], run_dir=rdir, files=files)
    g = ev.get("granularity")
    items = {r.ipip_id: r for r in _load_items(args)}
    by_stem = {r.get("stem"): r for r in reg_rows}
    sample = R.roger_sample(tables.get(int(g), []) if g is not None else [], by_stem, items,
                            doc_path=files["roger_sample"], n=args.sample, seed=args.seed)
    if args.dry_run:
        print(md)
        print(sample)
        print(f"DRY-RUN: would write {files['evaluation']}, {files['report']} and {files['roger_sample']}")
        return 0
    inputs = [current_file_input(dep_key=k, path=p) for k, p in (
        ("candidates", files["candidates"]), ("run_json", files["run"]), ("items", pp["items"]),
        ("cluster_summary", pp["cluster_summary"]), ("granularity_readout", pp["readout_json"]),
        ("naming_responses", pp["naming_responses"]), ("registry", Path(args.registry))) if Path(p).exists()]
    env = json_metadata(ev, title=f"IPIP generator evaluation, run {args.run_id}", inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", files["evaluation"])
    atomic_write_text(md, files["report"])
    atomic_write_text(sample, files["roger_sample"])
    print(f"wrote {files['evaluation']}, {files['report']} and {files['roger_sample']}")
    return 0


# --------------------------------------------------------------------------- parser

def _cost_flags(p, budget: float) -> None:
    p.add_argument("--budget-usd", type=float, default=budget, help=f"hard cap on the estimate (default ${budget:g})")
    p.add_argument("--confirm-expensive", action="store_true")
    p.add_argument("--confirmed-by", default=None, help="Roger's explicit go for anything over $20")
    p.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    from assistant_axis.gapgen.generators.ipip.granularity import SIGNALS as G_SIGNALS
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR, help="corpus data dir (default data/)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="where run directories go (default data/candidates; tests)")
    ap.add_argument("--external", type=Path, default=P.EXTERNAL_DIR, help="where the pages go (data/external/ipip)")
    ap.add_argument("--ipip-dir", type=Path, default=P.IPIP_DIR, help="the generator's tracked files (data/candidates/ipip)")
    ap.add_argument("--embedding-cache", type=Path, default=None, help="embedding cache root (default the platform's)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("download", help="fetch the IPIP pages (no API cost)")
    p.add_argument("--only", nargs="+", choices=sorted(SOURCES))
    p.add_argument("--force", action="store_true")
    p.add_argument("--approved-by", default=None,
                   help="Roger's go for a source with no approval on record (the assignment workbook, QUESTIONS 52)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("ingest", help="build items.jsonl and ingest_counts.json (no API cost)")
    p.add_argument("--skip-hex-check", action="store_true",
                   help="write even when a scrape-completeness check fails (the HEX assertion of plan § 7, or a "
                        "missing or empty key page); the checks still print and are recorded in the counts")
    p.add_argument("--require-workbook", action="store_true",
                   help="refuse to ingest without Tedone's workbook (source A, the check on the key pages); by "
                        "default its absence is recorded and the key pages alone are committed")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("cluster", help="embed (OpenAI + EmbeddingGemma), cluster, consensus, poles (about $0.01)")
    p.add_argument("--arms", nargs=2, default=["openai", "gemma"], metavar=("PRIMARY", "SECOND"))
    p.add_argument("--targets", nargs="+", type=int, default=list(P.GRANULARITIES))
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--no-hdbscan", action="store_true", help="skip the HDBSCAN cross-check (report only)")
    p.add_argument("--budget-usd", type=float, default=1.0)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_cluster)

    p = sub.add_parser("name", help="name poles on Haiku 5.5, blind and (--hinted) with the scale names")
    p.add_argument("--granularity", type=int, required=True, choices=P.GRANULARITIES)
    which = p.add_mutually_exclusive_group()
    which.add_argument("--clusters", type=int, default=40, help="a seeded sample of N kept clusters (default 40)")
    which.add_argument("--all", action="store_true", help="every kept cluster")
    which.add_argument("--cluster-ids", type=int, nargs="+", default=None)
    p.add_argument("--hinted", action="store_true", help="also the hinted call beside the blind one")
    p.add_argument("--force", action="store_true", help="name poles already named again")
    p.add_argument("--render", type=int, nargs="?", const=3, default=0, metavar="N",
                   help="print the system prompt and the first N user turns exactly as they are sent (for the "
                        "rubric files' rendered samples); with --dry-run it prints and stops")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--model", default="claude-haiku-5-5")
    _cost_flags(p, 1.0)
    p.set_defaults(func=cmd_name)

    p = sub.add_parser("granularity", help="read within-pole item pairs with M3's overlap call (Sonnet 5.5)")
    p.add_argument("--granularities", nargs="+", type=int, default=list(P.GRANULARITIES))
    p.add_argument("--per-cluster", type=int, default=3)
    p.add_argument("--cross-pole", type=int, default=1)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--sample-clusters", type=int, default=10,
                   help="clusters printed in full per granularity (signal 2), chosen to span the size range")
    p.add_argument("--signals", nargs="+", choices=list(G_SIGNALS), default=list(G_SIGNALS),
                   help="which readings to make: `nearest` is QUESTIONS 50's signal 1 (each pole against the "
                        "nearest pole of another cluster, by name and gloss), `within` the within-pole item pairs "
                        "and the bipolar check.  Signal 2 (the clusters in full) costs nothing and is always "
                        "rendered")
    p.add_argument("--label-choice", choices=("blind", "hinted"), default="blind",
                   help="which name signal 1 reads a pole by (default blind, the submitted surface)")
    _cost_flags(p, 3.0)
    p.set_defaults(func=cmd_granularity)

    p = sub.add_parser("submit", help="write a run's candidates.jsonl and submit it (no API cost; gated on M1 + M3)")
    p.add_argument("--granularity", type=int, required=True, choices=P.GRANULARITIES)
    p.add_argument("--run-id", required=True)
    sel = p.add_mutually_exclusive_group()
    sel.add_argument("--poles-file", type=Path, default=None, help="pole ids, one a line (c017a)")
    sel.add_argument("--all-poles", "--all-trait-poles", action="store_true", dest="all_poles",
                     help="every named pole of a kept cluster (there is no trait gate since QUESTIONS 48; the "
                          "old spelling --all-trait-poles still works and means the same)")
    p.add_argument("--label-choice", choices=("blind", "hinted"), default="blind")
    _cost_flags(p, 8.0)
    p.set_defaults(func=cmd_submit)

    p = sub.add_parser("report", help="evaluation.json, report.md and roger_sample.md for a run (no API cost)")
    p.add_argument("--run-id", required=True)
    p.add_argument("--census-table", type=Path, default=None, help="the census table (default the census generator's)")
    p.add_argument("--sample", type=int, default=40)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[Sequence[str]] = None) -> int:
    from assistant_axis.gapgen.runs import configure_logging
    configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
