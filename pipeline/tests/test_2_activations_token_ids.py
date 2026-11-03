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


def _stored(mod, tok, content, *, plan=None, stop=True, extra=(), lead=""):
    """What step 1 would store for ``content``: the ids of ``plan`` and
    ``</think>`` (a stripped record) and of ``lead`` (the ``"\\n\\n"`` the strip
    takes after it), the content's ids, ``extra`` ids past the range (a
    partial character at the cap) and the stop token; the range is the
    content's ids, starting after the lead, as step 1 points since
    2026-11-03 (until then the range started at the lead)."""
    ids = []
    if plan is not None:
        ids += _ids(tok, plan) + [tok.convert_tokens_to_ids("</think>")]
    ids += _ids(tok, lead) if lead else []
    start = len(ids)
    ids += _ids(tok, content)
    end = len(ids)
    ids += list(extra)
    if stop:
        ids.append(tok.convert_tokens_to_ids("<|im_end|>"))
    return mod.StoredTokens(ids=ids, content_range=(start, end))


def _bf16(x):
    return torch.tensor(float(x)).to(torch.bfloat16).item()


# ---------------------------------------------------------------------------
# § 5.2: the sequence the ids path prefills, through extract_activations_batch
# ---------------------------------------------------------------------------

def test_the_end_of_turn_is_read_off_the_template(pm):
    from assistant_axis.internals.chat_layout import derive_turn_end_ids
    from assistant_axis.model_families import FAMILIES
    from assistant_axis.tests.internals_fakes import make_llama3_like_tokenizer
    tok = pm.tokenizer
    assert list(derive_turn_end_ids(tok, FAMILIES["qwen3"])) == tok.convert_tokens_to_ids(
        ["<|im_end|>", "\n"])
    llama = make_llama3_like_tokenizer()
    assert list(derive_turn_end_ids(llama, FAMILIES["llama"])) == [
        llama.convert_tokens_to_ids("<|eot_id|>")]


# Flagged change of test data (Roger, 2026-11-03): " Yes" and "Yes \n" were
# here, and gave equal activations only because the ids path trimmed
# boundary whitespace as the text path does; it no longer trims, so contents
# with whitespace at their ends are the boundary-whitespace case below
# (test_a_trailing_newline_is_averaged_as_stored_on_the_ids_path).
EQUIVALENT = ["Arr matey. Law rules!", "Yes", "Law rules.", "", "The sea is wide."]


def test_ids_equal_to_the_re_encoding_give_the_text_paths_activations(mod, pm):
    # § 5.8 item 1 at the extraction level: stored ids that are the content's
    # re-encoding (plus the stop token) give bit-identical activations, for a
    # content with no whitespace at its ends.
    convs = [_conv(c, system=None if i % 2 else "You are a pirate")
             for i, c in enumerate(EQUIVALENT)]
    records = [_stored(mod, pm.tokenizer, c) for c in EQUIVALENT]
    text, mm_t, meta_t = mod.extract_activations_batch(pm, convs, [0, 1, 2], batch_size=2)
    text_ids = [c["input_ids"] for c in pm.model.calls]
    ids, mm_i, meta_i = mod.extract_activations_batch(pm, convs, [0, 1, 2], batch_size=2,
                                                      token_records=records)
    ids_ids = [c["input_ids"] for c in pm.model.calls[len(text_ids):]]
    assert len(ids_ids) == len(text_ids) == 3                 # the model saw the same ids
    assert all(torch.equal(a, b) for a, b in zip(text_ids, ids_ids))
    assert mm_t == mm_i == [] and meta_t == meta_i
    assert [a is None for a in text] == [a is None for a in ids] == [False, False, False, True,
                                                                     False]
    for a, b in zip(text, ids):
        if a is not None:
            assert torch.equal(_bits(a), _bits(b))


def test_a_llama_like_model_takes_the_ids_path_too(mod):
    from assistant_axis.tests.internals_fakes import make_llama3_like_tokenizer
    tok = make_llama3_like_tokenizer()
    pm = make_fake_probing_model(N_LAYERS, model_name="meta-llama/x", model_type="llama",
                                 tokenizer=tok)
    convs = [_conv("Arr matey. Law rules!"), _conv("Yes")]
    eot = tok.convert_tokens_to_ids("<|eot_id|>")
    records = [mod.StoredTokens(ids=_ids(tok, c[-1]["content"]) + [eot],
                                content_range=(0, len(_ids(tok, c[-1]["content"]))))
               for c in convs]
    text, _, _ = mod.extract_activations_batch(pm, convs, [0, 1, 2])
    ids, _, _ = mod.extract_activations_batch(pm, convs, [0, 1, 2], token_records=records)
    assert torch.equal(pm.model.calls[0]["input_ids"], pm.model.calls[1]["input_ids"])
    assert all(torch.equal(_bits(a), _bits(b)) for a, b in zip(text, ids))


