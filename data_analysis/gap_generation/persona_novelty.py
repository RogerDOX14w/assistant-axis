#!/usr/bin/env python3
"""Novelty measured in persona space (workstream 12; reports/trait_gap_generation/coding_plan_12_persona_space.md).

    uv run python data_analysis/gap_generation/persona_novelty.py <command> ...

The library is :mod:`assistant_axis.gapgen.persona_space`.  Commands:

* ``fit --fit-id F``: the pool (the May 8-slot vectors at slot 6, layer 25, centred, soft shear L=3), the corpus
  texts (``label: description``, ``w20``, from the embedding cache: $0 when every one is cached, which it is), the
  arrangement-grouped cross-validation over the alphas and the N sweep, the chosen alpha and N, the final model on
  every training row (``model.npz``, git-ignored, rebuilt by running ``fit`` again), ``calibration.json``, ``cv.json``,
  ``fit_report.md`` and ``fit_report.png`` in ``data/candidates/persona/fit/F/``.  Roger's gate-1 moves:
  ``--alpha``, ``--N``, ``--dup-threshold``, ``--novel-pct`` with ``--thresholds-set-by``.  On an existing fit
  directory without ``--force``, only a missing ``model.npz`` is rebuilt (and checked against the recorded
  training rows and alpha).
* ``score --batch-id B --fit-id F (--run G/R ... | --keys K ... | --all-rows) [--holding states|physical]
  [--write-registry] [--quantile 0.10]``: the candidates M3 takes (``candidate_from_row``), embedded as ``label:
  gloss`` (``w20``; cache misses only, the 8 canary texts first, OpenAI direct key), predicted, scored, compared
  with M3: ``scores.jsonl``, ``summary.json``, ``agreement.json``, ``disagreements.jsonl``, ``disagreements.md``,
  ``score_report.md``, ``predictions.npz`` (git-ignored, float16), ``run.json``, ``usage.json`` in
  ``data/candidates/persona/score/B/``; with ``--write-registry`` the ``persona`` block on every scored row
  (decision 1a; ``novelty`` untouched).  The estimate is printed first and checked against ``--budget-usd``.
* ``apply --batch-id B``: the batch's blocks (``scores.jsonl``, with the readings of ``readings.jsonl``) applied to
  this checkout's registry log; $0, idempotent.
* ``compare --batch-id B``: the agreement and the disagreements again, from ``scores.jsonl`` and M3's decisions in
  the registry now; $0.
* ``judge-disagreements --batch-id B [--kind dup_vs_new] [--max-pairs 700] [--budget-usd 5] [--resume]
  [--write-registry]`` (decision 2b): M3's overlap call (rubric A as pinned, Sonnet 5.5 then Opus 5.5 under M3's
  rule, one pair per call, live) on each listed disagreement, the candidate as the target and the persona-nearest
  corpus trait as the other: ``responses.jsonl`` (every response, recorded before it is parsed), ``readings.jsonl``,
  the ``reading`` on the blocks (with ``--write-registry``), never the ``novelty`` block.  The dry run prints the
  rendered prompt of the first pair.
* ``prospective predict --fit-id F``: the corpus entities with a file and no training vector, scored with the fit
  ($0: their texts are cached): ``data/candidates/persona/prospective/F/predicted.jsonl``.
  ``prospective compare --fit-id F --new-vectors-dir DIR [--N n]``: after the next extraction ($0).
* ``report --batch-id B``: ``score_report.md`` again.

Common flags: ``--data-dir``, ``--vectors-dir`` (default the 8-slot tree), ``--pool-cache-dir`` (where
``persona_s6_l25.npz`` is), ``--registry`` (the live log) or ``--snapshot`` (the tracked one, read-only),
``--out-root``, ``--cache-dir`` (the embedding cache), ``--budget-usd``, ``--confirm-expensive --confirmed-by``,
``--allow-dirty`` (a paid command refuses uncommitted platform code), ``--dry-run`` (prints the plan and the
estimate; writes nothing, calls nothing).  Every JSON output carries the provenance envelope; every paid command
writes ``usage.json`` and ``run.json``.  Exit status: 0; 1 (missing inputs, an existing directory); 2 (refused, or a
budget stop).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.atomic_io import atomic_write_text  # noqa: E402
from assistant_axis.gapgen import novelty as NV  # noqa: E402
from assistant_axis.gapgen import novelty_runner as NR  # noqa: E402
from assistant_axis.gapgen import paths  # noqa: E402
from assistant_axis.gapgen import persona_space as PS  # noqa: E402
from assistant_axis.gapgen.cost import CostRefused, Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.persona import DEFAULT_VECTORS_DIR  # noqa: E402
from assistant_axis.gapgen.persona_space import calibrate as CAL  # noqa: E402
from assistant_axis.gapgen.persona_space import compare as CMP  # noqa: E402
from assistant_axis.gapgen.persona_space import fit as FIT  # noqa: E402
from assistant_axis.gapgen.persona_space import judge as JDG  # noqa: E402
from assistant_axis.gapgen.persona_space import pool as POOL  # noqa: E402
from assistant_axis.gapgen.persona_space import prospective as PRO  # noqa: E402
from assistant_axis.gapgen.persona_space import report as REP  # noqa: E402
from assistant_axis.gapgen.persona_space import score as SC  # noqa: E402
from assistant_axis.gapgen.registry import Registry, read_snapshot, snapshot_file, utc_now, utc_stamp  # noqa: E402
from assistant_axis.gapgen.runs import configure_logging, dirty_refusal, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage, cost_for_usage  # noqa: E402
from assistant_axis.plot_metadata import json_metadata  # noqa: E402

logger = logging.getLogger("persona_novelty")

#: Characters per input token for the embedding estimate (OpenAI's rule of thumb for English).
CHARS_PER_TOKEN = 4.0
#: The judge's spend over its estimate: the recovery harness's measured factor for the same calls (match stage).
ESTIMATE_CALIBRATION = 1.25
M1_GLOSS_CHECK = paths.DATA_CANDIDATES / "filter" / "m1_validation_r2" / "results.jsonl"


# --------------------------------------------------------------------------- helpers

def repo_rel(path: Path) -> str:
    """``path`` relative to the root of the checkout that holds it (the nearest ancestor with a ``.git``), so a
    record never carries a home directory; the absolute path when no checkout holds it."""
    p = Path(path).resolve()
    for a in [p] + list(p.parents):
        if (a / ".git").exists():
            return str(p.relative_to(a)) or "."
    return str(p)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def files_fingerprint(paths_: list[Path]) -> str:
    return _sha(json.dumps([[p.name, p.stat().st_size, int(p.stat().st_mtime)] for p in sorted(paths_)]))


def vectors_input(vectors_dir: Path) -> dict:
    d = Path(vectors_dir)
    files = [f for k in POOL.KINDS for f in (d / k / "vectors").glob("*.pt")]
    return {"path": repo_rel(d), "n_files": len(files), "fingerprint_sha256": files_fingerprint(files)}


def corpus_input(data_dir: Path) -> dict:
    out = {}
    for k in POOL.KINDS:
        files = list((Path(data_dir) / k / "instructions").glob("*.json"))
        h = hashlib.sha256()
        for f in sorted(files):
            h.update(f.name.encode())
            h.update(f.read_bytes())
        out[k] = {"path": repo_rel(Path(data_dir) / k / "instructions"), "n_files": len(files),
                  "content_sha256": h.hexdigest()}
    return out


def file_specs(**named: Optional[Path]) -> list:
    """Provenance ``InputSpec``s for files, their paths relative to the checkout that holds them."""
    from dataclasses import replace

    from assistant_axis.provenance import current_file_input
    out = []
    for k, p in named.items():
        if p is not None and Path(p).exists():
            out.append(replace(current_file_input(dep_key=k, path=Path(p)), path=repo_rel(Path(p))))
    return out


def write_json(path: Path, payload, *, title: str, inputs=None) -> None:
    env = json_metadata(payload, title=title, inputs=inputs)
    atomic_write_text(json.dumps(env, indent=2, ensure_ascii=False, default=_default) + "\n", path)


def _default(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    raise TypeError(type(o))


def write_jsonl(path: Path, rows) -> None:
    atomic_write_text("".join(json.dumps(r, ensure_ascii=False, default=_default) + "\n" for r in rows), path)


def read_jsonl(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]


def read_env(path: Path) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("result", d)


def embed_estimate(texts: list[str], model: str) -> tuple[int, float]:
    tok = int(round(sum(len(t) for t in texts) / CHARS_PER_TOKEN))
    return tok, cost_for_usage(model, tok, 0)


def load_cfg(args):
    from assistant_axis.gapgen.metric_config import MetricConfig
    return MetricConfig.load(args.metric_config)


def embedder_for(cfg):
    from assistant_axis.gapgen import embed as EM
    live = cfg.live_model
    if live["arm"] != "openai":
        raise SystemExit(f"live model arm {live['arm']!r}: this scorer embeds with OpenAI (the config's live model)")
    return EM.OpenAIEmbedder(live["model_id"])


def cache_lookup(args, cfg, texts: list[str]):
    from assistant_axis.gapgen import embed as EM
    cache = EM.EmbeddingCache(root=args.cache_dir)
    emb = embedder_for(cfg)
    uniq = list(dict.fromkeys(texts))
    found, missing = cache.lookup(emb.tag, uniq)
    return cache, emb, [uniq[i] for i in missing]


def paid_gate(args, est_usd: float, *, paid: bool) -> Optional[dict]:
    """The dirty-tree check and the cost gate for a command that will call an API (``paid``); returns the dirty
    record, raises :class:`CostRefused` (exit 2)."""
    if not paid:
        return None
    refusal, record = dirty_refusal(platform_dirty_files(), args.allow_dirty)
    if refusal:
        raise CostRefused(refusal)
    confirm_or_abort(est_usd, args.budget_usd, confirm_expensive=args.confirm_expensive,
                     confirmed_by=args.confirmed_by)
    return record


def embed_all(args, cfg, texts: list[str], usage, *, canary: bool) -> np.ndarray:
    """Every text's unit embedding (cache misses embedded and charged; the canary first when anything is sent)."""
    from assistant_axis.gapgen import embed as EM
    cache, emb, missing = cache_lookup(args, cfg, texts)
    info = None
    if missing and canary and cfg.canary.get("texts"):
        info = EM.check_canary(emb, cfg.canary["texts"], cache, usage=usage,
                               min_cosine=cfg.canary.get("min_cosine", EM.CANARY_MIN_COSINE))
    E = EM.embed_texts(emb, texts, cache=cache, usage=usage) if texts else np.zeros((0, 0))
    args._canary = info
    args._n_embedded = len(missing)
    return E


