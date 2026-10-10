"""Shared fixtures for the IPIP generator's tests (no network, no model, no API)."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ipip"

#: The synthetic item assignment workbook: the documented columns of Tedone's table (instrument, alpha, key,
#: text, label), one row per (item, scale).  "Get chores done right away." is on two scales, three items are
#: keyed -1, Diligence is the one HEX construct, and the last row's text is in no item list (unmatched).
ASSIGNMENT_HEADER = ("instrument", "alpha", "key", "text", "label")
ASSIGNMENT_ROWS: tuple[tuple, ...] = (
    ("NEO", 0.82, 1, "Get chores done right away.", "Orderliness"),
    ("HEXACO", 0.80, 1, "Get chores done right away.", "Diligence"),
    ("NEO", 0.82, -1, "Leave a mess in my room.", "Orderliness"),
    ("NEO", 0.82, 1, "Love order and regularity.", "Orderliness"),
    ("NEO", 0.82, 1, "Like to tidy up.", "Orderliness"),
    ("NEO", 0.87, 1, "Talk to a lot of different people at parties.", "Friendliness"),
    ("NEO", 0.87, -1, "Keep in the background.", "Friendliness"),
    ("NEO", 0.87, 1, "Make friends easily.", "Friendliness"),
    ("NEO", 0.83, 1, "Worry about things.", "Anxiety"),
    ("NEO", 0.83, -1, "Am relaxed most of the time.", "Anxiety"),
    ("CAT-PD", 0.90, 1, "Fear for the worst.", "Anxiety"),
    ("VIA", 0.78, 1, "Keep my promises.", "Integrity/Honesty/Authenticity"),
    ("NEO", 0.80, 1, "An item that is in no list.", "Orderliness"),
)


def _col(i: int) -> str:
    s = ""
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def write_xlsx(rows: Sequence[Sequence], path: Path, *, sheet_name: str = "Sheet1") -> Path:
    """A minimal .xlsx (one sheet, shared strings for text cells, numbers as numbers), as Excel lays it out."""
    shared: list[str] = []
    index: dict[str, int] = {}
    body = []
    for r, row in enumerate(rows, 1):
        cells = []
        for c, v in enumerate(row):
            ref = f"{_col(c)}{r}"
            if v is None:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                cells.append(f'<c r="{ref}"><v>{v}</v></c>')
            else:
                s = str(v)
                if s not in index:
                    index[s] = len(shared)
                    shared.append(s)
                cells.append(f'<c r="{ref}" t="s"><v>{index[s]}</v></c>')
        body.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel_ns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    sheet = f'<?xml version="1.0" encoding="UTF-8"?><worksheet {ns}><sheetData>{"".join(body)}</sheetData></worksheet>'
    sst = (f'<?xml version="1.0" encoding="UTF-8"?><sst {ns} count="{len(shared)}" uniqueCount="{len(shared)}">'
           + "".join(f"<si><t>{escape(s)}</t></si>" for s in shared) + "</sst>")
    workbook = (f'<?xml version="1.0" encoding="UTF-8"?><workbook {ns} {rel_ns}><sheets>'
                f'<sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets></workbook>')
    wb_rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships '
               'xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
               '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
               'worksheet" Target="worksheets/sheet1.xml"/>'
               '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
               'sharedStrings" Target="sharedStrings.xml"/></Relationships>')
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types '
                   'xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        z.writestr("xl/sharedStrings.xml", sst)
    return path


def fixture_workbook(path: Path, rows: Iterable[tuple] = ASSIGNMENT_ROWS, *, title_rows: int = 0) -> Path:
    """The synthetic assignment workbook at ``path`` (``title_rows`` blank-ish rows above the header)."""
    lead = [("Item assignment table",)] * title_rows
    return write_xlsx([*lead, ASSIGNMENT_HEADER, *rows], path)


def fixture_pages(dest: Path, *, rows: Iterable[tuple] = ASSIGNMENT_ROWS) -> Path:
    """The three inputs of ``ingest`` laid out as ``download`` lays them out (pages under their file names, the
    workbook under its own), in ``dest``."""
    from assistant_axis.gapgen.generators.ipip.sources import SOURCES
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / SOURCES["item_list"].dest).write_bytes((FIXTURES / "item_list.htm").read_bytes())
    (dest / SOURCES["scale_index"].dest).write_bytes((FIXTURES / "scale_index.htm").read_bytes())
    fixture_workbook(dest / SOURCES["assignment_workbook"].dest, rows)
    return dest


def make_corpus(root: Path, traits: dict | None = None, queue: Sequence[dict] = ()) -> Path:
    """A data dir with trait files (stem -> (label, description)) and a seed queue."""
    traits = traits if traits is not None else {
        "orderly": ("orderly", "This means keeping things tidy and in their place."),
        "anxious": ("anxious", "This means worrying about what might go wrong."),
        "sociable": ("sociable", "This means seeking out company and talking easily to people."),
        "diligent_hexaco": ("diligent (HEXACO)", "This means working hard and steadily toward goals."),
    }
    d = Path(root) / "data"
    (d / "traits" / "instructions").mkdir(parents=True, exist_ok=True)
    for stem, (label, desc) in traits.items():
        (d / "traits" / "instructions" / f"{stem}.json").write_text(json.dumps(
            {"positive_label": label, "negative_label": f"non-{label}", "description": desc}))
    (d / "seed_queue.json").write_text(json.dumps({"entries": list(queue)}))
    return d
