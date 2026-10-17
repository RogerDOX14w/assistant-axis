"""Workstream 5: the corpus-frames generator (generator id ``corpus_frames``).

Plan: ``reports/trait_gap_generation/coding_plan_05_corpus_frames.md`` (authoritative), from ``05_corpus_frames.md``.
The generator harvests the words English speakers use of people by counting the **fillers** of **lexical frames**
("a very X person", "known for his X", "an incorrigible X"): one ranking per frame, the frames merged by
reciprocal-rank fusion so that no frame dominates the union by count.  Two kinds of source, both in the first build
(Roger, 2026-10-14, open decisions 1 and 2):

* the **Google Books n-grams** (v3, 20200217, English; CC BY 3.0): the 3- and 4-gram shards that hold each frame's
  fixed prefix are located by head-peeking (:mod:`.books`) and streamed once, both tiers of the bank
  (:mod:`.frames`), keeping only the matching lines (``data/external/books_ngrams/``, git-ignored);
* two **text corpora** of curated character descriptions (:mod:`.text`): PIPPA's ``bot_description`` (Apache-2.0)
  and the 5,755 character cards of ``hieunguyenminh/roleplay`` (CC BY 4.0), read with looser regex frames
  (adjective lists in descriptive passages count) and the filler-first frames Books cannot locate ("X to a fault",
  "X by nature", "X at heart").  Regex only, no spaCy.

The table (:mod:`.table`) folds every filler through the platform's noun helper (``assistant_axis.gapgen.nouns``:
British to US spelling, a noun of disposition to its adjective) and ranks it within each frame by document
frequency and by lift; :mod:`.evaluate` measures the recovery of our labels, each frame's yield and net filter
after the pilot; :mod:`.submit` submits one candidate per stem (the platform's M1 and M3 do the filtering and
scoring; the platform adds a relabelled noun's adjective as a linked sibling).  **The generator makes no LLM call**,
so every run's ``usage.json`` has zero calls.

Frozen interface (plan, "Frozen interface")::

    from assistant_axis.gapgen.generators.corpus_frames import load_frames_table, TABLE_PATH, person_frequency
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL

GENERATOR = "corpus_frames"
FRAMES_DIR = DATA_CANDIDATES / "corpus_frames"
#: The table: one row per stem (git-ignored; its sha256 goes into ``evaluation.json`` and every ``run.json``).
TABLE_PATH = FRAMES_DIR / "frames_table.jsonl"
SHARD_PLAN_PATH = FRAMES_DIR / "shard_plan.json"
FRAME_STATS_PATH = FRAMES_DIR / "frame_stats.json"
EVALUATION_PATH = FRAMES_DIR / "evaluation.json"
CURVES_PNG_PATH = FRAMES_DIR / "recovery_curves.png"
READOUT_PATH = FRAMES_DIR / "readout.md"
#: The tracked copy of both download manifests (the Books stream and the text corpora), as the IPIP generator keeps
#: one: the manifests themselves live beside the git-ignored files.
SOURCES_MANIFEST_PATH = FRAMES_DIR / "sources_manifest.json"
#: The Books extracts (``<frame_id>.tsv``, the kept lines) and their manifest (git-ignored with ``data/external``).
EXTERNAL_DIR = DATA_EXTERNAL / "books_ngrams"
#: The text corpora's downloads and extracts (git-ignored with ``data/external``).
TEXT_EXTERNAL_DIR = DATA_EXTERNAL / "corpus_frames"
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"

#: The frozen interface's names, imported from :mod:`.table` on first use.
LAZY_EXPORTS: dict[str, str] = {"load_frames_table": "table", "person_frequency": "table", "PersonFreq": "table"}


def __getattr__(name: str):
    if name in LAZY_EXPORTS:
        import importlib
        return getattr(importlib.import_module(f"{__name__}.{LAZY_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["GENERATOR", "FRAMES_DIR", "TABLE_PATH", "SHARD_PLAN_PATH", "FRAME_STATS_PATH", "EVALUATION_PATH",
           "CURVES_PNG_PATH", "READOUT_PATH", "SOURCES_MANIFEST_PATH", "EXTERNAL_DIR", "TEXT_EXTERNAL_DIR",
           "DOWNLOAD_MANIFEST_NAME", "load_frames_table", "person_frequency", "PersonFreq"]
