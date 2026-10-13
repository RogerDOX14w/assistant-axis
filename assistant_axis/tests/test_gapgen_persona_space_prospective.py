"""Plan 12 § 8, ``prospective``: the pending entities (toy, and the hard count of the recorded corpus), the
predictions, and the comparison on a toy new tree (a rotated, shifted copy of the toy pool with the pending
entities added): rank Spearman 1.0, full name hits, centred on itself."""
import json

import numpy as np
import pytest

from assistant_axis.entity_id import entity_id
from assistant_axis.gapgen.embed import HashEmbedder, normalize_rows
from assistant_axis.gapgen.persona_space import fit as FIT
from assistant_axis.gapgen.persona_space import pool as POOL
from assistant_axis.gapgen.persona_space import prospective as PRO
from assistant_axis.tests import persona_space_fakes as F
from assistant_axis.tests.test_gapgen_persona_space_calibrate import table_cal


@pytest.fixture
def toy(tmp_path):
    data = F.write_toy_corpus(tmp_path / "data")
    return data, POOL.pool_from_space(F.toy_space(), data)


def test_pending_on_the_toy_corpus(toy):
    data, pool = toy
    # the two new traits, and the current file of the sense-changed rename (its May vector is the old sense);
    # robust -> sturdy carries; default and the orphans are not entities with a file
    assert PRO.pending(pool, data) == [("traits", "p_one"), ("traits", "p_two"), ("traits", "violent")]


def test_predict_pending(toy):
    data, pool = toy
    texts = POOL.corpus_texts(pool, data)
    E = normalize_rows(HashEmbedder(32).embed_batch([texts[i] for i in pool.train_idx])[0])
    model = FIT.fit_final(pool, E, 0.3)
    ents = PRO.pending(pool, data)
    Ep = normalize_rows(HashEmbedder(32).embed_batch(PRO.pending_texts(ents, data))[0])
    rows, P = PRO.predict_pending(model, table_cal(N=4, residual_pred_quantiles_by_N={}), pool, Ep, ents, Ns=(4,),
                                  partners=POOL.pair_partners(pool, data), fit_id="f")
    assert [r["id"] for r in rows] == ["p_one|T", "p_two|T", "violent|T"] and P.shape == (3, F.DIM)
    assert all(set(r) >= {"kind", "stem", "residual", "residual_pct", "nn", "nearest", "flag"} for r in rows)
    assert PRO.pending_texts(ents, data)[2].startswith("violent: This means being violent")


def test_compare_on_a_rotated_shifted_tree(toy, tmp_path):
    data, pool = toy
    raw = F.toy_raw_vectors()
    N = 3
    B = POOL.pc_basis(pool.M, N)
    res = POOL.residual_N(pool.M, B)
    train = list(pool.train_idx)
    lo = min(train, key=lambda i: res[i])                         # the entity most inside the top-N span
    hi = max(train, key=lambda i: res[i])                         # and the one most outside it
    u_last = np.linalg.svd(pool.M, full_matrices=False)[2][-1]
    key = {pool.ids[i]: (pool.vector_stems[i], pool.kinds[i]) for i in range(pool.n)}
    new_raw = {}
    for eid in pool.train_ids:                                    # re-extracted under the current stems
        s, k = key[eid]
        cur = eid.split("|")[0]
        new_raw[(cur, k)] = raw[(s, k)]
    base_lo, base_hi = raw[key[pool.ids[lo]]], raw[key[pool.ids[hi]]]
    new_raw[("p_one", "traits")] = base_lo + 0.02 * np.linalg.norm(base_lo) * B[0]
    new_raw[("p_two", "traits")] = base_hi + 0.3 * np.linalg.norm(pool.M[hi]) * u_last
    rng = np.random.default_rng(7)
    R, _ = np.linalg.qr(rng.standard_normal((F.DIM, F.DIM)))
    shift = 50.0 * np.ones(F.DIM)                                 # far from the May mean
    new_dir = F.write_vectors_tree(tmp_path / "new_tree", {k: R @ v + shift for k, v in new_raw.items()})
    pred = [{"id": "p_one|T", "kind": "traits", "stem": "p_one", "residual": 0.1, "residual_by_N": {str(N): 0.1},
             "nn": [pool.ids[lo], 0.99], "nearest": [[pool.ids[lo], 0.99], ["t01|T", 0.2], ["t02|T", 0.1]]},
            {"id": "p_two|T", "kind": "traits", "stem": "p_two", "residual": 0.9, "residual_by_N": {str(N): 0.9},
             "nn": [pool.ids[hi], 0.5], "nearest": [[pool.ids[hi], 0.5], ["t03|T", 0.1], ["t04|T", 0.1]]}]
    comp = PRO.compare(pred, new_dir, data_dir=data, N=N, shear_L=None, cache_dir=tmp_path / "cache",
                       known_ids=pool.train_ids)
    assert comp["n_with_vector"] == 2 and comp["n_known"] == len(pool.train_ids)
    assert comp["rho_residual_rank"] == pytest.approx(1.0)
    assert comp["top1_name_hit"] == 1.0 and comp["top3_name_hit"] == 1.0
    assert comp["shear_applied"] is False
    assert {r["id"]: r["nearest_actual"][0] for r in comp["rows"]} == {"p_one|T": pool.ids[lo], "p_two|T": pool.ids[hi]}
    # the slice cache went where it was told, never into data/candidates/cache/persona_s6_l25.npz
    assert (tmp_path / "cache" / "persona_s6_l25.npz").exists()
    json.dumps(comp)


def test_the_default_cache_is_not_the_may_one(tmp_path):
    d = PRO.default_cache_dir(tmp_path / "x")
    assert d.parent.name == "persona_prospective"


@pytest.mark.skipif(not F.real_data_present(), reason=F.REAL_REASON)
def test_real_pending_count():
    ents = PRO.pending(F.real_pool())
    k = [x for x, _ in ents]
    # 637 traits with no vector + violent and metaphysical_libertarian (sense-changed renames: their May vector is the
    # old sense), 60 roles (instrumentally_aligned_ai's vector carries under renamed_from): QUESTIONS 147
    assert (k.count("traits"), k.count("roles")) == (639, 60)
    assert ("traits", "violent") in ents and ("traits", "metaphysical_libertarian") in ents
    assert ("roles", "instrumentally_aligned_ai") not in ents and ("roles", "default") not in ents
    assert entity_id("dull", "traits") not in F.real_pool().train_ids
