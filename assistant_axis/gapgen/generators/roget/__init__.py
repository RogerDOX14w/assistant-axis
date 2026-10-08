"""Workstream 2: Roget heads as a coverage map, WordNet clusters as a sibling stream.

Plan: ``reports/trait_gap_generation/coding_plan_02_roget_wordnet.md`` (its last section, the
2026-10-08 revision, overrides the earlier ones).  CLI:
``data_analysis/gap_generation/roget_generate.py``.

Modules:

* :mod:`.parse`: download, checksum and parser of Roget's Thesaurus (1911, Gutenberg #10681);
  ``load_heads`` reads ``data/candidates/roget/heads.json``.
* :mod:`.pairs`: opposed heads by rule (``head_pairs.json``).
* :mod:`.mapping`: the corpus and queue labels placed on heads, lexical and semantic routes
  (``label_heads.json``).
* :mod:`.coverage`: the coverage map (``roget_coverage.{json,md}``).
* :mod:`.harvest`: candidate words from the gap heads, ``candidates.jsonl`` per run.
* :mod:`.wn_clusters`: Open English WordNet lookups and the ``wn_clusters`` sibling stream.

The Roget coordinate later workstreams read: ``label_heads.json`` (stem -> ``primary``,
``secondary``) and ``head_pairs.json`` (head -> ``partner``, ``kind``); registry ``source_ref``
``roget:<head id>`` (one Candidate per head) and ``oewn:<synset id>``.

The functions ``coverage.coverage`` and ``harvest.harvest`` are not re-exported here: their
names are the submodules' names.
"""
from .coverage import CoverageReport, load_coverage
from .harvest import HarvestConfig
from .parse import RogetIndex, load_heads

__all__ = ["CoverageReport", "HarvestConfig", "RogetIndex", "load_coverage", "load_heads"]
