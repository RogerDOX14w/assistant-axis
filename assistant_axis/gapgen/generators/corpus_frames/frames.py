"""The Books frame bank (plan section 6): fixed strings with one slot, across six syntactic types.

A **frame** is a fixed string with one slot ("very X man", "an incorrigible X", "known for his X"); its **fillers**
are the words found in the slot.  In the Google Books n-grams a frame is an n-gram shape: a fixed **prefix** that
places it in the globally sorted shards (:mod:`.books` locates it by head-peeking), the slot, and for the degree and
copular frames a **suffix** set that closes it (a person noun, :data:`PERSON_NOUNS`, recorded per hit).  Six types,
as Roger's item 6 asks (2026-10-13: "a range of such frames ... summing across them gives little net filtering"), so
that no one grammatical filter shapes the union:

==========  =======================================  =============================================  ====
type        the n-gram (slot X)                      filler                                         n
==========  =======================================  =============================================  ====
degree      ``very X <person noun>``; ``too X to``   adjective                                      3
nominal     ``an incorrigible X``                    a person noun, or a noun the helper relabels   3
possessive  ``known for his X``; ``man of X``        a quality noun (honesty: honest by the helper)  4 / 3
copular     ``was a X <person noun>``                adjective                                      4
tendency    ``tendency to be X``                     adjective                                      4
habitual    ``he was always X``                      adjective                                      4
==========  =======================================  =============================================  ====

Two tiers (tier 1: one to three frames of every type; tier 2: the rarer degree adverbs, the second copular and
habitual forms, four more nominal anchors).  Roger decided on 2026-10-14 to stream both tiers in the first build
(open decision 1 (b)); ``--tier`` still selects them, for a rerun.

:func:`regex_for` matches a Books line (``ngram TAB year,match,volumes ...``) of one frame, **plain lowercase tokens
only**: a token with a ``_TAG`` suffix (``very_ADJ``), a wildcard (``_ADV_``), a capital (``very Christian man``) or a
function word in the slot (``very the man``; ``normalize.STOPWORDS``) does not match.  So sentence-initial and
proper-adjective fillers are lost (a known gap, counted in the readout).  Filler-first frames ("X to a fault", "X by
nature") are **not in this bank**: every n-gram that starts with X lies in a different shard, so Books cannot locate
them; the text corpora's bank has them (:mod:`.text`).

Every field of every frame is in :func:`bank_sha256`, recorded in the shard plan, the table and every run.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Union

from assistant_axis.gapgen.normalize import STOPWORDS

TYPES: tuple[str, ...] = ("degree", "nominal", "possessive", "copular", "tendency", "habitual")
FILLER_KINDS: tuple[str, ...] = ("adj", "noun", "quality_noun")
TIERS: tuple[int, ...] = (1, 2)
#: The frame floor (the workstream's): a filler counts in a Books frame only with at least this many matches over the
#: years kept (>= 1920, Roger 2026-10-13).
FRAME_FLOOR = 40
#: The filler: lowercase letters, hyphenated compounds kept (plan section 6).
TOKEN_RE = r"[a-z]+(?:-[a-z]+)*"
#: The suffix set of the degree and copular frames (recorded per hit; plan section 6, 22 nouns).
PERSON_NOUNS: frozenset = frozenset(
    "person man woman fellow people character individual soul chap lady guy girl boy gentleman creature child youth "
    "friend companion neighbor neighbour master".split())


@dataclass(frozen=True)
class Frame:
    """One Books frame: ``prefix`` tokens, the slot at index ``slot`` (always ``len(prefix)``), then the ``suffix``
    token when the frame has a suffix set.  ``n`` is the n-gram order the frame lives in."""
    id: str
    type: str
    n: int
    prefix: tuple
    slot: int
    suffix: Optional[frozenset]
    tier: int
    filler_kind: str
    note: str = ""
    source: str = "books"
    floor: int = FRAME_FLOOR

    @property
    def key(self) -> str:
        """The frame's sort key in the shards: its prefix and a space (the untagged block's start)."""
        return " ".join(self.prefix) + " "

    @property
    def template(self) -> str:
        """The frame as a reader sees it (``very X <person noun>``)."""
        tail = ""
        if self.suffix is not None:
            tail = " <person noun>" if self.suffix == PERSON_NOUNS else " " + "|".join(sorted(self.suffix))
        return " ".join(self.prefix) + " X" + tail

    def as_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "n": self.n, "prefix": list(self.prefix), "slot": self.slot,
                "suffix": sorted(self.suffix) if self.suffix is not None else None, "tier": self.tier,
                "filler_kind": self.filler_kind, "note": self.note, "source": self.source, "floor": self.floor}


def _frame(fid: str, type_: str, prefix: Sequence[str], *, tier: int, filler_kind: str,
           suffix: Optional[Iterable[str]] = None, note: str = "") -> Frame:
    sfx = frozenset(suffix) if suffix is not None else None
    n = len(prefix) + 1 + (1 if sfx is not None else 0)
    return Frame(id=fid, type=type_, n=n, prefix=tuple(prefix), slot=len(prefix), suffix=sfx, tier=tier,
                 filler_kind=filler_kind, note=note)


def _degree(adv: str, tier: int) -> Frame:
    return _frame(f"d_{adv}", "degree", (adv,), tier=tier, filler_kind="adj", suffix=PERSON_NOUNS,
                  note=f"{adv} X <person noun>")


def _nominal(anchor: str, tier: int) -> Frame:
    art = "an" if anchor[0] in "aeiou" else "a"
    return _frame(f"n_{anchor}", "nominal", (art, anchor), tier=tier, filler_kind="noun",
                  note=f"{art} {anchor} X (X a person noun, or a noun the helper relabels)")


FRAME_BANK: tuple[Frame, ...] = (
    # degree, tier 1 (the `too` block also serves d_too_to at no extra shard)
    *(_degree(a, 1) for a in ("very", "too", "so", "rather", "quite", "extremely")),
    _frame("d_too_to", "degree", ("too",), tier=1, filler_kind="adj", suffix=("to",),
           note="too X to (the too block, free with d_too)"),
    # degree, tier 2
    *(_degree(a, 2) for a in ("utterly", "notoriously", "hopelessly", "thoroughly", "remarkably", "chronically",
                              "famously", "incurably")),
    # nominal
    *(_nominal(a, 1) for a in ("incorrigible", "inveterate", "notorious", "shameless", "hopeless", "born",
                               "confirmed", "compulsive")),
    *(_nominal(a, 2) for a in ("habitual", "chronic", "natural", "total")),
    # possessive
    _frame("p_known_for_his", "possessive", ("known", "for", "his"), tier=1, filler_kind="quality_noun",
           note="known for his X"),
    _frame("p_known_for_her", "possessive", ("known", "for", "her"), tier=1, filler_kind="quality_noun",
           note="known for her X"),
    _frame("p_man_of", "possessive", ("man", "of"), tier=1, filler_kind="quality_noun", note="man of X"),
    _frame("p_woman_of", "possessive", ("woman", "of"), tier=1, filler_kind="quality_noun", note="woman of X"),
    _frame("p_reputation_for", "possessive", ("reputation", "for"), tier=1, filler_kind="quality_noun",
           note="reputation for X"),
    _frame("p_noted_for_his", "possessive", ("noted", "for", "his"), tier=2, filler_kind="quality_noun",
           note="noted for his X"),
    _frame("p_famous_for_his", "possessive", ("famous", "for", "his"), tier=2, filler_kind="quality_noun",
           note="famous for his X"),
    # copular
    _frame("c_was_a", "copular", ("was", "a"), tier=1, filler_kind="adj", suffix=PERSON_NOUNS,
           note="was a X <person noun>"),
    _frame("c_was_an", "copular", ("was", "an"), tier=1, filler_kind="adj", suffix=PERSON_NOUNS,
           note="was an X <person noun>"),
    _frame("c_is_a", "copular", ("is", "a"), tier=2, filler_kind="adj", suffix=PERSON_NOUNS,
           note="is a X <person noun>"),
    _frame("c_seemed_a", "copular", ("seemed", "a"), tier=2, filler_kind="adj", suffix=PERSON_NOUNS,
           note="seemed a X <person noun>"),
    # tendency
    _frame("t_tendency", "tendency", ("tendency", "to", "be"), tier=1, filler_kind="adj", note="tendency to be X"),
    _frame("t_inclined", "tendency", ("inclined", "to", "be"), tier=1, filler_kind="adj", note="inclined to be X"),
    _frame("t_apt", "tendency", ("apt", "to", "be"), tier=1, filler_kind="adj", note="apt to be X"),
    # habitual
    _frame("h_he_was_always", "habitual", ("he", "was", "always"), tier=1, filler_kind="adj",
           note="he was always X"),
    _frame("h_she_was_always", "habitual", ("she", "was", "always"), tier=1, filler_kind="adj",
           note="she was always X"),
    _frame("h_he_is_always", "habitual", ("he", "is", "always"), tier=2, filler_kind="adj", note="he is always X"),
    _frame("h_she_is_always", "habitual", ("she", "is", "always"), tier=2, filler_kind="adj",
           note="she is always X"),
)
FRAME_BY_ID: dict[str, Frame] = {f.id: f for f in FRAME_BANK}


def frames_for(tier: Union[int, str] = "all", bank: Sequence[Frame] = FRAME_BANK) -> list[Frame]:
    """The frames of a tier: ``1``, ``2`` (tier 2 alone: the increment over tier 1) or ``"all"``."""
    t = str(tier).strip().lower()
    if t == "all":
        return list(bank)
    if t not in ("1", "2"):
        raise ValueError(f"--tier must be 1, 2 or all, not {tier!r}")
    return [f for f in bank if f.tier == int(t)]


def _stop_alternation() -> str:
    return "|".join(re.escape(w) for w in sorted(STOPWORDS, key=lambda w: (-len(w), w)))


def regex_pattern(frame: Frame) -> str:
    """The frame's pattern over a Books line (see :func:`regex_for`)."""
    head = re.escape(" ".join(frame.prefix)) + " "
    slot = rf"(?!(?:{_stop_alternation()})(?:[ \t]|$))(?P<filler>{TOKEN_RE})"
    tail = ""
    if frame.suffix is not None:
        alt = "|".join(re.escape(w) for w in sorted(frame.suffix, key=lambda w: (-len(w), w)))
        tail = rf" (?P<noun>{alt})"
    return "^" + head + slot + tail + r"(?=\t|$)"


