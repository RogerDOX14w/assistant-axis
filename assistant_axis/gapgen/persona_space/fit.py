"""The map from a description's embedding to its persona vector (coding_plan_12_persona_space.md § 1, § 5).

**Ridge regression** (least squares with a penalty ``alpha`` on the coefficients' size, the intercept unpenalised)
from the unit embedding plus a 0/1 role column (the *kind covariate*) to the full centred, sheared 5,120-d vector,
on the training rows of the pool (traits and roles together).  Solved in closed form, in the dual when there are
fewer rows than features, exactly as scikit-learn's ``Ridge(alpha)`` solves it (the test checks the two agree), so
that two fits on the same inputs give the same bytes.

**Cross-validation** on arrangement-grouped folds (``GroupKFold``, every row of a group in one fold;
:func:`assistant_axis.gapgen.persona_space.pool.fold_groups`), per alpha: the held-out prediction of every training
row, its cosine to the row's actual vector, its rank among the actual vectors (top-1 / top-5 recovery), the per-PC
R² on the whole pool's top 64 principal components, and for every N of the sweep the energy outside the top N
directions (``residual_N``) of the actual and the predicted vector, on the fold's own basis (the pool less the
held-out rows, as a candidate is scored on a basis it is not in), with the Spearman correlation between the two.
Beside it the kNN baseline (the cosine-weighted mean of the k nearest training vectors by embedding cosine).

:func:`choose_alpha`: the largest held-out median cosine wins; alphas within ``tie_window`` (0.01) of it tie, and a
tie goes to the smaller alpha.  :func:`choose_N`: the largest Spearman wins; Ns within ``tie_window`` (0.02) of it
tie, and a tie goes to the N nearest ``prefer`` (20), then to the higher Spearman.  Alpha is chosen on the same
grouped folds that report it (not nested): five values, a small optimism.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

import numpy as np

from .pool import Pool, pc_basis, residual_N, spectrum

#: The model file's format (``save_model`` / ``load_model``).
MODEL_FORMAT = 1


@dataclass(frozen=True)
class FitConfig:
    alphas: tuple = (0.03, 0.1, 0.3, 1.0, 3.0)
    n_folds: int = 5
    Ns: tuple = (12, 16, 20, 24, 28, 32)
    knn_k: int = 5
    knn_ks: tuple = (1, 3, 5, 10)
    n_report_pcs: int = 64
    seed: int = 0
    shuffle: bool = False
    alpha_tie_window: float = 0.01
    n_tie_window: float = 0.02
    prefer_N: int = 20

    def as_dict(self) -> dict:
        return {k: (list(v) if isinstance(v, tuple) else v) for k, v in asdict(self).items()}


def _unit(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=np.float64)
    n = np.linalg.norm(X, axis=-1, keepdims=True)
    return X / np.where(n == 0, 1.0, n)


def role_column(kinds: Sequence[str]) -> np.ndarray:
    """1 for a role (``roles``, ``role``, ``R``), 0 for a trait."""
    out = []
    for k in kinds:
        k = str(k).lower()
        if k in ("roles", "role", "r"):
            out.append(1.0)
        elif k in ("traits", "trait", "t"):
            out.append(0.0)
        else:
            raise ValueError(f"unknown kind {k!r}")
    return np.array(out, dtype=np.float64)


def features(E: np.ndarray, kinds: Sequence[str]) -> np.ndarray:
    """The regression's inputs: the embeddings as unit rows, plus one column, 1 for a role and 0 for a trait."""
    E = _unit(np.atleast_2d(E))
    rc = role_column(kinds)
    if len(rc) != len(E):
        raise ValueError(f"{len(E)} embeddings for {len(rc)} kinds")
    return np.hstack([E, rc[:, None]])


def ridge(X: np.ndarray, Y: np.ndarray, alpha: float) -> tuple[np.ndarray, np.ndarray]:
    """``(coef (d, m), intercept (m,))`` minimising ``|Y - X coef - b|^2 + alpha |coef|^2`` (``b`` unpenalised):
    scikit-learn's ``Ridge(alpha, fit_intercept=True)``, in the dual when ``n <= d``."""
    from scipy.linalg import solve
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    xm, ym = X.mean(axis=0), Y.mean(axis=0)
    Xc, Yc = X - xm, Y - ym
    n, d = Xc.shape
    if n <= d:
        K = Xc @ Xc.T
        K[np.diag_indices(n)] += alpha
        W = Xc.T @ solve(K, Yc, assume_a="pos")
    else:
        G = Xc.T @ Xc
        G[np.diag_indices(d)] += alpha
        W = solve(G, Xc.T @ Yc, assume_a="pos")
    return W, ym - xm @ W


