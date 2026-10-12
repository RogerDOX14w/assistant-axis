"""Steps 2 and 4 return before importing torch when there is nothing to do.

Walk-through P8.3(c) (2026-10-12): the recorded slow starts of the pipeline
steps are the torch import from the pod's network volume, so a rerun that
finds every output in place should return at once.  The scripts run here as
real subprocesses with a fake ``torch`` package first on PYTHONPATH that
raises on import: a run with nothing to do exits 0 without touching it, and
a run with work fails on it (which shows the check comes first).  No model,
no GPU.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def no_torch(tmp_path):
    fake = tmp_path / "fake_site" / "torch"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text("raise ImportError('torch must not be imported here')\n")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(tmp_path / "fake_site")
    return env


def _run(script: str, args: list[str], env) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "pipeline" / script), *args],
                          cwd=REPO / "pipeline", env=env, capture_output=True, text=True,
                          timeout=120)


# ---------------------------------------------------------------------------
# Step 2
# ---------------------------------------------------------------------------

def _step2_dirs(tmp_path, names, done):
    resp, act = tmp_path / "responses", tmp_path / "activations"
    resp.mkdir()
    act.mkdir()
    for n in names:
        (resp / f"{n}.jsonl").write_text("{}\n")
    for n in done:
        (act / f"{n}.pt").write_bytes(b"x")
    return ["--model", "fake/model", "--responses_dir", str(resp), "--output_dir", str(act)]


def test_step2_with_everything_extracted_exits_0_without_torch(tmp_path, no_torch):
    proc = _run("2_activations.py", _step2_dirs(tmp_path, ["a", "b"], ["a", "b"]), no_torch)
    assert proc.returncode == 0, proc.stderr
    assert "Nothing to process" in proc.stderr


def test_step2_filters_apply_to_the_early_check(tmp_path, no_torch):
    """--roles / --name_prefix narrow the work before the check: only r_x is
    asked for, and it is done."""
    args = _step2_dirs(tmp_path, ["r_x", "t_y"], ["r_x"])
    assert _run("2_activations.py", [*args, "--name_prefix", "r_"], no_torch).returncode == 0
    assert _run("2_activations.py", [*args, "--roles", "r_x"], no_torch).returncode == 0


def test_step2_with_work_goes_on_to_the_heavy_imports(tmp_path, no_torch):
    proc = _run("2_activations.py", _step2_dirs(tmp_path, ["a", "b"], ["a"]), no_torch)
    assert proc.returncode != 0
    assert "torch must not be imported here" in proc.stderr


# ---------------------------------------------------------------------------
# Step 4
# ---------------------------------------------------------------------------

def _step4_dirs(tmp_path, acts, vectors, *, placeholders=()):
    a, s, v = tmp_path / "activations", tmp_path / "scores", tmp_path / "vectors"
    for d in (a, s, v):
        d.mkdir()
    for n in acts:
        (a / f"{n}.pt").write_bytes(b"" if n in placeholders else b"x")
    for n in vectors:
        (v / f"{n}.pt").write_bytes(b"x")
    return ["--activations_dir", str(a), "--scores_dir", str(s), "--output_dir", str(v)]


def test_step4_with_every_vector_present_exits_0_without_torch(tmp_path, no_torch):
    args = _step4_dirs(tmp_path, ["a", "b", "ph"], ["a", "b"], placeholders=("ph",))
    proc = _run("4_vectors.py", args, no_torch)
    assert proc.returncode == 0, proc.stderr
    assert "Nothing to do" in proc.stderr


@pytest.mark.parametrize("case", ["missing_vector", "overwrite", "no_activations"])
def test_step4_with_work_or_an_error_goes_on_to_the_heavy_imports(tmp_path, no_torch, case):
    """A missing vector or --overwrite is work; an empty activations
    directory is main's error (exit 1), not "nothing to do"."""
    if case == "missing_vector":
        args = _step4_dirs(tmp_path, ["a", "b"], ["a"])
    elif case == "overwrite":
        args = [*_step4_dirs(tmp_path, ["a"], ["a"]), "--overwrite"]
    else:
        args = _step4_dirs(tmp_path, [], [])
    proc = _run("4_vectors.py", args, no_torch)
    assert proc.returncode != 0
    assert "torch must not be imported here" in proc.stderr
