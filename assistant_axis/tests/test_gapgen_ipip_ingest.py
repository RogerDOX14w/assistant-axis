"""IPIP generator, ingest: the fixture pages (12 items, one on two scales, three keyed -1, one HEX construct)
and a synthetic assignment workbook built with the standard library."""
import json

import pytest

from assistant_axis.gapgen.generators.ipip import ingest as I
from assistant_axis.gapgen.generators.ipip.sources import SOURCES
from assistant_axis.tests.ipip_fakes import ASSIGNMENT_ROWS, FIXTURES, fixture_pages, fixture_workbook, write_xlsx


def test_parse_item_list():
    items = I.parse_item_list((FIXTURES / "item_list.htm").read_bytes())
    assert len(items) == 12
    assert ("H1", "Get chores done right away.", ("H1",)) in items    # the line break inside the cell is collapsed
    # one item printed with three survey codes: one row, the first code its id, all three kept
    assert ("W11", "Am always prepared.", ("W11", "H99", "T200")) in items
    assert ("Y12", "Keep my promises.", ("Y12",)) in items              # a footnote asterisk ("Y12 *") dropped
    assert all(I.CODE_RE.match(c) for row in items for c in row[2])


def test_parse_scale_index():
    rows = I.parse_scale_index((FIXTURES / "scale_index.htm").read_bytes())
    by = {(r.label, r.inventory): r for r in rows}
    assert by[("Orderliness", "NEO")].scale == "C2" and by[("Orderliness", "HEX")].scale == "C-Orga"
    assert by[("Anxiety", "CAT-PD")].scale == "Anxiousness"
    assert by[("Diligence", "HEX")].href == "newHEXACO_PI_key.htm#Diligence"
    assert by[("Extraversion", "NEO")].scale == "Domain"                     # "NEO Domain", no colon
    assert {r.label for r in rows} == {"Anxiety", "Diligence", "Friendliness", "Integrity/Honesty/Authenticity",
                                       "Orderliness", "Extraversion"}


def test_read_workbook_rows(tmp_path):
    p = fixture_workbook(tmp_path / "wb.xlsx", title_rows=2)
    table = I.read_xlsx_rows(p.read_bytes())
    assert table[2] == ["instrument", "alpha", "key", "text", "label"]
    rows = I.parse_assignment_table(p.read_bytes())
    assert len(rows) == len(ASSIGNMENT_ROWS)
    r = rows[2]
    assert (r.instrument, r.key, r.text, r.construct) == ("NEO", "-", "Leave a mess in my room.", "Orderliness")
    assert rows[1].inventory == "HEX" and rows[0].inventory == "NEO"


def test_workbook_without_the_columns_is_refused(tmp_path):
    p = write_xlsx([("a", "b"), (1, 2)], tmp_path / "bad.xlsx")
    with pytest.raises(ValueError, match="header"):
        I.parse_assignment_table(p.read_bytes())


def test_bad_key_is_refused(tmp_path):
    p = fixture_workbook(tmp_path / "wb.xlsx", rows=[("NEO", 0.8, 2, "Like to tidy up.", "Orderliness")])
    with pytest.raises(ValueError, match="key"):
        I.parse_assignment_table(p.read_bytes())


def build(tmp_path, rows=ASSIGNMENT_ROWS):
    d = fixture_pages(tmp_path / "ext", rows=rows)
    return I.build_from_dir(d)


def test_build_items_counts_and_joins(tmp_path):
    items, counts = build(tmp_path)
    assert len(items) == 12 and counts["n_items"] == 12
    by = {r.ipip_id: r for r in items}
    # the multi-scale item keeps both, in a deterministic order
    assert by["H1"].scales == [{"inventory": "HEX", "construct": "Diligence", "key": "+"},
                               {"inventory": "NEO", "construct": "Orderliness", "key": "+"}]
    assert by["H2"].scales == [{"inventory": "NEO", "construct": "Orderliness", "key": "-"}]
    assert by["W11"].scales == [] and by["W11"].codes == ["W11", "H99", "T200"] and by["H1"].codes == ["H1"]
    assert counts["n_with_scales"] == 11 and counts["n_multi_scale"] == 1 and counts["n_multi_code"] == 1
    assert counts["n_codes"] == 14
    assert counts["n_keyed_minus"] == 3
    assert counts["unmatched_assignments"] == 1 and counts["unmatched_list"] == ["An item that is in no list."]
    assert counts["per_inventory"]["NEO"] == {"items": 9, "constructs": 3}
    assert counts["per_inventory"]["HEX"] == {"items": 1, "constructs": 1}
    assert counts["hex"] == {"constructs": 1, "items": 1, "construct_list": ["Diligence"]}
    # items come out in code order: letter, then number
    assert [r.ipip_id for r in items] == ["E5", "E6", "H1", "H2", "H3", "H4", "P8", "P9", "T10", "W11", "X7", "Y12"]


def test_item_row_schema(tmp_path):
    items, _ = build(tmp_path)
    d = items[0].to_json()
    assert list(d) == ["schema_version", "ipip_id", "codes", "text", "scales"] and d["schema_version"] == 1


def test_rerun_is_byte_identical_and_snapshots_on_change(tmp_path):
    items, _ = build(tmp_path)
    out = tmp_path / "ipip" / "items.jsonl"
    assert I.write_items(items, out) is None
    first = out.read_bytes()
    items2, _ = build(tmp_path)
    assert I.write_items(items2, out) is None and out.read_bytes() == first
    assert not list(out.parent.glob("items.jsonl.bak.*"))
    assert [r.to_json() for r in I.load_items(out)] == [r.to_json() for r in items]
    changed = [r for r in ASSIGNMENT_ROWS if r[3] != "Keep my promises."]
    items3, _ = build(tmp_path / "b", rows=changed)
    backup = I.write_items(items3, out)
    assert backup is not None and backup.read_bytes() == first
    assert json.loads(out.read_text().splitlines()[-1])["scales"] == []        # Y12 lost its scale


def test_hex_assertion(tmp_path):
    items, counts = build(tmp_path)
    I.check_hex(counts, min_constructs=1, item_range=(1, 5))                    # one HEX construct: passes
    with pytest.raises(I.HexAssertionError):
        I.check_hex(counts)                                                      # the real bar: 20 constructs
    no_hex = [r for r in ASSIGNMENT_ROWS if r[0] != "HEXACO"]
    _, counts2 = build(tmp_path / "nohex", rows=no_hex)
    assert counts2["hex"]["constructs"] == 0
    with pytest.raises(I.HexAssertionError, match="hexaco_key"):
        I.check_hex(counts2, min_constructs=1, item_range=(1, 5))


def test_missing_workbook_names_the_question(tmp_path):
    d = fixture_pages(tmp_path / "ext")
    (d / SOURCES["assignment_workbook"].dest).unlink()
    with pytest.raises(FileNotFoundError, match="QUESTIONS 52"):
        I.build_from_dir(d)


def test_text_key_normalisation():
    assert I.text_key("Don’t  like to\ndraw attention to myself.") == I.text_key("don't like to draw attention to myself")
