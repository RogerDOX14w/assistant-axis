"""Parse the census files into one table, ``census_table.jsonl`` (plan section 6).

One row per distinct stem (``normalize_to_file_name`` of the cleaned surface): a word in
several Allport-Odbert columns, or in both the TDA and Allport-Odbert, is one row.  Rows that
cannot be cleaned (digits, letters outside Latin, internal punctuation) are kept with
``ineligible_reason: "malformed"`` and no stem.

Eligibility (decisions table, rows 1-2 and 23 of the plan):

* every TDA word is eligible (the TDA is curated and carries a human familiarity, ``prop``);
* an Allport-Odbert-only word is eligible unless it is below the platform's hard-reject line
  as ``gapgen.freq.zipf_info`` computes it for a dictionary word (``curated=False``; the
  negating-prefix rescue applies): Zipf is a feature, never a local literal.  A word in
  neither ``wordfreq`` nor OEWN (after the one-edit repair, :data:`SAFE_REPAIR_KINDS`) has Zipf
  0, so it is cut with the reason ``unknown_word`` unless the negating-prefix rescue holds
  (``unsprightly``), as the platform would route it.
* the corpus and queue matches are computed for evaluation only; no eligibility field reads
  them.

Stages: ``tda``; ``allport_hi`` (Allport-only, eligible, not in the probe band);
``allport_probe`` (Allport-only, eligible, in the probe band).  ``rank`` is global: TDA rows by
``prop`` descending (ties: ``gbooks_freq`` descending, then surface), then Allport-only rows by
Zipf descending (ties: surface), then malformed rows.

``freq_platform`` records what the platform's filter will do with the candidate as submitted
(``curated=True`` since the censuses are a curated generator, the gloss hint, the TDA
familiarity): whether it goes to the definition probe and by which rescue route.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import shutil
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.entity_id import normalize_to_file_name
from assistant_axis.gapgen.freq import HARD_REJECT_BELOW, PROBE_BELOW, FreqInfo, zipf_info
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from . import CENSUS_TABLE_PATH
from .glosshint import Sense, SenseHint, adjective_senses, gloss_hint, person_sense
from .sources import ALLPORT_COLUMNS

SCHEMA_VERSION = 1
STAGE_TDA, STAGE_HI, STAGE_PROBE = "tda", "allport_hi", "allport_probe"
INELIGIBLE_REASONS = ("malformed", "unknown_word", "below_hard_reject")

_FOLD = {"œ": "oe", "Œ": "oe", "æ": "ae", "Æ": "ae", "ß": "ss", "ø": "o", "Ø": "o", "ł": "l", "Ł": "l"}
_APOSTROPHES = "’‘ʼ`´"
_SURFACE_RE = re.compile(r"[a-z]+(?:[ '\-]+[a-z]+)*'?")
_TRAILING = ".,;:!?\"'*)]} -"


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RawEntry:
    raw: str
    line: int
    column: Optional[str]


@dataclass(frozen=True)
class TdaRow:
    adjective: str
    row: int                       # 1-based data row (first row when merged)
    prop: Optional[float]
    n: Optional[int]
    gbooks_freq: Optional[float]
    gn1710: Optional[bool]
    sg435: Optional[bool]
    bffm100: Optional[bool]
    n_rows: int = 1


def parse_allport_txt(path: Path, column: Optional[str]) -> list[RawEntry]:
    """One entry per non-blank line (1-based line numbers; CRLF and a BOM tolerated)."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return [RawEntry(raw=line.strip(), line=i, column=column)
            for i, line in enumerate(text.splitlines(), 1) if line.strip()]


def _num(v: Optional[str], cast):
    if v is None:
        return None
    v = v.strip()
    if v == "" or v.upper() in ("NA", "NAN", "NULL"):
        return None
    try:
        return cast(v)
    except ValueError:
        return cast(float(v)) if cast is int else None


def _flag(v: Optional[str]) -> Optional[bool]:
    n = _num(v, float)
    return None if n is None else bool(n)


