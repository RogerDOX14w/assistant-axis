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

**The item-to-scale table is not on the three pages** (found 2026-10-10, QUESTIONS 52):
``ItemAssignmentTable.htm`` describes the table and links to an Excel workbook compiled by Thomas Tedone,
``TedoneItemAssignmentTable30APR21.xlsx`` (columns instrument, alpha, key, text, label).  It is listed here as
``assignment_workbook`` with no approval: :func:`.download.fetch_all` refuses a source whose ``approval`` is
``None`` unless the caller names Roger's go (``download --only assignment_workbook --approved-by '...'``), and
records that go in the manifest.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

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


#: Roger's go for the IPIP fetch (coding_plan_07 § 9 task 2).
APPROVAL_2026_10_10 = ("Roger, 2026-10-10: the three pages, under ~2 MB, the HEXACO key page only on the fallback "
                       "(coding_plan_07 § 9 task 2)")


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
    #: Who approved fetching it; ``None``: not approved, refused unless the caller names the go.
    approval: Optional[str] = APPROVAL_2026_10_10

    def as_dict(self) -> dict:
        return asdict(self)


def _page(key: str, filename: str, what: str, *, optional: bool = False, approval: Optional[str] = APPROVAL_2026_10_10,
          licence: str = LICENCE) -> Source:
    return Source(key=key, filename=filename, url=BASE_URL + filename, dest=filename, optional=optional, what=what,
                  approval=approval, licence=licence)


#: The workbook's licence as far as the page states one: none of its own (QUESTIONS 52).
WORKBOOK_LICENCE = ("no licence stated; compiled by Thomas Tedone from IPIP's public-domain items and keys, shared "
                    "on ipip.ori.org (ItemAssignmentTable.htm)")

SOURCES: dict[str, Source] = {s.key: s for s in (
    _page("item_list", "AlphabeticalItemList.htm", "every item's text with its Eugene-Springfield code"),
    _page("assignment_table", "ItemAssignmentTable.htm",
          "a page describing the item assignment table and linking to its workbook (the table is not on the page)"),
    _page("scale_index", "newIndexofScaleLabels.htm", "construct labels by inventory, with links to the key pages"),
    _page("hexaco_key", "newHEXACO_PI_key.htm", "the IPIP-HEXACO key (fallback only)", optional=True),
    _page("assignment_workbook", "TedoneItemAssignmentTable30APR21.xlsx",
          "the item assignment table: instrument, alpha, key (1 / -1), text, construct label", optional=True,
          approval=None, licence=WORKBOOK_LICENCE),
)}

#: Fetched by ``download`` with no ``--only``: the three pages.
DEFAULT_FETCH: tuple[str, ...] = tuple(k for k, s in SOURCES.items() if not s.optional)
