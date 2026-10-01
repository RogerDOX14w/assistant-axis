"""Space variants and leave-one-out geometry for embedding novelty (M2, plan 15).

``fit_space(E_corpus, variant)`` returns a :class:`SpaceTransform` fitted on
the corpus embeddings only (the fixed corpus mean: plan 15 §11; never the
pooled corpus-plus-candidate mean); ``.apply(E)`` maps any embeddings (corpus
or candidates) into the variant and renormalises the rows.  Variants
(:data:`VARIANTS`):

* ``raw``: the model's unit vectors.
* ``centred``: minus the corpus mean.
* ``centred_pc1`` / ``centred_pc3``: centred, then the top 1 / 3 principal
  components of the centred corpus projected out ("all-but-the-top", Mu and
  Viswanath 2018).
* ``zca``: centred, then whitened with a regularised ZCA,
  ``(C + eps I)^(-1/2)``.  With fewer corpus points than dimensions (659
  against 1024-3072) the unregularised ZCA makes every corpus point
  equidistant from every other, so nearest neighbours are meaningless;
  ``eps`` defaults to the eigenvalue at the 95%-variance cut
  (``zca_eps="k95"``): components above it are equalised, the tail is left
  as it is.  ``zca_eps=0`` is the exact ZCA on the corpus span (the unit
  test checks it gives identity covariance).
* ``pw<N>`` (round 2, Roger 2026-10-01), partial whitening: centred, then
  each of the top N principal components of the centred corpus shrunk so
  that its standard deviation equals the (N+1)th's; every other component
  is left as it is.  ``pw0`` is plain centring (accepted by ``fit_space``,
  not listed in :data:`VARIANTS`).  N in :data:`PW_NS`.

Also: ``k_for_variance`` (the 95%-variance rule), ``pca_basis``,
``residual_fraction`` (directional novelty), ``loo_residuals`` (each row
against the top-K PCs of the *other* rows, for several K from one
eigendecomposition per row, through the Gram matrix), ``csls`` (cross-domain
similarity local scaling) and ``loo_nearest``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Union

import numpy as np

PW_NS = (1, 2, 4, 8, 16, 32, 64)
VARIANTS = ("raw", "centred", "centred_pc1", "centred_pc3", "zca") + tuple(f"pw{n}" for n in PW_NS)


def _unit(E: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(E, axis=-1, keepdims=True)
    return E / np.where(n == 0, 1.0, n)


def _eig_centred(Xc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Eigenvalues (descending, of the covariance ``Xc^T Xc / n``) and the
    matching right singular vectors as rows, from the SVD of ``Xc``."""
    _, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    return (S ** 2) / Xc.shape[0], Vt


@dataclass
class SpaceTransform:
    variant: str
    mean: Optional[np.ndarray] = None          # fixed corpus mean (d,)
    remove: Optional[np.ndarray] = None        # (k, d) orthonormal rows projected out
    zca_basis: Optional[np.ndarray] = None     # (r, d) eigenvector rows
    zca_scale: Optional[np.ndarray] = None     # (r,) multiplier per eigen-direction
    zca_tail: float = 0.0                      # multiplier for the part outside the span
    zca_eps: Optional[float] = None
    scale_basis: Optional[np.ndarray] = None   # (N, d) rows rescaled by partial whitening
    scale_factors: Optional[np.ndarray] = None  # (N,) multiplier per row

    def apply(self, E: np.ndarray, *, renorm: bool = True) -> np.ndarray:
        X = np.asarray(E, dtype=np.float64)
        single = X.ndim == 1
        X = np.atleast_2d(X)
        if self.variant != "raw":
            X = X - self.mean
        if self.remove is not None and len(self.remove):
            X = X - (X @ self.remove.T) @ self.remove
        if self.scale_basis is not None and len(self.scale_basis):
            coef = X @ self.scale_basis.T
            X = X + (coef * (self.scale_factors - 1.0)) @ self.scale_basis
        if self.variant == "zca":
            coef = X @ self.zca_basis.T
            X = (coef * self.zca_scale) @ self.zca_basis + self.zca_tail * (X - coef @ self.zca_basis)
        if renorm:
            X = _unit(X)
        return X[0] if single else X


