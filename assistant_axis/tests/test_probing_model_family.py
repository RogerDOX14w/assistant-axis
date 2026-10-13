"""ProbingModel's family (multi-model plan § 5.4, task 5): ``model_type`` from
the loaded model's config, ``family`` from the table, ``hf_load_kwargs`` to
``from_pretrained``.  No model is loaded: the fakes, and a monkeypatched
``from_pretrained`` for the load path."""
from __future__ import annotations

import pytest
import torch

from assistant_axis.internals import model as model_mod
from assistant_axis.model_families import FAMILIES, UnknownFamilyError
from assistant_axis.tests.internals_fakes import FakeCausalLM, make_fake_probing_model


def test_model_type_and_family_come_from_the_config_not_the_name():
    pm = make_fake_probing_model(model_name="/workspace/models/q3-32b")
    assert pm.model_type == "qwen3"
    assert pm.family is FAMILIES["qwen3"]
    assert pm.detect_type() == "unknown"      # the old name test still misses it


def test_an_unknown_model_type_raises():
    pm = make_fake_probing_model(model_type="nope")
    assert pm.model_type == "nope"
    with pytest.raises(UnknownFamilyError, match="nope"):
        pm.family


def test_hf_load_kwargs_reach_from_pretrained(monkeypatch):
    seen = {}

    class FakeTok:
        pad_token = "<pad>"

        @classmethod
        def from_pretrained(cls, name):
            return cls()

    class FakeAuto:
        @staticmethod
        def from_pretrained(name, **kwargs):
            seen.update(kwargs, name=name)
            return FakeCausalLM(2, model_type="gemma2")

    monkeypatch.setattr(model_mod, "AutoTokenizer", FakeTok)
    monkeypatch.setattr(model_mod, "AutoModelForCausalLM", FakeAuto)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    pm = model_mod.ProbingModel("google/gemma-2-27b-it",
                                hf_load_kwargs=FAMILIES["gemma2"].hf_load_kwargs)
    assert seen["attn_implementation"] == "eager" and seen["dtype"] == torch.bfloat16
    assert seen["name"] == "google/gemma-2-27b-it"
    assert pm.model_type == "gemma2" and pm.family is FAMILIES["gemma2"]

    seen.clear()
    model_mod.ProbingModel("Qwen/Qwen3-32B")                 # none: the load is as before
    assert set(seen) == {"dtype", "device_map", "name"}
