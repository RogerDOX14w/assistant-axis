"""Tests for the pure helpers of scripts/jev_plain_vs_relative.py."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "jev_plain_vs_relative", Path(__file__).resolve().parents[1] / "jev_plain_vs_relative.py")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
ARMS, COMPARISONS, compare, mean_of = _MODULE.ARMS, _MODULE.COMPARISONS, _MODULE.compare, _MODULE.mean_of


def test_mean_of_averages_each_entity_over_the_runs_that_scored_it():
    m = mean_of([{"a": 1.0, "b": 3.0}, {"a": 3.0}])
    assert m == {"a": 2.0, "b": 3.0}


def test_compare_is_paired_over_the_common_axes():
    rng = np.random.default_rng(0)
    a = {f"ax{i}": 0.7 + 0.01 * i for i in range(10)}
    b = {f"ax{i}": 0.7 for i in range(10)}
    b["ax0"] = 0.72                          # a trails on this one
    a["only_in_a"] = 0.9                     # left out
    c = compare(a, b, rng, n_boot=500)
    assert c["n_axes"] == 10
    assert c["mean"] == pytest.approx(np.mean([0.01 * i for i in range(10)]) - 0.002)
    assert c["lo"] <= c["mean"] <= c["hi"]
    assert c["a_ahead_on"] == 9
    assert c["worst_for_a"][0] == ("ax0", -0.02)
    assert c["best_for_a"][0] == ("ax9", 0.09)


def test_compare_with_no_common_axes():
    assert compare({"x": 0.5}, {"y": 0.5}, np.random.default_rng(0))["n_axes"] == 0


def test_every_comparison_names_arms_of_its_mode():
    for mode, pairs in COMPARISONS.items():
        for a, b in pairs:
            assert a in ARMS[mode] and b in ARMS[mode]
