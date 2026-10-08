"""Two-route mapping of the corpus's trait labels (and the seed queue's) onto Roget heads.

Plan § 5 (``roget_map.py``) as revised on 2026-10-08: no LLM adjudication.

* **Lexical route** (:func:`lexical_route`): the label's key forms (lowercase, standard suffix such
  as "(Big Five)" dropped, hyphen and space variants) and their derived forms (WordNet
  derivations and suffix rules: cautious / caution, absolutist / absolutism) looked up among the
  heads' adjectives and nouns.  Strengths: ``exact_adj``, ``exact_noun``, ``derived_adj``,
  ``derived_noun``, ``loose`` (the label as a word of a multiword item, or a multiword label's
  last word).  Hits are ranked dispositional heads first (number >= 450, plus ``extra``), then by
  strength, then by semicolon-group position.
* **Semantic route** (:func:`semantic_route`): the label's corpus text (``label: description``,
  ``representation.trait_text``) against each head's profile (``parse.head_profile``) with the
  platform's embedder (OpenAI ``text-embedding-3-large`` through ``gapgen.embed``, cached); the
  top five heads by cosine.
* **Agreement** (:func:`agreement`): a lexical hit among the semantic top three is the primary
  (``route: agree``), other lexical hits in the top five are secondaries.  Otherwise
  :func:`resolve` applies the rule that replaced the LLM pass: a lexical hit in the top five
  (``rule``), else the semantic top head when its cosine reaches :data:`SEM_FLOOR`
  (``semantic``), else a dispositional exact or derived adjective hit (``lexical``), else
  nothing (``none``).
"""
from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Collection, Iterable, Mapping, Optional, Sequence

import numpy as np

from assistant_axis.atomic_io import atomic_write_text
from assistant_axis.entity_id import normalize_to_file_name

from .parse import DISPOSITIONAL_MIN, RogetIndex, head_profile

MAPPING_RULES_VERSION = 1
STRENGTHS = ("exact_adj", "exact_noun", "derived_adj", "derived_noun", "loose")
ROUTES = ("agree", "rule", "semantic", "lexical", "none")
#: Semantic-only floor: the cosine (text-embedding-3-large, label text against head profile) the
#: top head must reach when no lexical hit is in the top five.  From the first full run
#: (2026-10-08): top cosines of ``agree`` labels run p5 0.33, median 0.47; of the labels left with
#: no head, median 0.34.  By eye, semantic-only placements at 0.40-0.43 were right about three
#: times in five and at 0.36-0.40 about one in two (astrology signs, MBTI types and memberships
#: land on unrelated heads), so the floor stays at 0.40.
SEM_FLOOR = 0.40
#: Confidence recorded per route.
CONFIDENCE = {"agree": 1.0, "rule": 0.7, "semantic": 0.5, "lexical": 0.4, "none": 0.0}
#: Derivational suffix pairs (adjective side first); each is applied in both directions.
DERIVATION_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ious", "ion"), ("ive", "ion"), ("ous", "ousness"), ("ive", "iveness"), ("ent", "ence"),
    ("ant", "ance"), ("ful", "fulness"), ("less", "lessness"), ("al", "ality"), ("able", "ability"),
    ("ible", "ibility"), ("ic", "icism"), ("ist", "ism"), ("istic", "ism"), ("y", "iness"),
    ("ate", "acy"), ("ed", "edness"), ("", "ness"), ("", "ity"), ("ous", "osity"), ("ent", "ency"),
    ("ant", "ancy"),
)


# --------------------------------------------------------------------------- labels

@dataclass
class LabelRecord:
    stem: str
    label: str
    description: Optional[str]
    source: str                         # existing | queued
    status: Optional[str] = None        # queue status (None for an existing file)
    partner_stem: Optional[str] = None
    partner_has_file: bool = False


