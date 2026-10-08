#!/usr/bin/env python3
"""M3, the novelty check: does the corpus already have each candidate trait?

    uv run python data_analysis/gap_generation/novelty_score.py <command> ...

The brief is ``reports/trait_gap_generation/coding_plan_m3.md``; the logic is
:mod:`assistant_axis.gapgen.novelty`, the waves :mod:`assistant_axis.gapgen.novelty_runner`.

Commands:

* ``score --batch-id B (--run GEN/RUN [--run ...] | --keys K ... | --unscored)``: M3 on the registry rows
  whose filter verdict is ``trait`` (with a gloss): the exact-label check, retrieval in the covered setting of
  ``metric_config.json`` (OpenAI ``text-embedding-3-large``, direct key; the 8 canary texts re-embedded first),
  arrangement expansion, the relation call (Haiku 5.5 from 2026-10-08, Haiku 4.5 before; ``--relation-model``;
  ``rubrics/relation.md``; ``unsure`` to Sonnet 5.5), the
  overlap call (rubric A as pinned, one pair per call, Sonnet 5.5 then Opus 5.5 by the rule, early exit), the
  decision.  Writes the ``novelty`` block of every decided row through the Registry API (once per run and key;
  a resume skips the rows already decided in the run) and ``data/candidates/novelty/<B>/``: ``responses.jsonl``,
  ``results.jsonl`` (every decided candidate's block), ``readings.jsonl`` (one line per pair judged, beside its
  cosine), ``summary.json``, ``decisions.md`` (the table for Roger to sample from), ``usage.json``, ``run.json``,
  ``run.log`` and, with the batches transport, ``batches.json``.  Rows held on a list (nationalities) are left
  out unless ``--include-held``; rows already decided by another run unless ``--rescore``.
  ``--embed-only`` embeds the candidates (charged to the run) and stops before any LLM call, so that
  ``render --key`` or the dry run can show a real candidate's prompt first; ``--resume`` then goes on.
  ``--hide HIDDEN_JSON`` (the recovery harness, ``recovery_test.py``; ``assistant_axis/gapgen/recovery.py``): score
  against the corpus without the traits the file's ``hidden`` list names: the index is built without them,
  expansion and the "opposite" rule never reach them, and the exact-label check no longer knows them (nor the
  seed queue's entries for them, nor their ``renamed_from``).  Such a run never writes the registry (its blocks
  go to its own run directory only), takes the selected rows whatever other runs decided, and records the
  hidden file's path and sha256 in ``run.json``, ``summary.json`` and every block (``hide``); a resume refuses
  another hidden file.  Not with ``--redecide`` or ``--relation-only``.
* ``score --redecide --from-batch B --batch-id B2``: re-run the decision rules on run B's records: B's
  candidates, its corpus (the trait files and seed queue as committed at B's ``git_sha``, unless
  ``--corpus-at current``), its relation-call order, and every answer B has on record replayed instead of sent;
  a call that a rule now needs and B never made (the ``renamed_from`` candidates of decision 15, say) is sent
  live and recorded in B2's ``responses.jsonl``.  Writes B2's run directory as ``score`` does (not the registry),
  plus ``decision_changes.md`` / ``.json``: every row whose decision or covering trait differs from B's, with
  the rule that changed it (the rules are added one decision at a time, each step replayed on the records), and
  the check that rule set 1 on the same records reproduces B exactly.  ``--dry-run`` replays offline and prints
  the calls not on record and their estimate.  The relation call is B's model (its ``run.json`` ``models``), so
  B's answers replay whatever today's default; ``--relation-model`` is refused here.  ``--write-registry``: once
  the run has decided every candidate, its blocks are written to the registry as ``promote-redecide`` does.
* ``promote-redecide --batch-id B2 [--dry-run]`` (coding_plan_haiku55.md, "The switch", item 5): write a finished
  re-decided run's ``novelty`` blocks (its ``results.jsonl``; each names B2 as ``run_id`` and the source run as
  ``redecided_from``) to the registry rows, replacing the blocks of the runs it re-decided (``run.json``
  ``replay_from``); idempotent per (run, key): a row already holding B2's block is left alone, and a row whose
  block came from any other run (decided since) is left alone and listed.  Appends what it did to
  ``B2/registry_writes.jsonl``.  No API call.  The tracked snapshot changes only with ``gap_registry.py compact``.
* ``score --relation-only --from-batch B --batch-id R [--relation-model M] [--keys K ...]`` (coding_plan_haiku55.md):
  stage 3 alone, so that the relation call can be compared on another model without re-running M3: B's
  candidates, corpus (``--corpus-at``), list order and cached query embeddings; the relation call on
  ``--relation-model`` (default Haiku 5.5 from 2026-10-08) and the unsure re-ask on Sonnet 5.5; the shortlists built under
  ``--rules``; then stop (no overlap call, no decision, no registry write).  Before sending, every request is
  checked against B's relation call for the same candidate (the same user turn, system prompt, ``max_tokens``
  and cache setting; only the model differs); a difference refuses the run.  Writes ``R``'s directory:
  ``responses.jsonl``, ``relation.jsonl`` (one row per candidate that reached the call: every answer, the final
  relations, the counts, the shortlist and its length, each call's usage and answer length),
  ``relation_summary.json``, ``usage.json``, ``run.json``, ``run.log``.
  ``--relation-model`` also sets the relation call's model of an ordinary ``score`` run (not of ``--redecide``).
* ``full-scan --batch-id S --from-batch B [--sample 100 --sample-seed 0 | --keys K ...]``: the pilot's check on
  the shortlist: the overlap call on every listed trait of a seeded sample of B's candidates (those that reached
  the relation call), or of the named registry keys, no relation call, no shortlist, no early exit, Opus on the
  pairs the rule sends it; the walk is replayed on the readings afterwards under the run's rules (listed traits
  below the floor are read but left out of the replayed walk).  The corpus is B's (``--corpus-at``).  Writes only
  its own run directory, never the registry.
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

Rules: ``--rules 2`` (the default from 2026-10-07: decisions 12-15 of ``coding_plan_platform.md``'s M3 section
and the cosine floor) or ``--rules 1`` (the pilot's); ``--cosine-floor F`` (default: the rule set's, 0.25 for
rule set 2, none for 1; ``none`` turns it off).  Recorded in ``run.json`` and in every row's block.

Cost: ``score`` and ``full-scan`` print the estimate by stage (``n_calls x (in, out) tokens at model rates``),
``--budget-usd`` is the hard cap (default $5; an estimate over it is refused), and a budget or estimate over $20
needs ``--confirm-expensive`` and ``--confirmed-by``.  ``--dry-run`` prints the plan, the estimate and the first
rendered prompt and writes and calls nothing.  A paid run is refused while the platform's code or prompt paths
have uncommitted changes, unless ``--allow-dirty`` (recorded).  ``--transport auto`` sends fewer than 300
candidates live and more through the Message Batches API (half price, the 1-hour cache on the rubric).
"""
from __future__ import annotations

import argparse
import atexit
import io
import json
import logging
import os
import random
import shutil
import subprocess
import sys
import tarfile
import tempfile
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
from assistant_axis.judge_pricing import BATCH_SUFFIX, BudgetExceededError, MultiModelUsage  # noqa: E402

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


def select_candidates(rows: dict, args, *, batch_id: str, ignore_decided: bool = False) -> tuple[list[NR.M3Candidate], dict]:
    """The candidates of ``score``, and why every other selected row was left out.  ``ignore_decided`` (a run
    with ``--hide``, which writes no block to the registry): rows are taken whatever run decided them."""
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
        if not ignore_decided and nv.get("run_id") == batch_id and nv.get("decision"):
            skipped["decided_in_this_run"] += 1
            continue
        if not ignore_decided and nv.get("decision") and nv.get("run_id") and not args.rescore:
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


def load_index(cfg, *, data_dir: Path, cache, usage=None, allow_embed: bool = False,
               hide=()) -> tuple[NV.CorpusIndex, dict]:
    """The corpus in the covered setting from the embedding cache (``label: description`` in the covered
    representation); a text missing from the cache is embedded only with ``allow_embed`` (charged).  ``hide``:
    stems left out of the corpus before the space is fitted (``recovery.reduced_traits``; ``ValueError`` for a
    stem the corpus does not have)."""
    import numpy as np
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.recovery import reduced_traits
    from assistant_axis.gapgen.representation import represent
    traits = NV.load_trait_corpus(data_dir)
    if hide:
        traits = reduced_traits(traits, hide)
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


def label_sets_for(data_dir: Path, hide=()) -> NV.LabelSets:
    """Stage 0's names, from the trait files and the seed queue (no embedding needed); ``hide``: without the
    hidden traits (``recovery.reduced_label_sets``)."""
    import data_analysis.seed_entities as se
    queue = se.load_queue(Path(data_dir) / "seed_queue.json")
    if hide:
        from assistant_axis.gapgen.recovery import reduced_label_sets, reduced_traits
        return reduced_label_sets(reduced_traits(NV.load_trait_corpus(data_dir), hide), queue, hide)
    return NV.label_sets(NV.load_trait_corpus(data_dir), queue)


# --------------------------------------------------------------------------- rules, sources, corpus snapshots

def parse_floor(value: str):
    """``--cosine-floor``: a number, or ``none`` for no floor."""
    if value.strip().lower() in ("none", "off"):
        return "none"
    try:
        return float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"--cosine-floor takes a number or 'none', not {value!r}") from exc


def resolve_rules(args) -> NV.Rules:
    """The rule set of ``--rules`` with ``--cosine-floor`` applied (default: the set's own floor)."""
    rules = NV.RULES[int(getattr(args, "rules", NV.DEFAULT_RULES.version))]
    floor = getattr(args, "cosine_floor", None)
    if floor == "none":
        return rules.with_floor(None)
    if floor is not None:
        return rules.with_floor(floor)
    return rules


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def load_source(batch_id: str, out_root: Optional[Path], *, with_records: bool = False) -> dict:
    """A finished run's directory: ``{"batch_id", "dir", "run", "results", "records", "replay_from"}``.
    ``records`` (with ``with_records``) are its responses and those of every run it replayed in turn (a
    re-decided run keeps only its own new calls, and names its sources in ``run.json``'s ``replay_from``)."""
    d = paths.novelty_dir(batch_id, candidates_dir=out_root)
    if not (d / "results.jsonl").exists():
        raise SystemExit(f"{d / 'results.jsonl'} not found: run score --batch-id {batch_id} first")
    run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
    replay_from = list(run.get("replay_from") or [])
    records: list[dict] = []
    if with_records:
        for b in replay_from:
            records += _read_jsonl(paths.novelty_dir(b, candidates_dir=out_root) / "responses.jsonl")
        records += _read_jsonl(d / "responses.jsonl")
    return {"batch_id": batch_id, "dir": d, "run": run, "results": _read_jsonl(d / "results.jsonl"),
            "records": records, "replay_from": replay_from + [batch_id]}


