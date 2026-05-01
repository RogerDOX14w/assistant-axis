"""Mirror a Hugging Face model cache into RAM-backed tmpfs (/dev/shm).

Python port of the ``setup_tmpfs`` shell function from
``pipeline/run_pipeline.sh``.  Lets non-bash entry points (e.g. the
steering driver) get the same speed-up: model weights load from RAM-backed
tmpfs instead of NFS-backed ``/workspace``, which on RunPod can otherwise
hang for hours on cold mmap reads.

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

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TMPFS_HF_HOME = "/dev/shm/hf-cache"
HEADROOM_FACTOR = 1.5    # 1.5× model size required free in /dev/shm


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


def setup_model_tmpfs_cache(
    model_name: str,
    *,
    tmpfs_hf_home: str = DEFAULT_TMPFS_HF_HOME,
    source_hf_home: Optional[str] = None,
    headroom_factor: float = HEADROOM_FACTOR,
) -> Optional[str]:
    """Mirror the HF cache for `model_name` into a RAM-backed tmpfs.

    Behaviour mirrors `setup_tmpfs` in pipeline/run_pipeline.sh:

    - If /dev/shm not present -> log and return None (caller keeps default HF_HOME).
    - If the model's directory in source HF cache is missing -> log and return
      None (HF will download to the source on first use).
    - If already mirrored -> return tmpfs_hf_home (no-op).
    - Otherwise check headroom (default 1.5× model size) in /dev/shm; if
      insufficient, log a loud WARNING and return None so the caller knows
      a multi-hour cold mmap is likely.
    - Copy the model subtree to tmpfs and return the new HF_HOME path.

    The caller is responsible for setting ``os.environ["HF_HOME"]`` to the
    returned value (we don't mutate the environment from inside this
    helper, to keep it composable for callers that prefer to manage env).

    Returns the new HF_HOME path on success, ``None`` on any skip/failure.
    """
    if not Path("/dev/shm").is_dir():
        logger.warning("[tmpfs] /dev/shm not present; tmpfs setup skipped")
        return None

    source_hf = Path(source_hf_home) if source_hf_home else Path(
        os.environ.get("HF_HOME") or (Path.home() / ".cache" / "huggingface"))
    model_subdir = "models--" + model_name.replace("/", "--")
    source_model_dir = source_hf / "hub" / model_subdir
    tmpfs_root = Path(tmpfs_hf_home)
    tmpfs_model_dir = tmpfs_root / "hub" / model_subdir

    if not source_model_dir.is_dir():
        logger.warning(
            f"[tmpfs] {model_name} not found at {source_model_dir}; "
            f"HF will download to {source_hf} on first use "
            f"(no tmpfs cache pre-populated)"
        )
        return None

    if tmpfs_model_dir.is_dir():
        logger.info(f"[tmpfs] {model_name} already present at {tmpfs_model_dir}; reusing")
        return str(tmpfs_root)

    needed_kb = _du_kb(source_model_dir)
    avail_kb = _avail_kb(Path("/dev/shm"))
    if needed_kb is None or avail_kb is None:
        logger.warning(
            f"[tmpfs] couldn't measure space (need={needed_kb}, avail={avail_kb}); "
            f"skipping tmpfs cache to be safe"
        )
        return None

    required_kb = int(needed_kb * headroom_factor)
    if avail_kb < required_kb:
        # Loud warning per the pattern in run_pipeline.sh: silent fallback
        # to NFS results in multi-hour mmap stalls that are easy to miss.
        bar = "[tmpfs] " + "=" * 60
        logger.warning("")
        logger.warning(bar)
        logger.warning("[tmpfs]  WARNING: insufficient /dev/shm space — tmpfs cache DISABLED")
        logger.warning(f"[tmpfs]  need {required_kb}kB ({headroom_factor:.1f}x model), have {avail_kb}kB")
        logger.warning(f"[tmpfs]  Falling back to source HF cache: {source_hf}")
        logger.warning(f"[tmpfs]  If that is on NFS or other slow storage, expect model loads to")
        logger.warning(f"[tmpfs]  hang for HOURS on cold mmap reads of the safetensors shards.")
        logger.warning(f"[tmpfs]  Fix: increase --shm-size on the container, or free /dev/shm.")
        logger.warning(bar)
        logger.warning("")
        return None

    logger.info(
        f"[tmpfs] copying {model_name} ({needed_kb // 1024} MB) "
        f"from {source_model_dir} to {tmpfs_model_dir} ..."
    )
    tmpfs_root.mkdir(parents=True, exist_ok=True)
    (tmpfs_root / "hub").mkdir(parents=True, exist_ok=True)
    try:
        # cp -r equivalent.  copytree copies the dir's contents into the
        # destination so we pass `dst = .../hub/<model_subdir>` to mirror
        # the structure run_pipeline.sh ends up with.
        shutil.copytree(source_model_dir, tmpfs_model_dir, symlinks=True,
                        dirs_exist_ok=False)
    except (OSError, shutil.Error) as e:
        logger.warning(
            f"[tmpfs] copy failed ({e}); falling back to {source_hf}"
        )
        # Best-effort cleanup of any partial copy
        try:
            shutil.rmtree(tmpfs_model_dir, ignore_errors=True)
        except OSError:
            pass
        return None

    logger.info(f"[tmpfs] copy complete; HF_HOME={tmpfs_root}")
    return str(tmpfs_root)


def setup_tmpdir_if_unset() -> str:
    """Set TMPDIR to /dev/shm when unset, mirroring run_pipeline.sh.

    Returns the resolved TMPDIR after the (possible) mutation.

    The steering driver writes its records.jsonl staging files via
    atomic_io.py, which honours TMPDIR.  Pointing TMPDIR at /dev/shm
    avoids small-container-/tmp fill-ups when many workers flush
    concurrently.
    """
    if os.environ.get("TMPDIR"):
        logger.info(f"[tmpfs] TMPDIR={os.environ['TMPDIR']} (preserved from environment)")
        return os.environ["TMPDIR"]

    if Path("/dev/shm").is_dir():
        os.environ["TMPDIR"] = "/dev/shm"
        logger.info("[tmpfs] TMPDIR=/dev/shm (avoid filling small container /tmp)")
        return "/dev/shm"

    os.environ["TMPDIR"] = "/tmp"
    return "/tmp"
