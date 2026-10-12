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
    ("claude-haiku-4-5-20251001", "OpenAI only"),          # step 3 calls OpenAI only
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
    combos.write_text(json.dumps({"scores": [{"output_name": "r_chef__patient",
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
