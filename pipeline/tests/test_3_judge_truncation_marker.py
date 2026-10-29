"""Tests for pipeline/3_judge.py --mark_truncated (Roger, 2026-10-28): a
response step 1 cut at --max_tokens (finish_reason "length") is shown to the
judge with "…" appended (no space; the steering judges see " …"); only the judge's copy
is marked, the setting is recorded in judge_rubric.json, and a scores
directory judged with the other setting is refused.

No API calls: the OpenAI client is a mock that records the prompts it gets.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "pipeline" / "3_judge.py"
ROLES = REPO / "data" / "roles" / "instructions"
TRAITS = REPO / "data" / "traits" / "instructions"


@pytest.fixture(scope="module")
def judge():
    spec = importlib.util.spec_from_file_location("_pipeline_3_judge_truncation", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _responses(finish_reasons):
    out = []
    for q, fr in enumerate(finish_reasons):
        r = {"prompt_index": 0, "question_index": q, "question": f"q{q}", "label": "pos",
             "conversation": [{"role": "system", "content": "Be patient."},
                              {"role": "user", "content": f"q{q}"},
                              {"role": "assistant", "content": f"answer {q}"}]}
        if fr is not None:
            r["finish_reason"] = fr
        out.append(r)
    return out


def test_only_responses_cut_at_the_cap_are_marked(judge):
    rs = _responses(["length", "stop", None])
    marked, n = judge.mark_truncated_responses(rs)
    assert n == 1
    assert [r["conversation"][-1]["content"] for r in marked] == ["answer 0…", "answer 1", "answer 2"]
    assert marked[0]["conversation"][0] == rs[0]["conversation"][0]   # system and user turns untouched
    assert rs[0]["conversation"][-1]["content"] == "answer 0"          # the input is not changed


def test_the_judge_prompt_carries_the_marker(judge):
    marked, _ = judge.mark_truncated_responses(_responses(["length", "stop"]))
    prompts = dict(judge.pending_prompts(marked, "Q: {question}\nA: {answer}\nEND", {}))
    assert prompts["pos_p0_q0"] == "Q: q0\nA: answer 0…\nEND"
    assert prompts["pos_p0_q1"] == "Q: q1\nA: answer 1\nEND"


def test_the_conflict_check_reads_the_stamp(judge, tmp_path):
    assert judge.truncation_marker_conflict(tmp_path, judge.TRUNCATION_MARKER) is None   # no stamp
    judge.stamp_rubric(tmp_path, entity_type="trait", judge_model="gpt-4.1-mini")
    # a stamp without the field predates the flag: no marker
    assert judge.truncation_marker_conflict(tmp_path, None) is None
    msg = judge.truncation_marker_conflict(tmp_path, judge.TRUNCATION_MARKER)
    assert "no truncation marker" in msg and "--mark_truncated" in msg
    judge.stamp_rubric(tmp_path, entity_type="trait", judge_model="gpt-4.1-mini",
                       extra={"truncation_marker": judge.TRUNCATION_MARKER})
    assert judge.truncation_marker_conflict(tmp_path, judge.TRUNCATION_MARKER) is None
    assert "the truncation marker" in judge.truncation_marker_conflict(tmp_path, None)


def _client(prompts):
    async def create(**kw):
        prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Fine.\nSCORE: 3"),
                                     finish_reason="stop")],
            usage=SimpleNamespace(prompt_tokens=300, completion_tokens=40))
    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=create)
    return client


def _run(judge, monkeypatch, responses_dir, output_dir, client, *extra):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda **kw: client)
    monkeypatch.setattr(judge, "judge_client", lambda model, tier=None: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--roles_dir", str(ROLES), "--traits_dir", str(TRAITS), "--entity_type", "trait",
        "--no_incongruity_filtering", "--requests_per_second", "1000", "--no_batch", *extra])
    asyncio.run(judge.main_async())


def _write(responses_dir, finish_reasons):
    responses_dir.mkdir(exist_ok=True)
    with open(responses_dir / "patient.jsonl", "w") as f:
        for r in _responses(finish_reasons):
            f.write(json.dumps(r) + "\n")


def test_by_default_a_run_marks_stamps_and_refuses_the_other_setting(judge, monkeypatch, tmp_path, caplog):
    """The default since 2026-10-28 (Roger): marked, with no flag."""
    caplog.set_level("INFO")
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write(responses_dir, ["length", "stop", "length"])
    prompts = []
    _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts))
    assert sum("answer 0…" in p for p in prompts) == 1 and sum("answer 2…" in p for p in prompts) == 1
    assert not any("answer 1…" in p for p in prompts)
    stamp = json.loads((output_dir / "judge_rubric.json").read_text())
    assert stamp["truncation_marker"] == judge.TRUNCATION_MARKER
    assert "Marked as cut off" in caplog.text and "2 of 3 responses read" in caplog.text

    # the same directory with --no_mark_truncated is refused, before any request
    _write(responses_dir, ["length", "stop", "length", "stop"])   # one response not yet scored
    n_before = len(prompts)
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts), "--no_mark_truncated")
    assert e.value.code == 1 and len(prompts) == n_before
    assert "judged with the truncation marker" in caplog.text
    # --mark_truncated, kept for explicit commands, is the default's setting
    _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts), "--mark_truncated")
    assert len(prompts) == n_before + 1


def test_no_mark_truncated_shows_the_text_as_stored(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write(responses_dir, ["length", "stop"])
    prompts = []
    _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts), "--no_mark_truncated")
    assert prompts and not any("…" in p for p in prompts)
    assert json.loads((output_dir / "judge_rubric.json").read_text())["truncation_marker"] is None


def test_a_directory_judged_before_the_default_needs_the_flag_off(judge, monkeypatch, tmp_path, caplog):
    """A stamp written before 2026-10-28 has no truncation_marker: a default run into it is
    refused, naming --mark_truncated, and --no_mark_truncated resumes it."""
    caplog.set_level("INFO")
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write(responses_dir, ["length", "stop"])
    output_dir.mkdir()
    judge.stamp_rubric(output_dir, entity_type="trait", judge_model="gpt-4.1-mini")
    stamp = json.loads((output_dir / "judge_rubric.json").read_text())
    stamp.pop("truncation_marker", None)
    (output_dir / "judge_rubric.json").write_text(json.dumps(stamp))
    prompts = []
    with pytest.raises(SystemExit):
        _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts))
    assert not prompts and "no truncation marker" in caplog.text
    _run(judge, monkeypatch, responses_dir, output_dir, _client(prompts), "--no_mark_truncated")
    assert len(prompts) == 2 and not any("…" in p for p in prompts)
