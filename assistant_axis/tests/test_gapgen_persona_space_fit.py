"""Plan 12 § 8, ``fit``: the features, ridge against scikit-learn, recovery of a planted linear map, a planted
unpredictable direction, the choice rules, determinism, the saved model; and the hard figures of the recorded pool
at alpha 0.3 (skipped where the vectors tree or the embedding cache is absent)."""
import numpy as np
import pytest

from assistant_axis.gapgen.persona_space import fit as FIT
from assistant_axis.gapgen.persona_space.pool import Pool, pc_basis
from assistant_axis.tests import persona_space_fakes as F


def synthetic(n=240, d_in=30, d_out=60, *, noise=0.02, planted=0.0, seed=0, roles_every=4):
    """A pool whose vectors are a linear map of the embeddings plus noise (and, with ``planted``, a component along
    one fixed direction that the embedding does not predict)."""
    rng = np.random.default_rng(seed)
    E = rng.standard_normal((n, d_in))
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    kinds = ["roles" if i % roles_every == 0 else "traits" for i in range(n)]
    W = rng.standard_normal((d_in + 1, d_out))
    Y = FIT.features(E, kinds) @ W + noise * rng.standard_normal((n, d_out))
    u = None
    if planted:
        u = rng.standard_normal(d_out)
        Q, _ = np.linalg.qr(W.T)                                  # outside the map's span: a direction of its own
        u -= Q @ (Q.T @ u)
        u /= np.linalg.norm(u)
        Y = Y + planted * rng.standard_normal((n, 1)) * u
    Y = Y - Y.mean(axis=0)
    ids = [f"e{i:03d}|{'R' if k == 'roles' else 'T'}" for i, k in enumerate(kinds)]
    pool = Pool(ids=ids, vector_stems=[i.split("|")[0] for i in ids], kinds=kinds, cur_stems=[i.split("|")[0] for i in ids],
                has_file=np.ones(n, dtype=bool), M=Y, space={"shear_applied": False}, train_idx=np.arange(n))
    groups = [f"g{i // 2}" for i in range(n)]                    # pairs of rows held out together
    return pool, E, groups, u


CFG = FIT.FitConfig(alphas=(0.01, 0.1, 1.0), n_folds=5, Ns=(4, 8, 12), knn_ks=(1, 5), n_report_pcs=20)


class TestFeaturesAndRidge:
    def test_features_append_one_column(self):
        E = np.random.default_rng(1).standard_normal((5, 7)) * 3
        X = FIT.features(E, ["traits", "roles", "T", "R", "trait"])
        assert X.shape == (5, 8)
        assert np.allclose(np.linalg.norm(X[:, :7], axis=1), 1.0)
        assert X[:, 7].tolist() == [0, 1, 0, 1, 0]
        with pytest.raises(ValueError):
            FIT.features(E, ["mammal"] * 5)

    @pytest.mark.parametrize("n,d", [(40, 80), (80, 20)])          # the dual and the primal solve
    def test_ridge_equals_sklearn(self, n, d):
        from sklearn.linear_model import Ridge
        rng = np.random.default_rng(2)
        X, Y = rng.standard_normal((n, d)), rng.standard_normal((n, 9))
        W, b = FIT.ridge(X, Y, 0.3)
        sk = Ridge(alpha=0.3).fit(X, Y)
        assert np.allclose(W, sk.coef_.T, atol=1e-8) and np.allclose(b, sk.intercept_, atol=1e-8)


