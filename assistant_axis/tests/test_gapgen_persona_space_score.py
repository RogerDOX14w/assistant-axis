"""Plan 12 § 8, ``score``: the candidates are M3's, the texts are ``label: gloss`` in ``w20``, the planted nearest
and pair-axis positions on the toy pool, the block's fields, and ``apply_blocks`` (decision 1a)."""
import json

import numpy as np
import pytest

from assistant_axis.gapgen import novelty_runner as NR
from assistant_axis.gapgen.persona_space import pool as POOL
from assistant_axis.gapgen.persona_space import score as SC
from assistant_axis.gapgen.registry import Registry, new_record
from assistant_axis.tests import persona_space_fakes as F
from assistant_axis.tests.test_gapgen_persona_space_calibrate import table_cal

GLOSS = "This means pursuing set goals with steady determination, measuring one's days by what gets accomplished and " \
        "treating each success as a step toward the next target."


def reg_row(stem, *, verdict="trait", gloss=GLOSS, holding=None, novelty=None, gen="ipip", run="r1", filtered=True,
            alignment=1, extra=None):
    r = new_record(stem.replace("_", " "))
    r["gloss"] = gloss
    r["holding"] = holding
    r["sources"] = [{"generator": gen, "run_id": run, "surface": stem}]
    r["filter"] = {"verdict": verdict, "alignment": alignment, "region": "moral_stance"} if filtered else None
    r["novelty"] = novelty
    r.update(extra or {})
    return r


def fixture_rows():
    rows = [reg_row("achievement_driven"), reg_row("tagged_one", verdict="tagged"), reg_row("unfiltered", filtered=False),
            reg_row("glossless", gloss="  "), reg_row("held_one", holding="nationalities"),
            reg_row("other_run", run="r2"),
            reg_row("released", verdict="tagged", holding="states_released",
                    extra={"states_pass": {"route": "lasting", "gloss": "This means staying put for years.",
                                           "alignment": 0, "checked": True}})]
    return {r["key"]: r for r in rows}


class TestCandidates:
    @pytest.mark.parametrize("holding", [None, "states", "physical"])
    def test_exactly_what_candidate_from_row_takes(self, holding):
        rows = fixture_rows()
        got, skipped = SC.candidates(rows, all_rows=True, holding=holding)
        want = []
        for k in sorted(rows):
            c, _ = NR.candidate_from_row(rows[k], holding=holding) if holding else NR.candidate_from_row(rows[k])
            if c is not None:
                want.append(c)
        assert got == want
        assert sum(skipped.values()) == len(rows) - len(got)
        if holding is None:
            assert [c.key for c in got] == ["achievement_driven#1", "held_one#1", "other_run#1"]
            assert skipped == {"not_a_trait": 2, "not_filtered": 1, "no_gloss": 1}

    def test_selection_by_run_and_keys(self):
        rows = fixture_rows()
        got, _ = SC.candidates(rows, run=[("ipip", "r2")])
        assert [c.key for c in got] == ["other_run#1"]
        got, _ = SC.candidates(rows, keys=["held_one#1", "achievement_driven#1"])
        assert [c.key for c in got] == ["held_one#1", "achievement_driven#1"]
        with pytest.raises(ValueError):
            SC.candidates(rows, run=[("ipip", "r2")], all_rows=True)
        with pytest.raises(KeyError):
            SC.candidates(rows, keys=["nope#1"])

    def test_texts_are_label_gloss_w20(self):
        c, _ = NR.candidate_from_row(fixture_rows()["achievement_driven#1"])
        t = SC.candidate_texts([c])[0]
        assert t.startswith("achievement driven: This means pursuing set goals")
        assert len(t.split(": ", 1)[1].split()) <= 20


@pytest.fixture
def toy(tmp_path):
    data = F.write_toy_corpus(tmp_path / "data")
    pool = POOL.pool_from_space(F.toy_space(), data)
    return data, pool, POOL.pair_partners(pool, data)


def cands(*keys):
    return [NR.M3Candidate(key=k, stem=k.split("#")[0], label=k.split("#")[0], gloss="g", alignment_score=1,
                           region=None, generators=["ipip"]) for k in keys]


