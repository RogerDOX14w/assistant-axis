"""Open English WordNet for workstream 2: the lookups the Roget generator needs, and the small
WordNet sibling stream (generator id ``wn_clusters``).

:class:`Lexicon` wraps a ``wn.Wordnet`` handle (the platform's :func:`assistant_axis.gapgen.wordnet.oewn`,
lexicon ``oewn:2024`` under ``data/external/wn``) with cached lookups: adjective synsets
(``a`` and satellite ``s``), sense-level antonyms (direct, and indirect through a satellite's
cluster head), derivational forms, the cluster of an adjective head synset, and the hyponym closure
of the trait nouns.  Tests pass a fake handle with the same methods
(``synsets``, ``senses``; ``Synset.id/.pos/.lemmas()/.definition()/.get_related()/.hyponyms()``;
``Sense.word().lemma()/.synset()/.get_related()``).

The sibling stream (plan § 5, ``wn_clusters.py``; task 14):

* :func:`harvest_wn_antonyms`: for existing labels with no partner file (a ``non-X`` placeholder
  or a one-way pointer to a word with no file), the WordNet antonyms of the label, each a
  candidate whose ``partner_hint`` is the label;
* :func:`harvest_trait_closure`: adjectives derived from the nouns under ``trait``,
  ``disposition``, ``temperament``, ``attitude`` and ``character`` (bounded depth).

Both drop words already in the corpus or the seed queue, words the frequency floor rejects, and
words with no adjective sense; ``source_ref`` is ``oewn:<synset id>``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable, Collection, Iterable, Optional, Sequence

from assistant_axis.entity_id import normalize_to_file_name

ADJ_POS = ("a", "s")
TRAIT_ROOT_LEMMAS = ("trait", "disposition", "temperament", "attitude", "character")
#: The noun senses of the roots that are about persons (OEWN 2024 ids, checked 2026-10-08):
#: trait "a distinguishing feature of your personal nature"; disposition / temperament "your
#: usual mood"; disposition "a natural or acquired habit or characteristic tendency in a person
#: or thing"; attitude "a complex mental state involving beliefs and feelings and values and
#: dispositions to act in certain ways"; character / fiber "the inherent complex of attributes
#: that determines a persons moral and ethical actions and reactions".  Left out: the other
#: senses of character (a fictional character, an eccentric, a reference) and quality.
TRAIT_ROOT_SYNSETS: tuple[str, ...] = ("oewn-04623416-n", "oewn-04630969-n", "oewn-04950046-n",
                                       "oewn-06202938-n", "oewn-04627573-n")


def oewn():
    """The platform's OEWN handle (``data/external/wn``, lexicon ``oewn:2024``)."""
    from assistant_axis.gapgen import wordnet as gw
    return gw.oewn()


@dataclass
class Cluster:
    head_id: str
    head_lemmas: list
    satellites: list            # [(synset id, lemmas)]
    antonym_head_id: Optional[str] = None


