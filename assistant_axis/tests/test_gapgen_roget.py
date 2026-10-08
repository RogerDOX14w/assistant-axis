"""Roget 1911 parser (workstream 2, coding_plan_02_roget_wordnet.md § 8 "Parser").

The fixture ``fixtures/roget_sample.txt`` is 23 heads cut verbatim from the pinned Gutenberg text
by ``roget_generate.py parse --fixture`` (``parse.extract_fixture``): 1, 2, 82, 83, 600-610 with
604a and 609a, 862-865, 897, 898.  Expected values below were read off the fixture when the tests
were written.  Tests on the full text skip when ``data/external/roget/pg10681.txt`` is absent.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from assistant_axis.gapgen.generators.roget import parse as P

FIXTURE = Path(__file__).parent / "fixtures" / "roget_sample.txt"
FULL_TEXT = Path(__file__).resolve().parents[2] / "data" / "external" / "roget" / "pg10681.txt"
FIXTURE_IDS = ["1", "2", "82", "83", "600", "601", "602", "603", "604", "604a", "605", "606", "607", "608",
               "609", "609a", "610", "862", "863", "864", "865", "897", "898"]


@pytest.fixture(scope="module")
def idx():
    return P.parse_roget(FIXTURE.read_text(encoding="utf-8"))


def test_head_set_is_the_fixture(idx):
    assert idx.order == FIXTURE_IDS
    assert len(idx) == 23


def test_lettered_head(idx):
    h = idx["604a"]
    assert (h.number, h.letter, h.title) == (604, "a", "Perseverance")


def test_structure_fields_of_604(idx):
    h = idx["604"]
    assert h.title == "Resolution"
    assert h.klass == "V"
    assert h.class_title == "Words relating to the voluntary powers"
    assert h.division == "I. Individual volition"
    assert h.section == "I. Volition in general"
    assert h.subsection == "1. Acts of Volition"
    assert h.path == "V > I. Individual volition > I. Volition in general > 1. Acts of Volition"
    # Class VI has no divisions; a capitalised subsection is title-cased
    assert idx["864"].division is None
    assert idx["864"].subsection == "3. Prospective affections"
    assert idx["1"].subsection == "1. Being, in the abstract"


def test_adjectives_and_groups(idx):
    adj = idx["604"].pos["Adj"]
    flat = [it for g in adj for it in g]
    assert "determined" in flat and "unflinching" in flat
    # semicolon groups are preserved
    assert ["strong-willed", "strong-minded"] in adj
    assert ["unhesitating", "unflinching"] in adj
    assert idx["864"].pos["Adj"][0] == ["cautious", "wary", "guarded"]


def test_obsolete_and_foreign_items_dropped_and_counted(idx):
    h = idx["863"]
    assert "foolhardihood" not in h.items("N") and "foolhardiness" in h.items("N")  # foolhardihood†
    assert "uncalculating" not in h.items("Adj")                                     # uncalculating†
    assert h.drops["obsolete"] >= 2 and h.n_dropped == sum(h.drops.values())
    assert "enfant perdu" not in h.items("N")                                        # [Fr.]
    assert h.drops["foreign"] >= 1


def test_us_item_kept_with_tag(idx):
    h = idx["863"]
    assert "boomer" in h.items("N")
    assert h.item_tags["boomer"] == ["U.S."]
    assert h.tags_seen["U.S."] >= 1


def test_xrefs_recorded_and_removed(idx):
    h = idx["863"]
    assert ("460", "careless") in h.xrefs        # careless &c (neglectful) 460
    assert "careless" not in h.items("Adj")
    assert ("605", "irresolute") in idx["607"].xrefs
    assert ("604a", "perseverance") in idx["606"].xrefs   # perseverance &c 604.1


def test_brace_notes_spanning_lines(idx):
    assert idx["82"].antonym_refs == ["83"] and idx["83"].antonym_refs == ["82"]
    assert idx["82"].pos["N"][0] == ["conformity", "conformance"]


def test_head_note_in_brackets(idx):
    h = idx["862"]
    assert h.title == "Cowardice" and h.note == "Excess of fear."


@pytest.mark.parametrize("raw,expected", [
    ("existence (in space)", "existence"),           # parenthetical stripped
    ("actuality.", "actuality"),                     # trailing period
    ("positiveness &c adj.", "positiveness"),        # "&c adj." removed
    ("cautiousness &c. n.", "cautiousness"),
    ("self-possessed", "self-possessed"),            # hyphenated word kept
    ("one or two", "one or two"),
    ("cento [Lat.]", None),                          # language tag drops
    ("conation†", None),                        # obsolete dagger drops
    ("the 100 days", None),                          # digits drop
    ("a word of five long words", None),             # five words drop
    ("'tu quoque'", None),                           # quotation drops
    ("make assurance doubly sure [Macbeth]", None),  # attribution: a quotation
])
def test_clean_item(raw, expected):
    assert P.clean_item(raw)[0] == expected


def test_clean_item_tags_and_xref():
    sink = P._Sink()
    assert P.clean_item("grit [U.S.]", sink=sink) == ("grit", ["U.S."])
    assert P.clean_item("careless &c (neglectful) 460", sink=sink) == (None, [])
    assert sink.xrefs == [("460", "careless")]


def test_split_items_respects_brackets():
    groups = P.split_items("rash, incautious; [Motion towards, actively; force] attraction, pull; x [Lat.]")
    assert groups == [["rash", "incautious"], ["attraction", "pull"]]


def test_head_profile(idx):
    prof = P.head_profile(idx["604"])
    assert prof.startswith("Resolution.")
    adj = prof.split("Adjectives: ", 1)[1].split(". Nouns:", 1)[0].split(", ")
    assert 1 <= len(adj) <= 15


def test_dispositional_heads(idx):
    got = [h.id for h in P.dispositional_heads(idx, extra=["82"])]
    assert got == [h for h in FIXTURE_IDS if int(h.rstrip("ab")) >= 450 or h == "82"]
    assert all(idx[h].number >= 450 for h in got if h != "82")


def test_strip_gutenberg():
    raw = ("header\r\n*** START OF THE PROJECT GUTENBERG EBOOK X ***\r\nbody <-- an editorial\r\ncomment --> end\r\n"
           "*** END OF THE PROJECT GUTENBERG EBOOK X ***\r\nlicence\r\n")
    out = P.strip_gutenberg(raw)
    assert "header" not in out and "licence" not in out and "\r" not in out
    assert "editorial" not in out and out.startswith("body")


def test_check_checksum(tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("hello", encoding="utf-8")
    good = P.sha256_of(f)
    assert P.check_checksum(f, expected=good) == good
    with pytest.raises(P.ChecksumMismatch):
        P.check_checksum(f, expected="0" * 64)
    assert P.check_checksum(f, expected="0" * 64, allow_mismatch=True) == good
    assert P.check_checksum(f, expected=None) == good


def test_fetch_with_fake_opener_and_dry_run(tmp_path):
    dest = tmp_path / "roget" / "pg10681.txt"
    assert P.fetch_roget(dest, dry_run=True, opener=lambda u: pytest.fail("dry run fetched")) == dest
    assert not dest.exists()
    calls = []
    P.fetch_roget(dest, opener=lambda u: calls.append(u) or b"text")
    assert dest.read_bytes() == b"text" and calls == [P.ROGET_URL]


def test_save_and_load_heads_round_trip(idx, tmp_path):
    text = tmp_path / "pg.txt"
    text.write_text("x", encoding="utf-8")
    idx.text_sha256 = "abc"
    path = P.save_heads(idx, tmp_path / "heads.json", text_path=text)
    env = json.loads(path.read_text(encoding="utf-8"))
    assert "_provenance" in env and env["result"]["n_heads"] == 23
    assert env["_provenance"]["inputs"][0]["dep_key"] == "roget_text"
    back = P.load_heads(path)
    assert back.order == idx.order
    assert back["604"].to_json() == idx["604"].to_json()
    assert back.by_subsection == idx.by_subsection


def test_extract_fixture_is_stable():
    """Re-extracting the fixture's own heads from the fixture gives the fixture back."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert P.extract_fixture(text, FIXTURE_IDS) == text


