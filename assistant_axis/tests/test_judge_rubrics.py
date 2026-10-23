"""Tests for assistant_axis/judge_rubrics.py: pipeline step 3's rubrics by
prompt version (2026-10-23).

Version 0 must be the original text (Christina's role rubric at the fork, the
April 2026 trait and combination rubrics) and reading; version 3 the rubric
step 3 sent until versions were selectable; version 4 version 3 plus the
approved edits and nothing else.  Every role file's baked ``eval_prompt``
against the version 3 rendering, and version 4 against the role rubric
experiment's A1 arm, are checked in pipeline/tests/test_3_judge.py.
"""
from __future__ import annotations

import difflib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from assistant_axis import judge_rubrics as jr

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _git_show(spec: str) -> str:
    try:
        return subprocess.run(["git", "show", spec], cwd=REPO, capture_output=True, text=True,
                              check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip(f"git show {spec} is not available here")


def test_version_3_role_template_is_the_generators():
    rr = _load("_rri_under_test", "data_analysis/regenerate_role_instructions.py")
    assert jr.ROLE_TEMPLATE_V3 == rr.ROLE_EVAL_PROMPT_TEMPLATE


def test_version_0_role_rubric_is_christinas_at_the_fork():
    """Rendered for altruist, whose description has not changed since the
    fork, version 0 is the fork's file byte for byte."""
    fork = json.loads(_git_show("949c35f3:data/prompts/roles/altruist.json"))["eval_prompt"]
    doc = json.loads((REPO / "data" / "roles" / "instructions" / "altruist.json").read_text())
    assert jr.ROLE_TEMPLATE_V0.format(role_name="altruist", description=doc["description"]) == fork


@pytest.mark.parametrize("name,attr", [("TRAIT_EVAL_TEMPLATE", "TRAIT_TEMPLATE_V0"),
                                       ("COMBINED_EVAL_TEMPLATE", "COMBINED_TEMPLATE_V0")])
def test_version_0_trait_and_combination_rubrics_are_the_first_ones(name, attr):
    src = _git_show("cac76b65:pipeline/3_judge.py")
    start = src.index(f"{name} = ")
    end = src.index('"""', start + len(name) + 6) + 3
    ns: dict = {}
    exec(src[start:end], ns)
    assert getattr(jr, attr) == ns[name]


@pytest.mark.parametrize("kind", ["role", "trait", "combination"])
def test_version_0_differs_from_version_3_in_the_closing_line_only(kind):
    v0, v3 = jr.PROMPT_VERSIONS[0].template(kind), jr.PROMPT_VERSIONS[3].template(kind)
    head0, last0 = v0.rsplit("\n\n", 1)
    head3, last3 = v3.rsplit("\n\n", 1)
    assert head0 == head3
    assert last0.startswith("Respond with a number between 0 and 3.") and "SCORE" not in last0
    assert last3.startswith("First, briefly reason") and last3.endswith("SCORE: <integer from 0 to 3>")


def test_version_4_role_rubric_is_version_3_with_a1_only():
    v3, v4 = jr.ROLE_TEMPLATE_V3, jr.ROLE_TEMPLATE_V4
    assert "Gemma" not in v4 and "((" not in v4
    assert v4.count("(an AI assistant, a language model, etc.)") == 3
    changed = [l for l in difflib.ndiff(v3.splitlines(), v4.splitlines()) if l[:1] in "+-"]
    assert len(changed) == 6                                     # levels 0, 1 and 2
    assert all(l[2:].startswith(("- 0 if", "- 1 if", "- 2 if")) for l in changed)


def test_version_4_trait_and_combination_rubrics_are_version_3s():
    assert jr.PROMPT_VERSIONS[4].trait == jr.PROMPT_VERSIONS[3].trait
    assert jr.PROMPT_VERSIONS[4].combination == jr.PROMPT_VERSIONS[3].combination


def test_settled_versions_are_never_edited():
    """A settled version's text is fixed: if this fails, the change belongs in
    a new version (or in the draft), not in this one.  The draft is not pinned."""
    pins = {0: {"role": "64b2f40f105169fc", "trait": "fb7b719698c5848c", "combination": "a3e0e4c381062b08"},
            3: {"role": "15d953a9bce06828", "trait": "9b9adda764fe6d86", "combination": "bee3d69ad7a814a8"}}
    for v, by_type in pins.items():
        assert {k: jr.PROMPT_VERSIONS[v].sha256(k) for k in by_type} == by_type
    assert jr.PROMPT_VERSIONS[4].draft and not jr.PROMPT_VERSIONS[3].draft


def test_versions_and_their_reading():
    assert jr.DEFAULT_PROMPT_VERSION == 3
    assert (jr.PROMPT_VERSIONS[0].reply_format, jr.PROMPT_VERSIONS[0].max_tokens) == ("first_integer", 10)
    for v in (3, 4):
        assert (jr.PROMPT_VERSIONS[v].reply_format, jr.PROMPT_VERSIONS[v].max_tokens) == ("score_marker", 200)
    v0, v3, v4 = (jr.PROMPT_VERSIONS[v] for v in (0, 3, 4))
    assert v0.differs_from(v3) == ("role", "trait", "combination")
    assert v4.differs_from(v3) == ("role",)                  # so far A1 only
    assert v3.differs_from(v3) == ()


@pytest.mark.parametrize("version", sorted(jr.PROMPT_VERSIONS))
def test_every_template_fills_cleanly(version):
    v = jr.PROMPT_VERSIONS[version]
    filled = [v.role.format(role_name="R", description="D."),
              v.trait.format(trait_name="T", trait_description="D."),
              v.combination.format(role_name="R", role_description="D.", trait_name="T",
                                   trait_description="E.")]
    for tpl in filled:
        out = tpl.format(question="Q?", answer="A.")
        assert "Q?" in out and "A." in out and "{" not in out


def test_historical_and_unknown_versions_are_refused():
    with pytest.raises(ValueError, match="not runnable"):
        jr.get_version(1)
    with pytest.raises(ValueError, match="not runnable"):
        jr.get_version(2)
    with pytest.raises(ValueError, match="no prompt version 9"):
        jr.get_version(9)
    with pytest.raises(ValueError, match="Unknown entity_type"):
        jr.PROMPT_VERSIONS[3].template("default")


@pytest.mark.parametrize("text,score", [
    ("2", 2), (" 3\n", 3), ("0", 0), ("Score: 1", 1),
    ("I'd say 2, maybe 3", 2),          # the first integer, as the fork read it
    ("4", None), ("10", None),          # out of range: None, not a later digit
    ("4 ... 2", None), ("", None), (None, None), ("three", None),
    ("x2", None),                        # \\b: digits inside a word are not a number
])
def test_first_integer_score_reads_as_the_fork_did(text, score):
    assert jr.first_integer_score(text) == score


def test_apply_edits_refuses_a_passage_it_cannot_find():
    with pytest.raises(ValueError, match="occurs 0 times, expected 1"):
        jr.apply_edits("abc", [("x", "y", 1)], what="t")
    assert jr.apply_edits("a a", [("a", "b", 2)], what="t") == "b b"
