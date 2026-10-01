"""Tests for assistant_axis/gapgen/metric_config.py (M2 round 3: two settings)."""
import json

import pytest

from assistant_axis.gapgen.metric_config import MetricConfig, validate_payload

PAYLOAD = {
    "config_version": "2026-10-02",
    "models": {"openai": "text-embedding-3-large", "local": ["BAAI/bge-large-en-v1.5", "google/embeddinggemma-300m"]},
    "covered": {"space": {"variant": "centred", "mean": "corpus_fixed"}, "representation": "w14", "metric": "cos",
                "contrast": {"openai": "keep"}, "thresholds": {"openai": {"t_hi": 0.62, "t_lo": 0.25}},
                "evaluation": {"paraphrase_recall_top1": {"openai": 0.97}}},
    "directional": {"space": {"variant": "centred", "mean": "corpus_fixed"}, "representation": "full", "K": 20,
                    "K_rule": "proxy: task (c)", "K_sensitivity": {"10": 0.29, "20": 0.26}, "evaluation": {}},
}


def test_two_blocks_round_trip(tmp_path):
    p = tmp_path / "metric_config.json"
    p.write_text(json.dumps({"result": PAYLOAD, "_provenance": {}}))
    cfg = MetricConfig.load(path=p)
    assert cfg.config_version == "2026-10-02"
    assert cfg.covered["representation"] == "w14" and cfg.directional["K"] == 20
    # the plan's single-setting accessors read the covered block
    assert cfg.space["variant"] == "centred" and cfg.thresholds["openai"]["t_hi"] == 0.62
    assert cfg.to_json()["directional"]["K"] == 20


def test_validation_names_what_is_missing():
    bad = json.loads(json.dumps(PAYLOAD))
    del bad["directional"]["K"]
    with pytest.raises(ValueError, match="directional.K"):
        validate_payload(bad)
    bad = json.loads(json.dumps(PAYLOAD))
    bad["covered"]["representation"] = "w99"
    with pytest.raises(ValueError, match="representation"):
        validate_payload(bad)
    validate_payload(PAYLOAD)
