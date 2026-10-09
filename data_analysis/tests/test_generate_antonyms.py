"""Tests for generate_antonyms.py: the classify call parses reasoning-first
JSON and ticks the usage tracker."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from assistant_axis.judge_pricing import MultiModelUsage
from data_analysis import generate_antonyms as module

INSTRUCTIONS = [{"pos": f"pos {i}", "neg": f"neg {i}"} for i in range(5)]
REPLY = {"reasoning": "the neg pole is humility", "negative_label": "humble", "antonym_score": 4}


def _client(text: str, usage=None) -> AsyncMock:
    resp = MagicMock()
    resp.content = [MagicMock(type="text", text=text)]
    resp.usage = usage if usage is not None else MagicMock(input_tokens=500, output_tokens=80)
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


class TestClassifyOne:
    def test_parses_reply_and_charges_usage(self):
        tracker = MultiModelUsage()
        result = asyncio.run(module.classify_one(
            _client(json.dumps(REPLY)), "arrogant", "Excessive confidence.", INSTRUCTIONS,
            asyncio.Semaphore(2), tracker,
        ))
        assert result["negative_label"] == "humble" and result["antonym_score"] == 4
        assert tracker.n_calls == 1
        assert tracker.total_prompt_tokens == 500 and tracker.total_completion_tokens == 80
        assert list(tracker.per_model) == [module.MODEL]

    def test_strips_fences_and_tolerates_no_tracker(self):
        text = "```json\n" + json.dumps(REPLY) + "\n```"
        result = asyncio.run(module.classify_one(
            _client(text), "arrogant", "Excessive confidence.", INSTRUCTIONS, asyncio.Semaphore(2),
        ))
        assert result["negative_label"] == "humble"

    def test_user_message_carries_definition_and_both_poles(self):
        msg = module.build_user_message("arrogant", "Excessive confidence.", INSTRUCTIONS)
        assert "positive_label: arrogant" in msg and "Definition: Excessive confidence." in msg
        assert "1. pos 0" in msg and "5. neg 4" in msg


class TestNamePos:
    """--name-pos: a label-blind call that names the pole the pos instructions describe."""

    POS_REPLY = {"reasoning": "all five push to change the world", "positive_name": "enterprising|driven"}

    def test_message_is_label_blind_and_pos_only(self):
        msg = module.build_pos_name_message(INSTRUCTIONS)
        assert "1. pos 0" in msg and "5. pos 4" in msg
        assert "neg" not in msg and "positive_label" not in msg and "Definition" not in msg

    def test_parses_reply_charges_usage_and_uses_its_own_prompt(self):
        tracker = MultiModelUsage()
        client = _client("```json\n" + json.dumps(self.POS_REPLY) + "\n```")
        result = asyncio.run(module.name_pos_one(client, INSTRUCTIONS, asyncio.Semaphore(2), tracker, "x"))
        assert result["positive_name"] == "enterprising|driven"
        assert tracker.n_calls == 1
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["system"] == module.POS_NAME_SYSTEM_PROMPT
        assert "arrogant" not in kwargs["messages"][0]["content"]

    def test_reply_without_the_field_is_retried_then_an_error_sentinel(self, monkeypatch):
        async def no_sleep(_):
            return None
        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        client = _client(json.dumps({"reasoning": "?", "negative_label": "x"}))
        result = asyncio.run(module.name_pos_one(client, INSTRUCTIONS, asyncio.Semaphore(2)))
        assert result["positive_name"] == "ERROR"
        assert client.messages.create.call_count == 5

    def test_flag_is_off_by_default(self):
        assert module.parse_args([]).name_pos is False
        assert module.parse_args(["--name-pos"]).name_pos is True


class TestTraitModeUnchanged:
    """The role mode (2026-10-09) must leave the trait check's system prompts
    byte-identical.  (The user message changed with W19, the same day: it
    names the trait in its judge display form, not its stem; see
    TestJudgeDisplayForm.)"""

    def test_trait_prompts_are_the_committed_ones(self):
        import hashlib
        sha = lambda s: hashlib.sha256(s.encode()).hexdigest()  # noqa: E731
        assert sha(module.SYSTEM_PROMPT) == "831ede1cfe1491924dc0647214284e50b61cd4f312d6d1fe29c95e05f774ffba"
        assert sha(module.POS_NAME_SYSTEM_PROMPT) == "f4bc50f0177b4426e48849bc6e9793661292d07f55a88432320a66f7f41baeba"

    def test_trait_defaults(self, monkeypatch):
        seen = {}

        async def fake_main_async(**kw):
            seen.update(kw)
        monkeypatch.setattr(module, "main_async", fake_main_async)
        module.main([])
        assert seen == {"trait_filter": None, "usage_json": module.DEFAULT_USAGE_JSON, "name_pos": False}
        assert module.DEFAULT_USAGE_JSON.parts[-2:] == ("traits", "antonym_check_usage.json")
        module.main(["--traits", "a", "b", "--usage-json", "x.json"])
        assert seen["trait_filter"] == ["a", "b"] and str(seen["usage_json"]) == "x.json"


class TestJudgeDisplayForm:
    """W19 (2026-10-09): the trait check shows the judge display form of the
    label (it showed the stem), and every result says so."""

    def test_prompt_label_of_a_file(self):
        assert module.trait_prompt_label("careless_hexaco", {"positive_label": "careless (HEXACO)"}) \
            == "careless (from HEXACO)"
        assert module.trait_prompt_label("systems_thinker", {"positive_label": "systems-thinker"}) \
            == "systems-thinker"
        assert module.trait_prompt_label("no_label_here", {}) == "no label here"

    def test_run_shows_the_judge_form_and_records_it(self, tmp_path, monkeypatch, capsys):
        client = _client(json.dumps(REPLY))
        monkeypatch.setattr(module.anthropic, "AsyncAnthropic", lambda: client)
        asyncio.run(module.main_async(trait_filter=["careless_hexaco", "patient"],
                                      usage_json=tmp_path / "usage.json"))
        out = json.loads(capsys.readouterr().out)
        assert list(out) == ["careless_hexaco", "patient"]
        assert out["careless_hexaco"]["prompt_form"] == module.PROMPT_FORM == "judge-display-v1"
        assert out["careless_hexaco"]["prompt_label"] == "careless (from HEXACO)"
        assert out["patient"]["prompt_label"] == "patient"
        firsts = sorted(c.kwargs["messages"][0]["content"].splitlines()[0]
                        for c in client.messages.create.call_args_list)
        assert firsts == ["positive_label: careless (from HEXACO)", "positive_label: patient"]


ROLE_INSTRUCTIONS = [{"pos": f"role pos {i}"} for i in range(5)]
ROLE_REPLY = {"reasoning": "a guardian protects what the destroyer ruins", "opposing_role": "guardian|protector",
              "opposition_score": 4}


class TestRoleMode:
    """--roles: the role-pair check names the opposing *role* from the
    description and the five pos instructions (roles have no neg side)."""

    def test_message_carries_name_description_and_pos_instructions(self):
        msg = module.build_role_message("devil's advocate", "Argues the other side.", ROLE_INSTRUCTIONS)
        assert msg.startswith("Role: devil's advocate\nDescription: Argues the other side.\n\nInstructions:\n")
        assert "1. role pos 0" in msg and "5. role pos 4" in msg
        assert "neg" not in msg and "positive_label" not in msg

    def test_prompt_asks_for_a_role_and_puts_the_reasoning_first(self):
        p = module.ROLE_SYSTEM_PROMPT
        assert "not an adjective" in p and "whether or not it is a common one" in p
        assert p.index('"reasoning"') < p.index('"opposing_role"') < p.index('"opposition_score"')
        assert "reasoning MUST come first" in p and "0 = not opposed at all" in p and "4 = perfectly opposed" in p

    def test_prompt_examples_are_no_pole_of_a_recorded_role_pair(self):
        """The check validates the recorded role pairs; its examples must not prime them."""
        import re
        examples = set(re.findall(r'"([a-z]+)"', module.ROLE_SYSTEM_PROMPT)) | {"tenant", "lodger"}
        poles = set()
        for path in module.ROLES_DIR.glob("*.json"):
            arr = json.loads(path.read_text(encoding="utf-8")).get("arrangement")
            for a in arr if isinstance(arr, list) else [arr] if arr else []:
                if a.get("kind") == "pair":
                    poles.update(a["members"])
        assert len(poles) >= 10 and {"landlord", "sailor"} <= examples
        assert not examples & poles, examples & poles

    def test_parses_reply_charges_usage_and_uses_the_role_prompt(self):
        tracker = MultiModelUsage()
        client = _client("```json\n" + json.dumps(ROLE_REPLY) + "\n```")
        result = asyncio.run(module.classify_role_one(
            client, "destroyer", "Destroys things.", ROLE_INSTRUCTIONS, asyncio.Semaphore(2), tracker))
        assert result == ROLE_REPLY
        assert tracker.n_calls == 1 and list(tracker.per_model) == [module.MODEL]
        kwargs = client.messages.create.call_args.kwargs
        assert kwargs["system"] == module.ROLE_SYSTEM_PROMPT and kwargs["temperature"] == 0
        assert kwargs["messages"][0]["content"].startswith("Role: destroyer\n")

    def test_a_reply_without_the_fields_is_retried_then_an_error_sentinel(self, monkeypatch):
        async def no_sleep(_):
            return None
        monkeypatch.setattr(module.asyncio, "sleep", no_sleep)
        client = _client(json.dumps(REPLY))      # a trait-shaped answer: no opposing_role
        result = asyncio.run(module.classify_role_one(
            client, "destroyer", "d", ROLE_INSTRUCTIONS, asyncio.Semaphore(2)))
        assert result == module.ROLE_ERROR_RESULT and client.messages.create.call_count == 5

    def _roles_dir(self, tmp_path):
        d = tmp_path / "roles" / "instructions"
        d.mkdir(parents=True)
        for stem, desc in (("devils_advocate", "Argues the other side."), ("destroyer", "Destroys things.")):
            (d / f"{stem}.json").write_text(json.dumps({"description": desc, "instruction": ROLE_INSTRUCTIONS}))
        (d / "seed_only.json").write_text(json.dumps({"description": "not generated yet"}))
        return d

    def test_load_tasks_uses_the_display_name(self, tmp_path):
        tasks = module.load_role_tasks(["devils_advocate", "destroyer"], self._roles_dir(tmp_path))
        assert [(t[0], t[1], t[2]) for t in tasks] == [
            ("devils_advocate", "devil's advocate", "Argues the other side."),
            ("destroyer", "destroyer", "Destroys things.")]
        assert tasks[0][3] == ROLE_INSTRUCTIONS

    @pytest.mark.parametrize("stem, message", [("nobody", "role files not found: nobody"),
                                               ("seed_only", "has no instructions")])
    def test_load_tasks_exits_on_a_missing_or_ungenerated_role(self, tmp_path, capsys, stem, message):
        with pytest.raises(SystemExit):
            module.load_role_tasks(["destroyer", stem], self._roles_dir(tmp_path))
        assert message in capsys.readouterr().err

    def test_run_prints_json_by_stem_and_merges_its_own_usage_record(self, tmp_path, monkeypatch, capsys, caplog):
        caplog.set_level("INFO", logger=module.logger.name)
        client = _client(json.dumps(ROLE_REPLY))
        monkeypatch.setattr(module.anthropic, "AsyncAnthropic", lambda: client)
        usage_json = tmp_path / "role_pair_check_usage.json"
        roles_dir = self._roles_dir(tmp_path)
        for _ in range(2):    # the record is cumulative
            asyncio.run(module.main_roles_async(["destroyer", "devils_advocate"], usage_json, roles_dir))
        out, err = capsys.readouterr()
        first, _ = json.JSONDecoder().raw_decode(out)
        assert list(first) == ["destroyer", "devils_advocate"]
        assert first["destroyer"] == {**ROLE_REPLY, "prompt_form": module.PROMPT_FORM, "prompt_label": "destroyer"}
        assert first["devils_advocate"]["prompt_label"] == "devil's advocate"
        assert json.loads(usage_json.read_text())["n_calls"] == 4
        assert "4: 2 roles" in err
        assert "generate_antonyms:roles:" in caplog.text and "parse rate: 2/2 OK" in caplog.text
        contents = [c.kwargs["messages"][0]["content"] for c in client.messages.create.call_args_list]
        assert any(c.startswith("Role: devil's advocate\n") for c in contents)

    def test_flags(self, monkeypatch):
        args = module.parse_args(["--roles", "provincial", "cosmopolitan"])
        assert args.roles == ["provincial", "cosmopolitan"] and args.traits is None and args.usage_json is None
        for bad in (["--roles", "a", "--traits", "b"], ["--roles", "a", "--name-pos"], ["--roles"]):
            with pytest.raises(SystemExit):
                module.parse_args(bad)
        seen = {}

        async def fake(stems, usage_json=None, roles_dir=None):
            seen.update(stems=stems, usage_json=usage_json)
        monkeypatch.setattr(module, "main_roles_async", fake)
        module.main(["--roles", "provincial"])
        assert seen == {"stems": ["provincial"], "usage_json": module.DEFAULT_ROLE_USAGE_JSON}
        assert module.DEFAULT_ROLE_USAGE_JSON.parts[-3:] == ("data", "roles", "role_pair_check_usage.json")
        module.main(["--roles", "provincial", "--usage-json", "y.json"])
        assert str(seen["usage_json"]) == "y.json"
