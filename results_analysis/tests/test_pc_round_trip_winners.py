"""PC round-trip: per-cell nth_pc winners and the winner decomposition.

Regression for the 2026-10-12 code review, walk-through D1 (review item
"Review 9b D2"):

- ``klm_sweep.py`` kept only the global winner per (PC, style), so no
  per-cell nth_pc winners existed for the 7-cell sweep and
  ``winner_decomposition.py`` fell back to the *fixed_principled* per-cell
  winners file: its "nth_pc winner" figure decomposed the nth PC at the
  configurations another search had chosen.  The sweep now records the
  per-cell winners of both stages, and the decomposition reads them.
- ``winner_decomposition.py`` built its columns from the first n = 1..3
  cells of the 7-cell order, so every winner at (6, 49), (0, 26), (0, 49)
  or (3, 25) was silently left out.  The levels are now n = 1, 2, 4, 6, 7
  and a winner no level reaches is reported.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.plot_metadata import json_metadata
from results_analysis.pc_round_trip import klm_sweep
from results_analysis.pc_round_trip import winner_decomposition as wd
from results_analysis.pc_round_trip.klm_sweep import (
    DEFAULT_CONFIGS, global_from_per_cell, serialise_results,
)


N_ENT, DIM = 40, 12
PCS = [1, 2, 3]
STYLES = ["glossary", "inline"]


# ---------------------------------------------------------------------------
# klm_sweep: per-cell winners
# ---------------------------------------------------------------------------

def _fake_setup_at(_data_dir, slot, layer):
    """Synthetic cell: entity matrix and pool depend on the cell, so each
    cell has its own PCs and its own winners."""
    rng = np.random.default_rng(1000 * slot + layer)
    names = [f"e{i}|T" for i in range(N_ENT)]
    M_raw = rng.normal(size=(N_ENT, DIM)).astype(np.float32)
    M_raw *= np.linspace(3.0, 0.5, DIM, dtype=np.float32)
    pool = rng.normal(size=(N_ENT + 5, DIM)).astype(np.float32)
    return names, M_raw, None, None, pool


def _scores() -> dict:
    rng = np.random.default_rng(7)
    return {(pc, s): {f"e{i}|T": float(rng.normal()) for i in range(N_ENT)}
            for pc in PCS for s in STYLES}


@pytest.fixture
def fake_cells(monkeypatch):
    monkeypatch.setattr(klm_sweep, "setup_at", _fake_setup_at)


def _run_stage2(configs):
    return klm_sweep.stage2_k_refinement(
        _scores(), data_dir=Path("unused"), configs=configs, l_values=[0],
        k_coarse=[0, 1, 2], pcs=PCS, styles=STYLES)


def _run_stage1(configs):
    return klm_sweep.stage1_m_sweep(
        _scores(), data_dir=Path("unused"), configs=configs, l_values=[0],
        k_coarse=[0, 1], m_values=[None, 6], pcs=PCS, styles=STYLES)


@pytest.mark.parametrize("run", [_run_stage1, _run_stage2],
                         ids=["stage1", "stage2"])
def test_sweep_records_a_winner_for_every_cell(fake_cells, run):
    _global, per_cell = run(DEFAULT_CONFIGS)
    expected = {(pc, s, slot, layer) for pc in PCS for s in STYLES
                for slot, layer in DEFAULT_CONFIGS}
    assert set(per_cell) == expected
    assert len(DEFAULT_CONFIGS) == 7


@pytest.mark.parametrize("run", [_run_stage1, _run_stage2],
                         ids=["stage1", "stage2"])
def test_per_cell_winner_is_that_cells_own_search(fake_cells, run):
    """A cell's per-cell entry equals the global winner of a sweep over that
    cell alone, and the global winner is the best of the per-cell ones."""
    global_all, per_cell = run(DEFAULT_CONFIGS)
    for cell in DEFAULT_CONFIGS:
        alone, _ = run([cell])
        for (pc, s), v in alone.items():
            assert per_cell[(pc, s, *cell)] == (v[0], *v[3:])
    for (pc, s), v in global_all.items():
        best = max(per_cell[(pc, s, *c)][0] for c in DEFAULT_CONFIGS)
        assert v[0] == best
        assert per_cell[(pc, s, v[1], v[2])][0] == best


def test_global_from_per_cell_breaks_ties_by_cell_order():
    configs = [(7, 25), (0, 26), (3, 25)]
    per_cell = {
        (1, "glossary", 3, 25): (0.5, 2, 4),
        (1, "glossary", 0, 26): (0.5, 1, 1),   # same ρ, earlier cell
        (1, "glossary", 7, 25): (0.4, 0, 0),
    }
    assert global_from_per_cell(per_cell, configs) == {
        (1, "glossary"): (0.5, 0, 26, 1, 1)}


def test_cache_round_trip_into_the_decomposition_loader(tmp_path):
    stage2_per_cell = {
        (pc, s, slot, layer): (0.1 * pc + 0.01 * slot, 0, slot % 3)
        for pc in PCS for s in STYLES for slot, layer in DEFAULT_CONFIGS}
    stage1_per_cell = {k: (v[0], v[1], v[2], None)
                       for k, v in stage2_per_cell.items()}
    stage2 = global_from_per_cell(stage2_per_cell, DEFAULT_CONFIGS)
    stage1 = global_from_per_cell(stage1_per_cell, DEFAULT_CONFIGS)
    payload = serialise_results(
        stage1, stage2, pcs=PCS, styles=STYLES,
        stage1_per_cell=stage1_per_cell, stage2_per_cell=stage2_per_cell,
        configs=DEFAULT_CONFIGS)
    # The global sections keep their old shape (downstream plots read them).
    g = payload["stage2_K_refinement_M_inf"]["pc001_glossary"]
    assert set(g) == {"rho", "slot", "layer", "L", "K"}
    assert payload["stage2_K_refinement_M_inf_per_cell"][
        "pc002_inline_s6_l49"] == {"rho": pytest.approx(0.26), "L": 0, "K": 0}
    assert payload["cell_order"] == [list(c) for c in DEFAULT_CONFIGS]

    path = tmp_path / "pc_round_trip_klm_results.json"
    path.write_text(json.dumps(json_metadata(payload, inputs=[], title="t")))
    source: dict = {}
    per_cell = wd.load_per_cell_winners(path, policy="off", source=source)
    assert source["variant"] == "nth_pc"
    assert source["section"] == wd.KLM_PER_CELL_SECTION
    assert set(per_cell) == set(stage2_per_cell)
    for k, (rho, L, K) in stage2_per_cell.items():
        assert per_cell[k] == {"rho": pytest.approx(rho), "L": L, "K": K}


# ---------------------------------------------------------------------------
# winner_decomposition: inputs
# ---------------------------------------------------------------------------

def test_loader_refuses_a_klm_cache_without_per_cell_winners(tmp_path):
    old = {"stage1_M_sweep": {}, "stage2_K_refinement_M_inf": {
        "pc001_glossary": {"rho": 0.9, "slot": 6, "layer": 49, "L": 4, "K": 0}}}
    path = tmp_path / "klm.json"
    path.write_text(json.dumps(json_metadata(old, inputs=[], title="t")))
    with pytest.raises(ValueError, match="per-cell"):
        wd.load_per_cell_winners(path, policy="off")


def test_loader_still_reads_a_flat_per_cell_file_and_names_its_variant(tmp_path):
    flat = {"pc001_glossary_s3_l25": {"rho": 0.8, "L": 5, "K": 0},
            "pc012_inline_s0_l49": {"rho": 0.3, "L": 0, "K": 22}}
    for tag in ("nth_pc", "fixed_principled"):
        path = tmp_path / f"pc_round_trip_{tag}_per_cell_winners_3-25_0-49.json"
        path.write_text(json.dumps(flat))
        source: dict = {}
        per_cell = wd.load_per_cell_winners(path, policy="off", source=source)
        assert source["variant"] == tag
        assert per_cell == {(1, "glossary", 3, 25): flat["pc001_glossary_s3_l25"],
                            (12, "inline", 0, 49): flat["pc012_inline_s0_l49"]}
    other = tmp_path / "winners.json"
    other.write_text(json.dumps(flat))
    source = {}
    wd.load_per_cell_winners(other, policy="off", source=source)
    assert source["variant"] == "unknown"


def test_default_input_is_the_nth_pc_sweep_cache():
    assert wd.DEFAULT_PER_CELL_PATH == klm_sweep.DEFAULT_CACHE_PATH


# ---------------------------------------------------------------------------
# winner_decomposition: every cell reaches a column
# ---------------------------------------------------------------------------

def _canonical(dim: int = 8):
    eye = np.eye(dim, dtype=np.float32)
    return ([], np.zeros((1, dim), np.float32), None,
            np.zeros((1, dim), np.float32), eye)


def _fake_direction_factory(calls: list):
    def fake(pc, slot, layer, L_w, K_w, **_kw):
        calls.append((pc, slot, layer, L_w, K_w))
        d = np.zeros(8, dtype=np.float32)
        d[(slot + layer) % 8] = 1.0          # mass on a cell-specific row
        return d
    return fake


def _per_cell_one_winner_per_pc(cells_by_pc: dict[int, tuple[int, int]]):
    """For each pc, every cell scores 0.1 except one, the winner, at 0.9."""
    out = {}
    for pc, win in cells_by_pc.items():
        for s in wd.DEFAULT_STYLES:
            for cell in wd.DEFAULT_CELL_ORDER:
                out[(pc, s, *cell)] = {"rho": 0.9 if cell == win else 0.1,
                                       "L": 0, "K": 0}
    return out


def test_winners_at_every_cell_reach_the_all_cell_column(capsys):
    # One target PC per cell the old n_max = 3 never reached.
    tail = [(6, 49), (0, 26), (0, 49), (3, 25)]
    cells_by_pc = {pc: cell for pc, cell in zip((1, 2, 3, 4), tail)}
    per_cell = _per_cell_one_winner_per_pc(cells_by_pc)
    calls: list = []
    matrix, keys, meta = wd.compute_decomposition_matrix(
        per_cell, data_dir=Path("unused"), pcs=list(cells_by_pc),
        _canonical=_canonical(), _direction_fn=_fake_direction_factory(calls))

    assert tuple(meta["n_values"]) == wd.DEFAULT_N_VALUES == (1, 2, 4, 6, 7)
    assert meta["uncovered_cells"] == []
    assert "WARNING" not in capsys.readouterr().err
    decomposed_cells = {(c[1], c[2]) for c in calls}
    assert set(tail) <= decomposed_cells
    rows = {(r["pc"], r["style"], r["n"]): r for r in meta["rows"]}
    for pc, cell in cells_by_pc.items():
        r = rows[(pc, "glossary", 7)]
        assert (r["slot"], r["layer"]) == cell
        col = keys.index((pc, "glossary", 7))
        assert matrix[(cell[0] + cell[1]) % 8, col] == pytest.approx(1.0)
    # A shared winner is mapped once per (pc, cell, L, K), not per column.
    assert len(calls) == len(set(calls))


def test_column_levels_follow_the_n_values():
    per_cell = _per_cell_one_winner_per_pc({1: (0, 49)})
    _m, keys, meta = wd.compute_decomposition_matrix(
        per_cell, data_dir=Path("unused"), pcs=[1],
        _canonical=_canonical(), _direction_fn=_fake_direction_factory([]))
    assert keys == [(1, s, n) for s in wd.DEFAULT_STYLES
                    for n in wd.DEFAULT_N_VALUES]
    rows = {(r["pc"], r["style"], r["n"]): r for r in meta["rows"]}
    # (0, 49) is the 6th cell: levels 1-4 take the best of the earlier
    # cells, 6 and 7 the winner.
    assert [(rows[(1, "inline", n)]["slot"], rows[(1, "inline", n)]["layer"])
            for n in (6, 7)] == [(0, 49), (0, 49)]
    assert all(rows[(1, "inline", n)]["rho"] == pytest.approx(0.1)
               for n in (1, 2, 4))


def test_a_winner_no_level_reaches_is_reported(capsys):
    per_cell = _per_cell_one_winner_per_pc({1: (3, 25)})
    _m, _k, meta = wd.compute_decomposition_matrix(
        per_cell, data_dir=Path("unused"), pcs=[1], n_values=(1, 2, 3),
        _canonical=_canonical(), _direction_fn=_fake_direction_factory([]))
    assert meta["uncovered_cells"] == [[0, 26], [0, 49], [3, 25], [6, 49]]
    err = capsys.readouterr().err
    assert "WARNING" in err and "(3, 25)" in err