@dataclass
class Model:
    coef: np.ndarray          # (d + 1, 5120) float32: the embedding dimensions, then the role column
    intercept: np.ndarray     # (5120,) float32
    alpha: float
    kinds_seen: list
    n_train: int
    ids: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def feature_dim(self) -> int:
        return int(self.coef.shape[0])


def fit_final(pool: Pool, E: np.ndarray, alpha: float, *, meta: Optional[Mapping] = None) -> Model:
    """The model on every training row of ``pool`` (``E``: their embeddings, in ``pool.train_idx`` order)."""
    kinds = pool.train_kinds
    X = features(E, kinds)
    W, b = ridge(X, pool.M[pool.train_idx], alpha)
    return Model(coef=W.astype(np.float32), intercept=b.astype(np.float32), alpha=float(alpha),
                 kinds_seen=sorted(set(kinds)), n_train=len(kinds), ids=list(pool.train_ids), meta=dict(meta or {}))


def model_sha256(model: Model) -> str:
    """The sha256 of the model's arrays (coefficients, then intercept): the same for a rebuilt model, whatever its
    file's metadata."""
    import hashlib
    h = hashlib.sha256()
    h.update(np.ascontiguousarray(model.coef).tobytes())
    h.update(np.ascontiguousarray(model.intercept).tobytes())
    return h.hexdigest()


def predict(model: Model, E: np.ndarray, kinds: Sequence[str]) -> np.ndarray:
    """Predicted persona vectors ``(n, 5120)`` float32 for embeddings ``E`` of entities of ``kinds``."""
    X = features(E, kinds).astype(np.float32)
    if X.shape[1] != model.feature_dim:
        raise ValueError(f"{X.shape[1]} features for a model fitted on {model.feature_dim}")
    return X @ model.coef + model.intercept


def save_model(model: Model, path: Path) -> Path:
    """``model.npz`` (git-ignored; rebuilt by ``persona_novelty.py fit`` in seconds)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"format": MODEL_FORMAT, "alpha": model.alpha, "kinds_seen": model.kinds_seen, "n_train": model.n_train,
            "ids": model.ids, "meta": model.meta}
    tmp = path.with_name(path.name + ".tmp.npz")
    np.savez(tmp, coef=model.coef, intercept=model.intercept, meta=json.dumps(meta))
    tmp.replace(path)
    return path


def load_model(path: Path) -> Model:
    with np.load(Path(path), allow_pickle=False) as z:
        meta = json.loads(str(z["meta"]))
        if meta.get("format") != MODEL_FORMAT:
            raise ValueError(f"{path}: model format {meta.get('format')}, expected {MODEL_FORMAT}")
        return Model(coef=z["coef"].copy(), intercept=z["intercept"].copy(), alpha=float(meta["alpha"]),
                     kinds_seen=list(meta["kinds_seen"]), n_train=int(meta["n_train"]), ids=list(meta["ids"]),
                     meta=dict(meta.get("meta") or {}))


# --------------------------------------------------------------------------- cross-validation

@dataclass
class CV:
    """The cross-validation record.  ``summary[alpha]``: the JSON-able figures of § 6's ``cv.json``;
    ``heldout[alpha]``: per-row arrays (``cos``, ``rank``, ``nn_cos``, ``nn_kind``, ``res_pred`` by N); ``res_true``:
    the actual residual of every training row by N, on its fold's basis."""
    cfg: FitConfig
    ids: list
    kinds: list
    groups: list
    summary: dict
    heldout: dict
    res_true: dict
    knn_cos_by_k: dict
    spectrum: dict
    alpha: float = 0.0
    N: int = 0
    alt: dict = field(default_factory=dict)

    @property
    def n_rows(self) -> int:
        return len(self.ids)

    @property
    def n_groups(self) -> int:
        return len(set(self.groups))


def _r2(true: np.ndarray, pred: np.ndarray) -> np.ndarray:
    ss_res = ((true - pred) ** 2).sum(axis=0)
    ss_tot = ((true - true.mean(axis=0)) ** 2).sum(axis=0)
    return 1.0 - ss_res / np.where(ss_tot == 0, 1.0, ss_tot)


