"""Tests for regenerate_trait_instructions.py.

Mocks the Anthropic client to verify merge logic: eval_prompt and labels must
be preserved, instruction (and optionally questions) must be replaced.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import data_analysis.regenerate_trait_instructions as module

from data_analysis.regenerate_trait_instructions import (
    _CHRISTINA_TEMPLATE,
    _ROGER_TEMPLATE_V1,
    atomic_write_json,
    build_christina_instruction_prompt,
    build_roger_instruction_prompt,
    build_eval_prompt,
    extract_definition,
    regenerate_one,
    strip_markdown_fences,
)

SAMPLE_EVAL_PROMPT = (
    "You are evaluating whether the model's response displays the trait: "
    "**arrogant**. This involves showing excessive confidence.\n\n"
    "Prompt:\n[QUESTION START]\n{question}\n[QUESTION END]"
)

SAMPLE_DESCRIPTION = "This involves showing excessive confidence."

SAMPLE_TRAIT = {
    "positive_label": "arrogant",
    "negative_label": "humble",
    "description": SAMPLE_DESCRIPTION,
    "instruction": [
        {"pos": "Old pos 1.", "neg": "Old neg 1."},
        {"pos": "Old pos 2.", "neg": "Old neg 2."},
        {"pos": "Old pos 3.", "neg": "Old neg 3."},
        {"pos": "Old pos 4.", "neg": "Old neg 4."},
        {"pos": "Old pos 5.", "neg": "Old neg 5."},
    ],
    "questions": [f"Old question {i}?" for i in range(40)],
    "eval_prompt": SAMPLE_EVAL_PROMPT,
}

FAKE_INSTRUCTIONS = [
    {"pos": "New pos 1.", "neg": "New neg 1."},
    {"pos": "New pos 2.", "neg": "New neg 2."},
    {"pos": "New pos 3.", "neg": "New neg 3."},
    {"pos": "New pos 4.", "neg": "New neg 4."},
    {"pos": "New pos 5.", "neg": "New neg 5."},
]

FAKE_QUESTIONS = [f"New question {i}?" for i in range(40)]


def _make_response(text: str) -> MagicMock:
    msg = MagicMock()
    block = MagicMock(type="text", text=text)
    msg.content = [block]
    return msg


@pytest.fixture
def trait_file(tmp_path: Path) -> Path:
    p = tmp_path / "arrogant.json"
    p.write_text(json.dumps(SAMPLE_TRAIT, indent=2))
    return p


FAKE_ROGER_RESPONSE = {
    "instruction": FAKE_INSTRUCTIONS,
    "questions": FAKE_QUESTIONS,
    "eval_prompt": "You are evaluating whether the model's response displays the trait: arrogant.",
}


@pytest.fixture
def mock_client() -> AsyncMock:
    client = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=_make_response(json.dumps(FAKE_ROGER_RESPONSE))
    )
    return client


class TestExtractDefinition:
    def test_extracts_definition(self):
        result = extract_definition(SAMPLE_EVAL_PROMPT)
        assert result == "This involves showing excessive confidence."

    def test_returns_empty_on_missing_bold(self):
        assert extract_definition("No bold markers here.") == ""

    def test_returns_empty_on_empty_string(self):
        assert extract_definition("") == ""


class TestBuildEvalPrompt:
    def test_contains_label_and_description(self):
        result = build_eval_prompt("arrogant", "Shows excessive confidence.")
        assert "**arrogant**" in result
        assert "Shows excessive confidence." in result

    def test_preserves_question_answer_placeholders(self):
        result = build_eval_prompt("arrogant", "Shows excessive confidence.")
        assert "{question}" in result
        assert "{answer}" in result

    def test_roundtrip_with_extract(self):
        desc = "This involves showing excessive confidence."
        rebuilt = build_eval_prompt("arrogant", desc)
        extracted = extract_definition(rebuilt)
        assert extracted == desc


class TestStripMarkdownFences:
    def test_strips_json_fence(self):
        assert strip_markdown_fences('```json\n[1,2]\n```') == "[1,2]"

    def test_strips_bare_fence(self):
        assert strip_markdown_fences("```\nfoo\n```") == "foo"

    def test_noop_on_clean_json(self):
        assert strip_markdown_fences('[{"a":1}]') == '[{"a":1}]'


class TestRegenerateOne:
    """Core merge-logic tests."""

    def test_preserves_eval_prompt_and_labels(self, trait_file, mock_client):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        expected_eval = build_eval_prompt("arrogant", SAMPLE_DESCRIPTION)
        assert data["eval_prompt"] == expected_eval
        assert data["positive_label"] == "arrogant"
        assert data["negative_label"] == "humble"
        assert data["description"] == SAMPLE_DESCRIPTION
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == FAKE_QUESTIONS

    def test_instructions_only_preserves_questions(self, trait_file):
        client = AsyncMock()
        client.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(FAKE_ROGER_RESPONSE))
        )

        result = asyncio.run(
            regenerate_one(
                client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=True,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == SAMPLE_TRAIT["questions"]
        assert client.messages.create.call_count == 1

    def test_skip_when_counts_match(self, trait_file, mock_client):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=False,
                dry_run=False,
            )
        )

        assert result.startswith("SKIP")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == SAMPLE_TRAIT["instruction"]
        mock_client.messages.create.assert_not_called()

    def test_force_overrides_skip(self, trait_file, mock_client):
        result = asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS

    def test_dry_run_no_writes(self, trait_file, mock_client):
        original = trait_file.read_text()

        result = asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=True,
            )
        )

        assert result.startswith("DRY-RUN")
        assert trait_file.read_text() == original
        mock_client.messages.create.assert_not_called()

    def test_missing_labels_skipped(self, tmp_path):
        p = tmp_path / "broken.json"
        p.write_text(json.dumps({"instruction": []}))

        client = AsyncMock()
        result = asyncio.run(
            regenerate_one(
                client,
                p,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("SKIP")
        client.messages.create.assert_not_called()

    def test_preserves_unknown_fields(self, trait_file, mock_client):
        """Extra fields in the JSON are carried through."""
        data = json.loads(trait_file.read_text())
        data["custom_field"] = "keep me"
        trait_file.write_text(json.dumps(data))

        # Reset mock for fresh calls
        mock_client.messages.create = AsyncMock(
            return_value=_make_response(json.dumps(FAKE_ROGER_RESPONSE))
        )

        asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        data = json.loads(trait_file.read_text())
        assert data["custom_field"] == "keep me"

    def test_key_order(self, trait_file, mock_client):
        """Output keys should be: positive_label, negative_label, description, instruction, questions, eval_prompt."""
        asyncio.run(
            regenerate_one(
                mock_client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        data = json.loads(trait_file.read_text())
        keys = list(data.keys())
        assert keys[0] == "positive_label"
        assert keys[1] == "negative_label"
        assert keys[2] == "description"
        assert keys[3] == "instruction"
        assert keys[4] == "questions"
        assert keys[5] == "eval_prompt"


class TestBuildChristinaInstructionPrompt:
    def test_substitutes_trait_and_description(self):
        result = build_christina_instruction_prompt(
            "sarcastic", "sincere", "This means using irony.", 5, 40
        )
        assert "<trait>\nsarcastic\n</trait>" in result
        assert "This means using irony." in result

    def test_parameterizes_counts(self):
        result = build_christina_instruction_prompt(
            "sarcastic", "sincere", "Desc.", 3, 20
        )
        assert "list of 3 instruction pairs" in result
        assert "Design 20 questions" in result
        assert "Generate 20 diverse questions" in result
        assert 'question 20' in result

    def test_eval_template_has_single_brace_placeholders(self):
        result = build_christina_instruction_prompt(
            "sarcastic", "sincere", "Desc.", 5, 40
        )
        assert "{TRAIT}" in result
        assert "{question}" in result
        assert "{answer}" in result
        # Should NOT have double braces (those are .format() escapes, not output)
        assert "{{TRAIT}}" not in result

    def test_json_format_has_single_braces(self):
        result = build_christina_instruction_prompt(
            "sarcastic", "sincere", "Desc.", 5, 40
        )
        idx = result.find("<output_format>")
        section = result[idx:]
        assert '{\n  "instruction"' in section
        assert '{"pos":' in section


FAKE_COMBINED_RESPONSE = {
    "instruction": FAKE_INSTRUCTIONS,
    "questions": FAKE_QUESTIONS,
    "eval_prompt": "You are evaluating whether the model's response displays the trait: sarcastic.",
}


@pytest.fixture
def christina_style(monkeypatch):
    """Set PROMPT_STYLE to Christina for the test, restore after."""
    monkeypatch.setattr(module, "PROMPT_STYLE", "Christina")


@pytest.fixture
def mock_client_combined() -> AsyncMock:
    """Mock client that returns a single combined response."""
    client = AsyncMock()
    client.messages.create = AsyncMock(
        return_value=_make_response(json.dumps(FAKE_COMBINED_RESPONSE))
    )
    return client


class TestRegenerateOneChristina:
    """Tests for regenerate_one with Christina prompt style."""

    def test_combined_call(self, trait_file, mock_client_combined, christina_style):
        result = asyncio.run(
            regenerate_one(
                mock_client_combined,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == FAKE_QUESTIONS
        # eval_prompt rebuilt deterministically, not from LLM response
        expected_eval = build_eval_prompt("arrogant", SAMPLE_DESCRIPTION)
        assert data["eval_prompt"] == expected_eval
        # Only one API call for combined
        assert mock_client_combined.messages.create.call_count == 1

    def test_instructions_only_discards_questions(
        self, trait_file, mock_client_combined, christina_style
    ):
        result = asyncio.run(
            regenerate_one(
                mock_client_combined,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=True,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        # Questions preserved from original file, not from LLM
        assert data["questions"] == SAMPLE_TRAIT["questions"]
        # Still only one API call (combined prompt, questions discarded)
        assert mock_client_combined.messages.create.call_count == 1

    def test_dry_run(self, trait_file, mock_client_combined, christina_style):
        original = trait_file.read_text()

        result = asyncio.run(
            regenerate_one(
                mock_client_combined,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=True,
            )
        )

        assert result.startswith("DRY-RUN")
        assert "Christina" in result
        assert trait_file.read_text() == original
        mock_client_combined.messages.create.assert_not_called()


@pytest.fixture
def jacob_style(monkeypatch):
    """Set PROMPT_STYLE to Jacob for the test, restore after."""
    monkeypatch.setattr(module, "PROMPT_STYLE", "Jacob")


@pytest.fixture
def mock_client_jacob() -> AsyncMock:
    """Mock client that returns separate instruction and question responses."""
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=[
            _make_response(json.dumps(FAKE_INSTRUCTIONS)),
            _make_response(json.dumps(FAKE_QUESTIONS)),
        ]
    )
    return client


class TestRegenerateOneJacob:
    """Tests for regenerate_one with Jacob prompt style (separate API calls)."""

    def test_separate_calls(self, trait_file, mock_client_jacob, jacob_style):
        result = asyncio.run(
            regenerate_one(
                mock_client_jacob,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == FAKE_QUESTIONS
        assert data["positive_label"] == "arrogant"
        assert data["negative_label"] == "humble"
        assert data["description"] == SAMPLE_DESCRIPTION
        assert mock_client_jacob.messages.create.call_count == 2

    def test_instructions_only(self, trait_file, jacob_style):
        client = AsyncMock()
        client.messages.create = AsyncMock(
            side_effect=[_make_response(json.dumps(FAKE_INSTRUCTIONS))]
        )

        result = asyncio.run(
            regenerate_one(
                client,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=True,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=False,
            )
        )

        assert result.startswith("OK")
        data = json.loads(trait_file.read_text())
        assert data["instruction"] == FAKE_INSTRUCTIONS
        assert data["questions"] == SAMPLE_TRAIT["questions"]
        assert client.messages.create.call_count == 1

    def test_dry_run(self, trait_file, mock_client_jacob, jacob_style):
        original = trait_file.read_text()

        result = asyncio.run(
            regenerate_one(
                mock_client_jacob,
                trait_file,
                n_variants=5,
                n_questions=40,
                instructions_only=False,
                model="test-model",
                semaphore=asyncio.Semaphore(10),
                temperature=1.0,
                force=True,
                dry_run=True,
            )
        )

        assert result.startswith("DRY-RUN")
        assert "Jacob" in result
        assert trait_file.read_text() == original
        mock_client_jacob.messages.create.assert_not_called()


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

    def test_regenerate_one_charges_tracker(self, trait_file):
        from assistant_axis.judge_pricing import MultiModelUsage

        resp = _make_response(json.dumps(FAKE_ROGER_RESPONSE))
        resp.usage = MagicMock(input_tokens=1200, output_tokens=3400)
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=resp)
        tracker = MultiModelUsage()
        result = asyncio.run(
            regenerate_one(
                client, trait_file, n_variants=5, n_questions=40,
                instructions_only=False, model="claude-sonnet-4-6",
                semaphore=asyncio.Semaphore(10), temperature=1.0,
                force=True, dry_run=False, usage=tracker,
            )
        )
        assert result.startswith("OK")
        assert tracker.n_calls == 1
        assert tracker.total_prompt_tokens == 1200
        assert tracker.total_completion_tokens == 3400
        assert list(tracker.per_model) == ["claude-sonnet-4-6"]
        assert tracker.total_cost_usd > 0

    def test_persist_usage_merges_into_existing_file(self, tmp_path):
        from assistant_axis.judge_pricing import MultiModelUsage

        path = tmp_path / "regeneration_usage.json"
        first = MultiModelUsage(); first.charge("claude-sonnet-4-6", 100, 200)
        module.persist_usage(first, path)
        second = MultiModelUsage(); second.charge("claude-sonnet-4-6", 10, 20)
        module.persist_usage(second, path)
        total = MultiModelUsage.load_or_create(path)
        assert total.n_calls == 2
        assert total.total_prompt_tokens == 110
        assert total.total_completion_tokens == 220

    def test_dry_run_and_default_do_not_need_a_tracker(self, trait_file, mock_client):
        # usage=None (the default) must remain a no-op for existing callers
        result = asyncio.run(
            regenerate_one(
                mock_client, trait_file, n_variants=5, n_questions=40,
                instructions_only=False, model="test-model",
                semaphore=asyncio.Semaphore(10), temperature=1.0,
                force=True, dry_run=False,
            )
        )
        assert result.startswith("OK")


class TestGeneratorProvenance:
    def test_generator_field_written(self, trait_file, mock_client, monkeypatch):
        monkeypatch.setattr(module, "PROMPT_STYLE", "Roger")
        monkeypatch.setattr(module, "USE_ANTONYM", True)
        asyncio.run(regenerate_one(
            mock_client, trait_file, n_variants=5, n_questions=40, instructions_only=False,
            model="test-model", semaphore=asyncio.Semaphore(10), temperature=1.0,
            force=True, dry_run=False,
        ))
        g = json.loads(trait_file.read_text())["generator"]
        assert g["style"] == "Roger" and g["model"] == "test-model" and g["use_antonym"] is True
        assert g["template_sha256"] == module.template_sha256("Roger") and len(g["template_sha256"]) == 12
        assert g["script"] == "regenerate_trait_instructions.py"

    def test_jacob_style_has_no_template_hash(self):
        assert module.template_sha256("Jacob") is None


# ---------------------------------------------------------------------------
# RogerV2: the draft trait rubric V2 (Sep 2026)
# ---------------------------------------------------------------------------

import re  # noqa: E402

V2_DEFINITION = "This means making a great deal of small wrongs and never letting one go."


@pytest.fixture
def v2_style(monkeypatch):
    monkeypatch.setattr(module, "PROMPT_STYLE", "RogerV2")
    monkeypatch.setattr(module, "USE_ANTONYM", True)


def _v2(neg="magnanimous", n_questions=40):
    return module.build_roger_v2_instruction_prompt("petty", neg, V2_DEFINITION, 5, n_questions)


def _v2_examples():
    """Every example instruction in the template, as (side, text)."""
    blocks = re.findall(r"<example_pairs>(.*?)</example_pairs>", module._ROGER_TEMPLATE_V2, re.S)
    return [m for b in blocks for m in re.findall(r'"(pos|neg)": "((?:[^"\\]|\\.)*?)"', b)]


class TestRogerV2Prompt:
    def test_substitutes_the_trait_and_carries_the_rules(self, v2_style):
        p = _v2()
        assert "<trait>\npetty\n</trait>" in p and V2_DEFINITION in p
        assert "a person who has the opposite trait: magnanimous." in p
        for rule in (
            "Open every instruction by telling the model who to be, and open each",
            "Use the ones that suit the trait",
            "Do not open with a plain command",
            "open each of the 5 positive instructions in a different way",
            '"Become someone who ..."',
            '"From now on, you are someone who ..."',
            "The model is to be the person, not to perform one",
            "often leaves the model answering as an ordinary assistant, without the trait, most of all when the trait is a fault",
            # Roger, 2026-10-01: the negatives feed the antonym check only, so beyond the opening they
            # need not mirror the positives (the opening sentence came back the same day)
            "A negative instruction opens in the same way as its positive",
            "they need not mirror the positives",
            "do the 5 positive instructions open in 5 different ways",
            "check the negative instructions: are they as strong and as definite as the positives",
            "The trait belongs to the person",
            "not a passing mood",
            "Do not mention a user, an assistant, or an AI",
            "State the trait plainly and at full strength",
            "The negative instruction is a real opposite",
            # Roger, 2026-09-30: the rule of drafts 1 to 8 with his addition, chosen over "take no
            # phrase of four or more words from it" (the same on every measure, shorter); halves the
            # instructions that repeat five words of the description (4.4% to 1.6%) at no cost to a
            # blind rating.  The self-check asks about it too, below.
            "Do not repeat the description's wording; say it in other words, and take no phrasing from it.",
            "has any phrase been taken from the description, and has anything been softened",
            # the fifth opening, named so that it is not read as covering "You are someone who ..."
            # (under a bare "You are ..." 52 of 100 files used "You are someone who" twice)
            'and "You are ..." followed by a description of what the person is (as in "You are underhanded: ...")',
            "Say what the person does, in verbs",
            "in the second person, what they do, decide, think, or feel",
            "a task the person is carrying out on their own",
        ):
            assert rule in " ".join(p.split()), rule

    def test_the_rule_on_openings_claims_the_effect_and_not_a_cause(self, v2_style):
        # tested on Qwen, 2026-09-29: the effect is large; that the model takes the sentence for a
        # description of the asker shows in fewer than one answer in ten
        p = " ".join(_v2().split())
        assert "description of the person asking" not in p and "describing someone else" not in p
        assert "does not tell the model who to be often produces no persona at all" in p

    def test_no_placeholder_is_left_unfilled(self, v2_style):
        for p in (_v2(), _v2(neg="non-petty")):
            assert not re.search(r"\{[A-Za-z_]+\}", p.replace("{question}", "").replace("{answer}", "")
                                 .replace("{TRAIT}", "").replace("{TRAIT_DESCRIPTION (IN YOUR OWN WORDS)}", ""))

    def test_a_placeholder_label_is_not_named(self, v2_style):
        p = _v2(neg="non-petty")
        assert "non-petty" not in p
        assert "a person who has the opposite trait. Write each instruction" in " ".join(p.split())

    def test_no_antonym_switch_leaves_the_opposite_unnamed(self, v2_style, monkeypatch):
        monkeypatch.setattr(module, "USE_ANTONYM", False)
        assert "magnanimous" not in _v2()

    def test_the_paragraph_on_verbs_and_particulars(self, v2_style):
        # Roger, 2026-09-30: aligned with the role rubric (particulars welcome and varied across the
        # five, no invented reason) in place of the ban of drafts 3 to 8; it was a switch
        # (--no-concrete) while under test and is now part of the template
        on = " ".join(_v2().split())
        assert ("Say what the person does, in verbs, rather than naming an attitude, an approach, or a style. "
                "Particulars are welcome where the description allows them; vary them across the 5 pairs so that "
                "together they span the trait rather than narrow it to one occasion. Do not give the trait a reason "
                "that the description does not contain.") in on
        assert "Do not invent" not in on and "{CONCRETE" not in on
        assert ("does it open by telling the model who to be, does it say what the person does, has any phrase "
                "been taken from the description, and has anything been softened") in on
        assert "across the 4 pairs" in " ".join(_v2(n_variants=4).split()) if "n_variants" in _v2.__code__.co_varnames else True

    def test_question_quotas_are_a_fifth_each(self, v2_style):
        p = " ".join(_v2().split())
        assert "At least 8 of the questions should pose a choice between two courses of action" in p
        # the pilot's generator read "two named options" as a call for the labels
        assert 'no labels such as "Option A"' in p and "named options" not in p
        # the development sample had questions that said "Both options cost you something"
        assert "do not add a sentence saying that there are costs" in p
        # "Up to 8" produced a median of one to three; a quota has to be asked for
        assert "About 8 should instead come from someone who describes a problem of their own, in the first person" in p
        p20 = " ".join(_v2(n_questions=20).split())
        assert "At least 4 of the questions" in p20 and "About 4 should instead" in p20 and '"question 20"' in p20

    def test_eval_template_and_json_format_have_single_braces(self, v2_style):
        p = _v2()
        assert "{question}" in p and "{answer}" in p and "{{" not in p and "}}" not in p
        assert '{"pos": "positive instruction 1", "neg": "negative instruction 1"}' in p

    def test_reasoning_comes_before_the_score(self, v2_style):
        p = _v2()
        assert p.index("First, briefly reason") < p.index("SCORE: <integer from 0 to 100>")
        assert "just the number" not in p


class TestRogerV2Examples:
    """The generator copies what it is shown, so the examples must obey the
    rubric's own rules."""

    def test_there_are_twelve_in_six_pairs(self):
        ex = _v2_examples()
        assert [s for s, _ in ex] == ["pos", "neg"] * 6

    # The last one names the trait and goes on in the same sentence (Roger, 2026-09-29: "You are
    # underhanded: you go ..." reads better than the bare "You are underhanded. You go ...").  On
    # Qwen the join made no difference (30 faults, the same content: bare 42.5%, colon 40.0%,
    # merged with a comma 43.2%), so the choice is one of writing.
    OPENINGS = (r"You are someone who habitually ", r"You are someone who ", r"From now on, you are someone who ",
                r"Be someone who ", r"Become someone who ", r"You are [a-z-]+[:,] ")

    def _opening(self, text):
        for k, rx in enumerate(self.OPENINGS):
            if re.match(rx, " ".join(text.split())):
                return k
        return None

    def test_each_opens_by_telling_the_model_who_to_be(self):
        # a plain command was among them until the test on Qwen: 25% on faults
        for _, text in _v2_examples():
            assert self._opening(text) is not None, text

    def test_none_opens_with_a_statement_about_the_person(self):
        for _, text in _v2_examples():
            assert not re.match(r"(?i)(you have|you believe|you want|you tend|you always|you never|your |when )", text), text

    def test_negatives_are_written_on_their_own_terms(self):
        # Roger, 2026-10-01: the negatives feed the antonym check only (the extraction reads the
        # positives), so mirroring the positive is a constraint for nothing; the examples show the
        # freedom: every negative still says who to be, and not every pair shares an opening
        ex = [t for _, t in _v2_examples()]
        assert all(self._opening(neg) is not None for neg in ex[1::2])
        assert any(self._opening(pos) != self._opening(neg) for pos, neg in zip(ex[0::2], ex[1::2]))

    def test_the_six_pairs_open_in_six_ways(self):
        # the generator copies the frames it is shown: the pilot of the first draft, whose
        # examples used three, gave every file the same three in the same order
        ex = [t for _, t in _v2_examples()]
        assert len({self._opening(pos) for pos in ex[0::2]}) == 6

    def test_one_positive_names_its_trait_to_show_that_opening(self):
        ex = [" ".join(t.split()) for _, t in _v2_examples()]
        pos = [t for t in ex[0::2] if re.search(r"\b(long-winded|corner-cutting|underhanded)\b", t)]
        assert len(pos) == 1 and re.match(r"You are underhanded[:,] ", pos[0])
        neg = [t for t in ex[1::2] if re.search(r"\b(terse|painstaking|aboveboard)\b", t)]
        assert all(re.match(r"You are (terse|painstaking|aboveboard)[:,] ", t) for t in neg)

    def test_no_example_tells_the_model_to_play_a_part(self):
        # Roger, 2026-09-29: the model is to be the person; role-play openings score higher on Qwen
        # and their answers are the most theatrical
        for _, text in _v2_examples():
            assert not re.match(r"(?i)(act as|behave like|play|take on|adopt|imagine|pretend)\b", text), text

    def test_the_habit_wording_is_shown_after_who_to_be_and_for_a_style(self):
        # Roger, 2026-09-29; on Qwen "You are someone who habitually ..." kept 62% on faults and 94% on
        # styles, where the same words as an opening ("You habitually ...") kept 9% on faults
        ex = [" ".join(t.split()) for _, t in _v2_examples()]
        habit = [t for t in ex if "habitually" in t]
        assert habit == [ex[0]] and ex[0].startswith("You are someone who habitually ")   # the first positive, a way of speaking

    def test_length_is_inside_the_stated_range(self):
        # Roger, 2026-10-01: the rule says 20 to 30 words and the examples are the untrimmed ones of drafts 5
        # to 9 (the generator writes about four words more than it is shown: "15 to 25" with 20-to-25-word
        # examples gave 28 words and cost three points of effectiveness; "20 to 40" with these gave 38).  The
        # two long-winded positives may run a little over, as suits the trait; the rest are within 30.
        lengths = [(len(" ".join(text.split()).split()), text) for _, text in _v2_examples()]
        assert all(20 <= n <= 33 for n, _ in lengths), lengths
        assert sum(n > 30 for n, _ in lengths) <= 3, lengths

    def test_no_chat_frame_and_no_hedges(self):
        for _, text in _v2_examples():
            flat = " ".join(text.split())
            assert not re.search(r"\b(user|users|assistant|AI|chatbot|response|responses)\b", flat), flat
            assert not re.search(r"\b(appropriate|appropriately|healthy|balanced|sometimes|may|can|overly|too|"
                                 r"tends?|tendency)\b", flat, re.I), flat

    def test_none_urges_the_trait_on_others(self):
        for _, text in _v2_examples():
            assert not re.search(r"\b(encourag\w+|urg\w+|advis\w+|recommend\w*|tell (others|people) to)\b", text, re.I), text

    def test_the_example_traits_are_not_in_the_corpus(self):
        from assistant_axis.entity_id import default_data_dir
        d = default_data_dir() / "traits" / "instructions"
        if not d.is_dir():
            pytest.skip("corpus not found")
        for stem in ("long_winded", "terse", "corner_cutting", "painstaking", "underhanded", "aboveboard"):
            assert not (d / f"{stem}.json").exists(), stem


