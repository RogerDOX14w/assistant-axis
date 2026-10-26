"""``question_bootstrap``: the cluster bootstrap's weighting and summaries
(Roger, 2026-10-26: question-sampling noise in role vectors)."""
from __future__ import annotations

import numpy as np
import pytest

from results_analysis.question_bootstrap import boot_means, norm_and_angle, question_counts, question_index


def test_question_index_reads_the_key():
    assert question_index("pos_p3_q47") == 47
    assert question_index("default_p0_q0") == 0


def test_counts_draw_every_question_slot_once_per_replicate():
    q = np.arange(10)
    c = question_counts(q, B=50, seed=1)
    assert c.shape == (50, 10) and (c.sum(1) == 10).all()
    assert (question_counts(q, B=50, seed=1) == c).all()          # seeded


def test_boot_means_weight_rows_by_their_questions_count():
    X = np.array([[1.0, 0.0], [3.0, 0.0], [10.0, 2.0]])
    q = np.array([0, 0, 1])                       # two responses to question 0, one to question 1
    counts = np.array([[1, 1],                    # each question once: plain mean of the rows
                       [2, 0],                    # question 0 twice: its two rows only
                       [0, 0]])                   # nothing drawn: NaN
    m = boot_means(X, q, counts)
    assert m[0] == pytest.approx(X.mean(0))
    assert m[1] == pytest.approx([2.0, 0.0])
    assert np.isnan(m[2]).all()


def test_joint_draws_cancel_a_shared_question_effect():
    """A pull that a question gives the role and the default alike cancels in the default-centred
    vector when both are drawn jointly, and not when the default is held fixed."""
    rng = np.random.default_rng(0)
    Q, D = 40, 5
    effect = rng.normal(size=(Q, D)) * 3          # each question's shared pull
    q = np.repeat(np.arange(Q), 5)
    role = effect[q] + np.array([1.0, 0, 0, 0, 0])
    default = effect[q]
    counts = question_counts(np.arange(Q), B=300, seed=2)
    full = role.mean(0) - default.mean(0)
    joint = norm_and_angle(full, boot_means(role, q, counts) - boot_means(default, q, counts))
    fixed = norm_and_angle(full, boot_means(role, q, counts) - default.mean(0))
    assert joint["norm_sd_pct"] < 1e-6 and joint["median_angle_deg"] < 1e-4
    assert fixed["norm_sd_pct"] > 10


def test_norm_and_angle_leaves_out_nan_replicates():
    full = np.array([1.0, 0.0])
    boot = np.array([[1.0, 0.0], [np.nan, np.nan], [1.0, 1.0]])
    out = norm_and_angle(full, boot)
    assert out["n_replicates"] == 2
    assert out["median_angle_deg"] == pytest.approx(22.5)
