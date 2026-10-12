"""pipeline/2_activations.py multi-worker mode reports a dead worker.

Before 2026-10-12 ``run_multi_worker`` returned 0 whatever its worker
processes did, so a worker killed mid-run (an OOM, a CUDA abort) left its
roles unextracted and the pipeline went on to step 4.  The worker processes
are faked here: nothing is spawned and no model is loaded.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_two_activations_workers", REPO_ROOT / "pipeline" / "2_activations.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _run(mod, monkeypatch, tmp_path, exitcodes):
    responses = tmp_path / "responses"
    responses.mkdir()
    for name in ("alpha", "beta"):
        (responses / f"{name}.jsonl").write_text("{}\n")
    launched = []

    class FakeProcess:
        def __init__(self, target, args):
            self.exitcode = exitcodes[len(launched)]
            launched.append(args[2])          # the worker's role files

        def start(self):
            pass

        def join(self):
            pass

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    monkeypatch.setattr(mod.mp, "Process", FakeProcess)
    monkeypatch.setattr(mod.mp, "set_start_method", lambda *a, **k: None)
    args = argparse.Namespace(tensor_parallel_size=1, responses_dir=str(responses),
                              output_dir=str(tmp_path / "out"), roles=None, name_prefix=None)
    rc = mod.run_multi_worker(args)
    return rc, launched


def test_all_workers_exiting_cleanly_returns_0(mod, monkeypatch, tmp_path):
    rc, launched = _run(mod, monkeypatch, tmp_path, [0, 0])
    assert rc == 0 and len(launched) == 2


def test_a_dead_worker_returns_1(mod, monkeypatch, tmp_path, caplog):
    rc, _ = _run(mod, monkeypatch, tmp_path, [0, -9])   # -9: killed (e.g. OOM)
    assert rc == 1
    assert "exited abnormally" in caplog.text
