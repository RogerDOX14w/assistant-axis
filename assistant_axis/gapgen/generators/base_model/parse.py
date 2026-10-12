"""Items out of a continuation, and their form (plan section 5, ``parse.py``; plan 03 section 3.4).

:func:`extract_items` reads the continuation the way its family's prompt left off:

* comma-list families (``list``, ``person``, ``occupation``) and ``contrast``: the first line, up to the first
  sentence end, split on commas, semicolons, "and" and "but" (prose after the list is never mined);
* ``list_gloss``: ``word: gloss`` lines, up to the first line without a colon;
* ``ai_assistant``: the numbered list (the prompt ends in ``1.``), up to the first line that is not an item;
  an item's own ``: explanation`` or `` - explanation`` becomes its gloss.

Each span is cleaned: list markers, quotes and brackets removed, a trailing parenthetical dropped, folded to
ASCII and lower-cased, leading determiners, degree and frequency words and a leading ``be`` stripped ("the very
kind" -> "kind", "always willing to listen" -> "willing to listen", "be sarcastic" -> "sarcastic",
"occasionally robotic" -> "robotic"; words that carry meaning, such as ``not``, ``never``, ``overly`` and
``highly``, stay); a list ending (``etc``, ``others``) is not an item, and a trailing ``etc`` is cut; a span
with a digit or a non-Latin letter, a span of more than four words, and a span of function words only are
dropped.  An ``ai_assistant`` item of at most four words is split on "and" ("unresponsive and dismissive" ->
two items, which carry no gloss: the explanation was written for the pair); a longer item, or one holding a
comma, is prose and is still dropped whole.  The leading-word, list-ending and
split rules were added after gate audit 3 (``reports/code_review_2026-10-12/gate_audits/base_model_table.md``
section 8, proposal 4; Roger accepted it on 2026-10-12).

:func:`normalize_form` applies **mechanical** rules only (Roger, plan 03 section 9.4), each gated on OEWN
having the result, so a fold never invents a word:

* a single noun of disposition becomes its adjective: ``-ness`` / ``-ity`` (``stubbornness`` -> ``stubborn``,
  ``generosity`` -> ``generous``; else it stays, tagged ``noun``) and, since gate audit 3, ``-acity`` /
  ``-ocity`` -> ``-acious`` / ``-ocious`` (``pugnacity`` -> ``pugnacious``), ``-ence`` / ``-ency`` /
  ``-ance`` / ``-ancy`` -> ``-ent`` / ``-ant`` (``patience`` -> ``patient``), ``-ism`` -> ``-istic`` / ``-ist``
  and ``-icism`` -> ``-ical`` / ``-ic`` (``optimism`` -> ``optimistic``, ``cynicism`` -> ``cynical``), with the
  nouns whose adjective is another sense left alone (:data:`SUFFIX_EXCEPTIONS`);
* a single ``-ly`` adverb that OEWN does not list as an adjective or a noun becomes its adjective
  (``incompetently`` -> ``incompetent``, ``bawdily`` -> ``bawdy``, ``gently`` -> ``gentle``);
* British spellings become US ones (the entity-naming rule: US English), word by word: ``-our`` -> ``-or``,
  ``-ise`` / ``-isation`` -> ``-ize`` / ``-ization``, ``-tre`` -> ``-ter``, ``-lled`` / ``-lling`` /
  ``-ller`` -> one ``l``, ``-ilful`` -> ``-illful``, ``-eable`` -> ``-able``, ``judgement`` -> ``judgment``,
  ``sceptic`` -> ``skeptic`` (``organised`` -> ``organized``, ``self-centred`` -> ``self-centered``,
  ``likeable`` -> ``likable``).

Every item is tagged ``adjective``, ``noun`` or ``phrase``; an unknown single word counts as adjective-like (the
frequency floor and M1 decide).  :func:`normalize_form_kind` also says which rule folded the item.
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
#: Degree and frequency words stripped from the front of a span.  Words that change the meaning stay:
#: ``not``, ``never``, ``rarely``, ``overly``, ``highly`` ("highly strung").  The frequency adverbs from
#: ``occasionally`` on were added after gate audit 3 ("occasionally robotic" reached the table).
DEGREE_WORDS = frozenset({"very", "extremely", "quite", "rather", "really", "so", "too", "somewhat", "fairly",
                          "incredibly", "terribly", "always", "often", "sometimes", "usually", "generally",
                          "deeply", "utterly", "totally", "completely", "truly", "most", "more", "also", "all",
                          "just", "even", "still", "simply",
                          "occasionally", "frequently", "typically", "normally", "mostly", "constantly",
                          "perpetually", "invariably", "habitually", "regularly", "slightly"})
#: Degree words stripped from the front only when another word follows that is not ``of`` ("a little shy" ->
#: "shy", "a bit lazy" -> "lazy"; "bit of a recluse" stays a phrase).
SOFT_DEGREE_WORDS = frozenset({"bit", "little"})
#: A leading ``be`` (the ``ai_assistant`` family's "1. be sarcastic", "2. be helpful"; gate audit 3).
LEADING_VERBS = frozenset({"be"})
#: A list ending is not an item ("kind, generous, etc." gave the row ``etc`` at count 16, which cost an M1 call).
LIST_ENDINGS = frozenset({"etc", "etcetera", "et cetera", "others", "so on", "so forth"})
#: A span holding one of these is a clause, not a candidate ("body has a wrist", "can be quite annoying").
CLAUSE_WORDS = frozenset({"is", "are", "was", "were", "has", "have", "had", "can", "could", "will", "would",
                          "does", "do", "did", "should", "may", "might", "must", "i", "you", "he", "she", "it",
                          "we", "they"})
#: A leading conjunction left by an Oxford comma (", and fiercely loyal").
CONJUNCTIONS = frozenset({"and", "or", "but", "nor"})
COMMA_FAMILIES = ("list", "person", "occupation", "contrast")
#: Words the suffix rules must leave alone: their suffix is not a derivation of the adjective found, or the
#: adjective is another sense (``presence`` is not being ``present``, ``capacity`` not being ``capacious``).
SUFFIX_EXCEPTIONS = frozenset({"business", "witness", "harness", "wilderness", "city", "pity", "duty", "entity",
                               "unity", "community", "university", "variety", "society", "deity", "laity",
                               "presence", "absence", "evidence", "difference", "instance", "importance",
                               "currency", "emergency", "frequency", "capacity", "residence", "conference",
                               "reference", "sentence", "substance", "consequence", "occurrence", "agency",
                               "velocity", "atrocity", "criticism", "audience", "experience", "science"})

_FOLD = {"œ": "oe", "æ": "ae", "ß": "ss", "ø": "o", "ł": "l"}
_SENT_END = re.compile(r"[.!?](?=\s|$)")
_SPLIT = re.compile(r"\s*[,;]\s*|\s+(?:and|but|&)\s+")
#: An ``ai_assistant`` item is split on "and" only (gate audit 3: 35 compound rows): a comma in an item usually
#: starts an explanation ("efficient, allowing for continuous operation"), whose fragments are not candidates.
_AND_SPLIT = re.compile(r"\s+(?:and|&)\s+")
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


def _strippable(words: list[str]) -> bool:
    """True when the first word of a span is a leading word :func:`clean_span` removes."""
    w = words[0]
    if w in DETERMINERS or w in CONJUNCTIONS or w in LEADING_VERBS:
        return True
    # a degree word before "of" heads the phrase ("somewhat of a dreamer", "bit of a recluse"): it stays
    of_next = len(words) > 1 and words[1] == "of"
    if w in DEGREE_WORDS:
        return not of_next
    return w in SOFT_DEGREE_WORDS and len(words) > 1 and not of_next


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
    while words and words[-1] in ("etc", "etcetera"):        # "kind etc." -> "kind"; "etc." alone -> nothing
        words = words[:-1]
    while words and _strippable(words):
        if " ".join(words) in LIST_ENDINGS:
            return None
        words = words[1:]
    if " ".join(words) in LIST_ENDINGS:
        return None
    if not words or len(words) > MAX_WORDS:
        return None
    if any(w in CLAUSE_WORDS for w in words):
        return None
    if not all(_WORD_OK.match(w) for w in words):
        return None              # digits, non-Latin letters, stray punctuation
    if all(w in STOPWORDS for w in words):
        return None
    return " ".join(words)


def _first_sentence(text: str) -> tuple[str, bool]:
    """The first line up to its first sentence end, and whether it ended (sentence end or line break) rather
    than running into the end of the text."""
    stripped = text.lstrip(" ")
    line, nl, _ = stripped.partition("\n")
    m = _SENT_END.search(line)
    return (line[:m.start()], True) if m else (line, bool(nl))


def _split_gloss(span: str) -> tuple[str, Optional[str]]:
    parts = _GLOSS_SPLIT.split(span.strip(), maxsplit=1)
    if len(parts) == 2 and parts[1].strip():
        return parts[0], parts[1].strip().rstrip(".")
    return span, None


def extract_items(text: str, family: str, *, truncated: bool = False) -> list[RawItem]:
    """The candidate items of one continuation (see the module docstring).  ``truncated``: the continuation hit
    the token cap, so a last span that does not end on a delimiter is cut off mid-word and is dropped."""
    out: list[RawItem] = []

    def add(span: str, gloss: Optional[str] = None) -> None:
        s = clean_span(span)
        if s is not None:
            out.append(RawItem(surface=s, gloss=gloss[:200] if gloss else None, position=len(out)))

    open_end = truncated and not text.endswith("\n")
    if family in COMMA_FAMILIES:
        part, ended = _first_sentence(text)
        spans = _SPLIT.split(part)
        if truncated and not ended and not part.rstrip().endswith((",", ";")):
            spans = spans[:-1]
        for span in spans:
            add(span)
    elif family == "list_gloss":
        lines = text.strip("\n").split("\n")
        for line in lines[:-1] if open_end else lines:
            if ":" not in line:
                break
            word, _, gloss = line.partition(":")
            add(word, gloss.strip() or None)
    elif family == "ai_assistant":
        lines = text.split("\n")
        for i, line in enumerate(lines[:-1] if open_end else lines):
            if i > 0 and not _ITEM_LINE.match(line):
                break
            word, gloss = _split_gloss(_ITEM_LINE.sub("", line))
            # only an item short enough to be a row splits (the audit's compound rows); a longer one is prose
            # whose fragments ("fast processing speed", "accurate information to users") are not candidates
            parts = [p for p in _AND_SPLIT.split(word) if p.strip()] if len(word.split()) <= MAX_WORDS else [word]
            if len(parts) > 1:          # "unresponsive and dismissive": two items; the gloss was for the pair
                for p in parts:
                    add(p)
            else:
                add(word, gloss)
    else:
        raise ValueError(f"unknown family {family!r}")
    return out


def _suffix_candidates(w: str) -> list[str]:
    """The ``-ness`` / ``-ity`` rule: a word with one of these suffixes is tagged ``noun`` when no candidate is
    an OEWN adjective."""
    if w in SUFFIX_EXCEPTIONS:
        return []
    if w.endswith("ness") and len(w) > 6:
        c = [w[:-5] + "y"] if w.endswith("iness") else []
        return c + [w[:-4]]
    if w.endswith("ity") and len(w) > 5:
        c = []
        if w.endswith("osity"):
            c.append(w[:-5] + "ous")
        if w.endswith(("acity", "ocity")):            # pugnacity -> pugnacious, ferocity -> ferocious
            c.append(w[:-3] + "ious")
        if w.endswith("bility"):
            c.append(w[:-6] + "ble")
        return c + [w[:-3], w[:-3] + "e"]
    return []


#: Further nouns of disposition (gate audit 3): suffix -> adjective endings tried in order.  ``-icism`` comes
#: before ``-ism``.  Unlike ``-ness`` / ``-ity``, a word none of whose candidates is an adjective keeps its
#: ordinary tag (``science`` is a noun because OEWN says so, not because of its ending).
NOUN_SUFFIXES = (("ence", ("ent",)), ("ency", ("ent",)), ("ance", ("ant",)), ("ancy", ("ant",)),
                 ("icism", ("ical", "ic")), ("ism", ("istic", "ist")))


def _noun_suffix_candidates(w: str) -> list[str]:
    if w in SUFFIX_EXCEPTIONS:
        return []
    for suf, ends in NOUN_SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return [w[:-len(suf)] + e for e in ends]
    return []


#: ``-ly`` adverbs whose adjective is another sense (``overly`` is not ``over``, ``hardly`` not ``hard``).
ADVERB_EXCEPTIONS = frozenset({"overly", "rarely", "hardly", "barely", "nearly", "lately", "shortly", "highly",
                               "fairly", "merely", "scarcely", "really", "presently", "surely", "simply",
                               "purely", "largely", "greatly", "widely", "closely"})


def _adverb_candidates(w: str) -> list[str]:
    """Adjectives an ``-ly`` adverb may come from, most specific first (``bawdily`` -> ``bawdy``,
    ``frantically`` -> ``frantic``, ``incompetently`` -> ``incompetent``, ``gently`` -> ``gentle``,
    ``dully`` -> ``dull``, ``truly`` -> ``true``)."""
    if len(w) < 5 or not w.endswith("ly") or w in ADVERB_EXCEPTIONS:
        return []
    c = []
    if w.endswith("ily"):
        c.append(w[:-3] + "y")
    c.append(w[:-2])
    if w.endswith("ically"):
        c.append(w[:-4])
    if w[-3] not in "aeiou":
        c += [w[:-1] + "e", w[:-1]]
    c.append(w[:-2] + "e")
    return list(dict.fromkeys(c))


#: British -> US spelling rules for one word (a space- or hyphen-separated part), applied in order; a fold is
#: kept only when OEWN has the result (:func:`us_spelling`).  The entity-naming rule: corpus labels are US
#: English, and the pilot's count 2-7 band held eight British variants of registry words (gate audit 3).
_UK_US = (
    (re.compile(r"(?<=[a-z]{3})our(?=(?:ed|ful|fully|less|able|ably|ing|ite|ites|s|ly|al|ally|hood|er|ers)?$)"),
     "or"),                                                                             # humour, colourful
    (re.compile(r"is(?=(?:e|ed|es|ing|ation|ations)$)"), "iz"),                        # organised, civilisation
    (re.compile(r"tre$"), "ter"),                                                      # centre
    (re.compile(r"tres$"), "ters"),
    (re.compile(r"tred$"), "tered"),                                                   # centred, self-centred
    (re.compile(r"(?<=[aeiou])ll(?=(?:ed|ing|er|ers)$)"), "l"),                        # travelled, untrammelled
    (re.compile(r"ilful(?=(?:ly|ness)?$)"), "illful"),                                 # skilful, wilful
    (re.compile(r"eable$"), "able"),                                                   # likeable, unshakeable
    (re.compile(r"dgement"), "dgment"),                                                # judgement, judgemental
    (re.compile(r"^sceptic"), "skeptic"),                                              # sceptical, scepticism
)
#: Words the spelling rules would turn into another word OEWN has.
UK_US_EXCEPTIONS = frozenset({"outre"})


def _in_lexicon(w: str, lexicon: Lexicon) -> bool:
    return w in lexicon.adjectives or w in lexicon.nouns


def us_spelling(s: str, *, lexicon: Lexicon) -> str:
    """``s`` with British spellings made US (:data:`_UK_US`), or ``s`` unchanged.  The fold is kept when OEWN
    has the whole result (``good-humored``) or every changed word (``well-organized`` from ``organized``)."""
    parts = re.split(r"([ -])", s)
    out, changed = [], []
    for p in parts:
        u = p
        if p not in (" ", "-") and p not in UK_US_EXCEPTIONS:
            for rx, rep in _UK_US:
                u = rx.sub(rep, u)
        if u != p:
            changed.append(u)
        out.append(u)
    if not changed:
        return s
    us = "".join(out)
    return us if _in_lexicon(us, lexicon) or all(_in_lexicon(u, lexicon) for u in changed) else s


def normalize_form_kind(surface: str, *, lexicon: Lexicon) -> tuple[str, str, Optional[str], Optional[str]]:
    """``(surface, form, normalized_from, kind)``: :func:`normalize_form` plus which rule folded the item
    (``noun_suffix``, ``adverb``, ``us_spelling``, two joined by ``+``; None when nothing changed)."""
    s = surface.strip().lower()
    us = us_spelling(s, lexicon=lexicon)
    spelled = us != s

    def done(out: str, form: str, kind: Optional[str] = None):
        kinds = "+".join(k for k in (("us_spelling" if spelled else None), kind) if k) or None
        return out, form, (s if out != s else None), kinds

    if " " in us:
        return done(us, "adjective" if us in lexicon.adjectives else "phrase")
    cands = _suffix_candidates(us)
    for c in cands:
        if c in lexicon.adjectives:
            return done(c, "adjective", "noun_suffix")
    if cands:
        return done(us, "noun")
    if us in lexicon.adjectives:
        return done(us, "adjective")
    for c in _noun_suffix_candidates(us):
        if c in lexicon.adjectives:
            return done(c, "adjective", "noun_suffix")
    if us in lexicon.nouns:
        return done(us, "noun")
    for c in _adverb_candidates(us):
        if c in lexicon.adjectives:
            return done(c, "adjective", "adverb")
    return done(us, "adjective")


def normalize_form(surface: str, *, lexicon: Lexicon) -> tuple[str, str, Optional[str]]:
    """``(surface, form, normalized_from)`` (see the module docstring)."""
    return normalize_form_kind(surface, lexicon=lexicon)[:3]
