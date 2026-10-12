"""ConversationEncoder's ``span_builder`` dispatch (multi-model plan § 5.4,
task 4), on the in-process fakes.  test_conversation_encoder.py pins the Qwen
path itself and is unchanged; this file pins which path is taken."""
from __future__ import annotations

import pytest

from assistant_axis.internals.conversation import ConversationEncoder
from assistant_axis.tests.internals_fakes import (
    LLAMA3_HEADER_TOKENS,
    make_llama3_like_tokenizer,
    make_qwen3_like_tokenizer,
)

THINKING_OFF = {"enable_thinking": False}


def _conv(response, system="You are a pirate"):
    conv = [{"role": "system", "content": system}] if system is not None else []
    return conv + [{"role": "user", "content": "What is law?"},
                   {"role": "assistant", "content": response}]


@pytest.fixture(scope="module")
def qwen_tok():
    return make_qwen3_like_tokenizer()


def _which_path(enc, monkeypatch):
    called = []
    orig = enc._build_turn_spans_qwen

    def spy(*a, **k):
        called.append("chatml")
        return orig(*a, **k)

    monkeypatch.setattr(enc, "_build_turn_spans_qwen", spy)
    enc.build_turn_spans(_conv("Arr matey."), **THINKING_OFF)
    return called[0] if called else "generic"


@pytest.mark.parametrize("model_name, span_builder, expected", [
    ("Qwen/Qwen3-32B", None, "chatml"),            # the old dispatch, kept for other callers
    ("/workspace/models/q3-32b", None, "generic"),  # ... which a local path misses
    ("/workspace/models/q3-32b", "chatml", "chatml"),   # the row decides, whatever the name
    ("Qwen/Qwen3-32B", "generic", "generic"),
])
def test_span_builder_picks_the_path(qwen_tok, monkeypatch, model_name, span_builder, expected):
    enc = ConversationEncoder(qwen_tok, model_name, span_builder=span_builder)
    assert _which_path(enc, monkeypatch) == expected


def test_chatml_by_row_gives_the_same_spans_as_chatml_by_name(qwen_tok):
    by_name = ConversationEncoder(qwen_tok, "Qwen/Qwen3-32B")
    by_row = ConversationEncoder(qwen_tok, "/local/path", span_builder="chatml")
    for conv in (_conv("Arr matey. Law rules!"), _conv("\n\nArr matey!\n", system=None),
                 _conv("")):
        assert by_row.build_turn_spans(conv, **THINKING_OFF) == \
            by_name.build_turn_spans(conv, **THINKING_OFF)


def test_generic_path_finds_the_content_after_a_llama_like_header():
    tok = make_llama3_like_tokenizer()
    enc = ConversationEncoder(tok, "meta-llama/x", span_builder="generic")
    full_ids, spans = enc.build_turn_spans(_conv("Arr matey. Law rules!"))
    a = [s for s in spans if s["role"] == "assistant"]
    assert len(a) == 1
    toks = tok.convert_ids_to_tokens(full_ids)
    assert toks[a[0]["start"] - 4:a[0]["start"]] == LLAMA3_HEADER_TOKENS
    assert tok.decode(full_ids[a[0]["start"]:a[0]["end"]]) == "Arr matey. Law rules!"


def test_an_unknown_span_builder_is_refused(qwen_tok):
    with pytest.raises(ValueError, match="span_builder"):
        ConversationEncoder(qwen_tok, span_builder="harmony")
