"""Standard, empirically-tuned mixing ratios for combining judge scores.

Four families of weights live here, all derived from sweeps at the
project's operating-point cells (slot 6 / layer 25 for response-mode,
slot 3 / 0 / 0 for desc+inst).  Centralised so any new analysis or
plotting script gets the project's current best-default with a single
import.

::

    from assistant_axis.judge_score_combine import (
        DEFAULT_DI_WEIGHTS,             # 0.499 desc / 0.501 inst   (within one judge)
        DEFAULT_GPT_SONNET_DI_WEIGHT,   # 0.50 GPT / 0.50 Sonnet    (within desc+inst ensemble)
        DEFAULT_GPT_HAIKU_Q9_WEIGHT,    # 0.60 GPT / 0.40 Haiku-q9  (within response ensemble)
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
   desc+inst ensemble (the rest goes on Sonnet).  Default ``0.50``.

   Picked from the GPT × Sonnet weight sweep on desc+inst at slot
   3 / layer 25 across 33 axes (see
   ``results_analysis/gpt_sonnet_weight_sweep.py``; full results
   in ``results_analysis/README.md``).  The 33-axis parabolic fit
   on the interior ``[0.1, 0.9]`` peaks at ``w = 0.530`` with mean
   ρ = 0.5949 -- *0.0004 below* the discrete 50/50 value of
   0.5953.  The curve is so flat that the entire decision-relevant
   range (``w ∈ [0.1, 0.9]``) sits within ±0.0004 of peak, so
   ``0.50`` is the empirical optimum and the round number that
   reproduces the historical 4-way mean ``(g_d + g_i + s_d + s_i) / 4``
   when paired with ``DI_WEIGHTS_EQUAL``.

   Re-tune only if a future sweep with substantially different
   judges or axes shows the parabolic peak shifting outside
   ``[0.45, 0.55]``.

3. **Within-response judge ensemble** --
   ``DEFAULT_GPT_HAIKU_Q9_WEIGHT``: weight on GPT-4.1-mini B=10 in
   the response-mode ensemble (the rest goes on Haiku-q9).
   Default ``0.60``.

   Picked from the GPT × Haiku-q9 weight sweep at slot 6 layer 25
   (see ``results_analysis/gpt_anthropic_response_weight_sweep.py``).
   The 12-axis parabolic fit on the interior ``[0.1, 0.9]`` peaks at
   ``w ≈ 0.609``; rounded to 0.60 for cleaner reporting.  The mean
   ρ is essentially flat over ``w ∈ [0.5, 0.75]`` (~0.001 spread),
   so the round number costs nothing measurable.

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

from typing import Dict, Tuple


# (desc_weight, inst_weight). Sums to 1.0 by convention but enforce-not-required.
DI_WEIGHTS_INST_TIE: Tuple[float, float] = (0.499, 0.501)  # default: instruction-favoring
DI_WEIGHTS_EQUAL: Tuple[float, float] = (0.500, 0.500)
DI_WEIGHTS_DESC_TIE: Tuple[float, float] = (0.501, 0.499)

DEFAULT_DI_WEIGHTS: Tuple[float, float] = DI_WEIGHTS_INST_TIE


# Cross-judge weight on GPT-4.1-mini inside the desc+inst ensemble
# (the rest goes on Sonnet, applied per-mode before the desc/inst
# tiebreak).  See module docstring for derivation.  At 0.50 this
# produces the historical 4-way mean ``(g_d + g_i + s_d + s_i) / 4``
# when paired with ``DI_WEIGHTS_EQUAL`` -- the parameterised function
# is a strict generalisation of the old hardcoded ``/2`` averaging.
DEFAULT_GPT_SONNET_DI_WEIGHT: float = 0.50

# Within-response ensemble weight on GPT-4.1-mini B=10 (the rest goes
# on Haiku-q9).  See module docstring for derivation.
DEFAULT_GPT_HAIKU_Q9_WEIGHT: float = 0.60


# Final per-entity score weight on the response ensemble (the rest
# goes on the desc+inst ensemble).  See module docstring for
# derivation.
DEFAULT_RESPONSE_DI_WEIGHT: float = 0.80

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