#: The corpus files a run reads: the trait files (labels, descriptions, arrangements, renames) and the queue.
CORPUS_PATHS = ("data/traits/instructions", "data/seed_queue.json")


def corpus_at_commit(sha: str, dest: Path, repo: Path = _REPO_ROOT) -> Path:
    """The trait files and the seed queue as committed at ``sha``, written under ``dest`` (``git archive``,
    nothing else of the tree); returns the data dir to pass where ``--data-dir`` goes."""
    sha = sha.split("+", 1)[0]
    out = subprocess.run(["git", "archive", "--format=tar", sha, "--", *CORPUS_PATHS], cwd=repo,
                         capture_output=True, check=True)
    with tarfile.open(fileobj=io.BytesIO(out.stdout)) as tf:
        tf.extractall(dest, filter="data")
    return Path(dest) / "data"


def resolve_data_dir(args, source: Optional[dict]) -> tuple[Path, dict]:
    """``(data dir, record)``: ``--corpus-at source`` (the default where there is a source run: re-deciding,
    the full scan) reads the corpus as committed at the source's ``git_sha``, so that retrieval, the relation
    call's list and the label check are the source's; ``current`` reads ``--data-dir``."""
    at = getattr(args, "corpus_at", None) or ("source" if source else "current")
    if at == "current" or source is None:
        return Path(args.data_dir), {"corpus_at": "current", "data_dir": str(args.data_dir)}
    sha = (source.get("run") or {}).get("git_sha")
    if not sha:
        raise SystemExit(f"--corpus-at source: {source['batch_id']}'s run.json records no git_sha; "
                         "pass --corpus-at current")
    dest = Path(tempfile.mkdtemp(prefix=f"m3_corpus_{sha.split('+', 1)[0]}_"))
    atexit.register(shutil.rmtree, dest, True)          # a scratch copy, not a deliverable (run.json records the sha)
    try:
        dd = corpus_at_commit(sha, dest)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f"--corpus-at source: git archive {sha} failed: {exc.stderr.decode(errors='replace')[:300]}")
    n = len(list((dd / "traits" / "instructions").glob("*.json")))
    return dd, {"corpus_at": "source", "source_batch": source["batch_id"], "git_sha": sha,
                "source_was_dirty": sha.endswith("+dirty"), "n_trait_files": n, "data_dir": str(dd)}


def select_redecide(rows: dict, args, source: dict) -> tuple[list[NR.M3Candidate], dict]:
    """The candidates of ``score --redecide``: every row the source run decided (or those of ``--keys``),
    rebuilt from the registry as the source built them."""
    keys = [r["key"] for r in source["results"]]
    if args.keys:
        unknown = sorted(set(args.keys) - set(keys))
        if unknown:
            raise SystemExit(f"not decided by {source['batch_id']}: {', '.join(unknown[:10])}")
        keys = [k for k in keys if k in set(args.keys)]
    out, skipped = [], Counter()
    for k in keys:
        cand, why = NR.candidate_from_row(rows[k]) if k in rows else (None, "not_in_registry")
        if cand is None:
            skipped[why] += 1
        else:
            out.append(cand)
    return out, dict(skipped)


def check_source_settings(source: dict, *, cfg, query_form: str) -> list[str]:
    """Settings of the source run that differ from this one's (any of them makes the replayed requests
    differ, so a re-decided run refuses)."""
    s = (source.get("run") or {}).get("settings") or {}
    mine = {"config_version": cfg.config_version, "k": cfg.k, "representation": cfg.representation,
            "variant": cfg.covered["space"]["variant"], "query_form": query_form,
            "embedding_model": cfg.live_model["model_id"]}
    return [f"{k}: source {s[k]!r}, here {v!r}" for k, v in mine.items() if k in s and s[k] != v]


# --------------------------------------------------------------------------- writing

def source_relation_model(source: dict) -> str:
    """The relation call's model of a source run: its ``run.json`` ``models.relation``, else the model most of
    its relation records name, else today's default.  A re-decided run replays the source's answers, whose
    records are keyed by model, so it must ask for the same model (Haiku 4.5 for every run before 2026-10-08)."""
    m = (((source.get("run") or {}).get("models") or {}).get("relation"))
    if m:
        return str(m)
    seen = Counter(r.get("model") for r in source.get("records") or [] if r.get("step") == "relation" and r.get("model"))
    return seen.most_common(1)[0][0] if seen else NR.RELATION_MODEL


def promote_redecided(reg: Registry, results: list[dict], *, run_id: str, replaced_runs, dry_run: bool = False) -> dict:
    """Write a re-decided run's ``novelty`` blocks (``results``, its ``results.jsonl`` rows) to the registry,
    idempotent per (run, key) (coding_plan_haiku55.md, "The switch", item 5).  A row is written when its
    current block is missing or came from one of ``replaced_runs`` (the runs this one re-decided); it is left
    alone when it already holds this run's block (``already``), when its block came from another run, decided
    since (``other_run``, listed with that run), when the key is not in the registry, or when the result has no
    decision.  Returns the counts and keys; writes nothing with ``dry_run``."""
    cur = reg.fold()
    replaced = set(replaced_runs) - {run_id}
    updates, out = {}, {"written": [], "already": [], "other_run": {}, "not_in_registry": [], "undecided": [],
                        "block_of_another_run": []}
    for r in results:
        key, nv = r.get("key"), r.get("novelty") or {}
        if not nv.get("decision"):
            out["undecided"].append(key)
            continue
        if nv.get("run_id") != run_id:   # a results row carried over from elsewhere: not this run's to write
            out["block_of_another_run"].append(key)
            continue
        if key not in cur:
            out["not_in_registry"].append(key)
            continue
        old = cur[key].get("novelty") or {}
        if old.get("run_id") == run_id and old.get("decision"):
            out["already"].append(key)
        elif not old or old.get("run_id") in replaced:
            updates[key] = {"novelty": nv}
            out["written"].append(key)
        else:
            out["other_run"].setdefault(str(old.get("run_id")), []).append(key)
    if updates and not dry_run:
        reg.update_many(updates, merge_blocks=False)
    return {"run_id": run_id, "replaced_runs": sorted(replaced), "dry_run": dry_run,
            "counts": {k: (sum(len(v) for v in out[k].values()) if k == "other_run" else len(out[k])) for k in out},
            **{k: (dict(sorted(v.items())) if k == "other_run" else sorted(v)) for k, v in out.items()}}


