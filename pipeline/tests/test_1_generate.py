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
generator are fakes.  Since the multi-model plan (2026-10-13) step 1 reads the
model's config.json and tokenizer before vLLM (``preflight_generation``); that
is faked for every test here with the qwen3 row and the Qwen3-like tokenizer
(``_fake_preflight``), since the Mac has no Hugging Face cache to read.
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


@pytest.fixture(autouse=True)
def _fake_preflight(mod, monkeypatch):
    """The qwen3 row, the Qwen3-like fake tokenizer and its derived layout,
    whatever --model says (no config.json is read)."""
    from assistant_axis.internals.chat_layout import derive_chat_layout
    from assistant_axis.model_families import FAMILIES
    from assistant_axis.tests.internals_fakes import make_qwen3_like_tokenizer
    tok = make_qwen3_like_tokenizer()
    pre = mod.GenerationPreflight(family=FAMILIES["qwen3"], tokenizer=tok,
                                  layout=derive_chat_layout(tok, FAMILIES["qwen3"]))
    calls = []

    def fake(model_name):
        calls.append(model_name)
        return pre

    monkeypatch.setattr(mod, "preflight_generation", fake)
    return calls


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
    (tmp_path / "questions.jsonl").write_text(
        "".join(json.dumps({"id": i, "question": f"q{i}"}) + "\n" for i in range(9)))
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


def _fake_generator(saved, bad=("bad",)):
    class FakeGen:
        def __init__(self, **kw):
            self.generator = argparse.Namespace(load=lambda: None)

        def load_role(self, path):
            if Path(path).stem in bad:
                raise OSError("Input/output error")
            return {"instruction": [{"pos": "p"}]}

        def generate_role_responses(self, name, data):
            return [{"label": "pos", "prompt_index": 0, "question_index": 0}]

        def save_responses(self, name, responses):
            saved.append(name)

    return FakeGen


def test_a_failing_item_does_not_stop_the_worker_but_makes_it_exit_1(mod, monkeypatch, tmp_path):
    """Per-item failures are logged and the worker goes on to its other items;
    since P8.1 (2026-10-12) it then exits 1, so the step does too.  (Changed
    expectation: until that decision the worker returned normally.)"""
    saved = []
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", _fake_generator(saved))
    items = [{"output_name": n, "type": "standalone", "file_path": str(tmp_path / f"{n}.json")}
             for n in ("bad", "good")]
    with pytest.raises(SystemExit) as exc:
        mod.process_items_on_worker(0, [0], items, _worker_args(tmp_path))
    assert exc.value.code == 1
    assert saved == ["good"]


def test_a_worker_whose_items_all_succeed_returns_normally(mod, monkeypatch, tmp_path):
    saved = []
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", _fake_generator(saved))
    items = [{"output_name": n, "type": "standalone", "file_path": str(tmp_path / f"{n}.json")}
             for n in ("a", "b")]
    mod.process_items_on_worker(0, [0], items, _worker_args(tmp_path))
    assert saved == ["a", "b"]


def test_run_items_stops_after_k_consecutive_failures(mod, tmp_path, caplog):
    """An engine that died fails every later item: stop after K in a row
    instead of failing the rest of the queue one by one."""
    saved = []
    gen = _fake_generator(saved, bad={"b1", "b2", "b3", "b4", "b5"})()
    names = ["ok1", "b1", "ok2", "b2", "b3", "b4", "b5", "never"]
    items = [{"output_name": n, "type": "standalone", "file_path": str(tmp_path / f"{n}.json")}
             for n in names]
    with caplog.at_level(logging.ERROR):
        result = mod.run_items(gen, items, logging.getLogger("t"), max_consecutive_failures=3)
    assert result["aborted"] is True
    assert result["failed_names"] == ["b1", "b2", "b3", "b4"]
    assert saved == ["ok1", "ok2"]            # "never" and "b5" were not tried
    assert "in a row" in caplog.text
    # An isolated failure is counted but does not stop the run.
    saved.clear()
    result = mod.run_items(gen, items[:3], logging.getLogger("t"), max_consecutive_failures=3)
    assert result == {"completed": 2, "failed": 1, "failed_names": ["b1"], "aborted": False}