class Lexicon:
    """Cached WordNet lookups over a ``wn.Wordnet``-like handle."""

    def __init__(self, handle):
        self.h = handle
        self._ant = lru_cache(maxsize=None)(self._antonyms)
        self._der = lru_cache(maxsize=None)(self._derivations)
        self._pos = lru_cache(maxsize=None)(self._pos_of)

    # -- primitive lookups -------------------------------------------------------------
    def synsets(self, lemma: str, pos: Optional[str] = None) -> list:
        try:
            return list(self.h.synsets(lemma, pos=pos)) if pos else list(self.h.synsets(lemma))
        except Exception:  # noqa: BLE001 - an unknown form is simply absent
            return []

    def senses(self, lemma: str, pos: Optional[str] = None) -> list:
        try:
            return list(self.h.senses(lemma, pos=pos)) if pos else list(self.h.senses(lemma))
        except Exception:  # noqa: BLE001
            return []

    def adj_synsets(self, lemma: str) -> list:
        out, seen = [], set()
        for p in ADJ_POS:
            for s in self.synsets(lemma, p):
                if s.id not in seen:
                    seen.add(s.id)
                    out.append(s)
        return out

    def _pos_of(self, lemma: str) -> tuple:
        return tuple(sorted({s.pos for s in self.synsets(lemma)}))

    def pos_of(self, lemma: str) -> tuple:
        return self._pos(lemma)

    def is_adjective(self, lemma: str) -> bool:
        return any(p in ADJ_POS for p in self.pos_of(lemma))

    # -- antonyms --------------------------------------------------------------------
    def _antonyms(self, lemma: str, pos: tuple) -> tuple:
        out: dict[str, str] = {}
        for p in pos:
            for se in self.senses(lemma, p):
                for r in se.get_related("antonym"):
                    out.setdefault(r.word().lemma(), r.synset().id)
        if not out and any(p in ADJ_POS for p in pos):
            # indirect antonymy: a satellite's cluster head and that head's antonyms
            for s in self.synsets(lemma, "s"):
                for head in s.get_related("similar"):
                    for hl in head.lemmas():
                        for se in self.senses(hl, "a"):
                            if se.synset().id != head.id:
                                continue
                            for r in se.get_related("antonym"):
                                out.setdefault(r.word().lemma(), r.synset().id)
        return tuple(sorted(out.items()))

    def antonyms(self, lemma: str, *, pos: Sequence[str] = ADJ_POS) -> list[tuple[str, str]]:
        """``[(antonym lemma, its synset id)]``, direct sense antonyms of every sense of ``pos``
        (adjectives by default), else indirect ones through a satellite's cluster head."""
        return list(self._ant(lemma, tuple(pos)))

    # -- adjective clusters (synset level) ------------------------------------------------
    def _head_synsets(self, lemma: str) -> frozenset:
        out = set()
        for s in self.adj_synsets(lemma):
            if s.pos == "a":
                out.add(s.id)
            else:
                out.update(h.id for h in s.get_related("similar"))
        return frozenset(out)

    def head_synsets(self, lemma: str) -> frozenset:
        """Ids of the adjective cluster heads ``lemma`` belongs to (its own head synsets, and the
        heads of its satellites)."""
        if not hasattr(self, "_hs"):
            self._hs = lru_cache(maxsize=None)(self._head_synsets)
        return self._hs(lemma)

    def _synset_antonyms(self, sid: str) -> frozenset:
        out = set()
        for s in self.synsets_by_id(sid):
            for lemma in s.lemmas():
                for se in self.senses(lemma, "a"):
                    if se.synset().id == sid:
                        out.update(r.synset().id for r in se.get_related("antonym"))
        return frozenset(out)

    def synsets_by_id(self, sid: str) -> list:
        try:
            return [self.h.synset(sid)]
        except Exception:  # noqa: BLE001
            return []

    def antonym_heads(self, lemma: str) -> frozenset:
        """Ids of the cluster heads opposed to ``lemma``'s cluster heads (Gross & Miller's indirect
        antonymy: a satellite is opposed to the satellites of its head's antonym)."""
        if not hasattr(self, "_ah"):
            self._ah = lru_cache(maxsize=None)(self._synset_antonyms)
        out = set()
        for h in self.head_synsets(lemma):
            out |= self._ah(h)
        return frozenset(out)

    # -- derivations -----------------------------------------------------------------
    def _derivations(self, lemma: str) -> tuple:
        out = set()
        for se in self.senses(lemma):
            for r in se.get_related("derivation"):
                out.add((r.word().lemma(), r.synset().pos))
        return tuple(sorted(out))

    def derivations(self, lemma: str) -> list[tuple[str, str]]:
        """``[(lemma, pos)]`` derivationally related to any sense of ``lemma``."""
        return list(self._der(lemma))

    # -- clusters and closure ---------------------------------------------------------------
    def cluster(self, synset) -> Cluster:
        """An adjective head synset with its satellites and its antonym head."""
        head = synset
        if getattr(synset, "pos", None) == "s":
            heads = list(synset.get_related("similar"))
            if heads:
                head = heads[0]
        sats = [(s.id, list(s.lemmas())) for s in head.get_related("similar")]
        ant_head = None
        for hl in head.lemmas():
            for se in self.senses(hl, "a"):
                if se.synset().id != head.id:
                    continue
                for r in se.get_related("antonym"):
                    ant_head = r.synset().id
                    break
        return Cluster(head_id=head.id, head_lemmas=list(head.lemmas()), satellites=sats, antonym_head_id=ant_head)

    def derivational_adjs(self, noun_synset) -> list[str]:
        """Adjectives derivationally related to any lemma of a noun synset (``courage`` ->
        ``courageous``)."""
        out = []
        for lemma in noun_synset.lemmas():
            for se in self.senses(lemma, "n"):
                if se.synset().id != noun_synset.id:
                    continue
                for r in se.get_related("derivation"):
                    if r.synset().pos in ADJ_POS and r.word().lemma() not in out:
                        out.append(r.word().lemma())
        return out

    def trait_closure(self, roots: Sequence[str] = TRAIT_ROOT_LEMMAS, *, max_depth: int = 3,
                      root_synsets: Optional[Sequence[str]] = None) -> dict:
        """Noun synsets under the roots' person senses, to ``max_depth`` levels of hyponymy:
        ``{synset id: (synset, depth)}``.  A root's senses are those in ``root_synsets`` when
        any is given for it, else every noun sense whose definition mentions a person
        (``person``, ``your``, ``character``, ``mood``, ``tendency``, ``mental``)."""
        if root_synsets is None:
            root_synsets = TRAIT_ROOT_SYNSETS
        cues = ("person", "your", "character", "mood", "tendency", "mental", "nature")
        frontier = []
        for r in roots:
            for s in self.synsets(r, "n"):
                if (root_synsets and s.id in root_synsets) or \
                        (not root_synsets and any(c in (s.definition() or "").lower() for c in cues)):
                    frontier.append((s, 0))
        seen: dict = {}
        while frontier:
            s, d = frontier.pop(0)
            if s.id in seen:
                continue
            seen[s.id] = (s, d)
            if d < max_depth:
                frontier.extend((h, d + 1) for h in s.hyponyms())
        return seen


