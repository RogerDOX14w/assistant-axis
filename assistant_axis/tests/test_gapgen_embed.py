"""Tests for assistant_axis/gapgen/embed.py (M2 task 11).

No model is loaded and no API is called: a deterministic hash embedder and a
fake OpenAI client stand in.  The real local models run only behind
``GAPGEN_RUN_LOCAL=1`` (after ``setup_external.py --hf-model ...``)."""
import json
import os
from types import SimpleNamespace

import numpy as np
import pytest

import assistant_axis.gapgen  # noqa: F401  (pins the HF cache)
from assistant_axis.gapgen import embed as E
from assistant_axis.gapgen.cost import GuardedUsage
from assistant_axis.gapgen.paths import REPO_ROOT, hf_cache_dir
from assistant_axis.judge_pricing import BudgetExceededError, MultiModelUsage


class FakeOpenAIClient:
    """``client.embeddings.create(model=, input=)`` -> hash vectors, usage.total_tokens."""

    def __init__(self, dim=16, tokens_per_text=7, fail_first=0):
        self.calls = []
        self._h = E.HashEmbedder(dim)
        self.tokens_per_text = tokens_per_text
        self.fail_first = fail_first
        self.embeddings = SimpleNamespace(create=self._create)

    def _create(self, *, model, input, **kw):
        self.calls.append({"model": model, "input": list(input), **kw})
        if self.fail_first:
            self.fail_first -= 1
            raise type("RateLimitError", (Exception,), {})("slow down")
        vecs, _ = self._h.embed_batch(input)
        data = [SimpleNamespace(index=i, embedding=v.tolist()) for i, v in enumerate(vecs)]
        data.reverse()  # the client must sort by index
        n = self.tokens_per_text * len(input)
        return SimpleNamespace(data=data, usage=SimpleNamespace(prompt_tokens=n, total_tokens=n))


def test_cache_hit_miss_and_round_trip(tmp_path):
    cache = E.EmbeddingCache(tmp_path)
    emb = E.HashEmbedder(32)
    texts = ["calm: This means calm.", "agitated: This means agitated.", "calm: This means calm."]
    usage = MultiModelUsage()
    out = E.embed_texts(emb, texts, cache=cache, usage=usage)
    assert out.shape == (3, 32)
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), 1.0)
    np.testing.assert_allclose(out[0], out[2])          # duplicates share a row, order kept
    assert usage.n_calls == 1                            # one batch, deduplicated
    # npz + manifest on disk
    assert (tmp_path / f"{emb.tag}.npz").exists()
    man = json.loads((tmp_path / "manifest.json").read_text())
    assert man[emb.tag]["n"] == 2 and man[emb.tag]["dim"] == 32 and man[emb.tag]["model_id"] == "hash-32"
    # a fresh cache object reads the npz back: all hits, no call
    cache2 = E.EmbeddingCache(tmp_path)
    found, missing = cache2.lookup(emb.tag, texts)
    assert missing == [] and len(found) == 3
    usage2 = MultiModelUsage()
    out2 = E.embed_texts(emb, list(reversed(texts)), cache=cache2, usage=usage2)
    assert usage2.n_calls == 0
    np.testing.assert_allclose(out2, out[::-1])
    # one new text is the only miss
    usage3 = MultiModelUsage()
    E.embed_texts(emb, texts + ["new: This means new."], cache=cache2, usage=usage3)
    assert usage3.n_calls == 1 and usage3.total_prompt_tokens == 4


def test_key_is_model_and_text_hash(tmp_path):
    cache = E.EmbeddingCache(tmp_path)
    a, b = E.HashEmbedder(8), E.HashEmbedder(16)
    E.embed_texts(a, ["x"], cache=cache)
    _, missing = cache.lookup(b.tag, ["x"])
    assert missing == [0]                    # same text, other model: a miss
    assert cache.get(a.tag, "x") is not None
    assert cache.get(a.tag, "x ") is None    # any change to the text is a miss


def test_fake_openai_charges_total_tokens_and_sorts(tmp_path):
    client = FakeOpenAIClient(dim=16, tokens_per_text=7)
    emb = E.OpenAIEmbedder(client=client, max_batch=2)
    usage = MultiModelUsage()
    texts = [f"t{i}: This means t{i}." for i in range(5)]
    out = E.embed_texts(emb, texts, cache=E.EmbeddingCache(tmp_path), usage=usage)
    assert [len(c["input"]) for c in client.calls] == [2, 2, 1]
    assert client.calls[0]["model"] == "text-embedding-3-large"
    assert usage.per_model["text-embedding-3-large"].prompt_tokens == 35
    assert usage.total_cost_usd == pytest.approx(35 * 0.13 / 1e6)
    ref, _ = E.HashEmbedder(16).embed_batch(texts)
    np.testing.assert_allclose(out, ref / np.linalg.norm(ref, axis=1, keepdims=True), atol=1e-6)