def base_run(args, argv, cmd: str) -> dict:
    return {"command": cmd, "argv": list(argv), "git_sha": git_sha(), "started_at": utc_now(),
            "script": "data_analysis/gap_generation/persona_novelty.py"}


def finish_run(path: Path, run: dict, usage: MultiModelUsage, out_dir: Path) -> None:
    run = dict(run, finished_at=utc_now(), cost_usd=round(usage.total_cost_usd, 6), n_calls=usage.n_calls)
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    if prev is not None:
        sessions = prev.get("sessions") or [{k: v for k, v in prev.items() if k != "sessions"}]
        run = dict(prev, sessions=sessions + [run], last=run["command"], finished_at=run["finished_at"])
    atomic_write_text(json.dumps(run, indent=2, ensure_ascii=False, default=_default) + "\n", path)
    usage.write_json(out_dir / "usage.json")


def backup_dir(d: Path) -> Optional[Path]:
    if not d.exists():
        return None
    bak = d.with_name(f"{d.name}.bak.{utc_stamp()}")
    shutil.move(str(d), str(bak))
    return bak


def registry_rows(args) -> dict:
    if args.snapshot:
        return read_snapshot(snapshot_file(paths.DATA_CANDIDATES) if args.snapshot is True else args.snapshot)
    return Registry(args.registry).fold()


def load_pool(args) -> POOL.Pool:
    return POOL.load_pool(args.data_dir, args.vectors_dir, cache_dir=args.pool_cache_dir)


# --------------------------------------------------------------------------- fit

def gloss_check_rows(pool: POOL.Pool, path: Optional[Path]) -> list[tuple[int, str]]:
    """``[(position among the training rows, label: M1 gloss)]`` for the trained traits with an M1 gloss of their
    label (the M1 validation run's ``existing`` stratum)."""
    if path is None or not Path(path).exists():
        return []
    from assistant_axis.entity_id import entity_id
    pos = {pool.ids[i]: j for j, i in enumerate(pool.train_idx)}
    out = []
    for r in read_jsonl(path):
        if (r.get("meta") or {}).get("stratum") != "existing" or not r.get("gloss"):
            continue
        eid = entity_id(r["key"].split("#")[0], "traits")
        if eid in pos:
            out.append((pos[eid], NV.query_text(r["label"], r["gloss"], query_form="label_gloss")))
    return out


