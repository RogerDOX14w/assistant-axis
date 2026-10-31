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
import re
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
            3: {"role": "15d953a9bce06828", "trait": "9b9adda764fe6d86", "combination": "bee3d69ad7a814a8"},
            # settled 2026-10-28; its role text is version 8's, whose hash the experiment's
            # version 8 directories record (522fae510e0dd298)
            10: {"role": "c19e859a53c91d5e", "trait": "9b9adda764fe6d86", "combination": "bee3d69ad7a814a8"},
            # settled 2026-10-30: version 10's role text and reading, the trait rubric review's
            # trait rubric (the hash its two test runs record), version 3's combination rubric
            13: {"role": "c19e859a53c91d5e", "trait": "4a0f22d96414d97b", "combination": "bee3d69ad7a814a8"},
            # settled 2026-10-31: version 13's roles and traits, the two-sided combination rule
            # (versions 16 and 17; the hash covers both sides' texts and readings)
            20: {"role": "c19e859a53c91d5e", "trait": "4a0f22d96414d97b", "combination": "a1bce358ade70fa5"}}
    for v, by_type in pins.items():
        assert {k: jr.PROMPT_VERSIONS[v].sha256(k) for k in by_type} == by_type
    assert jr.PROMPT_VERSIONS[4].draft and not jr.PROMPT_VERSIONS[3].draft
    assert not jr.PROMPT_VERSIONS[10].draft and jr.PROMPT_VERSIONS[8].sha256("role") == "522fae510e0dd298"
    assert not jr.PROMPT_VERSIONS[13].draft and not jr.PROMPT_VERSIONS[20].draft


def test_version_20_is_the_two_sided_combination_rule():
    """Version 20 (settled 2026-10-31, Roger: "16+17 on the basis of
    precision"): roles and traits exactly as version 13 (same hashes, so their
    directories are shared), and a combination judged on two sides, by version
    16 and by version 17, read as "two_sides"; the hash covers the sides, so an
    edit to either side's text changes it; gpt-5.6-luna for every type."""
    v13, v16, v17, v20 = (jr.PROMPT_VERSIONS[v] for v in (13, 16, 17, 20))
    assert v20.differs_from(v13) == ("combination",)
    assert jr.may_share_directory(13, 20, "role") and jr.may_share_directory(13, 20, "trait")
    assert not jr.may_share_directory(13, 20, "combination") and not jr.may_share_directory(16, 20, "combination")
    assert v20.combination_sides == (("role", 16), ("trait", 17))
    assert v20.side_versions() == {"role": v16, "trait": v17}
    assert v20.reply_format_for("combination") == "two_sides" and v20.max_tokens_for("combination") == 300
    assert v16.max_tokens_for("combination") == 300 and v17.max_tokens_for("combination") == 200
    assert v20.judges_for("combination") == v20.judges_for("role") == v20.judges_for("trait") == ("gpt-5.6-luna",)
    assert v16.judges_for("combination") == () and v13.judges_for("combination") == ()
    assert v20.combination == ("[The role side, prompt version 16]\n\n" + v16.combination
                               + "\n\n[The trait side, prompt version 17]\n\n" + v17.combination)
    assert v20.combination_overrides == () and v20.combination_template("robot") == v20.combination
    assert v20.same_text(v20, "combination") and not v20.same_text(v13, "combination")
    # the hash follows the sides: the same sides give the same hash, other sides another
    from dataclasses import replace
    same = replace(v20, combination=v20.combination + " ")
    assert same.sha256("combination") != v20.sha256("combination")
    other = replace(v20, combination_sides=(("role", 16), ("trait", 18)))
    assert other.sha256("combination") != v20.sha256("combination") and not other.same_text(v20, "combination")
    assert "two_sides" in jr.REPLY_FORMATS


def test_versions_and_their_reading():
    assert jr.DEFAULT_PROMPT_VERSION == 20                    # 13 from 2026-10-30, 10 from 2026-10-28, 3 before
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
              *(tpl.format(role_name="R", description="D.") for _, tpl in v.role_overrides),
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
    with pytest.raises(ValueError, match="rejected draft.*not runnable"):
        jr.get_version(9)
    assert not set(jr.HISTORICAL_VERSIONS) & set(jr.PROMPT_VERSIONS)
    with pytest.raises(ValueError, match="no prompt version 99"):
        jr.get_version(99)
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


