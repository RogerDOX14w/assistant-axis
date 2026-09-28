"""Every gapgen path stays inside the repository (file-access boundary)."""
from pathlib import Path

import pytest

from assistant_axis.gapgen import paths


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def test_repo_root_is_this_checkout():
    assert (paths.REPO_ROOT / "pyproject.toml").is_file()
    assert (paths.REPO_ROOT / "assistant_axis" / "gapgen" / "paths.py").is_file()


@pytest.mark.parametrize("name", sorted(paths.all_paths()))
def test_every_path_inside_repo(name):
    p = paths.all_paths()[name]
    assert _inside(p, paths.REPO_ROOT), f"{name} = {p} leaves the repository"


def test_downloads_under_data_external():
    assert paths.wn_data_dir() == paths.REPO_ROOT / "data" / "external" / "wn"
    assert paths.hf_cache_dir() == paths.REPO_ROOT / "data" / "external" / "hf"


def test_wn_config_points_in_tree():
    """Importing gapgen.wordnet pins the wn data directory in-tree before any
    lookup or download (the library default is under the home directory)."""
    pytest.importorskip("wn")
    import os

    from assistant_axis.gapgen import wordnet as gw
    import wn

    assert Path(os.environ["WN_DATA_DIR"]) == paths.wn_data_dir()
    assert Path(wn.config._data_directory) == paths.wn_data_dir()
    assert _inside(Path(wn.config._data_directory), paths.REPO_ROOT)
    assert gw.WN_DATA_DIR == paths.wn_data_dir()


@pytest.mark.parametrize("bad", ["", "..", "a/b", "../x", "a b", "/abs", ".hidden", "x/..", "a..b"])
def test_ids_that_escape_are_refused(bad):
    with pytest.raises(ValueError):
        paths.run_dir(bad, "r1")
    with pytest.raises(ValueError):
        paths.filter_dir(bad)


def test_run_dir_shape(tmp_path):
    assert paths.run_dir("wordnet_walk", "2026-09-30a", candidates_dir=tmp_path) == \
        tmp_path / "runs" / "wordnet_walk" / "2026-09-30a"
