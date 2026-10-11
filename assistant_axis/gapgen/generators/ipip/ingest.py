"""Parse the IPIP pages, the 21 key pages and the item assignment workbook into ``items.jsonl``.

* :func:`parse_item_list`: ``AlphabeticalItemList.htm`` -> ``[(code, text, codes)]``, one per Eugene-Springfield
  code (3,320 on the real page), the cell's text with its whitespace collapsed.
* :func:`parse_scale_index`: ``newIndexofScaleLabels.htm`` -> :class:`ConstructRow` per link (construct label,
  inventory abbreviation, scale code, the key page it links to).  It names the inventories, lists the constructs
  and says which key page each construct is on; the item keys are not on this page.
* :func:`parse_key_page`: one of IPIP's 21 per-inventory key pages -> :class:`KeyRow` per (item, construct), the
  key's sign from the page's own ``+ keyed`` / ``- keyed`` markers.  **This is source B, the primary source of
  every committed key** (QUESTIONS 52, option C, Roger 2026-10-11).
* :func:`parse_assignment_table`: Tedone's item assignment workbook (QUESTIONS 52: the table is an Excel
  workbook, not the HTML page the plan named) -> :class:`AssignmentRow` per (item text, scale), read with the
  standard library (:func:`read_xlsx_rows`: an ``.xlsx`` is a zip of XML parts), by its documented columns
  (instrument, alpha, key, text, label; found by header, wherever the header row sits).  **This is source A, a
  check on B and a gap-filler**, never the sole authority for a committed key.
* :func:`compare_keys`: what A keys and B does not and the reverse, and the share of items both key whose
  instrument, scale and sign match exactly.  Roger's standing instruction (QUESTIONS 52): anything beyond
  rounding -- above :data:`MISMATCH_LIMIT` of the shared items, or a coverage difference above
  :data:`COVERAGE_ITEM_LIMIT` items -- goes to him with the question reopened rather than resolved in code, so
  the comparison sets ``needs_roger`` and the CLI prints it loudly.
* :func:`merge_keys`: B's rows, plus A's rows for an (item, inventory, construct) B does not key at all; the
  merged row carries ``key_source`` (:data:`SOURCE_B` or :data:`SOURCE_A`), which is what makes the tracked
  ``items.jsonl`` self-describing (QUESTIONS 46) and an A-only key droppable in one pass.  Where both key the
  same (item, inventory, construct) with **different** signs, B wins and the row is marked ``disputed``.
* :func:`build_items`: the join, by item text (:func:`text_key`: case, whitespace, curly quotes and the final
  full stop do not count); a key row whose text is in no item list is counted and listed, never dropped
  silently.  Every item of the list is kept, with ``scales: []`` when no scale scores it.

**Decoding** (QUESTIONS 49): the IPIP pages are **iso-8859-1, not UTF-8**, and a silent mis-decode is what would
fire the HEX assertion for the wrong reason (BSD ``grep`` took them for binary files and printed nothing, which
is how two checks came back empty on 2026-10-11).  :func:`decode_page` decodes explicitly; nothing in this module
guesses an encoding.

``items.jsonl`` is deterministic (rows in code order: the letter, then the number; scales sorted), so a rerun on
the same inputs writes the same bytes; :func:`write_items` copies the old file to ``.bak.<UTC>`` before it changes
(snapshot before overwrite).  Two permanent scrape-completeness checks, each a clear error and never a silent
pass: :func:`check_hex` (plan § 7: at least 20 constructs keyed ``HEX`` with about 240 items, the IPIP-HEXACO
block of plan 07 § 2) and :func:`check_key_pages` (all 21 key pages parsed, each yielding rows).
"""
from __future__ import annotations

import hashlib
import html as _html
import io
import re
import shutil
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence
from xml.etree import ElementTree as ET

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.registry import utc_stamp

from . import EXTERNAL_DIR, ITEMS_PATH
from .sources import KEY_PAGE_KEYS, N_KEY_PAGES, SOURCES, WORKBOOK_KEY