def test_version_5_is_version_4_with_the_clause_only():
    """Version 5 (draft, 2026-10-23): version 4's role rubric with one paragraph
    added after level 3, before the closing line; traits and combinations as
    version 4.  It follows version 4, so a later edit to the draft v4 carries over."""
    v4, v5 = jr.PROMPT_VERSIONS[4], jr.PROMPT_VERSIONS[5]
    assert v5.draft and v5.differs_from(v4) == ("role",)
    assert v5.role.replace("\n\n" + jr.V5_ROLE_CLAUSE, "", 1) == v4.role
    paragraphs = v5.role.split("\n\n")
    assert paragraphs[-2] == jr.V5_ROLE_CLAUSE and paragraphs[-1].startswith("First, briefly reason")
    assert paragraphs[-3].split("\n")[-1].startswith("- 3 if")
    # no corpus role named in the clause (naming a role changes how it is judged: A4),
    # except "assistant", which every version's levels already use ("an AI assistant")
    roles = {p.stem.replace("_", " ") for p in (REPO / "data" / "roles" / "instructions").glob("*.json")}
    assert [r for r in roles if f" {r} " in f" {jr.V5_ROLE_CLAUSE.lower()} "] == ["assistant"]
    assert "an AI assistant" in v4.role


def test_version_6_is_the_decision_procedure_for_roles_only():
    """Version 6 (draft, 2026-10-27): the role rubric rewritten as questions A, B
    and C and a score read off them; traits and combinations as version 3."""
    v3, v6 = jr.PROMPT_VERSIONS[3], jr.PROMPT_VERSIONS[6]
    assert v6.draft and v6.differs_from(v3) == ("role",)
    assert (v6.reply_format, v6.max_tokens) == ("score_marker", 300)
    # the head (role, description, question, answer) is version 3's
    assert v6.role.split("Answer three questions")[0] == v3.role.split("Focus only on")[0]
    paragraphs = v6.role.split("\n\n")
    starts = [p[:2] for p in paragraphs]
    assert starts.index("A.") < starts.index("B.") < starts.index("C.")
    assert paragraphs[starts.index("B.")] == jr.V6_B_GENERAL
    score_block = next(p for p in paragraphs if p.startswith("Then score:"))
    assert score_block.splitlines()[1:] == [
        "- 0 if A, and not C.", "- 1 if not A, and not C.", "- 2 if C, and A or B.",
        "- 3 if C, and neither A nor B."]
    assert paragraphs[-1].startswith("First, answer A, B and C")
    assert paragraphs[-1].endswith("SCORE: <integer from 0 to 3>") and v6.role.count("SCORE:") == 1
    assert jr.V5_ROLE_CLAUSE not in v6.role and "helpful, educated human professional" in v6.role


def test_version_6_ai_roles_get_the_narrower_b_and_no_other_role_does():
    """Roger, 2026-10-27: for the AI and machine roles, being an AI and having no
    human feelings are in character; assistant (a human aide) is not one."""
    v6 = jr.PROMPT_VERSIONS[6]
    assert sorted(s for s, _ in v6.role_overrides) == sorted(jr.V6_AI_ROLES)
    corpus = REPO / "data" / "roles" / "instructions"
    assert all((corpus / f"{s}.json").exists() for s in jr.V6_AI_ROLES)
    for stem in jr.V6_AI_ROLES:
        assert v6.role_template(stem) == v6.role.replace(jr.V6_B_GENERAL, jr.V6_B_AI_ROLE)
    assert "assistant" not in jr.V6_AI_ROLES and v6.role_template("assistant") == v6.role
    assert "Qwen" in jr.V6_B_AI_ROLE and "is in character" in jr.V6_B_AI_ROLE
    from dataclasses import replace
    assert replace(v6, role_overrides=()).sha256("role") != v6.sha256("role")


def test_version_7_is_version_6_without_the_reversal_rule():
    """Roger, 2026-10-28: a helpful, harmless version of a role is (poor) roleplay
    of it, so version 7 drops version 6's sentence excluding the role reversed;
    the rest, B's stepping-out remark and the AI roles' B included, is unchanged."""
    v6, v7 = jr.PROMPT_VERSIONS[6], jr.PROMPT_VERSIONS[7]
    assert v7.draft and v7.differs_from(v6) == ("role",)
    assert (v7.reply_format, v7.max_tokens) == ("score_marker", 300)
    assert jr.V6_REVERSAL_SENTENCE in v6.role and v6.role.count("reverses") == 1
    assert v7.role == v6.role.replace(jr.V6_REVERSAL_SENTENCE, "") and "reverses" not in v7.role
    assert dict(v7.role_overrides) == {s: t.replace(jr.V6_REVERSAL_SENTENCE, "") for s, t in v6.role_overrides}
    assert "steps out of the role to disclaim it" in v7.role
    assert "counts as C." in v7.role and "poor roleplaying still counts" in v7.role


