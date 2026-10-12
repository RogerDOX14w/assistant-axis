"""Tests for tools/migrate_dataset_to_derived_layout.py (synthetic
datasets under tmp_path only; the real datasets are never touched)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools import migrate_dataset_to_derived_layout as mig  # noqa: E402


def _dataset(tmp_path: Path) -> Path:
    ds = tmp_path / "ds"
    cv = ds / "combinations" / "vectors"
    for et in mig.LEGACY_MARGINAL_NAMES:
        (cv / et).mkdir(parents=True)
        (cv / et / "a.pt").write_bytes(b"A" + et.encode())
    (cv / "mean_r_combos.pt").write_bytes(b"m")
    return ds


def _copy_dir(src: Path, dst: Path) -> None:
    dst.mkdir()
    for p in src.iterdir():
        (dst / p.name).write_bytes(p.read_bytes())


def test_identical_flat_copy_is_pruned_and_items_moved(tmp_path: Path) -> None:
    ds = _dataset(tmp_path)
    cv = ds / "combinations" / "vectors"
    _copy_dir(cv / "r_goal", cv / "r_goal copy")
    plan = mig._plan_for_dataset(ds, prune_finder_copies=True)
    assert plan.issues == []
    assert [a.kind for a in plan.actions].count("prune") == 1
    assert mig._execute(plan, dry_run=False) is True
    assert not (cv / "r_goal copy").exists()
    assert (cv / "derived" / "marginals" / "r_goal" / "a.pt").exists()
    assert (cv / "derived" / "aggregates" / "mean_r_combos.pt").exists()


def test_copy_with_a_subdirectory_is_not_pruned(tmp_path: Path) -> None:
    """Regression (2026-10-12): only top-level files were compared, but the
    prune removes the copy recursively, so a subdirectory with its own
    files would have been deleted as part of a "byte-identical" copy."""
    ds = _dataset(tmp_path)
    cv = ds / "combinations" / "vectors"
    _copy_dir(cv / "r_goal", cv / "r_goal copy")
    (cv / "r_goal copy" / "extra").mkdir()
    (cv / "r_goal copy" / "extra" / "only_here.pt").write_bytes(b"unique")

    plan = mig._plan_for_dataset(ds, prune_finder_copies=True)
    assert any("non_file_entries_in_copy" in i for i in plan.issues)
    assert mig._execute(plan, dry_run=False) is False      # refuses to run
    assert (cv / "r_goal copy" / "extra" / "only_here.pt").exists()
    assert (cv / "r_goal").exists()                         # nothing moved


def test_differing_copy_is_reported(tmp_path: Path) -> None:
    ds = _dataset(tmp_path)
    cv = ds / "combinations" / "vectors"
    _copy_dir(cv / "t_goal", cv / "t_goal copy")
    (cv / "t_goal copy" / "a.pt").write_bytes(b"changed")
    plan = mig._plan_for_dataset(ds, prune_finder_copies=True)
    assert any("differing" in i for i in plan.issues)


def test_dry_run_touches_nothing(tmp_path: Path) -> None:
    ds = _dataset(tmp_path)
    cv = ds / "combinations" / "vectors"
    plan = mig._plan_for_dataset(ds, prune_finder_copies=False)
    assert mig._execute(plan, dry_run=True) is True
    assert (cv / "r_goal" / "a.pt").exists()
    assert not (cv / "derived").exists()
