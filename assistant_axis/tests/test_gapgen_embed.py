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


# --------------------------------------------------------------------------- drift canary (task 19, 2026-10-02)


class PerturbedOpenAIClient(FakeOpenAIClient):
    """The fake OpenAI client after a silent model change: every vector is rotated a little."""

    def __init__(self, *a, scale=0.2, **kw):
        super().__init__(*a, **kw)
        self.scale = scale

    def _create(self, *, model, input, **kw):
        resp = super()._create(model=model, input=input, **kw)
        rng = np.random.default_rng(7)
        for r in resp.data:
            r.embedding = (np.asarray(r.embedding) + self.scale * rng.standard_normal(len(r.embedding))).tolist()
        return resp


def _canary_corpus(n=30):
    stems = [f"t{i:02d}" for i in range(n)]
    return stems, [f"label {s}: This means being {s} in every way that {s} can be." for s in stems]


def test_canary_texts_fixed_rule():
    stems, texts = _canary_corpus(30)
    c = E.canary_texts(list(reversed(stems)), list(reversed(texts)), n=8)    # input order does not matter
    assert [x["stem"] for x in c] == [stems[i * 30 // 8] for i in range(8)]
    assert all(x["text"] == texts[stems.index(x["stem"])] for x in c)
    assert E.canary_texts(stems, texts) == c and E.CANARY_N == 8
    with pytest.raises(ValueError):
        E.canary_texts(stems[:3], texts[:3], n=8)


def test_canary_passes_on_the_hash_embedder_and_seeds_missing_references(tmp_path, caplog):
    stems, texts = _canary_corpus()
    canary = E.canary_texts(stems, texts)
    cache, emb, usage = E.EmbeddingCache(tmp_path), E.HashEmbedder(32), MultiModelUsage()
    first = E.check_canary(emb, canary, cache, usage=usage)          # nothing cached: references stored, no warning
    assert first["n_compared"] == 0 and first["n_new_reference"] == 8 and first["ok"]
    assert len(cache.lookup(emb.tag, [c["text"] for c in canary])[1]) == 0
    E.embed_texts(emb, texts[:3], cache=cache)                       # ordinary use of the cache
    caplog.clear()
    second = E.check_canary(emb, canary, cache, usage=usage)
    assert second["n_compared"] == 8 and second["ok"] and second["min_cosine"] == pytest.approx(1.0)
    assert second["below"] == [] and second["threshold"] == E.CANARY_MIN_COSINE == 0.999
    assert not [r for r in caplog.records if r.levelname == "WARNING"]
    assert usage.n_calls == 2                                         # every check is charged


def test_canary_warns_naming_the_model_when_the_api_model_changed(tmp_path, caplog):
    stems, texts = _canary_corpus()
    canary = E.canary_texts(stems, texts)
    cache = E.EmbeddingCache(tmp_path)
    E.embed_texts(E.OpenAIEmbedder(client=FakeOpenAIClient(dim=32)), [c["text"] for c in canary], cache=cache)
    drifted = E.OpenAIEmbedder(client=PerturbedOpenAIClient(dim=32))
    before = {c["text"]: cache.get(drifted.tag, c["text"]).copy() for c in canary}
    caplog.clear()
    res = E.check_canary(drifted, canary, cache, usage=MultiModelUsage())
    assert not res["ok"] and len(res["below"]) == 8 and res["min_cosine"] < 0.999
    assert res["model"] == "text-embedding-3-large"
    warn = [r.getMessage() for r in caplog.records if r.levelname == "WARNING"]
    assert warn and "text-embedding-3-large" in warn[0] and "the API model may have changed" in warn[0]
    # the cached references are never overwritten by the canary
    assert all(np.array_equal(cache.get(drifted.tag, t), v) for t, v in before.items())


def test_canary_applies_to_real_models_not_the_test_embedder():
    assert E.canary_applies(E.OpenAIEmbedder(client=FakeOpenAIClient()))
    assert not E.canary_applies(E.HashEmbedder(8))
