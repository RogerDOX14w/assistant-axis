"""Metric calibration on the existing corpus (M2; plan 15 steps 1-4 and 6-8, and the
contrast-clause ablation of step 5).

The pieces, all pure functions on arrays so the unit tests run them on
synthetic embeddings:

* :func:`build_view` fits a space variant on one model's corpus embeddings
  for one representation and computes the leave-one-out geometry
  (cosine and CSLS nearest neighbours, 5-NN mean, the directional residual at
  K_95 and K = 10, 20, 40 for the centred variants).
* :func:`pair_similarities` scores labelled pairs (corpus stems and external
  members such as rejected queue entries) in a view.
* Tasks (plan 15 §3.4): (a) :func:`auc` of duplicate against near-distinct
  pair similarity; (b) antonym against synonym; (c) :func:`spearman` of a
  text novelty score against the persona-space yield.
* :func:`hubness` (step 6), :func:`place_thresholds` (step 7: the covered
  threshold from the labelled duplicates, the "unrelated" threshold from
  random pairs, the bulk and the low tail of the leave-one-out NN
  distribution), :func:`drop_or_merge_rows` (step 8).
* :func:`gloss_recovery`: each existing trait's M1 filter gloss ("label:
  gloss", median 14 words) as a query against the corpus; is its own trait
  the nearest?  A free stand-in for plan 10's paraphrase recall, and the
  direct measure of the gloss-length question.
* The contrast ablation's criteria (a)-(j): :func:`contrast_ablation`
  computes (a) (b) (c) (d) (f) (h) (j) locally; (g) and (i) need the Haiku
  paraphrases and (e) the Sonnet judge (``calibrate_llm``), run only without
  ``--skip-llm``.

``run_calibration`` (in ``data_analysis/gap_generation/calibrate_metric.py``)
wires them to the corpus, the embeddings and the output files.
"""
from __future__ import annotations

import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np

from .space import VARIANTS, SpaceTransform, csls, fit_space, k_for_variance, loo_residuals, topk_mean

CSLS_K = 10
RESIDUAL_KS = (10, 20, 40)
CENTRED_VARIANTS = ("centred", "centred_pc1", "centred_pc3")
SYNONYM_RELATIONS = ("duplicate", "deliberate_duplicate")
PAIR_METRICS = ("cos", "csls")


# --------------------------------------------------------------------------- statistics