class TestCopiedFromExamples:
    TERSE = ("You are direct and brief. When you write or speak, you answer in the fewest words that will "
             "do the job, and stop, and you never elaborate.")

    def test_a_run_from_an_example_is_reported(self):
        found = module.copied_from_examples([{"pos": self.TERSE, "neg": "You are expansive."}], "RogerV2")
        assert found == [(0, "pos", "in the fewest words that will do the job and")]   # the example says "stops"

    def test_an_opening_frame_is_not(self):
        # "Take on the character of someone who" is seven words, and the rubric offers it
        pair = {"pos": "From now on, you are someone who shouts. You raise your voice until others give in.",
                "neg": "Be someone who does the asking quietly and takes no for an answer."}
        assert module.copied_from_examples([pair], "RogerV2") == []

    def test_what_follows_a_shared_frame_still_counts(self):
        pair = {"pos": "x", "neg": "From now on, you are someone who checks everything twice: you read the whole "
                                   "document before signing, whatever the job."}
        assert module.copied_from_examples([pair], "RogerV2") == [
            (0, "neg", "checks everything twice you read the whole document before signing")]

    def test_a_run_does_not_span_two_examples(self):
        ex = module._example_instructions("RogerV2")
        assert len(ex) == 12 and ex[0].startswith("You are someone who habitually takes")
        # the end of one example followed by the start of the next
        joined = " ".join(ex[0].split()[-4:] + ex[1].split()[:4])
        assert module.copied_from_examples([{"pos": joined, "neg": "x"}], "RogerV2") == []

    def test_the_v1_example_is_found_in_the_v1_template(self):
        pair = {"pos": "Your responses should be impolite or harsh. Do not soften your language.", "neg": "x"}
        assert [(k, s) for k, s, _ in module.copied_from_examples([pair], "Christina")] == [(0, "pos")]

    def test_a_style_without_a_template_reports_nothing(self):
        assert module.copied_from_examples([{"pos": self.TERSE, "neg": self.TERSE}], "Jacob") == []

    def test_the_status_line_says_so(self, trait_file, mock_client, v2_style, monkeypatch, capsys):
        monkeypatch.setattr(module, "copied_from_examples", lambda instr, style: [(2, "neg", "a b c d e f g")])
        result = asyncio.run(regenerate_one(
            mock_client, trait_file, n_variants=5, n_questions=40, instructions_only=False,
            model="test-model", semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
        ))
        assert result.startswith("OK") and result.endswith("1 copied from the examples")
        assert "instruction 2 neg repeats the template's example" in capsys.readouterr().err


