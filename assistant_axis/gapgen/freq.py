"""Word-frequency floor (``wordfreq`` Zipf scale), a feature and not a gate.

Zipf = log10 occurrences per billion words.  Decision 1 of
``reports/trait_gap_generation/decisions_m1.md`` (Roger, 2026-09-29): hard
reject only below Zipf **1.5** (it cuts 13 of the 659 corpus labels and still
removes 27% of random dictionary adjectives for free); **1.5 <= Zipf < 2.5**
goes to a cheap definition probe; Zipf is recorded on every row either way.
For a phrase the floor uses the **rarest content word**
(``normalize.content_words``: function words from a fixed stoplist are
skipped, and hyphenated compounds are split into their parts), since
``wordfreq``'s own phrase estimate mixes in the function words.

Rescue rule 1b (approved, all three routes): a word below the floor goes to
the probe, not the bin, when

1. ``negating_prefix``: every content word below the floor is formed from a
   word at or above the floor by a negating prefix (un-, in-, non-).  A
   hyphenated compound whose parts all pass needs no rescue: its parts are
   scored separately, so it is never below the floor (and one whose part is
   below the floor, such as strong-stomached, is not rescued);
2. ``gloss_hint``: it arrives with a gloss hint (the generator says which
   sense it means);
3. ``curated_source``: one of its sources is a curated generator
   (:data:`CURATED_GENERATORS`), not a dictionary walk.

Familiarity override (interface resolution 4): when a generator documents its
``Candidate.score`` as a human familiarity (:data:`FAMILIARITY_GENERATORS`)
and the score is >= 0.5, a word below the floor also goes to the probe.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

from .normalize import normalize_candidate

HARD_REJECT_BELOW = 1.5
PROBE_BELOW = 2.5
FAMILIARITY_OVERRIDE_MIN = 0.5
NEGATING_PREFIXES = ("non", "un", "in")

#: Generators whose ``Candidate.score`` is a documented human familiarity
#: (the proportion of raters who knew the word).  Add a generator here only
#: with a pointer to where its plan documents the score.
FAMILIARITY_GENERATORS: dict[str, str] = {
    "censuses": "TDA `prop`: proportion of raters who knew the word "
                "(coding_plan_01_censuses.md, decisions table)",
}

#: Curated generators (rescue route 3): their candidates come from a curated
#: source such as a psychology inventory, not a dictionary walk, so a word
#: below the floor goes to the probe.  Add a generator only with a pointer to
#: the plan that justifies it.  The Roget and WordNet harvest
#: (coding_plan_02_roget_wordnet.md) is a dictionary walk and is NOT curated.
CURATED_GENERATORS: dict[str, str] = {
    "censuses": "psycholexical censuses: TDA and Allport-Odbert person-descriptive word lists "
                "(coding_plan_01_censuses.md; decisions_m1.md, rule 1b and 'Curated sources')",
}


@dataclass(frozen=True)
class FreqInfo:
    zipf_min: float
    zipf_words: dict = field(default_factory=dict)
    hard_reject: bool = False
    probe_band: bool = False
    familiarity_override: bool = False
    rescue: Optional[str] = None   # negating_prefix | gloss_hint | curated_source | familiarity

    def as_block(self) -> dict:
        """The registry ``freq`` block (``define_probe`` is filled by the filter)."""
        d = asdict(self)
        d["define_probe"] = None
        return d


def _default_zipf() -> Callable[[str], float]:
    from wordfreq import zipf_frequency

    return lambda w: float(zipf_frequency(w, "en"))


_ZIPF_FN: Optional[Callable[[str], float]] = None


def _negated_base(word: str) -> Optional[str]:
    w = word.lower()
    for p in NEGATING_PREFIXES:
        if w.startswith(p) and len(w) - len(p) >= 3:
            return w[len(p):].lstrip("-")
    return None


def zipf_info(surface: str, *, familiarity: Optional[float] = None, gloss_hint: bool = False,
              curated: bool = False, zipf_fn: Optional[Callable[[str], float]] = None) -> FreqInfo:
    """Frequency features of a candidate surface.

    ``familiarity`` is a documented familiarity score in [0, 1] (see
    :func:`familiarity_of`); ``gloss_hint`` and ``curated`` say whether the
    candidate arrived with a gloss hint or from a curated generator (rescue
    routes 2 and 3); ``zipf_fn`` replaces ``wordfreq`` in tests.
    """
    global _ZIPF_FN
    if zipf_fn is None:
        if _ZIPF_FN is None:
            _ZIPF_FN = _default_zipf()
        zipf_fn = _ZIPF_FN
    words = normalize_candidate(surface).content_words
    zw = {w: round(zipf_fn(w), 2) for w in words}
    zmin = min(zw.values()) if zw else 0.0
    below = zmin < HARD_REJECT_BELOW
    rescue = None
    override = False
    if below:
        low = [w for w, v in zw.items() if v < HARD_REJECT_BELOW]
        bases = [_negated_base(w) for w in low]
        if all(b and round(zipf_fn(b), 2) >= HARD_REJECT_BELOW for b in bases):
            rescue = "negating_prefix"
        elif gloss_hint:
            rescue = "gloss_hint"
        elif curated:
            rescue = "curated_source"
        elif familiarity is not None and familiarity >= FAMILIARITY_OVERRIDE_MIN:
            rescue = "familiarity"
            override = True
    hard = below and rescue is None
    probe = (HARD_REJECT_BELOW <= zmin < PROBE_BELOW) or rescue is not None
    return FreqInfo(zipf_min=zmin, zipf_words=zw, hard_reject=hard, probe_band=probe,
                    familiarity_override=override, rescue=rescue)


def familiarity_of(rec: dict) -> Optional[float]:
    """Highest documented familiarity among a registry row's sources, or None."""
    vals = [float(s["score"]) for s in rec.get("sources") or []
            if s.get("generator") in FAMILIARITY_GENERATORS and s.get("score") is not None]
    return max(vals) if vals else None