# --------------------------------------------------------------------------- the sibling stream

@dataclass
class WnItem:
    surface: str
    synset_id: str
    gloss_hint: str
    partner_hint: Optional[str]
    zipf_min: float
    probe_band: bool
    score: float
    route: str                  # antonym | closure
    origin: str                 # the label (antonym route) or the noun synset's lemma (closure)
    n_senses: int = 0
    extra: dict = field(default_factory=dict)


def _hint_from_definition(definition: str) -> str:
    d = " ".join((definition or "").split()).rstrip(".;")
    if not d:
        return ""
    return f"This means {d}."


def _freq_ok(surface: str, zipf: Callable) -> tuple[bool, float, bool]:
    from assistant_axis.gapgen.freq import zipf_info
    fi = zipf_info(surface, zipf_fn=zipf)
    return (not fi.hard_reject), fi.zipf_min, fi.probe_band


def harvest_wn_antonyms(records: Iterable, lex: Lexicon, *, known_stems: Collection[str],
                        zipf: Optional[Callable] = None) -> list[WnItem]:
    """WordNet antonyms of existing labels that have no partner file (``partner_has_file`` false),
    one item per new antonym word.  ``known_stems`` (corpus and queue) are never emitted."""
    known = set(known_stems)
    out: dict[str, WnItem] = {}
    for rec in records:
        if getattr(rec, "source", "existing") != "existing" or getattr(rec, "partner_has_file", False):
            continue
        label = rec.label
        for ant, sid in lex.antonyms(label):
            stem = normalize_to_file_name(ant)
            if stem in known or stem == rec.stem or not lex.is_adjective(ant):
                continue
            ok, zmin, probe = _freq_ok(ant, zipf)
            if not ok:
                continue
            syn = next((s for s in lex.adj_synsets(ant) if s.id == sid), None)
            hint = _hint_from_definition(syn.definition() if syn is not None else "")
            item = WnItem(surface=ant, synset_id=sid, gloss_hint=hint, partner_hint=label, zipf_min=zmin,
                          probe_band=probe, score=round(zmin, 3), route="antonym", origin=rec.stem,
                          n_senses=len(lex.adj_synsets(ant)))
            if stem not in out or item.score > out[stem].score:
                out[stem] = item
    return sorted(out.values(), key=lambda it: (-it.score, it.surface))


def harvest_trait_closure(lex: Lexicon, *, known_stems: Collection[str], zipf: Optional[Callable] = None,
                          max_depth: int = 3, cap: Optional[int] = None,
                          root_synsets: Optional[Sequence[str]] = None) -> list[WnItem]:
    """Adjectives derived from the trait-noun closure (:meth:`Lexicon.trait_closure`), one item per
    new adjective, its hint from the noun synset's definition ("This means having <noun>: ...")."""
    known = set(known_stems)
    out: dict[str, WnItem] = {}
    for sid, (syn, depth) in sorted(lex.trait_closure(max_depth=max_depth, root_synsets=root_synsets).items()):
        if depth == 0:
            continue
        noun = (syn.lemmas() or [""])[0]
        for adj in lex.derivational_adjs(syn):
            stem = normalize_to_file_name(adj)
            if stem in known or " " in adj.strip():
                continue
            ok, zmin, probe = _freq_ok(adj, zipf)
            if not ok:
                continue
            d = " ".join((syn.definition() or "").split()).rstrip(".;")
            hint = f"This means having {noun}: {d}." if d else ""
            item = WnItem(surface=adj, synset_id=sid, gloss_hint=hint, partner_hint=None, zipf_min=zmin,
                          probe_band=probe, score=round(zmin - 0.2 * depth, 3), route="closure", origin=noun,
                          n_senses=len(lex.adj_synsets(adj)), extra={"depth": depth})
            if stem not in out or item.score > out[stem].score:
                out[stem] = item
    items = sorted(out.values(), key=lambda it: (-it.score, it.surface))
    return items[:cap] if cap else items