def test_default_consecutive_failure_limit():
    """K is a constant of the script (P8.1: "say 20")."""
    spec = importlib.util.spec_from_file_location(
        "_pipeline_one_generate_k", REPO_ROOT / "pipeline" / "1_generate.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.MAX_CONSECUTIVE_FAILURES == 20


def test_main_single_worker_exits_1_when_an_item_failed(mod, monkeypatch, data):
    saved = []
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", _fake_generator(saved, bad={"x"}))
    monkeypatch.setattr(sys, "argv", [
        "1_generate.py", "--model", "fake/model", "--traits_only",
        "--roles_dir", str(data / "roles"), "--traits_dir", str(data / "traits"),
        "--output_dir", str(data / "out"), "--questions_file", str(data / "questions.jsonl")])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1
    assert sorted(saved) == ["patient", "y"]


# ---------------------------------------------------------------------------
# Goal lists: a missing name fails fast; the grid size is reported
# ---------------------------------------------------------------------------

def test_a_goal_list_name_with_no_file_fails_fast(mod, data):
    (data / "traits" / "y.json").unlink()
    (data / "traits" / "y2.json").write_text(json.dumps(
        {"description": "d", "instruction": [{"pos": "p"}], "renamed_from": {"stem": "y"}}))
    with pytest.raises(mod.GoalListError) as exc:
        mod.collect_work_items(_args(data))
    msg = str(exc.value)
    assert "trait 'y'" in msg and "renamed to y2" in msg


def test_a_missing_name_on_an_unused_half_is_not_an_error(mod, data):
    """--combos_only_t uses non-goal roles and goal traits only."""
    (data / "traits" / "y.json").unlink()          # y is a non-goal trait (the r_ half)
    items = mod.collect_work_items(_args(data, combos_only_t=True, no_traits=True))
    assert _names(items) == ["default", "t_b__x"]


def test_main_exits_1_on_a_missing_goal_list_name(mod, monkeypatch, data):
    (data / "roles" / "b.json").unlink()
    monkeypatch.setattr(sys, "argv", [
        "1_generate.py", "--model", "fake/model",
        "--roles_dir", str(data / "roles"), "--traits_dir", str(data / "traits"),
        "--goal_file", str(data / "goal.json"), "--goal_count", "1", "--non_goal_count", "1",
        "--output_dir", str(data / "out"), "--questions_file", str(data / "questions.jsonl")])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


def test_grid_size_is_reported_against_the_nominal(mod, data, caplog):
    with caplog.at_level(logging.INFO):
        mod.collect_work_items(_args(data))
    assert "Combination grid: 1 r_ + 1 t_ = 2 (goal_count x non_goal_count x 2 = 1 x 1 x 2 = 2)" in caplog.text
    # A count larger than one of the lists it applies to (allowed while the
    # other is long enough) shrinks the grid: a WARNING with the list sizes.
    goal = json.loads((data / "goal.json").read_text())
    goal["roles"]["goal"] = ["a", "patient"]
    (data / "goal.json").write_text(json.dumps(goal))
    caplog.clear()
    with caplog.at_level(logging.INFO):
        mod.collect_work_items(_args(data, goal_count=2))
    warn = [r for r in caplog.records if r.levelno == logging.WARNING and "Combination grid" in r.message]
    assert warn and "= 2 x 1 x 2 = 4" in warn[0].message and "traits.goal 1" in warn[0].message


def test_main_exits_1_when_a_worker_failed(mod, monkeypatch, data):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0,1")
    monkeypatch.setattr(mod, "run_multi_worker", lambda items, args: 1)
    monkeypatch.setattr(sys, "argv", [
        "1_generate.py", "--model", "fake/model", "--tensor_parallel_size", "1",
        "--roles_dir", str(data / "roles"), "--traits_dir", str(data / "traits"),
        "--goal_file", str(data / "goal.json"), "--goal_count", "1", "--non_goal_count", "1",
        "--output_dir", str(data / "out"), "--questions_file", str(data / "questions.jsonl")])
    with pytest.raises(SystemExit) as exc:
        mod.main()
    assert exc.value.code == 1


# ---------------------------------------------------------------------------
# generation_config.json (walk-through P2, 2026-10-12)
# ---------------------------------------------------------------------------

def _main_args(data, *extra):
    return ["1_generate.py", "--model", "Qwen/fake", "--traits_only",
            "--roles_dir", str(data / "roles"), "--traits_dir", str(data / "traits"),
            "--output_dir", str(data / "out"), "--questions_file", str(data / "questions.jsonl"),
            *extra]


def _run_main(mod, monkeypatch, data, *extra, bad=()):
    saved = []
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", _fake_generator(saved, bad=set(bad)))
    monkeypatch.setattr(sys, "argv", _main_args(data, *extra))
    try:
        mod.main()
        code = 0
    except SystemExit as e:
        code = e.code
    # the fake does not write files; make the "saved" ones exist, as the real one would
    (data / "out").mkdir(exist_ok=True)
    for name in saved:
        (data / "out" / f"{name}.jsonl").write_text("{}\n")
    return code, saved


def _config(data):
    return json.loads((data / "out" / "generation_config.json").read_text())


def test_step1_writes_the_side_car_before_generating(mod, monkeypatch, data):
    code, saved = _run_main(mod, monkeypatch, data, "--max_tokens", "256")
    assert code == 0 and sorted(saved) == ["patient", "x", "y"]
    cfg = _config(data)
    assert cfg["schema"] == 1 and len(cfg["runs"]) == 1
    run = cfg["runs"][0]
    # the multi-model plan's field names (§ 7)
    for key in ("script", "created_at", "git_sha", "model_name", "template_kwargs",
                "response_cleanup", "sampling", "questions"):
        assert key in run, key
    assert run["model_name"] == "Qwen/fake"
    assert run["template_kwargs"] == {"enable_thinking": False}
    assert run["response_cleanup"] == "strip_leaked_think"
    assert run["sampling"] == {"temperature": 0.7, "top_p": 0.9, "max_tokens": 256,
                               "max_model_len": 2048}
    q = run["questions"]
    assert q["question_count"] == 300 and q["reduce_questions"] == 3 and q["n_kept"] == 3
    assert len(q["sha256"]) == 64
    assert set(run["instructions"]) == {"roles_dir", "traits_dir"}
    traits = run["instructions"]["traits_dir"]
    assert traits["n_files"] == 3 and set(traits["pos_sha256"]) == {"patient", "x", "y"}
    assert run["selection"]["flags"] == ["traits_only"]
    assert sorted(run["selection"]["pending"]) == ["patient", "x", "y"]


def test_a_rerun_with_the_same_settings_appends(mod, monkeypatch, data):
    _run_main(mod, monkeypatch, data, bad={"y"})
    code, saved = _run_main(mod, monkeypatch, data)
    assert code == 0 and saved == ["y"]
    runs = _config(data)["runs"]
    assert len(runs) == 2 and runs[1]["selection"]["pending"] == ["y"]


def test_a_rerun_with_other_settings_is_refused(mod, monkeypatch, data, caplog):
    _run_main(mod, monkeypatch, data, bad={"y"})
    with caplog.at_level(logging.ERROR):
        code, saved = _run_main(mod, monkeypatch, data, "--max_tokens", "1024")
    assert code == 1 and saved == []
    assert "sampling" in caplog.text and "fresh output directory" in caplog.text
    assert len(_config(data)["runs"]) == 1
    code, saved = _run_main(mod, monkeypatch, data, "--max_tokens", "1024",
                            "--allow_mixed_settings")
    assert code == 0 and saved == ["y"]
    assert _config(data)["runs"][1]["allow_mixed_settings"] is True


def test_a_changed_question_set_is_refused(mod, monkeypatch, data):
    _run_main(mod, monkeypatch, data, bad={"y"})
    (data / "questions.jsonl").write_text(
        "".join(json.dumps({"id": i, "question": f"Q{i}"}) + "\n" for i in range(9)))
    code, _ = _run_main(mod, monkeypatch, data)
    assert code == 1


def test_responses_without_a_record_are_refused(mod, monkeypatch, data, caplog):
    """A tree made before the side-car (the May 8slot tree): skip-if-exists
    would keep its responses beside new ones."""
    (data / "out").mkdir()
    (data / "out" / "x.jsonl").write_text("{}\n")
    with caplog.at_level(logging.ERROR):
        code, saved = _run_main(mod, monkeypatch, data)
    assert code == 1 and saved == []
    assert "no generation_config.json" in caplog.text
    assert not (data / "out" / "generation_config.json").exists()


def test_the_drivers_default_symlink_is_not_a_response_made_here(mod, monkeypatch, data):
    """run_pipeline.sh links default/responses/default.jsonl into a fresh
    type's responses directory before step 1; step 1 refused that tree as
    "made before 2026-10-12" on the October extraction's first pod."""
    (data / "default").mkdir()
    (data / "default" / "default.jsonl").write_text("{}\n")
    (data / "out").mkdir()
    (data / "out" / "default.jsonl").symlink_to("../default/default.jsonl")
    code, saved = _run_main(mod, monkeypatch, data)
    assert code == 0 and sorted(saved) == ["patient", "x", "y"]
    assert len(_config(data)["runs"]) == 1


def test_changed_instructions_are_named_not_refused(mod, monkeypatch, data, caplog):
    _run_main(mod, monkeypatch, data, bad={"y"})
    doc = json.loads((data / "traits" / "x.json").read_text())
    doc["instruction"][0]["pos"] = "rewritten"
    (data / "traits" / "x.json").write_text(json.dumps(doc))
    # a change outside the pos texts is not a change of what step 1 reads
    doc_p = json.loads((data / "traits" / "patient.json").read_text())
    doc_p["eval_prompt"] = "new rubric"
    (data / "traits" / "patient.json").write_text(json.dumps(doc_p))
    with caplog.at_level(logging.WARNING):
        code, saved = _run_main(mod, monkeypatch, data)
    assert code == 0 and saved == ["y"]
    warn = [r.message for r in caplog.records if "instruction file(s) changed" in r.message]
    assert len(warn) == 1 and ": x." in warn[0] and "patient" not in warn[0]


def test_nothing_to_do_writes_no_record(mod, monkeypatch, data):
    _run_main(mod, monkeypatch, data)
    _run_main(mod, monkeypatch, data)
    assert len(_config(data)["runs"]) == 1


# ---------------------------------------------------------------------------
# The family and the tokenizer fields of the side-car (multi-model plan,
# 2026-10-13, § 5.3, § 7)
# ---------------------------------------------------------------------------

def test_the_side_car_carries_the_family_header_and_sample(mod, monkeypatch, data):
    from assistant_axis.tests.internals_fakes import QWEN3_HEADER_TOKENS, make_qwen3_like_tokenizer
    code, _ = _run_main(mod, monkeypatch, data)
    assert code == 0
    run = _config(data)["runs"][0]
    assert run["model_type"] == "qwen3"
    assert run["header_tokens"] == QWEN3_HEADER_TOKENS
    tok = make_qwen3_like_tokenizer()
    assert run["header_ids"] == tok.convert_tokens_to_ids(QWEN3_HEADER_TOKENS)
    assert run["generation_prompt_ids"] == run["header_ids"]
    assert run["system_prompt"] == "native"
    # The sample: the first pending item's first instruction and the first
    # question, and the ids step 1 hands vLLM for it.
    assert run["sample_conversation"] == [
        {"role": "system", "content": "trait patient 0"}, {"role": "user", "content": "q0"}]
    ids = tok.apply_chat_template(run["sample_conversation"], tokenize=True,
                                  add_generation_prompt=True, return_dict=False,
                                  enable_thinking=False)
    assert run["sample_prompt_ids"] == list(ids)


def test_an_unknown_family_stops_step_1_before_anything(mod, monkeypatch, data, caplog):
    from assistant_axis.model_families import UnknownFamilyError

    def unknown(model_name):
        raise UnknownFamilyError("model_type 'nope' has no row in the family table")

    monkeypatch.setattr(mod, "preflight_generation", unknown)
    with caplog.at_level(logging.ERROR):
        code, saved = _run_main(mod, monkeypatch, data)
    assert code == 1 and saved == []
    assert "Qwen/fake: model_type 'nope' has no row" in caplog.text
    assert not (data / "out" / "generation_config.json").exists()


def test_a_rerun_under_another_header_is_refused(mod, monkeypatch, data, caplog):
    _run_main(mod, monkeypatch, data, bad={"y"})
    cfg = _config(data)
    cfg["runs"][0]["header_ids"] = [1, 11, 5]          # as if made with another template
    (data / "out" / "generation_config.json").write_text(json.dumps(cfg))
    with caplog.at_level(logging.ERROR):
        code, saved = _run_main(mod, monkeypatch, data)
    assert code == 1 and saved == [] and "header_ids" in caplog.text


def test_the_family_and_expected_ids_reach_the_generator(mod, monkeypatch, data):
    seen = {}

    class Gen:
        def __init__(self, **kw):
            seen.update(kw)
            self.generator = argparse.Namespace(load=lambda: None)

        def load_role(self, path):
            return {"instruction": [{"pos": "p"}]}

        def generate_role_responses(self, name, data):
            return []

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "0")
    monkeypatch.setattr(mod, "RoleResponseGenerator", Gen)
    monkeypatch.setattr(sys, "argv", _main_args(data))
    with pytest.raises(SystemExit):
        mod.main()                                   # no responses: items fail, exit 1
    assert seen["family"].model_type == "qwen3"
    assert seen["expected_header_ids"] == _config(data)["runs"][0]["header_ids"]