def cmd_fit(args, argv) -> int:
    cfg = load_cfg(args)
    out = PS.fit_dir(args.fit_id, args.out_root)
    pool = load_pool(args)
    counts = pool.counts()
    texts_all = POOL.corpus_texts(pool, args.data_dir)
    texts = [texts_all[i] for i in pool.train_idx]
    gl = gloss_check_rows(pool, args.gloss_check)
    cache, emb, missing = cache_lookup(args, cfg, texts)
    gl_found = cache.lookup(emb.tag, [t for _, t in gl])[0] if gl else {}
    tok, usd = embed_estimate(missing, emb.model_id)
    print(f"pool: {counts['n']} vectors ({counts['n_traits']} traits, {counts['n_roles']} roles), "
          f"{counts['n_with_file']} with a file, {counts['n_train']} train "
          f"({counts['n_train_traits']} + {counts['n_train_roles']}); shear applied: {pool.space.get('shear_applied')}")
    print(f"orphans: {counts['orphans']}\nsense-changed: {counts['sense_changed']}")
    print(f"corpus texts: {len(texts)}, {len(texts) - len(missing)} cached, {len(missing)} to embed "
          f"(about {tok:,} tokens, ${usd:.4f}); gloss check: {len(gl_found)} of {len(gl)} cached")
    if args.dry_run:
        print(f"[dry run] would write {repo_rel(out)}/ (cv.json, calibration.json, fit_report.md, fit_report.png, "
              f"model.npz, run.json, usage.json); nothing written")
        return 0
    if out.exists() and (out / "cv.json").exists() and not args.force:
        return rebuild_model(args, out, pool, cfg, texts)
    if out.exists() and args.force:
        bak = backup_dir(out)
        print(f"moved the earlier fit to {repo_rel(bak)}")
    dirty = paid_gate(args, usd, paid=bool(missing))
    out.mkdir(parents=True, exist_ok=True)
    usage = GuardedUsage(budget_usd=args.budget_usd, usage_path=out / "usage.json")
    run = base_run(args, argv, "fit") | {"fit_id": args.fit_id, "dirty_check": dirty}
    try:
        E = embed_all(args, cfg, texts, usage, canary=True)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        finish_run(out / "run.json", run | {"status": 2}, usage, out)
        return 2
    groups = POOL.fold_groups(pool, args.data_dir)[pool.train_idx]
    fcfg = FIT.FitConfig(alphas=tuple(args.alphas), n_folds=args.folds, Ns=tuple(args.Ns), knn_k=args.knn_k,
                         seed=args.seed)
    alt = [(p, t) for p, t in gl if cache.get(emb.tag, t) is not None]      # cached texts only: the check is free
    alt_rows = [p for p, _ in alt]
    E_alt = None
    if alt:
        from assistant_axis.gapgen import embed as EM
        E_alt = EM.normalize_rows(np.stack([cache.get(emb.tag, t) for _, t in alt]))
    cv = FIT.cross_validate(pool, E, groups, fcfg, E_alt=E_alt, alt_rows=alt_rows or None,
                            alt_name="m1_validation_r2, existing stratum")
    chosen = {"alpha": cv.alpha, "N": cv.N}
    if args.alpha is not None:
        if float(args.alpha) not in cv.summary:
            raise SystemExit(f"--alpha {args.alpha} is not one of the swept alphas {sorted(cv.summary)}")
        cv.alpha = float(args.alpha)
    if args.N is not None:
        if int(args.N) not in fcfg.Ns:
            raise SystemExit(f"--N {args.N} is not one of the swept Ns {list(fcfg.Ns)}")
        cv.N = int(args.N)
    set_by = args.thresholds_set_by or (CAL.PLAN_DEFAULT if args.dup_threshold is None and args.novel_pct is None
                                        and args.alpha is None and args.N is None else "operator (no --thresholds-set-by)")
    feature_source = {"embedding": emb.model_id, "cache_tag": emb.tag, "representation": POOL.REPRESENTATION,
                      "text": "label: description (traits: positive_label; roles: mechanical display form)",
                      "candidate_text": "label: gloss (novelty.query_text, query_form label_gloss)",
                      "kind_covariate": "a 0/1 role column"}
    cal = CAL.from_cv(cv, fit_id=args.fit_id, config_version=cfg.config_version, dup_threshold=args.dup_threshold,
                      novel_pct=args.novel_pct if args.novel_pct is not None else CAL.DEFAULT_NOVEL_PCT,
                      thresholds_set_by=set_by, feature_source=feature_source)
    model = FIT.fit_final(pool, E, cv.alpha, meta={"fit_id": args.fit_id, "config_version": cfg.config_version,
                                                   "N": cv.N, "feature_source": feature_source})
    FIT.save_model(model, out / PS.MODEL_FILE)
    inputs_payload = {"vectors": vectors_input(args.vectors_dir), "corpus": corpus_input(args.data_dir),
                      "embedding_cache": {"path": repo_rel(cache.path(emb.tag)), "tag": emb.tag,
                                          "n_texts": len(texts)},
                      "space": {k: pool.space.get(k) for k in ("slot", "layer", "shear_L", "shear_applied",
                                                               "mean_over", "n")},
                      "config_version": cfg.config_version, "chosen_by_rule": chosen}
    specs = file_specs(producer_script=Path(__file__), metric_config=args.metric_config,
                       pool_cache=Path(args.pool_cache_dir or paths.DATA_CANDIDATES / "cache") / "persona_s6_l25.npz")
    write_json(out / "cv.json", FIT.cv_record(cv, pool=pool, inputs=inputs_payload),
               title=f"persona-space fit {args.fit_id}: cross-validation", inputs=specs)
    write_json(out / "calibration.json", cal.as_dict(), title=f"persona-space fit {args.fit_id}: calibration",
               inputs=specs)
    title = f"Persona-space fit {args.fit_id}: held-out R² by PC and residual agreement by N"
    REP.fit_png(cv, cal, out / "fit_report.png", title=title, inputs=specs)
    atomic_write_text(REP.fit_report(cv, cal, fit_id=args.fit_id, pool_counts=counts) + "\n", out / "fit_report.md")
    run |= {"status": 0, "alpha": cv.alpha, "N": cv.N, "chosen_by_rule": chosen, "n_train": cv.n_rows,
            "n_groups": cv.n_groups, "dup_threshold": cal.dup_threshold, "novel_pct": cal.novel_pct,
            "thresholds_set_by": cal.thresholds_set_by, "config_version": cfg.config_version,
            "canary": getattr(args, "_canary", None), "n_embedded": getattr(args, "_n_embedded", 0),
            "model_sha256": hashlib.sha256((out / PS.MODEL_FILE).read_bytes()).hexdigest()}
    finish_run(out / "run.json", run, usage, out)
    s = cv.summary[cv.alpha]
    print(f"alpha {cv.alpha:g}, N {cv.N}: median cos {s['median_cos']:.3f}, top-1 {s['top1']:.3f}, "
          f"top-5 {s['top5']:.3f}, rho {s['rho_by_N'][str(cv.N)]:.3f}; dup_threshold {cal.dup_threshold:.3f}; "
          f"wrote {repo_rel(out)}/")
    return 0