def write_promotion(out_dir: Path, rec: dict, registry_path: Path) -> None:
    """Append one promotion's record to ``<run dir>/registry_writes.jsonl``."""
    line = {"at": utc_now(), "registry": str(registry_path), "git_sha": git_sha(),
            **{k: v for k, v in rec.items() if k != "already"}, "n_already": len(rec["already"])}
    with open(out_dir / "registry_writes.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, ensure_ascii=False) + "\n")


def run_promotion(batch_id: str, *, out_root: Optional[Path], registry_path: Path, dry_run: bool = False) -> int:
    """``promote-redecide`` (and ``score --redecide --write-registry`` at its end): checks that ``batch_id`` is a
    finished re-decided run, writes its blocks, records and prints what it did."""
    d = paths.novelty_dir(batch_id, candidates_dir=out_root)
    run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
    if not run.get("redecide") or not run.get("replay_from"):
        print(f"REFUSED: {batch_id} is not a re-decided run (its run.json has no redecide / replay_from)", file=sys.stderr)
        return 2
    if run.get("status") not in (0, None) or run.get("n_stalled"):
        print(f"REFUSED: {batch_id} did not finish (status {run.get('status')}, {run.get('n_stalled')} stalled); "
              f"resume it first", file=sys.stderr)
        return 2
    results = _read_jsonl(d / "results.jsonl")
    if not results:
        print(f"REFUSED: {d / 'results.jsonl'} is empty or missing", file=sys.stderr)
        return 2
    rec = promote_redecided(Registry(registry_path), results, run_id=batch_id,
                            replaced_runs=[b for b in run["replay_from"] if b != batch_id], dry_run=dry_run)
    if not dry_run:
        write_promotion(d, rec, registry_path)
    print(f"{'DRY-RUN: would write' if dry_run else 'registry:'} {json.dumps(rec['counts'])} "
          f"(replacing the blocks of {rec['replaced_runs']}; source named in each block as redecided_from)")
    if rec["other_run"]:
        print(f"left alone, decided by another run since: {json.dumps(rec['other_run'])}")
    return 0


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


def _rules_line(results: list[dict]) -> str:
    sets = {}
    for r in results:
        ru = r["novelty"].get("rules") or {}
        sets[(ru.get("name") or NV.RULES[1].name, ru.get("version") or 1, ru.get("cosine_floor"))] = 1
    if not sets:
        return ""
    parts = []
    for name, version, floor in sorted(sets, key=str):
        what = ("decisions 1-11, the pilot's" if version == 1 else "decisions 12-15 of the M3 decisions added")
        parts.append(f"rule set {version} (`{name}`: {what}; cosine floor {floor if floor is not None else 'none'})")
    return "Rules: " + "; ".join(parts) + ".  "


def _covered_flagged(nv: dict) -> Optional[dict]:
    """The decision-12 detail of a row covered by the Opus check (Sonnet one below the cut-off, Opus at or
    above it, on the covering trait), else ``None``."""
    if nv.get("decision") != "covered":
        return None
    return next((d for d in nv.get("review_details") or [] if d.get("kind") == "sonnet_below_opus_at"
                 and d.get("stem") == nv.get("covered_by")), None)


def _note_text(n: dict, labels: dict) -> str:
    return " / ".join(_trait_link(s, labels.get(s)) for s in n["pair"]) + \
        (f" ({n['kind']})" if n.get("kind") and n["kind"] != "pair" else "")


def decisions_markdown(results: list[dict], *, batch_id: str, labels: dict, mode: str = "shortlist") -> str:
    """``decisions.md``: every candidate (label, decision, covered_by, cut-off, the readings that decided it,
    review flags, pair completions), then the review sections (the covered-and-flagged rows of decision 12 with
    both readings and reasons; the both-ends-similar rows of decision 13 with the ends' cosines and any readings
    on record; the ``grey`` rows), then the pair completions.  Trait names link to their files (paths relative
    to ``data/candidates/novelty/<batch>/``)."""
    order = {"covered": 0, "grey": 1, "new": 2}
    rows = sorted(results, key=lambda r: (order.get(r["novelty"]["decision"], 9), str(r["label"]).lower()))
    n = Counter(r["novelty"]["decision"] for r in results)
    lines = [f"# M3 decisions: `{batch_id}`" + (" (full scan)" if mode == "full_scan" else ""), "",
             f"{len(results)} candidates: " + ", ".join(f"{n[d]} {d}" for d in ("covered", "grey", "new") if n[d]) + ".  "
             "Cut-off: covered at 3 or more far from alignment (alignment score 0 or 1), at 4 near it (2 or 3).  "
             "The deciding readings are rubric A's 0-4 scale (Sonnet 5.5 first, Opus 5.5 where the rule sends it).  "
             + _rules_line(results) +
             "Built by `novelty_score.py`; every reading is in `readings.jsonl` beside this file.", "",
             "| candidate | decision | covered by | cut-off | deciding reading | review | pair completion for | "
             "pairs judged | gloss |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        nv = r["novelty"]
        cov = nv.get("covered_by")
        how = "exact label" if nv["reason"] == "exact_label" else _reading_text(nv.get("deciding_reading"))
        if nv["reason"] == "exact_label" and nv.get("exact_label"):
            how += f" ({nv['exact_label'].get('match')}" + (", separator-blind" if nv["exact_label"].get("blind") else "") + ")"
        if nv.get("renamed_from"):
            how += f" (renamed from {nv['renamed_from'].get('old_stem')}, judged)"
        pcf = ", ".join(_trait_link(s, labels.get(s)) for s in nv.get("pair_completion_for") or [])
        review = ", ".join(nv.get("review") or [])
        if nv.get("pair_notes"):
            review += ": " + "; ".join(_note_text(x, labels) for x in nv["pair_notes"])
        lines.append(f"| {_md(r['label'])} | {nv['decision']} | {_trait_link(cov, labels.get(cov)) if cov in labels else _md(cov)} | "
                     f"{nv['cut_off']} | {_md(how)} | {review} | {pcf} | "
                     f"{nv.get('n_pairs_judged', 0)} | {_md(r.get('gloss'))} |")
    flagged = [(r, _covered_flagged(r["novelty"])) for r in rows]
    flagged = [(r, d) for r, d in flagged if d is not None]
    lines += ["", f"## Covered, flagged ({len(flagged)} rows)", "",
              "Decision 12: Sonnet read the pair one below the cut-off and Opus at or above it, so the candidate is "
              "covered by that trait and flagged for review (Roger sided with Opus on 45 of 58 such pairs in the pilot).", ""]
    for r, d in flagged:
        nv = r["novelty"]
        lines += [f"- **{_md(r['label'])}** (`{r['key']}`, cut-off {nv['cut_off']}) by "
                  f"{_trait_link(d['stem'], labels.get(d['stem']))}: Sonnet {d['sonnet']['value']} "
                  f"(\"{_md(d['sonnet'].get('reason'))}\"), Opus {d['opus']['value']} (\"{_md(d['opus'].get('reason'))}\")",
                  f"  Gloss: {_md(r.get('gloss'))}"]
    noted = [r for r in rows if r["novelty"].get("pair_notes")]
    lines += ["", f"## Both ends similar (orthogonal to the pair?) ({len(noted)} rows)", "",
              "Decision 13 (Roger's rule): the relation call marked both members of a recorded pair (every corner of a "
              "triangle or simplex) similar, so the candidate is probably orthogonal to the pair's axis: neither member "
              "was judged or may cover it.  Cosines to the candidate; overlap readings where any are on record.", ""]
    for r in noted:
        nv = r["novelty"]
        lines.append(f"- **{_md(r['label'])}** (`{r['key']}`, {nv['decision']}"
                     + (f" by {_trait_link(nv['covered_by'], labels.get(nv['covered_by']))}" if nv.get("covered_by") else "")
                     + f", cut-off {nv['cut_off']}).  Gloss: {_md(r.get('gloss'))}")
        for note in nv["pair_notes"]:
            ends = []
            for s in note["pair"]:
                c = (note.get("cosines") or {}).get(s)
                rd = (note.get("readings_on_record") or {}).get(s) or {}
                txt = f"{_trait_link(s, labels.get(s))} (cosine {c:.3f}" if c is not None else f"{_trait_link(s, labels.get(s))} ("
                if rd:
                    txt += "; " + ", ".join(f"{m.capitalize()} {v['value']} (\"{_md(v.get('reason'))}\")"
                                            for m, v in rd.items())
                ends.append(txt + ")")
            lines.append(f"  - {note.get('kind', 'pair')}: " + "; ".join(ends))
    grey = [r for r in rows if r["novelty"]["decision"] == "grey"]
    lines += ["", f"## Review queue ({len(grey)} grey rows)", "",
              "Kept with a flag the rule set treats as grey (rule set 2: `unparsed` only; rule set 1 also the Opus "
              "check's flag and the pair flag).  The covered-and-flagged rows and the both-ends-similar rows above "
              "are in the review queue as well.", ""]
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
            elif d["kind"] == "both_similar":
                lines.append(f"- both similar: {_note_text({'pair': d['pair'], 'kind': d.get('arrangement')}, labels)} "
                             "(see \"Both ends similar\" above)")
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
             error: Optional[BaseException], inputs: list, extra: Optional[dict] = None) -> dict:
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
                    "resumed_calls": runner.stats.get("resumed", 0), "rubrics": runner.rubric_pins,
                    "rules_of_run": runner.rules.as_dict()})
    summary.update(extra or {})
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
    ap.add_argument("--rules", type=int, choices=sorted(NV.RULES), default=NV.DEFAULT_RULES.version,
                    help="decision rules: 2 (default from 2026-10-07: decisions 12-15 and the cosine floor) or 1 (the "
                         "pilot's, decisions 1-11)")
    ap.add_argument("--cosine-floor", type=parse_floor, default=None,
                    help="listed traits below this cosine to the candidate are not judged by the overlap call (an "
                         "opposed trait's partner and a renamed_from match are); default the rule set's (rule set 2: "
                         f"{NV.DEFAULT_COSINE_FLOOR}, rule set 1: none); 'none' turns it off")
    ap.add_argument("--corpus-at", choices=("source", "current"), default=None,
                    help="where a run with a source (score --redecide, full-scan) reads the trait files and the seed "
                         "queue: as committed at the source run's git_sha (source, the default there) or --data-dir")


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


def _resume_model_mismatch(earlier: Optional[dict], relation_model: str) -> Optional[str]:
    """Why a ``--resume`` is refused: the run's earlier session asked the relation call of another model (the
    default moved from Haiku 4.5 to Haiku 5.5 on 2026-10-08, so the rest of an older run would otherwise go to
    the new model, and its answers on record would not be found)."""
    was = ((earlier or {}).get("models") or {}).get("relation")
    if was and was != relation_model:
        return (f"the run's earlier session asked the relation call of {was}, this one would ask {relation_model}; "
                f"resume with --relation-model {was}")
    return None


def _mean_chars(index: NV.CorpusIndex) -> float:
    import numpy as np
    return float(np.mean([len(t.label) + len(t.description) + 40 for t in index.traits.values()]))


def _cand_chars(cands) -> float:
    import numpy as np
    return float(np.mean([len(c.label) + len(c.gloss) + 40 for c in cands])) if cands else 140.0


# --------------------------------------------------------------------------- re-deciding a run on its records

def _check_score_selection(args, redecide: bool) -> Optional[str]:
    """``score`` takes one of --run / --keys / --unscored; ``--redecide`` and ``--relation-only`` take
    --from-batch (and optionally --keys)."""
    chosen = [n for n, v in (("--run", args.run), ("--keys", args.keys), ("--unscored", args.unscored)) if v]
    if getattr(args, "hide", None) and (redecide or getattr(args, "relation_only", False)):
        return "--hide is for a new score run (the recovery harness), not --redecide or --relation-only"
    if getattr(args, "relation_only", False):
        if redecide:
            return "--relation-only and --redecide are two different runs: choose one"
        if not args.from_batch:
            return "--relation-only needs --from-batch (the run whose candidates, corpus and list order it reuses)"
        if args.from_batch == args.batch_id:
            return "--relation-only writes a new run: --batch-id must differ from --from-batch"
        if args.run or args.unscored:
            return "--relation-only takes the source run's candidates (narrow them with --keys), not --run or --unscored"
        return None
    if getattr(args, "write_registry", False) and not redecide:
        return "--write-registry is for --redecide (an ordinary score run writes the registry as it decides)"
    if redecide:
        if getattr(args, "relation_model", None):
            return ("--redecide replays the source's relation answers on the source's relation model; --relation-model "
                    "applies to a new run or to --relation-only")
        if not args.from_batch:
            return "--redecide needs --from-batch (the run whose records are re-decided)"
        if args.from_batch == args.batch_id:
            return "--redecide writes a new run: --batch-id must differ from --from-batch"
        if args.run or args.unscored:
            return "--redecide takes the source run's candidates (narrow them with --keys), not --run or --unscored"
        return None
    if args.from_batch:
        return "--from-batch is for --redecide"
    if len(chosen) != 1:
        return "score takes exactly one of --run, --keys, --unscored"
    return None


def _relation_seed(source: dict) -> str:
    """The seed of the source's relation-call order (its own, or the one it replayed in turn)."""
    return ((source.get("run") or {}).get("settings") or {}).get("relation_seed") or source["batch_id"]


def source_rules(source: dict) -> NV.Rules:
    """The rules the source run decided under (its blocks say; none recorded: rule set 1)."""
    blocks = [r["novelty"] for r in source["results"]]
    names = {json.dumps(b.get("rules"), sort_keys=True) for b in blocks}
    if len(names) > 1:
        raise SystemExit(f"{source['batch_id']}'s rows were decided under {len(names)} rule sets; re-decide one at a time")
    return NV.rules_of(blocks[0]) if blocks else NV.RULES[1]


def offline_replay(*, rules: NV.Rules, replay: list, cands, vectors, index, sets, rubrics, cfg, query_form: str,
                   relation_seed: str, batch_id: str, relation_model: str = NR.RELATION_MODEL) -> tuple[dict, list]:
    """Every candidate decided under ``rules`` from the answers on record alone (nothing sent, nothing written):
    ``({key: block or None}, wanted)``, ``None`` for a candidate that needs a call not on record, ``wanted``
    the first such call of each (:class:`novelty_runner.OfflineTransport`).  ``relation_model`` must be the
    model of the relation answers on record (:func:`source_relation_model`): they are found by model."""
    tr = NR.OfflineTransport()
    r = NR.NoveltyRunner(client=None, batch_id=batch_id, rubrics=rubrics, index=index, label_sets=sets,
                         usage=MultiModelUsage(), responses_path=Path(os.devnull), k=cfg.k, mode="shortlist",
                         config_version=cfg.config_version, embedding=_embedding_settings(cfg, query_form), transport=tr,
                         rules=rules, relation_seed=relation_seed, replay_records=replay, relation_model=relation_model)
    states = r.run(cands, vectors)
    return {k: st.block for k, st in states.items()}, tr.wanted


def _walk_sig(nv: dict) -> list:
    return [(x["stem"], (x.get("sonnet") or {}).get("value"), (x.get("opus") or {}).get("value"), x.get("outcome"))
            for x in nv.get("readings") or []]


