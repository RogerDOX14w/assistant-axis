"""RoleResponseGenerator.save_responses never leaves a truncated response file.

Step 1 skips any role whose ``<role>.jsonl`` exists (``should_skip_role``),
so a copy that died half way used to leave a truncated file that every
later run treated as done.  Since 2026-10-12 the copy goes to a side name
and is renamed into place.  No model is loaded (vLLM is only imported by
``VLLMGenerator.load``).

The local staging copy also has a unique name per save since 2026-10-12
(it was ``/tmp/<role>.jsonl.tmp``, shared by every process saving that
name).  The tests stage into a temporary directory instead of ``/tmp``.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid

import pytest

import assistant_axis.generation as generation
from assistant_axis.generation import RoleResponseGenerator


@pytest.fixture
def staging(tmp_path, monkeypatch):
    d = tmp_path / "staging"
    d.mkdir()
    monkeypatch.setattr(generation, "_LOCAL_STAGING_DIR", d)
    return d


@pytest.fixture
def gen(tmp_path, staging):
    return RoleResponseGenerator(
        model_name="fake/model", roles_dir=str(tmp_path / "roles"),
        output_dir=str(tmp_path / "out"), questions_file=str(tmp_path / "q.jsonl"),
        short_name="Fake")


def _responses(n=4, content="x" * 50):
    return [{"label": "pos", "prompt_index": 0, "question_index": i,
             "conversation": [{"role": "assistant", "content": content}]} for i in range(n)]


def test_saved_file_is_complete(gen, staging):
    role = f"test_role_{uuid.uuid4().hex[:8]}"
    gen.save_responses(role, _responses())
    out = gen.output_dir / f"{role}.jsonl"
    assert [json.loads(l)["question_index"] for l in out.read_text().splitlines()] == [0, 1, 2, 3]
    assert not list(gen.output_dir.glob("*.inprogress"))
    assert not list(staging.iterdir())          # the staging copy is removed on success
    # the mode a plain open() gives, not a private temp file's 0600 (copy2 copies modes)
    umask = os.umask(0)
    os.umask(umask)
    assert out.stat().st_mode & 0o777 == 0o666 & ~umask


def test_a_copy_that_dies_half_way_leaves_no_response_file(gen, staging, monkeypatch):
    role = f"test_role_{uuid.uuid4().hex[:8]}"

    def half_copy(src, dst, *a, **k):
        data = open(src, "rb").read()
        with open(dst, "wb") as f:
            f.write(data[: len(data) // 2])
        raise OSError("connection reset")

    monkeypatch.setattr(shutil, "copy2", half_copy)
    monkeypatch.setattr("time.sleep", lambda s: None)
    with pytest.raises(OSError):
        gen.save_responses(role, _responses())
    assert not (gen.output_dir / f"{role}.jsonl").exists()
    assert not gen.should_skip_role(role)
    assert not list(gen.output_dir.glob("*.inprogress"))
    # the local staging copy stays behind on failure (kept for a manual retry)
    kept = list(staging.iterdir())
    assert len(kept) == 1 and kept[0].name.startswith(f"{role}.")
    assert len(kept[0].read_text().splitlines()) == 4


def test_two_saves_of_one_name_do_not_share_a_staging_file(tmp_path, staging, monkeypatch):
    """A role and a trait with the same stem (``patient``) saved by two step-1
    runs at once: while the role's copy is in flight the trait's save runs to
    completion.  With the fixed staging name the trait's save overwrote and
    then deleted the role's staging file, so the role's output got the
    trait's responses (or the copy failed)."""
    def make(kind):
        return RoleResponseGenerator(
            model_name="fake/model", roles_dir=str(tmp_path / kind),
            output_dir=str(tmp_path / kind / "responses"),
            questions_file=str(tmp_path / "q.jsonl"), short_name="Fake")

    as_role, as_trait = make("roles"), make("traits")
    real_copy2 = shutil.copy2
    interleaved = []

    def copy2_with_a_rival(src, dst, *a, **k):
        if not interleaved:
            interleaved.append(src)
            as_trait.save_responses("patient", _responses(content="TRAIT"))
        return real_copy2(src, dst, *a, **k)

    monkeypatch.setattr(shutil, "copy2", copy2_with_a_rival)
    as_role.save_responses("patient", _responses(content="ROLE"))

    def contents(gen):
        out = gen.output_dir / "patient.jsonl"
        return {json.loads(l)["conversation"][0]["content"] for l in out.read_text().splitlines()}

    assert contents(as_role) == {"ROLE"}
    assert contents(as_trait) == {"TRAIT"}
    assert not list(staging.iterdir())
