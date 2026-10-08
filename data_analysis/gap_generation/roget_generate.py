#!/usr/bin/env python3
"""Workstream 2 of trait-gap generation: Roget's heads as a coverage map, WordNet clusters as a
sibling stream (``reports/trait_gap_generation/coding_plan_02_roget_wordnet.md``, as revised on
2026-10-08: no LLM passes, no recovery command; filtering, scoring and recovery are the platform's).

    uv run python data_analysis/gap_generation/roget_generate.py fetch [--force] [--dry-run]
    uv run python data_analysis/gap_generation/roget_generate.py parse [--allow-checksum-mismatch] [--fixture IDS]
    uv run python data_analysis/gap_generation/roget_generate.py pair [--sweep] [--position]
    uv run python data_analysis/gap_generation/roget_generate.py map [--embedder openai|hash] [--budget-usd 0.25]
    uv run python data_analysis/gap_generation/roget_generate.py coverage
    uv run python data_analysis/gap_generation/roget_generate.py harvest --run-id R [--every-nth K --offset J]
        [--per-head-cap 10] [--pair-top 3] [--classes ...] [--include-wn] [--force]
    uv run python data_analysis/gap_generation/roget_generate.py submit --run-id R [--generator roget|wn_clusters]

Every command takes ``--dry-run`` (prints what it would do; writes nothing, calls nothing).

* ``fetch``: Gutenberg #10681 into ``data/external/roget/pg10681.txt`` (gitignored), with the
  Project Gutenberg licence (the text's own closing section) as ``LICENSE.txt`` and a
  ``README.md`` recording the URL, date and SHA-256.  No API cost.
* ``parse``: ``data/candidates/roget/heads.json``; prints the census (heads, numbers, lettered
  heads, heads with adjectives, tags, drops).  ``--fixture`` writes the test fixture instead.
* ``pair``: ``head_pairs.json`` by rule (``pairs.rule_pairs``; WordNet from ``data/external/wn``);
  prints the known-pairs check (``known_pairs.json``) and, with ``--sweep``, the threshold sweep.
* ``map``: ``label_heads.json`` (lexical and semantic routes), ``map_spotcheck.md`` and the
  cumulative ``mapping_usage.json``.  The semantic route embeds head profiles and label texts with
  OpenAI ``text-embedding-3-large`` (direct key from ``.env``), cached under
  ``data/candidates/cache/embeddings/``: about 1,950 short texts, about $0.02 on a cold cache.
  ``--budget-usd`` is the hard cap (default $0.25).
* ``coverage``: ``roget_coverage.json`` and ``roget_coverage.md``.  No calls.
* ``harvest``: the run directory ``data/candidates/runs/roget/<R>/`` gets ``candidates.jsonl``
  (written before anything is submitted), ``pair_candidates.jsonl``, ``harvest_report.md`` and
  ``harvest_counts.json``; ``--include-wn`` also writes ``data/candidates/runs/wn_clusters/<R>/``.
  Prints the downstream (M1 and M3) estimate.  No calls.
* ``submit``: ``start_run``, ``submit_candidates`` (idempotent), ``RunContext.finish`` (``run.json``,
  ``usage.json``); prints the platform commands to run next.  Refuses without ``candidates.jsonl``.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import paths  # noqa: E402  (pins wn and HF in-tree)
from assistant_axis.gapgen.generators.roget import coverage as C  # noqa: E402
from assistant_axis.gapgen.generators.roget import harvest as H  # noqa: E402
from assistant_axis.gapgen.generators.roget import mapping as M  # noqa: E402
from assistant_axis.gapgen.generators.roget import pairs as PR  # noqa: E402
from assistant_axis.gapgen.generators.roget import parse as P  # noqa: E402

DEFAULT_OUT = paths.DATA_CANDIDATES / "roget"
DEFAULT_TEXT = paths.DATA_EXTERNAL / "roget" / "pg10681.txt"
FIXTURE_PATH = _REPO_ROOT / "assistant_axis" / "tests" / "fixtures" / "roget_sample.txt"
FIXTURE_IDS = "1,2,82,83,600-610,604a,609a,862-865,897,898"
EMBED_TOKENS_PER_TEXT = 70


def _ids(spec: str) -> list[str]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part and part.replace("-", "").isdigit():
            a, b = part.split("-")
            out.extend(str(n) for n in range(int(a), int(b) + 1))
        elif part:
            out.append(part)
    return out


def _lexicon(args):
    from assistant_axis.gapgen.generators.roget import wn_clusters as W
    if getattr(args, "no_wordnet", False):
        return None
    from assistant_axis.gapgen import wordnet as gw
    if not gw.oewn_installed():
        raise SystemExit("Open English WordNet is not in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn`")
    return W.Lexicon(W.oewn())


def _input(dep_key: str, path: Path, **extras):
    from assistant_axis.provenance import current_file_input
    return current_file_input(dep_key, Path(path), extras={k: str(v) for k, v in extras.items()} or None)


# --------------------------------------------------------------------------- fetch

LICENSE_START = "*** END OF THE PROJECT GUTENBERG EBOOK"


def cmd_fetch(args) -> int:
    dest = Path(args.text)
    if dest.exists() and not args.force:
        sha = P.sha256_of(dest)
        print(f"{dest} exists ({dest.stat().st_size:,} bytes, SHA-256 {sha}); pinned "
              f"{'matches' if sha == P.ROGET_EXPECTED_SHA256 else 'DIFFERS'}; --force downloads again")
        return 0
    if args.dry_run:
        print(f"DRY-RUN: would download {args.url} to {dest}, with LICENSE.txt and README.md beside it")
        return 0
    P.fetch_roget(dest, url=args.url)
    sha = P.sha256_of(dest)
    size = dest.stat().st_size
    pinned = P.ROGET_EXPECTED_SHA256
    print(f"{dest}: {size:,} bytes, SHA-256 {sha}")
    print("pinned SHA-256: " + ("matches" if sha == pinned else f"DIFFERS from {pinned} (pin the new value in "
                                                                 f"parse.ROGET_EXPECTED_SHA256 only after checking "
                                                                 f"the parser's invariants)"))
    write_license_and_readme(dest, url=args.url, sha=sha, size=size)
    return 0


def write_license_and_readme(dest: Path, *, url: str, sha: str, size: int) -> None:
    text = dest.read_text(encoding="utf-8")
    i = text.find(LICENSE_START)
    lic = text[i:] if i >= 0 else ""
    if lic:
        (dest.parent / "LICENSE.txt").write_text(lic, encoding="utf-8")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    readme = f"""# Roget's Thesaurus (1911), Project Gutenberg #10681

