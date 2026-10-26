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
import time
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


def test_loading_does_not_import_torch():
    """Torch can take minutes to import on the pod's network mount, and step
    3 has no use for it.  Changed expectation (P8.3, 2026-10-12): the script
    now imports the package itself, whose __init__ is lazy, instead of a
    stand-in package, so ``assistant_axis`` is loaded; torch, matplotlib,
    sklearn, scipy and plotly still are not."""
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('j', {str(SCRIPT)!r})\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "heavy = ('torch', 'matplotlib', 'sklearn', 'scipy', 'plotly')\n"
        "print(sorted(n for n in sys.modules if n.split('.')[0] in heavy)[:5], "
        "'assistant_axis' in sys.modules)\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["[]", "True"]


def test_the_scripts_modules_are_the_packages():
    """No second copy of judge / judge_pricing / openai_batch under a
    stand-in package name any more."""
    code = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('j', {str(SCRIPT)!r})\n"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
        "import assistant_axis.openai_batch as ob\n"
        "print(m.OpenAIBatchRunner is ob.OpenAIBatchRunner, "
        "any(n.startswith('_assistant_axis_standalone') for n in sys.modules))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.split() == ["True", "False"]


class TestJudgeDisplayForm:
    def test_rubric_version(self, judge):
        assert judge.JUDGE_RUBRIC_VERSION == 3        # 2 -> 3: P4, 2026-10-12
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
    assert stamp["rubric_version"] == 3 and stamp["rubric_versions"] == [3]
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
    assert stamp["rubric_versions"] == [1, 3]
    assert "rubric versions [1, 3]" in caplog.text
    # side-cars alone do not count as scores
    fresh = tmp_path / "fresh"; fresh.mkdir()
    (fresh / "usage.json").write_text("{}")
    assert judge.stamp_rubric(fresh, entity_type="trait", judge_model="m")["rubric_versions"] == [3]


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

    def __init__(self, text="Reasoning.\nSCORE: 3", *, limit=None, hard_limit=None, error_ids=(),
                 ensure_ascii=True, corrupt_ids=(), retrieve_failures=0):
        self.text, self.limit, self.hard_limit, self.error_ids = text, limit, hard_limit, set(error_ids)
        # Opt-in failure modes (2026-10-12): output lines written with raw
        # non-ASCII (as a JSON encoder may), result lines cut short, and the
        # first ``retrieve_failures`` status checks raising a network error.
        self.ensure_ascii, self.corrupt_ids = ensure_ascii, set(corrupt_ids)
        self.retrieve_failures = retrieve_failures
        self.uploaded, self.batches_created, self.deleted = {}, [], []
        self.inflight = set()
        self._batches = {}
        self.files = SimpleNamespace(create=self._fcreate, content=self._fcontent, delete=self._fdelete)
        self.batches = SimpleNamespace(create=self._bcreate, retrieve=self._bretrieve, list=self._blist)
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
        self._batches[bid] = {"input": input_file_id, "status": status, "errors": errors,
                              "created_at": int(time.time())}
        self.batches_created.append((bid, n, status))
        if not over:
            self.inflight.add(bid)
        return SimpleNamespace(id=bid, status=status, errors=errors)

    async def _blist(self, limit=20):
        """The organisation's batches, newest first (an async iterator, as the
        SDK's AsyncPaginator)."""
        for bid in reversed(list(self._batches)):
            b = self._batches[bid]
            yield SimpleNamespace(id=bid, status=b["status"], input_file_id=b["input"],
                                  created_at=b["created_at"])

    async def _bretrieve(self, bid):
        if self.retrieve_failures:
            self.retrieve_failures -= 1
            raise ConnectionError("network unreachable")
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
            lines = [json.dumps(o, ensure_ascii=self.ensure_ascii) for o in out]
            lines = [l[: len(l) // 2] if o["custom_id"] in self.corrupt_ids else l
                     for o, l in zip(out, lines)]
            ofid = f"file-out-{bid}"
            self.uploaded[ofid] = "\n".join(lines) + "\n"
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
    assert "temperature" not in body and body["max_completion_tokens"] == 200  # the default (1) is not sent (B1)
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


# ---------------------------------------------------------------------------
# Review of 2026-10-12 (step 3 before the October extraction)
# ---------------------------------------------------------------------------

def _flaky_reads(monkeypatch, target: Path, n_failures):
    """Make the first ``n_failures`` opens of ``target`` for reading raise
    OSError (an NFS hiccup); ``n_failures=None`` makes every one fail.  Both
    ``open`` and ``io.open`` (behind ``Path.read_text``) are wrapped."""
    import builtins
    import io
    real_open = io.open
    left = {"n": n_failures}

    def flaky_open(file, mode="r", *a, **k):
        if "r" in mode and Path(file) == target and (left["n"] is None or left["n"] > 0):
            if left["n"] is not None:
                left["n"] -= 1
            raise OSError(5, "Input/output error")
        return real_open(file, mode, *a, **k)
    monkeypatch.setattr(builtins, "open", flaky_open)
    monkeypatch.setattr(io, "open", flaky_open)


def test_a_transient_read_failure_is_retried_and_never_drops_saved_scores(judge, monkeypatch, tmp_path):
    """merge_scores used to take an unreadable score file as empty and
    overwrite it with the new scores alone, losing the scores (paid for)
    of the earlier batch."""
    monkeypatch.setattr(judge, "SCORE_READ_DELAYS_S", (0, 0), raising=False)
    f = tmp_path / "patient.json"
    f.write_text(json.dumps({"pos_p0_q0": 3}))
    with monkeypatch.context() as m:                        # one hiccup: retried
        _flaky_reads(m, f, 1)
        assert judge.merge_scores(f, {"pos_p0_q1": 2}) == {"pos_p0_q0": 3, "pos_p0_q1": 2}
    with monkeypatch.context() as m:                        # never readable: raise, keep the file
        _flaky_reads(m, f, None)
        with pytest.raises(OSError):
            judge.merge_scores(f, {"pos_p0_q2": 1})
    assert json.loads(f.read_text()) == {"pos_p0_q0": 3, "pos_p0_q1": 2}


@pytest.mark.parametrize("model, reason", [
    ("gpt-9-turbo", "Unknown judge model"),                 # no price: usage would raise after paying
    ("llama-3-70b", "unknown judge model"),
])
def test_an_unusable_judge_model_stops_before_any_request(judge, monkeypatch, tmp_path, caplog, model, reason):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    client = FakeBatchClient()
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--judge_model", model, batch=True)
    assert e.value.code == 1 and reason in caplog.text
    assert client.uploaded == {} and client.chat.completions.create.call_count == 0
    assert judge.check_judge_model("gpt-4.1-mini", batch=True) is None


def test_a_claude_judge_runs_in_real_time(judge, monkeypatch, tmp_path, caplog):
    """A Claude judge (2026-10-26, the judge comparison) runs with --no_batch through an Anthropic
    client: thinking off for Haiku 5.5, usage recorded under its name, a refusal counted as an
    unparseable reply ("refused") and never as a score."""
    from types import SimpleNamespace
    caplog.set_level("INFO")
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    calls = []

    async def create(**kw):
        calls.append(kw)
        if len(calls) == 2:
            return SimpleNamespace(content=[], stop_reason="refusal",
                                   stop_details=SimpleNamespace(category="general_harms"),
                                   usage=SimpleNamespace(input_tokens=300, output_tokens=0))
        return SimpleNamespace(content=[SimpleNamespace(type="text", text="Plays it.\nSCORE: 3")],
                               stop_reason="end_turn", stop_details=None,
                               usage=SimpleNamespace(input_tokens=300, output_tokens=40))
    client = SimpleNamespace(messages=SimpleNamespace(create=create))
    monkeypatch.setattr(judge, "judge_client", lambda model, tier=None: client)
    monkeypatch.setattr(judge._judge_mod, "REFUSED_REPLIES", {})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    with pytest.raises(SystemExit) as e:        # 2 of 3 parsed: under the 99% line, exit 1
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--judge_model", "claude-haiku-5-5")
    assert e.value.code == 1
    assert len(calls) == 3 and all(c["thinking"] == {"type": "disabled"} for c in calls)
    assert all("temperature" not in c for c in calls)
    scores = json.loads((output_dir / "patient.json").read_text())
    assert sorted(scores.values()) == [3, 3]
    usage = json.loads((output_dir / "usage.json").read_text())
    assert set(usage["per_model"]) == {"claude-haiku-5-5"} and usage["n_calls"] == 3
    assert "1 refused" in caplog.text


def test_a_claude_judge_runs_in_batch(judge, monkeypatch, tmp_path, caplog):
    """Batch mode with a Claude judge goes through Anthropic Message Batches (2026-10-26): the request is
    the real-time one (thinking off for Haiku 5.5), results come back under the step-3 ids, usage is
    recorded under <model>:batch, and a refusal or a reply cut at max_tokens is unparseable."""
    from types import SimpleNamespace
    caplog.set_level("INFO")
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    sent = {}

    class Batches:
        async def create(self, requests):
            sent["requests"] = requests
            return SimpleNamespace(id="msgbatch_1", processing_status="in_progress")

        async def retrieve(self, bid):
            return SimpleNamespace(id=bid, processing_status="ended", request_counts=None)

        async def results(self, bid):
            async def gen():
                for i, r in enumerate(sent["requests"]):
                    stop, content = "end_turn", [SimpleNamespace(type="text", text="Plays it.\nSCORE: 3")]
                    if i == 1:
                        stop, content = "refusal", []
                    if i == 2:
                        stop, content = "max_tokens", [SimpleNamespace(type="text", text="Plays it because")]
                    msg = SimpleNamespace(content=content, stop_reason=stop,
                                          usage=SimpleNamespace(input_tokens=300, output_tokens=40))
                    yield SimpleNamespace(custom_id=r["custom_id"], result=SimpleNamespace(type="succeeded", message=msg))
            return gen()

        def list(self, limit=100):
            async def gen():
                return
                yield
            return gen()

    client = SimpleNamespace(messages=SimpleNamespace(batches=Batches()))
    monkeypatch.setattr(judge, "judge_client", lambda model, tier=None: client)
    monkeypatch.setattr(judge._judge_mod, "REFUSED_REPLIES", {})
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    with pytest.raises(SystemExit) as e:        # 2 of 4 parsed: under the 99% line, exit 1
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--judge_model", "claude-haiku-5-5",
             batch=True)
    assert e.value.code == 1
    params = [r["params"] for r in sent["requests"]]
    assert len(params) == 4 and all(p["thinking"] == {"type": "disabled"} for p in params)
    assert all(r["custom_id"].startswith("r") and "|" not in r["custom_id"] for r in sent["requests"])
    assert sorted(json.loads((output_dir / "patient.json").read_text()).values()) == [3, 3]
    usage = json.loads((output_dir / "usage.json").read_text())
    assert set(usage["per_model"]) == {"claude-haiku-5-5:batch"} and usage["n_calls"] == 4
    assert "1 refused" in caplog.text and "1 truncated" in caplog.text


