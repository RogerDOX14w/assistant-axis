"""Step 1's prompts and family since the multi-model plan
(reports/pipeline/coding_plan_multi_model_extraction.md § 5.3, § 9 test 7).

vLLM is faked: a ``vllm`` module with ``LLM`` and ``SamplingParams`` that
record what they were given, so ``VLLMGenerator.load`` and
``generate_batch_detailed`` run as on the pod.  The tokenizers are the
in-process fakes; nothing is downloaded or loaded.
"""
from __future__ import annotations

import dataclasses
import json
import sys
import types
from types import SimpleNamespace

import pytest

from assistant_axis import generation as g
from assistant_axis.internals.chat_layout import LayoutError, derive_chat_layout
from assistant_axis.model_families import (
    FAMILIES,
    FamilyNotBuiltError,
    UnknownFamilyError,
)
from assistant_axis.tests import internals_fakes as fakes

CONVS = [
    [{"role": "system", "content": "You are a pirate"}, {"role": "user", "content": "What is law?"}],
    [{"role": "user", "content": "Hello there"}],
]


class FakeLLM:
    """Records the prompts and the constructor kwargs; answers every prompt
    with ``reply``."""

    instances: list = []

    def __init__(self, tokenizer=None, reply="Arr matey.", **kwargs):
        self.kwargs = kwargs
        self.tokenizer = tokenizer
        self.reply = reply
        self.prompts = None
        FakeLLM.instances.append(self)

    def get_tokenizer(self):
        return self.tokenizer

    def generate(self, prompts, sampling_params):
        self.prompts = prompts
        return [SimpleNamespace(outputs=[SimpleNamespace(text=self.reply, finish_reason="stop")])
                for _ in prompts]


@pytest.fixture
def fake_vllm(monkeypatch):
    """A ``vllm`` module whose LLM uses the tokenizer the test sets."""
    state = {"tokenizer": fakes.make_qwen3_like_tokenizer(), "reply": "Arr matey."}
    mod = types.ModuleType("vllm")
    mod.LLM = lambda **kw: FakeLLM(tokenizer=state["tokenizer"], reply=state["reply"], **kw)
    mod.SamplingParams = lambda **kw: SimpleNamespace(**kw)
    monkeypatch.setitem(sys.modules, "vllm", mod)
    FakeLLM.instances.clear()
    return state


def _loaded(model, family, **kw):
    gen = g.VLLMGenerator(model, family=family, **kw)
    gen.load()
    return gen


def test_prompts_are_the_templates_token_ids(fake_vllm):
    gen = _loaded("Qwen/Qwen3-32B", FAMILIES["qwen3"])
    gen.generate_batch(CONVS)
    tok = fake_vllm["tokenizer"]
    llm = FakeLLM.instances[-1]
    assert all(set(p) == {"prompt_token_ids"} for p in llm.prompts)
    for conv, p in zip(CONVS, llm.prompts):
        want = tok.apply_chat_template(conv, tokenize=True, add_generation_prompt=True,
                                       return_dict=False, enable_thinking=False)
        assert p["prompt_token_ids"] == list(want)


def test_qwen3_ids_equal_the_old_text_paths(fake_vllm):
    # The text path: vLLM tokenized the rendered prompt with the tokenizer's
    # defaults (special tokens on).  Qwen3's adds none, so the ids are equal.
    gen = _loaded("Qwen/Qwen3-32B", FAMILIES["qwen3"])
    gen.generate_batch(CONVS)
    tok = fake_vllm["tokenizer"]
    for conv, p in zip(CONVS, FakeLLM.instances[-1].prompts):
        text = tok.apply_chat_template(conv, tokenize=False, add_generation_prompt=True,
                                       enable_thinking=False)
        assert p["prompt_token_ids"] == tok(text)["input_ids"]


def test_llama_like_prompts_carry_exactly_one_bos(fake_vllm):
    tok = fakes.make_llama3_like_tokenizer()
    fake_vllm["tokenizer"] = tok
    gen = _loaded("meta-llama/x", FAMILIES["llama"])
    gen.generate_batch(CONVS)
    bos = tok.convert_tokens_to_ids("<|begin_of_text|>")
    for conv, p in zip(CONVS, FakeLLM.instances[-1].prompts):
        assert p["prompt_token_ids"].count(bos) == 1 and p["prompt_token_ids"][0] == bos
        text = tok.apply_chat_template(conv, tokenize=False, add_generation_prompt=True)
        assert tok(text)["input_ids"].count(bos) == 2          # what the text path sent


def test_the_leaked_think_strip_applies_to_the_qwen3_row_only(fake_vllm):
    fake_vllm["reply"] = "planning </think> Arr matey."
    [d] = _loaded("Qwen/Qwen3-32B", FAMILIES["qwen3"]).generate_batch_detailed(CONVS[:1])
    assert d["text"] == "Arr matey." and d["thinking_stripped"] is True
    fake_vllm["tokenizer"] = fakes.make_llama3_like_tokenizer()
    [d] = _loaded("meta-llama/x", FAMILIES["llama"]).generate_batch_detailed(CONVS[:1])
    assert d["text"] == "planning </think> Arr matey." and d["thinking_stripped"] is False


