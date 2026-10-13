"""Workstream 9: the structural generators (generator id ``structural``).

Plan: ``reports/trait_gap_generation/coding_plan_09_structural_generators.md`` (authoritative), from
``09_structural_generators.md``.  Two generators in one package:

* **A, the classical schemes** (:mod:`.classical`, :mod:`.modernise`): five tables typed by hand (Aristotle's mean,
  Theophrastus' Characters, the sins and the virtues, the VIA strengths with Niemiec's overuse and underuse names,
  Murray's needs) under ``data/candidates/structural/classical/``, modernised by Haiku 5.5 (1-3 modern labels and a
  gloss per row).  The VIA rows are unreadable until every one carries ``verified_by`` (the gate).
* **B, the structural operators** (:mod:`.operators`): one Haiku 5.5 call per corpus trait asks where the trait sits
  on its own scale (``position``) and for its ``opposite``, ``excess``, ``deficiency``, the same disposition aimed
  at other targets (``retarget``) and in other modes (``remode``).  The call never sees the trait's
  ``negative_label`` or its arrangement's members (the opposite runs blind).  The user, the operator and the
  developer are added as targets only for the traits at ``alignment_score`` >= ``--principal-min-score`` (default 3,
  stage 1: 108 traits on 2026-10-13).

Both emit structural metadata (a role in a structure and its siblings) in the generator's own table
(:mod:`.postprocess`, ``operator_table.jsonl``) and in each candidate's ``source_ref`` and ``partner_hint``; the
``position`` answers go to a side table (:mod:`.sidetable`), never into a trait file.  M1 and M3 (the platform's
CLIs, printed by ``submit``) filter and score what is submitted.

Frozen interface (for the pairing review, the tangle pass and plan 11)::

    from assistant_axis.gapgen.generators.structural import (load_operator_table, OPERATOR_TABLE_PATH,
                                                             load_position_table, POSITION_TABLE_PATH)

The table rows (``schema_version`` 1) carry ``roles``, ``siblings``, ``sources``, ``n_sources`` and the membership
tags of every distinct label; the side table the ``position`` and ``negative_label_check`` of every corpus trait
operated on.  Fields are added, never renamed, without a schema bump.
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES

GENERATOR = "structural"
STRUCTURAL_DIR = DATA_CANDIDATES / "structural"
CLASSICAL_DIR = STRUCTURAL_DIR / "classical"
CLASSICAL_MODERN_PATH = STRUCTURAL_DIR / "classical_modern.jsonl"
OPERATOR_TABLE_PATH = STRUCTURAL_DIR / "operator_table.jsonl"
POSITION_TABLE_PATH = STRUCTURAL_DIR / "position_table.jsonl"
MISMATCH_PATH = STRUCTURAL_DIR / "negative_label_mismatches.md"
EVALUATION_PATH = STRUCTURAL_DIR / "evaluation.json"
#: Every paid answer of a run, appended before it is parsed (``runs/structural/<run_id>/responses.jsonl``).
RESPONSES_NAME = "responses.jsonl"
SCHEMA_VERSION = 1

#: The frozen interface's functions, imported from their modules on first use.
LAZY_EXPORTS: dict[str, str] = {"load_operator_table": "postprocess", "load_position_table": "sidetable"}


def __getattr__(name: str):
    if name in LAZY_EXPORTS:
        import importlib
        return getattr(importlib.import_module(f"{__name__}.{LAZY_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GENERATOR", "STRUCTURAL_DIR", "CLASSICAL_DIR", "CLASSICAL_MODERN_PATH", "OPERATOR_TABLE_PATH",
           "POSITION_TABLE_PATH", "MISMATCH_PATH", "EVALUATION_PATH", "RESPONSES_NAME", "SCHEMA_VERSION",
           "load_operator_table", "load_position_table"]