def test_the_plan_is_prefilled_and_slot_0_is_the_content_only(mod, pm):
    # § 5.8 item 3: a stripped record, "plan </think> \n\n content".  Slot 0 is
    # the content only because step 1's range starts after the "\n\n" (since
    # 2026-11-03; the ids path trims nothing).
    tok = pm.tokenizer
    conv = _conv("Arr matey.")
    rec = _stored(mod, tok, "Arr matey.", plan="Law rules. Yes no.", lead="\n\n")
    [act], mm, meta = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec])
    from assistant_axis.generation import prompt_token_ids
    prompt = prompt_token_ids(tok, conv[:-1], THINKING_OFF)
    p, k, e = len(prompt), rec.content_range[0], rec.content_range[1]
    seen = pm.model.calls[-1]["input_ids"][0].tolist()
    assert seen[:p] == prompt
    assert seen[p:p + k] == rec.ids[:k]                       # plan, </think>, \n\n: after header
    assert tok.decode(rec.ids[k - 2:k]) == "</think>\n\n"
    assert seen[p + k:] == rec.ids[k:-1] + tok.convert_tokens_to_ids(["<|im_end|>", "\n"])
    content = list(range(p + k, p + e))                       # the stored range, as stored
    assert tok.decode([seen[i] for i in content]) == "Arr matey."
    assert act[0, 0, 0].item() == _bf16(sum(content) / len(content))
    assert [act[j, 0, 0].item() for j in range(1, 8)] == list(range(p - 7, p))
    assert [int(act[j, 0, 2].item()) for j in range(1, 8)] == meta["header_ids"]
    assert mm == []


def test_the_stop_token_and_the_end_of_turn(mod, pm):
    # § 5.8 item 6: ids ending in the stop token and ids without it give the
    # same slots, and the sequence ends in the template's end of turn once.
    tok = pm.tokenizer
    conv = _conv("Arr matey.")
    with_stop = _stored(mod, tok, "Arr matey.")
    without = _stored(mod, tok, "Arr matey.", stop=False)
    [a], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[with_stop])
    seen_a = pm.model.calls[-1]["input_ids"][0].tolist()
    [b], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[without])
    seen_b = pm.model.calls[-1]["input_ids"][0].tolist()
    assert seen_a == seen_b and torch.equal(_bits(a), _bits(b))
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    assert seen_a[-2:] == [im_end, tok.convert_tokens_to_ids("\n")]
    assert seen_a.count(im_end) == 3                          # system, user, assistant


def test_a_sampled_special_token_is_prefilled_and_averaged(mod, pm):
    # § 5.8 item 7: a special token the model sampled inside the content.
    tok = pm.tokenizer
    special = tok.convert_tokens_to_ids("<|endoftext|>")
    arr, matey = _ids(tok, "Arr "), _ids(tok, "matey.")
    rec = mod.StoredTokens(ids=arr + [special] + matey + [tok.convert_tokens_to_ids("<|im_end|>")],
                           content_range=(0, len(arr) + 1 + len(matey)))
    conv = _conv("Arr matey.")                                # the text has no special token
    [ids_act], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec])
    seen = pm.model.calls[-1]["input_ids"][0].tolist()
    [text_act], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2])
    assert special in seen[:-2]
    assert special not in pm.model.calls[-1]["input_ids"][0].tolist()[:-1]
    from assistant_axis.generation import prompt_token_ids
    p = len(prompt_token_ids(tok, conv[:-1], THINKING_OFF))
    span = list(range(p, p + len(arr) + 1 + len(matey)))       # the special token included
    assert ids_act[0, 0, 0].item() == _bf16(sum(span) / len(span))
    assert ids_act[0, 0, 2].item() == _bf16(sum(seen[i] for i in span) / len(span))
    assert not torch.equal(_bits(ids_act[0]), _bits(text_act[0]))


def test_ids_past_the_range_are_prefilled_and_not_averaged(mod, pm):
    # § 5.8 item 8: a partial character at the cap; its ids are not behind
    # the text, so the range ends before them.
    tok = pm.tokenizer
    extra = _ids(tok, "??")                                   # not special, so not stripped
    rec = _stored(mod, tok, "Arr matey", stop=False, extra=extra)
    conv = _conv("Arr matey")
    [act], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec])
    seen = pm.model.calls[-1]["input_ids"][0].tolist()
    from assistant_axis.generation import prompt_token_ids
    p = len(prompt_token_ids(tok, conv[:-1], THINKING_OFF))
    assert seen[p + 3:p + 5] == extra                         # prefilled
    assert act[0, 0, 0].item() == _bf16(sum(range(p, p + 3)) / 3)   # "Arr", " ", "matey" only


def test_a_range_that_does_not_fit_its_ids_raises(mod, pm):
    tok = pm.tokenizer
    ids = _ids(tok, "Arr matey.") + [tok.convert_tokens_to_ids("<|im_end|>")]
    for bad in ((0, len(ids)), (3, 2), (-1, 2)):               # the stop token; reversed; negative
        with pytest.raises(mod.TokenSourceError, match="does not fit"):
            mod.extract_activations_batch(pm, [_conv("Arr matey.")], [0],
                                          token_records=[mod.StoredTokens(ids, bad)],
                                          entity="pirate")


