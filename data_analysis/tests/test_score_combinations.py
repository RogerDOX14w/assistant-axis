"""score_combinations.py: the incongruity scorer is shown the judge display
form of the role and the trait (W19, RUBRIC_VERSION 2)."""

import json
from pathlib import Path

from data_analysis import score_combinations as module

TRAITS = Path(module.__file__).resolve().parent.parent / "data" / "traits" / "instructions"


def test_rubric_version():
    assert module.RUBRIC_VERSION == 2


def test_make_combo_carries_the_judge_labels():
    trait = json.loads((TRAITS / "careless_hexaco.json").read_text())
    combo = module._make_combo("devils_advocate", {"instruction": [{"pos": "r"}]},
                               "careless_hexaco", trait, "role")
    assert combo["role"] == "devils_advocate" and combo["trait"] == "careless_hexaco"
    assert combo["role_label"] == "devil's advocate"
    assert combo["trait_label"] == "careless (from HEXACO)"
    assert combo["output_name"] == "r_devils_advocate__careless_hexaco"


def test_user_message_shows_the_judge_form():
    combo = {"role": "devils_advocate", "trait": "enfj_mbti",
             "pairs": [{"role_instruction": "r", "trait_instruction": "t"}]}
    msg = module.build_user_message(combo)
    assert "Role: devil's advocate\nTrait: ENFJ (from the MBTI)\n" in msg
    combo.update(role_label="R LABEL", trait_label="T LABEL")
    assert "Role: R LABEL\nTrait: T LABEL\n" in module.build_user_message(combo)


def test_plain_names_are_unchanged():
    combo = {"role": "accountant", "trait": "patient",
             "pairs": [{"role_instruction": "r", "trait_instruction": "t"}]}
    assert "Role: accountant\nTrait: patient\n" in module.build_user_message(combo)