def auc(pos: Sequence[float], neg: Sequence[float]) -> Optional[float]:
    """Mann-Whitney AUC: P(a positive scores above a negative), ties count half.
    ``None`` when either side is empty."""
    pos, neg = np.asarray(pos, dtype=float), np.asarray(neg, dtype=float)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if len(pos) == 0 or len(neg) == 0:
        return None
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sorted_v = allv[order]
    i = 0
    while i < len(sorted_v):          # average ranks over ties
        j = i
        while j + 1 < len(sorted_v) and sorted_v[j + 1] == sorted_v[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    r_pos = ranks[:len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def spearman(x: Sequence[float], y: Sequence[float]) -> tuple[Optional[float], Optional[float], int]:
    """``(rho, p, n)`` over the finite pairs; ``(None, None, n)`` below 5 pairs."""
    from scipy.stats import spearmanr
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    n = int(ok.sum())
    if n < 5:
        return None, None, n
    r = spearmanr(x[ok], y[ok])
    return float(r.statistic), float(r.pvalue), n


def _r(x: Optional[float], nd: int = 4) -> Optional[float]:
    return None if x is None or (isinstance(x, float) and not math.isfinite(x)) else round(float(x), nd)


# --------------------------------------------------------------------------- views

@dataclass
class View:
    """One (model, representation, variant): the transformed corpus and its
    leave-one-out geometry."""
    variant: str
    T: SpaceTransform
    Z: np.ndarray                 # (n, d) unit rows
    S: np.ndarray                 # cosine, diagonal = -inf
    C: np.ndarray                 # CSLS, diagonal = -inf
    r: np.ndarray                 # each corpus point's mean similarity to its CSLS_K nearest
    nn_cos: np.ndarray
    nn_cos_idx: np.ndarray
    nn_csls: np.ndarray
    nn_csls_idx: np.ndarray
    knn5: np.ndarray
    K95: Optional[int] = None
    residual: dict = field(default_factory=dict)   # {K: (n,)} for centred variants
    raw: Optional[np.ndarray] = None               # the model's unit rows before the transform

    def transform(self, E: np.ndarray) -> np.ndarray:
        return self.T.apply(E)

    def novelty(self, metric: str) -> np.ndarray:
        """Higher = more novel."""
        if metric == "cos":
            return 1.0 - self.nn_cos
        if metric == "csls":
            return -self.nn_csls
        if metric == "knn5":
            return 1.0 - self.knn5
        if metric.startswith("resid_"):
            k = metric.split("_", 1)[1]
            key = self.K95 if k == "K95" else int(k)
            return self.residual[key]
        raise ValueError(metric)

    def topk(self, i: int, k: int = 5, *, metric: str = "cos") -> list[int]:
        M = self.S if metric == "cos" else self.C
        return list(np.argsort(-M[i])[:k])


def build_view(E: np.ndarray, variant: str, *, residual: bool = True, residual_ks: Iterable[int] = RESIDUAL_KS,
               csls_k: int = CSLS_K) -> View:
    T = fit_space(E, variant)
    Z = T.apply(E)
    S = Z @ Z.T
    np.fill_diagonal(S, -np.inf)
    r = topk_mean(np.where(np.isinf(S), -np.inf, S), csls_k, exclude_diag=True)
    C = 2 * S - r[:, None] - r[None, :]
    np.fill_diagonal(C, -np.inf)
    nn_cos_idx = S.argmax(axis=1)
    nn_csls_idx = C.argmax(axis=1)
    ar = np.arange(len(S))
    knn5 = topk_mean(S, 5, exclude_diag=True)
    v = View(variant=variant, T=T, Z=Z, S=S, C=C, r=r, nn_cos=S[ar, nn_cos_idx], nn_cos_idx=nn_cos_idx,
             nn_csls=C[ar, nn_csls_idx], nn_csls_idx=nn_csls_idx, knn5=knn5, raw=np.asarray(E, dtype=np.float64))
    if residual and (variant in CENTRED_VARIANTS or variant.startswith("pw")):
        v.K95 = k_for_variance(Z, 0.95)
        v.residual = loo_residuals(Z, sorted(set(residual_ks) | {v.K95}))
    return v


def pair_similarities(view: View, pairs: Sequence, index: Mapping[str, int],
                      ext: Mapping[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """``(cos, csls)`` for each pair ``(a, b)`` (objects with ``.a``/``.b`` or tuples).
    Corpus members are read from the view; external members are embedded
    vectors in ``ext`` (raw model space), transformed here, their CSLS radius
    measured against the corpus."""
    ext_ids = sorted({m for p in pairs for m in _ab(p) if m not in index})
    missing = [m for m in ext_ids if m not in ext]
    if missing:
        raise KeyError(f"no embedding for external members {missing[:5]}")
    Xe = view.transform(np.stack([ext[m] for m in ext_ids])) if ext_ids else np.zeros((0, view.Z.shape[1]))
    re_ = topk_mean(Xe @ view.Z.T, CSLS_K, exclude_diag=False) if ext_ids else np.zeros(0)
    epos = {m: i for i, m in enumerate(ext_ids)}

    def vec(m):
        return view.Z[index[m]] if m in index else Xe[epos[m]]

    def rad(m):
        return view.r[index[m]] if m in index else re_[epos[m]]

    cos, cs = [], []
    for p in pairs:
        a, b = _ab(p)
        if a in index and b in index:
            c = float(view.Z[index[a]] @ view.Z[index[b]])
        else:
            c = float(vec(a) @ vec(b))
        cos.append(c)
        cs.append(2 * c - rad(a) - rad(b))
    return np.asarray(cos), np.asarray(cs)


def _ab(p) -> tuple[str, str]:
    return (p.a, p.b) if hasattr(p, "a") else (p[0], p[1])


# --------------------------------------------------------------------------- tasks

def labelled_tasks(view: View, lp, index: Mapping[str, int], ext: Mapping[str, np.ndarray]) -> dict:
    """Tasks (a) and (b) for one view, under cosine and CSLS."""
    rel_pairs = defaultdict(list)
    for p in lp.pairs:
        rel_pairs[p.relation].append(p)
    sims = {rel: pair_similarities(view, ps, index, ext) for rel, ps in rel_pairs.items() if ps}
    certain = {rel: np.array([not p.uncertain for p in ps]) for rel, ps in rel_pairs.items()}
    out = {}
    for mi, metric in enumerate(PAIR_METRICS):
        def s(rel, only_certain=False):
            if rel not in sims:
                return np.zeros(0)
            v = sims[rel][mi]
            return v[certain[rel]] if only_certain else v
        syn = np.concatenate([s(r) for r in SYNONYM_RELATIONS])
        syn_c = np.concatenate([s(r, True) for r in SYNONYM_RELATIONS])
        dist = s("near_distinct")
        out[metric] = {
            "auc_dup_vs_distinct": _r(auc(syn, dist)), "auc_dup_vs_distinct_certain": _r(auc(syn_c, s("near_distinct", True))),
            "auc_dup_vs_unrelated": _r(auc(syn, s("unrelated"))), "auc_ant_vs_syn": _r(auc(syn, s("antonym"))),
            "auc_ant_vs_unrelated": _r(auc(s("antonym"), s("unrelated"))),
            "n_dup": int(len(syn)), "n_dup_certain": int(len(syn_c)), "n_distinct": int(len(dist)),
            "n_ant": int(len(s("antonym"))), "n_unrelated": int(len(s("unrelated"))),
            "median": {rel: _r(float(np.median(s(rel)))) for rel in sims}}
    return {"metrics": out, "sims": sims}


def persona_task(view: View, stems: Sequence[str], yields: Mapping[str, float], metric: str) -> tuple:
    """Task (c): Spearman of the view's novelty score with the persona yield."""
    nov = view.novelty(metric)
    x = [nov[i] for i, s in enumerate(stems) if s in yields]
    y = [yields[s] for s in stems if s in yields]
    return spearman(x, y)


def hubness(view: View, stems: Sequence[str], *, k: int = 10, top: int = 10) -> dict:
    """k-occurrence census: how often each trait is among others' k nearest
    (and the nearest), under cosine and CSLS; skewness and the top hubs."""
    from scipy.stats import skew
    out = {}
    n = len(stems)
    for metric, M in (("cos", view.S), ("csls", view.C)):
        nnk = np.argsort(-M, axis=1)[:, :k]
        Nk = np.bincount(nnk.ravel(), minlength=n)
        N1 = np.bincount(nnk[:, 0], minlength=n)
        order = np.argsort(-Nk)[:top]
        out[metric] = {"skew_Nk": _r(float(skew(Nk))), "max_Nk": int(Nk.max()), "n_hubs": int((Nk >= 3 * k).sum()),
                       "n_antihubs": int((Nk == 0).sum()), "max_N1": int(N1.max()),
                       "top": [{"stem": stems[i], "Nk": int(Nk[i]), "N1": int(N1[i])} for i in order]}
    hub_cos = {h["stem"] for h in out["cos"]["top"] if h["Nk"] >= 3 * k}
    out["hubs_removed_by_csls"] = int(out["cos"]["n_hubs"] - out["csls"]["n_hubs"])
    out["k"] = k
    out["cos_hubs_not_hubs_under_csls"] = sorted(
        s for s in hub_cos if s not in {h["stem"] for h in out["csls"]["top"] if h["Nk"] >= 3 * k})
    return out


def place_thresholds(nn_sims: np.ndarray, dup_sims: np.ndarray, unrelated_sims: np.ndarray, *,
                     recall: float = 0.95, unrelated_q: float = 0.99,
                     dup_folds: Optional[Sequence[Optional[int]]] = None,
                     dup_certain: Optional[Sequence[bool]] = None) -> dict:
    """Step 7.  ``t_hi``: the similarity at which ``recall`` of the labelled
    duplicates are at or above it (the "covered" threshold); ``t_lo``: the
    ``unrelated_q`` quantile of random pairs (below it, "new").  The bulk of
    the leave-one-out NN similarities (quartiles), its upper fence
    (Q3 + 1.5 IQR) and the low tail (traits whose NN similarity is at or above
    ``t_hi``, i.e. closer than a typical duplicate) are reported beside them.
    With ``dup_folds``, ``t_hi`` is also set on the other folds and the recall
    measured on each held-out fold."""
    nn = np.asarray(nn_sims, dtype=float)
    dup = np.asarray(dup_sims, dtype=float)
    unr = np.asarray(unrelated_sims, dtype=float)
    t_hi = float(np.quantile(dup, 1 - recall, method="lower")) if len(dup) else None
    t_lo = float(np.quantile(unr, unrelated_q, method="higher")) if len(unr) else None
    q1, med, q3 = (float(x) for x in np.quantile(nn, [0.25, 0.5, 0.75]))
    fence = q3 + 1.5 * (q3 - q1)
    out = {"t_hi": _r(t_hi), "t_lo": _r(t_lo), "recall_at_t_hi": _r(float((dup >= t_hi).mean())) if t_hi is not None else None,
           "unrelated_below_t_lo": _r(float((unr <= t_lo).mean())) if t_lo is not None else None,
           "bulk": {"q1": _r(q1), "median": _r(med), "q3": _r(q3), "upper_fence": _r(fence)},
           "n_low_tail": int((nn >= t_hi).sum()) if t_hi is not None else None,
           "n_above_fence": int((nn > fence).sum()), "n_dup": int(len(dup)), "n_unrelated": int(len(unr)),
           "gap_t_hi_minus_t_lo": _r(t_hi - t_lo) if (t_hi is not None and t_lo is not None) else None}
    out["t_hi_above_t_lo"] = bool(t_hi is not None and t_lo is not None and t_hi > t_lo)
    out["dup_median"] = _r(float(np.median(dup))) if len(dup) else None
    out["n_nn_at_or_above_dup_median"] = int((nn >= np.median(dup)).sum()) if len(dup) else None
    if dup_certain is not None and len(dup):
        dc = dup[np.asarray(dup_certain, bool)]
        if len(dc):
            t_c = float(np.quantile(dc, 1 - recall, method="lower"))
            out["t_hi_certain"] = _r(t_c)
            out["n_low_tail_certain"] = int((nn >= t_c).sum())
    out["tail_rule"] = ("t_hi below t_lo: the labelled duplicates do not separate from random pairs at 95% recall, "
                        "so the drop-or-merge list uses the upper fence of the NN distribution" if not out["t_hi_above_t_lo"]
                        else "t_hi above t_lo")
    if dup_folds is not None and len(dup):
        f = np.asarray([-1 if x is None else x for x in dup_folds])
        recs = []
        for fold in sorted(set(f) - {-1}):
            train, test = dup[f != fold], dup[f == fold]
            if len(train) and len(test):
                t = np.quantile(train, 1 - recall, method="lower")
                recs.append(float((test >= t).mean()))
        out["heldout_recall_mean"] = _r(float(np.mean(recs))) if recs else None
        out["heldout_recall_by_fold"] = [_r(x) for x in recs]
    return out


def gloss_recovery(view: View, queries: Mapping[str, np.ndarray], index: Mapping[str, int]) -> dict:
    """Each query (an existing trait's gloss, embedded in raw model space) against
    the corpus: recall@1 and @5 of its own trait, under cosine and CSLS."""
    stems = [s for s in queries if s in index]
    if not stems:
        return {"n": 0}
    Q = view.transform(np.stack([queries[s] for s in stems]))
    S = Q @ view.Z.T
    rq = topk_mean(S, CSLS_K, exclude_diag=False)
    C = 2 * S - rq[:, None] - view.r[None, :]
    target = np.array([index[s] for s in stems])
    out = {"n": len(stems)}
    for name, M in (("cos", S), ("csls", C)):
        rank = (M > M[np.arange(len(stems)), target][:, None]).sum(axis=1)
        out[name] = {"recall_at_1": _r(float((rank == 0).mean())), "recall_at_5": _r(float((rank < 5).mean())),
                     "median_rank": int(np.median(rank)) + 1}
    return out


def masked_nn(view: View, exclude: Iterable[tuple[int, int]], *, metric: str = "cos") -> tuple[np.ndarray, np.ndarray]:
    """Nearest neighbours with some pairs ruled out (step 8: "after the antonym
    probe has excluded pair partners"; here the recorded arrangements stand in
    for the probe, which is M3's)."""
    M = np.array(view.S if metric == "cos" else view.C, copy=True)
    for i, j in exclude:
        M[i, j] = M[j, i] = -np.inf
    idx = M.argmax(axis=1)
    return idx, M[np.arange(len(M)), idx]


def drop_or_merge_rows(views: Mapping[str, View], stems: Sequence[str], *, primary: str, metric: str,
                       t_hi: float, flagged_by: str = "", arrangement_link=None, deliberate=frozenset(),
                       nn: Optional[tuple[np.ndarray, np.ndarray]] = None) -> list[dict]:
    """Step 8: traits whose nearest neighbour under ``views[primary]`` (``metric``)
    is at or above ``t_hi``; each row gives the neighbour, its similarity under
    every variant, whether the two share a recorded arrangement, and whether
    they are a labelled deliberate duplicate.  ``arrangement_link(a, b)``
    returns the arrangement kind or ``None``."""
    v = views[primary]
    if nn is not None:
        nn_idx, nn_val = nn
    else:
        nn_idx = v.nn_cos_idx if metric == "cos" else v.nn_csls_idx
        nn_val = v.nn_cos if metric == "cos" else v.nn_csls
    rows, seen = [], set()
    for i in np.argsort(-nn_val):
        if nn_val[i] < t_hi:
            break
        j = int(nn_idx[i])
        key = tuple(sorted((i, j)))
        if key in seen:
            continue
        seen.add(key)
        a, b = stems[i], stems[j]
        rows.append({"trait": a, "nearest": b, "sim": {name: _r(float(vv.Z[i] @ vv.Z[j])) for name, vv in views.items()},
                     "primary_score": _r(float(nn_val[i])), "arrangement": arrangement_link(a, b) if arrangement_link else None,
                     "deliberate_duplicate": tuple(sorted((a, b))) in deliberate, "flagged_by": flagged_by})
    return rows


# --------------------------------------------------------------------------- contrast ablation

def _mean(x) -> Optional[float]:
    x = [v for v in x if v is not None and math.isfinite(v)]
    return _r(float(np.mean(x))) if x else None


def contrast_ablation(full: View, strip: View, *, stems: Sequence[str], index: Mapping[str, int],
                      classes: Mapping[str, Optional[str]], partner: Mapping[str, str], lp,
                      ext_full: Mapping[str, np.ndarray], ext_strip: Mapping[str, np.ndarray],
                      minimal: Optional[Sequence[dict]] = None, minimal_vecs: Optional[Mapping[str, np.ndarray]] = None,
                      persona: Optional[dict] = None, paraphrases: Optional[Mapping[str, np.ndarray]] = None) -> dict:
    """Criteria (a) (b) (c) (d) (f) (h) for one model and one variant (full against
    stripped representation); (g) and (i) when ``paraphrases`` are given.  (e)
    and (j) are assembled by the caller (LLM judge; across models).
    ``classes`` maps every stripped stem to N / P / S, or ``None`` for a new
    hit; only stems in ``classes`` changed between the two representations."""
    changed = [s for s in stems if s in classes]
    cls_of = lambda s: classes.get(s) or "new"  # noqa: E731
    groups = ("N", "P", "S", "new", "all")
    res: dict = {}
    # (a) movement, and toward the recorded partner
    move = defaultdict(list)
    toward = defaultdict(list)
    for s in changed:
        i = index[s]
        m = float(full.Z[i] @ _in_full(full, strip, i))   # both texts in the full representation's space
        move[cls_of(s)].append(m)
        move["all"].append(m)
        p = partner.get(s)
        if p in index:
            j = index[p]
            d = float(_in_full(full, strip, i) @ full.Z[j] - full.Z[i] @ full.Z[j])
            toward[cls_of(s)].append(d)
            toward["all"].append(d)
    res["a_movement"] = {g: {"n": len(move[g]), "mean_cos_full_vs_strip": _mean(move[g]),
                             "n_with_partner": len(toward[g]), "mean_delta_cos_to_partner": _mean(toward[g]),
                             "frac_moved_away_from_partner": _r(float(np.mean(np.array(toward[g]) < 0))) if toward[g] else None}
                         for g in groups}
    # (b) labelled-pair tasks with and without the clause, per class of the member that changed
    res["b_tasks"] = {}
    for g in groups:
        sel = [p for p in lp.pairs if (g == "all" and (p.a in classes or p.b in classes))
               or any(cls_of(m) == g for m in (p.a, p.b) if m in classes)]
        if not sel:
            continue
        rows = {}
        for name, view, ext in (("full", full, ext_full), ("strip", strip, ext_strip)):
            by = defaultdict(list)
            for p in sel:
                by[p.relation].append(p)
            sims = {rel: pair_similarities(view, ps, index, ext)[0] for rel, ps in by.items()}
            syn = np.concatenate([sims.get(r, np.zeros(0)) for r in SYNONYM_RELATIONS])
            rows[name] = {"auc_ant_vs_syn": _r(auc(syn, sims.get("antonym", []))),
                          "auc_dup_vs_distinct": _r(auc(syn, sims.get("near_distinct", []))),
                          "auc_ant_vs_unrelated": _r(auc(sims.get("antonym", []), sims.get("unrelated", []))),
                          "n": {rel: len(v) for rel, v in sims.items()}}
        res["b_tasks"][g] = rows
    # (c) does the leave-one-out nearest neighbour change, and to what
    changes = defaultdict(list)
    for s in changed:
        i = index[s]
        a, b = int(full.nn_cos_idx[i]), int(strip.nn_cos_idx[i])
        changes[cls_of(s)].append({"stem": s, "full": stems[a], "strip": stems[b], "changed": a != b})
    res["c_nn_change"] = {g: {"n": len(changes[g]), "n_changed": sum(c["changed"] for c in changes[g]),
                              "n_unchanged": sum(not c["changed"] for c in changes[g]),
                              "changes": [c for c in changes[g] if c["changed"]]} for g in ("N", "P", "S", "new")}
    res["c_nn_change"]["all"] = {"n": len(changed), "n_changed": sum(res["c_nn_change"][g]["n_changed"]
                                                                     for g in ("N", "P", "S", "new"))}
    # (d) antonym margin: clean pairs move further apart than controls when a clause goes
    delta = {}
    for rel in ("antonym", "duplicate", "deliberate_duplicate", "near_distinct", "unrelated"):
        ps = [p for p in lp.pairs if p.relation == rel and (p.a in classes or p.b in classes)]
        if not ps:
            continue
        f = pair_similarities(full, ps, index, ext_full)[0]
        s_ = pair_similarities(strip, ps, index, ext_strip)[0]
        delta[rel] = s_ - f
    d_ant = delta.get("antonym", np.zeros(0))
    d_syn = np.concatenate([delta.get(r, np.zeros(0)) for r in SYNONYM_RELATIONS])
    d_unr = delta.get("unrelated", np.zeros(0))
    res["d_antonym_margin"] = {
        "mean_delta_antonym": _mean(d_ant), "mean_delta_synonym": _mean(d_syn), "mean_delta_unrelated": _mean(d_unr),
        "n_antonym": int(len(d_ant)), "n_synonym": int(len(d_syn)), "n_unrelated": int(len(d_unr)),
        "margin_vs_synonym": _r(float(np.mean(d_syn) - np.mean(d_ant))) if len(d_ant) and len(d_syn) else None,
        "margin_vs_unrelated": _r(float(np.mean(d_unr) - np.mean(d_ant))) if len(d_ant) and len(d_unr) else None,
        "auc_unrelated_delta_above_antonym_delta": _r(auc(d_unr, d_ant))}
    # (f) minimal pairs
    if minimal and minimal_vecs:
        res["f_minimal_pairs"] = minimal_pair_test(full, minimal, minimal_vecs, index)
    # (h) agreement with persona space
    if persona:
        res["h_persona"] = persona_agreement(full, strip, stems, persona, changed=set(changed))
    # (g) and (i): paraphrase-based, only when the paraphrases exist
    if paraphrases:
        res["g_paraphrase_invariance"] = paraphrase_invariance(full, strip, paraphrases, index, changed)
        res["i_heldout_recovery"] = {"full": gloss_recovery(full, paraphrases, index),
                                     "strip": gloss_recovery(strip, paraphrases, index)}
    return res


def _in_full(full: View, strip: View, i: int) -> np.ndarray:
    """Row ``i`` of the stripped representation, mapped into the full
    representation's space (same model, so the raw embeddings are comparable)."""
    return full.transform(strip.raw[i])


def minimal_pair_test(view: View, minimal: Sequence[dict], vecs: Mapping[str, np.ndarray],
                      index: Mapping[str, int]) -> dict:
    """Criterion (f): "X rather than Y" against "Y rather than X".  A model that
    reads the construction gives two different vectors, each nearer its own
    pole; a bag of words gives near-identical ones (accuracy about 0.5).
    Poles are the traits' own full corpus embeddings; also reported against
    the bare "This means being X." forms."""
    cos_xy_yx, correct_corpus, correct_bare, margins = [], [], [], []
    for m in minimal:
        if m["x"] not in index or m["y"] not in index:
            continue
        xy, yx, xo, yo = (view.transform(vecs[m[k]]) for k in ("xy", "yx", "x_only", "y_only"))
        px, py = view.Z[index[m["x"]]], view.Z[index[m["y"]]]
        cos_xy_yx.append(float(xy @ yx))
        ok1 = (xy @ px > xy @ py) and (yx @ py > yx @ px)
        correct_corpus.append(bool(ok1))
        correct_bare.append(bool((xy @ xo > xy @ yo) and (yx @ yo > yx @ xo)))
        margins.append(float((xy @ px - xy @ py) + (yx @ py - yx @ px)) / 2)
    n = len(cos_xy_yx)
    return {"n": n, "mean_cos_xy_yx": _mean(cos_xy_yx), "accuracy_vs_corpus_poles": _r(float(np.mean(correct_corpus))) if n else None,
            "accuracy_vs_bare_poles": _r(float(np.mean(correct_bare))) if n else None, "mean_margin": _mean(margins)}


def persona_agreement(full: View, strip: View, stems: Sequence[str], persona: dict, *, changed: set) -> dict:
    """Criterion (h): Spearman between pairwise text cosine and pairwise persona
    cosine, for the traits with vectors, with and without the clauses; over all
    pairs and over pairs touching a changed trait."""
    pidx = {s: i for i, s in enumerate(persona["stems"])}
    common = [s for s in stems if s in pidx]
    ci = np.array([stems.index(s) for s in common]) if common else np.zeros(0, int)
    P = persona["M"][[pidx[s] for s in common]]
    P = P / np.linalg.norm(P, axis=1, keepdims=True)
    Pc = P @ P.T
    iu = np.triu_indices(len(common), 1)
    touch = np.array([common[a] in changed or common[b] in changed for a, b in zip(*iu)])
    out = {"n_traits": len(common), "n_pairs": int(len(iu[0])), "n_pairs_touching_changed": int(touch.sum())}
    for name, v in (("full", full), ("strip", strip)):
        Z = v.Z[ci]
        T = Z @ Z.T
        rho, _, _ = spearman(T[iu], Pc[iu])
        rho_t, _, _ = spearman(T[iu][touch], Pc[iu][touch]) if touch.any() else (None, None, 0)
        out[name] = {"spearman_all_pairs": _r(rho), "spearman_pairs_touching_changed": _r(rho_t)}
    return out


def paraphrase_invariance(full: View, strip: View, paraphrases: Mapping[str, np.ndarray], index: Mapping[str, int],
                          changed: Sequence[str]) -> dict:
    """Criterion (g): a paraphrase of a description should move its vector less
    than removing the clause does; otherwise the clause effect is within noise."""
    para_move, clause_move = [], []
    for s in changed:
        if s not in paraphrases:
            continue
        i = index[s]
        para_move.append(1 - float(full.Z[i] @ full.transform(paraphrases[s])))
        clause_move.append(1 - float(full.Z[i] @ _in_full(full, strip, i)))
    n = len(para_move)
    return {"n": n, "mean_paraphrase_distance": _mean(para_move), "mean_clause_distance": _mean(clause_move),
            "frac_clause_moves_more": _r(float(np.mean(np.array(clause_move) > np.array(para_move)))) if n else None}


def cross_model_nn_agreement(views_by_model: Mapping[str, View], subset: Optional[Sequence[int]] = None) -> dict:
    """Criterion (j) building block: the fraction of traits whose nearest
    neighbour agrees between each pair of models (optionally on a subset)."""
    names = sorted(views_by_model)
    out = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ia, ib = views_by_model[a].nn_cos_idx, views_by_model[b].nn_cos_idx
            sel = np.arange(len(ia)) if subset is None else np.asarray(subset, int)
            out[f"{a}~{b}"] = _r(float((ia[sel] == ib[sel]).mean())) if len(sel) else None
    return out


def recommend_contrast(per_variant: Mapping[str, dict], *, n_class_ok_min: float = 0.8) -> dict:
    """Plan 15 §3.5's rule for one model: keep the clauses if the criteria are
    no worse with them, else strip at embedding time.  Each criterion that ran
    votes ``strip``, ``keep`` or ``tie``; the N class must keep its nearest
    neighbours (>= ``n_class_ok_min``) for ``strip`` to be allowed."""
    votes = {}
    c = per_variant
    b = (c.get("b_tasks") or {}).get("all") or {}
    if b:
        f, s = b["full"], b["strip"]
        dv = [(s.get(k) or 0) - (f.get(k) or 0) for k in ("auc_ant_vs_syn", "auc_dup_vs_distinct") if f.get(k) is not None and s.get(k) is not None]
        votes["b"] = _vote(np.mean(dv) if dv else 0.0, 0.01)
    d = c.get("d_antonym_margin") or {}
    if d.get("margin_vs_unrelated") is not None:
        votes["d"] = _vote(d["margin_vs_unrelated"], 0.002)       # antonyms move apart more than controls: the clause pulled them together
    f = c.get("f_minimal_pairs") or {}
    if f.get("accuracy_vs_corpus_poles") is not None:
        acc = f["accuracy_vs_corpus_poles"]
        votes["f"] = "keep" if acc >= 0.8 else ("strip" if acc <= 0.6 else "tie")   # a model that reads 'rather than' can keep it
    h = c.get("h_persona") or {}
    if h.get("full") and h.get("strip") and h["full"].get("spearman_all_pairs") is not None:
        votes["h"] = _vote(h["strip"]["spearman_all_pairs"] - h["full"]["spearman_all_pairs"], 0.005)
    g = c.get("g_paraphrase_invariance") or {}
    if g.get("frac_clause_moves_more") is not None:
        votes["g"] = "tie" if g["frac_clause_moves_more"] < 0.5 else "info"
    j = c.get("j_cross_model") or {}
    if j.get("full") is not None and j.get("strip") is not None:
        votes["j"] = _vote(j["strip"] - j["full"], 0.01)
    e = c.get("e_blinded") or {}
    if e.get("preference_strip_share") is not None:
        votes["e"] = _vote(e["preference_strip_share"] - 0.5, 0.05)
    nc = (c.get("c_nn_change") or {}).get("N") or {}
    n_ok = (nc.get("n_unchanged", 0) / nc["n"]) if nc.get("n") else None
    n_strip = sum(v == "strip" for v in votes.values())
    n_keep = sum(v == "keep" for v in votes.values())
    decision = "strip" if (n_strip > n_keep and (n_ok is None or n_ok >= n_class_ok_min)) else "keep"
    return {"votes": votes, "n_strip": n_strip, "n_keep": n_keep, "n_class_unchanged_share": _r(n_ok),
            "recommendation": decision,
            "rule": "strip only if more criteria favour stripping than keeping and the N class keeps >= 80% of its nearest "
                    "neighbours; otherwise keep (plan 15: keep the clauses if the criteria are no worse with them)"}


def _vote(delta: float, tol: float) -> str:
    if delta > tol:
        return "strip"
    if delta < -tol:
        return "keep"
    return "tie"


# --------------------------------------------------------------------------- blinded comparisons (criterion e)

def blinded_comparisons(full: View, strip: View, *, stems: Sequence[str], labels: Sequence[str],
                        descriptions: Sequence[str], classes: Mapping[str, Optional[str]], n: int = 60,
                        n_for_roger: int = 30, k: int = 5, seed: int = 0) -> list[dict]:
    """The sample for criterion (e): traits whose clause was cut, preferring those
    whose top-``k`` list changed, stratified by class (all N first), each with
    the two top-``k`` lists in a random A/B order; the first ``n_for_roger``
    are the ones Roger marks."""
    rng = random.Random(seed)
    idx = {s: i for i, s in enumerate(stems)}
    cand = []
    for s, c in classes.items():
        if s not in idx:
            continue
        i = idx[s]
        a, b = full.topk(i, k), strip.topk(i, k)
        cand.append((c or "new", s, a, b, a != b))
    order = {"N": 0, "P": 1, "S": 2, "new": 3}
    rng.shuffle(cand)
    cand.sort(key=lambda t: (not t[4], order[t[0]]))
    by_cls = defaultdict(list)
    for t in cand:
        by_cls[t[0]].append(t)
    chosen = list(by_cls["N"])
    rest = [t for t in cand if t[0] != "N"]
    chosen += rest[: max(0, n - len(chosen))]
    out = []
    for q, (c, s, a, b, differs) in enumerate(chosen[:n]):
        flip = rng.random() < 0.5
        lists = {"full": [stems[x] for x in a], "strip": [stems[x] for x in b]}
        A, B = ("strip", "full") if flip else ("full", "strip")
        i = idx[s]
        out.append({"id": q + 1, "stem": s, "label": labels[i], "description": descriptions[i], "class": c,
                    "A": lists[A], "B": lists[B], "key": {"A": A, "B": B}, "lists_differ": differs,
                    "for_roger": q < n_for_roger})
    return out


def comparisons_markdown(items: Sequence[dict], *, labels_of: Mapping[str, str], desc_of: Mapping[str, str],
                         link: callable) -> str:
    """The marks sheet for Roger: the trait, then lists A and B (neighbours with
    their descriptions), and a line to mark A / B / same."""
    lines = []
    for it in items:
        if not it["for_roger"]:
            continue
        lines.append(f"### {it['id']}. {link(it['stem'], it['label'])}\n")
        lines.append(f"{it['description']}\n")
        for side in ("A", "B"):
            lines.append(f"**List {side}**\n")
            for j, s in enumerate(it[side], 1):
                d = desc_of.get(s, "")
                lines.append(f"{j}. {link(s, labels_of.get(s, s))}: {d}")
            lines.append("")
        lines.append("Mark (A / B / same): \n")
    return "\n".join(lines)


def arrangement_linker(arrangement_of: Mapping[str, list]):
    """``f(a, b)`` -> the kind of a recorded arrangement holding both, else ``None``."""
    def link(a: str, b: str) -> Optional[str]:
        for kind, members in arrangement_of.get(a, []):
            if b in members:
                return kind
        return None
    return link


def deliberate_set(lp) -> set:
    return {tuple(sorted((p.a, p.b))) for p in lp.pairs if p.relation == "deliberate_duplicate"}


def most_and_least_novel(view: View, stems: Sequence[str], metric: str, n: int = 10,
                         nn: Optional[tuple[np.ndarray, np.ndarray]] = None) -> dict:
    """The ``n`` most and least novel traits (local score; with ``nn`` given, the
    masked nearest neighbours, e.g. with recorded partners excluded)."""
    if nn is not None:
        nov = (1.0 - nn[1]) if metric == "cos" else -nn[1]
        order = np.argsort(-nov)
        idx = nn[0]
        def row(i):
            return {"stem": stems[i], "score": _r(float(nov[i])), "nearest": stems[int(idx[i])]}
        return {"most": [row(i) for i in order[:n]], "least": [row(i) for i in order[::-1][:n]]}
    nov = view.novelty(metric)
    order = np.argsort(-nov)
    nn = view.nn_cos_idx if metric != "csls" else view.nn_csls_idx
    def row(i):
        return {"stem": stems[i], "score": _r(float(nov[i])), "nearest": stems[int(nn[i])]}
    return {"most": [row(i) for i in order[:n]], "least": [row(i) for i in order[::-1][:n]]}


def counts_summary(values: Iterable[str]) -> dict:
    return dict(Counter(values).most_common())


# --------------------------------------------------------------------------- plots

def plot_nn_histograms(path, *, model: str, representation: str, panels: Sequence[dict], inputs=None,
                       title_extra: str = "", ncols: Optional[int] = None) -> None:
    """Step 7's figure for one model: one panel per space variant, the
    histogram of leave-one-out nearest-neighbour cosine similarity (the bulk;
    filled) and, when given, the same with recorded arrangement partners
    excluded (outline), the labelled anchors as rugs under the axis
    (duplicates, near-distinct, antonyms), and as vertical lines the
    duplicate-recall threshold ``t_hi``, the random-pair threshold ``t_lo``
    and the upper fence of the partner-excluded bulk.  ``panels``:
    ``[{"variant", "nn", "nn_masked"?, "fence"?, "dup", "distinct", "antonym",
    "t_hi", "t_lo"}]``."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from assistant_axis.plot_metadata import png_metadata, suptitle_with_specs

    n = len(panels)
    ncols = min(n, ncols or n)
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.7 * ncols, 4.2 * nrows + 1.4), sharey=False, squeeze=False)
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    axes = axes.ravel()[:n]
    rugs = (("dup", "#c0392b", "labelled duplicates"), ("distinct", "#2e86c1", "near-distinct"),
            ("antonym", "#7d3c98", "recorded antonyms"))
    for ax, p in zip(axes, panels):
        nn = np.asarray(p["nn"])
        vals = [nn] + [np.asarray(p[k]) for k, _, _ in rugs if len(p[k])]
        if p.get("nn_masked") is not None:
            vals.append(np.asarray(p["nn_masked"]))
        lo, hi = min(v.min() for v in vals) - 0.02, max(v.max() for v in vals) + 0.02
        bins = np.linspace(lo, hi, 40)
        ax.hist(nn, bins=bins, color="#9aa7b8", edgecolor="white", label="nearest neighbour")
        if p.get("nn_masked") is not None:
            ax.hist(p["nn_masked"], bins=bins, histtype="step", color="#1f3a5f", lw=1.3,
                    label="nearest, partners excluded")
        ymax = ax.get_ylim()[1]
        for k, (key, color, lab) in enumerate(rugs):
            v = np.asarray(p[key])
            if len(v):
                ax.plot(v, np.full(len(v), -(0.06 + 0.07 * k) * ymax), "|", color=color, ms=8, mew=1.0,
                        clip_on=False, label=lab)
        if p.get("t_hi") is not None:
            ax.axvline(p["t_hi"], color="#c0392b", ls="--", lw=1.2, label="t_hi (95% duplicate recall)")
        if p.get("t_lo") is not None:
            ax.axvline(p["t_lo"], color="#555555", ls=":", lw=1.4, label="t_lo (99% of random pairs)")
        if p.get("fence") is not None:
            ax.axvline(p["fence"], color="#1f3a5f", ls="-.", lw=1.2, label="upper fence, partners excluded")
        ax.set_ylim(-0.27 * ymax, 1.05 * ymax)
        ax.set_yticks([t for t in ax.get_yticks() if 0 <= t <= ymax])
        ax.axhline(0, color="black", lw=0.5)
        ax.set_title(p["variant"], fontsize=11)
        ax.set_xlabel("cosine similarity")
    for ax in axes[::ncols]:
        ax.set_ylabel("traits")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.01))
    title = f"Leave-one-out nearest-neighbour similarity: {model}, {representation}"
    _, top = suptitle_with_specs(fig, title, "rugs under the axis: labelled pairs' own similarities" + title_extra)
    h_in = fig.get_size_inches()[1]
    fig.subplots_adjust(top=top - 0.45 / h_in, bottom=1.1 / h_in, wspace=0.25, hspace=0.45)
    fig.savefig(path, dpi=130, bbox_inches="tight", metadata=png_metadata(title=title, inputs=inputs))
    plt.close(fig)