def test_the_ids_path_needs_the_conversation_to_end_in_its_assistant_turn(mod, pm):
    tok = pm.tokenizer
    rec = _stored(mod, tok, "Yes")
    two = _conv("Arr.") + [{"role": "user", "content": "What is law?"},
                           {"role": "assistant", "content": "Yes"}]
    for conv in (two, _conv("Yes")[:-1]):
        with pytest.raises(mod.ContractError, match="pirate: conversation 0"):
            mod.extract_activations_batch(pm, [conv], [0], token_records=[rec], entity="pirate")


def test_a_trailing_newline_is_averaged_as_stored_on_the_ids_path(mod, pm):
    # Roger, 2026-11-03: the ids path trims nothing; the text path's chatml
    # builder still drops whitespace-only tokens at the ends (its own rule,
    # kept so that the text arm is today's step 2).  This replaces
    # test_the_boundary_trim_is_the_text_paths_rule.
    from assistant_axis.generation import prompt_token_ids
    tok = pm.tokenizer
    conv = _conv("Arr matey.\n")
    rec = _stored(mod, tok, "Arr matey.\n")                   # Arr, " ", matey, ".", \n
    p = len(prompt_token_ids(tok, conv[:-1], THINKING_OFF))
    [ids_act], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec])
    ids_seen = pm.model.calls[-1]["input_ids"]
    [text_act], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2])
    assert torch.equal(ids_seen, pm.model.calls[-1]["input_ids"])   # the same ids
    assert ids_act[0, 0, 0].item() == _bf16(sum(range(p, p + 5)) / 5)    # the newline included
    assert text_act[0, 0, 0].item() == _bf16(sum(range(p, p + 4)) / 4)   # the text path drops it
    assert torch.equal(_bits(ids_act[1:]), _bits(text_act[1:]))          # the same header slots
    # The text path's rule itself, unchanged.
    enc = ConversationEncoder(tok, pm.model_name, span_builder="chatml")
    full = _ids(tok, "\n\n Arr matey. \n")          # \n\n, " ", Arr, " ", matey, ".", " ", \n
    assert enc.trim_boundary_whitespace(full, list(range(len(full)))) == [2, 3, 4, 5]
    assert enc.trim_boundary_whitespace(full, []) == []


# ---------------------------------------------------------------------------
# § 5.1: which path a record takes, through process_role (§ 5.8 items 1, 2, 5)
# ---------------------------------------------------------------------------

def _record(i, content, *, stored=None, null_range=False):
    """A response record as step 1 writes it (the keys step 2 reads), with
    ``stored`` (a StoredTokens) as response_token_ids / content_token_range."""
    rec = {"conversation": _conv(content), "prompt_index": i % 2, "question_index": i,
           "label": "pos"}
    if stored is not None:
        rec["response_token_ids"] = list(stored.ids)
        rec["content_token_range"] = None if null_range else list(stored.content_range)
    return rec


def _write_jsonl(path, records):
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def _run(mod, pm, out_dir, records, **kw):
    f = _write_jsonl(out_dir / "pirate.jsonl", records)
    kw.setdefault("batch_size", 2)
    kw.setdefault("max_length", 2048)
    saved, _ = mod.process_role(pm, f, out_dir, [0, 1, 2], **kw)
    assert saved
    acts = torch.load(out_dir / "pirate.pt", weights_only=False)
    return acts, acts.pop("metadata")


def _canonical_bytes(path) -> bytes:
    """A file's content as bytes that do not depend on memory addresses: the
    file loaded and saved again in torch's zip format, whose storage keys are
    numbered in the order the pickle meets them.  The legacy format step 2
    writes (``use_zipfile_serialization=False``) keys each storage by its
    address (``str(storage._cdata)``) and writes the storages in the order of
    those keys, so two runs of the same code on the same records never write
    the same bytes.  Everything else survives the round trip and is compared
    byte for byte: the dict's keys in order, the metadata, each tensor's
    dtype, shape, strides, offset and storage, every byte of its data."""
    import io
    buf = io.BytesIO()
    torch.save(torch.load(path, weights_only=False), buf)
    return buf.getvalue()


def _same_tensors(a, b):
    assert sorted(a) == sorted(b)
    for k in a:
        assert a[k].dtype == b[k].dtype and a[k].shape == b[k].shape, k
        assert torch.equal(_bits(a[k]), _bits(b[k])), k


def test_ids_and_text_give_bit_identical_files_when_the_ids_are_the_re_encoding(mod, pm, tmp_path):
    # § 5.8 item 1: every activation (all eight slots), the prefix means and
    # every metadata key but the counts.
    recs = [_record(i, c, stored=_stored(mod, pm.tokenizer, c)) for i, c in enumerate(EQUIVALENT)]
    out = {}
    for source in ("ids", "text"):
        acts, meta = _run(mod, pm, tmp_path / source, recs, token_source=source,
                          prefix_tokens=[2, 1000])
        pfx = torch.load(tmp_path / source / "prefix_means" / "pirate.pt", weights_only=False)
        out[source] = (acts, meta, pfx, pfx.pop("metadata"))
    (a, ma, pa, pma), (b, mb, pb, pmb) = out["ids"], out["text"]
    assert ma.pop("token_source") == pma.pop("token_source") == {"ids": 5, "text": 0,
                                                                 "range_null": 0}
    assert mb.pop("token_source") == pmb.pop("token_source") == {"ids": 0, "text": 5,
                                                                 "range_null": 0}
    assert ma == mb and pma == pmb
    assert len(a) == 4                                       # the empty response has none
    _same_tensors(a, b)
    _same_tensors(pa, pb)


