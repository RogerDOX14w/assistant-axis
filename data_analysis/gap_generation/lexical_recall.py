#!/usr/bin/env python3
"""Workstream 11, lexical recall insurance for M3 (``reports/trait_gap_generation/coding_plan_11_novelty_ensemble.md``).

    uv run python data_analysis/gap_generation/lexical_recall.py build [--lexicons oewn moby] [--dry-run]
    uv run python data_analysis/gap_generation/lexical_recall.py labelled [--lexicons oewn moby] [--dry-run]
    uv run python data_analysis/gap_generation/lexical_recall.py dry [--rows all|trait|physical|states] [--batch-id B] [--dry-run]
    uv run python data_analysis/gap_generation/lexical_recall.py sweep --batch-id B [--rows ...] [--sample N --seed S]
        [--budget-usd 10] [--resume] [--dry-run] [--no-registry-write]
    uv run python data_analysis/gap_generation/lexical_recall.py report --batch-id B [--marks marks.json]
    uv run python data_analysis/gap_generation/lexical_recall.py marks --batch-id B [--n 40 --seed S] | --parse marked.md
    uv run python data_analysis/gap_generation/lexical_recall.py replay --batch-id B [--dry-run]
    uv run python data_analysis/gap_generation/lexical_recall.py reach --recovery-batch B [--dry-run]

* ``build`` ($0, seconds): the lookup table (``data/candidates/lexical/lookup.json``) over the corpus labels and the
  seed queue's live trait labels (with or without a text), in each lexicon; prints coverage per lexicon and kind and the
  name-only count; ``.bak.<UTC>`` copy of a table it replaces with different content.
* ``labelled`` ($0): the workstream plan's § 6 measurement over M2's labelled pairs (recall on duplicates and antonyms,
  false flags on near-distinct and unrelated pairs, per lexicon and link type): ``labelled_readout.json``.
* ``dry`` ($0): the retroactive lookup over every kept row (an M3 block decided ``new`` or ``grey``): the lexical-only
  pairs with their cosines (cached embeddings only), antonym evidence, stem families, the free labels (Roger's merges,
  the gate audit's five retrieval misses), the sweep's estimate: ``dry_readout.{json,md}``; with ``--batch-id`` also
  the sweep's ``plan.json``.
* ``sweep`` (paid, live by default): the overlap call (rubric A, Sonnet then Opus) on every judgeable lexical-only pair,
  each under its row's own recorded rule set and cut-off (open decision 1: every pair; ``--sample`` for a seeded
  sample), capped by ``--budget-usd`` (default $10; OEWN's pairs all, Moby's by cosine down to the cap); writes
  ``pairs.jsonl`` before the first call, ``responses.jsonl`` as answers arrive, then ``results.jsonl``, the ``lexical``
  block of each swept row with a link (``Registry.update_many``, ``merge_blocks=False``: never the ``novelty`` block;
  ``--no-registry-write`` leaves the registry alone), ``registry_writes.jsonl``, ``sweep_report.{json,md}``,
  ``usage.json`` (always, in a ``finally``) and ``run.json``.  The sweep never flips an M3 decision.
* ``report`` ($0): ``sweep_report.{json,md}`` again, with Roger's blind marks folded in when given; the stop-rule line
  first.
* ``marks`` ($0): the blind-marks sheet for Roger (up to 40 covers, shuffled, no readings; the cover audit's form):
  ``reports/trait_gap_generation/lexical_covers_for_marks.md`` and the seeded ``marks/key.json``; ``--parse`` reads
  the marked sheet back into ``marks/marks.json``.
* ``replay`` ($0): the sweep's ``registry_writes.jsonl`` applied to a registry (another checkout's), idempotently.
* ``reach`` ($0; task 8, dry): over a recovery run's hidden set, the hidden traits its kept candidates did not
  recover that a kept candidate's lexical link reaches, by lexicon: ``recovery/<B>/lexical_reach.json``.

Roger's gate-2 decision (2026-10-14, option (d)): **no lexical link ever cuts**, whichever lexicon; a link read at
the row's own cut-off (``lexical_cover`` in the block) is a *proposed merge*, flagged for review (the review graph
and card: "dictionary (WordNet | Moby thesaurus): probably the same as X"), and the M3 decision stays.  The forward
path for a new M3 wave is this sweep restricted to it: ``build`` (when the corpus or the queue changed), then
``sweep --batch-id <wave>_lex --from-batches <wave M3 batch>`` (flag only; the ``novelty`` blocks untouched), then
the review graph as usual.  ``dry --from-batches`` leaves ``lexical/dry_readout.*`` (every kept row) alone.

Every dry run prints its counts and estimate and writes nothing; ``sweep --dry-run`` also prints one rendered pair per
variant (an OEWN pair with a corpus trait, a queue entry, a Moby pair, when there is one).  The system prompt is the
pinned rubric file, unchanged (``rubric_pins.py check``).
"""
from __future__ import annotations

import argparse
import hashlib
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
from assistant_axis.gapgen import lexical as LX  # noqa: E402
from assistant_axis.gapgen import lexical_sweep as LS  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import records as RF  # noqa: E402
from assistant_axis.gapgen import overlap_test as OT  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.prompt_labels import DEFAULT_LABEL_FORM  # noqa: E402
from assistant_axis.gapgen.registry import Registry, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import configure_logging, dirty_refusal, git_sha, log_formatter, \
    platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError  # noqa: E402

logger = logging.getLogger("lexical_recall")

SWEEP_SUBDIR = Path("lexical") / "sweep"
MARKS_SHEET = paths.REPO_ROOT / "reports" / "trait_gap_generation" / "lexical_covers_for_marks.md"
LABELLED_PATH = paths.CALIBRATION_DIR / "labelled_pairs.json"


# --------------------------------------------------------------------------- shared

def _lexical_dir(args) -> Path:
    return Path(args.out_root or paths.DATA_CANDIDATES) / "lexical"


