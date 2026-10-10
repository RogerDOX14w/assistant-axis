"""The diversity harness (frozen interface; plan 03 section 7 promises it to the other workstreams).

Usable on any generator's emission stream, and needing nothing but stems and counts:

* :func:`rarefaction`: distinct candidates against draws.  A flattening curve says the generator is running
  out of new words.  Given a flat sequence of stems, one draw is one emission; given a sequence of lists
  (one list per sample, as the base-model generator records them), one draw is one sample.
* :func:`chao1`: an estimate of the total vocabulary reachable, from the number of words seen once (f1) and
  twice (f2): ``S_obs + f1^2 / (2 f2)``, and the bias-corrected ``S_obs + f1 (f1 - 1) / 2`` when no word was
  seen twice (Chao 1987; Colwell's EstimateS recommendation).
* :func:`collapse_index`: the share of all emissions taken by the ``top`` most frequent candidates (plan 03
  section 6: target under 15% for the top 50; high means the generator repeats a cliché set).
* :func:`string_recovery`: the fraction of the corpus's trait stems (or their ``renamed_from``) found among
  the candidates as strings.  An evaluation figure only; it never feeds eligibility.
* :func:`per_family`: emissions, samples and distinct stems per prompt family.

Signatures are added to, never renamed, without a note in the plan's "Frozen interface" section.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping, Optional, Sequence, Union

Counts = Union[Mapping[str, int], Iterable[int]]


def _values(counts: Counts) -> list[int]:
    if isinstance(counts, Mapping):
        return [int(v) for v in counts.values()]
    return [int(v) for v in counts]


def rarefaction(stems_in_order: Sequence, step: int = 1000) -> list[tuple[int, int]]:
    """``[(draws, distinct stems so far), ...]`` every ``step`` draws and at the end.

    ``stems_in_order`` is either a flat sequence of stems (a draw is one emission) or a sequence of
    lists / tuples / sets of stems (a draw is one sample, whose emissions all count at once)."""
    if step < 1:
        raise ValueError("step must be >= 1")
    seen: set[str] = set()
    out: list[tuple[int, int]] = []
    n = 0
    for n, item in enumerate(stems_in_order, 1):
        if isinstance(item, (list, tuple, set, frozenset)):
            seen.update(item)
        else:
            seen.add(item)
        if n % step == 0:
            out.append((n, len(seen)))
    if n and (not out or out[-1][0] != n):
        out.append((n, len(seen)))
    return out


def chao1(counts: Counts) -> float:
    """Chao1 richness estimate from per-stem counts (a mapping or the counts alone)."""
    vals = [v for v in _values(counts) if v > 0]
    s_obs = len(vals)
    f1 = sum(1 for v in vals if v == 1)
    f2 = sum(1 for v in vals if v == 2)
    if f1 == 0:
        return float(s_obs)
    if f2 > 0:
        return s_obs + f1 * f1 / (2.0 * f2)
    return s_obs + f1 * (f1 - 1) / 2.0


def collapse_index(counts: Counts, top: int = 50) -> float:
    """Share of all emissions taken by the ``top`` most frequent candidates (0 when there are none)."""
    vals = sorted(_values(counts), reverse=True)
    total = sum(vals)
    return sum(vals[:top]) / total if total else 0.0


def string_recovery(stems: Iterable[str], corpus_stems: Iterable[str],
                    renamed: Optional[Mapping[str, str]] = None) -> dict:
    """Corpus stems found among ``stems`` as strings.  ``renamed`` maps a corpus file's old stem
    (``renamed_from``) to its current stem, so a candidate spelling the old name recovers the current one.

    Returns ``{"n_corpus", "found", "recall", "found_stems", "via_renamed_from"}``."""
    corpus = set(corpus_stems)
    renamed = dict(renamed or {})
    found: set[str] = set()
    via: dict[str, str] = {}
    for s in set(stems):
        if s in corpus:
            found.add(s)
        elif s in renamed and renamed[s] in corpus:
            found.add(renamed[s])
            via[s] = renamed[s]
    return {"n_corpus": len(corpus), "found": len(found),
            "recall": round(len(found) / len(corpus), 4) if corpus else 0.0,
            "found_stems": sorted(found), "via_renamed_from": dict(sorted(via.items()))}


def per_family(rows: Iterable[Mapping], *, samples: Optional[Iterable[Mapping]] = None) -> dict[str, dict]:
    """Per prompt family: ``n_emissions`` (sums to the total over families), ``n_unique`` (stems the family
    emitted at least once; these overlap across families), ``n_only_here`` (stems no other family emitted),
    and, given the samples, ``n_samples`` (sums to the sample count) and ``uniques_per_1k``.

    A row is a mapping with ``stem``, ``count`` and ``families`` (family -> emissions); a sample a mapping
    with ``family``."""
    emis: Counter = Counter()
    uniq: Counter = Counter()
    only: Counter = Counter()
    for r in rows:
        fams = {f: int(c) for f, c in (r.get("families") or {}).items() if c}
        for f, c in fams.items():
            emis[f] += c
            uniq[f] += 1
        if len(fams) == 1:
            only[next(iter(fams))] += 1
    n_samp: Counter = Counter(s.get("family") for s in samples) if samples is not None else Counter()
    out: dict[str, dict] = {}
    for f in sorted(set(emis) | set(n_samp)):
        d = {"n_emissions": emis[f], "n_unique": uniq[f], "n_only_here": only[f]}
        if samples is not None:
            d["n_samples"] = n_samp[f]
            d["uniques_per_1k"] = round(1000.0 * uniq[f] / n_samp[f], 1) if n_samp[f] else None
        out[f] = d
    return out
