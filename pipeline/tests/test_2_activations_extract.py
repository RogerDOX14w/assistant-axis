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

Since the multi-model plan (2026-10-13; reports/pipeline/coding_plan_multi_model_extraction.md
§ 9 test 5) the family comes from the model's ``config.model_type`` (the fake's
config) and the header from its chat template; an unknown type refuses, a
conversation with two assistant turns raises ``ContractError``, ``--layers``
is validated, and ``--verify_spans`` decodes the assistant spans.  The
byte-identical comparison with the code before that work is
test_step2_qwen3_golden.py.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import torch

from assistant_axis.model_families import UnknownFamilyError
from assistant_axis.tests.internals_fakes import (
    LLAMA3_HEADER_TOKENS,
    QWEN3_HEADER_TOKENS,
    make_fake_probing_model,
    make_llama3_like_tokenizer,
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


def test_unknown_model_type_refuses_to_run(mod):
    # Flagged expectation change (plan § 9 test 5; § 15 Q8): this was
    # test_unrecognised_model_family_warns_and_drops_the_header_slots.  Until
    # 2026-10-13 the family came from a substring of --model and an unknown
    # one warned and saved body means only; now the family is the model's
    # config.model_type and a type with no row refuses.
    pm = make_fake_probing_model(N_LAYERS, model_type="nope")
    with pytest.raises(UnknownFamilyError, match="nope"):
        _extract(mod, pm, [_conv("Arr matey.")])
    with pytest.raises(UnknownFamilyError):
        _extract(mod, pm, [_conv("Arr matey.")], extract_headers=False)


def test_a_local_path_finds_its_family_by_config_not_by_name(mod):
    # What the old substring rule got wrong: a path without "qwen" in it.
    pm = make_fake_probing_model(N_LAYERS, model_name="/workspace/models/q3-32b")
    acts, _, meta = _extract(mod, pm, [_conv("Arr matey.")])
    assert meta["header_tokens"] == QWEN3_HEADER_TOKENS and meta["model_type"] == "qwen3"
    assert acts[0].shape == (1 + 7, N_LAYERS, 4)


def test_a_llama_like_model_gets_its_four_header_slots(mod):
    tok = make_llama3_like_tokenizer()
    pm = make_fake_probing_model(N_LAYERS, model_name="meta-llama/x", model_type="llama",
                                 tokenizer=tok)
    conv = _conv("Arr matey. Law rules!")
    acts, mismatches, meta = _extract(mod, pm, [conv])
    assert mismatches == [] and meta["header_tokens"] == LLAMA3_HEADER_TOKENS
    assert meta["template_kwargs"] == {} and meta["model_type"] == "llama"
    ids = tok.apply_chat_template(conv, tokenize=True, return_dict=False)
    toks = tok.convert_ids_to_tokens(ids)
    hdr = max(i for i, t in enumerate(toks) if t == "<|start_header_id|>")
    act = acts[0]
    assert act.shape == (1 + 4, N_LAYERS, 4)
    for k in range(4):                                   # slot k+1 = header position k
        assert act[1 + k, 0, 0].item() == hdr + k
    end = toks.index("<|eot_id|>", hdr)
    content = list(range(hdr + 4, end))
    assert act[0, 0, 0].item() == _bf16(sum(content) / len(content))


def test_two_assistant_turns_raise_contract_error(mod, pm):
    conv = _conv("Arr matey.") + [{"role": "user", "content": "What is law?"},
                                  {"role": "assistant", "content": "Yes"}]
    with pytest.raises(mod.ContractError,
                       match="pirate: conversation 1 has 2 assistant turns; the pipeline is "
                             "single-turn"):
        _extract(mod, pm, [_conv("Yes"), conv], entity="pirate")


@pytest.mark.parametrize("spec", ["3,1", "1,1", "-1", "64", "1,x", ""])
def test_layers_subset_is_validated(mod, spec):
    with pytest.raises(mod.LayersError) as e:
        mod.parse_layers(spec, N_LAYERS)
    assert "--layers" in str(e.value)
    if spec in ("3,1", "1,1", "-1", "64"):
        assert "the model has 3 layers, 0..2" in str(e.value)


def test_layers_all_and_a_valid_subset(mod):
    assert mod.parse_layers("all", N_LAYERS) == [0, 1, 2]
    assert mod.parse_layers("0, 2", N_LAYERS) == [0, 2]


def test_verify_spans_decodes_the_stored_content(mod, pm, caplog):
    convs = [_conv("Arr matey. Law rules!"), _conv("\n\nArr matey!\n", system=None), _conv("")]
    caplog.set_level("INFO")
    assert mod.verify_assistant_spans(pm, convs, 20, entity="pirate") == []
    assert "3 of 3 assistant spans decode to the stored content" in caplog.text


def test_verify_spans_reports_a_span_that_does_not_decode_to_the_content(mod, pm, monkeypatch,
                                                                         caplog, tmp_path):
    # A span builder off by one token (what a wrong template or a BPE merge
    # across the header boundary would do): the check names both strings.
    from assistant_axis.internals.conversation import ConversationEncoder
    orig = ConversationEncoder.build_turn_spans

    def shifted(self, conversation, **kw):
        ids, spans = orig(self, conversation, **kw)
        return ids, [dict(s, end=s["end"] - 1) if s["role"] == "assistant" else s
                     for s in spans]

    monkeypatch.setattr(ConversationEncoder, "build_turn_spans", shifted)
    bad = mod.verify_assistant_spans(pm, [_conv("Arr matey.")], 20, entity="pirate")
    assert bad == [{"conversation": 0, "decoded": ["Arr matey"], "stored": ["Arr matey."]}]
    assert "pirate: conversation 0: the assistant span decodes to" in caplog.text
    _write_responses(tmp_path / "pirate.jsonl", ["Arr matey."])
    with pytest.raises(mod.SpanVerificationError, match="1 of 1 assistant spans"):
        mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path, [0], batch_size=2,
                         max_length=2048, verify_spans=5)
    assert not (tmp_path / "pirate.pt").exists()


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
    assert (meta["max_length"], meta["batch_size"]) == (2048, 2)
    # Flagged expectation change (plan § 9 test 5): "thinking" (False in every
    # file) went; model_type, template_kwargs and generation_prompt_ids came.
    assert "thinking" not in meta
    assert meta["model_type"] == "qwen3" and meta["template_kwargs"] == {"enable_thinking": False}
    assert meta["generation_prompt_ids"] == meta["header_ids"]
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
    # Flagged expectation change (plan § 9 test 5): "thinking" out,
    # model_type and template_kwargs in.
    assert meta == {"extract_headers": False, "layers": [2], "max_length": 512,
                    "batch_size": 4, "model_type": "qwen3",
                    "template_kwargs": {"enable_thinking": False}}
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


