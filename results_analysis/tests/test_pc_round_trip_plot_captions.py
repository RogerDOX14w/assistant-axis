"""Caption regressions for the PC round-trip plots regenerated on 2026-10-12
(code review regeneration list, rows PC1-PC6 and R12).

- The null cache has been the *fixed_principled* search since May 9 (its
  ``_meta.variant``), while the actual curve is the *nth_pc* search; the
  null-overlay and winner-consistency figures did not say so, and the
  winner-consistency spec read "2 actual draws look concentrated next to
  200 null draws" as "evidence the actual search is finding meaningful
  structure".  Both captions now name the null's search and draw no such
  inference.
- The histogram and log-lin specs said "K refined via bracket-and-bisect",
  true of the April grid up to K=512; on the K <= 4 grid the refinement
  never fires.
"""
from __future__ import annotations

import json
import sys

import pytest

from results_analysis.pc_round_trip import (
    plot_histogram, plot_loglin, plot_null_overlay, plot_winner_consistency,
)
from results_analysis.pc_round_trip.klm_sweep import DEFAULT_CONFIGS


def _capture_spec(monkeypatch, mod) -> list[str]:
    seen: list[str] = []
    real = mod.suptitle_with_specs

    def spy(fig, title, specs=None, **kw):
        seen.append(specs if isinstance(specs, str) else "\n".join(specs or []))
        return real(fig, title, specs, **kw)

    monkeypatch.setattr(mod, "suptitle_with_specs", spy)
    return seen


def _klm_cache(path, with_cell_order=True):
    s2 = {f"pc{pc:03d}_{st}": {"rho": 0.1 * pc + (0.01 if st == "inline" else 0),
                               "slot": 7, "layer": 25, "L": 0, "K": 0}
          for pc in (1, 2, 4) for st in ("glossary", "inline")}
    s1 = {k: dict(v, M=None) for k, v in s2.items()}
    payload = {"stage1_M_sweep": s1, "stage2_K_refinement_M_inf": s2}
    if with_cell_order:
        payload["cell_order"] = [list(c) for c in DEFAULT_CONFIGS]
    path.write_text(json.dumps(payload))
    return path


def _null_cache(path, variant):
    stage2 = {}
    for pc in (1, 2, 4):
        for st in ("glossary", "inline"):
            for p in range(3):
                stage2[f"pc{pc:03d}_{st}_p{p:03d}"] = {
                    "rho": 0.02 * p, "slot": 6, "layer": 25, "L": 2, "K": p}
    payload = {"stage2": stage2, "stage1": {}}
    if variant is not None:
        payload["_meta"] = {"variant": variant, "n_perms": 3}
    path.write_text(json.dumps(payload))
    return path


def _run(monkeypatch, mod, argv):
    monkeypatch.setattr(sys, "argv", [mod.__name__] + argv)
    assert mod.main() == 0


@pytest.mark.parametrize("variant", ["fixed_principled", None])
def test_null_overlay_names_the_nulls_search(tmp_path, monkeypatch, variant):
    seen = _capture_spec(monkeypatch, plot_null_overlay)
    _run(monkeypatch, plot_null_overlay, [
        "--actual", str(_klm_cache(tmp_path / "a.json")),
        "--null", str(_null_cache(tmp_path / "n.json", variant)),
        "--output", str(tmp_path / "o.png")])
    spec = seen[-1]
    assert "actual: nth_pc search" in spec
    if variant == "fixed_principled":
        assert "null: fixed_principled" in spec
        assert "not the nth_pc search's own" in spec
    else:   # a cache without the field is the May 6 nth_pc null
        assert "null: nth_pc" in spec
        assert "not the nth_pc search's own" not in spec


@pytest.mark.parametrize("variant", ["fixed_principled", None])
def test_winner_consistency_draws_no_concentration_inference(
        tmp_path, monkeypatch, variant):
    seen = _capture_spec(monkeypatch, plot_winner_consistency)
    _run(monkeypatch, plot_winner_consistency, [
        "--actual", str(_klm_cache(tmp_path / "a.json")),
        "--null", str(_null_cache(tmp_path / "n.json", variant)),
        "--output", str(tmp_path / "o.png")])
    spec = seen[-1]
    assert "evidence" not in spec
    assert "2 draws look concentrated whatever their source" in spec
    assert f"Null: {variant or 'nth_pc'} search" in spec
    assert "6 per PC" in spec          # 3 permutations x 2 styles


@pytest.mark.parametrize("mod", [plot_histogram, plot_loglin],
                         ids=["histogram", "loglin"])
@pytest.mark.parametrize("with_cell_order", [True, False])
def test_rho_plots_state_the_grid_not_the_old_refinement(
        tmp_path, monkeypatch, mod, with_cell_order):
    seen = _capture_spec(monkeypatch, mod)
    _run(monkeypatch, mod, [
        "--cache_path", str(_klm_cache(tmp_path / "a.json", with_cell_order)),
        "--output", str(tmp_path / "o.png")])
    spec = seen[-1]
    assert "bracket-and-bisect" not in spec
    assert "nth_pc search" in spec
    assert "{0,1,2,4}" in spec
    assert ("7 cells" in spec) == with_cell_order
