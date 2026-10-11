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


# --------------------------------------------------------------------------- the layouts of the real pages
# Each of these is a shape one of IPIP's own 21 key pages is written in, found on 2026-10-11 when five of them
# parsed to no rows at all and the HEXACO page parsed to item fragments.  They are hand-made pages, twenty years
# apart, so the parser has to read several layouts; one fixture per shape.

def page(body: str) -> bytes:
    """A Word-exported key page: the markup hard-wrapped mid-sentence, as every real page is."""
    return ("<html><head></head><body>" + body + "</body></html>").encode("cp1252")


def test_a_source_newline_inside_an_item_is_whitespace_not_a_line_break():
    """BFASKeys.htm and the four other pages that parsed to nothing: Word wraps the markup inside the sentence,
    so "Get\\r\\nangry easily." was read as the two lines "Get" and "angry easily." and no line was ever an item.
    """
    html = page('<p class="MsoNormal">Volatility\r\n10-item scale</p>\r\n'
                '<p>+\r\nkeyed</p>\r\n<p>Get\r\nchores done right\r\naway. </p>')
    assert I.page_lines(html) == ["Volatility 10-item scale", "+ keyed", "Get chores done right away."]


def test_a_page_level_declaration_keys_the_whole_page(tmp_path):
    """newORAISKey.htm, newORVISKey.htm and newIPIP-IPCScoringKey.htm say "All items are +keyed" once and carry
    no per-construct marker, and number each item in its own table cell."""
    html = page("<p>IPIP-IPC Scoring Key</p><p>All items are +keyed</p>"
                "<table><tr><td><p>Orderliness</p></td></tr>"
                "<tr><td><p>6.</p></td><td><p>Like to tidy\r\nup.</p></td></tr>"
                "<tr><td><p>14.</p></td><td><p>Love order and regularity.</p></td></tr></table>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert [(r.construct, r.key, r.text) for r in rows] == [("Orderliness", "+", "Like to tidy up."),
                                                            ("Orderliness", "+", "Love order and regularity.")]
    assert counts["page_sign"] == "+" and counts["number_lines"] == 2 and counts["unmatched_items"] == 0


def test_an_item_behind_its_number_is_an_item_however_it_reads(tmp_path):
    """newORVISKey.htm prints items with no full stop ("Lead other people"), which every looser test reads as a
    heading; the number in its own cell is the page's own anchor that says it is an item."""
    html = page("<p>All items are + keyed</p><p>Orderliness</p>"
                "<table><tr><td><p>1.</p></td><td><p>Keep in the background</p></td></tr>"
                "<tr><td><p>9.</p></td><td><p>Make friends easily</p></td></tr></table>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert [(r.construct, r.text) for r in rows] == [("Orderliness", "Keep in the background"),
                                                     ("Orderliness", "Make friends easily")]
    assert counts["unlisted_constructs"] == []            # neither item became a construct of its own


def test_a_legend_declares_the_per_item_reverse_key_marker():
    """newCAT-PD-SFv1.1Keys.htm has no keyed markers: a footnote says "RK = reverse-keyed" and 35 items carry
    "(RK)".  The legend is read wherever it sits (here under the table, as on the real page), it makes "+" the
    page's default, and the marker keys its own item alone -- the next item is forward-keyed again."""
    html = page("<p>Items by Scale</p>"
                "<table><tr><td><p>Anxiousness (6 items; Comm &#945; = .83)</p></td></tr>"
                "<tr><td><p>1</p></td><td><p>1558</p></td><td><p>Worry about things.</p></td></tr>"
                "<tr><td><p>34</p></td><td><p>1946</p></td><td><p>Am relaxed most of the time. (RK)</p></td></tr>"
                "<tr><td><p>67</p></td><td><p>1719</p></td><td><p>Fear for the worst.</p></td></tr></table>"
                "<p>Note. SF # = Static Form item number; RK = reverse-keyed.</p>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newCAT-PD-SFv1.1Keys.htm"), known_texts=KNOWN,
                                    page="newCAT-PD-SFv1.1Keys.htm")
    assert [(r.construct, r.key, r.text) for r in rows] == [
        ("Anxiety", "+", "Worry about things."),
        ("Anxiety", "-", "Am relaxed most of the time."),      # the (RK) marker, stripped before the join
        ("Anxiety", "+", "Fear for the worst.")]
    assert counts["rk_mode"] is True and counts["page_sign"] == "+" and counts["number_lines"] == 6


