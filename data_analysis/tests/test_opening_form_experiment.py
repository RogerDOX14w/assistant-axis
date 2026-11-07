"""Tests for data_analysis/opening_form_experiment.py (no API calls, no key needed)."""
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from data_analysis import opening_form_experiment as exp  # noqa: E402

PLAN = {"n_questions": 3, "traits": {"petty": {
    "label": "petty", "description": "This means making much of small wrongs.",
    "variants": [{"name": "tendency", "text": "You have a tendency to nurse grievances."},
                 {"name": "be_someone", "text": "Be someone who nurses grievances."}]}}}


@pytest.fixture
def out_dir(tmp_path):
    (tmp_path / "plan.json").write_text(json.dumps(PLAN))
    return tmp_path


def _completion(text, reasoning=None, provider="SomeHost"):
    msg = SimpleNamespace(content=text, reasoning=reasoning)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason="stop")], provider=provider,
                           usage=SimpleNamespace(prompt_tokens=40, completion_tokens=200))


class TestSettings:
    def test_they_are_the_extraction_runs(self):
        assert exp.TEMPERATURE == 0.7 and exp.MAX_TOKENS == 512
        assert exp.DEFAULT_MODEL == "qwen/qwen3-32b" and exp.DEFAULT_JUDGE == "gpt-4.1-mini"

    def test_the_model_has_a_price(self):
        from assistant_axis.judge_pricing import price_for_model
        assert price_for_model(exp.DEFAULT_MODEL) == (0.08, 0.28)

    def test_only_western_hosts(self):
        # Roger, 2026-09-29: no host based in China or its bloc
        assert exp.ALLOWED_PROVIDERS == ("DeepInfra",) and exp.DEFAULT_PROVIDER in exp.ALLOWED_PROVIDERS
        assert "SiliconFlow" not in exp.ALLOWED_PROVIDERS

    def test_the_judge_prompt_is_the_pipelines(self):
        p = exp.trait_judge_prompt("petty", "This means making much of small wrongs.")
        assert "**petty**. This means making much of small wrongs." in p
        assert "{question}" in p and "{answer}" in p and "SCORE: <integer from 0 to 3>" in p
        assert p.index("First, briefly reason") < p.index("SCORE:")


class TestStripThinking:
    def test_a_whole_block(self):
        assert exp.strip_thinking("<think>\nhm\n</think>\n\nThe answer.") == "The answer."

    def test_an_orphaned_close_tag_as_in_the_extraction_run(self):
        assert exp.strip_thinking("hm, let me see</think>The answer.") == "The answer."

    def test_nothing_to_strip(self):
        assert exp.strip_thinking("  The answer. ") == "The answer."


class TestPlan:
    def test_loads(self, out_dir):
        assert list(exp.load_plan(out_dir)["traits"]) == ["petty"]

    def test_two_variants_with_one_name(self, tmp_path):
        bad = json.loads(json.dumps(PLAN))
        bad["traits"]["petty"]["variants"][1]["name"] = "tendency"
        (tmp_path / "plan.json").write_text(json.dumps(bad))
        with pytest.raises(SystemExit, match="share a name"):
            exp.load_plan(tmp_path)

    def test_the_judge_needs_a_description(self, tmp_path):
        bad = json.loads(json.dumps(PLAN))
        bad["traits"]["petty"]["description"] = ""
        (tmp_path / "plan.json").write_text(json.dumps(bad))
        with pytest.raises(SystemExit, match="description"):
            exp.load_plan(tmp_path)

    def test_questions_are_the_first_of_the_shared_bank(self):
        qs = exp.load_questions(3)
        assert len(qs) == 3 and qs[0] == "What is the relationship between law and morality?"


class TestGenerate:
    def run(self, out_dir, monkeypatch, create, dry_run=False):
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: client)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
        monkeypatch.setattr(exp.asyncio, "sleep", AsyncMock())
        args = SimpleNamespace(model=exp.DEFAULT_MODEL, provider=exp.DEFAULT_PROVIDER, concurrency=4, dry_run=dry_run)
        asyncio.run(exp.generate(args, exp.load_plan(out_dir), out_dir))
        return exp.read_jsonl(out_dir / "responses" / "petty.jsonl")

    def test_every_variant_gets_every_question_with_the_runs_settings(self, out_dir, monkeypatch):
        create = AsyncMock(return_value=_completion("An answer.", provider="DeepInfra"))
        rows = self.run(out_dir, monkeypatch, create)
        assert len(rows) == 6 and {r["variant"] for r in rows} == {"tendency", "be_someone"}
        kw = create.call_args.kwargs
        assert kw["temperature"] == 0.7 and kw["max_tokens"] == 512 and kw["model"] == "qwen/qwen3-32b"
        assert kw["extra_body"] == {"reasoning": {"enabled": False},
                                    "provider": {"order": ["DeepInfra"], "allow_fallbacks": False}}
        assert kw["messages"][0]["role"] == "system" and kw["messages"][1]["role"] == "user"
        assert kw["messages"][1]["content"].endswith("? /no_think")
        r = rows[0]
        assert r["conversation"][-1] == {"role": "assistant", "content": "An answer."}
        assert r["had_thinking"] is False and r["provider"] == "DeepInfra" and r["label"] == "pos"
        assert not r["question"].endswith("/no_think") and r["user_turn"].endswith("/no_think")
        usage = json.loads((out_dir / "usage.json").read_text())
        assert usage["n_calls"] == 6 and "qwen/qwen3-32b" in usage["per_model"]

    def test_a_trait_may_bring_its_own_questions(self, out_dir, monkeypatch):
        plan = json.loads(json.dumps(PLAN))
        plan["traits"]["petty"]["questions"] = ["A neighbor parks across your drive. What do you do?"]
        (out_dir / "plan.json").write_text(json.dumps(plan))
        create = AsyncMock(return_value=_completion("An answer.", provider="DeepInfra"))
        rows = self.run(out_dir, monkeypatch, create)
        assert len(rows) == 2 and {r["question"] for r in rows} == {"A neighbor parks across your drive. What do you do?"}

    def test_a_variant_with_no_text_is_asked_without_a_system_prompt(self, out_dir, monkeypatch):
        plan = json.loads(json.dumps(PLAN))
        plan["traits"]["petty"]["variants"] = [{"name": "no_instruction", "text": ""}]
        (out_dir / "plan.json").write_text(json.dumps(plan))
        create = AsyncMock(return_value=_completion("An answer.", provider="DeepInfra"))
        rows = self.run(out_dir, monkeypatch, create)
        assert [m["role"] for m in create.call_args.kwargs["messages"]] == ["user"]
        assert len(rows) == 3 and [m["role"] for m in rows[0]["conversation"]] == ["user", "assistant"]

    def test_a_second_run_asks_only_for_what_is_missing(self, out_dir, monkeypatch):
        create = AsyncMock(return_value=_completion("An answer.", provider="DeepInfra"))
        self.run(out_dir, monkeypatch, create)
        path = out_dir / "responses" / "petty.jsonl"
        path.write_text("\n".join(path.read_text().splitlines()[:4]) + "\n")
        again = AsyncMock(return_value=_completion("Another.", provider="DeepInfra"))
        rows = self.run(out_dir, monkeypatch, again)
        assert again.call_count == 2 and len(rows) == 6

    def test_a_response_that_came_with_thinking_is_not_kept(self, out_dir, monkeypatch):
        # the extraction run had thinking switched off; one host ignores the request
        for reply in (_completion("An answer.", reasoning="Let me think.", provider="DeepInfra"),
                      _completion("hm</think>An answer.", provider="DeepInfra")):
            assert self.run(out_dir, monkeypatch, AsyncMock(return_value=reply)) == []

    def test_an_empty_thinking_block_is_thinking_switched_off(self, out_dir, monkeypatch):
        # what DeepInfra returns under /no_think; the first version of the check threw every answer away
        for reply in (_completion("An answer.", reasoning="\n\n", provider="DeepInfra"),
                      _completion("<think>\n\n</think>\n\nAn answer.", provider="DeepInfra")):
            rows = self.run(out_dir, monkeypatch, AsyncMock(return_value=reply))
            assert len(rows) == 6 and rows[0]["conversation"][-1]["content"] == "An answer."
            (out_dir / "responses" / "petty.jsonl").unlink()

    def test_a_response_from_another_host_is_not_kept(self, out_dir, monkeypatch):
        reply = _completion("An answer.", provider="SiliconFlow")
        assert self.run(out_dir, monkeypatch, AsyncMock(return_value=reply)) == []

    def test_a_host_off_the_list_is_refused_before_any_call(self, out_dir, monkeypatch):
        create = AsyncMock()
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: client)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
        args = SimpleNamespace(model=exp.DEFAULT_MODEL, provider="SiliconFlow", concurrency=4, dry_run=False)
        with pytest.raises(SystemExit, match="not among the hosts"):
            asyncio.run(exp.generate(args, exp.load_plan(out_dir), out_dir))
        assert create.call_count == 0

    def test_a_dry_run_calls_nothing(self, out_dir, monkeypatch, capsys):
        create = AsyncMock()
        assert self.run(out_dir, monkeypatch, create, dry_run=True) == []
        assert create.call_count == 0 and "6 responses to generate" in capsys.readouterr().err

    def test_the_key_is_never_written(self, out_dir, monkeypatch, capsys):
        self.run(out_dir, monkeypatch, AsyncMock(return_value=_completion("An answer.", provider="DeepInfra")))
        captured = capsys.readouterr()
        written = "".join(p.read_text() for p in out_dir.rglob("*") if p.is_file())
        assert "test-key-not-real" not in written + captured.out + captured.err


