"""Regression test for ``load_named_subset`` in
``results_analysis/variance_decomposition.py``.

Review 2026-10-12: the helper skipped missing ``<name>.pt`` files while
the caller indexed the stack by each name's position in the list, so one
missing standalone would shift every later row and pair combinations
with the wrong role or trait vector.  It now raises instead.
"""
from __future__ import annotations

import numpy as np
import pytest
import torch

from results_analysis.variance_decomposition import load_named_subset


def _save(path, value):
    torch.save({"vector": torch.full((1, 1, 2), float(value))}, path)


def test_stacks_in_name_order(tmp_path):
    _save(tmp_path / "b.pt", 2)
    _save(tmp_path / "a.pt", 1)
    out = load_named_subset(tmp_path, ["b", "a"])
    assert out.shape == (2, 1, 1, 2)
    assert np.allclose(out[:, 0, 0, 0], [2.0, 1.0])


def test_missing_name_raises_instead_of_shifting(tmp_path):
    _save(tmp_path / "a.pt", 1)
    _save(tmp_path / "c.pt", 3)
    with pytest.raises(FileNotFoundError, match="'b'"):
        load_named_subset(tmp_path, ["a", "b", "c"])