# --------------------------------------------------------------------------- full text

full = pytest.mark.skipif(not FULL_TEXT.exists(), reason="data/external/roget/pg10681.txt not downloaded")


@full
def test_full_text_invariants():
    """Counts of the pinned text (Gutenberg #10681, updated 2024-10-28, SHA-256 pinned in parse.py).
    The plan's 1,032 / 994 / 38 / 927 were measured on an older edition: this one has every number
    1-1000 and 44 lettered heads; 912 heads keep at least one adjective (927 have an ``Adj.`` line;
    15 of those blocks hold only cross-references or long phrases)."""
    idx = P.parse_file(FULL_TEXT)
    c = P.census(idx)
    assert c["n_heads"] == 1044
    assert c["n_numbers"] == 1000
    assert c["n_lettered"] == 44
    assert c["n_with_adj"] == 912
    assert c["n_dispositional"] == 576
    # every head has a class and a section; unknown tags on kept items stay rare
    assert all(h.klass and h.section for h in idx.heads.values())
    from collections import Counter
    kept_unknown = Counter(t for h in idx.heads.values() for tags in h.item_tags.values() for t in tags
                           if t not in P.KEEP_TAGS)
    assert not [t for t, n in kept_unknown.items() if n > 20]
    # the fixture's heads parse identically inside the full text
    fx = P.parse_roget(FIXTURE.read_text(encoding="utf-8"))
    for hid in fx.order:
        a, b = fx[hid].to_json(), idx[hid].to_json()
        a.pop("line_start"), b.pop("line_start")
        assert a == b, hid
