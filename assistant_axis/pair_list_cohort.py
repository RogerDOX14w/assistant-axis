"""Cohort-token derivation from pair-list filenames.

The producer scripts in ``results_analysis/`` (whitening_k_sweep.py,
gpt_vs_sonnet_scatter.py, etc.) all consume a pair-list JSON via
``--pairs <file>``.  Historically the pair-list filename encoded a
count (``pair_list_12.json``, ``pair_list_33.json``).  Because the count
changes as more axes get judged, this gave us an accidental footgun:
output filenames like ``whitening_k_sweep_slot6.json`` collided across
cohorts (the same auto-derived path was used regardless of which pair
list fed the run).

Starting May 2026, pair lists use *definition-stable* names:

- ``pair_list_di.json`` -- "axes with desc+instr judging from both GPT
  and Sonnet" (formerly ``pair_list_33.json``).
- ``pair_list_responses.json`` -- "axes with desc+instr + GPT-responses
  judging" (formerly ``pair_list_12.json``).

These names won't change as the cohorts grow.  Producer scripts pluck a
``cohort`` token from the pair-list filename and bake it into their
auto-derived output filenames so that, e.g.,
``whitening_k_sweep_di_slot6.json`` and
``whitening_k_sweep_responses_slot6.json`` are unambiguously different
files.
"""
from __future__ import annotations

from pathlib import Path


_PAIR_LIST_PREFIX = "pair_list_"


def cohort_from_pairs(pairs: str | Path) -> str:
    """Extract the cohort token from a pair-list filename.

    >>> cohort_from_pairs("pair_list_responses.json")
    'responses'
    >>> cohort_from_pairs("pair_list_di.json")
    'di'
    >>> cohort_from_pairs("/abs/path/pair_list_3_cohort_b.json")
    '3_cohort_b'
    >>> cohort_from_pairs("custom_pairs.json")
    'custom_pairs'

    Falls back to the file stem if the prefix is unrecognized so callers
    always get *some* token.
    """
    stem = Path(pairs).stem
    if stem.startswith(_PAIR_LIST_PREFIX):
        return stem[len(_PAIR_LIST_PREFIX):]
    return stem
