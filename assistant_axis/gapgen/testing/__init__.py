"""Workstream 13: generator testing and saturation (``reports/trait_gap_generation/coding_plan_13_generator_testing.md``).

This package generates nothing and judges nothing new: it reads what the platform recorded (the registry, the review
app's logs, the review graph, the recovery harness's batches) and prints one table per generator, the dashboard.  The
CLI is ``data_analysis/gap_generation/generator_dashboard.py``; every output goes under ``data/candidates/testing/``.

Modules: ``independence`` (each generator's class and mechanism), ``review_minutes`` (Roger's review rate and the
promote share), ``repetition`` (pre-handled terms), ``concepts`` (concept units from the review graph, and their
agreement with Roger's decisions), ``estimators`` (Chapman, Chao2, Good-Turing coverage, accumulation curves),
``simulate`` (the estimators' sanity check), ``recovery_extras`` (the strict column, pair recovery, recall at N,
the pooled harness's per-generator figures), ``dashboard`` (the table and the stop rule), ``paraphrase_set`` (the
matcher sanity check).
"""
from __future__ import annotations

from ..paths import DATA_CANDIDATES

#: Every output of this workstream (tracked, enveloped, rebuilt by ``generator_dashboard.py dashboard``).
TESTING_DIR = DATA_CANDIDATES / "testing"
DASHBOARD_JSON_PATH = TESTING_DIR / "dashboard.json"
DASHBOARD_MD_PATH = TESTING_DIR / "dashboard.md"
PARAPHRASE_SET_DIR = TESTING_DIR / "paraphrase_set"

#: The frozen interface (plan 13, "Frozen interface"): for plans 04 and 09's wave sizing and the next dashboard
#: refreshes.  ``ReviewRate`` / ``review_rate`` / ``pooled_review_rate`` measure Roger's review from a batch's logs;
#: ``PromoteShare`` / ``promote_share`` give the share per group (decision 3) with the per-term share beside it;
#: ``GeneratorRow`` is the dashboard's row (``schema_version`` 1) and ``load_dashboard`` reads the last one written.
#: Fields are added, never renamed, without a schema bump.
FROZEN_INTERFACE: tuple[str, ...] = ("review_rate", "ReviewRate", "pooled_review_rate", "promote_share", "PromoteShare",
                                     "load_dashboard", "DASHBOARD_JSON_PATH", "GeneratorRow")

from .review_minutes import PromoteShare, ReviewRate, pooled_review_rate, promote_share, review_rate  # noqa: E402
from .dashboard import GeneratorRow, load_dashboard  # noqa: E402

__all__ = ["TESTING_DIR", "DASHBOARD_JSON_PATH", "DASHBOARD_MD_PATH", "PARAPHRASE_SET_DIR", "FROZEN_INTERFACE",
           *FROZEN_INTERFACE]