def rebuild_model(args, out: Path, pool, cfg, texts) -> int:
    """An existing fit: rebuild ``model.npz`` (git-ignored) from the recorded alpha, after checking the training rows
    are the recorded ones; nothing else is written."""
    rec = read_env(out / "cv.json")
    cal = read_env(out / "calibration.json")
    if (out / PS.MODEL_FILE).exists() and not args.rebuild_model:
        print(f"{repo_rel(out)} exists with its model: nothing to do (--force refits into a new record, moving this "
              f"one to a .bak directory; --rebuild-model rewrites model.npz)")
        return 1
    if rec.get("n_rows") != len(pool.train_idx):
        raise SystemExit(f"the pool has {len(pool.train_idx)} training rows; the fit recorded {rec.get('n_rows')}: "
                         f"refit with --force")
    cache, emb, missing = cache_lookup(args, cfg, texts)
    if missing:
        raise SystemExit(f"rebuilding the model needs {len(missing)} embeddings that are not cached: refit with --force")
    from assistant_axis.gapgen import embed as EM
    E = EM.normalize_rows(np.stack([cache.get(emb.tag, t) for t in texts]))
    model = FIT.fit_final(pool, E, float(rec["alpha"]), meta={"fit_id": args.fit_id, "N": cal.get("N"),
                                                              "config_version": cal.get("config_version")})
    FIT.save_model(model, out / PS.MODEL_FILE)
    print(f"rebuilt {repo_rel(out / PS.MODEL_FILE)} (alpha {rec['alpha']}, {model.n_train} rows)")
    return 0


# --------------------------------------------------------------------------- score

def parse_run(value: str) -> tuple[str, str]:
    gen, sep, run_id = value.partition("/")
    if not sep:
        raise argparse.ArgumentTypeError("--run takes GENERATOR/RUN_ID")
    paths.check_id(gen, "generator")
    paths.check_id(run_id, "run_id")
    return gen, run_id


def select(args, rows):
    if args.keys_file:
        args.keys = [x.strip() for x in Path(args.keys_file).read_text().splitlines() if x.strip()]
    return SC.candidates(rows, run=args.run or None, keys=args.keys or None, all_rows=bool(args.all_rows),
                         holding=args.holding)


def cmd_score(args, argv) -> int:
    if sum(bool(x) for x in (args.run, args.keys or args.keys_file, args.all_rows)) != 1:
        raise SystemExit("give exactly one of --run, --keys / --keys-file, --all-rows")
    if args.write_registry and args.snapshot:
        raise SystemExit("--write-registry writes the live log; --snapshot is read-only")
    cfg = load_cfg(args)
    out = PS.score_dir(args.batch_id, args.out_root)
    rows = registry_rows(args)
    cands, skipped = select(args, rows)
    texts = SC.candidate_texts(cands)
    cache, emb, missing = cache_lookup(args, cfg, texts)
    tok, usd = embed_estimate(missing, emb.model_id)
    can_tok, can_usd = embed_estimate([c["text"] for c in cfg.canary.get("texts", [])], emb.model_id) \
        if missing else (0, 0.0)
    est = Estimate()
    est.add(f"embed {len(missing)} candidate texts (label: gloss, w20)", emb.model_id,
            1 if missing else 0, tok, 0)
    est.add("canary (8 texts, re-embedded first)", emb.model_id, 1 if missing else 0, can_tok, 0)
    print(f"{len(cands)} candidates ({dict(skipped)} left out); {len(texts) - len(missing)} texts cached, "
          f"{len(missing)} to embed\n{est.format()}")
    for t in texts[:3]:
        print(f"  text: {t}")
    if args.dry_run:
        mf = PS.fit_dir(args.fit_id, args.out_root) / PS.MODEL_FILE
        print(f"[dry run] fit {args.fit_id}: model {'present' if mf.exists() else 'MISSING (run fit first)'}; would "
              f"write {repo_rel(out)}/" + ("; and the persona block on each row of the live registry" if
                                            args.write_registry else "") + "; nothing written")
        return 0
    if out.exists() and not args.force:
        print(f"{repo_rel(out)} exists: a new --batch-id, or --force (moves it to a .bak directory)", file=sys.stderr)
        return 1
    fit = PS.load_fit(args.fit_id, out_root=args.out_root, data_dir=args.data_dir, vectors_dir=args.vectors_dir,
                      pool_cache_dir=args.pool_cache_dir)
    dirty = paid_gate(args, est.usd, paid=bool(missing))
    if out.exists():
        backup_dir(out)
    out.mkdir(parents=True)
    usage = GuardedUsage(budget_usd=args.budget_usd, usage_path=out / "usage.json")
    run = base_run(args, argv, "score") | {"batch_id": args.batch_id, "fit_id": args.fit_id, "dirty_check": dirty,
                                           "estimate_usd": round(est.usd, 6), "holding": args.holding,
                                           "selection": {"run": [f"{g}/{r}" for g, r in args.run or []],
                                                         "keys": len(args.keys or []), "all_rows": args.all_rows}}
    try:
        E = embed_all(args, cfg, texts, usage, canary=True)
    except BudgetExceededError as exc:
        print(f"STOPPED: {exc}", file=sys.stderr)
        finish_run(out / "run.json", run | {"status": 2}, usage, out)
        return 2
    rc = score_and_write(args, fit, cands, E, rows, out, run=run, usage=usage, cfg=cfg)
    return rc


