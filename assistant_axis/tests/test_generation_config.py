"""The generation_config.json helpers in assistant_axis/generation.py
(walk-through P2, 2026-10-12).  Step 1's use of them is tested in
pipeline/tests/test_1_generate.py."""
from __future__ import annotations

import json

import pytest

from assistant_axis import generation as g


def test_template_kwargs_and_cleanup_follow_the_model_family():
    assert g.chat_template_kwargs_for("Qwen/Qwen3-32B") == {"enable_thinking": False}
    assert g.chat_template_kwargs_for("google/gemma-2-27b-it") == {}
    assert g.response_cleanup_for("Qwen/Qwen3-32B") == "strip_leaked_think"
    assert g.response_cleanup_for("meta-llama/Llama-3.3-70B-Instruct") == "none"


def test_instruction_dir_record_hashes_the_pos_texts_only(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(
        {"instruction": [{"pos": "p", "neg": "n"}], "eval_prompt": "e1"}))
    (tmp_path / "b.json").write_text("not json")
    rec1 = g.instruction_dir_record(tmp_path)
    assert rec1["n_files"] == 2 and rec1["pos_sha256"]["b"] is None
    (tmp_path / "a.json").write_text(json.dumps(
        {"instruction": [{"pos": "p", "neg": "N"}], "eval_prompt": "e2"}))
    rec2 = g.instruction_dir_record(tmp_path)
    assert rec2["pos_sha256"]["a"] == rec1["pos_sha256"]["a"]     # pos unchanged
    assert rec2["sha256"] != rec1["sha256"]                       # the directory did change


def test_settings_differences_and_changed_instructions():
    base = {"model_name": "m", "template_kwargs": {}, "response_cleanup": "none",
            "sampling": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512, "max_model_len": 2048},
            "questions": {"sha256": "q", "question_count": 300, "reduce_questions": 3, "file": "a"},
            "instructions": {"traits_dir": {"pos_sha256": {"x": "1", "y": "2"}}}}
    same = json.loads(json.dumps(base))
    same["questions"]["file"] = "elsewhere/same.jsonl"     # the path alone is not a setting
    assert g.settings_differences(base, same) == []
    other = json.loads(json.dumps(base))
    other["sampling"]["max_tokens"] = 1024
    other["questions"]["reduce_questions"] = 1
    other["instructions"]["traits_dir"]["pos_sha256"].update({"y": "3", "z": "9"})
    diffs = g.settings_differences(base, other)
    assert len(diffs) == 2 and diffs[0].startswith("sampling:") and "reduce_questions" in diffs[1]
    assert g.changed_instructions(base, other) == ["y"]          # z is new, not changed


def test_write_appends_and_never_replaces_a_bad_file(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    out = tmp_path / "responses"
    out.mkdir()
    assert g.read_generation_config(out) is None
    g.write_generation_config(out, {"created_at": "1"})
    g.write_generation_config(out, {"created_at": "2"})
    cfg = g.read_generation_config(out)
    assert cfg["schema"] == 1 and [r["created_at"] for r in cfg["runs"]] == ["1", "2"]
    (out / g.GENERATION_CONFIG_NAME).write_text("{broken")
    with pytest.raises(ValueError):
        g.write_generation_config(out, {"created_at": "3"})
    assert (out / g.GENERATION_CONFIG_NAME).read_text() == "{broken"


def test_git_sha_names_this_checkout():
    sha = g.git_sha()
    assert sha is None or len(sha.split("+")[0]) >= 7