class TestRogerV2Dispatch:
    def test_regenerate_one_sends_the_v2_prompt_and_records_it(self, trait_file, mock_client, v2_style):
        result = asyncio.run(regenerate_one(
            mock_client, trait_file, n_variants=5, n_questions=40, instructions_only=False,
            model="test-model", semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False,
        ))
        assert result.startswith("OK")
        assert mock_client.messages.create.call_count == 1
        sent = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "Open every instruction by telling the model who to be" in " ".join(sent.split())
        assert "opposite trait: humble" in sent
        g = json.loads(trait_file.read_text())["generator"]
        assert g["style"] == "RogerV2" and "concrete" not in g and g["use_antonym"] is True
        assert g["template_sha256"] == module.template_sha256("RogerV2")

    def test_v1_provenance_is_unchanged(self, monkeypatch):
        monkeypatch.setattr(module, "USE_ANTONYM", True)
        g = module.generator_provenance("Roger", "m", 1.0, 0)
        assert "concrete" not in g and g["use_antonym"] is True
        assert module.generator_provenance("Christina", "m", 1.0, 0)["use_antonym"] is None

    def test_template_hashes_are_distinct_and_v1_is_untouched(self):
        hashes = {s: module.template_sha256(s) for s in ("Christina", "Roger", "RogerV2")}
        assert len(set(hashes.values())) == 3
        # the hash carried by every trait file generated in September 2026
        assert "impolite" in _ROGER_TEMPLATE_V1 and "thanking the user" in _ROGER_TEMPLATE_V1

    def test_default_style_is_v2_and_v1_is_a_flag_away(self):
        # Roger, 2026-10-01: RogerV2 is the rubric in use; --style Roger is the May 2026 production
        # rubric, kept for comparison and rollback
        args = module.parse_args(["--traits", "arrogant"])
        assert args.style == "RogerV2" and args.antonym is True
        assert module.DEFAULT_PROMPT_STYLE == "RogerV2"
        assert module.parse_args(["--traits", "arrogant", "--style", "Roger"]).style == "Roger"
        with pytest.raises(SystemExit):   # stripped 2026-10-01, with its Step 1 substitution
            module.parse_args(["--traits", "arrogant", "--style", "Roger", "--use-original-step-one"])
        assert not hasattr(module, "USE_ORIGINAL_STEP_ONE") and not hasattr(module, "_replace_step_one")

    def test_parse_args_accepts_v2_and_its_switches(self):
        args = module.parse_args(["--traits", "arrogant", "--style", "RogerV2", "--no-antonym"])
        assert args.style == "RogerV2" and args.antonym is False
        with pytest.raises(SystemExit):   # the switch of 2026-09-29/30 is gone
            module.parse_args(["--traits", "arrogant", "--style", "RogerV2", "--no-concrete"])
        assert module.parse_args(["--traits", "a", "--style", "RogerV2"]).antonym is True

    def test_traits_dir_points_the_run_at_a_staging_copy(self, tmp_path, monkeypatch, capsys):
        corpus, stage = tmp_path / "corpus", tmp_path / "stage"
        for d in (corpus, stage):
            d.mkdir()
            (d / "arrogant.json").write_text(json.dumps(SAMPLE_TRAIT))
        (stage / "only_staged.json").write_text(json.dumps(SAMPLE_TRAIT))
        monkeypatch.setattr(module, "TRAITS_DIR", corpus)
        module.main(["--traits", "only_staged", "--traits-dir", str(stage), "--dry-run", "--force"])
        err = capsys.readouterr().err
        assert "not the corpus" in err and "DRY-RUN" in err
        assert module.TRAITS_DIR == stage.resolve()
        assert module.parse_args(["--traits", "a"]).traits_dir is None

    def test_combined_dispatch(self, v2_style):
        assert "impolite" in module.build_combined_prompt("Roger", "petty", "magnanimous", V2_DEFINITION, 5, 40)
        assert "long-winded" in module.build_combined_prompt("RogerV2", "petty", "magnanimous", V2_DEFINITION, 5, 40)
        with pytest.raises(ValueError):
            module.build_combined_prompt("Jacob", "petty", "magnanimous", V2_DEFINITION, 5, 40)