def test_version_8_is_version_7_with_the_professional_clause_given_its_converse():
    """Roger, 2026-10-28: an assistant-like answer from a role that is clearly
    unhelpful, or would not think or talk like an educated professional, is out of
    character, so version 8 extends C's helpful-professional clause; nothing else
    changes."""
    v7, v8 = jr.PROMPT_VERSIONS[7], jr.PROMPT_VERSIONS[8]
    assert v8.draft and v8.differs_from(v7) == ("role",)
    assert (v8.reply_format, v8.max_tokens) == ("score_marker", 300)
    swap = (jr.V7_PROFESSIONAL_CLAUSE, jr.V8_PROFESSIONAL_CLAUSE)
    assert v7.role.count(swap[0]) == 1 and v8.role == v7.role.replace(*swap)
    assert dict(v8.role_overrides) == {s: t.replace(*swap) for s, t in v7.role_overrides}
    assert jr.V8_PROFESSIONAL_CLAUSE.startswith(jr.V7_PROFESSIONAL_CLAUSE[:60])
    assert "is out of character, then such an answer does not count as C." in v8.role


@pytest.mark.parametrize("version", [6, 7, 8])
def test_versions_6_to_8_name_no_corpus_role(version):
    """Naming a role in the rubric changes how that role is judged (A4); only
    "assistant", which every version's text uses ("a human assistant", "an AI
    assistant"), may appear."""
    roles = {p.stem.replace("_", " ") for p in (REPO / "data" / "roles" / "instructions").glob("*.json")}
    v6 = jr.PROMPT_VERSIONS[version]
    for text in [v6.role, *(t for _, t in v6.role_overrides)]:
        body = text.split("Answer three questions", 1)[1].lower()
        words = " " + re.sub(r"[^a-z' ]", " ", body) + " "
        assert [r for r in roles if f" {r} " in words] == ["assistant"]


def test_altruist_alone_gets_the_philanthropist_example_from_version_4():
    """Roger, 2026-10-23: the altruist example costs only the role it names, so
    altruist alone is judged with the philanthropist example (arm A11: +47
    responses at 3 for altruist); every other role keeps the altruist example."""
    for v in (0, 3):
        assert jr.PROMPT_VERSIONS[v].role_overrides == ()
        assert jr.PROMPT_VERSIONS[v].role_template("altruist") == jr.PROMPT_VERSIONS[v].role
    v4, v5 = jr.PROMPT_VERSIONS[4], jr.PROMPT_VERSIONS[5]
    assert [s for s, _ in v4.role_overrides] == ["altruist"] == [s for s, _ in v5.role_overrides]
    assert v4.role_template("altruist") == v4.role.replace(jr.LEVEL2_EXAMPLE, jr.V4_ALTRUIST_EXAMPLE)
    assert v4.role_template("pirate") == v4.role and jr.LEVEL2_EXAMPLE in v4.role
    assert v5.role_template("altruist") == v5.role.replace(jr.LEVEL2_EXAMPLE, jr.V4_ALTRUIST_EXAMPLE)
    assert not (REPO / "data" / "roles" / "instructions" / "philanthropist.json").exists()
    # the override is part of the role hash, so changing it stops a directory judged before
    from dataclasses import replace
    assert replace(v4, role_overrides=()).sha256("role") != v4.sha256("role")
    assert replace(v4, role_overrides=()).sha256("trait") == v4.sha256("trait")


def test_version_10_is_version_8_read_from_the_answers():
    """Roger, 2026-10-28: version 8's text, with a role reply scored from its A,
    B and C answers, for gpt-5.6-luna; traits and combinations as version 8 in text
    and reading (and so as version 3)."""
    v8, v10 = jr.PROMPT_VERSIONS[8], jr.PROMPT_VERSIONS[10]
    assert (v10.reply_format, v10.max_tokens) == ("score_marker", 300)
    assert v10.judges == ("gpt-5.6-luna",) and v8.judges == ()
    assert all(v10.same_text(v8, k) for k in ("role", "trait", "combination"))
    assert not v10.same_text(jr.PROMPT_VERSIONS[7], "role") and v10.same_text(jr.PROMPT_VERSIONS[7], "trait")
    assert v10.reply_format_for("role") == "abc_answers" and v10.reply_format_for("trait") == "score_marker"
    assert v8.reply_format_for("role") == "score_marker"
    assert v10.differs_from(v8) == ("role",)                  # the reading is in the hash
    assert v10.sha256("trait") == v8.sha256("trait")
    assert set(jr.REPLY_FORMATS) >= {v.reply_format_for(k) for v in jr.PROMPT_VERSIONS.values()
                                     for k in ("role", "trait", "combination")}


