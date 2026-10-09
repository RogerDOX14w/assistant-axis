"""The instruction generators fill their prompts with the judge display form
of the labels (W19, Roger 2026-10-09: no exceptions), record it in the
``generator`` field as ``label_form``, and leave the template text (and so
the template hashes) and the stored labels unchanged."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import data_analysis.regenerate_role_instructions as roles
import data_analysis.regenerate_trait_instructions as traits

FIVE = [{"pos": f"Be someone who does thing {i}.", "neg": f"Become someone who avoids thing {i}."}
        for i in range(5)]
QUESTIONS = [f"Question {i}?" for i in range(40)]
STANDARD_TRAIT = {
    "positive_label": "careless (HEXACO)",
    "negative_label": "conscientious (HEXACO)",
    "description": "This means letting the room get messy and appointments slide.",
}


def _client(payload: dict) -> AsyncMock:
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text=json.dumps(payload))]
    resp.stop_reason = "end_turn"
    resp.usage = MagicMock(input_tokens=10, output_tokens=10)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


def test_template_text_is_untouched():
    """The hashes as they were before W19 (trait V2 adopted 2026-10-02, role
    V3 2026-10-03); W19 changes only the values filled in."""
    assert {s: traits.template_sha256(s) for s in ("Christina", "Roger", "RogerV2")} == {
        "Christina": "791482518555", "Roger": "87cdfe188478", "RogerV2": "9255dd3430ef"}
    assert {s: roles.template_sha256(s) for s in ("Christina", "Roger", "RogerV2", "RogerV3")} == {
        "Christina": "1258e2219126", "Roger": "1258e2219126", "RogerV2": "34cfa72295f6",
        "RogerV3": "977c98ac3463"}


class TestTraitGenerator:
    def test_prompt_labels(self):
        assert traits.prompt_labels(STANDARD_TRAIT) == ("careless (from HEXACO)", "conscientious (from HEXACO)")
        assert traits.prompt_labels({"positive_label": "ENFJ (MBTI)", "negative_label": "non-ENFJ (MBTI)"}) \
            == ("ENFJ (from the MBTI)", "non-ENFJ (from the MBTI)")
        plain = {"positive_label": "systems-thinker", "negative_label": "reductionist"}
        assert traits.prompt_labels(plain) == ("systems-thinker", "reductionist")

    def test_every_style_fills_in_the_judge_form(self):
        pos, neg = traits.prompt_labels(STANDARD_TRAIT)
        desc = STANDARD_TRAIT["description"]
        for style in traits.COMBINED_STYLES:
            prompt = traits.build_combined_prompt(style, pos, neg, desc, 5, 40)
            assert "careless (from HEXACO)" in prompt and "careless (HEXACO)" not in prompt, style
        assert "conscientious (from HEXACO)" in traits.build_combined_prompt("RogerV2", pos, neg, desc, 5, 40)
        assert "careless (from HEXACO)" in traits.build_jacob_instruction_prompt(pos, neg, desc, 5)
        assert "careless (from HEXACO)" in traits.build_questions_prompt(pos, neg, 40)

    def test_regeneration_sends_the_judge_form_and_keeps_the_stored_labels(self, tmp_path, monkeypatch):
        monkeypatch.setattr(traits, "PROMPT_STYLE", "RogerV2")
        monkeypatch.setattr(traits, "USE_ANTONYM", True)
        path = tmp_path / "careless_hexaco.json"
        path.write_text(json.dumps(STANDARD_TRAIT))
        client = _client({"instruction": FIVE, "questions": QUESTIONS, "eval_prompt": "x"})
        status = asyncio.run(traits.regenerate_one(
            client, path, n_variants=5, n_questions=40, instructions_only=False, model="m",
            semaphore=asyncio.Semaphore(2), temperature=1.0, force=True, dry_run=False))
        assert status.startswith("OK careless (HEXACO)")
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "careless (from HEXACO)" in sent and "careless (HEXACO)" not in sent
        assert "opposite trait: conscientious (from HEXACO)" in sent
        doc = json.loads(path.read_text())
        assert doc["positive_label"] == "careless (HEXACO)"
        assert doc["negative_label"] == "conscientious (HEXACO)"
        assert "**careless (from HEXACO)**. This means" in doc["eval_prompt"]
        assert doc["generator"]["label_form"] == "judge-display-v1"
        assert doc["generator"]["template_sha256"] == traits.template_sha256("RogerV2")

    def test_batch_requests_carry_the_judge_form(self, tmp_path, monkeypatch):
        monkeypatch.setattr(traits, "PROMPT_STYLE", "RogerV2")
        path = tmp_path / "careless_hexaco.json"
        path.write_text(json.dumps(STANDARD_TRAIT))
        requests, skipped = traits.build_batch_requests(
            [path], n_variants=5, n_questions=40, instructions_only=False, model="m",
            temperature=1.0, thinking_budget=0, force=True)
        assert not skipped
        assert "careless (from HEXACO)" in json.dumps(requests[0]["params"]["messages"])

    def test_provenance_records_the_label_form(self):
        assert traits.generator_provenance("RogerV2", "m", 1.0, 0)["label_form"] == "judge-display-v1"


class TestRoleGenerator:
    def test_prompt_name_is_the_judge_label(self):
        assert roles.role_prompt_name("devils_advocate") == "devil's advocate"
        assert roles.role_prompt_name("coral_reef") == "coral reef"
        # a standards role (none in the corpus yet) would take the long form
        # once its display override exists; without one it stays mechanical
        assert roles.role_prompt_name("the_fool_tarot") == "the fool tarot"

    def test_every_corpus_role_renders_as_before(self):
        """No role carries a standard's suffix, so every role prompt is unchanged."""
        stems = [p.stem for p in roles.ROLES_DIR.glob("*.json")]
        assert len(stems) > 100
        assert [s for s in stems if roles.role_prompt_name(s) != roles.role_display_name(s)] == []

    def test_regeneration_records_the_label_form(self, tmp_path, monkeypatch):
        monkeypatch.setattr(roles, "PROMPT_STYLE", "RogerV3")
        path = tmp_path / "devils_advocate.json"
        path.write_text(json.dumps({"description": "A devil's advocate is someone who argues."}))
        client = _client({"instruction": [{"pos": f"Become a devil's advocate {i}."} for i in range(5)],
                          "questions": QUESTIONS, "eval_prompt": "x"})
        asyncio.run(roles.regenerate_one(
            client, path, n_variants=5, n_questions=40, model="m", semaphore=asyncio.Semaphore(2),
            temperature=1.0, force=True, dry_run=False))
        doc = json.loads(path.read_text())
        assert doc["generator"]["label_form"] == "judge-display-v1"
        assert "**devil's advocate**" in doc["eval_prompt"]
        sent = client.messages.create.call_args.kwargs["messages"][0]["content"]
        assert "devil's advocate" in sent and "devils_advocate" not in sent