# ---------------------------------------------------------------------------
# Batch mode (--batch)
# ---------------------------------------------------------------------------

from types import SimpleNamespace  # noqa: E402


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
        result.message = _message(text if text is not None else json.dumps(FAKE_ROGER_RESPONSE))
    return SimpleNamespace(custom_id=stem, result=result)


def _counts(**kw):
    base = dict(succeeded=0, errored=0, expired=0, canceled=0, processing=0)
    base.update(kw)
    return SimpleNamespace(**base)


@pytest.fixture
def batch_setup(tmp_path, monkeypatch):
    stage = tmp_path / "stage"
    stage.mkdir()
    for stem in ("arrogant", "petty", "sloppy"):
        (stage / f"{stem}.json").write_text(json.dumps(dict(SAMPLE_TRAIT, positive_label=stem, keep_me="yes")))
    client = MagicMock()
    client.messages.batches.create = AsyncMock(return_value=SimpleNamespace(id="msgbatch_test"))
    client.messages.batches.retrieve = AsyncMock(side_effect=[
        SimpleNamespace(processing_status="in_progress", request_counts=_counts(processing=3)),
        SimpleNamespace(processing_status="ended", request_counts=_counts(succeeded=2, errored=1)),
    ])
    client.messages.batches.results = AsyncMock(return_value=_Results([
        _entry("petty"), _entry("arrogant", text="not json at all"), _entry("sloppy", kind="errored")]))
    real_time = _make_response(json.dumps(FAKE_ROGER_RESPONSE))
    real_time.usage = SimpleNamespace(input_tokens=2000, output_tokens=3000)
    client.messages.create = AsyncMock(return_value=real_time)
    monkeypatch.setattr(module.anthropic, "AsyncAnthropic", lambda **kw: client)
    monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    monkeypatch.setattr(module, "TRAITS_DIR", stage)
    usage_json = tmp_path / "records" / "usage.json"
    usage_json.parent.mkdir()
    # the fake replies open every instruction the same way: the opening reroll is off except where tested
    args = ["--all", "--traits-dir", str(stage), "--style", "RogerV2", "--force", "--usage-json", str(usage_json),
            "--no-opening-reroll"]
    return SimpleNamespace(stage=stage, client=client, usage_json=usage_json, args=args)


