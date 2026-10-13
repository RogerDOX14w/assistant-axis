"""Plan 12 § 8, ``pool``: the pool, its training rows, the fold groups, the residual (toy corpus), and the hard
counts of the recorded May pool (skipped where the vectors tree is absent)."""
import numpy as np
import pytest

from assistant_axis.gapgen.persona_space import pool as POOL
from assistant_axis.gapgen.space import k_for_variance
from assistant_axis.tests import persona_space_fakes as F


@pytest.fixture
def toy(tmp_path):
    data = F.write_toy_corpus(tmp_path / "data")
    return data, POOL.pool_from_space(F.toy_space(), data)


class TestToyPool:
    def test_ids_kinds_and_collisions(self, toy):
        _, pool = toy
        assert all(i.endswith(("|T", "|R")) for i in pool.ids)
        assert "patient|T" in pool.ids and "patient|R" in pool.ids          # same name, two rows
        assert pool.kinds[pool.row("patient|T")] == "traits" and pool.kinds[pool.row("patient|R")] == "roles"
        assert len(set(pool.ids)) == pool.n

    def test_orphans_renames_and_training_rows(self, toy):
        _, pool = toy
        assert pool.orphan_ids == ["lost|T", "ghost|R"]
        assert pool.sense_changed_ids == ["savage|T"]                      # savage -> violent changed the sense
        assert "sturdy|T" in pool.train_ids                                 # robust -> sturdy carries
        assert pool.renamed == {"robust|T": "sturdy|T", "savage|T": "violent|T"}
        train = set(pool.train_ids)
        assert not train & {"lost|T", "ghost|R", "savage|T", "violent|T"}
        c = pool.counts()
        assert c["n_with_file"] == pool.n - 2                               # every row but the two orphans
        assert c["n_train"] == pool.n - 3                                   # less the sense-changed rename
        assert c["n_renamed_traits"] == 2 and c["n_renamed_roles"] == 0

    def test_fold_groups(self, toy):
        data, pool = toy
        g = POOL.fold_groups(pool, data)
        grp = {pool.ids[i]: g[i] for i in range(pool.n)}
        assert grp["brave|T"] == grp["cowardly|T"] != grp["honest|T"]      # a pair together, pairs apart
        assert grp["alpha|T"] == grp["beta|T"] == grp["gamma|T"]          # a triangle's corners together
        assert grp["angel|R"] == grp["demon|R"]                             # a role pair together
        singles = [grp[f"t{i:02d}|T"] for i in range(1, 25)]
        assert len(set(singles)) == len(singles)                            # singletons alone
        assert grp["patient|T"] != grp["patient|R"]
        assert grp["lost|T"].startswith("solo:")                            # a row that does not train

    def test_pair_partners(self, toy):
        data, pool = toy
        pp = POOL.pair_partners(pool, data)
        assert pp["brave|T"] == "cowardly|T" and pp["cowardly|T"] == "brave|T"
        assert pp["angel|R"] == "demon|R"
        assert "alpha|T" not in pp                                          # a triangle corner is not a pair pole

    def test_corpus_texts(self, toy):
        data, pool = toy
        texts = POOL.corpus_texts(pool, data)
        t = texts[pool.row("sturdy|T")]
        assert t.startswith("sturdy: This means being sturdy")              # the current file's text, w20
        assert texts[pool.row("r01|R")].startswith("r01: A r01 is someone")
        assert texts[pool.row("lost|T")] is None and texts[pool.row("savage|T")] is None

    def test_residual(self, toy):
        _, pool = toy
        B = POOL.pc_basis(pool.M, 5)
        r = POOL.residual_N(pool.M, B)
        assert np.all((r >= 0) & (r <= 1))
        inside = 2.0 * B[0] - 0.5 * B[3]
        assert POOL.residual_N(inside, B)[0] == pytest.approx(0.0, abs=1e-10)


@pytest.mark.skipif(not F.real_data_present(), reason=F.REAL_REASON)
class TestRealPool:
    """Hard (measured 2026-10-13)."""

    def test_counts(self):
        pool = F.real_pool()
        c = pool.counts()
        assert (c["n"], c["n_traits"], c["n_roles"]) == (582, 302, 280)
        assert (c["n_with_file"], c["n_with_file_traits"], c["n_with_file_roles"]) == (574, 295, 279)
        assert (c["n_renamed_traits"], c["n_renamed_roles"]) == (19, 1)
        assert sorted(c["orphans"]) == sorted(["conceptual|T", "enigmatic|T", "dramatic|T", "mercurial|T",
                                               "technical|T", "cruel|T", "regulatory|T", "adolescent|R"])
        # the three sense-changed renames: bland has no May vector; libertarian and savage do, and never train
        assert sorted(c["sense_changed"]) == ["libertarian|T", "savage|T"]
        assert not set(c["sense_changed"]) & set(pool.train_ids)
        assert (c["n_train"], c["n_train_traits"], c["n_train_roles"]) == (572, 293, 279)
        assert pool.space["shear_applied"] is True

    def test_spectrum(self):
        M = F.real_pool().M
        assert (k_for_variance(M, 0.95), k_for_variance(M, 0.5), k_for_variance(M, 0.8)) == (170, 10, 45)