def _partner_of(stem: str, d: dict, stems: Collection[str]) -> Optional[str]:
    arr = d.get("arrangement")
    arrs = arr if isinstance(arr, list) else ([arr] if isinstance(arr, dict) else [])
    for a in arrs:
        if a.get("kind") == "pair":
            others = [m for m in a.get("members") or [] if m != stem]
            if others:
                return others[0]
    neg = (d.get("negative_label") or "").strip()
    if not neg or neg.lower().startswith("non-"):
        return None
    return normalize_to_file_name(neg)


def load_labels(data_dir: Path, queue_path: Optional[Path] = None) -> list[LabelRecord]:
    """Existing trait files (``data/traits/instructions/*.json``) and the seed queue's trait
    entries that have no file yet, sorted by stem."""
    inst = Path(data_dir) / "traits" / "instructions"
    files = sorted(inst.glob("*.json"))
    stems = {p.stem for p in files}
    out: list[LabelRecord] = []
    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        partner = _partner_of(p.stem, d, stems)
        out.append(LabelRecord(stem=p.stem, label=d.get("positive_label") or p.stem.replace("_", " "),
                               description=d.get("description"), source="existing", status=None,
                               partner_stem=partner, partner_has_file=bool(partner and partner in stems)))
    if queue_path is not None and Path(queue_path).exists():
        q = json.loads(Path(queue_path).read_text(encoding="utf-8"))
        seen = set(stems)
        for e in q.get("entries") or []:
            if e.get("entity_type") != "trait":
                continue
            stem = e.get("stem") or normalize_to_file_name(e.get("label") or "")
            if not stem or stem in seen:
                continue
            seen.add(stem)
            partner = e.get("partner")
            out.append(LabelRecord(stem=stem, label=e.get("label") or stem.replace("_", " "),
                                   description=e.get("description") or e.get("description_draft"),
                                   source="queued", status=e.get("status"),
                                   partner_stem=normalize_to_file_name(partner) if partner else None,
                                   partner_has_file=bool(partner and normalize_to_file_name(partner) in stems)))
    return sorted(out, key=lambda r: (r.source != "existing", r.stem))


# --------------------------------------------------------------------------- forms

def key_forms(label: str) -> list[str]:
    """Lowercase forms of a label: the standard's parenthesis dropped ("openness (Big Five)" ->
    "openness"), with hyphen / space / joined variants."""
    base = re.sub(r"\s*\([^)]*\)\s*", " ", label).strip().lower()
    base = " ".join(base.split())
    forms = [base, base.replace("-", " "), base.replace(" ", "-"), base.replace("-", "").replace(" ", "")]
    return [f for f in dict.fromkeys(forms) if f]


def _suffix_variants(w: str) -> list[str]:
    out = []
    for a, b in DERIVATION_SUFFIXES:
        if w.endswith(a) and len(w) - len(a) >= 3:
            out.append((w[: -len(a)] if a else w) + b)
        if b and w.endswith(b) and len(w) - len(b) >= 3:
            out.append(w[: -len(b)] + a)
    return out


def derived_forms(form: str, lex=None) -> list[str]:
    """Derivationally related forms of a one-word form: WordNet's derivations (when ``lex`` is
    given) and the suffix rules of :data:`DERIVATION_SUFFIXES`, both directions; the form itself
    excluded."""
    if " " in form or "-" in form:
        return []
    out: list[str] = []
    if lex is not None:
        out.extend(lemma.lower() for lemma, _pos in lex.derivations(form))
    out.extend(_suffix_variants(form))
    return [f for f in dict.fromkeys(out) if f and f != form]


# --------------------------------------------------------------------------- lexical route

@dataclass
class LexHit:
    head_id: str
    strength: str
    item: str
    block: str
    group_index: int
    dispositional: bool = True

    def to_json(self) -> dict:
        d = asdict(self)
        d.pop("dispositional")
        return d


