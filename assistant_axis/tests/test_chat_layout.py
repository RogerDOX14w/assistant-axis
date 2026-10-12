"""The header layout derived from the chat template (multi-model plan § 5.1,
§ 9 test 2), on in-process fake tokenizers only (``internals_fakes``)."""
from __future__ import annotations

import dataclasses

import pytest

from assistant_axis.internals.chat_layout import (
    ChatLayout,
    LayoutError,
    chat_ids,
    derive_chat_layout,
)
from assistant_axis.model_families import FAMILIES, QWEN3_NON_THINKING_HEADER_TOKENS
from assistant_axis.tests import internals_fakes as fakes

QWEN3 = FAMILIES["qwen3"]
UNPINNED_QWEN3 = dataclasses.replace(QWEN3, expected_header_tokens=None)


@pytest.fixture(scope="module")
def qwen_tok():
    return fakes.make_qwen3_like_tokenizer()


def test_qwen3_like_fake_derives_the_seven_header_tokens(qwen_tok):
    layout = derive_chat_layout(qwen_tok, QWEN3)
    assert layout.header_tokens == QWEN3_NON_THINKING_HEADER_TOKENS
    assert list(layout.header_tokens) == fakes.QWEN3_HEADER_TOKENS
    assert list(layout.header_ids) == qwen_tok.convert_tokens_to_ids(fakes.QWEN3_HEADER_TOKENS)
    assert layout.search_distance == 14            # spans._MAX_HEADER_SEARCH_DIST["qwen"] had 14
    assert layout.generation_prompt_ids == layout.header_ids   # the cross-check: equal for Qwen3
    assert layout.model_type == "qwen3" and layout.template_kwargs == {"enable_thinking": False}
    assert [m["role"] for m in layout.probe] == ["system", "user"]


def test_header_tokens_are_decoded_strings_not_byte_level_names(qwen_tok):
    layout = derive_chat_layout(qwen_tok, QWEN3)
    assert "\n" in layout.header_tokens and "\n\n" in layout.header_tokens
    assert not any(t.startswith("Ċ") for t in layout.header_tokens)


def test_metadata_has_the_layout_keys_as_lists(qwen_tok):
    meta = derive_chat_layout(qwen_tok, QWEN3).metadata()
    assert meta == {
        "header_tokens": list(QWEN3_NON_THINKING_HEADER_TOKENS),
        "header_ids": qwen_tok.convert_tokens_to_ids(list(QWEN3_NON_THINKING_HEADER_TOKENS)),
        "model_type": "qwen3",
        "template_kwargs": {"enable_thinking": False},
        "generation_prompt_ids": meta["header_ids"],
    }
    assert all(type(v) in (list, dict, str) for v in meta.values())


def test_a_template_without_the_think_block_derives_three_and_fails_the_qwen3_row():
    tok = fakes.make_qwen3_like_tokenizer(fakes.QWEN3_NO_THINK_BLOCK_TEMPLATE)
    assert derive_chat_layout(tok, UNPINNED_QWEN3).header_tokens == (
        "<|im_start|>", "assistant", "\n")
    with pytest.raises(LayoutError) as e:
        derive_chat_layout(tok, QWEN3)
    # names both: the derived header and the row's expectation
    assert "['<|im_start|>', 'assistant', '\\n']" in str(e.value)
    assert "'</think>'" in str(e.value) and "(3 tokens)" in str(e.value) and "(7)" in str(e.value)


def test_a_generation_prompt_unlike_the_stored_turn_raises():
    tok = fakes.make_qwen3_like_tokenizer(fakes.QWEN3_MISMATCHED_PROMPT_TEMPLATE)
    with pytest.raises(LayoutError, match="not a prefix of the stored assistant turn") as e:
        derive_chat_layout(tok, UNPINNED_QWEN3)
    assert "'<|im_start|>assistant\\n\\n" in str(e.value)        # both, decoded


