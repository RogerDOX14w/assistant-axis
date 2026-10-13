"""Scoring registry candidates in persona space (coding_plan_12_persona_space.md § 5, § 6; decision 1a).

The candidates are the registry rows M3 takes (:func:`assistant_axis.gapgen.novelty_runner.candidate_from_row`: a
``trait`` verdict with a gloss; ``holding`` for the states and physical passes' rows), embedded as ``label: gloss``
cut to 20 words (``novelty.query_text(..., query_form="label_gloss")``), the same form as a corpus entity's
``label: description``.  Each predicted vector is scored against the training entities of the pool: its nearest
three (traits and roles together, ``name|T`` / ``name|R``), its nearest three traits, the energy outside the top N
principal directions of the pool for every N of the sweep, the calibration percentile and z-score at the chosen N,
the position along the nearest trait's clean-pair axis when its partner has a vector (+1 at the trait, -1 at its
partner), and the flag.

The ``persona`` block (``registry.BLOCKS``, decision 1a) holds these and M3's decision beside them, never a vector,
and is written by :func:`apply_blocks` without touching any other field of the row (``novelty`` stays as it was).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.entity_id import entity_id

from .. import novelty as NV
from ..novelty_runner import M3Candidate, candidate_from_row
from .calibrate import Calibration, flag as flag_of, residual_pct, residual_z
from .pool import REPRESENTATION, Pool, pc_basis, residual_N

PERSONA_BLOCK_VERSION = 1
#: The ``persona`` block's fields, in order (§ 6).
BLOCK_FIELDS: tuple[str, ...] = ("version", "batch_id", "fit_id", "config_version", "N", "residual", "residual_pct",
                                 "residual_z", "nn", "nearest", "pair_axis", "flag", "m3_decision", "m3_listed_first",
                                 "disagreement", "reading", "at")
#: The fields a ``scores.jsonl`` row adds to the block's.
ROW_FIELDS: tuple[str, ...] = ("key", "label", "generators", "residual_by_N", "nn_cos_by_kind", "nearest_traits",
                               "m3_covered_by", "m3_cosine", "cos_to_covered_by", "holding")
DISAGREEMENTS = ("dup_vs_new", "cover_questioned", "novel_vs_covered")


def _unit(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    n = np.linalg.norm(X, axis=-1, keepdims=True)
    return X / np.where(n == 0, 1.0, n)


def candidates(rows: Mapping[str, Mapping], *, run: Optional[Sequence[tuple[str, str]]] = None,
               keys: Optional[Sequence[str]] = None, all_rows: bool = False,
               holding: Optional[str] = None) -> tuple[list[M3Candidate], dict]:
    """The rows to score, exactly as M3 takes them (:func:`candidate_from_row`, with ``holding`` for a pass's rows),
    from ``run`` (``[(generator, run_id)]``), ``keys`` or every row (``all_rows``); and why the others were left out.
    Exactly one of the three selections."""
    from ..registry import has_source
    if sum(x is not None and x is not False for x in (run, keys, all_rows or None)) != 1:
        raise ValueError("give exactly one of run, keys, all_rows")
    if keys is not None:
        missing = [k for k in keys if k not in rows]
        if missing:
            raise KeyError(f"not in the registry: {', '.join(missing[:10])}")
        sel = [rows[k] for k in keys]
    elif run is not None:
        sel = [r for k, r in sorted(rows.items()) if any(has_source(r, g, rid) for g, rid in run)]
    else:
        sel = [rows[k] for k in sorted(rows)]
    out, skipped = [], {}
    for r in sel:
        c, why = candidate_from_row(r, holding=holding) if holding else candidate_from_row(r)
        if c is None:
            skipped[why] = skipped.get(why, 0) + 1
            continue
        out.append(c)
    return out, skipped


def candidate_texts(cands: Iterable, representation: str = REPRESENTATION) -> list[str]:
    """``label: gloss`` in ``representation`` (``w20``): what a candidate is embedded as."""
    return [NV.query_text(c.label, c.gloss, query_form="label_gloss", representation=representation) for c in cands]


@dataclass
class PersonaScore:
    key: str
    label: str
    generators: list
    N: int
    residual: float
    residual_by_N: dict
    residual_pct: float
    residual_z: float
    nn: dict                      # {"id", "kind", "cos"}: the nearest training entity
    nearest: list                 # [[id, cos]] x 3, traits and roles together
    nearest_traits: list          # [[id, cos]] x 3, traits only
    nn_cos_by_kind: dict          # {"T": cos, "R": cos}
    pair_axis: Optional[dict]
    flag: str
    fit_id: str
    config_version: str

    def as_dict(self) -> dict:
        return asdict(self)


def pair_axis_position(p: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """``((p - (a + b) / 2) . d) / (|a - b| / 2)`` with ``d = (a - b) / |a - b|``: +1 at ``a``, -1 at ``b``, 0 at the
    midpoint."""
    diff = np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64)
    norm = float(np.linalg.norm(diff))
    if norm == 0:
        return 0.0
    mid = (np.asarray(a, dtype=np.float64) + np.asarray(b, dtype=np.float64)) / 2
    return float(((np.asarray(p, dtype=np.float64) - mid) @ (diff / norm)) / (norm / 2))


def score_vectors(P: np.ndarray, cands: Sequence, pool: Pool, cal: Calibration, *, Ns: Sequence[int] = (),
                  partners: Optional[Mapping[str, str]] = None, basis: Optional[np.ndarray] = None,
                  fit_id: Optional[str] = None, config_version: Optional[str] = None, top: int = 3
                  ) -> list[PersonaScore]:
    """Score predicted vectors ``P`` (one row per candidate) against the training entities of ``pool``.  ``Ns``: the
    sweep (the calibration's N is always included); ``partners``: :func:`pool.pair_partners`; ``basis``: the pool's
    top principal directions (computed when not given)."""
    P = np.asarray(P, dtype=np.float64)
    if len(P) != len(cands):
        raise ValueError(f"{len(P)} vectors for {len(cands)} candidates")
    Ns = sorted(set(int(n) for n in Ns) | {int(cal.N)})
    if basis is None or len(basis) < max(Ns):
        basis = pc_basis(pool.M, max(Ns))
    res = {N: residual_N(P, basis[:N]) for N in Ns}
    tr = np.asarray(pool.train_idx)
    ids = [pool.ids[i] for i in tr]
    is_role = np.array([pool.kinds[i] == "roles" for i in tr])
    S = _unit(P) @ _unit(pool.M[tr]).T
    pct = residual_pct(res[cal.N], cal)
    z = residual_z(res[cal.N], cal)
    partners = partners or {}
    out = []
    for i, c in enumerate(cands):
        s = S[i]
        order = np.argsort(-s, kind="stable")
        near = [[ids[j], round(float(s[j]), 4)] for j in order[:top]]
        t_order = [j for j in order if not is_role[j]][:top]
        r_order = [j for j in order if is_role[j]][:1]
        near_t = [[ids[j], round(float(s[j]), 4)] for j in t_order]
        j0 = int(order[0])
        nn = {"id": ids[j0], "kind": "roles" if is_role[j0] else "traits", "cos": round(float(s[j0]), 4)}
        by_kind = {"T": near_t[0][1] if near_t else None, "R": round(float(s[r_order[0]]), 4) if r_order else None}
        axis = None
        if near_t:
            a_id = near_t[0][0]
            b_id = partners.get(a_id)
            if b_id is not None and pool.row(b_id) is not None:
                pos = pair_axis_position(P[i], pool.M[pool.row(a_id)], pool.M[pool.row(b_id)])
                axis = {"a": a_id, "b": b_id, "position": round(pos, 3)}
        pc = float(np.atleast_1d(pct)[i])
        out.append(PersonaScore(
            key=c.key, label=c.label, generators=list(getattr(c, "generators", []) or []), N=int(cal.N),
            residual=round(float(res[cal.N][i]), 4), residual_by_N={str(N): round(float(res[N][i]), 4) for N in Ns},
            residual_pct=round(pc, 4), residual_z=round(float(np.atleast_1d(z)[i]), 3), nn=nn, nearest=near,
            nearest_traits=near_t, nn_cos_by_kind=by_kind, pair_axis=axis, flag=flag_of(nn["cos"], pc, cal),
            fit_id=fit_id or cal.fit_id, config_version=config_version or cal.config_version))
    return out


def cos_to(P_row: np.ndarray, pool: Pool, eid: str) -> Optional[float]:
    """The cosine of one predicted vector with a pool row (``None`` when ``eid`` has no row)."""
    j = pool.row(eid)
    if j is None:
        return None
    a, b = np.asarray(P_row, dtype=np.float64), pool.M[j]
    return round(float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-300)), 4)


def m3_view(row: Mapping) -> dict:
    """M3's reading of a registry row, as the block and the comparison need it: ``decision``, ``covered_by``, the
    first listed trait (rank 1) and its text cosine."""
    nv = row.get("novelty") or {}
    listed = nv.get("listed") or []
    first = next((x for x in listed if x.get("rank") == 1), listed[0] if listed else None)
    return {"decision": nv.get("decision"), "covered_by": nv.get("covered_by"),
            "listed_first": (first or {}).get("stem"), "cosine": (first or {}).get("cosine"),
            "run_id": nv.get("run_id")}


def score_rows(scores: Sequence[PersonaScore], P: np.ndarray, rows: Mapping[str, Mapping], pool: Pool, *,
               batch_id: str, at: str) -> list[dict]:
    """``scores.jsonl``'s rows: each score's block fields (``disagreement`` and ``reading`` null until
    :mod:`compare` and :mod:`judge` fill them) plus the row fields (§ 6)."""
    out = []
    for i, s in enumerate(scores):
        reg = rows.get(s.key) or {}
        m3 = m3_view(reg)
        cov = m3["covered_by"]
        cov_cos = cos_to(P[i], pool, entity_id(cov, "traits")) if cov else None
        d = {"version": PERSONA_BLOCK_VERSION, "batch_id": batch_id, "fit_id": s.fit_id,
             "config_version": s.config_version, "N": s.N, "residual": s.residual, "residual_pct": s.residual_pct,
             "residual_z": s.residual_z, "nn": {"id": s.nn["id"], "cos": s.nn["cos"]}, "nearest": s.nearest,
             "pair_axis": s.pair_axis, "flag": s.flag, "m3_decision": m3["decision"],
             "m3_listed_first": m3["listed_first"], "disagreement": None, "reading": None, "at": at,
             "key": s.key, "label": s.label, "generators": s.generators, "residual_by_N": s.residual_by_N,
             "nn_cos_by_kind": s.nn_cos_by_kind, "nearest_traits": s.nearest_traits, "m3_covered_by": cov,
             "m3_cosine": m3["cosine"], "cos_to_covered_by": cov_cos, "holding": reg.get("holding")}
        out.append(d)
    return out


def persona_block(score: Any, batch_id: Optional[str] = None, **overrides) -> dict:
    """The ``persona`` block of § 6 from a ``scores.jsonl`` row (or a :class:`PersonaScore` with the M3 fields given
    as keywords): exactly :data:`BLOCK_FIELDS`, no vector."""
    if isinstance(score, PersonaScore):
        d = score.as_dict()
        d["nn"] = {"id": score.nn["id"], "cos": score.nn["cos"]}
        d.setdefault("version", PERSONA_BLOCK_VERSION)
        for k in ("m3_decision", "m3_listed_first", "disagreement", "reading", "at"):
            d.setdefault(k, None)
    else:
        d = dict(score)
    d.update(overrides)
    if batch_id is not None:
        d["batch_id"] = batch_id
    d["version"] = d.get("version") or PERSONA_BLOCK_VERSION
    missing = [k for k in BLOCK_FIELDS if k not in d]
    if missing:
        raise ValueError(f"persona block is missing {missing}")
    return {k: d[k] for k in BLOCK_FIELDS}


def apply_blocks(registry, rows: Sequence[Mapping], batch_id: str, *, readings: Optional[Mapping[str, Mapping]] = None,
                 missing: Optional[list] = None, now: Optional[str] = None) -> int:
    """Write each row's ``persona`` block to ``registry`` (decision 1a), the block replaced whole and every other
    field of the row left as it was; ``readings`` (``{key: reading}``, decision 2b) fills the ``reading`` field.
    Idempotent: a row whose block is already this one is not written again.  Keys the registry does not have are
    skipped and appended to ``missing``.  Returns the number of rows written."""
    readings = readings or {}
    with registry.locked():
        cur = registry._fold_unlocked()
        updates: dict[str, dict] = {}
        for r in rows:
            if r.get("batch_id") != batch_id:
                raise ValueError(f"{r.get('key')}: a row of batch {r.get('batch_id')!r}, not {batch_id!r}")
            key = r["key"]
            if key not in cur:
                if missing is not None:
                    missing.append(key)
                continue
            block = persona_block(r)
            if key in readings:
                block["reading"] = readings[key]
            if cur[key].get("persona") == block:
                continue
            updates[key] = {"persona": block}
        if updates:
            registry.update_many(updates, now=now, merge_blocks=False)
    return len(updates)