class LexIndex:
    """Adjective and noun items of every head, by lowercase form and by word."""

    def __init__(self, index: RogetIndex, blocks: Sequence[str] = ("Adj", "N")):
        self.index = index
        self.exact: dict[str, list[tuple[str, str, int, str]]] = {}
        self.by_word: dict[str, list[tuple[str, str, int, str]]] = {}
        for hid in index.order:
            h = index.heads[hid]
            for b in blocks:
                for gi, g in enumerate(h.pos.get(b, [])):
                    for it in g:
                        low = it.lower()
                        self.exact.setdefault(low, []).append((hid, b, gi, it))
                        words = re.split(r"[\s-]+", low)
                        if len(words) > 1:
                            for w in set(words):
                                self.by_word.setdefault(w, []).append((hid, b, gi, it))


def lexical_route(record: LabelRecord, lexindex: LexIndex, lex=None, *,
                  dispositional: Collection[str] = ()) -> list[LexHit]:
    """Lexical hits for one label, best per head, ranked (see the module docstring)."""
    disp = set(dispositional)
    idx = lexindex.index

    def is_disp(hid: str) -> bool:
        return idx.heads[hid].number >= DISPOSITIONAL_MIN or hid in disp

    best: dict[str, LexHit] = {}

    def add(hits, kind_adj: str, kind_noun: str):
        for hid, b, gi, it in hits:
            strength = kind_adj if b == "Adj" else kind_noun
            hit = LexHit(hid, strength, it, b, gi, is_disp(hid))
            cur = best.get(hid)
            if cur is None or (STRENGTHS.index(hit.strength), hit.group_index) < (STRENGTHS.index(cur.strength),
                                                                                   cur.group_index):
                best[hid] = hit

    forms = key_forms(record.label)
    for f in forms:
        add(lexindex.exact.get(f, []), "exact_adj", "exact_noun")
    for f in forms:
        for d in derived_forms(f, lex):
            add(lexindex.exact.get(d, []), "derived_adj", "derived_noun")
    # loose: the label as one word of a multiword item, or a multiword label's last word as an item
    words = re.split(r"[\s-]+", forms[0])
    if len(words) == 1:
        add(lexindex.by_word.get(words[0], []), "loose", "loose")
    else:
        add(lexindex.exact.get(words[-1], []), "loose", "loose")
    hits = list(best.values())
    hits.sort(key=lambda h: (not h.dispositional, STRENGTHS.index(h.strength), h.group_index,
                             idx.position(h.head_id)))
    return hits


# --------------------------------------------------------------------------- semantic route

@dataclass
class SemHit:
    head_id: str
    sim: float
    rank: int


def label_text(record: LabelRecord) -> str:
    """The corpus representation (``label: description``; the label alone without one)."""
    from assistant_axis.gapgen.representation import trait_text
    return trait_text(record.label, record.description)


def semantic_route(records: Sequence[LabelRecord], index: RogetIndex, head_ids: Sequence[str], *, embedder,
                   cache=None, usage=None, top: int = 5) -> dict[str, list[SemHit]]:
    """Top ``top`` heads per label by cosine between the label text and the head profiles."""
    from assistant_axis.gapgen.embed import embed_texts

    head_ids = list(head_ids)
    htexts = [head_profile(index.heads[h]) for h in head_ids]
    ltexts = [label_text(r) for r in records]
    H = embed_texts(embedder, htexts, cache=cache, usage=usage)
    L = embed_texts(embedder, ltexts, cache=cache, usage=usage)
    S = L @ H.T
    out: dict[str, list[SemHit]] = {}
    for i, r in enumerate(records):
        order = np.argsort(-S[i], kind="stable")[:top]
        out[r.stem] = [SemHit(head_ids[j], round(float(S[i, j]), 4), k + 1) for k, j in enumerate(order)]
    return out


# --------------------------------------------------------------------------- agreement

@dataclass
class Assignment:
    primary: Optional[str]
    secondary: list = field(default_factory=list)
    route: str = "none"
    confidence: float = 0.0
    lexical: list = field(default_factory=list)     # LexHit dicts
    semantic: list = field(default_factory=list)    # SemHit dicts
    llm: Optional[dict] = None


