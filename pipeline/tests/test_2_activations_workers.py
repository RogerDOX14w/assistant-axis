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


def test_a_worker_reporting_failed_roles_returns_1(mod, monkeypatch, tmp_path):
    # Exit status 1 is what process_roles_on_worker now gives when a role
    # raised or its model failed to load (below).
    rc, _ = _run(mod, monkeypatch, tmp_path, [1, 0])
    assert rc == 1


# ---------------------------------------------------------------------------
# The worker's own exit status (review of 2026-10-12).  Until then a worker
# whose model failed to load (a CUDA out-of-memory error beside an orphaned
# process, the case run_pipeline.sh's GPU pre-flight guards against) or whose
# roles raised logged the error and exited 0, so the check above never fired.
# The worker runs in-process here, on fakes.
# ---------------------------------------------------------------------------

class _FakePM:
    """What load_worker_model reads: the layers, the family row and a
    tokenizer whose chat template the header layout is derived from (since
    the multi-model plan, 2026-10-13)."""

    model_name = "Qwen/Qwen3-32B"

    def __init__(self):
        from assistant_axis.model_families import FAMILIES
        from assistant_axis.tests.internals_fakes import make_qwen3_like_tokenizer
        self.family = FAMILIES["qwen3"]
        self.tokenizer = make_qwen3_like_tokenizer()

    def get_layers(self):
        return [object()] * 3


def _fake_probing_model(_name, **kwargs):
    return _FakePM()


def _worker_args(tmp_path):
    return argparse.Namespace(model="Qwen/Qwen3-32B", output_dir=str(tmp_path), layers="all",
                              no_headers=False, batch_size=2, max_length=2048, verify_spans=0)


def _role_files(tmp_path, names=("alpha", "beta")):
    return [tmp_path / f"{n}.jsonl" for n in names]


def test_worker_exits_1_when_the_model_fails_to_load(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")    # the worker overwrites it

    def boom(_name, **kwargs):
        raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(mod, "ProbingModel", boom)
    with pytest.raises(SystemExit) as e:
        mod.process_roles_on_worker(0, [0], _role_files(tmp_path), _worker_args(tmp_path))
    assert e.value.code == 1


def test_worker_exits_1_when_a_role_raises_and_still_does_the_rest(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    monkeypatch.setattr(mod, "ProbingModel", _fake_probing_model)
    done = []

    def fake_process_role(pm, role_file, *a, **k):
        done.append(role_file.stem)
        if role_file.stem == "alpha":
            raise mod.NoActivationsError("alpha: none of 2 conversations ...")
        return True, 0

    monkeypatch.setattr(mod, "process_role", fake_process_role)
    with pytest.raises(SystemExit) as e:
        mod.process_roles_on_worker(0, [0], _role_files(tmp_path), _worker_args(tmp_path))
    assert e.value.code == 1
    assert done == ["alpha", "beta"]


def test_worker_returns_normally_when_every_role_is_saved_or_empty(mod, monkeypatch, tmp_path):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    monkeypatch.setattr(mod, "ProbingModel", _fake_probing_model)
    # "beta" has no responses: a warning, not a failure.
    monkeypatch.setattr(mod, "process_role",
                        lambda pm, role_file, *a, **k: (role_file.stem == "alpha", 0))
    assert mod.process_roles_on_worker(
        0, [0], _role_files(tmp_path), _worker_args(tmp_path)) is None


def test_single_worker_mode_exits_1_after_a_role_with_no_activations(
        mod, monkeypatch, tmp_path):
    import logging
    import sys as _sys

    responses = tmp_path / "responses"
    responses.mkdir()
    for name in ("alpha", "beta"):
        (responses / f"{name}.jsonl").write_text("{}\n")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")    # no GPUs: single-worker mode
    monkeypatch.setattr(mod, "ProbingModel", _fake_probing_model)
    done = []

    def fake_process_role(pm, role_file, *a, **k):
        done.append(role_file.stem)
        if role_file.stem == "alpha":
            raise mod.NoActivationsError("alpha: none of 1 conversations ...")
        return True, 0

    monkeypatch.setattr(mod, "process_role", fake_process_role)
    # The preflight reads config.json and the tokenizer (never on the Mac):
    # faked with the qwen3 row and the Qwen3-like tokenizer.
    from assistant_axis.model_families import FAMILIES
    fake = _FakePM()
    monkeypatch.setattr(mod, "preflight_model", lambda name, **kw: mod.Preflight(
        family=FAMILIES["qwen3"], n_layers=3, tokenizer=fake.tokenizer,
        layout=mod.derive_chat_layout(fake.tokenizer, FAMILIES["qwen3"])))
    monkeypatch.setattr(_sys, "argv", [
        "2_activations.py", "--model", "Qwen/Qwen3-32B",
        "--responses_dir", str(responses), "--output_dir", str(tmp_path / "out")])
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        with pytest.raises(SystemExit) as e:
            mod.main()
    finally:
        for h in root.handlers[:]:        # main() adds a file handler
            if h not in before:
                root.removeHandler(h)
                h.close()
    assert e.value.code == 1
    assert done == ["alpha", "beta"]
