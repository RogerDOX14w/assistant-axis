"""pipeline/1_generate.py: work-item selection and the multi-worker exit status.

Two fixes of 2026-10-12 are pinned here:

* ``--roles`` keeps only the named work items in every mode.  Before, it was
  applied only with ``--roles_only`` and in christina mode and silently
  ignored otherwise, so ``--roles r_activist__abstract`` generated the whole
  combination grid and every standalone trait.
* A worker that cannot load the model exits non-zero, and ``run_multi_worker``
  returns 1 when any worker exited abnormally (it returned 0 whatever its
  workers did, so run_pipeline.sh went on to step 2 with part of the
  responses missing).

Nothing is spawned and no model is loaded: the worker processes and the
generator are fakes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_one_generate", REPO_ROOT / "pipeline" / "1_generate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _instruction_file(path: Path, text: str) -> None:
    path.write_text(json.dumps({"description": text,
                                "instruction": [{"pos": f"{text} {i}"} for i in range(5)]}))


@pytest.fixture
def data(tmp_path):
    """Roles a, b, patient, default; traits x, y, patient (a name of both kinds);
    goal role a, non-goal role b, goal trait x, non-goal trait y."""
    roles = tmp_path / "roles"
    traits = tmp_path / "traits"
    roles.mkdir()
    traits.mkdir()
    for stem in ("a", "b", "patient", "default"):
        _instruction_file(roles / f"{stem}.json", f"role {stem}")
    for stem in ("x", "y", "patient"):
        _instruction_file(traits / f"{stem}.json", f"trait {stem}")
    goal = tmp_path / "goal.json"
    goal.write_text(json.dumps({"roles": {"goal": ["a"], "non_goal": ["b"]},
                                "traits": {"goal": ["x"], "non_goal": ["y"]}}))
    return tmp_path


def _args(data, **over):
    a = dict(mode="roger", roles_dir=str(data / "roles"), traits_dir=str(data / "traits"),
             goal_file=str(data / "goal.json"), goal_count=1, non_goal_count=1,
             roles_only=False, traits_only=False, no_traits=False,
             combos_only_r=False, combos_only_t=False, roles=None)
    a.update(over)
    return argparse.Namespace(**a)


def _names(items):
    return sorted(i["output_name"] for i in items)


# ---------------------------------------------------------------------------
# Work items
# ---------------------------------------------------------------------------

def test_roger_default_mode_items(mod, data):
    items = mod.collect_work_items(_args(data))
    assert _names(items) == ["default", "patient", "r_a__y", "t_b__x", "x", "y"]
    combo = next(i for i in items if i["output_name"] == "r_a__y")
    assert combo["goal_source"] == "role"
    assert combo["role_file"].endswith("roles/a.json") and combo["trait_file"].endswith("traits/y.json")


def test_roles_filter_applies_to_combinations(mod, data):
    """The regression: --roles used to be ignored outside --roles_only."""
    items = mod.collect_work_items(_args(data, roles=["r_a__y"]))
    assert _names(items) == ["r_a__y"]


def test_roles_filter_applies_to_standalone_traits(mod, data):
    items = mod.collect_work_items(_args(data, traits_only=True, roles=["x"]))
    assert _names(items) == ["x"]


def test_roles_filter_warns_on_a_name_with_no_work_item(mod, data, caplog):
    with caplog.at_level(logging.WARNING):
        items = mod.collect_work_items(_args(data, roles=["r_a__y", "r_a__nope"]))
    assert _names(items) == ["r_a__y"]
    assert "r_a__nope" in caplog.text


def test_roles_only_and_christina_filters_unchanged(mod, data):
    """run_pipeline.sh's step 0 relies on --roles_only --roles default."""
    assert _names(mod.collect_work_items(_args(data, roles_only=True, roles=["default"]))) == ["default"]
    assert _names(mod.collect_work_items(_args(data, roles_only=True))) == ["a", "b", "default", "patient"]
    christina = _args(data, mode="christina", roles=["a", "b"])
    assert _names(mod.collect_work_items(christina)) == ["a", "b"]