def score_and_write(args, fit, cands, E, rows, out: Path, *, run: dict, usage, cfg) -> int:
    at = utc_now()
    P = FIT.predict(fit.model, E, ["traits"] * len(cands)) if len(cands) else np.zeros((0, 5120), np.float32)
    Ns = fit.Ns or (fit.calibration.N,)
    scores = SC.score_vectors(P, cands, fit.pool, fit.calibration, Ns=Ns, partners=fit.partners)
    srows = SC.score_rows(scores, P, rows, fit.pool, batch_id=args.batch_id, at=at)
    dis, counts = CMP.disagreements(srows, rows, fit.calibration, quantile=args.quantile)
    CMP.mark_rows(srows, dis)
    agr = CMP.agreement(srows, rows, dis)
    np.savez_compressed(out / "predictions.npz", keys=np.array([c.key for c in cands]), P=P.astype(np.float16))
    write_outputs(args, out, srows, dis, counts, agr, fit.calibration, readings=None)
    if args.write_registry:
        missing: list = []
        n = SC.apply_blocks(Registry(args.registry), srows, args.batch_id, missing=missing)
        run["registry"] = {"path": repo_rel(args.registry), "n_written": n, "n_missing": len(missing)}
        print(f"wrote the persona block on {n} rows of {repo_rel(args.registry)} ({len(missing)} keys not there)")
    run |= {"status": 0, "n_scored": len(srows), "config_version": cfg.config_version, "N": fit.calibration.N,
            "canary": getattr(args, "_canary", None), "n_embedded": getattr(args, "_n_embedded", 0),
            "flags": agr.flags, "disagreements": {k: v for k, v in counts.items()}}
    finish_run(out / "run.json", run, usage, out)
    print(f"scored {len(srows)}: flags {agr.flags}; AUC {agr.auc_nn_cos_covered_vs_new}; disagreements "
          f"{ {k: counts[k]['listed'] for k in SC.DISAGREEMENTS} }; wrote {repo_rel(out)}/")
    return 0


def write_outputs(args, out: Path, srows, dis, counts, agr, cal, *, readings) -> None:
    specs = file_specs(producer_script=Path(__file__), metric_config=args.metric_config)
    write_jsonl(out / "scores.jsonl", srows)
    write_jsonl(out / "disagreements.jsonl", [d.as_dict() for d in dis])
    summary = {"batch_id": args.batch_id, "fit_id": cal.fit_id, "N": cal.N, "n": len(srows), "flags": agr.flags,
               "disagreements": counts, "thresholds": {"dup_threshold": cal.dup_threshold, "novel_pct": cal.novel_pct,
                                                       "set_by": cal.thresholds_set_by},
               "by_generator": {g: {"n": v["n"], "flags": v["flags"]} for g, v in agr.by_generator.items()}}
    write_json(out / "summary.json", summary, title=f"persona-space scores {args.batch_id}: summary", inputs=specs)
    write_json(out / "agreement.json", agr.as_dict(), title=f"persona-space scores {args.batch_id}: agreement",
               inputs=specs)
    atomic_write_text(CMP.markdown(dis, counts, batch_id=args.batch_id, cal=cal, readings=readings) + "\n",
                      out / "disagreements.md")
    atomic_write_text(REP.score_report(srows, agr.as_dict(), counts, cal, batch_id=args.batch_id, readings=readings),
                      out / "score_report.md")


def batch_readings(out: Path) -> dict:
    """``{key: block reading}`` from ``readings.jsonl``."""
    return {r["key"]: JDG.block_reading(r) for r in read_jsonl(out / "readings.jsonl")}


def cmd_apply(args, argv) -> int:
    out = PS.score_dir(args.batch_id, args.out_root)
    srows = read_jsonl(out / "scores.jsonl")
    if not srows:
        raise SystemExit(f"{repo_rel(out)}/scores.jsonl is missing or empty")
    readings = batch_readings(out)
    if args.dry_run:
        print(f"[dry run] would apply {len(srows)} persona blocks ({len(readings)} with a reading) to "
              f"{repo_rel(args.registry)}; nothing written")
        return 0
    missing: list = []
    n = SC.apply_blocks(Registry(args.registry), srows, args.batch_id, readings=readings, missing=missing)
    print(f"applied: {n} rows written, {len(srows) - n - len(missing)} already current, {len(missing)} keys not in "
          f"{repo_rel(args.registry)}")
    return 0


def refresh_cover_cos(srows, rows, out: Path, pool) -> int:
    """Rows whose M3 covering trait changed since scoring: their cosine to the new one, from ``predictions.npz``."""
    p = out / "predictions.npz"
    if not p.exists():
        return 0
    from assistant_axis.entity_id import entity_id
    with np.load(p) as z:
        P = dict(zip([str(k) for k in z["keys"]], z["P"].astype(np.float64)))
    n = 0
    for s in srows:
        m = SC.m3_view(rows.get(s["key"]) or {})
        if m["covered_by"] and m["covered_by"] != s.get("m3_covered_by") and s["key"] in P:
            s["m3_covered_by"] = m["covered_by"]
            s["cos_to_covered_by"] = SC.cos_to(P[s["key"]], pool, entity_id(m["covered_by"], "traits"))
            n += 1
    return n


def cmd_compare(args, argv) -> int:
    out = PS.score_dir(args.batch_id, args.out_root)
    srows = read_jsonl(out / "scores.jsonl")
    if not srows:
        raise SystemExit(f"{repo_rel(out)}/scores.jsonl is missing or empty")
    fit_id = srows[0]["fit_id"]
    cal = CAL.Calibration.from_dict(read_env(PS.fit_dir(fit_id, args.out_root) / "calibration.json"))
    rows = registry_rows(args)
    if args.dry_run:
        print(f"[dry run] would recompute the agreement and disagreements of {len(srows)} rows; nothing written")
        return 0
    try:
        pool = load_pool(args)
        n = refresh_cover_cos(srows, rows, out, pool)
    except FileNotFoundError:
        n = 0
    dis, counts = CMP.disagreements(srows, rows, cal, quantile=args.quantile)
    CMP.mark_rows(srows, dis)
    agr = CMP.agreement(srows, rows, dis)
    write_outputs(args, out, srows, dis, counts, agr, cal, readings=batch_readings(out) or None)
    print(f"compared {len(srows)} rows ({n} covering traits refreshed): AUC {agr.auc_nn_cos_covered_vs_new}, "
          f"covered_by is nearest {agr.covered_by_is_nearest}; disagreements "
          f"{ {k: counts[k]['listed'] for k in SC.DISAGREEMENTS} }")
    return 0


