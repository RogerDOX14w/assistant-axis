"""Retrieval recall@k and paired statistics (M2 round 4, 2026-10-02).

The question changed in round 4: under the proposed M3 design the embedding
only *retrieves* the k nearest existing traits for every candidate and the LLM
adjudicates every candidate, so the covered setting is judged by whether a
re-proposed existing trait appears in that short list (recall@k), not by a
similarity threshold.  This module holds the pure pieces; the run is
``data_analysis/gap_generation/calibrate_metric.py --round4``.

* :func:`evaluate_view`: one model's corpus and queries in one space variant:
  each query's rank of its own trait, its top list, its similarity to its own
  trait and its best similarity to any other.
* :func:`target_ranks`, :func:`hits`, :func:`recall_at_k`, :func:`topk_indices`,
  :func:`union_hits` (two models' top-k lists merged).
* Paired comparisons of two settings on the same queries:
  :func:`mcnemar_exact` (the exact binomial test on the discordant queries) and
  :func:`paired_bootstrap` (a percentile interval for the difference in recall,
  resampling queries, or whole clusters of queries such as all the queries
  about one trait); :func:`holm` for a family of such tests.
* :func:`threshold_design`: the round-3 threshold numbers on the larger query
  set, for comparison with the old design.
* Round 4's query sources and its whole evaluation: :func:`plain_reading_same`,
  :func:`m1_gloss_queries`, :func:`query_text`, :func:`evaluate_round4`,
  :func:`summarise_round4` (recall@k per source and pooled, the two models'
  union, the paired comparisons against centred ``w14``, the threshold design)
  and :func:`round4_markdown`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

from .representation import represent_short
from .space import fit_space


# --------------------------------------------------------------------------- ranks and recall


def target_ranks(S: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """0-based rank of each row's target column: the number of columns with a
    strictly higher similarity (0 = the target is first)."""
    S = np.asarray(S, dtype=np.float64)
    t = np.asarray(targets, dtype=int)
    own = S[np.arange(len(S)), t]
    return (S > own[:, None]).sum(axis=1)


def hits(ranks: np.ndarray, k: int) -> np.ndarray:
    """Boolean per query: its own trait is among the first ``k``."""
    return np.asarray(ranks) < k


def recall_at_k(ranks: np.ndarray, ks: Iterable[int]) -> dict[int, float]:
    r = np.asarray(ranks)
    return {int(k): float((r < k).mean()) if len(r) else float("nan") for k in ks}


def topk_indices(S: np.ndarray, k: int) -> np.ndarray:
    """Each row's ``k`` most similar columns, nearest first."""
    S = np.asarray(S, dtype=np.float64)
    k = min(k, S.shape[1])
    part = np.argpartition(-S, k - 1, axis=1)[:, :k]
    order = np.argsort(-np.take_along_axis(S, part, axis=1), axis=1, kind="stable")
    return np.take_along_axis(part, order, axis=1)


