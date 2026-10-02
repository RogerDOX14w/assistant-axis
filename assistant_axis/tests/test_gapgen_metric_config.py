"""Tests for assistant_axis/gapgen/metric_config.py.

Round 3 split the config into two blocks; task 19 (Roger, 2026-10-02, coding_plan_platform.md "M2 final
settings and the M3 design") made the covered block a retrieval setting (``k``), recorded the thresholds as
information only, named one live model and an inactive fallback, and added the drift canary."""
import inspect
import json

import pytest

from assistant_axis.gapgen.metric_config import MetricConfig, validate_payload
from assistant_axis.gapgen.paths import METRIC_CONFIG_PATH

SPACE = {"variant": "centred", "mean": "corpus_fixed"}
PAYLOAD = {
    "config_version": "2026-10-02",
    "models": {"live": {"arm": "openai", "model_id": "text-embedding-3-large"},
               "fallback": {"arm": "gemma", "model_id": "google/embeddinggemma-300m", "active": False,
                            "settings": {"covered": {"representation": "w20", "space": SPACE, "k": 10},
                                         "directional": {"representation": "w20", "space": SPACE, "K": 10}}},
               "dropped": [{"arm": "bge", "model_id": "BAAI/bge-large-en-v1.5"}]},
    "covered": {"space": SPACE, "representation": "w20", "metric": "cos", "k": 10, "contrast": {"openai": "keep"},
                "retrieval": {"model": "openai", "recall_at_k": {"pooled": {"n": 3098, "10": 0.99}}},
                "thresholds": {"used_for_decisions": False, "note": "information only",
                               "openai": {"t_hi": 0.40, "t_lo": 0.24}},
                "evaluation": {"paraphrase_recall_top1": {"openai": 0.94}}},
    "directional": {"space": SPACE, "representation": "w20", "K": 10, "K_rule": "fixed, provisional",
                    "K_sensitivity": {"10": 0.30, "20": 0.26}, "evaluation": {}},
    "canary": {"n": 2, "min_cosine": 0.999, "texts": [{"stem": "calm", "text": "calm: This means calm."},
                                                      {"stem": "loyal", "text": "loyal: This means loyal."}]},
}


def _bad(**edits):
    d = json.loads(json.dumps(PAYLOAD))
    for path, value in edits.items():
        *head, last = path.split("__")
        node = d
        for h in head:
            node = node[h]
        if value is KeyError:
            del node[last]
        else:
            node[last] = value
    return d


def test_final_schema_round_trip(tmp_path):
    p = tmp_path / "metric_config.json"
    p.write_text(json.dumps({"result": PAYLOAD, "_provenance": {}}))
    cfg = MetricConfig.load(path=p)
    assert cfg.config_version == "2026-10-02"
    assert cfg.covered["representation"] == "w20" and cfg.directional["K"] == 10
    assert cfg.k == 10 and cfg.live_model == {"arm": "openai", "model_id": "text-embedding-3-large"}
    assert cfg.fallback_model["active"] is False and len(cfg.canary["texts"]) == 2
    # the plan's single-setting accessors still read the covered block
    assert cfg.space["variant"] == "centred" and cfg.representation == "w20"
    assert cfg.thresholds["openai"]["t_hi"] == 0.40 and cfg.thresholds["used_for_decisions"] is False
    assert cfg.to_json()["canary"]["min_cosine"] == 0.999 and cfg.to_json()["directional"]["K"] == 10


def test_frozen_interface_unchanged():
    # coding_plan_platform.md § Frozen interface: MetricConfig, MetricConfig.load(path=METRIC_CONFIG_PATH),
    # config_version keep their names and signatures
    sig = inspect.signature(MetricConfig.load)
    assert list(sig.parameters) == ["path"] and sig.parameters["path"].default is None
    assert "config_version" in MetricConfig.__dataclass_fields__
    assert METRIC_CONFIG_PATH.name == "metric_config.json"


@pytest.mark.parametrize("edits, match", [
    ({"directional__K": KeyError}, "directional.K"),
    ({"covered__representation": "w99"}, "representation"),
    ({"covered__k": KeyError}, "covered.k"),
    ({"covered__k": 0}, "covered.k"),
    ({"covered__k": 2.5}, "covered.k"),
    ({"covered__retrieval": KeyError}, "covered.retrieval"),
    ({"covered__thresholds__used_for_decisions": True}, "used_for_decisions"),
    ({"models__live": KeyError}, "models.live"),
    ({"models__live__model_id": KeyError}, "models.live"),
    ({"models__fallback__active": True}, "fallback"),
    ({"canary": KeyError}, "canary"),
    ({"canary__texts": []}, "canary.texts"),
    ({"canary__min_cosine": 1.5}, "canary.min_cosine"),
    ({"config_version": ""}, "config_version"),
])
def test_validation_names_what_is_wrong(edits, match):
    with pytest.raises(ValueError, match=match):
        validate_payload(_bad(**edits))


def test_valid_payload_and_optional_parts():
    validate_payload(PAYLOAD)
    # thresholds are information only and may be absent; the fallback may be absent
    validate_payload(_bad(covered__thresholds=KeyError, models__fallback=KeyError))
