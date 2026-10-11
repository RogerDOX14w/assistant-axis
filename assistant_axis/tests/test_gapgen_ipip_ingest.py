"""IPIP generator, ingest: the fixture pages (12 items), synthetic key pages (source B, QUESTIONS 52) and a
synthetic assignment workbook (source A), all offline."""
import json

import pytest

from assistant_axis.gapgen.generators.ipip import ingest as I
from assistant_axis.gapgen.generators.ipip.sources import KEY_PAGE_FILES, SOURCES, WORKBOOK_KEY
from assistant_axis.tests.ipip_fakes import (ASSIGNMENT_ROWS, FIXTURES, KEY_PAGE_ROWS, fixture_pages,
                                             fixture_workbook, write_key_page, write_xlsx)


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
    pages = I.constructs_by_page(rows)
    assert set(pages) == {"newNEOKey.htm", "newCAT-PD-SFv1.1Keys.htm", "newHEXACO_PI_key.htm", "newVIAKey.htm"}
    assert {c.label for c in pages["newNEOKey.htm"]} == {"Anxiety", "Friendliness", "Orderliness", "Extraversion"}


# --------------------------------------------------------------------------- decoding (QUESTIONS 49)

def test_pages_are_decoded_explicitly_not_as_utf8():
    """The real pages carry cp1252 bytes (0x92 a right single quote, 0x96 an en dash) that are not valid utf-8
    and that iso-8859-1 would turn into control characters; a silent mis-decode is what QUESTIONS 49 guards
    against."""
    raw = b"<p>Act as if I\x92m somebody else.</p><p>MPQ\x96276</p>"
    assert I.PAGE_ENCODING == "cp1252"
    text = I.decode_page(raw)
    assert "I’m somebody else" in text and "MPQ–276" in text
    assert I.decode_page(text) is text                                   # a str passes through
    with pytest.raises(UnicodeDecodeError):
        raw.decode("utf-8")
    assert I.text_key("Act as if I’m somebody else.") == I.text_key("act as if i'm somebody else")


def test_page_lines_splits_on_block_tags_and_resolves_entities():
    html = (b"<html><head><style>p{}</style></head><body><b>N1: ANXIETY</b>&nbsp;(.83)<br>"
            b"+ keyed&nbsp;&nbsp;Worry about things.<br>&nbsp;&nbsp;Fear for the worst.<br></body></html>")
    assert I.page_lines(html) == ["N1: ANXIETY (.83)", "+ keyed Worry about things.", "Fear for the worst."]


# --------------------------------------------------------------------------- the key pages (source B)

KNOWN = {I.text_key(t) for t in ("Worry about things.", "Am relaxed most of the time.", "Fear for the worst.",
                                 "Get chores done right away.", "Love order and regularity.", "Like to tidy up.",
                                 "Leave a mess in my room.", "Keep in the background.", "Make friends easily.",
                                 "Talk to a lot of different people at parties.", "Keep my promises.",
                                 "Am always prepared.")}


def constructs_for(page):
    rows = I.parse_scale_index((FIXTURES / "scale_index.htm").read_bytes())
    return I.constructs_by_page(rows).get(page, ())