#: 2 since 2026-10-11: every scale entry carries ``key_source`` (QUESTIONS 46).
SCHEMA_VERSION = 2
CODE_RE = re.compile(r"^[A-Z]\d+$")
#: plan § 7: at least 20 constructs keyed HEX, with about 240 items (24 facets x 10).
HEX_MIN_CONSTRUCTS = 20
HEX_ITEM_RANGE = (200, 300)
#: The IPIP pages are a single-byte Windows encoding, never UTF-8 (QUESTIONS 49); nothing here guesses.
#: ``cp1252`` and not ``iso-8859-1``, which is the family QUESTIONS 49 names and what the scale index's own
#: ``<meta>`` declares, because the pages in fact carry bytes that iso-8859-1 does not define as text: measured
#: on the three pages fetched 2026-10-10, ``AlphabeticalItemList.htm`` has one 0x92 ("Act as if I\x92m somebody
#: else", a right single quote) and ``newIndexofScaleLabels.htm`` one 0x96 ("Questionnaire\x96276", an en dash).
#: cp1252 is iso-8859-1 plus exactly that 0x80-0x9F block, so it reads both files correctly where iso-8859-1
#: would hand back the C1 control characters U+0092 and U+0096 -- which would then land in the tracked
#: ``items.jsonl`` and stop :func:`text_key` from matching the apostrophe.  The item list's own ``<meta>`` says
#: ``windows-1252``.  Decoding is strict, so a byte outside cp1252 is a loud error, not a silent replacement.
PAGE_ENCODING = "cp1252"
#: Where a committed key sign came from, as ``items.jsonl`` spells it.
SOURCE_B = "ipip_key_pages"
SOURCE_A = "tedone_workbook"
#: Roger's standing instruction (QUESTIONS 52): past these, the A-vs-B difference goes to him, not into code.
MISMATCH_LIMIT = 0.02
COVERAGE_ITEM_LIMIT = 50
#: The workbook's columns (ItemAssignmentTable.htm): which header names each field may carry.
COLUMNS: dict[str, tuple[str, ...]] = {
    "instrument": ("instrument", "inventory"),
    "alpha": ("alpha",),
    "key": ("key", "keyed"),
    "text": ("text", "item", "item text"),
    "label": ("label", "construct", "trait label"),
}
REQUIRED_COLUMNS = ("instrument", "key", "text", "label")
#: Instrument names as the workbook may write them -> the scale index's abbreviations (an unknown name is kept as
#: written, upper-cased).
INVENTORY_ALIASES: dict[str, str] = {
    "HEXACO": "HEX", "HEXACO-PI": "HEX", "HEXACO PI": "HEX", "HEXACO-PI-R": "HEX", "IPIP-HEXACO": "HEX",
    "NEO-PI-R": "NEO", "NEO PI-R": "NEO", "IPIP-NEO": "NEO",
}


class HexAssertionError(AssertionError):
    """The HEX block is not where plan 07 § 2 found it."""


class KeyPageError(AssertionError):
    """A key page is missing from the scrape, or parsed to nothing (QUESTIONS 49: a short scrape, loudly)."""


# --------------------------------------------------------------------------- the pages

def decode_page(data: bytes | str) -> str:
    """An IPIP page as text, decoded **explicitly** as :data:`PAGE_ENCODING` (QUESTIONS 49): these pages are not
    UTF-8, and a silent mis-decode is what would make a parser come back empty and fire the HEX assertion for the
    wrong reason.  A ``str`` is returned unchanged."""
    if isinstance(data, str):
        return data
    return bytes(data).decode(PAGE_ENCODING)


def _soup(html: bytes | str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(decode_page(html), "html.parser")


def _clean(s: str) -> str:
    return " ".join(str(s).replace("\xa0", " ").split())


def parse_item_list(html: bytes | str) -> list[tuple[str, str, tuple[str, ...]]]:
    """``[(code, text, codes)]`` in page order: every table row whose second cell holds one or more codes
    (``H1131``; an item given in several surveys is printed once with all its codes, ``H843, F44, T192``).
    ``code`` is the first code as printed, ``codes`` all of them.  A footnote asterisk after a code (29 of the
    VIA items added by du Plessis and de Bruin, ``W92*``) is dropped."""
    out = []
    for tr in _soup(html).find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        codes = tuple(c for c in re.split(r"[,\s;*]+", _clean(tds[1].get_text(" "))) if c)
        text = _clean(tds[0].get_text(" "))
        if codes and all(CODE_RE.match(c) for c in codes) and text:
            out.append((codes[0], text, codes))
    return out


@dataclass(frozen=True)
class ConstructRow:
    label: str          # the construct label of the index ("Orderliness")
    inventory: str      # "NEO", "HEX", "CAT-PD", ... (the text before the colon)
    scale: str          # "C2", "C-Orga", "Domain", ...
    href: str           # the key page it links to


def parse_scale_index(html: bytes | str) -> list[ConstructRow]:
    """One row per link of the index: the construct label is the text before the link's line's first
    parenthesis, the link text is ``INV: scale)`` (or ``INV Domain)``)."""
    soup = _soup(html)
    out: list[ConstructRow] = []
    label: Optional[str] = None
    for node in soup.descendants:
        name = getattr(node, "name", None)
        if name == "br":
            label = None
            continue
        if name is None:            # a text node
            parent = getattr(node.parent, "name", None)
            if parent == "a":
                continue
            text = _clean(node)
            if label is None and text and "(" in text:
                head = text.split("(", 1)[0].strip().strip(",").strip()
                if head:
                    label = head
            continue
        if name == "a" and label:
            href = node.get("href") or ""
            if not href or href.startswith(("http", "mailto")) or href == "index.htm":
                continue
            t = _clean(node.get_text(" ")).rstrip(")").strip()
            if ":" in t:
                inv, scale = (x.strip() for x in t.split(":", 1))
            elif t.endswith(" Domain"):                  # "NEO Domain", "Big-Five Domain"
                inv, scale = t[:-len(" Domain")], "Domain"
            else:                                         # "Barchard, 2001": a single scale, named by its source
                inv, scale = t, ""
            out.append(ConstructRow(label=label, inventory=inv.strip(), scale=scale.strip(), href=href))
    return out


def constructs_by_page(constructs: Sequence[ConstructRow]) -> dict[str, list[ConstructRow]]:
    """The scale index's rows grouped by the key page they link to (``newNEOKey.htm``, the fragment dropped)."""
    out: dict[str, list[ConstructRow]] = defaultdict(list)
    for c in constructs:
        page = (c.href or "").split("#", 1)[0].strip()
        if page:
            out[page].append(c)
    return dict(out)


# --------------------------------------------------------------------------- the key pages (source B)

@dataclass(frozen=True)
class KeyRow:
    """One (item, construct) key, from a key page (source B) or the workbook (source A)."""
    inventory: str              # the scale index's abbreviation ("NEO", "HEX", ...)
    construct: str              # the construct label ("Orderliness")
    key: str                    # "+" or "-"
    text: str                   # the item text as the source prints it
    key_source: str = SOURCE_B
    scale: Optional[str] = None   # the scale code of the index ("C2"), when known
    page: str = ""                # the key page's file name (B) or the workbook's (A)
    row: int = 0                  # the sheet row (A) or the page line (B), for tracing

    def as_dict(self) -> dict:
        return asdict(self)


#: ``+ keyed`` / ``- keyed`` as the key pages write it, allowing "(+ keyed)", "+keyed:", a unicode minus and an
#: en or em dash; the rest of the line (an item printed beside the marker) is group 2.
_KEYED_RE = re.compile(r"^[(\[]?\s*([+\-‐-―−])\s*keyed\b\s*[)\]:.]?\s*(.*)$", re.I)
#: Tags that end a line; everything between them is one line of the page's text.
_BLOCK_TAGS_RE = re.compile(r"</?(?:br|p|div|tr|td|th|li|h[1-6]|table|tbody|thead|ul|ol|dl|dt|dd|blockquote|hr|"
                            r"center|caption|pre)\b[^>]*>", re.I)
_SCRIPT_RE = re.compile(r"(?is)<(script|style)\b[^>]*>.*?</\1\s*>")
#: A construct header's ornaments: a leading scale code ("N1:", "I+.", "C2 -") and a trailing parenthesis
#: (an alpha, "(.83)", "(alpha = .83)", or an item count).
_LEADING_CODE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+\-/]{0,7}\s*[.:)\]]\s+")
_TRAILING_PAREN_RE = re.compile(r"\s*[(\[][^()\[\]]*[)\]]\s*$")
_ALPHA_RE = re.compile(r"[(\[]\s*(?:alpha|α|cronbach)?\s*=?\s*\.\d\d", re.I)


