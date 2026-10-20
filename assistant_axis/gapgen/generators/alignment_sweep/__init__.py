"""Workstream 8: the alignment sweep (generator id ``alignment_sweep``).

Plan: ``reports/trait_gap_generation/coding_plan_08_alignment_sweep.md`` (from ``08_alignment_sweep.md`` as Roger
greenlit it on 2026-10-10).  The generator reads documents that describe how AI assistants and agents are meant to
behave and how they fail (the OpenAI Model Spec, Anthropic's constitution, failure-mode taxonomies; variant B adds
incident lists), asks Sonnet 5.5 to turn each imperative or failure mode into a pair of dispositions (two poles, each
a label and a gloss), dedupes the glosses by embedding, and submits both poles of every surviving pair as
:class:`~assistant_axis.gapgen.Candidate` rows (``gloss_hint`` its gloss, ``partner_hint`` the other pole's
label).  The platform's CLIs then filter (M1) and score (M3) them; this generator's own paid calls are the
extraction, the mechanism rewrite, the enactability gate and the Qwen label probe.

Modules: :mod:`.sources` (what is read, licences, weights), :mod:`.fetch` (download into
``data/external/alignment_sweep/`` with a manifest), :mod:`.chunk` (headings and rows to chunks), :mod:`.extract`
(the extraction and rewrite calls), :mod:`.dedupe` (gloss embeddings, groups, partner hints), :mod:`.submit`
(candidates, the downstream estimate, the submission), :mod:`.gate` (the persona-enactability gate),
:mod:`.probe` (the Qwen label probe, DeepInfra only), :mod:`.report` (rank, readout, gold recovery) and, since
2026-10-20, :mod:`.humanize` (every sweep trait rewritten in its closest human phrasing, Roger's decision of that day,
submitted as a new run that replaces the old ones).  The CLI is ``data_analysis/gap_generation/alignment_sweep.py``.
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL

GENERATOR = "alignment_sweep"
#: Tracked inputs of the sweep: the sources manifest, the gold sets, the dedup labelled pairs.
SWEEP_DIR = DATA_CANDIDATES / "alignment_sweep"
#: Git-ignored: the fetched texts, ``chunks.jsonl`` and ``FETCH_MANIFEST.json``.
EXTERNAL_DIR = DATA_EXTERNAL / "alignment_sweep"
SOURCES_MANIFEST_PATH = SWEEP_DIR / "sources_manifest.json"
GOLD_PATH = SWEEP_DIR / "gold_alignment_traits.json"
GATE_GOLD_PATH = SWEEP_DIR / "gate_gold_items.json"
DEDUP_PAIRS_PATH = SWEEP_DIR / "dedup_labeled_pairs.json"
FETCH_MANIFEST_NAME = "FETCH_MANIFEST.json"
CHUNKS_NAME = "chunks.jsonl"

__all__ = ["GENERATOR", "SWEEP_DIR", "EXTERNAL_DIR", "SOURCES_MANIFEST_PATH", "GOLD_PATH", "GATE_GOLD_PATH",
           "DEDUP_PAIRS_PATH", "FETCH_MANIFEST_NAME", "CHUNKS_NAME"]