def agreement(lex_hits: Sequence[LexHit], sem_hits: Sequence[SemHit]) -> Optional[Assignment]:
    """The plan's truth table: the first lexical hit (in lexical rank) among the semantic top
    three is the primary (``agree``), other lexical hits in the top five are secondaries; no
    lexical hit in the top three, or no lexical hit, is ``None`` (the plan's LLM case)."""
    top3 = [s.head_id for s in sem_hits[:3]]
    top5 = [s.head_id for s in sem_hits[:5]]
    for h in lex_hits:
        if h.head_id in top3:
            sec = [x.head_id for x in lex_hits if x.head_id != h.head_id and x.head_id in top5]
            return Assignment(primary=h.head_id, secondary=sec, route="agree", confidence=CONFIDENCE["agree"],
                              lexical=[x.to_json() for x in lex_hits], semantic=[asdict(s) for s in sem_hits])
    return None


def resolve(lex_hits: Sequence[LexHit], sem_hits: Sequence[SemHit], *, sem_floor: float = SEM_FLOOR) -> Assignment:
    """:func:`agreement`, else the rule that replaces the LLM pass (module docstring)."""
    a = agreement(lex_hits, sem_hits)
    if a is not None:
        return a
    lexj = [x.to_json() for x in lex_hits]
    semj = [asdict(s) for s in sem_hits]
    top5 = [s.head_id for s in sem_hits[:5]]
    in5 = [h for h in lex_hits if h.head_id in top5]
    if in5:
        return Assignment(primary=in5[0].head_id, secondary=[h.head_id for h in in5[1:]], route="rule",
                          confidence=CONFIDENCE["rule"], lexical=lexj, semantic=semj)
    if sem_hits and sem_hits[0].sim >= sem_floor:
        return Assignment(primary=sem_hits[0].head_id, secondary=[], route="semantic",
                          confidence=CONFIDENCE["semantic"], lexical=lexj, semantic=semj)
    strong = [h for h in lex_hits if h.dispositional and h.strength in ("exact_adj", "derived_adj")]
    if strong:
        return Assignment(primary=strong[0].head_id, secondary=[], route="lexical",
                          confidence=CONFIDENCE["lexical"], lexical=lexj, semantic=semj)
    return Assignment(primary=None, secondary=[], route="none", confidence=0.0, lexical=lexj, semantic=semj)


def map_labels(records: Sequence[LabelRecord], index: RogetIndex, *, lex=None, embedder=None, cache=None,
               usage=None, dispositional: Collection[str] = (), head_ids: Optional[Sequence[str]] = None,
               sem_floor: float = SEM_FLOOR) -> dict[str, Assignment]:
    """Map every record: lexical route, semantic route (skipped without an embedder), resolution."""
    lexindex = LexIndex(index)
    if head_ids is None:
        head_ids = [h for h in index.order if index.heads[h].pos.get("Adj") or index.heads[h].pos.get("N")]
    sem = (semantic_route(records, index, head_ids, embedder=embedder, cache=cache, usage=usage)
           if embedder is not None else {})
    out = {}
    for r in records:
        hits = lexical_route(r, lexindex, lex, dispositional=dispositional)
        out[r.stem] = resolve(hits, sem.get(r.stem, []), sem_floor=sem_floor)
    return out


# --------------------------------------------------------------------------- persistence and reports

def label_heads_payload(records: Sequence[LabelRecord], assignments: Mapping[str, Assignment]) -> dict:
    out = {}
    for r in records:
        a = assignments.get(r.stem)
        if a is None:
            continue
        out[r.stem] = {"label": r.label, "source": r.source, "status": r.status, "partner_stem": r.partner_stem,
                       "partner_has_file": r.partner_has_file, "primary": a.primary, "secondary": list(a.secondary),
                       "route": a.route, "confidence": a.confidence, "lexical": a.lexical, "semantic": a.semantic,
                       "llm": a.llm}
    return out


