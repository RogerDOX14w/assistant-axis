"""RoleResponseGenerator.save_responses never leaves a truncated response file.

Step 1 skips any role whose ``<role>.jsonl`` exists (``should_skip_role``),
so a copy that died half way used to leave a truncated file that every
later run treated as done.  Since 2026-10-12 the copy goes to a side name
and is renamed into place.  No model is loaded (vLLM is only imported by
``VLLMGenerator.load``).
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

import pytest

from assistant_axis.generation import RoleResponseGenerator


@pytest.fixture
def gen(tmp_path):
    return RoleResponseGenerator(
        model_name="fake/model", roles_dir=str(tmp_path / "roles"),
        output_dir=str(tmp_path / "out"), questions_file=str(tmp_path / "q.jsonl"),
        short_name="Fake")


def _responses(n=4):
    return [{"label": "pos", "prompt_index": 0, "question_index": i,
             "conversation": [{"role": "assistant", "content": "x" * 50}]} for i in range(n)]


def test_saved_file_is_complete(gen):
    role = f"test_role_{uuid.uuid4().hex[:8]}"
    gen.save_responses(role, _responses())
    out = gen.output_dir / f"{role}.jsonl"
    assert [json.loads(l)["question_index"] for l in out.read_text().splitlines()] == [0, 1, 2, 3]
    assert not list(gen.output_dir.glob("*.inprogress"))


def test_a_copy_that_dies_half_way_leaves_no_response_file(gen, monkeypatch):
    role = f"test_role_{uuid.uuid4().hex[:8]}"

    def half_copy(src, dst, *a, **k):
        data = open(src, "rb").read()
        with open(dst, "wb") as f:
            f.write(data[: len(data) // 2])
        raise OSError("connection reset")

    monkeypatch.setattr(shutil, "copy2", half_copy)
    monkeypatch.setattr("time.sleep", lambda s: None)
    try:
        with pytest.raises(OSError):
            gen.save_responses(role, _responses())
    finally:   # the local staging copy stays behind on failure (kept for a manual retry)
        (Path("/tmp") / f"{role}.jsonl.tmp").unlink(missing_ok=True)
    assert not (gen.output_dir / f"{role}.jsonl").exists()
    assert not gen.should_skip_role(role)
    assert not list(gen.output_dir.glob("*.inprogress"))
