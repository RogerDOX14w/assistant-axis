"""The metric configuration M3 reads (``data/candidates/metric_config.json``).

Round 3 (Roger, 2026-10-02): the embedding serves two uses in M3, tuned
separately, so the config carries two blocks over the same cached embeddings:

* ``covered``: is a candidate already in the corpus?  Space variant,
  representation (scope-matched), similarity metric, contrast policy and the
  per-model thresholds ``t_hi`` / ``t_lo``; chosen on task (a) and on
  paraphrase recall at the 0.95 target.  Task (b) (duplicate vs antonym) is
  reported in ``evaluation`` as the confusion the LLM adjudicator absorbs.
* ``directional``: does a candidate add a direction?  Space variant,
  representation and K for the residual fraction; chosen on task (c), a proxy,
  with the K sensitivity and criterion (i) beside it.

Frozen interface (coding_plan_platform.md § Frozen interface): ``MetricConfig``
and ``MetricConfig.load(path=METRIC_CONFIG_PATH)`` and ``config_version`` are
unchanged.  The plan's single-setting fields (``representation``, ``space``,
``thresholds``) remain readable as properties and point at the ``covered``
block, so code written against §6's example keeps working.
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
    "covered": ("space", "representation", "metric", "thresholds"),
    "directional": ("space", "representation", "K"),
}


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
    if d["covered"]["metric"] not in ("cos", "csls"):
        raise ValueError("covered.metric must be cos or csls")
    if not isinstance(d["directional"]["K"], int) or d["directional"]["K"] < 1:
        raise ValueError("directional.K must be a positive integer")


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
        return self.covered["thresholds"]
