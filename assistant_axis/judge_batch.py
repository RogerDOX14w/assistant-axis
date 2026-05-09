"""Project-wide canonical batch size for response judging.

Response-mode judging partitions an entity's score==3 responses into
roughly equal-sized batches before sending each batch to the LLM judge
(see ``results_analysis.axis_judge_correlation.plan_response_batches``).
The batch size is a noise-vs-cost trade-off knob; once chosen, it
influences every downstream rho/correlation analysis that consumes
``scores_responses.json`` files, so all consumers should agree on a
single value.

Why a module-level constant
---------------------------
Historically, the default was duplicated in two places kept in sync by
comments:

- ``results_analysis.axis_judge_correlation``: argparse default for
  ``--response_target_batch_size``.
- ``assistant_axis.steering_judges.DEFAULT_TARGET_BATCH_SIZE``: the
  steering effect-judge default, which is intentionally pinned to the
  axis-judge default so the two score distributions are apples-to-apples
  in the same judging regime.

Plus a third implicit convention: judging output directories use the
``_b{BATCH_SIZE}`` suffix (e.g. ``gpt_responses_traits_b10``), and a
handful of analysis scripts hard-coded ``"_b10"`` in path construction.

This module makes the default a single named constant and offers a tiny
helper for path construction so that bumping the value (e.g. to retire
the b=10 corpus and pay the rejudging cost for b=12) is a one-line edit
that ripples to every consumer.

Changing the value
------------------
Bumping ``RESPONSE_BATCH_SIZE`` invalidates every existing
``*_b{old}/scores_responses.json`` cache for *response* judging
purposes (the desc+inst caches are unaffected -- their rubric is
batch-size-agnostic).  After bumping you'll need to:

1. Re-run ``axis_judge_correlation.py --score_responses`` for every
   axis x judge cell you care about (LLM cost).
2. Re-run every downstream consumer (whitening_k_sweep, rho_by_layer,
   optimal_axis_for_judge, batch_size_rho_curve, ...).
3. Either delete the old ``_b{old}`` caches or defer them via
   ``tools/defer_rejudge.py``.

The constant intentionally lives here (not in
``axis_judge_correlation``) so steering-side modules can import it
without pulling in the whole results-analysis pipeline.
"""
from __future__ import annotations

RESPONSE_BATCH_SIZE: int = 10
"""Canonical target batch size for response-mode judging.

Used by:

- ``results_analysis.axis_judge_correlation`` -- argparse default for
  ``--response_target_batch_size``.
- ``assistant_axis.steering_judges`` -- ``DEFAULT_TARGET_BATCH_SIZE``.
- ``results_analysis.whitening_k_sweep`` /
  ``results_analysis.rho_by_layer`` /
  ``results_analysis.optimal_axis_for_judge`` -- the per-axis
  ``gpt_responses_{traits,roles}_b{N}/`` directory they read from.
"""


def response_subdir(
    judge: str,
    mode: str,
    *,
    batch_size: int = RESPONSE_BATCH_SIZE,
) -> str:
    """Construct the canonical response-judging output subdir name.

    Parameters
    ----------
    judge : str
        Judge identifier (``"gpt"``, ``"haiku"``, ``"sonnet"``).
    mode : str
        Entity-mode bucket: ``"traits"`` or ``"roles"``.
    batch_size : int, optional
        Response-judging batch size.  Defaults to the canonical
        ``RESPONSE_BATCH_SIZE``; pass an explicit value to construct a
        legacy-batch path (e.g. for cross-batch comparison plots that
        need to read ``_b5`` / ``_b7`` / ``_b15`` archives).

    Returns
    -------
    str
        Subdirectory name like ``"gpt_responses_traits_b10"``.

    Notes
    -----
    Pre-Phase-6 caches without a ``_b{N}`` suffix (bare
    ``gpt_responses_traits/``) are *not* covered by this helper and
    are treated as legacy v1 archives -- consumers that still need to
    read them should do so explicitly via the unsuffixed path.
    """
    return f"{judge}_responses_{mode}_b{batch_size}"
