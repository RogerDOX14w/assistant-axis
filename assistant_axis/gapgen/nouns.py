"""The shared noun-to-adjective relabel helper (``reports/trait_gap_generation/coding_plan_noun_normalization.md``).

The corpus prefers an adjective (pedantic, cowardly) to a noun of disposition (pedant, coward), because a persona is
prompted "You are <label>".  :func:`relabel` proposes the adjective *sibling* of a single-word noun, never a
replacement: the platform (:func:`assistant_axis.gapgen.registry.submit_candidates`) submits the noun as the
generator emitted it and adds the adjective as a second candidate of the same generator and run, linked both ways by
the ``relabel`` block (:func:`relabel_blocks`).  A role noun is untouched for the same reason: priest and pedant
look alike to a lexicon, and M1 tells them apart.

Mechanical rules only, each gated on Open English WordNet (OEWN) having the result, so a fold never invents a word;
British spellings fold to US.  The rule, in this order:

1. a surface with a space: ``phrase``;
2. the lookup forms (as given, lower case, hyphen and space); none in OEWN: ``not_in_oewn``;
3. any adjective sense: ``has_adjective_sense`` (atheist, feminist, bully: the label is valid as it is);
4. no noun sense: ``not_a_noun``;
5. the base model's suffix fold (:func:`normalize_form_kind`: -ness, -ity, -ence, -ism, ...) gives an OEWN
   adjective: rule ``suffix:<kind>`` (stubbornness to stubborn);
6. OEWN's derivation link from a sense in a person or quality lexicographer file (:data:`PERSON_LEXFILES`,
   :data:`QUALITY_LEXFILES`; the gate refuses rat to ratty, bog to boggy), adjectives only, a person sense first,
   then by Zipf; a lemma under :data:`FLOOR_ZIPF` gives way to the synset mate sharing its first four letters with
   the highest Zipf (childly to childlike: rule ``derivation+spelling``); rule ``derivation``;
7. the suffix rules of the noun's lexicographer-file class (:data:`PERSON_SUFFIX_RULES`,
   :data:`QUALITY_SUFFIX_RULES`): rule ``suffix:-<removed>+<added>`` (``suffix:-ist+istic``, ``suffix:+ish``,
   ``suffix:-ty+t``);
8. otherwise ``person_no_adjective``, ``quality_no_adjective`` or ``other_noun`` (the noun is submitted as it is and
   M1 decides).

Steps 6 and 7 share two gates: the adjective is not a pure pertainym (every adjective sense's definition
matches :data:`PERTAINYM_RE`: doctor to doctoral is ``pertainym_only``) and clears the platform's Zipf floor
(``below_floor``).  A candidate that fails a gate gives way to the next; the first failure is the reason when none
passes.  A noun in :data:`SUFFIX_EXCEPTIONS` (personality, reality: the adjective is another sense) skips steps 6
and 7 too.  Only the derivation link's lexicographer-file gate checks the sense; every suffix rule's route reads
"sense not checked" on the review card (:func:`route_text`; Roger, decision 2 (c), 2026-10-14, which also admitted
the +y and +ly endings).

The mechanical rules of the base model's parser (:func:`normalize_form` and its tables) live here since
2026-10-14; ``generators/base_model/parse.py`` re-exports them under the same names.

A change to any rule table changes :func:`rules_sha256`; bump :data:`HELPER_VERSION` and add a row to
:data:`RULES_HISTORY` (``test_gapgen_nouns.py`` pins it).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Collection, Iterable, Mapping, Optional, Protocol, Sequence, Union

from .freq import HARD_REJECT_BELOW

#: The helper's version, stamped on every ``relabel`` block.  A rule change bumps it (see :data:`RULES_HISTORY`).
HELPER_VERSION = 1
#: The OEWN lexicon the helper reads (``wordnet.OEWN_LEXICON``; not imported, so that this module never imports
#: ``wn``).
OEWN_LEXICON = "oewn:2024"
FLOOR_ZIPF = HARD_REJECT_BELOW
ADJ_POS = ("a", "s")

# --------------------------------------------------------------------------- the base model's mechanical rules

@dataclass(frozen=True)
class Lexicon:
    """Adjective and noun lemmas, lower-case (OEWN in production, a fake in tests)."""
    adjectives: frozenset
    nouns: frozenset


#: Words the suffix rules must leave alone: their suffix is not a derivation of the adjective found, or the
#: adjective is another sense (``presence`` is not being ``present``, ``capacity`` not being ``capacious``).  The
#: ``-ity`` sense-drift words (personality is not being personal) were added on 2026-10-14 (noun normalization
#: plan, section 5); the relabel helper also skips OEWN's derivation link for every word here.  The second row of
#: -ity words (majority is not being major) came from the Fable review the same day, before any block was written;
#: ability -> able, security -> secure and possibility -> possible keep the sense and stay folded.
SUFFIX_EXCEPTIONS = frozenset({"business", "witness", "harness", "wilderness", "city", "pity", "duty", "entity",
                               "unity", "community", "university", "variety", "society", "deity", "laity",
                               "presence", "absence", "evidence", "difference", "instance", "importance",
                               "currency", "emergency", "frequency", "capacity", "residence", "conference",
                               "reference", "sentence", "substance", "consequence", "occurrence", "agency",
                               "velocity", "atrocity", "criticism", "audience", "experience", "science",
                               "personality", "reality", "mentality", "nationality", "sexuality", "individuality",
                               "actuality", "speciality", "locality", "totality", "legality",
                               "majority", "minority", "priority", "gravity", "activity", "electricity"})


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
    """``(surface, form, normalized_from)``: a single noun of disposition folded to its adjective (-ness, -ity,
    -ence, -ism, ...), an ``-ly`` adverb to its adjective, British spellings to US, each only where OEWN has the
    result; every item tagged ``adjective``, ``noun`` or ``phrase`` (the base model's parser; see
    ``generators/base_model/parse.py``)."""
    return normalize_form_kind(surface, lexicon=lexicon)[:3]


# --------------------------------------------------------------------------- the relabel helper's tables

#: Lexicographer files whose senses name a kind of person, or a quality (the derivation link's gate).
PERSON_LEXFILES = frozenset({"noun.person"})
QUALITY_LEXFILES = frozenset({"noun.attribute", "noun.feeling", "noun.cognition"})
#: Person-noun endings OEWN's derivation link misses: ``(removed, (added, ...))``, first match whose result is an
#: OEWN adjective that clears the gates.  ``+y`` and ``+ly``: decision 2 (c), Roger 2026-10-14 (slipper to slippery;
#: about 40% right by the plan's reading, every one judged by M1 and M3 on its own merits).
PERSON_SUFFIX_RULES = (("ist", ("istic",)), ("ite", ("itical",)), ("vert", ("verted",)), ("ot", ("oted",)),
                       ("", ("ish", "y", "ly")))
#: Quality-noun endings (honesty to honest, loyalty to loyal, grace to graceful).
QUALITY_SUFFIX_RULES = (("ty", ("t", "")), ("cy", ("te",)), ("", ("ful", "ous")))
#: A pure "of or relating to" adjective (doctoral, editorial): not a disposition.  Matched at the start of a
#: definition, after an optional domain label in parentheses.
PERTAINYM_RE = re.compile(r"^\s*(?:\([^)]*\)\s*)?(?:of or (?:relating|pertaining|belonging) to|relating to|"
                          r"pertaining to|belonging to|used (?:by|for))\b", re.IGNORECASE)

REASONS = ("phrase", "not_in_oewn", "has_adjective_sense", "not_a_noun", "person_no_adjective",
           "quality_no_adjective", "other_noun", "pertainym_only", "below_floor")

#: :data:`HELPER_VERSION` -> :func:`rules_sha256` of its tables.  Append only.
RULES_HISTORY: dict[int, str] = {
    1: "bae02bb9af934e7d9b090f4e58ca7dd50a85c01ce5cd40c90f4ba4807e3c870d",  # re-pinned 2026-10-14 (review S4, -ity exceptions) before any block was written
}


def rules_sha256() -> str:
    """The sha256 of every table the helper reads (a change here bumps :data:`HELPER_VERSION`)."""
    tables = {"person_lexfiles": sorted(PERSON_LEXFILES), "quality_lexfiles": sorted(QUALITY_LEXFILES),
              "person_suffix_rules": PERSON_SUFFIX_RULES, "quality_suffix_rules": QUALITY_SUFFIX_RULES,
              "pertainym_re": PERTAINYM_RE.pattern, "floor_zipf": FLOOR_ZIPF,
              "suffix_exceptions": sorted(SUFFIX_EXCEPTIONS), "noun_suffixes": NOUN_SUFFIXES,
              "uk_us": [(rx.pattern, rep) for rx, rep in _UK_US], "uk_us_exceptions": sorted(UK_US_EXCEPTIONS)}
    return hashlib.sha256(json.dumps(tables, sort_keys=True).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- lookups

@dataclass(frozen=True)
class Derivation:
    """One derivation link from a noun sense to an adjective sense."""
    adjective: str
    lexfile: str            # the noun sense's lexicographer file
    definition: str         # the adjective sense's definition (cleaned)


class NounLookups(Protocol):
    def pos(self, form: str) -> list[str]: ...
    def lexfiles(self, form: str) -> set[str]: ...
    def derivations(self, form: str) -> list[Derivation]: ...
    def adjective_definitions(self, adj: str) -> list[str]: ...
    def synset_mates(self, adj: str) -> set[str]: ...
    def zipf(self, word: str) -> float: ...
    def lexicon(self) -> Lexicon: ...


def _clean_definition(text: str) -> str:
    """The definition up to its first semicolon (OEWN appends usage notes after one)."""
    return " ".join(str(text or "").split(";", 1)[0].split()).strip()


class FakeLookups:
    """Lookups from dicts, for tests.  ``pos``: form -> parts of speech; ``lexfiles``: noun form -> its senses'
    lexicographer files; ``derivations``: noun form -> :class:`Derivation`; ``definitions``: adjective -> its
    senses' definitions; ``mates``: adjective -> its synsets' lemmas; ``zipf``: word -> Zipf (``default_zipf``
    otherwise).  A form is looked up as given, then lower-cased."""

    def __init__(self, *, pos: Optional[Mapping[str, Sequence[str]]] = None,
                 lexfiles: Optional[Mapping[str, Collection[str]]] = None,
                 derivations: Optional[Mapping[str, Sequence[Derivation]]] = None,
                 definitions: Optional[Mapping[str, Sequence[str]]] = None,
                 mates: Optional[Mapping[str, Collection[str]]] = None,
                 zipf: Optional[Mapping[str, float]] = None, default_zipf: float = 3.0):
        self._pos, self._lexfiles, self._derivations = dict(pos or {}), dict(lexfiles or {}), dict(derivations or {})
        self._definitions, self._mates, self._zipf = dict(definitions or {}), dict(mates or {}), dict(zipf or {})
        self.default_zipf = default_zipf
        self._lexicon = Lexicon(
            adjectives=frozenset(w.lower() for w, p in self._pos.items() if set(p) & set(ADJ_POS)),
            nouns=frozenset(w.lower() for w, p in self._pos.items() if "n" in p))

    @staticmethod
    def _get(d: Mapping, form: str):
        return d.get(form) or d.get(form.lower())

    def pos(self, form: str) -> list[str]:
        return list(self._get(self._pos, form) or [])

    def lexfiles(self, form: str) -> set[str]:
        return set(self._get(self._lexfiles, form) or ())

    def derivations(self, form: str) -> list[Derivation]:
        return list(self._get(self._derivations, form) or [])

    def adjective_definitions(self, adj: str) -> list[str]:
        return list(self._definitions.get(adj) or [])

    def synset_mates(self, adj: str) -> set[str]:
        return set(self._mates.get(adj) or ())

    def zipf(self, word: str) -> float:
        return float(self._zipf.get(word, self.default_zipf))

    def lexicon(self) -> Lexicon:
        return self._lexicon


class OewnLookups:
    """The real lookups: OEWN through the ``wn`` handle (:func:`assistant_axis.gapgen.wordnet.oewn`), Zipf through
    ``wordfreq``.  The adjective and noun lemma sets are built once per process and wordnet (:meth:`default` gives
    the process's shared instance); every lookup is cached."""

    _SHARED: dict[int, "OewnLookups"] = {}

    def __init__(self, wordnet=None, *, zipf_fn=None):
        if wordnet is None:
            from .wordnet import oewn
            wordnet = oewn()
        self.w = wordnet
        self._zipf_fn = zipf_fn
        self._lex: Optional[Lexicon] = None
        self._cache: dict[tuple[str, str], object] = {}

    @classmethod
    def default(cls) -> "OewnLookups":
        """The process's shared instance over the platform's OEWN handle."""
        from .wordnet import oewn
        w = oewn()
        if id(w) not in cls._SHARED:
            cls._SHARED[id(w)] = cls(w)
        return cls._SHARED[id(w)]

    def _memo(self, kind: str, key: str, fn):
        k = (kind, key)
        if k not in self._cache:
            self._cache[k] = fn()
        return self._cache[k]

    def _words(self, form: str) -> list:
        return self._memo("words", form, lambda: list(self.w.words(form)))

    def pos(self, form: str) -> list[str]:
        return sorted({x.pos for x in self._words(form)})

    def lexfiles(self, form: str) -> set[str]:
        return {s.synset().lexfile() for x in self._nouns(form) for s in x.senses()}

    def derivations(self, form: str) -> list[Derivation]:
        def build():
            out = []
            for x in self._nouns(form):
                for s in x.senses():
                    lf = s.synset().lexfile()
                    for d in s.relations().get("derivation", []):
                        dw = d.word()
                        if dw.pos in ADJ_POS:
                            out.append(Derivation(dw.lemma(), lf, _clean_definition(d.synset().definition())))
            return out
        return self._memo("derivations", form, build)

    def _nouns(self, form: str) -> list:
        """The noun words whose lemma is ``form`` itself: ``wn.words("hill")`` also returns the proper noun "Hill"
        (``noun.person``), which would make hill a person noun for the +y rule (review S4, 2026-10-14)."""
        return [x for x in self._words(form) if x.pos == "n" and x.lemma() == form]

    def _adj_synsets(self, adj: str) -> list:
        return [s.synset() for x in self._words(adj) if x.pos in ADJ_POS and x.lemma() == adj for s in x.senses()]

    def adjective_definitions(self, adj: str) -> list[str]:
        return [_clean_definition(syn.definition()) for syn in self._adj_synsets(adj)]

    def synset_mates(self, adj: str) -> set[str]:
        return {lem for syn in self._adj_synsets(adj) for lem in syn.lemmas()}

    def zipf(self, word: str) -> float:
        if self._zipf_fn is None:
            from wordfreq import zipf_frequency
            self._zipf_fn = lambda t: float(zipf_frequency(t, "en"))
        return self._memo("zipf", word, lambda: round(self._zipf_fn(word), 2))

    def lexicon(self) -> Lexicon:
        if self._lex is None:
            self._lex = Lexicon(
                adjectives=frozenset(x.lemma().lower() for pos in ADJ_POS for x in self.w.words(pos=pos)),
                nouns=frozenset(x.lemma().lower() for x in self.w.words(pos="n")))
        return self._lex


# --------------------------------------------------------------------------- the rule

@dataclass(frozen=True)
class Relabel:
    """The adjective sibling of a noun (:func:`relabel`)."""
    surface: str
    adjective: str
    rule: str
    lexfile: Optional[str]
    definition: Optional[str]
    zipf: float
    helper_version: int = HELPER_VERSION


@dataclass(frozen=True)
class NoRelabel:
    surface: str
    reason: str             # one of REASONS


def _lookup_forms(surface: str) -> list[str]:
    s = " ".join(str(surface).strip().split())
    forms = [s, s.lower()]
    if "-" in s:
        forms.append(s.lower().replace("-", " "))
    return list(dict.fromkeys(f for f in forms if f))


def is_pertainym(adj: str, *, lookups: NounLookups) -> bool:
    """Every adjective sense of ``adj`` is a pure "of or relating to" sense (:data:`PERTAINYM_RE`); False when OEWN
    gives no definition."""
    defs = [d for d in lookups.adjective_definitions(adj) if d]
    return bool(defs) and all(PERTAINYM_RE.search(d) for d in defs)


def _best_definition(adj: str, lookups: NounLookups) -> Optional[str]:
    """The adjective's person-descriptive sense, as the censuses' gloss hint picks it, a pertainym last."""
    from .generators.censuses.glosshint import Sense, person_sense
    defs = [d for d in lookups.adjective_definitions(adj) if d]
    defs = [d for d in defs if not PERTAINYM_RE.search(d)] + [d for d in defs if PERTAINYM_RE.search(d)]
    h = person_sense([Sense(d, "a") for d in defs])
    return h.definition if h else None


def _rule_name(removed: str, added: str) -> str:
    return "suffix:" + (f"-{removed}" if removed else "") + (f"+{added}" if added else "")


def relabel(surface: str, *, lookups: NounLookups) -> Union[Relabel, NoRelabel]:
    """The adjective sibling of a single-word noun, or why there is none (see the module docstring)."""
    s = " ".join(str(surface).strip().split())
    if " " in s:
        return NoRelabel(surface, "phrase")
    form = next((f for f in _lookup_forms(s) if lookups.pos(f)), None)
    if form is None:
        return NoRelabel(surface, "not_in_oewn")
    pos = set(lookups.pos(form))
    if pos & set(ADJ_POS):
        return NoRelabel(surface, "has_adjective_sense")
    if "n" not in pos:
        return NoRelabel(surface, "not_a_noun")
    lex = lookups.lexicon()
    low = form.lower()
    lexf = lookups.lexfiles(form)
    person, quality = sorted(lexf & PERSON_LEXFILES), sorted(lexf & QUALITY_LEXFILES)

    def make(adj: str, rule: str, lexfile: Optional[str], definition: Optional[str]) -> Relabel:
        adj = us_spelling(adj, lexicon=lex)
        return Relabel(surface=surface, adjective=adj, rule=rule, lexfile=lexfile,
                       definition=(definition if definition and not PERTAINYM_RE.search(definition)
                                   else _best_definition(adj, lookups)),
                       zipf=lookups.zipf(adj))

    # 5: the base model's suffix fold
    out, form_kind, _from, kind = normalize_form_kind(low, lexicon=lex)
    if form_kind == "adjective" and kind and "noun_suffix" in kind and out != low:
        return make(out, f"suffix:{kind}", (quality + person + sorted(lexf) + [None])[0], None)
    failed: Optional[str] = None
    if low not in SUFFIX_EXCEPTIONS:
        # 6: OEWN's derivation link, from a person or quality sense only
        links = [d for d in lookups.derivations(form)
                 if d.lexfile in PERSON_LEXFILES | QUALITY_LEXFILES and d.adjective.lower() != low]
        links.sort(key=lambda d: (d.lexfile not in PERSON_LEXFILES, -lookups.zipf(d.adjective), d.adjective))
        seen: set[str] = set()
        for d in links:
            if d.adjective in seen:
                continue
            seen.add(d.adjective)
            adj, rule = d.adjective, "derivation"
            if lookups.zipf(adj) < FLOOR_ZIPF:
                mates = [m for m in lookups.synset_mates(adj)
                         if m != adj and " " not in m and m[:4].lower() == adj[:4].lower()]
                if mates:
                    best = max(mates, key=lambda m: (lookups.zipf(m), m))
                    if lookups.zipf(best) >= FLOOR_ZIPF:
                        adj, rule = best, "derivation+spelling"
            if is_pertainym(adj, lookups=lookups):
                failed = failed or "pertainym_only"
                continue
            if lookups.zipf(adj) < FLOOR_ZIPF:
                failed = failed or "below_floor"
                continue
            return make(adj, rule, d.lexfile, d.definition)
        # 7: the suffix rules of the noun's class
        rules = [(r, person[0]) for r in PERSON_SUFFIX_RULES] if person else []
        rules += [(r, quality[0]) for r in QUALITY_SUFFIX_RULES] if quality else []
        for (removed, ends), lexfile in rules:
            if not low.endswith(removed) or len(low) - len(removed) < 3:
                continue
            base = low[:len(low) - len(removed)] if removed else low
            for e in ends:
                adj = base + e
                if adj == low or adj not in lex.adjectives:
                    continue
                if is_pertainym(adj, lookups=lookups):
                    failed = failed or "pertainym_only"
                    continue
                if lookups.zipf(adj) < FLOOR_ZIPF:
                    failed = failed or "below_floor"
                    continue
                return make(adj, _rule_name(removed, e), lexfile, None)
    # 8
    if failed:
        return NoRelabel(surface, failed)
    return NoRelabel(surface, "person_no_adjective" if person else "quality_no_adjective" if quality
                     else "other_noun")


# --------------------------------------------------------------------------- candidates and blocks

def derived_candidate(c, r: Relabel):
    """The adjective's :class:`~assistant_axis.gapgen.registry.Candidate`: the noun's generator, run, rank and score;
    the linked adjective sense's definition as the gloss hint; ``source_ref`` ``relabel:<rule>:<noun surface>``."""
    from .registry import Candidate
    return Candidate(surface=r.adjective, generator=c.generator, run_id=c.run_id, rank=c.rank, score=c.score,
                     gloss_hint=r.definition, sense_id=1, source_ref=f"relabel:{r.rule}:{c.surface}",
                     partner_hint=None)


@dataclass(frozen=True)
class Derived:
    noun: object                     # the generator's Candidate
    adjective: Optional[object]      # the derived Candidate; None when the adjective is a corpus trait
    relabel: Relabel
    corpus_stem: Optional[str]


def corpus_stem_map(data_dir=None) -> dict[str, str]:
    """``{stem: current corpus stem}``: every corpus trait stem, and every ``renamed_from`` stem to the trait it
    became."""
    from .generators.censuses.corpus import corpus_renamed_from, corpus_trait_stems
    out = {s: s for s in corpus_trait_stems(data_dir)}
    for old, new in corpus_renamed_from(data_dir).items():
        out.setdefault(old, new)
    return out


def relabel_candidates(cands: Iterable, *, lookups: NounLookups,
                       corpus_stems: Union[Mapping[str, str], Collection[str]]) -> list[Derived]:
    """One :class:`Derived` per noun that relabels (first candidate per generator, run, surface and sense), in input
    order.  A candidate already derived (``source_ref`` ``relabel:...``) is skipped.  ``corpus_stems``: a set of
    corpus stems, or ``{stem: current stem}`` (:func:`corpus_stem_map`); an adjective found there makes no
    candidate and carries the corpus stem."""
    from .normalize import normalize_candidate
    cmap = corpus_stems if isinstance(corpus_stems, Mapping) else {s: s for s in corpus_stems}
    out: list[Derived] = []
    seen: set[tuple] = set()
    memo: dict[str, Union[Relabel, NoRelabel]] = {}
    for c in cands:
        if str(c.source_ref or "").startswith("relabel:") or " " in " ".join(str(c.surface).split()):
            continue
        ident = (c.generator, c.run_id, str(c.surface).lower(), c.sense_id)
        if ident in seen:
            continue
        seen.add(ident)
        if c.surface not in memo:
            memo[c.surface] = relabel(c.surface, lookups=lookups)
        r = memo[c.surface]
        if not isinstance(r, Relabel):
            continue
        r = Relabel(**{**r.__dict__, "surface": c.surface})
        stem = normalize_candidate(r.adjective).stem
        hit = cmap.get(stem)
        out.append(Derived(noun=c, adjective=None if hit else derived_candidate(c, r), relabel=r, corpus_stem=hit))
    return out


def relabel_blocks(noun_key: str, adj_key: Optional[str], r: Relabel, *, corpus_stem: Optional[str] = None,
                   run: Optional[str] = None, now: str) -> tuple[dict, Optional[dict]]:
    """``(noun block, adjective block)`` (plan section 6).  With ``corpus_stem`` the noun block carries
    ``to_corpus_stem`` and there is no adjective block."""
    common = {"rule": r.rule, "lexfile": r.lexfile, "helper_version": r.helper_version, "oewn": OEWN_LEXICON,
              "at": now}
    if corpus_stem:
        return {"to_corpus_stem": corpus_stem, **common}, None
    noun = {"to_key": adj_key, **common}
    adj = {"from_key": noun_key, "from_surface": r.surface, "rule": r.rule, "lexfile": r.lexfile,
           "helper_version": r.helper_version, "oewn": OEWN_LEXICON, "run": run, "at": now}
    return noun, adj


def same_block(a: Optional[Mapping], b: Optional[Mapping]) -> bool:
    """Two ``relabel`` blocks equal but for their time stamps."""
    if not a or not b:
        return not a and not b
    return {k: v for k, v in a.items() if k != "at"} == {k: v for k, v in b.items() if k != "at"}


def _route(rule: Optional[str], lexfile: Optional[str]) -> tuple[str, str]:
    """``(how, tail)``: "derivation link" with its lexicographer file, or "suffix rule <ending>" with "sense not
    checked"."""
    rule = rule or "?"
    if rule.startswith("derivation"):
        spell = ", spelling mate" if rule == "derivation+spelling" else ""
        return f"derivation link{spell}", f" ({lexfile})" if lexfile else ""
    if rule.startswith("suffix:"):
        return f"suffix rule {rule[len('suffix:'):]}", ", sense not checked"
    return rule, ""


def route_text(block: Optional[Mapping]) -> Optional[str]:
    """How a row was linked, for the review card (Roger, decision 2 (c), 2026-10-14): on an adjective row
    "suffix rule +y from 'slipper', sense not checked" / "derivation link from 'pedant' (noun.person)"; on a noun row
    "adjective 'pedantic' by derivation link (noun.person)".  ``None`` for no block.  Every suffix rule says "sense
    not checked": the derivation link's lexicographer-file gate is the helper's only sense check."""
    if not block:
        return None
    how, tail = _route(block.get("rule"), block.get("lexfile"))
    if block.get("from_key") or block.get("from_surface"):
        src = block.get("from_surface") or str(block.get("from_key")).split("#")[0]
        return f"{how} from '{src}'{tail}"
    if block.get("to_corpus_stem"):
        return f"adjective '{block['to_corpus_stem']}' (a corpus trait) by {how}{tail}"
    if block.get("to_key"):
        return f"adjective '{str(block['to_key']).split('#')[0]}' by {how}{tail}"
    return None


def link_wanted(old: Optional[Mapping], new: Mapping) -> bool:
    """Whether a row's ``relabel`` block ``old`` gives way to ``new``: not when they are equal but for their time
    stamps (a resubmission writes nothing), nor when ``old`` is of the same or a later helper version (the first
    noun to link an adjective stays its ``from_key``; a noun keeps its adjective).  A later helper version's link
    replaces the block (the earlier linked row keeps its own)."""
    if same_block(old, new):
        return False
    return not (old and int(old.get("helper_version") or 0) >= int(new.get("helper_version") or 0))


# --------------------------------------------------------------------------- the Haiku pilot (open decision 3)

#: The pilot's system prompt (plan section 10), pinned in ``rubric_versions.HISTORY["noun_relabel"]``.  Reason
#: first (judging rule: a short reason before the answer, never the model's thinking).
PILOT_PROMPT_VERSION = 1
PILOT_SYSTEM_PROMPT = """You are helping curate a research corpus of personality traits. Each entry is a one- or two-word label, and the
corpus prefers an adjective ("pedantic", "cowardly") to a noun for the kind of person ("pedant", "coward"),
because a persona is prompted with "You are <label>." Some such nouns have a standard English adjective meaning
"like such a person" (pedant: pedantic; hypocrite: hypocritical; bookworm: bookish); many have none (charlatan,
loner, go-getter), and for those the noun stays.

You are given one noun and a one-sentence gloss of the disposition it names. Say whether English has a standard
adjective for being that kind of person.
- The adjective must be in established use with that meaning, one word (a hyphen is allowed), not coined for the
  occasion, and derived from the noun or its root (bookworm: bookish is fine; liar: dishonest is not, a synonym is
  not a relabel).
- If several exist, give the most common.
- If none exists, say so; do not force one.

Respond with one JSON object and nothing else, reason first:
{"reason": "<one short sentence>", "adjective": "<word>"|null, "confidence": <0-1>}"""
PILOT_MODEL = "claude-haiku-5-5"
PILOT_MAX_TOKENS = 120


def render_pilot_user(label: str, gloss: Optional[str]) -> str:
    """One row's user turn: the noun in the trait-gap prompts' label form, and its gloss."""
    from .prompt_labels import prompt_label
    return f"Noun: {prompt_label(label)}\nGloss: {' '.join(str(gloss or '').split())}"


def parse_pilot_reply(text: Optional[str]) -> Optional[dict]:
    """``{"reason", "adjective", "confidence"}`` from a reply, or None when it does not parse (``adjective`` a
    lower-case word or None; ``confidence`` a float in [0, 1] or None)."""
    from assistant_axis.judge import extract_json_blob
    if not text:
        return None
    try:
        d = json.loads(extract_json_blob(text) or "")
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(d, dict) or "adjective" not in d:
        return None
    adj = d.get("adjective")
    if isinstance(adj, str):
        adj = " ".join(adj.strip().lower().split()) or None
        if adj in ("null", "none"):
            adj = None
    elif adj is not None:
        return None
    conf = d.get("confidence")
    try:
        conf = None if conf is None else max(0.0, min(1.0, float(conf)))
    except (TypeError, ValueError):
        conf = None
    return {"reason": d.get("reason"), "adjective": adj, "confidence": conf}
