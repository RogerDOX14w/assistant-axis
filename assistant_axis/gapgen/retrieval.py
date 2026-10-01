"""Retrieval recall@k and paired statistics (M2 round 4, 2026-10-02).

The question changed in round 4: under the proposed M3 design the embedding
only *retrieves* the k nearest existing traits for every candidate and the LLM
adjudicates every candidate, so the covered setting is judged by whether a
re-proposed existing trait appears in that short list (recall@k), not by a
similarity threshold.  This module holds the pure pieces; the run is
``data_analysis/gap_generation/retrieval_eval.py``.

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
"""
from __future__ import annotations

import math
from typing import Iterable, Optional, Sequence

import numpy as np

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