def test_a_name_of_both_kinds_reads_the_file_of_its_kind(mod, data):
    role = next(i for i in mod.collect_work_items(_args(data, roles_only=True))
                if i["output_name"] == "patient")
    trait = next(i for i in mod.collect_work_items(_args(data, traits_only=True))
                 if i["output_name"] == "patient")
    assert Path(role["file_path"]).parent.name == "roles"
    assert Path(trait["file_path"]).parent.name == "traits"


# ---------------------------------------------------------------------------
# Workers and exit status
# ---------------------------------------------------------------------------

def _run_multi(mod, monkeypatch, exitcodes, n_items=2):
    launched = []

    class FakeProcess:
        def __init__(self, target, args):
            self.exitcode = exitcodes[len(launched)]
            launched.append(args[2])          # the worker's items

        def start(self):
            pass

        def join(self):
            pass

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    monkeypatch.setattr(mod.mp, "Process", FakeProcess)
    monkeypatch.setattr(mod.mp, "set_start_method", lambda *a, **k: None)
    items = [{"output_name": f"e{i}", "type": "standalone", "file_path": "-"} for i in range(n_items)]
    rc = mod.run_multi_worker(items, argparse.Namespace(tensor_parallel_size=1))
    return rc, launched


def test_all_workers_exiting_cleanly_returns_0(mod, monkeypatch):
    rc, launched = _run_multi(mod, monkeypatch, [0, 0])
    assert rc == 0 and [len(c) for c in launched] == [1, 1]


def test_a_failed_or_dead_worker_returns_1(mod, monkeypatch, caplog):
    for codes in ([0, 1], [-9, 0]):          # 1: model failed to load; -9: killed
        rc, _ = _run_multi(mod, monkeypatch, codes)
        assert rc == 1
    assert "exited abnormally" in caplog.text


def _worker_args(tmp_path):
    return argparse.Namespace(
        model="fake/model", roles_dir=str(tmp_path), output_dir=str(tmp_path / "out"),
        questions_file=str(tmp_path / "q.jsonl"), max_model_len=2048, tensor_parallel_size=1,
        gpu_memory_utilization=0.9, question_count=3, reduce_questions=1,
        temperature=0.7, max_tokens=8, top_p=0.9)


def test_a_worker_that_cannot_load_the_model_exits_1(mod, monkeypatch, tmp_path):
    class CannotLoad:
        def __init__(self, **kw):
            raise RuntimeError("CUDA out of memory")

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")   # the worker sets it; restored after
    monkeypatch.setattr(mod, "RoleResponseGenerator", CannotLoad)
    item = {"output_name": "a", "type": "standalone", "file_path": str(tmp_path / "a.json")}
    with pytest.raises(SystemExit) as exc:
        mod.process_items_on_worker(0, [0], [item], _worker_args(tmp_path))
    assert exc.value.code == 1


def test_a_failing_item_does_not_stop_the_worker(mod, monkeypatch, tmp_path):
    """Per-item failures are logged and the worker goes on to its other items
    (whether they should also make the step exit non-zero is an open
    question for Roger; the worker returns normally for now)."""
    saved = []

    class FakeGen:
        def __init__(self, **kw):
            self.generator = argparse.Namespace(load=lambda: None)

        def load_role(self, path):
            if Path(path).stem == "bad":
                raise OSError("Input/output error")
            return {"instruction": [{"pos": "p"}]}

        def generate_role_responses(self, name, data):
            return [{"label": "pos", "prompt_index": 0, "question_index": 0}]

        def save_responses(self, name, responses):
            saved.append(name)

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", FakeGen)
    items = [{"output_name": n, "type": "standalone", "file_path": str(tmp_path / f"{n}.json")}
             for n in ("bad", "good")]
    mod.process_items_on_worker(0, [0], items, _worker_args(tmp_path))
    assert saved == ["good"]


def test_main_exits_1_when_a_worker_failed(mod, monkeypatch, data):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    monkeypatch.setattr(mod, "run_multi_worker", lambda items, args: 1)
    monkeypatch.setattr(sys, "argv", [
        "1_generate.py", "--model", "fake/model", "--tensor_parallel_size", "1",
        "--roles_dir", str(data / "roles"), "--traits_dir", str(data / "traits"),
        "--goal_file", str(data / "goal.json"), "--goal_count", "1", "--non_goal_count", "1",
        "--output_dir", str(data / "out")])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
