"""Trait-gap generation platform (``reports/trait_gap_generation/coding_plan_platform.md``).

Milestone M1: candidate registry, trait-hood filter, promotion.  This package
re-exports the frozen interface that generator workstreams depend on; M2 and
M3 add the embedding, calibration and novelty names.

Generators use only these names::

    from assistant_axis.gapgen import Candidate, start_run, submit_candidates

and then run ``data_analysis/gap_generation/traithood_filter.py --run G/R``.
Importing this package, or any module in it, pins the ``wn`` data directory
to ``data/external/wn`` (``paths.pin_wn_data_dir``), whether or not ``wn`` is
already imported.
"""
from .paths import pin_wn_data_dir as _pin_wn_data_dir

_pin_wn_data_dir()

from .normalize import (  # noqa: E402
    DECISIONS, NOVELTY_FLAGS, REGION_VOCAB, RELATIONS, REVIEW_STATUSES, TAG_VOCAB, VERDICTS,
    Normalized, make_key, normalize_candidate,
)
from .paths import (
    DATA_CANDIDATES, DATA_EXTERNAL, METRIC_CONFIG_PATH, REGISTRY_PATH, REGISTRY_SNAPSHOT_PATH,
    hf_cache_dir, run_dir, wn_data_dir,
)
from .registry import (
    Candidate, Registry, SubmitReport, compact, holding_list, records_for_status, submit_candidates,
)
from .runs import RunContext, start_run

__all__ = [
    # frozen interface (generators)
    "Candidate", "SubmitReport", "RunContext", "start_run", "submit_candidates", "REGISTRY_PATH",
    # registry access
    "Registry", "compact", "holding_list", "records_for_status",
    # vocabularies and normalisation
    "VERDICTS", "TAG_VOCAB", "REGION_VOCAB", "DECISIONS", "NOVELTY_FLAGS", "RELATIONS",
    "REVIEW_STATUSES", "Normalized", "normalize_candidate", "make_key",
    # paths
    "DATA_CANDIDATES", "DATA_EXTERNAL", "METRIC_CONFIG_PATH", "REGISTRY_SNAPSHOT_PATH",
    "hf_cache_dir", "run_dir", "wn_data_dir",
]