def parse_tda_properties(path: Path) -> list[TdaRow]:
    """Header-driven parse of ``TDA_properties`` (comma or tab separated, quotes stripped).

    Rows naming the same adjective (case-insensitive) are merged: mean ``prop`` (over rows that
    have one), summed ``N``, the first non-null ``gbooks.freq``, flags or-ed, ``n_rows`` the
    count.  Output is in first-appearance order."""
    text = Path(path).read_text(encoding="utf-8-sig")
    first = text.splitlines()[0] if text else ""
    delim = "\t" if first.count("\t") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    cols = {c.strip().strip('"').lower(): c for c in (reader.fieldnames or [])}
    for need in ("adjective", "prop"):
        if need not in cols:
            raise ValueError(f"{path}: header lacks {need!r} (has {list(cols)})")

    def get(r, name):
        c = cols.get(name)
        return None if c is None else (r.get(c) or "").strip().strip('"')

    merged: dict[str, dict] = {}
    for i, r in enumerate(reader, 1):
        adj = get(r, "adjective")
        if not adj:
            continue
        key = adj.lower()
        rec = {"adjective": adj, "row": i, "prop": _num(get(r, "prop"), float), "n": _num(get(r, "n"), int),
               "gbooks_freq": _num(get(r, "gbooks.freq"), float), "gn1710": _flag(get(r, "gn1710")),
               "sg435": _flag(get(r, "sg435")), "bffm100": _flag(get(r, "bffm100"))}
        if key not in merged:
            merged[key] = {**rec, "_props": [rec["prop"]] if rec["prop"] is not None else [], "n_rows": 1}
            continue
        m = merged[key]
        m["n_rows"] += 1
        if rec["prop"] is not None:
            m["_props"].append(rec["prop"])
        if rec["n"] is not None:
            m["n"] = (m["n"] or 0) + rec["n"]
        if m["gbooks_freq"] is None:
            m["gbooks_freq"] = rec["gbooks_freq"]
        for f in ("gn1710", "sg435", "bffm100"):
            if rec[f] is not None:
                m[f] = bool(m[f]) or rec[f]
    out = []
    for m in merged.values():
        props = m.pop("_props")
        m["prop"] = round(sum(props) / len(props), 4) if props else None
        out.append(TdaRow(**m))
    return out


# ---------------------------------------------------------------------------
# Cleaning and repair
# ---------------------------------------------------------------------------

def fold_ascii(s: str) -> str:
    for k, v in _FOLD.items():
        s = s.replace(k, v)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def clean_surface(raw: str) -> Optional[str]:
    """Strip, fold to ASCII, lowercase, straighten apostrophes, drop trailing punctuation.
    ``None`` when digits, non-Latin letters or internal punctuation other than hyphen,
    apostrophe and space remain (``F.F.V``)."""
    if raw is None:
        return None
    s = str(raw).strip()
    for a in _APOSTROPHES:
        s = s.replace(a, "'")
    s = fold_ascii(s).lower()
    s = " ".join(s.split())
    s = s.rstrip(_TRAILING).lstrip(" -'\"(")
    if not s or not _SURFACE_RE.fullmatch(s):
        return None
    return s


def edits1(word: str) -> set[str]:
    """Every string one insertion, deletion or substitution away (letters a-z, hyphen)."""
    letters = "abcdefghijklmnopqrstuvwxyz-"
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    out = {a + b[1:] for a, b in splits if b}
    out |= {a + c + b[1:] for a, b in splits if b for c in letters}
    out |= {a + c + b for a, b in splits for c in letters}
    out.discard(word)
    return out


def repair_ocr(surface: str, *, lexicon: Iterable[str]) -> Optional[str]:
    """The unique OEWN adjective lemma one edit away, else None.  Called only for a surface that
    is in neither ``wordfreq`` nor OEWN (:func:`build_table`)."""
    lex = lexicon if isinstance(lexicon, (set, frozenset)) else set(lexicon)
    hits = sorted(edits1(surface) & lex)
    return hits[0] if len(hits) == 1 else None


