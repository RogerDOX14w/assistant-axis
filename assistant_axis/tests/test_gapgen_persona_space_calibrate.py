"""Plan 12 § 8, ``calibrate``: the quantile tables, the percentile and the z-score, the flags; and the hard
calibration figures of the recorded pool (skipped where the vectors tree or the embedding cache is absent)."""
import numpy as np
import pytest

from assistant_axis.gapgen.persona_space import calibrate as CAL
from assistant_axis.gapgen.persona_space import fit as FIT
from assistant_axis.tests import persona_space_fakes as F
from assistant_axis.tests.test_gapgen_persona_space_fit import CFG, synthetic


def table_cal(**kw) -> CAL.Calibration:
    rp = np.linspace(0.1, 0.3, 101)                     # held-out predicted residuals: median 0.2
    d = dict(fit_id="f", N=20, alpha=0.3, residual_pred_quantiles=CAL.quantiles(rp),
             residual_true_quantiles=CAL.quantiles(rp + 0.2), self_cos_quantiles=CAL.quantiles(np.linspace(0.5, 0.9, 101)),
             nn_cos_pred_quantiles=CAL.quantiles(np.linspace(0.3, 0.8, 101)), dup_threshold=0.73, novel_pct=0.8,
             config_version="cfg", n_train=101, residual_pred_mean=0.2, residual_pred_sd=0.05)
    d.update(kw)
    return CAL.Calibration(**d)


class TestCalibration:
    def test_quantile_tables(self):
        q = CAL.quantiles(np.arange(101.0))
        assert len(q) == 21 and q[0] == 0 and q[10] == 50 and q[-1] == 100

    def test_percentile_is_monotone_and_half_at_the_median(self):
        cal = table_cal()
        assert CAL.residual_pct(0.2, cal) == pytest.approx(0.5)
        xs = np.linspace(0.0, 0.5, 200)
        p = CAL.residual_pct(xs, cal)
        assert np.all(np.diff(p) >= 0) and p[0] == 0.0 and p[-1] == 1.0
        assert CAL.residual_pct(0.29, cal) == pytest.approx(0.95, abs=0.01)    # 0.29 is the 95th percentile

    def test_percentile_with_repeated_quantiles(self):
        cal = table_cal(residual_pred_quantiles=CAL.quantiles(np.r_[np.zeros(50), np.linspace(0.1, 0.3, 51)]))
        p = CAL.residual_pct(np.linspace(0, 0.3, 50), cal)
        assert np.all(np.diff(p) >= 0)

    def test_z(self):
        cal = table_cal()
        assert CAL.residual_z(0.25, cal) == pytest.approx(1.0)
        assert CAL.residual_z(np.array([0.15, 0.2]), cal).tolist() == pytest.approx([-1.0, 0.0])

    def test_flags_on_the_three_regions(self):
        cal = table_cal()
        assert CAL.flag(0.80, 0.95, cal) == "duplicate_like"          # near an entity: duplicate wins
        assert CAL.flag(0.60, 0.85, cal) == "novel_like"
        assert CAL.flag(0.60, 0.50, cal) == "ordinary"
        assert CAL.flag(0.73, 0.10, cal) == "duplicate_like"          # at the threshold
        assert CAL.flag(0.70, 0.80, cal) == "novel_like"

    def test_from_cv_and_round_trip(self):
        pool, E, groups, _ = synthetic()
        cv = FIT.cross_validate(pool, E, groups, CFG)
        cal = CAL.from_cv(cv, fit_id="fit_x", config_version="cfg")
        h = cv.heldout[cv.alpha]
        assert cal.N == cv.N and cal.alpha == cv.alpha and cal.n_train == 240
        assert cal.dup_threshold == pytest.approx(np.median(h["cos"]), abs=1e-4)
        assert cal.novel_pct == 0.8 and cal.thresholds_set_by == "plan default"
        assert cal.cover_questioned_cos == pytest.approx(np.quantile(h["cos"], 0.1), abs=1e-4)
        assert set(cal.residual_pred_quantiles_by_N) == {"4", "8", "12"}
        back = CAL.Calibration.from_dict({"result": cal.as_dict()})
        assert back == cal
        moved = CAL.from_cv(cv, fit_id="fit_x", config_version="cfg", dup_threshold=0.8, novel_pct=0.9,
                            thresholds_set_by="Roger, gate 1")
        assert (moved.dup_threshold, moved.novel_pct, moved.thresholds_set_by) == (0.8, 0.9, "Roger, gate 1")


@pytest.mark.skipif(not F.real_data_present(), reason=F.REAL_REASON)
def test_real_calibration_hard():
    cv = F.real_cv_alpha03()
    cal = CAL.from_cv(cv, 24, alpha=0.3, fit_id="t", config_version="t")
    assert 0.68 <= cal.dup_threshold <= 0.78
    assert 0.12 <= cal.residual_pred_quantiles[10] <= 0.24          # the held-out predicted residual_24 median
    assert 0.32 <= cal.residual_true_quantiles[10] <= 0.40          # against the actual


def test_overlap_check_by_reading():
    pool, E, groups, _ = synthetic()
    cv = FIT.cross_validate(pool, E, groups, CFG)
    readings = [{"target": "e001", "listed": "e002", "reading": 3}, {"target": "e001", "listed": "e003", "reading": 3},
                {"target": "e002", "listed": "e000", "reading": 4},          # e000 is a role: not a trait pair
                {"target": "e005", "listed": "e006", "reading": "opposite"}, {"target": "nope", "listed": "e001",
                                                                             "reading": 0}]
    t = CAL.overlap_check(cv, pool, readings, dup_threshold=0.5)
    assert list(t) == ["3", "opposite"] and t["3"]["n"] == 2 and t["opposite"]["n"] == 1
    P = cv.heldout[cv.alpha]["P"]
    c = float(P[1] @ pool.M[2] / (np.linalg.norm(P[1]) * np.linalg.norm(pool.M[2])))
    c2 = float(P[1] @ pool.M[3] / (np.linalg.norm(P[1]) * np.linalg.norm(pool.M[3])))
    assert t["3"]["median_pred_cos"] == pytest.approx(np.median([c, c2]), abs=1e-4)


def test_base_rate_split():
    """Review of 2026-10-13, should-fix 1: the base rate splits into real neighbours and predictor false alarms, and
    the two parts add back to the base rate."""
    pool, E, groups, _ = synthetic()
    cv = FIT.cross_validate(pool, E, groups, CFG)
    cal = CAL.from_cv(cv, fit_id="fit_x", config_version="cfg")
    s = CAL.base_rate_split(cv, pool, dup_threshold=cal.dup_threshold)
    assert s["n"] == cal.n_train == 240
    near, fa, hit = s["share_with_neighbour"], s["false_alarm_rate"], s["hit_rate"]
    total = (near * (hit or 0)) + ((1 - near) * (fa or 0))
    assert total == pytest.approx(cal.dup_base_rate, abs=2e-3)
    if s["false_share_of_flags"] is not None:
        assert 0.0 <= s["false_share_of_flags"] <= 1.0


@pytest.mark.skipif(not F.real_data_present(), reason=F.REAL_REASON)
def test_real_base_rate_split():
    """The reviewer's figures at alpha 0.3, threshold 0.732: 37% with an actual neighbour, false alarms 13%."""
    cv, pool = F.real_cv_alpha03(), F.real_pool()
    s = CAL.base_rate_split(cv, pool, dup_threshold=0.732, alpha=0.3)
    assert 0.33 <= s["share_with_neighbour"] <= 0.41 and 0.10 <= s["false_alarm_rate"] <= 0.16
