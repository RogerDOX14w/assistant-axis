"""scripts/judge_response_share_rate.py (2026-11-07): the share rows, the slopes and the stopping rule on a fake figure
JSON's points.  Pure functions only."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def sr():
    spec = importlib.util.spec_from_file_location("judge_response_share_rate", REPO / "scripts" / "judge_response_share_rate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fake_points(rhos, costs):
    """points for shares 10/15/20/25 of model m, format f, k=4: rhos[share][coverage] a mean rho (the 12 variants set so
    that six sit 0.01 above and six 0.01 below it), costs[share][coverage] the cost."""
    pts = {}
    for pct in rhos:
        for cov, key in [("ninth", "ninth x 3/3"), ("third", "1/3"), ("all", "all"), ("lift", "lift")]:
            r = rhos[pct][cov]
            pts[f"m@fx{pct}k4|{key}"] = dict(rho={f"v{i}": r + (0.01 if i % 2 else -0.01) for i in range(12)}, cost=costs[pct][cov])
    return pts


def test_rows_and_slopes(sr):
    rhos = {10: dict(ninth=0.70, third=0.72, all=0.73, lift=0.705), 15: dict(ninth=0.71, third=0.725, all=0.732, lift=0.715),
            20: dict(ninth=0.71, third=0.724, all=0.731, lift=0.715), 25: dict(ninth=0.709, third=0.723, all=0.730, lift=0.714)}
    costs = {10: dict(ninth=40, third=120, all=360, lift=40), 15: dict(ninth=45, third=135, all=405, lift=45),
             20: dict(ninth=50, third=150, all=450, lift=50), 25: dict(ninth=55, third=165, all=495, lift=55)}
    pts = fake_points(rhos, costs)
    rows = sr.share_rows(pts, "m", "f", 4)
    assert sorted(rows) == [10, 15, 20, 25]
    # the mean over panels of 1/(1-rho), not 1/(1-mean rho)
    expected = np.mean([1 / (1 - (0.70 + d)) for d in (0.01, -0.01) for _ in range(6)])
    assert rows[10]["ninth"]["quality"] == pytest.approx(expected)
    assert rows[10]["ninth"]["cost"] == 40
    sl = sr.share_slopes(rows)
    q = lambda pct, cov: rows[pct][cov]["quality"]
    assert sl["between_shares"]["ninth"]["10->15"] == pytest.approx(100 * (q(15, "ninth") - q(10, "ninth")) / 5)
    assert sl["third_to_all"][10] == pytest.approx(100 * (q(10, "all") - q(10, "third")) / 240)
    assert sl["lift_to_third"][10] == pytest.approx(100 * (q(10, "third") - q(10, "lift")) / 80)
    # the stopping rule: at "all" the 10->15 step (+0.002 of rho for $45) beats 15's third-to-all slope (+0.007 of rho
    # for $270), the 15->20 step is negative, so the share stops at 15
    assert sl["stops_at"]["all"] == 15
    assert sl["stops_at"]["ninth"] == 15
    wins = sr.panel_wins(pts, "m", "f", 4, [10, 15, 20, 25], "ninth x 3/3")
    assert wins["10->15"] == 12 and wins["15->20"] == 0
    text = sr.report(rows, sl, {"ninth": wins}, "t")
    assert "| 10% to 15% |" in text and "stops beating marginal coverage: ninth 15%" in text


def test_missing_arms_fail_loudly(sr):
    with pytest.raises(SystemExit):
        sr.share_rows({}, "m", "f", 4)