#: What "identical" means for a re-decided row: the decision, what covered it and how, the flags, the walk
#: (every pair judged, both readings, the outcome) and the stage-3 outputs.
_SAME_FIELDS = {"decision": lambda nv: nv["decision"], "reason": lambda nv: nv["reason"],
                "covered_by": lambda nv: nv.get("covered_by"), "review": lambda nv: list(nv.get("review") or []),
                "walk": _walk_sig, "shortlist": lambda nv: list(nv.get("shortlist") or []),
                "pair_flags": lambda nv: list(nv.get("pair_flags") or []),
                "pair_completion_for": lambda nv: list(nv.get("pair_completion_for") or []),
                "listed": lambda nv: [(x["stem"], x["cosine"], x.get("relation")) for x in nv.get("listed") or []]}


def reproduction_check(expected: list[dict], blocks: dict) -> dict:
    """Each row of ``expected`` (``{"key", "novelty"}``) against the replayed block of the same key, field by
    field (:data:`_SAME_FIELDS`): ``{"n", "identical", "differ": [{"key", "fields"}], "not_replayable"}``."""
    same, differ, missing = 0, [], []
    for r in expected:
        b = blocks.get(r["key"])
        if b is None:
            missing.append(r["key"])
            continue
        bad = [f for f, get in _SAME_FIELDS.items() if get(r["novelty"]) != get(b)]
        if bad:
            differ.append({"key": r["key"], "fields": bad})
        else:
            same += 1
    return {"n": len(expected), "identical": same, "differ": differ, "not_replayable": missing}


def redecide_estimate(wanted: list, *, listed_mean: float, rubrics: dict, index, cands, transport: str) -> Estimate:
    """The calls a re-decided run must send: each call not on record (one per candidate, the first its walk
    needs, at its own size), and for those candidates the walk after it at the plan's rates (3 pairs, early
    exit, Opus on its share).  Live unless ``transport`` is ``batches``."""
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    est = Estimate()
    by: dict[tuple, list] = {}
    for w in wanted:
        by.setdefault((w["step"], w["model"]), []).append(NR.call_tokens(w["call"]))
    for (step, model), toks in sorted(by.items()):
        n = len(toks)
        est.add(f"calls not on record: {step}", model + suffix, n, int(round(sum(t[0] for t in toks) / n)),
                int(round(sum(t[1] for t in toks) / n)))
    n_c = len({w["key"] for w in wanted})
    if n_c:
        st = NR.plan_estimate(n_candidates=n_c, n_scan=0, mean_listed=listed_mean,
                              relation_text_chars=len(rubrics["relation"]["text"]), trait_chars=_mean_chars(index),
                              cand_chars=_cand_chars(cands), transport=transport, n_embed=0)
        for x in st["overlap"].lines:
            est.add(f"their walks after it: {x.label}", x.model, x.n_calls, x.in_tok, x.out_tok)
    return est


def _state(nv: Optional[dict]) -> Optional[tuple]:
    """What a change is measured on: the decision, the covering trait, and how it was reached (``exact_label``
    or ``overlap``: a renamed_from row covered by the same trait through the walk has changed)."""
    return None if nv is None else (nv["decision"], nv.get("covered_by"), nv["reason"])


def decision_changes(*, source: dict, results: list[dict], chain: list[tuple[str, NV.Rules, dict]],
                     final_check: dict, new_calls: dict, rules: NV.Rules) -> dict:
    """``decision_changes.json``: every row whose decision or covering trait differs between the source and the
    re-decided run, with the steps of ``chain`` (version 1, then one decision added at a time) at which it
    changed; the reproduction check (the chain's first step against the source) and the final check (its last
    step against the run's own results)."""
    src = {r["key"]: r for r in source["results"]}
    res = {r["key"]: r for r in results}
    rows = []
    for key in sorted(src):
        a, b = src[key]["novelty"], (res.get(key) or {}).get("novelty")
        if b is None:
            continue
        steps, prev = [], _state(a)
        for name, _, blocks in chain[1:]:
            cur = _state(blocks.get(key))
            if cur is None:
                steps.append({"step": name, "note": "not replayable from the records at this step"})
                continue
            if cur != prev:
                steps.append({"step": name, "from": list(prev), "to": list(cur)})
                prev = cur
        if _state(a) == _state(b):
            continue
        rows.append({"key": key, "label": src[key]["label"], "gloss": src[key].get("gloss"), "cut_off": b["cut_off"],
                     "source": {"decision": a["decision"], "covered_by": a.get("covered_by"), "reason": a["reason"],
                                "review": a.get("review"), "pair_flags": a.get("pair_flags"),
                                "deciding_reading": a.get("deciding_reading"), "exact_label": a.get("exact_label")},
                     "now": {"decision": b["decision"], "covered_by": b.get("covered_by"), "reason": b["reason"],
                             "review": b.get("review"), "deciding_reading": b.get("deciding_reading"),
                             "exact_label": b.get("exact_label"), "renamed_from": b.get("renamed_from"),
                             "below_floor": b.get("below_floor"), "pair_notes": b.get("pair_notes"),
                             "n_pairs_judged": b.get("n_pairs_judged"),
                             "readings": b.get("readings") if b.get("renamed_from") else None},
                     "decision_changed": a["decision"] != b["decision"], "steps": steps})
    trans = Counter(f"{src[k]['novelty']['decision']} -> {res[k]['novelty']['decision']}" for k in src if k in res)
    by_step = Counter()
    for r in rows:
        for s in r["steps"]:
            if "from" in s:
                by_step[f"{s['step']}: {s['from'][0]} -> {s['to'][0]}"
                        + (" (covering trait or reason)" if s["from"][0] == s["to"][0] else "")] += 1
    notes = [{"key": k, "label": res[k]["label"], "decision": res[k]["novelty"]["decision"],
              "covered_by": res[k]["novelty"].get("covered_by"), "pair_notes": res[k]["novelty"]["pair_notes"]}
             for k in sorted(res) if res[k]["novelty"].get("pair_notes")]
    renamed = [{"key": k, "label": res[k]["label"], "decision": res[k]["novelty"]["decision"],
                "covered_by": res[k]["novelty"].get("covered_by"), "renamed_from": res[k]["novelty"]["renamed_from"],
                "deciding_reading": res[k]["novelty"].get("deciding_reading"),
                "readings": res[k]["novelty"].get("readings"), "review": res[k]["novelty"].get("review"),
                "source": src[k]["novelty"].get("exact_label") if k in src else None}
               for k in sorted(res) if res[k]["novelty"].get("renamed_from")]
    return {"source_batch": source["batch_id"], "rules": rules.as_dict(), "source_rules": chain[0][1].as_dict(),
            "chain": [name for name, _, _ in chain], "reproduction": chain_repro(chain, source),
            "final_check": final_check, "new_calls": new_calls,
            "counts": {"rows": len(src), "decision_changed": sum(1 for r in rows if r["decision_changed"]),
                       "covering_trait_changed": sum(1 for r in rows if not r["decision_changed"]),
                       "transitions": dict(sorted(trans.items())), "by_step": dict(sorted(by_step.items()))},
            "rows": rows, "both_similar": notes, "renamed_from": renamed}


def chain_repro(chain: list, source: dict) -> dict:
    return reproduction_check(source["results"], chain[0][2])


def write_decision_changes(out_dir: Path, *, source: dict, results: list[dict], runner: NR.NoveltyRunner,
                           rules: NV.Rules, ctx: dict) -> dict:
    """Replay the chain of rule steps offline on the source's records and this run's (no call), then write
    ``decision_changes.json`` and ``decision_changes.md`` beside the run's other files."""
    from assistant_axis.plot_metadata import json_metadata
    replay = list(source["records"]) + [r for r in runner.records if r.get("text") is not None]
    src_rules = source_rules(source)
    if src_rules.as_dict() == NV.RULES[1].as_dict() and rules.version == 2:
        steps = [(n, r) for n, r in NV.rule_chain(rules.cosine_floor)]
        steps[-1] = (steps[-1][0], rules)
    else:
        steps = [(f"source rules ({src_rules.name})", src_rules), (f"these rules ({rules.name})", rules)]
    chain = []
    for name, ru in steps:
        blocks, _ = offline_replay(rules=ru, replay=replay, **ctx)
        chain.append((name, ru, blocks))
    final_check = reproduction_check(results, chain[-1][2])
    new = [r for r in runner.records if r.get("batch_id") == runner.batch_id and r.get("text") is not None]
    new_calls = {"n": len(new), "by_step_model": dict(Counter(f"{r['step']}:{r['model']}" for r in new)),
                 "cost_usd": round(sum(NR.record_cost(r) for r in new), 6),
                 "keys": sorted({r["key"] for r in new})}
    dc = decision_changes(source=source, results=results, chain=chain, final_check=final_check, new_calls=new_calls,
                          rules=rules)
    env = json_metadata(dc, title=f"novelty_score decision changes {runner.batch_id} vs {source['batch_id']}")
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "decision_changes.json")
    labels = {s: t.label for s, t in runner.traits.items()}
    atomic_write_text(decision_changes_markdown(dc, batch_id=runner.batch_id, labels=labels),
                      out_dir / "decision_changes.md")
    return dc


def _short(r: Optional[dict]) -> str:
    """``stem: Sonnet s, Opus o`` of a deciding reading."""
    if not r:
        return ""
    return f"{r.get('stem')} at cosine {r.get('cosine'):.3f}: {_reading_text(r)}" if r.get("cosine") is not None else \
        f"{r.get('stem')}: {_reading_text(r)}"


def _reasons(r: Optional[dict]) -> str:
    if not r:
        return ""
    out = []
    for m in ("sonnet", "opus"):
        v = r.get(m)
        if v and v.get("reason"):
            out.append(f"{m.capitalize()} {v.get('value')}: \"{_md(v['reason'])}\"")
    return "; ".join(out)


