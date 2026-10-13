"""Plan 13's additions to the recovery harness's library (``assistant_axis/gapgen/recovery.py``): the exclusion
in the draw (a draw without one byte for byte the draw before 2026-10-13), the fixed hidden list, the affected-only
split, the pooled selection and attribution, and the per-generator figures.  The end-to-end acceptance test of
decision 1 (affected-only equals a full re-score; pooled equals separate runs) is
``data_analysis/tests/test_gap_generation_recovery_pooled.py``.  No API calls."""
import hashlib
import json

import numpy as np
import pytest

from assistant_axis.gapgen import novelty as NV
from assistant_axis.gapgen import recovery as RC
from assistant_axis.tests.test_gapgen_novelty import cand, query, toy_index, write_corpus
from assistant_axis.tests.test_gapgen_recovery import TOY_GROUPS, TOY_REGIONS, hidden_doc

#: sha256 of ``json.dumps(draw_hidden(toy, frac=0.3, seed=s, ...), sort_keys=True)`` computed with the function as
#: it was at c6d8c433 (before the ``exclude`` parameter), seeds 0-3.
PINNED = ["c3660e20c73ce0431934c49e2198caf248af1e2f46f2445cd8c6e8a430cb0bd4",
          "54297fe9089a0e30e622a405df1caa2c0a669e41b6a069970edf87067cf73dc7",
          "379e12df18e80af5d65b0169628ed84ec53f838e31cdaf621c20f0a62d14b121",
          "209cce10bb8a5d89cce8bc33bba1ed8e7cc9ae6f6644e2a797db25fcd99043e7"]


def toy(tmp_path):
    data = write_corpus(tmp_path / "data")
    traits = NV.load_trait_corpus(data)
    return data, traits, RC.arrangement_kinds(data, traits)


