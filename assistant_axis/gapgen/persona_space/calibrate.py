"""Reading a predicted residual and a predicted vector's neighbours (coding_plan_12_persona_space.md § 1, § 5).

The regression pulls every prediction toward the mean (*shrinkage*), so a predicted residual is smaller than the
actual one and is never read raw: a candidate's ``residual_pct`` is its **percentile among the held-out predicted
residuals of the training entities** at the chosen N (the *calibration percentile*: there the shrinkage is the same),
with ``residual_z`` beside it.  The quantile tables (every 5th percentile) come from the cross-validation.

Flags (:func:`flag`): **duplicate_like** when the cosine to the nearest existing entity is at least
``dup_threshold``, by default the median held-out cosine between a training entity's prediction and its own vector
(the candidate is as close to an existing entity as a held-out entity's prediction is to itself, half the time);
else **novel_like** when ``residual_pct >= novel_pct`` (0.80); else **ordinary**.  Both thresholds are Roger's to
move at the pilot gate; ``thresholds_set_by`` says who set them.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping, Optional

import numpy as np

FLAGS = ("duplicate_like", "novel_like", "ordinary")
QUANTILE_LEVELS = tuple(round(x, 2) for x in np.linspace(0.0, 1.0, 21))
DEFAULT_NOVEL_PCT = 0.80
#: ``novel_vs_covered``: M3 covered the row and its residual percentile is at least this (§ 6).
NOVEL_VS_COVERED_PCT = 0.90
#: ``cover_questioned``: the cosine to M3's covering trait is below this percentile of the held-out self-cosines.
COVER_QUESTIONED_LEVEL = 0.10
PLAN_DEFAULT = "plan default"


def quantiles(x: np.ndarray) -> list[float]:
    return [round(float(v), 6) for v in np.quantile(np.asarray(x, dtype=np.float64), QUANTILE_LEVELS)]


@dataclass
class Calibration:
    fit_id: str
    N: int
    alpha: float
    residual_pred_quantiles: list
    residual_true_quantiles: list
    self_cos_quantiles: list
    nn_cos_pred_quantiles: list
    dup_threshold: float
    novel_pct: float
    config_version: str
    n_train: int
    residual_pred_mean: float = 0.0
    residual_pred_sd: float = 1.0
    cover_questioned_cos: float = 0.0
    novel_vs_covered_pct: float = NOVEL_VS_COVERED_PCT
    thresholds_set_by: str = PLAN_DEFAULT
    residual_pred_quantiles_by_N: dict = field(default_factory=dict)
    residual_true_quantiles_by_N: dict = field(default_factory=dict)
    #: the share of held-out training entities whose prediction is at or above ``dup_threshold`` to *another* entity:
    #: the rate at which the flag would call an existing entity duplicate-like (the flag's base rate)
    dup_base_rate: Optional[float] = None
    #: :func:`overlap_check`'s table (the overlap test's pairs by rubric-A reading), when the fit had them
    overlap_check: Optional[dict] = None
    feature_source: dict = field(default_factory=dict)
    levels: list = field(default_factory=lambda: list(QUANTILE_LEVELS))

    def as_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Mapping) -> "Calibration":
        d = d.get("result", d)
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})

    def residual_quantiles_at(self, N: int) -> list:
        return self.residual_pred_quantiles_by_N.get(str(N)) or (self.residual_pred_quantiles if N == self.N else [])


def from_cv(cv, N: Optional[int] = None, *, fit_id: str, config_version: str, alpha: Optional[float] = None,
            dup_threshold: Optional[float] = None, novel_pct: float = DEFAULT_NOVEL_PCT,
            thresholds_set_by: str = PLAN_DEFAULT, feature_source: Optional[Mapping] = None) -> Calibration:
    """The calibration of a :class:`~assistant_axis.gapgen.persona_space.fit.CV` at its chosen alpha (or
    ``alpha``) and N (or ``N``)."""
    alpha = float(cv.alpha if alpha is None else alpha)
    N = int(cv.N if N is None else N)
    h = cv.heldout[alpha]
    rp = h["res_pred"][N]
    dup = float(np.median(h["cos"])) if dup_threshold is None else float(dup_threshold)
    return Calibration(
        fit_id=fit_id, N=N, alpha=alpha, residual_pred_quantiles=quantiles(rp),
        residual_true_quantiles=quantiles(cv.res_true[N]), self_cos_quantiles=quantiles(h["cos"]),
        nn_cos_pred_quantiles=quantiles(h["nn_cos"]), dup_threshold=round(dup, 4), novel_pct=float(novel_pct),
        config_version=config_version, n_train=int(len(rp)), residual_pred_mean=float(np.mean(rp)),
        residual_pred_sd=float(np.std(rp, ddof=1)) if len(rp) > 1 else 1.0,
        cover_questioned_cos=round(float(np.quantile(h["cos"], COVER_QUESTIONED_LEVEL)), 4),
        dup_base_rate=round(float(np.mean(np.asarray(h["nn_cos"]) >= round(dup, 4))), 4),
        thresholds_set_by=thresholds_set_by,
        residual_pred_quantiles_by_N={str(n): quantiles(h["res_pred"][n]) for n in sorted(h["res_pred"])},
        residual_true_quantiles_by_N={str(n): quantiles(cv.res_true[n]) for n in sorted(cv.res_true)},
        feature_source=dict(feature_source or {}))


def _pct(x, q: list, levels: list) -> np.ndarray:
    q = np.asarray(q, dtype=np.float64)
    lv = np.asarray(levels, dtype=np.float64)
    # strictly increasing knots for interp: drop repeated quantile values (keep the middle level of a run)
    xs, ys = [], []
    i = 0
    while i < len(q):
        j = i
        while j + 1 < len(q) and q[j + 1] <= q[i]:
            j += 1
        xs.append(q[i])
        ys.append((lv[i] + lv[j]) / 2)
        i = j + 1
    return np.clip(np.interp(np.asarray(x, dtype=np.float64), xs, ys), 0.0, 1.0)


def residual_pct(x, cal: Calibration, N: Optional[int] = None):
    """The calibration percentile of a predicted residual ``x`` (a number or an array) at ``N`` (default the
    calibration's): the share of held-out predicted residuals below it, read off the quantile table; monotone, 0.5 at
    the median, clipped to [0, 1]."""
    q = cal.residual_quantiles_at(int(N or cal.N))
    if not q:
        raise ValueError(f"no quantile table at N = {N} in the calibration")
    out = _pct(x, q, cal.levels)
    return float(out) if np.ndim(x) == 0 else out


def residual_z(x, cal: Calibration):
    """``(x - mean) / sd`` of the held-out predicted residuals at the calibration's N."""
    out = (np.asarray(x, dtype=np.float64) - cal.residual_pred_mean) / (cal.residual_pred_sd or 1.0)
    return float(out) if np.ndim(x) == 0 else out


def flag(nn_cos: float, residual_pct_: float, cal: Calibration) -> str:
    """``duplicate_like`` (nearest cosine at or above ``dup_threshold``), else ``novel_like`` (``residual_pct`` at or
    above ``novel_pct``), else ``ordinary``."""
    if nn_cos is not None and nn_cos >= cal.dup_threshold:
        return "duplicate_like"
    if residual_pct_ is not None and residual_pct_ >= cal.novel_pct:
        return "novel_like"
    return "ordinary"


def overlap_check(cv, pool, readings, *, dup_threshold: float, alpha: Optional[float] = None) -> dict:
    """Where the duplicate threshold sits against M3's own concept readings (plan 12 § 1: the overlap test's pairs
    are calibration data, not training data).  ``readings``: ``[{"target", "listed", "reading"}]``, trait stems and
    a rubric-A answer (0-4, ``opposite``, ``unsure``).  For every pair whose two traits train, the cosine of the
    target's **held-out prediction** with the listed trait's actual vector (what a candidate that duplicates the
    listed trait would show) and the actual-actual cosine, by reading: ``{reading: {"n", "median_pred_cos",
    "median_actual_cos", "share_pred_at_or_above_dup"}}``."""
    from collections import defaultdict

    from assistant_axis.entity_id import entity_id
    alpha = float(cv.alpha if alpha is None else alpha)
    P = cv.heldout[alpha]["P"]
    pos = {eid: j for j, eid in enumerate(cv.ids)}
    Y = pool.M[pool.train_idx]

    def cos(a, b):
        return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-300))
    by = defaultdict(list)
    for r in readings:
        t, li = entity_id(r["target"], "traits"), entity_id(r["listed"], "traits")
        if t in pos and li in pos:
            by[str(r["reading"])].append((cos(P[pos[t]], Y[pos[li]]), cos(Y[pos[t]], Y[pos[li]])))
    order = ["4", "3", "2", "1", "0", "opposite", "unsure"]
    out = {}
    for k in sorted(by, key=lambda x: order.index(x) if x in order else 99):
        pc = np.array([x for x, _ in by[k]])
        ac = np.array([y for _, y in by[k]])
        out[k] = {"n": int(len(pc)), "median_pred_cos": round(float(np.median(pc)), 4),
                  "median_actual_cos": round(float(np.median(ac)), 4),
                  "share_pred_at_or_above_dup": round(float(np.mean(pc >= dup_threshold)), 4)}
    return out
