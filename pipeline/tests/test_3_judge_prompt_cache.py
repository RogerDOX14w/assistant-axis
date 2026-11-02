"""Tests for pipeline/3_judge.py --prompt_cache (2026-11-01): a judge that takes
OpenAI's prompt_cache_options (GPT-5.6 and later) is sent explicit mode with no
breakpoints by default, in real time (the SDK's extra_body) and in a Batch API
body (top level), and usage.json records and prices the cache tokens a reply
reports.  Why: those models cache every prompt of 1,024 tokens or more by
default and bill the write at 1.25x; a judge prompt is never read back.

No API calls: the clients are fakes.
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
    spec = importlib.util.spec_from_file_location("_pipeline_3_judge_prompt_cache", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_responses(responses_dir, name, n):
    responses_dir.mkdir(parents=True, exist_ok=True)
    with open(responses_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for q in range(n):
            f.write(json.dumps({"prompt_index": 0, "question_index": q, "question": f"q{q}", "label": "pos",
                                "conversation": [{"role": "user", "content": f"q{q}"},
                                                 {"role": "assistant", "content": f"a{q}"}]}) + "\n")


def _client(cache_write=0, cached=0):
    """A luna reply as the live probe of 2026-11-01 saw it: 1,218 prompt tokens, of which
    ``cache_write`` were written to the cache or ``cached`` read from it."""
    details = SimpleNamespace(cached_tokens=cached, cache_write_tokens=cache_write, audio_tokens=0)
    resp = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Reasoning.\nSCORE: 3"), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=1218, completion_tokens=4, prompt_tokens_details=details))
    client = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=resp)
    return client


def _run(judge, monkeypatch, responses_dir, output_dir, client, *extra, batch=False):
    """Step 3 on one trait under version 13, which takes gpt-5.6-luna only."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--roles_dir", str(ROLES), "--traits_dir", str(TRAITS), "--entity_type", "trait",
        "--no_incongruity_filtering", "--requests_per_second", "1000",
        *(["--batch_poll_seconds", "0"] if batch else ["--no_batch"]),
        "--prompt_version", "13", "--judge_model", "gpt-5.6-luna", *extra])
    asyncio.run(judge.main_async())


def test_real_time_calls_turn_caching_off_and_implicit_restores_the_default(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    client = _client()
    _run(judge, monkeypatch, responses_dir, output_dir, client)
    calls = [c.kwargs for c in client.chat.completions.create.call_args_list]
    assert len(calls) == 2
    assert all(c["extra_body"] == {"prompt_cache_options": {"mode": "explicit"}} for c in calls)
    assert all("prompt_cache_options" not in c and c["reasoning_effort"] == "none" for c in calls)
    assert json.loads((output_dir / "patient.json").read_text()) == {"pos_p0_q0": 3, "pos_p0_q1": 3}
    # nothing cached: the record reads as before
    usage = json.loads((output_dir / "usage.json").read_text())
    assert usage["per_model"]["gpt-5.6-luna"] == {
        "model": "gpt-5.6-luna", "prompt_tokens": 2436, "completion_tokens": 8, "cost_usd": 0.0005, "n_calls": 2}

    client = _client()
    _run(judge, monkeypatch, responses_dir, tmp_path / "scores_implicit", client, "--prompt_cache", "implicit")
    calls = [c.kwargs for c in client.chat.completions.create.call_args_list]
    assert len(calls) == 2 and all("extra_body" not in c and "prompt_cache_options" not in c for c in calls)


def test_usage_json_prices_the_cache_tokens_a_reply_reports(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    _run(judge, monkeypatch, responses_dir, output_dir, _client(cache_write=1215), "--prompt_cache", "implicit")
    rec = json.loads((output_dir / "usage.json").read_text())["per_model"]["gpt-5.6-luna"]
    assert rec["cache_write_tokens"] == 3 * 1215 and "cache_read_tokens" not in rec
    assert rec["prompt_tokens"] == 3 * 1218 and rec["n_calls"] == 3
    # per call: 3 plain tokens at $0.20, 1,215 written at 1.25 x $0.20, 4 out at $1.20 (per 1M)
    assert rec["cost_usd"] == pytest.approx(3 * (3 * 0.20 + 1215 * 0.25 + 4 * 1.20) / 1e6, abs=5e-5)
    # a resume merges the counts and recomputes the cost with them
    _write_responses(responses_dir, "patient", 4)
    _run(judge, monkeypatch, responses_dir, output_dir, _client(cached=1215), "--prompt_cache", "implicit")
    rec = json.loads((output_dir / "usage.json").read_text())["per_model"]["gpt-5.6-luna"]
    assert rec["cache_write_tokens"] == 3 * 1215 and rec["cache_read_tokens"] == 1215 and rec["n_calls"] == 4


def test_batch_bodies_carry_the_field_at_top_level(judge, monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("_test_3_judge_fakes", REPO / "pipeline" / "tests" / "test_3_judge.py")
    fakes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fakes)
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    client = fakes.FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    # the fake keeps the result files beside the request files: keep the request lines
    lines = [rec for text in client.uploaded.values() for x in text.splitlines() if x.strip()
             for rec in [json.loads(x)] if rec.get("method") == "POST"]
    assert len(lines) == 2
    assert all(line["body"]["prompt_cache_options"] == {"mode": "explicit"} for line in lines)
    assert all("extra_body" not in line["body"] for line in lines)
    assert json.loads((output_dir / "patient.json").read_text()) == {"pos_p0_q0": 3, "pos_p0_q1": 3}
    assert list(json.loads((output_dir / "usage.json").read_text())["per_model"]) == ["gpt-5.6-luna:batch"]
    assert client.chat.completions.create.call_count == 0

    client = fakes.FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, tmp_path / "scores_implicit", client, "--prompt_cache", "implicit",
         batch=True)
    lines = [rec for text in client.uploaded.values() for x in text.splitlines() if x.strip()
             for rec in [json.loads(x)] if rec.get("method") == "POST"]
    assert len(lines) == 2 and all("prompt_cache_options" not in line["body"] for line in lines)