def fit_space(E_corpus: np.ndarray, variant: str, *, zca_eps: Union[str, float] = "k95",
              var_frac: float = 0.95) -> SpaceTransform:
    """Fit ``variant`` on the corpus embeddings ``E_corpus`` (n, d)."""
    if variant not in VARIANTS and variant != "pw0":
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    E = np.asarray(E_corpus, dtype=np.float64)
    if variant == "raw":
        return SpaceTransform("raw")
    mu = E.mean(axis=0)
    Xc = E - mu
    if variant == "centred":
        return SpaceTransform("centred", mean=mu)
    if variant == "pw0":
        return SpaceTransform("pw0", mean=mu)
    lam, Vt = _eig_centred(Xc)
    if variant.startswith("pw"):
        n = int(variant[2:])
        if n >= len(lam) or lam[n] <= 0:
            raise ValueError(f"{variant}: the corpus has no ({n}+1)th principal component to match")
        factors = np.sqrt(lam[n] / lam[:n])          # sd of the (N+1)th / sd of each of the top N
        return SpaceTransform(variant, mean=mu, scale_basis=Vt[:n].copy(), scale_factors=factors)
    if variant in ("centred_pc1", "centred_pc3"):
        k = 1 if variant == "centred_pc1" else 3
        return SpaceTransform(variant, mean=mu, remove=Vt[:k].copy())
    # zca
    keep = lam > lam[0] * 1e-10
    lam, Vt = lam[keep], Vt[keep]
    if zca_eps == "k95":
        eps = float(lam[k_for_variance_from_eigs(lam, var_frac) - 1])
    else:
        eps = float(zca_eps)
    if eps > 0:
        scale = np.sqrt(eps / (lam + eps))     # (C + eps I)^(-1/2), times sqrt(eps) (renormalised anyway)
        tail = 1.0
    else:
        scale = 1.0 / np.sqrt(lam)
        tail = 0.0
    return SpaceTransform("zca", mean=mu, zca_basis=Vt, zca_scale=scale, zca_tail=tail, zca_eps=eps)


def k_for_variance_from_eigs(eigs: np.ndarray, frac: float = 0.95) -> int:
    eigs = np.sort(np.asarray(eigs, dtype=np.float64))[::-1]
    c = np.cumsum(eigs) / eigs.sum()
    return int(np.searchsorted(c, frac - 1e-12) + 1)


def k_for_variance(E_centred: np.ndarray, frac: float = 0.95) -> int:
    """Smallest K whose top-K principal components carry ``frac`` of the
    variance of the (already centred) rows."""
    S = np.linalg.svd(np.asarray(E_centred, dtype=np.float64), compute_uv=False)
    return k_for_variance_from_eigs(S ** 2, frac)


def pca_basis(E_centred: np.ndarray, K: int) -> np.ndarray:
    """Top-``K`` principal directions (rows, orthonormal) of centred rows."""
    _, _, Vt = np.linalg.svd(np.asarray(E_centred, dtype=np.float64), full_matrices=False)
    return Vt[:K]


def residual_fraction(x: np.ndarray, basis_K: np.ndarray) -> Union[float, np.ndarray]:
    """``1 - |B x|^2 / |x|^2``: the share of ``x``'s squared norm outside the
    span of the orthonormal rows ``basis_K``; in [0, 1], 0 for a vector in the
    subspace.  ``x`` may be one vector or rows."""
    X = np.atleast_2d(np.asarray(x, dtype=np.float64))
    proj = X @ np.asarray(basis_K, dtype=np.float64).T
    out = 1.0 - (proj ** 2).sum(axis=1) / np.maximum((X ** 2).sum(axis=1), 1e-300)
    out = np.clip(out, 0.0, 1.0)
    return float(out[0]) if np.ndim(x) == 1 else out