VOWELS = frozenset("aeiouy")
#: Repairs :func:`build_table` applies.  On the real list (2026-10-08) the unique one-edit
#: lemma was right for most letter doublings and vowel insertions past the second letter
#: (belicose, probbing, orented, marriagable) and wrong for most other edits, because the
#: Allport-Odbert transcription is not OCR and its unknown words are mostly genuine archaic
#: words near a modern one (cullying -> bullying, unlicked -> unlocked, stirless -> starless).
#: Other one-edit hits are recorded as suggestions in ``ingest_counts.json``, not applied.
SAFE_REPAIR_KINDS = ("doubling", "vowel_insertion")


def repair_kind(original: str, repaired: str) -> str:
    """Classify a one-edit repair: ``early`` (an edit in the first two letters), ``doubling``
    (a doubled letter added or removed), ``vowel_insertion``, ``vowel_substitution``, ``other``."""
    a, b = original, repaired
    if len(a) == len(b):
        i = next((k for k in range(len(a)) if a[k] != b[k]), len(a))
        if i < 2:
            return "early"
        return "vowel_substitution" if a[i] in VOWELS and b[i] in VOWELS else "other"
    if len(b) == len(a) + 1:
        i = next((k for k in range(len(a)) if a[k] != b[k]), len(a))
        c = b[i]
        if i < 2:
            return "early"
        if b[i - 1] == c or (i + 1 < len(b) and b[i + 1] == c):
            return "doubling"
        return "vowel_insertion" if c in VOWELS else "other"
    if len(b) == len(a) - 1:
        i = next((k for k in range(len(b)) if a[k] != b[k]), len(b))
        c = a[i]
        if i < 2:
            return "early"
        if a[i - 1] == c or (i + 1 < len(a) and a[i + 1] == c):
            return "doubling"
        return "other"
    return "other"


# ---------------------------------------------------------------------------
# Lookups (real data, or fakes in tests)
# ---------------------------------------------------------------------------

@dataclass
class Lookups:
    """External lookups the table needs; :func:`default_lookups` wires the real ones."""
    zipf: Callable[[str], float]                    # wordfreq Zipf of the whole surface
    in_wordnet: Callable[[str], bool]               # OEWN has the surface (any form, any POS)
    senses: Callable[[str], list[Sense]]            # glosshint.adjective_senses
    adjective_lemmas: frozenset = frozenset()       # OCR repair lexicon
    freq: Callable[..., FreqInfo] = zipf_info       # the platform's frequency features
    zipf_word: Optional[Callable[[str], float]] = None  # per-word Zipf passed to ``freq`` (tests)

    def freq_info(self, surface: str, **kw) -> FreqInfo:
        if self.zipf_word is not None:
            kw["zipf_fn"] = self.zipf_word
        return self.freq(surface, **kw)


def default_lookups() -> Lookups:  # pragma: no cover - needs wordfreq and the OEWN database
    from wordfreq import zipf_frequency

    from assistant_axis.gapgen.wordnet import adjective_lemmas, ensure_oewn, oewn

    if not ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = oewn()
    from .glosshint import lookup_forms

    def in_wn(surface: str) -> bool:
        return any(w.words(f) for f in lookup_forms(surface))

    lemmas = frozenset(x.lower() for x in adjective_lemmas(wordnet=w))
    return Lookups(zipf=lambda s: float(zipf_frequency(s, "en")), in_wordnet=in_wn,
                   senses=lambda s: adjective_senses(s, wordnet=w), adjective_lemmas=lemmas)


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

@dataclass
class TableRow:
    schema_version: int
    surface: Optional[str]
    stem: Optional[str]
    label: Optional[str]
    allport: Optional[dict]
    in_merged: Optional[bool]
    tda: Optional[dict]
    zipf: Optional[float]
    freq_hard_reject: Optional[bool]
    freq_probe_band: Optional[bool]
    freq_rescue: Optional[str]
    freq_platform: Optional[dict]
    wordnet: Optional[dict]
    gloss_hint: Optional[str]
    repaired_from: Optional[str]
    unknown_word: bool
    eligible: bool
    ineligible_reason: Optional[str]
    stage: Optional[str]
    rank: int
    score: Optional[float]
    corpus_stem_match: bool
    queue_stem_match: bool

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, d: Mapping) -> "TableRow":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})

    @property
    def columns(self) -> list[str]:
        return list((self.allport or {}).get("columns") or [])

    @property
    def source_ref(self) -> Optional[str]:
        if self.tda:
            return f"tda:{self.tda['row']}"
        if self.allport:
            c = self.allport["columns"][0]
            return f"allport:{c}:{self.allport['line'][c]}"
        return None


