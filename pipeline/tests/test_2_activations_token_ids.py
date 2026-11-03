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
