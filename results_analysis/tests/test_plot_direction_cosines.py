"""Regression test for the judge-score load in
``results_analysis/pc_round_trip/plot_direction_cosines.py``.

Review 2026-10-12: ``klm_sweep.load_combined_scores`` now lifts the v1
(bare-name) PC round-trip judge caches to entity ids with a
``kinds_for_name`` map, falling back to ``DEFAULT_DATA_DIR`` when the
caller passes none.  This script must pass the map built from its own
``--data_dir``.  The test stops ``main`` right after the score load (by
making ``setup_at`` raise) and checks what the loader received.
"""
from __future__ import annotations

import sys

import pytest

from results_analysis.pc_round_trip import plot_direction_cosines as mod


class _Stop(Exception):
    pass


def test_scores_lifted_against_the_runs_data_dir(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "traits" / "vectors").mkdir(parents=True)
    (data / "roles" / "vectors").mkdir(parents=True)
    for et, stem in (("traits", "patient"), ("roles", "patient"),
                     ("traits", "only_here")):
        (data / et / "vectors" / f"{stem}.pt").touch()

    seen = []

    def spy(cell, *, inputs=None, cell_id=None, kinds_for_name=None,
            data_dir=None):
        seen.append(kinds_for_name)
        return {}

    def stop(*a, **k):
        raise _Stop

    monkeypatch.setattr(mod, "load_combined_scores", spy)
    monkeypatch.setattr(mod, "setup_at", stop)
    monkeypatch.setattr(sys, "argv", [
        "plot_direction_cosines.py", "--data_dir", str(data),
        "--sweep_dir", str(tmp_path / "sweep"), "--pcs", "1",
        "--output", str(tmp_path / "out.png")])
    with pytest.raises(_Stop):
        mod.main()

    assert seen  # one call per (pc, style)
    assert all(k == {"patient": {"traits", "roles"},
                     "only_here": {"traits"}} for k in seen)