def decision_changes_markdown(dc: dict, *, batch_id: str, labels: dict) -> str:
    """``decision_changes.md`` (see :func:`decision_changes`).  Links relative to ``data/candidates/novelty/<batch>/``."""
    L = lambda s: _trait_link(s, labels.get(s)) if s else ""  # noqa: E731
    c, rep, fin = dc["counts"], dc["reproduction"], dc["final_check"]
    rows = dc["rows"]
    lines = [f"# Decision changes: `{batch_id}` against `{dc['source_batch']}`", "",
             f"The source's {c['rows']} rows re-decided under `{dc['rules']['name']}` (cosine floor "
             f"{dc['rules']['cosine_floor']}) on the source's records (`novelty_score.py score --redecide`), against the "
             f"source's `{dc['source_rules']['name']}`.  New calls (only where a rule needed a reading not on record): "
             f"{dc['new_calls']['n']} ({json.dumps(dc['new_calls']['by_step_model'])}), ${dc['new_calls']['cost_usd']:.4f}.", "",
             "## Checks", "",
             f"- **Reproduction**: the source's own rules replayed on its records give {rep['identical']} of {rep['n']} rows "
             "identical (decision, covering trait, reason, flags, every pair judged with both readings and the outcome, "
             "shortlist, listed traits with cosines and relations, pair flags and completions)"
             + (f"; differ: {', '.join(d['key'] + ' (' + ', '.join(d['fields']) + ')' for d in rep['differ'][:20])}" if rep["differ"] else "")
             + (f"; not replayable: {', '.join(rep['not_replayable'][:20])}" if rep["not_replayable"] else "") + ".",
             f"- **Attribution**: the rules are added one decision at a time, each step replayed on the records with no "
             f"call ({' → '.join(dc['chain'])}); a change is credited to the step where it happens.  The last step "
             f"reproduces this run on {fin['identical']} of {fin['n']} rows"
             + (f" (differ: {', '.join(d['key'] for d in fin['differ'][:20])})" if fin["differ"] else "") + ".", "",
             "## Counts", "",
             f"{c['decision_changed']} rows changed decision and {c['covering_trait_changed']} kept it with a different "
             "covering trait (or reason).", "", "| source → now | rows |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in c["transitions"].items()]
    lines += ["", "| step: from → to | rows |", "|---|---|"]
    lines += [f"| {k} | {n} |" for k, n in c["by_step"].items()]

    def changed_at(r, step_prefix):
        return [s for s in r["steps"] if s.get("step", "").startswith(step_prefix) and "from" in s]

    floor = [r for r in rows if any(s["from"][0] == "covered" and s["to"][0] != "covered" for s in changed_at(r, "cosine floor"))]
    lines += ["", f"## Covers lost to the cosine floor ({len(floor)})", "",
              "Covered in the source by a trait whose cosine to the candidate is below the floor, so the walk no longer "
              "judges it.", ""]
    for r in floor:
        d = r["source"]["deciding_reading"]
        lines += [f"- **{_md(r['label'])}** (`{r['key']}`, cut-off {r['cut_off']}): source covered by {L(r['source']['covered_by'])} "
                  f"({_short(d)}); now **{r['now']['decision']}**"
                  + (f" by {L(r['now']['covered_by'])} ({_short(r['now']['deciding_reading'])})" if r["now"]["covered_by"] else "")
                  + ".", f"  {_reasons(d)}", f"  Gloss: {_md(r['gloss'])}"]
    d12 = [r for r in rows if changed_at(r, "decision 12")]
    d12_dec = [r for r in d12 if any(s["from"][0] != "covered" for s in changed_at(r, "decision 12"))]
    lines += ["", f"## Flagged rows that became covers (decision 12): {len(d12_dec)} changed decision, "
              f"{len(d12) - len(d12_dec)} changed covering trait", "",
              "Sonnet one below the cut-off and Opus at or above it on the trait that now covers the row (flagged "
              "`sonnet_below_opus_at`; the readings and reasons are in decisions.md's \"Covered, flagged\").", "",
              "| candidate | source | now | the reading |", "|---|---|---|---|"]
    for r in d12:
        lines.append(f"| {_md(r['label'])} | {r['source']['decision']}" + (f" by {L(r['source']['covered_by'])}" if r['source']['covered_by'] else "")
                     + f" | {r['now']['decision']} by {L(r['now']['covered_by'])} | {_md(_short(r['now']['deciding_reading']))} |")
    g2n = [r for r in rows if r["source"]["decision"] == "grey" and r["now"]["decision"] == "new"]
    lines += ["", f"## Grey rows that became new ({len(g2n)})", "",
              "| candidate | source flags | pair flags in the source | step |", "|---|---|---|---|"]
    for r in g2n:
        pf = "; ".join(f"{' / '.join(f['pair'])} both {f['both']}" for f in r["source"].get("pair_flags") or [])
        lines.append(f"| {_md(r['label'])} | {', '.join(r['source']['review'] or [])} | {_md(pf)} | "
                     f"{'; '.join(s['step'] for s in r['steps'] if 'from' in s)} |")
    rn = dc["renamed_from"]
    lines += ["", f"## The renamed_from rows, now judged (decision 15): {len(rn)}", "",
              "Covered at the exact-label stage in the source (the label is a corpus file's `renamed_from`); now judged like "
              "any other candidate, the current trait at the front of the shortlist.", "",
              "| candidate | current trait | now | covered by | deciding reading | pairs judged |", "|---|---|---|---|---|---|"]
    for r in rn:
        lines.append(f"| {_md(r['label'])} | {L(r['renamed_from']['current'])} | {r['decision']} | {L(r['covered_by'])} | "
                     f"{_md(_short(r['deciding_reading']))} | {len(r['readings'] or [])} |")
    for r in rn:
        rd = [x for x in r["readings"] or [] if x["stem"] == r["renamed_from"]["current"]]
        if rd:
            lines.append(f"- {_md(r['label'])} against {L(r['renamed_from']['current'])}: {_reasons(rd[0])}")
    others = [r for r in rows if r not in floor and r not in d12 and r not in g2n and not r["now"].get("renamed_from")]
    lines += ["", f"## Every other change ({len(others)})", "",
              "| candidate | source | now | steps |", "|---|---|---|---|"]
    for r in others:
        lines.append(f"| {_md(r['label'])} | {r['source']['decision']}" + (f" by {L(r['source']['covered_by'])}" if r['source']['covered_by'] else "")
                     + f" ({r['source']['reason']}) | {r['now']['decision']}"
                     + (f" by {L(r['now']['covered_by'])}" if r['now']['covered_by'] else "") + f" ({r['now']['reason']}"
                     + (", separator-blind" if (r["now"].get("exact_label") or {}).get("blind") else "") + ") | "
                     + "; ".join(f"{s['step']}: {s['from'][0]} → {s['to'][0]}" + (f" ({s['to'][1]})" if s['to'][1] else "")
                                 if "from" in s else f"{s['step']}: {s['note']}" for s in r["steps"]) + " |")
    bs = dc["both_similar"]
    lines += ["", f"## Both ends similar ({len(bs)} rows)", "",
              "Decision 13: the noted members were not judged and may not cover; the cosines and any readings on record "
              "are in decisions.md's \"Both ends similar\".", ""]
    for r in bs:
        lines.append(f"- {_md(r['label'])} ({r['decision']}" + (f" by {L(r['covered_by'])}" if r["covered_by"] else "") + "): "
                     + "; ".join(" / ".join(L(s) for s in n["pair"]) + (f" ({n['kind']})" if n.get("kind") != "pair" else "")
                                 for n in r["pair_notes"]))
    return "\n".join(lines) + "\n"


def _embedding_settings(cfg, query_form: str) -> dict:
    return {"model": cfg.live_model["model_id"], "query_form": query_form, "representation": cfg.representation,
            "variant": cfg.covered["space"]["variant"], "k": cfg.k}


def run_scoring(args, argv, *, mode: str, info: Optional[dict] = None) -> int:
    """``score`` and ``full-scan``.  ``info`` (the recovery harness calls this in-process): filled with the
    run's directory, plan, estimate and refusal (``out_dir``, ``plan``, ``estimate_usd``, ``estimate_lines``,
    ``refused``), and after a run with ``status`` and ``cost_usd``."""
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.provenance import current_file_input, current_files_input
    info = info if info is not None else {}
    paths.check_id(args.batch_id, "batch_id")
    redecide = mode == "shortlist" and bool(getattr(args, "redecide", False))
    if mode == "shortlist":
        bad = _check_score_selection(args, redecide)
        if bad:
            print(f"REFUSED: {bad}", file=sys.stderr)
            return 2
        if getattr(args, "relation_only", False):
            return run_relation_only(args, argv)
    relation_model = getattr(args, "relation_model", None) or NR.RELATION_MODEL
    out_dir = paths.novelty_dir(args.batch_id, candidates_dir=args.out_root)
    try:
        rubrics = load_m3_rubrics(args.rubrics_dir)
    except RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    rules = resolve_rules(args)
    cfg = MetricConfig.load(args.metric_config)
    reg = Registry(args.registry)
    rows = reg.fold()
    hide_rec = None
    if mode == "shortlist" and getattr(args, "hide", None):
        from assistant_axis.gapgen.recovery import load_hidden
        try:
            hide_rec = load_hidden(args.hide)
        except (OSError, ValueError) as exc:
            print(f"REFUSED (--hide): {exc}", file=sys.stderr)
            return 2
    hide = tuple(hide_rec["stems"]) if hide_rec else ()
    hide_meta = {"path": hide_rec["path"], "sha256": hide_rec["sha256"], "n_hidden": len(hide)} if hide_rec else None
    source = None
    if redecide or mode == "full_scan":
        source = load_source(args.from_batch, args.out_root, with_records=redecide)
    if redecide:   # the source's answers are replayed, and they are found by model
        relation_model = source_relation_model(source)
    data_dir, corpus_info = resolve_data_dir(args, source)
    if redecide:
        diffs = check_source_settings(source, cfg=cfg, query_form=args.query_form)
        if diffs:
            print(f"REFUSED: settings differ from {source['batch_id']}'s, so its requests would not replay: "
                  f"{'; '.join(diffs)}", file=sys.stderr)
            return 2
        cands, skipped = select_redecide(rows, args, source)
    elif mode == "shortlist":
        cands, skipped = select_candidates(rows, args, batch_id=args.batch_id, ignore_decided=bool(hide))
    else:
        cands, skipped = select_scan_sample(rows, args)
    if not cands:
        print(f"nothing to score ({json.dumps(skipped)})", file=sys.stderr)
        return 0
    cache = EM.EmbeddingCache(args.cache_dir)
    try:
        index, index_info = load_index(cfg, data_dir=data_dir, cache=cache, hide=hide)
    except ValueError as exc:            # a hidden stem the corpus does not have: drawn on another corpus
        print(f"REFUSED (--hide {args.hide}): {exc}", file=sys.stderr)
        return 2
    if index is None:
        print(f"{index_info['n_missing_from_cache']} corpus texts are not in the embedding cache "
              f"(first: {index_info['missing'][:5]}); they would be embedded (charged) by the run", file=sys.stderr)
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = {c.key: NV.query_text(c.label, c.gloss, query_form=args.query_form, representation=cfg.representation)
             for c in cands}
    found, miss = cache.lookup(embedder.tag, list(texts.values()))
    sets = label_sets_for(data_dir, hide)
    relation_seed = _relation_seed(source) if redecide else args.batch_id
    n_exact = sum(1 for c in cands if NV.exact_label_match(c.stem, sets, rules=rules)) if mode == "shortlist" else 0
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
                              cand_chars=_cand_chars(cands), transport=transport, n_embed=len(miss),
                              relation_model=relation_model)
    use = ("embeddings", "relation", "overlap") if mode == "shortlist" else ("embeddings", "full_scan")
    est = Estimate(lines=[x for s in use for x in stages[s].lines])
    plan = {"mode": mode, "n_candidates": len(cands), "n_exact_label": n_exact, "n_to_relation": n_live if mode == "shortlist" else 0,
            "skipped": skipped, "transport": transport, "query_form": args.query_form, "listed_mean": listed_mean,
            "n_query_texts_cached": len(found), "n_query_texts_to_embed": len(miss), "corpus": index_info,
            "rules": rules.as_dict(), "corpus_files": corpus_info}
    if hide_meta:
        plan["hide"] = hide_meta
    redecide_meta, offline_ctx = None, None
    if redecide:
        if index is None or miss:
            print("REFUSED: re-deciding replays the source's retrieval, so every corpus text and every candidate's "
                  "query text must be in the embedding cache (the source run embedded them); missing: corpus "
                  f"{index_info['n_missing_from_cache']}, query texts {len(miss)}", file=sys.stderr)
            return 2
        # unit rows, as embed_texts hands them to a run (the cache keeps the API's raw vectors; centring an
        # unnormalised one moves its cosines in the fifth decimal)
        unit = EM.normalize_rows([found[i] for i in range(len(cands))])
        offline_ctx = {"cands": cands, "vectors": {c.key: unit[i] for i, c in enumerate(cands)}, "index": index,
                       "sets": sets, "rubrics": rubrics, "cfg": cfg, "query_form": args.query_form,
                       "relation_seed": relation_seed, "batch_id": args.batch_id, "relation_model": relation_model}
        src_rules = source_rules(source)
        repro_blocks, _ = offline_replay(rules=src_rules, replay=source["records"], **offline_ctx)
        repro = reproduction_check(source["results"], repro_blocks)
        blocks0, wanted = offline_replay(rules=rules, replay=source["records"], **offline_ctx)
        est = redecide_estimate(wanted, listed_mean=listed_mean or 16.0, rubrics=rubrics, index=index, cands=cands,
                                transport=transport)
        stages, use = {"redecide": est}, ("redecide",)
        wanted_keys = sorted({w["key"] for w in wanted})
        preview = Counter(f"{r['novelty']['decision']} -> {blocks0[r['key']]['decision']}" for r in source["results"]
                          if blocks0.get(r["key"]) is not None)
        redecide_meta = {"from_batch": source["batch_id"], "source_rules": src_rules.as_dict(), "rules": rules.as_dict(),
                         "relation_seed": relation_seed, "relation_model": relation_model,
                         "write_registry": bool(getattr(args, "write_registry", False)),
                         "n_source_records": len(source["records"]),
                         "reproduction": {k: v for k, v in repro.items() if k != "rows"},
                         "calls_not_on_record": dict(Counter(f"{w['step']}:{w['model']}" for w in wanted)),
                         "candidates_needing_calls": wanted_keys,
                         "decided_offline": sum(1 for b in blocks0.values() if b is not None),
                         "offline_decisions": dict(sorted(preview.items()))}
        plan["redecide"] = redecide_meta
        ok = "OK" if repro["identical"] == repro["n"] else "MISMATCH"
        print(f"redecide: source {source['batch_id']} ({len(source['results'])} rows, {len(source['records'])} responses "
              f"on record; corpus {corpus_info.get('corpus_at')} {corpus_info.get('git_sha') or ''}); rules "
              f"{rules.name} (floor {rules.cosine_floor})")
        print(f"reproduction: {src_rules.name} replayed on the source's records: {repro['identical']} of {repro['n']} rows "
              f"identical [{ok}]" + (f"; differ: {[d['key'] for d in repro['differ'][:10]]}" if repro["differ"] else "")
              + (f"; not replayable: {repro['not_replayable'][:10]}" if repro["not_replayable"] else ""))
        print(f"calls not on record (sent live by the run): {len(wanted)} "
              f"{json.dumps(redecide_meta['calls_not_on_record'])}, for {len(wanted_keys)} candidates: {wanted_keys[:40]}")
        print(f"offline decisions (source -> {rules.name}, rows decided from the records alone): "
              f"{json.dumps(redecide_meta['offline_decisions'])}")
    print(f"plan: {json.dumps({k: v for k, v in plan.items() if k != 'redecide'})}")
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
    info.update(out_dir=str(out_dir), plan=plan, estimate_usd=est.usd, estimate_lines=[str(x) for x in est.lines],
                refused=refused, n_candidates=len(cands))
    if args.dry_run:
        if refused:
            print(f"DRY-RUN: the real run would be REFUSED: {refused}")
        writes_registry = mode == "shortlist" and not redecide and not hide
        print(f"DRY-RUN: would write {out_dir}/" + (f" and the registry {args.registry}" if writes_registry else
                                                     (" (no registry write: --hide)" if hide else "")))
        print(f"rubrics: {json.dumps({k: {'name': v['name'], 'version': v['version'], 'sha256': v['sha256'][:12]} for k, v in rubrics.items()})}")
        if redecide:
            need = {w["key"] for w in wanted}      # render a candidate whose calls are not on record, if any
            first = next((i for i, c in enumerate(cands) if c.key in need), None)
        else:
            first = next((i for i, c in enumerate(cands)
                          if i in found and not (sets and NV.exact_label_match(c.stem, sets, rules=rules))), None)
        if index is not None and first is not None:
            print(render_for(cands[first], found[first], index, rubrics, relation_seed, cfg.k,
                             relation_model=relation_model))
        elif not redecide:
            print("(no rendered prompt: no candidate's query embedding is cached yet; the run embeds them first)")
        return 0
    if refused:
        return 2
    status, resume_records, earlier = _prepare_out_dir(out_dir, args)
    if status:
        return status
    bad = _resume_model_mismatch(earlier, relation_model) if mode == "shortlist" else None
    if bad is None and earlier is not None and ((earlier.get("hide") or {}).get("sha256") != (hide_meta or {}).get("sha256")):
        bad = (f"the run's earlier session hid {(earlier.get('hide') or {}).get('path') or 'nothing'}, this one "
               f"{(hide_meta or {}).get('path') or 'nothing'} (by sha256): a resume must hide the same traits")
    if bad:
        print(f"REFUSED: {bad}", file=sys.stderr)
        return 2
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    run_meta = {"batch_id": args.batch_id, "mode": mode, "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv, "plan": plan,
                "transport": transport, "transport_reason": why, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by, "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")}
                                                               for k, v in rubrics.items()},
                "models": {"relation": relation_model, "relation_unsure": NR.UNSURE_MODEL, "overlap_first": NR.FIRST_MODEL,
                           "overlap_second": NR.SECOND_MODEL},
                "settings": {"config_version": cfg.config_version, "k": cfg.k, "representation": cfg.representation,
                             "variant": cfg.covered["space"]["variant"], "query_form": args.query_form,
                             "embedding_model": cfg.live_model["model_id"],
                             "cut_off_rule": "alignment score 0-1: 3; 2-3: 4; missing: 4",
                             "relation_max_tokens": NR.RELATION_MAX_TOKENS, "overlap_max_tokens": NR.OVERLAP_MAX_TOKENS,
                             "temperature": NR.TEMPERATURE, "cache_ttl_batches": NR.BATCH_CACHE_TTL,
                             "concurrency": args.concurrency, "ask_attempts": NR.ASK_ATTEMPTS,
                             "relation_seed": relation_seed, "cosine_floor": rules.cosine_floor},
                "rules": rules.as_dict(), "corpus": corpus_info,
                "resumed": bool(args.resume), "started_at": utc_now()}
    if mode == "full_scan":
        run_meta["full_scan"] = {"from_batch": args.from_batch, "sample": None if args.keys else args.sample,
                                 "sample_seed": None if args.keys else args.sample_seed, "keys": args.keys}
    if redecide:
        run_meta["redecide"] = redecide_meta
        run_meta["replay_from"] = source["replay_from"]
    if hide_meta:
        run_meta["hide"] = hide_meta
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
    if hide_meta:
        inputs.append(current_file_input(dep_key="hidden", path=Path(hide_meta["path"])))
    extra_block = ({"redecided_from": source["batch_id"]} if redecide else {}) | ({"hide": hide_meta} if hide_meta else {})
    status, error, runner = 0, None, None
    try:
        if index is None:
            index, index_info = load_index(cfg, data_dir=data_dir, cache=cache, usage=usage, allow_embed=True, hide=hide)
        canary = EM.check_canary(embedder, cfg.canary["texts"], cache, usage=usage)
        run_meta["canary"] = canary
        keys = [c.key for c in cands]
        E = EM.embed_texts(embedder, [texts[k] for k in keys], cache=cache, usage=usage)
        vectors = dict(zip(keys, E))
        if getattr(args, "embed_only", False):
            # the candidates are embedded (cached, charged to this run's usage.json); no LLM call is made, so
            # that a real candidate's prompt can be rendered (render --key, or the dry run) before the first one
            run_meta["embed_only"] = {"n_embedded": len(keys), "at": utc_now()}
            print(f"embedded {len(keys)} candidates' query texts; continue with --resume")
            return 0
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)

        def on_decided(states) -> None:
            # a re-decided run, and a run against a reduced corpus (--hide), write their own directory only
            if mode == "shortlist" and not redecide and not hide:
                n = write_blocks(reg, states, args.batch_id)
                logger.info("registry: %d novelty blocks written", n)

        runner = NR.NoveltyRunner(client=client, batch_id=args.batch_id, rubrics=rubrics, index=index, label_sets=sets,
                                  usage=usage, responses_path=out_dir / "responses.jsonl", k=cfg.k, mode=mode,
                                  config_version=cfg.config_version, concurrency=args.concurrency,
                                  embedding=_embedding_settings(cfg, args.query_form),
                                  resume_records=resume_records, on_decided=on_decided, rules=rules,
                                  relation_seed=relation_seed,
                                  replay_records=source["records"] if redecide else (),
                                  extra_block=extra_block or None, relation_model=relation_model)
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
        summary = None
        if runner is not None:
            summary = finalize(out_dir=out_dir, runner=runner, usage=usage, run_meta=run_meta, skipped=skipped,
                               status=status, error=error, inputs=inputs,
                               extra=({"redecide": redecide_meta} if redecide else {})
                               | ({"hide": hide_meta} if hide_meta else {}) or None)
        else:
            usage.write_json(out_dir / "usage.json")
            run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status)
            atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        logging.getLogger().removeHandler(fh)
        fh.close()
        info.update(status=status, cost_usd=round(usage.total_cost_usd, 6),
                    n_stalled=summary["n_stalled"] if summary else None)
    if redecide and runner is not None and status == 0 and summary and summary["n_stalled"] == 0:
        results = _read_jsonl(out_dir / "results.jsonl")
        dc = write_decision_changes(out_dir, source=source, results=results, runner=runner, rules=rules,
                                    ctx=offline_ctx | {"vectors": vectors})
        print(f"decision changes: {json.dumps(dc['counts'])}; reproduction {dc['reproduction']['identical']} of "
              f"{dc['reproduction']['n']}; run reproduced by the last step: {dc['final_check']['identical']} of "
              f"{dc['final_check']['n']}")
        if getattr(args, "write_registry", False):
            status = run_promotion(args.batch_id, out_root=args.out_root, registry_path=args.registry)
    elif redecide:
        print("decision_changes.md not written: the run did not decide every candidate (resume it first)"
              + ("; nothing written to the registry" if getattr(args, "write_registry", False) else ""),
              file=sys.stderr)
    return status


