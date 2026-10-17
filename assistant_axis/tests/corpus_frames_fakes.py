"""Shared fakes for the corpus-frames generator tests: gzipped fixture shards behind a watched fetcher, the noun
helper's fake lookups, gloss senses, person nouns and Zipf.  No network, no OEWN, no wordfreq."""
from __future__ import annotations

import gzip
import io
import json
import re
from pathlib import Path
from typing import Mapping, Optional, Sequence

from assistant_axis.gapgen import nouns as N
from assistant_axis.gapgen.generators.censuses.glosshint import Sense
from assistant_axis.gapgen.generators.corpus_frames import books as B
from assistant_axis.gapgen.generators.corpus_frames.table import Lookups

_URL_RE = re.compile(r"(\d)-(\d{5})-of-(\d{5})\.gz$")


def gz(lines: Sequence[str]) -> bytes:
    return gzip.compress("".join(line + "\n" for line in lines).encode("utf-8"))


class FakeShards:
    """A fetcher over in-memory shards: ``{n: [[line, ...], ...]}`` (each shard's lines sorted, the shards in order).
    Every request is logged in ``calls`` (``("range"|"size"|"stream", url)``)."""

    def __init__(self, shards: Mapping[int, Sequence[Sequence[str]]], *, base_url: str = B.BASE_URL):
        self.blobs = {n: [gz(s) for s in ss] for n, ss in shards.items()}
        self.n_shards = {n: len(ss) for n, ss in shards.items()}
        self.base_url = base_url
        self.calls: list[tuple[str, str]] = []

    def _blob(self, url: str) -> bytes:
        m = _URL_RE.search(url)
        assert m, url
        n, i = int(m.group(1)), int(m.group(2))
        assert int(m.group(3)) == self.n_shards[n], (url, self.n_shards)
        return self.blobs[n][i]

    def range(self, url: str, start: int, end: int) -> bytes:
        self.calls.append(("range", url))
        return self._blob(url)[start:end + 1]

    def size(self, url: str) -> int:
        self.calls.append(("size", url))
        return len(self._blob(url))

    def stream(self, url: str):
        self.calls.append(("stream", url))
        return io.BytesIO(self._blob(url))


