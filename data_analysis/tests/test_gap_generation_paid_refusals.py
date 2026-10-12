"""Code review 2026-10-12, B4 (reviews 1 D2, D3 and D4): the paid CLIs' refusals.

* ``runs.dirty_refusal``, the dirty-tree check the generator CLIs now share with the filter;
* ``rubric_versions.refusal_lines`` and the plain-reading CLI's refusal on an unpinned prompt;
* ``split_cli.resume_mismatch`` refusing a resume across a prompt version or text change.

The per-CLI dirty-tree refusals are tested beside each CLI's own fixtures (base model, IPIP, Roget, corpus
regions).  No network, no model."""
from __future__ import annotations

import argparse
import json

import pytest

from assistant_axis.gapgen import rubric_versions
from assistant_axis.gapgen.runs import PLATFORM_PATHS, dirty_refusal


class TestDirtyRefusal:
    def test_clean_tree_is_not_refused(self):
        refused, rec = dirty_refusal([], False)
        assert refused is None
        assert rec == {"paths": list(PLATFORM_PATHS), "dirty": [], "allow_dirty": False, "note": None}

    def test_dirty_tree_is_refused_unless_allowed(self):
        dirty = [" M assistant_axis/gapgen/cost.py", "?? data_analysis/gap_generation/new.py"]
        refused, rec = dirty_refusal(dirty, False)
        assert "uncommitted changes" in refused and "--allow-dirty" in refused and "cost.py" in refused
        assert rec["dirty"] == dirty
        refused, rec = dirty_refusal(dirty, True)
        assert refused is None and rec["allow_dirty"] is True and rec["dirty"] == dirty

    def test_git_unavailable_is_recorded_not_refused(self):
        refused, rec = dirty_refusal(None, False)
        assert refused is None and rec["note"] == "git unavailable: not checked"


class TestRubricRefusalLines:
    def test_empty_when_every_pin_holds(self):
        assert rubric_versions.mismatches() == [] and rubric_versions.refusal_lines() == []

    def test_split_and_other_prompts(self, monkeypatch):
        monkeypatch.setattr(rubric_versions, "mismatches", lambda: [
            "probe: text changed (sha ab...) but version 3 is pinned to cd...: bump the version",
            "split.kind: text changed (sha ab...)"])
        lines = rubric_versions.refusal_lines()
        assert lines[0].startswith("REFUSED (rubric not pinned): probe:")
        assert lines[1].startswith("REFUSED (rubric not pinned): split.kind:")
        assert "rubric_pins.py bump kind" in "\n".join(lines)
        assert "rubric_versions.py" in lines[-1]


def test_plain_reading_refuses_an_unpinned_prompt(tmp_path, monkeypatch, capsys):
    from data_analysis.gap_generation import plain_reading as cli
    monkeypatch.setattr(cli, "git_sha", lambda *a, **k: "abc")
    monkeypatch.setattr(cli, "platform_dirty_files", lambda *a, **k: [])
    monkeypatch.setattr(rubric_versions, "mismatches",
                        lambda: ["comparison: text changed (sha ab...) but version 2 is pinned to cd..."])
    pairs = tmp_path / "pairs.jsonl"
    pairs.write_text(json.dumps({"label": "calm", "intended": "This means staying even under stress."}) + "\n")
    cand = tmp_path / "cand"
    argv = ["--batch-id", "pr", "--pairs", str(pairs), "--out-root", str(cand)]
    assert cli.main(argv) == 2
    assert "REFUSED (rubric not pinned): comparison" in capsys.readouterr().err
    assert not (cand / "plain_reading" / "pr").exists()
    # a dry run says so and goes on (it writes nothing either way)
    assert cli.main(argv + ["--dry-run"]) == 0
    assert "REFUSED (rubric not pinned)" in capsys.readouterr().err
    assert not (cand / "plain_reading").exists()


class TestResumeMismatch:
    STEPS = {"sense": 8, "kind": 6}
    SHAS = {"sense": "a" * 64, "kind": "b" * 64, "probe": "c" * 64}

    def _args(self):
        return argparse.Namespace(model="claude-haiku-5-5", readings=3)

    def _earlier(self, **kw):
        return {"model": "claude-haiku-5-5", "readings": 3, "step_versions": dict(self.STEPS),
                "prompt_sha256": dict(self.SHAS), **kw}

    def test_same_prompts_resume(self):
        from data_analysis.gap_generation.split_cli import resume_mismatch
        assert resume_mismatch(self._earlier(), self._args(), step_versions=dict(self.STEPS),
                               prompt_sha256=dict(self.SHAS)) is None

    def test_a_version_change_is_refused(self):
        from data_analysis.gap_generation.split_cli import resume_mismatch
        why = resume_mismatch(self._earlier(), self._args(), step_versions={**self.STEPS, "kind": 7},
                              prompt_sha256=dict(self.SHAS))
        assert "prompt version changed" in why and "kind 6 -> 7" in why and "new --batch-id" in why

    def test_a_text_change_is_refused(self):
        from data_analysis.gap_generation.split_cli import resume_mismatch
        why = resume_mismatch(self._earlier(), self._args(), step_versions=dict(self.STEPS),
                              prompt_sha256={**self.SHAS, "probe": "d" * 64})
        assert "prompt text changed" in why and "probe" in why

    def test_a_dropped_prompt_is_refused_and_a_new_one_is_not(self):
        from data_analysis.gap_generation.split_cli import resume_mismatch
        steps_without_kind = {"sense": 8}
        assert "kind" in resume_mismatch(self._earlier(), self._args(), step_versions=steps_without_kind,
                                         prompt_sha256=dict(self.SHAS))
        assert resume_mismatch(self._earlier(), self._args(), step_versions={**self.STEPS, "gloss": 3},
                               prompt_sha256={**self.SHAS, "gloss": "e" * 64}) is None

    def test_a_run_without_the_fields_is_not_compared(self):
        """A run recorded before step_versions / prompt_sha256 existed cannot be compared: resumed as before."""
        from data_analysis.gap_generation.split_cli import resume_mismatch
        old = {"model": "claude-haiku-5-5", "readings": 3}
        assert resume_mismatch(old, self._args(), step_versions={"kind": 99}, prompt_sha256={"kind": "x"}) is None

    def test_model_and_readings_still_checked_first(self):
        from data_analysis.gap_generation.split_cli import resume_mismatch
        assert "--model" in resume_mismatch(self._earlier(model="claude-haiku-4-5-20251001"), self._args(),
                                            step_versions=dict(self.STEPS), prompt_sha256=dict(self.SHAS))
