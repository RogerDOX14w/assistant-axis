"""Plan 12 § 8, ``compare``: the agreement with M3 and the three disagreement kinds on a fixture registry with
planted covered and new rows, hand-computed; the quantile cap."""
import pytest

from assistant_axis.gapgen.persona_space import compare as CMP
from assistant_axis.tests.test_gapgen_persona_space_calibrate import table_cal


def srow(key, *, t_cos, nearest_traits=None, nn=None, pct=0.5, flag="ordinary", gens=("g1",), cov=None, cov_cos=None):
    nt = nearest_traits or [["x1|T", t_cos], ["x2|T", t_cos - 0.05], ["x3|T", t_cos - 0.1]]
    return {"key": key, "label": key.split("#")[0], "generators": list(gens), "N": 20, "residual": 0.2,
            "residual_pct": pct, "flag": flag, "nn": nn or {"id": nt[0][0], "cos": t_cos},
            "nearest_traits": nt, "nn_cos_by_kind": {"T": t_cos, "R": 0.1}, "m3_covered_by": cov,
            "cos_to_covered_by": cov_cos, "m3_decision": None, "m3_listed_first": None, "m3_cosine": None}


def rrow(key, decision, *, covered_by=None, first="z1", cos=0.4):
    return {"key": key, "novelty": {"decision": decision, "covered_by": covered_by,
                                    "listed": [{"stem": first, "rank": 1, "cosine": cos}]}}


def fixture():
    # covered: c1 (nearest trait cos 0.90, covered by its nearest x1), c2 (0.80, covered by x2: second nearest),
    # c3 (0.35, covered by far_away: not among its three nearest, cosine 0.10, residual pct 0.95)
    # new: n1 (0.85, duplicate-like), n2 (0.30), n3 (0.20)
    scores = [srow("c1#1", t_cos=0.90, cov="x1", cov_cos=0.90, gens=("g1",)),
              srow("c2#1", t_cos=0.80, cov="x2", cov_cos=0.75, gens=("g2",)),
              srow("c3#1", t_cos=0.35, cov="far_away", cov_cos=0.10, pct=0.95, flag="novel_like", gens=("g2",)),
              srow("n1#1", t_cos=0.85, flag="duplicate_like", gens=("g1",)),
              srow("n2#1", t_cos=0.30, gens=("g1",)),
              srow("n3#1", t_cos=0.20, gens=("g2",))]
    rows = {"c1#1": rrow("c1#1", "covered", covered_by="x1", cos=0.6),
            "c2#1": rrow("c2#1", "covered", covered_by="x2", cos=0.5),
            "c3#1": rrow("c3#1", "covered", covered_by="far_away", cos=0.3),
            "n1#1": rrow("n1#1", "new", cos=0.55), "n2#1": rrow("n2#1", "new", cos=0.2),
            "n3#1": rrow("n3#1", "new", cos=0.1)}
    return scores, rows


class TestAgreement:
    def test_hand_computed(self):
        scores, rows = fixture()
        a = CMP.agreement(scores, rows)
        # covered (0.90, 0.80, 0.35) above new (0.85, 0.30, 0.20): 0.90 beats 3, 0.80 beats 2, 0.35 beats 2 -> 7 of 9
        assert a.auc_nn_cos_covered_vs_new == pytest.approx(7 / 9, abs=1e-4)
        # covered_by: x1 is c1's nearest; x2 is c2's second; far_away is not among c3's three -> 1/3 and 2/3
        assert a.covered_by_is_nearest == pytest.approx(1 / 3, abs=1e-4)
        assert a.covered_by_in_top3 == pytest.approx(2 / 3, abs=1e-4)
        assert a.n_covered_by_with_vector == 3
        # persona nearest-trait cosine against M3's first cosine: the same order -> 1.0
        assert a.spearman_nn_cos_vs_m3_cosine == pytest.approx(1.0)
        assert a.flags == {"duplicate_like": 1, "novel_like": 1, "ordinary": 4}
        assert a.m3 == {"covered": 3, "new": 3}
        assert a.by_generator["g1"]["n"] == 3 and a.by_generator["g2"]["flags"] == {"novel_like": 1, "ordinary": 2}

    def test_auc_ties_count_half(self):
        assert CMP.auc([0.5], [0.5]) == 0.5 and CMP.auc([1, 2], []) is None

    def test_a_covering_trait_without_a_vector_is_left_out(self):
        scores, rows = fixture()
        scores[2]["cos_to_covered_by"] = None                 # far_away has no vector
        assert CMP.agreement(scores, rows).n_covered_by_with_vector == 2


