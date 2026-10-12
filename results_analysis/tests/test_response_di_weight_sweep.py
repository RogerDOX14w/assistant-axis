"""Regression test for ``results_analysis/response_di_weight_sweep.py``.

Review 2026-10-12: only the Sonnet desc/inst caches were passed through
``migrate_v1_static_scores``.  Three response axes
(accessible_vs_esoteric, benign_vs_malicious, introverted_vs_extroverted)
still have v1 (bare-name) GPT caches, so their bare GPT keys never met
the entity_id response keys and desc+inst came out Sonnet-only.

The synthetic axis puts all desc+inst signal in a v1 GPT cache (Sonnet
constant): with GPT included, the pure-desc+inst end of the sweep
(w = 0) has ρ = 1; with GPT dropped it is NaN.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest
import torch

from assistant_axis.provenance import InputSpec

try:  # imports gpt_anthropic_response_weight_sweep, which reads a pair list
    import results_analysis.response_di_weight_sweep as mod
except FileNotFoundError as e:  # pragma: no cover -- pair list absent
    pytest.skip(f"pair list missing: {e}", allow_module_level=True)

AXIS = ("pp_vs_nn", "pp", "nn")
ENTS = [f"ent{i}" for i in range(6)]


def _vec(path: Path, x: float) -> None:
    torch.save({"vector": torch.tensor([[[x, 0.0, 0.0]]])}, path)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _stub_subtree(data_dir=None, subtree_rel="", dep_key="", **_kw):
    return InputSpec(dep_key=dep_key, path=str(subtree_rel),
                     fingerprint="v1:test", kind="subtree")


def test_v1_gpt_desc_inst_is_migrated(tmp_path, monkeypatch):
    data = tmp_path / "data"
    (data / "traits" / "vectors").mkdir(parents=True)
    (data / "roles" / "vectors").mkdir(parents=True)
    _vec(data / "traits" / "vectors" / "default.pt", 0.0)
    _vec(data / "traits" / "vectors" / "pp.pt", 1.0)
    _vec(data / "traits" / "vectors" / "nn.pt", -1.0)
    for i, n in enumerate(ENTS):
        _vec(data / "traits" / "vectors" / f"{n}.pt", float(i))

    exp = tmp_path / "exp"
    axis_dir = exp / AXIS[0]
    for m in ("descriptions", "instructions"):
        # Both judges v1 (bare keys); GPT carries the ranking.
        _write(axis_dir / "gpt" / f"scores_{m}.json",
               {n: float(i) for i, n in enumerate(ENTS)})
        _write(axis_dir / "sonnet" / f"scores_{m}.json",
               {n: 0.0 for n in ENTS})

    # Response scores: entity_id keyed, as the real loader returns them.
    def fake_response_scores(experiment_dir, axis, _tmpl, *, judge_label,
                             inputs):
        return {f"{n}|T": float(i) for i, n in enumerate(ENTS)}

    monkeypatch.setattr(mod, "DEFAULT_AXES", [AXIS])
    monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    monkeypatch.setattr(mod, "_load_response_scores", fake_response_scores)
    out_json = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", [
        "response_di_weight_sweep.py",
        "--experiment_dir", str(exp), "--data_dir", str(data),
        "--slot", "0", "--layer", "0", "--whitening", "raw",
        "--plot", str(tmp_path / "out.png"), "--rhos_json", str(out_json),
    ])
    assert mod.main() == 0

    row = json.loads(out_json.read_text())["result"]["per_axis"][0]
    assert row["n"] == len(ENTS)
    assert math.isclose(row["rho_by_w"][0], 1.0, abs_tol=1e-9)  # w=0: DI only


def test_pair_list_selects_axes_and_names_outputs(tmp_path, monkeypatch):
    """--pair_list (review 2026-10-12): the axes come from the given list
    (DEFAULT_AXES, the *current* responses list, could not reproduce the
    22-axis _v1 record), a role-pair entry takes its direction from
    roles/vectors, and a non-'responses' cohort token goes into the
    default output names."""
    data = tmp_path / "data"
    (data / "traits" / "vectors").mkdir(parents=True)
    (data / "roles" / "vectors").mkdir(parents=True)
    _vec(data / "traits" / "vectors" / "default.pt", 0.0)
    _vec(data / "traits" / "vectors" / "pp.pt", 1.0)
    _vec(data / "traits" / "vectors" / "nn.pt", -1.0)
    # Role poles exist only under roles/: a traits/ lookup would fail.
    _vec(data / "roles" / "vectors" / "rp.pt", -1.0)
    _vec(data / "roles" / "vectors" / "rn.pt", 1.0)
    for i, n in enumerate(ENTS):
        _vec(data / "traits" / "vectors" / f"{n}.pt", float(i))

    exp = tmp_path / "exp"
    (exp).mkdir()
    (exp / "pair_list_responses_v1.json").write_text(json.dumps([
        {"pos": "pp", "neg": "nn"},
        {"pos": "rp", "neg": "rn", "pair_type": "roles"},
    ]))
    for axis in ("pp_vs_nn", "rp_vs_rn"):
        for j in ("gpt", "sonnet"):
            for m in ("descriptions", "instructions"):
                _write(exp / axis / j / f"scores_{m}.json",
                       {f"{n}|T": float(i) for i, n in enumerate(ENTS)})

    def fake_response_scores(experiment_dir, axis, _tmpl, *, judge_label,
                             inputs):
        return {f"{n}|T": float(i) for i, n in enumerate(ENTS)}

    monkeypatch.setattr(mod, "DEFAULT_AXES", [("never_vs_used", "a", "b")])
    monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    monkeypatch.setattr(mod, "_load_response_scores", fake_response_scores)
    monkeypatch.setattr(sys, "argv", [
        "response_di_weight_sweep.py",
        "--experiment_dir", str(exp), "--data_dir", str(data),
        "--slot", "0", "--layer", "0", "--whitening", "raw",
        "--pair_list", "pair_list_responses_v1.json",
    ])
    assert mod.main() == 0

    out = exp / "response_di_weight_sweep_slot0_responses_v1.json"
    result = json.loads(out.read_text())["result"]
    assert result["n_axes"] == 2
    assert result["pair_list"] == "pair_list_responses_v1.json"
    by_axis = {r["axis_name"]: r for r in result["per_axis"]}
    assert set(by_axis) == {"pp_vs_nn", "rp_vs_rn"}
    # The role axis points the other way (rp at -1, rn at +1).
    assert math.isclose(by_axis["rp_vs_rn"]["rho_by_w"][0], -1.0,
                        abs_tol=1e-9)
