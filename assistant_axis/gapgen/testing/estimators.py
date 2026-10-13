"""Population estimators for workstream 13: how many distinct concepts are there for generators to find?

Coding plan 13, § 6 "Estimates".  The generators are treated as *occasions* of a capture-recapture study: each
mechanism (lexicon, IPIP, base model, alignment sweep, ...) is a sample of one population of concepts, and the
fewer concepts two samples share, the larger the population they were drawn from.  Every function here is pure
(numbers in, numbers out); ``generator_dashboard.py estimate`` feeds them the concept table and prints
:data:`ASSUMPTIONS` with every result, because the assumptions behind these estimators are known to be false here
and all of them fail in the same direction (the estimates are low).

- :func:`chapman`: two occasions.  N = (n1 + 1)(n2 + 1) / (m + 1) - 1 (Chapman 1951), Seber's (1970) variance, and
  Chao's (1987) log-normal interval, whose lower end is never below the observed distinct count.
- :func:`chao2`: any number of occasions, from the concepts seen on exactly one (Q1) and exactly two (Q2) of
  them.  The bias-corrected form S + ((m - 1) / m) Q1 (Q1 - 1) / (2 (Q2 + 1)) is used throughout, which stays
  finite when Q2 = 0; :func:`chao2_classic` gives the classic Q1^2 / (2 Q2) form the plan's baseline also quotes.
  The variance is the bias-corrected one EstimateS uses (Chao 1987; Chao et al. 2005), with its Q2 = 0 and
  Q1 = 0 variants, and the interval is log-normal as for Chapman.
- :func:`good_turing_coverage` / :func:`coverage_from_Q`: the plan's coverage, 1 - Q1 / (all incidences), the
  share of the population the occasions have already seen (the simple Good-Turing form, not Chao and Jost's
  refinement with Q2).
- :func:`accumulation`, :func:`end_slope`, :func:`chao_extrapolate`: the accumulation curve of one mechanism
  (unique concepts against candidates drawn, in the run's emitted order), its marginal yield at the end, and its
  abundance-based extrapolation (Shen, Chao and Lin 2003; Chao et al. 2014), which levels off at the observed
  count plus Chao1's undetected estimate.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Any, Collection, Mapping, Sequence

#: The z value of a two-sided 95% interval.
Z95 = 1.96

#: Printed by ``generator_dashboard.py estimate`` with every result, and stored in ``estimates.json``.
ASSUMPTIONS: tuple[str, ...] = (
    "The population is closed: the set of concepts does not change while the occasions run.",
    "Equal catchability is false here: some concepts are much easier for every generator to find, so N̂ is low.",
    "Independent occasions are false between LLM-based mechanisms: they tend to find the same concepts, so N̂ is "
    "low.",
    "N̂ is a lower bound on what generators of these kinds can reach.",
)


@dataclass(frozen=True)
class Estimate:
    """A population-size estimate with its standard error and 95% interval."""

    N: float
    se: float
    lo: float
    hi: float

    def as_dict(self) -> dict[str, float]:
        return {"N": round(float(self.N), 1), "se": round(float(self.se), 1), "lo": round(float(self.lo), 1),
                "hi": round(float(self.hi), 1)}


def _lognormal_interval(N: float, var: float, S: float) -> tuple[float, float]:
    """Chao's (1987) log-normal 95% interval for an estimate N of a population with S members observed: the
    undetected part f0 = N - S is taken to be log-normal, so the interval is [S + f0 / C, S + f0 C] and never
    falls below S.  With nothing undetected (f0 <= 0) it is [S, S]."""
    f0 = N - S
    if f0 <= 0:
        return float(S), float(S)
    C = math.exp(Z95 * math.sqrt(math.log(1.0 + max(var, 0.0) / (f0 * f0))))
    return S + f0 / C, S + f0 * C


def chapman(n1: int, n2: int, m: int) -> Estimate:
    """Chapman's two-occasion estimate: ``n1`` and ``n2`` concepts seen on each occasion, ``m`` of them on both.

    N = (n1 + 1)(n2 + 1) / (m + 1) - 1; Seber's variance (n1 + 1)(n2 + 1)(n1 - m)(n2 - m) / ((m + 1)^2 (m + 2));
    the log-normal interval around the observed distinct count n1 + n2 - m."""
    if min(n1, n2, m) < 0 or m > min(n1, n2):
        raise ValueError(f"chapman: need 0 <= m <= min(n1, n2), got n1={n1}, n2={n2}, m={m}")
    N = (n1 + 1) * (n2 + 1) / (m + 1) - 1
    var = (n1 + 1) * (n2 + 1) * (n1 - m) * (n2 - m) / ((m + 1) ** 2 * (m + 2))
    lo, hi = _lognormal_interval(N, var, n1 + n2 - m)
    return Estimate(N=N, se=math.sqrt(var), lo=lo, hi=hi)


def _check_Q(Q: Mapping[int, int], m_occ: int) -> tuple[int, int, int, int]:
    """Validate incidence frequencies and return (S, Q1, Q2, incidences)."""
    if m_occ < 1:
        raise ValueError(f"need at least one occasion, got m_occ={m_occ}")
    S = incidences = 0
    for k, q in Q.items():
        if not isinstance(k, int) or not 1 <= k <= m_occ:
            raise ValueError(f"incidence frequency {k!r} is outside 1..{m_occ}")
        if q < 0:
            raise ValueError(f"negative count {q} for frequency {k}")
        S += q
        incidences += k * q
    return S, Q.get(1, 0), Q.get(2, 0), incidences


def chao2(Q: Mapping[int, int], m_occ: int) -> Estimate:
    """The bias-corrected Chao2 estimate from incidence frequencies: ``Q[k]`` concepts were seen on exactly ``k``
    of the ``m_occ`` occasions.

    N = S + A Q1 (Q1 - 1) / (2 (Q2 + 1)) with A = (m - 1) / m, for every Q2 (finite when Q2 = 0).  Variance, as
    EstimateS gives it for the bias-corrected form:

    - Q1 > 0, Q2 > 0: A Q1 (Q1 - 1) / (2 (Q2 + 1)) + A^2 Q1 (2 Q1 - 1)^2 / (4 (Q2 + 1)^2)
      + A^2 Q1^2 Q2 (Q1 - 1)^2 / (4 (Q2 + 1)^4);
    - Q1 > 0, Q2 = 0: A Q1 (Q1 - 1) / 2 + A^2 Q1 (2 Q1 - 1)^2 / 4 - A^2 Q1^4 / (4 N);
    - Q1 = 0: S exp(-M / S)(1 - exp(-M / S)), M the total incidences (the interval is then [S, S]).
    """
    S, Q1, Q2, incidences = _check_Q(Q, m_occ)
    A = (m_occ - 1) / m_occ
    N = S + A * Q1 * (Q1 - 1) / (2 * (Q2 + 1))
    if S == 0:
        var = 0.0
    elif Q1 == 0:
        e = math.exp(-incidences / S)
        var = S * e * (1 - e)
    elif Q2 > 0:
        var = (A * Q1 * (Q1 - 1) / (2 * (Q2 + 1)) + A ** 2 * Q1 * (2 * Q1 - 1) ** 2 / (4 * (Q2 + 1) ** 2)
               + A ** 2 * Q1 ** 2 * Q2 * (Q1 - 1) ** 2 / (4 * (Q2 + 1) ** 4))
    else:
        var = A * Q1 * (Q1 - 1) / 2 + A ** 2 * Q1 * (2 * Q1 - 1) ** 2 / 4 - A ** 2 * Q1 ** 4 / (4 * N)
    var = max(var, 0.0)
    lo, hi = _lognormal_interval(N, var, S)
    return Estimate(N=N, se=math.sqrt(var), lo=lo, hi=hi)


def chao2_classic(Q: Mapping[int, int], m_occ: int) -> float:
    """The classic Chao2 point estimate S + A Q1^2 / (2 Q2), A = (m - 1) / m; with no doubletons (Q2 = 0) it is
    undefined and the bias-corrected :func:`chao2` is returned instead."""
    S, Q1, Q2, _ = _check_Q(Q, m_occ)
    if Q2 == 0:
        return chao2(Q, m_occ).N
    return S + (m_occ - 1) / m_occ * Q1 * Q1 / (2 * Q2)


def incidence_counts(occasions_by_concept: Mapping[Any, Collection[str]]) -> Counter[int]:
    """Incidence frequencies from concept -> the occasions it was seen on: ``Q[k]`` is the number of concepts seen
    on exactly ``k`` distinct occasions.  A concept seen on no occasion is skipped."""
    out: Counter[int] = Counter()
    for occasions in occasions_by_concept.values():
        k = len(set(occasions))
        if k:
            out[k] += 1
    return out


def good_turing_coverage(Q1: int, incidences: int) -> float:
    """1 - Q1 / incidences, the share of the population the occasions have seen; ``incidences`` counts each
    concept once per occasion it was seen on (the sum of k Q[k]).  Clipped to [0, 1]; no incidences gives 0."""
    if incidences <= 0:
        return 0.0
    return min(1.0, max(0.0, 1.0 - Q1 / incidences))


def coverage_from_Q(Q: Mapping[int, int]) -> float:
    """:func:`good_turing_coverage` from incidence frequencies."""
    return good_turing_coverage(Q.get(1, 0), sum(k * q for k, q in Q.items()))


def _concepts_in_order(order: Sequence[str], concept_of: Mapping[str, Any]):
    for key in order:
        concept = concept_of.get(key)
        if concept is not None:
            yield concept


def accumulation(order: Sequence[str], concept_of: Mapping[str, Any], *, step: int = 1) -> list[tuple[int, int]]:
    """The accumulation curve: walking ``order`` (a run's candidate keys in emitted order), the number of
    distinct concepts after n candidates, as ``(n, unique)`` at every ``step``-th candidate and always at the
    last.  A key missing from ``concept_of`` (or mapped to None) is skipped and not counted in n.  The curve is
    non-decreasing; an order with no known key gives []."""
    if step < 1:
        raise ValueError(f"step must be at least 1, got {step}")
    seen: set[Any] = set()
    curve: list[tuple[int, int]] = []
    n = 0
    for n, concept in enumerate(_concepts_in_order(order, concept_of), start=1):
        seen.add(concept)
        if n % step == 0:
            curve.append((n, len(seen)))
    if n and (not curve or curve[-1][0] != n):
        curve.append((n, len(seen)))
    return curve


def abundance_counts(order: Sequence[str], concept_of: Mapping[str, Any]) -> Counter[int]:
    """Abundance frequencies of one run, under :func:`accumulation`'s rule for keys: ``F[k]`` is the number of
    concepts with exactly ``k`` candidates.  ``F[1]`` and ``F[2]`` are :func:`chao_extrapolate`'s Q1 and Q2."""
    return Counter(Counter(_concepts_in_order(order, concept_of)).values())


def chao_extrapolate(curve: Sequence[tuple[int, int]], *, Q1: int, Q2: int, to_n: int,
                     points: int = 10) -> list[tuple[int, float]]:
    """Extrapolate an accumulation curve from its last point (n, S_obs) to ``to_n`` candidates (Shen, Chao and
    Lin 2003; Chao et al. 2014, Ecological Monographs 84: 45-67).

    With Q1 and Q2 the concepts that have exactly one and exactly two candidates in the run, the undetected
    concepts are estimated as Chao1's f0 = ((n - 1) / n) Q1^2 / (2 Q2), or ((n - 1) / n) Q1 (Q1 - 1) / 2 when
    Q2 = 0, and S(n + m) = S_obs + f0 [1 - (1 - Q1 / (n f0 + Q1))^m].  Returned as ``points`` even steps from n
    to ``to_n`` after the starting point (n, S_obs); non-decreasing and never above S_obs + f0 (flat when f0 is
    0).  An empty curve gives []; ``to_n`` at or below n gives the starting point alone."""
    if not curve:
        return []
    if Q1 < 0 or Q2 < 0:
        raise ValueError(f"negative frequency counts: Q1={Q1}, Q2={Q2}")
    n, s_obs = int(curve[-1][0]), float(curve[-1][1])
    if to_n <= n:
        return [(n, s_obs)]
    if n <= 1 or Q1 == 0:
        f0 = 0.0
    elif Q2 > 0:
        f0 = (n - 1) / n * Q1 * Q1 / (2 * Q2)
    else:
        f0 = (n - 1) / n * Q1 * (Q1 - 1) / 2
    base = 1.0 - Q1 / (n * f0 + Q1) if f0 > 0 else 1.0
    span = to_n - n
    steps = max(int(points), 1)
    out: list[tuple[int, float]] = []
    for i in range(steps + 1):
        extra = round(span * i / steps)
        if out and n + extra == out[-1][0]:
            continue
        out.append((n + extra, s_obs + f0 * (1.0 - base ** extra) if f0 > 0 else s_obs))
    return out


def end_slope(curve: Sequence[tuple[int, int]], window: int) -> float:
    """The marginal yield at the end of an accumulation curve: (u_last - u_at) / (n_last - n_at), where (n_at,
    u_at) is the nearest curve point at or before n_last - ``window``.  0.0 for a curve too short to have such
    a point (a short curve reads as no measured yield, not as saturation: check its length)."""
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if len(curve) < 2:
        return 0.0
    n_last, u_last = curve[-1]
    target = n_last - window
    earlier = [(n, u) for n, u in curve[:-1] if n <= target]
    if not earlier:
        return 0.0
    n_at, u_at = earlier[-1]
    return (u_last - u_at) / (n_last - n_at) if n_last > n_at else 0.0