class TestCrossValidation:
    def test_recovers_a_linear_map(self):
        pool, E, groups, _ = synthetic()
        cv = FIT.cross_validate(pool, E, groups, CFG)
        s = cv.summary[cv.alpha]
        assert s["median_cos"] > 0.95 and s["top1"] > 0.9
        assert cv.n_rows == 240 and cv.n_groups == 120
        assert set(cv.knn_cos_by_k) == {"1", "5"} and cv.knn_cos_by_k["5"] < s["median_cos"]
        assert len(s["per_pc_r2"]) == 20 and set(s["rho_by_N"]) == {"4", "8", "12"}

    def test_a_planted_unpredictable_direction_has_r2_near_zero(self):
        pool, E, groups, u = synthetic(planted=4.0, noise=0.01)
        cv = FIT.cross_validate(pool, E, groups, CFG)
        r2 = np.array(cv.summary[cv.alpha]["per_pc_r2"])
        B = pc_basis(pool.M, CFG.n_report_pcs)
        k = int(np.argmax(np.abs(B @ u)))                            # the PC that is the planted direction
        assert abs(B[k] @ u) > 0.95
        assert r2[k] < 0.1
        assert np.median(np.delete(r2, k)[:8]) > 0.7                  # the predicted ones stay predicted

    def test_groups_are_held_out_whole(self):
        groups = [f"g{i // 3}" for i in range(30)]
        for tr, te in FIT.folds_for(groups, 5):
            assert not {groups[i] for i in tr} & {groups[i] for i in te}


class TestChoiceRules:
    def test_choose_alpha(self):
        assert FIT.choose_alpha({0.1: 0.710, 0.3: 0.729, 1.0: 0.734, 3.0: 0.711}) == 0.3     # 1.0 within 0.01: tie
        assert FIT.choose_alpha({0.1: 0.70, 0.3: 0.72, 1.0: 0.74}) == 1.0                    # outside the window
        assert FIT.choose_alpha({0.3: {"median_cos": 0.5}, 1.0: {"median_cos": 0.5}}) == 0.3

    def test_choose_N(self):
        assert FIT.choose_N({12: 0.61, 16: 0.62, 20: 0.62, 24: 0.62, 28: 0.62, 32: 0.63}) == 20   # tie: 20
        assert FIT.choose_N({12: 0.61, 16: 0.62, 20: 0.60, 24: 0.62, 28: 0.62, 32: 0.63}) == 16   # 20 out
        assert FIT.choose_N({12: 0.70, 16: 0.62, 20: 0.60, 24: 0.62}) == 12                       # max outside
        assert FIT.choose_N({16: 0.62, 24: 0.62, 32: 0.50}) == 16          # equally near 20: the higher, then smaller
        assert FIT.choose_N({16: 0.61, 24: 0.62, 32: 0.50}) == 24


class TestFinalModel:
    def test_deterministic_and_saved(self, tmp_path):
        pool, E, _, _ = synthetic(n=60)
        m1 = FIT.fit_final(pool, E, 0.3)
        m2 = FIT.fit_final(pool, E, 0.3)
        assert m1.coef.tobytes() == m2.coef.tobytes() and m1.intercept.tobytes() == m2.intercept.tobytes()
        assert m1.coef.dtype == np.float32 and m1.coef.shape == (31, 60)
        p = FIT.save_model(m1, tmp_path / "model.npz")
        m3 = FIT.load_model(p)
        kinds = pool.train_kinds[:7]
        assert np.array_equal(FIT.predict(m1, E[:7], kinds), FIT.predict(m3, E[:7], kinds))
        assert m3.alpha == 0.3 and m3.ids == pool.train_ids and m3.kinds_seen == ["roles", "traits"]


@pytest.mark.skipif(not F.real_data_present(), reason=F.REAL_REASON)
class TestRealFit:
    """Hard, on the recorded pool at alpha 0.3 (soft bounds, two decimals below the 2026-10-13 measurement)."""

    def test_hard_figures(self):
        cv = F.real_cv_alpha03()
        s = cv.summary[0.3]
        assert s["median_cos"] >= 0.70
        assert s["top1"] >= 0.70 and s["top5"] >= 0.95
        assert s["per_pc_r2"][0] >= 0.75
        assert all(v >= 0.55 for v in s["rho_by_N"].values()), s["rho_by_N"]
        assert cv.knn_cos_by_k["5"] <= 0.70
        assert cv.n_rows == 572
