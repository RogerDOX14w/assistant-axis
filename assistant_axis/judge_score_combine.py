"""Standard, empirically-tuned mixing ratios for combining judge scores.

Four families of weights live here, all derived from sweeps at the
project's operating-point cells (slot 6 / layer 25 for response-mode,
slot 3 / 0 / 0 for desc+inst).  Centralised so any new analysis or
plotting script gets the project's current best-default with a single
import.

::

    from assistant_axis.judge_score_combine import (
        DEFAULT_DI_WEIGHTS,             # 0.499 desc / 0.501 inst   (within one judge)
        DEFAULT_GPT_SONNET_DI_WEIGHT,   # 0.625 GPT / 0.375 Sonnet  (within desc+inst ensemble; v2 retune 2026-05-12)
        DEFAULT_GPT_HAIKU_Q9_WEIGHT,    # 0.625 GPT / 0.375 Haiku   (within response ensemble; canonical-whitening retune 2026-05-12)
        DEFAULT_RESPONSE_DI_WEIGHT,     # 0.80 response / 0.20 DI   (final blend)
        combine_desc_inst_two_judges,
    )

----

1. **Per-judge desc + inst** -- ``DEFAULT_DI_WEIGHTS`` /
   ``combine_desc_inst_*``: how to fold one judge's description-mode
   and instruction-mode scores together into a single per-entity
   scalar.  Default ``(0.499, 0.501)`` -- the **inst-tiebreak**
   weighting.

   Picked after a sweep at slot=(3,25)/(0,26)/(0,49) over three
   weight schemes (0.499/0.501, 0.500/0.500, 0.501/0.499).  The
   inst-favouring weight gave consistently higher mean activation→
   judge ρ across all three (slot, layer) configurations (typically
   +0.0005 to +0.0008 over the equal weighting).  The asymmetry only
   matters when desc and inst disagree per entity, so the weights act
   as a tiebreaker; we lean slightly toward instructions because
   instruction-mode judging was empirically more reliable than
   description-mode judging (~99% defensible on inst vs ~90% on
   desc; see the desc/inst audit).

2. **Within desc+inst ensemble (GPT vs Sonnet)** --
   ``DEFAULT_GPT_SONNET_DI_WEIGHT``: weight on GPT-4.1-mini's
   per-mode scores when averaging GPT and Sonnet inside the
   desc+inst ensemble (the rest goes on Sonnet).  Default ``0.625``.

   Selection history:

   * **0.50** (Apr 2026, pre-canonical-whitening): tuned on the
     33-axis ``--rubric v1`` raw-projection sweep at slot 3 /
     layer 25.  Parabolic interior peak at ``w = 0.530``, mean
     ρ = 0.5949 -- 0.0004 below the discrete 50/50 value of
     0.5953.  The curve was flat enough (±0.0004 across the entire
     ``w ∈ [0.1, 0.9]`` interior) that 0.50 was the natural pick,
     and it had the nice property of reproducing the historical
     4-way mean ``(g_d + g_i + s_d + s_i) / 4`` when paired with
     ``DI_WEIGHTS_EQUAL``.

   * **0.625** (2026-05-12, canonical-whitening retune): re-tuned on
     the 35-axis ``soft_shear=3`` view at slot 6 / layer 25 (the
     current canonical operating point -- see
     ``results_analysis/gpt_sonnet_weight_sweep.py --whitening
     soft_shear=3``).  Discrete grid peak at ``w = 0.625``,
     ρ = 0.70198; parabolic interior fit peaks slightly higher at
     ``w = 0.700`` (R²=0.987) but the upper plateau ``w∈[0.575,
     0.700]`` is flat within 0.0003 ρ -- entirely inside the
     ~±0.04 95% CI half-width (n=35, per-axis stdev 0.124), so the
     discrete peak and the parabolic fit are statistically tied
     across the upper half of the plateau.  Picked the literal
     discrete peak ``0.625`` over the parabolic ``0.700``: same ρ
     to four decimals, and the rightward shift under whitening
     (vs pre-whitening 0.50) is fully captured without
     overcommitting past the plateau edge.  The whitening-tilts-
     toward-GPT story is consistent across both this sweep and the
     GPT/Haiku response sweep: soft-shear cleans away
     goal/no-goal-overlap noise that previously masked GPT's
     per-axis advantage.

   Re-tune only if a future sweep with substantially different
   judges, axes, or whitening regime shows the discrete peak
   shifting outside ``[0.55, 0.75]``.

3. **Within-response judge ensemble** --
   ``DEFAULT_GPT_HAIKU_Q9_WEIGHT``: weight on GPT-4.1-mini in the
   response-mode ensemble (the rest goes on Haiku).  Default ``0.625``
   (so the blend is ``0.625 * GPT + 0.375 * Haiku``).

   Selection history:

   * **0.60** (Apr 2026, pre-Phase-5d): tuned on the v1 GPT-vs-Haiku-q9
     weight sweep at slot 6 layer 25 (legacy ``gpt_responses_*_b10`` /
     ``haiku_responses_*_b10_q9`` caches; see
     ``results_analysis/gpt_anthropic_response_weight_sweep.py
     --rubric v1``).  Parabolic peak at ``w ≈ 0.609`` → rounded to
     0.60.  Mean ρ flat over ``w ∈ [0.5, 0.75]``, so the round number
     cost nothing measurable.

   * **0.41** (2026-05-11, post-Phase-5d, raw-projection): re-tuned on
     the v2 ``--rubric v2`` view (GPT at B=7 Phase-5c full-volume vs
     Haiku at B=7-t3 surgical with B=10-q9 fallback) at *raw
     projection*.  Parabolic peak at ``w ≈ 0.410``; the ~0.2 leftward
     shift reflected Haiku's improved data quality after the Phase-5d
     surgical rejudge escalated the ~34 RP-depleted entities per axis
     from q9 to tiered M=3.  Confirmed in
     ``gpt_haiku_q9_response_weight_sweep_slot6__rubric_v2.png`` (raw
     view).  Superseded by the next entry once whitening became the
     project canonical.

   * **0.625** (2026-05-12, canonical-whitening retune): re-tuned on
     the v2 ``--rubric v2`` view at ``--whitening soft_shear=3``,
     i.e. the canonical operating point all downstream analyses now
     use.  Discrete grid peak at ``w = 0.600`` (ρ = 0.7524, w_step =
     0.025); the parabolic interior fit peaks at ``w = 0.624``.
     Picked ``0.625`` over the literal discrete 0.600 because (a)
     the plateau ``w ∈ [0.50, 0.70]`` is flat within 0.0006 ρ
     (vs ~0.055 95% CI half-width, n=12 axes per-axis stdev 0.097)
     so 0.600 / 0.624 / 0.625 are statistically tied, and (b)
     setting both response and desc+inst constants to the same
     value 0.625 is principled: under canonical whitening every
     judge-pair weight sweep we've run lands its peak within a few
     percent of 0.625, reflecting that soft-shear cleans away
     goal/no-goal-overlap noise that previously dragged the
     optimum toward whichever judge handled that noise better.
     The Phase-5d Haiku quality improvement is still real -- pure
     Haiku ρ is +0.041 higher than pre-Phase-5d -- but whitening
     separates signal from noise even more strongly, so the optimum
     lands back near the rounded pre-Phase-5d 0.60 value.  Smoother
     plot (no GPT-vs-Sonnet-style staircase) because response-mode
     scores are batch-averaged into a continuous ``mean_score`` per
     entity.

   The constant's name retains ``_Q9`` for back-compat (it was
   historically tuned against q9) but the v2 operating point is the
   mixed ``_b7_t3 ⇢ _b10_q9`` cohort.  Re-tune only if a future sweep
   with substantially different cohorts shows the peak shifting
   outside ``[0.50, 0.75]``.

4. **Final response × desc+inst blend** -- ``DEFAULT_RESPONSE_DI_WEIGHT``:
   weight on the response ensemble in the final per-entity score
   (the rest goes on the desc+inst ensemble).  Default ``0.80``.

   Picked from the response × desc+inst sweep at slot 6 layer 25
   (see ``results_analysis/response_di_weight_sweep.py``).  The
   12-axis parabolic peak is at ``w ≈ 0.84``; the 11-axis-without-
   eco/anthro peak is at ``w ≈ 0.71``.  ``0.80`` lands in the flat
   plateau of *both* curves (the 12-axis cohort gives ρ ≈ 0.762 at
   w=0.8 vs 0.763 at w=0.84; the 11-axis cohort gives ρ ≈ 0.770 at
   w=0.8 vs 0.772 at w=0.71) so the choice is robust to whether
   eco/anthro is treated as a regular or held-out axis.

Usage examples::

    # Combine one judge's desc + inst with the standard tiebreak.
    scores = combine_desc_inst_one_judge(g_d, g_i)

    # Combine GPT + Sonnet desc+inst (4-way) at the standard 0.5/0.5
    # GPT-Sonnet split + inst-tiebreak desc/inst weight.  Pass
    # gpt_sonnet_weight=... to override the cross-judge mix.
    di = combine_desc_inst_two_judges(g_d, g_i, s_d, s_i)

    # Build the response ensemble.
    response = {
        n: DEFAULT_GPT_HAIKU_Q9_WEIGHT * gpt_resp[n]
           + (1 - DEFAULT_GPT_HAIKU_Q9_WEIGHT) * haiku_resp[n]
        for n in set(gpt_resp) & set(haiku_resp)
    }

    # Build the final per-entity score.
    final = {
        n: DEFAULT_RESPONSE_DI_WEIGHT * response[n]
           + (1 - DEFAULT_RESPONSE_DI_WEIGHT) * di[n]
        for n in set(response) & set(di)
    }

When in doubt, prefer these constants to inline floats so future
re-tunings propagate everywhere with one edit.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .provenance import InputSpec, current_file_input


# (desc_weight, inst_weight). Sums to 1.0 by convention but enforce-not-required.
DI_WEIGHTS_INST_TIE: Tuple[float, float] = (0.499, 0.501)  # default: instruction-favoring
DI_WEIGHTS_EQUAL: Tuple[float, float] = (0.500, 0.500)
DI_WEIGHTS_DESC_TIE: Tuple[float, float] = (0.501, 0.499)

DEFAULT_DI_WEIGHTS: Tuple[float, float] = DI_WEIGHTS_INST_TIE


# Cross-judge weight on GPT-4.1-mini inside the desc+inst ensemble
# (the rest goes on Sonnet, applied per-mode before the desc/inst
# tiebreak).  Was 0.50 until 2026-05-12; retuned to 0.625 the same
# day on the 35-axis ``soft_shear=3`` view at slot 6 / layer 25
# (the canonical whitened operating point).  ``0.625`` is the
# discrete grid peak at w_step=0.025; the parabolic interior fit
# peaks at w=0.700 with R²=0.987 but the plateau ``w∈[0.575, 0.700]``
# is flat within 0.0003 ρ (vs ~0.04 95%-CI half-width), so the
# discrete peak and the parabolic fit are statistically tied across
# the upper half of the plateau.  Picked ``0.625`` because it's the
# literal discrete peak, leaning toward GPT (consistent with what
# whitening does on every weight sweep) without overcommitting past
# the plateau edge.  See module docstring "Selection history" for
# derivation, and ``results_analysis/gpt_sonnet_weight_sweep.py``
# (``--whitening soft_shear=3``) for reproduction.
DEFAULT_GPT_SONNET_DI_WEIGHT: float = 0.625

# Within-response ensemble weight on GPT-4.1-mini (the rest goes
# on Haiku).  Selection history (newest first):
#
#   * 0.625 (2026-05-12, canonical-whitening): on the v2 sweep at
#     --whitening soft_shear=3 (current canonical operating point).
#     Discrete grid peak w=0.600, parabolic-fit peak w=0.624; plateau
#     w∈[0.50, 0.70] flat within 0.0006 ρ vs ~0.055 95% CI half-width.
#     Picked 0.625 for symmetry with DEFAULT_GPT_SONNET_DI_WEIGHT
#     (both end up at 0.625 under canonical whitening -- a
#     soft-shear-cleans-the-pairwise-noise effect, not coincidence).
#   * 0.41 (2026-05-11, pre-whitening v2 retune): on the v2 sweep
#     at raw projection; parabolic peak w≈0.410.  Superseded once
#     soft_shear=3 became the canonical operating point.
#   * 0.60 (Apr 2026, pre-Phase-5d): v1 sweep, parabolic peak w≈0.609.
#
# Name retains ``_Q9`` suffix for back-compat (was historically tuned
# against q9-subsample Haiku); v2 operating point is the mixed
# ``_b7_t3 ⇢ _b10_q9`` cohort.  See module docstring "Selection
# history" for the full derivation of each entry above.
DEFAULT_GPT_HAIKU_Q9_WEIGHT: float = 0.625


# Final per-entity score weight on the response ensemble (the rest
# goes on the desc+inst ensemble).  See module docstring for
# derivation.
DEFAULT_RESPONSE_DI_WEIGHT: float = 0.80


# Cross-axis sample weight for "primary" axes (axes that have GPT
# response-mode judging in addition to desc+inst) when aggregating
# per-axis rho values into a cohort-mean.  Default ``5.0`` matches
# the 2026-05-07 RF analysis on (axis, K) pairs: each (axis, K)
# sample that included response-mode judging was treated as worth
# 5x a desc+inst-only sample, reflecting the additional signal
# response-mode brings on those axes where it's available.
#
# Used by :func:`cohort_mean_curves` below and by
# :mod:`results_analysis.shear_l_vs_k_comparison` (``--primary_weight``
# default).  Bump only after re-deriving from a sweep with new RF /
# regret weighting.
PRIMARY_AXIS_SAMPLE_WEIGHT: float = 5.0

DI_WEIGHT_CHOICES = {
    "inst_tie": DI_WEIGHTS_INST_TIE,  # 0.499*d + 0.501*i  -- DEFAULT
    "equal":    DI_WEIGHTS_EQUAL,     # 0.500*d + 0.500*i
    "desc_tie": DI_WEIGHTS_DESC_TIE,  # 0.501*d + 0.499*i
}


def parse_di_weights_arg(name: str) -> Tuple[float, float]:
    """Parse a ``--di_weights`` CLI value into a (desc, inst) weight tuple.

    Accepts: ``inst_tie`` (default), ``equal``, ``desc_tie``.
    """
    if name not in DI_WEIGHT_CHOICES:
        raise ValueError(
            f"Unknown di_weights name '{name}'. "
            f"Choices: {sorted(DI_WEIGHT_CHOICES)}."
        )
    return DI_WEIGHT_CHOICES[name]


def combine_desc_inst_one_judge(
    desc_scores: Dict[str, float],
    inst_scores: Dict[str, float],
    weights: Tuple[float, float] = DEFAULT_DI_WEIGHTS,
) -> Dict[str, float]:
    """Combine one judge's desc and inst scores using ``w_d * desc + w_i * inst``.

    Only includes names present in BOTH inputs. Ignores entries whose desc or
    inst score is non-numeric (e.g. ``None``).

    Parameters
    ----------
    desc_scores : dict[name -> int | float]
    inst_scores : dict[name -> int | float]
    weights : (desc_weight, inst_weight)
        Defaults to the inst-tiebreak weighting (0.499, 0.501); see module
        docstring for empirical rationale.

    Returns
    -------
    dict[name -> float]
    """
    w_d, w_i = weights
    out = {}
    for n in set(desc_scores) & set(inst_scores):
        d, i = desc_scores[n], inst_scores[n]
        if not (isinstance(d, (int, float)) and isinstance(i, (int, float))):
            continue
        out[n] = w_d * d + w_i * i
    return out


def combine_desc_inst_two_judges(
    gpt_desc: Dict[str, float],
    gpt_inst: Dict[str, float],
    sonnet_desc: Dict[str, float],
    sonnet_inst: Dict[str, float],
    weights: Tuple[float, float] = DEFAULT_DI_WEIGHTS,
    gpt_sonnet_weight: float = DEFAULT_GPT_SONNET_DI_WEIGHT,
) -> Dict[str, float]:
    """Combine two judges' desc and inst scores into a single scalar per entity.

    Cross-judge weighted average per mode, then desc/inst weighted
    combination::

        desc_avg = w_gs * gpt_desc + (1 - w_gs) * sonnet_desc
        inst_avg = w_gs * gpt_inst + (1 - w_gs) * sonnet_inst
        score    = w_d * desc_avg + w_i * inst_avg

    With the defaults ``w_gs = 0.5`` and ``weights = (0.499, 0.501)``
    this is the project standard.  At ``w_gs = 0.5`` the function is
    mathematically identical to the historical hardcoded
    ``(gpt + sonnet) / 2`` averaging; the parameterisation is a
    strict generalisation kept for the rare case where a future
    sweep would justify a non-50/50 GPT/Sonnet split (see the module
    docstring's ``DEFAULT_GPT_SONNET_DI_WEIGHT`` derivation -- the
    33-axis sweep places the parabolic peak so close to 0.5 that
    the round number is the empirical optimum).

    Only includes entities present in all four input dicts with
    numeric scores.

    Parameters
    ----------
    gpt_desc, gpt_inst, sonnet_desc, sonnet_inst : dict[name -> int | float]
    weights : (desc_weight, inst_weight)
        Defaults to inst-tiebreak ``(0.499, 0.501)``.
    gpt_sonnet_weight : float
        Cross-judge weight on GPT (the rest goes on Sonnet) per mode,
        applied before the desc/inst combination.  Default
        ``DEFAULT_GPT_SONNET_DI_WEIGHT`` (= 0.50).

    Returns
    -------
    dict[name -> float]
    """
    w_d, w_i = weights
    w_gs = gpt_sonnet_weight
    w_son = 1.0 - w_gs
    common = (
        set(gpt_desc) & set(gpt_inst) & set(sonnet_desc) & set(sonnet_inst)
    )
    out = {}
    for n in common:
        gd, gi, sd, si = gpt_desc[n], gpt_inst[n], sonnet_desc[n], sonnet_inst[n]
        if not all(isinstance(v, (int, float)) for v in (gd, gi, sd, si)):
            continue
        desc_avg = w_gs * gd + w_son * sd
        inst_avg = w_gs * gi + w_son * si
        out[n] = w_d * desc_avg + w_i * inst_avg
    return out


def cohort_mean_curves(
    rho_table: Dict[Tuple[str, str, str], list],
    pair_keys: list,
    *,
    w_rs: float = DEFAULT_RESPONSE_DI_WEIGHT,
    primary_weight: float = PRIMARY_AXIS_SAMPLE_WEIGHT,
    min_axes: int = 3,
):
    """Compute three cohort-mean ρ-vs-X curves from per-axis ρ tables.

    Produced for overlay on the per-axis curves in plots like
    :mod:`results_analysis.whitening_k_sweep` and
    :mod:`results_analysis.shear_l_sweep`, so the cross-axis trend is
    readable at a glance alongside the per-axis spaghetti.

    Args:
        rho_table: Dict ``{(pos, neg, source): [rho at X_0, rho at X_1, ...]}``.
            ``source`` is ``"responses"`` or ``"desc_inst"``.  Missing or
            NaN entries are tolerated.
        pair_keys: Ordered list of ``(pos, neg)`` axis tuples.  An axis
            is treated as *primary* (has response-mode judging) iff its
            ``"responses"`` row contains at least one finite value.
        w_rs: Within-axis blend weight on response-mode (the rest goes
            on desc+inst).  Default :data:`DEFAULT_RESPONSE_DI_WEIGHT`
            = 0.80, the project's "responses are ~4x as informative as
            desc+inst when both are available" empirical optimum.
        primary_weight: Cross-axis sample weight for primary axes
            (vs ``1.0`` for desc+inst-only axes).  Default
            :data:`PRIMARY_AXIS_SAMPLE_WEIGHT` = 5.0, matching the RF
            regret-weighted analysis.
        min_axes: An X-point's curve value is NaN if fewer than this
            many axes have finite data at that X.

    Returns:
        ``(avg_rs, avg_di, avg_blend)``, each a list of floats matching
        the length of any row in ``rho_table``.

        - ``avg_rs``: simple cross-axis mean of the ``responses`` rows
          (skipping NaN axes).  Reflects the response-mode-only cohort.
        - ``avg_di``: simple cross-axis mean of the ``desc_inst`` rows.
          Reflects the broader desc+inst cohort (often more axes than
          the response cohort).
        - ``avg_blend``: cross-axis weighted mean of the per-axis
          project-standard blend.  Per axis the blend is
          ``w_rs * rho_rs + (1 - w_rs) * rho_di`` for primary axes
          (those with finite ``responses`` data) and ``rho_di`` for
          desc+inst-only axes.  Cross-axis weights are ``primary_weight``
          for primary axes and ``1.0`` for desc+inst-only axes.  When
          a primary axis has NaN at some X-point (e.g. response data
          missing for a specific X), that axis silently falls back to
          its ``rho_di`` value at that X (still weighted at
          ``primary_weight``).

    NaN propagation: every entry is a Python ``float`` (NaN for empty
    cells), suitable for direct ``ax.plot(x_pos, avg_curve, ...)``
    consumption since matplotlib skips NaN segments.
    """
    import math
    if not rho_table:
        return [], [], []

    # Determine length of curve via any non-empty row.
    n_x: Optional[int] = None
    for row in rho_table.values():
        if hasattr(row, "__len__"):
            n_x = len(row)
            break
    if not n_x:
        return [], [], []

    def _is_finite(x) -> bool:
        return isinstance(x, (int, float)) and math.isfinite(x)

    # Which axes are primary (have response-mode judging anywhere on
    # the X grid)?  Used both for the avg_blend weighting and as a
    # sanity check on the avg_rs population.
    primary_pairs = set()
    for pos, neg in pair_keys:
        rs_row = rho_table.get((pos, neg, "responses"))
        if rs_row and any(_is_finite(v) for v in rs_row):
            primary_pairs.add((pos, neg))

    avg_rs: list[float] = []
    avg_di: list[float] = []
    avg_blend: list[float] = []
    for xi in range(n_x):
        # (a) responses cohort mean
        rs_vals = [
            rho_table[(p, n, "responses")][xi]
            for (p, n) in pair_keys
            if (p, n, "responses") in rho_table
            and xi < len(rho_table[(p, n, "responses")])
            and _is_finite(rho_table[(p, n, "responses")][xi])
        ]
        avg_rs.append(
            float(sum(rs_vals) / len(rs_vals))
            if len(rs_vals) >= min_axes else float("nan")
        )

        # (b) desc+inst cohort mean
        di_vals = [
            rho_table[(p, n, "desc_inst")][xi]
            for (p, n) in pair_keys
            if (p, n, "desc_inst") in rho_table
            and xi < len(rho_table[(p, n, "desc_inst")])
            and _is_finite(rho_table[(p, n, "desc_inst")][xi])
        ]
        avg_di.append(
            float(sum(di_vals) / len(di_vals))
            if len(di_vals) >= min_axes else float("nan")
        )

        # (c) per-axis blend cross-axis weighted mean
        num = 0.0
        den = 0.0
        n_contrib = 0
        for (p, n) in pair_keys:
            di_row = rho_table.get((p, n, "desc_inst"))
            rs_row = rho_table.get((p, n, "responses"))
            di_val = (di_row[xi] if di_row and xi < len(di_row) else None)
            rs_val = (rs_row[xi] if rs_row and xi < len(rs_row) else None)
            is_primary = (p, n) in primary_pairs
            if is_primary:
                if _is_finite(rs_val) and _is_finite(di_val):
                    blend = w_rs * rs_val + (1.0 - w_rs) * di_val
                elif _is_finite(di_val):
                    # Response-side hole at this X-point; fall back to
                    # desc+inst (still at the primary weight, since this
                    # axis IS primary overall).
                    blend = float(di_val)
                else:
                    continue
                w = primary_weight
            else:
                if not _is_finite(di_val):
                    continue
                blend = float(di_val)
                w = 1.0
            num += w * blend
            den += w
            n_contrib += 1
        avg_blend.append(
            float(num / den) if (den > 0 and n_contrib >= min_axes)
            else float("nan")
        )

    return avg_rs, avg_di, avg_blend


# ---------------------------------------------------------------------------
# Provenance helper: declare a dependency on this file's constants.
# ---------------------------------------------------------------------------

_THIS_FILE: Path = Path(__file__).resolve()


def declare_constants_dependency(
    inputs: List[InputSpec],
    *,
    dep_key: str = "judge_score_combine_constants",
) -> None:
    """Append an :class:`InputSpec` for this module's constants file to
    ``inputs``, so downstream caches that bake in any of the
    ``DEFAULT_*_WEIGHT`` / ``PRIMARY_AXIS_SAMPLE_WEIGHT`` constants get
    flagged as stale by ``tools/audit_caches.py`` whenever those
    constants are retuned.

    Lazy granularity
    ----------------
    The fingerprint is the file's ``(mtime, size)`` -- so ANY edit to
    this file (even a docstring tweak) triggers stale-flag on every
    consumer that records this dep, not just edits that touch the
    specific constant the consumer uses.

    That's the right trade-off for the project's actual workflow:
    constant retunings are rare (one or two per quarter), so a stray
    docstring edit causing a one-time "rerun all consumers" pulse is
    cheap.  The accurate alternative -- per-constant fingerprints --
    would require a new InputSpec ``kind`` plus a registry mapping
    constant-names to current values; deferred to "Constant-level
    provenance" in AGENT_NOTES if the lazy granularity ever becomes
    a real nuisance.

    For forensic purposes the current constant values are stamped
    into the InputSpec's ``extras`` (advisory only -- not part of
    drift comparison per the project convention).  Audit reports
    will surface the recorded values so a stale-cache reviewer can
    see what numbers each cache "thinks" the defaults are.

    Args:
        inputs: The caller's provenance accumulator.  Mutated in
            place by appending one new :class:`InputSpec`.
        dep_key: Override the default dep_key if needed (e.g. when
            multiple consumers of this file want distinct dep_keys
            for clarity in the audit output).
    """
    inputs.append(current_file_input(
        path=_THIS_FILE,
        dep_key=dep_key,
        extras={
            "DEFAULT_DI_WEIGHTS": str(DEFAULT_DI_WEIGHTS),
            "DEFAULT_GPT_SONNET_DI_WEIGHT": f"{DEFAULT_GPT_SONNET_DI_WEIGHT}",
            "DEFAULT_GPT_HAIKU_Q9_WEIGHT": f"{DEFAULT_GPT_HAIKU_Q9_WEIGHT}",
            "DEFAULT_RESPONSE_DI_WEIGHT": f"{DEFAULT_RESPONSE_DI_WEIGHT}",
            "PRIMARY_AXIS_SAMPLE_WEIGHT": f"{PRIMARY_AXIS_SAMPLE_WEIGHT}",
        },
    ))


def add_di_weights_arg(parser, default: str = "inst_tie") -> None:
    """Convenience: register a standard ``--di_weights`` argparse argument.

    Usage::

        from assistant_axis.judge_score_combine import add_di_weights_arg, parse_di_weights_arg
        ...
        add_di_weights_arg(parser)
        args = parser.parse_args()
        weights = parse_di_weights_arg(args.di_weights)
    """
    parser.add_argument(
        "--di_weights",
        choices=list(DI_WEIGHT_CHOICES.keys()),
        default=default,
        help=(
            "Weighting for combining description and instruction judge scores. "
            "'inst_tie' (default, 0.499*d+0.501*i) leans slightly toward "
            "instructions, which is empirically the more reliable judge mode. "
            "'equal' is the historical 0.5/0.5 weighting. 'desc_tie' "
            "(0.501*d+0.499*i) leans toward descriptions; included for "
            "ablation. The asymmetry only affects entities where desc and "
            "inst disagree, so the impact is modest (~+0.0005 ρ for inst_tie "
            "over equal, monotonic across (slot, layer) configurations)."
        ),
    )