def test_flex_runs_in_real_time_and_is_charged_as_flex(judge, monkeypatch, tmp_path):
    """--service_tier flex (2026-10-26): every request names the tier, usage goes under <model>:flex."""
    from types import SimpleNamespace
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    calls = []

    async def create(**kw):
        calls.append(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Fits.\nSCORE: 3"),
                                                        finish_reason="stop")],
                               usage=SimpleNamespace(prompt_tokens=700, completion_tokens=50))
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    seen = {}

    def fake_client(model, tier=None):
        seen["tier"] = tier
        return client
    monkeypatch.setattr(judge, "judge_client", fake_client)
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--judge_model", "gpt-6-luna", "--service_tier", "flex")
    assert seen["tier"] == "flex"
    assert len(calls) == 3 and all(c["service_tier"] == "flex" and c["reasoning_effort"] == "none" for c in calls)
    usage = json.loads((output_dir / "usage.json").read_text())
    assert set(usage["per_model"]) == {"gpt-6-luna:flex"}


@pytest.mark.parametrize("extra, reason", [
    ((), "pass --no_batch"),
    (("--no_batch", "--judge_model", "claude-haiku-5-5"), "OpenAI's Flex"),
])
def test_flex_is_refused_outside_real_time_openai(judge, monkeypatch, tmp_path, caplog, extra, reason):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 1)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(sys, "argv", ["3_judge.py", "--responses_dir", str(responses_dir), "--output_dir",
                                      str(output_dir), "--roles_dir", str(ROLES), "--traits_dir", str(TRAITS),
                                      "--entity_type", "trait", "--service_tier", "flex", *extra])
    with pytest.raises(SystemExit) as e:
        asyncio.run(judge.main_async())
    assert e.value.code == 1 and reason in caplog.text