def _spearman(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    from scipy.stats import spearmanr
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return None
    r = spearmanr(a, b)[0]
    return None if not np.isfinite(r) else float(r)


def folds_for(groups: Sequence[str], n_folds: int, *, shuffle: bool = False, seed: int = 0) -> list:
    from sklearn.model_selection import GroupKFold
    g = np.asarray(groups)
    kf = GroupKFold(n_splits=n_folds, shuffle=shuffle, random_state=seed if shuffle else None)
    return [(tr, te) for tr, te in kf.split(np.zeros(len(g)), groups=g)]


def cross_validate(pool: Pool, E: np.ndarray, groups: Sequence[str], cfg: FitConfig = FitConfig(), *,
                   E_alt: Optional[np.ndarray] = None, alt_rows: Optional[Sequence[int]] = None,
                   alt_name: str = "alt") -> CV:
    """§ 5's cross-validation.  ``E``: the training rows' embeddings (``pool.train_idx`` order); ``groups``: their
    fold groups (the same order).  ``E_alt`` / ``alt_rows``: optional other texts for some training rows (positions
    into the training rows), predicted with the fold model that held their row out (the gloss-side check)."""
    tr_idx = np.asarray(pool.train_idx)
    kinds = [pool.kinds[i] for i in tr_idx]
    X = features(E, kinds)
    Y = pool.M[tr_idx]
    Yu = _unit(Y)
    n = len(tr_idx)
    groups = np.asarray(groups)
    if len(groups) != n or len(X) != n:
        raise ValueError(f"{len(X)} embeddings and {len(groups)} groups for {n} training rows")
    folds = folds_for(groups, cfg.n_folds, shuffle=cfg.shuffle, seed=cfg.seed)
    others = np.setdiff1d(np.arange(pool.n), tr_idx)
    basis64 = pc_basis(pool.M, cfg.n_report_pcs)
    Nmax = max(cfg.Ns)
    fold_bases = []
    res_true = {N: np.zeros(n) for N in cfg.Ns}
    for tr, te in folds:
        rows = np.concatenate([tr_idx[tr], others])
        B = pc_basis(pool.M[rows], Nmax)
        fold_bases.append(B)
        for N in cfg.Ns:
            res_true[N][te] = residual_N(Y[te], B[:N])
    is_role = np.array([k == "roles" for k in kinds])
    summary, heldout = {}, {}
    alt = {}
    for alpha in cfg.alphas:
        P = np.zeros_like(Y)
        Palt = None if E_alt is None else np.zeros((len(E_alt), Y.shape[1]))
        res_pred = {N: np.zeros(n) for N in cfg.Ns}
        for (tr, te), B in zip(folds, fold_bases):
            W, b = ridge(X[tr], Y[tr], alpha)
            P[te] = X[te] @ W + b
            for N in cfg.Ns:
                res_pred[N][te] = residual_N(P[te], B[:N])
            if E_alt is not None:
                te_set = set(te.tolist())
                sel = [j for j, r in enumerate(alt_rows) if r in te_set]
                if sel:
                    Xa = features(np.asarray(E_alt)[sel], [kinds[alt_rows[j]] for j in sel])
                    Palt[sel] = Xa @ W + b
        Pu = _unit(P)
        S = Pu @ Yu.T
        own = S[np.arange(n), np.arange(n)]
        rank = (S > own[:, None]).sum(axis=1)
        S_other = S.copy()
        S_other[np.arange(n), np.arange(n)] = -np.inf
        nn_j = S_other.argmax(axis=1)
        nn_cos = S_other[np.arange(n), nn_j]
        r2 = _r2(Y @ basis64.T, P @ basis64.T)
        rho = {int(N): _spearman(res_true[N], res_pred[N]) for N in cfg.Ns}
        rho_t = {int(N): _spearman(res_true[N][~is_role], res_pred[N][~is_role]) for N in cfg.Ns}
        summary[float(alpha)] = {
            "median_cos": float(np.median(own)), "median_cos_traits": float(np.median(own[~is_role])),
            "median_cos_roles": float(np.median(own[is_role])) if is_role.any() else None,
            "top1": float((rank == 0).mean()), "top5": float((rank < 5).mean()),
            "top1_traits": float((rank[~is_role] == 0).mean()), "top5_traits": float((rank[~is_role] < 5).mean()),
            "top1_roles": float((rank[is_role] == 0).mean()) if is_role.any() else None,
            "top5_roles": float((rank[is_role] < 5).mean()) if is_role.any() else None,
            "per_pc_r2": [round(float(x), 4) for x in r2],
            "rho_by_N": {str(N): v for N, v in rho.items()},
            "rho_by_N_traits": {str(N): v for N, v in rho_t.items()},
            "residual_true_median_by_N": {str(N): float(np.median(res_true[N])) for N in cfg.Ns},
            "residual_pred_median_by_N": {str(N): float(np.median(res_pred[N])) for N in cfg.Ns},
            "median_nn_cos_pred": float(np.median(nn_cos)),
            "nn_is_role_share_traits": float(is_role[nn_j][~is_role].mean()),
        }
        heldout[float(alpha)] = {"cos": own, "rank": rank, "nn_cos": nn_cos, "nn_idx": nn_j,
                                 "res_pred": res_pred, "is_role": is_role, "P": P}
        if E_alt is not None:
            ar = np.asarray(alt_rows)
            ca = (_unit(Palt) * Yu[ar]).sum(axis=1)
            alt[float(alpha)] = {"name": alt_name, "n": int(len(ar)), "median_cos_alt": float(np.median(ca)),
                                 "median_cos_desc_same_rows": float(np.median(own[ar]))}
    # the kNN baseline: the cosine-weighted mean of the k nearest training vectors by embedding cosine
    Eu = _unit(X[:, :-1])
    knn = {}
    for k in cfg.knn_ks:
        cos_k = np.zeros(n)
        for tr, te in folds:
            sim = Eu[te] @ Eu[tr].T
            top = np.argsort(-sim, axis=1, kind="stable")[:, :k]
            w = np.take_along_axis(sim, top, axis=1)
            w = np.clip(w, 1e-6, None)
            pred = np.einsum("ij,ijk->ik", w, Y[tr][top]) / w.sum(axis=1, keepdims=True)
            cos_k[te] = (_unit(pred) * Yu[te]).sum(axis=1)
        knn[str(k)] = float(np.median(cos_k))
    cv = CV(cfg=cfg, ids=[pool.ids[i] for i in tr_idx], kinds=kinds, groups=groups.tolist(), summary=summary,
            heldout=heldout, res_true=res_true, knn_cos_by_k=knn, spectrum=spectrum(pool.M), alt=alt)
    cv.alpha = choose_alpha(cv, tie_window=cfg.alpha_tie_window)
    cv.N = choose_N(cv, cv.alpha, tie_window=cfg.n_tie_window, prefer=cfg.prefer_N)
    return cv


def _alpha_table(cv_or_table: Any) -> dict:
    t = cv_or_table.summary if isinstance(cv_or_table, CV) else cv_or_table
    return {float(a): (v["median_cos"] if isinstance(v, Mapping) else float(v)) for a, v in t.items()}


def choose_alpha(cv_or_table: Any, tie_window: float = 0.01) -> float:
    """The alpha with the largest held-out median cosine; alphas within ``tie_window`` of it tie, and the smallest
    of them wins.  ``cv_or_table``: a :class:`CV`, or ``{alpha: median cosine}`` (or ``{alpha: {"median_cos"}}``)."""
    t = _alpha_table(cv_or_table)
    best = max(t.values())
    return min(a for a, v in t.items() if v >= best - tie_window - 1e-12)


def choose_N(cv_or_table: Any, alpha: Optional[float] = None, tie_window: float = 0.02, prefer: int = 20) -> int:
    """The N whose predicted-against-actual residual Spearman is largest; Ns within ``tie_window`` of it tie, and the
    one nearest ``prefer`` wins (then the higher Spearman, then the smaller N).  ``cv_or_table``: a :class:`CV` (with
    ``alpha``) or ``{N: Spearman}``."""
    if isinstance(cv_or_table, CV):
        t = {int(N): v for N, v in cv_or_table.summary[float(alpha)]["rho_by_N"].items() if v is not None}
    else:
        t = {int(N): float(v) for N, v in cv_or_table.items() if v is not None}
    best = max(t.values())
    tied = [N for N, v in t.items() if v >= best - tie_window - 1e-12]
    return min(tied, key=lambda N: (abs(N - prefer), -t[N], N))


def cv_record(cv: CV, *, pool: Pool, inputs: Optional[Mapping] = None) -> dict:
    """``cv.json``'s payload (§ 6)."""
    c = pool.counts()
    return {"by_alpha": {str(a): v for a, v in cv.summary.items()}, "knn_cos_by_k": cv.knn_cos_by_k,
            "alpha": cv.alpha, "N": cv.N, "n_rows": cv.n_rows, "n_groups": cv.n_groups,
            "n_train_traits": c["n_train_traits"], "n_train_roles": c["n_train_roles"], "pool": c,
            "orphans": c["orphans"], "sense_changed": c["sense_changed"], "spectrum": cv.spectrum,
            "gloss_side_check": {str(a): v for a, v in cv.alt.items()} or None, "config": cv.cfg.as_dict(),
            "choice_rules": {"alpha": f"largest held-out median cosine; alphas within {cv.cfg.alpha_tie_window} "
                                      f"tie, and the smallest wins",
                             "N": f"largest residual Spearman; Ns within {cv.cfg.n_tie_window} tie, and the one "
                                  f"nearest {cv.cfg.prefer_N} wins"},
            "inputs": dict(inputs or {})}