def sweep_dir(args) -> Path:
    return Path(args.out_root or paths.DATA_CANDIDATES) / SWEEP_SUBDIR / paths.check_id(args.batch_id, "batch_id")


def _load_queue(data_dir: Path) -> tuple[dict, Path]:
    import data_analysis.seed_entities as se
    qp = Path(data_dir) / "seed_queue.json"
    return (se.load_queue(qp) if qp.exists() else {"entries": []}), qp


def _sha(path: Path) -> Optional[str]:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _write_json(obj, path: Path, *, title: Optional[str] = None, inputs=None, envelope: bool = True) -> None:
    from assistant_axis.plot_metadata import json_metadata
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = json_metadata(obj, title=title, inputs=inputs or None) if envelope else obj
    atomic_write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", path)


def _read_json(path: Path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc["result"] if isinstance(doc, dict) and isinstance(doc.get("result"), dict) else doc


def _read_jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not RF.exists(p):
        return []
    return RF.read_jsonl(p)


def _lexicons(args) -> dict:
    return LX.default_lexicons(args.lexicons, moby_path=getattr(args, "moby_path", None))


def _corpus_labels(corpus) -> dict:
    return {s: t.label for s, t in corpus.items()}


# --------------------------------------------------------------------------- build

def cmd_build(args) -> int:
    from assistant_axis.gapgen.recovery import corpus_fingerprint
    from assistant_axis.provenance import current_file_input
    corpus = NV.load_trait_corpus(args.data_dir)
    queue, qp = _load_queue(args.data_dir)
    entries, qrec = LX.live_queue_entries(queue, corpus)
    lex = _lexicons(args)
    extra = {"built_at": utc_now(), "corpus_fingerprint": corpus_fingerprint(args.data_dir),
             "n_trait_files": len(corpus), "queue": {"path": str(qp), "sha256": _sha(qp), **qrec}}
    lookup = LX.build_lookup(corpus, entries, lexicons=lex, extra_header=extra)
    h = lookup.header
    for name, cov in h["coverage"].items():
        print(f"{name} coverage: " + "; ".join(f"{k} {v['found']} of {v['of']}" for k, v in cov.items()))
    print(f"targets: {h['n_corpus']} corpus traits, {h['n_queue']} live queue entries ({h['n_queue_name_only']} with no "
          f"text: name-only links); content sha256 {h['content_sha256'][:12]}")
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    out = Path(args.lookup)
    if out.exists():
        try:
            old = LX.read_lookup_doc(out)["header"].get("content_sha256")
        except (ValueError, KeyError, json.JSONDecodeError):
            old = None
        if old != h["content_sha256"]:
            bak = out.with_name(f"{out.name}.bak.{utc_stamp()}")
            shutil.copy2(out, bak)
            print(f"the old table differs: copied to {bak}")
    inputs = [current_file_input(dep_key="seed_queue", path=qp)] if qp.exists() else []
    wn_db = paths.wn_data_dir() / "wn.db"
    if "oewn" in lex and wn_db.exists():
        inputs.append(current_file_input(dep_key="oewn_db", path=wn_db))
    if "moby" in lex and getattr(lex["moby"], "path", None):
        inputs.append(current_file_input(dep_key="moby", path=lex["moby"].path))
    LX.save_lookup(lookup, out, inputs=inputs)
    print(f"wrote {out}")
    return 0


# --------------------------------------------------------------------------- labelled

def cmd_labelled(args) -> int:
    from assistant_axis.provenance import current_file_input
    doc = _read_json(args.labelled)
    pairs = doc["pairs"]
    corpus = NV.load_trait_corpus(args.data_dir)
    lex = _lexicons(args)
    m = LX.labelled_measurement(pairs, lex, corpus_labels=_corpus_labels(corpus), externals=doc.get("externals") or {})
    m["labelled_file"] = {"path": str(args.labelled), "sha256": _sha(args.labelled),
                          "schema_version": doc.get("schema_version"), "built_at": doc.get("built_at")}
    m["lexicons"] = {n: lx.info() for n, lx in lex.items()}
    print(LS.labelled_markdown(m))
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    out = _lexical_dir(args) / "labelled_readout.json"
    _write_json(m, out, title="lexical links on the labelled pairs (plan 11, gate 1)",
                inputs=[current_file_input(dep_key="labelled_pairs", path=Path(args.labelled))])
    print(f"wrote {out}")
    return 0


# --------------------------------------------------------------------------- the plan (dry and sweep)

def load_rows(args) -> dict:
    reg = Registry(args.registry)
    return reg.fold()


def _passes(value: str) -> tuple[str, ...]:
    return LS.PASSES if value == "all" else (value,)


def candidate_vectors(kept: dict, cfg, cache) -> dict:
    """The cached query embeddings of the kept rows (the text M3 embedded: its block's ``embedding`` settings); a row
    whose text is not in the cache has none (no embedding is ever made here)."""
    from assistant_axis.gapgen import embed as EM
    tag = EM.OpenAIEmbedder(cfg.live_model["model_id"]).tag
    keys, texts = [], []
    for k, r in kept.items():
        c = LS.candidate_for(r)
        if c is None:
            continue
        emb = (r.get("novelty") or {}).get("embedding") or {}
        texts.append(NV.query_text(c.label, c.gloss, query_form=emb.get("query_form") or NV.DEFAULT_QUERY_FORM,
                                   representation=emb.get("representation") or cfg.representation))
        keys.append(k)
    found, _missing = cache.lookup(tag, texts)
    return {keys[i]: v for i, v in found.items()}


class Refused(RuntimeError):
    """A refusal before anything is sent or written (the command exits 2)."""


def select_kept(rows: dict, passes, from_batches=None) -> tuple[dict, dict]:
    """``(kept, all_kept)``: the kept rows of ``passes`` (:func:`lexical_sweep.kept_rows`), restricted to those whose
    ``novelty.run_id`` is one of ``from_batches`` when given (one M3 wave: the forward path, plan 11 as Roger decided
    it on 2026-10-14), and all of them (the stem families look across waves).  A batch no row carries is refused."""
    all_kept = LS.kept_rows(rows, passes)
    if not from_batches:
        return all_kept, all_kept
    present = {(r.get("novelty") or {}).get("run_id") for r in rows.values()}
    unknown = [b for b in from_batches if b not in present]
    if unknown:
        raise Refused(f"no registry row carries novelty.run_id {', '.join(unknown)} (an M3 batch id, as "
                      "novelty_score.py score --batch-id wrote it)")
    want = set(from_batches)
    return {k: r for k, r in all_kept.items() if (r.get("novelty") or {}).get("run_id") in want}, all_kept


def build_plan(args, *, need_index: bool) -> dict:
    """Everything ``dry`` and ``sweep`` share: the kept rows, the lookup with its lexicons, the index and cached
    vectors, the items and per-row plans."""
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    from data_analysis.gap_generation import novelty_score as NS
    rows = load_rows(args)
    kept, all_kept = select_kept(rows, _passes(args.rows), getattr(args, "from_batches", None))
    names = getattr(args, "lexicons", None)
    lookup = LX.load_lookup(args.lookup, lexicons=LX.default_lexicons(names) if names else None)
    cfg = MetricConfig.load(args.metric_config)
    cache = EM.EmbeddingCache(args.cache_dir)
    index, info = NS.load_index(cfg, data_dir=args.data_dir, cache=cache, allow_embed=False, queue_search=True)
    if index is None:
        msg = (f"the corpus index is not fully cached ({info.get('n_missing_from_cache')} texts missing: "
               f"{info.get('missing')}); cosines are unavailable")
        if need_index:
            raise SystemExit(f"REFUSED: {msg}; the sweep needs the index for the targets' descriptions")
        print(f"WARNING: {msg}", file=sys.stderr)
    vectors = candidate_vectors(kept, cfg, cache)
    corpus = NV.load_trait_corpus(args.data_dir)
    descriptions = ({s: t.description for s, t in index.traits.items() if t.description} if index is not None
                    else {s: t.description for s, t in corpus.items() if t.description})
    fam_cands = {r["stem"]: r["label"] for r in all_kept.values()}
    items, plans = LS.sweep_plan(kept, lookup, index, vectors, descriptions=descriptions,
                                 candidates_for_family=fam_cands)
    return {"rows": rows, "kept": kept, "lookup": lookup, "cfg": cfg, "index": index, "vectors": vectors,
            "corpus": corpus, "descriptions": descriptions, "items": items, "plans": plans}


def render_pair(it: LS.PairItem, descriptions: dict, target_labels: dict, *, label_form: str = DEFAULT_LABEL_FORM) -> str:
    """The sweep's overlap user turn for one pair (``overlap_test.render_single``, as the runner builds it)."""
    pc = OT.PairCall(call_id=f"{it.key}>{it.stem}", set="m3", target=it.key, listed=[it.stem])
    corpus = {it.key: {"label": it.label, "description": it.gloss or ""},
              it.stem: {"label": target_labels.get(it.stem, it.stem.replace("_", " ")),
                        "description": descriptions.get(it.stem, "")}}
    return OT.render_single(pc, corpus, label_form=label_form)


def _target_labels(plan: dict) -> dict:
    out = {s: r["label"] for s, r in plan["lookup"].rows.items()}
    if plan.get("index") is not None:
        out.update({s: t.label for s, t in plan["index"].traits.items()})
    return out


def plan_snapshot(plan: dict, items, *, batch_id: Optional[str], cap: Optional[dict] = None,
                  sample: Optional[dict] = None) -> dict:
    """``plan.json``: the pairs, and per kept row a snapshot of its ``novelty`` block (``at``, decision, run, sha256)
    for the acceptance check that the sweep left it alone, with its antonym evidence and family."""
    kept, plans = plan["kept"], plan["plans"]
    rows = {}
    for k, r in kept.items():
        nv = r.get("novelty") or {}
        p = plans[k]
        rows[k] = {"pass": p.pass_, "novelty_at": nv.get("at"), "novelty_decision": nv.get("decision"),
                   "novelty_run_id": nv.get("run_id"), "novelty_sha256": LS.block_sha256(nv),
                   "cut_off_rule": p.spec.as_dict(), "rules": p.rules.name,
                   "antonyms": [a.as_dict() for a in p.antonyms], "family": p.family,
                   "listed_by_m3": [it.stem for it in p.links if it.listed_by_m3]}
    return {"batch_id": batch_id, "lookup_sha256": plan["lookup"].content_sha256,
            "lexicons": plan["lookup"].lexicon_versions, "n_rows": len(kept),
            "n_items": len(items), "n_judged": sum(1 for it in items if it.judged), "cap": cap, "sample": sample,
            "items": [it.as_dict() for it in items], "rows": rows, "written_at": utc_now()}


# --------------------------------------------------------------------------- dry

def cmd_dry(args) -> int:
    try:
        plan = build_plan(args, need_index=False)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    items = plan["items"]
    cap = LS.cap_items(items, args.budget_usd)
    est = LS.sweep_estimate(sum(1 for it in items if it.judged))
    readout = LS.dry_readout(kept=plan["kept"], items=items, plans=plan["plans"], lookup=plan["lookup"], estimate=est,
                             corpus_labels=_corpus_labels(plan["corpus"]), cap=cap)
    p = readout["pairs"]
    print(f"kept rows {readout['kept_rows']['n']}; rows with lexical-only pairs {p['n_rows_with_links']} "
          f"({p['n_rows_with_links_single_word']} single words); pairs {p['n_pairs']} ({p['by_link']}; {p['by_kind']}); "
          f"judgeable {p['n_judgeable']}; already listed by M3 {p['n_listed_by_m3']}; name-only {p['name_only_links']}")
    print("audit retrieval misses reached: " + ", ".join(k for k, v in readout["audit_retrieval_misses"].items()
                                                         if v["reached"]))
    print(f"Roger's merges into the lexical target: {readout['free_labels']['lexical_target_merges']}")
    print("estimate:\n" + est.format())
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    lexdir = _lexical_dir(args)
    if args.from_batches:               # one wave: the gate-1 readout of every kept row is left as it is
        print("--from-batches: lexical/dry_readout.* left alone (they describe every kept row)")
    else:
        labelled = None
        lp = lexdir / "labelled_readout.json"
        if lp.exists():
            labelled = _read_json(lp)
        _write_json(readout, lexdir / "dry_readout.json", title="lexical recall: the dry readout (plan 11, gate 1)")
        atomic_write_text(LS.dry_markdown(readout, labelled=labelled), lexdir / "dry_readout.md")
        print(f"wrote {lexdir / 'dry_readout.json'} and dry_readout.md")
    if args.batch_id:
        d = sweep_dir(args)
        _write_json(plan_snapshot(plan, items, batch_id=args.batch_id, cap=cap), d / "plan.json",
                    title=f"lexical sweep plan {args.batch_id}")
        print(f"wrote {d / 'plan.json'}")
    return 0


# --------------------------------------------------------------------------- sweep

def _apply_sample(items, n: Optional[int], seed: int) -> Optional[dict]:
    if not n:
        return None
    judged = [it for it in items if it.judged]
    keep = set(map(id, random.Random(f"lex:{seed}").sample(judged, min(n, len(judged)))))
    for it in judged:
        if id(it) not in keep:
            it.judged, it.not_judged = False, "not_sampled"
    return {"n": n, "seed": seed, "n_sampled": len(keep), "of": len(judged)}


def _variants(items) -> list:
    """One judged pair per variant, for the rendered prompts: OEWN to a corpus trait, OEWN to a queue entry, Moby."""
    out, seen = [], set()
    for it in items:
        if not it.judged:
            continue
        v = ("moby" if it.lexicon == "moby" else "oewn", it.kind)
        if v not in seen:
            seen.add(v)
            out.append(it)
    return out


def _prepare_out_dir(out_dir: Path, args) -> tuple[int, list]:
    records: list = []
    if out_dir.exists() and (out_dir / "run.json").exists():
        if args.resume:
            records = _read_jsonl(out_dir / "responses.jsonl")
            print(f"resuming {out_dir}: {len(records)} responses on record", file=sys.stderr)
        elif args.overwrite:
            bak = out_dir.with_name(f"{out_dir.name}.bak.{utc_stamp()}")
            shutil.move(str(out_dir), str(bak))
            print(f"moved the old run to {bak}", file=sys.stderr)
        else:
            print(f"{out_dir} has a run; choose a new --batch-id, pass --resume to continue it, or --overwrite",
                  file=sys.stderr)
            return 1, []
    elif args.resume:
        print(f"--resume: {out_dir} has no run to resume", file=sys.stderr)
        return 1, []
    out_dir.mkdir(parents=True, exist_ok=True)
    return 0, records


def row_usage(records) -> dict:
    """``{key: usage}`` (``novelty.usage_dict``) over every response record of the run, an earlier session's
    included, charged as the runner charges them (``novelty_runner.billed_from_raw``)."""
    from assistant_axis.judge_pricing import cost_for_usage
    per: dict = {}
    for rec in records or []:
        m = rec.get("charged_as")
        if not m or not rec.get("key"):
            continue
        p, o = NR.billed_from_raw(rec.get("usage_raw") or {})
        u = per.setdefault(rec["key"], {}).setdefault(m, {"n_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                                            "cost_usd": 0.0})
        u["n_calls"] += 1
        u["prompt_tokens"] += p
        u["completion_tokens"] += o
        u["cost_usd"] += cost_for_usage(m, p, o)
    return {k: NV.usage_dict(v) for k, v in per.items()}


def write_blocks(results, *, plan: dict, items, run_id: str, runner, out_dir: Path, registry_path: Optional[Path]
                 ) -> int:
    """The ``lexical`` block of every kept row with a lexical-only link, antonym evidence or a family, into
    ``registry_writes.jsonl`` and (``registry_path``) the registry, ``merge_blocks=False`` (the block replaced whole,
    every other field untouched); a row that already carries the same block (all but its ``at``) is not written
    again.  Returns the number of blocks in ``registry_writes.jsonl``."""
    by_key: dict = {}
    for it in items:
        by_key.setdefault(it.key, []).append(it)
    readings = {(r["key"], r["stem"]): r for r in results}
    usage = row_usage(runner.records if runner is not None else [])
    at = utc_now()
    updates, lines = {}, []
    for key, p in sorted(plan["plans"].items()):
        if not LS.needs_block(p):
            continue
        block = LS.lexical_block(plan["kept"][key], p.links, p.antonyms, p.family, readings, run_id=run_id,
                                 lookup=plan["lookup"], spec=p.spec, rules=p.rules, usage=usage.get(key), at=at)
        lines.append(json.dumps({"key": key, "lexical": block, "at": at}, ensure_ascii=False))
        cur = (plan["rows"].get(key) or {}).get("lexical")
        if isinstance(cur, dict) and {k: v for k, v in cur.items() if k != "at"} == \
                {k: v for k, v in block.items() if k != "at"}:
            continue                       # the same block is on the row already (a resumed or repeated run)
        updates[key] = {"lexical": block}
    atomic_write_text("".join(x + "\n" for x in lines), out_dir / "registry_writes.jsonl")
    if registry_path is not None and updates:
        Registry(registry_path).update_many(updates, merge_blocks=False)
    logger.info("lexical blocks: %d on record, %d written to the registry", len(lines),
                len(updates) if registry_path is not None else 0)
    return len(lines)


def cmd_sweep(args) -> int:
    from data_analysis.gap_generation import novelty_score as NS
    try:
        plan = build_plan(args, need_index=True)
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    items = plan["items"]
    sample = _apply_sample(items, args.sample, args.seed)
    cap = LS.cap_items(items, args.budget_usd, transport=args.transport)
    n_j = sum(1 for it in items if it.judged)
    est = LS.sweep_estimate(n_j, transport=args.transport)
    low = LS.sweep_estimate(n_j, opus_share=LS.OPUS_SHARE_ASSUMED[0], transport=args.transport)
    rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    ov = rubrics["overlap"]
    print(f"rows {len(plan['kept'])}; lexical-only pairs {len(items)}; judged {n_j}; not judged "
          f"{dict(sorted(Counter(it.not_judged for it in items if not it.judged).items()))}; "
          f"cap {cap}" + (f"; sample {sample}" if sample else ""))
    print(f"estimate ({args.transport}), Opus share ASSUMED {LS.OPUS_SHARE_ASSUMED[1]:.2f} "
          f"(at {LS.OPUS_SHARE_ASSUMED[0]:.2f}: ${low.usd:.3f}):\n{est.format()}")
    labels = _target_labels(plan)
    for it in _variants(items):
        print(f"\n--- rendered pair ({it.lexicon} {it.link}, {it.kind}): {it.key} -> {it.stem}, cut-off "
              f"{it.cut_off['c']} ({it.cut_off.get('band')}), rules {it.rules}; system prompt: {ov['name']} v{ov['version']} "
              f"sha256 {ov['sha256'][:12]} (pinned, unchanged); models {NR.FIRST_MODEL} then {NR.SECOND_MODEL}")
        print(render_pair(it, plan["descriptions"], labels))
    for spec in args.show or []:
        k, _, s = spec.partition(">")
        hit = [it for it in items if it.key == k and it.stem == s]
        print(f"\n--- --show {spec}:")
        print(render_pair(hit[0], plan["descriptions"], labels) if hit else "(no such lexical-only pair)")
    if args.dry_run:
        print("\nDRY-RUN: nothing sent, nothing written")
        return 0
    try:
        cap_usd = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                                   confirmed_by=args.confirmed_by)
    except CostRefused:
        return 2
    refusal, dirty_check = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if refusal:
        print(f"REFUSED: {refusal}", file=sys.stderr)
        return 2
    out_dir = sweep_dir(args)
    status, records = _prepare_out_dir(out_dir, args)
    if status:
        return status
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    earlier = json.loads((out_dir / "run.json").read_text(encoding="utf-8")) if (out_dir / "run.json").exists() else None
    if not (args.resume and (out_dir / "plan.json").exists()):
        _write_json(plan_snapshot(plan, items, batch_id=args.batch_id, cap=cap, sample=sample), out_dir / "plan.json",
                    title=f"lexical sweep plan {args.batch_id}")
    atomic_write_text("".join(json.dumps(it.as_dict(), ensure_ascii=False) + "\n" for it in items if it.judged),
                      out_dir / "pairs.jsonl")
    run_meta = {"batch_id": args.batch_id, "git_sha": git_sha(), "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:], "transport": args.transport,
                "estimate_usd": round(est.usd, 4), "estimate_lines": [str(x) for x in est.lines],
                "opus_share_assumed": list(LS.OPUS_SHARE_ASSUMED), "budget_usd": args.budget_usd, "cap_usd": cap_usd,
                "confirmed_by": args.confirmed_by, "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")}
                                                               for k, v in rubrics.items()},
                "models": {"overlap_first": NR.FIRST_MODEL, "overlap_second": NR.SECOND_MODEL},
                "lookup": {"path": str(args.lookup), "content_sha256": plan["lookup"].content_sha256,
                           "lexicons": plan["lookup"].lexicon_versions},
                "rows": args.rows, "from_batches": args.from_batches, "n_rows": len(plan["kept"]), "n_pairs": len(items), "n_judged": n_j, "cap": cap,
                "sample": sample, "moby_cosine_floor": LX.MOBY_COSINE_FLOOR, "label_form": DEFAULT_LABEL_FORM,
                "registry": None if args.no_registry_write else str(args.registry), "resumed": bool(args.resume),
                "started_at": utc_now()}
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    usage = GuardedUsage(budget_usd=cap_usd, usage_path=out_dir / "usage.json")
    if args.resume:
        NS._merge_earlier_usage(usage, out_dir, records)       # noqa: SLF001 - the shared resume rule
    status, runner, results, n_written = 0, None, [], None
    try:
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        runner = NR.NoveltyRunner(client=anthropic.AsyncAnthropic(max_retries=0), batch_id=args.batch_id,
                                  rubrics=rubrics, index=plan["index"], label_sets=NS.label_sets_for(args.data_dir),
                                  usage=usage, responses_path=out_dir / "responses.jsonl", k=plan["cfg"].k,
                                  config_version=plan["cfg"].config_version, concurrency=args.concurrency,
                                  resume_records=records, label_form=DEFAULT_LABEL_FORM)
        if args.transport == "batches":
            from assistant_axis.gapgen.batches import BatchTransport
            runner.cache_ttl = NR.BATCH_CACHE_TTL
            runner.transport = BatchTransport(runner, anthropic.Anthropic(), out_dir / "batches.json", budget_usd=cap_usd)
        results, stop = LS.run_sweep(runner, items, rows=plan["kept"], wave="lex")
        if stop is not None:
            raise stop
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}; every answer is recorded: --resume continues", file=sys.stderr)
        status = 2
    finally:
        usage.write_json(out_dir / "usage.json")
        if results:
            atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results),
                              out_dir / "results.jsonl")
        parse = runner.warn_parse_rates(logger) if runner is not None else {}
        complete = status == 0 and results and not any("stalled" in r for r in results)
        if complete or (status == 0 and not any(it.judged for it in items)):
            n_written = write_blocks(results, plan=plan, items=items, run_id=args.batch_id, runner=runner,
                                     out_dir=out_dir, registry_path=None if args.no_registry_write else args.registry)
        rep = LS.sweep_report(results, items=items, kept=plan["kept"], plans=plan["plans"], usage=usage.as_dict(),
                              parse_rates=parse, n_written=n_written, labels=_target_labels(plan))
        _write_json(rep, out_dir / "sweep_report.json", title=f"lexical sweep {args.batch_id}")
        atomic_write_text(LS.sweep_markdown(rep, results, kept=plan["kept"], batch_id=args.batch_id),
                          out_dir / "sweep_report.md")
        run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status,
                        n_results=len(results), n_stalled=sum(1 for r in results if "stalled" in r),
                        n_blocks_written=n_written, parse_rates=parse)
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        logging.getLogger().removeHandler(fh)
        fh.close()
        print(usage.log_line())
    print(rep["stop_rule"]["line"])
    if n_written is None and status == 0:
        print("no registry block written: some pairs stalled (a request failed outright); --resume finishes them",
              file=sys.stderr)
    return status


