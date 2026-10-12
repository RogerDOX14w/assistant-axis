"""RoleResponseGenerator's inputs: the question list and the instruction files.

Since 2026-10-12 both are read through ``assistant_axis.atomic_io`` with the
project-standard retry (the repo lives on the /workspace network mount on
RunPod, where reads can fail with a transient EIO), and a malformed question
line raises instead of being skipped (skipping it would renumber every later
question, and ``question_index`` is a position in the list).  No model is
loaded.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import assistant_axis.atomic_io as atomic_io
from assistant_axis.generation import RoleResponseGenerator


def _gen(tmp_path, **kw):
    return RoleResponseGenerator(
        model_name="fake/model", roles_dir=str(tmp_path), output_dir=str(tmp_path / "out"),
        questions_file=str(tmp_path / "q.jsonl"), short_name="Fake", **kw)


def _write_questions(tmp_path, n):
    (tmp_path / "q.jsonl").write_text(
        "".join(json.dumps({"id": i, "question": f"q{i}"}) + "\n" for i in range(n)))


@pytest.fixture
def flaky_read_text(monkeypatch):
    """Path.read_text fails once with EIO, then reads normally; no sleeping."""
    real = Path.read_text
    calls = []

    def flaky(self, *a, **k):
        calls.append(self)
        if len(calls) == 1:
            raise OSError(5, "Input/output error")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", flaky)
    monkeypatch.setattr(atomic_io.time, "sleep", lambda s: None)
    return calls


def test_question_count_then_every_nth(tmp_path):
    """questions[:question_count][::reduce_questions], as the pipeline's
    defaults (300, 3) give 100 questions; indices are positions in that list."""
    _write_questions(tmp_path, 10)
    assert _gen(tmp_path, question_count=7, reduce_questions=3).load_questions() == ["q0", "q3", "q6"]
    assert _gen(tmp_path, question_count=300, reduce_questions=1).load_questions() == [
        f"q{i}" for i in range(10)]


def test_a_malformed_question_line_raises(tmp_path):
    _write_questions(tmp_path, 3)
    with open(tmp_path / "q.jsonl", "a") as f:
        f.write("{not json\n")
    with pytest.raises(ValueError, match="malformed"):
        _gen(tmp_path).load_questions()


def test_questions_read_is_retried(tmp_path, flaky_read_text):
    _write_questions(tmp_path, 4)
    assert _gen(tmp_path).load_questions() == ["q0", "q1", "q2", "q3"]
    assert len(flaky_read_text) == 2


def test_instruction_file_read_is_retried(tmp_path, flaky_read_text):
    path = tmp_path / "pirate.json"
    path.write_text(json.dumps({"instruction": [{"pos": "Arr"}]}))
    gen = _gen(tmp_path)
    flaky_read_text.clear()
    assert gen.load_role(path) == {"instruction": [{"pos": "Arr"}]}
    assert len(flaky_read_text) == 2