# --------------------------------------------------------------------------- the relation call alone

def relation_like_for_like(calls: list, source_records: list) -> dict:
    """Each relation call of a relation-only run (``novelty_runner.Call``) against the source's relation call for
    the same candidate (its last answered one): the same user turn (the candidate, its gloss and the listed
    traits in the same order), system prompt, ``max_tokens`` and cache setting, only the model differing.
    ``{"n", "identical", "differ": [{"key", "fields"}], "not_on_record": [keys], "source_models": {...}}``."""
    src: dict[str, dict] = {}
    for r in source_records:
        if r.get("step") == "relation" and r.get("text") is not None:
            src[r["key"]] = r
    same, differ, missing = 0, [], []
    models = Counter()
    for c in calls:
        r = src.get(c.key)
        if r is None:
            missing.append(c.key)
            continue
        models[r.get("model")] += 1
        req = r.get("request") or {}
        bad = [f for f, a, b in (("user", c.user, r.get("user")), ("system", c.prompt_sha256, r.get("prompt_sha256")),
                                  ("stems", list(c.stems), r.get("stems")), ("max_tokens", c.max_tokens, req.get("max_tokens")),
                                  ("cache_system", c.cache_system, req.get("cache_system"))) if a != b]
        if bad:
            differ.append({"key": c.key, "fields": bad})
        else:
            same += 1
    return {"n": len(calls), "identical": same, "differ": differ, "not_on_record": sorted(missing),
            "source_models": dict(models)}


