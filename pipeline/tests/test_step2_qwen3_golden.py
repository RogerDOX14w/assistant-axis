"""The golden gate: step 2 on Qwen3 is byte-identical to before the multi-model work.

reports/pipeline/coding_plan_multi_model_extraction.md § 9 test 1.  The
fixture (``fixtures/step2_qwen3_fake_golden.pt``, from the 12 records of
``fixtures/step2_qwen3_fake_golden.jsonl``) was made by
``fixtures/make_step2_qwen3_fake_golden.py`` from commit 828817a4, the code
before any of that work, on the in-process fakes.  This test runs today's
``process_role`` on the same records with the same arguments and requires:

* the same activation keys;
* every activation bit for bit the same (bf16 compared as its int16 bit
  pattern, so NaNs compare too), same shape and dtype;
* the same metadata for every key the fixture has except ``thinking``,
  which the plan removes (§ 5.4: it was ``False`` in every file and is now the
  ``enable_thinking`` entry of ``template_kwargs``), and the seven Qwen3
  header tokens;
* the same header-mismatch count.

It does not depend on how the new code is written: only on
``process_role(pm, file, out_dir, layers, batch_size, max_length,
extract_headers=...)`` and the fakes.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import torch

from assistant_axis.tests.internals_fakes import (
    QWEN3_HEADER_TOKENS,
    make_fake_probing_model,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOLDEN_PT = FIXTURES / "step2_qwen3_fake_golden.pt"
GOLDEN_JSONL = FIXTURES / "step2_qwen3_fake_golden.jsonl"
REMOVED_METADATA_KEYS = {"thinking"}


@pytest.fixture(scope="module")
def step2():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_two_activations_golden", REPO_ROOT / "pipeline" / "2_activations.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def golden():
    return torch.load(GOLDEN_PT, weights_only=False)


def _bits(t: torch.Tensor) -> torch.Tensor:
    return t.view(torch.int16) if t.dtype == torch.bfloat16 else t


@pytest.mark.parametrize("run_key", ["headers", "no_headers"])
def test_step2_matches_the_pre_change_fixture(step2, golden, run_key, tmp_path):
    assert golden["source_commit"].startswith("828817a4")
    expected = golden[run_key]
    run = expected["run"]
    responses = tmp_path / "golden.jsonl"
    responses.write_text(GOLDEN_JSONL.read_text())
    out_dir = tmp_path / "out"
    out_dir.mkdir()

    saved, n_mm = step2.process_role(make_fake_probing_model(3), responses, out_dir,
                                     run["layers"], run["batch_size"], golden["max_length"],
                                     extract_headers=run["extract_headers"])
    assert saved and n_mm == expected["mismatches"]

    data = torch.load(out_dir / "golden.pt", weights_only=False)
    meta = data.pop("metadata")
    assert sorted(data) == sorted(expected["activations"])
    for key, want in expected["activations"].items():
        got = data[key]
        assert got.dtype == want.dtype and got.shape == want.shape, key
        assert torch.equal(_bits(got), _bits(want)), f"{key} differs from the fixture"

    for k, v in expected["metadata"].items():
        if k in REMOVED_METADATA_KEYS:
            continue
        assert meta.get(k) == v, f"metadata[{k!r}]: {meta.get(k)!r} != {v!r}"
    if run["extract_headers"]:
        assert meta["header_tokens"] == QWEN3_HEADER_TOKENS