def cmd_report(args, argv) -> int:
    out = PS.score_dir(args.batch_id, args.out_root)
    srows = read_jsonl(out / "scores.jsonl")
    if not srows:
        raise SystemExit(f"{repo_rel(out)}/scores.jsonl is missing or empty")
    cal = CAL.Calibration.from_dict(read_env(PS.fit_dir(srows[0]["fit_id"], args.out_root) / "calibration.json"))
    agr = read_env(out / "agreement.json")
    counts = read_env(out / "summary.json").get("disagreements") or {}
    readings = batch_readings(out)
    text = REP.score_report(srows, agr, counts, cal, batch_id=args.batch_id, readings=readings or None)
    if args.dry_run:
        print(text[:2000])
        return 0
    atomic_write_text(text, out / "score_report.md")
    print(f"wrote {repo_rel(out / 'score_report.md')}")
    return 0


# --------------------------------------------------------------------------- judge-disagreements (decision 2b)

def light_index(data_dir: Path) -> NV.CorpusIndex:
    """The corpus traits for the overlap call's "other" side (labels, descriptions, partners); no embedding is
    needed to read a pair whole."""
    traits = NV.load_trait_corpus(Path(data_dir))
    stems = sorted(traits)
    return NV.CorpusIndex(stems=stems, Z=np.zeros((len(stems), 1)), transform=None, traits=traits,
                          settings={"note": "persona_novelty: corpus descriptions only"})


def make_runner(args, out: Path, usage, *, client=None, records=()) -> NR.NoveltyRunner:
    from data_analysis.gap_generation import novelty_score as NS
    rubrics = NS.load_m3_rubrics(args.rubrics_dir)
    if client is None:
        import anthropic
        from dotenv import load_dotenv
        load_dotenv(_REPO_ROOT / ".env")
        client = anthropic.AsyncAnthropic(max_retries=0)
    idx = light_index(args.data_dir)
    sets = NV.label_sets(idx.traits, {"entries": []})
    return NR.NoveltyRunner(client=client, batch_id=f"persona_{args.batch_id}", rubrics=rubrics, index=idx,
                            label_sets=sets, usage=usage, responses_path=out / "responses.jsonl", k=10,
                            mode="shortlist", config_version="", concurrency=args.concurrency,
                            resume_records=records, rules=NV.DEFAULT_RULES)


def judge_inputs(args, out: Path):
    dis = read_jsonl(out / "disagreements.jsonl")
    pl = JDG.pairs(dis, kind=args.kind)[:args.max_pairs]
    run = json.loads((out / "run.json").read_text(encoding="utf-8")) if (out / "run.json").exists() else {}
    holding = run.get("holding")
    rows = registry_rows(args)
    cands, missing = [], []
    for key, _, _ in pl:
        r = rows.get(key)
        c, why = (NR.candidate_from_row(r, holding=holding) if holding else NR.candidate_from_row(r)) if r else \
            (None, "not in the registry")
        if c is None:
            missing.append((key, why))
        else:
            cands.append(c)
    keep = {c.key for c in cands}
    return [p for p in pl if p[0] in keep], cands, missing


def cmd_judge(args, argv, *, client=None) -> int:
    out = PS.score_dir(args.batch_id, args.out_root)
    if not (out / "disagreements.jsonl").exists():
        raise SystemExit(f"{repo_rel(out)}/disagreements.jsonl is missing: run score first")
    if args.write_registry and args.snapshot:
        raise SystemExit("--write-registry writes the live log; --snapshot is read-only")
    pl, cands, missing = judge_inputs(args, out)
    est = JDG.estimate(len(pl))
    proj = est.usd * ESTIMATE_CALIBRATION
    print(f"{len(pl)} {args.kind} pairs to read ({len(missing)} rows left out: {missing[:5]})\n{est.format()}\n"
          f"  projected spend (x{ESTIMATE_CALIBRATION}, the harness's measured factor) = ${proj:.3f}")
    records = read_jsonl(out / "responses.jsonl") if args.resume else []
    if (out / "responses.jsonl").exists() and not args.resume and not args.dry_run:
        print(f"{repo_rel(out)}/responses.jsonl exists: --resume to continue (no call already answered is sent again)",
              file=sys.stderr)
        return 1
    earlier = MultiModelUsage.load_or_create(out / "usage.json")
    usage = GuardedUsage(budget_usd=args.budget_usd + earlier.total_cost_usd,
                         usage_path=None if args.dry_run else out / "usage.json")
    usage.merge_from(earlier)
    runner = make_runner(args, out, usage, client=client if client is not None else (_NoClient() if args.dry_run
                                                                                      else None), records=records)
    if pl:
        by = {c.key: c for c in cands}
        req = JDG.render(runner, by[pl[0][0]], pl[0][1])
        print("\nrendered prompt of the first pair (as the model receives it):\n[system]\n"
              f"{req['system'][0]['text']}\n\n[user]\n{req['messages'][0]['content']}\n"
              f"[request] model {req['model']}, max_tokens {req['max_tokens']}, temperature "
              f"{req.get('temperature', 'not sent')}, system cached: {'cache_control' in req['system'][0]}")
    if args.dry_run:
        print("[dry run] nothing sent, nothing written")
        return 0
    paid_gate(args, proj, paid=bool(pl))
    run = base_run(args, argv, "judge-disagreements") | {"batch_id": args.batch_id, "kind": args.kind,
                                                         "n_pairs": len(pl), "estimate_usd": round(est.usd, 6),
                                                         "projected_usd": round(proj, 6),
                                                         "rubrics": runner.rubric_pins, "rules": NV.DEFAULT_RULES.name,
                                                         "models": [NR.FIRST_MODEL, NR.SECOND_MODEL],
                                                         "label_form": runner.label_form}
    status = 0
    readings = {}
    try:
        readings = JDG.read_pairs(runner, cands, pl, wave="p")
    except BudgetExceededError as exc:
        print(f"STOPPED (budget): {exc}; every answer is recorded, --resume continues", file=sys.stderr)
        status = 2
    finally:
        usage.write_json(out / "usage.json")
    summ = JDG.summarise(readings, cands, rules=NV.DEFAULT_RULES, records=runner.records)
    rates = runner.warn_parse_rates(logger)
    n_ref = sum(1 for r in runner.records if r.get("stop_reason") == "refusal")
    if n_ref:
        logger.warning("%d responses were refusals (stop_reason refusal): counted as failed calls", n_ref)
    rows_out = [{"key": k, **v} for k, v in sorted(summ.items())]
    write_jsonl(out / "readings.jsonl", rows_out)
    if args.write_registry and status == 0:
        srows = [r for r in read_jsonl(out / "scores.jsonl") if r["key"] in summ]
        n = SC.apply_blocks(Registry(args.registry), srows, args.batch_id,
                            readings={k: JDG.block_reading(v) for k, v in summ.items()})
        run["registry"] = {"path": repo_rel(args.registry), "n_written": n}
    at = sum(1 for v in summ.values() if v["at_cut_off"])
    run |= {"status": status, "n_read": len(summ), "n_at_cut_off": at, "n_refused_responses": n_ref,
            "parse_rates": rates, "verdicts": _count(v["verdict"] for v in summ.values())}
    finish_run(out / "run.json", run, usage, out)
    # the disagreement list and the report again, with the readings
    srows = read_jsonl(out / "scores.jsonl")
    fit_id = srows[0]["fit_id"] if srows else None
    if fit_id:
        cal = CAL.Calibration.from_dict(read_env(PS.fit_dir(fit_id, args.out_root) / "calibration.json"))
        dis = [CMP.Disagreement(**d) for d in read_jsonl(out / "disagreements.jsonl")]
        counts = read_env(out / "summary.json").get("disagreements") or {}
        atomic_write_text(CMP.markdown(dis, counts, batch_id=args.batch_id, cal=cal, readings=summ) + "\n",
                          out / "disagreements.md")
    print(f"read {len(summ)} pairs: {at} at or above the candidate's cut-off; {n_ref} refusals; "
          f"${usage.total_cost_usd - earlier.total_cost_usd:.4f} spent; wrote {repo_rel(out / 'readings.jsonl')}")
    return status


