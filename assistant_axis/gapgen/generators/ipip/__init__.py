"""Workstream 7: the IPIP behavior-item generator (generator id ``ipip``).

Plan: ``reports/trait_gap_generation/coding_plan_07_behaviour_items.md`` (from ``07_behaviour_items.md`` and
Roger's answers of 2026-10-10).  The generator scrapes the public-domain IPIP self-report items ("Get chores
done right away") with their scale keys from three pages of ipip.ori.org, clusters them by embedding (OpenAI
``text-embedding-3-large`` and the local EmbeddingGemma, each item read as "I <text>"), keeps the clusters both
embedders reproduce, splits a cluster into two poles where the scale keys say it is bipolar, and has Haiku 5.5
name every pole twice: blind (the items alone) and hinted (with the IPIP construct names).  The named poles go to
the platform as candidates (``Candidate``, ``start_run``, ``submit_candidates``); trait-hood (M1) and novelty
(M3) are the platform's CLIs.

Modules: :mod:`.sources` (what is fetched), :mod:`.download` (fetch, record), :mod:`.ingest` (parse, join,
``items.jsonl``), :mod:`.cluster` (embeddings, clusters, consensus, poles, purity), :mod:`.naming` (the blind and
hinted naming calls), :mod:`.granularity` (the overlap readings that decide between ~350 and ~150 clusters),
:mod:`.submit` (candidates, the downstream estimate, submission), :mod:`.evaluate` and :mod:`.report` (the run's
evaluation and readout).  The CLI is ``data_analysis/gap_generation/ipip_generator.py``.
"""
from __future__ import annotations

from pathlib import Path

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL

GENERATOR = "ipip"
#: Tracked outputs: the item table, the sources manifest, the cluster tables, the granularity readings.
IPIP_DIR = DATA_CANDIDATES / "ipip"
ITEMS_PATH = IPIP_DIR / "items.jsonl"
SOURCES_MANIFEST_PATH = IPIP_DIR / "sources_manifest.json"
INGEST_COUNTS_PATH = IPIP_DIR / "ingest_counts.json"
NAMING_USAGE_PATH = IPIP_DIR / "naming_usage.json"
NAMING_RESPONSES_PATH = IPIP_DIR / "naming_responses.jsonl"
GRANULARITY_DIR = IPIP_DIR / "granularity"
GRANULARITY_READOUT_JSON = IPIP_DIR / "granularity_readout.json"
GRANULARITY_READOUT_MD = IPIP_DIR / "granularity_readout.md"
#: Git-ignored: the downloaded HTML pages and their manifest.
EXTERNAL_DIR = DATA_EXTERNAL / "ipip"
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"
#: The two granularities the pilot compares (plan § 1: ~350 and ~150 clusters).
GRANULARITIES: tuple[int, ...] = (350, 150)


def clusters_path(granularity: int, root: Path | None = None) -> Path:
    """``data/candidates/ipip/clusters_g<granularity>.jsonl`` (or under ``root``)."""
    return Path(root or IPIP_DIR) / f"clusters_g{int(granularity)}.jsonl"


__all__ = ["GENERATOR", "IPIP_DIR", "ITEMS_PATH", "SOURCES_MANIFEST_PATH", "INGEST_COUNTS_PATH", "NAMING_USAGE_PATH",
           "NAMING_RESPONSES_PATH", "GRANULARITY_DIR", "GRANULARITY_READOUT_JSON", "GRANULARITY_READOUT_MD",
           "EXTERNAL_DIR", "DOWNLOAD_MANIFEST_NAME", "GRANULARITIES", "clusters_path"]
