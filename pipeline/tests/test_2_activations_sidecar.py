"""Step 2 checks step 1's side-car before loading any model (multi-model
plan § 5.5, § 9 test 8; § 15 Q10: a tree with no side-car needs
``--ignore_generation_config``).  On the in-process fakes: the preflight is
built from the Qwen3-like tokenizer, and ``ProbingModel`` is replaced by a
stand-in that only records that a load was attempted."""
from __future__ import annotations

import importlib.util
import json
import logging
import sys
from pathlib import Path

import pytest

from assistant_axis.generation import prompt_token_ids, write_generation_config
from assistant_axis.model_families import FAMILIES
from assistant_axis.tests.internals_fakes import (
    make_llama3_like_tokenizer,
    make_qwen3_like_tokenizer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = [{"role": "system", "content": "You are a pirate"},
          {"role": "user", "content": "What is law?"}]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_two_activations_sidecar", REPO_ROOT / "pipeline" / "2_activations.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(autouse=True)
def _tmpdir(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))


def _pre(mod, tokenizer=None, family="qwen3"):
    tok = tokenizer or make_qwen3_like_tokenizer()
    return mod.Preflight(family=FAMILIES[family], n_layers=3, tokenizer=tok,
                         layout=mod.derive_chat_layout(tok, FAMILIES[family]))


def _sidecar(responses: Path, pre, **over):
    """A side-car run record as step 1 writes it for this tokenizer and row
    (only the fields step 2 reads, and created_at)."""
    rec = {"created_at": "2026-10-13T00:00:00+00:00",
           "model_type": pre.family.model_type,
           "template_kwargs": dict(pre.family.template_kwargs),
           "header_ids": list(pre.layout.header_ids),
           "sample_conversation": SAMPLE,
           "sample_prompt_ids": prompt_token_ids(pre.tokenizer, SAMPLE,
                                                 pre.family.template_kwargs)}
    rec.update(over)
    responses.mkdir(exist_ok=True)
    write_generation_config(responses, rec)


def test_a_matching_side_car_passes(mod, tmp_path, caplog):
    pre = _pre(mod)
    _sidecar(tmp_path / "responses", pre)
    with caplog.at_level(logging.INFO):
        assert mod.check_generation_config(tmp_path / "responses", pre) == []
    assert "match" in caplog.text


@pytest.mark.parametrize("key, value, named", [
    ("template_kwargs", {"enable_thinking": True}, "template_kwargs: step 1 {'enable_thinking': True}"),
    ("header_ids", [1, 11, 5], "header_ids: step 1 [1, 11, 5]"),
    ("model_type", "llama", "model_type: step 1 'llama', step 2 'qwen3'"),
])
def test_another_setting_fails_naming_both(mod, tmp_path, key, value, named):
    pre = _pre(mod)
    _sidecar(tmp_path / "responses", pre, **{key: value})
    with pytest.raises(mod.GenerationConfigError) as e:
        mod.check_generation_config(tmp_path / "responses", pre)
    assert named in str(e.value) and "--ignore_generation_config" in str(e.value)


def test_sample_prompt_ids_not_a_prefix_fails(mod, tmp_path):
    # What the text path did on Llama: step 1's ids with a second BOS.
    tok = make_llama3_like_tokenizer()
    pre = _pre(mod, tokenizer=tok, family="llama")
    ids = prompt_token_ids(tok, SAMPLE, {})
    bos = tok.convert_tokens_to_ids("<|begin_of_text|>")
    _sidecar(tmp_path / "responses", pre, sample_prompt_ids=[bos] + ids)
    with pytest.raises(mod.GenerationConfigError, match="is not the start of step 2's rendering"):
        mod.check_generation_config(tmp_path / "responses", pre)
    # ... and the ids step 1 sends now pass.
    _sidecar(tmp_path / "responses", pre)                  # appended: the last run is checked
    assert mod.check_generation_config(tmp_path / "responses", pre) == []


def test_a_side_car_from_before_the_sample_fields_fails(mod, tmp_path):
    pre = _pre(mod)
    _sidecar(tmp_path / "responses", pre, sample_conversation=None, sample_prompt_ids=None)
    with pytest.raises(mod.GenerationConfigError, match="not recorded"):
        mod.check_generation_config(tmp_path / "responses", pre)


def test_no_side_car_refuses_without_the_flag_and_runs_with_it(mod, tmp_path, caplog):
    pre = _pre(mod)
    (tmp_path / "responses").mkdir()
    with pytest.raises(mod.GenerationConfigError, match="no generation_config.json"):
        mod.check_generation_config(tmp_path / "responses", pre)
    with caplog.at_level(logging.WARNING):
        diffs = mod.check_generation_config(tmp_path / "responses", pre, ignore=True)
    assert len(diffs) == 1 and "--ignore_generation_config given" in caplog.text


class _Loaded(Exception):
    """Raised by the stand-in ProbingModel: the run got as far as loading."""


def _run_main(mod, monkeypatch, tmp_path, *extra):
    responses = tmp_path / "responses"
    responses.mkdir(exist_ok=True)
    (responses / "alpha.jsonl").write_text("{}\n")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")

    def load(*a, **k):
        raise _Loaded()

    monkeypatch.setattr(mod, "ProbingModel", load)
    pre = _pre(mod)
    monkeypatch.setattr(mod, "preflight_model", lambda name, **kw: pre)
    monkeypatch.setattr(sys, "argv", ["2_activations.py", "--model", "Qwen/Qwen3-32B",
                                      "--responses_dir", str(responses),
                                      "--output_dir", str(tmp_path / "out"), *extra])
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        mod.main()
        return "returned"
    except SystemExit as e:
        return e.code
    except _Loaded:
        return "loaded"
    finally:
        for h in root.handlers[:]:        # main() adds a file handler
            if h not in before:
                root.removeHandler(h)
                h.close()


def test_a_mismatch_stops_main_before_the_model_is_loaded(mod, monkeypatch, tmp_path, caplog):
    _sidecar(tmp_path / "responses", _pre(mod), template_kwargs={"enable_thinking": True})
    with caplog.at_level(logging.ERROR):
        assert _run_main(mod, monkeypatch, tmp_path) == 1
    assert "does not match this model" in caplog.text


def test_a_matching_side_car_lets_main_load_the_model(mod, monkeypatch, tmp_path):
    _sidecar(tmp_path / "responses", _pre(mod))
    assert _run_main(mod, monkeypatch, tmp_path) == "loaded"


def test_the_8slot_case_no_side_car_needs_the_flag(mod, monkeypatch, tmp_path):
    assert _run_main(mod, monkeypatch, tmp_path) == 1
    assert _run_main(mod, monkeypatch, tmp_path, "--ignore_generation_config") == "loaded"


def test_the_merged_trees_last_run_is_the_one_checked(mod, tmp_path):
    # tools/merge_pod_outputs.py joins every pod's runs (marked with "pod");
    # the merge checked them equal, step 2 reads the last.
    pre = _pre(mod)
    _sidecar(tmp_path / "responses", pre, header_ids=[0], pod="roles")
    _sidecar(tmp_path / "responses", pre, pod="traits")
    cfg = json.loads((tmp_path / "responses" / "generation_config.json").read_text())
    assert [r["pod"] for r in cfg["runs"]] == ["roles", "traits"]
    assert mod.check_generation_config(tmp_path / "responses", pre) == []
