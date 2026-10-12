"""Mirror a Hugging Face model cache into RAM-backed tmpfs (/dev/shm).

The one implementation of the model mirror for both drivers: the steering
driver (``steering/run_sweep.py``) imports it, and since 2026-10-12
``pipeline/run_pipeline.sh`` runs this file as a script
(``python ../assistant_axis/tmpfs.py mirror --model ...``, which prints the
new HF_HOME) instead of its own ``cp -r`` (review P4 D7, walk-through
P8.6).  Model weights load from RAM-backed tmpfs instead of NFS-backed
``/workspace``, which on RunPod can otherwise hang for hours on cold mmap
reads.

Two copy methods, chosen by ``method`` (``--tmpfs-method`` on both drivers):

* ``rsync`` -- ``rsync -a --delete --partial`` into the mirror directory;
  finishes an interrupted copy and tops up an existing mirror in place.
* ``cp`` -- a fresh copy into a staging directory beside the mirror, renamed
  into place only when complete (the shell driver's method until
  2026-10-12).  An existing directory without a completeness marker is not
  reused or deleted (another process may be loading from it): the call
  returns None and says to delete it or use rsync.
* ``auto`` (the default) -- rsync when it is installed, else cp.

Both write the completeness marker (:data:`MIRROR_MARKER_FILENAME`) that the
fast path checks, and neither ever leaves an incomplete copy at the mirror's
own path.  This file uses only the standard library, so the shell driver can
run it without importing the ``assistant_axis`` package.

Why this exists: ``HuggingFace.from_pretrained`` mmap's the safetensors
shards.  When those live on a slow network filesystem, the first
parameter access (or the .to(cuda) walk after device_map="cpu") page-faults
through the network for hours.  Mirroring the cache to /dev/shm puts
everything on a local RAM-backed mount, sidestepping the issue entirely.

Usage:

    from assistant_axis.tmpfs import setup_model_tmpfs_cache

    new_hf_home = setup_model_tmpfs_cache(model_name="Qwen/Qwen3-32B")
    if new_hf_home is not None:
        os.environ["HF_HOME"] = new_hf_home

    # Now load the model -- it will use the tmpfs-cached shards
    model = AutoModelForCausalLM.from_pretrained(model_name, ...)

Returns ``None`` (and logs prominently) if the tmpfs cache couldn't be set
up: ``/dev/shm`` not present, insufficient space, source cache missing,
etc.  The caller should fall back to the original ``HF_HOME``.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TMPFS_HF_HOME = "/dev/shm/hf-cache"
HEADROOM_FACTOR = 1.5    # 1.5× model size required free in /dev/shm

# How the mirror is copied (see the module docstring).
MIRROR_METHODS = ("auto", "rsync", "cp")
DEFAULT_MIRROR_METHOD = "auto"

# Sentinel file written into the tmpfs model dir after a successful rsync.
# Lets later setup_model_tmpfs_cache calls fast-path past a 5+ minute NFS
# rsync scan when the mirror is already complete and intact.  The fast-path
# verifies by re-measuring the tmpfs tree and comparing to the recorded
# size; if anything was added/removed/corrupted in tmpfs since the last
# sync, the size check fails and we fall through to a normal rsync.
MIRROR_MARKER_FILENAME = ".tmpfs_mirror_complete"
# Fraction of recorded size we tolerate as drift (filesystem rounding,
# the marker file itself, etc.) before declaring the mirror stale.
MIRROR_SIZE_TOLERANCE = 0.001    # 0.1%


def _du_kb(path: Path) -> Optional[int]:
    """Return size of `path` tree in 1K blocks via du -sk; None on failure."""
    try:
        result = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True, text=True, timeout=120, check=True,
        )
        return int(result.stdout.split()[0])
    except (subprocess.SubprocessError, ValueError, FileNotFoundError) as e:
        logger.warning(f"du -sk {path} failed: {e}")
        return None


def _avail_kb(path: Path) -> Optional[int]:
    """Return available KB at `path` mount via df; None on failure."""
    try:
        result = subprocess.run(
            ["df", "--output=avail", str(path)],
            capture_output=True, text=True, timeout=10, check=True,
        )
        # df --output=avail prints a header line then the value
        lines = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        if len(lines) >= 2:
            return int(lines[-1])
        return None
    except (subprocess.SubprocessError, ValueError, FileNotFoundError) as e:
        logger.warning(f"df --output=avail {path} failed: {e}")
        return None


def _check_existing_mirror(tmpfs_model_dir: Path) -> Optional[dict]:
    """Fast-path check: is the tmpfs mirror complete and intact?

    If the marker file written after a previous successful rsync is
    present AND the current tmpfs tree size still matches what the
    marker recorded, return the marker payload.  Otherwise return
    None and let the caller fall through to a full rsync.

    This deliberately does NOT touch the NFS source: the whole point
    is to skip the slow source-side stat traversal when we already
    have a known-good mirror.  Cost: one ``du -sk`` on tmpfs (cheap,
    RAM-backed) vs the alternative of one ``du -sk`` on NFS plus a
    full rsync scan against NFS (5+ minutes for a 60 GB model).

    Stale-source caveat: if the NFS source genuinely changed (model
    upgrade, cache repaired, etc.) we won't notice and will keep
    serving the old tmpfs copy.  Workaround: delete
    ``{tmpfs_model_dir}/{MIRROR_MARKER_FILENAME}`` to force a re-sync.
    For HF caches this is rarely an issue -- model snapshots are
    immutable and live under ``snapshots/<commit_hash>/``.
    """
    marker_path = tmpfs_model_dir / MIRROR_MARKER_FILENAME
    if not marker_path.is_file():
        return None

    try:
        marker = json.loads(marker_path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"[tmpfs] marker {marker_path} unreadable ({e}); "
                       f"will re-sync to be safe")
        return None

    recorded_size = marker.get("mirror_size_kb")
    if not isinstance(recorded_size, int):
        return None

    actual_size = _du_kb(tmpfs_model_dir)
    if actual_size is None:
        return None

    # We treat shrinkage (files deleted from the mirror) as cause for
    # re-sync but tolerate growth (e.g. the marker file itself, or stray
    # cache entries from other models added after the mirror).  An older
    # symmetric drift check would flag the marker file's own ~4 kB block
    # contribution as "drifted" on small tmpfs trees, blocking the
    # fast-path on every call.
    shortfall = max(0, recorded_size - actual_size)
    shortfall_ratio = shortfall / max(recorded_size, 1)
    if shortfall_ratio > MIRROR_SIZE_TOLERANCE:
        logger.warning(
            f"[tmpfs] marker says {recorded_size} kB but tmpfs is only "
            f"{actual_size} kB (shortfall {shortfall_ratio:.2%}); re-syncing"
        )
        return None

    return marker


def _write_mirror_marker(
    tmpfs_model_dir: Path,
    source_size_kb: int,
    *,
    model_subdir: Optional[str] = None,
    method: str = "rsync",
) -> None:
    """Record a 'mirror complete' marker after a successful copy.

    Stored fields are the keys ``_check_existing_mirror`` reads to
    decide whether the mirror is still good.  Best-effort: a write
    failure here just means the next call won't get the fast-path
    (a slow rsync against NFS), not a correctness problem.
    ``model_subdir`` names the mirror when ``tmpfs_model_dir`` is the cp
    method's staging directory, whose marker is written before the rename.
    """
    marker_path = tmpfs_model_dir / MIRROR_MARKER_FILENAME
    payload = {
        "marker_version": 1,
        "model_subdir": model_subdir or tmpfs_model_dir.name,
        "source_size_kb": source_size_kb,
        "mirror_size_kb": _du_kb(tmpfs_model_dir),
        "completed_at": time.time(),
        "method": method,
    }
    try:
        marker_path.write_text(json.dumps(payload, indent=2))
    except OSError as e:
        logger.warning(f"[tmpfs] couldn't write marker {marker_path}: {e}")


def _rsync_mirror(
    source: Path,
    dest: Path,
    *,
    timeout_s: int = 1800,
    logger_obj: Optional[logging.Logger] = None,
) -> bool:
    """Mirror ``source`` -> ``dest`` using ``rsync -a --delete --partial``.

    Why rsync rather than ``shutil.copytree``: rsync's incremental
    algorithm covers both the fresh-copy case and the
    finish-an-interrupted-copy case in a single invocation, with no
    need for a separate "is dest already up to date?" verification
    pass on our side.  After this returns True, ``dest`` matches
    ``source`` byte-for-byte modulo whatever ``-a`` doesn't preserve
    (xattrs, etc. -- not relevant for HF caches).

    Flags:
        ``-a``        : archive (preserves symlinks, perms, mtimes)
        ``--delete``  : remove files in dest that aren't in source,
                        so a stale extra shard from a previous run
                        gets cleaned up rather than confusing
                        downstream loaders
        ``--partial`` : keep partially-transferred files on failure
                        so a retry can resume rather than restart
                        from zero on each shard

    Returns True on success, False on rsync invocation or run failure
    (including ENOSPC mid-transfer).  Caller should treat False as
    "tmpfs cache unavailable, fall back to source HF_HOME".
    """
    log = logger_obj or logger

    # Trailing slashes on both paths = "copy CONTENTS of source into
    # dest", matching shutil.copytree(source, dest) semantics.
    cmd = [
        "rsync", "-a", "--delete", "--partial",
        str(source) + "/", str(dest) + "/",
    ]

    if shutil.which("rsync") is None:
        log.warning(
            "[tmpfs] rsync not on PATH; install it (e.g. "
            "`apt-get install -y rsync`) for tmpfs cache mirroring "
            "to work.  Falling back to no tmpfs cache."
        )
        return False

    try:
        dest.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=timeout_s, check=False,
        )
    except (OSError, subprocess.TimeoutExpired,
            subprocess.SubprocessError) as e:
        log.warning(f"[tmpfs] rsync invocation failed: {e}")
        return False

    if result.returncode != 0:
        # rsync exit codes: 0=ok, 23=partial transfer, 24=files vanished
        # during transfer, 11=error in IO, 12=error in protocol stream,
        # etc.  We treat anything non-zero as failure -- the caller's
        # fallback (no tmpfs cache) is safer than handing a possibly-
        # incomplete tree to vLLM.
        log.warning(
            f"[tmpfs] rsync failed (rc={result.returncode}): "
            f"{(result.stderr or result.stdout).strip()}"
        )
        return False
    return True


def resolve_mirror_method(method: str = DEFAULT_MIRROR_METHOD) -> str:
    """``auto`` -> ``rsync`` when it is on PATH, else ``cp``; the other two
    as given.  Raises ValueError for anything else."""
    if method not in MIRROR_METHODS:
        raise ValueError(f"unknown tmpfs mirror method {method!r}; one of {MIRROR_METHODS}")
    if method == "auto":
        return "rsync" if shutil.which("rsync") else "cp"
    return method


def _staging_dir_for(tmpfs_model_dir: Path) -> Path:
    """The cp method's staging directory, beside the mirror (same mount, so
    the final rename is atomic)."""
    return tmpfs_model_dir.parent / f".{tmpfs_model_dir.name}.partial.{os.getpid()}"


def _cp_mirror(
    source: Path,
    tmpfs_model_dir: Path,
    *,
    source_size_kb: int,
    logger_obj: Optional[logging.Logger] = None,
) -> bool:
    """Copy ``source`` into a staging directory beside ``tmpfs_model_dir``,
    write the completeness marker into it, and rename it into place.

    The mirror's own path never holds a partial copy: a copy that fails
    (ENOSPC) or is interrupted leaves only a ``.<name>.partial.<pid>``
    directory, and staging directories left by earlier interrupted runs are
    removed first (they hold RAM).  Symlinks are copied as symlinks, as
    ``cp -r`` does: a Hugging Face cache's ``snapshots/`` links point into
    its ``blobs/`` by relative path, so they resolve inside the copy.
    Returns False when the copy or the rename fails (the caller falls back
    to the source cache)."""
    log = logger_obj or logger
    parent = tmpfs_model_dir.parent
    parent.mkdir(parents=True, exist_ok=True)
    for stale in parent.glob(f".{tmpfs_model_dir.name}.partial.*"):
        shutil.rmtree(stale, ignore_errors=True)
    staging = _staging_dir_for(tmpfs_model_dir)
    try:
        shutil.copytree(source, staging, symlinks=True)
        _write_mirror_marker(staging, source_size_kb=source_size_kb,
                             model_subdir=tmpfs_model_dir.name, method="cp")
    except OSError as e:     # shutil.Error is an OSError
        log.warning(f"[tmpfs] copy into {staging} failed: {e}")
        shutil.rmtree(staging, ignore_errors=True)
        return False
    try:
        os.rename(staging, tmpfs_model_dir)
        return True
    except OSError as e:
        shutil.rmtree(staging, ignore_errors=True)
        # Another process finished the same copy first: use its mirror.
        if _check_existing_mirror(tmpfs_model_dir) is not None:
            log.info(f"[tmpfs] {tmpfs_model_dir} was completed by another process; using it")
            return True
        log.warning(f"[tmpfs] renaming {staging} to {tmpfs_model_dir} failed: {e}")
        return False


def _discard_failed_mirror(tmpfs_model_dir: Path, *, existed_before: bool) -> None:
    """Clean up after a failed rsync into ``tmpfs_model_dir``.

    A directory this call created is removed (rsync's ``--partial`` may
    have left a truncated shard under its real name, and
    ``run_pipeline.sh`` reuses any existing mirror directory without
    checking it).  A directory that was already there is left in place
    and only its completeness marker is removed: another process (a
    pipeline step, a steering worker) may be loading from it, and
    deleting it under them turns a failed top-up here into a crash
    there.  (Before 2026-10-12 both cases were ``rmtree``'d.)
    """
    if existed_before:
        logger.warning(
            f"[tmpfs] leaving the existing mirror {tmpfs_model_dir} in place "
            f"(other processes may be loading from it); its completeness "
            f"marker is removed so the next call re-syncs it"
        )
        try:
            (tmpfs_model_dir / MIRROR_MARKER_FILENAME).unlink(missing_ok=True)
        except OSError:
            pass
        return
    try:
        shutil.rmtree(tmpfs_model_dir, ignore_errors=True)
    except OSError:
        pass


def _existing_ancestor(path: Path) -> Optional[Path]:
    """``path`` or its deepest existing ancestor (what df can measure)."""
    p = path
    while not p.exists():
        if p.parent == p:
            return None
        p = p.parent
    return p


def setup_model_tmpfs_cache(
    model_name: str,
    *,
    tmpfs_hf_home: str = DEFAULT_TMPFS_HF_HOME,
    source_hf_home: Optional[str] = None,
    headroom_factor: float = HEADROOM_FACTOR,
    method: str = DEFAULT_MIRROR_METHOD,
) -> Optional[str]:
    """Mirror the HF cache for `model_name` into a RAM-backed tmpfs.

    - If ``tmpfs_hf_home``'s mount (``/dev/shm`` by default) is not present
      -> log and return None (caller keeps default HF_HOME).
    - If the model's directory in source HF cache is missing -> log and return
      None (HF will download to the source on first use).
    - If already mirrored (completeness marker present, tree not shrunk)
      -> return tmpfs_hf_home (no-op).
    - Otherwise check headroom (default 1.5× model size) on that mount; if
      insufficient, log a loud WARNING and return None so the caller knows
      a multi-hour cold mmap is likely.
    - Copy the model subtree with ``method`` (``auto`` / ``rsync`` / ``cp``;
      module docstring), write the marker and return the new HF_HOME path.

    The caller is responsible for setting ``os.environ["HF_HOME"]`` to the
    returned value (we don't mutate the environment from inside this
    helper, to keep it composable for callers that prefer to manage env).

    Returns the new HF_HOME path on success, ``None`` on any skip/failure.
    """
    method = resolve_mirror_method(method)
    tmpfs_root = Path(tmpfs_hf_home)
    # The mount the mirror goes on: the parent of tmpfs_hf_home (/dev/shm for
    # the default), which must exist (the shell driver's `[ -d /dev/shm ]`).
    # Before 2026-10-12 /dev/shm was checked and measured whatever
    # tmpfs_hf_home was.
    if not tmpfs_root.parent.is_dir():
        logger.warning(f"[tmpfs] {tmpfs_root.parent} not present; tmpfs setup skipped")
        return None
    mount_probe = _existing_ancestor(tmpfs_root)

    source_hf = Path(source_hf_home) if source_hf_home else Path(
        os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface"))
    model_subdir = "models--" + model_name.replace("/", "--")
    source_model_dir = source_hf / "hub" / model_subdir
    tmpfs_model_dir = tmpfs_root / "hub" / model_subdir

    if not source_model_dir.is_dir():
        logger.warning(
            f"[tmpfs] {model_name} not found at {source_model_dir}; "
            f"HF will download to {source_hf} on first use "
            f"(no tmpfs cache pre-populated)"
        )
        return None

    # Fast-path: if a previous run completed an rsync into tmpfs and
    # the tree is still intact (size matches the recorded marker), skip
    # the entire source-side scan + rsync.  This avoids a 5+ minute
    # NFS stat traversal of the source on every run when nothing has
    # changed.  Stale-source caveat documented in
    # _check_existing_mirror().
    existing_marker = _check_existing_mirror(tmpfs_model_dir)
    if existing_marker is not None:
        logger.info(
            f"[tmpfs] {model_name} already mirrored "
            f"({existing_marker.get('mirror_size_kb', '?')} kB, "
            f"completed at {time.ctime(existing_marker.get('completed_at', 0))}); "
            f"skipping rsync, HF_HOME={tmpfs_root}"
        )
        return str(tmpfs_root)

    # The cp method cannot top up: an existing directory without a valid
    # marker (a partial copy, or a mirror made by the shell driver's cp -r
    # before 2026-10-12) is neither reused nor deleted, since another
    # process may be loading from it.
    if method == "cp" and tmpfs_model_dir.exists():
        logger.warning(
            f"[tmpfs] {tmpfs_model_dir} exists without a completeness marker "
            f"(an interrupted copy, or one made before markers were written); "
            f"the cp method neither trusts nor deletes it.  Delete it (when no "
            f"process is loading from it) or use --tmpfs-method rsync.  "
            f"Falling back to the source cache {source_hf}.")
        return None

    needed_kb = _du_kb(source_model_dir)
    avail_kb = _avail_kb(mount_probe)

    if needed_kb is None or avail_kb is None:
        logger.warning(
            f"[tmpfs] couldn't measure space (need={needed_kb}, avail={avail_kb}); "
            f"skipping tmpfs cache to be safe"
        )
        return None

    # Headroom check.  rsync writes only what's missing, so an
    # incremental top-up may need less than the full source size --
    # but we don't know up-front how much is already in tmpfs that
    # also matches the source, so we pessimistically require room
    # for the whole model plus headroom.  If tmpfs is already
    # populated, the existing files count toward "free" via /dev/shm
    # accounting.  Net effect: this check rejects only the cases
    # where a fresh full copy genuinely won't fit.
    existing_kb = _du_kb(tmpfs_model_dir) if tmpfs_model_dir.is_dir() else 0
    additional_needed_kb = max(0, needed_kb - (existing_kb or 0))
    required_kb = int(additional_needed_kb * headroom_factor)
    if avail_kb < required_kb:
        # Loud warning per the pattern in run_pipeline.sh: silent fallback
        # to NFS results in multi-hour mmap stalls that are easy to miss.
        bar = "[tmpfs] " + "=" * 60
        logger.warning("")
        logger.warning(bar)
        logger.warning(f"[tmpfs]  WARNING: insufficient space on {mount_probe} — tmpfs cache DISABLED")
        logger.warning(f"[tmpfs]  need {required_kb}kB ({headroom_factor:.1f}x additional), have {avail_kb}kB")
        logger.warning(f"[tmpfs]  Falling back to source HF cache: {source_hf}")
        logger.warning(f"[tmpfs]  If that is on NFS or other slow storage, expect model loads to")
        logger.warning(f"[tmpfs]  hang for HOURS on cold mmap reads of the safetensors shards.")
        logger.warning(f"[tmpfs]  Fix: increase --shm-size on the container, or free /dev/shm.")
        logger.warning(bar)
        logger.warning("")
        return None

    # rsync covers fresh-copy AND finish-partial-copy in one call.
    # No verification pass needed: rsync compares (size, mtime) by
    # default and re-transfers anything that doesn't match, so an
    # interrupted previous run that left a half-written shard gets
    # cleaned up automatically.  --delete also removes any stale
    # extras that aren't in the source.
    if tmpfs_model_dir.is_dir():
        logger.info(
            f"[tmpfs] mirroring {model_name} via rsync "
            f"({needed_kb // 1024} MB source, "
            f"{(existing_kb or 0) // 1024} MB already in tmpfs); "
            f"only changed/missing files will be transferred"
        )
    else:
        logger.info(
            f"[tmpfs] copying {model_name} ({needed_kb // 1024} MB, {method}) "
            f"from {source_model_dir} to {tmpfs_model_dir} ..."
        )

    tmpfs_root.mkdir(parents=True, exist_ok=True)
    (tmpfs_root / "hub").mkdir(parents=True, exist_ok=True)

    if method == "cp":
        # Staged copy, marker written inside, renamed into place.
        if not _cp_mirror(source_model_dir, tmpfs_model_dir,
                          source_size_kb=needed_kb, logger_obj=logger):
            return None
        logger.info(f"[tmpfs] mirror complete (cp); HF_HOME={tmpfs_root}")
        return str(tmpfs_root)

    existed_before = tmpfs_model_dir.is_dir()
    # A marker left from an earlier complete mirror must not survive a
    # top-up that is interrupted half way.
    if existed_before:
        try:
            (tmpfs_model_dir / MIRROR_MARKER_FILENAME).unlink(missing_ok=True)
        except OSError:
            pass
    if not _rsync_mirror(source_model_dir, tmpfs_model_dir, logger_obj=logger):
        _discard_failed_mirror(tmpfs_model_dir, existed_before=existed_before)
        return None

    # Drop the fast-path marker so the next call can skip rsync entirely.
    # Best-effort: if this fails, correctness is unaffected -- the next
    # call will just do a full (slow) rsync and try writing the marker
    # again.
    _write_mirror_marker(tmpfs_model_dir, source_size_kb=needed_kb, method="rsync")

    logger.info(f"[tmpfs] mirror complete (rsync); HF_HOME={tmpfs_root}")
    return str(tmpfs_root)


def _main(argv=None) -> int:
    """``python assistant_axis/tmpfs.py mirror --model M [--tmpfs-hf-home D]
    [--method auto|rsync|cp]``: what ``pipeline/run_pipeline.sh`` runs.
    Prints the new HF_HOME on stdout and exits 0 when the mirror is ready;
    exits 1 (nothing on stdout) when the caller should keep its HF_HOME.
    Log lines go to stderr."""
    import argparse
    import sys
    parser = argparse.ArgumentParser(prog="tmpfs.py", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mirror", help="mirror one model's HF cache into tmpfs")
    m.add_argument("--model", required=True)
    m.add_argument("--tmpfs-hf-home", default=DEFAULT_TMPFS_HF_HOME)
    m.add_argument("--source-hf-home", default=None,
                   help="default: $HF_HOME, else ~/.cache/huggingface")
    m.add_argument("--method", choices=MIRROR_METHODS, default=DEFAULT_MIRROR_METHOD)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    new_home = setup_model_tmpfs_cache(
        args.model, tmpfs_hf_home=args.tmpfs_hf_home,
        source_hf_home=args.source_hf_home, method=args.method)
    if new_home is None:
        return 1
    print(new_home)
    return 0


DEFAULT_TMPDIR = "/dev/shm"


def setup_tmpdir(target: str = DEFAULT_TMPDIR) -> str:
    """Unconditionally set ``TMPDIR`` to ``target`` (default ``/dev/shm``).

    Returns the resolved TMPDIR after the mutation.

    The steering driver and pipeline atomic-write helpers stage files
    via TMPDIR; pointing it at RAM-backed tmpfs avoids small-container
    ``/tmp`` fill-ups AND avoids the silent footgun where a pod-config
    default like ``TMPDIR=/workspace/tmp`` would route every staging
    write through the slow NFS path.  Callers who genuinely want to
    preserve a pre-existing ``TMPDIR`` (e.g. for testing or a custom
    deployment) should pass it explicitly via the ``--tmpdir`` flag
    on the driver script.

    If ``target`` doesn't exist on disk, falls back to ``/tmp`` with
    a WARNING -- preferable to crashing, but the caller should fix
    their setup or override the target.

    Side effect: also sets ``TRITON_CACHE_DIR`` and
    ``TORCHINDUCTOR_CACHE_DIR`` to a non-tmpfs path if not already
    set by the user.  See :func:`_setup_compile_cache_dirs` for why.
    """
    _setup_compile_cache_dirs()

    prior = os.environ.get("TMPDIR")

    if Path(target).is_dir():
        os.environ["TMPDIR"] = target
        if prior and prior != target:
            logger.info(
                f"[tmpfs] TMPDIR={target} (overriding prior {prior!r}; "
                f"pass --tmpdir {prior!r} to preserve the previous value)"
            )
        else:
            logger.info(f"[tmpfs] TMPDIR={target}")
        return target

    # Target doesn't exist on disk.  Don't silently inherit a possibly
    # bad prior TMPDIR -- clamp to /tmp, which is local-disk and at
    # least won't route writes through slow network storage.
    logger.warning(
        f"[tmpfs] requested TMPDIR target {target} not present on disk; "
        f"falling back to /tmp.  Small container /tmp may fill under "
        f"concurrent writes -- pass --tmpdir <path> to override."
    )
    os.environ["TMPDIR"] = "/tmp"
    return "/tmp"


def setup_tmpdir_if_unset() -> str:
    """Deprecated: preserves any pre-existing ``TMPDIR`` (and silently
    inherits the pod-default footgun).  Kept as a thin backward-compat
    shim for external callers; new code should use :func:`setup_tmpdir`.
    """
    _setup_compile_cache_dirs()
    prior = os.environ.get("TMPDIR")
    if prior:
        logger.warning(
            f"[tmpfs] setup_tmpdir_if_unset is deprecated; "
            f"preserving prior TMPDIR={prior!r} (may be a pod-default footgun -- "
            f"consider switching to setup_tmpdir() for unconditional override)"
        )
        return prior
    return setup_tmpdir(DEFAULT_TMPDIR)


def _is_noexec(path: Path, mounts_file: Path = Path("/proc/mounts")) -> Optional[bool]:
    """Return True if ``path``'s mount has the ``noexec`` flag.

    Best-effort: returns ``None`` (don't know) if /proc/mounts is
    unavailable (e.g. macOS) or unparseable.  The result drives
    "should I cache executable .so files here?" decisions; on
    "don't know" the caller should err on the side of NOT placing
    exec content there.
    """
    try:
        if not mounts_file.exists():
            return None
        target = path.expanduser().resolve()
        # Walk /proc/mounts, find the longest mount-point prefix that
        # contains `target`.  Mounts file format:
        #   <device> <mount-point> <fs-type> <opts> <dump> <pass>
        best_match: tuple[int, str] = (-1, "")
        with open(mounts_file, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) < 4:
                    continue
                mp = parts[1]
                if (str(target) == mp or str(target).startswith(mp.rstrip("/") + "/")) \
                        and len(mp) > best_match[0]:
                    best_match = (len(mp), parts[3])
        if best_match[0] < 0:
            return None
        return "noexec" in best_match[1].split(",")
    except OSError:
        return None


def _setup_compile_cache_dirs() -> None:
    """Set ``TRITON_CACHE_DIR`` / ``TORCHINDUCTOR_CACHE_DIR`` to a
    non-tmpfs location if they're unset, AND if the prevailing TMPDIR
    (or /dev/shm) is mounted ``noexec``.

    Triton / torchinductor compile CUDA kernels into shared-object
    files at runtime, then ``dlopen()`` them.  ``dlopen`` requires
    ``mmap(PROT_EXEC)``, which the kernel rejects on a ``noexec``
    mount with a confusing "failed to map segment from shared
    object" ImportError.  RunPod (and most hardened containers)
    mount ``/dev/shm`` ``noexec`` by default, which is fine for
    read-only model-shard mmaps but breaks the compile cache as
    soon as TMPDIR is also pointed at /dev/shm.

    We don't override user-provided values; if the caller already
    set ``TRITON_CACHE_DIR`` / ``TORCHINDUCTOR_CACHE_DIR``, that
    wins.  Otherwise we route them to ``$HOME/.cache/triton`` and
    ``$HOME/.cache/torchinductor``, which are usually on a regular
    filesystem (and as a side benefit persist across container
    restarts so the ~50 s torch.compile pass becomes a one-time
    cost rather than a per-pipeline-run cost).
    """
    # Cheap exit: if the user has already set these, respect their choice.
    needs_triton = "TRITON_CACHE_DIR" not in os.environ
    needs_inductor = "TORCHINDUCTOR_CACHE_DIR" not in os.environ
    if not (needs_triton or needs_inductor):
        return

    # Only intervene if /dev/shm is the at-risk mount.  On a fresh box
    # where /dev/shm is exec-allowed (rare), default behaviour is fine.
    shm = Path("/dev/shm")
    if not shm.is_dir():
        return
    if _is_noexec(shm) is False:
        return  # exec allowed -> nothing to fix

    # Either noexec confirmed or unknown: route caches off /dev/shm.
    cache_root = Path(os.environ.get("XDG_CACHE_HOME") or
                      (Path.home() / ".cache"))
    if needs_triton:
        triton_dir = cache_root / "triton"
        triton_dir.mkdir(parents=True, exist_ok=True)
        os.environ["TRITON_CACHE_DIR"] = str(triton_dir)
        logger.info(
            f"[tmpfs] TRITON_CACHE_DIR={triton_dir} "
            f"(/dev/shm is noexec; routing compile cache off tmpfs)"
        )
    if needs_inductor:
        inductor_dir = cache_root / "torchinductor"
        inductor_dir.mkdir(parents=True, exist_ok=True)
        os.environ["TORCHINDUCTOR_CACHE_DIR"] = str(inductor_dir)
        logger.info(
            f"[tmpfs] TORCHINDUCTOR_CACHE_DIR={inductor_dir} "
            f"(/dev/shm is noexec; routing compile cache off tmpfs)"
        )


if __name__ == "__main__":
    raise SystemExit(_main())