def union_hits(top_a: np.ndarray, top_b: np.ndarray, targets: np.ndarray, *, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Merge two models' top-``k`` lists per query: ``(hit, length)``, whether
    the target is in the union and how many distinct traits the union holds."""
    A, B = np.asarray(top_a)[:, :k], np.asarray(top_b)[:, :k]
    t = np.asarray(targets)
    hit = (A == t[:, None]).any(axis=1) | (B == t[:, None]).any(axis=1)
    length = np.array([len(set(a.tolist()) | set(b.tolist())) for a, b in zip(A, B)])
    return hit, length


def evaluate_view(E_corpus: np.ndarray, Q_raw: np.ndarray, targets: np.ndarray, variant: str, *,
                  top: int = 10) -> dict:
    """Fit ``variant`` on the corpus, map corpus and queries into it, and score
    every query against every corpus trait (cosine).  Returns ``ranks`` (own
    trait, 0-based), ``top`` (the first ``top`` corpus rows per query), ``own``
    (cosine to its own trait) and ``other_max`` (the best cosine to any other
    trait: the "hidden original" case)."""
    T = fit_space(E_corpus, variant)
    Z = T.apply(E_corpus)
    Q = T.apply(Q_raw)
    S = Q @ Z.T
    t = np.asarray(targets, dtype=int)
    ar = np.arange(len(S))
    own = S[ar, t].copy()
    S_other = S.copy()
    S_other[ar, t] = -np.inf
    return {"ranks": target_ranks(S, t), "top": topk_indices(S, top), "own": own,
            "other_max": S_other.max(axis=1), "Z": Z}


# --------------------------------------------------------------------------- paired tests


def mcnemar_exact(a_hit: Sequence[bool], b_hit: Sequence[bool]) -> dict:
    """McNemar's exact test for two settings scored on the same queries.  Only
    the discordant queries carry information: ``a_only`` (A finds the trait, B
    does not) and ``b_only``.  Under "no difference" each discordant query is a
    fair coin, so the two-sided p is ``2 P(X <= min(a_only, b_only))`` for
    ``X ~ Binomial(a_only + b_only, 1/2)``, capped at 1; 1 when nothing is
    discordant.  ``diff`` is recall(A) - recall(B)."""
    from scipy.stats import binom
    a, b = np.asarray(a_hit, bool), np.asarray(b_hit, bool)
    if a.shape != b.shape:
        raise ValueError("paired arrays must have the same shape")
    a_only, b_only = int((a & ~b).sum()), int((~a & b).sum())
    m = a_only + b_only
    p = 1.0 if m == 0 else float(min(1.0, 2.0 * binom.cdf(min(a_only, b_only), m, 0.5)))
    n = len(a)
    return {"n": n, "a_only": a_only, "b_only": b_only, "p": p,
            "diff": float(a.mean() - b.mean()) if n else float("nan")}


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_boot: int = 2000, seed: int = 0,
                     clusters: Optional[Sequence] = None, alpha: float = 0.05) -> dict:
    """Percentile ``1 - alpha`` interval for ``mean(a) - mean(b)`` on paired
    data.  Without ``clusters`` each resample draws queries with replacement;
    with ``clusters`` it draws whole clusters (all the queries about one trait),
    which is the honest interval when one trait contributes several queries."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("paired arrays must have the same shape")
    d = a - b
    rng = np.random.default_rng(seed)
    if clusters is None:
        idx = rng.integers(0, len(d), size=(n_boot, len(d)))
        boots = d[idx].mean(axis=1)
    else:
        cl = np.asarray(clusters)
        _, inv = np.unique(cl, return_inverse=True)
        n_c = int(inv.max()) + 1
        sums = np.bincount(inv, weights=d, minlength=n_c)
        counts = np.bincount(inv, minlength=n_c).astype(np.float64)
        pick = rng.integers(0, n_c, size=(n_boot, n_c))
        boots = sums[pick].sum(axis=1) / counts[pick].sum(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return {"diff": float(d.mean()), "lo": float(lo), "hi": float(hi), "n_boot": int(n_boot), "seed": int(seed),
            "clustered": clusters is not None}


def holm(pvals: Sequence[float]) -> list[float]:
    """Holm's step-down adjustment (family-wise error), in the input order."""
    p = np.asarray(pvals, dtype=np.float64)
    m = len(p)
    order = np.argsort(p, kind="stable")
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


# --------------------------------------------------------------------------- the old threshold design


def threshold_design(own: np.ndarray, other_max: np.ndarray, antonym_sims: np.ndarray, *,
                     recall: float = 0.95) -> dict:
    """``t_hi`` = the highest similarity with at least ``recall`` of the queries'
    own-trait similarities at or above it; beside it, the share of recorded
    antonym pairs at or above ``t_hi`` and the share of queries whose best
    *other* trait reaches it (a new trait near an existing one, sent to the
    adjudicator rather than passed as new)."""
    own = np.sort(np.asarray(own, dtype=np.float64))
    n = len(own)
    j = int(math.floor((1 - recall) * n + 1e-9))
    t_hi = float(own[min(j, n - 1)])
    ant = np.asarray(antonym_sims, dtype=np.float64)
    return {"t_hi": t_hi, "recall_at_t_hi": float((own >= t_hi).mean()),
            "antonym_above_t_hi": float((ant >= t_hi).mean()) if len(ant) else None,
            "hidden_original_still_covered": float((np.asarray(other_max) >= t_hi).mean()), "n": n}


# --------------------------------------------------------------------------- round 4: query sources

#: Round 4's query sources, in report order.  The three paraphrase sets are keyed to the style that
#: wrote them (``calibrate_llm.paraphrase_prompt``: round 3's ``standard``, round 4's ``plain`` and
#: ``terse``); the two M1 sets are the split filter's glosses of existing labels, written by Haiku from
#: the bare label (the realistic M3 query), from the validation run and its rerun.
PARAPHRASE_SOURCES: dict[str, str] = {"paraphrase": "standard", "plain": "plain", "terse": "terse"}
M1_GLOSS_SOURCES: dict[str, Path] = {
    "m1_gloss_1": Path("data/candidates/filter/m1_validation/results.jsonl"),
    "m1_gloss_2": Path("data/candidates/filter/m1_validation_r2/results.jsonl"),
}
QUERY_SOURCES: tuple[str, ...] = tuple(PARAPHRASE_SOURCES) + tuple(M1_GLOSS_SOURCES)
SOURCE_TITLES: dict[str, str] = {
    "paraphrase": "paraphrase (round 3)", "plain": "plain paraphrase", "terse": "terse paraphrase",
    "m1_gloss_1": "M1 gloss, run 1", "m1_gloss_2": "M1 gloss, run 2", "pooled": "pooled"}
#: Sonnet's comparison of each corpus label's plain reading with its corpus sense: only labels read the
#: corpus's way (relation "same") are used as M1 gloss queries, so a gloss of another sense is not
#: counted as a retrieval miss.
PLAIN_READING_COMPARISON = Path("data/candidates/plain_reading/corpus_comparison_1/results.jsonl")
ROUND4_REPRESENTATIONS = ("w14", "w20")
ROUND4_VARIANTS = ("centred", "pw8", "pw12", "pw16", "pw24", "pw32")
ROUND4_KS = (1, 3, 5, 10)
COMPARISON_KS = (1, 5)
UNION_KS = (3, 5)
BASELINE = ("w14", "centred")
QUERY_REPRESENTATION = "w14"
ALPHA = 0.05
REAL_RULE = ("real: Holm-adjusted McNemar p < 0.05 over the family of pooled comparisons AND the 95% "
             "bootstrap interval (whole traits resampled) excludes zero")


def paraphrase_cache_name(style: str) -> str:
    """Round 3's ``paraphrases.json`` for the standard style, ``paraphrases_<style>.json`` otherwise."""
    return "paraphrases.json" if style == "standard" else f"paraphrases_{style}.json"


def query_text(text: str) -> str:
    """The M3 query form: the text alone, without a label, cut to a gloss's 14 words."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty query text")
    return represent_short(None, text.strip(), QUERY_REPRESENTATION)


def plain_reading_same(path: Path) -> set[str]:
    """Stems of the corpus labels whose plain reading was judged the corpus's own sense (relation
    ``same`` in the plain-reading comparison's ``results.jsonl``)."""
    from assistant_axis.entity_id import normalize_to_file_name
    out: set[str] = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if (r.get("comparison") or {}).get("relation") == "same":
                out.add(normalize_to_file_name(r.get("label") or r["key"]))
    return out


def m1_gloss_queries(results_path: Path, *, corpus: Iterable[str],
                     keep: Optional[Iterable[str]] = None) -> tuple[dict[str, str], dict]:
    """``({stem: gloss}, counts)`` from an M1 filter run's ``results.jsonl``: rows of the ``existing``
    stratum with a non-empty gloss whose label maps to a corpus stem (``normalize_to_file_name``) and,
    when ``keep`` is given, is in it.  The first row per stem wins."""
    from assistant_axis.entity_id import normalize_to_file_name
    corpus_set = set(corpus)
    keep_set = None if keep is None else set(keep)
    out: dict[str, str] = {}
    counts = {"existing": 0, "with_gloss": 0, "in_corpus": 0, "kept": 0}
    for line in Path(results_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if (r.get("meta") or {}).get("stratum") != "existing":
            continue
        counts["existing"] += 1
        g = r.get("gloss")
        if not (isinstance(g, str) and g.strip()):
            continue
        counts["with_gloss"] += 1
        stem = normalize_to_file_name(r["label"])
        if stem not in corpus_set:
            continue
        counts["in_corpus"] += 1
        if (keep_set is not None and stem not in keep_set) or stem in out:
            continue
        out[stem] = g.strip()
        counts["kept"] += 1
    return out, counts


# --------------------------------------------------------------------------- round 4: evaluation


def evaluate_round4(corpus: Mapping[str, Mapping[str, np.ndarray]], queries: Mapping[str, np.ndarray],
                    targets: Sequence[int], *, variants: Sequence[str], top: int = 10,
                    antonym_pairs: Optional[Sequence[Sequence[int]]] = None) -> dict:
    """Every ``(model, representation, variant)`` cell: :func:`evaluate_view` of
    the model's queries (the same rows, in the same order, for every cell)
    against its corpus under that representation, plus the cosine of each
    recorded antonym pair in that space (for :func:`threshold_design`).
    ``corpus[model][rep]`` and ``queries[model]`` are the model's raw rows."""
    t = np.asarray(targets, dtype=int)
    ap = np.asarray(antonym_pairs if antonym_pairs is not None and len(antonym_pairs) else np.zeros((0, 2)),
                    dtype=int).reshape(-1, 2)
    cells: dict = {}
    for model, reps in corpus.items():
        for rep, E in reps.items():
            for variant in variants:
                ev = evaluate_view(E, queries[model], t, variant, top=top)
                Z = ev.pop("Z")
                ev["antonym_sims"] = (Z[ap[:, 0]] * Z[ap[:, 1]]).sum(axis=1) if len(ap) else np.zeros(0)
                cells[(model, rep, variant)] = ev
    return cells


def _q(x, nd: int = 4):
    if x is None:
        return None
    x = float(x)
    return round(x, nd) if math.isfinite(x) else None


def _compare(a_hit: np.ndarray, b_hit: np.ndarray, clusters: np.ndarray, *, n_boot: int, seed: int) -> dict:
    mc = mcnemar_exact(a_hit, b_hit)
    bs = paired_bootstrap(a_hit, b_hit, n_boot=n_boot, seed=seed, clusters=clusters)
    return {"n": mc["n"], "recall": _q(np.mean(a_hit)), "recall_baseline": _q(np.mean(b_hit)), "diff": _q(mc["diff"]),
            "setting_only": mc["a_only"], "baseline_only": mc["b_only"], "p": mc["p"],
            "boot_lo": _q(bs["lo"]), "boot_hi": _q(bs["hi"])}


def _mark_real(rows: list[dict]) -> None:
    """Holm over the family, then the rule of :data:`REAL_RULE`."""
    if not rows:
        return
    for r, adj in zip(rows, holm([r["p"] for r in rows])):
        r["p_holm"] = adj
        excludes_zero = (r["boot_lo"] is not None and r["boot_lo"] > 0) or (r["boot_hi"] is not None and r["boot_hi"] < 0)
        r["real"] = bool(adj < ALPHA and excludes_zero)


def summarise_round4(cells: Mapping, *, models: Sequence[str], sources: Sequence[str], stems: Sequence[str],
                     targets: Sequence[int], corpus_stems: Sequence[str], ks: Sequence[int] = ROUND4_KS,
                     comparison_ks: Sequence[int] = COMPARISON_KS, union_ks: Sequence[int] = UNION_KS,
                     baseline: tuple[str, str] = BASELINE, n_boot: int = 2000, seed: int = 0,
                     miss_k: int = 5) -> dict:
    """The round-4 payload from :func:`evaluate_round4`'s cells.

    * ``recall``: recall@k per cell, pooled over the sources and per source.
    * ``comparisons``: per model and k in ``comparison_ks``, pooled: every other
      variant in the baseline's representation, and the other representations
      in the baseline's variant, against the baseline (centred ``w14``):
      McNemar's exact test (the discordant counts as ``setting_only`` /
      ``baseline_only``) and a paired bootstrap interval that resamples whole
      traits (one trait has up to one query per source); Holm over the family
      and :data:`REAL_RULE`.  ``comparisons_by_source``: the same per source.
    * ``union``: both models' top-k merged (k in ``union_ks``), recall and mean
      length, beside each model alone; ``union_vs_single``: the merged top-k
      against each model's own top 10, pooled.
    * ``threshold_design``: round 3's threshold numbers on these queries.
    * ``misses``: per cell, the queries whose trait is not in the top ``miss_k``
      as ``[source, stem, rank, first retrieved stem]``.
    """
    src = np.asarray(sources)
    stems_a = np.asarray(stems)
    t = np.asarray(targets, dtype=int)
    names = list(dict.fromkeys(src.tolist()))
    masks = {"pooled": np.ones(len(src), bool), **{s: src == s for s in names}}

    recall = []
    for (model, rep, variant), ev in cells.items():
        for name, m in masks.items():
            r = ev["ranks"][m]
            recall.append({"model": model, "representation": rep, "variant": variant, "source": name,
                           "n": int(m.sum()), "recall": {str(k): _q(v) for k, v in recall_at_k(r, ks).items()},
                           "median_rank": int(np.median(r)) + 1 if len(r) else None})

    reps_in = list(dict.fromkeys(rep for (_, rep, _) in cells))
    variants_in = list(dict.fromkeys(var for (_, _, var) in cells))
    challengers = [(baseline[0], v) for v in variants_in if v != baseline[1]] + \
                  [(rep, baseline[1]) for rep in reps_in if rep != baseline[0]]
    comps, comps_src = [], []
    for model in models:
        if (model, *baseline) not in cells:
            continue
        for k in comparison_ks:
            b_hit = hits(cells[(model, *baseline)]["ranks"], k)
            for ch in challengers:
                if (model, *ch) not in cells:
                    continue
                a_hit = hits(cells[(model, *ch)]["ranks"], k)
                head = {"model": model, "k": int(k), "setting": "|".join(ch), "baseline": "|".join(baseline)}
                comps.append({**head, **_compare(a_hit, b_hit, stems_a, n_boot=n_boot, seed=seed)})
                for name in names:
                    m = masks[name]
                    comps_src.append({**head, "source": name,
                                      **_compare(a_hit[m], b_hit[m], stems_a[m], n_boot=n_boot, seed=seed)})
    _mark_real(comps)
    _mark_real(comps_src)

    union, union_vs_single = [], []
    if len(models) == 2:
        a, b = models
        for rep in reps_in:
            for variant in variants_in:
                if (a, rep, variant) not in cells or (b, rep, variant) not in cells:
                    continue
                ca, cb = cells[(a, rep, variant)], cells[(b, rep, variant)]
                for k in union_ks:
                    hit, length = union_hits(ca["top"], cb["top"], t, k=k)
                    for name, m in masks.items():
                        union.append({"representation": rep, "variant": variant, "k": int(k), "source": name,
                                      "n": int(m.sum()), "recall": _q(hit[m].mean()),
                                      "mean_length": _q(length[m].mean(), 2),
                                      "single": {mdl: {"recall_at_k": _q(hits(c["ranks"][m], k).mean()),
                                                       "recall_at_10": _q(hits(c["ranks"][m], 10).mean())}
                                                 for mdl, c in ((a, ca), (b, cb))}})
                    for mdl, c in ((a, ca), (b, cb)):
                        union_vs_single.append({"representation": rep, "variant": variant, "k": int(k),
                                                "against": f"{mdl} top 10", "mean_length": _q(length.mean(), 2),
                                                **_compare(hit, hits(c["ranks"], 10), stems_a, n_boot=n_boot,
                                                           seed=seed)})

    threshold = []
    for (model, rep, variant), ev in cells.items():
        td = threshold_design(ev["own"], ev["other_max"], ev["antonym_sims"])
        threshold.append({"model": model, "representation": rep, "variant": variant,
                          **{k_: (_q(v) if isinstance(v, float) else v) for k_, v in td.items()},
                          "n_antonym_pairs": int(len(ev["antonym_sims"]))})

    misses = {}
    for key, ev in cells.items():
        bad = np.where(ev["ranks"] >= miss_k)[0]
        misses["|".join(key)] = [[str(src[i]), str(stems_a[i]), int(ev["ranks"][i]) + 1,
                                  str(corpus_stems[int(ev["top"][i, 0])])] for i in bad]

    return {"ks": [int(k) for k in ks], "baseline": "|".join(baseline),
            "n_queries": {name: int(m.sum()) for name, m in masks.items()},
            "n_traits_queried": int(len(set(stems_a.tolist()))),
            "recall": recall, "comparisons": comps, "comparisons_by_source": comps_src, "real_rule": REAL_RULE,
            "bootstrap": {"n_boot": int(n_boot), "seed": int(seed), "interval": "percentile, 95%",
                          "resampling_unit": "trait (all of one trait's queries together)"},
            "union": union, "union_vs_single": union_vs_single, "threshold_design": threshold,
            "misses": {"k": int(miss_k), "by_cell": misses}}


# --------------------------------------------------------------------------- round 4: markdown


def _f(x, nd: int = 3) -> str:
    return "–" if x is None else f"{x:.{nd}f}"


def _p(x) -> str:
    if x is None:
        return "–"
    return "<0.0001" if x < 1e-4 else f"{x:.4f}"


def round4_markdown(payload: Mapping) -> str:
    """The tables of ``retrieval_round4.json`` as markdown (the readout quotes from it)."""
    ks = [str(k) for k in payload["ks"]]
    srcs = [s for s in payload["n_queries"] if s != "pooled"]
    title = lambda s: SOURCE_TITLES.get(s, s)  # noqa: E731
    lines = ["# M2 round 4: retrieval recall@k for the covered setting", "",
             "Each query is a text about an existing trait, without its label, cut to 14 words; recall@k is the "
             "share of queries whose own trait is among the k nearest corpus entries (cosine; the corpus is "
             "`label: description` cut to 14 or 20 words).  Source: `retrieval_round4.json` beside this file.", "",
             "## Query sources", "", "| source | queries |", "|---|---|"]
    info = payload.get("query_sources", {})
    for s in srcs:
        extra = info.get(s, {}).get("note")
        lines.append(f"| {title(s)} | {payload['n_queries'][s]}{(' (' + extra + ')') if extra else ''} |")
    lines += [f"| pooled | {payload['n_queries']['pooled']} ({payload['n_traits_queried']} traits) |", "",
              "## Pooled recall@k", "", "| model | representation | variant | " + " | ".join(f"r@{k}" for k in ks) + " |",
              "|---|---|---|" + "---|" * len(ks)]
    for r in payload["recall"]:
        if r["source"] == "pooled":
            lines.append(f"| {r['model']} | {r['representation']} | {r['variant']} | "
                         + " | ".join(_f(r["recall"][k]) for k in ks) + " |")
    lines += ["", f"## Paired comparisons against centred w14, pooled", "",
              f"{payload['real_rule']}.  McNemar's exact test counts only the discordant queries (found by one "
              f"setting and not the other); the bootstrap ({payload['bootstrap']['n_boot']} resamples, seed "
              f"{payload['bootstrap']['seed']}) resamples whole traits, because one trait has up to one query per "
              "source.", "",
              "| model | k | setting | recall | centred w14 | difference | setting only / baseline only | McNemar p | "
              "Holm p | bootstrap 95% | real |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in payload["comparisons"]:
        lines.append(f"| {c['model']} | {c['k']} | {c['setting'].replace('|', ' ')} | {_f(c['recall'])} | "
                     f"{_f(c['recall_baseline'])} | {c['diff']:+.4f} | {c['setting_only']} / {c['baseline_only']} | "
                     f"{_p(c['p'])} | {_p(c['p_holm'])} | [{c['boot_lo']:+.4f}, {c['boot_hi']:+.4f}] | "
                     f"{'yes' if c['real'] else 'no'} |")
    lines += ["", "## Recall@1 / recall@5 per source", "",
              "| model | representation | variant | " + " | ".join(title(s) for s in srcs) + " |",
              "|---|---|---|" + "---|" * len(srcs)]
    by = {}
    for r in payload["recall"]:
        by.setdefault((r["model"], r["representation"], r["variant"]), {})[r["source"]] = r["recall"]
    for (m, rep, var), d in by.items():
        lines.append(f"| {m} | {rep} | {var} | " + " | ".join(
            f"{_f(d[s].get('1'))} / {_f(d[s].get('5'))}" if s in d else "–" for s in srcs) + " |")
    if payload["union"]:
        models = list(payload["union"][0]["single"])
        lines += ["", "## Both models' lists merged", "",
                  "The union of the two models' top k (in the same representation and variant), its recall and mean "
                  "length, beside each model's own recall@k and recall@10; pooled over the sources.", "",
                  "| representation | variant | k | merged recall | mean length | "
                  + " | ".join(f"{m} r@k / r@10" for m in models) + " |", "|---|---|---|---|---|" + "---|" * len(models)]
        for u in payload["union"]:
            if u["source"] == "pooled":
                lines.append(f"| {u['representation']} | {u['variant']} | {u['k']} | {_f(u['recall'])} | "
                             f"{_f(u['mean_length'], 2)} | " + " | ".join(
                                 f"{_f(u['single'][m]['recall_at_k'])} / {_f(u['single'][m]['recall_at_10'])}"
                                 for m in models) + " |")
        lines += ["", "Merged top k against one model's own top 10 (pooled; same tests as above, without Holm):", "",
                  "| representation | variant | k | against | merged recall | top-10 recall | merged only / top-10 only | "
                  "McNemar p | bootstrap 95% |", "|---|---|---|---|---|---|---|---|---|"]
        for u in payload["union_vs_single"]:
            lines.append(f"| {u['representation']} | {u['variant']} | {u['k']} | {u['against']} | {_f(u['recall'])} | "
                         f"{_f(u['recall_baseline'])} | {u['setting_only']} / {u['baseline_only']} | {_p(u['p'])} | "
                         f"[{u['boot_lo']:+.4f}, {u['boot_hi']:+.4f}] |")
    lines += ["", "## The old threshold design on the same queries (pooled)", "",
              "`t_hi` at 95% recall of the queries' similarity to their own trait; the share of recorded antonym "
              "pairs at or above it; the share of queries whose best other trait reaches it (the hidden-original case).",
              "", "| model | representation | variant | t_hi | antonyms above | hidden original still covered |",
              "|---|---|---|---|---|---|"]
    for r in payload["threshold_design"]:
        lines.append(f"| {r['model']} | {r['representation']} | {r['variant']} | {_f(r['t_hi'])} | "
                     f"{_f(r['antonym_above_t_hi'], 2)} | {_f(r['hidden_original_still_covered'], 2)} |")
    return "\n".join(lines) + "\n"