def test_the_text_arm_is_todays_step_2(mod, pm, tmp_path):
    # § 5.8 item 2: --token_source text on records with ids gives the same
    # bytes as the same records without them (auto on them is the text path),
    # but for the storage keys, which are memory addresses (_canonical_bytes).
    tok = pm.tokenizer
    plan = "Law rules. Yes no."
    with_ids = [_record(0, "Arr matey.", stored=_stored(mod, tok, "Arr matey.", plan=plan,
                                                         lead="\n\n")),
                _record(1, "Yes", stored=_stored(mod, tok, "Yes")),
                _record(2, "Arr.", stored=_stored(mod, tok, "Arr."), null_range=True)]
    without = [{k: v for k, v in r.items()
                if k not in ("response_token_ids", "content_token_range")} for r in with_ids]
    _run(mod, pm, tmp_path / "text", with_ids, token_source="text", prefix_tokens=[2])
    _run(mod, pm, tmp_path / "plain", without, prefix_tokens=[2])
    for rel in ("pirate.pt", "prefix_means/pirate.pt"):
        assert (_canonical_bytes(tmp_path / "text" / rel)
                == _canonical_bytes(tmp_path / "plain" / rel)), rel
    # The canonical form is not hiding a difference: the ids path on the
    # same records (the plan prefilled) does not compare equal.
    _run(mod, pm, tmp_path / "ids", with_ids, prefix_tokens=[2])
    assert _canonical_bytes(tmp_path / "ids" / "pirate.pt") != _canonical_bytes(
        tmp_path / "plain" / "pirate.pt")


def test_the_canonical_bytes_ignore_addresses_and_nothing_else(tmp_path):
    # Legacy saves of equal tensors at different addresses: other bytes, the
    # same canonical bytes; one bit of difference, or another key order, is
    # not the same.
    keep = []

    def save(name, d):
        keep.append(d)                                      # alive: distinct addresses
        torch.save(d, tmp_path / name, _use_new_zipfile_serialization=False)
        return tmp_path / name

    def make():
        return {"a": torch.arange(4, dtype=torch.bfloat16),
                "b": torch.ones(3, dtype=torch.bfloat16), "metadata": {"layers": [0]}}

    x, y = save("x.pt", make()), save("y.pt", make())
    assert x.read_bytes() != y.read_bytes()
    assert _canonical_bytes(x) == _canonical_bytes(y)
    flipped = make()
    flipped["b"].view(torch.int16)[1] ^= 1
    assert _canonical_bytes(save("z.pt", flipped)) != _canonical_bytes(x)
    reordered = dict(reversed(list(make().items())))
    assert _canonical_bytes(save("w.pt", reordered)) != _canonical_bytes(x)


def test_a_mixed_file_takes_both_paths_and_counts_them(mod, pm, tmp_path, caplog):
    # § 5.8 item 5: a record with a null range takes the text path under auto.
    tok = pm.tokenizer
    stored = _stored(mod, tok, "Arr matey.", plan="Law rules. Yes no.", lead="\n\n")
    recs = [_record(0, "Arr matey.", stored=stored),
            _record(1, "Arr matey.", stored=stored, null_range=True)]
    with caplog.at_level("INFO"):
        acts, meta = _run(mod, pm, tmp_path / "auto", recs)
    assert meta["token_source"] == {"ids": 1, "text": 1, "range_null": 1}
    assert "1 of 2 records have stored ids whose range is null" in caplog.text
    # Record 0 is the ids path's (the plan is prefilled, so the content sits
    # later), record 1 the text path's.
    [ids_act], _, _ = mod.extract_activations_batch(pm, [recs[0]["conversation"]], [0, 1, 2],
                                                    token_records=[stored])
    [text_act], _, _ = mod.extract_activations_batch(pm, [recs[1]["conversation"]], [0, 1, 2])
    assert torch.equal(_bits(acts["pos_p0_q0"]), _bits(ids_act))
    assert torch.equal(_bits(acts["pos_p1_q1"]), _bits(text_act))
    assert acts["pos_p0_q0"][0, 0, 0].item() > acts["pos_p1_q1"][0, 0, 0].item()
    # ... and --token_source ids refuses the file, naming the record.
    with pytest.raises(mod.TokenSourceError, match=r"1 of 2 records cannot take the ids "
                                                   r"path: pos_p1_q1 \(a null range\)"):
        _run(mod, pm, tmp_path / "ids", recs, token_source="ids")
    assert not (tmp_path / "ids" / "pirate.pt").exists()


def test_ids_without_a_range_key_take_the_text_path(mod, pm, tmp_path):
    # A record with ids and no content_token_range at all (written by a step 1
    # that kept the ids before it checked the ranges): the text path under auto.
    rec = _record(0, "Yes", stored=_stored(mod, pm.tokenizer, "Yes"))
    del rec["content_token_range"]
    _, meta = _run(mod, pm, tmp_path, [rec])
    assert meta["token_source"] == {"ids": 0, "text": 1, "range_null": 1}
    with pytest.raises(mod.TokenSourceError, match="no stored ids|a null range"):
        mod.select_token_paths([_record(0, "Yes")], "ids", entity="pirate")