def _count(xs) -> dict:
    from collections import Counter
    return dict(Counter(xs))


class _NoClient:
    """The dry run's client: any call is an error (nothing is ever sent)."""
    class messages:  # noqa: N801
        @staticmethod
        async def create(**kw):
            raise RuntimeError("the dry run sends nothing")


# --------------------------------------------------------------------------- prospective

def cmd_prospective_predict(args, argv) -> int:
    cfg = load_cfg(args)
    out = PS.prospective_dir(args.fit_id, args.out_root)
    fdir = PS.fit_dir(args.fit_id, args.out_root)
    pool = load_pool(args)
    ents = PRO.pending(pool, args.data_dir)
    texts = PRO.pending_texts(ents, args.data_dir)
    cache, emb, missing = cache_lookup(args, cfg, texts)
    tok, usd = embed_estimate(missing, emb.model_id)
    k = _count(kd for kd, _ in ents)
    print(f"{len(ents)} pending entities ({k}); {len(texts) - len(missing)} texts cached, {len(missing)} to embed "
          f"(about {tok:,} tokens, ${usd:.4f})")
    if args.dry_run:
        print(f"[dry run] fit {args.fit_id}: model "
              f"{'present' if (fdir / PS.MODEL_FILE).exists() else 'MISSING (run fit first)'}; would write "
              f"{repo_rel(out)}/; nothing written")
        return 0
    if (out / "predicted.jsonl").exists() and not args.force:
        print(f"{repo_rel(out)}/predicted.jsonl exists: --force moves the directory to a .bak first", file=sys.stderr)
        return 1
    fit = PS.load_fit(args.fit_id, out_root=args.out_root, data_dir=args.data_dir, vectors_dir=args.vectors_dir,
                      pool_cache_dir=args.pool_cache_dir)
    dirty = paid_gate(args, usd, paid=bool(missing))
    if out.exists():
        backup_dir(out)
    out.mkdir(parents=True)
    usage = GuardedUsage(budget_usd=args.budget_usd, usage_path=out / "usage.json")
    run = base_run(args, argv, "prospective predict") | {"fit_id": args.fit_id, "dirty_check": dirty}
    E = embed_all(args, cfg, texts, usage, canary=True)
    rows, P = PRO.predict_pending(fit.model, fit.calibration, fit.pool, E, ents, Ns=fit.Ns, partners=fit.partners,
                                  fit_id=args.fit_id, config_version=fit.calibration.config_version)
    write_jsonl(out / "predicted.jsonl", rows)
    np.savez_compressed(out / "predictions.npz", ids=np.array([r["id"] for r in rows]), P=P.astype(np.float16))
    cmd = compare_command(args)
    atomic_write_text(REP.prospective_report(rows, fit_id=args.fit_id, compare_cmd=cmd), out / "prospective_report.md")
    run |= {"status": 0, "n": len(rows), "by_kind": k, "flags": _count(r["flag"] for r in rows),
            "n_embedded": getattr(args, "_n_embedded", 0), "compare_command": cmd}
    finish_run(out / "run.json", run, usage, out)
    print(f"predicted {len(rows)}: flags {run['flags']}; wrote {repo_rel(out)}/")
    return 0


def compare_command(args) -> str:
    return ("uv run python data_analysis/gap_generation/persona_novelty.py prospective compare "
            f"--fit-id {args.fit_id} --new-vectors-dir '<the new extraction's model directory, holding "
            "traits/vectors and roles/vectors>'")


def cmd_prospective_compare(args, argv) -> int:
    out = PS.prospective_dir(args.fit_id, args.out_root)
    rows = read_jsonl(out / "predicted.jsonl")
    if not rows:
        raise SystemExit(f"{repo_rel(out)}/predicted.jsonl is missing: run `prospective predict` first")
    cal = CAL.Calibration.from_dict(read_env(PS.fit_dir(args.fit_id, args.out_root) / "calibration.json"))
    N = int(args.N or cal.N)
    tree = args.tree_name or Path(args.new_vectors_dir).name.replace(" ", "_")
    if args.dry_run:
        print(f"[dry run] would compare {len(rows)} predictions with {args.new_vectors_dir} at N = {N}; would write "
              f"compare_{tree}.json / .md; nothing written")
        return 0
    preds = {}
    if (out / "predictions.npz").exists():
        with np.load(out / "predictions.npz") as z:
            preds = dict(zip([str(i) for i in z["ids"]], z["P"].astype(np.float64)))
    old = load_pool(args)
    old_vecs = {old.ids[i]: old.M[i] for i in old.train_idx}
    comp = PRO.compare(rows, Path(args.new_vectors_dir), data_dir=args.data_dir, N=N, cache_dir=args.new_cache_dir,
                       predictions=preds, old_vectors=old_vecs, known_ids=old.train_ids)
    comp["tree"] = repo_rel(Path(args.new_vectors_dir))
    write_json(out / f"compare_{tree}.json", comp, title=f"persona-space prospective comparison {args.fit_id} / {tree}",
               inputs=file_specs(producer_script=Path(__file__)))
    atomic_write_text(REP.prospective_report(rows, fit_id=args.fit_id, compare_cmd=compare_command(args),
                                             comparison=comp), out / f"compare_{tree}.md")
    print(f"compared: {comp['n_with_vector']} of {comp['n']} have a new vector; rho {comp['rho_residual_rank']}, "
          f"top-1 {comp['top1_name_hit']}, top-3 {comp['top3_name_hit']}")
    return 0


