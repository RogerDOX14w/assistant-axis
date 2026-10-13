"""Shared fixtures for the persona-space tests (workstream 12): a toy corpus of traits and roles, a synthetic pool
with planted structure, a vectors tree of ``.pt`` files, an embedding cache filled with hash embeddings under the
live model's tag, and the real-data locations (the hard figures run only where the vectors tree and the embedding
cache are present; the environment variables point the tests at another checkout's copies)."""
from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Optional

import numpy as np

from assistant_axis.gapgen import persona as P
from assistant_axis.gapgen.paths import DATA_CANDIDATES, EMBEDDING_CACHE_DIR

# --------------------------------------------------------------------------- the real data (hard figures)

VECTORS_DIR = Path(os.environ.get("PERSONA_SPACE_VECTORS_DIR") or P.DEFAULT_VECTORS_DIR)
EMBED_CACHE_DIR = Path(os.environ.get("PERSONA_SPACE_EMBED_CACHE") or EMBEDDING_CACHE_DIR)
POOL_CACHE_DIR = Path(os.environ.get("PERSONA_SPACE_POOL_CACHE") or DATA_CANDIDATES / "cache")
OPENAI_TAG = "openai_text-embedding-3-large"


def real_data_present() -> bool:
    return (VECTORS_DIR / "traits" / "vectors").is_dir() and (EMBED_CACHE_DIR / f"{OPENAI_TAG}.npz").exists()


REAL_REASON = "persona vectors or the embedding cache not present (set PERSONA_SPACE_VECTORS_DIR / _EMBED_CACHE)"


@functools.lru_cache(maxsize=1)
def real_pool():
    from assistant_axis.gapgen.persona_space import pool as POOL
    return POOL.load_pool(vectors_dir=VECTORS_DIR, cache_dir=POOL_CACHE_DIR)


@functools.lru_cache(maxsize=1)
def real_embeddings():
    from assistant_axis.gapgen.embed import EmbeddingCache, normalize_rows
    from assistant_axis.gapgen.persona_space import pool as POOL
    pool = real_pool()
    texts = [t for t in POOL.corpus_texts(pool) if t is not None]
    cache = EmbeddingCache(root=EMBED_CACHE_DIR)
    found, missing = cache.lookup(OPENAI_TAG, texts)
    if missing:
        raise AssertionError(f"{len(missing)} corpus texts are not cached")
    return normalize_rows(np.stack([found[i] for i in range(len(texts))]))


@functools.lru_cache(maxsize=1)
def real_cv_alpha03():
    from assistant_axis.gapgen.persona_space import fit as FIT
    from assistant_axis.gapgen.persona_space import pool as POOL
    pool = real_pool()
    groups = POOL.fold_groups(pool)[pool.train_idx]
    return FIT.cross_validate(pool, real_embeddings(), groups, FIT.FitConfig(alphas=(0.3,)))


# --------------------------------------------------------------------------- the toy corpus

TRAIT_PAIRS = [("brave", "cowardly"), ("honest", "dishonest")]
TRIANGLE = ["alpha", "beta", "gamma"]
SINGLE_TRAITS = [f"t{i:02d}" for i in range(1, 25)] + ["patient"]
RENAMED = {"sturdy": "robust", "violent": "savage"}     # current stem: old stem (savage -> violent is sense-changed)
PENDING_TRAITS = ["p_one", "p_two"]
ROLE_PAIR = ("angel", "demon")
SINGLE_ROLES = [f"r{i:02d}" for i in range(1, 15)] + ["patient"]
ORPHANS = {"traits": ["lost"], "roles": ["ghost"]}


def _trait_doc(stem: str, *, neg: Optional[str] = None, arrangement=None, renamed_from=None) -> dict:
    d = {"positive_label": stem.replace("_", " "), "negative_label": neg or f"non-{stem}",
         "description": f"This means being {stem.replace('_', ' ')} in a way of its own, word {stem}."}
    if arrangement is not None:
        d["arrangement"] = arrangement
    if renamed_from:
        d["renamed_from"] = {"stem": renamed_from, "date": "2026-10-01", "reason": "test"}
    return d


