#!/usr/bin/env python3
"""M2 metric calibration on the existing corpus (plan 15; coding_plan_platform.md §7, §9 tasks 16-18).

    uv run python data_analysis/gap_generation/calibrate_metric.py --skip-llm [--models openai bge gemma]
        [--representations full noprefix w20 w14 strip] [--variants raw centred centred_pc1 centred_pc3 zca]
        [--vectors-dir 'runpod_workspace/qwen/qwen-3-32b Roger 8slot'] [--out data/candidates/calibration]
        [--budget-usd 1.0] [--rebuild-labels] [--dry-run] [--allow-dirty]

Embeds every trait as ``label: description`` under each representation and
model (OpenAI ``text-embedding-3-large``; local ``BAAI/bge-large-en-v1.5`` and
``google/embeddinggemma-300m``), plus the labelled pairs' external members
(rejected queue entries), the minimal pairs of criterion (f) and each trait's
M1 filter gloss; fits every space variant; and writes, under ``--out``:

* ``loo_metrics.json``: one row per model x representation x variant x metric
  with tasks (a) (b) (c), plus the gloss-recovery rows;
* ``hubness.json``, ``thresholds.json``, ``contrast_ablation.json``;
* ``nn_hist_<model>.png`` (one per model; read back and inspected);
* ``drop_or_merge.md`` (step 8's table);
* ``contrast_comparisons_key.json`` and, for Roger,
  ``reports/trait_gap_generation/contrast_comparisons_for_marks.md``;
* ``summary.json`` (the headline numbers and the provisional recommendations),
  ``run.json`` and ``usage.json`` (written after every stage).

``--skip-llm`` (the pilot) runs everything that needs no LLM; without it the
Haiku paraphrases (criteria g, i; cached in ``paraphrases.json``) and the
Sonnet blinded judgement (criterion e) run too, under the cost gate.
``--write-config`` (``metric_config.json``) is task 19 and waits for Roger's
decisions on the pilot.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis.gapgen import calibrate as C  # noqa: E402
from assistant_axis.gapgen import calibrate_llm as CL  # noqa: E402
from assistant_axis.gapgen import contrast as CT  # noqa: E402
from assistant_axis.gapgen import embed as EM  # noqa: E402
from assistant_axis.gapgen import labels as LB  # noqa: E402
from assistant_axis.gapgen import persona as PS  # noqa: E402
from assistant_axis.gapgen.cost import Estimate, GuardedUsage, confirm_or_abort  # noqa: E402
from assistant_axis.gapgen.paths import CALIBRATION_DIR, EMBEDDING_CACHE_DIR  # noqa: E402
from assistant_axis.gapgen.registry import utc_now  # noqa: E402
from assistant_axis.gapgen.representation import REPRESENTATIONS, represent  # noqa: E402
from assistant_axis.gapgen.runs import PLATFORM_PATHS, configure_logging, git_sha, platform_dirty_files  # noqa: E402
from assistant_axis.gapgen.space import VARIANTS, k_for_variance, loo_residuals  # noqa: E402

logger = logging.getLogger("calibrate_metric")

ARMS = ("openai", "bge", "gemma")
OPENAI_BATCH = 256
CHARS_PER_TOKEN = 4.0
MARKS_SHEET = _REPO_ROOT / "reports" / "trait_gap_generation" / "contrast_comparisons_for_marks.md"
NOVELTY_METRICS = ("cos", "csls", "knn5", "resid_K95", "resid_10", "resid_20", "resid_40")
PERSONA_KS = (10, 20, 37, 40)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=list(ARMS), choices=list(ARMS) + ["hash"])
    ap.add_argument("--representations", nargs="+", default=list(REPRESENTATIONS), choices=list(REPRESENTATIONS))
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    ap.add_argument("--skip-llm", action="store_true", help="no Haiku paraphrases, no Sonnet judge (the pilot)")
    ap.add_argument("--criteria", default="a,b,c,d,e,f,g,h,i,j", help="contrast-ablation criteria to report")
    ap.add_argument("--paraphrase-cache", type=Path, default=None, help="default: <out>/paraphrases.json")
    ap.add_argument("--vectors-dir", type=Path, default=PS.DEFAULT_VECTORS_DIR)
    ap.add_argument("--out", type=Path, default=CALIBRATION_DIR)
    ap.add_argument("--marks-sheet", type=Path, default=MARKS_SHEET)
    ap.add_argument("--cache-dir", type=Path, default=EMBEDDING_CACHE_DIR, help="embedding cache (gitignored)")
    ap.add_argument("--budget-usd", type=float, default=None, help="hard cap (default 1.0 with --skip-llm, else 5.0)")
    ap.add_argument("--confirm-expensive", action="store_true")
    ap.add_argument("--confirmed-by", default=None)
    ap.add_argument("--rebuild-labels", action="store_true", help="rebuild labelled_pairs.json from the curation file")
    ap.add_argument("--no-residual", action="store_true", help="skip the leave-one-out residual (fast runs)")
    ap.add_argument("--write-config", action="store_true", help="task 19 (after Roger's pilot decision)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, the estimate and three texts; call nothing")
    ap.add_argument("--allow-dirty", action="store_true", help="run with uncommitted platform changes (recorded)")
    return ap.parse_args(argv)


# --------------------------------------------------------------------------- inputs

def corpus_inputs(repo: Path) -> dict:
    from assistant_axis.arrangements import load_corpus_arrangements
    corpus = CT.load_corpus_texts(repo / "data")
    stems = sorted(corpus)
    recs = load_corpus_arrangements(repo / "data", "traits")
    arrangement_of = defaultdict(list)
    partner = {}
    for s, r in recs.items():
        for a in r.arrangements:
            if a.kind == "singleton":
                continue
            arrangement_of[s].append((a.kind, tuple(a.members)))
            if a.kind == "pair" and len(a.members) == 2:
                partner[s] = a.members[0] if a.members[1] == s else a.members[1]
    return {"corpus": corpus, "stems": stems, "labels": [corpus[s]["label"] for s in stems],
            "descriptions": [corpus[s]["description"] for s in stems], "index": {s: i for i, s in enumerate(stems)},
            "arrangement_of": dict(arrangement_of), "partner": partner}


def build_texts(ci: dict, lp, cuts: dict, reps, minimal, glosses: dict, paraphrases: dict) -> dict:
    """Every text an arm embeds, by role: corpus[rep] (row order), ext[rep][member],
    minimal[text], gloss[rep][stem], para[stem]."""
    out = {"corpus": {}, "ext": {}, "gloss": {}, "minimal": {}, "para": {}}
    for rep in reps:
        out["corpus"][rep] = [represent(l, d, rep, cut=cuts.get(s) if rep == "strip" else None)
                              for s, l, d in zip(ci["stems"], ci["labels"], ci["descriptions"])]
        out["ext"][rep] = {m: represent(e["label"], e.get("description"), rep) for m, e in lp.externals.items()}
        out["gloss"][rep] = {s: represent(ci["corpus"][s]["label"], g, rep) for s, g in glosses.items()
                             if s in ci["index"]}
    for m in minimal:
        for k in ("xy", "yx", "x_only", "y_only"):
            out["minimal"][m[k]] = m[k]
    for s, p in paraphrases.items():
        if s in ci["index"]:
            out["para"][s] = f"{ci['corpus'][s]['label']}: {p}"
    return out


def all_texts(texts: dict) -> list[str]:
    seen = []
    for rep_rows in texts["corpus"].values():
        seen.extend(rep_rows)
    for d in list(texts["ext"].values()) + list(texts["gloss"].values()):
        seen.extend(d.values())
    seen.extend(texts["minimal"].values())
    seen.extend(texts["para"].values())
    return list(dict.fromkeys(seen))


def embedding_estimate(models, n_texts_uncached: dict, avg_tokens: float) -> Estimate:
    est = Estimate()
    if "openai" in models:
        n = n_texts_uncached.get("openai", 0)
        calls = math.ceil(n / OPENAI_BATCH)
        if calls:
            est.add("openai embeddings (uncached texts)", EM.OPENAI_MODEL, calls,
                    int(avg_tokens * min(n, OPENAI_BATCH)), 0)
    return est


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    args = parse_args(argv)
    configure_logging()
    if args.write_config:
        print("--write-config is task 19: it waits for Roger's decisions on the M2 pilot", file=sys.stderr)
        return 2
    repo = _REPO_ROOT
    out = Path(args.out)
    budget = args.budget_usd if args.budget_usd is not None else (1.0 if args.skip_llm else 5.0)
    t0 = time.time()
    timings = {}

    # labels and cuts (no API)
    lp_path = out / LB.LABELLED_PAIRS_NAME
    lp = LB.build_default(repo, out_dir=out, write=not args.dry_run) if (args.rebuild_labels or not lp_path.exists()) \
        else LB.load(lp_path)
    cuts_payload = CT.build_default(repo, out_dir=out, write=not args.dry_run)
    cut_rows = {**cuts_payload["census_107"], **cuts_payload["new_hits"]}
    classes = {s: r["class"] for s, r in cut_rows.items() if r["cuts"]}
    ci = corpus_inputs(repo)
    minimal = CT.minimal_pairs([tuple(sorted((a, ci["partner"][a]))) for a in ci["partner"]],
                               {s: ci["corpus"][s]["label"] for s in ci["stems"]}, n=40, seed=0)
    glosses = LB.load_filter_glosses(repo / LB.DEFAULT_FILTER_RESULTS, strata=("existing",))
    para_path = args.paraphrase_cache or out / "paraphrases.json"
    paraphrases = json.loads(para_path.read_text()).get("paraphrases", {}) if para_path.exists() else {}
    texts = build_texts(ci, lp, cut_rows, args.representations, minimal, glosses, paraphrases)
    every = all_texts(texts)
    avg_tok = float(np.mean([len(t) for t in every])) / CHARS_PER_TOKEN
    cache = EM.EmbeddingCache(args.cache_dir)
    uncached = {}
    for arm in args.models:
        tag = EM.make_embedder(arm).tag
        uncached[arm] = len(cache.lookup(tag, every)[1])
    est = embedding_estimate(args.models, uncached, avg_tok)
    llm_items = [s for s in ci["stems"] if s not in paraphrases]
    if not args.skip_llm:
        for line in CL.llm_estimate(len(llm_items), 60).lines:
            est.lines.append(line)
    print(f"M2 calibration: {len(ci['stems'])} traits; models {args.models}; representations {args.representations}; "
          f"variants {args.variants}; {len(every)} distinct texts (about {avg_tok:.0f} tokens each); "
          f"uncached per model {uncached}; labelled pairs {lp.counts()}; contrast rows {len(classes)} "
          f"({cuts_payload['counts']['by_class']} census + {len(cuts_payload['new_hits'])} new hits)")
    print(f"cost estimate:\n{est.format()}\n  budget ${budget:.2f}; LLM criteria {'skipped (--skip-llm)' if args.skip_llm else 'on'}")
    cap = confirm_or_abort(est.usd, budget, confirm_expensive=args.confirm_expensive, confirmed_by=args.confirmed_by)
    if args.dry_run:
        for t in every[:3]:
            print(f"  text: {t}")
        print("DRY-RUN: nothing embedded, nothing written")
        return 0
    dirty = platform_dirty_files()
    if dirty and not args.allow_dirty:
        print(f"REFUSED: uncommitted changes to the platform's code ({len(dirty)}: {'; '.join(d.strip() for d in dirty[:5])}); "
              f"commit first, or pass --allow-dirty", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    # usage.json is cumulative over runs (a rerun from the cache must not erase what an earlier run paid);
    # this run's own usage goes into run.json, and the cap applies to this run.
    from assistant_axis.judge_pricing import MultiModelUsage
    prior = MultiModelUsage.load_or_create(out / "usage.json")
    usage = GuardedUsage(budget_usd=cap)

    def write_usage():
        total = MultiModelUsage()
        total.merge_from(prior)
        total.merge_from(usage)
        total.write_json(out / "usage.json")
        return total
    write_usage()
    run = {"started_at": utc_now(), "git_sha": git_sha(), "argv": sys.argv[1:] if argv is None else argv,
           "allow_dirty": bool(args.allow_dirty), "dirty_check": {"paths": list(PLATFORM_PATHS), "dirty": dirty},
           "estimate_usd": round(est.usd, 4), "budget_usd": cap, "models_requested": args.models,
           "models_run": [], "models_failed": {}, "timings_s": timings}

    def save_run():
        run["cost_usd"] = round(usage.total_cost_usd, 6)
        run["usage_this_run"] = usage.as_dict()
        run["cost_usd_cumulative"] = round(write_usage().total_cost_usd, 6)
        (out / "run.json").write_text(json.dumps(run, indent=2) + "\n")

    # ---------------------------------------------------------------- embeddings
    emb = {}
    for arm in args.models:
        ts = time.time()
        try:
            embedder = EM.make_embedder(arm)
            vec = dict(zip(every, EM.embed_texts(embedder, every, cache=cache, usage=usage)))
            emb[arm] = vec
            run["models_run"].append(arm)
            logger.info("[%s] embedded %d texts in %.0fs; %s", arm, len(every), time.time() - ts, usage.log_line())
        except Exception as exc:  # noqa: BLE001 - one arm failing must not lose the others
            if type(exc).__name__ == "BudgetExceededError":   # GuardedUsage raised at the cap
                save_run()
                raise
            run["models_failed"][arm] = f"{type(exc).__name__}: {exc}"
            logger.error("[%s] failed: %s; continuing without it", arm, exc)
        timings[f"embed_{arm}"] = round(time.time() - ts, 1)
        save_run()
    arms = run["models_run"]
    if not arms:
        print("no model could embed; nothing to calibrate", file=sys.stderr)
        return 1

    # ---------------------------------------------------------------- persona yields
    ts = time.time()
    persona = None
    persona_yields = {}
    persona_info = {}
    try:
        ps = PS.load_persona_space(args.vectors_dir)
        pool_k95 = k_for_variance(ps["M"], 0.95)
        res = loo_residuals(ps["M"], sorted(set(PERSONA_KS) | {pool_k95}))
        trait_rows = [i for i, k in enumerate(ps["kinds"]) if k == "traits"]
        for K, arr in res.items():
            persona_yields[K] = {ps["stems"][i]: float(arr[i]) for i in trait_rows if ps["stems"][i] in ci["index"]}
        persona = {"stems": [ps["stems"][i] for i in trait_rows], "M": ps["M"][trait_rows]}
        brackets = PS.parse_bracket_scores(repo / "data" / "traits" / "instructions" / "TRAITS_TO_ADD.md")
        bx = [s for s in brackets if s in persona_yields[PS.PLAN12_K]]
        rho_b = {K: C.spearman([brackets[s] for s in bx], [persona_yields[K][s] for s in bx])[0] for K in persona_yields}
        persona_info = {"n_entities": ps["n"], "n_traits_with_vectors": len(trait_rows),
                        "n_traits_in_corpus": len(persona_yields[PS.PLAN12_K]), "shear_applied": ps["shear_applied"],
                        "shear_note": ps["shear_note"], "pool_K95": pool_k95, "slot": ps["slot"], "layer": ps["layer"],
                        "bracket_scores": len(brackets), "bracket_overlap": len(bx),
                        "spearman_bracket_vs_recomputed": {str(k): C._r(v) for k, v in rho_b.items()},
                        "yield_source": "recomputed (plan 12 step 1): leave-one-out residual outside the top-K PCs of the "
                                        "other entities; the May 2026 scores survive only as the 24 bracketed values"}
        brackets_in = {s: brackets[s] for s in bx}
    except Exception as exc:  # noqa: BLE001
        persona_info = {"error": f"{type(exc).__name__}: {exc}"}
        brackets_in = {}
        logger.error("persona vectors unavailable: %s", exc)
    timings["persona"] = round(time.time() - ts, 1)
    run["persona"] = persona_info
    save_run()

    # ---------------------------------------------------------------- views and per-view metrics
    rows, gloss_rows, hub, thr = [], [], {}, {}
    keep_views = {}
    dup_rel = set(C.SYNONYM_RELATIONS)
    dup_pairs = [p for p in lp.pairs if p.relation in dup_rel]
    for arm in arms:
        vec = emb[arm]
        for rep in args.representations:
            E = np.stack([vec[t] for t in texts["corpus"][rep]])
            ext = {m: vec[t] for m, t in texts["ext"][rep].items()}
            gq = {s: vec[t] for s, t in texts["gloss"][rep].items()}
            for variant in args.variants:
                ts = time.time()
                v = C.build_view(E, variant, residual=not args.no_residual)
                lt = C.labelled_tasks(v, lp, ci["index"], ext)
                key = f"{arm}|{rep}|{variant}"
                for metric in NOVELTY_METRICS:
                    if metric.startswith("resid") and not v.residual:
                        continue
                    row = {"model": arm, "representation": rep, "variant": variant, "metric": metric,
                           "K": (v.K95 if metric == "resid_K95" else int(metric.split("_")[1])) if metric.startswith("resid") else None}
                    if metric in C.PAIR_METRICS:
                        row.update({k: val for k, val in lt["metrics"][metric].items() if k != "median"})
                        row["median_sim"] = lt["metrics"][metric]["median"]
                    if persona_yields:
                        by_k = {}
                        for K in PERSONA_KS:
                            rho, p, n = C.persona_task(v, ci["stems"], persona_yields[K], metric)
                            by_k[str(K)] = C._r(rho)
                            if K == PS.PLAN12_K:
                                row.update({"spearman_persona_yield": C._r(rho), "spearman_persona_p": C._r(p, 6),
                                            "n_persona": n})
                        row["spearman_persona_yield_by_K"] = by_k
                        if brackets_in:
                            rho_b, _, nb = C.persona_task(v, ci["stems"], brackets_in, metric)
                            row["spearman_bracket24"] = C._r(rho_b)
                            row["n_bracket"] = nb
                    rows.append(row)
                g = C.gloss_recovery(v, gq, ci["index"])
                gloss_rows.append({"model": arm, "representation": rep, "variant": variant, **g})
                hub[key] = C.hubness(v, ci["stems"])
                sims = lt["sims"]
                dup_sims = {m: np.concatenate([sims[r][mi] for r in C.SYNONYM_RELATIONS if r in sims])
                            for mi, m in enumerate(C.PAIR_METRICS)}
                folds = [p.fold for r in C.SYNONYM_RELATIONS for p in lp.pairs if p.relation == r]
                certain = [not p.uncertain for r in C.SYNONYM_RELATIONS for p in lp.pairs if p.relation == r]
                thr[key] = {}
                for mi, m in enumerate(C.PAIR_METRICS):
                    nn = v.nn_cos if m == "cos" else v.nn_csls
                    thr[key][m] = C.place_thresholds(nn, dup_sims[m], sims["unrelated"][mi], dup_folds=folds,
                                                     dup_certain=certain)
                thr[key]["K95"] = v.K95
                if rep in ("full", "strip"):
                    keep_views[key] = (v, lt["sims"], ext)
                timings[key] = round(time.time() - ts, 1)
                logger.info("[%s] view done in %.1fs", key, time.time() - ts)
        save_run()

    # ---------------------------------------------------------------- provisional recommendation
    def mean_over_arms(rep, variant, metric, field):
        vals = [r[field] for r in rows if r["representation"] == rep and r["variant"] == variant
                and r["metric"] == metric and r.get(field) is not None]
        return float(np.mean(vals)) if vals else float("nan")
    # provisional choice (Roger decides): mean rank, over the three local tasks that apply to a
    # nearest-neighbour metric, of the cross-model means: (a) duplicate vs near-distinct AUC,
    # (b) synonym vs antonym AUC and (c) Spearman with the persona yield; gloss recall@1 breaks ties.
    cands = []
    for variant in args.variants:
        for metric in C.PAIR_METRICS:
            a = mean_over_arms("full", variant, metric, "auc_dup_vs_distinct")
            b = mean_over_arms("full", variant, metric, "auc_ant_vs_syn")
            c = mean_over_arms("full", variant, metric, "spearman_persona_yield")
            gr = float(np.mean([g[metric]["recall_at_1"] for g in gloss_rows
                                if g["representation"] == "full" and g["variant"] == variant and g.get(metric)]))
            cands.append({"variant": variant, "metric": metric, "a": a, "b": b, "c": c, "gloss": gr})
    for task in ("a", "b", "c"):
        order = sorted(cands, key=lambda d: -(d[task] if np.isfinite(d[task]) else -9))
        for r_, d in enumerate(order):
            d[f"rank_{task}"] = r_ + 1
    for d in cands:
        d["mean_rank"] = float(np.mean([d["rank_a"], d["rank_b"], d["rank_c"]]))
    cands.sort(key=lambda d: (d["mean_rank"], -d["gloss"]))
    rank = [(d["a"], d["gloss"], d["variant"], d["metric"], d) for d in cands]
    rec_variant, rec_metric = cands[0]["variant"], cands[0]["metric"]
    primary = "openai" if "openai" in arms else arms[0]

    # ---------------------------------------------------------------- histograms
    pngs = []
    for arm in arms:
        panels = []
        for variant in args.variants:
            v, sims, _ = keep_views[f"{arm}|full|{variant}"]
            t = thr[f"{arm}|full|{variant}"]["cos"]
            panels.append({"variant": variant, "nn": v.nn_cos,
                           "dup": np.concatenate([sims[r][0] for r in C.SYNONYM_RELATIONS if r in sims]),
                           "distinct": sims.get("near_distinct", (np.zeros(0),))[0],
                           "antonym": sims.get("antonym", (np.zeros(0),))[0],
                           "t_hi": t["t_hi"], "t_lo": t["t_lo"], "n_low_tail": t["n_low_tail"]})
        p = out / f"nn_hist_{arm}.png"
        C.plot_nn_histograms(p, model={"openai": "text-embedding-3-large", "bge": "bge-large-en-v1.5",
                                       "gemma": "embeddinggemma-300m"}.get(arm, arm),
                             representation="label: full description", panels=panels)
        pngs.append(str(p.relative_to(repo)) if p.resolve().is_relative_to(repo.resolve()) else str(p))

    # ---------------------------------------------------------------- drop or merge
    link = C.arrangement_linker(ci["arrangement_of"])
    delib = C.deliberate_set(lp)
    arranged = {(ci["index"][a], ci["index"][b]) for a, lst in ci["arrangement_of"].items() for _, mem in lst
                for b in mem if b != a and a in ci["index"] and b in ci["index"]}
    dm, dm_masked, masked_info = {}, {}, {}
    for arm in arms:
        views = {var: keep_views[f"{arm}|full|{var}"][0] for var in args.variants}
        # plan 15 step 7: the tail that separates from the bulk (the NN distribution's upper fence,
        # cosine); t_hi from the labelled duplicates sits below t_lo on this corpus (see thresholds.json)
        t_cut = thr[f"{arm}|full|{rec_variant}"]["cos"]["bulk"]["upper_fence"]
        for r in C.drop_or_merge_rows(views, ci["stems"], primary=rec_variant, metric="cos", t_hi=t_cut,
                                      flagged_by=arm, arrangement_link=link, deliberate=delib):
            _merge_dm(dm, r, arm)
        # step 8 proper: the nearest neighbour once recorded arrangement partners are excluded
        mnn = C.masked_nn(views[rec_variant], arranged)
        q1, q3 = np.quantile(mnn[1], [0.25, 0.75])
        fence = float(q3 + 1.5 * (q3 - q1))
        masked_info[arm] = {"bulk": {"q1": C._r(float(q1)), "median": C._r(float(np.median(mnn[1]))), "q3": C._r(float(q3)),
                                     "upper_fence": C._r(fence)}, "n_above_fence": int((mnn[1] > fence).sum())}
        for r in C.drop_or_merge_rows(views, ci["stems"], primary=rec_variant, metric="cos", t_hi=fence,
                                      flagged_by=arm, arrangement_link=link, deliberate=delib, nn=mnn):
            _merge_dm(dm_masked, r, arm)
        if arm == primary:
            masked_primary = mnn
    write_drop_or_merge(out / "drop_or_merge.md", dm, dm_masked, masked_info, ci, arms, args.variants, rec_variant,
                        thr)

    # ---------------------------------------------------------------- contrast ablation
    ablation = {}
    minimal_vecs = {arm: {t: emb[arm][t] for t in texts["minimal"]} for arm in arms}
    para_vecs = {arm: {s: emb[arm][t] for s, t in texts["para"].items()} for arm in arms}
    changed_idx = [ci["index"][s] for s in classes if s in ci["index"]]
    if "full" in args.representations and "strip" in args.representations:
        for variant in args.variants:
            nn_full = {arm: keep_views[f"{arm}|full|{variant}"][0] for arm in arms}
            nn_strip = {arm: keep_views[f"{arm}|strip|{variant}"][0] for arm in arms}
            j_full_all = C.cross_model_nn_agreement(nn_full) if len(arms) > 1 else {}
            j_strip_all = C.cross_model_nn_agreement(nn_strip) if len(arms) > 1 else {}
            j_full = C.cross_model_nn_agreement(nn_full, changed_idx) if len(arms) > 1 else {}
            j_strip = C.cross_model_nn_agreement(nn_strip, changed_idx) if len(arms) > 1 else {}
            for arm in arms:
                vf, _, ext_f = keep_views[f"{arm}|full|{variant}"]
                vs, _, ext_s = keep_views[f"{arm}|strip|{variant}"]
                res = C.contrast_ablation(vf, vs, stems=ci["stems"], index=ci["index"], classes=classes,
                                          partner=ci["partner"], lp=lp, ext_full=ext_f, ext_strip=ext_s,
                                          minimal=minimal, minimal_vecs=minimal_vecs[arm], persona=persona,
                                          paraphrases=para_vecs[arm] or None)
                mine = lambda d: [x for k, x in d.items() if arm in k.split("~") and x is not None]  # noqa: E731
                if j_full:
                    res["j_cross_model"] = {"full": C._r(float(np.mean(mine(j_full)))),
                                            "strip": C._r(float(np.mean(mine(j_strip)))),
                                            "full_all_traits": C._r(float(np.mean(mine(j_full_all)))),
                                            "strip_all_traits": C._r(float(np.mean(mine(j_strip_all)))),
                                            "pairs_changed_subset": {"full": j_full, "strip": j_strip}}
                res["recommendation"] = C.recommend_contrast(res)
                ablation.setdefault(arm, {})[variant] = res

    # (e) the blinded comparisons: the sample (always) and the Sonnet judge (only without --skip-llm)
    vf = keep_views[f"{primary}|full|{rec_variant}"][0]
    vs = keep_views[f"{primary}|strip|{rec_variant}"][0]
    items = C.blinded_comparisons(vf, vs, stems=ci["stems"], labels=ci["labels"], descriptions=ci["descriptions"],
                                  classes=classes, n=60, n_for_roger=30, seed=0)
    (out / "contrast_comparisons_key.json").write_text(json.dumps(
        {"model": primary, "variant": rec_variant, "representations": ["full", "strip"], "items": items},
        indent=2, ensure_ascii=False) + "\n")
    write_marks_sheet(args.marks_sheet, items, ci, primary, rec_variant)
    llm = {"skipped": bool(args.skip_llm)}
    if not args.skip_llm:
        llm = run_llm_criteria(ci, items, llm_items, para_path, paraphrases, usage)
        if llm.get("blinded"):
            for arm in ablation:
                ablation[arm].setdefault(rec_variant, {})["e_blinded"] = llm["blinded"]
        save_run()
    for arm in ablation:
        for variant in ablation[arm]:
            r = ablation[arm][variant]
            r["criteria_status"] = {
                "a": "ran", "b": "ran", "c": "ran", "d": "ran", "f": "ran" if "f_minimal_pairs" in r else "skipped",
                "h": "ran" if "h_persona" in r else "skipped (no persona vectors)",
                "j": "ran" if "j_cross_model" in r else "skipped (one model)",
                "e": "ran" if "e_blinded" in r else "skipped (--skip-llm): needs the Sonnet judge; sample written",
                "g": "ran" if "g_paraphrase_invariance" in r else "skipped (--skip-llm): needs Haiku paraphrases",
                "i": "ran" if "i_heldout_recovery" in r else "skipped (--skip-llm): needs Haiku paraphrases"}

    # ---------------------------------------------------------------- write
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input, current_files_input
    inputs = [current_file_input(dep_key="labelled_pairs", path=lp_path),
              current_file_input(dep_key="contrast_cuts", path=out / CT.CUTS_NAME),
              current_files_input(dep_key="trait_files",
                                  paths=sorted((repo / "data" / "traits" / "instructions").glob("*.json")))]

    def write(name, payload, title):
        atomic_write_text(json.dumps(json_metadata(payload, inputs=inputs, title=title), indent=2,
                                     ensure_ascii=False, default=_jsonable) + "\n", out / name)
    write("loo_metrics.json", {"rows": rows, "gloss_recovery": gloss_rows, "persona": persona_info},
          "M2 leave-one-out metrics")
    write("hubness.json", hub, "M2 hubness census")
    write("thresholds.json", thr, "M2 thresholds against the bulk")
    write("contrast_ablation.json", ablation, "M2 contrast-clause ablation")
    rec_view = keep_views[f"{primary}|full|{rec_variant}"][0]
    summary = {
        "models_run": arms, "models_failed": run["models_failed"], "representations": args.representations,
        "variants": args.variants, "n_traits": len(ci["stems"]), "labelled_pairs": lp.counts(),
        "contrast_rows": {"census": cuts_payload["counts"], "changed": len(classes)},
        "provisional": {"variant": rec_variant, "metric": rec_metric, "primary_model": primary,
                        "rule": "mean rank over tasks (a), (b), (c) of the cross-model means (representation full); "
                                "gloss recall@1 breaks ties",
                        "ranking": [{k: (C._r(v) if isinstance(v, float) else v) for k, v in d.items()}
                                    for *_, d in rank]},
        "novelty_extremes": C.most_and_least_novel(rec_view, ci["stems"], rec_metric),
        "novelty_extremes_partners_excluded": C.most_and_least_novel(rec_view, ci["stems"], "cos", nn=masked_primary),
        "contrast_recommendation": {arm: ablation.get(arm, {}).get(rec_variant, {}).get("recommendation")
                                    for arm in arms},
        "drop_or_merge": {"n_pairs": len(dm), "n_expected": sum(1 for r in dm.values() if r["arrangement"] or r["deliberate_duplicate"]),
                          "partners_excluded": {"n_pairs": len(dm_masked), "by_model": masked_info}},
        "pngs": pngs, "persona": persona_info, "llm": llm, "cost_usd": round(usage.total_cost_usd, 6),
        "usage": usage.as_dict(), "cost_usd_cumulative": round(write_usage().total_cost_usd, 6),
        "wall_time_s": round(time.time() - t0, 1)}
    write("summary.json", summary, "M2 calibration summary")
    run["finished_at"] = utc_now()
    timings["total"] = round(time.time() - t0, 1)
    save_run()
    print(json.dumps({k: summary[k] for k in ("models_run", "models_failed", "provisional", "contrast_recommendation",
                                              "drop_or_merge", "cost_usd", "wall_time_s")}, indent=2, default=_jsonable))
    print(usage.log_line())
    return 0


def _jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, tuple)):
        return list(o)
    raise TypeError(type(o))


def _trait_link(stem: str, label: str, rel: str) -> str:
    return f"[{label}]({rel}/{stem}.json)"


def _merge_dm(dm: dict, r: dict, arm: str) -> None:
    k = tuple(sorted((r["trait"], r["nearest"])))
    if k in dm:
        dm[k]["flagged_by"].append(arm)
        dm[k]["sims_by_model"][arm] = r["sim"]
    else:
        dm[k] = {**r, "flagged_by": [arm], "sims_by_model": {arm: r["sim"]}}


def _dm_table(rows: dict, ci: dict, variants) -> list[str]:
    rel = "../../traits/instructions"
    lines = ["| trait | nearest | flagged by | " + " | ".join(variants) + " | arrangement | deliberate dup | description A | description B |",
             "|" + "---|" * (len(variants) + 7)]
    order = sorted(rows.values(), key=lambda r: (bool(r["arrangement"] or r["deliberate_duplicate"]), -len(r["flagged_by"]),
                                                 -(r["primary_score"] or 0)))
    for r in order:
        a, b = r["trait"], r["nearest"]
        sims = r["sims_by_model"][r["flagged_by"][0]]
        da = ci["corpus"][a]["description"].replace("|", "/")
        db = ci["corpus"][b]["description"].replace("|", "/")
        lines.append(f"| {_trait_link(a, ci['corpus'][a]['label'], rel)} | {_trait_link(b, ci['corpus'][b]['label'], rel)} | "
                     f"{', '.join(r['flagged_by'])} | " + " | ".join(str(sims.get(v)) for v in variants)
                     + f" | {r['arrangement'] or ''} | {'yes' if r['deliberate_duplicate'] else ''} | {da} | {db} |")
    return lines


def write_drop_or_merge(path: Path, dm: dict, dm_masked: dict, masked_info: dict, ci: dict, arms, variants,
                        rec_variant, thr) -> None:
    lines = ["# Drop-or-merge candidates (M2 pilot, plan 15 step 8)", "",
             "Similarities are cosine under each space variant, for the first model that flagged the pair; "
             f"membership is decided in the provisional variant ({rec_variant}, representation `full`).  The covered "
             "threshold from the labelled duplicates, `t_hi`, falls below the random-pair threshold `t_lo` on this "
             "corpus for every model and variant (see thresholds.json), so it cannot define a tail; both tables use "
             "the upper fence (Q3 + 1.5 IQR) of a nearest-neighbour distribution instead.", "",
             "## Partners excluded (the real candidates)", "",
             "Each trait's nearest neighbour once its recorded arrangement partners (pair, triangle, tetrahedron, "
             "sequence) are ruled out, as plan 15 step 8 asks (the antonym probe that would do this is M3's).  Fence per "
             "model: " + ", ".join(f"{a} {masked_info[a]['bulk']['upper_fence']} ({masked_info[a]['n_above_fence']} traits "
                                   f"above)" for a in arms) + ".", ""]
    lines += _dm_table(dm_masked, ci, variants) if dm_masked else ["(none)"]
    lines += ["", "## All neighbours (expected: recorded pairs)", "",
              "The plain nearest neighbour; fence per model: "
              + ", ".join(f"{a} {thr[f'{a}|full|{rec_variant}']['cos']['bulk']['upper_fence']}" for a in arms)
              + ".  Every row here is a recorded clean pair whose two descriptions mirror each other.", ""]
    lines += _dm_table(dm, ci, variants) if dm else ["(none)"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_marks_sheet(path: Path, items, ci, model, variant) -> None:
    rel = "../../data/traits/instructions"
    desc = {s: ci["corpus"][s]["description"] for s in ci["stems"]}
    labels = {s: ci["corpus"][s]["label"] for s in ci["stems"]}
    head = [f"# Contrast clauses: 30 blinded neighbour comparisons for Roger's marks (M2 pilot)", "",
            f"For each trait below, two lists of its five nearest existing traits, from {model} embeddings in the "
            f"`{variant}` space: one list embeds every description as written, the other with its contrast clause "
            "(\"rather than X\", \"instead of\", \"but not\", \"without being\") removed. The order of the two lists is "
            "random and the key is in [contrast_comparisons_key.json](../../data/candidates/calibration/contrast_comparisons_key.json) "
            "(do not open it before marking). Mark the list whose traits are closer in meaning to the given trait "
            "(synonyms first; an antonym is not close), or `same`. The same 30 are the first half of the Sonnet "
            "judge's sample (criterion e), so its agreement with you is known before its verdict counts.", ""]
    body = C.comparisons_markdown(items, labels_of=labels, desc_of=desc, link=lambda s, l: _trait_link(s, l, rel))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(head) + "\n" + body + "\n", encoding="utf-8")


def run_llm_criteria(ci, items, llm_items, para_path: Path, paraphrases: dict, usage) -> dict:
    """(g) paraphrases (cached) and (e) the blinded judgement.  Not run in the pilot."""
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env")
    import anthropic
    client = anthropic.AsyncAnthropic()
    todo = [{"stem": s, "label": ci["corpus"][s]["label"], "description": ci["corpus"][s]["description"]}
            for s in llm_items]
    new = asyncio.run(CL.run_paraphrases(client, todo, usage=usage)) if todo else {}
    paraphrases = {**paraphrases, **new}
    para_path.write_text(json.dumps({"model": CL.PARAPHRASE_MODEL, "prompt_version": CL.PARAPHRASE_PROMPT_VERSION,
                                     "paraphrases": paraphrases}, indent=2, ensure_ascii=False) + "\n")
    desc = {s: ci["corpus"][s]["description"] for s in ci["stems"]}
    labels = {s: ci["corpus"][s]["label"] for s in ci["stems"]}
    blinded = asyncio.run(CL.run_blinded(client, items, usage=usage, desc_of=desc, label_of=labels))
    return {"skipped": False, "n_paraphrases": len(paraphrases), "blinded": blinded,
            "note": "rerun the CLI once more to fold the new paraphrases into (g) and (i)"}


if __name__ == "__main__":
    sys.exit(main())
