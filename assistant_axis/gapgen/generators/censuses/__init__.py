"""Workstream 1: the psycholexical-census generator (generator id ``censuses``).

Plan: ``reports/trait_gap_generation/coding_plan_01_censuses.md`` (its last section, the
revision for the interface as built, overrides the earlier ones).  The generator reads two
census word lists, the Trait Descriptive Adjectives (TDA, Condon, Coughlin & Weston 2022,
CC0) and the Allport-Odbert (1936) list as digitised on OSF (CC BY 4.0), into one table
(``census_table.jsonl``), and submits staged runs of it to the candidate registry through
the platform's registry API (``Candidate``, ``start_run``, ``submit_candidates``).  It makes
no paid call: filtering (M1) and novelty scoring (M3) are the platform's CLIs.

Modules: :mod:`.sources` (what is fetched), :mod:`.download` (fetch and verify),
:mod:`.ingest` (parse, clean, table), :mod:`.glosshint` (OEWN sense hints), :mod:`.submit`
(stages, sampling, estimate, submission), :mod:`.evaluate` and :mod:`.report` (string
ceiling, known-label pass, counts, readout).

Frozen interface for other generators::

    from assistant_axis.gapgen.generators.censuses import load_census_table, CENSUS_TABLE_PATH
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL

GENERATOR = "censuses"
CENSUS_DIR = DATA_CANDIDATES / "censuses"
CENSUS_TABLE_PATH = CENSUS_DIR / "census_table.jsonl"
SOURCES_MANIFEST_PATH = CENSUS_DIR / "sources_manifest.json"
INGEST_COUNTS_PATH = CENSUS_DIR / "ingest_counts.json"
WORDLISTS_DIR = DATA_EXTERNAL / "wordlists"
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"

from .ingest import TableRow, load_census_table  # noqa: E402

__all__ = ["GENERATOR", "CENSUS_DIR", "CENSUS_TABLE_PATH", "SOURCES_MANIFEST_PATH", "INGEST_COUNTS_PATH",
           "WORDLISTS_DIR", "DOWNLOAD_MANIFEST_NAME", "TableRow", "load_census_table"]