def test_flex_client_waits_longer_and_retries_more(judge):
    c = judge.judge_client("gpt-6-luna", "flex")
    assert c.timeout == judge.FLEX_TIMEOUT_S and c.max_retries == judge.FLEX_MAX_RETRIES
    assert judge.judge_client("gpt-6-luna").max_retries != judge.FLEX_MAX_RETRIES


def test_judge_key_and_client_follow_the_provider(judge):
    assert judge.judge_key_name("claude-haiku-5-5") == "ANTHROPIC_API_KEY"
    assert judge.judge_key_name("gpt-6-luna") == "OPENAI_API_KEY"
    assert judge.check_judge_model("claude-haiku-5-5", batch=False) is None
    assert judge.check_judge_model("gpt-6-luna", batch=True) is None
    assert judge.check_judge_model("claude-haiku-5-5", batch=True) is None   # Message Batches
    assert "unknown judge model" in judge.check_judge_model("llama-3-70b", batch=True)


def test_default_corpus_dirs_do_not_depend_on_the_working_directory(judge, monkeypatch, tmp_path, caplog):
    """The defaults were ../data/..., relative to the working directory: run
    from the repository root they found no files and every entity was skipped."""
    responses_dir = tmp_path / "responses"
    _write_responses(responses_dir, "patient", 3)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(tmp_path / "scores"),
        "--entity_type", "trait", "--dry_run"])
    caplog.set_level("INFO")
    asyncio.run(judge.main_async())
    assert "Total prompts: 3" in caplog.text


def test_a_missing_instruction_dir_stops_the_run(judge, monkeypatch, tmp_path, caplog):
    responses_dir = tmp_path / "responses"
    _write_responses(responses_dir, "patient", 1)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(tmp_path / "scores"),
        "--entity_type", "trait", "--traits_dir", str(tmp_path / "nowhere"), "--dry_run"])
    with pytest.raises(SystemExit) as e:
        asyncio.run(judge.main_async())
    assert e.value.code == 1 and "nowhere" in caplog.text


def test_a_missing_combination_scores_file_is_reported(judge, monkeypatch, tmp_path, caplog):
    responses_dir = tmp_path / "responses"
    responses_dir.mkdir()
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(tmp_path / "scores"),
        "--entity_type", "combination", "--combination_scores", str(tmp_path / "none.json"), "--dry_run"])
    asyncio.run(judge.main_async())
    assert "no incongruity filtering" in caplog.text


def test_a_repeated_response_key_is_sent_once(judge, monkeypatch, tmp_path):
    """Two responses with one key made two requests with one custom_id,
    which fails the whole batch at validation, on every rerun."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    rows = _responses(3)
    later = json.loads(json.dumps(rows[1]))
    later["conversation"][-1]["content"] = "the later answer"
    _write_responses(responses_dir, "patient", 0)
    with open(responses_dir / "patient.jsonl", "w") as f:
        for r in rows + [later]:
            f.write(json.dumps(r) + "\n")
    client = FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    lines = client._lines("file-0")
    ids = [l["custom_id"] for l in lines]
    assert sorted(ids) == sorted(set(ids)) and len(ids) == 3
    [q1] = [l for l in lines if l["custom_id"] == "patient|pos_p0_q1"]
    assert "the later answer" in q1["body"]["messages"][0]["content"]     # the later one, as step 2 keeps


def test_a_failed_status_check_is_tried_again_at_the_next_poll(judge, monkeypatch, tmp_path):
    """One failed status check used to end the run during a wait of hours."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient(retrieve_failures=2)
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(json.loads((output_dir / "patient.json").read_text())) == 3
    assert len(client.batches_created) == 1


def test_polling_gives_up_after_the_limit_and_the_batch_stays_recorded(judge, tmp_path):
    client = FakeBatchClient(retrieve_failures=10**6)
    runner = judge.OpenAIBatchRunner(client, tmp_path / "_batches", tmp_path / "batch_state.json",
                                     poll_seconds=0, max_failed_poll_rounds=3)
    [chunk] = runner.write_chunks([("patient|pos_p0_q0", judge.chat_request_body("p", "gpt-4.1-mini", 200))])
    with pytest.raises(ConnectionError):
        asyncio.run(runner.run([chunk], lambda *a: None))
    state = json.loads((tmp_path / "batch_state.json").read_text())
    assert [(bool(r.get("batch_id")), r.get("collected")) for r in state["chunks"]] == [(True, None)]