def test_a_header_that_depends_on_the_system_message_raises():
    # The assistant header (in the generation prompt and in the stored turn
    # alike) ends in a blank line when a system message is there, a newline
    # when not: each rendering is consistent on its own, the two differ.
    template = (
        "{%- set sep = '\n\n' if messages[0].role == 'system' else '\n' -%}"
        "{%- for message in messages -%}"
        "{%- if message.role == 'assistant' -%}"
        "{{- '<|im_start|>assistant' + sep + message.content + '<|im_end|>\n' -}}"
        "{%- else -%}"
        "{{- '<|im_start|>' + message.role + '\n' + message.content + '<|im_end|>\n' -}}"
        "{%- endif -%}"
        "{%- endfor -%}"
        "{%- if add_generation_prompt -%}{{- '<|im_start|>assistant' + sep -}}{%- endif -%}"
    )
    tok = fakes.make_qwen3_like_tokenizer(template)
    with pytest.raises(LayoutError, match="differs with a system message"):
        derive_chat_layout(tok, UNPINNED_QWEN3)


def test_harmony_like_fake_derives_the_six_tokens_after_the_stored_thinking():
    tok = fakes.make_harmony_like_tokenizer()
    layout = derive_chat_layout(tok, FAMILIES["gpt_oss"])     # derivation only: not built
    assert list(layout.header_tokens) == fakes.HARMONY_HEADER_TOKENS
    # The generation prompt is a prefix of the stored turn but not the header:
    # the model writes the channel tokens itself.
    assert [tok.decode([i]) for i in layout.generation_prompt_ids] == ["<|start|>", "assistant"]
    assert layout.generation_prompt_ids != layout.header_ids
    assert layout.template_kwargs == {"reasoning_effort": "low"}


def test_llama3_like_fake_derives_four_tokens_and_one_bos():
    tok = fakes.make_llama3_like_tokenizer()
    layout = derive_chat_layout(tok, FAMILIES["llama"])
    assert list(layout.header_tokens) == fakes.LLAMA3_HEADER_TOKENS
    assert layout.generation_prompt_ids == layout.header_ids
    bos = tok.convert_tokens_to_ids("<|begin_of_text|>")
    ids = chat_ids(tok, list(layout.probe), add_generation_prompt=True)
    assert ids.count(bos) == 1 and ids[0] == bos
    # ... while the rendered text tokenized as text gets a second one (P1 D8).
    text = tok.apply_chat_template(list(layout.probe), tokenize=False, add_generation_prompt=True)
    assert tok(text)["input_ids"][:2] == [bos, bos]


def test_a_family_that_folds_the_system_prompt_probes_without_one():
    # A Gemma-2-like template that raises on a system role, under a
    # fold_into_user row: the probe has no system message, so it renders.
    template = ("{%- if messages[0].role == 'system' -%}{{ raise_exception('System role not "
                "supported') }}{%- endif -%}" + fakes.QWEN3_NO_THINK_BLOCK_TEMPLATE)
    tok = fakes.make_qwen3_like_tokenizer(template)
    row = dataclasses.replace(FAMILIES["gemma2"], expected_header_tokens=None)
    layout = derive_chat_layout(tok, row)
    assert [m["role"] for m in layout.probe] == ["user"]
    assert layout.header_tokens == ("<|im_start|>", "assistant", "\n")


def test_chat_ids_unwraps_a_mapping():
    class DictTokenizer:
        def apply_chat_template(self, messages, **kwargs):
            assert kwargs["return_dict"] is False and kwargs["tokenize"] is True
            return {"input_ids": [5, 6], "attention_mask": [1, 1]}

    assert chat_ids(DictTokenizer(), [{"role": "user", "content": "x"}],
                    add_generation_prompt=True) == [5, 6]


def test_layout_is_frozen_and_pickles(qwen_tok):
    import pickle
    layout = derive_chat_layout(qwen_tok, QWEN3)
    assert isinstance(layout, ChatLayout)
    with pytest.raises(dataclasses.FrozenInstanceError):
        layout.search_distance = 3
    assert pickle.loads(pickle.dumps(layout)) == layout