@dataclass
class _Acc:
    surface: str
    allport: dict = field(default_factory=lambda: {"columns": [], "raw": {}, "line": {}})
    tda: Optional[TdaRow] = None
    repaired_from: Optional[str] = None
    n_known: int = 0      # Allport entries found in wordfreq or OEWN (or repaired)
    n_unknown: int = 0    # Allport entries in neither, unrepaired

    @property
    def unknown_word(self) -> bool:
        """No TDA row and no Allport entry that wordfreq or OEWN knows."""
        return self.tda is None and self.n_known == 0 and self.n_unknown > 0


def _allport_order(entries: Iterable[RawEntry]) -> list[RawEntry]:
    order = {c: i for i, c in enumerate(ALLPORT_COLUMNS)}
    return sorted(entries, key=lambda e: (order.get(e.column, 99), e.line))


def build_table(allport: Iterable[RawEntry], tda: Sequence[TdaRow], *, lookups: Lookups,
                corpus_stems: Iterable[str] = (), queue_stems: Iterable[str] = (),
                merged: Optional[Iterable[RawEntry]] = None) -> tuple[list[TableRow], dict]:
    """The census table and its ingest counts (see the module docstring).

    ``allport`` holds the four column files' entries (``column`` set); ``merged`` the entries of
    the merged file, used only for ``in_merged``.  Returns ``(rows in rank order, counts)``."""
    corpus, queue = set(corpus_stems), set(queue_stems)
    counts: Counter = Counter()
    malformed: list[dict] = []
    repaired: list[dict] = []
    suggestions: list[dict] = []
    accs: dict[str, _Acc] = {}

    def acc_for(surface: str) -> _Acc:
        stem = normalize_to_file_name(normalize_candidate(surface).label)
        if stem not in accs:
            accs[stem] = _Acc(surface=surface)
        return accs[stem]

    # TDA first, so that its surface wins for a word in both censuses
    for t in tda:
        s = clean_surface(t.adjective)
        counts["tda_rows_merged_extra"] += t.n_rows - 1
        if s is None:
            malformed.append({"source": "tda", "raw": t.adjective, "row": t.row})
            continue
        a = acc_for(s)
        if a.tda is not None:
            counts["tda_stem_collisions"] += 1
            continue
        a.tda = t

    seen_col: set[tuple[str, str]] = set()
    for e in _allport_order(allport):
        counts[f"allport_lines_{e.column}"] += 1
        s = clean_surface(e.raw)
        if s is None:
            malformed.append({"source": f"allport:{e.column}", "raw": e.raw, "line": e.line})
            continue
        try:
            normalize_candidate(s)
        except ValueError:
            malformed.append({"source": f"allport:{e.column}", "raw": e.raw, "line": e.line})
            continue
        unknown = not lookups.in_wordnet(s) and lookups.zipf(s) <= 0.0
        rep = None
        if unknown:
            hit = repair_ocr(s, lexicon=lookups.adjective_lemmas)
            if hit is not None:
                kind = repair_kind(s, hit)
                rec = {"raw": e.raw, "column": e.column, "line": e.line, "repaired": hit, "kind": kind}
                if kind in SAFE_REPAIR_KINDS:
                    rep = hit
                    repaired.append(rec)
                else:
                    suggestions.append(rec)
        surface = rep or s
        stem = normalize_to_file_name(normalize_candidate(surface).label)
        existed = stem in accs
        a = acc_for(surface)
        if (stem, e.column) in seen_col:
            counts["allport_within_column_duplicates"] += 1
            continue
        seen_col.add((stem, e.column))
        if existed and a.allport["columns"]:
            counts["allport_cross_column_merges"] += 1
        if rep is not None:
            a.repaired_from = a.repaired_from or s
        if unknown and rep is None:
            a.n_unknown += 1
        else:
            a.n_known += 1
        a.allport["columns"].append(e.column)
        a.allport["raw"][e.column] = e.raw
        a.allport["line"][e.column] = e.line

    merged_surfaces = None
    if merged is not None:
        merged_surfaces = {clean_surface(m.raw) for m in merged}
        merged_surfaces.discard(None)

    rows: list[TableRow] = []
    for stem, a in accs.items():
        t = a.tda
        cols = a.allport["columns"]
        label = normalize_candidate(a.surface).label
        hint: Optional[SenseHint] = person_sense(lookups.senses(a.surface))
        gh = gloss_hint(label, hint, cols, in_tda=t is not None)
        dict_floor = lookups.freq_info(a.surface)
        platform = lookups.freq_info(a.surface, familiarity=t.prop if t else None, gloss_hint=bool(gh),
                                     curated=True)
        if t is not None:
            eligible, reason, stage = True, None, STAGE_TDA
        elif dict_floor.hard_reject:
            eligible, stage = False, None
            reason = "unknown_word" if a.unknown_word else "below_hard_reject"
        else:
            eligible, reason = True, None
            stage = STAGE_PROBE if dict_floor.probe_band else STAGE_HI
        in_merged = None
        if cols and merged_surfaces is not None:
            in_merged = any(clean_surface(a.allport["raw"][c]) in merged_surfaces for c in cols)
        senses_found = hint is not None
        rows.append(TableRow(
            schema_version=SCHEMA_VERSION, surface=a.surface, stem=stem, label=label,
            allport=({"columns": cols, "raw": dict(a.allport["raw"]), "line": dict(a.allport["line"])}
                     if cols else None),
            in_merged=in_merged,
            tda=({"row": t.row, "prop": t.prop, "n": t.n, "gbooks_freq": t.gbooks_freq, "gn1710": t.gn1710,
                  "sg435": t.sg435, "bffm100": t.bffm100, "n_rows": t.n_rows} if t else None),
            zipf=dict_floor.zipf_min,
            freq_hard_reject=dict_floor.hard_reject, freq_probe_band=dict_floor.probe_band,
            freq_rescue=dict_floor.rescue,
            freq_platform={"probe": platform.probe_band, "hard_reject": platform.hard_reject,
                           "rescue": platform.rescue},
            wordnet={"found": senses_found, "n_adj_senses": hint.n_adj_senses if hint else 0,
                     "person_sense_rank": hint.rank if hint else None,
                     "definition": hint.definition if hint else None, "pos": hint.pos if hint else None},
            gloss_hint=gh, repaired_from=a.repaired_from, unknown_word=a.unknown_word, eligible=eligible,
            ineligible_reason=reason, stage=stage, rank=0, score=t.prop if t else None,
            corpus_stem_match=stem in corpus, queue_stem_match=stem in queue))
    for m in malformed:
        rows.append(TableRow(
            schema_version=SCHEMA_VERSION, surface=None, stem=None, label=m["raw"],
            allport=({"columns": [m["source"].split(":")[1]], "raw": {m["source"].split(":")[1]: m["raw"]},
                      "line": {m["source"].split(":")[1]: m["line"]}} if m["source"] != "tda" else None),
            in_merged=None,
            tda=({"row": m["row"]} if m["source"] == "tda" else None),
            zipf=None, freq_hard_reject=None, freq_probe_band=None, freq_rescue=None,
            freq_platform=None, wordnet=None, gloss_hint=None, repaired_from=None, unknown_word=False,
            eligible=False, ineligible_reason="malformed", stage=None, rank=0, score=None,
            corpus_stem_match=False, queue_stem_match=False))

    def key(r: TableRow):
        if r.ineligible_reason == "malformed":
            return (2, 0.0, 0.0, r.label or "")
        if r.tda:
            gf = r.tda.get("gbooks_freq")
            return (0, -(r.tda.get("prop") or 0.0), -(gf if gf is not None else -1e9), r.surface)
        return (1, -(r.zipf or 0.0), 0.0, r.surface)

    rows.sort(key=key)
    for i, r in enumerate(rows, 1):
        r.rank = i
    counts["n_repaired"] = len(repaired)
    counts["n_repair_suggestions"] = len(suggestions)
    counts["n_malformed"] = len(malformed)
    return rows, {"counters": dict(sorted(counts.items())), "malformed": malformed, "repaired": repaired,
                  "repair_suggestions": suggestions}


