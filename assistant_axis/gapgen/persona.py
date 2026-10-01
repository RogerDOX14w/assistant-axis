"""Persona vectors for the calibration's criteria (c) and (h) (M2; plan 12 step 1).

The persona-space yield score is recomputed here, because the May 2026
per-trait residual fractions survive only for the 24 traits quoted in
``TRAITS_TO_ADD.md`` § "Strategy 1" (``[0.829] `melancholic` ...``), and that
analysis projected onto the top-20 PCs of the 60-axis Gram matrix, a basis
not recorded anywhere.  Plan 12 step 1 instead: the entity pool (traits and
roles) at the canonical cell (8-slot data, slot 6, layer 25), centred on the
pool mean, soft-sheared at L=3 when the goal / no-goal subspaces can be
built, then each trait's residual fraction outside the top-K principal
subspace of the *other* entities (leave-one-out), at K = 37 (95% variance in
plan 12) and the sensitivities 10 / 20 / 40.  ``parse_bracket_scores`` reads
the 24 quoted scores for a cross-check.

The (slot, layer) slice of every vector is cached in
``data/candidates/cache/persona_s<slot>_l<layer>.npz`` (gitignored), keyed by
the files' names, sizes and mtimes, so the 5 MB-per-entity tensors are read
once.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

from .paths import DATA_CANDIDATES, REPO_ROOT
from .space import loo_residuals

logger = logging.getLogger(__name__)

DEFAULT_VECTORS_DIR = REPO_ROOT / "runpod_workspace" / "qwen" / "qwen-3-32b Roger 8slot"
DEFAULT_SLOT, DEFAULT_LAYER, DEFAULT_SHEAR_L = 6, 25, 3
PLAN12_K = 37
SENSITIVITY_KS = (10, 20, 40)

_BRACKET_RE = re.compile(r"^\s*-\s*\[(0\.\d+|1(?:\.0+)?)\]\s*`([a-z0-9_]+)`", re.M)


def parse_bracket_scores(traits_to_add_md: Path | str) -> dict[str, float]:
    """``{stem: residual fraction}`` from lines like ``- [0.829] `melancholic` → ...``.
    Accepts a path or the markdown text itself."""
    src = traits_to_add_md
    is_path = isinstance(src, Path) or ("\n" not in str(src) and Path(str(src)).is_file())
    text = Path(src).read_text(encoding="utf-8") if is_path else str(src)
    out: dict[str, float] = {}
    for score, stem in _BRACKET_RE.findall(text):
        out.setdefault(stem, float(score))
    return out


def _fingerprint(files: Iterable[Path]) -> list[list]:
    return [[f.name, f.stat().st_size, int(f.stat().st_mtime)] for f in files]


def _load_slice(path: Path, slot: int, layer: int) -> np.ndarray:
    import torch
    obj = torch.load(path, map_location="cpu", weights_only=False)
    v = obj.get("vector", obj.get("axis", obj)) if isinstance(obj, dict) else obj
    return v[slot, layer].float().numpy()


def load_pool(data_dir: Path = DEFAULT_VECTORS_DIR, *, slot: int = DEFAULT_SLOT, layer: int = DEFAULT_LAYER,
              cache_dir: Optional[Path] = None) -> tuple[list[str], list[str], np.ndarray]:
    """Every trait and role vector at ``(slot, layer)``: ``(stems, kinds, M)``
    with kinds ``"traits"`` / ``"roles"`` (``default`` excluded).  Uncentred."""
    data_dir = Path(data_dir)
    files = {k: sorted(p for p in (data_dir / k / "vectors").glob("*.pt") if p.stem != "default")
             for k in ("traits", "roles")}
    if not files["traits"]:
        raise FileNotFoundError(f"no trait vectors under {data_dir / 'traits' / 'vectors'}")
    fp = {k: _fingerprint(v) for k, v in files.items()}
    cache = Path(cache_dir or DATA_CANDIDATES / "cache") / f"persona_s{slot}_l{layer}.npz"
    if cache.exists():
        with np.load(cache, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            if meta.get("fingerprint") == fp and meta.get("data_dir") == str(data_dir.resolve()):
                return [str(s) for s in z["stems"]], [str(k) for k in z["kinds"]], z["M"].astype(np.float64)
    stems, kinds, rows = [], [], []
    for k in ("traits", "roles"):
        for f in files[k]:
            stems.append(f.stem)
            kinds.append(k)
            rows.append(_load_slice(f, slot, layer))
    M = np.stack(rows).astype(np.float32)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, stems=np.array(stems), kinds=np.array(kinds), M=M,
             meta=json.dumps({"fingerprint": fp, "data_dir": str(data_dir.resolve()), "slot": slot, "layer": layer}))
    return stems, kinds, M.astype(np.float64)


def fit_pool_shear(data_dir: Path, slot: int, layer: int, L: int):
    """The project's soft shear at ``L`` from the combined goal / no-goal
    subspaces, or ``(None, reason)`` when they cannot be built."""
    import sys
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from results_analysis.canonical_angles.data import build_goal_nogoal_subspaces
        from results_analysis.canonical_angles.whitening import fit_shear
        A_g, A_n = build_goal_nogoal_subspaces(Path(data_dir), slot, layer, kind="combined")
        return fit_shear(A_g, A_n, L=L), None
    except Exception as exc:  # noqa: BLE001 - reported, the fallback is documented
        return None, f"{type(exc).__name__}: {str(exc).splitlines()[0][:200]}"


def load_persona_space(data_dir: Path = DEFAULT_VECTORS_DIR, *, slot: int = DEFAULT_SLOT,
                       layer: int = DEFAULT_LAYER, shear_L: Optional[int] = DEFAULT_SHEAR_L,
                       cache_dir: Optional[Path] = None) -> dict:
    """The centred (and, if buildable, sheared) entity pool:
    ``{"stems", "kinds", "M", "shear_applied", "shear_note", "mean_over", "slot", "layer"}``.
    The mean is the corpus mean over traits and roles together."""
    stems, kinds, M = load_pool(data_dir, slot=slot, layer=layer, cache_dir=cache_dir)
    Mc = M - M.mean(axis=0)
    note = None
    applied = False
    if shear_L:
        shear, note = fit_pool_shear(data_dir, slot, layer, shear_L)
        if shear is not None:
            Mc = shear.apply(Mc)
            applied = True
        else:
            logger.warning("soft shear L=%s not buildable (%s); using corpus-mean-centred raw vectors", shear_L, note)
    return {"stems": stems, "kinds": kinds, "M": Mc, "shear_applied": applied, "shear_L": shear_L,
            "shear_note": note, "mean_over": "traits+roles", "slot": slot, "layer": layer, "n": len(stems)}


def load_trait_vectors(data_dir: Path = DEFAULT_VECTORS_DIR, slot: int = DEFAULT_SLOT, layer: int = DEFAULT_LAYER,
                       shear_L: Optional[int] = DEFAULT_SHEAR_L) -> tuple[list[str], np.ndarray]:
    """``(trait stems, centred trait rows)`` (frozen signature; the mean is over
    traits and roles, the shear applied when buildable; see
    :func:`load_persona_space` for the full record)."""
    ps = load_persona_space(data_dir, slot=slot, layer=layer, shear_L=shear_L)
    idx = [i for i, k in enumerate(ps["kinds"]) if k == "traits"]
    return [ps["stems"][i] for i in idx], ps["M"][idx]


def loo_residual(M: np.ndarray, K: int) -> np.ndarray:
    """Each row's residual fraction outside the top-``K`` principal subspace of
    the other rows (``M`` already centred on the fixed mean)."""
    return loo_residuals(M, [K])[K]
