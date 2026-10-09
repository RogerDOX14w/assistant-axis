"""Tests for assistant_axis/gapgen/persona.py (M2 task 15)."""
import numpy as np
import pytest

from assistant_axis.gapgen import persona as P
from assistant_axis.gapgen.paths import REPO_ROOT
from assistant_axis.gapgen.space import pca_basis, residual_fraction

FIXTURE = """### Strategy 1: highest-yield isolated dimensions

Numbers in `[brackets]` = residual fraction; higher = more orthogonal.

**Family 1: emotional state**
- [0.829] `melancholic` → cheerful / sanguine
- [0.826] `calm` → agitated  ← simple
- [0.773] `existentialist` → essentialist (note: essentialist already
  in cohort)
- [1.0] `orthogonal_one` → x
Not a score: [0.5] `ignored` inline, and - [x] `bad` → y
"""


def test_bracket_parser_on_fixture(tmp_path):
    got = P.parse_bracket_scores(FIXTURE)
    assert got == {"melancholic": 0.829, "calm": 0.826, "existentialist": 0.773, "orthogonal_one": 1.0}
    f = tmp_path / "t.md"
    f.write_text(FIXTURE)
    assert P.parse_bracket_scores(f) == got


def test_bracket_parser_on_the_real_file():
    p = REPO_ROOT / "data" / "traits" / "instructions" / "TRAITS_ADDED.md"
    got = P.parse_bracket_scores(p)
    assert len(got) >= 20 and got["calm"] == pytest.approx(0.826)


def test_loo_residual_synthetic():
    rng = np.random.default_rng(0)
    # 60 points in a 3-d subspace of R^8 plus one point orthogonal to it
    B = np.linalg.qr(rng.standard_normal((8, 8)))[0]
    inside = rng.standard_normal((60, 3)) @ B[:, :3].T
    outlier = 5 * B[:, 7]
    M = np.vstack([inside, outlier])
    r = P.loo_residual(M, 3)
    assert r.shape == (61,)
    assert np.all(r[:60] < 1e-8)          # each in-subspace point is explained by the others
    assert r[60] == pytest.approx(1.0)    # the orthogonal one is not
    # agrees with a brute-force leave-one-out PCA (no re-centring: fixed mean)
    i = 5
    basis = pca_basis(np.delete(M, i, axis=0), 3)
    assert r[i] == pytest.approx(residual_fraction(M[i], basis), abs=1e-8)


@pytest.mark.skipif(not (P.DEFAULT_VECTORS_DIR / "traits" / "vectors").exists(), reason="persona vectors not linked")
def test_real_pool_shapes():
    stems, M = P.load_trait_vectors()
    assert len(stems) == M.shape[0] >= 250 and M.shape[1] == 5120
    assert "default" not in stems
