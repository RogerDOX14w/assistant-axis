"""The text that gets embedded for a trait or a candidate (M2/M3).

One function for both sides, by design (plan 10 addendum 2): an existing
trait is ``label: description``, a candidate ``label: gloss``, built by the
same :func:`trait_text` with the same options, so that whatever the metric
config chooses (prefix, contrast policy, length) applies to both.

Representations measured in M2 (:data:`REPRESENTATIONS`):

* ``full``: ``label: description`` as written (the plan's primary).
* ``noprefix``: the shared opener removed ("This means ", "This trait
  involves ", and a following "being X:" that repeats the label).
* ``w20``: the description cut to about 20 words (plan 15 §3.1's check).
* ``w14``: cut to about 14 words, the median length of the split filter's
  candidate glosses (launch decision 4), to tell M3 whether glosses must be
  lengthened or descriptions matched in length at embedding time.
* ``strip``: contrast clauses removed (``contrast.strip_contrast`` with the
  hand-checked cuts); descriptions without a clause are unchanged.
* ``dup`` (round 2, Roger 2026-10-01: "try concatenating two copies of the
  gloss"): the short side (a candidate gloss, or the M1 filter gloss that
  stands for one) is embedded as ``label: gloss gloss``; descriptions are
  embedded as written (so for the corpus ``dup`` equals ``full``).  The
  short side is built with :func:`represent_short`, which equals
  :func:`represent` for every other representation.

Truncation keeps the opener whole ("This means being world-shaping:" is
never cut) and cuts at a word boundary, closing with a full stop.
"""
from __future__ import annotations

import re
from typing import Mapping, Optional

from .contrast import strip_contrast

REPRESENTATIONS: dict[str, dict] = {
    "full": {},
    "noprefix": {"prefix": "strip"},
    "w20": {"words": 20},
    "w14": {"words": 14},
    "strip": {"contrast": "strip"},
    "dup": {},
}
#: Options applied only to the short side (candidate glosses), on top of :data:`REPRESENTATIONS`.
SHORT_SIDE: dict[str, dict] = {"dup": {"double": True}}

#: "This means ", "This trait involves ", "This trait manifests as ", with an
#: optional "being X:" / "having X:" / "staying X:" restatement of the label.
OPENER_RE = re.compile(r"^This (?:means|involves|trait (?:involves|manifests as))\s+"
                       r"(?:(?:being|having|staying|showing)\s+[^:.;,]{1,60}?:\s+)?", re.I)


_TAIL_WORDS = {"and", "or", "but", "nor", "by", "of", "the", "a", "an", "to", "with", "for", "in", "on", "from",
               "that", "as", "at", "into", "than", "rather", "its", "their", "one's", "while", "when", "who",
               "which", "whose", "without", "about", "over", "under", "is", "are", "be", "being", "so", "if"}


def opener(text: str) -> str:
    m = OPENER_RE.match(text or "")
    return m.group(0) if m else ""


def strip_prefix(text: str) -> str:
    """The description without its shared opener (first letter kept as written)."""
    o = opener(text)
    return text[len(o):] if o else text


def truncate_words(text: str, n: int) -> str:
    """The first ``n`` words (never fewer than the opener plus four), cut at a
    word boundary, trailing punctuation dropped, closed with a full stop.
    Texts of ``n`` words or fewer come back unchanged."""
    words = text.split()
    if len(words) <= n:
        return text
    n_open = len(opener(text).split())
    n_eff = max(n, n_open + 4)
    if len(words) <= n_eff:
        return text
    kept = words[:n_eff]
    # never end on a function word ("... observable facts, and." reads as broken)
    while len(kept) > max(n_eff - 4, n_open + 1) and re.sub(r"[^a-z']", "", kept[-1].lower()) in _TAIL_WORDS:
        kept.pop()
    out = re.sub(r"[\s,;:—–-]+$", "", " ".join(kept))
    return out if out.endswith((".", "!", "?")) else out + "."


def trait_text(label: str, description: Optional[str], *, prefix: str = "keep", contrast: str = "keep",
               cut: Optional[Mapping] = None, words: Optional[int] = None, double: bool = False) -> str:
    """``label: gloss`` under the given options.  ``cut`` is the hand-checked
    override for this description (``contrast_cuts.json`` row or
    ``contrast_cut_overrides.json`` entry); without one the mechanical rule
    applies.  A member with no description (a bare label) is just the label."""
    if prefix not in ("keep", "strip") or contrast not in ("keep", "strip"):
        raise ValueError("prefix and contrast are 'keep' or 'strip'")
    if not description:
        return label
    text = description
    if contrast == "strip":
        if cut is not None and "stripped" in cut:
            text = cut["stripped"]
        else:
            text, _ = strip_contrast(text, override=cut)
    if prefix == "strip":
        text = strip_prefix(text)
    if words:
        text = truncate_words(text, words)
    if double:
        text = f"{text} {text}"
    return f"{label}: {text}"


def candidate_text(label: str, gloss: Optional[str], **kw) -> str:
    """A candidate's embedded text: the same function as an existing trait's."""
    return trait_text(label, gloss, **kw)


def represent(label: str, description: Optional[str], representation: str, *,
              cut: Optional[Mapping] = None) -> str:
    """:func:`trait_text` under a named representation of :data:`REPRESENTATIONS`."""
    return trait_text(label, description, cut=cut, **REPRESENTATIONS[representation])


def represent_short(label: str, gloss: Optional[str], representation: str, *,
                    cut: Optional[Mapping] = None) -> str:
    """The short side (a gloss) under a named representation: as
    :func:`represent`, plus the :data:`SHORT_SIDE` options (``dup`` doubles it)."""
    opts = dict(REPRESENTATIONS[representation])
    opts.update(SHORT_SIDE.get(representation, {}))
    return trait_text(label, gloss, cut=cut, **opts)
