"""Generator B: lists of professions (generator id ``professions``; coding plan 16, build-order step 2).

Plan: ``reports/trait_gap_generation/coding_plan_16_role_generators.md`` (authoritative: § 5b, § 6.6, § 7, § 7a.5,
§ 7d), from ``16_role_generators.md`` § 6.  Not a sweep of a classification but a **ranked pick** (Roger,
2026-10-16: keep roughly the current balance, so occupations are about half of what the role generators submit;
aim for missing ones that are common, well known and not especially similar to the corpus's):

* :mod:`.sources` - what is downloaded (O*NET 31.0 occupations, on disk; O*NET 31.0 job titles; BLS OEWS May 2025
  national estimates; optionally BLS SOC 2018 structure; ESCO occupations by its API, wave 2 only), with licences,
  manifests and the attribution that travels with every run (``ATTRIBUTION.md``);
* :mod:`.soc`, :mod:`.onet` - the table: one row per SOC 2018 broad group (459) with its detailed O*NET occupations
  and OEWS employment, and one per selected O*NET job title (the cut of § 7d: 1-2 words, no parentheses or
  abbreviations, singular, Zipf >= 3.0, not a corpus role, deduplicated, the top 300 by Zipf);
* :mod:`.lay` - the Haiku 5.5 call (rubric ``profession_lay``): the lay roles of each group or title, three
  readings combined as a union with support;
* :mod:`.rank` - familiarity (Zipf of the lay title, log10 OEWS employment) and distance from the corpus (the
  nearest corpus role by the role index, query ``role_gloss_w14``), z-scored and summed;
* :mod:`.submit` - net-new rows from the top of the ranking, metered to ``share x wave_rows / kept_share``, as role
  candidates (``entity_type="role"``, ``kind_guess="occupation"``, ``human=True``);
* :mod:`.report` - the readout: sources, the cut, recovery by string of the 162 corpus occupations, the ranking,
  the occupation share before and after.

Run directories: ``data/candidates/runs/professions/<run_id>/`` with the files named below.  The CLI is
``data_analysis/gap_generation/professions_generator.py`` (fetch, build, lay, rank, label-fit, submit, report).
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_EXTERNAL

GENERATOR = "professions"
SCHEMA_VERSION = 1

#: Files of a run directory (coding plan 16, § 5b).
TABLE_NAME = "table.jsonl"
BUILD_NAME = "build.json"
LAY_RESPONSES_NAME = "lay_responses.jsonl"
LAY_NAME = "lay.jsonl"
BATCHES_NAME = "lay_batches.json"
RANKING_NAME = "ranking.jsonl"
CANDIDATES_NAME = "candidates.jsonl"
ATTRIBUTION_NAME = "ATTRIBUTION.md"
REPORT_NAME = "report.md"
SUBMIT_REPORT_NAME = "submit_report.json"
LABEL_FIT_DIR = "label_fit"
LABEL_FIT_INPUT_NAME = "label_fit_input.jsonl"
#: The record written beside downloaded files (the shape of ``data/external/onet/DOWNLOAD_MANIFEST.json``).
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"
EXTERNAL_DIR = DATA_EXTERNAL

__all__ = ["GENERATOR", "SCHEMA_VERSION", "TABLE_NAME", "BUILD_NAME", "LAY_RESPONSES_NAME", "LAY_NAME",
           "BATCHES_NAME", "RANKING_NAME", "CANDIDATES_NAME", "ATTRIBUTION_NAME", "REPORT_NAME",
           "SUBMIT_REPORT_NAME", "LABEL_FIT_DIR", "LABEL_FIT_INPUT_NAME", "DOWNLOAD_MANIFEST_NAME", "EXTERNAL_DIR"]