class TestBatchRequests:
    def test_one_request_per_file_with_the_stem_as_its_id(self, tmp_path, v2_style):
        paths = []
        for stem in ("arrogant", "petty"):
            p = tmp_path / f"{stem}.json"
            p.write_text(json.dumps(dict(SAMPLE_TRAIT, positive_label=stem)))
            paths.append(p)
        requests, skipped = module.build_batch_requests(
            paths, n_variants=5, n_questions=40, instructions_only=False, model="claude-sonnet-4-6",
            temperature=1.0, thinking_budget=0, force=True)
        assert [r["custom_id"] for r in requests] == ["arrogant", "petty"] and skipped == []
        params = requests[1]["params"]
        assert params["model"] == "claude-sonnet-4-6" and params["max_tokens"] == 16384
        assert params["temperature"] == 1.0 and "stream" not in params
        assert "<trait>\npetty\n</trait>" in params["messages"][0]["content"]
        # the request is the one the real-time call sends
        assert params == module.combined_create_kwargs(
            "petty", "humble", SAMPLE_DESCRIPTION, 5, 40, "claude-sonnet-4-6", 1.0, 0)

    def test_files_that_need_nothing_are_skipped_without_force(self, tmp_path, v2_style):
        p = tmp_path / "arrogant.json"
        p.write_text(json.dumps(SAMPLE_TRAIT))
        requests, skipped = module.build_batch_requests(
            [p], n_variants=5, n_questions=40, instructions_only=False, model="m", temperature=1.0,
            thinking_budget=0, force=False)
        assert requests == [] and skipped[0].startswith("SKIP arrogant")

    def test_a_stem_that_cannot_be_an_id(self, tmp_path, v2_style):
        p = tmp_path / "bad stem.json"
        p.write_text(json.dumps(SAMPLE_TRAIT))
        with pytest.raises(ValueError, match="cannot be the id"):
            module.build_batch_requests([p], n_variants=5, n_questions=40, instructions_only=False, model="m",
                                        temperature=1.0, thinking_budget=0, force=True)

    def test_every_corpus_stem_can_be_an_id(self):
        from assistant_axis.entity_id import default_data_dir
        d = default_data_dir() / "traits" / "instructions"
        if not d.is_dir():
            pytest.skip("corpus not found")
        assert not [p.stem for p in d.glob("*.json") if not module.BATCH_ID_PATTERN.match(p.stem)]


