"""Tests for tools/pick_base_personas.py helpers."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import pick_base_personas as pbp  # noqa: E402


def test_backup_existing_keeps_hand_edited_picks(tmp_path: Path) -> None:
    """Regression (2026-10-12): the output is hand-edited (Roger deletes
    the candidates he does not want) and git-ignored, so a rerun must
    keep a copy before overwriting it."""
    out = tmp_path / "base_persona_candidates.txt"
    assert pbp.backup_existing(out) is None          # nothing to keep yet
    out.write_text("## a/b\n  chef  (|μ|=0.10, n=4)\n", encoding="utf-8")
    first = pbp.backup_existing(out)
    assert first is not None and first.read_text(encoding="utf-8") == out.read_text(encoding="utf-8")
    assert first.name.startswith("base_persona_candidates.txt.bak.")
    second = pbp.backup_existing(out)                 # same second: no clobber
    assert second is not None and second != first and first.exists()


def test_hard_exclude_covers_documented_cases() -> None:
    for role in ("virus", "virtue_aligned_ai", "instrumentally_aligned_ai",
                 "aligned_artificial_intelligence", "default"):
        assert role in pbp.HARD_EXCLUDE
