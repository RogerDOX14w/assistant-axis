"""Regression test for ``results_analysis/rubric_v1_v2_compare.py``.

Review 2026-10-12: the script combined GPT desc/inst caches (v2,
``name|T`` keys) with Sonnet desc/inst caches (v1, bare keys) without
``migrate_v1_static_scores``.  Under the one-side-missing combiner the
two judges then never shared a key, and ``_blend`` against the
entity_id-keyed response scores kept only the GPT half: the "combined"
columns silently used GPT-only desc+inst.

The synthetic axis below puts all the signal in Sonnet: response scores
and GPT desc/inst are constant, Sonnet desc/inst rank the entities in
projection order.  With Sonnet included, combined ρ is 1; with Sonnet
dropped, the combined score is constant and ρ is NaN.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import torch

from assistant_axis.provenance import InputSpec
import results_analysis.rubric_v1_v2_compare as mod

AXIS = ("pp_vs_nn", "pp", "nn")
ENTS = [f"ent{i}" for i in range(6)]


def _vec(path: Path, x: float) -> None:
    # (slot=1, layer=1, hidden=3); projection onto the pp-nn axis is ``x``.
    torch.save({"vector": torch.tensor([[[x, 0.0, 0.0]]])}, path)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _stub_subtree(data_dir, subtree_rel, dep_key, **_kw):
    return InputSpec(dep_key=dep_key, path=str(subtree_rel),
                     fingerprint="v1:test", kind="subtree")


def test_combined_uses_v1_sonnet_desc_inst(tmp_path, monkeypatch):
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
    # GPT desc/inst: v2 (entity_id keys), constant.
    for m in ("descriptions", "instructions"):
        _write(axis_dir / "gpt" / f"scores_{m}.json",
               {f"{n}|T": 0.0 for n in ENTS})
        # Sonnet desc/inst: v1 (bare keys), carries the ranking.
        _write(axis_dir / "sonnet" / f"scores_{m}.json",
               {n: float(i) for i, n in enumerate(ENTS)})
    # Response scores (v2 file name), constant for both judges.
    for tmpl in (mod.GPT_DIR_TEMPLATE, mod.HAIKU_DIR_TEMPLATE):
        _write(axis_dir / tmpl.format(side="traits") / mod.V2_SCORES_FILENAME,
               {n: {"mean_score": 1.0} for n in ENTS})

    monkeypatch.setattr(mod, "DEFAULT_AXES", [AXIS])
    monkeypatch.setattr(mod, "current_data_subtree_input", _stub_subtree)
    out_json = tmp_path / "out.json"
    monkeypatch.setattr(sys, "argv", [
        "rubric_v1_v2_compare.py",
        "--experiment_dir", str(exp), "--data_dir", str(data),
        "--slot", "0", "--layer", "0",
        "--plot", str(tmp_path / "out.png"), "--rhos_json", str(out_json),
    ])
    assert mod.main() == 0

    row = json.loads(out_json.read_text())["result"]["per_axis"][0]
    assert row["combined_v2"]["n"] == len(ENTS)  # the poles carry no scores
    assert math.isclose(row["combined_v2"]["rho"], 1.0, abs_tol=1e-9)