def run_relation_only(args, argv) -> int:
    """``score --relation-only --from-batch B --batch-id R [--relation-model M] [--keys K ...]``
    (coding_plan_haiku55.md, comparison B): stage 3 of M3 on ``--relation-model`` for B's candidates, with B's
    corpus (as committed at B's ``git_sha``, unless ``--corpus-at current``), B's list order (its relation
    seed) and B's cached query embeddings, then stop: the relation calls and Sonnet's unsure re-ask are sent,
    the shortlists built under ``--rules``; no overlap call, no decision, no registry write.  Writes
    ``novelty/<R>/``: ``responses.jsonl``, ``relation.jsonl`` (one row per candidate that reached the call:
    every answer, the final relations, the counts, the shortlist and its length, each call's usage),
    ``relation_summary.json``, ``usage.json``, ``run.json``, ``run.log``.  The dry run (and the run) first
    checks that every request is B's request for the same candidate with only the model changed."""
    from assistant_axis.gapgen import embed as EM
    from assistant_axis.gapgen.metric_config import MetricConfig
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input, current_files_input
    relation_model = args.relation_model or NR.RELATION_MODEL
    out_dir = paths.novelty_dir(args.batch_id, candidates_dir=args.out_root)
    try:
        rubrics = load_m3_rubrics(args.rubrics_dir)
    except RubricError as exc:
        print(f"REFUSED (rubric not pinned): {exc}", file=sys.stderr)
        return 2
    rules = resolve_rules(args)
    cfg = MetricConfig.load(args.metric_config)
    rows = Registry(args.registry).fold()
    source = load_source(args.from_batch, args.out_root, with_records=True)
    data_dir, corpus_info = resolve_data_dir(args, source)
    diffs = check_source_settings(source, cfg=cfg, query_form=args.query_form)
    if diffs:
        print(f"REFUSED: settings differ from {source['batch_id']}'s, so its lists would not be rebuilt: "
              f"{'; '.join(diffs)}", file=sys.stderr)
        return 2
    cands, skipped = select_redecide(rows, args, source)
    if not cands:
        print(f"nothing to send ({json.dumps(skipped)})", file=sys.stderr)
        return 0
    cache = EM.EmbeddingCache(args.cache_dir)
    index, index_info = load_index(cfg, data_dir=data_dir, cache=cache)
    embedder = EM.OpenAIEmbedder(cfg.live_model["model_id"])
    texts = [NV.query_text(c.label, c.gloss, query_form=args.query_form, representation=cfg.representation)
             for c in cands]
    found, miss = cache.lookup(embedder.tag, texts)
    if index is None or miss:
        print("REFUSED: the relation-only run rebuilds the source's lists, so every corpus text and every candidate's "
              f"query text must be in the embedding cache; missing: corpus {index_info['n_missing_from_cache']}, query "
              f"texts {len(miss)}", file=sys.stderr)
        return 2
    unit = EM.normalize_rows([found[i] for i in range(len(cands))])      # as score --redecide reads them
    vectors = {c.key: unit[i] for i, c in enumerate(cands)}
    sets = label_sets_for(data_dir)
    relation_seed = _relation_seed(source)
    settings = {"config_version": cfg.config_version, "k": cfg.k, "representation": cfg.representation,
                "variant": cfg.covered["space"]["variant"], "query_form": args.query_form,
                "embedding_model": cfg.live_model["model_id"], "relation_max_tokens": NR.RELATION_MAX_TOKENS,
                "temperature": NR.TEMPERATURE, "concurrency": args.concurrency, "ask_attempts": NR.ASK_ATTEMPTS,
                "relation_seed": relation_seed, "cosine_floor": rules.cosine_floor}

    def make_runner(**kw):
        return NR.NoveltyRunner(batch_id=args.batch_id, rubrics=rubrics, index=index, label_sets=sets, k=cfg.k,
                                mode="shortlist", config_version=cfg.config_version,
                                embedding=_embedding_settings(cfg, args.query_form), rules=rules,
                                relation_seed=relation_seed, relation_model=relation_model, relation_only=True, **kw)
    # offline first (nothing sent): who reaches the relation call, the requests, and the check against the source
    tr = NR.OfflineTransport()
    off = make_runner(client=None, usage=MultiModelUsage(), responses_path=Path(os.devnull), transport=tr)
    off_states = off.run(cands, vectors)
    first_calls = [w["call"] for w in tr.wanted if w["step"] == "relation"]
    not_reached = dict(Counter("exact_label" if (st.block or {}).get("reason") == "exact_label" else
                               (st.block or {}).get("reason") or st.stalled or "?"
                               for st in off_states.values() if st.relation is None))
    lfl = relation_like_for_like(first_calls, source["records"])
    transport, why = choose_transport(args.transport, len(first_calls))
    suffix = BATCH_SUFFIX if transport == "batches" else ""
    est = Estimate()
    if first_calls:
        toks = [NR.call_tokens(c) for c in first_calls]
        n = len(toks)
        measured = any(f in relation_model.lower() for f in NR.RELATION_OUT_MEASURED)
        est.add(f"relation call on {OT.SHORT.get(relation_model, relation_model)} "
                f"({'output measured, thinking included' if measured else 'thinking not in the figure'})",
                relation_model + suffix, n, int(round(sum(t[0] for t in toks) / n)), int(round(sum(t[1] for t in toks) / n)))
        sf = OT.tokenizer_factor(NR.UNSURE_MODEL)
        u_share, u_traits = NR.unsure_for(relation_model)
        n_uns = int(round(u_share * n))
        est.add(f"unsure re-ask ({u_share:.0%} of candidates, {u_traits:g} traits)", NR.UNSURE_MODEL + suffix,
                n_uns, int(round((len(rubrics["relation"]["text"]) + _cand_chars(cands) + u_traits * _mean_chars(index))
                                 / NR.CHARS_PER_TOKEN * sf)),
                int(round((NR.RELATION_OUT_BASE + NR.RELATION_OUT_PER_TRAIT * u_traits) * sf)))
    plan = {"mode": "relation_only", "from_batch": source["batch_id"], "n_candidates": len(cands),
            "n_to_relation": len(first_calls), "not_reached": not_reached, "skipped": skipped, "transport": transport,
            "relation_model": relation_model, "rules": rules.as_dict(), "corpus_files": corpus_info,
            "listed_mean": round(sum(len(c.stems) for c in first_calls) / len(first_calls), 3) if first_calls else None,
            "like_for_like": {k: v for k, v in lfl.items() if k != "differ"} | {"n_differ": len(lfl["differ"])}}
    print(f"relation only: source {source['batch_id']} ({len(source['results'])} rows; corpus "
          f"{corpus_info.get('corpus_at')} {corpus_info.get('git_sha') or ''}); relation model {relation_model}; rules "
          f"{rules.name} (floor {rules.cosine_floor}); relation seed {relation_seed}")
    print(f"like for like: {lfl['identical']} of {lfl['n']} requests identical to the source's relation call for the same "
          f"candidate but for the model (source models {json.dumps(lfl['source_models'])}); differ {len(lfl['differ'])}"
          + (f" {lfl['differ'][:5]}" if lfl["differ"] else "") + f"; not on record in the source {len(lfl['not_on_record'])}"
          + (f" {lfl['not_on_record'][:12]}" if lfl["not_on_record"] else ""))
    print(f"plan: {json.dumps({k: v for k, v in plan.items() if k != 'like_for_like'})}")
    print(f"transport: {transport} ({why})")
    print(f"estimate:\n{est.format()}\ntotal estimate = ${est.usd:.3f}")
    refused: Optional[str] = None
    cap = None
    try:
        cap = confirm_or_abort(est.usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                               confirmed_by=args.confirmed_by)
        print(f"hard cap: ${cap:.2f}")
    except CostRefused as exc:
        refused = exc.msg
    if refused is None and lfl["differ"]:
        refused = f"{len(lfl['differ'])} requests differ from the source's beyond the model (first: {lfl['differ'][:3]})"
        print(f"REFUSED: {refused}", file=sys.stderr)
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
        print(f"DRY-RUN: would write {out_dir}/ (no registry write)")
        print(f"rubrics: {json.dumps({k: {'name': v['name'], 'version': v['version'], 'sha256': v['sha256'][:12]} for k, v in rubrics.items()})}")
        if first_calls:
            i = next(j for j, c in enumerate(cands) if c.key == first_calls[0].key)
            print(render_for(cands[i], found[i], index, rubrics, relation_seed, cfg.k, relation_model=relation_model,
                             overlap=False))
        return 0
    if refused:
        return 2
    status, resume_records, earlier = _prepare_out_dir(out_dir, args)
    if status:
        return status
    bad = _resume_model_mismatch(earlier, relation_model)
    if bad:
        print(f"REFUSED: {bad}", file=sys.stderr)
        return 2
    fh = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
    fh.setFormatter(log_formatter())
    logging.getLogger().addHandler(fh)
    run_meta = {"batch_id": args.batch_id, "mode": "relation_only", "git_sha": sha, "allow_dirty": bool(args.allow_dirty),
                "dirty_check": dirty_check, "argv": sys.argv[1:] if argv is None else argv, "plan": plan,
                "transport": transport, "transport_reason": why, "estimate_usd": round(est.usd, 4),
                "estimate_lines": [str(x) for x in est.lines], "budget_usd": args.budget_usd, "cap_usd": cap,
                "confirmed_by": args.confirmed_by,
                "rubrics": {k: {kk: v[kk] for kk in ("name", "version", "sha256")} for k, v in rubrics.items()},
                "models": {"relation": relation_model, "relation_unsure": NR.UNSURE_MODEL}, "settings": settings,
                "rules": rules.as_dict(), "corpus": corpus_info, "from_batch": source["batch_id"],
                "like_for_like": lfl, "resumed": bool(args.resume), "started_at": utc_now()}
    if earlier:
        run_meta["earlier_sessions"] = list(earlier.pop("earlier_sessions", [])) + [earlier]
    atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
    usage = GuardedUsage(budget_usd=cap, usage_path=out_dir / "usage.json")
    if args.resume:
        from assistant_axis.gapgen.batches import with_current_batch_keys
        usage.merge_from(with_current_batch_keys(MultiModelUsage.load_or_create(out_dir / "usage.json")))
    status, error, runner = 0, None, None
    try:
        from dotenv import load_dotenv
        import anthropic
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)
        runner = make_runner(client=client, usage=usage, responses_path=out_dir / "responses.jsonl",
                             concurrency=args.concurrency, resume_records=resume_records)
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
        usage.write_json(out_dir / "usage.json")
        if runner is not None:
            rel_rows = NR.relation_rows(runner.states, runner.records)
            atomic_write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rel_rows),
                              out_dir / "relation.jsonl")
            summary = NR.relation_summary(rel_rows, runner.records, usage, skipped=skipped, not_reached=not_reached)
            summary.update({"batch_id": args.batch_id, "from_batch": source["batch_id"], "relation_model": relation_model,
                            "parse_rates": runner.warn_parse_rates(logger), "like_for_like": lfl,
                            "stopped_by_budget": status == 2,
                            "stopped_by_error": f"{type(error).__name__}: {error}" if error is not None else None,
                            "stalled": {k: st.stalled for k, st in runner.states.items() if st.stalled},
                            "rubrics": runner.rubric_pins, "rules_of_run": rules.as_dict()})
            inputs = [current_file_input(dep_key="metric_config", path=args.metric_config),
                      current_files_input(dep_key="rubrics", paths=[paths.RUBRICS_DIR / "relation.md"]),
                      current_file_input(dep_key="source_results", path=source["dir"] / "results.jsonl")]
            env = json_metadata(summary, title=f"novelty_score relation-only {args.batch_id}", inputs=inputs)
            atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False) + "\n", out_dir / "relation_summary.json")
            print(usage.log_line())
            print(json.dumps({k: summary[k] for k in ("n_candidates_reached", "call_status", "answers", "final",
                                                      "unsure_rate", "spend_usd")}))
        run_meta.update(finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 4), status=status,
                        stopped_by_error=f"{type(error).__name__}: {error}" if error is not None else None)
        atomic_write_text(json.dumps(run_meta, indent=2) + "\n", out_dir / "run.json")
        logging.getLogger().removeHandler(fh)
        fh.close()
    return status


