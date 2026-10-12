"""PC round-trip score loading: v1 (bare-name) judge caches against the
entity-id keyed geometry.

Regression for the 2026-10-12 review finding: ``setup_at`` has keyed its
entity rows by entity id (``"helpful|T"``) since 2026-05-11, while every
judge cache under ``roger/pc_axis_describer_sweep/`` is schema v1 (bare
names), so ``load_combined_scores`` and the geometry never intersected and
every round-trip ρ came back ``None`` (and ``permutation_null`` would have
merged zero-ρ rows into its cache).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from results_analysis.pc_round_trip import klm_sweep
from results_analysis.pc_round_trip.klm_sweep import (
    kinds_for_name_from_data_dir,
    load_combined_scores,
    rho_for_direction,
)
from results_analysis.pc_round_trip.permutation_null import (
    build_permutation_score_arrays,
)


def _make_data_dir(root: Path, traits: list[str], roles: list[str]) -> Path:
    """Vector *names* only: the loader globs ``*.pt`` stems, never opens them."""
    for et, names in (("traits", traits), ("roles", roles)):
        vdir = root / et / "vectors"
        vdir.mkdir(parents=True)
        for n in names + ["default"]:
            (vdir / f"{n}.pt").write_bytes(b"")
    return root


def _make_cell(root: Path, scores: dict[str, int]) -> Path:
    cell = root / "pc001_glossary"
    for judge in ("gpt", "sonnet"):
        for mode in ("descriptions", "instructions"):
            p = cell / judge / f"scores_{mode}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(scores))
    return cell


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    klm_sweep._kinds_for_name_cached.cache_clear()
    return _make_data_dir(
        tmp_path / "data",
        traits=["helpful", "unhelpful", "patient", "honest"],
        roles=["angel", "demon", "patient"],
    )


def _names(data_dir: Path) -> list[str]:
    # The same construction as klm_sweep.setup_at (roles first, then traits).
    out = []
    for et, tag in (("roles", "R"), ("traits", "T")):
        for fp in sorted((data_dir / et / "vectors").glob("*.pt")):
            if fp.stem != "default":
                out.append(f"{fp.stem}|{tag}")
    return out


V1_SCORES = {"helpful": 3, "unhelpful": -3, "honest": 2,
             "angel": 3, "demon": -2, "patient": 1}


def test_v1_cache_is_lifted_to_entity_ids(tmp_path, data_dir):
    cell = _make_cell(tmp_path / "sweep", V1_SCORES)
    scores = load_combined_scores(cell, data_dir=data_dir)
    assert set(scores) == {"helpful|T", "unhelpful|T", "honest|T",
                           "angel|R", "demon|R"}
    # The collision stem cannot be attributed to a kind from a v1 cache.
    assert not any(k.startswith("patient") for k in scores)
    assert scores["helpful|T"] == pytest.approx(3.0)


def test_scores_now_intersect_the_geometry(tmp_path, data_dir):
    cell = _make_cell(tmp_path / "sweep", V1_SCORES)
    names = _names(data_dir)
    scores = load_combined_scores(
        cell, kinds_for_name=kinds_for_name_from_data_dir(data_dir))
    rng = np.random.default_rng(0)
    M_done = rng.standard_normal((len(names), 4))
    rho = rho_for_direction(M_done, names, np.array([1.0, 0, 0, 0]), scores)
    assert rho is not None  # was None for every cell before the fix


def test_v2_cache_passes_through(tmp_path, data_dir):
    v2 = {"helpful|T": 3, "patient|R": 1, "patient|T": -1}
    cell = _make_cell(tmp_path / "sweep", v2)
    scores = load_combined_scores(cell, data_dir=data_dir)
    assert set(scores) == set(v2)


def test_permutation_null_refuses_an_empty_overlap(data_dir):
    names = _names(data_dir)
    # Bare-name scores against entity-id names: the pre-fix situation.
    with pytest.raises(ValueError, match="do not match"):
        build_permutation_score_arrays(
            {(1, "glossary"): {"helpful": 3.0, "unhelpful": -3.0}},
            names, n_perms=2, seed=0)


def test_permutation_null_builds_with_lifted_scores(tmp_path, data_dir):
    cell = _make_cell(tmp_path / "sweep", V1_SCORES)
    names = _names(data_dir)
    scores = load_combined_scores(cell, data_dir=data_dir)
    _ranks, valid, ranks_c, normsq = build_permutation_score_arrays(
        {(1, "glossary"): scores}, names, n_perms=3, seed=0)
    assert int(valid[(1, "glossary")].sum()) == 5
    assert ranks_c[(1, "glossary")].shape == (3, 5)