def test_load_takes_trust_remote_code_from_the_row_and_derives_the_layout(fake_vllm):
    gen = _loaded("Qwen/Qwen3-32B", FAMILIES["qwen3"])
    assert FakeLLM.instances[-1].kwargs["trust_remote_code"] is False   # was True for all
    assert gen.layout.header_tokens == FAMILIES["qwen3"].expected_header_tokens


def test_load_resolves_the_family_from_the_config_when_not_given(fake_vllm, monkeypatch):
    import assistant_axis.model_families as mf
    monkeypatch.setattr(mf, "family_for_model", lambda name: FAMILIES["qwen3"])
    gen = _loaded("/local/q3", None)
    assert gen.family is FAMILIES["qwen3"]


def test_an_unknown_or_unbuilt_family_refuses_before_vllm_starts(fake_vllm, monkeypatch):
    import assistant_axis.model_families as mf

    def unknown(name):
        raise UnknownFamilyError("model_type 'nope' has no row")

    monkeypatch.setattr(mf, "family_for_model", unknown)
    with pytest.raises(UnknownFamilyError):
        g.VLLMGenerator("x/y").load()
    with pytest.raises(FamilyNotBuiltError):
        g.VLLMGenerator("openai/gpt-oss-20b", family=FAMILIES["gpt_oss"]).load()
    assert FakeLLM.instances == []


def test_load_refuses_a_header_unlike_the_preflights(fake_vllm):
    with pytest.raises(LayoutError, match="preflight"):
        _loaded("Qwen/Qwen3-32B", FAMILIES["qwen3"], expected_header_ids=[1, 11, 5])


def test_format_conversation_warns_when_the_template_and_the_row_disagree(caplog):
    # A template that raises on a system message, under a row that says
    # native: the instruction is folded into the user turn, with a warning.
    g._SYSTEM_PROMPT_WARNED.clear()
    tok = fakes.make_qwen3_like_tokenizer(
        "{%- if messages[0].role == 'system' -%}{{ raise_exception('no system') }}{%- endif -%}"
        + fakes.QWEN3_NO_THINK_BLOCK_TEMPLATE)
    row = dataclasses.replace(FAMILIES["qwen3"], expected_header_tokens=None)
    with caplog.at_level("WARNING"):
        conv = g.format_conversation("You are a pirate", "What is law?", tok, family=row)
        g.format_conversation("You are a pirate", "Hello", tok, family=row)
    assert conv == [{"role": "user", "content": "You are a pirate\n\nWhat is law?"}]
    warnings = [r.message for r in caplog.records if "system-prompt behaviour" in r.message]
    assert len(warnings) == 1                                       # once, not per conversation
    assert "'fold_into_user'" in warnings[0] and "'native'" in warnings[0]
    caplog.clear()
    with caplog.at_level("WARNING"):                                # agreeing: no warning
        g.format_conversation("You are a pirate", "Hi", fakes.make_qwen3_like_tokenizer(),
                              family=FAMILIES["qwen3"])
    assert "system-prompt behaviour" not in caplog.text


def _record(tmp_path, tok, family, **over):
    (tmp_path / "q.jsonl").write_text(json.dumps({"id": 0, "question": "What is law"}) + "\n")
    layout = derive_chat_layout(tok, family)
    sample = g.format_conversation("You are a pirate", "What is law", tok, family=family)
    kw = dict(model_name="Qwen/Qwen3-32B", family=family, layout=layout,
              system_prompt=g.system_prompt_mode(tok, family), sample_conversation=sample,
              sample_prompt_ids=g.prompt_token_ids(tok, sample, family.template_kwargs),
              temperature=0.7, top_p=0.9, max_tokens=512, max_model_len=2048,
              questions_file=str(tmp_path / "q.jsonl"), question_count=300, reduce_questions=3,
              instruction_dirs={})
    kw.update(over)
    return g.build_generation_run_record(**kw)


def test_the_side_car_has_the_plans_schema_and_appends(tmp_path, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    tok = fakes.make_qwen3_like_tokenizer()
    rec = _record(tmp_path, tok, FAMILIES["qwen3"])
    for key in ("script", "created_at", "git_sha", "model_name", "model_type", "template_kwargs",
                "header_tokens", "header_ids", "generation_prompt_ids", "system_prompt",
                "response_cleanup", "sampling", "questions", "sample_conversation",
                "sample_prompt_ids"):
        assert key in rec, key
    assert rec["model_type"] == "qwen3" and rec["template_kwargs"] == {"enable_thinking": False}
    assert rec["header_tokens"] == fakes.QWEN3_HEADER_TOKENS
    assert rec["system_prompt"] == "native" and rec["response_cleanup"] == "strip_leaked_think"
    json.dumps(rec)                                                 # serialisable as it is
    out = tmp_path / "responses"
    out.mkdir()
    g.write_generation_config(out, rec)
    g.write_generation_config(out, _record(tmp_path, tok, FAMILIES["qwen3"]))
    cfg = g.read_generation_config(out)
    assert cfg["schema"] == 1 and len(cfg["runs"]) == 2
    assert g.settings_differences(cfg["runs"][0], cfg["runs"][1]) == []
