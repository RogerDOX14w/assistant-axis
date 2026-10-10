"""The candidate table: one row per distinct stem (plan sections 5 and 6, ``table.py``).

:func:`build_table` reads a round's samples in index order, extracts each continuation's items
(:func:`.parse.extract_items`), applies the mechanical noun rule (:func:`.parse.normalize_form`), and folds the
items by stem (``normalize_candidate(surface).stem``, i.e. ``normalize_to_file_name``):

* ``count``: the number of samples that emitted the stem (a repeat inside one continuation counts once, so a
  degenerate loop cannot inflate it); ``families``: the same per prompt family;
* echoes are dropped and counted: a sample's own seed words (``n_seed_echo``), and, in the person family, the
  person's name and any several-word span found in the biography (``n_bio_echo``), so the tracked table never
  carries biography text;
* ``sample_gloss``: the first gloss the model wrote for the word (glossary and AI families only), kept for review
  and never sent to M1; ``gloss_hint``: the OEWN person-descriptive sense (the censuses' :mod:`glosshint`), else
  None; ``partner_seed``: the seed adjective of the contrast samples that emitted the word (the most frequent);
* eligibility: ``cleaned`` and not ``unknown_word`` (a content word neither ``wordfreq`` nor OEWN knows) and not
  ``freq_hard_reject`` (``gapgen.freq.zipf_info``, the platform's floor, never a local literal);
* ``rank``: count descending, ties by first appearance; ``corpus_stem_match`` / ``queue_stem_match`` /
  ``in_tda`` are for evaluation only (no eligibility field reads them).

Deterministic: the same samples give a byte-identical table.
"""
from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Mapping, Optional, Sequence

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.gapgen.freq import FreqInfo, zipf_info
from assistant_axis.gapgen.normalize import normalize_candidate
from assistant_axis.gapgen.registry import utc_stamp

from ..censuses.glosshint import Sense, gloss_hint, person_sense
from .parse import Lexicon, extract_items, normalize_form

SCHEMA_VERSION = 1
GLOSS_FAMILIES = ("list_gloss", "ai_assistant")
FORMS = ("adjective", "noun", "phrase")


@dataclass
class Lookups:
    """External lookups the table needs; :func:`default_lookups` wires the real ones."""
    zipf_word: Callable[[str], float]           # wordfreq Zipf of one word
    in_wordnet: Callable[[str], bool]           # OEWN has the form (any part of speech)
    senses: Callable[[str], list[Sense]]        # glosshint.adjective_senses
    lexicon: Lexicon
    freq: Callable[[str], FreqInfo] = field(default=zipf_info)


def default_lookups() -> Lookups:  # pragma: no cover - needs wordfreq and the OEWN database
    from wordfreq import zipf_frequency

    from assistant_axis.gapgen.wordnet import ADJ_POS, ensure_oewn, oewn

    from ..censuses.glosshint import adjective_senses, lookup_forms
    if not ensure_oewn(download=False):
        raise SystemExit("OEWN is not installed in data/external/wn: run "
                         "`uv run python data_analysis/gap_generation/setup_external.py --wn` first")
    w = oewn()
    adjs = frozenset(x.lemma().lower() for pos in ADJ_POS for x in w.words(pos=pos))
    nouns = frozenset(x.lemma().lower() for x in w.words(pos="n"))
    return Lookups(zipf_word=lambda t: float(zipf_frequency(t, "en")),
                   in_wordnet=lambda s: any(w.words(f) for f in lookup_forms(s)),
                   senses=lambda s: adjective_senses(s, wordnet=w), lexicon=Lexicon(adjectives=adjs, nouns=nouns))


@dataclass
class _Acc:
    surface: str
    form: str
    normalized_from: Optional[str]
    first: tuple
    first_sample_id: str
    count: int = 0
    families: Counter = field(default_factory=Counter)
    gloss: Optional[str] = None
    partners: Counter = field(default_factory=Counter)