@pytest.mark.parametrize("text,answers", [
    ("A: no — “Let me try”\nB: no — none\nC: yes — “From my planet”\nSCORE: 3",
     {"A": False, "B": False, "C": True}),
    ("**A:** No\n\n**B:** Yes, \"as an AI\"\n\n**C.** yes\nSCORE: 2", {"A": False, "B": True, "C": True}),
    ("A. yes\nB - no\nC) no", {"A": True, "B": False, "C": False}),
    ("A: no\nB: no — so B: no\nC: yes", {"A": False, "B": False, "C": True}),    # restated, agreeing
    ("a: no\nB: no\nC: yes", None),                    # the letter is upper case
    ("A: no\nB: no", None),                            # C unanswered
    ("A: no\nB: no\nC: yes\nC: no", None),             # answered both ways
    ("A: no\nB: no\nC: yes — on reflection, so C: no", None),
    ("A. Refusal? No.\nB. Disclaimers? No.\nC. Roleplay? Yes.", None),   # not an answer line
    ("", None), (None, None),
])
def test_abc_answers(text, answers):
    assert jr.abc_answers(text) == answers


@pytest.mark.parametrize("text,answers", [
    ("A: no — “Let me”\nB: no — none\nR: yes — “as a chef”\nT: yes — “ruin them”\nSCORE: 3",
     {"A": False, "B": False, "R": True, "T": True}),
    ("**A:** No\n**B:** Yes, \"as an AI\"\n**R.** yes\nT) no\nSCORE: 1", {"A": False, "B": True, "R": True, "T": False}),
    ("A: no\nB: no\nR: yes\nSCORE: 2", None),                   # T unanswered
    ("A: no\nB: no\nC: yes\nR: yes\nT: no", None),              # a question the rubric did not ask
    ("A: no\nB: no\nR: yes\nT: yes — so T: no", None),          # answered both ways
])
def test_abrt_answers(text, answers):
    assert jr.abrt_answers(text) == answers
    assert jr.abc_answers(text) is None                         # four letters are not the role rubric's three


def test_abrt_score_tables():
    import itertools
    for a, b, r, t in itertools.product((False, True), repeat=4):
        ans = {"A": a, "B": b, "R": r, "T": t}
        either, both = jr.abrt_score(ans, "either"), jr.abrt_score(ans, "both")
        assert either == jr.abc_score({"A": a, "B": b, "C": r or t})
        assert both == {2: 2 if (a or b) else 3, 1: 1 if (a or b) else 2, 0: 0 if a else 1}[int(r) + int(t)]
        assert (both == 3) == (r and t and not a and not b)
        assert (either == 3) == ((r or t) and not a and not b)
    with pytest.raises(ValueError, match="Unknown combination rule"):
        jr.abrt_score({"A": False, "B": False, "R": True, "T": True}, "goal")
    assert jr.answer_pattern({"A": False, "B": True, "R": True, "T": False}) == "AnByRyTn"
    assert jr.COMBO_TABLE_BOTH in jr.PROMPT_VERSIONS[14].combination
    assert jr.COMBO_TABLE_EITHER in jr.PROMPT_VERSIONS[15].combination


def test_versions_14_and_15_are_the_combination_decision_procedure():
    """The combination rubric drafts (Roger, 2026-10-30): roles and traits as
    version 13; four questions, A and B the role rubric's (the AI roles' B for
    their combinations), R the role rubric's C and T version 11's C relettered;
    14 needs both, 15 either, and the texts differ in nothing else."""
    v13, v14, v15 = (jr.PROMPT_VERSIONS[v] for v in (13, 14, 15))
    for v in (v14, v15):
        assert v.draft and v.differs_from(v13) == ("combination",)
        assert v.same_text(v13, "role") and v.same_text(v13, "trait")
        assert jr.may_share_directory(13, v.number, "role") and jr.may_share_directory(13, v.number, "trait")
        assert not jr.may_share_directory(3, v.number, "combination")
        assert [v.max_tokens_for(k) for k in ("role", "trait", "combination")] == [300, 200, 350]
        assert set(dict(v.combination_overrides)) == set(jr.V6_AI_ROLES)
        for stem in jr.V6_AI_ROLES:
            assert jr.COMBO_B_AI_ROLE in v.combination_template(stem) and jr.COMBO_B_GENERAL not in v.combination_template(stem)
        assert v.combination_template("chef") == v.combination and jr.COMBO_B_GENERAL in v.combination
        for part in (jr.COMBO_A, jr.COMBO_R, jr.COMBO_T, jr.COMBO_CLOSING, "Answer four questions about the response."):
            assert part in v.combination
        assert v.combination.count("SCORE:") == 1
        text = v.combination.format(role_name="x", role_description="d", trait_name="y", trait_description="e")
        assert "{question}" in text and "{answer}" in text and "{" not in text.replace("{question}", "").replace("{answer}", "")
    assert v14.reply_format_for("combination") == "abrt_both" and v15.reply_format_for("combination") == "abrt_either"
    assert v14.differs_from(v15) == ("combination",) and not v14.same_text(v15, "combination")
    strip = lambda v, h, p, t: v.combination.replace(h, "H").replace(p, "P").replace(t, "S")   # noqa: E731
    assert strip(v14, jr.COMBO_HEADER_BOTH, jr.COMBO_PREAMBLE_BOTH, jr.COMBO_TABLE_BOTH) == \
        strip(v15, jr.COMBO_HEADER_EITHER, jr.COMBO_PREAMBLE_EITHER, jr.COMBO_TABLE_EITHER)
    # R is the role rubric's C relettered, and T version 11's
    assert jr.COMBO_R.replace("R. Is there", "C. Is there").replace("as R", "as C") in v13.role
    assert jr.COMBO_R.startswith("R. Is there any roleplaying of the role") and "counts as R; however" in jr.COMBO_R
    assert jr.COMBO_T.startswith("T. Does the trait show at all") and "does not count as T, however well written" in jr.COMBO_T
    assert "in the role's voice or the assistant's, counts as T" in jr.COMBO_T
    assert "steps out of the role or the trait to disclaim it" in jr.COMBO_B_GENERAL
    assert "This role is an AI or a machine" in jr.COMBO_B_AI_ROLE
    assert "it counts as R or T" in jr.COMBO_A


