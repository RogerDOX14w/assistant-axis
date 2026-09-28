"""Filesystem layout of the trait-gap generation platform.

Every path the platform reads or writes is derived here, and every one of
them lies inside the repository (``test_gapgen_paths.py`` asserts it).  In
particular the two third-party downloads are pinned in-tree, because both
libraries default to a directory under the user's home:

* Open English WordNet (the ``wn`` package, default ``~/.wn_data``) lives in
  :func:`wn_data_dir` = ``data/external/wn/``;
* Hugging Face models (M2, default ``~/.cache/huggingface``) live in
  :func:`hf_cache_dir` = ``data/external/hf/``.

``data/external/`` and ``data/candidates/cache/`` are gitignored, as is the
live registry log ``data/candidates/registry.jsonl`` (review amendment 3 of
``reports/trait_gap_generation/coding_plan_platform.md``); the tracked copy
of the registry is the snapshot ``registry.snapshot.jsonl`` written by
``gap_registry.py compact``.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
DATA_CANDIDATES = DATA_DIR / "candidates"
DATA_EXTERNAL = DATA_DIR / "external"

REGISTRY_PATH = DATA_CANDIDATES / "registry.jsonl"
REGISTRY_SNAPSHOT_NAME = "registry.snapshot.jsonl"
REGISTRY_SNAPSHOT_PATH = DATA_CANDIDATES / REGISTRY_SNAPSHOT_NAME
METRIC_CONFIG_PATH = DATA_CANDIDATES / "metric_config.json"
CORPUS_REGIONS_PATH = DATA_CANDIDATES / "corpus_regions.json"
VALIDATION_DIR = DATA_CANDIDATES / "validation"
SEED_QUEUE_PATH = DATA_DIR / "seed_queue.json"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")


def check_id(value: str, what: str = "id") -> str:
    """Refuse ids that could escape their directory (slashes, ``..``, blanks).

    Generator names, run ids and batch ids become directory names; anything
    outside ``[A-Za-z0-9._+-]`` (first character alphanumeric) is rejected.
    """
    if not isinstance(value, str) or not _ID_RE.match(value) or ".." in value:
        raise ValueError(f"invalid {what} {value!r}: use letters, digits, '.', '_', '+', '-'")
    return value


def runs_root(candidates_dir: Path | None = None) -> Path:
    return (candidates_dir or DATA_CANDIDATES) / "runs"


def run_dir(generator: str, run_id: str, *, candidates_dir: Path | None = None) -> Path:
    """``data/candidates/runs/<generator>/<run_id>/`` (not created here)."""
    return runs_root(candidates_dir) / check_id(generator, "generator") / check_id(run_id, "run_id")


def filter_dir(batch_id: str, *, candidates_dir: Path | None = None) -> Path:
    """``data/candidates/filter/<batch_id>/`` (not created here)."""
    return (candidates_dir or DATA_CANDIDATES) / "filter" / check_id(batch_id, "batch_id")


def novelty_dir(batch_id: str, *, candidates_dir: Path | None = None) -> Path:
    return (candidates_dir or DATA_CANDIDATES) / "novelty" / check_id(batch_id, "batch_id")


def hf_cache_dir() -> Path:
    """In-tree Hugging Face cache (``data/external/hf``); M2's ``LocalEmbedder``
    passes it as ``cache_dir`` so no model lands under the home directory."""
    return DATA_EXTERNAL / "hf"


def wn_data_dir() -> Path:
    """In-tree data directory for the ``wn`` package (``data/external/wn``)."""
    return DATA_EXTERNAL / "wn"


def all_paths() -> dict[str, Path]:
    """Every fixed path above (the test checks each resolves inside the repo)."""
    return {
        "DATA_DIR": DATA_DIR,
        "DATA_CANDIDATES": DATA_CANDIDATES,
        "DATA_EXTERNAL": DATA_EXTERNAL,
        "REGISTRY_PATH": REGISTRY_PATH,
        "REGISTRY_SNAPSHOT_PATH": REGISTRY_SNAPSHOT_PATH,
        "METRIC_CONFIG_PATH": METRIC_CONFIG_PATH,
        "CORPUS_REGIONS_PATH": CORPUS_REGIONS_PATH,
        "VALIDATION_DIR": VALIDATION_DIR,
        "SEED_QUEUE_PATH": SEED_QUEUE_PATH,
        "hf_cache_dir": hf_cache_dir(),
        "wn_data_dir": wn_data_dir(),
        "runs_root": runs_root(),
        "run_dir": run_dir("g", "r"),
        "filter_dir": filter_dir("b"),
        "novelty_dir": novelty_dir("b"),
    }
