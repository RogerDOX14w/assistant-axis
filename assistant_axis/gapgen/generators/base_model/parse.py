"""Items out of a continuation, and their form (plan section 5, ``parse.py``; plan 03 section 3.4).

:func:`extract_items` reads the continuation the way its family's prompt left off:

* comma-list families (``list``, ``person``, ``occupation``) and ``contrast``: the first line, up to the first
  sentence end, split on commas, semicolons, "and" and "but" (prose after the list is never mined);
* ``list_gloss``: ``word: gloss`` lines, up to the first line without a colon;
* ``ai_assistant``: the numbered list (the prompt ends in ``1.``), up to the first line that is not an item;
  an item's own ``: explanation`` or `` - explanation`` becomes its gloss.

Each span is cleaned: list markers, quotes and brackets removed, a trailing parenthetical dropped, folded to
ASCII and lower-cased, leading determiners and degree words stripped ("the very kind" -> "kind", "always
willing to listen" -> "willing to listen"); a span with a digit or a non-Latin letter, a span of more than four
words, and a span of function words only are dropped.

:func:`normalize_form` applies v1's **mechanical** rule only (Roger, plan 03 section 9.4): a single ``-ness`` /
``-ity`` noun becomes its adjective when OEWN has that adjective (``stubbornness`` -> ``stubborn``,
``generosity`` -> ``generous``), else it stays, tagged ``noun``.  Every item is tagged ``adjective``, ``noun``
or ``phrase``; an unknown single word counts as adjective-like (the frequency floor and M1 decide).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from assistant_axis.gapgen.normalize import STOPWORDS

MAX_WORDS = 4
DETERMINERS = frozenset({"a", "an", "the", "his", "her", "their", "its", "my", "your", "our", "some", "this",
                         "that", "these", "those", "being"})
#: Degree and frequency words stripped from the front of a span.
DEGREE_WORDS = frozenset({"very", "extremely", "quite", "rather", "really", "so", "too", "somewhat", "fairly",
                          "incredibly", "terribly", "always", "often", "sometimes", "usually", "generally",
                          "deeply", "utterly", "totally", "completely", "truly", "most", "more"})
#: A leading conjunction left by an Oxford comma (", and fiercely loyal").
CONJUNCTIONS = frozenset({"and", "or", "but", "nor"})
COMMA_FAMILIES = ("list", "person", "occupation", "contrast")
#: Words the suffix rule must leave alone (their -ness / -ity is not a derivation of the adjective found).
SUFFIX_EXCEPTIONS = frozenset({"business", "witness", "harness", "wilderness", "city", "pity", "duty", "entity",
                               "unity", "community", "university", "variety", "society", "deity", "laity"})

_FOLD = {"œ": "oe", "æ": "ae", "ß": "ss", "ø": "o", "ł": "l"}
_SENT_END = re.compile(r"[.!?](?=\s|$)")
_SPLIT = re.compile(r"\s*[,;]\s*|\s+(?:and|but|&)\s+")
_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*•–])\s*")
_ITEM_LINE = re.compile(r"^\s*\d+[.)]\s*")
_TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")
_GLOSS_SPLIT = re.compile(r"\s*:\s+|\s+[-–—]\s+")
_WORD_OK = re.compile(r"^[a-z]+(?:['-][a-z]+)*$")


@dataclass(frozen=True)
class RawItem:
    surface: str
    gloss: Optional[str]
    position: int


@dataclass(frozen=True)
class Lexicon:
    """Adjective and noun lemmas, lower-case (OEWN in production, a fake in tests)."""
    adjectives: frozenset
    nouns: frozenset


def fold(s: str) -> str:
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def clean_span(span: str) -> Optional[str]:
    """One cleaned item, or None (see the module docstring)."""
    s = _MARKER.sub("", span.strip())
    s = s.strip(" \t\"'“”‘’`*_")
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    s = _TRAILING_PAREN.sub("", s)
    s = s.replace("’", "'").strip(" \t\"'“”‘’`()[]{}.!?:;")
    s = " ".join(fold(s).lower().split())
    if not s:
        return None
    words = s.split()
    while words and (words[0] in DETERMINERS or words[0] in DEGREE_WORDS or words[0] in CONJUNCTIONS):
        words = words[1:]
    if not words or len(words) > MAX_WORDS:
        return None
    if not all(_WORD_OK.match(w) for w in words):
        return None              # digits, non-Latin letters, stray punctuation
    if all(w in STOPWORDS for w in words):
        return None
    return " ".join(words)


def _first_sentence(text: str) -> str:
    line = text.lstrip(" ").split("\n", 1)[0]
    m = _SENT_END.search(line)
    return line[:m.start()] if m else line


def _split_gloss(span: str) -> tuple[str, Optional[str]]:
    parts = _GLOSS_SPLIT.split(span.strip(), maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return parts[0], parts[1].strip().rstrip(".")
    return span, None


def extract_items(text: str, family: str) -> list[RawItem]:
    """The candidate items of one continuation (see the module docstring)."""
    out: list[RawItem] = []

    def add(span: str, gloss: Optional[str] = None) -> None:
        s = clean_span(span)
        if s is not None:
            out.append(RawItem(surface=s, gloss=gloss[:200] if gloss else None, position=len(out)))

    if family in COMMA_FAMILIES:
        for span in _SPLIT.split(_first_sentence(text)):
            add(span)
    elif family == "list_gloss":
        for line in text.strip("\n").split("\n"):
            if ":" not in line:
                break
            word, _, gloss = line.partition(":")
            add(word, gloss.strip() or None)
    elif family == "ai_assistant":
        for i, line in enumerate(text.split("\n")):
            if i > 0 and not _ITEM_LINE.match(line):
                break
            word, gloss = _split_gloss(_ITEM_LINE.sub("", line))
            add(word, gloss)
    else:
        raise ValueError(f"unknown family {family!r}")
    return out


def _suffix_candidates(w: str) -> list[str]:
    if w in SUFFIX_EXCEPTIONS:
        return []
    if w.endswith("ness") and len(w) > 6:
        c = [w[:-5] + "y"] if w.endswith("iness") else []
        return c + [w[:-4]]
    if w.endswith("ity") and len(w) > 5:
        c = []
        if w.endswith("osity"):
            c.append(w[:-5] + "ous")
        if w.endswith("bility"):
            c.append(w[:-6] + "ble")
        return c + [w[:-3], w[:-3] + "e"]
    return []


def normalize_form(surface: str, *, lexicon: Lexicon) -> tuple[str, str, Optional[str]]:
    """``(surface, form, normalized_from)`` (see the module docstring)."""
    s = surface.strip().lower()
    if " " in s:
        return s, ("adjective" if s in lexicon.adjectives else "phrase"), None
    cands = _suffix_candidates(s)
    for c in cands:
        if c in lexicon.adjectives:
            return c, "adjective", s
    if cands:
        return s, "noun", None
    if s in lexicon.adjectives:
        return s, "adjective", None
    if s in lexicon.nouns:
        return s, "noun", None
    return s, "adjective", None