# --------------------------------------------------------------------------- report, marks, replay

def _report_inputs(args) -> tuple[dict, list, list, dict]:
    d = sweep_dir(args)
    pl = _read_json(d / "plan.json")
    items = [LS.PairItem.from_dict(x) for x in pl["items"]]
    results = _read_jsonl(d / "results.jsonl")
    rows = load_rows(args)
    kept = {k: rows[k] for k in pl["rows"] if k in rows}
    plans = {k: LS.RowPlan(key=k, pass_=v["pass"], links=[], antonyms=[LX.Antonym(**a) for a in v["antonyms"]],
                           family=v["family"], spec=NV.CutOff(**v["cut_off_rule"]), rules=LS._rules_by_name(v["rules"]),
                           candidate=None)
             for k, v in pl["rows"].items()}
    return pl, items, results, {"kept": kept, "plans": plans}


def cmd_report(args) -> int:
    d = sweep_dir(args)
    pl, items, results, ctx = _report_inputs(args)
    usage = json.loads((d / "usage.json").read_text(encoding="utf-8")) if (d / "usage.json").exists() else None
    run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
    marks = None
    if args.marks:
        mk = json.loads(Path(args.marks).read_text(encoding="utf-8"))
        key = json.loads((d / "marks" / "key.json").read_text(encoding="utf-8"))
        marks = LS.fold_marks(key, mk.get("rows") or mk.get("marks") or [])
    labels = {s: r["label"] for s, r in LX.load_lookup(args.lookup).rows.items()} if getattr(args, "lookup", None) else None
    rep = LS.sweep_report(results, items=items, kept=ctx["kept"], plans=ctx["plans"], usage=usage,
                          parse_rates=run.get("parse_rates"), marks=marks, n_written=run.get("n_blocks_written"),
                          labels=labels)
    print(rep["stop_rule"]["line"])
    if marks:
        print("marks: " + marks["line"])
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    _write_json(rep, d / "sweep_report.json", title=f"lexical sweep {args.batch_id}")
    atomic_write_text(LS.sweep_markdown(rep, results, kept=ctx["kept"], batch_id=args.batch_id), d / "sweep_report.md")
    print(f"wrote {d / 'sweep_report.md'}")
    return 0


