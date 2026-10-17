"""A filler's fold: British to US spelling, then the platform's noun helper (open decision 3).

**No local relabel rules.**  The noun-to-adjective step is ``assistant_axis.gapgen.nouns.relabel`` (built 2026-10-14,
``coding_plan_noun_normalization.md``: the base model's suffix fold, OEWN's derivation link from a person or quality
sense, the person- and quality-noun suffix rules, each gated on OEWN having the adjective and on Zipf 1.5), and the
spelling fold is ``nouns.us_spelling`` (entity-naming: US English).  The platform runs the same helper in
``submit_candidates``, which submits a noun as the generator emitted it and adds its adjective as a linked sibling,
so the table (:mod:`.table`) calls :func:`fold` for two things only: to merge a noun filler with the adjective it
relabels to (``known for his honesty`` and ``a very honest man`` are one row, ``honest``), and for the row's
``form`` / ``relabel_rule`` columns (the helper's answer per filler, for the readout).

:func:`is_person_noun` is the person-noun test of the nominal frames: Open English WordNet's person-noun hyponyms
(``masked_lm.wordlist.person_noun_lemmas``, the closure under *person* and *actor*), loaded once by the caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Collection, Optional

from assistant_axis.gapgen import nouns as N

FORMS: tuple[str, ...] = ("adjective", "noun", "phrase")
#: The helper's reasons that mean "a noun, left as it is" (the rest: an adjective already, or not a word OEWN has).
NOUN_REASONS = frozenset({"person_no_adjective", "quality_no_adjective", "other_noun", "pertainym_only",
                          "below_floor"})


@dataclass(frozen=True)
class Fold:
    raw: str                         # the filler as the corpus spells it
    surface: str                     # US spelling, lower case (what the platform would be given)
    label: str                       # the helper's adjective when it relabels, else ``surface``
    form: str                        # adjective | noun | phrase (of ``label``)
    rule: Optional[str]              # the helper's rule; "none" for a noun it leaves; None for an adjective
    reason: Optional[str]            # the helper's NoRelabel reason, else None
    us_spelling_from: Optional[str]  # ``raw`` when the spelling fold changed it

    @property
    def relabelled(self) -> bool:
        return self.label != self.surface


def is_multiword(s: str) -> bool:
    return " " in s or "-" in s


def fold(filler: str, *, lookups: N.NounLookups, kind_hint: str = "adj") -> Fold:
    """The fold of one filler (see the module docstring).  ``kind_hint`` (the frame's filler kind) gives the form of a
    word OEWN does not have: ``adjective`` for an adjective frame, ``noun`` for a nominal or possessive frame."""
    raw = " ".join(str(filler).split())
    low = raw.lower()
    us = N.us_spelling(low, lexicon=lookups.lexicon())
    r = N.relabel(us, lookups=lookups)
    if isinstance(r, N.Relabel):
        label = r.adjective
        return Fold(raw=raw, surface=us, label=label, form="phrase" if is_multiword(label) else "adjective",
                    rule=r.rule, reason=None, us_spelling_from=raw if us != low else None)
    reason = r.reason
    if is_multiword(us):
        form = "phrase"
    elif reason == "has_adjective_sense":
        form = "adjective"
    elif reason in NOUN_REASONS:
        form = "noun"
    else:                                  # not in OEWN, or not a noun (a verb or adverb only): the frame decides
        form = "adjective" if kind_hint == "adj" else "noun"
    return Fold(raw=raw, surface=us, label=us, form=form, rule="none" if form == "noun" else None, reason=reason,
                us_spelling_from=raw if us != low else None)


def is_person_noun(noun: str, person_nouns: Collection[str]) -> bool:
    """Whether ``noun`` (any case, hyphen or space) is one of OEWN's person-noun lemmas."""
    s = " ".join(str(noun).lower().split())
    return s in person_nouns or s.replace("-", " ") in person_nouns or s.replace(" ", "-") in person_nouns


def person_nouns_from_oewn(wordnet=None) -> frozenset:  # pragma: no cover - the OEWN database
    """OEWN's person-noun lemmas, lower case (the hyponym closure of *person* and *actor*)."""
    from ..masked_lm.wordlist import person_noun_lemmas
    if wordnet is None:
        from assistant_axis.gapgen.wordnet import oewn
        wordnet = oewn()
    return frozenset(x.lower() for x in person_noun_lemmas(wordnet))


__all__ = ["FORMS", "NOUN_REASONS", "Fold", "fold", "is_multiword", "is_person_noun", "person_nouns_from_oewn"]