def _bio_words(name: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[^\W\d_]+", name or "")}


def build_table(samples: Iterable[Mapping], *, lookups: Lookups, corpus_stems: Iterable[str] = (),
                queue_stems: Iterable[str] = (), tda_stems: Iterable[str] = (),
                bio_lookup: Optional[Callable[[str], Optional[tuple[str, str]]]] = None) -> tuple[list[dict], dict]:
    """``(rows in rank order, counts)`` from a round's sample records (see the module docstring).
    ``bio_lookup(ref) -> (name, text)`` serves the person family's biography (the cached pool)."""
    corpus, queue, tda = set(corpus_stems), set(queue_stems), set(tda_stems)
    counts: Counter = Counter()
    accs: dict[str, _Acc] = {}
    ordered = sorted(samples, key=lambda s: (int(s.get("index", 0)), str(s["sample_id"])))
    for s in ordered:
        counts["n_samples"] += 1
        fam = s["family"]
        seeds = {w.lower() for w in s.get("seed_words") or []}
        bio = None
        if fam == "person" and bio_lookup is not None:
            ref = next((r for r in s.get("seed_refs") or [] if r.startswith("wikibio:")), None)
            bio = bio_lookup(ref) if ref else None
        name_words = _bio_words(bio[0]) if bio else set()
        bio_text = (bio[1] or "").lower() if bio else ""
        seen_here: set[str] = set()
        for it in extract_items(s.get("text") or "", fam):
            counts["n_raw_items"] += 1
            surface, form, norm_from = normalize_form(it.surface, lexicon=lookups.lexicon)
            if surface in seeds or it.surface in seeds:
                counts["n_seed_echo"] += 1
                continue
            if bio is not None and (surface in name_words or (" " in surface and surface in bio_text)):
                counts["n_bio_echo"] += 1
                continue
            try:
                stem = normalize_candidate(surface).stem
            except ValueError:
                counts["n_malformed"] += 1
                continue
            if stem in seen_here:
                counts["n_repeat_in_sample"] += 1
                continue
            seen_here.add(stem)
            a = accs.get(stem)
            if a is None:
                a = accs[stem] = _Acc(surface=surface, form=form, normalized_from=norm_from,
                                      first=(int(s.get("index", 0)), str(s["sample_id"]), it.position),
                                      first_sample_id=str(s["sample_id"]))
            a.count += 1
            a.families[fam] += 1
            if a.gloss is None and it.gloss and fam in GLOSS_FAMILIES:
                a.gloss = it.gloss
            if fam == "contrast" and s.get("partner_seed"):
                a.partners[s["partner_seed"]] += 1
    rows = [_row(stem, a, lookups=lookups, corpus=corpus, queue=queue, tda=tda) for stem, a in accs.items()]
    rows.sort(key=lambda r: (-r["count"], accs[r["stem"]].first))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    by_form = {f: sum(1 for r in rows if r["form"] == f) for f in FORMS}
    out = {"n_samples": counts["n_samples"], "n_raw_items": counts["n_raw_items"], "n_unique": len(rows),
           "n_eligible": sum(1 for r in rows if r["eligible"]), "n_seed_echo": counts["n_seed_echo"],
           "n_bio_echo": counts["n_bio_echo"], "n_malformed": counts["n_malformed"],
           "n_repeat_in_sample": counts["n_repeat_in_sample"], "by_form": by_form,
           "by_form_eligible": {f: sum(1 for r in rows if r["form"] == f and r["eligible"]) for f in FORMS},
           "ineligible": dict(sorted(Counter(r["ineligible_reason"] for r in rows if not r["eligible"]).items())),
           "normalized_mechanically": sum(1 for r in rows if r["normalized_from"])}
    return rows, out


def _row(stem: str, a: _Acc, *, lookups: Lookups, corpus: set, queue: set, tda: set) -> dict:
    norm = normalize_candidate(a.surface)
    tokens = norm.content_words
    unknown = any(lookups.zipf_word(t) <= 0.0 and not lookups.in_wordnet(t) for t in tokens)
    fi = lookups.freq(a.surface)
    senses = lookups.senses(a.surface)
    hint = person_sense(senses)
    in_oewn = bool(senses) or lookups.in_wordnet(a.surface)
    if unknown:
        eligible, reason = False, "unknown_word"
    elif fi.hard_reject:
        eligible, reason = False, "below_hard_reject"
    else:
        eligible, reason = True, None
    partner = None
    if a.partners:
        top = max(a.partners.values())
        partner = sorted(k for k, v in a.partners.items() if v == top)[0]
    return {"schema_version": SCHEMA_VERSION, "surface": a.surface, "stem": stem, "form": a.form,
            "normalized_from": a.normalized_from, "count": a.count, "families": dict(sorted(a.families.items())),
            "first_sample_id": a.first_sample_id, "sample_gloss": a.gloss, "zipf": fi.zipf_min,
            "freq_hard_reject": fi.hard_reject, "freq_probe_band": fi.probe_band, "in_oewn": in_oewn,
            "in_tda": stem in tda,
            "wordnet": {"n_adj_senses": hint.n_adj_senses if hint else 0,
                        "person_sense_rank": hint.rank if hint else None,
                        "definition": hint.definition if hint else None},
            "gloss_hint": gloss_hint(norm.label, hint), "partner_seed": partner, "eligible": eligible,
            "ineligible_reason": reason, "unknown_word": unknown, "rank": 0, "corpus_stem_match": stem in corpus,
            "queue_stem_match": stem in queue}


# ---------------------------------------------------------------------------- I/O

def table_text(rows: Sequence[Mapping]) -> str:
    return "".join(json.dumps(dict(r), ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows)


def write_table(rows: Sequence[Mapping], path: Path) -> Optional[Path]:
    """Write the table; when the content changes, the old file is first copied to ``<path>.bak.<UTC>``
    (snapshot before overwrite).  Returns the backup path, if any."""
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


def load_table(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def load_samples(path: Path, *, temperature: Optional[float] = None) -> list[dict]:
    """A round's sample records (optionally one temperature of a grid)."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if temperature is None or float(d.get("temperature")) == float(temperature):
                out.append(d)
    return out


def bio_lookup_from_pool(pool: Iterable) -> Callable[[str], Optional[tuple[str, str]]]:
    m = {b.ref: (b.name, b.text) for b in pool}
    return m.get
