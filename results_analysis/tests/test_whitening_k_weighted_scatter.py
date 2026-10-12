"""Regression test for the weighted-OLS line in
``results_analysis/whitening_k_weighted_scatter.py``.

Review 2026-10-12: the "weighted OLS" line was fitted with
``np.polyfit(xs, ys, 1, w=ws)``.  ``polyfit`` multiplies the unsquared
residuals by ``w``, so that minimised ``Σ w² r²``, not the ``Σ w r²`` the
per-axis weights (and the weighted Pearson beside it) mean.
"""
from __future__ import annotations

import numpy as np

from results_analysis.whitening_k_weighted_scatter import _weighted_ols


def _wls_closed_form(x, y, w):
    xm = np.average(x, weights=w)
    ym = np.average(y, weights=w)
    slope = np.sum(w * (x - xm) * (y - ym)) / np.sum(w * (x - xm) ** 2)
    return slope, ym - slope * xm


def test_weighted_ols_minimises_w_times_squared_residuals():
    x = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
    y = np.array([0.1, 0.9, 2.3, 2.8, 5.0])
    w = np.array([1.0, 4.0, 0.5, 2.0, 9.0])
    slope, intercept = _weighted_ols(x, y, w)
    ref_slope, ref_intercept = _wls_closed_form(x, y, w)
    assert np.isclose(slope, ref_slope)
    assert np.isclose(intercept, ref_intercept)
    # ... and is not the w**2-weighted fit the old call produced.
    old_slope, _ = np.polyfit(x, y, 1, w=w)
    assert not np.isclose(slope, old_slope)
