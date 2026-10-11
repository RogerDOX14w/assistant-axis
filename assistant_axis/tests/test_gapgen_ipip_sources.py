"""IPIP generator (workstream 7), the sources: what is fetched, where it goes, the licence."""
from pathlib import Path

from assistant_axis.gapgen.generators import ipip as P
from assistant_axis.gapgen.generators.ipip import sources as S
from assistant_axis.gapgen.paths import DATA_CANDIDATES, DATA_EXTERNAL


def test_package_constants():
    assert P.GENERATOR == "ipip"
    assert P.IPIP_DIR == DATA_CANDIDATES / "ipip"
    assert P.ITEMS_PATH == P.IPIP_DIR / "items.jsonl"
    assert P.EXTERNAL_DIR == DATA_EXTERNAL / "ipip"
    assert P.clusters_path(350) == P.IPIP_DIR / "clusters_g350.jsonl"
    assert P.clusters_path(150).name == "clusters_g150.jsonl"


def test_every_source_has_url_dest_and_licence():
    assert set(S.SOURCES) >= {"item_list", "assignment_table", "scale_index", "home", "key_hexaco",
                              "assignment_workbook"}
    for key, s in S.SOURCES.items():
        assert s.key == key
        assert s.url.startswith("https://ipip.ori.org/") and s.url.endswith(s.filename)
        dest = (P.EXTERNAL_DIR / s.dest).resolve()
        assert P.EXTERNAL_DIR.resolve() in dest.parents, f"{key} lands outside data/external/ipip"
        assert s.licence and s.licence_quote == S.LICENCE_QUOTE
        assert s.role in ("items", "index", "licence", "keys_b", "keys_a")
    assert "public domain" in S.LICENCE_QUOTE.lower()
    assert "without asking permission" in S.LICENCE_QUOTE


def test_the_21_key_pages_are_source_b_and_all_approved():
    """QUESTIONS 52 option C: the 21 per-inventory key pages are the primary source of the keys, and both
    fetches (the pages and the one workbook) were approved on 2026-10-11."""
    keys = [k for k, s in S.SOURCES.items() if s.role == "keys_b"]
    assert len(keys) == len(S.KEY_PAGE_KEYS) == S.N_KEY_PAGES == 21
    assert S.SOURCES["key_hexaco"].filename == "newHEXACO_PI_key.htm"      # QUESTIONS 49: on the main path now
    for k in keys:
        assert S.SOURCES[k].approval == S.APPROVAL_2026_10_11
    wb = S.SOURCES[S.WORKBOOK_KEY]
    assert wb.role == "keys_a" and wb.approval == S.APPROVAL_2026_10_11
    assert wb.licence.startswith("no licence stated")
    assert "Tedone" in S.WORKBOOK_CREDIT and "no licence requires attribution" in S.WORKBOOK_CREDIT


def test_default_fetch_is_everything_approved():
    assert S.DEFAULT_FETCH == tuple(S.SOURCES)
    assert len(S.DEFAULT_FETCH) == 3 + 1 + 21 + 1                           # pages, home, key pages, workbook
    assert S.SOURCES["home"].role == "licence"                              # QUESTIONS 46: the licence sentence
    names = {s.filename for s in S.SOURCES.values()}
    assert {"AlphabeticalItemList.htm", "ItemAssignmentTable.htm", "newIndexofScaleLabels.htm",
            "TedoneItemAssignmentTable30APR21.xlsx"} <= names


def test_the_unapproved_stand_in_is_not_fetched():
    assert S.UNAPPROVED_EXAMPLE.approval is None
    assert S.UNAPPROVED_EXAMPLE.key not in S.SOURCES


def test_dest_is_a_relative_path():
    for s in list(S.SOURCES.values()) + [S.UNAPPROVED_EXAMPLE]:
        assert not Path(s.dest).is_absolute() and ".." not in Path(s.dest).parts
