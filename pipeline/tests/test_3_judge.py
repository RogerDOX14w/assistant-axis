"""Tests for pipeline/3_judge.py: the judge display form in its prompts (W19,
JUDGE_RUBRIC_VERSION 2) and the usage record beside its scores (W24).

No API calls: the OpenAI client is a mock that returns a fixed reply and
token counts.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
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
    spec = importlib.util.spec_from_file_location("_pipeline_3_judge_under_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_loading_does_not_import_torch_or_the_package():
    """The script's reason for loading modules standalone: the package
    __init__ imports torch, which can take minutes on a network mount."""
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('j', {str(SCRIPT)!r})\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "print('torch' in sys.modules, 'assistant_axis' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["False", "False"]


class TestJudgeDisplayForm:
    def test_rubric_version(self, judge):
        assert judge.JUDGE_RUBRIC_VERSION == 2
        assert judge.JUDGE_LABEL_FORM == "judge-display-v1"

    def test_trait_prompt_uses_the_long_form_of_a_standard(self, judge):
        p = judge.resolve_eval_prompt("enfj_mbti", ROLES, TRAITS, "trait")
        assert "displays the trait: **ENFJ (from the MBTI)**." in p
        p = judge.resolve_eval_prompt("killer_bartle", ROLES, TRAITS, "trait")
        assert "**killer (from Bartle's player types)**" in p

    def test_plain_trait_prompt_is_unchanged(self, judge):
        doc = json.loads((TRAITS / "patient.json").read_text())
        p = judge.resolve_eval_prompt("patient", ROLES, TRAITS, "trait")
        assert f"displays the trait: **{doc['positive_label']}**. {doc['description']}" in p

    def test_combination_prompt_no_longer_shows_raw_stems(self, judge):
        p = judge.resolve_eval_prompt("r_devils_advocate__systems_thinker", ROLES, TRAITS, "combination")
        assert "1. The role: **devil's advocate** — " in p
        assert "2. The trait: **systems-thinker** — " in p
        assert "devils_advocate" not in p and "systems_thinker" not in p
        p = judge.resolve_eval_prompt("t_coral_reef__careless_hexaco", ROLES, TRAITS, "combination")
        assert "**coral reef**" in p and "**careless (from HEXACO)**" in p

    def test_role_prompt_is_the_files_eval_prompt(self, judge):
        doc = json.loads((ROLES / "devils_advocate.json").read_text())
        assert judge.resolve_eval_prompt("devils_advocate", ROLES, TRAITS, "role") == doc["eval_prompt"]
        assert "**devil's advocate**" in doc["eval_prompt"]

    def test_traits_dir_outside_the_corpus_layout(self, judge, tmp_path):
        """A --traits_dir that is not <root>/traits/instructions still gets
        the label from the file it reads."""
        (tmp_path / "careless_hexaco.json").write_text(json.dumps(
            {"positive_label": "careless (HEXACO)", "description": "D."}))
        p = judge.resolve_eval_prompt("careless_hexaco", tmp_path, tmp_path, "trait")
        assert "**careless (from HEXACO)**. D." in p


# ---------------------------------------------------------------------------
# W24: usage.json
# ---------------------------------------------------------------------------

def _client(prompt_tokens=300, completion_tokens=40, text="Reasoning.\nSCORE: 3"):
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
    )
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


def _responses(n: int) -> list[dict]:
    return [{"prompt_index": 0, "question_index": q, "question": f"q{q}", "label": "pos",
             "conversation": [{"role": "user", "content": f"q{q}"},
                              {"role": "assistant", "content": f"a{q}"}]}
            for q in range(n)]


def test_score_entity_ticks_the_usage_tracker(judge):
    usage = judge.MultiModelUsage()
    scores, n_attempted, n_parsed = asyncio.run(judge.score_entity(
        name="patient", responses=_responses(3), eval_prompt_template="{question} {answer}",
        client=_client(), rate_limiter=judge.RateLimiter(1000), judge_model="gpt-4.1-mini",
        max_tokens=200, batch_size=50, existing_scores={}, usage=usage,
    ))
    assert n_attempted == n_parsed == 3 and set(scores.values()) == {3}
    assert usage.n_calls == 3
    assert usage.total_prompt_tokens == 900 and usage.total_completion_tokens == 120
    assert list(usage.per_model) == ["gpt-4.1-mini"]


def _run(judge, monkeypatch, responses_dir, output_dir, client):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--roles_dir", str(ROLES), "--traits_dir", str(TRAITS), "--entity_type", "trait",
        "--no_incongruity_filtering", "--requests_per_second", "1000",
    ])
    asyncio.run(judge.main_async())


def test_main_writes_usage_json_and_merges_on_resume(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    responses_dir.mkdir()
    with open(responses_dir / "patient.jsonl", "w") as f:
        for r in _responses(4):
            f.write(json.dumps(r) + "\n")
    client = _client()

    _run(judge, monkeypatch, responses_dir, output_dir, client)
    usage = json.loads((output_dir / "usage.json").read_text())
    assert usage["n_calls"] == 4 and usage["total_prompt_tokens"] == 1200
    assert set(usage["per_model"]) == {"gpt-4.1-mini"} and usage["total_cost_usd"] > 0
    assert json.loads((output_dir / "patient.json").read_text()) == {
        f"pos_p0_q{q}": 3 for q in range(4)}
    stamp = json.loads((output_dir / "judge_rubric.json").read_text())
    assert stamp["rubric_version"] == 2 and stamp["rubric_versions"] == [2]
    assert stamp["label_form"] == "judge-display-v1" and stamp["judge_models"] == ["gpt-4.1-mini"]

    # Resume with two more responses: only those are judged, and the record
    # accumulates instead of being overwritten.
    with open(responses_dir / "patient.jsonl", "a") as f:
        for r in _responses(6)[4:]:
            f.write(json.dumps(r) + "\n")
    _run(judge, monkeypatch, responses_dir, output_dir, client)
    usage = json.loads((output_dir / "usage.json").read_text())
    assert usage["n_calls"] == 6 and usage["total_prompt_tokens"] == 1800
    assert client.chat.completions.create.call_count == 6

    # A run with nothing to judge leaves the record as it was.
    _run(judge, monkeypatch, responses_dir, output_dir, client)
    assert json.loads((output_dir / "usage.json").read_text())["n_calls"] == 6


def test_stamp_marks_unstamped_scores_as_version_1(judge, tmp_path, caplog):
    (tmp_path / "patient.json").write_text(json.dumps({"pos_p0_q0": 3}))
    stamp = judge.stamp_rubric(tmp_path, entity_type="trait", judge_model="gpt-4.1-mini")
    assert stamp["rubric_versions"] == [1, 2]
    assert "rubric versions [1, 2]" in caplog.text
    # side-cars alone do not count as scores
    fresh = tmp_path / "fresh"; fresh.mkdir()
    (fresh / "usage.json").write_text("{}")
    assert judge.stamp_rubric(fresh, entity_type="trait", judge_model="m")["rubric_versions"] == [2]
