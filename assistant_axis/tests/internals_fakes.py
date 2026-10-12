"""In-process fakes for testing ``assistant_axis.internals`` and step 2.

Nothing here downloads or loads a real model.

* ``make_qwen3_like_tokenizer()`` builds a word-level
  ``PreTrainedTokenizerFast`` whose special tokens and chat template
  reproduce what step 2 depends on in Qwen3's: ``<|im_start|>role\\n ...
  <|im_end|>\\n`` turns, and the empty think block
  ``<think>\\n\\n</think>\\n\\n`` that Qwen3's template puts before the
  assistant turn after the last user message (and after the generation
  prompt when ``enable_thinking=False``).  ``\\n``, ``\\n\\n``, ``user`` and
  ``assistant`` are single tokens, as in Qwen3's vocabulary.  The template is
  a reduced copy written for these tests, not Qwen3's own: no tools, no
  ``reasoning_content``.

* ``FakeCausalLM`` is a model whose hidden state records where it came
  from: after decoder layer ``k`` the vector at position ``p`` of a sequence
  is ``[p, k + 1, token_id, attention_mask]``.  A test can then read off,
  from a saved activation, which positions were averaged and which layer it
  is, exactly (small integers and their means are exact in bf16 at these
  sizes, or within one bf16 step).
"""
from __future__ import annotations

import torch
import torch.nn as nn

QWEN3_LIKE_TEMPLATE = (
    "{%- set ns = namespace(last_query_index=messages|length - 1, seen=false) -%}"
    "{%- for m in messages[::-1] -%}"
    "{%- if m.role == 'user' and not ns.seen -%}"
    "{%- set ns.last_query_index = messages|length - 1 - loop.index0 -%}"
    "{%- set ns.seen = true -%}"
    "{%- endif -%}"
    "{%- endfor -%}"
    "{%- for message in messages -%}"
    "{%- if message.role in ['system', 'user'] -%}"
    "{{- '<|im_start|>' + message.role + '\n' + message.content + '<|im_end|>' + '\n' -}}"
    "{%- elif message.role == 'assistant' -%}"
    "{%- if loop.index0 > ns.last_query_index -%}"
    "{{- '<|im_start|>assistant\n<think>\n\n</think>\n\n' + message.content.lstrip('\n') -}}"
    "{%- else -%}"
    "{{- '<|im_start|>assistant\n' + message.content -}}"
    "{%- endif -%}"
    "{{- '<|im_end|>\n' -}}"
    "{%- endif -%}"
    "{%- endfor -%}"
    "{%- if add_generation_prompt -%}"
    "{{- '<|im_start|>assistant\n' -}}"
    "{%- if enable_thinking is defined and enable_thinking is false -%}"
    "{{- '<think>\n\n</think>\n\n' -}}"
    "{%- endif -%}"
    "{%- endif -%}"
)

_WORDS = (
    "system user assistant You are a pirate What is law Law rules Hello there "
    "Arr matey Yes no the of and code x"
).split()
_SPECIAL = ["<|endoftext|>", "<|im_start|>", "<|im_end|>"]
_ADDED = ["<think>", "</think>"]

# The seven tokens before a Qwen3 non-thinking assistant turn's content, in
# the order spans._HEADER_TOKENS["qwen"] lists them.
QWEN3_HEADER_TOKENS = ["<|im_start|>", "assistant", "\n", "<think>", "\n\n", "</think>", "\n\n"]


def make_qwen3_like_tokenizer():
    from tokenizers import Regex, Tokenizer, decoders, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast

    vocab: dict[str, int] = {}
    for t in _SPECIAL + _ADDED + ["\n", "\n\n", " ", "[UNK]"] + _WORDS + list(".,?!`"):
        vocab.setdefault(t, len(vocab))
    tok = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
    # Newline runs, space runs, words and single punctuation marks are tokens.
    tok.pre_tokenizer = pre_tokenizers.Split(
        Regex(r"\n+| +|[A-Za-z]+|[^\sA-Za-z]"), behavior="isolated")
    tok.decoder = decoders.Fuse()
    fast = PreTrainedTokenizerFast(
        tokenizer_object=tok, unk_token="[UNK]",
        eos_token="<|im_end|>", pad_token="<|endoftext|>")
    fast.add_special_tokens({"additional_special_tokens": _SPECIAL[1:]})
    fast.add_tokens(_ADDED)
    fast.chat_template = QWEN3_LIKE_TEMPLATE
    return fast


class _FakeDecoderLayer(nn.Module):
    """Adds 1 to feature 1; returns a tuple, as older HF decoder layers do."""

    def forward(self, hidden):
        out = hidden.clone()
        out[..., 1] += 1
        return (out,)


class _FakeInner(nn.Module):
    def __init__(self, n_layers: int):
        super().__init__()
        self.layers = nn.ModuleList(_FakeDecoderLayer() for _ in range(n_layers))


class FakeCausalLM(nn.Module):
    """Hidden state after layer k at position p: [p, k + 1, token_id, mask]."""

    HIDDEN = 4

    def __init__(self, n_layers: int = 3):
        super().__init__()
        self.model = _FakeInner(n_layers)   # ProbingModel.get_layers: model.model.layers
        self._anchor = nn.Parameter(torch.zeros(1))
        self.calls: list[dict] = []

    @property
    def device(self) -> torch.device:
        return self._anchor.device

    def forward(self, input_ids, attention_mask=None):
        b, t = input_ids.shape
        if attention_mask is None:
            attention_mask = torch.ones_like(input_ids)
        self.calls.append({"input_ids": input_ids.clone(),
                           "attention_mask": attention_mask.clone()})
        h = torch.zeros(b, t, self.HIDDEN)
        h[..., 0] = torch.arange(t, dtype=torch.float32)
        h[..., 2] = input_ids.float()
        h[..., 3] = attention_mask.float()
        for layer in self.model.layers:
            h = layer(h)[0]
        return h


def make_fake_probing_model(n_layers: int = 3, model_name: str = "Qwen/Qwen3-32B"):
    from assistant_axis.internals import ProbingModel

    return ProbingModel.from_existing(
        FakeCausalLM(n_layers), make_qwen3_like_tokenizer(), model_name=model_name)
