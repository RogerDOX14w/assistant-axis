"""ConversationEncoder: token ids and Qwen3 turn spans, on an in-process fake.

The spans decide which tokens step 2 averages into a response's activation
(slot 0 of every vector), so they are pinned here against a Qwen3-like chat
template (``internals_fakes``): the assistant span is the response's content
tokens, from its first to its last non-whitespace token, and nothing of the
``<|im_start|>assistant\\n<think>\\n\\n</think>\\n\\n`` header or the closing
``<|im_end|>\\n``.

Regression (review of 2026-10-12): transformers 5 made
``apply_chat_template(tokenize=True)`` return a ``BatchEncoding`` by default.
The encoder indexed that as a token list, found no spans, and step 2 saved
nothing for any entity, without an error.  The macOS lock has transformers
5.1.0, so these tests failed there before the fix; the pod's Linux lock has
4.57.6, which returned a list and was never affected.
"""
from __future__ import annotations

import pytest

from assistant_axis.internals.conversation import ConversationEncoder
from assistant_axis.tests.internals_fakes import (
    QWEN3_HEADER_TOKENS,
    make_qwen3_like_tokenizer,
)

QWEN = "Qwen/Qwen3-32B"
THINKING_OFF = {"enable_thinking": False}


@pytest.fixture(scope="module")
def tok():
    return make_qwen3_like_tokenizer()


def _conv(response, system="You are a pirate"):
    conv = [{"role": "system", "content": system}] if system is not None else []
    return conv + [
        {"role": "user", "content": "What is law?"},
        {"role": "assistant", "content": response},
    ]


def _rendered_ids(tok, conv):
    text = tok.apply_chat_template(conv, tokenize=False, add_generation_prompt=False,
                                   **THINKING_OFF)
    return tok(text, add_special_tokens=False)["input_ids"]


class TestChatIds:

    def test_is_a_flat_list_of_the_rendered_tokens(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        conv = _conv("Arr matey.")
        ids = enc._chat_ids(conv, **THINKING_OFF)
        assert type(ids) is list and all(type(i) is int for i in ids)
        assert ids == _rendered_ids(tok, conv)

    def test_public_token_ids_is_a_flat_list(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        conv = _conv("Arr matey.")
        assert enc.token_ids(conv, **THINKING_OFF) == _rendered_ids(tok, conv)

    def test_a_tokenizer_that_returns_a_mapping_is_unwrapped(self):
        class DictReturningTokenizer:
            name_or_path = QWEN

            def apply_chat_template(self, messages, **kwargs):
                return {"input_ids": [1, 2, 3], "attention_mask": [1, 1, 1]}

        enc = ConversationEncoder(DictReturningTokenizer(), QWEN)
        assert enc._chat_ids([{"role": "user", "content": "x"}]) == [1, 2, 3]


class TestQwenTurnSpans:

    def test_assistant_span_is_exactly_the_response_content(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        conv = _conv("Arr matey. Law rules!")
        full_ids, spans = enc.build_turn_spans(conv, **THINKING_OFF)
        assert full_ids == _rendered_ids(tok, conv)
        # The system turn has no span; user is turn 0, assistant turn 1.
        assert [(s["turn"], s["role"]) for s in spans] == [(0, "user"), (1, "assistant")]

        a = spans[1]
        toks = tok.convert_ids_to_tokens(full_ids)
        hdr = toks.index("assistant") - 1
        assert toks[hdr:hdr + 7] == QWEN3_HEADER_TOKENS
        assert a["start"] == hdr + 7                       # first content token
        assert toks[a["end"]] == "<|im_end|>"              # end is exclusive
        assert tok.decode(full_ids[a["start"]:a["end"]]) == "Arr matey. Law rules!"
        assert a["n_tokens"] == a["end"] - a["start"]

    def test_boundary_whitespace_tokens_are_left_out(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        # The template drops leading newlines; the trailing one is a token of
        # its own, and the span stops before it.
        conv = _conv("\n\nArr matey!\n", system=None)
        full_ids, spans = enc.build_turn_spans(conv, **THINKING_OFF)
        a = spans[-1]
        assert tok.decode(full_ids[a["start"]:a["end"]]) == "Arr matey!"
        assert tok.convert_ids_to_tokens(full_ids[a["end"]]) == "\n"

    def test_user_span_includes_the_newline_after_the_role(self, tok):
        # Not used by step 2 (it keeps assistant turns only), pinned so a
        # change shows up.
        enc = ConversationEncoder(tok, QWEN)
        conv = _conv("Yes")
        full_ids, spans = enc.build_turn_spans(conv, **THINKING_OFF)
        u = spans[0]
        assert tok.decode(full_ids[u["start"]:u["end"]]) == "\nWhat is law?"

    def test_empty_response_has_no_assistant_span(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        _, spans = enc.build_turn_spans(_conv(""), **THINKING_OFF)
        assert [s["role"] for s in spans] == ["user"]

    def test_batch_spans_carry_conversation_ids(self, tok):
        enc = ConversationEncoder(tok, QWEN)
        convs = [_conv("Yes"), _conv("Arr matey.", system=None)]
        batch_ids, spans, meta = enc.build_batch_turn_spans(convs, **THINKING_OFF)
        assert meta["total_conversations"] == 2
        assert meta["conversation_lengths"] == [len(i) for i in batch_ids]
        assert sorted({s["conversation_id"] for s in spans}) == [0, 1]
        for s in spans:
            assert s["local_start"] == s["start"] and s["local_end"] == s["end"]
