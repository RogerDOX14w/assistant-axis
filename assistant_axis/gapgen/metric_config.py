"""The metric configuration M3 reads (``data/candidates/metric_config.json``).

Round 3 (Roger, 2026-10-02): the embedding serves two uses in M3, tuned
separately, so the config carries two blocks over the same cached embeddings.
Task 19 (Roger, 2026-10-02; coding_plan_platform.md, "M2 final settings and the
M3 design") fixed their content for the retrieve-then-judge design:

* ``covered``: is a candidate already in the corpus?  Space variant,
  representation, similarity metric, contrast policy and **``k``**, the number
  of nearest existing traits handed to the LLM relation and overlap calls;
  ``retrieval`` records recall@k per query source and pooled.  No similarity
  threshold decides covered or new: ``thresholds`` (``t_hi`` / ``t_lo`` per
  model), when present, is information only and says so
  (``used_for_decisions: false``).
* ``directional``: does a candidate add a direction?  Space variant,
  representation and K for the residual fraction (provisional), with the K
  sensitivity and the proxy caveat.
* ``models``: ``live`` (the one model whose embeddings a run uses) and an
  optional ``fallback`` that must be inactive (its own settings recorded, never
  mixed into a run's results); dropped models are listed for the record.
* ``canary``: the fixed texts every embedding run re-embeds and compares with
  the cache (``embed.check_canary``), and the cosine below which it warns.

Frozen interface (coding_plan_platform.md § Frozen interface): ``MetricConfig``
and ``MetricConfig.load(path=METRIC_CONFIG_PATH)`` and ``config_version`` are
unchanged.  The plan's single-setting fields (``representation``, ``space``,
``thresholds``) remain readable as properties and point at the ``covered``
block; ``k``, ``live_model``, ``fallback_model`` and ``canary`` are additions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from .paths import METRIC_CONFIG_PATH
from .representation import REPRESENTATIONS
from .space import VARIANTS

REQUIRED = {
    "covered": ("space", "representation", "metric", "k", "retrieval"),
    "directional": ("space", "representation", "K"),
}


def _positive_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool) and x >= 1


def validate_payload(d: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` naming the first missing or invalid field."""
    if not d.get("config_version"):
        raise ValueError("config_version missing")
    for block, keys in REQUIRED.items():
        b = d.get(block)
        if not isinstance(b, Mapping):
            raise ValueError(f"{block} block missing")
        for k in keys:
            if k not in b:
                raise ValueError(f"{block}.{k} missing")
        if b["representation"] not in REPRESENTATIONS:
            raise ValueError(f"{block}.representation {b['representation']!r} is not one of {list(REPRESENTATIONS)}")
        variant = (b["space"] or {}).get("variant")
        if variant not in VARIANTS:
            raise ValueError(f"{block}.space.variant {variant!r} is not one of {list(VARIANTS)}")
    cov = d["covered"]
    if cov["metric"] not in ("cos", "csls"):
        raise ValueError("covered.metric must be cos or csls")
    if not _positive_int(cov["k"]):
        raise ValueError("covered.k must be a positive integer (the number of neighbours retrieved)")
    if not isinstance(cov["retrieval"], Mapping):
        raise ValueError("covered.retrieval must be a mapping (the retrieval evaluation)")
    thr = cov.get("thresholds")
    if thr is not None and (not isinstance(thr, Mapping) or thr.get("used_for_decisions") is not False):
        raise ValueError("covered.thresholds is information only: it must say used_for_decisions: false")
    if not _positive_int(d["directional"]["K"]):
        raise ValueError("directional.K must be a positive integer")
    models = d.get("models") or {}
    live = models.get("live")
    if not isinstance(live, Mapping) or not live.get("arm") or not live.get("model_id"):
        raise ValueError("models.live must name the live model (arm and model_id)")
    fb = models.get("fallback")
    if fb is not None and (not isinstance(fb, Mapping) or fb.get("active") is not False):
        raise ValueError("models.fallback must be inactive (active: false): it is never mixed into a run's results")
    can = d.get("canary")
    if not isinstance(can, Mapping):
        raise ValueError("canary block missing")
    texts = can.get("texts")
    if not isinstance(texts, list) or not texts or not all(
            isinstance(t, Mapping) and t.get("stem") and t.get("text") for t in texts):
        raise ValueError("canary.texts must be a non-empty list of {stem, text}")
    mc = can.get("min_cosine")
    if not isinstance(mc, (int, float)) or not 0 < mc <= 1:
        raise ValueError("canary.min_cosine must be in (0, 1]")


@dataclass
class MetricConfig:
    config_version: str
    models: dict
    covered: dict
    directional: dict
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_json(cls, d: Mapping[str, Any]) -> "MetricConfig":
        d = d.get("result", d)
        validate_payload(d)
        known = {"config_version", "models", "covered", "directional"}
        return cls(config_version=d["config_version"], models=dict(d.get("models") or {}),
                   covered=dict(d["covered"]), directional=dict(d["directional"]),
                   extra={k: v for k, v in d.items() if k not in known})

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "MetricConfig":
        p = Path(path or METRIC_CONFIG_PATH)
        return cls.from_json(json.loads(p.read_text()))

    def to_json(self) -> dict:
        return {"config_version": self.config_version, "models": self.models, "covered": self.covered,
                "directional": self.directional, **self.extra}

    # the plan's single-setting accessors (§6), read from the covered block
    @property
    def representation(self) -> str:
        return self.covered["representation"]

    @property
    def space(self) -> dict:
        return self.covered["space"]

    @property
    def thresholds(self) -> dict:
        """Information only since task 19 (``used_for_decisions`` is false)."""
        return self.covered.get("thresholds") or {}

    # additions (task 19)
    @property
    def k(self) -> int:
        """How many nearest existing traits the covered setting retrieves."""
        return int(self.covered["k"])

    @property
    def live_model(self) -> dict:
        return dict(self.models["live"])

    @property
    def fallback_model(self) -> Optional[dict]:
        fb = self.models.get("fallback")
        return dict(fb) if fb else None

    @property
    def canary(self) -> dict:
        return dict(self.extra.get("canary") or {})