class TestScoreVectors:
    def test_planted_nearest_and_pair_axis(self, toy):
        _, pool, partners = toy
        M = pool.M
        brave, coward, t07 = M[pool.row("brave|T")], M[pool.row("cowardly|T")], M[pool.row("t07|T")]
        rng = np.random.default_rng(3)
        P = np.stack([t07 + 0.01 * rng.standard_normal(M.shape[1]), brave, (brave + coward) / 2,
                      M[pool.row("angel|R")] + 0.01 * rng.standard_normal(M.shape[1])])
        cal = table_cal(N=4, residual_pred_quantiles_by_N={})
        out = SC.score_vectors(P, cands("a#1", "b#1", "c#1", "d#1"), pool, cal, Ns=(4, 8), partners=partners)
        assert out[0].nn["id"] == "t07|T" and out[0].nn["cos"] > 0.99 and out[0].pair_axis is None
        assert out[0].flag == "duplicate_like"
        assert out[1].pair_axis["a"] == "brave|T" and out[1].pair_axis["b"] == "cowardly|T"
        assert out[1].pair_axis["position"] == pytest.approx(1.0, abs=1e-6)
        assert out[2].pair_axis["position"] == pytest.approx(0.0, abs=1e-6)
        assert out[3].nn == {"id": "angel|R", "kind": "roles", "cos": out[3].nn["cos"]}
        assert out[3].nearest_traits[0][0].endswith("|T") and out[3].nn_cos_by_kind["R"] > out[3].nn_cos_by_kind["T"]
        assert set(out[0].residual_by_N) == {"4", "8"} and out[0].residual == out[0].residual_by_N["4"]
        # the neighbour lists never name a row that does not train
        listed = {a for s in out for a, _ in s.nearest + s.nearest_traits}
        assert not listed & {"lost|T", "ghost|R", "savage|T"}

    def test_pair_axis_position_formula(self):
        a, b = np.array([1.0, 0.0]), np.array([0.0, 1.0])
        assert SC.pair_axis_position(a, a, b) == pytest.approx(1.0)
        assert SC.pair_axis_position(b, a, b) == pytest.approx(-1.0)
        assert SC.pair_axis_position((a + b) / 2, a, b) == pytest.approx(0.0)


def score_row_fixture(pool, partners, rows, key="achievement_driven#1"):
    P = pool.M[[pool.row("t07|T")]]
    cal = table_cal(N=4, residual_pred_quantiles_by_N={})
    s = SC.score_vectors(P, cands(key), pool, cal, Ns=(4,), partners=partners)
    return SC.score_rows(s, P, rows, pool, batch_id="b1", at="2026-10-14T10:00:00+00:00")


class TestBlock:
    def test_block_fields_and_no_vector(self, toy):
        _, pool, partners = toy
        rows = fixture_rows()
        rows["achievement_driven#1"]["novelty"] = {"decision": "new", "listed": [{"stem": "t03", "rank": 1,
                                                                                  "cosine": 0.38}]}
        r = score_row_fixture(pool, partners, rows)[0]
        b = SC.persona_block(r)
        assert tuple(b) == SC.BLOCK_FIELDS
        assert b["version"] == 1 and b["batch_id"] == "b1" and b["m3_decision"] == "new" and b["m3_listed_first"] == "t03"
        assert b["nn"] == {"id": "t07|T", "cos": pytest.approx(1.0, abs=1e-4)}
        assert b["flag"] in ("duplicate_like", "novel_like", "ordinary") and b["disagreement"] is None
        flat = json.dumps(b)
        assert len(flat) < 800                                    # no vector on the row
        for k in SC.ROW_FIELDS:
            assert k in r


class TestApplyBlocks:
    def test_merges_the_block_only_and_is_idempotent(self, toy, tmp_path):
        _, pool, partners = toy
        rows = fixture_rows()
        rows["achievement_driven#1"]["novelty"] = {"decision": "new", "listed": [{"stem": "t03", "rank": 1,
                                                                                  "cosine": 0.38}],
                                                   "readings": [{"stem": "t03", "sonnet": {"value": 2}}]}
        reg = Registry(tmp_path / "registry.jsonl")
        reg.write(list(rows.values()))
        before = reg.fold()["achievement_driven#1"]
        srows = score_row_fixture(pool, partners, rows)
        assert SC.apply_blocks(reg, srows, "b1") == 1
        after = reg.fold()["achievement_driven#1"]
        assert json.dumps(after["novelty"], sort_keys=True) == json.dumps(before["novelty"], sort_keys=True)
        changed = {k for k in after if after[k] != before.get(k)}
        assert "persona" in changed and changed <= {"persona", "rev", "updated_at"}    # the same second: no updated_at
        assert after["persona"] == SC.persona_block(srows[0])
        n_lines = len((tmp_path / "registry.jsonl").read_text().splitlines())
        assert SC.apply_blocks(reg, srows, "b1") == 0                # applied twice: nothing new
        assert len((tmp_path / "registry.jsonl").read_text().splitlines()) == n_lines
        # a reading (decision 2b) changes the block, and only the block
        reading = {"stem": "t07", "sonnet": 2, "opus": None, "verdict": "keep", "at_cut_off": False}
        assert SC.apply_blocks(reg, srows, "b1", readings={"achievement_driven#1": reading}) == 1
        assert reg.fold()["achievement_driven#1"]["persona"]["reading"] == reading
        missing = []
        other = dict(srows[0], key="not_there#1")
        assert SC.apply_blocks(reg, [other], "b1", missing=missing) == 0 and missing == ["not_there#1"]
        with pytest.raises(ValueError):
            SC.apply_blocks(reg, srows, "another_batch")