def loo_residuals(Z: np.ndarray, Ks: Iterable[int]) -> dict[int, np.ndarray]:
    """For each row ``i`` of ``Z`` (already centred on the fixed mean, not
    re-centred per fold), the residual fraction outside the top-K principal
    subspace of the other rows, for every K in ``Ks``.  One ``eigh`` of the
    (n-1)x(n-1) Gram matrix per row: with ``G = Z Z^T`` and ``g = G[-i, i]``,
    the squared projection is ``sum_k (u_k . g)^2 / w_k`` over the top-K
    eigenpairs ``(w_k, u_k)`` of ``G[-i, -i]``."""
    Z = np.asarray(Z, dtype=np.float64)
    n = Z.shape[0]
    Ks = sorted(set(int(k) for k in Ks))
    G = Z @ Z.T
    out = {k: np.zeros(n) for k in Ks}
    idx = np.arange(n)
    for i in range(n):
        m = idx != i
        w, U = np.linalg.eigh(G[np.ix_(m, m)])
        w, U = w[::-1], U[:, ::-1]
        g = G[m, i]
        proj = (U.T @ g) ** 2 / np.maximum(w, 1e-300)
        proj[w <= w[0] * 1e-12] = 0.0
        csum = np.cumsum(proj)
        for k in Ks:
            kk = min(k, len(csum))
            out[k][i] = 1.0 - csum[kk - 1] / max(G[i, i], 1e-300)
    return {k: np.clip(v, 0.0, 1.0) for k, v in out.items()}


def topk_mean(sim: np.ndarray, k: int, *, exclude_diag: bool) -> np.ndarray:
    S = np.array(sim, dtype=np.float64, copy=True)
    if exclude_diag:
        np.fill_diagonal(S, -np.inf)
    k = min(k, S.shape[1] - (1 if exclude_diag else 0))
    part = -np.partition(-S, k - 1, axis=1)[:, :k]
    return part.mean(axis=1)


def csls(sim: np.ndarray, k: int = 10, *, r_rows: Optional[np.ndarray] = None,
         r_cols: Optional[np.ndarray] = None) -> np.ndarray:
    """Cross-domain similarity local scaling (Conneau et al. 2018):
    ``2 cos(x, y) - r(x) - r(y)`` with ``r`` the mean similarity to the ``k``
    nearest neighbours.  For a square corpus-by-corpus ``sim`` (self excluded),
    both ``r`` come from it; for queries against the corpus pass ``r_cols``
    (the corpus's own ``r``) and optionally ``r_rows``."""
    sim = np.asarray(sim, dtype=np.float64)
    square = sim.shape[0] == sim.shape[1] and r_rows is None and r_cols is None
    if square:
        r = topk_mean(sim, k, exclude_diag=True)
        out = 2 * sim - r[:, None] - r[None, :]
        np.fill_diagonal(out, -np.inf)
        return out
    if r_rows is None:
        r_rows = topk_mean(sim, k, exclude_diag=False)
    if r_cols is None:
        raise ValueError("queries against a corpus need r_cols (the corpus's own neighbourhood means)")
    return 2 * sim - np.asarray(r_rows)[:, None] - np.asarray(r_cols)[None, :]


def loo_nearest(E: np.ndarray, *, sim: Optional[np.ndarray] = None) -> tuple[np.ndarray, np.ndarray]:
    """Each row's nearest other row: ``(index, similarity)`` (cosine for unit
    rows, or the given ``sim`` such as a CSLS matrix)."""
    S = np.array(sim if sim is not None else np.asarray(E) @ np.asarray(E).T, dtype=np.float64, copy=True)
    np.fill_diagonal(S, -np.inf)
    idx = S.argmax(axis=1)
    return idx, S[np.arange(len(S)), idx]