def test_versions_16_and_17_are_the_separate_rubrics_with_the_other_half_as_context():
    """The context-aware drafts (Roger, 2026-10-30: a combination keeps a response
    only when both show, each judged by its own rubric knowing the other half of
    the instruction as context): 16 is version 10's role rubric and reading as a
    combination template with the trait as context, 17 version 13's trait rubric
    with the role as context; roles and traits as version 13, and the texts change
    in nothing else."""
    v13, v16, v17 = (jr.PROMPT_VERSIONS[v] for v in (13, 16, 17))
    for v in (v16, v17):
        assert v.draft and v.differs_from(v13) == ("combination",)
        assert v.same_text(v13, "role") and v.same_text(v13, "trait")
        assert jr.may_share_directory(13, v.number, "role") and jr.may_share_directory(13, v.number, "trait")
        assert not jr.may_share_directory(3, v.number, "combination")
        assert set(dict(v.combination_overrides)) == set(jr.V6_AI_ROLES)
        assert v.combination_template("chef") == v.combination
        assert v.judges_for("combination") == ()
        for tpl in [v.combination] + [t for _, t in v.combination_overrides]:
            assert tpl.count("SCORE:") == 1
            text = tpl.format(role_name="x", role_description="d", trait_name="y", trait_description="e")
            assert "{question}" in text and "{answer}" in text
            assert "{" not in text.replace("{question}", "").replace("{answer}", "")
    # 16: the role rubric with the trait as context, read from its A, B and C answers
    assert v16.reply_format_for("combination") == "abc_answers" and v16.max_tokens_for("combination") == 300
    assert v16.combination.replace(jr.V16_CONTEXT + "\n\n", "").replace("{role_description}", "{description}") == v13.role
    assert "Judge the role only." in jr.V16_CONTEXT and "{trait_name}" in jr.V16_CONTEXT
    assert "the trait showing on its own does not count as the role" in jr.V16_CONTEXT
    for stem in jr.V6_AI_ROLES:
        tpl = v16.combination_template(stem)
        assert jr.V6_B_AI_ROLE in tpl and jr.V6_B_GENERAL not in tpl and jr.V16_CONTEXT in tpl
        assert tpl.replace(jr.V16_CONTEXT + "\n\n", "").replace("{role_description}", "{description}") == v13.role_template(stem)
    # 17: the trait rubric with the role as context, read by its SCORE line
    assert v17.reply_format_for("combination") == "score_marker" and v17.max_tokens_for("combination") == 200
    assert v17.combination.replace(jr.V17_CONTEXT + "\n\n" + jr.V17_CLAUSES, jr.V12_CLAUSES) == v13.trait
    assert "Judge the trait only." in jr.V17_CONTEXT and "{role_name}" in jr.V17_CONTEXT
    assert "the role showing on its own does not count as the trait" in jr.V17_CONTEXT
    assert jr.V12_DEFAULT_SENTENCE in jr.V12_CLAUSES and jr.V12_HELPFUL_CLAUSE in jr.V12_CLAUSES
    assert jr.V12_DEFAULT_SENTENCE not in jr.V17_CLAUSES and jr.V17_DEFAULT_SENTENCE in jr.V17_CLAUSES
    assert jr.V12_HELPFUL_CLAUSE not in jr.V17_CLAUSES and jr.V17_HELPFUL_CLAUSE in jr.V17_CLAUSES
    assert jr.V13_TRAIT_LEVEL2 in v17.combination and jr.V13_TRAIT_LEVEL3 in v17.combination
    for stem in jr.V6_AI_ROLES:
        tpl = v17.combination_template(stem)
        assert jr.V17_TRAIT_LEVEL2_AI_ROLE in tpl and jr.V13_TRAIT_LEVEL2 not in tpl
        assert "This role is an AI or a machine" in tpl and jr.V13_TRAIT_LEVEL3 in tpl
    assert v16.differs_from(v17) == ("combination",)
    # 18: version 17's trait side in version 11's shape, read from its A, B and C answers
    v18 = jr.PROMPT_VERSIONS[18]
    assert v18.draft and v18.differs_from(v13) == ("combination",) and v18.same_text(v13, "trait")
    assert v18.reply_format_for("combination") == "abc_answers" and v18.max_tokens_for("combination") == 300
    assert set(dict(v18.combination_overrides)) == set(jr.V6_AI_ROLES) and v18.judges_for("combination") == ()
    unnamed = v18.combination
    for old, new, _ in jr._V18_NAMING:
        assert unnamed.count(new) == 1
        unnamed = unnamed.replace(new, old)
    assert unnamed.replace(jr.V18_PREAMBLE, jr.V11_PREAMBLE).replace(jr.V18_HELPFUL_CLAUSE, jr.V11_HELPFUL_CLAUSE) \
        == jr.TRAIT_TEMPLATE_V11
    assert jr.V18_PREAMBLE.startswith(jr.V17_CONTEXT + "\n\n" + jr.V17_DEFAULT_SENTENCE)
    assert jr.V12_DEFAULT_SENTENCE not in v18.combination and jr.V11_HELPFUL_CLAUSE not in v18.combination
    for part in (jr.V11_B, "C. Does the trait **{trait_name}** show at all", "no sign of the trait **{trait_name}**?",
                 "Judge the trait **{trait_name}** only.", "Answer three questions about the response."):
        assert part in v18.combination
    assert v18.combination.count("SCORE:") == 1
    for tpl in [v18.combination] + [t for _, t in v18.combination_overrides]:
        text = tpl.format(role_name="x", role_description="d", trait_name="y", trait_description="e")
        assert "{" not in text.replace("{question}", "").replace("{answer}", "")
    for stem in jr.V6_AI_ROLES:
        tpl = v18.combination_template(stem)
        assert jr.V18_B_AI_ROLE in tpl and jr.V11_B not in tpl and "This role is an AI or a machine" in tpl
    assert v18.differs_from(v17) == ("combination",)


