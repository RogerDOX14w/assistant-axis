"""Test doubles for workstream 2 (Roget and WordNet): a fake ``wn.Wordnet`` handle with the
methods :class:`assistant_axis.gapgen.generators.roget.wn_clusters.Lexicon` calls, behaving as
``wn`` 1.1 does where it matters (``synsets(pos="a")`` leaves satellites out; ``senses(pos="a")``
includes them), and a small synthetic Roget index builder."""
from __future__ import annotations

from typing import Optional, Sequence

from assistant_axis.gapgen.generators.roget.parse import Head, RogetIndex, subsection_key


class FakeWord:
    def __init__(self, lemma: str):
        self._lemma = lemma

    def lemma(self) -> str:
        return self._lemma


class FakeSynset:
    def __init__(self, wn: "FakeWordnet", id: str, pos: str, lemmas: Sequence[str], definition: str = ""):
        self.wn, self.id, self.pos = wn, id, pos
        self._lemmas = list(lemmas)
        self._def = definition
        self.rel: dict[str, list[str]] = {}

    def lemmas(self) -> list[str]:
        return list(self._lemmas)

    def definition(self) -> str:
        return self._def

    def get_related(self, rel: str) -> list["FakeSynset"]:
        return [self.wn.synset(i) for i in self.rel.get(rel, [])]

    def hyponyms(self) -> list["FakeSynset"]:
        return self.get_related("hyponym")

    def __repr__(self) -> str:
        return f"FakeSynset({self.id})"


class FakeSense:
    def __init__(self, wn: "FakeWordnet", lemma: str, synset_id: str):
        self.wn, self.lemma, self.synset_id = wn, lemma, synset_id
        self.id = f"{lemma}%{synset_id}"
        self.rel: dict[str, list[tuple[str, str]]] = {}

    def word(self) -> FakeWord:
        return FakeWord(self.lemma)

    def synset(self) -> FakeSynset:
        return self.wn.synset(self.synset_id)

    def get_related(self, rel: str) -> list["FakeSense"]:
        return [self.wn.sense(l, s) for l, s in self.rel.get(rel, [])]


class FakeWordnet:
    def __init__(self):
        self._syn: dict[str, FakeSynset] = {}
        self._senses: dict[tuple[str, str], FakeSense] = {}

    def add(self, sid: str, pos: str, lemmas: Sequence[str], definition: str = "", *,
            head: Optional[str] = None) -> FakeSynset:
        """A synset with a sense per lemma; ``head`` makes it a satellite of that head synset."""
        s = FakeSynset(self, sid, pos, lemmas, definition)
        self._syn[sid] = s
        for l in lemmas:
            self._senses[(l, sid)] = FakeSense(self, l, sid)
        if head is not None:
            s.rel.setdefault("similar", []).append(head)
            self._syn[head].rel.setdefault("similar", []).append(sid)
        return s

    def antonym(self, la: str, sa: str, lb: str, sb: str) -> None:
        self._senses[(la, sa)].rel.setdefault("antonym", []).append((lb, sb))
        self._senses[(lb, sb)].rel.setdefault("antonym", []).append((la, sa))

    def derivation(self, la: str, sa: str, lb: str, sb: str) -> None:
        self._senses[(la, sa)].rel.setdefault("derivation", []).append((lb, sb))
        self._senses[(lb, sb)].rel.setdefault("derivation", []).append((la, sa))

    def hyponym(self, parent: str, child: str) -> None:
        self._syn[parent].rel.setdefault("hyponym", []).append(child)

    # -- the wn.Wordnet methods Lexicon uses --------------------------------------------
    def synset(self, sid: str) -> FakeSynset:
        return self._syn[sid]

    def sense(self, lemma: str, sid: str) -> FakeSense:
        return self._senses[(lemma, sid)]

    def synsets(self, form: str, pos: Optional[str] = None) -> list[FakeSynset]:
        return [s for s in self._syn.values() if form in s._lemmas and (pos is None or s.pos == pos)]

    def senses(self, form: str, pos: Optional[str] = None) -> list[FakeSense]:
        out = []
        for (l, sid), se in self._senses.items():
            if l != form:
                continue
            p = self._syn[sid].pos
            if pos is None or p == pos or (pos == "a" and p == "s"):
                out.append(se)
        return out


def small_wordnet() -> FakeWordnet:
    """cautious / incautious (heads), wary (satellite of cautious), unwary (satellite of
    incautious); brave / cowardly; caution (noun) derived from cautious; trait root with two
    levels of hyponyms carrying derivational adjectives."""
    wn = FakeWordnet()
    wn.add("a-cautious", "a", ["cautious"], "showing careful forethought")
    wn.add("a-incautious", "a", ["incautious"], "lacking in caution")
    wn.add("s-wary", "s", ["wary", "chary"], "marked by keen caution", head="a-cautious")
    wn.add("s-unwary", "s", ["unwary"], "not alert to danger", head="a-incautious")
    wn.antonym("cautious", "a-cautious", "incautious", "a-incautious")
    wn.add("n-caution", "n", ["caution", "cautiousness"], "the trait of being cautious")
    wn.derivation("cautious", "a-cautious", "caution", "n-caution")
    wn.add("a-brave", "a", ["brave", "courageous"], "possessing or displaying courage")
    wn.add("a-cowardly", "a", ["cowardly"], "lacking courage")
    wn.antonym("brave", "a-brave", "cowardly", "a-cowardly")
    wn.add("n-courage", "n", ["courage"], "a quality of spirit that enables you to face danger")
    wn.derivation("courageous", "a-brave", "courage", "n-courage")
    wn.add("n-trait", "n", ["trait"], "a distinguishing feature of your personal nature")
    wn.add("n-quality", "n", ["quality"], "an essential and distinguishing attribute")
    wn.hyponym("n-trait", "n-courage")
    wn.hyponym("n-courage", "n-caution")
    wn.add("n-deep", "n", ["deepness"], "a level too deep for the closure")
    wn.add("a-deep", "a", ["deep"], "having great depth")
    wn.derivation("deep", "a-deep", "deepness", "n-deep")
    wn.add("n-mid", "n", ["middleness"], "an intermediate level")
    wn.hyponym("n-caution", "n-mid")
    wn.hyponym("n-mid", "n-deep")
    return wn


def make_index(heads: Sequence[dict]) -> RogetIndex:
    """A RogetIndex from short head specs ``{"id", "title", "adj": [[...]], "noun": [[...]], ...}``;
    defaults: Class V, section "I. Volition in general", subsection "1. Acts of volition"."""
    hs: dict[str, Head] = {}
    order = []
    for i, d in enumerate(heads):
        hid = d["id"]
        num = int("".join(ch for ch in hid if ch.isdigit()))
        letter = "".join(ch for ch in hid if ch.isalpha())
        pos = {}
        if d.get("noun"):
            pos["N"] = [list(g) for g in d["noun"]]
        if d.get("adj"):
            pos["Adj"] = [list(g) for g in d["adj"]]
        hs[hid] = Head(id=hid, number=num, letter=letter, title=d.get("title", hid), klass=d.get("klass", "V"),
                       class_title="Words relating to the voluntary powers", division=d.get("division"),
                       section=d.get("section", "I. Volition in general"),
                       subsection=d.get("subsection", "1. Acts of volition"), pos=pos,
                       antonym_refs=list(d.get("ants", [])), line_start=i + 1)
        order.append(hid)
    by_sub: dict[str, list[str]] = {}
    for h in order:
        by_sub.setdefault(subsection_key(hs[h]), []).append(h)
    return RogetIndex(heads=hs, order=order, by_subsection=by_sub)