def save_label_heads(records: Sequence[LabelRecord], assignments: Mapping[str, Assignment], path: Path, *,
                     inputs: Sequence = (), meta: Optional[dict] = None) -> Path:
    from assistant_axis.plot_metadata import json_metadata

    payload = {"rules_version": MAPPING_RULES_VERSION, "sem_floor": SEM_FLOOR, **(meta or {}),
               "labels": label_heads_payload(records, assignments)}
    env = json_metadata(payload, inputs=list(inputs), title="Roget coordinates of the corpus labels (workstream 2)")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    from .parse import dumps_one_per_line
    atomic_write_text(dumps_one_per_line(env, "labels"), path)
    return path


def load_label_heads(path: Path) -> dict[str, dict]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    d = d.get("result", d)
    return d.get("labels", d)


def route_counts(label_heads: Mapping[str, Mapping]) -> dict:
    from collections import Counter
    c = Counter((v["source"], v["route"]) for v in label_heads.values())
    return {f"{s}:{r}": n for (s, r), n in sorted(c.items())}


def trait_link(stem: str, source: str, *, rel: str = "../../traits/instructions", queue_rel: str = "../../seed_queue.json",
               label: Optional[str] = None) -> str:
    """A markdown link to the label's file (an existing trait) or to the seed queue (a queued
    label, whose file does not exist yet)."""
    text = label or stem
    if source == "existing":
        return f"[{text}]({rel}/{stem}.json)"
    return f"[{text}]({queue_rel}) (queued)"


def first_clause(text: Optional[str], n_words: int = 14) -> str:
    if not text:
        return ""
    t = re.split(r"(?<=[.;:])\s", text.strip(), maxsplit=1)[0]
    words = t.split()
    return " ".join(words[:n_words]) + (" ..." if len(words) > n_words else "")


def spotcheck_markdown(records: Sequence[LabelRecord], label_heads: Mapping[str, Mapping], index: RogetIndex, *,
                       n: int = 40, seed: int = 0) -> str:
    """``map_spotcheck.md``: ``n`` random assignments (seeded) for a by-eye check."""
    rng = random.Random(seed)
    pool = sorted(r.stem for r in records if r.stem in label_heads)
    pick = sorted(rng.sample(pool, min(n, len(pool))))
    by = {r.stem: r for r in records}

    def head(h: Optional[str]) -> str:
        return f"{h} {index.heads[h].title}" if h and h in index.heads else "-"

    lines = ["# Roget mapping spot check", "",
             f"{len(pick)} labels drawn at random (seed {seed}) from [label_heads.json](./label_heads.json): the "
             "label's first clause, its lexical hits (head, strength), the semantic top three (head, cosine), "
             "the route and the head chosen.  Routes: *agree* (a lexical hit among the semantic top three), "
             "*rule* (a lexical hit in the top five), *semantic* (the top head, no lexical support), "
             "*lexical* (an exact adjective hit with no semantic support), *none*.", "",
             "| label | first clause | lexical | semantic top 3 | route | primary | secondary |",
             "|---|---|---|---|---|---|---|"]
    for stem in pick:
        v = label_heads[stem]
        r = by[stem]
        lexs = "; ".join(f"{x['head_id']} {x['strength']}" for x in v["lexical"][:4]) or "-"
        sems = "; ".join(f"{x['head_id']} {index.heads[x['head_id']].title} {x['sim']:.2f}" for x in v["semantic"][:3]) or "-"
        lines.append(f"| {trait_link(stem, r.source, label=r.label)} | {first_clause(r.description).replace('|', '/')} | "
                     f"{lexs} | {sems} | {v['route']} | {head(v['primary'])} | "
                     f"{', '.join(head(s) for s in v['secondary']) or '-'} |")
    return "\n".join(lines) + "\n"