def page_lines(html: bytes | str) -> list[str]:
    """The page's visible text, one line per block tag or ``<br>``, whitespace collapsed, entities resolved,
    empty lines dropped.  Decoded iso-8859-1 (:func:`decode_page`)."""
    text = _SCRIPT_RE.sub(" ", decode_page(html))
    text = _BLOCK_TAGS_RE.sub("\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return [s for s in (_clean(line) for line in text.split("\n")) if s]


def _norm_label(s: str) -> str:
    """A construct label for matching: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


def _header_candidates(line: str) -> list[str]:
    """The forms of a line that could be a construct header, most-stripped last."""
    out = [line]
    stripped = _TRAILING_PAREN_RE.sub("", line).strip().rstrip(":").strip()
    out.append(stripped)
    out.append(_LEADING_CODE_RE.sub("", stripped).strip())
    seen, keep = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            keep.append(x)
    return keep


def inventory_from_page(page: str) -> str:
    """A key page's inventory abbreviation from its file name, for a page whose constructs the scale index does
    not list at all: ``new16PFKey.htm`` -> ``16PF``, ``BFASKeys.htm`` -> ``BFAS``.  A documented fallback only;
    on the real pages the index supplies the abbreviation."""
    s = re.sub(r"\.html?$", "", str(page or ""), flags=re.I)
    s = re.sub(r"^new", "", s)
    s = re.sub(r"(?:Scoring)?Keys?$", "", s)
    return s.strip("_-.").upper()


def _looks_like_header(line: str) -> bool:
    """A line that is a construct header rather than an item, when the scale index does not know the label:
    it carries an alpha in parentheses, or ends with a colon, or is short and does not end like a sentence."""
    if _ALPHA_RE.search(line):
        return True
    if line.endswith(":"):
        return True
    return len(line) <= 60 and not line.endswith((".", "?", "!", '."', ".)"))


def parse_key_page(html: bytes | str, *, constructs: Sequence[ConstructRow] = (), known_texts: Optional[set] = None,
                   page: str = "", default_inventory: Optional[str] = None) -> tuple[list[KeyRow], dict]:
    """``(rows, counts)`` for one of IPIP's per-inventory key pages.

    The page is read as lines (:func:`page_lines`).  A line matching ``+ keyed`` / ``- keyed`` sets the sign for
    the lines that follow; every other line is either a **construct header** -- the scale index's label for this
    page, or the anchor the index links to, or its scale code (matched on letters and digits alone, after a
    leading scale code and a trailing parenthesis are stripped) or, failing that, a line that
    :func:`_looks_like_header` -- or an **item**, which is kept when a sign is in force.  ``known_texts`` is the
    item list's :func:`text_key` set: with it, a line that is a known item text is always read as an item, never
    as a header, which is what keeps one unmatched line from stealing the construct from the items below it.

    A matched header records the **index's** construct label and inventory, not the heading as the page prints
    it, so that a key page naming an inventory's own scale ("Organization" under the anchor the index reaches as
    HEX / Orderliness) joins the other sources on one name.  A construct the index does not list keeps the
    heading as written, with ``default_inventory`` (the page's commonest) as its inventory.
    """
    by_label: dict[str, ConstructRow] = {}
    for c in constructs:           # the index's label first, then the anchor it links to, then the scale code
        by_label.setdefault(_norm_label(c.label), c)
    for c in constructs:
        frag = (c.href or "").split("#", 1)[1] if "#" in (c.href or "") else ""
        for alt in (frag, c.scale):
            if alt and _norm_label(alt):
                by_label.setdefault(_norm_label(alt), c)
    inv_counts = Counter(c.inventory for c in constructs if c.inventory)
    default_inventory = default_inventory or (inv_counts.most_common(1)[0][0] if inv_counts
                                              else inventory_from_page(page))
    rows: list[KeyRow] = []
    construct: Optional[ConstructRow] = None
    unindexed: Optional[str] = None
    sign: Optional[str] = None
    unmatched: list[str] = []
    other = 0
    seen_labels: set = set()
    for n, line in enumerate(page_lines(html), 1):
        m = _KEYED_RE.match(line)
        if m:
            sign = "+" if m.group(1) == "+" else "-"
            line = _clean(m.group(2))
            if not line:
                continue
        else:
            hit = None
            for cand in _header_candidates(line):
                hit = by_label.get(_norm_label(cand))
                if hit is not None:
                    break
            is_known_item = known_texts is not None and text_key(line) in known_texts
            if hit is not None and not is_known_item:
                construct, unindexed, sign = hit, None, None
                seen_labels.add(hit.label)
                continue
            if not is_known_item and _looks_like_header(line) and not _KEYED_RE.match(line):
                bare = _TRAILING_PAREN_RE.sub("", line).strip().rstrip(":").strip()
                construct, unindexed, sign = None, _clean(_LEADING_CODE_RE.sub("", bare)) or _clean(bare), None
                continue
        if sign is None:
            other += 1
            continue
        if known_texts is not None and text_key(line) not in known_texts:
            unmatched.append(line)
            continue
        label = construct.label if construct is not None else unindexed
        if not label:
            other += 1
            continue
        rows.append(KeyRow(inventory=(construct.inventory if construct is not None else default_inventory) or "",
                           construct=label, key=sign, text=line, key_source=SOURCE_B,
                           scale=construct.scale if construct is not None else None, page=page, row=n))
    counts = {"page": page, "n_rows": len(rows), "n_constructs": len({(r.inventory, r.construct) for r in rows}),
              "n_keyed_minus": sum(1 for r in rows if r.key == "-"),
              "indexed_constructs": len(seen_labels), "index_constructs": len(by_label),
              "unlisted_constructs": sorted({r.construct for r in rows if _norm_label(r.construct) not in by_label}),
              "unmatched_items": len(unmatched), "unmatched_list": sorted(set(unmatched))[:20],
              "other_lines": other, "default_inventory": default_inventory,
              "inventories": dict(sorted(Counter(r.inventory for r in rows).items()))}
    return rows, counts


def parse_key_pages(external: Path, *, constructs: Sequence[ConstructRow] = (), known_texts: Optional[set] = None,
                    keys: Sequence[str] = KEY_PAGE_KEYS) -> tuple[list[KeyRow], dict]:
    """Every key page on disk under ``external``, parsed and concatenated.  ``counts["missing"]`` names the pages
    not on disk and ``counts["empty"]`` the ones that parsed to no rows: both are scrape failures
    (:func:`check_key_pages`), never a silent pass."""
    external = Path(external)
    per_page = constructs_by_page(constructs)
    rows: list[KeyRow] = []
    pages, missing, empty = {}, [], []
    for k in keys:
        src = SOURCES[k]
        p = external / src.dest
        if not p.exists():
            missing.append(src.dest)
            continue
        got, c = parse_key_page(p.read_bytes(), constructs=per_page.get(src.dest, ()), known_texts=known_texts,
                                page=src.dest)
        c["sha256"] = file_sha256(p)
        pages[src.dest] = c
        rows += got
        if not got:
            empty.append(src.dest)
    counts = {"n_pages_expected": N_KEY_PAGES, "n_pages_read": len(pages), "missing": missing, "empty": empty,
              "n_rows": len(rows), "per_page": pages,
              "n_constructs": len({(r.inventory, r.construct) for r in rows}),
              "n_items": len({text_key(r.text) for r in rows})}
    return rows, counts


def check_key_pages(counts: Mapping) -> None:
    """Permanent scrape-completeness check on source B (QUESTIONS 49's spirit, applied to the key pages): all 21
    pages on disk, each yielding rows.  :class:`KeyPageError` names what to fetch."""
    k = counts.get("key_pages") or counts
    missing, empty = list(k.get("missing") or []), list(k.get("empty") or [])
    if not missing and not empty and int(k.get("n_pages_read") or 0) >= int(k.get("n_pages_expected") or N_KEY_PAGES):
        return
    parts = []
    if missing:
        parts.append(f"{len(missing)} key page(s) not on disk: {', '.join(missing)}")
    if empty:
        parts.append(f"{len(empty)} key page(s) parsed to no rows: {', '.join(empty)}")
    if not parts:
        parts.append(f"only {k.get('n_pages_read')} of {k.get('n_pages_expected')} key pages read")
    raise KeyPageError(
        "; ".join(parts) + ".  The key pages are the primary source of every committed key (QUESTIONS 52, option "
        "C): fetch them with `ipip_generator.py download` (all 21 are in DEFAULT_FETCH, approved 2026-10-11).  A "
        "page on disk that parses to nothing is a parser or an encoding problem, not a missing file: these pages "
        "are iso-8859-1 (QUESTIONS 49)")


# --------------------------------------------------------------------------- the workbook

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_PKG_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_REF_RE = re.compile(r"^([A-Z]+)(\d+)$")


def _col_index(ref: str) -> int:
    letters = _REF_RE.match(ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _first_sheet(z: zipfile.ZipFile) -> str:
    names = set(z.namelist())
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        sheet = next(wb.iter(f"{_NS}sheet"))
        rid = sheet.get(f"{_REL_NS}id")
        target = next(r.get("Target") for r in rels.iter(f"{_PKG_REL_NS}Relationship") if r.get("Id") == rid)
        path = target.lstrip("/") if target.startswith("/") else "xl/" + target
        if path in names:
            return path
    except (KeyError, StopIteration, ET.ParseError):
        pass
    if "xl/worksheets/sheet1.xml" in names:
        return "xl/worksheets/sheet1.xml"
    raise ValueError("no worksheet found in the workbook")


def read_xlsx_rows(data: bytes) -> list[list[str]]:
    """The first sheet's rows as lists of cell strings (empty cells as ""), with the standard library only.
    Shared strings, inline strings, numbers and booleans are read; formulas give their cached value."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_NS}si"):
                # the visible text: <t> directly under <si> and under rich-text runs <r>, not phonetic runs
                parts = [t.text or "" for t in si.findall(f"{_NS}t")]
                parts += [t.text or "" for r in si.findall(f"{_NS}r") for t in r.findall(f"{_NS}t")]
                shared.append("".join(parts))
        root = ET.fromstring(z.read(_first_sheet(z)))
    rows: list[list[str]] = []
    for row in root.iter(f"{_NS}row"):
        cells: dict[int, str] = {}
        for i, c in enumerate(row.findall(f"{_NS}c")):
            ref = c.get("r")
            col = _col_index(ref) if ref and _REF_RE.match(ref) else i
            t = c.get("t")
            v = c.find(f"{_NS}v")
            if t == "s" and v is not None and v.text is not None:
                val = shared[int(v.text)]
            elif t == "inlineStr":
                val = "".join(x.text or "" for x in c.iter(f"{_NS}t"))
            elif t == "b" and v is not None:
                val = "TRUE" if v.text == "1" else "FALSE"
            else:
                val = v.text if v is not None and v.text is not None else ""
            cells[col] = val
        rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
    return rows


@dataclass(frozen=True)
class AssignmentRow:
    instrument: str     # as the workbook writes it
    inventory: str      # the scale index's abbreviation (INVENTORY_ALIASES), or the instrument upper-cased
    construct: str      # the construct label ("Orderliness")
    key: str            # "+" or "-"
    text: str           # the item text
    alpha: Optional[str] = None
    row: int = 0        # 1-based row in the sheet


def inventory_code(instrument: str) -> str:
    s = _clean(instrument)
    return INVENTORY_ALIASES.get(s.upper(), INVENTORY_ALIASES.get(s, s.upper()))


def _key_sign(v: str, *, row: int) -> str:
    s = _clean(v).replace("−", "-")
    try:
        x = float(s)
    except ValueError:
        x = {"+": 1.0, "-": -1.0}.get(s, 0.0)
    if x == 1.0:
        return "+"
    if x == -1.0:
        return "-"
    raise ValueError(f"workbook row {row}: key {v!r} is not 1 or -1")


def _header(rows: Sequence[Sequence[str]]) -> tuple[int, dict[str, int]]:
    for i, row in enumerate(rows[:50]):
        names = [_clean(c).lower() for c in row]
        found = {}
        for field_, aliases in COLUMNS.items():
            for j, n in enumerate(names):
                if n in aliases and field_ not in found and j not in found.values():
                    found[field_] = j
        if all(f in found for f in REQUIRED_COLUMNS):
            return i, found
    raise ValueError(f"no header row with the columns {', '.join(REQUIRED_COLUMNS)} in the workbook's first 50 rows")


def parse_assignment_table(data: bytes) -> list[AssignmentRow]:
    """One :class:`AssignmentRow` per data row of the workbook (rows with no text are skipped)."""
    rows = read_xlsx_rows(data)
    h, cols = _header(rows)
    out = []
    for i, row in enumerate(rows[h + 1:], h + 2):
        def cell(f):
            j = cols.get(f)
            return row[j] if j is not None and j < len(row) else ""
        text = _clean(cell("text"))
        if not text:
            continue
        instrument = _clean(cell("instrument"))
        out.append(AssignmentRow(instrument=instrument, inventory=inventory_code(instrument),
                                 construct=_clean(cell("label")), key=_key_sign(cell("key"), row=i), text=text,
                                 alpha=_clean(cell("alpha")) or None, row=i))
    return out


def assignment_key_rows(rows: Sequence[AssignmentRow]) -> list[KeyRow]:
    """The workbook's rows as :class:`KeyRow` (source A), so that A and B compare and merge in one shape."""
    page = SOURCES[WORKBOOK_KEY].dest
    return [KeyRow(inventory=r.inventory, construct=r.construct, key=r.key, text=r.text, key_source=SOURCE_A,
                   scale=None, page=page, row=r.row) for r in rows]


# --------------------------------------------------------------------------- A against B (QUESTIONS 52)

def _link(r: KeyRow) -> tuple[str, str, str]:
    """A key's identity for comparison and merging: (item text, inventory, construct), all normalised."""
    return (text_key(r.text), _clean(r.inventory).upper(), _norm_label(r.construct))


def _by_link(rows: Iterable[KeyRow]) -> dict[tuple, KeyRow]:
    """One row per link; a source that repeats a link with the same sign keeps the first, a sign clash inside
    one source keeps the first and is counted by :func:`compare_keys` through ``n_rows`` against ``n_links``."""
    out: dict[tuple, KeyRow] = {}
    for r in rows:
        out.setdefault(_link(r), r)
    return out


def compare_keys(b_rows: Sequence[KeyRow], a_rows: Optional[Sequence[KeyRow]], *, examples: int = 25) -> dict:
    """What source B (the key pages) and source A (the workbook) each key, both ways, and how far they agree.

    Reported, never resolved in code (Roger's standing instruction, QUESTIONS 52): ``needs_roger`` is true when
    the items both key disagree on more than :data:`MISMATCH_LIMIT` of their links or of their items, or when
    either side covers more than :data:`COVERAGE_ITEM_LIMIT` items the other does not.  ``None`` for ``a_rows``
    (the workbook not on disk) gives a record saying so, with ``needs_roger`` false."""
    B = _by_link(b_rows)
    items_b = {k[0] for k in B}
    if a_rows is None:
        return {"compared": False, "reason": "the assignment workbook (source A) is not on disk: no check was run",
                "n_links_b": len(B), "n_items_b": len(items_b), "needs_roger": False}
    A = _by_link(a_rows)
    items_a = {k[0] for k in A}
    only_b, only_a = sorted(set(B) - set(A)), sorted(set(A) - set(B))
    shared = sorted(set(A) & set(B))
    conflicts = [k for k in shared if A[k].key != B[k].key]
    items_only_b, items_only_a = sorted(items_b - items_a), sorted(items_a - items_b)
    both_items = sorted(items_b & items_a)
    # per item: the whole set of (inventory, construct, sign) triples has to match for an exact match
    def triples(rows: Mapping[tuple, KeyRow], item: str) -> set:
        return {(k[1], k[2], r.key) for k, r in rows.items() if k[0] == item}
    exact_items = [i for i in both_items if triples(B, i) == triples(A, i)]
    # the mismatch rate is disagreement, not coverage: a link both sources have, read with different signs.
    # coverage (a link or an item only one side has) is counted on its own, in items, as Roger's limit is.
    link_mismatch = len(conflicts) / len(shared) if shared else None
    item_mismatch = 1 - len(exact_items) / len(both_items) if both_items else None
    reasons = []
    if link_mismatch is not None and link_mismatch > MISMATCH_LIMIT:
        reasons.append(f"{link_mismatch:.1%} of the shared links are keyed with different signs "
                       f"(limit {MISMATCH_LIMIT:.0%})")
    if item_mismatch is not None and item_mismatch > MISMATCH_LIMIT:
        reasons.append(f"{item_mismatch:.1%} of the items both key do not match exactly on instrument, scale and "
                       f"sign (limit {MISMATCH_LIMIT:.0%})")
    if len(items_only_a) > COVERAGE_ITEM_LIMIT:
        reasons.append(f"the workbook keys {len(items_only_a)} items the key pages do not "
                       f"(limit {COVERAGE_ITEM_LIMIT})")
    if len(items_only_b) > COVERAGE_ITEM_LIMIT:
        reasons.append(f"the key pages key {len(items_only_b)} items the workbook does not "
                       f"(limit {COVERAGE_ITEM_LIMIT})")
    return {
        "compared": True, "source_b": SOURCE_B, "source_a": SOURCE_A,
        "n_rows_b": len(b_rows), "n_rows_a": len(a_rows), "n_links_b": len(B), "n_links_a": len(A),
        "n_items_b": len(items_b), "n_items_a": len(items_a),
        "links_only_b": len(only_b), "links_only_a": len(only_a), "n_links_shared": len(shared),
        "items_only_b": len(items_only_b), "items_only_a": len(items_only_a), "n_items_shared": len(both_items),
        "items_only_b_list": items_only_b[:examples], "items_only_a_list": items_only_a[:examples],
        "sign_conflicts": len(conflicts),
        "sign_conflict_list": [{"text": B[k].text, "inventory": k[1], "construct": B[k].construct,
                                "key_pages": B[k].key, "workbook": A[k].key} for k in conflicts[:examples]],
        "link_mismatch_rate": round(link_mismatch, 6) if link_mismatch is not None else None,
        "exact_match_items": len(exact_items),
        "exact_match_rate": round(len(exact_items) / len(both_items), 6) if both_items else None,
        "item_mismatch_rate": round(item_mismatch, 6) if item_mismatch is not None else None,
        "limits": {"mismatch": MISMATCH_LIMIT, "coverage_items": COVERAGE_ITEM_LIMIT},
        "needs_roger": bool(reasons), "reasons": reasons,
        "instruction": ("QUESTIONS 52, Roger 2026-10-11: 'we may find A and B are identical, or very nearly so.  "
                        "If the differences are large, remind me of this and ask if I want to revisit it.'  Report "
                        "these numbers; do not resolve a large difference in code."),
    }


def merge_keys(b_rows: Sequence[KeyRow], a_rows: Optional[Sequence[KeyRow]] = None) -> tuple[list[KeyRow], dict]:
    """``(rows, counts)``: every key page row, plus a workbook row for an (item, inventory, construct) the key
    pages do not key at all (a gap-fill, tagged :data:`SOURCE_A` in the row).  Where both key the same link with
    different signs the key page wins and the row is counted as disputed; no A-only *sign* ever overrides B."""
    B = _by_link(b_rows)
    out = list(B.values())
    counts = {"n_from_key_pages": len(out), "n_gap_filled_from_workbook": 0, "n_disputed": 0,
              "gap_filled_items": 0}
    if a_rows:
        A = _by_link(a_rows)
        fills = [r for k, r in sorted(A.items()) if k not in B]
        out += fills
        counts["n_gap_filled_from_workbook"] = len(fills)
        counts["gap_filled_items"] = len({text_key(r.text) for r in fills})
        counts["n_disputed"] = sum(1 for k, r in A.items() if k in B and B[k].key != r.key)
    counts["n_committed"] = len(out)
    counts["by_source"] = dict(sorted(Counter(r.key_source for r in out).items()))
    return out, counts


# --------------------------------------------------------------------------- the join

def text_key(text: str) -> str:
    """The join key of an item text: lower case, whitespace collapsed, curly quotes straightened, a final full
    stop dropped."""
    s = _clean(text).lower().replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return s[:-1].rstrip() if s.endswith(".") else s


def code_order(code: str) -> tuple[str, int]:
    m = re.match(r"^([A-Z]+)(\d+)$", code)
    return (m.group(1), int(m.group(2))) if m else (code, 0)


@dataclass
class ItemRow:
    schema_version: int
    ipip_id: str            # the first code the item list prints for the item
    codes: list             # every code it prints (an item given in several surveys has several)
    text: str
    scales: list = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: Mapping) -> "ItemRow":
        return cls(schema_version=int(d.get("schema_version") or SCHEMA_VERSION), ipip_id=d["ipip_id"],
                   codes=list(d.get("codes") or [d["ipip_id"]]), text=d["text"],
                   scales=[dict(s) for s in d.get("scales") or []])