def test_result_lines_are_split_at_newlines_only_and_a_broken_one_is_unanswered(judge, monkeypatch, tmp_path):
    """str.splitlines() broke a result line at an unescaped U+2028 and the
    JSON error stopped every collection of the batch; a line that does not
    parse now leaves its request unanswered (here: judged in real time)."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient(text="It fits the trait\u0085well.\nSCORE: 3", ensure_ascii=False,
                             corrupt_ids={"patient|pos_p0_q2"})
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert json.loads((output_dir / "patient.json").read_text()) == {f"pos_p0_q{q}": 3 for q in range(3)}
    assert client.chat.completions.create.call_count == 1


def test_a_batch_that_fails_validation_has_its_upload_deleted(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 8)
    client = FakeBatchClient(limit=2, hard_limit=2)
    monkeypatch.setattr(judge._openai_batch, "MIN_SPLIT_REQUESTS", 1)
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "4", batch=True)
    failed_inputs = {client._batches[bid]["input"] for bid, _, s in client.batches_created if s == "failed"}
    assert failed_inputs and failed_inputs <= set(client.deleted)


# -- coordinator's items (end-to-end review, 2026-10-12) ---------------------

def _uploads(client):
    return [f for f in client.uploaded if not f.startswith("file-out")]


def test_a_held_chunk_is_resubmitted_from_the_same_upload(judge, monkeypatch, tmp_path):
    """A chunk the queue limit refused was uploaded again at every retry,
    and the rejected uploads were left on the service."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 6)
    client = FakeBatchClient(limit=2)        # over 2 requests is refused while another is in flight
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "3", batch=True)
    assert [s for _, _, s in client.batches_created] == ["in_progress", "failed", "in_progress"]
    assert len(_uploads(client)) == 2                    # two chunks, two uploads
    held_input = client._batches["batch-1"]["input"]
    assert client._batches["batch-2"]["input"] == held_input
    assert set(_uploads(client)) <= set(client.deleted)  # all tidied once collected
    assert len(json.loads((output_dir / "patient.json").read_text())) == 6


def _crash_after_create(judge, client, output_dir, n):
    """A run stopped between batches.create and the state write: the upload
    is recorded, the batch exists on the service, the state does not know it."""
    runner = judge.OpenAIBatchRunner(client, output_dir / "_batches", output_dir / "batch_state.json")
    tpl = judge.resolve_eval_prompt("patient", ROLES, TRAITS, "trait")
    reqs = [(f"patient|{k}", judge.chat_request_body(p, "gpt-4.1-mini", 200))
            for k, p in judge.pending_prompts(_responses(n), tpl, {})]
    [chunk] = runner.write_chunks(reqs)
    rec = runner._record(chunk)
    uploaded = asyncio.run(client.files.create(file=(chunk.name, chunk.read_bytes()), purpose="batch"))
    rec.update(input_file_id=uploaded.id, uploaded_ts=time.time())
    runner._save_state()
    return uploaded.id


def test_a_restart_collects_a_batch_whose_creation_was_not_recorded(judge, monkeypatch, tmp_path):
    """Known since review 7: the requests of such a batch were submitted
    again on restart and billed twice."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient()
    fid = _crash_after_create(judge, client, output_dir, 3)
    asyncio.run(client.batches.create(input_file_id=fid, endpoint="/v1/chat/completions",
                                      completion_window="24h", metadata={}))
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(client.batches_created) == 1                       # nothing submitted again
    assert len(json.loads((output_dir / "patient.json").read_text())) == 3


def test_a_restart_drops_an_upload_that_has_no_batch(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient()
    fid = _crash_after_create(judge, client, output_dir, 3)       # stopped before create
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert fid in client.deleted
    assert [n for _, n, _ in client.batches_created] == [3]
    assert len(json.loads((output_dir / "patient.json").read_text())) == 3


def test_no_batch_refuses_while_batches_are_uncollected(judge, monkeypatch, tmp_path, caplog):
    """--no_batch used to judge live what earlier batches were still
    answering: paid twice, batches never collected."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient()
    runner = judge.OpenAIBatchRunner(client, output_dir / "_batches", output_dir / "batch_state.json")
    [chunk] = runner.write_chunks([("patient|pos_p0_q0", judge.chat_request_body("p", "gpt-4.1-mini", 200))])
    asyncio.run(runner._submit(chunk))
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client)          # --no_batch
    assert e.value.code == 1 and "not collected" in caplog.text
    assert client.chat.completions.create.call_count == 0


def test_a_bad_entity_fails_alone_and_the_run_exits_1(judge, monkeypatch, tmp_path, caplog):
    """A record missing a field (or a template that does not format) raised
    inside the batch writer and stopped the whole run."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    bad = _responses(2)
    del bad[1]["conversation"]
    with open(responses_dir / "stoic.jsonl", "w") as f:
        for r in bad:
            f.write(json.dumps(r) + "\n")
    client = FakeBatchClient()
    caplog.set_level("INFO")
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert e.value.code == 1 and "stoic: KeyError" in caplog.text
    assert len(json.loads((output_dir / "patient.json").read_text())) == 2   # the rest judged
    assert not (output_dir / "stoic.json").exists()


def test_a_high_fail_rate_exits_1(judge, monkeypatch, tmp_path):
    """A parse rate under 99% exited 0, and step 4 ran on thin scores."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, _client(text="I cannot say."))
    assert e.value.code == 1
    assert json.loads((output_dir / "patient.json").read_text()) == {}       # what was written stays