def write_toy_corpus(data_dir: Path) -> Path:
    t = data_dir / "traits" / "instructions"
    r = data_dir / "roles" / "instructions"
    t.mkdir(parents=True, exist_ok=True)
    r.mkdir(parents=True, exist_ok=True)
    docs = {}
    for a, b in TRAIT_PAIRS:
        arr = {"kind": "pair", "members": sorted([a, b])}
        docs[a] = _trait_doc(a, neg=b, arrangement=arr)
        docs[b] = _trait_doc(b, neg=a, arrangement=arr)
    for s in TRIANGLE:
        docs[s] = _trait_doc(s, arrangement={"kind": "triangle", "members": sorted(TRIANGLE)})
    for s in SINGLE_TRAITS + PENDING_TRAITS:
        docs[s] = _trait_doc(s, arrangement={"kind": "singleton"})
    for cur, old in RENAMED.items():
        docs[cur] = _trait_doc(cur, arrangement={"kind": "singleton"}, renamed_from=old)
    for s, d in docs.items():
        (t / f"{s}.json").write_text(json.dumps(d), encoding="utf-8")
    for s in ROLE_PAIR:
        (r / f"{s}.json").write_text(json.dumps({"description": f"A {s} is someone who acts as a {s}, role {s}.",
                                                 "arrangement": {"kind": "pair", "members": sorted(ROLE_PAIR)}}))
    for s in SINGLE_ROLES:
        (r / f"{s}.json").write_text(json.dumps({"description": f"A {s} is someone of the kind {s}, role {s}.",
                                                 "arrangement": {"kind": "singleton"}}))
    (r / "default.json").write_text(json.dumps({"instruction": []}))
    return data_dir


def toy_vector_stems() -> list[tuple[str, str]]:
    """``[(stem, kind)]`` of the toy May tree: every trait file but the pending ones and the renamed ones (whose
    vectors carry the old stems), plus an orphan of each kind; every role but ``default``."""
    traits = [a for p in TRAIT_PAIRS for a in p] + TRIANGLE + SINGLE_TRAITS + list(RENAMED.values()) + ORPHANS["traits"]
    roles = list(ROLE_PAIR) + SINGLE_ROLES + ORPHANS["roles"]
    return [(s, "traits") for s in sorted(traits)] + [(s, "roles") for s in sorted(roles)]


DIM = 48


def toy_raw_vectors(seed: int = 0) -> dict[tuple[str, str], np.ndarray]:
    """Raw (uncentred) toy vectors: random, with each clean pair's poles sharing a component and pointing apart
    along a pair axis."""
    rng = np.random.default_rng(seed)
    out = {}
    for s, k in toy_vector_stems():
        out[(s, k)] = rng.standard_normal(DIM) + 3.0
    for a, b in TRAIT_PAIRS:
        shared = rng.standard_normal(DIM)
        axis = rng.standard_normal(DIM)
        out[(a, "traits")] = 3.0 + shared + axis
        out[(b, "traits")] = 3.0 + shared - axis
    return out


def toy_space(seed: int = 0) -> dict:
    """A :func:`persona.load_persona_space`-shaped record of the toy tree (centred on its mean, no shear)."""
    raw = toy_raw_vectors(seed)
    keys = toy_vector_stems()
    M = np.stack([raw[k] for k in keys]).astype(np.float64)
    return {"stems": [s for s, _ in keys], "kinds": [k for _, k in keys], "M": M - M.mean(axis=0),
            "shear_applied": False, "shear_L": None, "shear_note": "toy", "mean_over": "traits+roles", "slot": 6,
            "layer": 25, "n": len(keys)}


def write_vectors_tree(root: Path, vectors: dict[tuple[str, str], np.ndarray], *, slot: int = 6,
                       layer: int = 25) -> Path:
    """``<root>/{traits,roles}/vectors/<stem>.pt``, each ``{"vector": (slot + 1, layer + 1, d)}`` with the row at
    ``[slot, layer]``."""
    import torch
    for (s, k), v in vectors.items():
        d = root / k / "vectors"
        d.mkdir(parents=True, exist_ok=True)
        t = torch.zeros((slot + 1, layer + 1, len(v)), dtype=torch.float32)
        t[slot, layer] = torch.tensor(np.asarray(v, dtype=np.float32))
        torch.save({"vector": t}, d / f"{s}.pt")
    return root


def fill_cache(cache_dir: Path, texts, *, dim: int = 64, tag: str = OPENAI_TAG) -> None:
    """Put hash embeddings of ``texts`` in an embedding cache under the live model's tag, so the CLI finds every
    text cached and calls nothing."""
    from assistant_axis.gapgen.embed import EmbeddingCache, HashEmbedder
    texts = list(dict.fromkeys(texts))
    vecs, _ = HashEmbedder(dim).embed_batch(texts)
    c = EmbeddingCache(root=cache_dir)
    c.put(tag, texts, vecs, model_id="text-embedding-3-large")
    c.save()