def build_items(item_list: Sequence[tuple], keys: Sequence[KeyRow],
                constructs: Sequence[ConstructRow] = ()) -> tuple[list[ItemRow], dict]:
    """``(items, counts)``: every listed item (``(code, text)`` or ``(code, text, codes)``) with its scales
    (deduplicated, sorted by inventory, construct, key); ``counts`` for ``ingest_counts.json`` and the CLI.

    ``keys`` are the committed key rows of :func:`merge_keys`, each carrying ``key_source``; a scale entry of
    ``items.jsonl`` repeats it, so the tracked file says where every sign came from (QUESTIONS 46).  A key row
    whose text matches no listed item is counted and listed, never dropped silently."""
    by_text: dict[str, list[str]] = defaultdict(list)
    texts: dict[str, str] = {}
    all_codes: dict[str, list[str]] = {}
    dup_codes = Counter(c for row in item_list for c in (row[2] if len(row) > 2 else (row[0],)))
    for row in item_list:
        code, text = row[0], row[1]
        texts[code] = text
        all_codes[code] = list(row[2]) if len(row) > 2 else [code]
        by_text[text_key(text)].append(code)
    scales: dict[str, dict] = defaultdict(dict)
    unmatched: list[str] = []
    ambiguous = 0
    for a in keys:
        codes = by_text.get(text_key(a.text))
        if not codes:
            unmatched.append(a.text)
            continue
        if len(codes) > 1:
            ambiguous += 1
        src = getattr(a, "key_source", SOURCE_B)
        for c in codes:
            # a link already held by the key pages is never replaced by the workbook's (B is primary)
            cur = scales[c].get((a.inventory, a.construct, a.key))
            if cur is None or (cur != SOURCE_B and src == SOURCE_B):
                scales[c][(a.inventory, a.construct, a.key)] = src
    items = [ItemRow(schema_version=SCHEMA_VERSION, ipip_id=c, codes=all_codes[c], text=texts[c],
                     scales=[{"inventory": i, "construct": k, "key": s, "key_source": scales[c][(i, k, s)]}
                             for i, k, s in sorted(scales.get(c, {}))])
             for c in sorted(texts, key=code_order)]
    per_inv: dict[str, dict] = {}
    for inv in sorted({s["inventory"] for r in items for s in r.scales}):
        its = [r for r in items if any(s["inventory"] == inv for s in r.scales)]
        cons = {s["construct"] for r in items for s in r.scales if s["inventory"] == inv}
        per_inv[inv] = {"items": len(its), "constructs": len(cons)}
    hex_cons = sorted({s["construct"] for r in items for s in r.scales if s["inventory"] == "HEX"})
    counts = {
        "n_items": len(items), "n_codes": sum(len(r.codes) for r in items),
        "n_multi_code": sum(1 for r in items if len(r.codes) > 1),
        "n_with_scales": sum(1 for r in items if r.scales),
        "n_multi_scale": sum(1 for r in items if len(r.scales) > 1),
        "n_keyed_minus": sum(1 for r in items if any(s["key"] == "-" for s in r.scales)),
        "n_scale_links": sum(len(r.scales) for r in items),
        "n_assignment_rows": len(keys), "unmatched_assignments": len(unmatched),
        "unmatched_list": sorted(set(unmatched)), "ambiguous_text_joins": ambiguous,
        "duplicate_codes": sorted(c for c, n in dup_codes.items() if n > 1),
        "per_inventory": per_inv,
        "n_constructs": len({(s["inventory"], s["construct"]) for r in items for s in r.scales}),
        "hex": {"constructs": len(hex_cons), "items": per_inv.get("HEX", {}).get("items", 0),
                "construct_list": hex_cons},
        "scale_index": {"n_links": len(constructs), "n_labels": len({c.label for c in constructs}),
                        "inventories": dict(sorted(Counter(c.inventory for c in constructs).items()))},
        "key_sources": dict(sorted(Counter(s["key_source"] for r in items for s in r.scales).items())),
        "n_items_with_a_only_key": sum(1 for r in items if r.scales
                                       and all(s["key_source"] == SOURCE_A for s in r.scales)),
    }
    return items, counts