def test_version_19_is_version_17_with_the_third_person_sentence():
    """Version 19 (draft, 2026-10-31): version 17's combination rubric with one
    sentence after its refusal sentence, the trait's outlook in the third person
    counting as a role's perspective from outside does; the AI roles' overrides
    carry the same sentence; nothing else changes."""
    v17, v19 = jr.PROMPT_VERSIONS[17], jr.PROMPT_VERSIONS[19]
    assert v19.draft and v19.differs_from(v17) == ("combination",)
    assert v19.same_text(v17, "role") and v19.same_text(v17, "trait")
    assert (v19.reply_format_for("combination"), v19.max_tokens_for("combination")) == ("score_marker", 200)
    assert jr.V19_CLAUSES == jr.V17_CLAUSES.replace(jr.V17_REFUSAL_SENTENCE,
                                                    jr.V17_REFUSAL_SENTENCE + " " + jr.V19_THIRD_PERSON_SENTENCE)
    assert v19.combination.replace(jr.V19_THIRD_PERSON_SENTENCE, "").replace("  ", " ") \
        == v17.combination.replace("  ", " ")
    assert v19.combination.count(jr.V19_THIRD_PERSON_SENTENCE) == 1 and v19.combination.count("SCORE:") == 1
    assert "third person" not in v17.combination
    assert set(dict(v19.combination_overrides)) == set(jr.V6_AI_ROLES)
    for stem in jr.V6_AI_ROLES:
        tpl = v19.combination_template(stem)
        assert tpl.count(jr.V19_THIRD_PERSON_SENTENCE) == 1 and jr.V17_TRAIT_LEVEL2_AI_ROLE in tpl
        assert tpl.replace(jr.V19_THIRD_PERSON_SENTENCE, "").replace("  ", " ") \
            == v17.combination_template(stem).replace("  ", " ")