def cmd_marks(args) -> int:
    d = sweep_dir(args)
    mdir = d / "marks"
    sheet = Path(args.sheet)
    if args.parse:
        key = json.loads((mdir / "key.json").read_text(encoding="utf-8"))
        text = Path(args.parse).read_text(encoding="utf-8")
        parsed = LS.parse_marks_markdown(text)
        folded = LS.fold_marks(key, parsed)
        print(folded["line"])
        if args.dry_run:
            print("DRY-RUN: nothing written")
            return 0
        out = {"_provenance": {"transcribed_at": utc_now(), "by": "lexical_recall.py marks --parse",
                               "marks_file": str(args.parse), "marks_file_sha256": hashlib.sha256(text.encode()).hexdigest(),
                               "key": str(mdir / "key.json"), "mark_codes": LS.MARK_CODES},
               "counts": {k: folded[k] for k in ("n_marked", "confirmed", "rejected", "unsure", "unmarked", "precision",
                                                 "build", "line")},
               "by_link": folded["by_link"], "rows": folded["rows"]}
        atomic_write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", mdir / "marks.json")
        print(f"wrote {mdir / 'marks.json'}")
        return 0
    results = _read_jsonl(d / "results.jsonl")
    if not results:
        print(f"{d / 'results.jsonl'}: no sweep results yet (run the sweep first)", file=sys.stderr)
        return 1
    corpus = NV.load_trait_corpus(args.data_dir)
    queue, _ = _load_queue(args.data_dir)
    entries, _ = LX.live_queue_entries(queue, corpus)
    desc = {s: t.description for s, t in corpus.items()} | {e["stem"]: e["text"] for e in entries if e["text"]}
    labels = {s: t.label for s, t in corpus.items()} | {e["stem"]: e["label"] for e in entries}
    rel = "../../" if sheet.resolve().parent == MARKS_SHEET.parent.resolve() else ""
    md, key = LS.marks_sheet(results, descriptions=desc, target_labels=labels, n=args.n, seed=args.seed,
                             batch_id=args.batch_id, rel=rel)
    key["marks_file"] = str(sheet)
    print(f"{key['n_marked']} of {key['n_covers']} covers on the sheet")
    if args.dry_run:
        print(md)
        print("DRY-RUN: nothing written")
        return 0
    atomic_write_text(md, sheet)
    mdir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(key, indent=1, ensure_ascii=False) + "\n", mdir / "key.json")
    print(f"wrote {sheet} and {mdir / 'key.json'}")
    return 0