def split_sorted(lines: Sequence[str], n_shards: int, *, heads: Optional[Sequence[str]] = None) -> list[list[str]]:
    """Lines sorted in byte order and cut into ``n_shards`` shards, a new shard starting at each line whose n-gram is in
    ``heads`` (the first shard starts at the first line), else evenly."""
    lines = sorted(lines, key=lambda s: s.split("\t", 1)[0].encode("utf-8"))
    if heads:
        out, cur = [], []
        hs = set(heads)
        for line in lines:
            if line.split("\t", 1)[0] in hs and cur:
                out.append(cur)
                cur = []
            cur.append(line)
        out.append(cur)
        assert len(out) == n_shards, (len(out), n_shards)
        return out
    k = max(1, -(-len(lines) // n_shards))
    return [lines[i:i + k] for i in range(0, len(lines), k)]


#: The 3-gram fixture: a ``very`` block spanning two shards (with its tagged forms and a wildcard after it), ``too``
#: with ``too X to``, two nominal anchors (``old`` is not a person noun; ``liar`` is), the possessive ``man of``.
LINES_3 = [
    "about the house\t1950,1,1",
    "an incorrigible flirt\t1950,50,40",
    "an incorrigible liar\t1930,100,80\t1910,500,400",
    "an incorrigible old\t1950,60,50",
    "an incorrigible pedant\t1960,45,44",
    "being very good\t1950,5,5",
    "man of honesty\t1950,30,25",
    "man of integrity\t1950,90,70",
    "man of letters\t1950,900,600",
    "too clever by\t1950,77,7",
    "too clever to\t1950,70,60",
    "too honest to\t1950,41,33",
    "too_ADV clever_ADJ to\t1950,999,999",
    "very Christian man\t1950,999,999",
    "very good man\t1919,100,50\t1950,4000,3000",
    "very honest man\t1921,300,200",
    "very honest woman\t1930,40,30",
    "very kind fellow\t1950,500,400",
    "very leaky _ADV_\t1950,99,99",
    "very sceptical person\t1950,60,50",
    "very the man\t1950,99,99",
    "very_ADJ sergeant_NOUN\t1950,5,5",
    "zany old fellow\t1950,1,1",
]
HEADS_3 = ["about the house", "man of honesty", "too clever by", "very good man", "very kind fellow",
           "very_ADJ sergeant_NOUN"]
LINES_4 = [
    "he was always cheerful\t1950,80,70",
    "he was always kind\t1950,60,50",
    "known for his honesty\t1950,120,100",
    "known for his kindness\t1950,90,80",
    "she was always cheerful\t1950,50,45",
    "tendency to be jealous\t1950,55,50",
    "was a good man\t1950,9000,7000",
    "was a honest man\t1950,41,40",
    "zoo was a\t1950,1,1",
]
HEADS_4 = ["he was always cheerful", "known for his honesty", "tendency to be jealous", "zoo was a"]


def fixture_fetcher() -> FakeShards:
    return FakeShards({3: split_sorted(LINES_3, len(HEADS_3), heads=HEADS_3),
                       4: split_sorted(LINES_4, len(HEADS_4), heads=HEADS_4)})


# --------------------------------------------------------------------------- the table's lookups

POS = {"honest": ["a"], "honesty": ["n"], "pedant": ["n"], "pedantic": ["a"], "generous": ["a"],
       "generosity": ["n"], "pugnacious": ["a"], "pugnacity": ["n"], "liar": ["n"], "flirt": ["n", "v"],
       "good": ["a", "n"], "kind": ["a", "n"], "kindness": ["n"], "old": ["a"], "skeptical": ["a"],
       "integrity": ["n"], "letters": ["n"], "clever": ["a"], "cheerful": ["a"], "jealous": ["a"],
       "humor": ["n"], "humorous": ["a"], "shy": ["a"], "coward": ["n"], "cowardly": ["a"]}
LEXFILES = {"honesty": {"noun.attribute"}, "pedant": {"noun.person"}, "liar": {"noun.person"},
            "flirt": {"noun.person"}, "generosity": {"noun.attribute"}, "pugnacity": {"noun.attribute"},
            "kindness": {"noun.attribute"}, "integrity": {"noun.attribute"}, "letters": {"noun.communication"},
            "humor": {"noun.attribute"}, "coward": {"noun.person"}}
DERIVATIONS = {"pedant": [N.Derivation("pedantic", "noun.person", "marked by a narrow focus on learning")],
               "humor": [N.Derivation("humorous", "noun.attribute", "full of or characterized by humor")],
               "coward": [N.Derivation("cowardly", "noun.person", "lacking courage")]}
DEFINITIONS = {"honest": ["not disposed to cheat or defraud"], "pedantic": ["marked by a narrow focus on learning"],
               "generous": ["willing to give and share unstintingly"], "kind": ["having or showing a tender nature"],
               "cowardly": ["lacking courage"]}
#: Per-word Zipf (``zipf_info`` looks up content words; an unlisted word is 3.0).
ZIPF = {"good": 6.5, "honest": 4.6, "kind": 5.2, "pedant": 1.9, "pedantic": 2.6, "liar": 3.6, "flirt": 3.0,
        "skeptical": 3.4, "sceptical": 3.0, "honesty": 4.0, "integrity": 4.1, "letters": 4.8, "clever": 4.3,
        "cheerful": 3.7, "jealous": 3.9, "kindness": 3.9, "zorbish": 0.5, "blarg": 0.0}
SENSES = {"honest": [Sense("not disposed to cheat or defraud", "a")],
          "kind": [Sense("a category of things", "n"), Sense("having or showing a tender nature", "a")],
          "pedant": [Sense("a person who pays more attention to formal rules than they merit", "n")],
          "liar": [Sense("a person who has lied or who lies repeatedly", "n")],
          "good": [Sense("having desirable or positive qualities", "a")],
          "zorbish": [Sense("a made-up word with a gloss", "a")]}
PERSON_NOUNS = frozenset({"liar", "flirt", "pedant", "coward", "bully"})


def fake_nouns() -> N.FakeLookups:
    return N.FakeLookups(pos=POS, lexfiles=LEXFILES, derivations=DERIVATIONS, definitions=DEFINITIONS, zipf=ZIPF)


def fake_lookups(**over) -> Lookups:
    kw = dict(nouns=fake_nouns(), senses=lambda s: list(SENSES.get(s, [])), person_nouns=PERSON_NOUNS,
              zipf_word=lambda w: ZIPF.get(w, 3.0))
    kw.update(over)
    return Lookups(**kw)


def make_corpus(root: Path, traits=("honest", "kind", "pedantic", "cheerful", "jealous", "humble"),
                queue=("clever",), renamed=None) -> Path:
    """A fake data dir: trait files (with ``renamed_from`` where given) and a seed queue."""
    d = root / "data"
    inst = d / "traits" / "instructions"
    inst.mkdir(parents=True, exist_ok=True)
    for t in traits:
        doc = {"positive_label": t.replace("_", " ")}
        if renamed and t in renamed:
            doc["renamed_from"] = renamed[t]
        (inst / f"{t}.json").write_text(json.dumps(doc))
    (d / "seed_queue.json").write_text(json.dumps({"entries": [
        *({"stem": q, "label": q, "entity_type": "trait", "status": "candidate"} for q in queue)]}))
    return d