def test_a_range_that_is_not_two_integers_raises(mod):
    rec = _record(0, "Yes", stored=mod.StoredTokens([1, 2], (0, 1)))
    for bad in ([0], [0, 1, 2], ["0", "1"], [0.0, 1.0], [True, 1]):
        rec["content_token_range"] = bad
        with pytest.raises(mod.TokenSourceError, match="is not \\[start, end\\]"):
            mod.select_token_paths([rec], "auto", entity="pirate")


def test_the_token_source_flag(mod):
    p = mod.build_parser()
    base = ["--model", "m", "--responses_dir", "r", "--output_dir", "o"]
    assert p.parse_args(base).token_source == "auto"
    assert p.parse_args(base + ["--token_source", "ids"]).token_source == "ids"
    with pytest.raises(SystemExit):
        p.parse_args(base + ["--token_source", "both"])
    assert set(mod.TOKEN_SOURCES) == {"auto", "ids", "text"}


# ---------------------------------------------------------------------------
# § 5.5: --content_span turn, slot 0 over the whole generated turn (§ 5.8 item 3)
# ---------------------------------------------------------------------------

def test_content_span_turn_averages_the_plan_and_the_content(mod, pm, tmp_path):
    from assistant_axis.generation import prompt_token_ids
    tok = pm.tokenizer
    conv = _conv("Arr matey.")
    rec = _stored(mod, tok, "Arr matey.", plan="\n Law rules. Yes no.", lead="\n\n")
    [rng], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec])
    [turn], mm, meta = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[rec],
                                                     content_span="turn")
    seen = pm.model.calls[-1]["input_ids"][0].tolist()
    p = len(prompt_token_ids(tok, conv[:-1], THINKING_OFF))
    e = rec.content_range[1]
    # Flagged expectation change (Roger, 2026-11-03): nothing is trimmed, so
    # the plan's leading "\n" and " " are averaged too (the trim popped them,
    # and the span started at p + 2).
    span = list(range(p, p + e))
    assert tok.decode([seen[i] for i in span]) == "\n Law rules. Yes no.</think>\n\nArr matey."
    assert turn[0, 0, 0].item() == _bf16(sum(span) / len(span))
    assert torch.equal(_bits(turn[1:]), _bits(rng[1:]))        # the header slots are the same
    assert mm == []
    # With a record that has no plan, turn and range are the same span.
    plain = _stored(mod, tok, "Arr matey.")
    [a], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[plain])
    [b], _, _ = mod.extract_activations_batch(pm, [conv], [0, 1, 2], token_records=[plain],
                                              content_span="turn")
    assert torch.equal(_bits(a), _bits(b))


def test_content_span_is_recorded_and_refused_on_the_text_path(mod, pm, tmp_path, caplog):
    tok = pm.tokenizer
    stored = _stored(mod, tok, "Arr matey.", plan="Law rules.")
    recs = [_record(0, "Arr matey.", stored=stored),
            _record(1, "Yes", stored=_stored(mod, tok, "Yes"), null_range=True)]
    with caplog.at_level("WARNING"):
        _, meta = _run(mod, pm, tmp_path / "turn", recs, content_span="turn")
    assert meta["content_span"] == "turn"
    assert "the 1 record(s) on the text path average their stored content only" in caplog.text
    _, meta = _run(mod, pm, tmp_path / "range", recs)
    assert meta["content_span"] == "range"
    with pytest.raises(ValueError, match="refused with token_source 'text'"):
        _run(mod, pm, tmp_path / "text", recs, token_source="text", content_span="turn")
    with pytest.raises(ValueError, match="content_span"):
        _run(mod, pm, tmp_path / "bad", recs, content_span="all")


def test_the_content_span_flag_is_refused_with_the_text_source(mod, monkeypatch, tmp_path,
                                                               capsys):
    import sys
    responses = tmp_path / "responses"
    responses.mkdir()
    (responses / "alpha.jsonl").write_text("{}\n")
    monkeypatch.setattr(sys, "argv", ["2_activations.py", "--model", "Qwen/Qwen3-32B",
                                      "--responses_dir", str(responses),
                                      "--output_dir", str(tmp_path / "out"),
                                      "--token_source", "text", "--content_span", "turn"])
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert e.value.code == 2
    assert "refused with --token_source text" in capsys.readouterr().err
    p = mod.build_parser()
    base = ["--model", "m", "--responses_dir", "r", "--output_dir", "o"]
    assert p.parse_args(base).content_span == "range"
    assert p.parse_args(base + ["--content_span", "turn"]).content_span == "turn"


# ---------------------------------------------------------------------------
# § 5.6: --verify_ids (§ 5.8 item 9)
# ---------------------------------------------------------------------------