def is_curated(rec: dict) -> bool:
    """True when any of a registry row's sources is a curated generator."""
    return any(s.get("generator") in CURATED_GENERATORS for s in rec.get("sources") or [])


def is_free_floor_reject(rec: dict) -> bool:
    """True when a registry row's filter block is the frequency floor's reject, made without a call:
    the split filter's ``rule`` "floor", or the single-call filter's hard reject (``freq.hard_reject``,
    no model, tag ``too_rare``).  A definition-probe cut (``rule`` "probe") is a paid verdict and is
    not one."""
    f = rec.get("filter") or {}
    if not f:
        return False
    if f.get("rule") == "floor":
        return True
    return (bool((rec.get("freq") or {}).get("hard_reject")) and f.get("model") is None
            and "too_rare" in (f.get("tags") or []))


def floor_reject_rescued(rec: dict, *, zipf_fn: Optional[Callable[[str], float]] = None) -> bool:
    """Defect F3 (gate audit 1, 2026-10-12): True when a row's only filter verdict is the floor's free
    reject (:func:`is_free_floor_reject`) and the row's *current* sources would rescue the word, so the
    filter would no longer reject it unread.

    The registry merges a later source into an existing row and keeps its filter block, so the first
    generator to reach a stem decided its floor: ``irresolute`` was floor-rejected under
    ``antonym_check`` (not curated, no gloss hint) and the TDA's curated source and gloss hint never
    applied.  M1's row selection (``traithood_filter.py --run`` / ``--unfiltered``) takes such a row as
    unfiltered.  The test is :func:`zipf_info` with the row's current context, the same call the filter
    makes before any model call."""
    if not is_free_floor_reject(rec):
        return False
    hint = any(s.get("gloss_hint") for s in rec.get("sources") or [])
    label = rec.get("label") or rec.get("surface") or rec.get("stem") or ""
    if not label:
        return False
    fq = zipf_info(label, familiarity=familiarity_of(rec), gloss_hint=hint, curated=is_curated(rec),
                   zipf_fn=zipf_fn)
    return not fq.hard_reject
