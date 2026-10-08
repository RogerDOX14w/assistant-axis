#!/usr/bin/env python3
"""Workstream 2 of trait-gap generation: Roget's heads as a coverage map, WordNet clusters as a
sibling stream (``reports/trait_gap_generation/coding_plan_02_roget_wordnet.md``, as revised on
2026-10-08: no LLM passes, no recovery command; filtering, scoring and recovery are the platform's).

    uv run python data_analysis/gap_generation/roget_generate.py fetch [--force] [--dry-run]
    uv run python data_analysis/gap_generation/roget_generate.py parse [--allow-checksum-mismatch] [--fixture IDS]
    uv run python data_analysis/gap_generation/roget_generate.py pair [--sweep] [--position]
    uv run python data_analysis/gap_generation/roget_generate.py map [--embedder openai|hash] [--budget-usd 0.25]
        [--update | --force]
    uv run python data_analysis/gap_generation/roget_generate.py place-check [--budget-usd 5] [--resume] [--render STEMS]
        [--unchecked-only]
    uv run python data_analysis/gap_generation/roget_generate.py head-scope [--budget-usd 1] [--render IDS] [--force]
    uv run python data_analysis/gap_generation/roget_generate.py coverage [--head-scope F | --no-head-scope]
    uv run python data_analysis/gap_generation/roget_generate.py harvest --run-id R [--every-nth K --offset J]
        [--per-head-cap 10] [--pair-top 3] [--classes ...] [--include-wn] [--force] [--head-scope F | --no-head-scope]
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
  ``--budget-usd`` is the hard cap (default $0.25).  A full map refuses to overwrite a
  ``label_heads.json`` that holds placement-check records (``--force`` rebuilds anyway).
  ``--update`` (2026-10-08, after chunk 5) places again only the labels that need it
  (``mapping.plan_update``): keys with no trait file and no queue trait entry are dropped (a rename leaves
  its old stem behind; an old key is never remapped onto the new stem), labels with no entry are added,
  and labels whose text changed are placed again, found by the hash each entry records
  (``placed_text_sha256``) or, for an entry written before that, by the embedding cache confirmed by the
  recorded cosines.  The rest keep their placement and ``llm`` record (record fields refreshed, text
  hash added); a replaced entry keeps the old placement under ``previous_placement``.  The update is
  appended to the payload's ``map_updates``.  Then run ``place-check --unchecked-only --resume``.
* ``place-check``: the label placement check (QUESTIONS 39): every label in ``label_heads.json`` whose
  route was not ``agree`` goes to Sonnet 5.5 with its description and candidate heads (one label a
  call; rubric ``reports/trait_gap_generation/rubrics/roget_placement.md``, refused unless pinned); where
  Sonnet's head differs from the current primary, Opus 5.5 referees on the same prompt.  The answers go
  into each label's ``llm`` field, and ``primary`` / ``route`` change where the final answer does.
  Every call is appended to ``placement_responses.jsonl`` as it completes; ``--resume`` reuses the
  answers made there with the same rubric text, model and user turn (byte-identical).
  ``--unchecked-only`` checks only the labels with no check record yet (after ``map --update``, the
  re-placed ones) and leaves every other check record as it is.  The payload's ``placement_check`` holds
  the totals over the labels and every run's own record under ``runs``.  Usage: ``placement_usage.json``
  (cumulative); ``--budget-usd`` is the hard cap (default $5).  ``--render STEMS`` prints those labels'
  calls as sent and stops.
* ``head-scope``: one Haiku 5.5 rating per head of the coverage map's scope, 20 heads a call, of whether
  the head's adjectives describe a person's character (2 most, 1 some, 0 few or none; QUESTIONS 44;
  rubric ``reports/trait_gap_generation/rubrics/roget_head_scope.md``, refused unless pinned).  Writes
  ``head_scope.json``, the cumulative ``head_scope_usage.json`` and appends every response to
  ``head_scope_responses.jsonl``.  About 30 calls, a few cents; ``--budget-usd`` is the hard cap (default
  $1).  A rerun sends only the heads not yet rated under the same rubric and model (``--force``: all).
  ``--render IDS`` prints the calls that hold those heads, as sent, and stops.
* ``coverage``: ``roget_coverage.json`` and ``roget_coverage.md``.  No calls.  With the head-scope
  ratings (``--head-scope F``; default ``head_scope.json`` in ``--out`` when it exists; ``--no-head-scope``
  ignores it) the heads rated 0 are reported apart as "not character".
* ``harvest``: the run directory ``data/candidates/runs/roget/<R>/`` gets ``candidates.jsonl``
  (written before anything is submitted), ``pair_candidates.jsonl``, ``harvest_report.md`` and
  ``harvest_counts.json``; ``--include-wn`` also writes ``data/candidates/runs/wn_clusters/<R>/``.
  Prints the downstream (M1 and M3) estimate.  No calls.  ``--head-scope`` as for ``coverage``: the
  heads rated 0 are skipped (drop reason ``not_character``).
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

def _map_inputs(args, heads_path: Path) -> list:
    from assistant_axis.provenance import current_files_input
    inst = sorted((Path(args.data_dir) / "traits" / "instructions").glob("*.json"))
    return [_input("roget_heads", heads_path), _input("seed_queue", Path(args.queue)),
            current_files_input("trait_files", inst)]


def _merge_usage(usage, usage_path: Path) -> None:
    from assistant_axis.judge_pricing import MultiModelUsage
    total = MultiModelUsage.load_or_create(usage_path) if usage_path.exists() else MultiModelUsage()
    total.merge_from(usage.plain())
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    total.write_json(usage_path)
    print(usage.log_line("[usage this run]"), file=sys.stderr)
    print(total.log_line("[usage cumulative]"), file=sys.stderr)


def cmd_map_update(args) -> int:
    """``map --update``: place again only the labels that need it (``mapping.plan_update``)."""
    import numpy as np

    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.embed import EmbeddingCache, make_embedder, normalize_rows
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge_pricing import cost_for_usage

    if args.limit:
        raise SystemExit("--limit does not combine with --update")
    idx, heads_path = _load_index(args)
    out_dir = Path(args.out)
    lh_path = out_dir / "label_heads.json"
    if not lh_path.exists():
        raise SystemExit(f"{lh_path} not found: run `roget_generate.py map` first")
    lh = M.load_label_heads(lh_path)
    records = M.load_labels(Path(args.data_dir), Path(args.queue))
    head_ids = [h for h in idx.order if idx.heads[h].pos.get("Adj") or idx.heads[h].pos.get("N")]
    embedder = make_embedder(args.embedder)
    cache = EmbeddingCache(Path(args.cache_dir)) if args.cache_dir else EmbeddingCache()
    hp_texts = [P.head_profile(idx.heads[h]) for h in head_ids]
    hp_found, hp_miss = cache.lookup(embedder.tag, hp_texts)
    # the plan reads only the cache; the head matrix is read from it when every profile is there
    head_vecs = (normalize_rows(np.stack([hp_found[i] for i in range(len(hp_texts))]))
                 if not hp_miss else None)
    plan = M.plan_update(lh, records, cache=cache, embedder=embedder, head_ids=head_ids, head_vecs=head_vecs)
    by = {r.stem: r for r in records}
    sel_texts = list(dict.fromkeys(M.label_text(by[s]) for s in plan.selected))
    _, sel_miss = cache.lookup(embedder.tag, sel_texts)
    n_embed = len(hp_miss) + len(sel_miss)
    est = cost_for_usage(embedder.usage_model, n_embed * EMBED_TOKENS_PER_TEXT, 0)
    from collections import Counter
    print(f"labels {len(records)} ({sum(r.source == 'existing' for r in records)} existing, "
          f"{sum(r.source == 'queued' for r in records)} queued); entries in {lh_path.name}: {len(lh)}")
    print(f"dropped {len(plan.dropped)} (no trait file, no queue trait entry): "
          + (", ".join(f"{s} (was on {lh[s].get('primary') or 'no head'})" for s in plan.dropped) or "-"))
    print(f"added {len(plan.added)}: {', '.join(plan.added) or '-'}")
    print(f"changed text {len(plan.changed)} (found by {dict(Counter(plan.changed.values()))}); unchanged "
          f"{len(plan.unchanged)} (confirmed by {dict(Counter(plan.unchanged.values()))})")
    print(f"record fields to refresh on kept entries: {sum(1 for s in plan.metadata if s not in set(plan.selected))}")
    print(f"re-placing {len(plan.selected)} labels; estimate: {n_embed} texts not cached x ~{EMBED_TOKENS_PER_TEXT} "
          f"tokens at {embedder.usage_model} rates = ${est:.4f} (cap --budget-usd ${args.budget_usd:.2f})")
    if hp_miss:
        print(f"note: {len(hp_miss)} head profiles not cached; cache hits counted unchanged without the cosine check")
    if est > args.budget_usd:
        raise SystemExit(f"REFUSED: estimate ${est:.4f} is over --budget-usd ${args.budget_usd:.2f}")
    if args.dry_run:
        print("DRY-RUN: no embedding call; would rewrite label_heads.json and add to mapping_usage.json")
        return 0
    lex = _lexicon(args)
    usage = GuardedUsage(budget_usd=args.budget_usd)
    try:
        if head_vecs is None:   # embed the missing profiles, then confirm the cache hits as planned
            head_vecs = M.head_matrix(idx, head_ids, embedder=embedder, cache=cache, usage=usage)
            plan = M.plan_update(lh, records, cache=cache, embedder=embedder, head_ids=head_ids, head_vecs=head_vecs)
        new_lh, summary = M.update_label_heads(lh, records, idx, plan, now=utc_now(), lex=lex, embedder=embedder,
                                               cache=cache, usage=usage, head_ids=head_ids)
    finally:
        _merge_usage(usage, out_dir / "mapping_usage.json")
    from assistant_axis.gapgen.generators.roget import placement as PL
    env = json.loads(lh_path.read_text(encoding="utf-8"))
    payload = env.get("result", env)
    summary = {"at": utc_now(), "embedder": embedder.model_id, "cost_usd": round(usage.total_cost_usd, 6),
               **summary}
    updates = {"map_updates": list(payload.get("map_updates") or []) + [summary]}
    if payload.get("placement_check"):      # the re-placed labels' check records moved: recount the totals
        updates["placement_check"] = PL.cumulative_meta(payload["placement_check"], None, new_lh)
    M.rewrite_label_heads(lh_path, new_lh, extra_inputs=_map_inputs(args, heads_path), updates=updates)
    n_check = sum(1 for s in plan.selected if new_lh[s]["route"] != "agree")
    print("routes of the re-placed labels:", json.dumps(summary["routes_replaced"]))
    print("routes now:", json.dumps(M.route_counts(new_lh)))
    print(f"wrote {lh_path}; {n_check} re-placed labels are not `agree`: next, "
          f"`roget_generate.py place-check --unchecked-only --resume --budget-usd <cap>`")
    return 0


def cmd_map(args) -> int:
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.embed import EmbeddingCache, make_embedder
    from assistant_axis.judge_pricing import cost_for_usage

    if args.update:
        return cmd_map_update(args)
    lh_path = Path(args.out) / "label_heads.json"
    if lh_path.exists() and not args.force and not args.dry_run:
        checked = sum(1 for v in M.load_label_heads(lh_path).values() if v.get("llm"))
        if checked:
            raise SystemExit(f"REFUSED: {lh_path} holds {checked} placement-check records, which a full map "
                             f"would discard: use `map --update` (places again only new and changed labels), "
                             f"or --force to rebuild from scratch")
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
        _merge_usage(usage, usage_path)
    inputs = _map_inputs(args, heads_path)
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


# --------------------------------------------------------------------------- head scope

def _head_scope(args):
    """The head-scope ratings to apply: ``--head-scope F``, else ``head_scope.json`` in ``--out`` when it
    exists; ``None`` with ``--no-head-scope`` or when there is no file."""
    from assistant_axis.gapgen.generators.roget import head_scope as S
    if getattr(args, "no_head_scope", False):
        return None
    given = getattr(args, "head_scope", None)
    if given is not None:
        if not Path(given).exists():
            raise SystemExit(f"--head-scope {given}: not found (run `roget_generate.py head-scope`)")
        return S.load(Path(given))
    default = Path(args.out) / S.FILE_NAME
    return S.load(default) if default.exists() else None


def _anthropic_client():
    import anthropic
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    return anthropic.AsyncAnthropic(max_retries=0)


def cmd_head_scope(args) -> int:
    import asyncio

    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.roget import head_scope as S
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import MultiModelUsage

    idx, pairs, lh = _load_all(args)
    scope = [r.id for r in C.coverage(idx, pairs, lh).rows]
    try:
        rubric = S.load_rubric(args.rubrics_dir)
    except S.RubricNotPinned as exc:
        if not args.render:
            raise SystemExit(f"REFUSED: {exc}")
        # a draft is rendered to be read before it is pinned
        from assistant_axis.gapgen import split_rubrics as sr
        print(f"(rendering the unpinned draft: {str(exc).splitlines()[0]})", file=sys.stderr)
        rubric = {"name": S.RUBRIC_NAME, "text": sr.load_prompt(S.RUBRIC_NAME, args.rubrics_dir), "version": None,
                  "sha256": None}
    items, skipped = S.scope_items(idx, scope, max_adjectives=args.max_adjectives)
    out = Path(args.out)
    path = out / S.FILE_NAME
    prev = S.load(path) if path.exists() and not args.force else None
    keep = S.reusable(prev, rubric=rubric, model=args.model)
    todo = [it for it in items if it.id not in keep]
    if args.limit:
        todo = todo[: args.limit]
    batches = S.make_batches(todo, args.batch_size)
    system = rubric["text"]
    if args.render:
        want = set(_ids(args.render))
        every = S.make_batches(items, args.batch_size)
        print("SYSTEM:\n" + system + "\n")
        for bi, b in enumerate(every):
            if want & {it.id for it in b}:
                print(f"USER (call {bi + 1} of {len(every)}, heads {b[0].id}-{b[-1].id}):\n{S.render_user(b)}\n")
        return 0
    est = S.estimate(batches, system, args.model)
    cache = S.should_cache(system, args.model)
    print(f"heads in scope {len(scope)}: {len(items)} with adjectives, {len(skipped)} without (skipped); "
          f"{len(keep)} already rated under rubric version {rubric['version']} on {args.model} (kept); "
          f"{len(todo)} to rate in {len(batches)} calls of at most {args.batch_size}")
    print(f"estimate: {est['n_calls']} calls, {est['in_tok']:,} input and {est['out_tok']:,} output tokens at "
          f"{args.model} rates = ${est['usd']:.4f} (cap --budget-usd ${args.budget_usd:.2f}); system prompt "
          f"{'cached' if cache else 'sent uncached (under the caching minimum)'}")
    if est["usd"] > args.budget_usd:
        raise SystemExit(f"REFUSED: estimate ${est['usd']:.4f} is over --budget-usd ${args.budget_usd:.2f}")
    if args.dry_run:
        print("DRY-RUN: no call; the first three prompts as sent (system prompt = the rubric block):")
        for b in batches[:3]:
            print(S.render_user(b) + "\n")
        return 0
    if not batches:
        print("nothing to rate")
    usage_path = out / S.USAGE_NAME
    usage = GuardedUsage(budget_usd=args.budget_usd)
    res = S.RateResult()
    try:
        if batches:
            res = asyncio.run(S.rate_batches(batches, client=_anthropic_client(), model=args.model, system=system,
                                             usage=usage, concurrency=args.concurrency, cache_system=cache,
                                             rubric_version=rubric["version"], now=utc_now))
    finally:
        total = MultiModelUsage.load_or_create(usage_path) if usage_path.exists() else MultiModelUsage()
        total.merge_from(usage.plain())
        out.mkdir(parents=True, exist_ok=True)
        total.write_json(usage_path)
        print(usage.log_line("[usage this run]"), file=sys.stderr)
        print(total.log_line("[usage cumulative]"), file=sys.stderr)
    S.append_responses(res.log, out / S.RESPONSES_NAME)
    n_ok, n_total = res.parse_rate()
    warn_if_low_parse_rate(label=f"roget head_scope:{args.model}", n_ok=n_ok, n_total=n_total)
    payload = S.build_payload(idx, scope, skipped, res.rows, res.errors, model=args.model, rubric=rubric,
                              batch_size=args.batch_size, max_adjectives=args.max_adjectives, previous=keep,
                              extra={"last_run": {"at": utc_now(), "n_calls": len(res.log),
                                                  "n_retries": sum(1 for r in res.log if r["attempt"] > 1),
                                                  "cost_usd": round(usage.total_cost_usd, 6),
                                                  "estimate": est, "cache_system": cache,
                                                  "concurrency": args.concurrency, "parse_rate": [n_ok, n_total],
                                                  "stopped_by_budget": res.stopped_by_budget}})
    inputs = _coverage_inputs(out) + [_input("head_scope_rubric", sr_path(rubric), version=rubric["version"],
                                             sha256=rubric["sha256"])]
    S.save(payload, path, inputs=inputs)
    print(json.dumps(payload["summary"]))
    print(f"wrote {path}, {usage_path}, {out / S.RESPONSES_NAME}")
    if res.stopped_by_budget:
        print(f"STOPPED at --budget-usd ${args.budget_usd:.2f}: rerun to rate the rest", file=sys.stderr)
        return 2
    return 0


def cmd_place_check(args) -> int:
    import asyncio

    from assistant_axis.gapgen import split_rubrics as sr
    from assistant_axis.gapgen.cost import GuardedUsage
    from assistant_axis.gapgen.generators.roget import placement as PL
    from assistant_axis.gapgen.registry import utc_now
    from assistant_axis.judge import warn_if_low_parse_rate
    from assistant_axis.judge_pricing import MultiModelUsage
    from assistant_axis.provenance import current_files_input

    idx, heads_path = _load_index(args)
    out = Path(args.out)
    lh_path = out / "label_heads.json"
    if not lh_path.exists():
        raise SystemExit(f"{lh_path} not found: run `roget_generate.py map` first")
    lh = M.load_label_heads(lh_path)
    records = M.load_labels(Path(args.data_dir), Path(args.queue))
    want = [x.strip() for x in args.render.split(",")] if args.render else None
    items, skipped = PL.select_items(lh, records, idx, stems=want, unchecked_only=args.unchecked_only)
    if args.sample:
        import random
        items = sorted(random.Random(args.seed).sample(items, min(args.sample, len(items))), key=lambda it: it.stem)
    if args.limit:
        items = items[: args.limit]
    try:
        rubric = PL.load_rubric(args.rubrics_dir)
    except PL.RubricNotPinned as exc:
        if not args.render:
            raise SystemExit(f"REFUSED: {exc}")
        print(f"(rendering the unpinned draft: {str(exc).splitlines()[0]})", file=sys.stderr)
        rubric = {"name": PL.RUBRIC_NAME, "text": sr.load_prompt(PL.RUBRIC_NAME, args.rubrics_dir), "version": None,
                  "sha256": None}
    system = rubric["text"]
    if args.render:
        print("SYSTEM:\n" + system + "\n")
        for it in items:
            print(f"USER ({it.stem}; current primary {it.current or 'none'}, route {it.route}; not shown to the "
                  f"model):\n{PL.render_user(it, idx)}\n")
        return 0
    sha = sr.sha256(system)
    resp_path = out / PL.RESPONSES_NAME
    prev = PL.read_responses(resp_path) if args.resume else []
    # reuse only an answer to the same rubric text and the same user turn, byte for byte
    users = {it.stem: PL.render_user(it, idx) for it in items}
    s_done = PL.reusable_answers(prev, stage="sonnet", model=args.sonnet_model, prompt_sha=sha, users=users)
    o_done = PL.reusable_answers(prev, stage="opus", model=args.opus_model, prompt_sha=sha, users=users)
    by = {it.stem: it for it in items}
    todo_s = [it for it in items if it.stem not in s_done]
    est_s = PL.estimate(todo_s, idx, system, args.sonnet_model, "sonnet")
    est_o_all = PL.estimate(items, idx, system, args.opus_model, "opus")
    n_ref_guess = int(round(len(items) * args.referee_share))
    est_o = PL.estimate(items, idx, system, args.opus_model, "opus", n_calls=n_ref_guess)
    print(f"labels to check {len(items)} (route not agree; {skipped['agree']} agree left as they are; "
          + (f"{skipped['checked']} already checked left as they are (--unchecked-only); " if args.unchecked_only else "")
          + f"{len(skipped['no_record'])} with no corpus file or queue entry, {len(skipped['no_candidates'])} with no "
          f"candidate head, skipped); by source {dict(__import__('collections').Counter(it.source for it in items))}")
    if args.resume:
        print(f"resume: {len(s_done)} Sonnet and {len(o_done)} Opus answers reused from {resp_path}")
    print(f"estimate: Sonnet {est_s['n_calls']} calls, {est_s['in_tok']:,} in / {est_s['out_tok']:,} out = "
          f"${est_s['usd']:.2f}; Opus on about {args.referee_share:.0%} of the labels ({n_ref_guess} calls) "
          f"${est_o['usd']:.2f}, on all of them ${est_o_all['usd']:.2f}; cap --budget-usd ${args.budget_usd:.2f}")
    if est_s["usd"] + est_o["usd"] > args.budget_usd:
        raise SystemExit(f"REFUSED: estimate ${est_s['usd'] + est_o['usd']:.2f} is over --budget-usd "
                         f"${args.budget_usd:.2f}")
    if args.dry_run:
        print("DRY-RUN: no call; the first three Sonnet prompts as sent (system prompt = the rubric block):")
        for it in todo_s[:3]:
            print(PL.render_user(it, idx) + "\n")
        return 0
    usage_path = out / PL.USAGE_NAME
    usage = GuardedUsage(budget_usd=args.budget_usd)
    s_res, o_res = PL.StageResult(), PL.StageResult()
    sonnet, opus = dict(s_done), {}
    stopped = False
    client = None

    def record(rec: dict) -> None:
        PL.append_response(rec, resp_path)

    try:
        if todo_s:
            client = _anthropic_client()
            s_res = asyncio.run(PL.run_stage(todo_s, idx, stage="sonnet", client=client, model=args.sonnet_model,
                                             system=system, usage=usage, concurrency=args.concurrency,
                                             cache_system=True, rubric_version=rubric["version"], now=utc_now,
                                             on_record=record))
            sonnet.update(s_res.answers)
            stopped = s_res.stopped_by_budget
        ref = [it for it in items if PL.needs_referee(it, sonnet.get(it.stem))]
        opus = {it.stem: o_done[it.stem] for it in ref if it.stem in o_done}
        todo_o = [it for it in ref if it.stem not in o_done]
        print(f"referee: Sonnet differs from the current primary on {len(ref)} of {len(sonnet)} labels; "
              f"{len(todo_o)} Opus calls to make "
              f"(estimate ${PL.estimate(todo_o, idx, system, args.opus_model, 'opus')['usd']:.2f})")
        if todo_o and not stopped:
            client = client or _anthropic_client()
            o_res = asyncio.run(PL.run_stage(todo_o, idx, stage="opus", client=client, model=args.opus_model,
                                             system=system, usage=usage, concurrency=args.concurrency,
                                             cache_system=True, rubric_version=rubric["version"], now=utc_now,
                                             on_record=record))
            opus.update(o_res.answers)
            stopped = stopped or o_res.stopped_by_budget
    finally:
        total = MultiModelUsage.load_or_create(usage_path) if usage_path.exists() else MultiModelUsage()
        total.merge_from(usage.plain())
        out.mkdir(parents=True, exist_ok=True)
        total.write_json(usage_path)
        print(usage.log_line("[usage this run]"), file=sys.stderr)
        print(total.log_line("[usage cumulative]"), file=sys.stderr)
    for name, res, n in (("sonnet", s_res, len(todo_s)), ("opus", o_res, None)):
        n_total = n if n is not None else len(res.answers) + len(res.errors)
        warn_if_low_parse_rate(label=f"roget place-check:{name}", n_ok=len(res.answers), n_total=n_total)
        if res.errors:
            print(f"{name}: no usable answer for {len(res.errors)} labels: "
                  f"{dict(__import__('collections').Counter(res.errors.values()))}", file=sys.stderr)
    new_lh, counts = PL.apply_results(lh, items, sonnet, opus, rubric=rubric, checked_at=utc_now())
    cache = {"cache_read_input_tokens": sum((r.get("usage_raw") or {}).get("cache_read_input_tokens", 0)
                                            for r in s_res.log + o_res.log),
             "cache_creation_input_tokens": sum((r.get("usage_raw") or {}).get("cache_creation_input_tokens", 0)
                                                for r in s_res.log + o_res.log)}
    run_meta = {"rubric": {k: rubric[k] for k in ("name", "version", "sha256", "file")}, "models":
                {"sonnet": args.sonnet_model, "opus": args.opus_model}, "checked_at": utc_now(),
                "selection": "unchecked_only" if args.unchecked_only else "route_not_agree",
                "n_checked": len(items), "outcomes": counts,
                "n_referee": sum(1 for it in items if PL.needs_referee(it, sonnet.get(it.stem))),
                "n_reused": {"sonnet": len(s_done), "opus": len(o_done)},
                "cost_usd_this_run": round(usage.total_cost_usd, 4), "budget_usd": args.budget_usd, "cache": cache,
                "stopped_by_budget": stopped}
    prev_env = json.loads(lh_path.read_text(encoding="utf-8"))
    meta = PL.cumulative_meta(prev_env.get("result", prev_env).get("placement_check"), run_meta, new_lh)
    inst = sorted((Path(args.data_dir) / "traits" / "instructions").glob("*.json"))
    extra = [_input("placement_rubric", sr_path(rubric), version=rubric["version"], sha256=rubric["sha256"]),
             _input("placement_responses", resp_path), _input("placement_seed_queue", Path(args.queue)),
             current_files_input("placement_trait_files", inst)]
    PL.save_label_heads_checked(lh_path, new_lh, extra_inputs=extra, meta=meta)
    print(json.dumps({"this_run": run_meta, "totals": {k: v for k, v in meta.items() if k != "runs"},
                      "routes_now": M.route_counts(new_lh)}, indent=1))
    print(f"wrote {lh_path}, {usage_path}, {resp_path}")
    if stopped:
        print(f"STOPPED at --budget-usd ${args.budget_usd:.2f}: rerun with --resume to finish", file=sys.stderr)
        return 2
    return 0


def sr_path(rubric: dict) -> Path:
    p = Path(rubric["file"])
    return p if p.is_absolute() else _REPO_ROOT / p


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
    hs = _head_scope(args)
    rep = C.coverage(idx, pairs, lh, ratings=hs.ratings if hs else None, scope_meta=hs.meta() if hs else None)
    nc = rep.summary["not_character"]
    print(json.dumps({k: rep.summary[k] for k in ("n_heads", "class_i_iii_added", "covered_partly_uncovered",
                                                  "by_gap_class", "opposed_pairs", "labels", "head_scope")}
                     | {"not_character": {k: v for k, v in nc.items() if k != "heads"}}, indent=1))
    out = Path(args.out)
    if args.dry_run:
        print(f"DRY-RUN: would write {out / 'roget_coverage.json'} and {out / 'roget_coverage.md'}")
        return 0
    inputs = _coverage_inputs(out) + ([_input("head_scope", hs.path)] if hs else [])
    C.write_coverage(rep, out / "roget_coverage.json", out / "roget_coverage.md", index=idx, label_heads=lh,
                     inputs=inputs, unresolved_note=unresolved_note(idx, pairs))
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
    hs = _head_scope(args)
    res = H.harvest(rep, idx, pairs, cfg=cfg, known_stems=known, run_id=args.run_id, lex=lex, label_of=labels,
                    head_scope=hs.ratings if hs else None)
    res.counts["head_scope"] = hs.meta() if hs else None
    res.config["head_scope"] = hs.meta()["path"] if hs else None
    print(json.dumps({k: v for k, v in res.counts.items() if k not in ("per_head", "head_ratings")}, indent=1))
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
    first = not (run_d / "run.json").exists()
    try:
        rel = str(cpath.resolve().relative_to(_REPO_ROOT))
    except ValueError:
        rel = str(cpath)
    hc = run_d.parent.parent / H.GENERATOR / args.run_id / "harvest_counts.json"
    harvest_cfg = json.loads(hc.read_text())["config"] if hc.exists() else None
    run = start_run(gen, args.run_id, args={"command": "roget_generate.py submit", "generator": gen,
                                            "run_id": args.run_id, "candidates": rel,
                                            "harvest_config": harvest_cfg},
                    candidates_dir=args.candidates_dir)
    rep = submit_candidates(cands, registry_path=registry, run=run)
    # the harvest wrote candidates.jsonl, so record_candidates adds nothing: the first session counts
    # the run's candidates, a resubmission none (run.json sums n_emitted over sessions)
    run.finish(n_emitted=len(cands) if first else 0)
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

def _head_scope_flags(sp) -> None:
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--head-scope", type=Path, default=None,
                   help="head-scope ratings to apply (default: head_scope.json in --out when it exists)")
    g.add_argument("--no-head-scope", action="store_true", help="ignore the head-scope ratings")


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
    sp.add_argument("--update", action="store_true",
                    help="place again only new labels and labels whose text changed; drop stale keys; keep the rest")
    sp.add_argument("--force", action="store_true",
                    help="rebuild label_heads.json from scratch although it holds placement-check records")

    sp = sub.add_parser("place-check")
    sp.add_argument("--sonnet-model", default="claude-sonnet-5-5")
    sp.add_argument("--opus-model", default="claude-opus-5-5")
    sp.add_argument("--budget-usd", type=float, default=5.0)
    sp.add_argument("--concurrency", type=int, default=6)
    sp.add_argument("--referee-share", type=float, default=0.5,
                    help="share of the labels Opus is expected to referee, for the estimate only")
    sp.add_argument("--limit", type=int, default=None, help="check only the first N labels (sorted by stem)")
    sp.add_argument("--sample", type=int, default=None, metavar="N",
                    help="check a random sample of N labels (seeded by --seed), e.g. to measure tokens first")
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--resume", action="store_true",
                    help="reuse the answers in placement_responses.jsonl to a byte-identical prompt")
    sp.add_argument("--unchecked-only", action="store_true",
                    help="check only the labels with no check record yet (after `map --update`: the re-placed ones)")
    sp.add_argument("--render", default=None, metavar="STEMS",
                    help="print these labels' calls, as sent, and stop (no call, no write)")
    sp.add_argument("--rubrics-dir", type=Path, default=None, help=argparse.SUPPRESS)

    sp = sub.add_parser("head-scope")
    sp.add_argument("--model", default="claude-haiku-5-5")
    sp.add_argument("--batch-size", type=int, default=20)
    sp.add_argument("--max-adjectives", type=int, default=20)
    sp.add_argument("--budget-usd", type=float, default=1.0)
    sp.add_argument("--concurrency", type=int, default=4)
    sp.add_argument("--limit", type=int, default=None, help="rate only the first N heads still to rate")
    sp.add_argument("--force", action="store_true", help="rate every head again (ignore head_scope.json)")
    sp.add_argument("--render", default=None, metavar="IDS",
                    help="print the calls holding these head ids, as sent, and stop (no call, no write)")
    sp.add_argument("--rubrics-dir", type=Path, default=None, help=argparse.SUPPRESS)

    sp = sub.add_parser("coverage")
    _head_scope_flags(sp)

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
    _head_scope_flags(sp)

    sp = sub.add_parser("submit")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--generator", default=H.GENERATOR, choices=[H.GENERATOR, H.WN_GENERATOR])
    sp.add_argument("--registry", type=Path, default=None)
    # --dry-run is accepted after the command too (roget_generate.py harvest --run-id R --dry-run)
    for p in sub.choices.values():
        p.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS)
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return {"fetch": cmd_fetch, "parse": cmd_parse, "pair": cmd_pair, "map": cmd_map, "head-scope": cmd_head_scope,
            "place-check": cmd_place_check,
            "coverage": cmd_coverage, "harvest": cmd_harvest, "submit": cmd_submit}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
