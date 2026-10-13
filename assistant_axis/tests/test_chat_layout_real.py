"""The family rows against the real tokenizers (multi-model plan § 9 test 11).

**Skipped unless ``ASSISTANT_AXIS_HF_TESTS=1``.**  It downloads each family's
tokenizer and ``config.json`` (tokenizer files only, about 10-20 MB each; no
weights; Llama and Gemma are gated, so Roger's Hugging Face token must be
set).  Per § 15 Q5 these downloads happen on the pod, before each family's
smoke run, never on the Mac; an agent does not look in a cache to see whether
a tokenizer is there.  ``ASSISTANT_AXIS_HF_FAMILIES=qwen3,llama`` limits the
run to those rows.  Run it with ``-s`` to see the derived layouts, which are
what Roger reads before a row is pinned:

    ASSISTANT_AXIS_HF_TESTS=1 ASSISTANT_AXIS_HF_FAMILIES=qwen3 \\
        uv run pytest -s assistant_axis/tests/test_chat_layout_real.py

This is where the "to check" cells of the family table
(``assistant_axis.model_families.TO_CHECK``) become assertions: the
``model_type`` key, the derived header against ``DRAFT_HEADERS`` (and the
pinned ``qwen3`` ids), the system-prompt behaviour, the BOS, and the assistant
span decoding to the content under the row's span builder.
"""
from __future__ import annotations

import os

import pytest

from assistant_axis.model_families import DRAFT_HEADERS, FAMILIES, QWEN3_NON_THINKING_HEADER_IDS

pytestmark = pytest.mark.skipif(
    os.environ.get("ASSISTANT_AXIS_HF_TESTS") != "1",
    reason="real tokenizers: set ASSISTANT_AXIS_HF_TESTS=1 (on the pod; plan § 15 Q5)")

# The checkpoint each row is checked on (the plan's § 5.2 candidates; § 15 Q6
# leaves the OLMo and gpt-oss choice open, and gpt_oss is a TODO row).
FAMILY_MODELS = {
    "qwen3": "Qwen/Qwen3-32B",
    "llama": "meta-llama/Llama-3.3-70B-Instruct",
    "gemma2": "google/gemma-2-27b-it",
    "olmo2": "allenai/OLMo-2-0325-32B-Instruct",
    "olmo3": "allenai/Olmo-3-7B-Instruct",
}


def _selected():
    wanted = os.environ.get("ASSISTANT_AXIS_HF_FAMILIES")
    keys = sorted(FAMILY_MODELS)
    return [k for k in keys if not wanted or k in wanted.split(",")]


@pytest.fixture(scope="module", params=_selected())
def family_and_tokenizer(request):
    from transformers import AutoConfig, AutoTokenizer
    key = request.param
    model = FAMILY_MODELS[key]
    cfg = AutoConfig.from_pretrained(model)
    tok = AutoTokenizer.from_pretrained(model)
    return key, model, cfg, tok


def test_model_type_is_the_rows_key(family_and_tokenizer):
    key, model, cfg, _ = family_and_tokenizer
    assert cfg.model_type == key, f"{model}: config.model_type is {cfg.model_type!r}"


def test_derived_header_matches_the_draft(family_and_tokenizer):
    from assistant_axis.internals.chat_layout import derive_chat_layout
    key, model, _, tok = family_and_tokenizer
    layout = derive_chat_layout(tok, FAMILIES[key])     # asserts qwen3's pinned tokens
    print(f"\n{model} ({key}): header {list(layout.header_tokens)!r} ids "
          f"{list(layout.header_ids)}; generation prompt "
          f"{tok.decode(list(layout.generation_prompt_ids))!r}; search distance "
          f"{layout.search_distance}")
    if key == "qwen3":
        assert layout.header_ids == QWEN3_NON_THINKING_HEADER_IDS
    if key in DRAFT_HEADERS:
        tokens, ids = DRAFT_HEADERS[key]
        assert layout.header_tokens == tokens
        if ids is not None:
            assert layout.header_ids == ids


def test_system_prompt_behaviour_matches_the_row(family_and_tokenizer):
    from assistant_axis.generation import system_prompt_mode
    key, model, _, tok = family_and_tokenizer
    assert system_prompt_mode(tok) == FAMILIES[key].system_prompt, model


def test_the_prompt_ids_carry_one_bos_where_the_template_writes_one(family_and_tokenizer):
    from assistant_axis.generation import prompt_token_ids
    key, model, _, tok = family_and_tokenizer
    row = FAMILIES[key]
    conv = [{"role": "user", "content": "What is law?"}]
    ids = prompt_token_ids(tok, conv, row.template_kwargs)
    n_bos = ids.count(tok.bos_token_id) if tok.bos_token_id is not None else 0
    print(f"\n{model}: {n_bos} BOS in the prompt ids; template text mentions date_string: "
          f"{'date_string' in (tok.chat_template or '')}, strftime_now: "
          f"{'strftime_now' in (tok.chat_template or '')}")
    assert n_bos == (1 if row.bos_in_template else 0), model


def test_the_assistant_span_decodes_to_the_content(family_and_tokenizer):
    from assistant_axis.internals.conversation import ConversationEncoder
    key, model, _, tok = family_and_tokenizer
    row = FAMILIES[key]
    enc = ConversationEncoder(tok, model, span_builder=row.span_builder)
    system = ([{"role": "system", "content": "You are a pirate."}]
              if row.system_prompt == "native" else [])
    for content in ("Arr matey. The law is what the captain says!",
                    "\n\nLaw, you ask?\nIt is the code.\n",
                    "1. Rules\n2. Order"):
        conv = system + [{"role": "user", "content": "What is law?"},
                         {"role": "assistant", "content": content}]
        ids, spans = enc.build_turn_spans(conv, **dict(row.template_kwargs))
        [a] = [s for s in spans if s["role"] == "assistant"]
        decoded = tok.decode(ids[a["start"]:a["end"]], clean_up_tokenization_spaces=False)
        assert decoded.strip() == content.strip(), (model, decoded, content)
