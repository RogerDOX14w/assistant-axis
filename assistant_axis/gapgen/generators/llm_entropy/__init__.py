"""Workstream 6: LLM generation with injected entropy (generator id ``llm_entropy``).

Plan: ``reports/trait_gap_generation/coding_plan_06_llm_entropy.md`` (authoritative), from
``06_llm_entropy_generation.md``.  One generator, five prompt families, each carrying a constraint the model cannot
satisfy from its mode, so that the entropy comes from outside the model and the model supplies vocabulary and
glosses:

* **(a)** a domain x mode grid (30 life domains x 7 ways a trait shows, :mod:`.prompts`);
* **(b)** person seeding: one real or fictional person drawn at random from Wikidata per call (:mod:`.seeds`).
  **Person data is held in memory only** (plan section 5a, Roger's decision 3): the seeds and the raw answers live
  in the one process that fetches, asks, collects and redacts; tracked files carry opaque seed ids (``b:r0137``,
  ``b:f0042``) and redacted text only;
* **(c)** ten languages, the prompts translations of one pinned English master, each answer back-translated to an
  English label of at most four words (:mod:`.prompts`, :mod:`.calls`);
* **(d)** verbalized sampling, a wrapper on (a) and (e): stage 1 asks for a probability per item, stage 2 (a fresh
  call quoting stage 1) for items below 0.03;
* **(e)** spelling constraints (initial letters and bigrams, suffixes, prefixes, three multi-word frames).

The platform's M1 (the trait-hood filter) and M3 (the novelty scorer) filter and score what :mod:`.submit` sends.

Frozen interface (for plan 13's dashboard and the pairing review)::

    from assistant_axis.gapgen.generators.llm_entropy import (load_items_table, ITEMS_TABLE_PATH, load_collapse,
                                                              COLLAPSE_PATH, PERSON_SEEDS_FETCH_PATH, EntropyRunner)

The items-table rows (``schema_version`` 1), the collapse payload per family, the seeds' fetch record and the
generator-side Batches runner.  Fields are added, never renamed, without a schema bump.  In the registry a
candidate's family, prompt and language are readable from its ``source_ref``
(``llm_entropy:<prompt id>:r<run>``, :func:`.submit.parse_source_ref`) and its antonym from ``partner_hint``.
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES

GENERATOR = "llm_entropy"
ENTROPY_DIR = DATA_CANDIDATES / "llm_entropy"
#: The tracked record of every person-seed fetch (counts, requests, licence, capture date; per opaque seed id only
#: its kind and birth-era band).  There is **no seed file** (plan section 5a): names and descriptions never reach
#: the drive.
PERSON_SEEDS_FETCH_PATH = ENTROPY_DIR / "person_seeds_fetch.json"
#: The ten (c) prompts: translations of the pinned English master, with their hashes and back-translations.
MULTILINGUAL_PROMPTS_PATH = ENTROPY_DIR / "multilingual_prompts.json"
#: Usage of the translation commands (``translate-prompts``), beside the file they write (cumulative).
MULTILINGUAL_USAGE_PATH = ENTROPY_DIR / "multilingual_prompts_usage.json"
ITEMS_TABLE_PATH = ENTROPY_DIR / "items_table.jsonl"
COLLAPSE_PATH = ENTROPY_DIR / "collapse.json"
EVALUATION_PATH = ENTROPY_DIR / "evaluation.json"
ROLES_REPORT_PATH = ENTROPY_DIR / "roles_report.md"
#: Every paid answer of a run, appended before it is parsed (``runs/llm_entropy/<run_id>/responses.jsonl``).
RESPONSES_NAME = "responses.jsonl"
#: The Message Batches state of a run (batch ids and custom ids only).
BATCHES_NAME = "batches.json"
SCHEMA_VERSION = 1

#: The frozen interface's names, imported from their modules on first use.
LAZY_EXPORTS: dict[str, str] = {"load_items_table": "table", "load_collapse": "collapse", "EntropyRunner": "calls"}


def __getattr__(name: str):
    if name in LAZY_EXPORTS:
        import importlib
        return getattr(importlib.import_module(f"{__name__}.{LAZY_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GENERATOR", "ENTROPY_DIR", "PERSON_SEEDS_FETCH_PATH", "MULTILINGUAL_PROMPTS_PATH", "MULTILINGUAL_USAGE_PATH",
           "ITEMS_TABLE_PATH", "COLLAPSE_PATH", "EVALUATION_PATH", "ROLES_REPORT_PATH", "RESPONSES_NAME",
           "BATCHES_NAME", "SCHEMA_VERSION", "load_items_table", "load_collapse", "EntropyRunner"]
