"""Tests for tools/mark_rubric_equivalent.py (the CLI; the registry
itself is covered in assistant_axis/tests)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from assistant_axis import rubric_equivalence as eq  # noqa: E402
from tools import mark_rubric_equivalent as mre  # noqa: E402


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    r = tmp_path / "fake_repo"
    r.mkdir()
    (r / ".git").mkdir()
    monkeypatch.setattr(eq, "_repo_root_default", lambda: r)
    return r


@pytest.mark.parametrize("flag", [
    "--modes", "--axes", "--except-axes", "--entity-ids", "--except-entity-ids",
])
def test_scope_flag_without_values_is_refused(repo: Path, flag: str) -> None:
    """Regression (2026-10-12): ``nargs="*"`` turned a scope flag given no
    values into ``[]``, which the registry stores as a wildcard; an
    allow-list meant to name a few entities declared the bump equivalent
    for everything."""
    with pytest.raises(SystemExit, match="given with no values"):
        mre.main(["--from", "v3", "--to", "v4", "--reason", "r", flag])
    assert eq.load_registry(repo_root=repo) == []


def test_scoped_edge_is_recorded_with_its_scope(repo: Path) -> None:
    assert mre.main([
        "--from", "v3", "--to", "v4", "--reason", "only two entities",
        "--modes", "descriptions", "--entity-ids", "patient|R", "stoic|T",
    ]) == 0
    (edge,) = eq.load_registry(repo_root=repo)
    assert edge.modes == ("descriptions",)
    assert edge.entity_ids == ("patient|R", "stoic|T")
    assert edge.axes is None


def test_unscoped_edge_still_allowed_when_no_scope_flag_given(repo: Path) -> None:
    assert mre.main(["--from", "v3", "--to", "v4", "--reason", "global"]) == 0
    (edge,) = eq.load_registry(repo_root=repo)
    assert edge.modes is None and edge.axes is None and edge.entity_ids is None
