"""Regression tests for the title and layout of
``results_analysis/pc_round_trip/plot_winner_decomposition.py``.

Review 2026-10-12: the title and spec said "L=2 sheared space" /
"forward canonical L=2 shear" although the canonical cell has been raw
(``winner_decomposition.CANONICAL_L = 0``) since the May 2026 migration.

Walk-through D1 (same review): the title said "nth_pc winner" whatever
winners the npz was built from (the May 9 figure was built on the
fixed_principled configurations), and the strip layout was hard-coded to
6 columns (n = 1..3).  The title now comes from ``meta["winners_source"]``
and the layout from the column keys.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pytest
from PIL import Image

from results_analysis.pc_round_trip import plot_winner_decomposition as mod
from results_analysis.pc_round_trip.winner_decomposition import (
    CANONICAL_L, DEFAULT_N_VALUES, LAYER_C, SLOT_C,
)


def _write_npz(tmp_path, keys, meta):
    npz = tmp_path / "decomp.npz"
    matrix = np.full((4, len(keys)), 0.25, dtype=np.float32)
    np.savez(npz, matrix=matrix, column_keys=np.array(keys, dtype=object),
             meta=json.dumps(meta))
    return npz


def _render_title(tmp_path, monkeypatch, keys, meta) -> str:
    npz = _write_npz(tmp_path, keys, meta)
    out = tmp_path / "out.png"
    monkeypatch.setattr(sys, "argv", [
        "plot_winner_decomposition.py", "--npz", str(npz),
        "--output", str(out)])
    assert mod.main() == 0
    return Image.open(out).info["Title"]


def test_title_names_the_canonical_shear_depth(tmp_path, monkeypatch):
    # Expectation changed 2026-10-12 (walk-through D1, retitle): the title
    # used to end "(L=0 sheared space)"; it now names the canonical cell
    # as "(slot 7, layer 25, L=0 raw)".  The point of the test is
    # unchanged: the canonical shear depth is CANONICAL_L, never L=2.
    keys = [(pc, style, n) for pc in (1, 2)
            for style in ("glossary", "inline") for n in (1, 2, 3)]
    title = _render_title(tmp_path, monkeypatch, keys, {"_inputs": []})
    assert f"L={CANONICAL_L}" in title
    assert f"slot {SLOT_C}, layer {LAYER_C}" in title
    assert "L=2" not in title


def test_title_says_nth_pc_only_for_nth_pc_winners(tmp_path, monkeypatch):
    keys = [(pc, style, n) for pc in (1, 2)
            for style in ("glossary", "inline") for n in DEFAULT_N_VALUES]
    nth = _render_title(tmp_path, monkeypatch, keys, {
        "_inputs": [],
        "winners_source": {"variant": "nth_pc", "path": "x", "section": "s"}})
    assert "nth_pc search winners" in nth

    fixed = _render_title(tmp_path, monkeypatch, keys, {
        "_inputs": [],
        "winners_source": {"variant": "fixed_principled", "path": "x",
                           "section": None}})
    assert "nth_pc" not in fixed
    assert "fixed_principled" in fixed

    unknown = _render_title(tmp_path, monkeypatch, keys, {"_inputs": []})
    assert "nth_pc" not in unknown


def test_strip_layout_reads_the_n_levels_from_the_keys():
    keys = [(pc, style, n) for pc in (4, 8)
            for style in ("glossary", "inline") for n in DEFAULT_N_VALUES]
    pcs, width, styles, n_values = mod.strip_layout(keys)
    assert pcs == [4, 8]
    assert width == 2 * len(DEFAULT_N_VALUES) == 10
    assert styles == ["glossary", "inline"]
    assert n_values == list(DEFAULT_N_VALUES)


def test_strip_layout_rejects_ragged_strips():
    keys = [(1, "glossary", 1), (1, "inline", 1), (2, "glossary", 1)]
    with pytest.raises(ValueError):
        mod.strip_layout(keys)