# ---------------------------------------------------------------------------
# --prefix_token_means (the cap pilot, 2026-10-28): slot 0 over the first N
# content tokens, beside the activation file, from the same forward pass.
# ---------------------------------------------------------------------------

LONG = "Arr matey. Law rules! The sea is wide and the law is wider still."


def _prefix_run(mod, pm, tmp_path, responses, prefix, **kw):
    _write_responses(tmp_path / "pirate.jsonl", responses)
    kw.setdefault("batch_size", 2)
    kw.setdefault("max_length", 2048)
    saved = mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path, kw.pop("layers", [0, 1, 2]),
                             prefix_tokens=prefix, **kw)
    acts = torch.load(tmp_path / "pirate.pt", weights_only=False)
    pfx = torch.load(tmp_path / "prefix_means" / "pirate.pt", weights_only=False)
    return saved, acts, pfx


def test_a_full_length_prefix_mean_is_slot_0_bit_for_bit(mod, pm, tmp_path):
    _, acts, pfx = _prefix_run(mod, pm, tmp_path, [LONG, "Yes", "Arr matey."], [2, 1000])
    meta = pfx.pop("metadata")
    acts.pop("metadata")
    assert sorted(pfx) == sorted(acts)                   # keyed exactly as the activations
    for k, act in acts.items():
        assert pfx[k].shape == (2, N_LAYERS, 4) and pfx[k].dtype == act.dtype == torch.bfloat16
        assert torch.equal(pfx[k][1].view(torch.int16), act[0].view(torch.int16))
        assert meta["short"][k] == [meta["n_content_tokens"][k] < 2, True]


def test_a_prefix_mean_is_the_mean_of_the_first_n_content_positions(mod, pm, tmp_path):
    _, _, pfx = _prefix_run(mod, pm, tmp_path, [LONG], [1, 3, 5])
    _, content, _ = _expected_positions(pm.tokenizer, _conv(LONG))
    assert len(content) > 5
    row = pfx["pos_p0_q0"]
    for i, n in enumerate([1, 3, 5]):
        for j in range(N_LAYERS):
            assert row[i, j, 0].item() == _bf16(sum(content[:n]) / n)
            assert row[i, j, 1].item() == j + 1             # the layer
    assert pfx["metadata"]["n_content_tokens"] == {"pos_p0_q0": len(content)}
    assert pfx["metadata"]["short"] == {"pos_p0_q0": [False, False, False]}


def test_a_short_response_gives_its_full_mean_and_is_marked(mod, pm, tmp_path):
    _, acts, pfx = _prefix_run(mod, pm, tmp_path, ["Yes", LONG], [3, 1000])
    _, content, _ = _expected_positions(pm.tokenizer, _conv("Yes"))
    meta = pfx["metadata"]
    assert meta["n_content_tokens"]["pos_p0_q0"] == len(content) < 3
    assert meta["short"]["pos_p0_q0"] == [True, True]
    assert meta["short"]["pos_p1_q1"] == [False, True]
    short = pfx["pos_p0_q0"]
    assert torch.equal(short[0], short[1]) and torch.equal(short[0], acts["pos_p0_q0"][0])


