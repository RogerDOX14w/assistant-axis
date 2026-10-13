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

from types import SimpleNamespace

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


# Qwen3's template as a model without the think block renders it (the
# Qwen3-Instruct-2507 shape): the assistant header is the three tokens
# <|im_start|> assistant \n.  For the test that such a template fails the
# qwen3 row's seven-token expectation (multi-model plan § 9 test 2).
QWEN3_NO_THINK_BLOCK_TEMPLATE = (
    "{%- for message in messages -%}"
    "{{- '<|im_start|>' + message.role + '\n' + message.content + '<|im_end|>' + '\n' -}}"
    "{%- endfor -%}"
    "{%- if add_generation_prompt -%}"
    "{{- '<|im_start|>assistant\n' -}}"
    "{%- endif -%}"
)

# A template whose generation prompt is not how it renders a stored assistant
# turn (the prompt ends in "\n\n", the stored turn in "\n" and the think
# block), so step 2 would compute on a context step 1 never sent.
QWEN3_MISMATCHED_PROMPT_TEMPLATE = QWEN3_LIKE_TEMPLATE.replace(
    "{%- if add_generation_prompt -%}"
    "{{- '<|im_start|>assistant\n' -}}",
    "{%- if add_generation_prompt -%}"
    "{{- '<|im_start|>assistant\n\n' -}}")


def _word_level_fast_tokenizer(vocab_tokens, special, added, **kwargs):
    """A word-level ``PreTrainedTokenizerFast``: newline runs, space runs,
    words and single punctuation marks are tokens."""
    from tokenizers import Regex, Tokenizer, decoders, models, pre_tokenizers
    from transformers import PreTrainedTokenizerFast

    vocab: dict[str, int] = {}
    for t in vocab_tokens:
        vocab.setdefault(t, len(vocab))
    tok = Tokenizer(models.WordLevel(vocab=vocab, unk_token="[UNK]"))
    tok.pre_tokenizer = pre_tokenizers.Split(
        Regex(r"\n+| +|[A-Za-z]+|[^\sA-Za-z]"), behavior="isolated")
    tok.decoder = decoders.Fuse()
    post = kwargs.pop("post_processor", None)
    if post is not None:
        tok.post_processor = post(vocab)
    fast = PreTrainedTokenizerFast(tokenizer_object=tok, unk_token="[UNK]", **kwargs)
    fast.add_special_tokens({"additional_special_tokens": list(special)})
    if added:
        fast.add_tokens(list(added))
    return fast


def make_qwen3_like_tokenizer(template: str = QWEN3_LIKE_TEMPLATE):
    fast = _word_level_fast_tokenizer(
        _SPECIAL + _ADDED + ["\n", "\n\n", " ", "[UNK]"] + _WORDS + list(".,?!`"),
        _SPECIAL[1:], _ADDED, eos_token="<|im_end|>", pad_token="<|endoftext|>")
    fast.chat_template = template
    return fast


# ---------------------------------------------------------------------------
# Llama-3-like: a BOS the template writes and the tokenizer also adds to text
# ---------------------------------------------------------------------------

# Llama 3's turn format, reduced: the template writes <|begin_of_text|>, then
# <|start_header_id|>role<|end_header_id|>\n\n content <|eot_id|> per message,
# and the generation prompt is the assistant's header.  The real template also
# writes a date block into the system turn (the date pin is a TODO of the
# multi-model plan, § 15 Q6); this one does not.  The tokenizer's
# post-processor prepends <|begin_of_text|> to text, as Llama 3's does, so a
# rendered prompt tokenized as text gets a second BOS (review P1 D8).
LLAMA3_LIKE_TEMPLATE = (
    "{{- bos_token -}}"
    "{%- for message in messages -%}"
    "{{- '<|start_header_id|>' + message.role + '<|end_header_id|>\n\n' + message.content + '<|eot_id|>' -}}"
    "{%- endfor -%}"
    "{%- if add_generation_prompt -%}"
    "{{- '<|start_header_id|>assistant<|end_header_id|>\n\n' -}}"
    "{%- endif -%}"
)
LLAMA3_HEADER_TOKENS = ["<|start_header_id|>", "assistant", "<|end_header_id|>", "\n\n"]
_LLAMA_SPECIAL = ["<|begin_of_text|>", "<|start_header_id|>", "<|end_header_id|>", "<|eot_id|>",
                  "<|finetune_right_pad_id|>"]