class TestDisagreements:
    def test_the_three_kinds(self):
        scores, rows = fixture()
        dis, counts = CMP.disagreements(scores, rows, table_cal(cover_questioned_cos=0.5), quantile=0.5)
        by = {(d.key, d.kind): d for d in dis}
        assert set(by) == {("n1#1", "dup_vs_new"), ("c3#1", "cover_questioned"), ("c3#1", "novel_vs_covered")}
        d = by[("n1#1", "dup_vs_new")]
        assert d.judge_stem == "x1" and d.persona_nearest == "x1|T" and d.m3_listed_first == "z1"
        assert "0.85 >= dup_threshold 0.73" in d.evidence
        assert by[("c3#1", "cover_questioned")].covered_by == "far_away"
        assert counts["dup_vs_new"] == {"met_rule": 1, "listed": 1} and counts["cap"] == 3
        CMP.mark_rows(scores, dis)
        assert {r["key"]: r.get("disagreement") for r in scores}["c3#1"] == "cover_questioned"
        assert {r["key"]: r.get("disagreement") for r in scores}["n1#1"] == "dup_vs_new"

    def test_a_cover_changed_since_scoring_is_not_read_from_the_old_cosine(self):
        scores, rows = fixture()
        rows["c3#1"]["novelty"]["covered_by"] = "x1"            # M3 re-decided: the recorded cosine is for far_away
        dis, _ = CMP.disagreements(scores, rows, table_cal(cover_questioned_cos=0.5), quantile=0.5)
        assert ("c3#1", "cover_questioned") not in {(d.key, d.kind) for d in dis}

    def test_the_quantile_cap(self):
        scores = [{"key": f"k{i}#1", "label": "k", "generators": ["g"], "N": 20, "residual": 0.2, "residual_pct": 0.5,
                   "flag": "duplicate_like", "nn": {"id": f"x{i}|T", "cos": 0.74 + i / 1000},
                   "nearest_traits": [[f"x{i}|T", 0.74 + i / 1000]], "nn_cos_by_kind": {"T": 0.74 + i / 1000},
                   "m3_covered_by": None, "cos_to_covered_by": None} for i in range(40)]
        rows = {s["key"]: rrow(s["key"], "new") for s in scores}
        dis, counts = CMP.disagreements(scores, rows, table_cal(), quantile=0.1)
        assert len(dis) == 4 and counts["dup_vs_new"] == {"met_rule": 40, "listed": 4}
        assert [d.key for d in dis] == ["k39#1", "k38#1", "k37#1", "k36#1"]          # the strongest first
        assert [d.rank for d in dis] == [1, 2, 3, 4]

    def test_markdown(self):
        scores, rows = fixture()
        dis, counts = CMP.disagreements(scores, rows, table_cal(cover_questioned_cos=0.5), quantile=0.5)
        md = CMP.markdown(dis, counts, batch_id="b1", cal=table_cal(),
                          readings={"n1#1": {"stem": "x1", "sonnet": 2, "opus": None, "verdict": "keep",
                                             "at_cut_off": False}})
        assert "## M3 new, persona space duplicate-like (`dup_vs_new`): 1 listed of 1" in md
        assert "(../../../../traits/instructions/x1.json)" in md and "Sonnet 2" in md