class TestDraw:
    def test_without_exclusion_byte_identical_to_the_draw_before(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        for s, pin in enumerate(PINNED):
            for kw in ({}, {"exclude": ()}, {"exclude": ["not_a_trait"]}):
                d = RC.draw_hidden(traits, frac=0.3, seed=s, regions=TOY_REGIONS, kinds=kinds, **kw)
                assert hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest() == pin, (s, kw)

    def test_an_excluded_group_is_never_drawn(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        seen = set()
        for s in range(30):
            d = RC.draw_hidden(traits, frac=0.3, seed=s, regions=TOY_REGIONS, kinds=kinds, exclude=["delta"])
            assert not {"delta", "epsilon"} & set(d["hidden"])          # delta's pair is left out whole
            assert d["excluded"] == ["delta"] and d["excluded_groups"] == [["delta", "epsilon"]]
            seen |= set(d["hidden"])
            for st, v in d["strata"].items():                           # the quotas are the whole stratum's
                assert v["quota"] == RC.stratum_quotas({k: x["n_traits"] for k, x in d["strata"].items()}, 0.3)[st]
        assert seen >= {"alpha", "theta", "zeta"}

    def test_fixed_hidden(self, tmp_path):
        _, traits, kinds = toy(tmp_path)
        d = RC.fixed_hidden(["delta", "zeta", "alpha"], traits, regions=TOY_REGIONS, kinds=kinds, source="x")
        assert d["hidden"] == ["alpha", "beta", "delta", "epsilon", "gamma", "zeta"]     # groups whole
        assert d["hidden_frac"] is None and d["requested"] == ["alpha", "delta", "zeta"] and d["n_target"] == 3
        assert sorted(g["members"] for g in d["groups"]) == [["alpha", "beta", "gamma"], ["delta", "epsilon"], ["zeta"]]
        assert all(d["traits"][s]["kind"] == kinds[s] for s in d["hidden"])
        with pytest.raises(ValueError, match="not in the corpus"):
            RC.fixed_hidden(["nope"], traits, regions=TOY_REGIONS, kinds=kinds)


class TestAffectedSplit:
    def setup(self, tmp_path):
        idx = toy_index(tmp_path)                       # raw space: the toy's axes are the corpus traits
        traits = idx.traits
        hid = ["delta", "epsilon"]
        red_traits = RC.reduced_traits(traits, hid)
        E = np.eye(12)[[i for i, s in enumerate(sorted(traits)) if s in red_traits]]
        red = NV.build_index(red_traits, E, variant="raw", settings={"k": 4})
        queue = {"entries": [{"stem": "queued", "label": "queued", "status": "candidate"}]}
        full_sets = NV.label_sets(traits, queue)
        red_sets = RC.reduced_label_sets(red_traits, queue, hid, traits=traits)
        return idx, red, traits, hid, full_sets, red_sets

    def test_reasons(self, tmp_path):
        idx, red, traits, hid, fs, rs = self.setup(tmp_path)
        cs = [cand("delta"),                                         # its label is hidden
              cand("near delta"),                                    # delta among its nearest
              cand("far away"),                                      # nothing hidden near: unaffected
              cand("no block"),                                      # never decided: scored again
              cand("recorded"),                                      # its recorded block read epsilon
              cand("no vector")]
        vec = {cs[0].key: query(delta=0.9, zeta=0.5, eta=0.4, kappa=0.3),
               cs[1].key: query(delta=0.9, zeta=0.5, eta=0.4, kappa=0.3),
               cs[2].key: query(zeta=0.9, eta=0.8, kappa=0.7, theta=0.6),
               cs[3].key: query(zeta=0.9, eta=0.8, kappa=0.7, theta=0.6),
               cs[4].key: query(zeta=0.9, eta=0.8, kappa=0.7, theta=0.6)}
        blocks = {c.key: {"decision": "new", "listed": [{"stem": "zeta"}]} for c in cs}
        blocks[cs[3].key] = None
        blocks[cs[4].key] = {"decision": "covered", "covered_by": "zeta", "readings": [{"stem": "epsilon"}]}
        out = RC.affected_split(cs, blocks=blocks, hidden=hid, traits=traits, vectors=vec, k=4, reduced_index=red,
                                full_index=idx, match_index=idx, full_sets=fs, reduced_sets=rs, rules=NV.RULES[3])
        assert out[cs[0].key][:2] == ["label", "exact_label"]
        assert "m3_near" in out[cs[1].key] and "match_near" in out[cs[1].key]
        assert cs[2].key not in out
        assert out[cs[3].key] == ["no_block"]
        assert out[cs[4].key] == ["recorded"]
        assert out[cs[5].key] == ["no_vector"]
        assert set(sum(out.values(), [])) <= set(RC.AFFECTED_REASONS)

    def test_recorded_stems(self):
        b = {"covered_by": "a", "exact_label": {"covered_by": "b", "match": "corpus"}, "listed": [{"stem": "c"}],
             "readings": [{"stem": "d"}], "relation": {"order": ["e", "f"]}, "shortlist": ["g"],
             "below_floor": ["h"], "pair_completion_for": ["i"], "deciding_reading": {"stem": "j"}}
        assert RC.recorded_stems(b) == set("abcdefghij")
        assert RC.recorded_stems({}) == set()

    def test_copied_result(self):
        c = cand("far away")
        r = RC.copied_result({"novelty": {"run_id": "m3x", "decision": "new"}}, c)
        assert r["novelty"] == {"run_id": "m3x", "decision": "new", "copied_from": "m3x"} and r["key"] == c.key


def src(g, run="r", ref=None):
    return {"generator": g, "run_id": run, "source_ref": ref}


class TestPooled:
    ROWS = {"a#1": {"key": "a#1", "filter": {"verdict": "trait"}, "sources": [src("censuses", "tda")]},
            "b#1": {"key": "b#1", "filter": {"verdict": "trait"},
                    "sources": [src("censuses", "tda"), src("ipip", "g600"), src("m1_validation")]},
            "c#1": {"key": "c#1", "filter": {"verdict": "trait"}, "sources": [src("m1_validation")]},
            "d#1": {"key": "d#1", "filter": {"verdict": "reject"}, "sources": [src("censuses", "tda")]},
            "e#1": {"key": "e#1", "filter": {"verdict": "trait"}, "sources": [src("states_pass", "st", "a#1")]},
            "f#1": {"key": "f#1", "filter": {"verdict": "trait"}, "sources": [src("states_pass", "st", "c#1")]},
            "g#1": {"key": "g#1", "filter": {"verdict": "trait"}, "sources": [src("manual")]}}

    def test_selection_and_attribution(self):
        keys, counts = RC.pooled_rows(self.ROWS)
        assert keys == ["a#1", "b#1", "e#1"]
        assert counts == {"trait_rows": 6, "with_a_non_pool_source": 4, "only_states_pass_besides_pools": 2,
                          "states_pass_rows_with_no_generator_upstream": 1, "pooled": 3}
        assert RC.attribution(self.ROWS["b#1"], self.ROWS) == [("censuses", "tda"), ("ipip", "g600")]
        assert RC.attribution(self.ROWS["e#1"], self.ROWS) == [("censuses", "tda")]
        assert RC.attribution(self.ROWS["f#1"], self.ROWS) == []

    def test_breakdown(self):
        hd = hidden_doc()                                     # alpha beta gamma (a triangle), lambda mu
        results = [{"key": "a#1", "novelty": {"decision": "new"}}, {"key": "b#1", "novelty": {"decision": "new"}},
                   {"key": "e#1", "novelty": {"decision": "covered", "copied_from": "m3"}}]
        rows = [{"key": "a#1", "stem": "alpha", "how": "label", "recovers": True},
                {"key": "b#1", "stem": "beta", "how": "overlap", "recovers": True},
                {"key": "b#1", "stem": "gamma", "how": "overlap", "recovers": False},
                {"key": "e#1", "stem": "gamma", "how": "overlap", "recovers": True}]
        att = {"a#1": [("censuses", "tda")], "b#1": [("censuses", "tda"), ("ipip", "g600")],
               "e#1": [("censuses", "tda")]}
        br = RC.generator_breakdown(hd, results, rows, att)
        c, i = br["by_generator"]["censuses"], br["by_generator"]["ipip"]
        assert (c["n_kept"], c["n_recovered"], c["recall"], c["precision"]) == (2, 2, 0.5, 1.0)
        assert c["false_cover_candidates"] == 1 and c["hidden_missed_only_through_covers"] == 1 and c["n_copied"] == 1
        assert (i["n_kept"], i["n_recovered"], i["recall"], i["recovered"]) == (1, 1, 0.25, ["beta"])
        assert set(br["by_run"]) == {"censuses/tda", "ipip/g600"}
        assert c["recall_lo"] < 0.5 < c["recall_hi"]
        mean = RC.combine_breakdowns([{"breakdown": br}, {"breakdown": br}])
        assert mean["by_generator"]["ipip"]["recall"] == 0.25 and mean["by_generator"]["ipip"]["seeds"] == 2

    def test_wilson(self):
        lo, hi = RC.wilson(6, 83)
        assert 0.03 < lo < 0.0723 < hi < 0.16
        assert RC.wilson(0, 0) == (None, None) and RC.wilson(0, 10)[0] == 0.0