class TestBatchRun:
    def test_submit_wait_collect_and_fill_in_real_time(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        assert b.client.messages.batches.create.call_count == 1
        sent = b.client.messages.batches.create.call_args.kwargs["requests"]
        assert sorted(r["custom_id"] for r in sent) == ["arrogant", "petty", "sloppy"]
        assert b.client.messages.batches.retrieve.call_count == 2
        # petty came from the batch; arrogant (unusable reply) and sloppy (errored) were asked for in real time
        assert b.client.messages.create.call_count == 2
        for stem, from_batch in (("petty", True), ("arrogant", False), ("sloppy", False)):
            d = json.loads((b.stage / f"{stem}.json").read_text())
            assert d["instruction"] == FAKE_INSTRUCTIONS and d["keep_me"] == "yes"
            assert d["generator"]["style"] == "RogerV2" and d["generator"].get("batch", False) is from_batch
        assert "1 from the batch, 2 in real time" in err and "request errored" in err
        assert "test-key-not-real" not in err

    def test_usage_is_kept_at_the_batch_price(self, batch_setup):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        usage = json.loads(b.usage_json.read_text())["per_model"]
        # two replies came back from the batch (one of them unusable, and still paid for)
        assert usage["claude-sonnet-4-6:batch"]["n_calls"] == 2
        assert usage["claude-sonnet-4-6:batch"]["cost_usd"] == pytest.approx(2 * (2000 * 1.5 + 3000 * 7.5) / 1e6)
        assert usage["claude-sonnet-4-6"]["n_calls"] == 2
        assert usage["claude-sonnet-4-6"]["cost_usd"] == pytest.approx(2 * (2000 * 3 + 3000 * 15) / 1e6)

    def test_the_batch_is_recorded_beside_the_usage_record(self, batch_setup):
        b = batch_setup
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        log = json.loads(module.batch_log_path(b.usage_json).read_text())
        assert len(log) == 1 and log[0]["id"] == "msgbatch_test" and log[0]["n_requests"] == 3
        assert log[0]["style"] == "RogerV2" and log[0]["template_sha256"] == module.template_sha256("RogerV2")
        assert log[0]["traits_dir"] == str(b.stage.resolve())

    def test_submit_without_waiting_then_collect_by_id(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--batch-no-wait", "--model", "claude-sonnet-4-6"])
        assert b.client.messages.batches.retrieve.call_count == 0
        assert "--batch-id msgbatch_test" in capsys.readouterr().err
        assert json.loads((b.stage / "petty.json").read_text())["instruction"] == SAMPLE_TRAIT["instruction"]
        module.main(b.args + ["--batch-id", "msgbatch_test", "--model", "claude-sonnet-4-6"])
        assert b.client.messages.batches.create.call_count == 1  # not submitted again
        assert json.loads((b.stage / "petty.json").read_text())["instruction"] == FAKE_INSTRUCTIONS

    def test_a_dry_run_submits_nothing(self, batch_setup, capsys):
        b = batch_setup
        module.main(b.args + ["--batch", "--dry-run"])
        assert b.client.messages.batches.create.call_count == 0
        assert "Batch: 3 request(s), 0 file(s) skipped" in capsys.readouterr().err

    def test_batch_is_refused_for_the_two_call_style(self, batch_setup):
        b = batch_setup
        args = [a if a != "RogerV2" else "Jacob" for a in b.args]
        with pytest.raises(SystemExit, match="one call per trait"):
            module.main(args + ["--batch"])

    def test_real_time_is_the_default(self):
        args = module.parse_args(["--traits", "arrogant"])
        assert args.batch is False and args.batch_id is None and args.batch_no_wait is False
        assert args.batch_poll == module.DEFAULT_BATCH_POLL_SECONDS


# ---------------------------------------------------------------------------
# The opening reroll (2026-10-06): a set whose positives do not open in
# n_variants different ways is generated again, once
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _opening_reroll_off(monkeypatch):
    """The fake replies above open every instruction the same way and the
    older tests count calls, so the reroll is off unless a test turns it on."""
    monkeypatch.setattr(module, "OPENING_REROLL", False)


FIVE_OPENINGS = ["Be someone who sulks.", "Become someone who sulks.", "From now on, you are someone who sulks.",
                 "You are someone who sulks.", "You are petty: you sulk."]
FOUR_OPENINGS = FIVE_OPENINGS[:3] + ["You are someone who broods.", "You are someone who sulks."]


def _combined_reply(pos_openings):
    instr = [{"pos": p, "neg": f"Neg {i}."} for i, p in enumerate(pos_openings)]
    return _make_response(json.dumps({"instruction": instr, "questions": FAKE_QUESTIONS, "eval_prompt": "x"}))


class TestOpeningReroll:
    def run(self, client, trait_file):
        return asyncio.run(regenerate_one(
            client, trait_file, n_variants=5, n_questions=40, instructions_only=False, model="m",
            semaphore=asyncio.Semaphore(10), temperature=0.7, force=True, dry_run=False))

    def test_the_count_uses_the_audit_classifier(self):
        assert module.distinct_openings([{"pos": p} for p in FIVE_OPENINGS]) == 5
        assert module.distinct_openings([{"pos": p} for p in FOUR_OPENINGS]) == 4

    def test_a_doubled_opening_brings_a_second_call_and_the_better_set(self, trait_file, v2_style, monkeypatch, capsys):
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_combined_reply(FOUR_OPENINGS), _combined_reply(FIVE_OPENINGS)])
        result = self.run(client, trait_file)
        assert client.messages.create.call_count == 2 and "generated again for the openings" in result
        d = json.loads(trait_file.read_text())
        assert [p["pos"] for p in d["instruction"]] == FIVE_OPENINGS
        assert d["generator"]["opening_rerolls"] == 1
        assert "4 distinct openings of 5; generating again" in capsys.readouterr().err

    def test_still_short_keeps_the_better_set_and_warns(self, trait_file, v2_style, monkeypatch, capsys):
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        two = [FOUR_OPENINGS[0], FOUR_OPENINGS[3]] + [FOUR_OPENINGS[0]] * 3
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_combined_reply(FOUR_OPENINGS), _combined_reply(two)])
        self.run(client, trait_file)
        d = json.loads(trait_file.read_text())
        assert [p["pos"] for p in d["instruction"]] == FOUR_OPENINGS and d["generator"]["opening_rerolls"] == 1
        assert "still 4 distinct openings after a second generation" in capsys.readouterr().err

    def test_one_call_when_off_or_under_another_style(self, trait_file, v2_style, monkeypatch):
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_combined_reply(FOUR_OPENINGS))
        self.run(client, trait_file)                       # OPENING_REROLL is off (autouse)
        assert client.messages.create.call_count == 1
        assert "opening_rerolls" not in json.loads(trait_file.read_text())["generator"]
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        monkeypatch.setattr(module, "PROMPT_STYLE", "Roger")   # not a style whose rubric asks for it
        self.run(client, trait_file)
        assert client.messages.create.call_count == 2

    def test_the_switch(self):
        assert module.parse_args(["--traits", "x"]).opening_reroll is True
        assert module.parse_args(["--traits", "x", "--no-opening-reroll"]).opening_reroll is False


class TestOpeningRerollInBatch:
    def test_a_batch_reply_that_fails_the_check_is_redone_in_real_time(self, batch_setup, capsys):
        b = batch_setup
        module.main([a for a in b.args if a != "--no-opening-reroll"] + ["--batch", "--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        # petty's batch reply opens every instruction the same way: not written from the batch
        assert "petty: 1 distinct openings of 5; generated again in real time" in err
        assert "0 from the batch, 3 in real time" in err
        d = json.loads((b.stage / "petty.json").read_text())
        assert d["generator"].get("batch", False) is False and d["generator"]["opening_rerolls"] == 1


class TestReplyCounts:
    """A reply with the wrong number of pairs or questions is refused when the
    counts are given, so the retry loop asks again (2026-10-07)."""

    def test_counts_are_checked_only_when_given(self):
        reply = json.dumps({"instruction": FAKE_INSTRUCTIONS, "questions": FAKE_QUESTIONS[:39], "eval_prompt": "x"})
        assert len(module.validated_combined(reply, "arrogant")["questions"]) == 39
        with pytest.raises(ValueError, match="39 questions, not 40"):
            module.validated_combined(reply, "arrogant", n_variants=5, n_questions=40)
        with pytest.raises(ValueError, match="5 instruction pairs, not 6"):
            module.validated_combined(reply, "arrogant", n_variants=6, n_questions=39)

    def test_a_short_reply_is_asked_for_again(self, trait_file, v2_style, monkeypatch):
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        short = json.dumps({"instruction": FAKE_INSTRUCTIONS, "questions": FAKE_QUESTIONS[:39], "eval_prompt": "x"})
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_make_response(short), _make_response(json.dumps(FAKE_ROGER_RESPONSE))])
        result = asyncio.run(regenerate_one(
            client, trait_file, n_variants=5, n_questions=40, instructions_only=False, model="m",
            semaphore=asyncio.Semaphore(10), temperature=0.7, force=True, dry_run=False))
        assert client.messages.create.call_count == 2 and result.startswith("OK")
        assert len(json.loads(trait_file.read_text())["questions"]) == 40