def select_scan_sample(rows: dict, args) -> tuple[list[NR.M3Candidate], dict]:
    """The full scan's candidates: a seeded sample of ``--sample`` of the main run's candidates that reached the
    relation call (reason ``overlap``), read from its ``results.jsonl``, or the registry keys of ``--keys`` (in
    the order given; a key the main run did not walk is scanned all the same, and counted); their glosses from
    the registry."""
    main = paths.novelty_dir(args.from_batch, candidates_dir=args.out_root) / "results.jsonl"
    if not main.exists():
        raise SystemExit(f"{main} not found: run score --batch-id {args.from_batch} first")
    res = [json.loads(x) for x in main.read_text(encoding="utf-8").splitlines() if x.strip()]
    eligible = sorted(r["key"] for r in res if r["novelty"]["reason"] == "overlap")
    if getattr(args, "keys", None):
        missing = [k for k in args.keys if k not in rows]
        if missing:
            raise SystemExit(f"not in the registry: {', '.join(missing[:10])}")
        pick = list(dict.fromkeys(args.keys))
        extra = {"keys": len(pick), "keys_not_walked_in_main": sum(1 for k in pick if k not in set(eligible))}
    else:
        n = min(args.sample, len(eligible))
        pick = sorted(random.Random(args.sample_seed).sample(eligible, n))
        extra = {}
    out, skipped = [], Counter(extra)
    for k in pick:
        cand, why = NR.candidate_from_row(rows[k]) if k in rows else (None, "not_in_registry")
        if cand is None:
            skipped[why] += 1
        else:
            out.append(cand)
    return out, {"eligible_in_main": len(eligible), **skipped}


def render_for(cand: NR.M3Candidate, e_raw, index: NV.CorpusIndex, rubrics: dict, batch_id: str, k: int,
               *, exclude: tuple = (), relation_model: str = NR.RELATION_MODEL, overlap: bool = True) -> str:
    """The relation request (on ``relation_model``) and, unless ``overlap`` is false, the first overlap
    request for one candidate, as the models receive them."""
    from assistant_axis.gapgen.llm import request_params
    q = index.project(e_raw)
    listed = NV.expand(index.retrieve(q, k, exclude=exclude), index.traits, lambda s: index.cosine_to(q, s))
    order = NV.relation_order([x.stem for x in listed], batch_id, cand.key)
    user = NV.render_relation_user(cand.label, cand.gloss, [(index.traits[s].label, index.traits[s].description)
                                                            for s in order])
    p = request_params(model=relation_model, system=rubrics["relation"]["text"], user=user,
                       max_tokens=NR.RELATION_MAX_TOKENS, temperature=NR.TEMPERATURE, cache_system=False)
    head = {k2: v for k2, v in p.items() if k2 not in ("system", "messages")}
    relation_text = (f"=== relation call, request settings {json.dumps(head)} ===\n--- system (relation "
                     f"v{rubrics['relation']['version']}) ---\n{rubrics['relation']['text']}\n--- user ---\n{user}\n")
    listing = "\n".join(f"  {x.stem}: cosine {x.cosine:.3f}, {x.via}" + (f" rank {x.rank}" if x.rank else
                                                                           f" from {', '.join(x.expanded_from)}")
                        + (f", partners {', '.join(x.partners)}" if x.partners else "") for x in listed)
    top = f"=== candidate {cand.key} ({cand.label}), {len(listed)} listed traits (not shown to the model) ===\n{listing}\n"
    if not overlap:
        return top + relation_text
    first = listed[0].stem
    pc = OT.PairCall(call_id=f"{cand.key}>{first}", set="m3", target=cand.key, listed=[first])
    ou = OT.render_single(pc, {cand.key: {"label": cand.label, "description": cand.gloss},
                               first: {"label": index.traits[first].label, "description": index.traits[first].description}})
    po = request_params(model=NR.FIRST_MODEL, system=rubrics["overlap"]["text"], user=ou,
                        max_tokens=NR.OVERLAP_MAX_TOKENS, temperature=NR.TEMPERATURE, cache_system=True)
    ohead = {k2: v for k2, v in po.items() if k2 not in ("system", "messages")}
    return (top + relation_text +
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
                   # whether the scan's rules cover on this pair (a scan from before rule set 2: "cut" only)
                   "cuts": p.get("cuts", p["verdict"] == "cut"), "below_floor": p.get("below_floor", False),
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
    cut = [p for p in pairs if p["cuts"]]
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
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--run", type=parse_run, action="append", help="GENERATOR/RUN_ID (repeatable)")
    g.add_argument("--keys", nargs="+", help="registry keys (with --redecide: narrows the source run's rows)")
    g.add_argument("--unscored", action="store_true", help="every row with no novelty block")
    sp.add_argument("--redecide", action="store_true",
                    help="re-run the decision rules on --from-batch's records (its candidates, corpus, relation order, "
                         "relation model and answers on record); only calls a rule now needs and the source never made "
                         "are sent; writes this run's directory and decision_changes.md, and the registry only with "
                         "--write-registry")
    sp.add_argument("--write-registry", action="store_true",
                    help="with --redecide: once every candidate is decided, write the run's novelty blocks to the "
                         "registry, replacing the re-decided runs' blocks (idempotent per run and key; a row decided "
                         "by another run since is left alone); the same as promote-redecide afterwards")
    sp.add_argument("--from-batch", default=None,
                    help="with --redecide: the run to re-decide; with --relation-only: the run whose candidates, corpus, "
                         "list order and query embeddings are reused")
    sp.add_argument("--relation-model", default=None,
                    help=f"the relation call's model (default {NR.RELATION_MODEL}); the unsure re-ask stays on "
                         f"{NR.UNSURE_MODEL}.  Not with --redecide, which replays the source's answers on the source's "
                         f"model")
    sp.add_argument("--relation-only", action="store_true",
                    help="with --from-batch B (and optionally --keys): stage 3 alone for B's candidates (the relation "
                         "call on --relation-model and the unsure re-ask, B's corpus, list order and embeddings), then "
                         "stop: relation.jsonl and relation_summary.json, no overlap call, no decision, no registry "
                         "write; to compare the relation call on another model without re-running M3")
    sp.add_argument("--hide", type=Path, default=None, metavar="HIDDEN_JSON",
                    help="score against the corpus without the traits this file's 'hidden' list names (the recovery "
                         "harness's hidden.json): left out of the index, the expansion and the exact-label check; the "
                         "run never writes the registry and takes its rows whatever other runs decided")
    sp.add_argument("--rescore", action="store_true", help="also rows another run has decided (their block is replaced)")
    sp.add_argument("--include-held", action="store_true", help="also rows on a holding list (nationalities)")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--embed-only", action="store_true",
                    help="embed the candidates (the canary first; charged to the run's usage.json) and stop before any "
                         "LLM call, so a real candidate's prompt can be rendered first; continue with --resume")
    sp.set_defaults(func=lambda a, argv: run_scoring(a, argv, mode="shortlist"))
    sp = sub.add_parser("full-scan", help="the overlap call on every listed trait of a sample (no registry writes)")
    _common_args(sp)
    sp.add_argument("--from-batch", required=True)
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--sample", type=int, default=DEFAULT_SCAN_SAMPLE)
    g.add_argument("--keys", nargs="+", help="registry keys to scan, in place of a sample")
    sp.add_argument("--sample-seed", type=int, default=0)
    sp.set_defaults(func=lambda a, argv: run_scoring(a, argv, mode="full_scan"))
    sp = sub.add_parser("promote-redecide",
                        help="write a finished re-decided run's novelty blocks to the registry (no API call)")
    sp.add_argument("--batch-id", required=True, help="the re-decided run (score --redecide --batch-id)")
    sp.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    sp.add_argument("--out-root", type=Path, default=None)
    sp.add_argument("--dry-run", action="store_true", help="count what would be written; write nothing")
    sp.set_defaults(func=lambda a, argv: run_promotion(a.batch_id, out_root=a.out_root, registry_path=a.registry,
                                                       dry_run=a.dry_run))
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
