"""Workstream 4: the masked-LM template-fill generator (generator id ``masked_lm``).

Plan: ``reports/trait_gap_generation/coding_plan_04_masked_lm.md`` (authoritative), from ``04_masked_lm_fill.md``.
A local BERT-class fill-mask model (``roberta-large`` first; ``bert-large-cased-whole-word-masking`` and
``ModernBERT-large`` are coded for and wait on Roger's word for their downloads) fills person-describing frames
("She is [MASK] by nature", "He's habitually [MASK]", "an avowed [MASK]") and the whole ranked distribution is
kept, unioned across frames, subjects and passes:

* ``single``: one forward pass per frame instance, the full softmax at the slot (:mod:`.singlemask`);
* ``probe``: the same over the HHH probe frames (the assistant / chatbot register; Roger, plan 04 section 9.1);
* ``subword`` and ``multiword``: the beam passes that rebuild words the tokenizer splits and two-word phrases
  (:mod:`.beam`), kept at reduced K as the off-list complement (Roger, 2026-10-10, open question 1);
* ``variant_b``: Open English WordNet's adjectives and person nouns scored by pseudo-log-likelihood in a fixed
  set of frames (:mod:`.pll`, :mod:`.wordlist`), the primary route to split and multiword words.

The trait-hood **contrast score** (dispositional minus the larger of the state and physical frames,
:func:`score_words`) rides ``Candidate.score``.  The generator makes no paid call: filtering (M1) and novelty
scoring (M3) are the platform's CLIs, printed by ``submit``.

Layout: the per-model, per-pass aggregates are a cache (``data/candidates/cache/masked_lm/agg/``, gitignored);
the table, the evaluation, the curves PNG and the HHH probe readout are tracked under
``data/candidates/masked_lm/``; runs under ``data/candidates/runs/masked_lm/<run_id>/``; model weights under the
gitignored ``data/external/hf/`` (each download Roger's approval).

Frozen interface for other workstreams::

    from assistant_axis.gapgen.generators.masked_lm import load_mlm_table, MLM_TABLE_PATH, score_words
"""
from __future__ import annotations

from assistant_axis.gapgen.paths import DATA_CANDIDATES

GENERATOR = "masked_lm"
MLM_DIR = DATA_CANDIDATES / "masked_lm"
MLM_TABLE_PATH = MLM_DIR / "mlm_table.jsonl"
EVALUATION_PATH = MLM_DIR / "evaluation.json"
CURVES_PNG_PATH = MLM_DIR / "recovery_curves.png"
HHH_PROBE_PATH = MLM_DIR / "hhh_probe.md"
CENSUS_PATH = MLM_DIR / "census.json"
SOURCES_MANIFEST_PATH = MLM_DIR / "sources_manifest.json"
#: Per-model, per-pass aggregates (a cache: gitignored with the rest of ``data/candidates/cache/``).
AGG_DIR = DATA_CANDIDATES / "cache" / "masked_lm" / "agg"

#: The frozen interface's functions, imported from their modules on first use (``setup_external.py`` imports
#: :mod:`.models` for its allow patterns and should not pull in the passes).
LAZY_EXPORTS: dict[str, str] = {"load_mlm_table": "table", "score_words": "pll", "Contrast": "pll"}


def __getattr__(name: str):
    if name in LAZY_EXPORTS:
        import importlib
        return getattr(importlib.import_module(f"{__name__}.{LAZY_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ =["GENERATOR", "MLM_DIR", "MLM_TABLE_PATH", "EVALUATION_PATH", "CURVES_PNG_PATH", "HHH_PROBE_PATH",
           "CENSUS_PATH", "SOURCES_MANIFEST_PATH", "AGG_DIR", "load_mlm_table", "score_words", "Contrast"]