def _verify_set(mod, tok):
    """Records of every kind: the re-encoding, a plan, a special token, a
    partial character, a re-split ("\\n" "\\n" for "\\n\\n"), a null range."""
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    nl, nl2 = tok.convert_tokens_to_ids("\n"), tok.convert_tokens_to_ids("\n\n")
    arr, matey = _ids(tok, "Arr"), _ids(tok, "matey")
    special = tok.convert_tokens_to_ids("<|endoftext|>")
    assert _ids(tok, "Arr\n\nmatey") == arr + [nl2] + matey
    return [
        _record(0, "Arr matey.", stored=_stored(mod, tok, "Arr matey.")),
        _record(1, "Arr matey.", stored=_stored(mod, tok, "Arr matey.", plan="Law rules.",
                                                 lead="\n\n")),
        _record(2, "Arr matey.", stored=mod.StoredTokens(
            _ids(tok, "Arr ") + [special] + _ids(tok, "matey.") + [im_end], (0, 5))),
        _record(3, "Arr matey", stored=_stored(mod, tok, "Arr matey", stop=False,
                                                extra=_ids(tok, "?"))),
        _record(4, "Arr\n\nmatey", stored=mod.StoredTokens(arr + [nl, nl] + matey + [im_end],
                                                           (0, 4))),
        _record(5, "Yes", stored=_stored(mod, tok, "Yes"), null_range=True),
    ]


def test_verify_ids_reports_each_kind(mod, pm, tmp_path, caplog):
    recs = _verify_set(mod, pm.tokenizer)
    records, _ = mod.select_token_paths(recs, "auto", entity="pirate")
    with caplog.at_level("INFO"):
        res = mod.verify_token_paths(pm, [r["conversation"] for r in recs], records, 20,
                                     layers=[0, 1, 2], max_length=2048, entity="pirate")
    assert [r["conversation"] for r in res] == [0, 1, 2, 3, 4]        # the null range is not
    assert [r["identical"] for r in res] == [True, False, False, False, False]
    assert res[0]["slots_identical"] is True and res[0]["spans"] == "identical"
    assert [r.get("kinds") for r in res[1:]] == [["plan"], ["special token"],
                                                 ["partial character"], ["re-split"]]
    assert res[2]["positions"] == 1 and res[2]["regions"] == 1          # the special token
    assert res[4]["positions"] == 2 and res[4]["regions"] == 1          # \n \n for \n\n
    assert "conversation 0: identical ids" in caplog.text
    # Flagged expectation change (Roger, 2026-11-03): the summary also counts
    # the span comparison's outcomes.
    assert ("5 ids-path conversation(s): 1 with identical ids (1 with identical spans and "
            "bit-identical slots, 0 with spans differing by boundary whitespace (the text "
            "path's trim), 0 failed), 4 differing (partial character 1, plan 1, re-split 1, "
            "special token 1)") in caplog.text
    # N limits the conversations checked; a run with nothing on the ids path says so.
    assert len(mod.verify_token_paths(pm, [r["conversation"] for r in recs], records, 2,
                                      layers=[0], max_length=2048)) == 2
    with caplog.at_level("WARNING"):
        assert mod.verify_token_paths(pm, [recs[0]["conversation"]], [None], 5, layers=[0],
                                      max_length=2048, entity="pirate") == []
    assert "no conversation takes the ids path" in caplog.text
    # process_role with the flag reports and goes on to extract.
    acts, meta = _run(mod, pm, tmp_path, recs, verify_ids=20)
    assert len(acts) == 6 and meta["token_source"] == {"ids": 5, "text": 1, "range_null": 1}


def test_identical_ids_with_different_slots_stop_the_run(mod, pm, tmp_path, monkeypatch, caplog):
    recs = _verify_set(mod, pm.tokenizer)[:1]
    real = mod.extract_activations_batch

    def perturbed(*a, **k):                     # the second pass (the ids path) is off by one bit
        acts, mm, meta = real(*a, **k)
        if k.get("token_records") is not None:
            acts[0].view(torch.int16)[0, 0, 0] ^= 1
        return acts, mm, meta

    monkeypatch.setattr(mod, "extract_activations_batch", perturbed)
    with caplog.at_level("ERROR"):
        with pytest.raises(mod.TokenPathVerificationError, match="a bug in the ids path"):
            _run(mod, pm, tmp_path, recs, verify_ids=5)
    assert "identical ids (" in caplog.text and "but the slots differ" in caplog.text
    assert not (tmp_path / "pirate.pt").exists()


def test_identical_ids_are_compared_by_their_spans_first(mod, pm, tmp_path, caplog):
    # Roger, 2026-11-03: identical spans are run through the model; spans that
    # differ only by whitespace-only tokens at the ends (the text path's trim)
    # are reported, with no model pass, and the run goes on.
    tok = pm.tokenizer
    contents = ["Arr matey.", "Yes \n", " Yes", " "]
    recs = [_record(i, c, stored=_stored(mod, tok, c)) for i, c in enumerate(contents)]
    records, _ = mod.select_token_paths(recs, "auto", entity="pirate")
    n_calls = len(pm.model.calls)
    with caplog.at_level("INFO"):
        res = mod.verify_token_paths(pm, [r["conversation"] for r in recs], records, 20,
                                     layers=[0, 1, 2], max_length=2048, entity="pirate")
    assert [r["identical"] for r in res] == [True] * 4
    assert [r["spans"] for r in res] == ["identical"] + [mod.SPANS_BOUNDARY_WHITESPACE] * 3
    assert [r["slots_identical"] for r in res] == [True, None, None, None]
    assert len(pm.model.calls) == n_calls + 2                 # two passes, conversation 0's only
    assert not any(mod.token_path_check_failed(r) for r in res)
    assert ("conversation 1: identical ids (") in caplog.text
    assert "the spans differ by boundary whitespace (the text path's trim)" in caplog.text
    assert ("4 ids-path conversation(s): 4 with identical ids (1 with identical spans and "
            "bit-identical slots, 3 with spans differing by boundary whitespace (the text "
            "path's trim), 0 failed), 0 differing") in caplog.text
    acts, _ = _run(mod, pm, tmp_path, recs, verify_ids=20)     # and the extraction goes on
    assert len(acts) == 4


