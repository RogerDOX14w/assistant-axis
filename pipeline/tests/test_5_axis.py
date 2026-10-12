"""Tests for pipeline/5_axis.py (step 5: the axis from the vectors).

Pins what the axis is made of: mean of the default vector(s) minus the
nanmean of every other vector in the directory, per slot and layer, with
the vectors' metadata carried over; and that "default" is an exact name.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import torch

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "5_axis.py"
META = {"header_tokens": ["a", "b"], "header_ids": [1, 2], "model_name": "fake/model"}


@pytest.fixture(scope="module")
def step5():
    spec = importlib.util.spec_from_file_location("_pipeline_5_axis_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def _isolated_tmpdir(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    monkeypatch.setenv("TMPDIR", str(stage))


def _vec(path: Path, value, vtype="pos_3", meta=META, role=None):
    t = value if isinstance(value, torch.Tensor) else torch.full((3, 2, 4), float(value))
    data = {"vector": t, "type": vtype, "role": role or path.stem}
    if meta is not None:
        data["metadata"] = dict(meta)
    torch.save(data, path)


def _run(step5, monkeypatch, vec_dir: Path, out: Path):
    monkeypatch.setattr(sys, "argv", ["5_axis.py", "--vectors_dir", str(vec_dir),
                                      "--output", str(out)])
    step5.main()
    return torch.load(out, map_location="cpu", weights_only=False)


def test_axis_is_default_minus_nanmean_of_the_rest(step5, monkeypatch, tmp_path):
    vec_dir = tmp_path / "vectors"
    vec_dir.mkdir()
    _vec(vec_dir / "default.pt", 10.0, vtype="mean")
    _vec(vec_dir / "pirate.pt", 2.0)
    with_nan = torch.full((3, 2, 4), 4.0)
    with_nan[2] = float("nan")              # a header slot never found
    _vec(vec_dir / "chef.pt", with_nan)
    # a name containing "default" is an ordinary entity (role side)
    _vec(vec_dir / "defaulter.pt", 6.0)
    saved = _run(step5, monkeypatch, vec_dir, tmp_path / "axis.pt")
    axis = saved["axis"]
    assert axis.shape == (3, 2, 4)
    assert torch.allclose(axis[0], torch.full((2, 4), 10.0 - (2 + 4 + 6) / 3))
    assert torch.allclose(axis[2], torch.full((2, 4), 10.0 - (2 + 6) / 2))
    assert saved["metadata"]["header_ids"] == [1, 2]
    # what the axis was made of
    inputs = saved["inputs"]
    assert inputs["default"] == ["default"]
    assert sorted(inputs["entities"]) == ["chef", "defaulter", "pirate"]
    assert inputs["n_default"] == 1 and inputs["n_entities"] == 3


def test_mismatched_header_ids_stop_the_run(step5, monkeypatch, tmp_path):
    vec_dir = tmp_path / "vectors"
    vec_dir.mkdir()
    _vec(vec_dir / "default.pt", 1.0, vtype="mean")
    _vec(vec_dir / "pirate.pt", 2.0, meta={**META, "header_ids": [9, 9]})
    with pytest.raises(SystemExit) as e:
        _run(step5, monkeypatch, vec_dir, tmp_path / "axis.pt")
    assert e.value.code == 1


def test_mixed_slot_counts_stop_the_run(step5, monkeypatch, tmp_path):
    """A 4-slot vector beside 8-slot ones (vectors_4slot mixed into vectors)."""
    vec_dir = tmp_path / "vectors"
    vec_dir.mkdir()
    _vec(vec_dir / "default.pt", 1.0, vtype="mean")
    _vec(vec_dir / "pirate.pt", torch.zeros(2, 2, 4))
    with pytest.raises(SystemExit) as e:
        _run(step5, monkeypatch, vec_dir, tmp_path / "axis.pt")
    assert e.value.code == 1


def test_no_default_vector_stops_the_run(step5, monkeypatch, tmp_path):
    vec_dir = tmp_path / "vectors"
    vec_dir.mkdir()
    _vec(vec_dir / "pirate.pt", 2.0)
    with pytest.raises(SystemExit) as e:
        _run(step5, monkeypatch, vec_dir, tmp_path / "axis.pt")
    assert e.value.code == 1
