"""Text embeddings for the trait-gap platform (M2 calibration, M3 novelty).

Three backends behind one :class:`Embedder` protocol:

* :class:`OpenAIEmbedder`: OpenAI ``text-embedding-3-large`` through the
  official ``openai`` client with the direct key (``OPENAI_API_KEY`` from
  ``.env``; never a router).  Charged at $0.13 per million input tokens.
* :class:`LocalEmbedder`: a Hugging Face model on MPS (or CPU), loaded only
  from ``data/external/hf/`` with ``local_files_only=True`` (downloads happen
  only through ``setup_external.py --hf-model``).  Two configured arms
  (:data:`LOCAL_MODELS`):

  - ``bge``: ``BAAI/bge-large-en-v1.5`` with ``transformers`` and CLS pooling
    (the model's own sentence-transformers config is CLS + normalise); no
    instruction prefix, the same on both sides (symmetric similarity).
  - ``gemma``: ``google/embeddinggemma-300m`` through ``sentence-transformers``
    (its intended path: transformer, mean pooling, two dense layers,
    normalise), with the model's own "sentence similarity" prompt on both
    sides.  ``sentence-transformers`` is imported only when this arm loads, so
    the platform and its tests run without it.
* :class:`HashEmbedder`: a deterministic bag-of-words hash embedder for tests
  and dry runs (no model, no network).

Local models are free but are still charged to the usage record (calls and
tokens at zero cost), as the CLAUDE.md usage rule asks.

:class:`EmbeddingCache` keeps one ``<model_tag>.npz`` per embedder under
``data/candidates/cache/embeddings/`` (gitignored), keyed by
``sha256(text)``, plus a ``manifest.json``.  :func:`embed_texts` embeds only
the cache misses, charges the usage record per call, and returns unit rows
in input order.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Protocol, Sequence, runtime_checkable

import numpy as np

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.judge_pricing import MultiModelUsage

from .paths import EMBEDDING_CACHE_DIR, REPO_ROOT, hf_cache_dir, pin_hf_cache
from .registry import utc_now

logger = logging.getLogger(__name__)

OPENAI_MODEL = "text-embedding-3-large"

#: The two local arms.  ``usage_model`` is the key in usage.json (priced free
#: by ``judge_pricing``); ``prompt`` is prepended on both sides.
LOCAL_MODELS: dict[str, dict] = {
    "bge": {"model_id": "BAAI/bge-large-en-v1.5", "pooling": "cls", "prompt": None,
            "usage_model": "bge-large-en-v1.5"},
    "gemma": {"model_id": "google/embeddinggemma-300m", "pooling": "sentence_transformers",
              "prompt": "task: sentence similarity | query: ", "usage_model": "embeddinggemma-300m"},
}

#: What ``setup_external.py --hf-model`` fetches per repository: only the files
#: a load needs (config, tokenizer, safetensors weights, sentence-transformers
#: module configs).  ONNX, OpenVINO and PyTorch ``.bin`` duplicates are skipped.
HF_ALLOW_PATTERNS: dict[str, list[str]] = {
    "BAAI/bge-large-en-v1.5": ["config.json", "tokenizer.json", "tokenizer_config.json",
                               "special_tokens_map.json", "vocab.txt", "model.safetensors",
                               "modules.json", "sentence_bert_config.json",
                               "config_sentence_transformers.json", "1_Pooling/config.json"],
    "google/embeddinggemma-300m": ["*.json", "model.safetensors", "tokenizer.model",
                                   "1_Pooling/*", "2_Dense/*", "3_Dense/*"],
}
HF_IGNORE_PATTERNS = ["onnx/*", "openvino/*", "*.onnx", "*.bin", "*.h5", "*.msgpack", "*.ot"]


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tag(s: str) -> str:
    """A file-safe cache tag."""
    return re.sub(r"[^A-Za-z0-9._+-]+", "_", s).strip("_")


@runtime_checkable
class Embedder(Protocol):
    """``embed_batch(texts) -> (vectors (n, d) float32, input tokens charged)``."""
    name: str          # arm name: openai | bge | gemma | hash
    model_id: str      # e.g. "text-embedding-3-large"
    tag: str           # cache file tag (model plus anything that changes the vectors)
    usage_model: str   # key under which calls are charged in usage.json
    max_batch: int

    def embed_batch(self, texts: Sequence[str]) -> tuple[np.ndarray, int]: ...


# --------------------------------------------------------------------------- OpenAI

_TRANSIENT = {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError",
              "ServiceUnavailableError", "TimeoutError", "ConnectionError"}


def _is_transient(exc: BaseException) -> bool:
    return any(c.__name__ in _TRANSIENT for c in type(exc).__mro__)


class OpenAIEmbedder:
    """OpenAI embeddings through the official client, with the direct key only."""
    name = "openai"

    def __init__(self, model: str = OPENAI_MODEL, *, client=None, dimensions: Optional[int] = None,
                 max_batch: int = 256, retry_delays: Sequence[float] = (5, 20, 60),
                 sleep: Callable[[float], None] = time.sleep):
        self.model_id = model
        self.dimensions = dimensions
        self.max_batch = max_batch
        self.usage_model = model
        self.tag = _tag(f"openai_{model}" + (f"_d{dimensions}" if dimensions else ""))
        self._client = client
        self._retry_delays = tuple(retry_delays)
        self._sleep = sleep

    def client(self):
        if self._client is None:
            from dotenv import load_dotenv
            load_dotenv(REPO_ROOT / ".env")
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not set (.env): OpenAI embeddings need the direct key; "
                                   "there is no router fallback")
            from openai import OpenAI
            self._client = OpenAI()
        return self._client

    def embed_batch(self, texts: Sequence[str]) -> tuple[np.ndarray, int]:
        kwargs = {"model": self.model_id, "input": list(texts)}
        if self.dimensions:
            kwargs["dimensions"] = self.dimensions
        delays = list(self._retry_delays)
        while True:
            try:
                resp = self.client().embeddings.create(**kwargs)
                break
            except Exception as exc:  # noqa: BLE001 - classified below
                if not delays or not _is_transient(exc):
                    raise
                d = delays.pop(0)
                logger.warning("openai embeddings: %s; retrying in %ss", type(exc).__name__, d)
                self._sleep(d)
        data = sorted(resp.data, key=lambda r: r.index)
        if len(data) != len(texts):
            raise RuntimeError(f"openai returned {len(data)} embeddings for {len(texts)} texts")
        vecs = np.asarray([r.embedding for r in data], dtype=np.float32)
        u = getattr(resp, "usage", None)
        tokens = int(getattr(u, "total_tokens", None) or getattr(u, "prompt_tokens", 0) or 0)
        return vecs, tokens


# --------------------------------------------------------------------------- local

def hf_snapshot_dir(model_id: str, cache_dir: Optional[Path] = None) -> Path:
    """``<cache>/models--org--name`` (the hub cache layout)."""
    return Path(cache_dir or hf_cache_dir()) / ("models--" + model_id.replace("/", "--"))


def hf_snapshot_present(model_id: str, cache_dir: Optional[Path] = None) -> bool:
    snaps = hf_snapshot_dir(model_id, cache_dir) / "snapshots"
    return snaps.is_dir() and any(p.is_dir() for p in snaps.iterdir())


def default_device() -> str:
    import torch
    return "mps" if torch.backends.mps.is_available() else "cpu"


class LocalEmbedder:
    """A Hugging Face embedding model loaded from ``data/external/hf`` only.

    ``pooling="cls"`` uses ``transformers`` (bge); ``pooling="sentence_transformers"``
    uses the model's own sentence-transformers pipeline (EmbeddingGemma).
    ``prompt`` is prepended to every text (both sides, by design).  Loads lazily
    on the first batch, with ``local_files_only=True``: a missing snapshot is
    an error naming the setup command, never a download.
    """

    def __init__(self, model_id: str, *, name: Optional[str] = None, pooling: str = "cls",
                 prompt: Optional[str] = None, usage_model: Optional[str] = None,
                 device: Optional[str] = None, max_batch: int = 32, max_length: int = 512,
                 cache_dir: Optional[Path] = None):
        if pooling not in ("cls", "sentence_transformers"):
            raise ValueError(f"pooling must be cls or sentence_transformers, got {pooling!r}")
        self.model_id = model_id
        self.name = name or model_id.split("/")[-1]
        self.pooling = pooling
        self.prompt = prompt
        self.usage_model = usage_model or model_id
        self.device = device
        self.max_batch = max_batch
        self.max_length = max_length
        self.cache_dir = Path(cache_dir or hf_cache_dir())
        self.tag = _tag(f"local_{model_id}" + (f"_p{text_sha256(prompt)[:8]}" if prompt else ""))
        self._model = None
        self._tok = None

    def _load(self) -> None:
        if self._model is not None:
            return
        pin_hf_cache()
        if not hf_snapshot_present(self.model_id, self.cache_dir):
            raise FileNotFoundError(
                f"{self.model_id} is not in {self.cache_dir}; run "
                f"`uv run python data_analysis/gap_generation/setup_external.py --hf-model {self.model_id}`")
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
        token = os.environ.get("HF_TOKEN")
        self.device = self.device or default_device()
        if self.pooling == "cls":
            from transformers import AutoModel, AutoTokenizer
            self._tok = AutoTokenizer.from_pretrained(self.model_id, cache_dir=str(self.cache_dir),
                                                      local_files_only=True, token=token)
            self._model = AutoModel.from_pretrained(self.model_id, cache_dir=str(self.cache_dir),
                                                    local_files_only=True, token=token)
            self._model.eval().to(self.device)
        else:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # optional dependency
                raise ImportError("the EmbeddingGemma arm needs the optional package sentence-transformers "
                                  "(uv sync installs it)") from exc
            self._model = SentenceTransformer(self.model_id, cache_folder=str(self.cache_dir), device=self.device,
                                              local_files_only=True, token=token)
            self._tok = self._model.tokenizer

    def _with_prompt(self, texts: Sequence[str]) -> list[str]:
        return [(self.prompt or "") + t for t in texts]

    def embed_batch(self, texts: Sequence[str]) -> tuple[np.ndarray, int]:
        import torch
        self._load()
        full = self._with_prompt(texts)
        enc = self._tok(full, padding=True, truncation=True, max_length=self.max_length, return_tensors="pt")
        tokens = int(enc["attention_mask"].sum())
        with torch.no_grad():
            if self.pooling == "cls":
                enc = {k: v.to(self.device) for k, v in enc.items()}
                out = self._model(**enc)
                vecs = out.last_hidden_state[:, 0].float().cpu().numpy()
            else:
                vecs = self._model.encode(full, batch_size=self.max_batch, convert_to_numpy=True,
                                          normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32), tokens


def local_embedder(arm: str, **kw) -> LocalEmbedder:
    """The configured local arm ``bge`` or ``gemma`` (:data:`LOCAL_MODELS`)."""
    cfg = dict(LOCAL_MODELS[arm])
    return LocalEmbedder(cfg.pop("model_id"), name=arm, **cfg, **kw)


# --------------------------------------------------------------------------- hash (tests)

class HashEmbedder:
    """Deterministic bag-of-words embedder: each lower-cased word maps to a
    fixed random unit vector (seeded by its sha256); a text is the sum.  Texts
    sharing words are similar; word order is ignored (a pure bag of words)."""
    name = "hash"

    def __init__(self, dim: int = 64, *, max_batch: int = 1000):
        self.dim = dim
        self.model_id = f"hash-{dim}"
        self.usage_model = "bge-large"   # free; any zero-priced key keeps the record consistent
        self.tag = f"hash_{dim}"
        self.max_batch = max_batch
        self._memo: dict[str, np.ndarray] = {}

    def _word(self, w: str) -> np.ndarray:
        v = self._memo.get(w)
        if v is None:
            seed = int(text_sha256(w)[:16], 16)
            v = np.random.default_rng(seed).standard_normal(self.dim)
            v = v / np.linalg.norm(v)
            self._memo[w] = v
        return v

    def embed_batch(self, texts: Sequence[str]) -> tuple[np.ndarray, int]:
        out, n_tok = [], 0
        for t in texts:
            words = re.findall(r"[a-z]+", t.lower()) or ["<empty>"]
            n_tok += len(words)
            out.append(np.sum([self._word(w) for w in words], axis=0))
        return np.asarray(out, dtype=np.float32), n_tok


def make_embedder(arm: str, **kw) -> Embedder:
    """``openai`` | ``bge`` | ``gemma`` | ``hash``."""
    if arm == "openai":
        return OpenAIEmbedder(**kw)
    if arm in LOCAL_MODELS:
        return local_embedder(arm, **kw)
    if arm == "hash":
        return HashEmbedder(**kw)
    raise ValueError(f"unknown embedding arm {arm!r}: openai | bge | gemma | hash")


# --------------------------------------------------------------------------- cache

@dataclass
class EmbeddingCache:
    """``<root>/<tag>.npz`` (arrays ``keys`` = sha256 hex, ``vecs`` float32) and
    ``<root>/manifest.json`` (``{tag: {model_id, dim, n, updated_at}}``).
    Vectors are stored as returned by the model (normalised on the way out)."""
    root: Path = field(default_factory=lambda: EMBEDDING_CACHE_DIR)
    _mem: dict = field(default_factory=dict, repr=False)
    _dirty: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self.root = Path(self.root)

    def path(self, tag: str) -> Path:
        return self.root / f"{tag}.npz"

    def _table(self, tag: str) -> dict:
        if tag not in self._mem:
            table: dict[str, np.ndarray] = {}
            p = self.path(tag)
            if p.exists():
                with np.load(p, allow_pickle=False) as z:
                    for k, v in zip(z["keys"], z["vecs"]):
                        table[str(k)] = v
            self._mem[tag] = table
        return self._mem[tag]

    def get(self, tag: str, text: str) -> Optional[np.ndarray]:
        return self._table(tag).get(text_sha256(text))

    def lookup(self, tag: str, texts: Sequence[str]) -> tuple[dict[int, np.ndarray], list[int]]:
        table = self._table(tag)
        found, missing = {}, []
        for i, t in enumerate(texts):
            v = table.get(text_sha256(t))
            if v is None:
                missing.append(i)
            else:
                found[i] = v
        return found, missing

    def put(self, tag: str, texts: Sequence[str], vecs: np.ndarray, *, model_id: str) -> None:
        table = self._table(tag)
        for t, v in zip(texts, np.asarray(vecs, dtype=np.float32)):
            table[text_sha256(t)] = v
        self._dirty[tag] = model_id

    def __len__(self) -> int:
        return sum(len(t) for t in self._mem.values())

    def save(self) -> None:
        if not self._dirty:
            return
        self.root.mkdir(parents=True, exist_ok=True)
        mpath = self.root / "manifest.json"
        manifest = json.loads(mpath.read_text()) if mpath.exists() else {}
        for tag, model_id in list(self._dirty.items()):
            table = self._mem[tag]
            keys = np.array(sorted(table), dtype="U64")
            vecs = np.stack([table[k] for k in keys]).astype(np.float32) if len(keys) else np.zeros((0, 0), np.float32)
            fd, tmp = tempfile.mkstemp(dir=self.root, suffix=".npz.tmp")
            os.close(fd)
            with open(tmp, "wb") as fh:
                np.savez(fh, keys=keys, vecs=vecs)
            os.replace(tmp, self.path(tag))
            manifest[tag] = {"model_id": model_id, "dim": int(vecs.shape[1]) if vecs.ndim == 2 else 0,
                             "n": int(len(keys)), "updated_at": utc_now()}
        atomic_write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", mpath)
        self._dirty.clear()


def normalize_rows(E: np.ndarray) -> np.ndarray:
    E = np.asarray(E, dtype=np.float64)
    n = np.linalg.norm(E, axis=1, keepdims=True)
    if np.any(n == 0) or not np.all(np.isfinite(E)):
        raise ValueError("zero or non-finite embedding row")
    return E / n


def embed_texts(embedder: Embedder, texts: Sequence[str], *, cache: Optional[EmbeddingCache] = None,
                usage: Optional[MultiModelUsage] = None, batch_size: Optional[int] = None,
                on_batch: Optional[Callable[[int, int], None]] = None) -> np.ndarray:
    """Embed ``texts``; returns an ``(n, d)`` float64 array of unit rows in
    input order.  Cache misses only are sent, deduplicated, in batches of
    ``batch_size`` (default ``embedder.max_batch``); every call is charged to
    ``usage`` under ``embedder.usage_model`` (input tokens, zero output), and
    the cache is saved after every batch so a killed run keeps what it paid
    for.  ``on_batch(done, total)`` is called after each batch."""
    texts = list(texts)
    if not texts:
        return np.zeros((0, 0))
    uniq = list(dict.fromkeys(texts))
    vec_of: dict[str, np.ndarray] = {}
    missing = uniq
    if cache is not None:
        found, miss_idx = cache.lookup(embedder.tag, uniq)
        vec_of = {uniq[i]: v for i, v in found.items()}
        missing = [uniq[i] for i in miss_idx]
    bs = batch_size or embedder.max_batch
    for start in range(0, len(missing), bs):
        batch = missing[start:start + bs]
        vecs, tokens = embedder.embed_batch(batch)
        for t, v in zip(batch, vecs):
            vec_of[t] = v
        if cache is not None:  # keep what was paid for before a budget guard can raise
            cache.put(embedder.tag, batch, vecs, model_id=embedder.model_id)
            cache.save()
        if usage is not None:
            usage.charge(embedder.usage_model, int(tokens), 0)
        if on_batch:
            on_batch(min(start + bs, len(missing)), len(missing))
    return normalize_rows(np.stack([vec_of[t] for t in texts]))
