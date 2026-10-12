"""Regression test for the axis counts in ``rho_by_slot_and_K.py`` and
``rho_by_slot_and_L.py``.

Review 2026-10-12: the title and x-labels reported the pair-list length
(``len(pairs_di)``, ``len(pairs_resp)``) although the per-slot means run
only over axes whose score caches loaded -- an axis with a missing cache
is skipped -- so the plots could claim more axes than they averaged.
They now count the loaded axes.

Runs each script end to end at K=0 / L=0 (raw projection, so no whitening
pool or goal/no-goal subspaces are needed) on a two-axis pair list where
one axis has no judge caches, and reads the title back from the PNG's
provenance chunk.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch
from PIL import Image

from assistant_axis import response_subdir
from assistant_axis.provenance import InputSpec
import results_analysis.rho_by_slot_and_K as mod_k
import results_analysis.rho_by_slot_and_L as mod_l

ENTS = [f"ent{i}" for i in range(6)]
N_LAYERS = 26  # the scripts read layer 25


def _vec(path: Path, x: float) -> None:
    t = torch.zeros((1, N_LAYERS, 3))
    t[0, :, 0] = x
    torch.save({"vector": t}, path)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _stub_subtree(data_dir=None, subtree_rel="", dep_key="", **_kw):
    return InputSpec(dep_key=dep_key, path=str(subtree_rel),
                     fingerprint="v1:test", kind="subtree")


def _setup(tmp_path: Path) -> tuple[Path, Path]:
    data = tmp_path / "data"
    (data / "traits" / "vectors").mkdir(parents=True)
    (data / "roles" / "vectors").mkdir(parents=True)
    _vec(data / "traits" / "vectors" / "default.pt", 0.0)
    for name, x in (("pp", 1.0), ("nn", -1.0), ("qq", 2.0), ("rr", -2.0)):
        _vec(data / "traits" / "vectors" / f"{name}.pt", x)
    for i, n in enumerate(ENTS):
        _vec(data / "traits" / "vectors" / f"{n}.pt", float(i))

    exp = tmp_path / "exp"
    pairs = [{"pos": "pp", "neg": "nn"}, {"pos": "qq", "neg": "rr"}]
    _write(exp / "pair_list_di.json", pairs)
    _write(exp / "pair_list_responses.json", pairs)
    # Only pp_vs_nn has judge caches; qq_vs_rr has none.
    axis_dir = exp / "pp_vs_nn"
    for j in ("gpt", "sonnet"):
        for m in ("descriptions", "instructions"):
            _write(axis_dir / j / f"scores_{m}.json",
                   {f"{n}|T": float(i) for i, n in enumerate(ENTS)})
    _write(axis_dir / response_subdir("gpt", "traits") / "scores_responses.json",
           {n: {"mean_score": float(i)} for i, n in enumerate(ENTS)})
    return exp, data


@pytest.mark.parametrize("mod, grid_flag", [(mod_k, "--ks"), (mod_l, "--ls")])
def test_title_counts_loaded_axes(tmp_path, monkeypatch, mod, grid_flag):
    exp, data = _setup(tmp_path)
    monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    monkeypatch.setattr(sys, "argv", [
        "rho_by_slot_and_X.py", "--experiment_dir", str(exp),
        "--data_dir", str(data), grid_flag, "0", "--plot", "out.png",
    ])
    assert mod.main() == 0
    title = Image.open(exp / "out.png").info["Title"]
    assert "desc+inst = 1 axes" in title
    assert "responses = 1 axes" in title
