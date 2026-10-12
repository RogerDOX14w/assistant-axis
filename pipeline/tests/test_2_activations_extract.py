"""What pipeline/2_activations.py computes, pinned on in-process fakes.

The fake model (``assistant_axis.tests.internals_fakes.FakeCausalLM``) makes
the hidden state after decoder layer k at position p equal to
``[p, k + 1, token_id, attention_mask]``, so a saved activation says which
positions were averaged and which layer it is.  The fake tokenizer renders
the Qwen3 non-thinking assistant turn as Qwen3's template does.  No model is
loaded and nothing is downloaded.

Pinned here (the recorded 8slot vectors were made this way; changing any of
it is a decision for Roger, not a fix):

* each conversation's activation is a ``(1 + 7, n_layers, hidden)`` bf16
  tensor: slot 0 the mean over the response's content tokens (first to last
  non-whitespace token; no header, no think block, no ``<|im_end|>``),
  slots 1..7 the seven header positions ``<|im_start|> assistant \\n <think>
  \\n\\n </think> \\n\\n`` in that order;
* index j of the layer axis is the output of decoder layer ``layers[j]``
  (``model.model.layers[layers[j]]``, i.e. Hugging Face
  ``hidden_states[layers[j] + 1]``), positional in ``--layers``;
* conversations are right-padded, so padding does not move a position;
* an empty response gives no activation; a file in which no conversation
  gives one raises ``NoActivationsError`` (review of 2026-10-12) instead of
  passing as a success with nothing saved.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import torch

from assistant_axis.tests.internals_fakes import (
    QWEN3_HEADER_TOKENS,
    make_fake_probing_model,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
N_LAYERS = 3
THINKING_OFF = {"enable_thinking": False}


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def mod():
    return _load("_pipeline_two_activations_extract", "pipeline/2_activations.py")


@pytest.fixture()
def pm():
    return make_fake_probing_model(N_LAYERS)


def _conv(response, system="You are a pirate"):
    conv = [{"role": "system", "content": system}] if system is not None else []
    return conv + [
        {"role": "user", "content": "What is law?"},
        {"role": "assistant", "content": response},
    ]


def _expected_positions(tok, conv):
    """Header and content positions, found from the rendered tokens alone."""
    text = tok.apply_chat_template(conv, tokenize=False, add_generation_prompt=False,
                                   **THINKING_OFF)
    toks = tok.convert_ids_to_tokens(tok(text, add_special_tokens=False)["input_ids"])
    hdr = max(i for i, t in enumerate(toks[:-1])
              if t == "<|im_start|>" and toks[i + 1] == "assistant")
    end = toks.index("<|im_end|>", hdr)
    content = [i for i in range(hdr + 7, end)]
    while content and not tok.convert_tokens_to_string([toks[content[-1]]]).strip():
        content.pop()
    return list(range(hdr, hdr + 7)), content, toks


def _bf16(x):
    return torch.tensor(float(x)).to(torch.bfloat16).item()


def _extract(mod, pm, convs, **kw):
    kw.setdefault("layers", list(range(N_LAYERS)))
    kw.setdefault("batch_size", 8)
    return mod.extract_activations_batch(pm, convs, **kw)


def test_body_slot_is_the_mean_over_response_content_tokens(mod, pm):
    convs = [_conv("Arr matey. Law rules!"), _conv("\n\nArr matey!\n", system=None)]
    acts, mismatches, _ = _extract(mod, pm, convs)
    assert mismatches == []
    for conv, act in zip(convs, acts):
        _, content, _ = _expected_positions(pm.tokenizer, conv)
        assert act.shape == (1 + 7, N_LAYERS, 4) and act.dtype == torch.bfloat16
        for j in range(N_LAYERS):
            assert act[0, j, 0].item() == _bf16(sum(content) / len(content))
            assert act[0, j, 3].item() == 1.0          # no padding position averaged


def test_header_slots_hold_the_seven_header_positions_in_order(mod, pm):
    conv = _conv("Arr matey. Law rules!")
    acts, _, meta = _extract(mod, pm, [conv])
    header, _, toks = _expected_positions(pm.tokenizer, conv)
    assert meta["header_tokens"] == QWEN3_HEADER_TOKENS
    assert [toks[p] for p in header] == QWEN3_HEADER_TOKENS
    for k, pos in enumerate(header, start=1):
        assert acts[0][k, 0, 0].item() == pos
        assert pm.tokenizer.convert_ids_to_tokens(int(acts[0][k, 0, 2].item())) == \
            QWEN3_HEADER_TOKENS[k - 1]


def test_layer_axis_j_is_the_output_of_decoder_layer_layers_j(mod, pm):
    acts, _, _ = _extract(mod, pm, [_conv("Yes")])
    assert [acts[0][0, j, 1].item() for j in range(N_LAYERS)] == [1.0, 2.0, 3.0]
    # With a subset, the axis is positional in --layers: the file does not say
    # which layers they were (see the review's design note on --layers).
    sub, _, _ = _extract(mod, pm, [_conv("Yes")], layers=[2])
    assert sub[0].shape[1] == 1 and sub[0][0, 0, 1].item() == 3.0


def test_right_padding_leaves_a_shorter_conversation_unchanged(mod, pm):
    short, long_ = _conv("Yes", system=None), _conv("Arr matey. Law rules!")
    alone, _, _ = _extract(mod, pm, [short])
    batched, _, _ = _extract(mod, pm, [long_, short])
    assert torch.equal(alone[0], batched[1])
    mask = pm.model.calls[-1]["attention_mask"]
    assert mask[1, 0].item() == 1 and mask[1, -1].item() == 0   # padded at the end


def test_empty_response_gives_no_activation(mod, pm):
    acts, _, _ = _extract(mod, pm, [_conv(""), _conv("Yes")])
    assert acts[0] is None and acts[1] is not None


def test_truncation_averages_only_the_kept_content_tokens(mod, pm):
    conv = _conv("Arr matey. Law rules!")
    _, content, _ = _expected_positions(pm.tokenizer, conv)
    max_length = content[0] + 3                      # keep three content tokens
    acts, _, _ = _extract(mod, pm, [conv], max_length=max_length)
    kept = content[:3]
    assert acts[0][0, 0, 0].item() == _bf16(sum(kept) / len(kept))
    # A response wholly past max_length gives no activation.
    acts, _, _ = _extract(mod, pm, [conv], max_length=content[0])
    assert acts == [None]


def test_unrecognised_model_family_warns_and_drops_the_header_slots(mod, caplog):
    # The family comes from a substring of --model; a local path without
    # "qwen" in it switches the saved layout to (layers, hidden).  Until the
    # review of 2026-10-12 it did so without a word.
    pm = make_fake_probing_model(N_LAYERS, model_name="/workspace/models/q3-32b")
    acts, _, meta = _extract(mod, pm, [_conv("Arr matey.")])
    assert meta == {}
    assert acts[0].shape == (N_LAYERS, 4)
    assert "Header extraction requested but unavailable" in caplog.text


def _write_responses(path, responses):
    with open(path, "w") as f:
        for i, r in enumerate(responses):
            f.write(json.dumps({"conversation": _conv(r), "prompt_index": i % 2,
                                "question_index": i, "label": "pos"}) + "\n")


def test_process_role_saves_what_step_4_reads(mod, pm, tmp_path):
    _write_responses(tmp_path / "pirate.jsonl", ["Arr matey.", "", "Yes"])
    saved, n_mm = mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path,
                                   list(range(N_LAYERS)), batch_size=2, max_length=2048)
    assert saved and n_mm == 0
    step4 = _load("_pipeline_four_vectors_contract", "pipeline/4_vectors.py")
    acts, meta = step4.load_activations(tmp_path / "pirate.pt")
    assert sorted(acts) == ["pos_p0_q0", "pos_p0_q2"]   # the empty response is dropped
    assert meta["header_tokens"] == QWEN3_HEADER_TOKENS and meta["extract_headers"]
    # Extraction parameters, recorded since the review of 2026-10-12.
    assert meta["layers"] == list(range(N_LAYERS))
    assert (meta["max_length"], meta["thinking"], meta["batch_size"]) == (2048, False, 2)
    for v in acts.values():
        assert v.shape == (8, N_LAYERS, 4) and v.dtype == torch.bfloat16
    assert step4.compute_mean_vector(acts).shape == (8, N_LAYERS, 4)


def test_metadata_records_a_layer_subset_and_the_no_header_layout(mod, pm, tmp_path):
    # A --layers subset gives a layer axis shorter than the model's; the file
    # now says which model layer each index is.  Without header slots the
    # metadata says so too, and slot_labels still reads it as body-mean only.
    from assistant_axis.axis import slot_labels

    _write_responses(tmp_path / "pirate.jsonl", ["Arr matey."])
    mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path, [2], batch_size=4,
                     max_length=512, extract_headers=False)
    data = torch.load(tmp_path / "pirate.pt", weights_only=False)
    meta = data.pop("metadata")
    assert meta == {"extract_headers": False, "layers": [2], "max_length": 512,
                    "thinking": False, "batch_size": 4}
    (act,) = data.values()
    assert act.shape == (1, 4) and act[0, 1].item() == 3.0   # output of layers[2]
    assert slot_labels(meta) == ["body-mean"]


def test_process_role_raises_when_no_conversation_gives_an_activation(mod, pm, tmp_path):
    _write_responses(tmp_path / "mute.jsonl", ["", ""])
    with pytest.raises(mod.NoActivationsError, match="none of 2 conversations"):
        mod.process_role(pm, tmp_path / "mute.jsonl", tmp_path,
                         list(range(N_LAYERS)), batch_size=2, max_length=2048)
    assert not (tmp_path / "mute.pt").exists()


def test_process_role_on_an_empty_file_returns_false(mod, pm, tmp_path, caplog):
    (tmp_path / "blank.jsonl").write_text("")
    assert mod.process_role(pm, tmp_path / "blank.jsonl", tmp_path,
                            list(range(N_LAYERS)), batch_size=2, max_length=2048) == (False, 0)
    assert "no responses" in caplog.text
    assert not (tmp_path / "blank.pt").exists()