def test_a_run_that_judges_nothing_writes_no_rubric_stamp(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    output_dir.mkdir()
    (output_dir / "patient.json").write_text(json.dumps({"pos_p0_q0": 3, "pos_p0_q1": 3}))
    _run(judge, monkeypatch, responses_dir, output_dir, FakeBatchClient(), batch=True)
    assert not (output_dir / "judge_rubric.json").exists()


def test_braces_in_corpus_text_are_shown_literally(judge, tmp_path):
    (tmp_path / "curly.json").write_text(json.dumps(
        {"positive_label": "curly {x}", "description": "Uses {braces} and }odd{ ones."}))
    tpl = judge.resolve_eval_prompt("curly", tmp_path, tmp_path, "trait")
    [(key, prompt)] = judge.pending_prompts(_responses(1), tpl, {})
    assert "**curly {x}**. Uses {braces} and }odd{ ones." in prompt and "a0" in prompt


def test_responses_are_read_as_step_2_reads_them(judge, tmp_path, caplog):
    """A malformed line is skipped with a warning (step 2's reader), not
    fatal to the run."""
    p = tmp_path / "patient.jsonl"
    p.write_text(json.dumps(_responses(1)[0]) + "\n{broken\n")
    assert len(judge.load_responses(p)) == 1 and "malformed" in caplog.text


def test_a_combination_with_every_variant_excluded_is_skipped_not_failed(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "r_chef__patient", 2)                  # prompt_index 0 only
    combos = tmp_path / "combination_scores.json"
    # pairs_sha256 of the repository's chef and patient files (checked since
    # P4, 2026-10-12; the fixture had no hash before)
    sha = judge.combination_pairs_sha256("chef", "patient", ROLES, TRAITS)
    combos.write_text(json.dumps({"scores": [{"output_name": "r_chef__patient", "pairs_sha256": sha,
                                              "per_pair": [{"score": 3}] + [{"score": 0}] * 4}]}))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    client = FakeBatchClient()
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--entity_type", "combination", "--combination_scores", str(combos),
        "--batch_poll_seconds", "0"])
    asyncio.run(judge.main_async())                                         # no SystemExit
    assert client.batches_created == []


# ---------------------------------------------------------------------------
# One run per scores directory; model drift; a refused request (P5, 2026-10-12)
# ---------------------------------------------------------------------------

import os
import socket


def _dead_pid() -> int:
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


def _write_lock(output_dir, **payload):
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".3_judge.lock").write_text(json.dumps(payload))


