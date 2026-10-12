"""Tests for assistant_axis.tmpfs: the mirror-marker fast-path helpers
(``_check_existing_mirror``, ``_write_mirror_marker``) and, since the mount
became the parent of ``tmpfs_hf_home`` (P8.6, 2026-10-12), the whole
``setup_model_tmpfs_cache`` call on a fake cache under ``tmp_path`` with
both copy methods and the CLI the shell driver runs.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from assistant_axis import tmpfs


# ---------------------------------------------------------------------------
# _write_mirror_marker
# ---------------------------------------------------------------------------

class TestWriteMirrorMarker:
    def test_writes_expected_fields(self, tmp_path: Path):
        # Populate the mirror dir with some bytes so _du_kb returns a
        # nonzero size that the marker can record.
        (tmp_path / "blob.bin").write_bytes(b"x" * 4096)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=8)
        marker = json.loads(
            (tmp_path / tmpfs.MIRROR_MARKER_FILENAME).read_text()
        )
        assert marker["marker_version"] == 1
        assert marker["model_subdir"] == tmp_path.name
        assert marker["source_size_kb"] == 8
        assert isinstance(marker["mirror_size_kb"], int)
        assert marker["mirror_size_kb"] > 0
        # completed_at is roughly now (within 60s)
        assert abs(marker["completed_at"] - time.time()) < 60

    def test_swallows_oserror(self, tmp_path: Path):
        # Marker dir doesn't exist -> open() raises -> we should not
        # propagate (best-effort write).  Caller would otherwise have
        # no way to recover.
        nonexistent = tmp_path / "does_not_exist"
        # Should NOT raise, just log a warning.
        tmpfs._write_mirror_marker(nonexistent, source_size_kb=1)


# ---------------------------------------------------------------------------
# _check_existing_mirror
# ---------------------------------------------------------------------------

class TestCheckExistingMirror:
    def test_returns_none_when_marker_missing(self, tmp_path: Path):
        assert tmpfs._check_existing_mirror(tmp_path) is None

    def test_returns_none_when_marker_unreadable(self, tmp_path: Path):
        (tmp_path / tmpfs.MIRROR_MARKER_FILENAME).write_text("not-json{")
        assert tmpfs._check_existing_mirror(tmp_path) is None

    def test_returns_none_when_size_field_missing(self, tmp_path: Path):
        (tmp_path / tmpfs.MIRROR_MARKER_FILENAME).write_text(
            json.dumps({"marker_version": 1, "model_subdir": "x"})
        )
        assert tmpfs._check_existing_mirror(tmp_path) is None

    def test_returns_marker_when_size_matches(self, tmp_path: Path):
        # Real fixture: write some bytes, measure with _du_kb, write a
        # marker recording that size, then read it back.  Round-trip
        # exercises the full happy path.
        (tmp_path / "blob.bin").write_bytes(b"x" * 32_000)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=32)
        marker = tmpfs._check_existing_mirror(tmp_path)
        assert marker is not None
        assert marker["source_size_kb"] == 32
        assert marker["mirror_size_kb"] >= 32

    def test_tolerates_growth(self, tmp_path: Path):
        # Lay down 32 KB of payload, write the marker, then add another
        # 32 KB.  Growth doesn't invalidate the mirror -- the model files
        # we care about are still present, the extra is just noise (e.g.
        # the marker file itself, or another model coexisting in the
        # cache).  Should still return the marker.
        (tmp_path / "blob.bin").write_bytes(b"x" * 32_000)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=32)
        (tmp_path / "extra.bin").write_bytes(b"y" * 32_000)
        assert tmpfs._check_existing_mirror(tmp_path) is not None

    def test_returns_none_when_files_deleted(self, tmp_path: Path):
        # Lay down 200 KB across two blobs, mark, then delete one blob
        # so tmpfs is now ~100 KB while marker still says 200 KB.
        # Shortfall > tolerance -> mirror is broken, should re-sync.
        (tmp_path / "a.bin").write_bytes(b"a" * 100_000)
        (tmp_path / "b.bin").write_bytes(b"b" * 100_000)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=200)
        (tmp_path / "b.bin").unlink()
        assert tmpfs._check_existing_mirror(tmp_path) is None

    def test_failed_sync_keeps_a_mirror_that_was_already_there(self, tmp_path: Path):
        """Another process may be loading from a mirror this call only meant
        to top up; deleting it (the behaviour before 2026-10-12) turned a
        failed rsync here into a crash there.  The marker goes, so the
        next call re-syncs instead of trusting it."""
        mirror = tmp_path / "models--x--y"
        (mirror / "snapshots").mkdir(parents=True)
        (mirror / "snapshots" / "shard.safetensors").write_bytes(b"w" * 1000)
        tmpfs._write_mirror_marker(mirror, source_size_kb=1)
        tmpfs._discard_failed_mirror(mirror, existed_before=True)
        assert (mirror / "snapshots" / "shard.safetensors").exists()
        assert not (mirror / tmpfs.MIRROR_MARKER_FILENAME).exists()
        assert tmpfs._check_existing_mirror(mirror) is None

    def test_failed_sync_removes_a_mirror_it_created(self, tmp_path: Path):
        mirror = tmp_path / "models--x--y"
        mirror.mkdir()
        (mirror / "partial.safetensors").write_bytes(b"p" * 10)
        tmpfs._discard_failed_mirror(mirror, existed_before=False)
        assert not mirror.exists()

    def test_tolerates_marker_file_overhead(self, tmp_path: Path):
        # The marker file itself contributes ~4 KB on disk (one block).
        # On a real 60 GB model that's a 0.000007% overhead, well below
        # MIRROR_SIZE_TOLERANCE.  Verified here by re-writing the marker
        # without changing the tree contents -- the second write should
        # update the marker in place, and a subsequent check should still
        # succeed because actual >= recorded (no shortfall).
        (tmp_path / "blob.bin").write_bytes(b"x" * 32_000)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=32)
        tmpfs._write_mirror_marker(tmp_path, source_size_kb=32)
        assert tmpfs._check_existing_mirror(tmp_path) is not None


# ---------------------------------------------------------------------------
# setup_model_tmpfs_cache end to end on a fake cache (P8.6, 2026-10-12)
#
# The mirror's mount is now the parent of tmpfs_hf_home, so the whole call
# runs on tmp_path: a fake HF cache (a blob and a relative snapshot symlink,
# as the hub lays them out) mirrored into tmp_path/shm/hf-cache.  df's GNU
# --output flag is not on macOS, so the free-space probe is stubbed.
# ---------------------------------------------------------------------------

import os
import shutil
import subprocess
import sys

import pytest

MODEL = "org/model"
SUBDIR = "models--org--model"


def _fake_cache(root: Path) -> Path:
    model = root / "hub" / SUBDIR
    (model / "blobs").mkdir(parents=True)
    (model / "blobs" / "abc123").write_bytes(b"w" * 50_000)
    (model / "snapshots" / "rev1").mkdir(parents=True)
    os.symlink("../../blobs/abc123", model / "snapshots" / "rev1" / "model.safetensors")
    (model / "refs").mkdir()
    (model / "refs" / "main").write_text("rev1")
    return model


@pytest.fixture
def env(tmp_path, monkeypatch):
    src = tmp_path / "src"
    _fake_cache(src)
    (tmp_path / "shm").mkdir()
    monkeypatch.setattr(tmpfs, "_avail_kb", lambda path: 10**9)
    return tmp_path


def _mirror(env, **kw):
    return tmpfs.setup_model_tmpfs_cache(
        MODEL, tmpfs_hf_home=str(env / "shm" / "hf-cache"),
        source_hf_home=str(env / "src"), **kw)


def _assert_complete_mirror(env, method):
    mirror = env / "shm" / "hf-cache" / "hub" / SUBDIR
    link = mirror / "snapshots" / "rev1" / "model.safetensors"
    assert link.is_symlink() and link.read_bytes() == b"w" * 50_000
    marker = json.loads((mirror / tmpfs.MIRROR_MARKER_FILENAME).read_text())
    assert marker["model_subdir"] == SUBDIR and marker["method"] == method
    assert not list(mirror.parent.glob(".*partial*"))


class TestMirrorMethods:
    def test_resolve_method(self, monkeypatch):
        monkeypatch.setattr(tmpfs.shutil, "which", lambda name: "/usr/bin/rsync")
        assert tmpfs.resolve_mirror_method("auto") == "rsync"
        monkeypatch.setattr(tmpfs.shutil, "which", lambda name: None)
        assert tmpfs.resolve_mirror_method("auto") == "cp"
        assert tmpfs.resolve_mirror_method("rsync") == "rsync"
        with pytest.raises(ValueError):
            tmpfs.resolve_mirror_method("scp")

    def test_cp_copies_stages_and_marks(self, env, monkeypatch):
        assert _mirror(env, method="cp") == str(env / "shm" / "hf-cache")
        _assert_complete_mirror(env, "cp")
        # The second call takes the fast path: no copy at all.
        monkeypatch.setattr(tmpfs, "_cp_mirror", lambda *a, **k: pytest.fail("copied again"))
        assert _mirror(env, method="cp") == str(env / "shm" / "hf-cache")

    @pytest.mark.skipif(shutil.which("rsync") is None, reason="needs rsync")
    def test_rsync_copies_and_marks(self, env):
        assert _mirror(env, method="rsync") == str(env / "shm" / "hf-cache")
        _assert_complete_mirror(env, "rsync")

    def test_cp_failure_leaves_nothing_at_the_mirror_path(self, env, monkeypatch):
        real = shutil.copytree

        def dies_half_way(src, dst, **kw):
            Path(dst).mkdir(parents=True)
            (Path(dst) / "half").write_text("x")
            raise OSError(28, "No space left on device")

        monkeypatch.setattr(tmpfs.shutil, "copytree", dies_half_way)
        assert _mirror(env, method="cp") is None
        hub = env / "shm" / "hf-cache" / "hub"
        assert not (hub / SUBDIR).exists()
        assert not list(hub.glob(".*partial*"))
        monkeypatch.setattr(tmpfs.shutil, "copytree", real)
        assert _mirror(env, method="cp") is not None          # a rerun completes it

    def test_cp_removes_stale_staging_dirs_first(self, env):
        hub = env / "shm" / "hf-cache" / "hub"
        stale = hub / f".{SUBDIR}.partial.999999"
        stale.mkdir(parents=True)
        (stale / "junk").write_text("x")
        assert _mirror(env, method="cp") is not None
        assert not stale.exists()

    def test_cp_neither_trusts_nor_deletes_an_unmarked_mirror(self, env, caplog):
        """A directory with no marker (an interrupted copy, or one the shell
        driver's cp -r made before markers): another process may be loading
        from it, so cp leaves it alone and falls back."""
        mirror = env / "shm" / "hf-cache" / "hub" / SUBDIR
        mirror.mkdir(parents=True)
        (mirror / "partial.safetensors").write_text("p")
        assert _mirror(env, method="cp") is None
        assert (mirror / "partial.safetensors").exists()
        assert "--tmpfs-method rsync" in caplog.text

    @pytest.mark.skipif(shutil.which("rsync") is None, reason="needs rsync")
    def test_rsync_tops_up_an_unmarked_mirror(self, env):
        mirror = env / "shm" / "hf-cache" / "hub" / SUBDIR
        mirror.mkdir(parents=True)
        (mirror / "stale_extra").write_text("old")
        assert _mirror(env, method="rsync") is not None
        _assert_complete_mirror(env, "rsync")
        assert not (mirror / "stale_extra").exists()            # --delete

    def test_missing_mount_skips(self, tmp_path):
        assert tmpfs.setup_model_tmpfs_cache(
            MODEL, tmpfs_hf_home=str(tmp_path / "nope" / "hf-cache"),
            source_hf_home=str(tmp_path)) is None

    def test_cli_prints_hf_home_or_exits_1(self, env, monkeypatch, capsys):
        """What run_pipeline.sh runs; also as a real subprocess (stdlib only,
        so the package is not imported)."""
        argv = ["mirror", "--model", MODEL, "--tmpfs-hf-home", str(env / "shm" / "hf-cache"),
                "--source-hf-home", str(env / "src"), "--method", "cp"]
        assert tmpfs._main(argv) == 0
        assert capsys.readouterr().out.strip() == str(env / "shm" / "hf-cache")
        bad =["mirror", "--model", "org/absent", "--tmpfs-hf-home", str(env / "shm" / "hf-cache"),
               "--source-hf-home", str(env / "src")]
        assert tmpfs._main(bad) == 1
        assert capsys.readouterr().out == ""
        proc = subprocess.run(
            [sys.executable, str(Path(tmpfs.__file__)), *bad, "--method", "cp"],
            capture_output=True, text=True)
        assert proc.returncode == 1 and proc.stdout == ""
        assert "not found" in proc.stderr
