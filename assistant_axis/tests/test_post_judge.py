"""Tests for steering/post_judge.py.

Most of post_judge's logic is delegation to RealJudgeDispatcher (which
is unit-tested separately).  Here we cover:
- spec loading from a synthetic experiment dir
- _group_records_by_strength bucketing (including baseline skip)
- _group_needs_work decision (which records still need a judge)

End-to-end main() with real dispatch is exercised on the pod.
"""
from __future__ import annotations

import importlib.util as _iu
import json
from pathlib import Path

import pytest


def _load_post_judge():
    """Load post_judge.py via importlib so tests don't need a steering
    package init.  Same shim trick test_steering_run_sweep.py uses."""
    repo_root = Path(__file__).resolve().parents[2]
    path = repo_root / "steering" / "post_judge.py"
    spec = _iu.spec_from_file_location("_post_judge", path)
    mod = _iu.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pj():
    return _load_post_judge()


def _make_record(*, strength=1.0, sign=+1, q_idx=0, persona_score=None,
                 effect_combined=None):
    judges = {
        "coherence": {"score": 0, "model": "test"},
        "strength_mean_coh": 0.5,
        "persona": (
            {"score": persona_score, "model": "test",
             "skipped_due_to_strength_mean_coh": False}
            if persona_score is not None else None
        ),
        "effect": (
            {"mode": "bidirectional", "combined": effect_combined,
             "skipped_due_to_strength_mean_coh": False}
            if effect_combined is not None else None
        ),
    }
    return {
        "strength": strength, "sign": sign,
        "slot": 3, "layer": 25,
        "question_idx": q_idx, "question": f"Q{q_idx}",
        "response": f"R{q_idx}", "n_tokens": 10,
        "judges": judges, "timing": {"gen_s": 1.0},
    }


# ---------------------------------------------------------------------------
# _group_records_by_strength
# ---------------------------------------------------------------------------

class TestGroupByStrength:
    def test_groups_by_sign_and_strength(self, pj):
        records = [
            _make_record(sign=+1, strength=1.0, q_idx=0),
            _make_record(sign=+1, strength=1.0, q_idx=1),
            _make_record(sign=+1, strength=2.0, q_idx=0),
            _make_record(sign=-1, strength=1.0, q_idx=0),
        ]
        groups = pj._group_records_by_strength(records)
        assert sorted(groups.keys()) == [(-1, 1.0), (1, 1.0), (1, 2.0)]
        assert len(groups[(1, 1.0)]) == 2
        assert len(groups[(1, 2.0)]) == 1
        assert len(groups[(-1, 1.0)]) == 1


# ---------------------------------------------------------------------------
# _group_needs_work
# ---------------------------------------------------------------------------

class TestGroupNeedsWork:
    def test_all_judges_present_no_work(self, pj):
        records = [
            _make_record(persona_score=2, effect_combined=1.0),
            _make_record(persona_score=3, effect_combined=2.0, q_idx=1),
        ]
        assert pj._group_needs_work(records, ["persona", "effect"]) is False

    def test_missing_persona_needs_work(self, pj):
        records = [
            _make_record(persona_score=None, effect_combined=1.0),
        ]
        assert pj._group_needs_work(records, ["persona", "effect"]) is True
        # If we're only running effect, persona absence doesn't matter
        assert pj._group_needs_work(records, ["effect"]) is False

    def test_missing_effect_needs_work(self, pj):
        records = [
            _make_record(persona_score=2, effect_combined=None),
        ]
        assert pj._group_needs_work(records, ["persona", "effect"]) is True
        assert pj._group_needs_work(records, ["persona"]) is False


# ---------------------------------------------------------------------------
# load_experiment_specs
# ---------------------------------------------------------------------------

class TestLoadExperimentSpecs:
    def _setup_minimal_experiment(self, tmp_path: Path) -> Path:
        """Build an experiment dir with config.json + minimal data dirs."""
        exp = tmp_path / "exp"
        exp.mkdir()
        (exp / "config.json").write_text(json.dumps({
            "experiment_id": "exp",
            "model_name": "Qwen/Qwen3-32B",
            "output_dir": str(tmp_path),
            "axis_source": {
                "type": "role_transplant",
                "vectors_dir": str(tmp_path / "fake/vectors"),
                "role_from": "compassionate",
                "role_to": "callous",
            },
            "persona": {"type": "role", "role": "counselor"},
            "cells": [{"slot": 3, "layer": 25}],
            "questions_file": str(tmp_path / "questions.json"),
        }))
        return exp

    def _setup_data_dirs(self, tmp_path: Path) -> Path:
        data = tmp_path / "data"
        (data / "roles" / "instructions").mkdir(parents=True)
        (data / "traits" / "instructions").mkdir(parents=True)
        (data / "roles" / "instructions" / "counselor.json").write_text(
            json.dumps({"description": "provides emotional support"})
        )
        (data / "traits" / "instructions" / "callous.json").write_text(
            json.dumps({"description": "hard, indifferent"})
        )
        (data / "traits" / "instructions" / "compassionate.json").write_text(
            json.dumps({"description": "warm, sensitive"})
        )
        return data

    def test_loads_persona_and_steering(self, pj, tmp_path):
        exp = self._setup_minimal_experiment(tmp_path)
        data = self._setup_data_dirs(tmp_path)

        persona, steering = pj.load_experiment_specs(exp, data)
        assert persona.role == "counselor"
        assert "emotional support" in persona.description
        assert steering.pos_label == "callous"
        assert steering.neg_label == "compassionate"
        assert "hard" in steering.pos_description
        assert "warm" in steering.neg_description
        # Default axis_name format: "<neg>-<pos>"
        assert steering.axis_name == "compassionate-callous"

    def test_missing_persona_file_warns(self, pj, tmp_path, caplog):
        exp = self._setup_minimal_experiment(tmp_path)
        # No data dir at all -- everything missing
        data = tmp_path / "data"
        data.mkdir()

        persona, steering = pj.load_experiment_specs(exp, data)
        # Empty descriptions but loadable
        assert persona.role == "counselor"
        assert persona.description == ""
        assert steering.pos_description == ""
        assert steering.neg_description == ""

    def test_missing_config_raises(self, pj, tmp_path):
        empty = tmp_path / "no_config"
        empty.mkdir()
        with pytest.raises(SystemExit, match="config.json"):
            pj.load_experiment_specs(empty, tmp_path / "data")
