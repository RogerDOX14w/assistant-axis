"""``optimal_axis_for_judge`` Mode A (``--scores_file``): bare-name keys are
lifted to the entity ids the geometry uses (review of 2026-10-12).

Before the fix a bare-name file never intersected the entity-id keyed
geometry and the fit stopped on "Need >=5 common entities; got 0".
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from results_analysis.optimal_axis_for_judge import _load_scores_from_args


def _data_dir(root: Path) -> Path:
    for et, names in (("traits", ["helpful", "patient"]),
                      ("roles", ["angel", "patient"])):
        vdir = root / et / "vectors"
        vdir.mkdir(parents=True)
        for n in names + ["default"]:
            (vdir / f"{n}.pt").write_bytes(b"")
    return root


def test_bare_names_lifted_and_collisions_dropped(tmp_path, capsys):
    data_dir = _data_dir(tmp_path / "data")
    src = tmp_path / "scores.json"
    src.write_text(json.dumps({
        "helpful": 1.0, "Angel": 0.5, "patient": 0.2, "patient|R": -0.3,
    }))
    args = argparse.Namespace(scores_file=str(src), experiment_dir=None,
                              data_dir=str(data_dir))
    out = _load_scores_from_args(args, inputs=[])
    assert out == {"helpful|T": 1.0, "angel|R": 0.5, "patient|R": -0.3}
    assert "dropped 1 bare name" in capsys.readouterr().err
