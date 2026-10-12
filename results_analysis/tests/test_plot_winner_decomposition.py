"""Regression test for the title of
``results_analysis/pc_round_trip/plot_winner_decomposition.py``.

Review 2026-10-12: the title and spec said "L=2 sheared space" /
"forward canonical L=2 shear" although the canonical cell has been raw
(``winner_decomposition.CANONICAL_L = 0``) since the May 2026 migration.
"""
from __future__ import annotations

import json
import sys

import numpy as np
from PIL import Image

from results_analysis.pc_round_trip import plot_winner_decomposition as mod
from results_analysis.pc_round_trip.winner_decomposition import CANONICAL_L


def test_title_names_the_canonical_shear_depth(tmp_path, monkeypatch):
    keys = [(pc, style, n) for pc in (1, 2)
            for style in ("glossary", "inline") for n in (1, 2, 3)]
    npz = tmp_path / "decomp.npz"
    matrix = np.full((4, len(keys)), 0.25, dtype=np.float32)
    np.savez(npz, matrix=matrix, column_keys=np.array(keys, dtype=object),
             meta=json.dumps({"_inputs": []}))
    out = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", [
        "plot_winner_decomposition.py", "--npz", str(npz),
        "--output", str(out)])
    assert mod.main() == 0
    title = Image.open(out).info["Title"]
    assert f"(L={CANONICAL_L} sheared space)" in title