def test_a_hexaco_style_header_matches_the_index_through_its_scale_code():
    """newHEXACO_PI_key.htm heads each facet "Sincerity (H:Sinc) [Alpha = .81]": the index's label and its scale
    code in one line, with the alpha in a second, nested bracket group."""
    cands = I._header_candidates("Diligence (C-Dili) [Alpha = .81]")
    assert "Diligence" in cands and "C-Dili" in cands
    html = page("<p>Honesty-Humility (H ) Facets</p>"
                "<p><b>Diligence (C-Dili) [Alpha = .81]</b></p><p>+ keyed</p><p>Get chores\r\ndone right away.</p>")
    rows, _ = I.parse_key_page(html, constructs=constructs_for("newHEXACO_PI_key.htm"), known_texts=KNOWN,
                               page="newHEXACO_PI_key.htm")
    assert [(r.inventory, r.construct, r.key, r.scale) for r in rows] == [("HEX", "Diligence", "+", "C-Dili")]


def test_a_construct_named_after_the_alpha_is_matched():
    """newAB5CKey.htm puts the scale code first and the construct name last: "I+/I+ vs I-/I- (Alpha = .83)
    GREGARIOUSNESS"."""
    cands = I._header_candidates("C2+/C2+ vs C2-/C2- (Alpha = .83) ORDERLINESS")
    assert "ORDERLINESS" in cands and "C2+/C2+ vs C2-/C2-" in cands
    html = page("<p><b>C2+/C2+ vs C2-/C2- (Alpha = .83) ORDERLINESS</b></p><p>+ keyed</p><p>Like to tidy up.</p>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert [(r.inventory, r.construct, r.key) for r in rows] == [("NEO", "Orderliness", "+")]
    assert counts["unlisted_constructs"] == []


def test_an_item_count_and_alpha_line_annotates_the_construct_above_it():
    """BFASKeys.htm and newBigFive5broadKey.htm put the scale's length on its own line under the construct
    ("10-item scale (Alpha = .85)", "Combined Volatility and Withdrawal 20-item scale (Alpha = .89)").  Read as a
    heading, it filed the items under a construct called "10-item scale"."""
    html = page("<p>Orderliness</p><p>Combined Orderliness and Industriousness 20-item scale (Alpha = .89)</p>"
                "<p>10-item scale (Alpha = .85)</p><p>+ keyed</p><p>Like to tidy up.</p>"
                "<p>Love order and regularity.</p>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert {(r.construct, r.text) for r in rows} == {("Orderliness", "Like to tidy up."),
                                                     ("Orderliness", "Love order and regularity.")}
    assert counts["note_lines"] == 2 and counts["unlisted_constructs"] == []


def test_inside_a_keyed_block_only_a_strong_heading_ends_it():
    """BFASKeys.htm marks four items with a footnote letter ("Rarely put people under pressure. b"), and those
    items are not in the pool, so ``known_texts`` cannot anchor them.  Inside a block only an alpha, a trailing
    colon or capitals ends it, so such a line stays an item (unmatched) instead of becoming a construct; between
    blocks the looser test still names a construct the index does not list."""
    html = page("<p>Orderliness</p><p>+ keyed</p><p>Like to tidy up.</p>"
                "<p>Rarely put people under pressure. b</p><p>Love order and regularity.</p>")
    rows, counts = I.parse_key_page(html, constructs=constructs_for("newNEOKey.htm"), known_texts=KNOWN,
                                    page="newNEOKey.htm")
    assert all(r.construct == "Orderliness" for r in rows) and len(rows) == 2
    assert counts["unmatched_list"] == ["Rarely put people under pressure. b"]
    assert I._strong_header("LOW SELF-EFFICACY") and I._strong_header("Self-Reliance (.71)")
    assert I._strong_header("Dissociation: Absorption [Alpha = .75]")
    assert not I._strong_header("Rarely put people under pressure. b")
    assert _looks_like_header_of("Self-Reliance")          # between blocks, the looser test still applies


def _looks_like_header_of(line):
    return I._looks_like_header(line)


def test_a_page_whose_items_are_not_in_the_pool_is_not_an_empty_page(tmp_path):
    """newORAISKey.htm (203 items) and newORVISKey.htm (95) parse -- constructs matched, items read under their
    sign -- but their interest-inventory items are not in AlphabeticalItemList.htm, so no key can be committed.
    That is reported as ``outside_pool``, not as the parser failure ``empty``, and :func:`check_key_pages` passes
    on it: the page is read, the item list is what has nothing to join to."""
    ext = fixture_pages(tmp_path / "ext", all_21=True)
    (ext / "newORAISKey.htm").write_bytes(page(
        "<p>ORAIS Scoring Key</p><p>All items are +keyed</p><p>Being Alone (6 items [Alpha = .73])</p>"
        "<table><tr><td><p>23.</p></td><td><p>Ate dinner alone.</p></td></tr>"
        "<tr><td><p>49.</p></td><td><p>Went to the movies alone.</p></td></tr></table>"))
    _items, counts = I.build_from_dir(ext)
    k = counts["key_pages"]
    assert k["empty"] == [] and k["outside_pool"] == {"newORAISKey.htm": 2}
    assert k["per_page"]["newORAISKey.htm"]["n_item_lines"] == 2
    assert k["per_page"]["newORAISKey.htm"]["n_rows"] == 0
    I.check_key_pages(counts)


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


def test_an_unsigned_workbook_key_is_missing_data_not_a_negative(tmp_path):
    """Tedone's table records no sign for 239 of its rows (39 zeros among the rows that have an item text, 200
    blanks), and the zeros run both ways -- "Act before thinking through the consequences" under Prudence is
    reverse-keyed on the key page, "Am an extremely loyal person" under Teamwork is forward -- so ``0`` is
    missing data and not a code for "negative".  Such a row is kept with ``key == ""``, counted, and left out of
    the key rows; source B supplies the sign (QUESTIONS 52: B is primary)."""
    rows = [("NEO", 0.82, 1, "Like to tidy up.", "Orderliness"),
            ("NEO", 0.82, 0, "Leave a mess in my room.", "Orderliness"),       # a zero: no sign recorded
            ("NEO", 0.82, "", "Love order and regularity.", "Orderliness"),    # blank: likewise
            ("NEO", 0.82, -1, "Keep in the background.", "Friendliness")]
    p = fixture_workbook(tmp_path / "wb.xlsx", rows=rows)
    got = I.parse_assignment_table(p.read_bytes())
    assert [r.key for r in got] == ["+", "", "", "-"]
    assert I._key_sign("0", row=1) == "" and I._key_sign("", row=1) == "" and I._key_sign("-1", row=1) == "-"
    # an unsigned row is not a key: it never reaches the comparison, the merge or items.jsonl
    keys = I.assignment_key_rows(got)
    assert [(k.text, k.key) for k in keys] == [("Like to tidy up.", "+"), ("Keep in the background.", "-")]
    _items, counts = build(tmp_path / "ext_root", rows=tuple(rows))
    assert counts["workbook"]["n_rows"] == 4 and counts["workbook"]["n_unsigned"] == 2


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


def test_compare_keys_normalises_the_instrument_name():
    """``HEXACO_PI`` (the workbook) and ``HEX`` (the scale index) are one inventory; so are ``HPI-HIC`` and
    ``HPI``, ``NEO5-20`` and ``NEO``, ``BFAS-20`` and ``BFAS``.  Folding the spelling is what makes the exact-match
    rate measure sign and scale identity (QUESTIONS 52)."""
    b = [krow("Get chores done right away.", "HEX", "Diligence", "+")]
    a = [krow("Get chores done right away.", "HEXACO_PI", "Diligence", "+", I.SOURCE_A)]
    c = I.compare_keys(b, a)
    assert c["n_links_shared"] == 1 and c["links_only_a"] == 0 and c["exact_match_rate"] == 1.0
    assert c["normalisations"]["inventory_aliases"]["HEXACOPI"] == "HEX"
    assert I._norm_inventory("HPI-HIC") == I._norm_inventory("HPI") == "HPI"
    assert I._norm_inventory("Barchard, 2001") == I._norm_inventory("BARCHARD2001")
    assert I._norm_inventory("16PF") == "16PF"                      # an inventory of its own, not folded


def test_compare_keys_normalises_the_construct_name():
    """Three spellings of one construct, all of them from the sources themselves: the alternates written in
    another order (the index lists both orders as rows of its own), the index's scale code, and the heading the
    key page prints where the index's label is different."""
    assert I._norm_construct("Integrity/Honesty/Authenticity") == I._norm_construct("Honesty/Integrity/ "
                                                                                    "authenticity")
    b = [I.KeyRow(inventory="VIA", construct="Integrity/Honesty/Authenticity", key="+", text="Keep my promises.",
                  scale="Honesty", heading="Honesty (Integrity)"),
         I.KeyRow(inventory="HEX", construct="Orderliness", key="+", text="Like to tidy up.", scale="C-Orga",
                  heading="Organization")]
    a = [krow("Keep my promises.", "VIA", "Honesty/Integrity/Authenticity", "+", I.SOURCE_A),
         krow("Like to tidy up.", "HEXACO-PI", "Organization", "+", I.SOURCE_A)]      # the page's own heading
    c = I.compare_keys(b, a)
    assert c["n_links_shared"] == 2 and c["exact_match_rate"] == 1.0 and c["sign_conflicts"] == 0
    assert c["links_only_a"] == c["links_only_b"] == 0


def test_a_genuine_sign_disagreement_survives_every_normalisation():
    """The normalisations must not be able to hide a real disagreement: the same item, the same scale under two
    spellings, opposite signs is still a sign conflict, named with the page it came from."""
    b = [I.KeyRow(inventory="HEX", construct="Orderliness", key="-", text="Like to tidy up.", scale="C-Orga",
                  heading="Organization", page="newHEXACO_PI_key.htm")]
    a = [krow("Like to tidy up.", "HEXACO_PI", "Organization", "+", I.SOURCE_A)]
    c = I.compare_keys(b, a)
    assert c["sign_conflicts"] == 1 and c["n_links_shared"] == 1
    assert c["sign_conflict_list"][0]["key_pages"] == "-" and c["sign_conflict_list"][0]["workbook"] == "+"
    assert c["sign_conflict_list"][0]["page"] == "newHEXACO_PI_key.htm"
    assert c["link_mismatch_rate"] == 1.0 and c["needs_roger"] is True
    assert c["normalisations"]["signs"].startswith("untouched")
    # and a disagreement on one of an item's two links does not pass as an exact match either
    assert c["exact_match_items"] == 0


def test_compare_keys_pairs_equal_signs_first():
    """An item on two scales of one inventory, one of them reverse-keyed: the links must pair by construct and
    not leave a spurious conflict behind."""
    b = [krow("Like to tidy up.", "NEO", "Orderliness", "+"), krow("Like to tidy up.", "NEO", "Anxiety", "-")]
    a = [krow("Like to tidy up.", "NEO", "Anxiety", "-", I.SOURCE_A),
         krow("Like to tidy up.", "NEO", "Orderliness", "+", I.SOURCE_A)]
    c = I.compare_keys(b, a)
    assert c["sign_conflicts"] == 0 and c["n_links_shared"] == 2 and c["exact_match_rate"] == 1.0


def test_compare_keys_sets_aside_items_outside_the_pool():
    """Both sides are restricted to the item pool when it is given, because neither source can commit a key for
    an item the item list does not hold (the two Oregon interest inventories, ~300 items of the workbook)."""
    b = [krow("Keep my promises.", "VIA", "Integrity", "+")]
    a = a_rows(b) + [krow("Ate dinner alone.", "ORAIS", "Being Alone", "+", I.SOURCE_A)]
    loose = I.compare_keys(b, a)
    assert loose["items_only_a"] == 1 and loose["set_aside_a"] == 0
    tight = I.compare_keys(b, a, known_texts=KNOWN)
    assert tight["items_only_a"] == 0 and tight["set_aside_a"] == 1 and tight["exact_match_rate"] == 1.0
    assert "AlphabeticalItemList" in tight["normalisations"]["item_pool"]


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
