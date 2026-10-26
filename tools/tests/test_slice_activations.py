"""``tools/slice_activations.py``: one layer of every slot, read either way (2026-10-26)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import torch

from tools.slice_activations import read_file, slice_layer

REPO = Path(__file__).resolve().parents[2]


def _acts():
    torch.manual_seed(0)
    return {"pos_p0_q0": torch.randn(8, 4, 6, dtype=torch.bfloat16),
            "pos_p1_q3": torch.randn(8, 4, 6, dtype=torch.bfloat16),
            "_meta": {"model": "x"}}


def test_slice_keeps_one_layer_of_every_slot_and_drops_metadata():
    a = _acts()
    s = slice_layer(a, 2)
    assert set(s) == {"pos_p0_q0", "pos_p1_q3"}
    assert s["pos_p0_q0"].shape == (8, 6) and s["pos_p0_q0"].dtype == torch.bfloat16
    assert torch.equal(s["pos_p1_q3"], a["pos_p1_q3"][:, 2, :])


def test_both_read_ways_give_the_same_tensors(tmp_path):
    p = tmp_path / "e.pt"
    torch.save(_acts(), p, _use_new_zipfile_serialization=False)   # step 2's legacy format
    a, _ = read_file(p, preread=False)
    b, _ = read_file(p, preread=True)
    assert torch.equal(a["pos_p0_q0"], b["pos_p0_q0"]) and b["_meta"] == {"model": "x"}


def test_cli_writes_slices_and_skips_existing(tmp_path):
    src, out = tmp_path / "acts", tmp_path / "slices"
    src.mkdir()
    torch.save(_acts(), src / "patient.pt", _use_new_zipfile_serialization=False)
    cmd = [sys.executable, str(REPO / "tools/slice_activations.py"), "--activations-dir", str(src),
           "--out-dir", str(out), "--layer", "1", "--preread"]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    d = torch.load(out / "patient.pt", weights_only=False)
    assert d["layer"] == 1 and set(d["acts"]) == {"pos_p0_q0", "pos_p1_q3"}
    r2 = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    assert "exists, skipped" in r2.stdout
