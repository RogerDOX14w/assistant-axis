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
