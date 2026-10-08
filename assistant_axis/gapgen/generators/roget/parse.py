"""Roget's Thesaurus (1911, Project Gutenberg #10681): download, checksum and parser.

The text is the Gutenberg plain-text edition, UTF-8 with CRLF line ends, in which a head reads
``604. Resolution — N. determination, will; ...`` (an em dash, not the ``--`` of older
editions) and an obsolete word carries a trailing dagger (``conation†``).  Structure lines:
``CLASS V`` / ``DIVISION I`` / ``SECTION I.`` each followed by its title on the next line, then
numbered subsection lines with no em dash (``1. PASSIVE AFFECTIONS`` in capitals, under which
``1. Acts of Volition``-style lines in mixed case are a second level; a mixed-case line in a
section with no capitalised subsection is the subsection itself).

A head runs from its head line to the next head or structure line.  Its first part-of-speech
block starts after the em dash (normally ``N.``); later blocks start at the beginning of a line
(``V.``, ``Adj.``, ``Adv.``, ``Phr.``, ``Int.``); an indented line opens a new paragraph of the
current block; a line that is neither continues the paragraph (a line ending ``word-`` joins the
next without a space: the edition wraps compounds at their hyphen).  A paragraph is split into
semicolon groups of comma items, respecting brackets and parentheses.

Item policy (:func:`clean_item`): a dagger or a language tag (:data:`DROP_TAGS`) drops the item;
a usage tag in :data:`KEEP_TAGS` keeps it with the tag recorded; an unknown bracket tag keeps the
item and is counted in ``tags_seen`` (``parse`` prints the census so the lists can be extended);
a bracket at the start of an item is an editorial gloss and is removed; parentheticals are
removed; quotations, items with digits and items over four words are dropped.  Cross-references
``&c (sense) 604`` move the item into the head's ``xrefs`` as ``(target, word)`` (a ``604.1``
target is ``604a``); ``&c adj.`` / ``&c n.`` / bare ``&c`` are dropped from the item.  Brace notes
``{ant. 478}`` / ``{opp. 87}`` are removed and recorded in ``antonym_refs``.

Plan: ``reports/trait_gap_generation/coding_plan_02_roget_wordnet.md`` §§ 5-6 (``roget.py``).
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Collection, Iterable, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text

ROGET_URL = "https://www.gutenberg.org/cache/epub/10681/pg10681.txt"
#: SHA-256 of the text as downloaded on 2026-10-08 (Gutenberg's "Most recently updated:
#: October 28, 2024" edition, 1,519,303 bytes).  ``parse`` refuses another text unless
#: ``--allow-checksum-mismatch``: the parser's invariants (head counts) are pinned to this one.
ROGET_EXPECTED_SHA256: Optional[str] = "7e9f9b78bdef6292e97f46afe1c55f05fe3c5bc1f17a136680afc330675959a1"
PARSER_VERSION = 1
POS_BLOCKS = ("N", "V", "Adj", "Adv", "Phr", "Int")

#: Language and obsolescence tags: the item is dropped (and counted).
DROP_TAGS = frozenset({
    "Obs.", "Obs", "Obs3", "Lat.", "Lat", "L.", "Fr.", "Fr", "F.", "It", "It.", "Ital.", "G.", "Ger.", "Germ.",
    "Sp.", "Span.", "Gr.", "Grk.", "Greek", "Jap.", "Rus.", "Russ.", "Hind.", "Hindi", "Hindu", "Arab.", "Ar.",
    "Heb.", "Port.", "Dan.", "Dut.", "Sans.", "Skr.", "Pers.", "Chin.", "Turk.", "Swed.", "Malay", "Anglo-Ind.",
    "Anglo-Indian", "Yiddish", "Lat., Fr.", "Fr., Lat.", "Old Eng.", "Old English", "Arch.", "Archaic",
    "Fr.Tr.", "Afrik.", "Jap.Tr.",
})
#: Usage tags: the item is kept and the tag recorded.
KEEP_TAGS = frozenset({
    "U.S.", "US", "Colloq.", "Colloq", "Coll.", "Slang", "slang", "Naut.", "Law", "Med.", "Brit.", "Scot.",
    "Chem", "Chem.", "Biol.", "Anat.", "Iron.", "Gramm.", "Micro.", "Contr.", "Comp.", "Sarc.", "Vulg.",
    "Pigments", "Mil.", "Mus.", "Theol.", "Bot.", "Zool.", "Geol.", "Math.", "Archit.", "Her.", "Eccl.",
    "Rhet.", "Polit.", "Dial.", "Prov.", "Cant", "Euph.", "Hum.", "Fig.", "Lit.",
})

_STRUCT_CLASS = re.compile(r"^CLASS\s+([IVX]+)\.?\s*$")
_STRUCT_DIVISION = re.compile(r"^DIVISION\s+\(?([IVX]+)\)?\.?\s*$")
_STRUCT_SECTION = re.compile(r"^SECTION\s+([IVX]+)\.?\s*(.*)$")
_NUMBERED = re.compile(r"^#?(\d+)([a-z]?)\.?\s+(\S.*)$")
_POS_LINE = re.compile(r"^(N|V|Adj|Adv|Phr|Int)\.\s*(.*)$")
_BRACE = re.compile(r"\{([^}]*)\}", re.S)
_BRACE_REF = re.compile(r"(?:ant|opp)\.?\s*(?:of\s+)?(\d+[a-z]?)", re.I)
_XREF = re.compile(r"&c\.?\s*(?:\(([^)]*)\)\s*)?(\d+[a-z]?(?:\.\d+)?)\b")
_POS_XREF = re.compile(r"&c\.?\s*(?:n|v|adj|adv)\.*", re.I)
_BARE_ETC = re.compile(r"&c\.?")
_TAG = re.compile(r"\[([^\]]*)\]")
_PAREN = re.compile(r"\([^()]*\)")
_DAGGER = "†"
_EM_DASH = "—"


# --------------------------------------------------------------------------- download

def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_roget(dest: Path, *, url: str = ROGET_URL, dry_run: bool = False,
                opener: Optional[Callable[[str], bytes]] = None) -> Path:
    """Download the text to ``dest`` (atomically).  ``opener(url) -> bytes`` replaces the
    network in tests.  Dry run: nothing is fetched or written."""
    dest = Path(dest)
    if dry_run:
        return dest
    if opener is None:
        def opener(u: str) -> bytes:  # noqa: E306 - the default network opener
            req = urllib.request.Request(u, headers={"User-Agent": "assistant-axis gap generation (research)"})
            with urllib.request.urlopen(req, timeout=120) as resp:  # noqa: S310 - fixed https URL
                return resp.read()
    data = opener(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(dest)
    return dest


class ChecksumMismatch(ValueError):
    pass


def check_checksum(path: Path, *, allow_mismatch: bool = False,
                   expected: Optional[str] = ROGET_EXPECTED_SHA256) -> str:
    """The file's SHA-256; raises :class:`ChecksumMismatch` when it differs from ``expected``
    (unless ``allow_mismatch``).  ``expected=None`` (not pinned yet) accepts any text."""
    got = sha256_of(path)
    if expected is not None and got != expected and not allow_mismatch:
        raise ChecksumMismatch(f"{path}: SHA-256 {got} differs from the pinned {expected}; the parser's "
                               f"invariants are pinned to that text (pass --allow-checksum-mismatch to proceed)")
    return got


def strip_gutenberg(text: str) -> str:
    """The body between the ``*** START OF`` and ``*** END OF`` markers, with CRLF normalised,
    a byte-order mark removed and ``<-- ... -->`` editorial comments (multi-line) removed."""
    text = text.replace("﻿", "").replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(r"^\*\*\* ?START OF[^\n]*\n", text, re.M)
    if m:
        text = text[m.end():]
    m = re.search(r"^\*\*\* ?END OF", text, re.M)
    if m:
        text = text[:m.start()]
    return re.sub(r"<--.*?-->", " ", text, flags=re.S)


# --------------------------------------------------------------------------- data model

@dataclass
class Head:
    id: str                      # "604", "604a"
    number: int
    letter: str
    title: str
    klass: str                   # "V"
    class_title: str
    division: Optional[str]      # "I. Individual volition" (Classes IV and V only)
    section: str                 # "I. Volition in general"
    subsection: Optional[str]    # "1. Acts of volition"
    subsubsection: Optional[str] = None
    pos: dict = field(default_factory=dict)          # block -> semicolon groups -> items
    xrefs: list = field(default_factory=list)        # [target id, word]
    antonym_refs: list = field(default_factory=list)  # targets of {ant. N} / {opp. N}
    note: Optional[str] = None                       # bracketed gloss in the head line
    n_dropped: int = 0
    drops: dict = field(default_factory=dict)        # reason -> count
    tags_seen: dict = field(default_factory=dict)    # tag -> count (every bracket tag met)
    item_tags: dict = field(default_factory=dict)    # kept item -> its usage tags
    line_start: int = 0

    def items(self, block: str) -> list[str]:
        return [it for g in self.pos.get(block, []) for it in g]

    @property
    def path(self) -> str:
        parts = [self.klass, self.division, self.section, self.subsection, self.subsubsection]
        return " > ".join(p for p in parts if p)

    def to_json(self) -> dict:
        d = asdict(self)
        d["xrefs"] = [list(x) for x in self.xrefs]
        return d

    @classmethod
    def from_json(cls, d: dict) -> "Head":
        d = dict(d)
        d["xrefs"] = [tuple(x) for x in d.get("xrefs") or []]
        return cls(**d)


@dataclass
class RogetIndex:
    heads: dict                  # id -> Head
    order: list                  # ids in text order
    by_subsection: dict          # subsection key -> ids in order
    text_sha256: Optional[str] = None
    parser_version: int = PARSER_VERSION
    unknown_tags: dict = field(default_factory=dict)

    def __getitem__(self, hid: str) -> Head:
        return self.heads[hid]

    def __contains__(self, hid: str) -> bool:
        return hid in self.heads

    def __len__(self) -> int:
        return len(self.heads)

    def subsection_key(self, hid: str) -> str:
        return subsection_key(self.heads[hid])

    def position(self, hid: str) -> int:
        if not hasattr(self, "_pos"):
            self._pos = {h: i for i, h in enumerate(self.order)}
        return self._pos[hid]


def subsection_key(h: Head) -> str:
    return h.path


# --------------------------------------------------------------------------- items

@dataclass
class _Sink:
    xrefs: list = field(default_factory=list)
    drops: Counter = field(default_factory=Counter)
    tags_seen: Counter = field(default_factory=Counter)
    item_tags: dict = field(default_factory=dict)
    unknown: Counter = field(default_factory=Counter)


def _norm_target(num: str) -> str:
    """``604`` -> ``604``; ``604.1`` -> ``604a`` (the edition's decimal form of a lettered head)."""
    if "." in num:
        base, sub = num.split(".", 1)
        try:
            return base + "abcdefghij"[int(sub) - 1]
        except (ValueError, IndexError):
            return base
    return num


def _tidy(s: str) -> str:
    s = " ".join(s.split())
    s = s.strip(" ,;:")
    s = re.sub(r"\.+$", "", s).strip()
    s = s.strip(" ,;:")
    return s


def clean_item(raw: str, *, sink: Optional[_Sink] = None) -> tuple[Optional[str], list[str]]:
    """``(item, usage tags)`` or ``(None, tags)`` when the item is dropped.

    Cross-references are recorded in ``sink.xrefs`` and the item is dropped (the word belongs to
    the target head); see the module docstring for the policy."""
    sink = sink if sink is not None else _Sink()
    s = " ".join(str(raw).split())
    if not s:
        return None, []
    # a leading bracket is an editorial gloss ("[Science of existence], ontology")
    s = re.sub(r"^\[[^\]]*\]\s*", "", s)
    m = _XREF.search(s)
    if m:
        word = _tidy(_TAG.sub(" ", _PAREN.sub(" ", s[:m.start()]))).replace(_DAGGER, "")
        sink.xrefs.append((_norm_target(m.group(2)), word))
        return None, []
    s = _POS_XREF.sub(" ", s)
    s = _BARE_ETC.sub(" ", s)
    tags = [t.strip() for t in _TAG.findall(s)]
    s = _TAG.sub(" ", s)
    s = _PAREN.sub(" ", s)
    for t in tags:
        sink.tags_seen[t] += 1
    keep = []
    for t in tags:
        if t in DROP_TAGS:
            sink.drops["foreign" if not t.lower().startswith(("obs", "arch")) else "obsolete"] += 1
            return None, tags
        if t in KEEP_TAGS:
            keep.append(t)
        elif is_attribution(t):  # "[Hamlet]", "[Paradise Lost]": the item is a quotation
            sink.drops["quotation"] += 1
            return None, tags
        else:
            sink.unknown[t] += 1
            keep.append(t)
    s = _tidy(s)
    if not s:
        sink.drops["empty"] += 1
        return None, keep
    if _DAGGER in s:
        sink.drops["obsolete"] += 1
        return None, keep
    if s[0] in "'\"‘“" or s[-1:] in ("'", '"', "’", "”") and not s.endswith("s'"):
        sink.drops["quotation"] += 1
        return None, keep
    if re.search(r"\d", s):
        sink.drops["digits"] += 1
        return None, keep
    if re.search(r"[!?=/|{}<>\[\]()]", s):
        sink.drops["punctuation"] += 1
        return None, keep
    if len(s.split()) > 4:
        sink.drops["too_long"] += 1
        return None, keep
    if keep:
        sink.item_tags[s] = keep
    return s, keep


_MINOR_WORDS = frozenset({"and", "of", "the", "in", "on", "de", "la", "le", "von", "van", "a"})


def is_attribution(tag: str) -> bool:
    """A bracket that names an author or a work (every word capitalised, no closing period, not a
    known tag): ``[Hamlet]``, ``[Bert Lance]``, ``[All's Well]``.  Editorial glosses
    (``[Applied to persons]``) and unknown abbreviations (``[Ire.]``) are not attributions."""
    t = tag.strip()
    if not t or t.endswith(".") or t in KEEP_TAGS or t in DROP_TAGS:
        return False
    words = [w for w in re.split(r"[\s,]+", t) if w]
    content = [w for w in words if w.lower() not in _MINOR_WORDS]
    return bool(content) and all(w[:1].isupper() for w in content)


def _split_top(text: str, sep: str) -> list[str]:
    """Split on ``sep`` outside brackets, parentheses and braces."""
    out, depth, cur = [], 0, []
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth = max(0, depth - 1)
        if ch == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append("".join(cur))
    return out


def split_items(block_text: str, *, sink: Optional[_Sink] = None) -> list[list[str]]:
    """``';'`` groups of ``','`` items of one paragraph, cleaned (:func:`clean_item`); empty
    groups are left out; cross-references go to ``sink.xrefs``."""
    sink = sink if sink is not None else _Sink()
    groups = []
    for g in _split_top(block_text, ";"):
        items = []
        for raw in _split_top(g, ","):
            it, _ = clean_item(raw, sink=sink)
            if it and it not in items:
                items.append(it)
        if items:
            groups.append(items)
    return groups


# --------------------------------------------------------------------------- parser

def _title_case(s: str) -> str:
    s = " ".join(s.split()).strip(" .")
    if s.isupper():
        s = s.lower()
        s = s[:1].upper() + s[1:]
    return s


def _numbered_struct(num: str, text: str) -> str:
    return f"{num}. {_title_case(text)}"


def _join_lines(lines: Sequence[str]) -> str:
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if out.endswith("-") and re.search(r"[A-Za-z]-$", out):
            out += ln
        else:
            out = f"{out} {ln}" if out else ln
    return out


def _head_title(text: str) -> tuple[str, Optional[str]]:
    notes = [n.strip() for n in _TAG.findall(text)]
    t = _TAG.sub(" ", text).replace(_DAGGER, "")
    t = re.sub(r"\.\s*&", " &", t)
    t = _tidy(t)
    return t, ("; ".join(n for n in notes if n) or None)


def parse_roget(text: str) -> RogetIndex:
    """Parse the stripped (or raw) Gutenberg text into a :class:`RogetIndex`.

    ``index.struct_lines`` (not persisted) lists ``(line index, kind, n_lines)`` for every structure
    line, kind one of ``CLASS``, ``DIVISION``, ``SECTION``, ``SUB``, ``SUBSUB``."""
    if "*** START OF" in text or "\r" in text:
        text = strip_gutenberg(text)
    lines = text.split("\n")
    n = len(lines)
    heads: dict[str, Head] = {}
    order: list[str] = []
    struct: list[tuple[int, str, int]] = []
    unknown: Counter = Counter()
    klass = class_title = ""
    division: Optional[str] = None
    section = ""
    caps_sub: Optional[str] = None
    sub: Optional[str] = None
    subsub: Optional[str] = None
    last_number = 0

    def next_nonblank(i: int) -> int:
        j = i + 1
        while j < n and not lines[j].strip():
            j += 1
        return j

    def col0_numbered(ln: str):
        return _NUMBERED.match(ln.rstrip()) if ln[:1] and not ln[:1].isspace() else None

    def lookahead(i: int, rest: str) -> tuple[str, int]:
        """The numbered line at ``i`` joined with up to three following lines (not blank, not a
        block or numbered line) until an em dash appears; and the last line used."""
        head_lines = [rest]
        j = i
        while (_EM_DASH not in " ".join(head_lines) and j + 1 < n and lines[j + 1].strip()
               and len(head_lines) < 4 and not _POS_LINE.match(lines[j + 1])
               and not col0_numbered(lines[j + 1])):
            j += 1
            head_lines.append(lines[j])
        return _join_lines(head_lines), j

    i = 0
    while i < n:
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()
        if not s:
            i += 1
            continue
        top = line == s
        m = _STRUCT_CLASS.match(s) if top else None
        if m:
            j = next_nonblank(i)
            klass, class_title = m.group(1), (_title_case(lines[j]) if j < n else "")
            division, section, caps_sub, sub, subsub = None, "", None, None, None
            struct.append((i, "CLASS", j - i + 1))
            i = j + 1
            continue
        m = _STRUCT_DIVISION.match(s) if top else None
        if m:
            j = next_nonblank(i)
            division = f"{m.group(1)}. {_title_case(lines[j])}" if j < n else m.group(1)
            section, caps_sub, sub, subsub = "", None, None, None
            struct.append((i, "DIVISION", j - i + 1))
            i = j + 1
            continue
        m = _STRUCT_SECTION.match(s) if top else None
        if m:
            title = m.group(2).strip()
            j = i
            if not title:
                j = next_nonblank(i)
                title = lines[j] if j < n else ""
            section = f"{m.group(1)}. {_title_case(title)}"
            caps_sub, sub, subsub = None, None, None
            struct.append((i, "SECTION", j - i + 1))
            i = j + 1
            continue
        m = col0_numbered(raw)
        if m:
            num, letter, rest = int(m.group(1)), m.group(2), m.group(3)
            joined, j = lookahead(i, rest)
            is_head = _EM_DASH in joined and 1 <= num <= 1000 and num >= last_number - 1
            if is_head:
                head_text, _, after = joined.partition(_EM_DASH)
                ants = [_norm_target(x) for b in _BRACE.findall(head_text + " " + after)
                        for x in _BRACE_REF.findall(b)]
                title, note = _head_title(_BRACE.sub(" ", head_text))
                body_lines = [after]
                k = j + 1
                while k < n:
                    nxt = lines[k]
                    st = nxt.strip()
                    if st and not nxt[:1].isspace():
                        if _STRUCT_CLASS.match(st) or _STRUCT_DIVISION.match(st) or _STRUCT_SECTION.match(st):
                            break
                        mm = col0_numbered(nxt)
                        if mm and not _POS_LINE.match(nxt):
                            # the next head (an em dash within its lookahead), or a structure line
                            # (after a blank line); a wrapped cross-reference number ("718 equalization;")
                            # continues the paragraph
                            if not lines[k - 1].strip() or (int(mm.group(1)) >= num
                                                            and _EM_DASH in lookahead(k, mm.group(3))[0]):
                                break
                    body_lines.append(nxt)
                    k += 1
                hid = f"{num}{letter}"
                if hid in heads:  # a repeated id (none in the pinned text) keeps both, the second suffixed
                    hid = f"{hid}~L{i + 1}"
                head = Head(id=hid, number=num, letter=letter, title=title, klass=klass, class_title=class_title,
                            division=division, section=section, subsection=sub, subsubsection=subsub,
                            antonym_refs=sorted(set(ants)), note=note, line_start=i + 1)
                unknown.update(_fill_blocks(head, body_lines))
                heads[hid] = head
                order.append(hid)
                last_number = num
                i = k
                continue
            title = _join_lines([rest])
            if num <= 12 and _EM_DASH not in title and ";" not in title:
                if title.isupper():
                    caps_sub = sub = _numbered_struct(m.group(1), title)
                    subsub = None
                    struct.append((i, "SUB", 1))
                elif caps_sub:
                    subsub = _numbered_struct(m.group(1), title)
                    struct.append((i, "SUBSUB", 1))
                else:
                    sub, subsub = _numbered_struct(m.group(1), title), None
                    struct.append((i, "SUB", 1))
            i += 1
            continue
        i += 1
    by_sub: dict[str, list[str]] = {}
    for hid in order:
        by_sub.setdefault(subsection_key(heads[hid]), []).append(hid)
    idx = RogetIndex(heads=heads, order=order, by_subsection=by_sub, unknown_tags=dict(unknown))
    idx.struct_lines = struct  # type: ignore[attr-defined]
    return idx


def _fill_blocks(head: Head, body_lines: Sequence[str]) -> Counter:
    """Assign the body's lines to part-of-speech blocks and paragraphs, then split items.  Brace
    notes (``{opp.\n     83}`` may span lines) are removed first and their targets added to
    ``head.antonym_refs``."""
    body = "\n".join(body_lines)
    refs = [_norm_target(x) for b in _BRACE.findall(body) for x in _BRACE_REF.findall(b)]
    if refs:
        head.antonym_refs = sorted(set(head.antonym_refs) | set(refs))
    body_lines = _BRACE.sub("", body).split("\n")
    blocks: dict[str, list[list[str]]] = {}  # block -> paragraphs -> raw lines
    cur: Optional[str] = None
    for idx, raw in enumerate(body_lines):
        if not raw.strip():
            continue
        text = raw.strip()
        m = _POS_LINE.match(text) if (idx == 0 or not raw[:1].isspace()) else None
        if m:
            cur = m.group(1)
            blocks.setdefault(cur, []).append([m.group(2)])
            continue
        if cur is None:  # text before any block marker: the head's N. block was not marked
            cur = "N"
            blocks.setdefault(cur, []).append([text])
            continue
        if raw[:1].isspace():
            blocks[cur].append([text])
        else:
            blocks[cur][-1].append(text)
    sink = _Sink()
    pos: dict[str, list[list[str]]] = {}
    for b, paras in blocks.items():
        groups: list[list[str]] = []
        for para in paras:
            joined = _join_lines(para)
            joined = _BRACE.sub(" ", joined)
            groups.extend(split_items(joined, sink=sink))
        if groups:
            pos[b] = groups
    head.pos = {b: pos[b] for b in POS_BLOCKS if b in pos}
    head.xrefs = [(t, w) for t, w in dict.fromkeys(sink.xrefs)]
    head.drops = dict(sorted(sink.drops.items()))
    head.n_dropped = sum(sink.drops.values())
    head.tags_seen = dict(sorted(sink.tags_seen.items()))
    head.item_tags = dict(sink.item_tags)
    return sink.unknown


# --------------------------------------------------------------------------- selections and profiles

#: Classes IV-VI (intellect, volition, affections) start at head 450.
DISPOSITIONAL_MIN = 450


def dispositional_heads(index: RogetIndex, *, extra: Collection[str] = ()) -> list[Head]:
    """Heads numbered >= 450 (Classes IV-VI) plus ``extra`` ids, in text order."""
    extra = set(extra)
    return [index.heads[h] for h in index.order
            if index.heads[h].number >= DISPOSITIONAL_MIN or h in extra]


def head_profile(head: Head, *, n_adj: int = 15, n_noun: int = 10) -> str:
    """``"{title}. {section} / {subsection}. Adjectives: a, b, ... Nouns: x, y, ..."``: the text the
    semantic route embeds for a head."""
    where = " / ".join(p.split(". ", 1)[-1] for p in (head.section, head.subsubsection or head.subsection) if p)
    adj = head.items("Adj")[:n_adj]
    noun = head.items("N")[:n_noun]
    parts = [f"{head.title}."]
    if where:
        parts.append(f"{where}.")
    if adj:
        parts.append("Adjectives: " + ", ".join(adj) + ".")
    if noun:
        parts.append("Nouns: " + ", ".join(noun) + ".")
    return " ".join(parts)


# --------------------------------------------------------------------------- fixture

def extract_fixture(text: str, numbers: Sequence[str]) -> str:
    """The stripped text restricted to the heads ``numbers`` (ids such as ``"604a"``) and the
    structure lines above each (verbatim, in text order): a small sample for tests."""
    body = strip_gutenberg(text) if ("*** START OF" in text or "\r" in text) else text
    idx = parse_roget(body)
    lines = body.split("\n")
    struct = list(idx.struct_lines)  # type: ignore[attr-defined]
    starts = [(idx.heads[h].line_start - 1, h) for h in idx.order]
    boundaries = sorted({s for s, _ in starts} | {s for s, _, _ in struct} | {len(lines)})
    rank = {"CLASS": 0, "DIVISION": 1, "SECTION": 2, "SUB": 3, "SUBSUB": 4}
    out: list[str] = []
    emitted: set[int] = set()
    want = set(numbers)
    for begin, hid in starts:
        if hid not in want:
            continue
        ctx: dict[int, tuple[int, int]] = {}  # level -> (line, n_lines)
        for si, kind, nl in struct:
            if si >= begin:
                break
            lvl = rank[kind]
            ctx = {k: v for k, v in ctx.items() if k < lvl}
            ctx[lvl] = (si, nl)
        for lvl in sorted(ctx):
            si, nl = ctx[lvl]
            if si not in emitted:
                emitted.add(si)
                out.extend([ln for ln in lines[si:si + nl] if ln.strip()])
                out.append("")
        end = next(b for b in boundaries if b > begin)
        span = lines[begin:end]
        while span and not span[-1].strip():
            span.pop()
        out.extend(span)
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"


# --------------------------------------------------------------------------- persistence

def save_heads(index: RogetIndex, path: Path, *, text_path: Optional[Path] = None) -> Path:
    """``heads.json``: a ``json_metadata`` envelope around ``{"order", "heads", ...}``."""
    from assistant_axis.plot_metadata import json_metadata
    from assistant_axis.provenance import current_file_input

    payload = {"parser_version": index.parser_version, "text_sha256": index.text_sha256,
               "n_heads": len(index.order), "order": " ".join(index.order),
               "unknown_tags": dict(sorted(index.unknown_tags.items())),
               "heads": [index.heads[h].to_json() for h in index.order]}
    inputs = []
    if text_path is not None and Path(text_path).exists():
        inputs.append(current_file_input("roget_text", Path(text_path),
                                         extras={"sha256": index.text_sha256 or "",
                                                 "parser_version": str(index.parser_version)}))
    env = json_metadata(payload, inputs=inputs, title="Roget 1911 heads (gap generation, workstream 2)")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(dumps_one_per_line(env, "heads"), path)
    return path


def dumps_one_per_line(env: dict, key: str) -> str:
    """The envelope with ``result[key]`` (a list) written one compact element per line: small and
    readable in a diff."""
    marker = "\u0000LIST\u0000"
    items = env["result"][key]
    shell = {**env, "result": {**env["result"], key: marker}}
    text = json.dumps(shell, indent=1, ensure_ascii=False)
    if isinstance(items, dict):
        body = "{\n" + ",\n".join(json.dumps(k, ensure_ascii=False) + ":" + json.dumps(v, ensure_ascii=False,
                                                                                       separators=(",", ":"))
                                    for k, v in items.items()) + "\n }"
    else:
        body = "[\n" + ",\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n ]"
    return text.replace(json.dumps(marker), body) + "\n"


def index_from_payload(payload: dict) -> RogetIndex:
    heads = {d["id"]: Head.from_json(d) for d in payload["heads"]}
    order = payload.get("order") or [d["id"] for d in payload["heads"]]
    order = order.split() if isinstance(order, str) else list(order)
    by_sub: dict[str, list[str]] = {}
    for hid in order:
        by_sub.setdefault(subsection_key(heads[hid]), []).append(hid)
    return RogetIndex(heads=heads, order=order, by_subsection=by_sub, text_sha256=payload.get("text_sha256"),
                      parser_version=int(payload.get("parser_version") or PARSER_VERSION),
                      unknown_tags=dict(payload.get("unknown_tags") or {}))


def load_heads(path: Path) -> RogetIndex:
    """Read ``heads.json`` (enveloped or bare)."""
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return index_from_payload(d.get("result", d))


def parse_file(path: Path, *, allow_mismatch: bool = False,
               expected: Optional[str] = ROGET_EXPECTED_SHA256) -> RogetIndex:
    sha = check_checksum(path, allow_mismatch=allow_mismatch, expected=expected)
    idx = parse_roget(Path(path).read_text(encoding="utf-8"))
    idx.text_sha256 = sha
    return idx


def census(index: RogetIndex) -> dict:
    """Counts ``parse`` prints: heads, distinct numbers, lettered heads, heads with an Adj block,
    the bracket-tag census, drop reasons."""
    hs = [index.heads[h] for h in index.order]
    tags: Counter = Counter()
    drops: Counter = Counter()
    for h in hs:
        tags.update(h.tags_seen)
        drops.update(h.drops)
    return {"n_heads": len(hs), "n_numbers": len({h.number for h in hs}),
            "n_lettered": sum(1 for h in hs if h.letter), "n_with_adj": sum(1 for h in hs if "Adj" in h.pos),
            "n_dispositional": sum(1 for h in hs if h.number >= DISPOSITIONAL_MIN),
            "n_no_subsection": sum(1 for h in hs if not h.subsection),
            "drops": dict(drops.most_common()), "tags": dict(tags.most_common()),
            "unknown_tags": dict(Counter(index.unknown_tags).most_common())}


def iter_items(index: RogetIndex, block: str, heads: Optional[Iterable[str]] = None):
    """``(head id, group index, item)`` for every item of ``block``."""
    for hid in heads if heads is not None else index.order:
        for gi, g in enumerate(index.heads[hid].pos.get(block, [])):
            for it in g:
                yield hid, gi, it