Downloaded by [roget_generate.py](../../../data_analysis/gap_generation/roget_generate.py) `fetch` for
workstream 2 of trait-gap generation
([coding_plan_02_roget_wordnet.md](../../../reports/trait_gap_generation/coding_plan_02_roget_wordnet.md)).

- Source: <{url}>
- Retrieved: {now} (UTC)
- File: [pg10681.txt](./pg10681.txt), {size:,} bytes, SHA-256 `{sha}`
  (pinned in [parse.py](../../../assistant_axis/gapgen/generators/roget/parse.py) as `ROGET_EXPECTED_SHA256`)
- Edition: "Release date: April 1, 2004 [eBook #10681]; Most recently updated: October 28, 2024";
  credits "Produced by L. John Old (Taken from Project Gutenberg's #22)".
- Licence: the Project Gutenberg License, copied from the end of the file into
  [LICENSE.txt](./LICENSE.txt) (the text itself is in the public domain in the United States).

This directory is gitignored (`/data/external/`); the derived files the project keeps are under
[data/candidates/roget/](../../candidates/roget/).
"""
    (dest.parent / "README.md").write_text(readme, encoding="utf-8")


# --------------------------------------------------------------------------- parse

def cmd_parse(args) -> int:
    text_path = Path(args.text)
    if not text_path.exists():
        raise SystemExit(f"{text_path} not found: run `roget_generate.py fetch` first")
    if args.fixture:
        ids = _ids(args.fixture)
        fx = P.extract_fixture(text_path.read_text(encoding="utf-8"), ids)
        if args.dry_run:
            print(f"DRY-RUN: would write {FIXTURE_PATH} ({len(fx.splitlines())} lines, {len(ids)} heads)")
            return 0
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(fx, encoding="utf-8")
        print(f"wrote {FIXTURE_PATH} ({len(fx.splitlines())} lines, {len(ids)} heads)")
        return 0
    try:
        idx = P.parse_file(text_path, allow_mismatch=args.allow_checksum_mismatch)
    except P.ChecksumMismatch as exc:
        raise SystemExit(str(exc))
    c = P.census(idx)
    print(json.dumps({k: v for k, v in c.items() if not isinstance(v, dict)}))
    print("drops:", json.dumps(c["drops"]))
    print("unknown bracket tags (kept, counted; extend parse.DROP_TAGS / KEEP_TAGS as needed):",
          json.dumps(dict(list(c["unknown_tags"].items())[:30])))
    out = Path(args.out) / "heads.json"
    if args.dry_run:
        print(f"DRY-RUN: would write {out}")
        return 0
    P.save_heads(idx, out, text_path=text_path)
    print(f"wrote {out}")
    return 0


def _load_index(args):
    p = Path(args.out) / "heads.json"
    if not p.exists():
        raise SystemExit(f"{p} not found: run `roget_generate.py parse` first")
    return P.load_heads(p), p


# --------------------------------------------------------------------------- pair

def cmd_pair(args) -> int:
    idx, heads_path = _load_index(args)
    lex = _lexicon(args)
    pairing = PR.rule_pairs(idx, lex, position_pass=args.position)
    known_path = Path(args.out) / "known_pairs.json"
    known = PR.load_known_pairs(known_path) if known_path.exists() else []
    chk = PR.check_known_pairs(idx, pairing, known)
    from collections import Counter
    disp = [h for h in idx.order if idx.heads[h].number >= P.DISPOSITIONAL_MIN]
    print("pairing (all heads):", json.dumps(dict(Counter(f"{x.kind}:{x.source}" for x in pairing.values()))))
    print("pairing (dispositional):", json.dumps(dict(Counter(f"{pairing[h].kind}:{pairing[h].source}" for h in disp))))
    print(f"known pairs: {len(chk['hit'])}/{chk['checked']} hit (recall {chk['recall']}); wrong {chk['wrong']}; "
          f"miss {chk['miss']}; dropped (titles differ) {chk['dropped']}")
    if args.sweep:
        for row in PR.threshold_sweep(idx, lex, known):
            print("  sweep", json.dumps(row))
    res = PR.residue(idx, pairing)
    print(f"unresolved heads: {sum(len(x) for _, x in res)} in {len(res)} subsections")
    out = Path(args.out) / "head_pairs.json"
    if args.dry_run:
        print(f"DRY-RUN: would write {out}")
        return 0
    inputs = [_input("roget_heads", heads_path)]
    if known_path.exists():
        inputs.append(_input("known_pairs", known_path))
    PR.save_pairs(pairing, out, inputs=inputs, meta={"position_pass": bool(args.position),
                                                      "known_pairs_check": {k: chk[k] for k in ("checked", "recall")}
                                                      | {"hit": len(chk["hit"]), "wrong": chk["wrong"],
                                                         "miss": chk["miss"], "dropped": chk["dropped"]}})
    print(f"wrote {out}")
    return 0


# --------------------------------------------------------------------------- map

def cmd_map(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.embed import EmbeddingCache, make_embedder
    from assistant_axis.judge_pricing import MultiModelUsage, cost_for_usage

    idx, heads_path = _load_index(args)
    lex = _lexicon(args)
    records = M.load_labels(Path(args.data_dir), Path(args.queue))
    if args.limit:
        records = records[: args.limit]
    head_ids = [h for h in idx.order if idx.heads[h].pos.get("Adj") or idx.heads[h].pos.get("N")]
    embedder = make_embedder(args.embedder)
    cache = EmbeddingCache(Path(args.cache_dir)) if args.cache_dir else EmbeddingCache()
    texts = [P.head_profile(idx.heads[h]) for h in head_ids] + [M.label_text(r) for r in records]
    _, missing = cache.lookup(embedder.tag, list(dict.fromkeys(texts)))
    est = cost_for_usage(embedder.usage_model, len(missing) * EMBED_TOKENS_PER_TEXT, 0)
    print(f"labels {len(records)} ({sum(r.source == 'existing' for r in records)} existing, "
          f"{sum(r.source == 'queued' for r in records)} queued); heads embedded {len(head_ids)}")
    print(f"estimate: {len(missing)} texts not cached x ~{EMBED_TOKENS_PER_TEXT} tokens at {embedder.usage_model} "
          f"rates = ${est:.4f} (cap --budget-usd ${args.budget_usd:.2f})")
    if est > args.budget_usd:
        raise SystemExit(f"REFUSED: estimate ${est:.4f} is over --budget-usd ${args.budget_usd:.2f}")
    if args.dry_run:
        print("DRY-RUN: no embedding call; would write label_heads.json, map_spotcheck.md, mapping_usage.json")
        return 0
    out_dir = Path(args.out)
    usage_path = out_dir / "mapping_usage.json"
    usage = GuardedUsage(budget_usd=args.budget_usd)
    try:
        assignments = M.map_labels(records, idx, lex=lex, embedder=embedder, cache=cache, usage=usage,
                                   head_ids=head_ids)
    finally:
        total = MultiModelUsage.load_or_create(usage_path) if usage_path.exists() else MultiModelUsage()
        total.merge_from(usage.plain())
        out_dir.mkdir(parents=True, exist_ok=True)
        total.write_json(usage_path)
        print(usage.log_line("[usage this run]"), file=sys.stderr)
        print(total.log_line("[usage cumulative]"), file=sys.stderr)
    inputs = [_input("roget_heads", heads_path), _input("seed_queue", Path(args.queue))]
    from assistant_axis.provenance import current_files_input
    inst = sorted((Path(args.data_dir) / "traits" / "instructions").glob("*.json"))
    inputs.append(current_files_input("trait_files", inst))
    M.save_label_heads(records, assignments, out_dir / "label_heads.json", inputs=inputs,
                       meta={"embedder": embedder.model_id, "n_heads_embedded": len(head_ids)})
    lh = M.load_label_heads(out_dir / "label_heads.json")
    (out_dir / "map_spotcheck.md").write_text(M.spotcheck_markdown(records, lh, idx), encoding="utf-8")
    print("routes:", json.dumps(M.route_counts(lh)))
    ex = [v for v in lh.values() if v["source"] == "existing"]
    print(f"existing labels with a primary head: {sum(1 for v in ex if v['primary'])}/{len(ex)}; "
          f"agree {sum(1 for v in ex if v['route'] == 'agree') / max(1, len(ex)):.0%}")
    print(f"wrote {out_dir / 'label_heads.json'}, {out_dir / 'map_spotcheck.md'}, {usage_path}")
    return 0


# --------------------------------------------------------------------------- coverage

def _coverage_inputs(out_dir: Path):
    return [_input(k, out_dir / f) for k, f in (("roget_heads", "heads.json"), ("head_pairs", "head_pairs.json"),
                                                 ("label_heads", "label_heads.json"))]


def _load_all(args):
    idx, _ = _load_index(args)
    out = Path(args.out)
    for f in ("head_pairs.json", "label_heads.json"):
        if not (out / f).exists():
            raise SystemExit(f"{out / f} not found: run `roget_generate.py {'pair' if 'pairs' in f else 'map'}` first")
    return idx, PR.load_pairs(out / "head_pairs.json"), M.load_label_heads(out / "label_heads.json")


def unresolved_note(idx, pairs) -> str:
    disp = [h for h in idx.order if idx.heads[h].number >= P.DISPOSITIONAL_MIN]
    n = sum(1 for h in disp if pairs[h].kind == "unresolved")
    return (f"Pairing by rule only (the plan's LLM pass for the residue was dropped in the 2026-10-08 revision): "
            f"{n} of {len(disp)} dispositional heads are unresolved and are treated as having no opposed head.")


def cmd_coverage(args) -> int:
    idx, pairs, lh = _load_all(args)
    rep = C.coverage(idx, pairs, lh)
    print(json.dumps({k: rep.summary[k] for k in ("n_heads", "class_i_iii_added", "covered_partly_uncovered",
                                                  "by_gap_class", "opposed_pairs", "labels")}, indent=1))
    out = Path(args.out)
    if args.dry_run:
        print(f"DRY-RUN: would write {out / 'roget_coverage.json'} and {out / 'roget_coverage.md'}")
        return 0
    C.write_coverage(rep, out / "roget_coverage.json", out / "roget_coverage.md", index=idx, label_heads=lh,
                     inputs=_coverage_inputs(out), unresolved_note=unresolved_note(idx, pairs))
    print(f"wrote {out / 'roget_coverage.json'}, {out / 'roget_coverage.md'}")
    return 0


# --------------------------------------------------------------------------- harvest

def known_stems(args) -> set[str]:
    recs = M.load_labels(Path(args.data_dir), Path(args.queue))
    return {r.stem for r in recs}


def cmd_harvest(args) -> int:
    paths.check_id(args.run_id, "run_id")
    idx, pairs, lh = _load_all(args)
    out = Path(args.out)
    cov_path = out / "roget_coverage.json"
    rep = C.load_coverage(cov_path) if cov_path.exists() else C.coverage(idx, pairs, lh)
    cfg = H.HarvestConfig(per_head_cap=args.per_head_cap, pair_top=args.pair_top, max_words=args.max_words,
                          classes=tuple(args.classes), every_nth=args.every_nth, offset=args.offset,
                          include_wn=args.include_wn)
    lex = _lexicon(args)
    known = known_stems(args)
    labels = {k: v.get("label") or k for k, v in lh.items()}
    res = H.harvest(rep, idx, pairs, cfg=cfg, known_stems=known, run_id=args.run_id, lex=lex, label_of=labels)
    print(json.dumps({k: v for k, v in res.counts.items() if k != "per_head"}, indent=1))
    run = paths.run_dir(H.GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
    wn_items, wn_cands = [], []
    if cfg.include_wn:
        from assistant_axis.gapgen.generators.roget import wn_clusters as W
        recs = M.load_labels(Path(args.data_dir), Path(args.queue))
        ants = W.harvest_wn_antonyms(recs, lex, known_stems=known)
        clos = W.harvest_trait_closure(lex, known_stems=known | {normalize(it.surface) for it in ants},
                                       max_depth=cfg.wn_closure_depth)
        wn_items = ants + clos
        wn_cands = H.wn_candidates(wn_items, run_id=args.run_id, every_nth=cfg.every_nth, offset=cfg.offset)
        print(f"WordNet stream: {len(ants)} antonyms of partner-less labels, {len(clos)} trait-closure adjectives; "
              f"{len(wn_cands)} candidates after --every-nth")
    if args.dry_run:
        print(f"DRY-RUN: would write {run}/candidates.jsonl ({len(res.candidates)} candidates)"
              + (f" and {paths.run_dir(H.WN_GENERATOR, args.run_id, candidates_dir=args.candidates_dir)}"
                 f"/candidates.jsonl ({len(wn_cands)})" if cfg.include_wn else ""))
        return 0
    if (run / "run.json").exists():
        raise SystemExit(f"{run} has a run.json: this run was submitted; use a new --run-id")
    if (run / "candidates.jsonl").exists() and not args.force:
        raise SystemExit(f"{run / 'candidates.jsonl'} exists: --force to overwrite (not yet submitted)")
    written = H.write_harvest(res, run, idx, run_id=args.run_id)
    print("wrote", ", ".join(str(p) for p in written.values()))
    if cfg.include_wn:
        wrun = paths.run_dir(H.WN_GENERATOR, args.run_id, candidates_dir=args.candidates_dir)
        if (wrun / "run.json").exists():
            raise SystemExit(f"{wrun} has a run.json: this run was submitted; use a new --run-id")
        H.write_candidates(wn_cands, wrun / "candidates.jsonl")
        import dataclasses
        (wrun / "wn_items.jsonl").write_text("".join(json.dumps(dataclasses.asdict(it), ensure_ascii=False) + "\n"
                                                     for it in wn_items), encoding="utf-8")
        print(f"wrote {wrun / 'candidates.jsonl'} ({len(wn_cands)}), {wrun / 'wn_items.jsonl'} ({len(wn_items)})")
    return 0


def normalize(s: str) -> str:
    from assistant_axis.entity_id import normalize_to_file_name
    return normalize_to_file_name(s)


# --------------------------------------------------------------------------- submit

def cmd_submit(args) -> int:
    from assistant_axis.gapgen import start_run, submit_candidates

    paths.check_id(args.run_id, "run_id")
    gen = args.generator
    run_d = paths.run_dir(gen, args.run_id, candidates_dir=args.candidates_dir)
    cpath = run_d / "candidates.jsonl"
    if not cpath.exists():
        raise SystemExit(f"{cpath} not found: run `roget_generate.py harvest --run-id {args.run_id}` first")
    cands = H.read_candidates(cpath)
    bad = [c for c in cands if c.generator != gen or c.run_id != args.run_id]
    if bad:
        raise SystemExit(f"{cpath}: {len(bad)} rows name another generator or run id")
    registry = Path(args.registry) if args.registry else paths.REGISTRY_PATH
    if args.dry_run:
        print(f"DRY-RUN: would submit {len(cands)} candidates from {cpath} to {registry} as {gen}/{args.run_id}")
        return 0
    before = cpath.read_bytes()
    run = start_run(gen, args.run_id, args={"command": "roget_generate.py submit", "generator": gen,
                                            "run_id": args.run_id, "candidates": str(cpath)},
                    candidates_dir=args.candidates_dir)
    rep = submit_candidates(cands, registry_path=registry, run=run)
    run.finish(n_emitted=len(cands))
    if cpath.read_bytes() != before:
        print(f"WARNING: {cpath} changed on submit (it should already hold every candidate)", file=sys.stderr)
    print(json.dumps({k: v for k, v in rep.as_dict().items() if k != "keys"} | {"n_keys": len(rep.keys)}))
    print(f"run directory: {run.dir} (run.json, usage.json: {run.usage.n_calls} calls, ${run.usage.total_cost_usd:.4f})")
    print("next (platform, run by Fable):")
    print(f"  uv run python data_analysis/gap_generation/traithood_filter.py --batch-id {gen}-{args.run_id} "
          f"--run {gen}/{args.run_id} --budget-usd <cap>")
    print(f"  uv run python data_analysis/gap_generation/novelty_score.py score --batch-id {gen}-{args.run_id} "
          f"--run {gen}/{args.run_id} --budget-usd <cap>")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--queue", type=Path, default=paths.SEED_QUEUE_PATH)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--text", type=Path, default=DEFAULT_TEXT)
    ap.add_argument("--candidates-dir", type=Path, default=None,
                    help="override data/candidates for run directories (tests)")
    ap.add_argument("--no-wordnet", action="store_true", help="skip WordNet (tests; weaker pairing and harvest)")
    ap.add_argument("--dry-run", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("fetch")
    sp.add_argument("--url", default=P.ROGET_URL)
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("parse")
    sp.add_argument("--allow-checksum-mismatch", action="store_true")
    sp.add_argument("--fixture", nargs="?", const=FIXTURE_IDS, default=None,
                    help=f"write the test fixture for these head ids (default {FIXTURE_IDS})")

    sp = sub.add_parser("pair")
    sp.add_argument("--sweep", action="store_true", help="print the confirmation-threshold sweep")
    sp.add_argument("--position", action="store_true",
                    help="also pair evidence-free neighbours by position (source 'position'; off by default)")

    sp = sub.add_parser("map")
    sp.add_argument("--embedder", default="openai", choices=["openai", "hash"])
    sp.add_argument("--budget-usd", type=float, default=0.25)
    sp.add_argument("--cache-dir", type=Path, default=None)
    sp.add_argument("--limit", type=int, default=None)

    sub.add_parser("coverage")

    sp = sub.add_parser("harvest")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--per-head-cap", type=int, default=10)
    sp.add_argument("--pair-top", type=int, default=3)
    sp.add_argument("--max-words", type=int, default=2)
    sp.add_argument("--classes", nargs="+", default=list(C.HARVEST_CLASSES), choices=list(C.GAP_CLASSES))
    sp.add_argument("--every-nth", type=int, default=None)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--include-wn", action="store_true")
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("submit")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--generator", default=H.GENERATOR, choices=[H.GENERATOR, H.WN_GENERATOR])
    sp.add_argument("--registry", type=Path, default=None)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"fetch": cmd_fetch, "parse": cmd_parse, "pair": cmd_pair, "map": cmd_map, "coverage": cmd_coverage,
            "harvest": cmd_harvest, "submit": cmd_submit}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