def test_the_lock_is_taken_and_released(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    seen = []
    real = judge.ScoresDirLock.acquire

    def spy(self):
        real(self)
        seen.append(json.loads(self.path.read_text()))

    monkeypatch.setattr(judge.ScoresDirLock, "acquire", spy)
    _run(judge, monkeypatch, responses_dir, output_dir, FakeBatchClient(), batch=True)
    assert seen and seen[0]["pid"] == os.getpid() and seen[0]["host"] == socket.gethostname()
    assert not (output_dir / ".3_judge.lock").exists()


def test_a_live_lock_refuses_the_run_until_force_unlock(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    _write_lock(output_dir, pid=os.getpid(), host=socket.gethostname(), started_at="t0")
    client = FakeBatchClient()
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert e.value.code == 1 and client.batches_created == []
    assert "held by another step-3 run" in caplog.text
    assert (output_dir / ".3_judge.lock").exists()          # not ours to remove
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--force_unlock", batch=True)
    assert len(client.batches_created) == 1
    assert not (output_dir / ".3_judge.lock").exists()


def test_a_lock_from_another_host_needs_force_unlock(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    _write_lock(output_dir, pid=_dead_pid(), host="pod-elsewhere", started_at="t0")
    with pytest.raises(SystemExit):
        _run(judge, monkeypatch, responses_dir, output_dir, FakeBatchClient(), "--no_batch")


def test_a_lock_left_by_a_dead_run_on_this_host_is_removed(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    _write_lock(output_dir, pid=_dead_pid(), host=socket.gethostname(), started_at="t0")
    client = FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert len(client.batches_created) == 1
    assert "not running any more" in caplog.text


def test_release_leaves_a_lock_that_is_not_its_own(judge, tmp_path):
    lock = judge.ScoresDirLock(tmp_path)
    lock.acquire()
    (tmp_path / ".3_judge.lock").write_text(json.dumps({"pid": 1, "host": "other"}))
    lock.release()
    assert (tmp_path / ".3_judge.lock").exists()


def test_batches_in_flight_for_another_model_refuse_the_resume(judge, monkeypatch, tmp_path, caplog):
    """Collected under the new --judge_model, they would be charged and mixed
    as that model's (review P3 D4)."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = FakeBatchClient()
    runner = judge.OpenAIBatchRunner(client, output_dir / "_batches", output_dir / "batch_state.json")
    tpl = judge.resolve_eval_prompt("patient", ROLES, TRAITS, "trait")
    reqs = [(f"patient|{k}", judge.chat_request_body(p, "gpt-4.1-nano", 200))
            for k, p in judge.pending_prompts(_responses(3), tpl, {})]
    [chunk] = runner.write_chunks(reqs)
    asyncio.run(runner._submit(chunk))
    assert runner.inflight_models() == {"gpt-4.1-nano": [chunk.name]}
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, batch=True)
    assert e.value.code == 1
    assert "gpt-4.1-nano" in caplog.text and "not --judge_model gpt-4.1-mini" in caplog.text
    assert len(client.batches_created) == 1                     # nothing new submitted
    assert not (output_dir / "patient.json").exists()           # nothing collected
    assert not (output_dir / ".3_judge.lock").exists()


def test_a_refused_request_stops_a_real_time_run(judge, monkeypatch, tmp_path, caplog):
    """B1 (8bf84f14): an HTTP 400 is a JudgeRequestError; every later entity
    would be refused the same way, so the run stops and exits 1."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    _write_responses(responses_dir, "stoic", 2)
    calls = []

    async def refused(**kw):
        calls.append(kw["prompts"])
        raise judge.JudgeRequestError("400: unsupported parameter")

    monkeypatch.setattr(judge, "call_judge_batch", refused)
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, _client())
    assert e.value.code == 1 and len(calls) == 1               # the second entity not tried
    assert "refused a request" in caplog.text


# ---------------------------------------------------------------------------
# Several runs on one key (walk-through P1, 2026-10-12)
# ---------------------------------------------------------------------------

class SharedQueueClient(FakeBatchClient):
    """Another pod's batch is in the organisation's queue (created directly
    on the fake, unknown to this run's runner); it finishes after this run
    has read the batch list ``finish_after`` times."""

    def __init__(self, *a, finish_after=2, **kw):
        super().__init__(*a, **kw)
        self.lists = 0
        self.finish_after = finish_after
        self.uploaded["file-other"] = "\n".join(
            json.dumps({"custom_id": f"other|k{i}", "body": {}}) for i in range(3)) + "\n"
        asyncio.run(self._bcreate("file-other", "/v1/chat/completions", "24h", {}))
        self.other = self.batches_created[-1][0]

    async def _blist(self, limit=20):
        self.lists += 1
        if self.lists >= self.finish_after and self.other in self.inflight:
            self._batches[self.other]["status"] = "completed"
            self.inflight.discard(self.other)
        async for b in super()._blist(limit):
            yield b


def test_a_full_queue_of_other_runs_is_waited_for_not_split(judge, monkeypatch, tmp_path, caplog):
    """Before: refused with nothing of its own in flight, a run split its
    chunk in half, down to 50 requests, then stopped, although only other
    pods' batches filled the queue."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = SharedQueueClient(limit=2, finish_after=2)
    monkeypatch.setattr(judge._openai_batch, "MIN_SPLIT_REQUESTS", 1)
    with caplog.at_level("INFO"):
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "4", batch=True)
    ours = [(n, s) for b, n, s in client.batches_created if b != client.other]
    assert ours[0] == (4, "failed") and (4, "in_progress") in ours      # resent whole, not split
    assert all(n == 4 for n, _ in ours)
    assert "batch(es) of other runs are queued" in caplog.text
    assert len(json.loads((output_dir / "patient.json").read_text())) == 4
    # the retry reused the upload: one upload of ours
    assert len([f for f in client.uploaded if f.startswith("file-") and f[5:].isdigit()]) == 1


def test_with_no_other_batch_queued_an_oversized_chunk_is_still_split(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = FakeBatchClient(limit=2, hard_limit=2)
    monkeypatch.setattr(judge._openai_batch, "MIN_SPLIT_REQUESTS", 1)
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--batch_requests", "4", batch=True)
    assert [n for _, n, s in client.batches_created if s == "in_progress"] == [2, 2]



# ---------------------------------------------------------------------------
# Rubric v3: how a reply is read; --min_parse_rate; pairs_sha256 (P4, 2026-10-12)
# ---------------------------------------------------------------------------

def test_score_reply_reads_exactly_one_marker(judge):
    judge.REPLY_PROBLEMS.clear()
    assert judge.score_reply("Fits.\nSCORE: 3") == 3
    assert judge.score_reply("It lists 3 examples of the trait and then") is None
    assert judge.score_reply("SCORE: 2 ... no, SCORE: 3") is None
    assert judge.score_reply("SCORE: 7") is None
    assert judge.score_reply("Fine.\nSCORE: 3", "length") is None      # cut at max_tokens
    assert judge.score_reply(None) is None
    assert dict(judge.REPLY_PROBLEMS) == {"no_marker": 1, "several_markers": 1,
                                          "out_of_range": 1, "truncated": 1, "no_reply": 1}


def test_batch_replies_without_a_marker_or_truncated_are_unparseable(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)

    class Mixed(FakeBatchClient):
        async def _bretrieve(self, bid):
            b = await super()._bretrieve(bid)
            out = self.uploaded[b.output_file_id].splitlines()
            fixed = []
            for i, line in enumerate(out):
                o = json.loads(line)
                choice = o["response"]["body"]["choices"][0]
                if i == 1:
                    choice["message"]["content"] = "The reply lists 3 examples"   # no marker
                if i == 2:
                    choice["finish_reason"] = "length"                          # truncated
                fixed.append(json.dumps(o))
            self.uploaded[b.output_file_id] = "\n".join(fixed) + "\n"
            return b

    with caplog.at_level("INFO"):
        with pytest.raises(SystemExit) as e:          # 2 of 4 parsed: under 99%
            _run(judge, monkeypatch, responses_dir, output_dir, Mixed(), batch=True)
    assert e.value.code == 1
    assert sorted(json.loads((output_dir / "patient.json").read_text())) == ["pos_p0_q0", "pos_p0_q3"]
    assert "1 no marker" in caplog.text and "1 truncated" in caplog.text
    assert "--min_parse_rate 99%" in caplog.text


def test_min_parse_rate_sets_the_run_level_stop(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 4)
    client = FakeBatchClient(error_ids={"patient|pos_p0_q1"})
    client.chat = _client(text="no marker here").chat       # the fallback's reply is unparseable
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--min_parse_rate", "0.7",
         batch=True)                                         # 3 of 4 is enough at 0.7
    with pytest.raises(SystemExit):
        _run(judge, monkeypatch, responses_dir, tmp_path / "scores2", FakeBatchClient(
            error_ids={"patient|pos_p0_q1"}), "--min_parse_rate", "1.5", batch=True)


def test_a_real_time_reply_cut_at_max_tokens_is_counted(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    client = _client()
    resp = client.chat.completions.create.return_value
    resp.choices[0].finish_reason = "length"
    with caplog.at_level("INFO"):
        with pytest.raises(SystemExit):
            _run(judge, monkeypatch, responses_dir, output_dir, client)
    assert "2 truncated" in caplog.text and "no reply" not in caplog.text


def test_pairs_sha256_matches_score_combinations(judge):
    """The two computations must agree (score_combinations.py writes the
    recorded value, step 3 recomputes it)."""
    sys.path.insert(0, str(REPO / "data_analysis"))
    import score_combinations as sc
    for role, trait in (("chef", "patient"), ("devils_advocate", "careless_hexaco")):
        if not (ROLES / f"{role}.json").exists() or not (TRAITS / f"{trait}.json").exists():
            continue
        combo = sc._make_combo(role, json.loads((ROLES / f"{role}.json").read_text()), trait,
                               json.loads((TRAITS / f"{trait}.json").read_text()), "role")
        assert judge.combination_pairs_sha256(role, trait, ROLES, TRAITS) == combo["pairs_sha256"]


def test_a_stale_combination_score_stops_the_run(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "r_chef__patient", 2)
    _write_responses(responses_dir, "r_chef__stoic", 2)
    combos = tmp_path / "combination_scores.json"
    combos.write_text(json.dumps({"scores": [
        {"output_name": "r_chef__patient", "pairs_sha256": "0123456789abcdef",   # stale
         "per_pair": [{"score": 0}] * 5}]}))
    client = FakeBatchClient()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-used")
    monkeypatch.setattr(judge.openai, "AsyncOpenAI", lambda: client)
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--entity_type", "combination", "--combination_scores", str(combos)])
    with pytest.raises(SystemExit) as e:
        asyncio.run(judge.main_async())
    assert e.value.code == 1 and client.batches_created == []
    assert "r_chef__patient" in caplog.text and "pairs_sha256" in caplog.text
    assert "r_chef__stoic" in caplog.text                     # unlisted: a warning


# ---------------------------------------------------------------------------
# Prompt versions (--prompt_version, 2026-10-23)
# ---------------------------------------------------------------------------

def _load_module(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _role_stems():
    return [p.stem for p in sorted(ROLES.glob("*.json")) if p.stem != "default"]


def test_version_3_sends_every_role_files_baked_eval_prompt(judge):
    """Until 2026-10-23 step 3 sent the eval_prompt baked into the role file;
    it now renders the template, and version 3's rendering must be that text
    for every role (the generator bakes the same template, so a role whose
    description is edited without rebuilding its eval_prompt fails here)."""
    differ = [s for s in _role_stems()
              if judge.resolve_eval_prompt(s, ROLES, TRAITS, "role", prompt_version=3)
              != json.loads((ROLES / f"{s}.json").read_text())["eval_prompt"]]
    assert differ == []


def test_version_4_role_prompt_is_the_experiments_approved_arms(judge):
    """Version 4 is arm A1 of the role rubric experiment for every role, and arm
    A11 (A1 and the philanthropist example) for altruist alone, as Roger approved
    them on the prompts that experiment judged (2026-10-23)."""
    rre = _load_module("_role_rubric_experiment_under_test", "data_analysis/role_rubric_experiment.py")
    differ = []
    for s in _role_stems():
        baked = json.loads((ROLES / f"{s}.json").read_text())["eval_prompt"]
        arm = "A11" if s == "altruist" else "A1"
        if judge.resolve_eval_prompt(s, ROLES, TRAITS, "role", prompt_version=4) != rre.arm_template(arm, baked):
            differ.append(s)
    assert differ == []


def test_version_0_prompts_ask_for_the_number_alone(judge):
    role = judge.resolve_eval_prompt("altruist", ROLES, TRAITS, "role", prompt_version=0)
    assert role.endswith("Don't say anything else, just the number. "
                         "Don't say anything else, just the number.")
    trait = judge.resolve_eval_prompt("patient", ROLES, TRAITS, "trait", prompt_version=0)
    assert trait.endswith("Respond with a number between 0 and 3. Don't say anything else, just the number.")
    combo = judge.resolve_eval_prompt("r_devils_advocate__systems_thinker", ROLES, TRAITS,
                                      "combination", prompt_version=0)
    assert "**devil's advocate**" in combo and combo.endswith("just the number.")


@pytest.mark.parametrize("text,finish,score,problem", [
    ("2", None, 2, None),
    ("3", "length", 3, None),                 # version 0 reads a cut reply like any other
    ("Score: 1", None, 1, None),
    ("4", None, None, "out_of_range"),
    ("I cannot rate this.", None, None, "no_integer"),
    ("", None, None, "no_reply"),
])
def test_version_0_reading(judge, text, finish, score, problem):
    judge.REPLY_PROBLEMS.clear()
    assert judge.score_reply(text, finish, reply_format="first_integer") == score
    assert dict(judge.REPLY_PROBLEMS) == ({problem: 1} if problem else {})


def test_version_3_reading_is_unchanged(judge):
    judge.REPLY_PROBLEMS.clear()
    assert judge.score_reply("Reason.\nSCORE: 2") == 2
    assert judge.score_reply("Reason.\nSCORE: 2", "length") is None
    assert judge.score_reply("2") is None
    assert dict(judge.REPLY_PROBLEMS) == {"truncated": 1, "no_marker": 1}


def test_a_version_0_run_sends_the_original_request_and_stamps_it(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 3)
    client = _client(text="2")
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--prompt_version", "0")
    assert json.loads((output_dir / "patient.json").read_text()) == {f"pos_p0_q{q}": 2 for q in range(3)}
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["max_completion_tokens"] == 10                        # the fork's default
    assert kwargs["messages"][0]["content"].endswith("just the number.")
    stamp = json.loads((output_dir / "judge_rubric.json").read_text())
    assert stamp["rubric_version"] == 0 and stamp["rubric_versions"] == [0]
    assert stamp["prompt_sha256"] == {"0": judge.PROMPT_VERSIONS[0].sha256("trait")}
    assert stamp["reply_format"] == "first_integer"


def test_max_tokens_given_overrides_the_versions_default(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 1)
    client = _client(text="2")
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--prompt_version", "0",
         "--max_tokens", "50")
    assert client.chat.completions.create.call_args.kwargs["max_completion_tokens"] == 50


def test_a_version_4_batch_run_records_its_hash(judge, monkeypatch, tmp_path):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores_v4"
    _write_responses(responses_dir, "patient", 2)
    client = FakeBatchClient()
    _run(judge, monkeypatch, responses_dir, output_dir, client, "--prompt_version", "4", batch=True)
    assert len(json.loads((output_dir / "patient.json").read_text())) == 2
    stamp = json.loads((output_dir / "judge_rubric.json").read_text())
    assert stamp["rubric_versions"] == [4]
    assert stamp["prompt_sha256"] == {"4": judge.PROMPT_VERSIONS[4].sha256("trait")}


def test_a_directory_of_another_version_is_refused(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    _run(judge, monkeypatch, responses_dir, output_dir, _client(text="2"), "--prompt_version", "0")
    _write_responses(responses_dir, "patient", 4)                    # two more to judge
    client = _client()
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client)  # the default, version 3
    assert e.value.code == 1 and client.chat.completions.create.call_count == 0
    assert "judged under prompt version(s) 0, not 3" in caplog.text


def test_a_changed_draft_is_refused(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores_v4"
    _write_responses(responses_dir, "patient", 2)
    output_dir.mkdir()
    (output_dir / "judge_rubric.json").write_text(json.dumps(
        {"rubric_version": 4, "rubric_versions": [4], "prompt_sha256": {"4": "0123456789abcdef"}}))
    client = _client()
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, responses_dir, output_dir, client, "--prompt_version", "4")
    assert e.value.code == 1 and client.chat.completions.create.call_count == 0
    assert "another text of prompt version 4" in caplog.text


def test_old_versions_1_to_3_may_still_mix(judge, tmp_path):
    """Versions 1-3 send the same text and differ in how a reply was read:
    a directory of unstamped (version 1) scores takes version 3 with the old
    warning, as before 2026-10-23, but not version 0 or 4."""
    (tmp_path / "patient.json").write_text(json.dumps({"pos_p0_q0": 3}))
    assert judge.prompt_version_conflict(tmp_path, 3, "trait") is None
    assert "version(s) 1, not 4" in judge.prompt_version_conflict(tmp_path, 4, "trait")
    assert "version(s) 1, not 0" in judge.prompt_version_conflict(tmp_path, 0, "trait")
    (tmp_path / "judge_rubric.json").write_text(json.dumps({"rubric_versions": [2, 3]}))
    assert judge.prompt_version_conflict(tmp_path, 3, "trait") is None   # no hash recorded: accepted
    assert judge.prompt_version_conflict(tmp_path / "empty", 0, "trait") is None


def test_the_hash_checked_is_the_judged_types_own(judge, tmp_path):
    """A roles directory judged under the draft records the draft's role
    rubric hash: an edit to the draft's trait rubric must not stop it, and an
    edit to its role rubric must."""
    v4 = judge.PROMPT_VERSIONS[4]
    stamp = judge.stamp_rubric(tmp_path, entity_type="role", judge_model="gpt-4.1-mini", prompt_version=4)
    assert stamp["prompt_sha256"] == {"4": v4.sha256("role")} and v4.sha256("role") != v4.sha256("trait")
    assert judge.prompt_version_conflict(tmp_path, 4, "role") is None
    (tmp_path / "judge_rubric.json").write_text(json.dumps({**stamp, "prompt_sha256": {"4": "0" * 16}}))
    assert "another text of prompt version 4" in judge.prompt_version_conflict(tmp_path, 4, "role")


def test_a_batch_run_stamps_its_version_before_collecting(judge, monkeypatch, tmp_path):
    """A run stopped after submitting has recorded the version its batches
    were requested under, so a rerun under another version is refused rather
    than reading their replies by its own rule."""
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)

    async def stop(self, *a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(judge.OpenAIBatchRunner, "run", stop)
    with pytest.raises(KeyboardInterrupt):
        _run(judge, monkeypatch, responses_dir, output_dir, FakeBatchClient(), "--prompt_version", "0",
             batch=True)
    assert json.loads((output_dir / "judge_rubric.json").read_text())["rubric_versions"] == [0]
    assert "version(s) 0, not 3" in judge.prompt_version_conflict(output_dir, 3, "trait")


@pytest.mark.parametrize("value,message", [("1", "not runnable"), ("9", "no prompt version 9")])
def test_unrunnable_versions_are_refused_at_the_command_line(judge, monkeypatch, tmp_path, capsys,
                                                             value, message):
    with pytest.raises(SystemExit) as e:
        _run(judge, monkeypatch, tmp_path, tmp_path / "scores", _client(), "--prompt_version", value)
    assert e.value.code == 2 and message in capsys.readouterr().err


def test_dry_run_names_the_version_and_a_conflict(judge, monkeypatch, tmp_path, caplog):
    responses_dir, output_dir = tmp_path / "responses", tmp_path / "scores"
    _write_responses(responses_dir, "patient", 2)
    output_dir.mkdir()
    (output_dir / "judge_rubric.json").write_text(json.dumps({"rubric_versions": [0]}))
    monkeypatch.setattr(sys, "argv", [
        "3_judge.py", "--responses_dir", str(responses_dir), "--output_dir", str(output_dir),
        "--traits_dir", str(TRAITS), "--entity_type", "trait", "--no_incongruity_filtering",
        "--dry_run", "--prompt_version", "4"])
    caplog.set_level("INFO")
    asyncio.run(judge.main_async())
    assert "Prompt version 4 (draft)" in caplog.text and "--max_tokens 200" in caplog.text
    assert "A live run would stop" in caplog.text
