"""Workstream 3: the base-model generator (generator id ``base_model``).

Plan: ``reports/trait_gap_generation/coding_plan_03_base_model.md`` (authoritative), from
``03_base_model_generator.md``.  A local *pretrained* (not instruction-tuned) model, ``Qwen/Qwen3-8B-Base``,
continues short person-description prompts (lists, glossaries, a Wikipedia biography's opening, a contrast
sentence, an occupation, an AI system); trait candidates are parsed out of the continuations, counted, and
submitted to the candidate registry.  Every prompt is seeded from external sources only (the TDA rows of the
census table, ``wiki_bio``, O*NET occupation titles, OEWN common nouns), never from the corpus, so the
generator cannot see or imitate our list.  The generator makes no paid call: filtering (M1) and novelty
scoring (M3) are the platform's CLIs; the sampler's tokens are charged to a ``MultiModelUsage`` at a zero
rate so ``usage.json`` records the volume.

Modules: :mod:`.sources` (what is fetched), :mod:`.download` (fetch, verify, manifest), :mod:`.seeds` (the
seed bundle), :mod:`.prompts` (six families, ``PROMPTS_VERSION``), :mod:`.sampler` and :mod:`.bench` (the
local model), :mod:`.parse` (items out of a continuation), :mod:`.table` (one row per stem),
:mod:`.sense` (the gloss sense, settled before M1: the generator's only paid call, QUESTIONS 56),
:mod:`.diversity` (the frozen harness), :mod:`.submit` (estimate, guard, submission), :mod:`.waves`
(the review-hour waves: count-bucket x family cells, plan 03 decision (f)),
:mod:`.evaluate` and :mod:`.report` (the pilot readout).

Layout: rounds are numbered; round 0 is the temperature shakedown, rounds 1 and 2 the pilot's round A and
its iteration round, later rounds the full run.  Raw samples (which may echo biography text) live under the
gitignored ``data/candidates/cache/base_model/round<N>/``; the tracked tables and stats under
``data/candidates/base_model/`` carry no biography text.

Frozen interface for other generators::

    from assistant_axis.gapgen.generators.base_model import diversity
    diversity.rarefaction(stems_in_order, step)    diversity.chao1(counts)
    diversity.collapse_index(counts, top=50)       diversity.string_recovery(stems, corpus_stems, renamed)
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL

GENERATOR = "base_model"
MODEL_ID = "Qwen/Qwen3-8B-Base"
BASE_DIR = DATA_CANDIDATES / "base_model"
SAMPLES_DIR = DATA_CANDIDATES / "cache" / "base_model"
SOURCES_MANIFEST_PATH = BASE_DIR / "sources_manifest.json"
WIKIBIO_DIR = DATA_EXTERNAL / "wikibio"
ONET_DIR = DATA_EXTERNAL / "onet"
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"
#: The plan's single name; the per-round tables below replace it (two pilot rounds are compared side by side).
TABLE_PATH = BASE_DIR / "candidate_table.jsonl"


def _t(temperature: Optional[float]) -> str:
    return "" if temperature is None else f"_t{float(temperature):g}"


def round_dir(round_n: int) -> Path:
    """``data/candidates/cache/base_model/round<N>/`` (gitignored): samples, usage, sampling record."""
    return SAMPLES_DIR / f"round{int(round_n)}"


def samples_path(round_n: int) -> Path:
    return round_dir(round_n) / "samples.jsonl"


def table_path(round_n: int, *, temperature: Optional[float] = None) -> Path:
    """The tracked candidate table of a round (one row per stem, no biography text).  The temperature
    shakedown's per-temperature tables stay in the gitignored round directory."""
    if temperature is not None:
        return round_dir(round_n) / f"candidate_table{_t(temperature)}.jsonl"
    return BASE_DIR / f"candidate_table_round{int(round_n)}.jsonl"


def stats_path(round_n: int, *, temperature: Optional[float] = None) -> Path:
    """The tracked diversity stats of a round (``json_metadata`` envelope)."""
    return BASE_DIR / f"stats_round{int(round_n)}{_t(temperature)}.json"


def sense_usage_path(round_n: int, base_dir: Path = BASE_DIR) -> Path:
    """The tracked usage record of a round's gloss-sense step (the screen's embeddings and the paid calls),
    cumulative over the round's sessions, beside the round's tracked table (code review 2026-10-12, B2: until then it
    lived only in the gitignored round directory, as ``sense.USAGE_NAME``)."""
    return Path(base_dir) / f"gloss_sense_usage_round{int(round_n)}.json"


from . import diversity  # noqa: E402  (the frozen harness, re-exported)

__all__ = ["GENERATOR", "MODEL_ID", "BASE_DIR", "SAMPLES_DIR", "SOURCES_MANIFEST_PATH", "WIKIBIO_DIR", "ONET_DIR",
           "DOWNLOAD_MANIFEST_NAME", "TABLE_PATH", "round_dir", "samples_path", "table_path", "stats_path",
           "sense_usage_path", "diversity"]