def cmd_replay(args) -> int:
    d = sweep_dir(args)
    lines = _read_jsonl(d / "registry_writes.jsonl")
    reg = Registry(args.registry)
    cur = reg.fold()
    missing = [x["key"] for x in lines if x["key"] not in cur]
    todo = {x["key"]: {"lexical": x["lexical"]} for x in lines if x["key"] in cur and cur[x["key"]].get("lexical") != x["lexical"]}
    print(f"{len(lines)} blocks on record; {len(todo)} to write; {len(lines) - len(todo) - len(missing)} already in "
          f"place; {len(missing)} keys not in this registry" + (f" ({', '.join(missing[:5])})" if missing else ""))
    if args.dry_run or not todo:
        if args.dry_run:
            print("DRY-RUN: nothing written")
        return 0
    reg.update_many(todo, merge_blocks=False)
    print(f"wrote {len(todo)} lexical blocks to {args.registry}")
    return 0


# --------------------------------------------------------------------------- reach (task 8, dry)

def reach_seed(lookup: LX.Lookup, *, hidden, matches, kept_rows, cos=None, moby_floor: float = LX.MOBY_COSINE_FLOOR
               ) -> dict:
    """One seed of a recovery run: the hidden traits no kept candidate recovered (``matches``: the harness's
    ``matches.jsonl``), and those a kept candidate's lexical link reaches (:meth:`lexical.Lookup.neighbours`, a
    renamed hidden stem folded through the table's ``renamed_from``), by lexicon; per link whether the harness already
    read the pair (``read_by_harness``: its overlap call then said no) and whether the sweep would judge it (a Moby-only
    link under ``moby_floor``, or with no cosine, is not judged; ``cos(key, stem)``)."""
    renamed = {old: r["stem"] for r in lookup.rows.values() for old in r.get("renamed_from") or []}
    cur = {h: renamed.get(h, h) for h in hidden}
    recovered = {m["stem"] for m in matches if m.get("recovers") and m.get("decision") in LS.KEPT_DECISIONS}
    read = {(m.get("key"), m.get("stem")) for m in matches}
    unrec = [h for h in hidden if h not in recovered]
    want = {cur[h]: h for h in unrec}
    by: dict = {}
    for r in sorted(kept_rows, key=lambda r: r["key"]):
        for ln in lookup.neighbours(r["label"], r["stem"]):
            h = want.get(ln.stem)
            if h is None:
                continue
            c = cos(r["key"], ln.stem) if cos is not None else None
            judged = not ln.name_only and not (ln.moby_only and (c is None or c < moby_floor))
            by.setdefault(h, []).append({"key": r["key"], "label": r["label"], "lexicon": ln.lexicon, "link": ln.link,
                                         "moby_only": ln.moby_only, "cosine": c, "would_be_judged": judged,
                                         "read_by_harness": (r["key"], h) in read or (r["key"], ln.stem) in read})
    traits = [{"stem": h, "by": by[h]} for h in unrec if h in by]
    any_lex = lambda h, lex: any(x["lexicon"] == lex for x in by[h])  # noqa: E731
    return {"n_hidden": len(hidden), "n_recovered_by_kept": len(recovered & set(hidden)), "n_unrecovered": len(unrec),
            "n_kept": len(kept_rows), "not_in_lookup": sorted(h for h in unrec if cur[h] not in lookup.rows),
            "reached": {"n": len(traits),
                        "by_lexicon": {lex: sum(1 for h in by if any_lex(h, lex)) for lex in LX.LEXICONS
                                       if any(any_lex(h, lex) for h in by)},
                        "moby_only": sum(1 for h in by if not any_lex(h, "oewn")),
                        "would_be_judged": sum(1 for h in by if any(x["would_be_judged"] for x in by[h])),
                        "never_read": sum(1 for h in by if any(not x["read_by_harness"] for x in by[h])),
                        "read_below_cut": sum(1 for h in by if all(x["read_by_harness"] for x in by[h])),
                        "judged_and_never_read": sum(1 for h in by if any(x["would_be_judged"]
                                                                          and not x["read_by_harness"] for x in by[h])),
                        "traits": traits},
            "unreached": [h for h in unrec if h not in by]}


