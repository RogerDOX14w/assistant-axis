"""The family table (assistant_axis/model_families.py; the multi-model plan's
§ 5.2 and § 9 test 3).  No model or tokenizer is loaded: ``family_for_model``
is tested through a monkeypatched ``AutoConfig``."""
from __future__ import annotations

import dataclasses
import pickle
import sys
import types

import pytest

from assistant_axis import model_families as mf

SEVEN = ("<|im_start|>", "assistant", "\n", "<think>", "\n\n", "</think>", "\n\n")


def test_the_six_draft_rows_are_there():
    assert set(mf.FAMILIES) == {"qwen3", "llama", "gemma2", "olmo2", "olmo3", "gpt_oss"}
    for key, row in mf.FAMILIES.items():
        assert row.model_type == key


@pytest.mark.parametrize("key", sorted(mf.FAMILIES))
def test_every_row_has_every_field_with_a_known_value(key):
    row = mf.FAMILIES[key]
    names = {f.name for f in dataclasses.fields(mf.FamilySpec)}
    assert names == {"model_type", "template_kwargs", "reasoning", "reasoning_stored",
                     "system_prompt", "span_builder", "response_cleanup", "bos_in_template",
                     "end_token", "expected_header_tokens", "trust_remote_code",
                     "hf_load_kwargs", "notes"}
    assert row.reasoning in mf.REASONING_MODES
    assert row.system_prompt in mf.SYSTEM_PROMPT_MODES
    assert row.span_builder in mf.SPAN_BUILDERS
    assert row.response_cleanup in mf.RESPONSE_CLEANUPS
    assert isinstance(row.template_kwargs, dict) and isinstance(row.hf_load_kwargs, dict)
    assert row.reasoning_stored is False or row.reasoning == "always_on"
    assert row.trust_remote_code is False          # all six are native in transformers
    assert key in mf.TO_CHECK
    assert key in mf.DRAFT_HEADERS or key == "olmo3"     # olmo3: header unknown, derived


def test_qwen3_row_is_what_steps_1_and_2_ran_for_the_8slot_tree():
    row = mf.family_for_model_type("qwen3")
    assert row.expected_header_tokens == SEVEN == mf.QWEN3_NON_THINKING_HEADER_TOKENS
    assert row.template_kwargs == {"enable_thinking": False}
    assert (row.span_builder, row.response_cleanup, row.system_prompt) == (
        "chatml", "strip_leaked_think", "native")
    assert mf.QWEN3_NON_THINKING_HEADER_IDS == (151644, 77091, 198, 151667, 271, 151668, 271)
    assert mf.TO_CHECK["qwen3"] == ()


def test_only_qwen3_is_pinned():
    # No row is pinned before its smoke run has shown the derived header and
    # Roger has read it (plan § 5.2).
    assert [k for k, r in mf.FAMILIES.items() if r.expected_header_tokens] == ["qwen3"]
    assert all(mf.TO_CHECK[k] for k in mf.FAMILIES if k != "qwen3")


def test_unknown_model_type_raises_listing_the_keys():
    with pytest.raises(mf.UnknownFamilyError) as e:
        mf.family_for_model_type("nope")
    msg = str(e.value)
    assert "'nope'" in msg and "assistant_axis/model_families.py" in msg
    for key in mf.FAMILIES:
        assert key in msg


def test_family_for_model_reads_model_type_from_the_config(monkeypatch):
    seen = []

    class FakeAutoConfig:
        @staticmethod
        def from_pretrained(name):
            seen.append(name)
            return types.SimpleNamespace(model_type={"local/q": "qwen3", "x/y": "mystery"}[name])

    fake = types.ModuleType("transformers")
    fake.AutoConfig = FakeAutoConfig
    monkeypatch.setitem(sys.modules, "transformers", fake)
    # A local path with no "qwen" in it finds the qwen3 row by its config.
    assert mf.family_for_model("local/q") is mf.FAMILIES["qwen3"]
    with pytest.raises(mf.UnknownFamilyError, match="mystery"):
        mf.family_for_model("x/y")
    assert seen == ["local/q", "x/y"]


def test_gpt_oss_is_refused_until_its_todo_is_built():
    assert mf.unbuilt_reason(mf.FAMILIES["gpt_oss"]) is not None
    with pytest.raises(mf.FamilyNotBuiltError, match="Q3"):
        mf.require_built(mf.FAMILIES["gpt_oss"])
    for key in ("qwen3", "llama", "gemma2", "olmo2", "olmo3"):
        assert mf.require_built(mf.FAMILIES[key]) is mf.FAMILIES[key]


def test_rows_pickle_and_do_not_share_their_dicts():
    src = {"enable_thinking": False}
    row = mf.FamilySpec(model_type="t", template_kwargs=src, reasoning="none",
                        reasoning_stored=False, system_prompt="native", span_builder="generic",
                        response_cleanup="none", bos_in_template=False, end_token="",
                        expected_header_tokens=["a", "b"])
    src["enable_thinking"] = True
    assert row.template_kwargs == {"enable_thinking": False}
    assert row.expected_header_tokens == ("a", "b")
    with pytest.raises(dataclasses.FrozenInstanceError):
        row.model_type = "u"
    for r in list(mf.FAMILIES.values()) + [row]:
        assert pickle.loads(pickle.dumps(r)) == r


def test_get_config_adds_the_family_only_when_asked(monkeypatch):
    # models.py keeps its job (per-model facts by repository id); the family
    # comes through family_for_model on request (plan § 5.2, § 15 Q1).
    from assistant_axis import models
    seen = []
    monkeypatch.setattr(mf, "family_for_model", lambda name: seen.append(name) or mf.FAMILIES["qwen3"])
    plain = models.get_config("Qwen/Qwen3-32B")
    assert "family" not in plain and plain["short_name"] == "Qwen" and seen == []
    cfg = models.get_config("Qwen/Qwen3-32B", with_family=True)
    assert cfg["family"] is mf.FAMILIES["qwen3"] and cfg["target_layer"] == 32
    assert seen == ["Qwen/Qwen3-32B"]
    assert "family" not in models.MODEL_CONFIGS["Qwen/Qwen3-32B"]       # a copy
