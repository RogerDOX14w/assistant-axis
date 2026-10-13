"""The estimators' sanity check: a synthetic population of concepts caught by a few occasions, whose size is known.

Coding plan 13, § 6-8 ("simulate").  The real occasions break two assumptions of :mod:`.estimators`: some concepts
are easier for every generator to find (*heterogeneous catchability*), and the LLM-based mechanisms tend to find
the same concepts (*dependent occasions*).  Both make the estimates low.  This module shows it on a population of
known size N, so that the dashboard's estimates can be read as lower bounds with some sense of how low.

**The model** (a latent-threshold, that is probit, model; chosen over a logistic one because the marginal catch
rate then stays exactly ``p_mean`` in every scenario, so the scenarios differ only in how catches cluster).
Concept i has a catchability z_i ~ N(0, 1) and a bias c_i ~ N(0, 1) shared by the *dependent* occasions; occasion
j has independent noise u_ij ~ N(0, 1).  Concept i is caught by occasion j when

    sigma_catch z_i + e_ij > t,   e_ij = sqrt(rho_occ) c_i + sqrt(1 - rho_occ) u_ij  on a dependent occasion,
                                  e_ij = u_ij                                       on any other,

with t = sqrt(1 + sigma_catch^2) Phi^-1(1 - p_mean), so every catch has marginal probability ``p_mean``.

- ``sigma_catch = 0, rho_occ = 0``: each catch is an independent Bernoulli(``p_mean``), every concept equally
  catchable: the estimators' assumptions hold.
- ``sigma_catch > 0``: heterogeneity; the latent correlation between any two occasions is sigma^2 / (1 + sigma^2)
  (0.5 at sigma 1), so the occasions overlap more than independence predicts and the estimates fall.
- ``rho_occ > 0``: dependence beyond catchability, among the dependent occasions only (by default every occasion
  but occasion 0: occasion 0 plays the lexicon, the others the LLM-based mechanisms).  Their latent correlation
  rises to (sigma^2 + rho) / (1 + sigma^2); occasion 0's stays as it was.  A bias shared by *every* occasion
  would be indistinguishable from more heterogeneity (it is just another term of catchability), which is why
  the shared bias loads on a subset: then leaving out occasion 0 leaves only mutually dependent occasions and
  moves the estimate more than leaving out any other, which is what the leave-one-occasion-out spread detects.
  With fewer than two dependent occasions ``rho_occ`` has no effect.

:func:`run_scenarios` runs three scenarios over the same replicate seeds (common random numbers: the scenarios
differ only in sigma and rho, not in the draws), :func:`check` summarizes bias, interval coverage and the
leave-one-out spread, :func:`bias_table_markdown` prints them.  ``generator_dashboard.py simulate`` wraps the
payload in the envelope and writes ``data/candidates/testing/simulation.json``.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from statistics import NormalDist
from typing import Collection, Optional, Sequence

import numpy as np

from . import estimators as E

#: The three scenarios of :func:`run_scenarios`, in table order.
SCENARIOS = ("equal_independent", "heterogeneous_independent", "heterogeneous_correlated")
#: The estimators :func:`check` summarizes: Chao2 over all occasions, Chapman on occasions 0 and 1.
ESTIMATORS = ("chao2", "chapman_01")
#: Bitmask tables are built per occasion count; more than this many occasions is not a sanity check.
MAX_OCCASIONS = 16

MODEL = ("probit threshold: caught_ij = [sigma z_i + e_ij > t], e_ij = sqrt(rho) c_i + sqrt(1 - rho) u_ij on the "
         "dependent occasions and u_ij on the others, t = sqrt(1 + sigma^2) Phi^-1(1 - p_mean); z, c, u ~ N(0, 1)")


@dataclass(frozen=True)
class SimResult:
    """One synthetic capture history.  ``incidence`` maps each *caught* concept (0..N-1) to the occasions that
    caught it; ``Q`` its incidence frequencies; ``n_by_occasion`` the concepts each occasion caught.
    ``patterns`` is the same incidence as bitmasks (bit j: caught by occasion j), one per key of ``incidence`` in
    ascending order, for the vectorized :func:`estimates`."""

    incidence: dict[int, frozenset[int]]
    Q: Counter
    N: int
    n_by_occasion: list[int]
    m_occ: int = 0
    dependent_occasions: tuple[int, ...] = ()
    patterns: Optional[np.ndarray] = field(default=None, compare=False, repr=False)


@lru_cache(maxsize=None)
def _tables(m_occ: int) -> tuple[np.ndarray, tuple[frozenset[int], ...]]:
    """Per bitmask of ``m_occ`` occasions: its popcount and its occasion set."""
    masks = range(1 << m_occ)
    popcount = np.array([bin(p).count("1") for p in masks], dtype=np.int64)
    sets = tuple(frozenset(j for j in range(m_occ) if p >> j & 1) for p in masks)
    return popcount, sets


def _check_params(N: int, m_occ: int, sigma_catch: float, rho_occ: float, p_mean: float) -> None:
    if N < 0:
        raise ValueError(f"N must be non-negative, got {N}")
    if not 2 <= m_occ <= MAX_OCCASIONS:
        raise ValueError(f"m_occ must be in 2..{MAX_OCCASIONS}, got {m_occ}")
    if sigma_catch < 0:
        raise ValueError(f"sigma_catch must be non-negative, got {sigma_catch}")
    if not 0.0 <= rho_occ <= 1.0:
        raise ValueError(f"rho_occ must be in [0, 1], got {rho_occ}")
    if not 0.0 < p_mean < 1.0:
        raise ValueError(f"p_mean must be in (0, 1), got {p_mean}")


def simulate(N: int = 2000, m_occ: int = 4, sigma_catch: float = 1.0, rho_occ: float = 0.3, seed: int = 0,
             p_mean: float = 0.15, *, dependent_occasions: Optional[Collection[int]] = None) -> SimResult:
    """Draw one capture history under the module's model (``numpy.random.default_rng(seed)``; z, c and u are
    drawn in that order whatever the parameters, so one seed gives the same draws in every scenario).
    ``dependent_occasions`` defaults to every occasion but 0."""
    _check_params(N, m_occ, sigma_catch, rho_occ, p_mean)
    dep = tuple(sorted(set(range(1, m_occ) if dependent_occasions is None else dependent_occasions)))
    if any(not 0 <= j < m_occ for j in dep):
        raise ValueError(f"dependent_occasions {dep} outside 0..{m_occ - 1}")
    rng = np.random.default_rng(seed)
    z = rng.standard_normal(N)
    c = rng.standard_normal(N)
    u = rng.standard_normal((N, m_occ))
    load = np.zeros(m_occ)
    load[list(dep)] = np.sqrt(rho_occ)
    latent = sigma_catch * z[:, None] + c[:, None] * load + u * np.sqrt(1.0 - load ** 2)
    threshold = np.sqrt(1.0 + sigma_catch ** 2) * NormalDist().inv_cdf(1.0 - p_mean)
    catches = latent > threshold
    bits = catches.astype(np.int64) @ (np.int64(1) << np.arange(m_occ, dtype=np.int64))
    caught = np.flatnonzero(bits)
    patterns = bits[caught]
    popcount, sets = _tables(m_occ)
    incidence = {int(i): sets[p] for i, p in zip(caught.tolist(), patterns.tolist())}
    k = popcount[patterns]
    Q = Counter({int(f): int(n) for f, n in enumerate(np.bincount(k, minlength=m_occ + 1)) if f and n})
    return SimResult(incidence=incidence, Q=Q, N=N, n_by_occasion=catches.sum(axis=0).astype(int).tolist(),
                     m_occ=m_occ, dependent_occasions=dep, patterns=patterns)


def _patterns(sim: SimResult) -> tuple[np.ndarray, int]:
    m_occ = sim.m_occ or (max((max(o) for o in sim.incidence.values() if o), default=1) + 1)
    if sim.patterns is not None:
        return sim.patterns, m_occ
    keys = sorted(sim.incidence)
    return np.array([sum(1 << j for j in sim.incidence[c]) for c in keys], dtype=np.int64), m_occ


def _Q_of(patterns: np.ndarray, popcount: np.ndarray) -> dict[int, int]:
    k = popcount[patterns]
    return {int(f): int(n) for f, n in enumerate(np.bincount(k)) if f and n}


def _raw(est: E.Estimate) -> dict[str, float]:
    return {"N": est.N, "se": est.se, "lo": est.lo, "hi": est.hi}


def estimates(sim: SimResult) -> dict:
    """The estimates the dashboard makes, on one synthetic history: Chao2 (bias-corrected) over all occasions,
    Chapman on occasions 0 and 1, and Chao2 with each occasion left out in turn, with the spread of those (max -
    min, and relative to the all-occasion Chao2).  Values unrounded."""
    patterns, m_occ = _patterns(sim)
    popcount, _ = _tables(m_occ)
    Q = _Q_of(patterns, popcount)
    c2 = E.chao2(Q, m_occ)
    n1 = int(np.count_nonzero(patterns & 1))
    n2 = int(np.count_nonzero(patterns & 2))
    m = int(np.count_nonzero((patterns & 3) == 3))
    ch = E.chapman(n1, n2, m)
    loo = []
    for j in range(m_occ):
        rest = patterns & ~(1 << j)
        loo.append(E.chao2(_Q_of(rest[rest > 0], popcount), m_occ - 1).N)
    spread = max(loo) - min(loo)
    return {"S_obs": int(patterns.size), "Q": {str(k): v for k, v in sorted(Q.items())},
            "chao2": {**_raw(c2), "Q1": Q.get(1, 0), "Q2": Q.get(2, 0)},
            "chapman_01": {**_raw(ch), "n1": n1, "n2": n2, "m": m},
            "loo": {"N": loo, "spread": spread, "spread_rel": spread / c2.N if c2.N > 0 else 0.0}}


def check(results: Sequence[dict], truth: int) -> dict:
    """Summarize :func:`estimates` over replicates against the true N: per estimator the mean estimate, the mean
    relative bias (N̂ - N) / N with its standard error and sign (-1, 0, 1), the share of replicates whose 95%
    interval covers N, and the mean standard error; the leave-one-out spread (relative, mean and median); and the
    mean Chao2 estimate with each occasion left out (``loo_mean_N_by_left_out``, where the results carry it), which
    shows *which* occasion moves the estimate."""
    out: dict = {"n_replicates": len(results), "truth": int(truth), "estimators": {}}
    if not results:
        return out
    for name in ESTIMATORS:
        Ns = np.array([r[name]["N"] for r in results], dtype=float)
        bias = (Ns - truth) / truth
        covers = np.array([r[name]["lo"] <= truth <= r[name]["hi"] for r in results])
        rec = {"mean_N": round(float(Ns.mean()), 1), "mean_bias": round(float(bias.mean()), 4),
               "bias_se": round(float(bias.std(ddof=1) / np.sqrt(len(bias))), 4) if len(bias) > 1 else None,
               "bias_sign": int(np.sign(round(float(bias.mean()), 4))), "coverage": round(float(covers.mean()), 4)}
        if all("se" in r[name] for r in results):
            rec["mean_se"] = round(float(np.mean([r[name]["se"] for r in results])), 1)
        out["estimators"][name] = rec
    spreads = np.array([r["loo"]["spread_rel"] for r in results], dtype=float)
    out["loo_spread"] = {"mean": round(float(spreads.mean()), 4), "median": round(float(np.median(spreads)), 4)}
    if all("N" in r["loo"] for r in results) and len({len(r["loo"]["N"]) for r in results}) == 1:
        out["loo_mean_N_by_left_out"] = [round(float(x), 1)
                                         for x in np.mean([r["loo"]["N"] for r in results], axis=0)]
    if all("S_obs" in r for r in results):
        out["mean_S_obs"] = round(float(np.mean([r["S_obs"] for r in results])), 1)
    return out


def replicate_seeds(seed: int, replicates: int) -> list[int]:
    """The replicate seeds of :func:`run_scenarios`, derived from ``seed`` (``numpy.random.SeedSequence``)."""
    return [int(s) for s in np.random.SeedSequence(seed).generate_state(replicates)] if replicates > 0 else []


def run_scenarios(*, N: int = 2000, m_occ: int = 4, sigma: float = 1.0, rho: float = 0.3, replicates: int = 200,
                  seed: int = 0, p_mean: float = 0.15) -> dict:
    """The sanity run: ``replicates`` histories in each of the three scenarios (equal catchability and independent
    occasions; heterogeneous and independent; heterogeneous with the dependent occasions correlated), the same
    replicate seeds in each, and :func:`check` for each.  JSON-serializable (the CLI adds the envelope)."""
    _check_params(N, m_occ, sigma, rho, p_mean)
    settings = {"equal_independent": (0.0, 0.0), "heterogeneous_independent": (float(sigma), 0.0),
                "heterogeneous_correlated": (float(sigma), float(rho))}
    seeds = replicate_seeds(seed, replicates)
    scenarios = {}
    for name in SCENARIOS:
        s, r = settings[name]
        results = [estimates(simulate(N, m_occ, s, r, seed=x, p_mean=p_mean)) for x in seeds]
        scenarios[name] = {"sigma_catch": s, "rho_occ": r, "check": check(results, N)}
    return {"params": {"N": N, "m_occ": m_occ, "sigma": float(sigma), "rho": float(rho), "p_mean": float(p_mean),
                       "replicates": replicates, "seed": seed, "dependent_occasions": list(range(1, m_occ)),
                       "chapman_occasions": [0, 1], "model": MODEL},
            "scenarios": scenarios}


def bias_table_markdown(result: dict) -> str:
    """The bias table of a :func:`run_scenarios` payload: per scenario and estimator the mean estimate, the mean
    bias, the interval coverage, and (Chao2 only) the mean leave-one-occasion-out spread."""
    p = result["params"]
    lines = ["| scenario | sigma | rho | estimator | mean N̂ | bias | interval coverage | leave-one-out spread |",
             "|---|---|---|---|---|---|---|---|"]
    for name in SCENARIOS:
        sc = result["scenarios"].get(name)
        if sc is None:
            continue
        chk = sc["check"]
        for est in ESTIMATORS:
            rec = chk["estimators"].get(est)
            if rec is None:
                continue
            loo = f"{chk['loo_spread']['mean'] * 100:.1f}%" if est == "chao2" and "loo_spread" in chk else "n/a"
            lines.append(f"| {name} | {sc['sigma_catch']:g} | {sc['rho_occ']:g} | {est} | {rec['mean_N']:,.0f} | "
                         f"{rec['mean_bias'] * 100:+.1f}% | {rec['coverage'] * 100:.0f}% | {loo} |")
    lines.append("")
    lines.append(f"True N = {p['N']:,}; {p['m_occ']} occasions, marginal catch rate {p['p_mean']:g}; "
                 f"{p['replicates']} replicates per scenario, seed {p['seed']}; Chapman on occasions 0 and 1; "
                 f"rho loads on occasions {', '.join(map(str, p['dependent_occasions']))}.  Bias is the mean of "
                 f"(N̂ - N) / N; coverage the share of 95% intervals containing N; the spread is (max - min) / N̂ "
                 f"over the Chao2 estimates with one occasion left out.")
    return "\n".join(lines) + "\n"