def test_prefix_means_follow_the_truncation_and_drop_rules(mod, pm, tmp_path):
    # Cut at max_length: the prefix sees only the kept tokens, as slot 0 does;
    # an empty response has neither an activation nor a prefix mean.
    _, content, _ = _expected_positions(pm.tokenizer, _conv(LONG))
    max_length = content[0] + 4
    _, acts, pfx = _prefix_run(mod, pm, tmp_path, [LONG, ""], [2, 6], max_length=max_length)
    assert "pos_p1_q1" not in pfx and "pos_p1_q1" not in acts
    assert pfx["metadata"]["n_content_tokens"] == {"pos_p0_q0": 4}
    assert pfx["metadata"]["short"]["pos_p0_q0"] == [False, True]
    assert torch.equal(pfx["pos_p0_q0"][1], acts["pos_p0_q0"][0])


def test_the_flag_is_recorded_in_the_prefix_files_metadata(mod, pm, tmp_path):
    _, acts, pfx = _prefix_run(mod, pm, tmp_path, [LONG], [2, 4])
    meta, ameta = pfx["metadata"], acts["metadata"]
    assert meta["prefix_tokens"] == [2, 4]
    assert meta["layers"] == meta["activation_layers"] == ameta["layers"] == [0, 1, 2]
    for k in ("model_type", "template_kwargs", "header_tokens", "max_length", "batch_size"):
        assert meta[k] == ameta[k]
    # the activation file is what it is without the flag
    assert "prefix_tokens" not in ameta


def test_prefix_layers_keep_a_subset_of_the_extracted_layers(mod, pm, tmp_path):
    _, acts, pfx = _prefix_run(mod, pm, tmp_path, [LONG], [2], prefix_layers=[2])
    assert pfx["pos_p0_q0"].shape == (1, 1, 4) and pfx["pos_p0_q0"][0, 0, 1].item() == 3.0
    assert pfx["metadata"]["layers"] == [2] and pfx["metadata"]["activation_layers"] == [0, 1, 2]
    assert acts["pos_p0_q0"].shape == (8, N_LAYERS, 4)
    with pytest.raises(ValueError, match="not among the extracted layers"):
        mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path / "other", [0, 1],
                         batch_size=2, max_length=2048, prefix_tokens=[2], prefix_layers=[2])


def test_off_by_default_no_prefix_file(mod, pm, tmp_path):
    _write_responses(tmp_path / "pirate.jsonl", [LONG])
    mod.process_role(pm, tmp_path / "pirate.jsonl", tmp_path, [0, 1, 2], batch_size=2,
                     max_length=2048)
    assert (tmp_path / "pirate.pt").exists() and not (tmp_path / "prefix_means").exists()


def test_the_skip_rule_covers_both_files(mod, pm, tmp_path):
    out = tmp_path / "acts"
    out.mkdir()
    _write_responses(tmp_path / "pirate.jsonl", [LONG, "Yes"])
    _write_responses(tmp_path / "parrot.jsonl", ["Squawk"])
    # A tree extracted without the flag: both entities pending once it is given.
    for name in ("pirate", "parrot"):
        mod.process_role(pm, tmp_path / f"{name}.jsonl", out, [0, 1, 2], batch_size=2,
                         max_length=2048)
    assert mod.pending_response_files(tmp_path, out) == []
    assert [f.stem for f in mod.pending_response_files(tmp_path, out, prefix_means=True)] == \
        ["parrot", "pirate"]
    before = (out / "pirate.pt").read_bytes()
    mod.process_role(pm, tmp_path / "pirate.jsonl", out, [0, 1, 2], batch_size=2,
                     max_length=2048, prefix_tokens=[2])
    assert (out / "pirate.pt").read_bytes() == before     # the activation file is not rewritten
    assert (out / "prefix_means" / "pirate.pt").exists()
    assert [f.stem for f in mod.pending_response_files(tmp_path, out, prefix_means=True)] == \
        ["parrot"]
    # Both files there: nothing is computed (no forward pass).
    n_calls = len(pm.model.calls)
    assert mod.process_role(pm, tmp_path / "pirate.jsonl", out, [0, 1, 2], batch_size=2,
                            max_length=2048, prefix_tokens=[2]) == (True, 0)
    assert len(pm.model.calls) == n_calls


def test_extract_with_prefix_means_pairs_each_activation(mod, pm):
    convs = [_conv(""), _conv(LONG), _conv("Yes")]
    acts, pfx, _, _ = mod.extract_activations_with_prefix_means(
        pm, convs, [0, 1, 2], [2], batch_size=2)
    assert acts[0] is None and pfx[0] is None
    assert all(p is not None and p[0].shape == (1, N_LAYERS, 4) for p in pfx[1:])
    # The same activations as without the flag.
    plain, _, _ = _extract(mod, pm, convs, batch_size=2)
    assert all(torch.equal(a, b) for a, b in zip(acts[1:], plain[1:]))


@pytest.mark.parametrize("spec", ["512,256", "0,1", "256,256", "x", ""])
def test_prefix_token_counts_are_validated(mod, spec):
    import argparse
    with pytest.raises(argparse.ArgumentTypeError, match="--prefix_token_means"):
        mod.parse_prefix_tokens(spec)
    assert mod.parse_prefix_tokens("256, 512,768") == [256, 512, 768]
