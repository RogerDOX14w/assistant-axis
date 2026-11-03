"""Step 2's ids path: prefilling the ids step 1 stored (the response-token-ids
plan, reports/pipeline/response_token_ids/plan.md § 5 and § 5.8, 2026-11-02).

On the in-process fakes of assistant_axis/tests/internals_fakes.py: the
Qwen3-like word-level tokenizer and the fake causal model whose hidden state
after layer k at position p is ``[p, k + 1, token_id, attention_mask]``, so a
saved activation says which positions were averaged.  No model is loaded and
nothing is downloaded.  The text path's byte-identical comparison with the
code before the multi-model work stays test_step2_qwen3_golden.py, untouched.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import torch

from assistant_axis.internals import ActivationExtractor, ConversationEncoder
from assistant_axis.tests.internals_fakes import make_fake_probing_model

REPO_ROOT = Path(__file__).resolve().parents[2]
N_LAYERS = 3
THINKING_OFF = {"enable_thinking": False}


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "_pipeline_two_activations_token_ids", REPO_ROOT / "pipeline" / "2_activations.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture()
def pm():
    return make_fake_probing_model(N_LAYERS)


def _conv(response, system="You are a pirate"):
    conv = [{"role": "system", "content": system}] if system is not None else []
    return conv + [{"role": "user", "content": "What is law?"},
                   {"role": "assistant", "content": response}]


def _bits(t: torch.Tensor) -> torch.Tensor:
    return t.view(torch.int16) if t.dtype == torch.bfloat16 else t


CONVS = [_conv("Arr matey. Law rules!"), _conv("\n\nArr matey!\n", system=None), _conv(""),
         _conv("Yes"), _conv("The sea is wide and the law is wider still.")]


# ---------------------------------------------------------------------------
# § 5.4: batch_conversations split into batch_token_ids and a wrapper
# (§ 5.8 item 10; the golden gate is the other half)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("layer, max_length", [([0, 1, 2], 2048), ([2], 2048), (1, 2048),
                                               (None, 2048), ([0, 1, 2], 20)])
def test_batch_token_ids_gives_what_batch_conversations_gives(pm, layer, max_length):
    enc = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder="chatml")
    ex = ActivationExtractor(pm, enc)
    acts_a, meta_a = ex.batch_conversations(CONVS, layer=layer, max_length=max_length,
                                            **THINKING_OFF)
    ids, _spans, span_meta = enc.build_batch_turn_spans(CONVS, **THINKING_OFF)
    acts_b, meta_b = ex.batch_token_ids(ids, span_meta, layer=layer, max_length=max_length)
    assert acts_a.dtype == acts_b.dtype and acts_a.shape == acts_b.shape
    assert torch.equal(_bits(acts_a), _bits(acts_b))
    assert sorted(meta_a) == sorted(meta_b)
    for k in meta_a:
        if isinstance(meta_a[k], torch.Tensor):
            assert torch.equal(meta_a[k], meta_b[k]), k
        else:
            assert meta_a[k] == meta_b[k], k
    # The model saw the same ids both times.
    assert torch.equal(pm.model.calls[-1]["input_ids"], pm.model.calls[-2]["input_ids"])


def test_assemble_batch_is_what_build_batch_turn_spans_builds(pm):
    enc = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder="chatml")
    per = [enc.build_turn_spans(c, **THINKING_OFF) for c in CONVS]
    assert ConversationEncoder.assemble_batch(per) == enc.build_batch_turn_spans(
        CONVS, **THINKING_OFF)


def test_extract_batches_runs_one_forward_pass_per_batch(mod, pm):
    acts, _, _ = mod.extract_activations_batch(pm, CONVS, list(range(N_LAYERS)), batch_size=2)
    assert len(pm.model.calls) == 3 and len(acts) == len(CONVS)
    assert acts[2] is None and all(a is not None for i, a in enumerate(acts) if i != 2)


# ---------------------------------------------------------------------------
# § 5.3: the header is searched for from the span's header_anchor (§ 5.8 item 4)
# ---------------------------------------------------------------------------

def _ids(tok, text):
    return tok(text, add_special_tokens=False)["input_ids"]


def _map_one(pm, full_ids, span):
    """map_spans on one conversation whose ids are given, with the Qwen3-like
    layout; returns (activation (1+7, layers, hidden), mismatches)."""
    from assistant_axis.internals import SpanMapper
    from assistant_axis.internals.chat_layout import derive_chat_layout
    from assistant_axis.model_families import FAMILIES
    layout = derive_chat_layout(pm.tokenizer, FAMILIES["qwen3"])
    enc = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder="chatml")
    ids, spans, meta = ConversationEncoder.assemble_batch([(full_ids, [span])])
    acts, bmeta = ActivationExtractor(pm, enc).batch_token_ids(ids, meta, layer=[0, 1, 2])
    mapper = SpanMapper(pm.tokenizer, header_ids=layout.header_ids,
                        search_distance=layout.search_distance)
    convs, mismatches, roles = mapper.map_spans(acts, spans, bmeta, batch_full_ids=ids)
    assert roles == [["assistant"]]
    return convs[0][:, 0], mismatches, layout


def test_the_header_is_found_from_the_anchor_past_a_long_plan(pm):
    from assistant_axis.generation import prompt_token_ids
    tok = pm.tokenizer
    prompt = prompt_token_ids(tok, _conv("")[:-1], THINKING_OFF)      # ends with the header
    plan = _ids(tok, "Law rules " * 10)                                # 40 ids, past the reach
    assert len(plan) > 14
    content = _ids(tok, "Arr matey.")
    full = prompt + plan + content + _ids(tok, "<|im_end|>\n")
    p, c = len(prompt), len(prompt) + len(plan)
    span = {"turn": 1, "role": "assistant", "start": c, "end": c + len(content),
            "n_tokens": len(content), "text": "Arr matey."}
    act, mm, layout = _map_one(pm, full, dict(span, header_anchor=p))
    assert mm == []
    assert [act[k, 0, 0].item() for k in range(1, 8)] == list(range(p - 7, p))
    assert [int(act[k, 0, 2].item()) for k in range(1, 8)] == list(layout.header_ids)
    assert act[0, 0, 0].item() == torch.tensor(sum(range(c, c + len(content)))
                                               / len(content)).to(torch.bfloat16).item()
    # Without the anchor the search starts at the content and the plan puts the
    # header out of reach: the seven slots are NaN (what the anchor is for).
    act, mm, _ = _map_one(pm, full, span)
    assert mm and torch.isnan(act[1:]).all()


def test_an_anchor_at_the_spans_start_is_the_search_without_one(pm):
    # The text path's spans have no anchor; an anchor equal to the start
    # searches exactly as before.
    enc = ConversationEncoder(pm.tokenizer, pm.model_name, span_builder="chatml")
    full, spans = enc.build_turn_spans(_conv("\n\nArr matey!\n"), **THINKING_OFF)
    [span] = [s for s in spans if s["role"] == "assistant"]
    assert "header_anchor" not in span
    a, mm_a, _ = _map_one(pm, full, span)
    b, mm_b, _ = _map_one(pm, full, dict(span, header_anchor=span["start"]))
    assert mm_a == mm_b == [] and torch.equal(_bits(a), _bits(b))
