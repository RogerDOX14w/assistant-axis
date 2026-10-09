"""Tests for regenerate_role_instructions.py.

Mocks the Anthropic client to verify merge logic: eval_prompt rebuilt from
description, instructions and questions replaced, pos-only format.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import data_analysis.regenerate_role_instructions as module

from data_analysis.regenerate_role_instructions import (
    atomic_write_json,
    build_christina_role_prompt,
    build_eval_prompt,
    extract_description,
    regenerate_one,
    role_display_name,
    strip_markdown_fences,
)

SAMPLE_DESCRIPTION = "A financial professional who manages numerical data."

SAMPLE_ROLE = {
    "description": SAMPLE_DESCRIPTION,
    "instruction": [
        {"pos": "Old pos 1."},
        {"pos": "Old pos 2."},
        {"pos": "Old pos 3."},
        {"pos": "Old pos 4."},
        {"pos": "Old pos 5."},
    ],
    "questions": [f"Old question {i}?" for i in range(40)],
    "eval_prompt": build_eval_prompt("accountant", SAMPLE_DESCRIPTION),
}

FAKE_INSTRUCTIONS = [
    {"pos": "New pos 1."},
    {"pos": "New pos 2."},
    {"pos": "New pos 3."},
    {"pos": "New pos 4."},
    {"pos": "New pos 5."},
]

FAKE_QUESTIONS = [f"New question {i}?" for i in range(40)]

FAKE_COMBINED_RESPONSE = {
    "instruction": FAKE_INSTRUCTIONS,
    "questions": FAKE_QUESTIONS,
    "eval_prompt": "You are evaluating whether the model's response displays the role: accountant.",
}


def _make_response(text: str) -> MagicMock:
    msg = MagicMock()
    block = MagicMock(type="text", text=text)
    msg.content = [block]
    return msg


@pytest.fixture
def role_file(tmp_path: Path) -> Path:
    p = tmp_path / "accountant.json"
    p.write_text(json.dumps(SAMPLE_ROLE, indent=2))
    return p


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=_make_response(json.dumps(FAKE_COMBINED_RESPONSE))
    )
    return client


@pytest.fixture
def roger_style(monkeypatch):
    monkeypatch.setattr(module, "PROMPT_STYLE", "Roger")


@pytest.fixture
def christina_style(monkeypatch):
    monkeypatch.setattr(module, "PROMPT_STYLE", "Christina")


class TestRoleDisplayName:
    def test_simple_name(self):
        assert role_display_name("accountant") == "accountant"

    def test_underscore_to_space(self):
        assert role_display_name("coral_reef") == "coral reef"

    def test_override(self):
        assert role_display_name("devils_advocate") == "devil's advocate"


class TestExtractDescription:
    def test_extracts_description(self):
        ep = (
            "You are evaluating whether the model's response displays the role: "
            "**accountant**. A financial professional who manages data.\n\n"
            "Prompt:\n[QUESTION START]"
        )
        assert extract_description(ep) == "A financial professional who manages data."

    def test_returns_empty_on_missing_bold(self):
        assert extract_description("No bold markers here.") == ""

    def test_returns_empty_on_empty_string(self):
        assert extract_description("") == ""


class TestBuildEvalPrompt:
    def test_contains_role_and_description(self):
        result = build_eval_prompt("accountant", "Manages financial data.")
        assert "**accountant**" in result
        assert "Manages financial data." in result

    def test_preserves_question_answer_placeholders(self):
        result = build_eval_prompt("accountant", "Manages financial data.")
        assert "{question}" in result
        assert "{answer}" in result

    def test_uses_0_to_3_scale(self):
        result = build_eval_prompt("accountant", "Manages financial data.")
        assert "0 if" in result
        assert "1 if" in result
        assert "2 if" in result
        assert "3 if" in result
        # Reason-before-score ending (AGENT_NOTES "Judge prompts: reason BEFORE
        # score"); the pre-May-2026 "number between 0 and 3 ... just the number"
        # ending is the forbidden anti-pattern and must not come back.
        assert "SCORE: <integer from 0 to 3>" in result
        assert "briefly reason" in result
        assert "just the number" not in result

    def test_roundtrip_with_extract(self):
        desc = "A financial professional who manages data."
        rebuilt = build_eval_prompt("accountant", desc)
        extracted = extract_description(rebuilt)
        assert extracted == desc


class TestStripMarkdownFences:
    def test_strips_json_fence(self):
        assert strip_markdown_fences('```json\n[1,2]\n```') == "[1,2]"

    def test_strips_bare_fence(self):
        assert strip_markdown_fences("```\nfoo\n```") == "foo"

    def test_noop_on_clean_json(self):
        assert strip_markdown_fences('[{"a":1}]') == '[{"a":1}]'


class TestBuildChristinaRolePrompt:
    def test_substitutes_role_and_description(self):
        result = build_christina_role_prompt("accountant", "Manages data.", 5, 40)
        assert "<role>\naccountant\n</role>" in result
        assert "Manages data." in result

    def test_parameterizes_counts(self):
        result = build_christina_role_prompt("chef", "Cooks food.", 3, 20)
        assert "list of 3 instructions" in result
        assert "Design 20 questions" in result
        assert "Generate 20 diverse questions" in result
        assert "question 20" in result

    def test_no_neg_instructions(self):
        result = build_christina_role_prompt("chef", "Cooks food.", 5, 40)
        assert '"neg"' not in result
        assert "negative" not in result.lower()

    def test_eval_template_has_single_brace_placeholders(self):
        result = build_christina_role_prompt("chef", "Cooks food.", 5, 40)
        assert "{ROLE}" in result
        assert "{question}" in result
        assert "{answer}" in result
        assert "{{ROLE}}" not in result

    def test_json_format_has_single_braces(self):
        result = build_christina_role_prompt("chef", "Cooks food.", 5, 40)
        idx = result.find("<output_format>")
        section = result[idx:]
        assert '{\n  "instruction"' in section
        assert '{"pos":' in section


class TestRegenerateOne:
    """Core merge-logic tests for role regeneration."""

    def test_replaces_instructions_and_questions(self, role_file, mock_client, roger_style):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(role_file.read_text())
        expected_eval = build_eval_prompt("accountant", SAMPLE_DESCRIPTION)
        assert data["eval_prompt"] == expected_eval
        assert data["description"] == SAMPLE_DESCRIPTION
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == FAKE_QUESTIONS
        assert mock_client.messages.create.call_count == 1

    def test_skip_when_counts_match(self, role_file, mock_client, roger_style):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=False,
                dry_run=False,
            )
        )

        assert result.startswith("SKIP")
        data = json.loads(role_file.read_text())
        assert data["instruction"] == SAMPLE_ROLE["instruction"]
        mock_client.messages.create.assert_not_called()

    def test_force_overrides_skip(self, role_file, mock_client, roger_style):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(role_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS

    def test_dry_run_no_writes(self, role_file, mock_client, roger_style):
        original = role_file.read_text()

        result = asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=True,
            )
        )

        assert result.startswith("DRY-RUN")
        assert role_file.read_text() == original
        mock_client.messages.create.assert_not_called()

    def test_skip_default_role(self, tmp_path, mock_client, roger_style):
        p = tmp_path / "default.json"
        p.write_text(json.dumps({"instruction": [{"pos": ""}]}))

        result = asyncio.run(
            regenerate_one(
                mock_client,
                p,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("SKIP")
        assert "default" in result
        mock_client.messages.create.assert_not_called()

    def test_preserves_unknown_fields(self, role_file, mock_client, roger_style):
        data = json.loads(role_file.read_text())
        data["custom_field"] = "keep me"
        role_file.write_text(json.dumps(data))

        mock_client.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(FAKE_COMBINED_RESPONSE))
        )

        asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        data = json.loads(role_file.read_text())
        assert data["custom_field"] == "keep me"

    def test_key_order(self, role_file, mock_client, roger_style):
        """Output keys should be: description, instruction, questions, eval_prompt."""
        asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        data = json.loads(role_file.read_text())
        keys = list(data.keys())
        assert keys[0] == "description"
        assert keys[1] == "instruction"
        assert keys[2] == "questions"
        assert keys[3] == "eval_prompt"

    def test_pos_only_no_neg(self, role_file, mock_client, roger_style):
        """Verify output instructions are pos-only (no neg key)."""
        asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        data = json.loads(role_file.read_text())
        for item in data["instruction"]:
            assert "pos" in item
            assert "neg" not in item

    def test_christina_style(self, role_file, mock_client, christina_style):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                role_file,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(role_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == FAKE_QUESTIONS

    def test_underscore_role_name(self, tmp_path, mock_client, roger_style):
        """Role with underscore in filename uses display name."""
        p = tmp_path / "coral_reef.json"
        role_data = {
            "description": "A living underwater ecosystem.",
            "instruction": [{"pos": f"Old {i}."} for i in range(5)],
            "questions": [f"Q{i}?" for i in range(40)],
            "eval_prompt": build_eval_prompt("coral reef", "A living underwater ecosystem."),
        }
        p.write_text(json.dumps(role_data))

        mock_client.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(FAKE_COMBINED_RESPONSE))
        )

        result = asyncio.run(
            regenerate_one(
                mock_client,
                p,
                n_variants=5,
                n_questions=40,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        assert "coral reef" in result


class TestAtomicWriteJson:
    def test_writes_valid_json(self, tmp_path):
        p = tmp_path / "out.json"
        atomic_write_json(p, {"a": 1})
        assert json.loads(p.read_text()) == {"a": 1}

    def test_trailing_newline(self, tmp_path):
        p = tmp_path / "out.json"
        atomic_write_json(p, {"a": 1})
        assert p.read_text().endswith("\n")


class TestUsageTracking:
    """Every API response ticks the MultiModelUsage tracker (AGENT_NOTES
    "Token usage logging is mandatory on batched LLM call sites")."""

    def test_regenerate_one_charges_tracker(self, role_file, roger_style):
        from assistant_axis.judge_pricing import MultiModelUsage

        resp = _make_response(json.dumps(FAKE_COMBINED_RESPONSE))
        resp.usage = MagicMock(input_tokens=1100, output_tokens=3300)
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=resp)
        tracker = MultiModelUsage()
        result = asyncio.run(
            regenerate_one(
                client, role_file, n_variants=5, n_questions=40,
                model="claude-sonnet-4-6", semaphore=asyncio.Semaphore(10),
                temperature=1.0, force=True, dry_run=False, usage=tracker,
            )
        )
        assert result.startswith("OK")
        assert tracker.n_calls == 1
        assert tracker.total_prompt_tokens == 1100
        assert tracker.total_completion_tokens == 3300
        assert list(tracker.per_model) == ["claude-sonnet-4-6"]

    def test_persist_usage_merges_into_existing_file(self, tmp_path):
        from assistant_axis.judge_pricing import MultiModelUsage

        path = tmp_path / "regeneration_usage.json"
        first = MultiModelUsage(); first.charge("claude-sonnet-4-6", 100, 200)
        module.persist_usage(first, path)
        second = MultiModelUsage(); second.charge("claude-sonnet-4-6", 10, 20)
        module.persist_usage(second, path)
        total = MultiModelUsage.load_or_create(path)
        assert total.n_calls == 2 and total.total_prompt_tokens == 110


class TestRogerV2StyleAndProvenance:
    """The Sep 2026 RogerV2 template and the ``generator`` provenance field."""

    def test_v2_prompt_substitutes_and_carries_the_rules(self):
        p = module.build_roger_role_prompt_v2("smuggler", "A smuggler moves contraband.", 5, 40)
        assert "<role>\nsmuggler\n</role>" in p and "A smuggler moves contraband." in p
        for phrase in ("case-worker", "poisoner", "15 to 25", "self-justification", '"question 40"'):
            assert phrase in p, phrase
        assert "{n_variants}" not in p and "{n_questions}" not in p

    def test_v2_examples_obey_the_register_rule(self):
        p = module.build_roger_role_prompt_v2("x", "y", 5, 40)
        block = p.split("<example_instructions>")[1].split("</example_instructions>")[0]
        for marker in ("navigating", "individuals", "demonstrate", "appropriate", "engage with", "the challenges of", "in a healthy way"):
            assert marker not in block, marker

    def test_v2_json_format_has_single_braces(self):
        p = module.build_roger_role_prompt_v2("x", "y", 5, 40)
        assert '{\n  "instruction"' in p and "{{" not in p and "}}" not in p

    def test_style_dispatch_sends_v2_prompt_and_writes_generator(self, role_file, mock_client, monkeypatch):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV2")
        result = asyncio.run(regenerate_one(
            mock_client, role_file, n_variants=5, n_questions=40, model="test-model",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
        ))
        assert result.startswith("OK")
        sent = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "case-worker" in sent and "<example_instructions>" in sent
        g = json.loads(role_file.read_text())["generator"]
        assert g["style"] == "RogerV2" and g["model"] == "test-model"
        assert g["template_sha256"] == module.template_sha256("RogerV2") and len(g["template_sha256"]) == 12
        assert g["temperature"] == 1.0 and g["thinking_budget"] == 0 and g["script"] == "regenerate_role_instructions.py"

    def test_generator_written_for_v1_and_replaces_stale_value(self, role_file, mock_client, roger_style):
        d = json.loads(role_file.read_text()); d["generator"] = {"style": "stale"}
        role_file.write_text(json.dumps(d))
        asyncio.run(regenerate_one(
            mock_client, role_file, n_variants=5, n_questions=40, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
        ))
        g = json.loads(role_file.read_text())["generator"]
        assert g["style"] == "Roger" and g["template_sha256"] != module.template_sha256("RogerV2")

    def test_template_hashes_are_distinct_per_style(self):
        shas = {s: module.template_sha256(s) for s in ("Christina", "Roger", "RogerV2")}
        assert shas["Roger"] != shas["RogerV2"]

    def test_parse_args_accepts_v2(self):
        assert module.parse_args(["--roles", "x", "--style", "RogerV2"]).style == "RogerV2"


# ---------------------------------------------------------------------------
# --instructions-only, --roles-dir and --batch (2026-10-02, as for traits)
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402


class TestInstructionsOnly:
    def test_keeps_the_questions_in_the_file(self, role_file, mock_client, roger_style):
        result = asyncio.run(regenerate_one(
            mock_client, role_file, n_variants=5, n_questions=40, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
            instructions_only=True,
        ))
        d = json.loads(role_file.read_text())
        assert d["instruction"] == FAKE_INSTRUCTIONS
        assert d["questions"] == SAMPLE_ROLE["questions"]
        assert result == "OK accountant: 5 instructions"

    def test_skip_without_force_ignores_the_question_count(self, tmp_path):
        d = dict(SAMPLE_ROLE, questions=["just one?"])
        assert module.reason_to_skip("accountant", d, 5, 40, instructions_only=True, force=False)
        assert module.reason_to_skip("accountant", d, 5, 40, instructions_only=False, force=False) is None

    def test_default_is_always_skipped(self):
        assert module.reason_to_skip("default", {}, 5, 40, instructions_only=False, force=True).startswith("SKIP")


class TestRolesDir:
    def test_points_the_run_at_a_staging_copy(self, tmp_path, monkeypatch, capsys):
        corpus, stage = tmp_path / "corpus", tmp_path / "stage"
        for d in (corpus, stage):
            d.mkdir()
            (d / "accountant.json").write_text(json.dumps(SAMPLE_ROLE))
        (stage / "only_staged.json").write_text(json.dumps(SAMPLE_ROLE))
        monkeypatch.setattr(module, "ROLES_DIR", corpus)
        module.main(["--roles", "only_staged", "--roles-dir", str(stage), "--dry-run", "--force"])
        err = capsys.readouterr().err
        assert "not the corpus" in err and "DRY-RUN" in err
        assert module.ROLES_DIR == stage.resolve()
        assert module.parse_args(["--roles", "a"]).roles_dir is None


class _Results:
    """What ``client.messages.batches.results`` resolves to: an async iterator."""

    def __init__(self, entries):
        self._entries = list(entries)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._entries:
            raise StopAsyncIteration
        return self._entries.pop(0)


def _message(text, tokens=(2000, 3000)):
    return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)],
                           usage=SimpleNamespace(input_tokens=tokens[0], output_tokens=tokens[1]))


def _entry(stem, kind="succeeded", text=None):
    result = SimpleNamespace(type=kind)
    if kind == "succeeded":
        result.message = _message(text if text is not None else json.dumps(FAKE_COMBINED_RESPONSE))
    return SimpleNamespace(custom_id=stem, result=result)


def _counts(**kw):
    base = dict(succeeded=0, errored=0, expired=0, canceled=0, processing=0)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def batch_setup(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    for stem in ("accountant", "forger", "herder"):
        (stage / f"{stem}.json").write_text(json.dumps(dict(SAMPLE_ROLE, keep_me="yes")))
    (stage / "default.json").write_text(json.dumps({"instruction": [{"pos": ""}]}))
    client = MagicMock()
    client.messages.batches.create = AsyncMock(return_value=SimpleNamespace(id="msgbatch_test"))
    client.messages.batches.retrieve = AsyncMock(side_effect=[
        SimpleNamespace(processing_status="in_progress", request_counts=_counts(processing=3)),
        SimpleNamespace(processing_status="ended", request_counts=_counts(succeeded=2, errored=1)),
    ])
    client.messages.batches.results = AsyncMock(return_value=_Results([
        _entry("forger"), _entry("accountant", text="not json at all"), _entry("herder", kind="errored")]))
    real_time = _make_response(json.dumps(FAKE_COMBINED_RESPONSE))
    real_time.usage = SimpleNamespace(input_tokens=2000, output_tokens=3000)
    client.messages.create = AsyncMock(return_value=real_time)
    monkeypatch.setattr(module.anthropic, "AsyncAnthropic", lambda **kw: client)
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(module, "ROLES_DIR", stage)
    usage_json = tmp_path / "records" / "usage.json"
    usage_json.parent.mkdir()
    args = ["--all", "--roles-dir", str(stage), "--style", "RogerV2", "--force", "--usage-json", str(usage_json)]
    return SimpleNamespace(stage=stage, client=client, usage_json=usage_json, args=args)


class TestBatchRequests:
    def test_one_request_per_file_with_the_stem_as_its_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV2")
        paths = []
        for stem in ("accountant", "coral_reef"):
            p = tmp_path / f"{stem}.json"
            p.write_text(json.dumps(SAMPLE_ROLE))
            paths.append(p)
        requests, skipped = module.build_batch_requests(
            paths, n_variants=5, n_questions=40, instructions_only=False, model="claude-sonnet-4-6",
            temperature=1.0, thinking_budget=0, force=True)
        assert [r["custom_id"] for r in requests] == ["accountant", "coral_reef"] and skipped == []
        params = requests[1]["params"]
        assert params["model"] == "claude-sonnet-4-6" and params["max_tokens"] == 16384
        assert "<role>\ncoral reef\n</role>" in params["messages"][0]["content"]   # display form in the prompt
        assert params == module.combined_create_kwargs(
            "coral reef", SAMPLE_DESCRIPTION, 5, 40, "claude-sonnet-4-6", 1.0, 0)

    def test_files_that_need_nothing_are_skipped_without_force(self, tmp_path):
        p = tmp_path / "accountant.json"
        p.write_text(json.dumps(SAMPLE_ROLE))
        requests, skipped = module.build_batch_requests(
            [p], n_variants=5, n_questions=40, instructions_only=False, model="m", temperature=1.0,
            thinking_budget=0, force=False)
        assert requests == [] and skipped[0].startswith("SKIP accountant")

    def test_every_corpus_stem_can_be_an_id(self):
        d = Path(module.__file__).resolve().parent.parent / "data" / "roles" / "instructions"
        if not d.is_dir():
            pytest.skip("corpus not found")
        assert not [p.stem for p in d.glob("*.json") if not module.BATCH_ID_PATTERN.match(p.stem)]


class TestBatchRun:
    def test_submit_wait_collect_and_fill_in_real_time(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        sent = b.client.messages.batches.create.call_args.kwargs["requests"]
        assert sorted(r["custom_id"] for r in sent) == ["accountant", "forger", "herder"]   # never default
        assert b.client.messages.batches.retrieve.call_count == 2
        # forger came from the batch; accountant (unusable reply) and herder (errored) were asked for in real time
        assert b.client.messages.create.call_count == 2
        for stem, from_batch in (("forger", True), ("accountant", False), ("herder", False)):
            d = json.loads((b.stage / f"{stem}.json").read_text())
            assert d["instruction"] == FAKE_INSTRUCTIONS and d["keep_me"] == "yes"
            assert d["generator"]["style"] == "RogerV2" and d["generator"].get("batch", False) is from_batch
        assert "1 from the batch, 2 in real time" in err and "request errored" in err
        assert "test-key-not-real" not in err

    def test_usage_is_kept_at_the_batch_price(self, batch_setup):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        usage = json.loads(b.usage_json.read_text())["per_model"]
        assert usage["claude-sonnet-4-6:batch"]["n_calls"] == 2   # the unusable reply is still paid for
        assert usage["claude-sonnet-4-6:batch"]["cost_usd"] == pytest.approx(2 * (2000 * 1.5 + 3000 * 7.5) / 1e6)
        assert usage["claude-sonnet-4-6"]["n_calls"] == 2

    def test_the_batch_is_recorded_beside_the_usage_record(self, batch_setup):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        log = json.loads(module.batch_log_path(b.usage_json).read_text())
        assert len(log) == 1 and log[0]["id"] == "msgbatch_test" and log[0]["n_requests"] == 3
        assert log[0]["template_sha256"] == module.template_sha256("RogerV2")
        assert log[0]["roles_dir"] == str(b.stage.resolve())

    def test_submit_without_waiting_then_collect_by_id(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--batch-no-wait", "--model", "claude-sonnet-4-6"])
        assert b.client.messages.batches.retrieve.call_count == 0
        assert "--batch-id msgbatch_test" in capsys.readouterr().err
        assert json.loads((b.stage / "forger.json").read_text())["instruction"] == SAMPLE_ROLE["instruction"]
        module.main(b.args + ["--batch-id", "msgbatch_test", "--model", "claude-sonnet-4-6"])
        assert b.client.messages.batches.create.call_count == 1
        assert json.loads((b.stage / "forger.json").read_text())["instruction"] == FAKE_INSTRUCTIONS

    def test_instructions_only_keeps_the_questions_from_a_batch(self, batch_setup):
        b = batch_setup
        module.main(b.args + ["--batch", "--instructions-only", "--model", "claude-sonnet-4-6"])
        d = json.loads((b.stage / "forger.json").read_text())
        assert d["instruction"] == FAKE_INSTRUCTIONS and d["questions"] == SAMPLE_ROLE["questions"]

    def test_a_dry_run_submits_nothing(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--dry-run"])
        assert b.client.messages.batches.create.call_count == 0
        assert "Batch: 3 request(s), 1 file(s) skipped" in capsys.readouterr().err

    def test_real_time_is_the_default(self):
        args = module.parse_args(["--roles", "accountant"])
        assert args.batch is False and args.batch_id is None and args.instructions_only is False
        assert args.batch_poll == module.DEFAULT_BATCH_POLL_SECONDS


class TestRogerV3Draft:
    """The role rubric V3 draft (2026-10-03): openings, self-check, question quotas, five examples."""

    def test_prompt_substitutes_and_carries_the_new_rules(self):
        p = module.build_roger_role_prompt_v3("smuggler", "A smuggler moves contraband.", 5, 40)
        assert "<role>\nsmuggler\n</role>" in p and "A smuggler moves contraband." in p
        for phrase in ('"From now on, you are a ..."', '"Become a ..."', "do not tell it to play a part",
                       "does it open by telling the model who to be", "open in 5 different ways",
                       "At least 8 of the questions", "about 8 of the questions", "15 to 25", "self-justification",
                       '"question 40"', "costs the role something"):
            assert phrase in p, phrase
        for left in ("{n_variants}", "{n_two_option}", "{n_advice}", "{n_questions}", "{{"):
            assert left not in p, left

    def test_no_role_play_opening_in_the_menu_or_the_examples(self):
        p = module.build_roger_role_prompt_v3("x", "y", 5, 40)
        menu = p.split("Openings that work:")[1].split("Use the ones")[0]
        assert "Act as" not in menu
        block = p.split("<example_instructions>")[1].split("</example_instructions>")[0]
        assert "Act as" not in block and block.count('"pos"') == 5
        for marker in ("navigating", "individuals", "demonstrate", "appropriate", "engage with", "the challenges of"):
            assert marker not in block, marker

    def test_examples_open_in_five_different_ways_none_role_play(self):
        from data_analysis import audit_role_instructions as audit
        from data_analysis import audit_trait_instructions as A
        examples = audit.role_example_instructions("RogerV3")
        forms = [A.opening_form(e) for e in examples]
        assert len(examples) == 5 and len(set(forms)) == 5 and A.FORM_ACT_AS not in forms
        assert all(15 <= len(e.split()) <= 28 for e in examples)   # the liar example runs to 28 (Roger, 2026-10-03)

    def test_step_three_and_the_output_format_are_v2s(self):
        v2, v3 = module._ROGER_ROLE_TEMPLATE_V2, module._ROGER_ROLE_TEMPLATE_V3
        assert v3[v3.index("Step 3:"):] == v2[v2.index("Step 3:"):]
        assert "Step 2:" in v3 and v3.count("Step 3:") == 1

    def test_registered_and_the_default_since_adoption(self):
        assert module.template_sha256("RogerV3") != module.template_sha256("RogerV2")
        assert module.parse_args(["--roles", "x", "--style", "RogerV2"]).style == "RogerV2"
        assert module.parse_args(["--roles", "x"]).style == "RogerV3"   # adopted 2026-10-03
        # the module global is set by main() from --style, so an earlier test may have changed it; read the source
        import re
        source = Path(module.__file__).read_text(encoding="utf-8")
        assert re.search(r'^PROMPT_STYLE = "RogerV3"$', source, re.M)

    def test_dispatch_sends_v3_and_records_it(self, role_file, mock_client, monkeypatch):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV3")
        asyncio.run(regenerate_one(
            mock_client, role_file, n_variants=5, n_questions=40, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
        ))
        sent = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert '"From now on, you are a ..."' in sent and "Become a glacier" in sent
        g = json.loads(role_file.read_text())["generator"]
        assert g["style"] == "RogerV3" and g["template_sha256"] == module.template_sha256("RogerV3")


# ---------------------------------------------------------------------------
# The opening reroll (2026-10-06): a set whose instructions do not open in
# n_variants different ways is generated again, once
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _opening_reroll_off(monkeypatch):
    """The fake replies above open every instruction the same way and the
    older tests count calls, so the reroll is off unless a test turns it on."""
    monkeypatch.setattr(module, "OPENING_REROLL", False)


FIVE_OPENINGS = ["You are an accountant who counts everything.", "Be an accountant.", "You're an accountant.",
                 "Become an accountant.", "From now on, you are an accountant."]
FOUR_OPENINGS = FIVE_OPENINGS[:4] + ["Be an accountant who counts twice."]


def _combined_reply(openings):
    return _make_response(json.dumps({"instruction": [{"pos": p} for p in openings],
                                      "questions": FAKE_QUESTIONS, "eval_prompt": "x"}))


class TestOpeningReroll:
    def run(self, client, role_file):
        return asyncio.run(regenerate_one(
            client, role_file, n_variants=5, n_questions=40, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False))

    def test_the_count_uses_the_audit_classifier(self):
        assert module.distinct_openings([{"pos": p} for p in FIVE_OPENINGS]) == 5
        assert module.distinct_openings([{"pos": p} for p in FOUR_OPENINGS]) == 4

    def test_a_doubled_opening_brings_a_second_call_and_the_better_set(self, role_file, monkeypatch, capsys):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV3")
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_combined_reply(FOUR_OPENINGS), _combined_reply(FIVE_OPENINGS)])
        result = self.run(client, role_file)
        assert client.messages.create.call_count == 2 and "generated again for the openings" in result
        d = json.loads(role_file.read_text())
        assert [p["pos"] for p in d["instruction"]] == FIVE_OPENINGS and d["generator"]["opening_rerolls"] == 1
        assert "4 distinct openings of 5; generating again" in capsys.readouterr().err

    def test_one_call_when_off_or_under_another_style(self, role_file, monkeypatch):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV3")
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_combined_reply(FOUR_OPENINGS))
        self.run(client, role_file)                        # OPENING_REROLL is off (autouse)
        assert client.messages.create.call_count == 1
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV2")   # not a style whose rubric asks for it
        self.run(client, role_file)
        assert client.messages.create.call_count == 2

    def test_the_switch(self):
        assert module.parse_args(["--roles", "x"]).opening_reroll is True
        assert module.parse_args(["--roles", "x", "--no-opening-reroll"]).opening_reroll is False


class TestReplyCounts:
    """A reply with the wrong number of instructions or questions is refused
    when the counts are given, so the retry loop asks again (2026-10-07)."""

    def test_counts_are_checked_only_when_given(self):
        reply = json.dumps({"instruction": FAKE_INSTRUCTIONS, "questions": FAKE_QUESTIONS[:39], "eval_prompt": "x"})
        assert len(module.validated_combined(reply, "accountant")["questions"]) == 39
        with pytest.raises(ValueError, match="39 questions, not 40"):
            module.validated_combined(reply, "accountant", n_variants=5, n_questions=40)

    def test_a_short_reply_is_asked_for_again(self, role_file, roger_style, monkeypatch):
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        short = json.dumps({"instruction": FAKE_INSTRUCTIONS, "questions": FAKE_QUESTIONS[:39], "eval_prompt": "x"})
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_make_response(short), _make_response(json.dumps(FAKE_COMBINED_RESPONSE))])
        result = asyncio.run(regenerate_one(
            client, role_file, n_variants=5, n_questions=40, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False))
        assert client.messages.create.call_count == 2 and result.startswith("OK")
        assert len(json.loads(role_file.read_text())["questions"]) == 40


# ---------------------------------------------------------------------------
# Refusals (2026-10-08): recorded in generation_refusals.jsonl, never retried
# ---------------------------------------------------------------------------

from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402
from data_analysis import generation_refusals as refusals  # noqa: E402
from data_analysis.generation_refusals import GenerationRefusal  # noqa: E402


@pytest.fixture(autouse=True)
def _refusals_jsonl(tmp_path, monkeypatch):
    """No test writes into data/roles/generation_refusals.jsonl."""
    path = tmp_path / "refusals" / refusals.REFUSALS_NAME
    monkeypatch.setattr(module, "DEFAULT_REFUSALS_JSONL", path)
    return path


DECLINE = ("I'm not comfortable writing persona instructions for this role, since they would have a model act "
           "it out in earnest. " + "I would be glad to help with a related task instead. " * 6)


def _refused_reply(text=None, stop_reason="refusal"):
    """A reply as the SDK returns it: ``stop_reason`` "refusal" with no content,
    or a prose decline that ended normally."""
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content, stop_reason=stop_reason,
                           usage=SimpleNamespace(input_tokens=1500, output_tokens=0 if text is None else 60))


def _records(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


class TestRefusals:
    def run(self, client, role_file, **kw):
        return asyncio.run(regenerate_one(
            client, role_file, n_variants=5, n_questions=40, model="claude-sonnet-4-6",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False, **kw))

    @pytest.mark.parametrize("reply, stop_reason, excerpt", [
        (_refused_reply(), "refusal", ""),
        (_refused_reply(DECLINE, stop_reason="end_turn"), "end_turn", DECLINE[:300]),
    ], ids=["stop_reason", "prose_decline"])
    def test_raised_at_once_recorded_and_the_file_left_alone(self, role_file, monkeypatch, _refusals_jsonl,
                                                             reply, stop_reason, excerpt):
        monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV3")
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        before = role_file.read_text()
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=reply)
        usage = MultiModelUsage()
        with pytest.raises(GenerationRefusal) as info:
            self.run(client, role_file, usage=usage)
        assert client.messages.create.call_count == 1                 # not retried
        assert info.value.label == "accountant" and info.value.stop_reason == stop_reason
        assert role_file.read_text() == before
        assert usage.n_calls == 1                                      # the reply came back, so it is paid for
        [rec] = _records(_refusals_jsonl)
        assert len(DECLINE) > 300 and rec["reply_excerpt"] == excerpt
        assert {k: rec[k] for k in ("stem", "label", "kind", "model", "style", "stop_reason", "attempt")} == {
            "stem": "accountant", "label": "accountant", "kind": "role", "model": "claude-sonnet-4-6",
            "style": "RogerV3", "stop_reason": stop_reason, "attempt": "live"}
        assert rec["template_sha256"] == module.template_sha256("RogerV3") and rec["refused_at"]

    def test_a_json_reply_that_says_i_cant_is_not_a_refusal(self, role_file, roger_style, _refusals_jsonl):
        instr = [{"pos": "You are an accountant who says I can't when the books do not balance."}] * 5
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_make_response(json.dumps(dict(FAKE_COMBINED_RESPONSE, instruction=instr))))
        assert self.run(client, role_file).startswith("OK")
        assert json.loads(role_file.read_text())["instruction"] == instr
        assert not _refusals_jsonl.exists()

    def test_an_error_sentinel_in_the_json_is_a_refusal(self, role_file, roger_style, monkeypatch, _refusals_jsonl):
        """Housekeeping item 9: "ERROR: ..." in a field of a well-formed reply."""
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        before = role_file.read_text()
        sentinel = "ERROR: an accountant is an occupation, and these instructions would only restate it."
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_refused_reply(
            json.dumps(dict(FAKE_COMBINED_RESPONSE, instruction=[], eval_prompt=sentinel)), stop_reason="end_turn"))
        with pytest.raises(GenerationRefusal):
            self.run(client, role_file)
        assert client.messages.create.call_count == 1 and role_file.read_text() == before
        [rec] = _records(_refusals_jsonl)
        assert rec["reply_excerpt"] == f"eval_prompt: {sentinel}" and rec["stop_reason"] == "end_turn"

    def test_a_prose_preface_before_the_json_is_skipped(self, role_file, roger_style, capsys, _refusals_jsonl):
        """Housekeeping item 9: deliberation before the JSON is read past, not retried."""
        preface = "Let me consider the role first. An accountant keeps the books.\n\n```json"
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_make_response(
            preface + "\n" + json.dumps(FAKE_COMBINED_RESPONSE, indent=2) + "\n```"))
        assert self.run(client, role_file).startswith("OK") and client.messages.create.call_count == 1
        assert json.loads(role_file.read_text())["instruction"] == FAKE_INSTRUCTIONS
        assert f"skipped {len(preface)} characters of prose before the JSON for accountant" in capsys.readouterr().err
        assert not _refusals_jsonl.exists()

    def test_the_label_is_the_display_name(self, tmp_path, roger_style, _refusals_jsonl):
        p = tmp_path / "devils_advocate.json"
        p.write_text(json.dumps(SAMPLE_ROLE))
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_refused_reply())
        with pytest.raises(GenerationRefusal):
            self.run(client, p)
        [rec] = _records(_refusals_jsonl)
        assert rec["stem"] == "devils_advocate" and rec["label"] == "devil's advocate"


class TestRefusalRunSummary:
    def test_counted_apart_from_errors_and_the_run_goes_on(self, batch_setup, capsys):
        b = batch_setup

        def reply(**kw):
            prompt = kw["messages"][0]["content"]
            if "<role>\nforger\n</role>" in prompt:
                return _refused_reply(DECLINE, stop_reason="end_turn")
            if "<role>\nherder\n</role>" in prompt:
                return _make_response("not json at all")             # asked for five times, then an error
            return _make_response(json.dumps(FAKE_COMBINED_RESPONSE))
        b.client.messages.create = AsyncMock(side_effect=reply)
        module.main(b.args + ["--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        assert "REFUSED forger: I'm not comfortable writing persona instructions" in err
        assert "Done: 1 processed, 1 skipped, 1 refused, 1 errors" in err   # default is skipped
        assert b.client.messages.create.call_count == 1 + 1 + 5
        [rec] = _records(module.refusal_log_path(b.usage_json))
        assert rec["stem"] == "forger" and rec["attempt"] == "live"


class TestRefusalInBatch:
    def test_a_refused_batch_reply_is_recorded_and_not_asked_for_again(self, batch_setup, capsys):
        b = batch_setup
        refused = lambda stem, msg: SimpleNamespace(custom_id=stem, result=SimpleNamespace(type="succeeded", message=msg))
        b.client.messages.batches.results = AsyncMock(return_value=_Results([
            _entry("forger"), refused("accountant", _refused_reply()),
            refused("herder", _refused_reply(DECLINE, stop_reason="end_turn"))]))
        before = {s: (b.stage / f"{s}.json").read_text() for s in ("accountant", "herder")}
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        assert b.client.messages.create.call_count == 0               # nothing went to the real-time pass
        assert all((b.stage / f"{s}.json").read_text() == t for s, t in before.items())
        recs = _records(module.refusal_log_path(b.usage_json))
        assert [(r["stem"], r["kind"], r["attempt"], r["stop_reason"]) for r in recs] == [
            ("accountant", "role", "batch", "refusal"), ("herder", "role", "batch", "end_turn")]
        assert "1 processed (1 from the batch, 0 in real time), 1 skipped, 2 refused, 0 errors" in err
        assert json.loads(b.usage_json.read_text())["per_model"]["claude-sonnet-4-6:batch"]["n_calls"] == 3
