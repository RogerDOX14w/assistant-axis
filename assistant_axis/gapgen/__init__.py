"""Trait-gap generation platform: the interface as built (``reports/trait_gap_generation/coding_plan_platform.md``,
"Interface as built (2026-10-08)"; frozen by the platform close-out).

A generator imports only these names and runs the platform's CLIs on what it submits (``traithood_filter.py
--run G/R``, then ``novelty_score.py score --run G/R``, then ``recovery_test.py --generator G --run-id R``)::

    from assistant_axis.gapgen import Candidate, start_run, submit_candidates

The scorer side of the earlier frozen interface (``NoveltyQuery``, ``NoveltyResult``, ``Neighbour``,
``NoveltyIndex``, ``score_novelty``, ``recovery_test``, ``RecoveryReport``, ``embed_local``) was never built: M3 is
retrieve-then-judge (``novelty.py``, ``novelty_runner.py``) and none of those names exists.

Registry API (``registry.py``, ``runs.py``):

- ``Candidate``: one word or phrase a generator proposes (surface, generator, run_id, rank, score, gloss_hint,
  sense_id, source_ref, partner_hint).
- ``start_run``: opens ``data/candidates/runs/<generator>/<run_id>/`` and returns a ``RunContext``.
- ``RunContext``: a run's directory, ``usage`` (a ``MultiModelUsage``), ``log``, ``finish`` (writes ``run.json``
  and ``usage.json``).
- ``submit_candidates``: appends candidates to the registry log, idempotent per (generator, run_id, surface,
  sense_id); with ``run=`` also writes the run's ``candidates.jsonl``.
- ``SubmitReport``: what a submission did (n_submitted, n_new, n_merged, n_unchanged, keys, invalid).
- ``read_candidates``: a run's ``candidates.jsonl`` read back as ``Candidate`` objects (``gap_registry.py submit
  --from``).
- ``CANDIDATE_FIELDS``: the fields of a ``candidates.jsonl`` line, exactly ``Candidate``'s.
- ``Registry``: the log-structured registry (``fold``, ``get``, ``update_many``, ``merge_block``).
- ``compact``: folds the log to one line per key and writes the tracked snapshot.
- ``holding_list``: rows parked on a holding list (physical, roles, states, nationalities).
- ``records_for_status``: rows matching a verdict, decision, review status, holding list, generator or run.

Vocabularies and normalisation (``normalize.py``):

- ``VERDICTS``, ``TAG_VOCAB``, ``REGION_VOCAB``, ``DECISIONS``, ``NOVELTY_FLAGS``, ``RELATIONS``,
  ``REVIEW_STATUSES``: the row's vocabularies.
- ``normalize_candidate`` / ``Normalized``: a surface to its stem and label; ``make_key``: ``f"{stem}#{sense_id}"``.

Metric configuration (``metric_config.py``):

- ``MetricConfig``: ``data/candidates/metric_config.json`` (the covered and directional settings, the live
  embedding model, ``k``, the canary texts, ``config_version``).

Paths (``paths.py``; every one inside the repository):

- ``DATA_DIR``, ``DATA_CANDIDATES``, ``DATA_EXTERNAL``: ``data/``, ``data/candidates/``, ``data/external/``.
- ``REGISTRY_PATH``: the registry log ``data/candidates/registry.jsonl`` (git-ignored: one per checkout).
- ``REGISTRY_SNAPSHOT_PATH``: its tracked compacted copy.
- ``METRIC_CONFIG_PATH``, ``CORPUS_REGIONS_PATH``, ``SEED_QUEUE_PATH``: the metric config, the corpus's regions,
  the seed queue.
- ``run_dir``, ``filter_dir``, ``novelty_dir``, ``recovery_dir``: a generator run's, an M1 batch's, an M3 batch's
  and a recovery run's directory.
- ``check_id``: refuses an id that could leave its directory.
- ``hf_cache_dir``, ``wn_data_dir``: the in-tree Hugging Face cache and WordNet data.

Embedding and WordNet (``embed.py``, ``representation.py``, ``wordnet.py``; interface resolutions 2 and 3, what the
generators import; imported on first use):

- ``OpenAIEmbedder``: the live embedding model (OpenAI ``text-embedding-3-large``, direct key).
- ``LocalEmbedder``: an open-weights embedder from the in-tree Hugging Face cache.
- ``HashEmbedder``: a deterministic bag-of-words embedder for tests (no network).
- ``make_embedder``: an embedder by arm name (``openai``, ``bge``, ``gemma``, ``hash``).
- ``EmbeddingCache``: the per-model embedding cache under ``data/candidates/cache/embeddings/``.
- ``embed_texts``: embeds texts through the cache (only misses are sent, each call charged to a usage tracker).
- ``trait_text``: a trait's ``label: description`` text in a given representation.
- ``oewn``: the Open English WordNet handle (``wn``, data in ``data/external/wn``).

Recovery harness (``recovery.py``; imported on first use):

- ``draw_hidden``: the seeded draw of hidden traits, by region, arrangements whole.
- ``write_hidden`` / ``load_hidden``: ``hidden.json`` and its reading (stems, sha256).
- ``reduced_traits`` / ``reduced_label_sets``: the corpus and the exact-label names without the hidden traits.
- ``match_candidates``: a reduced run's decided candidates matched against the hidden traits (label, overlap call).
- ``seed_figures`` / ``combine_seeds`` / ``report_markdown``: one seed's figures, the seeds and their mean, the
  report.
- ``DEFAULT_HIDDEN_FRAC``, ``DEFAULT_SEEDS``: 0.1 and (0, 1).

Importing this package, or any module in it, pins the ``wn`` data directory to ``data/external/wn``
(``paths.pin_wn_data_dir``), whether or not ``wn`` is already imported, and points Hugging Face at
``data/external/hf`` (``paths.pin_hf_cache``).
"""
from .paths import pin_hf_cache as _pin_hf_cache
from .paths import pin_wn_data_dir as _pin_wn_data_dir

