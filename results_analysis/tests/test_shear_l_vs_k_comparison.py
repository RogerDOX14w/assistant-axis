"""Regression tests for ``results_analysis/shear_l_vs_k_comparison.py``.

Review 2026-10-12: the script stripped the ``|R`` / ``|T`` suffix from
the GPT desc/inst scores and from the projections (``_strip_kind``) so
they would match bare-name Sonnet caches.  That (a) clobbered the
collision names -- a trait's score could be paired with the role's
projection -- and (b) with v2 (entity_id) Sonnet caches, which 26 of the
61 di axes now have, left desc+inst GPT-only under the one-side-missing
combiner.  The fix keys everything by entity_id and lifts v1 caches with
``migrate_v1_static_scores``, as ``whitening_k_sweep`` does.

Also covered: ``_load_k_sweep_records`` on a raw-list (legacy) sweep
file, which its comment claimed to tolerate but which raised
``AttributeError`` (a list has no ``.get``).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

from assistant_axis.provenance import InputSpec
import results_analysis.shear_l_vs_k_comparison as mod

# entity -> projection == score (so a correct pairing gives rho = 1).
VALUES = {f"ent{i}|T": float(i) for i in range(6)}
VALUES["patient|T"] = 10.0     # collision name: trait end ...
VALUES["patient|R"] = -10.0    # ... and role end differ in sign


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _stub_subtree(data_dir=None, subtree_rel="", dep_key="", **_kw):
    return InputSpec(dep_key=dep_key, path=str(subtree_rel),
                     fingerprint="v1:test", kind="subtree")


def test_collision_names_keep_their_kind(tmp_path, monkeypatch):
    exp = tmp_path / "exp"
    _write(exp / "pair_list_di.json", [{"pos": "pp", "neg": "nn"}])
    _write(exp / "pair_list_responses.json", [])
    # Raw-list legacy shape; one desc+inst row, which the pair-list check
    # of walk-through A2 requires for every listed axis.
    _write(exp / "whitening_k_sweep_di_slot6.json",
           [{"pos": "pp", "neg": "nn", "source": "desc_inst", "K": 1, "rho": 0.5}])
    # Pole vector files: load_pool / axis_direction are stubbed below, but
    # the A2 check looks for the files.
    for n in ("pp", "nn"):
        _write(tmp_path / "data" / "traits" / "vectors" / f"{n}.pt", {})
    axis_dir = exp / "pp_vs_nn"
    # Trait written last so a bare-name clobber keeps the trait's score.
    gpt = dict(sorted(VALUES.items(), key=lambda kv: kv[0].endswith("|T")))
    for j in ("gpt", "sonnet"):
        for m in ("descriptions", "instructions"):
            _write(axis_dir / j / f"scores_{m}.json", gpt)

    # Traits first, then roles: a bare-name clobber keeps the role's
    # projection.
    entity_vecs = {
        k: torch.tensor([v, 0.0, 0.0])
        for k, v in sorted(VALUES.items(), key=lambda kv: kv[0].endswith("|R"))
    }
    kinds = {"patient": {"traits", "roles"}}
    kinds.update({f"ent{i}": {"traits"} for i in range(6)})

    monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    monkeypatch.setattr(mod, "build_goal_nogoal_subspaces",
                        lambda *a, **k: (np.zeros((3, 1)), np.zeros((3, 1))))
    monkeypatch.setattr(mod, "load_pool",
                        lambda *a, **k: (entity_vecs, None, None, kinds))
    monkeypatch.setattr(mod, "axis_direction",
                        lambda *a, **k: torch.tensor([1.0, 0.0, 0.0]))
    monkeypatch.setattr(mod, "L_VALUES", (0,))

    assert mod.main([
        "--experiment_dir", str(exp), "--data_dir", str(tmp_path / "data"),
        "--pairs", "pair_list_di.json",
        "--pairs_primary", "pair_list_responses.json",
        "--out", "out.json",
    ]) == 0

    records = json.loads((exp / "out.json").read_text())["result"]
    di = [r for r in records if r["source"] == "desc_inst" and r["L"] == 0]
    assert len(di) == 1
    assert math.isclose(di[0]["rho"], 1.0, abs_tol=1e-9)


def test_load_k_sweep_records_accepts_raw_list(tmp_path):
    p = tmp_path / "sweep.json"
    p.write_text(json.dumps(
        [{"pos": "a", "neg": "b", "source": "desc_inst", "K": 1, "rho": 0.5}]))
    assert mod._load_k_sweep_records(p) == {("a", "b", "desc_inst", 1): 0.5}
    p.write_text(json.dumps({"result": [
        {"pos": "a", "neg": "b", "source": "responses", "K": 0, "rho": 0.25}],
        "_provenance": {}}))
    assert mod._load_k_sweep_records(p) == {("a", "b", "responses", 0): 0.25}
