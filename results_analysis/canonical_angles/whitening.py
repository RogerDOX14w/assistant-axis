"""PCA-style whitening regimes for the canonical angles tool.

Four regimes are supported:

- ``raw``      identity (no whitening at all)
- ``soft_K``   rescale the top-K right-singular components of a centered pool
               so that their effective standard deviation matches sigma_{K+1};
               components K+1..D are left untouched.  This is the historical
               "soft-K" PCA whitening used elsewhere in the project (and by
               ``axis_judge_correlation.py``).
- ``lw``       Ledoit-Wolf shrinkage covariance, then ``cov^{-1/2}`` applied
               as the whitening matrix.
- ``oas``      Oracle Approximating Shrinkage; same structure as ``lw``.

A fitted basis is a :class:`WhiteningBasis` and is applied to a vector or
``(n, D)`` matrix via ``basis.apply(X)``.

Notes:

- The pool passed to :func:`fit_whitening` is mean-centered internally before
  the SVD / covariance is computed.  The fitted transform is then applied to
  vectors that may be expressed in any frame (the linear scaling is
  translation-equivariant for soft-K; for ``lw``/``oas`` you should center
  consistently or the cov^{-1/2} mapping mixes mean information into the
  output).
- Soft-K with K >= rank(pool) is a no-op (returns the identity transform).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


WhiteningMethod = str  # 'raw' | 'soft_K' | 'lw' | 'oas'


@dataclass
class WhiteningBasis:
    """Fitted whitening transform.

    Most callers should treat this as opaque and only call :meth:`apply`.
    The fields are exposed for diagnostics and caching keys.
    """

    method: WhiteningMethod
    K: int | None = None
    # soft_K state: top-K right singular vectors and per-PC scaling factors.
    Vt: np.ndarray | None = None       # (K, D)
    scales: np.ndarray | None = None   # (K,)  effective sigma_target / sigma_k
    # lw / oas state: cov^{-1/2} as a (D, D) matrix.
    cov_inv_sqrt: np.ndarray | None = None

    def apply(self, X: np.ndarray) -> np.ndarray:
        """Whiten a vector or (n, D) matrix.

        Returns a new array of the same shape; ``X`` is not modified.
        """
        if self.method == "raw":
            return X
        if X.ndim == 1:
            return self.apply(X[None, :])[0]

        if self.method == "soft_K":
            # X_w = X + sum_k (scale_k - 1) * (X . PC_k) * PC_k
            # i.e. scale only the top-K PC components, leave the residual fixed.
            assert self.Vt is not None and self.scales is not None
            coefs = X @ self.Vt.T                              # (n, K)
            adjustments = (coefs * (self.scales - 1.0)) @ self.Vt  # (n, D)
            return X + adjustments

        if self.method in ("lw", "oas"):
            assert self.cov_inv_sqrt is not None
            # Apply on the right: equivalent to multiplying each row by cov^{-1/2}.
            return X @ self.cov_inv_sqrt.T

        raise ValueError(f"Unknown whitening method {self.method!r}")


def fit_whitening(method: WhiteningMethod,
                  pool: np.ndarray,
                  K: int | None = None) -> WhiteningBasis:
    """Fit a whitening basis on a pool of shape ``(n_samples, hidden)``.

    Parameters
    ----------
    method : 'raw' | 'soft_K' | 'lw' | 'oas'
    pool   : (n, D) numpy array of pool vectors (will be mean-centered before fit)
    K      : required when ``method == 'soft_K'``; number of top PCs to rescale

    Returns
    -------
    WhiteningBasis
        Use ``basis.apply(X)`` to whiten new vectors / matrices.
    """
    if method == "raw":
        return WhiteningBasis(method="raw")

    if method == "soft_K":
        if K is None or K < 0:
            raise ValueError(f"soft_K requires K >= 0, got {K!r}")
        if pool.ndim != 2:
            raise ValueError(f"pool must be 2-D, got shape {pool.shape}")
        centered = pool - pool.mean(axis=0, keepdims=True)
        # SVD of centered: centered = U @ diag(S) @ Vt.  Right singular vectors
        # are the principal components in row-vector convention (i.e. PC_k
        # is the k-th row of Vt).
        _U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        if K >= len(S):
            # Nothing to rescale: pool has rank <= K, so soft_K is identity.
            return WhiteningBasis(method="raw", K=K)
        target_sigma = float(S[K])  # the (K+1)-th singular value (0-indexed: S[K])
        scales = target_sigma / np.maximum(S[:K], 1e-12)
        return WhiteningBasis(
            method="soft_K", K=K,
            Vt=Vt[:K].astype(np.float64),
            scales=scales.astype(np.float64),
        )

    if method in ("lw", "oas"):
        from sklearn.covariance import LedoitWolf, OAS
        est = LedoitWolf() if method == "lw" else OAS()
        est.fit(pool)
        cov = est.covariance_
        # Symmetric matrix; use eigh for numerical stability over generic eig.
        eigvals, eigvecs = np.linalg.eigh(cov)
        eigvals = np.maximum(eigvals, 1e-12)
        cov_inv_sqrt = eigvecs @ np.diag(eigvals ** -0.5) @ eigvecs.T
        return WhiteningBasis(method=method, cov_inv_sqrt=cov_inv_sqrt.astype(np.float64))

    raise ValueError(f"Unknown whitening method {method!r}")


def parse_whitening_spec(s: str) -> tuple[str, int | None]:
    """Parse a CLI string like 'raw' / 'soft_K=4' / 'lw' / 'oas' into (method, K).

    Used by wrappers to convert their --whitening flag to a method+K pair.
    """
    s = s.strip()
    if s == "raw":
        return "raw", None
    if s.startswith("soft_K"):
        # Accept 'soft_K=4' or 'soft_K_4' or 'soft_K4' for flexibility.
        for sep in ("=", "_"):
            if sep in s:
                tail = s.split(sep, 1)[1]
                return "soft_K", int(tail)
        if s == "soft_K":
            raise ValueError("soft_K requires a value, e.g. 'soft_K=4'")
        return "soft_K", int(s.removeprefix("soft_K"))
    if s in ("lw", "oas"):
        return s, None
    raise ValueError(f"Cannot parse whitening spec {s!r}; "
                     f"expected one of: 'raw', 'soft_K=N', 'lw', 'oas'")
