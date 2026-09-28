"""Word-frequency floor (``wordfreq`` Zipf scale), a feature and not a gate.

Zipf = log10 occurrences per billion words.  Decision (plan 14 resolution 3,
measured on the corpus labels): hard reject only below Zipf 2.0 (keeps about
95% of our own labels); 2.0 <= Zipf < 2.5 goes to a cheap definition probe;
Zipf is recorded on every row either way.  For a phrase the floor uses the
**rarest content word** (``normalize.content_words``: function words from a
fixed stoplist are skipped), since ``wordfreq``'s own phrase estimate mixes
in the function words.

Familiarity override (interface resolution 4): when a generator documents its
``Candidate.score`` as a human familiarity (:data:`FAMILIARITY_GENERATORS`)
and the score is >= 0.5, a word below Zipf 2.0 goes to the definition probe
instead of the hard reject.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from .normalize import normalize_candidate

HARD_REJECT_BELOW = 2.0
PROBE_BELOW = 2.5
FAMILIARITY_OVERRIDE_MIN = 0.5

#: Generators whose ``Candidate.score`` is a documented human familiarity
#: (the proportion of raters who knew the word).  Add a generator here only
#: with a pointer to where its plan documents the score.
FAMILIARITY_GENERATORS: dict[str, str] = {
    "censuses": "TDA `prop`: proportion of raters who knew the word "
                "(coding_plan_01_censuses.md, decisions table)",
}


@dataclass(frozen=True)
class FreqInfo:
    zipf_min: float
    zipf_words: dict = field(default_factory=dict)
    hard_reject: bool = False
    probe_band: bool = False
    familiarity_override: bool = False

    def as_block(self) -> dict:
        """The registry ``freq`` block (``define_probe`` is filled by the filter)."""
        d = asdict(self)
        d["define_probe"] = None
        return d


def _default_zipf() -> Callable[[str], float]:
    from wordfreq import zipf_frequency

    return lambda w: float(zipf_frequency(w, "en"))


_ZIPF_FN: Optional[Callable[[str], float]] = None


def zipf_info(surface: str, *, familiarity: Optional[float] = None,
              zipf_fn: Optional[Callable[[str], float]] = None) -> FreqInfo:
    """Frequency features of a candidate surface.

    ``familiarity`` is a documented familiarity score in [0, 1] (see
    :func:`familiarity_of`); ``zipf_fn`` replaces ``wordfreq`` in tests.
    """
    global _ZIPF_FN
    if zipf_fn is None:
        if _ZIPF_FN is None:
            _ZIPF_FN = _default_zipf()
        zipf_fn = _ZIPF_FN
    words = normalize_candidate(surface).content_words
    zw = {w: round(zipf_fn(w), 2) for w in words}
    zmin = min(zw.values()) if zw else 0.0
    override = zmin < HARD_REJECT_BELOW and familiarity is not None and familiarity >= FAMILIARITY_OVERRIDE_MIN
    hard = zmin < HARD_REJECT_BELOW and not override
    probe = (HARD_REJECT_BELOW <= zmin < PROBE_BELOW) or override
    return FreqInfo(zipf_min=zmin, zipf_words=zw, hard_reject=hard, probe_band=probe,
                    familiarity_override=override)


def familiarity_of(rec: dict) -> Optional[float]:
    """Highest documented familiarity among a registry row's sources, or None."""
    vals = [float(s["score"]) for s in rec.get("sources") or []
            if s.get("generator") in FAMILIARITY_GENERATORS and s.get("score") is not None]
    return max(vals) if vals else None
