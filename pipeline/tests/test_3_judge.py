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


def _run(judge, monkeypatch, responses_dir, output_dir, client, *extra, batch=False):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--roles_dir", str(ROLES), "--traits_dir", str(TRAITS), "--entity_type", "trait",
        "--no_incongruity_filtering", "--requests_per_second", "1000",
        *(["--batch_poll_seconds", "0"] if batch else ["--no_batch"]), *extra,
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


# ---------------------------------------------------------------------------
# Batch mode (the default since 2026-10-10)
# ---------------------------------------------------------------------------

class FakeBatchClient:
    """The slice of ``openai.AsyncOpenAI`` batch mode uses: files.create /
    content / delete and batches.create / retrieve.  A batch is in progress
    when created and completed at its first retrieve.  ``limit`` makes any
    batch of more requests than that fail validation with
    ``token_limit_exceeded`` while another is in flight, or always when it is
    larger than ``hard_limit``; ``error_ids`` are answered with an error line.
    The real-time fallback goes to ``chat.completions.create``."""

    def __init__(self, text="Reasoning.\nSCORE: 3", *, limit=None, hard_limit=None, error_ids=()):
        self.text, self.limit, self.hard_limit, self.error_ids = text, limit, hard_limit, set(error_ids)
        self.uploaded, self.batches_created, self.deleted = {}, [], []
        self.inflight = set()
        self._batches = {}
        self.files = SimpleNamespace(create=self._fcreate, content=self._fcontent, delete=self._fdelete)
        self.batches = SimpleNamespace(create=self._bcreate, retrieve=self._bretrieve)
        self.chat = _client(text=text).chat

    async def _fcreate(self, file, purpose):
        assert purpose == "batch"
        fid = f"file-{len(self.uploaded)}"
        self.uploaded[fid] = file[1].decode("utf-8")
        return SimpleNamespace(id=fid)

    async def _fcontent(self, fid):
        return SimpleNamespace(text=self.uploaded[fid])

    async def _fdelete(self, fid):
        self.deleted.append(fid)

    def _lines(self, fid):
        return [json.loads(x) for x in self.uploaded[fid].splitlines() if x.strip()]

    async def _bcreate(self, input_file_id, endpoint, completion_window, metadata):
        assert endpoint == "/v1/chat/completions" and completion_window == "24h"
        bid = f"batch-{len(self._batches)}"
        n = len(self._lines(input_file_id))
        over = self.limit is not None and n > self.limit and (self.inflight or (self.hard_limit is not None and n > self.hard_limit))
        status = "failed" if over else "in_progress"
        errors = SimpleNamespace(data=[SimpleNamespace(code="token_limit_exceeded", message="Enqueued token limit reached")]) if over else None
        self._batches[bid] = {"input": input_file_id, "status": status, "errors": errors}
        self.batches_created.append((bid, n, status))
        if not over:
            self.inflight.add(bid)
        return SimpleNamespace(id=bid, status=status, errors=errors)

    async def _bretrieve(self, bid):
        b = self._batches[bid]
        if b["status"] == "in_progress":
            out = []
            for line in self._lines(b["input"]):
                cid = line["custom_id"]
                if cid in self.error_ids:
                    out.append({"custom_id": cid, "response": {"status_code": 500, "body": {"error": {"message": "server"}}}, "error": None})
                else:
                    out.append({"custom_id": cid, "error": None, "response": {"status_code": 200, "body": {
                        "choices": [{"message": {"content": self.text}}],
                        "usage": {"prompt_tokens": 300, "completion_tokens": 40}}}})
            ofid = f"file-out-{bid}"
            self.uploaded[ofid] = "\n".join(json.dumps(o) for o in out) + "\n"
            b.update(status="completed", output_file_id=ofid)
            self.inflight.discard(bid)
        return SimpleNamespace(id=bid, status=b["status"], errors=b["errors"],
                               output_file_id=b.get("output_file_id"), error_file_id=None,
                               request_counts=SimpleNamespace(completed=0, total=0))


def _write_responses(responses_dir, name, n):
    responses_dir.mkdir(exist_ok=True)
    with open(responses_dir / f"{name}.jsonl", "w") as f:
        for r in _responses(n):
            f.write(json.dumps(r) + "\n")


def test_batch_is_the_default_and_sends_the_real_time_request(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)

    assert json.loads((output_dir / "patient.json").read_text()) == {f"pos_p0_q{q}": 3 for q in range(4)}
    assert client.chat.completions.create.call_count == 0          # nothing in real time
    lines = client._lines("file-0")
    assert [l["custom_id"] for l in lines] == [f"patient|pos_p0_q{q}" for q in range(4)]
    body = lines[0]["body"]
    assert body == judge.chat_request_body(body["messages"][0]["content"], "gpt-4.1-mini", 200)
    assert body["temperature"] == 1 and body["max_completion_tokens"] == 200
    usage = json.loads((output_dir / "usage.json").read_text())
    assert set(usage["per_model"]) == {"gpt-4.1-mini:batch"} and usage["n_calls"] == 4
    # priced at half the real-time rates
    rt_in, rt_out = judge._pricing_mod.price_for_model("gpt-4.1-mini")
    assert judge._pricing_mod.price_for_model("gpt-4.1-mini:batch") == (rt_in / 2, rt_out / 2)
    state = json.loads((output_dir / "batch_state.json").read_text())
    assert [r["collected"] for r in state["chunks"]] == [True]
    assert not list((output_dir / "_batches").glob("*.jsonl"))       # chunk files removed
    assert {"file-0", "file-out-batch-0"} <= set(client.deleted)       # service files tidied

    # a second run finds nothing to judge and submits nothing
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(client.batches_created) == 1


