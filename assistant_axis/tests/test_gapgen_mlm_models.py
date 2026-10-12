"""Masked-LM generator, task 2: models, tokenizers, device, census, the download record (plan section 8,
``models``).  No model is loaded and nothing is downloaded: the loaders are replaced by fakes that record their
keyword arguments."""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pytest

from assistant_axis.gapgen.generators.masked_lm import models as M
from assistant_axis.tests.mlm_fakes import FakeHFTokenizer, make_tokenizer

VOCAB = ["She", "Ġis", "Ġkind", "Ġsyc", "oph", "antic", "Ġrisk", "-", "a", "verse", "Ġto", "Ġanimals", "Ġby",
         "Ġnature", ".", "ly", "Ġhonest", "Ġhelpful", "ĠKant", "ian"]


def test_census_classes_on_a_fake_tokenizer():
    tok = make_tokenizer(VOCAB)
    rows = {r.label: r for r in M.token_census(["kind", "sycophantic", "risk-averse", "kind to animals", "Kantian",
                                                "honest"], tok)}
    assert (rows["kind"].klass, rows["kind"].n_tokens) == ("single", 1)
    assert (rows["sycophantic"].klass, rows["sycophantic"].n_tokens) == ("subword", 3)
    assert rows["Kantian"].klass == "subword"
    assert rows["risk-averse"].klass == "multiword" and rows["kind to animals"].klass == "multiword"
    s = M.census_summary(list(rows.values()))
    assert (s["single"], s["subword"], s["multiword"]) == (2, 2, 2)
    assert s["shares"]["single"] == pytest.approx(1 / 3, abs=1e-3)


def test_word_start_by_scheme():
    bpe = make_tokenizer(VOCAB)
    assert bpe.word_start[bpe.tok.ids["Ġkind"]] and not bpe.word_start[bpe.tok.ids["oph"]]
    assert not bpe.word_start[bpe.mask_id]          # a special token never starts a word
    assert bpe.piece_text[bpe.tok.ids["Ġkind"]] == "kind"
    wp = make_tokenizer(["she", "kind", "syc", "##oph", "##antic"], scheme="wordpiece")
    assert wp.word_start[wp.tok.ids["kind"]] and not wp.word_start[wp.tok.ids["##oph"]]
    assert wp.piece_text[wp.tok.ids["##oph"]] == "oph"


def test_a_space_piece_before_the_mask_is_dropped():
    tok = make_tokenizer(VOCAB + ["Ġ"])
    ids = [0, tok.tok.ids["She"], tok.tok.ids["Ġis"], tok.tok.ids["Ġ"], tok.mask_id, 2]
    assert tok._drop_space_before_mask(ids) == [0, tok.tok.ids["She"], tok.tok.ids["Ġis"], tok.mask_id, 2]


def test_only_approved_models_may_be_fetched():
    """Roger approved all three on 2026-10-11 (roberta-large) and 2026-10-12 (the other two, approved with the
    fill-mask plan): every model with a recorded approval is fetchable, and none without one."""
    assert set(M.HF_MODEL_ALLOW_PATTERNS) == {"FacebookAI/roberta-large", "google-bert/bert-large-cased-whole-word-masking",
                                              "answerdotai/ModernBERT-large"}
    assert all(M.MODELS[k].approved_by for k in ("roberta", "bert_wwm", "modernbert"))
    pats = M.HF_MODEL_ALLOW_PATTERNS["FacebookAI/roberta-large"]
    assert "model.safetensors" in pats and not any(p.endswith((".bin", ".h5", ".msgpack", ".onnx")) for p in pats)
    from data_analysis.gap_generation.setup_external import allow_patterns
    allowed = allow_patterns()
    assert set(M.HF_MODEL_ALLOW_PATTERNS) <= set(allowed)


def test_missing_model_message_names_the_setup_command():
    msg = M.model_missing("bert_wwm")
    assert "setup_external.py --hf-model google-bert/bert-large-cased-whole-word-masking" in msg
    assert "approved: Roger" in msg and "never downloads" in msg
    assert "approved: Roger" in M.model_missing("roberta")


class _FakeModel:
    def __init__(self, vocab):
        self._w = np.zeros((vocab, 2))

    def to(self, device):
        return self

    def eval(self):
        return self

    def get_output_embeddings(self):
        class E:
            pass
        e = E()
        e.weight = self._w
        return e


