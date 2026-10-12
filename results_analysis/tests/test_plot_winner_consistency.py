"""Regression tests for ``results_analysis/pc_round_trip/plot_winner_consistency.py``.

Review 2026-10-12:

* The L panel stacked a fixed ``[0, 1, 2, 3, 5]`` grid while klm_sweep's
  grid is ``[0, 1, 2, 4]``: every L=4 winner (14 of 48 actual, 1,317 of
  4,800 null in the May 2026 caches) was left out, so the bars did not
  sum to 1.
* The (slot, layer) colour map still held the three 4-slot-era cells;
  four of the seven post-migration cells all drew grey.
"""
from __future__ import annotations

import json
import sys

from results_analysis.pc_round_trip import plot_winner_consistency as mod
from results_analysis.pc_round_trip.klm_sweep import (
    DEFAULT_CONFIGS, DEFAULT_L_VALUES,
)


def test_l_values_cover_every_winner():
    actual = {"pc001_glossary": {"L": 4}, "pc001_inline": {"L": 0}}
    null = {"pc001_glossary_p0": {"L": 2}, "pc001_glossary_p1": {"L": 4}}
    assert mod._l_values(actual, null) == [0, 2, 4]


def test_every_klm_cell_has_its_own_colour():
    colours = [mod.CONFIG_COLORS.get(tuple(c)) for c in DEFAULT_CONFIGS]
    assert None not in colours
    assert len(set(colours)) == len(colours)


def test_main_renders(tmp_path, monkeypatch):
    def winners(n_per_pc):
        out = {}
        for pc in (1, 2):
            for i in range(n_per_pc):
                L = DEFAULT_L_VALUES[i % len(DEFAULT_L_VALUES)]
                s, layer = DEFAULT_CONFIGS[i % len(DEFAULT_CONFIGS)]
                out[f"pc{pc:03d}_s{i}"] = {"K": i, "L": L, "slot": s,
                                            "layer": layer, "rho": 0.1}
        return out

    actual = tmp_path / "actual.json"
    null = tmp_path / "null.json"
    actual.write_text(json.dumps({"stage2_K_refinement_M_inf": winners(2)}))
    null.write_text(json.dumps({"stage2": winners(8)}))
    out = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", [
        "plot_winner_consistency.py", "--actual", str(actual),
        "--null", str(null), "--output", str(out)])
    assert mod.main() == 0
    assert out.exists()
