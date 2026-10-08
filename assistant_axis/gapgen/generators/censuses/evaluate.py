"""Checks that need only the corpus files, the census table and the registry.

* :func:`string_ceiling`: how many corpus trait stems appear in the TDA, in Allport-Odbert and
  in either, as strings (plan sections 6 and 8), and how many of those the generator's own
  eligibility rule submits (``submitted_of_matched``, the "keep 95% of existing labels" policy).
* :func:`known_label_pass`: of the corpus labels a run submitted, the fraction the platform's
  filter passes (verdict ``trait``, or ``tagged`` with ``state`` or ``physical``); available
  once the filter has run on the run's rows.
* :func:`state_gloss_compliance`, :func:`cost_summary`, :func:`evaluate_run`.

The recovery parts of the original plan are dropped (revision of 2026-10-08): recovery is the
platform's ``recovery_test.py``.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from .ingest import TableRow

PASS_TAGS = ("state", "physical")
TENDENCY_RE = re.compile(r"\b(general tendency|tendency to|tendency toward|disposition|disposed to|prone to|"
                         r"habitually|characteristically)\b", re.IGNORECASE)


@dataclass
class Ceiling:
    n_corpus: int
    n_multiword: int
    n_tda: int
    n_allport: int
    n_union: int
    tda: float
    allport: float
    union: float
    union_single_word: float
    n_matched_eligible: int
    submitted_of_matched: float
    matched_ineligible: list[str] = field(default_factory=list)
    n_queue: int = 0
    n_queue_union: int = 0

    def as_dict(self) -> dict:
        return asdict(self)


def _frac(a: int, b: int) -> float:
    return round(a / b, 4) if b else 0.0


def string_ceiling(table: Sequence[TableRow], corpus_stems: Iterable[str],
                   queue_stems: Iterable[str] = ()) -> Ceiling:
    corpus = set(corpus_stems)
    queue = set(queue_stems) - corpus
    tda = {r.stem for r in table if r.stem and r.tda}
    allport = {r.stem for r in table if r.stem and r.allport}
    union = tda | allport
    eligible = {r.stem for r in table if r.stem and r.eligible}
    matched = corpus & union
    single = {s for s in corpus if "_" not in s}
    return Ceiling(
        n_corpus=len(corpus), n_multiword=len(corpus - single), n_tda=len(corpus & tda),
        n_allport=len(corpus & allport), n_union=len(matched), tda=_frac(len(corpus & tda), len(corpus)),
        allport=_frac(len(corpus & allport), len(corpus)), union=_frac(len(matched), len(corpus)),
        union_single_word=_frac(len(single & union), len(single)),
        n_matched_eligible=len(matched & eligible), submitted_of_matched=_frac(len(matched & eligible), len(matched)),
        matched_ineligible=sorted(matched - eligible), n_queue=len(queue), n_queue_union=len(queue & union))


@dataclass
class PassRates:
    n_known: int                 # corpus labels among the rows
    n_filtered: int              # of those, rows with a filter block
    n_pass: int
    pass_rate: Optional[float]
    by_outcome: dict
    misses: list[dict] = field(default_factory=list)
    unfiltered: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def is_pass(filter_block: Mapping) -> bool:
    v = filter_block.get("verdict")
    return v == "trait" or (v == "tagged" and bool(set(filter_block.get("tags") or []) & set(PASS_TAGS)))


def known_label_pass(rows: Iterable[Mapping], corpus_stems: Iterable[str]) -> PassRates:
    """``rows`` are registry rows (dicts with ``stem`` and an optional ``filter`` block)."""
    corpus = set(corpus_stems)
    known = [r for r in rows if r.get("stem") in corpus]
    filtered = [r for r in known if r.get("filter")]
    passed = [r for r in filtered if is_pass(r["filter"])]
    misses = [{"stem": r["stem"], "verdict": r["filter"].get("verdict"), "outcome": r["filter"].get("outcome"),
               "tags": r["filter"].get("tags"), "rule": r["filter"].get("rule")}
              for r in filtered if not is_pass(r["filter"])]
    return PassRates(n_known=len(known), n_filtered=len(filtered), n_pass=len(passed),
                     pass_rate=_frac(len(passed), len(filtered)) if filtered else None,
                     by_outcome=dict(sorted(Counter((r["filter"].get("outcome") or r["filter"].get("verdict"))
                                                    for r in filtered).items())),
                     misses=sorted(misses, key=lambda m: m["stem"]),
                     unfiltered=sorted(r["stem"] for r in known if not r.get("filter")))


def state_gloss_compliance(rows: Iterable[Mapping]) -> Optional[float]:
    """Of the rows the filter tagged ``state``, the fraction whose gloss reads as a tendency."""
    states = [r for r in rows if "state" in ((r.get("filter") or {}).get("tags") or [])]
    if not states:
        return None
    ok = sum(1 for r in states if TENDENCY_RE.search(r.get("gloss") or (r.get("filter") or {}).get("gloss") or ""))
    return _frac(ok, len(states))


def cost_summary(usage_paths: Iterable[Path]) -> dict:
    """Sum ``usage.json`` files (``MultiModelUsage.as_dict`` shape) per model."""
    per_model: dict[str, float] = {}
    files = []
    for p in usage_paths:
        p = Path(p)
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        files.append(str(p))
        for m, u in (d.get("per_model") or {}).items():
            per_model[m] = round(per_model.get(m, 0.0) + float(u.get("cost_usd") or 0.0), 6)
    return {"files": files, "per_model": dict(sorted(per_model.items())),
            "total_usd": round(sum(per_model.values()), 6)}


def run_rows(registry_rows: Mapping[str, Mapping], generator: str, run_id: str) -> list[Mapping]:
    """Registry rows with a source from this run, sorted by key."""
    return [r for k, r in sorted(registry_rows.items())
            if any(s.get("generator") == generator and s.get("run_id") == run_id for s in r.get("sources") or [])]