def test_trust_remote_code_is_never_passed(monkeypatch, tmp_path):
    import transformers
    seen = []

    def fake_tok(model_id, **kw):
        seen.append(("tok", model_id, kw))
        return FakeHFTokenizer(VOCAB)

    def fake_model(model_id, **kw):
        seen.append(("model", model_id, kw))
        return _FakeModel(len(VOCAB) + 5)
    monkeypatch.setattr(transformers.AutoTokenizer, "from_pretrained", staticmethod(fake_tok))
    monkeypatch.setattr(transformers.AutoModelForMaskedLM, "from_pretrained", staticmethod(fake_model))
    monkeypatch.setattr(M, "model_present", lambda key, cache_dir=None: True)
    monkeypatch.setattr(M, "snapshot_path", lambda key, cache_dir=None: tmp_path / "abc123")
    for key in M.MODELS:
        M.load_tokenizer(key, cache_dir=tmp_path)
        M.HFMaskedLM(key, device="cpu", cache_dir=tmp_path)
    assert {k for k, _, _ in seen} == {"tok", "model"} and len(seen) >= 2 * len(M.MODELS)
    for _, model_id, kw in seen:
        assert "trust_remote_code" not in kw, (model_id, kw)
        assert kw["local_files_only"] is True and kw["cache_dir"] == str(tmp_path)
    assert "trust_remote_code" not in M.loader_kwargs("modernbert")
    # and the package never spells it as an argument anywhere
    pkg = Path(M.__file__).parent
    for f in pkg.glob("*.py"):
        assert not re.search(r"trust_remote_code\s*=", f.read_text()), f.name


def test_loaders_refuse_a_missing_model(monkeypatch, tmp_path):
    with pytest.raises(FileNotFoundError, match="setup_external.py"):
        M.load_tokenizer("bert_wwm", cache_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="setup_external.py"):
        M.load_mlm("modernbert", "cpu", cache_dir=tmp_path)


def test_device(monkeypatch):
    import torch
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)
    with pytest.raises(RuntimeError) as exc:
        M.resolve_device("mps")
    assert str(exc.value) == M.MPS_REFUSAL and "--device cpu" in str(exc.value)
    assert M.resolve_device("auto") == "cpu" and M.resolve_device("cpu") == "cpu"
    with pytest.raises(ValueError):
        M.resolve_device("cuda")


def test_parse_models():
    assert M.parse_models("roberta, bert_wwm") == ["roberta", "bert_wwm"]
    with pytest.raises(KeyError):
        M.parse_models("deberta")


def _snapshot(root: Path, files: dict) -> Path:
    snap = root / "models--FacebookAI--roberta-large" / "snapshots" / M.MODELS["roberta"].revision
    snap.mkdir(parents=True)
    for name, data in files.items():
        (snap / name).write_bytes(data)
    return snap


def test_record_model_verifies_hashes_and_licence(tmp_path, monkeypatch):
    weights = b"weights-bytes"
    sha = hashlib.sha256(weights).hexdigest()
    _snapshot(tmp_path, {"model.safetensors": weights, "config.json": b"{}"})
    spec = M.MODELS["roberta"]
    monkeypatch.setitem(M.MODELS, "roberta", M.ModelSpec(**{**spec.__dict__, "weights_sha256": sha,
                                                            "weights_bytes": len(weights)}))

    def info(model_id, revision):
        return {"sha": revision, "license": "mit",
                "files": {"model.safetensors": {"size": len(weights), "sha256": sha}, "config.json": {"size": 2}}}
    e = M.record_model("roberta", approved_by="Roger, 2026-10-11", cache_dir=tmp_path, info_fn=info,
                       now="2026-10-12T00:00:00+00:00", echo=lambda *a: None)
    assert e["checksum_verified"] and e["licence_verified"] and e["revision_matches_pin"]
    assert e["weights_sha256"] == sha and e["approved_by"] == "Roger, 2026-10-11" and e["todo"] is None
    json.dumps(e)

    def bad(model_id, revision):
        return {"license": "apache-2.0", "files": {"model.safetensors": {"size": len(weights), "sha256": "0" * 64}}}
    e2 = M.record_model("roberta", cache_dir=tmp_path, info_fn=bad, echo=lambda *a: None)
    assert not e2["checksum_verified"] and not e2["licence_verified"]
