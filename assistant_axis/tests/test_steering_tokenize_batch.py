"""``steering_runner._tokenize_batch`` tokenizes through the chat template
(Roger, 2026-10-13; review P1 D8, the multi-model plan's step 1 fix applied to
steering): one BOS on Llama-like templates, Qwen3's ids and masks unchanged,
left padding kept.  On the in-process fake tokenizers; no model is loaded."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
import torch

from assistant_axis import steering_runner
from assistant_axis.tests.internals_fakes import (
    make_llama3_like_tokenizer,
    make_qwen3_like_tokenizer,
)

CONVS = [
    [{"role": "system", "content": "You are a pirate"},
     {"role": "user", "content": "What is law?"}],
    [{"role": "system", "content": "You are a pirate. Arr matey, the law of the code."},
     {"role": "user", "content": "Yes?"}],
    [{"role": "system", "content": "Hello"}, {"role": "user", "content": "no"}],
]


def _model(model_type):
    return SimpleNamespace(config=SimpleNamespace(model_type=model_type))


def _old_path(tok, convs, **kw):
    """What _tokenize_batch did until 2026-10-13: render the template to
    text, then tokenize the text as a left-padded batch."""
    prompts = [tok.apply_chat_template(c, tokenize=False, add_generation_prompt=True, **kw)
               for c in convs]
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    prev, tok.padding_side = tok.padding_side, "left"
    try:
        return tok(prompts, return_tensors="pt", padding=True)
    finally:
        tok.padding_side = prev


def test_qwen3_ids_and_mask_are_the_old_paths():
    tok = make_qwen3_like_tokenizer()
    new = steering_runner._tokenize_batch(tok, CONVS, model=_model("qwen3"))
    old = _old_path(tok, CONVS, enable_thinking=False)
    assert set(new) == {"input_ids", "attention_mask"}
    assert torch.equal(new["input_ids"], old["input_ids"])
    assert torch.equal(new["attention_mask"], old["attention_mask"])
    assert new["input_ids"].dtype == torch.long and new["attention_mask"].dtype == torch.long


def test_llama_like_rows_carry_one_bos_at_their_start():
    tok = make_llama3_like_tokenizer()
    bos = tok.convert_tokens_to_ids("<|begin_of_text|>")
    new = steering_runner._tokenize_batch(tok, CONVS, model=_model("llama"))
    for ids, mask in zip(new["input_ids"].tolist(), new["attention_mask"].tolist()):
        first = mask.index(1)
        assert ids[first] == bos                    # the BOS opens the real tokens
        assert ids.count(bos) == 1                  # and appears nowhere else
    # The old path put a second BOS after the template's.
    old = _old_path(tok, CONVS)
    for ids, mask in zip(old["input_ids"].tolist(), old["attention_mask"].tolist()):
        first = mask.index(1)
        assert ids[first:first + 2] == [bos, bos]


@pytest.mark.parametrize("make, model_type", [(make_qwen3_like_tokenizer, "qwen3"),
                                              (make_llama3_like_tokenizer, "llama")])
def test_padding_is_on_the_left(make, model_type):
    tok = make()
    new = steering_runner._tokenize_batch(tok, CONVS, model=_model(model_type))
    ids, mask = new["input_ids"], new["attention_mask"]
    lengths = mask.sum(dim=1).tolist()
    assert len(set(lengths)) > 1                    # the rows differ in length
    width = ids.shape[1]
    assert max(lengths) == width
    for row, m, n in zip(ids.tolist(), mask.tolist(), lengths):
        assert m == [0] * (width - n) + [1] * n     # padding first, real tokens last
        assert row[:width - n] == [tok.pad_token_id] * (width - n)
    assert tok.padding_side == make().padding_side  # the tokenizer is left as it was


def test_a_tokenizer_without_a_pad_token_pads_with_eos():
    tok = make_llama3_like_tokenizer()
    tok.pad_token = None
    new = steering_runner._tokenize_batch(tok, CONVS, model=_model("llama"))
    assert tok.pad_token == tok.eos_token
    row, mask = new["input_ids"].tolist()[2], new["attention_mask"].tolist()[2]
    n_pad = mask.count(0)
    assert n_pad > 0 and row[:n_pad] == [tok.eos_token_id] * n_pad
