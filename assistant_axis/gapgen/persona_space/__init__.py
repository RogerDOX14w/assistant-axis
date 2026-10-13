"""Novelty measured in persona space (workstream 12; reports/trait_gap_generation/coding_plan_12_persona_space.md).

A scorer, not a generator: a ridge map from a description's text embedding to the entity's Qwen3-32B persona vector
(fitted on the extracted traits and roles, with a kind covariate), used to place every registry candidate among the
extracted entities: its nearest entities, the energy of its predicted vector outside the pool's top N principal
directions (read as a percentile against held-out entities), the position along its nearest trait's clean-pair
axis, and a flag (``duplicate_like``, ``novel_like``, ``ordinary``), written to the registry row's ``persona`` block
beside M3's decision without touching it.

Modules: :mod:`.pool` (the pool and its training rows), :mod:`.fit` (ridge, grouped cross-validation, the choice of
alpha and N), :mod:`.calibrate` (percentiles and flags), :mod:`.score` (candidates, scores, the block),
:mod:`.compare` (agreement with M3, the disagreements), :mod:`.judge` (decision 2b: M3's overlap call on the
``dup_vs_new`` rows), :mod:`.prospective` (the entities with no vector yet), :mod:`.report`.  The CLI is
``data_analysis/gap_generation/persona_novelty.py``.

Frozen interface (for plan 13's dashboard, the review graph and a later M3 rule): ``PERSONA_DIR``,
``PERSONA_BLOCK_VERSION``, ``load_pool``, ``Pool``, ``load_fit``, ``Fit``, ``predict_texts``, ``score_vectors``,
``PersonaScore``, ``persona_block``, ``Calibration``.  Fields are added, never renamed, without a version bump; a
change to the space (cell, shear, mean) or to the embedding model is a new ``config_version`` and a new fit id.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from ..paths import DATA_CANDIDATES, DATA_DIR
from ..persona import DEFAULT_VECTORS_DIR
from .calibrate import Calibration
from .fit import Model, load_model, predict
from .pool import Pool, load_pool
from .score import PERSONA_BLOCK_VERSION, PersonaScore, persona_block, score_vectors

PERSONA_DIR = DATA_CANDIDATES / "persona"
FIT_SUBDIR, SCORE_SUBDIR, PROSPECTIVE_SUBDIR = "fit", "score", "prospective"
MODEL_FILE = "model.npz"


def fit_dir(fit_id: str, out_root: Optional[Path] = None) -> Path:
    from ..paths import check_id
    return Path(out_root or PERSONA_DIR) / FIT_SUBDIR / check_id(fit_id, "fit_id")


def score_dir(batch_id: str, out_root: Optional[Path] = None) -> Path:
    from ..paths import check_id
    return Path(out_root or PERSONA_DIR) / SCORE_SUBDIR / check_id(batch_id, "batch_id")


def prospective_dir(fit_id: str, out_root: Optional[Path] = None) -> Path:
    from ..paths import check_id
    return Path(out_root or PERSONA_DIR) / PROSPECTIVE_SUBDIR / check_id(fit_id, "fit_id")


@dataclass
class Fit:
    model: Model
    calibration: Calibration
    pool: Pool
    fit_id: str = ""
    partners: Optional[dict] = None
    Ns: tuple = ()


def load_fit(fit_id: str, *, out_root: Optional[Path] = None, data_dir: Path = DATA_DIR,
             vectors_dir: Path = DEFAULT_VECTORS_DIR, pool_cache_dir: Optional[Path] = None) -> Fit:
    """A recorded fit: its model (``model.npz``, rebuilt by ``persona_novelty.py fit`` when missing), its
    calibration and the pool it was fitted on."""
    from .pool import pair_partners
    d = fit_dir(fit_id, out_root)
    mp = d / MODEL_FILE
    if not mp.exists():
        raise FileNotFoundError(f"{mp} is missing (git-ignored): rebuild it with `persona_novelty.py fit --fit-id "
                                f"{fit_id}`, which reproduces it from the same inputs")
    cal = Calibration.from_dict(json.loads((d / "calibration.json").read_text(encoding="utf-8")))
    cv = json.loads((d / "cv.json").read_text(encoding="utf-8")).get("result", {})
    pool = load_pool(data_dir, vectors_dir, cache_dir=pool_cache_dir)
    return Fit(model=load_model(mp), calibration=cal, pool=pool, fit_id=fit_id, partners=pair_partners(pool, data_dir),
               Ns=tuple(int(n) for n in (cv.get("config") or {}).get("Ns", ())))


def predict_texts(fit: Fit, texts: Sequence[str], kinds: Sequence[str], *, embedder=None, cache=None,
                  usage=None) -> np.ndarray:
    """Predicted persona vectors ``(n, 5120)`` float32 for ``texts`` (``label: gloss`` or ``label: description``,
    ``w20``) of entities of ``kinds``: embedded through the platform's cache (misses only, charged to ``usage``)."""
    from ..embed import EmbeddingCache, OpenAIEmbedder, embed_texts
    embedder = embedder or OpenAIEmbedder()
    cache = cache if cache is not None else EmbeddingCache()
    E = embed_texts(embedder, list(texts), cache=cache, usage=usage)
    return predict(fit.model, E, kinds)


__all__ = ["PERSONA_DIR", "PERSONA_BLOCK_VERSION", "load_pool", "Pool", "load_fit", "Fit", "predict_texts",
           "score_vectors", "PersonaScore", "persona_block", "Calibration", "fit_dir", "score_dir", "prospective_dir"]
