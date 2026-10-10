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
    assert set(S.SOURCES) >= {"item_list", "assignment_table", "scale_index", "hexaco_key"}
    for key, s in S.SOURCES.items():
        assert s.key == key
        assert s.url.startswith("https://ipip.ori.org/") and s.url.endswith(s.filename)
        dest = (P.EXTERNAL_DIR / s.dest).resolve()
        assert P.EXTERNAL_DIR.resolve() in dest.parents, f"{key} lands outside data/external/ipip"
        assert s.licence and s.licence_quote == S.LICENCE_QUOTE
    assert "public domain" in S.LICENCE_QUOTE.lower()
    assert "without asking permission" in S.LICENCE_QUOTE


def test_the_three_pages_and_the_optional_fallback():
    assert [k for k, s in S.SOURCES.items() if not s.optional] == ["item_list", "assignment_table", "scale_index"]
    assert S.SOURCES["hexaco_key"].optional is True
    assert S.SOURCES["hexaco_key"].filename == "newHEXACO_PI_key.htm"
    assert S.DEFAULT_FETCH == ("item_list", "assignment_table", "scale_index")
    names = {s.filename for s in S.SOURCES.values()}
    assert {"AlphabeticalItemList.htm", "ItemAssignmentTable.htm", "newIndexofScaleLabels.htm"} <= names


def test_dest_is_a_relative_path():
    for s in S.SOURCES.values():
        assert not Path(s.dest).is_absolute() and ".." not in Path(s.dest).parts
