"""Walk-through A3 (2026-10-12): the goal lists come in two generations,
like the pair lists.

* ``data/goal_roles_and_traits_v1.json`` is the April 2026 goal file
  (cac76b65, 2026-04-06, unchanged until 3f6de81e on 2026-09-28), byte-exact
  from git: the one the May 8slot extraction used and the record behind the
  ``_v1`` pair lists.  Not the version just before W15 (87d84fc^): that one
  already carries the September renames and drops, so it names stems the
  8slot data has no vector for (coordinator, 2026-10-12, option (b)).
* The current pair lists' ``goal_type`` is derived from the current
  (W15) goal file by ``tools/build_pair_lists.py``; the ``_v1`` lists'
  from the ``_v1`` file.
* 8slot-era scripts that read the goal lists default to the ``_v1`` file.

The pair lists live under the git-ignored ``roger/``; those checks skip
when the files are absent (a fresh clone).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from tools.build_pair_lists import build_lists

REPO = Path(__file__).resolve().parents[2]
GOAL = REPO / "data" / "goal_roles_and_traits.json"
GOAL_V1 = REPO / "data" / "goal_roles_and_traits_v1.json"
EXP = REPO / "roger" / "axis_judge_experiments"
# sha256 of `git show cac76b65:data/goal_roles_and_traits.json`.
GOAL_V1_SHA256 = "4db5fa942ef290001f810fc64b805a2f747115e3baf0480c9c5f936dabd45486"


def test_v1_goal_file_is_the_april_file():
    assert hashlib.sha256(GOAL_V1.read_bytes()).hexdigest() == GOAL_V1_SHA256
    try:
        old = subprocess.run(
            ["git", "show", "cac76b65:data/goal_roles_and_traits.json"],
            cwd=REPO, capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover -- no git history
        pytest.skip("git history not available")
    assert old == GOAL_V1.read_bytes()


def test_v1_goal_file_names_only_stems_with_8slot_vectors_where_the_record_does():
    """The point of taking the April file: it uses the old stems the 8slot
    data and the _v1 pair lists use (aligned_artificial_intelligence, not
    instrumentally_aligned_ai)."""
    v1 = json.loads(GOAL_V1.read_text())
    assert "aligned_artificial_intelligence" in v1["roles"]["goal"]
    assert "instrumentally_aligned_ai" not in v1["roles"]["goal"]


def _lists(name):
    p = EXP / name
    if not p.exists():
        pytest.skip(f"{name} not present (roger/ is git-ignored)")
    return json.loads(p.read_text())


@pytest.mark.parametrize("clean, gng, goal", [
    ("pair_list_clean.json", "pair_list_goalnongoal.json", GOAL),
    ("pair_list_clean_v1.json", "pair_list_goalnongoal_v1.json", GOAL_V1),
])
def test_pair_list_goal_type_matches_its_goal_file(clean, gng, goal):
    recorded_clean, recorded_gng = _lists(clean), _lists(gng)
    src = [{k: v for k, v in e.items() if k != "goal_type"} for e in recorded_clean]
    built_clean, built_gng, _ = build_lists(src, json.loads(goal.read_text()))
    assert built_clean == recorded_clean
    if clean == "pair_list_clean.json":
        # The current goalnongoal list is exactly the builder's output.
        assert built_gng == recorded_gng
    else:
        # The _v1 records carry pairs the current corpus dropped; their
        # goal_type still agrees with the _v1 goal file.
        lk = json.loads(goal.read_text())
        rebuilt, _, _ = build_lists(
            [{k: v for k, v in e.items() if k != "goal_type"} for e in recorded_gng], lk)
        assert [e["goal_type"] for e in rebuilt] == [e["goal_type"] for e in recorded_gng]


def test_ca1_plane_defaults_to_the_v1_goal_file(monkeypatch):
    import sys
    from results_analysis.canonical_angles.plots import ca1_plane_pre_post_shear as m
    monkeypatch.setattr(sys, "argv", ["x", "--kind", "r", "--output", "o.png"])
    assert m.parse_args().goal_list == "data/goal_roles_and_traits_v1.json"