def _bos_post_processor(vocab):
    from tokenizers import processors
    return processors.TemplateProcessing(
        single="<|begin_of_text|> $A", pair="<|begin_of_text|> $A $B",
        special_tokens=[("<|begin_of_text|>", vocab["<|begin_of_text|>"])])


def make_llama3_like_tokenizer():
    fast = _word_level_fast_tokenizer(
        _LLAMA_SPECIAL + ["\n", "\n\n", " ", "[UNK]"] + _WORDS + list(".,?!`"),
        _LLAMA_SPECIAL, (), bos_token="<|begin_of_text|>", eos_token="<|eot_id|>",
        pad_token="<|finetune_right_pad_id|>", post_processor=_bos_post_processor)
    fast.chat_template = LLAMA3_LIKE_TEMPLATE
    return fast


# ---------------------------------------------------------------------------
# gpt-oss-like (harmony): reasoning that is always on and stored
# ---------------------------------------------------------------------------

# The harmony format as far as the multi-model plan (§ 5.1) knows it, reduced:
# a system block carrying the reasoning effort, the instruction as a developer
# block, and a stored assistant turn that is the analysis channel (the
# message's "thinking") followed by the final channel.  The generation prompt
# is only <|start|>assistant: the model writes the channel tokens itself.  Not
# gpt-oss's real template (that is the TODO of § 15 Q3); enough for the layout
# derivation's test.
HARMONY_LIKE_TEMPLATE = (
    "{{- '<|start|>system<|message|>Reasoning ' + (reasoning_effort | default('medium')) + '<|end|>' -}}"
    "{%- for message in messages -%}"
    "{%- if message.role == 'system' -%}"
    "{{- '<|start|>developer<|message|>' + message.content + '<|end|>' -}}"
    "{%- elif message.role == 'user' -%}"
    "{{- '<|start|>user<|message|>' + message.content + '<|end|>' -}}"
    "{%- elif message.role == 'assistant' -%}"
    "{%- if message.thinking is defined -%}"
    "{{- '<|start|>assistant<|channel|>analysis<|message|>' + message.thinking + '<|end|>' -}}"
    "{%- endif -%}"
    "{{- '<|start|>assistant<|channel|>final<|message|>' + message.content + '<|return|>' -}}"
    "{%- endif -%}"
    "{%- endfor -%}"
    "{%- if add_generation_prompt -%}"
    "{{- '<|start|>assistant' -}}"
    "{%- endif -%}"
)
HARMONY_HEADER_TOKENS = ["<|end|>", "<|start|>", "assistant", "<|channel|>", "final", "<|message|>"]
_HARMONY_SPECIAL = ["<|endoftext|>", "<|start|>", "<|end|>", "<|message|>", "<|channel|>",
                    "<|return|>"]


def make_harmony_like_tokenizer():
    fast = _word_level_fast_tokenizer(
        _HARMONY_SPECIAL + ["\n", "\n\n", " ", "[UNK]"] + _WORDS
        + "developer analysis final Reasoning low medium".split() + list(".,?!`"),
        _HARMONY_SPECIAL[1:], (), eos_token="<|return|>", pad_token="<|endoftext|>")
    fast.chat_template = HARMONY_LIKE_TEMPLATE
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

    def __init__(self, n_layers: int = 3, model_type: str = "qwen3"):
        super().__init__()
        self.model = _FakeInner(n_layers)   # ProbingModel.get_layers: model.model.layers
        # What ProbingModel.model_type / .family read (the family table's key).
        self.config = SimpleNamespace(model_type=model_type, hidden_size=self.HIDDEN,
                                      num_hidden_layers=n_layers)
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


def make_fake_probing_model(n_layers: int = 3, model_name: str = "Qwen/Qwen3-32B",
                            model_type: str = "qwen3", tokenizer=None):
    from assistant_axis.internals import ProbingModel

    return ProbingModel.from_existing(
        FakeCausalLM(n_layers, model_type=model_type),
        tokenizer if tokenizer is not None else make_qwen3_like_tokenizer(),
        model_name=model_name)
