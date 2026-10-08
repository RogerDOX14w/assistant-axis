"""One-line sense hints from Open English WordNet (the filter writes the real gloss).

``gloss_hint`` is what the platform shows the filter as the candidate's intended sense
(interface resolution 1).  The person-descriptive adjective sense is preferred: the first
adjective sense whose definition matches :data:`PERSON_RE`, else the first adjective sense,
else the first sense of any part of speech with its part of speech appended.  An Allport-Odbert
column II word (temporary states) is framed as a disposition; a column IV word (metaphorical or
doubtful) is marked as such.  No LLM is called.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Sequence

ADJ_POS = ("a", "s")
POS_NAMES = {"n": "noun", "v": "verb", "r": "adverb"}
MAX_WORDS = 25
#: The plan's person-descriptive pattern (section 6), split in two tiers: a definition naming a
#: person, a disposition or a manner outranks one that only opens with "having", "showing" or
#: "lacking" (OEWN uses those for plants and objects too: nodding is "having branches or flower
#: heads that bend downward").
PERSON_RE = re.compile(
    r"\b(person|people|someone|one who|disposition|inclined|disposed|tending|habitually|manner|"
    r"behaviou?r|mood|temperament|having|showing|marked by|characterized by|given to|lacking)\b",
    re.IGNORECASE)
WEAK_PERSON_RE = re.compile(r"\b(having|showing|lacking)\b", re.IGNORECASE)
STATE_PREFIX = "disposition to be {label} (a general tendency, not an episode): "
METAPHOR_SUFFIX = " (metaphorical or doubtful in Allport-Odbert)"


@dataclass(frozen=True)
class Sense:
    definition: str
    pos: str


@dataclass(frozen=True)
class SenseHint:
    definition: str
    rank: int            # 1-based, among the adjective senses (or among all senses for the fallback)
    n_adj_senses: int
    pos: str


def lookup_forms(surface: str) -> list[str]:
    """The surface, then hyphen <-> space variants, then the hyphen dropped."""
    s = " ".join(surface.strip().lower().split())
    forms = [s, s.replace("-", " "), s.replace(" ", "-"), s.replace("-", "")]
    out: list[str] = []
    for f in forms:
        if f and f not in out:
            out.append(f)
    return out


def _clean_definition(text: str) -> str:
    """The definition up to its first semicolon (OEWN appends usage notes after one)."""
    return " ".join(text.split(";", 1)[0].split()).strip()


def adjective_senses(lemma: str, *, wordnet=None) -> list[Sense]:
    """Every OEWN sense of the first lookup form that has any: adjective senses first, in the
    lemma's own sense order, then the other parts of speech.  ``wordnet`` is any object with a
    ``words(form)`` method (the real ``wn.Wordnet`` or a fake); by default the OEWN handle."""
    if wordnet is None:
        from assistant_axis.gapgen.wordnet import oewn
        wordnet = oewn()
    for form in lookup_forms(lemma):
        words = list(wordnet.words(form))
        if not words:
            continue
        adj, other = [], []
        for w in words:
            pos = "a" if w.pos in ADJ_POS else w.pos
            for s in w.senses():
                syn = s.synset()
                sp = syn.pos if getattr(syn, "pos", None) else pos
                (adj if sp in ADJ_POS else other).append(Sense(_clean_definition(syn.definition() or ""), sp))
        return adj + other
    return []


def _strong(defn: str) -> bool:
    """Matches :data:`PERSON_RE` on a word other than the weak openers."""
    return any(m.group(0).lower() not in ("having", "showing", "lacking") for m in PERSON_RE.finditer(defn))


def person_sense(senses: Sequence[Sense]) -> Optional[SenseHint]:
    """The first adjective sense with a strong person cue, else the first with a weak one, else
    the first adjective sense, else the first sense of any part of speech."""
    adj = [s for s in senses if s.pos in ADJ_POS]
    for test in (_strong, lambda d: bool(PERSON_RE.search(d))):
        for i, s in enumerate(adj, 1):
            if test(s.definition):
                return SenseHint(s.definition, i, len(adj), s.pos)
    if adj:
        return SenseHint(adj[0].definition, 1, len(adj), adj[0].pos)
    if senses:
        return SenseHint(senses[0].definition, 1, 0, senses[0].pos)
    return None


def _fit(prefix: str, body: str, suffix: str, limit: int = MAX_WORDS) -> str:
    """Cut ``body`` at a word boundary so that the whole hint has at most ``limit`` words."""
    room = max(limit - len(prefix.split()) - len(suffix.split()), 1)
    words = body.split()
    return prefix + " ".join(words[:room]) + suffix


def gloss_hint(label: str, hint: Optional[SenseHint], columns: Sequence[str] = (), *,
               in_tda: bool = False) -> Optional[str]:
    """The hint for a census row (None when OEWN lacks the word).

    Column II only (not also column I): the adjective sense is framed as a disposition (the
    prefix is left off when the only sense found is a noun or verb, where it would not parse).
    Column IV only, and not in the TDA: the metaphorical-or-doubtful note is appended (a TDA
    word is a trait-descriptive adjective by the TDA's own selection)."""
    if hint is None or not hint.definition:
        return None
    cols = list(columns)
    adjective = hint.pos in ADJ_POS
    prefix = STATE_PREFIX.format(label=label) if ("II" in cols and "I" not in cols and adjective) else ""
    suffix = f" ({POS_NAMES[hint.pos]})" if not adjective and hint.pos in POS_NAMES else ""
    if cols == ["IV"] and not in_tda:
        suffix += METAPHOR_SUFFIX
    return _fit(prefix, hint.definition, suffix)