class TestCheckpointedUsage:
    """A run that is killed must not lose its usage record (2026-09-30: a run
    stopped from the task list lost 2,443 calls)."""

    def on_file(self, out_dir):
        path = out_dir / "usage.json"
        return json.loads(path.read_text())["n_calls"] if path.exists() else 0

    def test_the_file_is_written_every_so_many_calls(self, out_dir):
        usage = exp.CheckpointedUsage(out_dir, every=3)
        for k in range(7):
            usage.charge("qwen/qwen3-32b", 40, 200)
            assert self.on_file(out_dir) == 3 * ((k + 1) // 3)
        assert usage.n_calls == 7

    def test_close_writes_the_rest_once(self, out_dir):
        usage = exp.CheckpointedUsage(out_dir, every=3)
        for _ in range(7):
            usage.charge("qwen/qwen3-32b", 40, 200)
        usage.close()
        usage.close()
        record = json.loads((out_dir / "usage.json").read_text())
        assert record["n_calls"] == 7 and record["per_model"]["qwen/qwen3-32b"]["completion_tokens"] == 1400

    def test_it_adds_to_what_the_file_already_holds(self, out_dir):
        for _ in range(2):
            usage = exp.CheckpointedUsage(out_dir, every=100)
            usage.charge("gpt-4.1-mini", 500, 60)
            usage.close()
        assert self.on_file(out_dir) == 2

    def test_a_closed_pipe_does_not_stop_the_record(self, out_dir, monkeypatch):
        class Closed:
            def write(self, text):
                raise BrokenPipeError

            def flush(self):
                raise BrokenPipeError

        usage = exp.CheckpointedUsage(out_dir, every=100)
        usage.charge("qwen/qwen3-32b", 40, 200)
        monkeypatch.setattr(exp.sys, "stderr", Closed())
        usage.close()
        assert self.on_file(out_dir) == 1

    def test_a_run_with_no_calls_writes_nothing(self, out_dir):
        exp.CheckpointedUsage(out_dir).close()
        assert not (out_dir / "usage.json").exists()

    def test_a_stopped_generation_keeps_what_it_was_charged(self, out_dir, monkeypatch):
        monkeypatch.setattr(exp, "USAGE_CHECKPOINT_CALLS", 2)
        calls = {"n": 0}

        async def create(**kw):
            calls["n"] += 1
            if calls["n"] == 5:
                raise KeyboardInterrupt
            return _completion("An answer.", provider="DeepInfra")

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: client)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
        args = SimpleNamespace(model=exp.DEFAULT_MODEL, provider=exp.DEFAULT_PROVIDER, concurrency=1, dry_run=False)
        with pytest.raises(KeyboardInterrupt):
            asyncio.run(exp.generate(args, exp.load_plan(out_dir), out_dir))
        assert self.on_file(out_dir) == 4


class TestJudge:
    def test_scores_are_keyed_by_variant_and_question_and_resumed(self, out_dir, monkeypatch):
        (out_dir / "responses").mkdir()
        rows = [{"variant": v, "question_index": q, "question": f"Q{q}?", "provider": "SomeHost",
                 "conversation": [{"role": "assistant", "content": f"answer {v} {q}"}]}
                for v in ("tendency", "be_someone") for q in range(3)]
        (out_dir / "responses" / "petty.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        (out_dir / "scores").mkdir()
        (out_dir / "scores" / "petty.json").write_text(json.dumps({"tendency_q0": 1}))
        seen = []

        async def fake(client, prompt, model, max_tokens, limiter, usage=None):
            seen.append(prompt)
            usage.charge(model, 500, 60)
            return "It shows the trait.\nSCORE: 3" if "be_someone" in prompt else "It answers as itself.\nSCORE: 1"
        monkeypatch.setattr(exp, "call_judge_single", fake)
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: object())
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        args = SimpleNamespace(judge_model="gpt-4.1-mini", requests_per_second=50, dry_run=False, via=None)
        asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))
        scores = json.loads((out_dir / "scores" / "petty.json").read_text())
        assert len(seen) == 5 and len(scores) == 6
        assert scores["be_someone_q2"] == 3 and scores["tendency_q1"] == 1
        assert "**petty**" in seen[0] and "[ANSWER START]" in seen[0]

        rows = exp.tabulate(exp.load_plan(out_dir), out_dir)
        by = {r["variant"]: r for r in rows}
        assert by["be_someone"]["share_3"] == 100 and by["tendency"]["share_3"] == 0 and by["tendency"]["share_1"] == 100
        across = {v["variant"]: v for v in exp.by_variant(rows, "be_someone")}
        assert across["tendency"]["mean_difference"] == -100 and across["tendency"]["traits_below"] == 1
        assert "against" not in across["be_someone"]