# --------------------------------------------------------------------------- CLI

def _common(ap: argparse.ArgumentParser, *, budget: float = 1.0) -> None:
    ap.add_argument("--data-dir", type=Path, default=paths.DATA_DIR)
    ap.add_argument("--vectors-dir", type=Path, default=DEFAULT_VECTORS_DIR)
    ap.add_argument("--pool-cache-dir", type=Path, default=None,
                    help="where persona_s6_l25.npz is (default data/candidates/cache)")
    ap.add_argument("--registry", type=Path, default=paths.REGISTRY_PATH)
    ap.add_argument("--snapshot", nargs="?", const=True, default=None, type=Path,
                    help="read the tracked snapshot (or this file) instead of the live log; read-only")
    ap.add_argument("--out-root", type=Path, default=None, help="default data/candidates/persona")
    ap.add_argument("--cache-dir", type=Path, default=paths.EMBEDDING_CACHE_DIR)
    ap.add_argument("--metric-config", type=Path, default=paths.METRIC_CONFIG_PATH)
    ap.add_argument("--rubrics-dir", type=Path, default=None)
    ap.add_argument("--budget-usd", type=float, default=budget)
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--dry-run", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("fit", help="cross-validate, choose alpha and N, fit, calibrate ($0 with the cache)")
    _common(sp)
    sp.add_argument("--fit-id", required=True)
    sp.add_argument("--alphas", type=float, nargs="+", default=list(FIT.FitConfig.alphas))
    sp.add_argument("--folds", type=int, default=FIT.FitConfig.n_folds)
    sp.add_argument("--Ns", type=int, nargs="+", default=list(FIT.FitConfig.Ns))
    sp.add_argument("--knn-k", type=int, default=FIT.FitConfig.knn_k)
    sp.add_argument("--seed", type=int, default=0)
    sp.add_argument("--alpha", type=float, default=None, help="override the rule's alpha (one of --alphas)")
    sp.add_argument("--N", type=int, default=None, help="override the rule's N (one of --Ns)")
    sp.add_argument("--dup-threshold", type=float, default=None, help="default the median held-out self-cosine")
    sp.add_argument("--novel-pct", type=float, default=None, help=f"default {CAL.DEFAULT_NOVEL_PCT}")
    sp.add_argument("--thresholds-set-by", default=None, help="who moved alpha, N or the thresholds (recorded)")
    sp.add_argument("--gloss-check", type=Path, default=M1_GLOSS_CHECK,
                    help="M1 validation results whose existing stratum gives the gloss-side check (cached texts only)")
    sp.add_argument("--force", action="store_true", help="refit into a new record (the old directory to .bak)")
    sp.add_argument("--rebuild-model", action="store_true", help="rewrite model.npz of an existing fit")
    sp.set_defaults(func=cmd_fit)

    sp = sub.add_parser("score", help="score registry candidates (embedding: about $0.035 for every trait row)")
    _common(sp)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--fit-id", required=True)
    sp.add_argument("--run", type=parse_run, action="append")
    sp.add_argument("--keys", nargs="+")
    sp.add_argument("--keys-file", type=Path)
    sp.add_argument("--all-rows", action="store_true")
    sp.add_argument("--holding", choices=("states", "physical"), default=None)
    sp.add_argument("--write-registry", action="store_true")
    sp.add_argument("--quantile", type=float, default=0.10)
    sp.add_argument("--force", action="store_true")
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("apply", help="apply a recorded batch's blocks to this checkout's registry ($0)")
    _common(sp)
    sp.add_argument("--batch-id", required=True)
    sp.set_defaults(func=cmd_apply)

    sp = sub.add_parser("compare", help="agreement and disagreements again, against M3 now ($0)")
    _common(sp)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--quantile", type=float, default=0.10)
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("judge-disagreements", help="decision 2b: M3's overlap call on the disagreements (live)")
    _common(sp, budget=5.0)
    sp.add_argument("--batch-id", required=True)
    sp.add_argument("--kind", default="dup_vs_new", choices=SC.DISAGREEMENTS)
    sp.add_argument("--max-pairs", type=int, default=700)
    sp.add_argument("--resume", action="store_true")
    sp.add_argument("--write-registry", action="store_true")
    sp.add_argument("--concurrency", type=int, default=NR.DEFAULT_CONCURRENCY)
    sp.set_defaults(func=cmd_judge)

    sp = sub.add_parser("prospective", help="the entities with no vector yet: predict now, compare later")
    psub = sp.add_subparsers(dest="pcmd", required=True)
    pp = psub.add_parser("predict")
    _common(pp)
    pp.add_argument("--fit-id", required=True)
    pp.add_argument("--force", action="store_true")
    pp.set_defaults(func=cmd_prospective_predict)
    pc = psub.add_parser("compare")
    _common(pc)
    pc.add_argument("--fit-id", required=True)
    pc.add_argument("--new-vectors-dir", type=Path, required=True)
    pc.add_argument("--N", type=int, default=None)
    pc.add_argument("--tree-name", default=None)
    pc.add_argument("--new-cache-dir", type=Path, default=None,
                    help="the new tree's slice cache (default data/candidates/cache/persona_prospective/<hash>)")
    pc.set_defaults(func=cmd_prospective_compare)

    sp = sub.add_parser("report", help="score_report.md again")
    _common(sp)
    sp.add_argument("--batch-id", required=True)
    sp.set_defaults(func=cmd_report)
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    configure_logging()
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args, argv) or 0)
    except CostRefused:
        return 2


if __name__ == "__main__":
    sys.exit(main())
