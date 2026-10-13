"""pipeline/2_activations.py's command line since the multi-model plan
(reports/pipeline/coding_plan_multi_model_extraction.md § 8, § 9 test 6):
``--thinking`` is gone (an argparse error saying why), ``--layers`` is
validated, and a model whose family is unknown is refused before any model is
loaded.  Nothing is loaded or downloaded: the preflight (config.json and the
tokenizer) is faked."""
from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

import pytest

from assistant_axis.model_families import FAMILIES, UnknownFamilyError
from assistant_axis.tests.internals_fakes import make_qwen3_like_tokenizer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_two_activations_cli", REPO_ROOT / "pipeline" / "2_activations.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


BASE = ["--model", "Qwen/Qwen3-32B", "--responses_dir", "r", "--output_dir", "o"]


@pytest.mark.parametrize("extra", [["--thinking"], ["--thinking", "false"],
                                   ["--thinking", "true"]])
def test_thinking_is_an_argparse_error(mod, capsys, extra):
    with pytest.raises(SystemExit) as e:
        mod.build_parser().parse_args(BASE + extra)
    assert e.value.code == 2
    assert "--thinking was removed" in capsys.readouterr().err


@pytest.mark.parametrize("spec", ["3,1", "1,1", "-1", "a"])
def test_layers_form_and_order_are_checked_by_the_parser(mod, capsys, spec):
    with pytest.raises(SystemExit) as e:
        mod.build_parser().parse_args(BASE + ["--layers", spec])
    assert e.value.code == 2 and "--layers" in capsys.readouterr().err


def test_verify_spans_defaults_to_off(mod):
    args = mod.build_parser().parse_args(BASE)
    assert args.verify_spans == 0 and args.layers == "all"
    assert mod.build_parser().parse_args(BASE + ["--verify_spans", "20"]).verify_spans == 20


def _run_main(mod, monkeypatch, tmp_path, argv_extra, preflight):
    responses = tmp_path / "responses"
    responses.mkdir()
    (responses / "alpha.jsonl").write_text("{}\n")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")

    def no_model(*a, **k):
        raise AssertionError("a model was loaded")

    monkeypatch.setattr(mod, "ProbingModel", no_model)
    monkeypatch.setattr(mod, "preflight_model", preflight)
    monkeypatch.setattr(sys, "argv", ["2_activations.py", "--model", "x/y", "--responses_dir",
                                      str(responses), "--output_dir", str(tmp_path / "out")]
                        + argv_extra)
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
    return e.value.code


def _qwen_preflight(mod, n_layers=3):
    tok = make_qwen3_like_tokenizer()
    return lambda name, **kw: mod.Preflight(
        family=FAMILIES["qwen3"], n_layers=n_layers, tokenizer=tok,
        layout=mod.derive_chat_layout(tok, FAMILIES["qwen3"]))


def test_layers_out_of_range_is_refused_before_the_model_loads(mod, monkeypatch, tmp_path,
                                                              capsys):
    code = _run_main(mod, monkeypatch, tmp_path, ["--layers", "1,64"], _qwen_preflight(mod))
    assert code == 2
    assert "[64] out of range (the model has 3 layers, 0..2)" in capsys.readouterr().err


def test_an_unknown_model_type_is_refused_before_the_model_loads(mod, monkeypatch, tmp_path,
                                                                 caplog):
    def unknown(name, **kw):
        raise UnknownFamilyError("model_type 'nope' has no row in the family table")

    assert _run_main(mod, monkeypatch, tmp_path, [], unknown) == 1
    assert "x/y: model_type 'nope' has no row" in caplog.text