_REGEX_CACHE: dict[str, re.Pattern] = {}


def regex_for(frame: Frame) -> re.Pattern:
    """A compiled pattern that matches a Books line of ``frame`` (the n-gram before the first tab must be exactly
    the frame: its prefix, a plain lowercase filler that is not a function word, and, for a frame with a suffix
    set, one of its nouns); groups ``filler`` and, with a suffix set, ``noun``."""
    pat = regex_pattern(frame)
    if pat not in _REGEX_CACHE:
        _REGEX_CACHE[pat] = re.compile(pat)
    return _REGEX_CACHE[pat]


def bank_sha256(bank: Sequence[Frame] = FRAME_BANK) -> str:
    """The sha256 of every frame's fields, the person nouns, the filler pattern, the floor and the function words the
    slot refuses: a change to any of them changes the hash."""
    doc = {"frames": [f.as_dict() for f in sorted(bank, key=lambda f: f.id)],
           "person_nouns": sorted(PERSON_NOUNS), "token_re": TOKEN_RE, "frame_floor": FRAME_FLOOR,
           "stopwords": sorted(STOPWORDS)}
    return hashlib.sha256(json.dumps(doc, sort_keys=True).encode("utf-8")).hexdigest()


__all__ = ["TYPES", "FILLER_KINDS", "TIERS", "FRAME_FLOOR", "TOKEN_RE", "PERSON_NOUNS", "Frame", "FRAME_BANK",
           "FRAME_BY_ID", "frames_for", "regex_pattern", "regex_for", "bank_sha256"]
