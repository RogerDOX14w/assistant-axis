"""The IPIP pages this generator downloads, and the licence they are used under.

Three pages of ipip.ori.org carry everything the generator needs (plan 07 § 2, verified 2026-10-10):

* ``AlphabeticalItemList.htm``: every item's text with its Eugene-Springfield survey code (``H1131``);
* ``ItemAssignmentTable.htm``: which scales each item is keyed on, and the key's sign (+ or -);
* ``newIndexofScaleLabels.htm``: the construct labels and the inventories they belong to (NEO, HEX, 16PF, CPI,
  JPI, MPQ, TCI, HPI, AB5C, VIA, CAT-PD and others).

``newHEXACO_PI_key.htm`` is the fallback of plan § 7 ``ingest``: fetched only when the HEX assertion fails (at
least 20 constructs keyed ``HEX``), under the same approval (Roger, 2026-10-10: "the three pages, under ~2 MB,
the HEXACO key page only on the fallback").  IPIP publishes no hashes; :mod:`.download` records the sha256 and
size of the bytes received.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

BASE_URL = "https://ipip.ori.org/"
#: The home page's public-domain statement, as quoted by plan 07 § 2 when it was verified on 2026-10-10 (the
#: ellipsis is the plan's).  :func:`.download.find_licence_sentence` looks for the full sentence in the pages
#: fetched and records it verbatim in the manifest when one of them carries it.
LICENCE_QUOTE = ("The items and scales are in the public domain ... use them for any purpose without asking "
                 "permission and without paying a fee")
LICENCE = "public domain (IPIP's blanket statement on ipip.ori.org)"
LICENCE_URL = BASE_URL
CITATION = ("International Personality Item Pool: A Scientific Collaboratory for the Development of Advanced "
            "Measures of Personality Traits and Other Individual Differences (https://ipip.ori.org/)")


@dataclass(frozen=True)
class Source:
    key: str
    filename: str
    url: str
    dest: str                       # relative to data/external/ipip/
    optional: bool = False
    licence: str = LICENCE
    licence_url: str = LICENCE_URL
    licence_quote: str = LICENCE_QUOTE
    what: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _page(key: str, filename: str, what: str, *, optional: bool = False) -> Source:
    return Source(key=key, filename=filename, url=BASE_URL + filename, dest=filename, optional=optional, what=what)


SOURCES: dict[str, Source] = {s.key: s for s in (
    _page("item_list", "AlphabeticalItemList.htm", "every item's text with its Eugene-Springfield code"),
    _page("assignment_table", "ItemAssignmentTable.htm", "item to scale assignments with key signs"),
    _page("scale_index", "newIndexofScaleLabels.htm", "construct labels by inventory"),
    _page("hexaco_key", "newHEXACO_PI_key.htm", "the IPIP-HEXACO key (fallback only)", optional=True),
)}

#: Fetched by ``download`` with no ``--only``: the three pages.
DEFAULT_FETCH: tuple[str, ...] = tuple(k for k, s in SOURCES.items() if not s.optional)
