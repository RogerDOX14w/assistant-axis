"""Tests for assistant_axis/gapgen/space.py (M2 task 14)."""
import numpy as np
import pytest

from assistant_axis.gapgen import space as S


def _data(n=200, d=12, seed=0):
    rng = np.random.default_rng(seed)
    scales = np.linspace(3.0, 0.2, d)
    X = rng.standard_normal((n, d)) * scales + 5.0   # a large common component, like raw embeddings
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def test_centring_uses_fixed_corpus_mean_on_new_points():
    E = _data()
    t = S.fit_space(E, "centred")
    new = _data(n=5, seed=9)
    got = t.apply(new, renorm=False)
    np.testing.assert_allclose(got, new - E.mean(axis=0))
    # fitting on corpus + new points would move the mean: the transform must not
    assert not np.allclose(S.fit_space(np.vstack([E, new]), "centred").mean, t.mean)
    np.testing.assert_allclose(np.linalg.norm(t.apply(new), axis=1), 1.0)


@pytest.mark.parametrize("variant,k", [("centred_pc1", 1), ("centred_pc3", 3)])
def test_pc_removal_is_orthogonal(variant, k):
    E = _data()
    t = S.fit_space(E, variant)
    assert t.remove.shape == (k, E.shape[1])
    np.testing.assert_allclose(t.remove @ t.remove.T, np.eye(k), atol=1e-10)
    Z = t.apply(E, renorm=False)
    np.testing.assert_allclose(Z @ t.remove.T, 0.0, atol=1e-10)
    top = S.pca_basis(E - E.mean(axis=0), k)
    np.testing.assert_allclose(np.abs(top @ t.remove.T), np.eye(k), atol=1e-8)


def test_zca_exact_gives_identity_covariance():
    E = _data(n=400, d=8)
    t = S.fit_space(E, "zca", zca_eps=0.0)
    Z = t.apply(E, renorm=False)
    cov = Z.T @ Z / len(Z)
    np.testing.assert_allclose(cov, np.eye(E.shape[1]), atol=1e-8)


def test_zca_regularised_shrinks_but_keeps_order():
    E = _data(n=400, d=8)
    t = S.fit_space(E, "zca")                      # eps at the 95%-variance eigenvalue
    assert t.zca_eps > 0 and np.all(np.diff(t.zca_scale) >= -1e-12)   # small eigenvalues get the larger multiplier
    Z = t.apply(E)
    np.testing.assert_allclose(np.linalg.norm(Z, axis=1), 1.0)


def test_raw_is_identity_up_to_norm():
    E = _data()
    np.testing.assert_allclose(S.fit_space(E, "raw").apply(E), E)
    with pytest.raises(ValueError):
        S.fit_space(E, "pca7")


def test_k_for_variance_synthetic_spectrum():
    rng = np.random.default_rng(0)
    d = 10
    eig = np.array([50, 25, 10, 5, 4, 3, 1.5, 0.8, 0.5, 0.2])     # cumulative: .5 .75 .85 .9 .94 .97 ...
    Q, _ = np.linalg.qr(rng.standard_normal((d, d)))
    X = rng.standard_normal((20000, d)) * np.sqrt(eig) @ Q.T
    X -= X.mean(axis=0)
    assert S.k_for_variance_from_eigs(eig, 0.95) == 6
    assert S.k_for_variance_from_eigs(eig, 0.90) == 4
    assert S.k_for_variance(X, 0.95) == 6


def test_residual_fraction_bounds_and_in_subspace_zero():
    rng = np.random.default_rng(1)
    B = np.linalg.qr(rng.standard_normal((6, 3)))[0].T          # 3 orthonormal rows in R^6
    inside = rng.standard_normal(3) @ B
    assert S.residual_fraction(inside, B) == pytest.approx(0.0, abs=1e-12)
    outside = rng.standard_normal((50, 6))
    r = S.residual_fraction(outside, B)
    assert r.shape == (50,) and np.all((r >= 0) & (r <= 1))
    ortho = np.linalg.qr(np.hstack([B.T, rng.standard_normal((6, 3))]))[0][:, 3:].T
    assert S.residual_fraction(ortho[0], B) == pytest.approx(1.0)


def test_loo_residuals_match_brute_force():
    E = _data(n=40, d=10)
    Z = S.fit_space(E, "centred").apply(E, renorm=False)
    got = S.loo_residuals(Z, [2, 5])
    for i in (0, 7, 39):
        others = np.delete(Z, i, axis=0)
        for k in (2, 5):
            B = np.linalg.svd(others, full_matrices=False)[2][:k]
            assert got[k][i] == pytest.approx(S.residual_fraction(Z[i], B), abs=1e-8)


def test_csls_demotes_a_hub():
    # point 0 is a hub: moderately close to everyone; 1-2 and 3-4 are tight pairs
    sim = np.array([[1.0, .60, .60, .60, .60],
                    [.60, 1.0, .65, .10, .10],
                    [.60, .65, 1.0, .10, .10],
                    [.60, .10, .10, 1.0, .62],
                    [.60, .10, .10, .62, 1.0]])
    idx_cos, _ = S.loo_nearest(None, sim=sim)
    c = S.csls(sim, k=2)
    idx_csls, _ = S.loo_nearest(None, sim=c)
    assert list(idx_cos) == [1, 2, 1, 4, 3]
    assert list(idx_csls[1:]) == [2, 1, 4, 3]
    assert np.isneginf(np.diag(c)).all()
    # nearest-neighbour counts: the hub's in-degree under CSLS is no higher than under cosine
    # queries against the corpus need the corpus's r
    q = np.array([[.5, .2, .2, .1, .1]])
    r_cols = S.topk_mean(sim, 2, exclude_diag=True)
    cq = S.csls(q, k=2, r_cols=r_cols)
    assert cq.shape == (1, 5)
    with pytest.raises(ValueError):
        S.csls(q, k=2)


def test_loo_nearest_excludes_self():
    E = _data(n=30)
    idx, sim = S.loo_nearest(E)
    assert np.all(idx != np.arange(30)) and np.all(sim < 1.0 + 1e-9)
