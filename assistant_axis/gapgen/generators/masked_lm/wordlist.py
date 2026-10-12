"""Variant B's universe and the stoplist flags (plan section 5, ``wordlist.py``).

:func:`oewn_candidates`: Open English WordNet's adjective lemmas (``a`` and satellite ``s``) plus the lemmas of its
person nouns, deduplicated by stem (``normalize_to_file_name``; the lower-case spelling wins a tie), sorted.  The
person nouns are the hyponym closure of two synsets: **person** ("a human being") and, because OEWN 2024 hangs
most person nouns (leader, optimist, pacifist, sycophant) under it rather than under person,
**actor / doer / worker** ("a person who acts and gets things done").  Checked 2026-10-11: 1,949 synsets under
person and 10,431 under actor (18,827 lemmas together); 21,632 adjective lemmas.  A person noun spelt with a
capital is a proper name (an instance: a king, a saint) and is left out; adjectives keep their case
("Kantian").  Lemmas of more than four words, or with characters other than letters, spaces, hyphens and
apostrophes, are left out.  The plan expected "roughly 20-25k words"; the count is printed by ``generate``.

:func:`stoplist_flags` flags memberships (religions, nationalities and other demonyms): **flagged, never
dropped** (memberships are traits, decisions_m1 decision 3; pre-registered question 3).
"""
from __future__ import annotations

import re
from typing import Iterable, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

ADJ_POS = ("a", "s")
#: (lemma, the start of its definition) of each person-noun root: found by text, so a renumbered OEWN still works.
PERSON_ROOTS: tuple[tuple[str, str], ...] = (("person", "a human being"),
                                             ("actor", "a person who acts and gets things done"))
MAX_WORDS = 4
_OK = re.compile(r"^[A-Za-z][A-Za-z' \-]*[A-Za-z]$")

RELIGIONS = frozenset("""
amish anglican baptist bahai buddhist calvinist catholic christian episcopalian evangelical hasidic hindu islamic
jain jewish judaic lutheran mennonite methodist mormon moslem muslim pentecostal presbyterian protestant puritan
quaker rastafarian shiite shia sikh sufi sunni taoist unitarian wiccan zoroastrian shinto confucian jew
""".split())
_NATIONALITY_RE = re.compile(r"\b(native or inhabitant|inhabitant of|of or relating to\b.*\b(people|language|"
                             r"inhabitants|culture|nation))\b", re.IGNORECASE)


def _ok(lemma: str) -> bool:
    return bool(_OK.match(lemma)) and len(lemma.split()) <= MAX_WORDS


def person_root_synsets(wordnet) -> list:
    out = []
    for lemma, defn in PERSON_ROOTS:
        for s in wordnet.synsets(lemma, pos="n"):
            if (s.definition() or "").lower().startswith(defn):
                out.append(s)
                break
    return out


def person_noun_lemmas(wordnet) -> set[str]:
    seen: dict[str, object] = {}
    front = list(person_root_synsets(wordnet))
    while front:
        s = front.pop()
        if s.id in seen:
            continue
        seen[s.id] = s
        front.extend(s.hyponyms())
    return {lem for s in seen.values() for lem in s.lemmas()}


def oewn_candidates(*, wordnet=None, include_person_nouns: bool = True) -> list[str]:
    """Variant B's universe (see the module docstring); ``wordnet`` is any ``wn.Wordnet``-like handle (default
    the platform's OEWN)."""
    if wordnet is None:  # pragma: no cover - the real database
        from assistant_axis.gapgen import wordnet as gw
        wordnet = gw.oewn()
    pool: list[str] = []
    for pos in ADJ_POS:
        pool.extend(w.lemma() for w in wordnet.words(pos=pos))
    if include_person_nouns:
        pool.extend(lem for lem in person_noun_lemmas(wordnet) if lem == lem.lower())
    by_stem: dict[str, str] = {}
    for lem in sorted(set(pool), key=lambda x: (x.lower(), x != x.lower(), x)):
        if not _ok(lem):
            continue
        stem = normalize_to_file_name(lem)
        if stem and stem not in by_stem:
            by_stem[stem] = lem
    return sorted(by_stem.values(), key=lambda x: (x.lower(), x))


def stoplist_flags(surface: str, definition: Optional[str] = None) -> list[str]:
    """``religion`` (a fixed list) and ``nationality`` (a capitalised word whose OEWN definition is the
    demonym boilerplate, "of or relating to or characteristic of ...", "a native or inhabitant of ...")."""
    flags = []
    words = surface.lower().replace("-", " ").split()
    if any(w in RELIGIONS for w in words):
        flags.append("religion")
    if surface[:1].isupper() and definition and _NATIONALITY_RE.search(definition):
        flags.append("nationality")
    return flags


def universe_coverage(labels: Iterable[str], universe: Sequence[str]) -> dict:
    """How many labels (bare corpus labels) the universe lacks, by stem: what bounds Variant B's recall
    (Roger, 2026-10-10: "how much of the corpus the WordNet approach could not recover")."""
    stems = {normalize_to_file_name(u) for u in universe}
    labs = list(dict.fromkeys(labels))
    absent = [lab for lab in labs if normalize_to_file_name(lab) not in stems]
    multi = [lab for lab in labs if re.search(r"[\s\-]", lab)]
    absent_multi = [lab for lab in absent if re.search(r"[\s\-]", lab)]
    n, nm = len(labs), len(multi)
    return {"n_labels": n, "n_universe": len(universe), "n_absent": len(absent),
            "share_absent": round(len(absent) / n, 4) if n else None,
            "n_single": n - nm, "n_single_absent": len(absent) - len(absent_multi),
            "n_multiword": nm, "n_multiword_absent": len(absent_multi),
            "absent_single": sorted(lab for lab in absent if lab not in absent_multi),
            "absent_multiword": sorted(absent_multi)}