def test_requests_are_split_into_batches_of_the_given_size(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 7)
    client = FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "3", batch=True)
    assert [n for _, n, _ in client.batches_created] == [3, 3, 1]
    assert len(json.loads((output_dir / "patient.json").read_text())) == 7


def test_queue_limit_holds_then_splits(judge, monkeypatch, tmp_path):
    """Over the queue limit with a batch in flight: wait for it; alone and
    still over: split in half."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 8)
    client = FakeBatchClient(limit=2, hard_limit=2)
    monkeypatch.setattr(judge._openai_batch, "MIN_SPLIT_REQUESTS", 1)
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "4", batch=True)
    statuses = [(n, s) for _, n, s in client.batches_created]
    assert (4, "failed") in statuses and (2, "in_progress") in statuses
    assert len(json.loads((output_dir / "patient.json").read_text())) == 8
    assert client.chat.completions.create.call_count == 0


def test_requests_a_batch_did_not_answer_go_to_real_time(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = FakeBatchClient(error_ids={"patient|pos_p0_q2"})
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(json.loads((output_dir / "patient.json").read_text())) == 4
    assert client.chat.completions.create.call_count == 1
    usage = json.loads((output_dir / "usage.json").read_text())
    assert usage["per_model"]["gpt-4.1-mini:batch"]["n_calls"] == 3
    assert usage["per_model"]["gpt-4.1-mini"]["n_calls"] == 1


def test_a_large_unanswered_remainder_is_left_for_a_rerun(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = FakeBatchClient(error_ids={"patient|pos_p0_q1", "patient|pos_p0_q2"})
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_fallback_max", "1", batch=True)
    assert e.value.code == 1
    assert len(json.loads((output_dir / "patient.json").read_text())) == 2
    assert client.chat.completions.create.call_count == 0
    # the rerun submits just the two
    client.error_ids = set()
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert client.batches_created[-1][1] == 2
    assert len(json.loads((output_dir / "patient.json").read_text())) == 4


def test_a_restart_collects_the_batch_in_flight_without_resubmitting(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient()
    # A run killed after submitting: the batch is on the service, the state
    # file records it, and its chunk file is still there.
    runner = judge.OpenAIBatchRunner(client, output_dir / "_batches", output_dir / "batch_state.json")
    tpl = judge.resolve_eval_prompt("patient", ROLES, TRAITS, "trait")
    reqs = [(f"patient|{k}", judge.chat_request_body(p, "gpt-4.1-mini", 200))
            for k, p in judge.pending_prompts(_responses(3), tpl, {})]
    [chunk] = runner.write_chunks(reqs)
    asyncio.run(runner._submit(chunk))
    assert len(client.batches_created) == 1

    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(client.batches_created) == 1                       # nothing resubmitted
    assert len(json.loads((output_dir / "patient.json").read_text())) == 3


def test_dry_run_reports_the_batch_plan(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 5)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--traits_dir", str(TRAITS), "--entity_type", "trait", "--no_incongruity_filtering",
        "--dry_run", "--batch_requests", "2"])
    caplog.set_level("INFO")
    asyncio.run(judge.main_async())
    assert "Mode: OpenAI Batch API, about 3 batch(es) of up to 2 requests" in caplog.text


def test_real_time_calls_send_the_shared_request_body(judge):
    client = _client()
    asyncio.run(judge.score_entity(
        name="patient", responses=_responses(1), eval_prompt_template="{question} {answer}",
        client=client, rate_limiter=judge.RateLimiter(1000), judge_model="gpt-4.1-mini",
        max_tokens=200, batch_size=50, existing_scores={}, usage=None))
    assert client.chat.completions.create.call_args.kwargs == judge.chat_request_body(
        "q0 a0", "gpt-4.1-mini", 200)


def test_an_unreadable_score_file_is_reported(judge, tmp_path, caplog):
    """A corrupt score file makes every response of the entity be judged
    again; the reader now says so instead of passing silently."""
    bad = tmp_path / "patient.json"
    bad.write_text('{"pos_p0_q0": 3,')
    with caplog.at_level("WARNING"):
        assert judge.load_scores(bad) == {}
    assert "unreadable" in caplog.text
    assert judge.load_scores(tmp_path / "missing.json") == {}