def test_parse_key_page_reads_signs_and_constructs(tmp_path):
    p = write_key_page(KEY_PAGE_ROWS["newNEOKey.htm"], tmp_path / "newNEOKey.htm")
    rows, counts = I.parse_key_page(p.read_bytes(), constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    got = {(r.construct, r.key, r.text) for r in rows}
    assert ("Anxiety", "+", "Worry about things.") in got
    assert ("Anxiety", "-", "Am relaxed most of the time.") in got         # the sign carries to the next line
    assert ("Friendliness", "-", "Keep in the background.") in got
    assert ("Orderliness", "+", "Like to tidy up.") in got                 # a continuation line under "+ keyed"
    assert all(r.inventory == "NEO" and r.key_source == I.SOURCE_B for r in rows)
    assert {r.scale for r in rows} == {"N1", "E1", "C2"}
    assert counts["n_rows"] == 9 and counts["n_constructs"] == 3 and counts["n_keyed_minus"] == 3
    assert counts["unmatched_items"] == 0 and counts["unlisted_constructs"] == []


def test_a_key_page_heading_is_matched_through_the_index_href(tmp_path):
    """A key page prints the inventory's own scale name ("Organization"), which the index reaches only as the
    href fragment; the row still records the index's label and inventory, so the sources join on one name."""
    p = write_key_page(KEY_PAGE_ROWS["newHEXACO_PI_key.htm"], tmp_path / "newHEXACO_PI_key.htm")
    rows, _ = I.parse_key_page(p.read_bytes(), constructs=constructs_for("newHEXACO_PI_key.htm"),
                               known_texts=KNOWN, page="newHEXACO_PI_key.htm")
    assert {(r.inventory, r.construct, r.text) for r in rows} == {
        ("HEX", "Diligence", "Get chores done right away."), ("HEX", "Orderliness", "Like to tidy up.")}


def test_a_construct_the_index_does_not_list_keeps_its_heading(tmp_path):
    p = write_key_page(KEY_PAGE_ROWS["new16PFKey.htm"], tmp_path / "new16PFKey.htm")
    rows, counts = I.parse_key_page(p.read_bytes(), constructs=(), known_texts=KNOWN, page="new16PFKey.htm")
    assert [(r.inventory, r.construct, r.key) for r in rows] == [("16PF", "Self-Reliance", "+")]
    assert counts["unlisted_constructs"] == ["Self-Reliance"]               # the alpha is stripped
    assert I.inventory_from_page("new16PFKey.htm") == "16PF"
    assert I.inventory_from_page("BFASKeys.htm") == "BFAS"


def test_an_unmatched_line_does_not_steal_the_construct(tmp_path):
    """The real risk of a line-based parser: one item text the list does not hold must not be read as a heading
    and take the construct away from the items under it."""
    blocks = (("C2: ORDERLINESS", "(.82)", (("+", "Get chores done right away."),
                                            ("+", "An item that is in no list."),
                                            ("+", "Love order and regularity."))),)
    p = write_key_page(blocks, tmp_path / "newNEOKey.htm")
    rows, counts = I.parse_key_page(p.read_bytes(), constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert [r.text for r in rows] == ["Get chores done right away.", "Love order and regularity."]
    assert all(r.construct == "Orderliness" for r in rows)
    assert counts["unmatched_items"] == 1 and counts["unmatched_list"] == ["An item that is in no list."]


def test_parse_key_pages_counts_missing_and_empty(tmp_path):
    ext = fixture_pages(tmp_path / "ext")                                   # only the five described pages
    constructs = I.parse_scale_index((ext / SOURCES["scale_index"].dest).read_bytes())
    rows, counts = I.parse_key_pages(ext, constructs=constructs, known_texts=KNOWN)
    assert counts["n_pages_expected"] == 21 and counts["n_pages_read"] == 5
    assert len(counts["missing"]) == 16 and counts["empty"] == []
    assert counts["n_rows"] == len(rows) == 14
    with pytest.raises(I.KeyPageError, match="not on disk"):
        I.check_key_pages({"key_pages": counts})
    # a page on disk that parses to nothing is the other scrape failure
    write_key_page((("Nothing here", "", ()),), ext / KEY_PAGE_FILES["key_hpi"])
    _rows, counts2 = I.parse_key_pages(ext, constructs=constructs, known_texts=KNOWN)
    assert counts2["empty"] == ["newHPIKeys.htm"]
    with pytest.raises(I.KeyPageError, match="parsed to no rows"):
        I.check_key_pages({"key_pages": counts2})


def test_check_key_pages_passes_on_all_21(tmp_path):
    ext = fixture_pages(tmp_path / "ext", all_21=True)
    _items, counts = I.build_from_dir(ext)
    assert counts["key_pages"]["n_pages_read"] == 21 and not counts["key_pages"]["empty"]
    I.check_key_pages(counts)


# --------------------------------------------------------------------------- the workbook (source A)

def test_read_workbook_rows(tmp_path):
    p = fixture_workbook(tmp_path / "wb.xlsx", title_rows=2)
    table = I.read_xlsx_rows(p.read_bytes())
    assert table[2] == ["instrument", "alpha", "key", "text", "label"]
    rows = I.parse_assignment_table(p.read_bytes())
    assert len(rows) == len(ASSIGNMENT_ROWS)
    r = rows[2]
    assert (r.instrument, r.key, r.text, r.construct) == ("NEO", "-", "Leave a mess in my room.", "Orderliness")
    assert rows[1].inventory == "HEX" and rows[0].inventory == "NEO"
    key_rows = I.assignment_key_rows(rows)
    assert all(k.key_source == I.SOURCE_A and k.page.endswith(".xlsx") for k in key_rows)


def test_workbook_without_the_columns_is_refused(tmp_path):
    p = write_xlsx([("a", "b"), (1, 2)], tmp_path / "bad.xlsx")
    with pytest.raises(ValueError, match="header"):
        I.parse_assignment_table(p.read_bytes())


def test_bad_key_is_refused(tmp_path):
    p = fixture_workbook(tmp_path / "wb.xlsx", rows=[("NEO", 0.8, 2, "Like to tidy up.", "Orderliness")])
    with pytest.raises(ValueError, match="key"):
        I.parse_assignment_table(p.read_bytes())


# --------------------------------------------------------------------------- A against B (QUESTIONS 52)

def krow(text, inv, construct, key, source=I.SOURCE_B):
    return I.KeyRow(inventory=inv, construct=construct, key=key, text=text, key_source=source)


B_ROWS = [krow("Get chores done right away.", "NEO", "Orderliness", "+"),
          krow("Leave a mess in my room.", "NEO", "Orderliness", "-"),
          krow("Keep my promises.", "VIA", "Integrity", "+")]


def a_rows(rows):
    return [krow(r.text, r.inventory, r.construct, r.key, I.SOURCE_A) for r in rows]


def test_compare_keys_identical_sources_need_nothing_from_roger():
    c = I.compare_keys(B_ROWS, a_rows(B_ROWS))
    assert c["compared"] and c["needs_roger"] is False and c["reasons"] == []
    assert c["n_links_b"] == c["n_links_a"] == 3 and c["n_links_shared"] == 3
    assert c["links_only_a"] == c["links_only_b"] == 0 and c["sign_conflicts"] == 0
    assert c["exact_match_rate"] == 1.0 and c["item_mismatch_rate"] == 0.0
    assert c["limits"] == {"mismatch": I.MISMATCH_LIMIT, "coverage_items": I.COVERAGE_ITEM_LIMIT}


def test_compare_keys_reports_a_sign_conflict_and_asks_roger():
    a = a_rows(B_ROWS)
    a[1] = krow("Leave a mess in my room.", "NEO", "Orderliness", "+", I.SOURCE_A)
    c = I.compare_keys(B_ROWS, a)
    assert c["sign_conflicts"] == 1 and c["sign_conflict_list"][0]["key_pages"] == "-"
    assert c["sign_conflict_list"][0]["workbook"] == "+"
    assert c["exact_match_items"] == 2 and c["n_items_shared"] == 3
    assert c["link_mismatch_rate"] == pytest.approx(1 / 3)
    assert c["needs_roger"] is True and any("different signs" in r for r in c["reasons"])
    assert "QUESTIONS 52" in c["instruction"]


def test_compare_keys_coverage_limit_is_in_items():
    """Roger's limit is 50 items either way; 60 items only A keys trips it, 3 do not."""
    extra = [krow(f"Item number {i}.", "HPI", "Filler", "+", I.SOURCE_A) for i in range(60)]
    c = I.compare_keys(B_ROWS, a_rows(B_ROWS) + extra)
    assert c["items_only_a"] == 60 and c["needs_roger"] is True
    assert any("the workbook keys 60 items" in r for r in c["reasons"])
    small = I.compare_keys(B_ROWS, a_rows(B_ROWS) + extra[:3])
    assert small["items_only_a"] == 3 and small["needs_roger"] is False


def test_compare_keys_without_the_workbook():
    c = I.compare_keys(B_ROWS, None)
    assert c["compared"] is False and c["needs_roger"] is False and "not on disk" in c["reason"]


def test_merge_keys_commits_b_and_tags_an_a_only_key():
    gap = krow("Fear for the worst.", "CAT-PD", "Anxiety", "+", I.SOURCE_A)
    conflict = krow("Leave a mess in my room.", "NEO", "Orderliness", "+", I.SOURCE_A)
    a = [r for r in a_rows(B_ROWS) if not r.text.startswith("Leave a mess")] + [gap, conflict]
    rows, counts = I.merge_keys(B_ROWS, a)
    assert counts["n_from_key_pages"] == 3 and counts["n_gap_filled_from_workbook"] == 1
    assert counts["n_disputed"] == 1 and counts["n_committed"] == 4
    assert counts["by_source"] == {I.SOURCE_B: 3, I.SOURCE_A: 1}
    # B wins the disputed link: the "-" sign the key page gives is the one committed
    mess = [r for r in rows if r.text.startswith("Leave a mess")]
    assert [(r.key, r.key_source) for r in mess] == [("-", I.SOURCE_B)]
    assert [(r.text, r.key_source) for r in rows if r.key_source == I.SOURCE_A] == [
        ("Fear for the worst.", I.SOURCE_A)]


# --------------------------------------------------------------------------- the join and the file

def build(tmp_path, rows=ASSIGNMENT_ROWS, **kw):
    d = fixture_pages(tmp_path / "ext", rows=rows, **kw)
    return I.build_from_dir(d)


def test_build_items_counts_and_joins(tmp_path):
    items, counts = build(tmp_path)
    assert len(items) == 12 and counts["n_items"] == 12
    by = {r.ipip_id: r for r in items}
    # the multi-scale item keeps both, in a deterministic order, each with where its sign came from
    assert by["H1"].scales == [
        {"inventory": "HEX", "construct": "Diligence", "key": "+", "key_source": I.SOURCE_B},
        {"inventory": "NEO", "construct": "Orderliness", "key": "+", "key_source": I.SOURCE_B}]
    assert by["H2"].scales == [{"inventory": "NEO", "construct": "Orderliness", "key": "-",
                                "key_source": I.SOURCE_B}]
    assert by["W11"].codes == ["W11", "H99", "T200"] and by["H1"].codes == ["H1"]
    assert counts["n_with_scales"] == 12 and counts["n_multi_scale"] == 2
    assert counts["n_codes"] == 14 and counts["n_multi_code"] == 1
    assert counts["n_keyed_minus"] == 3
    assert counts["per_inventory"]["NEO"] == {"items": 9, "constructs": 3}
    assert counts["per_inventory"]["HEX"] == {"items": 2, "constructs": 2}
    # items come out in code order: letter, then number
    assert [r.ipip_id for r in items] == ["E5", "E6", "H1", "H2", "H3", "H4", "P8", "P9", "T10", "W11", "X7", "Y12"]


def test_every_committed_key_says_where_it_came_from(tmp_path):
    """QUESTIONS 46: the tracked items.jsonl is self-describing, whichever way QUESTIONS 52 went."""
    items, counts = build(tmp_path)
    assert all(s["key_source"] in (I.SOURCE_B, I.SOURCE_A) for r in items for s in r.scales)
    assert counts["key_sources"] == {I.SOURCE_B: 14}
    # the one A-only row of the plain fixture is the item that is in no list, so nothing is committed from A
    assert counts["key_merge"]["n_gap_filled_from_workbook"] == 1
    assert counts["n_items_with_a_only_key"] == 0
    assert counts["workbook"]["n_rows"] == len(ASSIGNMENT_ROWS)


def test_an_a_only_key_is_committed_and_tagged(tmp_path):
    """QUESTIONS 52: an A-only key is a gap-fill, committed with its source in the row so that dropping the
    tagged rows is one pass if the question ever arose."""
    extra = ASSIGNMENT_ROWS + (("MPQ", 0.77, 1, "Am always prepared.", "Wellbeing"),)
    items, counts = build(tmp_path, rows=extra)
    by = {r.ipip_id: r for r in items}
    assert {"inventory": "MPQ", "construct": "Wellbeing", "key": "+", "key_source": I.SOURCE_A} in by["W11"].scales
    assert counts["key_sources"] == {I.SOURCE_A: 1, I.SOURCE_B: 14}
    assert counts["key_merge"]["n_gap_filled_from_workbook"] == 2      # the MPQ row and the unlisted item
    assert counts["n_items_with_a_only_key"] == 0                      # W11 also has a key-page key (16PF)


def test_item_row_schema(tmp_path):
    items, _ = build(tmp_path)
    d = items[0].to_json()
    assert list(d) == ["schema_version", "ipip_id", "codes", "text", "scales"] and d["schema_version"] == 2
    assert I.SCHEMA_VERSION == 2


def test_ingest_without_the_workbook_commits_the_key_pages_alone(tmp_path):
    items, counts = build(tmp_path, workbook=False)
    assert counts["workbook"] is None and counts["key_comparison"]["compared"] is False
    assert set(counts["key_sources"]) == {I.SOURCE_B} and counts["n_scale_links"] == 14
    with pytest.raises(FileNotFoundError, match="QUESTIONS 52"):
        I.build_from_dir(tmp_path / "ext", require_workbook=True)
    assert any(r.scales for r in items)


def test_rerun_is_byte_identical_and_snapshots_on_change(tmp_path):
    items, _ = build(tmp_path)
    out = tmp_path / "ipip" / "items.jsonl"
    assert I.write_items(items, out) is None
    first = out.read_bytes()
    items2, _ = build(tmp_path)
    assert I.write_items(items2, out) is None and out.read_bytes() == first
    assert not list(out.parent.glob("items.jsonl.bak.*"))
    assert [r.to_json() for r in I.load_items(out)] == [r.to_json() for r in items]
    # drop the VIA key page and the workbook's VIA row: Y12 loses its only scale
    pages = {k: v for k, v in KEY_PAGE_ROWS.items() if k != "newVIAKey.htm"}
    changed = [r for r in ASSIGNMENT_ROWS if r[3] != "Keep my promises."]
    items3, _ = build(tmp_path / "b", rows=changed, key_pages=pages)
    backup = I.write_items(items3, out)
    assert backup is not None and backup.read_bytes() == first
    assert json.loads(out.read_text().splitlines()[-1])["scales"] == []
    assert json.loads(out.read_text().splitlines()[-1])["ipip_id"] == "Y12"


def test_hex_assertion_is_a_scrape_completeness_check(tmp_path):
    items, counts = build(tmp_path)
    I.check_hex(counts, min_constructs=1, item_range=(1, 5))                    # two HEX constructs: passes
    with pytest.raises(I.HexAssertionError) as ei:
        I.check_hex(counts)                                                      # the real bar: 20 constructs
    msg = str(ei.value)
    assert "scrape-completeness check" in msg and "key_pages" in msg and "cp1252" not in msg
    assert "iso-8859-1" in msg or "Windows" in msg or "download --only key_hexaco" in msg
    # with the HEXACO page gone and no workbook row for it, the block is empty and the check fires
    pages = {k: v for k, v in KEY_PAGE_ROWS.items() if k != "newHEXACO_PI_key.htm"}
    no_hex = [r for r in ASSIGNMENT_ROWS if r[0] != "HEXACO"]
    _, counts2 = build(tmp_path / "nohex", rows=no_hex, key_pages=pages)
    assert counts2["hex"]["constructs"] == 0
    with pytest.raises(I.HexAssertionError):
        I.check_hex(counts2, min_constructs=1, item_range=(1, 5))


def test_text_key_normalisation():
    assert I.text_key("Don’t  like to\ndraw attention to myself.") == I.text_key(
        "don't like to draw attention to myself")


def test_sources_constants_are_used():
    assert SOURCES[WORKBOOK_KEY].dest.endswith(".xlsx")
    assert len(KEY_PAGE_FILES) == 21