def cmd_reach(args) -> int:
    """Plan 11 task 8, dry ($0): over a recovery run's hidden set, how many hidden traits its kept candidates did not
    recover have a lexical link from one of them (the flags a lexical sweep of that run could raise; Roger,
    2026-10-14: a lexical link only flags, never recovers by cutting)."""
    from assistant_axis.gapgen.recovery import load_hidden
    rdir = paths.recovery_dir(args.recovery_batch, candidates_dir=args.out_root)
    run = json.loads((rdir / "run.json").read_text(encoding="utf-8"))
    lookup = LX.load_lookup(args.lookup)
    index, cfg, cache = None, None, None
    if not args.no_cosines:
        from assistant_axis.gapgen import embed as EM
        from assistant_axis.gapgen.metric_config import MetricConfig
        from data_analysis.gap_generation import novelty_score as NS
        cfg = MetricConfig.load(args.metric_config)
        cache = EM.EmbeddingCache(args.cache_dir)
        index, _ = NS.load_index(cfg, data_dir=args.data_dir, cache=cache, allow_embed=False, queue_search=True)
    seeds = []
    for seed in run.get("seeds") or []:
        m3_run = (run.get("m3_runs") or {}).get(str(seed))
        sd = rdir / f"seed{seed}"
        hidden = load_hidden(sd / "hidden.json")["stems"]
        results = _read_jsonl(paths.novelty_dir(m3_run, candidates_dir=args.out_root) / "results.jsonl")
        kept = [r for r in results if (r.get("novelty") or {}).get("decision") in LS.KEPT_DECISIONS]
        cos = None
        if index is not None:
            cos = LS.cosine_fn(index, candidate_vectors({r["key"]: r for r in kept}, cfg, cache))
        s = reach_seed(lookup, hidden=hidden, matches=_read_jsonl(sd / "matches.jsonl"), kept_rows=kept, cos=cos)
        seeds.append({"seed": seed, "m3_run": m3_run} | s)
        rc = s["reached"]
        print(f"seed {seed} ({m3_run}): {s['n_hidden']} hidden, {s['n_recovered_by_kept']} recovered by the "
              f"{s['n_kept']} kept candidates; unrecovered hidden traits a lexical link reaches: {rc['n']} of "
              f"{s['n_unrecovered']} (by lexicon {rc['by_lexicon']}; Moby only {rc['moby_only']}; the sweep would "
              f"judge {rc['would_be_judged']}; with a link the harness never read {rc['never_read']}, every link read "
              f"below the cut {rc['read_below_cut']}; a link the sweep would judge and the harness never read: "
              f"{rc['judged_and_never_read']})")
        for t in rc["traits"]:
            print(f"  {t['stem']}: " + "; ".join(f"{x['label']} ({x['lexicon']} {x['link']}, cosine {x['cosine']}"
                                                 f"{', read' if x['read_by_harness'] else ''})" for x in t["by"]))
    doc = {"recovery_batch": args.recovery_batch, "lookup_sha256": lookup.content_sha256,
           "lexicons": lookup.lexicon_versions, "moby_cosine_floor": LX.MOBY_COSINE_FLOOR,
           "cosines": index is not None, "seeds": seeds, "at": utc_now()}
    if args.dry_run:
        print("DRY-RUN: nothing written")
        return 0
    _write_json(doc, rdir / "lexical_reach.json", title=f"lexical reach of {args.recovery_batch} (plan 11 task 8, dry)")
    print(f"wrote {rdir / 'lexical_reach.json'}")
    return 0