class TestJudgeThroughOpenRouter:
    def ask(self, reply):
        create = AsyncMock(return_value=reply)
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        usage = exp.MultiModelUsage()
        text = asyncio.run(exp.judge_through_openrouter(client, "the prompt", "gpt-4.1-mini", exp.RateLimiter(50), usage))
        return text, create, usage

    def test_it_is_the_pipelines_call_pinned_to_openai(self):
        text, create, usage = self.ask(_completion("Reasoning.\nSCORE: 2", provider="OpenAI"))
        kw = create.call_args.kwargs
        assert text.endswith("SCORE: 2") and kw["model"] == "openai/gpt-4.1-mini"
        assert kw["temperature"] == 1 and kw["max_tokens"] == 200
        assert kw["messages"] == [{"role": "user", "content": "the prompt"}]
        assert kw["extra_body"] == {"provider": {"order": ["OpenAI"], "allow_fallbacks": False}}
        assert usage.n_calls == 1 and list(usage.as_dict()["per_model"]) == ["gpt-4.1-mini"]

    def test_an_answer_from_another_host_is_not_used(self):
        text, _, usage = self.ask(_completion("Reasoning.\nSCORE: 2", provider="Azure"))
        assert text is None and usage.n_calls == 1

    def test_without_an_openai_key_the_judge_stops_and_does_not_turn_to_a_router(self, out_dir, monkeypatch):
        # Roger, 2026-09-29: OpenAI, Anthropic and Google models are reached directly
        (out_dir / "responses").mkdir()
        row = {"variant": "tendency", "question_index": 0, "question": "Q?", "provider": "DeepInfra",
               "conversation": [{"role": "assistant", "content": "an answer"}]}
        (out_dir / "responses" / "petty.jsonl").write_text(json.dumps(row) + "\n")
        # the pipeline's judge module loads .env when it is imported, which would bring a key back
        monkeypatch.setattr(exp, "trait_judge_prompt", lambda label, description: "{question} {answer}")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
        made = []
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: made.append(kw))
        args = SimpleNamespace(judge_model="gpt-4.1-mini", requests_per_second=50, dry_run=False, via=None)
        with pytest.raises(SystemExit, match="directly"):
            asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))
        assert made == []

    def test_the_route_is_openrouter_only_on_request(self, out_dir, monkeypatch, capsys):
        (out_dir / "responses").mkdir()
        row = {"variant": "tendency", "question_index": 0, "question": "Q?", "provider": "DeepInfra",
               "conversation": [{"role": "assistant", "content": "an answer"}]}
        (out_dir / "responses" / "petty.jsonl").write_text(json.dumps(row) + "\n")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
        made = {}

        def client(**kw):
            made.update(kw)
            create = AsyncMock(return_value=_completion("Reasoning.\nSCORE: 3", provider="OpenAI"))
            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", client)
        args = SimpleNamespace(judge_model="gpt-4.1-mini", requests_per_second=50, dry_run=False, via="openrouter")
        asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))
        assert made["base_url"] == "https://openrouter.ai/api/v1"
        assert json.loads((out_dir / "scores" / "petty.json").read_text()) == {"tendency_q0": 3}
        assert "test-key-not-real" not in capsys.readouterr().err


class TestWilson:
    def test_interval(self):
        lo, hi = exp.wilson(0, 100)
        assert lo == 0 and 0.03 < hi < 0.04


class TestDepthJudge:
    GOOD = json.dumps({"reason": "Declines to lead the meeting.", "voice": "person", "in_action": True,
                       "describes_itself": False, "caricature": 0})

    def test_the_reason_comes_before_the_verdict(self):
        p = exp.DEPTH_JUDGE_PROMPT
        assert "Write the reason first" in p
        example = p[p.rindex('{{"reason"'):]
        assert example.index('"reason"') < example.index('"voice"') < example.index('"caricature"')

    def test_the_judge_is_not_shown_the_instruction(self):
        assert "{system" not in exp.DEPTH_JUDGE_PROMPT and "instruction" not in exp.DEPTH_JUDGE_PROMPT.lower()
        for field in ("{trait}", "{description}", "{question}", "{answer}"):
            assert field in exp.DEPTH_JUDGE_PROMPT

    def test_parse(self):
        d = exp.parse_depth("Here:\n" + self.GOOD)
        assert d == {"reason": "Declines to lead the meeting.", "voice": "person", "in_action": True,
                     "describes_itself": False, "caricature": 0}

    @pytest.mark.parametrize("change, message", [
        ({"voice": "narrator"}, "voice"), ({"in_action": "yes"}, "in_action"),
        ({"caricature": 3}, "caricature"), ({"caricature": True}, "caricature"),
        ({"describes_itself": None}, "describes_itself"),
    ])
    def test_a_reply_off_the_scale_is_refused(self, change, message):
        d = dict(json.loads(self.GOOD), **change)
        with pytest.raises(ValueError, match=message):
            exp.parse_depth(json.dumps(d))

    def _setup(self, out_dir, monkeypatch, replies):
        (out_dir / "responses").mkdir()
        rows = [{"variant": v, "question_index": q, "question": f"Q{q}?", "provider": "DeepInfra",
                 "conversation": [{"role": "assistant", "content": f"answer under {v} to {q}"}]}
                for v in ("tendency", "be_someone") for q in range(3)]
        (out_dir / "responses" / "petty.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        (out_dir / "scores").mkdir()
        (out_dir / "scores" / "petty.json").write_text(json.dumps(
            {f"{v}_q{q}": (3 if v == "be_someone" else 1) for v in ("tendency", "be_someone") for q in range(3)}))
        create = AsyncMock(side_effect=replies)
        client = SimpleNamespace(messages=SimpleNamespace(create=create))
        monkeypatch.setattr(exp.anthropic, "AsyncAnthropic", lambda **kw: client)
        monkeypatch.setattr(exp.asyncio, "sleep", AsyncMock())
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        return create

    @staticmethod
    def _reply(text):
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                               usage=SimpleNamespace(input_tokens=600, output_tokens=80))

    def test_reads_answers_records_and_resumes(self, out_dir, monkeypatch):
        def reply(**kw):
            shown = kw["messages"][0]["content"]
            assert "You have a tendency" not in shown and "Be someone who" not in shown
            cartoon = "under be_someone" in shown
            return self._reply(json.dumps({"reason": "r", "voice": "person", "in_action": True,
                                           "describes_itself": False, "caricature": 2 if cartoon else 0}))
        create = self._setup(out_dir, monkeypatch, reply)
        args = SimpleNamespace(model="claude-sonnet-4-6", min_score=0, concurrency=2, dry_run=False)
        asyncio.run(exp.depth(args, exp.load_plan(out_dir), out_dir))
        judged = json.loads((out_dir / "depth" / "petty.json").read_text())
        assert len(judged) == 6 and create.call_count == 6
        # version 2 since W19 (2026-10-09); a version-1 reading of a label that
        # renders unchanged stays current, one of a standards label does not
        assert judged["be_someone_q1"]["caricature"] == 2 and judged["be_someone_q1"]["rubric_version"] == 2
        assert exp.depth_is_current({"rubric_version": 1, "model": "m"}, "petty", "m")
        assert not exp.depth_is_current({"rubric_version": 1, "model": "m"}, "careless (HEXACO)", "m")
        assert not exp.depth_is_current({"rubric_version": 2, "model": "other"}, "petty", "m")
        assert create.call_args.kwargs["temperature"] == 0.0
        usage = json.loads((out_dir / "usage.json").read_text())
        assert usage["per_model"]["claude-sonnet-4-6"]["n_calls"] == 6
        asyncio.run(exp.depth(args, exp.load_plan(out_dir), out_dir))
        assert create.call_count == 6  # nothing is read twice

        rows = {r["variant"]: r for r in exp.depth_table(exp.load_plan(out_dir), out_dir, top_only=False)}
        assert rows["be_someone"]["cartoon"] == 100 and rows["tendency"]["cartoon"] == 0
        assert rows["tendency"]["believable_in_action"] == 100 and rows["be_someone"]["believable_in_action"] == 0
        top = exp.depth_table(exp.load_plan(out_dir), out_dir, top_only=True)
        assert [r["variant"] for r in top] == ["be_someone"] and top[0]["n"] == 3

    def test_only_answers_at_or_over_the_score_asked_for(self, out_dir, monkeypatch):
        create = self._setup(out_dir, monkeypatch, lambda **kw: self._reply(self.GOOD))
        args = SimpleNamespace(model="claude-sonnet-4-6", min_score=2, concurrency=2, dry_run=False)
        asyncio.run(exp.depth(args, exp.load_plan(out_dir), out_dir))
        assert create.call_count == 3
        assert set(json.loads((out_dir / "depth" / "petty.json").read_text())) == {f"be_someone_q{q}" for q in range(3)}

    def test_an_unreadable_reply_is_asked_again_with_the_reason(self, out_dir, monkeypatch):
        seen = []

        def reply(**kw):
            seen.append(kw["messages"][0]["content"])
            return self._reply("no verdict" if len(seen) == 1 else self.GOOD)
        self._setup(out_dir, monkeypatch, reply)
        usage, tally = exp.MultiModelUsage(), {"ok": 0, "total": 0}
        client = exp.anthropic.AsyncAnthropic()
        out = asyncio.run(exp.depth_call(client, "claude-sonnet-4-6", "the prompt", asyncio.Semaphore(1), usage, tally))
        assert out["voice"] == "person" and tally == {"ok": 1, "total": 2} and usage.n_calls == 2
        assert "could not be used" not in seen[0] and "Your previous reply could not be used" in seen[1]