# ---------------------------------------------------------------------------
# Refusals (2026-10-08): recorded in generation_refusals.jsonl, never retried
# ---------------------------------------------------------------------------

from assistant_axis.judge_pricing import MultiModelUsage  # noqa: E402
from data_analysis import generation_refusals as refusals  # noqa: E402
from data_analysis.generation_refusals import GenerationRefusal  # noqa: E402


@pytest.fixture(autouse=True)
def _refusals_jsonl(tmp_path, monkeypatch):
    """No test writes into data/traits/generation_refusals.jsonl."""
    path = tmp_path / "refusals" / refusals.REFUSALS_NAME
    monkeypatch.setattr(module, "DEFAULT_REFUSALS_JSONL", path)
    return path


DECLINE = ("I can't help write instructions that would have a model act out this trait, because doing so could "
           "produce content that demeans people. " + "I would be glad to help with a related task instead. " * 6)


def _refused_reply(text=None, stop_reason="refusal"):
    """A reply as the SDK returns it: ``stop_reason`` "refusal" with no content,
    or a prose decline that ended normally."""
    content = [] if text is None else [SimpleNamespace(type="text", text=text)]
    return SimpleNamespace(content=content, stop_reason=stop_reason,
                           usage=SimpleNamespace(input_tokens=1500, output_tokens=0 if text is None else 60))


def _records(path):
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []


class TestDeclineDetection:
    @pytest.mark.parametrize("text", [
        "I can't help with this request.",
        "I'm sorry, but I won't write persona instructions for this trait.",
        "I appreciate the research framing, but I’m not able to write these.",   # typographic apostrophe
        "**I cannot create content that portrays this.**\n\nInstead, here is ...",
        "I don't feel comfortable writing instructions that ...",
    ])
    def test_a_decline(self, text):
        assert refusals.reads_as_decline(text)

    @pytest.mark.parametrize("text", [
        json.dumps({"instruction": [{"pos": "You are someone who says I can't to everything.", "neg": "x"}]}),
        "```json\n" + json.dumps({"instruction": [], "note": "I won't"}) + "\n```",
        json.dumps(["I cannot sit still.", "I will not wait."]),
        "Here is the set you asked for. I can't promise it is perfect.",   # not in the first sentence
        "not json at all",
        "",
    ])
    def test_not_a_decline(self, text):
        assert not refusals.reads_as_decline(text)

    def test_a_reply_without_a_stop_reason_or_a_decline_is_not_a_refusal(self):
        assert refusals.refusal_in(_make_response("not json at all"), "arrogant") is None   # MagicMock stop_reason
        r = refusals.refusal_in(_refused_reply(), "arrogant")
        assert r.stop_reason == "refusal" and r.reply_excerpt == "" and "no text" in r.excerpt_line


BROWN_HAIRED_ERROR = ("ERROR: 'Brown-haired' is a physical descriptor, not a personality trait. Writing instructions "
                      "would require fabricating false stereotypes. " + "It would corrupt any research using it. " * 6)


class TestErrorSentinel:
    """Housekeeping item 9 (2026-10-08, brown-haired): the generator refused by
    writing "ERROR: ..." into a field of an otherwise well-formed JSON reply,
    which the detector missed, so it was retried five times, twice."""

    @pytest.mark.parametrize("reply, excerpt_start", [
        (dict(FAKE_ROGER_RESPONSE, eval_prompt=BROWN_HAIRED_ERROR), "eval_prompt: ERROR: 'Brown-haired'"),
        (dict(FAKE_ROGER_RESPONSE, instruction=[], questions=[], eval_prompt="  " + BROWN_HAIRED_ERROR),
         "eval_prompt:   ERROR:"),
        (dict(FAKE_ROGER_RESPONSE, instruction=FAKE_INSTRUCTIONS[:2] + [{"pos": "ERROR: no.", "neg": "x"}]),
         "instruction[2].pos: ERROR: no."),
    ], ids=["eval_prompt", "empty_set", "nested"])
    def test_a_json_field_opening_error_is_a_refusal(self, reply, excerpt_start):
        for text in (json.dumps(reply), "```json\n" + json.dumps(reply, indent=2) + "\n```",
                     "Let me think about this first.\n\n```json\n" + json.dumps(reply) + "\n```"):
            r = refusals.refusal_in(_refused_reply(text, stop_reason="end_turn"), "brown-haired")
            assert r is not None and r.stop_reason == "end_turn" and r.label == "brown-haired"
            assert r.reply_excerpt.startswith(excerpt_start) and len(r.reply_excerpt) <= refusals.EXCERPT_CHARS

    def test_a_reply_that_opens_with_the_sentinel_is_a_refusal(self):
        r = refusals.refusal_in(_refused_reply("ERROR: this is not a personality trait.", "end_turn"), "x")
        assert r.reply_excerpt == "ERROR: this is not a personality trait."

    @pytest.mark.parametrize("text", [
        json.dumps(dict(FAKE_ROGER_RESPONSE, eval_prompt="error: lowercase is not the sentinel")),
        json.dumps(dict(FAKE_ROGER_RESPONSE, eval_prompt="Score 0 on an ERROR: the sentinel opens the value only")),
        json.dumps(FAKE_ROGER_RESPONSE),
        '{"instruction": [], "eval_prompt": "ERROR: but the JSON is broken"',     # left to the reader's retries
        "not json at all",
    ])
    def test_not_a_sentinel(self, text):
        assert refusals.refusal_in(_refused_reply(text, stop_reason="end_turn"), "x") is None

    def test_regeneration_records_it_once_and_leaves_the_file(self, trait_file, v2_style, monkeypatch,
                                                              _refusals_jsonl):
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        before = trait_file.read_text()
        reply = _refused_reply(json.dumps(dict(FAKE_ROGER_RESPONSE, eval_prompt=BROWN_HAIRED_ERROR)), "end_turn")
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=reply)
        with pytest.raises(GenerationRefusal):
            asyncio.run(regenerate_one(
                client, trait_file, n_variants=5, n_questions=40, instructions_only=False,
                model="claude-sonnet-4-6", semaphore=asyncio.Semaphore(10), temperature=1.0, force=True,
                dry_run=False))
        assert client.messages.create.call_count == 1 and trait_file.read_text() == before
        [rec] = _records(_refusals_jsonl)
        assert rec["stop_reason"] == "end_turn" and rec["reply_excerpt"].startswith("eval_prompt: ERROR:")