def zipf_band(z: Optional[float]) -> str:
    """Report bands; the two lower edges are the platform's own (``gapgen.freq``)."""
    if z is None:
        return "none"
    if z < HARD_REJECT_BELOW:
        return f"<{HARD_REJECT_BELOW}"
    if z < PROBE_BELOW:
        return f"{HARD_REJECT_BELOW}-{PROBE_BELOW}"
    if z < 3.5:
        return f"{PROBE_BELOW}-3.5"
    return ">=3.5"


def ingest_counts(rows: Sequence[TableRow], extra: Mapping) -> dict:
    """Rows per column, stage, Zipf band and reason; unknown / repaired / malformed counts."""
    c = {"n_rows": len(rows),
         "n_tda": sum(1 for r in rows if r.tda and r.stem),
         "n_allport": sum(1 for r in rows if r.allport and r.stem),
         "n_both": sum(1 for r in rows if r.tda and r.allport and r.stem),
         "n_eligible": sum(1 for r in rows if r.eligible),
         "per_column": {col: sum(1 for r in rows if col in r.columns and r.stem) for col in ALLPORT_COLUMNS},
         "only_column": {col: sum(1 for r in rows if r.columns == [col] and not r.tda) for col in ALLPORT_COLUMNS},
         "per_stage": dict(sorted(Counter(r.stage or "none" for r in rows).items())),
         "ineligible": dict(sorted(Counter(r.ineligible_reason for r in rows if not r.eligible).items())),
         "per_zipf_band": {
             "tda": dict(sorted(Counter(zipf_band(r.zipf) for r in rows if r.tda and r.stem).items())),
             "allport_only": dict(sorted(Counter(zipf_band(r.zipf) for r in rows
                                                 if r.allport and not r.tda and r.stem).items()))},
         "tda_below_dictionary_floor": sum(1 for r in rows if r.tda and r.freq_hard_reject),
         "platform_probe": dict(sorted(Counter(r.stage or "none" for r in rows
                                               if r.freq_platform and r.freq_platform.get("probe")).items())),
         "unknown_word": sum(1 for r in rows if r.unknown_word),
         "repaired": len(extra.get("repaired") or []),
         "repair_suggestions": len(extra.get("repair_suggestions") or []),
         "malformed": len(extra.get("malformed") or []),
         "with_gloss_hint": sum(1 for r in rows if r.gloss_hint),
         "corpus_stem_match": sum(1 for r in rows if r.corpus_stem_match),
         "queue_stem_match": sum(1 for r in rows if r.queue_stem_match)}
    c.update({"counters": dict(extra.get("counters") or {})})
    return c


# ---------------------------------------------------------------------------
# Table I/O
# ---------------------------------------------------------------------------

def table_text(rows: Sequence[TableRow]) -> str:
    return "".join(json.dumps(r.to_json(), ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)


def write_table(rows: Sequence[TableRow], path: Path = CENSUS_TABLE_PATH) -> Optional[Path]:
    """Write the table; when the content changes, the old file is first copied to
    ``<path>.bak.<UTC>`` (snapshot before overwrite).  Returns the backup path, if any."""
    path = Path(path)
    body = table_text(rows)
    backup = None
    if path.exists():
        if path.read_text(encoding="utf-8") == body:
            return None
        backup = path.with_name(f"{path.name}.bak.{utc_stamp()}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(body, path)
    return backup


def load_census_table(path: Path = CENSUS_TABLE_PATH) -> list[TableRow]:
    """The census table (frozen interface): rows in rank order."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(TableRow.from_json(json.loads(line)))
    return rows


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
