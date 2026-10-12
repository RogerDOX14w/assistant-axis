"""Steps 2 and 3 read response records that carry the additive fields of
walk-through P6 (2026-10-12): ``question_id``, ``finish_reason``,
``thinking_stripped``, ``thinking_suspected``.  Both read records by key, so
the new keys must change nothing: the same activation keys and tensors in
step 2, the same judge requests in step 3.  Fakes only (no model, no API).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import torch

from assistant_axis.tests.internals_fakes import make_fake_probing_model

REPO = Path(__file__).resolve().parents[2]
NEW_FIELDS = {"question_id": 21, "finish_reason": "length", "thinking_stripped": False,
              "thinking_suspected": True}


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _record(i, text, *, new):
    rec = {"system_prompt": "You are a pirate", "prompt_index": i % 2, "question_index": i,
           "question": "What is law?", "label": "pos",
           "conversation": [{"role": "system", "content": "You are a pirate"},
                            {"role": "user", "content": "What is law?"},
                            {"role": "assistant", "content": text}]}
    if new:
        rec.update(NEW_FIELDS)
    return rec


def _write(path, *, new):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for i, text in enumerate(["Arr, the law be the code.", "Yes", "No law at sea."]):
            f.write(json.dumps(_record(i, text, new=new)) + "\n")


def test_step2_activations_are_unchanged_by_the_new_fields(tmp_path):
    step2 = _load("_p6_step2", "pipeline/2_activations.py")
    pm = make_fake_probing_model(3)
    out = {}
    for new in (False, True):
        d = tmp_path / ("new" if new else "old")
        _write(d / "pirate.jsonl", new=new)
        saved, _ = step2.process_role(pm, d / "pirate.jsonl", d, [0, 1, 2], batch_size=2,
                                      max_length=2048)
        assert saved
        out[new] = torch.load(d / "pirate.pt", map_location="cpu", weights_only=False)
    old, new = out[False], out[True]
    assert sorted(k for k in new if k != "metadata") == ["pos_p0_q0", "pos_p0_q2", "pos_p1_q1"]
    for k in old:
        if k != "metadata":
            assert torch.equal(old[k], new[k])


def test_step3_judges_the_same_requests(tmp_path):
    step3 = _load("_p6_step3", "pipeline/3_judge.py")
    reqs = {}
    for new in (False, True):
        path = tmp_path / ("new" if new else "old") / "pirate.jsonl"
        _write(path, new=new)
        responses = step3.load_responses(path)
        reqs[new] = step3.pending_prompts(responses, "Q: {question} A: {answer}", {})
    assert reqs[True] == reqs[False]
    assert [k for k, _ in reqs[True]] == ["pos_p0_q0", "pos_p1_q1", "pos_p0_q2"]