class TestProsePreface:
    """Housekeeping item 9 (2026-10-08, brown-eyed): usable instructions behind
    a paragraph of deliberation broke the parse and were retried as errors."""

    PREFACE = ("I need to think about how to write these. Eye colour is physical, so the instructions should "
               "stay with the body: the color in the mirror, in photographs {not personality}.\n\nHere is the set:")

    def test_strip_prose_preface(self):
        body = json.dumps(FAKE_ROGER_RESPONSE, indent=2)
        assert refusals.strip_prose_preface(self.PREFACE + "\n" + body) == (body, self.PREFACE)
        assert refusals.strip_prose_preface(self.PREFACE + "\n```json\n" + body)[0] == body
        for whole in (body, json.dumps(FAKE_QUESTIONS), "no braces here", ""):
            assert refusals.strip_prose_preface(whole) == (whole, "")
        assert refusals.strip_prose_preface('Note {x} then {"a": 1}') == ('{x} then {"a": 1}', "Note")

    def test_validated_combined_reads_past_the_preface(self, capsys):
        text = self.PREFACE + "\n\n```json\n" + json.dumps(FAKE_ROGER_RESPONSE, indent=2) + "\n```"
        data = module.validated_combined(text, "brown-eyed", 5, 40)
        assert data["instruction"] == FAKE_INSTRUCTIONS and data["questions"] == FAKE_QUESTIONS
        err = capsys.readouterr().err
        assert f"skipped {len(self.PREFACE) + len(chr(10) * 2 + '```json')} characters of prose" in err
        assert "before the JSON for brown-eyed" in err

    def test_a_reply_with_no_preface_reads_as_before(self, capsys):
        data = module.validated_combined("```json\n" + json.dumps(FAKE_ROGER_RESPONSE) + "\n```", "x", 5, 40)
        assert data["eval_prompt"] == FAKE_ROGER_RESPONSE["eval_prompt"]
        assert "prose before the JSON" not in capsys.readouterr().err

    def test_regeneration_uses_the_set_at_the_first_try(self, trait_file, v2_style, _refusals_jsonl):
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_make_response(
            self.PREFACE + "\n" + json.dumps(FAKE_ROGER_RESPONSE)))
        result = asyncio.run(regenerate_one(
            client, trait_file, n_variants=5, n_questions=40, instructions_only=False, model="m",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False))
        assert result.startswith("OK") and client.messages.create.call_count == 1
        assert json.loads(trait_file.read_text())["instruction"] == FAKE_INSTRUCTIONS
        assert not _refusals_jsonl.exists()


class TestRefusals:
    def run(self, client, trait_file, **kw):
        return asyncio.run(regenerate_one(
            client, trait_file, n_variants=5, n_questions=40, instructions_only=False, model="claude-sonnet-4-6",
            semaphore=asyncio.Semaphore(10), temperature=1.0, force=True, dry_run=False, **kw))

    @pytest.mark.parametrize("reply, stop_reason, excerpt", [
        (_refused_reply(), "refusal", ""),
        (_refused_reply(DECLINE, stop_reason="end_turn"), "end_turn", DECLINE[:300]),
    ], ids=["stop_reason", "prose_decline"])
    def test_raised_at_once_recorded_and_the_file_left_alone(self, trait_file, v2_style, monkeypatch,
                                                             _refusals_jsonl, reply, stop_reason, excerpt):
        monkeypatch.setattr(module.asyncio, "sleep", AsyncMock())
        before = trait_file.read_text()
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=reply)
        usage = MultiModelUsage()
        with pytest.raises(GenerationRefusal) as info:
            self.run(client, trait_file, usage=usage)
        assert client.messages.create.call_count == 1                 # not retried
        assert info.value.label == "arrogant" and info.value.stop_reason == stop_reason
        assert trait_file.read_text() == before
        assert usage.n_calls == 1                                      # the reply came back, so it is paid for
        [rec] = _records(_refusals_jsonl)
        assert len(DECLINE) > 300 and rec["reply_excerpt"] == excerpt
        assert {k: rec[k] for k in ("stem", "label", "kind", "model", "style", "stop_reason", "attempt")} == {
            "stem": "arrogant", "label": "arrogant", "kind": "trait", "model": "claude-sonnet-4-6",
            "style": "RogerV2", "stop_reason": stop_reason, "attempt": "live"}
        assert rec["template_sha256"] == module.template_sha256("RogerV2")
        assert module.datetime.datetime.fromisoformat(rec["refused_at"]).tzinfo is not None

    def test_a_json_reply_that_says_i_cant_is_not_a_refusal(self, trait_file, v2_style, _refusals_jsonl):
        instr = [dict(p, pos="You are someone who says I can't before trying anything.") for p in FAKE_INSTRUCTIONS]
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_make_response(json.dumps(dict(FAKE_ROGER_RESPONSE, instruction=instr))))
        assert self.run(client, trait_file).startswith("OK")
        assert json.loads(trait_file.read_text())["instruction"] == instr
        assert not _refusals_jsonl.exists()

    def test_the_two_call_style_does_not_retry_either(self, trait_file, jacob_style, _refusals_jsonl):
        client = AsyncMock()
        client.messages.create = AsyncMock(return_value=_refused_reply())
        with pytest.raises(GenerationRefusal):
            self.run(client, trait_file)
        assert client.messages.create.call_count == 1
        [rec] = _records(_refusals_jsonl)
        assert rec["style"] == "Jacob" and rec["template_sha256"] is None

    def test_a_refused_second_sample_keeps_the_first_set(self, trait_file, v2_style, monkeypatch, capsys,
                                                          _refusals_jsonl):
        monkeypatch.setattr(module, "OPENING_REROLL", True)
        client = AsyncMock()
        client.messages.create = AsyncMock(side_effect=[_combined_reply(FOUR_OPENINGS), _refused_reply()])
        assert self.run(client, trait_file).startswith("OK") and client.messages.create.call_count == 2
        assert [p["pos"] for p in json.loads(trait_file.read_text())["instruction"]] == FOUR_OPENINGS
        assert "the second generation was refused" in capsys.readouterr().err
        assert not _refusals_jsonl.exists()


class TestRefusalRunSummary:
    def test_counted_apart_from_errors_and_the_run_goes_on(self, batch_setup, capsys):
        b = batch_setup

        def reply(**kw):
            prompt = kw["messages"][0]["content"]
            if "<trait>\npetty\n</trait>" in prompt:
                return _refused_reply(DECLINE, stop_reason="end_turn")
            if "<trait>\nsloppy\n</trait>" in prompt:
                return _make_response("not json at all")             # asked for five times, then an error
            return _make_response(json.dumps(FAKE_ROGER_RESPONSE))
        b.client.messages.create = AsyncMock(side_effect=reply)
        module.main(b.args + ["--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        assert "REFUSED petty: I can't help write instructions" in err
        assert "Done: 1 processed, 0 skipped, 1 refused, 1 errors" in err
        assert b.client.messages.create.call_count == 1 + 1 + 5
        [rec] = _records(module.refusal_log_path(b.usage_json))
        assert rec["stem"] == "petty" and rec["attempt"] == "live"
        assert json.loads(b.usage_json.read_text())["n_calls"] == 7    # the refused reply is charged too


class TestRefusalInBatch:
    def test_a_refused_batch_reply_is_recorded_and_not_asked_for_again(self, batch_setup, capsys):
        b = batch_setup
        refused = lambda stem, msg: SimpleNamespace(custom_id=stem, result=SimpleNamespace(type="succeeded", message=msg))
        b.client.messages.batches.results = AsyncMock(return_value=_Results([
            _entry("petty"), refused("arrogant", _refused_reply()),
            refused("sloppy", _refused_reply(DECLINE, stop_reason="end_turn"))]))
        before = {s: (b.stage / f"{s}.json").read_text() for s in ("arrogant", "sloppy")}
        module.main(b.args + ["--batch", "--model", "claude-sonnet-4-6"])
        err = capsys.readouterr().err
        assert b.client.messages.create.call_count == 0               # nothing went to the real-time pass
        assert all((b.stage / f"{s}.json").read_text() == t for s, t in before.items())
        recs = _records(module.refusal_log_path(b.usage_json))
        assert [(r["stem"], r["attempt"], r["stop_reason"]) for r in recs] == [
            ("arrogant", "batch", "refusal"), ("sloppy", "batch", "end_turn")]
        assert "REFUSED arrogant: (no text; stop_reason refusal)" in err
        assert "1 processed (1 from the batch, 0 in real time), 0 skipped, 2 refused, 0 errors" in err
        assert json.loads(b.usage_json.read_text())["per_model"]["claude-sonnet-4-6:batch"]["n_calls"] == 3
