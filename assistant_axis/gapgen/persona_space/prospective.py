"""The prospective test (coding_plan_12_persona_space.md § 1, § 7; "Inconsistencies", 9).

The corpus entities with a file and no training vector (*pending*: the entities seeded since the May extraction,
and the current files of the sense-changed renames, whose May vector describes the old sense) are scored now with
the fit on the May vectors, and compared with their actual vectors after the next extraction.  Positions cannot be
compared across the two spaces (every entity is re-extracted under regenerated instructions, and the new pool is
centred and sheared on itself, never on the May mean), so the comparison is on **ranks and names**: the rank
Spearman of the predicted residual against the actual one (the actual residual outside the top N principal
directions of the new pool less the pending entities, as a candidate is scored against the existing ones), the
overlap of the predicted and actual three nearest entities among those the fit knew, top-1 and top-3 name hits, the
AUC of the predicted nearest cosine for an actual nearest cosine of 0.7 or more, and the named pairs of the workstream
plan (cautious / risk-averse / bold, calibrated / overconfident).
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import entity_id

from ..paths import DATA_CANDIDATES, DATA_DIR
from ..persona import load_persona_space
from .calibrate import Calibration
from .fit import Model, predict
from .pool import KINDS, Pool, corpus_docs, pc_basis, pool_from_space, residual_N
from .score import score_vectors

#: The workstream plan's named test pairs (none had a vector in May): each ``(a, b)`` of traits.
NAMED_PAIRS: tuple[tuple[str, str], ...] = (("cautious", "risk_averse"), ("risk_averse", "bold"), ("cautious", "bold"),
                                            ("calibrated", "overconfident"))
#: The actual nearest cosine at or above which a pending entity counts as a duplicate for ``auc_dup``.
DUP_ACTUAL_COS = 0.7


def pending(pool: Pool, data_dir: Path = DATA_DIR) -> list[tuple[str, str]]:
    """``[(kind, stem)]``: every corpus entity with a description (``default`` excluded) that has no training
    vector in ``pool``, sorted by kind and stem."""
    train = set(pool.train_ids)
    out = []
    for k in KINDS:
        for stem, doc in corpus_docs(Path(data_dir), k).items():
            if stem == "default" or not (doc.get("description") or "").strip():
                continue
            if entity_id(stem, k) not in train:
                out.append((k, stem))
    return out


def predict_pending(model: Model, cal: Calibration, pool: Pool, E: np.ndarray, entities: Sequence[tuple[str, str]],
                    *, Ns: Sequence[int] = (), partners: Optional[Mapping[str, str]] = None,
                    fit_id: Optional[str] = None, config_version: Optional[str] = None
                    ) -> tuple[list[dict], np.ndarray]:
    """``(rows, P)``: the pending entities' predictions (``E``: their ``label: description`` embeddings, in
    ``entities`` order) scored as candidates are, one row per entity (§ 6's prospective row)."""
    kinds = [k for k, _ in entities]
    P = predict(model, E, kinds)
    cands = [SimpleNamespace(key=entity_id(s, k), label=s, generators=[]) for k, s in entities]
    scores = score_vectors(P, cands, pool, cal, Ns=Ns, partners=partners, fit_id=fit_id,
                           config_version=config_version)
    rows = []
    for (k, s), sc in zip(entities, scores):
        rows.append({"kind": k, "stem": s, "id": entity_id(s, k), "residual": sc.residual,
                     "residual_pct": sc.residual_pct, "residual_z": sc.residual_z, "residual_by_N": sc.residual_by_N,
                     "nn": [sc.nn["id"], sc.nn["cos"]], "nearest": sc.nearest, "nearest_traits": sc.nearest_traits,
                     "pair_axis": sc.pair_axis, "flag": sc.flag})
    return rows, P


def pending_texts(entities: Sequence[tuple[str, str]], data_dir: Path = DATA_DIR) -> list[str]:
    """``label: description`` (``w20``) for each pending entity, as an existing entity is embedded."""
    from .pool import entity_text
    docs = {k: corpus_docs(Path(data_dir), k) for k in KINDS}
    return [entity_text(k, s, docs[k][s]) for k, s in entities]


def _unit(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    n = np.linalg.norm(X, axis=-1, keepdims=True)
    return X / np.where(n == 0, 1.0, n)


def default_cache_dir(new_vectors_dir: Path) -> Path:
    """Where the new tree's slice cache goes: never ``data/candidates/cache/persona_s6_l25.npz`` itself, which
    holds the May tree's slices."""
    h = hashlib.sha256(str(Path(new_vectors_dir).resolve()).encode("utf-8")).hexdigest()[:12]
    return DATA_CANDIDATES / "cache" / "persona_prospective" / h


def compare(pred_rows: Sequence[Mapping], new_vectors_dir: Path, *, data_dir: Path = DATA_DIR, slot: int = 6,
            layer: int = 25, shear_L: Optional[int] = 3, N: int = 20, cache_dir: Optional[Path] = None,
            predictions: Optional[Mapping[str, np.ndarray]] = None, old_vectors: Optional[Mapping[str, np.ndarray]] = None,
            known_ids: Optional[Sequence[str]] = None, named_pairs: Sequence[tuple[str, str]] = NAMED_PAIRS,
            space: Optional[Mapping] = None) -> dict:
    """The comparison (§ 6) of ``pred_rows`` (``predicted.jsonl``) with the new tree at ``new_vectors_dir``,
    centred and sheared on itself.  ``known_ids``: the entities the fit trained on (the predicted neighbour lists'
    universe; default every new entity that is not pending); ``predictions`` / ``old_vectors``: ``{id: vector}`` for
    the named pairs' predicted cosines; ``space``: a loaded space record instead of reading the tree (tests)."""
    if space is None:
        space = load_persona_space(Path(new_vectors_dir), slot=slot, layer=layer, shear_L=shear_L,
                                   cache_dir=cache_dir or default_cache_dir(new_vectors_dir))
    new = pool_from_space(space, data_dir)
    pred_by_id = {r["id"]: r for r in pred_rows}
    new_train = set(new.train_ids)
    evaluated = [i for i in pred_by_id if i in new_train]
    known = [i for i in (known_ids if known_ids is not None else new.train_ids) if i in new_train and i not in pred_by_id]
    ev_rows = np.array([new.row(i) for i in evaluated], dtype=int)
    rest = np.setdiff1d(np.arange(new.n), ev_rows)
    basis = pc_basis(new.M[rest], N)
    kn_rows = np.array([new.row(i) for i in known], dtype=int)
    out_rows = []
    pr, ac, jac, h1, h3, pc, dup = [], [], [], [], [], [], []
    if len(ev_rows) and len(kn_rows):
        actual_res = residual_N(new.M[ev_rows], basis)
        S = _unit(new.M[ev_rows]) @ _unit(new.M[kn_rows]).T
        for j, eid in enumerate(evaluated):
            order = np.argsort(-S[j], kind="stable")[:3]
            act3 = [known[o] for o in order]
            p = pred_by_id[eid]
            p3 = [a for a, _ in p["nearest"]][:3]
            pr.append(p["residual_by_N"].get(str(N), p["residual"]))
            ac.append(float(actual_res[j]))
            jac.append(len(set(p3) & set(act3)) / len(set(p3) | set(act3)))
            h1.append(bool(p3) and p3[0] == act3[0])
            h3.append(act3[0] in p3)
            pc.append(p["nn"][1])
            dup.append(float(S[j, order[0]]) >= DUP_ACTUAL_COS)
            out_rows.append({"id": eid, "residual_pred": pr[-1], "residual_actual": round(ac[-1], 4),
                             "nearest_pred": p3, "nearest_actual": act3,
                             "nn_cos_actual": round(float(S[j, order[0]]), 4), "nn_cos_pred": p["nn"][1]})
    from scipy.stats import spearmanr

    from .compare import auc
    rho = float(spearmanr(pr, ac)[0]) if len(pr) >= 2 else None
    pos = [c for c, d in zip(pc, dup) if d]
    neg = [c for c, d in zip(pc, dup) if not d]
    named = {}
    for a, b in named_pairs:
        ia, ib = entity_id(a, "traits"), entity_id(b, "traits")
        ra, rb = new.row(ia), new.row(ib)
        act = None
        if ra is not None and rb is not None:
            va, vb = new.M[ra], new.M[rb]
            act = round(float(va @ vb / (np.linalg.norm(va) * np.linalg.norm(vb))), 4)
        pa = (predictions or {}).get(ia, (old_vectors or {}).get(ia))
        pb = (predictions or {}).get(ib, (old_vectors or {}).get(ib))
        prd = None
        if pa is not None and pb is not None:
            prd = round(float(np.dot(pa, pb) / (np.linalg.norm(pa) * np.linalg.norm(pb))), 4)
        named[f"{a}/{b}"] = {"actual_cos": act, "predicted_cos": prd}
    return {"tree": str(new_vectors_dir), "n": len(pred_rows), "n_with_vector": len(evaluated), "n_known": len(known),
            "N": N, "shear_applied": bool(space.get("shear_applied")),
            "rho_residual_rank": None if rho is None or not np.isfinite(rho) else round(rho, 4),
            "nearest3_jaccard_mean": round(float(np.mean(jac)), 4) if jac else None,
            "top1_name_hit": round(float(np.mean(h1)), 4) if h1 else None,
            "top3_name_hit": round(float(np.mean(h3)), 4) if h3 else None,
            "auc_dup": None if auc(pos, neg) is None else round(auc(pos, neg), 4), "n_dup_actual": len(pos),
            "named_pairs": named, "rows": out_rows}