def check_hex(counts: Mapping, *, min_constructs: int = HEX_MIN_CONSTRUCTS,
              item_range: tuple[int, int] = HEX_ITEM_RANGE) -> None:
    """Plan § 7's assertion on the HEX block, kept permanently as a scrape-completeness check (QUESTIONS 49,
    Roger 2026-10-11: a clear error, never a silent pass -- the failure it really guards against is a silently
    short scrape, as ``ItemAssignmentTable.htm`` turning out to be 3,759 bytes of prose already showed).
    :class:`HexAssertionError` says what to look at."""
    h = counts.get("hex") or {}
    n_c, n_i = int(h.get("constructs") or 0), int(h.get("items") or 0)
    if n_c >= min_constructs and item_range[0] <= n_i <= item_range[1]:
        return
    raise HexAssertionError(
        f"HEX block: {n_c} constructs and {n_i} items, expected at least {min_constructs} constructs and "
        f"{item_range[0]}-{item_range[1]} items (plan 07 § 2).  This is a scrape-completeness check "
        f"(QUESTIONS 49): newHEXACO_PI_key.htm is one of the 21 key pages on the main path (31 HEX links across "
        f"the 274 constructs), so a failure means a short or mis-decoded scrape rather than a missing fallback.  "
        f"Look at ingest_counts.json's `key_pages.per_page` for the page's row count, check that the page was "
        f"fetched whole (`download --only key_hexaco --force`), and remember these pages are iso-8859-1")


