"""The IPIP pages this generator downloads, and the licence they are used under.

Four kinds of source, all on ipip.ori.org:

* the **item list**, ``AlphabeticalItemList.htm``: every item's text with its Eugene-Springfield survey code
  (``H1131``);
* the **scale index**, ``newIndexofScaleLabels.htm``: the 274 construct labels with their inventories (NEO, HEX,
  16PF, CPI, JPI, MPQ, TCI, HPI, AB5C, VIA, CAT-PD and others) and a link to each inventory's key page;
* the **21 key pages** (:data:`KEY_PAGE_FILES`), IPIP's own scoring keys: each construct with its ``+`` and ``-``
  keyed items.  **These are the primary source of the key signs** (QUESTIONS 52, option C, Roger 2026-10-11);
* the **assignment workbook**, ``TedoneItemAssignmentTable30APR21.xlsx``, linked from ``ItemAssignmentTable.htm``
  (which is itself a 3,759-byte page about the table, not the table).  Thomas Tedone compiled it by scraping those
  same key pages; it is fetched as a **check and gap-filler** on the key pages, never as the sole authority for a
  committed key.  The ``home`` page is fetched for one reason: to record IPIP's public-domain sentence verbatim
  (QUESTIONS 46; it is on the home page and on none of the pages fetched on 2026-10-10).

Roger approved both fetches on 2026-10-11 (QUESTIONS 52: "option C, and both fetches are approved").
:data:`APPROVAL_2026_10_11` is what the manifest records for the key pages, the workbook and the home page;
the three pages of 2026-10-10 keep :data:`APPROVAL_2026_10_10`.  A source whose ``approval`` is ``None`` is
refused by :func:`.download.fetch_all` unless the caller names Roger's go (``--approved-by '<Roger, date>'``),
and that go is recorded in the manifest entry; no source in this module has ``approval`` ``None`` today, which
is why :data:`UNAPPROVED_EXAMPLE` exists for the tests.

IPIP publishes no hashes; :mod:`.download` records the sha256 and size of the bytes received.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

BASE_URL = "https://ipip.ori.org/"
#: The home page's public-domain statement, as quoted by plan 07 § 2 when it was verified on 2026-10-10 (the
#: ellipsis is the plan's).  Second-hand by construction: :func:`.download.find_licence_sentence` looks for the
#: full sentence in the pages fetched and records it verbatim in the manifest (``licence.verbatim``), which is
#: what the ``home`` page is fetched for (QUESTIONS 46).
LICENCE_QUOTE = ("The items and scales are in the public domain ... use them for any purpose without asking "
                 "permission and without paying a fee")
LICENCE = "public domain (IPIP's blanket statement on ipip.ori.org)"
LICENCE_URL = BASE_URL
CITATION = ("International Personality Item Pool: A Scientific Collaboratory for the Development of Advanced "
            "Measures of Personality Traits and Other Individual Differences (https://ipip.ori.org/)")
#: Credited in the manifest although no licence requires it (QUESTIONS 52, Roger 2026-10-11): the workbook is
#: Tedone's compilation of IPIP's own public-domain items and keys, shared on ipip.ori.org.
WORKBOOK_CREDIT = ("Item assignment table compiled by Thomas Tedone (TedoneItemAssignmentTable30APR21.xlsx, "
                   "corrected 2021-06-21), by web-scraping the hyperlinks of the International Personality Item "
                   "Pool website; shared on ipip.ori.org/ItemAssignmentTable.htm.  Credited by choice: its content "
                   "is IPIP's public-domain items and keys, and no licence requires attribution.")


#: Roger's go for the three pages (coding_plan_07 § 9 task 2).
APPROVAL_2026_10_10 = ("Roger, 2026-10-10: the three pages, under ~2 MB, the HEXACO key page only on the fallback "
                       "(coding_plan_07 § 9 task 2)")
#: Roger's go for option C (QUESTIONS 52): IPIP's 21 per-inventory key pages (primary) and Tedone's workbook
#: (a check and gap-filler), plus the home page for the licence sentence (QUESTIONS 46).
APPROVAL_2026_10_11 = ("Roger, 2026-10-11: option C, both fetches approved - IPIP's 21 per-inventory key pages "
                       "and the one workbook, into gitignored data/external/ipip/ with hashes in the manifest "
                       "(QUESTIONS 52); the home page for the licence sentence (QUESTIONS 46)")


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
    #: ``"keys_b"`` for a key page, ``"keys_a"`` for the workbook, ``"items"``, ``"index"``, ``"licence"``.
    role: str = ""
    #: A key page's inventory, as the scale index abbreviates it ("NEO", "HEX", ...); several for a page that
    #: carries more than one (``newHPIKeys.htm``), empty for a page whose inventories are read from its own text.
    inventories: tuple = ()

    def as_dict(self) -> dict:
        return asdict(self)


def _page(key: str, filename: str, what: str, *, optional: bool = False, approval: Optional[str] = APPROVAL_2026_10_10,
          licence: str = LICENCE, role: str = "", inventories: tuple = ()) -> Source:
    return Source(key=key, filename=filename, url=BASE_URL + filename, dest=filename, optional=optional, what=what,
                  approval=approval, licence=licence, role=role, inventories=inventories)


#: The workbook's licence as far as the page states one: none of its own (QUESTIONS 52).
WORKBOOK_LICENCE = ("no licence stated; compiled by Thomas Tedone from IPIP's public-domain items and keys, shared "
                    "on ipip.ori.org (ItemAssignmentTable.htm)")

#: The 21 per-inventory key pages, every one linked from ``newIndexofScaleLabels.htm`` (counted on the page
#: fetched 2026-10-10: 21 distinct key pages besides ``index.htm``, ``newHEXACO_PI_key.htm`` among them with 31
#: HEX links).  ``source key -> (file name, what)``; the inventory abbreviations a page is expected to carry are
#: read from the scale index, not hard-coded, so a page serving several inventories needs no special case.
KEY_PAGE_FILES: dict[str, str] = {
    "key_hpi": "newHPIKeys.htm",
    "key_via": "newVIAKey.htm",
    "key_ab5c": "newAB5CKey.htm",
    "key_neo": "newNEOKey.htm",
    "key_cat_pd": "newCAT-PD-SFv1.1Keys.htm",
    "key_orais": "newORAISKey.htm",
    "key_tci": "newTCIKey.htm",
    "key_cpi": "newCPIKey.htm",
    "key_single_constructs": "newSingleConstructsKey.htm",
    "key_hexaco": "newHEXACO_PI_key.htm",
    "key_6fpq": "new6FPQKey.htm",
    "key_bfas": "BFASKeys.htm",
    "key_jpi_r": "newJPI-RKey.htm",
    "key_16pf": "new16PFKey.htm",
    "key_mpq": "newMPQKey.htm",
    "key_orvis": "newORVISKey.htm",
    "key_bis_bas": "newBIS_BASkey.htm",
    "key_ipip_ipc": "newIPIP-IPCScoringKey.htm",
    "key_7factor": "new7FactorKey.htm",
    "key_emotional_intelligence": "newEmotionalIntelligenceKey.htm",
    "key_big_five_broad": "newBigFive5broadKey.htm",
}
N_KEY_PAGES = 21

SOURCES: dict[str, Source] = {s.key: s for s in (
    _page("item_list", "AlphabeticalItemList.htm", "every item's text with its Eugene-Springfield code",
          role="items"),
    _page("assignment_table", "ItemAssignmentTable.htm",
          "a page describing the item assignment table and linking to its workbook (the table is not on the page)",
          role="index"),
    _page("scale_index", "newIndexofScaleLabels.htm", "construct labels by inventory, with links to the key pages",
          role="index"),
    _page("home", "index.htm", "IPIP's home page, for the public-domain sentence recorded verbatim (QUESTIONS 46)",
          approval=APPROVAL_2026_10_11, role="licence"),
    *(_page(k, f, "IPIP's own scoring key: each construct with its + and - keyed items (source B, primary)",
            approval=APPROVAL_2026_10_11, role="keys_b") for k, f in KEY_PAGE_FILES.items()),
    _page("assignment_workbook", "TedoneItemAssignmentTable30APR21.xlsx",
          "the item assignment table: instrument, alpha, key (1 / -1), text, construct label (source A, a check "
          "and gap-filler on the key pages)", approval=APPROVAL_2026_10_11, licence=WORKBOOK_LICENCE, role="keys_a"),
)}

#: Fetched by ``download`` with no ``--only``: everything approved (the three pages of 2026-10-10, the home page,
#: the 21 key pages and the workbook).  ``optional`` is kept on :class:`Source` for a page that may be absent;
#: none is today.
DEFAULT_FETCH: tuple[str, ...] = tuple(k for k, s in SOURCES.items() if not s.optional)
#: The key pages, in the order of :data:`KEY_PAGE_FILES` (source B).
KEY_PAGE_KEYS: tuple[str, ...] = tuple(KEY_PAGE_FILES)
#: Source A: the one workbook.
WORKBOOK_KEY = "assignment_workbook"

#: A source with no approval on record, for the tests of :class:`.download.NotApproved` (every real source is
#: approved since 2026-10-11, so the refusal path would otherwise be untested).
UNAPPROVED_EXAMPLE = Source(key="unapproved_example", filename="NotApproved.htm", url=BASE_URL + "NotApproved.htm",
                            dest="NotApproved.htm", optional=True, what="a page with no approval on record",
                            approval=None, role="")