def test_another_span_difference_with_identical_ids_stops_the_run(mod, pm, tmp_path,
                                                                  monkeypatch, caplog):
    # A text-path span one non-whitespace token short (the "."): not the trim,
    # so a bug, whatever the slots; no model pass is run for it.
    from assistant_axis.internals.conversation import ConversationEncoder as Encoder
    orig = Encoder.build_turn_spans

    def short(self, conversation, **kw):
        ids, spans = orig(self, conversation, **kw)
        return ids, [dict(s, end=s["end"] - 1) if s["role"] == "assistant" else s
                     for s in spans]

    recs = [_record(0, "Arr matey.", stored=_stored(mod, pm.tokenizer, "Arr matey."))]
    monkeypatch.setattr(Encoder, "build_turn_spans", short)
    n_calls = len(pm.model.calls)
    with caplog.at_level("ERROR"):
        with pytest.raises(mod.TokenPathVerificationError, match="different spans or slots"):
            _run(mod, pm, tmp_path, recs, verify_ids=5)
    assert "but the assistant spans differ" in caplog.text
    assert len(pm.model.calls) == n_calls and not (tmp_path / "pirate.pt").exists()


def test_the_span_comparison(mod, pm):
    tok = pm.tokenizer
    full = _ids(tok, "x \nArr matey. \n")           # x, " ", \n, Arr, " ", matey, ".", " ", \n

    def rel(text, ids):
        return mod.compare_assistant_spans(
            tok, full, [{"role": "assistant", "start": s, "end": e} for s, e in text],
            [{"role": "assistant", "start": s, "end": e} for s, e in ids])

    assert rel([(3, 7)], [(3, 7)]) == "identical"
    assert rel([], []) == "identical"
    assert rel([(3, 7)], [(1, 9)]) == mod.SPANS_BOUNDARY_WHITESPACE      # both ends
    assert rel([(3, 7)], [(3, 9)]) == mod.SPANS_BOUNDARY_WHITESPACE      # the trailing end
    assert rel([], [(7, 9)]) == mod.SPANS_BOUNDARY_WHITESPACE            # all of it
    assert rel([(3, 6)], [(3, 9)]) == "different"                        # "." is not whitespace
    assert rel([(3, 7)], [(0, 7)]) == "different"                        # "x" is not
    assert rel([(1, 9)], [(3, 7)]) == "different"                        # the text path's wider
    assert rel([(3, 7)], []) == "different"


def test_a_worker_stops_on_a_failed_ids_check(mod, monkeypatch, tmp_path):
    import argparse

    class FakePM:
        model_name = "Qwen/Qwen3-32B"

        def __init__(self):
            from assistant_axis.model_families import FAMILIES
            self.family = FAMILIES["qwen3"]
            self.tokenizer = pm_tok

        def get_layers(self):
            return [object()] * 3

    pm_tok = make_fake_probing_model(N_LAYERS).tokenizer
    done = []

    def fake_process_role(pm, role_file, *a, **k):
        done.append((role_file.stem, k.get("verify_ids")))
        raise mod.TokenPathVerificationError("alpha: a bug in the ids path")

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    monkeypatch.setattr(mod, "ProbingModel", lambda name, **kw: FakePM())
    monkeypatch.setattr(mod, "process_role", fake_process_role)
    args = argparse.Namespace(model="Qwen/Qwen3-32B", output_dir=str(tmp_path), layers="all",
                              no_headers=False, batch_size=2, max_length=2048, verify_spans=0,
                              verify_ids=20)
    with pytest.raises(SystemExit) as e:
        mod.process_roles_on_worker(0, [0], [tmp_path / "alpha.jsonl", tmp_path / "beta.jsonl"],
                                    args)
    assert e.value.code == 1 and done == [("alpha", 20)]              # stopped at the first


def test_the_verify_ids_flag(mod):
    p = mod.build_parser()
    base = ["--model", "m", "--responses_dir", "r", "--output_dir", "o"]
    assert p.parse_args(base).verify_ids == 0
    assert p.parse_args(base + ["--verify_ids", "20"]).verify_ids == 20


# ---------------------------------------------------------------------------
# § 5.7: the metadata and the side-car's clean-up
# ---------------------------------------------------------------------------