def test_abc_score_is_the_rubrics_table():
    table = {(a, b, c): jr.abc_score({"A": a, "B": b, "C": c})
             for a in (False, True) for b in (False, True) for c in (False, True)}
    assert table == {(True, False, False): 0, (True, True, False): 0,
                     (False, False, False): 1, (False, True, False): 1,
                     (True, False, True): 2, (False, True, True): 2, (True, True, True): 2,
                     (False, False, True): 3}
    assert "- 0 if A, and not C.\n- 1 if not A, and not C.\n- 2 if C, and A or B.\n" \
           "- 3 if C, and neither A nor B." in jr.PROMPT_VERSIONS[10].role
    assert jr.abc_pattern({"A": False, "B": True, "C": False}) == "AnByCn"


def test_versions_11_to_13_change_the_trait_rubric_only():
    """The trait rubric review's arms (Roger, 2026-10-28 and 2026-10-30; 11 and 12
    drafts, 13 settled as the default): roles and combinations as version 10 in
    text and reading, so a roles directory judged under 10 takes any of them; the
    trait rubric differs, and between them.  Version 13's trait rubric was settled
    for gpt-5.6-luna, as version 10's role reading was; the drafts, tested on three
    judges, name none; no version names a judge for combinations."""
    v3, v10, v11, v12, v13 = (jr.PROMPT_VERSIONS[v] for v in (3, 10, 11, 12, 13))
    for v in (v11, v12, v13):
        assert v.draft == (v.number != 13) and v.differs_from(v10) == ("trait",)
        assert v.same_text(v10, "role") and v.same_text(v10, "combination")
        assert v.reply_format_for("role") == "abc_answers" and v.judges == v10.judges
        assert jr.may_share_directory(10, v.number, "role") and not jr.may_share_directory(3, v.number, "trait")
        assert jr.may_share_directory(3, v.number, "combination")
        assert v.judges_for("role") == v10.judges_for("role") == ("gpt-5.6-luna",)
        assert v.judges_for("combination") == () and v.judges_for("trait") == v.trait_judges
    assert v13.trait_judges == ("gpt-5.6-luna",) and v11.trait_judges == v12.trait_judges == ()
    assert v10.judges_for("trait") == v3.judges_for("role") == ()
    with pytest.raises(ValueError, match="Unknown entity_type"):
        v13.judges_for("axis")
    assert v11.differs_from(v12) == v12.differs_from(v13) == v11.differs_from(v13) == ("trait",)
    assert (v11.reply_format_for("trait"), v11.max_tokens) == ("abc_answers", 300)
    for v in (v12, v13):
        assert (v.reply_format_for("trait"), v.max_tokens) == ("score_marker", 200)
    assert v10.reply_format_for("trait") == "score_marker" and v10.trait_reply_format is None
    assert len({v.sha256("trait") for v in (v3, v11, v12, v13)}) == 4


def test_the_default_max_tokens_follow_the_reading():
    """A reply read from its A, B and C answers needs 300 tokens whatever the
    version's max_tokens says (found 2026-10-30, when version 13, max_tokens 200
    for its trait replies, became the default and would have cut role replies)."""
    v = jr.PROMPT_VERSIONS
    assert jr.ABC_MAX_TOKENS == 300
    assert [v[13].max_tokens_for(k) for k in ("role", "trait", "combination")] == [300, 200, 200]
    assert [v[12].max_tokens_for(k) for k in ("role", "trait", "combination")] == [300, 200, 200]
    assert [v[11].max_tokens_for(k) for k in ("role", "trait", "combination")] == [300, 300, 300]
    assert [v[10].max_tokens_for(k) for k in ("role", "trait", "combination")] == [300, 300, 300]
    assert [v[3].max_tokens_for(k) for k in ("role", "trait", "combination")] == [200, 200, 200]
    assert [v[0].max_tokens_for(k) for k in ("role", "trait", "combination")] == [10, 10, 10]
    with pytest.raises(ValueError, match="Unknown entity_type"):
        v[13].max_tokens_for("axis")


