"""Roget's own opposed-head pairing, read from the Tabular Synopsis of Categories of the printed 1911 edition.

Roget printed every head of the thesaurus in a synopsis of two facing columns, the opposites on one row
(1 Existence | 2 Inexistence).  The Gutenberg text (:mod:`.parse`) is linear and loses the rows, so
:mod:`.pairs` had to rebuild the pairs by rule; this module reads them from the printed page instead
(QUESTIONS 38).  Source: the Internet Archive scan ``rogetsthesauruso00mawsrich`` (ed. C. O. Sylvester
Mawson, Thomas Y. Crowell, 1911; not in copyright), its positional OCR ``..._djvu.xml``, which gives every
word's page (``leaf``) and box.  The synopsis is leaves 27-37 (printed pages xxi-xxxi), each headed
"TABULAR SYNOPSIS OF CATEGORIES".

**Entries.**  Right of the category outline each page has three columns of heads: left (L), middle (M,
centred entries such as 15 Difference) and right (R), told apart by the x of the head number against the
page's left and right number columns.  A head number is a word that reads as ``<digits><a|b>.`` after
stripping OCR junk around it (``r27.``, ``[105.``, ``987_``: :func:`read_number`).  In each column the
numbers must rise down the page and across pages; the longest rising run, weighted by how well the
title printed beside each number matches the Gutenberg title (:func:`title_score`), is kept and the
rest are listed as unused tokens (the centred headers "1. Actual Subservience", a misread "A77").
Every head of ``heads.json`` that is still missing is then looked for in the slot its neighbours in
number leave open, first as a garbled number (:func:`confusion_readings`: ``S09.`` reads 809,
``9g3a.`` 983a, ``A77`` 477), then by its title alone (``. Deputy`` for 759, the braced
"Narrowness / Thinness" for 203); each such repair is recorded with its method.  Heads still missing are
the lettered heads Gutenberg added after 1911 (59a Complexity, 374a Sexuality, ...).

**Heights.**  An entry's height on the page is the top of its number (digits are as tall as the capitals
of the title); where the number box is distorted by a merged glyph (height outside :data:`NUMBER_H`), the
top of its title.  A braced title over two lines (202 {Breadth, Thickness}) has its number centred on
the lines, and the facing entry may sit on either line (344 Plain beside the "Lake" of 343 {Gulf, Lake}),
so an entry also carries the tops of its title lines (``ys``) and two entries align when any of these
come within :data:`ROW_TOL` of a line pitch.

**Blocks** (:func:`build_blocks`), per page:

* ``row``: an L and an R entry that align are a **pair**;
* ``brace``: an entry centred half a line between two consecutive entries of the other column, aligned
  with neither, is braced against both (609 Choice against 609a Absence of choice and 610 Rejection;
  607 Tergiversation against 604a Perseverance and 606 Obstinacy).  Its partner is the unlettered one
  nearest in number (ties: the upper), as Roget numbered correlatives consecutively and the lettered
  heads are later insertions; the other is the block's third head;
* ``centred``: a middle entry joins the block with a pair just above or below it (no entry between),
  preferring one in its own subsection, then one next to it in number, then a row printed with its
  numbers inverted (641 Redundance | 640 Insufficiency around 639 Sufficiency), then the one above.
  A second centred entry under the first joins the same block (27 | 28 with 29 Mean and 30 Compensation);
* ``alone``: anything else is a **singleton** (762 Consent; 608 Caprice under 607);
* ``override``: :data:`OVERRIDES`, printed groupings the geometry cannot see, checked against the page
  image (one: the brace that sets 615a and 616 against 615 and 617 in two aligned rows).

The heads of a block's pair are ``kind: pair``; its other heads are ``kind: triad`` with the block's
members (three heads; four in two blocks), as :mod:`.pairs` records a third pole.  ``row`` is the
block's place on its page, top to bottom.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import re
import statistics
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

from .parse import RogetIndex

SYNOPSIS_VERSION = 1
ITEM_ID = "rogetsthesauruso00mawsrich"
XML_NAME = f"{ITEM_ID}_djvu.xml"
#: The item's files are served from this host (``archive.org/download/...`` answered 500 on 2026-10-08);
#: the item's metadata (https://archive.org/metadata/rogetsthesauruso00mawsrich) names the server.
XML_URL = f"https://ia801602.us.archive.org/33/items/{ITEM_ID}/{XML_NAME}"
METADATA_URL = f"https://archive.org/metadata/{ITEM_ID}"
#: SHA-256 of the djvu XML as downloaded on 2026-10-08 (34,831,231 bytes; SHA-1
#: 16d7d274d716949fcf017fbb2e2c51817222f0c8 as the item's metadata lists it).
XML_SHA256: Optional[str] = "0a1776986818c7e67796773ac44bc500fe59e93f5e0739d6a0dca6a2f46f42ac"
FILE_NAME = "synopsis_pairs.json"

#: Layout constants, in fractions of the page width or of the line pitch (the distance between two lines).
HEAD_AREA_MIN_X = 0.40          # the head columns lie right of this; the category outline left of it
NUMBER_H = (28, 40)             # a clean number box is 32-37 px tall at 400 dpi
SAME_LINE = 0.35                # a title word is on the number's line within this
LINE_REACH = 0.75               # title lines of an entry lie within this of its number
ROW_TIGHT = 0.16                # two numbers on one printed row (measured: 0-6 px, a pitch being 44 px)
ROW_TOL = 0.30                  # two entries align on a line of a braced title within this
BRACE_SPAN = 1.35               # the two braced entries are at most this far apart
BRACE_CENTRE = 0.32             # the single entry sits this close to their midpoint (926 Duty: 0.30)
MIDDLE_REACH = 1.35             # a centred entry is at most this far from the block it joins
DEFAULT_PITCH = 44.5            # px; measured on every synopsis page (44.2-44.6)

#: Printed groupings the geometry cannot see, each checked against the page image.  ``left`` and
#: ``right`` as printed; ``pair`` (left, right) by the module's brace rule (unlettered, nearest number).
OVERRIDES = (
    {"heads": ("615", "615a", "616", "617"), "left": ("615", "617"), "right": ("615a", "616"),
     "pair": ("615", "616"),
     "reason": "page xxvii: a brace groups 615a Absence of Motive and 616 Dissuasion against 615 Motive and "
               "617 Plea; the rows align, so the geometry alone would pair 617 Plea with 616 Dissuasion"},
)

#: OCR confusions of a letter or sign for a digit, seen in this scan.
CONFUSABLE = {"A": "4", "S": "85", "s": "85", "g": "98", "q": "90", "y": "9", "o": "0", "O": "0", "Q": "09",
              "l": "1", "I": "1", "i": "1", "|": "1", "!": "1", "B": "8", "Z": "2", "z": "2", "G": "6",
              "b": "6"}
_NUM = re.compile(r"^(?P<pre>[^0-9A-Za-z]{0,2}|[A-Za-z])(?P<num>[1-9]\d{0,3})(?P<let>[ab]?)"
                  r"(?P<post>[^0-9A-Za-z]{0,3})$")
_ROMAN = re.compile(r"^[xvi]+$", re.I)
_STOP = frozenset({"of", "and", "the", "or", "for", "with", "in", "to", "an", "by", "on", "at"})


# --------------------------------------------------------------------------- the djvu XML

@dataclass(frozen=True)
class Word:
    x0: int
    top: int
    x1: int
    bottom: int
    text: str

    @property
    def h(self) -> int:
        return self.bottom - self.top


@dataclass
class Page:
    leaf: int
    width: int
    height: int
    words: list
    label: Optional[str] = None


def read_pages(path: Path, *, leaves: Optional[Iterable[int]] = None) -> list[Page]:
    """Every page (``OBJECT``) of a djvu XML, streamed; ``leaves`` keeps only those.  A ``WORD``'s
    ``coords`` are ``x0,bottom,x1,top``.  (ElementTree resolves no external entity; the file is data.)"""
    want = set(leaves) if leaves is not None else None
    pages = []
    for _, el in ET.iterparse(str(path), events=("end",)):
        if el.tag != "OBJECT":
            continue
        m = re.search(r"_(\d+)\.djvu$", el.get("usemap") or "")
        leaf = int(m.group(1)) if m else len(pages) + 1
        if want is None or leaf in want:
            words = []
            for w in el.iter("WORD"):
                c = [int(v) for v in (w.get("coords") or "").split(",")[:4]]
                if len(c) == 4 and (w.text or "").strip():
                    words.append(Word(x0=c[0], top=c[3], x1=c[2], bottom=c[1], text=w.text.strip()))
            pages.append(Page(leaf=leaf, width=int(el.get("width") or 0), height=int(el.get("height") or 0),
                              words=words))
        el.clear()
    return pages


def _to_roman(n: int) -> str:
    out = ""
    for v, s in ((1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
                 (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while n >= v:
            out, n = out + s, n - v
    return out


def _from_roman(s: str) -> Optional[int]:
    vals = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}
    s = s.lower()
    if not s or any(ch not in vals for ch in s):
        return None
    total = 0
    for a, b in itertools.zip_longest(s, s[1:]):
        total += -vals[a] if b and vals[b] > vals[a] else vals[a]
    return total if _to_roman(total) == s else None


def synopsis_pages(pages: Sequence[Page]) -> list[Page]:
    """The pages headed "TABULAR SYNOPSIS OF CATEGORIES" (two of the three words, in capitals, on the
    page's top line: the contents page names the synopsis in mixed case further down), with their printed
    page number (``label``) read from the foot, or inferred from the leaf where the OCR lost it."""
    out = []
    for p in pages:
        if not p.words:
            continue
        first = min(w.top for w in p.words)
        head = {w.text.strip(".,") for w in p.words if w.top <= first + 15 and w.top < 0.2 * p.height}
        if len(head & {"TABULAR", "SYNOPSIS", "CATEGORIES"}) >= 2:
            foot = [w.text for w in p.words if w.top > 0.93 * p.height and _ROMAN.match(w.text.strip("."))]
            p.label = foot[0].strip(".").lower() if foot and _from_roman(foot[0].strip(".")) else None
            out.append(p)
    offsets = Counter(_from_roman(p.label) - p.leaf for p in out if p.label)
    if offsets:
        off = offsets.most_common(1)[0][0]
        for p in out:
            if not p.label or _from_roman(p.label) - p.leaf != off:
                p.label = _to_roman(p.leaf + off)
    return out


# --------------------------------------------------------------------------- numbers and titles

def read_number(text: str) -> Optional[tuple[str, bool]]:
    """``(head id, stripped)`` for a word that reads as a head number once OCR junk around it is
    stripped (``stripped`` is true when anything but a closing period was), else ``None``."""
    m = _NUM.match(text.strip())
    if not m:
        return None
    return m.group("num") + m.group("let"), bool(m.group("pre")) or m.group("post") not in ("", ".")


def confusion_readings(text: str) -> set[str]:
    """Every head id the word can read as when letters the OCR confuses with digits (:data:`CONFUSABLE`)
    are taken as those digits; a final ``a`` / ``b`` may be the letter of a lettered head and a single
    leading letter may be junk.  A word with no digit reads as nothing."""
    s = re.sub(r"^[^0-9A-Za-z|!]+|[^0-9A-Za-z|!]+$", "", text.strip())
    if not s or not re.search(r"\d", s):
        return set()
    variants = [(s, "")]
    if len(s) > 1 and s[-1] in "ab":
        variants.append((s[:-1], s[-1]))
    if len(s) > 1 and s[0].isalpha():
        variants += [(b[1:], suf) for b, suf in list(variants) if len(b) > 1]
    out = set()
    for body, suf in variants:
        opts = []
        for ch in body:
            if ch.isdigit():
                opts.append(ch)
            elif ch in CONFUSABLE:
                opts.append(CONFUSABLE[ch])
            else:
                opts = None
                break
        if not opts or len(opts) > 4:
            continue
        for digits in itertools.product(*opts):
            d = "".join(digits)
            if d[0] != "0":
                out.add(d + suf)
    return out


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z]+", s.lower())


def title_score(title: str, ocr: str) -> float:
    """Share of the title's content words (three letters or more, not a function word) found in the OCR
    text: exactly, by a fuzzy ratio of 0.8 or more, or as the start of a word split at a line end."""
    tw = [w for w in _words(title) if len(w) >= 3 and w not in _STOP] or _words(title)
    ow = [w for w in _words(ocr) if len(w) >= 2]
    if not tw:
        return 1.0
    if not ow:
        return 0.0

    def hit(w: str) -> bool:
        return any(w == o or SequenceMatcher(None, w, o).ratio() >= 0.8
                   or (len(o) >= 4 and (w.startswith(o) or o.startswith(w))) for o in ow)
    return round(sum(hit(w) for w in tw) / len(tw), 3)


def _key(index: RogetIndex, hid: str) -> tuple[int, str]:
    h = index.heads[hid]
    return (h.number, h.letter)


def _has_letters(w: Word) -> bool:
    return len(re.findall(r"[A-Za-z]", w.text)) >= 2


# --------------------------------------------------------------------------- page layout

class Layout:
    """One synopsis page: the words of its head area, its number columns and its line pitch."""

    def __init__(self, page: Page):
        self.page = page
        W, H = page.width, page.height
        first = min((w.top for w in page.words), default=0)
        heads = [w for w in page.words if w.top <= first + 15 and w.text.strip(".,").upper()
                 in ("TABULAR", "SYNOPSIS", "OF", "CATEGORIES")]
        top_min = max((w.bottom for w in heads), default=0) + 5
        self.words = [w for w in page.words if w.x0 >= HEAD_AREA_MIN_X * W and top_min < w.top < 0.95 * H]
        xs = [w.x0 for w in self.words if read_number(w.text)]
        left = [x for x in xs if x < 0.53 * W]
        right = [x for x in xs if 0.64 * W < x < 0.80 * W]
        self.left = statistics.median(left) if left else 0.445 * W
        self.right = statistics.median(right) if right else 0.71 * W
        self.span = max(1.0, self.right - self.left)
        lys = sorted(w.top for w in self.words if read_number(w.text) and self.column_of(w.x0) == "L")
        diffs = [b - a for a, b in zip(lys, lys[1:]) if 30 <= b - a <= 60]
        self.pitch = statistics.median(diffs) if diffs else DEFAULT_PITCH

    def column_of(self, x0: float) -> str:
        rel = (x0 - self.left) / self.span
        return "L" if rel < 0.35 else "R" if rel > 0.85 else "M"

    def title_words(self, number: Word, *, reach: float) -> list[Word]:
        """Words with letters right of the number in its column band, within ``reach`` pitches of it."""
        return [w for w in self.words if w is not number and _has_letters(w) and not read_number(w.text)
                and number.x0 + 10 < w.x0 < number.x0 + 0.45 * self.span
                and abs(w.top - number.top) <= reach * self.pitch]


# --------------------------------------------------------------------------- entries

@dataclass
class Entry:
    id: str
    leaf: int
    page: str
    column: str
    x0: float
    y: float
    ys: list
    token: Optional[str]
    title: str
    title_match: float
    repair: Optional[dict] = None


@dataclass
class _Cand:
    lay: Layout
    word: Word
    id: str
    stripped: bool
    column: str
    title: str
    score: float


@dataclass
class Block:
    leaf: int
    page: str
    how: str                          # row | brace | centred | alone | override
    left: list = field(default_factory=list)
    right: list = field(default_factory=list)
    middle: list = field(default_factory=list)
    pair: Optional[tuple] = None      # (left id, right id)
    top: float = 0.0
    bottom: float = 0.0
    row: int = 0
    id: int = 0

    @property
    def members(self) -> list:
        return self.left + self.right + self.middle

    @property
    def third(self) -> list:
        return [h for h in self.members if not self.pair or h not in self.pair]


def _lis(items: Sequence, key, weight) -> list:
    """The heaviest strictly rising subsequence (by ``key``), weights ``weight(item)``."""
    n = len(items)
    best = [0.0] * n
    prev = [-1] * n
    for i in range(n):
        best[i] = weight(items[i])
        for j in range(i):
            if key(items[j]) < key(items[i]) and best[j] + weight(items[i]) > best[i] + 1e-9:
                best[i], prev[i] = best[j] + weight(items[i]), j
    if not n:
        return []
    i = max(range(n), key=lambda k: (best[k], -k))
    out = []
    while i >= 0:
        out.append(items[i])
        i = prev[i]
    return out[::-1]


@dataclass
class SynopsisResult:
    entries: list
    blocks: list
    missing: list
    duplicates: list
    unused_tokens: list
    page_labels: list
    pitches: dict
    index_titles: dict = field(default_factory=dict)

    def by_id(self) -> dict:
        return {e.id: e for e in self.entries}

    def records(self) -> dict:
        """``{head id: record}`` in number order: ``kind`` (pair, triad, singleton), ``partner``,
        ``members``, ``block``, ``how``, ``page``, ``leaf``, ``row``, ``column``, ``y``, the OCR ``token``
        and ``title``, ``title_match`` (against Gutenberg) and the ``repair`` if any."""
        ents = self.by_id()
        out = {}
        for b in self.blocks:
            for h in b.members:
                e = ents[h]
                if b.pair and h in b.pair:
                    kind, partner = "pair", b.pair[1] if h == b.pair[0] else b.pair[0]
                    members = [x for x in self._order if x in b.pair]
                elif b.pair:
                    kind, partner, members = "triad", None, [x for x in self._order if x in b.members]
                else:
                    kind, partner, members = "singleton", None, [h]
                out[h] = {"kind": kind, "partner": partner, "members": members, "block": b.id, "how": b.how,
                          "page": b.page, "leaf": b.leaf, "row": b.row, "column": e.column, "y": round(e.y, 1),
                          "token": e.token, "title": e.title, "title_match": e.title_match, "repair": e.repair}
        return {h: out[h] for h in self._order if h in out}

    @property
    def _order(self) -> list:
        return list(self.index_titles)

    def blocks_json(self) -> list:
        return [{"id": b.id, "leaf": b.leaf, "page": b.page, "row": b.row, "how": b.how, "left": list(b.left),
                 "right": list(b.right), "middle": list(b.middle), "pair": list(b.pair) if b.pair else None,
                 "third": b.third if b.pair else []} for b in self.blocks]

    def repairs(self) -> list:
        return [{"id": e.id, "page": e.page, "leaf": e.leaf, "column": e.column, **e.repair,
                 "title_ocr": e.title, "title": self.index_titles.get(e.id)}
                for e in self.entries if e.repair]

    def title_mismatches(self, below: float = 0.5) -> list:
        return [{"id": e.id, "page": e.page, "title": self.index_titles.get(e.id), "title_ocr": e.title,
                 "title_match": e.title_match} for e in sorted(self.entries, key=lambda e: self._order.index(e.id))
                if e.title_match < below]


def read_synopsis(pages: Sequence[Page], index: RogetIndex, *,
                  overrides: Sequence[Mapping] = OVERRIDES) -> SynopsisResult:
    """Entries, repairs and blocks of the synopsis pages (module docstring)."""
    lays = [Layout(p) for p in pages]
    key = lambda h: _key(index, h)  # noqa: E731
    # 1. clean numbers, scored by the title beside them
    cands: list[_Cand] = []
    for lay in lays:
        for w in lay.words:
            r = read_number(w.text)
            if not r or r[0] not in index.heads:
                continue
            tw = sorted(lay.title_words(w, reach=SAME_LINE), key=lambda x: x.x0)
            title = " ".join(x.text for x in tw)
            cands.append(_Cand(lay, w, r[0], r[1], lay.column_of(w.x0), title,
                               title_score(index.heads[r[0]].title, title)))
    # 2. the heaviest rising run per column; an id kept in two columns stays where its title fits better
    kept: list[_Cand] = []
    for col in ("L", "M", "R"):
        seq = sorted((c for c in cands if c.column == col), key=lambda c: (c.lay.page.leaf, c.word.top))
        kept += _lis(seq, key=lambda c: key(c.id), weight=lambda c: 1.0 + c.score)
    by_id: dict[str, list[_Cand]] = {}
    for c in kept:
        by_id.setdefault(c.id, []).append(c)
    duplicates = []
    for h, cs in by_id.items():
        if len(cs) > 1:
            cs.sort(key=lambda c: -c.score)
            duplicates.append({"id": h, "kept": [cs[0].lay.page.leaf, cs[0].column],
                               "dropped": [[c.lay.page.leaf, c.column, c.word.text] for c in cs[1:]]})
    accepted = {h: cs[0] for h, cs in by_id.items()}
    used_words = {id(c.word) for c in accepted.values()}
    entries: dict[str, Entry] = {}
    for h, c in accepted.items():
        y = c.word.top
        if not NUMBER_H[0] <= c.word.h <= NUMBER_H[1]:
            # a distorted number box: the centre of its title lines (one line, or a braced title's lines)
            tw, _, _ = _title_lines(c.lay, c.word, index.heads[h].title, used_words, reach=SAME_LINE)
            if tw:
                y = _mean_line_top(tw)
        entries[h] = Entry(id=h, leaf=c.lay.page.leaf, page=c.lay.page.label or "", column=c.column, x0=c.word.x0,
                           y=float(y), ys=[float(y)], token=c.word.text, title=c.title, title_match=c.score,
                           repair={"method": "stripped", "token": c.word.text} if c.stripped else None)
    claimed = set(used_words)
    for c in accepted.values():
        claimed |= {id(w) for w in c.lay.title_words(c.word, reach=SAME_LINE)}
    # 3. repairs of the heads still missing
    order = sorted(index.heads, key=key)
    pos = {h: i for i, h in enumerate(order)}
    lay_of = {lay.page.leaf: lay for lay in lays}
    for m in order:
        if m in entries:
            continue
        rep = _repair(m, index, entries, order, pos, lay_of, claimed)
        if rep is not None:
            entries[m] = rep
    missing = [h for h in index.order if h not in entries]
    # unused number-like tokens (digits in the head area, not taken by an entry or a repair)
    unused = []
    for lay in lays:
        for w in lay.words:
            if re.search(r"\d", w.text) and id(w) not in claimed:
                r = read_number(w.text)
                unused.append({"leaf": lay.page.leaf, "page": lay.page.label, "text": w.text, "x0": w.x0,
                               "top": w.top, "column": lay.column_of(w.x0), "read_as": r[0] if r else None})
    # 4. title lines of each entry (for alignment)
    for e in entries.values():
        if e.repair and e.repair["method"].startswith("title"):
            continue
        lay = lay_of[e.leaf]
        same_col = [x for x in entries.values() if x.leaf == e.leaf and x.column == e.column and x is not e]
        num = next((w for w in lay.words if w.text == e.token and abs(w.x0 - e.x0) < 1), None)
        if num is None:
            continue
        for w in lay.title_words(num, reach=LINE_REACH):
            if abs(w.top - e.y) <= LINE_REACH * lay.pitch and \
                    all(abs(w.top - x.y) > abs(w.top - e.y) for x in same_col):
                if all(abs(w.top - v) > 10 for v in e.ys):
                    e.ys.append(float(w.top))
        e.ys.sort()
    ents = sorted(entries.values(), key=lambda e: (e.leaf, e.y))
    blocks = build_blocks(ents, index, pitches={lay.page.leaf: lay.pitch for lay in lays}, overrides=overrides)
    return SynopsisResult(entries=ents, blocks=blocks, missing=missing, duplicates=duplicates, unused_tokens=unused,
                          page_labels=[lay.page.label for lay in lays],
                          pitches={lay.page.leaf: round(lay.pitch, 1) for lay in lays},
                          index_titles={h: index.heads[h].title for h in order})


def _repair(m: str, index: RogetIndex, entries: Mapping[str, Entry], order: Sequence[str], pos: Mapping[str, int],
            lay_of: Mapping[int, Layout], claimed: set) -> Optional[Entry]:
    """Head ``m`` in the slot its found neighbours in number leave open: a garbled number that reads as
    ``m`` (with the title beside it), else its title on lines nobody claimed.  ``claimed`` grows."""
    before = [entries[h] for h in order[:pos[m]] if h in entries]
    after = [entries[h] for h in order[pos[m] + 1:] if h in entries]
    if not before or not after:
        return None
    a, b = before[-1], after[0]
    title = index.heads[m].title

    def in_window(leaf: int, top: float) -> bool:
        lay = lay_of[leaf]
        lo = (a.leaf, a.y - 1.5 * lay_of[a.leaf].pitch)
        hi = (b.leaf, b.y + 1.5 * lay_of[b.leaf].pitch)
        if a.leaf == b.leaf:
            lo = (a.leaf, min(a.y, b.y) - 1.5 * lay.pitch)
            hi = (a.leaf, max(a.y, b.y) + 1.5 * lay.pitch)
        return lo <= (leaf, top) <= hi

    def fits(leaf: int, col: str, y: float) -> bool:
        same = sorted((e for e in entries.values() if e.column == col), key=lambda e: (e.leaf, e.y))
        up = [e for e in same if (e.leaf, e.y) < (leaf, y)]
        down = [e for e in same if (e.leaf, e.y) > (leaf, y)]
        k = _key(index, m)
        return (not up or _key(index, up[-1].id) < k) and (not down or _key(index, down[0].id) > k)

    best = None
    for lay in (lay_of[l] for l in sorted({a.leaf, b.leaf, *range(a.leaf, b.leaf + 1)}) if l in lay_of):
        leaf = lay.page.leaf
        # a garbled number
        for w in lay.words:
            if id(w) in claimed or not in_window(leaf, w.top) or m not in confusion_readings(w.text):
                continue
            col = lay.column_of(w.x0)
            tw, tline, sc = _title_lines(lay, w, title, claimed, reach=SAME_LINE + 0.25)
            y = w.top if NUMBER_H[0] <= w.h <= NUMBER_H[1] or not tw else _mean_line_top(tw)
            if not fits(leaf, col, y):
                continue
            cand = (2 + sc, leaf, col, y, w, tw, tline, sc, "ocr_confusion+title" if sc >= 0.5 else "ocr_confusion")
            if best is None or cand[0] > best[0]:
                best = cand
        # its title alone
        lines = _free_lines(lay, claimed)
        for ln in lines:
            if not in_window(leaf, ln["top"]) or title_score(title, ln["text"]) < 0.5:
                continue
            group = [x for x in lines if x["column"] == ln["column"] and abs(x["top"] - ln["top"]) <= 1.2 * lay.pitch
                     and title_score(title, x["text"]) >= 0.5]
            text = " ".join(x["text"] for x in sorted(group, key=lambda x: x["top"]))
            sc = title_score(title, text)
            y = sum(x["top"] for x in group) / len(group)
            if not fits(leaf, ln["column"], y):
                continue
            cand = (1 + sc, leaf, ln["column"], y, None, [w for x in group for w in x["words"]], text, sc, "title")
            if best is None or cand[0] > best[0]:
                best = cand
    if best is None:
        return None
    _, leaf, col, y, w, tw, text, sc, method = best
    lay = lay_of[leaf]
    ys = sorted({float(y)} | {float(x.top) for x in tw})
    token = w.text if w is not None else None
    also = []
    # the garbled pieces of the same number (4qq and 4yy- for 499) and, for a title repair, the junk
    # left where its number was printed
    for x in lay.words:
        if x is w or id(x) in claimed or not re.search(r"\d", x.text):
            continue
        if lay.column_of(x.x0) == col and abs(x.top - y) <= 0.75 * lay.pitch and \
                (w is not None and m in confusion_readings(x.text) or w is None and x.x0 < min(t.x0 for t in tw)):
            also.append(x)
    if w is None and also:
        token = also[0].text
    for x in [w, *tw, *also]:
        if x is not None:
            claimed.add(id(x))
    rep = {"method": method, "token": token}
    if also and w is not None:
        rep["also"] = [x.text for x in also]
    return Entry(id=m, leaf=leaf, page=lay.page.label or "", column=col,
                 x0=(w.x0 if w is not None else min(t.x0 for t in tw) - 100), y=float(y), ys=ys, token=token,
                 title=text, title_match=sc, repair=rep)


def _title_lines(lay: Layout, number: Word, title: str, claimed: set, *, reach: float) -> tuple[list, str, float]:
    """The title words beside a number (within ``reach`` pitches), then the further lines of a braced title
    over two or three lines (202 {Breadth, Thickness}): an unclaimed line of the column within a pitch of
    one taken that raises the match with the Gutenberg title.  ``(words, text, score)``."""
    tw = [x for x in lay.title_words(number, reach=reach) if id(x) not in claimed]

    def text_of(ws):
        return " ".join(x.text for x in sorted(ws, key=lambda x: (x.top, x.x0)))
    sc = title_score(title, text_of(tw))
    if not tw:
        return tw, "", sc
    col = lay.column_of(number.x0)
    lines = [ln for ln in _free_lines(lay, claimed) if ln["column"] == col
             and not any(w in tw for w in ln["words"])]
    grown = True
    while grown and sc < 1.0:
        grown = False
        for ln in lines:
            if any(w in tw for w in ln["words"]) or \
                    min(abs(ln["top"] - x.top) for x in tw) > 1.2 * lay.pitch:
                continue
            new = title_score(title, text_of(tw + ln["words"]))
            if new > sc:
                tw, sc, grown = tw + ln["words"], new, True
    return tw, text_of(tw), sc


def _mean_line_top(words: Sequence[Word]) -> float:
    """The mean top of the lines the words lie on (tops within 10 px are one line): the centre of a braced
    title, on which its number is printed."""
    tops: list[float] = []
    for t in sorted(w.top for w in words):
        if not tops or t - tops[-1] > 10:
            tops.append(t)
    return sum(tops) / len(tops)


def _free_lines(lay: Layout, claimed: set) -> list[dict]:
    """Unclaimed words with letters, grouped into lines (tops within 12 px) per column, the column read from
    the line's start less a title indent."""
    words = sorted((w for w in lay.words if id(w) not in claimed and _has_letters(w) and not read_number(w.text)),
                   key=lambda w: (w.top, w.x0))
    lines: list[dict] = []
    for w in words:
        col = lay.column_of(w.x0 - 100)
        for ln in lines:
            if ln["column"] == col and abs(ln["top"] - w.top) <= 12:
                ln["words"].append(w)
                ln["text"] = " ".join(x.text for x in sorted(ln["words"], key=lambda x: x.x0))
                break
        else:
            lines.append({"column": col, "top": w.top, "words": [w], "text": w.text})
    return lines


# --------------------------------------------------------------------------- blocks

def _dist(a: Entry, b: Entry) -> float:
    return min(abs(x - y) for x in a.ys for y in b.ys)


def _brace_partner(index: RogetIndex, single: str, braced: Sequence[str]) -> str:
    """The braced entry the single one pairs with: unlettered first, then nearest in number, then the upper."""
    def k(h):
        head = index.heads[h]
        return (bool(head.letter), abs(head.number - index.heads[single].number), braced.index(h))
    return min(braced, key=k)


def build_blocks(entries: Sequence[Entry], index: RogetIndex, *, pitches: Optional[Mapping[int, float]] = None,
                 overrides: Sequence[Mapping] = OVERRIDES) -> list[Block]:
    """Rows, braces, centred entries and singletons per page (module docstring), then the overrides; blocks
    numbered by page and height (``row`` from 1 on each page)."""
    order = sorted(index.heads, key=lambda h: _key(index, h))
    rank = {h: i for i, h in enumerate(order)}
    blocks: list[Block] = []
    by_leaf: dict[int, list[Entry]] = {}
    for e in entries:
        by_leaf.setdefault(e.leaf, []).append(e)
    for leaf, ents in sorted(by_leaf.items()):
        P = (pitches or {}).get(leaf)
        if P is None:
            lys = sorted(e.y for e in ents if e.column == "L")
            diffs = [b - a for a, b in zip(lys, lys[1:]) if 30 <= b - a <= 60]
            P = statistics.median(diffs) if diffs else DEFAULT_PITCH
        page = ents[0].page
        blocks += _page_blocks(ents, index, P, page, leaf, rank)
    blocks = _apply_overrides(blocks, entries, overrides)
    blocks.sort(key=lambda b: (b.leaf, b.top))
    row = Counter()
    for i, b in enumerate(blocks, 1):
        row[b.leaf] += 1
        b.row, b.id = row[b.leaf], i
    return blocks


def _span(b: Block, ys: Mapping[str, float]) -> None:
    b.top = min(ys[h] for h in b.members)
    b.bottom = max(ys[h] for h in b.members)


def _page_blocks(ents: Sequence[Entry], index: RogetIndex, P: float, page: str, leaf: int,
                 rank: Mapping[str, int]) -> list[Block]:
    ys = {e.id: e.y for e in ents}
    L = sorted((e for e in ents if e.column == "L"), key=lambda e: e.y)
    R = sorted((e for e in ents if e.column == "R"), key=lambda e: e.y)
    M = sorted((e for e in ents if e.column == "M"), key=lambda e: e.y)
    out: list[Block] = []
    used: set[str] = set()

    def rows(dist, tol):
        edges = sorted((dist(l, r), abs(l.y - r.y), l.id, r.id) for l in L for r in R
                       if l.id not in used and r.id not in used and dist(l, r) <= tol * P)
        for _, _, l, r in edges:
            if l in used or r in used:
                continue
            used.update((l, r))
            out.append(Block(leaf=leaf, page=page, how="row", left=[l], right=[r], pair=(l, r)))
    # 1. rows whose numbers align (every printed row is within 6 px; ROW_TIGHT)
    rows(lambda l, r: abs(l.y - r.y), ROW_TIGHT)
    # 2. braces: an unmatched entry centred between two consecutive unmatched entries of the other column
    _braces(L, R, used, out, index, P, leaf, page)
    # 3. rows that align on a line of a braced title (343 {Gulf, Lake} beside 344 Plain)
    rows(_dist, ROW_TOL)
    for e in L + R:
        if e.id not in used:
            out.append(Block(leaf=leaf, page=page, how="alone", left=[e.id] if e.column == "L" else [],
                             right=[e.id] if e.column == "R" else []))
    for b in out:
        _span(b, ys)
    _centred(M, ents, out, index, P, leaf, page, ys, rank)
    return out


def _braces(L: Sequence[Entry], R: Sequence[Entry], used: set, out: list, index: RogetIndex, P: float, leaf: int,
            page: str) -> None:
    for x in sorted((e for e in list(L) + list(R) if e.id not in used), key=lambda e: e.y):
        if x.id in used:
            continue
        other = R if x.column == "L" else L
        for a, b in zip(other, other[1:]):
            if a.id in used or b.id in used or not a.y < x.y < b.y:
                continue
            if b.y - a.y <= BRACE_SPAN * P and abs(x.y - (a.y + b.y) / 2) <= BRACE_CENTRE * P:
                partner = _brace_partner(index, x.id, [a.id, b.id])
                used |= {x.id, a.id, b.id}
                single, braced = [x.id], [a.id, b.id]
                left, right = (single, braced) if x.column == "L" else (braced, single)
                pair = (x.id, partner) if x.column == "L" else (partner, x.id)
                out.append(Block(leaf=leaf, page=page, how="brace", left=left, right=right, pair=pair))
                break


def _centred(M: Sequence[Entry], ents: Sequence[Entry], out: list, index: RogetIndex, P: float, leaf: int,
             page: str, ys: Mapping[str, float], rank: Mapping[str, int]) -> None:
    """Centred entries, top to bottom, join a block with a pair or stay alone (module docstring)."""
    for m in M:
        cands = []
        for b in out:
            if not b.pair:
                continue
            if b.bottom < m.y and m.y - b.bottom <= MIDDLE_REACH * P:
                gap = (b.bottom, m.y)
            elif b.top > m.y and b.top - m.y <= MIDDLE_REACH * P:
                gap = (m.y, b.top)
            else:
                continue
            if any(gap[0] < e.y < gap[1] for e in ents if e.id != m.id and e.id not in b.members):
                continue
            cands.append(b)
        above = [b for b in cands if b.bottom < m.y]
        below = [b for b in cands if b.top > m.y]
        options = [x for x in (max(above, key=lambda b: b.bottom) if above else None,
                               min(below, key=lambda b: b.top) if below else None) if x is not None]
        chosen = _choose_middle(m.id, options, index, rank) if options else None
        if chosen is None:
            blk = Block(leaf=leaf, page=page, how="alone", middle=[m.id])
            out.append(blk)
        else:
            chosen.middle.append(m.id)
            if chosen.how == "row":
                chosen.how = "centred"
            blk = chosen
        _span(blk, ys)


def _choose_middle(m: str, options: Sequence[Block], index: RogetIndex, rank: Mapping[str, int]) -> Block:
    """Between the block above and the block below: the one in the centred head's subsection, then the
    one next to it in number, then a row printed with its numbers inverted, then the one above."""
    if len(options) == 1:
        return options[0]
    sub = index.subsection_key(m)

    def same_sub(b):
        return all(index.subsection_key(h) == sub for h in b.pair)

    def adjacent(b):
        return any(abs(rank[h] - rank[m]) == 1 for h in b.members)

    def inverted(b):
        return _key(index, b.pair[0]) > _key(index, b.pair[1])
    for test in (same_sub, adjacent, inverted):
        hits = [b for b in options if test(b)]
        if len(hits) == 1:
            return hits[0]
    return options[0]


def _apply_overrides(blocks: list[Block], entries: Sequence[Entry], overrides: Sequence[Mapping]) -> list[Block]:
    ents = {e.id: e for e in entries}
    for ov in overrides:
        heads = list(ov["heads"])
        if not all(h in ents for h in heads) or len({ents[h].leaf for h in heads}) != 1:
            continue
        leaf = ents[heads[0]].leaf
        hit = [b for b in blocks if set(b.members) & set(heads)]
        rest = [h for b in hit for h in b.members if h not in heads]
        blocks = [b for b in blocks if b not in hit]
        nb = Block(leaf=leaf, page=ents[heads[0]].page, how="override", left=list(ov["left"]),
                   right=list(ov["right"]), pair=tuple(ov["pair"]))
        _span(nb, {h: ents[h].y for h in heads})
        blocks.append(nb)
        for h in rest:
            e = ents[h]
            b = Block(leaf=e.leaf, page=e.page, how="alone", left=[h] if e.column == "L" else [],
                      right=[h] if e.column == "R" else [], middle=[h] if e.column == "M" else [])
            _span(b, {h: e.y})
            blocks.append(b)
    return blocks


# --------------------------------------------------------------------------- checks

def check(index: RogetIndex, synopsis: Mapping[str, Mapping], rules: Mapping, known: Sequence[Mapping]) -> dict:
    """The synopsis against the index (every head once), the hand-listed known pairs, the rule pairing
    (``rules``: head id -> :class:`.pairs.HeadPairing`) and the rules' unresolved dispositional heads."""
    from .parse import DISPOSITIONAL_MIN

    def summ(h):
        s = synopsis.get(h)
        return {"kind": s["kind"], "partner": s["partner"]} if s else None

    def same_block(a, b):
        return a in synopsis and b in synopsis and synopsis[a]["block"] == synopsis[b]["block"]
    out: dict = {"heads": {"n_index": len(index.heads), "n_synopsis": sum(1 for h in synopsis if h in index.heads),
                           "missing": [h for h in index.order if h not in synopsis],
                           "extra": [h for h in synopsis if h not in index.heads]}}
    disp = [h for h in index.order if index.heads[h].number >= DISPOSITIONAL_MIN]
    out["kinds"] = {"all": dict(Counter(s["kind"] for s in synopsis.values())),
                    "dispositional": dict(Counter(synopsis[h]["kind"] for h in disp if h in synopsis))}
    kp: dict = {"checked": 0, "pair": [], "same_block": [], "other": [], "dropped": []}
    for k in known:
        a, b = str(k["a"]), str(k["b"])
        ta, tb = k.get("title_a"), k.get("title_b")
        if a not in index.heads or b not in index.heads or \
                (ta and index.heads[a].title.lower() != ta.lower()) or (tb and index.heads[b].title.lower() != tb.lower()):
            kp["dropped"].append([a, b])
            continue
        kp["checked"] += 1
        if a in synopsis and synopsis[a]["partner"] == b:
            kp["pair"].append([a, b])
        elif same_block(a, b):
            kp["same_block"].append([a, b])
        else:
            kp["other"].append({"pair": [a, b], a: summ(a), b: summ(b)})
    out["known_pairs"] = kp
    seen, rp = set(), []
    for h in index.order:
        r = rules.get(h)
        if r is not None and r.kind == "pair" and r.partner and h not in seen:
            seen |= {h, r.partner}
            rp.append(sorted([h, r.partner], key=index.position))
    rr: dict = {"n_rule_pairs": len(rp), "agree": [], "same_block": [], "disagree": [], "not_in_synopsis": []}
    for a, b in rp:
        if a not in synopsis or b not in synopsis:
            rr["not_in_synopsis"].append([a, b])
        elif synopsis[a]["partner"] == b:
            rr["agree"].append([a, b])
        elif same_block(a, b):
            rr["same_block"].append([a, b])
        else:
            rr["disagree"].append({"pair": [a, b], "sources": [rules[a].source, rules[b].source],
                                   "synopsis": {a: summ(a), b: summ(b)}})
    rr["by_source"] = {k: dict(Counter(rules[p[0]].source for p in rr[k])) for k in
                       ("agree", "same_block", "not_in_synopsis")}
    rr["by_source"]["disagree"] = dict(Counter(x["sources"][0] for x in rr["disagree"]))
    rule_pairs = {tuple(p) for p in rp}
    new = []
    seen = set()
    for h, s in synopsis.items():
        if s["kind"] == "pair" and h not in seen and h in index.heads:
            seen |= {h, s["partner"]}
            ab = tuple(sorted([h, s["partner"]], key=index.position))
            if ab not in rule_pairs:
                new.append(list(ab))
    rr["synopsis_pairs_not_in_rules"] = len(new)
    rr["synopsis_pairs_not_in_rules_by_rule_kind"] = dict(Counter(
        "+".join(sorted({rules[x].kind if x in rules else "absent" for x in ab})) for ab in new))
    out["rules"] = rr
    unres = [h for h in disp if h in rules and rules[h].kind == "unresolved"]
    by = {"pair": [], "triad": [], "singleton": [], "absent": []}
    for h in unres:
        by[synopsis[h]["kind"] if h in synopsis else "absent"].append(h)
    out["unresolved"] = {"n": len(unres), "by_synopsis_kind": {k: len(v) for k, v in by.items()}, "heads": by}
    return out


# --------------------------------------------------------------------------- download and persistence

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_xml(dest: Path, *, url: str = XML_URL, opener: Optional[Callable[[str], bytes]] = None) -> Path:
    """Download the djvu XML to ``dest`` atomically (``opener(url) -> bytes`` replaces the network in tests)."""
    if opener is None:
        def opener(u: str) -> bytes:  # noqa: E306 - the default network opener
            req = urllib.request.Request(u, headers={"User-Agent": "assistant-axis gap generation (research)"})
            with urllib.request.urlopen(req, timeout=600) as resp:  # noqa: S310 - fixed https URL
                return resp.read()
    data = opener(url)
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


def save(result: SynopsisResult, path: Path, *, inputs: Sequence = (), meta: Optional[dict] = None,
         checks: Optional[dict] = None) -> Path:
    """``synopsis_pairs.json``: a ``json_metadata`` envelope; ``heads`` one record a line."""
    from assistant_axis.plot_metadata import json_metadata

    from .parse import dumps_one_per_line
    rec = result.records()
    payload = {"synopsis_version": SYNOPSIS_VERSION, **(meta or {}),
               "pages": [{"leaf": l, "page": p, "pitch": result.pitches.get(l)}
                         for l, p in zip(sorted(result.pitches), result.page_labels)],
               "counts": {"n_heads": len(rec), "kinds": dict(Counter(r["kind"] for r in rec.values())),
                          "blocks": dict(Counter(b.how for b in result.blocks)),
                          "repairs": dict(Counter(r["method"] for r in result.repairs())),
                          "n_missing": len(result.missing), "n_unused_tokens": len(result.unused_tokens)},
               "overrides": [dict(o, heads=list(o["heads"]), left=list(o["left"]), right=list(o["right"]),
                                  pair=list(o["pair"])) for o in OVERRIDES],
               "repairs": result.repairs(), "missing": result.missing, "duplicates": result.duplicates,
               "title_mismatches": result.title_mismatches(), "unused_tokens": result.unused_tokens,
               "checks": checks, "heads": rec}
    env = json_metadata(payload, inputs=list(inputs), title="Roget 1911 Tabular Synopsis: opposed heads as printed")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(dumps_one_per_line(env, "heads"), path)
    return path


def load(path: Path) -> dict:
    """The per-head records of ``synopsis_pairs.json`` (enveloped or bare)."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    return d["heads"]


def load_payload(path: Path) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d.get("result", d)