def _sidecar(mod, responses, *, response_cleanup):
    from assistant_axis.generation import prompt_token_ids, write_generation_config
    from assistant_axis.model_families import FAMILIES
    tok = make_fake_probing_model(N_LAYERS).tokenizer
    pre = mod.Preflight(family=FAMILIES["qwen3"], n_layers=N_LAYERS, tokenizer=tok,
                        layout=mod.derive_chat_layout(tok, FAMILIES["qwen3"]))
    sample = _conv("")[:-1]
    responses.mkdir(parents=True, exist_ok=True)
    write_generation_config(responses, {
        "created_at": "2026-11-02T00:00:00+00:00", "model_type": "qwen3",
        "template_kwargs": dict(THINKING_OFF), "header_ids": list(pre.layout.header_ids),
        "sample_conversation": sample, "response_cleanup": response_cleanup,
        "sample_prompt_ids": prompt_token_ids(tok, sample, THINKING_OFF)})
    return pre


def test_the_recorded_clean_up_is_logged_and_read(mod, tmp_path, caplog, monkeypatch):
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    pre = _sidecar(mod, tmp_path / "responses", response_cleanup="none")
    with caplog.at_level("INFO"):
        assert mod.check_generation_config(tmp_path / "responses", pre) == []
    assert "step 1's response clean-up was 'none'" in caplog.text
    assert mod.recorded_response_cleanup(tmp_path / "responses") == "none"
    assert mod.recorded_response_cleanup(tmp_path / "none") is None


def test_the_metadata_records_the_path_the_span_and_the_clean_up(mod, pm, tmp_path):
    recs = [_record(0, "Arr matey.", stored=_stored(mod, pm.tokenizer, "Arr matey."))]
    _, meta = _run(mod, pm, tmp_path, recs, response_cleanup="none", content_span="turn")
    assert meta["token_source"] == {"ids": 1, "text": 0, "range_null": 0}
    assert meta["content_span"] == "turn" and meta["response_cleanup"] == "none"


def test_main_passes_the_flags_and_the_recorded_clean_up(mod, pm, tmp_path, monkeypatch):
    import logging
    import sys
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    responses = tmp_path / "responses"
    pre = _sidecar(mod, responses, response_cleanup="strip_leaked_think")
    _write_jsonl(responses / "alpha.jsonl", [_record(0, "Yes")])
    seen = {}

    def fake_process_role(pm_, role_file, *a, **k):
        seen.update(k)
        return True, 0

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")         # single-worker mode
    monkeypatch.setattr(mod, "preflight_model", lambda name, **kw: pre)
    monkeypatch.setattr(mod, "load_worker_model", lambda args, log=None: (pm, [0, 1, 2], None))
    monkeypatch.setattr(mod, "process_role", fake_process_role)
    monkeypatch.setattr(sys, "argv", ["2_activations.py", "--model", "Qwen/Qwen3-32B",
                                      "--responses_dir", str(responses),
                                      "--output_dir", str(tmp_path / "out"),
                                      "--token_source", "ids", "--content_span", "turn",
                                      "--verify_ids", "7"])
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        mod.main()
    finally:
        for h in root.handlers[:]:                          # main() adds a file handler
            if h not in before:
                root.removeHandler(h)
                h.close()
    assert (seen["token_source"], seen["content_span"], seen["verify_ids"]) == ("ids", "turn", 7)
    assert seen["response_cleanup"] == "strip_leaked_think"


def test_step_4_copies_the_new_keys_into_the_vector_and_step_5_refuses_nothing_new(mod, pm,
                                                                                 tmp_path,
                                                                                 monkeypatch):
    import json
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    act_dir, scores, vec = tmp_path / "activations", tmp_path / "scores", tmp_path / "vectors"
    for d in (act_dir, scores, vec):
        d.mkdir()
    recs = [_record(i, c, stored=_stored(mod, pm.tokenizer, c))
            for i, c in enumerate(["Arr matey.", "Yes", "Law rules."])]
    f = _write_jsonl(tmp_path / "responses" / "pirate.jsonl", recs)
    mod.process_role(pm, f, act_dir, [0, 1, 2], 2, 2048, response_cleanup="none")
    (scores / "pirate.json").write_text(json.dumps({"pos_p0_q0": 3, "pos_p1_q1": 3,
                                                    "pos_p0_q2": 3}))
    spec = importlib.util.spec_from_file_location("_p4_for_token_ids", REPO_ROOT / "pipeline"
                                                  / "4_vectors.py")
    step4 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(step4)
    assert step4.main(["--activations_dir", str(act_dir), "--scores_dir", str(scores),
                       "--output_dir", str(vec), "--min_count", "2"]) == 0
    meta = torch.load(vec / "pirate.pt", weights_only=False)["metadata"]
    assert meta["token_source"] == {"ids": 3, "text": 0, "range_null": 0}
    assert meta["content_span"] == "range" and meta["response_cleanup"] == "none"
    spec5 = importlib.util.spec_from_file_location("_p5_for_token_ids", REPO_ROOT / "pipeline"
                                                   / "5_axis.py")
    step5 = importlib.util.module_from_spec(spec5)
    spec5.loader.exec_module(step5)
    assert step5.METADATA_MUST_AGREE == ("header_ids", "model_name", "model_type",
                                         "template_kwargs")


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
