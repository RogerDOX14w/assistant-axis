"""Parse the IPIP pages and the item assignment workbook into ``items.jsonl``.

* :func:`parse_item_list`: ``AlphabeticalItemList.htm`` -> ``[(code, text)]``, one per Eugene-Springfield code
  (3,320 on the real page), the cell's text with its whitespace collapsed.
* :func:`parse_scale_index`: ``newIndexofScaleLabels.htm`` -> :class:`ConstructRow` per link (construct label,
  inventory abbreviation, scale code, the key page it links to).  Used to name inventories and to list the
  constructs; the item keys are not on this page.
* :func:`parse_assignment_table`: the item assignment workbook (QUESTIONS 52: the table is Tedone's Excel
  workbook, not the HTML page the plan named) -> :class:`AssignmentRow` per (item text, scale), read with the
  standard library (:func:`read_xlsx_rows`: an ``.xlsx`` is a zip of XML parts), by its documented columns
  (instrument, alpha, key, text, label; found by header, wherever the header row sits).
* :func:`build_items`: the join, by item text (:func:`text_key`: case, whitespace, curly quotes and the final
  full stop do not count); an assignment whose text is in no item list is counted and listed, never dropped
  silently.  Every item of the list is kept, with ``scales: []`` when no scale scores it.

``items.jsonl`` is deterministic (rows in code order: the letter, then the number; scales sorted), so a rerun on
the same inputs writes the same bytes; :func:`write_items` copies the old file to ``.bak.<UTC>`` before it changes
(snapshot before overwrite).  :func:`check_hex` is plan § 7's assertion: at least 20 constructs keyed ``HEX``
with about 240 items (the IPIP-HEXACO block, plan 07 § 2).
"""
from __future__ import annotations

import hashlib
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
from .sources import SOURCES

SCHEMA_VERSION = 1
CODE_RE = re.compile(r"^[A-Z]\d+$")
#: plan § 7: at least 20 constructs keyed HEX, with about 240 items (24 facets x 10).
HEX_MIN_CONSTRUCTS = 20
HEX_ITEM_RANGE = (200, 300)
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


# --------------------------------------------------------------------------- the pages

def _soup(html: bytes | str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser")


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


def build_items(item_list: Sequence[tuple], assignments: Sequence[AssignmentRow],
                constructs: Sequence[ConstructRow] = ()) -> tuple[list[ItemRow], dict]:
    """``(items, counts)``: every listed item (``(code, text)`` or ``(code, text, codes)``) with its scales
    (deduplicated, sorted by inventory, construct, key); ``counts`` for ``ingest_counts.json`` and the CLI."""
    by_text: dict[str, list[str]] = defaultdict(list)
    texts: dict[str, str] = {}
    all_codes: dict[str, list[str]] = {}
    dup_codes = Counter(c for row in item_list for c in (row[2] if len(row) > 2 else (row[0],)))
    for row in item_list:
        code, text = row[0], row[1]
        texts[code] = text
        all_codes[code] = list(row[2]) if len(row) > 2 else [code]
        by_text[text_key(text)].append(code)
    scales: dict[str, set] = defaultdict(set)
    unmatched: list[str] = []
    ambiguous = 0
    for a in assignments:
        codes = by_text.get(text_key(a.text))
        if not codes:
            unmatched.append(a.text)
            continue
        if len(codes) > 1:
            ambiguous += 1
        for c in codes:
            scales[c].add((a.inventory, a.construct, a.key))
    items = [ItemRow(schema_version=SCHEMA_VERSION, ipip_id=c, codes=all_codes[c], text=texts[c],
                     scales=[{"inventory": i, "construct": k, "key": s} for i, k, s in sorted(scales.get(c, ()))])
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
        "n_assignment_rows": len(assignments), "unmatched_assignments": len(unmatched),
        "unmatched_list": sorted(set(unmatched)), "ambiguous_text_joins": ambiguous,
        "duplicate_codes": sorted(c for c, n in dup_codes.items() if n > 1),
        "per_inventory": per_inv,
        "n_constructs": len({(s["inventory"], s["construct"]) for r in items for s in r.scales}),
        "hex": {"constructs": len(hex_cons), "items": per_inv.get("HEX", {}).get("items", 0),
                "construct_list": hex_cons},
        "scale_index": {"n_links": len(constructs), "n_labels": len({c.label for c in constructs}),
                        "inventories": dict(sorted(Counter(c.inventory for c in constructs).items()))},
        "instrument_names": dict(sorted(Counter(a.instrument for a in assignments).items())),
    }
    return items, counts


def check_hex(counts: Mapping, *, min_constructs: int = HEX_MIN_CONSTRUCTS,
              item_range: tuple[int, int] = HEX_ITEM_RANGE) -> None:
    """Plan § 7's assertion on the HEX block; :class:`HexAssertionError` names the fallback when it fails."""
    h = counts.get("hex") or {}
    n_c, n_i = int(h.get("constructs") or 0), int(h.get("items") or 0)
    if n_c >= min_constructs and item_range[0] <= n_i <= item_range[1]:
        return
    raise HexAssertionError(
        f"HEX block: {n_c} constructs and {n_i} items, expected at least {min_constructs} constructs and "
        f"{item_range[0]}-{item_range[1]} items (plan 07 § 2).  Fallback (QUESTIONS 49, under the 2026-10-10 "
        f"approval): `ipip_generator.py download --only hexaco_key`, then ingest again")


def build_from_dir(external: Path = EXTERNAL_DIR) -> tuple[list[ItemRow], dict]:
    """Read the three inputs as ``download`` lays them out under ``external`` and join them."""
    external = Path(external)
    paths = {k: external / SOURCES[k].dest for k in ("item_list", "scale_index", "assignment_workbook")}
    for k in ("item_list", "scale_index"):
        if not paths[k].exists():
            raise FileNotFoundError(f"missing {paths[k]}: run `ipip_generator.py download` first")
    if not paths["assignment_workbook"].exists():
        raise FileNotFoundError(
            f"missing {paths['assignment_workbook']}: the item-to-scale table is Tedone's workbook, which needs "
            f"Roger's go before it is fetched (QUESTIONS 52); then `ipip_generator.py download --only "
            f"assignment_workbook --approved-by '<Roger, date>'`")
    item_list = parse_item_list(paths["item_list"].read_bytes())
    constructs = parse_scale_index(paths["scale_index"].read_bytes())
    assignments = parse_assignment_table(paths["assignment_workbook"].read_bytes())
    items, counts = build_items(item_list, assignments, constructs)
    counts["inputs"] = {k: {"file": p.name, "sha256": file_sha256(p)} for k, p in paths.items()}
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