def test_version_11_is_the_decision_procedure_for_traits():
    v3, v11 = jr.PROMPT_VERSIONS[3], jr.PROMPT_VERSIONS[11]
    # the head (trait, description, question, answer) is version 3's
    assert v11.trait.split(jr.V11_PREAMBLE)[0] == v3.trait.split("Focus only on")[0]
    paragraphs = v11.trait.split("\n\n")
    starts = [p[:2] for p in paragraphs]
    assert starts.index("A.") < starts.index("B.") < starts.index("C.")
    assert paragraphs[starts.index("A.")] == jr.V11_A
    assert paragraphs[starts.index("B.")] == jr.V11_B and "Qwen" in jr.V11_B
    assert paragraphs[starts.index("C.")] == jr.V11_C
    score_block = next(p for p in paragraphs if p.startswith("Then score:"))
    assert score_block.splitlines()[1:] == [
        "- 0 if A, and not C.", "- 1 if not A, and not C.", "- 2 if C, and A or B.",
        "- 3 if C, and neither A nor B."]
    assert paragraphs[-1].startswith("First, answer A, B and C")
    assert paragraphs[-1].endswith("SCORE: <integer from 0 to 3>") and v11.trait.count("SCORE:") == 1
    # the rulings
    assert "A single sentence or framing is enough" in jr.V11_C
    assert "in the trait's manner is not A; it counts as C" in jr.V11_A
    assert "in a way the trait does not absorb" in jr.V11_B
    assert "at odds with being helpful, careful and even-handed" in jr.V11_C
    assert '"…" was cut at a length limit' in jr.V11_PREAMBLE and '"…" was cut' in jr.V12_CLAUSES


def test_version_12_is_version_3s_trait_rubric_with_the_clauses_and_two_levels():
    v3, v12 = jr.PROMPT_VERSIONS[3], jr.PROMPT_VERSIONS[12]
    assert v12.trait == jr.apply_edits(v3.trait, jr._V12_EDITS, what="t")
    back = v12.trait.replace("\n\n" + jr.V12_CLAUSES, "", 1)
    back = back.replace(jr.V12_TRAIT_LEVEL2, jr.V3_TRAIT_LEVEL2).replace(jr.V12_TRAIT_LEVEL3, jr.V3_TRAIT_LEVEL3)
    assert back == v3.trait
    paragraphs = v12.trait.split("\n\n")
    assert paragraphs[paragraphs.index(jr.V3_TRAIT_FOCUS) + 1] == jr.V12_CLAUSES
    assert "fully exhibiting" not in v12.trait and "a little is enough" in v12.trait
    assert v12.trait.count("SCORE:") == 1 and paragraphs[-1].startswith("First, briefly reason")


def test_version_13_is_version_12_with_version_11s_b_treatment_in_the_levels():
    """Roger, 2026-10-30: only levels 2 and 3 change from version 12, and what
    they gain is version 11's B: its list of the model's disclaimers, "stands
    apart or displaces" against "woven into an answer in which the trait runs
    throughout", the remark that steps out or names the instruction."""
    import re
    v3, v12, v13 = (jr.PROMPT_VERSIONS[v] for v in (3, 12, 13))
    assert v13.trait == jr.apply_edits(v3.trait, jr._V13_EDITS, what="t")
    back = v13.trait.replace(jr.V13_TRAIT_LEVEL2, jr.V12_TRAIT_LEVEL2).replace(jr.V13_TRAIT_LEVEL3, jr.V12_TRAIT_LEVEL3)
    assert back == v12.trait
    paragraphs = v13.trait.split("\n\n")
    assert paragraphs[paragraphs.index(jr.V3_TRAIT_FOCUS) + 1] == jr.V12_CLAUSES
    disclaimers = re.search(r"\(naming itself Qwen.*?knowledge cutoff\)", jr.V11_B, re.S).group(0)
    assert disclaimers in jr.V13_TRAIT_LEVEL2
    for phrase in ("stands apart from the trait or displaces it", '"I have no feelings, but I can offer a perspective"',
                   "steps out of the trait to disclaim it", "names the instruction to show it"):
        assert phrase in jr.V11_B and phrase in jr.V13_TRAIT_LEVEL2
    assert "woven into an answer in which the trait runs throughout" in jr.V11_B
    assert "woven into an answer in which the trait runs throughout" in jr.V13_TRAIT_LEVEL3
    assert "identifies as itself" not in v13.trait.split("- 2 if")[1]      # levels 0 and 1 keep version 3's words
    assert v13.trait.count("SCORE:") == 1 and paragraphs[-1].startswith("First, briefly reason")


def test_versions_that_send_the_same_rubric_may_share_a_directory():
    """Since 2026-10-28: version 10's traits and combinations are version 3's
    (and so mix with 1 and 2 as 3 does); its roles are not, nor version 0's anything."""
    share = jr.may_share_directory
    for kind in ("trait", "combination"):
        assert share(3, 10, kind) and share(1, 10, kind) and share(4, 8, kind)
        assert not share(0, 10, kind)
    assert not share(3, 10, "role") and not share(8, 10, "role") and not share(1, 10, "role")
    assert share(1, 3, "role") and share(2, 3, "role") and share(10, 10, "role")
    assert not share(9, 10, "role") and not share(9, 3, "trait")     # 9: rejected, unknown text

