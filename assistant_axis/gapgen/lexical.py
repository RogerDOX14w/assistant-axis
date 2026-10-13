"""Workstream 11: lexical recall insurance for M3 (``reports/trait_gap_generation/coding_plan_11_novelty_ensemble.md``).

M3 retrieves a candidate's ten nearest corpus traits by embedding and judges only those (and their arrangements).  A
corpus trait the embedding puts far away is never read, however plainly a dictionary ties the two words: the gate
audit's five retrieval misses (delightful, pleasant, nice, annoying, unsteadfast) are such cases.  This module is
the dictionary side: a **lexical link** is a recorded tie between two words (Open English WordNet's synonym, "similar
to", "also see" and antonym links, and a Moby thesaurus row); a **lexical neighbour** of a candidate is a corpus trait
or live seed-queue entry its label is linked to; a **lexical-only pair** is a candidate and a lexical neighbour that
M3's retrieval and expansion never listed (:mod:`assistant_axis.gapgen.lexical_sweep` reads those pairs).

Links are **by word, not by sense** (decided, plan § 1): a candidate's label is looked up as a word, every synset of
the first form the lexicon knows counts, and the overlap call is the sense filter; nothing is rejected on a link alone.
Link types (:data:`LINK_TYPES`): ``synonym`` (a lemma of one of the label's synsets), ``similar`` and ``also`` (a lemma
of a synset one of the label's synsets points at by that relation); Moby gives ``synonym`` only (its row of the label,
and every row that lists the label).  Antonym evidence (:data:`ANTONYM_TYPES`): OEWN's sense-level ``antonym`` links,
and the negation-affix rule (``un-X``, ``in-X``, ... ``non-X``, ``dis-X``, ``a-X`` for a trait ``X``, and ``X-less`` /
``X-ful``).  Stem families (morphology, annotation for the review only): OEWN's ``derivation`` sense links and the same
affix rule.  A ``non-X`` placeholder label (:func:`is_placeholder`) is never a target and never a family member.

The **lookup table** (:func:`build_lookup`, :func:`save_lookup`, :data:`LOOKUP_PATH`) records every corpus trait and
live seed-queue label with the forms tried, its synsets (OEWN) or head row (Moby), whether it has a text (a queue entry
with none gives a *name-only* link: recorded, shown in review, never judged), the lexicon versions and a content hash.
A :class:`Lookup` answers :meth:`Lookup.neighbours`, :meth:`Lookup.antonym_evidence` and :meth:`Lookup.family` for a
candidate's label with the lexicons attached (the table names them; they are not saved in it).

Frozen interface (plan § "Frozen interface"): ``Lookup``, ``load_lookup``, ``LOOKUP_PATH``, ``LINK_TYPES``,
``ANTONYM_TYPES``, ``LEXICONS``; ``Lookup.neighbours(label, stem, *, exclude=()) -> list[Link]`` (``Link(stem, kind,
link, lexicon, name_only)``), ``Lookup.antonym_evidence(label, stem) -> list[Antonym]``, ``Lookup.family(label, stem)
-> list[str]``.  Fields are added, never renamed.

The Moby thesaurus (Gutenberg #3202, public domain) is fetched by ``setup_external.py --moby`` (:func:`fetch_moby`)
into ``data/external/moby/`` with a download manifest beside it and a tracked copy in
``data/candidates/lexical/sources_manifest.json``.  No API call anywhere in this module.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol, Sequence

from assistant_axis.entity_id import normalize_to_file_name

from .paths import DATA_CANDIDATES, DATA_EXTERNAL, REPO_ROOT

# --------------------------------------------------------------------------- constants

LEXICONS: tuple[str, ...] = ("oewn", "moby")
LINK_TYPES: tuple[str, ...] = ("synonym", "similar", "also")
ANTONYM_TYPES: tuple[str, ...] = ("antonym", "negation_affix")
#: The negation prefixes of the affix rule (antonym evidence and stem families), and the suffix pairs.
NEGATION_PREFIXES: tuple[str, ...] = ("un", "in", "im", "il", "ir", "non", "dis", "a")
SUFFIX_PAIRS: tuple[tuple[str, str], ...] = (("less", "ful"),)
#: The shortest stem the affix rule strips to or prefixes (``un`` + ``fit``), and for the bare ``a-`` prefix, which
#: makes most spurious pairs (``ashy`` is not the opposite of ``shy``), a longer one (``amoral`` -> ``moral``).
AFFIX_MIN_STEM = 3
A_PREFIX_MIN_STEM = 5
#: A Moby-only pair (a lexical neighbour no OEWN link reaches) is judged only at this cosine or above (plan § 1).
MOBY_COSINE_FLOOR = 0.2
KINDS: tuple[str, ...] = ("corpus", "queue")
LOOKUP_SCHEMA = 1
LEXICAL_DIR = DATA_CANDIDATES / "lexical"
LOOKUP_PATH = LEXICAL_DIR / "lookup.json"
SOURCES_MANIFEST_PATH = LEXICAL_DIR / "sources_manifest.json"
MOBY_DIR = DATA_EXTERNAL / "moby"
MOBY_FILE = "mthesaur.txt"
DOWNLOAD_MANIFEST_NAME = "DOWNLOAD_MANIFEST.json"
#: Project Gutenberg eBook #3202, the Moby Thesaurus List by Grady Ward: 24,853,275 bytes on 2026-10-13 (a HEAD
#: request; last modified 2025-08-23), plain comma-separated rows (head first), CRLF, no header.
MOBY_URL = "https://www.gutenberg.org/files/3202/files/mthesaur.txt"
MOBY_SOURCE = "Gutenberg #3202"
MOBY_EXPECTED_BYTES = 24_853_275
MOBY_LICENCE = "public domain (Project Gutenberg #3202, Moby Thesaurus List by Grady Ward)"
MOBY_TOOL = "setup_external.py --moby"
MOBY_APPROVAL = "Roger: the Moby download approved in plan 11 (11_novelty_ensemble.md § 9.1; coding_plan_11 § 1)"
#: Where the link's order comes from: OEWN before Moby, then synonym, similar, also.
_LEX_RANK = {name: i for i, name in enumerate(LEXICONS)}
_LINK_RANK = {name: i for i, name in enumerate(LINK_TYPES)}
_STANDARD_SUFFIX_RE = re.compile(r"\s*\(\s*[A-Z][^()]*\)\s*$")
_PLACEHOLDER_RE = re.compile(r"^non[-\s_]\S")


# --------------------------------------------------------------------------- forms

def norm(word: str) -> str:
    """The key a word is matched under: its file-name form (lowercase, separators ``_``, apostrophes and diacritics
    folded; :func:`normalize_to_file_name`), or a plain lowercase fallback for a string that does not normalise."""
    try:
        return normalize_to_file_name(word)
    except Exception:  # noqa: BLE001 - a lemma with characters the stem rule refuses
        return "_".join(str(word).lower().split())


def blind(stem: str) -> str:
    """A stem with its separators taken out (``kind_hearted`` and ``kindhearted`` are one word)."""
    return stem.replace("_", "")


def strip_standard_suffix(label: str) -> str:
    """``agreeable (Big Five)`` -> ``agreeable``: a capitalised parenthesised suffix (a standard's name) dropped; a
    lower-case one (``(tentative, PC10)``) is not a standard and stays."""
    return _STANDARD_SUFFIX_RE.sub("", label).strip() or label.strip()


def label_forms(label: str) -> list[str]:
    """The forms a label is looked up under, in order: a standard's suffix dropped, a stem's ``_`` read as a space,
    then as given (lowercase), hyphen to space, space to hyphen, hyphen dropped (the census gloss hint's forms,
    ``glosshint.lookup_forms``).  A phrase is tried whole and abstains when the lexicon lacks it (no word-by-word
    fallback)."""
    s = " ".join(strip_standard_suffix(str(label)).replace("_", " ").strip().lower().split())
    out: list[str] = []
    for f in (s, s.replace("-", " "), s.replace(" ", "-"), s.replace("-", "")):
        if f and f not in out:
            out.append(f)
    return out


def is_placeholder(label: Optional[str]) -> bool:
    """A ``non-X`` placeholder label (the form a singleton's ``negative_label`` takes): never a target, never a family
    member.  ``nonconformist`` (one word) is not one."""
    return bool(label) and bool(_PLACEHOLDER_RE.match(str(label).strip().lower()))


def affix_pairs(stem: str) -> list[tuple[str, str]]:
    """``[(blind stem, rule), ...]`` the affix rule pairs ``stem`` with: the stem with a negation prefix taken off or
    put on (``unkind`` <-> ``kind``: rule ``prefix:un``), and ``-less`` <-> ``-ful`` (rule ``suffix:less/ful``).  Blind
    forms (separators out); a stripped stem shorter than :data:`AFFIX_MIN_STEM` is not offered."""
    b = blind(stem)
    out: list[tuple[str, str]] = []
    for p in NEGATION_PREFIXES:
        least = A_PREFIX_MIN_STEM if p == "a" else AFFIX_MIN_STEM
        if b.startswith(p) and len(b) - len(p) >= least:
            out.append((b[len(p):], f"prefix:{p}"))
        if len(b) >= least:
            out.append((p + b, f"prefix:{p}"))
    for a, z in SUFFIX_PAIRS:
        for x, y in ((a, z), (z, a)):
            if b.endswith(x) and len(b) - len(x) >= AFFIX_MIN_STEM:
                out.append((b[: -len(x)] + y, f"suffix:{a}/{z}"))
    seen, uniq = set(), []
    for x in out:
        if x[0] != b and x[0] not in seen:
            seen.add(x[0])
            uniq.append(x)
    return uniq


# --------------------------------------------------------------------------- lexicons

class Lexicon(Protocol):
    """What :class:`Lookup` needs of a lexicon (the plan's protocol plus :meth:`links`)."""
    name: str

    def synsets(self, form: str) -> list[str]: ...
    def lemmas(self, sid: str) -> list[str]: ...
    def related(self, sid: str, rel: str) -> list[str]: ...
    def antonyms(self, form: str) -> list[str]: ...
    def derivations(self, form: str) -> list[str]: ...
    def links(self, form: str) -> dict[str, dict[str, str]]: ...
    @property
    def version(self) -> str: ...
    def info(self) -> dict: ...


def first_form(label: str, lexicon: Lexicon) -> tuple[Optional[str], list[str], list[str]]:
    """``(form, synset ids, forms tried)``: the first of :func:`label_forms` the lexicon knows (``None`` and ``[]`` when
    none), as ``wordnet.sense_info`` takes the first form that yields synsets."""
    tried = []
    for f in label_forms(label):
        tried.append(f)
        ids = lexicon.synsets(f)
        if ids:
            return f, list(ids), tried
    return None, [], tried


class OewnLexicon:
    """Open English WordNet through ``wn`` (``wordnet.oewn()`` by default, its data directory pinned in-tree), or any
    object with the ``wn.Wordnet`` methods used here (``synsets(form)``, ``synset(id)``, ``words(form)``; synsets with
    ``id``, ``lemmas()`` and ``relations(name)``; words with ``senses()``; senses with ``relations(name)`` and
    ``word()``; words with ``lemma()``).  Results are cached per form and synset."""
    name = "oewn"

    def __init__(self, wordnet: Any = None, *, lexicon_id: Optional[str] = None, wn_version: Optional[str] = None,
                 lexicon_version: Optional[str] = None):
        if wordnet is None:
            from . import wordnet as gw
            wordnet = gw.oewn()
            lexicon_id = lexicon_id or gw.OEWN_LEXICON
            try:
                import wn
                wn_version = wn_version or getattr(wn, "__version__", None)
                lex = wn.lexicons(lexicon=gw.OEWN_LEXICON)
                lexicon_version = lexicon_version or (lex[0].version if lex else None)
            except Exception:  # noqa: BLE001 - the version is a record, not a requirement
                pass
        self.wordnet = wordnet
        self.lexicon_id = lexicon_id or "oewn:2024"
        self.wn_version = wn_version
        self.lexicon_version = lexicon_version
        self._syn: dict[str, Any] = {}
        self._cache: dict[tuple, Any] = {}

    @property
    def version(self) -> str:
        return self.lexicon_id

    def info(self) -> dict:
        return {"id": self.lexicon_id, "wn_version": self.wn_version, "lexicon_version": self.lexicon_version}

    def _memo(self, key: tuple, fn: Callable[[], Any]) -> Any:
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    def synsets(self, form: str) -> list[str]:
        def go():
            out = []
            for s in self.wordnet.synsets(form):
                self._syn[s.id] = s
                out.append(s.id)
            return out
        return list(self._memo(("synsets", form), go))

    def _synset(self, sid: str):
        s = self._syn.get(sid)
        if s is None:
            s = self.wordnet.synset(sid)
            self._syn[sid] = s
        return s

    def lemmas(self, sid: str) -> list[str]:
        return list(self._memo(("lemmas", sid), lambda: [str(x) for x in self._synset(sid).lemmas()]))

    def related(self, sid: str, rel: str) -> list[str]:
        def go():
            out = []
            for t in (self._synset(sid).relations(rel) or {}).get(rel, []):
                self._syn[t.id] = t
                out.append(t.id)
            return out
        return list(self._memo(("related", sid, rel), go))

    def _sense_words(self, form: str, rel: str) -> list[str]:
        def go():
            out: list[str] = []
            for w in self.wordnet.words(form):
                for se in w.senses():
                    for t in (se.relations(rel) or {}).get(rel, []):
                        lem = t.word().lemma()
                        if lem not in out:
                            out.append(lem)
            return out
        return list(self._memo(("sense", form, rel), go))

    def antonyms(self, form: str) -> list[str]:
        """The lemmas OEWN's sense-level ``antonym`` links reach from any sense of ``form``."""
        return self._sense_words(form, "antonym")

    def derivations(self, form: str) -> list[str]:
        """The lemmas OEWN's sense-level ``derivation`` links reach from any sense of ``form``."""
        return self._sense_words(form, "derivation")

    def links(self, form: str) -> dict[str, dict[str, str]]:
        """``{link type: {norm(word): via}}`` for ``form``: the lemmas of its synsets (``synonym``), of the synsets they
        point at by ``similar`` and by ``also``; ``via`` is the synset of the label that gave the link (its id)."""
        out: dict[str, dict[str, str]] = {t: {} for t in LINK_TYPES}
        for sid in self.synsets(form):
            for lem in self.lemmas(sid):
                out["synonym"].setdefault(norm(lem), sid)
            for rel in ("similar", "also"):
                for tid in self.related(sid, rel):
                    for lem in self.lemmas(tid):
                        out[rel].setdefault(norm(lem), sid)
        return out


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def parse_moby(text: str) -> dict[str, list[str]]:
    """Moby's ``mthesaur.txt``: one row per line, ``head,synonym,synonym,...`` (a quoted field may hold a comma),
    lowercase; blank fields (a trailing comma) dropped, a line with no synonym skipped, a repeated head's rows
    merged.  ``{head: [synonyms in file order]}``; heads and synonyms as written (lowercased), matched later by
    :func:`norm`.  A Project Gutenberg header and footer, if a copy carries them, are cut at the ``*** START`` and
    ``*** END`` markers."""
    lines = text.splitlines()
    start = next((i for i, x in enumerate(lines) if x.startswith("*** START OF")), None)
    if start is not None:
        end = next((i for i, x in enumerate(lines) if x.startswith("*** END OF")), len(lines))
        lines = lines[start + 1:end]
    out: dict[str, list[str]] = {}
    for row in csv.reader(lines, skipinitialspace=True):
        fields = [" ".join(f.strip().lower().split()) for f in row]
        fields = [f for f in fields if f]
        if len(fields) < 2:
            continue
        head, syns = fields[0], fields[1:]
        cur = out.setdefault(head, [])
        seen = set(cur)
        for s in syns:
            if s != head and s not in seen:
                seen.add(s)
                cur.append(s)
    return out


class MobyLexicon:
    """Moby Thesaurus II as a lexicon (``path``: ``mthesaur.txt``; or ``rows``, ``{head: [synonyms]}``, for tests).  A
    "synset" is a head's row (``moby:<head>``), so a form has one when it is a head; :meth:`links` gives ``synonym``
    links both ways (the form's own row, and every head whose row lists the form).  No antonyms, no derivations.
    ``version``: the download manifest's sha256 when the manifest is beside the file, else the file's own."""
    name = "moby"

    def __init__(self, path: Optional[Path] = None, *, rows: Optional[Mapping[str, Sequence[str]]] = None,
                 sha256: Optional[str] = None):
        if rows is None:
            if path is None:
                raise ValueError("MobyLexicon needs a path or rows")
            p = Path(path)
            raw = p.read_bytes()
            rows = parse_moby(_decode(raw))
            if sha256 is None:
                man = p.parent / DOWNLOAD_MANIFEST_NAME
                doc = json.loads(man.read_text(encoding="utf-8")) if man.exists() else {}
                sha256 = doc.get("sha256") or hashlib.sha256(raw).hexdigest()
        self.path = Path(path) if path is not None else None
        self.sha256 = sha256 or hashlib.sha256(json.dumps(rows, sort_keys=True).encode("utf-8")).hexdigest()
        # every word normalised once and interned (the real file has about 2.5 million entries over far fewer words)
        memo: dict[str, str] = {}

        def key(w: str) -> str:
            k = memo.get(w)
            if k is None:
                k = memo[w] = sys.intern(norm(w))
            return k
        self.rows: dict[str, tuple[str, ...]] = {}
        for h, v in rows.items():
            kh = key(h)
            self.rows[kh] = tuple(dict.fromkeys((*self.rows.get(kh, ()), *(key(x) for x in v))))
        self._reverse: Optional[dict[str, set[str]]] = None

    @property
    def version(self) -> str:
        return self.sha256

    def info(self) -> dict:
        return {"sha256": self.sha256, "source": MOBY_SOURCE, "n_heads": len(self.rows)}

    @property
    def n_heads(self) -> int:
        return len(self.rows)

    def _rev(self) -> dict[str, set[str]]:
        if self._reverse is None:
            rev: dict[str, set[str]] = {}
            for h, syns in self.rows.items():
                for s in syns:
                    rev.setdefault(s, set()).add(h)
            self._reverse = rev
        return self._reverse

    def synsets(self, form: str) -> list[str]:
        n = norm(form)
        return [f"moby:{n}"] if n in self.rows else []

    def lemmas(self, sid: str) -> list[str]:
        h = sid.split(":", 1)[1]
        return [h] + list(self.rows.get(h, []))

    def related(self, sid: str, rel: str) -> list[str]:
        return []

    def antonyms(self, form: str) -> list[str]:
        return []

    def derivations(self, form: str) -> list[str]:
        return []

    def n_synonyms(self, form: str) -> int:
        return len(self.rows.get(norm(form), []))

    def links(self, form: str) -> dict[str, dict[str, str]]:
        n = norm(form)
        out: dict[str, dict[str, str]] = {t: {} for t in LINK_TYPES}
        for s in self.rows.get(n, ()):
            out["synonym"].setdefault(s, f"moby:{n}")
        for h in sorted(self._rev().get(n, ())):
            out["synonym"].setdefault(h, f"moby:{h}")
        return out


# --------------------------------------------------------------------------- links

@dataclass(frozen=True)
class Link:
    """One lexical neighbour of a candidate: the target's ``stem`` and ``kind`` (``corpus`` or ``queue``), the link
    type and lexicon of the strongest link (OEWN before Moby; synonym, similar, also), ``name_only`` (a queue entry
    with no text: recorded, never judged).  Added fields: ``word`` (the target form the lexicon named), ``via`` (the
    candidate's synset that gave the link, or the Moby row), ``also_found`` (the other ``lexicon:link`` ties to the
    same target, weakest last)."""
    stem: str
    kind: str
    link: str
    lexicon: str
    name_only: bool = False
    word: Optional[str] = None
    via: Optional[str] = None
    also_found: tuple = ()

    def as_dict(self) -> dict:
        d = asdict(self)
        d["also_found"] = list(self.also_found)
        return d

    @property
    def moby_only(self) -> bool:
        """Only Moby links the candidate to this target (no OEWN tie)."""
        return self.lexicon == "moby" and not any(str(x).startswith("oewn:") for x in self.also_found)


@dataclass(frozen=True)
class Antonym:
    """Antonym evidence: the target ``stem``, the ``link`` (``antonym``: OEWN's sense-level link; ``negation_affix``:
    the affix rule), ``partner_has_file`` (the target trait has a recorded clean-pair partner, a reciprocal pair, so a
    file; False flags a trait the candidate might complete), and added fields ``lexicon`` (``oewn`` or ``affix``),
    ``kind`` and ``rule`` (the affix rule that matched)."""
    stem: str
    link: str
    partner_has_file: bool
    lexicon: str = "oewn"
    kind: str = "corpus"
    rule: Optional[str] = None

    def as_dict(self) -> dict:
        return asdict(self)


def word_links(label: str, lexicon: Lexicon) -> tuple[Optional[str], dict[str, dict[str, str]]]:
    """``(form, {link type: {norm(word): via}})``: :meth:`Lexicon.links` of the first form of ``label`` the lexicon
    knows (``(None, {})`` when it knows none: the label abstains)."""
    form, _, _ = first_form(label, lexicon)
    if form is None:
        return None, {}
    return form, lexicon.links(form)


def link_between(label_a: str, label_b: str, lexicon: Lexicon) -> Optional[str]:
    """The strongest link type tying two labels in ``lexicon`` in either direction (``synonym`` > ``similar`` >
    ``also``), or ``None``; for the labelled-pairs measurement."""
    best = None
    for x, y in ((label_a, label_b), (label_b, label_a)):
        _, links = word_links(x, lexicon)
        keys = {norm(f) for f in label_forms(y)}
        for t in LINK_TYPES:
            if keys & set(links.get(t, {})):
                if best is None or _LINK_RANK[t] < _LINK_RANK[best]:
                    best = t
                break
    return best


def antonym_between(label_a: str, label_b: str, lexicon: Optional[Lexicon]) -> Optional[str]:
    """``antonym`` (an OEWN sense-level link either way), ``negation_affix`` (the affix rule), or ``None``."""
    if lexicon is not None:
        for x, y in ((label_a, label_b), (label_b, label_a)):
            form, _, _ = first_form(x, lexicon)
            if form is None:
                continue
            keys = {norm(f) for f in label_forms(y)}
            if keys & {norm(w) for w in lexicon.antonyms(form)}:
                return "antonym"
    a, b = norm(label_forms(label_a)[0]), norm(label_forms(label_b)[0])
    if blind(b) in {x for x, _ in affix_pairs(a)}:
        return "negation_affix"
    return None


# --------------------------------------------------------------------------- the seed queue

def live_queue_entries(queue: Mapping, corpus: Mapping) -> tuple[list[dict], dict]:
    """The seed queue's live trait entries, the same selection as M3's search (:func:`novelty.queue_traits`: a trait
    entry at a status of :data:`novelty.QUEUE_SEARCH_STATUSES`, not handed to the registry, not a corpus stem, a
    corpus file's ``renamed_from`` or a label that is a corpus stem; the first entry of a stem), **with or without a
    text**: ``[{"stem", "label", "has_text", "text", "status", "partner"}]`` and the record (counts by reason).  An
    entry with no text gives only name-only links (M3's index leaves it out as ``no_text``)."""
    from . import novelty as NV
    renamed = {old for t in corpus.values() for old in t.renamed_from}
    excluded: dict[str, int] = {}
    chosen: dict[str, dict] = {}

    def skip(why: str) -> None:
        excluded[why] = excluded.get(why, 0) + 1

    for e in queue.get("entries") or []:
        stem = e.get("stem")
        if (e.get("entity_type") or "trait") != "trait" or not stem:
            skip("not_a_trait_entry")
            continue
        if NV.handed_to_registry(e):
            skip("handed_to_registry")
            continue
        if e.get("status") not in NV.QUEUE_SEARCH_STATUSES:
            skip(f"status_{e.get('status')}")
            continue
        lab = normalize_to_file_name(e["label"]) if e.get("label") else stem
        if stem in corpus:
            skip("a_corpus_stem")
            continue
        if stem in renamed or lab in renamed:
            skip("a_corpus_files_renamed_from")
            continue
        if lab in corpus:
            skip("label_a_corpus_stem")
            continue
        if stem in chosen:
            skip("duplicate_stem")
            continue
        text = NV.queue_text(e)
        p = e.get("partner")
        p = normalize_to_file_name(p) if isinstance(p, str) and p.strip() else None
        chosen[stem] = {"stem": stem, "label": e.get("label") or stem.replace("_", " "), "has_text": bool(text),
                        "text": text, "status": e.get("status"), "partner": p if p != stem else None}
    rows = [chosen[s] for s in sorted(chosen)]
    return rows, {"statuses": list(NV.QUEUE_SEARCH_STATUSES), "n_entries": len(rows),
                  "n_with_text": sum(1 for r in rows if r["has_text"]),
                  "n_name_only": sum(1 for r in rows if not r["has_text"]), "excluded": dict(sorted(excluded.items()))}


# --------------------------------------------------------------------------- the lookup table

def _target_row(stem: str, label: str, kind: str, *, has_text: bool, renamed_from: Sequence[str] = (),
                has_partner: bool = False, status: Optional[str] = None,
                lexicons: Mapping[str, Lexicon]) -> dict:
    row: dict = {"stem": stem, "label": label, "kind": kind, "has_text": bool(has_text),
                 "forms_tried": label_forms(label)}
    if renamed_from:
        row["renamed_from"] = list(renamed_from)
    row["has_partner"] = bool(has_partner)
    if status is not None:
        row["status"] = status
    for name, lex in lexicons.items():
        form, ids, tried = first_form(label, lex)
        if name == "oewn":
            row["oewn"] = {"found": form is not None, "form": form, "synsets": ids,
                           "derivations": sorted({norm(w) for w in lex.derivations(form)}) if form else []}
        elif name == "moby":
            row["moby"] = {"found": form is not None, "head": form,
                           "n_synonyms": lex.n_synonyms(form) if form and hasattr(lex, "n_synonyms") else 0}
        else:
            row[name] = {"found": form is not None, "form": form, "synsets": ids}
    return row


def _content_sha(rows: Sequence[Mapping], lexicon_info: Mapping) -> str:
    payload = {"rows": [{k: r[k] for k in sorted(r)} for r in rows], "lexicons": dict(lexicon_info)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def build_lookup(corpus: Mapping, queue_entries: Sequence[Mapping], *, lexicons: Mapping[str, Lexicon] | Sequence[Lexicon],
                 extra_header: Optional[Mapping] = None) -> "Lookup":
    """The lookup table over every corpus trait (``corpus``: :func:`novelty.load_trait_corpus`; ``renamed_from``
    recorded so a link to an old name folds to the current stem) and live queue label (``queue_entries``:
    :func:`live_queue_entries`), with ``lexicons`` attached.  A ``non-X`` placeholder label is left out.  Header:
    ``lexicons`` (each one's :meth:`info`), ``n_corpus``, ``n_queue``, ``n_queue_name_only``, ``coverage`` (found per
    lexicon per kind), ``content_sha256`` (changes when a label, a form or a lexicon does)."""
    lexmap = dict(lexicons) if isinstance(lexicons, Mapping) else {lx.name: lx for lx in lexicons}
    lexmap = {k: lexmap[k] for k in sorted(lexmap, key=lambda n: _LEX_RANK.get(n, 99))}
    rows: list[dict] = []
    for stem in sorted(corpus):
        t = corpus[stem]
        if is_placeholder(t.label):
            continue
        rows.append(_target_row(stem, t.label, "corpus", has_text=bool(t.description), renamed_from=t.renamed_from,
                                has_partner=t.pair_partner is not None, lexicons=lexmap))
    for e in queue_entries:
        if is_placeholder(e["label"]) or e["stem"] in corpus:
            continue
        rows.append(_target_row(e["stem"], e["label"], "queue", has_text=bool(e.get("has_text")),
                                has_partner=bool(e.get("partner")), status=e.get("status"), lexicons=lexmap))
    info = {name: lx.info() for name, lx in lexmap.items()}
    cov: dict = {}
    for name in lexmap:
        cov[name] = {}
        for kind in KINDS:
            of = [r for r in rows if r["kind"] == kind]
            cov[name][kind] = {"found": sum(1 for r in of if (r.get(name) or {}).get("found")), "of": len(of)}
        qt = [r for r in rows if r["kind"] == "queue" and r["has_text"]]
        cov[name]["queue_with_text"] = {"found": sum(1 for r in qt if (r.get(name) or {}).get("found")), "of": len(qt)}
    header = {"schema": LOOKUP_SCHEMA, "lexicons": info,
              "n_corpus": sum(1 for r in rows if r["kind"] == "corpus"),
              "n_queue": sum(1 for r in rows if r["kind"] == "queue"),
              "n_queue_name_only": sum(1 for r in rows if r["kind"] == "queue" and not r["has_text"]),
              "coverage": cov, "content_sha256": _content_sha(rows, info)}
    header.update(dict(extra_header or {}))
    return Lookup(rows=rows, header=header, lexicons=lexmap)


class Lookup:
    """The lookup table with its lexicons attached (:func:`build_lookup`, :func:`load_lookup`)."""

    def __init__(self, *, rows: Sequence[Mapping], header: Mapping, lexicons: Optional[Mapping[str, Lexicon]] = None):
        self.rows: dict[str, dict] = {r["stem"]: dict(r) for r in rows}
        self.header = dict(header)
        self.lexicons: dict[str, Lexicon] = {k: v for k, v in sorted((lexicons or {}).items(),
                                                                      key=lambda kv: _LEX_RANK.get(kv[0], 99))}
        # norm(form) -> [stems]: every target's label forms and its renamed_from stems' forms (folded to the stem)
        self._by_form: dict[str, list[str]] = {}
        self._by_blind: dict[str, list[str]] = {}
        for stem, r in sorted(self.rows.items()):
            keys = {norm(f) for f in r.get("forms_tried") or label_forms(r["label"])}
            for old in r.get("renamed_from") or []:
                keys |= {norm(f) for f in label_forms(old)}
            for k in sorted(keys):
                self._by_form.setdefault(k, []).append(stem)
            for b in {blind(stem)} | {blind(k) for k in keys}:
                lst = self._by_blind.setdefault(b, [])
                if stem not in lst:
                    lst.append(stem)
        self._deriv: dict[str, list[str]] = {}
        for stem, r in sorted(self.rows.items()):
            for d in (r.get("oewn") or {}).get("derivations") or []:
                self._deriv.setdefault(d, []).append(stem)

    # -- table facts --------------------------------------------------------------------
    @property
    def content_sha256(self) -> str:
        return self.header.get("content_sha256", "")

    @property
    def lexicon_versions(self) -> dict:
        """``{lexicon: version string}`` as the blocks record them (``oewn:2024``; Moby's sha256)."""
        out = {}
        for name, info in (self.header.get("lexicons") or {}).items():
            out[name] = info.get("id") if name == "oewn" else info.get("sha256")
        return out

    def kind(self, stem: str) -> Optional[str]:
        r = self.rows.get(stem)
        return r["kind"] if r else None

    def has_text(self, stem: str) -> bool:
        return bool((self.rows.get(stem) or {}).get("has_text"))

    def targets(self, kind: Optional[str] = None) -> list[str]:
        return sorted(s for s, r in self.rows.items() if kind is None or r["kind"] == kind)

    def stems_for_word(self, word: str) -> list[str]:
        """The targets a word names (by its :func:`norm` form; a renamed_from stem folds to the current one)."""
        return list(self._by_form.get(norm(word), []))

    # -- the three questions -----------------------------------------------------------------
    def neighbours(self, label: str, stem: str, *, exclude: Iterable[str] = ()) -> list[Link]:
        """The candidate's lexical neighbours: one :class:`Link` per target (the strongest tie: OEWN before Moby, then
        synonym, similar, also; the others in ``also_found``), sorted in that order and by stem.  Never the candidate's
        own stem (separator-blind) nor a stem of ``exclude`` (the listed, read and covering stems; a hidden set);
        ``renamed_from`` folded to the current stem first; a text-less queue entry comes back ``name_only``."""
        ex = set(exclude)
        own = blind(stem)
        found: dict[str, list[tuple[str, str, str, str]]] = {}
        for lname, lex in self.lexicons.items():
            _, links = word_links(label, lex)
            for ltype in LINK_TYPES:
                for w, via in (links.get(ltype) or {}).items():
                    for t in self._by_form.get(w, ()):
                        if t in ex or blind(t) == own or t == stem:
                            continue
                        found.setdefault(t, []).append((lname, ltype, w, via))
        out = []
        for t, ties in found.items():
            ties = sorted(set(ties), key=lambda x: (_LEX_RANK.get(x[0], 99), _LINK_RANK[x[1]], x[2], x[3]))
            lname, ltype, w, via = ties[0]
            others = []
            for x in ties[1:]:
                tag = f"{x[0]}:{x[1]}"
                if tag != f"{lname}:{ltype}" and tag not in others:
                    others.append(tag)
            r = self.rows[t]
            out.append(Link(stem=t, kind=r["kind"], link=ltype, lexicon=lname, name_only=not r["has_text"], word=w,
                            via=via, also_found=tuple(others)))
        out.sort(key=lambda x: (_LEX_RANK.get(x.lexicon, 99), _LINK_RANK[x.link], x.stem))
        return out

    def antonym_evidence(self, label: str, stem: str) -> list[Antonym]:
        """Antonym evidence for the candidate: OEWN's sense-level antonyms of the label that name a target, then the
        affix rule's matches (``un-X`` for a target ``X`` and the reverse, ``X-less`` / ``X-ful``); one per target (an
        OEWN antonym the affix rule also gives keeps ``link: antonym`` and records the ``rule``), never the
        candidate's own stem or a placeholder.  ``partner_has_file``: the target has a recorded clean-pair partner (a
        queue entry: a recorded ``partner``)."""
        from dataclasses import replace as _replace
        own = blind(stem)
        out: list[Antonym] = []
        seen: set[tuple[str, str]] = set()
        lex = self.lexicons.get("oewn")
        if lex is not None:
            form, _, _ = first_form(label, lex)
            if form is not None:
                for w in lex.antonyms(form):
                    for t in self._by_form.get(norm(w), ()):
                        if blind(t) == own or (t, "antonym") in seen or is_placeholder(self.rows[t]["label"]):
                            continue
                        seen.add((t, "antonym"))
                        r = self.rows[t]
                        out.append(Antonym(stem=t, link="antonym", partner_has_file=bool(r.get("has_partner")),
                                           lexicon="oewn", kind=r["kind"]))
        for b, rule in affix_pairs(norm(label_forms(label)[0]) if label_forms(label) else stem):
            for t in self._by_blind.get(b, ()):
                if blind(t) == own or (t, "negation_affix") in seen or is_placeholder(self.rows[t]["label"]):
                    continue
                seen.add((t, "negation_affix"))
                if (t, "antonym") in seen:
                    out = [_replace(a, rule=rule) if a.stem == t and a.rule is None else a for a in out]
                    continue
                r = self.rows[t]
                out.append(Antonym(stem=t, link="negation_affix", partner_has_file=bool(r.get("has_partner")),
                                   lexicon="affix", kind=r["kind"], rule=rule))
        return out

    def family_links(self, label: str, stem: str, *, candidates: Optional[Mapping[str, str]] = None,
                     candidate_derivations: Optional[Mapping[str, Sequence[str]]] = None) -> list[dict]:
        """The candidate's stem family: ``[{"stem", "kind": corpus|queue|candidate, "via": derivation|affix,
        "rule"}]``, by stem.  Derivation: a lemma OEWN's ``derivation`` links reach from the label is the member's
        form, or the label's form is one the member's derivations reach (targets' derivations are in the table; a
        candidate's, from ``candidate_derivations`` when given).  Affix: :func:`affix_pairs`.  Members are corpus
        traits, queue entries and ``candidates`` (``{stem: label}``, e.g. the other kept rows); never the candidate
        itself, never a placeholder."""
        own = blind(stem)
        cands = {s: lb for s, lb in (candidates or {}).items() if blind(s) != own and not is_placeholder(lb)}
        cand_form: dict[str, list[str]] = {}
        cand_blind: dict[str, list[str]] = {}
        for s, lb in cands.items():
            for f in label_forms(lb):
                cand_form.setdefault(norm(f), []).append(s)
            cand_blind.setdefault(blind(s), []).append(s)
        out: dict[str, dict] = {}

        def add(s: str, kind: str, via: str, rule: Optional[str] = None) -> None:
            if blind(s) == own or s in out:
                return
            if kind != "candidate" and is_placeholder(self.rows[s]["label"]):
                return
            out[s] = {"stem": s, "kind": kind, "via": via} | ({"rule": rule} if rule else {})

        my_keys = {norm(f) for f in label_forms(label)}
        lex = self.lexicons.get("oewn")
        if lex is not None:
            form, _, _ = first_form(label, lex)
            if form is not None:
                for w in lex.derivations(form):
                    k = norm(w)
                    for t in self._by_form.get(k, ()):
                        add(t, self.rows[t]["kind"], "derivation")
                    for s in cand_form.get(k, ()):
                        add(s, "candidate", "derivation")
        for k in my_keys:
            for t in self._deriv.get(k, ()):
                add(t, self.rows[t]["kind"], "derivation")
        if candidate_derivations:
            for s, ds in candidate_derivations.items():
                if s in cands and my_keys & set(ds):
                    add(s, "candidate", "derivation")
        for b, rule in affix_pairs(norm(label_forms(label)[0]) if label_forms(label) else stem):
            for t in self._by_blind.get(b, ()):
                add(t, self.rows[t]["kind"], "affix", rule)
            for s in cand_blind.get(b, ()):
                add(s, "candidate", "affix", rule)
        return [out[s] for s in sorted(out)]

    def family(self, label: str, stem: str, *, candidates: Optional[Mapping[str, str]] = None,
               candidate_derivations: Optional[Mapping[str, Sequence[str]]] = None) -> list[str]:
        """The stems of :meth:`family_links` (the frozen signature; ``candidates`` adds a candidate set)."""
        return [d["stem"] for d in self.family_links(label, stem, candidates=candidates,
                                                     candidate_derivations=candidate_derivations)]


# --------------------------------------------------------------------------- save and load

def save_lookup(lookup: Lookup, path: Path = LOOKUP_PATH, *, inputs: Optional[list] = None) -> Path:
    """``lookup.json`` in a ``json_metadata`` envelope (``result``: ``{"header", "rows"}``), atomically."""
    from assistant_axis.atomic_io import atomic_write_text
    from assistant_axis.plot_metadata import json_metadata
    payload = {"header": lookup.header, "rows": [lookup.rows[s] for s in sorted(lookup.rows)]}
    env = json_metadata(payload, title="lexical lookup table (plan 11)", inputs=inputs or None)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(json.dumps(env, indent=1, ensure_ascii=False) + "\n", p)
    return p


class StaleLookupError(RuntimeError):
    """The lexicons attached are not the ones the table was built with (rebuild it: ``lexical_recall.py build``)."""


def read_lookup_doc(path: Path = LOOKUP_PATH) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc.get("result", doc)


def default_lexicons(names: Iterable[str], *, moby_path: Optional[Path] = None) -> dict[str, Lexicon]:
    """The real lexicons by name: OEWN through ``wordnet.oewn()``, Moby from ``data/external/moby/mthesaur.txt``
    (``FileNotFoundError`` with the download command when it is missing)."""
    out: dict[str, Lexicon] = {}
    for n in names:
        if n == "oewn":
            out[n] = OewnLexicon()
        elif n == "moby":
            p = Path(moby_path or MOBY_DIR / MOBY_FILE)
            if not p.exists():
                raise FileNotFoundError(f"{p}: the Moby thesaurus is not downloaded "
                                        f"(uv run python data_analysis/gap_generation/setup_external.py --moby)")
            out[n] = MobyLexicon(p)
        else:
            raise ValueError(f"unknown lexicon {n!r} (one of {LEXICONS})")
    return out


def load_lookup(path: Path = LOOKUP_PATH, *, lexicons: Optional[Mapping[str, Lexicon]] = None,
                check_versions: bool = True) -> Lookup:
    """The table at ``path`` with ``lexicons`` attached (default: the real ones the table names).  With
    ``check_versions`` a lexicon whose version differs from the one recorded raises :class:`StaleLookupError`."""
    doc = read_lookup_doc(path)
    header, rows = doc["header"], doc["rows"]
    names = list((header.get("lexicons") or {}).keys())
    lex = dict(lexicons) if lexicons is not None else default_lexicons(names)
    if check_versions:
        for name, info in (header.get("lexicons") or {}).items():
            if name not in lex:
                continue
            want = info.get("id") if name == "oewn" else info.get("sha256")
            if want and lex[name].version != want:
                raise StaleLookupError(f"{path}: built with {name} {want}, attached {lex[name].version}; rebuild it "
                                       f"(lexical_recall.py build)")
    return Lookup(rows=rows, header=header, lexicons=lex)


# --------------------------------------------------------------------------- the Moby download

def _rel(path: Path) -> str:
    for p, root in ((Path(path), REPO_ROOT), (Path(path).resolve(), REPO_ROOT.resolve())):
        try:
            return str(p.relative_to(root))
        except ValueError:
            continue
    return str(path)


@dataclass
class MobyFetch:
    target: Path
    url: str
    fetched: bool = False
    skipped: bool = False
    manifest: dict = field(default_factory=dict)
    written: list = field(default_factory=list)
    lines: list = field(default_factory=list)


def fetch_moby(*, dest_dir: Path = MOBY_DIR, url: str = MOBY_URL, fetcher: Optional[Callable[[str], bytes]] = None,
               dry_run: bool = False, force: bool = False, now: Optional[str] = None,
               sources_manifest_path: Optional[Path] = SOURCES_MANIFEST_PATH, git_sha: Optional[str] = None) -> MobyFetch:
    """Fetch ``mthesaur.txt`` into ``dest_dir`` (``.part``, then a rename), with ``DOWNLOAD_MANIFEST.json`` beside it
    (git-ignored) and the tracked ``sources_manifest.json``: ``{"file", "url", "sha256", "size", "fetched_at", "tool",
    "licence", "approval", "n_heads", "hash_source"}``.  Idempotent: a file on disk that matches the manifest is not
    fetched again (a file with no manifest is recorded as it is); ``force`` fetches anyway.  ``dry_run`` prints the
    target and fetches nothing.  The fetcher is the IPIP downloader's (``Range`` resume on a cut body) unless given."""
    from .registry import utc_now
    dest = Path(dest_dir) / MOBY_FILE
    out = MobyFetch(target=dest, url=url)
    out.lines.append(f"Moby Thesaurus II ({MOBY_SOURCE}): {url} -> {dest} (about {MOBY_EXPECTED_BYTES / 1e6:.1f} MB; "
                     f"{MOBY_LICENCE})")
    if dry_run:
        out.lines.append("DRY-RUN: nothing fetched" + (" (a copy is already on disk)" if dest.exists() else ""))
        return out
    from .generators.ipip.download import load_manifest, sha256_bytes, sha256_file, write_manifest
    man_path = Path(dest_dir) / DOWNLOAD_MANIFEST_NAME
    prev = load_manifest(man_path)
    if dest.exists() and not force:
        on_disk = sha256_file(dest)
        if prev.get("sha256") == on_disk:
            out.skipped = True
            out.manifest = prev
            out.lines.append(f"present: {dest} matches its manifest (sha256 {on_disk[:12]}...); nothing fetched")
            if sources_manifest_path is not None and load_manifest(sources_manifest_path) != prev:
                Path(sources_manifest_path).parent.mkdir(parents=True, exist_ok=True)
                out.written.append(write_manifest(prev, sources_manifest_path))
            return out
        data = dest.read_bytes() if not prev else None
    else:
        data = None
    if data is None:
        if fetcher is None:
            from .generators.ipip.download import _urlopen_bytes as fetcher   # noqa: N813 - the shared fetcher
        data = fetcher(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        part.write_bytes(data)
        part.replace(dest)
        out.fetched = True
    rows = parse_moby(_decode(data))
    doc = {"file": MOBY_FILE, "path": _rel(dest), "url": url, "sha256": sha256_bytes(data), "size": len(data),
           "hash_source": "received bytes (Project Gutenberg publishes no hash for this file)",
           "fetched_at": now or utc_now(), "tool": MOBY_TOOL, "licence": MOBY_LICENCE, "approval": MOBY_APPROVAL,
           "n_heads": len(rows), "git_sha": git_sha}
    if not out.fetched:
        doc["recorded_from_disk"] = True
    out.manifest = doc
    out.written.append(write_manifest(doc, man_path))
    if sources_manifest_path is not None:
        Path(sources_manifest_path).parent.mkdir(parents=True, exist_ok=True)
        out.written.append(write_manifest(doc, sources_manifest_path))
    out.lines.append(f"{'fetched' if out.fetched else 'recorded'} {dest}: {len(data):,} bytes, {len(rows):,} heads, "
                     f"sha256 {doc['sha256']}")
    return out


# --------------------------------------------------------------------------- the labelled pairs

def side_label(side: str, corpus_labels: Mapping[str, str], externals: Mapping[str, Mapping]) -> str:
    """A labelled pair's side as a label: an external (``gloss:``, ``queue:``, ``label:``) by its recorded label, a
    corpus stem by its corpus label, else the stem spaced."""
    if side in externals and externals[side].get("label"):
        return str(externals[side]["label"])
    if ":" in side:
        return side.split(":", 1)[1].replace("_", " ")
    return corpus_labels.get(side) or side.replace("_", " ")


def labelled_measurement(pairs: Sequence[Mapping], lexicons: Mapping[str, Lexicon], *,
                         corpus_labels: Optional[Mapping[str, str]] = None,
                         externals: Optional[Mapping[str, Mapping]] = None) -> dict:
    """The workstream plan's § 6 measurement over M2's labelled pairs: per relation and per lexicon, how many pairs
    have both sides in the lexicon, how many abstain (a side missing), how many carry a synonym-like link (by link
    type, either direction) and how many an antonym link (OEWN's or the affix rule).  ``recall`` on ``duplicate``
    (synonym-like) and ``antonym`` (antonym), ``false_flag`` on ``near_distinct`` and ``unrelated`` (any link), over
    the pairs with both sides found.  Each row of ``examples`` names a linked pair (at most 10 per relation)."""
    corpus_labels = corpus_labels or {}
    externals = externals or {}
    out: dict = {"by_lexicon": {}, "n_pairs": len(pairs)}
    for lname, lex in lexicons.items():
        rel: dict[str, dict] = {}
        for p in pairs:
            r = p.get("relation") or "unknown"
            d = rel.setdefault(r, {"n": 0, "both_found": 0, "abstain": 0, "linked": 0,
                                   "by_link": {t: 0 for t in LINK_TYPES}, "antonym_linked": 0,
                                   "by_antonym": {t: 0 for t in ANTONYM_TYPES}, "any_linked": 0, "examples": []})
            d["n"] += 1
            la = side_label(p["a"], corpus_labels, externals)
            lb = side_label(p["b"], corpus_labels, externals)
            fa, fb = first_form(la, lex)[0], first_form(lb, lex)[0]
            if fa is None or fb is None:
                d["abstain"] += 1
                continue
            d["both_found"] += 1
            t = link_between(la, lb, lex)
            if t:
                d["linked"] += 1
                d["by_link"][t] += 1
            # antonym evidence is OEWN's sense links and the affix rule; Moby has no antonyms
            a = antonym_between(la, lb, lex) if lname == "oewn" else None
            if a:
                d["antonym_linked"] += 1
                d["by_antonym"][a] += 1
            if t or a:
                d["any_linked"] += 1
                if len(d["examples"]) < 10:
                    d["examples"].append({"a": p["a"], "b": p["b"], "link": t, "antonym": a})
        for r, d in rel.items():
            bf = d["both_found"]
            if r == "duplicate":
                d["recall"] = round(d["linked"] / bf, 4) if bf else None
            elif r == "antonym":
                d["recall"] = round(d["antonym_linked"] / bf, 4) if bf else None
            elif r in ("near_distinct", "unrelated"):
                d["false_flag"] = round(d["any_linked"] / bf, 4) if bf else None
        out["by_lexicon"][lname] = dict(sorted(rel.items()))
    return out
