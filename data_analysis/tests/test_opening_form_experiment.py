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
        assert judged["be_someone_q1"]["caricature"] == 2 and judged["be_someone_q1"]["rubric_version"] == 1
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