def build_from_dir(external: Path = EXTERNAL_DIR, *, require_workbook: bool = False) -> tuple[list[ItemRow], dict]:
    """Read the inputs as ``download`` lays them out under ``external`` and join them: the item list, the scale
    index, the 21 key pages (source B, primary) and, when it is there, the assignment workbook (source A, a check
    and a gap-filler).  The workbook's absence is recorded, not fatal, unless ``require_workbook``; a missing or
    empty key page is fatal (:func:`check_key_pages`, called by the CLI on the counts this returns)."""
    external = Path(external)
    paths = {k: external / SOURCES[k].dest for k in ("item_list", "scale_index", WORKBOOK_KEY)}
    for k in ("item_list", "scale_index"):
        if not paths[k].exists():
            raise FileNotFoundError(f"missing {paths[k]}: run `ipip_generator.py download` first")
    item_list = parse_item_list(paths["item_list"].read_bytes())
    constructs = parse_scale_index(paths["scale_index"].read_bytes())
    known = {text_key(r[1]) for r in item_list}
    b_rows, key_counts = parse_key_pages(external, constructs=constructs, known_texts=known)
    wb = paths[WORKBOOK_KEY]
    if not wb.exists():
        if require_workbook:
            raise FileNotFoundError(
                f"missing {wb}: Tedone's workbook is source A, the check on the key pages (QUESTIONS 52, option "
                f"C, approved 2026-10-11); fetch it with `ipip_generator.py download --only {WORKBOOK_KEY}`")
        a_rows, assignments = None, []
    else:
        assignments = parse_assignment_table(wb.read_bytes())
        a_rows = assignment_key_rows(assignments)
    comparison = compare_keys(b_rows, a_rows)
    committed, merge_counts = merge_keys(b_rows, a_rows)
    items, counts = build_items(item_list, committed, constructs)
    counts["key_pages"] = key_counts
    counts["key_comparison"] = comparison
    counts["key_merge"] = merge_counts
    counts["workbook"] = ({"file": wb.name, "sha256": file_sha256(wb), "n_rows": len(assignments),
                           "instrument_names": dict(sorted(Counter(a.instrument for a in assignments).items()))}
                          if wb.exists() else None)
    counts["inputs"] = {k: {"file": p.name, "sha256": file_sha256(p)} for k, p in paths.items() if p.exists()}
    return items, counts


# --------------------------------------------------------------------------- the file

def items_text(items: Sequence[ItemRow]) -> str:
    import json
    return "".join(json.dumps(r.to_json(), ensure_ascii=False) + "\n" for r in items)


def write_items(items: Sequence[ItemRow], path: Path = ITEMS_PATH) -> Optional[Path]:
    """Write ``items.jsonl``; when its content changes, the old file is first copied to ``<path>.bak.<UTC>``.
    Returns the backup's path, if one was made."""
    path = Path(path)
    body = items_text(items)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_items(path: Path = ITEMS_PATH) -> list[ItemRow]:
    import json
    with open(path, encoding="utf-8") as fh:
        return [ItemRow.from_json(json.loads(x)) for x in fh if x.strip()]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def items_by_id(items: Iterable[ItemRow]) -> dict[str, ItemRow]:
    return {r.ipip_id: r for r in items}
