"""Regression test: every ``--ca_kind`` choice offered by the soft-shear
scripts is a kind ``build_goal_nogoal_subspaces`` accepts.

Review 2026-10-12 (found by the results_analysis 9a reviewer): the
choices were ``("combined", "traits", "roles")`` in
``response_di_weight_sweep.py``, ``rho_by_layer.py`` and
``shear_l_sweep.py``, but the builder accepts only ``combined``,
``r_only`` and ``t_only``, so two of the three offered choices crashed.
The test reads the choices from each script's source (the parsers are
built inside ``main``).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces

RA = Path(__file__).resolve().parents[1]
SCRIPTS = ["response_di_weight_sweep.py", "rho_by_layer.py", "shear_l_sweep.py"]
ACCEPTED = {"combined", "r_only", "t_only"}


def _ca_kind_choices(path: Path) -> set[str]:
    for node in ast.walk(ast.parse(path.read_text())):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "attr", None) == "add_argument"
                and node.args and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "--ca_kind"):
            for kw in node.keywords:
                if kw.arg == "choices":
                    return set(ast.literal_eval(kw.value))
    raise AssertionError(f"no --ca_kind choices in {path}")


@pytest.mark.parametrize("script", SCRIPTS)
def test_ca_kind_choices_are_accepted_kinds(script):
    assert _ca_kind_choices(RA / script) <= ACCEPTED


@pytest.mark.parametrize("kind", ["traits", "roles"])
def test_builder_rejects_the_old_choices(tmp_path, kind):
    with pytest.raises(ValueError, match="Unknown kind"):
        build_goal_nogoal_subspaces(tmp_path, slot=0, layer=0, kind=kind)