_pin_wn_data_dir()
_pin_hf_cache()

from .normalize import (  # noqa: E402
    DECISIONS, NOVELTY_FLAGS, REGION_VOCAB, RELATIONS, REVIEW_STATUSES, TAG_VOCAB, VERDICTS,
    Normalized, make_key, normalize_candidate,
)
from .paths import (  # noqa: E402
    CORPUS_REGIONS_PATH, DATA_CANDIDATES, DATA_DIR, DATA_EXTERNAL, METRIC_CONFIG_PATH, REGISTRY_PATH,
    REGISTRY_SNAPSHOT_PATH, SEED_QUEUE_PATH, check_id, filter_dir, hf_cache_dir, novelty_dir, recovery_dir,
    run_dir, wn_data_dir,
)
from .registry import (  # noqa: E402
    CANDIDATE_FIELDS, Candidate, Registry, SubmitReport, compact, holding_list, read_candidates,
    records_for_status, submit_candidates,
)
from .runs import RunContext, start_run  # noqa: E402
from .metric_config import MetricConfig  # noqa: E402

#: The recovery harness's entry points, imported from ``recovery.py`` on first use (it pulls in M3's modules,
#: which a generator that only submits candidates does not need).
RECOVERY_EXPORTS: tuple[str, ...] = (
    "draw_hidden", "write_hidden", "load_hidden", "reduced_traits", "reduced_label_sets", "match_candidates",
    "seed_figures", "combine_seeds", "report_markdown", "DEFAULT_HIDDEN_FRAC", "DEFAULT_SEEDS",
)
#: The embedding facade and the WordNet handle (interface resolutions 2 and 3), imported on first use (``wn``
#: is imported only by a caller of ``oewn``).
EMBED_EXPORTS: tuple[str, ...] = ("OpenAIEmbedder", "LocalEmbedder", "HashEmbedder", "make_embedder", "EmbeddingCache",
                                  "embed_texts")
#: Every name loaded on first use, and its module.
LAZY_EXPORTS: dict[str, str] = {**{n: "recovery" for n in RECOVERY_EXPORTS}, **{n: "embed" for n in EMBED_EXPORTS},
                                "trait_text": "representation", "oewn": "wordnet"}


from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:   # what static checkers and editors see; at run time these load on first use (``__getattr__``)
    from .embed import (  # noqa: F401
        EmbeddingCache, HashEmbedder, LocalEmbedder, OpenAIEmbedder, embed_texts, make_embedder,
    )
    from .recovery import (  # noqa: F401
        DEFAULT_HIDDEN_FRAC, DEFAULT_SEEDS, combine_seeds, draw_hidden, load_hidden, match_candidates,
        reduced_label_sets, reduced_traits, report_markdown, seed_figures, write_hidden,
    )
    from .representation import trait_text  # noqa: F401
    from .wordnet import oewn  # noqa: F401


def __getattr__(name: str):
    if name in LAZY_EXPORTS:
        import importlib
        return getattr(importlib.import_module(f"{__name__}.{LAZY_EXPORTS[name]}"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # registry API (generators)
    "Candidate", "SubmitReport", "RunContext", "start_run", "submit_candidates", "read_candidates",
    "CANDIDATE_FIELDS", "Registry", "compact", "holding_list", "records_for_status",
    # vocabularies and normalisation
    "VERDICTS", "TAG_VOCAB", "REGION_VOCAB", "DECISIONS", "NOVELTY_FLAGS", "RELATIONS",
    "REVIEW_STATUSES", "Normalized", "normalize_candidate", "make_key",
    # metric configuration
    "MetricConfig",
    # paths
    "DATA_DIR", "DATA_CANDIDATES", "DATA_EXTERNAL", "REGISTRY_PATH", "REGISTRY_SNAPSHOT_PATH", "METRIC_CONFIG_PATH",
    "CORPUS_REGIONS_PATH", "SEED_QUEUE_PATH", "run_dir", "filter_dir", "novelty_dir", "recovery_dir", "check_id",
    "hf_cache_dir", "wn_data_dir",
    # embedding and WordNet (lazy)
    *EMBED_EXPORTS, "trait_text", "oewn",
    # recovery harness (lazy)
    *RECOVERY_EXPORTS,
]