def test_openai_retries_transient_then_succeeds():
    client = FakeOpenAIClient(fail_first=1)
    slept = []
    emb = E.OpenAIEmbedder(client=client, sleep=slept.append, retry_delays=(1,))
    vecs, tok = emb.embed_batch(["a", "b"])
    assert vecs.shape == (2, 16) and tok == 14 and slept == [1] and len(client.calls) == 2


def test_budget_guard_keeps_cache_and_usage(tmp_path):
    client = FakeOpenAIClient(tokens_per_text=1_000_000)
    emb = E.OpenAIEmbedder(client=client, max_batch=1)
    usage = GuardedUsage(budget_usd=0.2, usage_path=tmp_path / "usage.json")
    cache = E.EmbeddingCache(tmp_path / "c")
    with pytest.raises(BudgetExceededError):
        E.embed_texts(emb, ["a", "b", "c"], cache=cache, usage=usage)
    assert json.loads((tmp_path / "usage.json").read_text())["n_calls"] == 2
    assert E.EmbeddingCache(tmp_path / "c").get(emb.tag, "b") is not None   # paid-for vector kept


def test_hash_embedder_is_bag_of_words():
    h = E.HashEmbedder(64)
    v, n = h.embed_batch(["calm rather than agitated", "agitated rather than calm", "lazy"])
    assert n == 9
    np.testing.assert_allclose(v[0], v[1])
    assert abs(float(v[0] @ v[2])) < np.linalg.norm(v[0]) * np.linalg.norm(v[2])


def test_hf_cache_is_inside_repo():
    """Every Hugging Face path the platform uses lies inside the repository."""
    root = REPO_ROOT.resolve()
    assert hf_cache_dir().resolve().is_relative_to(root)
    assert os.environ["HF_HOME"] == str(hf_cache_dir())
    assert os.environ["HF_HUB_CACHE"] == str(hf_cache_dir())
    for arm in E.LOCAL_MODELS:
        emb = E.local_embedder(arm)
        assert emb.cache_dir.resolve().is_relative_to(root)
        assert E.hf_snapshot_dir(emb.model_id).resolve().is_relative_to(root)


def test_local_embedder_refuses_missing_snapshot(tmp_path):
    emb = E.LocalEmbedder("org/absent-model", cache_dir=tmp_path)
    assert not E.hf_snapshot_present("org/absent-model", tmp_path)
    with pytest.raises(FileNotFoundError, match="setup_external.py --hf-model org/absent-model"):
        emb.embed_batch(["x"])


def test_allow_patterns_cover_both_models_and_skip_duplicates():
    assert set(E.HF_ALLOW_PATTERNS) == {cfg["model_id"] for cfg in E.LOCAL_MODELS.values()}
    assert "model.safetensors" in E.HF_ALLOW_PATTERNS["BAAI/bge-large-en-v1.5"]
    assert "onnx/*" in E.HF_IGNORE_PATTERNS and "*.bin" in E.HF_IGNORE_PATTERNS


def test_make_embedder_arms():
    assert E.make_embedder("hash").name == "hash"
    assert E.make_embedder("bge").pooling == "cls"
    g = E.make_embedder("gemma")
    assert g.pooling == "sentence_transformers" and g.prompt.startswith("task: sentence similarity")
    assert g.tag != E.make_embedder("bge").tag
    with pytest.raises(ValueError):
        E.make_embedder("qwen")


@pytest.mark.skipif(os.environ.get("GAPGEN_RUN_LOCAL") != "1", reason="set GAPGEN_RUN_LOCAL=1 to load real models")
@pytest.mark.parametrize("arm", ["bge", "gemma"])
def test_real_local_model_smoke(arm):
    emb = E.local_embedder(arm)
    if not E.hf_snapshot_present(emb.model_id):
        pytest.skip(f"{emb.model_id} not downloaded")
    texts = ["calm: This means staying calm under pressure.",
             "serene: This means being serene and untroubled.",
             "quantitative: This means emphasizing numbers and statistics."]
    usage = MultiModelUsage()
    out = E.embed_texts(emb, texts, usage=usage)
    np.testing.assert_allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)
    assert out[0] @ out[1] > out[0] @ out[2]
    assert usage.n_calls == 1 and usage.total_prompt_tokens > 0 and usage.total_cost_usd == 0
