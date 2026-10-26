"""``rubric_version_vector_change.pair_stats``: the cosine and the norm change
between two versions of a role's default-centred vector (Roger, 2026-10-26:
the range of cosines and of percentage norm changes across rubric versions)."""
from __future__ import annotations

import numpy as np
import pytest

from results_analysis.rubric_version_vector_change import pair_stats


def test_identical_vectors_give_cos_one_and_no_norm_change():
    x = np.array([3.0, 4.0, 0.0])
    st = pair_stats(x, x.copy(), lambda v: v)
    assert st["cos"] == pytest.approx(1.0)
    assert st["norm_change_pct"] == pytest.approx(0.0)
    assert st["norm_base"] == pytest.approx(5.0)


def test_scaled_vector_keeps_direction_and_reports_percent_change():
    x = np.array([3.0, 4.0, 0.0])
    st = pair_stats(x, 1.1 * x, lambda v: v)
    assert st["cos"] == pytest.approx(1.0)
    assert st["norm_change_pct"] == pytest.approx(10.0)
    assert st["norm_change_pct_raw"] == pytest.approx(10.0)
    assert st["norm_other"] == pytest.approx(5.5)


def test_softened_and_raw_figures_are_kept_apart():
    # a transform that stretches the first axis: raw vectors are orthogonal-ish in
    # one space and not the other, and their norms change by different amounts
    stretch = np.diag([10.0, 1.0])
    xb, xo = np.array([1.0, 1.0]), np.array([1.0, 2.0])
    st = pair_stats(xb, xo, lambda v: stretch @ v)
    sb, so = stretch @ xb, stretch @ xo
    assert st["cos_raw"] == pytest.approx(xb @ xo / (np.linalg.norm(xb) * np.linalg.norm(xo)))
    assert st["cos"] == pytest.approx(sb @ so / (np.linalg.norm(sb) * np.linalg.norm(so)))
    assert st["norm_change_pct_raw"] == pytest.approx(100 * (np.sqrt(5) / np.sqrt(2) - 1))
    assert st["norm_change_pct"] == pytest.approx(100 * (np.linalg.norm(so) / np.linalg.norm(sb) - 1))
    assert st["norm_change_pct"] != pytest.approx(st["norm_change_pct_raw"])