class TestArms:
    """A plan from staged directories of trait files, and the paired comparison of arms."""

    def make_arms(self, tmp_path, description_b=None):
        stems = ["petty", "stoic"]
        for code, opening in (("v1", "You are"), ("d10", "Be someone who is")):
            d = tmp_path / code
            d.mkdir()
            for s in stems:
                doc = {"positive_label": s, "negative_label": f"non-{s}", "description": f"This means being {s}.",
                       "instruction": [{"pos": f"{opening} {s}, number {k}.", "neg": "x"} for k in range(5)],
                       "generator": {"style": "RogerV2" if code == "d10" else "Roger", "template_sha256": "abc"}}
                if code == "d10" and s == "stoic" and description_b:
                    doc["description"] = description_b
                (d / f"{s}.json").write_text(json.dumps(doc))
        return stems, [("v1", tmp_path / "v1", None), ("d10", tmp_path / "d10", "RogerV2@abc")]

    def test_a_plan_has_five_variants_an_arm_and_the_shared_questions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_arms(tmp_path)
        plan, left_out = exp.build_arms_plan(arms, stems, 20, kinds={"petty": "bad"}, purpose="test")
        assert left_out == [] and set(plan["traits"]) == {"petty", "stoic"}
        t = plan["traits"]["petty"]
        assert t["kind"] == "bad" and plan["traits"]["stoic"]["kind"] == "unclassified"
        assert [v["name"] for v in t["variants"]] == [f"v1_p{k}" for k in range(5)] + [f"d10_p{k}" for k in range(5)]
        assert t["variants"][5]["form"] == exp_audit_form("Be someone who is petty, number 0.")
        assert t["questions"] == [f"Q{i}?" for i in range(0, 100, 5)] and len(t["questions"]) == 20
        assert plan["arms"]["d10"]["style"] == "RogerV2@abc" and plan["arms"]["d10"]["traits"] == 2

    def test_a_trait_described_differently_between_arms_is_left_out(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_arms(tmp_path, description_b="This means something else.")
        plan, left_out = exp.build_arms_plan(arms, stems, 20)
        assert left_out == ["stoic"] and set(plan["traits"]) == {"petty"}

    def test_adding_an_arm_keeps_the_plan_and_replaces_the_arm(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_arms(tmp_path)
        plan, _ = exp.build_arms_plan(arms[:1], stems, 20, kinds={"petty": "bad"})
        plan["traits"]["petty"]["questions"] = ["kept"]
        plan, _ = exp.build_arms_plan(arms[1:], stems, 20, existing=plan)
        plan, _ = exp.build_arms_plan(arms[1:], stems, 20, existing=plan)   # again: replaced, not doubled
        t = plan["traits"]["petty"]
        assert t["questions"] == ["kept"] and t["kind"] == "bad"
        assert sorted({v["arm"] for v in t["variants"]}) == ["d10", "v1"] and len(t["variants"]) == 10

    def test_n_questions_must_divide_the_hundred(self):
        with pytest.raises(SystemExit):
            exp.arm_questions(30)

    def test_arm_spec(self):
        assert exp.parse_arm_spec("d10=some/dir:RogerV2@abc") == ("d10", Path("some/dir"), "RogerV2@abc")
        assert exp.parse_arm_spec("v1=some/dir") == ("v1", Path("some/dir"), None)
        with pytest.raises(SystemExit):
            exp.parse_arm_spec("nodir")

    def test_report_pairs_arms_over_traits_by_kind(self, out_dir):
        plan = {"traits": {}, "arms": {"v1": {}, "d10": {}}}
        (out_dir / "scores").mkdir()
        for i in range(12):
            stem = f"t{i}"
            plan["traits"][stem] = {"label": stem, "description": "d", "kind": "bad" if i < 6 else "good",
                                    "variants": [{"name": f"{a}_p{k}", "text": "x", "arm": a, "form": "f"}
                                                 for a in ("v1", "d10") for k in range(2)], "questions": ["q"] * 10}
            scores = {}
            for a, share in (("v1", 0.5), ("d10", 0.7 if i < 6 else 0.5)):
                for k in range(2):
                    for q in range(10):
                        scores[f"{a}_p{k}_q{q}"] = 3 if q < share * 10 else 1
            (out_dir / "scores" / f"{stem}.json").write_text(json.dumps(scores))
        (out_dir / "plan.json").write_text(json.dumps(plan))
        report = exp.arms_report(exp.load_plan(out_dir), out_dir, "v1", ["d10"])
        assert report["by_kind"]["all"]["v1"]["mean"] == 50.0 and report["by_kind"]["all"]["d10"]["mean"] == 60.0
        c = report["by_kind"]["bad"]["d10"]["against_baseline"]
        assert c["traits"] == 6 and c["difference"] == 20.0 and c["better"] == 6 and c["p"] < 0.05
        assert report["by_kind"]["good"]["d10"]["against_baseline"]["difference"] == 0.0
        assert report["instructions"]["v1"]["under_50"] == 0.0 and report["instructions"]["v1"]["n"] == 24
        assert report["instructions"]["v1"]["weakest_trait_scored_3_of_500"] == 250.0
        text = exp.render_arms_report(report)
        assert "d10 minus v1: +20.0" in text and "bad          traits   6" in text


def exp_audit_form(text):
    from data_analysis import audit_trait_instructions as audit
    return audit.opening_form(text)


class TestRoleArms:
    """Role mode (2026-10-02): a plan from staged role files, judged with each file's own eval_prompt."""

    def make_role_arms(self, tmp_path):
        from data_analysis.regenerate_role_instructions import build_eval_prompt
        stems = ["coral_reef", "devils_advocate"]
        d = tmp_path / "r0"
        d.mkdir()
        for s in stems:
            name = s.replace("_", " ")
            doc = {"description": f"A {name} is something.", "eval_prompt": build_eval_prompt(name, f"A {name} is something."),
                   "instruction": [{"pos": ("Act as" if k == 0 else "You are") + f" a {name}, number {k}."} for k in range(5)],
                   "generator": {"style": "RogerV2", "template_sha256": "abc"}}
            (d / f"{s}.json").write_text(json.dumps(doc))
        return stems, [("r0", d, "RogerV2@abc")]

    def test_a_role_plan_carries_the_display_name_and_the_files_judge_prompt(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_role_arms(tmp_path)
        plan, left_out = exp.build_arms_plan(arms, stems, 20, entity="role")
        assert left_out == [] and plan["entity"] == "role"
        t = plan["traits"]["devils_advocate"]
        assert t["label"] == "devil's advocate" and t["entity"] == "role"
        assert t["judge_prompt"].startswith("You are evaluating whether the model's response displays the role")
        assert "{question}" in t["judge_prompt"] and "{answer}" in t["judge_prompt"]
        assert t["variants"][0]["form"] == exp_audit_form("Act as a devils advocate.")

    def test_a_trait_plan_cannot_take_role_arms_or_the_reverse(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_role_arms(tmp_path)
        plan, _ = exp.build_arms_plan(arms, stems, 20, entity="role")
        with pytest.raises(SystemExit):
            exp.build_arms_plan(arms, stems, 20, existing=plan, entity="trait")

    def test_a_role_is_judged_with_its_own_prompt(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_role_arms(tmp_path)
        plan, _ = exp.build_arms_plan(arms, stems[:1], 20, entity="role")
        out = tmp_path / "out"
        (out / "responses").mkdir(parents=True)
        (out / "plan.json").write_text(json.dumps(plan))
        rows = [{"variant": "r0_p0", "question_index": 0, "question": "Where do you live?", "provider": "SomeHost",
                 "conversation": [{"role": "assistant", "content": "In the warm shallows."}]}]
        (out / "responses" / "coral_reef.jsonl").write_text(json.dumps(rows[0]) + "\n")
        seen = []

        async def fake(client, prompt, model, max_tokens, limiter, usage=None):
            seen.append(prompt)
            return "It speaks as the reef.\nSCORE: 3"
        monkeypatch.setattr(exp, "call_judge_single", fake)
        monkeypatch.setattr(exp.openai, "AsyncOpenAI", lambda **kw: object())
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        args = SimpleNamespace(judge_model="gpt-4.1-mini", requests_per_second=50, dry_run=False, via=None)
        asyncio.run(exp.judge(args, exp.load_plan(out), out))
        assert len(seen) == 1 and "displays the role: **coral reef**" in seen[0]
        assert "Where do you live?" in seen[0] and "In the warm shallows." in seen[0]
        trait_template = exp.trait_judge_prompt("coral reef", "A coral reef is something.")
        assert seen[0].split("[QUESTION START]")[0] != trait_template.split("[QUESTION START]")[0]
        assert json.loads((out / "scores" / "coral_reef.json").read_text()) == {"r0_p0_q0": 3}

    def test_the_report_breaks_shares_down_by_opening(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        stems, arms = self.make_role_arms(tmp_path)
        plan, _ = exp.build_arms_plan(arms, stems, 20, entity="role")
        out = tmp_path / "out"
        (out / "scores").mkdir(parents=True)
        (out / "plan.json").write_text(json.dumps(plan))
        for s in stems:   # p0 opens "Act as" and always scores 3; the others score 3 half the time
            sc = {f"r0_p{k}_q{q}": (3 if k == 0 or q % 2 == 0 else 1) for k in range(5) for q in range(4)}
            (out / "scores" / f"{s}.json").write_text(json.dumps(sc))
        report = exp.arms_report(exp.load_plan(out), out, "r0", [])
        forms = report["forms"]["r0"]
        act_as = exp_audit_form("Act as a reef.")
        assert forms[act_as] == {"n": 2, "mean": 100.0}
        assert sum(f["n"] for f in forms.values()) == 10
        assert "by opening" in exp.render_arms_report(report)


class TestRoleDepthJudge:
    """The role wording of the depth judge (2026-10-02): same points, scale and reply format."""

    def test_same_fields_and_order_as_the_trait_version(self):
        p = exp.ROLE_DEPTH_JUDGE_PROMPT
        for field in ("{trait}", "{description}", "{question}", "{answer}"):
            assert field in p
        assert "<role>" in p and "personality" not in p
        assert "{system" not in p and "instruction" not in p.lower()
        for point in ("- voice:", "- in_action:", "- describes_itself:", "- caricature:"):
            assert point in p
        example = p[p.rindex('{{"reason"'):]
        assert example.index('"reason"') < example.index('"voice"') < example.index('"caricature"')
        assert exp.parse_depth(TestDepthJudge.GOOD)["caricature"] == 0

    def test_a_role_entry_is_read_with_the_role_wording(self, tmp_path, monkeypatch):
        out = tmp_path / "out"
        (out / "responses").mkdir(parents=True)
        plan = {"traits": {"forger": {"label": "forger", "description": "A forger copies signatures.",
                                      "entity": "role", "judge_prompt": "x", "questions": ["Q?"],
                                      "variants": [{"name": "act_as", "text": "Act as a forger."}]}}}
        (out / "plan.json").write_text(json.dumps(plan))
        row = {"variant": "act_as", "question_index": 0, "question": "Q?", "provider": "SomeHost",
               "conversation": [{"role": "assistant", "content": "I age the paper with tea."}]}
        (out / "responses" / "forger.jsonl").write_text(json.dumps(row) + "\n")
        (out / "scores").mkdir()
        (out / "scores" / "forger.json").write_text(json.dumps({"act_as_q0": 3}))   # only scored answers are read
        seen = []

        async def fake(client, model, prompt, semaphore, usage, tally):
            seen.append(prompt)
            return exp.parse_depth(TestDepthJudge.GOOD)
        monkeypatch.setattr(exp, "depth_call", fake)
        monkeypatch.setattr(exp.anthropic, "AsyncAnthropic", lambda **kw: object())
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
        args = SimpleNamespace(model="claude-sonnet-4-6", min_score=0, concurrency=2, dry_run=False)
        asyncio.run(exp.depth(args, exp.load_plan(out), out))
        assert len(seen) == 1 and "<role>\nforger\n</role>" in seen[0] and "I age the paper" in seen[0]


# ---------------------------------------------------------------------------
# openings (2026-11-06): one body under several openings
# ---------------------------------------------------------------------------

COLON = "You are easily thrown: every unexpected question breaks your composure, and you stammer."
SENTENCE = "You are completely stuck the moment circumstances are not ideal. You quit without looking further."


class TestSplitAdjective:
    def test_the_colon_form(self):
        a = exp.split_adjective(COLON)
        assert a.colon and a.x == "easily thrown" and a.rest.startswith("every unexpected")
        assert a.opening == "You are easily thrown:" and a.compose("At heart, you are easily thrown") == COLON.replace(
            "You are", "At heart, you are", 1)

    def test_the_sentence_form(self):
        a = exp.split_adjective(SENTENCE)
        assert not a.colon and a.x == "completely stuck the moment circumstances are not ideal"
        assert a.rest == " You quit without looking further."
        assert a.compose("Being stuck is your way") == "Being stuck is your way. You quit without looking further."

    @pytest.mark.parametrize("text", ["You are someone who quits.", "You are a person who quits: always.",
                                      "Be someone who quits.", "From now on, you are someone who quits.",
                                      "You are the kind of person who quits."])
    def test_other_openings_are_not_taken(self, text):
        assert exp.split_adjective(text) is None

    def test_it_agrees_with_the_audits_classifier_on_the_corpus(self):
        import glob
        from data_analysis import audit_trait_instructions as audit
        for f in sorted(glob.glob("data/traits/instructions/*.json"))[:150]:
            for p in json.loads(Path(f).read_text())["instruction"]:
                assert (exp.split_adjective(p["pos"]) is not None) == (audit.opening_form(p["pos"]) == audit.FORM_YOU_ARE), p["pos"]

    @pytest.mark.parametrize("word, art", [("easily", "an"), ("petty", "a"), ("honest", "an"), ("unique", "a"),
                                           ("unfair", "an"), ("useful", "a"), ("open", "an")])
    def test_article(self, word, art):
        assert exp.article(word) == art


class TestOpeningArms:
    def test_mechanical_adjective_arms_keep_the_body(self):
        a = exp.split_adjective(COLON)
        arms = exp.adjective_arms(a, None)
        body = COLON[len("You are easily thrown"):]
        assert arms["A1"]["text"] == COLON and arms["A1"]["built"] == "as is"
        assert arms["A2"]["text"] == "You are an easily thrown person" + body and arms["A2"]["built"] == "swap"
        assert arms["A3"]["text"] == "By nature, you are easily thrown" + body
        assert arms["A4"]["text"] == "At heart, you are easily thrown" + body
        assert arms["A5"]["text"] == "You have always been easily thrown" + body
        assert arms["A7"]["text"] == "You are someone who is easily thrown" + body
        assert arms["A6"]["text"] == "This is who you are: easily thrown. Every unexpected question breaks your " \
                                     "composure, and you stammer."
        assert "A8" not in arms   # needs the rewrite

    def test_a_long_opening_takes_the_rewrite_for_a2_and_a8(self):
        a = exp.split_adjective(SENTENCE)
        assert not a.simple
        rw = {"a_person": "You are a helpless person the moment circumstances are not ideal",
              "trait_first": "Being stuck comes over you the moment things are not ideal"}
        arms = exp.adjective_arms(a, rw)
        assert arms["A2"]["text"] == rw["a_person"] + ". You quit without looking further." and arms["A2"]["built"] == "rewrite"
        assert arms["A8"]["text"] == rw["trait_first"] + ". You quit without looking further."
        assert arms["A6"]["text"] == "This is who you are: " + SENTENCE[len("You are "):]
        assert "A2" not in exp.adjective_arms(a, None)

    def test_who_arms_swap_only_the_opening(self):
        pos = ["Be someone who frets. More.", "Become someone who frets. More.", "You are someone who frets.",
               COLON]
        arms = exp.who_arms(pos)
        assert set(arms) == {"W1", "W2", "W4", "W5", "W6", "W8", "R1"}   # no W3, so no W7
        assert arms["W5"]["text"] == "Be a person who frets. More." and arms["W5"]["source"] == "W1"
        assert arms["R1"]["text"] == "Speak as a person who frets. More."
        assert arms["W8"]["text"] == "You are the kind of person who frets."

    @pytest.mark.parametrize("text, negates", [("Nothing much ruffles you", True), ("You don't rattle", True),
                                               ("Calm holds you", False), ("Your notes are tidy", False)])
    def test_negation(self, text, negates):
        assert bool(exp.NEGATION.search(text)) is negates

    @pytest.mark.parametrize("text, label, neg, named", [
        ("Nothing ruffles you", "unflappable", "flustered", False),
        ("You are never flustered", "unflappable", "flustered", True),
        ("Fairness means nothing to you", "unfair", "non-unfair", True),     # the root of un-fair
        ("You are careless", "careless (HEXACO)", "careful (HEXACO)", False),
        ("You are never careful", "careless (HEXACO)", "careful (HEXACO)", True),
        ("You are kind", "kind", "non-kind", False),
    ])
    def test_names_opposite(self, text, label, neg, named):
        assert exp.names_opposite(text, label, neg) is named


class TestRewrite:
    GOOD = 'Keeps the image.\n{"trait_first": "Every striking image captures your whole mind", ' \
           '"a_person": "You are an utterly capturable person"}'

    def test_parse(self):
        assert exp.parse_rewrite(self.GOOD) == {"trait_first": "Every striking image captures your whole mind",
                                                "a_person": "You are an utterly capturable person"}

    @pytest.mark.parametrize("tf, ap, message", [
        ("You are captured by images", "You are a capturable person", "you are"),
        ("Your answers drift toward every image", "You are a capturable person", "questions and answers"),
        ("Playing a dreamer comes naturally", "You are a capturable person", "part to play"),
        ("Images", "You are a capturable person", "words"),
        ("Every image captures your mind", "You are capturable", "You are a ... person"),
        ("Every image captures your mind", "You are a person who is capturable", "You are a ... person"),
        ("Capture is your nature", "You are a capturable person", "nature"),
        ("Every image captures your mind", "You are a stuck-in-a-rut person", "plain words"),
        ("Every image captures your mind", "You are a very easily and deeply captured person", "plain words"),
    ])
    def test_a_reply_off_the_rules_is_refused(self, tf, ap, message):
        with pytest.raises(ValueError, match=message):
            exp.parse_rewrite(json.dumps({"trait_first": tf, "a_person": ap}))

    def test_a_word_the_opening_already_has_is_allowed(self):
        reply = json.dumps({"trait_first": "Inventiveness runs so deep that the ordinary answer feels like failure",
                            "a_person": "You are an inventive person"})
        with pytest.raises(ValueError, match="questions and answers"):
            exp.parse_rewrite(reply)
        opening = "You are inventive to the point where the ordinary answer feels like a failure."
        assert exp.parse_rewrite(reply, opening=opening)["trait_first"].startswith("Inventiveness")

    def test_a_sentence_opening_may_go_on_after_person_but_not_with_who(self):
        ok = json.dumps({"trait_first": "Being stuck comes over you whenever things are not ideal",
                         "a_person": "You are a helpless person the moment circumstances are not ideal"})
        assert exp.parse_rewrite(ok, 15, colon=False)["a_person"].endswith("not ideal")
        with pytest.raises(ValueError):
            exp.parse_rewrite(ok, 15, colon=True)
        who = json.dumps({"trait_first": "Being stuck comes over you", "a_person": "You are a stuck person who quits"})
        with pytest.raises(ValueError):
            exp.parse_rewrite(who, 15, colon=False)

    def test_the_prompt_shows_the_opening_and_what_follows(self):
        a = exp.split_adjective(COLON)
        p = exp.rewrite_prompt("easily thrown", "This means losing composure.", a)
        assert 'Its opening is "You are easily thrown"' in p and '(": every unexpected question' in p
        assert "Four to twelve words." in p and 'ending with the word "person"' in p
        assert "{" not in p.replace('{"trait_first"', "")
        s = exp.rewrite_prompt("helpless", "This means giving up.", exp.split_adjective(SENTENCE))
        assert 'not with "who"' in s and "no more than 14 words" in s

    def test_an_unusable_reply_is_asked_again_with_the_reason(self, monkeypatch):
        seen = []

        async def fake(client, prompt, model, max_tokens, limiter, usage=None, *, reject_truncated=False):
            seen.append(prompt)
            return "No JSON here." if len(seen) == 1 else self.GOOD
        import assistant_axis.judge as judge_mod
        monkeypatch.setattr(judge_mod, "call_anthropic_judge_single", fake)
        a = exp.split_adjective(COLON)
        out = asyncio.run(exp.rewrite_one(None, "claude-sonnet-5-5", "x", "easily thrown", "d", a, None, None))
        assert out["attempts"] == 2 and out["trait_first"].startswith("Every") and out["model"] == "claude-sonnet-5-5"
        assert "could not be used: no JSON object" in seen[1]


class TestOpeningsPlan:
    def make_traits(self, tmp_path):
        d = tmp_path / "traits"
        d.mkdir()
        flust = {"positive_label": "easily thrown", "negative_label": "unflappable", "description": "Losing composure.",
                 "instruction": [{"pos": "Be someone who frets. More."}, {"pos": "Become someone who frets."},
                                 {"pos": "From now on, you are someone who frets."}, {"pos": "You are someone who frets."},
                                 {"pos": COLON}],
                 "questions": [f"Own question {i}?" for i in range(40)]}
        (d / "easily_thrown.json").write_text(json.dumps(flust))
        other = dict(flust, positive_label="calm", negative_label="non-calm",
                     instruction=[{"pos": "Be someone who rests."}, {"pos": "You are calm: you rest."}])
        (d / "calm.json").write_text(json.dumps(other))
        return d

    def test_every_arm_that_can_be_made(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        d = self.make_traits(tmp_path)
        rw = {"easily_thrown": {"trait_first": "Composure leaves you at the first surprise", "a_person": "x"}}
        blind = {"easily_thrown": [f"blind {i}. More." for i in range(5)]}
        plan, missing = exp.build_openings_plan(["easily_thrown", "calm", "gone"], d,
                                                kinds={"calm": "good"}, problem={"easily_thrown"},
                                                rewrites=rw, blind=blind)
        t = plan["traits"]["easily_thrown"]
        names = [v["name"] for v in t["variants"]]
        assert names == ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "R1", "A1", "A2", "A3", "A4", "A5", "A6",
                         "A7", "A8", "B0", "B3", "B4"]
        by = {v["name"]: v for v in t["variants"]}
        assert by["B3"]["text"] == "blind 3. More." and by["B3"]["opening"] == "blind 3." and by["B3"]["built"] == "blind"
        assert by["A8"]["text"].startswith("Composure leaves you at the first surprise: every unexpected")
        assert t["problem"] is True and t["kind"] == "unclassified" and t["label"] == "easily thrown"
        assert t["questions"] == [f"Q{i}?" for i in range(0, 100, 5)] and t["adjective"] == {"x": "easily thrown", "colon": True}
        c = plan["traits"]["calm"]
        assert c["kind"] == "good" and not c["problem"]
        assert {v["name"] for v in c["variants"]} == {"W1", "W5", "A1", "A2", "A3", "A4", "A5", "A6", "A7"}
        assert missing["(no file)"] == ["gone"] and missing["A8"] == ["calm"] and "B0" not in missing
        assert plan["max_tokens"] == 1024 and plan["temperature"] == 0.7 and plan["judge"] == exp.STEP3_JUDGE
        assert ["B3", "A8"] in plan["arm_pairs"]

    def test_own_questions_are_spread_over_the_files(self, tmp_path):
        d = self.make_traits(tmp_path)
        plan, _ = exp.build_openings_plan(["easily_thrown"], d, questions="own", n_questions=8)
        assert plan["traits"]["easily_thrown"]["questions"] == [f"Own question {i}?" for i in range(0, 40, 5)]

    def test_plan_openings_command(self, tmp_path, monkeypatch):
        monkeypatch.setattr(exp, "load_questions", lambda n: [f"Q{i}?" for i in range(n)])
        d = self.make_traits(tmp_path)
        out = tmp_path / "out"
        (tmp_path / "stems.json").write_text(json.dumps(["easily_thrown", "calm"]))
        (tmp_path / "kinds.json").write_text(json.dumps({"calm": "nice"}))
        args = exp.parse_args(["plan-openings", "--out", str(out), "--stems", str(tmp_path / "stems.json"),
                               "--traits-dir", str(d), "--kinds", str(tmp_path / "kinds.json")])
        with pytest.raises(SystemExit, match="kinds must be one of"):
            args.func(args)
        (tmp_path / "kinds.json").write_text(json.dumps({"calm": "good"}))
        args.func(args)
        plan = exp.load_plan(out)
        assert len(plan["traits"]) == 2
        with pytest.raises(SystemExit, match="--replace"):
            args.func(args)


def _write_scores(scores_dir, traits_dir, stem, shares, n=100):
    """A trait file with five instructions and step-3 scores with the given share of 3s per instruction."""
    instr = ["Be someone who a.", "Become someone who b.", "From now on, you are someone who c.",
             "You are someone who d.", "You are petty: e."]
    (traits_dir / f"{stem}.json").write_text(json.dumps({"instruction": [{"pos": s} for s in instr]}))
    sc = {f"pos_p{p}_q{q}": (3 if q < round(shares[p] * n) else 1) for p in range(5) for q in range(n)}
    (scores_dir / f"{stem}.json").write_text(json.dumps(sc))


class TestProblemInstructions:
    def test_under_half_of_the_others_and_significant(self, tmp_path):
        s, t = tmp_path / "scores", tmp_path / "traits"
        s.mkdir(), t.mkdir()
        _write_scores(s, t, "petty", [0.9, 0.85, 0.9, 0.95, 0.05])
        _write_scores(s, t, "fine", [0.9, 0.85, 0.9, 0.95, 0.6])
        _write_scores(s, t, "low", [0.06, 0.04, 0.05, 0.05, 0.01])   # under half, not significant
        (s / "usage.json").write_text("{}")
        rows = exp.problem_instructions(s, t)
        assert [(r["stem"], r["index"], r["adjective"]) for r in rows] == [("petty", 4, True)]
        assert rows[0]["kept"] == 5 and rows[0]["others"] == pytest.approx(0.9)


class TestStep3Judge:
    def test_the_template_is_step_3s(self):
        mod = exp._pipeline_judge_module()
        from assistant_axis.judge_rubrics import get_version
        for stem in ("flustered", "careless_hexaco"):
            doc = json.loads(Path(f"data/traits/instructions/{stem}.json").read_text())
            mine = exp.step3_trait_template(doc["positive_label"], doc["description"], 20)
            assert mine == mod._trait_prompt(stem, Path("data/traits/instructions"), get_version(20))

    def test_the_spec_and_the_stamp(self, tmp_path):
        assert exp.step3_judge_spec({}) is None
        spec = exp.step3_judge_spec({"judge": {"rubric": "step3"}})
        assert spec["model"] == "gpt-5.6-luna" and spec["prompt_version"] == 20 and spec["service_tier"] == "flex"
        with pytest.raises(SystemExit):
            exp.step3_judge_spec({"judge": {"rubric": "other"}})
        stamp = exp.judge_stamp(spec)
        assert stamp["truncation_marker"] == "…" and stamp["reply_format"] == "score_marker"
        (tmp_path / "scores").mkdir()
        (tmp_path / "scores" / "petty.json").write_text("{}")
        with pytest.raises(SystemExit, match="old judge"):
            exp.check_judge_stamp(tmp_path, spec)
        exp.check_judge_stamp(tmp_path, None)
        (tmp_path / "scores" / exp.JUDGE_STAMP).write_text(json.dumps(stamp))
        exp.check_judge_stamp(tmp_path, spec)
        with pytest.raises(SystemExit, match="was judged with"):
            exp.check_judge_stamp(tmp_path, None)
        with pytest.raises(SystemExit, match="was judged with"):
            exp.check_judge_stamp(tmp_path, dict(spec, prompt_version=13))

    def test_judging_marks_cut_answers_and_reads_the_marker(self, out_dir, monkeypatch):
        plan = json.loads(json.dumps(PLAN))
        plan["judge"] = {"rubric": "step3"}
        (out_dir / "plan.json").write_text(json.dumps(plan))
        (out_dir / "responses").mkdir()
        rows = [{"variant": v, "question_index": q, "question": f"Q{q}?", "finish_reason": "length" if q == 2 else "stop",
                 "conversation": [{"role": "assistant", "content": f"answer {v} {q}"}]}
                for v in ("tendency", "be_someone") for q in range(3)]
        (out_dir / "responses" / "petty.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        seen, clients = [], []

        async def fake(client, prompt, model, max_tokens, limiter, usage=None, **kw):
            seen.append((prompt, kw))
            return "Shown.\nSCORE: 3" if "be_someone" in prompt else "Not shown.\nSCORE: 1"
        import assistant_axis.judge as judge_mod
        monkeypatch.setattr(exp, "call_judge_single", fake)
        monkeypatch.setattr(judge_mod, "judge_client", lambda m, tier=None: clients.append((m, tier)) or object())
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        args = SimpleNamespace(judge_model=None, requests_per_second=50, dry_run=False, via=None, chunk=4)
        asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))
        scores = json.loads((out_dir / "scores" / "petty.json").read_text())
        assert len(scores) == 6 and scores["be_someone_q2"] == 3 and scores["tendency_q0"] == 1
        cut = [p for p, _ in seen if "answer tendency 2" in p][0]
        assert "answer tendency 2…" in cut and "answer tendency 1…" not in "".join(p for p, _ in seen)
        assert clients == [("gpt-5.6-luna", "flex"), ("gpt-5.6-luna", None)]
        kw = seen[0][1]
        assert kw["service_tier"] == "flex" and kw["reject_truncated"] is True and kw["fallback_client"] is not None
        assert json.loads((out_dir / "scores" / exp.JUDGE_STAMP).read_text())["model"] == "gpt-5.6-luna"
        args.judge_model = "gpt-4.1-mini"
        with pytest.raises(SystemExit, match="does not apply"):
            asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))

    def test_a_slow_call_holds_up_only_its_worker(self, out_dir, monkeypatch):
        """The first call waits until every other response is judged; in fixed chunks it would hold up its
        chunk and never finish.  The scores are written on the way out as well as every --chunk answers."""
        plan = json.loads(json.dumps(PLAN))
        plan["judge"] = {"rubric": "step3"}
        (out_dir / "plan.json").write_text(json.dumps(plan))
        (out_dir / "responses").mkdir()
        rows = [{"variant": v, "question_index": q, "question": f"Q{q}?", "finish_reason": "stop",
                 "conversation": [{"role": "assistant", "content": f"answer {v} {q}"}]}
                for v in ("tendency", "be_someone") for q in range(3)]
        (out_dir / "responses" / "petty.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        done = []

        async def fake(client, prompt, model, max_tokens, limiter, usage=None, **kw):
            if "answer tendency 0" in prompt:
                for _ in range(200):
                    if len(done) == 5:
                        break
                    await asyncio.sleep(0)
                else:
                    raise AssertionError("the slow call held up the others")
            done.append(prompt)
            return "Shown.\nSCORE: 3"
        import assistant_axis.judge as judge_mod
        monkeypatch.setattr(exp, "call_judge_single", fake)
        monkeypatch.setattr(judge_mod, "judge_client", lambda m, tier=None: object())
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
        args = SimpleNamespace(judge_model=None, requests_per_second=1000, dry_run=False, via=None, chunk=4,
                               in_flight=2)
        asyncio.run(exp.judge(args, exp.load_plan(out_dir), out_dir))
        assert len(done) == 6 and "answer tendency 0" in done[-1]
        assert len(json.loads((out_dir / "scores" / "petty.json").read_text())) == 6

    def test_the_plans_generation_settings(self, out_dir, monkeypatch):
        plan = json.loads(json.dumps(PLAN))
        plan["max_tokens"] = 1024
        (out_dir / "plan.json").write_text(json.dumps(plan))
        create = AsyncMock(return_value=_completion("An answer.", provider="DeepInfra"))
        rows = TestGenerate().run(out_dir, monkeypatch, create)
        assert create.call_args.kwargs["max_tokens"] == 1024 and create.call_args.kwargs["temperature"] == 0.7
        assert rows[0]["max_tokens"] == 1024 and rows[0]["temperature"] == 0.7
        assert exp.generation_settings({}) == (0.7, 512)


class TestDepthByBatch:
    def test_batched_reads_are_recorded_and_the_rest_left_for_real_time(self, out_dir, monkeypatch):
        import assistant_axis.anthropic_batch as ab
        sent = {}

        class FakeRunner:
            def __init__(self, client, work, state, **kw):
                assert kw["adopt_lost_batches"] is False

            async def resume(self):
                return set()

            def write_chunks(self, requests):
                sent.update(requests)
                return [requests]

            async def run(self, chunks, on_result, on_batch_done):
                for cid, params in chunks[0]:
                    text = TestDepthJudge.GOOD if cid.endswith("q0") else "no verdict"
                    on_result(cid, {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                                    "usage": {"input_tokens": 600, "output_tokens": 80}}, None)
                on_batch_done()
                return []
        monkeypatch.setattr(ab, "AnthropicBatchRunner", FakeRunner)
        judged = {"petty": {}}
        todo = [("petty", f"{v}_q{q}", f"prompt {v} {q}") for v in ("tendency", "be_someone") for q in range(3)]
        usage, tally = exp.CheckpointedUsage(out_dir), {"ok": 0, "total": 0}
        left = asyncio.run(exp.depth_by_batch(None, "claude-sonnet-4-6", todo, judged, PLAN, out_dir, usage, tally))
        usage.close()
        assert len(sent) == 6 and sent["petty|tendency_q0"]["temperature"] == 0.0
        assert sent["petty|tendency_q0"]["messages"][0]["content"] == "prompt tendency 0"
        assert set(judged["petty"]) == {"tendency_q0", "be_someone_q0"} and judged["petty"]["tendency_q0"]["via"] == "batch"
        assert [k for _, k, _ in left] == ["tendency_q1", "tendency_q2", "be_someone_q1", "be_someone_q2"]
        assert tally == {"ok": 2, "total": 6}
        u = json.loads((out_dir / "usage.json").read_text())
        assert u["per_model"]["claude-sonnet-4-6:batch"]["n_calls"] == 6
        assert json.loads((out_dir / "depth" / "petty.json").read_text()).keys() == {"tendency_q0", "be_someone_q0"}


class TestOpeningsReport:
    def make(self, tmp_path, shares):
        """One trait per entry of ``shares`` (arm -> share scored 3, out of 20)."""
        plan = {"traits": {}, "arm_pairs": [["A3", "A1"]]}
        (tmp_path / "responses").mkdir()
        (tmp_path / "scores").mkdir()
        for i, per in enumerate(shares):
            trait = f"t{i}"
            plan["traits"][trait] = {"label": trait, "description": "d", "kind": "bad" if i % 2 else "good",
                                     "problem": i == 0, "variants": [{"name": a, "text": a} for a in per]}
            rows, sc = [], {}
            for a, share in per.items():
                for q in range(20):
                    rows.append({"variant": a, "question_index": q, "question": "Q?",
                                 "conversation": [{"role": "assistant", "content": "As an AI, someone who" if a == "W1" else "x"}]})
                    sc[f"{a}_q{q}"] = 3 if q < round(share * 20) else 0
            (tmp_path / "responses" / f"{trait}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            (tmp_path / "scores" / f"{trait}.json").write_text(json.dumps(sc))
        return plan

    def test_menus_flag_an_opening_under_half_its_siblings(self, tmp_path):
        base = {"W1": 0.9, "W2": 0.9, "W3": 0.85, "W4": 0.9}
        plan = self.make(tmp_path, [dict(base, A1=0.0, A3=0.8), dict(base, A1=0.9, A3=0.9)])
        rep = exp.openings_report(plan, tmp_path)
        cur = rep["menus"]["current"]
        assert cur["traits"] == 2 and cur["traits_flagged"] == 1 and cur["flagged_by_arm"]["A1"] == 1
        assert cur["problem_list"]["traits_flagged"] == 1 and cur["weakest"]["trait"] == "t0"
        assert rep["menus"]["fifth=A3"]["traits_flagged"] == 0
        assert rep["arms"]["A1"]["complete_failures"] == 1 and rep["arms"]["A1"]["under_half_of_W1_W4"] == 1
        assert rep["arms"]["W1"]["ai"] == 100 and rep["arms"]["W1"]["echo"] == 100 and rep["arms"]["A1"]["echo"] is None
        assert rep["pairs"]["A3 vs A1"]["all"]["difference"] == pytest.approx(40)
        assert "fifth=A3" in exp.render_openings_report(rep)
        # a flagged trait's count must be a plain int, or --write cannot store the report (2026-11-06)
        assert type(rep["arms"]["A1"]["under_half_of_W1_W4"]) is int
        json.dumps(rep)

    def test_a_menu_must_have_five(self, tmp_path):
        plan = self.make(tmp_path, [{"W1": 0.5}])
        (tmp_path / "plan.json").write_text(json.dumps(plan))
        args = exp.parse_args(["openings-report", "--out", str(tmp_path), "--menu", "m=W1,W2"])
        with pytest.raises(SystemExit, match="five arms"):
            args.func(args)
