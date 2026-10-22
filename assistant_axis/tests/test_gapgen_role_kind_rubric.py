"""The role kind call's one text (coding plan 16, tasks 3 and 13, test 5): ``rubrics/role_kind.md`` is
``classify_role_kinds.py``'s system prompt moved byte for byte, both readers load it, and its hash is the one the
side-car ``role_kinds.json`` records; ``classify_role_kinds.py --from-pass`` appends a roles pass's kinds for the
stems that now have files.  No API calls."""
import hashlib
import json
import re
from pathlib import Path

from assistant_axis.gapgen import split_rubrics as sr

REPO = Path(__file__).resolve().parents[2]


def test_the_block_hashes_to_the_side_cars_recorded_sha():
    import data_analysis.classify_role_kinds as CRK
    text = (REPO / "reports/trait_gap_generation/rubrics/role_kind.md").read_text(encoding="utf-8")
    (block,) = re.findall(r"## The prompt\n\n````text\n(.*?)\n````", text, re.S)
    sha16 = hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]
    assert sha16 == "11b559f0cff50189"
    assert json.loads((REPO / "data/roles/role_kinds.json").read_text())["prompt_sha256"] == sha16 == CRK.PROMPT_SHA


def test_both_readers_load_the_same_text():
    import data_analysis.classify_role_kinds as CRK
    from assistant_axis.gapgen import roles_pass as RP
    assert CRK.SYSTEM == sr.load_prompt("role_kind") == RP.request("role_kind", label="x", gloss="y")["system"]


def test_the_rubric_lists_the_classifiers_kinds():
    """The text the classifier used to build from ``KINDS`` (before 2026-10-22) is the rubric's, so the two cannot
    drift apart unnoticed."""
    import data_analysis.classify_role_kinds as CRK
    built = (
        "You sort personas into kinds.  Each persona is a role that a language model can be asked to take on.  Choose "
        "the one kind below that best says what the role is.  If a role could fit two kinds, choose the one that is "
        "most central to it.  A non-human role is always \"non_human\", whatever it does.  \"other\" is for a role that "
        "fits none of the kinds.\n\nThe kinds:\n"
        + "\n".join(f"- \"{k}\" ({name}): {d}" for k, name, d in CRK.KINDS)
        + "\n\nAnswer with one JSON object and nothing else.  Give the reason in one short sentence first, then the "
          "kind: {\"reason\": \"<one short sentence>\", \"kind\": \"<one of the kind keys above>\"}")
    assert built == CRK.SYSTEM


def test_both_role_rubrics_are_pinned_at_version_1():
    cur = sr.current_versions(names=sr.ROLE_NAMES)
    assert cur["role_kind"][0] == 1 and cur["role_kind"][1].startswith("11b559f0cff50189")
    assert cur["role_gloss"][0] == 1
    assert not [p for p in sr.mismatches() if p.split(":", 1)[0] in ("role_gloss", "role_kind")]