# --------------------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(sp, *, lexicons=True):
        sp.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
        sp.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
        sp.add_argument("--out-root", type=Path, default=None, help="candidates dir holding lexical/ (default data/candidates)")
        sp.add_argument("--lookup", type=Path, default=LX.LOOKUP_PATH)
        if lexicons:
            sp.add_argument("--lexicons", nargs="+", choices=LX.LEXICONS, default=list(LX.LEXICONS),
                            help="the lexicons (default both; Moby must be downloaded: setup_external.py --moby)")
            sp.add_argument("--moby-path", type=Path, default=None, help=argparse.SUPPRESS)
        sp.add_argument("--dry-run", action="store_true", help="print the counts (and estimate); write nothing")

    def plan_args(sp):
        sp.add_argument("--rows", choices=("all",) + LS.PASSES, default="all", help="which passes' kept rows (default all)")
        sp.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
        sp.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
        sp.add_argument("--lexicons", nargs="+", choices=LX.LEXICONS, default=None,
                        help="only these lexicons' links (default: every lexicon the lookup table was built with)")
        sp.add_argument("--budget-usd", type=float, default=LS.DEFAULT_BUDGET_USD,
                        help=f"the sweep's hard cap (default ${LS.DEFAULT_BUDGET_USD:.0f}); Moby's pairs are cut by cosine to fit")
        sp.add_argument("--from-batches", nargs="+", metavar="M3_BATCH", default=None,
                        help="only the kept rows these M3 batches decided (a new wave: the forward path; default every "
                             "kept row)")

    sp = sub.add_parser("build", help="the lookup table ($0)")
    common(sp)
    sp.set_defaults(func=cmd_build)
    sp = sub.add_parser("labelled", help="the labelled-pairs measurement ($0)")
    common(sp)
    sp.add_argument("--labelled", type=Path, default=LABELLED_PATH)
    sp.set_defaults(func=cmd_labelled)
    sp = sub.add_parser("dry", help="the retroactive lookup over every kept row ($0)")
    common(sp, lexicons=False)
    plan_args(sp)
    sp.add_argument("--batch-id", default=None, help="also write the sweep's plan.json under lexical/sweep/<batch_id>/")
    sp.set_defaults(func=cmd_dry)
    sp = sub.add_parser("sweep", help="the overlap call on every judgeable lexical-only pair (paid)")
    common(sp, lexicons=False)
    plan_args(sp)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--sample", type=int, default=None, help="a seeded sample of the judgeable pairs (default: all)")
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--resume", action="store_true")
    sp.add_argument("--overwrite", action="store_true")
    sp.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    sp.add_argument("--transport", choices=("live", "batches"), default="live",
                    help="live (default: under the $20 line the rule is real time) or the Message Batches API")
    sp.add_argument("--confirm-expensive", action="store_true")
    sp.add_argument("--confirmed-by", default=None, help="who gave the explicit go for a budget over $20")
    sp.add_argument("--allow-dirty", action="store_true")
    sp.add_argument("--rubrics-dir", type=Path, default=None)
    sp.add_argument("--no-registry-write", action="store_true",
                    help="leave the registry alone (registry_writes.jsonl is still written; replay applies it)")
    sp.add_argument("--show", action="append", metavar="KEY>STEM", help="also render this pair (dry run)")
    sp.set_defaults(func=cmd_sweep)
    sp = sub.add_parser("report", help="the sweep's readout again, with Roger's marks ($0)")
    common(sp, lexicons=False)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--marks", type=Path, default=None, help="marks.json (marks --parse) to fold in")
    sp.set_defaults(func=cmd_report)
    sp = sub.add_parser("marks", help="the blind-marks sheet for Roger, or --parse his marked sheet ($0)")
    common(sp, lexicons=False)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--n", type=int, default=LS.MARKS_MAX)
    sp.add_argument("--seed", type=int, default=20261014)
    sp.add_argument("--sheet", type=Path, default=MARKS_SHEET)
    sp.add_argument("--parse", type=Path, default=None, help="the marked sheet to read back into marks/marks.json")
    sp.set_defaults(func=cmd_marks)
    sp = sub.add_parser("reach", help="task 8, dry: the unrecovered hidden traits of a recovery run a lexical link "
                                      "reaches ($0)")
    common(sp, lexicons=False)
    sp.add_argument("--recovery-batch", required=True, help="data/candidates/recovery/<B>/ (its run.json, seeds' "
                                                            "hidden.json and matches.jsonl, and the M3 runs' results)")
    sp.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    sp.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    sp.add_argument("--no-cosines", action="store_true", help="skip the cosines (no index; Moby's floor not applied)")
    sp.set_defaults(func=cmd_reach)
    sp = sub.add_parser("replay", help="apply registry_writes.jsonl to a registry ($0)")
    common(sp, lexicons=False)
    sp.add_argument("--batch-id", required=True)
    sp.set_defaults(func=cmd_replay)
    return ap


def main(argv=None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
