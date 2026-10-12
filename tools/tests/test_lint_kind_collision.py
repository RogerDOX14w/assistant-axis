"""Tests for tools/lint_kind_collision.py."""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import lint_kind_collision as lk  # noqa: E402


def _lint(tmp_path: Path, src: str, name: str = "mod.py") -> list:
    p = tmp_path / name
    p.write_text(textwrap.dedent(src), encoding="utf-8")
    return lk.lint_file(p)


def test_tuple_loop_with_bare_key_is_flagged(tmp_path: Path) -> None:
    f = _lint(tmp_path, """
        merged = {}
        for kind in ("traits", "roles"):
            for name in names(kind):
                merged[name] = 1
    """)
    assert [x.lineno for x in f] == [5]


def test_list_loop_and_augmented_assignment_are_flagged(tmp_path: Path) -> None:
    """2026-10-12: the list form of the loop and ``+=`` were not seen."""
    f = _lint(tmp_path, """
        counts = {}
        for kind in ["roles", "traits"]:
            for stem in stems(kind):
                counts[stem] += 1
                counts[stem]: int = 0
    """)
    assert sorted(x.lineno for x in f) == [5, 6]


def test_entity_id_key_and_noqa_are_quiet(tmp_path: Path) -> None:
    f = _lint(tmp_path, """
        merged = {}
        for kind in ("traits", "roles"):
            for name in names(kind):
                merged[entity_id(name, kind)] = 1
                other[name] = 2  # noqa: kind-collision
    """)
    assert f == []


def test_each_finding_reported_once(tmp_path: Path) -> None:
    f = _lint(tmp_path, """
        for kind in ("traits", "roles"):
            for name in names(kind):
                d[name] = e[name] = 1
    """)
    assert len(f) == 2 and len({(x.lineno, x.pattern) for x in f}) == 1


def test_main_exit_code(tmp_path: Path) -> None:
    _lint(tmp_path, """
        for kind in ("traits", "roles"):
            for name in names(kind):
                d[name] = 1
    """)
    assert lk.main([str(tmp_path / "mod.py")]) == 1
    (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
    assert lk.main([str(tmp_path / "clean.py")]) == 0
